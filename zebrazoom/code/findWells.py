import h5py
import numpy as np
import cv2
import cvui
import math
import json
import sys
import os
from scipy import interpolate
import zebrazoom.code.popUpAlgoFollow as popUpAlgoFollow
from zebrazoom.code.adjustHyperparameters import initializeAdjustHyperparametersWindows, adjustHyperparameters
import tkinter as tk

def findRectangularWellsArea(frame, videoPath, hyperparameters):
  
  frame2 = frame.copy()
  
  root = tk.Tk()
  horizontal = root.winfo_screenwidth()
  vertical   = root.winfo_screenheight()
  getRealValueCoefX = 1
  getRealValueCoefY = 1
  if len(frame2[0]) > horizontal or len(frame2) > vertical:
    getRealValueCoefX = len(frame2[0]) / int(horizontal*0.8)
    getRealValueCoefY = len(frame2) / int(vertical*0.8)
    frame2 = cv2.resize(frame2, (int(horizontal*0.8), int(vertical*0.8)))
  root.destroy()
  
  WINDOW_NAME = "Click on the top left of one of the wells"
  cvui.init(WINDOW_NAME)
  cv2.moveWindow(WINDOW_NAME, 0,0)
  cvui.imshow(WINDOW_NAME, frame2)
  while not(cvui.mouse(cvui.CLICK)):
    cursor = cvui.mouse()
    if cv2.waitKey(20) == 27:
      break
  topLeft = [cursor.x, cursor.y]
  cv2.destroyAllWindows()
  
  WINDOW_NAME = "Click on the bottom right of the same well"
  cvui.init(WINDOW_NAME)
  cv2.moveWindow(WINDOW_NAME, 0,0)
  cvui.imshow(WINDOW_NAME, frame2)
  while not(cvui.mouse(cvui.CLICK)):
    cursor = cvui.mouse()
    if cv2.waitKey(20) == 27:
      break
  bottomRight = [cursor.x, cursor.y]
  cv2.destroyAllWindows()  
  
  rectangularWellsArea = int(abs((topLeft[0] - bottomRight[0]) * getRealValueCoefX) * abs((topLeft[1] - bottomRight[1]) * getRealValueCoefY))
  
  return rectangularWellsArea


def findRectangularWells(frame, videoPath, hyperparameters, rectangularWellsArea):
  
  findRectangleWellArea                    = rectangularWellsArea
  hyperparameters["findRectangleWellArea"] = rectangularWellsArea
  
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
  if rectangularWellsInvertBlackWhite:
    gray = cv2.dilate(gray, kernel, iterations = 1)
    gray = cv2.erode(gray,  kernel, iterations = 1)  
  else:
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
  
  if hyperparameters["adjustRectangularWellsDetect"]:
    
    gray   = cv2.cvtColor(gray, cv2.COLOR_GRAY2RGB)
    frame2 = frame.copy()
    rectangleTickness = 2
    lengthY = len(frame)
    lengthX = len(frame[0])
    if len(wellPositions):
      perm1 = np.random.permutation(len(wellPositions)) * int(255/len(wellPositions))
      perm2 = np.random.permutation(len(wellPositions)) * int(255/len(wellPositions))
      perm3 = np.random.permutation(len(wellPositions)) * int(255/len(wellPositions))
      for i in range(0, len(wellPositions)):
        if hyperparameters["wellsAreRectangles"]:
          topLeft     = (wellPositions[i]['topLeftX'], wellPositions[i]['topLeftY'])
          bottomRight = (wellPositions[i]['topLeftX'] + wellPositions[i]['lengthX'], wellPositions[i]['topLeftY'] + wellPositions[i]['lengthY'])
          color = (int(perm1[i]), int(perm2[i]), int(perm3[i]))
          frame2 = cv2.rectangle(frame2, topLeft, bottomRight, color, rectangleTickness)
    
    hyperparametersListNames = ["rectangleWellAreaImageThreshold", "rectangleWellErodeDilateKernelSize","findRectangleWellArea", "rectangularWellsInvertBlackWhite"]
    marginX = 30
    organizationTab = [\
    [470,  marginX + 5,  350,  0, 255,   "Adjust this threshold in order to get the inside of the wells as white as possible and the well's borders as black as possible."],
    [1,    marginX + 71, 350,  0, 75,    "Increase the value of this parameter if some sections of the well's borders are not black (if there are some 'holes' in the borders)."],
    [470,  marginX + 71, 350,  0, 50000, "Only change the value of this parameter as a last resort (and change it 'slowly' if you do). This parameter represents the mean area of the wells to detect."],
    [1,   marginX + 137, 350,  0, 1,     "Put this value to 1 if and only if the inside of your wells are darker than the well's borders in your video."],
    [470, marginX + 137,  -1, -1, -1,    "Click here once all wells are detected on the image on the right."]]
    WINDOW_NAME = "Rectangular Wells Detection: Adjust parameters until you get the right number of wells detected (on the right side)"
    frameToShow = np.concatenate((gray, frame2), axis=1)
    
    cv2.putText(frameToShow, "Wells detected:" + str(len(wellPositions)), (int(len(frameToShow[0])/2), 80), cv2.FONT_HERSHEY_SIMPLEX, 3, (255, 0, 255), 8)
  
    [l, hyperparameters, organizationTab] = adjustHyperparameters(0, hyperparameters, hyperparametersListNames, frameToShow, WINDOW_NAME, organizationTab)
    
    for param in hyperparametersListNames:
      hyperparameters[param] = int(hyperparameters[param])
    if hyperparameters["rectangularWellsInvertBlackWhite"] > 1:
      hyperparameters["rectangularWellsInvertBlackWhite"] = 1
    
    findRectangularWells(frame, videoPath, hyperparameters, hyperparameters["findRectangleWellArea"])
  
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
  if hyperparameters["invertBlackWhiteOnImages"]:
    frame = 255 - frame
  
  if hyperparameters["wellsAreRectangles"]:
    if hyperparameters["adjustRectangularWellsDetect"]:
      rectangularWellsArea = findRectangularWellsArea(frame, videoPath, hyperparameters)
      initializeAdjustHyperparametersWindows("Rectangular Wells Detection: Adjust parameters until you get the right number of wells detected (on the right side)")
    else:
      rectangularWellsArea = hyperparameters["findRectangleWellArea"]
      
    wellPositions = findRectangularWells(frame, videoPath, hyperparameters, rectangularWellsArea)
  else:
    wellPositions = findCircularWells(frame, videoPath, hyperparameters)
  
  cap.release()
  
  # Sorting wells
  
  nbWellsPerRows = hyperparameters["nbWellsPerRows"]
  nbRowsOfWells  = hyperparameters["nbRowsOfWells"]
  
  if len(wellPositions) >= nbWellsPerRows * nbRowsOfWells:
    
    for i in range(0, len(wellPositions)):
      for j in range(0, len(wellPositions)-1):
        if wellPositions[j]['topLeftY'] > wellPositions[j+1]['topLeftY']:
          aux                = wellPositions[j]
          wellPositions[j]   = wellPositions[j+1]
          wellPositions[j+1] = aux
    
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
  
  else:
    
    print("Not enough wells detected, please adjust your configuration file")
  
  # Creating validation image
  
  rectangleTickness = 2
  lengthY = len(frame)
  lengthX = len(frame[0])
  if len(wellPositions):
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
  frame = cv2.resize(frame, (int(lengthX/2), int(lengthY/2))) # ???
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
