import cv2
import os
import shutil
import math
import matplotlib.pyplot as plt
import numpy as np
import time
import pandas as pd
import pickle
import scipy as sp

def tailAnglesHeatMap(superStruct, hyperparameters, videoName):
  
  # Creation of the sub-folder "anglesHeatMap" 
  outputPath = os.path.join(os.path.join(hyperparameters["outputFolder"], videoName), "anglesHeatMap")
  if os.path.exists(outputPath):
    shutil.rmtree(outputPath)
  while True:
    try:
      os.mkdir(outputPath)
      break
    except OSError as e:
      print("waiting inside except")
      time.sleep(0.1)
    else:
      print("waiting")
      time.sleep(0.1)
  
  # Video frame start and end
  firstFrame = hyperparameters["firstFrame"]
  lastFrame  = hyperparameters["lastFrame"]
  nbFrames   = lastFrame - firstFrame + 1
  perBoutOutputVideoStartStopFrameMargin = hyperparameters["perBoutOutputVideoStartStopFrameMargin"]
  
  plotTailAngleRaw      = False
  plotTailAngleSmoothed = False
  plotTailAngleHeatmap  = True
  
  pointsToTakeIntoAccountStart = 9 - int(hyperparameters["tailAnglesHeatMapNbPointsToTakeIntoAccount"])
  
  # Going through each well, each fish and each bout
  for i in range(0, len(superStruct["wellPoissMouv"])):
    for j in range(0, len(superStruct["wellPoissMouv"][i])):
      for k in range(0, len(superStruct["wellPoissMouv"][i][j])):
        
        # Creation of tail angles raw graph for bout k
        if plotTailAngleRaw:
          bStart = superStruct["wellPoissMouv"][i][j][k]["BoutStart"]
          bEnd   = superStruct["wellPoissMouv"][i][j][k]["BoutEnd"]
          tailAngles = superStruct["wellPoissMouv"][i][j][k]["allTailAngles"][pointsToTakeIntoAccountStart:]
          plt.figure(1)
          for tailAngle in tailAngles:
            if bEnd - bStart + 1 == len(tailAngle):
              plt.plot([i for i in range(bStart, bEnd + 1)], [t*(180/math.pi) for t in tailAngle])
              if hyperparameters["perBoutOutputYaxis"]:
                plt.axis([bStart, bEnd + 1, hyperparameters["perBoutOutputYaxis"][0], hyperparameters["perBoutOutputYaxis"][1]])
          plt.savefig(os.path.join(outputPath, hyperparameters["videoName"] + "_angles_bout" + str(i) + '_' + str(j) + '_' + str(k) + '.png'))
          plt.close(1)
        
        # Creation of tail angles smoothed graph and tail angle heatmap for bout k
        bStart = superStruct["wellPoissMouv"][i][j][k]["BoutStart"]
        bEnd   = superStruct["wellPoissMouv"][i][j][k]["BoutEnd"]
        tailAngles = superStruct["wellPoissMouv"][i][j][k]["allTailAnglesSmoothed"][pointsToTakeIntoAccountStart:]
        tailAngleHeatmap = []
        if plotTailAngleSmoothed:
          plt.figure(1)
        for tailAngle in tailAngles:
          if bEnd - bStart + 1 == len(tailAngle):
            tailAngleHeatmap.append([t*(180/math.pi) for t in tailAngle])
            if plotTailAngleSmoothed:
              plt.plot([i for i in range(bStart, bEnd + 1)], [t*(180/math.pi) for t in tailAngle])
              if hyperparameters["perBoutOutputYaxis"]:
                plt.axis([bStart, bEnd + 1, hyperparameters["perBoutOutputYaxis"][0], hyperparameters["perBoutOutputYaxis"][1]])
        if plotTailAngleSmoothed:
          plt.savefig(os.path.join(outputPath, hyperparameters["videoName"] + "_anglesSmoothed_bout" + str(i) + '_' + str(j) + '_' + str(k) + '.png'))
          plt.close(1)
        
        # Creation of tail angle heatmap
        if plotTailAngleHeatmap:
          fig = plt.figure(1)
          # plt.pcolor(tailAngleHeatmap)
          plt.pcolor(tailAngleHeatmap, vmin=-180, vmax=180)
          ax = fig.axes
          ax[0].set_xlabel('Frame number')
          ax[0].set_ylabel('Tail angle: Tail base to tail extremity')
          plt.colorbar()
          plt.savefig(os.path.join(outputPath, hyperparameters["videoName"] + "_tailAngleHeatmap_bout" + str(i) + '_' + str(j) + '_' + str(k) + '.png'))
          plt.close(1)
        