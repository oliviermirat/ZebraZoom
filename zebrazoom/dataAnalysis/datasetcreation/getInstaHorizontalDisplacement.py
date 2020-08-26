import numpy as np
from scipy.interpolate import UnivariateSpline
import math
from numpy.linalg import norm

def getInstaHorizontalDisplacement(curbout, nbFramesTakenIntoAccount):

  fin = curbout["BoutEnd"] - curbout["BoutStart"] + 1

  if fin > 2:
    HeadX = curbout["HeadX"].copy()
    HeadY = curbout["HeadY"].copy()
    heading  = curbout["Heading"].copy()
    
    instHorizDisp = [0]*fin
    for i in range(0, len(instHorizDisp)-1):
      p1 = np.array((HeadX[i], HeadY[i]))
      p2 = np.array((HeadX[i] + math.cos(heading[i]), HeadY[i] + math.sin(heading[i])))
      p3 = np.array((HeadX[i+1], HeadY[i+1]))
      instHorizDisp[i] = norm(np.cross(p2-p1, p1-p3))/norm(p2-p1)
    
    instHorizDisp = np.append(instHorizDisp, instHorizDisp[len(instHorizDisp)-1])
    
  else:
    instHorizDisp = [0]*fin
    
  instHorizDisp2  = [0]*nbFramesTakenIntoAccount
  
  sizeTabNotZero = min(fin, nbFramesTakenIntoAccount)
  instHorizDisp2[0:sizeTabNotZero] = instHorizDisp[0:sizeTabNotZero]

  return instHorizDisp2
