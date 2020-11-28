import h5py
import numpy as np
import cv2
import popUpAlgoFollow
import math
import os

from getImages import getImages
from headTrackingHeadingCalculation import headTrackingHeadingCalculation
from debugTracking import debugTracking
from tailTracking import tailTracking
from blackFramesDetection import getThresForBlackFrame, savingBlackFrames
from getTailTipManual import getHeadPositionByFileSaved, findTailTipByUserInput, getTailTipByFileSaved, findHeadPositionByUserInput

from headEmbededFrame import headEmbededFrame
from headEmbededFrameBackExtract import headEmbededFrameBackExtract

from adjustHyperparameters import initializeAdjustHyperparametersWindows, adjustHyperparameters, getHeadEmbededTrackingParamsForHyperParamAdjusts, getFreelySwimTrackingParamsForHyperParamAdjusts
from headEmbededTailTracking import adjustHeadEmbededHyperparameters

from headEmbededTailTracking import headEmbededTailTrackFindMaxDepth
from headEmbededTailTrackingTeresaNicolson import headEmbededTailTrackFindMaxDepthTeresaNicolson, headEmbededTailTrackingTeresaNicolson
from centerOfMassTailTracking import centerOfMassTailTrackFindMaxDepth

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
  
  threshForBlackFrames = getThresForBlackFrame(hyperparameters, videoPath) # For headEmbededTeresaNicolson 
  cap.set(1, firstFrame)
  
  # Using the first frame of the video to calculate parameters that will be used afterwards for the tracking
  if (hyperparameters["headEmbeded"] == 1):
    # Getting images
    if hyperparameters["headEmbededRemoveBack"] == 0:
      [frame, thresh1] = headEmbededFrame(videoPath, firstFrame)
    else:
      [frame, thresh1] = headEmbededFrameBackExtract(videoPath, background, hyperparameters, firstFrame)
    gray = frame.copy()
    oppHeading = (heading + math.pi) % (2 * math.pi)
    # Getting headPositionFirstFrame and tailTipFirstFrame positions
    if os.path.exists(videoPath+'HP.csv'):
      headPositionFirstFrame = getHeadPositionByFileSaved(videoPath)
    else:
      if hyperparameters["findHeadPositionByUserInput"]:
        headPositionFirstFrame = findHeadPositionByUserInput(frame)
      else:
        [frame, gray, thresh1, blur, thresh2, frame2] = getImages(hyperparameters, cap, videoPath, firstFrame, background, wellNumber, wellPositions)
        cap.set(1, firstFrame)
        [trackingHeadingAllAnimals, trackingHeadTailAllAnimals, heading, lastFirstTheta] = headTrackingHeadingCalculation(hyperparameters, firstFrame, firstFrame, blur, thresh1, thresh2, gray, hyperparameters["erodeSize"], frame_width, frame_height, trackingHeadingAllAnimals, trackingHeadTailAllAnimals, headPositionFirstFrame, wellPositions[wellNumber]["lengthX"])
    if os.path.exists(videoPath+'.csv'):
      tailTipFirstFrame  = getTailTipByFileSaved(hyperparameters,videoPath)
    else:
      tailTipFirstFrame  = findTailTipByUserInput(frame,hyperparameters)
    if hyperparameters["automaticallySetSomeOfTheHeadEmbededHyperparameters"] == 1:
      hyperparameters = adjustHeadEmbededHyperparameters(hyperparameters, frame, headPositionFirstFrame, tailTipFirstFrame)
    # Getting max depth
    if hyperparameters["headEmbededTeresaNicolson"] == 1:
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
        popUpAlgoFollow.prepend("Tracking: wellNumber:" + str(wellNumber) + " ; frame:" + str(i))
    if hyperparameters["debugTracking"]:
      print("frame:",i)
    # Get images for frame i
    [frame, gray, thresh1, blur, thresh2, frame2] = getImages(hyperparameters, cap, videoPath, i, background, wellNumber, wellPositions)
    # Head tracking and heading calculation
    [trackingHeadingAllAnimals, trackingHeadTailAllAnimals, heading, lastFirstTheta] = headTrackingHeadingCalculation(hyperparameters, firstFrame, i, blur, thresh1, thresh2, gray, hyperparameters["erodeSize"], frame_width, frame_height, trackingHeadingAllAnimals, trackingHeadTailAllAnimals, headPositionFirstFrame, wellPositions[wellNumber]["lengthX"])
    # Tail tracking for frame i
    if hyperparameters["trackTail"] == 1 :
      for animalId in range(0, hyperparameters["nbAnimalsPerWell"]):
        headPosition = [trackingHeadTailAllAnimals[animalId, i-firstFrame][0][0], trackingHeadTailAllAnimals[animalId, i-firstFrame][0][1]]
        [trackingHeadTailAllAnimals, maxDepth] = tailTracking(animalId, i, firstFrame, heading, videoPath, headPosition, frame, hyperparameters, thresh1, nbTailPoints, threshForBlackFrames, thetaDiffAccept, trackingHeadTailAllAnimals, lastFirstTheta, maxDepth, tailTipFirstFrame)
    
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
  
  savingBlackFrames(hyperparameters, videoName, trackingHeadTailAllAnimals)
  
  print("Tracking done for well", wellNumber)
  if hyperparameters["popUpAlgoFollow"]:
    popUpAlgoFollow.prepend("Tracking done for well "+ str(wellNumber))
  
  return [trackingHeadTailAllAnimals, trackingHeadingAllAnimals, headPositionFirstFrame, tailTipFirstFrame]
