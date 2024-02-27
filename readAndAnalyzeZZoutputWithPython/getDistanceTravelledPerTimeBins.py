import json
import math

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

pathToVideos = './'

listOfVideosTracked = ['nameOfVideo']

fps = 25
numberOfWells = 6
totalNumberOfFrames = 70000

data = pd.DataFrame(data=[[wellNum, frameNum, frameNum/fps, (frameNum/fps)/60, float('nan'), float('nan'), 0] for wellNum in range(0, numberOfWells) for frameNum in range(0, totalNumberOfFrames)], columns=['wellId', 'frameNumber', 'second', 'minute', 'xPosition', 'yPosition', 'instantaneousDistance'])


# Transfering data from results_videoName.txt to 'per frame' pandas dataframe

for videoName in listOfVideosTracked:
  
  with open(pathToVideos + '/results_' + videoName + '.txt') as video:
    
    supstruct = json.load(video)
    
    for numWell in range(0, len(supstruct['wellPoissMouv'])):
      
      for numAnimal in range(0, len(supstruct['wellPoissMouv'][numWell])):
        
        for numBout in range(0, len(supstruct['wellPoissMouv'][numWell][numAnimal])):
          
          bout = supstruct['wellPoissMouv'][numWell][numAnimal][numBout]

          if bout["BoutEnd"] < totalNumberOfFrames:
          
            print("numWell:", numWell, "; numBout:", numBout, "; boutStart:", bout["BoutStart"])
            
            data.loc[np.logical_and(np.logical_and(data['wellId'] == numWell, data['frameNumber'] >= bout["BoutStart"]), data['frameNumber'] <= bout["BoutEnd"]), 'xPosition'] = bout['HeadX']
            
            data.loc[np.logical_and(np.logical_and(data['wellId'] == numWell, data['frameNumber'] >= bout["BoutStart"]), data['frameNumber'] <= bout["BoutEnd"]), 'yPosition'] = bout['HeadY']


# Calculating the "instantaneousDistance"

previousNumWell = 0
previousXPos = -1
previousYPos = -1
for i in range(0, len(data) - 1):
  print(i, len(data))
  if data.loc[i, 'wellId'] == previousNumWell:
    if not(np.isnan(data.loc[i, 'xPosition'])):
      if not(previousXPos == -1) and not(previousYPos == -1):
        data.loc[i, 'instantaneousDistance'] = math.sqrt((data.loc[i, 'xPosition'] - previousXPos)**2 + (data.loc[i, 'yPosition'] - previousYPos)**2)
      previousXPos = data.loc[i, 'xPosition']
      previousYPos = data.loc[i, 'yPosition']
  else:
    previousNumWell = data.loc[i, 'wellId']
    previousXPos = -1
    previousYPos = -1


# Optional first plot

if False:
  wellData = data.loc[data['wellId']==0]
  minute = well0Data['minute']
  instantaneousDistance = wellData['instantaneousDistance']
  plt.plot(minute, instantaneousDistance)
  plt.show()


# Regrouping per "time bins"

distanceOperation = 'mean' # can be set to 'sum', 'mean', 'median'

finalDataArray = 0
for wellId in range(0, 6):
  fig = plt.subplots(1, 1)

  wellData = data.loc[data['wellId'] == wellId]

  wellData = wellData.loc[wellData['minute'] < 40]

  wellData['minuteGroup'] = (wellData['minute'] / 0.05).astype('int')

  if distanceOperation == 'sum':
    minuteGroupSum = wellData[['minuteGroup', 'instantaneousDistance']].groupby(['minuteGroup']).sum()['instantaneousDistance'].tolist()
  elif distanceOperation == 'mean':
    minuteGroupSum = wellData[['minuteGroup', 'instantaneousDistance']].groupby(['minuteGroup']).mean()['instantaneousDistance'].tolist()
  elif distanceOperation == 'median':
    minuteGroupSum = wellData[['minuteGroup', 'instantaneousDistance']].groupby(['minuteGroup']).median()['instantaneousDistance'].tolist()

  minuteGroupFirst = wellData[['minuteGroup', 'minute']].groupby(['minuteGroup']).first()['minute'].tolist()

  plt.plot(minuteGroupFirst, minuteGroupSum, '.')

  pointsOfInterest1 = np.logical_or(np.logical_or(np.logical_or(np.logical_or(np.logical_or(np.logical_or(np.logical_or(np.logical_or(np.logical_or(np.array(minuteGroupFirst) == 20, np.array(minuteGroupFirst) == 21), np.array(minuteGroupFirst) == 22), np.array(minuteGroupFirst) == 23), np.array(minuteGroupFirst) == 24), np.array(minuteGroupFirst) == 25), np.array(minuteGroupFirst) == 26), np.array(minuteGroupFirst) == 27), np.array(minuteGroupFirst) == 28), np.array(minuteGroupFirst) == 29)

  plt.plot(np.array(minuteGroupFirst)[pointsOfInterest1], np.array(minuteGroupSum)[pointsOfInterest1], '.')

  pointsOfInterest2 = np.array(minuteGroupFirst) == 10

  plt.plot(np.array(minuteGroupFirst)[pointsOfInterest2], np.array(minuteGroupSum)[pointsOfInterest2], '.r')

  plt.savefig('well' + str(wellId) + '.png')

  if type(finalDataArray) == int:
    finalDataArray = np.concatenate((np.transpose(np.array([[int(roundedMin*100)/100 for roundedMin in minuteGroupFirst]])), np.transpose(np.array([minuteGroupSum]))), axis=1)
  else:
    finalDataArray = np.concatenate((finalDataArray, np.transpose(np.array([minuteGroupSum]))), axis=1)

finalData = pd.DataFrame(data=finalDataArray, columns=['minute', 'distanceWell0', 'distanceWell1', 'distanceWell2', 'distanceWell3', 'distanceWell4', 'distanceWell5'])

finalData.to_excel('finalData.xls')