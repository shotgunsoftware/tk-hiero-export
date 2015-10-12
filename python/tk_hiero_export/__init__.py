# Copyright (c) 2013 Shotgun Software Inc.
# 
# CONFIDENTIAL AND PROPRIETARY
# 
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit 
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your 
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights 
# not expressly granted therein are reserved by Shotgun Software Inc.

from .base import ShotgunHieroObjectBase
from .sg_shot_processor import ShotgunShotProcessorPreset

# If we're in Hiero 9.0+ then the first import will work,
# otherwise we will pull in the legacy shot processor.
try:
	from .sg_shot_processor import (
		ShotgunShotProcessor,
		ShotgunShotProcessorUI,
		ShotgunShotProcessorPreset,
	)
except ImportError:
	from .sg_shot_processor_legacy import LegacyShotgunShotProcessor as ShotgunShotProcessor
	from .sg_shot_processor_legacy import LegacyShotgunShotProcessorPreset as ShotgunShotProcessorPreset
	ShotgunShotProcessorUI = ShotgunShotProcessor

from .shot_updater import ShotgunShotUpdater, ShotgunShotUpdaterPreset
from .version_creator import ShotgunTranscodeExporterUI, ShotgunTranscodeExporter, ShotgunTranscodePreset
from .sg_nuke_shot_export import ShotgunNukeShotExporterUI, ShotgunNukeShotExporter, ShotgunNukeShotPreset
from .sg_audio_export import ShotgunAudioExporterUI, ShotgunAudioExporter, ShotgunAudioPreset