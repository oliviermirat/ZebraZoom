import numpy as np

from ._calculateAndStoreCurvature import calculateAndStoreCurvature
from ._openResultsFile import openResultsFile


def getCurvaturePerTimeInterval(videoName: str, numWell: int, numAnimal: int, startTimeInSeconds: int, endTimeInSeconds: int) -> [np.array, np.array, np.array]:
  
  with openResultsFile(videoName, 'r+') as results:
    if 'videoFPS' not in results.attrs:
      raise ValueError(f'videoFPS not found in the results, cannot convert seconds to frames')
    if 'videoPixelSize' not in results.attrs:
      raise ValueError(f'videoPixelSize not found in the results, cannot convert seconds to frames')
    intervalStart = int(startTimeInSeconds * results.attrs['videoFPS'])
    intervalEnd   = int(endTimeInSeconds * results.attrs['videoFPS'])
    firstFrame    = results.attrs['firstFrame']
    dataGroup = results[f'dataForWell{numWell}/dataForAnimal{numAnimal}/dataPerFrame']
    
    if 'curvature' in dataGroup:
      curvature = np.array([dataGroup['curvature'][column][intervalStart:intervalEnd] for column in dataGroup['curvature'].attrs['columns']])
    else:
      curvature = np.array([data[intervalStart:intervalEnd] for data in calculateAndStoreCurvature(results, dataGroup)])
    
    # Getting x time values for each curvature point
    boutStart = int(startTimeInSeconds * results.attrs['videoFPS'])
    boutEnd   = int(endTimeInSeconds   * results.attrs['videoFPS'])
    xTimeValues = curvature.copy()
    for i in range(0, len(xTimeValues[0])):
      xTimeValues[:, i] = int(100*((i + boutStart)/results.attrs['videoFPS']))/100
    
    # Getting y distance along the tail values for each curvature point
    perFramePath = f'dataForWell{numWell}/dataForAnimal{numAnimal}/dataPerFrame'
    start = boutStart - firstFrame
    end   = boutEnd   - firstFrame
    tailX = np.transpose(np.concatenate((np.array([results[perFramePath+"/HeadPos"]['X'][start:end]]).reshape((-1, 1)), results[perFramePath+"/TailPosX"][start:end].view((float, len(results[perFramePath+"/TailPosX"][start:end].dtype.names)))), axis=1))
    tailY = np.transpose(np.concatenate((np.array([results[perFramePath+"/HeadPos"]['Y'][start:end]]).reshape((-1, 1)), results[perFramePath+"/TailPosY"][start:end].view((float, len(results[perFramePath+"/TailPosX"][start:end].dtype.names)))), axis=1))
    nbLinesTail = len(tailX)
    yDistanceAlongTheTail = curvature.copy()
    yDistanceAlongTheTail[:, :] = np.sqrt(np.square(tailX[2:nbLinesTail, :] - tailX[1:nbLinesTail-1, :]) + np.square(tailY[2:nbLinesTail, :] - tailY[1:nbLinesTail-1, :])) * results.attrs['videoPixelSize']
    for i in range(len(yDistanceAlongTheTail)-2, -1, -1):
      yDistanceAlongTheTail[i, :] += yDistanceAlongTheTail[i+1, :]

    return [curvature, xTimeValues, yDistanceAlongTheTail]
