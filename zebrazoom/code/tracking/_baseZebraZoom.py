import math
import pickle
import os
import cv2

import h5py
import numpy as np

from zebrazoom.code.dataPostProcessing.dataPostProcessing import dataPostProcessing

from ._base import BaseTrackingMethod
from ._getBackground import GetBackgroundMixin
from ._updateBackgroundAtInterval import UpdateBackgroundAtIntervalMixin


class BaseZebraZoomTrackingMethod(BaseTrackingMethod, GetBackgroundMixin, UpdateBackgroundAtIntervalMixin):
  '''Base class for tracking implementations which use ZebraZoom mixins.'''

  def _debugFrame(self, frame, title=None, buttons=(), timeout=None):
    raise ValueError("debug mode is not available without the GUI")

  def dataPostProcessing(self, outputFolder, superStruct):
    # Various post-processing options depending on configuration file choices
    return dataPostProcessing(outputFolder, superStruct, self._hyperparameters, self._hyperparameters['videoNameWithTimestamp'], os.path.splitext(os.path.basename(self._videoPath))[1])

  def _debugTracking(self, frameNumber: int, output: list, outputHeading: list, frame2: np.array) -> None:
    pass

  @staticmethod
  def __rollingMedianFilter(array, window):
    array2 = np.convolve(array, np.ones(window), 'same') / window
    array2[:window-1] = array[:window-1]
    array2[-window+1:] = array[-window+1:]
    return array2
  
  @staticmethod
  def _putAngleInOtherAngleReferential(firstAngle, secondAngle):
    secondAngleInFirstReferential = secondAngle - firstAngle
    return abs(math.pi - ((secondAngleInFirstReferential + 2 * math.pi) % (2 * math.pi)))
  
  @staticmethod
  def _calculateListOfSurroundingAngles(self, frameNumber, headingValue, headPos, windowNbFrames, minDist):

    listOfSurroundingAngles    = []
    listOfSurroundingAnglesOri = []
    
    xPos = headPos[frameNumber][0][0]
    yPos = headPos[frameNumber][0][1]

    back = 1
    while frameNumber - back >= 0 and len(listOfSurroundingAngles) < windowNbFrames:
      xPosAround = headPos[frameNumber - back][0][0]
      yPosAround = headPos[frameNumber - back][0][1]
      if math.sqrt((xPosAround - xPos) ** 2 + (yPosAround - yPos) ** 2) >= minDist:
        listOfSurroundingAngles    = [self._putAngleInOtherAngleReferential(headingValue, self._calculateAngle(xPosAround, yPosAround, xPos, yPos))] + listOfSurroundingAngles
        listOfSurroundingAnglesOri = [self._calculateAngle(xPosAround, yPosAround, xPos, yPos)] + listOfSurroundingAnglesOri
      back += 1
    if len(listOfSurroundingAngles) < windowNbFrames:
      while len(listOfSurroundingAngles) < windowNbFrames:
        listOfSurroundingAngles    = [listOfSurroundingAngles[0] if len(listOfSurroundingAngles) else 0] + listOfSurroundingAngles
        listOfSurroundingAnglesOri = [listOfSurroundingAnglesOri[0] if len(listOfSurroundingAnglesOri) else 0] + listOfSurroundingAnglesOri

    fwd = 1
    while frameNumber + fwd < len(headPos) and len(listOfSurroundingAngles) < 2 * windowNbFrames:
      xPosAround = headPos[frameNumber + fwd][0][0]
      yPosAround = headPos[frameNumber + fwd][0][1]
      if math.sqrt((xPosAround - xPos) ** 2 + (yPosAround - yPos) ** 2) >= minDist:
        listOfSurroundingAngles.append(self._putAngleInOtherAngleReferential(headingValue, self._calculateAngle(xPos, yPos, xPosAround, yPosAround)))
        listOfSurroundingAnglesOri.append(self._calculateAngle(xPos, yPos, xPosAround, yPosAround))
      fwd += 1
    if len(listOfSurroundingAngles) < 2 * windowNbFrames:
      while len(listOfSurroundingAngles) < 2 * windowNbFrames:
        listOfSurroundingAngles.append(listOfSurroundingAngles[len(listOfSurroundingAngles) - 1] if len(listOfSurroundingAngles) else 0)
        listOfSurroundingAnglesOri.append(listOfSurroundingAnglesOri[len(listOfSurroundingAnglesOri) - 1] if len(listOfSurroundingAnglesOri) else 0)
    
    return [listOfSurroundingAngles, listOfSurroundingAnglesOri]
  
  
  def _postProcessHeadingWithTrajectoryAdvanced(self, trackingHeadTailAllAnimals, trackingHeadingAllAnimals, trackingProbabilityOfHeadingGoodCalculation):

    mean_Error = 2.48183
    std_Error  = 0.25525
    windowNbFrames = 30
    minDist = 5
    
    for animalId in range(0, len(trackingHeadTailAllAnimals)):
      for frameNumber in range(0, len(trackingHeadTailAllAnimals[animalId])):
        headPos = trackingHeadTailAllAnimals[animalId]
        heading = trackingHeadingAllAnimals[animalId]
        if frameNumber < windowNbFrames or frameNumber >= len(trackingHeadTailAllAnimals[animalId]) - windowNbFrames:
          heading[frameNumber] = float('nan')
        else:
          [listOfSurroundingAngles, listOfSurroundingAnglesOri] = self._calculateListOfSurroundingAngles(self, frameNumber, heading[frameNumber], headPos, windowNbFrames, minDist)
          sumErrorLoc = np.mean(listOfSurroundingAngles)
          if (sumErrorLoc < mean_Error - 2 * std_Error):
            [listOfSurroundingAngles, listOfSurroundingAnglesOri] = self._calculateListOfSurroundingAngles(self, frameNumber, (heading[frameNumber] + math.pi) % (2 * math.pi), headPos, windowNbFrames, minDist)
            if True:
              heading[frameNumber] = float('nan')
            else:
              sumErrorLocReverse = np.mean(listOfSurroundingAngles)
              if (sumErrorLocReverse > mean_Error - 1 * std_Error):
                heading[frameNumber] = (heading[frameNumber] + math.pi) % (2 * math.pi)
              else:
                heading[frameNumber] = float('nan')
  
  
  def _postProcessHeadingWithTrajectory(self, trackingHeadTailAllAnimals, trackingHeadingAllAnimals, trackingProbabilityOfHeadingGoodCalculation):
    for animalId in range(0, len(trackingHeadTailAllAnimals)):
      last_index   = 0
      last_xHead   = trackingHeadTailAllAnimals[animalId][last_index][0][0]
      last_yHead   = trackingHeadTailAllAnimals[animalId][last_index][0][1]
      last_heading = (trackingHeadingAllAnimals[animalId][last_index] + math.pi) % (2*math.pi)
      curDist = 0
      for frameNumber in range(0, len(trackingHeadTailAllAnimals[animalId])):
        xHead = trackingHeadTailAllAnimals[animalId][frameNumber][0][0]
        yHead = trackingHeadTailAllAnimals[animalId][frameNumber][0][1]
        heading = trackingHeadingAllAnimals[animalId][frameNumber]
        last_heading = self._calculateAngle(xHead, yHead, last_xHead, last_yHead)
        dist = math.sqrt((xHead - last_xHead)**2 + (yHead - last_yHead)**2)
        while dist > self._hyperparameters["postProcessHeadingWithTrajectory_minDist"] and last_index+1 < len(trackingHeadTailAllAnimals[animalId]):
          dist = math.sqrt((xHead - last_xHead)**2 + (yHead - last_yHead)**2)
          last_index += 1
          last_xHead   = trackingHeadTailAllAnimals[animalId][last_index][0][0]
          last_yHead   = trackingHeadTailAllAnimals[animalId][last_index][0][1]
        if self._distBetweenThetas((heading + math.pi) % (2*math.pi), last_heading) > self._distBetweenThetas(heading, last_heading) and self._distBetweenThetas(heading, last_heading) < 0.25 * math.pi and abs(trackingProbabilityOfHeadingGoodCalculation[0, frameNumber]) <= 10:
          trackingHeadingAllAnimals[animalId][frameNumber] = (heading + math.pi) % (2*math.pi)
          print("Inversion of heading in post processing, animalId:", animalId, " ; frame:", frameNumber, "; proba:", trackingProbabilityOfHeadingGoodCalculation[0, frameNumber])
      
      potentiallyAbnormalRangeIndStart = -1
      for revert in [0, 1]:
        if revert:
          trackingHeadingAllAnimals[animalId] = np.flip(trackingHeadingAllAnimals[animalId])
        for frameNumber in range(1, len(trackingHeadTailAllAnimals[animalId])):
          heading = trackingHeadingAllAnimals[animalId][frameNumber]
          if self._distBetweenThetas(heading, trackingHeadingAllAnimals[animalId][potentiallyAbnormalRangeIndStart-1 if potentiallyAbnormalRangeIndStart!=-1 else frameNumber-1]) > 0.8 * math.pi:
            if potentiallyAbnormalRangeIndStart == -1:
              potentiallyAbnormalRangeIndStart = frameNumber
          else:
            if potentiallyAbnormalRangeIndStart != -1:
              if frameNumber - potentiallyAbnormalRangeIndStart > 100:
                print("heading post processing second step: potentiallyAbnormalRange too long, reseting")
                potentiallyAbnormalRangeIndStart = -1
              else:
                print("Second heading post processing step: looking for potential invertion between frame", potentiallyAbnormalRangeIndStart, "and", frameNumber)
                for frameNumber2 in range(potentiallyAbnormalRangeIndStart, frameNumber):
                  if self._distBetweenThetas(trackingHeadingAllAnimals[animalId][frameNumber2], trackingHeadingAllAnimals[animalId][potentiallyAbnormalRangeIndStart-1]) > math.pi / 2:
                    print("Second heading post processing step: inverting angle for frame", frameNumber2)
                    trackingHeadingAllAnimals[animalId][frameNumber2] = (trackingHeadingAllAnimals[animalId][frameNumber2] + math.pi) % (2*math.pi)
                potentiallyAbnormalRangeIndStart = -1
      trackingHeadingAllAnimals[animalId] = np.flip(trackingHeadingAllAnimals[animalId])
      
      for frameNumber in range(1, len(trackingHeadTailAllAnimals[animalId])-1):
        headingBef  = trackingHeadingAllAnimals[animalId][frameNumber-1]
        headingPres = trackingHeadingAllAnimals[animalId][frameNumber]
        headingAft  = trackingHeadingAllAnimals[animalId][frameNumber+1]
        if self._distBetweenThetas(headingBef, headingPres) > 110*(math.pi/180) and self._distBetweenThetas(headingPres, headingAft) > 110*(math.pi/180):
          print("Third heading post processing step: inverting frame", frameNumber)
          trackingHeadingAllAnimals[animalId][frameNumber] = (trackingHeadingAllAnimals[animalId][frameNumber] + math.pi) % (2 * math.pi)

  
  def _postProcessMultipleTrajectories(self, trackingHeadTailAllAnimals, trackingProbabilityOfGoodDetection):
    maxDistanceAuthorized = self._hyperparameters["postProcessMaxDistanceAuthorized"]
    maxDisapearanceFrames = self._hyperparameters["postProcessMaxDisapearanceFrames"]

    # Removing all points for which the sum of all pixels of the inverted image (the "probability of good detection") is too low
    if self._hyperparameters["postProcessRemoveLowProbabilityDetection"]:
      for animalId in range(0, len(trackingHeadTailAllAnimals)):
        probabilityOfGoodDetection = trackingProbabilityOfGoodDetection[animalId, :]
        if self._hyperparameters["postProcessLowProbabilityDetectionPercentOfMaximum"] == 0:
          toRemove   = (probabilityOfGoodDetection - np.mean(probabilityOfGoodDetection) < -self._hyperparameters["postProcessLowProbabilityDetectionThreshold"] * np.std(probabilityOfGoodDetection))
        else:
          toRemove   = (probabilityOfGoodDetection < np.max(probabilityOfGoodDetection) * self._hyperparameters["postProcessLowProbabilityDetectionPercentOfMaximum"])
        print("Well ", animalId, ": Number of elements to remove:", np.sum(toRemove), " out of ", len(toRemove), "elements")
        trackingHeadTailAllAnimals[animalId, toRemove, 0, 0] = 0
        trackingHeadTailAllAnimals[animalId, toRemove, 0, 1] = 0

    # Removing all points that are too close to the borders
    if self._hyperparameters["postProcessRemovePointsOnBordersMargin"]:
      borderMargin = self._hyperparameters["postProcessRemovePointsOnBordersMargin"]
      for animalId in range(0, len(trackingHeadTailAllAnimals)):
        for frameNumber in range(0, len(trackingHeadTailAllAnimals[animalId])):
          xHead = trackingHeadTailAllAnimals[animalId][frameNumber][0][0]
          yHead = trackingHeadTailAllAnimals[animalId][frameNumber][0][1]
          if (xHead <= borderMargin) or (yHead <= borderMargin) or (xHead >= self._wellPositions[animalId]["lengthX"] - borderMargin - 1) or (yHead >= self._wellPositions[animalId]["lengthY"] - borderMargin - 1):
            trackingHeadTailAllAnimals[animalId][frameNumber][0][0] = 0
            trackingHeadTailAllAnimals[animalId][frameNumber][0][1] = 0

    # Removing all points that are deviating too much from the main trajectory
    if self._hyperparameters["postProcessRemovePointsAwayFromMainTrajectory"]:
      for animalId in range(0, len(trackingHeadTailAllAnimals)):
        xHeadPositions = trackingHeadTailAllAnimals[animalId, :, 0, 0]
        yHeadPositions = trackingHeadTailAllAnimals[animalId, :, 0, 1]
        xHeadPositionsRollingMedian = self.__rollingMedianFilter(xHeadPositions, 11)
        yHeadPositionsRollingMedian = self.__rollingMedianFilter(yHeadPositions, 11)
        distance = np.sqrt((xHeadPositions - xHeadPositionsRollingMedian) ** 2 + (yHeadPositions - yHeadPositionsRollingMedian) ** 2)
        distanceRollingMedian = self.__rollingMedianFilter(distance, 5)
        normalizedDistance = np.array([1 for x in range(0,len(xHeadPositions))])
        normalizedDistance = distance / distanceRollingMedian
        normalizedDistance = np.nan_to_num(normalizedDistance, nan=1)
        toRemove   = normalizedDistance - np.mean(normalizedDistance) > self._hyperparameters["postProcessRemovePointsAwayFromMainTrajectoryThreshold"] * np.std(normalizedDistance)
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

  @staticmethod
  def _calculateAngle(xStart, yStart, xEnd, yEnd):
    vx = xEnd - xStart
    vy = yEnd - yStart
    if vx == 0:
      if vy > 0:
        lastFirstTheta = math.pi/2
      else:
        lastFirstTheta = (3*math.pi)/2
    else:
      lastFirstTheta = np.arctan(abs(vy/vx))
      if (vx < 0) and (vy >= 0):
        lastFirstTheta = math.pi - lastFirstTheta
      elif (vx < 0) and (vy <= 0):
        lastFirstTheta = lastFirstTheta + math.pi
      elif (vx > 0) and (vy <= 0):
        lastFirstTheta = 2*math.pi - lastFirstTheta
    return lastFirstTheta

  @staticmethod
  def _distBetweenThetas(theta1, theta2):
    diff = 0
    if theta1 > theta2:
      diff = theta1 - theta2
    else:
      diff = theta2 - theta1
    if diff > math.pi:
      diff = (2 * math.pi) - diff
    return diff

  @staticmethod
  def _assignValueIfBetweenRange(value, minn, maxx):
    if value < minn:
      return minn
    if value > maxx:
      return maxx
    return value

  def getBackground(self):
    if not("calculateBackgroundNoMatterWhat" in self._hyperparameters and self._hyperparameters["calculateBackgroundNoMatterWhat"]) and (self._hyperparameters["backgroundSubtractorKNN"] or (self._hyperparameters["headEmbeded"] and self._hyperparameters["headEmbededRemoveBack"] == 0 and self._hyperparameters["headEmbededAutoSet_BackgroundExtractionOption"] == 0 and not self._hyperparameters['adjustHeadEmbeddedEyeTracking'] and self._hyperparameters["adjustHeadEmbededTracking"] == 0) or self._hyperparameters["trackingDL"] or self._hyperparameters["fishTailTrackingDifficultBackground"]):
      background = []
    else:
      print("start get background")
      if self._hyperparameters["reloadBackground"]:
        fname = next(reversed(sorted(name for name in os.listdir(self._hyperparameters['outputFolder']) if os.path.splitext(name)[0][:-20] == self._videoName and os.path.splitext(name)[0] != self._hyperparameters['videoNameWithTimestamp'])))
        with h5py.File(os.path.join(self._hyperparameters['outputFolder'], fname)) as results:
          background = results['background'][:]
      else:
        background = self._getBackground()
      if self._hyperparameters['storeH5']:
        with h5py.File(self._hyperparameters['H5filename'], 'a') as results:
          results.create_dataset('background', data=background)
      else:
        outputFolderVideo = os.path.join(self._hyperparameters['outputFolder'], self._hyperparameters['videoNameWithTimestamp'])
        if not os.path.exists(outputFolderVideo):
          os.makedirs(outputFolderVideo)
        cv2.imwrite(os.path.join(outputFolderVideo, 'background.png'), background)

    if self._hyperparameters["exitAfterBackgroundExtraction"]:
      print("exitAfterBackgroundExtraction")
      raise ValueError

    return background
