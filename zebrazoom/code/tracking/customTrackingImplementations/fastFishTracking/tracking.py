from zebrazoom.code.tracking.customTrackingImplementations.fastFishTracking.utilities import calculateAngle, distBetweenThetas
from zebrazoom.code.tracking.customTrackingImplementations.fastFishTracking.detectMovementWithTrackedDataAfterTracking import detectMovementWithTrackedDataAfterTracking
from zebrazoom.code.tracking.customTrackingImplementations.fastFishTracking.detectMovementWithRawVideoInsideTracking import detectMovementWithRawVideoInsideTracking
from zebrazoom.code.tracking.customTrackingImplementations.fastFishTracking.trackTail import trackTail
import zebrazoom.videoFormatConversion.zzVideoReading as zzVideoReading
from zebrazoom.code.extractParameters import extractParameters
import zebrazoom.code.util as util
import zebrazoom.code.tracking
import numpy as np
import queue
import math
import time
import cv2

class Tracking(zebrazoom.code.tracking.BaseTrackingMethod):
  
  def __init__(self, videoPath, wellPositions, hyperparameters):
    self._videoPath = videoPath
    self._wellPositions = wellPositions
    self._hyperparameters = hyperparameters
    self._auDessusPerAnimalIdList = None
    self._firstFrame = self._hyperparameters["firstFrame"]
    self._lastFrame = self._hyperparameters["lastFrame"]
    self._nbTailPoints = self._hyperparameters["nbTailPoints"]
    self._previousFrames = None


  def run(self):
    
    ### Step 1 (out of 2): Tracking:
    
    # Getting video reader
    cap = zzVideoReading.VideoCapture(self._videoPath)
    if (cap.isOpened()== False):
      print("Error opening video stream or file")
    
    # Simple background extraction with first and last frame of the video
    ret, self._background = cap.read()
    cap.set(cv2.CAP_PROP_POS_FRAMES, int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) - 1)
    ret, frame = cap.read()
    self._background = cv2.max(frame, self._background)
    self._background = cv2.cvtColor(self._background, cv2.COLOR_BGR2GRAY)
    cap.set(cv2.CAP_PROP_POS_FRAMES, 0)
    
    times = np.zeros((int(cap.get(cv2.CAP_PROP_FRAME_COUNT) + 1), 2))
    
    # Initializing variables
    ret = True
    trackingDataPerWell = [np.zeros((self._hyperparameters["nbAnimalsPerWell"], self._lastFrame-self._firstFrame+1, self._nbTailPoints, 2)) for _ in range(len(self._wellPositions))]
    
    lastFirstTheta = np.zeros(len(self._wellPositions))
    lastFirstTheta[:] = -99999
    
    printInterTime = False
    
    startTime = time.time()
    # Going through each frame of the video
    k = 0
    while (ret):
      time1 = time.time()
      ret, frame = cap.read()
      time2 = time.time()
      if ret:
      
        # Color to grey scale transformation
        t1 = time.time()
        frame = frame[:,:,0]
        t2 = time.time()
        if printInterTime:
          print("Color to grey", t2 - t1)
        
        # Subtracting background of image
        t1 = time.time()
        frame = 255 - np.where(self._background >= frame, self._background - frame, 0).astype(np.uint8)
        t2 = time.time()
        if printInterTime:
          print("Background substraction", t2 - t1)
        
        t1 = time.time()
        paramGaussianBlur = self._hyperparameters["paramGaussianBlur"]
        frame = cv2.GaussianBlur(frame, (paramGaussianBlur, paramGaussianBlur), 0)
        t2 = time.time()
        if printInterTime:
          print("Gaussian blur:", t2 - t1)
        
        t1 = time.time()
        # Going through each well/arena/tank and applying tracking method on it
        for wellNumber in range(0, len(self._wellPositions)):
          
          animalId = 0
          
          # Retrieving well/tank/arena coordinates and selecting ROI
          wellXtop = self._wellPositions[wellNumber]['topLeftX']
          wellYtop = self._wellPositions[wellNumber]['topLeftY']
          lenghtWell_X = self._wellPositions[wellNumber]['lengthX']
          lenghtWell_Y = self._wellPositions[wellNumber]['lengthY']
          frameROI = frame[wellYtop:wellYtop+lenghtWell_Y, wellXtop:wellXtop+lenghtWell_X]

          (minVal, maxVal, headPosition, maxLoc) = cv2.minMaxLoc(frameROI)
          if minVal >= 240:
            headPosition = [0, 0]
          
          if self._hyperparameters["trackTail"]:
            a, lastFirstTheta[wellNumber] = trackTail(frameROI, headPosition, self._hyperparameters, wellNumber, k, lastFirstTheta[wellNumber])
            trackingDataPerWell[wellNumber][animalId][k][:len(a[0])] = a
          else:
            trackingDataPerWell[wellNumber][animalId][k] = np.array([[headPosition]])
        
        self._previousFrames = detectMovementWithRawVideoInsideTracking(self, k, frame, self._previousFrames, trackingDataPerWell)
        
        t2 = time.time()
        if printInterTime:
          print("Tracking on each well:", t2 - t1)
      
      time3 = time.time()   
      times[k, 0] = time2 - time1
      times[k, 1] = time3 - time2
      k += 1
    
    endTime = time.time()
    
    cap.release()
    
    print("")
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
    
      trackingHeadingAllAnimalsList = [[[((calculateAngle(trackingDataPerWell[wellNumber][0][i][0][0], trackingDataPerWell[wellNumber][0][i][0][1], trackingDataPerWell[wellNumber][0][i][1][0], trackingDataPerWell[wellNumber][0][i][1][1]) + math.pi) % (2 * math.pi) if len(trackingDataPerWell[wellNumber][0][i]) > 1 else 0) for i in range(0, self._lastFrame)]] for wellNumber in range(0, len(self._wellPositions))]
      
      return {wellNumber: extractParameters([trackingDataPerWell[wellNumber], trackingHeadingAllAnimalsList[wellNumber], [], 0, 0, self._auDessusPerAnimalIdList[wellNumber]], wellNumber, self._hyperparameters, self._videoPath, self._wellPositions, self._background) for wellNumber in range(0, len(self._wellPositions))}
    
    else:
      
      outputData = detectMovementWithTrackedDataAfterTracking(self, trackingDataPerWell)
      
      return outputData


zebrazoom.code.tracking.register_tracking_method('fastFishTracking.tracking', Tracking)
