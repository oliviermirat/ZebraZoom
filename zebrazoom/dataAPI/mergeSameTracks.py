import numpy as np
import zebrazoom.dataAPI as dataAPI

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


def _computeSegmentLengths(validMask):
    """
    For every frame, returns the length (number of frames) of the maximal
    uninterrupted run of "valid" (not [0,0]) frames it belongs to (0 for
    invalid frames). Used only to decide, once two slots are found to be
    duplicates, which of the two has the longer/more established run of
    detections and should therefore be the one that is kept.
    """
    segLengths = np.zeros(len(validMask), dtype=int)
    for (start, end) in _findTrueRuns(validMask):
        segLengths[start:end] = end - start
    return segLengths


def mergeSameTracks(videoName, numWell, nbAnimalsPerWell,
                     startTimeInSeconds=None, endTimeInSeconds=None,
                     distanceThreshold=30, minDuplicateFrames=0,
                     verbose=True):
    """
    Post-processing step meant to be run once, at the very end of the
    pipeline, after YOLO detection + HybridSORT linkage are complete for
    the whole video.

    THE PROBLEM
    ------------
    YOLO sometimes fires two (or more) detections on the very same
    physical fish. HybridSORT then tracks each of those duplicate
    detections as if they were separate animals, so a single real fish
    ends up "cloned" across several of the nbAnimalsPerWell track slots
    for a while, until the duplicate detections stop appearing and the
    extra track(s) die out.

    THE APPROACH
    -------------
    For every PAIR of track slots, look for stretches of time where:
      - both slots have a valid (non [0,0]) position, AND
      - the two positions stay within `distanceThreshold` pixels of one
        another for at least `minDuplicateFrames` CONSECUTIVE frames.

    Such a stretch is strong evidence the two slots are duplicate
    detections of the same fish: two genuinely different, correctly
    tracked fish essentially never sit glued to within a few pixels of
    each other for many consecutive frames. A crossing/close-contact
    event between two real fish is brief and has a distance profile that
    dips and then rises again -- it does not stay tiny for a long run of
    frames. This is what makes the whole approach safe with respect to
    real crossings: it only acts when two tracks are suspiciously,
    persistently on top of one another, which a genuine pair of fish
    essentially never is.

    When such a stretch is found, only ONE of the two slots is kept
    (untouched) for that stretch, and the other is blanked to [0,0] for
    that stretch only. Which one is kept is decided by "seniority": the
    slot whose own uninterrupted run of detections is the longest is kept
    (it is presumably the more complete/reliable track, and keeping it
    maximizes how much of the final trajectory lives continuously in a
    single slot rather than jumping between slots).

    WHAT THIS FUNCTION DELIBERATELY DOES NOT DO
    ----------------------------------------------
    It never tries to decide "who's who" when two genuinely different fish
    cross paths or swim close together, and it never re-links or relabels
    tracks. It only ever removes data it is confident is a pure duplicate;
    everything HybridSORT produced for two distinct fish -- including any
    identity switch it might have made while they were close -- is left
    completely untouched. The function only reasons about raw pixel
    proximity, so it is entirely agnostic to (and can't interfere with)
    whatever identity assignment HybridSORT made.

    PARAMETERS
    ----------
    dataAPI : object exposing getDataPerTimeInterval / setDataPerTimeInterval
    videoName : str
    numWell : int
        Process one well per call (loop over wells outside this function
        if you have several -- see example below).
    nbAnimalsPerWell : int
        Number of track slots to consider (0 .. nbAnimalsPerWell - 1).
    startTimeInSeconds, endTimeInSeconds : same as in your dataAPI calls.
        Leave as None to process the full video.
    distanceThreshold : float, default 10
        Max distance (pixels) between two slots to be considered "on top
        of each other". MUST be tuned to your resolution/fish size: pick
        something clearly smaller than the gap you'd expect between two
        distinct, nearby fish, but generous enough to absorb the small
        jitter between two duplicate YOLO boxes on the same fish.
    minDuplicateFrames : int, default 5
        Minimum number of CONSECUTIVE frames the two positions must stay
        under distanceThreshold before being trusted as a duplicate.
        Raise it if you see false merges around genuine crossings; lower
        it if short-lived duplicates are being missed.
    verbose : bool, default True
        Prints every merge decision so you can sanity-check results
        before trusting them blindly. Keep this on for your first runs.

    RETURNS
    -------
    The list of (possibly modified) trajectories, one per numAnimal, in
    case you want to inspect/plot them -- they are also written back
    through dataAPI.setDataPerTimeInterval before returning.
    """

    # ------------------------------------------------------------------
    # 1) retrieve every track ("slot") of this well
    # ------------------------------------------------------------------
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
                f"mergeSameTracks: numAnimal={numAnimal} has {data.shape[0]} frames, "
                f"expected {nbFrames} like the other slots."
            )

    # ------------------------------------------------------------------
    # 2) validity mask + "how long is my own uninterrupted run" per slot
    # ------------------------------------------------------------------
    validMasks = []
    segmentLengths = []
    for data in dataForEachAnimal:
        valid = ~((data[:, 0] == 0) & (data[:, 1] == 0))
        validMasks.append(valid)
        segmentLengths.append(_computeSegmentLengths(valid))

    # ------------------------------------------------------------------
    # 3) test every pair of slots for sustained "glued together" stretches.
    #    Detection only: dataForEachAnimal is NOT modified here, so every
    #    pair is always tested against the ORIGINAL, untouched data,
    #    regardless of loop order.
    # ------------------------------------------------------------------
    toClear = []  # (slotToDrop, rangeStart, rangeEnd)

    for i in range(nbAnimalsPerWell):
        for j in range(i + 1, nbAnimalsPerWell):

            bothValid = validMasks[i] & validMasks[j]
            if not bothValid.any():
                continue  # these two slots never coexist

            diff = dataForEachAnimal[i] - dataForEachAnimal[j]
            dist = np.sqrt((diff ** 2).sum(axis=1))
            close = bothValid & (dist < distanceThreshold)

            for (rs, re) in _findTrueRuns(close):
                if re - rs < minDuplicateFrames:
                    continue  # too short: likely just a crossing / close contact

                lenI = segmentLengths[i][rs]
                lenJ = segmentLengths[j][rs]
                if lenI > lenJ or (lenI == lenJ and i < j):
                    keepSlot, dropSlot = i, j
                else:
                    keepSlot, dropSlot = j, i

                toClear.append((dropSlot, rs, re))

                if verbose:
                    print(f"[mergeSameTracks] well {numWell}: slots {i} & {j} look like the same "
                          f"fish over frames [{rs}, {re}) (mean dist={dist[rs:re].mean():.1f}px, "
                          f"{re - rs} frames) -> keeping slot {keepSlot}, clearing slot {dropSlot}")

    # ------------------------------------------------------------------
    # 4) apply every clearing decision now, after ALL pairs have been
    #    tested against the original data
    # ------------------------------------------------------------------
    for (slot, rs, re) in toClear:
        dataForEachAnimal[slot][rs:re] = 0

    if verbose:
        print(f"[mergeSameTracks] well {numWell}: {len(toClear)} duplicate stretch(es) resolved.")

    # ------------------------------------------------------------------
    # 5) write everything back
    # ------------------------------------------------------------------
    for numAnimal in range(nbAnimalsPerWell):
        dataAPI.setDataPerTimeInterval(videoName, numWell, numAnimal,
                                        startTimeInSeconds, endTimeInSeconds, "HeadPos",
                                        dataForEachAnimal[numAnimal])

    return dataForEachAnimal


# Example usage, once per well:
# for numWell in range(nbWells):
#     mergeSameTracks(videoName, numWell, nbAnimalsPerWell)