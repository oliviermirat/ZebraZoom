import numpy as np
import cv2
from zebrazoom.code.trackingFolder.tailTrackingFunctionsFolder.tailTrackingExtremityDetectFolder.getMidline import getMidline
import math

def checkIfMidlineIsInBlob(headX, headY, pointAlongTheTail, bodyContour, dst, size, distance2, debugAdv, hyperparameters, nbTailPoints):

  tail = getMidline(headX, headY, pointAlongTheTail, bodyContour, dst, size, distance2, debugAdv, hyperparameters, nbTailPoints)
  
  tail2 = tail[0]
  n = len(tail2)
  allMidlinePointsInsideBlob = True
  for j in range(0, n):
    dist = cv2.pointPolygonTest(bodyContour,(tail2[j][0],tail2[j][1]),False)
    if dist < 0:
      allMidlinePointsInsideBlob = False
  
  tailLength = 0
  if allMidlinePointsInsideBlob:
    for j in range(0, n-1):
      tailLength = tailLength + math.sqrt( pow(tail2[j,0]-tail2[j+1,0], 2) + pow(tail2[j,1]-tail2[j+1,1], 2) )
  
  return [allMidlinePointsInsideBlob, tailLength]