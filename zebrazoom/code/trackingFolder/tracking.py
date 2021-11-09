import h5py
import numpy as np
import cv2
import zebrazoom.videoFormatConversion.zzVideoReading as zzVideoReading
from zebrazoom.code.popUpAlgoFollow import prepend
import math
import os

from zebrazoom.code.trackingFolder.getImages import getImages
from zebrazoom.code.trackingFolder.headTrackingHeadingCalculationFolder.headTrackingHeadingCalculation import headTrackingHeadingCalculation
from zebrazoom.code.trackingFolder.debugTracking import debugTracking
from zebrazoom.code.trackingFolder.tailTracking import tailTracking
from zebrazoom.code.trackingFolder.blackFramesDetection import getThresForBlackFrame, savingBlackFrames
from zebrazoom.code.trackingFolder.tailTrackingFunctionsFolder.getTailTipManual import getHeadPositionByFileSaved, findTailTipByUserInput, getTailTipByFileSaved, findHeadPositionByUserInput, getAccentuateFrameForManualPointSelect
from zebrazoom.code.trackingFolder.eyeTracking.eyeTracking import eyeTracking
from zebrazoom.code.trackingFolder.postProcessMultipleTrajectories import postProcessMultipleTrajectories

from zebrazoom.code.getImage.headEmbededFrame import headEmbededFrame
from zebrazoom.code.getImage.headEmbededFrameBackExtract import headEmbededFrameBackExtract

from zebrazoom.code.adjustHyperparameters import initializeAdjustHyperparametersWindows, adjustHyperparameters, getHeadEmbededTrackingParamsForHyperParamAdjusts, getFreelySwimTrackingParamsForHyperParamAdjusts, getFreelySwimTrackingAutoParamsForHyperParamAdjusts
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
  
  threshForBlackFrames = getThresForBlackFrame(hyperparameters, videoPath) # For headEmbededTeresaNicolson 
  cap.set(1, firstFrame)
  
  # Using the first frame of the video to calculate parameters that will be used afterwards for the tracking
  if (hyperparameters["headEmbeded"] == 1):
    # Getting images
    
    if hyperparameters["headEmbededRemoveBack"] == 0 and hyperparameters["headEmbededAutoSet_BackgroundExtractionOption"] == 0:
      [frame, thresh1] = headEmbededFrame(videoPath, firstFrame, hyperparameters)
    else:
      hyperparameters["headEmbededRemoveBack"] = 1
      hyperparameters["minPixelDiffForBackExtract"] = hyperparameters["headEmbededAutoSet_BackgroundExtractionOption"]
      [frame, thresh1] = headEmbededFrameBackExtract(videoPath, background, hyperparameters, firstFrame)
    
    # Setting hyperparameters in order to add line on image
    if hyperparameters["addBlackLineToImg_Width"]:
      hyperparameters = addBlackLineToImgSetParameters(hyperparameters, frame)
    
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
        headPositionFirstFrame = findHeadPositionByUserInput(frameForManualPointSelection, firstFrame, videoPath)
      else:
        [frame, gray, thresh1, blur, thresh2, frame2, initialCurFrame, back] = getImages(hyperparameters, cap, videoPath, firstFrame, background, wellNumber, wellPositions)
        cap.set(1, firstFrame)
        [trackingHeadingAllAnimals, trackingHeadTailAllAnimals, trackingProbabilityOfGoodDetection, lastFirstTheta] = headTrackingHeadingCalculation(hyperparameters, firstFrame, firstFrame, blur, thresh1, thresh2, gray, hyperparameters["erodeSize"], frame_width, frame_height, trackingHeadingAllAnimals, trackingHeadTailAllAnimals, trackingProbabilityOfGoodDetection, headPositionFirstFrame, wellPositions[wellNumber]["lengthX"])
    if os.path.exists(videoPath+'.csv'):
      tailTipFirstFrame  = getTailTipByFileSaved(hyperparameters,videoPath)
    else:
      frameForManualPointSelection = getAccentuateFrameForManualPointSelect(frame, hyperparameters)
      tailTipFirstFrame  = findTailTipByUserInput(frameForManualPointSelection, firstFrame, videoPath, hyperparameters)
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
  
  if hyperparameters["adjustHeadEmbededTracking"] == 1 or hyperparameters["adjustFreelySwimTracking"] == 1 or hyperparameters["adjustFreelySwimTrackingAutomaticParameters"] == 1:
    initializeAdjustHyperparametersWindows("Tracking")
  organizationTabCur = []
  
  # Performing the tracking on each frame
  i = firstFrame
  if int(hyperparameters["onlyDoTheTrackingForThisNumberOfFrames"]) != 0:
    lastFrame = min(lastFrame, firstFrame + int(hyperparameters["onlyDoTheTrackingForThisNumberOfFrames"]))
  while (i < lastFrame+1):
    
    if (hyperparameters["freqAlgoPosFollow"] != 0) and (i % hyperparameters["freqAlgoPosFollow"] == 0):
      print("Tracking: wellNumber:",wellNumber," ; frame:",i)
      if hyperparameters["popUpAlgoFollow"]:
        prepend("Tracking: wellNumber:" + str(wellNumber) + " ; frame:" + str(i))
    if hyperparameters["debugTracking"]:
      print("frame:",i)
    # Get images for frame i
    [frame, gray, thresh1, blur, thresh2, frame2, initialCurFrame, back] = getImages(hyperparameters, cap, videoPath, i, background, wellNumber, wellPositions)
    # Head tracking and heading calculation
    [trackingHeadingAllAnimals, trackingHeadTailAllAnimals, trackingProbabilityOfGoodDetection, lastFirstTheta] = headTrackingHeadingCalculation(hyperparameters, firstFrame, i, blur, thresh1, thresh2, gray, hyperparameters["erodeSize"], frame_width, frame_height, trackingHeadingAllAnimals, trackingHeadTailAllAnimals, trackingProbabilityOfGoodDetection, headPositionFirstFrame, wellPositions[wellNumber]["lengthX"])
    # Tail tracking for frame i
    if hyperparameters["trackTail"] == 1 :
      for animalId in range(0, hyperparameters["nbAnimalsPerWell"]):
        [trackingHeadTailAllAnimals, trackingHeadingAllAnimals] = tailTracking(animalId, i, firstFrame, videoPath, frame, hyperparameters, thresh1, nbTailPoints, threshForBlackFrames, thetaDiffAccept, trackingHeadTailAllAnimals, trackingHeadingAllAnimals, lastFirstTheta, maxDepth, tailTipFirstFrame, initialCurFrame, back, wellNumber)
    # Eye tracking for frame i
    if hyperparameters["eyeTracking"]:
      trackingEyesAllAnimals = eyeTracking(animalId, i, firstFrame, frame, hyperparameters, thresh1, trackingHeadingAllAnimals, trackingHeadTailAllAnimals, trackingEyesAllAnimals)
    # Debug functions
    if hyperparameters["nbAnimalsPerWell"] > 1 or hyperparameters["forceBlobMethodForHeadTracking"] or hyperparameters["headEmbeded"] == 1 or hyperparameters["fixedHeadPositionX"] != -1:
      debugTracking(nbTailPoints, i, firstFrame, trackingHeadTailAllAnimals, trackingHeadingAllAnimals, frame2, hyperparameters)
    else:
      debugTracking(nbTailPoints, i, firstFrame, trackingHeadTailAllAnimals, trackingHeadingAllAnimals, blur, hyperparameters)
    
    if hyperparameters["adjustHeadEmbededTracking"] == 1:
      [hyperparametersListNames, frameToShow, WINDOW_NAME, organizationTab] = getHeadEmbededTrackingParamsForHyperParamAdjusts(nbTailPoints, i, firstFrame, trackingHeadTailAllAnimals, trackingHeadingAllAnimals, frame, frame2, hyperparameters)
      if len(organizationTabCur) == 0:
        organizationTabCur = organizationTab
      [i, hyperparameters, organizationTabCur] = adjustHyperparameters(i, hyperparameters, hyperparametersListNames, frameToShow, WINDOW_NAME, organizationTabCur)
      hyperparameters = adjustHeadEmbededHyperparameters(hyperparameters, frame, headPositionFirstFrame, tailTipFirstFrame)
    elif hyperparameters["adjustFreelySwimTracking"] == 1:
      [hyperparametersListNames, frameToShow, WINDOW_NAME, organizationTab] = getFreelySwimTrackingParamsForHyperParamAdjusts(nbTailPoints, i, firstFrame, trackingHeadTailAllAnimals, trackingHeadingAllAnimals, frame, frame2, hyperparameters)
      if len(organizationTabCur) == 0:
        organizationTabCur = organizationTab
      [i, hyperparameters, organizationTabCur] = adjustHyperparameters(i, hyperparameters, hyperparametersListNames, frameToShow, WINDOW_NAME, organizationTabCur)
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
      [hyperparametersListNames, frameToShow, WINDOW_NAME, organizationTab] = getFreelySwimTrackingAutoParamsForHyperParamAdjusts(nbTailPoints, i, firstFrame, trackingHeadTailAllAnimals, trackingHeadingAllAnimals, frame, frame2, hyperparameters)
      if len(organizationTabCur) == 0:
        organizationTabCur = organizationTab
      [i, hyperparameters, organizationTabCur] = adjustHyperparameters(i, hyperparameters, hyperparametersListNames, frameToShow, WINDOW_NAME, organizationTabCur)
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
    prepend("Tracking done for well "+ str(wellNumber))
  
  return [trackingHeadTailAllAnimals, trackingHeadingAllAnimals, trackingEyesAllAnimals, headPositionFirstFrame, tailTipFirstFrame]
