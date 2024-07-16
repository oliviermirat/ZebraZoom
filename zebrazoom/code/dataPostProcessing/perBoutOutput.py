import cv2
import zebrazoom.videoFormatConversion.zzVideoReading as zzVideoReading
from zebrazoom.code.extractParameters import calculateAngle
from zebrazoom.code.extractParameters import calculateTailAngle
import h5py
import os
import shutil
import math
import matplotlib.pyplot as plt
import numpy as np
import time
import pandas as pd
import pickle
from scipy import ndimage


def calculateCurvature(TailX_VideoReferential, TailY_VideoReferential, hyperparameters):
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
    for ii in range(0, l):#-1):
      num = xdiff[ii] * ydiff2[ii] - ydiff[ii] * xdiff2[ii]
      den = (xdiff[ii]**2 + ydiff[ii]**2)**1.5
      curv[ii] = num / den

    curv = curv[hyperparameters["nbPointsToIgnoreAtCurvatureBeginning"]: l-hyperparameters["nbPointsToIgnoreAtCurvatureEnd"]]
    curvature.append(curv)
  return curvature


def perBoutOutput(superStruct, hyperparameters, videoNameWithTimestamp):
  
  # Creation of the sub-folder "perBoutOutput"
  if hyperparameters["saveAllDataEvenIfNotInBouts"] or hyperparameters["saveCurvaturePlots"] or hyperparameters["saveTailAngleGraph"] or hyperparameters["saveSubVideo"] or hyperparameters["saveCurvatureData"]:
    outputPath = os.path.join(hyperparameters["outputFolder"], videoNameWithTimestamp, "perBoutOutput")
    if not os.path.exists(outputPath):
      os.makedirs(outputPath)
      
  # opening the video previously created in createValidationVideo as an input video stream
  if hyperparameters['storeH5']:
    videoPath = os.path.join(hyperparameters["outputFolder"], f'{videoNameWithTimestamp}.avi')
  else:
    videoPath = os.path.join(hyperparameters["outputFolder"], hyperparameters["videoName"], f'{videoNameWithTimestamp}.avi')
  cap = zzVideoReading.VideoCapture(videoPath, hyperparameters)
  
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
  
  # alternativeCurvatureCalculation: Going through each well, each fish and each bout
  if hyperparameters["alternativeCurvatureCalculation"]:
    for i in range(0, len(superStruct["wellPoissMouv"])):
      for j in range(0, len(superStruct["wellPoissMouv"][i])):
        for k in range(0, len(superStruct["wellPoissMouv"][i][j])):
          
          # Creation of the curvature graph for bout k
          TailX_VideoReferential = superStruct["wellPoissMouv"][i][j][k]["TailX_VideoReferential"]
          TailY_VideoReferential = superStruct["wellPoissMouv"][i][j][k]["TailY_VideoReferential"]
          
          alternativeCurvatureCalculation = []
          for l in range(0, len(TailX_VideoReferential)):
            tailX = TailX_VideoReferential[l]
            tailY = TailY_VideoReferential[l]

            l = len(tailX)
            alternativeCurvatureCalculationForFrame = np.zeros(l-2)
            av = 0
            for ii in range(1, l-1):
              angleBef = calculateAngle(np.array([tailX[ii-1], tailY[ii-1]]), np.array([tailX[ii],   tailY[ii]]))
              angleAft = calculateAngle(np.array([tailX[ii],   tailY[ii]]),   np.array([tailX[ii+1], tailY[ii+1]]))
              alternativeCurvatureCalculationForFrame[ii-1] = calculateTailAngle(angleBef, angleAft)
            alternativeCurvatureCalculation.append(alternativeCurvatureCalculationForFrame)
          
          rolling_window = hyperparameters["curvatureMedianFilterSmoothingWindow"]
          if rolling_window:
            alternativeCurvatureCalculation = ndimage.median_filter(alternativeCurvatureCalculation, size=rolling_window) # 2d median filter
          else:
            alternativeCurvatureCalculation = np.array(alternativeCurvatureCalculation)
          
          alternativeCurvatureCalculation = np.flip(np.transpose(alternativeCurvatureCalculation), 0)
          
          superStruct["wellPoissMouv"][i][j][k]["alternativeCurvatureCalculation"] = alternativeCurvatureCalculation.tolist()
          
          if hyperparameters["saveCurvaturePlots"]:
            fig = plt.figure(1)
            if hyperparameters["maxCurvatureValues"] == 0:
              maxx = max([max(abs(np.array(t))) for t in alternativeCurvatureCalculation])
            else:
              maxx = hyperparameters["maxCurvatureValues"]
            if hyperparameters["curvatureXaxisNbFrames"] != 0:
              if len(alternativeCurvatureCalculation[0]) < hyperparameters["curvatureXaxisNbFrames"]:
                alternativeCurvatureCalculation2 = np.pad(alternativeCurvatureCalculation, ((0, 0), (0, hyperparameters["curvatureXaxisNbFrames"] - len(alternativeCurvatureCalculation[0]))), mode='constant')
              elif len(alternativeCurvatureCalculation[0]) > hyperparameters["curvatureXaxisNbFrames"]:
                alternativeCurvatureCalculation2 = alternativeCurvatureCalculation[:, 0:hyperparameters["curvatureXaxisNbFrames"]]
              else:
                alternativeCurvatureCalculation2 = alternativeCurvatureCalculation
            else:
              alternativeCurvatureCalculation2 = alternativeCurvatureCalculation
            plt.pcolor(alternativeCurvatureCalculation2, vmin=-maxx, vmax=maxx, cmap=hyperparameters["colorMapCurvature"])
            ax = fig.axes
            ax[0].set_ylabel('Rostral to Caudal')
            if hyperparameters["videoFPS"]:
              ax[0].set_xlabel('Second')
              plt.xticks([i for i in range(0, len(alternativeCurvatureCalculation2[0]), int(len(alternativeCurvatureCalculation2[0])/10))], [int(100*(i/hyperparameters["videoFPS"]))/100 for i in range(0, len(alternativeCurvatureCalculation2[0]), int(len(alternativeCurvatureCalculation2[0])/10))])
            else:
              ax[0].set_xlabel('Frame number')
            
            if hyperparameters["videoPixelSize"] and int(len(alternativeCurvatureCalculation2)/10):
              ax[0].set_ylabel('Rostral to Caudal (in mm)')
              plt.yticks([i for i in range(0, len(alternativeCurvatureCalculation2), int(len(alternativeCurvatureCalculation2)/10))], [int(100*( hyperparameters["videoPixelSize"] * tailLenghtInPixels * (i/len(alternativeCurvatureCalculation2)) ))/100 for i in range(0, len(alternativeCurvatureCalculation2), int(len(alternativeCurvatureCalculation2)/10))])
            else:
              ax[0].set_ylabel('Rostral to Caudal (arbitrary units)')
            
            plt.colorbar()
            plt.savefig(os.path.join(outputPath, hyperparameters["videoName"] + "_alternativeCurvatureCalculation_bout" + str(i) + '_' + str(j) + '_' + str(k) + '.png'))
            plt.close(1)
  
  
  # Curvature calculation: Going through each well, each fish and each bout
  for i in range(0, len(superStruct["wellPoissMouv"])):
    for j in range(0, len(superStruct["wellPoissMouv"][i])):
      if not superStruct["wellPoissMouv"][i][j]:  # no bouts, nothing to calculate
        continue
      curvatures = {}
      if hyperparameters["saveAllDataEvenIfNotInBouts"]:
        fname = os.path.join(hyperparameters["outputFolder"], videoNameWithTimestamp, f'allData_{hyperparameters["videoName"]}_wellNumber{i}_animal{j}.csv')
        startLines = []
        with open(fname) as f:
          line = f.readline()
          while ',' not in line:
            startLines.append(line)
            line = f.readline()
        df = pd.read_csv(fname, skiprows=len(startLines))
        df = df.loc[:, ~df.columns.str.contains('^Unnamed')]
      for k in range(0, len(superStruct["wellPoissMouv"][i][j])):
        
        # Creation of the curvature graph for bout k
        TailX_VideoReferential = superStruct["wellPoissMouv"][i][j][k]["TailX_VideoReferential"]
        TailY_VideoReferential = superStruct["wellPoissMouv"][i][j][k]["TailY_VideoReferential"]

        if hyperparameters["videoPixelSize"]:
          tailLenghtInPixels = np.sum([math.sqrt((TailX_VideoReferential[0][l] - TailX_VideoReferential[0][l+1])**2 + (TailY_VideoReferential[0][l] - TailY_VideoReferential[0][l+1])**2) for l in range(0, len(TailX_VideoReferential[0]) - 1)])

        curvature = calculateCurvature(TailX_VideoReferential, TailY_VideoReferential, hyperparameters)
        originalCurvature = np.flip(np.transpose(curvature), 0)

        if hyperparameters["saveAllDataEvenIfNotInBouts"]:
          bStart = superStruct["wellPoissMouv"][i][j][k]["BoutStart"]
          bEnd = superStruct["wellPoissMouv"][i][j][k]["BoutEnd"]
          curvatures[(bStart - firstFrame, bEnd + 1 - firstFrame)] = originalCurvature.tolist()

        rolling_window = hyperparameters["curvatureMedianFilterSmoothingWindow"]
        if rolling_window:
          curvature = ndimage.median_filter(curvature, size=rolling_window) # 2d median filter
          curvature = np.flip(np.transpose(curvature), 0)
        else:
          curvature = originalCurvature
        
        superStruct["wellPoissMouv"][i][j][k]["curvature"] = curvature.tolist()

        if hyperparameters["saveCurvaturePlots"]:
          fig = plt.figure(1)
          if hyperparameters["maxCurvatureValues"] == 0:
            maxx = max([max(abs(np.array(t))) for t in curvature])
          else:
            maxx = hyperparameters["maxCurvatureValues"]          
          if hyperparameters["curvatureXaxisNbFrames"] != 0:
            if len(curvature[0]) < hyperparameters["curvatureXaxisNbFrames"]:
              curvature2 = np.pad(curvature, ((0, 0), (0, hyperparameters["curvatureXaxisNbFrames"] - len(curvature[0]))), mode='constant')
            elif len(curvature[0]) > hyperparameters["curvatureXaxisNbFrames"]:
              curvature2 = curvature[:, 0:hyperparameters["curvatureXaxisNbFrames"]]
            else:
              curvature2 = curvature
          else:
            curvature2 = curvature
          plt.pcolor(curvature2, vmin=-maxx, vmax=maxx, cmap=hyperparameters["colorMapCurvature"])
          ax = fig.axes
          
          if hyperparameters["videoFPS"] and int(len(curvature2[0])/10):
            ax[0].set_xlabel('Second')
            plt.xticks([i for i in range(0, len(curvature2[0]), int(len(curvature2[0])/10))], [int(100*(i/hyperparameters["videoFPS"]))/100 for i in range(0, len(curvature2[0]), int(len(curvature2[0])/10))])
          else:
            ax[0].set_xlabel('Frame number')
            
          if hyperparameters["videoPixelSize"] and int(len(curvature2)/10):
            ax[0].set_ylabel('Rostral to Caudal (in mm)')
            plt.yticks([i for i in range(0, len(curvature2), int(len(curvature2)/10))], [int(100*( hyperparameters["videoPixelSize"] * tailLenghtInPixels * (i/len(curvature2)) ))/100 for i in range(0, len(curvature2), int(len(curvature2)/10))])
          else:
            ax[0].set_ylabel('Rostral to Caudal (arbitrary unit)')
          
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

      if hyperparameters["saveAllDataEvenIfNotInBouts"]:
        curvatureCount = max(map(len, curvatures.values())) if curvatures else 0
        curvatureData = [[float('nan')] * nbFrames for _ in range(curvatureCount)]
        for (start, end), values in curvatures.items():
          for data, vals in zip(curvatureData, values):
            data[start:end] = vals
        for idx, data in enumerate(curvatureData):
          df[f'curvature{idx + 1}'] = data
        with open(fname, 'w+', newline='') as f:
          f.write(''.join(startLines))
          df.convert_dtypes().to_csv(f)
      if hyperparameters['storeH5'] and superStruct["wellPoissMouv"][i][j]:
        with h5py.File(hyperparameters['H5filename'], 'a') as results:
          dataGroup = results.require_group(f"dataForWell{i}/dataForAnimal{j}/dataPerFrame")
          curvature = np.empty((lastFrame - firstFrame + 1, hyperparameters['nbTailPoints'] - 2), dtype=float)
          TailX_VideoReferential = np.column_stack([dataGroup['HeadPos']['X']] + [dataGroup['TailPosX'][col] for col in dataGroup['TailPosX'].attrs['columns']])
          TailY_VideoReferential = np.column_stack([dataGroup['HeadPos']['Y']] + [dataGroup['TailPosY'][col] for col in dataGroup['TailPosY'].attrs['columns']])
          curvature = list(np.flip(np.transpose(calculateCurvature(TailX_VideoReferential, TailY_VideoReferential, hyperparameters)), 0))
          data = np.empty(len(curvature[0]), dtype=[(f'Pos{idx}', float) for idx in range(1, len(curvature) + 1)])
          for idx, curvatureData in enumerate(curvature):
            data[f'Pos{idx + 1}'] = curvatureData
          dataset = dataGroup.create_dataset('curvature', data=data)
          dataset.attrs['columns'] = data.dtype.names

  return superStruct
