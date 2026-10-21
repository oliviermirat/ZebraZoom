# OrTools post-processing: offline fish tracking with min-cost flow

`"OrTools": 1` turns on a post-processing of the YOLO detections (`yolov11basedTracking`) that links boxes into
trajectories **offline**, by looking at long stretches of the video at once (past *and* future frames), with the
min-cost flow solver of [Google OR-Tools](https://developers.google.com/optimization). It is meant to replace the
`centerOfMass_YOLO_hybridSORT` + `mergeSameTracks` + `smoothMergedTracksAndRemoveImmobileTracks` combination, which
is why these three options are normally set to 0 when `OrTools` is 1.

Nothing in this post-processing is deep learning: YOLO produces the boxes, everything after that is classic
optimisation. The code is in [`zebrazoom/dataAPI/trackWithOrTools.py`](zebrazoom/dataAPI/trackWithOrTools.py)
(integration into ZebraZoom) and [`zebrazoom/dataAPI/_flowtrack.py`](zebrazoom/dataAPI/_flowtrack.py) (the tracker,
with a comment for every parameter).

Configuration files without `"OrTools": 1` are not affected in any way.

## Install

```bash
pip install ortools
```

OR-Tools is only needed when `OrTools` is 1.

## Quick start

In your configuration file:

```json
  "OrTools": 1,
  "centerOfMass_YOLO_hybridSORT": 0,
  "mergeSameTracks": 0,
  "smoothMergedTracksAndRemoveImmobileTracks": 0,
  "storeH5": 1,
```

`storeH5` must be 1: the boxes and the results are stored in the `.h5` results file. Then launch the tracking as
usual. Two things happen:

1. **During the tracking**, YOLO is run with a low confidence threshold (`OrTools_yolo_conf`, default 0.01, replaces
   `yolo11MinConf`) and a relaxed NMS (`OrTools_yolo_iou`, default 0.8, so that two touching fish are less often merged
   into one box), and *every* box is recorded in the results file. The weak boxes matter: the tracker decides later
   which ones are fish.
2. **After the tracking**, `dataAPI.trackWithOrTools` links these boxes into tracks and writes them into the `HeadPos`
   of the `nbAnimalsPerWell` slots, replacing what was stored there during the tracking. It runs before every other
   dataAPI post-processing: anything else you enable (`smoothHeadPositionsWindow`, ...) applies to its output.

## How it works, in plain words

Think of every YOLO box as a **dot** on a timeline.

### Level 1 — connect the dots (min-cost flow over boxes)

Over a window of ~2000 frames, the solver draws one line per fish through the dots, choosing the combination of lines
with the lowest total cost:

* passing through a box earns a **reward** that grows with its score; boxes around `p_neutral` (0.2) are roughly
  free and weaker ones cost a little, so lines are not pulled onto long chains of debris, nor onto the extra, weaker
  boxes YOLO often fires on a fish that is already followed (a second "ghost" line along them would make the cutting
  below shred the real fish's line);
* moving from one box to the next **costs** more the further the jump (beyond a small free allowance that absorbs box
  jitter), and more if the box size or shape (heading) changes;
* skipping frames (missed detections) costs a little per frame;
* **two lines may share one box** (a merged box around two touching fish) at a small cost per frame;
* **starting a line** in open water is expensive and only allowed at a confident box (`p_entry`), which stops debris
  from becoming "fish"; starting/ending is cheap at the image border and at the video start/end.

The solver finds the exact best combination of lines for the whole window at once, so frames *after* a tangle
influence the decisions *inside* it.

Then the lines are **cut** where who-is-who is not reliable: at boxes shared by two fish, and at steps where two lines
could swap for almost no extra cost (`swap_margin`). Very short pieces between two cuts are dissolved, and the very weak
boxes at both ends of a piece are cut off (`trim_score`: a line that lost its fish often lingers on junk before
ending). What remains are trustworthy pieces called **tracklets**; the boxes of the cut regions are kept aside to
follow the trail later.

### Level 2 — join the pieces (min-cost flow over tracklets)

The same solver now works on tracklets. Joining the end of piece A to the start of piece B costs:

* **position**: push A forward in time along its direction, push B backward along its own; how far apart are they?
  (tolerance grows with the gap);
* **velocity**: do A and B move in the same direction at the same speed? This is what separates two fish that
  *cross*, where positions coincide;
* **size** (bigger fish stay bigger), measured by the box diagonal (`size_cue`), which stays close to the fish length
  when it turns, unlike the box area; and **box shape** (heading);
* a small cost per frame of gap.

Starting a new fish or ending one costs more, so pieces get joined across tangles and across disappearances of up to
`max_gap` = 300 frames. This is where identities are decided. A join is only made if it costs less than ending the
first piece plus starting the second one (`exit_cost` + `entry_cost`): raising these joins more pieces (fewer identity
breaks), while **lowering them refuses the joins across tangles**, and the fish then disappear during every tangle.

For every join, the tracker also computes a **margin**: how much more the best alternative would have cost (swapping
two fish, giving the piece to another fish, or not joining at all). A small margin means the choice was nearly a coin
flip: those joins are marked `ambiguous`. Joins across long gaps where the fish was not seen (`confident_gap`, 50
frames) are always ambiguous: re-identifying look-alike fish after a long absence is guesswork.

### Gap filling

Between two joined pieces, the tracker follows the trail of boxes through the tangle (the smoothest chain, same costs
as level 1), using the boxes not owned by another piece, including weak ones YOLO barely saw. Three rules keep the trail
on its own fish:

* a box that is a duplicate of a box of another piece in the same frame (lying inside it, `trail_max_containment`)
  belongs to a fish already followed and is not used;
* each box is followed by one trail only (`trail_exclusive`): the shortest gaps, the most reliable, are filled first,
  so two tracks never end up on the same fish while another fish is shown missing;
* the trail is not attracted by confident boxes (`trail_reward` 0), so it does not make detours onto other fish.

No point is ever allowed to "fly" (move fast, or slide across empty water). Your cavefish swim about 0.03 size per
frame on average (0.14 for 99% of frames), so:

* a trail step may not be faster than `fill_max_speed` (0.1 size per frame) nor jump over more than `fill_max_skip`
  (5) empty frames;
* a straight line (interpolation) is only drawn where the fish barely moved, at most `interp_max_speed` (0.06 size
  per frame) over gaps of up to `max_interp` (100) frames, and only where the point lies on a YOLO box of that frame
  (`interp_on_box`: typically the fish hidden under another fish), never in empty water;
* a final pass along every track (`max_fill_step`) removes any filled point still moving faster than 0.15 size per
  frame, and splits a track in two where its own boxes jump faster than a fish swims (`max_own_step`, 0.4 size per
  frame: a line that switched to a touching fish), so that no dot ever jumps;
* all these limits get the same small tolerance for box jitter (`fill_gate_slack`, 0.1 size).

A gap that cannot be filled this way is left empty: the fish is shown missing for those frames rather than wrongly
placed. Long gaps with no trail (a fish that was not visible) are left empty too.

Finally, tracks that never had a confident box (`p_confirm`) or have too few boxes (`min_detections`) are dropped:
that removes most debris, floating particles and rocks.

## Outputs

**`HeadPos` of each slot** (`dataForWell<N>/dataForAnimal<k>/dataPerFrame`): track k goes to slot k-1, tracks being
numbered by order of first appearance; `[0, 0]` where the slot has no fish. If there are more tracks than
`nbAnimalsPerWell` slots, tracks that do not overlap in time share a slot (longest first) and the ones that still do
not fit are dropped (a message says so: raise `nbAnimalsPerWell`). `probabilityGoodDetection`, when present, receives
the score of the box used (0 for interpolated positions).

**Group `OrToolsTracking/well<N>` of the results file**:

| dataset | content |
|---|---|
| `detections` | every recorded YOLO box: `frame`, `x1 y1 x2 y2` (pixels), `score` |
| `tracks` | one row per (frame, track): `slot`, `track_id`, `frame`, box, `score`, `source`, `det_index`, `uncertain`, `id_segment` |
| `links` | every join between two pieces: `slot`, `track_id`, `from_frame`, `to_frame`, `gap`, `cost`, `margin`, `ambiguous` |

`frame` is the row index in the per-frame datasets (`HeadPos`, ...). In `tracks`:

| column | meaning |
|---|---|
| `source` | `detected` (box of one of the fish's own pieces), `trail` (box followed through a tangle), `shared` (merged box, also used by another fish), `interpolated` |
| `det_index` | row of the box in `detections` (-1 if interpolated) |
| `uncertain` | the row lies inside an **ambiguous** join: position approximate, identity may have swapped here |
| `id_segment` | increases by 1 after every ambiguous join: use `(slot, id_segment)` as a strict identity if you cannot tolerate possible swaps |

The attributes `trackerSettings` and `trackerStats` of the group record the exact settings used and a summary of the
run. Reading the tables:

```python
import h5py
import pandas as pd

with h5py.File('ZZoutput/myVideo_2026_10_20-10_39_00.h5', 'r') as results:
  tracks = pd.DataFrame(results['OrToolsTracking/well0/tracks'][:])
  links = pd.DataFrame(results['OrToolsTracking/well0/links'][:])
print(links.sort_values('margin').head(20))  # the least certain decisions first
```

## Tuning without running YOLO again

The boxes are saved, so the tracker can be re-run on an existing results file in seconds to minutes, with different
settings, as often as needed:

```python
import zebrazoom.dataAPI as dataAPI

dataAPI.trackWithOrTools('myVideo_2026_10_20-10_39_00', 0, 200, {'OrTools_level1_swap_margin': 0.8,
                                                                  'OrTools_level2_max_gap': 200})
```

(arguments: results file name, well number, `nbAnimalsPerWell`, settings). Note that the other dataAPI
post-processing steps enabled in the configuration file are not re-run by this call.

### Looking at level 1 alone

To see what level 1 does by itself, run instead:

```python
dataAPI.trackWithOrToolsLevel1Only('myVideo_2026_10_20-10_39_00', 0, 200)
```

It writes into the slots the lines exactly as the level-1 solver draws them through the boxes: no cut where two
fish touch, no joining of pieces (level 2), no gap filling, no final filtering of the tracks. Each line gets its own
slot; a box that two lines pass through is marked `shared` in the `tracks` table; frames where a line jumped over a
missed detection are left empty. The same settings dictionary can be passed (only the `OrTools_level1_...` ones,
`OrTools_window` and `OrTools_overlap` matter). The attribute `trackerMode` of `OrToolsTracking/well<N>` says which
of the two functions wrote the current HeadPos ("level1Only" or "full"); running `trackWithOrTools` on the same file
gives back the full result.

Every tracker parameter can be set, in the configuration file or in that dictionary, with the key
`OrTools_<group>_<parameter>` (groups: `level1`, `level2`, `output`) or `OrTools_<parameter>` for `window`, `overlap`
and `cost_scale`, e.g. `"OrTools_level1_swap_margin": 0.8`, `"OrTools_output_p_confirm": 0.6`, `"OrTools_window": 3000`.
A misspelled `OrTools_...` key raises an error. The parameters, with their defaults and meaning, are listed at the top of
[`_flowtrack.py`](zebrazoom/dataAPI/_flowtrack.py).

Tune on a few hand-checked clips and change one thing at a time:

| Symptom | Try |
|---|---|
| fish with good YOLO boxes are not tracked, or two dots on one fish ("ghosts") | raise `OrTools_level1_p_neutral` (0.25–0.3) |
| points still "fly" | lower `OrTools_output_max_fill_step`, `OrTools_output_fill_max_speed`, `OrTools_output_interp_max_speed` |
| too many holes (fish shown missing during tangles), or faster animals | raise `OrTools_output_interp_max_speed` and `OrTools_output_fill_max_speed`, or set `OrTools_output_interp_on_box` to 0 |
| tracks split where fish really swim fast | raise `OrTools_output_max_own_step` |
| too many identity breaks (tracks ending and starting mid-video) | raise `OrTools_level2_entry_cost` / `OrTools_level2_exit_cost` |
| debris / particles become tracks | raise `OrTools_level1_p_entry` or `OrTools_output_p_confirm` |
| tracks get pulled onto debris | raise `OrTools_level1_p_neutral` (weak boxes cost more) |
| a fish's track breaks in the middle of a tangle | raise `OrTools_level1_entry_cost` / `OrTools_level1_exit_cost`, lower `OrTools_level1_share_cost` |
| a fish "jumps" onto a nearby box | raise `OrTools_level1_w_dist`, lower `OrTools_level1_max_speed` |
| two fish swap inside tangles (not flagged) | raise `OrTools_level1_swap_margin` (cut more, let level 2 decide) |
| too many tiny pieces / identities lost in long tangles | lower `OrTools_level1_swap_margin`, raise `OrTools_level1_min_tracklet` |
| wrong joins across long disappearances | lower `OrTools_level2_max_gap` or `OrTools_level2_max_speed`, raise `OrTools_level2_w_gap` |
| correct long joins are missed | raise `OrTools_level2_entry_cost` / `OrTools_level2_exit_cost`, raise `OrTools_level2_sigma_per_frame` |
| crossing fish swap | raise `OrTools_level2_w_vel`, lower `OrTools_level2_sigma_vel0` |
| fish of clearly different sizes swap | raise `OrTools_level2_w_size` |
| too many / too few ambiguity flags | change `OrTools_level2_ambiguity_margin` |
| too slow | raise `OrTools_yolo_conf` (needs a new tracking), lower `OrTools_window` |

Do **not** lower `OrTools_level2_entry_cost` / `OrTools_level2_exit_cost` to find more fish: it refuses the joins
across tangles (see level 2 above) and loses fish instead.

Distances are in **sizes** (size = √(box width × box height)), so the same settings work for near and far fish.
Frame-based settings (`max_skip`, `max_gap`, `damping`, `vel_frames`, `confident_gap`, `max_interp`,
`fill_max_skip`) and speeds (`fill_max_speed`, `interp_max_speed`, `max_fill_step`, `max_own_step`, in sizes per
frame) assume roughly 25–30 fps and slow fish like cavefish: scale them for another frame rate or faster animals.

The defaults were first tuned on synthetic data, then changed after testing on a real, crowded cavefish video (about
50 fish, frames 1–400 of DSCF0062, checked against hand annotations and by looking at the video): `level1.p_neutral`
0.1 → 0.2, `level1.trim_score` 0 → 0.1, `level2.entry_cost` / `exit_cost` 6 → 8, `size_cue` "area" → "diagonal", and
the gap-filling rules above (`trail_reward` 1 → 0, `trail_max_containment` 1 → 0.6, `trail_exclusive` off → on,
`fill_max_skip` 30 → 5, `max_interp` 30 → 100, and the new speed limits `fill_max_speed` 0.1, `interp_max_speed` 0.06,
`interp_on_box` on, `max_fill_step` 0.15, `max_own_step` 0.4, all off in the demo). On that video, compared with only
`p_neutral` 0.2: points sliding in a straight line across empty water 36 → 3 (the 3 left: one-frame gaps inside a
piece), longest straight-line slide 149 → 84 px (and now always slow, under other fish), fastest move between two
consecutive positions of a track 67 → 15 px per frame, pairs of tracks on top of each other 3.6 → 0.7 per frame,
distinct fish per frame 45 → 46, tracks starting or ending mid-video 29 → 22; the price: about 5% of the frames of
the tracks are left empty (fish shown missing during tangles, instead of wrongly placed). Setting the old values back gives exactly the
original flowtrack algorithm.

## Speed and memory

Level 1 is solved in windows (default 2000 frames, overlapping by 200); the pieces cut at window edges are re-joined
by level 2. Time and memory grow with the number of boxes per frame: with ~10 boxes per frame it tracks close to 1000
frames per second, on a crowded video it is much slower. For example, on a 1280×720 video with about 50 fish (176 boxes
per frame at `OrTools_yolo_conf` 0.01), 400 frames take about 20 s, i.e. about 15 minutes for a 10-minute video.
Raising `OrTools_yolo_conf` (e.g. 0.05, needs a new tracking) speeds it up, at the cost of the weakest boxes.

## Limitations

* If two look-alike fish stay merged or glued together for a long time, the pixels contain no information about who
  is who. The tracker then relies on size, shape and motion before/after, and **flags** the join instead of pretending
  to know: check `links` / `uncertain`.
* Positions inside tangles are approximate (weak or merged boxes).
* Level 1 only compares neighbouring boxes; direction is used in level 2.
* Like the other YOLO post-processing steps, it only rewrites `HeadPos` (and `probabilityGoodDetection`): other
  per-frame datasets computed during the tracking are left as they are.
