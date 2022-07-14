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

from zebrazoom.code.trackingFolder.tailTrackingFunctionsFolder.tailTrackingExtremityDetectFolder.findTailExtremeteFolder.functions import initialiseDistance2
from zebrazoom.code.trackingFolder.tailTrackingFunctionsFolder.tailTrackingExtremityDetectFolder.findTailExtremeteFolder.functions import PointDot
from zebrazoom.code.trackingFolder.tailTrackingFunctionsFolder.tailTrackingExtremityDetectFolder.findTailExtremeteFolder.functions import calculateJuge
from zebrazoom.code.trackingFolder.tailTrackingFunctionsFolder.tailTrackingExtremityDetectFolder.findTailExtremeteFolder.functions import calculateJuge2
from zebrazoom.code.trackingFolder.tailTrackingFunctionsFolder.tailTrackingExtremityDetectFolder.findTailExtremeteFolder.functions import smoothTail
from zebrazoom.code.trackingFolder.tailTrackingFunctionsFolder.tailTrackingExtremityDetectFolder.findTailExtremeteFolder.insideTailExtremete import insideTailExtremete

def findTailExtremete(rotatedContour, bodyContour, aaa, bord1b, bord2b, debug, dst, tailExtremityMaxJugeDecreaseCoeff, hyperparameters):

  max  = 0
  max2 = 0
  TotalBPts = len(rotatedContour)
  DotProds = np.zeros(TotalBPts)
  distance = np.zeros(TotalBPts)

  for i in range(0, TotalBPts):
    distance[i] = 0

  distance2 = np.zeros(TotalBPts+1)
  for i in range(0, TotalBPts):
    distance2[i] = 0
    
  [d, distance2] = initialiseDistance2(distance2, rotatedContour)
 
  max_droite = 0
  min_gauche = 5000
  max_bas    = 0
  min_haut   = 5000
  
  ind_droite = 0
  ind_gauche = 0
  ind_bas    = 0
  ind_haut   = 0
  
  x = 0
  y = 0
  
  bord1 = 0
  bord2 = 0
  if (bord2b < bord1b):
    bord1 = bord2b
    bord2 = bord1b
  else:
    bord1 = bord1b
    bord2 = bord2b

  Bord1 = rotatedContour[bord1][0]
  Bord2 = rotatedContour[bord2][0]
        
  max1 = distance2[bord2] - distance2[bord1] 
  max2 = (distance2[bord1] - distance2[0])  + (distance2[len(rotatedContour)] - distance2[bord2])
  
  if hyperparameters["checkAllContourForTailExtremityDetect"] == 0:
    tailRange = []
    if (max1 > max2):
      for i in range(bord1, bord2):
        tailRange.append(i)
    else:
      for i in range(0, bord1):
        tailRange.append(i)
      for i in range(bord2, len(rotatedContour)):
        tailRange.append(i)
  else:
    tailRange = []
    for i in range(0, len(rotatedContour)):
      tailRange.append(i)
    
  [max2, max_droite, min_gauche, max_bas, min_haut, ind_droite, ind_gauche, ind_bas, ind_haut] = insideTailExtremete(distance2, DotProds, max_droite, min_gauche, max_bas, min_haut, ind_droite, ind_gauche, ind_bas, ind_haut, tailRange, rotatedContour, dst)
    
  MostCurvy = 100000
  CurrentCurviness = 0
  MostCurvyIndex = 0
  TailIndex = 0

  max_dist = 15000.0
  
  jugeDroite = calculateJuge2(ind_droite,distance2,bord1,bord2,TotalBPts)
  jugeGauche = calculateJuge2(ind_gauche,distance2,bord1,bord2,TotalBPts)
  jugeHaut   = calculateJuge2(ind_haut,distance2,bord1,bord2,TotalBPts)
  jugeBas    = calculateJuge2(ind_bas,distance2,bord1,bord2,TotalBPts)
  maxJuge    = 0.0
  if jugeDroite > jugeGauche:
    maxJuge = jugeDroite
  else:
    maxJuge = jugeGauche

  if jugeHaut > maxJuge:
    maxJuge = jugeHaut

  if jugeBas > maxJuge:
    maxJuge = jugeBas

  maxJuge = maxJuge - tailExtremityMaxJugeDecreaseCoeff * maxJuge
  
  if debug:
    print("MostCurvy:",MostCurvy,";maxJuge:",maxJuge)
  
  DotProdPtr = DotProds[ind_droite]
  if debug:
    print("Droite (red) = curv: ", DotProdPtr, " ; jugeDroite: ", jugeDroite)

  if ((DotProdPtr < MostCurvy) and (jugeDroite > maxJuge)):
    MostCurvy =  DotProdPtr
    MostCurvyIndex = ind_droite
    if debug:
      print("droite wins")
  
  DotProdPtr=DotProds[ind_gauche]
  if (debug):
    print("Gauche (blue) = curv: ", DotProdPtr, " ; jugeGauche: ", jugeGauche)

  if (( DotProdPtr < MostCurvy) and (jugeGauche > maxJuge)):
    MostCurvy =  DotProdPtr
    MostCurvyIndex = ind_gauche
    if (debug):
      print("gauche wins")
  
  DotProdPtr = DotProds[ind_haut]
  if debug:
    print("Haut (white) = curv: ", DotProdPtr, " ; jugeHaut: ", jugeHaut)

  if (( DotProdPtr < MostCurvy) and (jugeHaut > maxJuge) and hyperparameters["considerHighPointForTailExtremityDetect"]):
    MostCurvy =  DotProdPtr
    MostCurvyIndex = ind_haut
    if (debug):
      print("haut wins")
  
  DotProdPtr = DotProds[ind_bas]
  if debug:
    print("Bas (Purple)= curv: ", DotProdPtr, " ; jugeBas: ", jugeBas)

  if (( DotProdPtr < MostCurvy) and (jugeBas > maxJuge)):
    MostCurvy =  DotProdPtr
    MostCurvyIndex = ind_bas
    if (debug):
      print("bas wins")
    
  if (debug):
    import zebrazoom.code.util as util

    # Droite
    pt1 = bodyContour[int(ind_droite)][0]
    cv2.circle(dst, (pt1[0],pt1[1]), 1, (255, 0, 0), -1)
    # Gauche
    pt1 = bodyContour[int(ind_gauche)][0]
    cv2.circle(dst, (pt1[0],pt1[1]), 1, (0, 255, 0), -1)
    # Haut
    pt1 = bodyContour[int(ind_haut)][0]
    cv2.circle(dst, (pt1[0],pt1[1]), 1, (0, 0, 255), -1)
    # Bas
    pt1 = bodyContour[int(ind_bas)][0]
    cv2.circle(dst, (pt1[0],pt1[1]), 1, (255, 255, 0), -1)
    if False: # The following can sometimes be useful when debugging
      for i in range(0, len(rotatedContour)):
        pt1 = rotatedContour[int(i)][0]
        cv2.circle(dst, (pt1[0],pt1[1]), 1, (0, 0, 0), -1)
    if hyperparameters["debugTrackingPtExtremeLargeVerticals"]:
      dst = dst[pt1[1]-200:len(dst), :]
    # Plotting points
    util.showFrame(dst, title='Frame')
    
  # allPossibilities = [[ind_droite,DotProds[ind_droite],jugeDroite], [ind_gauche,DotProds[ind_gauche],jugeGauche], [ind_haut,DotProds[ind_haut],jugeHaut], [ind_bas,DotProds[ind_bas],jugeBas]]
  
  return [MostCurvyIndex, distance2]
