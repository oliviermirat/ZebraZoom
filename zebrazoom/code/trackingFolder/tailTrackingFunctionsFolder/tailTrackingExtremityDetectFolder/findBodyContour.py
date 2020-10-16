import h5py
import numpy as np
import cv2
import math
import json
import sys
import matplotlib.pyplot as plt
from scipy import interpolate
from getForegroundImage import getForegroundImage
from headEmbededFrame import headEmbededFrame
from scipy.interpolate import UnivariateSpline
from numpy import linspace

def findBodyContour(headPosition, hyperparameters, thresh1):
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
        M = cv2.moments(contour)
        if takeTheHeadClosestToTheCenter == 0:
          if M['m00']:
            cx = int(M['m10']/M['m00'])
            cy = int(M['m01']/M['m00'])
            bodyContour = contour
          else:
            cx = 0
            cy = 0
        else:
          if M['m00']:
            cxNew = int(M['m10']/M['m00'])
            cyNew = int(M['m01']/M['m00'])
          else:
            cxNew = 0
            cyNew = 0
          distToCenterNew = math.sqrt((cxNew-x)**2 + (cyNew-y)**2)
          distToCenter    = math.sqrt((cx-x)**2    + (cy-y)**2)
          if distToCenterNew < distToCenter:
            cx = cxNew
            cy = cyNew
            bodyContour = contour
    minAreaCur = minAreaCur - 100
    maxAreaCur = maxAreaCur + 100
  return bodyContour
