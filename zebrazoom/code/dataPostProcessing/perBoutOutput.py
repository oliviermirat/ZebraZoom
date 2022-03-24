import cv2
import zebrazoom.videoFormatConversion.zzVideoReading as zzVideoReading
import os
import shutil
import math
import matplotlib.pyplot as plt
import numpy as np
import time
import pandas as pd
import pickle
from scipy import ndimage

def perBoutOutput(superStruct, hyperparameters, videoName):
  
  # Creation of the sub-folder "perBoutOutput"
  if hyperparameters["saveCurvaturePlots"] or hyperparameters["saveTailAngleGraph"] or hyperparameters["saveSubVideo"] or hyperparameters["saveCurvatureData"]:
    outputPath = os.path.join(os.path.join(hyperparameters["outputFolder"], videoName), "perBoutOutput")
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
      
  # opening the video previously created in createValidationVideo as an input video stream
  cap = zzVideoReading.VideoCapture(os.path.join(os.path.join(hyperparameters["outputFolder"], videoName), hyperparameters["videoName"] + '.avi'))
  
  if (cap.isOpened()== False): 
    print("Error opening video stream or file")
  
  # Video frame start and end
  firstFrame = hyperparameters["firstFrame"]
  lastFrame  = hyperparameters["lastFrame"]
  nbFrames   = lastFrame - firstFrame + 1
  perBoutOutputVideoStartStopFrameMargin = hyperparameters["perBoutOutputVideoStartStopFrameMargin"]
  
  # Getting well positions
  infoWells = []
  for i in range(0, len(superStruct["wellPositions"])):
    x = superStruct["wellPositions"][i]["topLeftX"]
    y = superStruct["wellPositions"][i]["topLeftY"]
    lengthX = superStruct["wellPositions"][i]["lengthX"]
    lengthY = superStruct["wellPositions"][i]["lengthY"]
    infoWells.append([x, y, lengthX, lengthY])
  
  # Going through each well, each fish and each bout
  for i in range(0, len(superStruct["wellPoissMouv"])):
    for j in range(0, len(superStruct["wellPoissMouv"][i])):
      for k in range(0, len(superStruct["wellPoissMouv"][i][j])):
        
        # Creation of the curvature graph for bout k
        TailX_VideoReferential = superStruct["wellPoissMouv"][i][j][k]["TailX_VideoReferential"]
        TailY_VideoReferential = superStruct["wellPoissMouv"][i][j][k]["TailY_VideoReferential"]
        
        curvature = []
        for l in range(0, len(TailX_VideoReferential)):
          tailX = TailX_VideoReferential[l]
          tailY = TailY_VideoReferential[l]

          ydiff  = np.diff(tailY)
          ydiff2 = np.diff(ydiff)
          xdiff  = np.diff(tailX)
          xdiff2 = np.diff(xdiff)
          curv = xdiff2
          l = len(curv)
          av = 0
          for ii in range(0, l-1):
            num = xdiff[ii] * ydiff2[ii] - ydiff[ii] * xdiff2[ii]
            den = (xdiff[ii]**2 + ydiff[ii]**2)**1.5
            curv[ii] = num / den
          
          curv = curv[hyperparameters["nbPointsToIgnoreAtCurvatureBeginning"]: l-1-hyperparameters["nbPointsToIgnoreAtCurvatureEnd"]]
          curvature.append(curv)
        
        rolling_window = hyperparameters["curvatureMedianFilterSmoothingWindow"]
        if rolling_window:
          curvature = ndimage.median_filter(curvature, size=rolling_window) # 2d median filter
        else:
          curvature = np.array(curvature)
        
        curvature = np.flip(np.transpose(curvature), 0)
        
        superStruct["wellPoissMouv"][i][j][k]["curvature"] = curvature.tolist()
        
        if hyperparameters["saveCurvaturePlots"]:
          fig = plt.figure(1)
          maxx = max([max(abs(np.array(t))) for t in curvature])
          plt.pcolor(curvature, vmin=-maxx, vmax=maxx, cmap=hyperparameters["colorMapCurvature"])
          ax = fig.axes
          ax[0].set_ylabel('Rostral to Caudal')
          if hyperparameters["videoFPS"]:
            ax[0].set_xlabel('Second')
            plt.xticks([i for i in range(0, len(curvature[0]), int(len(curvature[0])/10))], [int(100*(i/hyperparameters["videoFPS"]))/100 for i in range(0, len(curvature[0]), int(len(curvature[0])/10))])
          else:
            ax[0].set_xlabel('Frame number')
          plt.colorbar()
          plt.savefig(os.path.join(outputPath, hyperparameters["videoName"] + "_curvature_bout" + str(i) + '_' + str(j) + '_' + str(k) + '.png'))
          plt.close(1)
        
        if hyperparameters["saveCurvatureData"]:
          curvatureMatrixFile = open(os.path.join(outputPath, hyperparameters["videoName"] + "_curvatureData" + str(i) + '_' + str(j) + '_' + str(k) + '.txt'), 'wb')
          pickle.dump(curvature, curvatureMatrixFile)
          curvatureMatrixFile.close()
        
        
        # Creation of tail angle graph for bout k
        if hyperparameters["saveTailAngleGraph"]:
          bStart = superStruct["wellPoissMouv"][i][j][k]["BoutStart"]
          bEnd   = superStruct["wellPoissMouv"][i][j][k]["BoutEnd"]
          tailAngle = superStruct["wellPoissMouv"][i][j][k]["TailAngle_smoothed"]
          if bEnd - bStart + 1 == len(tailAngle):
            plt.figure(1)
            plt.plot([i for i in range(bStart, bEnd + 1)], [t*(180/math.pi) for t in tailAngle])
            if hyperparameters["perBoutOutputYaxis"]:
              plt.axis([bStart, bEnd + 1, hyperparameters["perBoutOutputYaxis"][0], hyperparameters["perBoutOutputYaxis"][1]])
            plt.savefig(os.path.join(outputPath, hyperparameters["videoName"] + "_angle_bout" + str(i) + '_' + str(j) + '_' + str(k) + '.png'))
            plt.close(1)
        
        # Creation of sub-video for bout k
        if hyperparameters["saveSubVideo"]:
          x0 = superStruct["wellPoissMouv"][i][j][k]["HeadX"][0]
          y0 = superStruct["wellPoissMouv"][i][j][k]["HeadY"][0]
          TailX_VideoReferential = superStruct["wellPoissMouv"][i][j][k]["TailX_VideoReferential"]
          TailY_VideoReferential = superStruct["wellPoissMouv"][i][j][k]["TailY_VideoReferential"]
          tailExtX = TailX_VideoReferential[0][len(TailX_VideoReferential[0])-1]
          tailExtY = TailY_VideoReferential[0][len(TailY_VideoReferential[0])-1]
          dist = int((math.sqrt((tailExtX-x0)**2 + (tailExtY-y0)**2))*1.3)
          
          outputName = os.path.join(outputPath, hyperparameters["videoName"] + "_bout" + str(i) + '_' + str(j) + '_' + str(k) + '.avi')
          if dist < cap.get(3) and dist < cap.get(4):
            outputVideoX = int(dist)
            outputVideoY = int(dist)
          else:
            outputVideoX = min(cap.get(3), cap.get(4))
            outputVideoY = min(cap.get(3), cap.get(4))
          
          out = cv2.VideoWriter(outputName,cv2.VideoWriter_fourcc('M','J','P','G'), 10, (outputVideoX, outputVideoY))
          
          BoutStart = superStruct["wellPoissMouv"][i][j][k]["BoutStart"] - perBoutOutputVideoStartStopFrameMargin
          BoutEnd = superStruct["wellPoissMouv"][i][j][k]["BoutEnd"] + perBoutOutputVideoStartStopFrameMargin
          if BoutStart < 0:
            BoutStart = 0
          if BoutEnd >= lastFrame:
            BoutEnd = lastFrame - 1
          mouvLength = len(superStruct["wellPoissMouv"][i][j][k]["HeadX"])
          cap.set(1, BoutStart - firstFrame)
          
          for l in range(BoutStart, BoutEnd):
            ret, frame = cap.read()
            
            if l < superStruct["wellPoissMouv"][i][j][k]["BoutStart"]:
              l2 = 0
            elif l >= superStruct["wellPoissMouv"][i][j][k]["BoutEnd"]:
              l2 = mouvLength - 1
            else:
              l2 = l - superStruct["wellPoissMouv"][i][j][k]["BoutStart"]
            x = superStruct["wellPoissMouv"][i][j][k]["HeadX"][l2]
            y = superStruct["wellPoissMouv"][i][j][k]["HeadY"][l2]
            Heading = superStruct["wellPoissMouv"][i][j][k]["Heading"][l2]
            
            x = int(x + infoWells[i][0])
            y = int(y + infoWells[i][1])
            
            rows = len(frame)
            cols = len(frame[0])
            M = cv2.getRotationMatrix2D((x, y), -(((math.pi/2) - (Heading+math.pi))%(2*math.pi))*(180/math.pi), 1)
            frame = cv2.warpAffine(frame, M, (cols,rows))
            
            if int(x-dist/2)+outputVideoX <= 0:
              print("problem in perBoutOutput")
            else:
              if int(x-dist/2) > 0:
                frame = frame[int(y):int(y)+outputVideoY, int(x-dist/2):int(x-dist/2)+outputVideoX]
              else:
                frame = frame[int(y):int(y)+outputVideoY, 0:outputVideoX]
            
            frame2 = np.zeros((outputVideoX, outputVideoY, 3), np.uint8)
            frame2[0:len(frame), 0:len(frame[0]), :] = frame[0:len(frame), 0:len(frame[0]), :]
            frame = frame2
            
            cv2.putText(frame, str(l + hyperparameters["firstFrame"] - 1), (int(outputVideoX - 100), int(outputVideoY - 30)), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0))
            
            out.write(frame)
            
          out.release()
  
  return superStruct
