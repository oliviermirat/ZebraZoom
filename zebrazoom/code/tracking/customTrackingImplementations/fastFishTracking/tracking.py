from zebrazoom.code.tracking.customTrackingImplementations.fastFishTracking.utilities import calculateAngle, distBetweenThetas
from zebrazoom.code.tracking.customTrackingImplementations.fastFishTracking.detectMovementWithTrackedDataAfterTracking import detectMovementWithTrackedDataAfterTracking
from zebrazoom.code.tracking.customTrackingImplementations.fastFishTracking.detectMovementWithRawVideoInsideTracking import detectMovementWithRawVideoInsideTracking
from zebrazoom.code.tracking.customTrackingImplementations.fastFishTracking.getListOfWellsOnWhichToRunTheTracking import getListOfWellsOnWhichToRunTheTracking
from zebrazoom.code.tracking.customTrackingImplementations.fastFishTracking.backgroundSubtractionOnWholeImage import backgroundSubtractionOnWholeImage
from zebrazoom.code.tracking.customTrackingImplementations.fastFishTracking.backgroundSubtractionOnlyOnROIs import backgroundSubtractionOnlyOnROIs
import zebrazoom.videoFormatConversion.zzVideoReading as zzVideoReading
from zebrazoom.code.extractParameters import extractParameters
import zebrazoom.code.util as util
import zebrazoom.code.tracking
import numpy as np
import queue
import math
import time
import cv2

from ..._updateBackgroundAtInterval import UpdateBackgroundAtIntervalMixin


class Tracking(zebrazoom.code.tracking.BaseTrackingMethod, UpdateBackgroundAtIntervalMixin):
  
  def __init__(self, videoPath, wellPositions, hyperparameters):
    self._videoPath = videoPath
    self._wellPositions = wellPositions
    self._hyperparameters = hyperparameters
    self._auDessusPerAnimalIdList = None
    
    self.cap = zzVideoReading.VideoCapture(self._videoPath, self._hyperparameters)
    if (self.cap.isOpened()== False):
      print("Error opening video stream or file")
    if ("readEventBasedData" in self._hyperparameters) and self._hyperparameters["readEventBasedData"]:
      self._hyperparameters["lastFrame"] = int(self.cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    self._firstFrame = self._hyperparameters["firstFrame"]
    self._lastFrame = self._hyperparameters["lastFrame"]
    self._nbTailPoints = self._hyperparameters["nbTailPoints"]
    self._previousFrames = None
    self._trackingDataPerWell = [np.zeros((self._hyperparameters["nbAnimalsPerWell"], self._lastFrame-self._firstFrame+1, self._nbTailPoints, 2)) for _ in range(len(self._wellPositions))]
    self._lastFirstTheta = np.zeros(len(self._wellPositions))
    self._lastFirstTheta[:] = -99999
    self._listOfWellsOnWhichToRunTheTracking = [i for i in range(0, len(self._wellPositions))] if hyperparameters["onlyTrackThisOneWell"] == -1 else [hyperparameters["onlyTrackThisOneWell"]]
    self._times2 = np.zeros((self._lastFrame - self._firstFrame + 1, 5))
    self._printInterTime = False

  def _debugFrame(self, frame, title=None, buttons=(), timeout=None):
    util.showFrame(frame, title=title, buttons=buttons, timeout=timeout)

  def _adjustParameters(self, i, frame, unprocessedFrame, widgets):
    return None

  def run(self):
    
    ### Step 1 (out of 2): Tracking:
    resizeFrameFactor = self._hyperparameters["resizeFrameFactor"] if "resizeFrameFactor" in self._hyperparameters else 0
    
    # Getting video reader
    cap = self.cap
    if (cap.isOpened()== False):
      print("Error opening video stream or file")
    
    # Simple background extraction with first and last frame of the video + Getting list of wells on which to run the tracking
    ret, self._background = cap.read()
    if resizeFrameFactor:
      self._background = cv2.resize(self._background, (int(len(self._background[0])/resizeFrameFactor), int(len(self._background)/resizeFrameFactor)))
    if "lastFrameForInitialBackDetect" in self._hyperparameters and self._hyperparameters["lastFrameForInitialBackDetect"]:
      if int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) <= self._hyperparameters["lastFrameForInitialBackDetect"]:
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) - 1)
      else:
        cap.set(cv2.CAP_PROP_POS_FRAMES, self._hyperparameters["lastFrameForInitialBackDetect"])
    else:
      cap.set(cv2.CAP_PROP_POS_FRAMES, int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) - 1)
    ret, frame = cap.read()
    while not(ret):
      cap.set(cv2.CAP_PROP_POS_FRAMES, int(cap.get(cv2.CAP_PROP_POS_FRAMES)) - 1)
      ret, frame = cap.read()
    if resizeFrameFactor:
      frame = cv2.resize(frame, (int(len(frame[0])/resizeFrameFactor), int(len(frame)/resizeFrameFactor)))
    if self._hyperparameters["chooseWellsToRunTrackingOnWithFirstAndLastFrame"] and self._hyperparameters["onlyTrackThisOneWell"] == -1:
      self._listOfWellsOnWhichToRunTheTracking = getListOfWellsOnWhichToRunTheTracking(self, self._background[:,:,0], frame[:,:,0])
    print("listOfWellsOnWhichToRunTheTracking:", self._listOfWellsOnWhichToRunTheTracking)
    if not("noBackgroundSubtraction" in self._hyperparameters) or not(self._hyperparameters["noBackgroundSubtraction"]):
      if not(self._hyperparameters["useFirstFrameAsBackground"]):
        self._background = cv2.max(frame, self._background) # INCONSISTENT!!! should be changed!
      if len(self._background.shape) == 3 and self._background.shape[2] == 3:
        self._background = cv2.cvtColor(self._background, cv2.COLOR_BGR2GRAY) # INCONSISTENT!!! should be changed!
    cap.set(cv2.CAP_PROP_POS_FRAMES, self._firstFrame)
    
    if resizeFrameFactor:
      initialWellPositions = self._wellPositions.copy()
      self._wellPositions = [{'topLeftX': int(pos['topLeftX']/resizeFrameFactor), 'topLeftY': int(pos['topLeftY']/resizeFrameFactor), 'lengthX': int(pos['lengthX']/resizeFrameFactor), 'lengthY': int(pos['lengthY']/resizeFrameFactor)} for pos in self._wellPositions]
    
    # Initializing variables
    times  = np.zeros((self._lastFrame - self._firstFrame + 1, 2))
    ret = True
    
    # Going through each frame of the video
    widgets = None
    startTime = time.time()
    k = self._firstFrame
    while (ret and k <= self._lastFrame):
      if self._hyperparameters["freqAlgoPosFollow"] and k % self._hyperparameters["freqAlgoPosFollow"] == 0:
        print("Tracking at frame", k)
      time1 = time.time()
      if self._hyperparameters['adjustFreelySwimTracking']:
        cap.set(1, k)
      ret, frame = cap.read()
      time2 = time.time()
      if resizeFrameFactor:
        frame = cv2.resize(frame, (int(len(frame[0])/resizeFrameFactor), int(len(frame)/resizeFrameFactor)))
      if ret:
        if self._hyperparameters["backgroundSubtractionOnWholeImage"] or k == self._firstFrame:
          frameROI, unprocessedFrameROI = backgroundSubtractionOnWholeImage(self, frame, k-self._firstFrame)
        else:
          backgroundSubtractionOnlyOnROIs(self, frame, k-self._firstFrame)
        if self._hyperparameters["updateBackgroundAtInterval"]:
          for wellNumber in range(0, len(self._wellPositions)):
            self._updateBackgroundAtInterval(k, wellNumber, frame[self._wellPositions[wellNumber]["topLeftY"]:self._wellPositions[wellNumber]["topLeftY"]+self._wellPositions[wellNumber]["lengthY"], self._wellPositions[wellNumber]["topLeftX"]:self._wellPositions[wellNumber]["topLeftX"]+self._wellPositions[wellNumber]["lengthX"], 0], self._trackingDataPerWell[wellNumber], frame)
      
      time3 = time.time()
      times[k-self._firstFrame, 0] = time2 - time1
      times[k-self._firstFrame, 1] = time3 - time2
      adjustParamsInfo = self._adjustParameters(k, frameROI, unprocessedFrameROI, widgets)
      if adjustParamsInfo is not None:
        k, widgets = adjustParamsInfo
        if self._nbTailPoints != self._hyperparameters["nbTailPoints"]:
          self._nbTailPoints = self._hyperparameters["nbTailPoints"]
          self._trackingDataPerWell = [np.zeros((self._hyperparameters["nbAnimalsPerWell"], self._lastFrame-self._firstFrame+1, self._nbTailPoints, 2)) for _ in range(len(self._wellPositions))]
      else:
        k += 1
    
    
    if resizeFrameFactor:
      self._trackingDataPerWell = [resizeFrameFactor * elem for elem in self._trackingDataPerWell]
      self._wellPositions = initialWellPositions
    
    endTime = time.time()
    
    cap.release()
    
    if self._hyperparameters["detectMovementWithRawVideoInsideTracking"] and ("detectMovementCompareWithTheFuture" in self._hyperparameters) and self._hyperparameters["detectMovementCompareWithTheFuture"]:
      frameGapComparision = self._hyperparameters["frameGapComparision"]
      nbFrames = len(self._trackingDataPerWell[0][0])
      for wellNumber in range(len(self._trackingDataPerWell)):
        for animalId in range(len(self._trackingDataPerWell[wellNumber])):
          self._trackingDataPerWell[wellNumber][animalId][:nbFrames-frameGapComparision][:][:] = self._trackingDataPerWell[wellNumber][animalId][frameGapComparision:nbFrames][:][:]
          self._auDessusPerAnimalIdList[wellNumber][animalId][:nbFrames-frameGapComparision] = self._auDessusPerAnimalIdList[wellNumber][animalId][frameGapComparision:nbFrames]
    
    print("")
    print("Color to grey:"           , np.median(self._times2[:,0]))
    print("Bout detection:"          , np.median(self._times2[:,1]))
    print("Background substraction:" , np.median(self._times2[:,2]))
    print("Gaussian blur:"           , np.median(self._times2[:,3]))
    print("Tracking on each well:"   , np.median(self._times2[:,4]))
    
    loadingImagesTime       = np.median(times[:,0])
    processingImagesTime    = np.median(times[:,1])
    percentTimeSpentLoading = loadingImagesTime / (loadingImagesTime + processingImagesTime)
    print("Median time spent on: Loading images:", loadingImagesTime, "; Processing images:", processingImagesTime)
    print("Percentage of time spent loading images:", percentTimeSpentLoading*100)
    print("Total tracking Time:", endTime - startTime)
    print("Tracking Time (without loading image):", (endTime - startTime) * (1 - percentTimeSpentLoading))
    print("Total tracking fps:", k / (endTime - startTime))
    print("Tracking fps (without loading image):", k / ((endTime - startTime) * (1 - percentTimeSpentLoading)))
    print("")
    
    ### Step 2 (out of 2): Extracting bout of movements:
    
    if self._hyperparameters["detectMovementWithRawVideoInsideTracking"] and self._hyperparameters["thresForDetectMovementWithRawVideo"]:
    
      trackingHeadingAllAnimalsList = [[[((calculateAngle(self._trackingDataPerWell[wellNumber][animalNumber][i][0][0], self._trackingDataPerWell[wellNumber][animalNumber][i][0][1], self._trackingDataPerWell[wellNumber][animalNumber][i][1][0], self._trackingDataPerWell[wellNumber][animalNumber][i][1][1]) + math.pi) % (2 * math.pi) if len(self._trackingDataPerWell[wellNumber][0][i]) > 1 else 0) for i in range(0, self._lastFrame-self._firstFrame+1)] for animalNumber in range(0, self._hyperparameters["nbAnimalsPerWell"])] for wellNumber in range(0, len(self._wellPositions))]
      
      return {wellNumber: extractParameters([self._trackingDataPerWell[wellNumber], trackingHeadingAllAnimalsList[wellNumber], [], 0, 0, self._auDessusPerAnimalIdList[wellNumber]], wellNumber, self._hyperparameters, self._videoPath, self._wellPositions, self._background) for wellNumber in range(0, len(self._wellPositions))}

    elif self._hyperparameters["adjustDetectMovWithRawVideo"]:

      trackingHeadingAllAnimalsList = [[[((calculateAngle(self._trackingDataPerWell[wellNumber][animalNumber][i][0][0], self._trackingDataPerWell[wellNumber][animalNumber][i][0][1], self._trackingDataPerWell[wellNumber][animalNumber][i][1][0], self._trackingDataPerWell[wellNumber][animalNumber][i][1][1]) + math.pi) % (2 * math.pi) if len(self._trackingDataPerWell[wellNumber][0][i]) > 1 else 0) for i in range(0, self._lastFrame-self._firstFrame+1)] for animalNumber in range(0, self._hyperparameters["nbAnimalsPerWell"])] for wellNumber in range(0, len(self._wellPositions))]

      return {wellNumber: extractParameters([self._trackingDataPerWell[wellNumber], trackingHeadingAllAnimalsList[wellNumber], [], 0, 0], wellNumber, self._hyperparameters, self._videoPath, self._wellPositions, self._background) for wellNumber in self._listOfWellsOnWhichToRunTheTracking}

    elif  self._hyperparameters["coordinatesOnlyBoutDetection"]:

      trackingHeadingAllAnimalsList = [[[((calculateAngle(self._trackingDataPerWell[wellNumber][animalNumber][i][0][0], self._trackingDataPerWell[wellNumber][animalNumber][i][0][1], self._trackingDataPerWell[wellNumber][animalNumber][i][1][0], self._trackingDataPerWell[wellNumber][animalNumber][i][1][1]) + math.pi) % (2 * math.pi) if len(self._trackingDataPerWell[wellNumber][0][i]) > 1 else 0) for i in range(0, self._lastFrame-self._firstFrame+1)] for animalNumber in range(0, self._hyperparameters["nbAnimalsPerWell"])] for wellNumber in range(0, len(self._wellPositions))]

      return {wellNumber: extractParameters([self._trackingDataPerWell[wellNumber], trackingHeadingAllAnimalsList[wellNumber], [], 0, 0], wellNumber, self._hyperparameters, self._videoPath, self._wellPositions, self._background) for wellNumber in range(0, len(self._wellPositions))}

    else:
    
      if not(self._hyperparameters["detectBouts"]):
        
        trackingHeadingAllAnimalsList = [[[((calculateAngle(self._trackingDataPerWell[wellNumber][animalNumber][i][0][0], self._trackingDataPerWell[wellNumber][animalNumber][i][0][1], self._trackingDataPerWell[wellNumber][animalNumber][i][1][0], self._trackingDataPerWell[wellNumber][animalNumber][i][1][1]) + math.pi) % (2 * math.pi) if len(self._trackingDataPerWell[wellNumber][0][i]) > 1 else 0) for i in range(0, self._lastFrame-self._firstFrame+1)] for animalNumber in range(0, self._hyperparameters["nbAnimalsPerWell"])] for wellNumber in range(0, len(self._wellPositions))]
        
        self._auDessusPerAnimalIdList = [[np.ones((self._lastFrame-self._firstFrame+1, 1)) for nbAnimalsPerWell in range(0, self._hyperparameters["nbAnimalsPerWell"])] for wellNumber in range(len(self._wellPositions))]
        
        return {wellNumber: extractParameters([self._trackingDataPerWell[wellNumber], trackingHeadingAllAnimalsList[wellNumber], [], 0, 0, self._auDessusPerAnimalIdList[wellNumber]], wellNumber, self._hyperparameters, self._videoPath, self._wellPositions, self._background) for wellNumber in range(0, len(self._wellPositions))}
        
      else:
        
        outputData = detectMovementWithTrackedDataAfterTracking(self)
      
      return outputData


zebrazoom.code.tracking.register_tracking_method('fastFishTracking.tracking', Tracking)
