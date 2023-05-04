import math

import cv2
import numpy as np
from numpy import linspace
from scipy.interpolate import UnivariateSpline

from ._tailTrackingBase import TailTrackingBase


class CenterOfMassTailTrackingMixin(TailTrackingBase):
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
