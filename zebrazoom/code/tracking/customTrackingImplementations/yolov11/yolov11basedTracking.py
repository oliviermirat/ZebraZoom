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
    
    DLmodelPath = self._hyperparameters["DLmodelPath"]
    if os.path.isabs(DLmodelPath):
      modelPathCandidates = [DLmodelPath]
    else:
      modelPathCandidates = []
      if self._hyperparameters.get("configFileFolder"):
        modelPathCandidates.append(os.path.join(self._hyperparameters["configFileFolder"], DLmodelPath))
      modelPathCandidates.append(DLmodelPath)
      modelPathCandidates.append(os.path.join('zebrazoom', 'configuration', DLmodelPath))
      modelPathCandidates.append(os.path.join('ZebraZoom', 'zebrazoom', 'configuration', DLmodelPath))

    for modelPathCandidate in modelPathCandidates:
      if os.path.exists(modelPathCandidate):
        model = YOLO(modelPathCandidate)
        break
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
          
          if not(("centerOfMass_YOLO_hybridSORT" in self._hyperparameters) and self._hyperparameters["centerOfMass_YOLO_hybridSORT"]):
          
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
          
          else:

            # One HybridSort instance + one slot map per well, created the first time each well is seen.
            # Move this into __init__ if you'd rather not check hasattr() every frame.
            if not hasattr(self, "_hybridSortTrackerForWell"):
                try:
                  from boxmot.trackers.bbox import HybridSort
                except ImportError as e:
                  raise ImportError("centerOfMass_YOLO_hybridSORT requires a version of boxmot providing "
                                     "boxmot.trackers.bbox.HybridSort, which isn't available in this environment") from e
                self._HybridSort = HybridSort
                self._hybridSortTrackerForWell = {}   # wellNum -> HybridSort instance
                self._animalNumForTrackId = {}        # wellNum -> {trackId: animalNum}

            if wellNum not in self._hybridSortTrackerForWell:
                self._hybridSortTrackerForWell[wellNum] = self._HybridSort(
                    det_thresh=self._hyperparameters["yolo11MinConf"],
                    with_reid=False,     # no appearance model needed/available for this use case
                    cmc_method=None,     # camera is static per well, skip motion compensation
                    max_age=30,          # frames a track survives with no matching detection - tune to your fps
                    min_hits=1,          # confirm a track immediately, matching your original per-frame behavior
                    iou_threshold=0.3,
                    asso_func="giou",
                )
                self._animalNumForTrackId[wellNum] = {}

            tracker = self._hybridSortTrackerForWell[wellNum]
            nbAnimalsPerWell = self._hyperparameters["nbAnimalsPerWell"]
            slotOfTrackId = self._animalNumForTrackId[wellNum]

            # Build the [x1, y1, x2, y2, conf, cls] array HybridSort expects, keeping only
            # detections that pass the minimum-confidence hyperparameter
            dets = []
            for result in results[0].boxes:
                conf = float(result.conf[0])
                if conf >= self._hyperparameters["yolo11MinConf"]:
                    xmin, ymin, xmax, ymax = result.xyxy[0]
                    dets.append([float(xmin), float(ymin), float(xmax), float(ymax), conf, 0])  # cls=0: single-class detector
            dets = np.array(dets, dtype=np.float32) if dets else np.empty((0, 6), dtype=np.float32)

            # `frame` must be the same image (H, W, C numpy array) you ran YOLO on for this well
            tracks = tracker.update(dets, frame)

            # Free slots only for tracks HybridSort has actually dropped — a brief occlusion keeps
            # a track's id alive internally (within max_age) even though it's absent from this frame's output
            aliveTrackIds = {int(t.id) for t in tracker.active_tracks}
            for trackId in [t for t in slotOfTrackId if t not in aliveTrackIds]:
                del slotOfTrackId[trackId]

            # Give free slots to new tracks, most-confident first, until nbAnimalsPerWell is reached
            order = sorted(range(len(tracks)), key=lambda i: tracks.conf[i], reverse=True)
            usedSlots = set(slotOfTrackId.values())
            for i in order:
                trackId = int(tracks.id[i])
                if trackId not in slotOfTrackId and len(slotOfTrackId) < nbAnimalsPerWell:
                    freeSlot = next(s for s in range(nbAnimalsPerWell) if s not in usedSlots)
                    slotOfTrackId[trackId] = freeSlot
                    usedSlots.add(freeSlot)

            # Write each tracked animal into its stable slot for this frame
            for i in order:
                animalNum = slotOfTrackId.get(int(tracks.id[i]))
                if animalNum is None:
                    continue  # more live tracks than nbAnimalsPerWell slots; the least promising are dropped

                xmin, ymin, xmax, ymax = tracks.xyxy[i]
                xCenter = float((xmin + xmax) / 2)
                yCenter = float((ymin + ymax) / 2)

                self._trackingHeadTailAllAnimalsList[wellNum][animalNum, frameNum-self._firstFrame][0][0] = int(xCenter)
                self._trackingHeadTailAllAnimalsList[wellNum][animalNum, frameNum-self._firstFrame][0][1] = int(yCenter)
                self._trackingProbabilityOfGoodDetectionList[wellNum][animalNum, frameNum-self._firstFrame] = float(tracks.conf[i])
            
      frameNum += 1
    
    if frameNum-self._firstFrame < len(self._trackingHeadTailAllAnimalsList[wellNum][0]):
      for animalNum in range(self._hyperparameters["nbAnimalsPerWell"]):
        self._trackingHeadTailAllAnimalsList[wellNum][animalNum, frameNum-self._firstFrame][0][0] = self._trackingHeadTailAllAnimalsList[wellNum][animalNum, frameNum-self._firstFrame-1][0][0]
        self._trackingHeadTailAllAnimalsList[wellNum][animalNum, frameNum-self._firstFrame][0][1] = self._trackingHeadTailAllAnimalsList[wellNum][animalNum, frameNum-self._firstFrame-1][0][1]
    
    cap.release()
    
    return self._formatOutput()


zebrazoom.code.tracking.register_tracking_method('yolov11basedTracking', Yolov11basedTracking)
