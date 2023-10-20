from zebrazoom.code.tracking.customTrackingImplementations.fastFishTracking.tailTrackFindNextPoint import tailTrackFindNextPoint
from zebrazoom.code.extractParameters import calculateTailAngle
import numpy as np
import math
import cv2

def _calculateAngle(xStart, yStart, xEnd, yEnd):
  vx = xEnd - xStart
  vy = yEnd - yStart
  if vx == 0:
    if vy > 0:
      lastFirstTheta = math.pi/2
    else:
      lastFirstTheta = (3*math.pi)/2
  else:
    lastFirstTheta = np.arctan(abs(vy/vx))
    if (vx < 0) and (vy >= 0):
      lastFirstTheta = math.pi - lastFirstTheta
    elif (vx < 0) and (vy <= 0):
      lastFirstTheta = lastFirstTheta + math.pi
    elif (vx > 0) and (vy <= 0):
      lastFirstTheta = 2*math.pi - lastFirstTheta
  return lastFirstTheta

def _getCurvature(points):
  tailX = points[0]
  tailY = points[1]
  l = len(tailX)
  if l > 2:
    curvature = np.zeros(l-2)
    for ii in range(1, l-1):
      angleBef = _calculateAngle(tailX[ii-1], tailY[ii-1], tailX[ii], tailY[ii])
      angleAft = _calculateAngle(tailX[ii],   tailY[ii],   tailX[ii+1], tailY[ii+1])
      curvature[ii-1] = calculateTailAngle(angleBef, angleAft)
    return curvature
  else:
    return []

def tailTrackTry4InitialPerpendicularDirections(headPosition, frameROI, points, lastFirstTheta, maxDepth, steps, nbList, hyperparameters, debug, lenX, lenY):
  (points1, lastFirstTheta1, medianPixTotList1) = tailTrackFindNextPoint(0, headPosition, frameROI, points, lastFirstTheta, maxDepth, steps, nbList,  hyperparameters, debug, lenX, lenY)
  (points2, lastFirstTheta2, medianPixTotList2) = tailTrackFindNextPoint(0, headPosition, frameROI, points, (lastFirstTheta + (math.pi/2)) % (2 * math.pi), maxDepth, steps, nbList,  hyperparameters, debug, lenX, lenY)
  (points3, lastFirstTheta3, medianPixTotList3) = tailTrackFindNextPoint(0, headPosition, frameROI, points, (lastFirstTheta + math.pi) % (2 * math.pi), maxDepth, steps, nbList,  hyperparameters, debug, lenX, lenY)
  (points4, lastFirstTheta4, medianPixTotList4) = tailTrackFindNextPoint(0, headPosition, frameROI, points, (lastFirstTheta + (3/2)*math.pi) % (2 * math.pi), maxDepth, steps, nbList,  hyperparameters, debug, lenX, lenY)
  #
  listOfPoints           = [points1, points2, points3, points4]
  listOfLastFirstTheta   = [lastFirstTheta1, lastFirstTheta2, lastFirstTheta3, lastFirstTheta4]
  listOfMedianPixTotList = [medianPixTotList1, medianPixTotList2, medianPixTotList3, medianPixTotList4]
  listOfCurvatures       = [_getCurvature(point) for point in listOfPoints]
  listOfCurvaturesMeans  = [np.mean(curvature) if len(curvature) else 10000000000 for curvature in listOfCurvatures]
  #
  if False:
    selectedOptionPix  = np.argmin(listOfMedianPixTotList)
    selectedOptionCurv = np.argmin(listOfCurvaturesMeans)
    selectedOption     = selectedOptionCurv
  else:
    argsortOptionPix  = np.argsort(listOfMedianPixTotList)
    argsortOptionCurv = np.argsort(listOfCurvaturesMeans)
    scores = np.ones(len(listOfMedianPixTotList))
    for i in range(len(scores)):
      scores[argsortOptionPix[i]]  += i
      scores[argsortOptionCurv[i]] += i
    selectedOptionTemp = np.argmin(scores)
    possibleInd = (scores < scores[selectedOptionTemp] * 1.5)
    possibleInds = []
    selectedOption = 0
    curMin = 1000000000000000000000000000000000
    for i in range(len(scores)):
      if possibleInd[i] and listOfMedianPixTotList[i] < curMin:
        selectedOption = i
        curMin = listOfMedianPixTotList[i]
    # print("listOfMedianPixTotList:", listOfMedianPixTotList)
    # print("listOfCurvaturesMeans:", listOfCurvaturesMeans)
    # print("scores:", scores)
    # print("possibleInd:", possibleInd)
    # print("selectedOption:", selectedOption)
  #
  points           = listOfPoints[selectedOption]
  lastFirstTheta   = listOfLastFirstTheta[selectedOption]
  medianPixTotList = listOfMedianPixTotList[selectedOption]
  # print("frameNumber:", frameNumber, ";selectedOption:", selectedOption, "; lastFirstTheta:", lastFirstTheta)
  
  return (points, lastFirstTheta, medianPixTotList)
