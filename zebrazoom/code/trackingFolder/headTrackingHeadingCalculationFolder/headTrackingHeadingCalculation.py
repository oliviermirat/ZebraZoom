import cv2

from headTrackingTakeHeadClosestToWellCenter import headTrackingTakeHeadClosestToWellCenter
from calculateHeading import calculateHeading
from multipleAnimalsHeadTracking import multipleAnimalsHeadTracking
from multipleAnimalsHeadTrackingAdvance import multipleAnimalsHeadTrackingAdvance
# from postProcessingMultiAnimalTrajectories import postProcessingMultiAnimalTrajectories

def headTrackingHeadingCalculation(hyperparameters, firstFrame, i, blur, thresh1, thresh2, gray, erodeSize, frame_width, frame_height, trackingHeadingAllAnimals, trackingHeadTailAllAnimals, headPosition, lengthX):

  xHB_TN = 0
  heading = 0
  x = 0
  y = 0
  lastFirstTheta = 0
  
  if hyperparameters["nbAnimalsPerWell"] > 1 or hyperparameters["forceBlobMethodForHeadTracking"]:
    
    if hyperparameters["multipleAnimalTrackingAdvanceAlgorithm"] == 0:
      [trackingHeadingAllAnimals, trackingHeadTailAllAnimals] = multipleAnimalsHeadTracking(trackingHeadingAllAnimals, trackingHeadTailAllAnimals, hyperparameters, gray, i, firstFrame, thresh1, thresh2)
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
        # Finds head position for frame i
        takeTheHeadClosestToTheCenter = hyperparameters["takeTheHeadClosestToTheCenter"]
        if takeTheHeadClosestToTheCenter == 0:
          (minVal, maxVal, headPosition, maxLoc) = cv2.minMaxLoc(blur)
        else:
          headPosition = headTrackingTakeHeadClosestToWellCenter(thresh1, thresh2, blur, erodeSize, hyperparameters["minArea"], hyperparameters["maxArea"], frame_width, frame_height)
        
        x = headPosition[0]
        y = headPosition[1]
        
        if (hyperparameters["headEmbededTeresaNicolson"] == 1) and (i == firstFrame):
          xHB_TN = x
        
        if (hyperparameters["headEmbededTeresaNicolson"] == 1):
          headPosition = [xHB_TN + 100, y]
        
        # Calculate heading for frame i
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
    
  return [trackingHeadingAllAnimals, trackingHeadTailAllAnimals, lastFirstTheta]
