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

def initialiseDistance2(distance, boundary):
  TotalBPts   = len(boundary)
  distance[0] = 0
  for i in range(1, TotalBPts+1):
    if (i == TotalBPts):
      Pt = boundary[0][0]
    else:
      Pt = boundary[i][0]
    AvantPt = boundary[i-1][0]
    Dx = AvantPt[0] - Pt[0]
    Dy = AvantPt[1] - Pt[1]
    if i:
      distance[i] = distance[i-1] + math.sqrt(Dx*Dx + Dy*Dy)
    else:
      distance[i] = math.sqrt(Dx*Dx + Dy*Dy)
  return [distance[TotalBPts], distance]

  
def PointDot(VecA, VecB):
  return (VecA[0])*(VecB[0]) + (VecA[1])*(VecB[1])


def calculateJuge(indice, distance, max):
  juge = 0
  if distance[indice] < max - distance[indice]:
    juge = (max-2*distance[indice])/max
  else:
    juge = (2*distance[indice]-max)/max
  return juge


def calculateJuge2(indice, distance, bord1, bord2, nb):
  
  dist  = 0
  dist2 = 0
  dist3 = 0
  dist4 = 0
  mindist = 10000000000
  
  if indice < bord1:
    dist  = distance[bord1] - distance[indice]
    dist2 = distance[indice] + (distance[nb] - distance[bord1])
  else:
    dist  = distance[indice] - distance[bord1]
    dist2 = distance[bord1] + ( distance[nb] - distance[indice] )
  
  if indice < bord2:
    dist3 = distance[bord2] - distance[indice]
    dist4 = distance[indice] + ( distance[nb] - distance[bord2] )
  else:
    dist3 = distance[indice] - distance[bord2]
    dist4 = distance[bord2] + ( distance[nb] - distance[indice] )
  
  if dist < mindist:
    mindist = dist

  if dist2 < mindist:
    mindist = dist2

  if dist3 < mindist:
    mindist = dist3

  if dist4 < mindist:
    mindist = dist4
  
  return mindist

  
def smoothTail(points, nbTailPoints):
  
  y = points[0]
  x = linspace(0, 1, len(y))
  
  if len(x) > 3:    
  
    s = UnivariateSpline(x, y, s=10)
    xs = linspace(0, 1, nbTailPoints)
    newX = s(xs)

    y = points[1]
    x = linspace(0, 1, len(y))
    s = UnivariateSpline(x, y, s=10)
    xs = linspace(0, 1, nbTailPoints)
    newY = s(xs)
    
  else:
  
    newX = x
    newY = y
  
  return [newX, newY]
