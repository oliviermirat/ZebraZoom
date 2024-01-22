from zebrazoom.code.tracking.customTrackingImplementations.fastFishTracking.tailTrackTry4InitialPerpendicularDirections import tailTrackTry4InitialPerpendicularDirections
from zebrazoom.code.tracking.customTrackingImplementations.fastFishTracking.dualDirectionTailDetection import dualDirectionTailDetection
from zebrazoom.code.tracking.customTrackingImplementations.fastFishTracking.tailTrackFindNextPoint import tailTrackFindNextPoint
from zebrazoom.code.tracking.customTrackingImplementations.fastFishTracking.utilities import calculateAngle
from zebrazoom.code.extractParameters import calculateTailAngle
from scipy.interpolate import interp1d
from numpy import linspace
import numpy as np
import math

def trackTail(self, frameROI, headPosition, hyperparameters, wellNumber, frameNumber, lastFirstTheta):
  
  steps   = hyperparameters["steps"]
  nbList  = 10 if hyperparameters["nbList"] == -1 else hyperparameters["nbList"]
  maxDepth = hyperparameters["maxDepth"]

  angle = 0

  points = np.zeros((2, 0))
  
  debug = hyperparameters["debugHeadEmbededFindNextPoints"]
  if debug:
    print("Frame number:", frameNumber + self._firstFrame)
  
  lenX = len(frameROI[0]) - 1
  lenY = len(frameROI) - 1
  
  if "tries4rotationsCombination" in hyperparameters and hyperparameters["tries4rotationsCombination"]:
    (points, lastFirstTheta, medianPixTotList) = tailTrackTry4InitialPerpendicularDirections(headPosition, frameROI, points, lastFirstTheta, maxDepth, steps, nbList, hyperparameters, debug, lenX, lenY)
  elif "dualDirectionTailDetection" in hyperparameters and hyperparameters["dualDirectionTailDetection"]:
    points = np.insert(points, 0, headPosition, 1)
    (points, lastFirstTheta, medianPixTotList) = dualDirectionTailDetection(headPosition, frameROI, points, lastFirstTheta, maxDepth, steps, nbList, hyperparameters, debug, lenX, lenY)
    if len(points) == 0: # or medianPixTotList > hyperparameters["maximumMedianValueOfAllPointsAlongTheTail"]:
      return [], lastFirstTheta
  else:
    (points, lastFirstTheta, medianPixTotList) = tailTrackFindNextPoint(0, headPosition, frameROI, points, lastFirstTheta, maxDepth, steps, nbList,  hyperparameters, debug, lenX, lenY)
  
  points = np.insert(points, 0, headPosition, axis=1)
  
  if False:
    points = np.transpose(points)
    num_samples = hyperparameters["nbTailPoints"]
    x = points[:, 0]
    y = points[:, 1]
    path_length = np.sum(np.sqrt(np.diff(x)**2 + np.diff(y)**2))
    desired_distance = path_length / (num_samples - 1)
    cumulative_distances = np.cumsum(np.sqrt(np.diff(x)**2 + np.diff(y)**2))
    cumulative_distances = np.insert(cumulative_distances, 0, 0)
    interp_func = interp1d(cumulative_distances, points, axis=0)
    new_distances = np.linspace(0, path_length, num=num_samples)
    resampled_points = interp_func(new_distances)
    points = np.transpose(resampled_points)
  
  output = np.zeros((1, hyperparameters["nbTailPoints"], 2))
  for idx, x in enumerate(points[0]):
    if idx < hyperparameters["nbTailPoints"]:
      output[0][idx][0] = x
      output[0][idx][1] = points[1][idx]
  
  if len(points[0]) < hyperparameters["nbTailPoints"]:
    for idx in range(len(points[0]), hyperparameters["nbTailPoints"]):
      output[0][idx][0] = output[0][len(points[0])-1][0]
      output[0][idx][1] = output[0][len(points[0])-1][1]
  else:
    if len(points[0]) > hyperparameters["nbTailPoints"]:
      output[0][hyperparameters["nbTailPoints"]-1][0] = points[0][len(points[0])-1]
      output[0][hyperparameters["nbTailPoints"]-1][1] = points[1][len(points[0])-1]
  
  return output, lastFirstTheta
