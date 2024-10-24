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


class MultipleCenterOfMassTracking(BaseFasterMultiprocessing, EyeTrackingMixin, GetImagesMixin):
  def __init__(self, videoPath, wellPositions, hyperparameters):
    super().__init__(videoPath, wellPositions, hyperparameters)
    if self._hyperparameters["eyeTracking"]:
      self._trackingEyesAllAnimalsList = [np.zeros((self._hyperparameters["nbAnimalsPerWell"], self._lastFrame-self._firstFrame+1, 8))
                                          for _ in range(self._hyperparameters["nbWells"])]
    else:
      self._trackingEyesAllAnimals = 0

    # if not(self._hyperparameters["nbAnimalsPerWell"] > 1) and not(self._hyperparameters["headEmbeded"]) and (self._hyperparameters["findHeadPositionByUserInput"] == 0) and (self._hyperparameters["takeTheHeadClosestToTheCenter"] == 0):
    self._trackingProbabilityOfGoodDetectionList = [np.zeros((self._hyperparameters["nbAnimalsPerWell"], self._lastFrame-self._firstFrame+1))
                                                      for _ in range(self._hyperparameters["nbWells"])]
    # else:
      # self._trackingProbabilityOfGoodDetectionList = 0
    
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

    if self._hyperparameters["backgroundSubtractorKNN"]:
      fgbg = cv2.createBackgroundSubtractorKNN()
      for i in range(0, min(self._lastFrame - 1, 500), int(min(self._lastFrame - 1, 500) / 10)):
        cap.set(1, min(self._lastFrame - 1, 500) - i)
        ret, frame = cap.read()
        fgmask = fgbg.apply(frame)
      cap.release()
      cap = zzVideoReading.VideoCapture(self._videoPath)

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

          # prepend("Tracking: frame:" + str(i))

      if self._hyperparameters["debugTracking"]:
        print("frame:",i)

      ret, frame = cap.read()

      if ret:
        
        frameOri = frame.copy()
        if self._hyperparameters["detectMovementWithRawVideoInsideTracking"]:
          frameOri = cv2.cvtColor(frameOri, cv2.COLOR_BGR2GRAY)
        
        if self._hyperparameters["backgroundSubtractorKNN"]:
          frame = fgbg.apply(frame)
          frame = 255 - frame

        for wellNumber in range(self._firstWell, self._lastWell + 1):
          # if self._hyperparameters["nbAnimalsPerWell"] == 1 and not(self._hyperparameters["forceBlobMethodForHeadTracking"]):
          minPixelDiffForBackExtract = self._hyperparameters["minPixelDiffForBackExtract"]
          xtop = self._wellPositions[wellNumber]['topLeftX']
          ytop = self._wellPositions[wellNumber]['topLeftY']
          lenX = self._wellPositions[wellNumber]['lengthX']
          lenY = self._wellPositions[wellNumber]['lengthY']
          if self._hyperparameters["backgroundSubtractorKNN"]:
            grey = frame
          else:
            grey = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
          
          curFrame = grey[ytop:ytop+lenY, xtop:xtop+lenX].copy()
          # if not(self._hyperparameters["backgroundSubtractorKNN"]):
            # back = self._background[ytop:ytop+lenY, xtop:xtop+lenX]
            # putToWhite = ( curFrame.astype('int32') >= (back.astype('int32') - minPixelDiffForBackExtract) )
            # curFrame[putToWhite] = 255
          # else:
            # print("here")
            # self._hyperparameters["paramGaussianBlur"] = int(math.sqrt(cv2.countNonZero(255 - curFrame) / self._hyperparameters["nbAnimalsPerWell"]) / 2) * 2 + 1
          
          self._hyperparameters["paramGaussianBlur"] = 31 #15 #31
            
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
          # else:
            # [frame2, gray, thresh1, blur, thresh2, frame2, initialCurFrame, back, xHead, yHead] = self._getImages(0, i, wellNumber, frame)

          headPositionFirstFrame = 0

          # Head tracking and heading calculation
          lastFirstTheta = _headTrackingHeadingCalculation(self, i, blur, thresh1, thresh2, frameOri, self._hyperparameters["erodeSize"], int(cap.get(3)), int(cap.get(4)), self._trackingHeadingAllAnimalsList[wellNumber], self._trackingHeadTailAllAnimalsList[wellNumber], self._trackingProbabilityOfGoodDetectionList[wellNumber], headPositionFirstFrame, self._wellPositions[wellNumber]["lengthX"], 0, 0, wellNumber)

          # Tail tracking for frame i
          if self._hyperparameters["trackTail"] == 1 :
            threshForBlackFrames = 0
            thetaDiffAccept = 1.2
            lastFirstTheta = 0
            maxDepth = 0
            tailTipFirstFrame = []
            for animalId in range(0, self._hyperparameters["nbAnimalsPerWell"]):
              self._tailTracking(animalId, i, frame, thresh1, threshForBlackFrames, thetaDiffAccept, self._trackingHeadTailAllAnimalsList[wellNumber], self._trackingHeadingAllAnimalsList[wellNumber], lastFirstTheta, maxDepth, tailTipFirstFrame, initialCurFrame.copy(), back)

          # Eye tracking for frame i
          if self._hyperparameters["eyeTracking"]:
            self._eyeTracking(animalId, i, frame, thresh1, self._trackingHeadingAllAnimalsList[wellNumber], self._trackingHeadTailAllAnimalsList[wellNumber], self._trackingHeadingAllAnimalsList[wellNumber])

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
