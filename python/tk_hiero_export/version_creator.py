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

from hiero.exporters import FnTranscodeExporterUI

from .base import ShotgunHieroObjectBase

class ShotgunTranscodeExporterUI(FnTranscodeExporterUI.TranscodeExporterUI):
    """
    Custom Preferences UI for the shotgun transcoder
    
    Embeds the UI for the std transcoder UI.
    """
    
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



class ShotgunTranscodeExporter(ShotgunHieroObjectBase, FnTranscodeExporter.TranscodeExporter):
    """
    Create Transcode object and send to Shotgun
    """
    
    def __init__(self, initDict):
        """
        Constructor
        """
        FnTranscodeExporter.TranscodeExporter.__init__(self, initDict)
        self._resolved_export_path = None
        self._sequence_name = None
        self._shot_name = None
        self._thumbnail = None

    def taskStep(self):
        """
        Run Task
        """
        if self._resolved_export_path is None:
            self._resolved_export_path = self.resolvedExportPath()
            self._shot_name = self.shotName()
            self._sequence_name = self.sequenceName()

            source = self._item.source()
            self._thumbnail = source.thumbnail(source.posterFrame())

        return FnTranscodeExporter.TranscodeExporter.taskStep(self)

    def finishTask(self):
        """
        Finish Task
        """
        
        # run base class implementation
        FnTranscodeExporter.TranscodeExporter.finishTask(self)

        sg = self.app.shotgun

        # lookup current login
        sg_current_user = tank.util.get_current_user(self.app.tank)

        # lookup sequence
        sg_sequence = sg.find_one("Sequence",
                                  [["project", "is", self.app.context.project], 
                                   ["code", "is", self._sequence_name]])
        sg_shot = None
        if sg_sequence:
            sg_shot = sg.find_one("Shot", [["sg_sequence", "is", sg_sequence], ["code", "is", self._shot_name]])
        
        # file name 
        file_name = os.path.basename(self._resolved_export_path)
        file_name = os.path.splitext(file_name)[0]
        file_name = file_name.capitalize()
        
        # lookup seq/shot
        data = {
            "user": sg_current_user,
            "created_by": sg_current_user,
            "entity": sg_shot,
            "project": self.app.context.project,
            "sg_path_to_movie": self._resolved_export_path,
            "code": file_name,
        }

        self.app.log_debug("Creating Shotgun Version %s" % str(data))
        vers = sg.create("Version", data)

        self.app.log_debug("Uploading quicktime to Shotgun...")
        sg.upload("Version", vers["id"], self._resolved_export_path, "sg_uploaded_movie")

        
        


class ShotgunTranscodePreset(ShotgunHieroObjectBase, FnTranscodeExporter.TranscodePreset):
    """
    Settings for the shotgun transcode step
    """
    
    def __init__(self, name, properties):
        FnTranscodeExporter.TranscodePreset.__init__(self, name, properties)
        self._parentType = ShotgunTranscodeExporter
