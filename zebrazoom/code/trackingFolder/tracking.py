import h5py
import numpy as np
import cv2
from zebrazoom.code.popUpAlgoFollow import prepend
import math
import os

from zebrazoom.code.trackingFolder.getImages import getImages
from zebrazoom.code.trackingFolder.headTrackingHeadingCalculationFolder.headTrackingHeadingCalculation import headTrackingHeadingCalculation
from zebrazoom.code.trackingFolder.debugTracking import debugTracking
from zebrazoom.code.trackingFolder.tailTracking import tailTracking
from zebrazoom.code.trackingFolder.blackFramesDetection import getThresForBlackFrame, savingBlackFrames
from zebrazoom.code.trackingFolder.tailTrackingFunctionsFolder.getTailTipManual import getHeadPositionByFileSaved, findTailTipByUserInput, getTailTipByFileSaved, findHeadPositionByUserInput
from zebrazoom.code.trackingFolder.eyeTracking.eyeTracking import eyeTracking
from zebrazoom.code.trackingFolder.postProcessMultipleTrajectories import postProcessMultipleTrajectories

from zebrazoom.code.getImage.headEmbededFrame import headEmbededFrame
from zebrazoom.code.getImage.headEmbededFrameBackExtract import headEmbededFrameBackExtract

from zebrazoom.code.adjustHyperparameters import initializeAdjustHyperparametersWindows, adjustHyperparameters, getHeadEmbededTrackingParamsForHyperParamAdjusts, getFreelySwimTrackingParamsForHyperParamAdjusts
from zebrazoom.code.trackingFolder.tailTrackingFunctionsFolder.headEmbededTailTracking import adjustHeadEmbededHyperparameters

from zebrazoom.code.trackingFolder.tailTrackingFunctionsFolder.headEmbededTailTracking import headEmbededTailTrackFindMaxDepth
from zebrazoom.code.trackingFolder.tailTrackingFunctionsFolder.headEmbededTailTrackingTeresaNicolson import headEmbededTailTrackFindMaxDepthTeresaNicolson, headEmbededTailTrackingTeresaNicolson
from zebrazoom.code.trackingFolder.tailTrackingFunctionsFolder.centerOfMassTailTracking import centerOfMassTailTrackFindMaxDepth

def tracking(videoPath, background, wellNumber, wellPositions, hyperparameters, videoName):

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
  
  cap = cv2.VideoCapture(videoPath)
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
      
    # if hyperparameters["invertBlackWhiteOnImages"]:
      # frame   = 255 - frame
    
    gray = frame.copy()
    
    oppHeading = (heading + math.pi) % (2 * math.pi)
    
    # Getting headPositionFirstFrame and tailTipFirstFrame positions
    if os.path.exists(videoPath+'HP.csv'):
      headPositionFirstFrame = getHeadPositionByFileSaved(videoPath)
    else:
      if hyperparameters["findHeadPositionByUserInput"]:
        headPositionFirstFrame = findHeadPositionByUserInput(frame, firstFrame, videoPath)
      else:
        [frame, gray, thresh1, blur, thresh2, frame2, initialCurFrame, back] = getImages(hyperparameters, cap, videoPath, firstFrame, background, wellNumber, wellPositions)
        cap.set(1, firstFrame)
        [trackingHeadingAllAnimals, trackingHeadTailAllAnimals, lastFirstTheta] = headTrackingHeadingCalculation(hyperparameters, firstFrame, firstFrame, blur, thresh1, thresh2, gray, hyperparameters["erodeSize"], frame_width, frame_height, trackingHeadingAllAnimals, trackingHeadTailAllAnimals, headPositionFirstFrame, wellPositions[wellNumber]["lengthX"])
    if os.path.exists(videoPath+'.csv'):
      tailTipFirstFrame  = getTailTipByFileSaved(hyperparameters,videoPath)
    else:
      tailTipFirstFrame  = findTailTipByUserInput(frame, firstFrame, videoPath, hyperparameters)
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
  
  if hyperparameters["adjustHeadEmbededTracking"] == 1 or hyperparameters["adjustFreelySwimTracking"] == 1:
    initializeAdjustHyperparametersWindows("Tracking")
  organizationTabCur = []
  
  # Performing the tracking on each frame
  i = firstFrame
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
    [trackingHeadingAllAnimals, trackingHeadTailAllAnimals, lastFirstTheta] = headTrackingHeadingCalculation(hyperparameters, firstFrame, i, blur, thresh1, thresh2, gray, hyperparameters["erodeSize"], frame_width, frame_height, trackingHeadingAllAnimals, trackingHeadTailAllAnimals, headPositionFirstFrame, wellPositions[wellNumber]["lengthX"])
    # Tail tracking for frame i
    if hyperparameters["trackTail"] == 1 :
      for animalId in range(0, hyperparameters["nbAnimalsPerWell"]):
        [trackingHeadTailAllAnimals, trackingHeadingAllAnimals] = tailTracking(animalId, i, firstFrame, videoPath, frame, hyperparameters, thresh1, nbTailPoints, threshForBlackFrames, thetaDiffAccept, trackingHeadTailAllAnimals, trackingHeadingAllAnimals, lastFirstTheta, maxDepth, tailTipFirstFrame, initialCurFrame, back)
    # Eye tracking for frame i
    if hyperparameters["eyeTracking"]:
      trackingEyesAllAnimals = eyeTracking(animalId, i, firstFrame, frame, hyperparameters, thresh1, trackingHeadingAllAnimals, trackingHeadTailAllAnimals, trackingEyesAllAnimals)
    # Debug functions
    debugTracking(nbTailPoints, i, firstFrame, trackingHeadTailAllAnimals, trackingHeadingAllAnimals, frame2, hyperparameters)
    
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
    else:
      i = i + 1
      
  if hyperparameters["postProcessMultipleTrajectories"]:
    [trackingHeadingAllAnimals, trackingHeadTailAllAnimals, trackingEyesAllAnimals] = postProcessMultipleTrajectories(trackingHeadingAllAnimals, trackingHeadTailAllAnimals, trackingEyesAllAnimals, hyperparameters)
  
  savingBlackFrames(hyperparameters, videoName, trackingHeadTailAllAnimals)
  
  print("Tracking done for well", wellNumber)
  if hyperparameters["popUpAlgoFollow"]:
    prepend("Tracking done for well "+ str(wellNumber))
  
  return [trackingHeadTailAllAnimals, trackingHeadingAllAnimals, trackingEyesAllAnimals, headPositionFirstFrame, tailTipFirstFrame]
