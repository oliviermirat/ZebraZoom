from zebrazoom.code.preprocessImage import preprocessImage
import numpy as np
import cv2

def getForegroundImage(videoPath, background, frameNumber, wellNumber, wellPositions, hyperparameters):
  
  minPixelDiffForBackExtract = hyperparameters["minPixelDiffForBackExtract"]
  debug = 0
  
  if len(wellPositions):
    xtop = wellPositions[wellNumber]['topLeftX']
    ytop = wellPositions[wellNumber]['topLeftY']
    lenX = wellPositions[wellNumber]['lengthX']
    lenY = wellPositions[wellNumber]['lengthY']
  else:
    xtop = 0
    ytop = 0
    lenX = len(background[0])
    lenY = len(background)
  
  back = background[ytop:ytop+lenY, xtop:xtop+lenX]
  
  cap = cv2.VideoCapture(videoPath)
  cap.set(1, frameNumber)
  ret, frame = cap.read()
  
  while not(ret) and frameNumber:
    frameNumber = frameNumber - 1
    cap.set(1, frameNumber)
    ret, frame = cap.read()
  
  if hyperparameters["invertBlackWhiteOnImages"]:
    frame = 255 - frame
    
  if hyperparameters["imagePreProcessMethod"]:
    frame = preprocessImage(frame, hyperparameters)
    
  grey = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
  curFrame = grey[ytop:ytop+lenY, xtop:xtop+lenX]
  
  # if False:
  putToWhite = ( curFrame.astype('int32') >= (back.astype('int32') - minPixelDiffForBackExtract) )
  
  curFrame[putToWhite] = 255
  
  if hyperparameters["adjustMinPixelDiffForBackExtract_nbBlackPixelsMax"]:
    countTries = 0
    nbBlackPixels = 0
    nbBlackPixelsMax = int(hyperparameters["adjustMinPixelDiffForBackExtract_nbBlackPixelsMax"])
    while ((nbBlackPixels < 1) or (nbBlackPixels > nbBlackPixelsMax)) and (countTries < 30):
      if countTries > 0:
        curFrame = grey[ytop:ytop+lenY, xtop:xtop+lenX]
        putToWhite = ( curFrame.astype('int32') >= (back.astype('int32') - minPixelDiffForBackExtract) )
        curFrame[putToWhite] = 255
      ret, thresh1 = cv2.threshold(curFrame, hyperparameters["thresholdForBlobImg"], 255, cv2.THRESH_BINARY)
      thresh1 = 255 - thresh1
      nbBlackPixels = cv2.countNonZero(thresh1)
      if nbBlackPixels > nbBlackPixelsMax:
        minPixelDiffForBackExtract = minPixelDiffForBackExtract + 1
      if nbBlackPixels < 1 and minPixelDiffForBackExtract > 1:
        minPixelDiffForBackExtract = minPixelDiffForBackExtract - 1
      countTries = countTries + 1
    # print("countTries:", countTries, "; nbBlackPixels:", nbBlackPixels, "; minPixelDiffForBackExtract:", minPixelDiffForBackExtract)
    curFrame = grey[ytop:ytop+lenY, xtop:xtop+lenX]
    putToWhite = ( curFrame.astype('int32') >= (back.astype('int32') - minPixelDiffForBackExtract) )
    curFrame[putToWhite] = 255      
    
  # else:
    # putToBlack3a = ( curFrame.astype('int32') <= (back.astype('int32') - minPixelDiffForBackExtract) )
    # putToBlack3b = ( curFrame.astype('int32') >= (back.astype('int32') + minPixelDiffForBackExtract) )
    
    # putToWhite  = (curFrame <= 220)
    # putToBlack  = (curFrame >= 220)
    
    # curFrame[putToWhite]   = 255
    # curFrame[putToBlack]   = 0
    # curFrame[putToBlack3a] = 0
    # curFrame[putToBlack3b] = 0
  
  if (debug):
    # cv2.imshow('Frame', curFrame)
    cv2.imshow('Frame', frame)
    cv2.waitKey(0)
    
  return curFrame
