import h5py
import numpy as np
import pandas as pd
import pytest

pytest.importorskip('ortools')

import zebrazoom.dataAPI as dataAPI
from zebrazoom.dataAPI import _flowtrack
from zebrazoom.dataAPI.trackWithOrTools import _assignTracksToSlots

FRAME_SIZE = (1280, 720)


def _simulateDetections(nbFish=4, nbFrames=600, seed=0):
  """Synthetic YOLO output (adapted from the flowtrack demo): fish swimming along smooth paths that cross each
  other, with jittered boxes and missed detections, plus weak debris boxes. The 'fish' column is the truth (-1: debris)."""
  rng = np.random.default_rng(seed)
  width, height = FRAME_SIZE
  t = np.arange(nbFrames)
  rows = []
  for fish in range(nbFish):
    cx = width / 2 + 450 * np.sin(2 * np.pi * t / rng.uniform(600, 1000) + rng.uniform(0, 2 * np.pi))
    cy = height / 2 + 250 * np.sin(2 * np.pi * t / rng.uniform(500, 900) + rng.uniform(0, 2 * np.pi))
    length = rng.uniform(60, 100)
    for frame in t:
      if rng.random() < 0.05:  # missed detection
        continue
      x, y = cx[frame] + rng.normal(0, 2), cy[frame] + rng.normal(0, 2)
      rows.append((frame, x - length / 2, y - length / 8, x + length / 2, y + length / 8, rng.uniform(0.5, 0.95), fish))
  for frame in t:
    for _ in range(rng.poisson(2)):
      x, y = rng.uniform(0, width), rng.uniform(0, height)
      rows.append((frame, x - 15, y - 10, x + 15, y + 10, rng.uniform(0.01, 0.1), -1))
  return pd.DataFrame(rows, columns=['frame', 'x1', 'y1', 'x2', 'y2', 'score', 'fish'])


def _createResultsFile(path, nbFrames, nbAnimalsPerWell):
  """Minimal ZebraZoom results file, slots filled with junk that the OrTools post-processing must replace."""
  with h5py.File(path, 'w') as results:
    results.attrs['firstFrame'] = 1
    results.attrs['lastFrame'] = nbFrames
    for numAnimal in range(nbAnimalsPerWell):
      dataGroup = results.create_group(f'dataForWell0/dataForAnimal{numAnimal}/dataPerFrame')
      headPos = np.full(nbFrames, 999., dtype=[('X', float), ('Y', float)])
      dataGroup.create_dataset('HeadPos', data=headPos).attrs['columns'] = headPos.dtype.names
      dataGroup.create_dataset('probabilityGoodDetection', data=np.full(nbFrames, 0.3))


def test_tracker_recovers_synthetic_fish():
  detections = _simulateDetections()
  res = _flowtrack.track(detections, _flowtrack.FlowTrackConfig(frame_size=FRAME_SIZE, verbose=False))
  tracks = res.tracks
  assert tracks['track_id'].nunique() == 4  # one track per fish, none for the debris
  detected = tracks[tracks['det_index'] >= 0]
  truth = detections['fish'].to_numpy()[detected['det_index'].to_numpy()]
  # (track_id, id_segment) is the strict identity: each one must follow a single fish
  for _, fishes in pd.Series(truth).groupby([detected['track_id'].to_numpy(), detected['id_segment'].to_numpy()]):
    assert (fishes == fishes.mode()[0]).mean() > 0.95
  # nearly every box of every fish is used
  assert (truth >= 0).sum() > 0.95 * (detections['fish'] >= 0).sum()


def test_trackWithOrTools_rewrites_the_results_file(tmp_path):
  nbFrames, nbAnimalsPerWell = 600, 10
  path = str(tmp_path / 'video_2026_01_01-00_00_00.h5')
  _createResultsFile(path, nbFrames, nbAnimalsPerWell)
  detections = _simulateDetections(nbFrames=nbFrames)

  assert dataAPI.trackWithOrTools(path, 0, nbAnimalsPerWell, verbose=False) is None  # nothing recorded yet

  dataAPI.storeDetectionsForOrTools(path, 0, detections[['frame', 'x1', 'y1', 'x2', 'y2', 'score']].to_numpy(), FRAME_SIZE, 0.01, 0.8)
  with pytest.raises(ValueError):
    dataAPI.trackWithOrTools(path, 0, nbAnimalsPerWell, {'OrTools_level1_swap_margn': 1.}, verbose=False)
  configuration = {'OrTools': 1, 'OrTools_yolo_conf': 0.01, 'OrTools_level2_max_gap': 200, 'nbAnimalsPerWell': nbAnimalsPerWell}
  tracks = dataAPI.trackWithOrTools(path, 0, nbAnimalsPerWell, configuration, verbose=False)

  assert sorted(tracks['slot'].unique()) == [0, 1, 2, 3]
  with h5py.File(path, 'r') as results:
    headPos = [results[f'dataForWell0/dataForAnimal{numAnimal}/dataPerFrame/HeadPos'][:] for numAnimal in range(nbAnimalsPerWell)]
    probability = [results[f'dataForWell0/dataForAnimal{numAnimal}/dataPerFrame/probabilityGoodDetection'][:] for numAnimal in range(nbAnimalsPerWell)]
    assert len(results['OrToolsTracking/well0/tracks']) == len(tracks)
    assert 'links' in results['OrToolsTracking/well0']
  for numAnimal in range(4):  # every frame of the 4 fish is filled, including the last one
    assert (headPos[numAnimal]['X'] != 0).all() and (headPos[numAnimal]['X'] != 999).all()
    assert ((probability[numAnimal] >= 0) & (probability[numAnimal] <= 1)).all()
  for numAnimal in range(4, nbAnimalsPerWell):  # unused slots are emptied
    assert (headPos[numAnimal]['X'] == 0).all() and (headPos[numAnimal]['Y'] == 0).all() and (probability[numAnimal] == 0).all()
  rows = tracks[tracks['slot'] == 0]
  assert np.allclose(headPos[0]['X'][rows['frame']], (rows['x1'] + rows['x2']) / 2)


def test_trackWithOrToolsLevel1Only_writes_the_raw_lines(tmp_path):
  nbFrames, nbAnimalsPerWell = 600, 10
  path = str(tmp_path / 'video_2026_01_01-00_00_00.h5')
  _createResultsFile(path, nbFrames, nbAnimalsPerWell)
  detections = _simulateDetections(nbFrames=nbFrames)
  dataAPI.storeDetectionsForOrTools(path, 0, detections[['frame', 'x1', 'y1', 'x2', 'y2', 'score']].to_numpy(), FRAME_SIZE)

  # small windows: the lines must be chained from one level-1 window to the next
  lines = dataAPI.trackWithOrToolsLevel1Only(path, 0, nbAnimalsPerWell, {'OrTools_window': 200, 'OrTools_overlap': 40}, verbose=False)
  assert lines['track_id'].nunique() == 4  # one line per fish, none for the debris
  assert not lines.duplicated(['track_id', 'frame']).any()
  assert set(lines['source']) <= {'detected', 'shared'}  # raw lines only: nothing filled
  with h5py.File(path, 'r') as results:
    group = results['OrToolsTracking/well0']
    assert group.attrs['trackerMode'] == 'level1Only' and 'links' not in group
    headPos = [results[f'dataForWell0/dataForAnimal{numAnimal}/dataPerFrame/HeadPos'][:] for numAnimal in range(nbAnimalsPerWell)]
  for numAnimal in range(4):  # the frames where YOLO missed the fish (5%) are left empty
    assert (headPos[numAnimal]['X'] != 0).mean() > 0.9

  dataAPI.trackWithOrTools(path, 0, nbAnimalsPerWell, verbose=False)  # back to the full result
  with h5py.File(path, 'r') as results:
    assert results['OrToolsTracking/well0'].attrs['trackerMode'] == 'full' and 'links' in results['OrToolsTracking/well0']


def test_assignTracksToSlots_shares_slots_only_when_needed():
  tracks = pd.DataFrame({'track_id': [1, 1, 2, 2, 3, 3], 'frame': [0, 10, 20, 30, 0, 30]})
  assert _assignTracksToSlots(tracks, 3, 0, False) == {1: 0, 2: 1, 3: 2}
  assert _assignTracksToSlots(tracks, 2, 0, False) == {3: 0, 1: 1, 2: 1}  # longest first, 1 and 2 do not overlap
  assert _assignTracksToSlots(tracks, 1, 0, False) == {3: 0}
