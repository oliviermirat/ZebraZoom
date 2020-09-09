import numpy as np
from scipy.interpolate import UnivariateSpline

def getDynamicParameters(curbout, smoothingFactor, nbFramesTakenIntoAccount, numberOfBendsIncludedForMaxDetect):

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

    instAbs   = [0]*l
    instFreq  = [0]*l
    instAmp   = [0]*l
    instMean  = [0]*l

    for j in range(0, l):
      instAbs[j]  = (Bend_Timing[j+1] + Bend_Timing[j]) / 2
      instFreq[j] = 1 / (Bend_Timing[j+1] - Bend_Timing[j])
      instAmp[j]  = abs(Bend_Amplitude[j+1] - Bend_Amplitude[j])
      # instMean[j] = abs(np.mean(TailAngle[Bend_Timing[j]:Bend_Timing[j+1]]))
      instMean[j] = np.mean(TailAngle[Bend_Timing[j]:Bend_Timing[j+1]])
    
    instAbs.insert(0, 1)
    instAbs.append(10*fin)
    instFreq.insert(0, 0)
    instFreq.append(0)
    instAmp.insert(0, 0)
    instAmp.append(0)
    instMean.insert(0, 0)
    instMean.append(0)
    
    if numberOfBendsIncludedForMaxDetect == -1 or numberOfBendsIncludedForMaxDetect >= len(Bend_Amplitude):
      argmax = np.argmax(np.abs(Bend_Amplitude))
    else:
      Bend_Amplitude_Array = Bend_Amplitude[0:numberOfBendsIncludedForMaxDetect]
      argmax               = np.argmax(np.abs(Bend_Amplitude_Array))
    
    maxAbsBendValue = Bend_Amplitude[argmax]
    if maxAbsBendValue < 0:
      instMean  = (-np.array(instMean)).tolist()
  
    x = np.linspace(1, fin, fin)
    s = UnivariateSpline(instAbs, instFreq, s=smoothingFactor)
    instFreq2 = s(x).tolist()
    s = UnivariateSpline(instAbs, instAmp,  s=smoothingFactor)
    instAmp2 = s(x).tolist()
    s = UnivariateSpline(instAbs, instMean, s=smoothingFactor)
    instMean2 = s(x).tolist()
  
  else:
    
    instFreq2 = [0]*fin
    instAmp2  = [0]*fin
    instMean2 = [0]*fin
    
  instFreq3  = [0]*nbFramesTakenIntoAccount
  instAmp3   = [0]*nbFramesTakenIntoAccount
  instMean3  = [0]*nbFramesTakenIntoAccount
  
  sizeTabNotZero = min(fin, nbFramesTakenIntoAccount)
  instFreq3[0:sizeTabNotZero] = instFreq2[0:sizeTabNotZero]
  instAmp3[0:sizeTabNotZero]  = instAmp2[0:sizeTabNotZero]
  instMean3[0:sizeTabNotZero] = instMean2[0:sizeTabNotZero]

  dynamicParameters = instFreq3 + instAmp3 + instMean3

  return dynamicParameters
