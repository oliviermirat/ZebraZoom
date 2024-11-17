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

import zebrazoom.dataAPI as dataAPI


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
    videoNameWithTimestamp = f'{self._hyperparameters["videoName"]}_{datetime.now().strftime("%Y_%m_%d-%H_%M_%S")}'
    while os.path.exists(os.path.join(self._hyperparameters["outputFolder"], f'{videoNameWithTimestamp}.h5')) or os.path.exists(os.path.join(self._hyperparameters["outputFolder"], f'{videoNameWithTimestamp}')):
      time.sleep(0.5)
      videoNameWithTimestamp = f'{self._hyperparameters["videoName"]}_{datetime.now().strftime("%Y_%m_%d-%H_%M_%S")}'
    self._hyperparameters['videoNameWithTimestamp'] = videoNameWithTimestamp
    if self._hyperparameters['storeH5']:
      self._hyperparameters['H5filename'] = os.path.join(self._hyperparameters["outputFolder"], f'{videoNameWithTimestamp}.h5')
    # Setting output folder
    self._outputFolderVideo = os.path.join(self._hyperparameters["outputFolder"], videoNameWithTimestamp)

  def _checkFirstAndLastFrame(self):
    # Checking first frame and last frame value
    cap   = zzVideoReading.VideoCapture(os.path.join(self._pathToVideo, self._videoNameWithExt))
    nbFrames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    cap.release()
    if self._hyperparameters["firstFrame"] < 0:
      print("Error for video " + self._videoName + ": The parameter 'firstFrame' in your configuration file is too small" + " (firstFrame value is " + str(self._hyperparameters["firstFrame"]) + ", number of frames in the video is " + str(nbFrames) + ")")
      raise NameError("Error for video " + self._videoName + ": The parameter 'firstFrame' in your configuration file is too small" + " (firstFrame value is " + str(self._hyperparameters["firstFrame"]) + ", number of frames in the video is " + str(nbFrames) + ")")
    if self._hyperparameters["firstFrame"] > nbFrames and nbFrames != -1: # The nbFrames != -1 is for event based tracking
      print("Error for video " + self._videoName + ": The parameter 'firstFrame' in your configuration file is too big" + " (firstFrame value is " + str(self._hyperparameters["firstFrame"]) + ", number of frames in the video is " + str(nbFrames) + ")")
      raise NameError("Error for video " + self._videoName + ": The parameter 'firstFrame' in your configuration file is too big" + " (firstFrame value is " + str(self._hyperparameters["firstFrame"]) + ", number of frames in the video is " + str(nbFrames) + ")")
    if ((self._hyperparameters["lastFrame"] < 0) or (self._hyperparameters["lastFrame"] <= self._hyperparameters["firstFrame"])) and not((nbFrames == - 1) and (self._hyperparameters["lastFrame"] == -1)):
      print("Error for video " + self._videoName + ": The parameter 'lastFrame' in your configuration file is too small" + " (lastFrame value is " + str(self._hyperparameters["lastFrame"]) + ", number of frames in the video is " + str(nbFrames) + ")")
      raise NameError("Error for video " + self._videoName + ": The parameter 'lastFrame' in your configuration file is too small" + " (lastFrame value is " + str(self._hyperparameters["lastFrame"]) + ", number of frames in the video is " + str(nbFrames) + ")")
    if self._hyperparameters["lastFrame"] > nbFrames and nbFrames != -1: # The nbFrames != -1 is for event based tracking
      print("Warning: The parameter 'lastFrame' in your configuration file is too big so we adjusted it to the value:", nbFrames-2, "it was originally set to", self._hyperparameters["lastFrame"])
      self._hyperparameters["lastFrame"] = nbFrames - 2
      # raise NameError("Error: The parameter 'lastFrame' in your configuration file is too big")

  def storeConfigUsed(self, config):
    if self._hyperparameters['storeH5']:
      with h5py.File(self._hyperparameters['H5filename'], 'a') as results:
        results.require_group("configurationFileUsed").attrs.update(config)
    else:
      if not os.path.exists(self._outputFolderVideo):
        os.makedirs(self._outputFolderVideo)
      with open(os.path.join(self._outputFolderVideo, 'configUsed.json'), 'w') as outfile:
        json.dump(config, outfile)

  def _storeConfigUsed(self):
    '''Saving the configuration file used'''
    self.storeConfigUsed(self._configFile)

  def storeWellPositions(self, wellPositions, rotationAngleParams=None):
    if self._hyperparameters['storeH5']:
      with h5py.File(self._hyperparameters['H5filename'], 'a') as results:
        for idx, wellPos in enumerate(wellPositions):
          results.require_group(f"wellPositions/well{idx}").attrs.update(wellPos)
        if rotationAngleParams is not None:
          results['configurationFileUsed'].attrs.update(rotationAngleParams)
    else:
      with open(os.path.join(self._outputFolderVideo, 'intermediaryWellPosition.txt'), 'wb') as outfile:
        pickle.dump(wellPositions, outfile)
      if rotationAngleParams is not None:
        with open(os.path.join(self._outputFolderVideo, 'configUsed.json'), 'r') as f:
          config = json.load(f)
        config.update(rotationAngleParams)
        with open(os.path.join(self._outputFolderVideo, 'configUsed.json'), 'w') as f:
          json.dump(config, f)

  def getWellPositions(self):
    '''Get well positions'''
    rotationAngleParams = None
    if self._hyperparameters["headEmbeded"] and not self._hyperparameters["oneWellManuallyChosenTopLeft"]:
      self.wellPositions = [{"topLeftX":0, "topLeftY":0, "lengthX": self._hyperparameters["videoWidth"], "lengthY": self._hyperparameters["videoHeight"]}]
    else:
      print("start find wells")
      maybeReloadWells = self._hyperparameters["groupOfMultipleSameSizeAndShapeEquallySpacedWells"] or self._hyperparameters["multipleROIsDefinedDuringExecution"]
      inputFilesFolder = os.path.join(self._hyperparameters['outputFolder'], '.ZebraZoomVideoInputs', self._videoName)
      if self._hyperparameters["groupOfMultipleSameSizeAndShapeEquallySpacedWells"]:
        rotationAngleFile = os.path.join(inputFilesFolder, 'rotationAngle.txt')
        if os.path.exists(rotationAngleFile):
          with open(rotationAngleFile, 'rb') as f:
            rotationAngleParams = pickle.load(f)
          self._hyperparameters.update(rotationAngleParams)
      if self._hyperparameters["saveWellPositionsToBeReloadedNoMatterWhat"]:
        if not maybeReloadWells:
          print('Well positions can only be stored for multiple ROIs defined during execution or grid system')
          raise ValueError
        self.wellPositions = findWells(os.path.join(self._pathToVideo, self._videoNameWithExt), self._hyperparameters)
        if not os.path.exists(inputFilesFolder):
          os.makedirs(inputFilesFolder)
        with open(os.path.join(inputFilesFolder, 'intermediaryWellPositionReloadNoMatterWhat.txt'), 'wb') as outfile:
          pickle.dump(self.wellPositions, outfile)
      elif maybeReloadWells and os.path.exists(os.path.join(inputFilesFolder, 'intermediaryWellPositionReloadNoMatterWhat.txt')):
        with open(os.path.join(inputFilesFolder, 'intermediaryWellPositionReloadNoMatterWhat.txt'), 'rb') as outfile:
          self.wellPositions = pickle.load(outfile)
        gridSystem = len(self.wellPositions) > 1 and len({(pos['lengthX'], pos['lengthY']) for pos in self.wellPositions}) == 1
        nbWells = self._hyperparameters["nbWellsPerRows"] * self._hyperparameters["nbRowsOfWells"] if self._hyperparameters["groupOfMultipleSameSizeAndShapeEquallySpacedWells"] else self._hyperparameters["nbWells"]
        if self._hyperparameters["groupOfMultipleSameSizeAndShapeEquallySpacedWells"] ^ gridSystem or len(self.wellPositions) != nbWells:
          self.wellPositions = findWells(os.path.join(self._pathToVideo, self._videoNameWithExt), self._hyperparameters)
      elif self._hyperparameters["reloadWellPositions"]:
        fname = next(reversed(sorted(name for name in os.listdir(self._hyperparameters['outputFolder']) if os.path.splitext(name)[0][:-20] == self._videoName and os.path.splitext(name)[0] != self._hyperparameters['videoNameWithTimestamp'])))
        with h5py.File(os.path.join(self._hyperparameters['outputFolder'], fname)) as results:
          self.wellPositions = [dict(results[f'wellPositions/well{idx}'].attrs) for idx in range(len(results['wellPositions']))]
      elif self._hyperparameters["reloadWellPositionsFromFileInZZoutputIfItExistSaveInItOtherwise"] and os.path.exists(os.path.join(self._hyperparameters["outputFolder"], 'wellPosition.txt')):
        with open(os.path.join(self._hyperparameters["outputFolder"], 'wellPosition.txt'), 'rb') as outfile:
          self.wellPositions = pickle.load(outfile)
      else:
        self.wellPositions = findWells(os.path.join(self._pathToVideo, self._videoNameWithExt), self._hyperparameters)
        if self._hyperparameters["reloadWellPositionsFromFileInZZoutputIfItExistSaveInItOtherwise"]:
          with open(os.path.join(self._hyperparameters["outputFolder"], 'wellPosition.txt'), 'wb') as outfile:
            pickle.dump(self.wellPositions, outfile)

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

    if self.wellPositions is not None:
      self.storeWellPositions(self.wellPositions, rotationAngleParams=rotationAngleParams)

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
    if self._hyperparameters.get('savePathToOriginalVideoForValidationVideo', False):
      return
    if self._hyperparameters["copyOriginalVideoToOutputFolderForValidation"]:
      fname = f'{self._hyperparameters["videoNameWithTimestamp"]}_originalVideoWithoutAnyTrackingDisplayed_pleaseUseTheGUIToVisualizeTrackingPoints.avi'
      shutil.copyfile(os.path.join(self._pathToVideo, self._videoNameWithExt), fname)
    elif self._hyperparameters["createValidationVideo"]:
      folder = self._hyperparameters['outputFolder'] if self._hyperparameters['storeH5'] else os.path.join(self._outputFolderVideo)
      if not os.path.exists(folder):
        os.makedirs(folder)
      fname = os.path.join(folder, f'{self._hyperparameters["videoNameWithTimestamp"]}.avi')
      infoFrame = createValidationVideo(os.path.join(self._pathToVideo, self._videoNameWithExt), superStruct, self._hyperparameters, outputName=fname)

  def _storeH5Results(self, superStruct):
    print("Store results:", self._hyperparameters['H5filename'])
    with h5py.File(self._hyperparameters['H5filename'], 'a') as results:
      results.attrs['version'] = 0
      results.attrs['firstFrame'] = superStruct["firstFrame"]
      results.attrs['lastFrame'] = superStruct['lastFrame']
      if 'videoFPS' in superStruct:
        results.attrs['videoFPS'] = superStruct['videoFPS']
      if 'videoPixelSize' in superStruct:
        results.attrs['videoPixelSize'] = superStruct['videoPixelSize']
      if 'pathToOriginalVideo' in superStruct:
        results.attrs['pathToOriginalVideo'] = superStruct['pathToOriginalVideo']
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
      results.create_dataset('exampleFrame', data=zzVideoReading.VideoCapture(os.path.join(self._pathToVideo, self._videoNameWithExt), self._hyperparameters).read()[1])

  def _storeResults(self, superStruct):
    if self._hyperparameters['storeH5']:
      self._storeH5Results(superStruct)
    else:
      if not os.path.exists(self._outputFolderVideo):
        os.makedirs(self._outputFolderVideo)
      cv2.imwrite(os.path.join(self._outputFolderVideo, "exampleFrame.png"), zzVideoReading.VideoCapture(os.path.join(self._pathToVideo, self._videoNameWithExt)).read()[1])
      path = os.path.join(self._outputFolderVideo, f'results_{self._hyperparameters["videoNameWithTimestamp"]}.txt')
      print("createSuperStruct:", path)
      with open(path, 'w') as outfile:
        json.dump(superStruct, outfile)

    if self._hyperparameters["saveSuperStructToMatlab"]:
      from scipy.io import savemat
      if not os.path.exists(self._outputFolderVideo):
        os.makedirs(self._outputFolderVideo)
      matlabPath = os.path.join(self._outputFolderVideo, f'results_{self._hyperparameters["videoName"]}.mat')
      savemat(matlabPath, {'videoDataResults': superStruct})

  def _storeVersionUsed(self):
    if self._hyperparameters['storeH5']:
      with h5py.File(self._hyperparameters['H5filename'], 'a') as results:
        results.attrs['ZebraZoomVersionUsed'] = zebrazoom.__version__
    else:
      with open(os.path.join(self._outputFolderVideo, 'ZebraZoomVersionUsed.txt'), 'w') as fp:
        fp.write(zebrazoom.__version__)

  def _storeInAdditionalFolder(self):
      if os.path.isdir(self._hyperparameters["additionalOutputFolder"]):
        if self._hyperparameters["additionalOutputFolderOverwriteIfAlreadyExist"]:
          shutil.rmtree(self.hyperparameters["additionalOutputFolder"])
        else:
          print("The path " + self._hyperparameters["additionalOutputFolder"] + " already exists. New folder not created. If you want the folder to be overwritten in such situation in future executions, set the parameter 'additionalOutputFolderOverwriteIfAlreadyExist' to 1 in your configuration file.")
          return
      if os.path.exists(self._outputFolderVideo):
        shutil.copytree(self._outputFolderVideo, self._hyperparameters["additionalOutputFolder"])
      else:
        os.makedirs(self._hyperparameters["additionalOutputFolder"])
      if self._hyperparameters['storeH5']:
        for fname in os.listdir(self._hyperparameters['outputFolder']):
          fullPath = os.path.join(self._hyperparameters['outputFolder'], fname)
          if os.path.isfile(fullPath) and os.path.splitext(fname)[0] == self._hyperparameters['videoNameWithTimestamp']:
            shutil.copy2(fullPath, self._hyperparameters['additionalOutputFolder'])

  def run(self):
    '''Run tracking'''
    # Checking that path and video exists
    if not(os.path.exists(os.path.join(self._pathToVideo, self._videoNameWithExt))):
      print("Path or video name is incorrect for", os.path.join(self._pathToVideo, self._videoNameWithExt))
      return 0

    self._checkFirstAndLastFrame()

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
      if self._hyperparameters["saveWellPositionsToBeReloadedNoMatterWhat"]:
        try:  # try to clean up temporary results
          if self._hyperparameters['storeH5']:
            os.remove(self._hyperparameters['H5filename'])
          else:
            shutil.rmtree(os.path.join(self._hyperparameters['outputFolder'], self._hyperparameters['videoNameWithTimestamp']))
        except OSError:
          pass
      print("exitAfterWellsDetection")
      if self._hyperparameters["popUpAlgoFollow"]:
        import zebrazoom.code.popUpAlgoFollow as popUpAlgoFollow

        popUpAlgoFollow.prepend("ZebraZoom Analysis finished for " + self._videoName)
      raise ValueError

    paramDataPerWell, postProcessingCb = self._runTracking()

    superStruct = self._createSuperStruct(paramDataPerWell)
    self._createValidationVideo(superStruct)
    if postProcessingCb is not None:
      superStruct = postProcessingCb(self._outputFolderVideo, superStruct)
    self._storeResults(superStruct)

    self._storeVersionUsed()

    # Copying output result folder in another folder
    if len(self._hyperparameters["additionalOutputFolder"]):
      self._storeInAdditionalFolder()
    
    # DataAPI calls
    if "reassignMultipleAnimalsId" in self._hyperparameters and self._hyperparameters["reassignMultipleAnimalsId"]:
      dataAPI.reassignMultipleAnimalsId(self._videoName, self._hyperparameters["nbWells"], self._hyperparameters["nbAnimalsPerWell"], self._hyperparameters["freqAlgoPosFollow"] if "freqAlgoPosFollow" in self._hyperparameters else 0, self)
      
    if "smoothHeadPositionsWindow" in self._hyperparameters and self._hyperparameters["smoothHeadPositionsWindow"]:
      dataAPI.smoothHeadPositions(self._videoName, self._hyperparameters["nbWells"], self._hyperparameters["nbAnimalsPerWell"], self._hyperparameters["smoothHeadPositionsWindow"])
      
    if "coordinatesOnlyBoutDetectionMinDistDataAPI" in self._hyperparameters and self._hyperparameters["coordinatesOnlyBoutDetectionMinDistDataAPI"]:
      dataAPI.detectBouts(self._videoName, self._hyperparameters["nbWells"], self._hyperparameters["nbAnimalsPerWell"], self)
    
    if self._hyperparameters["popUpAlgoFollow"]:
      import zebrazoom.code.popUpAlgoFollow as popUpAlgoFollow

      popUpAlgoFollow.prepend("ZebraZoom Analysis finished for " + self._videoName)
      # popUpAlgoFollow.prepend("")
      # if self._hyperparameters["closePopUpWindowAtTheEnd"]:
        # popUpAlgoFollow.prepend("ZebraZoom Analysis all finished")
