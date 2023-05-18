import os

import h5py
import numpy as np

from zebrazoom.code.paths import getDefaultZZoutputFolder


def getCurvaturePerTimeInterval(videoName: str, numWell: int, numAnimal: int, startTimeInSeconds: int, endTimeInSeconds: int) -> list[np.array]:
  ZZoutputPath = getDefaultZZoutputFolder()
  resultsPath = os.path.join(ZZoutputPath, f'{videoName}.h5')
  if not os.path.exists(resultsPath):
    raise ValueError(f'video {videoName} not found in the default ZZoutput folder ({ZZoutputPath})')
  with h5py.File(resultsPath) as results:
    if 'videoFPS' not in results.attrs:
      raise ValueError(f'videoFPS not found in the results, cannot convert seconds to frames')
    firstFrame = startTimeInSeconds * results.attrs['videoFPS']
    lastFrame = endTimeInSeconds * results.attrs['videoFPS']
    dataPath = f'dataForWell{numWell}/dataForAnimal{numAnimal}/dataPerFrame'
    if dataPath not in results:
      raise ValueError(f"data per frame for animal {numAnimal} in well {numWell} doesn't exist")
    dataGroup = results[dataPath]
    if 'curvature' in dataGroup:
     return [dataGroup['curvature'][column][firstFrame:lastFrame] for column in dataGroup['curvature'].attrs['columns']]
    return [] # TODO: implement curvature calculation
