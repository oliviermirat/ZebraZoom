import math

import cv2
import numpy as np
from numpy import linspace
from scipy.interpolate import interp1d
from scipy.interpolate import splprep, splev
from scipy.optimize import curve_fit

from ._tailTrackingBase import TailTrackingBase

applyDilateErode  = True
printDebbbbug     = False
maxThresholdMinus = 20
#

class HeadEmbeddedTailTrackingForImageMixin(TailTrackingBase):

  def __smoothTail(self, points, nbTailPoints, smoothingFactor):
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

  def _headEmbededTailTrackingForImage(self, headPosition, i, frame, maxDepth, tailTip, trackingHeadingAllAnimals=[]):
    steps   = self._hyperparameters["step"]
    nbList  = 10 if self._hyperparameters["nbList"] == -1 else self._hyperparameters["nbList"]

    x = headPosition[0]
    y = headPosition[1]

    initialImage = frame.copy()
    
    if printDebbbbug:
      self._debugFrame(frame, title='Test1')
    
    back = frame.copy()
    back[:, :] = np.median(back[:3, :], axis=0)
    putToWhite = ( frame.astype('int32') >= (back.astype('int32') - 0) )
    frame[putToWhite] = 255
    
    ret, threshEyes = cv2.threshold(frame.copy(), 25, 255, cv2.THRESH_BINARY)
    
    
    ret, frame = cv2.threshold(frame.copy(), 254, 255, cv2.THRESH_BINARY)
    
    if applyDilateErode:
      erodeDilateSize = 25
      frame = cv2.erode(frame, np.ones((erodeDilateSize, erodeDilateSize), np.uint8), iterations=1)
      frame = cv2.dilate(frame, np.ones((erodeDilateSize, erodeDilateSize), np.uint8), iterations=1)
    
    # homogeneous = frame.copy()
    # homogeneous[:, :] = np.median(frame) - maxThresholdMinus #maxThreshold
    
    # frame = np.maximum(frame, homogeneous)
    
    if printDebbbbug:
      self._debugFrame(frame, title='Test2')

    gaussian_blur = self._hyperparameters["headEmbededParamGaussianBlur"]

    frame = cv2.GaussianBlur(frame, (gaussian_blur, gaussian_blur), 0)
    
    if printDebbbbug:
      self._debugFrame(frame, title='Test3')

    if ("initialTailForMaxDepthCalculNotStraight" in self._hyperparameters) and self._hyperparameters["initialTailForMaxDepthCalculNotStraight"]:
      angle = self._hyperparameters["headEmbededParamInitialAngle"]
    else:
      angle = self._calculateAngle(x, y, tailTip[0], tailTip[1])

    points = np.zeros((2, 0))

    (points, lastFirstTheta2) = self.__findNextPoints(0,x,y,frame,points,angle,maxDepth,steps,nbList,initialImage,self._hyperparameters["debugHeadEmbededFindNextPoints"])
    points = np.insert(points, 0, headPosition, axis=1)
    # points = np.insert(points, 0, [cX, cY], axis=1)

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
    
    
    for idx, x in enumerate(points[0]):
      y = points[1][idx]
      cv2.circle(threshEyes, (int(x), int(y)), 50, (255, 255, 255), -1)
    if printDebbbbug:
      self._debugFrame(threshEyes, title='threshEyes1')
    threshEyes[0, :] = 255
    threshEyes[:, 0] = 255
    threshEyes[len(threshEyes)-1, :] = 255
    threshEyes[:, len(threshEyes[0])-1] = 255
    contours, hierarchy = cv2.findContours(threshEyes,cv2.RETR_TREE,cv2.CHAIN_APPROX_SIMPLE)
    areas = np.array([cv2.contourArea(contour) for contour in contours])
    max1 = 0
    max2 = 0
    max1_index = -1
    max2_index = -1
    for index, value in enumerate(areas):
      if value >= 1000000:
        continue
      if value > max1:
        max2 = max1
        max2_index = max1_index
        max1 = value
        max1_index = index
      elif value > max2:
        max2 = value
        max2_index = index
    M1 = cv2.moments(contours[max1_index])
    if M1["m00"] != 0:
      cX1 = int(M1["m10"] / M1["m00"])
      cY1 = int(M1["m01"] / M1["m00"])
    else:
      cX1, cY1 = 0, 0
    M2 = cv2.moments(contours[max2_index])
    if M2["m00"] != 0:
      cX2 = int(M2["m10"] / M2["m00"])
      cY2 = int(M2["m01"] / M2["m00"])
    else:
      cX2, cY2 = 0, 0
    cX = (cX1 + cX2) / 2
    cY = (cY1 + cY2) / 2
    heading = self._calculateAngle(headPosition[0], headPosition[1], cX, cY)
    threshEyes = cv2.cvtColor(threshEyes, cv2.COLOR_GRAY2RGB)
    cv2.circle(threshEyes, (int(cX), int(cY)), 5, (0, 255, 0), -1)
    cv2.circle(threshEyes, (int(headPosition[0]), int(headPosition[1])), 5, (0, 255, 0), -1)
    if printDebbbbug:
      self._debugFrame(threshEyes, title='threshEyes')
    
    return output, heading

  def _headEmbededTailTrackFindMaxDepthForImage(self, frame):
    if not(("initialTailForMaxDepthCalculNotStraight" in self._hyperparameters) and self._hyperparameters["initialTailForMaxDepthCalculNotStraight"]):
      return math.sqrt((self._headPositionFirstFrame[0] - self._tailTipFirstFrame[0])**2 + (self._headPositionFirstFrame[1] - self._tailTipFirstFrame[1])**2)

    headEmbededParamTailDescentPixThreshStopInit = self._hyperparameters["headEmbededParamTailDescentPixThreshStop"]
    self._hyperparameters["headEmbededParamTailDescentPixThreshStop"] = 256

    x = self._headPositionFirstFrame[0]
    y = self._headPositionFirstFrame[1]

    steps   = self._hyperparameters["step"]
    nbList  = 10

    initialImage = frame.copy()
    
    #####
    # frame = cv2.GaussianBlur(frame, (5, 5), 0)
    # frame = cv2.Canny(frame, threshold1=50, threshold2=50) #threshold1=100, threshold2=200)
    #####
    
    back = frame.copy()
    back[:, :] = np.median(back[:3, :], axis=0)
    putToWhite = ( frame.astype('int32') >= (back.astype('int32') - 0) )
    frame[putToWhite] = 255
    ret, frame = cv2.threshold(frame.copy(), 254, 255, cv2.THRESH_BINARY)
    
    if applyDilateErode:
      erodeDilateSize = 25
      frame = cv2.erode(frame, np.ones((erodeDilateSize, erodeDilateSize), np.uint8), iterations=1)
      frame = cv2.dilate(frame, np.ones((erodeDilateSize, erodeDilateSize), np.uint8), iterations=1)
    
    #####
    
    if printDebbbbug:
      self._debugFrame(frame, title='Test1')
    
    # homogeneous = frame.copy()
    # homogeneous[:, :] = np.median(frame) - maxThresholdMinus #maxThreshold
    
    # frame = np.maximum(frame, homogeneous)
    
    if printDebbbbug:
      self._debugFrame(frame, title='Test2')
    
    gaussian_blur = self._hyperparameters["headEmbededParamGaussianBlur"]

    frame = cv2.GaussianBlur(frame, (gaussian_blur, gaussian_blur), 0)

    angle = self._calculateAngle(x, y, self._tailTipFirstFrame[0], self._tailTipFirstFrame[1])

    points = np.zeros((2, 0))
    
    if printDebbbbug:
      self._debugFrame(frame, title='Test3')

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
