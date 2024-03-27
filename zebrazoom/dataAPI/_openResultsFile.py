import contextlib
import os

import h5py

from zebrazoom.code.paths import getDefaultZZoutputFolder


def _findResultsFile(videoName):
  if videoName.endswith('.h5'):
    videoName, _ = os.path.splitext(videoName)
  ZZoutputPath, videoName = os.path.split(os.path.normpath(videoName))
  if not ZZoutputPath:
    ZZoutputPath = getDefaultZZoutputFolder()
  resultsPath = os.path.join(ZZoutputPath, f'{videoName}.h5')
  if os.path.exists(resultsPath):  # exact match
    return resultsPath
  path = next(reversed(sorted(name for name in os.listdir(ZZoutputPath)
                              if os.path.splitext(name)[0][:-20] == videoName and name[-3::] == ".h5")), None)
  if path is None:
    raise ValueError(f'video {videoName} not found in the ZZoutput folder ({ZZoutputPath})')
  return os.path.join(ZZoutputPath, path)


@contextlib.contextmanager
def openResultsFile(videoName, mode):
  with h5py.File(_findResultsFile(videoName), mode) as results:
    yield results
