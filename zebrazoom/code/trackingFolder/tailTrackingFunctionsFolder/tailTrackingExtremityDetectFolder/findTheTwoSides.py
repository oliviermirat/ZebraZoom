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
# import time

def findTheTwoSides(headPosition, bodyContour, dst, hyperparameters):
  
  if hyperparameters["detectMouthInsteadOfHeadTwoSides"] == 1:
    
    lenX = len(dst[0])
    lenY = len(dst)
    originalShape = np.zeros((lenY, lenX))
    originalShape[:, :] = 0
    originalShape = originalShape.astype(np.uint8)
    cv2.fillPoly(originalShape, pts =[bodyContour], color=(255))
    
    # Heading calculation: first approximation
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
    bestAngleAfterFirstStep = bestAngle
    
    # Heading calculation: second (and refined) approximation
    # Searching for the optimal value of iterationsForErodeImageForHeadingCalculation
    countTries = 0
    nbIterations2nbWhitePixels = {}
    if "iterationsForErodeImageForHeadingCalculation" in hyperparameters:
      iterationsForErodeImageForHeadingCalculation = hyperparameters["iterationsForErodeImageForHeadingCalculation"]
    else:
      iterationsForErodeImageForHeadingCalculation = 4
    kernel = np.ones((3, 3), np.uint8)
    nbWhitePixelsMax = 75
    while (iterationsForErodeImageForHeadingCalculation > 0) and (countTries < 50) and not(iterationsForErodeImageForHeadingCalculation in nbIterations2nbWhitePixels):
      testImage2 = cv2.erode(testImage, kernel, iterations = iterationsForErodeImageForHeadingCalculation)
      nbWhitePixels = cv2.countNonZero(testImage2)
      nbIterations2nbWhitePixels[iterationsForErodeImageForHeadingCalculation] = nbWhitePixels
      if nbWhitePixels < nbWhitePixelsMax:
        iterationsForErodeImageForHeadingCalculation = iterationsForErodeImageForHeadingCalculation - 1
      if nbWhitePixels >= nbWhitePixelsMax:
        iterationsForErodeImageForHeadingCalculation = iterationsForErodeImageForHeadingCalculation + 1
      countTries = countTries + 1
    best_iterations = 0
    minDist = 10000000000000
    for iterations in nbIterations2nbWhitePixels:
      nbWhitePixels = nbIterations2nbWhitePixels[iterations]
      dist = abs(nbWhitePixels - nbWhitePixelsMax)
      if dist < minDist:
        minDist = dist
        best_iterations = iterations
    iterationsForErodeImageForHeadingCalculation = best_iterations
    hyperparameters["iterationsForErodeImageForHeadingCalculation"] = iterationsForErodeImageForHeadingCalculation
    
    maxDist = -1
    for i in range(0, nTries):
      angleOption = bestAngleAfterFirstStep - (math.pi / 5) + i * ((2 * (math.pi / 5)) / nTries)

      startPoint = (int(headPosition[0]), int(headPosition[1]))
      endPoint   = (int(headPosition[0] + 100000 * math.cos(angleOption)), int(headPosition[1] + 100000 * math.sin(angleOption)))
      testImage  = originalShape.copy()
      
      # applying dilation with the iterationsForErodeImageForHeadingCalculation value found
      testImage = cv2.erode(testImage, kernel, iterations = iterationsForErodeImageForHeadingCalculation)
      testImage  = cv2.line(testImage, startPoint, endPoint, (0), 1)
      nbWhitePixels = cv2.countNonZero(testImage)
      if nbWhitePixels < minWhitePixel:
        minWhitePixel = nbWhitePixels
        bestAngle     = angleOption
    
    # Finding the 'mouth' of the fish
    unitVector = np.array([math.cos(bestAngle + math.pi), math.sin(bestAngle + math.pi)])
    factor     = 1
    headPos    = np.array(headPosition)
    testBorder = headPos + factor * unitVector
    testBorder = testBorder.astype(int)
    while (cv2.pointPolygonTest(bodyContour, (testBorder[0], testBorder[1]), True) > 0) and (factor < 100) and (testBorder[0] >= 0) and (testBorder[1] >= 0) and (testBorder[0] < len(dst[0])) and (testBorder[1] < len(dst)):
      factor = factor + 1
      testBorder = headPos + factor * unitVector
    
    # Finding the indexes of the two "border points" along the contour (these are the two points that are the closest from the 'mouth' of fish)
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
      
    res = [indMin1, indMin2, bestAngle + math.pi]
    
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
    import zebrazoom.code.util as util

    cv2.circle(dst, (pt1[0],pt1[1]), 1, (0, 0, 255), -1)
    cv2.circle(dst, (pt2[0],pt2[1]), 1, (0, 0, 255), -1)
    util.showFrame(dst, title='Frame')
  
  return res
