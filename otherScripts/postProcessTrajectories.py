import zebrazoom.dataAPI as dataAPI
import matplotlib.pyplot as plt
from scipy import stats
import pandas as pd
import numpy as np
import shutil
import math
import os

videoNameOri = "CF_1_4_ala3R_Exp5_2024_09_30-19_10_50" #"CF_1_4_ala3R_Exp5_2024_09_25-11_35_05"
videoName    = "CF_1_4_ala3R_Exp5_copy_2024_09_30-19_10_50"
ZZoutputPath = os.path.join('zebrazoom', 'ZZoutput')

window_size_options = [10, 50, 100, 200]
plotFigs = False
postProcessPointsOnBorders = True

startTimeInSeconds = 0
endTimeInSeconds = 833 #291

nbWells = 4
videoFPS = 24
videoPixelSize = 0.01

dataAPI.setFPSandPixelSize(videoName, videoFPS, videoPixelSize)


def findOutliersSimple(distances):
  z_score_max = 2 #3
  non_nan_indices = np.where(~np.isnan(distances))[0]
  cleaned_distances = distances[non_nan_indices]
  z_scores = np.abs(stats.zscore(cleaned_distances))
  outlier_cleaned_indices = np.where(z_scores > z_score_max)[0]
  outlier_original_indices = non_nan_indices[outlier_cleaned_indices]
  return outlier_original_indices

def findOutliers(distances, z_score_max=2, mean=None, std=None):
  non_nan_indices = np.where(~np.isnan(distances))[0]
  cleaned_distances = distances[non_nan_indices]
  
  if mean is None:
    mean = np.mean(cleaned_distances)
    print("mean:", mean)
  if std is None:
    std = np.std(cleaned_distances)
    print("std:", std)
  
  z_scores = np.abs((cleaned_distances - mean) / std)
  
  outlier_cleaned_indices = np.where(z_scores > z_score_max)[0]
  outlier_original_indices = non_nan_indices[outlier_cleaned_indices]
  
  return outlier_original_indices


shutil.copyfile(os.path.join(ZZoutputPath, videoNameOri + ".h5"), os.path.join(ZZoutputPath, videoName + ".h5"))

for numWell in range(nbWells):
  
  numAnimal = 0

  data = dataAPI.getDataPerTimeInterval(videoName, numWell, numAnimal, startTimeInSeconds, endTimeInSeconds, "HeadPos")
  
  df = pd.DataFrame(data, columns=['Column1', 'Column2'])
  
  outliers = np.array([])
  
  for window_size in window_size_options:
    
    print("numWell:", numWell, "; window_size:", window_size)
    
    df_rolling = df.rolling(window=window_size).mean()
    data_rolling = df_rolling.to_numpy()
    distances = np.linalg.norm(data - data_rolling, axis=1)
    
    # Plotting both original and rolling mean data on a 2D graph
    if plotFigs:
      plt.figure(figsize=(10, 6))
      plt.plot(df['Column1'], df['Column2'], label='Original Data', color='blue', linestyle='--', marker='o')
      plt.plot(df_rolling['Column1'], df_rolling['Column2'], label='Rolling Mean Data', color='red', linestyle='-', marker='x')
      plt.title('Original vs Rolling Mean Data (2D Plot)')
      plt.xlabel('Column 1')
      plt.ylabel('Column 2')
      plt.legend()
      plt.grid(True)
      plt.show()
      plt.figure(figsize=(10, 6))
      plt.plot(distances, label='Euclidean Distance', marker='o')
      plt.title('Euclidean Distance Between Original and Rolling Mean Data at Each Timepoint')
      plt.xlabel('Timepoint')
      plt.ylabel('Distance')
      plt.grid(True)
      plt.legend()
      plt.show()

    condition1 = findOutliers(distances)
    condition2 = findOutliers(abs(np.diff(distances, prepend=np.nan)))
    # outliersForWindow = np.where(condition1 | condition2)[0]
    outliersForWindow = np.unique(np.sort(np.concatenate((condition1, condition2))))
    
    outliers = np.unique(np.sort(np.concatenate((outliers, outliersForWindow))))

  zero_rows_indices = np.where((data[:, 0] == 0) & (data[:, 1] == 0))
  outliers = np.unique(np.sort(np.concatenate((outliers, zero_rows_indices[0]))))

  # Replacing outlier data by value of previous frame
  for idx in outliers.astype(int):
    if idx > 0:
      data[idx] = data[idx - 1]
  
  # Post processing points on borders
  if postProcessPointsOnBorders:
    borderMargin = 1 #self._hyperparameters["postProcessRemovePointsOnBordersMargin"]
    [topLeftX, topLeftY, lengthX, lengthY] = dataAPI.getWellCoordinates(videoName, numWell)
    for frameNumber in range(0, len(data)):
      xHead = data[frameNumber][0]
      yHead = data[frameNumber][1]
      if (xHead <= borderMargin) or (yHead <= borderMargin) or (xHead >= lengthX - borderMargin - 1) or (yHead >= lengthY - borderMargin - 1):
        data[frameNumber][0] = 0
        data[frameNumber][1] = 0
      
    currentlyZero  = False
    zeroFrameStart = 0
    for frameNumber in range(0, len(data)):
      print("frameNumber:", frameNumber)
      xHead = data[frameNumber][0]
      yHead = data[frameNumber][1]
      if frameNumber != 0:
        xHeadPrev = data[frameNumber-1][0]
        yHeadPrev = data[frameNumber-1][1]
      else:
        xHeadPrev = data[frameNumber][0]
        yHeadPrev = data[frameNumber][1]
      if xHead == 0 and yHead == 0 and (frameNumber != len(data) - 1):
        if not(currentlyZero):
          zeroFrameStart = frameNumber
        # print("currentlyZero at True: animalId:", animalId, "; frameNumber:", frameNumber)
        currentlyZero = True
      else:
        if currentlyZero:
          if zeroFrameStart >= 1:
            xHeadStart = data[zeroFrameStart-1][0]
            yHeadStart = data[zeroFrameStart-1][1]
          else:
            xHeadStart = data[frameNumber][0]
            yHeadStart = data[frameNumber][1]
          xHeadEnd = data[frameNumber][0]
          yHeadEnd = data[frameNumber][1]
          
          currentlyZero = False
          if not((xHeadEnd == 0) and (yHeadEnd == 0)):
            xStep = (xHeadEnd - xHeadStart) / (frameNumber - zeroFrameStart)
            yStep = (yHeadEnd - yHeadStart) / (frameNumber - zeroFrameStart)
            for frameAtZeroToChange in range(zeroFrameStart, frameNumber):
              data[frameAtZeroToChange][0] = xHeadStart + xStep * (frameAtZeroToChange - zeroFrameStart)
              data[frameAtZeroToChange][1] = yHeadStart + yStep * (frameAtZeroToChange - zeroFrameStart)
          else:
            for frameAtZeroToChange in range(zeroFrameStart, frameNumber):
              data[frameAtZeroToChange][0] = xHeadStart
              data[frameAtZeroToChange][1] = yHeadStart
  
  
  dataAPI.setDataPerTimeInterval(videoName, numWell, numAnimal, startTimeInSeconds, endTimeInSeconds, 'HeadPos', data)

