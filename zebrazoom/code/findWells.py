import h5py
import numpy as np
import cv2
import math
import json
import sys
from scipy import interpolate
import zebrazoom.code.popUpAlgoFollow as popUpAlgoFollow

def findRectangularWells(videoPath, hyperparameters):
  
  nbWells                  = 12
  binaryThres              = 85
  wellDetectImgFirstErode  = 0
  wellDetectImgFirstDilate = 0
  rectangleWellArea        = 300000
  rectangleWellAreaPercentMarginAccepted = 0.2
  orderRectangularWellsHorizontally      = 1
  
  cap = cv2.VideoCapture(videoPath)
  nx  = int(cap.get(3))
  ny  = int(cap.get(4))
  if (cap.isOpened()== False): 
    print("Error opening video stream or file")
  ret, frame = cap.read()
  copie = frame.copy()
  copie = cv2.cvtColor(copie, cv2.COLOR_BGR2GRAY)
  
  ret, copie = cv2.threshold(copie, binaryThres, 255, 0)
  
  if (wellDetectImgFirstErode != 0) and (wellDetectImgFirstDilate != 0):
    kernel = np.ones((3,3),np.uint8)
    copie = cvErode(copie,  kernel, iterations = wellDetectImgFirstErode)
    copie = cvDilate(copie, kernel, iterations = wellDetectImgFirstDilate)
  
  im2, contours, hierarchy = cv2.findContours(copie, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
  
  j = 0
  rectangleWellAreaDelta = rectangleWellArea * rectangleWellAreaPercentMarginAccepted
  rectangleWellAreaMin   = rectangleWellArea - rectangleWellAreaDelta
  rectangleWellAreaMax   = rectangleWellArea + rectangleWellAreaDelta
  
  wellXtab    = [0] * nbWells
  wellYtab    = [0] * nbWells
  wellLenXtab = [0] * nbWells
  wellLenYtab = [0] * nbWells
  
  for contour in contours:
    if (cv2.contourArea(contour)>rectangleWellAreaMin) and (cv2.contourArea(contour)<rectangleWellAreaMax):
      minY = ny
      maxY = 0
      minX = nx
      maxX = 0
      for i in range(0, len(contour)):
        Pt = contour[i]
        x = Pt[0][0]
        y = Pt[0][1]
        if (y < minY):
          minY = y
        if (y > maxY):
          maxY = y
        if (x < minX):
          minX = x
        if (x > maxX):
          maxX = x
      
      wellX = minX - 5
      wellY = minY - 5
      wellLenX = maxX - minX + 10
      wellLenY = maxY - minY + 10
      if wellX <= 0:
        wellX = 1
      if wellY <= 0:
        wellY = 1
      if wellX + wellLenX > nx:
        wellLenX = nx - wellX
      if wellY + wellLenY > ny:
        wellLenY = ny - wellY
      
      wellXtab[j]    = wellX
      wellYtab[j]    = wellY
      wellLenXtab[j] = wellLenX
      wellLenYtab[j] = wellLenY
      
      j = j + 1
  
  if (orderRectangularWellsHorizontally):
    aux = 0
    # Ordering wells on the x axis
    for i in range(0, nbWells):
      for j in range(0, nbWells-1):
        if (wellXtab[j] > wellXtab[j+1]):
          aux = wellXtab[j]
          wellXtab[j]   = wellXtab[j+1]
          wellXtab[j+1] = aux
        
          aux = wellYtab[j]
          wellYtab[j]   = wellYtab[j+1]
          wellYtab[j+1] = aux
          
          aux = wellLenXtab[j]
          wellLenXtab[j]   = wellLenXtab[j+1]
          wellLenXtab[j+1] = aux
          
          aux = wellLenYtab[j]
          wellLenYtab[j]   = wellLenYtab[j+1]
          wellLenYtab[j+1] = aux
  
  cap.release()
  
  l = []
  for i in range(0, nbWells):
    l.append({ 'topLeftX' : int(wellXtab[i]) , 'topLeftY' : int(wellYtab[i]) , 'lengthX' : int(wellLenXtab[i]) , 'lengthY': int(wellLenYtab[i])})
  
  for i in range(0, nbWells):
    lengthY = len(frame)
    lengthX = len(frame[0])
    for i in range(0, nbWells):
      cv2.putText(frame,str(i),(int(l[i]['topLeftX'] + 10), int(l[i]['topLeftY'] + l[i]['lengthY']/2)), cv2.FONT_HERSHEY_SIMPLEX, 4,(255,255,255),2,cv2.LINE_AA)
    cv2.imwrite(hyperparameters["outputFolder"] + hyperparameters["videoName"] + "/repartition.jpg", frame)
  
  return l

  
def findWells(videoPath, hyperparameters):

  if hyperparameters["noWellDetection"]:
    
    cap = cv2.VideoCapture(videoPath)
    if (cap.isOpened()== False): 
      print("Error opening video stream or file")
    frame_width  = int(cap.get(3))
    frame_height = int(cap.get(4))
    l = []
    well = { 'topLeftX' : 0 , 'topLeftY' : 0 , 'lengthX' : frame_width , 'lengthY': frame_height }
    l.append(well)
    return l
    
  if len(hyperparameters["oneWellManuallyChosenTopLeft"]):
    l = []
    topLeft_X = hyperparameters["oneWellManuallyChosenTopLeft"][0]
    topLeft_Y = hyperparameters["oneWellManuallyChosenTopLeft"][1]
    bottomRight_X = hyperparameters["oneWellManuallyChosenBottomRight"][0]
    bottomRight_Y = hyperparameters["oneWellManuallyChosenBottomRight"][1]
    frame_width  = bottomRight_X - topLeft_X
    frame_height = bottomRight_Y - topLeft_Y
    well = { 'topLeftX' : topLeft_X , 'topLeftY' : topLeft_Y , 'lengthX' : frame_width , 'lengthY': frame_height }
    l.append(well)
    return l
    
  if hyperparameters["wellsAreRectangles"]:
  
    wellPositions = findRectangularWells(videoPath, hyperparameters)
    return wellPositions
  
  else:

    minWellDistanceForWellDetection = hyperparameters["minWellDistanceForWellDetection"]
    wellOutputVideoDiameter         = hyperparameters["wellOutputVideoDiameter"]
    debugFindWells                  = hyperparameters["debugFindWells"]

    cap = cv2.VideoCapture(videoPath)
    
    # print(cap.get(cv2.CAP_PROP_FRAME_COUNT))

    if (cap.isOpened()== False): 
      print("Error opening video stream or file")

    frame_width  = int(cap.get(3))
    frame_height = int(cap.get(4))

    ret, frame = cap.read()
    gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

    circles2 = cv2.HoughCircles(gray, cv2.HOUGH_GRADIENT, 1, minWellDistanceForWellDetection)
    if debugFindWells and (hyperparameters["exitAfterBackgroundExtraction"] == 0):
      print(circles2)
      cv2.imshow('Frame', gray)
      cv2.waitKey(0)
      cv2.destroyWindow('Frame')
    
    circles = np.uint16(np.around(circles2))

    l = []

    for circle in circles[0,:]:
      xtop = int(circle[0] - (wellOutputVideoDiameter/2))
      ytop = int(circle[1] - (wellOutputVideoDiameter/2))
      if xtop < 0:
        xtop = 0
      if ytop < 0:
        ytop = 0
      nx   = wellOutputVideoDiameter
      ny   = wellOutputVideoDiameter
      well = { 'topLeftX' : xtop , 'topLeftY' : ytop , 'lengthX' : nx , 'lengthY': ny }
      l.append(well)
    
    nbWells = min(len(circles[0,:]), hyperparameters["nbWells"])
    
    for i in range(0, nbWells):
      for j in range(0, nbWells-1):
        if l[j]['topLeftY'] > l[j+1]['topLeftY']:
          aux    = l[j]
          l[j]   = l[j+1]
          l[j+1] = aux
    
    nbWellsPerRows = hyperparameters["nbWellsPerRows"]
    nbRowsOfWells  = hyperparameters["nbRowsOfWells"]
    
    if (nbRowsOfWells == 0):
      for i in range(0, nbWells):
        for j in range(0, nbWells-1):
          if l[j]['topLeftX'] > l[j+1]['topLeftX']:
            aux    = l[j]
            l[j]   = l[j+1]
            l[j+1] = aux
    else:
      for k in range(0, nbRowsOfWells):
        for i in range(nbWellsPerRows*k, nbWellsPerRows*(k+1)):
          for j in range(nbWellsPerRows*k, nbWellsPerRows*(k+1)-1):
            if l[j]['topLeftX'] > l[j+1]['topLeftX']:
              aux    = l[j]
              l[j]   = l[j+1]
              l[j+1] = aux   
    
    cap.release()
    
    lengthY = len(frame);
    lengthX = len(frame[0]);
    for i in range(0, nbWells):
      cv2.circle(frame,(l[i]['topLeftX']+200,l[i]['topLeftY']+200), 170, (0,0,255), 2)
      cv2.putText(frame,str(i),(l[i]['topLeftX']+200,l[i]['topLeftY']+200), cv2.FONT_HERSHEY_SIMPLEX, 4,(255,255,255),2,cv2.LINE_AA)
    frame = cv2.resize(frame,(int(lengthX/2),int(lengthY/2)))
    cv2.imwrite( hyperparameters["outputFolder"] + hyperparameters["videoName"] + "/repartition.jpg", frame );
    if debugFindWells:
      cv2.imshow('Wells Detection', frame)
      if hyperparameters["exitAfterBackgroundExtraction"]:
        cv2.waitKey(3000)
      else:
        cv2.waitKey(0)
      cv2.destroyWindow('Wells Detection')
    
    print("Wells found")
    if hyperparameters["popUpAlgoFollow"]:
      popUpAlgoFollow.prepend("Wells found")

    return l
