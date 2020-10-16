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

def tracking(videoPath,background,wellNumber,wellPositions,hyperparameters,videoName):

  firstFrame = hyperparameters["firstFrame"]
  if hyperparameters["firstFrameForTracking"] != -1:
    firstFrame = hyperparameters["firstFrameForTracking"]
  lastFrame = hyperparameters["lastFrame"]
  
  if (hyperparameters["freqAlgoPosFollow"] != 0):
    print("lastFrame:",lastFrame)

  nbTailPoints = hyperparameters["nbTailPoints"]
  thetaDiffAccept = 1.2 # 0.5 for the head embedded maybe
  maxDepth = 0
  headPosition = []
  tailTip = []
  
  cap = cv2.VideoCapture(videoPath)
  if (cap.isOpened()== False): 
    print("Error opening video stream or file")
  frame_width  = int(cap.get(3))
  frame_height = int(cap.get(4))
  
  heading = -1
  if hyperparameters["headEmbeded"]:
    heading = 0.7
    
  output = np.zeros((hyperparameters["nbAnimalsPerWell"], lastFrame-firstFrame+1, nbTailPoints, 2))
  outputHeading = np.zeros((hyperparameters["nbAnimalsPerWell"], lastFrame-firstFrame+1))
  
  threshForBlackFrames = getThresForBlackFrame(hyperparameters, videoPath) # For headEmbededTeresaNicolson 
  cap.set(1, firstFrame)
  
  if (hyperparameters["headEmbeded"] == 1):
    # Getting images
    if hyperparameters["headEmbededRemoveBack"] == 0:
      [frame, thresh1] = headEmbededFrame(videoPath, firstFrame)
    else:
      [frame, thresh1] = headEmbededFrameBackExtract(videoPath, background, hyperparameters, firstFrame)
    gray = frame.copy()
    oppHeading = (heading + math.pi) % (2 * math.pi)
    # Getting head and tailtip positions
    if os.path.exists(videoPath+'HP.csv'):
      headPosition = getHeadPositionByFileSaved(videoPath)
    else:
      if hyperparameters["findHeadPositionByUserInput"]:
        headPosition = findHeadPositionByUserInput(frame)
      else:
        [frame, gray, thresh1, blur, thresh2, frame2] = getImages(hyperparameters, cap, videoPath, firstFrame, background, wellNumber, wellPositions)
        cap.set(1, firstFrame)
        [outputHeading, output, heading, headPosition, lastFirstTheta] = headTrackingHeadingCalculation(hyperparameters, firstFrame, firstFrame, blur, thresh1, thresh2, gray, hyperparameters["erodeSize"], frame_width, frame_height, outputHeading, output, headPosition, wellPositions[wellNumber]["lengthX"])
    if os.path.exists(videoPath+'.csv'):
      tailTip  = getTailTipByFileSaved(hyperparameters,videoPath)
    else:
      tailTip  = findTailTipByUserInput(frame,hyperparameters)
    if hyperparameters["automaticallySetSomeOfTheHeadEmbededHyperparameters"] == 1:
      hyperparameters = adjustHeadEmbededHyperparameters(hyperparameters, frame, headPosition, tailTip)
    # Getting max depth
    if hyperparameters["headEmbededTeresaNicolson"] == 1:
      maxDepth = headEmbededTailTrackFindMaxDepthTeresaNicolson(headPosition,nbTailPoints,firstFrame,headPosition[0],headPosition[1],thresh1,frame,hyperparameters,oppHeading,tailTip)
    else:
      if hyperparameters["centerOfMassTailTracking"] == 0:
        maxDepth = headEmbededTailTrackFindMaxDepth(headPosition,nbTailPoints,firstFrame,headPosition[0],headPosition[1],thresh1,frame,hyperparameters,oppHeading,tailTip)
      else:
        maxDepth = centerOfMassTailTrackFindMaxDepth(headPosition,nbTailPoints,firstFrame,headPosition[0],headPosition[1],thresh1,frame,hyperparameters,oppHeading,tailTip)
  
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
    [outputHeading, output, heading, headPosition, lastFirstTheta] = headTrackingHeadingCalculation(hyperparameters, firstFrame, i, blur, thresh1, thresh2, gray, hyperparameters["erodeSize"], frame_width, frame_height, outputHeading, output, headPosition, wellPositions[wellNumber]["lengthX"])
    # Tail tracking for frame i
    if hyperparameters["nbAnimalsPerWell"] == 1 and hyperparameters["trackTail"] == 1 :
      animalId = 0
      
      [output, maxDepth, tailTip, headPosition] = tailTracking(animalId, i, firstFrame, heading, videoPath, headPosition, frame, hyperparameters, thresh1, nbTailPoints, threshForBlackFrames, thetaDiffAccept, output, lastFirstTheta, maxDepth, tailTip)
    
    # Debug functions
    debugTracking(nbTailPoints, i, firstFrame, headPosition[0], headPosition[1], output, outputHeading, frame2, hyperparameters)
    
    if hyperparameters["adjustHeadEmbededTracking"] == 1:
      [hyperparametersListNames, frameToShow, WINDOW_NAME, organizationTab] = getHeadEmbededTrackingParamsForHyperParamAdjusts(nbTailPoints, i, firstFrame, headPosition[0], headPosition[1], output, outputHeading, frame, frame2, hyperparameters)
      if len(organizationTabCur) == 0:
        organizationTabCur = organizationTab
      [i, hyperparameters, organizationTabCur] = adjustHyperparameters(i, hyperparameters, hyperparametersListNames, frameToShow, WINDOW_NAME, organizationTabCur)
      hyperparameters = adjustHeadEmbededHyperparameters(hyperparameters, frame, headPosition, tailTip)
    elif hyperparameters["adjustFreelySwimTracking"] == 1:
      [hyperparametersListNames, frameToShow, WINDOW_NAME, organizationTab] = getFreelySwimTrackingParamsForHyperParamAdjusts(nbTailPoints, i, firstFrame, headPosition[0], headPosition[1], output, outputHeading, frame, frame2, hyperparameters)
      if len(organizationTabCur) == 0:
        organizationTabCur = organizationTab
      [i, hyperparameters, organizationTabCur] = adjustHyperparameters(i, hyperparameters, hyperparametersListNames, frameToShow, WINDOW_NAME, organizationTabCur)
    else:
      i = i + 1
  
  savingBlackFrames(hyperparameters, videoName, output)
  
  print("Tracking done for well", wellNumber)
  if hyperparameters["popUpAlgoFollow"]:
    popUpAlgoFollow.prepend("Tracking done for well "+ str(wellNumber))
  
  return [output, outputHeading, headPosition, tailTip]
