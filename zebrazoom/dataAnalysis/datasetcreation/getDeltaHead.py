import numpy as np
from scipy.interpolate import UnivariateSpline

#Heading change in degrees
def getDeltaHead(b, fromHeadingIdx=None):
  if fromHeadingIdx is not None:
    if 'Heading' not in b:
      return np.nan
    slope0 = b['Heading'][0] * 180 / np.pi
    slope1 = b['Heading'][fromHeadingIdx] * 180 / np.pi
  else:
    numps = int(len(b["TailX_VideoReferential"][0]) / 3) # Taking point at a third of the lenght of the tail
    if numps == 0:
      numps = 1
    bXs = np.concatenate((b["TailX_VideoReferential"][0][-numps:],[b["HeadX"][0]]))
    bYs = np.concatenate((b["TailY_VideoReferential"][0][-numps:],[b["HeadY"][0]]))
    slope0 = np.arctan2((bYs[-1]-bYs[0]),(bXs[-1]-bXs[0]))*180/np.pi
    bXs = np.concatenate((b["TailX_VideoReferential"][-1][-numps:],[b["HeadX"][-1]]))
    bYs = np.concatenate((b["TailY_VideoReferential"][-1][-numps:],[b["HeadY"][-1]]))
    slope1 = np.arctan2((bYs[-1]-bYs[0]),(bXs[-1]-bXs[0]))*180/np.pi
  
  delt = slope1 - slope0
  if delt > 180:
    return -(360 - delt)
  elif delt < -180:
    return 360 + delt
  else:
    return delt