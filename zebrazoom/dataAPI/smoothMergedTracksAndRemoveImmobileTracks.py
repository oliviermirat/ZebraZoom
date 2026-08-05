import zebrazoom.dataAPI as dataAPI
import numpy as np

def _findTrueRuns(boolArray):
    """
    Returns every maximal run of consecutive True values in a 1D boolean
    array, as a list of (start, end) tuples with 'end' excluded (i.e.
    usable directly as boolArray[start:end]).
    """
    boolArray = np.asarray(boolArray)
    if boolArray.size == 0 or not boolArray.any():
        return []
    padded = np.concatenate(([False], boolArray, [False]))
    diff = np.diff(padded.astype(np.int8))
    starts = np.where(diff == 1)[0]
    ends = np.where(diff == -1)[0]
    return list(zip(starts.tolist(), ends.tolist()))


def _stitchSegments(stacked, numWell, maxGapToBridge, maxStitchDistance, verbose):
    """
    Collects every segment (maximal run of valid frames) across ALL slots,
    then greedily chains together any pair where a later segment starts
    shortly after (<= maxGapToBridge frames) an earlier one ends, at a
    nearby position (<= maxStitchDistance pixels) -- regardless of whether
    the two segments happen to live in the same slot (a brief dropout) or
    in different slots (the tracker assigned a new ID partway through).

    Chained segments are relabeled under the EARLIER segment's slot; any
    gap between them is linearly interpolated; the donor slot (when
    different) is cleared to [0,0] over that range so the data lives in
    exactly one place.
    """
    nbAnimalsPerWell, nbFrames, _ = stacked.shape

    segments = []
    for k in range(nbAnimalsPerWell):
        validK = ~((stacked[k, :, 0] == 0) & (stacked[k, :, 1] == 0))
        for (s, e) in _findTrueRuns(validK):
            segments.append({'slot': k, 'start': s, 'end': e})
    segments.sort(key=lambda seg: seg['start'])

    consumed = [False] * len(segments)
    nbStitches = 0

    for idx in range(len(segments)):
        if consumed[idx]:
            continue
        currentSlot = segments[idx]['slot']
        currentEnd = segments[idx]['end']

        while True:
            currentEndPos = stacked[currentSlot, currentEnd - 1, :]
            bestIdx, bestScore = None, None

            for idx2 in range(len(segments)):
                if consumed[idx2] or idx2 == idx:
                    continue
                seg2 = segments[idx2]
                if seg2['start'] < currentEnd:
                    continue  # only look forward in time -- overlaps are mergeSameTracks's job
                gap = seg2['start'] - currentEnd
                if gap > maxGapToBridge:
                    continue
                candidatePos = stacked[seg2['slot'], seg2['start'], :]
                dist = np.linalg.norm(candidatePos - currentEndPos)
                if dist > maxStitchDistance:
                    continue
                score = (dist, gap)
                if bestScore is None or score < bestScore:
                    bestScore, bestIdx = score, idx2

            if bestIdx is None:
                break  # chain ends here, no qualifying continuation found

            succ = segments[bestIdx]
            gap = succ['start'] - currentEnd

            if gap > 0:
                posBefore = currentEndPos
                posAfter = stacked[succ['slot'], succ['start'], :]
                for step, t in enumerate(range(currentEnd, succ['start']), start=1):
                    frac = step / (gap + 1)
                    stacked[currentSlot, t, :] = posBefore + frac * (posAfter - posBefore)

            stacked[currentSlot, succ['start']:succ['end'], :] = stacked[succ['slot'], succ['start']:succ['end'], :]
            if succ['slot'] != currentSlot:
                stacked[succ['slot'], succ['start']:succ['end'], :] = 0

            if verbose:
                gapMsg = f", bridging a {gap}-frame gap" if gap > 0 else " (no gap, immediate handoff)"
                sameSlotMsg = "same slot" if succ['slot'] == currentSlot else f"slot {succ['slot']} -> slot {currentSlot}"
                print(f"[smoothMergedTracksAndRemoveImmobileTracks] well {numWell}: "
                      f"stitched frames [{succ['start']}, {succ['end']}) onto the track ending at "
                      f"frame {currentEnd - 1} ({sameSlotMsg}{gapMsg}, handoff distance={bestScore[0]:.1f}px)")

            consumed[bestIdx] = True
            nbStitches += 1
            currentEnd = succ['end']

    if verbose:
        print(f"[smoothMergedTracksAndRemoveImmobileTracks] well {numWell}: {nbStitches} track segment(s) stitched together.")
    return stacked


def _removeImmobileOrShortSegments(stacked, numWell, minSegmentLength, minNetDisplacement, verbose):
    """
    Discards (sets to [0,0]) any segment shorter than minSegmentLength
    (not enough data to trust either way), and any longer segment whose
    straight-line distance between its FIRST and LAST valid position is
    under minNetDisplacement -- i.e. a track that never really got
    anywhere over its whole lifetime, even though it might have jittered
    around from frame to frame along the way. Using start-vs-end position
    instead of frame-to-frame speed means detection jitter cannot make a
    genuinely static false detection look "mobile".
    """
    nbAnimalsPerWell, nbFrames, _ = stacked.shape
    nbDiscarded = 0

    for k in range(nbAnimalsPerWell):
        validK = ~((stacked[k, :, 0] == 0) & (stacked[k, :, 1] == 0))
        for (s, e) in _findTrueRuns(validK):
            length = e - s

            if length < minSegmentLength:
                stacked[k, s:e, :] = 0
                nbDiscarded += 1
                if verbose:
                    print(f"[smoothMergedTracksAndRemoveImmobileTracks] well {numWell}: "
                          f"slot {k} frames [{s}, {e}) discarded (only {length} frame(s), too short to trust)")
                continue

            netDisplacement = np.linalg.norm(stacked[k, e - 1, :] - stacked[k, s, :])
            if netDisplacement < minNetDisplacement:
                stacked[k, s:e, :] = 0
                nbDiscarded += 1
                if verbose:
                    print(f"[smoothMergedTracksAndRemoveImmobileTracks] well {numWell}: "
                          f"slot {k} frames [{s}, {e}) discarded (immobile: start-to-end "
                          f"displacement={netDisplacement:.1f}px < {minNetDisplacement})")

    if verbose:
        print(f"[smoothMergedTracksAndRemoveImmobileTracks] well {numWell}: {nbDiscarded} immobile/too-short segment(s) removed.")
    return stacked


def smoothMergedTracksAndRemoveImmobileTracks(videoName, numWell, nbAnimalsPerWell,
                                               startTimeInSeconds=None, endTimeInSeconds=None,
                                               maxGapToBridge=3, maxStitchDistance=15,
                                               minSegmentLength=3, minNetDisplacement=10,
                                               verbose=True):
    """
    Second post-processing pass, meant to run right after mergeSameTracks
    (on the same well). Fixes two remaining issues:

      1) SPLIT IDENTITIES: a track is associated with ID1 up through frame
         n, and then -- for whatever reason (a brief dropout, or the
         tracker just assigning a new ID even with no gap at all) -- the
         very same fish continues on as ID2 starting at or shortly after
         frame n+1. This is detected by comparing every track segment's
         end to every OTHER segment's start (across ALL slots, including
         its own): if a segment begins within maxGapToBridge frames of
         another one ending, at a position within maxStitchDistance
         pixels of where that one left off, the two are chained into a
         single continuous track living in ONE slot (whichever segment
         started first), any gap between them is linearly interpolated,
         and the donor slot is cleared for that stretch. This also
         naturally covers plain short dropouts within a single slot, since
         that's just the special case where the two chained segments
         happen to already share the same slot.

      2) IMMOBILE FAKE TRACKS: since real fish never fully stop, a track
         segment whose position barely differs between its first and its
         LAST frame is almost certainly a static false-positive detection
         (reflection, debris, etc.), not a fish, and is cleared to [0,0].
         Comparing start vs. end (rather than frame-to-frame speed) means
         detection jitter can't make a static object look like it's
         moving. Segments shorter than minSegmentLength are cleared
         outright regardless, since there isn't enough data to trust them
         either way.

    Stitching runs FIRST so that a real fish whose track got split across
    an ID change or a short dropout is judged as ONE full-length segment
    by the immobility check, instead of being unfairly evaluated as
    several short fragments.

    PARAMETERS
    ----------
    dataAPI, videoName, numWell, nbAnimalsPerWell, startTimeInSeconds,
    endTimeInSeconds : same meaning as in mergeSameTracks.
    maxGapToBridge : int, default 3
        Longest gap (in frames) between the end of one segment and the
        start of the next that will still be considered for stitching
        (and linearly interpolated if used). Applies whether the two
        segments are in the same slot or different slots.
    maxStitchDistance : float, default 15
        Max distance (pixels) between where one segment ends and the next
        begins for them to be treated as the same fish. MUST be tuned to
        your setup -- generous enough to cover how far a fish could
        plausibly move in up to maxGapToBridge+1 frames, but well below
        the typical distance between two distinct, unrelated fish.
    minSegmentLength : int, default 3
        Segments shorter than this (in frames), after stitching, are
        discarded outright regardless of displacement.
    minNetDisplacement : float, default 10
        Straight-line distance (pixels) between a segment's first and
        last position, below which it's treated as a static false
        detection and discarded. MUST be tuned to your setup: look at the
        start-to-end displacement of a track you know is a real fish over
        a comparable duration, and set this comfortably below that.
    verbose : bool, default True
        Prints every stitch and every discard so you can sanity-check
        results.

    RETURNS
    -------
    The list of (possibly modified) trajectories, one per numAnimal.
    """

    dataForEachAnimal = []
    for numAnimal in range(nbAnimalsPerWell):
        data = dataAPI.getDataPerTimeInterval(videoName, numWell, numAnimal,
                                               startTimeInSeconds, endTimeInSeconds, "HeadPos")
        dataForEachAnimal.append(np.array(data, dtype=float))

    if nbAnimalsPerWell == 0:
        return dataForEachAnimal

    nbFrames = dataForEachAnimal[0].shape[0]
    for numAnimal, data in enumerate(dataForEachAnimal):
        if data.shape[0] != nbFrames:
            raise ValueError(
                f"smoothMergedTracksAndRemoveImmobileTracks: numAnimal={numAnimal} has "
                f"{data.shape[0]} frames, expected {nbFrames} like the other slots."
            )

    stacked = np.stack(dataForEachAnimal, axis=0)  # shape (nbAnimalsPerWell, nbFrames, 2)

    stacked = _stitchSegments(stacked, numWell, maxGapToBridge, maxStitchDistance, verbose)
    stacked = _removeImmobileOrShortSegments(stacked, numWell, minSegmentLength, minNetDisplacement, verbose)

    dataForEachAnimal = [stacked[k] for k in range(nbAnimalsPerWell)]

    for numAnimal in range(nbAnimalsPerWell):
        dataAPI.setDataPerTimeInterval(videoName, numWell, numAnimal,
                                        startTimeInSeconds, endTimeInSeconds, "HeadPos",
                                        dataForEachAnimal[numAnimal])

    return dataForEachAnimal


# Usage, once per well, right after mergeSameTracks:
# for numWell in range(nbWells):
#     mergeSameTracks(dataAPI, videoName, numWell, nbAnimalsPerWell)
#     smoothMergedTracksAndRemoveImmobileTracks(dataAPI, videoName, numWell, nbAnimalsPerWell)