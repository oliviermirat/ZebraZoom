import os

import matplotlib.pyplot as plt
import pandas as pd
import numpy as np

def _readFPSAndPixelSize(fname):
  headerRows = 0
  with open(fname) as f:
    line = f.readline()
    if line.startswith('videoFPS'):  # If videoFPS is stored in the file, read it
      videoFPS = float(line.split()[1])
      headerRows += 1
      line = f.readline()
    else:
      videoFPS = 300  # This value will be used if videoFPS is not stored in the file
    if line.startswith('videoPixelSize'):  # If videoPixelSize is stored in the file, read it
      videoPixelSize = float(line.split()[1])
      headerRows += 1
    else:
      videoPixelSize = 0.02  # This value will be used if videoPixelSize is not stored in the file
  return videoFPS, videoPixelSize, headerRows


def _plotCurvature(curvature, maxCurvatureValues, curvatureXaxisNbFrames, videoFPS, videoPixelSize, tailLenghtInPixels):
  
  if maxCurvatureValues == 0:
    maxx = max([max(abs(np.array(t))) for t in curvature])
  else:
    maxx = maxCurvatureValues    

  fig = plt.figure(1)
  # 'BrBG' is the colormap chosen here, you can view other options on this page: https://matplotlib.org/3.5.1/tutorials/colors/colormaps.html (in the paragraph "Diverging")

  if curvatureXaxisNbFrames != 0:
    if len(curvature[0]) < curvatureXaxisNbFrames:
      curvature2 = np.pad(curvature, ((0, 0), (0, curvatureXaxisNbFrames - len(curvature[0]))), mode='constant')
    elif len(curvature[0]) > curvatureXaxisNbFrames:
      curvature2 = curvature[:, 0:curvatureXaxisNbFrames]
    else:
      curvature2 = curvature
  else:
    curvature2 = curvature
  
  plt.pcolor(curvature, vmin=-maxx, vmax=maxx, cmap='BrBG')

  ax = fig.axes
  ax[0].set_xlabel('Second')
  plt.xticks([i for i in range(0, len(curvature[0]), 10)], [int(100*(i/videoFPS))/100 for i in range(0, len(curvature[0]), 10)])
  ax[0].set_ylabel('Rostral to Caudal (in mm)')
  plt.yticks([i for i in range(0, len(curvature2), int(len(curvature2)/10))], [int(100 * videoPixelSize * tailLenghtInPixels * (i/len(curvature2)) )/100 for i in range(0, len(curvature2), int(len(curvature2)/10))])

  plt.colorbar()
  plt.show()


if __name__ == '__main__':
  # One csv file should have been generated for each animal in each well inside the output data folder if "saveAllDataEvenIfNotInBouts" was set to 1 in the configuration file
  # To load the data for the specific video, well and animal combination the following values should be modified:
  ZZoutputPath = 'ZebraZoom/zebrazoom/ZZoutput'
  videoName    = 'nameOfVideo'
  wellNumber   = 0
  animalNumber = 0
  boutNumber   = 0
  
  maxCurvatureValues = 0 #0.02 # Set to 0 if you don't want the curvature scale to be fixed (the scale will then be change from one bout to the next); set to the maximum curvature value otherwise
  curvatureXaxisNbFrames = 0 #300 # Set to 0 if you don't all graphs to be of the same length on the x axis; set to length on the x axis otherwise

  fname = os.path.join(ZZoutputPath, videoName, f'allData_{videoName}_wellNumber{wellNumber}_animal{animalNumber}.csv')
  videoFPS, videoPixelSize, headerRows = _readFPSAndPixelSize(fname)  # To use custom videoFPS and videoPixelSize values instead of the ones found in the file, uncomment the lines below and modify the values
  # videoFPS = 300
  # videoPixelSize = 0.02

  data = pd.read_csv(fname, skiprows=headerRows)
  dataL = data[data['BoutNumber'] == boutNumber]
  allCurvCols = [curvCol for curvCol in dataL.columns if 'curvature' in curvCol]
  curvature = np.transpose(dataL[allCurvCols].to_numpy())
  tailLenghtInPixels = dataL["TailLength"][dataL.index[0]]
  
  _plotCurvature(curvature, maxCurvatureValues, curvatureXaxisNbFrames, videoFPS, videoPixelSize, tailLenghtInPixels)

