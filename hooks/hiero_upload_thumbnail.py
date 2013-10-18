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
import shutil
import tempfile
import traceback

from PySide import QtCore

from tank import Hook
import tank.templatekey


class HieroUploadThumbnail(Hook):
    """
    Upload a thumbnail to a given Shotgun entity for a given Hiero source item.
    """
    def execute(self, entity, source, item, **kwargs):
        thumbdir = tempfile.mkdtemp(prefix='hiero_process_shot')
        try:
            path = "%s.png" % os.path.join(thumbdir, source.name())
            poster = source.posterFrame()
            thumb_qimage = source.thumbnail(poster)
            # scale it down to 600px wide
            thumb_qimage_scaled = thumb_qimage.scaledToWidth(600, QtCore.Qt.SmoothTransformation)
            # scale thumbnail here...
            thumb_qimage_scaled.save(path)
            self.parent.log_debug("Uploading thumbnail for %s %s..." % (entity['type'], entity['id']))
            self.parent.shotgun.upload_thumbnail(entity['type'], entity['id'], path)
        except:
            self.parent.log_info("Thumbnail for %s was not refreshed in Shotgun." % source)

            tb = traceback.format_exc()
            self.parent.log_debug(tb)
        finally:
            shutil.rmtree(thumbdir)
