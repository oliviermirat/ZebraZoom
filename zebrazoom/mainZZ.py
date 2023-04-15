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


class ZebraZoomVideoAnalysis:
  def __init__(self, pathToVideo, videoName, videoExt, configFile, argv, useGUI=True):
    self._pathToVideo = pathToVideo
    self._videoName = videoName
    self._videoExt = videoExt
    self._configFile = configFile
    self._useGUI = useGUI
    self._videoNameWithExt = videoName + '.' + videoExt
    self._previouslyAcquiredTrackingDataForDebug = []
    self.wellPositions = None
    self.background = None
    self._dlModel = 0
    # Getting hyperparameters
    self._hyperparameters, self._configFile = getHyperparameters(configFile, self._videoNameWithExt, os.path.join(pathToVideo, self._videoNameWithExt), argv)

    if self._hyperparameters["trackingDL"]:
      import torch.multiprocessing as mp
    else:
      import multiprocessing as mp
    if globalVariables["mac"] or self._hyperparameters["trackingDL"]:
      mp.set_start_method('spawn', force=True)

    self._output = mp.Queue()
    # Setting output folder
    self._outputFolderVideo = os.path.join(self._hyperparameters["outputFolder"], videoName)

  def _checkFirstAndLastFrame(self):
    # Checking first frame and last frame value
    cap   = zzVideoReading.VideoCapture(os.path.join(self._pathToVideo, self._videoNameWithExt))
    nbFrames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    cap.release()
    if self._hyperparameters["firstFrame"] < 0:
      print("Error for video " + self._videoName + ": The parameter 'firstFrame' in your configuration file is too small" + " (firstFrame value is " + str(self._hyperparameters["firstFrame"]) + ", number of frames in the video is " + str(nbFrames) + ")")
      raise NameError("Error for video " + self._videoName + ": The parameter 'firstFrame' in your configuration file is too small" + " (firstFrame value is " + str(self._hyperparameters["firstFrame"]) + ", number of frames in the video is " + str(nbFrames) + ")")
    if self._hyperparameters["firstFrame"] > nbFrames:
      print("Error for video " + self._videoName + ": The parameter 'firstFrame' in your configuration file is too big" + " (firstFrame value is " + str(self._hyperparameters["firstFrame"]) + ", number of frames in the video is " + str(nbFrames) + ")")
      raise NameError("Error for video " + self._videoName + ": The parameter 'firstFrame' in your configuration file is too big" + " (firstFrame value is " + str(self._hyperparameters["firstFrame"]) + ", number of frames in the video is " + str(nbFrames) + ")")
    if (self._hyperparameters["lastFrame"] < 0) or (self._hyperparameters["lastFrame"] <= self._hyperparameters["firstFrame"]):
      print("Error for video " + self._videoName + ": The parameter 'lastFrame' in your configuration file is too small" + " (lastFrame value is " + str(self._hyperparameters["lastFrame"]) + ", number of frames in the video is " + str(nbFrames) + ")")
      raise NameError("Error for video " + self._videoName + ": The parameter 'lastFrame' in your configuration file is too small" + " (lastFrame value is " + str(self._hyperparameters["lastFrame"]) + ", number of frames in the video is " + str(nbFrames) + ")")
    if self._hyperparameters["lastFrame"] > nbFrames:
      print("Warning: The parameter 'lastFrame' in your configuration file is too big so we adjusted it to the value:", nbFrames-2, "it was originally set to", self._hyperparameters["lastFrame"])
      self._hyperparameters["lastFrame"] = nbFrames - 2
      # raise NameError("Error: The parameter 'lastFrame' in your configuration file is too big")

  def _reloadPreviousTrackingData(self):
    # Reloading previously extracted tracking data if debugging option selected
    with open(os.path.join(self._outputFolderVideo, 'intermediaryTracking.txt'),'rb') as outfile:
        self._previouslyAcquiredTrackingDataForDebug = pickle.load(outfile)

  def _prepareOutputFolder(self):
    # Creating output folder
    if not self._hyperparameters["reloadWellPositions"] and not self._hyperparameters["reloadBackground"] and not self._hyperparameters["dontDeleteOutputFolderIfAlreadyExist"]:
      filesToKeep = {'intermediaryWellPositionReloadNoMatterWhat.txt', 'rotationAngle.txt'}
      filesToCopy = []
      if os.path.exists(self._outputFolderVideo):
        if glob.glob(os.path.join(self._outputFolderVideo, 'results_*.txt')):
          pastNumbersTaken = 1
          while os.path.exists(self._outputFolderVideo + '_PastTracking_' + str(pastNumbersTaken)) and pastNumbersTaken < 99:
            pastNumbersTaken += 1
          movedFolderName = self._outputFolderVideo + '_PastTracking_' + str(pastNumbersTaken)
          shutil.move(self._outputFolderVideo, movedFolderName)
          for filename in os.listdir(movedFolderName):
            if filename in filesToKeep:
              filesToCopy.append(os.path.join(movedFolderName, filename))
        else:
          for filename in os.listdir(self._outputFolderVideo):
            if filename not in filesToKeep:
              os.remove(os.path.join(self._outputFolderVideo, filename))
      if not os.path.exists(self._outputFolderVideo):
        if self._hyperparameters["tryCreatingFolderUntilSuccess"]:
          while True:
            try:
              os.mkdir(self._outputFolderVideo)
              break
            except OSError as e:
              print("waiting inside except")
              time.sleep(0.1)
            else:
              print("waiting")
              time.sleep(0.1)
        else:
          try:
            os.mkdir(self._outputFolderVideo)
          except OSError as e:
            time.sleep(0.1)
          else:
            time.sleep(0.1)
      for filename in filesToCopy:
        shutil.copy2(filename, self._outputFolderVideo)

  def _loadDLModel(self):
    # Reloading DL model for tracking with DL
    if self._hyperparameters["trackingDL"]:
      from zebrazoom.code.deepLearningFunctions.loadDLmodel import loadDLmodel
      self._dlModel = loadDLmodel(self._hyperparameters["trackingDL"])

  def _getParametersForWell(self, wellNumber):
    '''Does the tracking and then the extraction6 of parameters'''
    videoPath = os.path.join(self._pathToVideo, self._videoNameWithExt)
    if self._useGUI:
      from PyQt5.QtWidgets import QApplication

      if QApplication.instance() is None:
        from zebrazoom.GUIAllPy import PlainApplication
        app = PlainApplication(sys.argv)
    if self._hyperparameters["debugPauseBetweenTrackAndParamExtract"] == "noDebug":
      # Normal execution process
      trackingData = tracking(videoPath,self.background,wellNumber,self.wellPositions,self._hyperparameters, self._videoName, self._dlModel)
      parameters = extractParameters(trackingData, wellNumber, self._hyperparameters, videoPath, self.wellPositions, self.background)
      self._output.put([wellNumber,parameters,[]])
    elif self._hyperparameters["debugPauseBetweenTrackAndParamExtract"] == "justSaveTrackData":
      # Extracing tracking data, saving it, and that's it
      trackingData = tracking(videoPath,self.background,wellNumber,self.wellPositions,self._hyperparameters, self._videoName, self._dlModel)
      self._output.put([wellNumber,[],trackingData])
    elif self._hyperparameters["debugPauseBetweenTrackAndParamExtract"] == "saveTrackDataAndExtractParam":
      # Extracing tracking data, saving it, and continuing normal execution
      trackingData = tracking(videoPath,self.background,wellNumber,self.wellPositions,self._hyperparameters, self._videoName, self._dlModel)
      parameters = extractParameters(trackingData, wellNumber, self._hyperparameters, videoPath, self.wellPositions, self.background)
      self._output.put([wellNumber,parameters,trackingData])
    else: # self._hyperparameters["debugPauseBetweenTrackAndParamExtract"] == "justExtractParamFromPreviousTrackData"
      # Reloading previously tracked data and using it to extract parameters
      trackingData = self._previouslyAcquiredTrackingDataForDebug[wellNumber]
      parameters = extractParameters(trackingData, wellNumber, self._hyperparameters, videoPath, self.wellPositions, self.background)
      self._output.put([wellNumber,parameters,[]])

  def _storeConfigUsed(self):
    '''Saving the configuration file used'''
    with open(os.path.join(self._outputFolderVideo, 'configUsed.json'), 'w') as outfile:
      json.dump(self._configFile, outfile)

  def getWellPositions(self):
    '''Get well positions'''
    if self._hyperparameters["headEmbeded"] and not self._hyperparameters["oneWellManuallyChosenTopLeft"]:
      self.wellPositions = [{"topLeftX":0, "topLeftY":0, "lengthX": self._hyperparameters["videoWidth"], "lengthY": self._hyperparameters["videoHeight"]}]
    else:
      print("start find wells")
      if self._hyperparameters["groupOfMultipleSameSizeAndShapeEquallySpacedWells"]:
        rotationAngleFile = os.path.join(self._outputFolderVideo, 'rotationAngle.txt')
        if os.path.exists(rotationAngleFile):
          with open(rotationAngleFile, 'rb') as f:
            rotationAngleParams = pickle.load(f)
          self._hyperparameters.update(rotationAngleParams)
          with open(os.path.join(self._outputFolderVideo, 'configUsed.json'), 'r') as f:
            config = json.load(f)
          config.update(rotationAngleParams)
          with open(os.path.join(self._outputFolderVideo, 'configUsed.json'), 'w') as f:
            json.dump(config, f)
      if self._hyperparameters["saveWellPositionsToBeReloadedNoMatterWhat"]:
        outfile = open(os.path.join(self._outputFolderVideo, 'intermediaryWellPositionReloadNoMatterWhat.txt'),'wb')
        self.wellPositions = findWells(os.path.join(self._pathToVideo, self._videoNameWithExt), self._hyperparameters)
        pickle.dump(self.wellPositions,outfile)
      elif os.path.exists(os.path.join(self._outputFolderVideo, 'intermediaryWellPositionReloadNoMatterWhat.txt')):
        outfile = open(os.path.join(self._outputFolderVideo, 'intermediaryWellPositionReloadNoMatterWhat.txt'), 'rb')
        self.wellPositions = pickle.load(outfile)
      elif self._hyperparameters["reloadWellPositions"]:
        outfile = open(os.path.join(self._outputFolderVideo, 'intermediaryWellPosition.txt'), 'rb')
        self.wellPositions = pickle.load(outfile)
      elif self._hyperparameters["reloadWellPositionsFromFileInZZoutputIfItExistSaveInItOtherwise"] and os.path.exists(os.path.join(self._hyperparameters["outputFolder"], 'wellPosition.txt')):
        outfile = open(os.path.join(self._hyperparameters["outputFolder"], 'wellPosition.txt'), 'rb')
        self.wellPositions = pickle.load(outfile)
      else:
        outfile = open(os.path.join(self._outputFolderVideo, 'intermediaryWellPosition.txt'),'wb')
        self.wellPositions = findWells(os.path.join(self._pathToVideo, self._videoNameWithExt), self._hyperparameters)
        pickle.dump(self.wellPositions,outfile)
        if self._hyperparameters["reloadWellPositionsFromFileInZZoutputIfItExistSaveInItOtherwise"]:
          outfile2 = open(os.path.join(self._hyperparameters["outputFolder"], 'wellPosition.txt'), 'wb')
          pickle.dump(self.wellPositions, outfile2)
          outfile2.close()
      outfile.close()
      if self._useGUI:
        from PyQt5.QtWidgets import QApplication

        app = QApplication.instance()
        if hasattr(app, "wellPositions"):
          if self.wellPositions is None:
            return
          app.wellPositions[:] = [(position['topLeftX'], position['topLeftY'], position['lengthX'], position['lengthY'])
                                  for idx, position in enumerate(self.wellPositions)]
          if self._hyperparameters["wellsAreRectangles"] or len(self._hyperparameters["oneWellManuallyChosenTopLeft"]) or int(self._hyperparameters["multipleROIsDefinedDuringExecution"]) or self._hyperparameters["noWellDetection"] or self._hyperparameters["groupOfMultipleSameSizeAndShapeEquallySpacedWells"]:
            app.wellShape = 'rectangle'
          else:
            app.wellShape = 'circle'

  def getBackground(self):
    '''Get background'''
    if self._hyperparameters["backgroundSubtractorKNN"] or (self._hyperparameters["headEmbeded"] and self._hyperparameters["headEmbededRemoveBack"] == 0 and self._hyperparameters["headEmbededAutoSet_BackgroundExtractionOption"] == 0 and self._hyperparameters["adjustHeadEmbededTracking"] == 0) or self._hyperparameters["trackingDL"] or self._hyperparameters["fishTailTrackingDifficultBackground"]:
      self.background = []
    else:
      print("start get background")
      if self._hyperparameters["reloadBackground"]:
        outfile = open(os.path.join(self._outputFolderVideo, 'intermediaryBackground.txt'),'rb')
        self.background = pickle.load(outfile)
        print("Background Reloaded")
      else:
        outfile = open(os.path.join(self._outputFolderVideo, 'intermediaryBackground.txt'),'wb')
        self.background = getBackground(os.path.join(self._pathToVideo, self._videoNameWithExt), self._hyperparameters)
        pickle.dump(self.background, outfile)
        cv2.imwrite(os.path.join(self._outputFolderVideo, 'background.png'), self.background)
      outfile.close()
      if self._useGUI:
        from PyQt5.QtWidgets import QApplication

        app = QApplication.instance()
        if hasattr(app, "background"):
          app.background = self.background

  def _runTracking(self, process_type):
    # Tracking and extraction of parameters
    if self._hyperparameters["fasterMultiprocessing"] == 1:
      processes = -1
      output2 = fasterMultiprocessing(os.path.join(self._pathToVideo, self._videoNameWithExt), self.background, self.wellPositions, [], self._hyperparameters, self._videoName)
    elif self._hyperparameters["fasterMultiprocessing"] == 2:
      processes = -1
      output2 = fasterMultiprocessing2(os.path.join(self._pathToVideo, self._videoNameWithExt), self.background, self.wellPositions, [], self._hyperparameters, self._videoName)
    else:
      if globalVariables["noMultiprocessing"] == 0 and not self._hyperparameters['headEmbeded']:
        if self._hyperparameters["onlyTrackThisOneWell"] == -1:
          # for all wells, in parallel
          processes = []
          for wellNumber in range(0,self._hyperparameters["nbWells"]):
            p = process_type(target=self._getParametersForWell, args=(wellNumber,))
            p.start()
            processes.append(p)
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
    dlModel = loadDLmodel(hyperparameters["trackingDL"], hyperparameters["unet"])
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
        if self._hyperparameters["onlyTrackThisOneWell"] == -1:
          processes = [1 for i in range(0, self._hyperparameters["nbWells"])]
          for wellNumber in range(0,self._hyperparameters["nbWells"]):
            self._getParametersForWell(wellNumber,)
        else:
          processes = [1]
          self._getParametersForWell(self._hyperparameters["onlyTrackThisOneWell"],)

    # Sorting wells after the end of the parallelized calls end
    if processes != -1:
      dataPerWellUnsorted = [self._output.get() for p in processes]
    else:
      dataPerWellUnsorted = output2
    paramDataPerWell = [[]] * (self._hyperparameters["nbWells"])
    trackingDataPerWell = [[]] * (self._hyperparameters["nbWells"])
    for data in dataPerWellUnsorted:
      paramDataPerWell[data[0]]    = data[1]
      trackingDataPerWell[data[0]] = data[2]
    if processes != -1 and self._hyperparameters["onlyTrackThisOneWell"] == -1 and (globalVariables["noMultiprocessing"] == 0 and not self._hyperparameters['headEmbeded']):
      for p in processes:
        p.join()
    if (self._hyperparameters["freqAlgoPosFollow"] != 0):
      print("processes joined")
    return paramDataPerWell, trackingDataPerWell

  def _storeIntermediaryResults(self, trackingDataPerWell):
    # saving tracking results for future uses
    with open(os.path.join(self._outputFolderVideo, 'intermediaryTracking.txt'),'wb') as outfile:
      pickle.dump(trackingDataPerWell, outfile)
    if (self._hyperparameters["freqAlgoPosFollow"] != 0):
      print("intermediary results saved")

  def _createSuperStruct(self, paramDataPerWell):
    '''Create super structure'''
    return createSuperStruct(paramDataPerWell, self.wellPositions, self._hyperparameters, os.path.join(self._pathToVideo, self._videoNameWithExt))

  def _createValidationVideo(self, superStruct):
    '''Create validation video'''
    if not(self._hyperparameters["savePathToOriginalVideoForValidationVideo"]):
      if self._hyperparameters["copyOriginalVideoToOutputFolderForValidation"]:
        shutil.copyfile(os.path.join(self._pathToVideo, self._videoNameWithExt), os.path.join(os.path.join(self._hyperparameters["outputFolder"], self._hyperparameters["videoName"]), 'originalVideoWithoutAnyTrackingDisplayed_pleaseUseTheGUIToVisualizeTrackingPoints.avi'))
      else:
        if self._hyperparameters["createValidationVideo"]:
          infoFrame = createValidationVideo(os.path.join(self._pathToVideo, self._videoNameWithExt), superStruct, self._hyperparameters)

  def _dataPostProcessing(self, superStruct):
    return dataPostProcessing(self._outputFolderVideo, superStruct, self._hyperparameters, self._videoName, self._videoExt)

  def _storeResults(self, paramDataPerWell):
    superStruct = self._createSuperStruct(paramDataPerWell)
    self._createValidationVideo(superStruct)
    # Various post-processing options depending on configuration file choices
    superStruct = self._dataPostProcessing(superStruct)

    path = os.path.join(os.path.join(self._hyperparameters["outputFolder"], self._hyperparameters["videoName"]), 'results_' + self._hyperparameters["videoName"] + '.txt')
    print("createSuperStruct:", path)
    with open(path, 'w') as outfile:
      json.dump(superStruct, outfile)
    if self._hyperparameters["saveSuperStructToMatlab"]:
      from scipy.io import savemat
      matlabPath = os.path.join(os.path.join(self._hyperparameters["outputFolder"], self._hyperparameters["videoName"]), 'results_' + self._hyperparameters["videoName"] + '.mat')
      videoDataResults2 = {}
      videoDataResults2['videoDataResults'] = superStruct
      savemat(matlabPath, videoDataResults2)

  def _storeVersionUsed(self):
    with open(os.path.join(os.path.join(self._hyperparameters["outputFolder"], self._hyperparameters["videoName"]), 'ZebraZoomVersionUsed.txt'), 'w') as fp:
      fp.write(zebrazoom.__version__)

  def _storeInAdditionalFolder(self):
      if os.path.isdir(self._hyperparameters["additionalOutputFolder"]):
        if self._hyperparameters["additionalOutputFolderOverwriteIfAlreadyExist"]:
          shutil.rmtree(self.hyperparameters["additionalOutputFolder"])
          while True:
            try:
              shutil.copytree(self._outputFolderVideo, self._hyperparameters["additionalOutputFolder"])
              break
            except OSError as e:
              print("waiting inside except")
              time.sleep(0.1)
            else:
              print("waiting")
              time.sleep(0.1)
        else:
          print("The path " + self._hyperparameters["additionalOutputFolder"] + " already exists. New folder not created. If you want the folder to be overwritten in such situation in future executions, set the parameter 'additionalOutputFolderOverwriteIfAlreadyExist' to 1 in your configuration file.")
      else:
        shutil.copytree(self._outputFolderVideo, self._hyperparameters["additionalOutputFolder"])

  def run(self):
    '''Run tracking'''
    # Checking that path and video exists
    if not(os.path.exists(os.path.join(self._pathToVideo, self._videoNameWithExt))):
      print("Path or video name is incorrect for", os.path.join(self._pathToVideo, self._videoNameWithExt))
      return 0

    self._checkFirstAndLastFrame()

    if self._hyperparameters["debugPauseBetweenTrackAndParamExtract"] == "justExtractParamFromPreviousTrackData":
      self._reloadPreviousTrackingData()
    else:
      self._prepareOutputFolder()

    self._storeConfigUsed()

    if self._hyperparameters["trackingDL"]:
      from torch.multiprocessing import Process
    else:
      from multiprocessing import Process

    # Launching GUI algoFollower if necessary
    if self._hyperparameters["popUpAlgoFollow"]:
      import zebrazoom.code.popUpAlgoFollow as popUpAlgoFollow

      popUpAlgoFollow.createTraceFile("starting ZebraZoom analysis on " + self._videoName)
      p = Process(target=popUpAlgoFollow.initialise)
      p.start()

    self.getWellPositions()
    if int(self._hyperparameters["exitAfterWellsDetection"]):
      print("exitAfterWellsDetection")
      if self._hyperparameters["popUpAlgoFollow"]:
        import zebrazoom.code.popUpAlgoFollow as popUpAlgoFollow

        popUpAlgoFollow.prepend("ZebraZoom Analysis finished for " + self._videoName)
      raise ValueError

    self.getBackground()
    if self._hyperparameters["exitAfterBackgroundExtraction"]:
      print("exitAfterBackgroundExtraction")
      raise ValueError

    self._loadDLModel()

    paramDataPerWell, trackingDataPerWell = self._runTracking(Process)

    if (self._hyperparameters["debugPauseBetweenTrackAndParamExtract"] == "saveTrackDataAndExtractParam") or (self._hyperparameters["debugPauseBetweenTrackAndParamExtract"] == "justSaveTrackData"):
      self._storeIntermediaryResults(trackingDataPerWell)

    if self._hyperparameters["debugPauseBetweenTrackAndParamExtract"] != "justSaveTrackData":
      self._storeResults(paramDataPerWell)

    self._storeVersionUsed()

    # Copying output result folder in another folder
    if len(self._hyperparameters["additionalOutputFolder"]):
      self._storeInAdditionalFolder()

    if self._hyperparameters["popUpAlgoFollow"]:
      import zebrazoom.code.popUpAlgoFollow as popUpAlgoFollow

      popUpAlgoFollow.prepend("ZebraZoom Analysis finished for " + self._videoName)
      # popUpAlgoFollow.prepend("")
      # if self._hyperparameters["closePopUpWindowAtTheEnd"]:
        # popUpAlgoFollow.prepend("ZebraZoom Analysis all finished")
