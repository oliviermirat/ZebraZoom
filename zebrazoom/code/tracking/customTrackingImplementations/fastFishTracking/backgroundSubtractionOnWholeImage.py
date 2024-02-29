from zebrazoom.code.tracking.customTrackingImplementations.fastFishTracking.detectMovementWithRawVideoInsideTracking import detectMovementWithRawVideoInsideTracking
from zebrazoom.code.tracking.customTrackingImplementations.fastFishTracking.trackTail import trackTail
from zebrazoom.code.tracking.customTrackingImplementations.fastFishTracking.removeAnimalJustTrackedFromFrame import removeAnimalJustTrackedFromFrame
# import zebrazoom.code.tracking
import numpy as np
import time
import math
import cv2

def backgroundSubtractionOnWholeImage(self, frame, k):
  unprocessedFrame = frame

  # Color to grey scale transformation
  t1 = time.time()
  if type(frame[0][0]) == np.ndarray:
    frame = frame[:,:,0]
  t2 = time.time()
  self._times2[k, 0] = t2 - t1
  if self._printInterTime:
    print("Color to grey", t2 - t1)
  
  # Bout detection
  if self._hyperparameters["detectMovementWithRawVideoInsideTracking"]:
    t1 = time.time()
    prevFrame = detectMovementWithRawVideoInsideTracking(self, k, frame)
    if ("detectMovementCompareWithTheFuture" in self._hyperparameters) and self._hyperparameters["detectMovementCompareWithTheFuture"]:
      frame = prevFrame
    t2 = time.time()
    self._times2[k, 1] = t2 - t1
    if self._printInterTime:
      print("Bout detection", t2 - t1)
  
  # Subtracting background of image
  t1 = time.time()
  if not("noBackgroundSubtraction" in self._hyperparameters) or not(self._hyperparameters["noBackgroundSubtraction"]):
    frame = 255 - np.where(self._background >= frame, self._background - frame, 0).astype(np.uint8)
  t2 = time.time()
  self._times2[k, 2] = t2 - t1
  if self._printInterTime:
    print("Background substraction", t2 - t1)
  
  # Applying gaussian filter
  t1 = time.time()
  if ("paramGaussianBlurForHeadPosition" in self._hyperparameters) and self._hyperparameters["paramGaussianBlurForHeadPosition"]:
    frameGaussianBlurForHeadPosition = frame.copy()
    frameGaussianBlurForHeadPosition = cv2.GaussianBlur(frameGaussianBlurForHeadPosition, (self._hyperparameters["paramGaussianBlurForHeadPosition"], self._hyperparameters["paramGaussianBlurForHeadPosition"]), 0)
  paramGaussianBlur = self._hyperparameters["paramGaussianBlur"]
  frame = cv2.GaussianBlur(frame, (paramGaussianBlur, paramGaussianBlur), 0)
  t2 = time.time()
  self._times2[k, 3] = t2 - t1
  if self._printInterTime:
    print("Gaussian blur:", t2 - t1)
  
  # Going through each well/arena/tank and applying tracking method on it
  t1 = time.time()
  for wellNumber in self._listOfWellsOnWhichToRunTheTracking:
    
    if self._hyperparameters["detectMovementWithRawVideoInsideTracking"] == 0 or k <= 2 or np.sum([self._auDessusPerAnimalIdList[wellNumber][i][k] for i in range(0, self._hyperparameters["nbAnimalsPerWell"])]):
    
      # Retrieving well/tank/arena coordinates and selecting ROI
      wellXtop = self._wellPositions[wellNumber]['topLeftX']
      wellYtop = self._wellPositions[wellNumber]['topLeftY']
      lenghtWell_X = self._wellPositions[wellNumber]['lengthX']
      lenghtWell_Y = self._wellPositions[wellNumber]['lengthY']
      frameROI = frame[wellYtop:wellYtop+lenghtWell_Y, wellXtop:wellXtop+lenghtWell_X]
      unprocessedFrameROI = unprocessedFrame[wellYtop:wellYtop+lenghtWell_Y, wellXtop:wellXtop+lenghtWell_X]
      unmodifiedFrameROI = frameROI.copy()
      
      for animalId in range(0, self._hyperparameters["nbAnimalsPerWell"]):
        
        if self._hyperparameters["detectMovementWithRawVideoInsideTracking"] == 0 or self._auDessusPerAnimalIdList[wellNumber][animalId][k] or k <= 2:
          
          # Head position tracking
          if ("paramGaussianBlurForHeadPosition" in self._hyperparameters) and self._hyperparameters["paramGaussianBlurForHeadPosition"]:
            (minVal, maxVal, headPosition, maxLoc) = cv2.minMaxLoc(frameGaussianBlurForHeadPosition)
          else:
            (minVal, maxVal, headPosition, maxLoc) = cv2.minMaxLoc(frameROI)

          if minVal >= self._hyperparameters["minimumHeadPixelValue"] or (("readEventBasedData" in self._hyperparameters) and self._hyperparameters["readEventBasedData"]):
            self._trackingDataPerWell[wellNumber][animalId][k] = self._trackingDataPerWell[wellNumber][animalId][k-1]
          else:
            if self._hyperparameters["trackTail"]:
              # Tail tracking
              a, self._lastFirstTheta[wellNumber] = trackTail(self, frameROI, headPosition, self._hyperparameters, wellNumber, k, self._lastFirstTheta[wellNumber])
              self._trackingDataPerWell[wellNumber][animalId][k][:len(a[0])] = a
            else:
              self._trackingDataPerWell[wellNumber][animalId][k] = np.array([[headPosition]])
        else:
          if k > 0:
            self._trackingDataPerWell[wellNumber][animalId][k] = self._trackingDataPerWell[wellNumber][animalId][k-1]
        
        # 'Removing' animal just tracked
        if self._hyperparameters["nbAnimalsPerWell"] > 1:
          if "largerPixelRemoval" in self._hyperparameters and self._hyperparameters["largerPixelRemoval"]:
            cv2.circle(frameROI, (int(self._trackingDataPerWell[wellNumber][animalId][k][0][0]), int(self._trackingDataPerWell[wellNumber][animalId][k][0][1])), int(self._hyperparameters["maxDepth"]/3), (255, 255, 255), -1)
            for pointOnTail in range(1, len(self._trackingDataPerWell[wellNumber][animalId][k])):
              start_point = (int(self._trackingDataPerWell[wellNumber][animalId][k][pointOnTail-1][0]), int(self._trackingDataPerWell[wellNumber][animalId][k][pointOnTail-1][1]))
              end_point   = (int(self._trackingDataPerWell[wellNumber][animalId][k][pointOnTail][0]), int(self._trackingDataPerWell[wellNumber][animalId][k][pointOnTail][1]))
              if pointOnTail == 1:
                end_point   = (int(3 * self._trackingDataPerWell[wellNumber][animalId][k][pointOnTail-1][0] - 2 * self._trackingDataPerWell[wellNumber][animalId][k][pointOnTail][0]), int(3 * self._trackingDataPerWell[wellNumber][animalId][k][pointOnTail-1][1] - 2 * self._trackingDataPerWell[wellNumber][animalId][k][pointOnTail][1]))
              if pointOnTail == len(self._trackingDataPerWell[wellNumber][animalId][k]) - 1:
                end_point   = (int(2 * self._trackingDataPerWell[wellNumber][animalId][k][pointOnTail][0] - self._trackingDataPerWell[wellNumber][animalId][k][pointOnTail-1][0]), int(2 * self._trackingDataPerWell[wellNumber][animalId][k][pointOnTail][1] - self._trackingDataPerWell[wellNumber][animalId][k][pointOnTail-1][1]))
              cv2.line(frameROI, start_point, end_point, (255, 255, 255), max(min(int(self._hyperparameters["maxDepth"]/3), 32), 1))
          else:
            cv2.circle(frameROI, (int(self._trackingDataPerWell[wellNumber][animalId][k][0][0]), int(self._trackingDataPerWell[wellNumber][animalId][k][0][1])), int(self._hyperparameters["maxDepth"]/4), (255, 255, 255), -1)
            for pointOnTail in range(1, len(self._trackingDataPerWell[wellNumber][animalId][k])):
              start_point = (int(self._trackingDataPerWell[wellNumber][animalId][k][pointOnTail-1][0]), int(self._trackingDataPerWell[wellNumber][animalId][k][pointOnTail-1][1]))
              end_point   = (int(self._trackingDataPerWell[wellNumber][animalId][k][pointOnTail][0]), int(self._trackingDataPerWell[wellNumber][animalId][k][pointOnTail][1]))
              cv2.line(frameROI, start_point, end_point, (255, 255, 255), max(min(int(self._hyperparameters["maxDepth"]/5), 32), 1))
          if ("paramGaussianBlurForHeadPosition" in self._hyperparameters) and self._hyperparameters["paramGaussianBlurForHeadPosition"]:
            frameGaussianBlurForHeadPosition = removeAnimalJustTrackedFromFrame(self, frameGaussianBlurForHeadPosition, wellNumber, animalId, k)
      
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
  
  t2 = time.time()
  self._times2[k, 4] = t2 - t1
  if self._printInterTime:
    print("Tracking on each well:", t2 - t1)
  if self._hyperparameters['adjustFreelySwimTracking']:
    return unmodifiedFrameROI, unprocessedFrameROI
  return None, None
