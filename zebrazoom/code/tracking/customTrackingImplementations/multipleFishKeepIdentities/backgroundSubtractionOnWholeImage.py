from zebrazoom.code.tracking.customTrackingImplementations.fastFishTracking.detectMovementWithRawVideoInsideTracking import detectMovementWithRawVideoInsideTracking
from zebrazoom.code.tracking.customTrackingImplementations.fastFishTracking.utilities import calculateAngle
from zebrazoom.code.tracking.customTrackingImplementations.fastFishTracking.trackTail import trackTail
# import zebrazoom.code.tracking
import numpy as np
import random
import time
import math
import cv2

def backgroundSubtractionOnWholeImage(self, frame, k):

  # Color to grey scale transformation
  t1 = time.time()
  frame = frame[:,:,0]
  t2 = time.time()
  self._times2[k, 0] = t2 - t1
  if self._printInterTime:
    print("Color to grey", t2 - t1)
  
  # Subtracting background of image
  t1 = time.time()
  frame = 255 - np.where(self._background >= frame, self._background - frame, 0).astype(np.uint8)
  t2 = time.time()
  self._times2[k, 2] = t2 - t1
  if self._printInterTime:
    print("Background substraction", t2 - t1)
  
  # Applying gaussian filter
  t1 = time.time()
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
      
      if k <= 2:
        print("Normal tracking for frame:", k)
        for animalId in range(0, self._hyperparameters["nbAnimalsPerWell"]):
          # Head position tracking
          (minVal, maxVal, headPosition, maxLoc) = cv2.minMaxLoc(frameROI)
          self._trackingDataPerWell[wellNumber][animalId][k] = self._trackingDataPerWell[wellNumber][animalId][k-1]
          # Tail Tracking
          a, self._lastFirstTheta[wellNumber] = trackTail(self, frameROI, headPosition, self._hyperparameters, wellNumber, k, self._lastFirstTheta[wellNumber])
          self._trackingDataPerWell[wellNumber][animalId][k][:len(a[0])] = a
          # Heading calculation
          self._trackingHeadingDataPerWell[wellNumber][animalId][k] = (calculateAngle(self._trackingDataPerWell[wellNumber][animalId][k][0][0], self._trackingDataPerWell[wellNumber][animalId][k][0][1], self._trackingDataPerWell[wellNumber][animalId][k][1][0], self._trackingDataPerWell[wellNumber][animalId][k][1][1]) + math.pi) % (2 * math.pi)
          # 'Removing' animal just tracked
          cv2.circle(frameROI, (int(self._trackingDataPerWell[wellNumber][animalId][k][0][0]), int(self._trackingDataPerWell[wellNumber][animalId][k][0][1])), int(self._hyperparameters["maxDepth"]/4), (255, 255, 255), -1)
          for pointOnTail in range(1, len(self._trackingDataPerWell[wellNumber][animalId][k])):
            start_point = (int(self._trackingDataPerWell[wellNumber][animalId][k][pointOnTail-1][0]), int(self._trackingDataPerWell[wellNumber][animalId][k][pointOnTail-1][1]))
            end_point   = (int(self._trackingDataPerWell[wellNumber][animalId][k][pointOnTail][0]), int(self._trackingDataPerWell[wellNumber][animalId][k][pointOnTail][1]))
            cv2.line(frameROI, start_point, end_point, (255, 255, 255), int(self._hyperparameters["maxDepth"]/5))
      else:
        print("Multiple tracking good identities:", k)
        halfDiam = 20
        tickness = 8
        pixelMaximumVariation = 100
        headingMaximumVariation = 0.5
        pixelNumberOfTests = 5
        headingNumberOfTests = 5
        maxTotPixel = 0
        animalId1 = 0
        animalId2 = 1
        previousHeading1 = self._trackingHeadingDataPerWell[wellNumber][animalId1][k-1]
        previousHeading2 = self._trackingHeadingDataPerWell[wellNumber][animalId2][k-1]
        for pixelChange1 in range(-pixelMaximumVariation, pixelMaximumVariation, int((2 * pixelMaximumVariation) / pixelNumberOfTests)):
          plusOrMinus = [-1, 1][random.randint(0, 1)]
          
          center1X = self._trackingDataPerWell[wellNumber][animalId1][k-1][0][0] + [-1, 1][random.randint(0, 1)] * pixelChange1
          center1Y = self._trackingDataPerWell[wellNumber][animalId1][k-1][0][1] + [-1, 1][random.randint(0, 1)] * pixelChange1
          for headingOption1 in np.arange(previousHeading1 - headingMaximumVariation, previousHeading1 + headingMaximumVariation, (2 * headingMaximumVariation) / headingNumberOfTests):
            for pixelChange2 in range(-pixelMaximumVariation, pixelMaximumVariation, int((2 * pixelMaximumVariation) / pixelNumberOfTests)):
              center2X = self._trackingDataPerWell[wellNumber][animalId2][k-1][0][0] + [-1, 1][random.randint(0, 1)] * pixelChange2
              center2Y = self._trackingDataPerWell[wellNumber][animalId2][k-1][0][1] + [-1, 1][random.randint(0, 1)] * pixelChange2
              for headingOption2 in np.arange(previousHeading2 - headingMaximumVariation, previousHeading2 + headingMaximumVariation, (2 * headingMaximumVariation) / headingNumberOfTests):
                frameTest = frameROI.copy()
                start_point1 = (int(center1X + halfDiam * math.cos(headingOption1)), int(center1Y + halfDiam * math.sin(headingOption1)))
                end_point1   = (int(center1X - halfDiam * math.cos(headingOption1)), int(center1Y - halfDiam * math.sin(headingOption1)))
                cv2.line(frameTest, start_point1, end_point1, (255, 255, 255), tickness)
                start_point2 = (int(center2X + halfDiam * math.cos(headingOption2)), int(center2Y + halfDiam * math.sin(headingOption2)))
                end_point2   = (int(center2X - halfDiam * math.cos(headingOption2)), int(center2Y - halfDiam * math.sin(headingOption2)))
                cv2.line(frameTest, start_point2, end_point2, (255, 255, 255), tickness)
                tot = np.sum(np.sum(frameTest))
                if False:
                  print("Coord1:", start_point1, end_point1, " ; pixelChange1:", pixelChange1, "; headingOption1:", headingOption1)
                  print("Coord2:", start_point2, end_point2, " ; pixelChange2:", pixelChange2, "; headingOption2:", headingOption2)
                  print("tot:", tot)
                  import zebrazoom.code.util as util
                  util.showFrame(frameTest, title="Best")
                if tot > maxTotPixel:
                  maxTotPixel = tot
                  self._trackingDataPerWell[wellNumber][animalId1][k][0][0]  = center1X
                  self._trackingDataPerWell[wellNumber][animalId1][k][0][1]  = center1Y
                  self._trackingDataPerWell[wellNumber][animalId2][k][0][0]  = center2X
                  self._trackingDataPerWell[wellNumber][animalId2][k][0][1]  = center2Y
                  self._trackingHeadingDataPerWell[wellNumber][animalId1][k] = headingOption1
                  self._trackingHeadingDataPerWell[wellNumber][animalId2][k] = headingOption2
        
        if True:
          center1X = self._trackingDataPerWell[wellNumber][animalId1][k][0][0]
          center1Y = self._trackingDataPerWell[wellNumber][animalId1][k][0][1]
          center2X = self._trackingDataPerWell[wellNumber][animalId2][k][0][0]
          center2Y = self._trackingDataPerWell[wellNumber][animalId2][k][0][1]
          headingOption1 = self._trackingHeadingDataPerWell[wellNumber][animalId1][k]
          headingOption2 = self._trackingHeadingDataPerWell[wellNumber][animalId2][k]
          frameTest = frameROI.copy()
          start_point1 = (int(center1X + halfDiam * math.cos(headingOption1)), int(center1Y + halfDiam * math.sin(headingOption1)))
          end_point1   = (int(center1X - halfDiam * math.cos(headingOption1)), int(center1Y - halfDiam * math.sin(headingOption1)))
          cv2.line(frameTest, start_point1, end_point1, (255, 255, 255), tickness)
          start_point2 = (int(center2X + halfDiam * math.cos(headingOption2)), int(center2Y + halfDiam * math.sin(headingOption2)))
          end_point2   = (int(center2X - halfDiam * math.cos(headingOption2)), int(center2Y - halfDiam * math.sin(headingOption2)))
          cv2.line(frameTest, start_point2, end_point2, (255, 255, 255), tickness)
          print("start_point1:", start_point1)
          print("end_point1:", end_point1)
          print("start_point2:", start_point2)
          print("end_point2:", end_point2)
          import zebrazoom.code.util as util
          util.showFrame(frameTest, title="Best")
        
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