import os

import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

def plotCurvatureYaxisExact(curvatureValues, xTimeValues, yDistanceAlongTail):

  # Input parameters of this function should actually be:
  # name, curvature, maxCurvatureValues, xAxisLengthInSeconds, yAxisLengthInPixels, videoFPS, videoPixelSize, boutStart, boutEnd

  allTailXCols = ['HeadPosX'] + [col for col in dataL.columns if 'TailPosX' in col]
  allTailYCols = ['HeadPosY'] + [col for col in dataL.columns if 'TailPosY' in col]
  tailX = np.transpose(dataL[allTailXCols].to_numpy())
  tailY = np.transpose(dataL[allTailYCols].to_numpy())
  nbLinesTail = len(tailX)
  tailLengthCumul = curvature.copy()
  if True: # This is technically the correct one, but need to plot the y axis up side down
    tailLengthCumul[:, :] = np.sqrt(np.square(tailX[2:nbLinesTail, :] - tailX[1:nbLinesTail-1, :]) + np.square(tailY[2:nbLinesTail, :] - tailY[1:nbLinesTail-1, :])) * videoPixelSize
    for i in range(len(tailLengthCumul)-2, -1, -1):
      tailLengthCumul[i, :] += tailLengthCumul[i+1, :]
  else:
    tailLengthCumul[:, :] = np.sqrt(np.square(tailX[2:nbLinesTail, :] - tailX[1:nbLinesTail-1, :]) + np.square(tailY[2:nbLinesTail, :] - tailY[1:nbLinesTail-1, :])) * videoPixelSize
    # for i in range(len(tailLengthCumul)-2, -1, -1):
    for i in range(0, len(tailLengthCumul)-2, 1):
      tailLengthCumul[i+1, :] += tailLengthCumul[i, :]
  
  time = curvature.copy()
  for i in range(0, len(time[0])):
    time[:, i] = int(100*((i+boutStart)/videoFPS))/100
  
  x = time.flatten()
  y = tailLengthCumul.flatten()
  values = curvature.flatten()
  
  if maxCurvatureValues == 0:
    maxx = max([max(abs(np.array(t))) for t in curvature])
  else:
    maxx = maxCurvatureValues
  
  fig, ax = plt.subplots()
  scatter = ax.scatter(x, y, c=values, cmap='viridis', s=40, vmin=-maxx, vmax=maxx)
  ax.set_xlim(boutStart / videoFPS, (boutStart / videoFPS) + xAxisLengthInSeconds)
  maxY = np.max(y) * 1.05
  ax.set_ylim(maxY, maxY - yAxisLengthInPixels)
  for spine in ax.spines.values():
      spine.set_edgecolor('white')
  cbar = fig.colorbar(scatter)
  cbar.set_label('Values')
  ax.set_xlabel('Time (in seconds)')
  ax.set_ylabel('Rostral to Caudal (in mm)')
  plt.show()



def plotCurvatureYaxisApproximate(curvatureValues, xTimeValues, yDistanceAlongTail):
  
  # Input parameters should actually be:
  # name, curvature, maxCurvatureValues, xAxisLengthInSeconds, yAxisLengthInPixels, videoFPS, videoPixelSize, tailLenghtInPixels, boutStart, boutEnd
  
  if maxCurvatureValues == 0:
    maxx = max([max(abs(np.array(t))) for t in curvature])
  else:
    maxx = maxCurvatureValues

  fig = plt.figure()
  ax = fig.add_subplot(111)
  cax = ax.pcolor(curvature, vmin=-maxx, vmax=maxx, cmap='BrBG')

  # Set color of the surrounding box
  for spine in ax.spines.values():
    spine.set_edgecolor('white')
  
  nbTicks = 5
  
  ax.set_xlabel('Time (in seconds)')
  plt.xticks([i for i in range(0, len(curvature[0]), int(len(curvature[0])/nbTicks))], [int(100*((i+boutStart)/videoFPS))/100 for i in range(0, len(curvature[0]), int(len(curvature[0])/nbTicks))])
  ax.set_ylabel('Rostral to Caudal (in mm)')
  plt.yticks([i for i in range(0, len(curvature), int(len(curvature)/nbTicks))], [int(100 * videoPixelSize * tailLenghtInPixels * ((len(curvature)-i)/len(curvature)) )/100 for i in range(0, len(curvature), int(len(curvature)/nbTicks))])
  
  ax.set_xlim([0, xAxisLengthInSeconds * videoFPS])
  ax.set_ylim([0, (yAxisLengthInPixels * len(curvature)) / (videoPixelSize * tailLenghtInPixels)])
  
  cbar = fig.colorbar(cax)
  plt.show()
