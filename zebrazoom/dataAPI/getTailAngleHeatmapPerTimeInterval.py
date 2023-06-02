import numpy as np

from ._calculateAndStoreTailAngleHeatmap import calculateAndStoreTailAngleHeatmap
from ._openResultsFile import openResultsFile


def getTailAngleHeatmapPerTimeInterval(videoName: str, numWell: int, numAnimal: int, startTimeInSeconds: int, endTimeInSeconds: int) -> tuple:
  with openResultsFile(videoName, 'r+') as results:
    if 'videoFPS' not in results.attrs:
      raise ValueError(f'videoFPS not found in the results, cannot convert seconds to frames')
    boutsPath = f'dataForWell{numWell}/dataForAnimal{numAnimal}/listOfBouts'
    if boutsPath not in results:
      raise ValueError(f"bouts not found for animal {numAnimal} in well {numWell}")
    boutsGroup = results[boutsPath]
    firstFrame = results.attrs['firstFrame']
    intervalStart = int(startTimeInSeconds * results.attrs['videoFPS']) - firstFrame
    intervalEnd = int(endTimeInSeconds * results.attrs['videoFPS']) - firstFrame
    dataGroup = results[f'dataForWell{numWell}/dataForAnimal{numAnimal}/dataPerFrame']
    if 'tailAngleHeatmap' in dataGroup:
      tailAngleHeatmap = dataGroup['tailAngleHeatmap']
    else:
      tailAngleHeatmap = calculateAndStoreTailAngleHeatmap(results, dataGroup, boutsGroup)
    return [tailAngleHeatmap[col][intervalStart:intervalEnd] for col in tailAngleHeatmap.dtype.names], int(startTimeInSeconds * results.attrs['videoFPS']), dataGroup['TailLength'][0]
