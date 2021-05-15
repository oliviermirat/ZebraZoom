from pathlib import Path
import numpy as np
import tkinter as tk
from tkinter import font  as tkfont
from tkinter import filedialog
from tkinter import ttk
from tkinter import *
import json
import cv2
from zebrazoom.code.GUI.getCoordinates import findWellLeft, findWellRight, findHeadCenter, findBodyExtremity
from zebrazoom.code.GUI.automaticallyFindOptimalParameters import automaticallyFindOptimalParameters
import math
from zebrazoom.code.findWells import findWells
from zebrazoom.code.getHyperparameters import getHyperparametersSimple
from zebrazoom.code.getBackground import getBackground
from zebrazoom.code.getImage.getForegroundImage import getForegroundImage
import cvui
import pickle
from zebrazoom.code.vars import getGlobalVariables
from zebrazoom.mainZZ import mainZZ
import json
import os
globalVariables = getGlobalVariables()

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

def chooseVideoToCreateConfigFileFor(self, controller, reloadConfigFile):

  if int(reloadConfigFile):
  
    cur_dir_path = os.path.dirname(os.path.realpath(__file__))
    pathconf = Path(cur_dir_path)
    pathconf = pathconf.parent.parent
    pathconf = os.path.join(pathconf, 'configuration/')
    
    if globalVariables["mac"]:
      configFileName =  filedialog.askopenfilename(initialdir = pathconf, title = "Select file")
    else:
      configFileName =  filedialog.askopenfilename(initialdir = pathconf, title = "Select file", filetypes = (("json files","*.json"),("all files","*.*")))
    with open(configFileName) as f:
      self.configFile = json.load(f)

  if globalVariables["mac"]:
    self.videoToCreateConfigFileFor = filedialog.askopenfilename(initialdir = os.path.expanduser("~"),title = "Select video to create config file for")
  else:
    self.videoToCreateConfigFileFor = filedialog.askopenfilename(initialdir = os.path.expanduser("~"),title = "Select video to create config file for",filetypes = (("video","*.*"),("all files","*.*")))
  controller.show_frame("ChooseGeneralExperiment")

def chooseGeneralExperimentFirstStep(self, controller, freeZebra, headEmbZebra, drosophilia, rodent, other):
  self.configFile["extractAdvanceZebraParameters"] = 0
  if int(freeZebra):
    controller.show_frame("FreelySwimmingExperiment")
  else:
    chooseGeneralExperiment(self, controller, freeZebra, headEmbZebra, drosophilia, rodent, other, 0)

def chooseGeneralExperiment(self, controller, freeZebra, headEmbZebra, drosophilia, rodent, other, freeZebra2):
  self.configFile["extractAdvanceZebraParameters"] = 0
  if int(freeZebra):
    self.organism = 'zebrafish'
    self.configFile["headEmbeded"] = 0
    controller.show_frame("WellOrganisation")
  elif int(freeZebra2):
    self.organism = 'zebrafishNew'
    self.configFile["headEmbeded"] = 0
    controller.show_frame("WellOrganisation")
  elif int(headEmbZebra):
    self.organism = 'headembeddedzebrafish'
    self.configFile["headEmbeded"] = 1
    chooseBeginningAndEndOfVideo(self, controller)
  else:
    self.organism = 'drosoorrodent'
    self.configFile["headEmbeded"] = 0
    self.configFile["freeSwimmingTailTrackingMethod"] = "none"
    controller.show_frame("WellOrganisation")

def wellOrganisation(self, controller, circular, rectangular, roi, other):
  if rectangular:
    self.shape = 'rectangular'
    self.configFile["wellsAreRectangles"] = 1
    controller.show_frame("CircularOrRectangularWells")
  else:
    if circular and self.organism != 'drosoorrodent': # should remove the self.organism != 'drosoorrodent' at some point
      self.shape = 'circular'
      controller.show_frame("CircularOrRectangularWells")
    else:
      self.shape = 'other'
      if roi:
        cap = cv2.VideoCapture(self.videoToCreateConfigFileFor)
        cap.set(1, 10)
        ret, frame = cap.read()
        
        WINDOW_NAME = "Click on the top left of the region of interest"
        cvui.init(WINDOW_NAME)
        cv2.moveWindow(WINDOW_NAME, 0,0)
        cvui.imshow(WINDOW_NAME, frame)
        while not(cvui.mouse(cvui.CLICK)):
          cursor = cvui.mouse()
          if cv2.waitKey(20) == 27:
            break
        self.configFile["oneWellManuallyChosenTopLeft"] = [cursor.x, cursor.y]
        cv2.destroyAllWindows()
        
        WINDOW_NAME = "Click on the bottom right of the region of interest"
        cvui.init(WINDOW_NAME)
        cv2.moveWindow(WINDOW_NAME, 0,0)
        cvui.imshow(WINDOW_NAME, frame)
        while not(cvui.mouse(cvui.CLICK)):
          cursor = cvui.mouse()
          if cv2.waitKey(20) == 27:
            break
        self.configFile["oneWellManuallyChosenBottomRight"] = [cursor.x, cursor.y]
        cv2.destroyAllWindows()
        
        self.configFile["nbWells"] = 1
        chooseBeginningAndEndOfVideo(self, controller)
      else:
        self.configFile["noWellDetection"] = 1
        self.configFile["nbWells"] = 1
        chooseBeginningAndEndOfVideo(self, controller)


def rectangularWells(self, controller, nbwells, nbRowsOfWells, nbWellsPerRows):
  
  [pathToVideo, videoName, videoExt, configFile, argv] = getMainArguments(self)
  
  configFile["adjustRectangularWellsDetect"] = 1
  
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
  
  configFile["adjustRectangularWellsDetect"] = 0
  
  self.configFile = configFile
  
  chooseBeginningAndEndOfVideo(self, controller)
  

def circularOrRectangularWells(self, controller, nbwells, nbRowsOfWells, nbWellsPerRows):
  self.configFile["nbWells"]        = int(nbwells)
  
  if len(nbRowsOfWells):
    self.configFile["nbRowsOfWells"]  = int(nbRowsOfWells)
  else:
    self.configFile["nbRowsOfWells"]  = 1
    
  if len(nbWellsPerRows):
    self.configFile["nbWellsPerRows"]  = int(nbWellsPerRows)
  else:
    self.configFile["nbWellsPerRows"]  = 4
  
  if self.shape == 'circular':
    controller.show_frame("ChooseCircularWellsLeft")
  else:
    rectangularWells(self, controller, nbwells, nbRowsOfWells, nbWellsPerRows)


def chooseCircularWellsLeft(self, controller):
  cap = cv2.VideoCapture(self.videoToCreateConfigFileFor)
  ret, frame = cap.read()
  [x, y] = findWellLeft(frame)
  self.wellLeftBorderX = x
  self.wellLeftBorderY = y
  controller.show_frame("ChooseCircularWellsRight")
  
def chooseCircularWellsRight(self, controller):
  cap = cv2.VideoCapture(self.videoToCreateConfigFileFor)
  ret, frame = cap.read()
  [xRight, yRight] = findWellRight(frame)
  xLeft = self.wellLeftBorderX
  yLeft = self.wellLeftBorderY
  dist = math.sqrt((xLeft - xRight)**2 + (yLeft - yRight)**2)
  self.configFile["minWellDistanceForWellDetection"] = int(dist)
  self.configFile["wellOutputVideoDiameter"]         = int(dist + dist * 0.2)
  chooseBeginningAndEndOfVideo(self, controller)

def chooseBeginningAndEndOfVideo(self, controller):
  cap = cv2.VideoCapture(self.videoToCreateConfigFileFor)
  max_l = int(cap.get(7)) - 2
  
  cap.set(1, 1)
  ret, frame = cap.read()
  WINDOW_NAME = "Choose where the analysis of your video should start."
  WINDOW_NAME_CTRL = "Control"
  cvui.init(WINDOW_NAME)
  cv2.moveWindow(WINDOW_NAME, 0,0)
  cvui.init(WINDOW_NAME_CTRL)
  cv2.moveWindow(WINDOW_NAME_CTRL, 0, 300)
  value = [1]
  curValue = value[0]
  buttonclicked = False
  buttonEntireVideo = False
  widgetX = 40
  widgetY = 20
  widgetL = 300
  while not(buttonclicked) and not(buttonEntireVideo):
      value[0] = int(value[0])
      if curValue != value[0]:
        cap.set(1, value[0])
        frameOld = frame
        ret, frame = cap.read()
        if not(ret):
          frame = frameOld
        curValue = value[0]
      frameCtrl = np.full((200, 750), 100).astype('uint8')
      frameCtrl[widgetY:widgetY+60, widgetX:widgetX+widgetL] = 0
      cvui.text(frameCtrl, widgetX, widgetY, 'Frame')
      cvui.trackbar(frameCtrl, widgetX, widgetY+10, widgetL, value, 0, max_l)
      cvui.counter(frameCtrl, widgetX, widgetY+60, value)
      buttonclicked = cvui.button(frameCtrl, widgetX, widgetY+90, "Ok, I want the tracking to start at this frame!")
      
      cvui.text(frameCtrl, widgetX+350, widgetY+1, 'No, this is unecessary:')
      buttonEntireVideo = cvui.button(frameCtrl, widgetX+350, widgetY+40, "I want the tracking to run on the entire video!")
      
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
  cv2.destroyAllWindows()
  
  if not(buttonEntireVideo):
    self.configFile["firstFrame"] = int(value[0])
    cap.set(1, max_l)
    ret, frame = cap.read()
    while not(ret):
      max_l = max_l - 1
      cap.set(1, max_l)
      ret, frame = cap.read()
    WINDOW_NAME = "Choose where the analysis of your video should end."
    WINDOW_NAME_CTRL = "Control"
    cvui.init(WINDOW_NAME)
    cv2.moveWindow(WINDOW_NAME, 0,0)
    cvui.init(WINDOW_NAME_CTRL)
    cv2.moveWindow(WINDOW_NAME_CTRL, 0, 300)
    value = [max_l]
    curValue = value[0]
    buttonclicked = False
    widgetX = 40
    widgetY = 20
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
        buttonclicked = cvui.button(frameCtrl, widgetX, widgetY+90, "Ok, I want the tracking to end at this frame!")
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
    self.configFile["lastFrame"] = int(value[0])
    cv2.destroyAllWindows()
  
  if int(self.configFile["headEmbeded"]) == 1:
    controller.show_frame("HeadEmbeded")
  else:
    if self.organism == 'zebrafishNew':
      controller.show_frame("NumberOfAnimals2")
    elif self.organism == 'zebrafish':
      controller.show_frame("NumberOfAnimals")
    else:
      controller.show_frame("NumberOfAnimalsCenterOfMass")

  
def getImageForMultipleAnimalGUI(l, vertical, horizontal, nx, ny, max_l, videoToCreateConfigFileFor, background, wellPositions, hyperparameters):
  
  [frame, a1, a2] = getForegroundImage(videoToCreateConfigFileFor, background, l, 0, [], hyperparameters)
  
  lengthX = nx * 2
  lengthY = ny
  
  newX = lengthX
  newY = lengthY
  
  vertical2   = vertical   - vertical   * 0.12
  horizontal2 = horizontal - horizontal * 0.01
  if ( (lengthX > horizontal2) or (lengthY > vertical2) ):
    sinkFactor = 1
    sinkFactorX = horizontal2 / lengthX
    sinkFactorY = vertical2   / lengthY
    if (sinkFactorX > sinkFactorY):
      sinkFactor = sinkFactorY
    else:
      sinkFactor = sinkFactorX
    newX = lengthX * sinkFactor
    newY = lengthY * sinkFactor
  
  frame2 = frame
  ret,thresh2 = cv2.threshold(frame2,hyperparameters["thresholdForBlobImg"],255,cv2.THRESH_BINARY)
  kernel  = np.ones((hyperparameters["erodeSize"],hyperparameters["erodeSize"]), np.uint8)
  thresh2 = cv2.dilate(thresh2, kernel, iterations=hyperparameters["dilateIter"])

  thresh = thresh2
  thresh2 = cv2.cvtColor(thresh2, cv2.COLOR_GRAY2RGB)
  frame   = cv2.cvtColor(frame,   cv2.COLOR_GRAY2RGB)
  thresh[0, :]                = 255
  thresh[:, 0]                = 255
  thresh[len(thresh)-1, :]    = 255
  thresh[:, len(thresh[0])-1] = 255
  areaList = []
  contours, hierarchy = cv2.findContours(thresh,cv2.RETR_TREE,cv2.CHAIN_APPROX_SIMPLE)
  for contour in contours:
    area = cv2.contourArea(contour)
    if area < (len(thresh) * len(thresh[0]))/2:
      areaList.append(area)
    if (area > hyperparameters["minArea"]) and (area < hyperparameters["maxArea"]):
      M = cv2.moments(contour)
      if M['m00']:
        x = int(M['m10']/M['m00'])
        y = int(M['m01']/M['m00'])
        cv2.circle(thresh2, (x,y), 3, (0,0,255), -1)
      else:
        x = 0
        y = 0
  
  frame = cv2.line(frame, (len(frame[0])-5, 0), (len(frame[0])-5, len(frame)), (255, 0, 0), 5) 
  
  frame = np.concatenate((frame, thresh2), axis=1)
  
  frame = cv2.resize(frame,(int(newX),int(newY)))
  
  if len(areaList):
    maxToReturn = int((max(areaList)+2)*2)
  else:
    maxToReturn = (len(thresh) * len(thresh[0]))/5
  
  return [frame, maxToReturn]

def printStuffOnCtrlImg(frameCtrl, frameNum, x, y, l, minn, maxx, name):
  cvui.text(frameCtrl,     x,         y,    name)
  cvui.trackbar(frameCtrl, x,      y+10, l, frameNum, minn, maxx)
  cvui.counter(frameCtrl,  x+l+10, y+20,    frameNum)

def identifyMultipleHead(self, controller, nbanimals):
  
  self.configFile["videoName"] = "configFilePrep"

  tempConfig = self.configFile
  
  horizontal = self.winfo_screenwidth()
  vertical   = self.winfo_screenheight()
  
  # Wait image
  WINDOW_NAME = "Please Wait"
  cv2.destroyAllWindows()
  cvui.init(WINDOW_NAME)
  cv2.moveWindow(WINDOW_NAME, 0,0)
  # Getting hyperparameters, wellPositions, and background
  hyperparameters = getHyperparametersSimple(tempConfig)
  wellPositions = findWells(self.videoToCreateConfigFileFor, hyperparameters)
  background    = getBackground(self.videoToCreateConfigFileFor, hyperparameters)
  
  cur_dir_path = os.path.dirname(os.path.realpath(__file__))
  cur_dir_path = Path(cur_dir_path)
  
  tab = [1]
  img = cv2.imread(os.path.join(cur_dir_path, 'no1.png'))
  img = cv2.resize(img,(int(horizontal*0.95),int(vertical*0.8)))
  buttonclicked = False
  count = 0
  while not(buttonclicked):
    buttonclicked = cvui.button(img, 10, 10, "Ok, I understand!")
    cvui.imshow(WINDOW_NAME, img)
    cv2.waitKey(20)
    count = count + 1
    if count > 100:
      buttonclicked = True
  img = cv2.imread(os.path.join(cur_dir_path, 'no2.png'))
  img = cv2.resize(img,(int(horizontal*0.95),int(vertical*0.8)))
  buttonclicked = False
  count = 0
  while not(buttonclicked):
    buttonclicked = cvui.button(img, 10, 10, "Ok, I understand!")
    cvui.imshow(WINDOW_NAME, img)
    cv2.waitKey(20)
    count = count + 1
    if count > 100:
      buttonclicked = True
  img = cv2.imread(os.path.join(cur_dir_path, 'ok1.png'))
  img = cv2.resize(img,(int(horizontal*0.95),int(vertical*0.8)))
  buttonclicked = False
  count = 0
  while not(buttonclicked):
    buttonclicked = cvui.button(img, 10, 10, "Ok, I understand!")
    cvui.imshow(WINDOW_NAME, img)
    cv2.waitKey(20)
    count = count + 1
    if count > 100:
      buttonclicked = True
  
  WINDOW_NAME = "Adjust Parameters: As much as possible, you must see red points on and only on animals on the right image."
  WINDOW_NAME_CTRL = "Adjust Parameters."
  cv2.destroyAllWindows()
  # Manual parameters adjustements
  cap        = cv2.VideoCapture(self.videoToCreateConfigFileFor)
  nx         = int(cap.get(3))
  ny         = int(cap.get(4))
  max_l      = int(cap.get(7))
  
  hyperparameters["minArea"] = 5
  hyperparameters["maxArea"] = 800

  [frame, maxAreaBlobs] = getImageForMultipleAnimalGUI(1, vertical, horizontal, nx, ny, max_l, self.videoToCreateConfigFileFor, background, wellPositions, hyperparameters)
  frameCtrl = np.full((200, 1100), 100).astype('uint8')
  
  cvui.init(WINDOW_NAME)
  cv2.moveWindow(WINDOW_NAME, 0, 0)
  cvui.imshow(WINDOW_NAME, frame)
  
  cvui.init(WINDOW_NAME_CTRL)
  cv2.moveWindow(WINDOW_NAME_CTRL, 0, vertical-290)
  cvui.imshow(WINDOW_NAME_CTRL, frameCtrl)
  
  frameNum = [hyperparameters["firstFrame"]] if "firstFrame" in hyperparameters else [ 1 ]
  curFrameNum = frameNum[0] + 1
  minPixelDiffForBackExtract = [hyperparameters["minPixelDiffForBackExtract"]]
  thresholdForBlobImg        = [hyperparameters["thresholdForBlobImg"]]
  dilateIter                 = [hyperparameters["dilateIter"]]
  minArea                    = [hyperparameters["minArea"]]
  maxArea                    = [hyperparameters["maxArea"]]
  firstFrame = hyperparameters["firstFrame"] if "firstFrame" in hyperparameters else 1
  lastFrame  = hyperparameters["lastFrame"]-1 if "lastFrame" in hyperparameters else max_l - 10
  
  buttonclicked = False
  while not(buttonclicked):
    if curFrameNum != frameNum[0] or hyperparameters["minPixelDiffForBackExtract"] != minPixelDiffForBackExtract[0] or hyperparameters["thresholdForBlobImg"] != thresholdForBlobImg[0] or hyperparameters["dilateIter"] != dilateIter[0] or hyperparameters["minArea"] != minArea[0] or hyperparameters["maxArea"] != maxArea[0]:
      
      curFrameNum = frameNum[0]
      hyperparameters["minPixelDiffForBackExtract"] = int(minPixelDiffForBackExtract[0])
      hyperparameters["thresholdForBlobImg"] = int(thresholdForBlobImg[0])
      hyperparameters["dilateIter"] = int(dilateIter[0])
      hyperparameters["minArea"] = int(minArea[0])
      hyperparameters["maxArea"] = int(maxArea[0])
      
      [frame, maxAreaBlobs] = getImageForMultipleAnimalGUI(curFrameNum, vertical, horizontal, nx, ny, max_l, self.videoToCreateConfigFileFor, background, wellPositions, hyperparameters)
      
    frameCtrl = np.full((200, 1100), 100).astype('uint8')
    
    printStuffOnCtrlImg(frameCtrl, frameNum,                     1, 5,  350,  firstFrame, lastFrame, "Frame number")
    printStuffOnCtrlImg(frameCtrl, minPixelDiffForBackExtract, 470, 5,  350,  0, 255, "Threshold left image")
    printStuffOnCtrlImg(frameCtrl, thresholdForBlobImg,          1, 71,  350, 0, 255, "Threshold right image")
    printStuffOnCtrlImg(frameCtrl, dilateIter,                 470, 71,  350, 0, 15, "Area dilatation")
    printStuffOnCtrlImg(frameCtrl, minArea,                      1, 137, 350, 0, maxAreaBlobs, "Minimum area")
    printStuffOnCtrlImg(frameCtrl, maxArea,                    470, 137, 350, 0, maxAreaBlobs, "Maximum area")
    
    buttonclicked = cvui.button(frameCtrl, 940, 10, "Ok, done!")
    
    cvui.imshow(WINDOW_NAME, frame)
    cvui.imshow(WINDOW_NAME_CTRL, frameCtrl)
    
    if cv2.waitKey(20) == 27:
        break
  cv2.destroyAllWindows()
  
  del self.configFile["videoName"]
  
  self.configFile["minPixelDiffForBackExtract"] = int(hyperparameters["minPixelDiffForBackExtract"])
  self.configFile["thresholdForBlobImg"]        = int(hyperparameters["thresholdForBlobImg"])
  self.configFile["dilateIter"]                 = int(hyperparameters["dilateIter"])
  self.configFile["minArea"]                    = int(hyperparameters["minArea"])
  self.configFile["maxArea"]                    = int(hyperparameters["maxArea"])
  self.configFile["headSize"]        = math.sqrt((int(hyperparameters["minArea"]) + int(hyperparameters["maxArea"])) / 2)


def numberOfAnimals(self, controller, nbanimals, yes, noo, forceBlobMethodForHeadTracking, yesBouts, nooBouts, recommendedMethod, alternativeMethod, yesBends, nooBends, adjustBackgroundExtractionBasedOnNumberOfBlackPixels):

  self.configFile["noBoutsDetection"] = 1
  self.configFile["noChecksForBoutSelectionInExtractParams"] = 1
  self.configFile["trackingPointSizeDisplay"] = 4
  self.configFile["validationVideoPlotHeading"] = 0
  
  if int(yesBends):
    self.configFile["extractAdvanceZebraParameters"] = 1
  
  nbanimals = int(nbanimals)
  if nbanimals == self.configFile["nbWells"]:
    self.configFile["nbAnimalsPerWell"] = 1
  else:
    self.configFile["nbAnimalsPerWell"] = int(nbanimals / self.configFile["nbWells"])
    if noo:
      self.configFile["multipleHeadTrackingIterativelyRelaxAreaCriteria"] = 0
    else:
      self.configFile["multipleHeadTrackingIterativelyRelaxAreaCriteria"] = 1
      
  self.forceBlobMethodForHeadTracking = int(forceBlobMethodForHeadTracking)
  if self.forceBlobMethodForHeadTracking:
    self.configFile["forceBlobMethodForHeadTracking"] = self.forceBlobMethodForHeadTracking
  
  if self.organism == 'zebrafish':
    controller.show_frame("IdentifyHeadCenter")
  elif self.organism == 'zebrafishNew':
    detectBouts = 0
    if int(yesBouts):
      detectBouts = 1
    method = 0
    if int(alternativeMethod):
      method = 1
    automaticallyFindOptimalParameters(self, controller, True, detectBouts, method, int(noo), int(adjustBackgroundExtractionBasedOnNumberOfBlackPixels))
  elif self.organism == 'drosoorrodent' and int(recommendedMethod):
    automaticallyFindOptimalParameters(self, controller, True, 0, 0, int(noo), int(adjustBackgroundExtractionBasedOnNumberOfBlackPixels))
  else:
    identifyMultipleHead(self, controller, nbanimals)
    controller.show_frame("FinishConfig")

def chooseHeadCenter(self, controller):
  cap = cv2.VideoCapture(self.videoToCreateConfigFileFor)
  ret, frame = cap.read()
  [x, y] = findHeadCenter(frame)
  self.headCenterX = x
  self.headCenterY = y
  controller.show_frame("IdentifyBodyExtremity")

def chooseBodyExtremity(self, controller):
  cap = cv2.VideoCapture(self.videoToCreateConfigFileFor)
  ret, frame = cap.read()
  [extX, extY] = findBodyExtremity(frame)
  headCenterX = self.headCenterX
  headCenterY = self.headCenterY
  dist = math.sqrt((extX - headCenterX)**2 + (extY - headCenterY)**2)
  
  if self.organism == 'zebrafish':
    minArea = int(dist * (dist * 0.1))
    maxArea = int(dist * (dist * 0.4))
    self.configFile["minArea"]     = minArea
    self.configFile["maxArea"]     = maxArea
    self.configFile["minAreaBody"] = minArea
    self.configFile["maxAreaBody"] = maxArea
    self.configFile["headSize"]    = int(dist * 0.3)
    self.configFile["minTailSize"] = int(dist * 0.05)
    self.configFile["maxTailSize"] = int(dist * 2)
    self.configFile["paramGaussianBlur"] = int(int(dist*(31/52))/2)*2 + 1
  else:
    minArea = int(((2 * dist) * (2 * dist)) * 0.2)
    maxArea = int(((2 * dist) * (2 * dist)) * 1.5)
    self.configFile["minArea"]     = minArea
    self.configFile["maxArea"]     = maxArea
    self.configFile["minAreaBody"] = minArea
    self.configFile["maxAreaBody"] = maxArea
    self.configFile["headSize"]    = int(dist * 2)
  
  self.configFile["extractBackWhiteBackground"] = 1
  
  self.configFile["noBoutsDetection"] = 1
  
  if int(self.configFile["nbAnimalsPerWell"]) > 1 or self.forceBlobMethodForHeadTracking:
    identifyMultipleHead(self, controller, int(self.configFile["nbAnimalsPerWell"]))
    
  controller.show_frame("GoToAdvanceSettings")


def goToAdvanceSettings(self, controller, yes, no):

  if int(no):
    controller.show_frame("FinishConfig")
  else:
    self.configFile["noBoutsDetection"] = 0
    self.calculateBackgroundFreelySwim(controller, 0)

def finishConfig(self, controller, configFileNameToSave):

  cur_dir_path = os.path.dirname(os.path.realpath(__file__))
  cur_dir_path = Path(cur_dir_path)
  cur_dir_path = cur_dir_path.parent.parent
  reference = os.path.join(cur_dir_path, os.path.join('configuration', configFileNameToSave + '.json'))

  with open(reference, 'w') as outfile:
    json.dump(self.configFile, outfile)
  self.configFile = {}
  self.videoToCreateConfigFileFor = ''
  self.wellLeftBorderX = 0
  self.wellLeftBorderY = 0
  self.headCenterX = 0
  self.headCenterY = 0
  self.organism = ''
  
  if (globalVariables["mac"] or globalVariables["lin"]):
    self.destroy()
  else:
    controller.show_frame("StartPage")
