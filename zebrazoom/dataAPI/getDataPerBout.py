import numpy as np

from ._openResultsFile import openResultsFile


def getDataPerBout(videoName: str, numWell: int, numAnimal: int, numBout: int, parameterName: str) -> np.array:
  with openResultsFile(videoName, 'r') as results:
    boutPath = f'dataForWell{numWell}/dataForAnimal{numAnimal}/listOfBouts/bout{numBout}'
    perFramePath = f'dataForWell{numWell}/dataForAnimal{numAnimal}/dataPerFrame'
    if boutPath not in results:
      raise ValueError(f"bout {numBout} for animal {numAnimal} in well {numWell} doesn't exist")
    boutGroup = results[boutPath]
    firstFrame = results.attrs['firstFrame']
    start = boutGroup.attrs['BoutStart'] - firstFrame
    end = boutGroup.attrs['BoutEnd'] - firstFrame + 1
    dataGroup = results[perFramePath]
    if parameterName not in dataGroup:
      allParameters = ', '.join(dataGroup.keys())
      raise ValueError(f'Parameter "{parameterName}" not found in results. Available parameters: {allParameters}')
    dataset = dataGroup[parameterName]
    return np.array(dataset[start:end]) if 'columns' not in dataset.attrs else np.column_stack([dataset[col][start:end] for col in dataset.attrs['columns']])
