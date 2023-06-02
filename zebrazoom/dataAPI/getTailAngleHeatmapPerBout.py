import numpy as np

from ._calculateAndStoreTailAngleHeatmap import calculateAndStoreTailAngleHeatmap
from ._openResultsFile import openResultsFile


def getTailAngleHeatmapPerBout(videoName: str, numWell: int, numAnimal: int, numBout: int) -> tuple:
  with openResultsFile(videoName, 'r+') as results:
    boutsPath = f'dataForWell{numWell}/dataForAnimal{numAnimal}/listOfBouts'
    if boutsPath not in results:
      raise ValueError(f"bouts not found for animal {numAnimal} in well {numWell}")
    boutsGroup = results[boutsPath]
    boutGroup = boutsGroup[f'bout{numBout}']
    firstFrame = results.attrs['firstFrame']
    start = boutGroup.attrs['BoutStart'] - firstFrame
    end = boutGroup.attrs['BoutEnd'] - firstFrame + 1
    dataGroup = results[f'dataForWell{numWell}/dataForAnimal{numAnimal}/dataPerFrame']
    if 'tailAngleHeatmap' in dataGroup:
      tailAngleHeatmap = dataGroup['tailAngleHeatmap']
    else:
      print(f'calculating and storing tail angle heatmap for all bouts for well {numWell}, animal {numAnimal}')
      tailAngleHeatmap = calculateAndStoreTailAngleHeatmap(results, dataGroup, boutsGroup)
    return [tailAngleHeatmap[col][start:end] for col in tailAngleHeatmap.dtype.names], boutGroup.attrs['BoutStart'], dataGroup['TailLength'][0]
