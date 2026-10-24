"""
compareTrackingResults.py

Standalone PyQt5 GUI to decide which of two tracking algorithms (or two
variations of the same algorithm) works best, by comparing two groups of
ZebraZoom tracking results of the SAME videos.

This script is entirely self-contained: it only needs PyQt5, opencv,
h5py and numpy (it doesn't import anything from ZebraZoom itself).

Usage:

    python compareTrackingResults.py [pathToZZoutputFolder]

Workflow:
  1. Select the FIRST group of .h5 results files of the ZZoutput folder.
     The list is sorted by tracking time (most recent first): click the
     first results file of the group and shift-click the last one to
     select all the results tracked in between. These results are shown
     at the TOP of the comparison window.
  2. Select the SECOND group of results files, shown at the BOTTOM.
     Results of the two groups are paired by video name (the results file
     name without its tracking date and time).
  3. For each pair, the script finds where the two tracking results
     disagree (see "How differences are found" below) and ranks these
     differences.
  4. The comparison window then shows one portion of video at a time:
     the same video frame at the top (with the tracking of group 1) and
     at the bottom (with the tracking of group 2). Move through the
     portion with the Left/Right arrow keys, then click "TOP is better" or
     "BOTTOM is better" on the right side of the window (or press the
     Up/Down arrow keys). The scoreboard on the right counts how many
     portions each group won. Every choice is also saved to
     trackingComparison_[date].csv in the ZZoutput folder.

Order in which the portions of video are shown:
  First the biggest difference of each video (the videos being ordered by
  the size of that difference, biggest first), then the second biggest
  difference of each video (again ordered by size), and so on. The most
  informative portions are therefore shown first, and every video gets a
  turn before any video is shown a second time.

How differences are found:
  On every frame, the tracking points of the two results are paired
  one-to-one (closest pairs first) when they are less than "matching
  distance" pixels apart. A point left without a partner means that one
  result has a fish there that the other result doesn't have. For each
  trajectory, these unpaired points are grouped into stretches of
  consecutive frames (stretches separated by only a few frames being
  merged): each stretch is one difference, whose size is its number of
  unpaired frames. A long trajectory present in only one of the results
  (or a trajectory the other result doesn't have at all) is therefore a
  big difference, while a trajectory lasting a few frames longer than in
  the other result is a small one. Differences of the same video that
  overlap in time are shown together in the same portion of video.

  The last frame of each results file is ignored: on ZebraZoom results
  post-processed with synthesizeTracksFromDetectionCloud, it still holds
  raw, unprocessed tracking points.

Video frames are read sequentially from the beginning of the video,
exactly like ZebraZoom does during tracking (seeking directly to a frame
number gives wrong frames on some AVI files).

Keyboard shortcuts in the comparison window:
  Left / Right           previous / next frame (10 frames with Shift)
  Home / End             first / last frame of the portion
  Space                  play / pause
  Up or T                TOP is better
  Down or B              BOTTOM is better
  S                      can't tell (counted separately)
  Page Up / Page Down    previous / next portion (without choosing)
"""

import csv
import datetime
import importlib.util
import os
import re
import sys
import threading

import cv2
import h5py
import numpy as np

from PyQt5.QtCore import QEvent, Qt, QTimer
from PyQt5.QtGui import QFont, QImage, QPixmap
from PyQt5.QtWidgets import (
    QAbstractItemView,
    QApplication,
    QCheckBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressDialog,
    QPushButton,
    QSizePolicy,
    QSlider,
    QSpinBox,
    QTreeWidget,
    QTreeWidgetItem,
    QVBoxLayout,
    QWidget,
)


# Two tracking points (one from each group of results) closer than this many
# pixels are considered to be the same fish. On the 1280x720 cavefish videos
# this was set up with, the points of the same fish in two results are
# almost always less than 5 px apart, while two different fish are very
# rarely less than 15 px apart.
DEFAULT_MATCHING_DISTANCE = 15
# Differences lasting fewer frames than this are ignored.
DEFAULT_MIN_DIFFERENCE_FRAMES = 3
# Number of frames shown before and after each difference.
DEFAULT_CONTEXT_FRAMES = 15
# Unpaired stretches of the same trajectory separated by at most this many
# frames are merged into a single difference (e.g. a trajectory missing from
# the other result which briefly passes next to another fish).
MERGE_GAP_FRAMES = 5
# Differences of the same video whose paths come closer than this many times
# the matching distance (on frames at most MERGE_GAP_FRAMES apart) are the
# same event, shown together in one portion of video: e.g. a trajectory
# leaving its fish in one result while the other result keeps following
# that fish, or a fish followed by two consecutive trajectories.
SAME_EVENT_DISTANCE_FACTOR = 3

SIDE_NAMES = ("TOP", "BOTTOM")
CHOICE_LABELS = {"top": "TOP (group 1)", "bottom": "BOTTOM (group 2)", "tie": "can't tell"}

# Drawing (BGR colors).
TRAIL_LENGTH = 10  # frames
POINT_RADIUS = 3  # display pixels
POINT_COLOR = (0, 255, 0)
TRAIL_COLOR = (0, 190, 0)
OUTLINE_COLOR = (0, 0, 0)
ONLY_HERE_COLOR = (0, 0, 255)  # trajectory present in this result only
MISSING_HERE_COLOR = (0, 255, 255)  # trajectory present in the other result only

# Video frames of the portions being looked at are kept in memory as JPEG
# images (a few hundred raw frames would take gigabytes).
JPEG_QUALITY = 92

# Same default as ZebraZoom's validation video viewer "Contrast" checkbox.
CONTRAST_QUANTILE = 0.01

RESULTS_TIMESTAMP_REGEX = re.compile(r"^(?P<videoName>.+)_(?P<timestamp>\d{4}_\d{2}_\d{2}-\d{2}_\d{2}_\d{2})$")
FULL_VIDEO_COPY_SUFFIX = "_originalVideoWithoutAnyTrackingDisplayed_pleaseUseTheGUIToVisualizeTrackingPoints.avi"


def getDefaultZZoutputFolder():
    candidates = [os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "zebrazoom", "ZZoutput")]
    # Location of an installed zebrazoom package, found without importing it.
    spec = importlib.util.find_spec("zebrazoom")
    if spec is not None and spec.submodule_search_locations:
        candidates.append(os.path.join(list(spec.submodule_search_locations)[0], "ZZoutput"))
    candidates.append(os.path.join(os.path.expanduser("~"), "Documents", "ZebraZoom", "ZZoutput"))
    for candidate in candidates:
        if os.path.isdir(candidate):
            return candidate
    return os.getcwd()


def improveContrast(frame):
    """Same contrast enhancement as ZebraZoom's validation video viewer (zebrazoom.code.createValidationVideo)."""
    gray = cv2.cvtColor(255 - frame, cv2.COLOR_BGR2GRAY)
    lowVal = int(np.quantile(gray, CONTRAST_QUANTILE))
    highVal = int(np.quantile(gray, 1 - CONTRAST_QUANTILE))
    gray = np.clip(gray, lowVal, highVal) - lowVal
    gray = (gray * (255 / max(int(gray.max()), 1))).astype(np.uint8)
    return cv2.cvtColor(gray, cv2.COLOR_GRAY2BGR)


# ----------------------------------------------------------------------
# Results files
# ----------------------------------------------------------------------

def describeResultsFile(path):
    fileName = os.path.basename(path)
    baseName = os.path.splitext(fileName)[0]
    match = RESULTS_TIMESTAMP_REGEX.match(baseName)
    if match:
        videoName = match.group("videoName")
        trackingTime = datetime.datetime.strptime(match.group("timestamp"), "%Y_%m_%d-%H_%M_%S")
    else:
        videoName = baseName
        trackingTime = datetime.datetime.fromtimestamp(os.path.getmtime(path))
    return {"path": path, "fileName": fileName, "videoName": videoName, "trackingTime": trackingTime}


def listResultsFiles(folder):
    resultsFiles = []
    for fileName in os.listdir(folder):
        path = os.path.join(folder, fileName)
        if fileName.lower().endswith(".h5") and os.path.isfile(path):
            resultsFiles.append(describeResultsFile(path))
    resultsFiles.sort(key=lambda resultsFile: resultsFile["trackingTime"], reverse=True)
    return resultsFiles


def pairResultsFiles(group1, group2):
    """
    Pairs the results files of the two groups by video name.

    Returns (pairs, unpaired1, unpaired2, duplicates): pairs is a list of
    (videoName, resultsFile1, resultsFile2) sorted by video name. When a
    group holds several results of the same video, the most recently
    tracked one is used and the others are listed in duplicates.
    """
    def latestResultsPerVideo(group):
        latest = {}
        duplicates = []
        for resultsFile in sorted(group, key=lambda resultsFile: resultsFile["trackingTime"]):
            key = resultsFile["videoName"].lower()
            if key in latest:
                duplicates.append(latest[key])
            latest[key] = resultsFile
        return latest, duplicates

    latest1, duplicates1 = latestResultsPerVideo(group1)
    latest2, duplicates2 = latestResultsPerVideo(group2)
    pairs = [(latest1[key]["videoName"], latest1[key], latest2[key]) for key in sorted(latest1) if key in latest2]
    unpaired1 = [latest1[key] for key in sorted(latest1) if key not in latest2]
    unpaired2 = [latest2[key] for key in sorted(latest2) if key not in latest1]
    return pairs, unpaired1, unpaired2, duplicates1 + duplicates2


class TrackingResults:
    """
    Tracking points of one ZebraZoom .h5 results file: trajectories is an
    array of shape (nbTrajectories, nbFrames, 2) holding the (x, y)
    position (in whole video frame coordinates) of each trajectory on each
    frame from firstFrame to lastFrame, NaN where there is no point.
    """

    def __init__(self, path):
        self.path = path
        self.fileName = os.path.basename(path)
        self.trajectoryNames = []
        trajectories = []
        frameSize = None
        with h5py.File(path, "r") as results:
            self.firstFrame = int(results.attrs.get("firstFrame", 0))
            self.lastFrame = int(results.attrs.get("lastFrame", self.firstFrame))
            pathToOriginalVideo = results.attrs.get("pathToOriginalVideo", "")
            if isinstance(pathToOriginalVideo, bytes):
                pathToOriginalVideo = pathToOriginalVideo.decode("utf-8")
            self.pathToOriginalVideo = str(pathToOriginalVideo)
            exampleFrame = results.get("exampleFrame")
            if isinstance(exampleFrame, h5py.Dataset) and len(exampleFrame.shape) >= 2:
                frameSize = (int(exampleFrame.shape[1]), int(exampleFrame.shape[0]))

            nbFrames = self.lastFrame - self.firstFrame + 1
            wellNames = sorted(
                (name for name in results.keys() if name.startswith("dataForWell")),
                key=lambda name: int(name[len("dataForWell"):]),
            )
            for wellName in wellNames:
                wellIndex = int(wellName[len("dataForWell"):])
                wellGroup = results[wellName]
                offsetX, offsetY = 0, 0
                wellPositionGroup = results.get(f"wellPositions/well{wellIndex}")
                if wellPositionGroup is not None:
                    offsetX = int(wellPositionGroup.attrs.get("topLeftX", 0))
                    offsetY = int(wellPositionGroup.attrs.get("topLeftY", 0))
                animalNames = sorted(
                    (name for name in wellGroup.keys() if name.startswith("dataForAnimal")),
                    key=lambda name: int(name[len("dataForAnimal"):]),
                )
                for animalName in animalNames:
                    headPosDataset = wellGroup.get(f"{animalName}/dataPerFrame/HeadPos")
                    if headPosDataset is None:
                        continue
                    headPos = headPosDataset[:]
                    nbRows = min(nbFrames, len(headPos))
                    rawX = np.asarray(headPos["X"][:nbRows], dtype=float)
                    rawY = np.asarray(headPos["Y"][:nbRows], dtype=float)
                    # (0, 0) is the "no point on this frame" convention used throughout ZebraZoom.
                    noPoint = ~np.isfinite(rawX) | ~np.isfinite(rawY) | ((rawX == 0) & (rawY == 0))
                    if noPoint.all():
                        continue
                    trajectory = np.full((nbFrames, 2), np.nan)
                    trajectory[:nbRows, 0] = np.where(noPoint, np.nan, rawX + offsetX)
                    trajectory[:nbRows, 1] = np.where(noPoint, np.nan, rawY + offsetY)
                    trajectories.append(trajectory)
                    self.trajectoryNames.append(animalName if len(wellNames) == 1 else f"{wellName}/{animalName}")

        self.trajectories = np.array(trajectories) if trajectories else np.full((0, max(nbFrames, 0), 2), np.nan)
        if frameSize is None:
            maxX, maxY = (np.nanmax(self.trajectories, axis=(0, 1)) if len(trajectories) else (640, 480))
            frameSize = (int(maxX) + 20, int(maxY) + 20)
        self.frameSize = frameSize

    def positionsBetween(self, firstFrame, lastFrame, trajectoryIndex=None):
        """Positions from firstFrame to lastFrame (included), NaN on frames outside of the tracked range."""
        rows = np.arange(firstFrame, lastFrame + 1) - self.firstFrame
        inside = (rows >= 0) & (rows < self.trajectories.shape[1])
        trajectories = self.trajectories if trajectoryIndex is None else self.trajectories[trajectoryIndex:trajectoryIndex + 1]
        positions = np.full((len(trajectories), len(rows), 2), np.nan)
        positions[:, inside] = trajectories[:, rows[inside]]
        return positions if trajectoryIndex is None else positions[0]


# ----------------------------------------------------------------------
# Finding and ranking the differences between two tracking results
# ----------------------------------------------------------------------

class Difference:
    """A stretch of frames during which one trajectory of one result has no counterpart in the other result."""

    def __init__(self, side, trajectoryIndex, trajectoryName, startFrame, endFrame, nbFrames, wholeTrajectory, path):
        self.side = side  # 0: present in the top results only, 1: present in the bottom results only
        self.trajectoryIndex = trajectoryIndex
        self.trajectoryName = trajectoryName
        self.startFrame = startFrame
        self.endFrame = endFrame
        self.nbFrames = nbFrames  # number of unpaired frames: the size of the difference
        self.wholeTrajectory = wholeTrajectory  # no point of this trajectory has a counterpart in the other result
        self.path = path  # (x, y) positions of the trajectory from startFrame to endFrame
        valid = self.path[np.isfinite(self.path[:, 0])]
        self.boundingBox = (*valid.min(axis=0), *valid.max(axis=0))  # (minX, minY, maxX, maxY)

    def positionsBetween(self, firstFrame, lastFrame):
        """Positions of the trajectory from firstFrame to lastFrame (included), NaN outside of this difference."""
        positions = np.full((lastFrame - firstFrame + 1, 2), np.nan)
        first, last = max(firstFrame, self.startFrame), min(lastFrame, self.endFrame)
        if last >= first:
            positions[first - firstFrame:last - firstFrame + 1] = self.path[first - self.startFrame:last - self.startFrame + 1]
        return positions

    def isCloseTo(self, other, maxDistance, maxFrameGap):
        """True when the paths of the two differences come within maxDistance of each other, on frames at most maxFrameGap apart."""
        start = max(self.startFrame, other.startFrame) - maxFrameGap
        end = min(self.endFrame, other.endFrame) + maxFrameGap
        if end < start:
            return False
        boxGapX = max(self.boundingBox[0] - other.boundingBox[2], other.boundingBox[0] - self.boundingBox[2])
        boxGapY = max(self.boundingBox[1] - other.boundingBox[3], other.boundingBox[1] - self.boundingBox[3])
        if max(boxGapX, boxGapY) > maxDistance:
            return False
        ownPositions = self.positionsBetween(start - maxFrameGap, end + maxFrameGap)
        otherPositions = other.positionsBetween(start, end)
        for offset in range(2 * maxFrameGap + 1):
            shifted = ownPositions[offset:offset + len(otherPositions)]
            # NaN distances (no point on one of the frames) compare as False.
            if np.any(np.hypot(shifted[:, 0] - otherPositions[:, 0], shifted[:, 1] - otherPositions[:, 1]) <= maxDistance):
                return True
        return False

    def describe(self):
        here, other = SIDE_NAMES[self.side], SIDE_NAMES[1 - self.side]
        frames = f"{self.nbFrames} frames, between frames {self.startFrame} and {self.endFrame}"
        if self.wholeTrajectory:
            return f"{here} has a trajectory that {other} doesn't have at all ({frames})"
        return f"{here} tracks a fish where {other} has nothing ({frames})"


class Portion:
    """A portion of one video showing one difference, or several differences that are part of the same event."""

    def __init__(self, pair, difference, contextFrames):
        self.pair = pair
        self.contextFrames = contextFrames
        self.differences = []
        self.score = 0
        self.differencesStart = difference.startFrame
        self.differencesEnd = difference.endFrame
        self.rankInVideo = 0
        self.round = 0
        self.add(difference)

    def add(self, difference):
        self.differences.append(difference)
        self.score += difference.nbFrames
        self.differencesStart = min(self.differencesStart, difference.startFrame)
        self.differencesEnd = max(self.differencesEnd, difference.endFrame)
        self.startFrame = max(self.pair.analysisStart, self.differencesStart - self.contextFrames)
        self.endFrame = min(self.pair.analysisEnd, self.differencesEnd + self.contextFrames)


class VideoPair:
    """The two tracking results (top and bottom) of the same video, and the portions where they differ."""

    def __init__(self, videoName, results1, results2):
        self.videoName = videoName
        self.results = (results1, results2)
        self.analysisStart = max(results1.firstFrame, results2.firstFrame)
        # The last frame is left out: see "How differences are found" at the top of this file.
        self.analysisEnd = min(results1.lastFrame, results2.lastFrame) - 1
        self.portions = []
        self.videoPath = findVideo(self.results)
        self.videoPathAsked = False
        self.frameSize = results1.frameSize


def findStretches(frameIndices, maxGap):
    """Splits sorted frame indices into stretches whose consecutive indices are at most maxGap frames apart: [(first, last, nbIndices)]."""
    if len(frameIndices) == 0:
        return []
    breaks = np.flatnonzero(np.diff(frameIndices) > maxGap + 1)
    starts = np.concatenate(([0], breaks + 1))
    ends = np.concatenate((breaks, [len(frameIndices) - 1]))
    return [(int(frameIndices[start]), int(frameIndices[end]), int(end - start + 1)) for start, end in zip(starts, ends)]


def findDifferences(pair, matchingDistance, minDifferenceFrames):
    if pair.analysisEnd < pair.analysisStart:
        return []
    points = [results.positionsBetween(pair.analysisStart, pair.analysisEnd) for results in pair.results]
    hasPoint = [np.isfinite(positions[:, :, 0]) for positions in points]
    paired = [np.zeros_like(present) for present in hasPoint]

    for frameIndex in range(pair.analysisEnd - pair.analysisStart + 1):
        indices1 = np.flatnonzero(hasPoint[0][:, frameIndex])
        indices2 = np.flatnonzero(hasPoint[1][:, frameIndex])
        if len(indices1) == 0 or len(indices2) == 0:
            continue
        positions1 = points[0][indices1, frameIndex]
        positions2 = points[1][indices2, frameIndex]
        distances = np.hypot(positions1[:, None, 0] - positions2[None, :, 0], positions1[:, None, 1] - positions2[None, :, 1])
        candidates1, candidates2 = np.nonzero(distances <= matchingDistance)
        taken1 = np.zeros(len(indices1), dtype=bool)
        taken2 = np.zeros(len(indices2), dtype=bool)
        # Greedy one-to-one pairing, closest pairs first: a duplicate trajectory following the same fish as
        # another trajectory of its own result is left unpaired, so it counts as a difference too.
        for candidate in np.argsort(distances[candidates1, candidates2], kind="stable"):
            index1, index2 = candidates1[candidate], candidates2[candidate]
            if not taken1[index1] and not taken2[index2]:
                taken1[index1] = taken2[index2] = True
        paired[0][indices1[taken1], frameIndex] = True
        paired[1][indices2[taken2], frameIndex] = True

    differences = []
    for side in (0, 1):
        unpaired = hasPoint[side] & ~paired[side]
        for trajectoryIndex in np.flatnonzero(unpaired.any(axis=1)):
            wholeTrajectory = not paired[side][trajectoryIndex].any()
            for start, end, nbFrames in findStretches(np.flatnonzero(unpaired[trajectoryIndex]), MERGE_GAP_FRAMES):
                if nbFrames >= minDifferenceFrames:
                    differences.append(Difference(
                        side, int(trajectoryIndex), pair.results[side].trajectoryNames[trajectoryIndex],
                        pair.analysisStart + start, pair.analysisStart + end, nbFrames, wholeTrajectory,
                        points[side][trajectoryIndex, start:end + 1].copy(),
                    ))
    return differences


def groupDifferencesIntoPortions(pair, differences, contextFrames, matchingDistance):
    """
    Biggest differences first; a difference that is part of the same event as a bigger one (close to it in
    space and time) is shown with it. Only the closeness to the main (biggest) difference of a portion counts,
    so that a portion doesn't spread, step by step, over a whole crowded area.
    """
    portions = []
    sameEventDistance = SAME_EVENT_DISTANCE_FACTOR * matchingDistance
    for difference in sorted(differences, key=lambda difference: difference.nbFrames, reverse=True):
        for portion in portions:
            if difference.isCloseTo(portion.differences[0], sameEventDistance, MERGE_GAP_FRAMES):
                portion.add(difference)
                break
        else:
            portions.append(Portion(pair, difference, contextFrames))
    portions.sort(key=lambda portion: portion.score, reverse=True)
    for rank, portion in enumerate(portions):
        portion.rankInVideo = rank + 1
    return portions


def orderPortionsInRounds(pairs):
    """Round 1: the biggest portion of each video, biggest first; round 2: the second biggest portion of each video; etc."""
    orderedPortions = []
    nbRounds = max((len(pair.portions) for pair in pairs), default=0)
    for roundIndex in range(nbRounds):
        roundPortions = [pair.portions[roundIndex] for pair in pairs if len(pair.portions) > roundIndex]
        roundPortions.sort(key=lambda portion: portion.score, reverse=True)
        for portion in roundPortions:
            portion.round = roundIndex + 1
        orderedPortions.extend(roundPortions)
    return orderedPortions


def compareResults(pairedFiles, matchingDistance, minDifferenceFrames, contextFrames, progressCallback=None):
    """
    Loads and compares each pair of results files. progressCallback(index, videoName)
    is called before each pair and can return True to cancel (then None is returned).

    Returns (videoPairs, failures) with failures a list of (videoName, error message).
    """
    videoPairs = []
    failures = []
    for index, (videoName, resultsFile1, resultsFile2) in enumerate(pairedFiles):
        if progressCallback is not None and progressCallback(index, videoName):
            return None
        try:
            pair = VideoPair(videoName, TrackingResults(resultsFile1["path"]), TrackingResults(resultsFile2["path"]))
        except Exception as exc:
            failures.append((videoName, str(exc)))
            continue
        differences = findDifferences(pair, matchingDistance, minDifferenceFrames)
        pair.portions = groupDifferencesIntoPortions(pair, differences, contextFrames, matchingDistance)
        videoPairs.append(pair)
    return videoPairs, failures


# ----------------------------------------------------------------------
# Video frames
# ----------------------------------------------------------------------

def findVideo(resultsPair):
    candidates = []
    for results in resultsPair:
        if results.pathToOriginalVideo:
            originalPath = results.pathToOriginalVideo.replace("\\", "/")
            candidates += [results.pathToOriginalVideo, originalPath, os.path.join(os.path.dirname(results.path), os.path.basename(originalPath))]
        candidates.append(os.path.splitext(results.path)[0] + FULL_VIDEO_COPY_SUFFIX)
    for candidate in candidates:
        if candidate and os.path.isfile(candidate):
            return candidate
    return None


class PortionFrames:
    """
    Reads the video frames of one portion in a background thread, reading
    the video sequentially from its very first frame, as ZebraZoom does
    during tracking (seeking directly to a frame number gives wrong frames
    on some AVI files).
    """

    def __init__(self, videoPath, startFrame, endFrame, frameSize):
        self.videoPath = videoPath
        self.startFrame = startFrame
        self.endFrame = endFrame
        self.frameSize = frameSize
        self.fps = 25.0
        self.error = None
        self._frames = [None] * (endFrame - startFrame + 1)
        self._cancelled = False
        self.finished = videoPath is None
        if videoPath is not None:
            threading.Thread(target=self._read, daemon=True).start()

    def cancel(self):
        self._cancelled = True

    def _read(self):
        videoCapture = cv2.VideoCapture(self.videoPath)
        try:
            if not videoCapture.isOpened():
                self.error = f"could not open {self.videoPath}"
                return
            fps = videoCapture.get(cv2.CAP_PROP_FPS)
            if fps and 1 <= fps <= 240:
                self.fps = fps
            for frameNumber in range(self.startFrame):
                if self._cancelled:
                    return
                if not videoCapture.grab():
                    self.error = f"the video ends at frame {frameNumber}"
                    return
            for index in range(len(self._frames)):
                if self._cancelled:
                    return
                ret, frame = videoCapture.read()
                if not ret or frame is None:
                    self.error = f"the video ends at frame {self.startFrame + index}"
                    return
                if frame.ndim == 2:
                    frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
                self._frames[index] = cv2.imencode(".jpg", frame, [cv2.IMWRITE_JPEG_QUALITY, JPEG_QUALITY])[1]
        except Exception as exc:
            self.error = str(exc)
        finally:
            videoCapture.release()
            self.finished = True

    def frame(self, frameNumber):
        """The frame (BGR image), or None if it isn't read yet. A black frame if it can't be read at all."""
        index = frameNumber - self.startFrame
        encoded = self._frames[index] if 0 <= index < len(self._frames) else None
        if encoded is not None:
            return cv2.imdecode(encoded, cv2.IMREAD_COLOR)
        if self.finished:
            return np.zeros((self.frameSize[1], self.frameSize[0], 3), dtype=np.uint8)
        return None


# ----------------------------------------------------------------------
# Drawing
# ----------------------------------------------------------------------

def drawPath(image, positions, color, thickness):
    """Draws the (n, 2) positions (display coordinates, NaN = no point) as lines between consecutive points."""
    valid = np.isfinite(positions[:, 0])
    for start, end, _nbPoints in findStretches(np.flatnonzero(valid), 0):
        if end > start:
            cv2.polylines(image, [np.round(positions[start:end + 1]).astype(np.int32)], False, color, thickness, cv2.LINE_AA)


def drawDashedCircle(image, center, radius, color, thickness):
    for angle in range(0, 360, 30):
        cv2.ellipse(image, center, (radius, radius), 0, angle, angle + 18, color, thickness, cv2.LINE_AA)


def drawCaption(image, text, position, scale=0.55):
    font = cv2.FONT_HERSHEY_SIMPLEX
    (width, height), baseline = cv2.getTextSize(text, font, scale, 1)
    x, y = position
    cv2.rectangle(image, (x - 4, y - height - 4), (x + width + 4, y + baseline + 2), (0, 0, 0), -1)
    cv2.putText(image, text, (x, y), font, scale, (255, 255, 255), 1, cv2.LINE_AA)


class FramePanel(QLabel):
    """Shows an image that was already resized to fit this panel."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignCenter)
        # Ignored: the panel's size must not depend on the size of the image it shows.
        self.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Ignored)
        self.setMinimumSize(200, 120)
        self.setStyleSheet("background-color: black; color: white;")
        self.onResize = None

    def showImage(self, bgrImage):
        rgb = np.ascontiguousarray(cv2.cvtColor(bgrImage, cv2.COLOR_BGR2RGB))
        qImage = QImage(rgb.data, rgb.shape[1], rgb.shape[0], rgb.strides[0], QImage.Format_RGB888)
        # .copy(): Qt must own the pixel data, as rgb goes out of scope right after.
        self.setPixmap(QPixmap.fromImage(qImage.copy()))

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.onResize is not None:
            self.onResize()


# ----------------------------------------------------------------------
# Selection of the two groups of results
# ----------------------------------------------------------------------

class ResultsSelectionDialog(QDialog):
    def __init__(self, folder):
        super().__init__()
        self.setWindowTitle("Compare tracking results - select the two groups of results")
        self.resize(1000, 780)
        self.folder = folder
        self.group1 = []
        self.group2 = []
        self.pairs = []
        self._step = 1
        self._items = []  # (QTreeWidgetItem, resultsFile)

        layout = QVBoxLayout(self)
        self.stepLabel = QLabel()
        self.stepLabel.setWordWrap(True)
        stepFont = QFont()
        stepFont.setPointSize(11)
        self.stepLabel.setFont(stepFont)
        layout.addWidget(self.stepLabel)

        folderLayout = QHBoxLayout()
        folderLayout.addWidget(QLabel("ZZoutput folder:"))
        self.folderLabel = QLabel()
        folderLayout.addWidget(self.folderLabel, stretch=1)
        changeFolderButton = QPushButton("Change folder...")
        changeFolderButton.clicked.connect(self._changeFolder)
        folderLayout.addWidget(changeFolderButton)
        layout.addLayout(folderLayout)

        filterLayout = QHBoxLayout()
        filterLayout.addWidget(QLabel("Filter:"))
        self.filterBox = QLineEdit()
        self.filterBox.setPlaceholderText("Only show results whose name or tracking date contains this text, e.g. 2026-10-23 12: or DSCF00")
        self.filterBox.textChanged.connect(self._applyFilter)
        filterLayout.addWidget(self.filterBox, stretch=1)
        layout.addLayout(filterLayout)

        self.fileList = QTreeWidget()
        self.fileList.setColumnCount(3)
        self.fileList.setHeaderLabels(["Tracked on", "Results file", "Group"])
        self.fileList.setRootIsDecorated(False)
        self.fileList.setUniformRowHeights(True)
        self.fileList.setAlternatingRowColors(True)
        self.fileList.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.fileList.header().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.fileList.header().setSectionResizeMode(1, QHeaderView.Stretch)
        self.fileList.header().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.fileList.itemSelectionChanged.connect(self._updateSelectionInfo)
        layout.addWidget(self.fileList, stretch=1)

        self.selectionInfoLabel = QLabel()
        self.selectionInfoLabel.setWordWrap(True)
        layout.addWidget(self.selectionInfoLabel)

        settingsBox = QGroupBox("Difference detection settings")
        settingsLayout = QFormLayout(settingsBox)
        self.matchingDistanceBox = QSpinBox()
        self.matchingDistanceBox.setRange(1, 500)
        self.matchingDistanceBox.setValue(DEFAULT_MATCHING_DISTANCE)
        self.matchingDistanceBox.setSuffix(" px")
        settingsLayout.addRow("Matching distance (two points closer than this are the same fish):", self.matchingDistanceBox)
        self.minDifferenceFramesBox = QSpinBox()
        self.minDifferenceFramesBox.setRange(1, 100000)
        self.minDifferenceFramesBox.setValue(DEFAULT_MIN_DIFFERENCE_FRAMES)
        self.minDifferenceFramesBox.setSuffix(" frames")
        settingsLayout.addRow("Ignore differences shorter than:", self.minDifferenceFramesBox)
        self.contextFramesBox = QSpinBox()
        self.contextFramesBox.setRange(0, 100000)
        self.contextFramesBox.setValue(DEFAULT_CONTEXT_FRAMES)
        self.contextFramesBox.setSuffix(" frames")
        settingsLayout.addRow("Frames shown before and after each difference:", self.contextFramesBox)
        layout.addWidget(settingsBox)

        buttonLayout = QHBoxLayout()
        buttonLayout.addStretch(1)
        self.backButton = QPushButton("< Back")
        self.backButton.clicked.connect(self._back)
        buttonLayout.addWidget(self.backButton)
        self.nextButton = QPushButton()
        self.nextButton.setDefault(True)
        self.nextButton.clicked.connect(self._next)
        buttonLayout.addWidget(self.nextButton)
        cancelButton = QPushButton("Cancel")
        cancelButton.clicked.connect(self.reject)
        buttonLayout.addWidget(cancelButton)
        layout.addLayout(buttonLayout)

        self._loadFolder()

    def settings(self):
        return self.matchingDistanceBox.value(), self.minDifferenceFramesBox.value(), self.contextFramesBox.value()

    def _loadFolder(self):
        self.folderLabel.setText(self.folder)
        self.fileList.clear()
        self._items = []
        resultsFiles = listResultsFiles(self.folder) if os.path.isdir(self.folder) else []
        for resultsFile in resultsFiles:
            item = QTreeWidgetItem([resultsFile["trackingTime"].strftime("%Y-%m-%d %H:%M:%S"), resultsFile["fileName"], ""])
            self.fileList.addTopLevelItem(item)
            self._items.append((item, resultsFile))
        self.group1 = []
        self._setStep(1)
        self._applyFilter()

    def _changeFolder(self):
        folder = QFileDialog.getExistingDirectory(self, "Choose the ZZoutput folder", self.folder)
        if folder:
            self.folder = folder
            self._loadFolder()

    def _applyFilter(self):
        text = self.filterBox.text().strip().lower()
        for item, _resultsFile in self._items:
            item.setHidden(bool(text) and text not in f"{item.text(0)} {item.text(1)}".lower())

    def _selectedFiles(self):
        return [resultsFile for item, resultsFile in self._items if item.isSelected() and not item.isHidden() and not item.isDisabled()]

    def _setStep(self, step):
        self._step = step
        group1Paths = {resultsFile["path"] for resultsFile in self.group1} if step == 2 else set()
        self.fileList.clearSelection()
        for item, resultsFile in self._items:
            inGroup1 = resultsFile["path"] in group1Paths
            item.setDisabled(inGroup1)
            item.setText(2, "1 (top)" if inGroup1 else "")
        if step == 1:
            self.stepLabel.setText(
                "<b>Step 1/2: select the FIRST group of tracking results</b> (shown at the TOP of the comparison window).<br>"
                "Results are sorted by tracking time, most recent first: click the first results file of the group and "
                "shift-click the last one to select all the results in between (ctrl-click adds or removes a single file)."
            )
            self.nextButton.setText("Next >")
            self.backButton.setEnabled(False)
        else:
            self.stepLabel.setText(
                "<b>Step 2/2: select the SECOND group of tracking results</b> (shown at the BOTTOM of the comparison window): "
                "results of the same videos as the first group, tracked with another algorithm or another variation of the algorithm.<br>"
                "Results are paired with the first group by video name (the results file name without its tracking date and time)."
            )
            self.nextButton.setText("Compare")
            self.backButton.setEnabled(True)
        self._updateSelectionInfo()

    def _describeGroup(self, group):
        if not group:
            return "no results selected"
        times = sorted(resultsFile["trackingTime"] for resultsFile in group)
        nbVideos = len({resultsFile["videoName"].lower() for resultsFile in group})
        return (f"{len(group)} results selected ({nbVideos} different videos), tracked between "
                f"{times[0]:%Y-%m-%d %H:%M:%S} and {times[-1]:%Y-%m-%d %H:%M:%S}")

    def _updateSelectionInfo(self):
        selected = self._selectedFiles()
        if self._step == 1:
            self.selectionInfoLabel.setText(f"Group 1 (top): {self._describeGroup(selected)}")
            return
        pairs, unpaired1, unpaired2, _duplicates = pairResultsFiles(self.group1, selected)
        self.selectionInfoLabel.setText(
            f"Group 1 (top): {self._describeGroup(self.group1)}<br>"
            f"Group 2 (bottom): {self._describeGroup(selected)}<br>"
            f"<b>{len(pairs)} videos in common</b>; {len(unpaired1)} group 1 results and "
            f"{len(unpaired2)} group 2 results without a counterpart in the other group."
        )

    def _back(self):
        selection = {resultsFile["path"] for resultsFile in self.group1}
        self._setStep(1)
        for item, resultsFile in self._items:
            item.setSelected(resultsFile["path"] in selection)

    def _next(self):
        selected = self._selectedFiles()
        if not selected:
            QMessageBox.information(self, "No results selected", "Please select at least one results file.")
            return
        if self._step == 1:
            self.group1 = selected
            self._setStep(2)
            return
        pairs, unpaired1, unpaired2, duplicates = pairResultsFiles(self.group1, selected)
        if not pairs:
            QMessageBox.warning(self, "No videos in common", "None of the selected results are results of the same videos as the first group.")
            return
        warnings = []
        if unpaired1 or unpaired2:
            unpairedNames = sorted({resultsFile["videoName"] for resultsFile in unpaired1 + unpaired2})
            warnings.append(f"{len(unpaired1) + len(unpaired2)} results have no counterpart in the other group and will be left out: "
                            + ", ".join(unpairedNames[:15]) + (", ..." if len(unpairedNames) > 15 else ""))
        if duplicates:
            warnings.append("Some videos have several results in the same group: only the most recent one is used, so these are left out: "
                            + ", ".join(resultsFile["fileName"] for resultsFile in duplicates[:10]) + (", ..." if len(duplicates) > 10 else ""))
        if warnings:
            answer = QMessageBox.question(self, "Compare anyway?", "\n\n".join(warnings) + f"\n\nCompare the {len(pairs)} videos in common?")
            if answer != QMessageBox.Yes:
                return
        self.group2 = selected
        self.pairs = pairs
        self.accept()


# ----------------------------------------------------------------------
# Comparison window
# ----------------------------------------------------------------------

class ComparisonWindow(QMainWindow):
    def __init__(self, videoPairs, portions, group1, group2, matchingDistance, outputFolder, summary):
        super().__init__()
        self.setWindowTitle(f"Tracking comparison - TOP: group 1 ({len(group1)} results) vs BOTTOM: group 2 ({len(group2)} results)")
        self.resize(1500, 1000)
        self._videoPairs = videoPairs
        self._portions = portions
        self._matchingDistance = matchingDistance
        self._csvPath = os.path.join(outputFolder, f"trackingComparison_{datetime.datetime.now():%Y_%m_%d-%H_%M_%S}.csv")
        self._votes = {}  # portion index -> "top", "bottom" or "tie"
        self._currentIndex = -1
        self._loaders = {}  # portion index -> PortionFrames
        self._decodedFrame = (None, None, None)  # (portion index, frame number, image)
        self._saveErrorShown = False

        centralWidget = QWidget()
        self.setCentralWidget(centralWidget)
        rootLayout = QHBoxLayout(centralWidget)

        # Left: the information about the portion, the two videos and the frame slider.
        leftLayout = QVBoxLayout()
        self.infoLabel = QLabel()
        self.infoLabel.setWordWrap(True)
        self.infoLabel.setTextFormat(Qt.RichText)
        leftLayout.addWidget(self.infoLabel)
        self.panels = (FramePanel(), FramePanel())
        for panel in self.panels:
            panel.onResize = self._scheduleRedraw
            leftLayout.addWidget(panel, stretch=1)

        sliderLayout = QHBoxLayout()
        self.playButton = QPushButton("Play")
        self.playButton.setFocusPolicy(Qt.NoFocus)
        self.playButton.clicked.connect(self._togglePlay)
        sliderLayout.addWidget(self.playButton)
        self.frameSlider = QSlider(Qt.Horizontal)
        self.frameSlider.setFocusPolicy(Qt.NoFocus)
        self.frameSlider.valueChanged.connect(lambda _value: self._redraw())
        sliderLayout.addWidget(self.frameSlider, stretch=1)
        self.frameLabel = QLabel("Frame: -")
        self.frameLabel.setMinimumWidth(260)
        sliderLayout.addWidget(self.frameLabel)
        leftLayout.addLayout(sliderLayout)

        optionsLayout = QHBoxLayout()
        self.trailsCheckbox = QCheckBox(f"Trails ({TRAIL_LENGTH} frames)")
        self.trailsCheckbox.setChecked(True)
        self.zoomCheckbox = QCheckBox("Zoom on the difference")
        self.contrastCheckbox = QCheckBox("Contrast")
        for checkbox in (self.trailsCheckbox, self.zoomCheckbox, self.contrastCheckbox):
            checkbox.setFocusPolicy(Qt.NoFocus)
            checkbox.toggled.connect(lambda _checked: self._redraw())
            optionsLayout.addWidget(checkbox)
        legend = QLabel(
            "<span style='color:#00b000'>&#9679;</span> tracked fish &nbsp; "
            "<span style='color:#e00000'>&#9711;</span> trajectory present only in this result &nbsp; "
            "<span style='color:#c8a800'>&#9711; (dashed)</span> trajectory the other result has, missing here"
        )
        # Word wrap on all long labels: otherwise their text width becomes the window's minimum width.
        legend.setWordWrap(True)
        optionsLayout.addWidget(legend, stretch=1)
        leftLayout.addLayout(optionsLayout)
        keysLabel = QLabel(
            "Keys: Left/Right = previous/next frame (Shift: 10 frames), Home/End = start/end of the portion, Space = play/pause, "
            "Up or T = TOP is better, Down or B = BOTTOM is better, S = can't tell, Page Up/Page Down = previous/next portion"
        )
        keysLabel.setWordWrap(True)
        leftLayout.addWidget(keysLabel)
        rootLayout.addLayout(leftLayout, stretch=1)

        # Right: the choice buttons (next to their video) and the scoreboard.
        rightWidget = QWidget()
        rightWidget.setFixedWidth(240)
        rightLayout = QVBoxLayout(rightWidget)
        rightLayout.setContentsMargins(0, 0, 0, 0)
        buttonFont = QFont()
        buttonFont.setPointSize(13)
        buttonFont.setBold(True)
        self.topButton = QPushButton("▲\nTOP\nis better\n(group 1)")
        self.bottomButton = QPushButton("BOTTOM\nis better\n(group 2)\n▼")
        self.tieButton = QPushButton("Can't tell")
        for button, choice, color in ((self.topButton, "top", "#cfe3ff"), (self.bottomButton, "bottom", "#ffe0c2"), (self.tieButton, "tie", "#e6e6e6")):
            button.setCheckable(True)
            button.setFocusPolicy(Qt.NoFocus)
            button.setFont(buttonFont)
            button.setStyleSheet(
                f"QPushButton {{ background-color: {color}; border: 2px solid #888; border-radius: 6px; padding: 6px; color: black; }}"
                "QPushButton:checked { background-color: #2e7d32; color: white; border: 3px solid #1b5e20; }"
            )
            button.clicked.connect(lambda _checked, choice=choice: self._vote(choice))
        self.topButton.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.bottomButton.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        rightLayout.addWidget(self.topButton, stretch=1)

        middleLayout = QVBoxLayout()
        self.scoreLabel = QLabel()
        self.scoreLabel.setWordWrap(True)
        self.scoreLabel.setTextFormat(Qt.RichText)
        self.scoreLabel.setAlignment(Qt.AlignCenter)
        self.scoreLabel.setStyleSheet("background-color: #fafafa; color: black; border: 1px solid #bbb; border-radius: 6px; padding: 6px;")
        middleLayout.addWidget(self.scoreLabel)
        middleLayout.addWidget(self.tieButton)
        navigationLayout = QHBoxLayout()
        self.previousButton = QPushButton("< Previous")
        self.previousButton.clicked.connect(lambda: self._showPortion(self._currentIndex - 1))
        self.nextButton = QPushButton("Next >")
        self.nextButton.clicked.connect(lambda: self._showPortion(self._currentIndex + 1))
        for button in (self.previousButton, self.nextButton):
            button.setFocusPolicy(Qt.NoFocus)
            navigationLayout.addWidget(button)
        middleLayout.addLayout(navigationLayout)
        rightLayout.addLayout(middleLayout)
        rightLayout.addWidget(self.bottomButton, stretch=1)
        rootLayout.addWidget(rightWidget)

        self.statusBar().showMessage(summary)

        self._redrawTimer = QTimer(self)
        self._redrawTimer.setSingleShot(True)
        self._redrawTimer.timeout.connect(self._redraw)
        self._playTimer = QTimer(self)
        self._playTimer.timeout.connect(self._playNextFrame)

        # The keyboard shortcuts must work whichever widget has the keyboard focus.
        QApplication.instance().installEventFilter(self)
        self._showPortion(0)

    # ------------------------------------------------------------------
    # Keyboard
    # ------------------------------------------------------------------

    def eventFilter(self, watchedObject, event):
        if event.type() != QEvent.KeyPress or not self.isActiveWindow():
            return super().eventFilter(watchedObject, event)
        key = event.key()
        if key in (Qt.Key_Left, Qt.Key_Right):
            step = 10 if event.modifiers() & Qt.ShiftModifier else 1
            self._stopPlaying()
            self.frameSlider.setValue(self.frameSlider.value() + (step if key == Qt.Key_Right else -step))
        elif key == Qt.Key_Home:
            self.frameSlider.setValue(self.frameSlider.minimum())
        elif key == Qt.Key_End:
            self.frameSlider.setValue(self.frameSlider.maximum())
        elif key == Qt.Key_Space:
            if not event.isAutoRepeat():
                self._togglePlay()
        elif key in (Qt.Key_Up, Qt.Key_T, Qt.Key_Down, Qt.Key_B, Qt.Key_S, Qt.Key_PageUp, Qt.Key_PageDown):
            # Keeping a key pressed must not choose for several portions in a row.
            if not event.isAutoRepeat():
                if key in (Qt.Key_Up, Qt.Key_T):
                    self._vote("top")
                elif key in (Qt.Key_Down, Qt.Key_B):
                    self._vote("bottom")
                elif key == Qt.Key_S:
                    self._vote("tie")
                else:
                    self._showPortion(self._currentIndex + (1 if key == Qt.Key_PageDown else -1))
        else:
            return super().eventFilter(watchedObject, event)
        return True

    def closeEvent(self, event):
        QApplication.instance().removeEventFilter(self)
        self._playTimer.stop()
        for loader in self._loaders.values():
            loader.cancel()
        print(self._scoreText(html=False))
        if self._votes:
            print(f"Choices saved to: {self._csvPath}")
        super().closeEvent(event)

    # ------------------------------------------------------------------
    # Portions
    # ------------------------------------------------------------------

    def _showPortion(self, index):
        if index < 0 or index >= len(self._portions):
            if index >= len(self._portions):
                QMessageBox.information(
                    self, "All portions shown",
                    f"All the {len(self._portions)} portions of video with differences have been shown.\n\n{self._scoreText(html=False)}",
                )
            return
        self._stopPlaying()
        self._currentIndex = index
        portion = self._portions[index]
        self._updateLoaders()
        self.frameSlider.blockSignals(True)
        self.frameSlider.setRange(portion.startFrame, portion.endFrame)
        self.frameSlider.setValue(portion.startFrame)
        self.frameSlider.blockSignals(False)
        self._updateInfo()
        self._updateScore()
        self._redraw()

    def _loader(self, index, askForMissingVideo):
        if index not in self._loaders:
            portion = self._portions[index]
            pair = portion.pair
            if pair.videoPath is None and not pair.videoPathAsked:
                if not askForMissingVideo:
                    return None
                pair.videoPathAsked = True
                QMessageBox.information(
                    self, "Video not found",
                    f"The video of {pair.videoName} could not be found (neither at the path stored in the results files, "
                    "nor next to them). Please locate it (cancel to see the tracking points on a black background).",
                )
                videoPath, _ = QFileDialog.getOpenFileName(self, f"Select the video {pair.videoName}", os.path.dirname(pair.results[0].path))
                pair.videoPath = videoPath or None
            self._loaders[index] = PortionFrames(pair.videoPath, portion.startFrame, portion.endFrame, pair.frameSize)
        return self._loaders[index]

    def _updateLoaders(self):
        """Reads the frames of the current portion, and in advance those of the next one; frees the others (except the previous one)."""
        index = self._currentIndex
        self._loader(index, True)
        if index + 1 < len(self._portions):
            self._loader(index + 1, False)
        for loaderIndex in list(self._loaders):
            if loaderIndex not in (index - 1, index, index + 1):
                self._loaders.pop(loaderIndex).cancel()

    def _vote(self, choice):
        if self._currentIndex < 0:
            return
        self._votes[self._currentIndex] = choice
        self._saveVotes()
        self._updateScore()
        if self._currentIndex + 1 < len(self._portions):
            self._showPortion(self._currentIndex + 1)
        else:
            self._showPortion(len(self._portions))  # shows the "all portions shown" message

    def _saveVotes(self):
        try:
            with open(self._csvPath, "w", newline="", encoding="utf-8") as csvFile:
                writer = csv.writer(csvFile)
                writer.writerow([
                    "portionNumber", "round", "video", "topResults (group 1)", "bottomResults (group 2)",
                    "firstFrame", "lastFrame", "differenceSize", "differences", "choice",
                ])
                for index in sorted(self._votes):
                    portion = self._portions[index]
                    writer.writerow([
                        index + 1, portion.round, portion.pair.videoName,
                        portion.pair.results[0].fileName, portion.pair.results[1].fileName,
                        portion.startFrame, portion.endFrame, portion.score,
                        " | ".join(difference.describe() for difference in portion.differences),
                        CHOICE_LABELS[self._votes[index]],
                    ])
            self.statusBar().showMessage(f"Choices saved to {self._csvPath}")
        except OSError as exc:
            if not self._saveErrorShown:
                self._saveErrorShown = True
                QMessageBox.warning(self, "Could not save the choices", f"Failed to write to:\n{self._csvPath}\n\n{exc}")

    def _scoreText(self, html):
        counts = {choice: sum(1 for vote in self._votes.values() if vote == choice) for choice in CHOICE_LABELS}
        lines = [
            f"TOP (group 1) better: {counts['top']}",
            f"BOTTOM (group 2) better: {counts['bottom']}",
            f"Can't tell: {counts['tie']}",
            f"Portions judged: {len(self._votes)} / {len(self._portions)}",
        ]
        if not html:
            return "\n".join(lines)
        return (
            "<div style='font-size:11pt'><b>Score</b></div>"
            f"<div style='font-size:16pt'><b>TOP: {counts['top']}</b></div>"
            f"<div style='font-size:16pt'><b>BOTTOM: {counts['bottom']}</b></div>"
            f"<div>Can't tell: {counts['tie']}</div>"
            f"<div style='margin-top:6px'>Portion {self._currentIndex + 1} / {len(self._portions)}<br>"
            f"(round {self._portions[self._currentIndex].round})<br>{len(self._votes)} judged</div>"
        )

    def _updateScore(self):
        self.scoreLabel.setText(self._scoreText(html=True))
        vote = self._votes.get(self._currentIndex)
        self.topButton.setChecked(vote == "top")
        self.bottomButton.setChecked(vote == "bottom")
        self.tieButton.setChecked(vote == "tie")
        self.previousButton.setEnabled(self._currentIndex > 0)
        self.nextButton.setEnabled(self._currentIndex + 1 < len(self._portions))

    def _updateInfo(self):
        portion = self._portions[self._currentIndex]
        pair = portion.pair
        lines = [
            f"<b>Video {pair.videoName}</b> &nbsp;&mdash;&nbsp; portion {self._currentIndex + 1} of {len(self._portions)} "
            f"(round {portion.round}: difference #{portion.rankInVideo} of {len(pair.portions)} for this video, "
            f"size {portion.score} frames) &nbsp;&mdash;&nbsp; frames {portion.startFrame} to {portion.endFrame}"
        ]
        maxShown = 3
        for difference in portion.differences[:maxShown]:
            lines.append(f"&bull; {difference.describe()}")
        if len(portion.differences) > maxShown:
            lines.append(f"&bull; ... and {len(portion.differences) - maxShown} smaller difference(s) in this portion")
        self.infoLabel.setText("<br>".join(lines))

    # ------------------------------------------------------------------
    # Playing
    # ------------------------------------------------------------------

    def _togglePlay(self):
        if self._playTimer.isActive():
            self._stopPlaying()
            return
        if self.frameSlider.value() >= self.frameSlider.maximum():
            self.frameSlider.setValue(self.frameSlider.minimum())
        loader = self._loaders.get(self._currentIndex)
        fps = loader.fps if loader is not None else 25.0
        self._playTimer.start(int(1000 / fps))
        self.playButton.setText("Pause")

    def _stopPlaying(self):
        self._playTimer.stop()
        self.playButton.setText("Play")

    def _playNextFrame(self):
        if self.frameSlider.value() >= self.frameSlider.maximum():
            self._stopPlaying()
            return
        loader = self._loaders.get(self._currentIndex)
        if loader is not None and loader.frame(self.frameSlider.value() + 1) is None:
            return  # the next frame isn't read yet: wait for it
        self.frameSlider.setValue(self.frameSlider.value() + 1)

    # ------------------------------------------------------------------
    # Drawing
    # ------------------------------------------------------------------

    def _scheduleRedraw(self, delay=0):
        self._redrawTimer.start(delay)

    def _currentFrame(self, frameNumber):
        cachedIndex, cachedFrameNumber, cachedImage = self._decodedFrame
        if cachedIndex == self._currentIndex and cachedFrameNumber == frameNumber:
            return cachedImage
        loader = self._loader(self._currentIndex, True)
        image = loader.frame(frameNumber) if loader is not None else None
        if image is not None:
            self._decodedFrame = (self._currentIndex, frameNumber, image)
        return image

    def _redraw(self):
        if self._currentIndex < 0:
            return
        portion = self._portions[self._currentIndex]
        frameNumber = self.frameSlider.value()
        frame = self._currentFrame(frameNumber)
        loader = self._loaders.get(self._currentIndex)
        if frame is None:
            for panel in self.panels:
                panel.clear()
                panel.setText("Reading the video...")
            self.frameLabel.setText(f"Frame {frameNumber} (reading the video...)")
            self._scheduleRedraw(50)
            return
        if self.contrastCheckbox.isChecked():
            frame = improveContrast(frame)
        for side, panel in enumerate(self.panels):
            panel.showImage(self._renderPanel(frame, portion, side, frameNumber, panel.width(), panel.height()))
        frameText = f"Frame {frameNumber}  ({frameNumber - portion.startFrame + 1} / {portion.endFrame - portion.startFrame + 1} in this portion)"
        if loader is not None and loader.error:
            frameText += f"  -  video problem: {loader.error}"
        elif portion.pair.videoPath is None:
            frameText += "  -  video not found"
        self.frameLabel.setText(frameText)

    def _cropRectangle(self, portion, frameWidth, frameHeight, panelAspectRatio):
        """Whole frame, or (when zooming) the area around the differences of the portion, with the panel's aspect ratio."""
        if not self.zoomCheckbox.isChecked():
            return 0, 0, frameWidth, frameHeight
        points = np.concatenate([difference.path for difference in portion.differences])
        points = points[np.isfinite(points[:, 0])]
        if len(points) == 0:
            return 0, 0, frameWidth, frameHeight
        margin = 4 * self._matchingDistance
        width = max(points[:, 0].max() - points[:, 0].min() + 2 * margin, frameWidth / 4)
        height = max(points[:, 1].max() - points[:, 1].min() + 2 * margin, frameHeight / 4)
        if width / height < panelAspectRatio:
            width = height * panelAspectRatio
        else:
            height = width / panelAspectRatio
        width, height = min(width, frameWidth), min(height, frameHeight)
        centerX, centerY = (points[:, 0].max() + points[:, 0].min()) / 2, (points[:, 1].max() + points[:, 1].min()) / 2
        x0 = int(np.clip(centerX - width / 2, 0, frameWidth - width))
        y0 = int(np.clip(centerY - height / 2, 0, frameHeight - height))
        return x0, y0, x0 + int(width), y0 + int(height)

    def _renderPanel(self, frame, portion, side, frameNumber, panelWidth, panelHeight):
        frameHeight, frameWidth = frame.shape[:2]
        x0, y0, x1, y1 = self._cropRectangle(portion, frameWidth, frameHeight, max(panelWidth, 1) / max(panelHeight, 1))
        scale = min(panelWidth / (x1 - x0), panelHeight / (y1 - y0))
        displayWidth, displayHeight = max(int((x1 - x0) * scale), 1), max(int((y1 - y0) * scale), 1)
        image = cv2.resize(frame[y0:y1, x0:x1], (displayWidth, displayHeight), interpolation=cv2.INTER_AREA if scale < 1 else cv2.INTER_LINEAR)

        def toDisplay(positions):
            return (positions - (x0, y0)) * scale

        results = portion.pair.results[side]
        if self.trailsCheckbox.isChecked():
            trails = toDisplay(results.positionsBetween(max(portion.startFrame, frameNumber - TRAIL_LENGTH), frameNumber))
            for trail in trails:
                drawPath(image, trail, TRAIL_COLOR, 1)

        # The differences: their whole path, and a circle around the trajectory on the current frame.
        ringRadius = max(int(round(self._matchingDistance * scale)), 8)
        for difference in portion.differences:
            presentHere = difference.side == side
            color = ONLY_HERE_COLOR if presentHere else MISSING_HERE_COLOR
            drawPath(image, toDisplay(difference.path), color, 1)
            if difference.startFrame <= frameNumber <= difference.endFrame:
                position = toDisplay(difference.path[frameNumber - difference.startFrame])
                if np.isfinite(position[0]):
                    center = (int(round(position[0])), int(round(position[1])))
                    if presentHere:
                        cv2.circle(image, center, ringRadius, color, 2, cv2.LINE_AA)
                    else:
                        drawDashedCircle(image, center, ringRadius, color, 2)

        points = toDisplay(results.positionsBetween(frameNumber, frameNumber)[:, 0])
        for x, y in points[np.isfinite(points[:, 0])]:
            center = (int(round(x)), int(round(y)))
            cv2.circle(image, center, POINT_RADIUS, POINT_COLOR, -1, cv2.LINE_AA)
            cv2.circle(image, center, POINT_RADIUS, OUTLINE_COLOR, 1, cv2.LINE_AA)

        drawCaption(image, f"{SIDE_NAMES[side]} - group {side + 1}: {results.fileName}   (frame {frameNumber})", (8, 20))
        return image


# ----------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------

def runComparison(dialog):
    """Compares the pairs selected in the dialog, showing a progress dialog. Returns (videoPairs, failures), or None if cancelled."""
    matchingDistance, minDifferenceFrames, contextFrames = dialog.settings()
    progress = QProgressDialog("Comparing the tracking results...", "Cancel", 0, len(dialog.pairs))
    progress.setWindowTitle("Compare tracking results")
    progress.setWindowModality(Qt.ApplicationModal)
    progress.setMinimumDuration(0)
    progress.setMinimumWidth(500)

    def onProgress(index, videoName):
        progress.setValue(index)
        progress.setLabelText(f"Comparing the tracking results of {videoName} ({index + 1}/{len(dialog.pairs)})")
        QApplication.processEvents()
        return progress.wasCanceled()

    result = compareResults(dialog.pairs, matchingDistance, minDifferenceFrames, contextFrames, onProgress)
    progress.setValue(len(dialog.pairs))
    return result


def main():
    app = QApplication(sys.argv)
    folder = sys.argv[1] if len(sys.argv) > 1 else getDefaultZZoutputFolder()
    dialog = ResultsSelectionDialog(folder)
    if dialog.exec_() != QDialog.Accepted:
        return
    result = runComparison(dialog)
    if result is None:
        return
    videoPairs, failures = result
    if failures:
        QMessageBox.warning(None, "Some results could not be read",
                            "\n".join(f"{videoName}: {error}" for videoName, error in failures))
    portions = orderPortionsInRounds(videoPairs)
    identicalVideos = [pair.videoName for pair in videoPairs if not pair.portions]
    if not portions:
        QMessageBox.information(None, "No differences", f"No differences were found between the two groups of results ({len(videoPairs)} videos compared).")
        return
    summary = (f"{len(videoPairs)} videos compared: {len(portions)} portions of video with differences"
               + (f"; no differences for {len(identicalVideos)} videos ({', '.join(identicalVideos[:5])}{', ...' if len(identicalVideos) > 5 else ''})"
                  if identicalVideos else ""))
    matchingDistance = dialog.settings()[0]
    window = ComparisonWindow(videoPairs, portions, dialog.group1, dialog.group2, matchingDistance, dialog.folder, summary)
    window.showMaximized()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
