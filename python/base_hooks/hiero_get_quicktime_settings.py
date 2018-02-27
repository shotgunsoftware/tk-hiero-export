# Copyright (c) 2013 Shotgun Software Inc.
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


class HieroGetQuicktimeSettings(HookBaseClass):
    """
    Return a Shotgun Shot dictionary for the given Hiero items
    """
    def execute(self, for_shotgun, **kwargs):
        """
        Returns a tuple where the first item is the file_type of a Nuke
        write node and the second item is a dictionary of knob names and
        values.
        """
        pass
