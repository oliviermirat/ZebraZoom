import os

import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

def plotCurvatureYaxisExact(curvatureValues: np.array, xTimeValues: np.array, yDistanceAlongTail: np.array, videoFPS: float, videoPixelSize: float, maxCurvatureValues: float = 0.05, xAxisLengthInSeconds: int = 1, yAxisLengthInMm: int = 6) -> None:
  
  x = xTimeValues.flatten()
  y = yDistanceAlongTail.flatten()
  values    = curvatureValues.flatten()
  boutStart = xTimeValues[0,0] * videoFPS
  
  if maxCurvatureValues == 0:
    maxx = max([max(abs(np.array(t))) for t in curvatureValues])
  else:
    maxx = maxCurvatureValues
  
  fig, ax = plt.subplots()
  scatter = ax.scatter(x, y, c=values, cmap='viridis', s=40, vmin=-maxx, vmax=maxx)
  ax.set_xlim(boutStart / videoFPS, (boutStart / videoFPS) + xAxisLengthInSeconds)
  maxY = np.max(y) * 1.05
  ax.set_ylim(maxY, maxY - yAxisLengthInMm)
  for spine in ax.spines.values():
      spine.set_edgecolor('white')
  cbar = fig.colorbar(scatter)
  cbar.set_label('Values')
  ax.set_xlabel('Time (in seconds)')
  ax.set_ylabel('Rostral to Caudal (in mm)')
  plt.show()
