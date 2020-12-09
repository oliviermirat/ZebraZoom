from zebrazoom.code.findWells import findWells
from zebrazoom.code.getBackground import getBackground
from zebrazoom.code.getImage.getForegroundImage import getForegroundImage
from zebrazoom.code.trackingFolder.tracking import tracking
from zebrazoom.code.extractParameters import extractParameters
from zebrazoom.code.createSuperStruct import createSuperStruct
from zebrazoom.code.createValidationVideo import createValidationVideo
from zebrazoom.code.getHyperparameters import getHyperparameters
from zebrazoom.code.generateAllTimeTailAngleGraph import generateAllTimeTailAngleGraph
from zebrazoom.code.perBoutOutput import perBoutOutput
import zebrazoom.code.popUpAlgoFollow as popUpAlgoFollow

import sys
import pickle
import os
import shutil
import time

from zebrazoom.code.vars import getGlobalVariables
globalVariables = getGlobalVariables()
import multiprocessing as mp
if globalVariables["mac"]:
  mp.set_start_method('spawn', force=True)
from multiprocessing import Process

output = mp.Queue()

# Does the tracking and then the extraction of parameters
def getParametersForWell(videoPath,background,wellNumber,wellPositions,output,previouslyAcquiredTrackingDataForDebug,hyperparameters, videoName):
  if hyperparameters["debugPauseBetweenTrackAndParamExtract"] == "noDebug":
    # Normal execution process
    trackingData = tracking(videoPath,background,wellNumber,wellPositions,hyperparameters, videoName)
    parameters = extractParameters(trackingData, wellNumber, hyperparameters, videoPath, wellPositions, background)
    output.put([wellNumber,parameters,[]])
  elif hyperparameters["debugPauseBetweenTrackAndParamExtract"] == "justSaveTrackData":
    # Extracing tracking data, saving it, and that's it
    trackingData = tracking(videoPath,background,wellNumber,wellPositions,hyperparameters, videoName)
    output.put([wellNumber,[],trackingData])
  elif hyperparameters["debugPauseBetweenTrackAndParamExtract"] == "saveTrackDataAndExtractParam":
    # Extracing tracking data, saving it, and continuing normal execution
    trackingData = tracking(videoPath,background,wellNumber,wellPositions,hyperparameters, videoName)
    parameters = extractParameters(trackingData, wellNumber, hyperparameters, videoPath, wellPositions, background)
    output.put([wellNumber,parameters,trackingData])
  else: # hyperparameters["debugPauseBetweenTrackAndParamExtract"] == "justExtractParamFromPreviousTrackData"
    # Reloading previously tracked data and using it to extract parameters
    trackingData = previouslyAcquiredTrackingDataForDebug[wellNumber]
    parameters = extractParameters(trackingData, wellNumber, hyperparameters, videoPath, wellPositions, background)
    output.put([wellNumber,parameters,[]])


# Getting parameters
if len(sys.argv) > 2:
  pathToVideo = sys.argv[1]
  videoName   = sys.argv[2]
  videoExt    = sys.argv[3] # Ext means extension (avi, mp4, etc...)
  configFile  = sys.argv[4]
  argv        = sys.argv
else:
  configFile  = ""


def mainZZ(pathToVideo, videoName, videoExt, configFile, argv):
  
  videoNameWithExt = videoName + '.' + videoExt
  previouslyAcquiredTrackingDataForDebug = []

  # Getting hyperparameters
  hyperparameters = getHyperparameters(configFile, videoNameWithExt, os.path.join(pathToVideo, videoNameWithExt), argv)
  
  outputFolderVideo = os.path.join(hyperparameters["outputFolder"], videoName)
  
  # Launching GUI algoFollower if necessary
  if hyperparameters["popUpAlgoFollow"]:
    popUpAlgoFollow.initialise()
    popUpAlgoFollow.prepend("starting ZebraZoom analysis on " + videoName)

  if hyperparameters["debugPauseBetweenTrackAndParamExtract"] == "justExtractParamFromPreviousTrackData":
    # Reloading previously extracted tracking data if debugging option selected
    outfile = open(os.path.join(outputFolderVideo, 'intermediaryTracking.txt'),'rb')
    previouslyAcquiredTrackingDataForDebug = pickle.load(outfile)
    outfile.close()
  else:
    # Creating output folder
    if not(hyperparameters["reloadWellPositions"]) and not(hyperparameters["reloadBackground"]):
      if os.path.exists(outputFolderVideo):
        shutil.rmtree(outputFolderVideo)
      while True:
        try:
          os.mkdir(outputFolderVideo)
          break
        except OSError as e:
          print("waiting inside except")
          time.sleep(0.1)
        else:
          print("waiting")
          time.sleep(0.1)
    
  # Saving the configuration file used
  if type(configFile) == str:
    print(os.path.join(outputFolderVideo, 'configUsed.txt'), outputFolderVideo)
    shutil.copyfile(configFile, os.path.join(outputFolderVideo, 'configUsed.txt'))

  # Getting well positions
  if hyperparameters["headEmbeded"]:
    wellPositions = [{"topLeftX":0, "topLeftY":0, "lengthX": hyperparameters["videoWidth"], "lengthY": hyperparameters["videoHeight"]}]
  else:
    print("start find wells")
    if hyperparameters["reloadWellPositions"]:
      outfile = open(os.path.join(outputFolderVideo, 'intermediaryWellPosition.txt'),'rb')
      wellPositions = pickle.load(outfile)
    else:
      outfile = open(os.path.join(outputFolderVideo, 'intermediaryWellPosition.txt'),'wb')
      wellPositions = findWells(os.path.join(pathToVideo, videoNameWithExt), hyperparameters)
      pickle.dump(wellPositions,outfile)
    outfile.close()
    
  # Getting background
  if hyperparameters["headEmbeded"] and hyperparameters["headEmbededRemoveBack"] == 0 and hyperparameters["headEmbededAutoSet_BackgroundExtractionOption"] == 0 and hyperparameters["adjustHeadEmbededTracking"] == 0:
    background = []
  else:
    print("start get background")
    if hyperparameters["reloadBackground"]:
      outfile = open(os.path.join(outputFolderVideo, 'intermediaryBackground.txt'),'rb')
      background = pickle.load(outfile)
      print("Background Reloaded")
    else:
      outfile = open(os.path.join(outputFolderVideo, 'intermediaryBackground.txt'),'wb')
      background = getBackground(os.path.join(pathToVideo, videoNameWithExt), hyperparameters)
      pickle.dump(background,outfile)
    outfile.close()
  if hyperparameters["exitAfterBackgroundExtraction"]:
    raise ValueError
  
  # Tracking and extraction of parameters
  if globalVariables["noMultiprocessing"] == 0:
    if hyperparameters["onlyTrackThisOneWell"] == -1:
      # for all wells, in parallel
      processes = []
      for wellNumber in range(0,hyperparameters["nbWells"]):
        p = Process(target=getParametersForWell, args=(os.path.join(pathToVideo, videoNameWithExt), background, wellNumber, wellPositions, output, previouslyAcquiredTrackingDataForDebug, hyperparameters, videoName))
        p.start()
        processes.append(p)
    else:
      # for just one well
      processes = [1]
      getParametersForWell(os.path.join(pathToVideo, videoNameWithExt), background, hyperparameters["onlyTrackThisOneWell"], wellPositions, output, previouslyAcquiredTrackingDataForDebug, hyperparameters, videoName)
  else:
    if hyperparameters["onlyTrackThisOneWell"] == -1:
      processes = [1 for i in range(0, hyperparameters["nbWells"])]
      for wellNumber in range(0,hyperparameters["nbWells"]):
        getParametersForWell(os.path.join(pathToVideo, videoNameWithExt), background, wellNumber, wellPositions, output, previouslyAcquiredTrackingDataForDebug, hyperparameters, videoName)
    else:
      processes = [1]
      getParametersForWell(os.path.join(pathToVideo, videoNameWithExt), background, hyperparameters["onlyTrackThisOneWell"], wellPositions, output, previouslyAcquiredTrackingDataForDebug, hyperparameters, videoName)
  
  # Sorting wells after the end of the parallelized calls end
  dataPerWellUnsorted = [output.get() for p in processes]
  paramDataPerWell = [[]] * (hyperparameters["nbWells"])
  trackingDataPerWell = [[]] * (hyperparameters["nbWells"])
  for data in dataPerWellUnsorted:
    paramDataPerWell[data[0]]    = data[1]
    trackingDataPerWell[data[0]] = data[2]
  if hyperparameters["onlyTrackThisOneWell"] == -1 and globalVariables["noMultiprocessing"] == 0:
    for p in processes:
      p.join()
  if (hyperparameters["freqAlgoPosFollow"] != 0):
    print("processes joined")

  if (hyperparameters["debugPauseBetweenTrackAndParamExtract"] == "saveTrackDataAndExtractParam") or (hyperparameters["debugPauseBetweenTrackAndParamExtract"] == "justSaveTrackData"):
    # saving tracking results for future uses
    outfile = open(os.path.join(outputFolderVideo, 'intermediaryTracking.txt'),'wb')
    pickle.dump(trackingDataPerWell,outfile)
    outfile.close()
    
  if hyperparameters["debugPauseBetweenTrackAndParamExtract"] != "justSaveTrackData":
    # Creating super structure
    superStruct = createSuperStruct(paramDataPerWell, wellPositions, hyperparameters)
  
  if hyperparameters["generateAllTimeTailAngleGraph"]:
    generateAllTimeTailAngleGraph(outputFolderVideo, superStruct, hyperparameters["generateAllTimeTailAngleGraphLineWidth"])
    
  if hyperparameters["createValidationVideo"]:
    # Creating validation video
    infoFrame = createValidationVideo(os.path.join(pathToVideo, videoNameWithExt), superStruct, hyperparameters)
  
  if hyperparameters["perBoutOutput"]:
    # Creating additional validation output per bout
    perBoutOutput(superStruct, hyperparameters, videoName)

  if hyperparameters["popUpAlgoFollow"]:
    popUpAlgoFollow.prepend("ZebraZoom Analysis finished for " + videoName)
    # popUpAlgoFollow.prepend("")
    # if hyperparameters["closePopUpWindowAtTheEnd"]:
      # popUpAlgoFollow.prepend("ZebraZoom Analysis all finished")

