'''

monkey-patched nuke script exporter for hiero

'''



from os.path import dirname, realpath, exists, join, exists
import os, math
from pprint import pprint
import re, copy, itertools

from PySide2 import(QtCore, QtGui, QtWidgets)

import hiero #@UnresolvedImport
from hiero.exporters import FnNukeShotExporter, FnNukeShotExporterUI #@UnresolvedImport
import hiero.core.nuke as nuke #@UnresolvedImport
from hiero.exporters.FnReformatHelpers import reformatNodeFromPreset #@UnresolvedImport
from hiero.exporters.FnExportUtil import trackItemTimeCodeNodeStartFrame, TrackItemExportScriptWriter #@UnresolvedImport
from hiero.exporters import FnShotExporter, FnExternalRender, FnScriptLayout #@UnresolvedImport
from hiero.core import FnNukeHelpersV2, FnNukeHelpers, Clip, Keys, isVideoFileExtension #@UnresolvedImport

from hiero.ui.nuke_bridge import FnNsFrameServer as postProcessor #@UnresolvedImport

from .base import ShotgunHieroObjectBase
from base_hooks import HieroGetShot

#get the location of this install, and the location of the sgtk config directory
currentRoot=dirname(realpath(__file__))
configRoot=join(dirname(dirname(dirname(dirname(dirname(dirname(currentRoot)))))), "config")

class PhospheneWriteNode(nuke.UserDefinedNode):
	'''
	an extension of the hiero node creation class, specifically for the phosphene write node
	'''
	
	def __init__(self, app, inputNode0=None, inputNodes=None, **keywords):
				
		#store for debug (available function setWarning)
		self.app=app
		
		#if we hard code the string here, it'll lose a lot of the formating it needs
		#better to keep it as-is in the python internal buffer by reading it directly from disk
		
		self.phospheneWriteFile=join(configRoot, "phosphene", "nuke", "phospheneWriteNode", "writeNode.nk")
		print "loading phosphene write node from "+str(self.phospheneWriteFile)
		if not exists(self.phospheneWriteFile):
			print "ERROR - cannot locate file, node will be empty"
			nuke.UserDefinedNode.__init__(self, "Group {\n xpos 900\n ypos 1043\n}")
			return
		
		with open(self.phospheneWriteFile, 'r') as myFile:
			self.phospheneWriteNode=myFile.read()
			
		#trim off the header
		self.phospheneWriteNode="Group {"+self.phospheneWriteNode.split("Group {")[1]
		
		#remove the inputs 0 line (seems to indicate node is not connected to anything
		if " inputs 0\n" in self.phospheneWriteNode:
			self.phospheneWriteNode=self.phospheneWriteNode.replace(" inputs 0\n", "")
			
		#try removing the position as well
		#find the first instances of coord lines
		try:
			xCoords=re.findall("(.xpos -?\\d\\d?\\d?.)", self.phospheneWriteNode, flags=re.DOTALL)[0]
			yCoords=re.findall("(.ypos -?\\d\\d?\\d?.)", self.phospheneWriteNode, flags=re.DOTALL)[0]
			
			self.phospheneWriteNode=self.phospheneWriteNode.replace(xCoords, "")
			self.phospheneWriteNode=self.phospheneWriteNode.replace(yCoords, "")
		except:
			pass
			
		nuke.UserDefinedNode.__init__(self, self.phospheneWriteNode)
		
class PhospheneSlateNode(nuke.UserDefinedNode):
	'''
	an extension of the hiero node creation class, specifically for the phosphene slate node
	'''
	
	def __init__(self, app, inputNode0=None, inputNodes=None, **keywords):
				
		#store for debug (available function setWarning)
		self.app=app
		
		#if we hard code the string here, it'll lose a lot of the formating it needs
		#better to keep it as-is in the python internal buffer by reading it directly from disk
		
		self.phospheneSlateFile=join(configRoot, "phosphene", "nuke", "phospheneSlateNode", "slateNode.nk")
		print "loading phosphene slate node from "+str(self.phospheneSlateFile)
		if not exists(self.phospheneSlateFile):
			print "ERROR - cannot locate file, node will be empty"
			nuke.UserDefinedNode.__init__(self, "Group {\n xpos 900\n ypos 1043\n}")
			return
		
		with open(self.phospheneSlateFile, 'r') as myFile:
			self.phospheneSlateNode=myFile.read()
			
		#trim off the header
		self.phospheneSlateNode="Group {"+self.phospheneSlateNode.split("Group {")[1]
		
		#remove the inputs 0 line (seems to indicate node is not connected to anything)
		if " inputs 0\n" in self.phospheneSlateNode:
			self.phospheneSlateNode=self.phospheneSlateNode.replace(" inputs 0\n", "")
			
		#try removing the position as well
		#find the first instances of coord lines
		try:
			xCoords=re.findall("(.xpos -?\\d\\d?\\d?.)", self.phospheneSlateNode, flags=re.DOTALL)[0]
			yCoords=re.findall("(.ypos -?\\d\\d?\\d?.)", self.phospheneSlateNode, flags=re.DOTALL)[0]
			
			self.phospheneSlateNode=self.phospheneSlateNode.replace(xCoords, "")
			self.phospheneSlateNode=self.phospheneSlateNode.replace(yCoords, "")
		except:
			pass
			
		nuke.UserDefinedNode.__init__(self, self.phospheneSlateNode)



#
#
#
# I take no responsibility for the state of the following mess!
# Simple asks like adjusting the name of the read node created for a track required re-writing and instantiating
# up to 4-5 classes each.
#
# I have tried to only re-write the functions that I am adjusting, and leave the rest defined in the source class.
# However in many cases, the core function is several hundered lines long, and it's re-created here in its entirety.
#

class PhospheneNukeShotExporterUI(hiero.ui.TaskUIBase):
	#we made this class to hide all the UI options, so we can be sure the export is consistent
	
	def __init__(self, preset):
		"""UI for CustomNukeShotExporter task."""
		hiero.ui.TaskUIBase.__init__(self, preset.parentType(), preset, "Nuke Project File")
		
		self._uiProperties = []
		self._tags = []
		
		self._collateTimeProperty = True
		self._collateNameProperty = True
		self._includeAnnotationsProperty = False
		self._showAnnotationsProperty = False

	def populateUI (self, widget, exportTemplate):
		
		if exportTemplate:
		
			self._exportTemplate = exportTemplate
			layout = widget.layout()

			overriddenLabel=QtWidgets.QLabel('Advanced settings have been overridden to ensure consistency.')
			layout.addWidget(overriddenLabel)

	def _isShotExport(self):
		""" Check if the export task is for shots or whole sequences. The UI should
		be slightly different in these cases.
		"""
		return (self._preset.supportedItems() & self._preset.kTrackItem)

	def setTags ( self, tags ):
		"""setTags passes the subset of tags associated with the selection for export"""
		self._tags = tags

class PhospheneNukeShotExporter(ShotgunHieroObjectBase, FnNukeShotExporter.NukeShotExporter):

	
	def __init__( self, initDict ):
		
		#print "running init on phospheneNukeShotExporter with arguments: "
		#pprint(initDict)
		
		FnNukeShotExporter.NukeShotExporter.__init__(self, initDict)
		#self.NukeShotPreset=FnNukeShotExporter.NukeShotPreset()

	def _buildAdditionalNodes(self, item):
		# Callback from script generation to add additional nodes, returns a list of hiero nuke.Node objects
		return FnNukeShotExporter.NukeShotExporter._buildAdditionalNodes(self, item)
	
	def resolvePath(self, path):
		"""Replace any recognized tokens in path with their current value."""
		
		if not hasattr(self.app, "preprocess_data"):
			self.app.preprocess_data = {}
	
		# Replace Windows path separators before token resolve
		path = path.replace("\\", "/")
		
		# first use sg-derived info before defaulting to hiero values
		shot = self.app.execute_hook(
				"hook_get_shot",
				task=None,
				item=self._item,
				data=self.app.preprocess_data,
				upload_thumbnail=False,
				base_class=HieroGetShot,
			)
		
		#it's amazing how complicated the resolver class is to do this
		for fieldName in shot:
			if "{"+fieldName.lower()+"}" in path:
				path=path.replace("{"+fieldName.lower()+"}", shot[fieldName])

	
		try:
			# Resolve token in path
			path = self._resolver.resolve(self, path, isPath=True)
		except RuntimeError as error:
			self.setError(str(error))


		# Strip padding out of single file types
		if isVideoFileExtension(os.path.splitext(path)[1].lower()):
			path = re.sub(r'.[#]+', '', path)
			path = re.sub(r'.%[\d]+d', '', path)
	
		# Normalise path to use / for separators
		path = path.replace("\\", "/")
	
		# Strip trailing spaces on directory names.	This causes problems on Windows 
		# because it will not let you create a directory ending with a space, so if you do 
		# e.g. mkdir("adirectory ") the space will be silently removed.
		path = path.replace(" /", "/")
	
		return path

	def resolvedExportPath(self):
		"""resolvedExportPath()
		returns the output path with and tokens resolved"""
		print "attempting to resolve path "+str(self._exportPath)+" with item "+str(self._item)
		outputPath=self.resolvePath(self._exportPath)
		print "resolved to: "+str(outputPath)
		return outputPath
	
	def _buildCollatedSequence(self):
		"""From the list of collated Items build a sequence, extend edge shots for handles, offset relative to custom start or master shot source frame"""
		
		FnNukeShotExporter.NukeShotExporter._buildCollatedSequence(self)
		
		#set the master track correctly, for attach of write node
		for trackitem in self._collatedItems:
			parentTrack = trackitem.parentTrack()
			if parentTrack.name() == "VFXPLATE":
				trackItemCopy = trackitem.copy()
				self._masterTrackItemCopy = trackItemCopy

	def _createWriteNodes(self, firstFrame, start, end, framerate, rootNode):
		#returns a list of write nodes (and push/set nodes for placement) - expects hiero nuke.Node objects

		
		class WriteNodeGroup():
			#helper class to allow grouping of nodes around a write node
			def __init__(self):
				self._list = []
				self._name = ""

			def append(self, node):
				self._list.append(node)

			def remove(self, node):
				self._list.remove(node)

			def setWriteNodeName(self, name):
				self._name = name

			def getWriteNodeName(self):
				return self._name

			def nodes(self):
				return self._list

		# To add Write nodes, we get a task for the paths with the preset
		# (default is the "Nuke Write Node" preset) and ask it to generate the Write node for
		# us, since it knows all about codecs and extensions and can do the token
		# substitution properly for that particular item.
		# And doing it here rather than in taskStep out of threading paranoia.
		writeNodes = []
		# Create a stack to prevent multiple write nodes inputting into each other
		StackIdBase = "WriteBranch_"
		branchCount = 0
		stackId = StackIdBase + str(branchCount)

		mainStackId = stackId

		mainStackEndId = "MainStackEnd"

		writeNodes.append( nuke.SetNode(stackId, 0) )
		writeNodeGroups = []

		timelineWriteNode = self._preset.properties()["timelineWriteNode"]
		timelineWriteNodeName = ""
		mainWriteStack = None

		for task, writePath, writePreset in self._writeTaskData:
			if hasattr(task, "nukeWriteNode"):
				localWriteNodeGroup = WriteNodeGroup()
				# Push to the stack before adding the write node

				# If the write path matches the timeline write path and we don't already have a timeline
				# write group, then set this group as the timeline write group.
				setAsMainWrite = ((writePath == timelineWriteNode) and not mainWriteStack)

				if setAsMainWrite:
					# Timeline Write goes on the main branch
					localWriteNodeGroup.append( nuke.PushNode(mainStackId) )
				else:
					# Add dot nodes for non timeline writes.
					# Add a push so that these branch from the Set for the last branch.
					localWriteNodeGroup.append( nuke.PushNode(stackId) )

					# Add the dot
					dotNode = nuke.DotNode()
					localWriteNodeGroup.append(dotNode)

					# Add a set so that the next branch connects to the dot for the last branch
					branchCount += 1
					stackId = StackIdBase + str(branchCount)
					localWriteNodeGroup.append( nuke.SetNode(stackId, 0) )

				try:
					trackItem = self._item if isinstance(self._item, hiero.core.TrackItem) else None
					reformatNode = reformatNodeFromPreset(writePreset, self._parentSequence.format(), trackItem=trackItem)
					if reformatNode:
						localWriteNodeGroup.append(reformatNode)
				except Exception as e:
					self.setError(str(e))

				# Add Burnin group (if enabled)
				burninGroup = task.addBurninNodes(script=None)
				if burninGroup is not None:
					localWriteNodeGroup.append(burninGroup)

				try:
					writeNode = task.nukeWriteNode(framerate, project=self._project)
					writeNode.setKnob("first", start)
					writeNode.setKnob("last", end)
					localWriteNodeGroup.append(writeNode)

					# Set the groups write node name
					localWriteNodeGroup.setWriteNodeName(writeNode.knob("name"))

					if setAsMainWrite:
						mainWriteStack = localWriteNodeGroup
						localWriteNodeGroup.append( nuke.SetNode(mainStackEndId, 0) )

					writeNodeGroups.append(localWriteNodeGroup)

				except RuntimeError as e:
					# Failed to generate write node, set task error in export queue
					# Most likely because could not map default colourspace for format settings.
					self.setError(str(e))

		# Find duplicate write node names
		nameSet = set()
		for nodeStack in writeNodeGroups:
			nodeName = nodeStack.getWriteNodeName()
			if nodeName in nameSet:
				self.setWarning("Duplicate write node name:\'%s\'"%nodeName)
			else:
				nameSet.add(nodeName)

		# If no timelineWriteNode was set, just pick the first one
		if not mainWriteStack and writeNodeGroups:
			mainWriteStack = writeNodeGroups[0]
			# Get rid of the dot node as we're going to add this group to the main branch
			for node in mainWriteStack.nodes():
				if isinstance(node, nuke.DotNode):
					mainWriteStack.remove(node)
			mainWriteStack.append( nuke.SetNode(mainStackEndId, 0) )

		# Set the write node name to the root
		if mainWriteStack:
			timelineWriteNodeName = mainWriteStack.getWriteNodeName()
			rootNode.setKnob(nuke.RootNode.kTimelineWriteNodeKnobName, timelineWriteNodeName)

		# Flatten the groups as a list
		for nodeStack in writeNodeGroups:
			writeNodes.extend(nodeStack.nodes())

		# Add push to connect the next node (probably the viewer) to the timeline write node 
		if mainWriteStack:
			writeNodes.append( nuke.PushNode(mainStackEndId) )

		return writeNodes
	
	def writeSequence(self, script):
		""" Write the collated sequence to the script. """
		sequenceDisconnected = self.writingSequenceDisconnected()

		script.pushLayoutContext("sequence", self._sequence.name(), disconnected=sequenceDisconnected)
		# When building a collated sequence, everything is offset by 1000
		# This gives head room for shots which may go negative when transposed to a
		# custom start frame. This offset is negated during script generation.
		#offset = -FnNukeShotExporter.NukeShotExporter.kCollatedSequenceFrameOffset if self._collate else 0
		offset = 0

		# When exporting a sequence, everything must output to the same format,
		# if it's set to plate format, use the sequence format. When collating,
		# the sequence will have the same format as the master track item.
		reformatMethod = copy.copy(self._preset.properties()["reformat"])
		if reformatMethod['to_type'] == nuke.ReformatNode.kCompFormatAsPlate:
			reformatMethod['to_type'] = nuke.ReformatNode.kCompReformatToSequence

		scriptParams = FnNukeHelpersV2.ScriptWriteParameters(includeAnnotations=self.includeAnnotations(),
																includeEffects=self.includeEffects(),
																retimeMethod=self._preset.properties()["method"],
																reformatMethod=reformatMethod,
																additionalNodesCallback=self._buildAdditionalNodes)
		
		sequenceWriter = CustomSequenceScriptWriter(self._sequence, scriptParams)
		
		sequenceWriter.writeToScript(script,
										offset=offset,
										skipOffline=self._skipOffline,
										disconnected=sequenceDisconnected,
										 masterTrackItem=self._masterTrackItemCopy)

		script.popLayoutContext()

	def _taskStep(self):
		FnShotExporter.ShotTask.taskStep(self)
		if self._nothingToDo:
			return False
		
		script = nuke.ScriptWriter()
		
		start, end = self.outputRange(ignoreRetimes=True, clampToSource=False)
		
		#
		#
		# The root is defined here
		#
		
		#use overall start frame if it's been defined
		#if self._startFrame is not None and self._cutHandles is not None:
		#	start += self._startFrame
		#	end += self._startFrame
				
		unclampedStart = start
		hiero.core.log.debug( "rootNode range is %s %s %s", start, end, self._startFrame )
		
		firstFrame = start
		if self._startFrame is not None:
			firstFrame = self._startFrame

		# if startFrame is negative we can only assume this is intentional
		if start < 0 and (self._startFrame is None or self._startFrame >= 0):
			# We dont want to export an image sequence with negative frame numbers
			self.setWarning("%i Frames of handles will result in a negative frame index.\nFirst frame clamped to 0." % self._cutHandles)
			start = 0
			firstFrame = 0

		# Clip framerate may be invalid, then use parent sequence framerate
		framerate = self._sequence.framerate()
		dropFrames = self._sequence.dropFrame()
		if self._clip and self._clip.framerate().isValid():
			framerate = self._clip.framerate()
			dropFrames = self._clip.dropFrame()
		fps = framerate.toFloat()
		showAnnotations = self._preset.properties()["showAnnotations"]

		# Create the root node, this specifies the global frame range and frame rate
		rootNode = nuke.RootNode(firstFrame, firstFrame+end, fps, showAnnotations)
		rootNode.addProjectSettings(self._projectSettings)
		#rootNode.setKnob("project_directory", os.path.split(self.resolvedExportPath())[0])
		script.addNode(rootNode)

		if isinstance(self._item, hiero.core.TrackItem):
			rootNode.addInputTextKnob("shot_guid", value=hiero.core.FnNukeHelpers._guidFromCopyTag(self._item),
																tooltip="This is used to identify the master track item within the script",
																visible=False)
			inHandle, outHandle = self.outputHandles(self._retime != True)
			rootNode.addInputTextKnob("in_handle", value=int(inHandle), visible=False)
			rootNode.addInputTextKnob("out_handle", value=int(outHandle), visible=False)

		# Set the format knob of the root node
		rootNode.setKnob("format", self.rootFormat())

		# BUG 40367 - proxy_type should be set to 'scale' by default to reflect
		# the custom default set in Nuke. Sadly this value can't be queried,
		# as it's set by nuke.knobDefault, hence the hard coding.
		rootNode.setKnob("proxy_type","scale")

		# Add Unconnected additional nodes
		if self._preset.properties()["additionalNodesEnabled"]:
			script.addNode(FnExternalRender.createAdditionalNodes(FnExternalRender.kUnconnected, self._preset.properties()["additionalNodesData"], self._item))

		writeNodes = self._createWriteNodes(firstFrame, start, end, framerate, rootNode)

		# MPLEC TODO should enforce in UI that you can't pick things that won't work.
		if not writeNodes:
			# Blank preset is valid, if preset has been set and doesn't exist, report as error
			self.setWarning(str("NukeShotExporter: No write node destination selected"))

		if self.writingSequence():
			self.writeSequence(script)

		# Write out the single track item
		else:
			self.writeTrackItem(script, firstFrame)


		script.pushLayoutContext("write", "%s_Render" % self._item.name())
		
		#
		# creating write starts here!
		#
		#create a dot
		dotWrite = nuke.DotNode()
		dotWrite.setName('OUTPUT_TREE')
		script.addNode(dotWrite)
		
		metadataNode = nuke.MetadataNode(metadatavalues=[("hiero/project", self._projectName), ("hiero/project_guid", self._project.guid())] )
		
		# Add sequence Tags to metadata
		metadataNode.addMetadataFromTags( self._sequence.tags() )
		
		# Apply timeline offset to nuke output
		if isinstance(self._item, hiero.core.TrackItem):
			if self._cutHandles is None:
				# Whole clip, so timecode start frame is first frame of clip
				timeCodeNodeStartFrame = unclampedStart
			else:
				startHandle, endHandle = self.outputHandles()
				timeCodeNodeStartFrame = trackItemTimeCodeNodeStartFrame(unclampedStart, self._item, startHandle, endHandle)
			timecodeStart = self._clip.timecodeStart()
		else:
			# Exporting whole sequence/clip
			timeCodeNodeStartFrame = unclampedStart
			timecodeStart = self._item.timecodeStart()

		script.addNode(nuke.AddTimeCodeNode(timecodeStart=timecodeStart, fps=framerate, dropFrames=dropFrames, frame=timeCodeNodeStartFrame))
		# The AddTimeCode field will insert an integer framerate into the metadata, if the framerate is floating point, we need to correct this
		metadataNode.addMetadata([("input/frame_rate",framerate.toFloat())])

		script.addNode(metadataNode)
		
		#add phosphene slate node
		phospheneSlate=PhospheneSlateNode(self)
		script.addNode(phospheneSlate)

		# add phosphene write node
		phospheneWrite=PhospheneWriteNode(self)
		script.addNode(phospheneWrite)

		# Create pre-comp nodes for external annotation scripts
		annotationsNodes = self._createAnnotationsPreComps()
		if annotationsNodes:
			script.addNode(annotationsNodes)

		scriptFilename = self.resolvedExportPath()
		hiero.core.log.debug( "Writing Script to: %s", scriptFilename )

		# Call callback before writing script to disk (see _beforeNukeScriptWrite definition below)
		self._beforeNukeScriptWrite(script)

		script.popLayoutContext()

		# Layout the script
		FnScriptLayout.scriptLayout(script)

		#only write to the disk if the destination script doesn't exist (don't overwrite)
		if not exists(scriptFilename):
			script.writeToDisk(scriptFilename)
			#if postProcessScript has been set to false, don't post process
			#it will be done on a background thread by create comp
			#needs to be done as part of export task so that information
			#is added in hiero workflow
			if self._preset.properties().get("postProcessScript", True):
				error = postProcessor.postProcessScript(scriptFilename)
				if error:
					hiero.core.log.error( "Script Post Processor: An error has occurred while preparing script:\n%s", scriptFilename )
			
		else:
			hiero.core.log.error('Not overwriting script that currently exists!')
			
		# Nothing left to do, return False. <- of course this makes sense to do!
		return False
	
	#
	#
	# this function seems to do read nodes
	# 
	
	def writeTrackItemOriginalReadPath(self, script, firstFrame):
		""" Write the source track item to the script. """

		# Construct a TrackItemExportScriptWriter and write the track item
		writer = CustomTrackItemExportScriptWriter(self._item)
		writer.setAdditionalNodesCallback(self._buildAdditionalNodes)
		writer.setEffects(self.includeEffects(), self._effects)
		writer.setAnnotations(self.includeAnnotations(), self._annotations)

		# TODO This is being done in both the NukeShotExporter and TranscodeExporter.
		# There should be fully shared code for doing the handles calculations.
		fullClipLength = (self._cutHandles is None)
		if fullClipLength:
			writer.setOutputClipLength()
		else:
			writer.setOutputHandles(*self.outputHandles())

		writer.setIncludeRetimes(self._retime, self._preset.properties()["method"])
		writer.setReformat(self._preset.properties()["reformat"])
		writer.setFirstFrame(firstFrame)
		writer.writeToScript(script)

	#
	#
	# this function seems to do read nodes as well, but is unused in my testing
	# left here because finding the functions in the garbage hiero api is the hardest part

	'''
	def writeTrackItemCustomReadPaths(self, script, firstFrame):
		""" If other export items are selected as Read nodes, add those to the
			script.	This allows for e.g. using the output of the copy exporter as
			the path for the read node.

			Returns True if any read paths were set.
		"""

		# Note: Due to the way this is currently implemented, the script will be a
		# bit different using custom read nodes:
		# - No effects or annotations are included
		# - The output format will always be that of the source clip

		if not self._readTaskData:
			return False

		for task, _, _ in self._readTaskData:
			readNodePath = task.resolvedExportPath()
			itemStart, itemEnd = task.outputRange()
			itemFirstFrame = firstFrame
			if self._startFrame:
				itemFirstFrame = self._startFrame

			if hiero.core.isVideoFileExtension(os.path.splitext(readNodePath)[1].lower()):
				# Don't specify frame range when media is single file
				newSource = hiero.core.MediaSource(readNodePath)
				itemEnd = itemEnd - itemStart
				itemStart = 0
			else:
				# File is image sequence, so specify frame range
				newSource = hiero.core.MediaSource(readNodePath + (" %i-%i" % task.outputRange()))

			newClip = hiero.core.Clip(newSource, itemStart, itemEnd)

			if self._cutHandles is None:
				newClip.addToNukeScript(script,
											firstFrame=itemFirstFrame,
											trimmed=True,
											nodeLabel=self._item.parent().name(),
											additionalNodesCallback=self._buildAdditionalNodes,
											includeEffects=self.includeEffects())
			else:
				# Copy track item and replace source with new clip (which may be offline)
				newTrackItem = hiero.core.TrackItem(self._item.name(), self._item.mediaType())

				for tag in self._item.tags():
					newTrackItem.addTag(tag)

				# Handles may not be exactly what the user specified. They may be clamped to media range
				inHandle, outHandle = 0, 0
				if self._cutHandles:
					# Get the output range without handles
					inHandle, outHandle = task.outputHandles()
					hiero.core.log.debug( "in/outHandle %s %s", inHandle, outHandle )


				newTrackItem.setSource(newClip)

				# Set the new track item's timeline range
				newTrackItem.setTimelineIn(self._item.timelineIn())
				newTrackItem.setTimelineOut(self._item.timelineOut())

				# Set the new track item's source range.	This is the clip range less the handles.
				# So if the export is being done with, say, 10 frames of handles, the source in should be 10
				# (first frame of clip is always 0), and the source out should be (duration - 1 - 10) (there's
				# a 1 frame offset since the source out is the start of the last frame that should be read).
				newTrackItem.setSourceIn(inHandle)
				newTrackItem.setSourceOut((newClip.duration() -1 )- outHandle)

				# Add track item to nuke script
				newTrackItem.addToNukeScript(script,
												firstFrame=itemFirstFrame,
												includeRetimes=self._retime,
												retimeMethod=self._preset.properties()["method"],
												startHandle=self._cutHandles,
												endHandle=self._cutHandles,
												nodeLabel=self._item.parent().name(),
												additionalNodesCallback=self._buildAdditionalNodes,
												includeEffects=self.includeEffects())

		return True
		'''


	def _beforeNukeScriptWrite(self, script):
		""" Call-back method introduced to allow modifications of the script object before it is written to disk. 
		Note that this is a bit of a hack, please speak to the AssetMgrAPI team before improving it. """
		pass
	
#
# Sequence Writer
#   if you can believe it, i'm ONLY ADDING A DOT AFTER THE READS

class CustomSequenceScriptWriter(object):
	""" Class for writing Sequences to a Nuke script. """
	def __init__(self, sequence, params):
		self._sequence = sequence
		self._params = params

		self._trackWriters = []

	def writeToScript(self,
						script=nuke.ScriptWriter(),
						offset=0,
						skipOffline=True,
						mediaToSkip=(),
						disconnected=False,
						masterTrackItem=None,):

		added_nodes = []

		hiero.core.log.debug( '<'*10 + "Sequence.addToNukeScript()" + '>'*10 )
		previousTrack = None


		# First write the tracks in reverse order.	When it comes to detemining the inputs for the merges below,
		# Nuke uses a stack.	We also need to add each track's annotations and soft effects in the right place.
		# Effects/annotations on a track which also has clips should only apply to that track, so are added before the
		# track is merged.	Otherwise they should apply to all the tracks below, so are added after.
		# So for example if there are 4 tracks (Video 1, Video 2, Effects 1, Video 3) then the order is as follows:
		#	 Video 3
		#	 Video 3 annotations
		#	 Video 3 effects
		#	 Video 2
		#	 Video 2 annotations
		#	 Video 2 effects
		#	 Video 1
		#	 Video 1 annotations
		#	 Video 1 effects
		#	 Merge track 2 over track 1
		#	 Effects 1
		#	 Merge track 3 over track 2
		#	 Write

		# If there is an output format specified, to make sure effects and annotations appear in the right place,
		# they should have their 'cliptype' knob set to 'bbox'.
		effectsClipType = "bbox"

		tracksWithVideo = set()

		# If layout is disconnected, only the 'master' track is connected to the Write node, any others
		# will be placed in the script but with clips disconnected.	To make this work, connected tracks
		# needs to be written last, so re-order the list. Effects/annotations which apply to the master track
		# also need to be connected

		connectedTracks, disconnectedTracks = FnNukeHelpers.getConnectedDisconnectedTracks(self._sequence,
																																											 masterTrackItem,
																																											 disconnected,
																																											 self._params.includeEffects(),
																																											 self._params.includeAnnotations())
		tracks = connectedTracks + disconnectedTracks

		readNodeUsageCollator = FnNukeHelpersV2.ReadNodeUsageCollator()
		readNodeUsageCollator.collateReadNodes(tracks, self._params, offset)
		readNodes = readNodeUsageCollator.getReadNodes()

		# Keep a record of the last Node in each track, since this will be used later to set the 
		# correct connections to Merge nodes
		lastTrackNodeDict = {}

		# Keep a list of all LifeTime ranges of each track. This is the range Specified by the 
		# TimeClip nodes first and last knobs. 
		# We will also need to know the overall comp's start frame, so that we can disable
		# the Merge node over it's entire range initially
		lastLifetimeRange = {}
		firstCompFrame = None

		# Also keep track of Dot nodes created for tidying up the layout of A and
		# mask inputs, since we will be positioning these after the Merge node gets
		# its final aplacement
		maskInputDict = {}
		AInputDict = {}

		# Keep track of whether all TrackItems are disabled for a track
		trackDisabled = {}

		# Check all tracks for soft effect tracks
		hasSoftEffectTracks = False
		for track in tracks:
			trackItems = track.items()
			subTrackItems = track.subTrackItems()
			if len(trackItems) is 0 and len(subTrackItems) > 0:
				# Soft effect tracks if track only contains sub track items
				hasSoftEffectTracks = True


		# First write out the tracks and their annotations in reverse order, as described above
		for track in reversed(tracks):
			trackDisconnected = track in disconnectedTracks
			# If the track has any clips, write them and the effects out.
			trackItems = track.items()
			if len(trackItems) > 0:
				# Add the track and whether it is disconnected as data to the layout context
				script.pushLayoutContext("track", track.name(), track=track, disconnected=trackDisconnected)

				# Check if we'll need to add an AddChannels node to each track item in this track
				addChannelNode = not (track == tracks[0]) and not trackDisconnected and not track.isBlendEnabled()
				trackWriter = FnNukeHelpersV2.VideoTrackScriptWriter(track, self._params)

				self._trackWriters.append(trackWriter)

				track_nodes = trackWriter.writeToScript(script,
														offset=offset,
														skipOffline=skipOffline,
														mediaToSkip=mediaToSkip,
														disconnected=trackDisconnected,
														needToAddChannelNode=addChannelNode,
														readNodes = readNodes)

				# Traverse the track nodes to find all Timeclip nodes. 
				# When we find one, use it to define that TrackItem's lifetime. 
				# This will later be written to the Merge.
				for node in track_nodes:
					if isinstance(node, nuke.TimeClipNode):
						if not track in lastLifetimeRange:
							lastLifetimeRange[track] = []
						startFrame = node.knob("first")
						endFrame = node.knob("last")

						if firstCompFrame is None or startFrame < firstCompFrame:
							firstCompFrame = startFrame

						#check if the clip is disabled
						shouldAddLifetime = True
						if str("disable") in node.knobs():
							shouldAddLifetime =	not node.knob("disable")

						if shouldAddLifetime:
							lastLifetimeRange[track].append((startFrame, endFrame))

				added_nodes = added_nodes + track_nodes

				effectsAnnotationsNodes = FnNukeHelpers._addEffectsAnnotationsForTrack(track,
																						self._params.includeEffects(),
																						self._params.includeAnnotations(),
																						script,
																						offset,
																						cliptype=effectsClipType)
				added_nodes.extend( effectsAnnotationsNodes )

				# Check whether every track item is disabled on this track
				trackDisabled[track] = trackWriter.allTrackItemsDisabled()

				# If all track items are disabled, we should also disable all effects
				# and annotations nodes
				if trackDisabled[track]:
					for node in effectsAnnotationsNodes:
						node.setKnob("disable", "true")


					# Add a constant node to ensure we're always passing channels through.
					# It's range should be the super-range of all contained clips.
					firstFrame, lastFrame = 0, 0
					if track in lastLifetimeRange and len(lastLifetimeRange[track]) > 0:
						firstFrame, lastFrame = lastLifetimeRange[track][0]
						for start, end in lastLifetimeRange[track]:
							if start < firstFrame:
								firstFrame = start
							if end > lastFrame:
								lastFrame = end
					
					constant = nuke.ConstantNode(firstFrame, lastFrame, channels="rgb")
					added_nodes.append(constant)
					script.addNode(constant)

				shouldAddBlackOutside = hasSoftEffectTracks and track.isBlendEnabled() and not trackDisconnected
				if shouldAddBlackOutside:
					# We will be merging this track later and we need to make sure we have black outside so that
					# subsequent transform effects work correctly.
					blackOutside = nuke.Node("BlackOutside")
					script.addNode(blackOutside)
					added_nodes.append(blackOutside)

				tracksWithVideo.add(track)

				# Check if we will be adding a merge node here later. If so, this would be the A input and 
				# we will need a dot node to connect between this and the Merge
				
				dot = nuke.DotNode()
				# Set the dot node's input so we can properly align it after laying out the associated Merge node
				dot.setInputNode(0, added_nodes[-1])
				dot.setName("DOT_"+track.name())
				script.addNode(dot)
				added_nodes.append(dot)
				
				if track != tracks[0] and not trackDisconnected:

					# If the next item will be a Merge node, and blendMask is enabled, 
					# we'll need a set and push here, as well as additional Dot nodes 
					# to join everything up nicely.
					if track.isBlendMaskEnabled(): 
						# Add a dot for the mask input
						dotA = nuke.DotNode()
						script.addNode(dotA)
						added_nodes.append(dotA)

						AInputDict[track] = dotA

						# Construct a unique label for the set/push. 
						commandLabel = "Mask_" + str(tracks.index(track))

						# Add the set command
						setCommand = nuke.SetNode(commandLabel, 0)
						script.addNode(setCommand)
						added_nodes.append(setCommand)

						# Add a dot command to bring together the A and mask inputs
						dotMask = nuke.DotNode()
						script.addNode(dotMask)
						added_nodes.append(dotMask)

						#Add a set command so that we can back to this dot for the merge mask input
						dotMaskSetNode = nuke.SetNode(trackWriter.getMaskJumpName(), 0)
						script.addNode(dotMaskSetNode)
						added_nodes.append(dotMaskSetNode)

						maskInputDict[track] = dotMask

						# Add the push command
						pushCommand = nuke.PushNode(commandLabel)
						script.addNode(pushCommand)
						added_nodes.append(pushCommand)

						lastTrackNodeDict[track] = dot

				# Add a set node to the end of the track
				setNode = nuke.SetNode(trackWriter.getJumpName(), 0)
				added_nodes.append(setNode)
				script.addNode(setNode)

				script.popLayoutContext()

			elif trackDisconnected:
				script.pushLayoutContext("track", track.name(), track=track, disconnected=trackDisconnected)

				added_nodes.extend( FnNukeHelpers._addEffectsAnnotationsForTrack(track,
																					self._params.includeEffects(),
																					self._params.includeAnnotations(),
																					script,
																					offset,
																					inputs=0,
																					cliptype=effectsClipType) )
				script.popLayoutContext()


			# Store the last node added to this track
			if not track in lastTrackNodeDict and len(added_nodes) > 0:
				# Get the last non-tcl command Node added
				for node in reversed(added_nodes):
					lastTrackNodeDict[track] = node
					if node.isNode(): 
						break

		# Now iterate over the tracks in order, writing merges and their soft effects
		previousTrack = None
		for track in tracks:
			trackDisconnected = track in disconnectedTracks

			if not trackDisconnected and previousTrack:
				# We need a merge if this track contains any clips
				if track in tracksWithVideo:
					merge = nuke.MergeNode()
					if track.isBlendEnabled():
						blendMode = track.blendMode()
						merge.setKnob('operation', blendMode )

						# For a blend track, use 'All' for metadata which means the B input
						# is copied over A
						merge.setKnob('metainput', 'All')

						# For blend track, we want to output the bbox to be the union of A and B
						merge.setKnob('bbox', 'union')

						# will this node need to connect to its mask input to its A input?
						if track.isBlendMaskEnabled():
							# The correct command in the nuke script should be:
							#		inputs 2+1
							# However we need to use quotes here to stop the 2nd parameter being 
							# evaluated as 3. This will be special cased in the Script contruction
							# later.
							merge.setKnob("inputs", "2+1")
							merge.setDotInputs(AInputDict[track], maskInputDict[track])

					else:
						# For non-blend track, we want to output the metadata from the A input
						merge.setKnob('metainput', 'A')

						# For non-blend track, we want to output the bbox from the A input
						merge.setKnob('bbox', 'A')

						# This Merge node should use the custom alpha channel created on the A input track
						merge.setKnob('Achannels', '{rgba.red rgba.green rgba.blue Track_Alpha.a}')
					if previousTrack:
						merge.setKnob( 'label', track.name()+' over '+previousTrack.name() )


						# Set the Merge's inputs, so we can use them to properly position the Merge later.
						if track in lastTrackNodeDict:
							merge.setInputNode(0, lastTrackNodeDict[track])
						if previousTrack in lastTrackNodeDict:
							merge.setInputNode(1, lastTrackNodeDict[previousTrack])

						# Any subsequent Merges will be connected to this one, so update the last Node in the track.
						lastTrackNodeDict[track] = merge					
					else:
						merge.setKnob( 'label', track.name() )

					# If all items from the track are disabled, also fully disable the Merge Node
					if track in trackDisabled and trackDisabled[track] == True:
						merge.setKnob("disable", "true")
					elif track in lastLifetimeRange:
						# Animate the Merge node's disable knob over each lifetime on the track
						for start, end in lastLifetimeRange[track]:
							merge.addEnabledRange(start, end, firstCompFrame)

					script.pushLayoutContext("merge", "Merge " + previousTrack.name() + " " + track.name(), track=previousTrack, inputA=track, inputB=previousTrack)

					inputAWriter = None
					inputBWriter = None
					for writer in self._trackWriters:
						if writer._track == track:
							inputAWriter = writer
						if writer._track == previousTrack:
							inputBWriter = writer

					#Add pushes for inputs
					if track.isBlendMaskEnabled():
						# Push for the mask input
						pushMaskNode = nuke.PushNode(inputAWriter.getMaskJumpName())
						added_nodes.append(pushMaskNode)
						script.addNode(pushMaskNode)

					pushANode = nuke.PushNode(inputAWriter.getJumpName())
					added_nodes.append(pushANode)
					script.addNode(pushANode)

					pushBNode = nuke.PushNode(inputBWriter.getJumpName())
					added_nodes.append(pushBNode)
					script.addNode(pushBNode)

					script.addNode(merge)
					added_nodes.append(merge)

					#Add a set for the merge because this merge should replace the track
					mergeJumpName = inputAWriter.getJumpName() + "Merge"
					mergeSetNode = nuke.SetNode(mergeJumpName, 0)
					added_nodes.append(mergeSetNode)
					script.addNode(mergeSetNode)
					inputAWriter.setJumpName(mergeJumpName)

					script.popLayoutContext()
				# If there were no clips on the track, write the effects and annotations after the merge so they get applied to the tracks below
				else:
					script.pushLayoutContext("effectsTrack", track.name(), track=track, disconnected=trackDisconnected)

					effectInputs = 1
					if trackDisconnected:
						effectInputs = 0

					extendedNodes = FnNukeHelpers._addEffectsAnnotationsForTrack(track,
																					self._params.includeEffects(),
																					self._params.includeAnnotations(),
																					script,
																					offset,
																					inputs=effectInputs,
																					cliptype=effectsClipType)

					if extendedNodes:
						added_nodes.extend( extendedNodes )

						# We need to make sure that effects and annotations are aligned under the main comp branch
						if previousTrack and previousTrack in lastTrackNodeDict:
							previousNode = None
							for node in extendedNodes:
								if previousNode is None:
									inputNode = lastTrackNodeDict[previousTrack]
								else:
									inputNode = previousNode
									lastTrackNodeDict[track] = node
								
								node.setInputNode(0, inputNode)
								previousNode = node

					# Add the effects jump
					effectsJump = FnNukeHelpersV2.EffectsTrackJump(track)
					effectsSetNode = nuke.SetNode(effectsJump.getJumpName(), 0)
					added_nodes.append(effectsSetNode)
					script.addNode(effectsSetNode)
					self._trackWriters.append(effectsJump)

					script.popLayoutContext() # effectsTrack

			previousTrack = track

		# Add any additional nodes.
		perSequenceNodes = self._params.doAdditionalNodesCallback(self._sequence)
		for node in perSequenceNodes:
			if node is not None:
				added_nodes.append(node)
				script.addNode(node)

		return added_nodes
	
#
#
# This class calls TrackItemScriptWriter, which handles writing the read nodes
# believe it or not, we're copying all this code just to name the read node when it's made
#


class CustomTrackItemExportScriptWriter(TrackItemExportScriptWriter):
	""" Helper class for writing TrackItems to a Nuke script. This provides a
		higher-level wrapper around the code in FnNukeHelpers/FnNukeHelpersV2.
		TODO Could probably be got rid of with some refactoring.
	"""

	def __init__(self, trackItem):
		
		#passed a trackItem
		
		TrackItemExportScriptWriter.__init__(self, trackItem)
		
		#track name seems to be None here for some reason, maybe the item has been removed from the track?
		self._track=trackItem.parent()
		self._trackName=self._track.name()
		


	def setFirstFrame(self, firstFrame):
		""" Set the first frame of the script.	This is used to apply appropriate
		offsets to the written nodes.
		"""
		self._firstFrame = firstFrame


	def writeToScript(self, script):
		# For the moment, if annotations are being written, fall back to the old
		# code path
		if self._writeAnnotations:
			self.writeToScript_old(script)
			return

		retimeMethod = self._retimeMethod if self._includeRetimes else None
		scriptParameters = FnNukeHelpersV2.ScriptWriteParameters(includeAnnotations=self._writeAnnotations,
																	includeEffects=self._writeEffects,
																	retimeMethod=retimeMethod,
																	reformatMethod=self._reformatProperties,
																	additionalNodesCallback=self._additionalNodesCallback)
		
		additionalEffects = self._sequenceEffects if self._writeEffects else []
		
		writer = CustomTrackItemScriptWriter(self._trackItem, 
												scriptParameters,													 
												firstFrame=self._firstFrame,
												startHandle=self._startHandle,
												endHandle=self._endHandle)
		writer.writeToScript(script,
								nodeLabel=self._trackItem.parent().name(),
								additionalEffects=additionalEffects,
								addTimeClip = False,
								trackName=self._trackName)
		
#
#
# This class creates read nodes and related nodes (reformat, retime, etc)
#
#
		
class CustomTrackItemScriptWriter(FnNukeHelpersV2.TrackItemScriptWriter):
	""" Class for writing TrackItems to a Nuke script. """
	
	def __init__(self, trackItem, params, firstFrame=None, startHandle=0, endHandle=0, offset=0):
		"""
			@param firstFrame: optional frame for the Read node to start at
			@param startHandle: the number of frames of handles to include at the start
			@param endHandle: the number of frames of handles to include at the end
			@param offset: global frame offset applied across whole script
		"""
		
		FnNukeHelpersV2.TrackItemScriptWriter.__init__(self, trackItem, params, firstFrame, startHandle, endHandle, offset)
		
	def writeToScript(self,
						script=nuke.ScriptWriter(),
						nodeLabel=None,
						additionalEffects=(),
						addChannelNode = False,
						readNodes = {},
						addTimeClip = True,
						trackName=None):
		
		""" Writes the TrackItem to a script. Returns the added nodes.
			@param script: the script writer to add nodes to
			@param nodeLabel: label for the Read node
			@param additionalEffects: unlinked effects on the sequence which should be included
			@param addChannelNode: add an AddChannels Node to the TrackItem, which will
									inject a full alpha channel to Node tree
		"""
		added_nodes = []

		clip = self._trackItem.source()
		hiero.core.log.debug("CustomTrackItemScriptWriter clip: "+str(clip))
		hiero.core.log.debug("CustomTrackItemScriptWriter _trackItem: "+str(self._trackItem))
		hiero.core.log.debug("CustomTrackItemScriptWriter _trackItem.parent: "+str(self._trackItem.parent()))
		hiero.core.log.debug("CustomTrackItemScriptWriter _trackItem.parent.name(): "+str(self._trackItem.parent().name()))
		trackName=self._trackItem.parent().name()

		# Create a metadata node
		metadataNode = nuke.MetadataNode()

		# Add TrackItem metadata to node
		metadataNode.addMetadata([("hiero/shot", self._trackItem.name()), ("hiero/shot_guid", FnNukeHelpers._guidFromCopyTag(self._trackItem))])

		# sequence level metadata
		seq = self._trackItem.parentSequence()
		if seq:
			seqTimecodeStart = seq.timecodeStart()
			seqTimecodeFrame = seqTimecodeStart + self._trackItem.timelineIn() - self._outputStartHandle
			seqTimecode = hiero.core.Timecode.timeToString(seqTimecodeFrame, seq.framerate(), hiero.core.Timecode.kDisplayTimecode)

			metadataNode.addMetadata( [ ("hiero/project", clip.project().name() ),
										("hiero/sequence/frame_rate", seq.framerate() ),
										("hiero/sequence/timecode", "[make_timecode %s %s %d]" % (seqTimecode, str(seq.framerate()), self._first_frame) )
											] )

		# Add Tags to metadata
		metadataNode.addMetadataFromTags( self._trackItem.tags() )

		# Add Track and Sequence here as these metadata nodes are going to be added per clip/track item. Not per sequence or track.
		if self._trackItem.parent():
			metadataNode.addMetadata([("hiero/track", self._trackItem.parent().name()), ("hiero/track_guid", FnNukeHelpers._guidFromCopyTag(self._trackItem.parent()))])
			if self._trackItem.parentSequence():
				metadataNode.addMetadata([("hiero/sequence", self._trackItem.parentSequence().name()), ("hiero/sequence_guid", FnNukeHelpers._guidFromCopyTag(self._trackItem.parentSequence()))])

		# Capture the clip nodes without adding to the script, so that we can group them as necessary
		clip_nodes = clip.addToNukeScript(None,
											firstFrame=self._readNodeFirstFrame,
											metadataNode=metadataNode,
											nodeLabel=nodeLabel,
											enabled=self._trackItem.isEnabled(),
											includeEffects=self._params.includeEffects(),
											readNodes = readNodes,
											trackName = trackName)

		# Add the read node to the script
		# This assumes the read node will be the first node
		lastReadAssociatedNode = 0
		read_node = clip_nodes[0]

		if isinstance(read_node, nuke.PushNode):
			# Push nodes come before PostageStamps, to connect the PostageStamp to its original Read.
			# Need to add the Push command first
			if script:
				script.addNode(read_node)
			added_nodes.append(read_node)

			# Get the actual PostageStamp
			read_node = clip_nodes[1]
			lastReadAssociatedNode += 1

		# Add the read or postage stamp node
		if script:
			script.addNode(read_node)
		added_nodes.append(read_node)

		# If it's a Read, Add the next 2 nodes also, which represent set and push nodes
		if readNodes is not None and len(readNodes) > 0 and isinstance(read_node, nuke.ReadNode):
			if lastReadAssociatedNode < len(clip_nodes) - 2:
				setNode = clip_nodes[lastReadAssociatedNode + 1]
				pushNode = clip_nodes[lastReadAssociatedNode + 2]

				if isinstance(setNode, nuke.SetNode) and isinstance(pushNode, nuke.PushNode):
					if script:
						script.addNode(setNode)
						script.addNode(pushNode)
					added_nodes.append(setNode)
					added_nodes.append(pushNode)
					lastReadAssociatedNode += 2
		elif isinstance(read_node, nuke.PostageStampNode):
			# For PostageStamps, the TimeOffset should immediately follow the Node itself
			timeOffsetNode = clip_nodes[lastReadAssociatedNode + 1]

			if script:
				script.addNode(timeOffsetNode)
			added_nodes.append(timeOffsetNode)
			lastReadAssociatedNode += 1

		if self._params.includeAnnotations():
			# Add the clip annotations.	This goes immediately after the Read, so it is affected by the Reformat if there is one
			clipAnnotations = clip.addAnnotationsToNukeScript(script, firstFrame=self._readNodeFirstFrame, trimmed=True, trimStart=self._readStart, trimEnd=self._readEnd)
			added_nodes.extend(clipAnnotations)

		added_nodes.extend( clip_nodes[lastReadAssociatedNode + 1:] )
		# Add all other clip nodes to the group
		for node in clip_nodes[lastReadAssociatedNode + 1:]:
			script.addNode(node)

		# Add metadata node
		added_nodes.append(metadataNode)
		script.addNode(metadataNode)

		# This parameter allow the whole nuke script to be shifted by a number of frames
		self._first_frame += self._offset
		self._last_frame += self._offset

		# Add Additional nodes.
		postReadNodes = self._params.doAdditionalNodesCallback(self._trackItem)

		# Add any additional nodes.
		for node in postReadNodes:
			if node is not None:
				node = copy.deepcopy(node)
				# Disable additional nodes too
				if not self._trackItem.isEnabled():
					node.setKnob("disable", True)

				added_nodes.append(node)
				script.addNode(node)

		# If this clip is a freeze frame add a frame hold node
		isFreezeFrame = (self._retimeRate == 0.0)
		if isFreezeFrame:
			# first_frame is max of first_frame and readNodeFirstFrame because when
			# using a dissolve with a still clip first_frame is the first frame of 2
			# clips, which is lower than readNodeFirstFrame.
			holdFirstFrame = max(self._first_frame, self._readNodeFirstFrame)
			frameHoldNode = nuke.Node("FrameHold", first_frame=holdFirstFrame)
			added_nodes.append(frameHoldNode)
			script.addNode(frameHoldNode)

		# If the clip is retimed we need to also add an OFlow node.
		elif self._params.includeRetimes() and self._retimeRate != 1 and self._params.retimeMethod() != 'None':

			# Obtain keyFrames
			tIn, tOut = self._trackItem.timelineIn(), self._trackItem.timelineOut()
			sIn, sOut = self._trackItem.sourceIn(), FnNukeHelpers.getRetimeSourceOut(self._trackItem)

			# Offset keyFrames, so that they match the input range (source times) and produce expected output range (timeline times)
			# timeline values must start at first_frame
			tOffset = (self._first_frame + self._startHandle + self._inTransitionHandle) - self._trackItem.timelineIn()
			tIn += tOffset
			tOut += tOffset
			sOffset = self._readNodeFirstFrame
			sIn += sOffset
			sOut += sOffset

			# Create OFlow node for computed keyFrames
			keyFrames = "{{curve l x%d %f x%d %f}}" % (tIn, sIn, tOut, sOut)
			oflow = nuke.Node("OFlow2",
												interpolation=self._params.retimeMethod(),
												timing="Source Frame",
												timingFrame=keyFrames)
			oflow.setKnob('label', 'retime ' + str(self._retimeRate))
			added_nodes.append(oflow)
			script.addNode(oflow)

		added_nodes.extend( self.writeReformatAndEffects(script, additionalEffects) )

		# TimeClip is used to correct the range from OFlow. This isn't necessary
		# when exporting a single shot, and was causing problems with retimes, so only
		# add it if requested
		if addTimeClip:
			timeClipNode = nuke.TimeClipNode( self._first_frame, self._last_frame, clip.sourceIn(), clip.sourceOut(), self._first_frame)
			timeClipNode.setKnob('label', 'Set frame range to [knob first] - [knob last]')
			added_nodes.append(timeClipNode)
			script.addNode(timeClipNode)

		# Add any AddChannels nodes and Layers commands
		if addChannelNode:
			self.addChannelNodeToScript(script, added_nodes)

		# Disable all clip nodes if Track Item is disabled
		if not self._trackItem.isEnabled():
			for node in added_nodes:
				node.setKnob("disable", "true")

		return added_nodes
	
#
#
#
# Here we are, nearly 5 classes/functions down the tree, and we are finally where read nodes are made

def _Custom_Clip_addToNukeScript(self,
							script,
							additionalNodes=None,
							additionalNodesCallback=None,
							firstFrame=None,
							trimmed=True,
							trimStart=None,
							trimEnd=None,
							colourTransform=None,
							metadataNode=None,
							includeMetadataNode=True,
							nodeLabel=None,
							enabled=True,
							includeEffects=True,
							beforeBehaviour=None,
							afterBehaviour=None,
							project = None,
							readNodes = {},
							trackName = None):
	"""addToNukeScript(self, script, trimmed=True, trimStart=None, trimEnd=None)

		Add a Read node to the Nuke script for each media sequence/file used in this clip. If there is no media, nothing is added.

		@param script: Nuke script object to add nodes
		@param additionalNodes: List of nodes to be added post read
		@param additionalNodesCallback: callback to allow custom additional node per item function([Clip|TrackItem|Track|Sequence])
		@param firstFrame: Custom offset to move start frame of clip
		@param trimmed: If True, a TimeClip node will be added to trim the range output by the Read node. The range defaults to the clip's soft trim range. If soft trims are not enabled on the clip, the range defaults to the clip range. The range can be overridden by passing trimStart and/or trimEnd values.
		@param trimStart: Override the trim range start with this value.
		@param trimEnd: Override the trim range end with this value.
		@param colourTransform: if specified, is set as the color transform for the clip
		@param metadataNode: node containing metadata to be inserted into the script
		@param includeMetadataNode: specifies whether a metadata node should be added to the script
		@param nodeLabel: optional label for the Read node
		@param enabled: enabled status of the read node. True by default
		@param includeEffects: if True, soft effects in the clip are included
		@param beforeBehaviour: What to do for frames before the first ([hold|loop|bounce|black])
		@param afterBehaviour: What to do for frames after the last ([hold|loop|bounce|black]) 
		@param trackName: name of the source track for the read node (for labeleing)
	"""

	hiero.core.log.debug( "trimmed=%s, trimStart=%s, trimEnd=%s, firstFrame=%s" % (str(trimmed), str(trimStart), str(trimEnd), str(firstFrame)) )
	# Check that we are on the right type of object, just to be safe.
	assert isinstance(self, Clip), "This function can only be punched into a Clip object."

	added_nodes = []

	source = self.mediaSource()

	if source is None:
		# TODO: Add a constant here so that offline media has some representation within the nuke scene.
		# For now just do nothing
		return added_nodes

	# MPLEC TODO
	# Currently, on ingest only one source media element is added to the Clip timeline.
	# However it is possible for the Clip timeline to contain multiple track items.
	# We don't currently allow other source media to be added (though stereo will do this)
	# but users can cut/trim/etc on the one that's there so this needs to be smarter.
	# It will need to do the same thing as the timeline build-out does, with multiple
	# tracks, AppendClips, gap filling -- the whole routine. Should be able to share that?
	for fi in source.fileinfos():

		# Get start frame. First frame of an image sequence. Zero if quicktime/r3d
		startFrame = self.sourceIn()
		hiero.core.log.debug( "startFrame: " + str(startFrame) )

		start, end = FnNukeHelpers._Clip_getStartEndFrames(self, firstFrame, trimmed, trimStart, trimEnd)

		# Grab clip format
		format = self.format()
		clipMetadata = self.metadata()

		hiero.core.log.debug( "- adding Nuke node for:%s %s %s", fi.filename(), start, end )
		isRead = False
		isPostageStamp = False

		readFilename = fi.filename()

		# When writing a clip which points to an nk script, we can't just add a Read
		# node with the nk as path.
		# For an nk clip, try to find the metadata for the write path, and use that
		# in the Read node.	This should be present, it's set by nkReader.	If it's
		# not, CompSourceInfo will throw an exception, fall back to using a Precomp
		# just in case
		try:
			compInfo = FnNukeHelpers.CompSourceInfo(self)
			if compInfo.isComp():
				# Change the readFilename to point to the nk script render path
				readFilename = compInfo.writePath
		except RuntimeError:
			if isNukeScript(readFilename):
				# Create a Precomp node and reset readFilename to prevent a Read node
				# being created below
				readFilename = None
				read_node = nuke.PrecompNode( fi.filename() )

		# If there is a read filename, create a Read node
		if readFilename:
			# First check if we want to create a PostageStamp or Read node
			readInfoKey = FnNukeHelpers._Clip_readInfoKey(self, readFilename)
			if enabled and readInfoKey in readNodes:
				readInfo = readNodes[readInfoKey]

				# Increment the usage
				readInfo.instancesUsed += 1
			else:
				readInfo = None

			# Only create a Read Node if this is the only usage of this filename, or this 
			# is the last usage
			isPostageStamp = readInfo is not None and readInfo.instancesUsed < readInfo.totalInstances

			if isPostageStamp:
				# We will need a push command to connect it its Read Node
				pushCommandID = readInfo.readNodeID + "_" + str(readInfo.totalInstances)
				pushCommand = nuke.PushNode(pushCommandID)
				if script is not None:
					script.addNode(pushCommand)
				added_nodes.append(pushCommand)

				read_node = nuke.PostageStampNode()
			else:
				read_node = nuke.ReadNode(readFilename,
											format.width(),
											format.height(),
											format.pixelAspect(),
											round(start),
											round(end),
											clipMetadata=clipMetadata)
				#FINALLY!
				#name the read node
				if trackName:
					read_node.setName(str(trackName))
				
				read_node.setKnob("localizationPolicy", FnNukeHelpers.localisationMap[self.localizationPolicy()] )

				if firstFrame is not None:
					read_node.setKnob("frame_mode", 'start at')
					read_node.setKnob("frame", firstFrame)
				
				if beforeBehaviour is not None:
					read_node.setKnob("before", beforeBehaviour)
				if afterBehaviour is not None:
					read_node.setKnob("after", afterBehaviour)

				# Add the knobs from the clip's own Read node
				FnNukeHelpers._Clip_addReadNodeKnobs(self, read_node)

				isRead = True


		# If a node name has been specified
		if nodeLabel is not None:
			read_node.setKnob("label", nodeLabel)

		if script is not None:
			script.addNode(read_node)
		added_nodes.append(read_node)

		if readInfo:
			if isRead:
				# We'll need a set and a push command, so that the script can be reordered later to put all 
				# the Read and associated Set commands to the top. The Push commands will stay 
				# where they are so that Nodes will connect up properly afterwards
				if enabled:
					setCommandID = readInfo.readNodeID + "_" + str(readInfo.totalInstances)
				else:
					setCommandID = readInfo.readNodeID + "_disabled"

				setCommand = nuke.SetNode(setCommandID, 0)
				pushCommand = nuke.PushNode(setCommandID)
				if script is not None:
					script.addNode(setCommand)
					script.addNode(pushCommand)
				added_nodes.append(setCommand)
				added_nodes.append(pushCommand)
			elif isPostageStamp:
				# If it's a postage stamp node, we'll also need a time offset to correct the Frame Range
				# relative to the original read
				originalFirstFrame = readInfo.startAt
				if originalFirstFrame is not None:
					# There's a slight difference between how frame ranges are handled by Read Nodes
					# and TimeOffset's in Nuke, and the information we pass.
					# Ideally, the Timeoffset would work entirely in floating point, but it, and its interface,
					# don't. We have added the dtime_offset as a workaround for this, but there's an additional
					# problem that the Read Node's original range (originalFirstFrame here) gets cast to int
					# before getting through to Timeoffset.
					# This means that Timeoffset cannot properly process the range because the fractional part
					# of originalFirstFrame has already been lost. We compensate for that here, by adding the 
					# fractional part to the Timeoffset value.
					fractpart, intpart = math.modf(originalFirstFrame)
					if fractpart is None:
						fractpart = 0
					timeOffset = nuke.TimeOffsetNode(firstFrame - originalFirstFrame + fractpart)
					if script is not None:
						script.addNode(timeOffset)
					added_nodes.append(timeOffset)

		if not isRead and not isPostageStamp and firstFrame is not None:

			timeClip = nuke.TimeClipNode( round(start), round(end), start, end, round(firstFrame) )
			added_nodes.append( timeClip )

		if not enabled:
			read_node.setKnob("disable", True)

		if includeMetadataNode:
			if metadataNode is None:
				metadataNode = nuke.MetadataNode()
				if script is not None:
					script.addNode(metadataNode)
				added_nodes.append(metadataNode)
				metadataNode.setInputNode(0, read_node)

			metadataNode.addMetadata([("hiero/clip", self.name())])
			# Also set the reel name (if any) on the metadata key the dpx writer expects for this.
			if Keys.kSourceReelId in clipMetadata:
				reel = clipMetadata[Keys.kSourceReelId]
				if len(reel):
					metadataNode.addMetadata( [ ("hiero/reel", reel), ('dpx/input_device', reel), ('quicktime/reel', reel) ] )

			# Add Tags to metadata
			metadataNode.addMetadataFromTags( self.tags() )

		if includeEffects:
			# Add clip internal soft effects
			# We need to offset the frame range of the effects from clip time into the output time.
			if firstFrame is not None:
				effectOffset = firstFrame + startFrame - start
			else:
				effectOffset = startFrame

			effects = [ item for item in itertools.chain( *itertools.chain(*self.subTrackItems()) ) if isinstance(item, EffectTrackItem) ]
			hiero.core.log.info("Clip.addToNukeScript effects %s %s" % (effects, self.subTrackItems()))
			for effect in reversed(effects):
				added_nodes.extend( effect.addToNukeScript(script, effectOffset) )

		postReadNodes = []
		if callable(additionalNodesCallback):
			postReadNodes.extend(additionalNodesCallback(self))

		if additionalNodes is not None:
			postReadNodes.extend(additionalNodes)

		if includeMetadataNode:
			prevNode = metadataNode
		else:
			prevNode = read_node

		for node in postReadNodes:
			# Add additional nodes
			if node is not None:
				node = copy.deepcopy(node)
				node.setInputNode(0, prevNode)
				prevNode = node

				# Disable additional nodes too
				if not enabled:
					node.setKnob("disable", "true")

				added_nodes.append(node)
				if script is not None:
					script.addNode(node)

	return added_nodes

#replace internal Clip addToNukeScriptFunction with this one
Clip.addToNukeScript = _Custom_Clip_addToNukeScript
#
