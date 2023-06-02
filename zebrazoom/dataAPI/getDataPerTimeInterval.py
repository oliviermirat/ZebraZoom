import numpy as np

from ._openResultsFile import openResultsFile


def getDataPerTimeInterval(videoName: str, numWell: int, numAnimal: int, startTimeInSeconds: float, endTimeInSeconds: float, parameterName: str) -> np.array:
  if startTimeInSeconds >= endTimeInSeconds:
    raise ValueError('end time must be larger than start time')
  with openResultsFile(videoName, 'r') as results:
    firstFrame = results.attrs['firstFrame']
    firstFrameInSeconds = firstFrame / results.attrs['videoFPS']
    lastFrameInSeconds = results.attrs['lastFrame'] / results.attrs['videoFPS']
    if startTimeInSeconds < firstFrameInSeconds or endTimeInSeconds > lastFrameInSeconds:
      raise ValueError(f'Tracking was performed from {firstFrameInSeconds}s to {lastFrameInSeconds}s, start and end times must be within this interval.')
    if 'videoFPS' not in results.attrs:
      raise ValueError(f'videoFPS not found in the results, cannot convert seconds to frames')
    intervalStart = int(startTimeInSeconds * results.attrs['videoFPS']) - firstFrame
    intervalEnd = int(endTimeInSeconds * results.attrs['videoFPS']) - firstFrame
    dataGroup = results[f'dataForWell{numWell}/dataForAnimal{numAnimal}/dataPerFrame']
    if parameterName not in dataGroup:
      allParameters = ', '.join(dataGroup.keys())
      raise ValueError(f'Parameter "{parameterName}" not found in results. Available parameters: {allParameters}')
    dataset = dataGroup[parameterName]
    return np.array(dataset[intervalStart:intervalEnd]) if 'columns' not in dataset.attrs else np.column_stack([dataset[col][intervalStart:intervalEnd] for col in dataset.attrs['columns']])
