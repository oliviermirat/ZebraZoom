from zebrazoom.code.tracking.customTrackingImplementations.fastFishTracking.trackTail import trackTail
from zebrazoom.code.tracking.customTrackingImplementations.fastFishTracking.getNewFrameROI import getNewFrameROI
from zebrazoom.code.tracking.customTrackingImplementations.fastFishTracking.removeAnimalJustTrackedFromFrame import removeAnimalJustTrackedFromFrame
import numpy as np
import cv2

def animalDetectionBackToWholeImage(self, k, frame, wellNumber, animalNotTracked):
  
  listOfAnimalIds = []
  for i in range(len(animalNotTracked)):
    if animalNotTracked[i]:
      if self._trackingDataPerWell[wellNumber][i][k-1][0][0] == 0 and self._trackingDataPerWell[wellNumber][i][k-1][0][1] == 0:
        listOfAnimalIds = [i] + listOfAnimalIds
      else:
        listOfAnimalIds.append(i)
  
  curIdInListOfAnimalIds = 0
  for i in range(len(animalNotTracked)):
    if animalNotTracked[i]:
      
      # Animal Id selection
      animalId = listOfAnimalIds[curIdInListOfAnimalIds]
      curIdInListOfAnimalIds += 1
      
      # Frame ROI selection
      wellXtop = self._wellPositions[wellNumber]['topLeftX']
      wellYtop = self._wellPositions[wellNumber]['topLeftY']
      lenghtWell_X = self._wellPositions[wellNumber]['lengthX']
      lenghtWell_Y = self._wellPositions[wellNumber]['lengthY']
      frameROI = frame[wellYtop:wellYtop+lenghtWell_Y, wellXtop:wellXtop+lenghtWell_X]
      
      # Applying gaussian filter
      paramGaussianBlur = self._hyperparameters["paramGaussianBlur"]
      frameROI = cv2.GaussianBlur(frameROI, (paramGaussianBlur, paramGaussianBlur), 0)
      
      # Tracking
      (minVal, maxVal, headPosition, maxLoc) = cv2.minMaxLoc(frameROI)
      if not(minVal >= self._hyperparameters["minimumHeadPixelValue"]):
        a, self._lastFirstTheta[wellNumber] = trackTail(self, frameROI, headPosition, self._hyperparameters, wellNumber, k, self._lastFirstTheta[wellNumber])
        if len(a):
          a[0, :, 0] -= self._wellPositions[wellNumber]['topLeftX']
          a[0, :, 1] -= self._wellPositions[wellNumber]['topLeftY']

          self._trackingDataPerWell[wellNumber][animalId][k][:len(a[0])] = a
          
          frameROI = getNewFrameROI(self, k, frame, wellNumber, animalId)
          
          if np.sum(np.sum(255 - frameROI)) < self._hyperparameters["minimumPixelIntensitySumForAnimalDetection"]:
            
            self._trackingDataPerWell[wellNumber][animalId][k] = self._trackingDataPerWell[wellNumber][animalId][k-1]
          
          else:
          
            # 'Removing' animal just tracked
            if self._hyperparameters["nbAnimalsPerWell"] > 1:
              frame = removeAnimalJustTrackedFromFrame(self, frame, wellNumber, animalId, k)