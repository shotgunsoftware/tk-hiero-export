"""
Copyright (c) 2013 Shotgun Software, Inc
----------------------------------------------------
"""
import os
import sys
import shutil

from PySide import QtGui
from PySide import QtCore

import hiero.core
from hiero.exporters import FnShotExporter
from hiero.exporters import FnShotProcessor
from hiero.exporters import FnTranscodeExporter
import tank


class ShotgunExporterBase(object):
    """Base class to make the Hiero classes app aware."""
    _app = None

    @classmethod
    def setApp(cls, app):
        cls._app = app

    @classmethod
    def app(cls):
        return cls._app


class ShotgunShotProcessor(ShotgunExporterBase, FnShotProcessor.ShotProcessor):
    """Add extra UI and hook functionality to the built in Shot processor."""
    def __init__(self, preset, submission=None, synchronous=False):
        FnShotProcessor.ShotProcessor.__init__(self, preset, submission, synchronous)
        self._shotCreatePreset = None

    def displayName(self):
        return "Process as Shotgun Shots"

    def toolTip(self):
        return "Process as Shots generates output on a per shot basis and logs it in Shotgun."

    def startProcessing(self, exportItems):
        # Use tank to set the project root
        projectRoot = self.app().tank.project_path
        self.app().engine.log_debug("Setting projectRoot to '%s'" % projectRoot)
        self._exportTemplate.setExportRootPath(projectRoot)

        # add a top level task to manage shotgun shots
        exportTemplate = self._exportTemplate.flatten()
        properties = self._preset.properties().get('shotgunShotCreateProperties', {})
        exportTemplate.insert(0, (".shotgun", ShotgunShotUpdaterPreset(".shotgun", properties)))
        self._exportTemplate.restore(exportTemplate)

        # tag app as first shot
        self.app().first_shot = True

        # do the normal processing
        FnShotProcessor.ShotProcessor.startProcessing(self, exportItems)

        # get rid of our placeholder
        exportTemplate.pop()
        self._exportTemplate.restore(exportTemplate)

    def populateUI(self, widget, exportItems, editMode=None):
        # create a layout with custom top and bottom widgets
        layout = QtGui.QVBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)

        default = QtGui.QWidget()
        shotgun = QtGui.QGroupBox("Shotgun")

        layout.addWidget(shotgun)
        layout.addWidget(default)

        layout = QtGui.QVBoxLayout(shotgun)

        above = QtGui.QWidget()
        layout.addWidget(above)

        # populate the middle with the standard layout
        FnShotProcessor.ShotProcessor.populateUI(self, default, exportItems, editMode)

        # and call the app hook to populate the shotgun ui
        properties = self._preset.properties().get('shotgunShotCreateProperties', {})
        self.app().execute_hook("hook_populate_shot_ui",
            widget=above, items=exportItems, properties=properties)


class ShotgunShotProcessorPreset(ShotgunExporterBase, FnShotProcessor.ShotProcessorPreset):
    """Add ability to configure preset properties via hooks."""
    def __init__(self, name, properties):
        FnShotProcessor.ShotProcessorPreset.__init__(self, name, properties)
        self._parentType = ShotgunShotProcessor

        # give hooks a chance to add properties to the preset
        default = self.properties()['shotgunShotCreateProperties'] = {}
        passed = properties.get('shotgunShotCreateProperties', {})
        self.app().execute_hook("hook_populate_shot_properties",
            default=default, passed=passed)


##### Shot updater task
###########################################################################
class ShotgunShotUpdater(ShotgunExporterBase, FnShotExporter.ShotTask):
    def __init__(self, initDict):
        FnShotExporter.ShotTask.__init__(self, initDict)

    def taskStep(self):
        FnShotExporter.ShotTask.taskStep(self)

        # hand shot processing off to a hook
        ret = self.app().execute_hook("hook_process_shot", task=self)

        # no longer the first shot
        self.app().first_shot = False

        return ret


class ShotgunShotUpdaterPreset(ShotgunExporterBase, hiero.core.TaskPresetBase):
    def __init__(self, name, properties):
        hiero.core.TaskPresetBase.__init__(self, ShotgunShotUpdater, name)
        self.properties().update(properties)

    def supportedItems(self):
        return hiero.core.TaskPresetBase.kAllItems


##### Wrapped transcoder
###########################################################################
class ShotgunTranscodeExporter(ShotgunExporterBase, FnTranscodeExporter.TranscodeExporter):
    def __init__(self, initDict):
        FnTranscodeExporter.TranscodeExporter.__init__(self, initDict)
        self._resolvedExportPath = None
        self._sequenceName = None
        self._shotName = None
        self._thumbnail = None

    def taskStep(self):
        if self._resolvedExportPath is None:
            self._resolvedExportPath = self.resolvedExportPath()
            self._shotName = self.shotName()
            self._sequenceName = self.sequenceName()

            source = self._item.source()
            self._thumbnail = source.thumbnail(source.posterFrame())

        return FnTranscodeExporter.TranscodeExporter.taskStep(self)

    def finishTask(self):
        FnTranscodeExporter.TranscodeExporter.finishTask(self)

        # once the task is finished call a task to handle the publish
        self.app().execute_hook("hook_publish_transcode",
            path=self._resolvedExportPath, sequence=self._sequenceName,
            shot=self._shotName, thumbnail=self._thumbnail)


class ShotgunTranscodePreset(ShotgunExporterBase, FnTranscodeExporter.TranscodePreset):
    def __init__(self, name, properties):
        FnTranscodeExporter.TranscodePreset.__init__(self, name, properties)
        self._parentType = ShotgunTranscodeExporter
