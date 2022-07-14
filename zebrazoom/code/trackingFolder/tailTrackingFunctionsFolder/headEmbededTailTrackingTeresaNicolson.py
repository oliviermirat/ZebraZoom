import numpy as np
import cv2
import zebrazoom.videoFormatConversion.zzVideoReading as zzVideoReading
from zebrazoom.code.trackingFolder.trackingFunctions import calculateAngle
from zebrazoom.code.trackingFolder.trackingFunctions import distBetweenThetas
from zebrazoom.code.trackingFolder.trackingFunctions import assignValueIfBetweenRange
import math
from scipy.interpolate import UnivariateSpline
from numpy import linspace
import os.path
import csv
from scipy.interpolate import interp1d


def smoothTail(points, nbTailPoints):

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

def appendPoint(x, y, points):
  curPoint = np.zeros((2, 1))
  curPoint[0] = x;
  curPoint[1] = y;
  points = np.append(points, curPoint, axis=1)
  return points

def findNextPoints(depth,x,y,frame,points,angle,maxDepth,steps,nbList,initialImage,debug):
  
  lenX = len(frame[0]) - 1
  lenY = len(frame) - 1

  thetaDiffAccept = 1 #0.4
  
  if depth < 0.15*maxDepth:
    thetaDiffAccept = 0.4
  
  if depth > 0.85*maxDepth:
    thetaDiffAccept = 0.6
  
  pixTotMax = 1000000
  maxTheta  = angle

  l = [i*(math.pi/nbList) for i in range(0,2*nbList) if distBetweenThetas(i*(math.pi/nbList), angle) < thetaDiffAccept]
  
  if debug:
    print("debug")
  
  xTot = assignValueIfBetweenRange(x + steps[0], 0, lenX)
  yTot = assignValueIfBetweenRange(y, 0, lenY)
  if yTot == 0:
    yTot = 400
  
  for step in steps:
  
    for theta in l:
      
      xNew = assignValueIfBetweenRange(int(x + step * (math.cos(theta))), 0, lenX)
      yNew = assignValueIfBetweenRange(int(y + step * (math.sin(theta))), 0, lenY)
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
    points = appendPoint(xTot, yTot, points)
    if debug:
      import zebrazoom.code.util as util

      cv2.circle(frame, (xTot, yTot), 3, (255,0,0),   -1)
      util.showFrame(frame, title='HeadEmbeddedTailTracking')
    
  newTheta = calculateAngle(x,y,xTot,yTot)
  
  if (distSubsquentPoints > 0) and (depth < 2*maxDepth) and (xTot < 1280 - 10) and (yTot > 10) and (yTot < 1024 - 10) and ((pixSur < pixSurMax) or (depth < 2*0.85*maxDepth)):
    (points,nop) = findNextPoints(depth+distSubsquentPoints,xTot,yTot,frame,points,newTheta,maxDepth,steps,nbList,initialImage,debug)
  
  return (points,newTheta)


def headEmbededTailTrackingTeresaNicolson(headPosition,nbTailPoints,i,thresh1,frame,hyperparameters,heading,maxDepth,tailTip,threshForBlackFrames):

  steps   = hyperparameters["step"]
  nbList  = 10
  
  x = headPosition[0]
  y = headPosition[1]
  
  initialImage = frame.copy()
  
  gaussian_blur = hyperparameters["headEmbededParamGaussianBlur"]
  frame = cv2.GaussianBlur(frame, (gaussian_blur, gaussian_blur), 0)
  # angle = hyperparameters["headEmbededParamInitialAngle"]
  angle = calculateAngle(x, y, tailTip[0], tailTip[1])
  
  points = np.zeros((2, 0))
  
  if np.mean(np.mean(frame)) > threshForBlackFrames:
    (points, lastFirstTheta2) = findNextPoints(0,x,y,frame,points,angle,maxDepth,steps,nbList,initialImage,hyperparameters["debugHeadEmbededFindNextPoints"])
    points = np.insert(points, 0, headPosition, axis=1) 
    if len(points[0]) > 3:
      points = smoothTail(points, nbTailPoints)
    points[0][0] = headPosition[0]
    points[1][0] = headPosition[1]
  else:
    points = np.zeros((2, nbTailPoints))
  
  output = np.zeros((1, len(points[0]), 2))

  for idx, x in enumerate(points[0]):
    output[0][idx][0] = x
    output[0][idx][1] = points[1][idx]

  return output


def headEmbededTailTrackFindMaxDepthTeresaNicolson(headPosition,nbTailPoints,i,x,y,thresh1,frame,hyperparameters,oppHeading,tailTip):

  x = headPosition[0]
  y = headPosition[1]

  steps   = hyperparameters["step"]
  nbList  = 10
  
  initialImage = frame.copy()
  
  gaussian_blur = hyperparameters["headEmbededParamGaussianBlur"]
  frame = cv2.GaussianBlur(frame, (gaussian_blur, gaussian_blur), 0)
  
  angle = calculateAngle(x, y, tailTip[0], tailTip[1])
  
  points = np.zeros((2, 0))
  
  (points, lastFirstTheta2) = findNextPoints(0,x,y,frame,points,angle,hyperparameters["headEmbededTailTrackFindMaxDepthInitialMaxDepth"],steps,nbList,initialImage, hyperparameters["debugHeadEmbededFindNextPoints"])
  
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
  
  
def getMeanOfImageOverVideo(videoPath, hyperparameters):
  cap = zzVideoReading.VideoCapture(videoPath)
  meanss = []
  ret = True
  i = 0
  while (i < 100):
    ret, frame = cap.read()
    if ret:
      if hyperparameters["invertBlackWhiteOnImages"]:
        frame = 255 - frame
      val = np.mean(np.mean(frame))
      meanss.append(val)
    i = i +1
  return np.mean(meanss)
  
