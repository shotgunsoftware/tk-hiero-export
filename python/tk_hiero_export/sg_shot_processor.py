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

# For Hiero versions prior to 9.0 the ShotProcessor class
# contained both the execution and UI logic. That was split
# into two classes in 9.0. To maintain backwards compatibility
# but without duplicating code or breaking existing local
# export presets we've split into separate UI and Processor
# classes, but for the UI class we will fall back on using
# the ShotProcessor as the base class in cases where we are
# unable to import the separate ShotProcessorUI class that
# was introduced in 9.0.
try:
    from hiero.exporters.FnShotProcessorUI import ShotProcessorUI
except ImportError:
    ShotProcessorUI = FnShotProcessor.ShotProcessor

from .base import ShotgunHieroObjectBase
from .version_creator import ShotgunTranscodeExporter
from .shot_updater import ShotgunShotUpdaterPreset
from .shot_updater import ShotgunShotUpdater
from .collating_exporter import CollatedShotPreset
from .collating_exporter_ui import CollatingExporterUI

class ShotgunShotProcessorUI(ShotgunHieroObjectBase, ShotProcessorUI, CollatingExporterUI):
    """
    Add extra UI to the built in Shot processor.
    """
    def __init__(self, preset):
        ShotProcessorUI.__init__(self, preset)
        CollatingExporterUI.__init__(self)

    def displayName(self):
        return "Process as Shotgun Shots"

    def toolTip(self):
        return "Process as Shotgun Shots generates output on a per-shot basis and logs it in Shotgun."

    def populateUI(self, widget, exportItems, editMode=None):
        """
        Create Settings UI.
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

        if _cutsSupported(self.app.shotgun):
            cut_type_layout = self._build_cut_type_layout(properties)
            shotgun_layout.addLayout(cut_type_layout)

        # add default settings from baseclass below
        default = QtGui.QWidget()
        master_layout.addWidget(default)
        ShotProcessorUI.populateUI(self, default, exportItems, editMode)

    def _build_cut_type_layout(self, properties):
        """
        Returns a QComboBox with a list of cut types
        """
        tooltip = "What to populate in the `Type` field for this Cut in Shotgun"

        # ---- construct the widget

        # populate the list of cut types and default from the site schema
        schema = self.app.shotgun.schema_field_read('Cut', 'sg_cut_type')
        cut_types = schema['sg_cut_type']['properties']['valid_values']['value']

        # make sure we have an empty item at the top
        cut_types.insert(0, "")

        # create a combo box for the cut types
        cut_type_widget = QtGui.QComboBox()
        cut_type_widget.setToolTip(tooltip)
        cut_type_widget.addItems(cut_types)

        # make sure the current value is set
        current_value = properties["sg_cut_type"]
        index = cut_type_widget.findText(current_value)
        if index > 0:
            # found a match
            cut_type_widget.setCurrentIndex(index)
        else:
            # empty value
            cut_type_widget.setCurrentIndex(0)

        # a callback to update the property dict when the value changes
        def value_changed(new_value):
            properties["sg_cut_type"] = new_value

        # connect the widget index changed to the callback
        cut_type_widget.currentIndexChanged[str].connect(value_changed)

        # ---- construct the layout with a label

        cut_type_label = QtGui.QLabel("Cut Type:")
        cut_type_label.setToolTip(tooltip)

        cut_type_layout = QtGui.QHBoxLayout()
        cut_type_layout.addWidget(cut_type_label)
        cut_type_layout.addWidget(cut_type_widget)
        cut_type_layout.addStretch()

        return cut_type_layout

    def _build_tag_selector_widget(self, items, properties):
        """
        Returns a QT widget which contains the tag.
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

class ShotgunShotProcessor(ShotgunHieroObjectBase, FnShotProcessor.ShotProcessor):
    """
    Adds hook functionality to the built in Shot processor.
    """
    def __init__(self, preset, submission=None, synchronous=False):
        FnShotProcessor.ShotProcessor.__init__(self, preset, submission, synchronous)

        # Call pre processor hook here to make sure it happens pior to any 'hook_resolve_custom_strings'.
        # The order if execution is basically [init processor, resolve user entries, startProcessing].
        self.app.execute_hook("hook_pre_export", processor=self)

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

        # get rid of our placeholder
        exportTemplate.pop(0)
        self._exportTemplate.restore(exportTemplate)

    def processTaskPreQueue(self):
        """Process the tasks just before they're queued up for execution."""

        # do the normal pre processing as defined in the base class
        FnShotProcessor.ShotProcessor.processTaskPreQueue(self)

        # we'll keep a list of tuples of associated transcode and shot updater
        # tasks. later we'll attach cut related information to these tasks that
        # they can use during execution
        cut_related_tasks = []

        # iterate over the tasks groups to be executed
        for taskGroup in self._submission.children():

            # placeholders for the tasks we want to pre-process
            (transcode_task, shot_updater_task) = (None, None)

            # look at all the tasks in the group and identify the shot updater
            # and transcode tasks.
            for task in taskGroup.children():

                # shot updater
                if isinstance(task, ShotgunShotUpdater):
                    if task.isCollated():
                        # For collating sequences, skip tasks that are not hero
                        if task.isHero():
                            shot_updater_task = task
                    else:
                        # For non-collating sequences, add every task
                        shot_updater_task = task

                # transcode
                elif isinstance(task, ShotgunTranscodeExporter):
                    transcode_task = task

            # add the pair of associated tasks to the list of cut related tasks
            cut_related_tasks.append((shot_updater_task, transcode_task))

        # sort the tasks based on their position in the timeline. this gives
        # us the cut order.
        cut_related_tasks.sort(key=lambda tb: tb[0]._item.timelineIn())

        # go ahead and populate the shot updater tasks with the cut order. this
        # is used to set the cut order on the Shot as it is created/updated.
        for i in range(0, len(cut_related_tasks)):
            (shot_updater_task, transcode_task) = cut_related_tasks[i]

            # Cut order is 1-based
            shot_updater_task._cut_order = i + 1

        if not _cutsSupported(self.app.shotgun):
            # cuts not supported. all done here
            return

        # ---- at this point, we have the cut related tasks in order.

        # Create the Cut and CutItem entries for this submission. This will be
        # done in a batch call, so show the busy popup while this is going on.
        # Otherwise, it may look like Hiero is hanging.
        self.app.engine.show_busy(
            "Preprocessing Sequence",
            "Creating Cut and Cut Items in Shotgun ..."
        )

        # wrap in a try/catch to make sure we can clear the popup at the end
        try:
            # pre-process the cut data for the tasks about to execute
            self._processCut(cut_related_tasks)
        finally:
            self.app.engine.clear_busy()

    def _getCutData(self, hiero_sequence):
        """Returns a dict of cut data for the supplied hiero sequence."""

        # get the parent entity for the Shot
        parent_entity = self.app.execute_hook(
            "hook_get_shot_parent",
            hiero_sequence=hiero_sequence,
            data=self.app.preprocess_data
        )

        # first determine which revision number of the cut to create
        sg = self.app.shotgun
        prev_cut = sg.find_one(
            "Cut",
            [["code", "is", hiero_sequence.name()],
             ["entity", "is", parent_entity]],
            ["revision_number"],
            [{"field_name": "revision_number", "direction": "desc"}]
        )
        if prev_cut is None:
            next_revision_number = 1
        else:
            next_revision_number = prev_cut["revision_number"] + 1

        self._app.log_debug(
            "The cut revision number will be %s." % (next_revision_number,))

        # retrieve the cut type from the presets
        properties = self._preset.properties().get(
            'shotgunShotCreateProperties', {})
        cut_type = properties.get("sg_cut_type", "")

        cut_data = {
            "project": self.app.context.project,
            "entity": parent_entity,
            "code": hiero_sequence.name(),
            "sg_cut_type": cut_type,
            "description": "Automatically created by the Hiero Shot exporter.",
            "revision_number": next_revision_number,
            "fps": hiero_sequence.framerate().toFloat(),
        }

        return cut_data

    def _processCut(self, cut_related_tasks):
        """Collect data and create the Cut and CutItem entries for the tasks.

        We need to pre-create the Cut entity so that the CutItems can be
        parented to it. Ideally the CutItems would be created during the
        execution of the shot updater task, but we need the individual tasks to
        build the complete Cut data. So we're creating all the CutItems before
        the tasks are processed. We also need to associate the Versions created
        during the transcode tasks with the corresponding CutItems. Pre
        processing the CutItems allow us to attach the CutItem data to the
        Transcode task so that it can update the item in SG after the version
        is created.
        """

        # make sure the data cache is ready. this code may create entities in
        # SG and they'll be stored here for reuse.
        if not hasattr(self.app, "preprocess_data"):
            self.app.preprocess_data = {}

        # get the hiero sequence from the first updater task's item
        hiero_sequence = cut_related_tasks[0][0]._item.sequence()
        fps = hiero_sequence.framerate().toFloat()

        # populate the bulk of the cut data
        cut_data = self._getCutData(hiero_sequence)

        # calculate the cut duration while processing the individual tasks
        cut_duration = 0

        # will hold a list of cut item dictionaries that will be populated as
        # the tasks are processed. these will be used to batch create the cut
        # items at the end
        cut_item_data_list = []

        # process the tasks in order
        for i in range(0, len(cut_related_tasks)):
            (shot_updater_task, transcode_task) = cut_related_tasks[i]

            cut_order = i + 1

            # this retrieves the basic cut information from the updater task.
            cut_item_data = shot_updater_task.get_cut_item_data()

            # translate some of the data to timecodes
            tc_cut_item_in = self._timecode(cut_item_data["cut_item_in"], fps)
            tc_cut_item_out = self._timecode(cut_item_data["cut_item_out"], fps)
            tc_edit_in = self._timecode(cut_item_data["edit_in"], fps)
            tc_edit_out = self._timecode(cut_item_data["edit_out"], fps)

            # get the shot so that we have all we need for the cut item.
            # this may create the shot if it doesn't exist already
            shot = self.app.execute_hook(
                "hook_get_shot",
                task=shot_updater_task,
                item=shot_updater_task._item,
                data=self.app.preprocess_data,
            )

            # update the cut item data with the timecodes and other fields
            cut_item_data.update({
                "code": shot_updater_task.clipName(),
                "project": self.app.context.project,
                "shot": {"id": shot["id"], "type": "Shot"},
                "cut_order": cut_order,
                "timecode_cut_item_in": tc_cut_item_in,
                "timecode_cut_item_out": tc_cut_item_out,
                "timecode_edit_in": tc_edit_in,
                "timecode_edit_out": tc_edit_out,
            })

            # add the populated cut item data to the list
            cut_item_data_list.append(cut_item_data)

            if cut_order == 1:
                # this is the first item in the cut,
                cut_data["timecode_start"] = tc_edit_in

            if cut_order == len(cut_related_tasks):
                cut_data["timecode_end"] = tc_edit_out

            # add the length of this item to the cut duration
            cut_duration += \
                cut_item_data["cut_item_out"] - \
                cut_item_data["cut_item_in"] + 1

        # all tasks processed, add the duration to the cut data
        cut_data["duration"] = cut_duration

        # create the cut to get the id.
        sg = self.app.shotgun
        cut = sg.create("Cut", cut_data)
        self._app.log_info("Created Cut in Shotgun: %s" % (cut,))

        # build a list of batch requests for the cut items
        batch_data = []
        for cut_item_data in cut_item_data_list:

            # make sure the cut items have a parent Cut
            cut_item_data["cut"] = {"id": cut["id"], "type": cut["type"]}

            batch_data.append({
                "request_type": "create",
                "entity_type": "CutItem",
                "data": cut_item_data,
            })

        # batch create the cut items
        self.app.log_debug("Executing sg batch command for cut items....")
        cut_items = sg.batch(batch_data)
        self._app.log_info("Created CutItems in Shotgun: %s" % (cut_items,))
        self._app.log_debug("...done!")

        # attach the newly created cut items to their corresponding tasks.
        # the transcode task will update the cut item with the version
        # after it is created.
        for cut_item in cut_items:
            cut_order = cut_item["cut_order"]
            (shot_updater_task, transcode_task) = cut_related_tasks[cut_order - 1]

            # dont' want to assume that there is an associated transcode task.
            # if there is, attache the cut item data so that the version is
            # updated. If not, then we'll get a cut item without an associated
            # version (cut info only in SG, no playable).
            if transcode_task:
                transcode_task._cut_item_data = cut_item

    def _timecode(self, frame, fps):
        """Convenience wrapper to convert a given frame and fps to a timecode.

        :param frame: Frame number
        :param fps: Frames per seconds (float)
        :return: timecode string
        """
        return hiero.core.Timecode.timeToString(frame, fps,
            hiero.core.Timecode.kDisplayTimecode)


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

        # holds the cut type to use when creating Cut entires in SG
        default_properties["sg_cut_type"] = ""

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

def _cutsSupported(sg_connection):
    """Returns True if the site has Cut support, False otherwise."""
    return sg_connection.server_caps.version >= (6, 3, 13)

