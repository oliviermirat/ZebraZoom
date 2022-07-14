from zebrazoom.code.preprocessImage import preprocessImage
import numpy as np
import cv2


def getImageSequential(cap, videoPath, frameNumber, wellNumber, wellPositions, hyperparameters):
  
  minPixelDiffForBackExtract = hyperparameters["minPixelDiffForBackExtract"]
  debug = 0
  
  xtop = wellPositions[wellNumber]['topLeftX']
  ytop = wellPositions[wellNumber]['topLeftY']
  lenX = wellPositions[wellNumber]['lengthX']
  lenY = wellPositions[wellNumber]['lengthY']
  
  ret, frame = cap.read()
  
  while not(ret):
    print("WARNING: was not able to extract the frame", str(frameNumber),"in 'getImageSequential'")
    frameNumber = frameNumber - 1
    cap.set(1, frameNumber)
    ret, frame = cap.read()
    
  if hyperparameters["invertBlackWhiteOnImages"]:
    frame = 255 - frame
  
  if hyperparameters["imagePreProcessMethod"]:
    frame = preprocessImage(frame, hyperparameters)
  
  grey = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
  curFrame = grey[ytop:ytop+lenY, xtop:xtop+lenX]
  
  if (debug):
    import zebrazoom.code.util as util
    util.showFrame(curFrame, title='Frame')
    
  return curFrame
