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

def resampleSeqConstPtsPerArcLength(OrigBound, numTailPoints):
  
  n = len(OrigBound)
  distOrg = np.zeros(n)
  xOrg    = np.zeros(n)
  yOrg    = np.zeros(n)
  
  totDist = 0
  distOrg[0] = totDist
  xOrg[0] = OrigBound[0][0][0]
  yOrg[0] = OrigBound[0][0][1]
  
  for i in range(1, n):
    diff       = math.sqrt((OrigBound[i-1][0][0]-OrigBound[i][0][0])**2 + (OrigBound[i-1][0][1]-OrigBound[i][0][1])**2)
    totDist    = totDist + diff
    distOrg[i] = totDist
  
  uniDist = np.zeros(numTailPoints)
  uniX    = np.zeros(numTailPoints)
  uniY    = np.zeros(numTailPoints)
  
  for i in range(0, numTailPoints):
    uniDist[i] = totDist * (i/(numTailPoints-1))
  
  for i in range(1, n):
    xOrg[i] = OrigBound[i][0][0]
    yOrg[i] = OrigBound[i][0][1]
  
  uniX = np.interp(uniDist, distOrg, xOrg)
  uniY = np.interp(uniDist, distOrg, yOrg)
  
  output = np.zeros((numTailPoints, 2))
  for i in range(0, numTailPoints):
    output[i][0] = uniX[i]
    output[i][1] = uniY[i]
  
  return output
