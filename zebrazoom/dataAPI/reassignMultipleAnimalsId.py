from scipy.optimize import linear_sum_assignment
import zebrazoom.dataAPI as dataAPI
import matplotlib.pyplot as plt
from scipy import stats
import pandas as pd
import numpy as np
import shutil
import math
import os


def identifyPointsToClose(curr_positions, threshold, dataForLine, numFrame):
  points = curr_positions[0]
  valid_points = points[~np.all(points == 0, axis=1)]
  distances = np.sqrt(np.sum((valid_points[:, np.newaxis, :] - valid_points[np.newaxis, :, :]) ** 2, axis=2))
  close_pairs = np.argwhere((distances < threshold) & (distances >= 0))
  close_pairs = [pair for pair in close_pairs if pair[0] < pair[1]]
  for _, second_idx in close_pairs:
    curr_positions[0, second_idx] = [0, 0]
    dataForLine[second_idx][numFrame] = [0, 0]


def reassignMultipleAnimalsId(videoName: str, nbWells: int, nbAnimalsPerWell: int, freqAlgoPosFollow: int, self):
  
  # NEED TO REMOVE THE FOLLOWING LINE AS SOON AS GETDATAPERTIMEINTERVAL AND SETDATAPERTIMEINTERVAL ARE FIXED
  dataAPI.setFPSandPixelSize(videoName, 24, 0.1)
  
  startTimeInSeconds = None
  endTimeInSeconds = None

  nbWells   = 1
  nbAnimals = 20
  videoFPS  = 24
  videoPixelSize = 0.01

  max_distance_threshold = 100
  max_NbFramesAllowedToDisapeared = 50
  minimumTraceLength = 5
  removeNewDetectionsTooClose = 8
  minDistTravel = 1

  printDebug = False

  for numWell in range(nbWells):
    
    numAnimal = 0
    
    dataForEachAnimal = []
    for numAnimal in range(nbAnimalsPerWell):
      data = dataAPI.getDataPerTimeInterval(videoName, numWell, numAnimal, startTimeInSeconds, endTimeInSeconds, "HeadPos")
      dataForEachAnimal.append(data)
    
    maximalDisappearanceFrames = [2 * max_NbFramesAllowedToDisapeared for i in range(nbAnimalsPerWell)]
    nbFramesNotAtZero = [0 for i in range(nbAnimalsPerWell)]
    curFirstCoordinates = [[0, 0] for i in range(nbAnimalsPerWell)]
    
    for numFrame in range(1, len(dataForEachAnimal[0])):
      
      if numFrame % freqAlgoPosFollow == 0:
        print("reassignMultipleIds: numFrame:", numFrame)
      
      prev_positions = np.empty((0, 1, 2))
      curr_positions = np.empty((0, 2))
      for numAnimal in range(nbAnimalsPerWell):
        prev_positions = np.append(prev_positions, np.array([np.array([dataForEachAnimal[numAnimal][numFrame-1]])]), axis = 0)
        curr_positions = np.append(curr_positions, np.array([dataForEachAnimal[numAnimal][numFrame]]), axis = 0)
      curr_positions = np.array([curr_positions])
      if removeNewDetectionsTooClose > 0:
        identifyPointsToClose(curr_positions, removeNewDetectionsTooClose, dataForEachAnimal, numFrame)
      
      distance_matrix = np.linalg.norm(prev_positions - curr_positions, axis=2)
      
      
      # Identifying next possible positions equal to (0, 0) or not
      non_zero_mask = np.linalg.norm(curr_positions, axis=2) != 0
      zero_mask = np.linalg.norm(curr_positions, axis=2) == 0
      
      # Adding disavantage for long distance position changes 
      # but only for next possible positions not at (0, 0) (because we want it to be possible for the trace to "end")
      # typically this will results in the first columns (possible next coordinates) being penalized for distances too long (first lines because traces currently at (0, 0), last lines because they could be simply too far)
      distance_matrix[(distance_matrix > max_distance_threshold) & non_zero_mask] += 1e6
      
      # Making all end of trace "return to (0, 0)" equal regardless of current position
      distance_matrix[(distance_matrix != 0) & zero_mask] = 1e4 #0.5 * distance_matrix[(distance_matrix != 0) & zero_mask]
      
      # Adding disavantage for traces at (0, 0) to stay at (0, 0) (to promote traces to "start")
      # typically this will result in the first lines (not yet assigned to a trace) being penalized for the last columns (which are (0, 0) next coordinates options) (starting from numcolumn = number of possible next coordinates options)
      distance_matrix[(distance_matrix == 0) & zero_mask] += 1e6
      
      row_ind, col_ind = linear_sum_assignment(distance_matrix)
      
      if printDebug:
        print("row_ind, col_ind:", row_ind, col_ind)
        print(numFrame, [dataForEachAnimal[idAnimal][numFrame] for idAnimal in range(nbAnimalsPerWell)])
      
      if np.sum(row_ind == col_ind) != nbAnimalsPerWell:
        newPossibilities = [dataForEachAnimal[i][numFrame].copy() for i in range(len(dataForEachAnimal))]
        for idx, rowId in enumerate(row_ind):
          colId = col_ind[idx]
          if rowId != colId:
            dataForEachAnimal[rowId][numFrame] = newPossibilities[colId]
      
      if printDebug:
        print(numFrame, [dataForEachAnimal[idAnimal][numFrame] for idAnimal in range(nbAnimalsPerWell)])
      
      for numAnimal in range(nbAnimalsPerWell):
        if np.sum(dataForEachAnimal[numAnimal][numFrame - 1] == [0, 0]) != 2 and np.sum(dataForEachAnimal[numAnimal][numFrame] == [0, 0]) == 2: # No candidate point was found for the current numAnimal trace
          if maximalDisappearanceFrames[numAnimal] < max_NbFramesAllowedToDisapeared:
            dataForEachAnimal[numAnimal][numFrame] = dataForEachAnimal[numAnimal][numFrame - 1]
            maximalDisappearanceFrames[numAnimal] += 1
          else: # Trace was lost after max_NbFramesAllowedToDisapeared disappearance: removing points artificially added
            nbFrameDisappeared = maximalDisappearanceFrames[numAnimal]
            
            distTravelMat = dataForEachAnimal[numAnimal][max(0, numFrame - nbFrameDisappeared - nbFramesNotAtZero[numAnimal] + 2)] - dataForEachAnimal[numAnimal][max(0, numFrame - nbFrameDisappeared)]
            # distTravelMat = curFirstCoordinates[numAnimal] - dataForEachAnimal[numAnimal][max(0, numFrame - nbFrameDisappeared)]
            distTravel    = np.sqrt(np.sum(distTravelMat**2))
            
            nbRemoveMoreFramesAsTraceTooShort = 0 if (nbFramesNotAtZero[numAnimal] >= minimumTraceLength and distTravel > minDistTravel) else nbFramesNotAtZero[numAnimal]
            
            for i in range(max(0, numFrame - nbFrameDisappeared - nbRemoveMoreFramesAsTraceTooShort - 1), numFrame):
              dataForEachAnimal[numAnimal][i][0] = 0
              dataForEachAnimal[numAnimal][i][1] = 0
            maximalDisappearanceFrames[numAnimal] = 0
            nbFramesNotAtZero[numAnimal] = 0
        else:
          if maximalDisappearanceFrames[numAnimal] != 0 and maximalDisappearanceFrames[numAnimal] != 2 * max_NbFramesAllowedToDisapeared: # A point had disappeared: rebuilding the lost points
            nbFrameDisappeared = maximalDisappearanceFrames[numAnimal]
            xOri = dataForEachAnimal[numAnimal][numFrame - nbFrameDisappeared][0]
            yOri = dataForEachAnimal[numAnimal][numFrame - nbFrameDisappeared][1]
            xEnd = dataForEachAnimal[numAnimal][numFrame][0]
            yEnd = dataForEachAnimal[numAnimal][numFrame][1]
            for i in range(numFrame - nbFrameDisappeared, numFrame):
              dataForEachAnimal[numAnimal][i][0] = xOri + ((i - (numFrame - nbFrameDisappeared)) / nbFrameDisappeared) * (xEnd - xOri)
              dataForEachAnimal[numAnimal][i][1] = yOri + ((i - (numFrame - nbFrameDisappeared)) / nbFrameDisappeared) * (yEnd - yOri)
            nbFramesNotAtZero[numAnimal] += nbFrameDisappeared
          else:
            if np.sum(dataForEachAnimal[numAnimal][numFrame] == [0, 0]) != 2:
              nbFramesNotAtZero[numAnimal] += 1
          maximalDisappearanceFrames[numAnimal] = 0
      
      if printDebug:
        print(numFrame, [dataForEachAnimal[idAnimal][numFrame] for idAnimal in range(nbAnimalsPerWell)])
    
    for numAnimal in range(nbAnimalsPerWell):
      if maximalDisappearanceFrames[numAnimal] != 0: # Removing artifically added points if the trace had not been "saved" by the end of the video
        nbFrameDisappeared = maximalDisappearanceFrames[numAnimal]
        for i in range(numFrame - nbFrameDisappeared, numFrame):
          dataForEachAnimal[numAnimal][i][0] = 0
          dataForEachAnimal[numAnimal][i][1] = 0
    
    for numAnimal in range(nbAnimalsPerWell):
      data = dataForEachAnimal[numAnimal]
      dataAPI.setDataPerTimeInterval(videoName, numWell, numAnimal, startTimeInSeconds, endTimeInSeconds, "HeadPos", data)
