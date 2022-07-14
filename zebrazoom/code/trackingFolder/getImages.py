import cv2
import numpy as np

from zebrazoom.code.getImage.getForegroundImageSequential import getForegroundImageSequential
from zebrazoom.code.getImage.getForegroundImage import getForegroundImage
from zebrazoom.code.getImage.getImageSequential import getImageSequential
from zebrazoom.code.getImage.getImage import getImage
from zebrazoom.code.getImage.headEmbededFrame import headEmbededFrame
from zebrazoom.code.getImage.headEmbededFrameSequential import headEmbededFrameSequential
from zebrazoom.code.getImage.headEmbededFrameSequentialBackExtract import headEmbededFrameSequentialBackExtract
from zebrazoom.code.getImage.headEmbededFrameBackExtract import headEmbededFrameBackExtract

def getImages(hyperparameters, cap, videoPath, i, background, wellNumber, wellPositions, alreadyExtractedImage=0, trackingHeadTailAllAnimals=0):
  
  xHead = 0
  yHead = 0
  
  initialCurFrame = 0
  back = 0

  if hyperparameters["headEmbeded"]:
    if hyperparameters["headEmbededRemoveBack"] == 0:
      if hyperparameters["adjustHeadEmbededTracking"] == 0 and not hyperparameters["adjustHeadEmbeddedEyeTracking"]:
        [frame, thresh1] = headEmbededFrameSequential(cap, videoPath, i, wellNumber, wellPositions, hyperparameters)
      else:
        [frame, thresh1] = headEmbededFrame(videoPath, i, wellNumber, wellPositions, hyperparameters)
      gray = frame.copy()
    else:
      if hyperparameters["adjustHeadEmbededTracking"] == 0 and not hyperparameters["adjustHeadEmbeddedEyeTracking"]:
        [frame, thresh1] = headEmbededFrameSequentialBackExtract(cap, videoPath, background, hyperparameters, i, wellNumber, wellPositions)
      else:
        [frame, thresh1] = headEmbededFrameBackExtract(videoPath, background, hyperparameters, i, wellNumber, wellPositions)
      gray = frame.copy()
  else:
    if hyperparameters["adjustFreelySwimTracking"] == 0 and hyperparameters["adjustFreelySwimTrackingAutomaticParameters"] == 0:
      if len(background):
        [frame, initialCurFrame, back, xHead, yHead] = getForegroundImageSequential(cap, videoPath, background, i, wellNumber, wellPositions, hyperparameters, alreadyExtractedImage, trackingHeadTailAllAnimals)
      else:
        frame = getImageSequential(cap, videoPath, i, wellNumber, wellPositions, hyperparameters)
    else:
      if len(background):
        [frame, initialCurFrame, back] = getForegroundImage(videoPath, background, i, wellNumber, wellPositions, hyperparameters)
      else:
        frame = getImage(videoPath, i, wellNumber, wellPositions, hyperparameters)
    
    gray = frame.copy()
    
    ret,thresh1 = cv2.threshold(gray,hyperparameters["thresholdForBlobImg"],255,cv2.THRESH_BINARY)
  
  
  coverHorizontalPortionBelowForHeadDetect = hyperparameters["coverHorizontalPortionBelowForHeadDetect"]
  if coverHorizontalPortionBelowForHeadDetect != -1:
    gray[coverHorizontalPortionBelowForHeadDetect:len(gray)-1,:] = 255
    
  coverHorizontalPortionAboveForHeadDetect = hyperparameters["coverHorizontalPortionAboveForHeadDetect"]
  if coverHorizontalPortionAboveForHeadDetect != -1:
    gray[0:coverHorizontalPortionAboveForHeadDetect,:] = 255
    
  coverVerticalPortionRightForHeadDetect = hyperparameters["coverVerticalPortionRightForHeadDetect"]
  if coverVerticalPortionRightForHeadDetect != -1:
    gray[:,coverVerticalPortionRightForHeadDetect:len(gray[0])-1] = 255
  
  
  coverPortionForHeadDetect = hyperparameters["coverPortionForHeadDetect"]
  if coverPortionForHeadDetect == "Bottom":
    gray[int(len(gray)/2):len(gray)-1, :] = 255
  if coverPortionForHeadDetect == "Top":
    gray[0:int(len(gray)/2), :] = 255
  if coverPortionForHeadDetect == "Left":
    gray[:, 0:int(len(gray[0])/2)] = 255
  if coverPortionForHeadDetect == "Right":
    gray[:, int(len(gray[0])/2):len(gray[0])-1] = 255
  
  if hyperparameters["debugCoverHorizontalPortionBelow"] and i==firstFrame:
    import zebrazoom.code.util as util

    util.showFrame(gray, title='Frame')
  
  # paramGaussianBlur = int((hyperparameters["paramGaussianBlur"] / 2)) * 2 + 1
  # blur = cv2.GaussianBlur(gray, (paramGaussianBlur, paramGaussianBlur), 0)
  blur = 0
  
  frame2 = frame #frame.copy()
  
  if hyperparameters["erodeIter"] or hyperparameters["dilateIter"]:
    erodeSize = hyperparameters["erodeSize"]
    kernel  = np.ones((erodeSize,erodeSize), np.uint8)
  
  if hyperparameters["erodeIter"]:
    thresh1 = cv2.erode(thresh1, kernel, iterations=hyperparameters["erodeIter"])
  
  if hyperparameters["dilateIter"]:
    thresh2 = thresh1.copy()
    thresh2 = cv2.dilate(thresh2, kernel, iterations=hyperparameters["dilateIter"])
  else:
    thresh2 = thresh1
  
  return [frame, gray, thresh1, blur, thresh2, frame2, initialCurFrame, back, xHead, yHead]
