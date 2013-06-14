"""
Copyright (c) 2013 Shotgun Software, Inc
----------------------------------------------------

Build a UI for processing a Hiero export as shots.  Currently provides
an interface to map Hiero tags to Shotgun statuses and task templates.
"""
import itertools

from PySide import QtGui
from PySide import QtCore

import hiero.core
from hiero.core import FnExporterBase

from tank import Hook


class HieroPopulateShotUI(Hook):
    def execute(self, widget, items, properties, **kwargs):
        self.parent.log_debug("HieroPopulateShotUI.execute()")

        # add the ui to map tags to shotgun status
        layout = QtGui.QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._buildTagMap(items, properties))
        layout.addStretch(1)

    def _buildTagMap(self, items, properties):
        fields = ['code']
        filt = [['entity_type', 'is', 'Shot']]
        templates = [t['code'] for t in self.parent.shotgun.find('TaskTemplate', filt, fields=fields)]

        schema = self.parent.shotgun.schema_field_read('Shot', 'sg_status_list')
        statuses = schema['sg_status_list']['properties']['valid_values']['value']

        tagTable = self._buildTableWidget(
            items,
            properties,
            [statuses, templates],
            ['Shot Status', 'Shot Task Template'],
            ['statusMap', 'templateMap'],
        )
        return tagTable

    def _getAllTagsByName(self):
        tagsByName = {}
        projects = [hiero.core.project('Tag Presets')] + list(hiero.core.projects())
        for project in projects:
            tagsByName.update(dict([(tag.name(), tag) for tag in hiero.core.findProjectTags(project)]))
        return tagsByName

    def _getTags(self, items):
        tags = FnExporterBase.tagsFromSelection(items, includeChildren=True)
        tags = [tag for (tag, objType) in tags if tag.visible() and "Transcode" not in tag.name()]
        tags = [tag for tag in tags if "Nuke Project File" not in tag.name()]
        return tags

    def _buildTableWidget(self, items, properties, values, labels, keys):
        # build a map of tag value pairs from the properties
        propertyDicts = [dict(properties[key]) for key in keys]
        propertyTags = list(set(itertools.chain(*[d.keys() for d in propertyDicts])))
        map = {}
        for tag in propertyTags:
            map[tag] = [d.get(tag, None) for d in propertyDicts]

        # add in blank entries for the current tags
        tags = self._getTags(items)
        for tag in tags:
            map.setdefault(tag.name(), [None]*len(keys))

        # keep a known order
        names = sorted(map.keys())

        # setup the table
        tagTable = QtGui.QTableWidget(len(names), len(labels) + 1)
        tagTable.setHorizontalHeaderLabels(['Tags'] + labels)
        tagTable.setAlternatingRowColors(True)
        tagTable.setSelectionMode(tagTable.NoSelection)
        tagTable.setShowGrid(False)
        tagTable.verticalHeader().hide()
        tagTable.horizontalHeader().setStretchLastSection(True)
        tagTable.setSizePolicy(QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Preferred)

        # on change rebuild the properties
        def changed(index):
            for (row, name) in enumerate(names):
                for (col, key) in enumerate(keys):
                    combo = tagTable.cellWidget(row, col+1)
                    select = combo.currentText()
                    propertyDicts[col][name] = (select and str(select) or None)
                    properties[key] = [(k, v) for (k, v) in propertyDicts[col].items() if v]

        # and build the table
        tagsByName = self._getAllTagsByName()
        for (row, name) in enumerate(names):
            tag = tagsByName.get(name, None)
            if tag is None:
                continue

            # build item for the tag
            item = QtGui.QTableWidgetItem(name)
            item.setIcon(QtGui.QIcon(tag.icon()))
            tagTable.setItem(row, 0, item)

            # build combo boxes for each set of values
            for (col, vals) in enumerate(values):
                combo = QtGui.QComboBox()
                combo.addItem(None)
                for (i, value) in enumerate(vals):
                    combo.addItem(value)
                    # see if the current item is the one in the properties
                    if map[name][col] == value:
                        combo.setCurrentIndex(i+1)
                combo.currentIndexChanged[int].connect(changed)
                # adjust sizes to avoid clipping or scrolling
                width = combo.minimumSizeHint().width()
                combo.setMinimumWidth(width)
                combo.setSizeAdjustPolicy(combo.AdjustToContents)
                tagTable.setCellWidget(row, col+1, combo)

        tagTable.resizeRowsToContents()
        tagTable.resizeColumnsToContents()

        width = sum([tagTable.columnWidth(i) for i in xrange(len(keys)+1)]) + 60
        tagTable.setMinimumWidth(width)

        return tagTable
