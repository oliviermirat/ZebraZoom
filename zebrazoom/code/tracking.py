import numpy as np
import cv2
import zebrazoom.videoFormatConversion.zzVideoReading as zzVideoReading
import math
import os
import pickle
import sys
import queue

from zebrazoom.code.extractParameters import extractParameters

from zebrazoom.code.eyeTracking import EyeTrackingMixin
from zebrazoom.code.getImages import GetImagesMixin
from zebrazoom.code.tailTracking import TailTrackingMixin

from zebrazoom.mainZZ import BaseTrackingMethod, register_tracking_method
from zebrazoom.code.vars import getGlobalVariables
globalVariables = getGlobalVariables()


class _TailTrackingDifficultBackgroundMixin:
  def _getCoordinates(self, frame, title, zoomable, dialog):
    raise ValueError("Some of the required inputs were not specified, please specify them in advance or run tracking from the GUI.") # TODO: a better exception?

  @staticmethod
  def __simpleOptimalValueSearch(PtClosest, contour, unitVector, lenX, lenY):
    factor = 0
    dist = 1
    maxDist = 0
    indMax = 0
    testCenter = PtClosest + factor * unitVector
    while (dist > 0) and (factor < 20) and (testCenter[0] >= 0) and (testCenter[1] >= 0) and (testCenter[0] < lenX) and (testCenter[1] < lenY):
      factor = factor + 1
      testCenter = PtClosest + factor * unitVector
      testCenter = testCenter.astype(int)
      dist = cv2.pointPolygonTest(contour, (testCenter[0], testCenter[1]), True)
      if dist > maxDist:
        maxDist = dist
        indMax  = factor

    testCenter = PtClosest + indMax * unitVector
    testCenter = testCenter.astype(int)

    return testCenter

  @staticmethod
  def __reajustCenterOfMassIfNecessary(contour, x, y, lenX, lenY):
    inside = cv2.pointPolygonTest(contour, (x, y), True)
    if inside < 0:

      minDist = 100000000000000
      indMin  = 0
      for i in range(0, len(contour)):
        Pt = contour[i][0]
        dist = math.sqrt((Pt[0] - x)**2 + (Pt[1] - y)**2)
        if dist < minDist:
          minDist = dist
          indMin  = i
      PtClosest = contour[indMin][0]
      unitVector = np.array([PtClosest[0] - x, PtClosest[1] - y])
      unitVectorLength = math.sqrt(unitVector[0]**2 + unitVector[1]**2)
      unitVector[0] = unitVector[0] / unitVectorLength
      unitVector[1] = unitVector[1] / unitVectorLength
      if False:
        factor = 5
        testCenter = PtClosest + factor * unitVector
        testCenter = testCenter.astype(int)
        while (cv2.pointPolygonTest(contour, (testCenter[0], testCenter[1]), True) <= 0) and (factor > 1):
          factor = factor - 1
          testCenter = PtClosest + factor * unitVector
      else:
        testCenter = self.__simpleOptimalValueSearch(PtClosest, contour, unitVector, lenX, lenY)

      x = testCenter[0]
      y = testCenter[1]

    return [x, y]

  @staticmethod
  def __fillWhiteHoles(frame):
    frameBeforeWhiteFill = frame.copy()
    im_floodfill = frame.copy()
    h, w = frame.shape[:2]
    mask = np.zeros((h+2, w+2), np.uint8)
    cv2.floodFill(im_floodfill, mask, (0,0), 255);
    im_floodfill_inv = cv2.bitwise_not(im_floodfill)
    frame = frame | im_floodfill_inv

    if cv2.countNonZero(frame) > (len(frame) * len(frame[0])) * 0.95:
      frame = frameBeforeWhiteFill
      print("BACK TO IMAGE BEFORE WHITE FILL")

    return frame

  @staticmethod
  def __erodeThenAddWhiteBorders(frame, kernel):
    frame = cv2.erode(frame, kernel, iterations=1)
    frame[0,:] = 255
    frame[len(frame)-1,:] = 255
    frame[:,0] = 255
    frame[:,len(frame[0])-1] = 255
    return frame

  @staticmethod
  def __erodeThenDilateThenAddWhiteBorders(frame, kernel, nbOfIterations):
    frame = cv2.erode(frame, kernel, iterations=nbOfIterations)
    frame = cv2.dilate(frame, kernel, iterations=nbOfIterations)
    frame[0,:] = 255
    frame[len(frame)-1,:] = 255
    frame[:,0] = 255
    frame[:,len(frame[0])-1] = 255
    return frame

  @staticmethod
  def __addWhiteBorders(frame):
    frame[0,:] = 255
    frame[len(frame)-1,:] = 255
    frame[:,0] = 255
    frame[:,len(frame[0])-1] = 255
    return frame

  def _fishTailTrackingDifficultBackground(self, wellNumber):
    chooseValueForAnimalBodyArea = -1 #600 # -1
    showInitialVideo = True # This is not used anymore, should be removed soon
    iterativelyErodeEachImage = False
    showFramesForDebugging = self._hyperparameters["debugTracking"]
    dist2Threshold = 400
    historyLength  = 1000
    reduceImageResolutionPercentage = self._hyperparameters["reduceImageResolutionPercentage"]

    pathToVideo = os.path.split(self._videoPath)[0]

    kernel  = np.ones((3, 3), np.uint8)
    ROIHalfDiam = -1

    class CustomError(Exception):
      pass

    cap = zzVideoReading.VideoCapture(self._videoPath)
    if (cap.isOpened()== False):
      print("Error opening video stream or file")
    frame_width  = int(cap.get(3))
    frame_height = int(cap.get(4))

    fgbg = cv2.createBackgroundSubtractorKNN(dist2Threshold = dist2Threshold, history = historyLength)

    if os.path.exists(os.path.join(pathToVideo, self._videoName + '_BackgroundKNN_' + str(historyLength) + '.pkl')):
      print("Background already pre-calculated")
      with open(os.path.join(pathToVideo, self._videoName + '_BackgroundKNN_' + str(historyLength) + '.pkl'), 'rb') as handle:
        listOfFramesToSave = pickle.load(handle)
      for i in range(0, len(listOfFramesToSave)):
        print("calculating background, currently at frame:", i)
        frame = listOfFramesToSave[i]
        fgmask = fgbg.apply(frame)
    else:
      print("Background calculation starting")

      listOfFramesToSave = []
      framesToKeep = [i for i in range(0, self._lastFrame - 1, int((self._lastFrame - 1) / historyLength if (self._lastFrame - 1) / historyLength >= 1 else 1))]
      cap.set(1, 0)
      for i in range(0, self._lastFrame):
        ret, frame = cap.read()
        if i in framesToKeep and ret:
          print(i, self._lastFrame)
          frame = cv2.resize(frame, (int(frame_width * reduceImageResolutionPercentage), int(frame_height * reduceImageResolutionPercentage)), interpolation = cv2.INTER_AREA)
          listOfFramesToSave.append(frame)

      listOfFramesToSave.reverse()

      for i in range(0, len(listOfFramesToSave)):
        print("calculating background, currently at frame:", i)
        frame = listOfFramesToSave[i]
        fgmask = fgbg.apply(frame)

      # listOfFramesToSave = []
      # for i in range(0, self._lastFrame - 1, int((self._lastFrame - 1) / historyLength if (self._lastFrame - 1) / historyLength >= 1 else 1))]
        # cap.set(1, self._lastFrame - 1 - i)
        # print("calculating background, currently at frame:", self._lastFrame - 1 - i)
        # ret, frame = cap.read()
        # if ret:
          # frame = cv2.resize(frame, (int(frame_width * reduceImageResolutionPercentage), int(frame_height * reduceImageResolutionPercentage)), interpolation = cv2.INTER_AREA)
          # fgmask = fgbg.apply(frame)
          # listOfFramesToSave.append(frame)
      cap.release()
      with open(os.path.join(pathToVideo, self._videoName + '_BackgroundKNN_' + str(historyLength) + '.pkl'), 'wb') as handle:
        pickle.dump(listOfFramesToSave, handle) #, protocol=pickle.HIGHEST_PROTOCOL)

    cap = zzVideoReading.VideoCapture(self._videoPath)

    i = self._firstFrame
    cap.set(1, self._firstFrame)

    while i < self._lastFrame:

      print(i, self._lastFrame)

      ret, frame = cap.read()

      if ret:

        frameInitialImage = frame.copy()

        if self._hyperparameters["reduceImageResolutionPercentage"]:
          frame = cv2.resize(frame, (int(frame_width * self._hyperparameters["reduceImageResolutionPercentage"]), int(frame_height * self._hyperparameters["reduceImageResolutionPercentage"])), interpolation = cv2.INTER_AREA)
          frameInitialImage = frame.copy()

        if i == self._firstFrame:

          previousCenterDetectedX, previousCenterDetectedY = self._getCoordinates(frame, "Click on the center of the head of the animal", True, True)
          tailTipX, tailTipY = self._getCoordinates(frame, "Click on the tip of the tail of the same animal", True, True)

          frame2 = frame.copy()
          frame2 = fgbg.apply(frame2)
          ret, frame2 = cv2.threshold(frame2, 0, 255, cv2.THRESH_BINARY)
          frame2 = self.__fillWhiteHoles(frame2)
          frame2 = 255 - frame2
          if iterativelyErodeEachImage:
            frame2 = self.__erodeThenAddWhiteBorders(frame2, kernel)
          else:
            frame2 = self.__addWhiteBorders(frame2)
          contours, hierarchy = cv2.findContours(frame2, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
          for contour in contours:
            if cv2.pointPolygonTest(contour, (previousCenterDetectedX, previousCenterDetectedY), False) >= 0:
              animalBodyArea = cv2.contourArea(contour)
              ROIHalfDiam = int(math.sqrt(animalBodyArea) * 4)
          print("animalBodyArea:", animalBodyArea)
          print("ROIHalfDiam:", ROIHalfDiam)
          if showFramesForDebugging:
            self._debugFrame(frame2, title='frame0')

        if chooseValueForAnimalBodyArea > 0:
          animalBodyArea = chooseValueForAnimalBodyArea

        if ROIHalfDiam == -1:
          raise CustomError("An error occurred")

        diffAreaAuthorized = 0.5
        self._hyperparameters["minAreaBody"] = int(animalBodyArea - animalBodyArea * diffAreaAuthorized)
        self._hyperparameters["maxAreaBody"] = int(animalBodyArea + animalBodyArea * diffAreaAuthorized)
        self._hyperparameters["minArea"] = int(animalBodyArea - animalBodyArea * diffAreaAuthorized)
        self._hyperparameters["maxArea"] = int(animalBodyArea + animalBodyArea * diffAreaAuthorized)
        self._hyperparameters["headSize"]    = int(math.sqrt(animalBodyArea) * 2)
        self._hyperparameters["minTailSize"] = int(math.sqrt(animalBodyArea) * 0.5)
        self._hyperparameters["maxTailSize"] = int(math.sqrt(animalBodyArea) * 4)

        xmin = previousCenterDetectedX - ROIHalfDiam if previousCenterDetectedX - ROIHalfDiam > 0 else 0
        xmax = previousCenterDetectedX + ROIHalfDiam if previousCenterDetectedX + ROIHalfDiam < len(frame[0]) else len(frame[0]) - 1
        ymin = previousCenterDetectedY - ROIHalfDiam if previousCenterDetectedY - ROIHalfDiam > 0 else 0
        ymax = previousCenterDetectedY + ROIHalfDiam if previousCenterDetectedY + ROIHalfDiam < len(frame) else len(frame) - 1

        previousCenterDetectedXROICoordinates = previousCenterDetectedX - xmin
        previousCenterDetectedYROICoordinates = previousCenterDetectedY - ymin

        if showInitialVideo:
          initialImage = frame.copy()

        frame = fgbg.apply(frame)

        frame = frame[ymin:ymax, xmin:xmax]

        ret, frame = cv2.threshold(frame, 0, 255, cv2.THRESH_BINARY)

        frame = self.__fillWhiteHoles(frame)

        frame = 255 - frame

        countNbOfRightArea = 0
        distanceToPreviousCenterDetected = 100000000000000000000
        countNbTries = 0
        newCenterDetectedX_ROICordinates = previousCenterDetectedXROICoordinates
        newCenterDetectedY_ROICordinates = previousCenterDetectedYROICoordinates
        mostLikelyContour = 0
        while countNbOfRightArea == 0 and countNbTries < 10:
          countNbTries = countNbTries + 1
          if iterativelyErodeEachImage:
            frame = self.__erodeThenAddWhiteBorders(frame, kernel)
          else:
            frame = self.__addWhiteBorders(frame)
          if showFramesForDebugging:
            self._debugFrame(frame, title='frame1')

          nbOfIterations = 1
          while cv2.countNonZero(255 - frame) < animalBodyArea and nbOfIterations < 10:
            print("try " + str(nbOfIterations))
            frame = self.__erodeThenDilateThenAddWhiteBorders(frame, kernel, nbOfIterations)
            nbOfIterations += 1
            if showFramesForDebugging:
              self._debugFrame(frame, title='frame%d' % str(nbOfIterations))

          if nbOfIterations > 1:
            dist2t = fgbg.getDist2Threshold()
            fgbg.setDist2Threshold(dist2t - dist2t * 0.1)
            print("dist2t set to a smaller value:", dist2t - dist2t * 0.1)
          else:
            if cv2.countNonZero(255 - frame) > 1.5 * animalBodyArea:
              dist2t = fgbg.getDist2Threshold()
              fgbg.setDist2Threshold(dist2t + dist2t * 0.1)
              print("dist2t set to a bigger value:", dist2t + dist2t * 0.1)

          contours, hierarchy = cv2.findContours(frame, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
          for contour in contours:
            contourArea = cv2.contourArea(contour)
            if contourArea > self._hyperparameters["minAreaBody"] and contourArea < self._hyperparameters["maxAreaBody"]:
              countNbOfRightArea = countNbOfRightArea + 1
              M = cv2.moments(contour)
              cx = int(M['m10']/M['m00'])
              cy = int(M['m01']/M['m00'])
              [cx, cy] = self.__reajustCenterOfMassIfNecessary(contour, cx, cy, len(frame[0]), len(frame))
              if math.sqrt((previousCenterDetectedXROICoordinates - cx)**2 + (previousCenterDetectedYROICoordinates - cy)**2) < distanceToPreviousCenterDetected:
                newCenterDetectedX_ROICordinates = cx
                newCenterDetectedY_ROICordinates = cy
                mostLikelyContour = contour

          if not(iterativelyErodeEachImage):
            countNbTries = 10
          # print("First: newCenterDetectedX_ROICordinates, newCenterDetectedY_ROICordinates:", newCenterDetectedX_ROICordinates, newCenterDetectedY_ROICordinates)

          if type(mostLikelyContour) != int:

            cntXmin = 100000000000000
            cntYmin = 100000000000000
            cntXmax = -1
            cntYmax = -1

            for point in mostLikelyContour:
              if point[0][0] < cntXmin:
                cntXmin = point[0][0]
              if point[0][1] < cntYmin:
                cntYmin = point[0][1]
              if point[0][0] > cntXmax:
                cntXmax = point[0][0]
              if point[0][1] > cntYmax:
                cntYmax = point[0][1]

              cntXmin = cntXmin - 10
              cntYmin = cntYmin - 10
              cntXmax = cntXmax + 10
              cntYmax = cntYmax + 10

            if False:

              print("This is False")
              # for point in mostLikelyContour:
                # point[0][0] = point[0][0] - cntXmin
                # point[0][1] = point[0][1] - cntYmin

              # blank = np.zeros((cntYmax - cntYmin, cntXmax - cntXmin, 3), np.uint8)
              # blank = 255 - blank

              # blank = cv2.fillPoly(blank, pts =[mostLikelyContour], color=(0, 0, 0))

              # blank = cv2.dilate(blank, kernel, iterations=1)
              # blankIni = blank.copy()

              # nbDilationCount = 0
              # blankPreviousIteration = blank

              # while cv2.countNonZero(cv2.cvtColor(255 - blank, cv2.COLOR_BGR2GRAY)) != 0 and nbDilationCount < 10:
                # blankPreviousIteration = cv2.cvtColor(blank.copy(), cv2.COLOR_BGR2GRAY)
                # blank = cv2.dilate(blank, kernel, iterations=1)
                # nbDilationCount = nbDilationCount + 1

              # contours, hierarchy = cv2.findContours(blankPreviousIteration, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
              # largestContourArea = 0
              # for contour in contours:
                # contourArea = cv2.contourArea(contour)
                # if contourArea > largestContourArea:
                  # largestContourArea = contourArea
                  # M = cv2.moments(contour)
                  # x = int(M['m10']/M['m00'])
                  # y = int(M['m01']/M['m00'])
                  # if False:
                    # [newCenterDetectedX_ROICordinates, newCenterDetectedY_ROICordinates] = self.__reajustCenterOfMassIfNecessary(contour, x, y, len(blankPreviousIteration[0]), len(blankPreviousIteration))
                  # newCenterDetectedX_ROICordinates = x
                  # newCenterDetectedY_ROICordinates = y

            else:

              cntXmin = 10
              cntYmin = 10

              blank = np.zeros((xmax - xmin, ymax - ymin, 3), np.uint8)
              blank = 255 - blank

              blank = cv2.fillPoly(blank, pts =[mostLikelyContour], color=(0, 0, 0))

              blank = cv2.dilate(blank, kernel, iterations=1)
              blankIni = blank.copy()

              nbDilationCount = 0
              blankPreviousIteration = blank

              while cv2.countNonZero(cv2.cvtColor(255 - blank, cv2.COLOR_BGR2GRAY)) != 0 and nbDilationCount < 10:
                blankPreviousIteration = cv2.cvtColor(blank.copy(), cv2.COLOR_BGR2GRAY)
                blank = cv2.dilate(blank, kernel, iterations=1)
                nbDilationCount = nbDilationCount + 1

              if type(blankPreviousIteration) == np.ndarray and len(blankPreviousIteration) and len(blankPreviousIteration[0]) and type(blankPreviousIteration[0][0]) == np.uint8:
                contours, hierarchy = cv2.findContours(blankPreviousIteration, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
                largestContourArea = 0
                for contour in contours:
                  contourArea = cv2.contourArea(contour)
                  if contourArea > largestContourArea and contourArea < (len(blankPreviousIteration)*len(blankPreviousIteration[0])) * 0.8:
                    largestContourArea = contourArea
                    M = cv2.moments(contour)
                    x = int(M['m10']/M['m00'])
                    y = int(M['m01']/M['m00'])
                    # if False:
                      # [newCenterDetectedX_ROICordinates, newCenterDetectedY_ROICordinates] = self.__reajustCenterOfMassIfNecessary(contour, x, y, len(blankPreviousIteration[0]), len(blankPreviousIteration))
                    newCenterDetectedX_ROICordinates = x
                    newCenterDetectedY_ROICordinates = y

        # print("Second: newCenterDetectedX_ROICordinates, newCenterDetectedY_ROICordinates:", newCenterDetectedX_ROICordinates, newCenterDetectedY_ROICordinates)

        self._trackingHeadTailAllAnimals[0, i-self._firstFrame][0][0] = newCenterDetectedX_ROICordinates
        self._trackingHeadTailAllAnimals[0, i-self._firstFrame][0][1] = newCenterDetectedY_ROICordinates

        if self._hyperparameters["trackTail"] == 1:
          if type(blankIni) == np.ndarray and len(blankIni) and len(blankIni[0]):
            if type(blankIni[0][0]) != np.uint8:
              blankIni = cv2.cvtColor(blankIni, cv2.COLOR_BGR2GRAY)
            for animalId in range(0, self._hyperparameters["nbAnimalsPerWell"]):
              self._tailTracking(animalId, i, blankIni, blankIni, blankIni, 0, self._trackingHeadTailAllAnimals, self._trackingHeadingAllAnimals, 0, 0, 0, blankIni, 0, wellNumber)
          else:
            print("problem")

        for j in range(0, len(self._trackingHeadTailAllAnimals[0, i-self._firstFrame])):
          self._trackingHeadTailAllAnimals[0, i-self._firstFrame][j][0] += xmin + cntXmin - 10
          self._trackingHeadTailAllAnimals[0, i-self._firstFrame][j][1] += ymin + cntYmin - 10

        self._debugTracking(i, self._trackingHeadTailAllAnimals, self._trackingHeadingAllAnimals, initialImage)
        # if showInitialVideo:
          # initialImage = cv2.circle(initialImage, (newCenterDetectedX_ROICordinates + xmin + cntXmin - 10, newCenterDetectedY_ROICordinates + ymin + cntYmin - 10), 3, (255, 0, 0), 2)
          # cv2.imshow("frame", initialImage)
          # cv2.waitKey(0)
        # else:
          # frame = cv2.circle(frame, (newCenterDetectedX_ROICordinates, newCenterDetectedY_ROICordinates), 3, (255, 0, 0), 2)
          # cv2.imshow("frame", frame)
          # cv2.waitKey(0)

        previousCenterDetectedX = newCenterDetectedX_ROICordinates + xmin + cntXmin - 10
        previousCenterDetectedY = newCenterDetectedY_ROICordinates + ymin + cntYmin - 10

      i = i + 1

    return [self._trackingHeadTailAllAnimals, self._trackingHeadingAllAnimals, 0]


class Tracking(BaseTrackingMethod, _TailTrackingDifficultBackgroundMixin, EyeTrackingMixin, GetImagesMixin, TailTrackingMixin):
  def __init__(self, videoPath, background, wellPositions, hyperparameters, dlModel=0):
    self._videoPath = videoPath
    self._background = background
    self._wellPositions = wellPositions
    self._hyperparameters = hyperparameters
    self._dlModel = dlModel
    self._videoName = os.path.splitext(os.path.basename(videoPath))[0]
    self._auDessusPerAnimalId = None
    self._firstFrame = self._hyperparameters["firstFrame"] if self._hyperparameters["firstFrameForTracking"] == -1 else self._hyperparameters["firstFrameForTracking"]
    self._lastFrame = self._hyperparameters["lastFrame"]
    self._nbTailPoints = self._hyperparameters["nbTailPoints"]
    self._headPositionFirstFrame = []
    self._tailTipFirstFrame = []
    self._trackingHeadTailAllAnimals = np.zeros((self._hyperparameters["nbAnimalsPerWell"], self._lastFrame-self._firstFrame+1, self._nbTailPoints, 2))
    self._trackingHeadingAllAnimals = np.zeros((self._hyperparameters["nbAnimalsPerWell"], self._lastFrame-self._firstFrame+1))
    if self._hyperparameters["eyeTracking"]:
      self._trackingEyesAllAnimals = np.zeros((self._hyperparameters["nbAnimalsPerWell"], self._lastFrame-self._firstFrame+1, 8))
    else:
      self._trackingEyesAllAnimals = 0

    if not(self._hyperparameters["nbAnimalsPerWell"] > 1 or self._hyperparameters["forceBlobMethodForHeadTracking"]) and not(self._hyperparameters["headEmbeded"]) and (self._hyperparameters["findHeadPositionByUserInput"] == 0) and (self._hyperparameters["takeTheHeadClosestToTheCenter"] == 0):
      self._trackingProbabilityOfGoodDetection = np.zeros((self._hyperparameters["nbAnimalsPerWell"], self._lastFrame-self._firstFrame+1))
    else:
      self._trackingProbabilityOfGoodDetection = 0

    self.useGUI = True

  def _adjustParameters(self, i, initialCurFrame, frame, frame2, widgets):
    pass

  def _addBlackLineToImgSetParameters(self, frame):
    pass

  def findTailTipByUserInput(self, frame, frameNumber, wellNumber):
    pass

  def findHeadPositionByUserInput(self, frame, frameNumber, wellNumber):
    pass

  def _getTailTipByFileSaved(self):
    ix = -1
    iy = -1
    with open(self._videoPath+'.csv') as csv_file:
      csv_reader = csv.reader(csv_file, delimiter=',')
      line_count = 0
      for row in csv_reader:
        if len(row):
          ix = row[0]
          iy = row[1]
    return [int(ix),int(iy)]

  def _getHeadPositionByFileSaved(self):
    ix = -1
    iy = -1
    with open(self._videoPath+'HP.csv') as csv_file:
      csv_reader = csv.reader(csv_file, delimiter=',')
      line_count = 0
      for row in csv_reader:
        if len(row):
          ix = row[0]
          iy = row[1]
    return [int(ix),int(iy)]

  def _detectMovementWithRawVideoInsideTracking(self, xHead, yHead, initialCurFrame):
    previousFrames   = queue.Queue(self._hyperparameters["frameGapComparision"])
    previousXYCoords = queue.Queue(self._hyperparameters["frameGapComparision"])
    self._auDessusPerAnimalId = [np.zeros((self._lastFrame-self._firstFrame+1, 1)) for _ in range(self._hyperparameters["nbAnimalsPerWell"])]
    halfDiameterRoiBoutDetect = self._hyperparameters["halfDiameterRoiBoutDetect"]
    if previousFrames.full():
      previousFrame   = previousFrames.get()
      curFrame        = initialCurFrame.copy()
      previousXYCoord = previousXYCoords.get()
      curXYCoord      = [xHead, yHead]
      if previousXYCoord[0] < curXYCoord[0]:
        previousFrame = previousFrame[:, (curXYCoord[0]-previousXYCoord[0]):]
      elif previousXYCoord[0] > curXYCoord[0]:
        curFrame      = curFrame[:, (previousXYCoord[0]-curXYCoord[0]):]
      if previousXYCoord[1] < curXYCoord[1]:
        previousFrame = previousFrame[(curXYCoord[1]-previousXYCoord[1]):, :]
      elif previousXYCoord[1] > curXYCoord[1]:
        curFrame      = curFrame[(previousXYCoord[1]-curXYCoord[1]):, :]
      maxX = min(len(previousFrame[0]), len(curFrame[0]))
      maxY = min(len(previousFrame), len(curFrame))

      previousFrame = previousFrame[:maxY, :maxX]
      curFrame      = curFrame[:maxY, :maxX]

      # Possible optimization in the future: refine the ROI based on halfDiameterRoiBoutDetect !!!

      res = cv2.absdiff(previousFrame, curFrame)
      ret, res = cv2.threshold(res,self._hyperparameters["thresForDetectMovementWithRawVideo"],255,cv2.THRESH_BINARY)

      totDiff = cv2.countNonZero(res)
      for animalId in range(self._hyperparameters["nbAnimalsPerWell"]):
        if totDiff > self._hyperparameters["minNbPixelForDetectMovementWithRawVideo"]:
          self._auDessusPerAnimalId[animalId][i-self._firstFrame] = 1
        else:
          self._auDessusPerAnimalId[animalId][i-self._firstFrame] = 0
    else:
      self._auDessusPerAnimalId[animalId][i-self._firstFrame] = 0
    previousFrames.put(initialCurFrame)
    previousXYCoords.put([xHead, yHead])

  def _trackingDL(self, wellNumber, device):
    import torch
    debugPlus = False
    # dicotomySearchOfOptimalBlobArea = self._hyperparameters["trackingDLdicotomySearchOfOptimalBlobArea"] # 500 # 700 # 850
    # applySimpleThresholdOnPredictedMask = self._hyperparameters["applySimpleThresholdOnPredictedMask"] # 230

    xtop = self._wellPositions[wellNumber]['topLeftX']
    ytop = self._wellPositions[wellNumber]['topLeftY']
    lenX = self._wellPositions[wellNumber]['lengthX']
    lenY = self._wellPositions[wellNumber]['lengthY']

    cap = zzVideoReading.VideoCapture(self._videoPath)
    if (cap.isOpened()== False):
      print("Error opening video stream or file")

    # Performing the tracking on each frame
    i = self._firstFrame
    cap.set(1, self._firstFrame)
    if int(self._hyperparameters["onlyDoTheTrackingForThisNumberOfFrames"]) != 0:
      self._lastFrame = min(self._lastFrame, self._firstFrame + int(self._hyperparameters["onlyDoTheTrackingForThisNumberOfFrames"]))
    while (i < self._lastFrame+1):

      if (self._hyperparameters["freqAlgoPosFollow"] != 0) and (i % self._hyperparameters["freqAlgoPosFollow"] == 0):
        print("Tracking: wellNumber:",wellNumber," ; frame:",i)
        if self._hyperparameters["popUpAlgoFollow"]:
          from zebrazoom.code.popUpAlgoFollow import prepend
          prepend("Tracking: wellNumber:" + str(wellNumber) + " ; frame:" + str(i))
      if self._hyperparameters["debugTracking"]:
        print("frame:",i)

      ret, frame = cap.read()
      if self._hyperparameters["unet"]:
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        quartileChose = 0.03
        lowVal  = int(np.quantile(frame, quartileChose))
        highVal = int(np.quantile(frame, 1 - quartileChose))
        frame[frame < lowVal]  = lowVal
        frame[frame > highVal] = highVal
        frame = frame - lowVal
        mult  = np.max(frame)
        frame = frame * (255/mult)
        frame = frame.astype('uint8')

      if not(ret):
        currentFrameNum = int(cap.get(1))
        while not(ret):
          currentFrameNum = currentFrameNum - 1
          cap.set(1, currentFrameNum)
          ret, frame = cap.read()
          if self._hyperparameters["unet"]:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            quartileChose = 0.01
            lowVal  = int(np.quantile(frame, quartileChose))
            highVal = int(np.quantile(frame, 1 - quartileChose))
            frame[frame < lowVal]  = lowVal
            frame[frame > highVal] = highVal
            frame = frame - lowVal
            mult  = np.max(frame)
            frame = frame * (255/mult)
            frame = frame.astype('uint8')

      if self._hyperparameters["unet"]:
        grey = frame
      else:
        grey = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY

      curFrame = grey[ytop:ytop+lenY, xtop:xtop+lenX]

      if self._hyperparameters["unet"]:

        device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        imgTorch = torch.from_numpy(curFrame/255)
        imgTorch = imgTorch.unsqueeze(0).unsqueeze(0)
        imgTorch = imgTorch.to(device=device, dtype=torch.float32)

        output = dlModel(imgTorch).cpu()

        import torch.nn.functional as F
        output = F.interpolate(output, (len(curFrame[1]), len(curFrame)), mode='bilinear')
        if dlModel.n_classes > 1:
            mask = output.argmax(dim=1)
        else:
            mask = torch.sigmoid(output) > out_threshold
        thresh2 = mask[0].long().squeeze().numpy()
        thresh2 = thresh2 * 255
        thresh2 = thresh2.astype('uint8')

        thresh3 = thresh2.copy()

        if self._hyperparameters["debugTracking"]:
          self._debugFrame(thresh2, title='After Unet')

        lastFirstTheta = self._headTrackingHeadingCalculation(i, thresh2, thresh2, thresh2, thresh2, self._hyperparameters["erodeSize"], frame_width, frame_height, self._trackingHeadingAllAnimals, self._trackingHeadTailAllAnimals, trackingProbabilityOfGoodDetection, 0, self._wellPositions[wellNumber]["lengthX"])

        if self._hyperparameters["trackTail"] == 1:
          for animalId in range(0, self._hyperparameters["nbAnimalsPerWell"]):
            self._tailTracking(animalId, i, thresh3, thresh3, thresh3, 0, self._trackingHeadTailAllAnimals, self._trackingHeadingAllAnimals, 0, 0, 0, thresh3, 0, wellNumber)

        # Debug functions
        self._debugTracking(i, self._trackingHeadTailAllAnimals, self._trackingHeadingAllAnimals, curFrame)

      else: # mask rcnn

        oneChannel  = curFrame.tolist()
        oneChannel2 = [[a/255 for a in list] for list in oneChannel]
        imgTorch    = torch.tensor([oneChannel2, oneChannel2, oneChannel2])

        with torch.no_grad():
          prediction = self._dlModel([imgTorch.to(device)])

        if len(prediction) and len(prediction[0]['masks']):
          thresh = prediction[0]['masks'][0, 0].mul(255).byte().cpu().numpy()
          if debugPlus:
            self._debugFrame(255 - thresh, title="thresh")

          if self._hyperparameters["applySimpleThresholdOnPredictedMask"]:
            ret, thresh2 = cv2.threshold(thresh, self._hyperparameters["applySimpleThresholdOnPredictedMask"], 255, cv2.THRESH_BINARY)
            if self._hyperparameters["simpleThresholdCheckMinForMaxCountour"]:
              contours, hierarchy = cv2.findContours(thresh2, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
              maxContourArea = 0
              for contour in contours:
                area = cv2.contourArea(contour)
                if area > maxContourArea:
                  maxContourArea = area
              if maxContourArea < self._hyperparameters["simpleThresholdCheckMinForMaxCountour"]:
                print("maxContour found had a value that's too low (for wellNumber:", wellNumber, ", frame:", i,")")
                countNonZeroTarget = self._hyperparameters["trackingDLdicotomySearchOfOptimalBlobArea"]
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
            if self._hyperparameters["trackingDLdicotomySearchOfOptimalBlobArea"]:
              countNonZeroTarget = self._hyperparameters["trackingDLdicotomySearchOfOptimalBlobArea"]
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
            self._debugFrame(255 - thresh2, title="thresh2")

          lastFirstTheta = self._headTrackingHeadingCalculation(i, thresh2, thresh2, thresh2, thresh2, self._hyperparameters["erodeSize"], frame_width, frame_height, self._trackingHeadingAllAnimals, self._trackingHeadTailAllAnimals, trackingProbabilityOfGoodDetection, 0, self._wellPositions[wellNumber]["lengthX"])

          if self._hyperparameters["trackTail"] == 1:
            for animalId in range(0, self._hyperparameters["nbAnimalsPerWell"]):
              self._tailTracking(animalId, i, thresh3, thresh3, thresh3, 0, self._trackingHeadTailAllAnimals, self._trackingHeadingAllAnimals, 0, 0, 0, thresh3, 0, wellNumber)

          # Debug functions
          self._debugTracking(i, self._trackingHeadTailAllAnimals, self._trackingHeadingAllAnimals, curFrame)

        else:

          print("No predictions for frame", i, "and well number", wellNumber)

      print("done for frame", i)
      i = i + 1

    return [self._trackingHeadTailAllAnimals, self._trackingHeadingAllAnimals, 0, 0, 0]

  def runTracking(self, wellNumber):
    if self._hyperparameters["trackingDL"]:
      import torch
      return self._trackingDL(wellNumber, torch.device('cuda') if torch.cuda.is_available() else torch.device('cpu'))

    if self._hyperparameters["fishTailTrackingDifficultBackground"]:
      [self._trackingHeadTailAllAnimals, self._trackingHeadingAllAnimals, self._trackingEyesAllAnimals] = self._fishTailTrackingDifficultBackground(wellNumber)
      return [self._trackingHeadTailAllAnimals, self._trackingHeadingAllAnimals, self._trackingEyesAllAnimals, 0, 0]

    if (self._hyperparameters["freqAlgoPosFollow"] != 0):
      print("lastFrame:",self._lastFrame)

    thetaDiffAccept = 1.2 # 0.5 for the head embedded maybe
    maxDepth = 0

    cap = zzVideoReading.VideoCapture(self._videoPath)
    if (cap.isOpened()== False):
      print("Error opening video stream or file")

    heading = -1
    if self._hyperparameters["headEmbeded"]:
      heading = 0.7

    threshForBlackFrames = self._getThresForBlackFrame() # For headEmbededTeresaNicolson
    cap.set(1, self._firstFrame)

    # Using the first frame of the video to calculate parameters that will be used afterwards for the tracking
    if (self._hyperparameters["headEmbeded"] == 1):
      # Getting images

      if self._hyperparameters["headEmbededRemoveBack"] == 0 and self._hyperparameters["headEmbededAutoSet_BackgroundExtractionOption"] == 0:
        [frame, thresh1] = self.headEmbededFrame(self._firstFrame, wellNumber)
      else:
        self._hyperparameters["headEmbededRemoveBack"] = 1
        self._hyperparameters["minPixelDiffForBackExtract"] = self._hyperparameters["headEmbededAutoSet_BackgroundExtractionOption"]
        [frame, thresh1] = self.headEmbededFrameBackExtract(self._firstFrame, wellNumber)

      # Setting self._hyperparameters in order to add line on image
      if self._hyperparameters["addBlackLineToImg_Width"]:
        self._addBlackLineToImgSetParameters(frame)

      # (x, y) coordinates for both eyes for head embedded fish eye tracking
      if self._hyperparameters["eyeTracking"] and self._hyperparameters["headEmbeded"] == 1:
        forEye = self.getAccentuateFrameForManualPointSelect(frame)
        if True:
          leftEyeCoordinate = list(self._getCoordinates(np.uint8(forEye * 255), "Click on the center of the left eye", True, True))
          rightEyeCoordinate = list(self._getCoordinates(np.uint8(forEye * 255), "Click on the center of the right eye", True, True))
        else:
          leftEyeCoordinate  = [261, 201] # [267, 198] # [210, 105]
          rightEyeCoordinate = [285, 157] # [290, 151] # [236, 72]
        print("leftEyeCoordinate:", leftEyeCoordinate)
        print("rightEyeCoordinate:", rightEyeCoordinate)

      # if self._hyperparameters["invertBlackWhiteOnImages"]:
        # frame   = 255 - frame

      gray = frame.copy()

      oppHeading = (heading + math.pi) % (2 * math.pi)

      # Getting headPositionFirstFrame and tailTipFirstFrame positions
      if os.path.exists(self._videoPath+'HP.csv'):
        self._headPositionFirstFrame = self._getHeadPositionByFileSaved()
      else:
        if self._hyperparameters["findHeadPositionByUserInput"]:
          frameForManualPointSelection = self.getAccentuateFrameForManualPointSelect(frame)
          self._headPositionFirstFrame = self.findHeadPositionByUserInput(frameForManualPointSelection, self._firstFrame, wellNumber)
        else:
          [frame, gray, thresh1, blur, thresh2, frame2, initialCurFrame, back, xHead, yHead] = self._getImages(cap, wellNumber)
          cap.set(1, self._firstFrame)
          lastFirstTheta = self._headTrackingHeadingCalculation(self._firstFrame, blur, thresh1, thresh2, gray, self._hyperparameters["erodeSize"], int(cap.get(3)), int(cap.get(4)), self._trackingHeadingAllAnimals, self._trackingHeadTailAllAnimals, self._trackingProbabilityOfGoodDetection, self._headPositionFirstFrame, self._wellPositions[wellNumber]["lengthX"])
      if os.path.exists(self._videoPath+'.csv'):
        self._tailTipFirstFrame  = self._getTailTipByFileSaved()
      else:
        frameForManualPointSelection = self.getAccentuateFrameForManualPointSelect(frame)
        self._tailTipFirstFrame  = self.findTailTipByUserInput(frameForManualPointSelection, self._firstFrame, wellNumber)
      if self._hyperparameters["automaticallySetSomeOfTheHeadEmbededHyperparameters"] == 1:
        self._adjustHeadEmbededHyperparameters(frame)
      # Getting max depth
      if self._hyperparameters["headEmbededTeresaNicolson"] == 1:
        if len(self._headPositionFirstFrame) == 0:
          self._headPositionFirstFrame = [self._trackingHeadTailAllAnimals[0][0][0][0], self._trackingHeadTailAllAnimals[0][0][0][1]]
        maxDepth = self._headEmbededTailTrackFindMaxDepthTeresaNicolson(frame)
      else:
        if self._hyperparameters["centerOfMassTailTracking"] == 0:
          maxDepth = self._headEmbededTailTrackFindMaxDepth(frame)
        else:
          maxDepth = self._centerOfMassTailTrackFindMaxDepth(frame)

    widgets = None
    # Performing the tracking on each frame
    i = self._firstFrame
    if int(self._hyperparameters["onlyDoTheTrackingForThisNumberOfFrames"]) != 0:
      self._lastFrame = min(self._lastFrame, self._firstFrame + int(self._hyperparameters["onlyDoTheTrackingForThisNumberOfFrames"]))
    while (i < self._lastFrame+1):

      if (self._hyperparameters["freqAlgoPosFollow"] != 0) and (i % self._hyperparameters["freqAlgoPosFollow"] == 0):
        print("Tracking: wellNumber:",wellNumber," ; frame:",i)
        if self._hyperparameters["popUpAlgoFollow"]:
          from zebrazoom.code.popUpAlgoFollow import prepend
          prepend("Tracking: wellNumber:" + str(wellNumber) + " ; frame:" + str(i))
      if self._hyperparameters["debugTracking"]:
        print("frame:",i)
      # Get images for frame i
      [frame, gray, thresh1, blur, thresh2, frame2, initialCurFrame, back, xHead, yHead] = self._getImages(cap, i, wellNumber, 0, self._trackingHeadTailAllAnimals)
      # Head tracking and heading calculation
      lastFirstTheta = self._headTrackingHeadingCalculation(i, blur, thresh1, thresh2, gray, self._hyperparameters["erodeSize"], int(cap.get(3)), int(cap.get(4)), self._trackingHeadingAllAnimals, self._trackingHeadTailAllAnimals, self._trackingProbabilityOfGoodDetection, self._headPositionFirstFrame, self._wellPositions[wellNumber]["lengthX"], xHead, yHead)

      # Tail tracking for frame i
      if self._hyperparameters["trackTail"] == 1 :
        for animalId in range(0, self._hyperparameters["nbAnimalsPerWell"]):
          self._tailTracking(animalId, i, frame, thresh1, threshForBlackFrames, thetaDiffAccept, self._trackingHeadTailAllAnimals, self._trackingHeadingAllAnimals, lastFirstTheta, maxDepth, self._tailTipFirstFrame, initialCurFrame, back, wellNumber, xHead, yHead)

      if self._hyperparameters["updateBackgroundAtInterval"]:
        self._updateBackgroundAtInterval(i, wellNumber, initialCurFrame, self._trackingHeadTailAllAnimals, frame)

      # Eye tracking for frame i
      if self._hyperparameters["eyeTracking"]:
        if self._hyperparameters["headEmbeded"] == 1:
          if self._hyperparameters["adjustHeadEmbeddedEyeTracking"]: # TODO: aaaaa
            i, widgets = self._eyeTrackingHeadEmbedded(animalId, i, frame, thresh1, self._trackingHeadingAllAnimals, self._trackingHeadTailAllAnimals, self._trackingEyesAllAnimals, leftEyeCoordinate, rightEyeCoordinate, widgets=widgets)
            if not self._hyperparameters["eyeFilterKernelSize"] % 2:
              self._hyperparameters["eyeFilterKernelSize"] -= 1
            continue
          else:
            self._eyeTrackingHeadEmbedded(animalId, i, frame, thresh1, self._trackingHeadingAllAnimals, self._trackingHeadTailAllAnimals, self._trackingEyesAllAnimals, leftEyeCoordinate, rightEyeCoordinate)
        else:
          self._eyeTracking(animalId, i, frame, thresh1, self._trackingHeadingAllAnimals, self._trackingHeadTailAllAnimals, self._trackingEyesAllAnimals)

      # Debug functions
      if self._hyperparameters["nbAnimalsPerWell"] > 1 or self._hyperparameters["forceBlobMethodForHeadTracking"] or self._hyperparameters["headEmbeded"] == 1 or self._hyperparameters["fixedHeadPositionX"] != -1:
        self._debugTracking(i, self._trackingHeadTailAllAnimals, self._trackingHeadingAllAnimals, frame)
      else:
        self._debugTracking(i, self._trackingHeadTailAllAnimals, self._trackingHeadingAllAnimals, frame)
      # DetectMovementWithRawVideoInsideTracking
      if self._hyperparameters["detectMovementWithRawVideoInsideTracking"]:
        self._detectMovementWithRawVideoInsideTracking(xHead, yHead, initialCurFrame)

      if self._hyperparameters["trackOnlyOnROI_halfDiameter"]:
        if not(xHead == 0 and yHead == 0):
          for animalId in range(0, self._hyperparameters["nbAnimalsPerWell"]):
            for j in range(0, len(self._trackingHeadTailAllAnimals[animalId][i-self._firstFrame])): # Head Position should already shifted, only shifting tail positions now
              self._trackingHeadTailAllAnimals[animalId][i-self._firstFrame][j][0] = self._trackingHeadTailAllAnimals[animalId][i-self._firstFrame][j][0] + xHead
              self._trackingHeadTailAllAnimals[animalId][i-self._firstFrame][j][1] = self._trackingHeadTailAllAnimals[animalId][i-self._firstFrame][j][1] + yHead

      paramsAdjusted = self._adjustParameters(i, initialCurFrame, frame, frame2, widgets)
      if paramsAdjusted is not None:
        i, widgets = paramsAdjusted
      else:
        i = i + 1

    if self._hyperparameters["postProcessMultipleTrajectories"]:
      self._postProcessMultipleTrajectories(self._trackingHeadTailAllAnimals, self._trackingProbabilityOfGoodDetection)

    self._savingBlackFrames()

    print("Tracking done for well", wellNumber)
    if self._hyperparameters["popUpAlgoFollow"]:
      from zebrazoom.code.popUpAlgoFollow import prepend
      prepend("Tracking done for well "+ str(wellNumber))

    if self._auDessusPerAnimalId is not None:
      return [self._trackingHeadTailAllAnimals, self._trackingHeadingAllAnimals, self._trackingEyesAllAnimals, self._headPositionFirstFrame, self._tailTipFirstFrame, self._auDessusPerAnimalId]
    else:
      return [self._trackingHeadTailAllAnimals, self._trackingHeadingAllAnimals, self._trackingEyesAllAnimals, self._headPositionFirstFrame, self._tailTipFirstFrame]

  def _getParametersForWell(self, wellNumber):
    '''Does the tracking and then the extraction of parameters'''
    if self.useGUI:
      from PyQt5.QtWidgets import QApplication

      if QApplication.instance() is None:
        from zebrazoom.GUIAllPy import PlainApplication
        app = PlainApplication(sys.argv)
    if self._hyperparameters["debugPauseBetweenTrackAndParamExtract"] == "noDebug":
      # Normal execution process
      trackingData = self.runTracking(wellNumber)
      parameters = extractParameters(trackingData, wellNumber, self._hyperparameters, self._videoPath, self._wellPositions, self._background)
      return [wellNumber,parameters,[]]
    elif self._hyperparameters["debugPauseBetweenTrackAndParamExtract"] == "justSaveTrackData":
      # Extracing tracking data, saving it, and that's it
      trackingData = self.runTracking(wellNumber)
      return [wellNumber,[],trackingData]
    elif self._hyperparameters["debugPauseBetweenTrackAndParamExtract"] == "saveTrackDataAndExtractParam":
      # Extracing tracking data, saving it, and continuing normal execution
      trackingData = self.runTracking(wellNumber)
      parameters = extractParameters(trackingData, wellNumber, self._hyperparameters, self._videoPath, self._wellPositions, self._background)
      return [wellNumber,parameters,trackingData]
    else:
      assert self._hyperparameters["debugPauseBetweenTrackAndParamExtract"] == "justExtractParamFromPreviousTrackData"
      # Reloading previously tracked data and using it to extract parameters
      trackingData = self._previouslyAcquiredTrackingDataForDebug[wellNumber]
      parameters = extractParameters(trackingData, wellNumber, self._hyperparameters, self._videoPath, self._wellPositions, self._background)
      return [wellNumber,parameters,[]]

  def _storeParametersInQueue(self, queue, wellNumber):
    queue.put(self._getParametersForWell(wellNumber))

  def run(self):
    if self._hyperparameters["trackingDL"]:
      from torch.multiprocessing import Process
      import torch.multiprocessing as mp
    else:
      from multiprocessing import Process
      import multiprocessing as mp
    if globalVariables["mac"] or self._hyperparameters["trackingDL"]:
      mp.set_start_method('spawn', force=True)

    # Tracking and extraction of parameters
    if globalVariables["noMultiprocessing"] == 0 and not self._hyperparameters['headEmbeded']:
      if self._hyperparameters["onlyTrackThisOneWell"] == -1:
        # for all wells, in parallel
        queue = mp.Queue()
        processes = [Process(target=self._storeParametersInQueue, args=(queue, wellNumber), daemon=True)
                     for wellNumber in range(self._hyperparameters["nbWells"])]
        for p in processes:
          p.start()
        parametersPerWell = [queue.get() for p in processes]
        for p in processes:
          p.join()
      else:
        # for just one well
        parametersPerWell = [self._getParametersForWell(self._hyperparameters["onlyTrackThisOneWell"])]
    else:
      if self._hyperparameters["onlyTrackThisOneWell"] == -1:
        parametersPerWell = [self._getParametersForWell(wellNumber) for wellNumber in range(self._hyperparameters["nbWells"])]
      else:
        parametersPerWell = [self._getParametersForWell(self._hyperparameters["onlyTrackThisOneWell"])]
    # Sorting wells after the end of the parallelized calls end
    return parametersPerWell

register_tracking_method('tracking', Tracking)
