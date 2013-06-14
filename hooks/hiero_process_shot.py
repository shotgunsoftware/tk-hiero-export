"""
Copyright (c) 2013 Shotgun Software, Inc
----------------------------------------------------
"""
import os
import shutil
import tempfile

from tank import Hook


class HieroProcessShot(Hook):
    def execute(self, task, **kwargs):
        self.parent.log_debug("HieroProcessShot.execute(%s)" % task)

        sequence = self._get_sequence(task._sequence)
        shot = self._get_shot(task._item, sequence)

        # update the shots
        start, end = task.outputRange(ignoreHandles=False, ignoreRetimes=False, clampToSource=True)
        data = {
            'sg_cut_duration': end - start + 1,
            'sg_cut_in': start,
            'sg_cut_out': end,
        }

        # get status from the tags
        status = None
        statusMap = dict(task._preset.properties()["statusMap"])
        for tag in task._item.tags():
            if tag.name() in statusMap:
                status = statusMap[tag.name()]
                break
        if status:
            data['sg_status_list'] = status

        # get task template from the tags
        template = None
        templateMap = dict(task._preset.properties()["templateMap"])
        for tag in task._item.tags():
            if tag.name() in templateMap:
                template = self.parent.tank.shotgun.find_one(
                    'TaskTemplate',
                    [['entity_type', 'is', 'Shot'], ['code', 'is', templateMap[tag.name()]]],
                )
                break
        if not template:
            default_template = self.parent.get_setting('default_task_template')
            if default_template:
                template = self.parent.tank.shotgun.find_one(
                    'TaskTemplate',
                    [['entity_type', 'is', 'Shot'], ['code', 'is', default_template]],
                )
        if template:
            data['task_template'] = template

        # commit the changes and update the thumbnail
        self.parent.tank.shotgun.update('Shot', shot['id'], data)
        self._upload_poster_frame(shot, task._item.source())

        # create the directory structure
        self.parent.tank.create_filesystem_structure('Shot', [shot['id']])

        # return without error
        self.parent.log_info("Updated shot %s" % task.shotName())
        return False

    def _get_sequence(self, sequence):
        if self.parent.first_shot:
            self.parent._seqMap = {}

        if sequence.guid() in self.parent._seqMap:
            return self.parent._seqMap[sequence.guid()]

        # sequence not found yet, grab it from Shotgun
        sg = self.parent.tank.shotgun
        filt = [
            ['project', 'is', self.parent.context.project],
            ['code', 'is', sequence.name()],
        ]
        sequences = sg.find('Sequence', filt)
        if len(sequences) > 1:
            # can not handle multiple sequences with the same name
            raise StandardError("Multiple sequences named '%s' found", sequence.name())

        if len(sequences) == 0:
            # create the sequence in shotgun
            data = {
                'code': sequence.name(),
                'project': self.parent.context.project,
            }
            self.parent.log_info("Created sequence %s" % sequence.name())
            sg_seq = sg.create('Sequence', data)
        else:
            sg_seq = sequences[0]

        self._upload_poster_frame(sg_seq, sequence)

        # cache the results
        self.parent._seqMap[sequence.guid()] = sg_seq
        return sg_seq

    def _get_shot(self, item, sequence):
        # grab shot from Shotgun
        sg = self.parent.tank.shotgun
        filt = [
            ['project', 'is', self.parent.context.project],
            ['sg_sequence', 'is', sequence],
            ['code', 'is', item.name()],
        ]
        shots = sg.find('Shot', filt)
        if len(shots) > 1:
            # can not handle multiple shots with the same name
            raise StandardError("Multiple shots named '%s' found", item.name())
        if len(shots) == 0:
            # create shot in shotgun
            data = {
                'code': item.name(),
                'sg_sequence': sequence,
                'project': self.parent.context.project,
            }
            shot = sg.create('Shot', data)
        else:
            shot = shots[0]

        return shot

    def _upload_poster_frame(self, entity, source):
        # update the thumbnail
        sg = self.parent.tank.shotgun
        thumbdir = tempfile.mkdtemp(prefix='hiero_process_shot')
        try:
            path = "%s.jpg" % os.path.join(thumbdir, source.name())
            thumb = source.thumbnail(source.posterFrame())
            thumb.save(path)
            sg.upload_thumbnail(entity['type'], entity['id'], path)
        finally:
            shutil.rmtree(thumbdir)
