import sys
# sys.path.insert(1, './code/')
# sys.path.insert(1, './code/tracking/')
# sys.path.insert(1, './code/getImage/')

from getForegroundImage import getForegroundImage
from createSuperStruct import createSuperStruct
from createValidationVideo import createValidationVideo
from getHyperparameters import getHyperparameters

import os
import shutil
import json
# import pdb

# Getting parameters
# if len(sys.argv) > 4:
  # pathToVideo = sys.argv[1]
  # videoName   = sys.argv[2]
  # videoExt    = sys.argv[3] # Ext means extension (avi, mp4, etc...)
  # configFile  = sys.argv[4]
  # argv        = sys.argv
# else:
  # configFile  = ""

def recreateSuperStruct(pathToVideo, videoName, videoExt, configFile, argv):
  
  # Getting parameters
  pathToVideo = sys.argv[1]
  videoName   = sys.argv[2]
  videoExt    = sys.argv[3] # Ext means extension (avi, mp4, etc...)
  configFile  = sys.argv[4]
  videoNameWithExt = videoName + '.' + videoExt

  # Getting hyperparameters
  hyperparameters = getHyperparameters(configFile, videoNameWithExt, pathToVideo + videoNameWithExt, argv)
    
  # Saving the configuration file used
  shutil.copyfile(configFile, hyperparameters["outputFolder"] + videoName + '/configUsed.txt')
  
  
  with open(hyperparameters["outputFolder"] + videoName + '/results_' + videoName + '.txt') as inires:
    iniRes = json.load(inires)
  
  # Getting well positions
  wellPositions = iniRes["wellPositions"]
  
  # Sorting wells after the end of the parrallelized calls end
  dataPerWell = iniRes["wellPoissMouv"]
  n = len(dataPerWell)
  for i in range(0,n):
    dataPerWell[i] = dataPerWell[i][0]
  
  # Creating super structure
  superStruct = createSuperStruct(dataPerWell, wellPositions, hyperparameters)
  if (hyperparameters["freqAlgoPosFollow"] != 0):
    print("superStruct created")
    
  if hyperparameters["createValidationVideo"]:
    # Creating validation video
    infoFrame = createValidationVideo(pathToVideo + videoNameWithExt, superStruct, hyperparameters)


# if __name__ == '__main__':

  # __spec__ = "ModuleSpec(name='builtins', loader=<class '_frozen_importlib.BuiltinImporter'>)"
  
  # recreateSuperStruct(pathToVideo, videoName, videoExt, configFile, argv)
