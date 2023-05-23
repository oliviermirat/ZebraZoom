import numpy as np

from zebrazoom.code.dataPostProcessing.perBoutOutput import calculateCurvature
from zebrazoom.code.getHyperparameters import getHyperparametersSimple


def calculateAndStoreCurvature(results, dataGroup):
  hyperparameters = getHyperparametersSimple(dict(results['configurationFileUsed'].attrs))
  firstFrame = results.attrs['firstFrame']
  lastFrame = results.attrs['lastFrame']
  curvature = np.empty((lastFrame - firstFrame + 1, hyperparameters['nbTailPoints'] - 2), dtype=float)
  TailX_VideoReferential = np.column_stack([dataGroup['HeadPos']['X']] + [dataGroup['TailPosX'][col] for col in dataGroup['TailPosX'].attrs['columns']])
  TailY_VideoReferential = np.column_stack([dataGroup['HeadPos']['Y']] + [dataGroup['TailPosY'][col] for col in dataGroup['TailPosY'].attrs['columns']])
  curvature = list(np.flip(np.transpose(calculateCurvature(TailX_VideoReferential, TailY_VideoReferential, hyperparameters)), 0))
  data = np.empty(len(curvature[0]), dtype=[(f'Pos{idx}', float) for idx in range(1, len(curvature) + 1)])
  for idx, curvatureData in enumerate(curvature):
    data[f'Pos{idx + 1}'] = curvatureData
  dataset = dataGroup.create_dataset('curvature', data=data)
  dataset.attrs['columns'] = data.dtype.names
  return curvature
