import os

import matplotlib.pyplot as plt
import pandas as pd
import numpy as np


def plotCurvatureYaxisApproximateImplementation(curvature: np.array, xTimeValues: np.array, yDistanceAlongTheTail: np.array, videoFPS: float, videoPixelSize: float, cmapVal: str = 'coolwarm', maxCurvatureValues: float = 0.05, xAxisLengthInSeconds: int = 1, yAxisLengthInMm: int = 6) -> None:

  boutStart          = xTimeValues[0,0] * videoFPS
  tailLengthInPixels = yDistanceAlongTheTail[0, len(yDistanceAlongTheTail[0]) - 1] / videoPixelSize

  if maxCurvatureValues is None:
    maxCurvatureValues = max(max(t.min(), t.max(), key=abs) for t in curvature)

  fig = plt.figure()
  ax = fig.add_subplot(111)
  cax = ax.pcolor(curvature, vmin=-maxCurvatureValues, vmax=maxCurvatureValues, cmap=cmapVal)

  for spine in ax.spines.values():
    spine.set_edgecolor('white')

  nbTicksXaxis = int(int(100*((len(curvature)+boutStart)/videoFPS))/100 - int(100*((boutStart)/videoFPS))/100) + 1
  if nbTicksXaxis <= 2:
    nbTicksXaxis = 2
  nbTicksXaxis = 5

  nbTicksYaxis = int(100 * videoPixelSize * tailLengthInPixels * ((len(curvature))/len(curvature)) )/100
  if nbTicksYaxis <= 2:
    nbTicksYaxis = 2

  ax.set_xlabel('Time (in seconds)')
  nbXaxis = int(len(curvature[0])/nbTicksXaxis) if int(len(curvature[0])/nbTicksXaxis) >= 2 else 2
  plt.xticks([i for i in range(0, len(curvature[0]), nbXaxis)], [int(100*(xTimeValues[0, i]))/100 for i in range(0, len(curvature[0]), nbXaxis)])
  ax.set_ylabel('Rostral to Caudal (in mm)')
  nbYaxis = int(len(curvature)/nbTicksYaxis) if int(len(curvature)/nbTicksYaxis) >= 2 else 2
  plt.yticks([i for i in range(0, len(curvature), nbYaxis)], [int(100 * videoPixelSize * tailLengthInPixels * ((len(curvature)-i)/len(curvature)) )/100 for i in range(0, len(curvature), nbYaxis)])

  ax.set_xlim([0, xAxisLengthInSeconds * videoFPS])
  ax.set_ylim([0, (yAxisLengthInMm * len(curvature)) / (videoPixelSize * tailLengthInPixels)])

  cbar = fig.colorbar(cax)


def plotCurvatureYaxisApproximate(curvature: np.array, xTimeValues: np.array, yDistanceAlongTheTail: np.array, videoFPS: float, videoPixelSize: float, cmapVal: str = 'coolwarm', maxCurvatureValues: float = 0.05, xAxisLengthInSeconds: int = 1, yAxisLengthInMm: int = 6) -> None:
  plotCurvatureYaxisApproximateImplementation(curvature, xTimeValues, yDistanceAlongTheTail, videoFPS, videoPixelSize, cmapVal=cmapVal, maxCurvatureValues=maxCurvatureValues, xAxisLengthInSeconds=xAxisLengthInSeconds, yAxisLengthInMm=yAxisLengthInMm)
  plt.show()
