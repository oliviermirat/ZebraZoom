import numpy as np
from scipy.interpolate import UnivariateSpline

def getTailAngleRecalculated2(curbout, nbFramesTakenIntoAccount, numberOfBendsIncludedForMaxDetect):

  fin = curbout["BoutEnd"] - curbout["BoutStart"] + 1
  
  numps = 3
  
  headx = curbout["HeadX"]
  heady = curbout["HeadY"]
  tailx = curbout["TailX_VideoReferential"]
  taily = curbout["TailY_VideoReferential"]
  
  tailangles_arr = np.zeros((nbFramesTakenIntoAccount,7))
  for i in range(min(len(headx),tailangles_arr.shape[0])):
    if len(taily[i]) > 3 and len(tailx[i]) > 3:
      ang = np.arctan2(heady[i] - taily[i][-3],headx[i] - tailx[i][-3])*180/np.pi
      for j in range(tailangles_arr.shape[1]):
        ang2 = np.arctan2(heady[i] - taily[i][j],headx[i] - tailx[i][j])*180/np.pi
        delang = ang2 - ang
        if np.abs(delang) < 180:
          tailangles_arr[i,j] = delang
        elif delang > 180:
          tailangles_arr[i,j] = delang - 360
        elif delang < -180:
          tailangles_arr[i,j] = 360 + delang
    else:
      for j in range(tailangles_arr.shape[1]):
        tailangles_arr[i,j] = 0
    
  tailangles_arr = tailangles_arr.flatten()
  
  return tailangles_arr
