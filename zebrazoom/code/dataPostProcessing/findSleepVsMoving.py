import json
import numpy as np
import pandas as pd
import os

def calculateSleepVsMovingPeriods(pathToZZoutput, videoName, speedThresholdForMoving, notMovingNumberOfFramesThresholdForSleep, distanceTravelledRollingMedianFilter=0, videoPixelSize=-1, videoFPS=-1):
  
  pathToVideo = os.path.join(pathToZZoutput, videoName, "results_" + videoName + ".txt")
  
  with open(pathToVideo) as ff:
    dataRef = json.load(ff)
  
  if videoPixelSize == -1:
    if "videoPixelSize" in dataRef:
      videoPixelSize = dataRef["videoPixelSize"]
    else:
      print("You should add the parameter 'videoPixelSize' in your configuration file")
      videoPixelSize = 1
  
  if videoFPS == -1:
    if "videoFPS" in dataRef:
      videoFPS = dataRef["videoFPS"]
    else:
      print("You should add the parameter 'videoFPS' in your configuration file")
      videoFPS = 1
  
  dfFinal = pd.DataFrame()
  
  for wellNumber in range(len(dataRef['wellPoissMouv'])):
    
    displacementVector = videoPixelSize * np.diff(np.array([dataRef['wellPoissMouv'][wellNumber][0][0]["HeadX"], dataRef['wellPoissMouv'][wellNumber][0][0]["HeadY"]]))
    squaredDisplacement = displacementVector * displacementVector
    distance = np.sqrt(squaredDisplacement[0] + squaredDisplacement[1])
    # distance = np.append(distance, [0])
    distance = np.insert(distance, 0, 0)
    distance = np.insert(distance, 0, 0)
    if distanceTravelledRollingMedianFilter:
      distance2 = np.convolve(distance, np.ones(distanceTravelledRollingMedianFilter), 'same') / distanceTravelledRollingMedianFilter
      distance2[:distanceTravelledRollingMedianFilter-1] = distance[:distanceTravelledRollingMedianFilter-1]
      distance2[-distanceTravelledRollingMedianFilter+1:] = distance[-distanceTravelledRollingMedianFilter+1:]
      distance = distance2
    
    speed = distance * videoFPS
    
    moving = speed > speedThresholdForMoving
    
    sleep = np.array([False for i in range(len(moving))])
    countNotMovingFrames = 0
    for i in range(len(sleep)):
      if moving[i]:
        countNotMovingFrames = 0
      else:
        countNotMovingFrames = countNotMovingFrames + 1
        if countNotMovingFrames >= notMovingNumberOfFramesThresholdForSleep:
          sleep[i] = True
        if countNotMovingFrames == notMovingNumberOfFramesThresholdForSleep:
          countNotMovingFrames2 = countNotMovingFrames - 1
          j = i - 1
          while j >= 0 and countNotMovingFrames2 > 0:
            sleep[j] = True
            countNotMovingFrames2 = countNotMovingFrames2 - 1
            j = j - 1
    
    df = pd.DataFrame(data = np.transpose(np.append(np.append([speed], [moving], axis=0), [sleep], axis=0)), columns = ['speed_' + str(wellNumber), 'moving_' + str(wellNumber), 'sleep_' + str(wellNumber)])
    dfFinal = pd.concat([dfFinal, df], axis=1)
    
  dfFinal.to_excel(os.path.join(pathToZZoutput, videoName, "sleepVsMoving_" + videoName + ".xlsx"))
