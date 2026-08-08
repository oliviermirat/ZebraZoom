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
| `maxFramesToCoast` | 10 | increase | decrease |
| `maxGatingCovariance` | 300.0 | increase | decrease |
| `maxReacquisitionDistance` | 60 | increase | decrease |
| `maxGapForReacquisitionFallback` | 2 | increase | decrease |
| `maxPlausibleSpeed` | 15 | increase | decrease |
| `maxConsecutiveWeakMatches` | 3 | increase | decrease |
| `maxGapFramesForStitching` | 40 | increase | decrease |
| `minSegmentLength` | 3 | decrease | increase |
| `minNetDisplacement` | 10 | decrease | increase |
| `minMeanConfidenceForReal` | 0.15 | decrease | increase |
| `measurementConfidenceFloor` | 0.5 | decrease (toward 0.1) | increase |
| `minAverageSpeed` | 0.11 | decrease (or 0) | increase |
| `collisionPruneDistance` / `collisionPruneMinFrames` | 8 / 5 | decrease | increase |
| `nbAnimalsPerWell` | — | increase (capacity, not a real/fake dial) | — |

Change one parameter at a time and re-check the diagnosis log — most of these interact, and moving several at once makes it much harder to tell which change actually helped.

<a name="falseNegatives"/>
<H2 CLASS="western">If real fish are going missing (too many false negatives)</H2>

**`nbAnimalsPerWell` too low.** This is checked first because it's the one hard capacity limit, not a balance to strike: if more real fish are alive at the same time than `nbAnimalsPerWell` provides slots for, the least-established ones are dropped in Stage 5 no matter how every other parameter is set (look for `dropped -- more concurrently-alive fish than nbAnimalsPerWell` in the log). Raise it if you ever see this line.

**A confirmed track keeps dying too early during genuine occlusions.**
- `maxFramesToCoast` (default 10): raise this if real fish routinely disappear behind something, or drop out of detection, for longer than ~10 frames and never get reconnected by Stage 2 either. Don't raise it carelessly, though — every extra frame a track coasts without a real detection makes its position estimate less certain, and past a point that uncertainty can let it latch onto a completely unrelated detection instead of dying cleanly (see the false-positives section). If your occlusions are genuinely long, prefer raising `maxGapFramesForStitching` instead (see below) and let Stage 2's more careful, whole-fragment comparison do the reconnecting.
- `maxGatingCovariance` (default 300.0): raise this if a track keeps dying (or getting rejected mid-reconnect) during occlusions that involve a real, substantial jump in position — e.g. a fast fish briefly lost behind an obstacle, reappearing well away from where it was last seen. This caps how much uncertainty the matching gate is ever allowed to trust (see the false-positives section for why it exists); raised too high, it stops doing its job, but raised a little it can recover a genuinely fast reconnection that the default was too conservative about.
- `maxGapFramesForStitching` (default 40): Stage 2's own, larger patience for reconnecting two fragments after Stage 1 has already given up. Raise this for videos with long real occlusions (a fish going behind an opaque object, a long stretch of poor lighting).

**A track never becomes "confirmed" at all, or gets abandoned immediately.**
- `minHitsToConfirm` (default 3): lower this if a real fish's detections are noisy enough that it rarely manages 3 clean hits in a row before something interrupts it.
- `maxMissesTentative` (default 1): raise this if brand-new (not-yet-confirmed) tracks are being abandoned after a single missed frame that a real fish legitimately has now and then.

**A track loses its detection during a sharp turn or a crossing.**
- `gatingMahalanobisThreshold` (default 9.21): raising this makes the frame-to-frame motion-model gate more forgiving of an unexpected jump. Only raise this a little at a time — it's the primary defense against wrong matches, and a value that's too loose defeats its own purpose.
- `maxReacquisitionDistance` (default 60): raise this if a fish making a sharp turn (e.g. bouncing off a well wall) is losing its track because the constant-velocity motion model couldn't predict the turn. This gate is independent of velocity, so it specifically helps with sudden direction changes.
- `maxGapForReacquisitionFallback` (default 2): raise this if a fish makes a sharp turn right as (or just after) it briefly drops out of detection for a couple of frames — `maxReacquisitionDistance`'s allowance above is only offered for this many consecutive missed frames before it stops applying (see the false-positives section for why). If your fish's sharp turns tend to coincide with a slightly longer dropout, raise this a little; otherwise leave it low, since it's a flat-radius check that doesn't get more careful with a longer gap the way every other test here does.
- `processNoiseScale` (default 1.0): raise this if your fish make frequent sharp turns in general — it tells the motion model to expect more frame-to-frame velocity change before treating it as suspicious.

**A trajectory is recovered but then discarded at the very end.**
- `minSegmentLength` (default 3): lower this if genuinely real fish are only ever glimpsed for a couple of frames (e.g. briefly at the edge of the frame) and are getting discarded purely for being short.
- `minNetDisplacement` (default 10): lower this if you have genuinely slow-moving or resting fish whose first and last recorded position are too close together to clear the bar. Check the `STAGE4 REJECT` log line for the actual `cumulativeRealDisplacement` value to see how close it came.
- `minMeanConfidenceForReal` (default 0.15, only active if the video has `probabilityGoodDetection` data): lower this if real, well-tracked fish are being discarded for low average confidence. **Be careful raising this one**: this has now been calibrated against two different videos' real, confirmed data, and both times a clean gap showed up between confirmed-fake and confirmed-real trajectories, but the exact location of that gap differs by video (one had fakes at 0.01-0.08 and real fish as low as 0.18-0.20; another had fakes at 0.10-0.13 and real fish at 0.18+). 0.15 is a reasonable default sitting below both observed real-fish floors, but it is not guaranteed to be right for your video. Check the log's `STAGE4` lines for the actual `meanConfidence` of your missing trajectory (and of your accepted trajectories) before changing this — the right number is wherever the gap sits in your own data.
- `measurementConfidenceFloor` (default 0.5): lower this (toward the more permissive 0.1) if a real fish with consistently very low detection confidence is failing to reconnect after a brief occlusion. This is a different mechanism from `minMeanConfidenceForReal` above — it governs the frame-to-frame Kalman matching cost, not the final accept/reject decision, and mainly matters for tracks trying to reconnect to a low-confidence cluster (see the false-positives section for why it defaults high).
- `minAverageSpeed` (default 0.11, pixels/frame): this one only matters for trajectories spanning a large fraction of the whole video. Lower it (or set it to 0 to disable it entirely) if you have a genuinely real fish that stays almost motionless for nearly the entire video and is being rejected as a result — check the log for its actual average speed (`cumulativeRealDisplacement` divided by trajectory length) to see how close it is to the threshold.

<a name="falsePositives"/>
<H2 CLASS="western">If you're seeing fake/ghost fish (too many false positives)</H2>

**A static false detection (reflection, debris, sensor artifact) survives to the final output.**
- `minNetDisplacement` (default 10): raise this if static objects are clearing the displacement bar. Check the log's `STAGE4 ACCEPT` line for the false trajectory's actual `cumulativeRealDisplacement` to see how much headroom to add.
- `minAverageSpeed` (default 0.11): raise this specifically if the fake trajectory spans a large fraction of the video and drifts *just* past `minNetDisplacement` through accumulated jitter rather than real motion — a persistently-redetected static object's own frame-to-frame noise doesn't average to exactly zero, so over hundreds of frames it can slip past a flat pixel threshold even though its *average speed* is nowhere near a real fish's. This parameter scales the displacement requirement with trajectory length precisely to catch that pattern without penalizing short trajectories.
- `minMeanConfidenceForReal` (default 0.15, needs `probabilityGoodDetection` data): raise this if fake detections are getting through with low but nonzero confidence. This is usually the most effective single lever for a *confidently, coherently* fake detection — one that moves smoothly enough, and consistently enough, that no motion- or displacement-based check catches it, but that YOLO itself was never very sure about. See the caution above about calibrating it from your own data rather than guessing.
- `minSegmentLength` (default 3): raise this if brief one-off noise blips are surviving purely by chance.

Note one hard limit here: if a false detection is confidently, coherently, and continuously tracked — smooth motion, no implausible jumps, and *not* particularly low confidence — no combination of these parameters can separate it from a real fish. The tracker is correctly following what it was given; the ambiguity is in what YOLO detected, not in how it was tracked. If you keep seeing the same fake object at consistent pixel locations across multiple videos or re-runs, that's a sign the fix belongs upstream (in the detector) or in a position-based exclusion list, not in this function's thresholds.

**Two unrelated fragments get spliced into one fake "trajectory" (a straight-line "teleport" between two unrelated positions).**
This has two distinct causes with two distinct fixes — check which one your log shows before picking a parameter:
- `maxGatingCovariance` (default 300.0): lower this if the log shows a track coasting for several frames and then jumping to a distant, usually low-confidence cluster with a Mahalanobis cost that only just barely passed `gatingMahalanobisThreshold` (the `kind=STRONG` match right after several `MISS`/coasting frames in the Stage 1 trace). The longer a track coasts, the less certain its predicted position becomes, and past a point almost any nearby detection starts looking statistically "cheap" — even one that has nothing to do with the original fish. This is the primary defense against that: it caps how much uncertainty the matching gate is ever allowed to trust, so the gate stays meaningful for as long as the track keeps coasting, not just for the first few missed frames. Lowering `maxFramesToCoast` alone does **not** fully close this: there is always some "last possible frame" before a track would die where its covariance is most inflated, and shrinking the patience window just moves where that frame is rather than removing it.
- `maxGapForReacquisitionFallback` (default 2): lower this (down to 0 to disable the fallback outside the same frame) if the log shows the same kind of bad jump, but through a match explicitly logged as `kind=WEAK`, with a `staticFallbackCost` under gate while the plain Mahalanobis cost is far over it. `maxReacquisitionDistance`'s allowance is a **flat radius that does not scale with how long the track has been missing** — unlike every other test in this function — so left unrestricted it becomes a second, gap-blind way for an unrelated detection to be accepted, regardless of how implausible the elapsed time makes it. This parameter limits how many consecutive missed frames that flat-radius shortcut is still offered for.
- `measurementConfidenceFloor` (default 0.5): raise this if the wrongly-matched cluster in the log has very low confidence (its effective measurement noise is let out too far, making it "cheap" to match for any nearby track — including one that rightfully belongs to a different, well-established track). This is a broader lever than the two above: it affects every match in the video, not just long-gap reconnections, so change it in smaller steps and re-check.
- `maxFramesToCoast` (default 10): lower this as a *complementary* measure once the two levers above are already sensible for your video — it narrows the window during which a track is even allowed to attempt a long-gap reconnection at all, handing genuinely long occlusions off to Stage 2 instead (which evaluates both fragments' full evidence, not a single frame's uncertainty).
- `maxPlausibleSpeed` (default 15, pixels/frame): lower this if you know your fish species can't move faster than some particular speed. This is a hard physical cap independent of the motion model's own confidence — no reconnection is ever accepted that would require moving faster than this, regardless of how "cheap" the statistical test says it is.
- `maxReacquisitionDistance` (default 60): lower this if tracks are jumping to a wrong nearby detection via the position-only fallback gate, and the gap is already short (see `maxGapForReacquisitionFallback` above for the longer-gap version of this same failure).
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

A third pattern worth knowing: a fake "teleport" trajectory can come from two different places in the log, and they call for different fixes. Find the frame where the bad jump happened and look at its `kind`. If it says `kind=STRONG` and the match came after several consecutive `MISS` lines, the cause is covariance inflation during coasting — fix with `maxGatingCovariance` (or, secondarily, `maxFramesToCoast`). If it says `kind=WEAK` with a `staticFallbackCost` under gate but the plain Mahalanobis cost far over it, the cause is `maxReacquisitionDistance`'s flat, gap-blind radius — fix with `maxGapForReacquisitionFallback` instead. Lowering the wrong one of the two won't fix the bug and will just make ordinary reconnections stricter for no benefit.
