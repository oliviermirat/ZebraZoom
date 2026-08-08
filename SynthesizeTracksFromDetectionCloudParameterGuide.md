<H1 CLASS="western" style="text-align:center;">Tuning synthesizeTracksFromDetectionCloud: A Practical Guide</H1>

`synthesizeTracksFromDetectionCloud` is the dataAPI post-processing step that turns raw, over-provisioned YOLO + HybridSORT detections into clean fish trajectories. It replaces the older `mergeSameTracks` + `smoothMergedTracksAndRemoveImmobileTracks` pair. Like any tracker, it has to balance two opposite kinds of mistakes:

- **False negatives**: a real fish goes missing — its track dies early, never gets confirmed, or gets thrown away at the end even though it was really there.
- **False positives**: a "fish" appears that isn't one — a reflection, a piece of debris, a duplicate/ghost detection, or two unrelated blips falsely stitched into one fake trajectory.

Almost every parameter in this function sits on a dial between these two failure modes: loosening it catches more real fish but lets more fakes through, tightening it rejects more fakes but risks losing real fish. This guide explains, parameter by parameter, which way each dial leans, and gives you a practical workflow for finding the right balance for your own videos.

<a name="tableofcontent"/>

<H2 CLASS="western">Table of content:</H2>

[Step 0: diagnose before you tune](#step0)<br/>
[Quick-reference table](#quickref)<br/>
[If real fish are going missing (too many false negatives)](#falseNegatives)<br/>
[If you're seeing fake/ghost fish (too many false positives)](#falsePositives)<br/>
[Parameters that are usually safe to leave alone](#safeToLeave)<br/>
[A step-by-step tuning workflow](#workflow)<br/>
[Worked example](#example)<br/>

<a name="step0"/>
<H2 CLASS="western">Step 0: diagnose before you tune</H2>

Before touching any parameter, turn on `diagnosisMode` (it's on by default) and look at the log file it writes next to your results (`<video>_synthesizeDiagnosis_well<N>.log`). Guessing which parameter to change from the final result alone is slow and unreliable — the log tells you exactly what happened and why:

- **A fish went missing**: search the log around the frame range and (x, y) position where it disappeared. The `PREDICT` / `PASS1` / `PASS2` / `MISS` / `KILL` lines (Stage 1) show whether it lost its match, and if so why (failed the motion gate? lost a competing assignment? ran out of coasting patience?). The `STAGE2 ELIGIBILITY` / `CANDIDATE` lines show whether a later reconnection was considered and why it was or wasn't made. The `STAGE4 REJECT` lines show whether a recovered trajectory was thrown away at the end, and for which exact reason (too short, too immobile, too low-confidence).
- **A fake fish appeared**: search the log for its approximate position and frame range. `STAGE4 ACCEPT` lines show the exact numbers (`cumulativeRealDisplacement`, `meanConfidence`) a trajectory was judged on — if a clearly-fake trajectory got accepted, these numbers tell you which threshold it's slipping through, precisely.

This matters because the fix is almost never "turn everything looser" or "turn everything stricter" — it's usually one specific parameter that's slightly miscalibrated for your video's detection quality, frame rate, or fish speed. The log tells you which one.

If you already know roughly when/where the issue happens, pass a narrower `startTimeInSeconds`/`endTimeInSeconds` window so the log stays small and fast to read.

<a name="quickref"/>
<H2 CLASS="western">Quick-reference table</H2>

| Parameter | Default | Loosen (→ fewer missed fish) | Tighten (→ fewer fake fish) |
|---|---|---|---|
| `gatingMahalanobisThreshold` | 9.21 | increase | decrease |
| `minHitsToConfirm` | 3 | decrease | increase |
| `maxMissesTentative` | 1 | increase | decrease |
| `maxFramesToCoast` | 15 | increase | decrease |
| `maxReacquisitionDistance` | 60 | increase | decrease |
| `maxPlausibleSpeed` | 15 | increase | decrease |
| `maxConsecutiveWeakMatches` | 3 | increase | decrease |
| `maxGapFramesForStitching` | 40 | increase | decrease |
| `minSegmentLength` | 3 | decrease | increase |
| `minNetDisplacement` | 10 | decrease | increase |
| `minMeanConfidenceForReal` | 0.1 | decrease | increase |
| `minAverageSpeed` | 0.06 | decrease (or 0) | increase |
| `collisionPruneDistance` / `collisionPruneMinFrames` | 8 / 5 | decrease | increase |
| `nbAnimalsPerWell` | — | increase (capacity, not a real/fake dial) | — |

Change one parameter at a time and re-check the diagnosis log — most of these interact, and moving several at once makes it much harder to tell which change actually helped.

<a name="falseNegatives"/>
<H2 CLASS="western">If real fish are going missing (too many false negatives)</H2>

**`nbAnimalsPerWell` too low.** This is checked first because it's the one hard capacity limit, not a balance to strike: if more real fish are alive at the same time than `nbAnimalsPerWell` provides slots for, the least-established ones are dropped in Stage 5 no matter how every other parameter is set (look for `dropped -- more concurrently-alive fish than nbAnimalsPerWell` in the log). Raise it if you ever see this line.

**A confirmed track keeps dying too early during genuine occlusions.**
- `maxFramesToCoast` (default 15): raise this if real fish routinely disappear behind something, or drop out of detection, for longer than ~15 frames and never get reconnected by Stage 2 either. Don't raise it carelessly, though — every extra frame a track coasts without a real detection makes its position estimate less certain, and past a point that uncertainty can let it latch onto a completely unrelated detection instead of dying cleanly (see the false-positives section). If your occlusions are genuinely long, prefer raising `maxGapFramesForStitching` instead (see below) and let Stage 2's more careful, whole-fragment comparison do the reconnecting.
- `maxGapFramesForStitching` (default 40): Stage 2's own, larger patience for reconnecting two fragments after Stage 1 has already given up. Raise this for videos with long real occlusions (a fish going behind an opaque object, a long stretch of poor lighting).

**A track never becomes "confirmed" at all, or gets abandoned immediately.**
- `minHitsToConfirm` (default 3): lower this if a real fish's detections are noisy enough that it rarely manages 3 clean hits in a row before something interrupts it.
- `maxMissesTentative` (default 1): raise this if brand-new (not-yet-confirmed) tracks are being abandoned after a single missed frame that a real fish legitimately has now and then.

**A track loses its detection during a sharp turn or a crossing.**
- `gatingMahalanobisThreshold` (default 9.21): raising this makes the frame-to-frame motion-model gate more forgiving of an unexpected jump. Only raise this a little at a time — it's the primary defense against wrong matches, and a value that's too loose defeats its own purpose.
- `maxReacquisitionDistance` (default 60): raise this if a fish making a sharp turn (e.g. bouncing off a well wall) is losing its track because the constant-velocity motion model couldn't predict the turn. This gate is independent of velocity, so it specifically helps with sudden direction changes.
- `processNoiseScale` (default 1.0): raise this if your fish make frequent sharp turns in general — it tells the motion model to expect more frame-to-frame velocity change before treating it as suspicious.

**A trajectory is recovered but then discarded at the very end.**
- `minSegmentLength` (default 3): lower this if genuinely real fish are only ever glimpsed for a couple of frames (e.g. briefly at the edge of the frame) and are getting discarded purely for being short.
- `minNetDisplacement` (default 10): lower this if you have genuinely slow-moving or resting fish whose first and last recorded position are too close together to clear the bar. Check the `STAGE4 REJECT` log line for the actual `cumulativeRealDisplacement` value to see how close it came.
- `minMeanConfidenceForReal` (default 0.1, only active if the video has `probabilityGoodDetection` data): lower this if real, well-tracked fish are being discarded for low average confidence. **Be careful raising this one**: in real observed data, genuinely real, continuously-tracked fish had mean detection confidence as low as 0.18-0.20, while clearly-fake trajectories clustered at 0.01-0.08 — there's a real gap around 0.08-0.18 and the safest value sits below it, not in the middle of the 0-1 range. Check the log's `STAGE4` lines for the actual `meanConfidence` of your missing trajectory before changing this.
- `minAverageSpeed` (default 0.06, pixels/frame): this one only matters for trajectories spanning a large fraction of the whole video. Lower it (or set it to 0 to disable it entirely) if you have a genuinely real fish that stays almost motionless for nearly the entire video and is being rejected as a result — check the log for its actual average speed (`cumulativeRealDisplacement` divided by trajectory length) to see how close it is to the threshold.

<a name="falsePositives"/>
<H2 CLASS="western">If you're seeing fake/ghost fish (too many false positives)</H2>

**A static false detection (reflection, debris, sensor artifact) survives to the final output.**
- `minNetDisplacement` (default 10): raise this if static objects are clearing the displacement bar. Check the log's `STAGE4 ACCEPT` line for the false trajectory's actual `cumulativeRealDisplacement` to see how much headroom to add.
- `minAverageSpeed` (default 0.06): raise this specifically if the fake trajectory spans a large fraction of the video and drifts *just* past `minNetDisplacement` through accumulated jitter rather than real motion — a persistently-redetected static object's own frame-to-frame noise doesn't average to exactly zero, so over hundreds of frames it can slip past a flat pixel threshold even though its *average speed* is nowhere near a real fish's. This parameter scales the displacement requirement with trajectory length precisely to catch that pattern without penalizing short trajectories.
- `minMeanConfidenceForReal` (default 0.1, needs `probabilityGoodDetection` data): raise this if fake detections are getting through with low but nonzero confidence. See the caution above about not raising it too far.
- `minSegmentLength` (default 3): raise this if brief one-off noise blips are surviving purely by chance.

**Two unrelated fragments get spliced into one fake "trajectory" (a straight-line "teleport" between two unrelated positions).**
- `maxFramesToCoast` (default 15): lower this if a track is reconnecting to an unrelated detection after coasting for a long time. The longer a track coasts without a real detection, the less certain its predicted position becomes, and past a point almost any nearby detection starts looking statistically "close enough" — even one that has nothing to do with the original fish. Lowering this shortens the window where that can happen; genuinely long real occlusions are then handled by Stage 2 instead, which looks at both fragments' full evidence rather than a single frame's inflated uncertainty.
- `maxPlausibleSpeed` (default 15, pixels/frame): lower this if you know your fish species can't move faster than some particular speed. This is a hard physical cap independent of the motion model's own confidence — no reconnection is ever accepted that would require moving faster than this, regardless of how "cheap" the statistical test says it is.
- `maxReacquisitionDistance` (default 60): lower this if tracks are jumping to a wrong nearby detection via the position-only fallback gate.
- `maxConsecutiveWeakMatches` (default 3): lower this if a track that lost its real fish (most often during a collision) is chaining together a string of marginal, unrelated detections into a fake smooth trajectory instead of being killed once it's clearly lost.
- `maxGapFramesForStitching` (default 40): lower this if Stage 2 is reconnecting two fragments that are genuinely too far apart in time to plausibly be the same fish.

**A duplicate/ghost trajectory sits right on top of a real one.**
- `collisionPruneDistance` and `collisionPruneMinFrames` (defaults 8, 5): lower these to catch ghost duplicates that stay a bit further apart, or for fewer consecutive frames, than the defaults require. Be careful: two genuinely *distinct* fish in prolonged close contact can also stay within a similar distance of each other for a while, so tightening this too aggressively can cause one of a genuinely crossing pair to be wrongly blanked out (a false negative in disguise).

**Two overlapping detections aren't being merged, so the same fish spawns extra clutter.**
- `clusterDistanceThreshold` (default 30): raise this if the same fish's several overlapping YOLO boxes aren't being merged into one clean detection. Be careful raising it too far, though — too large a radius can accidentally merge two *different*, nearby real fish into a single detection, which relies on `splitAmbiguousClusters` to pull them back apart during crossings.

<a name="safeToLeave"/>
<H2 CLASS="western">Parameters that are usually safe to leave alone</H2>

These affect quality generally rather than sitting directly on the false-positive/false-negative dial, and rarely need adjusting unless you have a specific, evidenced reason to (again, check the diagnosis log first):

- `splitAmbiguousClusters` (default True): keep this on unless you have a specific reason not to — it's what keeps identities correctly separated during crossings and close contacts.
- `measurementNoiseBase` (default 25.0): how much position noise a single raw YOLO point is assumed to have. Only worth touching if you have strong, independent evidence about your detector's actual pixel-level noise.
- `verbose` / `diagnosisMode` / `diagnosisLogPath`: these control logging, not tracking behavior. Leave `diagnosisMode` on while tuning (see Step 0); you can turn it off later for routine runs to save the file-writing overhead.

<a name="workflow"/>
<H2 CLASS="western">A step-by-step tuning workflow</H2>

1. Run once with the defaults and `diagnosisMode` on (the default).
2. Look at the actual output: are there fish you know should be there but aren't? Fish that shouldn't be there but are? If everything looks right, you're done.
3. For each problem fish, find it in the diagnosis log (search by approximate frame/position) and read the relevant `KILL` / `MISS` / `STAGE2` / `STAGE4` lines to find the *specific* reason it was lost or kept.
4. Change the ONE parameter that log evidence points to, in the direction indicated by the tables above. Move it a modest amount — most of these parameters interact, and a small change is easier to evaluate than a large one.
5. Re-run on the same (ideally short, narrowed-by-time) section of video and check the log again: did the specific problem you were fixing go away? Did anything else change that you didn't intend (a new false positive appearing where there wasn't one, another fish now missing)?
6. Repeat for the next problem. Once a full pass produces no more issues on your test section, run on the full video to confirm before considering it final.

<a name="example"/>
<H2 CLASS="western">Worked example</H2>

Suppose your diagnosis log shows a fish's track dying with `reason=patience_exceeded` after coasting for the full duration of `maxFramesToCoast`, and no Stage 2 reconnection happens afterward because the two fragments are just outside `maxGapFramesForStitching` of each other. That's a clean false-negative diagnosis: the fish was really there the whole time, but neither stage's patience was long enough to bridge the gap. Rather than blindly raising `maxFramesToCoast` (which risks the "coast-then-jump" false positive described above), the more targeted fix is usually to raise `maxGapFramesForStitching` a bit, since Stage 2's reconnection logic is specifically built to evaluate a long gap carefully using both fragments' whole-trajectory evidence rather than a single frame's uncertainty.

Conversely, if the log shows a `STAGE4 ACCEPT` line for a trajectory that spans almost the entire video with a `cumulativeRealDisplacement` only barely above `minNetDisplacement`, and dividing that displacement by the trajectory's length gives an implausibly slow average speed (well under what your slowest known real fish shows over a similar duration), that's a clean false-positive diagnosis pointing specifically at `minAverageSpeed` — not at `minNetDisplacement`, which would also penalize short, genuinely real trajectories that happen to be brief.
