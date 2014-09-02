# Copyright (c) 2013 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

import re
import os
import sys
import ast

from PySide import QtGui
from PySide import QtCore

from hiero.exporters import FnAudioExportTask
from hiero.exporters import FnAudioExportUI

import tank
from .base import ShotgunHieroObjectBase

class ShotgunAudioExporterUI(ShotgunHieroObjectBase, FnAudioExportUI.AudioExportUI):
    """
    Custom Preferences UI for the shotgun audio exporter
    """
    def __init__(self, preset):
        FnAudioExportUI.AudioExportUI.__init__(self, preset)
        self._displayName = "Shotgun Audio Export"
        self._taskType = ShotgunAudioExporter

    def populateUI(self, widget, exportTemplate):
        FnAudioExportUI.AudioExportUI.populateUI(self, widget, exportTemplate)

class ShotgunAudioExporter(ShotgunHieroObjectBase, FnAudioExportTask.AudioExportTask):
    """
    Create Audio object and send to Shotgun
    """
    def __init__(self, initDict):
        """
        Constructor
        """
        FnAudioExportTask.AudioExportTask.__init__(self, initDict)


class ShotgunAudioPreset(ShotgunHieroObjectBase, FnAudioExportTask.AudioExportPreset):
    """
    Settings for the shotgun audio export step
    """

    def __init__(self, name, properties):
        FnAudioExportTask.AudioExportPreset.__init__(self, name, properties)
        self._parentType = ShotgunAudioExporter
        
