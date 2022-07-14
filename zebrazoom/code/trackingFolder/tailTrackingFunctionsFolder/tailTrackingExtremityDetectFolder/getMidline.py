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

from zebrazoom.code.trackingFolder.tailTrackingFunctionsFolder.tailTrackingExtremityDetectFolder.resampleSeqConstPtsPerArcLength import resampleSeqConstPtsPerArcLength

def fillTailRanges(tailRange1,tailRange2,fillSecond,i,MostCurvyIndex):
  if (i == MostCurvyIndex):
    fillSecond = 1
  if fillSecond == 0:
    tailRange1.append(i)
  else:
    tailRange2.append(i)
  return [tailRange1,tailRange2,fillSecond]

def getMidline(bord1, bord2, MostCurvyIndex, boundary, dst, taille, distance2, debug, hyperparameters, nbTailPoints):

  nbTailPoints = taille
  output = np.zeros((1, 0, 2))

  numTailPoints = nbTailPoints
  minTailSize = 20
  maxTailSize = 60
  trackingPointSizeDisplay = 1

  OrigBoundA = []
  OrigBoundB = []
  
  if (bord2 < bord1):
    temp  = bord2
    bord2 = bord1
    bord1 = temp
    
  max1 = distance2[bord2] - distance2[bord1] 
  max2 = (distance2[bord1] - distance2[0])  + (distance2[len(boundary)] - distance2[bord2])
  
  tailRangeA = []
  tailRangeB = []
  fillSecond = 0
  if (max1 > max2):
    for i in range(bord1, bord2):
      [tailRangeA,tailRangeB,fillSecond] = fillTailRanges(tailRangeA,tailRangeB,fillSecond,i,MostCurvyIndex)
  else:
    for i in range(bord2, len(boundary)):
      [tailRangeA,tailRangeB,fillSecond] = fillTailRanges(tailRangeA,tailRangeB,fillSecond,i,MostCurvyIndex)
    for i in range(0, bord1):
      [tailRangeA,tailRangeB,fillSecond] = fillTailRanges(tailRangeA,tailRangeB,fillSecond,i,MostCurvyIndex)
  
  OrigBoundA = boundary[tailRangeA]
  OrigBoundB = boundary[tailRangeB]
  
  if ((bord1!=bord2) and (bord1!=MostCurvyIndex) and (bord2!=MostCurvyIndex) and not((bord1==1) and (bord2==1) and (MostCurvyIndex==1)) and (len(OrigBoundA)>1) and (len(OrigBoundB)>1)):
    
    if False:
      for pt in OrigBoundA:
        cv2.circle(dst, (pt[0][0], pt[0][1]), 1, (0, 255, 0), -1)
      for pt in OrigBoundB:
        cv2.circle(dst, (pt[0][0], pt[0][1]), 1, (255, 0, 0), -1)
      import zebrazoom.code.util as util

      util.showFrame(dst, title='dst')
    
    NBoundA = resampleSeqConstPtsPerArcLength(OrigBoundA, numTailPoints)
    NBoundB = resampleSeqConstPtsPerArcLength(OrigBoundB, numTailPoints)

    # calculates length of the tail
    TotalDist = 0
    for i in range(1, taille):
      Pt  = NBoundB[i % taille]
      Pt2 = NBoundA[taille - i]
      x = (Pt[0]+Pt2[0]) / 2
      y = (Pt[1]+Pt2[1]) / 2
      if i > 1:
        TotalDist = TotalDist + math.sqrt((x-xAvant)*(x-xAvant)+(y-yAvant)*(y-yAvant))
      xAvant = x
      yAvant = y
      
    if ((TotalDist<hyperparameters["minTailSize"]) or (TotalDist>hyperparameters["maxTailSize"])):
    
      if (debug):
        print("innapropriate tail size! TailDist: ", TotalDist, " ; but minTailSize is ", minTailSize, " and maxTailSize is ", maxTailSize)
        
    else:
      
      Tail = boundary[MostCurvyIndex][0]
      
      point = np.array([Tail[0], Tail[1]])
      output = np.insert(output, 0, point, axis=1)
      
      for i in range(1, taille):
        Pt  = NBoundB[i % taille]
        Pt2 = NBoundA[taille - i]
        point = np.array([(Pt[0]+Pt2[0])/2, (Pt[1]+Pt2[1])/2])
        output = np.insert(output, 0, point, axis=1)
      
      i = taille-2
      if i >= 1:
        Pt =  NBoundB[i % taille]
        Pt2 = NBoundA[taille-i]
        ClosestPoint = [ (Pt[0]+Pt2[0])/2 , (Pt[1]+Pt2[1])/2 ]
      else:
        ClosestPoint = [-200, -200]
  
  else:
  
    # THIS SHOULD BE IMPROVED IN THE FUTURE:
    # WE SHOULD CHECK FOR TAIL LENGHT
    # ALSO WE SHOULD DO SOMETHING BETTER THAN JUST PUTTING THE TAIL TIP FOR EACH OF THE TEN POINTS !!!
    Tail = boundary[MostCurvyIndex][0]    
    point = np.array([Tail[0], Tail[1]])
    for i in range(0, taille):
      output = np.insert(output, 0, point, axis=1)    
  
  return output
