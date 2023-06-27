from zebrazoom.code.extractParameters import extractParameters
from zebrazoom.code.getHyperparameters import getHyperparameters
from zebrazoom.code.createSuperStruct import createSuperStruct
import numpy as np
import shutil
import os

def extractZZParametersFromTailAngle(videoName, tailAngle):
  
  [hyperparameters, config] = getHyperparameters({"noChecksForBoutSelectionInExtractParams": 1, "windowForLocalBendMinMaxFind": 3, "thresAngleBoutDetect": 0.1, "nbWells": 1}, videoName + '.avi', '', [])

  n = len(tailAngle)
  nbTailPoints = 2
  
  trackingHeadTailAllAnimals = np.zeros((1, n, nbTailPoints, 2))
  trackingHeadingAllAnimals  = np.zeros((1, n))
  trackingHeadTailAllAnimals[:] = np.nan
  trackingHeadingAllAnimals[:]  = np.nan
  
  trackingData = [trackingHeadTailAllAnimals, trackingHeadingAllAnimals, 0, 0]
  
  parameters = extractParameters(trackingData, 0, hyperparameters, 0, 0, 0, tailAngle)
  
  superStruct = createSuperStruct([parameters], [], hyperparameters)
