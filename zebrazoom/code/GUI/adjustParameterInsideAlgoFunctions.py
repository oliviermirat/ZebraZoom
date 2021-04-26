import numpy as np
import tkinter as tk
from tkinter import font  as tkfont
from tkinter import filedialog
from tkinter import ttk
from tkinter import *
from zebrazoom.mainZZ import mainZZ
import pickle
import cv2
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
  
  cap = cv2.VideoCapture(videoToCreateConfigFileFor)
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
    mainZZ(pathToVideo, videoName, videoExt, configFile, argv)
    cv2.destroyAllWindows()
  except ValueError:
    newhyperparameters = pickle.load(open('newhyperparameters', 'rb'))
    for index in newhyperparameters:
      configFile[index] = newhyperparameters[index]
  
  configFile["onlyTrackThisOneWell"]        = -1
  configFile["trackTail"]                   = 1
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
    mainZZ(pathToVideo, videoName, videoExt, configFile, argv)
  except ValueError:
    configFile["exitAfterBackgroundExtraction"] = 0
  
  cv2.destroyAllWindows()
  
  configFile["exitAfterBackgroundExtraction"]   = 0
  configFile["headEmbededRemoveBack"]           = 0
  configFile["debugExtractBack"]                = 0
  
  controller.show_frame("AdujstParamInsideAlgo")
  

def calculateBackgroundFreelySwim(self, controller, nbImagesForBackgroundCalculation):
  
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
    mainZZ(pathToVideo, videoName, videoExt, configFile, argv)
  except ValueError:
    configFile["exitAfterBackgroundExtraction"] = 0
  
  cv2.destroyAllWindows()
  
  configFile["exitAfterBackgroundExtraction"]   = 0
  configFile["debugExtractBack"]                = 0
  configFile["debugFindWells"]                  = 0
  
  controller.show_frame("AdujstParamInsideAlgoFreelySwim")
