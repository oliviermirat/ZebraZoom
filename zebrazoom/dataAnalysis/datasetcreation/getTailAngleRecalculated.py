import numpy as np
from scipy.interpolate import UnivariateSpline

def getTailAngleRecalculated(curbout, nbFramesTakenIntoAccount, numberOfBendsIncludedForMaxDetect):

  fin = curbout["BoutEnd"] - curbout["BoutStart"] + 1

  numps = 3
  
  headx = curbout["HeadX"]
  heady = curbout["HeadY"]
  tailx = curbout["TailX_VideoReferential"]
  taily = curbout["TailY_VideoReferential"]
  
  tailangles_arr = np.zeros(fin)
  for i in range(0, fin):
    if len(taily[i]) > 3 and len(tailx[i]) > 3:
      ang = np.arctan2(heady[i] - taily[i][-3], headx[i] - tailx[i][-3])*180/np.pi
      ang2 = np.arctan2(heady[i] - taily[i][0], headx[i] - tailx[i][0])*180/np.pi
      delang = ang2 - ang
      if np.abs(delang) < 180:
        tailangles_arr[i] = delang
      elif delang > 180:
        tailangles_arr[i] = delang - 360
      elif delang < -180:
        tailangles_arr[i] = 360 + delang
    else:
      tailangles_arr[i] = 0
      # base = min(len(taily[i]), len(tailx[i])) - 1
    # if i==0:
      # print("yo:")
      # print(heady[i])
      # print(taily[i])
      # print(headx[i])
      # print(tailx[i])
    #print(i,j,ang,ang2,tailangles_arr[i,j])
  
  tailAngle3 = [0]*nbFramesTakenIntoAccount
  sizeTabNotZero = min(fin, nbFramesTakenIntoAccount)
  tailAngle3[0:sizeTabNotZero]  = tailangles_arr[0:sizeTabNotZero]
  
  # Is this necessary ???
  # Bend_Amplitude = curbout["Bend_Amplitude"].copy()
  # Bend_Amplitude.insert(0, 0)
  # Bend_Amplitude.append(0)
  # if numberOfBendsIncludedForMaxDetect == -1 or numberOfBendsIncludedForMaxDetect >= len(Bend_Amplitude):
    # argmax = np.argmax(np.abs(Bend_Amplitude))
  # else:
    # Bend_Amplitude_Array = Bend_Amplitude[0:numberOfBendsIncludedForMaxDetect]
    # argmax               = np.argmax(np.abs(Bend_Amplitude_Array))
  # maxAbsBendValue = Bend_Amplitude[argmax]
  # tailAngle = 0
  # if maxAbsBendValue < 0:
    # tailAngle = (-np.array(curbout["TailAngle_smoothed"])).tolist()
    # instMean  = (-np.array(instMean)).tolist()
  # else:
    # tailAngle = curbout["TailAngle_smoothed"]
  
  return tailAngle3
