import h5py
import numpy as np
import cv2
import math
import json
import os
import sys
import pandas as pd
from scipy.interpolate import UnivariateSpline

import numpy as np
# from filterpy.kalman import KalmanFilter
# from filterpy.common import Q_discrete_white_noise

from zebrazoom.code.detectMovementWithRawVideo import detectMovementWithRawVideo
from zebrazoom.code.trackingFolder.tailTrackingFunctionsFolder.getTailTipManual import getHeadPositionByFileSaved, getTailTipByFileSaved

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
  
def smoothAllTailAngles(allAngles, hyperparameters, start, end):
  # The first angle is removed here because it corresponds to the angle between two same point (the center of the head)
  tailangles_arr = np.transpose(allAngles[start:end+1, 1:len(allAngles)])
  tailangles_arr_smoothed = np.zeros((0, len(tailangles_arr[0])))
  for angle_raw in tailangles_arr:
    rolling_window = hyperparameters["tailAngleMedianFilter"]
    if rolling_window > 0:
      shift = int(-rolling_window / 2)
      angle_median = np.array(pd.Series(angle_raw).rolling(rolling_window).median())
      angle_median = np.roll(angle_median, shift)
      for ii in range(0, rolling_window):
        if ii >= 0 and ii < len(angle_raw):
          angle_median[ii] = angle_raw[ii]
      for ii in range(len(angle_median)-rolling_window,len(angle_median)):
        if ii >= 0 and ii < len(angle_raw):
          angle_median[ii] = angle_raw[ii]
    else:
      angle_median = angle_raw
    tailToSmooth = angle_median
    if len(tailToSmooth) >= 5:
      x = np.linspace(0, 1, len(tailToSmooth))
      s = UnivariateSpline(x, tailToSmooth, s=hyperparameters["tailAngleSmoothingFactor"])
      tailSmoothed     = s(x)
    else:
      tailSmoothed = tailToSmooth
      
    tailSmoothed2    = np.zeros((1, len(tailSmoothed)))
    tailSmoothed2[0] = tailSmoothed
      
    tailangles_arr_smoothed = np.append(tailangles_arr_smoothed, tailSmoothed2, axis=0)
  return [tailangles_arr, tailangles_arr_smoothed]

def extractParameters(trackingData, wellNumber, hyperparameters, videoPath, wellPositions, background, tailAngle = 0):

  firstFrame = hyperparameters["firstFrame"]
  thresAngleBoutDetect = hyperparameters["thresAngleBoutDetect"]
  debugExtractParams = hyperparameters["debugExtractParams"]
  tailAngleSmoothingFactor = hyperparameters["tailAngleSmoothingFactor"]

  trackingHeadTailAllAnimals = trackingData[0]
  trackingHeadingAllAnimals  = trackingData[1]
  trackingEyesAllAnimals     = trackingData[2]
  headPositionFirstFrame     = trackingData[3]
  tailTipFirstFrame          = trackingData[4]
  auDessusPerAnimal          = trackingData[5] if len(trackingData) == 6 else 0
    
  data = []
  
  for animalId in range(0, len(trackingHeadTailAllAnimals)):
    
    trackingTail    = trackingHeadTailAllAnimals[animalId]
    trackingHeading = trackingHeadingAllAnimals[animalId]
    
    n = len(trackingTail[0])
    
    debug = 0

    nbFrames = len(trackingTail)
    nbPoints = len(trackingTail[0])

    tail_1    = np.zeros((nbFrames, 2))
    tail_2    = np.zeros((nbFrames, 2))
    tip       = np.zeros((nbFrames, 2))
    head      = np.zeros((nbFrames, 2))
    heading   = np.zeros((nbFrames, 1))
    angle     = np.zeros((nbFrames, 1))
    allAngles = np.zeros((nbFrames, n))
    tailX     = np.zeros((nbFrames, n))
    tailY     = np.zeros((nbFrames, n))
    
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
      tail_2[i]  = np.array([ trackingTail[i][2][0], trackingTail[i][2][1] ])
      
      nbTailPoints = len(trackingTail[0]) - 1
      tip[i]     = np.array([ trackingTail[i][nbTailPoints][0], trackingTail[i][nbTailPoints][1] ])
      
      head[i]    = np.array([ trackingTail[i][0][0], trackingTail[i][0][1] ])
      
      if hyperparameters["headingCalculationMethod"] == "calculatedWithFirstTailPt":
        heading[i] = calculateAngle(head[i], tail_1[i])
      if hyperparameters["headingCalculationMethod"] == "calculatedWithTwoFirstTailPt":
        heading[i] = calculateAngle(head[i], tail_2[i])
      elif hyperparameters["headingCalculationMethod"] == "calculatedWithMedianTailTip":
        heading[i] = calculateAngle(head[i], medianTip)
      elif hyperparameters["headingCalculationMethod"] == "simplyFromPreviousCalculations":
        heading[i] = trackingHeading[i]
        heading[i] = (heading[i] + math.pi) % (2*math.pi)
      elif hyperparameters["headingCalculationMethod"] == "fromPreviousCalculationsAndAdjustWithPreviousFrame":
        heading[i] = trackingHeading[i]
        heading[i] = (heading[i] + math.pi) % (2*math.pi)
        if i != 0 and distBetweenThetas(heading[i-1], ((heading[i] + math.pi) % (2*math.pi))) > distBetweenThetas(heading[i-1], heading[i]):
          heading[i] = (heading[i] + math.pi) % (2*math.pi)
      else: # calculatedWithHead : THIS IS THE DEFAULT
        if not(math.isnan(trackingHeading[i])):
          heading[i] = trackingHeading[i]
          diff1 = distBetweenThetas(heading[i],           calculateAngle(head[i], tail_1[i]))
          diff2 = distBetweenThetas(heading[i] + math.pi, calculateAngle(head[i], tail_1[i]))
          if diff2 < diff1:
            heading[i] = heading[i] + math.pi
        else:
          heading[i] = 0
      
      if type(tailAngle) == int:
        angle[i] = calculateTailAngle(calculateAngle(head[i], tip[i]), heading[i])
      else:
        angle[i] = tailAngle[i]
        
      if hyperparameters["calculateAllTailAngles"]:
        for j in range(0, n):
          allAngles[i][j] = calculateTailAngle(calculateAngle(head[i], np.array([trackingTail[i][j][0], trackingTail[i][j][1]])), heading[i])
      
      heading[i] = (heading[i] + math.pi) % (2*math.pi)
      
      tailX[i]   = trackingTail[i,:,0]
      tailY[i]   = trackingTail[i,:,1]
    
    if hyperparameters["saveAllDataEvenIfNotInBouts"]:
      trackingFlatten = [trackingHeadTailAllAnimals[animalId][i].flatten().tolist() + [heading[i]] + angle[i].tolist() for i in range(0, len(heading))]
      trackingFlattenColumnsNames = ['HeadPosX', 'HeadPosY']
      for i in range(0, int((len(trackingHeadTailAllAnimals[0][0].flatten().tolist()) - 2) / 2)):
        trackingFlattenColumnsNames += ['TailPosX' + str(i + 1)]
        trackingFlattenColumnsNames += ['TailPosY' + str(i + 1)]
      trackingFlattenColumnsNames += ['Heading']
      trackingFlattenColumnsNames += ['tailAngle']
      trackingFlattenPandas = pd.DataFrame(np.array(trackingFlatten), columns=trackingFlattenColumnsNames)
      trackingFlattenPandas.to_csv(os.path.join(os.path.join(hyperparameters["outputFolder"], hyperparameters["videoName"]), 'allData_' + hyperparameters["videoName"] + '_wellNumber' + str(wellNumber) + '_animal' + str(animalId) + '.cvs'))

    
    if hyperparameters["noBoutsDetection"] == 1:
      auDessus        = np.zeros((nbFrames, 1))
      for i in range(0,nbFrames):
        auDessus[i] = 1
    elif hyperparameters["boutEdgesWhereZeros"] == 1:
      auDessus        = np.zeros((nbFrames, 1))
      for i in range(0,nbFrames):
        if ((head[i][0] == 0) and (head[i][1] == 0)):
          auDessus[i] = 0
        else:
          auDessus[i] = 1
    elif type(auDessusPerAnimal) != int:

      auDessus = auDessusPerAnimal[animalId]
    elif hyperparameters["coordinatesOnlyBoutDetection"]:
      frameDistance = hyperparameters["frameGapComparision"]
      auDessus = [int(math.sqrt(sum((head[i+frameDistance] - coords) ** 2)) >= hyperparameters["coordinatesOnlyBoutDetectionMinDist"]) for i, coords in enumerate(head[:-frameDistance])]
      auDessus.extend([0] * frameDistance)
    elif hyperparameters["thresForDetectMovementWithRawVideo"] == 0:

      # Calculating angle median
      angle2 = np.transpose(angle)
      angle2 = angle2[0]
      rolling_window = hyperparameters["tailAngleMedianFilter"]
      if rolling_window > 0:
        shift = int(-rolling_window / 2)
        angle_median = np.array(pd.Series(angle2).rolling(rolling_window).median())
        angle_median = np.roll(angle_median, shift)
        for ii in range(0, rolling_window):
          angle_median[ii] = angle2[ii]
        for ii in range(len(angle_median)-rolling_window,len(angle_median)):
          angle_median[ii] = angle2[ii]
      else:
        angle_median = angle2
      # Calculating angle variation to detect movement
      angleVariation  = np.zeros((nbFrames, 1))
      auDessus        = np.zeros((nbFrames, 1))
      for i in range(0,nbFrames):
        if (hyperparameters["freqAlgoPosFollow"] != 0) and (i % (hyperparameters["freqAlgoPosFollow"]) == 0):
          print("Extract Param Middle: wellNumber:",wellNumber," ; frame:",i)
        min = 10000
        max = -10000
        # for j in range(i-hyperparameters["windowForBoutDetectWithAngle"], i+1):
        for j in range(i-int(hyperparameters["windowForBoutDetectWithAngle"]/2), i+int(hyperparameters["windowForBoutDetectWithAngle"]/2)):
          if (j >= 0) and (j<nbFrames):
            if angle_median[j] > max:
              max = angle_median[j]
            if angle_median[j] < min:
              min = angle_median[j]
        angleVariation[i] = max - min
        if debug:
          print(i,angleVariation[i])
        if angleVariation[i] > thresAngleBoutDetect:
          auDessus[i] = 1

    else:
      auDessus = detectMovementWithRawVideo(hyperparameters, videoPath, background, wellNumber, wellPositions, head, headPositionFirstFrame, tailTipFirstFrame)
    
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
        if curBout[0][2] - curBout[0][1] >= hyperparameters["detectBoutMinNbFrames"] or (hyperparameters["noChecksForBoutSelectionInExtractParams"] and curBout[0][2] - curBout[0][1] >= hyperparameters["boutsMinNbFrames"]):
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
      if hyperparameters["addOneFrameAtTheEndForBoutDetection"]:
        if bouts[numBout][2] + 1 < nbFrames:
          bouts[numBout][2] = bouts[numBout][2] + 1
    
    for i in range(0,len(bouts)):
    
      if (hyperparameters["freqAlgoPosFollow"] != 0) and (i % (hyperparameters["freqAlgoPosFollow"]*10) == 0):
        print("Extract Param End2 Freq*10 : wellNumber:",wellNumber," ; frame:",i)
      
      item = {}
      start = int(bouts[i][1])
      end   = int(bouts[i][2])
      item["AnimalNumber"]  = animalId
      item["BoutStart"]     = start + firstFrame
      item["BoutEnd"]       = end + firstFrame
      item["TailAngle_Raw"] = angle[start:end+1,0].tolist()
      
      if hyperparameters["eyeTracking"]:
        item["leftEyeX"]      = trackingEyesAllAnimals[animalId, start:end+1, 0].tolist()
        item["leftEyeY"]      = trackingEyesAllAnimals[animalId, start:end+1, 1].tolist()
        item["leftEyeAngle"]  = trackingEyesAllAnimals[animalId, start:end+1, 2].tolist()
        item["leftEyeArea"]   = trackingEyesAllAnimals[animalId, start:end+1, 3].tolist()
        item["rightEyeX"]     = trackingEyesAllAnimals[animalId, start:end+1, 4].tolist()
        item["rightEyeY"]     = trackingEyesAllAnimals[animalId, start:end+1, 5].tolist()
        item["rightEyeAngle"] = trackingEyesAllAnimals[animalId, start:end+1, 6].tolist()
        item["rightEyeArea"]  = trackingEyesAllAnimals[animalId, start:end+1, 7].tolist()
      
      if hyperparameters["calculateAllTailAngles"]:
        [tailangles_arr, tailangles_arr_smoothed] = smoothAllTailAngles(allAngles, hyperparameters, start, end)
        item["allTailAngles"]         = tailangles_arr.tolist()
        item["allTailAnglesSmoothed"] = tailangles_arr_smoothed.tolist()
      
      if np.isnan(head[start:end+1,0]).any():
        item["HeadX"] = [0]
        item["HeadY"] = [0]
      else:
        item["HeadX"]         = head[start:end+1,0].tolist()
        item["HeadY"]         = head[start:end+1,1].tolist()
        item["Heading"]       = heading[start:end+1,0].tolist()
        item["TailX_VideoReferential"] = tailX[start:end+1].tolist()
        item["TailY_VideoReferential"] = tailY[start:end+1].tolist()
      data.append(item)
  
  print("Parameters extracted for well",wellNumber)
  if hyperparameters["popUpAlgoFollow"]:
    import zebrazoom.code.popUpAlgoFollow as popUpAlgoFollow
    popUpAlgoFollow.prepend("Parameters extracted for well " + str(wellNumber))
  
  return data
