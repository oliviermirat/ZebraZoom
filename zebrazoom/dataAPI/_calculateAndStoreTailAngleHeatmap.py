import math

import numpy as np

from zebrazoom.code.extractParameters import calculateAngle, calculateTailAngle, smoothAllTailAngles
from zebrazoom.code.getHyperparameters import getHyperparametersSimple


def calculateAndStoreTailAngleHeatmap(results, dataGroup, boutsGroup):
  hyperparameters = getHyperparametersSimple(dict(results['configurationFileUsed'].attrs))
  firstFrame = results.attrs['firstFrame']
  lastFrame = results.attrs['lastFrame']
  pointsToTakeIntoAccountStart = 9 - int(hyperparameters["tailAnglesHeatMapNbPointsToTakeIntoAccount"])
  allAngles = None
  data = np.empty(lastFrame - firstFrame + 1, dtype=[(f'Pos{idx}', float) for idx in range(1, hyperparameters['nbTailPoints'] - 1)])
  data[:] = np.nan
  for bout in boutsGroup:
    boutGroup = boutsGroup[bout]
    start = boutGroup.attrs['BoutStart'] - firstFrame
    end = boutGroup.attrs['BoutEnd'] - firstFrame + 1

    if 'allTailAnglesSmoothed' not in boutsGroup[bout]:  # calculate all tail angles
      if allAngles is None:
        TailX_VideoReferential = np.column_stack([dataGroup['HeadPos']['X']] + [dataGroup['TailPosX'][col] for col in dataGroup['TailPosX'].attrs['columns']])
        TailY_VideoReferential = np.column_stack([dataGroup['HeadPos']['Y']] + [dataGroup['TailPosY'][col] for col in dataGroup['TailPosY'].attrs['columns']])
        Heading = np.array(dataGroup['Heading'])
        frames, points = TailX_VideoReferential.shape
        allAngles = np.zeros((frames, points))
        for i in range(frames):
          head = np.array([TailX_VideoReferential[i, 0], TailY_VideoReferential[i, 0]])
          for j in range(points):
            allAngles[i][j] = calculateTailAngle(calculateAngle(head, np.array([TailX_VideoReferential[i, j], TailY_VideoReferential[i, j]])), (Heading[i] + math.pi) % (2 * math.pi))

      allTailAngles, allTailAnglesSmoothed = smoothAllTailAngles(allAngles, hyperparameters, start, end - 1)
      boutGroup.create_dataset('allTailAngles', data=allTailAngles)
      boutGroup.create_dataset('allTailAnglesSmoothed', data=allTailAnglesSmoothed)
      tailAngles = list(allTailAnglesSmoothed)[pointsToTakeIntoAccountStart:]
    else:
      tailAngles = list(boutsGroup[bout]['allTailAnglesSmoothed'])[pointsToTakeIntoAccountStart:]

    for idx, tailAngle in enumerate(tailAngles):  # calculate tail angle heatmap
      if end - start == len(tailAngle):
        data[f'Pos{idx + 1}'][start:end] = [t * (180 / math.pi) for t in tailAngle]

  dataset = dataGroup.create_dataset('tailAngleHeatmap', data=data)
  dataset.attrs['columns'] = data.dtype.names
  return data
