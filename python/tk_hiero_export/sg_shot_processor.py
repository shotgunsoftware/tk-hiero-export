# Copyright (c) 2013 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

import itertools

from PySide import QtGui

import hiero.core
from hiero.core import FnExporterBase

from hiero.exporters import FnShotProcessor

from .base import ShotgunHieroObjectBase
from .shot_updater import ShotgunShotUpdaterPreset
from .shot_updater import ShotgunShotUpdater
from .collating_exporter import CollatedShotPreset
from .collating_exporter_ui import CollatingExporterUI


class ShotgunShotProcessor(ShotgunHieroObjectBase, FnShotProcessor.ShotProcessor, CollatingExporterUI):
    """
    Add extra UI and hook functionality to the built in Shot processor.
    """
    def __init__(self, preset, submission=None, synchronous=False):
        FnShotProcessor.ShotProcessor.__init__(self, preset, submission, synchronous)
        CollatingExporterUI.__init__(self)

        # Call pre processor hook here to make sure it happens pior to any 'hook_resolve_custom_strings'.
        # The order if execution is basically [init processor, resolve user entries, startProcessing].
        self.app.execute_hook("hook_pre_export", processor=self)

    def displayName(self):
        return "Shotgun Shot Processor"

    def toolTip(self):
        return "Process as Shots generates output on a per shot basis and logs it in Shotgun."

    def startProcessing(self, exportItems):
        """
        Executing the export
        """

        # add a top level task to manage shotgun shots
        exportTemplate = self._exportTemplate.flatten()
        properties = self._preset.properties().get('shotgunShotCreateProperties', {})

        # inject collate settings into Tasks where needed
        collateTracks = properties.get('collateTracks', False)
        collateShotNames = properties.get('collateShotNames', False)
        for (itemPath, itemPreset) in exportTemplate:
            if 'collateTracks' in itemPreset.properties():
                itemPreset.properties()['collateTracks'] = collateTracks
            if 'collateShotNames' in itemPreset.properties():
                itemPreset.properties()['collateShotNames'] = collateShotNames

        exportTemplate.insert(0, (".shotgun", ShotgunShotUpdaterPreset(".shotgun", properties)))
        self._exportTemplate.restore(exportTemplate)

        # tag app as first shot
        self.app.shot_count = 0

        # do the normal processing
        FnShotProcessor.ShotProcessor.startProcessing(self, exportItems)

        self._setCutOrder()

        # get rid of our placeholder
        exportTemplate.pop(0)
        self._exportTemplate.restore(exportTemplate)

    def _setCutOrder(self):
        """
        Set a proper time-based cut order on shot updater tasks.
        Otherwise the cut order is entirely dependent on how tasks are
        scheduled by the ShotProcessor.
        """

        tasks = []
        for taskGroup in self._submission.children():
            for task in taskGroup.children():
                if isinstance(task, ShotgunShotUpdater):
                    if task.isCollated():
                        # For collating sequences, skip tasks that are not hero
                        if task.isHero():
                            tasks.append(task)
                    else:
                        # For non-collating sequences, add every task
                        tasks.append(task)

        tasks.sort(key=lambda task: task._item.timelineIn())
        for i in range(0, len(tasks)):
            # Cut order are 1-based
            tasks[i]._cut_order = i + 1

    def populateUI(self, widget, exportItems, editMode=None):
        """
        Create Settings UI
        """
        # create a layout with custom top and bottom widgets
        master_layout = QtGui.QVBoxLayout(widget)
        master_layout.setContentsMargins(0, 0, 0, 0)

        # add group box for shotgun stuff
        shotgun_groupbox = QtGui.QGroupBox("Shotgun Shot and Sequence Creation Settings")
        master_layout.addWidget(shotgun_groupbox)
        shotgun_layout = QtGui.QVBoxLayout(shotgun_groupbox)

        # create some helpful text
        header_text = QtGui.QLabel()
        header_text.setText("""<big>Welcome to the Shotgun Shot Export!</big>
                      <p>When you are using the Shotgun Shot Processor, Shots and Sequences in<br>
                      Shotgun will be created based on your Hiero Project. Existing Shots will<br>
                      be updated with the latest cut lengths. Quicktimes for each shot will be <br>
                      sent to Screening Room for review when you use the special Shotgun <br>
                      Transcode plugin - all included and ready to go in the default preset.<br>&nbsp;
                      </p>
                      """)
        shotgun_layout.addWidget(header_text)

        # make space for the spreadsheet
        spreadsheet_widget = QtGui.QWidget()
        shotgun_layout.addWidget(spreadsheet_widget)
        layout = QtGui.QHBoxLayout(spreadsheet_widget)
        layout.setContentsMargins(0, 0, 0, 0)
        properties = self._preset.properties().get('shotgunShotCreateProperties', {})
        layout.addWidget(self._build_tag_selector_widget(exportItems, properties))
        layout.addStretch(1)

        footer_text = QtGui.QLabel()
        default_task_template = self.app.get_setting('default_task_template')
        footer_text.setText("<p>Shots without any tags will be assigned the '%s' task template.</p>" % default_task_template )
        shotgun_layout.addWidget(footer_text)

        # add collate options
        collating_widget = QtGui.QWidget()
        shotgun_layout.addWidget(collating_widget)
        CollatingExporterUI.populateUI(self, collating_widget, properties)

        # add default settings from baseclass below
        default = QtGui.QWidget()
        master_layout.addWidget(default)
        FnShotProcessor.ShotProcessor.populateUI(self, default, exportItems, editMode)

    def _build_tag_selector_widget(self, items, properties):
        """
        Returns a QT widget which contains the tag
        """
        fields = ['code']
        filt = [['entity_type', 'is', 'Shot']]
        templates = [t['code'] for t in self.app.shotgun.find('TaskTemplate', filt, fields=fields)]

        schema = self.app.shotgun.schema_field_read('Shot', 'sg_status_list')
        statuses = schema['sg_status_list']['properties']['valid_values']['value']

        values = [statuses, templates]
        labels = ['Shotgun Shot Status', 'Shotgun Task Template for Shots']
        keys = ['sg_status_hiero_tags', 'task_template_map']

        # build a map of tag value pairs from the properties
        propertyDicts = [dict(properties[key]) for key in keys]
        propertyTags = list(set(itertools.chain(*[d.keys() for d in propertyDicts])))
        map = {}
        for tag in propertyTags:
            map[tag] = [d.get(tag, None) for d in propertyDicts]

        # add in blank entries for the current tags
        tags = self._get_tags(items)
        for tag in tags:
            map.setdefault(tag.name(), [None]*len(keys))

        # keep a known order
        names = sorted(map.keys())

        # setup the table
        tagTable = QtGui.QTableWidget(len(names), len(labels) + 1)
        tagTable.setMinimumHeight(150)
        tagTable.setHorizontalHeaderLabels(['Hiero Tags'] + labels)
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

                    # if no tag mapped to a name
                    if combo is None:
                        continue

                    # otherwise grab the text and keep it in the properties
                    select = combo.currentText()
                    propertyDicts[col][name] = (select and str(select) or None)
                    properties[key] = [(k, v) for (k, v) in propertyDicts[col].items() if v]

        # and build the table
        tagsByName = self._get_all_tags_by_name()
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

    def _get_all_tags_by_name(self):
        """
        Returns all tags by name
        """
        tagsByName = {}
        projects = [hiero.core.project('Tag Presets')] + list(hiero.core.projects())
        for project in projects:
            tagsByName.update(dict([(tag.name(), tag) for tag in hiero.core.findProjectTags(project)]))
        return tagsByName

    def _get_tags(self, items):
        tags = FnExporterBase.tagsFromSelection(items, includeChildren=True)
        tags = [tag for (tag, objType) in tags if tag.visible() and "Transcode" not in tag.name()]
        tags = [tag for tag in tags if "Nuke Project File" not in tag.name()]
        return tags


class ShotgunShotProcessorPreset(ShotgunHieroObjectBase, FnShotProcessor.ShotProcessorPreset, CollatedShotPreset):
    """
    Handles presets for the shot processor.
    """
    def __init__(self, name, properties):
        FnShotProcessor.ShotProcessorPreset.__init__(self, name, properties)

        self._parentType = ShotgunShotProcessor

        # set up default properties
        self.properties()['shotgunShotCreateProperties'] = {}
        default_properties = self.properties()['shotgunShotCreateProperties']
        CollatedShotPreset.__init__(self, default_properties)

        # add setting to control how we map sg statuses and tags
        # just map the standard "status" tags in hiero against
        # the standard task statuses in Shotgun. If a user wants
        # to change these, they can just create a new preset :)
        default_properties["sg_status_hiero_tags"] = [ ("Ready To Start", "rdy"),
                                                       ("In Progress", "ip"),
                                                       ("On Hold", "hld"),
                                                       ("Final", "fin"), ]

        # add setting to control the default task template in Shotgun.
        # again, populate some of the standard tags in hiero. The rest
        # of them can be manually set.
        default_template = self.app.get_setting('default_task_template')
        default_properties["task_template_map"] = [("Ready To Start", default_template),
                                                   ("In Progress", default_template),
                                                   ("On Hold", default_template),
                                                   ("Final", default_template)]

        # finally, update the properties based on the properties passed to the constructor
        explicit_constructor_properties = properties.get('shotgunShotCreateProperties', {})
        default_properties.update(explicit_constructor_properties)

    def addUserResolveEntries(self, resolver):
        self.app.log_debug('Adding custom resolver tk_version')

        # the following hook can end up pulling shots from the get_shot hook,
        # so initialize the cache that is used to store the values from that
        # hook.
        if not hasattr(self.app, "preprocess_data"):
            self.app.preprocess_data = {}

        resolver.addResolver("{tk_version}", "Version string formatted by Shotgun Toolkit.", 
                             lambda keyword, task: self._formatTkVersionString(task.versionString()))

        custom_template_fields = self.app.get_setting("custom_template_fields")
        self.app.log_debug('Adding custom resolvers %s' % [ctf['keyword'] for ctf in custom_template_fields])
        for ctf in custom_template_fields:
            resolver.addResolver(
                "{%s}" % ctf['keyword'], ctf['description'],
                lambda keyword, task:
                    self.app.execute_hook("hook_resolve_custom_strings", keyword=keyword, task=task)
            )
