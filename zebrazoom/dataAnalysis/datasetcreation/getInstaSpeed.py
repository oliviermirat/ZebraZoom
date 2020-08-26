import numpy as np
from scipy.interpolate import UnivariateSpline

def getInstaSpeed(curbout, nbFramesTakenIntoAccount):

  fin = curbout["BoutEnd"] - curbout["BoutStart"] + 1
  
  if fin > 2:
    HeadX = curbout["HeadX"].copy()
    HeadY = curbout["HeadY"].copy()
    instSpeed = np.sqrt(np.power(np.diff(HeadX),2)+np.power(np.diff(HeadY),2))
    instSpeed = np.append(instSpeed, instSpeed[len(instSpeed)-1])
  else:
    instSpeed = [0]*fin
    
  instSpeed2  = [0]*nbFramesTakenIntoAccount
  
  sizeTabNotZero = min(fin, nbFramesTakenIntoAccount)
  
  # for i in range(0,sizeTabNotZero):
    # instSpeed2[i] = instSpeed[i]
  instSpeed2[0:sizeTabNotZero] = instSpeed[0:sizeTabNotZero]
  
  
  return instSpeed2
