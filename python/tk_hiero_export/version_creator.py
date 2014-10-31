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
import ast
import sys
import shutil
import tempfile

from PySide import QtGui
from PySide import QtCore

from hiero.exporters import FnExternalRender
from hiero.exporters import FnTranscodeExporter
from hiero.exporters import FnTranscodeExporterUI

import hiero
from hiero import core
from hiero.core import *

import tank
import sgtk.util

from .base import ShotgunHieroObjectBase
from .collating_exporter import CollatingExporter, CollatedShotPreset


class ShotgunTranscodeExporterUI(ShotgunHieroObjectBase, FnTranscodeExporterUI.TranscodeExporterUI):
    """
    Custom Preferences UI for the shotgun transcoder

    Embeds the UI for the std transcoder UI.
    """
    def __init__(self, preset):
        FnTranscodeExporterUI.TranscodeExporterUI.__init__(self, preset)
        self._displayName = "Shotgun Transcode Images"
        self._taskType = ShotgunTranscodeExporter

    def create_version_changed(self, state):
        create_version = (state == QtCore.Qt.Checked)
        self._preset._properties["create_version"] = create_version

    def populateUI(self, widget, exportTemplate):
        # create a layout with custom top and bottom widgets
        layout = QtGui.QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(9)

        top = QtGui.QWidget()
        middle = QtGui.QWidget()
        bottom = QtGui.QWidget()
        layout.addWidget(top)
        layout.addWidget(middle)
        layout.addWidget(bottom)

        top_layout = QtGui.QVBoxLayout(top)
        top_layout.setContentsMargins(9, 0, 9, 0)
        create_version_checkbox = QtGui.QCheckBox("Create Shotgun Version", widget)
        create_version_checkbox.setToolTip(
            "Create a Version in Shotgun for this transcode.\n\n"
            "If the output format is not a quicktime, then\n"
            "a quicktime will be created.  The quicktime will\n"
            "be uploaded to Shotgun as Screening Room media."
            )
        create_version_checkbox.setCheckState(QtCore.Qt.Checked)
        if not self._preset._properties.get("create_version", True):
            create_version_checkbox.setCheckState(QtCore.Qt.Unchecked)
        create_version_checkbox.stateChanged.connect(self.create_version_changed)
        top_layout.addWidget(create_version_checkbox)

        # populate the middle with the standard layout
        FnTranscodeExporterUI.TranscodeExporterUI.populateUI(self, middle, exportTemplate)

        layout = QtGui.QVBoxLayout(top)


class ShotgunTranscodeExporter(ShotgunHieroObjectBase, FnTranscodeExporter.TranscodeExporter, CollatingExporter):
    """
    Create Transcode object and send to Shotgun
    """
    def __init__(self, initDict):
        """ Constructor """
        FnTranscodeExporter.TranscodeExporter.__init__(self, initDict)
        CollatingExporter.__init__(self)
        self._resolved_export_path = None
        self._sequence_name = None
        self._shot_name = None
        self._thumbnail = None
        self._quicktime_path = None
        self._temp_quicktime = None

    def buildScript(self):
        """
        Override the default buildScript functionality to also output a temp movie
        file if needed for uploading to Shotgun
        """
        # Build the usual script
        FnTranscodeExporter.TranscodeExporter.buildScript(self)

        # If we are not creating a version then we do not need the extra node
        if not self._preset.properties()['create_version']:
            return

        if self._preset.properties()['file_type'] in ["mov", "ffmpeg"]:
            # already outputting a mov file, use that for upload
            self._quicktime_path = self.resolvedExportPath()
            self._temp_quicktime = False
            return

        self._quicktime_path = os.path.join(tempfile.mkdtemp(), 'preview.mov')
        self._temp_quicktime = True
        nodeName = "Shotgun Screening Room Media"

        framerate = None
        if self._sequence:
            framerate = self._sequence.framerate()
        if self._clip.framerate().isValid():
            framerate = self._clip.framerate()

        preset = FnTranscodeExporter.TranscodePreset("Qt Write", self._preset.properties())

        # insert the write node to generate the quicktime
        file_type, properties = self.app.execute_hook("hook_get_quicktime_settings", for_shotgun=True)
        preset.properties().update({
            "file_type": file_type,
            file_type: properties,
        })

        mov_write_node = FnExternalRender.createWriteNode(self._quicktime_path,
            preset, nodeName, framerate=framerate, projectsettings=self._projectSettings)

        self._script.addNode(mov_write_node)

    def sequenceName(self):
        """override default sequenceName() to handle collated shots"""
        try:
            if self.isCollated():
                return self._parentSequence.name()
            else:
                return FnTranscodeExporter.TranscodeExporter.sequenceName(self)
        except AttributeError:
            return FnTranscodeExporter.TranscodeExporter.sequenceName(self)

    def writeAudio(self):
        """
        Overridden method to allow proper timings for audio export
        """
        item = self._item
        if item.guid() in self._collatedItemsMap:
            item = self._collatedItemsMap[item.guid()]

        # Call parent method with swapped items in order to get proper timings
        original = self._item
        self._item = item
        
        result = FnTranscodeExporter.TranscodeExporter.writeAudio(self)

        self._item = original

        return result

    def startTask(self):
        """ Run Task """
        if self._resolved_export_path is None:
            self._resolved_export_path = self.resolvedExportPath()
            self._tk_version = self._formatTkVersionString(self.versionString())
            self._sequence_name = self.sequenceName()

            # convert slashes to native os style..
            self._resolved_export_path = self._resolved_export_path.replace("/", os.path.sep)

        # call the get_shot hook
        ########################
        if self.app.shot_count == 0:
            self.app.preprocess_data = {}

        # associate publishes with correct shot, which will be the hero item
        # if we are collating
        if self.isCollated() and not self.isHero():
            item = self.heroItem()
        else:
            item = self._item

        # store the shot for use in finishTask
        self._sg_shot = self.app.execute_hook("hook_get_shot", task=self, item=item, data=self.app.preprocess_data)

        # populate the data dictionary for our Version while the item is still valid
        ##############################
        # see if we get a task to use
        self._sg_task = None
        try:
            task_filter = self.app.get_setting("default_task_filter", "[]")
            task_filter = ast.literal_eval(task_filter)
            task_filter.append(["entity", "is", self._sg_shot])
            tasks = self.app.shotgun.find("Task", task_filter)
            if len(tasks) == 1:
                self._sg_task = tasks[0]
        except ValueError:
            # continue without task
            setting = self.app.get_setting("default_task_filter", "[]")
            self.app.log_error("Invalid value for 'default_task_filter': %s" % setting)

        if self._preset.properties()['create_version']:
            # lookup current login
            sg_current_user = tank.util.get_current_user(self.app.tank)

            file_name = os.path.basename(self._resolved_export_path)
            file_name = os.path.splitext(file_name)[0]
            file_name = file_name.capitalize()

            self._version_data = {
                "user": sg_current_user,
                "created_by": sg_current_user,
                "entity": self._sg_shot,
                "project": self.app.context.project,
                "sg_path_to_movie": self._resolved_export_path,
                "code": file_name,
            }

            if self._sg_task is not None:
                self._version_data["sg_task"] = self._sg_task

            # call the update version hook to allow for customization
            self.app.execute_hook(
                "hook_update_version_data",
                version_data=self._version_data,
                task=self)

        # call the publish data hook to allow for publish customization
        self._extra_publish_data = self.app.execute_hook(
            "hook_get_extra_publish_data", task=self)

        # figure out the thumbnail frame
        ##########################
        source = self._item.source()
        self._thumbnail = source.thumbnail(source.posterFrame())

        return FnTranscodeExporter.TranscodeExporter.startTask(self)

    def finishTask(self):
        """ Finish Task """
        # run base class implementation
        FnTranscodeExporter.TranscodeExporter.finishTask(self)

        # create publish
        ################
        # by using entity instead of export path to get context, this ensures
        # collated plates get linked to the hero shot
        ctx = self.app.tank.context_from_entity('Shot', self._sg_shot['id'])
        published_file_type = self.app.get_setting('plate_published_file_type')

        args = {
            "tk": self.app.tank,
            "context": ctx,
            "path": self._resolved_export_path,
            "name": os.path.basename(self._resolved_export_path),
            "version_number": int(self._tk_version),
            "published_file_type": published_file_type,
        }

        if self._sg_task is not None:
            args["task"] = self._sg_task

        published_file_entity_type = sgtk.util.get_published_file_entity_type(self.app.sgtk)

        # register publish
        self.app.log_debug("Register publish in shotgun: %s" % str(args))
        pub_data = tank.util.register_publish(**args)
        if self._extra_publish_data is not None:
            self.app.log_debug("Updating Shotgun %s %s" % (published_file_entity_type, str(self._extra_publish_data)))
            self.app.shotgun.update(pub_data["type"], pub_data["id"], self._extra_publish_data)

        # upload thumbnail for publish
        self._upload_thumbnail_to_sg(pub_data, self._thumbnail)

        # create version
        ################
        if self._preset.properties()['create_version']:
            if published_file_entity_type == "PublishedFile":
                self._version_data["published_files"] = [pub_data]
            else:  # == "TankPublishedFile
                self._version_data["tank_published_file"] = pub_data

            self.app.log_debug("Creating Shotgun Version %s" % str(self._version_data))
            vers = self.app.shotgun.create("Version", self._version_data)

            if os.path.exists(self._quicktime_path):
                self.app.log_debug("Uploading quicktime to Shotgun... (%s)" % self._quicktime_path)
                self.app.shotgun.upload("Version", vers["id"], self._quicktime_path, "sg_uploaded_movie")
                if self._temp_quicktime:
                    shutil.rmtree(os.path.dirname(self._quicktime_path))


class ShotgunTranscodePreset(ShotgunHieroObjectBase, FnTranscodeExporter.TranscodePreset, CollatedShotPreset):
    """ Settings for the shotgun transcode step """
    def __init__(self, name, properties):
        FnTranscodeExporter.TranscodePreset.__init__(self, name, properties)
        self._parentType = ShotgunTranscodeExporter
        CollatedShotPreset.__init__(self, self.properties())

        # set default values
        self._properties["create_version"] = True

        self.properties().update(properties)
