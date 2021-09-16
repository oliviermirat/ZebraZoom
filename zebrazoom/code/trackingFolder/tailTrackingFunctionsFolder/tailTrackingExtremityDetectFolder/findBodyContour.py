import h5py
import numpy as np
import cv2
import math
import json
import sys
from scipy import interpolate
from zebrazoom.code.getImage.getForegroundImage import getForegroundImage
from zebrazoom.code.getImage.headEmbededFrame import headEmbededFrame
from zebrazoom.code.deepLearningFunctions.labellingFunctions import drawWhitePointsOnInitialImages, saveImagesAndData
from scipy.interpolate import UnivariateSpline
from numpy import linspace

def findBodyContour(headPosition, hyperparameters, thresh1, initialCurFrame, back, wellNumber=-1, frameNumber=-1):

  if hyperparameters["saveBodyMask"] and hyperparameters["bodyMask_addWhitePoints"]:
    [img, thresh1] = drawWhitePointsOnInitialImages(initialCurFrame, back, hyperparameters)
  
  thresh1[:,0] = 255
  thresh1[0,:] = 255
  thresh1[:, len(thresh1[0])-1] = 255
  thresh1[len(thresh1)-1, :]    = 255
  
  x = headPosition[0]
  y = headPosition[1]
  cx = 0
  cy = 0
  takeTheHeadClosestToTheCenter = 1
  bodyContour = 0

  if hyperparameters["findContourPrecision"] == "CHAIN_APPROX_SIMPLE":
    contourPrecision = cv2.CHAIN_APPROX_SIMPLE
  else: # hyperparameters["findContourPrecision"] == "CHAIN_APPROX_NONE"
    contourPrecision = cv2.CHAIN_APPROX_NONE
  
  if hyperparameters["recalculateForegroundImageBasedOnBodyArea"]:
    
    minPixel2nbBlackPixels = {}
    countTries = 0
    nbBlackPixels = 0
    nbBlackPixelsMax = int(hyperparameters["adjustMinPixelDiffForBackExtract_nbBlackPixelsMax"] / hyperparameters["nbAnimalsPerWell"])
    minPixelDiffForBackExtract = int(hyperparameters["minPixelDiffForBackExtract"])
    if "minPixelDiffForBackExtractBody" in hyperparameters:
      minPixelDiffForBackExtract = hyperparameters["minPixelDiffForBackExtractBody"]
    
    previousNbBlackPixels = []
    while (minPixelDiffForBackExtract > 0) and (countTries < 30) and not(minPixelDiffForBackExtract in minPixel2nbBlackPixels):
      curFrame = initialCurFrame.copy()
      putToWhite = ( curFrame.astype('int32') >= (back.astype('int32') - minPixelDiffForBackExtract) )
      curFrame[putToWhite] = 255
      ret, thresh1_b = cv2.threshold(curFrame, hyperparameters["thresholdForBlobImg"], 255, cv2.THRESH_BINARY)
      thresh1_b = 255 - thresh1_b
      bodyContour = 0
      contours, hierarchy = cv2.findContours(thresh1_b, cv2.RETR_TREE, contourPrecision)
      for contour in contours:
        dist = cv2.pointPolygonTest(contour, (x, y), True)
        if dist >= 0:
          M = cv2.moments(contour)
          if M['m00']:
            cx = int(M['m10']/M['m00'])
            cy = int(M['m01']/M['m00'])
            bodyContour = contour
          else:
            cx = 0
            cy = 0
      if not(type(bodyContour) == int):
        nbBlackPixels = cv2.contourArea(bodyContour)
      else:
        nbBlackPixels = -100000000
    
      minPixel2nbBlackPixels[minPixelDiffForBackExtract] = nbBlackPixels
      if nbBlackPixels > nbBlackPixelsMax:
        minPixelDiffForBackExtract = minPixelDiffForBackExtract + 1
      if nbBlackPixels <= nbBlackPixelsMax:
        minPixelDiffForBackExtract = minPixelDiffForBackExtract - 1
      
      countTries = countTries + 1
      
      previousNbBlackPixels.append(nbBlackPixels)
      if len(previousNbBlackPixels) >= 3:
        lastThree = previousNbBlackPixels[len(previousNbBlackPixels)-3: len(previousNbBlackPixels)]
        if lastThree.count(lastThree[0]) == len(lastThree):
          countTries = 1000000
    
    best_minPixelDiffForBackExtract = 0
    minDist = 10000000000000
    for minPixelDiffForBackExtract in minPixel2nbBlackPixels:
      nbBlackPixels = minPixel2nbBlackPixels[minPixelDiffForBackExtract]
      dist = abs(nbBlackPixels - nbBlackPixelsMax)
      if dist < minDist:
        minDist = dist
        best_minPixelDiffForBackExtract = minPixelDiffForBackExtract
        
    minPixelDiffForBackExtract = best_minPixelDiffForBackExtract
    putToWhite = (curFrame.astype('int32') >= (back.astype('int32') - minPixelDiffForBackExtract) )
    curFrame[putToWhite] = 255
    
    ret, thresh1 = cv2.threshold(curFrame, hyperparameters["thresholdForBlobImg"], 255, cv2.THRESH_BINARY)
    thresh1 = 255 - thresh1
    
    hyperparameters["minPixelDiffForBackExtractBody"] = minPixelDiffForBackExtract
  
  contours, hierarchy = cv2.findContours(thresh1, cv2.RETR_TREE, contourPrecision)
  for contour in contours:
    area = cv2.contourArea(contour)
    if (area >= hyperparameters["minAreaBody"]) and (area <= hyperparameters["maxAreaBody"]):
      dist = cv2.pointPolygonTest(contour, (x, y), True)
      if dist >= 0 or hyperparameters["saveBodyMask"]:
        M = cv2.moments(contour)
        if M['m00']:
          cx = int(M['m10']/M['m00'])
          cy = int(M['m01']/M['m00'])
          bodyContour = contour
        else:
          cx = 0
          cy = 0
  
  if type(bodyContour) != int:
    if cv2.contourArea(bodyContour) >= hyperparameters["maxAreaBody"]:
      bodyContour = 0
  
  if hyperparameters["saveBodyMask"]:
    saveImagesAndData(hyperparameters, bodyContour, initialCurFrame, wellNumber, frameNumber)
        
  return bodyContour
