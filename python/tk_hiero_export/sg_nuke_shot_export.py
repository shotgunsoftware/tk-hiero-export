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
import json

import hiero.core
from hiero.core import nuke
from hiero.exporters import FnNukeShotExporter
from hiero.exporters import FnNukeShotExporterUI

import tank
from tank import TankError
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
        self._tk_version_number = None

    def taskStep(self):
        """
        Run Task
        """
        if self._resolved_export_path is None:
            self._resolved_export_path = self.resolvedExportPath()
            self._tk_version_number = self._formatTkVersionString(self.versionString())
        return FnNukeShotExporter.NukeShotExporter.taskStep(self)

    def finishTask(self):
        """
        Finish Task
        """
        # run base class implementation
        FnNukeShotExporter.NukeShotExporter.finishTask(self)

        # register publish
        #

        # get context we're publishing to
        ctx = self.app.tank.context_from_path(self._resolved_export_path)

        # get the type of file we're publishing from multi-publish
        published_file_type = None
        multi_publish_settings = tank.platform.find_app_settings('tk-nuke', 'tk-multi-publish', self.app.tank, ctx)
        if multi_publish_settings:
            try:
                published_file_type = multi_publish_settings[0]['settings'].get('primary_tank_type')
            except:
                pass
        if not published_file_type:
            self.app.log_error("No 'primary_tank_type' defined in tk-nuke:tk-multi-publish for "
                               "context %s! This is used to determine the published file type "
                               "value when publishing Nuke scripts during the export process. "
                               "Continuing but this value will be blank on the PublishedFile "
                               "record" % ctx)

        args = {
            "tk": self.app.tank,
            "context": ctx, 
            "path": self._resolved_export_path,
            "name": os.path.basename(self._resolved_export_path),
            "version_number": int(self._tk_version_number),
            "published_file_type": published_file_type,  
        }
                
        self.app.log_debug("Register publish in shotgun: %s" % str(args))
        sg_publish = tank.util.register_publish(**args)

        # upload thumbnail for sequence
        try:
            self._upload_poster_frame(sg_publish, self._project.sequences()[0])
        except IndexError:
            self.app.log_warning("Couldn't find sequence to upload thumbnail from")

    def _get_write_node_settings(self):
        """
        Return write node settings from the tk-nuke-writenode app for the context
        of the published nuke script.
        """
        ctx = self.app.tank.context_from_path(self._resolved_export_path)
        app_settings_list = tank.platform.find_app_settings('tk-nuke', 'tk-nuke-writenode', self.app.tank, ctx)

        # no settings found for app!
        if len(app_settings_list) == 0:
            self.app.log_error("Could not find Shotgun Nuke write node settings. "
                               "Check your tk-nuke-writenode config. No write "
                               "node will be added.")
            return           
        elif len(app_settings_list) > 1:
            self.app.log_error("More than one set of tk-nuke-writenode app settings "
                               "was returned. Don't know which one to use so no "
                               "write node will be added.")  
            return          

        # a single app setting dict exists, extract the settings
        app_settings = app_settings_list[0].get("settings")
        # extract the list of write node settings from the app settings
        write_node_settings = app_settings.get("write_nodes")

        return write_node_settings

    def _parse_write_node_settings(self, wn_settings):
        """
        Parse the write node settings and ensure that the settings are all
        valid. Raise a TankError if anything is missing or invalid. 
        Return a tuple of the valid relevant settings on success
        """
        name = wn_settings.get("name", "unknown")
        file_type = wn_settings.get("file_type")
        file_settings = wn_settings.get("settings", {})
        if not isinstance(file_settings, dict):
            raise TankError("Configuration Error: Write node contains invalid settings. "
                            "Settings must be a dictionary. Current config: %s" % wn_settings)

        render_template_name = wn_settings.get("render_template")
        if render_template_name is None:
            raise TankError("Configuration Error: Write node has no render_template: %s" % wn_settings)

        publish_template_name = wn_settings.get("publish_template")
        if publish_template_name is None:
            raise TankError("Configuration Error: Write node has no publish_template: %s" % wn_settings)

        return (name, render_template_name, publish_template_name, file_type, file_settings)


    def _beforeNukeScriptWrite(self, script):
        """
        Add HieroWriteTank Metadata Nodes for tk-nuke-writenode to use in order
        to create full Tk WriteNodes in the Nuke environment
        """
        tk_wn_settings = self._get_write_node_settings()

        metadata = []
        for wn_settings in tk_wn_settings:
            (name, 
             render_template_name, 
             publish_template_name, 
             file_type, 
             file_settings) = self._parse_write_node_settings(wn_settings)

            metadata = {
                'name': name,
                'render_template': render_template_name,
                'publish_template': publish_template_name,
                'file_type': file_type,
                'file_settings': json.dumps(file_settings).replace('"', '\\"')
            }

            node = nuke.MetadataNode(metadatavalues=metadata.items())
            node.setName('HieroWriteTank')

            self.app.log_debug("Created HieroWriteTank MetadataNode Node: %s" % node._knobValues)
            script.addNode(node)


class ShotgunNukeShotPreset(ShotgunHieroObjectBase, FnNukeShotExporter.NukeShotPreset):
    """
    Settings for the shotgun transcode step
    """
    
    def __init__(self, name, properties):
        FnNukeShotExporter.NukeShotPreset.__init__(self, name, properties)
        self._parentType = ShotgunNukeShotExporter
