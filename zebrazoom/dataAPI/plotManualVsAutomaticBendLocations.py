import numpy as np
import matplotlib.pyplot as plt

from ._openResultsFile import openResultsFile


def plotManualVsAutomaticBendLocations(videoName: str, numWell: int, numAnimal: int, numBout: int):
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
    
    manualBendDetect = dataGroup['manualBend'][start:end]
    manualBendDetect = [1 if manualBendDetect[i] else 0 for i in range(len(manualBendDetect))]
    
    autoBendDetect   = np.array([0 for i in range(len(dataGroup['manualBend'][start:end]))])
    for i in results['dataForWell0/dataForAnimal' + str(numAnimal) + '/listOfBouts/bout' + str(numBout) + '/Bend_Timing'][:]:
      if i < len(autoBendDetect):
        autoBendDetect[i] = 2
    
    plt.plot(manualBendDetect, label='Manual Bend Detect')
    plt.plot(autoBendDetect,   label='Automatic Bend Detect')
    
    plt.legend()
    
    plt.show()
    