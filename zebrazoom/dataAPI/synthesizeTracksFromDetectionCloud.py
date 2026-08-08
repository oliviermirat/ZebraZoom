import os

import numpy as np
from scipy.optimize import linear_sum_assignment

import zebrazoom.dataAPI as dataAPI


def _fmtPos(pos):
  return f"({pos[0]:.1f},{pos[1]:.1f})"


class _Diagnostics:
  """
  Unified logger for synthesizeTracksFromDetectionCloud. Two levels:

  - summary(msg): a short, human-readable line describing a stage's overall
    outcome. Printed to stdout when verbose (as before this diagnosis mode
    existed), and always written to the diagnosis file when enabled.
  - detail(msgFn): a fine-grained, per-frame/per-decision line -- far too
    voluminous for stdout, so it only ever goes to the diagnosis file.
    Takes a NO-ARGUMENT CALLABLE (typically a lambda) rather than a plain
    string, and only calls it when the file is actually open, so building
    an expensive, loop-heavy diagnostic string costs nothing when
    diagnosisMode=False.

  A disabled-and-non-verbose instance is a fast no-op everywhere: summary()
  returns immediately, detail()'s lambda is never even invoked.

  The point of this whole mechanism: when a fish that used to be tracked
  goes missing, "why" is almost never obvious from the final output alone
  -- it requires seeing what the tracker considered and rejected, frame by
  frame, in the area/time the fish was last seen. That's exactly what the
  detail log is for. Search it for the frame numbers and approximate pixel
  coordinates where the fish disappeared to find the relevant PREDICT/
  PASS1/PASS2/MISS/KILL lines (Stage 1), then the STAGE2 TRACKLET/CANDIDATE
  lines to see whether/why a reconnection was or wasn't made, then the
  STAGE4 lines to see whether a recovered trajectory was ultimately
  rejected as fake and why.
  """

  def __init__(self, enabled, verbose, filePath):
    self.enabled = enabled
    self.verbose = verbose
    self.filePath = filePath
    self._fh = open(filePath, 'w', encoding='utf-8') if enabled else None
    self.lineCount = 0

  def summary(self, msg):
    if self.verbose:
      print(msg)
    if self._fh:
      self._fh.write(msg + "\n")
      self.lineCount += 1

  def detail(self, msgFn):
    if self._fh:
      self._fh.write(msgFn() + "\n")
      self.lineCount += 1

  def close(self):
    if self._fh:
      self._fh.close()
      self._fh = None


def _inv2x2(S):
  """
  Closed-form inverse of a 2x2 matrix. Every covariance/gating computation
  in this module lives in 2D measurement space, so this is called a huge
  number of times (once per track/cluster pair, every single frame); the
  generic np.linalg.inv/solve pay for LAPACK dispatch and dtype checks that
  dwarf the two multiplications an explicit 2x2 formula actually needs, so
  hand-coding it is a meaningful, easily-verified speedup, not premature
  optimization.
  """
  a, b = S[0, 0], S[0, 1]
  c, d = S[1, 0], S[1, 1]
  det = a * d - b * c
  return np.array([[d, -b], [-c, a]]) / det


# ============================================================================
# Low-level building blocks
# ============================================================================

class _ConstantVelocityKalmanFilter2D:
  """
  Textbook constant-velocity Kalman filter, state x = [x, y, vx, vy].

  Used per-track in Stage 1 (see synthesizeTracksFromDetectionCloud below) so
  that both PREDICTION (where do we expect this fish next frame) and GATING
  (how far is "too far" to still be the same fish) are principled and, most
  importantly, uncertainty-aware: P (the state covariance) shrinks every time
  a track gets a confident measurement and grows every frame it doesn't,
  which is exactly the behaviour we want during a crossing / brief occlusion
  -- the filter automatically becomes more tolerant of a bigger jump the
  longer it's been coasting blind, instead of using one fixed pixel radius
  for every situation.
  """

  F = np.array([[1, 0, 1, 0],
                [0, 1, 0, 1],
                [0, 0, 1, 0],
                [0, 0, 0, 1]], dtype=float)
  H = np.array([[1, 0, 0, 0],
                [0, 1, 0, 0]], dtype=float)

  def __init__(self, initialPos, processNoiseScale):
    self.x = np.array([initialPos[0], initialPos[1], 0.0, 0.0], dtype=float)
    # weak position prior, very weak velocity prior (we have no motion estimate yet)
    self.P = np.diag([25.0, 25.0, 400.0, 400.0])
    self.q = processNoiseScale

  def predict(self):
    Q = np.diag([0.25 * self.q, 0.25 * self.q, self.q, self.q])
    self.x = self.F @ self.x
    self.P = self.F @ self.P @ self.F.T + Q

  def update(self, z, R, positionOnly=False):
    """
    positionOnly=True performs a restricted update that corrects position
    but deliberately leaves velocity untouched. Used when the "detection"
    being fed in is really an unresolved multi-fish blob (see
    _buildTrackletsOnline's isFused handling): the blob's centroid is still
    useful evidence of roughly where the track's fish is, but the apparent
    velocity implied by chasing a drifting blob centroid is not -- it's an
    artifact of two fish's combined motion, not either one's real heading.
    Zeroing the velocity rows of the Kalman gain (consistently, in both the
    state and covariance updates) keeps this a valid, if intentionally
    conservative, linear estimator: trust the measurement for where, not
    for which way. This preserves the track's pre-contact heading through
    a prolonged close contact, so that when the fish separate again the
    track is still a good prior for reclaiming the fish it actually
    started on rather than drifting onto whichever fish the blob's average
    position happened to end up nearer to.
    """
    y = z - self.H @ self.x
    S = self.H @ self.P @ self.H.T + R
    K = self.P @ self.H.T @ _inv2x2(S)
    if positionOnly:
      K = K.copy()
      K[2:, :] = 0
    self.x = self.x + K @ y
    self.P = (np.eye(4) - K @ self.H) @ self.P

  @property
  def pos(self):
    return self.x[:2]

  @property
  def vel(self):
    return self.x[2:]


def _clusterPointsAtFrame(points, radius, confidences=None):
  """
  Single-linkage clustering of the raw points detected at one frame: any two
  points closer than `radius` are placed in the same cluster (transitively),
  and every cluster collapses to a single representative position.

  This is what turns the "abundance of points" (with yolo11MinConf set very
  low, a real fish typically fires 3 to 6 overlapping YOLO detections) into
  a single, denoised position estimate per physical fish -- averaging
  several redundant boxes on the same fish is a strictly better position
  estimate than picking any single one of them.

  `confidences`, if provided (the per-point YOLO detection confidence,
  aligned with `points`), is used two ways: the representative centroid is
  a confidence-weighted average rather than a plain mean (a detection YOLO
  was more sure about pulls the estimate toward it more), and each cluster
  carries a 'meanConfidence' -- how sure YOLO was, on average, that this
  blob of points is really a fish. When `confidences` is None (the caller
  has no probabilityGoodDetection data for this video), every point is
  treated as equally trusted and 'meanConfidence' is a neutral 1.0.

  Returns a list of dicts {centroid, weight (member count), spread (mean
  distance of members to the centroid), points (the raw member points, kept
  around in case _splitCluster later needs to re-partition this cluster),
  confidences (per-member, for the same reason), meanConfidence}.
  """
  n = len(points)
  if n == 0:
    return []
  if n == 1:
    conf = float(confidences[0]) if confidences is not None else 1.0
    ptConfidences = confidences if confidences is not None else np.array([1.0])
    return [{'centroid': points[0], 'weight': 1, 'spread': 0.0, 'points': points,
             'confidences': ptConfidences, 'meanConfidence': conf}]

  parent = list(range(n))

  def find(a):
    while parent[a] != a:
      parent[a] = parent[parent[a]]
      a = parent[a]
    return a

  # one vectorized pairwise-distance computation instead of n^2 individual
  # np.linalg.norm calls -- this is by far the hottest loop in the whole
  # module (called once per frame, over every raw point in the frame), and
  # the per-call Python/numpy dispatch overhead of n^2 tiny norm() calls
  # swamps the actual arithmetic for any realistic point count.
  diffs = points[:, np.newaxis, :] - points[np.newaxis, :, :]
  distMatrix = np.sqrt((diffs ** 2).sum(axis=2))
  closeI, closeJ = np.where(np.triu(distMatrix < radius, k=1))
  for i, j in zip(closeI.tolist(), closeJ.tolist()):
    ri, rj = find(i), find(j)
    if ri != rj:
      parent[ri] = rj

  groups = {}
  for i in range(n):
    groups.setdefault(find(i), []).append(i)

  clusters = []
  for idx in groups.values():
    pts = points[idx]
    if confidences is not None:
      memberConfidences = confidences[idx]
      centroid = np.average(pts, axis=0, weights=np.maximum(memberConfidences, 1e-6))
      meanConfidence = float(memberConfidences.mean())
    else:
      memberConfidences = np.ones(len(idx))
      centroid = pts.mean(axis=0)
      meanConfidence = 1.0
    spread = float(np.linalg.norm(pts - centroid, axis=1).mean()) if len(idx) > 1 else 0.0
    clusters.append({'centroid': centroid, 'weight': len(idx), 'spread': spread, 'points': pts,
                      'confidences': memberConfidences, 'meanConfidence': meanConfidence})
  return clusters


def _splitCluster(cluster, seeds, iterations=5):
  """
  Re-partitions a single cluster's raw member points into len(seeds)
  sub-clusters via a few iterations of Lloyd's algorithm (k-means), warm-
  started at `seeds` (the predicted positions of the tracks competing for
  this cluster).

  This is the mechanism that lets two (or three) fish that briefly fuse into
  one blob during a crossing be told apart using the informative prior of
  where each of them was already expected to be, instead of collapsing them
  into a single point and forcing one of the two tracks to simply go blind
  for the duration of the contact.
  """
  pts = cluster['points']
  confs = cluster['confidences']
  k = len(seeds)
  centers = np.array(seeds, dtype=float).copy()
  assign = np.zeros(len(pts), dtype=int)
  for _ in range(iterations):
    dists = np.linalg.norm(pts[:, np.newaxis, :] - centers[np.newaxis, :, :], axis=2)
    assign = np.argmin(dists, axis=1)
    for c in range(k):
      members = pts[assign == c]
      if len(members) > 0:
        centers[c] = members.mean(axis=0)

  subClusters = []
  for c in range(k):
    members = pts[assign == c]
    if len(members) == 0:
      continue
    memberConfidences = confs[assign == c]
    centroid = np.average(members, axis=0, weights=np.maximum(memberConfidences, 1e-6))
    meanConfidence = float(memberConfidences.mean())
    spread = float(np.linalg.norm(members - centroid, axis=1).mean()) if len(members) > 1 else 0.0
    subClusters.append({'centroid': centroid, 'weight': len(members), 'spread': spread, 'points': members,
                         'confidences': memberConfidences, 'meanConfidence': meanConfidence})
  return subClusters


def _velocityFromEntries(entries, n=3, fromEnd=False):
  """Finite-difference velocity (px/frame) estimated from the first/last `n`
  entries of a trajectory; used only for Stage 2's motion-consistency cost."""
  sample = entries[-n:] if fromEnd else entries[:n]
  if len(sample) < 2:
    return np.zeros(2)
  frames = np.array([e[0] for e in sample], dtype=float)
  positions = np.array([e[1] for e in sample])
  dt = frames[-1] - frames[0]
  if dt <= 0:
    return np.zeros(2)
  return (positions[-1] - positions[0]) / dt


def _hermiteInterpolateGap(p0, v0, p1, v1, gap):
  """
  Cubic Hermite interpolation of the (gap - 1) missing frames strictly
  between a known (position, velocity) at one end and a known (position,
  velocity) at the other, `gap` frames later. Unlike a straight line, this
  matches the direction/speed the fish was already leaving on AND the
  direction/speed it's already moving with when picked back up, which
  avoids an unnatural kink at either end of a bridged gap.
  """
  result = []
  for step in range(1, gap):
    t = step / gap
    h00 = 2 * t ** 3 - 3 * t ** 2 + 1
    h10 = t ** 3 - 2 * t ** 2 + t
    h01 = -2 * t ** 3 + 3 * t ** 2
    h11 = t ** 3 - t ** 2
    pos = h00 * p0 + h10 * gap * v0 + h01 * p1 + h11 * gap * v1
    result.append((step, pos))
  return result


# ============================================================================
# Stage 4: fake-fish removal
# ============================================================================

def _realFishStats(track):
  """
  Shared computation behind _isRealFish, factored out so diagnostic logging
  (Stage 2 eligibility checks, the final Stage 4 gate) can report the exact
  numbers a trajectory was judged on, not just the pass/fail verdict.

  Returns (length, cumulativeRealDisplacement, numRealRuns, realRuns). See
  _isRealFish for what these mean and why cumulative-across-runs is used
  instead of either a plain first-vs-last check or requiring any single run
  to pass alone.
  """
  entries = track['entries']
  length = entries[-1][0] - entries[0][0] + 1

  realRuns = []
  run = []
  for entry in entries:
    isReal = entry[2] if len(entry) > 2 else True
    if isReal:
      run.append(entry)
    elif run:
      realRuns.append(run)
      run = []
  if run:
    realRuns.append(run)

  cumulativeRealDisplacement = sum(np.linalg.norm(run[-1][1] - run[0][1]) for run in realRuns)
  return length, cumulativeRealDisplacement, len(realRuns), realRuns


def _passesRealismTest(length, cumulativeRealDisplacement, minSegmentLength, minNetDisplacement,
                        minAverageSpeed=0.0):
  """
  Shared pass/fail rule behind _isRealFish, _isStitchEligible (Stage 2) and
  the Stage 4 gate, factored out so all three apply IDENTICAL criteria to
  the same (length, cumulativeRealDisplacement) numbers instead of three
  hand-written copies of the same formula silently drifting apart.

  minNetDisplacement alone is a flat, duration-independent floor: it asks
  "did this trajectory cover at least minNetDisplacement px of genuine
  motion, ever", regardless of whether that trajectory spans 10 frames or
  300. That's the right question for short/typical trajectories, but it
  quietly breaks down for a trajectory that happens to span (close to) the
  WHOLE video: a persistently-redetected but genuinely static false
  detection (a reflection, a piece of debris) accumulates its own frame-to-
  frame jitter for hundreds of frames, and pure noise doesn't average to
  exactly zero -- over a long enough run it can drift past a flat 10px
  floor purely by chance, even though its average speed (displacement /
  length) is nowhere near what an actually-swimming fish shows. Real,
  confirmed fish -- even slow ones -- were observed to sustain at least
  roughly 0.12-0.15 px/frame across a full 300-frame trajectory, while a
  confirmed fake, near-static object sat at roughly 0.04 px/frame; the same
  0.04 px/frame signature turned up, independently, on similarly long-
  lived low-confidence trajectories in two other videos.

  minAverageSpeed adds a second, duration-SCALED requirement on top of the
  flat floor rather than replacing it: the effective minimum displacement
  becomes max(minNetDisplacement, minAverageSpeed * length). For a short
  trajectory this makes no difference (minAverageSpeed * length stays below
  minNetDisplacement), so ordinary short/typical tracks are completely
  unaffected; it only starts to bind once a trajectory has been alive long
  enough that "just barely clearing the flat floor" stops being a
  meaningful signal of real, purposeful motion. Default 0.0 keeps the old,
  duration-independent behavior for any caller that doesn't pass one.
  """
  if length < minSegmentLength:
    return False
  return cumulativeRealDisplacement >= max(minNetDisplacement, minAverageSpeed * length)


def _isRealFish(track, minSegmentLength, minNetDisplacement, minAverageSpeed=0.0):
  """
  A track that never really got anywhere between its first and its last
  frame (or that is too short to trust either way) is almost certainly a
  static false detection, not a fish. "Really got anywhere" is judged from
  CUMULATIVE, genuinely-observed motion rather than a single first-vs-last
  measurement, to close a specific loophole without opening a different one:

  - Two separate, genuinely stationary false detections (e.g. two pieces of
    debris) can end up joined into one track by an interpolated gap-fill
    (Stage 1 coasting, or a Stage 2 stitch). Naively comparing first-to-last
    position on the WHOLE trajectory would then pass, even though NEITHER
    original piece ever moved -- the interpolation itself, not any real
    observed motion, supplies the apparent travel.
  - But a real, genuinely-swimming fish is not always seen continuously
    either: YOLO can legitimately lose and reacquire it every few frames,
    producing many short, individually-modest real bursts that only add up
    to something substantial when taken together. Requiring any ONE such
    burst to independently cover minNetDisplacement on its own -- an
    earlier, stricter version of this function -- wrongly rejected exactly
    this common, benign pattern.

  The fix that satisfies both: each entry in track['entries'] is
  (frame, xy) or (frame, xy, isReal) (isReal defaults to True when absent,
  e.g. for callers/tests that don't track the distinction). The trajectory
  is split into maximal runs of consecutive REAL (non-interpolated)
  entries, and the NET displacement of every individual run (first-to-last
  position WITHIN that run) is summed across all runs. Jitter around one or
  a few static locations never accumulates real net displacement this way,
  however many runs it's split into (each run's own net displacement stays
  near zero), whereas a real fish's short bursts of real, directed motion
  add up -- exactly the cumulative signal minNetDisplacement is meant to
  measure. A track with no interpolated entries at all (the common case) is
  one single real run spanning the whole thing, so this reduces to exactly
  a plain first-vs-last check.

  See _passesRealismTest for what minAverageSpeed adds on top of this.
  """
  length, cumulativeRealDisplacement, _, _ = _realFishStats(track)
  return _passesRealismTest(length, cumulativeRealDisplacement, minSegmentLength, minNetDisplacement,
                             minAverageSpeed)


# ============================================================================
# Stage 1: online (causal, per-frame) tracklet construction
# ============================================================================

def _buildTrackletsOnline(rawSlots, rawConfidence, nbAnimalsPerWell, nbFrames, clusterDistanceThreshold,
                           splitAmbiguousClusters, gatingMahalanobisThreshold,
                           measurementNoiseBase, processNoiseScale, minHitsToConfirm,
                           maxMissesTentative, maxFramesToCoast, maxReacquisitionDistance,
                           maxPlausibleSpeed, maxConsecutiveWeakMatches, diag, numWell,
                           measurementConfidenceFloor=0.5, maxGatingCovariance=300.0,
                           maxGapForReacquisitionFallback=2):
  """
  Frame-by-frame multi-object tracker producing a set of "tracklets"
  (trajectory fragments). Every active track carries its own
  _ConstantVelocityKalmanFilter2D. `rawConfidence` (optional, aligned with
  rawSlots -- None if the video has no probabilityGoodDetection data) feeds
  YOLO's own per-detection confidence into clustering (see
  _clusterPointsAtFrame) and into the Kalman measurement noise: a cluster
  built from several LOW-confidence boxes is treated as less trustworthy
  even if it has decent raw point count, and each track accumulates a
  running 'confidenceSum' (÷ 'hits' = how sure YOLO was, on average, about
  the detections that built it) that Stage 2 and the final fake-fish gate
  both use. Each frame:

    1) every active track's filter is predicted forward;
    2) any cluster simultaneously "claimed" (predicted position nearby) by
       several CONFIRMED tracks is provisionally split (see _splitCluster)
       so a crossing doesn't force a single wrong pick;
    3) tracks are matched to (possibly split) clusters via the Hungarian
       algorithm on a cost that is the BETTER of two views of the same pair:
       the motion-model (Mahalanobis) distance to the filter's predicted
       position, gated at gatingMahalanobisThreshold ("STRONG" match), OR a
       simple straight-line distance to the track's last CONFIRMED
       position, gated at maxReacquisitionDistance ("WEAK" match). The
       second view exists because a constant-velocity model is a poor
       predictor exactly when a fish makes a sharp turn (e.g. bouncing off
       a well wall): the predicted position drifts away fast even though
       the fish's actual position barely moved, and a real fish never
       teleports regardless of how wrong its current velocity estimate is
       -- so a raw-distance fallback recovers it in one frame instead of
       losing it to a coast-then-maybe-Stage-2-stitch that a pure motion
       model would need. But that same forgivingness is dangerous if it
       fires over and over: a track that has lost its real fish (e.g. two
       fish collided and only one track can win the fused cluster) can
       otherwise hop from one marginal, motion-inconsistent detection to
       the next indefinitely, hallucinating a smooth "trajectory" out of
       what is really an unrelated chain of weak coincidences -- so a
       track that racks up more than maxConsecutiveWeakMatches WEAK
       matches in a row is killed outright rather than allowed to keep
       walking (see step 4). On top of both views, a track that has been
       coasting (predicted but not corrected) for a while accumulates
       growing covariance, and growing covariance makes even the STRONG
       view progressively cheaper for ANY nearby detection -- including one
       that belongs to a completely different, genuinely stationary object
       a modest distance away (e.g. two separate pieces of debris), which
       neither the STRONG nor the WEAK test alone is guaranteed to catch.
       A hard, physically-grounded veto closes that gap: no match, strong
       or weak, is ever accepted if it is farther from the track's last
       real position than maxReacquisitionDistance plus
       maxPlausibleSpeed*(frames since that last match) -- no fish can
       outrun a cap on how far it could plausibly have travelled, no
       matter how forgiving the covariance-driven cost has become;
    4) matched tracks are updated (and any internal coasting gap is filled
       via Hermite interpolation using the filter's own velocity estimate
       just before/after the correction). If the winning match was WEAK,
       the track's consecutive-weak-match counter increments and, once it
       exceeds maxConsecutiveWeakMatches, the track is finalized right
       then instead of being updated -- the cluster is left unclaimed so
       another track (or a fresh one) can use it. If the matched cluster's
       spread suggests it's really an unresolved multi-fish blob (did not
       get split in step 2, most commonly because only one confirmed track
       is competing for it), the Kalman update is position-only (see
       _ConstantVelocityKalmanFilter2D.update): the track's pre-contact
       heading is preserved through the contact instead of being corrupted
       by the blob's drifting average position, which gives it a better
       shot at reclaiming the right fish once the contact ends;
    5) unmatched tracks accumulate a miss; TENTATIVE tracks (not yet proven
       real -- fewer than minHitsToConfirm consecutive hits) are dropped
       after maxMissesTentative misses (cheap, fast noise rejection);
       CONFIRMED tracks are given much more slack (maxFramesToCoast) since
       real fish keep firing detections almost every frame and a long gap
       is far more likely to be an occlusion/crossing than actual absence;
    6) unmatched clusters spawn new tentative tracks.

  Returns the list of every tracklet that ever existed (as plain dicts with
  at least a 'tid', a 'strongHits' count, and an 'entries' list of
  (frame, xy) pairs, contiguous from the tracklet's own first to last
  frame), confirmed or not -- the fake-fish filter downstream is what
  ultimately prunes the noise.
  """
  frameClusters = []
  for t in range(nbFrames):
    validMask = [not (rawSlots[k][t][0] == 0 and rawSlots[k][t][1] == 0) for k in range(nbAnimalsPerWell)]
    pts = np.array([rawSlots[k][t] for k in range(nbAnimalsPerWell) if validMask[k]])
    confs = (np.array([rawConfidence[k][t] for k in range(nbAnimalsPerWell) if validMask[k]])
             if rawConfidence is not None else None)
    frameClusters.append(_clusterPointsAtFrame(pts, clusterDistanceThreshold, confs))

  activeTracks = {}
  finishedTracklets = []
  nextTid = 0
  nbConfirmed = 0
  nbNoiseRejected = 0
  nbSplits = 0
  nbWeakChainKilled = 0

  def _matchAndApply(t, clusters, candidateTrackIds, candidateClusterIdx, useReacquisitionFallback):
    """
    Runs one Hungarian assignment between candidateTrackIds and the clusters at
    candidateClusterIdx (indices into the outer `clusters` list for this frame), applies
    every accepted match (Kalman update, gap interpolation, hit/miss/status bookkeeping,
    weak-match-chain killing -- see the STRONG/WEAK note below), and returns the set of
    track ids and the set of (outer-numbered) cluster indices consumed this call.
    """
    nonlocal nbConfirmed, nbWeakChainKilled
    matchedTids, matchedCidx = set(), set()
    if not candidateTrackIds or not candidateClusterIdx:
      return matchedTids, matchedCidx

    subClusters = [clusters[c] for c in candidateClusterIdx]
    # measurement noise R is diagonal (r*I), so for a fixed per-track HPHt = [[a0,b0],[c0,d0]],
    # S = HPHt + r*I only shifts the diagonal -- the whole row of the cost matrix (one track vs.
    # every cluster) is computed in one vectorized shot per track instead of one Python-level
    # np.linalg.solve call per (track, cluster) pair, which is by far the hottest inner loop here.
    centroids = np.array([c['centroid'] for c in subClusters])
    weights = np.array([c['weight'] for c in subClusters], dtype=float)
    meanConfidences = np.array([c['meanConfidence'] for c in subClusters], dtype=float)
    # effective sample size is scaled by how sure YOLO was about these points, not just how many
    # there were -- a cluster built from several LOW-confidence boxes is still not very trustworthy.
    # Floored at measurementConfidenceFloor (NOT a lower, more permissive floor): letting rVals
    # grow without real limit for a near-zero-confidence cluster makes the Mahalanobis cost of
    # matching it artificially "cheap" for ANY nearby track, including one that rightfully
    # belongs to a completely different, well-established detection a real distance away -- in
    # one observed real case, a long-tracked fish briefly missed one frame and its own rightful,
    # nearly-exact-position detection went unclaimed while it was instead matched, at a cost
    # comfortably under gate, to an unrelated cluster 54px away purely because that cluster's
    # confidence (0.03) let its effective noise balloon under the old, more permissive floor.
    rVals = measurementNoiseBase / np.maximum(weights * meanConfidences, measurementConfidenceFloor)

    cost = np.empty((len(candidateTrackIds), len(subClusters)))
    mahalanobisCostMatrix = np.empty_like(cost)
    for i, tid in enumerate(candidateTrackIds):
      tr = activeTracks[tid]
      kf = tr['kf']
      HPHt = kf.H @ kf.P @ kf.H.T
      # Capped for GATING purposes only -- the Kalman UPDATE a few lines below still uses the
      # real, uncapped kf.P, so the filter's own internal state is unaffected. Left uncapped, a
      # track that keeps missing for long enough eventually has a Pxx/Pyy so large that even a
      # jump of ~100px prices out cheaper than gatingMahalanobisThreshold, no matter how far
      # maxFramesToCoast is lowered -- there is always some "last possible frame" with maximally
      # inflated covariance, and shrinking maxFramesToCoast only moves where that frame is, not
      # whether it exists. In one observed real case a track coasting right up to
      # maxFramesToCoast's limit had its covariance grow enough that a 92px jump to a
      # low-confidence, unrelated cluster passed the gate (cost 8.06 against a 9.21 threshold)
      # on the very last frame before it would otherwise have died. Capping how much the
      # matching test is ever allowed to trust keeps the gate meaningful throughout the whole
      # coasting window instead of only near its start.
      a0 = min(HPHt[0, 0], maxGatingCovariance)
      d0 = min(HPHt[1, 1], maxGatingCovariance)
      b0, c0 = HPHt[0, 1], HPHt[1, 0]
      aArr, dArr = a0 + rVals, d0 + rVals
      detArr = aArr * dArr - b0 * c0
      yArr = centroids - kf.pos
      y0, y1 = yArr[:, 0], yArr[:, 1]
      mahalanobisCost = (dArr * y0 ** 2 - (b0 + c0) * y0 * y1 + aArr * y1 ** 2) / detArr
      mahalanobisCostMatrix[i, :] = mahalanobisCost

      lastFrame, lastPos = tr['entries'][-1][0], tr['entries'][-1][1]
      staticDist = np.linalg.norm(centroids - lastPos, axis=1)
      gapSinceLastMatch = t - lastFrame

      if useReacquisitionFallback and gapSinceLastMatch <= maxGapForReacquisitionFallback:
        # positional re-acquisition fallback: a fish that just made a sharp turn (e.g. off a
        # well wall) can badly fool the constant-velocity prediction used above, yet it still
        # can't have physically moved far from where it was last actually seen. Rescale plain
        # distance-from-last-confirmed-position onto the same cost scale as the Mahalanobis
        # distance and let whichever view of the pair is more forgiving win. Only offered to
        # tracks in the SECOND assignment pass (see below) -- a track that matched cleanly
        # last frame doesn't need this crutch, and letting it use it anyway is exactly what let
        # an uncertain, coasting track's inflated (and therefore artificially cheap) covariance
        # outbid a confident track for a detection that rightfully belonged to the confident one.
        #
        # Also gated on gapSinceLastMatch: this fallback is a FLAT distance radius with no
        # gap-scaling at all, unlike every other test here (the Mahalanobis cost naturally
        # loosens as covariance grows, and even that is now capped -- see maxGatingCovariance).
        # Its own comment states the scenario it exists for precisely: recovering from a sharp
        # turn the constant-velocity model couldn't see coming, in a SINGLE missed frame. Left
        # available for tracks that have been coasting many frames, it becomes a second, gap-
        # blind route to exactly the failure maxGatingCovariance was added to close: in one
        # observed real case, a track that had genuinely lost its fish 6 frames earlier matched
        # a completely unrelated, low-confidence cluster 58.5px away -- just inside the flat
        # 60px radius -- entirely through this fallback (its Mahalanobis-only cost, unaffected
        # by this fallback, was far over gate).
        staticCost = (staticDist / maxReacquisitionDistance) * gatingMahalanobisThreshold
        cost[i, :] = np.minimum(mahalanobisCost, staticCost)
      else:
        cost[i, :] = mahalanobisCost

      # HARD veto, independent of both cost views above: a track that has been coasting a
      # while (predict()-ed every frame with no correcting measurement) accumulates growing
      # covariance, and growing covariance makes the Mahalanobis test progressively cheaper
      # for ANY nearby detection -- including one that belongs to a completely different,
      # genuinely stationary object (e.g. two separate pieces of debris a modest distance
      # apart), which the motion-model test alone can eventually be fooled into accepting as
      # "the same object, just re-predicted with low confidence". No physical fish can outrun
      # a hard cap on how far it could plausibly have travelled since it was last actually
      # seen, so cap it here regardless of what either cost view above says.
      maxPlausibleDist = maxReacquisitionDistance + maxPlausibleSpeed * gapSinceLastMatch
      cost[i, staticDist > maxPlausibleDist] += 1e6
    cost[cost > gatingMahalanobisThreshold] += 1e6

    rowInd, colInd = linear_sum_assignment(cost)
    matchedRows = set()
    matchLines, killLines, confirmLines = [], [], []
    for r, c in zip(rowInd, colInd):
      if cost[r, c] >= 1e6:
        continue
      matchedRows.add(r)
      tid = candidateTrackIds[r]
      tr = activeTracks[tid]
      cluster = subClusters[c]
      origClusterIdx = candidateClusterIdx[c]

      # a STRONG match is one the pure motion model would have accepted by itself; a WEAK
      # match only survived through the static re-acquisition fallback. A track allowed to
      # chain an unbounded run of WEAK matches can hop from one marginal, motion-inconsistent
      # detection to the next indefinitely -- hallucinating a smooth "trajectory" out of what
      # is really an unrelated string of coincidences. Cut that off after
      # maxConsecutiveWeakMatches instead of letting it run.
      isStrong = mahalanobisCostMatrix[r, c] <= gatingMahalanobisThreshold
      if not isStrong and tr['consecutiveWeakMatches'] + 1 > maxConsecutiveWeakMatches:
        killLines.append(f"tid={tid} consecutiveWeak={tr['consecutiveWeakMatches']} "
                          f"lastRealPos={_fmtPos(tr['entries'][-1][1])} "
                          f"attemptedClusterPos={_fmtPos(cluster['centroid'])}")
        finishedTracklets.append(tr)
        del activeTracks[tid]
        nbWeakChainKilled += 1
        continue  # cluster stays unclaimed this frame: free for another track or a fresh spawn

      # a cluster whose spread wasn't resolved by splitting (typically because only one
      # CONFIRMED track is currently competing for it) is an unresolved multi-fish blob:
      # trust its centroid for position but not for the velocity it would otherwise imply.
      isFused = cluster['spread'] > 0.3 * clusterDistanceThreshold
      R = np.eye(2) * (measurementNoiseBase / max(cluster['weight'] * cluster['meanConfidence'], measurementConfidenceFloor))

      lastFrame, lastPos = tr['entries'][-1][0], tr['entries'][-1][1]
      gap = t - lastFrame
      v0 = tr['kf'].vel.copy()
      tr['kf'].update(cluster['centroid'], R, positionOnly=isFused)
      if gap > 1:
        v1 = tr['kf'].vel.copy()
        for step, pos in _hermiteInterpolateGap(lastPos, v0, tr['kf'].pos, v1, gap):
          tr['entries'].append((lastFrame + step, pos, False))  # interpolated, not observed
      tr['entries'].append((t, tr['kf'].pos.copy(), True))  # a real, directly-matched detection

      tr['hits'] += 1
      tr['misses'] = 0
      tr['confidenceSum'] += cluster['meanConfidence']
      if isStrong:
        tr['consecutiveWeakMatches'] = 0
        tr['strongHits'] += 1
      else:
        tr['consecutiveWeakMatches'] += 1
      # confirmation requires minHitsToConfirm STRONG hits specifically, not just any match --
      # a track that has only ever survived on the reacquisition fallback hasn't actually
      # demonstrated motion-consistent evidence of a real object yet, and letting it reach
      # 'confirmed' status anyway (e.g. by chaining 3 unrelated weak matches right up to the
      # maxConsecutiveWeakMatches cutoff) would make it eligible for Stage 2 stitching and let
      # it survive Stage 4's fake-fish filter as its own short "trajectory" purely by chance.
      if tr['status'] == 'tentative' and tr['strongHits'] >= minHitsToConfirm:
        tr['status'] = 'confirmed'
        nbConfirmed += 1
        confirmLines.append(f"tid={tid} strongHits={tr['strongHits']} pos={_fmtPos(tr['kf'].pos)}")

      matchedTids.add(tid)
      matchedCidx.add(origClusterIdx)
      matchLines.append(f"tid={tid}->cid={origClusterIdx}@{_fmtPos(cluster['centroid'])} "
                         f"cost={cost[r, c]:.2f} kind={'STRONG' if isStrong else 'WEAK'}"
                         + (" FUSED" if isFused else "") + (" gap>1" if gap > 1 else ""))

    passLabel = "PASS2" if useReacquisitionFallback else "PASS1"
    if matchLines:
      diag.detail(lambda: f"F{t:06d} {passLabel} MATCH " + " | ".join(matchLines))
    if killLines:
      diag.detail(lambda: f"F{t:06d} {passLabel} KILL reason=weakChain " + " | ".join(killLines))
    if confirmLines:
      diag.detail(lambda: f"F{t:06d} {passLabel} CONFIRM " + " | ".join(confirmLines))

    # for every candidate that did NOT end up matched, report its single best candidate
    # cluster (by pure motion-model cost, ignoring every gate) and exactly which gate(s)
    # rejected it -- or, if it passed every gate but still wasn't picked, that it lost out
    # to a better-fitting competitor in the globally optimal assignment. This is the single
    # most useful line in the whole trace for "why didn't my fish's track continue here".
    nomatchLines = []
    for i, tid in enumerate(candidateTrackIds):
      if i in matchedRows or mahalanobisCostMatrix.shape[1] == 0:
        continue
      bestC = int(np.argmin(mahalanobisCostMatrix[i, :]))
      bestMahal = float(mahalanobisCostMatrix[i, bestC])
      bestCluster = subClusters[bestC]
      trLast = activeTracks[tid]['entries'][-1]
      bestStaticDist = float(np.linalg.norm(bestCluster['centroid'] - trLast[1]))
      gapSince = t - trLast[0]
      vetoMax = maxReacquisitionDistance + maxPlausibleSpeed * gapSince
      reasons = []
      if bestMahal > gatingMahalanobisThreshold:
        reasons.append(f"mahalanobis={bestMahal:.1f}>gate={gatingMahalanobisThreshold}")
      if useReacquisitionFallback and bestStaticDist > maxReacquisitionDistance:
        staticCost = (bestStaticDist / maxReacquisitionDistance) * gatingMahalanobisThreshold
        if staticCost > gatingMahalanobisThreshold:
          reasons.append(f"staticFallbackCost={staticCost:.1f}>gate={gatingMahalanobisThreshold}")
      if bestStaticDist > vetoMax:
        reasons.append(f"HARD_VETO staticDist={bestStaticDist:.1f}>maxPlausibleDist={vetoMax:.1f}"
                        f"(gapSinceLastMatch={gapSince})")
      if not reasons:
        reasons.append("passed_all_gates_but_lost_to_a_better_competitor_in_optimal_assignment")
      nomatchLines.append(f"tid={tid} bestCandidate={_fmtPos(bestCluster['centroid'])} "
                           f"mahal={bestMahal:.2f} staticDist={bestStaticDist:.1f} "
                           f"reasons=[{'; '.join(reasons)}]")
    if nomatchLines:
      diag.detail(lambda: f"F{t:06d} {passLabel} NOMATCH " + " | ".join(nomatchLines))

    return matchedTids, matchedCidx

  for t in range(nbFrames):
    for tr in activeTracks.values():
      tr['kf'].predict()

    clusters = frameClusters[t]

    if clusters:
      diag.detail(lambda clusters=clusters: f"F{t:06d} RAWPTS n={sum(c['weight'] for c in clusters)} "
                  + " ".join(f"{_fmtPos(p)}c{cf:.2f}" for c in clusters
                             for p, cf in zip(c['points'], c['confidences'])))
      diag.detail(lambda clusters=clusters: f"F{t:06d} CLUSTERS(pre-split) n={len(clusters)} "
                  + " ".join(f"[{_fmtPos(c['centroid'])} w={c['weight']} spread={c['spread']:.1f} "
                             f"conf={c['meanConfidence']:.2f}]" for c in clusters))

    if splitAmbiguousClusters and clusters:
      confirmedIds = [tid for tid, tr in activeTracks.items() if tr['status'] == 'confirmed']
      if len(confirmedIds) >= 2:
        newClusters = []
        for cluster in clusters:
          competing = [tid for tid in confirmedIds
                       if np.linalg.norm(activeTracks[tid]['kf'].pos - cluster['centroid'])
                       < clusterDistanceThreshold * 2]
          if len(competing) >= 2 and cluster['weight'] >= 2 and cluster['spread'] > 0.3 * clusterDistanceThreshold:
            k = min(len(competing), 3)
            seeds = [activeTracks[tid]['kf'].pos for tid in competing[:k]]
            subClusters = _splitCluster(cluster, seeds)
            newClusters.extend(subClusters)
            nbSplits += 1
            diag.detail(lambda cluster=cluster, competing=competing, subClusters=subClusters:
                        f"F{t:06d} SPLIT cluster_centroid={_fmtPos(cluster['centroid'])} "
                        f"weight={cluster['weight']} competing_tracks={competing} -> "
                        + " ".join(f"[{_fmtPos(sc['centroid'])} w={sc['weight']}]" for sc in subClusters))
          else:
            newClusters.append(cluster)
        clusters = newClusters
        diag.detail(lambda clusters=clusters: f"F{t:06d} CLUSTERS(post-split) n={len(clusters)} "
                    + " ".join(f"[{_fmtPos(c['centroid'])} w={c['weight']} conf={c['meanConfidence']:.2f}]"
                               for c in clusters))

    if activeTracks:
      diag.detail(lambda: f"F{t:06d} PREDICT n={len(activeTracks)} "
                  + " ".join(f"[tid={tid} {tr['status']} miss={tr['misses']} pos={_fmtPos(tr['kf'].pos)} "
                             f"vel=({tr['kf'].vel[0]:.2f},{tr['kf'].vel[1]:.2f}) "
                             f"Pxx={tr['kf'].P[0,0]:.1f} strongHits={tr['strongHits']} "
                             f"lastReal=F{tr['entries'][-1][0]:06d}@{_fmtPos(tr['entries'][-1][1])}]"
                             for tid, tr in activeTracks.items()))

    matchedClusterIdx = set()
    matchedTrackIds = set()
    if activeTracks and clusters:
      trackIds = list(activeTracks.keys())

      # PASS 1: tracks that matched cleanly last frame ("confident") get first, EXCLUSIVE pick
      # of nearby clusters, using ONLY the strict motion-model test (no re-acquisition fallback,
      # they don't need it). This is what stops an uncertain/coasting track from ever winning a
      # detection away from a confident one just because its own inflated, post-coast covariance
      # makes almost anything look "cheap" in raw Mahalanobis terms -- without this priority
      # split, a plain single Hungarian pass over every track at once can and does let a lost,
      # drifting track outbid the fish's rightful, actively-tracking track for its own detection.
      #
      # "Confident" additionally requires strongHits well past minHitsToConfirm, not just
      # misses==0 -- a track that only just reached 'confirmed' status a couple of frames ago
      # has, by definition, never had the chance to miss yet, so misses==0 alone doesn't
      # distinguish it from a track with months of established evidence behind it. Without this,
      # a brand-new, barely-confirmed track spawned right next to an established track's
      # temporarily-missed detection can win PASS 1's exclusive pick of that detection outright
      # (the established track, having missed last frame, is demoted to PASS 2 and left with
      # whatever's leftover) -- in one observed real case this is exactly how a long-tracked real
      # fish's rightful next detection was handed to a track that had existed for all of 3 frames,
      # forcing the real fish's own track onto a distant, wrong cluster instead.
      confidentIds = [tid for tid in trackIds
                       if activeTracks[tid]['misses'] == 0 and activeTracks[tid]['strongHits'] >= 2 * minHitsToConfirm]
      remainingClusterIdx = list(range(len(clusters)))
      if confidentIds:
        m, c = _matchAndApply(t, clusters, confidentIds, remainingClusterIdx, useReacquisitionFallback=False)
        matchedTrackIds |= m
        matchedClusterIdx |= c
        remainingClusterIdx = [ci for ci in remainingClusterIdx if ci not in c]

      # PASS 2: everyone still unmatched (uncertain/coasting tracks, plus any confident track
      # that didn't find a strict match above) competes for whatever clusters are left, with the
      # full Mahalanobis + re-acquisition-fallback test as before.
      pass2Ids = [tid for tid in trackIds if tid not in matchedTrackIds and tid in activeTracks]
      if pass2Ids and remainingClusterIdx:
        m, c = _matchAndApply(t, clusters, pass2Ids, remainingClusterIdx, useReacquisitionFallback=True)
        matchedTrackIds |= m
        matchedClusterIdx |= c

    unmatchedTids = [tid for tid in activeTracks if tid not in matchedTrackIds]
    for tid in unmatchedTids:
      tr = activeTracks[tid]
      tr['misses'] += 1
      patience = maxMissesTentative if tr['status'] == 'tentative' else maxFramesToCoast
      if tr['misses'] > patience:
        finishedTracklets.append(tr)
        if tr['status'] == 'tentative':
          nbNoiseRejected += 1
        diag.detail(lambda tid=tid, tr=tr, patience=patience:
                    f"F{t:06d} KILL track={tid} reason=patience_exceeded status={tr['status']} "
                    f"misses={tr['misses']}/{patience} lastPos={_fmtPos(tr['entries'][-1][1])} "
                    f"lastRealFrame=F{tr['entries'][-1][0]:06d}")
        del activeTracks[tid]
      elif unmatchedTids:
        diag.detail(lambda tid=tid, tr=tr, patience=patience:
                    f"F{t:06d} MISS track={tid} status={tr['status']} misses={tr['misses']}/{patience} "
                    f"lastPos={_fmtPos(tr['entries'][-1][1])}")

    for c, cluster in enumerate(clusters):
      if c in matchedClusterIdx:
        continue
      diag.detail(lambda nextTid=nextTid, cluster=cluster:
                  f"F{t:06d} SPAWN track={nextTid} pos={_fmtPos(cluster['centroid'])} "
                  f"weight={cluster['weight']} conf={cluster['meanConfidence']:.2f}")
      kf = _ConstantVelocityKalmanFilter2D(cluster['centroid'], processNoiseScale)
      activeTracks[nextTid] = {'tid': nextTid, 'kf': kf, 'status': 'tentative',
                                'hits': 1, 'misses': 0, 'strongHits': 1, 'consecutiveWeakMatches': 0,
                                'confidenceSum': cluster['meanConfidence'],
                                'entries': [(t, cluster['centroid'].copy(), True)]}
      nextTid += 1

  finishedTracklets.extend(activeTracks.values())

  diag.summary(f"[synthesizeTracksFromDetectionCloud] well {numWell}: Stage 1 (online Kalman tracking) "
               f"produced {len(finishedTracklets)} tracklet(s) ({nbConfirmed} reached confirmed status, "
               f"{nbNoiseRejected} tentative tracklet(s) rejected immediately as likely noise, "
               f"{nbWeakChainKilled} track(s) killed for chaining too many consecutive weak matches, "
               f"{nbSplits} ambiguous-cluster split(s) performed).")
  diag.detail(lambda: f"STAGE1 TRACKLETS n={len(finishedTracklets)} " + " | ".join(
      f"[tid={tr['tid']} {tr['status']} frames=[{tr['entries'][0][0]:06d},{tr['entries'][-1][0]:06d}] "
      f"start={_fmtPos(tr['entries'][0][1])} end={_fmtPos(tr['entries'][-1][1])} "
      f"strongHits={tr['strongHits']} hits={tr['hits']} "
      f"meanConf={(tr['confidenceSum'] / tr['hits'] if tr['hits'] else 1.0):.2f}]"
      for tr in finishedTracklets))

  return finishedTracklets


# ============================================================================
# Stage 2: offline (whole-video hindsight) global tracklet stitching
# ============================================================================

def _stitchTrackletsGlobally(tracklets, nbFrames, maxGapFramesForStitching, clusterDistanceThreshold,
                              minSegmentLength, minNetDisplacement, minMeanConfidenceForReal, diag, numWell,
                              minAverageSpeed=0.0):
  """
  Stage 1 is necessarily causal: at frame t it can only use what happened at
  frame <= t. This stage runs AFTER the whole video has already been
  processed, so it can do something a causal tracker never can: look at
  BOTH ends of every gap between two tracklets and ask whether the ones on
  either side are moving consistently with becoming one continuous fish --
  the exit velocity of the earlier tracklet extrapolated forward should land
  near the later tracklet's start, AND the later tracklet's entry velocity
  extrapolated backward should land near the earlier tracklet's end.

  Every (tracklet-end, tracklet-start) pair satisfying the gap/motion
  constraints is a candidate; the whole set of candidates is resolved in one
  shot with the Hungarian algorithm, which finds the single globally best
  set of pairings -- as opposed to a greedy scan that commits to the first
  good-enough candidate it stumbles across and can't undo it later even if a
  better one turns up. This is what recovers a fish whose Stage-1 tracklet
  died (occlusion, or nbAnimalsPerWell slot starvation upstream, longer than
  maxFramesToCoast) and reappeared under a fresh tracklet.

  The motion-consistency tolerance for a candidate pair is scaled down the
  weaker either tracklet is (see the 'strongHits' quality score computed in
  Stage 1) and by how sure YOLO was about each one's detections on average
  ('confidenceSum' / 'hits', when confidence data is available): two long,
  well-established, high-confidence tracklets get the full, generous
  tolerance, but a tracklet that only just barely reached 'confirmed'
  status, or was built mostly from low-confidence boxes, gets a much
  stricter one. Chains built purely out of such barely-qualifying fragments
  -- which is what a stray run of duplicate/spurious detections tends to
  produce -- are therefore hard to link into one long, fabricated
  trajectory even when each individual hop looks locally plausible enough
  to pass on its own.

  CRITICALLY, a tracklet is only eligible to participate in a stitch at all
  if it ALREADY looks like a plausible piece of a real trajectory ON ITS
  OWN -- i.e. it independently passes the exact same length/displacement
  test used by Stage 4 (_isRealFish) to reject fake fish, using ITS OWN
  first and last position, before any stitching happens. Without this, two
  entirely separate STATIC false detections (e.g. two different pieces of
  debris, or two reflections, each individually immobile and therefore
  exactly the kind of thing Stage 4 exists to reject) could be bridged by
  the interpolated gap between them into one trajectory that LOOKS mobile
  purely because of the artificial travel invented by the bridge itself --
  the stitch would manufacture the very displacement that lets the result
  slip past Stage 4, even though neither original piece ever moved at all.
  """
  for tr in tracklets:
    tr['startFrame'] = tr['entries'][0][0]
    tr['endFrame'] = tr['entries'][-1][0]
    tr['startPos'] = tr['entries'][0][1]
    tr['endPos'] = tr['entries'][-1][1]
    tr['entryVel'] = _velocityFromEntries(tr['entries'], n=3, fromEnd=False)
    tr['exitVel'] = _velocityFromEntries(tr['entries'], n=3, fromEnd=True)
    tr['meanConfidence'] = tr['confidenceSum'] / tr['hits'] if tr.get('hits') else 1.0

  # Only tracklets that (a) reached 'confirmed' status in Stage 1 AND (b) already look like a
  # plausible piece of a real trajectory ON THEIR OWN (same test Stage 4 uses) are trusted
  # enough to participate in stitching (as either end of a candidate pair). See the docstring
  # above for why (b) matters: without it, two independently-immobile false detections can be
  # bridged into one fake "mobile" trajectory by the interpolation itself. A never-confirmed
  # tracklet -- typically a single isolated low-confidence noise detection, with no velocity
  # estimate of its own (_velocityFromEntries returns zero for it) -- would also let the
  # motion-consistency check degenerate into a lenient static-distance check. Ineligible
  # tracklets still pass through to Stage 4 untouched, as their own (usually too-short/
  # immobile/low-confidence-to-survive) singleton trajectory.
  def _isStitchEligible(tr):
    if tr['status'] != 'confirmed':
      return False, 'not_confirmed'
    length, cumDisp, nRuns, _ = _realFishStats(tr)
    if not _passesRealismTest(length, cumDisp, minSegmentLength, minNetDisplacement, minAverageSpeed):
      return False, f'fails_realism_test(length={length},cumulativeRealDisplacement={cumDisp:.1f})'
    if tr['meanConfidence'] < minMeanConfidenceForReal:
      return False, f'low_confidence({tr["meanConfidence"]:.2f}<{minMeanConfidenceForReal})'
    return True, 'eligible'

  eligibility = {tr['tid']: _isStitchEligible(tr) for tr in tracklets}
  diag.detail(lambda: f"STAGE2 ELIGIBILITY n={len(tracklets)} " + " | ".join(
      f"[tid={tr['tid']} frames=[{tr['startFrame']:06d},{tr['endFrame']:06d}] "
      f"start={_fmtPos(tr['startPos'])} end={_fmtPos(tr['endPos'])} -> {eligibility[tr['tid']][1]}]"
      for tr in tracklets))

  endCandidates = [tr for tr in tracklets if tr['endFrame'] < nbFrames - 1 and eligibility[tr['tid']][0]]
  startCandidates = [tr for tr in tracklets if tr['startFrame'] > 0 and eligibility[tr['tid']][0]]

  successorOf = {}
  if endCandidates and startCandidates:
    nE, nS = len(endCandidates), len(startCandidates)
    cost = np.full((nE, nS), 1e6)
    for i, a in enumerate(endCandidates):
      for j, b in enumerate(startCandidates):
        if a is b:
          continue
        gap = b['startFrame'] - a['endFrame']
        if gap <= 0 or gap > maxGapFramesForStitching:
          continue
        predictedBStart = a['endPos'] + a['exitVel'] * gap
        predictedAEnd = b['startPos'] - b['entryVel'] * gap
        forwardErr = np.linalg.norm(predictedBStart - b['startPos'])
        backwardErr = np.linalg.norm(predictedAEnd - a['endPos'])
        motionCost = 0.5 * (forwardErr + backwardErr)
        speedRef = max(np.linalg.norm(a['exitVel']), np.linalg.norm(b['entryVel']), 1.0)

        # Scale the tolerance by how well-established BOTH tracklets are. A pair of long,
        # well-established tracklets (the common, important case: a real fish's tracklet
        # broke in two around a long occlusion) gets the full, generous tolerance. A tracklet
        # that only just barely reached 'confirmed' status (a handful of strong hits) gets a
        # much stricter one. Without this, a chain of short, barely-qualifying fragments --
        # e.g. stray duplicate detections near a well wall, or a brief blip off some other
        # fish -- can each individually look like a "plausible enough" hop and be stitched
        # together into one long, entirely fabricated trajectory that a single strict A-to-B
        # check would have rejected outright, since each hop alone stays under the radar.
        qualityRef = 10.0
        minQualityFloor = 0.3
        weakestLink = min(a.get('strongHits', 0), b.get('strongHits', 0))
        qualityFactor = minQualityFloor + (1 - minQualityFloor) * min(1.0, weakestLink / qualityRef)

        # Same idea, driven by YOLO's own confidence instead of hit count: two fragments YOLO
        # was consistently unsure about (mean confidence near minMeanConfidenceForReal, the
        # bare minimum to even be eligible) get a much stricter tolerance than two fragments
        # YOLO was consistently confident about. A no-op (factor 1.0) when confidence data
        # isn't available, since meanConfidence then defaults to the neutral value 1.0.
        confRef = 0.6
        weakestConfidence = min(a['meanConfidence'], b['meanConfidence'])
        confidenceFactor = minQualityFloor + (1 - minQualityFloor) * min(1.0, weakestConfidence / confRef)

        tolerance = (clusterDistanceThreshold + 0.5 * speedRef * gap) * qualityFactor * confidenceFactor
        accepted = motionCost <= tolerance
        if accepted:
          cost[i, j] = motionCost + 0.01 * gap  # small tie-break preference for shorter gaps
        diag.detail(lambda a=a, b=b, gap=gap, motionCost=motionCost, tolerance=tolerance,
                    qualityFactor=qualityFactor, confidenceFactor=confidenceFactor, accepted=accepted:
                    f"STAGE2 CANDIDATE end_tid={a['tid']}(F{a['endFrame']:06d}@{_fmtPos(a['endPos'])}) -> "
                    f"start_tid={b['tid']}(F{b['startFrame']:06d}@{_fmtPos(b['startPos'])}) gap={gap} "
                    f"motionCost={motionCost:.1f} tolerance={tolerance:.1f} "
                    f"(qualityFactor={qualityFactor:.2f} confidenceFactor={confidenceFactor:.2f}) "
                    + ("ACCEPTED" if accepted else "rejected"))

    rowInd, colInd = linear_sum_assignment(cost)
    for r, c in zip(rowInd, colInd):
      if cost[r, c] < 1e6:
        successorOf[endCandidates[r]['tid']] = startCandidates[c]
    diag.detail(lambda: "STAGE2 ASSIGNMENT " + (
        " | ".join(f"end_tid={etid}->start_tid={s['tid']}" for etid, s in successorOf.items())
        if successorOf else "no stitches resolved"))

  successorTids = {s['tid'] for s in successorOf.values()}
  heads = [tr for tr in tracklets if tr['tid'] not in successorTids]

  merged = []
  usedTids = set()
  nbStitches = 0
  for head in heads:
    if head['tid'] in usedTids:
      continue
    chainEntries = list(head['entries'])
    totalStrongHits = head.get('strongHits', 0)
    totalConfidenceSum = head.get('confidenceSum', 0.0)
    totalHits = head.get('hits', 0)
    current = head
    usedTids.add(current['tid'])
    while current['tid'] in successorOf:
      nxt = successorOf[current['tid']]
      if nxt['tid'] in usedTids:
        break  # defensive: a matching can't legitimately produce a cycle, but never trust blindly
      gap = nxt['startFrame'] - current['endFrame']
      if gap > 1:
        for step, pos in _hermiteInterpolateGap(current['endPos'], current['exitVel'],
                                                  nxt['startPos'], nxt['entryVel'], gap):
          chainEntries.append((current['endFrame'] + step, pos, False))  # interpolated, not observed
      chainEntries.extend(nxt['entries'])
      totalStrongHits += nxt.get('strongHits', 0)
      totalConfidenceSum += nxt.get('confidenceSum', 0.0)
      totalHits += nxt.get('hits', 0)
      usedTids.add(nxt['tid'])
      nbStitches += 1
      current = nxt
    # a chain is only ever built out of already-confirmed pieces (endCandidates/startCandidates
    # are confirmed-only), so a multi-piece chain is always confirmed; an un-stitched head keeps
    # whatever status it already had (tentative heads pass through untouched to Stage 4).
    status = 'confirmed' if current is not head else head.get('status', 'tentative')
    merged.append({'tid': head['tid'], 'entries': chainEntries, 'strongHits': totalStrongHits,
                    'confidenceSum': totalConfidenceSum, 'hits': totalHits, 'status': status})

  diag.summary(f"[synthesizeTracksFromDetectionCloud] well {numWell}: Stage 2 (global motion-consistent "
               f"stitching) merged {len(tracklets)} tracklet(s) into {len(merged)} trajectory(ies) via "
               f"{nbStitches} stitch(es).")
  diag.detail(lambda: f"STAGE2 MERGED n={len(merged)} " + " | ".join(
      f"[tid={tr['tid']} {tr['status']} frames=[{tr['entries'][0][0]:06d},{tr['entries'][-1][0]:06d}] "
      f"start={_fmtPos(tr['entries'][0][1])} end={_fmtPos(tr['entries'][-1][1])} "
      f"strongHits={tr['strongHits']}]"
      for tr in merged))

  return merged


# ============================================================================
# Stage 3: collision pruning -- safety net against near-duplicate trajectories
# ============================================================================

def _pruneCollidingTracks(tracks, collisionPruneDistance, collisionPruneMinFrames, diag, numWell):
  """
  Real fish essentially never stay glued to within a few pixels of one
  another for many consecutive frames -- a genuine crossing / close contact
  is brief, and the inter-fish distance dips and then rises again. So if two
  of the surviving trajectories overlap in time and stay within
  collisionPruneDistance of each other for at least collisionPruneMinFrames
  consecutive frames, one of them is almost certainly not a second fish: it
  is a "ghost" that lost its own fish somewhere earlier (Stage 1's weak-match
  cutoff catches most of these before they can wander far, but this is the
  backstop for whatever still slips through, or that got stitched onto
  someone else's territory in Stage 2) and has drifted onto, or been
  reconnected onto, territory another track already legitimately owns.

  This mirrors the original mergeSameTracks logic (duplicate YOLO detections
  of the same fish glued to each other for a sustained stretch), just
  applied to the FINAL synthesized trajectories instead of the raw per-slot
  HybridSORT output, and using each trajectory's number of Stage-1 STRONG
  (motion-model-confirmed) hits, scaled by its mean YOLO confidence (when
  available), as the tie-break for which of the two is the real one, rather
  than which happens to be longer -- a ghost can easily rack up a long
  apparent duration purely from coasting/weak matches, so raw length is not
  a trustworthy signal of which trajectory to keep here.

  For every such stretch, the lower-quality trajectory is blanked out over
  that stretch only; the higher-quality one is left completely untouched.
  Blanking can split a trajectory into several disjoint pieces, so the
  result is re-expanded into one dict per surviving contiguous run.
  """
  diag.detail(lambda: f"STAGE3 INPUT n={len(tracks)} " + " | ".join(
      f"[i={idx} frames=[{tr['entries'][0][0]:06d},{tr['entries'][-1][0]:06d}] "
      f"start={_fmtPos(tr['entries'][0][1])} end={_fmtPos(tr['entries'][-1][1])}]"
      for idx, tr in enumerate(tracks)))

  positionByFrame = [{entry[0]: entry[1] for entry in tr['entries']} for tr in tracks]
  quality = [tr.get('strongHits', len(tr['entries']))
             * (tr.get('confidenceSum', tr.get('hits', 0)) / tr['hits'] if tr.get('hits') else 1.0)
             for tr in tracks]
  blankedFrames = [set() for _ in tracks]
  nbCollisions = 0

  for i in range(len(tracks)):
    for j in range(i + 1, len(tracks)):
      common = sorted(set(positionByFrame[i]) & set(positionByFrame[j]))
      if not common:
        continue
      closeFrames = [f for f in common
                     if np.linalg.norm(positionByFrame[i][f] - positionByFrame[j][f]) < collisionPruneDistance]
      diag.detail(lambda i=i, j=j, common=common, closeFrames=closeFrames:
                  f"STAGE3 COMPARE i={i} j={j} overlap_frames={len(common)}"
                  f"[{common[0]:06d},{common[-1]:06d}] close_frames={len(closeFrames)}"
                  + (f" close=[{closeFrames[0]:06d},{closeFrames[-1]:06d}]" if closeFrames else ""))

      run = []
      runs = []
      for f in closeFrames:
        if run and f != run[-1] + 1:
          runs.append(run)
          run = []
        run.append(f)
      if run:
        runs.append(run)

      loser = j if quality[i] >= quality[j] else i
      for run in runs:
        if len(run) < collisionPruneMinFrames:
          continue
        blankedFrames[loser].update(run)
        nbCollisions += 1
        winner = i if loser == j else j
        diag.summary(f"[synthesizeTracksFromDetectionCloud] well {numWell}: trajectories {i} and {j} "
                     f"stay within {collisionPruneDistance}px of each other over frames "
                     f"[{run[0]}, {run[-1]}] -- treating this as one fish, keeping the "
                     f"better-established trajectory ({'i' if winner == i else 'j'}, quality="
                     f"{quality[winner]:.1f} vs {quality[loser]:.1f}), discarding that "
                     f"stretch from the other")

  result = []
  for idx, tr in enumerate(tracks):
    keptEntries = [entry for entry in tr['entries'] if entry[0] not in blankedFrames[idx]]
    if not keptEntries:
      continue
    totalLen = len(tr['entries'])
    runStart = 0
    for k in range(1, len(keptEntries) + 1):
      if k == len(keptEntries) or keptEntries[k][0] != keptEntries[k - 1][0] + 1:
        piece = keptEntries[runStart:k]
        # confidenceSum/hits/strongHits are aggregate counts over the WHOLE original
        # trajectory; when blanking splits it into several pieces, apportion them
        # proportionally to how much of the original each piece retained, so a
        # downstream meanConfidence computed on a piece stays representative.
        frac = len(piece) / totalLen
        result.append({'entries': piece, 'status': tr.get('status', 'tentative'),
                        'strongHits': tr.get('strongHits', totalLen) * frac,
                        'confidenceSum': tr.get('confidenceSum', tr.get('hits', totalLen)) * frac,
                        'hits': tr.get('hits', totalLen) * frac})
        runStart = k

  diag.summary(f"[synthesizeTracksFromDetectionCloud] well {numWell}: Stage 3 (collision pruning) "
               f"resolved {nbCollisions} sustained-overlap stretch(es), yielding {len(result)} "
               f"trajectory piece(s) from the original {len(tracks)}.")
  diag.detail(lambda: f"STAGE3 OUTPUT n={len(result)} " + " | ".join(
      f"[frames=[{tr['entries'][0][0]:06d},{tr['entries'][-1][0]:06d}] "
      f"start={_fmtPos(tr['entries'][0][1])} end={_fmtPos(tr['entries'][-1][1])}]"
      for tr in result))

  return result


# Stage 4 (fake-fish removal) is _isRealFish, defined earlier among the low-level
# building blocks -- applied by the public entry point right after this stage.


# ============================================================================
# Stage 5: quality-prioritized packing into the nbAnimalsPerWell output slots
# ============================================================================

def _assignTracksToSlots(tracks, nbAnimalsPerWell, diag, numWell):
  """
  Packs the surviving trajectories into nbAnimalsPerWell output slots so
  that no two trajectories overlapping in time share a slot. Unlike a plain
  first-come-first-served packing (which is optimal only for MINIMIZING the
  number of slots used), trajectories are offered slots in order of
  decreasing duration, so that if there ever are more concurrently-alive
  trajectories than nbAnimalsPerWell (more real fish detected than the
  storage was provisioned for -- should not happen under normal use), it is
  the least-established, shortest-lived one(s) that get dropped rather than
  whichever happened to be processed first.
  """
  tracks = sorted(tracks, key=lambda tr: -(tr['entries'][-1][0] - tr['entries'][0][0] + 1))
  slotIntervals = [[] for _ in range(nbAnimalsPerWell)]
  assignment = []
  nbDropped = 0

  for tr in tracks:
    start, end = tr['entries'][0][0], tr['entries'][-1][0]
    placed = False
    for slot in range(nbAnimalsPerWell):
      if all(end < s or start > e for (s, e) in slotIntervals[slot]):
        slotIntervals[slot].append((start, end))
        assignment.append((slot, tr))
        diag.detail(lambda slot=slot, start=start, end=end:
                    f"STAGE5 PLACE slot={slot} frames=[{start:06d},{end:06d}] "
                    f"start={_fmtPos(tr['entries'][0][1])} end={_fmtPos(tr['entries'][-1][1])}")
        placed = True
        break
    if not placed:
      nbDropped += 1
      diag.summary(f"[synthesizeTracksFromDetectionCloud] well {numWell}: trajectory over frames "
                   f"[{start}, {end}] dropped -- more concurrently-alive fish than nbAnimalsPerWell "
                   f"({nbAnimalsPerWell}) output slots")

  diag.summary(f"[synthesizeTracksFromDetectionCloud] well {numWell}: Stage 5 (slot packing) kept "
               f"{len(assignment)} trajectory(ies), dropped {nbDropped} for lack of a free slot.")

  return assignment


# ============================================================================
# Public entry point
# ============================================================================

def synthesizeTracksFromDetectionCloud(videoName, numWell, nbAnimalsPerWell,
                                        startTimeInSeconds=None, endTimeInSeconds=None,
                                        clusterDistanceThreshold=30,
                                        splitAmbiguousClusters=True,
                                        gatingMahalanobisThreshold=9.21,
                                        measurementNoiseBase=25.0,
                                        measurementConfidenceFloor=0.5,
                                        maxGatingCovariance=300.0,
                                        maxGapForReacquisitionFallback=2,
                                        processNoiseScale=1.0,
                                        minHitsToConfirm=3,
                                        maxMissesTentative=1,
                                        maxFramesToCoast=10,
                                        maxReacquisitionDistance=60,
                                        maxPlausibleSpeed=15,
                                        maxConsecutiveWeakMatches=3,
                                        maxGapFramesForStitching=40,
                                        collisionPruneDistance=8,
                                        collisionPruneMinFrames=5,
                                        minSegmentLength=3,
                                        minNetDisplacement=10,
                                        minMeanConfidenceForReal=0.15,
                                        minAverageSpeed=0.11,
                                        verbose=True,
                                        diagnosisMode=True,
                                        diagnosisLogPath=None):
  """
  Post-processing step meant to be run once, at the very end of the
  pipeline, on the raw YOLO detection + HybridSORT slot output for the whole
  video -- as a REPLACEMENT for calling mergeSameTracks then
  smoothMergedTracksAndRemoveImmobileTracks.

  THE PROBLEM
  ------------
  yolo11MinConf is typically set very low (around 0.01), so at any given
  time there are usually several (3 to 6) overlapping YOLO detections on
  every real fish, not just one. HybridSORT has to turn that into a
  temporal id for each detection, and with that many near-duplicate boxes
  competing every frame it inevitably spawns more live track ids than there
  are real fish. Those extra ids still need somewhere to go, so
  nbAnimalsPerWell (the number of slots actually stored) is set higher than
  the true number of fish on purpose, to give the clutter somewhere to live
  without immediately evicting a genuine track. But HybridSORT's slot
  assignment is causal and greedy: it can and does occasionally starve a
  genuinely-detected fish of every slot for a while, which no amount of
  merging/stitching after the fact can fix once the position was never
  written down anywhere.

  THE APPROACH
  -------------
  This function ignores HybridSORT's slot identities entirely and rebuilds
  trajectories from scratch, in five stages:

  STAGE 1 -- online Kalman tracking (_buildTrackletsOnline).
  Every frame, the raw points across ALL nbAnimalsPerWell stored slots are
  declustered (points within clusterDistanceThreshold of one another are
  averaged into one denoised detection -- this is what recovers the
  "abundance of points" the storage was over-provisioned to hold). Each
  track carries its own constant-velocity Kalman filter; the measurement
  noise fed into it for a given detection is inversely proportional to how
  many raw points were averaged into it (the more duplicate YOLO boxes
  agree, the more the filter trusts the measurement -- a direct, principled
  use of detection abundance, not just an averaging trick). Association
  happens in TWO priority passes, not one: PASS 1 lets every track that
  matched cleanly last frame ("confident") take first, exclusive pick of
  nearby clusters using only the strict motion-model (Mahalanobis) test,
  gated at gatingMahalanobisThreshold; PASS 2 then lets everyone still
  unmatched (coasting/uncertain tracks, plus any confident track that
  didn't find anything) compete for whatever clusters are left, now also
  allowed the plain-distance-to-last-confirmed-position fallback (a "WEAK"
  match, gated at maxReacquisitionDistance, which exists so a fish's sharp
  turn -- e.g. bouncing off a well wall -- doesn't cost it its track just
  because the constant-velocity model couldn't see it coming). The two-
  pass split matters because a single Hungarian pass over every track at
  once is vulnerable to a subtle failure: a track that's been coasting for
  a while has an inflated covariance, which makes almost ANY nearby
  detection look artificially "cheap" in raw Mahalanobis terms -- cheap
  enough, sometimes, to falsely outbid the fish's own confident,
  continuously-matching track for its own rightful detection. Giving
  confident tracks first, uncontested pick removes that failure mode
  entirely, regardless of the exact covariance numbers on any given frame.
  On top of that, a track that racks up more than maxConsecutiveWeakMatches
  WEAK matches in a row (necessarily all won in PASS 2) is killed on the
  spot instead of being allowed to keep chaining marginal detections
  indefinitely -- left unchecked, this is how a track that lost its real
  fish in a collision could otherwise hallucinate a smooth "trajectory" out
  of an unrelated string of coincidences. Newly spawned tracks start
  "tentative" and need minHitsToConfirm hits to become "confirmed";
  tentative tracks are abandoned after just maxMissesTentative misses
  (cheap, fast rejection of one-off noise), while confirmed tracks are
  given much more slack (maxFramesToCoast).
  Whenever two or more CONFIRMED tracks simultaneously predict a position
  inside the same cluster -- the signature of a crossing / close contact
  fusing several fish into one blob of raw points -- that cluster is
  provisionally re-split via a short k-means pass warm-started at the
  competing tracks' predicted positions (_splitCluster), so each track
  keeps following its own fish through the contact. When a cluster can't
  be resolved this way (most often because only ONE confirmed track is
  competing for it, so there's no second prior to split against), the
  Kalman update is position-only: the track's pre-contact heading is
  preserved through the whole contact instead of being corrupted by the
  fused blob's drifting average position, giving it a better chance of
  reclaiming the right fish once the contact ends.

  STAGE 2 -- offline global stitching (_stitchTrackletsGlobally).
  Stage 1 is causal by construction: at frame t it only knows the past. This
  stage runs once the whole video's tracklets exist, and can therefore use
  information a causal tracker never has access to -- what a tracklet was
  doing right before it disappeared AND what the tracklet that might
  continue it was doing right as it appeared. Every plausible
  (end-of-one-tracklet, start-of-another) pair within maxGapFramesForStitching
  frames of each other is scored by how well the FIRST tracklet's exit
  motion, extrapolated forward, predicts the second one's start (and vice
  versa, extrapolated backward) -- then the whole set of candidate pairs is
  resolved in one global optimum via the Hungarian algorithm, rather than a
  greedy walk that locks in its first acceptable choice. This recovers
  fish whose Stage-1 tracklet died for longer than maxFramesToCoast
  (a long occlusion, or an upstream nbAnimalsPerWell slot-starvation
  event) and reappeared under a new id. Only tracklets that (a) reached
  CONFIRMED status in Stage 1 and (b) ALREADY pass the same
  length/displacement realism test Stage 4 uses -- on their own, before any
  stitching -- are eligible to participate, so neither a chain of isolated
  noise detections nor a pair of independently-immobile false detections
  (two different pieces of debris, two reflections) can be stitched into a
  fake trajectory whose only "motion" is the interpolation between them.

  STAGE 3 -- collision pruning (_pruneCollidingTracks).
  A backstop against near-duplicate trajectories: real fish essentially
  never stay glued to within a few pixels of one another for many
  consecutive frames, so if two surviving trajectories stay within
  collisionPruneDistance of each other for at least collisionPruneMinFrames,
  one of them is almost certainly a ghost that drifted onto (or got
  reconnected onto, in Stage 2) territory another, better-established
  trajectory already owns. The trajectory with fewer Stage-1 STRONG hits is
  blanked out over that stretch -- raw duration is deliberately NOT used to
  decide, since a ghost can rack up a long apparent duration purely from
  weak/coasted matches.

  STAGE 4 -- fake-fish removal (_isRealFish + a confidence gate).
  Exactly the same start-vs-end displacement test used by
  smoothMergedTracksAndRemoveImmobileTracks: any trajectory shorter than
  minSegmentLength, or whose first and last position are closer than
  minNetDisplacement, is discarded as a static false detection (reflection,
  debris, or noise never properly rejected upstream). Run after Stages 2-3
  so a real fish whose track was fragmented, or partly blanked by collision
  pruning, isn't unfairly judged as several short pieces. When
  probabilityGoodDetection data is available for this video, a trajectory
  additionally has to average at least minMeanConfidenceForReal across every
  detection that built it -- a real fish is something YOLO was consistently
  fairly sure about, not just something that happened to move enough.

  STAGE 5 -- quality-prioritized slot packing (_assignTracksToSlots).
  Surviving trajectories are packed into the nbAnimalsPerWell output slots,
  longest/most-established trajectories first, so that if there is ever
  slot contention it's the least-established trajectory that loses out, not
  an arbitrary one.

  WHAT THIS FUNCTION DELIBERATELY DOES NOT DO
  ----------------------------------------------
  It does not try to be certain who's who across a crossing / close contact
  -- the cluster-splitting and position-only updates in Stage 1 usually keep
  identities correctly separated because they're anchored to each track's
  own motion history, but when they can't, an occasional identity swap is
  accepted as the cost of never letting a track vanish -- or worse, silently
  hallucinate its way onto a different fish -- outright.

  PARAMETERS
  ----------
  dataAPI : object exposing getDataPerTimeInterval / setDataPerTimeInterval
  videoName : str
  numWell : int
      Process one well per call (loop over wells outside this function).
  nbAnimalsPerWell : int
      Number of stored slots to read on input, and number of output slots
      to (re)write.
  startTimeInSeconds, endTimeInSeconds : same as in your dataAPI calls.
      Leave as None to process the full video.
  clusterDistanceThreshold : float, default 30
      Max distance (pixels), within a single frame, for two raw points to be
      considered duplicate detections of the same fish and averaged
      together. Also used, at a smaller scale, as the base positional
      tolerance in Stage 2's stitching cost.
  splitAmbiguousClusters : bool, default True
      Enable the k-means de-fusion of clusters simultaneously claimed by 2+
      confirmed tracks (see STAGE 1 above). Turn off to fall back to
      "closest track wins, the other coasts blind" during crossings.
  gatingMahalanobisThreshold : float, default 9.21
      Squared-Mahalanobis-distance gate for accepting a track-to-detection
      match in Stage 1 (9.21 is the chi-squared 99% quantile for 2 degrees
      of freedom, the standard choice for 2D position gating). Grows
      effectively less strict the longer a track has been coasting, since
      it's compared against a covariance that keeps growing during a gap.
  measurementNoiseBase : float, default 25.0
      Assumed variance (px^2) of a single raw YOLO point's position noise.
      A cluster's effective measurement noise fed to the Kalman filter is
      this divided by the number of raw points merged into it -- the
      variance of a mean of n iid samples is sigma^2 / n, so more duplicate
      detections directly buys a more precise position estimate.
  measurementConfidenceFloor : float, default 0.5
      Floor under (cluster weight * cluster mean confidence) before it's
      used to scale measurement noise down -- prevents a near-zero-
      confidence cluster's effective noise from growing without real limit.
      Raising it makes very-low-confidence clusters trusted LESS both for
      the Kalman update and, more importantly, for the matching gate: a
      cluster whose effective noise is allowed to balloon becomes
      artificially "cheap" to match for ANY nearby track in Mahalanobis
      terms, including one that rightfully belongs to a completely
      different, well-established track a real distance away. In one
      observed real case, a long-tracked fish missed a single frame and its
      own rightful, near-exact-position detection went unclaimed while it
      was instead matched, at a cost comfortably under gate, to an
      unrelated cluster 54px away purely because that cluster's confidence
      (0.03) let its effective noise balloon under a lower, more permissive
      floor. Lowering this back towards 0.1 restores the original, more
      permissive behavior if you find it's rejecting genuine reconnections
      to real, consistently low-confidence fish.
  maxGatingCovariance : float, default 300.0
      Ceiling (px^2) on the position covariance the matching GATE is ever
      allowed to trust -- independent of, and in addition to,
      measurementConfidenceFloor above. The Kalman UPDATE step still always
      uses the track's real, uncapped covariance (so the filter's own
      internal state is unaffected); only the accept/reject decision is
      capped. Without this, a track that's been coasting (missing) for a
      while has a covariance that keeps growing for as long as
      maxFramesToCoast allows, and growing covariance makes ANY nearby
      detection look progressively cheaper in Mahalanobis terms -- there is
      always some "last possible frame" before a track would die where its
      covariance is maximally inflated, and lowering maxFramesToCoast only
      moves where that frame is, it doesn't remove it. In one observed real
      case, a track coasting right up against maxFramesToCoast's limit had
      its covariance grow enough that a 92px jump to a low-confidence,
      unrelated cluster passed the gate on the very last frame before it
      would otherwise have died. Capping the covariance the gate can ever
      use keeps it meaningful throughout the whole coasting window rather
      than only near its start -- roughly, no reconnect farther than
      sqrt(gatingMahalanobisThreshold * (maxGatingCovariance +
      effective measurement noise)) away is ever accepted, however long the
      track has been coasting. BE CAUTIOUS LOWERING THIS: it caps how far a
      genuine reconnection can ever be trusted too, regardless of how
      slowly or briefly the fish was actually undetected -- if you find
      real fish failing to reconnect after a legitimate sharp turn or brief
      occlusion, raise this (or rely on maxReacquisitionDistance/
      maxPlausibleSpeed's separate, distance-based fallback instead).
  processNoiseScale : float, default 1.0
      Scales how much frame-to-frame velocity change the Kalman filter
      expects from a real fish; higher values track sharper turns at the
      cost of a noisier, less discriminating gate.
  minHitsToConfirm : int, default 3
      Consecutive matched frames a brand-new track needs before it's
      trusted as a real fish candidate and given the full occlusion
      patience below. Also used, doubled, as the bar for Stage 1's PASS 1
      priority pick (see the STAGE 1 description above): a track needs
      strongHits >= 2*minHitsToConfirm, not just zero misses last frame, to
      get PASS 1's exclusive first pick of nearby clusters. Zero misses
      alone doesn't distinguish a track with months of established evidence
      from one that reached 'confirmed' status two frames ago and has
      simply never had the chance to miss yet -- without this extra bar,
      such a brand-new track can win PASS 1's exclusive pick of a detection
      that rightfully belongs to an established track that merely missed
      the previous frame, forcing the established track onto a distant,
      wrong cluster in PASS 2 instead.
  maxMissesTentative : int, default 1
      An unconfirmed track is abandoned after this many consecutive misses.
  maxFramesToCoast : int, default 10
      Once confirmed, how many consecutive missed frames a track tolerates,
      coasting on its Kalman-predicted position, before Stage 1 gives up on
      it (not necessarily the end of the story -- see Stage 2). Deliberately
      kept well short of Stage 2's own maxGapFramesForStitching: every
      missed frame the track coasts through grows its Kalman covariance
      further, and growing covariance makes the Mahalanobis gate cheaper
      for ANY nearby detection, real or not (see maxPlausibleSpeed and
      measurementConfidenceFloor). Reconnecting a track that's been
      coasting for a long time is exactly the situation Stage 2 is built to
      handle carefully -- it looks at BOTH fragments' full, whole-trajectory
      evidence (confidence, quality, independent realism) rather than a
      single frame's now-heavily-inflated covariance -- so once a gap has
      gone on this long, it's deliberately handed off rather than let
      Stage 1 keep gambling on it. In observed real cases, a track that lost
      its detection legitimately coasted right up to this patience limit,
      by which point its covariance had grown enough that an unrelated,
      low-confidence detection tens to low-hundreds of pixels away became
      cheap enough to pass the strict motion-model gate at the very last
      possible frame, silently splicing two unrelated fragments into one
      fake, linearly-interpolated "trajectory" -- this kept happening even
      at the previous default of 15 (itself already lowered once from an
      original 25 for the same reason), which is why it's now lower still.
      Lowering this value shrinks how much any single track's covariance is
      ever allowed to inflate before Stage 1 defers the decision, without
      touching the gate math itself.
  maxReacquisitionDistance : float, default 60
      A second, motion-model-independent gate (pixels): a detection within
      this distance of a track's last CONFIRMED position is always an
      acceptable ("WEAK") match candidate even if it is far from where the
      constant-velocity filter currently predicts. This is what lets a
      track survive a real fish's sharp turn (e.g. bouncing off a well
      wall) in a single frame, instead of relying on Stage 2 to reconnect
      it later -- a fish can't teleport, even when its velocity estimate
      is momentarily wrong. See maxGapForReacquisitionFallback: this
      distance is flat and does NOT scale with how long the track has been
      missing, so it is only actually offered for the first few missed
      frames.
  maxGapForReacquisitionFallback : int, default 2
      How many consecutive missed frames a track may have before
      maxReacquisitionDistance's flat-radius fallback stops being offered
      to it (the ordinary, covariance-based Mahalanobis test -- see
      maxGatingCovariance -- still applies regardless). maxReacquisitionDistance
      is a FLAT radius that does not scale with gap length at all, unlike
      every other test in Stage 1; its own purpose, per its docstring, is
      recovering from a sharp turn in a SINGLE missed frame, not standing
      in for the motion model indefinitely. Left available for longer
      gaps, it becomes a second, gap-blind route to the same failure
      maxGatingCovariance exists to close: in one observed real case, a
      track that had genuinely lost its fish 6 frames earlier matched a
      completely unrelated, low-confidence cluster 58.5px away -- just
      inside the flat 60px radius -- through this fallback alone (its
      Mahalanobis-only cost was far over gate). Raise this if real fish
      making sharp turns after a slightly longer occlusion are losing
      their track; lower it (down to 0 to disable the fallback entirely,
      since gapSinceLastMatch is never less than 1) if still-implausible
      reconnections persist.
  maxPlausibleSpeed : float, default 15
      Hard cap (pixels/frame) on how fast a fish could plausibly be
      moving. No match -- strong or weak -- is ever accepted farther than
      maxReacquisitionDistance + maxPlausibleSpeed*(frames since that
      track's last real match), regardless of how cheap a long-coasting
      track's growing covariance has made the motion-model test look. This
      is what stops two different, genuinely stationary false detections
      (e.g. two separate pieces of debris) a modest distance apart from
      being silently merged into one track after enough coasting frames
      have inflated its uncertainty -- lower it if you know your fish
      can't move fast, raise it for a very fast-swimming species.
  maxConsecutiveWeakMatches : int, default 3
      How many WEAK matches (see maxReacquisitionDistance) a track may
      chain in a row before it's killed outright. Guards against a track
      that lost its real fish (most commonly in a collision, where only
      one track can win the fused cluster) silently hallucinating a smooth
      trajectory out of an unrelated string of marginal detections instead
      of admitting it's lost -- raise it to give sharp real turns more
      benefit of the doubt at the cost of tolerating longer drift chains.
  maxGapFramesForStitching : int, default 40
      Stage 2's own, larger patience: the max frame gap between one
      tracklet ending and another starting for them to be considered,
      offline, as the same fish reappearing rather than two different
      events.
  collisionPruneDistance : float, default 8
      Stage 3: max distance (pixels) between two surviving trajectories, at
      the same frame, for them to be considered "on top of one another"
      and therefore evidence that one of them is a ghost/duplicate rather
      than a second fish. Deliberately tight: two DISTINCT real fish in
      genuine, prolonged close contact (not a duplicate) can still end up
      staying within a similar distance of each other for a while, and
      this only exists as a backstop for near-exact overlap that Stage 1's
      two-pass assignment and Stage 2's quality-scaled stitching (the
      primary defenses -- see their docstrings) should already prevent
      from happening in the first place.
  collisionPruneMinFrames : int, default 5
      Stage 3: minimum number of CONSECUTIVE frames two trajectories must
      stay within collisionPruneDistance of each other before being
      trusted as a genuine duplicate rather than an ordinary brief crossing.
  minSegmentLength : int, default 3
      Trajectories shorter than this (in frames) are discarded outright.
  minNetDisplacement : float, default 10
      Straight-line distance (pixels) between a trajectory's first and last
      position, below which it's treated as a static false detection and
      discarded.
  minMeanConfidenceForReal : float, default 0.15
      Minimum average YOLO detection confidence (0-1) a trajectory's
      underlying detections must have, in addition to passing the
      length/displacement test, to be kept -- only enforced when this
      video has probabilityGoodDetection data (i.e. was tracked with
      addGoodDetectionProbability enabled); silently has no effect
      otherwise, since there is nothing to check. Also used, the same way,
      to decide which tracklets Stage 2 is allowed to stitch (see its
      docstring). This has been recalibrated twice against real, confirmed
      data, both times landing on the same picture: genuinely real,
      continuously-tracked fish had mean confidence as low as 0.18-0.20 in
      one video, while in another every trajectory the confidence gate
      needed to reject (confirmed by direct human review) sat at
      0.10-0.13, and every trajectory that should stay sat at 0.18 or
      above -- a clean gap with nothing in between. 0.15 sits in the
      middle of that gap. BE CAUTIOUS RAISING THIS FURTHER: real fish are
      not always detected with high confidence, and pushing this toward
      the 0.18-0.20 floor observed for genuine fish risks starting to
      discard them too. If you suspect this is still filtering out real
      fish (or letting through fakes) in your own videos, check the
      diagnosis log's STAGE4 lines (see diagnosisMode) for the actual
      meanConfidence values of both your accepted and your missing
      trajectories before changing this -- the right number is whatever
      sits between your own data's two clusters, which may not be 0.15.
  minAverageSpeed : float, default 0.11
      Second, duration-SCALED companion to minNetDisplacement (pixels/frame):
      the effective minimum displacement a trajectory must show becomes
      max(minNetDisplacement, minAverageSpeed * length). For short/typical
      trajectories this changes nothing (minAverageSpeed * length stays
      below minNetDisplacement); it only starts to matter for a trajectory
      spanning a large fraction of the whole video, where minNetDisplacement
      alone stops being a meaningful bar -- a persistently-redetected but
      genuinely static false detection (a reflection, a piece of debris)
      accumulates its own frame-to-frame jitter for hundreds of frames, and
      that jitter doesn't average to exactly zero, so it can drift past a
      flat pixel floor by chance alone over a long enough run. Confirmed
      real, continuously-tracked fish were observed sustaining roughly
      0.12-0.15 px/frame over full, ~300-frame trajectories; confirmed
      static false detections were observed at roughly 0.04-0.10 px/frame
      over similarly long trajectories -- including one that a still lower
      former default of this parameter (0.06) was, in hindsight, just
      barely still letting through. BE CAUTIOUS RAISING THIS FURTHER: the
      margin between the slowest observed real fish and the fastest
      observed static false detection is narrow (roughly 0.10-0.15
      px/frame), so this is inherently a best-effort, evidence-calibrated
      compromise rather than a clean separation -- if you still see a
      long-lived, genuinely static false detection surviving, check the
      diagnosis log's STAGE4 lines for its actual average speed
      (cumulativeRealDisplacement / length) before raising this further,
      and if you find real, very slow fish being rejected, lower it toward
      0.06 or 0. Set to 0 to disable and fall back to the flat floor alone.
  verbose : bool, default True
      Prints a summary of every stage's decisions, plus every individual
      drop, to stdout, so you can sanity-check results before trusting
      them blindly. Independent of diagnosisMode below: this controls what
      reaches your terminal, diagnosisMode controls what's written to disk
      (everything verbose prints always ALSO goes to the diagnosis file
      when diagnosisMode is on, regardless of this flag).
  diagnosisMode : bool, default True
      When enabled (the default), writes a far more detailed, line-by-line
      trace of the whole run to a text file -- see diagnosisLogPath -- than
      anything printed to stdout, however verbose. This is the tool for
      answering "why did the fish that used to be near (x, y) around frame
      N stop being tracked": search the file for that frame range and
      those coordinates and read the PREDICT/PASS1/PASS2/MISS/KILL lines
      (Stage 1, what the online tracker considered and rejected frame by
      frame), the STAGE2 ELIGIBILITY/CANDIDATE/ASSIGNMENT lines (whether a
      later reconnection was possible and why it was or wasn't made), and
      the STAGE3/STAGE4/STAGE5 lines (whether a recovered trajectory was
      subsequently discarded as a duplicate, a fake, or for lack of a free
      slot). For a long video this file can get large; if you already know
      roughly when the fish disappeared, pass a narrower
      startTimeInSeconds/endTimeInSeconds window covering just that period
      to keep the trace focused and the run fast. Set to False once you're
      done diagnosing a specific issue, to avoid the file-writing overhead
      on routine runs.
  diagnosisLogPath : str, optional
      Where to write the diagnosis file when diagnosisMode is on. Defaults
      to "<videoName without extension>_synthesizeDiagnosis_well<numWell>.log"
      next to your results file; the exact path is always printed at the
      start and end of the run.

  RETURNS
  -------
  The list of nbAnimalsPerWell (possibly all-zero) trajectories actually
  written back through dataAPI.setDataPerTimeInterval.
  """

  if nbAnimalsPerWell == 0:
    return []

  if diagnosisLogPath is None:
    # resolve the ACTUAL underlying .h5 results file path (videoName is often just a bare
    # video name, with the real file located via ZZoutput-folder lookup) so the diagnosis
    # log lands next to it rather than wherever the current working directory happens to be.
    try:
      from zebrazoom.dataAPI._openResultsFile import _findResultsFile
      base, _ext = os.path.splitext(_findResultsFile(videoName))
    except Exception:
      base, _ext = os.path.splitext(videoName)
    diagnosisLogPath = f"{base}_synthesizeDiagnosis_well{numWell}.log"
  diag = _Diagnostics(diagnosisMode, verbose, diagnosisLogPath)
  if diagnosisMode:
    print(f"[synthesizeTracksFromDetectionCloud] well {numWell}: writing diagnosis trace to "
          f"{diagnosisLogPath}")

  try:
    # ------------------------------------------------------------------
    # 0) retrieve every stored slot of this well: the raw, over-provisioned
    #    YOLO + HybridSORT output whose identities we are about to ignore.
    #    probabilityGoodDetection is optional (only present if the video was
    #    tracked with addGoodDetectionProbability enabled) -- if even one slot
    #    is missing it, confidence-aware behavior is disabled for the whole
    #    well and every stage below falls back to its confidence-independent
    #    behavior (a neutral, uniform trust in every detection).
    # ------------------------------------------------------------------
    rawSlots = []
    rawConfidence = []
    hasConfidence = True
    for numAnimal in range(nbAnimalsPerWell):
      data = dataAPI.getDataPerTimeInterval(videoName, numWell, numAnimal,
                                             startTimeInSeconds, endTimeInSeconds, "HeadPos")
      rawSlots.append(np.array(data, dtype=float))
      if hasConfidence:
        try:
          conf = dataAPI.getDataPerTimeInterval(videoName, numWell, numAnimal,
                                                 startTimeInSeconds, endTimeInSeconds,
                                                 "probabilityGoodDetection")
          rawConfidence.append(np.asarray(conf, dtype=float).reshape(-1))
        except ValueError:
          hasConfidence = False
    rawConfidence = rawConfidence if hasConfidence else None

    diag.summary(f"[synthesizeTracksFromDetectionCloud] well {numWell}: YOLO detection confidence data "
                 + ("found -- confidence-aware clustering/stitching/filtering is active."
                    if hasConfidence else
                    "NOT found (needs addGoodDetectionProbability enabled during tracking) -- "
                    "falling back to confidence-independent behavior everywhere."))

    nbFrames = rawSlots[0].shape[0]
    for numAnimal, data in enumerate(rawSlots):
      if data.shape[0] != nbFrames:
        raise ValueError(
            f"synthesizeTracksFromDetectionCloud: numAnimal={numAnimal} has {data.shape[0]} frames, "
            f"expected {nbFrames} like the other slots.")
    diag.summary(f"[synthesizeTracksFromDetectionCloud] well {numWell}: processing nbFrames={nbFrames}, "
                 f"nbAnimalsPerWell={nbAnimalsPerWell} (input slots read from stored HeadPos)")

    tracklets = _buildTrackletsOnline(rawSlots, rawConfidence, nbAnimalsPerWell, nbFrames,
                                       clusterDistanceThreshold, splitAmbiguousClusters,
                                       gatingMahalanobisThreshold, measurementNoiseBase, processNoiseScale,
                                       minHitsToConfirm, maxMissesTentative, maxFramesToCoast,
                                       maxReacquisitionDistance, maxPlausibleSpeed, maxConsecutiveWeakMatches,
                                       diag, numWell, measurementConfidenceFloor, maxGatingCovariance,
                                       maxGapForReacquisitionFallback)

    mergedTracks = _stitchTrackletsGlobally(tracklets, nbFrames, maxGapFramesForStitching,
                                             clusterDistanceThreshold, minSegmentLength, minNetDisplacement,
                                             minMeanConfidenceForReal, diag, numWell, minAverageSpeed)

    prunedTracks = _pruneCollidingTracks(mergedTracks, collisionPruneDistance,
                                          collisionPruneMinFrames, diag, numWell)

    realTracks = []
    for tr in prunedTracks:
      s, e = tr['entries'][0][0], tr['entries'][-1][0]
      start, end = tr['entries'][0][1], tr['entries'][-1][1]
      # 'confirmed' status is required in addition to the length/displacement test: it means
      # the trajectory accumulated minHitsToConfirm STRONG, motion-consistent hits at some
      # point, not just any run of matches. Without this, a short chain of coincidentally-
      # aligned weak/marginal matches between unrelated noise detections can rack up enough
      # net displacement by pure chance to pass the displacement test on its own.
      if tr.get('status') != 'confirmed':
        diag.detail(lambda s=s, e=e, start=start, end=end:
                    f"STAGE4 REJECT frames=[{s:06d},{e:06d}] start={_fmtPos(start)} end={_fmtPos(end)} "
                    f"reason=never_confirmed")
        continue
      length, cumDisp, nRuns, _ = _realFishStats(tr)
      if not _passesRealismTest(length, cumDisp, minSegmentLength, minNetDisplacement, minAverageSpeed):
        effectiveMinDisp = max(minNetDisplacement, minAverageSpeed * length)
        diag.detail(lambda s=s, e=e, start=start, end=end, length=length, cumDisp=cumDisp, nRuns=nRuns,
                    effectiveMinDisp=effectiveMinDisp:
                    f"STAGE4 REJECT frames=[{s:06d},{e:06d}] start={_fmtPos(start)} end={_fmtPos(end)} "
                    f"reason=too_short_or_immobile length={length}(min={minSegmentLength}) "
                    f"cumulativeRealDisplacement={cumDisp:.1f}(min={effectiveMinDisp:.1f}, "
                    f"flatFloor={minNetDisplacement}) realRuns={nRuns}")
        continue
      # confidence gate: a no-op (meanConfidence defaults to 1.0) when this video has no
      # probabilityGoodDetection data -- see minMeanConfidenceForReal's docstring.
      meanConfidence = tr['confidenceSum'] / tr['hits'] if tr.get('hits') else 1.0
      if meanConfidence < minMeanConfidenceForReal:
        diag.detail(lambda s=s, e=e, start=start, end=end, meanConfidence=meanConfidence:
                    f"STAGE4 REJECT frames=[{s:06d},{e:06d}] start={_fmtPos(start)} end={_fmtPos(end)} "
                    f"reason=low_confidence meanConfidence={meanConfidence:.2f}(min={minMeanConfidenceForReal})")
        continue
      diag.detail(lambda s=s, e=e, start=start, end=end, cumDisp=cumDisp:
                  f"STAGE4 ACCEPT frames=[{s:06d},{e:06d}] start={_fmtPos(start)} end={_fmtPos(end)} "
                  f"cumulativeRealDisplacement={cumDisp:.1f}")
      realTracks.append(tr)

    assignment = _assignTracksToSlots(realTracks, nbAnimalsPerWell, diag, numWell)

    output = [np.zeros((nbFrames, 2)) for _ in range(nbAnimalsPerWell)]
    for slot, tr in assignment:
      for entry in tr['entries']:
        output[slot][entry[0]] = entry[1]

    # ------------------------------------------------------------------
    # write everything back
    # ------------------------------------------------------------------
    for numAnimal in range(nbAnimalsPerWell):
      dataAPI.setDataPerTimeInterval(videoName, numWell, numAnimal,
                                      startTimeInSeconds, endTimeInSeconds, "HeadPos",
                                      output[numAnimal])

    return output
  finally:
    if diagnosisMode:
      print(f"[synthesizeTracksFromDetectionCloud] well {numWell}: diagnosis trace complete: "
            f"{diagnosisLogPath} ({diag.lineCount} lines)")
    diag.close()


# Example usage, once per well, REPLACING the mergeSameTracks +
# smoothMergedTracksAndRemoveImmobileTracks pair:
# for numWell in range(nbWells):
#     synthesizeTracksFromDetectionCloud(videoName, numWell, nbAnimalsPerWell)
