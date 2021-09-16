from zebrazoom.code.findWells import findWells
from zebrazoom.code.getBackground import getBackground
from zebrazoom.code.getImage.getForegroundImage import getForegroundImage
from zebrazoom.code.trackingFolder.tracking import tracking
from zebrazoom.code.extractParameters import extractParameters
from zebrazoom.code.createSuperStruct import createSuperStruct
from zebrazoom.code.createValidationVideo import createValidationVideo
from zebrazoom.code.getHyperparameters import getHyperparameters
import zebrazoom.code.popUpAlgoFollow as popUpAlgoFollow
from zebrazoom.code.dataPostProcessing.dataPostProcessing import dataPostProcessing
from zebrazoom.code.fasterMultiprocessing import fasterMultiprocessing

import sys
import pickle
import os
import shutil
import time
import cv2
import json

from zebrazoom.code.vars import getGlobalVariables
globalVariables = getGlobalVariables()
import multiprocessing as mp
if globalVariables["mac"]:
  mp.set_start_method('spawn', force=True)
from multiprocessing import Process

output = mp.Queue()

# Does the tracking and then the extraction of parameters
def getParametersForWell(videoPath,background,wellNumber,wellPositions,output,previouslyAcquiredTrackingDataForDebug,hyperparameters, videoName, dlModel):
  if hyperparameters["debugPauseBetweenTrackAndParamExtract"] == "noDebug":
    # Normal execution process
    trackingData = tracking(videoPath,background,wellNumber,wellPositions,hyperparameters, videoName, dlModel)
    parameters = extractParameters(trackingData, wellNumber, hyperparameters, videoPath, wellPositions, background)
    output.put([wellNumber,parameters,[]])
  elif hyperparameters["debugPauseBetweenTrackAndParamExtract"] == "justSaveTrackData":
    # Extracing tracking data, saving it, and that's it
    trackingData = tracking(videoPath,background,wellNumber,wellPositions,hyperparameters, videoName, dlModel)
    output.put([wellNumber,[],trackingData])
  elif hyperparameters["debugPauseBetweenTrackAndParamExtract"] == "saveTrackDataAndExtractParam":
    # Extracing tracking data, saving it, and continuing normal execution
    trackingData = tracking(videoPath,background,wellNumber,wellPositions,hyperparameters, videoName, dlModel)
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
  [hyperparameters, configFile] = getHyperparameters(configFile, videoNameWithExt, os.path.join(pathToVideo, videoNameWithExt), argv)
  
  # Checking first frame and last frame value
  cap   = cv2.VideoCapture(os.path.join(pathToVideo, videoNameWithExt))
  nbFrames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
  cap.release()
  if hyperparameters["firstFrame"] < 0:
    print("Error: The parameter 'firstFrame' in your configuration file is too small")
    raise NameError("Error: The parameter 'firstFrame' in your configuration file is too small")
  if hyperparameters["firstFrame"] > nbFrames:
    print("Error: The parameter 'firstFrame' in your configuration file is too big")
    raise NameError("Error: The parameter 'firstFrame' in your configuration file is too big")
  if (hyperparameters["lastFrame"] < 0) or (hyperparameters["lastFrame"] <= hyperparameters["firstFrame"]):
    print("Error: The parameter 'lastFrame' in your configuration file is too small")
    raise NameError("Error: The parameter 'lastFrame' in your configuration file is too small")
  if hyperparameters["lastFrame"] > nbFrames:
    print("Error: The parameter 'lastFrame' in your configuration file is too big")
    raise NameError("Error: The parameter 'lastFrame' in your configuration file is too big")
  
  # Setting output folder
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
    if not(hyperparameters["reloadWellPositions"]) and not(hyperparameters["reloadBackground"]) and not(os.path.exists(os.path.join(outputFolderVideo, 'intermediaryWellPositionReloadNoMatterWhat.txt'))) and not(hyperparameters["dontDeleteOutputFolderIfAlreadyExist"]):
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
  with open(os.path.join(outputFolderVideo, 'configUsed.json'), 'w') as outfile:
    json.dump(configFile, outfile)
  

  # Getting well positions
  if hyperparameters["headEmbeded"]:
    wellPositions = [{"topLeftX":0, "topLeftY":0, "lengthX": hyperparameters["videoWidth"], "lengthY": hyperparameters["videoHeight"]}]
  else:
    print("start find wells")
    if hyperparameters["saveWellPositionsToBeReloadedNoMatterWhat"]:
      outfile = open(os.path.join(outputFolderVideo, 'intermediaryWellPositionReloadNoMatterWhat.txt'),'wb')
      wellPositions = findWells(os.path.join(pathToVideo, videoNameWithExt), hyperparameters)
      pickle.dump(wellPositions,outfile)
    elif os.path.exists(os.path.join(outputFolderVideo, 'intermediaryWellPositionReloadNoMatterWhat.txt')):
      outfile = open(os.path.join(outputFolderVideo, 'intermediaryWellPositionReloadNoMatterWhat.txt'), 'rb')
      wellPositions = pickle.load(outfile)
    elif hyperparameters["reloadWellPositions"]:
      outfile = open(os.path.join(outputFolderVideo, 'intermediaryWellPosition.txt'), 'rb')
      wellPositions = pickle.load(outfile)
    elif hyperparameters["reloadWellPositionsFromFileInZZoutputIfItExistSaveInItOtherwise"] and os.path.exists(os.path.join(hyperparameters["outputFolder"], 'wellPosition.txt')):
      outfile = open(os.path.join(hyperparameters["outputFolder"], 'wellPosition.txt'), 'rb')
      wellPositions = pickle.load(outfile)
    else:
      outfile = open(os.path.join(outputFolderVideo, 'intermediaryWellPosition.txt'),'wb')
      wellPositions = findWells(os.path.join(pathToVideo, videoNameWithExt), hyperparameters)
      pickle.dump(wellPositions,outfile)
      if hyperparameters["reloadWellPositionsFromFileInZZoutputIfItExistSaveInItOtherwise"]:
        outfile2 = open(os.path.join(hyperparameters["outputFolder"], 'wellPosition.txt'), 'wb')
        pickle.dump(wellPositions, outfile2)
        outfile2.close()
    outfile.close()
  if int(hyperparameters["exitAfterWellsDetection"]):
    print("exitAfterWellsDetection")
    if hyperparameters["popUpAlgoFollow"]:
      popUpAlgoFollow.prepend("ZebraZoom Analysis finished for " + videoName)
    raise ValueError
    
  # Getting background
  if hyperparameters["backgroundSubtractorKNN"] or (hyperparameters["headEmbeded"] and hyperparameters["headEmbededRemoveBack"] == 0 and hyperparameters["headEmbededAutoSet_BackgroundExtractionOption"] == 0 and hyperparameters["adjustHeadEmbededTracking"] == 0) or hyperparameters["trackingDL"]:
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
    print("exitAfterBackgroundExtraction")
    raise ValueError
  
  # Reloading DL model for tracking with DL
  if hyperparameters["trackingDL"]:
    from zebrazoom.code.deepLearningFunctions.loadDLmodel import loadDLmodel
    dlModel = loadDLmodel(hyperparameters["trackingDL"])
  else:
    dlModel = 0
  
  # Tracking and extraction of parameters
  if hyperparameters["fasterMultiprocessing"] == 1:
    processes = -1
    output2 = fasterMultiprocessing(os.path.join(pathToVideo, videoNameWithExt), background, wellPositions, [], hyperparameters, videoName)
  else:
    if globalVariables["noMultiprocessing"] == 0:
      if hyperparameters["onlyTrackThisOneWell"] == -1:
        # for all wells, in parallel
        processes = []
        for wellNumber in range(0,hyperparameters["nbWells"]):
          p = Process(target=getParametersForWell, args=(os.path.join(pathToVideo, videoNameWithExt), background, wellNumber, wellPositions, output, previouslyAcquiredTrackingDataForDebug, hyperparameters, videoName, dlModel))
          p.start()
          processes.append(p)
      else:
        # for just one well
        processes = [1]
        getParametersForWell(os.path.join(pathToVideo, videoNameWithExt), background, hyperparameters["onlyTrackThisOneWell"], wellPositions, output, previouslyAcquiredTrackingDataForDebug, hyperparameters, videoName, dlModel)
    else:
      if hyperparameters["onlyTrackThisOneWell"] == -1:
        processes = [1 for i in range(0, hyperparameters["nbWells"])]
        for wellNumber in range(0,hyperparameters["nbWells"]):
          getParametersForWell(os.path.join(pathToVideo, videoNameWithExt), background, wellNumber, wellPositions, output, previouslyAcquiredTrackingDataForDebug, hyperparameters, videoName, dlModel)
      else:
        processes = [1]
        getParametersForWell(os.path.join(pathToVideo, videoNameWithExt), background, hyperparameters["onlyTrackThisOneWell"], wellPositions, output, previouslyAcquiredTrackingDataForDebug, hyperparameters, videoName, dlModel)
  
  # Sorting wells after the end of the parallelized calls end
  if processes != -1:
    dataPerWellUnsorted = [output.get() for p in processes]
  else:
    dataPerWellUnsorted = output2
  paramDataPerWell = [[]] * (hyperparameters["nbWells"])
  trackingDataPerWell = [[]] * (hyperparameters["nbWells"])
  for data in dataPerWellUnsorted:
    paramDataPerWell[data[0]]    = data[1]
    trackingDataPerWell[data[0]] = data[2]
  if processes != -1 and hyperparameters["onlyTrackThisOneWell"] == -1 and globalVariables["noMultiprocessing"] == 0:
    for p in processes:
      p.join()
  if (hyperparameters["freqAlgoPosFollow"] != 0):
    print("processes joined")

  if (hyperparameters["debugPauseBetweenTrackAndParamExtract"] == "saveTrackDataAndExtractParam") or (hyperparameters["debugPauseBetweenTrackAndParamExtract"] == "justSaveTrackData"):
    # saving tracking results for future uses
    outfile = open(os.path.join(outputFolderVideo, 'intermediaryTracking.txt'),'wb')
    pickle.dump(trackingDataPerWell,outfile)
    outfile.close()
    if (hyperparameters["freqAlgoPosFollow"] != 0):
      print("intermediary results saved")
    
  if hyperparameters["debugPauseBetweenTrackAndParamExtract"] != "justSaveTrackData":
    # Creating super structure
    superStruct = createSuperStruct(paramDataPerWell, wellPositions, hyperparameters)
  
    # Creating validation video
    if hyperparameters["copyOriginalVideoToOutputFolderForValidation"]:
      shutil.copyfile(os.path.join(pathToVideo, videoNameWithExt), os.path.join(os.path.join(hyperparameters["outputFolder"], hyperparameters["videoName"]), 'originalVideoWithoutAnyTrackingDisplayed_pleaseUseTheGUIToVisualizeTrackingPoints.avi'))
    else:
      if hyperparameters["createValidationVideo"]:
        infoFrame = createValidationVideo(os.path.join(pathToVideo, videoNameWithExt), superStruct, hyperparameters)
    
    # Various post-processing options depending on configuration file choices
    dataPostProcessing(outputFolderVideo, superStruct, hyperparameters, videoName, videoExt)
  
  # Copying output result folder in another folder
  if len(hyperparameters["additionalOutputFolder"]):
    if os.path.isdir(hyperparameters["additionalOutputFolder"]):
      if hyperparameters["additionalOutputFolderOverwriteIfAlreadyExist"]:
        shutil.rmtree(hyperparameters["additionalOutputFolder"])
        while True:
          try:
            shutil.copytree(outputFolderVideo, hyperparameters["additionalOutputFolder"])
            break
          except OSError as e:
            print("waiting inside except")
            time.sleep(0.1)
          else:
            print("waiting")
            time.sleep(0.1)
      else:
        print("The path " + hyperparameters["additionalOutputFolder"] + " already exists. New folder not created. If you want the folder to be overwritten in such situation in future executions, set the parameter 'additionalOutputFolderOverwriteIfAlreadyExist' to 1 in your configuration file.")
    else:
      shutil.copytree(outputFolderVideo, hyperparameters["additionalOutputFolder"])
  
  
  if hyperparameters["popUpAlgoFollow"]:
    popUpAlgoFollow.prepend("ZebraZoom Analysis finished for " + videoName)
    # popUpAlgoFollow.prepend("")
    # if hyperparameters["closePopUpWindowAtTheEnd"]:
      # popUpAlgoFollow.prepend("ZebraZoom Analysis all finished")

