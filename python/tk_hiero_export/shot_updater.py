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

class ShotgunShotUpdater(ShotgunHieroObjectBase, FnShotExporter.ShotTask):
    """
    Ensures that Shots and Sequences exist in Shotgun
    """
    def __init__(self, initDict):
        FnShotExporter.ShotTask.__init__(self, initDict)

    def taskStep(self):
        """
        Execution payload.
        """
        # execute base class
        FnShotExporter.ShotTask.taskStep(self)

        # call the preprocess hook to get extra values
        if self.app.first_shot:
            self.app.preprocess_data= {}
        sg_shot = self.app.execute_hook("hook_get_shot", task=self, item=self._item, data=self.app.preprocess_data)

        # clean up the dict
        shot_id = sg_shot['id']
        del sg_shot['id']
        shot_type = sg_shot['type']
        del sg_shot['type']

        # update the frame range
        start, end = self.outputRange(ignoreHandles=False, ignoreRetimes=False, clampToSource=True)
        sg_shot["sg_cut_duration"] = end - start + 1
        sg_shot["sg_cut_in"] = start
        sg_shot["sg_cut_out"] = end

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
        if len(self._item.tags()) == 0:
            default_template = self.parent.get_setting('default_task_template')
            if default_template:
                template = self.parent.tank.shotgun.find_one('TaskTemplate', [['entity_type', 'is', shot_type],
                                                                              ['code', 'is', default_template]])

        if template:
            sg_shot['task_template'] = template

        # commit the changes and update the thumbnail
        self.app.log_debug("Updating info for %s %s: %s" % (shot_type, shot_id, str(sg_shot)))
        self.app.tank.shotgun.update(shot_type, shot_id, sg_shot)

        # create the directory structure
        self.app.log_debug("Creating file system structure for %s %s..." % (shot_type, shot_id))
        self.app.tank.create_filesystem_structure(shot_type, [shot_id])

        # return without error
        self.app.log_info("Updated %s %s" % (shot_type, self.shotName()))

        # no longer the first shot
        self.app.first_shot = False

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


