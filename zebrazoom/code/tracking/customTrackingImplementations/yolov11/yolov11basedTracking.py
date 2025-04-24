# from zebrazoom.code.tracking.customTrackingImplementations.fastFishTracking.detectMovementWithRawVideoInsideTracking import detectMovementWithRawVideoInsideTracking
from zebrazoom.code.tracking.customTrackingImplementations.yolov11.trackTailWithClassicalCV import trackTailWithClassicalCV
from zebrazoom.code.tracking.customTrackingImplementations.yolov11.trackTailWithYOLO import trackTailWithYOLO
from zebrazoom.code.extractParameters import extractParameters

import cv2
import os
import zebrazoom.videoFormatConversion.zzVideoReading as zzVideoReading
import numpy as np
from zebrazoom.code.tracking import register_tracking_method
from ..._fasterMultiprocessingBase import BaseFasterMultiprocessing

import zebrazoom.code.tracking

from ultralytics import YOLO


class Yolov11basedTracking(BaseFasterMultiprocessing):
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
    
    return {wellNumber: extractParameters([self._trackingHeadTailAllAnimalsList[wellNumber], self._trackingHeadingAllAnimalsList[wellNumber], [], 0, 0] + ([self._auDessusPerAnimalIdList[wellNumber]] if self._auDessusPerAnimalIdList is not None else []), wellNumber, self._hyperparameters, self._videoPath, self._wellPositions, self._background, 0, self._trackingProbabilityOfGoodDetectionList[wellNumber])
            for wellNumber in range(self._firstWell, self._lastWell + 1)}

  def run(self):
    
    if os.path.exists(self._hyperparameters["DLmodelPath"]):
      model = YOLO(self._hyperparameters["DLmodelPath"])
    elif os.path.exists(os.path.join('zebrazoom', 'configuration', self._hyperparameters["DLmodelPath"])):
      model = YOLO(os.path.join('zebrazoom', 'configuration', self._hyperparameters["DLmodelPath"]))
    elif os.path.exists(os.path.join('ZebraZoom', 'zebrazoom', 'configuration', self._hyperparameters["DLmodelPath"])):
      model = YOLO(os.path.join('ZebraZoom', 'zebrazoom', 'configuration', self._hyperparameters["DLmodelPath"]))
    else:
      print("Path to DL model not found")
      raise ValueError("Path to DL model not found")
    
    if self._hyperparameters["trackTail"] or (("onlyRecenterHeadPosition" in self._hyperparameters) and (self._hyperparameters["onlyRecenterHeadPosition"] == 1)):
      self._lastFirstTheta = np.zeros(len(self._wellPositions))
      self._lastFirstTheta[:] = -99999
      
    if "trackTailWithYOLO" in self._hyperparameters and self._hyperparameters["trackTailWithYOLO"]:
      prev_contours = [0] * self._hyperparameters["nbAnimalsPerWell"]
      disappeared_counts = [0] * self._hyperparameters["nbAnimalsPerWell"]
      numAlreadyInvertedWithThePast = [0] * int(self._hyperparameters["nbAnimalsPerWell"])
    
    wellNum = 0
    
    # Open the video
    cap = cv2.VideoCapture(self._videoPath)
    frameNum = 0
    while cap.isOpened() and frameNum <= self._lastFrame:
      
      ret, frame = cap.read()
      if not ret:
        break
        
      # if self._hyperparameters["detectMovementWithRawVideoInsideTracking"]:
        # prevFrame = detectMovementWithRawVideoInsideTracking(self, k, frame)
        # if ("detectMovementCompareWithTheFuture" in self._hyperparameters) and self._hyperparameters["detectMovementCompareWithTheFuture"]:
          # frame = prevFrame
      
      if self._hyperparameters["trackTail"] or (("onlyRecenterHeadPosition" in self._hyperparameters) and (self._hyperparameters["onlyRecenterHeadPosition"] == 1)):
        frameGaussianBlur = frame.copy()
        paramGaussianBlur = self._hyperparameters["paramGaussianBlur"]
        frameGaussianBlur = cv2.GaussianBlur(frameGaussianBlur, (paramGaussianBlur, paramGaussianBlur), 0)
        if ("paramGaussianBlurForHeadPosition" in self._hyperparameters) and self._hyperparameters["paramGaussianBlurForHeadPosition"]:
          frameGaussianBlurForHeadPosition = frame.copy()
          frameGaussianBlurForHeadPosition = cv2.GaussianBlur(frameGaussianBlurForHeadPosition, (self._hyperparameters["paramGaussianBlurForHeadPosition"], self._hyperparameters["paramGaussianBlurForHeadPosition"]), 0)
        else:
          frameGaussianBlurForHeadPosition = frameGaussianBlur
      
      if frameNum >= self._firstFrame:
      
        if frameNum % self._hyperparameters["freqAlgoPosFollow"] == 0:
          print("YOLO tracking at frame", frameNum)
        
        if "yolo11MinConf" in self._hyperparameters:
          results = model(frame, verbose=False, conf=float(self._hyperparameters["yolo11MinConf"]))
        else:
          results = model(frame, verbose=False)
          
        # Set to True for debugging
        if False:
          result = results[0]
          # Draw contours if masks are available
          if result.masks is not None:
            for idx, mask in enumerate(result.masks.data):
              # Convert mask tensor to uint8 numpy array
              mask_np = (mask.cpu().numpy() * 255).astype(np.uint8)
              # Find contours
              contours, _ = cv2.findContours(mask_np, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
              # Draw contours on the original frame
              if idx == 0:
                cv2.drawContours(frame, contours, -1, (0, 255, 0), 2)
              else:
                cv2.drawContours(frame, contours, -1, (0, 0, 255), 2)
          # Show the result
          import zebrazoom.code.util as util
          util.showFrame(frame, title="write title here")
          ################          
        
        if "trackTailWithYOLO" in self._hyperparameters and self._hyperparameters["trackTailWithYOLO"]:
          
          [prev_contours, disappeared_counts] = trackTailWithYOLO(self, frame, results, frameNum, wellNum, prev_contours, disappeared_counts, numAlreadyInvertedWithThePast)
          
        else:
          animalNum = 0

          for animalNum, result in enumerate(results[0].boxes):
            
            if animalNum < self._hyperparameters["nbAnimalsPerWell"]:
              xmin, ymin, xmax, ymax = result.xyxy[0]
              
              if self._hyperparameters["trackTail"] or (("onlyRecenterHeadPosition" in self._hyperparameters) and (self._hyperparameters["onlyRecenterHeadPosition"] == 1)):
                trackTailWithClassicalCV(self, frameGaussianBlur, frameGaussianBlurForHeadPosition, xmin, ymin, xmax, ymax, wellNum, animalNum, frameNum)
              else:
                xCenter = float((xmin + xmax) / 2)
                yCenter = float((ymin + ymax) / 2)
                self._trackingHeadTailAllAnimalsList[wellNum][animalNum, frameNum-self._firstFrame][0][0] = int(xCenter)
                self._trackingHeadTailAllAnimalsList[wellNum][animalNum, frameNum-self._firstFrame][0][1] = int(yCenter)
              
              self._trackingProbabilityOfGoodDetectionList[wellNum][animalNum, frameNum-self._firstFrame] = float(result.conf[0])
      
      frameNum += 1
    
    if frameNum-self._firstFrame < len(self._trackingHeadTailAllAnimalsList[wellNum][0]):
      for animalNum in range(self._hyperparameters["nbAnimalsPerWell"]):
        self._trackingHeadTailAllAnimalsList[wellNum][animalNum, frameNum-self._firstFrame][0][0] = self._trackingHeadTailAllAnimalsList[wellNum][animalNum, frameNum-self._firstFrame-1][0][0]
        self._trackingHeadTailAllAnimalsList[wellNum][animalNum, frameNum-self._firstFrame][0][1] = self._trackingHeadTailAllAnimalsList[wellNum][animalNum, frameNum-self._firstFrame-1][0][1]
    
    cap.release()
    
    return self._formatOutput()


zebrazoom.code.tracking.register_tracking_method('yolov11basedTracking', Yolov11basedTracking)
