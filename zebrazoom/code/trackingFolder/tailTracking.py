import cv2
import math
import os

from headEmbededTailTracking import headEmbededTailTracking
from centerOfMassTailTracking import centerOfMassTailTracking
from tailTrackingExtremityDetect import tailTrackingExtremityDetect
from tailTrackingBlobDescent import tailTrackingBlobDescent
from getTailTipManual import findHeadPositionByUserInput
from headEmbededTailTrackingTeresaNicolson import headEmbededTailTrackingTeresaNicolson

def tailTracking(animalId, i, firstFrame, heading, videoPath, x, y, headPosition, frame, hyperparameters, thresh1, nbTailPoints, threshForBlackFrames, thetaDiffAccept, output, lastFirstTheta, maxDepth, tailTip):
  
  if (hyperparameters["headEmbeded"] == 1):
    # through the "head embeded" method, either through "segment descent" or "center of mass descent"
    
    if hyperparameters["headEmbededTeresaNicolson"] == 1:
      oppHeading = (heading + math.pi) % (2 * math.pi)
      outputI = headEmbededTailTrackingTeresaNicolson(headPosition,nbTailPoints,i,thresh1,frame,hyperparameters,oppHeading,maxDepth,tailTip,threshForBlackFrames)
    else:
      oppHeading = (heading + math.pi) % (2 * math.pi) # INSERTED FOR THE REFACTORING
      if hyperparameters["centerOfMassTailTracking"] == 0:
        outputI = headEmbededTailTracking(headPosition,nbTailPoints,i,thresh1,frame,hyperparameters,oppHeading,maxDepth,tailTip)
      else:
        outputI = centerOfMassTailTracking(headPosition,nbTailPoints,i,thresh1,frame,hyperparameters,oppHeading,maxDepth)
    
    if len(outputI[0]) == len(output[animalId, i-firstFrame]):
      output[animalId, i-firstFrame] = outputI

  else:
    if hyperparameters["freeSwimmingTailTrackingMethod"] == "tailExtremityDetect":
      # through the tail extremity descent method (original C++ method)
      outputI = tailTrackingExtremityDetect(headPosition,nbTailPoints,i,thresh1,frame,hyperparameters["debugTrackingPtExtreme"],heading,hyperparameters)
      output[animalId, i-firstFrame] = outputI
    elif hyperparameters["freeSwimmingTailTrackingMethod"] == "blobDescent":
      # through the "blob descent" method
      outputI = tailTrackingBlobDescent(headPosition,nbTailPoints,i,x,y,thresh1,frame,lastFirstTheta,hyperparameters["debugTrackingPtExtreme"],thetaDiffAccept,hyperparameters)
      output[animalId, i-firstFrame] = outputI
    else: # hyperparameters["freeSwimmingTailTrackingMethod"] == "none"
      # only tracking the head, not the tail
      output[animalId, i-firstFrame][0][0] = headPosition[0]
      output[animalId, i-firstFrame][0][1] = headPosition[1]
      
  return [output, maxDepth, tailTip, headPosition]
