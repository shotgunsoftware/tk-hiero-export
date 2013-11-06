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

    def _formatTkVersionString(self, version_str):
        """Reformat the Hiero version string to the tk format.

        Heiro's {version} tag includes the 'v'. Strip it off and have
        tk format the numeric value as defined in the templates file.

        We can't assume that the {version} key will exist in any specific
        template object so we iterate through all of them until we find
        one and use it to format the value. If we don't find one, log an
        error and return the original value.
        """
        # find a version TemplateKey
        for name, template in self._app.sgtk.templates.items():
            if 'version' in template.keys:
                version_template_key = template.keys['version']
                break
        try:
            val = int(version_str[1:])
            return version_template_key.str_from_value(val)
        except NameError:
            self._app.log_error("Unable to find a version TemplateKey to translate "
                                "the Hiero version string")
            return version_str



