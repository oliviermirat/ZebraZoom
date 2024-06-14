from sklearn.preprocessing import MinMaxScaler
import zebrazoom.dataAPI as dataAPI
import matplotlib.pyplot as plt
import numpy as np
import pickle
import math

# regular tracking first 1000 frames
# videoName = "C:/Users/mirat/Desktop/openZZ/ZebraZoom/zebrazoom/ZZoutput/subvideoAll_2024_06_12-16_56_17.h5"
# nbFrames  = 1000

# regular tracking all frames
videoName = "C:/Users/mirat/Desktop/openZZ/ZebraZoom/zebrazoom/ZZoutput/Trial1_2024_06_13-19_12_12.h5"
nbFrames  = 152825

# Fast tracking
# videoName = "C:/Users/mirat/Desktop/openZZ/ZebraZoom/zebrazoom/ZZoutput/subvideoAll_2024_06_12-17_08_31.h5"
# nbFrames  = 1000


videoFPS = 40
numAnimal = 0
videoPixelSize = 1
dataAPI.setFPSandPixelSize(videoName, videoFPS, videoPixelSize)

fig, axs = plt.subplots(4, 6)

# Getting data
movementDataToExport = []
for numWell in range(24):
  print("numWell:", numWell)
  movementDataToExport.append(dataAPI.createExcelFileWithRawData(videoName, numWell, numAnimal, 1, nbFrames))

fig, axs = plt.subplots(4, 6)
for numWell in range(24):
  print("numWell:", numWell)
  mov = movementDataToExport[numWell]
  # filtered_mov = mov[mov['subsequentPointsDistance'] != 0]
  TailLength = mov['TailLength'] * videoPixelSize
  axs[int(numWell/6)][int(numWell%6)].hist(TailLength)
  axs[int(numWell/6)][int(numWell%6)].set_title("Median: " + str(int(np.median(TailLength)*10)/10))
plt.tight_layout()
plt.show()


fig, axs = plt.subplots(4, 6)
for numWell in range(24):
  print("numWell:", numWell)
  mov = movementDataToExport[numWell]
  TailLength = mov['TailLength'] * videoPixelSize
  axs[int(numWell/6)][int(numWell%6)].plot(TailLength)
plt.show()
