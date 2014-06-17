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
    def execute(self, item, data, **kwargs):
        """
        Takes a hiero.core.TrackItem as input and returns a data dictionary for
        the shot to update the cut info for.
        """
        # get the parent sequence for the Shot
        sequence = self._get_sequence(item, data)

        # grab shot from Shotgun
        sg = self.parent.shotgun
        filt = [
            ["project", "is", self.parent.context.project],
            ["sg_sequence", "is", sequence],
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
                "sg_sequence": sequence,
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

    def _get_sequence(self, item, data):
        """Return the shotgun sequence for the given Hiero items"""
        # stick a lookup cache on the data object.
        if "seq_cache" not in data:
            data["seq_cache"] = {}

        hiero_sequence = item.parentSequence()
        if hiero_sequence.guid() in data["seq_cache"]:
            return data["seq_cache"][hiero_sequence.guid()]

        # sequence not found in cache, grab it from Shotgun
        sg = self.parent.shotgun
        filt = [
            ["project", "is", self.parent.context.project],
            ["code", "is", hiero_sequence.name()],
        ]
        sequences = sg.find("Sequence", filt)
        if len(sequences) > 1:
            # can not handle multiple sequences with the same name
            raise StandardError("Multiple sequences named '%s' found" % hiero_sequence.name())

        if len(sequences) == 0:
            # create the sequence in shotgun
            seq_data = {
                "code": hiero_sequence.name(),
                "project": self.parent.context.project,
            }
            sequence = sg.create("Sequence", seq_data)
            self.parent.log_info("Created Sequence in Shotgun: %s" % seq_data)
        else:
            sequence = sequences[0]

        # update the thumbnail for the sequence
        self.parent.execute_hook("hook_upload_thumbnail", entity=sequence, source=hiero_sequence, item=None)

        # cache the results
        data["seq_cache"][hiero_sequence.guid()] = sequence

        return sequence
