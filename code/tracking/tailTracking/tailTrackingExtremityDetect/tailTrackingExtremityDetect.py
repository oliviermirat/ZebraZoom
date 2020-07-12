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

from getMidline import getMidline
from findTailExtremete import findTailExtremete
from findTheTwoSides import findTheTwoSides
from findBodyContour import findBodyContour
from Rotate import Rotate
from checkIfMidlineIsInBlob import checkIfMidlineIsInBlob

# from kalmanFilter import kalman_xy
# from trackingFunctions import calculateAngle
# from trackingFunctions import distBetweenThetas
# from trackingFunctions import assignValueIfBetweenRange

 
def tailTrackingExtremityDetect(headPosition,nbTailPoints,i,thresh1,frame,debugAdv,heading, hyperparameters):
  
  dst = frame.copy()
  dst = cv2.cvtColor(dst, cv2.COLOR_GRAY2RGB)
  firstFrame = hyperparameters["firstFrame"]
  lastFrame = hyperparameters["lastFrame"]
  
  if hyperparameters["debugTrackingThreshImg"]:
    cv2.imshow('debugTrackingThreshImg', thresh1)
    cv2.waitKey(0)
  
  # Finding blob corresponding to the body of the fish
  bodyContour = findBodyContour(headPosition, hyperparameters, thresh1)
  
  if type(bodyContour) != int:
    
    # Finding the two sides of the fish
    res = findTheTwoSides(headPosition, bodyContour, dst)
    
    # Finding tail extremity
    # if True:
    rotatedContour = bodyContour.copy()
    rotatedContour = Rotate(rotatedContour,int(headPosition[0]),int(headPosition[1]),heading,dst)
    [MostCurvyIndex, distance2] = findTailExtremete(rotatedContour, bodyContour, headPosition[0], int(res[0]), int(res[1]), debugAdv, dst, hyperparameters["tailExtremityMaxJugeDecreaseCoeff"])
    # else:
      # [MostCurvyIndex, distance2] = findTailExtremete(bodyContour, headPosition[0], int(res[0]), int(res[1]), debugAdv, dst)
    
    if debugAdv:
      # Head Center
      cv2.circle(dst, (int(headPosition[0]),int(headPosition[1])), 3, (255, 255, 0), -1)
      # Tail basis 1
      pt1 = bodyContour[int(res[0])][0]
      cv2.circle(dst, (pt1[0],pt1[1]), 3, (255, 0, 0), -1)
      # Tail basis 2
      pt1 = bodyContour[int(res[1])][0]
      cv2.circle(dst, (pt1[0],pt1[1]), 3, (255, 0, 0), -1)
      # Tail extremity
      pt1 = bodyContour[int(MostCurvyIndex)][0]
      cv2.circle(dst, (pt1[0],pt1[1]), 3, (0, 0, 255), -1)
      # Plotting points
      cv2.imshow('Frame', dst)
      cv2.waitKey(0)
    
    # Getting Midline
    taille = 10
    tail = getMidline(int(res[0]), int(res[1]), int(MostCurvyIndex), bodyContour, dst, taille-1, distance2, debugAdv, hyperparameters)
    
    # Optimizing midline if necessary
    midlineIsInBlobTrackingOptimization = hyperparameters["midlineIsInBlobTrackingOptimization"]
    if midlineIsInBlobTrackingOptimization:
      [allInside, tailLength] = checkIfMidlineIsInBlob(int(res[0]), int(res[1]), int(MostCurvyIndex), bodyContour, dst, taille-1, distance2, debugAdv, hyperparameters)
      if allInside == False:
        n = len(bodyContour)
        maxTailLength = -1
        for j in range(0, n):
          [allInside, tailLength] = checkIfMidlineIsInBlob(int(res[0]), int(res[1]), j, bodyContour, dst, taille-1, distance2, debugAdv, hyperparameters)
          if allInside:
            if tailLength > maxTailLength:
              MostCurvyIndex = j
              maxTailLength = tailLength
        tail = getMidline(int(res[0]), int(res[1]), int(MostCurvyIndex), bodyContour, dst, taille-1, distance2, debugAdv, hyperparameters)        
    
    # Applying snake on tail
    applySnake = False
    if applySnake:
      tail2 = tail[0]
      n = len(tail2)
      # tail2[n-1][0] = tail2[n-1][0] + (tail2[n-1][0] - tail2[n-2][0]) * 6
      # tail2[n-1][1] = tail2[n-1][1] + (tail2[n-1][1] - tail2[n-2][1]) * 6
      # print(type(tail))
      # r = np.linspace(tail2[0][0], tail2[0][0] + (tail2[1][0]-tail2[0][0]) * 15, 9)
      # c = np.linspace(tail2[0][1], tail2[0][1] + (tail2[1][1]-tail2[0][1]) * 15, 9)
      # tail2 = np.array([r, c]).T
      # r = np.linspace(tail2[0][0], tail2[n-1][0], 9)
      # c = np.linspace(tail2[0][1], tail2[n-1][1], 9)
      # tail2 = np.array([r, c]).T
      from skimage.color import rgb2gray
      from skimage.filters import gaussian
      from skimage.segmentation import active_contour
      snake = active_contour(gaussian(frame, 3), tail2, w_edge=-1000, bc="fixed")
      # snake = active_contour(gaussian(frame, 3), tail2, w_edge=0, bc="fixed-free")
      print(snake)
      # snake = tail2
      tail[0] = snake
  
  else:
    
    tail = np.zeros((1, 0, 2))
  
  # Inserting head position, smoothing tail and creating output
  tail = np.insert(tail, 0, headPosition, axis=1)
  # tail = smoothTail(tail, nbTailPoints)
  
  output = np.zeros((1, len(tail[0]), 2))
  
  for idx, x in enumerate(tail[0]):
    output[0][idx][0] = x[0]
    output[0][idx][1] = x[1]

  return output
