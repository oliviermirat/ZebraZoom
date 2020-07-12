import sys
import os
import json
# import mat4py
import scipy.io as io
from scipy.interpolate import UnivariateSpline
import scipy.interpolate as interp
import numpy as np
from scipy.signal import find_peaks
import pandas as pd
import math
import popUpAlgoFollow
# from scipy.interpolate import splprep, splev, splrep

def IsMinOrMax(maxpeaks, minpeaks, val ):
  is_minOrMax = 0
  r = len(maxpeaks)
  for i in range(0,r):
    if maxpeaks[i] == val:
      is_minOrMax=1
  r = len(minpeaks)
  for i in range(0,r):
    if minpeaks[i] == val:
      is_minOrMax=1
  return is_minOrMax

def createSuperStruct(dataPerWell, wellPositions, hyperparameters):

  nbWells                      = hyperparameters["nbWells"]
  wellsAreRectangles           = hyperparameters["wellsAreRectangles"]
  tailAngleSmoothingFactor     = hyperparameters["tailAngleSmoothingFactor"]
  windowForLocalBendMinMaxFind = hyperparameters["windowForLocalBendMinMaxFind"]

  videoDataResults  = {}
  wellPoissMouv     = []
  
  for numWell in range(0,nbWells):
    
    item = {}
    
    j = dataPerWell[numWell]
    
    nbMouv = len(j)
    
    tab  = [[] for idAnimal in range(0, hyperparameters["nbAnimalsPerWell"])]
    # tab2 = []
    
    for i in range(0,nbMouv):
      item = j[i]
      
      angle_raw = item["TailAngle_Raw"]
      
      if len(angle_raw) > 10:
      
        rolling_window = hyperparameters["tailAngleMedianFilter"]
        if rolling_window > 0:
          shift = int(-rolling_window / 2)
          angle_median = np.array(pd.Series(angle_raw).rolling(rolling_window).median())
          angle_median = np.roll(angle_median, shift)
          for ii in range(0, rolling_window):
            angle_median[ii] = angle_raw[ii]
            # jj = rolling_window - 1 - ii
            # if math.isnan(angle_median[jj]):
              # angle_median[jj] = angle_median[jj+1]
          for ii in range(len(angle_median)-rolling_window,len(angle_median)):
            angle_median[ii] = angle_raw[ii]
            # if math.isnan(angle_median[ii]):
              # angle_median[ii] = angle_median[ii-1]
        else:
          angle_median = angle_raw
          
        # rolling_window = 3
        # if rolling_window > 0:
          # shift = int(-rolling_window / 2)
          # angle_median2 = np.array(pd.Series(angle_raw).rolling(rolling_window).median())
          # angle_median2 = np.roll(angle_median2, shift)
          # for ii in range(0, rolling_window):
            # jj = rolling_window - 1 - ii
            # if math.isnan(angle_median2[jj]):
              # angle_median2[jj] = angle_median2[jj+1]
          # for ii in range(len(angle_median2)-rolling_window,len(angle_median2)):
            # if math.isnan(angle_median2[ii]):
              # angle_median2[ii] = angle_median2[ii-1]
        # else:
          # angle_median2 = angle_raw
      
        x = np.linspace(0, 1, len(angle_median))
        
        # if True: # Original method
        s = UnivariateSpline(x, angle_median, s=tailAngleSmoothingFactor)
        TailAngle_smoothed = s(x) 
        # else:
          # tck = splrep(x, angle_median, s=0.01)
          # TailAngle_smoothed = splev(x, tck)
        
        # angle_median2 = np.zeros((len(angle_median),1))
        # angle_median2[:,0] = angle_median
        # print(angle_median2)

        # angle_median2 = np.zeros((1, len(angle_median)))
        # angle_median2[0,:] = angle_median
        # print(angle_median2)
        
        # angle_median2 = np.array(angle_median)
        # print(angle_median2)
        
        # tck, u = interp.splprep(angle_median2, s=0)
        # u = np.linspace(0, 1, len(angle_median2))
        # TailAngle_smoothed = np.column_stack(interp.splev(u, tck))
        
        item['TailAngle_smoothed'] = TailAngle_smoothed.tolist()
      else:
        TailAngle_smoothed = np.array(angle_raw)
        item['TailAngle_smoothed'] = angle_raw
      
      # maxDiffPeakToPeak = 0
      # for k in range(0, len(TailAngle_smoothed)):
        # wind = hyperparameters["windowForLocalBendMinMaxFind"]
        # if (k - wind >= 0) and (k + wind < len(TailAngle_smoothed)):
          # maxAngle = max([TailAngle_smoothed[k + l] for l in range(-wind, wind+1)])
          # minAngle = min([TailAngle_smoothed[k + l] for l in range(-wind, wind+1)])
          # if (maxAngle - minAngle > maxDiffPeakToPeak):
            # maxDiffPeakToPeak = maxAngle - minAngle
      
      if hyperparameters['extractAdvanceZebraParameters']:
      
        maxDiffPeakToPeak = 0
        maxAngle = max([TailAngle_smoothed[l] for l in range(0, len(TailAngle_smoothed))])
        minAngle = min([TailAngle_smoothed[l] for l in range(0, len(TailAngle_smoothed))])
        maxDiffPeakToPeak = maxAngle - minAngle
        
        minProminenceForBendsDetect = hyperparameters["minProminenceForBendsDetect"]
        if minProminenceForBendsDetect == -1:
          minProminenceForBendsDetect = maxDiffPeakToPeak / 10
          
        # TailAngle_smoothed = angle_median2
        maxpeaks, properties = find_peaks(TailAngle_smoothed, prominence=minProminenceForBendsDetect, width=hyperparameters["windowForLocalBendMinMaxFind"])
        minpeaks, properties = find_peaks(-TailAngle_smoothed, prominence=minProminenceForBendsDetect, width=hyperparameters["windowForLocalBendMinMaxFind"])
        
        if (len(minpeaks) + len(maxpeaks) >= hyperparameters["minNbPeaksForBoutDetect"] ):
        
          ind = 1
          minDiffBetweenSubsequentBendAmp = hyperparameters["minDiffBetweenSubsequentBendAmp"]
          
          Bend_Timing = []
          lastTailValue = 100000
          # Bend_TimingAbsolute(1)=floor((debut+fin)/2)

          for i in range(item['BoutStart'],item['BoutEnd']+1):
          
            minOrMax = IsMinOrMax(maxpeaks, minpeaks, i - item['BoutStart'] )
            
            if minOrMax:
              if (abs(lastTailValue - TailAngle_smoothed[i - item['BoutStart'] ]) > minDiffBetweenSubsequentBendAmp):
                Bend_Timing.append(i - item['BoutStart'] + 1) 
                lastTailValue = TailAngle_smoothed[i- item['BoutStart'] ]
            
            if (len(Bend_Timing) == 1) and (abs(lastTailValue) < hyperparameters["minFirstBendValue"]):
              Bend_Timing = []
              
          if len(Bend_Timing) > 3:
            Bend_Timing2 = []
            if hyperparameters["doubleCheckBendMinMaxStatus"]:
              # Checking first bend
              bendId = 0
              ind2 = Bend_Timing[bendId]
              ind3 = Bend_Timing[bendId+1]
              cond1 = (TailAngle_smoothed[0] < TailAngle_smoothed[ind2-1]) and (TailAngle_smoothed[ind3-1] < TailAngle_smoothed[ind2-1])
              cond2 = (TailAngle_smoothed[0] > TailAngle_smoothed[ind2-1]) and (TailAngle_smoothed[ind3-1] > TailAngle_smoothed[ind2-1])
              if cond1 or cond2:
                Bend_Timing2.append(ind2)
              # Checking bends in the middle
              for bendId in range(1, len(Bend_Timing)-1):
                ind1 = Bend_Timing[bendId-1]
                ind2 = Bend_Timing[bendId]
                ind3 = Bend_Timing[bendId+1]
                cond1 = (TailAngle_smoothed[ind1-1] < TailAngle_smoothed[ind2-1]) and (TailAngle_smoothed[ind3-1] < TailAngle_smoothed[ind2-1])
                cond2 = (TailAngle_smoothed[ind1-1] > TailAngle_smoothed[ind2-1]) and (TailAngle_smoothed[ind3-1] > TailAngle_smoothed[ind2-1])
                if cond1 or cond2:
                  Bend_Timing2.append(ind2)
              # Checking last bend
              bendId = len(Bend_Timing)-1
              ind1 = Bend_Timing[bendId-1]
              ind2 = Bend_Timing[bendId]
              n = len(TailAngle_smoothed)-1
              cond1 = (TailAngle_smoothed[ind1-1] < TailAngle_smoothed[ind2-1]) and (TailAngle_smoothed[n] < TailAngle_smoothed[ind2-1])
              cond2 = (TailAngle_smoothed[ind1-1] > TailAngle_smoothed[ind2-1]) and (TailAngle_smoothed[n] > TailAngle_smoothed[ind2-1])
              if cond1 or cond2:
                Bend_Timing2.append(ind2)
              Bend_Timing = Bend_Timing2
          
          if hyperparameters["removeFirstSmallBend"] and len(Bend_Timing) > 1:
            ind1 = Bend_Timing[0]
            ind2 = Bend_Timing[1]
            if abs(TailAngle_smoothed[ind1-1]) < abs(TailAngle_smoothed[ind2-1]) / hyperparameters["removeFirstSmallBend"]:
              Bend_Timing.pop(0)
          
          item['Bend_Timing'] = Bend_Timing
          
          Bend_TimingAbsolute = [val + item['BoutStart'] for val in Bend_Timing]
          
          item['Bend_TimingAbsolute'] = Bend_TimingAbsolute
          
          Bend_Amplitude = [TailAngle_smoothed[val-1] for val in Bend_Timing]
          item['Bend_Amplitude'] = Bend_Amplitude
            
          #####
          
          tab[item["AnimalNumber"]].append(item)
      else:
        item['TailAngle_raw'] = []
        item['TailAngle_smoothed'] = []
        tab[item["AnimalNumber"]].append(item)
    
    # tab2.append(tab)
    wellPoissMouv.append(tab)
  
  videoDataResults['wellPoissMouv'] = wellPoissMouv
  videoDataResults['wellPositions'] = wellPositions
  videoDataResults['firstFrame']    = hyperparameters["firstFrame"]
  
  path = hyperparameters["outputFolder"] + hyperparameters["videoName"] + '/results_' + hyperparameters["videoName"]
  
  # io.savemat(path + '.mat', videoDataResults)
  
  with open(path + '.txt', 'w') as outfile:
    json.dump(videoDataResults, outfile)
    
  if (hyperparameters["freqAlgoPosFollow"] != 0):
    print("Super Structure created")
  if hyperparameters["popUpAlgoFollow"]:
    popUpAlgoFollow.prepend("Super Structure created")

  return videoDataResults
  

# saving results in matlab file
# io.savemat('results.mat', videoDataResults2)


