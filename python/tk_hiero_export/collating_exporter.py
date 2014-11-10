# Copyright (c) 2013 Shotgun Software Inc.
#
# CONFIDENTIAL AND PROPRIETARY
#
# This work is provided "AS IS" and subject to the Shotgun Pipeline Toolkit
# Source Code License included in this distribution package. See LICENSE.
# By accessing, using, copying or modifying this work you indicate your
# agreement to the Shotgun Pipeline Toolkit Source Code License. All rights
# not expressly granted therein are reserved by Shotgun Software Inc.

import sys
import math

import hiero
from random import randrange

class CollatingExporter(object):
    def __init__(self, properties=None):
        super(CollatingExporter, self).__init__()

        # When building a collated sequence, everything is offset by 1000
        # This gives head room for shots which may go negative when transposed to a
        # custom start frame. This offset should be negated during script generation.
        self.HEAD_ROOM_OFFSET = 1000

        self._parentSequence = None
        self._collate = False
        self._hero = False
        self._heroItem = False
        self._collatedItemsMap = {}

        if properties is None:
            properties = self._preset.properties()

        if isinstance(self._item, hiero.core.TrackItem):
            # Build list of collated shots
            self._collatedItems = self._collatedItems(properties)

            # Only build sequence if there are multiple shots
            if len(self._collatedItems) > 1:
                self._collate = True
                # Build the sequence of collated shots
                self._buildCollatedSequence(properties)

    def _offsetTimelineLinked(self, trackItem, offset):
        """
        Offset timeline for trackitem and it's linked audio items (since each video track is processed separately)
        """
        trackItem.setTimelineOut(trackItem.timelineOut() + offset)
        trackItem.setTimelineIn(trackItem.timelineIn() + offset)

        for item in trackItem.linkedItems():
            if item.mediaType() is hiero.core.TrackItem.MediaType.kAudio:
                item.setTimelineOut(item.timelineOut() + offset)
                item.setTimelineIn(item.timelineIn() + offset)

    def _trimInLinked(self, trackitem, value):
        """
        Trim In trackitem and it's linked audio items (since each video track is processed separately)
        """
        trackitem.trimIn(value)
        for item in trackitem.linkedItems(): 
            if item.mediaType() is hiero.core.TrackItem.MediaType.kAudio:
                item.trimIn(value)

    def _trimOutLinked(self, trackitem, value):
        """
        Trim Out trackitem and it's linked audio items (since each video track is processed separately)
        """
        trackitem.trimOut(value)
        for item in trackitem.linkedItems(): 
            if item.mediaType() is hiero.core.TrackItem.MediaType.kAudio:
                item.trimOut(value)

    def _collatedItems(self, properties):
        """
        Build and return list of collated shots, the CollateTracks option includes overlapping and identically named shots.
        CollateSequence Option includes all shots in parent sequence.
        """
        collatedItems = []

        collateTime = properties["collateTracks"]
        collateName = properties["collateShotNames"]

        if properties["collateSequence"]:
            # Add all trackitems to collate list
            for track in self._sequence.videoTracks():
                for trackitem in track:
                    collatedItems.append(trackitem)

        elif collateName or collateTime:
            nameMatches = [self._item]
            orderedMatches = []

            if collateName:
                # The collate tracks option will detect any trackitems on other tracks which overlap
                # so they can be included in the nuke script.
                for track in self._sequence.videoTracks():
                    for trackitem in track:
                        if trackitem is not self._item:
                            # Collate if shot name matches.
                            if trackitem.name() == self._item.name():
                                nameMatches.append(trackitem)
                                continue
            for track in self._sequence.videoTracks():
                for trackitem in track:
                    for nameMatchTrackItem in nameMatches:
                        if collateTime:
                            # Starts before or at same time
                            if trackitem.timelineIn() <= nameMatchTrackItem.timelineIn():
                                # finishes after start
                                if trackitem.timelineOut() >= nameMatchTrackItem.timelineIn():
                                    orderedMatches.append(trackitem)
                                    break
                            elif trackitem.timelineIn() > nameMatchTrackItem.timelineIn():
                                # Starts before end
                                if trackitem.timelineIn() < nameMatchTrackItem.timelineOut():
                                    orderedMatches.append(trackitem)
                                    break
                        elif trackitem == nameMatchTrackItem:
                            orderedMatches.append(trackitem)
                            break
            collatedItems = orderedMatches
        return collatedItems

    def _buildCollatedSequence(self, properties):
        """From the list of collated Items build a sequence, extend edge shots for handles, offset relative to custom start or master shot source frame"""
        if not self._collate or not self._collatedItems:
            return

        # Hero item for a collated sequence is the first one on the highest track
        def keyFunc(item):
            return ((sys.maxint - item.timelineIn()) * 1000) + item.parent().trackIndex()
        heroItem = max(self._collatedItems, key=keyFunc)
        self._hero = (heroItem.guid() == self._item.guid())
        self._heroItem = heroItem

        # Build a new sequence from the collated items
        newSequence = hiero.core.Sequence(self._item.name())

        # Copy tags from sequence to clone
        for tag in self._sequence.tags():
            newSequence.addTag(hiero.core.Tag(tag))

        # Apply the format of the master shot to the whole sequence
        # NOTE: Shouldn't it be taken from self._sequence instead? Multiple clips can have different resolution/formats
        newSequence.setFormat(self._clip.format())
        
        # Note: Without correct framerate, audio comes out silent when manually exporting the sequence.
        newSequence.setFramerate(self._clip.framerate())

        offset = self._item.sourceIn() - self._item.timelineIn()
        if self._startFrame is not None:
            # This flag indicates that an explicit start frame has been specified
            # To make sure that when the shot is expanded to include handles this is still the first
            # frame, here we offset the start frame by the in-handle size
            if properties["collateCustomStart"]:
                self._startFrame += self._cutHandles

            # The offset required to shift the timeline position to the custom start frame.
            offset = self._startFrame - self._item.timelineIn()
        
        sequenceIn, sequenceOut = sys.maxint, 0
        for trackitem in self._collatedItems:
            if trackitem.timelineIn() <= sequenceIn:
                sequenceIn = trackitem.timelineIn()
            if trackitem.timelineOut() >= sequenceOut:
                sequenceOut = trackitem.timelineOut()

        newTracks = {}
        audioTracks = {}
        for trackitem in self._collatedItems:
            parentTrack = trackitem.parentTrack()

            # Clone each track and add it to a dictionary, using guid as key
            if parentTrack.guid() not in newTracks:
                trackClone = hiero.core.VideoTrack(parentTrack.name())
                newTracks[parentTrack.guid()] = trackClone
                newSequence.addTrack(trackClone)

                # Copy tags from track to clone
                for tag in parentTrack.tags():
                    trackClone.addTag(hiero.core.Tag(tag))

            trackItemClone = trackitem.clone()
            self._collatedItemsMap[trackitem.guid()] = trackItemClone
            
            # Copy audio for track item
            linkedItems = trackitem.linkedItems()
            newAudio = {}
            for item in linkedItems:
                if item.mediaType() is hiero.core.TrackItem.MediaType.kAudio:
                    audioParentTrack = item.parentTrack()

                    if audioParentTrack.guid() not in audioTracks:
                        audioTrackClone = hiero.core.AudioTrack(audioParentTrack.name())
                        audioTracks[audioParentTrack.guid()] = audioTrackClone
                        newSequence.addTrack(audioTrackClone)

                        # Copy tags from track to clone
                        for tag in audioParentTrack.tags():
                            audioTrackClone.addTag(hiero.core.Tag(tag))
                    
                    audioItemClone = item.clone()
                    trackItemClone.link(audioItemClone)

                    self._collatedItemsMap[item.guid()] = audioItemClone
                    
                    if audioParentTrack.guid() not in newAudio: 
                        newAudio[audioParentTrack.guid()] = []
                    newAudio[audioParentTrack.guid()].append(audioItemClone)

            # extend any shots
            if self._cutHandles is not None:
                # Maximum available handle size
                handleInLength, handleOutLength = trackitem.handleInLength(), trackitem.handleOutLength()
                # Clamp to desired handle size
                handleIn, handleOut = min(self._cutHandles, handleInLength), min(self._cutHandles, handleOutLength)

                if trackItemClone.timelineIn() <= sequenceIn and handleIn:
                    self._trimInLinked(trackItemClone, -handleIn)
                    hiero.core.log.debug("Expanding %s in by %i frames" % (trackItemClone.name(), handleIn))
                if trackItemClone.timelineOut() >= sequenceOut and handleOut:
                    self._trimOutLinked(trackItemClone, -handleOut)
                    hiero.core.log.debug("Expanding %s out by %i frames" % (trackItemClone.name(), handleOut))

            self._offsetTimelineLinked(trackItemClone, self.HEAD_ROOM_OFFSET + offset)

            # Add Cloned track item to cloned track
            try:
                newTracks[parentTrack.guid()].addItem(trackItemClone)
                for trackGuid in newAudio.keys():
                    for item in newAudio[trackGuid]:
                        audioTracks[trackGuid].addItem(item)
            except Exception as e:
                clash = newTracks[parentTrack.guid()].items()[0]
                error = "Failed to add shot %s (%i - %i) due to clash with collated shots, This is likely due to the expansion of the master shot to include handles. (%s %i - %i)\n" % (trackItemClone.name(), trackItemClone.timelineIn(), trackItemClone.timelineOut(), clash.name(), clash.timelineIn(), clash.timelineOut())
                self.setError(error)
                hiero.core.log.error(error)
                hiero.core.log.error(str(e))

        handles = self._cutHandles if self._cutHandles is not None else 0

        # Use in/out point to constrain output framerange to track item range
        newSequence.setInTime(max(0, (sequenceIn + offset + self.HEAD_ROOM_OFFSET) - handles))
        newSequence.setOutTime((sequenceOut + offset + self.HEAD_ROOM_OFFSET) + handles)

        # Copy posterFrame from Hero item to sequence
        base = heroItem.source()
        if isinstance(base, hiero.core.SequenceBase):
            posterFrame = base.posterFrame()
            if posterFrame:
                newSequence.setPosterFrame(heroItem.timelineIn() + posterFrame + self.HEAD_ROOM_OFFSET + offset)

        # Useful for debugging, add cloned collated sequence to Project
        #hiero.core.projects()[-1].clipsBin().addItem(hiero.core.BinItem(newSequence))

        # Use this newly built sequence instead
        self._parentSequence = self._sequence

        # Need to use the sequence clone here, otherwise audio becomes silent for unknown reasons.
        self._sequence = newSequence.clone()

    def isCollated(self):
        return self._collate

    def originalSequence(self):
        return self._parentSequence

    def isHero(self):
        return self._hero

    def heroItem(self):
        return self._heroItem

    def finishTask(self):
        self._parentSequence = None

    def collatedOutputRange(self, ignoreHandles=False, ignoreRetimes=True, clampToSource=True):
        """Returns the output file range (as tuple) for this task, if applicable"""
        start = 0
        end  = 0

        if isinstance(self._item, hiero.core.Sequence) or self._collate:
            start, end = 0, self._item.duration() - 1
            if self._startFrame is not None:
                start += self._startFrame
                end += self._startFrame

            try:
                start = self._sequence.inTime()
            except RuntimeError:
                # This is fine, no in time set
                pass

            try:
                end = self._sequence.outTime()
            except RuntimeError:
                # This is fine, no out time set
                pass
        elif isinstance(self._item, (hiero.core.TrackItem, hiero.core.Clip)):
            # Get input frame range
            start, end = self.inputRange(ignoreHandles=ignoreHandles, ignoreRetimes=ignoreRetimes, clampToSource=clampToSource)

            if self._retime and isinstance(self._item, hiero.core.TrackItem) and ignoreRetimes:
                srcDuration = abs(self._item.sourceDuration())
                playbackSpeed = self._item.playbackSpeed()
                end = (end - srcDuration) + (srcDuration / playbackSpeed) + (playbackSpeed - 1.0)

            start = int(math.floor(start))
            end = int(math.ceil(end))

            # Offset by custom start time
            if self._startFrame is not None:
                end = self._startFrame + (end - start)
                start = self._startFrame

        return (start, end)


class CollatedShotPreset(object):
    def __init__(self, properties):
        properties["collateTracks"] = False
        properties["collateShotNames"] = False

        # Not exposed in UI
        properties["collateSequence"] = False    # Collate all trackitems within sequence
        properties["collateCustomStart"] = True  # Start frame is inclusive of handles
