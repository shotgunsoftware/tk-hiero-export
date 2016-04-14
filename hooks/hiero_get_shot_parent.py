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


class HieroGetShotParent(Hook):
    """
    Return a Shotgun entity that corresponds to the supplied Hiero sequence.
    """
    def execute(self, hiero_sequence, data):
        """
        Given a Hiero sequence and data cache, return the corresponding entity
        in Shotgun to serve as the parent for contained Shots.

        :param hiero_sequence: A Hiero sequence object
        :param data: A dictionary with cached parent data.

        The data dict is typically the app's `preprocess_data` which maintains
        the cache across invocations of this hook.
        """

        # stick a lookup cache on the data object.
        if "parent_cache" not in data:
            data["parent_cache"] = {}

        if hiero_sequence.guid() in data["parent_cache"]:
            return data["parent_cache"][hiero_sequence.guid()]

        # parent not found in cache, grab it from Shotgun
        sg = self.parent.shotgun
        filt = [
            ["project", "is", self.parent.context.project],
            ["code", "is", hiero_sequence.name()],
        ]

        # the entity type of the parent.
        par_entity_type = "Sequence"

        parents = sg.find(par_entity_type, filt)
        if len(parents) > 1:
            # can not handle multiple parents with the same name
            raise StandardError(
                "Multiple %s entities named '%s' found" %
                (par_entity_type, hiero_sequence.name())
            )

        if len(parents) == 0:
            # create the parent in shotgun
            par_data = {
                "code": hiero_sequence.name(),
                "project": self.parent.context.project,
            }
            parent = sg.create(par_entity_type, par_data)
            self.parent.log_info(
                "Created %s in Shotgun: %s" % (par_entity_type, par_data))
        else:
            parent = parents[0]

        # update the thumbnail for the parent
        self.parent.execute_hook("hook_upload_thumbnail", entity=parent,
            source=hiero_sequence, item=None)

        # cache the results
        data["parent_cache"][hiero_sequence.guid()] = parent

        return parent

