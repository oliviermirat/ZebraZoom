from zebrazoom.code.tracking.customTrackingImplementations.fastFishTracking.detectMovementWithRawVideoInsideTracking import detectMovementWithRawVideoInsideTracking
from zebrazoom.code.tracking.customTrackingImplementations.fastFishTracking.trackTail import trackTail
from zebrazoom.code.tracking.customTrackingImplementations.fastFishTracking.animalDetectionBackToWholeImage import animalDetectionBackToWholeImage
from zebrazoom.code.tracking.customTrackingImplementations.fastFishTracking.removeAnimalJustTrackedFromFrame import removeAnimalJustTrackedFromFrame
# import zebrazoom.code.tracking
import numpy as np
import time
import math
import cv2

def backgroundSubtractionOnlyOnROIs(self, frame, k):
  
  # Color to grey scale transformation
  if type(frame[0][0]) == np.ndarray:
    frame = frame[:,:,0]
  
  # Bout detection
  if self._hyperparameters["detectMovementWithRawVideoInsideTracking"]:
    prevFrame = detectMovementWithRawVideoInsideTracking(self, k, frame)
    if ("detectMovementCompareWithTheFuture" in self._hyperparameters) and self._hyperparameters["detectMovementCompareWithTheFuture"]:
      frame = prevFrame
  
  if ("paramGaussianBlurForHeadPosition" in self._hyperparameters) and self._hyperparameters["paramGaussianBlurForHeadPosition"]:
    frameGaussianBlurForHeadPosition = frame.copy()
  
  # Going through each well/arena/tank and applying tracking method on it
  t1 = time.time()
  for wellNumber in self._listOfWellsOnWhichToRunTheTracking:
    
    if self._hyperparameters["detectMovementWithRawVideoInsideTracking"] == 0 or k <= 2 or np.sum([self._auDessusPerAnimalIdList[wellNumber][i][k] for i in range(0, self._hyperparameters["nbAnimalsPerWell"])]):
      
      animalNotTracked = np.zeros((self._hyperparameters["nbAnimalsPerWell"]))
      
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
          if ("paramGaussianBlurForHeadPosition" in self._hyperparameters) and self._hyperparameters["paramGaussianBlurForHeadPosition"]:
            frameGaussianBlurForHeadPositionROI = frameGaussianBlurForHeadPosition[roiYStart:roiYEnd, roiXStart:roiXEnd].copy()
          
          # Subtracting background of image
          if not("noBackgroundSubtraction" in self._hyperparameters) or not(self._hyperparameters["noBackgroundSubtraction"]):
            backgroundROI = self._background[roiYStart:roiYEnd, roiXStart:roiXEnd]
            frameROI = 255 - np.where(backgroundROI >= frameROI, backgroundROI - frameROI, 0).astype(np.uint8)
            if ("paramGaussianBlurForHeadPosition" in self._hyperparameters) and self._hyperparameters["paramGaussianBlurForHeadPosition"]:
              frameGaussianBlurForHeadPositionROI = 255 - np.where(backgroundROI >= frameGaussianBlurForHeadPositionROI, backgroundROI - frameGaussianBlurForHeadPositionROI, 0).astype(np.uint8)

          # Applying gaussian filter
          paramGaussianBlur = self._hyperparameters["paramGaussianBlur"]
          frameROI = cv2.GaussianBlur(frameROI, (paramGaussianBlur, paramGaussianBlur), 0)
          if ("paramGaussianBlurForHeadPosition" in self._hyperparameters) and self._hyperparameters["paramGaussianBlurForHeadPosition"]:
            frameGaussianBlurForHeadPositionROI = cv2.GaussianBlur(frameGaussianBlurForHeadPositionROI, (self._hyperparameters["paramGaussianBlurForHeadPosition"], self._hyperparameters["paramGaussianBlurForHeadPosition"]), 0)
          
          # Head position tracking
          if ("paramGaussianBlurForHeadPosition" in self._hyperparameters) and self._hyperparameters["paramGaussianBlurForHeadPosition"]:
            (minVal, maxVal, headPosition, maxLoc) = cv2.minMaxLoc(frameGaussianBlurForHeadPositionROI)
          else:
            (minVal, maxVal, headPosition, maxLoc) = cv2.minMaxLoc(frameROI)
          if minVal >= self._hyperparameters["minimumHeadPixelValue"]:
            self._trackingDataPerWell[wellNumber][animalId][k] = self._trackingDataPerWell[wellNumber][animalId][k-1]
            animalNotTracked[animalId] = 1
          else:
            if self._hyperparameters["trackTail"]:
              # Tail tracking
              a, self._lastFirstTheta[wellNumber] = trackTail(self, frameROI, headPosition, self._hyperparameters, wellNumber, k, self._lastFirstTheta[wellNumber])
              if len(a):
                a[0, :, 0] += roiXStart - self._wellPositions[wellNumber]['topLeftX']
                a[0, :, 1] += roiYStart - self._wellPositions[wellNumber]['topLeftY']
                self._trackingDataPerWell[wellNumber][animalId][k][:len(a[0])] = a
              else:
                self._trackingDataPerWell[wellNumber][animalId][k] = self._trackingDataPerWell[wellNumber][animalId][k-1]
                animalNotTracked[animalId] = 1
            else:
              self._trackingDataPerWell[wellNumber][animalId][k][0][0] = headPosition[0] + roiXStart - self._wellPositions[wellNumber]['topLeftX']
              self._trackingDataPerWell[wellNumber][animalId][k][0][1] = headPosition[1] + roiYStart - self._wellPositions[wellNumber]['topLeftY']
        else:
          if k > 0:
            animalNotTracked[animalId] = 1
            self._trackingDataPerWell[wellNumber][animalId][k] = self._trackingDataPerWell[wellNumber][animalId][k-1]
        
        # 'Removing' animal just tracked
        if self._hyperparameters["nbAnimalsPerWell"] > 1:
          frame = removeAnimalJustTrackedFromFrame(self, frame, wellNumber, animalId, k)
          if ("paramGaussianBlurForHeadPosition" in self._hyperparameters) and self._hyperparameters["paramGaussianBlurForHeadPosition"]:
            frameGaussianBlurForHeadPosition = removeAnimalJustTrackedFromFrame(self, frameGaussianBlurForHeadPosition, wellNumber, animalId, k)
      
      if "animalDetectionBackToWholeImage" in self._hyperparameters and self._hyperparameters["animalDetectionBackToWholeImage"] and np.sum(animalNotTracked):
        animalDetectionBackToWholeImage(self, k, frame, wellNumber, animalNotTracked)
            
      # Id invertion if necessary
      if self._hyperparameters["nbAnimalsPerWell"] > 1 and False:
        # NEED TO IMPROVE THIS IN THE FUTURE!!!
        for animalId in range(0, self._hyperparameters["nbAnimalsPerWell"]-1):
          dist_animalIdCurFrame_animal0PrevFrame = math.sqrt((self._trackingDataPerWell[wellNumber][animalId][k][0][0] - self._trackingDataPerWell[wellNumber][0][k-1][0][0])**2     +     (self._trackingDataPerWell[wellNumber][animalId][k][0][1] - self._trackingDataPerWell[wellNumber][0][k-1][0][1])**2)
          dist_animalIdCurFrame_animal1PrevFrame = math.sqrt((self._trackingDataPerWell[wellNumber][animalId][k][0][0] - self._trackingDataPerWell[wellNumber][1][k-1][0][0])**2     +     (self._trackingDataPerWell[wellNumber][animalId][k][0][1] - self._trackingDataPerWell[wellNumber][1][k-1][0][1])**2)
          if dist_animalIdCurFrame_animal1PrevFrame < dist_animalIdCurFrame_animal0PrevFrame:
            temp = self._trackingDataPerWell[wellNumber][0][k].copy()
            self._trackingDataPerWell[wellNumber][0][k] = self._trackingDataPerWell[wellNumber][1][k]
            self._trackingDataPerWell[wellNumber][1][k] = temp
      
      # Checking for superimposed tracking, removing them if necessary
      if ("checkAndRemoveSuperimposedTrackingIfPresent_minDistance" in self._hyperparameters) and (self._hyperparameters["checkAndRemoveSuperimposedTrackingIfPresent_minDistance"] != 0):
        for animalId1 in range(0, self._hyperparameters["nbAnimalsPerWell"]-1):
          for animalId2 in range(animalId1 + 1, self._hyperparameters["nbAnimalsPerWell"]):
            min_distBetweenTwoPointsOfAnimals = 10000000000000000000000
            for p1 in range(len(self._trackingDataPerWell[wellNumber][animalId1][k])):
              for p2 in range(len(self._trackingDataPerWell[wellNumber][animalId2][k])):
                distBetweenTwoPointsOfAnimals = math.sqrt((self._trackingDataPerWell[wellNumber][animalId1][k][p1][0] - self._trackingDataPerWell[wellNumber][animalId2][k][p2][0])**2   +   (self._trackingDataPerWell[wellNumber][animalId1][k][p1][1] - self._trackingDataPerWell[wellNumber][animalId2][k][p2][1])**2)
                if distBetweenTwoPointsOfAnimals < min_distBetweenTwoPointsOfAnimals:
                  min_distBetweenTwoPointsOfAnimals = distBetweenTwoPointsOfAnimals
            if min_distBetweenTwoPointsOfAnimals < self._hyperparameters["checkAndRemoveSuperimposedTrackingIfPresent_minDistance"]:
              # randomly choosing to remove animalId1, in the future should better choose which one to remove
              for p1 in range(len(self._trackingDataPerWell[wellNumber][animalId1][k])):
                self._trackingDataPerWell[wellNumber][animalId1][k][p1][0] = 0
                self._trackingDataPerWell[wellNumber][animalId1][k][p1][1] = 0
    else:  
      for animalId in range(0, self._hyperparameters["nbAnimalsPerWell"]):
        self._trackingDataPerWell[wellNumber][animalId][k] = self._trackingDataPerWell[wellNumber][animalId][k-1]