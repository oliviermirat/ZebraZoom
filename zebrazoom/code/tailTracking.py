import math
import os

import cv2
import numpy as np
from numpy import linspace
from scipy.interpolate import interp1d
from scipy.interpolate import splprep, splev
from scipy.optimize import curve_fit


class _TailTrackingBase:
  @staticmethod
  def _appendPoint(x, y, points):
    curPoint = np.zeros((2, 1))
    curPoint[0] = x
    curPoint[1] = y
    points = np.append(points, curPoint, axis=1)
    return points


class _HeadEmbeddedTailTrackingMixin(_TailTrackingBase):
  @staticmethod
  def __curvatureToXYPositions(successiveAngles, firstAngle, firstX, firstY, distance):
    l    = len(successiveAngles) + 1
    xPos = np.zeros(l)
    yPos = np.zeros(l)
    xPos[0] = firstX
    yPos[0] = firstY
    currentAngle = firstAngle
    for i in range(0, len(successiveAngles)):
      currentAngle = currentAngle + successiveAngles[i]
      xPos[i + 1]  = xPos[i] + distance * math.cos(currentAngle)
      yPos[i + 1]  = yPos[i] + distance * math.sin(currentAngle)
    return [xPos, yPos]

  @staticmethod
  def __sin3Combination(x, a1, a2, a3, b1, b2, b3, c1, c2, c3):
    return a1 * np.sin(a2 * (x - a3)) + b1 * np.sin(b2 * (x - b3)) + c1 * np.sin(c2 * (x - c3))

  @staticmethod
  def __sin2Combination(x, a1, a2, a3, b1, b2, b3):
    return a1 * np.sin(a2 * (x - a3)) + b1 * np.sin(b2 * (x - b3))

  @staticmethod
  def __smoothBasedOnCurvature(points, polynomialDegree):
    from zebrazoom.code.extractParameters import calculateTailAngle

    tailX = points[0]
    tailY = points[1]

    l = len(tailX)
    curvature = np.zeros(l-2)
    distanceC = np.zeros(l-2)
    av = 0
    firstAngle = self._calculateAngle(np.array([tailX[0], tailY[0]]), np.array([tailX[1], tailY[1]]))
    for ii in range(1, l-1):
      angleBef = self._calculateAngle(np.array([tailX[ii-1], tailY[ii-1]]), np.array([tailX[ii],   tailY[ii]]))
      angleAft = self._calculateAngle(np.array([tailX[ii],   tailY[ii]]),   np.array([tailX[ii+1], tailY[ii+1]]))
      curvature[ii-1] = calculateTailAngle(angleBef, angleAft)
      distanceC[ii-1] = math.sqrt((tailX[ii-1] - tailX[ii])**2 + (tailY[ii-1] - tailY[ii])**2)

    if False:
      x = np.linspace(0, len(curvature)-1, len(curvature))
      print("x:", x)
      print("curvature:", curvature)
      popt, pcov = curve_fit(self.__sin2Combination, x, curvature, maxfev=2000)
      curvaturePoly = self.__sin2Combination(np.linspace(0, len(curvature)-1, len(curvature)+1), *popt)
    else:
      x = np.linspace(0,len(curvature)-1,len(curvature))
      # curvature[0] = 0
      poly = np.polyfit(x, curvature, deg=polynomialDegree)
      curvaturePoly = np.polyval(poly, np.linspace(0, len(curvature)-1, len(curvature)+1))
      # curvaturePoly[0] = 0

    [xPosT, yPosT] = self.__curvatureToXYPositions(-curvaturePoly, firstAngle, tailX[0], tailY[0], np.mean(distanceC))

    if False:
      import matplotlib.pyplot as plt

      plt.plot(curvature)
      plt.plot(curvaturePoly)
      plt.show()

      ax = plt.gca()
      ax.invert_yaxis()
      plt.plot(tailX, tailY)
      plt.plot(xPosT, yPosT)
      plt.show()

    return [xPosT, yPosT]

  @staticmethod
  def __smoothTail(points, nbTailPoints, smoothingFactor):
    points3 = [np.array(points[0]), np.array(points[1])]

    y = points[0]
    x = linspace(0, 1, len(y))

    if len(x) > 3:
      interpolated_points = {}

      try:
        if smoothingFactor != -1:
          tck, u = splprep(points3, s=smoothingFactor)
        else:
          tck, u = splprep(points3)
        u2 = [i/(nbTailPoints-1) for i in range(0, nbTailPoints)]
        interpolated_points = splev(u2, tck)
        newX = interpolated_points[0]
        newY = interpolated_points[1]
      except:
        newX = points[0]
        newY = points[1]

    else:
      newX = points[0]
      newY = points[1]

    return [newX, newY]

  @staticmethod
  def __interpolateTail(points, nbTailPoints):

    y = points[0]
    x = linspace(0, 1, len(y))

    if len(x) > 3:

      points2 = []
      for i in range(0, len(points[0])-1):
        if not((points[0][i] == points[0][i+1]) and (points[1][i] == points[1][i+1])):
          points2.append([points[0][i], points[1][i]])

      i = len(points[0]) - 1
      if not((points[0][i-1] == points[0][i]) and (points[1][i-1] == points[1][i])):
        points2.append([points[0][i], points[1][i]])

      points = np.array(points2).T

      # Define some points:
      points = np.array([points[0], points[1]]).T  # a (nbre_points x nbre_dim) array

      # Linear length along the line:
      distance = np.cumsum( np.sqrt(np.sum( np.diff(points, axis=0)**2, axis=1 )) )
      distance = np.insert(distance, 0, 0)/distance[-1]

      # Interpolation for different methods:
      interpolation_method = 'quadratic'    # 'slinear', 'quadratic', 'cubic'
      alpha = np.linspace(0, 1, nbTailPoints)

      interpolated_points = {}

      interpolator =  interp1d(distance, points, kind=interpolation_method, axis=0)
      interpolated_points = interpolator(alpha)

      interpolated_points = interpolated_points.T

      newX = interpolated_points[0]
      newY = interpolated_points[1]

    else:

      newX = points[0]
      newY = points[1]

    return [newX, newY]

  def __findNextPoints(self, depth, x, y, frame, points, angle, maxDepth, steps, nbList, initialImage, debug, dontChooseThisPoint = [], maxRadiusForDontChoosePoint = 0):
    lenX = len(frame[0]) - 1
    lenY = len(frame) - 1

    thetaDiffAccept = 1

    if depth < self._hyperparameters["initialTailPortionMaxSegmentDiffAngleCutOffPos"] * maxDepth:
      thetaDiffAccept = self._hyperparameters["initialTailPortionMaxSegmentDiffAngleValue"]

    if depth > 0.85*maxDepth:
      thetaDiffAccept = 0.6

    if self._hyperparameters["headEmbededMaxAngleBetweenSubsequentSegments"]:
      thetaDiffAccept = self._hyperparameters["headEmbededMaxAngleBetweenSubsequentSegments"]

    pixTotMax = 1000000
    maxTheta  = angle

    l = [i*(math.pi/nbList) for i in range(0,2*nbList) if self._distBetweenThetas(i*(math.pi/nbList), angle) < thetaDiffAccept]

    # if debug:
      # print("debug")

    for step in steps:

      if (step < maxDepth - depth) or (step == steps[0]):

        for theta in l:

          xNew = self._assignValueIfBetweenRange(int(x + step * (math.cos(theta))), 0, lenX)
          yNew = self._assignValueIfBetweenRange(int(y + step * (math.sin(theta))), 0, lenY)
          pixTot = frame[yNew][xNew]

          # if debug:
            # print([theta,pixTot])

          # Keeps that theta angle as maximum if appropriate
          if (pixTot < pixTotMax):
            if (len(dontChooseThisPoint) == 0):
              pixTotMax = pixTot
              maxTheta = theta
              xTot = xNew
              yTot = yNew
            else:
              dist = 1000000000000000000
              for num in range(0, len(dontChooseThisPoint[0])):
                dist = min(dist, math.sqrt((xNew - dontChooseThisPoint[0, num])**2 + (yNew - dontChooseThisPoint[1, num])**2))
              if (not(dist <= maxRadiusForDontChoosePoint)):
                pixTotMax = pixTot
                maxTheta = theta
                xTot = xNew
                yTot = yNew

    w = 4
    ym = yTot - w
    yM = yTot + w
    xm = xTot - w
    xM = xTot + w
    if ym < 0:
      ym = 0
    if xm < 0:
      xm = 0
    if yM > len(initialImage):
      yM = len(initialImage)
    if xM > len(initialImage[0]):
      xM = len(initialImage[0])

    pixSur = np.min(frame[ym:yM, xm:xM]) #initialImage[ym:yM, xm:xM])
    # if debug:
      # print("depth:", depth, " ; maxDepth:", maxDepth, " ; pixSur:", pixSur)

    # if depth > 0.95*maxDepth:
      # pixTot = frame[y][x]
      # if (pixTot < pixTotMax):
        # pixTotMax = pixTot
        # maxTheta = theta
        # xTot = x
        # yTot = y
        # depth = maxDepth + 10

    # if debug:
      # print(["max:",maxTheta,pixTotMax])

    # Calculates distance between new and old point
    distSubsquentPoints = math.sqrt((xTot - x)**2 + (yTot - y)**2)

    pixSurMax = self._hyperparameters["headEmbededParamTailDescentPixThreshStop"]
    # pixSurMax = 220 #150 #245 #150
    if depth + distSubsquentPoints < maxDepth and ((pixSur < pixSurMax) or (depth < self._hyperparameters["authorizedRelativeLengthTailEnd"]*maxDepth)):
      points = self._appendPoint(xTot, yTot, points)
    else:
      vectX = xTot - x
      vectY = yTot - y
      xTot  = int(x + (maxDepth / (depth + distSubsquentPoints)) * vectX)
      yTot  = int(y + (maxDepth / (depth + distSubsquentPoints)) * vectY)
      points = self._appendPoint(xTot, yTot, points)
    if debug:
      cv2.circle(frame, (xTot, yTot), 3, (255,0,0),   -1)
      self._debugFrame(frame, title='HeadEmbeddedTailTracking')

    newTheta = self._calculateAngle(x,y,xTot,yTot)
    if distSubsquentPoints > 0 and depth + distSubsquentPoints < maxDepth and ((pixSur < pixSurMax) or (depth < self._hyperparameters["authorizedRelativeLengthTailEnd"]*maxDepth)):
      (points,nop) = self.__findNextPoints(depth+distSubsquentPoints,xTot,yTot,frame,points,newTheta,maxDepth,steps,nbList,initialImage,debug)

    if depth == 0:
      lenPoints = len(points[0]) - 1
      if points[0, lenPoints-1] == points[0, lenPoints] and points[1, lenPoints-1] == points[1, lenPoints]:
        points = points[:, :len(points[0])-1]

    return (points,newTheta)

  @staticmethod
  def __weirdTrackingPoints(points, headPosition, tailTip):

    newTrackedTipX = points[0, len(points[0]) - 1]
    newTrackedTipY = points[1, len(points[0]) - 1]

    distInitialHeadToNewTrackedTip = math.sqrt((headPosition[0] - newTrackedTipX)**2 + (headPosition[1] - newTrackedTipY)**2)
    distInitialTipToNewTrackTip    = math.sqrt((tailTip[0] - newTrackedTipX)**2 + (tailTip[1] - newTrackedTipY)**2)

    initialTailLength = math.sqrt((headPosition[0] - tailTip[0])**2 + (headPosition[1] - tailTip[1])**2)

    if (initialTailLength * 0.7 < distInitialHeadToNewTrackedTip) and (distInitialHeadToNewTrackedTip <initialTailLength * 1.3 ) and (distInitialTipToNewTrackTip < initialTailLength):
      return False
    else:
      return True

  def __retrackIfWeirdInitialTracking(self, points, headPosition, tailTip, x, y, frame, angle, maxDepth, nbList, initialImage, i):
    steps = self._hyperparameters["step"]

    if self.__weirdTrackingPoints(points, headPosition, tailTip):
      dontTakeThesePoints       = points.copy()
      dontTakeThesePointsAdding = points.copy()
      pointNumTest   = 0
      steps3 = [indStep for indStep in range(steps[0], steps[len(steps)-1])]
      # First Attempt: for each of the previously tracked points, prevent new tracking from choosing that previously tracked point + steps change
      while (self.__weirdTrackingPoints(points, headPosition, tailTip)) and (pointNumTest < len(dontTakeThesePoints[0])):
        points = np.zeros((2, 0))
        (points, lastFirstTheta2) = self._findNextPoints(0,x,y,frame,points,angle,maxDepth,steps3,nbList,initialImage,self._hyperparameters["debugHeadEmbededFindNextPoints"], np.transpose(np.array([dontTakeThesePoints[:,pointNumTest]])))
        dontTakeThesePointsAdding = np.concatenate((dontTakeThesePointsAdding, points), axis=1)
        dontTakeThesePointsAdding = np.unique(dontTakeThesePointsAdding, axis=1)
        points = np.insert(points, 0, headPosition, axis=1)
        pointNumTest = pointNumTest + 1

      if (pointNumTest == len(dontTakeThesePoints[0])) and (self.__weirdTrackingPoints(points, headPosition, tailTip)):
        pointNumTest   = 0
        # Second Attempt: for each of the previously tracked points, prevent new tracking from choosing any point in a 2 pixel radius of that previously tracked point + steps change
        while (self.__weirdTrackingPoints(points, headPosition, tailTip)) and (pointNumTest < len(dontTakeThesePoints[0])):
          points = np.zeros((2, 0))
          (points, lastFirstTheta2) = self.__findNextPoints(0,x,y,frame,points,angle,maxDepth,steps3,nbList,initialImage,self._hyperparameters["debugHeadEmbededFindNextPoints"], np.transpose(np.array([dontTakeThesePoints[:,pointNumTest]])), 2)
          dontTakeThesePointsAdding = np.concatenate((dontTakeThesePointsAdding, points), axis=1)
          dontTakeThesePointsAdding = np.unique(dontTakeThesePointsAdding, axis=1)
          points = np.insert(points, 0, headPosition, axis=1)
          pointNumTest = pointNumTest + 1

      if (pointNumTest == len(dontTakeThesePoints[0])) and (self.__weirdTrackingPoints(points, headPosition, tailTip)):
        points = np.zeros((2, 0))
        # Third attempt: prevents new tracking from choosing any of the initially tracked points as well as all the points tracked in the second and third attempt + step change
        (points, lastFirstTheta2) = self.__findNextPoints(0,x,y,frame,points,angle,maxDepth,steps3,nbList,initialImage,self._hyperparameters["debugHeadEmbededFindNextPoints"], dontTakeThesePointsAdding, 0)
        points = np.insert(points, 0, headPosition, axis=1)

      if (pointNumTest == len(dontTakeThesePoints[0])) and (self.__weirdTrackingPoints(points, headPosition, tailTip)):
        points = np.zeros((2, 0))
        # Third attempt: prevents new tracking from choosing any of the initially tracked points as well as all the points tracked in the second and third attempt + extended step change
        steps2 = [indStep for indStep in range(max(0, steps[0]-1), steps[len(steps)-1]+4)]
        (points, lastFirstTheta2) = self.__findNextPoints(0,x,y,frame,points,angle,maxDepth,steps2,nbList,initialImage,self._hyperparameters["debugHeadEmbededFindNextPoints"], dontTakeThesePointsAdding, 0)
        points = np.insert(points, 0, headPosition, axis=1)

      if (pointNumTest == len(dontTakeThesePoints[0])) and (self.__weirdTrackingPoints(points, headPosition, tailTip)):
        print("PROBLEM for frame", i, "despite applying correction procedure")
      else:
        print("Ok! Problem solved for frame", i)

    return points

  def _headEmbededTailTracking(self, headPosition, i, frame, maxDepth, tailTip):
    steps   = self._hyperparameters["step"]
    nbList  = 10 if self._hyperparameters["nbList"] == -1 else self._hyperparameters["nbList"]

    x = headPosition[0]
    y = headPosition[1]

    initialImage = frame.copy()

    gaussian_blur = self._hyperparameters["headEmbededParamGaussianBlur"]

    frame = cv2.GaussianBlur(frame, (gaussian_blur, gaussian_blur), 0)

    # angle = self._hyperparameters["headEmbededParamInitialAngle"]
    angle = self._calculateAngle(x, y, tailTip[0], tailTip[1])

    points = np.zeros((2, 0))

    (points, lastFirstTheta2) = self.__findNextPoints(0,x,y,frame,points,angle,maxDepth,steps,nbList,initialImage,self._hyperparameters["debugHeadEmbededFindNextPoints"])
    points = np.insert(points, 0, headPosition, axis=1)

    # Anomalie detection here
    headEmbededRetrackIfWeirdInitialTracking = self._hyperparameters["headEmbededRetrackIfWeirdInitialTracking"]
    if headEmbededRetrackIfWeirdInitialTracking:
      points = self.__retrackIfWeirdInitialTracking(points, headPosition, tailTip, self._hyperparameters, x, y, frame, angle, maxDepth, nbList, initialImage, i)

    if len(points[0]) > 3:
      if self._hyperparameters["smoothTailHeadEmbeded"]:
        for smoothTailIteration in range(0, self._hyperparameters["smoothTailHeadEmbededNbOfIterations"]):
          points = self.__smoothTail(points, self._nbTailPoints, self._hyperparameters["smoothTailHeadEmbeded"])
      else:
        if not(self._hyperparameters["adjustHeadEmbededTracking"]):
          points   = self._nbTailPoints(points, self._nbTailPoints)
        else:
          nDist    = len(points[0]) - 1
          stepDist = 10 / nDist
          tab      = [int((i/9)*nDist) for i in range(0,10)]
          points   = [[points[0][i] for i in tab], [points[1][i] for i in tab]]


    if False:
      polynomialDegree = 5
      points = self.__smoothBasedOnCurvature(points, polynomialDegree)


    output = np.zeros((1, len(points[0]), 2))

    for idx, x in enumerate(points[0]):
      output[0][idx][0] = x
      output[0][idx][1] = points[1][idx]

    return output

  def _headEmbededTailTrackFindMaxDepth(self, frame):
    if True:
      return math.sqrt((self._headPositionFirstFrame[0] - self._tailTipFirstFrame[0])**2 + (self._headPositionFirstFrame[1] - self._tailTipFirstFrame[1])**2)

    headEmbededParamTailDescentPixThreshStopInit = self._hyperparameters["headEmbededParamTailDescentPixThreshStop"]
    self._hyperparameters["headEmbededParamTailDescentPixThreshStop"] = 256

    x = self._headPositionFirstFrame[0]
    y = self._headPositionFirstFrame[1]

    steps   = self._hyperparameters["step"]
    nbList  = 10

    initialImage = frame.copy()

    gaussian_blur = self._hyperparameters["headEmbededParamGaussianBlur"]

    frame = cv2.GaussianBlur(frame, (gaussian_blur, gaussian_blur), 0)

    angle = self._calculateAngle(x, y, self._tailTipFirstFrame[0], self._tailTipFirstFrame[1])

    points = np.zeros((2, 0))

    (points, lastFirstTheta2) = self.__findNextPoints(0,x,y,frame,points,angle,self._hyperparameters["headEmbededTailTrackFindMaxDepthInitialMaxDepth"],steps,nbList,initialImage, self._hyperparameters["debugHeadEmbededFindNextPoints"])

    distToTip        = np.full((200),10000)
    distToBase       = np.full((200),10000)
    curTailLengthTab = np.full((200),10000)
    curTailLength  = 0

    k = 0
    distToTip[k]        = abs(math.sqrt((points[0,k]-self._tailTipFirstFrame[0])**2 + (points[1,k]-self._tailTipFirstFrame[1])**2))
    distToBase[k]       = abs(math.sqrt((points[0,k] - x)**2 + (points[1,k] - y)**2))
    curTailLength       = abs(math.sqrt((points[0,k] - x)**2 + (points[1,k] - y)**2))
    curTailLengthTab[k] = curTailLength

    k = 1
    distFromHeadToTip = abs(math.sqrt((x-self._tailTipFirstFrame[0])**2 + (y-self._tailTipFirstFrame[1])**2))
    while (curTailLength < 1.5*distFromHeadToTip) and (k < len(points[0])-1):
      curTailLength = curTailLength + abs(math.sqrt((points[0,k]-points[0,k-1])**2 + (points[1,k]-points[1,k-1])**2))
      distToTip[k]  = abs(math.sqrt((points[0,k]-self._tailTipFirstFrame[0])**2 + (points[1,k]-self._tailTipFirstFrame[1])**2))
      distToBase[k] = abs(math.sqrt((points[0,k] - x)**2 + (points[1,k] - y)**2))
      curTailLengthTab[k] = curTailLength
      k = k + 1

    minDistToTip    = 1000000
    indMinDistToTip = 0
    for idx, dist in enumerate(distToTip):
      if dist < minDistToTip:
        minDistToTip = dist
        indMinDistToTip = idx

    self._hyperparameters["headEmbededParamTailDescentPixThreshStop"] = headEmbededParamTailDescentPixThreshStopInit

    pathFactor = curTailLengthTab[indMinDistToTip] / distToBase[indMinDistToTip]

    return (math.sqrt((x - self._tailTipFirstFrame[0])**2 + (y - self._tailTipFirstFrame[1])**2)* pathFactor)

  def _adjustHeadEmbededHyperparameters(self, frame):
    dist = math.sqrt((self._headPositionFirstFrame[0] - self._tailTipFirstFrame[0])**2 + (self._headPositionFirstFrame[1] - self._tailTipFirstFrame[1])**2)
    factor = dist / 220

    if self._hyperparameters["headEmbededAutoSet_BackgroundExtractionOption"]:
      self._hyperparameters["headEmbededRemoveBack"] = 1
      self._hyperparameters["minPixelDiffForBackExtract"] = self._hyperparameters["headEmbededAutoSet_BackgroundExtractionOption"] # 7
      # if self._hyperparameters["invertBlackWhiteOnImages"] == 0:
      self._hyperparameters["extractBackWhiteBackground"] = 0
      # else:
        # self._hyperparameters["extractBackWhiteBackground"] = 1

    if self._hyperparameters["headEmbededAutoSet_ExtendedDescentSearchOption"]:
      initialStepsTab = [10,11,12,13,14,15,16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32,33,34,35,36,37,38,39,40,41,42,43,44,45,46,47,48,49,50]
    else:
      initialStepsTab = [10, 13, 15]
    self._hyperparameters["step"] = [int(val*factor) for val in initialStepsTab]
    self._hyperparameters["step"] = list(dict.fromkeys(self._hyperparameters["step"])) # removes duplicate values
    if len(self._hyperparameters["step"]) == 0:
      self._hyperparameters["step"] = [2, 4]

    if self._hyperparameters["overwriteFirstStepValue"] or self._hyperparameters["overwriteLastStepValue"]:
      self._hyperparameters["overwriteFirstStepValue"] = int(self._hyperparameters["overwriteFirstStepValue"])
      self._hyperparameters["overwriteLastStepValue"]  = int(self._hyperparameters["overwriteLastStepValue"])
      if self._hyperparameters["overwriteLastStepValue"] <= self._hyperparameters["overwriteFirstStepValue"]:
        self._hyperparameters["overwriteLastStepValue"] = self._hyperparameters["overwriteFirstStepValue"] + 1
      self._hyperparameters["overwriteNbOfStepValues"] = self._hyperparameters["overwriteLastStepValue"] - self._hyperparameters["overwriteFirstStepValue"] + 1
      step = [self._hyperparameters["overwriteFirstStepValue"] + stepVal for stepVal in range(0, self._hyperparameters["overwriteNbOfStepValues"])]
      self._hyperparameters["step"] = step

    self._hyperparameters["headEmbededParamGaussianBlur"] = int(13 * factor)

    if self._hyperparameters["overwriteHeadEmbededParamGaussianBlur"]:
      self._hyperparameters["headEmbededParamGaussianBlur"] = int(self._hyperparameters["overwriteHeadEmbededParamGaussianBlur"])

    if self._hyperparameters["headEmbededParamGaussianBlur"] % 2 == 0:
      self._hyperparameters["headEmbededParamGaussianBlur"] = self._hyperparameters["headEmbededParamGaussianBlur"] + 1

    self._hyperparameters["addBlackCircleOfHalfDiamOnHeadForBoutDetect"] = int(70 * factor)

    self._hyperparameters["headEmbededTailTrackFindMaxDepthInitialMaxDepth"] = int(300*factor)

    self._hyperparameters["trackingPointSizeDisplay"] = int(5*factor) if int(5*factor) > 0 else 1 # CAN DO BETTER HERE !!!

    tailTipSurroundingDiameter = int(15 * factor)
    x, y = self._tailTipFirstFrame
    videoWidth  = self._hyperparameters["videoWidth"]
    videoHeight = self._hyperparameters["videoHeight"]
    if y-tailTipSurroundingDiameter < 0:
      ymin = 0
    else:
      ymin = y-tailTipSurroundingDiameter
    if y+tailTipSurroundingDiameter > videoHeight:
      ymax = videoHeight - 1
    else:
      ymax = y+tailTipSurroundingDiameter
    if x-tailTipSurroundingDiameter < 0:
      xmin = 0
    else:
      xmin = x-tailTipSurroundingDiameter
    if x+tailTipSurroundingDiameter > videoWidth:
      xmax = videoWidth - 1
    else:
      xmax = x+tailTipSurroundingDiameter
    self._hyperparameters["headEmbededParamTailDescentPixThreshStop"] = int(np.mean(frame[int(ymin):int(ymax), int(xmin):int(xmax)]))

    if self._hyperparameters["headEmbededParamTailDescentPixThreshStopOverwrite"] != -1:
      self._hyperparameters["headEmbededParamTailDescentPixThreshStop"] = self._hyperparameters["headEmbededParamTailDescentPixThreshStopOverwrite"]

    if False:
      print("headEmbededParamTailDescentPixThreshStop:", self._hyperparameters["headEmbededParamTailDescentPixThreshStop"])
      print("dist:", dist)
      print("step:", self._hyperparameters["step"])
      print("headEmbededParamGaussianBlur:", self._hyperparameters["headEmbededParamGaussianBlur"])
      print("trackingPointSizeDisplay:", self._hyperparameters["trackingPointSizeDisplay"])


class _CenterOfMassTailTrackingMixin(_TailTrackingBase):
  @staticmethod
  def __smoothTail(points, nbTailPoints):
    y = points[0]
    x = linspace(0, 1, len(y))

    if len(x) > 3:
      s = UnivariateSpline(x, y, s=10)
      xs = linspace(0, 1, nbTailPoints)
      newX = s(xs)

      y = points[1]
      x = linspace(0, 1, len(y))
      s = UnivariateSpline(x, y, s=10)
      xs = linspace(0, 1, nbTailPoints)
      newY = s(xs)
    else:
      newX = x
      newY = y

    return [newX, newY]

  def __findNextPoints(self, depth, x, y, frame, points, angle, maxDepth, debug):
    step     = self._hyperparameters["centerOfMassParamStep"]
    segStep  = self._hyperparameters["centerOfMassParamSegStep"]
    halfDiam = self._hyperparameters["centerOfMassParamHalfDiam"]

    if debug:
      frameDisplay = frame.copy()
      frameDisplay = cv2.cvtColor(frameDisplay, cv2.COLOR_GRAY2RGB)

    lenX = len(frame[0]) - 1
    lenY = len(frame) - 1

    thetaDiffAccept = 0.4
    pixTotMax = 1000000
    maxTheta  = angle

    xNew = self._assignValueIfBetweenRange(int(x + step * (math.cos(angle))), 0, lenX)
    yNew = self._assignValueIfBetweenRange(int(y + step * (math.sin(angle))), 0, lenY)

    # if debug:
      # cv2.circle(frameDisplay, (xNew, yNew), 1, (0,0,0),   -1)

    framecopy = frame.copy()

    xmin = self._assignValueIfBetweenRange(xNew - halfDiam, 0, lenX-1)
    xmax = self._assignValueIfBetweenRange(xNew + halfDiam, 0, lenX-1)
    ymin = self._assignValueIfBetweenRange(yNew - halfDiam, 0, lenY-1)
    ymax = self._assignValueIfBetweenRange(yNew + halfDiam, 0, lenY-1)

    if debug:
      cv2.circle(frameDisplay, (xmin, ymin), 1, (255,0,0),   -1)
      cv2.circle(frameDisplay, (xmax, ymax), 1, (255,0,0),   -1)
      cv2.circle(frameDisplay, (x, y),       1, (0,255,0),   -1)

    if (xmin==0 or xmin==lenX-1 or xmax==0 or xmax==lenX-1 or ymin==0 or ymin==lenY-1 or ymax==0 or ymax==lenY-1):
      return (points,0)

    framecopy[0:ymin, :]              = 255
    framecopy[ymax:lenY+1, :]         = 255
    framecopy[:, 0:xmin]              = 255
    framecopy[:, xmax:lenX+1]         = 255

    if debug:
      self._debugFrame(framecopy, title='Frame2')

    (minVal, maxVal, headPosition, maxLoc) = cv2.minMaxLoc(framecopy)

    xNew = headPosition[0]
    yNew = headPosition[1]

    theta = self._calculateAngle(x, y, xNew, yNew)

    xNew = self._assignValueIfBetweenRange(int(x + segStep  * (math.cos(theta)) ), 0, lenX)
    yNew = self._assignValueIfBetweenRange(int(y + segStep  * (math.sin(theta)) ), 0, lenY)

    # Calculates distance between new and old point
    distSubsquentPoints = math.sqrt((xNew - x)**2 + (yNew - y)**2)

    if debug:
      cv2.circle(frameDisplay, (xNew, yNew), 1, (0,0,255),   -1)
      self._debugFrame(frameDisplay, title='Frame2')
      self._debugFrame(framecopy, title='Frame2')

    points = self._appendPoint(xNew, yNew, points)
    newTheta = self._calculateAngle(x,y,xNew,yNew)
    if distSubsquentPoints > 0 and depth < maxDepth:
      (points,nop) = self.__findNextPoints(depth+distSubsquentPoints,xNew,yNew,frame,points,newTheta,maxDepth,debug)

    return (points,newTheta)

  def _centerOfMassTailTracking(self, headPosition, frame, maxDepth):
    x = headPosition[0]
    y = headPosition[1]

    initialAngle = self._hyperparameters["headEmbededParamInitialAngle"]

    gaussian_blur = self._hyperparameters["headEmbededParamGaussianBlur"]
    frame = cv2.GaussianBlur(frame, (gaussian_blur, gaussian_blur), 0)
    points = np.zeros((2, 0))

    # if i > 63033:
      # (points, lastFirstTheta2) = self.__findNextPoints(0,x,y,frame,points,initialAngle,maxDepth,True)
    # else:
    (points, lastFirstTheta2) = self.__findNextPoints(0,x,y,frame,points,initialAngle,maxDepth,False)

    output = np.zeros((1, self._nbTailPoints, 2))

    points = np.insert(points, 0, headPosition, axis=1)

    points = points[:,0:(len(points[0])-1)]

    points = self.__smoothTail(points, self._nbTailPoints)

    for idx, x in enumerate(points[0]):
      output[0][idx][0] = x
      output[0][idx][1] = points[1][idx]

    return output

  def _centerOfMassTailTrackFindMaxDepth(self, frame):
    gaussian_blur = self._hyperparameters["headEmbededParamGaussianBlur"]
    frame = cv2.GaussianBlur(frame, (gaussian_blur, gaussian_blur), 0)
    angle = self._hyperparameters["headEmbededParamInitialAngle"]
    points = np.zeros((2, 0))

    x = self._headPositionFirstFrame[0]
    y = self._headPositionFirstFrame[1]

    (points, lastFirstTheta2) = self.__findNextPoints(0,x,y,frame,points,angle,300,False)

    distToTip        = np.full((200),10000)
    curTailLengthTab = np.full((200),10000)
    curTailLength  = 0
    k = 0

    distFromHeadToTip = abs(math.sqrt((x-self._tailTipFirstFrame[0])**2 + (y-self._tailTipFirstFrame[1])**2))
    while (curTailLength < 1.5*distFromHeadToTip) and (k < len(points[0])-1):
      curTailLength = curTailLength + abs(math.sqrt((points[0,k]-points[0,k+1])**2 + (points[1,k]-points[1,k+1])**2))
      distToTip[k]  = abs(math.sqrt((points[0,k]-self._tailTipFirstFrame[0])**2 + (points[1,k]-self._tailTipFirstFrame[1])**2))
      curTailLengthTab[k] = curTailLength
      k = k + 1

    minDistToTip    = 1000000
    indMinDistToTip = 0
    for idx, dist in enumerate(distToTip):
      if dist < minDistToTip:
        minDistToTip = dist
        indMinDistToTip = idx

    return (curTailLengthTab[indMinDistToTip])


class _HeadEmbeddedTailTrackingTeresaNicolsonMixin(_TailTrackingBase):
  @staticmethod
  def __smoothTail(points, nbTailPoints):
    y = points[0]
    x = linspace(0, 1, len(y))

    if len(x) > 3:

      points2 = []
      for i in range(0, len(points[0])-1):
        if not((points[0][i] == points[0][i+1]) and (points[1][i] == points[1][i+1])):
          points2.append([points[0][i], points[1][i]])

      i = len(points[0]) - 1
      if not((points[0][i-1] == points[0][i]) and (points[1][i-1] == points[1][i])):
        points2.append([points[0][i], points[1][i]])

      points = np.array(points2).T

      # Define some points:
      points = np.array([points[0], points[1]]).T  # a (nbre_points x nbre_dim) array

      # Linear length along the line:
      distance = np.cumsum( np.sqrt(np.sum( np.diff(points, axis=0)**2, axis=1 )) )
      distance = np.insert(distance, 0, 0)/distance[-1]

      # Interpolation for different methods:
      interpolation_method = 'quadratic'    # 'slinear', 'quadratic', 'cubic'
      alpha = np.linspace(0, 1, nbTailPoints)

      interpolated_points = {}

      interpolator =  interp1d(distance, points, kind=interpolation_method, axis=0)
      interpolated_points = interpolator(alpha)

      interpolated_points = interpolated_points.T

      newX = interpolated_points[0]
      newY = interpolated_points[1]

    else:

      newX = points[0]
      newY = points[1]

    return [newX, newY]

  def __findNextPoints(self, depth, x, y, frame, points, angle, maxDepth, steps, nbList, initialImage, debug):
    lenX = len(frame[0]) - 1
    lenY = len(frame) - 1

    thetaDiffAccept = 1 #0.4

    if depth < 0.15*maxDepth:
      thetaDiffAccept = 0.4

    if depth > 0.85*maxDepth:
      thetaDiffAccept = 0.6

    pixTotMax = 1000000
    maxTheta  = angle

    l = [i*(math.pi/nbList) for i in range(0,2*nbList) if self._distBetweenThetas(i*(math.pi/nbList), angle) < thetaDiffAccept]

    if debug:
      print("debug")

    xTot = self._assignValueIfBetweenRange(x + steps[0], 0, lenX)
    yTot = self._assignValueIfBetweenRange(y, 0, lenY)
    if yTot == 0:
      yTot = 400

    for step in steps:

      for theta in l:

        xNew = self._assignValueIfBetweenRange(int(x + step * (math.cos(theta))), 0, lenX)
        yNew = self._assignValueIfBetweenRange(int(y + step * (math.sin(theta))), 0, lenY)
        pixTot = frame[yNew][xNew]

        if debug:
          print([theta,pixTot])

        # Keeps that theta angle as maximum if appropriate
        if (pixTot < pixTotMax):
          pixTotMax = pixTot
          maxTheta = theta
          if depth < 0.4*maxDepth:
            if xNew > x:
              xTot = xNew
              yTot = yNew
          else:
            xTot = xNew
            yTot = yNew

    w = 8 # THIS IS IMPORTANT
    ym = yTot - w
    yM = yTot + w
    xm = xTot - w
    xM = xTot + w
    if ym < 0:
      ym = 0
    if xm < 0:
      xm = 0
    if yM > len(initialImage):
      yM = len(initialImage)
    if xM > len(initialImage[0]):
      xM = len(initialImage[0])

    pixSur = np.min(initialImage[ym:yM, xm:xM])
    if debug:
      print("depth:", depth, " ; maxDepth:", maxDepth, " ; pixSur:", pixSur)

    # if depth > 0.95*maxDepth:
      # pixTot = frame[y][x]
      # if (pixTot < pixTotMax):
        # pixTotMax = pixTot
        # maxTheta = theta
        # xTot = x
        # yTot = y
        # depth = maxDepth + 10

    if debug:
      print(["max:",maxTheta,pixTotMax])

    # Calculates distance between new and old point
    distSubsquentPoints = math.sqrt((xTot - x)**2 + (yTot - y)**2)

    pixSurMax = 150
    if ((pixSur < pixSurMax) or (depth < 2*0.85*maxDepth)):
      points = self._appendPoint(xTot, yTot, points)
      if debug:
        cv2.circle(frame, (xTot, yTot), 3, (255,0,0),   -1)
        self._debugFrame(frame, title='HeadEmbeddedTailTracking')

    newTheta = self._calculateAngle(x,y,xTot,yTot)

    if (distSubsquentPoints > 0) and (depth < 2*maxDepth) and (xTot < 1280 - 10) and (yTot > 10) and (yTot < 1024 - 10) and ((pixSur < pixSurMax) or (depth < 2*0.85*maxDepth)):
      (points,nop) = self.__findNextPoints(depth+distSubsquentPoints,xTot,yTot,frame,points,newTheta,maxDepth,steps,nbList,initialImage,debug)

    return (points,newTheta)

  def _headEmbededTailTrackingTeresaNicolson(self, headPosition, frame, maxDepth, tailTip, threshForBlackFrames):
    steps   = self._hyperparameters["step"]
    nbList  = 10

    x = headPosition[0]
    y = headPosition[1]

    initialImage = frame.copy()

    gaussian_blur = self._hyperparameters["headEmbededParamGaussianBlur"]
    frame = cv2.GaussianBlur(frame, (gaussian_blur, gaussian_blur), 0)
    # angle = self._hyperparameters["headEmbededParamInitialAngle"]
    angle = self._calculateAngle(x, y, tailTip[0], tailTip[1])

    points = np.zeros((2, 0))

    if np.mean(np.mean(frame)) > threshForBlackFrames:
      (points, lastFirstTheta2) = self.__findNextPoints(0,x,y,frame,points,angle,maxDepth,steps,nbList,initialImage,self._hyperparameters["debugHeadEmbededFindNextPoints"])
      points = np.insert(points, 0, headPosition, axis=1)
      if len(points[0]) > 3:
        points = self.__smoothTail(points, self._nbTailPoints)
      points[0][0] = headPosition[0]
      points[1][0] = headPosition[1]
    else:
      points = np.zeros((2, self._nbTailPoints))

    output = np.zeros((1, len(points[0]), 2))

    for idx, x in enumerate(points[0]):
      output[0][idx][0] = x
      output[0][idx][1] = points[1][idx]

    return output

  def _headEmbededTailTrackFindMaxDepthTeresaNicolson(self, frame):
    x = self._headPositionFirstFrame[0]
    y = self._headPositionFirstFrame[1]

    steps   = self._hyperparameters["step"]
    nbList  = 10

    initialImage = frame.copy()

    gaussian_blur = self._hyperparameters["headEmbededParamGaussianBlur"]
    frame = cv2.GaussianBlur(frame, (gaussian_blur, gaussian_blur), 0)

    angle = self._calculateAngle(x, y, self._tailTipFirstFrame[0], self._tailTipFirstFrame[1])

    points = np.zeros((2, 0))

    (points, lastFirstTheta2) = self.__findNextPoints(0,x,y,frame,points,angle,self._hyperparameters["headEmbededTailTrackFindMaxDepthInitialMaxDepth"],steps,nbList,initialImage, self._hyperparameters["debugHeadEmbededFindNextPoints"])

    distToTip        = np.full((200),10000)
    curTailLengthTab = np.full((200),10000)
    curTailLength  = 0
    k = 0

    distFromHeadToTip = abs(math.sqrt((x-self._tailTipFirstFrame[0])**2 + (y-self._tailTipFirstFrame[1])**2))
    while (curTailLength < 1.5*distFromHeadToTip) and (k < len(points[0])-1):
      curTailLength = curTailLength + abs(math.sqrt((points[0,k]-points[0,k+1])**2 + (points[1,k]-points[1,k+1])**2))
      distToTip[k]  = abs(math.sqrt((points[0,k]-self._tailTipFirstFrame[0])**2 + (points[1,k]-self._tailTipFirstFrame[1])**2))
      curTailLengthTab[k] = curTailLength
      k = k + 1

    minDistToTip    = 1000000
    indMinDistToTip = 0
    for idx, dist in enumerate(distToTip):
      if dist < minDistToTip:
        minDistToTip = dist
        indMinDistToTip = idx

    return (curTailLengthTab[indMinDistToTip] )

  def __getMeanOfImageOverVideo(self):
    cap = zzVideoReading.VideoCapture(self._videoPath)
    meanss = []
    ret = True
    i = 0
    while (i < 100):
      ret, frame = cap.read()
      if ret:
        if self._hyperparameters["invertBlackWhiteOnImages"]:
          frame = 255 - frame
        val = np.mean(np.mean(frame))
        meanss.append(val)
      i = i +1
    return np.mean(meanss)

  def _getThresForBlackFrame(self):
    threshForBlackFrames = 0
    if self._hyperparameters["headEmbededTeresaNicolson"] == 1:
      imagesMeans = self.__getMeanOfImageOverVideo()
      threshForBlackFrames = imagesMeans * 0.8 #0.75
    return threshForBlackFrames

  def _savingBlackFrames(self):
    if self._hyperparameters["headEmbededTeresaNicolson"] == 1:
      if self._hyperparameters["noBoutsDetection"] == 1:
        f = open(os.path.join(self._hyperparameters["outputFolder"], os.path.join(self._videoName, 'blackFrames_' + self._videoName + '.csv')), "a")
        for k in range(1,len(output[0])):
          if np.sum(output[0, k]) == 0:
            output[0, k] = output[0, k-1]
            f.write(str(k)+'\n')
        f.close()


class _TailTrackingBlobDescentMixin(_TailTrackingBase):
  @staticmethod
  def __dist2(v, w):
    return (v["x"] - w["x"])**2 + (v["y"] - w["y"])**2

  @staticmethod
  def __distToSegmentSquared(p, v, w):
    l2 = dist2(v, w)
    if l2 == 0:
      return dist2(p, v)
    t = ((p["x"] - v["x"]) * (w["x"] - v["x"]) + (p["y"] - v["y"]) * (w["y"] - v["y"])) / l2
    t = max(0, min(1, t))
    return self.__dist2(p, {"x": v["x"] + t * (w["x"] - v["x"]), "y": v["y"] + t * (w["y"] - v["y"]) })

  @staticmethod
  def __distToSegment(p, v, w):
    return math.sqrt(self.__distToSegmentSquared(p, v, w))

  @staticmethod
  def __checkNewPointNotRedundant(points, x, y):
    if len(points[0]) > 3:
      dist = (points[0] - x)**2 + (points[1] - y)**2
      min1 = np.argmin(dist)
      minDist = dist[min1]

      p = {"x": x, "y": y}
      for i in range(0,len(points[0])-1):
        v = {"x": points[0][i],   "y": points[1][i]   }
        w = {"x": points[0][i+1], "y": points[1][i+1] }
        d = self.__distToSegment(p, v, w)
        if d < minDist:
          minDist = d

      if minDist <= 1:
        return 0
      else:
        return 1
    else:
      return 1

  @staticmethod
  def __recenterPointAlongOrthogonalTailAxis(x,y,theta,frame,thresh1):
    l = [[x,y]]

    thresh1lenX = len(thresh1[0]) - 1
    thresh1lenY = len(thresh1) - 1

    pixVal = 1
    k1 = 1
    while pixVal < 150 and k1 < 100:
      xNew = self._assignValueIfBetweenRange(int(x + k1 * (math.cos(theta)) ), 0, thresh1lenX)
      yNew = self._assignValueIfBetweenRange(int(y + k1 * (math.sin(theta)) ), 0, thresh1lenY)
      pixVal = thresh1[yNew][xNew]
      if pixVal < 150:
        k1 = k1 + 1
        cv2.circle(frame, (xNew, yNew), 1, (0,0,0),   -1)
        point = [xNew, yNew]
        l.append(point)

    pixVal = 1
    k2 = 1
    while pixVal < 150 and k2 < 100:
      xNew = self._assignValueIfBetweenRange(int(x - k2 * (math.cos(theta)) ), 0, thresh1lenX)
      yNew = self._assignValueIfBetweenRange(int(y - k2 * (math.sin(theta)) ), 0, thresh1lenY)
      pixVal = thresh1[yNew][xNew]
      if pixVal < 150:
        k2 = k2 + 1
        cv2.circle(frame, (xNew, yNew), 1, (0,0,0),   -1)
        point = [xNew, yNew]
        l = [point] + l

    n = len(l)
    xNew = self._assignValueIfBetweenRange(int((l[0][0] + l[n-1][0]) / 2), 0, thresh1lenX)
    yNew = self._assignValueIfBetweenRange(int((l[0][1] + l[n-1][1]) / 2), 0, thresh1lenY)

    return [xNew, yNew]

  def __findNextPoints(self, x, y, thresh1, frame, depth, points, lastTheta, debugAdv, nbList, thetaDiffAccept, expDecreaseFactor, step, debugTracking):
    thresh1lenX = len(thresh1[0]) - 1
    thresh1lenY = len(thresh1) - 1

    maxThetaCorrected = -1

    if debugAdv:
      self._debugFrame(frame, title='Frame')

    if (depth < 25): #15):
      maxTheta = 0
      ktotMax = 0
      k1Max = 0
      k2Max = 0

      l = [i*(math.pi/nbList) for i in range(0,2*nbList) if abs(i*(math.pi/nbList)-lastTheta) < thetaDiffAccept]

      for thetaB in l:
        theta = thetaB % math.pi

        # Find furtherest point away from "old" "current" point still inside blob along the theta angle in one direction
        pixVal = 1
        k1 = 1
        while pixVal < 150 and k1 < 100:
          xNew = self._assignValueIfBetweenRange(int(x + k1 * (math.cos(theta))), 0, thresh1lenX)
          yNew = self._assignValueIfBetweenRange(int(y + k1 * (math.sin(theta))), 0, thresh1lenY)
          pixVal = thresh1[yNew][xNew]
          k1 = k1 + 1
        k1 = k1 - 2

        # Find furtherest point away from "old" "current" point still inside blob along the theta angle in the other direction
        pixVal = 1
        k2 = 1
        while pixVal < 150 and k2 < 100:
          xNew = self._assignValueIfBetweenRange(int(x - k2 * (math.cos(theta)) ), 0, thresh1lenX)
          yNew = self._assignValueIfBetweenRange(int(y - k2 * (math.sin(theta)) ), 0, thresh1lenY)
          pixVal = thresh1[yNew][xNew]
          k2 = k2 + 1
        k2 = k2 - 2
        ktot = k1 + k2

        # Calculate "score" for this theta angle based on the lenght of the segment fitted inside the blob
        ktot = 0
        for i in range(0,k1):
          ktot = ktot + math.exp(-i*expDecreaseFactor)
        for i in range(0,k2):
          ktot = ktot + math.exp(-i*expDecreaseFactor)

        # Keeps that theta angle as maximum if appropriate
        if (ktot > ktotMax):
          ktotMax = ktot
          k1Max = k1
          k2Max = k2
          maxTheta = theta

      # Calculates the two new possible points on both side of the local tail angle derivate
      if k1Max > step:
        x1 = self._assignValueIfBetweenRange(int(x + step  * (math.cos(maxTheta)) ), 0, thresh1lenX)
        y1 = self._assignValueIfBetweenRange(int(y + step  * (math.sin(maxTheta)) ), 0, thresh1lenY)
      else:
        x1 = self._assignValueIfBetweenRange(int(x + k1Max  * (math.cos(maxTheta)) ), 0, thresh1lenX)
        y1 = self._assignValueIfBetweenRange(int(y + k1Max  * (math.sin(maxTheta)) )  , 0, thresh1lenY)
      if k2Max > step:
        x2 = self._assignValueIfBetweenRange(int(x - step  * (math.cos(maxTheta)) ), 0, thresh1lenX)
        y2 = self._assignValueIfBetweenRange(int(y - step  * (math.sin(maxTheta)) ), 0, thresh1lenY)
      else:
        x2 = self._assignValueIfBetweenRange(int(x - k2Max  * (math.cos(maxTheta)) ), 0, thresh1lenX)
        y2 = self._assignValueIfBetweenRange(int(y - k2Max  * (math.sin(maxTheta)) ), 0, thresh1lenY)

      # Sanity check
      if debugTracking:
        if thresh1[y2][x2] > 150:
          print("oups white zone forw",k2Max)
        if thresh1[y1][x1] > 150:
          print("oups white zone back",k1Max)

      if (depth == 0):
        predictedTetha = maxTheta
      else:
        predictedTetha = maxTheta + ((maxTheta - lastTheta + 2*math.pi) % (2*math.pi))
      [x1, y1] = self.__recenterPointAlongOrthogonalTailAxis(x1, y1, predictedTetha+(math.pi)/2, frame, thresh1)
      [x2, y2] = self.__recenterPointAlongOrthogonalTailAxis(x2, y2, predictedTetha+(math.pi)/2, frame, thresh1)

      x1 = self._assignValueIfBetweenRange(x1, 0, thresh1lenX)
      y1 = self._assignValueIfBetweenRange(y1, 0, thresh1lenY)
      x2 = self._assignValueIfBetweenRange(x2, 0, thresh1lenX)
      y2 = self._assignValueIfBetweenRange(y2, 0, thresh1lenY)

      cv2.circle(frame, (x, y), 1, (255,0,255),   -1)

      # Calculates distance between new and old local tail angle
      diffAngle1 = self._distBetweenThetas(lastTheta, maxTheta )
      diffAngle2 = self._distBetweenThetas(lastTheta, (maxTheta + math.pi) )

      # Calculates distance between new and old point
      distSubsquentPoints1 = (x1 - x)**2 + (y1 - y)**2
      distSubsquentPoints2 = (x2 - x)**2 + (y2 - y)**2

      # If the distance between new and old point larger than 0, appends points and launch search for new point
      if (diffAngle1 > diffAngle2):
        if debugTracking:
          if thresh1[y2][x2] > 150:
            print("oups white zone")
          if debugAdv:
            print("diffAngle2: ",diffAngle2," ; k2Max: ",k2Max," distSubsquentPoints2:",distSubsquentPoints2)
        cv2.circle(frame, (x2, y2), 1, (0,255,0),   -1)
        check = self.__checkNewPointNotRedundant(points, x2, y2)
        if check:
          points = self._appendPoint(x2, y2, points)
          if distSubsquentPoints2 > 0:
            maxThetaCorrected = maxTheta + math.pi
            newTheta = self._calculateAngle(x,y,x2,y2)
            (points,nop) = self.__findNextPoints(x2,y2,thresh1,frame,depth+1,points,newTheta,debugAdv,nbList,thetaDiffAccept,expDecreaseFactor,step,debugTracking)
      else:
        if debugTracking:
          if thresh1[y1][x1] > 150:
            print("oups white zone")
          if debugAdv:
            print("diffAngle1: ",diffAngle1," ; k1Max: ",k1Max," distSubsquentPoints1:",distSubsquentPoints1)
        cv2.circle(frame, (x1, y1), 1, (0,255,0),   -1)
        check = self.__checkNewPointNotRedundant(points, x1, y1)
        if check:
          points = self._appendPoint(x1, y1, points)
          if distSubsquentPoints1 > 0:
            maxThetaCorrected = maxTheta
            newTheta = self._calculateAngle(x,y,x1,y1)
            (points,nop) = self.__findNextPoints(x1,y1,thresh1,frame,depth+1,points,newTheta,debugAdv,nbList,thetaDiffAccept,expDecreaseFactor,step,debugTracking)

    return (points,maxThetaCorrected)

  @staticmethod
  def __smoothTail(points, nbTailPoints):
    y = points[0]
    x = linspace(0, 1, len(y))

    if len(x) > 3:

      s = UnivariateSpline(x, y, s=10)
      xs = linspace(0, 1, nbTailPoints)
      newX = s(xs)

      y = points[1]
      x = linspace(0, 1, len(y))
      s = UnivariateSpline(x, y, s=10)
      xs = linspace(0, 1, nbTailPoints)
      newY = s(xs)
    else:
      newX = x
      newY = y

    return [newX, newY]

  def _tailTrackingBlobDescent(self, headPosition, i, thresh1, frame, lastFirstTheta, debugAdv, thetaDiffAccept):
    step = self._hyperparameters["step"]
    nbList = self._hyperparameters["nbList"]
    expDecreaseFactor = self._hyperparameters["expDecreaseFactor"]
    firstFrame = self._hyperparameters["firstFrame"]
    lastFrame = self._hyperparameters["lastFrame"]
    minArea = self._hyperparameters["minArea"]
    maxArea = self._hyperparameters["maxArea"]
    headSize = self._hyperparameters["headSize"]
    debugTracking = self._hyperparameters["debugTracking"]
    headEmbeded = self._hyperparameters["headEmbeded"]
    x, y = headPosition

    output = np.zeros((1, self._nbTailPoints, 2))

    possiblePoints = []
    for ste in step:
      points = np.zeros((2, 0))
      (points, lastFirstTheta2) = self.__findNextPoints(x,y,thresh1,frame,0,points,lastFirstTheta,debugAdv,nbList,thetaDiffAccept,expDecreaseFactor,ste,debugTracking)
      possiblePoints.append(points)

    nbPossiblePoints = len(possiblePoints)
    minDist = 1000
    pBest = 0
    if nbPossiblePoints == 1:
      points = possiblePoints[0]
    else:
      for p1 in range(0, nbPossiblePoints):
        for p2 in range(0, nbPossiblePoints):
          if p2 > p1:
            points1 = possiblePoints[p1]
            n1 = len(points1[0]) - 1
            x1 = int(points1[0][n1])
            y1 = int(points1[1][n1])

            points2 = possiblePoints[p2]
            n2 = len(points2[0]) - 1
            x2 = int(points2[0][n2])
            y2 = int(points2[1][n2])

            dist = math.sqrt((x1-x2)**2 + (y1-y2)**2)
            if dist < minDist:
              minDist = dist
              pBest = p1
      points = possiblePoints[pBest]

    points = np.insert(points, 0, headPosition, axis=1)
    points = self.__smoothTail(points, self._nbTailPoints)

    # for idx, x in enumerate(points[0]):
      # output[i-firstFrame][idx][0] = x
      # output[i-firstFrame][idx][1] = points[1][idx]

    for idx, x in enumerate(points[0]):
      output[0][idx][0] = x
      output[0][idx][1] = points[1][idx]

    return output


class _FindTailExtremityMixin:
  @staticmethod
  def __initialiseDistance2(distance, boundary):
    TotalBPts   = len(boundary)
    distance[0] = 0
    for i in range(1, TotalBPts+1):
      if (i == TotalBPts):
        Pt = boundary[0][0]
      else:
        Pt = boundary[i][0]
      AvantPt = boundary[i-1][0]
      Dx = AvantPt[0] - Pt[0]
      Dy = AvantPt[1] - Pt[1]
      if i:
        distance[i] = distance[i-1] + math.sqrt(Dx*Dx + Dy*Dy)
      else:
        distance[i] = math.sqrt(Dx*Dx + Dy*Dy)
    return [distance[TotalBPts], distance]

  @staticmethod
  def __calculateJuge(indice, distance, max):
    juge = 0
    if distance[indice] < max - distance[indice]:
      juge = (max-2*distance[indice])/max
    else:
      juge = (2*distance[indice]-max)/max
    return juge

  @staticmethod
  def __calculateJuge2(indice, distance, bord1, bord2, nb):

    dist  = 0
    dist2 = 0
    dist3 = 0
    dist4 = 0
    mindist = 10000000000

    if indice < bord1:
      dist  = distance[bord1] - distance[indice]
      dist2 = distance[indice] + (distance[nb] - distance[bord1])
    else:
      dist  = distance[indice] - distance[bord1]
      dist2 = distance[bord1] + ( distance[nb] - distance[indice] )

    if indice < bord2:
      dist3 = distance[bord2] - distance[indice]
      dist4 = distance[indice] + ( distance[nb] - distance[bord2] )
    else:
      dist3 = distance[indice] - distance[bord2]
      dist4 = distance[bord2] + ( distance[nb] - distance[indice] )

    if dist < mindist:
      mindist = dist

    if dist2 < mindist:
      mindist = dist2

    if dist3 < mindist:
      mindist = dist3

    if dist4 < mindist:
      mindist = dist4

    return mindist

  def __insideTailExtremete(self, distance, DotProds, max_droite, min_gauche, max_bas, min_haut, ind_droite, ind_gauche, ind_bas, ind_haut, tailRange, boundary, dst):
    TotalBPts = len(boundary)

    # This may require some adjustements in the future (maybe some value other than 25)
    dist_calculate_curv = int(TotalBPts / 25)
    if dist_calculate_curv < 3:
      dist_calculate_curv = 3

    max = 0

    AheadPtr  = 0
    BehindPtr = 0
    Ptr       = 0

    juge = 0
    x = 0
    y = 0

    for i in tailRange:
      AheadPtr = (i + dist_calculate_curv) % TotalBPts
      BehindPtr = (i + TotalBPts - dist_calculate_curv) % TotalBPts
      Ptr = i % TotalBPts
      AheadPt = boundary[AheadPtr][0]
      Pt = boundary[Ptr][0]

      BehindPt    = boundary[BehindPtr][0]
      AheadVec    = [AheadPt[0] - Pt[0],  AheadPt[1] - Pt[1]]

      BehindVec   = [Pt[0] - BehindPt[0], Pt[1] - BehindPt[1]]
      DotProdVal  = (AheadVec[0])*(BehindVec[0]) + (AheadVec[1])*(BehindVec[1])
      DotProds[i] = DotProdVal
      x = Pt[0]
      y = Pt[1]

      # Hmm... not sure about this part bellow...
      fin_boucle = tailRange[len(tailRange)-1]
      juge = self.__calculateJuge(i,distance,distance[fin_boucle-1])
      # The line above should probably be replace by the one below at some point !!!
      # juge=self.__calculateJuge2(i,distance,bord1,bord2,TotalBPts);
      # (juge > trackParameters.minDistFromTailExtremityToTailBasis)

      if x > max_droite:
        max_droite = x
        ind_droite = i
      if x < min_gauche:
        min_gauche = x
        ind_gauche = i
      if y > max_bas:
        max_bas = y
        ind_bas = i
      if (y < min_haut): # and (juge < 0.20):
        min_haut = y
        ind_haut = i

      droite = ind_droite
      gauche = ind_gauche
      haut   = ind_haut
      bas    = ind_bas

      max = distance[i]

    return [max, max_droite, min_gauche, max_bas, min_haut, ind_droite, ind_gauche, ind_bas, ind_haut]

  def _findTailExtremete(self, rotatedContour, bodyContour, aaa, bord1b, bord2b, debug, dst, tailExtremityMaxJugeDecreaseCoeff):
    max  = 0
    max2 = 0
    TotalBPts = len(rotatedContour)
    DotProds = np.zeros(TotalBPts)
    distance = np.zeros(TotalBPts)

    for i in range(0, TotalBPts):
      distance[i] = 0

    distance2 = np.zeros(TotalBPts+1)
    for i in range(0, TotalBPts):
      distance2[i] = 0

    [d, distance2] = self.__initialiseDistance2(distance2, rotatedContour)

    max_droite = 0
    min_gauche = 5000
    max_bas    = 0
    min_haut   = 5000

    ind_droite = 0
    ind_gauche = 0
    ind_bas    = 0
    ind_haut   = 0

    x = 0
    y = 0

    bord1 = 0
    bord2 = 0
    if (bord2b < bord1b):
      bord1 = bord2b
      bord2 = bord1b
    else:
      bord1 = bord1b
      bord2 = bord2b

    Bord1 = rotatedContour[bord1][0]
    Bord2 = rotatedContour[bord2][0]

    max1 = distance2[bord2] - distance2[bord1]
    max2 = (distance2[bord1] - distance2[0])  + (distance2[len(rotatedContour)] - distance2[bord2])

    if self._hyperparameters["checkAllContourForTailExtremityDetect"] == 0:
      tailRange = []
      if (max1 > max2):
        for i in range(bord1, bord2):
          tailRange.append(i)
      else:
        for i in range(0, bord1):
          tailRange.append(i)
        for i in range(bord2, len(rotatedContour)):
          tailRange.append(i)
    else:
      tailRange = []
      for i in range(0, len(rotatedContour)):
        tailRange.append(i)

    [max2, max_droite, min_gauche, max_bas, min_haut, ind_droite, ind_gauche, ind_bas, ind_haut] = self.__insideTailExtremete(distance2, DotProds, max_droite, min_gauche, max_bas, min_haut, ind_droite, ind_gauche, ind_bas, ind_haut, tailRange, rotatedContour, dst)

    MostCurvy = 100000
    CurrentCurviness = 0
    MostCurvyIndex = 0
    TailIndex = 0

    max_dist = 15000.0

    jugeDroite = self.__calculateJuge2(ind_droite,distance2,bord1,bord2,TotalBPts)
    jugeGauche = self.__calculateJuge2(ind_gauche,distance2,bord1,bord2,TotalBPts)
    jugeHaut   = self.__calculateJuge2(ind_haut,distance2,bord1,bord2,TotalBPts)
    jugeBas    = self.__calculateJuge2(ind_bas,distance2,bord1,bord2,TotalBPts)
    maxJuge    = 0.0
    if jugeDroite > jugeGauche:
      maxJuge = jugeDroite
    else:
      maxJuge = jugeGauche

    if jugeHaut > maxJuge:
      maxJuge = jugeHaut

    if jugeBas > maxJuge:
      maxJuge = jugeBas

    maxJuge = maxJuge - tailExtremityMaxJugeDecreaseCoeff * maxJuge

    if debug:
      print("MostCurvy:",MostCurvy,";maxJuge:",maxJuge)

    DotProdPtr = DotProds[ind_droite]
    if debug:
      print("Droite (red) = curv: ", DotProdPtr, " ; jugeDroite: ", jugeDroite)

    if ((DotProdPtr < MostCurvy) and (jugeDroite > maxJuge)):
      MostCurvy =  DotProdPtr
      MostCurvyIndex = ind_droite
      if debug:
        print("droite wins")

    DotProdPtr=DotProds[ind_gauche]
    if (debug):
      print("Gauche (blue) = curv: ", DotProdPtr, " ; jugeGauche: ", jugeGauche)

    if (( DotProdPtr < MostCurvy) and (jugeGauche > maxJuge)):
      MostCurvy =  DotProdPtr
      MostCurvyIndex = ind_gauche
      if (debug):
        print("gauche wins")

    DotProdPtr = DotProds[ind_haut]
    if debug:
      print("Haut (white) = curv: ", DotProdPtr, " ; jugeHaut: ", jugeHaut)

    if (( DotProdPtr < MostCurvy) and (jugeHaut > maxJuge) and self._hyperparameters["considerHighPointForTailExtremityDetect"]):
      MostCurvy =  DotProdPtr
      MostCurvyIndex = ind_haut
      if (debug):
        print("haut wins")

    DotProdPtr = DotProds[ind_bas]
    if debug:
      print("Bas (Purple)= curv: ", DotProdPtr, " ; jugeBas: ", jugeBas)

    if (( DotProdPtr < MostCurvy) and (jugeBas > maxJuge)):
      MostCurvy =  DotProdPtr
      MostCurvyIndex = ind_bas
      if (debug):
        print("bas wins")

    if debug:
      # Droite
      pt1 = bodyContour[int(ind_droite)][0]
      cv2.circle(dst, (pt1[0],pt1[1]), 1, (255, 0, 0), -1)
      # Gauche
      pt1 = bodyContour[int(ind_gauche)][0]
      cv2.circle(dst, (pt1[0],pt1[1]), 1, (0, 255, 0), -1)
      # Haut
      pt1 = bodyContour[int(ind_haut)][0]
      cv2.circle(dst, (pt1[0],pt1[1]), 1, (0, 0, 255), -1)
      # Bas
      pt1 = bodyContour[int(ind_bas)][0]
      cv2.circle(dst, (pt1[0],pt1[1]), 1, (255, 255, 0), -1)
      if False: # The following can sometimes be useful when debugging
        for i in range(0, len(rotatedContour)):
          pt1 = rotatedContour[int(i)][0]
          cv2.circle(dst, (pt1[0],pt1[1]), 1, (0, 0, 0), -1)
      if self._hyperparameters["debugTrackingPtExtremeLargeVerticals"]:
        dst = dst[pt1[1]-200:len(dst), :]
      # Plotting points
      self._debugFrame(dst, title='Frame')

    # allPossibilities = [[ind_droite,DotProds[ind_droite],jugeDroite], [ind_gauche,DotProds[ind_gauche],jugeGauche], [ind_haut,DotProds[ind_haut],jugeHaut], [ind_bas,DotProds[ind_bas],jugeBas]]

    return [MostCurvyIndex, distance2]


class TailTrackingExtremityDetectMixin(_FindTailExtremityMixin):
  def __checkIfMidlineIsInBlob(self, headX, headY, pointAlongTheTail, bodyContour, dst, size, distance2, debugAdv):
    tail = self._getMidline(headX, headY, pointAlongTheTail, bodyContour, dst, size, distance2, debugAdv)

    tail2 = tail[0]
    n = len(tail2)
    allMidlinePointsInsideBlob = True
    for j in range(0, n):
      dist = cv2.pointPolygonTest(bodyContour,(tail2[j][0],tail2[j][1]),False)
      if dist < 0:
        allMidlinePointsInsideBlob = False

    tailLength = 0
    if allMidlinePointsInsideBlob:
      for j in range(0, n-1):
        tailLength = tailLength + math.sqrt( pow(tail2[j,0]-tail2[j+1,0], 2) + pow(tail2[j,1]-tail2[j+1,1], 2) )

    return [allMidlinePointsInsideBlob, tailLength]

  def __findTheTwoSides(self, headPosition, bodyContour, dst):
    if self._hyperparameters["detectMouthInsteadOfHeadTwoSides"] == 1:

      lenX = len(dst[0])
      lenY = len(dst)
      originalShape = np.zeros((lenY, lenX))
      originalShape[:, :] = 0
      originalShape = originalShape.astype(np.uint8)
      cv2.fillPoly(originalShape, pts =[bodyContour], color=(255))

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
      nbWhitePixelsMax = 75
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

      maxDist = -1
      for i in range(0, nTries):
        angleOption = bestAngleAfterFirstStep - (math.pi / 5) + i * ((2 * (math.pi / 5)) / nTries)

        startPoint = (int(headPosition[0]), int(headPosition[1]))
        endPoint   = (int(headPosition[0] + 100000 * math.cos(angleOption)), int(headPosition[1] + 100000 * math.sin(angleOption)))
        testImage  = originalShape.copy()

        # applying dilation with the iterationsForErodeImageForHeadingCalculation value found
        testImage = cv2.erode(testImage, kernel, iterations = iterationsForErodeImageForHeadingCalculation)
        testImage  = cv2.line(testImage, startPoint, endPoint, (0), 1)
        nbWhitePixels = cv2.countNonZero(testImage)
        if nbWhitePixels < minWhitePixel:
          minWhitePixel = nbWhitePixels
          bestAngle     = angleOption

      # Finding the 'mouth' of the fish
      unitVector = np.array([math.cos(bestAngle + math.pi), math.sin(bestAngle + math.pi)])
      factor     = 1
      headPos    = np.array(headPosition)
      testBorder = headPos + factor * unitVector
      testBorder = testBorder.astype(int)
      while (cv2.pointPolygonTest(bodyContour, (testBorder[0], testBorder[1]), True) > 0) and (factor < 100) and (testBorder[0] >= 0) and (testBorder[1] >= 0) and (testBorder[0] < len(dst[0])) and (testBorder[1] < len(dst)):
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

      res = [indMin1, indMin2, bestAngle + math.pi]

    else:

      res = np.zeros(2)

      x = headPosition[0]
      y = headPosition[1]

      minDist = 1000000000000
      indMin  = 0
      for i in range(0, len(bodyContour)):
        Pt   = bodyContour[i][0]
        dist = math.sqrt((Pt[0] - x)**2 + (Pt[1] - y)**2)
        if (dist < minDist):
          minDist = dist
          indMin  = i

      res[0] = indMin
      PtClosest = bodyContour[indMin][0]
      headPos   = np.array(headPosition)

      unitVector = np.array([x - PtClosest[0], y - PtClosest[1]])
      unitVectorLength = math.sqrt(unitVector[0]**2 + unitVector[1]**2)
      unitVector[0] = unitVector[0] / unitVectorLength
      unitVector[1] = unitVector[1] / unitVectorLength

      factor = 1
      testBorder = headPos + factor * unitVector
      testBorder = testBorder.astype(int)
      while (cv2.pointPolygonTest(bodyContour, (testBorder[0], testBorder[1]), True) > 0) and (factor < 100) and (testBorder[0] >= 0) and (testBorder[1] >= 0) and (testBorder[0] < len(dst[0])) and (testBorder[1] < len(dst)):
        factor = factor + 1
        testBorder = headPos + factor * unitVector

      xOtherBorder = testBorder[0]
      yOtherBorder = testBorder[1]

      minDist = 1000000000000
      indMin2  = 0
      for i in range(0, len(bodyContour)):
        Pt   = bodyContour[i][0]
        dist = math.sqrt((Pt[0] - xOtherBorder)**2 + (Pt[1] - yOtherBorder)**2)
        if (dist < minDist):
          minDist = dist
          indMin2  = i

      res[1] = indMin2

    if False:
      cv2.circle(dst, (pt1[0],pt1[1]), 1, (0, 0, 255), -1)
      cv2.circle(dst, (pt2[0],pt2[1]), 1, (0, 0, 255), -1)
      self._debugFrame(dst, title='Frame')

    return res

  def __findBodyContour(self, headPosition, thresh1, initialCurFrame, back, wellNumber=-1, frameNumber=-1):
    if self._hyperparameters["saveBodyMask"] and self._hyperparameters["bodyMask_addWhitePoints"]:
      [img, thresh1] = drawWhitePointsOnInitialImages(initialCurFrame, back, self._hyperparameters)

    thresh1[:,0] = 255
    thresh1[0,:] = 255
    thresh1[:, len(thresh1[0])-1] = 255
    thresh1[len(thresh1)-1, :]    = 255

    x = headPosition[0]
    y = headPosition[1]
    cx = 0
    cy = 0
    takeTheHeadClosestToTheCenter = 1
    bodyContour = 0

    if self._hyperparameters["findContourPrecision"] == "CHAIN_APPROX_SIMPLE":
      contourPrecision = cv2.CHAIN_APPROX_SIMPLE
    else: # self._hyperparameters["findContourPrecision"] == "CHAIN_APPROX_NONE"
      contourPrecision = cv2.CHAIN_APPROX_NONE

    if self._hyperparameters["recalculateForegroundImageBasedOnBodyArea"]:

      minPixel2nbBlackPixels = {}
      countTries = 0
      nbBlackPixels = 0
      nbBlackPixelsMax = int(self._hyperparameters["adjustMinPixelDiffForBackExtract_nbBlackPixelsMax"] / self._hyperparameters["nbAnimalsPerWell"])
      minPixelDiffForBackExtract = int(self._hyperparameters["minPixelDiffForBackExtract"])
      if "minPixelDiffForBackExtractBody" in self._hyperparameters:
        minPixelDiffForBackExtract = self._hyperparameters["minPixelDiffForBackExtractBody"]

      previousNbBlackPixels = []
      while (minPixelDiffForBackExtract > 0) and (countTries < 30) and not(minPixelDiffForBackExtract in minPixel2nbBlackPixels):
        curFrame = initialCurFrame.copy()
        putToWhite = ( curFrame.astype('int32') >= (back.astype('int32') - minPixelDiffForBackExtract) )
        curFrame[putToWhite] = 255
        ret, thresh1_b = cv2.threshold(curFrame, self._hyperparameters["thresholdForBlobImg"], 255, cv2.THRESH_BINARY)
        thresh1_b = 255 - thresh1_b
        bodyContour = 0
        contours, hierarchy = cv2.findContours(thresh1_b, cv2.RETR_TREE, contourPrecision)
        for contour in contours:
          dist = cv2.pointPolygonTest(contour, (x, y), True)
          if dist >= 0:
            M = cv2.moments(contour)
            if M['m00']:
              cx = int(M['m10']/M['m00'])
              cy = int(M['m01']/M['m00'])
              bodyContour = contour
            else:
              cx = 0
              cy = 0
        if not(type(bodyContour) == int):
          nbBlackPixels = cv2.contourArea(bodyContour)
        else:
          nbBlackPixels = -100000000

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
      putToWhite = (curFrame.astype('int32') >= (back.astype('int32') - minPixelDiffForBackExtract) )
      curFrame[putToWhite] = 255

      ret, thresh1 = cv2.threshold(curFrame, self._hyperparameters["thresholdForBlobImg"], 255, cv2.THRESH_BINARY)
      thresh1 = 255 - thresh1

      self._hyperparameters["minPixelDiffForBackExtractBody"] = minPixelDiffForBackExtract

    contours, hierarchy = cv2.findContours(thresh1, cv2.RETR_TREE, contourPrecision)
    for contour in contours:
      area = cv2.contourArea(contour)
      if (area >= self._hyperparameters["minAreaBody"]) and (area <= self._hyperparameters["maxAreaBody"]):
        dist = cv2.pointPolygonTest(contour, (x, y), True)
        if dist >= 0 or self._hyperparameters["saveBodyMask"]:
          M = cv2.moments(contour)
          if M['m00']:
            cx = int(M['m10']/M['m00'])
            cy = int(M['m01']/M['m00'])
            bodyContour = contour
          else:
            cx = 0
            cy = 0

    if type(bodyContour) != int:
      if cv2.contourArea(bodyContour) >= self._hyperparameters["maxAreaBody"]:
        bodyContour = 0

    if self._hyperparameters["saveBodyMask"]:
      saveImagesAndData(self._hyperparameters, bodyContour, initialCurFrame, wellNumber, frameNumber)

    return bodyContour

  @staticmethod
  def _rotate(boundary, aaa, bbb, angle):
    gauche = 0
    haut   = 0

    x1 = aaa + 100*math.cos(angle)
    y1 = bbb + 100*math.sin(angle)
    x2 = aaa + 100*math.cos(angle + math.pi)
    y2 = bbb + 100*math.sin(angle + math.pi)
    x = 0
    y = 0
    r = 0
    Yoo = [x1 + gauche,y1 + haut]
    Yaa = [x2 + gauche,y2 + haut]

    dist1 = 0
    min_dist1 = 1000000
    dist2 = 0
    min_dist2 = 1000000
    theta = 0
    alpha = 0
    alpha_aux = 0
    final_angle = 0
    for i in range(0, len(boundary)):
      Pt = boundary[i][0]
      dist1 = (Pt[0] - x1)*(Pt[0] - x1) + (Pt[1] - y1)*(Pt[1] - y1)
      dist2 = (Pt[0] - x2)*(Pt[0] - x2) + (Pt[1] - y2)*(Pt[1] - y2)
      if (dist1<min_dist1):
        min_dist1 = dist1
      if (dist2<min_dist2):
        min_dist2 = dist2

    if (min_dist1<min_dist2):
      theta = angle
    else:
      theta = angle + math.pi

    theta = (math.pi/2) - theta

    for i in range(0, len(boundary)):
      Pt = boundary[i][0]
      x = Pt[0]
      y = Pt[1]
      x = x - aaa
      y = y - bbb
      r = math.sqrt(x*x + y*y)
      if (x>0):
        alpha = math.atan(y/x)
      if (x<0):
        x = -x
        alpha_aux = math.atan(y/x)
        alpha = math.pi - alpha_aux
      if (x == 0):
        if (y>0):
          alpha = math.pi/2
        else:
          alpha = -math.pi/2

      final_angle = theta + alpha
      x = r*math.cos(final_angle)
      y = r*math.sin(final_angle)
      Pt[0] = x + aaa
      Pt[1] = y + bbb + 200

      boundary[i] = Pt

    return boundary

  @staticmethod
  def __resampleSeqConstPtsPerArcLength(OrigBound, numTailPoints):
    n = len(OrigBound)
    distOrg = np.zeros(n)
    xOrg    = np.zeros(n)
    yOrg    = np.zeros(n)

    totDist = 0
    distOrg[0] = totDist
    xOrg[0] = OrigBound[0][0][0]
    yOrg[0] = OrigBound[0][0][1]

    for i in range(1, n):
      diff       = math.sqrt((OrigBound[i-1][0][0]-OrigBound[i][0][0])**2 + (OrigBound[i-1][0][1]-OrigBound[i][0][1])**2)
      totDist    = totDist + diff
      distOrg[i] = totDist

    uniDist = np.zeros(numTailPoints)
    uniX    = np.zeros(numTailPoints)
    uniY    = np.zeros(numTailPoints)

    for i in range(0, numTailPoints):
      uniDist[i] = totDist * (i/(numTailPoints-1))

    for i in range(1, n):
      xOrg[i] = OrigBound[i][0][0]
      yOrg[i] = OrigBound[i][0][1]

    uniX = np.interp(uniDist, distOrg, xOrg)
    uniY = np.interp(uniDist, distOrg, yOrg)

    output = np.zeros((numTailPoints, 2))
    for i in range(0, numTailPoints):
      output[i][0] = uniX[i]
      output[i][1] = uniY[i]

    return output

  @staticmethod
  def __fillTailRanges(tailRange1,tailRange2,fillSecond,i,MostCurvyIndex):
    if (i == MostCurvyIndex):
      fillSecond = 1
    if fillSecond == 0:
      tailRange1.append(i)
    else:
      tailRange2.append(i)
    return [tailRange1,tailRange2,fillSecond]

  def _getMidline(self, bord1, bord2, MostCurvyIndex, boundary, dst, nbTailPoints, distance2, debug):
    output = np.zeros((1, 0, 2))

    minTailSize = 20
    maxTailSize = 60
    trackingPointSizeDisplay = 1

    OrigBoundA = []
    OrigBoundB = []

    if (bord2 < bord1):
      temp  = bord2
      bord2 = bord1
      bord1 = temp

    max1 = distance2[bord2] - distance2[bord1]
    max2 = (distance2[bord1] - distance2[0])  + (distance2[len(boundary)] - distance2[bord2])

    tailRangeA = []
    tailRangeB = []
    fillSecond = 0
    if (max1 > max2):
      for i in range(bord1, bord2):
        [tailRangeA,tailRangeB,fillSecond] = self.__fillTailRanges(tailRangeA,tailRangeB,fillSecond,i,MostCurvyIndex)
    else:
      for i in range(bord2, len(boundary)):
        [tailRangeA,tailRangeB,fillSecond] = self.__fillTailRanges(tailRangeA,tailRangeB,fillSecond,i,MostCurvyIndex)
      for i in range(0, bord1):
        [tailRangeA,tailRangeB,fillSecond] = self.__fillTailRanges(tailRangeA,tailRangeB,fillSecond,i,MostCurvyIndex)

    OrigBoundA = boundary[tailRangeA]
    OrigBoundB = boundary[tailRangeB]

    if ((bord1!=bord2) and (bord1!=MostCurvyIndex) and (bord2!=MostCurvyIndex) and not((bord1==1) and (bord2==1) and (MostCurvyIndex==1)) and (len(OrigBoundA)>1) and (len(OrigBoundB)>1)):

      if False:
        for pt in OrigBoundA:
          cv2.circle(dst, (pt[0][0], pt[0][1]), 1, (0, 255, 0), -1)
        for pt in OrigBoundB:
          cv2.circle(dst, (pt[0][0], pt[0][1]), 1, (255, 0, 0), -1)
        self._debugFrame(dst, title='dst')

      NBoundA = self.__resampleSeqConstPtsPerArcLength(OrigBoundA, nbTailPoints)
      NBoundB = self.__resampleSeqConstPtsPerArcLength(OrigBoundB, nbTailPoints)

      # calculates length of the tail
      TotalDist = 0
      for i in range(1, nbTailPoints):
        Pt  = NBoundB[i % nbTailPoints]
        Pt2 = NBoundA[nbTailPoints - i]
        x = (Pt[0]+Pt2[0]) / 2
        y = (Pt[1]+Pt2[1]) / 2
        if i > 1:
          TotalDist = TotalDist + math.sqrt((x-xAvant)*(x-xAvant)+(y-yAvant)*(y-yAvant))
        xAvant = x
        yAvant = y

      if ((TotalDist<self._hyperparameters["minTailSize"]) or (TotalDist>self._hyperparameters["maxTailSize"])):

        if (debug):
          print("innapropriate tail size! TailDist: ", TotalDist, " ; but minTailSize is ", minTailSize, " and maxTailSize is ", maxTailSize)

      else:

        Tail = boundary[MostCurvyIndex][0]

        point = np.array([Tail[0], Tail[1]])
        output = np.insert(output, 0, point, axis=1)

        for i in range(1, nbTailPoints):
          Pt  = NBoundB[i % nbTailPoints]
          Pt2 = NBoundA[nbTailPoints - i]
          point = np.array([(Pt[0]+Pt2[0])/2, (Pt[1]+Pt2[1])/2])
          output = np.insert(output, 0, point, axis=1)

        i = nbTailPoints-2
        if i >= 1:
          Pt =  NBoundB[i % nbTailPoints]
          Pt2 = NBoundA[nbTailPoints-i]
          ClosestPoint = [ (Pt[0]+Pt2[0])/2 , (Pt[1]+Pt2[1])/2 ]
        else:
          ClosestPoint = [-200, -200]

    else:

      # THIS SHOULD BE IMPROVED IN THE FUTURE:
      # WE SHOULD CHECK FOR TAIL LENGHT
      # ALSO WE SHOULD DO SOMETHING BETTER THAN JUST PUTTING THE TAIL TIP FOR EACH OF THE TEN POINTS !!!
      Tail = boundary[MostCurvyIndex][0]
      point = np.array([Tail[0], Tail[1]])
      for i in range(0, nbTailPoints):
        output = np.insert(output, 0, point, axis=1)

    return output

  def _tailTrackingExtremityDetect(self, headPosition, i, thresh1, frame, debugAdv, heading, initialCurFrame, back, wellNumber=-1):
    newHeading = -1

    dst = frame.copy()
    if type(dst[0][0]) == np.uint8:
      dst = cv2.cvtColor(dst, cv2.COLOR_GRAY2RGB)
    firstFrame = self._hyperparameters["firstFrame"]
    lastFrame = self._hyperparameters["lastFrame"]

    if self._hyperparameters["debugTrackingThreshImg"]:
      if self._hyperparameters["debugTrackingPtExtremeLargeVerticals"]:
        self._debugFrame(thresh1[int(headPosition[1])-200:len(thresh1), :], title='debugTrackingThreshImg')
      else:
        self._debugFrame(thresh1, title='debugTrackingThreshImg')

    # Finding blob corresponding to the body of the fish
    bodyContour = self.__findBodyContour(headPosition, thresh1, initialCurFrame, back, wellNumber, i)
    if type(bodyContour) != int:
      # Finding the two sides of the fish
      res = self.__findTheTwoSides(headPosition, bodyContour, dst)
      if len(res) == 3:
        heading = res[2]
        newHeading = res[2]
      # Finding tail extremity
      rotatedContour = bodyContour.copy()
      rotatedContour = self._rotate(rotatedContour,int(headPosition[0]),int(headPosition[1]),heading)
      [MostCurvyIndex, distance2] = self._findTailExtremete(rotatedContour, bodyContour, headPosition[0], int(res[0]), int(res[1]), debugAdv, dst, self._hyperparameters["tailExtremityMaxJugeDecreaseCoeff"])
      if debugAdv:
        if True:
          # Head Center
          cv2.circle(dst, (int(headPosition[0]),int(headPosition[1])), 3, (255, 255, 0), -1)
          # Tail basis 1
          pt1 = bodyContour[int(res[0])][0]
          cv2.circle(dst, (pt1[0],pt1[1]), 3, (255, 0, 0), -1)
          # Tail basis 2
          pt1 = bodyContour[int(res[1])][0]
          cv2.circle(dst, (pt1[0],pt1[1]), 3, (180, 0, 0), -1)
          # Tail extremity
          pt1 = bodyContour[int(MostCurvyIndex)][0]
          cv2.circle(dst, (pt1[0],pt1[1]), 3, (0, 0, 255), -1)
        else:
          for pt in bodyContour:
            cv2.circle(dst, (pt[0][0], pt[0][1]), 1, (0, 255, 0), -1)
          cv2.circle(dst, (int(headPosition[0]),int(headPosition[1])), 1, (0, 0, 255), -1)
        #
        if self._hyperparameters["debugTrackingPtExtremeLargeVerticals"]:
          dst = dst[int(headPosition[1])-200:len(dst), :]
        # Plotting points
        self._debugFrame(dst, title='Frame')

      # Getting Midline
      if self._hyperparameters["detectMouthInsteadOfHeadTwoSides"] == 0:
        tail = self._getMidline(int(res[0]), int(res[1]), int(MostCurvyIndex), bodyContour, dst, self._nbTailPoints-1, distance2, debugAdv)
      else:
        tail = self._getMidline(int(res[0]), int(res[1]), int(MostCurvyIndex), bodyContour, dst, self._nbTailPoints, distance2, debugAdv)
        tail = np.array([tail[0][1:len(tail[0])]])

      if False:
        maxDistContourToTail = -1
        for contourPt in bodyContour:
          contourPtX = contourPt[0][0]
          contourPtY = contourPt[0][1]
          minDistContourPointToTail = 1000000000000
          for tailPt in np.append(tail[0], np.array([headPosition]), axis=0):
            tailPtX = tailPt[0]
            tailPtY = tailPt[1]
            dist = math.sqrt((tailPtX - contourPtX)**2 + (tailPtY - contourPtY)**2)
            if dist < minDistContourPointToTail:
              minDistContourPointToTail = dist
          if minDistContourPointToTail > maxDistContourToTail:
            maxDistContourToTail = minDistContourPointToTail
        print("maxDistContourToTail:", maxDistContourToTail, "; tailLength:", self._hyperparameters["minTailSize"]*10)

      if False:
        for pt in bodyContour:
          cv2.circle(dst, (pt[0][0], pt[0][1]), 3, (0, 0, 255), -1)
        self._debugFrame(dst, title='Frame')

      # Optimizing midline if necessary
      midlineIsInBlobTrackingOptimization = self._hyperparameters["midlineIsInBlobTrackingOptimization"]
      if midlineIsInBlobTrackingOptimization:
        [allInside, tailLength] = self.__checkIfMidlineIsInBlob(int(res[0]), int(res[1]), int(MostCurvyIndex), bodyContour, dst, self._nbTailPoints-1, distance2, debugAdv)
        if allInside == False:
          n = len(bodyContour)
          maxTailLength = -1
          for j in range(0, n):
            [allInside, tailLength] = self.__checkIfMidlineIsInBlob(int(res[0]), int(res[1]), j, bodyContour, dst, self._nbTailPoints-1, distance2, debugAdv)
            if allInside:
              if tailLength > maxTailLength:
                MostCurvyIndex = j
                maxTailLength = tailLength
          tail = self._getMidline(int(res[0]), int(res[1]), int(MostCurvyIndex), bodyContour, dst, self._nbTailPoints-1, distance2, debugAdv)
      # Applying snake on tail
      applySnake = False
      if applySnake:
        tail2 = tail[0]
        n = len(tail2)
        # tail2[n-1][0] = tail2[n-1][0] + (tail2[n-1][0] - tail2[n-2][0]) * 6
        # tail2[n-1][1] = tail2[n-1][1] + (tail2[n-1][1] - tail2[n-2][1]) * 6
        # print(type(tail))
        # r = np.linspace(tail2[0][0], tail2[0][0] + (tail2[1][0]-tail2[0][0]) * 15, 9)
        # c = np.linspace(tail2[0][1], tail2[0][1] + (tail2[1][1]-tail2[0][1]) * 15, 9)
        # tail2 = np.array([r, c]).T
        # r = np.linspace(tail2[0][0], tail2[n-1][0], 9)
        # c = np.linspace(tail2[0][1], tail2[n-1][1], 9)
        # tail2 = np.array([r, c]).T
        from skimage.color import rgb2gray
        from skimage.filters import gaussian
        from skimage.segmentation import active_contour
        snake = active_contour(gaussian(frame, 3), tail2, w_edge=-1000, bc="fixed")
        # snake = active_contour(gaussian(frame, 3), tail2, w_edge=0, bc="fixed-free")
        print(snake)
        # snake = tail2
        tail[0] = snake

    else:

      tail = np.zeros((1, 0, 2))
      point = np.array([0, 0])
      for i in range(0, self._nbTailPoints):
        tail = np.insert(tail, 0, point, axis=1)
      # if self._hyperparameters["detectMouthInsteadOfHeadTwoSides"] != 0:
        # tail = np.insert(tail, 0, point, axis=1)

    # Inserting head position, smoothing tail and creating output
    # if self._hyperparameters["detectMouthInsteadOfHeadTwoSides"] == 0:
      # tail = np.insert(tail, 0, headPosition, axis=1)
    tail = np.insert(tail, 0, headPosition, axis=1)

    # if self._nbTailPoints != len(tail[0]):
      # print("small problem 1 in tailTrackingExtremityDetect")

    # output = np.zeros((1, len(tail[0]), 2))
    output = np.zeros((1, self._nbTailPoints, 2))

    for idx, x in enumerate(tail[0]):
      if idx < self._nbTailPoints:
        output[0][idx][0] = x[0]
        output[0][idx][1] = x[1]
      # else:
        # print("small problem 2 in tailTrackingExtremityDetect")

    return [output, newHeading]


class TailTrackingMixin(_HeadEmbeddedTailTrackingMixin, _CenterOfMassTailTrackingMixin, _HeadEmbeddedTailTrackingTeresaNicolsonMixin, _TailTrackingBlobDescentMixin, TailTrackingExtremityDetectMixin):
  def _tailTracking(self, animalId, i, frame, thresh1, threshForBlackFrames, thetaDiffAccept, trackingHeadTailAllAnimals, trackingHeadingAllAnimals, lastFirstTheta, maxDepth, tailTip, initialCurFrame, back, wellNumber=-1, xmin=0, ymin=0):
    headPosition = [trackingHeadTailAllAnimals[animalId, i-self._firstFrame][0][0]-xmin, trackingHeadTailAllAnimals[animalId, i-self._firstFrame][0][1]-ymin]
    heading      = trackingHeadingAllAnimals[animalId, i-self._firstFrame]

    if (self._hyperparameters["headEmbeded"] == 1):
      # through the "head embeded" method, either through "segment descent" or "center of mass descent"

      if self._hyperparameters["headEmbededTeresaNicolson"] == 1:
        oppHeading = (heading + math.pi) % (2 * math.pi)
        trackingHeadTailAllAnimalsI = headEmbededTailTrackingTeresaNicolson(headPosition, frame, maxDepth, tailTip, threshForBlackFrames)
      else:
        oppHeading = (heading + math.pi) % (2 * math.pi) # INSERTED FOR THE REFACTORING
        if self._hyperparameters["centerOfMassTailTracking"] == 0:
          trackingHeadTailAllAnimalsI = self._headEmbededTailTracking(headPosition, i, frame, maxDepth, tailTip)
        else:
          trackingHeadTailAllAnimalsI = self._centerOfMassTailTracking(headPosition, frame, maxDepth)

      if len(trackingHeadTailAllAnimalsI[0]) == len(trackingHeadTailAllAnimals[animalId, i-self._firstFrame]):
        trackingHeadTailAllAnimals[animalId, i-self._firstFrame] = trackingHeadTailAllAnimalsI

    else:
      if self._hyperparameters["freeSwimmingTailTrackingMethod"] == "tailExtremityDetect":
        # through the tail extremity descent method (original C++ method)
        [trackingHeadTailAllAnimalsI, newHeading] = self._tailTrackingExtremityDetect(headPosition, i, thresh1, frame, self._hyperparameters["debugTrackingPtExtreme"], heading, initialCurFrame, back, wellNumber)
        trackingHeadTailAllAnimals[animalId, i-self._firstFrame] = trackingHeadTailAllAnimalsI
        if newHeading != -1:
          trackingHeadingAllAnimals[animalId, i-self._firstFrame] = newHeading
      elif self._hyperparameters["freeSwimmingTailTrackingMethod"] == "blobDescent":
        # through the "blob descent" method
        trackingHeadTailAllAnimals[animalId, i-self._firstFrame] = self._tailTrackingBlobDescent(headPosition, i, thresh1, frame, lastFirstTheta, self._hyperparameters["debugTrackingPtExtreme"], thetaDiffAccept)
      else: # self._hyperparameters["freeSwimmingTailTrackingMethod"] == "none"
        # only tracking the head, not the tail
        trackingHeadTailAllAnimals[animalId, i-self._firstFrame][0][0] = headPosition[0]
        trackingHeadTailAllAnimals[animalId, i-self._firstFrame][0][1] = headPosition[1]
