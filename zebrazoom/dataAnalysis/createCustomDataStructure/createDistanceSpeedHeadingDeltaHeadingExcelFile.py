import json
import matplotlib.pyplot as plt
import cv2
import numpy as np
import math
import pandas as pd
import os

from PyQt5.QtWidgets import QFileDialog

def distBetweenThetas(theta1, theta2):
  diff     = 0
  addMinus = False
  if theta1 > theta2:
    diff = theta1 - theta2
  else:
    diff = theta2 - theta1
    addMinus = True
  if diff > 180:
    diff = 360 - diff
  if addMinus:
    return -diff
  else:
    return diff

def createDistanceSpeedHeadingDeltaHeadingExcelFile(ZZoutputFolder, fps, pixelSize):
  
  pathToResultFolder =  QFileDialog.getExistingDirectory(caption='Choose the result folder for which an excel file should be generated', directory=ZZoutputFolder)
  if not pathToResultFolder:
    return

  videoName = os.path.basename(os.path.normpath(pathToResultFolder))
  
  numberOfWells       = 0
  totalNumberOfFrames = 0
  
  # Transfering data from results_videoName.txt to 'per frame' pandas dataframe
  with open(os.path.join(pathToResultFolder, 'results_' + videoName + '.txt')) as video:
  
    supstruct = json.load(video)
    
    numberOfWells = len(supstruct['wellPoissMouv'])
    firstFrame = 0
    lastFrame  = 0
    if ('lastFrame' in supstruct) and ('firstFrame' in supstruct):
      totalNumberOfFrames = supstruct['lastFrame'] - supstruct['firstFrame'] + 1
      firstFrame = int(supstruct['firstFrame'])
      lastFrame  = int(supstruct['lastFrame'])
    else:
      raise NameError('firstFrame and lastFrame are not in the superstructure results file!')
    
    print("totalNumberOfFrames: ", totalNumberOfFrames)

    data = pd.DataFrame(data=[[wellNum, frameNum, frameNum/fps, (frameNum/fps)/60, float('nan'), float('nan'), float('nan'), float('nan'), float('nan'), float('nan')] for wellNum in range(0, numberOfWells) for frameNum in range(firstFrame, lastFrame)], columns=['wellId', 'frameNumber', 'second', 'minute', 'xPosition', 'yPosition', 'instantaneousDistance', 'instantaneousSpeed', 'heading', 'deltaHeading'])
    
    for numWell in range(0, len(supstruct['wellPoissMouv'])):  
      for numAnimal in range(0, len(supstruct['wellPoissMouv'][numWell])):
        for numBout in range(0, len(supstruct['wellPoissMouv'][numWell][numAnimal])):
          bout = supstruct['wellPoissMouv'][numWell][numAnimal][numBout]
          # if bout["BoutEnd"] < totalNumberOfFrames:
          print("numWell:", numWell, "; numBout:", numBout, "; boutStart:", bout["BoutStart"])
          try:
            data.loc[np.logical_and(np.logical_and(data['wellId'] == numWell, data['frameNumber'] >= bout["BoutStart"]), data['frameNumber'] <= bout["BoutEnd"]), 'xPosition'] = bout['HeadX']
            data.loc[np.logical_and(np.logical_and(data['wellId'] == numWell, data['frameNumber'] >= bout["BoutStart"]), data['frameNumber'] <= bout["BoutEnd"]), 'yPosition'] = bout['HeadY']
            data.loc[np.logical_and(np.logical_and(data['wellId'] == numWell, data['frameNumber'] >= bout["BoutStart"]), data['frameNumber'] <= bout["BoutEnd"]), 'heading'] = bout['Heading']
          except:
            data.loc[np.logical_and(np.logical_and(data['wellId'] == numWell, data['frameNumber'] >= bout["BoutStart"]), data['frameNumber'] <= bout["BoutEnd"]), 'xPosition'] = bout['HeadX'][0:len(data.loc[np.logical_and(np.logical_and(data['wellId'] == numWell, data['frameNumber'] >= bout["BoutStart"]), data['frameNumber'] <= bout["BoutEnd"]), 'xPosition'])]
            data.loc[np.logical_and(np.logical_and(data['wellId'] == numWell, data['frameNumber'] >= bout["BoutStart"]), data['frameNumber'] <= bout["BoutEnd"]), 'yPosition'] = bout['HeadY'][0:len(data.loc[np.logical_and(np.logical_and(data['wellId'] == numWell, data['frameNumber'] >= bout["BoutStart"]), data['frameNumber'] <= bout["BoutEnd"]), 'yPosition'])]
            data.loc[np.logical_and(np.logical_and(data['wellId'] == numWell, data['frameNumber'] >= bout["BoutStart"]), data['frameNumber'] <= bout["BoutEnd"]), 'heading'] = bout['Heading'][0:len(data.loc[np.logical_and(np.logical_and(data['wellId'] == numWell, data['frameNumber'] >= bout["BoutStart"]), data['frameNumber'] <= bout["BoutEnd"]), 'yPosition'])]
  
  # Calculating the "instantaneousDistance" and "instantaneousSpeed"
  previousNumWell = 0
  previousXPos = -1
  previousYPos = -1
  for i in range(0, len(data) - 1):
    print(i, len(data))
    data.loc[i, 'heading'] = (180 / math.pi) * data.loc[i, 'heading']
    if data.loc[i, 'wellId'] == previousNumWell:
      if not(np.isnan(data.loc[i, 'xPosition'])):
        if not(previousXPos == -1) and not(previousYPos == -1):
          data.loc[i, 'instantaneousDistance'] = math.sqrt((data.loc[i, 'xPosition'] - previousXPos)**2 + (data.loc[i, 'yPosition'] - previousYPos)**2) * pixelSize
          data.loc[i, 'instantaneousSpeed']    = data.loc[i, 'instantaneousDistance'] * fps
          data.loc[i, 'deltaHeading']          = distBetweenThetas(data.loc[i, 'heading'], previousHeading)
        previousXPos    = data.loc[i, 'xPosition']
        previousYPos    = data.loc[i, 'yPosition']
        previousHeading = data.loc[i, 'heading']
    else:
      previousNumWell = data.loc[i, 'wellId']
      previousXPos = -1
      previousYPos = -1
  
  # Changing the shape of the data
  finalDataArray = 0
  for wellId in range(0, numberOfWells):
    wellData = data.loc[data['wellId'] == wellId]
    if type(finalDataArray) == int:
      finalDataArray = np.concatenate((np.transpose(np.array([[i for i in range(firstFrame, lastFrame)]])), np.transpose(np.array([[i/fps for i in range(firstFrame, lastFrame)]])), np.transpose(np.array([wellData['xPosition']])), np.transpose(np.array([wellData['yPosition']])), np.transpose(np.array([wellData['instantaneousDistance']])), np.transpose(np.array([wellData['instantaneousSpeed']])), np.transpose(np.array([wellData['heading']])), np.transpose(np.array([wellData['deltaHeading']]))), axis=1)
    else:
      finalDataArray = np.concatenate((finalDataArray, np.transpose(np.array([wellData['xPosition']])), np.transpose(np.array([wellData['yPosition']])), np.transpose(np.array([wellData['instantaneousDistance']])), np.transpose(np.array([wellData['instantaneousSpeed']])), np.transpose(np.array([wellData['heading']])), np.transpose(np.array([wellData['deltaHeading']]))), axis=1)
  
  # Converting to excel
  finalData = pd.DataFrame(data=finalDataArray, columns=['frame', 'second'] + [item for i in range(0, numberOfWells) for item in ['xPosition' + str(i), 'yPosition' + str(i), 'distanceWell' + str(i), 'speedWell' + str(i), 'heading' + str(i), 'deltaHeading' + str(i)]])
  finalData.to_excel(os.path.join(pathToResultFolder, videoName + '_Distances.xlsx'))

