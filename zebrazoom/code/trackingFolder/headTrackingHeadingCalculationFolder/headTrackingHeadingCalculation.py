import cv2
import numpy as np

from zebrazoom.code.trackingFolder.headTrackingHeadingCalculationFolder.headTrackingTakeHeadClosestToWellCenter import headTrackingTakeHeadClosestToWellCenter
from zebrazoom.code.trackingFolder.headTrackingHeadingCalculationFolder.calculateHeading import calculateHeading
from zebrazoom.code.trackingFolder.headTrackingHeadingCalculationFolder.multipleAnimalsHeadTracking import multipleAnimalsHeadTracking
from zebrazoom.code.trackingFolder.headTrackingHeadingCalculationFolder.multipleAnimalsHeadTrackingAdvance import multipleAnimalsHeadTrackingAdvance
# from postProcessingMultiAnimalTrajectories import postProcessingMultiAnimalTrajectories

def headTrackingHeadingCalculation(hyperparameters, firstFrame, i, blur, thresh1, thresh2, gray, erodeSize, frame_width, frame_height, trackingHeadingAllAnimals, trackingHeadTailAllAnimals, trackingProbabilityOfGoodDetection, headPosition, lengthX, xmin=0, ymin=0):

  xHB_TN = 0
  heading = 0
  x = 0
  y = 0
  lastFirstTheta = 0
  
  if hyperparameters["fixedHeadPositionX"] != -1:
  
    trackingHeadTailAllAnimals[0, i-firstFrame][0][0] = int(hyperparameters["fixedHeadPositionX"])
    trackingHeadTailAllAnimals[0, i-firstFrame][0][1] = int(hyperparameters["fixedHeadPositionY"])
    
  else:
  
    if hyperparameters["nbAnimalsPerWell"] > 1 or hyperparameters["forceBlobMethodForHeadTracking"]:
      
      if hyperparameters["multipleAnimalTrackingAdvanceAlgorithm"] == 0:
        [trackingHeadingAllAnimals, trackingHeadTailAllAnimals] = multipleAnimalsHeadTracking(trackingHeadingAllAnimals, trackingHeadTailAllAnimals, hyperparameters, gray, i, firstFrame, thresh1, xmin, ymin)
      else:
        [trackingHeadingAllAnimals, trackingHeadTailAllAnimals] = multipleAnimalsHeadTrackingAdvance(trackingHeadingAllAnimals, trackingHeadTailAllAnimals, hyperparameters, gray, i, firstFrame, thresh1, thresh2, lengthX)
      
      heading = 0
      headPosition = [0, 0]
      x = 0
      y = 0
      lastFirstTheta = 0
      
    else:
      
      if (hyperparameters["headEmbeded"] == 1 and i == firstFrame) or (hyperparameters["headEmbeded"] == 0) or (hyperparameters["headEmbededTeresaNicolson"] == 1):
        
        if hyperparameters["findHeadPositionByUserInput"] == 0:
          
          if type(blur) == int: # it won't be equal to int for images coming from the faster screen 'multiprocessing'
            paramGaussianBlur = int((hyperparameters["paramGaussianBlur"] / 2)) * 2 + 1
            blur = cv2.GaussianBlur(gray, (paramGaussianBlur, paramGaussianBlur), 0)
          
          # Finds head position for frame i
          takeTheHeadClosestToTheCenter = hyperparameters["takeTheHeadClosestToTheCenter"]
          if takeTheHeadClosestToTheCenter == 0:
            (minVal, maxVal, headPosition, maxLoc) = cv2.minMaxLoc(blur)
            if type(trackingProbabilityOfGoodDetection) != int and len(trackingProbabilityOfGoodDetection) and i-firstFrame < len(trackingProbabilityOfGoodDetection[0]):
              trackingProbabilityOfGoodDetection[0, i-firstFrame] = np.sum(255 - blur)
          else:
            headPosition = headTrackingTakeHeadClosestToWellCenter(thresh1, thresh2, blur, erodeSize, hyperparameters["minArea"], hyperparameters["maxArea"], frame_width, frame_height)
          
          x = headPosition[0]
          y = headPosition[1]
          
          if (hyperparameters["headEmbededTeresaNicolson"] == 1) and (i == firstFrame):
            xHB_TN = x
          
          if (hyperparameters["headEmbededTeresaNicolson"] == 1):
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
            [heading, lastFirstTheta] = calculateHeading(x, y, i, thresh1, thresh2, takeTheHeadClosestToTheCenter, hyperparameters)
          
          if (hyperparameters["headEmbededTeresaNicolson"] == 1):
            heading = 0
            lastFirstTheta = 0
          
          trackingHeadTailAllAnimals[0, i-firstFrame][0][0] = headPosition[0]
          trackingHeadTailAllAnimals[0, i-firstFrame][0][1] = headPosition[1]
          trackingHeadingAllAnimals[0, i-firstFrame] = heading
          
        else:
          
          # This is for the head-embedeed: at this point, this is set again in the tail tracking (the heading is set in the tail tracking as well)
          trackingHeadTailAllAnimals[0, i-firstFrame][0][0] = headPosition[0]
          trackingHeadTailAllAnimals[0, i-firstFrame][0][1] = headPosition[1]
          
      else:
        # If head embeded, heading and head position stay the same for all frames
        trackingHeadingAllAnimals[0, i-firstFrame]  = trackingHeadingAllAnimals[0, 0]
        trackingHeadTailAllAnimals[0, i-firstFrame] = trackingHeadTailAllAnimals[0, 0]
    
  return [trackingHeadingAllAnimals, trackingHeadTailAllAnimals, trackingProbabilityOfGoodDetection, lastFirstTheta]
