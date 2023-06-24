from zebrazoom.code.tracking.customTrackingImplementations.fastFishTracking.utilities import calculateAngle, distBetweenThetas
from zebrazoom.code.tracking.customTrackingImplementations.fastFishTracking.detectMovementWithTrackedDataAfterTracking import detectMovementWithTrackedDataAfterTracking
from zebrazoom.code.tracking.customTrackingImplementations.fastFishTracking.detectMovementWithRawVideoInsideTracking import detectMovementWithRawVideoInsideTracking
from zebrazoom.code.tracking.customTrackingImplementations.fastFishTracking.getListOfWellsOnWhichToRunTheTracking import getListOfWellsOnWhichToRunTheTracking
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
    
    # Simple background extraction with first and last frame of the video + Getting list of wells on which to run the tracking
    if self._firstFrame != 1:
      cap.set(cv2.CAP_PROP_POS_FRAMES, self._firstFrame - 1)
    ret, self._background = cap.read()
    cap.set(cv2.CAP_PROP_POS_FRAMES, int(cap.get(cv2.CAP_PROP_FRAME_COUNT)) - 1)
    ret, frame = cap.read()
    if self._hyperparameters["chooseWellsToRunTrackingOnWithFirstAndLastFrame"]:
      listOfWellsOnWhichToRunTheTracking = getListOfWellsOnWhichToRunTheTracking(self, self._background[:,:,0], frame[:,:,0])
    else:
      listOfWellsOnWhichToRunTheTracking = [i for i in range(0, len(self._wellPositions))]
    print("listOfWellsOnWhichToRunTheTracking:", listOfWellsOnWhichToRunTheTracking)
    self._background = cv2.max(frame, self._background)
    self._background = cv2.cvtColor(self._background, cv2.COLOR_BGR2GRAY)
    cap.set(cv2.CAP_PROP_POS_FRAMES, self._firstFrame - 1)
    
    # Initializing variables
    trackingDataPerWell = [np.zeros((self._hyperparameters["nbAnimalsPerWell"], self._lastFrame-self._firstFrame+1, self._nbTailPoints, 2)) for _ in range(len(self._wellPositions))]
    lastFirstTheta = np.zeros(len(self._wellPositions))
    lastFirstTheta[:] = -99999
    times  = np.zeros((int(cap.get(cv2.CAP_PROP_FRAME_COUNT) + 1), 2))
    times2 = np.zeros((int(cap.get(cv2.CAP_PROP_FRAME_COUNT) + 1), 5))
    ret = True
    printInterTime = False
    
    # Going through each frame of the video
    startTime = time.time()
    k = self._firstFrame - 1
    while (ret and k <= self._lastFrame):
      time1 = time.time()
      ret, frame = cap.read()
      time2 = time.time()
      if ret:
      
        # Color to grey scale transformation
        t1 = time.time()
        frame = frame[:,:,0]
        t2 = time.time()
        times2[k, 0] = t2 - t1
        if printInterTime:
          print("Color to grey", t2 - t1)
        
        # Bout detection
        if self._hyperparameters["detectMovementWithRawVideoInsideTracking"]:
          t1 = time.time()
          self._previousFrames = detectMovementWithRawVideoInsideTracking(self, k, frame, self._previousFrames, trackingDataPerWell, listOfWellsOnWhichToRunTheTracking)
          t2 = time.time()
          times2[k, 1] = t2 - t1
          if printInterTime:
            print("Bout detection", t2 - t1)
        
        # Subtracting background of image
        t1 = time.time()
        frame = 255 - np.where(self._background >= frame, self._background - frame, 0).astype(np.uint8)
        t2 = time.time()
        times2[k, 2] = t2 - t1
        if printInterTime:
          print("Background substraction", t2 - t1)
        
        # Applying gaussian filter
        t1 = time.time()
        paramGaussianBlur = self._hyperparameters["paramGaussianBlur"]
        frame = cv2.GaussianBlur(frame, (paramGaussianBlur, paramGaussianBlur), 0)
        t2 = time.time()
        times2[k, 3] = t2 - t1
        if printInterTime:
          print("Gaussian blur:", t2 - t1)
        
        # Going through each well/arena/tank and applying tracking method on it
        t1 = time.time()
        for wellNumber in listOfWellsOnWhichToRunTheTracking:
          
          animalId = 0
          
          if self._hyperparameters["detectMovementWithRawVideoInsideTracking"] == 0 or self._auDessusPerAnimalIdList[wellNumber][animalId][k] or k <= 2:
            # Retrieving well/tank/arena coordinates and selecting ROI
            wellXtop = self._wellPositions[wellNumber]['topLeftX']
            wellYtop = self._wellPositions[wellNumber]['topLeftY']
            lenghtWell_X = self._wellPositions[wellNumber]['lengthX']
            lenghtWell_Y = self._wellPositions[wellNumber]['lengthY']
            frameROI = frame[wellYtop:wellYtop+lenghtWell_Y, wellXtop:wellXtop+lenghtWell_X]
            # Head position tracking
            (minVal, maxVal, headPosition, maxLoc) = cv2.minMaxLoc(frameROI)
            if minVal >= self._hyperparameters["minimumHeadPixelValue"]:
              trackingDataPerWell[wellNumber][animalId][k] = trackingDataPerWell[wellNumber][animalId][k-1]
            else:
              if self._hyperparameters["trackTail"]:
                # Tail tracking
                a, lastFirstTheta[wellNumber] = trackTail(frameROI, headPosition, self._hyperparameters, wellNumber, k, lastFirstTheta[wellNumber])
                trackingDataPerWell[wellNumber][animalId][k][:len(a[0])] = a
              else:
                trackingDataPerWell[wellNumber][animalId][k] = np.array([[headPosition]])
          else:
            if k > 0:
              trackingDataPerWell[wellNumber][animalId][k] = trackingDataPerWell[wellNumber][animalId][k-1]
        
        t2 = time.time()
        times2[k, 4] = t2 - t1
        if printInterTime:
          print("Tracking on each well:", t2 - t1)
      
      time3 = time.time()   
      times[k, 0] = time2 - time1
      times[k, 1] = time3 - time2
      k += 1
    
    endTime = time.time()
    
    cap.release()
    
    print("")
    print("Color to grey:"           , np.median(times2[:,0]))
    print("Bout detection:"          , np.median(times2[:,1]))
    print("Background substraction:" , np.median(times2[:,2]))
    print("Gaussian blur:"           , np.median(times2[:,3]))
    print("Tracking on each well:"   , np.median(times2[:,4]))
    
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
