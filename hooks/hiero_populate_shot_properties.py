"""
Copyright (c) 2013 Shotgun Software, Inc
----------------------------------------------------
"""
from tank import Hook


class HieroPopulateShotProperties(Hook):
    def execute(self, default, passed, **kwargs):
        self.parent.log_debug("HieroPopulateShotProperties.execute()")

        # initialize our properties to their default value
        default["statusMap"] = [
            ("Ready To Start", "rdy"),
            ("In Progress", "ip"),
            ("On Hold", "hld"),
            ("Final", "fin"),
        ]

        default["templateMap"] = []

        # merge in any properties being loaded
        default.update(passed)
