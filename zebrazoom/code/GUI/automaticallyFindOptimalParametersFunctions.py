import numpy as np
import json
import cv2
import math
from zebrazoom.code.getHyperparameters import getHyperparametersSimple
from zebrazoom.code.getImage.getForegroundImage import getForegroundImage
from zebrazoom.mainZZ import mainZZ
import cvui
import pickle
import json
import os
import re
from zebrazoom.code.getBackground import getBackground
from zebrazoom.code.findWells import findWells
from zebrazoom.code.trackingFolder.tracking import tracking
from zebrazoom.code.GUI.adjustParameterInsideAlgoFunctions import prepareConfigFileForParamsAdjustements

def getGroundTruthFromUser(self, controller, nbOfImagesToManuallyClassify, saveIntermediary, zebrafishToTrack):
  
  videoPath = self.videoToCreateConfigFileFor
  
  for m in re.finditer('/', videoPath):
    last = m.start()
    pathToVideo      = videoPath[:last+1]
    videoNameWithExt = videoPath[last+1:]
    allDotsPositions = [m.start() for m in re.finditer('\.', videoNameWithExt)]
    pointPos  = allDotsPositions[len(allDotsPositions)-1]
    videoName = videoNameWithExt[:pointPos]
    videoExt  = videoNameWithExt[pointPos+1:]
  
  initialConfigFile = self.configFile
  
  initialHyperparameters = getHyperparametersSimple(initialConfigFile)
  initialHyperparameters["videoName"]      = videoName
  wellPositions = findWells(os.path.join(pathToVideo, videoNameWithExt), initialHyperparameters)
  
  cap   = cv2.VideoCapture(videoPath)
  max_l = int(cap.get(7))
  
  # Finding the well with the most movement
  cap.set(1, 0)
  ret, firstFrame = cap.read()
  firstFrame = cv2.cvtColor(firstFrame, cv2.COLOR_BGR2GRAY)
  cap.set(1, max_l-1)
  ret, lastFrame = cap.read()
  lastFrame = cv2.cvtColor(lastFrame, cv2.COLOR_BGR2GRAY)
  pixelsChange = np.zeros((len(wellPositions)))
  for wellNumberId in range(0, len(wellPositions)):
    xtop  = wellPositions[wellNumberId]['topLeftX']
    ytop  = wellPositions[wellNumberId]['topLeftY']
    lenX  = wellPositions[wellNumberId]['lengthX']
    lenY  = wellPositions[wellNumberId]['lengthY']
    firstFrameROI = firstFrame[ytop:ytop+lenY, xtop:xtop+lenX]
    lastFrameROI  = lastFrame[ytop:ytop+lenY, xtop:xtop+lenX]
    pixelsChange[wellNumberId] = np.sum(abs(firstFrameROI-lastFrameROI))
  wellNumber = np.argmax(pixelsChange)
  
  backCalculationStep = int(max_l / nbOfImagesToManuallyClassify)
  data = []
  
  for k in range(0, max_l):
    
    if (k % backCalculationStep == 0):
      
      cap.set(1, k)
      ret, frame = cap.read()
      
      xtop  = wellPositions[wellNumber]['topLeftX']
      ytop  = wellPositions[wellNumber]['topLeftY']
      lenX  = wellPositions[wellNumber]['lengthX']
      lenY  = wellPositions[wellNumber]['lengthY']
      frame = frame[ytop:ytop+lenY, xtop:xtop+lenX]
      
      if zebrafishToTrack:
        WINDOW_NAME_1 = "Click on the center of the head of one animal"
      else:
        WINDOW_NAME_1 = "Click on the center of mass of an animal"
        
      cvui.init(WINDOW_NAME_1)
      cv2.moveWindow(WINDOW_NAME_1, 0,0)
      cvui.imshow(WINDOW_NAME_1, frame)
      while not(cvui.mouse(cvui.CLICK)):
        cursor = cvui.mouse()
        if cv2.waitKey(20) == 27:
          break
        headCoordinates = [cursor.x, cursor.y]
      cv2.destroyAllWindows()
      
      if zebrafishToTrack:
        WINDOW_NAME_2 = "Click on the tip of the tail of the same animal"
      else:
        WINDOW_NAME_2 = "Click on a point on the border of the same animal"
      
      cvui.init(WINDOW_NAME_2)
      cv2.moveWindow(WINDOW_NAME_2, 0,0)
      frame2 = frame.copy()
      frame2 = cv2.circle(frame, (headCoordinates[0], headCoordinates[1]), 2, (0, 0, 255), -1)
      cvui.imshow(WINDOW_NAME_2, frame2)
      while not(cvui.mouse(cvui.CLICK)):
        cursor = cvui.mouse()
        if cv2.waitKey(20) == 27:
          break
        tailTipCoordinates = [cursor.x, cursor.y]
      frame2 = cv2.circle(frame, (tailTipCoordinates[0], tailTipCoordinates[1]), 2, (0, 0, 255), -1)  
      cvui.imshow(WINDOW_NAME_2, frame2)
      cv2.waitKey(2000)
      cv2.destroyAllWindows()
      
      if True: # Centered on the animal
        minX = min(headCoordinates[0], tailTipCoordinates[0])
        maxX = max(headCoordinates[0], tailTipCoordinates[0])
        minY = min(headCoordinates[1], tailTipCoordinates[1])
        maxY = max(headCoordinates[1], tailTipCoordinates[1])
        lengthX = maxX - minX
        lengthY = maxY - minY
        
        widdeningFactor = 2
        minX = minX - int(widdeningFactor * lengthX)
        maxX = maxX + int(widdeningFactor * lengthX)
        minY = minY - int(widdeningFactor * lengthY)
        maxY = maxY + int(widdeningFactor * lengthY)
        
        oneWellManuallyChosenTopLeft     = [minX, minY]
        oneWellManuallyChosenBottomRight = [maxX, maxY]
      else: # Focused on the initial well
        oneWellManuallyChosenTopLeft     = [xtop, ytop]
        oneWellManuallyChosenBottomRight = [xtop + lenX, ytop + lenY]          
      
      data.append({"image": frame, "headCoordinates": headCoordinates, "tailTipCoordinates": tailTipCoordinates, "oneWellManuallyChosenTopLeft": oneWellManuallyChosenTopLeft, "oneWellManuallyChosenBottomRight": oneWellManuallyChosenBottomRight, "frameNumber": k, "wellNumber": wellNumber})

  if saveIntermediary:
    toSave    = [initialConfigFile, videoPath, data, wellPositions, pathToVideo, videoNameWithExt, videoName, videoExt, zebrafishToTrack]
    pickle.dump(toSave, open(videoName + '_paramSet', 'wb'))
    
  cap.release()
  
  return [initialConfigFile, videoPath, data, wellPositions, pathToVideo, videoNameWithExt, videoName, videoExt]


def evaluateMinPixelDiffForBackExtractForCenterOfMassTracking(videoPath, background, image, wellPositions, hyperparameters, tailTipGroundTruth):
  
  [foregroundImage, o1, o2] = getForegroundImage(videoPath, background, image["frameNumber"], image["wellNumber"], wellPositions, hyperparameters)
  ret, thresh = cv2.threshold(foregroundImage, hyperparameters["thresholdForBlobImg"], 255, cv2.THRESH_BINARY)
  thresh[0,:] = 255
  thresh[len(thresh)-1,:] = 255
  thresh[:,0] = 255
  thresh[:,len(thresh[0])-1] = 255
  contourClickedByUser = 0
  contours, hierarchy = cv2.findContours(thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
  tailTipDistError = 1000000000000000
  for contour in contours:
    dist = cv2.pointPolygonTest(contour, (image["headCoordinates"][0], image["headCoordinates"][1]), True)
    if dist >= 0:
      for pt in contour:
        contourToPointOnBorderDistance = math.sqrt((pt[0][0] - tailTipGroundTruth[0])**2 + (pt[0][1] - tailTipGroundTruth[1])**2)
        if contourToPointOnBorderDistance < tailTipDistError:
          tailTipDistError = contourToPointOnBorderDistance
        
  return tailTipDistError

def findBestBackgroundSubstractionParameterForEachImage(data, videoPath, background, wellPositions, hyperparameters, videoName, zebrafishToTrack):
  
  for image in data:
    
    oneWellManuallyChosenTopLeft     = image["oneWellManuallyChosenTopLeft"]
    oneWellManuallyChosenBottomRight = image["oneWellManuallyChosenBottomRight"]
    
    hyperparameters["oneWellManuallyChosenTopLeft"]     = oneWellManuallyChosenTopLeft
    hyperparameters["oneWellManuallyChosenBottomRight"] = oneWellManuallyChosenBottomRight
    hyperparameters["videoWidth"]    = oneWellManuallyChosenBottomRight[0] - oneWellManuallyChosenTopLeft[0]
    hyperparameters["videoHeight"]   = oneWellManuallyChosenBottomRight[1] - oneWellManuallyChosenTopLeft[1]
    
    hyperparameters["firstFrame"]    = image["frameNumber"]
    hyperparameters["lastFrame"]     = image["frameNumber"]
    hyperparameters["debugTracking"] = 0
    
    hyperparameters["fixedHeadPositionX"] = int(image["headCoordinates"][0])
    hyperparameters["fixedHeadPositionY"] = int(image["headCoordinates"][1])
    hyperparameters["midlineIsInBlobTrackingOptimization"] = 0
    
    bestMinPixelDiffForBackExtract = 10
    lowestTailTipDistError = 1000000000
    for minPixelDiffForBackExtract in range(3, 25):
      hyperparameters["minPixelDiffForBackExtract"] = minPixelDiffForBackExtract
      tailTipGroundTruth = image["tailTipCoordinates"]
      if zebrafishToTrack:
        trackingData = tracking(videoPath, background, image["wellNumber"], wellPositions, hyperparameters, videoName)
        tailTipPredicted = trackingData[0][0][0][len(trackingData[0][0][0])-1]
        if (trackingData[0][0][0][0][0] == tailTipPredicted[0] and trackingData[0][0][0][0][1] == tailTipPredicted[1]) or (trackingData[0][0][0][1][0] == tailTipPredicted[0] and trackingData[0][0][0][1][1] == tailTipPredicted[1]):
          tailTipDistError = 1000000000
        else:
          tailTipDistError = math.sqrt((tailTipGroundTruth[0] - tailTipPredicted[0])** 2 + (tailTipGroundTruth[1] - tailTipPredicted[1])**2)
      else:
        tailTipDistError = evaluateMinPixelDiffForBackExtractForCenterOfMassTracking(videoPath, background, image, wellPositions, hyperparameters, tailTipGroundTruth)
      
      if tailTipDistError < lowestTailTipDistError:
        lowestTailTipDistError = tailTipDistError
        bestMinPixelDiffForBackExtract = minPixelDiffForBackExtract
        
        if zebrafishToTrack:
          previousDataPoint = []
          tailLength = 0
          for dataPoint in trackingData[0][0][0]:
            if len(previousDataPoint):
              tailLength = tailLength + math.sqrt((dataPoint[0] - previousDataPoint[0])**2 + (dataPoint[1] - previousDataPoint[1])**2)
            previousDataPoint = dataPoint
          image["tailLength"] = tailLength
          image["tailLengthManual"] = math.sqrt((image["headCoordinates"][0] - tailTipGroundTruth[0])**2 + (image["headCoordinates"][1] - tailTipGroundTruth[1])**2)
      
      print("minPixelDiffForBackExtract:", minPixelDiffForBackExtract, "; tailTipDistError:", tailTipDistError)
    
    image["bestMinPixelDiffForBackExtract"] = bestMinPixelDiffForBackExtract
    image["lowestTailTipDistError"]         = lowestTailTipDistError
    
    if lowestTailTipDistError != 1000000000:
      hyperparameters["minPixelDiffForBackExtract"] = image["bestMinPixelDiffForBackExtract"]
      [foregroundImage, o1, o2] = getForegroundImage(videoPath, background, image["frameNumber"], image["wellNumber"], wellPositions, hyperparameters)
      ret, thresh = cv2.threshold(foregroundImage, hyperparameters["thresholdForBlobImg"], 255, cv2.THRESH_BINARY)
      thresh[0,:] = 255
      thresh[len(thresh)-1,:] = 255
      thresh[:,0] = 255
      thresh[:,len(thresh[0])-1] = 255
      contourClickedByUser = 0
      contours, hierarchy = cv2.findContours(thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
      for contour in contours:
        dist = cv2.pointPolygonTest(contour, (image["headCoordinates"][0], image["headCoordinates"][1]), True)
        if dist >= 0:
          contourClickedByUser = contour
      if not(type(contourClickedByUser) == int): # We found the contour that the user selected
        bodyContourArea = cv2.contourArea(contourClickedByUser)
        image["bodyContourArea"] = bodyContourArea
      else:
        image["bodyContourArea"] = -1
      
    del hyperparameters["fixedHeadPositionX"]
    del hyperparameters["fixedHeadPositionY"]
    del hyperparameters["midlineIsInBlobTrackingOptimization"]
  
  return data


def findInitialBlobArea(data, videoPath, background, wellPositions, hyperparameters, maxTailLengthManual):
  
  for image in data:
    
    if image["lowestTailTipDistError"] != 1000000000 and image["bodyContourArea"] and (not("tailLength" in image) or (image["tailLength"] < 10 * maxTailLengthManual)):
      
      bodyContourArea = image["bodyContourArea"]
      
      [foregroundImage, o1, o2] = getForegroundImage(videoPath, background, image["frameNumber"], image["wellNumber"], wellPositions, hyperparameters)
      
      ret, thresh = cv2.threshold(foregroundImage, hyperparameters["thresholdForBlobImg"], 255, cv2.THRESH_BINARY)
      thresh[0,:] = 255
      thresh[len(thresh)-1,:] = 255
      thresh[:,0] = 255
      thresh[:,len(thresh[0])-1] = 255
      contourClickedByUser = 0
      contours, hierarchy = cv2.findContours(thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
      for contour in contours:
        dist = cv2.pointPolygonTest(contour, (image["headCoordinates"][0], image["headCoordinates"][1]), True)
        if dist >= 0:
          contourClickedByUser = contour
      
      if not(type(contourClickedByUser) == int): # We found the contour that the user selected
        
        image["contourClickedByUser"] = contourClickedByUser
        image["headContourArea"] = cv2.contourArea(contourClickedByUser)
  
  return data


def boutDetectionParameters(data, configFile, pathToVideo, videoName, videoExt, wellPositions, videoPath):

  # Extracting Background and finding Wells
  
  configFile["exitAfterBackgroundExtraction"] = 1
  configFile["debugExtractBack"]              = 1
  configFile["debugFindWells"]                = 1
  
  WINDOW_NAME = "Please Wait"
  cvui.init(WINDOW_NAME)
  cv2.moveWindow(WINDOW_NAME, 0,0)
  img = np.zeros((400, 900, 3), np.uint8)
  lineType               = 2
  img = cv2.putText(img,'In the next window, you will need to adjust parameters in order', (5, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,255), lineType)
  cv2.putText(img,'for the red dot to appear when and only when the animal is moving.', (5, 150), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,255), lineType)
  cv2.imshow(WINDOW_NAME, img)
  r = cv2.waitKey(10)
  
  try:
    mainZZ(pathToVideo, videoName, videoExt, configFile, [])
  except ValueError:
    configFile["exitAfterBackgroundExtraction"] = 0
  
  cv2.destroyAllWindows()
  
  del configFile["exitAfterBackgroundExtraction"]
  del configFile["debugExtractBack"]
  del configFile["debugFindWells"]

  # Finding the frame with the most movement
  
  cap   = cv2.VideoCapture(videoPath)
  max_l = int(cap.get(7))
  
  wellNumber = data[0]["wellNumber"]
  xtop = wellPositions[wellNumber]['topLeftX']
  ytop = wellPositions[wellNumber]['topLeftY']
  lenX = wellPositions[wellNumber]['lengthX']
  lenY = wellPositions[wellNumber]['lengthY']
  
  print("xtop, ytop, lenX, lenY:", xtop, ytop, lenX, lenY)
  
  firstFrameNum  = 0
  lastFrameNum   = max_l - 1
  
  while abs(lastFrameNum - firstFrameNum) > 40:
    
    middleFrameNum = int((firstFrameNum + lastFrameNum) / 2)
    
    cap.set(1, firstFrameNum)
    ret, firstFrame = cap.read()
    firstFrame = cv2.cvtColor(firstFrame, cv2.COLOR_BGR2GRAY)
    
    cap.set(1, middleFrameNum)
    ret, middleFrame = cap.read()
    middleFrame = cv2.cvtColor(middleFrame, cv2.COLOR_BGR2GRAY)
    
    cap.set(1, lastFrameNum)
    ret, lastFrame = cap.read()
    lastFrame = cv2.cvtColor(lastFrame, cv2.COLOR_BGR2GRAY)
    
    firstFrameROI  = firstFrame[ytop:ytop+lenY, xtop:xtop+lenX]
    middleFrameROI = middleFrame[ytop:ytop+lenY, xtop:xtop+lenX]
    lastFrameROI   = lastFrame[ytop:ytop+lenY, xtop:xtop+lenX]
    pixelsChangeFirstToMiddle = np.sum(abs(firstFrameROI-middleFrameROI))
    pixelsChangeMiddleToLast  = np.sum(abs(middleFrameROI-lastFrameROI))
    
    if pixelsChangeFirstToMiddle > pixelsChangeMiddleToLast:
      lastFrameNum  = middleFrameNum
    else:
      firstFrameNum = middleFrameNum
    
    print("intermediary: firstFrameNum:", firstFrameNum, "; lastFrameNum:", lastFrameNum)
    print("pixelsChangeFirstToMiddle:", pixelsChangeFirstToMiddle, "; pixelsChangeMiddleToLast:", pixelsChangeMiddleToLast)
    
  cap.release()
  
  print("wellNumber:", wellNumber, "; lastFrameNum:", lastFrameNum, "; firstFrameNum:", firstFrameNum)
  
  # Launching the interactive adjustement of hyperparameters related to the detection of bouts
  
  wellNumber = str(data[0]["wellNumber"])
  firstFrameParamAdjust = 0
  adjustOnWholeVideo    = 0
  
  [configFile, initialFirstFrameValue, initialLastFrameValue] = prepareConfigFileForParamsAdjustements(configFile, wellNumber, firstFrameParamAdjust, videoPath, adjustOnWholeVideo)
  configFile["firstFrame"] = lastFrameNum - 500 if lastFrameNum - 500 > 0 else 0
  configFile["lastFrame"]  = (configFile["firstFrame"] + 500) if (configFile["firstFrame"] + 500) < (max_l - 1) else (max_l - 1)
  
  configFile["noBoutsDetection"] = 0
  configFile["trackTail"]                   = 0
  configFile["adjustDetectMovWithRawVideo"] = 1
  configFile["reloadWellPositions"]         = 1
  
  if "thresForDetectMovementWithRawVideo" in configFile:
    if configFile["thresForDetectMovementWithRawVideo"] == 0:
      configFile["thresForDetectMovementWithRawVideo"] = 1
  else:
    configFile["thresForDetectMovementWithRawVideo"] = 1
  
  try:
    WINDOW_NAME = "Please Wait"
    cvui.init(WINDOW_NAME)
    cv2.moveWindow(WINDOW_NAME, 0,0)
    img = np.zeros((400, 900, 3), np.uint8)
    lineType               = 2
    img = cv2.putText(img,'In the next window, you will need to adjust parameters in order', (5, 100), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,255), lineType)
    cv2.putText(img,'for the red dot to appear when and only when the animal is moving.', (5, 150), cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255,255,255), lineType)
    cv2.imshow(WINDOW_NAME, img)
    r = cv2.waitKey(10)
    mainZZ(pathToVideo, videoName, videoExt, configFile, [])
    cv2.destroyAllWindows()
  except ValueError:
    newhyperparameters = pickle.load(open('newhyperparameters', 'rb'))
    for index in newhyperparameters:
      configFile[index] = newhyperparameters[index]
  
  del configFile["onlyTrackThisOneWell"]
  del configFile["trackTail"]
  del configFile["adjustDetectMovWithRawVideo"]
  del configFile["reloadWellPositions"]
  
  if initialLastFrameValue == -1:
    if 'firstFrame' in configFile:
      del configFile['firstFrame']
    if 'lastFrame' in configFile:
      del configFile['lastFrame']
  else:
    configFile["firstFrame"]                  = initialFirstFrameValue
    configFile["lastFrame"]                   = initialLastFrameValue
  
  del configFile["reloadBackground"]
  
  configFile["fillGapFrameNb"] = 2 # We would need to try to improve this in the future
  
  return configFile
