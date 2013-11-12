# Copyright (c) 2013 Shotgun Software Inc.
# 
# CONFIDENTIAL AND PROPRIETARY
# 
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit 
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your 
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights 
# not expressly granted therein are reserved by Shotgun Software Inc.

"""
Update the Hiero export to be Tank/Shotgun aware
"""
import re
import os
import sys
import shutil
import tempfile
import traceback

from PySide import QtCore

from tank.platform import Application

from tank import TankError

import hiero.ui
import hiero.core
import hiero.exporters

from hiero.exporters import FnExternalRender
from hiero.exporters import FnNukeShotExporter

# do not use tk import here, hiero needs the classes to be in their
# standard namespace, hack to get the right path in sys.path
sys.path.append(os.path.join(os.path.dirname(__file__), "python"))
from tk_hiero_export import ShotgunShotUpdater
from tk_hiero_export import ShotgunShotProcessor
from tk_hiero_export import ShotgunTranscodePreset
from tk_hiero_export import ShotgunShotUpdaterPreset
from tk_hiero_export import ShotgunTranscodeExporter
from tk_hiero_export import ShotgunShotProcessorPreset
from tk_hiero_export import ShotgunTranscodeExporterUI
from tk_hiero_export import ShotgunHieroObjectBase
sys.path.pop()

# list keywords Hiero is using in its export substitution
HIERO_SUBSTITUTION_KEYWORDS = ["clip", "day", "DD", "event",
                               "ext", "filebase", "fileext", "filehead",
                               "filename", "filepadding", "fullbinpath", "fullday", "fullmonth",
                               "MM", "month", "project", "projecroot", "sequence", "shot", 
                               "tk_version", "track", "user", "version", "YY", "YYYY"]


class HieroExport(Application):
    def init_app(self):
        # let the shot exporter know when the first shot is being run
        self.first_shot = False
        self._register_exporter()

    def _register_exporter(self):
        """
        Set up this app with the hiero exporter frameworks
        """
        # register our app with the base class that all custom hiero objects derive from.
        ShotgunHieroObjectBase.setApp(self)

        hiero.core.taskRegistry.registerTask(ShotgunShotUpdaterPreset, ShotgunShotUpdater)
        hiero.core.taskRegistry.registerTask(ShotgunTranscodePreset, ShotgunTranscodeExporter)
        hiero.core.taskRegistry.registerProcessor(ShotgunShotProcessorPreset, ShotgunShotProcessor)

        hiero.ui.taskUIRegistry.registerTaskUI(ShotgunTranscodePreset, ShotgunTranscodeExporterUI)
        hiero.ui.taskUIRegistry.registerProcessorUI(ShotgunShotProcessorPreset, ShotgunShotProcessor)

        # Add our default preset
        self._old_AddDefaultPresets_fn = hiero.core.taskRegistry._defaultPresets
        hiero.core.taskRegistry.setDefaultPresets(self._add_default_presets)

    def _add_default_presets(self, overwrite):
        """
        Hiero std method to add new exporter presets.
        Passed in to hiero.core.taskRegistry.setDefaultPresets() as a function pointer.
        """
        # add all built-in defaults
        self._old_AddDefaultPresets_fn(overwrite)

        # Add Shotgun template
        name = "Basic Shotgun Shot"
        localpresets = [preset.name() for preset in hiero.core.taskRegistry.localPresets()]

        # only add the preset if it is not already there - or if a reset to defaults is requested.
        if overwrite or name not in localpresets:
            # grab all our path templates
            plate_template = self.get_template("template_plate_path")
            script_template = self.get_template("template_nuke_script_path")
            render_template = self.get_template("template_render_path")

            # call the hook to translate them into hiero paths, using hiero keywords
            plate_hiero_str = self.execute_hook("hook_translate_template", template=plate_template)
            self.log_debug("Translated %s --> %s" % (plate_template, plate_hiero_str))

            script_hiero_str = self.execute_hook("hook_translate_template", template=script_template)
            self.log_debug("Translated %s --> %s" % (script_template, script_hiero_str))

            render_hiero_str = self.execute_hook("hook_translate_template", template=render_template)
            self.log_debug("Translated %s --> %s" % (render_template, render_hiero_str))

            # check so that no unknown keywords exist in the templates after translation
            self._validate_hiero_export_template(plate_hiero_str)
            self._validate_hiero_export_template(script_hiero_str)
            self._validate_hiero_export_template(render_hiero_str)

            # and set the default properties to be based off of those templates
            properties = {
                "exportTemplate": (
                    (script_hiero_str, FnNukeShotExporter.NukeShotPreset("", {'readPaths': [], 'writePaths': []})),
                    (render_hiero_str, FnExternalRender.NukeRenderPreset("", {'file_type': 'dpx', 'dpx': {'datatype' : '10 bit'}})),
                    (plate_hiero_str, ShotgunTranscodePreset("", {'file_type': 'mov', 'mov': {}})),
                )
            }
            preset = ShotgunShotProcessorPreset(name, properties)
            hiero.core.taskRegistry.removeProcessorPreset(name)
            hiero.core.taskRegistry.addProcessorPreset(name, preset)

    def _validate_hiero_export_template(self, template_str):
        """
        Validate that a template_str only contains hiero substitution keywords.
        """
        hiero_keywords = ["{%s}" % x for x in HIERO_SUBSTITUTION_KEYWORDS]
        for x in hiero_keywords:
            template_str = template_str.replace(x, "")
        # find any {xyz}
        regex = r"(?<={)[a-zA-Z_ 0-9]+(?=})"
        key_names = re.findall(regex, template_str)
        if len(key_names) > 0:
            raise TankError("The configuration template '%s' contains keywords %s which are "
                            "not recognized by Hiero. Either remove them from the sgtk template "
                            "or adjust the hook that converts a template to a hiero export "
                            "path to convert these fields into fixed strings or hiero "
                            "substitution tokens." % (template_str, ",".join(key_names) ) )
