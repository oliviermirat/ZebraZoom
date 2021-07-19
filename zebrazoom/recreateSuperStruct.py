from zebrazoom.code.getImage.getForegroundImage import getForegroundImage
from zebrazoom.code.createSuperStruct import createSuperStruct
from zebrazoom.code.createValidationVideo import createValidationVideo
from zebrazoom.code.getHyperparameters import getHyperparameters

import os
import shutil
import json

def recreateSuperStruct(pathToVideo, videoName, videoExt, configFile, argv):
  
  # Getting parameters
  pathToVideo = sys.argv[1]
  videoName   = sys.argv[2]
  videoExt    = sys.argv[3] # Ext means extension (avi, mp4, etc...)
  configFile  = sys.argv[4]
  videoNameWithExt = videoName + '.' + videoExt

  # Getting hyperparameters
  [hyperparameters, configFile] = getHyperparameters(configFile, videoNameWithExt, pathToVideo + videoNameWithExt, argv)
    
  # Saving the configuration file used
  shutil.copyfile(configFile, hyperparameters["outputFolder"] + videoName + '/configUsed.json')
  
  
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
