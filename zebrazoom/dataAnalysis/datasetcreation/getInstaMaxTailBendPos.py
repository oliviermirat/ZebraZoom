# WORK IN PROGRESS

import numpy as np
from scipy.interpolate import UnivariateSpline

def getInstaMaxTailBendPos(curbout, nbFramesTakenIntoAccount):

  fin = curbout["BoutEnd"] - curbout["BoutStart"] + 1
  
  if fin > 2:
    tailPosX = curbout["TailX_VideoReferential"].copy()
    tailPosY = curbout["TailY_VideoReferential"].copy()
    for i in range(0, fin):
      tailPosXcur = tailPosX[i]
      tailPosYcur = tailPosY[i]
      for j in range(1, len(tailPosXcur)-1):
        
    
    instMaxTailBendPos = 
    instMaxTailBendPos = np.append(instMaxTailBendPos, instMaxTailBendPos[len(instMaxTailBendPos)-1])
  else:
    instMaxTailBendPos = [0]*fin
    
  instMaxTailBendPos2  = [0]*nbFramesTakenIntoAccount
  
  sizeTabNotZero = min(fin, nbFramesTakenIntoAccount)
  
  # for i in range(0,sizeTabNotZero):
    # instSpeed2[i] = instSpeed[i]
  instMaxTailBendPos2[0:sizeTabNotZero] = instMaxTailBendPos[0:sizeTabNotZero]
  
  
  return instMaxTailBendPos2
