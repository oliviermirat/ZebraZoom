import os
from PIL import Image # TO REMOVE !!!
import numpy as np
import torch
import cv2

from zebrazoom.code.trackingFolder.headTrackingHeadingCalculationFolder.headTrackingHeadingCalculation import headTrackingHeadingCalculation
from zebrazoom.code.trackingFolder.tailTracking import tailTracking
from zebrazoom.code.trackingFolder.debugTracking import debugTracking

def trackingDL(videoPath, wellNumber, wellPositions, hyperparameters, videoName, dlModel, device):
  
  debugPlus = False
  dicotomySearchOfOptimalBlobArea = 0 #850
  
  firstFrame = hyperparameters["firstFrame"]
  if hyperparameters["firstFrameForTracking"] != -1:
    firstFrame = hyperparameters["firstFrameForTracking"]
  lastFrame = hyperparameters["lastFrame"]
  
  xtop = wellPositions[wellNumber]['topLeftX']
  ytop = wellPositions[wellNumber]['topLeftY']
  lenX = wellPositions[wellNumber]['lengthX']
  lenY = wellPositions[wellNumber]['lengthY']
  
  cap = cv2.VideoCapture(videoPath)
  if (cap.isOpened()== False): 
    print("Error opening video stream or file")
  frame_width  = int(cap.get(3))
  frame_height = int(cap.get(4))
  
  nbTailPoints = hyperparameters["nbTailPoints"]
  trackingHeadTailAllAnimals = np.zeros((hyperparameters["nbAnimalsPerWell"], lastFrame-firstFrame+1, nbTailPoints, 2))
  trackingHeadingAllAnimals  = np.zeros((hyperparameters["nbAnimalsPerWell"], lastFrame-firstFrame+1))
  trackingEyesAllAnimals     = 0
  trackingProbabilityOfGoodDetection = 0
  
  # Performing the tracking on each frame
  i = firstFrame
  cap.set(1, firstFrame)
  if int(hyperparameters["onlyDoTheTrackingForThisNumberOfFrames"]) != 0:
    lastFrame = min(lastFrame, firstFrame + int(hyperparameters["onlyDoTheTrackingForThisNumberOfFrames"]))
  while (i < lastFrame+1):
    
    if (hyperparameters["freqAlgoPosFollow"] != 0) and (i % hyperparameters["freqAlgoPosFollow"] == 0):
      print("Tracking: wellNumber:",wellNumber," ; frame:",i)
      if hyperparameters["popUpAlgoFollow"]:
        prepend("Tracking: wellNumber:" + str(wellNumber) + " ; frame:" + str(i))
    if hyperparameters["debugTracking"]:
      print("frame:",i)

    ret, frame = cap.read()
    if not(ret):
      currentFrameNum = int(cap.get(1))
      while not(ret):
        currentFrameNum = currentFrameNum - 1
        cap.set(1, currentFrameNum)
        ret, frame = cap.read()
    grey = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    curFrame = grey[ytop:ytop+lenY, xtop:xtop+lenX]
    
    oneChannel  = curFrame.tolist()
    oneChannel2 = [[a/255 for a in list] for list in oneChannel]
    imgTorch    = torch.tensor([oneChannel2, oneChannel2, oneChannel2])

    with torch.no_grad():
      prediction = dlModel([imgTorch.to(device)])
    
    thresh = prediction[0]['masks'][0, 0].mul(255).byte().cpu().numpy()
    if debugPlus:
      cv2.imshow("thresh", 255 - thresh)
    
    if dicotomySearchOfOptimalBlobArea:
      countNonZeroTarget = dicotomySearchOfOptimalBlobArea
      countNonZero       = 0
      low  = 0
      high = 255
      while abs(countNonZero - countNonZeroTarget) > 100 and (high - low) > 1:
        thresValueToTry = int((low + high) / 2)
        ret, thresh2 = cv2.threshold(thresh, thresValueToTry, 255, cv2.THRESH_BINARY)
        countNonZero = cv2.countNonZero(thresh2)
        if countNonZero > countNonZeroTarget:
          low = thresValueToTry
        else:
          high = thresValueToTry
    else:
      thresh2 = thresh
    thresh3 = thresh2.copy()
    
    if debugPlus:
      cv2.imshow("thresh2", 255 - thresh2)
    
    [trackingHeadingAllAnimals, trackingHeadTailAllAnimals, trackingProbabilityOfGoodDetection, lastFirstTheta] = headTrackingHeadingCalculation(hyperparameters, firstFrame, i, thresh2, thresh2, thresh2, thresh2, hyperparameters["erodeSize"], frame_width, frame_height, trackingHeadingAllAnimals, trackingHeadTailAllAnimals, trackingProbabilityOfGoodDetection, 0, wellPositions[wellNumber]["lengthX"])
    
    if hyperparameters["trackTail"] == 1:
      for animalId in range(0, hyperparameters["nbAnimalsPerWell"]):
        [trackingHeadTailAllAnimals, trackingHeadingAllAnimals] = tailTracking(animalId, i, firstFrame, videoPath, thresh3, hyperparameters, thresh3, nbTailPoints, thresh3, 0, trackingHeadTailAllAnimals, trackingHeadingAllAnimals, 0, 0, 0, thresh3, 0, wellNumber)
    
    # Debug functions
    debugTracking(nbTailPoints, i, firstFrame, trackingHeadTailAllAnimals, trackingHeadingAllAnimals, curFrame, hyperparameters)
    
    print("done for frame", i)
    i = i + 1
  
  return [trackingHeadTailAllAnimals, trackingHeadingAllAnimals, trackingEyesAllAnimals, 0, 0]