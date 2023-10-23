from zebrazoom.code.tracking.customTrackingImplementations.fastFishTracking.utilities import appendPoint, distBetweenThetas, assignValueIfBetweenRange, calculateAngle
import zebrazoom.code.util as util
import numpy as np
import math
import cv2
 
def dualDirectionTailDetection(headPosition, frame, points, angle, maxDepth, steps, nbList, hyperparameters, debug, lenX, lenY):
  
  x = headPosition[0]
  y = headPosition[1]
  
  depth = 0
  angleOpp = angle
  
  pixSurMax = hyperparameters["headEmbededParamTailDescentPixThreshStop"]
  
  pixTotList = []
  
  distSubsquentPoints = 0.000001
  pixSur = 0
  
  if debug:
    frameDisplay = frame.copy()
    cv2.circle(frameDisplay, (x, y), 3, (0,0,0),   -1)
    util.showFrame(frameDisplay, title="HeadEmbeddedTailTracking")
  
  while (distSubsquentPoints > 0 and depth < maxDepth and ((pixSur < pixSurMax) or (depth < hyperparameters["authorizedRelativeLengthTailEnd"]*maxDepth))):
  
    if depth == 0 and angle == -99999: # First frame, first segment
      thetaDiffAccept = 1.8
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
    
    if debug:
      print("thetaDiffAccept:", thetaDiffAccept)
    
    # Initial direction
    if len(points[0]) == 0:
      xOld = x
      yOld = y
    else:
      nbCols = len(points[0])
      xOld = points[0][nbCols - 1]
      yOld = points[1][nbCols - 1]
    pixTotMax = 1000000
    maxTheta  = angle
    l = [i*(math.pi/nbList) for i in range(0,2*nbList) if distBetweenThetas(i*(math.pi/nbList), angle) < thetaDiffAccept]
    if debug:
      print("l normal:", l)
    for step in steps:
      if (step < maxDepth - depth) or (step == steps[0]):
        for theta in l:
          xNew = assignValueIfBetweenRange(int(xOld + step * (math.cos(theta))), 0, lenX)
          yNew = assignValueIfBetweenRange(int(yOld + step * (math.sin(theta))), 0, lenY)
          pixTot = frame[yNew][xNew]
          if (pixTot < pixTotMax):
            pixTotMax = pixTot
            maxTheta = theta
            xTot = xNew
            yTot = yNew
            if debug:
              print("regular dir: Choosing (x, y):", xTot, yTot, "; step:", step, "; theta:", theta, "; pixTot:", pixTot)
    pixTotList.append(pixTotMax)
    pixSur = frame[yTot, xTot]

    # Opposite direction
    if len(points[0]) == 0:
      xOld = x
      yOld = y
    else:
      xOld = points[0][0]
      yOld = points[1][0]
    pixTotMax = 1000000 # remove this line?
    maxTheta  = angleOpp
    l = [i*(math.pi/nbList) for i in range(0,2*nbList) if distBetweenThetas(i*(math.pi/nbList), angleOpp) < thetaDiffAccept]
    if debug:
      print("l opposite:", l)
    for step in steps:
      if (step < maxDepth - depth) or (step == steps[0]):
        for theta in l:
          xNew = assignValueIfBetweenRange(int(xOld + step * (math.cos(theta))), 0, lenX)
          yNew = assignValueIfBetweenRange(int(yOld + step * (math.sin(theta))), 0, lenY)
          pixTot = frame[yNew][xNew]
          if (pixTot < pixTotMax):
            pixTotMax = pixTot
            maxTheta = theta
            xTotOpp = xNew
            yTotOpp = yNew
            if debug:
              print("opposite dir: Choosing (x, y):", xTotOpp, yTotOpp, "; step:", step, "; theta:", theta, "; pixTot:", pixTot)
    pixTotList.append(pixTotMax)
    pixSurOpp = frame[yTotOpp, xTotOpp]
    
    # Choosing between initial and opposite direction
    if pixSurOpp < pixSur:
      xTot   = xTotOpp
      yTot   = yTotOpp
      pixSur = pixSurOpp
      oppChosen = True
    else:
      oppChosen = False
      
    if debug:
      print("oppChosen:", oppChosen)
      print("xTot, yTot:", xTot, yTot)
    
    # Calculates distance between new and old point
    if len(points[0]) == 0:
      xOld = x
      yOld = y
    else:
      if oppChosen:
        xOld = points[0][0]
        yOld = points[1][0]
      else:
        nbCols = len(points[0])
        xOld = points[0][nbCols - 1]
        yOld = points[1][nbCols - 1]
    
    distSubsquentPoints = math.sqrt((xTot - xOld)**2 + (yTot - yOld)**2)
    if debug:
      print("distSubsquentPoints:", distSubsquentPoints)
    
    if depth + distSubsquentPoints < maxDepth and ((pixSur < pixSurMax) or (depth < hyperparameters["authorizedRelativeLengthTailEnd"]*maxDepth)):
      if oppChosen:
        points = np.insert(points, 0, [xTot, yTot], 1)
      else:
        points = appendPoint(xTot, yTot, points)
    else:
      if debug:
        print("diff")
      vectX = xTot - xOld
      vectY = yTot - yOld
      xTot  = int(xOld + (maxDepth / (depth + distSubsquentPoints)) * vectX)
      yTot  = int(yOld + (maxDepth / (depth + distSubsquentPoints)) * vectY)
      if oppChosen:
        points = np.insert(points, 0, [xTot, yTot], 1)
      else:
        points = appendPoint(xTot, yTot, points)
    
    if debug:
      print("points:", points)
      cv2.circle(frameDisplay, (xTot, yTot), 1, (0,0,0),   -1)
      util.showFrame(frameDisplay, title="HeadEmbeddedTailTracking")
    
    newTheta = calculateAngle(xOld,yOld,xTot,yTot)
    
    if depth == 0:
      if oppChosen:
        angleOpp = newTheta
        angle    = (newTheta + math.pi) % (2 * math.pi)
      else:
        angle    = newTheta 
        angleOpp = (newTheta + math.pi) % (2 * math.pi)
    else:
      if oppChosen:
        angleOpp = newTheta
      else:
        angle = newTheta
    
    if depth == 0:
      lastFirstTheta = angle
    depth = depth + distSubsquentPoints
  
  lenPoints = len(points[0]) - 1
  if points[0, lenPoints-1] == points[0, lenPoints] and points[1, lenPoints-1] == points[1, lenPoints]:
    points = points[:, :len(points[0])-1]
  
  if debug:
    print(np.median(pixTotList), np.mean(pixTotList), pixTotList)
  
  medianPixTotList = np.median(pixTotList)
  
  return (points, lastFirstTheta, medianPixTotList)
  