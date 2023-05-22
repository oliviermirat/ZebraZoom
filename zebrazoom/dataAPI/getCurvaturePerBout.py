import os

import h5py
import numpy as np

from zebrazoom.code.paths import getDefaultZZoutputFolder
from ._storeCurvature import storeCurvature


def getCurvaturePerBout(videoName: str, numWell: int, numAnimal: int, numBout: int) -> list[np.array]:
  ZZoutputPath = getDefaultZZoutputFolder()
  resultsPath = os.path.join(ZZoutputPath, f'{videoName}.h5')
  if not os.path.exists(resultsPath):
    raise ValueError(f'video {videoName} not found in the default ZZoutput folder ({ZZoutputPath})')
  with h5py.File(resultsPath, 'r+') as results:
    boutPath = f'dataForWell{numWell}/dataForAnimal{numAnimal}/listOfBouts/bout{numBout}'
    if boutPath not in results:
      raise ValueError(f"bout {numBout} for animal {numAnimal} in well {numWell} doesn't exist")
    boutGroup = results[boutPath]
    firstFrame = results.attrs['firstFrame']
    start = boutGroup.attrs['BoutStart'] - firstFrame
    end = boutGroup.attrs['BoutEnd'] - firstFrame + 1
    dataGroup = results[f'dataForWell{numWell}/dataForAnimal{numAnimal}/dataPerFrame']
    if 'curvature' in dataGroup:
      return [dataGroup['curvature'][column][start:end] for column in dataGroup['curvature'].attrs['columns']]
    boutGroup = results[boutPath]
    return [data[start:end] for data in storeCurvature(results, dataGroup, results[f'dataForWell{numWell}/dataForAnimal{numAnimal}/listOfBouts'])]
