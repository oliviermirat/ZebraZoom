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

def findTheTwoSides(headPosition, bodyContour, dst, hyperparameters):
  
  if hyperparameters["detectMouthInsteadOfHeadTwoSides"] == 1:
    
    lenX = len(dst[0])
    lenY = len(dst)
    originalShape = np.zeros((lenY, lenX))
    originalShape[:, :] = 0
    originalShape = originalShape.astype(np.uint8)
    cv2.fillPoly(originalShape, pts =[bodyContour], color=(255))
    
    minWhitePixel = 1000000000
    bestAngle     = 0
    nTries        = 50
    for i in range(0, nTries):
      angleOption = i * ((2 * math.pi) / nTries)
      startPoint = (int(headPosition[0]), int(headPosition[1]))
      endPoint   = (int(headPosition[0] + 100000 * math.cos(angleOption)), int(headPosition[1] + 100000 * math.sin(angleOption)))
      testImage  = originalShape.copy()
      testImage  = cv2.line(testImage, startPoint, endPoint, (0), 1)
      nbWhitePixels = cv2.countNonZero(testImage)
      if nbWhitePixels < minWhitePixel:
        minWhitePixel = nbWhitePixels
        bestAngle     = angleOption
    
    for i in range(0, nTries):
      angleOption = bestAngle - (math.pi / 5) + i * ((2 * (math.pi / 5)) / nTries)
      startPoint = (int(headPosition[0]), int(headPosition[1]))
      endPoint   = (int(headPosition[0] + 100000 * math.cos(angleOption)), int(headPosition[1] + 100000 * math.sin(angleOption)))
      testImage  = originalShape.copy()
      testImage  = cv2.line(testImage, startPoint, endPoint, (0), 1)
      nbWhitePixels = cv2.countNonZero(testImage)
      if nbWhitePixels < minWhitePixel:
        minWhitePixel = nbWhitePixels
        bestAngle     = angleOption
    
    unitVector = np.array([math.cos(bestAngle + math.pi), math.sin(bestAngle + math.pi)])
    factor     = 1
    headPos    = np.array(headPosition)
    testBorder = headPos + factor * unitVector
    testBorder = testBorder.astype(int)
    while (cv2.pointPolygonTest(bodyContour, (testBorder[0], testBorder[1]), True) > 0) and (factor < 100) and (testBorder[0] >= 0) and (testBorder[1] >= 0) and (testBorder[0] < len(dst[0])) and (testBorder[1] < len(dst)):
      factor = factor + 1
      testBorder = headPos + factor * unitVector
    
    xOtherBorder = testBorder[0]
    yOtherBorder = testBorder[1]
    minDist1 = 1000000000000
    minDist2 = 1000000000000
    indMin1  = 0
    indMin2  = 0
    for i in range(0, len(bodyContour)):
      Pt   = bodyContour[i][0]
      dist = math.sqrt((Pt[0] - xOtherBorder)**2 + (Pt[1] - yOtherBorder)**2)
      if (dist < minDist1):
        minDist2 = minDist1
        indMin2  = indMin1
        minDist1 = dist
        indMin1  = i
      else:
        if (dist < minDist2):
          minDist2 = dist
          indMin2  = i
    
    res = [indMin1, indMin2]
    
  else:
    
    res = np.zeros(2)
    
    x = headPosition[0]
    y = headPosition[1]
    
    minDist = 1000000000000
    indMin  = 0
    for i in range(0, len(bodyContour)):
      Pt   = bodyContour[i][0]
      dist = math.sqrt((Pt[0] - x)**2 + (Pt[1] - y)**2)
      if (dist < minDist):
        minDist = dist
        indMin  = i
    
    res[0] = indMin
    PtClosest = bodyContour[indMin][0]
    headPos   = np.array(headPosition)
    
    unitVector = np.array([x - PtClosest[0], y - PtClosest[1]])
    unitVectorLength = math.sqrt(unitVector[0]**2 + unitVector[1]**2)
    unitVector[0] = unitVector[0] / unitVectorLength
    unitVector[1] = unitVector[1] / unitVectorLength
    
    factor = 1
    testBorder = headPos + factor * unitVector
    testBorder = testBorder.astype(int)
    while (cv2.pointPolygonTest(bodyContour, (testBorder[0], testBorder[1]), True) > 0) and (factor < 100) and (testBorder[0] >= 0) and (testBorder[1] >= 0) and (testBorder[0] < len(dst[0])) and (testBorder[1] < len(dst)):
      factor = factor + 1
      testBorder = headPos + factor * unitVector
    
    xOtherBorder = testBorder[0]
    yOtherBorder = testBorder[1]
    
    minDist = 1000000000000
    indMin2  = 0
    for i in range(0, len(bodyContour)):
      Pt   = bodyContour[i][0]
      dist = math.sqrt((Pt[0] - xOtherBorder)**2 + (Pt[1] - yOtherBorder)**2)
      if (dist < minDist):
        minDist = dist
        indMin2  = i
    
    res[1] = indMin2
    
  if False:
    cv2.circle(dst, (pt1[0],pt1[1]), 1, (0, 0, 255), -1)
    cv2.circle(dst, (pt2[0],pt2[1]), 1, (0, 0, 255), -1)
    cv2.imshow('Frame', dst)
    cv2.waitKey(0)
  
  return res
