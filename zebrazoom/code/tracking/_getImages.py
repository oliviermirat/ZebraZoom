import cv2
import numpy as np

import zebrazoom.videoFormatConversion.zzVideoReading as zzVideoReading
from zebrazoom.code.preprocessImage import preprocessImage


class GetImagesMixin:
  def _getImage(self, frameNumber, wellNumber):
    minPixelDiffForBackExtract = self._hyperparameters["minPixelDiffForBackExtract"]
    debug = 0

    xtop = self._wellPositions[wellNumber]['topLeftX']
    ytop = self._wellPositions[wellNumber]['topLeftY']
    lenX = self._wellPositions[wellNumber]['lengthX']
    lenY = self._wellPositions[wellNumber]['lengthY']

    ret = False
    while (not(ret)):
      cap = zzVideoReading.VideoCapture(self._videoPath)
      cap.set(1, frameNumber)
      ret, frame = cap.read()
      if not(ret):
        frameNumber = frameNumber - 1

    if self._hyperparameters["invertBlackWhiteOnImages"]:
      frame = 255 - frame

    if self._hyperparameters["imagePreProcessMethod"]:
      frame = preprocessImage(frame, self._hyperparameters)

    grey = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    curFrame = grey[ytop:ytop+lenY, xtop:xtop+lenX]

    if (debug):
      self._debugFrame(curFrame, title='Frame')

    return curFrame

  def _getForegroundImageSequential(self, cap, frameNumber, wellNumber, alreadyExtractedImage=0, trackingHeadTailAllAnimals=0):
    minPixelDiffForBackExtract = self._hyperparameters["minPixelDiffForBackExtract"]
    if "minPixelDiffForBackExtractHead" in self._hyperparameters:
      minPixelDiffForBackExtract = self._hyperparameters["minPixelDiffForBackExtractHead"]
    debug = 0

    xtop = self._wellPositions[wellNumber]['topLeftX']
    ytop = self._wellPositions[wellNumber]['topLeftY']
    lenX = self._wellPositions[wellNumber]['lengthX']
    lenY = self._wellPositions[wellNumber]['lengthY']

    back = self._background[ytop:ytop+lenY, xtop:xtop+lenX]

    if (type(alreadyExtractedImage) != int):
      ret   = True
      frame = alreadyExtractedImage.copy()
    else:
      ret, frame = cap.read()

    if not(ret):
      if self._hyperparameters["searchPreviousFramesIfCurrentFrameIsCorrupted"]:
        currentFrameNum = int(cap.get(1))
        while not(ret) and currentFrameNum:
          currentFrameNum = currentFrameNum - 1
          cap.set(1, currentFrameNum)
          ret, frame = cap.read()
      else:
        frame = back.copy()

    if self._hyperparameters["invertBlackWhiteOnImages"]:
      frame = 255 - frame

    if self._hyperparameters["imagePreProcessMethod"]:
      frame = preprocessImage(frame, self._hyperparameters)

    grey = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    curFrame = grey[ytop:ytop+lenY, xtop:xtop+lenX]

    xHead = trackingHeadTailAllAnimals[0][frameNumber - self._hyperparameters["firstFrame"] - 1][0][0]
    yHead = trackingHeadTailAllAnimals[0][frameNumber - self._hyperparameters["firstFrame"] - 1][0][1]
    if self._hyperparameters["trackOnlyOnROI_halfDiameter"] != 0 and frameNumber != self._hyperparameters["firstFrame"] and xHead != 0 and yHead != 0:
      xHeadMin = xHead
      xHeadMax = xHead
      yHeadMin = yHead
      yHeadMax = yHead
      for animalId in range(1, self._hyperparameters["nbAnimalsPerWell"]):
        xHead = trackingHeadTailAllAnimals[animalId][frameNumber - self._hyperparameters["firstFrame"] - 1][0][0]
        yHead = trackingHeadTailAllAnimals[animalId][frameNumber - self._hyperparameters["firstFrame"] - 1][0][1]
        xHeadMin = xHeadMin if xHeadMin < xHead else xHead
        xHeadMax = xHeadMax if xHeadMax > xHead else xHead
        yHeadMin = yHeadMin if yHeadMin < yHead else yHead
        yHeadMax = yHeadMax if yHeadMax > yHead else yHead
      maxHalfDiameter = self._hyperparameters["trackOnlyOnROI_halfDiameter"]
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
    if self._hyperparameters["adjustMinPixelDiffForBackExtract_nbBlackPixelsMax"]:
      minPixel2nbBlackPixels = {}
      countTries = 0
      nbBlackPixels = 0
      nbBlackPixelsMax = int(self._hyperparameters["adjustMinPixelDiffForBackExtract_nbBlackPixelsMax"])
      while (minPixelDiffForBackExtract > 0) and (countTries < 30) and not(minPixelDiffForBackExtract in minPixel2nbBlackPixels):
        if countTries > 0:
          curFrame = grey[ytop:ytop+lenY, xtop:xtop+lenX]
          if self._hyperparameters["trackOnlyOnROI_halfDiameter"] != 0 and frameNumber != self._hyperparameters["firstFrame"] and xHead != 0 and yHead != 0:
            curFrame = curFrame[ymin:ymax, xmin:xmax]
          putToWhite = ( curFrame.astype('int32') >= (back.astype('int32') - minPixelDiffForBackExtract) )
          curFrame[putToWhite] = 255
        ret, thresh1 = cv2.threshold(curFrame, self._hyperparameters["thresholdForBlobImg"], 255, cv2.THRESH_BINARY)
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
      self._hyperparameters["minPixelDiffForBackExtractHead"] = minPixelDiffForBackExtract
      curFrame = grey[ytop:ytop+lenY, xtop:xtop+lenX]
      if self._hyperparameters["trackOnlyOnROI_halfDiameter"] != 0 and frameNumber != self._hyperparameters["firstFrame"] and xHead != 0 and yHead != 0:
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

    if debug:
      self._debugFrame(frame, title='Frame')

    if self._hyperparameters["trackOnlyOnROI_halfDiameter"] != 0:
      ret, res = cv2.threshold(curFrame, self._hyperparameters["thresholdForBlobImg"], 255, cv2.THRESH_BINARY)
      if ret:
        reinitialize = 1
        contours, hierarchy = cv2.findContours(res, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        for contour in contours:
          contourArea = cv2.contourArea(contour)
          if contourArea > self._hyperparameters["minAreaBody"] and contourArea < self._hyperparameters["maxAreaBody"]:
            reinitialize = 0
        if reinitialize and type(curFrameInitial) != int:
          curFrame = curFrameInitial
          initialCurFrame = initialCurFrameInitial
          back = backInitial

    return [curFrame, initialCurFrame, back, xmin, ymin]

  def getForegroundImage(self, background, frameNumber, wellNumber):
    minPixelDiffForBackExtract = self._hyperparameters["minPixelDiffForBackExtract"]
    if "minPixelDiffForBackExtractHead" in self._hyperparameters:
      minPixelDiffForBackExtract = self._hyperparameters["minPixelDiffForBackExtractHead"]
    debug = 0

    if len(self._wellPositions):
      xtop = self._wellPositions[wellNumber]['topLeftX']
      ytop = self._wellPositions[wellNumber]['topLeftY']
      lenX = self._wellPositions[wellNumber]['lengthX']
      lenY = self._wellPositions[wellNumber]['lengthY']
    else:
      xtop = 0
      ytop = 0
      lenX = len(background[0])
      lenY = len(background)

    back = background[ytop:ytop+lenY, xtop:xtop+lenX]

    cap = zzVideoReading.VideoCapture(self._videoPath)
    cap.set(1, frameNumber)
    ret, frame = cap.read()

    if not(ret):
      if self._hyperparameters["searchPreviousFramesIfCurrentFrameIsCorrupted"]:
        currentFrameNum = int(cap.get(1))
        while not(ret) and currentFrameNum:
          currentFrameNum = currentFrameNum - 1
          cap.set(1, currentFrameNum)
          ret, frame = cap.read()
      else:
        frame = back.copy()

    if self._hyperparameters["invertBlackWhiteOnImages"]:
      frame = 255 - frame

    if self._hyperparameters["imagePreProcessMethod"]:
      frame = preprocessImage(frame, self._hyperparameters)

    grey = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    curFrame = grey[ytop:ytop+lenY, xtop:xtop+lenX]
    initialCurFrame = curFrame.copy()

    # if False:
    putToWhite = ( curFrame.astype('int32') >= (back.astype('int32') - minPixelDiffForBackExtract) )

    curFrame[putToWhite] = 255
    previousNbBlackPixels = []
    if self._hyperparameters["adjustMinPixelDiffForBackExtract_nbBlackPixelsMax"]:
      minPixel2nbBlackPixels = {}
      countTries = 0
      nbBlackPixels = 0
      nbBlackPixelsMax = int(self._hyperparameters["adjustMinPixelDiffForBackExtract_nbBlackPixelsMax"])
      while (minPixelDiffForBackExtract > 0) and (countTries < 30) and not(minPixelDiffForBackExtract in minPixel2nbBlackPixels):
        if countTries > 0:
          curFrame = grey[ytop:ytop+lenY, xtop:xtop+lenX]
          putToWhite = ( curFrame.astype('int32') >= (back.astype('int32') - minPixelDiffForBackExtract) )
          curFrame[putToWhite] = 255
        ret, thresh1 = cv2.threshold(curFrame, self._hyperparameters["thresholdForBlobImg"], 255, cv2.THRESH_BINARY)
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
      self._hyperparameters["minPixelDiffForBackExtractHead"] = minPixelDiffForBackExtract
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

    if debug:
      self._debugFrame(frame, title='Frame')

    return [curFrame, initialCurFrame, back]

  def getImageSequential(self, cap, frameNumber, wellNumber):
    minPixelDiffForBackExtract = self._hyperparameters["minPixelDiffForBackExtract"]
    debug = 0

    xtop = self._wellPositions[wellNumber]['topLeftX']
    ytop = self._wellPositions[wellNumber]['topLeftY']
    lenX = self._wellPositions[wellNumber]['lengthX']
    lenY = self._wellPositions[wellNumber]['lengthY']

    ret, frame = cap.read()

    while not(ret):
      print("WARNING: was not able to extract the frame", str(frameNumber),"in 'getImageSequential'")
      frameNumber = frameNumber - 1
      cap.set(1, frameNumber)
      ret, frame = cap.read()

    if self._hyperparameters["invertBlackWhiteOnImages"]:
      frame = 255 - frame

    if self._hyperparameters["imagePreProcessMethod"]:
      frame = preprocessImage(frame, self._hyperparameters)

    grey = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    curFrame = grey[ytop:ytop+lenY, xtop:xtop+lenX]

    if debug:
      self._debugFrame(curFrame, title='Frame')

    return curFrame

  def headEmbededFrame(self, frameNumber, wellNumber):
    debug = 0

    cap = zzVideoReading.VideoCapture(self._videoPath)

    cap.set(1, frameNumber)
    ret, frame = cap.read()

    while not(ret):
      print("WARNING: couldn't read the frameNumber", frameNumber, "for the video", self._hyperparameters["videoName"])
      frameNumber = frameNumber - 1
      cap.set(1, frameNumber)
      ret, frame = cap.read()

    xtop = self._wellPositions[wellNumber]['topLeftX']
    ytop = self._wellPositions[wellNumber]['topLeftY']
    lenX = self._wellPositions[wellNumber]['lengthX']
    lenY = self._wellPositions[wellNumber]['lengthY']
    frame = frame[ytop:ytop+lenY, xtop:xtop+lenX]

    if ("invertBlackWhiteOnImages" in self._hyperparameters) and self._hyperparameters["invertBlackWhiteOnImages"]:
      frame = 255 - frame

    if ("imagePreProcessMethod" in self._hyperparameters) and self._hyperparameters["imagePreProcessMethod"]:
      frame = preprocessImage(frame, self._hyperparameters)

    kernel = np.ones((8,8),np.float32)/25
    thres1  = cv2.filter2D(frame,-1,kernel)
    retval, thres1 = cv2.threshold(thres1, 80, 255, cv2.THRESH_BINARY)
    thres1 = 255 - thres1

    frame = 255 - frame

    if (debug):
      self._debugFrame(frame, title='thres1')
      self._debugFrame(thres1, title='thres1')

    frame  = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    thres1 = cv2.cvtColor(thres1, cv2.COLOR_BGR2GRAY)

    return [frame, thres1]

  def headEmbededFrameBackExtract(self, background, frameNumber, wellNumber):
    minPixelDiffForBackExtract = self._hyperparameters["minPixelDiffForBackExtract"]
    debug = 0

    cap = zzVideoReading.VideoCapture(self._videoPath)

    cap.set(1, frameNumber)
    ret, frame = cap.read()

    while not(ret):
      print("WARNING: couldn't read the frameNumber", frameNumber, "for the video", self._hyperparameters["videoName"])
      frameNumber = frameNumber - 1
      cap.set(1, frameNumber)
      ret, frame = cap.read()

    xtop = self._wellPositions[wellNumber]['topLeftX']
    ytop = self._wellPositions[wellNumber]['topLeftY']
    lenX = self._wellPositions[wellNumber]['lengthX']
    lenY = self._wellPositions[wellNumber]['lengthY']
    frame = frame[ytop:ytop+lenY, xtop:xtop+lenX]
    background = background[ytop:ytop+lenY, xtop:xtop+lenX]

    if ("invertBlackWhiteOnImages" in self._hyperparameters) and self._hyperparameters["invertBlackWhiteOnImages"]:
      frame = 255 - frame

    if ("imagePreProcessMethod" in self._hyperparameters) and self._hyperparameters["imagePreProcessMethod"]:
      frame = preprocessImage(frame, self._hyperparameters)

    kernel = np.ones((8,8),np.float32)/25
    thres1  = cv2.filter2D(frame,-1,kernel)
    retval, thres1 = cv2.threshold(thres1, 80, 255, cv2.THRESH_BINARY)

    frame  = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    thres1 = cv2.cvtColor(thres1, cv2.COLOR_BGR2GRAY)

    if debug:
      self._debugFrame(frame, title='thres1')

    putToWhite = ( frame.astype('int32') >= (background.astype('int32') + minPixelDiffForBackExtract) )
    # This puts the pixels that belong to a fish to white
    frame[putToWhite] = 255

    if debug:
      self._debugFrame(frame, title='thres1')
      # cv2.imshow('thres1', thres1)
      # cv2.waitKey(0)

    thres1 = 255 - thres1
    frame  = 255 - frame

    return [frame, thres1]

  def _headEmbededFrameSequential(self, cap, frameNumber, wellNumber):
    debug = 0

    ret, frame = cap.read()

    while not(ret):
      print("WARNING: couldn't read the frameNumber", frameNumber, "for the video", self._hyperparameters["videoName"])
      frameNumber = frameNumber - 1
      cap.set(1, frameNumber)
      ret, frame = cap.read()

    xtop = self._wellPositions[wellNumber]['topLeftX']
    ytop = self._wellPositions[wellNumber]['topLeftY']
    lenX = self._wellPositions[wellNumber]['lengthX']
    lenY = self._wellPositions[wellNumber]['lengthY']
    frame = frame[ytop:ytop+lenY, xtop:xtop+lenX]

    if ("invertBlackWhiteOnImages" in self._hyperparameters) and self._hyperparameters["invertBlackWhiteOnImages"]:
      frame = 255 - frame

    if ("imagePreProcessMethod" in self._hyperparameters) and self._hyperparameters["imagePreProcessMethod"]:
      frame = preprocessImage(frame, self._hyperparameters)

    kernel = np.ones((8,8),np.float32)/25
    thres1  = cv2.filter2D(frame,-1,kernel)
    retval, thres1 = cv2.threshold(thres1, 80, 255, cv2.THRESH_BINARY)
    thres1 = 255 - thres1

    frame = 255 - frame

    if debug:
      self._debugFrame(frame, title='thres1')
      self._debugFrame(thres1, title='thres1')

    frame  = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    thres1 = cv2.cvtColor(thres1, cv2.COLOR_BGR2GRAY)

    return [frame, thres1]

  def _headEmbededFrameSequentialBackExtract(self, cap, frameNumber, wellNumber):
    minPixelDiffForBackExtract = self._hyperparameters["minPixelDiffForBackExtract"]
    debug = 0

    ret, frame = cap.read()

    while not(ret):
      print("WARNING: couldn't read the frameNumber", frameNumber, "for the video", self._hyperparameters["videoName"])
      frameNumber = frameNumber - 1
      cap.set(1, frameNumber)
      ret, frame = cap.read()

    xtop = self._wellPositions[wellNumber]['topLeftX']
    ytop = self._wellPositions[wellNumber]['topLeftY']
    lenX = self._wellPositions[wellNumber]['lengthX']
    lenY = self._wellPositions[wellNumber]['lengthY']
    frame = frame[ytop:ytop+lenY, xtop:xtop+lenX]
    background = self._background[ytop:ytop+lenY, xtop:xtop+lenX]

    if ("invertBlackWhiteOnImages" in self._hyperparameters) and self._hyperparameters["invertBlackWhiteOnImages"]:
      frame = 255 - frame

    if ("imagePreProcessMethod" in self._hyperparameters) and self._hyperparameters["imagePreProcessMethod"]:
      frame = preprocessImage(frame, self._hyperparameters)

    kernel = np.ones((8,8),np.float32)/25
    thres1  = cv2.filter2D(frame,-1,kernel)
    retval, thres1 = cv2.threshold(thres1, 80, 255, cv2.THRESH_BINARY)

    frame  = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
    thres1 = cv2.cvtColor(thres1, cv2.COLOR_BGR2GRAY)

    if debug:
      self._debugFrame(frame, title='thres1')

    putToWhite = ( frame.astype('int32') >= (background.astype('int32') + minPixelDiffForBackExtract) )
    # This puts the pixels that belong to a fish to white
    frame[putToWhite] = 255

    if (debug):
      self._debugFrame(frame, title='thres1')

    thres1 = 255 - thres1
    frame  = 255 - frame

    return [frame, thres1]

  def _getImages(self, cap, i, wellNumber, alreadyExtractedImage=0, trackingHeadTailAllAnimals=0):
    xHead = 0
    yHead = 0

    initialCurFrame = 0
    back = 0

    if self._hyperparameters["headEmbeded"]:
      if self._hyperparameters["headEmbededRemoveBack"] == 0:
        if self._hyperparameters["adjustHeadEmbededTracking"] == 0 and not self._hyperparameters["adjustHeadEmbeddedEyeTracking"]:
          [frame, thresh1] = self._headEmbededFrameSequential(cap, i, wellNumber)
        else:
          [frame, thresh1] = self.headEmbededFrame(i, wellNumber)
        gray = frame.copy()
      else:
        if self._hyperparameters["adjustHeadEmbededTracking"] == 0 and not self._hyperparameters["adjustHeadEmbeddedEyeTracking"]:
          [frame, thresh1] = self._headEmbededFrameSequentialBackExtract(cap, i, wellNumber)
        else:
          [frame, thresh1] = self.headEmbededFrameBackExtract(self._background, i, wellNumber)
        gray = frame.copy()
    else:
      if self._hyperparameters["adjustFreelySwimTracking"] == 0 and self._hyperparameters["adjustFreelySwimTrackingAutomaticParameters"] == 0:
        if len(self._background):
          [frame, initialCurFrame, back, xHead, yHead] = self._getForegroundImageSequential(cap, i, wellNumber, alreadyExtractedImage, trackingHeadTailAllAnimals)
        else:
          frame = self.getImageSequential(cap, i, wellNumber)
      else:
        if len(self._background):
          [frame, initialCurFrame, back] = self.getForegroundImage(self._background, i, wellNumber)
        else:
          frame = self._getImage(i, wellNumber)

      gray = frame.copy()

      ret,thresh1 = cv2.threshold(gray,self._hyperparameters["thresholdForBlobImg"],255,cv2.THRESH_BINARY)

    coverHorizontalPortionBelowForHeadDetect = self._hyperparameters["coverHorizontalPortionBelowForHeadDetect"]
    if coverHorizontalPortionBelowForHeadDetect != -1:
      gray[coverHorizontalPortionBelowForHeadDetect:len(gray)-1,:] = 255

    coverHorizontalPortionAboveForHeadDetect = self._hyperparameters["coverHorizontalPortionAboveForHeadDetect"]
    if coverHorizontalPortionAboveForHeadDetect != -1:
      gray[0:coverHorizontalPortionAboveForHeadDetect,:] = 255

    coverVerticalPortionRightForHeadDetect = self._hyperparameters["coverVerticalPortionRightForHeadDetect"]
    if coverVerticalPortionRightForHeadDetect != -1:
      gray[:,coverVerticalPortionRightForHeadDetect:len(gray[0])-1] = 255

    coverPortionForHeadDetect = self._hyperparameters["coverPortionForHeadDetect"]
    if coverPortionForHeadDetect == "Bottom":
      gray[int(len(gray)/2):len(gray)-1, :] = 255
    if coverPortionForHeadDetect == "Top":
      gray[0:int(len(gray)/2), :] = 255
    if coverPortionForHeadDetect == "Left":
      gray[:, 0:int(len(gray[0])/2)] = 255
    if coverPortionForHeadDetect == "Right":
      gray[:, int(len(gray[0])/2):len(gray[0])-1] = 255

    if self._hyperparameters["debugCoverHorizontalPortionBelow"] and i==self._firstFrame:
      self._debugFrame(gray, title='Frame')

    # paramGaussianBlur = int((self._hyperparameters["paramGaussianBlur"] / 2)) * 2 + 1
    # blur = cv2.GaussianBlur(gray, (paramGaussianBlur, paramGaussianBlur), 0)
    blur = 0

    frame2 = frame #frame.copy()

    if self._hyperparameters["erodeIter"] or self._hyperparameters["dilateIter"]:
      erodeSize = self._hyperparameters["erodeSize"]
      kernel  = np.ones((erodeSize,erodeSize), np.uint8)

    if self._hyperparameters["erodeIter"]:
      thresh1 = cv2.erode(thresh1, kernel, iterations=self._hyperparameters["erodeIter"])

    if self._hyperparameters["dilateIter"]:
      thresh2 = thresh1.copy()
      thresh2 = cv2.dilate(thresh2, kernel, iterations=self._hyperparameters["dilateIter"])
    else:
      thresh2 = thresh1

    return [frame, gray, thresh1, blur, thresh2, frame2, initialCurFrame, back, xHead, yHead]
