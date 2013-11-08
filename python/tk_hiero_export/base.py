# Copyright (c) 2013 Shotgun Software Inc.
# 
# CONFIDENTIAL AND PROPRIETARY
# 
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit 
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your 
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights 
# not expressly granted therein are reserved by Shotgun Software Inc.

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


class ShotgunHieroObjectBase(object):
    """Base class to make the Hiero classes app aware."""
    _app = None

    @classmethod
    def setApp(cls, app):
        cls._app = app

    @property
    def app(self):
        return self._app

    def _formatTkVersionString(self, hiero_version_str):
        """Reformat the Hiero version string to the tk format.

        Heiro's {version} tag includes the 'v'. Strip it off and have
        tk format the numeric value as defined in the templates file.
        """
        version_template = self.app.get_template_by_name('hiero_version')
        if not version_template:
            raise tank.TankError("'hiero_version' must be defined in your templates file!")
        tpl_field = version_template.get_fields(hiero_version_str[1:]).popitem()
        tk_version_str = version_template.apply_fields({tpl_field[0]: tpl_field[1]})
        return tk_version_str




