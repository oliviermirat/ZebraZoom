import bisect
import collections
import heapq

import numpy as np
from scipy.optimize import linear_sum_assignment

from ._openResultsFile import openResultsFile

__all__ = ['growTracksFromConfidentDetections']

_LOG_PREFIX = '[growTracksFromConfidentDetections]'

# Where the YOLO tracking with "OrTools": 1 records every YOLO box (frame, x1, y1, x2, y2, score)
_RAW_DETECTIONS_DATASET = 'OrToolsTracking/well{numWell}/detections'


def _distances(points, anchors):
  """(len(points), len(anchors)) matrix of the euclidean distances between two lists of (x, y) positions."""
  return np.sqrt(((points[:, None, :] - anchors[None, :, :]) ** 2).sum(axis=2))


def _gatedAssignment(dist, maxDisplacement, cost=None):
  """
  One-to-one matching between the rows and the columns of a distance matrix (Hungarian algorithm) which only ever
  uses pairs that are at most maxDisplacement apart: as many pairs as possible are matched and, among the matchings
  with that many pairs, the one with the smallest total distance is chosen. Returns a list of (row, column).
  cost (same shape as dist, optional): what is minimized instead of the total distance (dist then only says which
  pairs are allowed).
  """
  feasible = dist <= maxDisplacement
  rows = np.flatnonzero(feasible.any(axis=1))
  if not len(rows):
    return []
  cols = np.flatnonzero(feasible.any(axis=0))
  dist = dist[np.ix_(rows, cols)]
  feasible = feasible[np.ix_(rows, cols)]
  if cost is not None:
    cost = cost[np.ix_(rows, cols)]
  if len(rows) == 1 or len(cols) == 1:
    i, j = np.unravel_index(np.argmin(np.where(feasible, dist if cost is None else cost, np.inf)), dist.shape)
    return [(rows[i], cols[j])]
  # A forbidden pair costs more than any whole matching made of allowed pairs, so the solver only uses forbidden
  # pairs when it has no other choice (they are then thrown away): this maximizes the number of allowed pairs first.
  if cost is None:
    forbiddenCost = maxDisplacement * (min(dist.shape) + 1) + 1
    rowInd, colInd = linear_sum_assignment(np.where(feasible, dist, forbiddenCost))
  else:
    forbiddenCost = max(cost[feasible].max(), 0) * (min(dist.shape) + 1) + 1
    rowInd, colInd = linear_sum_assignment(np.where(feasible, cost, forbiddenCost))
  return [(rows[i], cols[j]) for i, j in zip(rowInd, colInd) if feasible[i, j]]


class _ExclusionZones:
  """
  Points held by the tracks, frame by frame, for the exclusionRadius option: a detection lying within exclusionRadius
  of a point already held by a track in the same frame is taken for a duplicate YOLO box of an animal already tracked,
  so it never joins nor starts a track.
  """

  def __init__(self, positions, radius):
    self._positions = positions
    self._radius = radius
    self._heldByFrame = collections.defaultdict(list)  # frame -> detections held by the tracks

  def excluded(self, detections, frame, alsoHeld=()):
    """For each detection (all in this frame): is it within the radius of a point held in this frame (or of alsoHeld)?"""
    held = self._heldByFrame.get(frame, []) + list(alsoHeld)
    if not held:
      return np.zeros(len(detections), dtype=bool)
    return (_distances(self._positions[detections].reshape(-1, 2), self._positions[held]) <= self._radius).any(axis=1)

  def hold(self, detection, frame):
    self._heldByFrame[frame].append(detection)


def _assignCandidates(positions, candidates, anchors, maxDisplacement, exclusion, frame):
  """
  Optimal one-to-one matching (_gatedAssignment) between the candidate detections of a frame and the anchors (track
  ends). Returns a list of (index in candidates, index in anchors). With exclusion zones, excluded candidates are left
  out of the matching, and the matched pairs are then accepted from the closest one to the farthest one, a candidate
  being refused (left unmatched) if it is within the exclusion radius of a candidate accepted before it.
  """
  if exclusion is None:
    return _gatedAssignment(_distances(positions[candidates], anchors), maxDisplacement)
  allowed = np.flatnonzero(~exclusion.excluded(candidates, frame))
  if not len(allowed):
    return []
  dist = _distances(positions[candidates[allowed]], anchors)
  accepted, taken = [], []
  for i, j in sorted(_gatedAssignment(dist, maxDisplacement), key=lambda pair: dist[pair[0], pair[1]]):
    if not exclusion.excluded([candidates[allowed[i]]], frame, taken)[0]:
      accepted.append((allowed[i], j))
      taken.append(candidates[allowed[i]])
  return accepted


class _Tracks:
  """
  The tracks being built. A track holds exactly one detection per frame, over consecutive frames: it only grows by
  its ends (a detection in the frame right after its last frame, or right before its first frame), or by being
  merged with a track starting right after it ends.
  """

  def __init__(self, positions):
    self._positions = positions  # (x, y) of every detection
    self.detections = {}  # track id -> deque of detection indices, one per frame, from the first to the last frame
    self.first = {}  # track id -> first frame
    self.last = {}  # track id -> last frame
    self._endingAt = collections.defaultdict(set)  # frame -> ids of the tracks whose last frame it is
    self._startingAt = collections.defaultdict(set)  # frame -> ids of the tracks whose first frame it is
    self._nextId = 0

  def endingAt(self, frame):
    return sorted(self._endingAt.get(frame, ()))

  def startingAt(self, frame):
    return sorted(self._startingAt.get(frame, ()))

  def lastFrames(self):
    return sorted(frame for frame, trackIds in self._endingAt.items() if trackIds)

  def firstPositions(self, trackIds):
    return self._positions[[self.detections[trackId][0] for trackId in trackIds]].reshape(-1, 2)

  def lastPositions(self, trackIds):
    return self._positions[[self.detections[trackId][-1] for trackId in trackIds]].reshape(-1, 2)

  def create(self, detection, frame):
    trackId = self._nextId
    self._nextId += 1
    self.detections[trackId] = collections.deque([detection])
    self.first[trackId] = self.last[trackId] = frame
    self._startingAt[frame].add(trackId)
    self._endingAt[frame].add(trackId)

  def append(self, trackId, detection):
    last = self.last[trackId]
    self._endingAt[last].discard(trackId)
    self._endingAt[last + 1].add(trackId)
    self.last[trackId] = last + 1
    self.detections[trackId].append(detection)

  def prepend(self, trackId, detection):
    first = self.first[trackId]
    self._startingAt[first].discard(trackId)
    self._startingAt[first - 1].add(trackId)
    self.first[trackId] = first - 1
    self.detections[trackId].appendleft(detection)

  def merge(self, trackId, nextTrackId):
    """nextTrackId starts on the frame right after trackId's last frame: trackId absorbs it."""
    self._endingAt[self.last[trackId]].discard(trackId)
    self._startingAt[self.first.pop(nextTrackId)].discard(nextTrackId)
    nextLast = self.last.pop(nextTrackId)
    self._endingAt[nextLast].discard(nextTrackId)
    self._endingAt[nextLast].add(trackId)
    self.last[trackId] = nextLast
    self.detections[trackId].extend(self.detections.pop(nextTrackId))


def _seedTracks(tracks, positions, confidence, frameBounds, seedConfidence, maxDisplacement, exclusion=None):
  """
  Initial process: goes through the frames from the first one to the last one. In each frame, every detection whose
  confidence is >= seedConfidence either extends a track ending on the previous frame (at most maxDisplacement
  away, optimal one-to-one matching), or starts a new track. Returns the indices of all these detections.
  With exclusion zones, the unmatched detections start new tracks from the most confident one to the least confident
  one, and an excluded detection starts no track (it leaves the pool all the same).
  """
  seeded = []
  for frame in range(len(frameBounds) - 1):
    candidates = np.arange(frameBounds[frame], frameBounds[frame + 1])
    candidates = candidates[confidence[candidates] >= seedConfidence]
    if not len(candidates):
      continue
    matched = np.zeros(len(candidates), dtype=bool)
    trackIds = tracks.endingAt(frame - 1)
    if trackIds:
      for i, j in _assignCandidates(positions, candidates, tracks.lastPositions(trackIds), maxDisplacement, exclusion, frame):
        tracks.append(trackIds[j], candidates[i])
        matched[i] = True
        if exclusion is not None:
          exclusion.hold(candidates[i], frame)
    if exclusion is None:
      for i in np.flatnonzero(~matched):
        tracks.create(candidates[i], frame)
    else:
      for i in sorted(np.flatnonzero(~matched), key=lambda i: -confidence[candidates[i]]):
        if not exclusion.excluded([candidates[i]], frame)[0]:
          tracks.create(candidates[i], frame)
          exclusion.hold(candidates[i], frame)
    seeded.append(candidates)
  return np.concatenate(seeded) if seeded else np.zeros(0, dtype=int)


def _mergeConsecutiveTracks(tracks, maxDisplacement):
  """
  Core process, step 1: merges the tracks ending on a frame with the tracks starting on the next frame, when their
  facing ends are at most maxDisplacement apart (optimal one-to-one matching, frame by frame, from the first frame
  to the last). Returns the number of merges.
  """
  nbMerges = 0
  for frame in tracks.lastFrames():
    ending = tracks.endingAt(frame)
    starting = tracks.startingAt(frame + 1)
    if not ending or not starting:
      continue
    for i, j in _gatedAssignment(_distances(tracks.lastPositions(ending), tracks.firstPositions(starting)), maxDisplacement):
      tracks.merge(ending[i], starting[j])
      nbMerges += 1
  return nbMerges


def _absorbConfidenceTier(tracks, positions, tierDetectionsByFrame, inPool, maxDisplacement, exclusion=None):
  """
  Core process, step 2, for one confidence tier: goes through the frames from the first one to the last one. In each
  frame, the detections of this tier still in the pool are matched (optimal one-to-one matching, never more than
  maxDisplacement away) with the tracks ending on the previous frame and the tracks starting on the next frame; the
  matched detections leave the pool and extend their track, the others stay in the pool. Only the frames next to an
  end of a track can receive a detection, so only those are visited (in increasing order); a track extended forward
  makes the next frame such a frame. Returns the number of detections taken from the pool.
  With exclusion zones, excluded detections stay in the pool (see _assignCandidates).
  """
  framesToVisit = sorted({last + 1 for last in tracks.last.values()} | {first - 1 for first in tracks.first.values()})
  previousFrame = None
  nbAbsorbed = 0
  while framesToVisit:
    frame = heapq.heappop(framesToVisit)
    if frame == previousFrame:
      continue
    previousFrame = frame
    candidates = tierDetectionsByFrame.get(frame)
    if candidates is None:
      continue
    candidates = candidates[inPool[candidates]]
    if not len(candidates):
      continue
    ending = tracks.endingAt(frame - 1)
    starting = tracks.startingAt(frame + 1)
    if not ending and not starting:
      continue
    anchors = np.concatenate((tracks.lastPositions(ending), tracks.firstPositions(starting)))
    for i, j in _assignCandidates(positions, candidates, anchors, maxDisplacement, exclusion, frame):
      if j < len(ending):
        tracks.append(ending[j], candidates[i])
        heapq.heappush(framesToVisit, frame + 1)
      else:
        tracks.prepend(starting[j - len(ending)], candidates[i])
      inPool[candidates[i]] = False
      if exclusion is not None:
        exclusion.hold(candidates[i], frame)
      nbAbsorbed += 1
  return nbAbsorbed


def _bestOfTies(scores, steps):
  """Index of the smallest score, the smallest step deciding between exactly equal scores."""
  return np.where(scores == scores.min(), steps, np.inf).argmin()


def _tracePath(history, index):
  """Detections of the path ending on detection number index of the last frame of history, from its first frame."""
  path = []
  for detections, predecessors in reversed(history):
    path.append(detections[index])
    index = predecessors[index]
  return path[::-1]


def _bridgeGaps(tracks, positions, frameBounds, inPool, exclusion, maxGapFrames, maxDistance, maxStep):
  """
  Step 3 (bridgeGaps): links track ends to track beginnings across gaps, through the detections left in the pool.
  1) Candidate pairs: each track end with each track beginning at most maxGapFrames frames later and at most
     maxDistance pixels away. For each pair, the path made of one left over detection per frame of the gap whose largest
     step (distance between the detections of two consecutive frames, the end of the first track and the beginning of
     the second track included) is the smallest possible is found; that largest step is the score of the pair, and the
     pairs scoring more than maxStep are dropped. Left over detections can be used by several paths. With exclusion
     zones, the left over detections within the exclusion radius of a point of a track are not used.
     The paths are found exactly, frame by frame (dynamic programming), from each track end: for each left over
     detection of the next frames, the best possible largest step of a path coming from that track end, and the
     detection it comes from (the closest one when several give exactly the same score). Detections that can only be
     reached with a step larger than maxStep are not followed further.
  2) The remaining pairs are linked with the Hungarian algorithm: as many links as possible, then the smallest total
     score, the shortest gaps winning between exactly equal scores. Each linked pair becomes one track, its path filling
     the gap.
  Returns (number of candidate pairs, number of candidate pairs with a path scoring <= maxStep, [(score, gap) of each
  link]).
  """
  nbFrames = len(frameBounds) - 1
  leftoverByFrame = []
  for frame in range(nbFrames):
    leftover = np.arange(frameBounds[frame], frameBounds[frame + 1])
    leftover = leftover[inPool[leftover]]
    if exclusion is not None and len(leftover):
      leftover = leftover[~exclusion.excluded(leftover, frame)]
    leftoverByFrame.append(leftover)

  pairs = {}  # (id of the track whose end it is, id of the track whose beginning it is) -> (score, path)
  nbCandidates = 0
  for endId in sorted(tracks.detections):
    last = tracks.last[endId]
    endPosition = tracks.lastPositions([endId])
    beginningsByFrame = {}
    for frame in range(last + 1, min(last + maxGapFrames, nbFrames - 1) + 1):
      beginnings = tracks.startingAt(frame)
      if beginnings:
        close = _distances(endPosition, tracks.firstPositions(beginnings))[0] <= maxDistance
        if close.any():
          beginningsByFrame[frame] = [beginning for beginning, isClose in zip(beginnings, close) if isClose]
    if not beginningsByFrame:
      continue
    nbCandidates += sum(len(beginnings) for beginnings in beginningsByFrame.values())
    lastBeginningFrame = max(beginningsByFrame)
    # Frontier: the points of the current frame reachable from the track end with a largest step <= maxStep, with
    # that best largest step (on the frame of the track end: the track end itself, with 0).
    frontierPositions, frontierScores = endPosition, np.zeros(1)
    history = []  # for each frame after the track end: (frontier detections, index of their predecessor)
    frame = last
    while True:
      for beginning in beginningsByFrame.get(frame + 1, ()):
        steps = _distances(frontierPositions, tracks.firstPositions([beginning]))[:, 0]
        scores = np.maximum(frontierScores, steps)
        best = _bestOfTies(scores, steps)
        if scores[best] <= maxStep:
          pairs[(endId, beginning)] = (scores[best], _tracePath(history, best))
      frame += 1
      if frame >= lastBeginningFrame or not len(leftoverByFrame[frame]):
        break
      leftover = leftoverByFrame[frame]
      steps = _distances(frontierPositions, positions[leftover])
      scores = np.maximum(frontierScores[:, None], steps)
      bestScores = scores.min(axis=0)
      predecessors = np.where(scores == bestScores, steps, np.inf).argmin(axis=0)
      reachable = bestScores <= maxStep
      if not reachable.any():
        break
      history.append((leftover[reachable], predecessors[reachable]))
      frontierPositions, frontierScores = positions[leftover[reachable]], bestScores[reachable]

  if not pairs:
    return nbCandidates, 0, []
  endIds = sorted({endId for endId, _ in pairs})
  beginningIds = sorted({beginningId for _, beginningId in pairs})
  rowOf = {endId: row for row, endId in enumerate(endIds)}
  columnOf = {beginningId: column for column, beginningId in enumerate(beginningIds)}
  scoreMatrix = np.full((len(endIds), len(beginningIds)), np.inf)
  gapMatrix = np.zeros(scoreMatrix.shape)
  for (endId, beginningId), (score, _path) in pairs.items():
    scoreMatrix[rowOf[endId], columnOf[beginningId]] = score
    gapMatrix[rowOf[endId], columnOf[beginningId]] = tracks.first[beginningId] - tracks.last[endId]
  # 1e-9 per frame of gap: even summed over all the links, far too small to outweigh a real difference of scores, so it
  # only decides between exactly equal scores (frequent with positions in whole pixels).
  links = _gatedAssignment(scoreMatrix, maxStep, cost=np.where(np.isfinite(scoreMatrix), scoreMatrix + 1e-9 * gapMatrix, np.inf))

  absorbedBy = {}  # id of a track merged into another one -> id of that other track
  linkStats = []
  for row, column in links:
    endId, beginningId = endIds[row], beginningIds[column]
    score, path = pairs[(endId, beginningId)]
    trackId = endId
    while trackId in absorbedBy:  # the track whose end it is may already have been merged after another track
      trackId = absorbedBy[trackId]
    for detection in path:
      tracks.append(trackId, detection)
      inPool[detection] = False
    tracks.merge(trackId, beginningId)
    absorbedBy[beginningId] = trackId
    linkStats.append((score, gapMatrix[row, column]))
  return nbCandidates, len(pairs), linkStats


def _assignTracksToSlots(spans, nbAnimalsPerWell):
  """
  Slot of each track (-1 if it does not fit), spans being the (first frame, last frame) of each track. When there are
  enough slots, each track gets its own slot (in order of first frame). Otherwise, tracks share slots, longest tracks
  first; two tracks only share a slot if at least one empty frame separates them, so that they are never drawn as one
  continuous trajectory.
  """
  order = sorted(range(len(spans)), key=lambda t: (spans[t][0], t))
  slots = [-1] * len(spans)
  if len(spans) <= nbAnimalsPerWell:
    for slot, t in enumerate(order):
      slots[t] = slot
    return slots
  slotFirsts = [[] for _ in range(nbAnimalsPerWell)]  # first frames of the tracks placed in each slot, sorted
  slotLasts = [[] for _ in range(nbAnimalsPerWell)]  # their last frames, in the same order
  for t in sorted(order, key=lambda t: spans[t][0] - spans[t][1]):  # stable sort: longest first, then by first frame
    first, last = spans[t]
    for slot in range(nbAnimalsPerWell):
      k = bisect.bisect_left(slotFirsts[slot], first)
      if (k == 0 or slotLasts[slot][k - 1] < first - 1) and (k == len(slotFirsts[slot]) or slotFirsts[slot][k] > last + 1):
        slotFirsts[slot].insert(k, first)
        slotLasts[slot].insert(k, last)
        slots[t] = slot
        break
  return slots


def _readColumns(dataset):
  """Values of a per-frame results dataset as a 2D array (same reading as getDataPerTimeInterval)."""
  if 'columns' in dataset.attrs:
    return np.column_stack([dataset[column][:] for column in dataset.attrs['columns']])
  return np.array(dataset[:])


def _readDetectionPool(results, numWell, nbAnimalsPerWell, detectionSource):
  """
  (frames, positions, confidences, nbFrames, description) of the detections available for this well, or None (with
  a message) if they can't be found.
  """
  nbFrames = len(results[f'dataForWell{numWell}/dataForAnimal0/dataPerFrame/HeadPos'])
  rawDatasetName = _RAW_DETECTIONS_DATASET.format(numWell=numWell)
  if detectionSource not in ('auto', 'rawYoloDetections', 'storedSlots'):
    raise ValueError(f'detectionSource must be "auto", "rawYoloDetections" or "storedSlots", not "{detectionSource}"')

  if detectionSource == 'rawYoloDetections' or (detectionSource == 'auto' and rawDatasetName in results):
    if rawDatasetName not in results:
      print(f"{_LOG_PREFIX} well {numWell}: no YOLO detections recorded in the results file ({rawDatasetName} is "
            f"missing: the tracking must be launched with \"OrTools\": 1 to record them), nothing done.")
      return None
    raw = results[rawDatasetName][:]
    frames = raw['frame'].astype(int)
    positions = np.column_stack(((raw['x1'] + raw['x2']) / 2, (raw['y1'] + raw['y2']) / 2)).astype(float)
    confidence = raw['score'].astype(float)
    description = f"every YOLO box recorded during the tracking ({rawDatasetName})"
  else:
    frames, positions, confidence = [], [], []
    for numAnimal in range(nbAnimalsPerWell):
      dataGroup = results[f'dataForWell{numWell}/dataForAnimal{numAnimal}/dataPerFrame']
      if 'probabilityGoodDetection' not in dataGroup:
        print(f"{_LOG_PREFIX} well {numWell}: no detection probabilities in the results file (the tracking must be "
              f"launched with \"addGoodDetectionProbability\": 1), nothing done.")
        return None
      headPos = _readColumns(dataGroup['HeadPos']).astype(float)
      probability = np.asarray(dataGroup['probabilityGoodDetection'][:], dtype=float).reshape(-1)
      slotFrames = np.flatnonzero(np.isfinite(headPos).all(axis=1) & ~((headPos[:, 0] == 0) & (headPos[:, 1] == 0)))
      frames.append(slotFrames)
      positions.append(headPos[slotFrames])
      confidence.append(probability[slotFrames])
    frames = np.concatenate(frames)
    positions = np.concatenate(positions).reshape(-1, 2)
    confidence = np.concatenate(confidence)
    description = f"the points stored in the {nbAnimalsPerWell} slots of the well (HeadPos + probabilityGoodDetection)"

  keep = (frames >= 0) & (frames < nbFrames) & np.isfinite(positions).all(axis=1) & np.isfinite(confidence)
  return frames[keep], positions[keep], confidence[keep], nbFrames, description


def _defaultMinConfidence(results):
  """yolo11MinConf of the configuration file used for the tracking (0 if not found)."""
  configuration = results.get('configurationFileUsed')
  if configuration is not None and 'yolo11MinConf' in configuration.attrs:
    return float(configuration.attrs['yolo11MinConf'])
  return 0.


def growTracksFromConfidentDetections(videoName, numWell, nbAnimalsPerWell, maxDisplacement=5, exclusionRadius=0,
                                      bridgeGaps=True, bridgeMaxGapFrames=150, bridgeMaxDistance=300, bridgeMaxStep=10,
                                      seedConfidence=0.5, confidenceStep=0.05, minConfidence=None,
                                      detectionSource='storedSlots', verbose=True):
  """
  Post-processing step usually run once, right after the YOLO tracking (configuration file:
  "growTracksFromConfidentDetections": 1), or later on an existing results file by calling it directly. It rebuilds
  all the trajectories of a well from the YOLO detections, ignoring the tracks stored in the slots, and replaces them.

  The tracks are seeded with the confident detections only, and then grown with less and less confident detections:
  during this growth, a detection is never linked to a track (and two tracks are never merged) if they are more than
  maxDisplacement pixels apart. The pieces of tracks obtained are then linked across their gaps (step 3, bridgeGaps).
  A track is a sequence of detections on consecutive frames, one detection per frame.

  THE DETECTIONS ("POOL")
  ------------------------
  All the YOLO detections whose confidence is >= minConfidence. By default (detectionSource="storedSlots"), they are
  the points stored in the nbAnimalsPerWell slots (HeadPos, with their probabilityGoodDetection as confidence: the
  tracking must be launched with "addGoodDetectionProbability": 1). If the slots were already post-processed (by this
  function or another one), they hold that result, not the original detections. With detectionSource="rawYoloDetections",
  they are the YOLO boxes recorded during the tracking (dataset OrToolsTracking/well<numWell>/detections, written when
  the tracking is launched with "OrTools": 1: every box YOLO outputs, weak ones included); with detectionSource="auto",
  these recorded boxes when the results file has them, and otherwise the slots. The position of a detection is the
  center of its box.

  INITIAL PROCESS
  ----------------
  From the first frame to the last one: in frame n, each detection with confidence >= seedConfidence that is at most
  maxDisplacement away from the last position of a track ending in frame n-1 is a candidate to extend such a track.
  The candidates are matched to these tracks with the Hungarian algorithm (as many matches as possible, then the
  smallest total distance; only pairs at most maxDisplacement apart can be matched). Every detection >= seedConfidence
  that is not matched starts a new track. All these detections leave the pool. A track that gets no detection in
  frame n ends in frame n-1.

  CORE PROCESS, repeated until one iteration changes nothing
  -----------------------------------------------------------
  Step 1: for each frame n (from the first to the last), the tracks ending in frame n and the tracks starting in
  frame n+1 are matched with the Hungarian algorithm (only pairs whose facing ends are at most maxDisplacement
  apart), and each matched pair is merged into one track.
  Step 2: for each confidence tier [seedConfidence - confidenceStep, seedConfidence), then
  [seedConfidence - 2 * confidenceStep, seedConfidence - confidenceStep), ... down to [0, confidenceStep): from the
  first frame to the last one, in frame n, the detections of this tier still in the pool are matched with the
  Hungarian algorithm (only pairs at most maxDisplacement apart) with the tracks ending in frame n-1 (distance to
  their last position) and the tracks starting in frame n+1 (distance to their first position). A matched detection
  leaves the pool and extends its track (a track extended forward in frame n can then be extended again in frame n+1
  during the same pass); an unmatched one stays in the pool.
  The iterations stop as soon as one iteration (step 1 + step 2) neither merges any track nor takes any detection
  from the pool.

  STEP 3: GAP BRIDGING (bridgeGaps, on by default)
  -------------------------------------------------
  Links the pieces of tracks obtained above across their gaps, through the detections left in the pool.
  1) Every pair (end of a track, beginning of another track) at most bridgeMaxGapFrames frames apart (the beginning
     after the end) and at most bridgeMaxDistance pixels apart is a candidate. For each candidate pair, the path made of
     one left over detection per frame of the gap whose largest step (distance between the points of two consecutive
     frames, from the end of the first track to the beginning of the second one) is the smallest possible is found
     (exactly, by dynamic programming over the frames). That largest step is the score of the pair, and the pairs
     scoring more than bridgeMaxStep are dropped. A left over detection can be used by several paths (two linked
     tracks can then share a point in a frame of their gaps). With exclusionRadius > 0, the left over detections within
     exclusionRadius of a point of a track are not used (they are taken for duplicate boxes of tracked animals).
  2) The remaining pairs are linked with the Hungarian algorithm (as many links as possible, then the smallest total
     score; between exactly equal scores, the shortest gap wins), and each linked pair becomes one track, its path
     filling the gap. The tracks are then final.

  EXCLUSION RADIUS (optional, off by default)
  --------------------------------------------
  With a low YOLO confidence threshold, YOLO outputs several overlapping boxes for each animal. Without this option,
  these duplicate boxes can build several tracks on the same animal: when a track misses a frame, the track ending
  just before and the track starting just after can each take a different duplicate box in that frame, so they
  overlap, can never be merged, and then keep growing side by side on duplicate boxes. With exclusionRadius > 0, a
  detection that is within exclusionRadius pixels of a point already held by a track in the same frame never joins
  nor starts a track (it is taken for a duplicate box of an animal already tracked). In practice:
    - the matched pairs of a frame are accepted from the closest one to the farthest one, and a detection within
      exclusionRadius of a detection accepted before it in the same frame is left unmatched;
    - in the initial process, the unmatched detections start new tracks from the most confident one to the least
      confident one, so of two duplicate confident boxes only the most confident one starts a track.
  The price: two different animals closer than exclusionRadius (overlapping) cannot both be tracked in that frame.

  OUTPUT
  -------
  The tracks are written into the HeadPos of the nbAnimalsPerWell slots ([0, 0] where a slot has no track), together
  with probabilityGoodDetection when it exists (the confidence of the detection used, 0 elsewhere). Every frame of
  the results is written, the last one included. When there are more tracks than slots, tracks share slots (longest
  tracks first), two tracks sharing a slot being always separated by at least one empty frame; tracks that still do
  not fit are dropped (a message says how many). Nothing else in the results file is modified: in particular, the
  OrToolsTracking/well<numWell>/tracks table, if any, still describes the OrTools result, not the new HeadPos.

  PARAMETERS
  ----------
  videoName : str
      Results file (as for all dataAPI functions: a video name, or the path of the .h5 file).
  numWell : int
      Process one well per call (loop over the wells outside this function).
  nbAnimalsPerWell : int
      Number of slots: the stored slots read (detectionSource "storedSlots") and the slots written.
  maxDisplacement : float, default 5
      Maximum distance (pixels) between a detection and the end of the track it extends, and between the facing
      ends of two merged tracks.
  exclusionRadius : float, default 0
      See EXCLUSION RADIUS above; 0 disables it (the algorithm is then exactly the one described above it). Should
      be clearly smaller than the distance between the centers of two animals side by side, and about twice
      maxDisplacement to catch the duplicate boxes taken by the two tracks around a missed frame (whose centers can
      be up to about 2 * maxDisplacement apart). Example: on a video of slow cavefish (~33 px long) tracked with a
      YOLO confidence threshold of 0.01, 10 removed every stacked duplicate track (maxDisplacement 5).
  bridgeGaps : bool, default True
      Run step 3 (gap bridging).
  bridgeMaxGapFrames : int, default 150
      Step 3: maximum number of frames between the end of a track and the beginning of the track it is linked to
      (1 = the beginning is on the frame right after the end).
  bridgeMaxDistance : float, default 300
      Step 3: maximum distance (pixels) between the end of a track and the beginning of the track it is linked to.
  bridgeMaxStep : float, default 10
      Step 3: maximum score of a link, i.e. maximum distance (pixels) between the points of two consecutive frames
      along the path filling the gap. On a video of slow cavefish (~1 px/frame), the links checked on the video with a
      score >= 10 were the doubtful ones (paths through crowds of fish or through the many weak detections of a rope),
      while 15 also linked a few real fast fish: raise it for faster animals, lower it if wrong links remain.
  seedConfidence : float, default 0.5
      Detections with at least this confidence start/extend tracks in the initial process.
  confidenceStep : float, default 0.05
      Width of the confidence tiers of the core process's step 2.
  minConfidence : float, optional
      Detections with a lower confidence are ignored. Defaults to the yolo11MinConf of the configuration file used
      for the tracking (stored in the results file), or 0 if not found.
  detectionSource : "storedSlots" (default), "rawYoloDetections" or "auto"
      Where the detections are read (see THE DETECTIONS above). With "rawYoloDetections", nothing is done if the
      results file has no recorded YOLO boxes.
  verbose : bool, default True
      Prints a summary of each step.

  RETURNS
  -------
  The list of the nbAnimalsPerWell (nbFrames, 2) arrays written into HeadPos (None if nothing was done).
  """
  if nbAnimalsPerWell == 0:
    return []

  with openResultsFile(videoName, 'r') as results:
    loaded = _readDetectionPool(results, numWell, nbAnimalsPerWell, detectionSource)
    if minConfidence is None:
      minConfidence = _defaultMinConfidence(results)
  if loaded is None:
    return None
  frames, positions, confidence, nbFrames, description = loaded

  keep = confidence >= minConfidence
  order = np.argsort(frames[keep], kind='stable')
  frames, positions, confidence = frames[keep][order], positions[keep][order], confidence[keep][order]
  frameBounds = np.searchsorted(frames, np.arange(nbFrames + 1))  # detections of frame n: frameBounds[n]:frameBounds[n+1]
  if verbose:
    print(f"{_LOG_PREFIX} well {numWell}: {len(frames)} detections with confidence >= {minConfidence} over {nbFrames} "
          f"frames, read from {description}.")

  tracks = _Tracks(positions)
  exclusion = _ExclusionZones(positions, exclusionRadius) if exclusionRadius > 0 else None
  inPool = np.ones(len(frames), dtype=bool)
  inPool[_seedTracks(tracks, positions, confidence, frameBounds, seedConfidence, maxDisplacement, exclusion)] = False
  if verbose:
    print(f"{_LOG_PREFIX} well {numWell}: initial process: {len(frames) - inPool.sum()} detections with confidence >= "
          f"{seedConfidence} formed {len(tracks.detections)} tracks" +
          (f" (exclusion radius: {exclusionRadius} px)." if exclusion is not None else "."))

  # Confidence tiers of step 2, from the most confident one: [seedConfidence - confidenceStep, seedConfidence), ...
  tierDetectionsByFrame = []
  nbTiers = int(np.ceil(round(seedConfidence / confidenceStep, 9)))
  for numTier in range(nbTiers):
    high = round(seedConfidence - numTier * confidenceStep, 9)
    low = max(round(seedConfidence - (numTier + 1) * confidenceStep, 9), 0.)
    inTier = np.flatnonzero(inPool & (confidence >= low) & (confidence < high))
    tierFrames, firstIndex = np.unique(frames[inTier], return_index=True)
    tierDetectionsByFrame.append((low, high, dict(zip(tierFrames.tolist(), np.split(inTier, firstIndex[1:])))))

  iteration = 0
  while True:
    iteration += 1
    nbMerges = _mergeConsecutiveTracks(tracks, maxDisplacement)
    absorbedPerTier = [_absorbConfidenceTier(tracks, positions, detectionsByFrame, inPool, maxDisplacement, exclusion)
                       for _low, _high, detectionsByFrame in tierDetectionsByFrame]
    if verbose:
      perTier = ', '.join(f"[{low:g},{high:g}): {nb}" for (low, high, _), nb in zip(tierDetectionsByFrame, absorbedPerTier) if nb)
      print(f"{_LOG_PREFIX} well {numWell}: core iteration {iteration}: {nbMerges} track merges, "
            f"{sum(absorbedPerTier)} detections taken from the pool" + (f" ({perTier})" if perTier else "") +
            f", {len(tracks.detections)} tracks.")
    if not nbMerges and not sum(absorbedPerTier):
      break

  if bridgeGaps:
    nbCandidates, nbKept, linkStats = _bridgeGaps(tracks, positions, frameBounds, inPool, exclusion,
                                                  bridgeMaxGapFrames, bridgeMaxDistance, bridgeMaxStep)
    if verbose:
      scores, gaps = np.array([s for s, _ in linkStats]), np.array([g for _, g in linkStats])
      print(f"{_LOG_PREFIX} well {numWell}: gap bridging: {nbCandidates} candidate pairs (track end -> track beginning "
            f"<= {bridgeMaxGapFrames} frames and <= {bridgeMaxDistance} px later), {nbKept} with a path whose largest "
            f"step is <= {bridgeMaxStep} px, {len(linkStats)} links made" +
            (f" (score median {np.median(scores):.2f} px, max {scores.max():.2f} px; gap median {np.median(gaps):g} "
             f"frames, max {gaps.max():g})" if len(linkStats) else "") + f", {len(tracks.detections)} tracks.")

  trackIds =sorted(tracks.detections, key=lambda trackId: (tracks.first[trackId], trackId))
  slots = _assignTracksToSlots([(tracks.first[trackId], tracks.last[trackId]) for trackId in trackIds], nbAnimalsPerWell)
  outputPositions = [np.zeros((nbFrames, 2)) for _ in range(nbAnimalsPerWell)]
  outputConfidence = [np.zeros(nbFrames) for _ in range(nbAnimalsPerWell)]
  for trackId, slot in zip(trackIds, slots):
    if slot < 0:
      continue
    detections = np.fromiter(tracks.detections[trackId], dtype=int)
    outputPositions[slot][frames[detections]] = positions[detections]
    outputConfidence[slot][frames[detections]] = confidence[detections]

  if verbose:
    lengths = np.array([len(tracks.detections[trackId]) for trackId in trackIds])
    nbDropped = sum(slot < 0 for slot in slots)
    print(f"{_LOG_PREFIX} well {numWell}: final: {len(trackIds)} tracks (median length {np.median(lengths) if len(lengths) else 0:g} "
          f"frames, {int((lengths == 1).sum())} single-frame tracks), {int(inPool.sum())} detections left in the pool, "
          f"{len(set(slots) - {-1})} slots used" + (f", {nbDropped} tracks DROPPED for lack of a free slot "
          f"(nbAnimalsPerWell={nbAnimalsPerWell})" if nbDropped else "") + ".")

  with openResultsFile(videoName, 'a') as results:
    for numAnimal in range(nbAnimalsPerWell):
      dataGroup = results[f'dataForWell{numWell}/dataForAnimal{numAnimal}/dataPerFrame']
      headPosDataset = dataGroup['HeadPos']
      headPos = headPosDataset[:]
      if 'columns' in headPosDataset.attrs:
        columnX, columnY = headPosDataset.attrs['columns'][:2]
        headPos[columnX], headPos[columnY] = outputPositions[numAnimal][:, 0], outputPositions[numAnimal][:, 1]
      else:
        headPos[:, 0], headPos[:, 1] = outputPositions[numAnimal][:, 0], outputPositions[numAnimal][:, 1]
      headPosDataset[...] = headPos
      if 'probabilityGoodDetection' in dataGroup:
        dataGroup['probabilityGoodDetection'][...] = outputConfidence[numAnimal].reshape(dataGroup['probabilityGoodDetection'].shape)

  return outputPositions


# Example usage, once per well:
# for numWell in range(nbWells):
#     growTracksFromConfidentDetections(videoName, numWell, nbAnimalsPerWell, maxDisplacement=5)
