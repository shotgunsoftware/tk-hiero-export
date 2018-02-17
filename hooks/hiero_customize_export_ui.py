# Copyright (c) 2018 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

#  UI Hook
# ===========================

import sgtk
import hiero

from sgtk.platform.qt import QtGui

HookBaseClass = sgtk.get_hook_baseclass()


class HieroCustomizeExportUI(HookBaseClass):
    """

    """
    def create_shot_processor_widget(self, parent):
        """

        """
        # return None

        widget = QtGui.QWidget(parent)
        widget.setLayout(QtGui.QFormLayout())
        return widget

    def get_shot_processor_ui_properties(self):
        """
        [
            dict(
                label=str,
                key=str,
                value=property_value,
                type=property_type # Usually == type(value)
                tooltip=str,
            ),
            ...
        ]
        """
        # return []

        return [
            dict(
                label="Create Cut:",
                key="sgCreateCut",
                value=True,
                type=bool,
                tooltip="Create a Cut and CutItems in Shotgun...",
            ),
            dict(
                label="Head In:",
                key="updateSgHeadIn",
                value=True,
                type=bool,
                tooltip="Update 'sg_head_in' on the Shot entity.",
            ),
            dict(
                label="Cut In:",
                key="updateSgCutIn",
                value=True,
                type=bool,
                tooltip="Update 'sg_cut_in' on the Shot entity.",
            ),
            dict(
                label="Cut Out:",
                key="updateSgCutOut",
                value=True,
                type=bool,
                tooltip="Update 'sg_cut_out' on the Shot entity.",
            ),
            dict(
                label="Tail Out:",
                key="updateSgTailOut",
                value=True,
                type=bool,
                tooltip="Update 'sg_tail_out' on the Shot entity.",
            ),
            dict(
                label="Cut Duration:",
                key="updateSgCutDuration",
                value=True,
                type=bool,
                tooltip="Update 'sg_cut_duration' on the Shot entity.",
            ),
            dict(
                label="Working Duration:",
                key="updateSgWorkingDuration",
                value=True,
                type=bool,
                tooltip="Update 'sg_working_duration' on the Shot entity.",
            ),
            dict(
                label="Create Folders:",
                key="tkCreateFilesystemStructure",
                value=True,
                type=bool,
                tooltip="Run the Toolkit 'Create Folders' command for the Shot entity.",
            ),
        ]

    def set_shot_processor_ui_properties(self, widget, properties):
        """
        :param widget: The Qt widget that was created by the
            create_shot_processor_widget hook method.
        :param OrderedDict properties: A dict containing hiero.ui.FnUIProperty
            objects, keyed by label, that were constructed from the data
            built by the get_shot_processor_ui_properties hook method.
        """
        # return

        layout = widget.layout()

        for label, prop in properties.iteritems():
            if label == "Create Cut:":
                layout.addRow(create_cut, properties[create_cut])
                layout.addRow(QtGui.QLabel("--- Frame Ranges ---"))
                continue

            layout.addRow(label, prop)

    def create_transcode_exporter_widget(self, parent):
        """

        """
        return None

    def get_transcode_exporter_ui_properties(self):
        """
        [
            dict(
                label=str,
                key=str,
                value=property_value,
                type=property_type # Usually == type(value)
                tooltip=str,
            ),
            ...
        ]
        """
        return []

    def set_transcode_exporter_ui_properties(self, widget, properties):
        """
        :param widget: The Qt widget that was created by the
            create_transcode_exporter_widget hook method.
        :param OrderedDict properties: A dict containing hiero.ui.FnUIProperty
            objects, keyed by label, that were constructed from the data
            built by the get_transcode_exporter_ui_properties hook method.
        """
        return

    def create_audio_exporter_widget(self, parent):
        """

        """
        return None

    def get_audio_exporter_ui_properties(self):
        """
        [
            dict(
                label=str,
                key=str,
                value=property_value,
                type=property_type # Usually == type(value)
                tooltip=str,
            ),
            ...
        ]
        """
        return []

    def set_audio_exporter_ui_properties(self, widget, properties):
        """
        :param widget: The Qt widget that was created by the
            create_audio_exporter_widget hook method.
        :param OrderedDict properties: A dict containing hiero.ui.FnUIProperty
            objects, keyed by label, that were constructed from the data
            built by the get_audio_exporter_ui_properties hook method.
        """
        return

    def create_nuke_shot_exporter_widget(self, parent):
        """

        """
        return None

    def get_nuke_shot_exporter_ui_properties(self):
        """
        [
            dict(
                label=str,
                key=str,
                value=property_value,
                type=property_type # Usually == type(value)
                tooltip=str,
            ),
            ...
        ]
        """
        return []

    def set_nuke_shot_exporter_ui_properties(self, widget, properties):
        """
        :param widget: The Qt widget that was created by the
            create_audio_exporter_widget hook method.
        :param OrderedDict properties: A dict containing hiero.ui.FnUIProperty
            objects, keyed by label, that were constructed from the data
            built by the get_audio_exporter_ui_properties hook method.
        """
        return
        










