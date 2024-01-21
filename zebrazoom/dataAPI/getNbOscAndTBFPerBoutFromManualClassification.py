import numpy as np

from ._openResultsFile import openResultsFile


def getNbOscAndTBFPerBoutFromManualClassification(videoName: str, numWell: int, numAnimal: int, numBout: int):
  with openResultsFile(videoName, 'r') as results:
    
    # Retrieving bout data
    if 'videoFPS' not in results.attrs:
      raise ValueError(f'videoFPS is not defined, cannot calculate tail beat frequency')
    fps = results.attrs['videoFPS']
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
    
    # Extracting timings of bends
    Bend_Timing = []
    for i in range(start, end):
      if dataGroup['manualBend'][i]:
        Bend_Timing.append(i)
    if not(0 in Bend_Timing):
      Bend_Timing = [start] + Bend_Timing
    
    # Number of Oscillations calculation
    numberOfOscillations = dataGroup['manualBend'][start:end].sum() / 2
    
    # Quotient TBF calculation
    boutDuration = (end - start) / results.attrs['videoFPS']
    quotientTBF = numberOfOscillations / boutDuration
    
    # Instantaneous TBF calculation
    meanOfInstantaneousTBF = float('NaN')
    if len(Bend_Timing):
      meanOfInstantaneousTBF = np.mean(fps / (2 * np.diff(Bend_Timing)))
    
    return numberOfOscillations, quotientTBF, meanOfInstantaneousTBF
