from scipy.optimize import linear_sum_assignment
import zebrazoom.dataAPI as dataAPI
import matplotlib.pyplot as plt
from scipy import stats
import pandas as pd
import numpy as np
import shutil
import math
import h5py
import os


def detectBouts(videoName: str, nbWells: int, nbAnimalsPerWell: int, self):

  for numWell in range(nbWells):
    numAnimal = 0
    dataForEachAnimal = []
    for numAnimal in range(nbAnimalsPerWell):
      data = dataAPI.getDataPerTimeInterval(videoName, numWell, numAnimal, None, None, "HeadPos")
      dataForEachAnimal.append(data)
  
    for numAnimal in range(nbAnimalsPerWell):
      
      # data = dataAPI.getDataPerTimeInterval(videoName, numWell, numAnimal, None, None, "HeadPos")
      dataForAnimal = dataForEachAnimal[numAnimal]
    
      # for numAnimal, dataForAnimal in enumerate(data):
        
      frameDistance = self._hyperparameters["frameGapComparision"]
      auDessus = [int(math.sqrt(sum((dataForAnimal[i+frameDistance] - coords) ** 2)) >= self._hyperparameters["coordinatesOnlyBoutDetectionMinDistDataAPI"]) for i, coords in enumerate(dataForAnimal[:-frameDistance])]
      auDessus.extend([0] * frameDistance)
      
      auDessus2 = np.copy(auDessus)
      windowGap = self._hyperparameters["fillGapFrameNb"]
      if windowGap:
        for i in range(windowGap,nbFrames-windowGap):
          if auDessus[i] == 0:
            j = i - windowGap
            while (auDessus[j] == 0) and (j < i + windowGap):
              j = j + 1
            if j < i + windowGap:
              j = j + 1;
              while (auDessus[j] == 0) and (j < i + windowGap):
                j = j + 1;
              if auDessus[j] > 0:
                for k in range(i - windowGap, i + windowGap):
                  auDessus2[k] = 1
    
    numWell = 0
    numAnimal = 0
    with h5py.File(self._hyperparameters['H5filename'], 'a') as results:
      listOfBouts = results.require_group(f"dataForWell{numWell}/dataForAnimal{numAnimal}/listOfBouts")
      inBout = 0
      nbFrames = len(dataForAnimal)
      boutIdx = 0
      for i in range(0, nbFrames):
        if (inBout == 0) and (auDessus2[i] == 1):
          firstFrame = i
          inBout = 1
        if (inBout == 1) and ((auDessus2[i] == 0) or (i == nbFrames-1)):
          if firstFrame != (i - 1):
            listOfBouts.attrs['numberOfBouts'] = boutIdx + 1
            boutGroup = listOfBouts.require_group(f'bout{boutIdx}')
            boutGroup.attrs["BoutStart"] = self._hyperparameters["firstFrame"] + firstFrame
            boutGroup.attrs["BoutEnd"]   = self._hyperparameters["firstFrame"] + i - 1
            boutIdx += 1
          inBout = 0
