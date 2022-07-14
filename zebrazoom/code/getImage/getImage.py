from zebrazoom.code.preprocessImage import preprocessImage
import numpy as np
import cv2
import zebrazoom.videoFormatConversion.zzVideoReading as zzVideoReading


def getImage(videoPath, frameNumber, wellNumber, wellPositions, hyperparameters):
  
  minPixelDiffForBackExtract = hyperparameters["minPixelDiffForBackExtract"]
  debug = 0
  
  xtop = wellPositions[wellNumber]['topLeftX']
  ytop = wellPositions[wellNumber]['topLeftY']
  lenX = wellPositions[wellNumber]['lengthX']
  lenY = wellPositions[wellNumber]['lengthY']
  
  ret = False
  while (not(ret)):
    cap = zzVideoReading.VideoCapture(videoPath)
    cap.set(1, frameNumber)
    ret, frame = cap.read()
    if not(ret):
      frameNumber = frameNumber - 1
  
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
