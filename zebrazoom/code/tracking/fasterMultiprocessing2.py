import cv2
import numpy as np
import math

import zebrazoom.videoFormatConversion.zzVideoReading as zzVideoReading
from zebrazoom.code.extractParameters import extractParameters
from zebrazoom.code.preprocessImage import preprocessImage

from ._base import register_tracking_method
from ._fasterMultiprocessingBase import BaseFasterMultiprocessing
from ._tailExtremityTracking import TailTrackingExtremityDetectMixin

from zebrazoom.code.deepLearningFunctions.labellingFunctions import drawWhitePointsOnInitialImages, saveImagesAndData


class FasterMultiprocessing2(BaseFasterMultiprocessing, TailTrackingExtremityDetectMixin):
  def __init__(self, videoPath, wellPositions, hyperparameters):
    super().__init__(videoPath, wellPositions, hyperparameters)

    # if self._hyperparameters["eyeTracking"]:
      # self._trackingEyesAllAnimalsList = []
    # else:
      # self._trackingEyesAllAnimals = 0
    # for wellNumber in range(0, self._hyperparameters["nbWells"]):
      # if self._hyperparameters["eyeTracking"]:
        # self._trackingHeadingAllAnimalsList.append(np.zeros((self._hyperparameters["nbAnimalsPerWell"], self._lastFrame-self._firstFrame+1, 8)))
      # self._trackingProbabilityOfGoodDetectionList.append(np.zeros((self._hyperparameters["nbAnimalsPerWell"], self._lastFrame-self._firstFrame+1)))

    # if not(self._hyperparameters["nbAnimalsPerWell"] > 1) and not(self._hyperparameters["headEmbeded"]) and (self._hyperparameters["findHeadPositionByUserInput"] == 0) and (self._hyperparameters["takeTheHeadClosestToTheCenter"] == 0):
      # self._trackingProbabilityOfGoodDetectionList = []
    # else:
      # self._trackingProbabilityOfGoodDetectionList = 0
    # self._trackingProbabilityOfGoodDetectionList = []

  def _adjustParameters(self, i, back, frame, initialCurFrame, widgets):
    return None

  def _findTheTwoSides(self, headPosition, bodyContour, curFrame, bestAngle):
    # Finding the 'mouth' of the fish
    unitVector = np.array([math.cos(bestAngle), math.sin(bestAngle)])
    factor     = 1
    headPos    = np.array(headPosition)
    testBorder = headPos + factor * unitVector
    testBorder = testBorder.astype(int)
    while (cv2.pointPolygonTest(bodyContour, (float(testBorder[0]), float(testBorder[1])), True) > 0) and (factor < 100) and (testBorder[0] >= 0) and (testBorder[1] >= 0) and (testBorder[0] < len(curFrame[0])) and (testBorder[1] < len(curFrame)):
      factor = factor + 1
      testBorder = headPos + factor * unitVector

    # Finding the indexes of the two "border points" along the contour (these are the two points that are the closest from the 'mouth' of fish)
    xOtherBorder = testBorder[0]
    yOtherBorder = testBorder[1]
    minDist1 = 1000000000000
    minDist2 = 1000000000000
    indMin1  = 0
    indMin2  = 0
    for i in range(0, len(bodyContour)):
      Pt   = bodyContour[i][0]
      dist = math.sqrt((Pt[0] - xOtherBorder)**2 + (Pt[1] - yOtherBorder)**2)
      if (dist < minDist1):
        minDist2 = minDist1
        indMin2  = indMin1
        minDist1 = dist
        indMin1  = i
      else:
        if (dist < minDist2):
          minDist2 = dist
          indMin2  = i

    return indMin1, indMin2

  def _computeHeading(self, initialContour, lenX, lenY, headPosition):
    xmin = lenX
    ymin = lenY
    xmax = 0
    ymax = 0
    for pt in initialContour:
      if pt[0][0] < xmin:
        xmin = pt[0][0]
      if pt[0][1] < ymin:
        ymin = pt[0][1]
      if pt[0][0] > xmax:
        xmax = pt[0][0]
      if pt[0][1] > ymax:
        ymax = pt[0][1]

    for pt in initialContour:
      pt[0][0] = pt[0][0] - xmin
      pt[0][1] = pt[0][1] - ymin

    headPosition = [headPosition[0] - xmin, headPosition[1] - ymin]

    image = np.zeros((ymax - ymin, xmax - xmin))
    image[:, :] = 255
    image = image.astype(np.uint8)
    kernel  = np.ones((3, 3), np.uint8)
    if type(initialContour) != int:
      cv2.fillPoly(image, pts =[initialContour], color=(0))
      image[:,0] = 255
      image[0,:] = 255
      image[:, len(image[0])-1] = 255
      image[len(image)-1, :]    = 255

    originalShape = 255 - image

    # Heading calculation: first approximation
    minWhitePixel = 1000000000
    bestAngle     = 0
    nTries        = 50
    for i in range(0, nTries):
      angleOption = i * ((2 * math.pi) / nTries)
      startPoint = (int(headPosition[0]), int(headPosition[1]))
      endPoint   = (int(headPosition[0] + 100000 * math.cos(angleOption)), int(headPosition[1] + 100000 * math.sin(angleOption)))
      testImage  = originalShape.copy()
      testImage  = cv2.line(testImage, startPoint, endPoint, (0), 1)
      nbWhitePixels = cv2.countNonZero(testImage)

      if nbWhitePixels < minWhitePixel:
        minWhitePixel = nbWhitePixels
        bestAngle     = angleOption
    bestAngleAfterFirstStep = bestAngle

    # Heading calculation: second (and refined) approximation
    # Searching for the optimal value of iterationsForErodeImageForHeadingCalculation
    countTries = 0
    nbIterations2nbWhitePixels = {}
    if "iterationsForErodeImageForHeadingCalculation" in self._hyperparameters:
      iterationsForErodeImageForHeadingCalculation = self._hyperparameters["iterationsForErodeImageForHeadingCalculation"]
    else:
      iterationsForErodeImageForHeadingCalculation = 4
    kernel = np.ones((3, 3), np.uint8)
    nbWhitePixelsMax = 0.3 * cv2.contourArea(initialContour)
    while (iterationsForErodeImageForHeadingCalculation > 0) and (countTries < 50) and not(iterationsForErodeImageForHeadingCalculation in nbIterations2nbWhitePixels):
      testImage2 = cv2.erode(testImage, kernel, iterations = iterationsForErodeImageForHeadingCalculation)
      nbWhitePixels = cv2.countNonZero(testImage2)
      nbIterations2nbWhitePixels[iterationsForErodeImageForHeadingCalculation] = nbWhitePixels
      if nbWhitePixels < nbWhitePixelsMax:
        iterationsForErodeImageForHeadingCalculation = iterationsForErodeImageForHeadingCalculation - 1
      if nbWhitePixels >= nbWhitePixelsMax:
        iterationsForErodeImageForHeadingCalculation = iterationsForErodeImageForHeadingCalculation + 1
      countTries = countTries + 1
    best_iterations = 0
    minDist = 10000000000000
    for iterations in nbIterations2nbWhitePixels:
      nbWhitePixels = nbIterations2nbWhitePixels[iterations]
      dist = abs(nbWhitePixels - nbWhitePixelsMax)
      if dist < minDist:
        minDist = dist
        best_iterations = iterations
    iterationsForErodeImageForHeadingCalculation = best_iterations
    self._hyperparameters["iterationsForErodeImageForHeadingCalculation"] = iterationsForErodeImageForHeadingCalculation

    testImage2 = cv2.erode(originalShape.copy(), kernel, iterations = iterationsForErodeImageForHeadingCalculation)

    maxDist = -1
    for i in range(0, nTries):
      angleOption = bestAngleAfterFirstStep - (math.pi / 5) + i * ((2 * (math.pi / 5)) / nTries)

      startPoint = (int(headPosition[0]), int(headPosition[1]))
      endPoint   = (int(headPosition[0] + 100000 * math.cos(angleOption)), int(headPosition[1] + 100000 * math.sin(angleOption)))

      testImage = testImage2.copy()

      testImage  = cv2.line(testImage, startPoint, endPoint, (0), 1)
      nbWhitePixels = cv2.countNonZero(testImage)
      if nbWhitePixels < minWhitePixel:
        minWhitePixel = nbWhitePixels
        bestAngle     = angleOption

    theta = bestAngle

    if self._hyperparameters["debugHeadingCalculation"]:
      img2 = image.copy()
      img2 = cv2.cvtColor(img2, cv2.COLOR_GRAY2RGB)
      cv2.line(img2, (int(len(img2[0])/2), int(len(img2)/2)), (int(len(img2[0])/2 + 20 * math.cos(theta)), int(len(img2)/2 + 20 * math.sin(theta))), (255,0,255), 1)
      self._debugFrame(img2, title='imgForHeadingCalculation')

    return theta + math.pi

# def computeHeading(self, thresh1, x, y):

  # videoWidth  = self._hyperparameters["videoWidth"]
  # videoHeight = self._hyperparameters["videoHeight"]
  # headSize = self._hyperparameters["headSize"]
  # ymin  = y - headSize - 10 if y - headSize >= 0 else 0
  # ymax  = y + headSize + 10 if y + headSize < len(thresh1) else len(thresh1) - 1
  # xmin  = x - headSize - 10 if x - headSize >= 0 else 0
  # xmax  = x + headSize + 10 if x + headSize < len(thresh1[0]) else len(thresh1[0]) - 1
  # img = thresh1[int(ymin):int(ymax), int(xmin):int(xmax)]

  # img[0,:] = 255
  # img[len(img)-1,:] = 255
  # img[:,0] = 255
  # img[:,len(img[0])-1] = 255

  # y2, x2 = np.nonzero(img)
  # x2 = x2 - np.mean(x2)
  # y2 = y2 - np.mean(y2)
  # coords = np.vstack([x2, y2])
  # cov = np.cov(coords)
  # evals, evecs = np.linalg.eig(cov)
  # sort_indices = np.argsort(evals)[::-1]
  # x_v1, y_v1 = evecs[:, sort_indices[0]]  # Eigenvector with largest eigenvalue
  # x_v2, y_v2 = evecs[:, sort_indices[1]]
  # scale = 20
  # theta = self._calculateAngle(0, 0, x_v1, y_v1)
  # theta = (theta - math.pi/2) % (2 * math.pi)

  # if False:
    # width  = len(img[0])
    # height = len(img)
    # option1X = x + width * math.cos(theta)
    # option1Y = y + height * math.sin(theta)
    # option2X = x - width * math.cos(theta)
    # option2Y = y - height * math.sin(theta)
    # if math.sqrt((option1X - width)**2 + (option1Y - height)**2) < math.sqrt((option2X - width)**2 + (option2Y - height)**2):
      # theta += theta + math.pi

  # if self._hyperparameters["debugHeadingCalculation"]:
    # img2 = img.copy()
    # img2 = cv2.cvtColor(img2, cv2.COLOR_GRAY2BGR)
    # cv2.line(img2, (int(len(img2[0])/2), int(len(img2)/2)), (int(len(img[0])/2 + 20 * math.cos(theta)), int(len(img)/2 + 20 * math.sin(theta))), (255,0,0), 1)
    # self._debugFrame(img2, title='imgForHeadingCalculation')

  # return theta

  def _findOptimalIdCorrespondance(self, wellNumber, i):
    from scipy.optimize import linear_sum_assignment

    if i > self._firstFrame:

      costMatrix = np.zeros((len(self._trackingHeadTailAllAnimalsList[wellNumber]), len(self._trackingHeadTailAllAnimalsList[wellNumber])))

      for animalIdPrev in range(0, len(self._trackingHeadTailAllAnimalsList[wellNumber])):
        for animalIdCur in range(0, len(self._trackingHeadTailAllAnimalsList[wellNumber])):
          coordPrevX = self._trackingHeadTailAllAnimalsList[wellNumber][animalIdPrev, i-self._firstFrame-1][0][0]
          coordPrevY = self._trackingHeadTailAllAnimalsList[wellNumber][animalIdPrev, i-self._firstFrame-1][0][1]
          coordCurX  = self._trackingHeadTailAllAnimalsList[wellNumber][animalIdCur,  i-self._firstFrame][0][0]
          coordCurY  = self._trackingHeadTailAllAnimalsList[wellNumber][animalIdCur,  i-self._firstFrame][0][1]
          # TO DO: add some very high cost for (0, 0) coordinates
          costMatrix[animalIdPrev, animalIdCur] = math.sqrt((coordCurX - coordPrevX)**2 + (coordCurY - coordPrevY)**2)

      row_ind, col_ind = linear_sum_assignment(costMatrix)

      return col_ind
    else:
      return np.array([k for k in range(0, len(self._trackingHeadTailAllAnimalsList[wellNumber]))])

  def _switchIdentities(self, correspondance, wellNumber, i):
    trackingHeadTailAllAnimalsListWellNumberOriginal = self._trackingHeadTailAllAnimalsList[wellNumber][:, i-self._firstFrame].copy()
    trackingHeadingAllAnimalsListWellNumberOriginal  = self._trackingHeadingAllAnimalsList[wellNumber][:, i-self._firstFrame].copy()

    for previousId, newId in enumerate(correspondance):
      self._trackingHeadTailAllAnimalsList[wellNumber][previousId, i-self._firstFrame] = trackingHeadTailAllAnimalsListWellNumberOriginal[newId]

    for previousId, newId in enumerate(correspondance):
      self._trackingHeadingAllAnimalsList[wellNumber][previousId, i-self._firstFrame] = trackingHeadingAllAnimalsListWellNumberOriginal[newId]

  def _findCenterByIterativelyDilating(self, initialContour, lenX, lenY):
    x = 0
    y = 0

    xmin = lenX
    ymin = lenY
    xmax = 0
    ymax = 0
    for pt in initialContour:
      if pt[0][0] < xmin:
        xmin = pt[0][0]
      if pt[0][1] < ymin:
        ymin = pt[0][1]
      if pt[0][0] > xmax:
        xmax = pt[0][0]
      if pt[0][1] > ymax:
        ymax = pt[0][1]

    for pt in initialContour:
      pt[0][0] = pt[0][0] - xmin
      pt[0][1] = pt[0][1] - ymin

    image = np.zeros((ymax - ymin, xmax - xmin))
    image[:, :] = 255
    image = image.astype(np.uint8)
    kernel  = np.ones((3, 3), np.uint8)
    if type(initialContour) != int:
      cv2.fillPoly(image, pts =[initialContour], color=(0))
      image[:,0] = 255
      image[0,:] = 255
      image[:, len(image[0])-1] = 255
      image[len(image)-1, :]    = 255
      nbBlackPixels = 1
      dilateIter = 0
      while nbBlackPixels > 0:
        dilateIter   = dilateIter + 1
        dilatedImage = cv2.dilate(image, kernel, iterations=dilateIter)
        nbBlackPixels = cv2.countNonZero(255-dilatedImage)
      dilateIter   = dilateIter - 1
      dilatedImage = cv2.dilate(image, kernel, iterations=dilateIter)
      dilatedImage[:,0] = 255
      dilatedImage[0,:] = 255
      dilatedImage[:, len(dilatedImage[0])-1] = 255
      dilatedImage[len(dilatedImage)-1, :]    = 255
      contours, hierarchy = cv2.findContours(dilatedImage, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
      maxContour = 0
      maxContourArea = 0
      for contour in contours:
        contourArea = cv2.contourArea(contour)
        if contourArea < int((xmax - xmin) * (ymax - ymin) * 0.8):
          if contourArea > maxContourArea:
            maxContourArea = contourArea
            maxContour     = contour
      M = cv2.moments(maxContour)
      if M['m00']:
        x = int(M['m10']/M['m00'])
        y = int(M['m01']/M['m00'])

    return [x + xmin, y + ymin]

  def _formatOutput(self):
    # if self._hyperparameters["postProcessMultipleTrajectories"]:
      # self._postProcessMultipleTrajectories(self._trackingHeadTailAllAnimalsList[wellNumber], self._trackingProbabilityOfGoodDetectionList[wellNumber])
    if self._auDessusPerAnimalIdList == None:
      return {wellNumber: extractParameters([self._trackingHeadTailAllAnimalsList[wellNumber], self._trackingHeadingAllAnimalsList[wellNumber], [], 0, 0, 0], wellNumber, self._hyperparameters, self._videoPath, self._wellPositions, self._background)
              for wellNumber in range(self._firstWell, self._lastWell + 1)}
    else:
      return {wellNumber: extractParameters([self._trackingHeadTailAllAnimalsList[wellNumber], self._trackingHeadingAllAnimalsList[wellNumber], [], 0, 0, self._auDessusPerAnimalIdList[wellNumber]], wellNumber, self._hyperparameters, self._videoPath, self._wellPositions, self._background)
              for wellNumber in range(self._firstWell, self._lastWell + 1)}

  def run(self):
    self._background = self.getBackground()

    cap = zzVideoReading.VideoCapture(self._videoPath)
    if (cap.isOpened()== False):
      print("Error opening video stream or file")
    
    lastFrameRememberedForBackgroundExtract = 0
    
    # if self._hyperparameters["backgroundSubtractorKNN"]:
      # fgbg = cv2.createBackgroundSubtractorKNN()
      # for i in range(0, min(self._lastFrame - 1, 500), int(min(self._lastFrame - 1, 500) / 10)):
        # cap.set(1, min(self._lastFrame - 1, 500) - i)
        # ret, frame = cap.read()
        # fgmask = fgbg.apply(frame)
      # cap.release()
      # cap = zzVideoReading.VideoCapture(videoPath)

    i = self._firstFrame

    if self._firstFrame:
      cap.set(1, self._firstFrame)

    previousFrames = None
    widgets = None
    while (i < self._lastFrame + 1):

      if (self._hyperparameters["freqAlgoPosFollow"] != 0) and (i % self._hyperparameters["freqAlgoPosFollow"] == 0):
        print("Tracking: frame:",i)
        if self._hyperparameters["popUpAlgoFollow"]:
          from zebrazoom.code.popUpAlgoFollow import prepend

          prepend("Tracking: frame:" + str(i))

      if self._hyperparameters["debugTracking"]:
        print("frame:",i)

      ret, frame = cap.read()

      if ret:
        
        if self._hyperparameters["invertBlackWhiteOnImages"]:
          frame = 255 - frame
        
        if self._hyperparameters["imagePreProcessMethod"]:
          frame = preprocessImage(frame, self._hyperparameters)
        
        # if self._hyperparameters["backgroundSubtractorKNN"]:
          # frame = fgbg.apply(frame)
          # frame = 255 - frame

        for wellNumber in range(self._firstWell, self._lastWell + 1):

          minPixelDiffForBackExtract = self._hyperparameters["minPixelDiffForBackExtract"]
          xtop = self._wellPositions[wellNumber]['topLeftX']
          ytop = self._wellPositions[wellNumber]['topLeftY']
          lenX = self._wellPositions[wellNumber]['lengthX']
          lenY = self._wellPositions[wellNumber]['lengthY']
          # if self._hyperparameters["backgroundSubtractorKNN"]:
            # grey = frame
          # else:
          grey = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

          curFrame = grey[ytop:ytop+lenY, xtop:xtop+lenX].copy()
          initialCurFrame = curFrame.copy()
          # if not(self._hyperparameters["backgroundSubtractorKNN"]):
          back = self._background[ytop:ytop+lenY, xtop:xtop+lenX]
          putToWhite = ( curFrame.astype('int32') >= (back.astype('int32') - minPixelDiffForBackExtract) )
          curFrame[putToWhite] = 255
          # else:
            # self._hyperparameters["paramGaussianBlur"] = int(math.sqrt(cv2.countNonZero(255 - curFrame) / self._hyperparameters["nbAnimalsPerWell"]) / 2) * 2 + 1
          # if self._hyperparameters["paramGaussianBlur"]:
            # blur = cv2.GaussianBlur(curFrame, (self._hyperparameters["paramGaussianBlur"], self._hyperparameters["paramGaussianBlur"]),0)
          # else:
            # blur = curFrame
          headPositionFirstFrame = 0

          ret, thresh1 = cv2.threshold(curFrame.copy(), 254, 255, cv2.THRESH_BINARY)
          
          thresh1[:,0] = 255
          thresh1[0,:] = 255
          thresh1[:, len(thresh1[0])-1] = 255
          thresh1[len(thresh1)-1, :]    = 255
          
          contours, hierarchy = cv2.findContours(thresh1,cv2.RETR_TREE,cv2.CHAIN_APPROX_SIMPLE)
          areas = np.array([cv2.contourArea(contour) for contour in contours])

          maxIndexes = []
          for numFish in range(0, self._hyperparameters["nbAnimalsPerWell"]):
            maxArea = -1
            maxInd  = -1
            for idx, area in enumerate(areas):
              if area > maxArea and area > 0.7 * self._hyperparameters["minAreaBody"] and area < 1.3 * self._hyperparameters["maxAreaBody"]:
                maxArea = area
                maxInd  = idx
            areas[maxInd] = -1
            if maxInd != -1:
              maxIndexes.append(maxInd)

          for animal_Id, idx in enumerate(maxIndexes):
            bodyContour = contours[idx]
            M = cv2.moments(bodyContour)
            if M['m00']:
              # x = int(M['m10']/M['m00'])
              # y = int(M['m01']/M['m00'])
              # headPosition = [x, y]
              headPosition = self._findCenterByIterativelyDilating(bodyContour.copy(), len(curFrame[0]), len(curFrame))

              self._trackingHeadTailAllAnimalsList[wellNumber][animal_Id, i-self._firstFrame][0][0] = headPosition[0]
              self._trackingHeadTailAllAnimalsList[wellNumber][animal_Id, i-self._firstFrame][0][1] = headPosition[1]

              heading = self._computeHeading(bodyContour.copy(), len(curFrame[0]), len(curFrame), headPosition)

              self._trackingHeadingAllAnimalsList[wellNumber][animal_Id, i-self._firstFrame] = heading

              if self._hyperparameters["trackTail"] == 1 :

                res = self._findTheTwoSides(headPosition, bodyContour, curFrame, heading)

                # Finding tail extremity
                rotatedContour = bodyContour.copy()
                rotatedContour = self._rotate(rotatedContour,int(headPosition[0]),int(headPosition[1]),heading)
                debugAdv = False

                [MostCurvyIndex, distance2] = self._findTailExtremete(rotatedContour, bodyContour, headPosition[0], int(res[0]), int(res[1]), debugAdv, curFrame, self._hyperparameters["tailExtremityMaxJugeDecreaseCoeff"])

                # Getting Midline
                if self._hyperparameters["detectMouthInsteadOfHeadTwoSides"] == 0:
                  tail = self._getMidline(int(res[0]), int(res[1]), int(MostCurvyIndex), bodyContour, curFrame, self._nbTailPoints-1, distance2, debugAdv)
                else:
                  tail = self._getMidline(int(res[0]), int(res[1]), int(MostCurvyIndex), bodyContour, curFrame, self._nbTailPoints, distance2, debugAdv)
                  tail = np.array([tail[0][1:len(tail[0])]])
                tail = np.insert(tail, 0, headPosition, axis=1)
                self._trackingHeadTailAllAnimalsList[wellNumber][animal_Id, i-self._firstFrame] = tail
                
                if self._hyperparameters["saveBodyMask"]:
                  saveImagesAndData(self._hyperparameters, bodyContour, initialCurFrame, wellNumber, i)

          # Eye tracking for frame i
          # if self._hyperparameters["eyeTracking"]:
            # self._eyeTracking(animalId, i, frame, thresh1, self._trackingHeadingAllAnimalsList[wellNumber], self._trackingHeadTailAllAnimalsList[wellNumber], self._trackingHeadingAllAnimalsList[wellNumber])

          correspondance = self._findOptimalIdCorrespondance(wellNumber,  i)

          self._switchIdentities(correspondance, wellNumber, i)

          self._debugTracking(i, self._trackingHeadTailAllAnimalsList[wellNumber], self._trackingHeadingAllAnimalsList[wellNumber], curFrame)

          if self._hyperparameters["updateBackgroundAtInterval"]:
            self._updateBackgroundAtInterval(i, wellNumber, initialCurFrame, self._trackingHeadTailAllAnimalsList[wellNumber], initialCurFrame)
          
          if ("updateBackgroundAtIntervalRememberLastFrame" in self._hyperparameters) and (self._hyperparameters["updateBackgroundAtIntervalRememberLastFrame"]):
            lastFrameRememberedForBackgroundExtract = self._updateBackgroundAtIntervalRememberLastFrame(i, wellNumber, grey, lastFrameRememberedForBackgroundExtract)
            
          
          if self._hyperparameters["freqAlgoPosFollow"]:
            if i % self._hyperparameters["freqAlgoPosFollow"] == 0:
              print("Tracking at frame", i)

        if self._hyperparameters["detectMovementWithRawVideoInsideTracking"]:
          previousFrames = self._detectMovementWithRawVideoInsideTracking(i, grey, previousFrames)

      paramsAdjusted = self._adjustParameters(i, back, frame, initialCurFrame, widgets)
      if paramsAdjusted is not None:
        i, widgets = paramsAdjusted
        cap.set(1, i)
      else:
        i = i + 1

    cap.release()
    return self._formatOutput()


register_tracking_method('fasterMultiprocessing2', FasterMultiprocessing2)
