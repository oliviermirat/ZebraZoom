import math
import os

import numpy as np
import pandas as pd

from ._openResultsFile import openResultsFile


def createDistanceBetweenFramesExcelFile(videoName: str) -> None:
  with openResultsFile(videoName, 'r') as results:
    numberOfWells = len(results['wellPositions'])
    firstFrame = results.attrs['firstFrame']
    lastFrame = results.attrs['lastFrame']

    if 'videoFPS' not in results.attrs:
      raise ValueError(f'videoFPS not found in the results')
    if 'videoPixelSize' not in results.attrs:
      raise ValueError(f'videoPixelSize not found in the results')
    fps = results.attrs['videoFPS']
    pixelSize = results.attrs['videoPixelSize']

    data = pd.DataFrame(columns=['wellId', 'frameNumber', 'second', 'minute', 'xPosition', 'yPosition', 'instantaneousDistance'], index=range((lastFrame - firstFrame) * numberOfWells))
    data.loc[:, 'frameNumber'] = [x for _ in range(numberOfWells) for x in range(firstFrame, lastFrame)]
    data.loc[:, 'second'] = data['frameNumber'] / fps
    data.loc[:, 'minute'] = data['second'] / 60
    data.loc[:, 'instantaneousDistance'] = 0
    for wellIdx in range(numberOfWells):
      data.loc[data.index[wellIdx * (lastFrame - firstFrame): (wellIdx + 1) * (lastFrame - firstFrame)], 'wellId'] = wellIdx
      for bout in results[f'dataForWell{wellIdx}']['dataForAnimal0']['listOfBouts']:
        boutStart = results[f'dataForWell{wellIdx}']['dataForAnimal0']['listOfBouts'][bout].attrs['BoutStart'] - firstFrame
        boutEnd = results[f'dataForWell{wellIdx}']['dataForAnimal0']['listOfBouts'][bout].attrs['BoutEnd'] - firstFrame + 1
        rowSlice = np.s_[wellIdx * (lastFrame - firstFrame) + boutStart: wellIdx * (lastFrame - firstFrame) + boutEnd]
        data.loc[data.index[rowSlice], 'xPosition'] = results[f'dataForWell{wellIdx}']['dataForAnimal0']['dataPerFrame']['HeadPos']['X'][boutStart:boutEnd]
        data.loc[data.index[rowSlice], 'yPosition'] = results[f'dataForWell{wellIdx}']['dataForAnimal0']['dataPerFrame']['HeadPos']['Y'][boutStart:boutEnd]
    ZZoutputFolder = os.path.dirname(results.filename)

  # Calculating the "instantaneousDistance"
  previousNumWell = 0
  previousXPos = -1
  previousYPos = -1
  for i in range(0, len(data) - 1):
    print(i, len(data))
    if data.loc[i, 'wellId'] == previousNumWell:
      if not(np.isnan(data.loc[i, 'xPosition'])):
        if not(previousXPos == -1) and not(previousYPos == -1):
          data.loc[i, 'instantaneousDistance'] = math.sqrt((data.loc[i, 'xPosition'] - previousXPos)**2 + (data.loc[i, 'yPosition'] - previousYPos)**2) * pixelSize
        previousXPos = data.loc[i, 'xPosition']
        previousYPos = data.loc[i, 'yPosition']
    else:
      previousNumWell = data.loc[i, 'wellId']
      previousXPos = -1
      previousYPos = -1

  # Changing the shape of the data
  finalDataArray = 0
  for wellId in range(0, numberOfWells):
    wellData = data.loc[data['wellId'] == wellId]
    if type(finalDataArray) == int:
      finalDataArray = np.concatenate((np.transpose(np.array([[i for i in range(firstFrame, lastFrame)]])), np.transpose(np.array([[i/fps for i in range(firstFrame, lastFrame)]])), np.transpose(np.array([wellData['instantaneousDistance']])), np.transpose(np.array([wellData['xPosition']])), np.transpose(np.array([wellData['yPosition']]))), axis=1)
    else:
      finalDataArray = np.concatenate((finalDataArray, np.transpose(np.array([wellData['instantaneousDistance']])), np.transpose(np.array([wellData['xPosition']])), np.transpose(np.array([wellData['yPosition']]))), axis=1)

  # Converting to excel
  finalData = pd.DataFrame(data=finalDataArray, columns=['frame', 'second'] + [item for i in range(0, numberOfWells) for item in ['distanceWell' + str(i), 'xPosition' + str(i), 'yPosition' + str(i)]])
  finalData.to_excel(os.path.join(ZZoutputFolder, videoName + '_Distances.xlsx'))
