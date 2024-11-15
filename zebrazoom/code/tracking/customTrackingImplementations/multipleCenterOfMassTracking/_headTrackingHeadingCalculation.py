import math
import cv2
import numpy as np


def _headTrackingHeadingCalculation(self, i, blur, thresh1, thresh2, frameOri, erodeSize, frame_width, frame_height, trackingHeadingAllAnimals, trackingHeadTailAllAnimals, trackingProbabilityOfGoodDetection, headPosition, lengthX, xmin=0, ymin=0, wellNumber=-1, oldFrameList=[]):
  xHB_TN = 0
  heading = 0
  x = 0
  y = 0
  lastFirstTheta = 0

  if self._hyperparameters["fixedHeadPositionX"] != -1:

    trackingHeadTailAllAnimals[0, i-self._firstFrame][0][0] = int(self._hyperparameters["fixedHeadPositionX"])
    trackingHeadTailAllAnimals[0, i-self._firstFrame][0][1] = int(self._hyperparameters["fixedHeadPositionY"])

  else:

    if (self._hyperparameters["headEmbeded"] == 1 and i == self._firstFrame) or (self._hyperparameters["headEmbeded"] == 0) or (self._hyperparameters["headEmbededTeresaNicolson"] == 1):

      if self._hyperparameters["findHeadPositionByUserInput"] == 0:

        # Finds head position for frame i
        takeTheHeadClosestToTheCenter = self._hyperparameters["takeTheHeadClosestToTheCenter"]
        
        (minVal, maxVal, headPosition, maxLoc) = cv2.minMaxLoc(blur)
        
        # if i >= 250:
          # import zebrazoom.code.util as util
          # util.showFrame(frameOri, title="frameOri")
        
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

            if (self._hyperparameters["headEmbededTeresaNicolson"] == 1) and (i == self._firstFrame):
              xHB_TN = x

            if (self._hyperparameters["headEmbededTeresaNicolson"] == 1):
              headPosition = [xHB_TN + 100, y]

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

            if (self._hyperparameters["headEmbededTeresaNicolson"] == 1):
              heading = 0
              lastFirstTheta = 0
            
            okAll = True
            if i > 110:
              for oldFrame in oldFrameList:
                compareDarknestWithThePastWindow = 10
                centeredROIValue = np.mean(frameOri[headPosition[1]-compareDarknestWithThePastWindow:headPosition[1]+compareDarknestWithThePastWindow, headPosition[0]-compareDarknestWithThePastWindow:headPosition[0]+compareDarknestWithThePastWindow])
                centeredROIValueOld = np.mean(oldFrame[headPosition[1]-compareDarknestWithThePastWindow:headPosition[1]+compareDarknestWithThePastWindow, headPosition[0]-compareDarknestWithThePastWindow:headPosition[0]+compareDarknestWithThePastWindow])
                ok = (centeredROIValue > centeredROIValueOld)
                okAll = (okAll and ok)
            
            # halfDiameter = 20 #30
            # largerROIValue   = np.median(frameOri[headPosition[1]-halfDiameter:headPosition[1]+halfDiameter+1, headPosition[0]-halfDiameter:headPosition[0]+halfDiameter+1])
            
            # if i >= 50:
              # print("centeredROIValue:", centeredROIValue, "; centeredROIValueOld:", centeredROIValueOld)
              # import zebrazoom.code.util as util
              # util.showFrame(frameOri[headPosition[1]-compareDarknestWithThePastWindow:headPosition[1]+compareDarknestWithThePastWindow, headPosition[0]-compareDarknestWithThePastWindow:headPosition[0]+compareDarknestWithThePastWindow], title="frameOri")
              # util.showFrame(oldFrame[headPosition[1]-compareDarknestWithThePastWindow:headPosition[1]+compareDarknestWithThePastWindow, headPosition[0]-compareDarknestWithThePastWindow:headPosition[0]+compareDarknestWithThePastWindow], title="oldFrame")
            
            if minVal < localMinimumDarkestThreshold and okAll: # 110: #180:
              trackingHeadTailAllAnimals[animalNumber, i-self._firstFrame][0][0] = headPosition[0]
              trackingHeadTailAllAnimals[animalNumber, i-self._firstFrame][0][1] = headPosition[1]
              trackingHeadingAllAnimals[animalNumber, i-self._firstFrame] = heading
            else:
              trackingHeadTailAllAnimals[animalNumber, i-self._firstFrame][0][0] = 0
              trackingHeadTailAllAnimals[animalNumber, i-self._firstFrame][0][1] = 0
              trackingHeadingAllAnimals[animalNumber, i-self._firstFrame] = 0
            
            cv2.circle(blur, headPosition, 40, (255, 255, 255), -1)
            (minVal, maxVal, headPosition, maxLoc) = cv2.minMaxLoc(blur)

      else:

        # This is for the head-embedeed: at this point, this is set again in the tail tracking (the heading is set in the tail tracking as well)
        trackingHeadTailAllAnimals[0, i-self._firstFrame][0][0] = headPosition[0]
        trackingHeadTailAllAnimals[0, i-self._firstFrame][0][1] = headPosition[1]

    else:
      # If head embeded, heading and head position stay the same for all frames
      trackingHeadingAllAnimals[0, i-self._firstFrame]  = trackingHeadingAllAnimals[0, 0]
      trackingHeadTailAllAnimals[0, i-self._firstFrame] = trackingHeadTailAllAnimals[0, 0]

  return lastFirstTheta
