import numpy as np
import pandas as pd

from ._openResultsFile import openResultsFile


def createExcelFileWithRawData(videoName: str, numWell: int, numAnimal: int, startFrame: int, endFrame: int) -> dict:
  with openResultsFile(videoName, 'r+') as results:
        
    firstFrame = results.attrs['firstFrame']
    lastFrame = results.attrs['lastFrame']
    if startFrame < firstFrame or endFrame > lastFrame:
      raise ValueError(f"[{startFrame}, {endFrame}] is not a valid interval, tracking was run from frame {results.attrs['firstFrame']} to frame {results.attrs['lastFrame']}")
    animalPath = f'dataForWell{numWell}/dataForAnimal{numAnimal}'
    if animalPath not in results:
      raise ValueError(f"data for animal {numAnimal} in well {numWell} doesn't exist")
    if 'videoFPS' not in results.attrs:
      raise ValueError(f'videoFPS not found in the results, cannot calculate kinematic parameters')
    if 'videoPixelSize' not in results.attrs:
      raise ValueError(f'videoPixelSize not found in the results, cannot calculate kinematic parameters')

    dataGroup = results[animalPath]['dataPerFrame']
    boutData = {'AnimalNumber': numAnimal, 'BoutStart': startFrame, 'BoutEnd': endFrame}
    start = startFrame - firstFrame
    end = endFrame + 1 - firstFrame
    HeadPos = dataGroup['HeadPos'][start:end]
    TailPosX = dataGroup['TailPosX'][start:end]
    TailPosY = dataGroup['TailPosY'][start:end]
    boutData['HeadX'] = HeadPos['X']
    boutData['HeadY'] = HeadPos['Y']
    boutData['TailX_VideoReferential'] = np.column_stack([HeadPos['X']] + [TailPosX[col] for col in dataGroup['TailPosX'].attrs['columns']])
    boutData['TailY_VideoReferential'] = np.column_stack([HeadPos['Y']] + [TailPosY[col] for col in dataGroup['TailPosY'].attrs['columns']])
    boutData['TailAngle_Raw'] = dataGroup['TailAngle'][start:end]
    boutData['Heading'] = dataGroup['Heading'][start:end]
    
    ### Saving raw movement data in csv file
    if 'TailAngle_smoothed' in dataGroup:
      if not(len(dataGroup["TailAngle_smoothed"].shape)) or not(type(dataGroup["TailAngle_smoothed"][0]) == np.float):
        del dataGroup["TailAngle_smoothed"]
        dataGroup.create_dataset("TailAngle_smoothed", (len(dataGroup['HeadPos']),), dtype=float)
    else:
      dataGroup.create_dataset("TailAngle_smoothed", (len(dataGroup['HeadPos']),), dtype=float)
    dataGroup["TailAngle_smoothed"][:] = 0
    for numBout in range(results[animalPath]['listOfBouts'].attrs["numberOfBouts"]):
      BoutStart = results[animalPath]['listOfBouts']['bout'+str(numBout)].attrs["BoutStart"]
      BoutEnd   = results[animalPath]['listOfBouts']['bout'+str(numBout)].attrs["BoutEnd"]
      if ((BoutStart <= startFrame) and (startFrame <= BoutEnd)) or ((BoutStart <= endFrame) and (endFrame <= BoutEnd)):
        dataGroup['TailAngle_smoothed'][BoutStart-1:BoutEnd] = results[animalPath]['listOfBouts']['bout'+str(numBout)]['TailAngle_smoothed'][:]
    # Getting tail length
    tailLength = []
    for i in range(len(TailPosX)):
      tailLength.append(np.sum(np.sqrt(np.diff([val for val in TailPosX[i]])**2 + np.diff([val for val in TailPosY[i]])**2)))
    tailLength = np.array(tailLength)
    # Getting subsequent points distance
    subsequentPointsDistance = np.array([np.sqrt(np.sum((np.array([val for val in HeadPos[i+1]]) - np.array([val for val in HeadPos[i]]))**2)).tolist() for i in range(len(HeadPos)-1)] + [0])
    
    # Export to csv
    movementDataToExport= pd.DataFrame(np.transpose(np.array([dataGroup['TailAngle'][start:end], dataGroup['TailAngle_smoothed'][start:end], dataGroup['Heading'][start:end], tailLength, subsequentPointsDistance, boutData['HeadX'], boutData['HeadY']])), columns=['TailAngle', 'TailAngle_smoothed', 'Heading', 'TailLength', 'subsequentPointsDistance', 'HeadX', 'HeadY'])
    movementDataToExport.to_csv('animal' + str(numAnimal) + '_frame_' + str(startFrame) + '_to_' + str(endFrame) + '.csv')
    
    return movementDataToExport
