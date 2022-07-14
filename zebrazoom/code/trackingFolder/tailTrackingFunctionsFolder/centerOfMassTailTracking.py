import numpy as np
import cv2
from zebrazoom.code.trackingFolder.trackingFunctions import calculateAngle
from zebrazoom.code.trackingFolder.trackingFunctions import distBetweenThetas
from zebrazoom.code.trackingFolder.trackingFunctions import assignValueIfBetweenRange
import math
from scipy.interpolate import UnivariateSpline
from numpy import linspace
import os.path
import csv
import pdb


def smoothTail(points, nbTailPoints):
  
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

def appendPoint(x, y, points):
  curPoint = np.zeros((2, 1))
  curPoint[0] = x;
  curPoint[1] = y;
  points = np.append(points, curPoint, axis=1)
  return points

def findNextPoints(depth,x,y,frame,points,angle,maxDepth,hyperparameters,debug):
  
  step     = hyperparameters["centerOfMassParamStep"]
  segStep  = hyperparameters["centerOfMassParamSegStep"]
  halfDiam = hyperparameters["centerOfMassParamHalfDiam"]
  
  if debug:
    frameDisplay = frame.copy()
    frameDisplay = cv2.cvtColor(frameDisplay, cv2.COLOR_GRAY2RGB)
    
  lenX = len(frame[0]) - 1
  lenY = len(frame) - 1

  thetaDiffAccept = 0.4
  pixTotMax = 1000000
  maxTheta  = angle

  xNew = assignValueIfBetweenRange(int(x + step * (math.cos(angle))), 0, lenX)
  yNew = assignValueIfBetweenRange(int(y + step * (math.sin(angle))), 0, lenY)
  
  # if debug:
    # cv2.circle(frameDisplay, (xNew, yNew), 1, (0,0,0),   -1)

  framecopy = frame.copy()
  
  xmin = assignValueIfBetweenRange(xNew - halfDiam, 0, lenX-1)
  xmax = assignValueIfBetweenRange(xNew + halfDiam, 0, lenX-1)
  ymin = assignValueIfBetweenRange(yNew - halfDiam, 0, lenY-1)
  ymax = assignValueIfBetweenRange(yNew + halfDiam, 0, lenY-1)
  
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
    import zebrazoom.code.util as util

    util.showFrame(framecopy, title='Frame2')
  
  (minVal, maxVal, headPosition, maxLoc) = cv2.minMaxLoc(framecopy)
  
  xNew = headPosition[0]
  yNew = headPosition[1]
  
  theta = calculateAngle(x, y, xNew, yNew)
  
  xNew = assignValueIfBetweenRange(int(x + segStep  * (math.cos(theta)) ), 0, lenX)
  yNew = assignValueIfBetweenRange(int(y + segStep  * (math.sin(theta)) ), 0, lenY)
  
  # Calculates distance between new and old point
  distSubsquentPoints = math.sqrt((xNew - x)**2 + (yNew - y)**2)
  
  if debug:
    import zebrazoom.code.util as util

    cv2.circle(frameDisplay, (xNew, yNew), 1, (0,0,255),   -1)
    util.showFrame(frameDisplay, title='Frame2')
    
    util.showFrame(framecopy, title='Frame2')
    
  points = appendPoint(xNew, yNew, points)
  newTheta = calculateAngle(x,y,xNew,yNew)
  if distSubsquentPoints > 0 and depth < maxDepth:
    (points,nop) = findNextPoints(depth+distSubsquentPoints,xNew,yNew,frame,points,newTheta,maxDepth,hyperparameters,debug)
  
  return (points,newTheta)


def centerOfMassTailTracking(headPosition,nbTailPoints,i,thresh1,frame,hyperparameters,heading,maxDepth):
  
  x = headPosition[0]
  y = headPosition[1]
  
  initialAngle = hyperparameters["headEmbededParamInitialAngle"]
  
  gaussian_blur = hyperparameters["headEmbededParamGaussianBlur"]
  frame = cv2.GaussianBlur(frame, (gaussian_blur, gaussian_blur), 0)
  points = np.zeros((2, 0))
  
  # if i > 63033:
    # (points, lastFirstTheta2) = findNextPoints(0,x,y,frame,points,initialAngle,maxDepth,hyperparameters,True)
  # else:
  (points, lastFirstTheta2) = findNextPoints(0,x,y,frame,points,initialAngle,maxDepth,hyperparameters,False)
  
  output = np.zeros((1, nbTailPoints, 2))
  
  points = np.insert(points, 0, headPosition, axis=1)
  
  points = points[:,0:(len(points[0])-1)]
  
  points = smoothTail(points, nbTailPoints)

  for idx, x in enumerate(points[0]):
    output[0][idx][0] = x
    output[0][idx][1] = points[1][idx]

  return output


def centerOfMassTailTrackFindMaxDepth(headPosition,nbTailPoints,i,x,y,thresh1,frame,hyperparameters,oppHeading,tailTip):
  
  gaussian_blur = hyperparameters["headEmbededParamGaussianBlur"]
  frame = cv2.GaussianBlur(frame, (gaussian_blur, gaussian_blur), 0)
  angle = hyperparameters["headEmbededParamInitialAngle"]
  points = np.zeros((2, 0))
  
  (points, lastFirstTheta2) = findNextPoints(0,x,y,frame,points,angle,300,hyperparameters,False)
  
  distToTip        = np.full((200),10000)
  curTailLengthTab = np.full((200),10000)
  curTailLength  = 0
  k = 0
  
  distFromHeadToTip = abs(math.sqrt((x-tailTip[0])**2 + (y-tailTip[1])**2))
  while (curTailLength < 1.5*distFromHeadToTip) and (k < len(points[0])-1):
    curTailLength = curTailLength + abs(math.sqrt((points[0,k]-points[0,k+1])**2 + (points[1,k]-points[1,k+1])**2))
    distToTip[k]  = abs(math.sqrt((points[0,k]-tailTip[0])**2 + (points[1,k]-tailTip[1])**2))
    curTailLengthTab[k] = curTailLength
    k = k + 1
  
  minDistToTip    = 1000000
  indMinDistToTip = 0
  for idx, dist in enumerate(distToTip):
    if dist < minDistToTip:
      minDistToTip = dist
      indMinDistToTip = idx
  
  return (curTailLengthTab[indMinDistToTip] )
