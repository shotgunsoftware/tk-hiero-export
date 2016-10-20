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

        The values correspond to the exported version created on disk.
        """

        (head_in, tail_out) = self.collatedOutputRange(clampToSource=False)

        handles = self._cutHandles if self._cutHandles is not None else 0
        in_handle = handles
        out_handle = handles

        source_in = int(self._item.sourceIn())
        source_out = int(self._item.sourceOut())

        duration = source_out - source_in

        if source_in < in_handle:
            # the source in point is within the specified handles. this is
            # handled differently in different versions of hiero. in versions
            # that will write black frames, the head in/out returned above will
            # encompass the full in/out
            if self._has_nuke_backend():
                # no black frames written, the in/out should be correct.
                # but the start handle is limited by the in value
                in_handle = source_in

        # "cut_length" is a boolean set on the updater by the shot processor.
        # it signifies whether the transcode task will write the cut length
        # to disk (True) or if it will write the full source to disk (False)
        if self.is_cut_length_export():
            cut_in = in_handle
            cut_out = in_handle + duration
        else:
            # don't account for custom start frame (head/tail will be full
            # source in/out)
            cut_in = source_in
            cut_out = source_out

        edit_in = self._item.timelineIn()
        edit_out = self._item.timelineOut()

        if self._startFrame is not None:
            # a custom start frame was specified
            cut_in += self._startFrame
            cut_out += self._startFrame

        cut_duration = cut_out - cut_in + 1
        edit_duration = edit_out - edit_in + 1

        if cut_duration != edit_duration:
            self.app.log_warning(
                "It looks like the shot %s has a retime applied. SG cuts do "
                "not support retimes." % (self.clipName(),)
            )

        working_duration = tail_out - head_in + 1

        if not self._has_nuke_backend() and self.isCollated():
            # undo the offset that is automatically added when collating.
            # this is only required in older versions of hiero
            head_in -= self.HEAD_ROOM_OFFSET
            tail_out -= self.HEAD_ROOM_OFFSET

        # return the computed cut information
        return {
            "in_handle": in_handle,
            "out_handle": out_handle,
            "cut_item_in": cut_in,
            "cut_item_out": cut_out,
            "cut_item_duration": cut_duration,
            "edit_in": edit_in,
            "edit_out": edit_out,
            "edit_duration": edit_duration,
            "head_in": head_in,
            "tail_out": tail_out,
            "working_duration": working_duration,
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

        # The cut order may have been set by the processor. Otherwise keep old behavior.
        cut_order = self.app.shot_count + 1
        if self._cut_order:
            cut_order = self._cut_order

        # update the frame range
        sg_shot["sg_cut_order"] = cut_order

        # get cut info
        cut_info = self.get_cut_item_data()

        in_handle = cut_info["in_handle"]
        out_handle = cut_info["out_handle"]
        head_in = cut_info["head_in"]
        tail_out = cut_info["tail_out"]
        cut_in = cut_info["cut_item_in"]
        cut_out = cut_info["cut_item_out"]

        self.app.log_debug("Head/Tail from Hiero: %s, %s" % (head_in, tail_out))

        if self.isCollated():

            # The collate logic gives us fairly reasonable values for head/tail.
            # We can deduce the cut in/out from those by factoring the in/out
            # handles.
            cut_in = head_in + in_handle
            cut_out = tail_out - out_handle

            if self.is_cut_length_export():
                # nothing to do here. the default calculation above is enough.
                self.app.log_debug("Exporting... collated, cut length.")

                # Log cut length collate metric
                try:
                    self.app.log_metric("Collate/Cut Length", log_version=True)
                except:
                    # ingore any errors. ex: metrics logging not supported
                    pass

            else:
                self.app.log_debug("Exporting... collated, clip length.")

                # NOTE: Hiero crashes when trying to collate with a
                # custom start frame. so this will only work for source start
                # frame.

                # the head/in out values should be the first and last frames of
                # the source, but they're not. ensure head/tail match the entire
                # clip (clip length export)
                head_in = 0
                tail_out = self._clip.duration() - 1

                if self._startFrame is not None:
                    # account for a custom start frame if/when collate works on
                    # custom start frame.
                    head_in += self._startFrame
                    tail_out += self._startFrame

                # Log clip length collate metric
                try:
                    self.app.log_metric("Collate/Clip Length", log_version=True)
                except:
                    # ingore any errors. ex: metrics logging not supported
                    pass

        else:
            # regular export. we can deduce the proper values based on the
            # values we have

            if self.is_cut_length_export():
                self.app.log_debug("Exporting... cut length.")
                # cut length is the typical export. we can fall back to the
                # legacy calculation which seems to be valid.
                cut_in = head_in + in_handle
                cut_out = tail_out - out_handle
            else:
                # the cut in/out should already be correct here. just log
                self.app.log_debug("Exporting... clip length.")

        # calculate the duration values now that the ins/outs are set
        cut_duration = cut_out - cut_in + 1
        working_duration = tail_out - head_in + 1

        # update the frame range
        sg_shot["sg_head_in"] = head_in
        sg_shot["sg_cut_in"] = cut_in
        sg_shot["sg_cut_out"] = cut_out
        sg_shot["sg_tail_out"] = tail_out
        sg_shot["sg_cut_duration"] = cut_duration
        sg_shot["sg_working_duration"] = working_duration

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

    def is_cut_length_export(self):
        """
        Returns ``True`` if this task has the "Cut Length" option checked.

        This is set by the shot processor.
        """
        return hasattr(self, "_cut_length") and self._cut_length


class ShotgunShotUpdaterPreset(ShotgunHieroObjectBase, hiero.core.TaskPresetBase):
    """
    Settings preset
    """
    def __init__(self, name, properties):
        hiero.core.TaskPresetBase.__init__(self, ShotgunShotUpdater, name)
        self.properties().update(properties)

    def supportedItems(self):
        return hiero.core.TaskPresetBase.kAllItems
