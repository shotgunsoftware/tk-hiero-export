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


class HieroGetShot(Hook):
    """
    Return a Shotgun Shot dictionary for the given Hiero items
    """
    def execute(self, task, item, data, **kwargs):
        """
        Takes a hiero.core.TrackItem as input and returns a data dictionary for
        the shot to update the cut info for.
        """

        # get the parent entity for the Shot
        parent = self.parent.execute_hook(
            "hook_get_shot_parent",
            hiero_sequence=item.parentSequence(),
            data=data
        )

        # shot parent field
        parent_field = "sg_sequence"

        # grab shot from Shotgun
        sg = self.parent.shotgun
        filt = [
            ["project", "is", self.parent.context.project],
            [parent_field, "is", parent],
            ["code", "is", item.name()],
        ]
        fields = kwargs.get("fields", [])
        shots = sg.find("Shot", filt, fields=fields)
        if len(shots) > 1:
            # can not handle multiple shots with the same name
            raise StandardError("Multiple shots named '%s' found", item.name())
        if len(shots) == 0:
            # create shot in shotgun
            shot_data = {
                "code": item.name(),
                parent_field: parent,
                "project": self.parent.context.project,
            }
            shot = sg.create("Shot", shot_data)
            self.parent.log_info("Created Shot in Shotgun: %s" % shot_data)
        else:
            shot = shots[0]

        # update the thumbnail for the shot
        upload_thumbnail = kwargs.get("upload_thumbnail", True)
        if upload_thumbnail:
            self.parent.execute_hook(
                "hook_upload_thumbnail",
                entity=shot,
                source=item.source(),
                item=item,
                task=kwargs.get("task")
            )

        return shot

