import numpy as np
import queue
import math
import cv2

def getListOfWellsOnWhichToRunTheTracking(self, frame1, frame2):
  
  listOfWellsOnWhichToRunTheTracking = []
  
  for wellNumber in range(0, len(self._wellPositions)):
  
    # Retrieving well/tank/arena coordinates and selecting ROI
    wellXtop = self._wellPositions[wellNumber]['topLeftX']
    wellYtop = self._wellPositions[wellNumber]['topLeftY']
    lenghtWell_X = self._wellPositions[wellNumber]['lengthX']
    lenghtWell_Y = self._wellPositions[wellNumber]['lengthY']
    frameROI1 = frame1[wellYtop:wellYtop+lenghtWell_Y, wellXtop:wellXtop+lenghtWell_X]
    frameROI2 = frame2[wellYtop:wellYtop+lenghtWell_Y, wellXtop:wellXtop+lenghtWell_X]
    
    res = cv2.absdiff(frameROI1, frameROI2)
    ret, res = cv2.threshold(res,self._hyperparameters["thresForDetectMovementWithRawVideo"],255,cv2.THRESH_BINARY)
    totDiff = cv2.countNonZero(res)
    
    if totDiff > self._hyperparameters["minNbPixelForDetectMovementInWell"]:
      listOfWellsOnWhichToRunTheTracking.append(wellNumber)
    
  return listOfWellsOnWhichToRunTheTracking
