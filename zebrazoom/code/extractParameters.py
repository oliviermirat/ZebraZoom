import h5py
import numpy as np
import cv2
import math
import json
import os
import sys
import popUpAlgoFollow

import numpy as np
from filterpy.kalman import KalmanFilter
from filterpy.common import Q_discrete_white_noise

# from calculateCurvature import calculateCurvature
from detectMovementWithRawVideo import detectMovementWithRawVideo
from getTailTipManual import getHeadPositionByFileSaved, getTailTipByFileSaved

import pdb

def distBetweenThetas(theta1, theta2):
  diff = 0
  if theta1 > theta2:
    diff = theta1 - theta2
  else:
    diff = theta2 - theta1
  if diff > math.pi:
    diff = (2 * math.pi) - diff
  return diff

def calculateAngle(vectStart, vectEnd):
  x = vectEnd[0] - vectStart[0]
  y = vectEnd[1] - vectStart[1]
  if x == 0:
    if y > 0:
      heading = math.pi / 2
    else:
      heading = (3 * math.pi) / 2
  else:
    heading = np.arctan(abs(y/x))
    if (x < 0) and (y > 0):
      heading = math.pi - heading
    elif (x < 0) and (y < 0):
      heading = heading + math.pi
    elif (x < 0) and (y == 0):
      heading = math.pi
    elif (x > 0) and (y < 0):
      heading = 2*math.pi - heading
  return heading
  
def calculateTailAngle(angle1, angle2):
  output = angle1 - angle2
  output = (output + 2 * 3.14159265) % (2 * 3.14159265)
  if output > 3.14159265:
    output = output - 2*3.14159265;
  return output

def extractParameters(trackingData, wellNumber, hyperparameters, videoPath, wellPositions, background):

  firstFrame = hyperparameters["firstFrame"]
  thresAngleBoutDetect = hyperparameters["thresAngleBoutDetect"]
  debugExtractParams = hyperparameters["debugExtractParams"]

  trackingTailAllAnimals = trackingData[0]
  trackingHeadingAllAnimals = trackingData[1]
  headPosition = trackingData[2]
  tailTip = trackingData[3]
  
  data = []
  
  for animalId in range(0, len(trackingTailAllAnimals)):
    
    trackingTail    = trackingTailAllAnimals[animalId]
    trackingHeading = trackingHeadingAllAnimals[animalId]
    
    n = len(trackingTail[0])
    
    debug = 0

    nbFrames = len(trackingTail)
    nbPoints = len(trackingTail[0])

    tail_1  = np.zeros((nbFrames, 2))
    tip     = np.zeros((nbFrames, 2))
    head    = np.zeros((nbFrames, 2))
    heading = np.zeros((nbFrames, 1))
    angle   = np.zeros((nbFrames, 1))
    tailX   = np.zeros((nbFrames, n))
    tailY   = np.zeros((nbFrames, n))
    
    # fTipX = KalmanFilter (dim_x=2, dim_z=1)
    # fTipX.x = np.array([[2.],[0.]])
    # fTipX.F = np.array([[1.,1.],[0.,1.]])
    # fTipX.H = np.array([[1.,0.]])
    # fTipX.P = np.array([[1000.,    0.],[   0., 1000.] ])
    # fTipX.R = np.array([[5.]])
    # fTipX.Q = Q_discrete_white_noise(dim=2, dt=0.1, var=0.13)

    # fTipY = KalmanFilter (dim_x=2, dim_z=1)
    # fTipY.x = np.array([[2.],[0.]])
    # fTipY.F = np.array([[1.,1.],[0.,1.]])
    # fTipY.H = np.array([[1.,0.]])
    # fTipY.P = np.array([[1000.,    0.],[   0., 1000.] ])
    # fTipY.R = np.array([[5.]])
    # fTipY.Q = Q_discrete_white_noise(dim=2, dt=0.1, var=0.13)
    
    if hyperparameters["headingCalculationMethod"] == "calculatedWithMedianTailTip":
      tip2 = np.zeros((nbFrames, 2))
      nbTailPoints = len(trackingTail[0]) - 1
      for i in range(0,nbFrames):
        tip2[i] = np.array([ trackingTail[i][nbTailPoints][0], trackingTail[i][nbTailPoints][1] ])
      medianTip = np.median(tip2,axis=0)
      
    curvatureBef = 0
    
    for i in range(0,nbFrames):
    
      if (hyperparameters["freqAlgoPosFollow"] != 0) and (i % hyperparameters["freqAlgoPosFollow"] == 0):
        print("Extract Param Begin: wellNumber:",wellNumber," ; frame:",i)
      
      tail_1[i]  = np.array([ trackingTail[i][1][0], trackingTail[i][1][1] ])
      
      nbTailPoints = len(trackingTail[0]) - 1
      tip[i]     = np.array([ trackingTail[i][nbTailPoints][0], trackingTail[i][nbTailPoints][1] ])
      
      # print("bef:",tip[i])
      # fTipX.predict()
      # fTipX.update(np.array([tip[i][0]]))
      # tip[i][0] = fTipX.x[0]
      # trackingTail[i][nbTailPoints][0] = fTipX.x[0]
      
      # fTipY.predict()
      # fTipY.update(np.array([tip[i][1]]))
      # tip[i][1] = fTipY.x[0]
      # trackingTail[i][nbTailPoints][1] = fTipY.x[0]
      # print("aft:",tip[i])
      
      head[i]    = np.array([ trackingTail[i][0][0], trackingTail[i][0][1] ])
      
      if hyperparameters["headingCalculationMethod"] == "calculatedWithFirstTailPt":
        heading[i] = calculateAngle(head[i], tail_1[i])
      elif hyperparameters["headingCalculationMethod"] == "calculatedWithMedianTailTip":
        heading[i] = calculateAngle(head[i], medianTip)
      else: # calculatedWithHead
        heading[i] = trackingHeading[i]
        diff1 = distBetweenThetas(heading[i],           calculateAngle(head[i], tail_1[i]))
        diff2 = distBetweenThetas(heading[i] + math.pi, calculateAngle(head[i], tail_1[i]))
        if diff2 < diff1:
          heading[i] = heading[i] + math.pi
      
      angle[i] = calculateTailAngle(calculateAngle(head[i], tip[i]), heading[i])
      
      heading[i] = (heading[i] + math.pi) % (2*math.pi)
      
      tailX[i]   = trackingTail[i,:,0]
      tailY[i]   = trackingTail[i,:,1]

      # if False:
        # tailForCurv = np.zeros((10, 2))
        # for j in range(0,10):
          # tailForCurv[j][0] = tailX[i][j]
          # tailForCurv[j][1] = tailY[i][j]
        # curvature = calculateCurvature(tailForCurv)
        # diff = np.max(np.abs(curvature))
        # curvatureBef = curvature
    
    if hyperparameters["noBoutsDetection"] == 1:
      auDessus        = np.zeros((nbFrames, 1))
      for i in range(0,nbFrames):
        auDessus[i] = 1
    else:
      if hyperparameters["boutEdgesWhereZeros"] == 1:
        auDessus        = np.zeros((nbFrames, 1))
        for i in range(0,nbFrames):
          if ((head[i][0] == 0) and (head[i][1] == 0)):
            auDessus[i] = 0
          else:
            auDessus[i] = 1
      else:
        if hyperparameters["thresForDetectMovementWithRawVideo"] == 0:
          window = 5
          angleVariation  = np.zeros((nbFrames, 1))
          auDessus        = np.zeros((nbFrames, 1))
          for i in range(0,nbFrames):
            if (hyperparameters["freqAlgoPosFollow"] != 0) and (i % (hyperparameters["freqAlgoPosFollow"]) == 0):
              print("Extract Param Middle: wellNumber:",wellNumber," ; frame:",i)
            min = 10000
            max = -10000
            for j in range(i-2*window,i+1):
              if (j >= 0) and (j<nbFrames):
                if angle[j] > max:
                  max = angle[j]
                if angle[j] < min:
                  min = angle[j]
            angleVariation[i] = max - min
            if debug:
              print(i,angleVariation[i])
            if angleVariation[i] > thresAngleBoutDetect:
              auDessus[i] = 1
        else:
          auDessus = detectMovementWithRawVideo(hyperparameters, videoPath, background, wellNumber, wellPositions, head, headPosition, tailTip)
    
    if (hyperparameters["freqAlgoPosFollow"] != 0):
      print("Extract Param Middle: wellNumber:",wellNumber," ; frame:",i)
    
    auDessus2 = np.copy(auDessus)
    if hyperparameters["boutEdgesWhereZeros"] == 0 and hyperparameters["noBoutsDetection"] == 0:
      windowGap = hyperparameters["fillGapFrameNb"]
      if windowGap:
        for i in range(windowGap,nbFrames-windowGap):
          if auDessus[i] == 0:
            j = i - windowGap
            while (auDessus[j] == 0) and (j < i + windowGap):
              j = j + 1
            if j < i + windowGap:
              j = j + 1;
              while (auDessus[j] == 0) and (j < i + windowGap):
                j = j + 1;
              if auDessus[j] > 0:
                for k in range(i - windowGap, i + windowGap):
                  auDessus2[k] = 1
    
    bouts   = np.zeros((0, 3))
    curBout = np.zeros((1, 3))
    position = 0
    
    for i in range(0, nbFrames):
    
      if (hyperparameters["freqAlgoPosFollow"] != 0) and (i % (hyperparameters["freqAlgoPosFollow"]*10) == 0):
        print("Extract Param End1 Freq*10 : wellNumber:",wellNumber," ; frame:",i)
    
      if (position==0) and (auDessus2[i]==1):
        curBout[0][0] = wellNumber
        curBout[0][1] = i
        position = 1
        retire = 1
      if (position == 1) and ((auDessus2[i] == 0) or (i == nbFrames-1)):
        curBout[0][2] = i-1
        position = 0
        if curBout[0][2] - curBout[0][1] >= hyperparameters["detectBoutMinNbFrames"] or hyperparameters["noChecksForBoutSelectionInExtractParams"]:
          debMouv = int(curBout[0][1])
          endMouv = int(curBout[0][2])
          dist = math.sqrt( (head[debMouv,0]-head[endMouv,0])**2 + (head[debMouv,1]-head[endMouv,1])**2 )
          if ((dist >= hyperparameters["detectBoutMinDist"]) and (np.max(angle[debMouv:endMouv])-np.min(angle[debMouv:endMouv]) >= hyperparameters["detectBoutMinAngleDiff"])) or hyperparameters["noChecksForBoutSelectionInExtractParams"]:
            bouts = np.append(bouts, curBout, axis=0)
          else:
            if debugExtractParams:
              print("Bout starting at", debMouv, " has a dist or angle diff too big. Dist:", dist," minimum was:", hyperparameters["detectBoutMinDist"],". DetectBoutMinAngleDiff:",np.max(angle[debMouv:endMouv])-np.min(angle[debMouv:endMouv]),", minimmum was:",hyperparameters["detectBoutMinAngleDiff"])
        else:
          if debugExtractParams:
            print("Bout starting at", int(curBout[0][1]), "was too small. Length:", curBout[0][2] - curBout[0][1],". Minimum was:", hyperparameters["detectBoutMinNbFrames"])
    
    # Refining beginning and end of bout detection to remove the artefacts from the fill gap procedure
    for numBout in range(0,len(bouts)):
      debMouv = int(bouts[numBout][1])
      finMouv = int(bouts[numBout][2])
      # Refining the beginning
      pos = debMouv
      while int(auDessus[pos]) == 0:
        pos = pos + 1
      bouts[numBout][1] = pos
      # Refining the end
      pos = finMouv
      while int(auDessus[pos]) == 0:
        pos = pos - 1
      bouts[numBout][2] = pos
    
    for i in range(0,len(bouts)):
    
      if (hyperparameters["freqAlgoPosFollow"] != 0) and (i % (hyperparameters["freqAlgoPosFollow"]*10) == 0):
        print("Extract Param End2 Freq*10 : wellNumber:",wellNumber," ; frame:",i)
      
      item = {}
      start = int(bouts[i][1])
      end   = int(bouts[i][2])
      item["AnimalNumber"]  = animalId #int(bouts[i][0])
      item["BoutStart"]     = start + firstFrame
      item["BoutEnd"]       = end + firstFrame
      item["TailAngle_Raw"] = angle[start:end+1,0].tolist()
      item["HeadX"]         = head[start:end+1,0].tolist()
      item["HeadY"]         = head[start:end+1,1].tolist()
      # item["Heading_raw"]   = heading[start:end,0]
      item["Heading"]       = heading[start:end+1,0].tolist()
      item["TailX_VideoReferential"] = tailX[start:end+1].tolist()
      item["TailY_VideoReferential"] = tailY[start:end+1].tolist()
      # item["TailX_HeadingReferential"]
      # item["TailY_HeadingReferential"]
      data.append(item)
  
  print("Parameters extracted for well",wellNumber)
  if hyperparameters["popUpAlgoFollow"]:
    popUpAlgoFollow.prepend("Parameters extracted for well " + str(wellNumber))
  
  return data
