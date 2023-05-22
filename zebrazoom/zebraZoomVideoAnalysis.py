import zebrazoom
import zebrazoom.code.tracking
import zebrazoom.code.tracking.customTrackingImplementations
from zebrazoom.code.findWells import findWells
from zebrazoom.code.createSuperStruct import createSuperStruct
from zebrazoom.code.createValidationVideo import createValidationVideo
from zebrazoom.code.getHyperparameters import getHyperparameters

import h5py
import pickle
import os
import shutil
import time
import cv2
import zebrazoom.videoFormatConversion.zzVideoReading as zzVideoReading
import json
import glob
import numpy as np
from datetime import datetime


class ZebraZoomVideoAnalysis:
  def __init__(self, pathToVideo, videoName, videoExt, configFile, argv, useGUI=True):
    self._pathToVideo = pathToVideo
    self._videoName = videoName
    self._configFile = configFile
    self._useGUI = useGUI
    self._videoNameWithExt = videoName + '.' + videoExt
    self.wellPositions = None
    # Getting hyperparameters
    self._hyperparameters, self._configFile = getHyperparameters(configFile, self._videoNameWithExt, os.path.join(pathToVideo, self._videoNameWithExt), argv)
    if self._hyperparameters['storeH5']:
      self._hyperparameters['H5filename'] = os.path.join(self._hyperparameters["outputFolder"], f'{self._hyperparameters["videoName"]}_{datetime.now().strftime("%Y_%m_%d-%H_%M_%S")}.h5')

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

  def _runTracking(self):
    if 'trackingImplementation' in self._hyperparameters:
      name = self._hyperparameters['trackingImplementation']
    else:
      name = "fasterMultiprocessing" if self._hyperparameters["fasterMultiprocessing"] == 1 else "fasterMultiprocessing2" if self._hyperparameters["fasterMultiprocessing"] == 2 else "tracking"
    tracking = zebrazoom.code.tracking.get_tracking_method(name)(os.path.join(self._pathToVideo, self._videoNameWithExt), self.wellPositions, self._hyperparameters)
    if hasattr(tracking, 'useGUI'):
      tracking.useGUI = self._useGUI
    return tracking.run(), getattr(tracking, 'dataPostProcessing', None)

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

  def _storeH5(self, superStruct):
    with h5py.File(self._hyperparameters['H5filename'], 'a') as results:
      results.attrs['version'] = 0
      results.attrs['firstFrame'] = superStruct["firstFrame"]
      results.attrs['lastFrame'] = superStruct['lastFrame']
      results.attrs['ZebraZoomVersionUsed'] = zebrazoom.__version__
      if 'videoFPS' in superStruct:
        results.attrs['videoFPS'] = superStruct['videoFPS']
      if 'videoPixelSize' in superStruct:
        results.attrs['videoPixelSize'] = superStruct['videoPixelSize']
      if 'pathToOriginalVideo' in superStruct:
        results.attrs['pathToOriginalVideo'] = superStruct['pathToOriginalVideo']
      results.require_group("configurationFileUsed").attrs.update(self._configFile)
      for idx, wellPositions in enumerate(self.wellPositions):
        results.require_group(f"wellPositions/well{idx}").attrs.update(wellPositions)
      keysToSkip = {'AnimalNumber', 'curvature', 'HeadX', 'HeadY', 'Heading', 'TailAngle_Raw', 'TailX_VideoReferential', 'TailY_VideoReferential'}
      for wellIdx, well in enumerate(superStruct['wellPoissMouv']):
        for animalIdx, animal in enumerate(well):
          listOfBouts = results.require_group(f"dataForWell{wellIdx}/dataForAnimal{animalIdx}/listOfBouts")
          listOfBouts.attrs['numberOfBouts'] = len(animal)
          for boutIdx, bout in enumerate(animal):
            boutGroup = listOfBouts.require_group(f'bout{boutIdx}')
            for key, value in bout.items():
              if key in keysToSkip:
                continue
              if isinstance(value, list):
                boutGroup.create_dataset(key, data=np.array(value))
              else:
                boutGroup.attrs[key] = value

  def _storeResults(self, superStruct):
    path = os.path.join(self._hyperparameters["outputFolder"], self._hyperparameters["videoName"], f'results_{self._hyperparameters["videoName"]}.txt')
    print("createSuperStruct:", path)
    with open(path, 'w') as outfile:
      json.dump(superStruct, outfile)
    if self._hyperparameters["saveSuperStructToMatlab"]:
      from scipy.io import savemat
      matlabPath = os.path.join(os.path.join(self._hyperparameters["outputFolder"], self._hyperparameters["videoName"]), 'results_' + self._hyperparameters["videoName"] + '.mat')
      videoDataResults2 = {}
      videoDataResults2['videoDataResults'] = superStruct
      savemat(matlabPath, videoDataResults2)
    if self._hyperparameters["storeH5"]:
      self._storeH5(superStruct)

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

    if self._hyperparameters["debugPauseBetweenTrackAndParamExtract"] != "justExtractParamFromPreviousTrackData":
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

    paramDataPerWell, postProcessingCb = self._runTracking()

    if self._hyperparameters["debugPauseBetweenTrackAndParamExtract"] != "justSaveTrackData":
      superStruct = self._createSuperStruct(paramDataPerWell)
      self._createValidationVideo(superStruct)
      if postProcessingCb is not None:
        superStruct = postProcessingCb(self._outputFolderVideo, superStruct)
      self._storeResults(superStruct)

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
