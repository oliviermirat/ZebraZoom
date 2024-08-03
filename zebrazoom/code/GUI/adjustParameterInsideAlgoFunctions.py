import numpy as np
from zebrazoom.zebraZoomVideoAnalysis import ZebraZoomVideoAnalysis
import os
import pickle
import cv2
import zebrazoom.videoFormatConversion.zzVideoReading as zzVideoReading
from zebrazoom.code.GUI.adjustParameterInsideAlgo import adjustParamInsideAlgoPage, adjustBoutDetectionOnlyPage, adjustParamInsideAlgoFreelySwimPage, adjustParamInsideAlgoFreelySwimAutomaticParametersPage

from PyQt5.QtWidgets import QApplication

import zebrazoom.code.paths as paths
import zebrazoom.code.util as util


def getMainArguments(self):
  s            = self.videoToCreateConfigFileFor
  arr          = s.split("/")
  nameWithExt  = arr.pop()
  pathToVideo  = '/'.join(arr) + '/'
  nameWithExtL = nameWithExt.split(".")
  videoExt     = nameWithExtL.pop()
  videoName    = '.'.join(nameWithExtL)
  configFile   = self.configFile
  argv = ["outputFolder", self.ZZoutputLocation]
  return [pathToVideo, videoName, videoExt, configFile, argv]


def prepareConfigFileForParamsAdjustements(configFile, wellNumber, firstFrame, videoToCreateConfigFileFor, adjustOnWholeVideo):

  initialFirstFrameValue = -1
  initialLastFrameValue  = -1
  if "firstFrame" in configFile:
    initialFirstFrameValue = configFile["firstFrame"]
  if "lastFrame" in configFile:
    initialLastFrameValue  = configFile["lastFrame"]

  cap = zzVideoReading.VideoCapture(videoToCreateConfigFileFor)
  max_l = int(cap.get(7))

  configFile["firstFrame"] = firstFrame
  if not adjustOnWholeVideo:
    if ("lastFrame" in configFile):
      if (configFile["lastFrame"] - configFile["firstFrame"] > 500):
        configFile["lastFrame"] = configFile["firstFrame"] + 500
    else:
      configFile["lastFrame"]  = min(configFile["firstFrame"] + 500, max_l-10)

  if "lastFrame" in configFile:
    if configFile["lastFrame"] > initialLastFrameValue and initialLastFrameValue != -1:
      configFile["lastFrame"] = initialLastFrameValue

  configFile["onlyTrackThisOneWell"] = wellNumber

  configFile["reloadBackground"] = 1

  return initialFirstFrameValue, initialLastFrameValue


def detectBouts(self, controller, wellNumber, firstFrame, adjustOnWholeVideo, reloadWellPositions=True):
  [pathToVideo, videoName, videoExt, configFile, argv] = getMainArguments(self)

  initialFirstFrameValue, initialLastFrameValue = prepareConfigFileForParamsAdjustements(configFile, wellNumber, firstFrame, self.videoToCreateConfigFileFor, adjustOnWholeVideo)

  if configFile.get('trackingImplementation') == 'fastFishTracking.tracking':
    configFile['detectMovementWithRawVideoInsideTracking'] = 1

  paramsToRemove = ["useFirstFrameAsBackground", "updateBackgroundAtInterval", "detectMovementWithRawVideoInsideTracking"]
  if configFile.get("fasterMultiprocessing", 0) == 2:
    paramsToRemove.append("fasterMultiprocessing")
  temporarilyRemovedParams = {param: configFile.pop(param, None) for param in paramsToRemove}

  configFile["noBoutsDetection"] = 0
  if "trackTail" in configFile:
    trackTailOriginalValue = configFile["trackTail"]
  else:
    trackTailOriginalValue = 1
  configFile["trackTail"]                   = 0
  configFile["adjustDetectMovWithRawVideo"] = 1
  configFile["reloadWellPositions"]         = int(reloadWellPositions)
  if "freqAlgoPosFollow" in configFile:
    freqAlgoPosFollowInitial = configFile["freqAlgoPosFollow"]
  else:
    freqAlgoPosFollowInitial = -1
  configFile["freqAlgoPosFollow"] = 10
  
  if "thresForDetectMovementWithRawVideo" in configFile:
    if configFile["thresForDetectMovementWithRawVideo"] == 0:
      configFile["thresForDetectMovementWithRawVideo"] = 1
  else:
    configFile["thresForDetectMovementWithRawVideo"] = 1

  app = QApplication.instance()
  with app.busyCursor():
    try:
      storeH5 = configFile.get('storeH5')
      configFile['storeH5'] = 1
      if "lastFrame" in configFile and "firstFrame" in configFile and configFile["lastFrame"] < configFile["firstFrame"]:
        del configFile["lastFrame"]
      ZebraZoomVideoAnalysis(pathToVideo, videoName, videoExt, configFile, argv).run()
    except ValueError:
      newhyperparameters = pickle.load(open(os.path.join(paths.getRootDataFolder(), 'newhyperparameters'), 'rb'))
      for index in newhyperparameters:
        configFile[index] = newhyperparameters[index]
    except NameError:
      print("Configuration file parameters changes discarded.")
    finally:
      if storeH5 is not None:
        configFile['storeH5'] = storeH5
      else:
        del configFile['storeH5']

  del configFile["onlyTrackThisOneWell"]
  configFile["trackTail"]                   = trackTailOriginalValue
  del configFile["adjustDetectMovWithRawVideo"]
  del configFile["reloadWellPositions"]

  if initialLastFrameValue == -1:
    if 'firstFrame' in configFile:
      del configFile['firstFrame']
    if 'lastFrame' in configFile:
      del configFile['lastFrame']
  else:
    configFile["firstFrame"]                  = initialFirstFrameValue
    configFile["lastFrame"]                   = initialLastFrameValue
  
  if freqAlgoPosFollowInitial == -1:
    del configFile["freqAlgoPosFollow"]
  else:
    configFile["freqAlgoPosFollow"] = freqAlgoPosFollowInitial
  
  configFile["reloadBackground"] = 0

  configFile.update({param: value for param, value in temporarilyRemovedParams.items() if value is not None})

  self.configFile = configFile


def adjustHeadEmbededTracking(self, controller, wellNumber, firstFrame, adjustOnWholeVideo):

  [pathToVideo, videoName, videoExt, configFile, argv] = getMainArguments(self)

  initialFirstFrameValue, initialLastFrameValue = prepareConfigFileForParamsAdjustements(configFile, wellNumber, firstFrame, self.videoToCreateConfigFileFor, adjustOnWholeVideo)

  configFile["adjustHeadEmbededTracking"] = 1

  try:
    storeH5 = configFile.get('storeH5')
    configFile['storeH5'] = 1
    if "lastFrame" in configFile and "firstFrame" in configFile and configFile["lastFrame"] < configFile["firstFrame"]:
      del configFile["lastFrame"]
    ZebraZoomVideoAnalysis(pathToVideo, videoName, videoExt, configFile, argv).run()
  except ValueError:
    newhyperparameters = pickle.load(open(os.path.join(paths.getRootDataFolder(), 'newhyperparameters'), 'rb'))
    for index in newhyperparameters:
      configFile[index] = newhyperparameters[index]
  except NameError:
    print("Configuration file parameters changes discarded.")
  finally:
    if storeH5 is not None:
      configFile['storeH5'] = storeH5
    else:
      del configFile['storeH5']

  configFile["onlyTrackThisOneWell"]      = -1
  configFile["adjustHeadEmbededTracking"] = 0
  if initialLastFrameValue == -1:
    if 'firstFrame' in configFile:
      del configFile['firstFrame']
    if 'lastFrame' in configFile:
      del configFile['lastFrame']
  else:
    configFile["firstFrame"]                  = initialFirstFrameValue
    configFile["lastFrame"]                   = initialLastFrameValue

  configFile["reloadBackground"] = 0

  self.configFile = configFile


def adjustFreelySwimTracking(self, controller, wellNumber, firstFrame, adjustOnWholeVideo):

  [pathToVideo, videoName, videoExt, configFile, argv] = getMainArguments(self)

  initialFirstFrameValue, initialLastFrameValue = prepareConfigFileForParamsAdjustements(configFile, wellNumber, firstFrame, self.videoToCreateConfigFileFor, adjustOnWholeVideo)

  configFile["reloadWellPositions"] = 1
  configFile["adjustFreelySwimTracking"] = 1

  try:
    storeH5 = configFile.get('storeH5')
    configFile['storeH5'] = 1
    if "lastFrame" in configFile and "firstFrame" in configFile and configFile["lastFrame"] < configFile["firstFrame"]:
      del configFile["lastFrame"]
    ZebraZoomVideoAnalysis(pathToVideo, videoName, videoExt, configFile, argv).run()
  except ValueError:
    newhyperparameters = pickle.load(open(os.path.join(paths.getRootDataFolder(), 'newhyperparameters'), 'rb'))
    for index in newhyperparameters:
      configFile[index] = newhyperparameters[index]
  except NameError:
    print("Configuration file parameters changes discarded.")
  finally:
    if storeH5 is not None:
      configFile['storeH5'] = storeH5
    else:
      del configFile['storeH5']

  configFile["onlyTrackThisOneWell"]      = -1
  configFile["adjustFreelySwimTracking"] = 0
  if initialLastFrameValue == -1:
    if 'firstFrame' in configFile:
      del configFile['firstFrame']
    if 'lastFrame' in configFile:
      del configFile['lastFrame']
  else:
    configFile["firstFrame"]                  = initialFirstFrameValue
    configFile["lastFrame"]                   = initialLastFrameValue

  configFile["reloadBackground"]    = 0
  configFile["reloadWellPositions"] = 0

  self.configFile = configFile


def _adjustFastFreelySwimTracking(self, controller, oldFirstFrame, detectBouts):
  wellNumber = 0
  adjustOnWholeVideo = True

  [pathToVideo, videoName, videoExt, configFile, argv] = getMainArguments(self)

  firstFrame = self.configFile["firstFrame"]
  if oldFirstFrame is not None:
    self.configFile["firstFrame"] = oldFirstFrame
  else:
    del self.configFile["firstFrame"]
  initialFirstFrameValue, initialLastFrameValue = prepareConfigFileForParamsAdjustements(configFile, wellNumber, firstFrame, self.videoToCreateConfigFileFor, adjustOnWholeVideo)

  configFile["reloadWellPositions"] = 1
  configFile["adjustFreelySwimTracking"] = 1
  configFile["reloadBackground"] = 1

  try:
    storeH5 = configFile.get('storeH5')
    configFile['storeH5'] = 1
    if "lastFrame" in configFile and "firstFrame" in configFile and configFile["lastFrame"] < configFile["firstFrame"]:
      del configFile["lastFrame"]
    ZebraZoomVideoAnalysis(pathToVideo, videoName, videoExt, configFile, argv).run()
  except ValueError:
    newhyperparameters = pickle.load(open(os.path.join(paths.getRootDataFolder(), 'newhyperparameters'), 'rb'))
    for index in newhyperparameters:
      configFile[index] = newhyperparameters[index]
  except NameError:
    print("Configuration file parameters changes discarded.")
  finally:
    if storeH5 is not None:
      configFile['storeH5'] = storeH5
    else:
      del configFile['storeH5']

  del configFile["reloadBackground"]
  del configFile["reloadWellPositions"]
  del configFile["adjustFreelySwimTracking"]

  self.configFile = configFile
  
  trackingMethodOldValue = configFile["trackingMethod"]

  if configFile["trackTail"] == 0: # FasterMultiprocessing screen option here

    # The image filtering option should be added here in the future
    self.configFile = {"nbWells": 25, "nbRowsOfWells": 5, "nbWellsPerRows": 5, "minPixelDiffForBackExtract": 20, "backgroundPreProcessParameters": [[3]], "backgroundPreProcessMethod": ["erodeThenMin"], "postProcessMultipleTrajectories": 1, "postProcessRemoveLowProbabilityDetection" : 0,"postProcessLowProbabilityDetectionThreshold" : 1, "postProcessRemovePointsOnBordersMargin" : 1, "trackingPointSizeDisplay": 1, "extractAdvanceZebraParameters": 0, "groupOfMultipleSameSizeAndShapeEquallySpacedWells": 1, "nbAnimalsPerWell": 1, "trackTail": 0, "validationVideoPlotHeading": 0, "freqAlgoPosFollow": 100, "fasterMultiprocessing": 1, "copyOriginalVideoToOutputFolderForValidation": 0, "backgroundExtractionForceUseAllVideoFrames": 1}
    
    if len(trackingMethodOldValue):
      self.configFile["trackingMethod"] = trackingMethodOldValue

    self.configFile["nbWells"]          = configFile["nbAnimalsPerWell"]
    self.configFile["nbRowsOfWells"]    = configFile["nbRowsOfWells"]
    self.configFile["nbWellsPerRows"]   = configFile["nbWellsPerRows"]
    self.configFile["nbAnimalsPerWell"] = 1
    self.configFile["minPixelDiffForBackExtract"] = configFile["minPixelDiffForBackExtract"]

  if detectBouts:
    util.addToHistory(controller.calculateBackgroundFreelySwim)(controller, 0, boutDetectionsOnly=True)
  else:
    util.addToHistory(controller.show_frame)("FinishConfig")


def adjustFastFreelySwimTracking(self, controller, detectBouts):
  oldFirstFrame = self.configFile.get("firstFrame")
  util.chooseBeginningPage(QApplication.instance(), self.videoToCreateConfigFileFor, "Choose where you want to start the procedure to adjust parameters.", "Ok, I want the procedure to start at this frame.",
                           lambda: _adjustFastFreelySwimTracking(self, controller, oldFirstFrame, detectBouts))


def adjustFreelySwimTrackingAutomaticParameters(self, controller, wellNumber, firstFrame, adjustOnWholeVideo):

  [pathToVideo, videoName, videoExt, configFile, argv] = getMainArguments(self)

  initialFirstFrameValue, initialLastFrameValue = prepareConfigFileForParamsAdjustements(configFile, wellNumber, firstFrame, self.videoToCreateConfigFileFor, adjustOnWholeVideo)

  configFile["reloadWellPositions"] = 1
  configFile["adjustFreelySwimTrackingAutomaticParameters"] = 1

  try:
    storeH5 = configFile.get('storeH5')
    configFile['storeH5'] = 1
    if "lastFrame" in configFile and "firstFrame" in configFile and configFile["lastFrame"] < configFile["firstFrame"]:
      del configFile["lastFrame"]
    ZebraZoomVideoAnalysis(pathToVideo, videoName, videoExt, configFile, argv).run()
  except ValueError:
    newhyperparameters = pickle.load(open(os.path.join(paths.getRootDataFolder(), 'newhyperparameters'), 'rb'))
    for index in newhyperparameters:
      configFile[index] = newhyperparameters[index]
  except NameError:
    print("Configuration file parameters changes discarded.")
  finally:
    if storeH5 is not None:
      configFile['storeH5'] = storeH5
    else:
      del configFile['storeH5']

  del configFile["onlyTrackThisOneWell"]
  del configFile["adjustFreelySwimTrackingAutomaticParameters"]
  if initialLastFrameValue == -1:
    if 'firstFrame' in configFile:
      del configFile['firstFrame']
    if 'lastFrame' in configFile:
      del configFile['lastFrame']
  else:
    configFile["firstFrame"]                  = initialFirstFrameValue
    configFile["lastFrame"]                   = initialLastFrameValue
  if "reloadBackground" in configFile:
    del configFile["reloadBackground"]
  if "reloadWellPositions" in configFile:
    del configFile["reloadWellPositions"]

  self.configFile = configFile


def calculateBackground(self, controller, nbImagesForBackgroundCalculation, useNext=True, wellPositions=None, wellShape=None, frameIdx=None):

  [pathToVideo, videoName, videoExt, configFile, argv] = getMainArguments(self)

  configFile["exitAfterBackgroundExtraction"] = 1
  configFile["headEmbededRemoveBack"]         = 1
  configFile["debugExtractBack"]              = 1

  if int(nbImagesForBackgroundCalculation):
    configFile["nbImagesForBackgroundCalculation"] = int(nbImagesForBackgroundCalculation)

  storeH5 = configFile.get('storeH5')
  configFile['storeH5'] = 1
  if "lastFrame" in configFile and "firstFrame" in configFile and configFile["lastFrame"] < configFile["firstFrame"]:
    del configFile["lastFrame"]

  app = QApplication.instance()
  app.wellPositions = []
  app.background = []
  with app.busyCursor():
    if wellPositions is not None:
      zzAnalysis = ZebraZoomVideoAnalysis(pathToVideo, videoName, videoExt, configFile, ['outputFolder', app.ZZoutputLocation])
      zzAnalysis.storeConfigUsed(configFile)
      zzAnalysis.storeWellPositions(wellPositions)
    try:
      ZebraZoomVideoAnalysis(pathToVideo, videoName, videoExt, configFile, argv).run()
    except ValueError:
      configFile["exitAfterBackgroundExtraction"] = 0
    finally:
      if storeH5 is not None:
        configFile['storeH5'] = storeH5
      else:
        del configFile['storeH5']

  configFile["exitAfterBackgroundExtraction"]   = 0
  configFile["headEmbededRemoveBack"]           = 0
  configFile["debugExtractBack"]                = 0

  adjustParamInsideAlgoPage(useNext=useNext, frameIdx=frameIdx)


def calculateBackgroundFreelySwim(self, controller, nbImagesForBackgroundCalculation, morePreciseFastScreen=False, automaticParameters=False, boutDetectionsOnly=False, useNext=True, nextCb=None, reloadWellPositions=False, wellPositions=None, wellShape=None, wellIdx=0, frameIdx=None):

  [pathToVideo, videoName, videoExt, configFile, argv] = getMainArguments(self)

  configFile["exitAfterBackgroundExtraction"] = 1
  configFile["debugExtractBack"]              = 1
  configFile["debugFindWells"]                = int(wellPositions is None)
  configFile["reloadWellPositions"] = int(reloadWellPositions)

  if int(nbImagesForBackgroundCalculation):
    configFile["nbImagesForBackgroundCalculation"] = int(nbImagesForBackgroundCalculation)

  storeH5 = configFile.get('storeH5')
  configFile['storeH5'] = 1
  if "lastFrame" in configFile and "firstFrame" in configFile and configFile["lastFrame"] < configFile["firstFrame"]:
    del configFile["lastFrame"]

  app = QApplication.instance()
  app.wellPositions = []
  with app.busyCursor():
    if wellPositions is not None:
      zzAnalysis = ZebraZoomVideoAnalysis(pathToVideo, videoName, videoExt, configFile, ['outputFolder', app.ZZoutputLocation])
      zzAnalysis.storeConfigUsed(configFile)
      zzAnalysis.storeWellPositions(wellPositions)
    try:
      ZebraZoomVideoAnalysis(pathToVideo, videoName, videoExt, configFile, argv).run()
    except ValueError:
      configFile["exitAfterBackgroundExtraction"] = 0
    finally:
      if storeH5 is not None:
        configFile['storeH5'] = storeH5
      else:
        del configFile['storeH5']

  del configFile["exitAfterBackgroundExtraction"] #  = 0
  del configFile["debugExtractBack"]              #  = 0
  del configFile["debugFindWells"]                #  = 0
  if "firstFrame" in configFile:
    del configFile["firstFrame"]
  if "lastFrame" in configFile:
    del configFile["lastFrame"]
  if "onlyTrackThisOneWell" in configFile:
    del configFile["onlyTrackThisOneWell"]
  if "reloadBackground" in configFile:
    del configFile["reloadBackground"]
  if "adjustDetectMovWithRawVideo" in configFile:
    del configFile["adjustDetectMovWithRawVideo"]
  if "reloadWellPositions" in configFile:
    del configFile["reloadWellPositions"]

  if morePreciseFastScreen:
    adjustFastFreelySwimTracking(self, controller, boutDetectionsOnly)
  elif boutDetectionsOnly:
    adjustBoutDetectionOnlyPage(useNext=useNext, nextCb=nextCb)
  elif automaticParameters:
    adjustParamInsideAlgoFreelySwimAutomaticParametersPage(useNext=useNext, wellIdx=wellIdx, frameIdx=frameIdx)
  else:
    adjustParamInsideAlgoFreelySwimPage(useNext=useNext)
