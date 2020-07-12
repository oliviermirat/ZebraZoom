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

def findTheTwoSides(headPosition, bodyContour, dst):

  aaa = headPosition[0]
  bbb = headPosition[1]
  minNbPointsBetweenTwoBordersIndexes     = 3
  findSecondTailBasisVectorCreationFactor = 1
  dist = 0
  min  = 10000000
  coolIndex  = 0
  coolIndex2 = 0
  k = findSecondTailBasisVectorCreationFactor
  res = np.zeros(2)
  res[0] = 0
  res[1] = 0
  
  while (abs(coolIndex-coolIndex2) < minNbPointsBetweenTwoBordersIndexes) and (k < 20):

    for i in range(0, len(bodyContour)):
      Pt   = bodyContour[i][0]
      dist = (Pt[0] - aaa) * (Pt[0] - aaa) + (Pt[1] - bbb) * (Pt[1]-bbb)
      if (dist < min):
        coolIndex = i
        min       = dist
		
    res[0] = coolIndex
    Pt = bodyContour[coolIndex][0]
		
    z = (k+1) * aaa - k * (Pt[0])
    v = (k+1) * bbb - k * (Pt[1])
    min = 10000000
    
    for i in range(0, len(bodyContour)):
      Pt   = bodyContour[i][0]
      dist = (Pt[0] - z) * (Pt[0] - z) + (Pt[1] - v) * (Pt[1] - v);
      if (dist < min):
        coolIndex2 = i
        min        = dist
    res[1] = coolIndex2
    k = k + 1
  
  pt1 = bodyContour[int(res[0])][0]
  pt2 = bodyContour[int(res[1])][0]
  
  if False:
    cv2.circle(dst, (pt1[0],pt1[1]), 1, (0, 0, 255), -1)
    cv2.circle(dst, (pt2[0],pt2[1]), 1, (0, 0, 255), -1)
    cv2.imshow('Frame', dst)
    cv2.waitKey(0)
  
  return res
