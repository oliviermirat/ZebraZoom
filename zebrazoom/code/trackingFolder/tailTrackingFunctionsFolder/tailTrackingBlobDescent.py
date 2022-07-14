import h5py
import numpy as np
import cv2
import math
import json
import sys
from scipy import interpolate
from zebrazoom.code.getImage.getForegroundImage import getForegroundImage
from zebrazoom.code.getImage.headEmbededFrame import headEmbededFrame
from scipy.interpolate import UnivariateSpline
from numpy import linspace
# from kalmanFilter import kalman_xy

from zebrazoom.code.trackingFolder.trackingFunctions import calculateAngle
from zebrazoom.code.trackingFolder.trackingFunctions import distBetweenThetas
from zebrazoom.code.trackingFolder.trackingFunctions import assignValueIfBetweenRange

def dist2(v, w):
  return (v["x"] - w["x"])**2 + (v["y"] - w["y"])**2

def distToSegmentSquared(p, v, w):
  l2 = dist2(v, w)
  if l2 == 0:
    return dist2(p, v)
  t = ((p["x"] - v["x"]) * (w["x"] - v["x"]) + (p["y"] - v["y"]) * (w["y"] - v["y"])) / l2
  t = max(0, min(1, t))
  return dist2(p, {"x": v["x"] + t * (w["x"] - v["x"]), "y": v["y"] + t * (w["y"] - v["y"]) })

def distToSegment(p, v, w):
  return math.sqrt(distToSegmentSquared(p, v, w))

def checkNewPointNotRedundant(points, x, y):
  if len(points[0]) > 3:
    dist = (points[0] - x)**2 + (points[1] - y)**2
    min1 = np.argmin(dist)
    minDist = dist[min1]
    
    p = {"x": x, "y": y}
    for i in range(0,len(points[0])-1):
      v = {"x": points[0][i],   "y": points[1][i]   }
      w = {"x": points[0][i+1], "y": points[1][i+1] }
      d = distToSegment(p, v, w)
      if d < minDist:
        minDist = d
    
    if minDist <= 1:
      return 0
    else:
      return 1
  else:
    return 1

def appendPoint(x, y, points):
  curPoint = np.zeros((2, 1))
  curPoint[0] = x;
  curPoint[1] = y;
  points = np.append(points, curPoint, axis=1)
  return points

def recenterPointAlongOrthogonalTailAxis(x,y,theta,frame,thresh1):
  l = [[x,y]]
  
  thresh1lenX = len(thresh1[0]) - 1
  thresh1lenY = len(thresh1) - 1
  
  pixVal = 1
  k1 = 1
  while pixVal < 150 and k1 < 100:
    xNew = assignValueIfBetweenRange(int(x + k1 * (math.cos(theta)) ), 0, thresh1lenX)
    yNew = assignValueIfBetweenRange(int(y + k1 * (math.sin(theta)) ), 0, thresh1lenY)
    pixVal = thresh1[yNew][xNew]
    if pixVal < 150:
      k1 = k1 + 1
      cv2.circle(frame, (xNew, yNew), 1, (0,0,0),   -1)
      point = [xNew, yNew]
      l.append(point)

  pixVal = 1
  k2 = 1
  while pixVal < 150 and k2 < 100:
    xNew = assignValueIfBetweenRange(int(x - k2 * (math.cos(theta)) ), 0, thresh1lenX)
    yNew = assignValueIfBetweenRange(int(y - k2 * (math.sin(theta)) ), 0, thresh1lenY)
    pixVal = thresh1[yNew][xNew]
    if pixVal < 150:
      k2 = k2 + 1
      cv2.circle(frame, (xNew, yNew), 1, (0,0,0),   -1)
      point = [xNew, yNew]
      l = [point] + l
  
  n = len(l)
  xNew = assignValueIfBetweenRange(int((l[0][0] + l[n-1][0]) / 2), 0, thresh1lenX)
  yNew = assignValueIfBetweenRange(int((l[0][1] + l[n-1][1]) / 2), 0, thresh1lenY)
  
  return [xNew, yNew]

def findNextPoints(x,y,thresh1,frame,depth,points,lastTheta,debugAdv,nbList,thetaDiffAccept,expDecreaseFactor,step,debugTracking):

  thresh1lenX = len(thresh1[0]) - 1
  thresh1lenY = len(thresh1) - 1
  
  maxThetaCorrected = -1

  if debugAdv:
    import zebrazoom.code.util as util

    util.showFrame(frame, title='Frame')

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
        xNew = assignValueIfBetweenRange(int(x + k1 * (math.cos(theta))), 0, thresh1lenX)
        yNew = assignValueIfBetweenRange(int(y + k1 * (math.sin(theta))), 0, thresh1lenY)
        pixVal = thresh1[yNew][xNew]
        k1 = k1 + 1
      k1 = k1 - 2
      
      # Find furtherest point away from "old" "current" point still inside blob along the theta angle in the other direction
      pixVal = 1
      k2 = 1
      while pixVal < 150 and k2 < 100:
        xNew = assignValueIfBetweenRange(int(x - k2 * (math.cos(theta)) ), 0, thresh1lenX)
        yNew = assignValueIfBetweenRange(int(y - k2 * (math.sin(theta)) ), 0, thresh1lenY)
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
      x1 = assignValueIfBetweenRange(int(x + step  * (math.cos(maxTheta)) ), 0, thresh1lenX)
      y1 = assignValueIfBetweenRange(int(y + step  * (math.sin(maxTheta)) ), 0, thresh1lenY)
    else:
      x1 = assignValueIfBetweenRange(int(x + k1Max  * (math.cos(maxTheta)) ), 0, thresh1lenX)
      y1 = assignValueIfBetweenRange(int(y + k1Max  * (math.sin(maxTheta)) )  , 0, thresh1lenY)
    if k2Max > step:
      x2 = assignValueIfBetweenRange(int(x - step  * (math.cos(maxTheta)) ), 0, thresh1lenX)
      y2 = assignValueIfBetweenRange(int(y - step  * (math.sin(maxTheta)) ), 0, thresh1lenY)
    else:
      x2 = assignValueIfBetweenRange(int(x - k2Max  * (math.cos(maxTheta)) ), 0, thresh1lenX)
      y2 = assignValueIfBetweenRange(int(y - k2Max  * (math.sin(maxTheta)) ), 0, thresh1lenY)
    
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
    [x1, y1] = recenterPointAlongOrthogonalTailAxis(x1, y1, predictedTetha+(math.pi)/2, frame, thresh1)
    [x2, y2] = recenterPointAlongOrthogonalTailAxis(x2, y2, predictedTetha+(math.pi)/2, frame, thresh1)
    
    x1 = assignValueIfBetweenRange(x1, 0, thresh1lenX)
    y1 = assignValueIfBetweenRange(y1, 0, thresh1lenY)
    x2 = assignValueIfBetweenRange(x2, 0, thresh1lenX)
    y2 = assignValueIfBetweenRange(y2, 0, thresh1lenY)
    
    cv2.circle(frame, (x, y), 1, (255,0,255),   -1)
    
    # Calculates distance between new and old local tail angle
    diffAngle1 = distBetweenThetas(lastTheta, maxTheta )
    diffAngle2 = distBetweenThetas(lastTheta, (maxTheta + math.pi) )
    
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
      check = checkNewPointNotRedundant(points, x2, y2)
      if check:
        points = appendPoint(x2, y2, points)
        if distSubsquentPoints2 > 0:
          maxThetaCorrected = maxTheta + math.pi
          newTheta = calculateAngle(x,y,x2,y2)
          (points,nop) = findNextPoints(x2,y2,thresh1,frame,depth+1,points,newTheta,debugAdv,nbList,thetaDiffAccept,expDecreaseFactor,step,debugTracking)
    else:
      if debugTracking:
        if thresh1[y1][x1] > 150:
          print("oups white zone")
        if debugAdv:
          print("diffAngle1: ",diffAngle1," ; k1Max: ",k1Max," distSubsquentPoints1:",distSubsquentPoints1)
      cv2.circle(frame, (x1, y1), 1, (0,255,0),   -1)
      check = checkNewPointNotRedundant(points, x1, y1)
      if check:
        points = appendPoint(x1, y1, points)
        if distSubsquentPoints1 > 0:
          maxThetaCorrected = maxTheta
          newTheta = calculateAngle(x,y,x1,y1)
          (points,nop) = findNextPoints(x1,y1,thresh1,frame,depth+1,points,newTheta,debugAdv,nbList,thetaDiffAccept,expDecreaseFactor,step,debugTracking)
        
  return (points,maxThetaCorrected)
  
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

  # x,y,thresh1,frame,0,points,lastFirstTheta,debugAdv,nbList,thetaDiffAccept,expDecreaseFactor,ste,debugTracking
  
def tailTrackingBlobDescent(headPosition,nbTailPoints,i,x,y,thresh1,frame,lastFirstTheta,debugAdv,thetaDiffAccept,hyperparameters):

  step = hyperparameters["step"]
  nbList = hyperparameters["nbList"]
  expDecreaseFactor = hyperparameters["expDecreaseFactor"]
  firstFrame = hyperparameters["firstFrame"]
  lastFrame = hyperparameters["lastFrame"]
  minArea = hyperparameters["minArea"]
  maxArea = hyperparameters["maxArea"]
  headSize = hyperparameters["headSize"]
  debugTracking = hyperparameters["debugTracking"]
  headEmbeded = hyperparameters["headEmbeded"]
  
  output = np.zeros((1, nbTailPoints, 2))
  
  possiblePoints = []
  for ste in step:
    points = np.zeros((2, 0))
    (points, lastFirstTheta2) = findNextPoints(x,y,thresh1,frame,0,points,lastFirstTheta,debugAdv,nbList,thetaDiffAccept,expDecreaseFactor,ste,debugTracking)
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
  points = smoothTail(points, nbTailPoints)

  # for idx, x in enumerate(points[0]):
    # output[i-firstFrame][idx][0] = x
    # output[i-firstFrame][idx][1] = points[1][idx]
    
  for idx, x in enumerate(points[0]):
    output[0][idx][0] = x
    output[0][idx][1] = points[1][idx]

  return output
