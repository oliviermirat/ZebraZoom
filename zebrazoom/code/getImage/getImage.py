from zebrazoom.code.preprocessImage import preprocessImage
import numpy as np
import cv2

def getImage(videoPath, frameNumber, wellNumber, wellPositions, hyperparameters):
  
  minPixelDiffForBackExtract = hyperparameters["minPixelDiffForBackExtract"]
  debug = 0
  
  xtop = wellPositions[wellNumber]['topLeftX']
  ytop = wellPositions[wellNumber]['topLeftY']
  lenX = wellPositions[wellNumber]['lengthX']
  lenY = wellPositions[wellNumber]['lengthY']
  
  ret = False
  while (not(ret)):
    cap = cv2.VideoCapture(videoPath)
    cap.set(1, frameNumber)
    ret, frame = cap.read()
    if not(ret):
      frameNumber = frameNumber - 1
  
  if hyperparameters["imagePreProcessMethod"]:
    frame = preprocessImage(frame, hyperparameters)
  
  grey = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
  curFrame = grey[ytop:ytop+lenY, xtop:xtop+lenX]
  
  if (debug):
    cv2.imshow('Frame', curFrame)
    cv2.waitKey(0)
    
  return curFrame
