import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

###
### The parameters below need to be adjusted
###

data = pd.read_pickle('nameOfVideo.pkl') # The pkl file should have been generated inside the output data folder if "createPandasDataFrameOfParameters" was set to 1 in the configuration file

numBout        = 0 # Choose the number of the bout you want to plot (can be between 0 and len(data))
videoFPS       = 300
videoPixelSize = 0.02

maxCurvatureValues = 0 #0.02 # Set to 0 if you don't want the curvature scale to be fixed (the scale will then be change from one bout to the next); set to the maximum curvature value otherwise
curvatureXaxisNbFrames = 0 #300 # Set to 0 if you don't all graphs to be of the same length on the x axis; set to length on the x axis otherwise
tailLenghtInPixels = 0 #40 # Set to 0 for the y axis to be in arbitrary unit

###
###
###

curvature = data.loc[numBout]['curvature']

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
