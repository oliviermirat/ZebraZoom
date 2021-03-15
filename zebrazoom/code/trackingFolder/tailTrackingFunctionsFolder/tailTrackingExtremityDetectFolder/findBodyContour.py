import h5py
import numpy as np
import cv2
import math
import json
import sys
from scipy import interpolate
from zebrazoom.code.getImage.getForegroundImage import getForegroundImage
from zebrazoom.code.getImage.headEmbededFrame import headEmbededFrame
from scipy.interpolate import UnivariateSpline
from numpy import linspace

def findBodyContour(headPosition, hyperparameters, thresh1):

  thresh1[:,0] = 255
  thresh1[0,:] = 255
  thresh1[:, len(thresh1[0])-1] = 255
  thresh1[len(thresh1)-1, :]    = 255

  x = headPosition[0]
  y = headPosition[1]
  cx = 0
  cy = 0
  takeTheHeadClosestToTheCenter = 1
  minAreaCur = hyperparameters["minAreaBody"]
  maxAreaCur = hyperparameters["maxAreaBody"]
  bodyContour = 0
  while (cx == 0) and (minAreaCur > -200):
    if hyperparameters["findContourPrecision"] == "CHAIN_APPROX_SIMPLE":
      contourPrecision = cv2.CHAIN_APPROX_SIMPLE
    else: # hyperparameters["findContourPrecision"] == "CHAIN_APPROX_NONE"
      contourPrecision = cv2.CHAIN_APPROX_NONE
    
    contours, hierarchy = cv2.findContours(thresh1, cv2.RETR_TREE, contourPrecision)
    for contour in contours:
      area = cv2.contourArea(contour)
      if (area > minAreaCur) and (area < maxAreaCur):
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
    
    minAreaCur = minAreaCur - 100
    maxAreaCur = maxAreaCur + 100
  return bodyContour
