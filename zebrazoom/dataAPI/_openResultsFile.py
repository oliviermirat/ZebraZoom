import contextlib
import os

import h5py

from zebrazoom.code.paths import getDefaultZZoutputFolder


def _findResultsFile(videoName):
  videoName, _ = os.path.splitext(videoName)
  if os.path.isabs(videoName):
    ZZoutputPath = os.path.dirname(videoName)
    videoName = os.path.basename(videoName)
  else:
    ZZoutputPath = getDefaultZZoutputFolder()
  resultsPath = os.path.join(ZZoutputPath, f'{videoName}.h5')
  if os.path.exists(resultsPath):  # exact match
    return resultsPath
  path = next(reversed(sorted(name for name in os.listdir(ZZoutputPath)
                              if os.path.splitext(name)[0][:-20] == videoName)), None)
  if path is None:
    raise ValueError(f'video {videoName} not found in the ZZoutput folder ({ZZoutputPath})')
  return os.path.join(ZZoutputPath, path)


@contextlib.contextmanager
def openResultsFile(videoName, mode):
  with h5py.File(_findResultsFile(videoName), mode) as results:
    yield results
