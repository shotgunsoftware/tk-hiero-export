# Copyright (c) 2018 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

import sgtk

HookBaseClass = sgtk.get_hook_baseclass()


class HieroGetProperties(HookBaseClass):
    """

    """
    def get_shot_processor_preset_properties(self):
        """

        """
        # return dict()

        return dict(
            updateSgHeadIn=True,
            updateSgCutIn=True,
            updateSgCutOut=True,
            updateSgTailOut=True,
            updateSgCutDuration=True,
            updateSgWorkingDuration=True,
            tkCreateFilesystemStructure=True,
            sgCreateCut=True,
        )

    def get_transcode_exporter_preset_properties(self):
        """

        """
        return dict()

    def get_audio_exporter_preset_properties(self):
        """

        """
        return dict()

    def get_nuke_shot_exporter_preset_properties(self):
        """

        """
        return dict()











