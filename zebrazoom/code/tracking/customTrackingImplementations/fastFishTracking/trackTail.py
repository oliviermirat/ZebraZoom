from zebrazoom.code.tracking.customTrackingImplementations.fastFishTracking.utilities import appendPoint, distBetweenThetas, assignValueIfBetweenRange, calculateAngle
import numpy as np
import math
import cv2

def __insideTrackTail(depth, x, y, frame, points, angle, maxDepth, steps, nbList, hyperparameters, debug, lenX, lenY):
  
  pixSurMax = hyperparameters["headEmbededParamTailDescentPixThreshStop"]
  
  distSubsquentPoints = 0.000001
  pixSur = 0
  
  while (distSubsquentPoints > 0 and depth < maxDepth and ((pixSur < pixSurMax) or (depth < hyperparameters["authorizedRelativeLengthTailEnd"]*maxDepth))):
  
    if depth == 0:
      thetaDiffAccept = 3.6
    else:
      thetaDiffAccept = 1

    pixTotMax = 1000000
    maxTheta  = angle

    l = [i*(math.pi/nbList) for i in range(0,2*nbList) if distBetweenThetas(i*(math.pi/nbList), angle) < thetaDiffAccept]

    for step in steps:

      if (step < maxDepth - depth) or (step == steps[0]):

        for theta in l:

          xNew = assignValueIfBetweenRange(int(x + step * (math.cos(theta))), 0, lenX)
          yNew = assignValueIfBetweenRange(int(y + step * (math.sin(theta))), 0, lenY)
          pixTot = frame[yNew][xNew]

          # Keeps that theta angle as maximum if appropriate
          if (pixTot < pixTotMax):
            pixTotMax = pixTot
            maxTheta = theta
            xTot = xNew
            yTot = yNew

    if False:
      w = 4
      ym = yTot - w
      yM = yTot + w
      xm = xTot - w
      xM = xTot + w
      if ym < 0:
        ym = 0
      if xm < 0:
        xm = 0
      if yM > lenY + 1:
        yM = lenY + 1
      if xM > lenX + 1:
        xM = lenX + 1
      pixSur = np.min(frame[ym:yM, xm:xM])
    else:
      pixSur = frame[yTot, xTot]

    # Calculates distance between new and old point
    distSubsquentPoints = math.sqrt((xTot - x)**2 + (yTot - y)**2)
    
    if depth + distSubsquentPoints < maxDepth and ((pixSur < pixSurMax) or (depth < hyperparameters["authorizedRelativeLengthTailEnd"]*maxDepth)):
      points = appendPoint(xTot, yTot, points)
    else:
      vectX = xTot - x
      vectY = yTot - y
      xTot  = int(x + (maxDepth / (depth + distSubsquentPoints)) * vectX)
      yTot  = int(y + (maxDepth / (depth + distSubsquentPoints)) * vectY)
      points = appendPoint(xTot, yTot, points)
    
    if debug:
      cv2.circle(frame, (xTot, yTot), 3, (255,0,0),   -1)
      util.showFrame(frame, title="HeadEmbeddedTailTracking")
    
    newTheta = calculateAngle(x,y,xTot,yTot)
    
    angle = newTheta
    depth = depth + distSubsquentPoints
    x = xTot
    y = yTot
  
  lenPoints = len(points[0]) - 1
  if points[0, lenPoints-1] == points[0, lenPoints] and points[1, lenPoints-1] == points[1, lenPoints]:
    points = points[:, :len(points[0])-1]
  
  return (points, newTheta)


def __findNextPointsRecursive(depth, x, y, frame, points, angle, maxDepth, steps, nbList, hyperparameters, debug, lenX, lenY):
  
  if depth == 0:
    thetaDiffAccept = 3.6
  else:
    thetaDiffAccept = 1

  pixTotMax = 1000000
  maxTheta  = angle

  l = [i*(math.pi/nbList) for i in range(0,2*nbList) if distBetweenThetas(i*(math.pi/nbList), angle) < thetaDiffAccept]

  for step in steps:

    if (step < maxDepth - depth) or (step == steps[0]):

      for theta in l:

        xNew = assignValueIfBetweenRange(int(x + step * (math.cos(theta))), 0, lenX)
        yNew = assignValueIfBetweenRange(int(y + step * (math.sin(theta))), 0, lenY)
        pixTot = frame[yNew][xNew]

        # Keeps that theta angle as maximum if appropriate
        if (pixTot < pixTotMax):
          pixTotMax = pixTot
          maxTheta = theta
          xTot = xNew
          yTot = yNew

  if False:
    w = 4
    ym = yTot - w
    yM = yTot + w
    xm = xTot - w
    xM = xTot + w
    if ym < 0:
      ym = 0
    if xm < 0:
      xm = 0
    if yM > lenY + 1:
      yM = lenY + 1
    if xM > lenX + 1:
      xM = lenX + 1
    pixSur = np.min(frame[ym:yM, xm:xM])
  else:
    pixSur = frame[yTot, xTot]

  # Calculates distance between new and old point
  distSubsquentPoints = math.sqrt((xTot - x)**2 + (yTot - y)**2)

  pixSurMax = hyperparameters["headEmbededParamTailDescentPixThreshStop"]
  
  if depth + distSubsquentPoints < maxDepth and ((pixSur < pixSurMax) or (depth < hyperparameters["authorizedRelativeLengthTailEnd"]*maxDepth)):
    points = appendPoint(xTot, yTot, points)
  else:
    vectX = xTot - x
    vectY = yTot - y
    xTot  = int(x + (maxDepth / (depth + distSubsquentPoints)) * vectX)
    yTot  = int(y + (maxDepth / (depth + distSubsquentPoints)) * vectY)
    points = appendPoint(xTot, yTot, points)
  
  if debug:
    cv2.circle(frame, (xTot, yTot), 3, (255,0,0),   -1)
    util.showFrame(frame, title="HeadEmbeddedTailTracking")

  newTheta = calculateAngle(x,y,xTot,yTot)
  if distSubsquentPoints > 0 and depth + distSubsquentPoints < maxDepth and ((pixSur < pixSurMax) or (depth < hyperparameters["authorizedRelativeLengthTailEnd"]*maxDepth)):
    (points,nop) = __findNextPointsRecursive(depth+distSubsquentPoints,xTot,yTot,frame,points,newTheta,maxDepth,steps,nbList,hyperparameters, debug, lenX, lenY)

  if depth == 0:
    lenPoints = len(points[0]) - 1
    if points[0, lenPoints-1] == points[0, lenPoints] and points[1, lenPoints-1] == points[1, lenPoints]:
      points = points[:, :len(points[0])-1]

  return (points, newTheta)


def trackTail(frameROI, headPosition, hyperparameters):
  
  steps   = hyperparameters["steps"]
  nbList  = 10 if hyperparameters["nbList"] == -1 else hyperparameters["nbList"]
  maxDepth = hyperparameters["maxDepth"]
  
  x = headPosition[0]
  y = headPosition[1]

  angle = 0 #self.calculateAngle(x, y, tailTip[0], tailTip[1])

  points = np.zeros((2, 0))
  
  debug = hyperparameters["debugHeadEmbededFindNextPoints"]
  lenX = len(frameROI[0]) - 1
  lenY = len(frameROI) - 1
  
  if True:
    (points, lastFirstTheta2) = __insideTrackTail(0, x, y, frameROI, points, angle, maxDepth, steps, nbList,  hyperparameters, debug, lenX, lenY)
  else:
    (points, lastFirstTheta2) = __findNextPointsRecursive(0, x, y, frameROI, points, angle, maxDepth, steps, nbList,  hyperparameters, debug, lenX, lenY)
  
  points = np.insert(points, 0, headPosition, axis=1)

  output = np.zeros((1, len(points[0]), 2))

  for idx, x in enumerate(points[0]):
    output[0][idx][0] = x
    output[0][idx][1] = points[1][idx]

  return output
