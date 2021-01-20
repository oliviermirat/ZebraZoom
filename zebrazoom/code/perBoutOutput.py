import cv2
import os
import shutil
import math
import matplotlib.pyplot as plt
import numpy as np
import time
import pandas as pd
import pickle

def perBoutOutput(superStruct, hyperparameters, videoName):
  
  # Creation of the sub-folder "perBoutOutput" 
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
  cap = cv2.VideoCapture(os.path.join(os.path.join(hyperparameters["outputFolder"], videoName), hyperparameters["videoName"] + '.avi'))
  
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
          # curvature calculation method 1
          # a = np.array([[tailX[m], tailY[m]] for m in range(5, len(tailX))]) # CHECK OUT THE 5 HERE !!!
          # dx_dt = np.gradient(a[:, 0])
          # dy_dt = np.gradient(a[:, 1])
          # velocity = np.array([ [dx_dt[i], dy_dt[i]] for i in range(dx_dt.size)])
          # ds_dt = np.sqrt(dx_dt * dx_dt + dy_dt * dy_dt)
          # tangent = np.array([1/ds_dt] * 2).transpose() * velocity
          # tangent_x = tangent[:, 0]
          # tangent_y = tangent[:, 1]
          # deriv_tangent_x = np.gradient(tangent_x)
          # deriv_tangent_y = np.gradient(tangent_y)
          # dT_dt = np.array([ [deriv_tangent_x[i], deriv_tangent_y[i]] for i in range(deriv_tangent_x.size)])
          # length_dT_dt = np.sqrt(deriv_tangent_x * deriv_tangent_x + deriv_tangent_y * deriv_tangent_y)
          # normal = np.array([1/length_dT_dt] * 2).transpose() * dT_dt
          # d2s_dt2 = np.gradient(ds_dt)
          # d2x_dt2 = np.gradient(dx_dt)
          # d2y_dt2 = np.gradient(dy_dt)
          # curv = np.abs(d2x_dt2 * dy_dt - dx_dt * d2y_dt2) / (dx_dt * dx_dt + dy_dt * dy_dt)**1.5
          # curvature calculation method 2
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
          curv = curv[1:l-2]  
          curvature.append(curv)
          
        rolling_window = hyperparameters["curvatureMedianFilterSmoothingWindow"]
        curvature2 = []
        curvatureTransposed = np.transpose(curvature)
        for transposedCurv in curvatureTransposed:
          # x = [i for i in range(0, len(transposedCurv))]
          # tck = splrep(x, transposedCurv, s=0.0001)
          # smoothedTransposedCurv = splev(x, tck)
          shift = int(-rolling_window / 2)
          smoothedTransposedCurv = np.array(pd.Series(transposedCurv).rolling(rolling_window).median())
          smoothedTransposedCurv = np.roll(smoothedTransposedCurv, shift)
          for ii in range(0, rolling_window):
            smoothedTransposedCurv[ii] = transposedCurv[ii]
          for ii in range(len(smoothedTransposedCurv)-rolling_window,len(smoothedTransposedCurv)):
            smoothedTransposedCurv[ii] = transposedCurv[ii] 
          curvature2.append(smoothedTransposedCurv)  
        curvature = np.transpose(curvature2)
          
        fig = plt.figure(1)
        plt.pcolor(curvature)
        
        ax = fig.axes
        ax[0].set_xlabel('Rostral to Caudal')
        ax[0].set_ylabel('Frame number')
        plt.colorbar()
        plt.savefig(os.path.join(outputPath, hyperparameters["videoName"] + "_curvature_bout" + str(i) + '_' + str(j) + '_' + str(k) + '.png'))
        plt.close(1)
        
        curvatureMatrixFile = open(os.path.join(outputPath, hyperparameters["videoName"] + "_curvatureData" + str(i) + '_' + str(j) + '_' + str(k) + '.txt'), 'wb')
        pickle.dump(curvature, curvatureMatrixFile)
        curvatureMatrixFile.close()
        
        # Creation of tail angle graph for bout k
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
        
        x0 = superStruct["wellPoissMouv"][i][j][k]["HeadX"][0]
        y0 = superStruct["wellPoissMouv"][i][j][k]["HeadY"][0]
        TailX_VideoReferential = superStruct["wellPoissMouv"][i][j][k]["TailX_VideoReferential"]
        TailY_VideoReferential = superStruct["wellPoissMouv"][i][j][k]["TailY_VideoReferential"]
        tailExtX = TailX_VideoReferential[0][len(TailX_VideoReferential[0])-1]
        tailExtY = TailY_VideoReferential[0][len(TailY_VideoReferential[0])-1]
        dist = int((math.sqrt((tailExtX-x0)**2 + (tailExtY-y0)**2))*1.3)
        
        outputName = os.path.join(outputPath, hyperparameters["videoName"] + "_bout" + str(i) + '_' + str(j) + '_' + str(k) + '.avi')
        outputVideoX = int(x+dist/2)-int(x-dist/2)
        outputVideoY = int(dist)
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
              frame = frame[int(y):int(y)+outputVideoY, 0:int(x-dist/2)+outputVideoX]
          
          frame2 = np.zeros((outputVideoX, outputVideoY, 3), np.uint8)
          frame2[0:len(frame), 0:len(frame[0]), :] = frame[0:len(frame), 0:len(frame[0]), :]
          frame = frame2
          
          out.write(frame)
          
        out.release()
