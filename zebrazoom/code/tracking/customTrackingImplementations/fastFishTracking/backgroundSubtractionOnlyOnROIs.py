from zebrazoom.code.tracking.customTrackingImplementations.fastFishTracking.detectMovementWithRawVideoInsideTracking import detectMovementWithRawVideoInsideTracking
from zebrazoom.code.tracking.customTrackingImplementations.fastFishTracking.trackTail import trackTail
# import zebrazoom.code.tracking
import numpy as np
import time
import math
import cv2

def backgroundSubtractionOnlyOnROIs(self, frame, k):

  # Color to grey scale transformation
  frame = frame[:,:,0]
  
  # Bout detection
  if self._hyperparameters["detectMovementWithRawVideoInsideTracking"]:
    detectMovementWithRawVideoInsideTracking(self, k, frame)
  
  # Going through each well/arena/tank and applying tracking method on it
  t1 = time.time()
  for wellNumber in self._listOfWellsOnWhichToRunTheTracking:
    
    if self._hyperparameters["detectMovementWithRawVideoInsideTracking"] == 0 or k <= 2 or np.sum([self._auDessusPerAnimalIdList[wellNumber][i][k] for i in range(0, self._hyperparameters["nbAnimalsPerWell"])]):
      
      for animalId in range(0, self._hyperparameters["nbAnimalsPerWell"]):
        
        if self._hyperparameters["detectMovementWithRawVideoInsideTracking"] == 0 or self._auDessusPerAnimalIdList[wellNumber][animalId][k] or k <= 2:
          
          # Retrieving ROI coordinates and selecting ROI
          roiXStart = self._wellPositions[wellNumber]['topLeftX'] + int(self._trackingDataPerWell[wellNumber][animalId][k-1][0][0] - self._hyperparameters["backgroundSubtractionOnROIhalfDiameter"])
          roiYStart = self._wellPositions[wellNumber]['topLeftY'] + int(self._trackingDataPerWell[wellNumber][animalId][k-1][0][1] - self._hyperparameters["backgroundSubtractionOnROIhalfDiameter"])
          roiXEnd   = roiXStart + 2 * self._hyperparameters["backgroundSubtractionOnROIhalfDiameter"]
          roiYEnd   = roiYStart + 2 * self._hyperparameters["backgroundSubtractionOnROIhalfDiameter"]
          if roiXStart < 0:
            roiXStart = 0
            roiXEnd   = 2 * self._hyperparameters["backgroundSubtractionOnROIhalfDiameter"]
          if roiYStart < 0:
            roiYStart = 0
            roiYEnd   = 2 * self._hyperparameters["backgroundSubtractionOnROIhalfDiameter"]
          if roiXEnd >= len(frame[0]):
            roiXEnd   = len(frame[0]) - 1
            roiXStart = len(frame[0]) - 2 * self._hyperparameters["backgroundSubtractionOnROIhalfDiameter"]
          if roiYEnd >= len(frame):
            roiYEnd   = len(frame) - 1
            roiYStart = len(frame) - 2 * self._hyperparameters["backgroundSubtractionOnROIhalfDiameter"]
          frameROI = frame[roiYStart:roiYEnd, roiXStart:roiXEnd].copy()
          
          # Subtracting background of image
          backgroundROI = self._background[roiYStart:roiYEnd, roiXStart:roiXEnd]
          frameROI = 255 - np.where(backgroundROI >= frameROI, backgroundROI - frameROI, 0).astype(np.uint8)

          # Applying gaussian filter
          paramGaussianBlur = self._hyperparameters["paramGaussianBlur"]
          frameROI = cv2.GaussianBlur(frameROI, (paramGaussianBlur, paramGaussianBlur), 0)
          
          # Head position tracking
          (minVal, maxVal, headPosition, maxLoc) = cv2.minMaxLoc(frameROI)
          if minVal >= self._hyperparameters["minimumHeadPixelValue"]:
            self._trackingDataPerWell[wellNumber][animalId][k] = self._trackingDataPerWell[wellNumber][animalId][k-1]
          else:
            if self._hyperparameters["trackTail"]:
              # Tail tracking
              a, self._lastFirstTheta[wellNumber] = trackTail(self, frameROI, headPosition, self._hyperparameters, wellNumber, k, self._lastFirstTheta[wellNumber])
              a[0, :, 0] += roiXStart - self._wellPositions[wellNumber]['topLeftX']
              a[0, :, 1] += roiYStart - self._wellPositions[wellNumber]['topLeftY']
              self._trackingDataPerWell[wellNumber][animalId][k][:len(a[0])] = a
            else:
              self._trackingDataPerWell[wellNumber][animalId][k][0][0] = headPosition[0] + roiXStart - self._wellPositions[wellNumber]['topLeftX']
              self._trackingDataPerWell[wellNumber][animalId][k][0][1] = headPosition[1] + roiYStart - self._wellPositions[wellNumber]['topLeftY']
        else:
          if k > 0:
            self._trackingDataPerWell[wellNumber][animalId][k] = self._trackingDataPerWell[wellNumber][animalId][k-1]
        
        # 'Removing' animal just tracked
        if self._hyperparameters["nbAnimalsPerWell"] > 1:
          frame = cv2.circle(frame.copy(), (int(self._wellPositions[wellNumber]['topLeftX'] + self._trackingDataPerWell[wellNumber][animalId][k][0][0]), int(self._wellPositions[wellNumber]['topLeftY'] + self._trackingDataPerWell[wellNumber][animalId][k][0][1])), int(self._hyperparameters["maxDepth"]/4), (255, 255, 255), -1)
          for pointOnTail in range(1, len(self._trackingDataPerWell[wellNumber][animalId][k])):
            start_point = (int(self._wellPositions[wellNumber]['topLeftX'] + self._trackingDataPerWell[wellNumber][animalId][k][pointOnTail-1][0]), int(self._wellPositions[wellNumber]['topLeftY'] + self._trackingDataPerWell[wellNumber][animalId][k][pointOnTail-1][1]))
            end_point   = (int(self._wellPositions[wellNumber]['topLeftX'] + self._trackingDataPerWell[wellNumber][animalId][k][pointOnTail][0]), int(self._wellPositions[wellNumber]['topLeftY'] + self._trackingDataPerWell[wellNumber][animalId][k][pointOnTail][1]))
            cv2.line(frame, start_point, end_point, (255, 255, 255), int(self._hyperparameters["maxDepth"]/5))
        
      # Id invertion if necessary
      if self._hyperparameters["nbAnimalsPerWell"] > 1:
        # NEED TO IMPROVE THIS IN THE FUTURE!!!
        for animalId in range(0, self._hyperparameters["nbAnimalsPerWell"]-1):
          dist_animalIdCurFrame_animal0PrevFrame = math.sqrt((self._trackingDataPerWell[wellNumber][animalId][k][0][0] - self._trackingDataPerWell[wellNumber][0][k-1][0][0])**2     +     (self._trackingDataPerWell[wellNumber][animalId][k][0][1] - self._trackingDataPerWell[wellNumber][0][k-1][0][1])**2)
          dist_animalIdCurFrame_animal1PrevFrame = math.sqrt((self._trackingDataPerWell[wellNumber][animalId][k][0][0] - self._trackingDataPerWell[wellNumber][1][k-1][0][0])**2     +     (self._trackingDataPerWell[wellNumber][animalId][k][0][1] - self._trackingDataPerWell[wellNumber][1][k-1][0][1])**2)
          if dist_animalIdCurFrame_animal1PrevFrame < dist_animalIdCurFrame_animal0PrevFrame:
            temp = self._trackingDataPerWell[wellNumber][0][k].copy()
            self._trackingDataPerWell[wellNumber][0][k] = self._trackingDataPerWell[wellNumber][1][k]
            self._trackingDataPerWell[wellNumber][1][k] = temp
    else:  
      for animalId in range(0, self._hyperparameters["nbAnimalsPerWell"]):
        self._trackingDataPerWell[wellNumber][animalId][k] = self._trackingDataPerWell[wellNumber][animalId][k-1]