from zebrazoom.code.tracking.customTrackingImplementations.fastFishTracking.utilities import calculateAngle, distBetweenThetas
import numpy as np
import queue
import math
import cv2

def detectMovementWithTrackedDataAfterTracking(self):

  trackingDataPerWell = self._trackingDataPerWell
  
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
      boutOfMovement["BoutEnd"]       = len(trackingDataPerWell[wellNumber][0])
      boutOfMovement["HeadX"]         = [trackingDataPerWell[wellNumber][0][i][0][0] for i in range(0, lastFrame)]
      boutOfMovement["HeadY"]         = [trackingDataPerWell[wellNumber][0][i][0][1] for i in range(0, lastFrame)]
      boutOfMovement["Heading"]       = [(calculateAngle(trackingDataPerWell[wellNumber][0][i][0][0], trackingDataPerWell[wellNumber][0][i][0][1], trackingDataPerWell[wellNumber][0][i][1][0], trackingDataPerWell[wellNumber][0][i][1][1]) + math.pi) % (2 * math.pi) for i in range(0, lastFrame)]
      boutOfMovement["TailAngle_Raw"]          = [distBetweenThetas(calculateAngle(trackingDataPerWell[wellNumber][0][i][0][0], trackingDataPerWell[wellNumber][0][i][0][1], trackingDataPerWell[wellNumber][0][i][1][0], trackingDataPerWell[wellNumber][0][i][1][1]), calculateAngle(trackingDataPerWell[wellNumber][0][i][0][0], trackingDataPerWell[wellNumber][0][i][0][1], trackingDataPerWell[wellNumber][0][i][len(trackingDataPerWell[wellNumber][0][i])-1][0], trackingDataPerWell[wellNumber][0][i][len(trackingDataPerWell[wellNumber][0][i])-1][1])) for i in range(0, lastFrame)]
      boutOfMovement["TailX_VideoReferential"] = [[trackingDataPerWell[wellNumber][0][i][j][0] for j in range(0, len(trackingDataPerWell[wellNumber][0][i]))] for i in range(0, lastFrame)]
      boutOfMovement["TailY_VideoReferential"] = [[trackingDataPerWell[wellNumber][0][i][j][1] for j in range(0, len(trackingDataPerWell[wellNumber][0][i]))] for i in range(0, lastFrame)]
      outputDataForWell.append(boutOfMovement)
    
    # Saving all tracked bouts of movements for current frame
    outputData[wellNumber] = outputDataForWell
  
  return outputData