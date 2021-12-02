import cv2
import math
import os

from zebrazoom.code.trackingFolder.tailTrackingFunctionsFolder.headEmbededTailTracking import headEmbededTailTracking
from zebrazoom.code.trackingFolder.tailTrackingFunctionsFolder.centerOfMassTailTracking import centerOfMassTailTracking
from zebrazoom.code.trackingFolder.tailTrackingFunctionsFolder.tailTrackingExtremityDetectFolder.tailTrackingExtremityDetect import tailTrackingExtremityDetect
from zebrazoom.code.trackingFolder.tailTrackingFunctionsFolder.tailTrackingBlobDescent import tailTrackingBlobDescent
from zebrazoom.code.trackingFolder.tailTrackingFunctionsFolder.getTailTipManual import findHeadPositionByUserInput
from zebrazoom.code.trackingFolder.tailTrackingFunctionsFolder.headEmbededTailTrackingTeresaNicolson import headEmbededTailTrackingTeresaNicolson

def tailTracking(animalId, i, firstFrame, videoPath, frame, hyperparameters, thresh1, nbTailPoints, threshForBlackFrames, thetaDiffAccept, trackingHeadTailAllAnimals, trackingHeadingAllAnimals, lastFirstTheta, maxDepth, tailTip, initialCurFrame, back, wellNumber=-1, xmin=0, ymin=0):

  headPosition = [trackingHeadTailAllAnimals[animalId, i-firstFrame][0][0]-xmin, trackingHeadTailAllAnimals[animalId, i-firstFrame][0][1]-ymin]
  heading      = trackingHeadingAllAnimals[animalId, i-firstFrame]
  
  if (hyperparameters["headEmbeded"] == 1):
    # through the "head embeded" method, either through "segment descent" or "center of mass descent"
    
    if hyperparameters["headEmbededTeresaNicolson"] == 1:
      oppHeading = (heading + math.pi) % (2 * math.pi)
      trackingHeadTailAllAnimalsI = headEmbededTailTrackingTeresaNicolson(headPosition,nbTailPoints,i,thresh1,frame,hyperparameters,oppHeading,maxDepth,tailTip,threshForBlackFrames)
    else:
      oppHeading = (heading + math.pi) % (2 * math.pi) # INSERTED FOR THE REFACTORING
      if hyperparameters["centerOfMassTailTracking"] == 0:
        trackingHeadTailAllAnimalsI = headEmbededTailTracking(headPosition,nbTailPoints,i,thresh1,frame,hyperparameters,oppHeading,maxDepth,tailTip)
      else:
        trackingHeadTailAllAnimalsI = centerOfMassTailTracking(headPosition,nbTailPoints,i,thresh1,frame,hyperparameters,oppHeading,maxDepth)
    
    if len(trackingHeadTailAllAnimalsI[0]) == len(trackingHeadTailAllAnimals[animalId, i-firstFrame]):
      trackingHeadTailAllAnimals[animalId, i-firstFrame] = trackingHeadTailAllAnimalsI
    
  else:
    if hyperparameters["freeSwimmingTailTrackingMethod"] == "tailExtremityDetect":
      # through the tail extremity descent method (original C++ method)
      [trackingHeadTailAllAnimalsI, newHeading] = tailTrackingExtremityDetect(headPosition,nbTailPoints,i,thresh1,frame,hyperparameters["debugTrackingPtExtreme"],heading,hyperparameters, initialCurFrame, back, wellNumber)
      trackingHeadTailAllAnimals[animalId, i-firstFrame] = trackingHeadTailAllAnimalsI
      if newHeading != -1:
        trackingHeadingAllAnimals[animalId, i-firstFrame] = newHeading
    elif hyperparameters["freeSwimmingTailTrackingMethod"] == "blobDescent":
      # through the "blob descent" method
      trackingHeadTailAllAnimalsI = tailTrackingBlobDescent(headPosition, nbTailPoints, i, headPosition[0], headPosition[1], thresh1, frame, lastFirstTheta, hyperparameters["debugTrackingPtExtreme"], thetaDiffAccept, hyperparameters)
      trackingHeadTailAllAnimals[animalId, i-firstFrame] = trackingHeadTailAllAnimalsI
    else: # hyperparameters["freeSwimmingTailTrackingMethod"] == "none"
      # only tracking the head, not the tail
      trackingHeadTailAllAnimals[animalId, i-firstFrame][0][0] = headPosition[0]
      trackingHeadTailAllAnimals[animalId, i-firstFrame][0][1] = headPosition[1]
      
  return [trackingHeadTailAllAnimals, trackingHeadingAllAnimals]
