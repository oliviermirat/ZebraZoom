import numpy as np
import cv2
import zebrazoom.videoFormatConversion.zzVideoReading as zzVideoReading
from zebrazoom.code.GUI.getCoordinates import findWellLeft, findWellRight, findHeadCenter, findBodyExtremity
from zebrazoom.code.GUI.automaticallyFindOptimalParameters import automaticallyFindOptimalParameters
import math
from zebrazoom.code.findWells import findWells
from zebrazoom.code.getHyperparameters import getHyperparametersSimple
from zebrazoom.code.getBackground import getBackground
from zebrazoom.code.getImage.getForegroundImage import getForegroundImage
import pickle
from zebrazoom.mainZZ import mainZZ
import json
import os

from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtWidgets import QApplication, QFileDialog, QGridLayout, QLabel, QMessageBox, QVBoxLayout

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
  argv         = []
  return [pathToVideo, videoName, videoExt, configFile, argv]


def chooseVideoToCreateConfigFileFor(self, controller, reloadConfigFile):

  if int(reloadConfigFile):

    configFileName, _ =  QFileDialog.getOpenFileName(self.window, "Select configuration file", paths.getConfigurationFolder(), "JSON (*.json)")
    if not configFileName:
      return False
    try:
      with open(configFileName) as f:
        self.configFile = json.load(f)
    except (EnvironmentError, json.JSONDecodeError) as e:
      QMessageBox.critical(self.window, "Could not read config file", "Config file couldn't be read: %s\n" % str(e))
      return False
    self.savedConfigFile = self.configFile.copy()

  self.videoToCreateConfigFileFor, _ = QFileDialog.getOpenFileName(self.window, "Select video to create config file for", os.path.expanduser("~"), "All files(*)")
  if not self.videoToCreateConfigFileFor:
    self.configFile.clear()
    return False
  return True


@util.addToHistory
def chooseGeneralExperimentFirstStep(self, controller, freeZebra, headEmbZebra, drosophilia, rodent, other, fastScreen):
  if int(fastScreen):
    controller.show_frame("HomegeneousWellsLayout")
  else:
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


def _getRegion(controller):
  cap = zzVideoReading.VideoCapture(controller.videoToCreateConfigFileFor)
  cap.set(1, 10)
  ret, frame = cap.read()
  back = False
  def backClicked():
    nonlocal back
    back = True
  rect = util.getRectangle(frame, "Click on the top left and bottom right of the region of interest", backBtnCb=backClicked)
  if back:
    controller.window.centralWidget().layout().setCurrentIndex(0)
    controller.configFileHistory[-2]()
    return None
  return rect


@util.addToHistory
def wellOrganisation(self, controller, circular, rectangular, roi, other, multipleROIs, groupSameSizeAndShapeEquallySpacedWells):
  if multipleROIs:
    controller.show_frame("NbRegionsOfInterest")
  else:
    if groupSameSizeAndShapeEquallySpacedWells:
      self.shape = 'groupSameSizeAndShapeEquallySpacedWells'
      self.configFile["groupOfMultipleSameSizeAndShapeEquallySpacedWells"] = 1
      controller.show_frame("CircularOrRectangularWells")
    else:
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
            rect = _getRegion(controller)
            if rect is None:
              return
            self.configFile["oneWellManuallyChosenTopLeft"], self.configFile["oneWellManuallyChosenBottomRight"] = rect
            self.configFile["nbWells"] = 1
            util.addToHistory(chooseBeginningAndEndOfVideo)(self, controller)
          else:
            self.configFile["noWellDetection"] = 1
            self.configFile["nbWells"] = 1
            chooseBeginningAndEndOfVideo(self, controller)


@util.addToHistory
def regionsOfInterest(self, controller, nbwells):

  self.configFile["multipleROIsDefinedDuringExecution"] = 1
  self.configFile["nbWells"] = int(nbwells)

  chooseBeginningAndEndOfVideo(self, controller)


def rectangularWells(self, controller, nbwells, nbRowsOfWells, nbWellsPerRows):

  [pathToVideo, videoName, videoExt, configFile, argv] = getMainArguments(self)

  configFile["adjustRectangularWellsDetect"] = 1

  app = QApplication.instance()
  with app.busyCursor():
    try:
      mainZZ(pathToVideo, videoName, videoExt, configFile, argv)
    except ValueError:
      newhyperparameters = pickle.load(open(os.path.join(paths.getRootDataFolder(), 'newhyperparameters'), 'rb'))
      for index in newhyperparameters:
        configFile[index] = newhyperparameters[index]
    except NameError:
      print("Configuration file parameters changes discarded.")

  configFile["adjustRectangularWellsDetect"] = 0

  self.configFile = configFile

  chooseBeginningAndEndOfVideo(self, controller)


@util.addToHistory
def homegeneousWellsLayout(self, controller, nbRowsOfWells, nbWellsPerRows, detectBouts):

  self.configFile = {"trackingMethod": "fastCenterOfMassTracking_KNNbackgroundSubtraction", "nbAnimalsPerWell": 1, "nbWells": 8, "nbRowsOfWells": 2, "nbWellsPerRows": 4, "groupOfMultipleSameSizeAndShapeEquallySpacedWells": 1, "postProcessMultipleTrajectories": 0, "trackingPointSizeDisplay": 3, "extractAdvanceZebraParameters": 0,  "validationVideoPlotHeading": 0, "trackTail": 0, "freqAlgoPosFollow": 100, "fasterMultiprocessing": 1, "copyOriginalVideoToOutputFolderForValidation": 0, "backgroundSubtractorKNN": 1, "boutsMinNbFrames": 0, "addOneFrameAtTheEndForBoutDetection": 1, "fillGapFrameNb": 0} # "postProcessMultipleTrajectories": 1, "postProcessRemoveLowProbabilityDetection" : 1, "postProcessLowProbabilityDetectionPercentOfMaximum" : 0.2

  self.configFile["nbWells"] = int(nbRowsOfWells) * int(nbWellsPerRows)
  self.configFile["nbRowsOfWells"] = int(nbRowsOfWells)
  self.configFile["nbWellsPerRows"] = int(nbWellsPerRows)
  self.configFile["noBoutsDetection"] = int(not detectBouts)

  if detectBouts:
    controller.calculateBackgroundFreelySwim(controller, 0, boutDetectionsOnly=True)
  else:
    controller.show_frame("FinishConfig")


@util.addToHistory
def morePreciseFastScreen(self, controller, nbRowsOfWells, nbWellsPerRows, detectBouts):

  # The gaussian image filtering should be added here in the future
  self.configFile = {"trackingMethod": "fastCenterOfMassTracking_ClassicalBackgroundSubtraction", "minPixelDiffForBackExtract": 20, "backgroundPreProcessParameters": [[3]], "backgroundPreProcessMethod": ["erodeThenMin"], "trackingPointSizeDisplay": 1, "nbAnimalsPerWell": 1, "extractAdvanceZebraParameters": 0, "trackTail": 0, "nbWells": 1, "noWellDetection": 1, "backgroundExtractionForceUseAllVideoFrames": 1, "headSize": 2, "createValidationVideo": 0, "lastFrame": 1000}

  self.configFile["nbAnimalsPerWell"] = int(nbRowsOfWells) * int(nbWellsPerRows)

  # self.configFile["nbWells"]          = int(nbwells)

  self.configFile["nbRowsOfWells"] = int(nbRowsOfWells)
  self.configFile["nbWellsPerRows"] = int(nbWellsPerRows)
  self.configFile["noBoutsDetection"] = int(not detectBouts)

  self.calculateBackgroundFreelySwim(controller, 0, morePreciseFastScreen=True, boutDetectionsOnly=detectBouts)

  # controller.show_frame("FinishConfig")


@util.addToHistory
def circularOrRectangularWells(self, controller, nbRowsOfWells, nbWellsPerRows, nbanimals):
  self.configFile["nbWells"]        = int(nbRowsOfWells) * int(nbWellsPerRows)
  self.configFile["nbAnimalsPerWell"] = int(nbanimals)
  self.configFile["nbRowsOfWells"]  = int(nbRowsOfWells)
  self.configFile["nbWellsPerRows"]  = int(nbWellsPerRows)

  if self.shape == 'circular':
    controller.show_frame("ChooseCircularWellsLeft")
  else:
    if self.shape == 'groupSameSizeAndShapeEquallySpacedWells':
      chooseBeginningAndEndOfVideo(self, controller)
    else:
      rectangularWells(self, controller, self.configFile["nbWells"], nbRowsOfWells, nbWellsPerRows)


@util.addToHistory
def chooseCircularWellsLeft(self, controller):
  cap = zzVideoReading.VideoCapture(self.videoToCreateConfigFileFor)
  ret, frame = cap.read()
  wellLeft = findWellLeft(frame)
  if wellLeft is None:
    return
  [x, y] = wellLeft
  self.wellLeftBorderX = x
  self.wellLeftBorderY = y
  util.addToHistory(controller.show_frame)("ChooseCircularWellsRight")

@util.addToHistory
def chooseCircularWellsRight(self, controller):
  cap = zzVideoReading.VideoCapture(self.videoToCreateConfigFileFor)
  ret, frame = cap.read()
  wellRight = findWellRight(frame)
  if wellRight is None:
    return
  [xRight, yRight] = wellRight
  xLeft = self.wellLeftBorderX
  yLeft = self.wellLeftBorderY
  dist = math.sqrt((xLeft - xRight)**2 + (yLeft - yRight)**2)
  self.configFile["minWellDistanceForWellDetection"] = int(dist)
  self.configFile["wellOutputVideoDiameter"]         = int(dist + dist * 0.2)
  util.addToHistory(chooseBeginningAndEndOfVideo)(self, controller)


@util.addToHistory
def _beginningAndEndChosen(self, controller):
  controller.window.centralWidget().layout().setCurrentIndex(0)
  if int(controller.configFile["headEmbeded"]) == 1:
    controller.show_frame("HeadEmbeded")
  else:
    if controller.organism == 'zebrafishNew':
      controller.show_frame("NumberOfAnimals2")
    elif controller.organism == 'zebrafish':
      controller.show_frame("NumberOfAnimals")
    else:
      self.configFile["trackingMethod"] = "classicCenterOfMassTracking"
      controller.show_frame("NumberOfAnimalsCenterOfMass")


@util.addToHistory
def _chooseEnd(self, controller):
  util.chooseEndPage(controller, controller.videoToCreateConfigFileFor, "Choose where the analysis of your video should end.", "Ok, I want the tracking to end at this frame!", lambda: _beginningAndEndChosen(self, controller))


def chooseBeginningAndEndOfVideo(self, controller):
  util.chooseBeginningPage(controller, controller.videoToCreateConfigFileFor, "Choose where the analysis of your video should start.", "Ok, I want the tracking to start at this frame!", lambda: _chooseEnd(self, controller),
                           extraButtonInfo=("I want the tracking to run on the entire video!", lambda: _beginningAndEndChosen(self, controller), {"background_color": util.DEFAULT_BUTTON_COLOR}))


def getImageForMultipleAnimalGUI(l, nx, ny, max_l, videoToCreateConfigFileFor, background, wellPositions, hyperparameters):

  [frame, a1, a2] = getForegroundImage(videoToCreateConfigFileFor, background, l, 0, [], hyperparameters)

  lengthX = nx * 2
  lengthY = ny

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

  if len(areaList):
    maxToReturn = int((max(areaList)+2)*2)
  else:
    maxToReturn = (len(thresh) * len(thresh[0]))/5

  return [frame, maxToReturn]


def _createWidget(layout, values, key, minn, maxx, name, updateFrame):
  slider = util.SliderWithSpinbox(values[key], minn, maxx, name=name)

  def valueChanged():
    values[key] = slider.value()
    updateFrame()
  slider.valueChanged.connect(valueChanged)

  if name != "Frame number":
    elements = layout.count() - 2  # frame, frameSlider
    row = elements // 2 + 2
    col = elements % 2
    layout.addWidget(slider, row, col, Qt.AlignmentFlag.AlignLeft if col else Qt.AlignmentFlag.AlignRight)
  else:
    layout.addWidget(slider, 1, 0, 1, 2, Qt.AlignmentFlag.AlignCenter)

  return slider


def identifyMultipleHead(self, controller, nbanimals):
  self.configFile["videoName"] = "configFilePrep"

  tempConfig = self.configFile

  app = QApplication.instance()
  with app.busyCursor():
    # Getting hyperparameters, wellPositions, and background
    hyperparameters = getHyperparametersSimple(tempConfig)
    wellPositions = util.addToHistory(findWells)(self.videoToCreateConfigFileFor, hyperparameters)
    background    = getBackground(self.videoToCreateConfigFileFor, hyperparameters)

  cur_dir_path = os.path.dirname(os.path.realpath(__file__))

  def imagesGenerator():
    images = (cv2.imread(os.path.join(cur_dir_path, 'no1.png')),
              cv2.imread(os.path.join(cur_dir_path, 'no2.png')),
              cv2.imread(os.path.join(cur_dir_path, 'ok1.png')))
    while True:
      yield from images
  images = imagesGenerator()

  label = QLabel()
  label.setMinimumSize(1, 1)
  layout = QVBoxLayout()
  layout.addWidget(label, alignment=Qt.AlignmentFlag.AlignCenter)
  timer = QTimer()
  timer.setInterval(2000)
  timer.timeout.connect(lambda: util.setPixmapFromCv(next(images), label))
  timer.start()
  util.showBlockingPage(layout, title="", buttons=(("Ok, I understand!", lambda: timer.stop()),), labelInfo=(next(images), label))

  # Manual parameters adjustements
  cap        = zzVideoReading.VideoCapture(self.videoToCreateConfigFileFor)
  nx         = int(cap.get(3))
  ny         = int(cap.get(4))
  max_l      = int(cap.get(7))

  hyperparameters["minArea"] = 5
  hyperparameters["maxArea"] = 800

  frameNum = {"frameNum": hyperparameters.get("firstFrame", 1)}
  minPixelDiffForBackExtract = [hyperparameters["minPixelDiffForBackExtract"]]
  thresholdForBlobImg        = [hyperparameters["thresholdForBlobImg"]]
  dilateIter                 = [hyperparameters["dilateIter"]]
  minArea                    = [hyperparameters["minArea"]]
  maxArea                    = [hyperparameters["maxArea"]]
  firstFrame = hyperparameters["firstFrame"] if "firstFrame" in hyperparameters else 1
  lastFrame  = hyperparameters["lastFrame"]-1 if "lastFrame" in hyperparameters else max_l - 10

  frame, maxAreaBlobs = getImageForMultipleAnimalGUI(frameNum["frameNum"], nx, ny, max_l, self.videoToCreateConfigFileFor, background, wellPositions, hyperparameters)

  label = QLabel()
  label.setMinimumSize(1, 1)
  layout = QGridLayout()
  layout.addWidget(label, 0, 0, 1, 2, Qt.AlignmentFlag.AlignCenter)
  layout.setRowStretch(0, 1)

  def updateFrame():
    frame, maxAreaBlobs = getImageForMultipleAnimalGUI(frameNum["frameNum"], nx, ny, max_l, self.videoToCreateConfigFileFor, background, wellPositions, hyperparameters)
    util.setPixmapFromCv(frame, label)
    minAreaWidget.setMaximum(maxAreaBlobs)
    maxAreaWidget.setMaximum(maxAreaBlobs)

  _createWidget(layout, frameNum, "frameNum", firstFrame, lastFrame, "Frame number", updateFrame)
  _createWidget(layout, hyperparameters, "minPixelDiffForBackExtract", 0, 255, "Threshold left image", updateFrame)
  _createWidget(layout, hyperparameters, "thresholdForBlobImg", 0, 255, "Threshold right image", updateFrame)
  _createWidget(layout, hyperparameters, "dilateIter", 0, 15, "Area dilatation", updateFrame)
  minAreaWidget = _createWidget(layout, hyperparameters, "minArea", 0, maxAreaBlobs, "Minimum area", updateFrame)
  maxAreaWidget = _createWidget(layout, hyperparameters, "maxArea", 0, maxAreaBlobs, "Maximum area", updateFrame)

  util.showBlockingPage(layout, title="Adjust Parameters: As much as possible, you must see red points on and only on animals on the right image.", buttons=(("Ok, done!", None),), labelInfo=(frame, label))

  del self.configFile["videoName"]

  self.configFile["minPixelDiffForBackExtract"] = int(hyperparameters["minPixelDiffForBackExtract"])
  self.configFile["thresholdForBlobImg"]        = int(hyperparameters["thresholdForBlobImg"])
  self.configFile["dilateIter"]                 = int(hyperparameters["dilateIter"])
  self.configFile["minArea"]                    = int(hyperparameters["minArea"])
  self.configFile["maxArea"]                    = int(hyperparameters["maxArea"])
  self.configFile["headSize"]        = math.sqrt((int(hyperparameters["minArea"]) + int(hyperparameters["maxArea"])) / 2)


@util.addToHistory
def numberOfAnimals(nbanimals, animalsAlwaysVisible, forceBlobMethodForHeadTracking, detectBoutsMethod, recommendedMethod, calculateBends, adjustBackgroundExtractionBasedOnNumberOfBlackPixels):
  app = QApplication.instance()

  app.configFile["noBoutsDetection"] = 1
  app.configFile["noChecksForBoutSelectionInExtractParams"] = 1
  app.configFile["trackingPointSizeDisplay"] = 4
  app.configFile["validationVideoPlotHeading"] = 0

  if calculateBends:
    app.configFile["extractAdvanceZebraParameters"] = 1

  nbanimals = int(nbanimals) if nbanimals is not None else app.configFile["nbWells"] * app.configFile["nbAnimalsPerWell"]
  if nbanimals == app.configFile["nbWells"]:
    app.configFile["nbAnimalsPerWell"] = 1
  else:
    app.configFile["nbAnimalsPerWell"] = int(nbanimals / app.configFile["nbWells"])
    app.configFile["multipleHeadTrackingIterativelyRelaxAreaCriteria"] = int(animalsAlwaysVisible)

  app.forceBlobMethodForHeadTracking = int(forceBlobMethodForHeadTracking)
  if app.forceBlobMethodForHeadTracking:
    app.configFile["forceBlobMethodForHeadTracking"] = app.forceBlobMethodForHeadTracking

  if app.organism == 'zebrafish':
    app.show_frame("IdentifyHeadCenter")
  elif app.organism == 'zebrafishNew':
    automaticallyFindOptimalParameters(app, app, True, detectBoutsMethod, not recommendedMethod, not animalsAlwaysVisible, adjustBackgroundExtractionBasedOnNumberOfBlackPixels)
    app.window.centralWidget().layout().currentWidget().refreshPage(showFasterTracking=not adjustBackgroundExtractionBasedOnNumberOfBlackPixels)
  elif app.organism == 'drosoorrodent' and recommendedMethod:
    automaticallyFindOptimalParameters(app, app, True, 0, False, not animalsAlwaysVisible, adjustBackgroundExtractionBasedOnNumberOfBlackPixels)
    app.window.centralWidget().layout().currentWidget().refreshPage(showFasterTracking=not adjustBackgroundExtractionBasedOnNumberOfBlackPixels)
  else:
    identifyMultipleHead(app, app, nbanimals)
    util.addToHistory(app.show_frame)("FinishConfig")
    app.window.centralWidget().layout().currentWidget().refreshPage(showFasterTracking=not adjustBackgroundExtractionBasedOnNumberOfBlackPixels)


@util.addToHistory
def chooseHeadCenter(self, controller):
  cap = zzVideoReading.VideoCapture(self.videoToCreateConfigFileFor)
  ret, frame = cap.read()
  headCenter = findHeadCenter(frame)
  if headCenter is None:
    return
  [x, y] = headCenter
  self.headCenterX = x
  self.headCenterY = y
  util.addToHistory(controller.show_frame)("IdentifyBodyExtremity")


@util.addToHistory
def chooseBodyExtremity(self, controller):
  cap = zzVideoReading.VideoCapture(self.videoToCreateConfigFileFor)
  ret, frame = cap.read()
  bodyExtremity = findBodyExtremity(frame)
  if bodyExtremity is None:
    return
  [extX, extY] = bodyExtremity
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

  util.addToHistory(controller.show_frame)("GoToAdvanceSettings")


@util.addToHistory
def goToAdvanceSettings(self, controller, yes, no):

  if int(no):
    controller.show_frame("FinishConfig")
  else:
    self.configFile["noBoutsDetection"] = 0
    self.calculateBackgroundFreelySwim(controller, 0)
