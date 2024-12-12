import math
import cv2
import numpy as np


def _headTrackingHeadingCalculation(self, i, blur, thresh1, thresh2, frameOri, erodeSize, frame_width, frame_height, trackingHeadingAllAnimals, trackingHeadTailAllAnimals, trackingProbabilityOfGoodDetection, headPosition, lengthX, xmin=0, ymin=0, wellNumber=-1, oldFrameList=[]):
  xHB_TN = 0
  heading = 0
  x = 0
  y = 0
  lastFirstTheta = 0

  # Finds head position for frame i
  takeTheHeadClosestToTheCenter = self._hyperparameters["takeTheHeadClosestToTheCenter"]
  
  (minVal, maxVal, headPosition, maxLoc) = cv2.minMaxLoc(blur)
  
  if "localMinimumDarkestThreshold" in self._hyperparameters and self._hyperparameters["localMinimumDarkestThreshold"]:
    localMinimumDarkestThreshold = int(self._hyperparameters["localMinimumDarkestThreshold"])
  else:
    localMinimumDarkestThreshold = 180
  
  for animalNumber in range(self._hyperparameters["nbAnimalsPerWell"]):
    
    if minVal < localMinimumDarkestThreshold:
      
      if type(trackingProbabilityOfGoodDetection) != int and len(trackingProbabilityOfGoodDetection) and i-self._firstFrame < len(trackingProbabilityOfGoodDetection[0]):
        trackingProbabilityOfGoodDetection[0, i-self._firstFrame] = np.sum(255 - blur)

      x = headPosition[0]
      y = headPosition[1]

      if type(headPosition) == tuple:
        headPosition = list(headPosition)
        headPosition[0] = headPosition[0] + xmin
        headPosition[1] = headPosition[1] + ymin
        headPosition = tuple(headPosition)
      else:
        headPosition[0] = headPosition[0] + xmin
        headPosition[1] = headPosition[1] + ymin

      # Calculate heading for frame i
      if type(thresh1) != int:
        [heading, lastFirstTheta] = self._calculateHeading(x, y, i, thresh1, thresh2, takeTheHeadClosestToTheCenter, 0, wellNumber)
      
      okAll = True
      if "removeShades" in self._hyperparameters and self._hyperparameters["removeShades"]:
        if i > 110:
          for oldFrame in oldFrameList:
            compareDarknestWithThePastWindow = int(self._hyperparameters["headSize"] / 2) if int(self._hyperparameters["headSize"] / 2) >= 2 else 2
            centeredROIValue = np.mean(frameOri[headPosition[1]-compareDarknestWithThePastWindow:headPosition[1]+compareDarknestWithThePastWindow, headPosition[0]-compareDarknestWithThePastWindow:headPosition[0]+compareDarknestWithThePastWindow])
            centeredROIValueOld = np.mean(oldFrame[headPosition[1]-compareDarknestWithThePastWindow:headPosition[1]+compareDarknestWithThePastWindow, headPosition[0]-compareDarknestWithThePastWindow:headPosition[0]+compareDarknestWithThePastWindow])
            if self._hyperparameters["brightAnimalDarkBackground"]:
              ok = (centeredROIValue > centeredROIValueOld)
            else:
              ok = (centeredROIValue < centeredROIValueOld)
            okAll = (okAll and ok)
      
      if minVal < localMinimumDarkestThreshold and okAll:
        trackingHeadTailAllAnimals[animalNumber, i-self._firstFrame][0][0] = headPosition[0]
        trackingHeadTailAllAnimals[animalNumber, i-self._firstFrame][0][1] = headPosition[1]
        trackingHeadingAllAnimals[animalNumber, i-self._firstFrame] = heading
      else:
        trackingHeadTailAllAnimals[animalNumber, i-self._firstFrame][0][0] = 0
        trackingHeadTailAllAnimals[animalNumber, i-self._firstFrame][0][1] = 0
        trackingHeadingAllAnimals[animalNumber, i-self._firstFrame] = 0
      
      cv2.circle(blur, headPosition, self._hyperparameters["headSize"], (255, 255, 255), -1)
      (minVal, maxVal, headPosition, maxLoc) = cv2.minMaxLoc(blur)

  return lastFirstTheta
