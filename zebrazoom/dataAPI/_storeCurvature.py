import numpy as np

from zebrazoom.code.dataPostProcessing.perBoutOutput import calculateCurvature
from zebrazoom.code.getHyperparameters import getHyperparametersSimple


def storeCurvature(results, dataGroup, boutsGroup):
  hyperparameters = getHyperparametersSimple(dict(results['configurationFileUsed'].attrs))
  firstFrame = results.attrs['firstFrame']
  lastFrame = results.attrs['lastFrame']
  curvature = np.empty((lastFrame - firstFrame + 1, hyperparameters['nbTailPoints'] - 2), dtype=float)
  TailX_VideoReferential = np.column_stack([dataGroup['HeadPos']['X']] + [dataGroup['TailPosX'][col] for col in dataGroup['TailPosX'].attrs['columns']])
  TailY_VideoReferential = np.column_stack([dataGroup['HeadPos']['Y']] + [dataGroup['TailPosY'][col] for col in dataGroup['TailPosY'].attrs['columns']])
  for boutGroup in boutsGroup.values():
    start = boutGroup.attrs['BoutStart'] - firstFrame
    end = boutGroup.attrs['BoutEnd'] - firstFrame + 1
    curvature[start:end, :] = np.flip(np.transpose(calculateCurvature(TailX_VideoReferential[start:end, :], TailY_VideoReferential[start:end, :], hyperparameters)), 0).T
  curvature = list(curvature.T)
  data = np.empty(len(curvature[0]), dtype=[(f'Pos{idx}', float) for idx in range(1, len(curvature) + 1)])
  for idx, curvatureData in enumerate(curvature):
    data[f'Pos{idx + 1}'] = curvatureData
  dataGroup.create_dataset('curvature', data=data)
  return curvature
