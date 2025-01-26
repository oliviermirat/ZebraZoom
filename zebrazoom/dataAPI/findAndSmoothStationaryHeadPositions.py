from scipy.optimize import linear_sum_assignment
import zebrazoom.dataAPI as dataAPI
import matplotlib.pyplot as plt
from scipy import stats
import pandas as pd
import numpy as np
import shutil
import math
import h5py
import os

def findAndSmooth(data, threshold=3, k=10):
  n = len(data)
  if k >= n:
    raise ValueError("k must be smaller than the length of the data.")
  
  # Calculate distances between points n and n+k
  distances = np.zeros(n - k)
  for i in range(n - k):
    distances[i] = np.linalg.norm(data[i + k] - data[i])
  
  # Identify stationary segments
  stationary_mask = distances <= threshold
  result = data.copy()
  
  i = 0
  while i < n - k:
    if stationary_mask[i]:
      # Start of a stationary segment
      start_idx = i
      while i < n - k and stationary_mask[i]:
        i += 1
      # Replace the segment with the coordinates at the start
      result[start_idx + 1:i + k] = data[start_idx]
    else:
      i += 1
  
  return result


def findAndSmoothStationaryHeadPositions(videoName: str, nbWells: int, nbAnimalsPerWell: int, findAndSmoothStationaryDist: int = 3, findAndSmoothStationaryIndexDiff: int = 10):

  for numWell in range(nbWells):
    dataForEachAnimal = []
    for numAnimal in range(nbAnimalsPerWell):
      data = dataAPI.getDataPerTimeInterval(videoName, numWell, numAnimal, None, None, "HeadPos")
      smoothed_data = findAndSmooth(data, findAndSmoothStationaryDist, findAndSmoothStationaryIndexDiff)
      dataAPI.setDataPerTimeInterval(videoName, numWell, numAnimal, None, None, "HeadPos", smoothed_data)
