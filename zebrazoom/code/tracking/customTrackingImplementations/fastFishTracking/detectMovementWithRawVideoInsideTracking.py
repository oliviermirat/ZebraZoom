import numpy as np
import queue
import math
import cv2

def detectMovementWithRawVideoInsideTracking(self, i, grey):
  returnPreviousFrame = False
  if self._previousFrames is None:
    self._previousFrames = queue.Queue(self._hyperparameters["frameGapComparision"])
    self._auDessusPerAnimalIdList = [[np.zeros((self._lastFrame-self._firstFrame+1, 1)) for nbAnimalsPerWell in range(0, self._hyperparameters["nbAnimalsPerWell"])]
                                     for wellNumber in range(len(self._wellPositions))]
  halfDiameterRoiBoutDetect = self._hyperparameters["halfDiameterRoiBoutDetect"]
  if self._previousFrames.full():
    returnPreviousFrame = True
    previousFrame   = self._previousFrames.get()
    curFrame        = grey
    for wellNumber in self._listOfWellsOnWhichToRunTheTracking:
      for animal_Id in range(self._hyperparameters["nbAnimalsPerWell"]):
        headX = self._trackingDataPerWell[wellNumber][animal_Id][i-1][0][0]
        headY = self._trackingDataPerWell[wellNumber][animal_Id][i-1][0][1]
        xmin = headX - self._hyperparameters["halfDiameterRoiBoutDetect"]
        ymin = headY - self._hyperparameters["halfDiameterRoiBoutDetect"]
        xmax = xmin + 2 * self._hyperparameters["halfDiameterRoiBoutDetect"]
        ymax = ymin + 2 * self._hyperparameters["halfDiameterRoiBoutDetect"]
        lenX = self._wellPositions[wellNumber]['lengthX']
        lenY = self._wellPositions[wellNumber]['lengthY']
        if xmin < 0:
          xmin = 0
        if ymin < 0:
          ymin = 0
        if xmax > lenX - 1:
          xmax = lenX - 1
        if ymax > lenY - 1:
          ymax = lenY - 1
        if ymax < ymin:
          ymax = ymin + 2 * self._hyperparameters["halfDiameterRoiBoutDetect"]
        if xmax < xmin:
          xmax = xmin + 2 * self._hyperparameters["halfDiameterRoiBoutDetect"]
        if ( (xmin > lenX - 1) or (xmax < 0) ):
          xmin = 0
          xmax = 0 + lenX - 1
        if ( (ymin > lenY - 1) or (ymax < 0) ):
          ymin = 0
          ymax = 0 + lenY - 1
        xmin = int(xmin + self._wellPositions[wellNumber]['topLeftX'])
        xmax = int(xmax + self._wellPositions[wellNumber]['topLeftX'])
        ymin = int(ymin + self._wellPositions[wellNumber]['topLeftY'])
        ymax = int(ymax + self._wellPositions[wellNumber]['topLeftY'])
        subPreviousFrame = previousFrame[ymin:ymax, xmin:xmax].copy()
        subCurFrame      = curFrame[ymin:ymax, xmin:xmax].copy()

        res = cv2.absdiff(subPreviousFrame, subCurFrame)
        
        ret, res = cv2.threshold(res,self._hyperparameters["thresForDetectMovementWithRawVideo"],255,cv2.THRESH_BINARY)
        totDiff = cv2.countNonZero(res)

        if totDiff > self._hyperparameters["minNbPixelForDetectMovementWithRawVideo"]:
          self._auDessusPerAnimalIdList[wellNumber][animal_Id][i] = 1
        else:
          self._auDessusPerAnimalIdList[wellNumber][animal_Id][i] = 0
  
  else:
    
    for wellNumber in self._listOfWellsOnWhichToRunTheTracking:
      for animalId in range(0, self._hyperparameters["nbAnimalsPerWell"]):
        self._auDessusPerAnimalIdList[wellNumber][animalId][i] = 0 # Need to improve this part
  
  self._previousFrames.put(grey)
  
  if returnPreviousFrame:
    return previousFrame
  else:
    return grey
