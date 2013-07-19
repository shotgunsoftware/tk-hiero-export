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


