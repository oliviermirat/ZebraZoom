import numpy as np
from scipy.interpolate import UnivariateSpline

def getTailAngles(curbout, smoothingFactor, nbFramesTakenIntoAccount, numberOfBendsIncludedForMaxDetect):

  fin = curbout["BoutEnd"] - curbout["BoutStart"] + 1

  if type(curbout["Bend_Timing"]) == list and len(curbout["Bend_Timing"]) > 2:
    
    Bend_Timing = curbout["Bend_Timing"].copy()
    Bend_Timing.insert(0, 1)
    Bend_Timing.append(fin)
    Bend_Amplitude = curbout["Bend_Amplitude"].copy()
    Bend_Amplitude.insert(0, 0)
    Bend_Amplitude.append(0)
    TailAngle = curbout["TailAngle_smoothed"].copy()
    l = len(Bend_Timing) - 1
    
    if numberOfBendsIncludedForMaxDetect == -1 or numberOfBendsIncludedForMaxDetect >= len(Bend_Amplitude):
      argmax = np.argmax(np.abs(Bend_Amplitude))
    else:
      Bend_Amplitude_Array = Bend_Amplitude[0:numberOfBendsIncludedForMaxDetect]
      argmax               = np.argmax(np.abs(Bend_Amplitude_Array))
    
    maxAbsBendValue = Bend_Amplitude[argmax]
    tailAngle = 0
    if maxAbsBendValue < 0:
      tailAngle = (-np.array(curbout["TailAngle_smoothed"])).tolist()
    else:
      tailAngle = curbout["TailAngle_smoothed"]
  
  else:
    
    tailAngle = [0]*fin
  
  tailAngle3 = [0]*nbFramesTakenIntoAccount
  
  sizeTabNotZero = min(fin, nbFramesTakenIntoAccount)
  tailAngle3[0:sizeTabNotZero]  = tailAngle[0:sizeTabNotZero]

  return tailAngle3
