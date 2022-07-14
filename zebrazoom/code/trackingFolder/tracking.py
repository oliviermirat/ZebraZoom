import h5py
import numpy as np
import cv2
import zebrazoom.videoFormatConversion.zzVideoReading as zzVideoReading
import math
import os
import queue

from zebrazoom.code.trackingFolder.getImages import getImages
from zebrazoom.code.trackingFolder.headTrackingHeadingCalculationFolder.headTrackingHeadingCalculation import headTrackingHeadingCalculation
from zebrazoom.code.trackingFolder.debugTracking import debugTracking
from zebrazoom.code.trackingFolder.tailTracking import tailTracking
from zebrazoom.code.trackingFolder.blackFramesDetection import getThresForBlackFrame, savingBlackFrames
from zebrazoom.code.trackingFolder.tailTrackingFunctionsFolder.getTailTipManual import getHeadPositionByFileSaved, findTailTipByUserInput, getTailTipByFileSaved, findHeadPositionByUserInput, getAccentuateFrameForManualPointSelect
from zebrazoom.code.trackingFolder.eyeTracking.eyeTracking import eyeTracking, eyeTrackingHeadEmbedded
from zebrazoom.code.trackingFolder.postProcessMultipleTrajectories import postProcessMultipleTrajectories

from zebrazoom.code.getImage.headEmbededFrame import headEmbededFrame
from zebrazoom.code.getImage.headEmbededFrameBackExtract import headEmbededFrameBackExtract

from zebrazoom.code.adjustHyperparameters import adjustHeadEmbededTrackingParams, adjustFreelySwimTrackingParams, adjustFreelySwimTrackingAutoParams
from zebrazoom.code.trackingFolder.tailTrackingFunctionsFolder.headEmbededTailTracking import adjustHeadEmbededHyperparameters

from zebrazoom.code.trackingFolder.tailTrackingFunctionsFolder.headEmbededTailTracking import headEmbededTailTrackFindMaxDepth
from zebrazoom.code.trackingFolder.tailTrackingFunctionsFolder.headEmbededTailTrackingTeresaNicolson import headEmbededTailTrackFindMaxDepthTeresaNicolson, headEmbededTailTrackingTeresaNicolson
from zebrazoom.code.trackingFolder.tailTrackingFunctionsFolder.centerOfMassTailTracking import centerOfMassTailTrackFindMaxDepth

from zebrazoom.code.trackingFolder.trackingFunctions import addBlackLineToImgSetParameters


def tracking(videoPath, background, wellNumber, wellPositions, hyperparameters, videoName, dlModel=0):
  
  if hyperparameters["trackingDL"]:
    import torch
    from zebrazoom.code.deepLearningFunctions.trackingDL import trackingDL
    device = torch.device('cuda') if torch.cuda.is_available() else torch.device('cpu')
    [trackingHeadTailAllAnimals, trackingHeadingAllAnimals, trackingEyesAllAnimals, headPositionFirstFrame, tailTipFirstFrame] = trackingDL(videoPath, wellNumber, wellPositions, hyperparameters, videoName, dlModel, device)
    return [trackingHeadTailAllAnimals, trackingHeadingAllAnimals, trackingEyesAllAnimals, headPositionFirstFrame, tailTipFirstFrame]
  
  if hyperparameters["fishTailTrackingDifficultBackground"]:
    from zebrazoom.code.trackingFolder.fishTailTrackingDifficultBackground import fishTailTrackingDifficultBackground
    [trackingHeadTailAllAnimals, trackingHeadingAllAnimals, trackingEyesAllAnimals] = fishTailTrackingDifficultBackground(videoPath, wellNumber, wellPositions, hyperparameters, videoName)
    return [trackingHeadTailAllAnimals, trackingHeadingAllAnimals, trackingEyesAllAnimals, 0, 0]
  
  firstFrame = hyperparameters["firstFrame"]
  if hyperparameters["firstFrameForTracking"] != -1:
    firstFrame = hyperparameters["firstFrameForTracking"]
  lastFrame = hyperparameters["lastFrame"]
  
  if (hyperparameters["freqAlgoPosFollow"] != 0):
    print("lastFrame:",lastFrame)

  nbTailPoints = hyperparameters["nbTailPoints"]
  thetaDiffAccept = 1.2 # 0.5 for the head embedded maybe
  maxDepth = 0
  headPositionFirstFrame = []
  tailTipFirstFrame = []
  
  cap = zzVideoReading.VideoCapture(videoPath)
  if (cap.isOpened()== False): 
    print("Error opening video stream or file")
  frame_width  = int(cap.get(3))
  frame_height = int(cap.get(4))
  
  heading = -1
  if hyperparameters["headEmbeded"]:
    heading = 0.7
    
  trackingHeadTailAllAnimals = np.zeros((hyperparameters["nbAnimalsPerWell"], lastFrame-firstFrame+1, nbTailPoints, 2))
  trackingHeadingAllAnimals = np.zeros((hyperparameters["nbAnimalsPerWell"], lastFrame-firstFrame+1))
  if hyperparameters["eyeTracking"]:
    trackingEyesAllAnimals = np.zeros((hyperparameters["nbAnimalsPerWell"], lastFrame-firstFrame+1, 8))
  else:
    trackingEyesAllAnimals = 0
  
  if not(hyperparameters["nbAnimalsPerWell"] > 1 or hyperparameters["forceBlobMethodForHeadTracking"]) and not(hyperparameters["headEmbeded"]) and (hyperparameters["findHeadPositionByUserInput"] == 0) and (hyperparameters["takeTheHeadClosestToTheCenter"] == 0):
    trackingProbabilityOfGoodDetection = np.zeros((hyperparameters["nbAnimalsPerWell"], lastFrame-firstFrame+1))
  else:
    trackingProbabilityOfGoodDetection = 0
  
  if hyperparameters["detectMovementWithRawVideoInsideTracking"]:
    previousFrames   = queue.Queue(hyperparameters["frameGapComparision"])
    previousXYCoords = queue.Queue(hyperparameters["frameGapComparision"])
    auDessusPerAnimalId = [np.zeros((lastFrame-firstFrame+1, 1)) for nbAnimalsPerWell in range(0, hyperparameters["nbAnimalsPerWell"])]
  
  threshForBlackFrames = getThresForBlackFrame(hyperparameters, videoPath) # For headEmbededTeresaNicolson 
  cap.set(1, firstFrame)
  
  # Using the first frame of the video to calculate parameters that will be used afterwards for the tracking
  if (hyperparameters["headEmbeded"] == 1):
    # Getting images
    
    if hyperparameters["headEmbededRemoveBack"] == 0 and hyperparameters["headEmbededAutoSet_BackgroundExtractionOption"] == 0:
      [frame, thresh1] = headEmbededFrame(videoPath, firstFrame, wellNumber, wellPositions, hyperparameters)
    else:
      hyperparameters["headEmbededRemoveBack"] = 1
      hyperparameters["minPixelDiffForBackExtract"] = hyperparameters["headEmbededAutoSet_BackgroundExtractionOption"]
      [frame, thresh1] = headEmbededFrameBackExtract(videoPath, background, hyperparameters, firstFrame, wellNumber, wellPositions)
    
    # Setting hyperparameters in order to add line on image
    if hyperparameters["addBlackLineToImg_Width"]:
      hyperparameters = addBlackLineToImgSetParameters(hyperparameters, frame, videoName)
    
    # (x, y) coordinates for both eyes for head embedded fish eye tracking
    if hyperparameters["eyeTracking"] and hyperparameters["headEmbeded"] == 1:
      forEye = getAccentuateFrameForManualPointSelect(frame, hyperparameters)
      if True:
        from PyQt5.QtWidgets import QApplication

        import zebrazoom.code.util as util

        leftEyeCoordinate = list(util.getPoint(np.uint8(forEye * 255), "Click on the center of the left eye", zoomable=True, dialog=not hasattr(QApplication.instance(), 'window')))
        rightEyeCoordinate = list(util.getPoint(np.uint8(forEye * 255), "Click on the center of the right eye", zoomable=True, dialog=not hasattr(QApplication.instance(), 'window')))
      else:
        leftEyeCoordinate  = [261, 201] # [267, 198] # [210, 105]
        rightEyeCoordinate = [285, 157] # [290, 151] # [236, 72]
      print("leftEyeCoordinate:", leftEyeCoordinate)
      print("rightEyeCoordinate:", rightEyeCoordinate)
    
    # if hyperparameters["invertBlackWhiteOnImages"]:
      # frame   = 255 - frame
    
    gray = frame.copy()
    
    oppHeading = (heading + math.pi) % (2 * math.pi)
    
    # Getting headPositionFirstFrame and tailTipFirstFrame positions
    if os.path.exists(videoPath+'HP.csv'):
      headPositionFirstFrame = getHeadPositionByFileSaved(videoPath)
    else:
      if hyperparameters["findHeadPositionByUserInput"]:
        frameForManualPointSelection = getAccentuateFrameForManualPointSelect(frame, hyperparameters)
        headPositionFirstFrame = findHeadPositionByUserInput(frameForManualPointSelection, firstFrame, videoPath, hyperparameters, wellNumber, wellPositions)
      else:
        [frame, gray, thresh1, blur, thresh2, frame2, initialCurFrame, back, xHead, yHead] = getImages(hyperparameters, cap, videoPath, firstFrame, background, wellNumber, wellPositions)
        cap.set(1, firstFrame)
        [trackingHeadingAllAnimals, trackingHeadTailAllAnimals, trackingProbabilityOfGoodDetection, lastFirstTheta] = headTrackingHeadingCalculation(hyperparameters, firstFrame, firstFrame, blur, thresh1, thresh2, gray, hyperparameters["erodeSize"], frame_width, frame_height, trackingHeadingAllAnimals, trackingHeadTailAllAnimals, trackingProbabilityOfGoodDetection, headPositionFirstFrame, wellPositions[wellNumber]["lengthX"])
    if os.path.exists(videoPath+'.csv'):
      tailTipFirstFrame  = getTailTipByFileSaved(hyperparameters,videoPath)
    else:
      frameForManualPointSelection = getAccentuateFrameForManualPointSelect(frame, hyperparameters)
      tailTipFirstFrame  = findTailTipByUserInput(frameForManualPointSelection, firstFrame, videoPath, hyperparameters, wellNumber, wellPositions)
    if hyperparameters["automaticallySetSomeOfTheHeadEmbededHyperparameters"] == 1:
      hyperparameters = adjustHeadEmbededHyperparameters(hyperparameters, frame, headPositionFirstFrame, tailTipFirstFrame)
    # Getting max depth
    if hyperparameters["headEmbededTeresaNicolson"] == 1:
      if len(headPositionFirstFrame) == 0:
        headPositionFirstFrame = [trackingHeadTailAllAnimals[0][0][0][0], trackingHeadTailAllAnimals[0][0][0][1]]
      maxDepth = headEmbededTailTrackFindMaxDepthTeresaNicolson(headPositionFirstFrame,nbTailPoints,firstFrame,headPositionFirstFrame[0],headPositionFirstFrame[1],thresh1,frame,hyperparameters,oppHeading,tailTipFirstFrame)
    else:
      if hyperparameters["centerOfMassTailTracking"] == 0:
        maxDepth = headEmbededTailTrackFindMaxDepth(headPositionFirstFrame,nbTailPoints,firstFrame,headPositionFirstFrame[0],headPositionFirstFrame[1],thresh1,frame,hyperparameters,oppHeading,tailTipFirstFrame)
      else:
        maxDepth = centerOfMassTailTrackFindMaxDepth(headPositionFirstFrame,nbTailPoints,firstFrame,headPositionFirstFrame[0],headPositionFirstFrame[1],thresh1,frame,hyperparameters,oppHeading,tailTipFirstFrame)
  
  if hyperparameters["adjustHeadEmbededTracking"] == 1 or hyperparameters["adjustFreelySwimTracking"] == 1 or hyperparameters["adjustFreelySwimTrackingAutomaticParameters"] == 1 or hyperparameters["adjustHeadEmbeddedEyeTracking"]:
    widgets = None
  
  # Performing the tracking on each frame
  i = firstFrame
  if int(hyperparameters["onlyDoTheTrackingForThisNumberOfFrames"]) != 0:
    lastFrame = min(lastFrame, firstFrame + int(hyperparameters["onlyDoTheTrackingForThisNumberOfFrames"]))
  while (i < lastFrame+1):
    
    if (hyperparameters["freqAlgoPosFollow"] != 0) and (i % hyperparameters["freqAlgoPosFollow"] == 0):
      print("Tracking: wellNumber:",wellNumber," ; frame:",i)
      if hyperparameters["popUpAlgoFollow"]:
        from zebrazoom.code.popUpAlgoFollow import prepend
        prepend("Tracking: wellNumber:" + str(wellNumber) + " ; frame:" + str(i))
    if hyperparameters["debugTracking"]:
      print("frame:",i)
    # Get images for frame i
    [frame, gray, thresh1, blur, thresh2, frame2, initialCurFrame, back, xHead, yHead] = getImages(hyperparameters, cap, videoPath, i, background, wellNumber, wellPositions, 0, trackingHeadTailAllAnimals)
    # Head tracking and heading calculation
    [trackingHeadingAllAnimals, trackingHeadTailAllAnimals, trackingProbabilityOfGoodDetection, lastFirstTheta] = headTrackingHeadingCalculation(hyperparameters, firstFrame, i, blur, thresh1, thresh2, gray, hyperparameters["erodeSize"], frame_width, frame_height, trackingHeadingAllAnimals, trackingHeadTailAllAnimals, trackingProbabilityOfGoodDetection, headPositionFirstFrame, wellPositions[wellNumber]["lengthX"], xHead, yHead)
    # Tail tracking for frame i
    if hyperparameters["trackTail"] == 1 :
      for animalId in range(0, hyperparameters["nbAnimalsPerWell"]):
        [trackingHeadTailAllAnimals, trackingHeadingAllAnimals] = tailTracking(animalId, i, firstFrame, videoPath, frame, hyperparameters, thresh1, nbTailPoints, threshForBlackFrames, thetaDiffAccept, trackingHeadTailAllAnimals, trackingHeadingAllAnimals, lastFirstTheta, maxDepth, tailTipFirstFrame, initialCurFrame, back, wellNumber, xHead, yHead)
    # Eye tracking for frame i
    if hyperparameters["eyeTracking"]:
      if hyperparameters["headEmbeded"] == 1:
        if hyperparameters["adjustHeadEmbeddedEyeTracking"]:
          i, widgets = eyeTrackingHeadEmbedded(animalId, i, firstFrame, frame, hyperparameters, thresh1, trackingHeadingAllAnimals, trackingHeadTailAllAnimals, trackingEyesAllAnimals, leftEyeCoordinate, rightEyeCoordinate, widgets=widgets)
          if not hyperparameters["eyeFilterKernelSize"] % 2:
            hyperparameters["eyeFilterKernelSize"] -= 1
          continue
        else:
          trackingEyesAllAnimals = eyeTrackingHeadEmbedded(animalId, i, firstFrame, frame, hyperparameters, thresh1, trackingHeadingAllAnimals, trackingHeadTailAllAnimals, trackingEyesAllAnimals, leftEyeCoordinate, rightEyeCoordinate)
      else:
        trackingEyesAllAnimals = eyeTracking(animalId, i, firstFrame, frame, hyperparameters, thresh1, trackingHeadingAllAnimals, trackingHeadTailAllAnimals, trackingEyesAllAnimals)
    
    # Debug functions
    if hyperparameters["nbAnimalsPerWell"] > 1 or hyperparameters["forceBlobMethodForHeadTracking"] or hyperparameters["headEmbeded"] == 1 or hyperparameters["fixedHeadPositionX"] != -1:
      debugTracking(nbTailPoints, i, firstFrame, trackingHeadTailAllAnimals, trackingHeadingAllAnimals, frame, hyperparameters)
    else:
      debugTracking(nbTailPoints, i, firstFrame, trackingHeadTailAllAnimals, trackingHeadingAllAnimals, frame, hyperparameters)
    # DetectMovementWithRawVideoInsideTracking
    if hyperparameters["detectMovementWithRawVideoInsideTracking"]:
        halfDiameterRoiBoutDetect = hyperparameters["halfDiameterRoiBoutDetect"]
        if previousFrames.full():
          previousFrame   = previousFrames.get()
          curFrame        = initialCurFrame.copy()
          previousXYCoord = previousXYCoords.get()
          curXYCoord      = [xHead, yHead]
          if previousXYCoord[0] < curXYCoord[0]:
            previousFrame = previousFrame[:, (curXYCoord[0]-previousXYCoord[0]):]
          elif previousXYCoord[0] > curXYCoord[0]:
            curFrame      = curFrame[:, (previousXYCoord[0]-curXYCoord[0]):]
          if previousXYCoord[1] < curXYCoord[1]:
            previousFrame = previousFrame[(curXYCoord[1]-previousXYCoord[1]):, :]
          elif previousXYCoord[1] > curXYCoord[1]:
            curFrame      = curFrame[(previousXYCoord[1]-curXYCoord[1]):, :]
          maxX = min(len(previousFrame[0]), len(curFrame[0]))
          maxY = min(len(previousFrame), len(curFrame))
          
          previousFrame = previousFrame[:maxY, :maxX]
          curFrame      = curFrame[:maxY, :maxX]
          
          # Possible optimization in the future: refine the ROI based on halfDiameterRoiBoutDetect !!!
          
          res = cv2.absdiff(previousFrame, curFrame)
          ret, res = cv2.threshold(res,hyperparameters["thresForDetectMovementWithRawVideo"],255,cv2.THRESH_BINARY)
          
          totDiff = cv2.countNonZero(res)
          for animalId in range(0, hyperparameters["nbAnimalsPerWell"]):
            if totDiff > hyperparameters["minNbPixelForDetectMovementWithRawVideo"]:
              auDessusPerAnimalId[animalId][i-firstFrame] = 1
            else:
              auDessusPerAnimalId[animalId][i-firstFrame] = 0
        else:
          auDessusPerAnimalId[animalId][i-firstFrame] = 0
        previousFrames.put(initialCurFrame)
        previousXYCoords.put([xHead, yHead])
    
    if hyperparameters["trackOnlyOnROI_halfDiameter"]:
      if not(xHead == 0 and yHead == 0):
        for animalId in range(0, hyperparameters["nbAnimalsPerWell"]):
          for j in range(0, len(trackingHeadTailAllAnimals[animalId][i-firstFrame])): # Head Position should already shifted, only shifting tail positions now
            trackingHeadTailAllAnimals[animalId][i-firstFrame][j][0] = trackingHeadTailAllAnimals[animalId][i-firstFrame][j][0] + xHead
            trackingHeadTailAllAnimals[animalId][i-firstFrame][j][1] = trackingHeadTailAllAnimals[animalId][i-firstFrame][j][1] + yHead
    
    if hyperparameters["adjustHeadEmbededTracking"] == 1:
      i, widgets = adjustHeadEmbededTrackingParams(nbTailPoints, i, firstFrame, trackingHeadTailAllAnimals, trackingHeadingAllAnimals, frame, frame2, hyperparameters, widgets)
      hyperparameters = adjustHeadEmbededHyperparameters(hyperparameters, frame, headPositionFirstFrame, tailTipFirstFrame)
    elif hyperparameters["adjustFreelySwimTracking"] == 1:
      i, widgets = adjustFreelySwimTrackingParams(nbTailPoints, i, firstFrame, trackingHeadTailAllAnimals, trackingHeadingAllAnimals, frame, frame2, hyperparameters, widgets)
    elif hyperparameters["adjustFreelySwimTrackingAutomaticParameters"] == 1:
      # Preparing image to show
      if hyperparameters["recalculateForegroundImageBasedOnBodyArea"] == 1:
        minPixelDiffForBackExtract = hyperparameters["minPixelDiffForBackExtractBody"]
      else:
        if hyperparameters["adjustMinPixelDiffForBackExtract_nbBlackPixelsMax"]:
          minPixelDiffForBackExtract = hyperparameters["minPixelDiffForBackExtractHead"]
          del hyperparameters["minPixelDiffForBackExtractHead"] # Not sure why this is necessary: need to check the code to make sure there isn't a bug somewhere
        else:
          minPixelDiffForBackExtract = hyperparameters["minPixelDiffForBackExtract"]
      curFrame = initialCurFrame
      putToWhite = (curFrame.astype('int32') >= (back.astype('int32') - minPixelDiffForBackExtract) )
      curFrame[putToWhite] = 255
      ret, frame2 = cv2.threshold(curFrame, hyperparameters["thresholdForBlobImg"], 255, cv2.THRESH_BINARY)
      # Showing current image and waiting for next parameter/frame change
      i, widgets = adjustFreelySwimTrackingAutoParams(nbTailPoints, i, firstFrame, trackingHeadTailAllAnimals, trackingHeadingAllAnimals, frame, frame2, hyperparameters, widgets)
      # Puts hyperparameters values to accepted values
      hyperparameters["recalculateForegroundImageBasedOnBodyArea"] = 0 if hyperparameters["recalculateForegroundImageBasedOnBodyArea"] < 0.5 else 1
      if hyperparameters["adjustMinPixelDiffForBackExtract_nbBlackPixelsMax"] < 0:
        hyperparameters["adjustMinPixelDiffForBackExtract_nbBlackPixelsMax"] = 0
      if hyperparameters["minPixelDiffForBackExtract"] < 0:
        hyperparameters["minPixelDiffForBackExtract"] = 0
      else:
        if hyperparameters["minPixelDiffForBackExtract"] > 255:
          hyperparameters["minPixelDiffForBackExtract"] = 255
      hyperparameters["minPixelDiffForBackExtract"] = int(hyperparameters["minPixelDiffForBackExtract"])
      
    else:
      i = i + 1
  
  if hyperparameters["postProcessMultipleTrajectories"]:
    [trackingHeadingAllAnimals, trackingHeadTailAllAnimals, trackingEyesAllAnimals] = postProcessMultipleTrajectories(trackingHeadingAllAnimals, trackingHeadTailAllAnimals, trackingEyesAllAnimals, trackingProbabilityOfGoodDetection, hyperparameters, wellPositions)
  
  savingBlackFrames(hyperparameters, videoName, trackingHeadTailAllAnimals)
  
  print("Tracking done for well", wellNumber)
  if hyperparameters["popUpAlgoFollow"]:
    from zebrazoom.code.popUpAlgoFollow import prepend
    prepend("Tracking done for well "+ str(wellNumber))
  
  if hyperparameters["detectMovementWithRawVideoInsideTracking"]:
    return [trackingHeadTailAllAnimals, trackingHeadingAllAnimals, trackingEyesAllAnimals, headPositionFirstFrame, tailTipFirstFrame, auDessusPerAnimalId]
  else:
    return [trackingHeadTailAllAnimals, trackingHeadingAllAnimals, trackingEyesAllAnimals, headPositionFirstFrame, tailTipFirstFrame]
