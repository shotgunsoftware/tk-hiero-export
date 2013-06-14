"""
Copyright (c) 2013 Shotgun Software, Inc
----------------------------------------------------
"""
import os
import getpass

from tank import Hook


class HieroPublishTranscode(Hook):
    def execute(self, path, sequence, shot, thumbnail, **kwargs):
        self.parent.log_debug("HieroPublishTranscode.execute()")
        sg = self.parent.tank.shotgun

        # lookup current login
        login = getpass.getuser()
        sg_user = sg.find_one('HumanUser', [['login', 'is', login]])

        # lookup sequence
        sg_sequence = sg.find_one('Sequence',
            [['project', 'is', self.parent.context.project], ['code', 'is', sequence]]
        )
        sg_shot = None
        if sg_sequence:
            sg_shot = sg.find_one('Shot', [['sg_sequence', 'is', sg_sequence], ['code', 'is', shot]])
        # lookup seq/shot
        data = {
            'user': sg_user,
            'created_by': sg_user,
            'entity': sg_shot,
            'project': self.parent.context.project,
            'code': os.path.splitext(os.path.basename(path))[0],
        }

        vers = sg.create('Version', data)

        sg.upload('Version', vers['id'], path, 'sg_uploaded_movie')
