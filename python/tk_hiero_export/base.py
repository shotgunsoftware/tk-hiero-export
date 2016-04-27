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
import time

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
        """
        try:
            version_number = int(hiero_version_str[1:])
        except ValueError:
            # Version is sometimes a glob expression (when building tracks for example)
            # in these cases, return the original string without the leading 'v'
            return hiero_version_str[1:]

        version_template = self.app.get_template('template_version')
        tk_version_str = version_template.apply_fields({'version': version_number})
        return tk_version_str

    def _upload_thumbnail_to_sg(self, sg_entity, thumb_qimage):
        """
        Updates the thumbnail for an entity in Shotgun
        """
        import tempfile
        import uuid

        thumbdir = tempfile.mkdtemp(prefix='hiero_process_thumbnail_')
        try:
            path = "%s.png" % os.path.join(thumbdir, sg_entity.get('name', 'thumbnail'))
            # scale it down to 600px wide
            thumb_qimage_scaled = thumb_qimage.scaledToWidth(600, QtCore.Qt.SmoothTransformation)
            thumb_qimage_scaled.save(path)
            self.app.log_debug("Uploading thumbnail for %s %s..." % (sg_entity['type'], sg_entity['id']))
            self.app.shotgun.upload_thumbnail(sg_entity['type'], sg_entity['id'], path)
        except Exception, e:
            self.app.log_info("Thumbnail for %s %s (#%s) was not refreshed in Shotgun: %s" % (sg_entity['type'], sg_entity.get('name'), sg_entity['id'], e))
        finally:
            # Sometimes Windows holds on to the temporary thumbnail file longer than expected which
            # can cause an exception here. If we wait a second and try again, this usually solves
            # the issue.
            try:
                shutil.rmtree(thumbdir)
            except Exception:
                self.parent.log_error("Error removing temporary thumbnail file, trying again.")
                time.sleep(1.0)
                shutil.rmtree(thumbdir)

    def _cutsSupported(self):
        """Returns True if the site has Cut support, False otherwise."""
        return self.app.shotgun.server_caps.version >= (7, 0, 0)




