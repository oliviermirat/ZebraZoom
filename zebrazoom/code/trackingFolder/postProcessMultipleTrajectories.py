import numpy as np
import cv2
import math

def postProcessMultipleTrajectories(trackingHeadingAllAnimals, trackingHeadTailAllAnimals, trackingEyesAllAnimals, hyperparameters):
  
  maxDistanceAuthorized = hyperparameters["postProcessMaxDistanceAuthorized"]
  maxDisapearanceFrames = hyperparameters["postProcessMaxDisapearanceFrames"]
  
  currentlyZero  = False
  zeroFrameStart = 0
  for animalId in range(0, len(trackingHeadTailAllAnimals)):
    for frameNumber in range(0, len(trackingHeadTailAllAnimals[animalId])):
      xHead = trackingHeadTailAllAnimals[animalId][frameNumber][0][0]
      yHead = trackingHeadTailAllAnimals[animalId][frameNumber][0][1]
      if frameNumber != 0:
        xHeadPrev = trackingHeadTailAllAnimals[animalId][frameNumber-1][0][0]
        yHeadPrev = trackingHeadTailAllAnimals[animalId][frameNumber-1][0][1]
      else:
        xHeadPrev = trackingHeadTailAllAnimals[animalId][frameNumber][0][0]
        yHeadPrev = trackingHeadTailAllAnimals[animalId][frameNumber][0][1]
      if (xHead == 0 and yHead == 0) or (math.sqrt((xHead - xHeadPrev)**2 + (yHead - yHeadPrev)**2) > maxDistanceAuthorized):
        if not(currentlyZero):
          zeroFrameStart = frameNumber
        print("currentlyZero at True: animalId:", animalId, "; frameNumber:", frameNumber)
        currentlyZero = True
      else:
        if currentlyZero:
          if zeroFrameStart >= 1:
            xHeadStart = trackingHeadTailAllAnimals[animalId][zeroFrameStart-1][0][0]
            yHeadStart = trackingHeadTailAllAnimals[animalId][zeroFrameStart-1][0][1]
          else:
            xHeadStart = trackingHeadTailAllAnimals[animalId][frameNumber][0][0]
            yHeadStart = trackingHeadTailAllAnimals[animalId][frameNumber][0][1]
          xHeadEnd = trackingHeadTailAllAnimals[animalId][frameNumber][0][0]
          yHeadEnd = trackingHeadTailAllAnimals[animalId][frameNumber][0][1]
          if (math.sqrt((xHeadEnd - xHeadStart)**2 + (yHeadEnd - yHeadStart)**2) < maxDistanceAuthorized) or (frameNumber - zeroFrameStart > maxDisapearanceFrames):
            currentlyZero = False
            if (math.sqrt((xHeadEnd - xHeadStart)**2 + (yHeadEnd - yHeadStart)**2) < maxDistanceAuthorized):
              xStep = (xHeadEnd - xHeadStart) / (frameNumber - zeroFrameStart)
              yStep = (yHeadEnd - yHeadStart) / (frameNumber - zeroFrameStart)
              for frameAtZeroToChange in range(zeroFrameStart, frameNumber):
                trackingHeadTailAllAnimals[animalId][frameAtZeroToChange][0][0] = xHeadStart + xStep * (frameAtZeroToChange - zeroFrameStart)
                trackingHeadTailAllAnimals[animalId][frameAtZeroToChange][0][1] = yHeadStart + yStep * (frameAtZeroToChange - zeroFrameStart)    
            else:
              xStep = (xHeadEnd - xHeadStart) / (frameNumber - zeroFrameStart)
              yStep = (yHeadEnd - yHeadStart) / (frameNumber - zeroFrameStart)
              for frameAtZeroToChange in range(zeroFrameStart, frameNumber):
                trackingHeadTailAllAnimals[animalId][frameAtZeroToChange][0][0] = xHeadStart
                trackingHeadTailAllAnimals[animalId][frameAtZeroToChange][0][1] = yHeadStart
  
  return [trackingHeadingAllAnimals, trackingHeadTailAllAnimals, trackingEyesAllAnimals]
