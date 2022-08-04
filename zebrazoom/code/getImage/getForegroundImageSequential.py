from zebrazoom.code.preprocessImage import preprocessImage
import numpy as np
import cv2


def getForegroundImageSequential(cap, videoPath, background, frameNumber, wellNumber, wellPositions, hyperparameters, alreadyExtractedImage=0, trackingHeadTailAllAnimals=0):
  
  minPixelDiffForBackExtract = hyperparameters["minPixelDiffForBackExtract"]
  if "minPixelDiffForBackExtractHead" in hyperparameters:
    minPixelDiffForBackExtract = hyperparameters["minPixelDiffForBackExtractHead"]
  debug = 0
  
  xtop = wellPositions[wellNumber]['topLeftX']
  ytop = wellPositions[wellNumber]['topLeftY']
  lenX = wellPositions[wellNumber]['lengthX']
  lenY = wellPositions[wellNumber]['lengthY']
  
  back = background[ytop:ytop+lenY, xtop:xtop+lenX]
  
  if (type(alreadyExtractedImage) != int):
    ret   = True
    frame = alreadyExtractedImage.copy()
  else:
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
  
  xHead = trackingHeadTailAllAnimals[0][frameNumber - hyperparameters["firstFrame"] - 1][0][0]
  yHead = trackingHeadTailAllAnimals[0][frameNumber - hyperparameters["firstFrame"] - 1][0][1]
  if hyperparameters["trackOnlyOnROI_halfDiameter"] != 0 and frameNumber != hyperparameters["firstFrame"] and xHead != 0 and yHead != 0:
    xHeadMin = xHead
    xHeadMax = xHead
    yHeadMin = yHead
    yHeadMax = yHead
    for animalId in range(1, hyperparameters["nbAnimalsPerWell"]):
      xHead = trackingHeadTailAllAnimals[animalId][frameNumber - hyperparameters["firstFrame"] - 1][0][0]
      yHead = trackingHeadTailAllAnimals[animalId][frameNumber - hyperparameters["firstFrame"] - 1][0][1]
      xHeadMin = xHeadMin if xHeadMin < xHead else xHead
      xHeadMax = xHeadMax if xHeadMax > xHead else xHead
      yHeadMin = yHeadMin if yHeadMin < yHead else yHead
      yHeadMax = yHeadMax if yHeadMax > yHead else yHead
    maxHalfDiameter = hyperparameters["trackOnlyOnROI_halfDiameter"]
    xmin = int(xHeadMin - maxHalfDiameter) if xHeadMin - maxHalfDiameter >= 0 else 0
    ymin = int(yHeadMin - maxHalfDiameter) if yHeadMin - maxHalfDiameter >= 0 else 0
    xmax = int(xHeadMax + maxHalfDiameter) if xHeadMax + maxHalfDiameter < len(curFrame[0]) else len(curFrame[0]) - 1
    ymax = int(yHeadMax + maxHalfDiameter) if yHeadMax + maxHalfDiameter < len(curFrame)    else len(curFrame) - 1
    curFrameInitial = curFrame.copy()
    backInitial     = back.copy()
    initialCurFrameInitial = curFrame.copy()
    initialCurFrame = curFrame.copy()
    curFrame = curFrame[ymin:ymax, xmin:xmax]
    back     = back[ymin:ymax, xmin:xmax]
  else:
    xmin = 0
    ymin = 0
    initialCurFrameInitial = 0
    curFrameInitial = 0
    backInitial     = 0
    initialCurFrame = curFrame.copy()
  
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
        if hyperparameters["trackOnlyOnROI_halfDiameter"] != 0 and frameNumber != hyperparameters["firstFrame"] and xHead != 0 and yHead != 0:
          curFrame = curFrame[ymin:ymax, xmin:xmax]
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
    if hyperparameters["trackOnlyOnROI_halfDiameter"] != 0 and frameNumber != hyperparameters["firstFrame"] and xHead != 0 and yHead != 0:
      curFrame = curFrame[ymin:ymax, xmin:xmax]
      curFrameInitial = curFrame
      backInitial     = back
      # initialCurFrameInitial = curFrame
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
  
  if hyperparameters["trackOnlyOnROI_halfDiameter"] != 0:
    ret, res = cv2.threshold(curFrame, hyperparameters["thresholdForBlobImg"], 255, cv2.THRESH_BINARY)
    if ret:
      reinitialize = 1
      contours, hierarchy = cv2.findContours(res, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
      for contour in contours:
        contourArea = cv2.contourArea(contour)
        if contourArea > hyperparameters["minAreaBody"] and contourArea < hyperparameters["maxAreaBody"]:
          reinitialize = 0
      if reinitialize and type(curFrameInitial) != int:
        curFrame = curFrameInitial
        initialCurFrame = initialCurFrameInitial
        back = backInitial
  
  return [curFrame, initialCurFrame, back, xmin, ymin]
