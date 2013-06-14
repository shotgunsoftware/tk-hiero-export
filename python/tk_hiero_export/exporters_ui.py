"""
Copyright (c) 2013 Shotgun Software, Inc
----------------------------------------------------
"""
from PySide import QtGui
from PySide import QtCore

import hiero.ui
import hiero.core
from hiero.exporters import FnTranscodeExporterUI

from .exporters import ShotgunTranscodeExporter


class ShotgunTranscodeExporterUI(FnTranscodeExporterUI.TranscodeExporterUI):
    def __init__(self, preset):
        FnTranscodeExporterUI.TranscodeExporterUI.__init__(self, preset)
        self._displayName = "Shotgun Transcode Images"
        self._taskType = ShotgunTranscodeExporter

    def populateUI(self, widget, exportTemplate):
        # create a layout with custom top and bottom widgets
        layout = QtGui.QVBoxLayout(widget)
        top = QtGui.QWidget()
        middle = QtGui.QWidget()
        bottom = QtGui.QWidget()
        layout.addWidget(top)
        layout.addWidget(middle)
        layout.addWidget(bottom)

        # populate the middle with the standard layout
        FnTranscodeExporterUI.TranscodeExporterUI.populateUI(self, middle, exportTemplate)

        layout = QtGui.QVBoxLayout(top)
