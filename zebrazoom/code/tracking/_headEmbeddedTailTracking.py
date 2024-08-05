import math

import cv2
import numpy as np
from numpy import linspace
from scipy.interpolate import interp1d
from scipy.interpolate import splprep, splev
from scipy.optimize import curve_fit

from ._tailTrackingBase import TailTrackingBase


class HeadEmbeddedTailTrackingMixin(TailTrackingBase):
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

  def __smoothBasedOnCurvature(self, points, polynomialDegree):
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
      points = self.__retrackIfWeirdInitialTracking(points, headPosition, tailTip, x, y, frame, angle, maxDepth, nbList, initialImage, i)

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
