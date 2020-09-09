import numpy as np
from scipy.interpolate import UnivariateSpline
import math

def getGlobalParameters(curbout, fps, pixelSize):

  BoutDuration = (curbout["BoutEnd"] - curbout["BoutStart"] + 1) / fps
  
  NumberOfOscillations = len(curbout["Bend_Timing"]) / 2
  
  TotalDistance = 0 
  posX = curbout["HeadX"]
  posX = [posX[4*i] for i in range(0, int(len(posX)/4))]
  posY = curbout["HeadY"]
  posY = [posY[4*i] for i in range(0, int(len(posY)/4))]
  for j in range(1, len(posX)-1):
      TotalDistance = TotalDistance + math.sqrt((posX[j+1] - posX[j])**2 + (posY[j+1] - posY[j])**2)
  TotalDistance = TotalDistance * pixelSize

  Speed = TotalDistance / BoutDuration
  
  meanTBF = NumberOfOscillations / BoutDuration
  
  maxAmplitude = max([abs(ta) for ta in curbout["TailAngle_smoothed"]])
  
  firstBendTime = curbout["Bend_Timing"][0]
  
  firstBendAmplitude = abs(curbout["Bend_Amplitude"][0])
  
  return [BoutDuration, TotalDistance, Speed, NumberOfOscillations, meanTBF, maxAmplitude, posY[0], posY[len(posY)-1], np.mean(posY), firstBendTime, firstBendAmplitude]
