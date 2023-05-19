import os

import h5py
import numpy as np

from zebrazoom.code.dataPostProcessing.perBoutOutput import calculateCurvature
from zebrazoom.code.getHyperparameters import getHyperparametersSimple
from zebrazoom.code.paths import getDefaultZZoutputFolder


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
    hyperparameters = getHyperparametersSimple(dict(results['configurationFileUsed'].attrs))
    firstFrame = results.attrs['firstFrame']
    lastFrame = results.attrs['lastFrame']
    curvature = np.empty((lastFrame - firstFrame + 1, hyperparameters['nbTailPoints'] - 2), dtype=float)
    for boutGroup in results[f'dataForWell{numWell}/dataForAnimal{numAnimal}/listOfBouts'].values():
      start = boutGroup.attrs['BoutStart'] - firstFrame
      end = boutGroup.attrs['BoutEnd'] - firstFrame + 1
      curvature[start:end, :] = np.flip(np.transpose(calculateCurvature(list(boutGroup['TailX_VideoReferential']), list(boutGroup['TailY_VideoReferential']), hyperparameters)), 0).T
    curvature = list(curvature.T)
    data = np.empty(len(curvature[0]), dtype=[(f'Pos{idx}', float) for idx in range(1, len(curvature) + 1)])
    for idx, curvatureData in enumerate(curvature):
      data[f'Pos{idx + 1}'] = curvatureData
    dataGroup.create_dataset('curvature', data=data)
    return [curvatureData[intervalStart:intervalEnd] for curvatureData in curvature]
