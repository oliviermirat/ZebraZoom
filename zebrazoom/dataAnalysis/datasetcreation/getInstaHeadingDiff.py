import numpy as np
from scipy.interpolate import UnivariateSpline
import math

def getInstaHeadingDiff(curbout, nbFramesTakenIntoAccount):

  fin = curbout["BoutEnd"] - curbout["BoutStart"] + 1

  if fin > 2:
    heading = curbout["Heading"].copy()
    instHeading = np.diff(heading)
    # 0.1 - 6.2 = -6.1 but should be  0.2 so : +2 pi
    # 6.2 - 0.1 =  6.1 but should be -0.2 so : -2 pi
    tooSmall = (instHeading < -math.pi)
    tooBig   = (instHeading >  math.pi)
    instHeading[tooSmall] = instHeading[tooSmall] + 2*math.pi
    instHeading[tooBig]   = instHeading[tooBig]   - 2*math.pi
    instHeading = np.append(instHeading, instHeading[len(instHeading)-1])
    
  else:
    instHeading = [0]*fin
    
  instHeading2  = [0]*nbFramesTakenIntoAccount
  
  sizeTabNotZero = min(fin, nbFramesTakenIntoAccount)
  instHeading2[0:sizeTabNotZero] = instHeading[0:sizeTabNotZero]

  return instHeading2
