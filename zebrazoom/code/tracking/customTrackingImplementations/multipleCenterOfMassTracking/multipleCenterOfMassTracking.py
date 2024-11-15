from zebrazoom.code.extractParameters import extractParameters

import cv2
import zebrazoom.videoFormatConversion.zzVideoReading as zzVideoReading
import numpy as np
import math
from zebrazoom.code.tracking import register_tracking_method
from ..._eyeTracking import EyeTrackingMixin
from ..._fasterMultiprocessingBase import BaseFasterMultiprocessing
from ..._getImages import GetImagesMixin

from zebrazoom.code.tracking.customTrackingImplementations.multipleCenterOfMassTracking._headTrackingHeadingCalculation import _headTrackingHeadingCalculation

import zebrazoom.code.tracking
from collections import deque


class MultipleCenterOfMassTracking(BaseFasterMultiprocessing, EyeTrackingMixin, GetImagesMixin):
  def __init__(self, videoPath, wellPositions, hyperparameters):
    super().__init__(videoPath, wellPositions, hyperparameters)

    self._trackingProbabilityOfGoodDetectionList = [np.zeros((self._hyperparameters["nbAnimalsPerWell"], self._lastFrame-self._firstFrame+1)) for _ in range(self._hyperparameters["nbWells"])]
    
    if self._hyperparameters["headingCalculationMethod"]:
      self._trackingProbabilityOfHeadingGoodCalculation = [np.zeros((self._hyperparameters["nbAnimalsPerWell"], self._lastFrame-self._firstFrame+1)) for _ in range(self._hyperparameters["nbWells"])]
    else:
      self._trackingProbabilityOfHeadingGoodCalculation = 0

  def _adjustParameters(self, i, frame, widgets):
    return None

  def _formatOutput(self):
    if self._hyperparameters["postProcessMultipleTrajectories"]:
      for wellNumber in range(self._firstWell, self._lastWell + 1):
        self._postProcessMultipleTrajectories(self._trackingHeadTailAllAnimalsList[wellNumber], self._trackingProbabilityOfGoodDetectionList[wellNumber])
    
    if "postProcessHeadingWithTrajectory_minDist" in self._hyperparameters and self._hyperparameters["postProcessHeadingWithTrajectory_minDist"]:
      for wellNumber in range(self._firstWell, self._lastWell + 1):
        self._postProcessHeadingWithTrajectory(self._trackingHeadTailAllAnimalsList[wellNumber], self._trackingHeadingAllAnimalsList[wellNumber], self._trackingProbabilityOfHeadingGoodCalculation[wellNumber])
    
    return {wellNumber: extractParameters([self._trackingHeadTailAllAnimalsList[wellNumber], self._trackingHeadingAllAnimalsList[wellNumber], [], 0, 0] + ([self._auDessusPerAnimalIdList[wellNumber]] if self._auDessusPerAnimalIdList is not None else []), wellNumber, self._hyperparameters, self._videoPath, self._wellPositions, self._background)
            for wellNumber in range(self._firstWell, self._lastWell + 1)}

  def run(self):
    self._background = self.getBackground()
    
    cap = zzVideoReading.VideoCapture(self._videoPath)
    if (cap.isOpened()== False):
      print("Error opening video stream or file")

    if "backgroundSubtractorKNN_history" in self._hyperparameters and self._hyperparameters["backgroundSubtractorKNN_history"]:
      if "backgroundSubtractorKNN_dist2Threshold" in self._hyperparameters and self._hyperparameters["backgroundSubtractorKNN_dist2Threshold"]:
        dist2Threshold = int(self._hyperparameters["backgroundSubtractorKNN_dist2Threshold"])
      else:
        dist2Threshold = 400
      fgbg = cv2.createBackgroundSubtractorKNN(int(self._hyperparameters["backgroundSubtractorKNN_history"]), dist2Threshold)
    else:
      fgbg = cv2.createBackgroundSubtractorKNN()
    
    for i in range(0, min(self._lastFrame - 1, 500), int(min(self._lastFrame - 1, 500) / 10)):
      cap.set(1, min(self._lastFrame - 1, 500) - i)
      ret, frame = cap.read()
      fgmask = fgbg.apply(frame)
    cap.release()
    cap = zzVideoReading.VideoCapture(self._videoPath)
    
    queue1 = deque()
    queue2 = deque()
    queue3 = deque()
    
    i = self._firstFrame

    if self._firstFrame:
      cap.set(1, self._firstFrame)

    previousFrames = None
    widgets = None
    while (i < self._lastFrame + 1):

      if (self._hyperparameters["freqAlgoPosFollow"] != 0) and (i % self._hyperparameters["freqAlgoPosFollow"] == 0):
        print("Tracking: frame:",i)
        if self._hyperparameters["popUpAlgoFollow"]:
          from zebrazoom.code.popUpAlgoFollow import prepend

      if self._hyperparameters["debugTracking"]:
        print("frame:",i)

      ret, frame = cap.read()

      if ret:
        
        frameOri = frame.copy()
        if self._hyperparameters["detectMovementWithRawVideoInsideTracking"]:
          frameOri = cv2.cvtColor(frameOri, cv2.COLOR_BGR2GRAY)
        
        if "removeShades" in self._hyperparameters and self._hyperparameters["removeShades"]:
          if len(queue1) >= 20:
            oldFrame1 = queue1.popleft()
          else:
            oldFrame1 = frameOri.copy()
          queue1.append(frameOri.copy())
          if len(queue2) >= 50:
            oldFrame2 = queue2.popleft()
          else:
            oldFrame2 = frameOri.copy()
          queue2.append(frameOri.copy())
          if len(queue3) >= 100:
            oldFrame3 = queue3.popleft()
          else:
            oldFrame3 = frameOri.copy()
          queue3.append(frameOri.copy())
        else:
          oldFrame1 = 0
          oldFrame2 = 0
          oldFrame3 = 0
        
        frame = fgbg.apply(frame)
        frame = 255 - frame

        for wellNumber in range(self._firstWell, self._lastWell + 1):
          minPixelDiffForBackExtract = self._hyperparameters["minPixelDiffForBackExtract"]
          xtop = self._wellPositions[wellNumber]['topLeftX']
          ytop = self._wellPositions[wellNumber]['topLeftY']
          lenX = self._wellPositions[wellNumber]['lengthX']
          lenY = self._wellPositions[wellNumber]['lengthY']
          grey = frame
          
          curFrame = grey[ytop:ytop+lenY, xtop:xtop+lenX].copy()
            
          if self._hyperparameters["paramGaussianBlur"]:
            blur = cv2.GaussianBlur(curFrame, (self._hyperparameters["paramGaussianBlur"], self._hyperparameters["paramGaussianBlur"]),0)
          else:
            blur = curFrame
          if "headingCalculationMethod" in self._hyperparameters:
            t, thresh1 = cv2.threshold(curFrame, 254, 255, cv2.THRESH_BINARY)
            t, thresh2 = cv2.threshold(curFrame, 254, 255, cv2.THRESH_BINARY)
          else:
            thresh1 = 0
            thresh2 = 0
          gray    = 0

          headPositionFirstFrame = 0

          # Head tracking and heading calculation
          lastFirstTheta = _headTrackingHeadingCalculation(self, i, blur, thresh1, thresh2, frameOri, self._hyperparameters["erodeSize"], int(cap.get(3)), int(cap.get(4)), self._trackingHeadingAllAnimalsList[wellNumber], self._trackingHeadTailAllAnimalsList[wellNumber], self._trackingProbabilityOfGoodDetectionList[wellNumber], headPositionFirstFrame, self._wellPositions[wellNumber]["lengthX"], 0, 0, wellNumber, [oldFrame1, oldFrame2, oldFrame3])

          self._debugTracking(i, self._trackingHeadTailAllAnimalsList[wellNumber], self._trackingHeadingAllAnimalsList[wellNumber], curFrame)

          if self._hyperparameters["freqAlgoPosFollow"]:
            if i % self._hyperparameters["freqAlgoPosFollow"] == 0:
              print("Tracking at frame", i)

        if self._hyperparameters["detectMovementWithRawVideoInsideTracking"]:
          previousFrames = self._detectMovementWithRawVideoInsideTracking(i, frameOri, previousFrames)
      
      paramsAdjusted = self._adjustParameters(i, frame, widgets)
      if paramsAdjusted is not None:
        i, widgets = paramsAdjusted
        cap.set(1, i)
      else:
        i = i + 1
    
    if self._hyperparameters["detectMovementWithRawVideoInsideTracking"]:
      frameGapComparision = self._hyperparameters["frameGapComparision"]
      nbFrames = len(self._trackingHeadTailAllAnimalsList[0][0])
      for wellNumber in range(len(self._trackingHeadTailAllAnimalsList)):
        for animalId in range(len(self._trackingHeadTailAllAnimalsList[wellNumber])):
          self._auDessusPerAnimalIdList[wellNumber][animalId][:nbFrames-frameGapComparision] = self._auDessusPerAnimalIdList[wellNumber][animalId][frameGapComparision:nbFrames]
      
    cap.release()
    return self._formatOutput()


zebrazoom.code.tracking.register_tracking_method('multipleCenterOfMassTracking', MultipleCenterOfMassTracking)
