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
import sys
import shutil

from PySide import QtGui
from PySide import QtCore

import hiero.core
from hiero.exporters import FnShotExporter
from hiero.exporters import FnShotProcessor
from hiero.exporters import FnNukeShotExporter
import tank
from tank import TankError

from hiero.exporters import FnNukeShotExporterUI

from .base import ShotgunHieroObjectBase

class ShotgunNukeShotExporterUI(FnNukeShotExporterUI.NukeShotExporterUI):
    """
    Custom Preferences UI for the shotgun nuke shot exporter
    """
    
    def __init__(self, preset):
        FnNukeShotExporterUI.NukeShotExporterUI.__init__(self, preset)
        self._displayName = "Shotgun Nuke Project File"
        self._taskType = ShotgunNukeShotExporter


class ShotgunNukeShotExporter(ShotgunHieroObjectBase, FnNukeShotExporter.NukeShotExporter):
    """
    Create Transcode object and send to Shotgun
    """
    
    def __init__(self, initDict):
        """
        Constructor
        """
        FnNukeShotExporter.NukeShotExporter.__init__(self, initDict)
        self._resolved_export_path = None
        self._thumbnail = None
        self._tk_version_number = None

    def taskStep(self):
        """
        Run Task
        """
        if self._resolved_export_path is None:
            self._resolved_export_path = self.resolvedExportPath()
            self._tk_version_number = self._formatTkVersionString(self.versionString())
            self.app.log_info("TK_VERSION: %s" % self._tk_version_number)
            # access settings for writenode app from shot env and use those settings
            # other_settings = tank.platform.find_app_settings(self._app.engine.name, self._app.name, self._app.tank, context)
            source = self._item.source()
            self._thumbnail = source.thumbnail(source.posterFrame())
        self.app.log_info('TASKSTEP: %s' % self)
        return FnNukeShotExporter.NukeShotExporter.taskStep(self)

    def finishTask(self):
        """
        Finish Task
        """
        # run base class implementation
        FnNukeShotExporter.NukeShotExporter.finishTask(self)

        sg_current_user = tank.util.get_current_user(self.app.tank)

        # register publish
         
        # context we're publishing to
        ctx = self.app.tank.context_from_path(self._resolved_export_path)

        args = {
            "tk": self.app.tank,
            "context": ctx, 
            "path": self._resolved_export_path,
            "name": os.path.basename(self._resolved_export_path),
            "version_number": int(self._tk_version_number),
            "published_file_type": 'Nuke Script',  # comes from config - try for nuke
        }
                
        # register publish
        self.app.log_debug("Register publish in shotgun: %s" % str(args))
        sg_data = tank.util.register_publish(**args)

        # upload thumbnail for sequence
        try:
            self._upload_poster_frame(sg_data, self._project.sequences()[0])
        except IndexError:
            self.app.log_warning("Couldn't find sequence to upload thumbnail from")


    def _beforeNukeScriptWrite(self, script):
        """Remove existing WriteNodes and replace with Tk WriteNodes
        """
        pass
        return

        self.app.log_debug('SCRIPT: %s' % script)
        self.app.log_debug('SCRIPT dir(): %s' % dir(script))
        
        # find the node to use from the config
        tk_write_node_setting = self.app.get_setting("nuke_write_node_setting")
        if not tk_write_node_setting:
            self.app.log_debug("No Shotgun Nuke write node setting defined in "
                               "the config. No write node will be added.")
            return

        # we will need the write node app to create Shotgun write nodes for the
        # nuke script.
        write_node_app = self.app.engine.apps.get("tk-nuke-writenode")
        if not write_node_app:
            raise TankError("Unable to create write node without tk-nuke-writenode app!")
        tk_write_node = write_node_app.create_write_node(tk_write_node_setting)
        script.add_node(tk_write_node)




class ShotgunNukeShotPreset(ShotgunHieroObjectBase, FnNukeShotExporter.NukeShotPreset):
    """
    Settings for the shotgun transcode step
    """
    
    def __init__(self, name, properties):
        FnNukeShotExporter.NukeShotPreset.__init__(self, name, properties)
        self._parentType = ShotgunNukeShotExporter
