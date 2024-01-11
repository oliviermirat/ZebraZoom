import numpy as np

from ._openResultsFile import openResultsFile


def getNumberOfOscillationsAndTBFPerBout(videoName: str, numWell: int, numAnimal: int, numBout: int):
  with openResultsFile(videoName, 'r') as results:
    if 'videoFPS' not in results.attrs:
      raise ValueError(f'videoFPS is not defined, cannot calculate tail beat frequency')
    boutPath     = f'dataForWell{numWell}/dataForAnimal{numAnimal}/listOfBouts/bout{numBout}'
    if boutPath not in results:
      raise ValueError(f"bout {numBout} for animal {numAnimal} in well {numWell} doesn't exist")
    boutGroup = results[boutPath]
    firstFrame = results.attrs['firstFrame']
    start = boutGroup.attrs['BoutStart'] - firstFrame
    end = boutGroup.attrs['BoutEnd'] - firstFrame + 1
    dataGroup = results[f'dataForWell{numWell}/dataForAnimal{numAnimal}/dataPerFrame']
    if 'manualBend' not in dataGroup:
      raise ValueError(f'Manual validation data not found for animal {numAnimal} in well {numWell}')
    numberOfOscillations = dataGroup['manualBend'][start:end].sum() / 2
    boutDuration = (end - start) / results.attrs['videoFPS']
    return numberOfOscillations, numberOfOscillations / boutDuration
