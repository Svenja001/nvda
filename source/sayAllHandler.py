#sayAllHandler.py
#A part of NonVisual Desktop Access (NVDA)
#Copyright (C) 2006-2007 NVDA Contributors <http://www.nvda-project.org/>
#This file is covered by the GNU General Public License.
#See the file COPYING for more details.

import itertools
import queueHandler
import config
import speech
import textInfos
import globalVars
import api
import tones
import time

CURSOR_CARET=0
CURSOR_REVIEW=1

_generatorID = None

def _startGenerator(generator):
	global _generatorID
	stop()
	_generatorID = queueHandler.registerGeneratorObject(generator)

def stop():
	"""Stop say all if a say all is in progress.
	"""
	global _generatorID
	if _generatorID is None:
		return
	queueHandler.cancelGeneratorObject(_generatorID)
	_generatorID = None

def isRunning():
	"""Determine whether say all is currently running.
	@return: C{True} if say all is currently running, C{False} if not.
	@rtype: bool
	@note: If say all completes and there is no call to L{stop} (which is called from L{speech.cancelSpeech}), this will incorrectly return C{True}.
		This should not matter, but is worth noting nevertheless.
	"""
	global _generatorID
	return _generatorID is not None

def readObjects(obj):
	_startGenerator(readObjectsHelper_generator(obj))

def generateObjectSubtreeSpeech(obj,indexGen):
	index=indexGen.next()
	speech.speakObject(obj,reason=speech.REASON_SAYALL,index=index)
	yield obj,index
	child=obj.simpleFirstChild
	while child:
		childSpeech=generateObjectSubtreeSpeech(child,indexGen)
		for r in childSpeech:
			yield r
		child=child.simpleNext

def readObjectsHelper_generator(obj):
	lastSentIndex=0
	lastReceivedIndex=0
	speechGen=generateObjectSubtreeSpeech(obj,itertools.count())
	objIndexMap={}
	keepReading=True
	keepUpdating=True
	while keepUpdating:
		# lastReceivedIndex might be None if other speech was interspersed with this say all.
		# In this case, we want to send more text in case this was the last chunk spoken.
		if lastReceivedIndex is None or (lastSentIndex-lastReceivedIndex)<=1:
			if keepReading:
				try:
					o,lastSentIndex=speechGen.next()
				except StopIteration:
					keepReading=False
					continue
				objIndexMap[lastSentIndex]=o
		receivedIndex=speech.getLastSpeechIndex()
		if receivedIndex!=lastReceivedIndex and (lastReceivedIndex!=0 or receivedIndex!=None): 
			lastReceivedIndex=receivedIndex
			lastReceivedObj=objIndexMap.get(lastReceivedIndex)
			if lastReceivedObj is not None:
				api.setNavigatorObject(lastReceivedObj)
			#Clear old objects from the map
			for i in objIndexMap.keys():
				if i<=lastReceivedIndex:
					del objIndexMap[i]
		while speech.isPaused:
			yield
		yield

def readText(info,cursor):
	_startGenerator(readTextHelper_generator(info,cursor))

def readTextHelper_generator(info,cursor):
	lastSentIndex=0
	lastReceivedIndex=0
	cursorIndexMap={}
	if not info.obj:
		# The object died, so we should too.
		return
	reader=info.copy()
	if not reader.isCollapsed:
		reader.collapse()
	keepReading=True
	keepUpdating=True
	while keepUpdating:
		if not reader.obj:
			# The object died, so we should too.
			return
		# lastReceivedIndex might be None if other speech was interspersed with this say all.
		# In this case, we want to send more text in case this was the last chunk spoken.
		if lastReceivedIndex is None or (lastSentIndex-lastReceivedIndex)<=10:
			if keepReading:
				bookmark=reader.bookmark
				index=lastSentIndex+1
				delta=reader.move(textInfos.UNIT_READINGCHUNK,1,endPoint="end")
				if delta<=0:
					speech.speakWithoutPauses(None)
					keepReading=False
					continue
				speech.speakTextInfo(reader,unit=textInfos.UNIT_READINGCHUNK,reason=speech.REASON_SAYALL,index=index)
				lastSentIndex=index
				cursorIndexMap[index]=bookmark
				try:
					reader.collapse(end=True)
				except RuntimeError: #MS Word when range covers end of document
					speech.speakWithoutPauses(None)
					keepReading=False
		else:
			# We'll wait for speech to catch up a bit before sending more text.
			if speech.speakWithoutPauses.lastSentIndex is None or (lastSentIndex-speech.speakWithoutPauses.lastSentIndex)>=10:				# There is a 
				# There is a large chunk of pending speech
				# Force speakWithoutPauses to send text to the synth so we can move on.
				speech.speakWithoutPauses(None)
		receivedIndex=speech.getLastSpeechIndex()
		if receivedIndex!=lastReceivedIndex and (lastReceivedIndex!=0 or receivedIndex!=None): 
			lastReceivedIndex=receivedIndex
			bookmark=cursorIndexMap.get(receivedIndex,None)
			if bookmark is not None:
				updater=reader.obj.makeTextInfo(bookmark)
				if cursor==CURSOR_CARET:
					updater.updateCaret()
				if cursor!=CURSOR_CARET or config.conf["reviewCursor"]["followCaret"]:
					api.setReviewPosition(updater)
		while speech.isPaused:
			yield
		yield
