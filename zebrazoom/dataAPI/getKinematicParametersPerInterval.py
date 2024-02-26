import numpy as np

from zebrazoom.dataAnalysis.datasetcreation.getGlobalParameters import getGlobalParameters

from ._openResultsFile import openResultsFile


def getKinematicParametersPerInterval(videoName: str, numWell: int, numAnimal: int, startFrame: int, endFrame: int) -> dict:
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

    parametersToCalculate = ['Bout Duration (s)', 'Bout Distance (mm)', 'Bout Speed (mm/s)', 'maxTailAngleAmplitude', 'Absolute Yaw (deg)', 'Signed Yaw (deg)']
    return dict(zip(parametersToCalculate, getGlobalParameters(boutData, results.attrs['videoFPS'], results.attrs['videoPixelSize'], 4, None, parametersToCalculate, firstFrame, lastFrame)))
