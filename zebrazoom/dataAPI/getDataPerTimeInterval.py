import numpy as np

from ._openResultsFile import openResultsFile


def getDataPerTimeInterval(videoName: str, numWell: int, numAnimal: int, startTimeInSeconds: int, endTimeInSeconds: int, parameterName: str) -> np.array:
  with openResultsFile(videoName, 'r') as results:
    if 'videoFPS' not in results.attrs:
      raise ValueError(f'videoFPS not found in the results, cannot convert seconds to frames')
    firstFrame = results.attrs['firstFrame']
    intervalStart = int(startTimeInSeconds * results.attrs['videoFPS']) - firstFrame
    intervalEnd = int(endTimeInSeconds * results.attrs['videoFPS']) - firstFrame
    dataGroup = results[f'dataForWell{numWell}/dataForAnimal{numAnimal}/dataPerFrame']
    if parameterName not in dataGroup:
      allParameters = ', '.join(dataGroup.keys())
      raise ValueError(f'Parameter "{parameterName}" not found in results. Available parameters: {allParameters}')
    dataset = dataGroup[parameterName]
    return np.array(dataset[intervalStart:intervalEnd]) if 'columns' not in dataset.attrs else np.column_stack([dataset[col][intervalStart:intervalEnd] for col in dataset.attrs['columns']])
