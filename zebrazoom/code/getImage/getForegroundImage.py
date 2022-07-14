from zebrazoom.code.preprocessImage import preprocessImage
import numpy as np
import cv2
import zebrazoom.videoFormatConversion.zzVideoReading as zzVideoReading

def getForegroundImage(videoPath, background, frameNumber, wellNumber, wellPositions, hyperparameters):
  
  minPixelDiffForBackExtract = hyperparameters["minPixelDiffForBackExtract"]
  if "minPixelDiffForBackExtractHead" in hyperparameters:
    minPixelDiffForBackExtract = hyperparameters["minPixelDiffForBackExtractHead"]
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
  
  cap = zzVideoReading.VideoCapture(videoPath)
  cap.set(1, frameNumber)
  ret, frame = cap.read()
  
  if not(ret):
    if hyperparameters["searchPreviousFramesIfCurrentFrameIsCorrupted"]:
      currentFrameNum = int(cap.get(1))
      while not(ret) and currentFrameNum:
        currentFrameNum = currentFrameNum - 1
        cap.set(1, currentFrameNum)
        ret, frame = cap.read()
    else:
      frame = back.copy()
  
  if hyperparameters["invertBlackWhiteOnImages"]:
    frame = 255 - frame
    
  if hyperparameters["imagePreProcessMethod"]:
    frame = preprocessImage(frame, hyperparameters)
    
  grey = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
  curFrame = grey[ytop:ytop+lenY, xtop:xtop+lenX]
  initialCurFrame = curFrame.copy()
  
  # if False:
  putToWhite = ( curFrame.astype('int32') >= (back.astype('int32') - minPixelDiffForBackExtract) )
  
  curFrame[putToWhite] = 255
  previousNbBlackPixels = []
  if hyperparameters["adjustMinPixelDiffForBackExtract_nbBlackPixelsMax"]:
    minPixel2nbBlackPixels = {}
    countTries = 0
    nbBlackPixels = 0
    nbBlackPixelsMax = int(hyperparameters["adjustMinPixelDiffForBackExtract_nbBlackPixelsMax"])
    while (minPixelDiffForBackExtract > 0) and (countTries < 30) and not(minPixelDiffForBackExtract in minPixel2nbBlackPixels):
      if countTries > 0:
        curFrame = grey[ytop:ytop+lenY, xtop:xtop+lenX]
        putToWhite = ( curFrame.astype('int32') >= (back.astype('int32') - minPixelDiffForBackExtract) )
        curFrame[putToWhite] = 255
      ret, thresh1 = cv2.threshold(curFrame, hyperparameters["thresholdForBlobImg"], 255, cv2.THRESH_BINARY)
      thresh1 = 255 - thresh1
      nbBlackPixels = cv2.countNonZero(thresh1)
      minPixel2nbBlackPixels[minPixelDiffForBackExtract] = nbBlackPixels
      if nbBlackPixels > nbBlackPixelsMax:
        minPixelDiffForBackExtract = minPixelDiffForBackExtract + 1
      if nbBlackPixels <= nbBlackPixelsMax:
        minPixelDiffForBackExtract = minPixelDiffForBackExtract - 1
      countTries = countTries + 1
      previousNbBlackPixels.append(nbBlackPixels)
      if len(previousNbBlackPixels) >= 3:
        lastThree = previousNbBlackPixels[len(previousNbBlackPixels)-3: len(previousNbBlackPixels)]
        if lastThree.count(lastThree[0]) == len(lastThree):
          countTries = 1000000
    
    best_minPixelDiffForBackExtract = 0
    minDist = 10000000000000
    for minPixelDiffForBackExtract in minPixel2nbBlackPixels:
      nbBlackPixels = minPixel2nbBlackPixels[minPixelDiffForBackExtract]
      dist = abs(nbBlackPixels - nbBlackPixelsMax)
      if dist < minDist:
        minDist = dist
        best_minPixelDiffForBackExtract = minPixelDiffForBackExtract
        
    minPixelDiffForBackExtract = best_minPixelDiffForBackExtract
    hyperparameters["minPixelDiffForBackExtractHead"] = minPixelDiffForBackExtract
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
    import zebrazoom.code.util as util

    # cv2.imshow('Frame', curFrame)
    util.showFrame(frame, title='Frame')
    
  return [curFrame, initialCurFrame, back]
