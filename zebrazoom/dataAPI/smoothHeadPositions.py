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

def rolling_mean(data, window_size):
    # Ensure window size is odd for symmetric padding
    if window_size % 2 == 0:
        raise ValueError("Window size must be odd for symmetric padding.")
    
    half_window = window_size // 2
    
    # Apply rolling mean separately on each column
    cumsum = np.cumsum(np.insert(data, 0, 0, axis=0), axis=0)
    smoothed_data = (cumsum[window_size:] - cumsum[:-window_size]) / window_size
    
    # Pad the result to match the input size
    start_pad = np.tile(smoothed_data[0], (half_window, 1))
    end_pad = np.tile(smoothed_data[-1], (half_window, 1))
    smoothed_data = np.vstack((start_pad, smoothed_data, end_pad))
    
    return smoothed_data
def smoothHeadPositions(videoName: str, nbWells: int, nbAnimalsPerWell: int, smoothHeadPositionsWindow: int):

  for numWell in range(nbWells):
    dataForEachAnimal = []
    for numAnimal in range(nbAnimalsPerWell):
      data = dataAPI.getDataPerTimeInterval(videoName, numWell, numAnimal, None, None, "HeadPos")
      smoothed_data = rolling_mean(data, smoothHeadPositionsWindow)
      dataAPI.setDataPerTimeInterval(videoName, numWell, numAnimal, None, None, "HeadPos", smoothed_data)
