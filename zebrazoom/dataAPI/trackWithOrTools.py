import json

import numpy as np
import pandas as pd

from ._openResultsFile import openResultsFile

__all__ = ['storeDetectionsForOrTools', 'trackWithOrTools', 'trackWithOrToolsLevel1Only']

# Everything specific to the OrTools post-processing lives in this top-level group of the results file,
# never inside dataForWell<N> (whose number of children is the number of animals per well).
_GROUP = 'OrToolsTracking'

# "OrTools_..." configuration keys used while recording the YOLO boxes (see yolov11basedTracking), not by the tracker
YOLO_PARAMETERS_DEFAULTS = {'OrTools_yolo_conf': 0.01, 'OrTools_yolo_iou': 0.8}


def storeDetectionsForOrTools(videoName, numWell, detections, frameSize, yoloConf=None, yoloIou=None):
  """
  Stores, in the results file, the YOLO boxes recorded during the tracking for the OrTools post-processing.

  detections : (nbBoxes, 6) array, one row per box: frame, x1, y1, x2, y2, score.
      frame is the index of the frame in the per-frame results (HeadPos, ...), the box is in pixels.
  frameSize : (width, height) of the video frames, in pixels.
  yoloConf, yoloIou : YOLO confidence threshold and NMS IoU used to obtain the boxes (stored for reference).
  """
  detections = np.asarray(detections, dtype=float).reshape(-1, 6)
  data = np.empty(len(detections), dtype=[('frame', np.int32)] + [(name, np.float32) for name in ('x1', 'y1', 'x2', 'y2', 'score')])
  for column, name in enumerate(data.dtype.names):
    data[name] = detections[:, column]
  with openResultsFile(videoName, 'a') as results:
    group = results.require_group(f'{_GROUP}/well{numWell}')
    for name in ('detections', 'tracks', 'links'):
      if name in group:
        del group[name]
    group.create_dataset('detections', data=data)
    group.attrs['frameWidth'], group.attrs['frameHeight'] = frameSize
    if yoloConf is not None:
      group.attrs['yoloConf'] = yoloConf
    if yoloIou is not None:
      group.attrs['yoloIou'] = yoloIou


def _flowTrackConfig(parameters, frameSize, verbose):
  """
  Tracker settings from the "OrTools_..." keys of a configuration file (all other keys are ignored):
    "OrTools_level1_swap_margin": 0.8  ->  level1.swap_margin = 0.8
    "OrTools_level2_max_gap": 200      ->  level2.max_gap = 200
    "OrTools_window": 3000             ->  window = 3000
  """
  from ._flowtrack import FlowTrackConfig

  settings = {}
  for key, value in parameters.items():
    if not key.startswith('OrTools_') or key in YOLO_PARAMETERS_DEFAULTS:
      continue
    name = key[len('OrTools_'):]
    group, _, subName = name.partition('_')
    if group in ('level1', 'level2', 'output'):
      settings.setdefault(group, {})[subName] = value
    else:
      settings[name] = value
  try:
    cfg = FlowTrackConfig.from_dict(settings)
  except KeyError as e:
    raise ValueError(f'Unknown OrTools parameter ({e.args[0]}), check the spelling of the "OrTools_..." keys of the configuration file') from e
  cfg.frame_size = frameSize
  cfg.verbose = verbose
  return cfg


def _assignTracksToSlots(tracks, nbAnimalsPerWell, numWell, verbose):
  """
  Returns {track_id: slot}. Each track gets its own slot when there are enough of them (tracks are numbered
  by order of first appearance, so track k goes to slot k-1). Otherwise, tracks that do not overlap in time
  share a slot, the longest tracks being placed first, and the tracks that still do not fit are dropped.
  """
  if tracks.empty:
    return {}
  spans = tracks.groupby('track_id')['frame'].agg(['min', 'max'])
  if len(spans) <= nbAnimalsPerWell:
    return {trackId: slot for slot, trackId in enumerate(spans.index)}
  slotIntervals = [[] for _ in range(nbAnimalsPerWell)]
  slotOfTrack = {}
  for trackId in (spans['max'] - spans['min']).sort_values(ascending=False, kind='stable').index:
    start, end = spans.at[trackId, 'min'], spans.at[trackId, 'max']
    for slot, intervals in enumerate(slotIntervals):
      if all(end < s or start > e for (s, e) in intervals):
        intervals.append((start, end))
        slotOfTrack[trackId] = slot
        break
  if verbose:
    print(f"[trackWithOrTools] well {numWell}: {len(spans)} tracks found for {nbAnimalsPerWell} slots (nbAnimalsPerWell): "
          f"tracks not overlapping in time share a slot, {len(spans) - len(slotOfTrack)} track(s) dropped for lack of a free slot")
  return slotOfTrack


def _toStructuredArray(table):
  """DataFrame -> numpy structured array that h5py can store (strings become fixed-length bytes)."""
  columns = []
  for name in table.columns:
    values = table[name].to_numpy()
    if values.dtype == object:
      values = values.astype(str).astype(np.bytes_)
    columns.append((name, values))
  data = np.empty(len(table), dtype=[(name, values.dtype) for name, values in columns])
  for name, values in columns:
    data[name] = values
  return data


def trackWithOrTools(videoName, numWell, nbAnimalsPerWell, parameters=None, verbose=True):
  """
  OrTools post-processing: rebuilds the trajectories of a well from ALL the YOLO boxes recorded during the
  tracking (configuration file: "OrTools": 1), with an offline minimum-cost flow tracker (Google OR-Tools)
  that looks at long stretches of the video at once, past and future frames alike. It ignores whatever was
  stored in the nbAnimalsPerWell slots during the tracking, and replaces it.

  1) Level 1 links the boxes into reliable pieces of trajectories ("tracklets"), cut wherever two fish touch.
  2) Level 2 joins the pieces into full tracks, using direction, speed, size and the length of the gap.
  3) Gaps between joined pieces are filled by following weak boxes, or interpolated if short.
  See OrToolsTrackingGuide.md for details and tuning.

  The tracks are written into the HeadPos of the nbAnimalsPerWell slots ([0, 0] where an animal is not
  tracked), together with probabilityGoodDetection when it exists (the score of the box used, 0 if none).
  The full tracker output is also stored in the results file, in the group OrToolsTracking/well<numWell>:
    tracks : one row per (frame, track): slot, box (x1, y1, x2, y2), score, source ("detected", "trail",
             "shared" or "interpolated"), det_index (row in "detections", -1 if interpolated), uncertain
             (row inside an ambiguous join: identity may have swapped there) and id_segment (increases after
             every ambiguous join: (slot, id_segment) is a strict identity)
    links  : every join between two pieces, with its margin (small margin = ambiguous join)
  e.g.: pd.DataFrame(h5py.File(resultsFile)['OrToolsTracking/well0/tracks'][:])

  This can be re-run on an existing results file with different parameters, without running YOLO again.

  PARAMETERS
  ----------
  videoName : str
  numWell : int
  nbAnimalsPerWell : int
      Number of output slots.
  parameters : dict, optional
      Tracker settings, with the same "OrTools_..." keys as in the configuration file (e.g.
      {"OrTools_level1_swap_margin": 0.8, "OrTools_level2_max_gap": 200}); other keys are ignored.
  verbose : bool, default True

  RETURNS
  -------
  The tracks DataFrame described above (None if no YOLO boxes were recorded for this well).
  """
  loaded = _readDetections(videoName, numWell)
  if loaded is None:
    return None
  detections, frameSize = loaded

  from ._flowtrack import track

  cfg = _flowTrackConfig(parameters or {}, frameSize, verbose)
  res = track(detections, cfg)
  return _writeTracks(videoName, numWell, nbAnimalsPerWell, cfg, res, res.links, 'full', verbose)


def trackWithOrToolsLevel1Only(videoName, numWell, nbAnimalsPerWell, parameters=None, verbose=True):
  """
  For experimentation: runs only the first part of the OrTools post-processing and writes its raw result, to look
  at what level 1 does on its own. The YOLO boxes recorded during the tracking are linked by level 1 (the min-cost
  flow that draws one line per fish through the boxes), and the lines are written as they come out of the solver:
  no cut where two fish touch, no level 2 (joining of the pieces), no gap filling, no final filtering. Each line
  goes into its own slot (a line may pass through a box shared with another line; frames where a line skipped a
  missed detection are left empty).

  Same arguments as trackWithOrTools (the "OrTools_level1_..." settings and "OrTools_window" / "OrTools_overlap"
  are the ones that matter here), same outputs: HeadPos (and probabilityGoodDetection) of the slots, and the table
  OrToolsTracking/well<numWell>/tracks (no "links" table). Running trackWithOrTools again on the same results file
  gives back the full result.
  """
  loaded = _readDetections(videoName, numWell)
  if loaded is None:
    return None
  detections, frameSize = loaded

  from ._flowtrack import track_level1_only

  cfg = _flowTrackConfig(parameters or {}, frameSize, verbose)
  res = track_level1_only(detections, cfg)
  return _writeTracks(videoName, numWell, nbAnimalsPerWell, cfg, res, None, 'level1Only', verbose)


def _readDetections(videoName, numWell):
  """(detections DataFrame, (frame width, frame height)) recorded for this well, or None (with a message)."""
  with openResultsFile(videoName, 'r') as results:
    if f'{_GROUP}/well{numWell}/detections' not in results:
      print(f"[trackWithOrTools] well {numWell}: no YOLO detections recorded for this well in the results file "
            f"(the tracking must be launched with \"OrTools\": 1 in the configuration file), nothing done.")
      return None
    group = results[f'{_GROUP}/well{numWell}']
    detections = pd.DataFrame(group['detections'][:])
    frameSize = (int(group.attrs['frameWidth']), int(group.attrs['frameHeight']))
  return detections, frameSize


def _writeTracks(videoName, numWell, nbAnimalsPerWell, cfg, res, links, mode, verbose):
  """Writes the tracks into the HeadPos (and probabilityGoodDetection) of the slots, and the tracks / links
  tables, settings and stats into OrToolsTracking/well<numWell>. Returns the tracks DataFrame (with its slots)."""
  tracks = res.tracks
  slotOfTrack = _assignTracksToSlots(tracks, nbAnimalsPerWell, numWell, verbose)
  for table in (tracks, links):
    if table is not None and 'track_id' in table.columns:  # (no columns at all when no box was recorded)
      table.insert(0, 'slot', table['track_id'].map(slotOfTrack).fillna(-1).astype(np.int64))
  tracksBySlot = dict(tuple(tracks.groupby('slot'))) if 'slot' in tracks.columns else {}

  with openResultsFile(videoName, 'a') as results:
    for numAnimal in range(nbAnimalsPerWell):
      dataGroup = results[f'dataForWell{numWell}/dataForAnimal{numAnimal}/dataPerFrame']
      headPos = dataGroup['HeadPos'][:]
      x, y, score = np.zeros(len(headPos)), np.zeros(len(headPos)), np.zeros(len(headPos))
      if numAnimal in tracksBySlot:
        rows = tracksBySlot[numAnimal]
        rows = rows[rows['frame'] < len(headPos)]
        frames = rows['frame'].to_numpy()
        x[frames] = (rows['x1'].to_numpy() + rows['x2'].to_numpy()) / 2
        y[frames] = (rows['y1'].to_numpy() + rows['y2'].to_numpy()) / 2
        score[frames] = rows['score'].fillna(0).to_numpy()
      headPos['X'], headPos['Y'] = x, y
      dataGroup['HeadPos'][...] = headPos
      if 'probabilityGoodDetection' in dataGroup:
        dataGroup['probabilityGoodDetection'][...] = score

    group = results[f'{_GROUP}/well{numWell}']
    for name in ('tracks', 'links'):  # the group always describes what HeadPos now contains
      if name in group:
        del group[name]
    for name, table in (('tracks', tracks), ('links', links)):
      if table is not None and len(table.columns):
        group.create_dataset(name, data=_toStructuredArray(table))
    group.attrs['trackerMode'] = mode
    group.attrs['trackerSettings'] = json.dumps(cfg.to_dict(), default=lambda value: value.item())  # .item(): numpy scalars
    group.attrs['trackerStats'] = json.dumps(res.stats)

  if verbose:
    nbSlots = len(set(slotOfTrack.values()))
    what = 'level-1 line(s)' if mode == 'level1Only' else 'track(s)'
    print(f"[trackWithOrTools] well {numWell}: {len(slotOfTrack)} {what} written into {nbSlots} slot(s).")
  return tracks
