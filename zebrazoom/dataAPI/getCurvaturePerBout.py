import os

import h5py
import numpy as np

from zebrazoom.code.dataPostProcessing.perBoutOutput import calculateCurvature
from zebrazoom.code.getHyperparameters import getHyperparametersSimple
from zebrazoom.code.paths import getDefaultZZoutputFolder


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
    if 'curvature' in boutGroup:
      return list(boutGroup['curvature'])
    curvature = calculateCurvature(list(boutGroup['TailX_VideoReferential']), list(boutGroup['TailY_VideoReferential']), getHyperparametersSimple(dict(results['configurationFileUsed'].attrs)))
    curvature = list(np.flip(np.transpose(curvature), 0))
    data = np.empty(len(curvature[0]), dtype=[(f'Pos{idx}', float) for idx in range(1, len(curvature) + 1)])
    for idx, curvatureData in enumerate(curvature):
      data[f'Pos{idx + 1}'] = curvatureData
    boutGroup.create_dataset('curvature', data=data)
    return curvature
