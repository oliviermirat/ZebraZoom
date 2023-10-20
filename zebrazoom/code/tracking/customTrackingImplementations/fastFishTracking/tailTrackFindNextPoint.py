from zebrazoom.code.tracking.customTrackingImplementations.fastFishTracking.utilities import appendPoint, distBetweenThetas, assignValueIfBetweenRange, calculateAngle
import zebrazoom.code.util as util
import numpy as np
import math
import cv2

def tailTrackFindNextPoint(depth, headPosition, frame, points, angle, maxDepth, steps, nbList, hyperparameters, debug, lenX, lenY, secondTry=False):
  
  x = headPosition[0]
  y = headPosition[1]
  
  pixSurMax = hyperparameters["headEmbededParamTailDescentPixThreshStop"]
  
  pixTotList = []
  
  distSubsquentPoints = 0.000001
  pixSur = 0
  
  while (distSubsquentPoints > 0 and depth < maxDepth and ((pixSur < pixSurMax) or (depth < hyperparameters["authorizedRelativeLengthTailEnd"]*maxDepth))):
  
    if depth == 0 and angle == -99999: # First frame, first segment
      thetaDiffAccept = 3.6
    else:
      if (depth < hyperparameters["authorizedRelativeLengthTailEnd"]*maxDepth):
        thetaDiffAccept = hyperparameters["thetaDiffAccept"]
      else:
        if not("authorizedRelativeLengthTailEnd2" in hyperparameters) or (depth < hyperparameters["authorizedRelativeLengthTailEnd2"]*maxDepth):
          thetaDiffAccept = hyperparameters["thetaDiffAcceptAfterAuthorizedRelativeLengthTailEnd"]
          nbList = hyperparameters["nbListAfterAuthorizedRelativeLengthTailEnd"]
        else:
          thetaDiffAccept = hyperparameters["thetaDiffAcceptAfterAuthorizedRelativeLengthTailEnd2"]
          nbList = hyperparameters["nbListAfterAuthorizedRelativeLengthTailEnd2"]
          

    pixTotMax = 1000000
    maxTheta  = angle

    l = [i*(math.pi/nbList) for i in range(0,2*nbList) if distBetweenThetas(i*(math.pi/nbList), angle) < thetaDiffAccept]

    for step in steps:
      if (step < maxDepth - depth) or (step == steps[0]):
        for theta in l:
          xNew = assignValueIfBetweenRange(int(x + step * (math.cos(theta))), 0, lenX)
          yNew = assignValueIfBetweenRange(int(y + step * (math.sin(theta))), 0, lenY)
          pixTot = frame[yNew][xNew]
          if (pixTot < pixTotMax):
            pixTotMax = pixTot
            maxTheta = theta
            xTot = xNew
            yTot = yNew
    
    pixTotList.append(pixTotMax)
    
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
      frameDisplay = frame.copy()
      cv2.circle(frameDisplay, (xTot, yTot), 1, (0,0,0),   -1)
      util.showFrame(frameDisplay, title="HeadEmbeddedTailTracking")
    
    newTheta = calculateAngle(x,y,xTot,yTot)
    
    angle = newTheta
    if depth == 0:
      lastFirstTheta = angle
    depth = depth + distSubsquentPoints
    x = xTot
    y = yTot
  
  lenPoints = len(points[0]) - 1
  if points[0, lenPoints-1] == points[0, lenPoints] and points[1, lenPoints-1] == points[1, lenPoints]:
    points = points[:, :len(points[0])-1]
  
  if debug:
    print(np.median(pixTotList), np.mean(pixTotList), pixTotList)
  
  medianPixTotList = np.median(pixTotList)
  if "tries4rotationsCombination" in hyperparameters and hyperparameters["tries4rotationsCombination"] and len(pixTotList) <= 2:
    medianPixTotList += 25
  
  if hyperparameters["maximumMedianValueOfAllPointsAlongTheTail"] and medianPixTotList > hyperparameters["maximumMedianValueOfAllPointsAlongTheTail"] and not(secondTry):
    # print("second try")
    (points2, lastFirstTheta2, medianPixTotList2) = tailTrackFindNextPoint(0, headPosition, frame, np.zeros((2, 0)), (lastFirstTheta + math.pi) % (2 * math.pi), maxDepth, steps, nbList, hyperparameters, debug, lenX, lenY, True)
    if medianPixTotList2 < medianPixTotList:
      return (points2, lastFirstTheta2, medianPixTotList2)
  
  return (points, lastFirstTheta, medianPixTotList)