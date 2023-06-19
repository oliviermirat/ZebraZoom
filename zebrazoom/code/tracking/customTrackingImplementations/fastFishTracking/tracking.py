from zebrazoom.code.tracking.customTrackingImplementations.fastFishTracking.utilities import calculateAngle, distBetweenThetas
from zebrazoom.code.tracking.customTrackingImplementations.fastFishTracking.trackTail import trackTail
import zebrazoom.code.util as util
import zebrazoom.code.tracking
import numpy as np
import math
import cv2
import time

class Tracking(zebrazoom.code.tracking.BaseTrackingMethod):
  
  def __init__(self, videoPath, wellPositions, hyperparameters):
    self._videoPath = videoPath
    self._wellPositions = wellPositions
    self._hyperparameters = hyperparameters

  def run(self):
    
    ### Step 1 (out of 2): Tracking:
    
    # Getting video reader
    cap = cv2.VideoCapture(self._videoPath)
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
    trackingDataPerWell = {}
    for wellNumber in range(0, len(self._wellPositions)):
      trackingDataPerWell[wellNumber] = []
    
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
          
          # Retrieving well/tank/arena coordinates and selecting ROI
          wellXtop = self._wellPositions[wellNumber]['topLeftX']
          wellYtop = self._wellPositions[wellNumber]['topLeftY']
          lenghtWell_X = self._wellPositions[wellNumber]['lengthX']
          lenghtWell_Y = self._wellPositions[wellNumber]['lengthY']
          frameROI = frame[wellYtop:wellYtop+lenghtWell_Y, wellXtop:wellXtop+lenghtWell_X].copy()

          (minVal, maxVal, headPosition, maxLoc) = cv2.minMaxLoc(frameROI)
          if minVal >= 240:
            headPosition = [0, 0]
          
          if self._hyperparameters["trackTail"]:
            a = trackTail(frameROI, headPosition, self._hyperparameters)
            trackingDataPerWell[wellNumber].append(a[0])
          else:
            trackingDataPerWell[wellNumber].append(headPosition)
        
        t2 = time.time()
        if printInterTime:
          print("Tracking on each well:", t2 - t1)
      
      time3 = time.time()   
      times[k, 0] = time2 - time1
      times[k, 1] = time3 - time2
      k += 1
    
    endTime = time.time()
    
    print("")
    loadingImagesTime       = np.median(times[:,0])
    processingImagesTime    = np.median(times[:,1])
    percentTimeSpentLoading = loadingImagesTime / (loadingImagesTime + processingImagesTime)
    print("Median time spent on: Loading images:", loadingImagesTime, "; Processing images:", processingImagesTime)
    print("Percentage of time spent loading images:", percentTimeSpentLoading*100)
    print("Total tracking Time:", endTime - startTime)
    print("Tracking Time (without loading image):", (endTime - startTime) * (1 - percentTimeSpentLoading))
    print("Total tracking fps:", int(cap.get(cv2.CAP_PROP_FRAME_COUNT) + 1) / (endTime - startTime))
    print("Tracking fps (without loading image):", int(cap.get(cv2.CAP_PROP_FRAME_COUNT) + 1) / ((endTime - startTime) * (1 - percentTimeSpentLoading)))
    print("")
    
    ### Step 2 (out of 2): Extracting bout of movements:
    
    outputData = {} # Each element of this object will correspond to the tracking data of a particular well/tank/arena
    
    for wellNumber in range(0, len(self._wellPositions)):
      
      outputDataForWell = []
        
      if self._hyperparameters["detectBouts"]: # See below ("else") for no bout detection scenario
        
        nbFramesStepToAvoidNoise = self._hyperparameters["nbFramesStepToAvoidNoise"]
        minNbFramesForBoutDetect = self._hyperparameters["minNbFramesForBoutDetect"]
        
        # Finding frames with an instantaneous distance over a predifined threshold
        boutOccuring = [math.sqrt((trackingDataPerWell[wellNumber][i+nbFramesStepToAvoidNoise][0][0] - trackingDataPerWell[wellNumber][i][0][0])**2 + (trackingDataPerWell[wellNumber][i+nbFramesStepToAvoidNoise][0][1] - trackingDataPerWell[wellNumber][i][0][1])**2) > self._hyperparameters["minimumInstantaneousDistanceForBoutDetect"] for i in range(0, len(trackingDataPerWell[wellNumber])-nbFramesStepToAvoidNoise)]
        
        # Detecting bouts by finding long enough sequence of frames with high enough instantaneous distance
        boutCurrentlyOccuring = False
        boutFrameNumberStart  = -1
        for frameNumber, boutIsOccuring in enumerate(boutOccuring):
          if boutIsOccuring:
            if not(boutCurrentlyOccuring):
              boutFrameNumberStart = frameNumber
            boutCurrentlyOccuring = True
          else:
            if boutCurrentlyOccuring:
              boutCurrentlyOccuring = False
              if frameNumber - boutFrameNumberStart > minNbFramesForBoutDetect:
                # Saving information for each bout of movement detected
                boutOfMovement = {}
                boutOfMovement["AnimalNumber"]  = 0
                boutOfMovement["BoutStart"]     = boutFrameNumberStart
                boutOfMovement["BoutEnd"]       = frameNumber
                boutOfMovement["HeadX"]         = [trackingDataPerWell[wellNumber][i][0][0] for i in range(boutFrameNumberStart, frameNumber)]
                boutOfMovement["HeadY"]         = [trackingDataPerWell[wellNumber][i][0][1] for i in range(boutFrameNumberStart, frameNumber)]
                boutOfMovement["Heading"]                = [(calculateAngle(trackingDataPerWell[wellNumber][i][0][0], trackingDataPerWell[wellNumber][i][0][1], trackingDataPerWell[wellNumber][i][1][0], trackingDataPerWell[wellNumber][i][1][1]) + math.pi) % (2 * math.pi) for i in range(boutFrameNumberStart, frameNumber+1)]
                boutOfMovement["TailAngle_Raw"]          = [distBetweenThetas(calculateAngle(trackingDataPerWell[wellNumber][i][0][0], trackingDataPerWell[wellNumber][i][0][1], trackingDataPerWell[wellNumber][i][1][0], trackingDataPerWell[wellNumber][i][1][1]), calculateAngle(trackingDataPerWell[wellNumber][i][0][0], trackingDataPerWell[wellNumber][i][0][1], trackingDataPerWell[wellNumber][i][len(trackingDataPerWell[wellNumber][i])-1][0], trackingDataPerWell[wellNumber][i][len(trackingDataPerWell[wellNumber][i])-1][1])) for i in range(boutFrameNumberStart, frameNumber+1)]
                boutOfMovement["TailX_VideoReferential"] = [[trackingDataPerWell[wellNumber][i][j][0] for j in range(0, len(trackingDataPerWell[wellNumber][i]))] for i in range(boutFrameNumberStart, frameNumber+1)]
                boutOfMovement["TailY_VideoReferential"] = [[trackingDataPerWell[wellNumber][i][j][1] for j in range(0, len(trackingDataPerWell[wellNumber][i]))] for i in range(boutFrameNumberStart, frameNumber+1)]
                
                outputDataForWell.append(boutOfMovement)
      
      else: # No bout detction in this case
      
        lastFrame = len(trackingDataPerWell[wellNumber])
        boutOfMovement = {}
        boutOfMovement["AnimalNumber"]  = 0
        boutOfMovement["BoutStart"]     = 0
        boutOfMovement["BoutEnd"]       = len(trackingDataPerWell[wellNumber])
        boutOfMovement["HeadX"]         = [trackingDataPerWell[wellNumber][i][0][0] for i in range(0, lastFrame)]
        boutOfMovement["HeadY"]         = [trackingDataPerWell[wellNumber][i][0][1] for i in range(0, lastFrame)]
        boutOfMovement["Heading"]       = [(calculateAngle(trackingDataPerWell[wellNumber][i][0][0], trackingDataPerWell[wellNumber][i][0][1], trackingDataPerWell[wellNumber][i][1][0], trackingDataPerWell[wellNumber][i][1][1]) + math.pi) % (2 * math.pi) for i in range(0, lastFrame)]
        boutOfMovement["TailAngle_Raw"]          = [distBetweenThetas(calculateAngle(trackingDataPerWell[wellNumber][i][0][0], trackingDataPerWell[wellNumber][i][0][1], trackingDataPerWell[wellNumber][i][1][0], trackingDataPerWell[wellNumber][i][1][1]), calculateAngle(trackingDataPerWell[wellNumber][i][0][0], trackingDataPerWell[wellNumber][i][0][1], trackingDataPerWell[wellNumber][i][len(trackingDataPerWell[wellNumber][i])-1][0], trackingDataPerWell[wellNumber][i][len(trackingDataPerWell[wellNumber][i])-1][1])) for i in range(0, lastFrame)]
        boutOfMovement["TailX_VideoReferential"] = [[trackingDataPerWell[wellNumber][i][j][0] for j in range(0, len(trackingDataPerWell[wellNumber][i]))] for i in range(0, lastFrame)]
        boutOfMovement["TailY_VideoReferential"] = [[trackingDataPerWell[wellNumber][i][j][1] for j in range(0, len(trackingDataPerWell[wellNumber][i]))] for i in range(0, lastFrame)]
        outputDataForWell.append(boutOfMovement)        
      
      # Saving all tracked bouts of movements for current frame
      outputData[wellNumber] = outputDataForWell
    
    return outputData


zebrazoom.code.tracking.register_tracking_method('fastFishTracking.tracking', Tracking)
