"""
compareTrackingGroupsGUI.py

GUI helping to decide which of two tracking algorithms (or two variations of the same tracking
algorithm) works best, by going through the biggest differences between two groups of ZebraZoom
tracking results (.h5 files of the ZZoutput folder) obtained on the same original videos.

The script is entirely self-contained: it only needs numpy, opencv, h5py and PyQt5 (all installed
with ZebraZoom) and doesn't import anything from ZebraZoom itself.

Usage:

    python compareTrackingGroupsGUI.py [pathToZZoutputFolder]

1) Group selection window
   The results files of the ZZoutput folder are listed by tracking session (results whose tracking
   started less than 10 minutes apart are put in the same session, most recent session first).
   Tick the results of the FIRST group in the left list (they will be shown at the TOP), and the
   results of the SECOND group in the right list (shown at the BOTTOM). Ticking a session ticks all
   of its results. The results of the two groups are paired by video name (the results file name
   without its tracking date and time).

2) How the differences are found and ranked
   On each frame, the tracked points of the two results are paired one-to-one (closest pairs first)
   when they are less than "matching distance" pixels apart. A point left without partner means that
   one result tracks a fish there while the other one doesn't. Along each trajectory, the frames
   without partner are grouped into stretches (stretches separated by at most 2 frames are joined).
   Each stretch is a difference whose score is:
       number of frames without partner * (1 + fraction of the trajectory without partner)
   So a long trajectory tracked where/when the other result has nothing is a big difference, a
   trajectory that the other result doesn't have at all gets its score doubled, and a trajectory that
   just lasts a few frames longer than in the other result is a small difference.
   A difference of the top result and a difference of the bottom result happening at the same time
   and at nearly the same place (for instance the top result tracks a fish 40 pixels away from where
   the bottom result tracks it, or one result's trajectory ends where the other's starts) are grouped
   together into one portion of video, whose score is the sum of the scores of its differences.
   Only the frames tracked in both results are compared. On results post-processed with
   synthesizeTracksFromDetectionCloud, the last frame (which still holds raw, unprocessed points)
   is ignored.

3) Order in which the portions of video are shown
   Round 1: the biggest difference of each video, the videos being sorted from the biggest to the
   smallest difference. Round 2: the second biggest difference of each video (again sorted by size),
   and so on. Every video is therefore shown once before any video is shown a second time.

4) Comparison window
   The same video frame is shown at the top (with the tracking of the first group) and at the bottom
   (with the tracking of the second group). Only the frames of the portion of video containing the
   difference (plus a few frames before and after) are accessible. On the right side, click
   "TOP is better" / "BOTTOM is better" (or "Equal / can't tell"): the choice is counted on the
   scoreboard, saved, and the next portion is shown. Choices can be changed by going back to a
   previous portion. Every choice is saved in ZZoutput/trackingComparison_[date-time].csv

   Drawing on the videos:
     - colored dots and trails: tracked points (one color per trajectory)
     - thin red circle: point without partner in the other result on this frame
     - thick yellow circle: the difference being judged, in the result that has the trajectory
     - dashed yellow circle: same location in the result that doesn't have that trajectory
     - faint yellow line: whole path of the difference being judged

   Keyboard shortcuts:
     Left / Right            previous / next frame (Shift: 10 frames)
     Home / End              first / last frame of the portion
     Space                   play / pause
     Up or T                 TOP is better
     Down or B               BOTTOM is better
     E                       equal / can't tell
     Page Up / Page Down     previous / next portion (without choosing)
     Z                       zoom on the difference / full frame

   Video frames are read sequentially from the beginning of the video, exactly like ZebraZoom does
   during tracking (seeking directly to a frame gives wrong frames on some AVI files), in a
   background thread which also preloads the next portions.
"""

import csv
import datetime
import importlib.util
import os
import re
import sys
import threading
from collections import OrderedDict

import cv2
import h5py
import numpy as np

from PyQt5.QtCore import QPointF, QRectF, Qt, QThread, QTimer, pyqtSignal
from PyQt5.QtGui import QColor, QImage, QKeySequence, QPainter, QPen, QPolygonF
from PyQt5.QtWidgets import (QApplication, QCheckBox, QComboBox, QFileDialog, QFrame, QGridLayout, QGroupBox, QHBoxLayout,
                             QLabel, QMessageBox, QProgressDialog, QPushButton, QScrollArea, QShortcut, QSizePolicy,
                             QSpinBox, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget)


# Default parameters (the first three can also be changed in the group selection window)
MATCHING_DISTANCE = 25          # pixels: points of the two results closer than this are the same fish
MIN_DIFFERENCE_LENGTH = 3       # frames: differences shorter than this are ignored
PORTION_MARGIN = 20             # frames shown before and after each difference
BRIDGE_GAP = 2                  # frames: stretches separated by at most this number of frames are joined
WHOLE_TRAJECTORY_FRACTION = 0.9 # a difference covering this fraction of its trajectory is a "whole trajectory" difference
MERGE_DISTANCE_FACTOR = 2       # top and bottom differences closer than this * matching distance (and close in time) form one portion
MERGE_FRAME_TOLERANCE = 5       # frames: time tolerance used when grouping differences into portions
BATCH_GAP_MINUTES = 10          # results whose tracking started less than this apart belong to the same session
TRAIL_LENGTH = 15               # frames of trajectory drawn behind each tracked point
SEEK_THRESHOLD = 1500           # frames: beyond this, non-AVI videos are positioned by seeking instead of reading
JPEG_QUALITY = 92               # quality of the in-memory compressed frames cache
FRAME_CACHE_MEGABYTES = 600     # size of the in-memory frames cache

RESULTS_NAME_REGEX = re.compile(r'^(?P<name>.+)_(?P<time>\d{4}_\d{2}_\d{2}-\d{2}_\d{2}_\d{2})\.h5$', re.IGNORECASE)

TOP, BOTTOM = 0, 1
SIDE_NAMES = ('TOP', 'BOTTOM')
SIDE_COLORS = ('#2f6fd6', '#c2410c')
FOCUS_COLOR = '#ffd60a'
DISAGREEMENT_COLOR = '#ff3030'


# ------------------------------------------------------------------------------------------------
# Results files and tracking data
# ------------------------------------------------------------------------------------------------

class ResultsFile:
  """A ZebraZoom .h5 results file, with the video name and the tracking time read from its name."""

  def __init__(self, path):
    self.path = os.path.normpath(path)
    self.filename = os.path.basename(path)
    match = RESULTS_NAME_REGEX.match(self.filename)
    if match:
      self.videoName = match.group('name')
      self.trackingTime = datetime.datetime.strptime(match.group('time'), '%Y_%m_%d-%H_%M_%S')
    else:
      self.videoName = os.path.splitext(self.filename)[0]
      self.trackingTime = datetime.datetime.fromtimestamp(os.path.getmtime(path))


def listResultsFiles(folder):
  resultsFiles = []
  for entry in os.scandir(folder):
    if entry.is_file() and entry.name.lower().endswith('.h5'):
      resultsFiles.append(ResultsFile(entry.path))
  return resultsFiles


def groupIntoTrackingSessions(resultsFiles, gapMinutes=BATCH_GAP_MINUTES):
  """Groups results files whose tracking started less than gapMinutes apart. Most recent session first."""
  sessions = []
  for resultsFile in sorted(resultsFiles, key=lambda r: (r.trackingTime, r.videoName)):
    if sessions and (resultsFile.trackingTime - sessions[-1][-1].trackingTime).total_seconds() <= gapMinutes * 60:
      sessions[-1].append(resultsFile)
    else:
      sessions.append([resultsFile])
  return sessions[::-1]


def _asBool(value):
  try:
    return bool(np.any(np.asarray(value, dtype=float)))
  except (TypeError, ValueError):
    return bool(value)


class TrackingData:
  """Head positions of all the trajectories of a results file, in video coordinates.

  positions has the shape (nbTrajectories, nbFrames, 2), NaN where the trajectory isn't tracked;
  positions[:, i] corresponds to the video frame firstFrame + i.
  """

  def __init__(self, path):
    self.path = path
    with h5py.File(path, 'r') as f:
      self.firstFrame = int(f.attrs.get('firstFrame', 0))
      videoPath = f.attrs.get('pathToOriginalVideo', '')
      self.videoPath = videoPath.decode() if isinstance(videoPath, bytes) else str(videoPath)
      config = f['configurationFileUsed'].attrs if 'configurationFileUsed' in f else {}
      postProcessedWithSynthesize = _asBool(config.get('synthesizeTracksFromDetectionCloud', 0))
      self.frameSize = None
      if 'exampleFrame' in f and len(f['exampleFrame'].shape) >= 2:
        self.frameSize = (int(f['exampleFrame'].shape[1]), int(f['exampleFrame'].shape[0]))
      wellsExtent = [0, 0]
      wellKeys = sorted((key for key in f.keys() if re.fullmatch(r'dataForWell\d+', key)), key=lambda key: int(key[11:]))
      labels = []
      trajectories = []
      for wellKey in wellKeys:
        wellNum = int(wellKey[11:])
        offsetX = offsetY = 0
        if 'wellPositions/well%d' % wellNum in f:
          wellAttrs = f['wellPositions/well%d' % wellNum].attrs
          offsetX = max(int(wellAttrs.get('topLeftX', 0)), 0)
          offsetY = max(int(wellAttrs.get('topLeftY', 0)), 0)
          wellsExtent[0] = max(wellsExtent[0], offsetX + int(wellAttrs.get('lengthX', 0)))
          wellsExtent[1] = max(wellsExtent[1], offsetY + int(wellAttrs.get('lengthY', 0)))
        animalKeys = sorted((key for key in f[wellKey].keys() if re.fullmatch(r'dataForAnimal\d+', key)), key=lambda key: int(key[13:]))
        for animalKey in animalKeys:
          dataset = f[wellKey][animalKey].get('dataPerFrame/HeadPos')
          if dataset is None:
            continue
          headPos = dataset[()]
          x = np.asarray(headPos['X'], dtype=np.float32)
          y = np.asarray(headPos['Y'], dtype=np.float32)
          missing = ~np.isfinite(x) | ~np.isfinite(y) | ((x == 0) & (y == 0))
          if missing.all():
            continue
          xy = np.stack([x + offsetX, y + offsetY], axis=1)
          xy[missing] = np.nan
          trajectories.append(xy)
          labels.append('animal %d' % int(animalKey[13:]) if len(wellKeys) == 1 else 'well %d animal %d' % (wellNum, int(animalKey[13:])))
      if self.frameSize is None and wellsExtent[0] > 0 and wellsExtent[1] > 0:
        self.frameSize = tuple(wellsExtent)
      if trajectories:
        nbFrames = max(len(xy) for xy in trajectories)
      else:
        nbFrames = int(f.attrs.get('lastFrame', self.firstFrame)) - self.firstFrame + 1
    self.positions = np.full((len(trajectories), nbFrames, 2), np.nan, dtype=np.float32)
    for k, xy in enumerate(trajectories):
      self.positions[k, :len(xy)] = xy
    self.labels = labels
    # Last frame usable for comparisons: with synthesizeTracksFromDetectionCloud, the last row isn't post-processed
    self.lastFrame = self.firstFrame + nbFrames - 1 - (1 if postProcessedWithSynthesize and nbFrames > 1 else 0)
    hues = (np.arange(len(labels)) * 0.618033988749895) % 1
    self.colors = [QColor.fromHsvF(float(hue), 0.75, 1.0) for hue in hues]

  def pointsAt(self, frame):
    """Returns the indices of the trajectories tracked on this frame and their positions."""
    index = frame - self.firstFrame
    if index < 0 or index >= self.positions.shape[1] or frame > self.lastFrame:
      return np.zeros(0, dtype=int), np.zeros((0, 2), dtype=np.float32)
    xy = self.positions[:, index]
    trajectories = np.flatnonzero(~np.isnan(xy[:, 0]))
    return trajectories, xy[trajectories]


# ------------------------------------------------------------------------------------------------
# Finding and ranking the differences between two tracking results
# ------------------------------------------------------------------------------------------------

class Parameters:
  def __init__(self, matchingDistance=MATCHING_DISTANCE, minDifferenceLength=MIN_DIFFERENCE_LENGTH, portionMargin=PORTION_MARGIN):
    self.matchingDistance = float(matchingDistance)
    self.minDifferenceLength = int(minDifferenceLength)
    self.portionMargin = int(portionMargin)
    self.bridgeGap = BRIDGE_GAP
    self.mergeDistance = MERGE_DISTANCE_FACTOR * self.matchingDistance
    self.mergeFrameTolerance = MERGE_FRAME_TOLERANCE


def matchPoints(pointsA, pointsB, maxDistance):
  """Pairs points of A and B one-to-one, closest pairs first, if closer than maxDistance.
  Returns two boolean arrays telling which points of A and of B have a partner."""
  matchedA = np.zeros(len(pointsA), dtype=bool)
  matchedB = np.zeros(len(pointsB), dtype=bool)
  if len(pointsA) == 0 or len(pointsB) == 0:
    return matchedA, matchedB
  distances = np.hypot(pointsA[:, None, 0] - pointsB[None, :, 0], pointsA[:, None, 1] - pointsB[None, :, 1])
  candidatesA, candidatesB = np.nonzero(distances <= maxDistance)
  for k in np.argsort(distances[candidatesA, candidatesB], kind='stable'):
    i, j = candidatesA[k], candidatesB[k]
    if not matchedA[i] and not matchedB[j]:
      matchedA[i] = matchedB[j] = True
  return matchedA, matchedB


def stretches(mask, gap=0):
  """(start, end) indices of the stretches of True values of mask, stretches separated by at most gap False values being joined."""
  indices = np.flatnonzero(mask)
  if len(indices) == 0:
    return []
  breaks = np.flatnonzero(np.diff(indices) > gap + 1)
  starts = np.concatenate([indices[:1], indices[breaks + 1]])
  ends = np.concatenate([indices[breaks], indices[-1:]])
  return list(zip(starts.tolist(), ends.tolist()))


class Difference:
  """A stretch of frames during which one trajectory of one result has no partner in the other result."""

  def __init__(self, side, label, frames, positions, trajectoryStart, trajectoryEnd, trajectoryLength, bridgeGap):
    self.side = side
    self.label = label
    self.frames = frames
    self.positions = positions
    self.nbFrames = len(frames)
    self.start = int(frames[0])
    self.end = int(frames[-1])
    self.trajectoryLength = trajectoryLength
    fraction = self.nbFrames / max(trajectoryLength, 1)
    if fraction >= WHOLE_TRAJECTORY_FRACTION:
      self.kind = 'whole'
    elif self.start - trajectoryStart <= bridgeGap:
      self.kind = 'start'
    elif trajectoryEnd - self.end <= bridgeGap:
      self.kind = 'end'
    else:
      self.kind = 'middle'
    self.score = self.nbFrames * (1 + fraction)
    # Index ranges of the positions to join with lines when drawing the path of the difference
    self.pathSegments = [(int(start), int(end)) for start, end in
                         zip(np.r_[0, np.flatnonzero(np.diff(frames) > bridgeGap + 1) + 1],
                             np.r_[np.flatnonzero(np.diff(frames) > bridgeGap + 1), len(frames) - 1])]

  def describe(self):
    side, other = SIDE_NAMES[self.side], SIDE_NAMES[1 - self.side]
    if self.kind == 'whole':
      return "%s has a %d-frame trajectory that %s doesn't have" % (side, self.nbFrames, other)
    if self.kind == 'start':
      return "%s has %d extra frames at the start of a %d-frame trajectory" % (side, self.nbFrames, self.trajectoryLength)
    if self.kind == 'end':
      return "%s has %d extra frames at the end of a %d-frame trajectory" % (side, self.nbFrames, self.trajectoryLength)
    return "%s tracks a fish for %d frames where %s doesn't (middle of a %d-frame trajectory)" % (side, self.nbFrames, other, self.trajectoryLength)

  def positionAt(self, frame):
    index = np.searchsorted(self.frames, frame)
    if index < len(self.frames) and self.frames[index] == frame:
      return self.positions[index]
    return None


def findDifferences(side, positions, tracked, withoutPartner, firstFrame, labels, params):
  differences = []
  for k in np.flatnonzero(withoutPartner.any(axis=1)):
    for trajectoryStart, trajectoryEnd in stretches(tracked[k], params.bridgeGap):
      trajectoryLength = int(tracked[k, trajectoryStart:trajectoryEnd + 1].sum())
      for start, end in stretches(withoutPartner[k, trajectoryStart:trajectoryEnd + 1], params.bridgeGap):
        indices = trajectoryStart + start + np.flatnonzero(withoutPartner[k, trajectoryStart + start:trajectoryStart + end + 1])
        if len(indices) < params.minDifferenceLength:
          continue
        differences.append(Difference(side, labels[k], indices + firstFrame, positions[k, indices].copy(),
                                      trajectoryStart + firstFrame, trajectoryEnd + firstFrame, trajectoryLength, params.bridgeGap))
  return differences


def _subsample(difference, maxPoints=300):
  step = max(1, int(np.ceil(difference.nbFrames / maxPoints)))
  return difference.frames[::step], difference.positions[::step]


def differencesAreClose(a, b, frameTolerance, maxDistance):
  framesA, positionsA = _subsample(a)
  framesB, positionsB = _subsample(b)
  closeInTime = np.abs(framesA[:, None] - framesB[None, :]) <= frameTolerance
  if not closeInTime.any():
    return False
  distances = np.hypot(positionsA[:, None, 0] - positionsB[None, :, 0], positionsA[:, None, 1] - positionsB[None, :, 1])
  return bool((distances[closeInTime] <= maxDistance).any())


class DifferenceGroup:
  """Differences of a video happening at the same time and place: they are shown in the same portion of video."""

  def __init__(self, differences):
    self.differences = sorted(differences, key=lambda difference: -difference.score)
    self.start = min(difference.start for difference in differences)
    self.end = max(difference.end for difference in differences)
    self.score = sum(difference.score for difference in differences)


def groupDifferences(differences, params):
  differences = sorted(differences, key=lambda difference: difference.start)
  parent = list(range(len(differences)))

  def root(i):
    while parent[i] != i:
      parent[i] = parent[parent[i]]
      i = parent[i]
    return i

  for i, a in enumerate(differences):
    for j in range(i + 1, len(differences)):
      b = differences[j]
      if b.start > a.end + params.mergeFrameTolerance:
        break
      if a.side != b.side and root(i) != root(j) and differencesAreClose(a, b, params.mergeFrameTolerance, params.mergeDistance):
        parent[root(j)] = root(i)
  groups = OrderedDict()
  for i, difference in enumerate(differences):
    groups.setdefault(root(i), []).append(difference)
  return sorted((DifferenceGroup(group) for group in groups.values()), key=lambda group: -group.score)


def compareTracking(top, bottom, params):
  """Returns the groups of differences between two TrackingData of the same video (biggest first),
  and the first and last frames compared."""
  start = max(top.firstFrame, bottom.firstFrame)
  end = min(top.lastFrame, bottom.lastFrame)
  if end < start:
    return [], start, end
  positions = [data.positions[:, start - data.firstFrame:end - data.firstFrame + 1] for data in (top, bottom)]
  tracked = [~np.isnan(xy[:, :, 0]) for xy in positions]
  withoutPartner = [mask.copy() for mask in tracked]
  for t in range(end - start + 1):
    topTrajectories = np.flatnonzero(tracked[TOP][:, t])
    bottomTrajectories = np.flatnonzero(tracked[BOTTOM][:, t])
    if len(topTrajectories) == 0 or len(bottomTrajectories) == 0:
      continue
    matchedTop, matchedBottom = matchPoints(positions[TOP][topTrajectories, t], positions[BOTTOM][bottomTrajectories, t], params.matchingDistance)
    withoutPartner[TOP][topTrajectories[matchedTop], t] = False
    withoutPartner[BOTTOM][bottomTrajectories[matchedBottom], t] = False
  differences = []
  for side, data in ((TOP, top), (BOTTOM, bottom)):
    differences += findDifferences(side, positions[side], tracked[side], withoutPartner[side], start, data.labels, params)
  return groupDifferences(differences, params), start, end


class VideoPair:
  """The two tracking results of one video and their differences."""

  def __init__(self, name, topResults, bottomResults, topData, bottomData, groups, start, end, zzOutputFolder):
    self.name = name
    self.results = (topResults, bottomResults)
    self.groups = groups
    self.start = start
    self.end = end
    self.originalVideoPath = topData.videoPath or bottomData.videoPath
    self.videoPath = findVideo([topData.videoPath, bottomData.videoPath], zzOutputFolder)
    self.frameSize = topData.frameSize or bottomData.frameSize


def findVideo(candidatePaths, zzOutputFolder, movedFolders=None):
  candidatePaths = [os.path.normpath(path) for path in candidatePaths if path]
  for path in candidatePaths:
    if os.path.isfile(path):
      return path
  for path in candidatePaths:
    for oldFolder, newFolder in (movedFolders or {}).items():
      if os.path.normcase(os.path.dirname(path)) == oldFolder:
        candidate = os.path.join(newFolder, os.path.basename(path))
        if os.path.isfile(candidate):
          return candidate
    candidate = os.path.join(zzOutputFolder, os.path.basename(path))
    if os.path.isfile(candidate):
      return candidate
  return None


def analyzeVideoPair(name, topResults, bottomResults, params, zzOutputFolder):
  topData = TrackingData(topResults.path)
  bottomData = TrackingData(bottomResults.path)
  groups, start, end = compareTracking(topData, bottomData, params)
  return VideoPair(name, topResults, bottomResults, topData, bottomData, groups, start, end, zzOutputFolder)


class Portion:
  """A portion of video to show: one group of differences of one video, plus a margin before and after."""

  def __init__(self, pair, group, rankInVideo, roundNumber, positionInRound, roundSize, margin):
    self.pair = pair
    self.group = group
    self.rankInVideo = rankInVideo
    self.roundNumber = roundNumber
    self.positionInRound = positionInRound
    self.roundSize = roundSize
    self.start = max(pair.start, group.start - margin)
    self.end = min(pair.end, group.end + margin)

  def describe(self, maxLines=4):
    lines = [difference.describe() for difference in self.group.differences[:maxLines]]
    if len(self.group.differences) > maxLines:
      lines.append('+ %d smaller difference(s) at the same time and place' % (len(self.group.differences) - maxLines))
    return lines


def orderPortions(pairs, margin):
  """Round 1: biggest difference of each video (biggest first), round 2: second biggest of each video, etc."""
  portions = []
  roundIndex = 0
  while True:
    candidates = sorted((pair for pair in pairs if len(pair.groups) > roundIndex), key=lambda pair: -pair.groups[roundIndex].score)
    if not candidates:
      return portions
    for position, pair in enumerate(candidates):
      portions.append(Portion(pair, pair.groups[roundIndex], roundIndex + 1, roundIndex + 1, position + 1, len(candidates), margin))
    roundIndex += 1


# ------------------------------------------------------------------------------------------------
# Video frames reading
# ------------------------------------------------------------------------------------------------

class FrameLoader:
  """Reads video frames in a background thread and keeps them JPEG-compressed in memory.

  Frames are read sequentially from the beginning of the video, like ZebraZoom does when tracking
  (except non-AVI videos beyond SEEK_THRESHOLD frames, which are positioned by seeking).
  setWanted() gives the frame ranges to load, most urgent first.
  """

  def __init__(self, cacheMegabytes=FRAME_CACHE_MEGABYTES):
    self._condition = threading.Condition()
    self._wanted = []
    self._cache = OrderedDict()
    self._cacheBytes = 0
    self._maxCacheBytes = cacheMegabytes * 1024 * 1024
    self._unreadableFrom = {}
    self.videoInfo = {}
    self._stopped = False
    self._capture = None
    self._capturePath = None
    self._capturePosition = 0
    self._thread = threading.Thread(target=self._run, daemon=True)
    self._thread.start()

  def stop(self):
    with self._condition:
      self._stopped = True
      self._condition.notify_all()
    self._thread.join(timeout=5)

  def setWanted(self, ranges):
    with self._condition:
      self._wanted = [(path, int(start), int(end)) for path, start, end in ranges if path]
      self._condition.notify_all()

  def getFrame(self, path, frame):
    """Returns ('ok', image), ('loading', None) or ('error', None)."""
    with self._condition:
      data = self._cache.get((path, frame))
      if data is not None:
        self._cache.move_to_end((path, frame))
      unreadableFrom = self._unreadableFrom.get(path)
    if data is not None:
      return 'ok', cv2.imdecode(np.frombuffer(data, dtype=np.uint8), cv2.IMREAD_COLOR)
    if unreadableFrom is not None and frame >= unreadableFrom:
      return 'error', None
    return 'loading', None

  def countLoaded(self, path, start, end):
    with self._condition:
      return sum((path, frame) in self._cache for frame in range(start, end + 1))

  def _firstMissingFrame(self, path, start, end):
    unreadableFrom = self._unreadableFrom.get(path)
    for frame in range(start, end + 1):
      if unreadableFrom is not None and frame >= unreadableFrom:
        return None
      if (path, frame) not in self._cache:
        return frame
    return None

  def _nextTask(self):
    for priority, (path, start, end) in enumerate(self._wanted):
      frame = self._firstMissingFrame(path, start, end)
      if frame is not None:
        return priority, path, frame, end
    return None

  def _stillWanted(self, priority, path, frame):
    if self._stopped or priority >= len(self._wanted):
      return False
    wantedPath, start, end = self._wanted[priority]
    if wantedPath != path or not start <= frame <= end:
      return False
    return all(self._firstMissingFrame(*moreUrgent) is None for moreUrgent in self._wanted[:priority])

  def _markUnreadable(self, path, frame):
    with self._condition:
      self._unreadableFrom[path] = min(frame, self._unreadableFrom.get(path, frame))

  def _run(self):
    try:
      while True:
        with self._condition:
          task = self._nextTask()
          while task is None and not self._stopped:
            self._condition.wait()
            task = self._nextTask()
          if self._stopped:
            return
        try:
          self._readFrames(*task)
        except Exception as error:
          print('Error while reading %s: %s' % (task[1], error))
          self._markUnreadable(task[1], task[2])
    finally:
      if self._capture is not None:
        self._capture.release()

  def _moveTo(self, priority, path, frame):
    if self._capture is None or self._capturePath != path or self._capturePosition > frame:
      if self._capture is not None:
        self._capture.release()
      self._capture = cv2.VideoCapture(path)
      self._capturePath = path
      self._capturePosition = 0
      if not self._capture.isOpened():
        self._capture = None
        self._markUnreadable(path, 0)
        return False
      fps = self._capture.get(cv2.CAP_PROP_FPS)
      self.videoInfo[path] = (int(self._capture.get(cv2.CAP_PROP_FRAME_WIDTH)), int(self._capture.get(cv2.CAP_PROP_FRAME_HEIGHT)), fps if fps and fps > 0 else 25.)
      if frame > SEEK_THRESHOLD and os.path.splitext(path)[1].lower() != '.avi':
        self._capture.set(cv2.CAP_PROP_POS_FRAMES, frame)
        self._capturePosition = frame
    while self._capturePosition < frame:
      if (frame - self._capturePosition) % 25 == 0:
        with self._condition:
          if not self._stillWanted(priority, path, frame):
            return False
      if not self._capture.grab():
        self._markUnreadable(path, self._capturePosition)
        return False
      self._capturePosition += 1
    return True

  def _readFrames(self, priority, path, start, end):
    if not self._moveTo(priority, path, start):
      return
    for frame in range(start, end + 1):
      with self._condition:
        if not self._stillWanted(priority, path, frame):
          return
        alreadyLoaded = (path, frame) in self._cache
      if alreadyLoaded:
        ok = self._capture.grab()
        image = None
      else:
        ok, image = self._capture.read()
      if not ok or (not alreadyLoaded and image is None):
        self._markUnreadable(path, frame)
        return
      self._capturePosition += 1
      if alreadyLoaded:
        continue
      encoded = cv2.imencode('.jpg', image, [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY])[1].tobytes()
      with self._condition:
        self._cache[(path, frame)] = encoded
        self._cacheBytes += len(encoded)
        self._evict()

  def _evict(self):
    if self._cacheBytes <= self._maxCacheBytes:
      return
    for key in list(self._cache.keys()):
      if self._cacheBytes <= self._maxCacheBytes:
        return
      path, frame = key
      if any(wantedPath == path and start <= frame <= end for wantedPath, start, end in self._wanted):
        continue
      self._cacheBytes -= len(self._cache.pop(key))


# ------------------------------------------------------------------------------------------------
# Widgets
# ------------------------------------------------------------------------------------------------

def toQImage(bgrImage):
  rgb = np.ascontiguousarray(cv2.cvtColor(bgrImage, cv2.COLOR_BGR2RGB))
  height, width = rgb.shape[:2]
  return QImage(rgb.data, width, height, 3 * width, QImage.Format_RGB888).copy()


class Overlay:
  def __init__(self):
    self.trails = []          # (QColor, [(x, y), ...])
    self.points = []          # (x, y, QColor)
    self.disagreements = []   # (x, y)
    self.focus = []           # (x, y)
    self.ghosts = []          # (x, y)
    self.focusPaths = []      # [(x, y), ...]


class FrameView(QWidget):
  """Draws a video frame (or part of it) scaled to the widget, with the tracking overlay."""

  def __init__(self, parent=None):
    super().__init__(parent)
    self.setMinimumSize(320, 160)
    self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
    self.setFocusPolicy(Qt.NoFocus)
    self._image = None
    self._frameSize = (640, 480)
    self._crop = None
    self._overlay = Overlay()
    self._message = ''
    self._ringRadius = 10

  def setContent(self, image, frameSize, crop, overlay, message, ringRadius):
    self._image = image
    self._frameSize = frameSize
    self._crop = crop
    self._overlay = overlay
    self._message = message
    self._ringRadius = ringRadius
    self.update()

  def paintEvent(self, event):
    painter = QPainter(self)
    painter.fillRect(self.rect(), QColor(18, 18, 18))
    frameWidth, frameHeight = self._frameSize
    cropX, cropY, cropWidth, cropHeight = self._crop if self._crop is not None else (0, 0, frameWidth, frameHeight)
    scale = min(self.width() / cropWidth, self.height() / cropHeight)
    offsetX = (self.width() - cropWidth * scale) / 2
    offsetY = (self.height() - cropHeight * scale) / 2
    target = QRectF(offsetX, offsetY, cropWidth * scale, cropHeight * scale)
    painter.setRenderHint(QPainter.SmoothPixmapTransform)
    painter.setRenderHint(QPainter.Antialiasing)
    if self._image is not None:
      painter.drawImage(target, self._image, QRectF(cropX, cropY, cropWidth, cropHeight))
    else:
      painter.fillRect(target, QColor(48, 48, 48))
    painter.setClipRect(target)

    def toScreen(x, y):
      return QPointF(offsetX + (x - cropX) * scale, offsetY + (y - cropY) * scale)

    radius = self._ringRadius * scale
    overlay = self._overlay
    pen = QPen(QColor(FOCUS_COLOR), 1.5, Qt.DotLine)
    pen.setColor(QColor(255, 214, 10, 150))
    painter.setPen(pen)
    for path in overlay.focusPaths:
      if len(path) > 1:
        painter.drawPolyline(QPolygonF([toScreen(x, y) for x, y in path]))
    for color, trail in overlay.trails:
      if len(trail) > 1:
        painter.setPen(QPen(color, 1.5))
        painter.drawPolyline(QPolygonF([toScreen(x, y) for x, y in trail]))
    painter.setPen(QPen(QColor(0, 0, 0), 1))
    for x, y, color in overlay.points:
      painter.setBrush(color)
      painter.drawEllipse(toScreen(x, y), 3.5, 3.5)
    painter.setBrush(Qt.NoBrush)
    painter.setPen(QPen(QColor(DISAGREEMENT_COLOR), 1.5))
    for x, y in overlay.disagreements:
      painter.drawEllipse(toScreen(x, y), max(radius, 7), max(radius, 7))
    focusRadius = max(radius * 1.6, 13)
    for x, y in overlay.ghosts:
      painter.setPen(QPen(QColor(0, 0, 0, 200), 4))
      painter.drawEllipse(toScreen(x, y), focusRadius, focusRadius)
      painter.setPen(QPen(QColor(FOCUS_COLOR), 2.5, Qt.DashLine))
      painter.drawEllipse(toScreen(x, y), focusRadius, focusRadius)
    for x, y in overlay.focus:
      painter.setPen(QPen(QColor(0, 0, 0, 200), 6))
      painter.drawEllipse(toScreen(x, y), focusRadius, focusRadius)
      painter.setPen(QPen(QColor(FOCUS_COLOR), 3.5))
      painter.drawEllipse(toScreen(x, y), focusRadius, focusRadius)
    painter.setClipping(False)
    if self._message:
      font = painter.font()
      font.setPointSize(12)
      painter.setFont(font)
      textRect = painter.boundingRect(self.rect(), Qt.AlignCenter | Qt.TextWordWrap, self._message).adjusted(-12, -8, 12, 8)
      painter.setPen(Qt.NoPen)
      painter.setBrush(QColor(0, 0, 0, 170))
      painter.drawRoundedRect(textRect, 6, 6)
      painter.setPen(QColor(255, 255, 255))
      painter.drawText(self.rect(), Qt.AlignCenter | Qt.TextWordWrap, self._message)


class Timeline(QWidget):
  """Frames of the portion, with the frames where each result has the trajectory the other result doesn't have."""

  seek = pyqtSignal(int)

  def __init__(self, parent=None):
    super().__init__(parent)
    self.setFixedHeight(46)
    self.setFocusPolicy(Qt.NoFocus)
    self.LABEL_WIDTH = self.fontMetrics().horizontalAdvance('BOTTOM only') + 16
    self.start, self.end, self.current = 0, 1, 0
    self.spans = ([], [])

  def setPortion(self, start, end, framesPerSide):
    self.start, self.end = start, end
    self.spans = tuple(_frameSpans(frames) for frames in framesPerSide)
    self.update()

  def setCurrent(self, frame):
    self.current = frame
    self.update()

  def _x(self, frame):
    width = self.width() - self.LABEL_WIDTH - 10
    return self.LABEL_WIDTH + (frame - self.start) / max(self.end - self.start + 1, 1) * width

  def paintEvent(self, event):
    painter = QPainter(self)
    painter.fillRect(self.rect(), QColor(30, 30, 30))
    frameWidth = self._x(self.start + 1) - self._x(self.start)
    for side in (TOP, BOTTOM):
      y = 5 + side * 19
      painter.setPen(QColor(SIDE_COLORS[side]).lighter(150))
      painter.drawText(QRectF(2, y, self.LABEL_WIDTH - 8, 16), Qt.AlignRight | Qt.AlignVCenter, '%s only' % SIDE_NAMES[side])
      painter.fillRect(QRectF(self._x(self.start), y, self._x(self.end + 1) - self._x(self.start), 16), QColor(62, 62, 62))
      for spanStart, spanEnd in self.spans[side]:
        painter.fillRect(QRectF(self._x(spanStart), y, max(self._x(spanEnd + 1) - self._x(spanStart), 2), 16), QColor(SIDE_COLORS[side]))
    x = self._x(self.current) + frameWidth / 2
    painter.setPen(QPen(QColor(255, 255, 255), 2))
    painter.drawLine(QPointF(x, 1), QPointF(x, self.height() - 1))

  def _seekTo(self, x):
    width = self.width() - self.LABEL_WIDTH - 10
    frame = self.start + int((x - self.LABEL_WIDTH) / max(width, 1) * (self.end - self.start + 1))
    self.seek.emit(min(max(frame, self.start), self.end))

  def mousePressEvent(self, event):
    self._seekTo(event.x())

  def mouseMoveEvent(self, event):
    if event.buttons() & Qt.LeftButton:
      self._seekTo(event.x())


def _frameSpans(frames):
  frames = np.unique(np.asarray(frames, dtype=int))
  if len(frames) == 0:
    return []
  breaks = np.flatnonzero(np.diff(frames) > 1)
  starts = np.concatenate([frames[:1], frames[breaks + 1]])
  ends = np.concatenate([frames[breaks], frames[-1:]])
  return list(zip(starts.tolist(), ends.tolist()))


# ------------------------------------------------------------------------------------------------
# Comparison window
# ------------------------------------------------------------------------------------------------

CHOICE_TEXTS = {'top': 'TOP (group 1) better', 'bottom': 'BOTTOM (group 2) better', 'equal': "equal / can't tell"}


class ComparisonWindow(QWidget):

  def __init__(self, portions, params, zzOutputFolder, onClose=None):
    super().__init__()
    self.setWindowTitle('Tracking comparison: TOP = group 1, BOTTOM = group 2')
    self.portions = portions
    self.params = params
    self.zzOutputFolder = zzOutputFolder
    self.onClose = onClose
    self.choices = {}
    self.csvPath = os.path.join(zzOutputFolder, 'trackingComparison_%s.csv' % datetime.datetime.now().strftime('%Y_%m_%d-%H_%M_%S'))
    self.loader = FrameLoader()
    self.trackingCache = OrderedDict()
    self.movedFolders = {}
    self.index = 0
    self.frame = 0
    self.playTimer = QTimer(self)
    self.playTimer.timeout.connect(self._playStep)
    self.refreshTimer = QTimer(self)
    self.refreshTimer.setSingleShot(True)
    self.refreshTimer.timeout.connect(self.render)
    self._buildInterface()
    self._createShortcuts()
    self.showPortion(0)

  # --- Interface ---

  def _button(self, text, slot, checkable=False):
    button = QPushButton(text)
    button.setFocusPolicy(Qt.NoFocus)
    button.setCheckable(checkable)
    button.clicked.connect(slot)
    return button

  def _sideButton(self, side, text, slot):
    button = self._button(text, slot, checkable=True)
    button.setMinimumHeight(90)
    color = QColor(SIDE_COLORS[side])
    button.setStyleSheet('QPushButton {background-color: %s; color: white; font-size: 15pt; font-weight: bold; border-radius: 8px; border: 4px solid %s;}'
                         'QPushButton:hover {background-color: %s;}'
                         'QPushButton:checked {border: 5px solid %s;}' % (color.name(), color.name(), color.lighter(120).name(), FOCUS_COLOR))
    return button

  def _buildInterface(self):
    mainLayout = QHBoxLayout(self)
    mainLayout.setContentsMargins(6, 6, 6, 6)

    videosLayout = QVBoxLayout()
    videosLayout.setSpacing(3)
    self.headers = []
    self.views = []
    for side in (TOP, BOTTOM):
      header = QLabel()
      header.setTextFormat(Qt.RichText)
      header.setStyleSheet('background-color: %s; color: white; padding: 3px 8px; font-weight: bold;' % SIDE_COLORS[side])
      view = FrameView()
      self.headers.append(header)
      self.views.append(view)
    self.timeline = Timeline()
    self.timeline.seek.connect(self.setFrame)
    videosLayout.addWidget(self.headers[TOP])
    videosLayout.addWidget(self.views[TOP], 1)
    videosLayout.addWidget(self.timeline)
    videosLayout.addWidget(self.headers[BOTTOM])
    videosLayout.addWidget(self.views[BOTTOM], 1)
    mainLayout.addLayout(videosLayout, 1)

    panel = QWidget()
    panel.setFixedWidth(330)
    panelLayout = QVBoxLayout(panel)
    panelLayout.setContentsMargins(4, 0, 0, 0)
    self.topButton = self._sideButton(TOP, '▲  TOP is better', lambda: self.choose('top'))
    self.bottomButton = self._sideButton(BOTTOM, '▼  BOTTOM is better', lambda: self.choose('bottom'))
    self.equalButton = self._button("=  Equal / can't tell", lambda: self.choose('equal'), checkable=True)
    self.equalButton.setMinimumHeight(34)
    self.equalButton.setStyleSheet('QPushButton:checked {border: 3px solid %s; font-weight: bold;}' % FOCUS_COLOR)

    self.infoLabel = QLabel()
    self.infoLabel.setWordWrap(True)
    self.infoLabel.setTextFormat(Qt.RichText)
    self.infoLabel.setAlignment(Qt.AlignTop | Qt.AlignLeft)
    infoScrollArea = QScrollArea()
    infoScrollArea.setWidget(self.infoLabel)
    infoScrollArea.setWidgetResizable(True)
    infoScrollArea.setFrameShape(QFrame.NoFrame)
    infoScrollArea.setFocusPolicy(Qt.NoFocus)
    infoScrollArea.setMinimumHeight(120)
    self.frameLabel = QLabel()
    self.frameLabel.setWordWrap(True)

    scoreBox = QGroupBox('Scoreboard')
    scoreLayout = QVBoxLayout(scoreBox)
    self.scoreLabel = QLabel()
    self.scoreLabel.setTextFormat(Qt.RichText)
    scoreLayout.addWidget(self.scoreLabel)

    navigationLayout = QGridLayout()
    self.previousButton = self._button('◀ Previous portion', self.previousPortion)
    self.nextButton = self._button('Next portion ▶', self.nextPortion)
    self.playButton = self._button('▶ Play', self.togglePlay)
    self.speedCombo = QComboBox()
    self.speedCombo.setFocusPolicy(Qt.NoFocus)
    for speed in ('0.25', '0.5', '1', '2'):
      self.speedCombo.addItem('speed x%s' % speed, float(speed))
    self.speedCombo.setCurrentIndex(1)
    self.speedCombo.currentIndexChanged.connect(self._updatePlaySpeed)
    navigationLayout.addWidget(self.previousButton, 0, 0)
    navigationLayout.addWidget(self.nextButton, 0, 1)
    navigationLayout.addWidget(self.playButton, 1, 0)
    navigationLayout.addWidget(self.speedCombo, 1, 1)

    self.zoomCheckbox = QCheckBox('Zoom on the difference (Z)')
    self.zoomCheckbox.setChecked(True)
    self.trailsCheckbox = QCheckBox('Show trajectory trails')
    self.trailsCheckbox.setChecked(True)
    self.disagreementsCheckbox = QCheckBox('Circle in red all points without partner')
    self.disagreementsCheckbox.setChecked(True)
    for checkbox in (self.zoomCheckbox, self.trailsCheckbox, self.disagreementsCheckbox):
      checkbox.setFocusPolicy(Qt.NoFocus)
      checkbox.toggled.connect(self.render)
    self.locateVideoButton = self._button('Locate video...', self.locateVideo)
    self.locateVideoButton.hide()

    helpLabel = QLabel('<small>Keys: ← → frame (Shift: 10) &middot; Space play &middot; ↑/T top better &middot; '
                       '↓/B bottom better &middot; E equal &middot; PgUp/PgDn portion &middot; Z zoom<br>'
                       '<b style="color:#b38f00">Thick yellow circle</b>: the difference being judged; <b style="color:#b38f00">dashed</b>: '
                       'same place in the other result; <b style="color:%s">red circle</b>: point without partner</small>' % DISAGREEMENT_COLOR)
    helpLabel.setWordWrap(True)
    self.csvLabel = QLabel('<small>Choices saved in ZZoutput: %s</small>' % os.path.basename(self.csvPath))
    self.csvLabel.setToolTip(self.csvPath)
    self.csvLabel.setWordWrap(True)

    panelLayout.addWidget(self.topButton)
    panelLayout.addSpacing(6)
    panelLayout.addWidget(infoScrollArea, 1)
    panelLayout.addWidget(self.frameLabel)
    panelLayout.addWidget(self.locateVideoButton)
    panelLayout.addLayout(navigationLayout)
    for checkbox in (self.zoomCheckbox, self.trailsCheckbox, self.disagreementsCheckbox):
      panelLayout.addWidget(checkbox)
    panelLayout.addWidget(helpLabel)
    panelLayout.addWidget(scoreBox)
    panelLayout.addWidget(self.equalButton)
    panelLayout.addWidget(self.csvLabel)
    panelLayout.addSpacing(6)
    panelLayout.addWidget(self.bottomButton)
    mainLayout.addWidget(panel)

  def _createShortcuts(self):
    shortcuts = [
      ('Left', lambda: self.setFrame(self.frame - 1)), ('Right', lambda: self.setFrame(self.frame + 1)),
      ('Shift+Left', lambda: self.setFrame(self.frame - 10)), ('Shift+Right', lambda: self.setFrame(self.frame + 10)),
      ('Home', lambda: self.setFrame(self.portions[self.index].start)), ('End', lambda: self.setFrame(self.portions[self.index].end)),
      ('Space', self.togglePlay), ('Up', lambda: self.choose('top')), ('T', lambda: self.choose('top')),
      ('Down', lambda: self.choose('bottom')), ('B', lambda: self.choose('bottom')), ('E', lambda: self.choose('equal')),
      ('PgUp', self.previousPortion), ('PgDown', self.nextPortion), ('Z', self.zoomCheckbox.toggle),
    ]
    for key, slot in shortcuts:
      shortcut = QShortcut(QKeySequence(key), self)
      shortcut.activated.connect(slot)

  # --- Data ---

  def _tracking(self, path):
    if path in self.trackingCache:
      self.trackingCache.move_to_end(path)
    else:
      self.trackingCache[path] = TrackingData(path)
      while len(self.trackingCache) > 6:
        self.trackingCache.popitem(last=False)
    return self.trackingCache[path]

  def _frameRange(self, index):
    portion = self.portions[index]
    return (portion.pair.videoPath, portion.start, portion.end)

  def locateVideo(self):
    pair = self.portions[self.index].pair
    path, _ = QFileDialog.getOpenFileName(self, 'Locate the video %s' % os.path.basename(pair.originalVideoPath), self.zzOutputFolder)
    if not path:
      return
    pair.videoPath = os.path.normpath(path)
    if pair.originalVideoPath:
      self.movedFolders[os.path.normcase(os.path.dirname(os.path.normpath(pair.originalVideoPath)))] = os.path.dirname(pair.videoPath)
    for portion in self.portions:
      if portion.pair.videoPath is None:
        portion.pair.videoPath = findVideo([portion.pair.originalVideoPath], self.zzOutputFolder, self.movedFolders)
    self.showPortion(self.index)

  # --- Navigation ---

  def showPortion(self, index):
    self.index = min(max(index, 0), len(self.portions) - 1)
    portion = self.portions[self.index]
    self.loader.setWanted([self._frameRange(i) for i in range(self.index, min(self.index + 3, len(self.portions)))])
    framesPerSide = ([], [])
    for difference in portion.group.differences:
      framesPerSide[difference.side].extend(difference.frames.tolist())
    self.timeline.setPortion(portion.start, portion.end, framesPerSide)
    self.frame = min(max(portion.group.start, portion.start), portion.end)
    self.locateVideoButton.setVisible(portion.pair.videoPath is None)
    self._updateInfo()
    self._updateChoiceButtons()
    self.render()

  def previousPortion(self):
    if self.index > 0:
      self.showPortion(self.index - 1)

  def nextPortion(self):
    if self.index < len(self.portions) - 1:
      self.showPortion(self.index + 1)

  def setFrame(self, frame):
    portion = self.portions[self.index]
    frame = min(max(frame, portion.start), portion.end)
    if frame != self.frame:
      self.frame = frame
      self.render()

  def togglePlay(self):
    if self.playTimer.isActive():
      self.playTimer.stop()
      self.playButton.setText('▶ Play')
    else:
      if self.frame >= self.portions[self.index].end:
        self.setFrame(self.portions[self.index].start)
      self._updatePlaySpeed()
      self.playTimer.start()
      self.playButton.setText('⏸ Pause')

  def _updatePlaySpeed(self):
    path = self.portions[self.index].pair.videoPath
    fps = self.loader.videoInfo.get(path, (0, 0, 25.))[2]
    self.playTimer.setInterval(max(int(1000 / (fps * self.speedCombo.currentData())), 5))

  def _playStep(self):
    portion = self.portions[self.index]
    if self.frame >= portion.end:
      self.togglePlay()
      return
    status, _ = self.loader.getFrame(portion.pair.videoPath, self.frame + 1) if portion.pair.videoPath else ('error', None)
    if status != 'loading':
      self.setFrame(self.frame + 1)

  # --- Choices ---

  def choose(self, choice):
    self.choices[self.index] = (choice, datetime.datetime.now())
    self._saveChoices()
    self._updateChoiceButtons()
    if self.index < len(self.portions) - 1:
      self.showPortion(self.index + 1)
    else:
      self._updateInfo()
      QMessageBox.information(self, 'All portions shown', 'All the portions of video have been shown.\n\n' + self._scoreText())

  def _updateChoiceButtons(self):
    choice = self.choices.get(self.index, (None, None))[0]
    self.topButton.setChecked(choice == 'top')
    self.bottomButton.setChecked(choice == 'bottom')
    self.equalButton.setChecked(choice == 'equal')
    counts = {key: 0 for key in CHOICE_TEXTS}
    for chosen, _ in self.choices.values():
      counts[chosen] += 1
    total = counts['top'] + counts['bottom']

    def percent(count):
      return ' <small>(%d%%)</small>' % round(100 * count / total) if total else ''

    self.scoreLabel.setText(
      '<table cellspacing="4">'
      '<tr><td><b style="color:%s">TOP</b> (group 1) better</td><td align="right" style="font-size:18pt"><b>%d</b>%s</td></tr>'
      '<tr><td><b style="color:%s">BOTTOM</b> (group 2) better</td><td align="right" style="font-size:18pt"><b>%d</b>%s</td></tr>'
      "<tr><td>Equal / can't tell</td><td align='right' style='font-size:12pt'>%d</td></tr>"
      '<tr><td>Portions judged</td><td align="right">%d / %d</td></tr></table>'
      % (SIDE_COLORS[TOP], counts['top'], percent(counts['top']), SIDE_COLORS[BOTTOM], counts['bottom'], percent(counts['bottom']),
         counts['equal'], len(self.choices), len(self.portions)))

  def _scoreText(self):
    counts = {key: 0 for key in CHOICE_TEXTS}
    for chosen, _ in self.choices.values():
      counts[chosen] += 1
    return ('TOP (group 1) better: %d\nBOTTOM (group 2) better: %d\nEqual / can\'t tell: %d\n(portions judged: %d of %d)'
            % (counts['top'], counts['bottom'], counts['equal'], len(self.choices), len(self.portions)))

  def _saveChoices(self):
    try:
      with open(self.csvPath, 'w', newline='') as csvFile:
        writer = csv.writer(csvFile)
        writer.writerow(['portion', 'round', 'video', 'choice', 'firstFrameShown', 'lastFrameShown', 'differenceFirstFrame',
                         'differenceLastFrame', 'differenceScore', 'differences', 'topResults(group1)', 'bottomResults(group2)', 'choiceTime'])
        for index in sorted(self.choices):
          portion = self.portions[index]
          choice, when = self.choices[index]
          writer.writerow([index + 1, portion.roundNumber, portion.pair.name, CHOICE_TEXTS[choice], portion.start, portion.end,
                           portion.group.start, portion.group.end, round(portion.group.score, 1), ' | '.join(portion.describe(maxLines=100)),
                           portion.pair.results[TOP].filename, portion.pair.results[BOTTOM].filename, when.strftime('%Y-%m-%d %H:%M:%S')])
    except OSError as error:
      QMessageBox.warning(self, 'Could not save the choices', str(error))

  # --- Drawing ---

  def _updateInfo(self):
    portion = self.portions[self.index]
    pair = portion.pair
    differences = ''.join('<li>%s</li>' % line for line in portion.describe())
    self.infoLabel.setText(
      '<b>Portion %d / %d</b> &nbsp;&middot;&nbsp; round %d (video %d / %d of this round)<br>'
      '<span style="font-size:13pt"><b>%s</b></span><br>'
      'Difference score <b>%.0f</b> (%s biggest of this video)'
      '<ul style="margin-left:-20px">%s</ul>'
      % (self.index + 1, len(self.portions), portion.roundNumber, portion.positionInRound, portion.roundSize, pair.name,
         portion.group.score, _ordinal(portion.rankInVideo), differences))

  def _zoomRectangle(self, portion, frameSize):
    frameWidth, frameHeight = frameSize
    points = np.concatenate([difference.positions for difference in portion.group.differences])
    x0, y0 = np.nanmin(points, axis=0)
    x1, y1 = np.nanmax(points, axis=0)
    padding = max(80, 4 * self.params.matchingDistance)
    viewAspect = self.views[TOP].width() / max(self.views[TOP].height(), 1)
    height = max(y1 - y0 + 2 * padding, (x1 - x0 + 2 * padding) / viewAspect, frameHeight * 0.3)
    height = min(height, frameHeight)
    width = min(max(height * viewAspect, x1 - x0 + 2 * padding), frameWidth)
    if width >= frameWidth * 0.98 and height >= frameHeight * 0.98:
      return None
    x = min(max((x0 + x1) / 2 - width / 2, 0), frameWidth - width)
    y = min(max((y0 + y1) / 2 - height / 2, 0), frameHeight - height)
    return (x, y, width, height)

  def render(self):
    portion = self.portions[self.index]
    pair = portion.pair
    data = [self._tracking(pair.results[side].path) for side in (TOP, BOTTOM)]
    frame = self.frame

    if pair.videoPath is None:
      status, image = 'missing', None
    else:
      status, image = self.loader.getFrame(pair.videoPath, frame)
    if image is not None:
      frameSize = (image.shape[1], image.shape[0])
    elif pair.videoPath in self.loader.videoInfo:
      frameSize = self.loader.videoInfo[pair.videoPath][:2]
    elif pair.frameSize:
      frameSize = pair.frameSize
    else:
      allPoints = np.concatenate([d.positions.reshape(-1, 2) for d in data])
      frameSize = (int(np.nanmax(allPoints[:, 0])) + 20, int(np.nanmax(allPoints[:, 1])) + 20) if np.isfinite(allPoints).any() else (640, 480)
    message = ''
    if status == 'loading':
      message = 'Loading video frames... (%d / %d)' % (self.loader.countLoaded(pair.videoPath, portion.start, portion.end), portion.end - portion.start + 1)
      self.refreshTimer.start(80)
    elif status == 'error':
      message = 'Frame %d could not be read from the video' % frame
    elif status == 'missing':
      message = 'Video not found:\n%s\nUse "Locate video..." on the right' % pair.originalVideoPath
    qImage = toQImage(image) if image is not None else None
    crop = self._zoomRectangle(portion, frameSize) if self.zoomCheckbox.isChecked() else None

    points = [d.pointsAt(frame) for d in data]
    matched = matchPoints(points[TOP][1], points[BOTTOM][1], self.params.matchingDistance)
    overlays = [Overlay(), Overlay()]
    for side in (TOP, BOTTOM):
      trajectories, positions = points[side]
      overlay = overlays[side]
      index = frame - data[side].firstFrame
      for k, (x, y) in zip(trajectories, positions):
        color = data[side].colors[k]
        overlay.points.append((x, y, color))
        if self.trailsCheckbox.isChecked():
          trail = data[side].positions[k, max(0, index - TRAIL_LENGTH):index + 1]
          for start, end in stretches(~np.isnan(trail[:, 0])):
            overlay.trails.append((color, trail[start:end + 1].tolist()))
      if self.disagreementsCheckbox.isChecked():
        overlay.disagreements = positions[~matched[side]].tolist()
    for difference in portion.group.differences:
      for start, end in difference.pathSegments:
        segment = difference.positions[start:end + 1].tolist()
        overlays[TOP].focusPaths.append(segment)
        overlays[BOTTOM].focusPaths.append(segment)
      position = difference.positionAt(frame)
      if position is not None:
        overlays[difference.side].focus.append(tuple(position))
        overlays[1 - difference.side].ghosts.append(tuple(position))

    ringRadius = self.params.matchingDistance * 0.5
    for side in (TOP, BOTTOM):
      self.views[side].setContent(qImage, frameSize, crop, overlays[side], message if side == TOP or status != 'loading' else '', ringRadius)
      results = pair.results[side]
      self.headers[side].setText('%s  &middot;  group %d  &middot;  %s  &middot;  %d points tracked on this frame%s'
                                 % ('▲ TOP' if side == TOP else '▼ BOTTOM', side + 1, results.filename,
                                    len(points[side][0]), '  &middot;  zoomed (Z: full frame)' if crop is not None else ''))
    self.timeline.setCurrent(frame)
    self.frameLabel.setText('Frame <b>%d</b> &nbsp;(shown: %d – %d, difference: %d – %d)'
                            % (frame, portion.start, portion.end, portion.group.start, portion.group.end))

  def closeEvent(self, event):
    self.playTimer.stop()
    self.refreshTimer.stop()
    self.loader.stop()
    if self.choices:
      print('\nTracking comparison saved in %s\n%s' % (self.csvPath, self._scoreText()))
    if self.onClose is not None:
      self.onClose()
    super().closeEvent(event)


def _ordinal(number):
  if number == 1:
    return 'the'
  suffix = 'th' if 10 <= number % 100 <= 20 else {1: 'st', 2: 'nd', 3: 'rd'}.get(number % 10, 'th')
  return '%d%s' % (number, suffix)


# ------------------------------------------------------------------------------------------------
# Group selection window
# ------------------------------------------------------------------------------------------------

class AnalysisThread(QThread):
  progress = pyqtSignal(int, str)
  finishedAnalysis = pyqtSignal(object, object)

  def __init__(self, videos, params, zzOutputFolder):
    super().__init__()
    self.videos = videos
    self.params = params
    self.zzOutputFolder = zzOutputFolder

  def run(self):
    pairs = []
    errors = []
    for i, (name, topResults, bottomResults) in enumerate(self.videos):
      if self.isInterruptionRequested():
        break
      self.progress.emit(i, name)
      try:
        pairs.append(analyzeVideoPair(name, topResults, bottomResults, self.params, self.zzOutputFolder))
      except Exception as error:
        errors.append('%s: %s' % (name, error))
    self.finishedAnalysis.emit(pairs, errors)


class SelectionWindow(QWidget):

  def __init__(self, zzOutputFolder):
    super().__init__()
    self.setWindowTitle('Compare two groups of tracking results')
    self.resize(1150, 780)
    self.zzOutputFolder = zzOutputFolder
    self.resultsByPath = {}
    self.comparisonWindow = None
    self.analysisThread = None
    self._summaryPending = False

    layout = QVBoxLayout(self)
    folderLayout = QHBoxLayout()
    self.folderLabel = QLabel()
    changeFolderButton = QPushButton('Change folder...')
    changeFolderButton.clicked.connect(self.changeFolder)
    folderLayout.addWidget(self.folderLabel, 1)
    folderLayout.addWidget(changeFolderButton)
    layout.addLayout(folderLayout)

    instructions = QLabel(
      'Tick the results of the <b>first group</b> on the left (they will be shown at the <b style="color:%s">TOP</b>), and the results '
      'of the <b>second group</b> on the right (shown at the <b style="color:%s">BOTTOM</b>). The two groups should contain the results of '
      'the same videos tracked with different algorithms (results are paired by video name).<br>Results are listed by tracking session '
      '(results whose tracking started less than %d minutes apart), most recent first: tick a session to select all its results.'
      % (SIDE_COLORS[TOP], SIDE_COLORS[BOTTOM], BATCH_GAP_MINUTES))
    instructions.setWordWrap(True)
    layout.addWidget(instructions)

    treesLayout = QHBoxLayout()
    self.trees = []
    self.groupLabels = []
    for side in (TOP, BOTTOM):
      box = QGroupBox('%d. %s group: shown at the %s' % (side + 1, ('First', 'Second')[side], SIDE_NAMES[side]))
      box.setStyleSheet('QGroupBox {font-weight: bold; color: %s;}' % SIDE_COLORS[side])
      boxLayout = QVBoxLayout(box)
      tree = QTreeWidget()
      tree.setHeaderHidden(True)
      tree.itemChanged.connect(self._scheduleSummary)
      label = QLabel()
      boxLayout.addWidget(tree)
      boxLayout.addWidget(label)
      treesLayout.addWidget(box)
      self.trees.append(tree)
      self.groupLabels.append(label)
    layout.addLayout(treesLayout, 1)

    self.summaryLabel = QLabel()
    self.summaryLabel.setWordWrap(True)
    layout.addWidget(self.summaryLabel)

    parametersLayout = QHBoxLayout()
    self.matchingDistanceSpin = self._spinBox(1, 1000, MATCHING_DISTANCE, ' px')
    self.minLengthSpin = self._spinBox(1, 100000, MIN_DIFFERENCE_LENGTH, ' frames')
    self.marginSpin = self._spinBox(0, 100000, PORTION_MARGIN, ' frames')
    for text, spin, tooltip in (
        ('Matching distance:', self.matchingDistanceSpin, 'Points of the two results closer than this are considered to be the same fish'),
        ('Ignore differences shorter than:', self.minLengthSpin, 'Differences lasting fewer frames than this are not shown'),
        ('Frames shown before/after each difference:', self.marginSpin, '')):
      label = QLabel(text)
      label.setToolTip(tooltip)
      spin.setToolTip(tooltip)
      parametersLayout.addWidget(label)
      parametersLayout.addWidget(spin)
      parametersLayout.addSpacing(16)
    parametersLayout.addStretch(1)
    self.compareButton = QPushButton('Find and show the differences')
    self.compareButton.setMinimumHeight(36)
    self.compareButton.setStyleSheet('font-weight: bold; font-size: 11pt; padding: 4px 16px;')
    self.compareButton.clicked.connect(self.compare)
    parametersLayout.addWidget(self.compareButton)
    layout.addLayout(parametersLayout)

    self.populate()

  def _spinBox(self, minimum, maximum, value, suffix):
    spin = QSpinBox()
    spin.setRange(minimum, maximum)
    spin.setValue(value)
    spin.setSuffix(suffix)
    return spin

  def changeFolder(self):
    folder = QFileDialog.getExistingDirectory(self, 'Select the ZZoutput folder', self.zzOutputFolder)
    if folder:
      self.zzOutputFolder = os.path.normpath(folder)
      self.populate()

  def populate(self):
    self.folderLabel.setText('ZZoutput folder: <b>%s</b>' % self.zzOutputFolder)
    resultsFiles = listResultsFiles(self.zzOutputFolder)
    self.resultsByPath = {resultsFile.path: resultsFile for resultsFile in resultsFiles}
    sessions = groupIntoTrackingSessions(resultsFiles)
    for tree in self.trees:
      tree.blockSignals(True)
      tree.clear()
      for session in sessions:
        first, last = session[0].trackingTime, session[-1].trackingTime
        if first.date() == last.date():
          period = '%s   %s → %s' % (first.strftime('%Y-%m-%d'), first.strftime('%H:%M'), last.strftime('%H:%M'))
        else:
          period = '%s → %s' % (first.strftime('%Y-%m-%d %H:%M'), last.strftime('%Y-%m-%d %H:%M'))
        sessionItem = QTreeWidgetItem(['%s   (%d results)' % (period, len(session))])
        sessionItem.setFlags(Qt.ItemIsEnabled | Qt.ItemIsUserCheckable | Qt.ItemIsAutoTristate)
        sessionItem.setCheckState(0, Qt.Unchecked)
        for resultsFile in session:
          item = QTreeWidgetItem(['%s    %s' % (resultsFile.trackingTime.strftime('%H:%M:%S' if first.date() == last.date() else '%Y-%m-%d %H:%M:%S'), resultsFile.videoName)])
          item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsUserCheckable | Qt.ItemNeverHasChildren)
          item.setCheckState(0, Qt.Unchecked)
          item.setData(0, Qt.UserRole, resultsFile.path)
          item.setToolTip(0, resultsFile.filename)
          sessionItem.addChild(item)
        tree.addTopLevelItem(sessionItem)
      tree.blockSignals(False)
    self.updateSummary()

  def _scheduleSummary(self, *args):
    if not self._summaryPending:
      self._summaryPending = True
      QTimer.singleShot(0, self.updateSummary)

  def selectedResults(self, side):
    tree = self.trees[side]
    selected = []
    for i in range(tree.topLevelItemCount()):
      sessionItem = tree.topLevelItem(i)
      for j in range(sessionItem.childCount()):
        item = sessionItem.child(j)
        if item.checkState(0) == Qt.Checked:
          selected.append(self.resultsByPath[item.data(0, Qt.UserRole)])
    return selected

  def pairedVideos(self):
    """Returns [(videoName, topResults, bottomResults)] and a list of warnings."""
    warnings = []
    byName = []
    for side in (TOP, BOTTOM):
      results = {}
      for resultsFile in sorted(self.selectedResults(side), key=lambda r: r.trackingTime):
        if resultsFile.videoName in results:
          warnings.append('%s is selected several times in group %d: the most recent results are used' % (resultsFile.videoName, side + 1))
        results[resultsFile.videoName] = resultsFile
      byName.append(results)
    commonNames = sorted(set(byName[TOP]) & set(byName[BOTTOM]), key=str.lower)
    for side in (TOP, BOTTOM):
      alone = sorted(set(byName[side]) - set(byName[1 - side]), key=str.lower)
      if alone:
        warnings.append('%d video(s) only in group %d, ignored: %s%s' % (len(alone), side + 1, ', '.join(alone[:6]), ', ...' if len(alone) > 6 else ''))
    sameFiles = [name for name in commonNames if byName[TOP][name].path == byName[BOTTOM][name].path]
    if sameFiles:
      warnings.append('%d video(s) have the same results file in both groups, ignored: %s' % (len(sameFiles), ', '.join(sameFiles[:6])))
    videos = [(name, byName[TOP][name], byName[BOTTOM][name]) for name in commonNames if name not in sameFiles]
    return videos, warnings

  def updateSummary(self):
    self._summaryPending = False
    for side in (TOP, BOTTOM):
      self.groupLabels[side].setText('%d results selected' % len(self.selectedResults(side)))
    videos, warnings = self.pairedVideos()
    text = '<b>%d video(s) tracked in both groups.</b>' % len(videos)
    if warnings:
      text += '<br><span style="color:#b45309">%s</span>' % '<br>'.join(warnings)
    self.summaryLabel.setText(text)
    self.compareButton.setEnabled(len(videos) > 0)

  def compare(self):
    videos, _ = self.pairedVideos()
    if not videos:
      return
    self.params = Parameters(self.matchingDistanceSpin.value(), self.minLengthSpin.value(), self.marginSpin.value())
    self.progressDialog = QProgressDialog('Comparing the tracking results...', 'Cancel', 0, len(videos), self)
    self.progressDialog.setWindowTitle('Finding the differences')
    self.progressDialog.setWindowModality(Qt.WindowModal)
    self.progressDialog.setMinimumDuration(0)
    self.analysisThread = AnalysisThread(videos, self.params, self.zzOutputFolder)
    self.analysisThread.progress.connect(lambda i, name: (self.progressDialog.setValue(i), self.progressDialog.setLabelText('Comparing the tracking results of %s...' % name)))
    self.analysisThread.finishedAnalysis.connect(self._analysisFinished)
    self.progressDialog.canceled.connect(self.analysisThread.requestInterruption)
    self.compareButton.setEnabled(False)
    self.analysisThread.start()

  def _analysisFinished(self, pairs, errors):
    canceled = self.progressDialog.wasCanceled()
    self.progressDialog.close()
    self.compareButton.setEnabled(True)
    if canceled:
      return
    if errors:
      QMessageBox.warning(self, 'Some results could not be compared', '\n'.join(errors[:20]))
    portions = orderPortions(pairs, self.params.portionMargin)
    printSummary(pairs, portions)
    if not portions:
      QMessageBox.information(self, 'No difference', 'No difference was found between the two groups of tracking results.')
      return
    missingVideos = sorted({pair.originalVideoPath for pair in pairs if pair.videoPath is None and pair.groups})
    if missingVideos:
      QMessageBox.warning(self, 'Videos not found', 'These videos could not be found (you can locate them from the comparison window):\n\n' + '\n'.join(missingVideos[:20]))
    self.comparisonWindow = ComparisonWindow(portions, self.params, self.zzOutputFolder, onClose=self.show)
    self.comparisonWindow.showMaximized()
    self.hide()


def printSummary(pairs, portions):
  print('\n%d videos compared, %d portions of video to show' % (len(pairs), len(portions)))
  print('Biggest difference of each video:')
  for pair in sorted(pairs, key=lambda pair: -pair.groups[0].score if pair.groups else 0):
    if pair.groups:
      group = pair.groups[0]
      print('  %-45s %3d portions, biggest: score %6.0f, frames %d-%d: %s' % (pair.name, len(pair.groups), group.score, group.start, group.end, group.differences[0].describe()))
    else:
      print('  %-45s no difference (frames %d-%d compared)' % (pair.name, pair.start, pair.end))


# ------------------------------------------------------------------------------------------------

def findZZoutputFolder():
  candidates = []
  try:
    spec = importlib.util.find_spec('zebrazoom')
    if spec is not None and spec.submodule_search_locations:
      candidates += [os.path.join(location, 'ZZoutput') for location in spec.submodule_search_locations]
  except (ImportError, ValueError):
    pass
  scriptFolder = os.path.dirname(os.path.abspath(__file__))
  candidates += [os.path.join(scriptFolder, '..', 'zebrazoom', 'ZZoutput'), os.path.join(scriptFolder, 'ZZoutput'),
                 os.path.join(os.path.expanduser('~'), 'Documents', 'ZebraZoom', 'ZZoutput')]
  for candidate in candidates:
    if os.path.isdir(candidate):
      return os.path.normpath(candidate)
  return None


def main():
  app = QApplication(sys.argv)
  folder = sys.argv[1] if len(sys.argv) > 1 else findZZoutputFolder()
  if not folder or not os.path.isdir(folder):
    folder = QFileDialog.getExistingDirectory(None, 'Select the ZZoutput folder')
    if not folder:
      return
  window = SelectionWindow(os.path.normpath(folder))
  window.show()
  sys.exit(app.exec_())


if __name__ == '__main__':
  main()
