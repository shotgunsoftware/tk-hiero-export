"""
Copyright (c) 2013 Shotgun Software, Inc
----------------------------------------------------

Update the Hiero export to be Tank/Shotgun aware
"""
import os
import sys

from tank.platform import Application

import hiero.ui
import hiero.core
import hiero.exporters

from hiero.exporters import FnExternalRender
from hiero.exporters import FnNukeShotExporter

# do not use tk import here, hiero needs the classes to be in their
# standard namespace, hack to get the right path in sys.path
sys.path.append(os.path.join(os.path.dirname(__file__), "python"))
import tk_hiero_export.exporters
from tk_hiero_export.exporters import ShotgunShotUpdater
from tk_hiero_export.exporters import ShotgunShotProcessor
from tk_hiero_export.exporters import ShotgunTranscodePreset
from tk_hiero_export.exporters import ShotgunShotUpdaterPreset
from tk_hiero_export.exporters import ShotgunTranscodeExporter
from tk_hiero_export.exporters import ShotgunShotProcessorPreset
from tk_hiero_export.exporters_ui import ShotgunTranscodeExporterUI
sys.path.pop()


class HieroExport(Application):
    def init_app(self):
        # let the shot exporter know when the first shot is being run
        self.first_shot = False

        self.register_exporter()

    def register_exporter(self):
        tk_hiero_export.exporters.ShotgunExporterBase.setApp(self)

        hiero.core.taskRegistry.registerTask(ShotgunShotUpdaterPreset, ShotgunShotUpdater)
        hiero.core.taskRegistry.registerTask(ShotgunTranscodePreset, ShotgunTranscodeExporter)
        hiero.core.taskRegistry.registerProcessor(ShotgunShotProcessorPreset, ShotgunShotProcessor)

        hiero.ui.taskUIRegistry.registerTaskUI(ShotgunTranscodePreset, ShotgunTranscodeExporterUI)
        hiero.ui.taskUIRegistry.registerProcessorUI(ShotgunShotProcessorPreset, ShotgunShotProcessor)

        # Add our default preset
        self._oldAddDefaultPresets = hiero.core.taskRegistry._defaultPresets
        hiero.core.taskRegistry.setDefaultPresets(self.AddDefaultPresets)

    def AddDefaultPresets(self, overwrite):
        # add all previous defaults
        self._oldAddDefaultPresets(overwrite)

        name = "Basic Shotgun Shot"
        localpresets = [preset.name() for preset in hiero.core.taskRegistry.localPresets()]

        if overwrite or name not in localpresets:
            # grab all our path templates
            plateTemplate = self.get_template('template_plate_path')
            scriptTemplate = self.get_template('template_script_path')
            renderTemplate = self.get_template('template_render_path')

            # call the hook to translate them
            plate = self.execute_hook("hook_translate_template", template=plateTemplate)
            script = self.execute_hook("hook_translate_template", template=scriptTemplate)
            render = self.execute_hook("hook_translate_template", template=renderTemplate)

            # and set the default properties to be based off of those templates
            properties = {
                "exportTemplate": (
                    (script, FnNukeShotExporter.NukeShotPreset("", {'readPaths': [], 'writePaths': ['{shot}/nuke/renders/{shot}_comp_{version}.####.{ext}']})),
                    (render, FnExternalRender.NukeRenderPreset("", {'file_type': 'dpx', 'dpx': {'datatype' : '10 bit'}})),
                    (plate, ShotgunTranscodePreset("", {'file_type': 'mov', 'mov': {}})),
                )
            }
            preset = ShotgunShotProcessorPreset(name, properties)
            hiero.core.taskRegistry.removeProcessorPreset(name)
            hiero.core.taskRegistry.addProcessorPreset(name, preset)
