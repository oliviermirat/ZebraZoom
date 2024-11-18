import numpy as np

from ._openResultsFile import openResultsFile


def setDataPerTimeInterval(videoName: str, numWell: int, numAnimal: int, startTimeInSeconds: float, endTimeInSeconds: float, parameterName: str, newValues: np.array):
  if endTimeInSeconds is not None and startTimeInSeconds is not None and startTimeInSeconds >= endTimeInSeconds:
    raise ValueError('end time must be larger than start time')
  with openResultsFile(videoName, 'a') as results:
    if not startTimeInSeconds and endTimeInSeconds is None:
      intervalStart = 0
      intervalEnd = results.attrs['lastFrame'] - results.attrs['firstFrame']
    else:
      if 'videoFPS' not in results.attrs:
        raise ValueError(f'videoFPS not found in the results, cannot convert seconds to frames')
      firstFrame = results.attrs['firstFrame']
      firstFrameInSeconds = firstFrame / results.attrs['videoFPS']
      if startTimeInSeconds == 0 and firstFrame == 1:
        # when running tracking on the whole video, firstFrame is 1, but from the user's perspective, startTimeInSeconds is 0
        startTimeInSeconds = firstFrameInSeconds
      lastFrameInSeconds = results.attrs['lastFrame'] / results.attrs['videoFPS']
      if startTimeInSeconds is None:
        startTimeInSeconds = firstFrameInSeconds
      if endTimeInSeconds is None:
        endTimeInSeconds = lastFrameInSeconds
      if startTimeInSeconds < firstFrameInSeconds or endTimeInSeconds > lastFrameInSeconds:
        raise ValueError(f'Tracking was performed from {firstFrameInSeconds}s to {lastFrameInSeconds}s, start and end times must be within this interval.')
      intervalStart = int(startTimeInSeconds * results.attrs['videoFPS']) - firstFrame
      intervalEnd = int(endTimeInSeconds * results.attrs['videoFPS']) - firstFrame
    dataGroup = results[f'dataForWell{numWell}/dataForAnimal{numAnimal}/dataPerFrame']
    if parameterName not in dataGroup:
      allParameters = ', '.join(dataGroup.keys())
      raise ValueError(f'Parameter "{parameterName}" not found in results. Available parameters: {allParameters}')
    dataset = dataGroup[parameterName]
    if parameterName == 'HeadPos':
      dataset[intervalStart:intervalEnd] = [(newValues[i, 0], newValues[i, 1]) for i in range(len(newValues))]
    else:
      dataset[intervalStart:intervalEnd] = newValues
