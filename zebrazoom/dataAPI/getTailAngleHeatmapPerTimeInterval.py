import numpy as np

from ._calculateAndStoreTailAngleHeatmap import calculateAndStoreTailAngleHeatmap
from ._openResultsFile import openResultsFile


def getTailAngleHeatmapPerTimeInterval(videoName: str, numWell: int, numAnimal: int, startTimeInSeconds: float, endTimeInSeconds: float) -> tuple:
  if endTimeInSeconds is not None and startTimeInSeconds is not None and startTimeInSeconds >= endTimeInSeconds:
    raise ValueError('end time must be larger than start time')
  with openResultsFile(videoName, 'r+') as results:
    boutsPath = f'dataForWell{numWell}/dataForAnimal{numAnimal}/listOfBouts'
    if boutsPath not in results:
      raise ValueError(f"bouts not found for animal {numAnimal} in well {numWell}")
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
    boutsGroup = results[boutsPath]
    dataGroup = results[f'dataForWell{numWell}/dataForAnimal{numAnimal}/dataPerFrame']
    if 'tailAngleHeatmap' in dataGroup:
      tailAngleHeatmap = dataGroup['tailAngleHeatmap']
    else:
      print(f'calculating and storing tail angle heatmap for all bouts for well {numWell}, animal {numAnimal}')
      tailAngleHeatmap = calculateAndStoreTailAngleHeatmap(results, dataGroup, boutsGroup)
    return [tailAngleHeatmap[col][intervalStart:intervalEnd] for col in tailAngleHeatmap.dtype.names], int(startTimeInSeconds * results.attrs['videoFPS']), dataGroup['TailLength'][0]
