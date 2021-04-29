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

from zebrazoom.code.trackingFolder.tailTrackingFunctionsFolder.tailTrackingExtremityDetectFolder.findTailExtremeteFolder.functions import PointDot
from zebrazoom.code.trackingFolder.tailTrackingFunctionsFolder.tailTrackingExtremityDetectFolder.findTailExtremeteFolder.functions import calculateJuge
from zebrazoom.code.trackingFolder.tailTrackingFunctionsFolder.tailTrackingExtremityDetectFolder.findTailExtremeteFolder.functions import calculateJuge2
from zebrazoom.code.trackingFolder.tailTrackingFunctionsFolder.tailTrackingExtremityDetectFolder.findTailExtremeteFolder.functions import smoothTail

def insideTailExtremete(distance, DotProds, max_droite, min_gauche, max_bas, min_haut, ind_droite, ind_gauche, ind_bas, ind_haut, tailRange, boundary, dst):
  
  
  TotalBPts = len(boundary)
  
  # This may require some adjustements in the future (maybe some value other than 25)
  dist_calculate_curv = int(TotalBPts / 25)
  if dist_calculate_curv < 3:
    dist_calculate_curv = 3
  
  max = 0

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
