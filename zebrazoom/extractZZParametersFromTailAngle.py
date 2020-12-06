import sys
sys.path.insert(1, './')
sys.path.insert(1, './code/')
sys.path.insert(1, './code/GUI/')
sys.path.insert(1, './code/getImage/')
sys.path.insert(1, './code/trackingFolder/')
sys.path.insert(1, './code/trackingFolder/headTrackingHeadingCalculationFolder/')
sys.path.insert(1, './code/trackingFolder/tailTrackingFunctionsFolder/')
sys.path.insert(1, './code/trackingFolder/tailTrackingFunctionsFolder/tailTrackingExtremityDetectFolder/')
sys.path.insert(1, './code/trackingFolder/tailTrackingFunctionsFolder/tailTrackingExtremityDetectFolder/findTailExtremeteFolder/')

from extractParameters import extractParameters
from getHyperparameters import getHyperparameters
from createSuperStruct import createSuperStruct
import numpy as np
import shutil
import os

def extractZZParametersFromTailAngle(videoName, tailAngle):
  
  hyperparameters = getHyperparameters({"noChecksForBoutSelectionInExtractParams": 1, "windowForLocalBendMinMaxFind": 3, "thresAngleBoutDetect": 0.1, "nbWells": 1}, videoName + '.avi', '', [])
  
  if os.path.exists(hyperparameters["outputFolder"] + videoName):
    shutil.rmtree(hyperparameters["outputFolder"] + videoName)
  while True:
    try:
      os.mkdir(hyperparameters["outputFolder"] + videoName)
      break
    except OSError as e:
      print("waiting inside except")
      time.sleep(0.1)
    else:
      print("waiting")
      time.sleep(0.1)
  
  n = len(tailAngle)
  nbTailPoints = 2
  
  trackingHeadTailAllAnimals = np.zeros((1, n, nbTailPoints, 2))
  trackingHeadingAllAnimals  = np.zeros((1, n))
  trackingHeadTailAllAnimals[:] = np.nan
  trackingHeadingAllAnimals[:]  = np.nan
  
  trackingData = [trackingHeadTailAllAnimals, trackingHeadingAllAnimals, 0, 0]
  
  parameters = extractParameters(trackingData, 0, hyperparameters, 0, 0, 0, tailAngle)
  
  superStruct = createSuperStruct([parameters], [], hyperparameters)
