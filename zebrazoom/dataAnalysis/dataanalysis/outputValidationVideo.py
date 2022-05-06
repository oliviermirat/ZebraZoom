# from win32api import GetSystemMetrics
import cv2
import zebrazoom.videoFormatConversion.zzVideoReading as zzVideoReading
import json
import numpy as np
import sys
import os
from pathlib import Path

def outputValidationVideo(videoPath, folderName, configFilePath, numWell, numBout, zoom, start, boutEnd, out, length, analyzeAllWellsAtTheSameTime, ZZoutputLocation=''):
  
  s1  = videoPath
  s2  = folderName
  s3  = "/"
  s3b = "results_"
  s4  = folderName
  s5  = ".avi"
  s5b = ".txt"
  
  cur_dir_path = os.path.dirname(os.path.realpath(__file__))
  initialPath  = Path(cur_dir_path)
  initialPath  = os.path.join(initialPath.parent.parent, 'ZZoutput')
  initialPath  = os.path.join(initialPath, s1)
  if len(ZZoutputLocation):
    initialPath = ZZoutputLocation
  
  videoPath   = os.path.join(os.path.join(initialPath, s2),       s4 + s5)
  resultsPath = os.path.join(os.path.join(initialPath, s2), s3b + s4 + s5b)
  
  cap = zzVideoReading.VideoCapture(videoPath)
  
  nx    = int(cap.get(3))
  ny    = int(cap.get(4))
  max_l = int(cap.get(7))
  
  with open(resultsPath) as f:
    supstruct = json.load(f)
  
  # Getting the information about the head positions
  topLeftX = supstruct["wellPositions"][numWell]["topLeftX"]
  topLeftY = supstruct["wellPositions"][numWell]["topLeftY"]
  HeadX = [pos + topLeftX for pos in supstruct["wellPoissMouv"][numWell][0][numBout]['HeadX']]
  HeadY = [pos + topLeftY for pos in supstruct["wellPoissMouv"][numWell][0][numBout]['HeadY']]
  
  if not("firstFrame" in supstruct):
    supstruct["firstFrame"] = 1
  
  boutStart = supstruct["wellPoissMouv"][numWell][0][numBout]['BoutStart']
  boutEnd   = supstruct["wellPoissMouv"][numWell][0][numBout]['BoutEnd']
  
  l = boutStart - supstruct["firstFrame"]
  
  while (l < boutEnd):
    
    cap.set(1, l )
    ret, img = cap.read()
    
    if ret and l - boutStart + supstruct["firstFrame"] < len(HeadX) and (numWell != -1) and (zoom):
        
      xmin = int(HeadX[l - boutStart + supstruct["firstFrame"]] - length/2)
      xmax = int(HeadX[l - boutStart + supstruct["firstFrame"]] + length/2)
      ymin = int(HeadY[l - boutStart + supstruct["firstFrame"]] - length/2)
      ymax = int(HeadY[l - boutStart + supstruct["firstFrame"]] + length/2)
      
      if (xmin < 0):
        xmin = 0
      if (ymin < 0):
        ymin = 0
      if (xmax > nx-1):
        xmax = nx-1
      if (ymax > ny-1):
        ymax = ny-1
      
      blank = np.zeros((length, length, 3), np.uint8)
    
      blank[0:ymax-ymin, 0:xmax-xmin] = img[ymin:ymax, xmin:xmax]
      
      out.write(blank)
    
    l = l + 1
  
  blank = np.zeros((length, length, 3), np.uint8)
  for k in range(0, 10):
    out.write(blank)
  
  return out
