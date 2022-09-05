import zebrazoom
from zebrazoom.code.findWells import findWells
from zebrazoom.code.getBackground import getBackground
from zebrazoom.code.getImage.getForegroundImage import getForegroundImage
from zebrazoom.code.trackingFolder.tracking import tracking
from zebrazoom.code.extractParameters import extractParameters
from zebrazoom.code.createSuperStruct import createSuperStruct
from zebrazoom.code.createValidationVideo import createValidationVideo
from zebrazoom.code.getHyperparameters import getHyperparameters
from zebrazoom.code.dataPostProcessing.dataPostProcessing import dataPostProcessing
from zebrazoom.code.fasterMultiprocessing import fasterMultiprocessing
from zebrazoom.code.fasterMultiprocessing2 import fasterMultiprocessing2

import sys
import pickle
import os
import shutil
import time
import cv2
import zebrazoom.videoFormatConversion.zzVideoReading as zzVideoReading
import json
import subprocess
import glob

from zebrazoom.code.vars import getGlobalVariables
globalVariables = getGlobalVariables()

output = 0

# Does the tracking and then the extraction of parameters
def getParametersForWell(videoPath,background,wellNumber,wellPositions,output,previouslyAcquiredTrackingDataForDebug,hyperparameters, videoName, dlModel, useGUI):
  if useGUI:
    from PyQt5.QtWidgets import QApplication

    if QApplication.instance() is None:
      from zebrazoom.GUIAllPy import PlainApplication
      app = PlainApplication(sys.argv)
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


def mainZZ(pathToVideo, videoName, videoExt, configFile, argv, useGUI=True):
  
  videoNameWithExt = videoName + '.' + videoExt
  previouslyAcquiredTrackingDataForDebug = []

  # Checking that path and video exists
  if not(os.path.exists(os.path.join(pathToVideo, videoNameWithExt))):
    print("Path or video name is incorrect for", os.path.join(pathToVideo, videoNameWithExt))
    return 0

  # Getting hyperparameters
  [hyperparameters, configFile] = getHyperparameters(configFile, videoNameWithExt, os.path.join(pathToVideo, videoNameWithExt), argv)
  
  if hyperparameters["trackingDL"]:
    import torch.multiprocessing as mp
  else:
    import multiprocessing as mp
  if globalVariables["mac"] or hyperparameters["trackingDL"]:
    mp.set_start_method('spawn', force=True)
  if hyperparameters["trackingDL"]:
    from torch.multiprocessing import Process
  else:
    from multiprocessing import Process

  output = mp.Queue()
  
  # Checking first frame and last frame value
  cap   = zzVideoReading.VideoCapture(os.path.join(pathToVideo, videoNameWithExt))
  nbFrames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
  cap.release()
  if hyperparameters["firstFrame"] < 0:
    print("Error for video " + videoName + ": The parameter 'firstFrame' in your configuration file is too small" + " (firstFrame value is " + str(hyperparameters["firstFrame"]) + ", number of frames in the video is " + str(nbFrames) + ")")
    raise NameError("Error for video " + videoName + ": The parameter 'firstFrame' in your configuration file is too small" + " (firstFrame value is " + str(hyperparameters["firstFrame"]) + ", number of frames in the video is " + str(nbFrames) + ")")
  if hyperparameters["firstFrame"] > nbFrames:
    print("Error for video " + videoName + ": The parameter 'firstFrame' in your configuration file is too big" + " (firstFrame value is " + str(hyperparameters["firstFrame"]) + ", number of frames in the video is " + str(nbFrames) + ")")
    raise NameError("Error for video " + videoName + ": The parameter 'firstFrame' in your configuration file is too big" + " (firstFrame value is " + str(hyperparameters["firstFrame"]) + ", number of frames in the video is " + str(nbFrames) + ")")
  if (hyperparameters["lastFrame"] < 0) or (hyperparameters["lastFrame"] <= hyperparameters["firstFrame"]):
    print("Error for video " + videoName + ": The parameter 'lastFrame' in your configuration file is too small" + " (lastFrame value is " + str(hyperparameters["lastFrame"]) + ", number of frames in the video is " + str(nbFrames) + ")")
    raise NameError("Error for video " + videoName + ": The parameter 'lastFrame' in your configuration file is too small" + " (lastFrame value is " + str(hyperparameters["lastFrame"]) + ", number of frames in the video is " + str(nbFrames) + ")")
  if hyperparameters["lastFrame"] > nbFrames:
    print("Warning: The parameter 'lastFrame' in your configuration file is too big so we adjusted it to the value:", nbFrames-2, "it was originally set to", hyperparameters["lastFrame"])
    hyperparameters["lastFrame"] = nbFrames - 2
    # raise NameError("Error: The parameter 'lastFrame' in your configuration file is too big")
  
  # Setting output folder
  outputFolderVideo = os.path.join(hyperparameters["outputFolder"], videoName)

  if hyperparameters["debugPauseBetweenTrackAndParamExtract"] == "justExtractParamFromPreviousTrackData":
    # Reloading previously extracted tracking data if debugging option selected
    outfile = open(os.path.join(outputFolderVideo, 'intermediaryTracking.txt'),'rb')
    previouslyAcquiredTrackingDataForDebug = pickle.load(outfile)
    outfile.close()
  else:
    # Creating output folder
    if not hyperparameters["reloadWellPositions"] and not hyperparameters["reloadBackground"] and not hyperparameters["dontDeleteOutputFolderIfAlreadyExist"]:
      filesToKeep = {'intermediaryWellPositionReloadNoMatterWhat.txt', 'rotationAngle.txt'}
      filesToCopy = []
      if os.path.exists(outputFolderVideo):
        if glob.glob(os.path.join(outputFolderVideo, 'results_*.txt')):
          pastNumbersTaken = 1
          while os.path.exists(outputFolderVideo + '_PastTracking_' + str(pastNumbersTaken)) and pastNumbersTaken < 99:
            pastNumbersTaken += 1
          movedFolderName = outputFolderVideo + '_PastTracking_' + str(pastNumbersTaken)
          shutil.move(outputFolderVideo, movedFolderName)
          for filename in os.listdir(movedFolderName):
            if filename in filesToKeep:
              filesToCopy.append(os.path.join(movedFolderName, filename))
        else:
          for filename in os.listdir(outputFolderVideo):
            if filename not in filesToKeep:
              os.remove(os.path.join(outputFolderVideo, filename))
      if not os.path.exists(outputFolderVideo):
        if hyperparameters["tryCreatingFolderUntilSuccess"]:
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
        else:
          try:
            os.mkdir(outputFolderVideo)
          except OSError as e:
            time.sleep(0.1)
          else:
            time.sleep(0.1)
      for filename in filesToCopy:
        shutil.copy2(filename, outputFolderVideo)

  # Saving the configuration file used
  with open(os.path.join(outputFolderVideo, 'configUsed.json'), 'w') as outfile:
    json.dump(configFile, outfile)
  

  # Getting well positions
  if hyperparameters["headEmbeded"] and not hyperparameters["oneWellManuallyChosenTopLeft"]:
    wellPositions = [{"topLeftX":0, "topLeftY":0, "lengthX": hyperparameters["videoWidth"], "lengthY": hyperparameters["videoHeight"]}]
  else:
    print("start find wells")
    if hyperparameters["groupOfMultipleSameSizeAndShapeEquallySpacedWells"]:
      rotationAngleFile = os.path.join(outputFolderVideo, 'rotationAngle.txt')
      if os.path.exists(rotationAngleFile):
        with open(rotationAngleFile, 'rb') as f:
          rotationAngleParams = pickle.load(f)
        hyperparameters.update(rotationAngleParams)
        with open(os.path.join(outputFolderVideo, 'configUsed.json'), 'r') as f:
          config = json.load(f)
        config.update(rotationAngleParams)
        with open(os.path.join(outputFolderVideo, 'configUsed.json'), 'w') as f:
          json.dump(config, f)
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
    if useGUI:
      from PyQt5.QtWidgets import QApplication

      app = QApplication.instance()
      if hasattr(app, "wellPositions"):
        if wellPositions is None:
          return
        app.wellPositions[:] = [(position['topLeftX'], position['topLeftY'], position['lengthX'], position['lengthY'])
                                for idx, position in enumerate(wellPositions)]
        if hyperparameters["wellsAreRectangles"] or len(hyperparameters["oneWellManuallyChosenTopLeft"]) or int(hyperparameters["multipleROIsDefinedDuringExecution"]) or hyperparameters["noWellDetection"] or hyperparameters["groupOfMultipleSameSizeAndShapeEquallySpacedWells"]:
          app.wellShape = 'rectangle'
        else:
          app.wellShape = 'circle'

  if int(hyperparameters["exitAfterWellsDetection"]):
    print("exitAfterWellsDetection")
    if hyperparameters["popUpAlgoFollow"]:
      import zebrazoom.code.popUpAlgoFollow as popUpAlgoFollow

      popUpAlgoFollow.prepend("ZebraZoom Analysis finished for " + videoName)
    raise ValueError

  # Launching GUI algoFollower if necessary
  if hyperparameters["popUpAlgoFollow"]:
    import zebrazoom.code.popUpAlgoFollow as popUpAlgoFollow

    popUpAlgoFollow.createTraceFile("starting ZebraZoom analysis on " + videoName)
    p = Process(target=popUpAlgoFollow.initialise)
    p.start()

  # Getting background
  if hyperparameters["backgroundSubtractorKNN"] or (hyperparameters["headEmbeded"] and hyperparameters["headEmbededRemoveBack"] == 0 and hyperparameters["headEmbededAutoSet_BackgroundExtractionOption"] == 0 and hyperparameters["adjustHeadEmbededTracking"] == 0) or hyperparameters["trackingDL"] or hyperparameters["fishTailTrackingDifficultBackground"]:
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
      pickle.dump(background, outfile)
      cv2.imwrite(os.path.join(outputFolderVideo, 'background.png'), background)
    outfile.close()
    if useGUI:
      from PyQt5.QtWidgets import QApplication

      app = QApplication.instance()
      if hasattr(app, "background"):
        app.background = background
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
  elif hyperparameters["fasterMultiprocessing"] == 2:
    processes = -1
    output2 = fasterMultiprocessing2(os.path.join(pathToVideo, videoNameWithExt), background, wellPositions, [], hyperparameters, videoName)
  else:
    if globalVariables["noMultiprocessing"] == 0 and not hyperparameters['headEmbeded']:
      if hyperparameters["onlyTrackThisOneWell"] == -1:
        # for all wells, in parallel
        processes = []
        for wellNumber in range(0,hyperparameters["nbWells"]):
          p = Process(target=getParametersForWell, args=(os.path.join(pathToVideo, videoNameWithExt), background, wellNumber, wellPositions, output, previouslyAcquiredTrackingDataForDebug, hyperparameters, videoName, dlModel, useGUI))
          p.start()
          processes.append(p)
      else:
        # for just one well
        processes = [1]
        getParametersForWell(os.path.join(pathToVideo, videoNameWithExt), background, hyperparameters["onlyTrackThisOneWell"], wellPositions, output, previouslyAcquiredTrackingDataForDebug, hyperparameters, videoName, dlModel, useGUI)
    else:
      if hyperparameters["onlyTrackThisOneWell"] == -1:
        processes = [1 for i in range(0, hyperparameters["nbWells"])]
        for wellNumber in range(0,hyperparameters["nbWells"]):
          getParametersForWell(os.path.join(pathToVideo, videoNameWithExt), background, wellNumber, wellPositions, output, previouslyAcquiredTrackingDataForDebug, hyperparameters, videoName, dlModel, useGUI)
      else:
        processes = [1]
        getParametersForWell(os.path.join(pathToVideo, videoNameWithExt), background, hyperparameters["onlyTrackThisOneWell"], wellPositions, output, previouslyAcquiredTrackingDataForDebug, hyperparameters, videoName, dlModel, useGUI)
  
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
  if processes != -1 and hyperparameters["onlyTrackThisOneWell"] == -1 and (globalVariables["noMultiprocessing"] == 0 and not hyperparameters['headEmbeded']):
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
    superStruct = createSuperStruct(paramDataPerWell, wellPositions, hyperparameters, os.path.join(pathToVideo, videoNameWithExt))
  
    # Creating validation video
    if not(hyperparameters["savePathToOriginalVideoForValidationVideo"]):
      if hyperparameters["copyOriginalVideoToOutputFolderForValidation"]:
        shutil.copyfile(os.path.join(pathToVideo, videoNameWithExt), os.path.join(os.path.join(hyperparameters["outputFolder"], hyperparameters["videoName"]), 'originalVideoWithoutAnyTrackingDisplayed_pleaseUseTheGUIToVisualizeTrackingPoints.avi'))
      else:
        if hyperparameters["createValidationVideo"]:
          infoFrame = createValidationVideo(os.path.join(pathToVideo, videoNameWithExt), superStruct, hyperparameters)
    
    # Various post-processing options depending on configuration file choices
    superStruct = dataPostProcessing(outputFolderVideo, superStruct, hyperparameters, videoName, videoExt)
    
    path = os.path.join(os.path.join(hyperparameters["outputFolder"], hyperparameters["videoName"]), 'results_' + hyperparameters["videoName"] + '.txt')
    print("createSuperStruct:", path)
    with open(path, 'w') as outfile:
      json.dump(superStruct, outfile)
    if hyperparameters["saveSuperStructToMatlab"]:
      from scipy.io import savemat
      matlabPath = os.path.join(os.path.join(hyperparameters["outputFolder"], hyperparameters["videoName"]), 'results_' + hyperparameters["videoName"] + '.mat')
      videoDataResults2 = {}
      videoDataResults2['videoDataResults'] = superStruct
      savemat(matlabPath, videoDataResults2)
  
    
  try:
    with open(os.path.join(os.path.join(hyperparameters["outputFolder"], hyperparameters["videoName"]), 'ZebraZoomVersionUsed.txt'), 'w') as fp:
      fp.write(zebrazoom.__version__)
  except:
    fileVersionUsed = open(os.path.join(os.path.join(hyperparameters["outputFolder"], hyperparameters["videoName"]), 'ZebraZoomVersionUsed.txt'), 'w')
    fileVersionUsed.write("Was not able to retrive the version number used.")
    fileVersionUsed.close()
  
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
    import zebrazoom.code.popUpAlgoFollow as popUpAlgoFollow

    popUpAlgoFollow.prepend("ZebraZoom Analysis finished for " + videoName)
    # popUpAlgoFollow.prepend("")
    # if hyperparameters["closePopUpWindowAtTheEnd"]:
      # popUpAlgoFollow.prepend("ZebraZoom Analysis all finished")

