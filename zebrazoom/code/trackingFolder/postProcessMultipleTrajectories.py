import numpy as np
import cv2
import math

def rollingMedianFilter(array, window):
  array2 = np.convolve(array, np.ones(window), 'same') / window
  array2[:window-1] = array[:window-1]
  array2[-window+1:] = array[-window+1:]
  array = array2
  return array

def postProcessMultipleTrajectories(trackingHeadingAllAnimals, trackingHeadTailAllAnimals, trackingEyesAllAnimals, trackingProbabilityOfGoodDetection, hyperparameters, wellPositions):
  
  maxDistanceAuthorized = hyperparameters["postProcessMaxDistanceAuthorized"]
  maxDisapearanceFrames = hyperparameters["postProcessMaxDisapearanceFrames"]
  
  # Removing all points for which the sum of all pixels of the inverted image (the "probability of good detection") is too low
  if hyperparameters["postProcessRemoveLowProbabilityDetection"]:
    for animalId in range(0, len(trackingHeadTailAllAnimals)):
      probabilityOfGoodDetection = trackingProbabilityOfGoodDetection[animalId, :]
      if hyperparameters["postProcessLowProbabilityDetectionPercentOfMaximum"] == 0:
        toRemove   = (probabilityOfGoodDetection - np.mean(probabilityOfGoodDetection) < -hyperparameters["postProcessLowProbabilityDetectionThreshold"] * np.std(probabilityOfGoodDetection))
      else:
        toRemove   = (probabilityOfGoodDetection < np.max(probabilityOfGoodDetection) * hyperparameters["postProcessLowProbabilityDetectionPercentOfMaximum"])
      print("Well ", animalId, ": Number of elements to remove:", np.sum(toRemove), " out of ", len(toRemove), "elements")
      trackingHeadTailAllAnimals[animalId, toRemove, 0, 0] = 0
      trackingHeadTailAllAnimals[animalId, toRemove, 0, 1] = 0
  
  # Removing all points that are too close to the borders
  if hyperparameters["postProcessRemovePointsOnBordersMargin"]:
    borderMargin = hyperparameters["postProcessRemovePointsOnBordersMargin"]
    for animalId in range(0, len(trackingHeadTailAllAnimals)):
      for frameNumber in range(0, len(trackingHeadTailAllAnimals[animalId])):
        xHead = trackingHeadTailAllAnimals[animalId][frameNumber][0][0]
        yHead = trackingHeadTailAllAnimals[animalId][frameNumber][0][1]
        if (xHead <= borderMargin) or (yHead <= borderMargin) or (xHead >= wellPositions[animalId]["lengthX"] - borderMargin - 1) or (yHead >= wellPositions[animalId]["lengthY"] - borderMargin - 1):
          trackingHeadTailAllAnimals[animalId][frameNumber][0][0] = 0
          trackingHeadTailAllAnimals[animalId][frameNumber][0][1] = 0
  
  # Removing all points that are deviating too much from the main trajectory
  if hyperparameters["postProcessRemovePointsAwayFromMainTrajectory"]:
    for animalId in range(0, len(trackingHeadTailAllAnimals)):
      xHeadPositions = trackingHeadTailAllAnimals[animalId, :, 0, 0]
      yHeadPositions = trackingHeadTailAllAnimals[animalId, :, 0, 1]
      xHeadPositionsRollingMedian = rollingMedianFilter(xHeadPositions, 11)
      yHeadPositionsRollingMedian = rollingMedianFilter(yHeadPositions, 11)
      distance = np.sqrt((xHeadPositions - xHeadPositionsRollingMedian) ** 2 + (yHeadPositions - yHeadPositionsRollingMedian) ** 2)
      distanceRollingMedian = rollingMedianFilter(distance, 5)
      normalizedDistance = np.array([1 for x in range(0,len(xHeadPositions))])
      normalizedDistance = distance / distanceRollingMedian
      normalizedDistance = np.nan_to_num(normalizedDistance, nan=1)
      toRemove   = normalizedDistance - np.mean(normalizedDistance) > hyperparameters["postProcessRemovePointsAwayFromMainTrajectoryThreshold"] * np.std(normalizedDistance)
      trackingHeadTailAllAnimals[animalId, toRemove, 0, 0] = 0
      trackingHeadTailAllAnimals[animalId, toRemove, 0, 1] = 0
  
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
      if ((xHead == 0 and yHead == 0) or (math.sqrt((xHead - xHeadPrev)**2 + (yHead - yHeadPrev)**2) > maxDistanceAuthorized)) and (frameNumber != len(trackingHeadTailAllAnimals[animalId]) - 1):
        if not(currentlyZero):
          zeroFrameStart = frameNumber
        # print("currentlyZero at True: animalId:", animalId, "; frameNumber:", frameNumber)
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
            if (math.sqrt((xHeadEnd - xHeadStart)**2 + (yHeadEnd - yHeadStart)**2) < maxDistanceAuthorized) and not((xHeadEnd == 0) and (yHeadEnd == 0)):
              xStep = (xHeadEnd - xHeadStart) / (frameNumber - zeroFrameStart)
              yStep = (yHeadEnd - yHeadStart) / (frameNumber - zeroFrameStart)
              for frameAtZeroToChange in range(zeroFrameStart, frameNumber):
                trackingHeadTailAllAnimals[animalId][frameAtZeroToChange][0][0] = xHeadStart + xStep * (frameAtZeroToChange - zeroFrameStart)
                trackingHeadTailAllAnimals[animalId][frameAtZeroToChange][0][1] = yHeadStart + yStep * (frameAtZeroToChange - zeroFrameStart)    
            else:
              for frameAtZeroToChange in range(zeroFrameStart, frameNumber):
                trackingHeadTailAllAnimals[animalId][frameAtZeroToChange][0][0] = xHeadStart
                trackingHeadTailAllAnimals[animalId][frameAtZeroToChange][0][1] = yHeadStart
  
  return [trackingHeadingAllAnimals, trackingHeadTailAllAnimals, trackingEyesAllAnimals]
