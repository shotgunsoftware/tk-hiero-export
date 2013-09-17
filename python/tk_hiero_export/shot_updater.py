# Copyright (c) 2013 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

import os
import shutil
import tempfile
import traceback

from PySide import QtCore

import hiero.core
from hiero.exporters import FnShotExporter

from .base import ShotgunHieroObjectBase
from .collating_exporter import CollatingExporter


class ShotgunShotUpdater(ShotgunHieroObjectBase, FnShotExporter.ShotTask, CollatingExporter):
    """
    Ensures that Shots and Sequences exist in Shotgun
    """
    def __init__(self, initDict):
        FnShotExporter.ShotTask.__init__(self, initDict)
        CollatingExporter.__init__(self)

    def taskStep(self):
        """
        Execution payload.
        """
        # Only process actual shots... so uncollated items and hero collated items
        if self.isCollated() and not self.isHero():
            return False

        # execute base class
        FnShotExporter.ShotTask.taskStep(self)

        # ensure we have a sequence in shotgun
        sg_sequence = self._create_and_return_sg_sequence()

        # refresh thumbnail for seq
        self._upload_poster_frame(sg_sequence, self._sequence)

        # ensure we have a shot in shotgun, code project and sequence will be filled out
        sg_shot = self._create_and_return_sg_shot(sg_sequence)

        # get cut info
        handles = self._cutHandles if self._cutHandles is not None else 0
        (head_in, tail_out) = self.collatedOutputRange(clampToSource=False)
        cut_in = head_in + handles
        cut_out = tail_out - handles

        # update the shot in Shotgun
        data = {
            "sg_cut_order": self.app.shot_count + 1,
            "sg_head_in": head_in,
            "sg_cut_in": cut_in,
            "sg_cut_out": cut_out,
            "sg_tail_out": tail_out,
            "sg_cut_duration": cut_out - cut_in + 1,
            "sg_working_duration": tail_out - head_in + 1,
        }

        # get status from the hiero tags
        status = None
        status_map = dict(self._preset.properties()["sg_status_hiero_tags"])
        for tag in self._item.tags():
            if tag.name() in status_map:
                status = status_map[tag.name()]
                break
        if status:
            data['sg_status_list'] = status

        # get task template from the tags
        template = None
        template_map = dict(self._preset.properties()["task_template_map"])
        for tag in self._item.tags():
            if tag.name() in template_map:
                template = self.app.tank.shotgun.find_one('TaskTemplate',
                                                          [['entity_type', 'is', 'Shot'],
                                                           ['code', 'is', template_map[tag.name()]]])
                break

        # if there are no associated, assign default template...
        if len(self._item.tags()) == 0:
            default_template = self.parent.get_setting('default_task_template')
            if default_template:
                template = self.parent.tank.shotgun.find_one('TaskTemplate', [['entity_type', 'is', 'Shot'],
                                                                              ['code', 'is', default_template]])

        if template:
            data['task_template'] = template

        # commit the changes and update the thumbnail
        self.app.log_debug("Updating info for Shot %s: %s" % (sg_shot["id"], str(data)))
        self.app.tank.shotgun.update('Shot', sg_shot['id'], data)
        self._upload_poster_frame(sg_shot, self._item.source())

        # create the directory structure
        self.app.log_debug("Creating file system structure for Shot %s..." % sg_shot['id'])
        self.app.tank.create_filesystem_structure('Shot', [sg_shot['id']])

        # return without error
        self.app.log_info("Updated shot %s" % self.shotName())

        # keep shot count
        self.app.shot_count += 1

        # return false to indicate success
        return False

    def _create_and_return_sg_sequence(self):
        """
        Checks for a sequence in shotgun for the current object.
        Creates on if it doesn't exist.

        :returns: A shotgun entity dictionary
        """
        # stick a lookup cache on the app object.
        if self.app.shot_count == 0:
            self.app.sg_lookup_map = {}

        hiero_sequence = self._item.parentSequence()
        if hiero_sequence.guid() in self.app.sg_lookup_map:
            return self.app.sg_lookup_map[ hiero_sequence.guid() ]

        # sequence not found in cache, grab it from Shotgun
        sg = self.app.tank.shotgun
        filt = [
            ['project', 'is', self.app.context.project],
            ['code', 'is', hiero_sequence.name()],
        ]
        sequences = sg.find('Sequence', filt)
        if len(sequences) > 1:
            # can not handle multiple sequences with the same name
            raise StandardError("Multiple sequences named '%s' found" % hiero_sequence.name())

        if len(sequences) == 0:
            # create the sequence in shotgun
            data = {
                'code': hiero_sequence.name(),
                'project': self.app.context.project,
            }
            sg_seq = sg.create('Sequence', data)
            self.app.log_info("Created sequence in Shotgun: %s" % hiero_sequence.name())
        else:
            sg_seq = sequences[0]

        # cache the results
        self.app.sg_lookup_map[hiero_sequence.guid()] = sg_seq
        return sg_seq

    def _create_and_return_sg_shot(self, sg_sequence):
        """
        Checks for a shot in shotgun for the current object.
        Creates on if it doesn't exist.

        :returns: A shotgun entity dictionary
        """
        # grab shot from Shotgun
        sg = self.app.tank.shotgun
        filt = [
            ['project', 'is', self.app.context.project],
            ['sg_sequence', 'is', sg_sequence],
            ['code', 'is', self._item.name()],
        ]
        shots = sg.find('Shot', filt)
        if len(shots) > 1:
            # can not handle multiple shots with the same name
            raise StandardError("Multiple shots named '%s' found", self._item.name())
        if len(shots) == 0:
            # create shot in shotgun
            data = {
                'code': self._item.name(),
                'sg_sequence': sg_sequence,
                'project': self.app.context.project,
            }
            shot = sg.create('Shot', data)
        else:
            shot = shots[0]

        return shot

    def _upload_poster_frame(self, sg_entity, source):
        """
        Updates the thumbnail for an entity in Shotgun
        """
        sg = self.app.tank.shotgun
        thumbdir = tempfile.mkdtemp(prefix='hiero_process_shot')
        try:
            path = "%s.png" % os.path.join(thumbdir, source.name())
            poster = source.posterFrame()
            thumb_qimage = source.thumbnail(poster)
            # scale it down to 600px wide
            thumb_qimage_scaled = thumb_qimage.scaledToWidth(600, QtCore.Qt.SmoothTransformation)
            # scale thumbnail here...
            thumb_qimage_scaled.save(path)
            self.app.log_debug("Uploading thumbnail for %s %s..." % (sg_entity['type'], sg_entity['id']))
            sg.upload_thumbnail(sg_entity['type'], sg_entity['id'], path)
        except Exception:
            self.app.log_info("Thumbnail for %s was not refreshed in Shotgun." % source)

            tb = traceback.format_exc()
            self.app.log_debug(tb)
        finally:
            shutil.rmtree(thumbdir)


class ShotgunShotUpdaterPreset(ShotgunHieroObjectBase, hiero.core.TaskPresetBase):
    """
    Settings preset
    """
    def __init__(self, name, properties):
        hiero.core.TaskPresetBase.__init__(self, ShotgunShotUpdater, name)
        self.properties().update(properties)

    def supportedItems(self):
        return hiero.core.TaskPresetBase.kAllItems
