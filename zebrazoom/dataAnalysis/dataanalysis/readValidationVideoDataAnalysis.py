# from win32api import GetSystemMetrics
import cv2
import zebrazoom.videoFormatConversion.zzVideoReading as zzVideoReading
import json
import numpy as np
import sys
import tkinter as tk

def readValidationVideoDataAnalysis(videoPath, folderName, configFilePath, numWell, zoom, start, boutEnd):

  print("configFilePath:",configFilePath)

  # horizontal = GetSystemMetrics(0)
  # vertical   = GetSystemMetrics(1)
  root = tk.Tk()
  horizontal = root.winfo_screenwidth()
  vertical   = root.winfo_screenheight()
  
  cv2.namedWindow("press q to quit")
  cv2.moveWindow("press q to quit", 0, 0)
  cv2.resizeWindow("press q to quit", horizontal, vertical)
  
  s1  = videoPath + "/ZZoutput/"
  s2  = folderName
  s3  = "/"
  s3b = "/results_"
  s4  = folderName
  s5  = ".avi"
  s5b = ".txt"
  
  videoPath = s1 + s2 + s3 + s4 + s5
  resultsPath = s1 + s2 + s3b + s4 + s5b
  
  cap = zzVideoReading.VideoCapture(videoPath)
  
  nx    = int(cap.get(3))
  ny    = int(cap.get(4))
  max_l = int(cap.get(7))
  
  print("resultsPath:",resultsPath)
  
  with open(resultsPath) as f:
    supstruct = json.load(f)
  
  infoWells = []
  
  HeadX = np.zeros(max_l)
  HeadY = np.zeros(max_l)
  
  if ((numWell != -1) and (zoom)):
    lastEnd = 0;
    lastXpos = supstruct["wellPoissMouv"][numWell][0][0]["HeadX"][0]
    lastYpos = supstruct["wellPoissMouv"][numWell][0][0]["HeadY"][0]
    for k in range(0,len(supstruct["wellPoissMouv"][numWell][0])):
      beg = supstruct["wellPoissMouv"][numWell][0][k]["BoutStart"]
      end = supstruct["wellPoissMouv"][numWell][0][k]["BoutEnd"]
      for l in range(lastEnd, beg):
        HeadX[l] = lastXpos
        HeadY[l] = lastYpos
      for l in range(beg, end):
        HeadX[l]  = supstruct["wellPoissMouv"][numWell][0][k]["HeadX"][l-beg]
        HeadY[l]  = supstruct["wellPoissMouv"][numWell][0][k]["HeadY"][l-beg]
      lastEnd = end
      lastXpos = supstruct["wellPoissMouv"][numWell][0][k]["HeadX"][end-1-beg]
      lastYpos = supstruct["wellPoissMouv"][numWell][0][k]["HeadY"][end-1-beg]
    for l in range(lastEnd, max_l):
      HeadX[l] = lastXpos
      HeadY[l] = lastYpos
  
  # /* Getting the info about well positions */
  analyzeAllWellsAtTheSameTime = 0
  if (analyzeAllWellsAtTheSameTime == 0):
    for i in range(0, len(supstruct["wellPositions"])):
      x = 0
      y = 0
      lengthX = 0
      lengthY = 0
      rectangleWellArea = 1
      if (rectangleWellArea == 0): # circular wells
        x = supstruct["wellPositions"][i]["topLeftX"]
        y = supstruct["wellPositions"][i]["topLeftY"]
        r = supstruct["wellPositions"][i]["diameter"]
        lengthX = 300 # wellOutputVideoDiameter;
        lengthY = 300 # wellOutputVideoDiameter;
      else:
        x = supstruct["wellPositions"][i]["topLeftX"]
        y = supstruct["wellPositions"][i]["topLeftY"]
        lengthX = supstruct["wellPositions"][i]["lengthX"]
        lengthY = supstruct["wellPositions"][i]["lengthY"]
      if (x < 0):
        x = 0
      if (y < 0):
        y = 0
      infoWells.append([x, y, lengthX, lengthY])
  else:
    infoWells.append([0, 0, nx, ny])

  x = 0
  y = 0
  lengthX = 0
  lengthY = 0
  if (numWell != -1):
    x = infoWells[numWell][0]
    y = infoWells[numWell][1]
    lengthX = infoWells[numWell][2]
    lengthY = infoWells[numWell][3]
  else:
    lengthX = nx
    lengthY = ny
  
  l = 0
  
  if not("firstFrame" in supstruct):
    supstruct["firstFrame"] = 1
    print("supstruct['firstFrame'] not found")
  
  if (start > 0):
      l = start - supstruct["firstFrame"] + 1
  
  xOriginal = x
  yOriginal = y
  
  imageWaitTime = 1
  
  while (l < boutEnd):
    
    cap.set(1, l )
    ret, img = cap.read()
    
    if ((numWell != -1) and (zoom)):
      
      length = 250
      xmin = HeadX[l] - length/2
      xmax = HeadX[l] + length/2
      ymin = HeadY[l] - length/2
      ymax = HeadY[l] + length/2
      
      if (xmin <= 0):
        xmin = 1
      if (ymin <= 0):
        ymin = 1
      if (xmax > nx-1):
        xmax = nx-1
      if (ymax > ny-1):
        ymax = ny-1
      
      if (xmin > nx-1):
        xmin = 1
      if (ymin > ny-1):
        ymin = 1
      if (xmax <= 0):
        xmax = nx-1
      if (ymax <= 0):
        ymax = ny-1
      
      x = xmin + xOriginal
      y = ymin + yOriginal
      lengthX = xmax - xmin
      lengthY = ymax - ymin
    
    if (numWell != -1):
      img = img[int(y):int(y+lengthY), int(x):int(x+lengthX)]
      progress = ( l / max_l ) * lengthX
      cv2.line(img, (0,int(lengthY-7)), (int(lengthX),int(lengthY-7)), (255,255,255), 10)
      cv2.circle(img, (int(progress), int(lengthY-6)), 5, (0, 0, 255), -1)
    else:
      progress = ( l / max_l ) * nx
      cv2.line(img,(0,ny-7),(nx,ny-7), (255,255,255), 10)
      cv2.circle(img, (int(progress), int(ny-6)), 5, (0, 0, 255), -1)
    
    font = cv2.FONT_HERSHEY_SIMPLEX
    cv2.putText(img,str(l + supstruct["firstFrame"] - 1),(int(lengthX-110), int(lengthY-30)),font,1,(0,255,0))
    
    vertical2   = vertical   - vertical   * 0.12
    horizontal2 = horizontal - horizontal * 0.015
    if ( (lengthX > horizontal2) or (lengthY > vertical2) ):
      sinkFactor = 1
      sinkFactorX = horizontal2 / lengthX
      sinkFactorY = vertical2   / lengthY
      if (sinkFactorX > sinkFactorY):
        sinkFactor = sinkFactorY
      else:
        sinkFactor = sinkFactorX
      newX = lengthX * sinkFactor
      newY = lengthY * sinkFactor
      
      imgResized2 = cv2.resize(img,(int(newX),int(newY)))
      
    else:
      imgResized2 = img
    
    cv2.imshow("press q to quit", imgResized2)
    r = cv2.waitKey(imageWaitTime)
    
    print(r)
    if (r == 54) or (r == 100):
      l = l + 1
      imageWaitTime = 0
    elif (r == 52) or (r == 97):
      l = l - 1
      imageWaitTime = 0
    elif (r == 56) or (r == 119):
      l = l + 20
      imageWaitTime = 0
    elif (r == 50) or (r == 115):
      l = l - 20
      imageWaitTime = 0
    elif (r == 102):
      l = l - 100
      imageWaitTime = 0
    elif (r == 103):
      l = l - 50
      imageWaitTime = 0
    elif (r == 104):
      l = l + 50
      imageWaitTime = 0
    elif (r == 106):
      l = l + 100
      imageWaitTime = 0
    elif (r == 113):
      l = max_l+500
      cv2.destroyWindow("press q to quit")
      root.destroy()
    else:
      l = l + 1
    
    if ((l > max_l-1) and (l != max_l+500)):
      l = max_l-1

    if (l < 0):
      l = 0
  
  cv2.destroyWindow("press q to quit")
