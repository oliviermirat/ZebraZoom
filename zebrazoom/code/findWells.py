import h5py
import numpy as np
import cv2
import math
import json
import sys
import os
from scipy import interpolate
import zebrazoom.code.popUpAlgoFollow as popUpAlgoFollow

def findRectangularWells(frame, videoPath, hyperparameters):
  
  findRectangleWellArea              = hyperparameters["findRectangleWellArea"]
  rectangleWellAreaImageThreshold    = hyperparameters["rectangleWellAreaImageThreshold"]
  rectangleWellErodeDilateKernelSize = hyperparameters["rectangleWellErodeDilateKernelSize"]
  rectangularWellsInvertBlackWhite   = hyperparameters["rectangularWellsInvertBlackWhite"]
  
  rectangularWellStretchPercentage     = hyperparameters["rectangularWellStretchPercentage"]
  rectangleWellAreaTolerancePercentage = hyperparameters["rectangleWellAreaTolerancePercentage"]
  nbPixelToleranceRectangleArea    = int(findRectangleWellArea * (rectangleWellAreaTolerancePercentage / 100))
  minRectangleArea                 = findRectangleWellArea - nbPixelToleranceRectangleArea
  maxRectangleArea                 = findRectangleWellArea + nbPixelToleranceRectangleArea
  
  wellPositions = []
  
  gray  = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
  
  if rectangularWellsInvertBlackWhite:
    gray  = 255 - gray

  retval, gray = cv2.threshold(gray, rectangleWellAreaImageThreshold, 255, cv2.THRESH_BINARY)

  kernel = np.ones((rectangleWellErodeDilateKernelSize, rectangleWellErodeDilateKernelSize), np.uint8)
  gray = cv2.erode(gray,  kernel, iterations = 1)
  gray = cv2.dilate(gray, kernel, iterations = 1)

  contours, hierarchy = cv2.findContours(gray, cv2.RETR_LIST, cv2.CHAIN_APPROX_SIMPLE)
  for contour in contours:
    print("Possible Well Area:", cv2.contourArea(contour))
    if cv2.contourArea(contour) > minRectangleArea and cv2.contourArea(contour) < maxRectangleArea:
      if True:
        topLeftCoord          = [0, 0]
        bottomRightCoord      = [0, 0]
        topLeftDistToZero     = float("inf")
        bottomRightDistToZero = -1
        for point in contour:
          if math.sqrt(point[0][0]**2 + point[0][1]**2) < topLeftDistToZero:
            topLeftDistToZero = math.sqrt(point[0][0]**2 + point[0][1]**2)
            topLeftCoord = point[0]
          if math.sqrt(point[0][0]**2 + point[0][1]**2) > bottomRightDistToZero:
            bottomRightDistToZero = math.sqrt(point[0][0]**2 + point[0][1]**2)
            bottomRightCoord = point[0]
        stretchDist = int(math.sqrt((bottomRightCoord[0] - topLeftCoord[0]) * (bottomRightCoord[1] - topLeftCoord[1])) * (rectangularWellStretchPercentage / 100))
        well = {'topLeftX': int(topLeftCoord[0] - stretchDist), 'topLeftY': int(topLeftCoord[1] - stretchDist), 'lengthX': int(bottomRightCoord[0] - topLeftCoord[0] + 2 * stretchDist), 'lengthY': int(bottomRightCoord[1] - topLeftCoord[1] + 2 * stretchDist)}
      else:
        top    = float("inf")
        bottom = -1
        left   = float("inf")
        right  = -1
        for point in contour:
          if point[0][1] < top:
            top    = point[0][1]
          if point[0][1] > bottom:
            bottom = point[0][1]
          if point[0][0] < left:
            left   = point[0][0]
          if point[0][0] > right:
            right  = point[0][0]
        well = {'topLeftX' : left, 'topLeftY' : top, 'lengthX' : right - left, 'lengthY': bottom - top}
      
      wellPositions.append(well)
  
  return wellPositions


def findCircularWells(frame, videoPath, hyperparameters):

  minWellDistanceForWellDetection = hyperparameters["minWellDistanceForWellDetection"]
  wellOutputVideoDiameter         = hyperparameters["wellOutputVideoDiameter"]

  gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)

  circles2 = cv2.HoughCircles(gray, cv2.HOUGH_GRADIENT, 1, minWellDistanceForWellDetection)
  if hyperparameters["debugFindWells"] and (hyperparameters["exitAfterBackgroundExtraction"] == 0):
    print(circles2)
    cv2.imshow('Frame', gray)
    cv2.waitKey(0)
    cv2.destroyWindow('Frame')
  
  circles = np.uint16(np.around(circles2))

  wellPositions = []

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
    wellPositions.append(well)
  
  return wellPositions


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
  
  # Circular or rectangular wells
  
  cap = cv2.VideoCapture(videoPath)
  if (cap.isOpened()== False): 
    print("Error opening video stream or file")
  ret, frame = cap.read()
  
  if hyperparameters["wellsAreRectangles"]:
    wellPositions = findRectangularWells(frame, videoPath, hyperparameters)
  else:
    wellPositions = findCircularWells(frame, videoPath, hyperparameters)
  
  cap.release()
  
  # Sorting wells
  
  for i in range(0, len(wellPositions)):
    for j in range(0, len(wellPositions)-1):
      if wellPositions[j]['topLeftY'] > wellPositions[j+1]['topLeftY']:
        aux                = wellPositions[j]
        wellPositions[j]   = wellPositions[j+1]
        wellPositions[j+1] = aux
  
  nbWellsPerRows = hyperparameters["nbWellsPerRows"]
  nbRowsOfWells  = hyperparameters["nbRowsOfWells"]
  
  if (nbRowsOfWells == 0):
    for i in range(0, len(wellPositions)):
      for j in range(0, len(wellPositions)-1):
        if wellPositions[j]['topLeftX'] > wellPositions[j+1]['topLeftX']:
          aux                = wellPositions[j]
          wellPositions[j]   = wellPositions[j+1]
          wellPositions[j+1] = aux
  else:
    for k in range(0, nbRowsOfWells):
      for i in range(nbWellsPerRows*k, nbWellsPerRows*(k+1)):
        for j in range(nbWellsPerRows*k, nbWellsPerRows*(k+1)-1):
          if wellPositions[j]['topLeftX'] > wellPositions[j+1]['topLeftX']:
            aux                = wellPositions[j]
            wellPositions[j]   = wellPositions[j+1]
            wellPositions[j+1] = aux   
  
  # Creating validation image
  
  rectangleTickness = 2
  lengthY = len(frame)
  lengthX = len(frame[0])
  perm1 = np.random.permutation(len(wellPositions)) * int(255/len(wellPositions))
  perm2 = np.random.permutation(len(wellPositions)) * int(255/len(wellPositions))
  perm3 = np.random.permutation(len(wellPositions)) * int(255/len(wellPositions))
  for i in range(0, len(wellPositions)):
    if hyperparameters["wellsAreRectangles"]:
      topLeft     = (wellPositions[i]['topLeftX'], wellPositions[i]['topLeftY'])
      bottomRight = (wellPositions[i]['topLeftX'] + wellPositions[i]['lengthX'], wellPositions[i]['topLeftY'] + wellPositions[i]['lengthY'])
      color = (int(perm1[i]), int(perm2[i]), int(perm3[i]))
      frame = cv2.rectangle(frame, topLeft, bottomRight, color, rectangleTickness)
    else:
      cv2.circle(frame, (int(wellPositions[i]['topLeftX'] + wellPositions[i]['lengthX'] / 2), int(wellPositions[i]['topLeftY'] + wellPositions[i]['lengthY'] / 2)), 170, (0,0,255), 2)
    cv2.putText(frame, str(i), (int(wellPositions[i]['topLeftX'] + wellPositions[i]['lengthX'] / 2), int(wellPositions[i]['topLeftY'] + wellPositions[i]['lengthY'] / 2)), cv2.FONT_HERSHEY_SIMPLEX, 4,(255,255,255),2,cv2.LINE_AA)
  frame = cv2.resize(frame, (int(lengthX/2), int(lengthY/2)))
  cv2.imwrite(os.path.join(os.path.join(hyperparameters["outputFolder"], hyperparameters["videoName"]), "repartition.jpg"), frame )
  if hyperparameters["debugFindWells"]:
    cv2.imshow('Wells Detection', frame)
    if hyperparameters["exitAfterBackgroundExtraction"]:
      cv2.waitKey(3000)
    else:
      cv2.waitKey(0)
    cv2.destroyWindow('Wells Detection')
  
  print("Wells found")
  if hyperparameters["popUpAlgoFollow"]:
    popUpAlgoFollow.prepend("Wells found")

  return wellPositions
