# Copyright (c) 2013 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

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
        self._cut_order = None

    def get_cut_item_data(self):
        """
        Return some computed values for use when creating cut items.
        """

        # this is the head in/out of the source clip. For the cut item in SG,
        # we need to translate this to the exported version's frames
        (head_in, tail_out) = self.collatedOutputRange(clampToSource=False)

        # the handles as specified in the export UI
        handles = self._cutHandles if self._cutHandles is not None else 0

        # the in/out of the exported version. assume start at 0, then calculate
        # based on the handles and the length of the clip
        cut_in = handles
        cut_out = tail_out - head_in - handles

        # determine the edit in/out which includes the sequence start
        edit_in = self._item.timelineIn()
        edit_out = self._item.timelineOut()

        if self._startFrame:
            # a custom start frame was specified
            edit_in += self._startFrame
            edit_out += self._startFrame
        else:
            # use the start time from the hiero sequence
            seq = self._item.sequence()
            edit_in += seq.timecodeStart()
            edit_out += seq.timecodeStart()

        # return the computed cut information
        return {
            "cut_item_in": cut_in,
            "cut_item_out": cut_out,
            "cut_item_duration": cut_out - cut_in + 1,
            "edit_in": edit_in,
            "edit_out": edit_out,
        }

    def taskStep(self):
        """
        Execution payload.
        """
        # Only process actual shots... so uncollated items and hero collated items
        if self.isCollated() and not self.isHero():
            return False

        # execute base class
        FnShotExporter.ShotTask.taskStep(self)

        # call the preprocess hook to get extra values
        if self.app.shot_count == 0:
            self.app.preprocess_data = {}
        sg_shot = self.app.execute_hook("hook_get_shot", task=self, item=self._item, data=self.app.preprocess_data)

        # clean up the dict
        shot_id = sg_shot['id']
        del sg_shot['id']
        shot_type = sg_shot['type']
        del sg_shot['type']

        # get cut info.
        # NOTE: this cut data pre-dates the cut support with SG 6.3.13 and is
        # specific to the Shot entity. This information may not match the
        # information found in the Shot's CutItems.
        handles = self._cutHandles if self._cutHandles is not None else 0
        (head_in, tail_out) = self.collatedOutputRange(clampToSource=False)
        cut_in = head_in + handles
        cut_out = tail_out - handles

        # The cut order may have been set by the processor. Otherwise keep old behavior.
        cut_order = self.app.shot_count + 1
        if self._cut_order:
            cut_order = self._cut_order

        # update the frame range
        sg_shot["sg_cut_order"] = cut_order
        sg_shot["sg_head_in"] = head_in
        sg_shot["sg_cut_in"] = cut_in
        sg_shot["sg_cut_out"] = cut_out
        sg_shot["sg_tail_out"] = tail_out
        sg_shot["sg_cut_duration"] = cut_out - cut_in + 1
        sg_shot["sg_working_duration"] = tail_out - head_in + 1

        # get status from the hiero tags
        status = None
        status_map = dict(self._preset.properties()["sg_status_hiero_tags"])
        for tag in self._item.tags():
            if tag.name() in status_map:
                status = status_map[tag.name()]
                break
        if status:
            sg_shot['sg_status_list'] = status

        # get task template from the tags
        template = None
        template_map = dict(self._preset.properties()["task_template_map"])
        for tag in self._item.tags():
            if tag.name() in template_map:
                template = self.app.tank.shotgun.find_one('TaskTemplate',
                                                          [['entity_type', 'is', shot_type],
                                                           ['code', 'is', template_map[tag.name()]]])
                break

        # if there are no associated, assign default template...
        if template is None:
            default_template = self.app.get_setting('default_task_template')
            if default_template:
                template = self.app.tank.shotgun.find_one('TaskTemplate',
                    [['entity_type', 'is', shot_type], ['code', 'is', default_template]])

        if template is not None:
            sg_shot['task_template'] = template

        # commit the changes and update the thumbnail
        self.app.log_debug("Updating info for %s %s: %s" % (shot_type, shot_id, str(sg_shot)))
        self.app.tank.shotgun.update(shot_type, shot_id, sg_shot)

        # create the directory structure
        self.app.log_debug("Creating file system structure for %s %s..." % (shot_type, shot_id))
        self.app.tank.create_filesystem_structure(shot_type, [shot_id])

        # return without error
        self.app.log_info("Updated %s %s" % (shot_type, self.shotName()))

        # keep shot count
        self.app.shot_count += 1

        cut = None
        # create the CutItem with the data populated by the shot processor
        if hasattr(self, "_cut_item_data"):
            cut_item_data = self._cut_item_data
            cut_item = self.app.tank.shotgun.create("CutItem", cut_item_data)
            self.app.log_info("Created CutItem in Shotgun: %s" % (cut_item,))

            # update the object's cut item data to include the new info
            self._cut_item_data.update(cut_item)

            cut = cut_item["cut"]

        # see if this task has been designated to update the Cut thumbnail
        if cut and hasattr(self, "_create_cut_thumbnail"):
            hiero_sequence = self._item.sequence()
            try:
                # see if we can find a poster frame for the sequence
                thumbnail = hiero_sequence.thumbnail(hiero_sequence.posterFrame())
            except Exception:
                self.app.log_debug("No thumbnail found for the 'Cut'.")
                pass
            else:
                # found one, uplaod to sg for the cut
                self._upload_thumbnail_to_sg(cut, thumbnail)

        # return false to indicate success
        return False


class ShotgunShotUpdaterPreset(ShotgunHieroObjectBase, hiero.core.TaskPresetBase):
    """
    Settings preset
    """
    def __init__(self, name, properties):
        hiero.core.TaskPresetBase.__init__(self, ShotgunShotUpdater, name)
        self.properties().update(properties)

    def supportedItems(self):
        return hiero.core.TaskPresetBase.kAllItems
