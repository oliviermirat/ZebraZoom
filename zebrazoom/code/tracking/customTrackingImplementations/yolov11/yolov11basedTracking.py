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
    
    return {wellNumber: extractParameters([self._trackingHeadTailAllAnimalsList[wellNumber], self._trackingHeadingAllAnimalsList[wellNumber], [], 0, 0] + ([self._auDessusPerAnimalIdList[wellNumber]] if self._auDessusPerAnimalIdList is not None else []), wellNumber, self._hyperparameters, self._videoPath, self._wellPositions, self._background)
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
    
    wellNum = 0
    
    # Open the video
    cap = cv2.VideoCapture(self._videoPath)
    frameNum = 0
    while cap.isOpened() and frameNum <= self._lastFrame:
      
      ret, frame = cap.read()
      if not ret:
        break
      
      if frameNum >= self._firstFrame:
      
        if frameNum % self._hyperparameters["freqAlgoPosFollow"] == 0:
          print("YOLO tracking at frame", frameNum)
        
        results = model(frame, verbose=False)

        animalNum = 0

        for animalNum, result in enumerate(results[0].boxes):
          
          if animalNum < self._hyperparameters["nbAnimalsPerWell"]:
            xmin, ymin, xmax, ymax = result.xyxy[0]
            
            xCenter = float((xmin + xmax) / 2)
            yCenter = float((ymin + ymax) / 2)
            self._trackingHeadTailAllAnimalsList[wellNum][animalNum, frameNum-self._firstFrame][0][0] = int(xCenter)
            self._trackingHeadTailAllAnimalsList[wellNum][animalNum, frameNum-self._firstFrame][0][1] = int(yCenter)
      
      frameNum += 1
    
    if frameNum <= len(self._trackingHeadTailAllAnimalsList[wellNum][animalNum]):
      for animalNum in range(self._hyperparameters["nbAnimalsPerWell"]):
        self._trackingHeadTailAllAnimalsList[wellNum][animalNum, frameNum-self._firstFrame][0][0] = self._trackingHeadTailAllAnimalsList[wellNum][animalNum, frameNum-self._firstFrame-1][0][0]
        self._trackingHeadTailAllAnimalsList[wellNum][animalNum, frameNum-self._firstFrame][0][1] = self._trackingHeadTailAllAnimalsList[wellNum][animalNum, frameNum-self._firstFrame-1][0][1]
    
    cap.release()
    
    return self._formatOutput()


zebrazoom.code.tracking.register_tracking_method('yolov11basedTracking', Yolov11basedTracking)
