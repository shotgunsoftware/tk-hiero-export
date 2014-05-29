# Copyright (c) 2013 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

from tank import Hook


class HieroUpdateVersionData(Hook):
    """ Update the data dictionary for a Version to be created in Shotgun. """
    def execute(self, version_data, task, **kwargs):
        """
        Update the version_data dictionary to change the data for the Version
        that will be created in Shotgun.
        """
        pass
