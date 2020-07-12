import sys

from findWells import findWells
from getBackground import getBackground
from getForegroundImage import getForegroundImage
from tracking import tracking
from extractParameters import extractParameters
from createSuperStruct import createSuperStruct
from createValidationVideo import createValidationVideo
from getHyperparameters import getHyperparameters
from generateAllTimeTailAngleGraph import generateAllTimeTailAngleGraph
from perBoutOutput import perBoutOutput
import popUpAlgoFollow
  
import pickle
import os
import shutil
import time

from vars import getGlobalVariables
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
  hyperparameters = getHyperparameters(configFile, videoNameWithExt, pathToVideo + videoNameWithExt, argv)
  
  # Launching GUI algoFollower if necessary
  if hyperparameters["popUpAlgoFollow"]:
    # if hyperparameters["popUpAlgoFollow"] == 2:
    popUpAlgoFollow.initialise()
    popUpAlgoFollow.prepend("starting ZebraZoom analysis on " + videoName)

  if hyperparameters["debugPauseBetweenTrackAndParamExtract"] == "justExtractParamFromPreviousTrackData":
    # Reloading previously extracted tracking data if debugging option selected
    outfile = open(hyperparameters["outputFolder"] + videoName + '/intermediaryTracking.txt','rb')
    previouslyAcquiredTrackingDataForDebug = pickle.load(outfile)
    outfile.close()
  else:
    # Creating output folder
    if not(hyperparameters["reloadWellPositions"]) and not(hyperparameters["reloadBackground"]):
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
    
  # Saving the configuration file used
  if type(configFile) == str:
    shutil.copyfile(configFile, hyperparameters["outputFolder"] + videoName + '/configUsed.txt')

  # Getting well positions
  if hyperparameters["headEmbeded"]:
    wellPositions = [{"topLeftX":0, "topLeftY":0, "lengthX":hyperparameters["videoWidth"], "lengthY":hyperparameters["videoHeight"]}]
  else:
    print("start find wells")
    if hyperparameters["reloadWellPositions"]:
      outfile = open(hyperparameters["outputFolder"] + videoName + '/intermediaryWellPosition.txt','rb')
      wellPositions = pickle.load(outfile)
    else:
      outfile = open(hyperparameters["outputFolder"] + videoName + '/intermediaryWellPosition.txt','wb')
      wellPositions = findWells(pathToVideo + videoNameWithExt, hyperparameters)
      pickle.dump(wellPositions,outfile)
    outfile.close()
    
  # Getting background
  if hyperparameters["headEmbeded"] and hyperparameters["headEmbededRemoveBack"] == 0 and hyperparameters["headEmbededAutoSet_BackgroundExtractionOption"] == 0 and hyperparameters["adjustHeadEmbededTracking"] == 0:
    background = []
  else:
    print("start get background")
    if hyperparameters["reloadBackground"]:
      outfile = open(hyperparameters["outputFolder"] + videoName + '/intermediaryBackground.txt','rb')
      background = pickle.load(outfile)
      print("Background Reloaded")
    else:
      outfile = open(hyperparameters["outputFolder"] + videoName + '/intermediaryBackground.txt','wb')
      background = getBackground(pathToVideo + videoNameWithExt, hyperparameters)
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
        p = Process(target=getParametersForWell, args=(pathToVideo + videoNameWithExt, background, wellNumber, wellPositions, output, previouslyAcquiredTrackingDataForDebug, hyperparameters, videoName))
        p.start()
        processes.append(p)
    else:
      # for just one well
      processes = [1]
      getParametersForWell(pathToVideo + videoNameWithExt, background, hyperparameters["onlyTrackThisOneWell"], wellPositions, output, previouslyAcquiredTrackingDataForDebug, hyperparameters, videoName)
  else:
    if hyperparameters["onlyTrackThisOneWell"] == -1:
      processes = [1 for i in range(0, hyperparameters["nbWells"])]
      for wellNumber in range(0,hyperparameters["nbWells"]):
        getParametersForWell(pathToVideo + videoNameWithExt, background, wellNumber, wellPositions, output, previouslyAcquiredTrackingDataForDebug, hyperparameters, videoName)
    else:
      processes = [1]
      getParametersForWell(pathToVideo + videoNameWithExt, background, hyperparameters["onlyTrackThisOneWell"], wellPositions, output, previouslyAcquiredTrackingDataForDebug, hyperparameters, videoName)
  
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
    outfile = open(hyperparameters["outputFolder"] + videoName + '/intermediaryTracking.txt','wb')
    pickle.dump(trackingDataPerWell,outfile)
    outfile.close()
    
  if hyperparameters["debugPauseBetweenTrackAndParamExtract"] != "justSaveTrackData":
    # Creating super structure
    superStruct = createSuperStruct(paramDataPerWell, wellPositions, hyperparameters)
  
  if hyperparameters["generateAllTimeTailAngleGraph"]:
    generateAllTimeTailAngleGraph(hyperparameters["outputFolder"] + videoName, superStruct, hyperparameters["generateAllTimeTailAngleGraphLineWidth"])
    
  if hyperparameters["createValidationVideo"]:
    # Creating validation video
    infoFrame = createValidationVideo(pathToVideo + videoNameWithExt, superStruct, hyperparameters)
  
  if hyperparameters["perBoutOutput"]:
    # Creating additional validation output per bout
    perBoutOutput(superStruct, hyperparameters, videoName)

  if hyperparameters["popUpAlgoFollow"]:
    popUpAlgoFollow.prepend("ZebraZoom Analysis finished for "+ videoName)
    # popUpAlgoFollow.prepend("")
    # if hyperparameters["closePopUpWindowAtTheEnd"]:
      # popUpAlgoFollow.prepend("ZebraZoom Analysis all finished")

