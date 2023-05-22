import os

import h5py
import numpy as np

from zebrazoom.code.paths import getDefaultZZoutputFolder
from ._storeCurvature import storeCurvature


def getCurvaturePerTimeInterval(videoName: str, numWell: int, numAnimal: int, startTimeInSeconds: int, endTimeInSeconds: int) -> list[np.array]:
  ZZoutputPath = getDefaultZZoutputFolder()
  resultsPath = os.path.join(ZZoutputPath, f'{videoName}.h5')
  if not os.path.exists(resultsPath):
    raise ValueError(f'video {videoName} not found in the default ZZoutput folder ({ZZoutputPath})')
  with h5py.File(resultsPath, 'r+') as results:
    if 'videoFPS' not in results.attrs:
      raise ValueError(f'videoFPS not found in the results, cannot convert seconds to frames')
    intervalStart = startTimeInSeconds * results.attrs['videoFPS']
    intervalEnd = endTimeInSeconds * results.attrs['videoFPS']
    dataGroup = results[f'dataForWell{numWell}/dataForAnimal{numAnimal}/dataPerFrame']
    if 'curvature' in dataGroup:
      return [dataGroup['curvature'][column][intervalStart:intervalEnd] for column in dataGroup['curvature'].attrs['columns']]
    return [data[intervalStart:intervalEnd] for data in storeCurvature(results, dataGroup, results[f'dataForWell{numWell}/dataForAnimal{numAnimal}/listOfBouts'])]
