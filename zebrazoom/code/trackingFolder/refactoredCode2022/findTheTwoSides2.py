import numpy as np
import math
import cv2

def findTheTwoSides2(headPosition, bodyContour, curFrame, hyperparameters, bestAngle):
  
  # Finding the 'mouth' of the fish
  unitVector = np.array([math.cos(bestAngle), math.sin(bestAngle)])
  factor     = 1
  headPos    = np.array(headPosition)
  testBorder = headPos + factor * unitVector
  testBorder = testBorder.astype(int)
  while (cv2.pointPolygonTest(bodyContour, (testBorder[0], testBorder[1]), True) > 0) and (factor < 100) and (testBorder[0] >= 0) and (testBorder[1] >= 0) and (testBorder[0] < len(curFrame[0])) and (testBorder[1] < len(curFrame)):
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
  
  res = [indMin1, indMin2]
  
  return res