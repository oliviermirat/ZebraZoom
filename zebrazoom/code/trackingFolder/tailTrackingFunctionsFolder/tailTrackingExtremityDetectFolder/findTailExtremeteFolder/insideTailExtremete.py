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

from functions import PointDot
from functions import calculateJuge
from functions import calculateJuge2
from functions import smoothTail

def insideTailExtremete(distance, DotProds, max_droite, min_gauche, max_bas, min_haut, ind_droite, ind_gauche, ind_bas, ind_haut, tailRange, boundary, dst):
  
  dist_calculate_curv=3;
  max = 0

  TotalBPts = len(boundary)

  AheadPtr  = 0
  BehindPtr = 0
  Ptr       = 0

  juge = 0
  x = 0
  y = 0

  for i in tailRange:
    AheadPtr = (i + dist_calculate_curv) % TotalBPts
    BehindPtr = (i + TotalBPts - dist_calculate_curv) % TotalBPts
    Ptr = i % TotalBPts
    AheadPt = boundary[AheadPtr][0]
    Pt = boundary[Ptr][0]
    
    BehindPt    = boundary[BehindPtr][0]
    AheadVec    = [AheadPt[0] - Pt[0],  AheadPt[1] - Pt[1]]
    
    BehindVec   = [Pt[0] - BehindPt[0], Pt[1] - BehindPt[1]]
    DotProdVal  = PointDot(AheadVec, BehindVec)
    DotProds[i] = DotProdVal
    x = Pt[0]
    y = Pt[1]
    
    # Hmm... not sure about this part bellow...
    fin_boucle = tailRange[len(tailRange)-1]
    juge = calculateJuge(i,distance,distance[fin_boucle-1])
    # The line above should probably be replace by the one below at some point !!!
    # juge=calculateJuge2(i,distance,bord1,bord2,TotalBPts);
    # (juge > trackParameters.minDistFromTailExtremityToTailBasis)
    
    if x > max_droite:
      max_droite = x
      ind_droite = i
    if x < min_gauche:
      min_gauche = x
      ind_gauche = i
    if y > max_bas:
      max_bas = y
      ind_bas = i
    if (y < min_haut): # and (juge < 0.20):
      min_haut = y
      ind_haut = i

    droite = ind_droite
    gauche = ind_gauche
    haut   = ind_haut
    bas    = ind_bas
    
    max = distance[i]
  
  return [max, max_droite, min_gauche, max_bas, min_haut, ind_droite, ind_gauche, ind_bas, ind_haut]
