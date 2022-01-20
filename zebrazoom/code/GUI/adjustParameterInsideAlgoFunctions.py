import numpy as np
from zebrazoom.mainZZ import mainZZ
import pickle
import cv2
import zebrazoom.videoFormatConversion.zzVideoReading as zzVideoReading
import cvui

def getMainArguments(self):
  s            = self.videoToCreateConfigFileFor
  arr          = s.split("/")
  nameWithExt  = arr.pop()
  pathToVideo  = '/'.join(arr) + '/'
  nameWithExtL = nameWithExt.split(".")
  videoExt     = nameWithExtL.pop()
  videoName    = '.'.join(nameWithExtL)
  configFile   = self.configFile
  argv         = []
  return [pathToVideo, videoName, videoExt, configFile, argv]


def prepareConfigFileForParamsAdjustements(configFile, wellNumber, firstFrameParamAdjust, videoToCreateConfigFileFor, adjustOnWholeVideo):

  initialFirstFrameValue = -1
  initialLastFrameValue  = -1
  if "firstFrame" in configFile:
    initialFirstFrameValue = configFile["firstFrame"]
  if "lastFrame" in configFile:
    initialLastFrameValue  = configFile["lastFrame"]

  cap = zzVideoReading.VideoCapture(videoToCreateConfigFileFor)
  max_l = int(cap.get(7))
  if int(firstFrameParamAdjust):
    cap.set(1, 1)
    ret, frame = cap.read()
    WINDOW_NAME = "Choose where you want to start the procedure to adjust parameters."
    WINDOW_NAME_CTRL = "Control"
    cvui.init(WINDOW_NAME)
    cv2.moveWindow(WINDOW_NAME, 0,0)
    cvui.init(WINDOW_NAME_CTRL)
    cv2.moveWindow(WINDOW_NAME_CTRL, 0, 300)
    value = [1]
    curValue = value[0]
    buttonclicked = False
    widgetX = 40
    widgetY = 50
    widgetL = 300
    while not(buttonclicked):
      value[0] = int(value[0])
      if curValue != value[0]:
        cap.set(1, value[0])
        frameOld = frame
        ret, frame = cap.read()
        if not(ret):
          frame = frameOld
        curValue = value[0]
      frameCtrl = np.full((200, 400), 100).astype('uint8')
      frameCtrl[widgetY:widgetY+60, widgetX:widgetX+widgetL] = 0
      cvui.text(frameCtrl, widgetX, widgetY, 'Frame')
      cvui.trackbar(frameCtrl, widgetX, widgetY+10, widgetL, value, 0, max_l-1)
      cvui.counter(frameCtrl, widgetX, widgetY+60, value)
      buttonclicked = cvui.button(frameCtrl, widgetX, widgetY+90, "Ok, I want the procedure to start at this frame.")
      cvui.text(frameCtrl, widgetX, widgetY+130, 'Keys: 4 or a: move backwards; 6 or d: move forward')
      cvui.text(frameCtrl, widgetX, widgetY+160, 'Keys: g or f: fast backwards; h or j: fast forward')
      cvui.imshow(WINDOW_NAME, frame)
      cvui.imshow(WINDOW_NAME_CTRL, frameCtrl)
      r = cv2.waitKey(20)
      if (r == 54) or (r == 100) or (r == 0):
        value[0] = value[0] + 1
      elif (r == 52) or (r == 97) or (r == 113):
        value[0] = value[0] - 1
      elif (r == 103):
        value[0] = value[0] - 30
      elif (r == 104):
        value[0] = value[0] + 30
      elif (r == 102):
        value[0] = value[0] - 100
      elif (r == 106):
        value[0] = value[0] + 100
    configFile["firstFrame"] = int(value[0])
    cv2.destroyAllWindows()
    if not(int(adjustOnWholeVideo)):
      if ("lastFrame" in configFile):
        if (configFile["lastFrame"] - configFile["firstFrame"] > 500):
          configFile["lastFrame"] = configFile["firstFrame"] + 500
      else:
        configFile["lastFrame"]  = min(configFile["firstFrame"] + 500, max_l-10)
  else:
    if not(int(adjustOnWholeVideo)):
      if ("firstFrame" in configFile) and ("lastFrame" in configFile):
        if configFile["lastFrame"] - configFile["firstFrame"] > 500:
          configFile["lastFrame"] = configFile["firstFrame"] + 500
      else:
        configFile["firstFrame"] = 1
        configFile["lastFrame"]  = min(max_l-10, 500)

  if "lastFrame" in configFile:
    if configFile["lastFrame"] > initialLastFrameValue and initialLastFrameValue != -1:
      configFile["lastFrame"] = initialLastFrameValue

  if len(wellNumber) != 0:
    configFile["onlyTrackThisOneWell"] = int(wellNumber)
  else:
    configFile["onlyTrackThisOneWell"] = 0

  configFile["reloadBackground"] = 1

  return [configFile, initialFirstFrameValue, initialLastFrameValue]


def detectBouts(self, controller, wellNumber, firstFrameParamAdjust, adjustOnWholeVideo):

  [pathToVideo, videoName, videoExt, configFile, argv] = getMainArguments(self)

  [configFile, initialFirstFrameValue, initialLastFrameValue] = prepareConfigFileForParamsAdjustements(configFile, wellNumber, firstFrameParamAdjust, self.videoToCreateConfigFileFor, adjustOnWholeVideo)

  configFile["noBoutsDetection"] = 0
  if "trackTail" in configFile:
    trackTailOriginalValue = configFile["trackTail"]
  else:
    trackTailOriginalValue = 1
  configFile["trackTail"]                   = 0
  configFile["adjustDetectMovWithRawVideo"] = 1
  configFile["reloadWellPositions"]         = 1

  if "thresForDetectMovementWithRawVideo" in configFile:
    if configFile["thresForDetectMovementWithRawVideo"] == 0:
      configFile["thresForDetectMovementWithRawVideo"] = 1
  else:
    configFile["thresForDetectMovementWithRawVideo"] = 1

  try:
    WINDOW_NAME = "Please Wait"
    cvui.init(WINDOW_NAME)
    cv2.moveWindow(WINDOW_NAME, 0,0)
    r = cv2.waitKey(2)
    if "lastFrame" in configFile and "firstFrame" in configFile and configFile["lastFrame"] < configFile["firstFrame"]:
      del configFile["lastFrame"]
    mainZZ(pathToVideo, videoName, videoExt, configFile, argv)
    cv2.destroyAllWindows()
  except ValueError:
    newhyperparameters = pickle.load(open('newhyperparameters', 'rb'))
    for index in newhyperparameters:
      configFile[index] = newhyperparameters[index]
  except NameError:
    print("Configuration file parameters changes discarded.")

  configFile["onlyTrackThisOneWell"]        = -1
  configFile["trackTail"]                   = trackTailOriginalValue
  configFile["adjustDetectMovWithRawVideo"] = 0
  configFile["reloadWellPositions"]         = 0

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


def adjustHeadEmbededTracking(self, controller, wellNumber, firstFrameParamAdjust, adjustOnWholeVideo):

  [pathToVideo, videoName, videoExt, configFile, argv] = getMainArguments(self)

  [configFile, initialFirstFrameValue, initialLastFrameValue] = prepareConfigFileForParamsAdjustements(configFile, wellNumber, firstFrameParamAdjust, self.videoToCreateConfigFileFor, adjustOnWholeVideo)

  if len(wellNumber) != 0:
    configFile["onlyTrackThisOneWell"]    = int(wellNumber)
  else:
    configFile["onlyTrackThisOneWell"]    = 0
  configFile["adjustHeadEmbededTracking"] = 1

  try:
    if "lastFrame" in configFile and "firstFrame" in configFile and configFile["lastFrame"] < configFile["firstFrame"]:
      del configFile["lastFrame"]
    mainZZ(pathToVideo, videoName, videoExt, configFile, argv)
  except ValueError:
    newhyperparameters = pickle.load(open('newhyperparameters', 'rb'))
    for index in newhyperparameters:
      configFile[index] = newhyperparameters[index]

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


def adjustFreelySwimTracking(self, controller, wellNumber, firstFrameParamAdjust, adjustOnWholeVideo):

  [pathToVideo, videoName, videoExt, configFile, argv] = getMainArguments(self)

  [configFile, initialFirstFrameValue, initialLastFrameValue] = prepareConfigFileForParamsAdjustements(configFile, wellNumber, firstFrameParamAdjust, self.videoToCreateConfigFileFor, adjustOnWholeVideo)

  configFile["reloadWellPositions"] = 1

  if len(wellNumber) != 0:
    configFile["onlyTrackThisOneWell"]    = int(wellNumber)
  else:
    configFile["onlyTrackThisOneWell"]    = 0
  configFile["adjustFreelySwimTracking"] = 1

  try:
    if "lastFrame" in configFile and "firstFrame" in configFile and configFile["lastFrame"] < configFile["firstFrame"]:
      del configFile["lastFrame"]
    mainZZ(pathToVideo, videoName, videoExt, configFile, argv)
  except ValueError:
    newhyperparameters = pickle.load(open('newhyperparameters', 'rb'))
    for index in newhyperparameters:
      configFile[index] = newhyperparameters[index]

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

def adjustFastFreelySwimTracking(self, controller):

  wellNumber = ''
  firstFrameParamAdjust = 1
  adjustOnWholeVideo = 1

  [pathToVideo, videoName, videoExt, configFile, argv] = getMainArguments(self)

  [configFile, initialFirstFrameValue, initialLastFrameValue] = prepareConfigFileForParamsAdjustements(configFile, wellNumber, firstFrameParamAdjust, self.videoToCreateConfigFileFor, adjustOnWholeVideo)

  configFile["reloadWellPositions"] = 1
  configFile["adjustFreelySwimTracking"] = 1
  configFile["reloadBackground"] = 1

  try:
    if "lastFrame" in configFile and "firstFrame" in configFile and configFile["lastFrame"] < configFile["firstFrame"]:
      del configFile["lastFrame"]
    mainZZ(pathToVideo, videoName, videoExt, configFile, argv)
  except ValueError:
    newhyperparameters = pickle.load(open('newhyperparameters', 'rb'))
    for index in newhyperparameters:
      configFile[index] = newhyperparameters[index]

  del configFile["reloadBackground"]
  del configFile["reloadWellPositions"]
  del configFile["adjustFreelySwimTracking"]

  self.configFile = configFile

  if configFile["trackTail"] == 0: # FasterMultiprocessing screen option here

    # The image filtering option should be added here in the future
    self.configFile = {"nbWells": 25, "nbRowsOfWells": 5, "nbWellsPerRows": 5, "minPixelDiffForBackExtract": 20, "backgroundPreProcessParameters": [[3]], "backgroundPreProcessMethod": ["erodeThenMin"], "postProcessMultipleTrajectories": 1, "postProcessRemoveLowProbabilityDetection" : 0,"postProcessLowProbabilityDetectionThreshold" : 1, "postProcessRemovePointsOnBordersMargin" : 1, "trackingPointSizeDisplay": 1, "extractAdvanceZebraParameters": 0, "groupOfMultipleSameSizeAndShapeEquallySpacedWells": 1, "nbAnimalsPerWell": 1, "trackTail": 0, "validationVideoPlotHeading": 0, "freqAlgoPosFollow": 100, "fasterMultiprocessing": 1, "copyOriginalVideoToOutputFolderForValidation": 0, "backgroundExtractionForceUseAllVideoFrames": 1}

    self.configFile["nbWells"]          = configFile["nbAnimalsPerWell"]
    self.configFile["nbRowsOfWells"]    = configFile["nbRowsOfWells"]
    self.configFile["nbWellsPerRows"]   = configFile["nbWellsPerRows"]
    self.configFile["nbAnimalsPerWell"] = 1
    self.configFile["minPixelDiffForBackExtract"] = configFile["minPixelDiffForBackExtract"]

  controller.show_frame("FinishConfig")


def adjustFreelySwimTrackingAutomaticParameters(self, controller, wellNumber, firstFrameParamAdjust, adjustOnWholeVideo):

  [pathToVideo, videoName, videoExt, configFile, argv] = getMainArguments(self)

  [configFile, initialFirstFrameValue, initialLastFrameValue] = prepareConfigFileForParamsAdjustements(configFile, wellNumber, firstFrameParamAdjust, self.videoToCreateConfigFileFor, adjustOnWholeVideo)

  configFile["reloadWellPositions"] = 1

  if len(wellNumber) != 0:
    configFile["onlyTrackThisOneWell"]    = int(wellNumber)
  else:
    configFile["onlyTrackThisOneWell"]    = 0
  configFile["adjustFreelySwimTrackingAutomaticParameters"] = 1

  try:
    if "lastFrame" in configFile and "firstFrame" in configFile and configFile["lastFrame"] < configFile["firstFrame"]:
      del configFile["lastFrame"]
    mainZZ(pathToVideo, videoName, videoExt, configFile, argv)
  except ValueError:
    newhyperparameters = pickle.load(open('newhyperparameters', 'rb'))
    for index in newhyperparameters:
      configFile[index] = newhyperparameters[index]
  except NameError:
    print("Configuration file parameters changes discarded.")

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


def calculateBackground(self, controller, nbImagesForBackgroundCalculation):

  [pathToVideo, videoName, videoExt, configFile, argv] = getMainArguments(self)

  configFile["exitAfterBackgroundExtraction"] = 1
  configFile["headEmbededRemoveBack"]         = 1
  configFile["debugExtractBack"]              = 1

  if int(nbImagesForBackgroundCalculation):
    configFile["nbImagesForBackgroundCalculation"] = int(nbImagesForBackgroundCalculation)

  WINDOW_NAME = "Please Wait"
  cvui.init(WINDOW_NAME)
  cv2.moveWindow(WINDOW_NAME, 0,0)

  try:
    if "lastFrame" in configFile and "firstFrame" in configFile and configFile["lastFrame"] < configFile["firstFrame"]:
      del configFile["lastFrame"]
    mainZZ(pathToVideo, videoName, videoExt, configFile, argv)
  except ValueError:
    configFile["exitAfterBackgroundExtraction"] = 0

  cv2.destroyAllWindows()

  configFile["exitAfterBackgroundExtraction"]   = 0
  configFile["headEmbededRemoveBack"]           = 0
  configFile["debugExtractBack"]                = 0

  controller.show_frame("AdujstParamInsideAlgo")


def calculateBackgroundFreelySwim(self, controller, nbImagesForBackgroundCalculation, morePreciseFastScreen=False, automaticParameters=False, boutDetectionsOnly=False):

  [pathToVideo, videoName, videoExt, configFile, argv] = getMainArguments(self)

  configFile["exitAfterBackgroundExtraction"] = 1
  configFile["debugExtractBack"]              = 1
  configFile["debugFindWells"]                = 1

  if int(nbImagesForBackgroundCalculation):
    configFile["nbImagesForBackgroundCalculation"] = int(nbImagesForBackgroundCalculation)

  WINDOW_NAME = "Please Wait"
  cvui.init(WINDOW_NAME)
  cv2.moveWindow(WINDOW_NAME, 0,0)

  try:
    if "lastFrame" in configFile and "firstFrame" in configFile and configFile["lastFrame"] < configFile["firstFrame"]:
      del configFile["lastFrame"]
    mainZZ(pathToVideo, videoName, videoExt, configFile, argv)
  except ValueError:
    configFile["exitAfterBackgroundExtraction"] = 0

  cv2.destroyAllWindows()

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


  if boutDetectionsOnly:
    controller.show_frame("AdujstBoutDetectionOnly")
  else:
    if automaticParameters:
      controller.show_frame("AdujstParamInsideAlgoFreelySwimAutomaticParameters")
    else:
      if morePreciseFastScreen:
        adjustFastFreelySwimTracking(self, controller)
      else:
        controller.show_frame("AdujstParamInsideAlgoFreelySwim")


def updateFillGapFrameNb(self, fillGapFrameNb):

  if len(fillGapFrameNb):
    self.configFile["fillGapFrameNb"] = int(fillGapFrameNb)
    toShow = np.zeros((200, 1000))
    toShow = cv2.putText(toShow, 'The parameter fillGapFrameNb has been updated to ' + str(fillGapFrameNb), (10, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 2)
    cv2.imshow("Done!", toShow)
    cv2.waitKey(3000)
    cv2.destroyAllWindows()
  else:
    toShow = np.zeros((200, 1000))
    toShow = cv2.putText(toShow, 'Insert a number in the box', (10, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, (255, 0, 0), 2)
    cv2.imshow("Done!", toShow)
    cv2.waitKey(3000)
    cv2.destroyAllWindows()
