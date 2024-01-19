import numpy as np
import json
import cv2
import zebrazoom.videoFormatConversion.zzVideoReading as zzVideoReading
import math
from zebrazoom.code.getHyperparameters import getHyperparametersSimple
from zebrazoom.zebraZoomVideoAnalysis import ZebraZoomVideoAnalysis
import pickle
import json
import os
import re
from zebrazoom.code.findWells import findWells
from zebrazoom.code.GUI.adjustParameterInsideAlgoFunctions import prepareConfigFileForParamsAdjustements
import zebrazoom.code.paths as paths
import zebrazoom.code.util as util

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QApplication, QHBoxLayout, QLabel, QPushButton, QVBoxLayout

from zebrazoom.code.tracking import get_default_tracking_method


def _selectWell(app, cap, wellPositions):
  layout = QVBoxLayout()

  app.wellPositions = [(position['topLeftX'], position['topLeftY'], position['lengthX'], position['lengthY'])
                       for position in wellPositions]

  firstFrame = app.configFile.get("firstFrame", 1)
  maxFrame = app.configFile.get("lastFrame", cap.get(7) - 1)
  frameSlider = util.SliderWithSpinbox(firstFrame, 0, maxFrame, name="Frame")

  def getFrame():
    cap.set(1, frameSlider.value())
    ret, frame = cap.read()
    return frame
  frameSlider.valueChanged.connect(lambda: util.setPixmapFromCv(getFrame(), video))

  img = getFrame()
  height, width = img.shape[:2]
  video = util.WellSelectionLabel(width, height)
  layout.addWidget(video, alignment=Qt.AlignmentFlag.AlignCenter, stretch=1)

  sublayout = QHBoxLayout()
  sublayout.addStretch(1)
  sublayout.addWidget(frameSlider, alignment=Qt.AlignmentFlag.AlignCenter)
  if maxFrame - firstFrame > 1000:
    adjustLayout = QVBoxLayout()
    adjustLayout.setSpacing(0)
    adjustLayout.addStretch()
    zoomInSliderBtn = QPushButton("Zoom in slider")

    def updatePreciseFrameSlider(value):
      if frameSlider.minimum() == value and frameSlider.minimum():
        frameSlider.setMinimum(frameSlider.minimum() - 1)
        frameSlider.setMaximum(frameSlider.maximum() - 1)
      elif value == frameSlider.maximum() and frameSlider.maximum() != maxFrame:
        frameSlider.setMinimum(frameSlider.minimum() + 1)
        frameSlider.setMaximum(frameSlider.maximum() + 1)

    def zoomInButtonClicked():
      if "in" in zoomInSliderBtn.text():
        zoomInSliderBtn.setText("Zoom out slider")
        value = frameSlider.value()
        minimum = value - 250
        maximum = value + 250
        if minimum < 0:
          maximum = 500
          minimum = 0
        if maximum > frameSlider.maximum():
          maximum = frameSlider.maximum()
          minimum = maximum - 500
        frameSlider.setMinimum(max(0, minimum))
        frameSlider.setMaximum(min(frameSlider.maximum(), maximum))
        frameSlider.setValue(value)
        frameSlider.valueChanged.connect(updatePreciseFrameSlider)
      else:
        zoomInSliderBtn.setText("Zoom in slider")
        frameSlider.setMinimum(0)
        frameSlider.setMaximum(maxFrame)
        frameSlider.valueChanged.disconnect(updatePreciseFrameSlider)
    zoomInSliderBtn.clicked.connect(zoomInButtonClicked)
    adjustLayout.addWidget(QLabel())
    adjustLayout.addWidget(zoomInSliderBtn, alignment=Qt.AlignmentFlag.AlignLeft, stretch=1)
    adjustLayout.addStretch()
    sublayout.addLayout(adjustLayout)
  sublayout.addStretch(1)
  layout.addLayout(sublayout)

  cancelled = False
  def cancelCb():
    nonlocal cancelled
    cancelled = True
  buttons = (("Cancel", cancelCb, True), ("Ok", None, True, None, util.DEFAULT_BUTTON_COLOR))
  util.showBlockingPage(layout, title='Select the well with the most movement', buttons=buttons, labelInfo=(img, video, False))
  wellNumber = None if cancelled else video.getWell()
  del app.wellPositions
  return wellNumber


def findWellWithMostMovement(cap, wellPositions):
  max_l = int(cap.get(7))
  cap.set(1, 0)
  ret, firstFrame = cap.read()
  firstFrame = cv2.cvtColor(firstFrame, cv2.COLOR_BGR2GRAY)
  cap.set(1, max_l-1)
  ret, lastFrame = cap.read()
  while not(ret):
    max_l = max_l - 1
    cap.set(1, max_l-1)
    ret, lastFrame = cap.read()
  lastFrame = cv2.cvtColor(lastFrame, cv2.COLOR_BGR2GRAY)
  pixelsChange = np.zeros((len(wellPositions)))
  for wellNumberId in range(0, len(wellPositions)):
    xtop  = wellPositions[wellNumberId]['topLeftX']
    ytop  = wellPositions[wellNumberId]['topLeftY']
    lenX  = wellPositions[wellNumberId]['lengthX']
    lenY  = wellPositions[wellNumberId]['lengthY']
    firstFrameROI = firstFrame[ytop:ytop+lenY, xtop:xtop+lenX]
    lastFrameROI  = lastFrame[ytop:ytop+lenY, xtop:xtop+lenX]
    pixelsChange[wellNumberId] = np.sum(abs(firstFrameROI-lastFrameROI)) / np.sum(abs(firstFrameROI)) if np.sum(abs(firstFrameROI)) else 0
  return np.argmax(pixelsChange)


def getGroundTruthFromUser(self, controller, nbOfImagesToManuallyClassify, saveIntermediary, zebrafishToTrack, wellNumber=None):
  
  firstFrameIndex = self.configFile["firstFrame"] if "firstFrame" in self.configFile else -1
  lastFrameIndex  = self.configFile["lastFrame"]  if "lastFrame"  in self.configFile else -1
  
  videoPath = self.videoToCreateConfigFileFor
  
  for m in re.finditer('/', videoPath):
    last = m.start()
    pathToVideo      = videoPath[:last+1]
    videoNameWithExt = videoPath[last+1:]
    allDotsPositions = [m.start() for m in re.finditer('\.', videoNameWithExt)]
    pointPos  = allDotsPositions[len(allDotsPositions)-1]
    videoName = videoNameWithExt[:pointPos]
    videoExt  = videoNameWithExt[pointPos+1:]
  
  initialConfigFile = self.configFile
  
  initialHyperparameters = getHyperparametersSimple(initialConfigFile)
  initialHyperparameters["videoName"]      = videoName
  initialConfigFile["exitAfterWellsDetection"] = 1
  app = QApplication.instance()
  app.wellPositions = wellPositions = []
  try:
    storeH5 = initialConfigFile.get('storeH5')
    initialConfigFile['storeH5'] = 1
    with app.busyCursor():
      ZebraZoomVideoAnalysis(pathToVideo, videoName, videoExt, initialConfigFile, ["outputFolder", app.ZZoutputLocation]).run()
  except ValueError:
    pass
  finally:
    if storeH5 is not None:
      initialConfigFile['storeH5'] = storeH5
    else:
      del initialConfigFile['storeH5']
    del initialConfigFile["exitAfterWellsDetection"]
    del app.wellPositions
  if not wellPositions:
    return None
  wellPositions = [dict(zip(('topLeftX', 'topLeftY', 'lengthX', 'lengthY'), values)) for values in wellPositions]

  cap   = zzVideoReading.VideoCapture(videoPath)
  max_l = int(cap.get(7))

  if wellNumber is None:
    # Finding the well with the most movement
    wellNumber = findWellWithMostMovement(cap, wellPositions)
  
  backCalculationStep = int(max_l / nbOfImagesToManuallyClassify) if (firstFrameIndex == -1 or lastFrameIndex == -1) else int((lastFrameIndex - firstFrameIndex + 1) / nbOfImagesToManuallyClassify)
  data = [None] * ((max_l - 1) // backCalculationStep + 1)
  
  k = firstFrameIndex if firstFrameIndex != -1 else 0
  firstK = k
  while k < (lastFrameIndex if lastFrameIndex != -1 else max_l):
      
    cap.set(1, k)
    ret, frame = cap.read()
    
    if ret:
      
      xtop  = wellPositions[wellNumber]['topLeftX']
      ytop  = wellPositions[wellNumber]['topLeftY']
      lenX  = wellPositions[wellNumber]['lengthX']
      lenY  = wellPositions[wellNumber]['lengthY']
      frame = frame[ytop:ytop+lenY, xtop:xtop+lenX]

      changeWell = False
      def changeWellCallback(video):
        nonlocal changeWell
        changeWell = True

      def callback():
        nonlocal k
        k -= backCalculationStep
      oldk = k
      if data[k//backCalculationStep] is None:
        extraButtons = (('Switch well', changeWellCallback, True),)
        headCoordinates = list(util.getPoint(frame, "Click on the center of the head of one animal" if zebrafishToTrack else "Click on the center of mass of an animal",
                                             backBtnCb=callback, zoomable=True, extraButtons=extraButtons))
        while changeWell:
          newWellNumber = _selectWell(controller, cap, wellPositions)
          if newWellNumber is None:
            changeWell = False
            headCoordinates = list(util.getPoint(frame, "Click on the center of the head of one animal" if zebrafishToTrack else "Click on the center of mass of an animal",
                                                 backBtnCb=callback, zoomable=True, extraButtons=extraButtons))
          else:
            return getGroundTruthFromUser(self, controller, nbOfImagesToManuallyClassify, saveIntermediary, zebrafishToTrack, wellNumber=newWellNumber)
      else:
        headCoordinates = data[k//backCalculationStep]["headCoordinates"]
      if oldk != k:
        if k >= 0:
          continue
        elif initialHyperparameters["groupOfMultipleSameSizeAndShapeEquallySpacedWells"] or initialHyperparameters["multipleROIsDefinedDuringExecution"]:
          return getGroundTruthFromUser(self, controller, nbOfImagesToManuallyClassify, saveIntermediary, zebrafishToTrack, wellNumber=wellNumber)
        else:
          QApplication.instance().configFileHistory[-2]()
          return None
      frame2 = cv2.circle(frame, tuple(headCoordinates), 2, (0, 0, 255), -1)

      goToOptimize = False
      def callback2():
        nonlocal goToOptimize
        goToOptimize = True
      extraButtons = (('I want to manually adjust tracking parameters', callback2, True, None),) if k == firstK else ()
      extraButtons += (('Switch well', changeWellCallback, True),)
      tailTipCoordinates = list(util.getPoint(frame2, "Click on the tip of the tail of the same animal" if zebrafishToTrack else "Click on a point on the border of the same animal",
                                backBtnCb=callback, zoomable=True, extraButtons=extraButtons))
      if goToOptimize:
        # TODO: add calculations here
        util.addToHistory(controller.optimizeConfigFile)()
        return None

      while changeWell:
        newWellNumber = _selectWell(controller, cap, wellPositions)
        if newWellNumber is None:
          changeWell = False
          tailTipCoordinates = list(util.getPoint(frame2, "Click on the tip of the tail of the same animal" if zebrafishToTrack else "Click on a point on the border of the same animal",
                                                  backBtnCb=callback, zoomable=True, extraButtons=extraButtons))
        else:
          return getGroundTruthFromUser(self, controller, nbOfImagesToManuallyClassify, saveIntermediary, zebrafishToTrack, wellNumber=newWellNumber)

      if oldk != k:
        k = oldk
        if data[k//backCalculationStep] is not None:
          data[k//backCalculationStep] = None
        continue

      if True: # Centered on the animal
        minX = min(headCoordinates[0], tailTipCoordinates[0])
        maxX = max(headCoordinates[0], tailTipCoordinates[0])
        minY = min(headCoordinates[1], tailTipCoordinates[1])
        maxY = max(headCoordinates[1], tailTipCoordinates[1])
        lengthX = maxX - minX
        lengthY = maxY - minY
        
        widdeningFactor = 2
        minX = minX - int(widdeningFactor * lengthX)
        maxX = maxX + int(widdeningFactor * lengthX)
        minY = minY - int(widdeningFactor * lengthY)
        maxY = maxY + int(widdeningFactor * lengthY)
        
        oneWellManuallyChosenTopLeft     = [minX, minY]
        oneWellManuallyChosenBottomRight = [maxX, maxY]
      else: # Focused on the initial well
        oneWellManuallyChosenTopLeft     = [xtop, ytop]
        oneWellManuallyChosenBottomRight = [xtop + lenX, ytop + lenY]

      data[k//backCalculationStep] = {"image": frame, "headCoordinates": headCoordinates, "tailTipCoordinates": tailTipCoordinates, "oneWellManuallyChosenTopLeft": oneWellManuallyChosenTopLeft, "oneWellManuallyChosenBottomRight": oneWellManuallyChosenBottomRight, "frameNumber": k, "wellNumber": wellNumber}
      k += backCalculationStep

  if saveIntermediary:
    toSave    = [initialConfigFile, videoPath, data, wellPositions, pathToVideo, videoNameWithExt, videoName, videoExt, zebrafishToTrack]
    pickle.dump(toSave, open(videoName + '_paramSet', 'wb'))
    
  cap.release()
  
  return [initialConfigFile, videoPath, data, wellPositions, pathToVideo, videoNameWithExt, videoName, videoExt]


def evaluateMinPixelDiffForBackExtractForCenterOfMassTracking(videoPath, background, image, wellPositions, hyperparameters, tailTipGroundTruth):
  [foregroundImage, o1, o2] = get_default_tracking_method()(videoPath, wellPositions, hyperparameters).getForegroundImage(background, image["frameNumber"], image["wellNumber"])
  ret, thresh = cv2.threshold(foregroundImage, hyperparameters["thresholdForBlobImg"], 255, cv2.THRESH_BINARY)
  thresh[0,:] = 255
  thresh[len(thresh)-1,:] = 255
  thresh[:,0] = 255
  thresh[:,len(thresh[0])-1] = 255
  contourClickedByUser = 0
  contours, hierarchy = cv2.findContours(thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
  tailTipDistError = 1000000000000000
  for contour in contours:
    dist = cv2.pointPolygonTest(contour, (float(image["headCoordinates"][0]), float(image["headCoordinates"][1])), True)
    if dist >= 0:
      for pt in contour:
        contourToPointOnBorderDistance = math.sqrt((pt[0][0] - tailTipGroundTruth[0])**2 + (pt[0][1] - tailTipGroundTruth[1])**2)
        if contourToPointOnBorderDistance < tailTipDistError:
          tailTipDistError = contourToPointOnBorderDistance
        
  return tailTipDistError

def findBestBackgroundSubstractionParameterForEachImage(data, videoPath, background, wellPositions, hyperparameters, videoName, zebrafishToTrack):
  
  data = [i for i in data if i]
  
  for image in data:
    
    oneWellManuallyChosenTopLeft     = image["oneWellManuallyChosenTopLeft"]
    oneWellManuallyChosenBottomRight = image["oneWellManuallyChosenBottomRight"]
    
    hyperparameters["oneWellManuallyChosenTopLeft"]     = oneWellManuallyChosenTopLeft
    hyperparameters["oneWellManuallyChosenBottomRight"] = oneWellManuallyChosenBottomRight
    hyperparameters["videoWidth"]    = oneWellManuallyChosenBottomRight[0] - oneWellManuallyChosenTopLeft[0]
    hyperparameters["videoHeight"]   = oneWellManuallyChosenBottomRight[1] - oneWellManuallyChosenTopLeft[1]
    
    hyperparameters["firstFrame"]    = image["frameNumber"]
    hyperparameters["lastFrame"]     = image["frameNumber"]
    hyperparameters["debugTracking"] = 0
    
    hyperparameters["fixedHeadPositionX"] = int(image["headCoordinates"][0])
    hyperparameters["fixedHeadPositionY"] = int(image["headCoordinates"][1])
    hyperparameters["midlineIsInBlobTrackingOptimization"] = 0
    
    bestMinPixelDiffForBackExtract = 10
    lowestTailTipDistError = 1000000000
    for minPixelDiffForBackExtract in range(3, 25):
      hyperparameters["minPixelDiffForBackExtract"] = minPixelDiffForBackExtract
      tailTipGroundTruth = image["tailTipCoordinates"]
      if zebrafishToTrack:
        trackingData = get_default_tracking_method()(videoPath, wellPositions, hyperparameters).runTracking(image["wellNumber"], background=background)
        tailTipPredicted = trackingData[0][0][0][len(trackingData[0][0][0])-1]
        if (trackingData[0][0][0][0][0] == tailTipPredicted[0] and trackingData[0][0][0][0][1] == tailTipPredicted[1]) or (trackingData[0][0][0][1][0] == tailTipPredicted[0] and trackingData[0][0][0][1][1] == tailTipPredicted[1]):
          tailTipDistError = 1000000000
        else:
          tailTipDistError = math.sqrt((tailTipGroundTruth[0] - tailTipPredicted[0])** 2 + (tailTipGroundTruth[1] - tailTipPredicted[1])**2)
      else:
        tailTipDistError = evaluateMinPixelDiffForBackExtractForCenterOfMassTracking(videoPath, background, image, wellPositions, hyperparameters, tailTipGroundTruth)
      
      if tailTipDistError < lowestTailTipDistError:
        lowestTailTipDistError = tailTipDistError
        bestMinPixelDiffForBackExtract = minPixelDiffForBackExtract
        
        if zebrafishToTrack:
          previousDataPoint = []
          tailLength = 0
          for dataPoint in trackingData[0][0][0]:
            if len(previousDataPoint):
              tailLength = tailLength + math.sqrt((dataPoint[0] - previousDataPoint[0])**2 + (dataPoint[1] - previousDataPoint[1])**2)
            previousDataPoint = dataPoint
          image["tailLength"] = tailLength
          image["tailLengthManual"] = math.sqrt((image["headCoordinates"][0] - tailTipGroundTruth[0])**2 + (image["headCoordinates"][1] - tailTipGroundTruth[1])**2)
      
      print("minPixelDiffForBackExtract:", minPixelDiffForBackExtract, "; tailTipDistError:", tailTipDistError)
    
    image["bestMinPixelDiffForBackExtract"] = bestMinPixelDiffForBackExtract
    image["lowestTailTipDistError"]         = lowestTailTipDistError
    
    if lowestTailTipDistError != 1000000000:
      hyperparameters["minPixelDiffForBackExtract"] = image["bestMinPixelDiffForBackExtract"]
      [foregroundImage, o1, o2] = get_default_tracking_method()(videoPath, wellPositions, hyperparameters).getForegroundImage(background, image["frameNumber"], image["wellNumber"])
      ret, thresh = cv2.threshold(foregroundImage, hyperparameters["thresholdForBlobImg"], 255, cv2.THRESH_BINARY)
      thresh[0,:] = 255
      thresh[len(thresh)-1,:] = 255
      thresh[:,0] = 255
      thresh[:,len(thresh[0])-1] = 255
      contourClickedByUser = 0
      contours, hierarchy = cv2.findContours(thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
      for contour in contours:
        dist = cv2.pointPolygonTest(contour, (float(image["headCoordinates"][0]), float(image["headCoordinates"][1])), True)
        if dist >= 0:
          contourClickedByUser = contour
      if not(type(contourClickedByUser) == int): # We found the contour that the user selected
        bodyContourArea = cv2.contourArea(contourClickedByUser)
        image["bodyContourArea"] = bodyContourArea
      else:
        image["bodyContourArea"] = -1
      
    del hyperparameters["fixedHeadPositionX"]
    del hyperparameters["fixedHeadPositionY"]
    del hyperparameters["midlineIsInBlobTrackingOptimization"]
  
  return data


def findInitialBlobArea(data, videoPath, background, wellPositions, hyperparameters, maxTailLengthManual):
  
  for image in data:
    
    if image["lowestTailTipDistError"] != 1000000000 and image["bodyContourArea"] and (not("tailLength" in image) or (image["tailLength"] < 10 * maxTailLengthManual)):
      
      bodyContourArea = image["bodyContourArea"]
      
      [foregroundImage, o1, o2] = get_default_tracking_method()(videoPath, wellPositions, hyperparameters).getForegroundImage(background, image["frameNumber"], image["wellNumber"])
      
      ret, thresh = cv2.threshold(foregroundImage, hyperparameters["thresholdForBlobImg"], 255, cv2.THRESH_BINARY)
      thresh[0,:] = 255
      thresh[len(thresh)-1,:] = 255
      thresh[:,0] = 255
      thresh[:,len(thresh[0])-1] = 255
      contourClickedByUser = 0
      contours, hierarchy = cv2.findContours(thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
      for contour in contours:
        dist = cv2.pointPolygonTest(contour, (float(image["headCoordinates"][0]), float(image["headCoordinates"][1])), True)
        if dist >= 0:
          contourClickedByUser = contour
      
      if not(type(contourClickedByUser) == int): # We found the contour that the user selected
        
        image["contourClickedByUser"] = contourClickedByUser
        image["headContourArea"] = cv2.contourArea(contourClickedByUser)
  
  return data


def boutDetectionParameters(data, configFile, pathToVideo, videoName, videoExt, wellPositions, videoPath):

  # Extracting Background and finding Wells

  configFile["exitAfterBackgroundExtraction"] = 1
  configFile["debugExtractBack"]              = 1
  configFile["debugFindWells"]                = 1
  configFile["reloadWellPositions"] = 1
  
  app = QApplication.instance()
  with app.busyCursor():
    try:
      storeH5 = configFile.get('storeH5')
      configFile['storeH5'] = 1
      ZebraZoomVideoAnalysis(pathToVideo, videoName, videoExt, configFile, ["outputFolder", app.ZZoutputLocation]).run()
    except ValueError:
      configFile["exitAfterBackgroundExtraction"] = 0
    finally:
      if storeH5 is not None:
        configFile['storeH5'] = storeH5
      else:
        del configFile['storeH5']

  del configFile["exitAfterBackgroundExtraction"]
  del configFile["debugExtractBack"]
  del configFile["debugFindWells"]
  del configFile["reloadWellPositions"]

  # Finding the frame with the most movement
  
  cap   = zzVideoReading.VideoCapture(videoPath)
  max_l = int(cap.get(7))
  
  wellNumber = data[0]["wellNumber"]
  xtop = wellPositions[wellNumber]['topLeftX']
  ytop = wellPositions[wellNumber]['topLeftY']
  lenX = wellPositions[wellNumber]['lengthX']
  lenY = wellPositions[wellNumber]['lengthY']
  
  print("xtop, ytop, lenX, lenY:", xtop, ytop, lenX, lenY)
  
  firstFrameNum  = 0
  lastFrameNum   = max_l - 1
  
  while abs(lastFrameNum - firstFrameNum) > 40:
    
    middleFrameNum = int((firstFrameNum + lastFrameNum) / 2)
    
    cap.set(1, firstFrameNum)
    ret, firstFrame = cap.read()
    firstFrame = cv2.cvtColor(firstFrame, cv2.COLOR_BGR2GRAY)
    
    cap.set(1, middleFrameNum)
    ret, middleFrame = cap.read()
    middleFrame = cv2.cvtColor(middleFrame, cv2.COLOR_BGR2GRAY)
    
    cap.set(1, lastFrameNum)
    ret, lastFrame = cap.read()
    while not(ret):
      lastFrameNum = lastFrameNum - 1
      cap.set(1, lastFrameNum)
      ret, lastFrame = cap.read()
    lastFrame = cv2.cvtColor(lastFrame, cv2.COLOR_BGR2GRAY)
    
    firstFrameROI  = firstFrame[ytop:ytop+lenY, xtop:xtop+lenX]
    middleFrameROI = middleFrame[ytop:ytop+lenY, xtop:xtop+lenX]
    lastFrameROI   = lastFrame[ytop:ytop+lenY, xtop:xtop+lenX]
    pixelsChangeFirstToMiddle = np.sum(abs(firstFrameROI-middleFrameROI))
    pixelsChangeMiddleToLast  = np.sum(abs(middleFrameROI-lastFrameROI))
    
    if pixelsChangeFirstToMiddle > pixelsChangeMiddleToLast:
      lastFrameNum  = middleFrameNum
    else:
      firstFrameNum = middleFrameNum
    
    print("intermediary: firstFrameNum:", firstFrameNum, "; lastFrameNum:", lastFrameNum)
    print("pixelsChangeFirstToMiddle:", pixelsChangeFirstToMiddle, "; pixelsChangeMiddleToLast:", pixelsChangeMiddleToLast)
    
  cap.release()
  
  print("wellNumber:", wellNumber, "; lastFrameNum:", lastFrameNum, "; firstFrameNum:", firstFrameNum)
  
  # Launching the interactive adjustement of hyperparameters related to the detection of bouts
  
  wellNumber = int(data[0]["wellNumber"])
  
  initialFirstFrameValue, initialLastFrameValue = prepareConfigFileForParamsAdjustements(configFile, wellNumber, configFile.get("firstFrame", 1), videoPath, False)
  configFile["firstFrame"] = lastFrameNum - 500 if lastFrameNum - 500 > 0 else 0
  configFile["lastFrame"]  = (configFile["firstFrame"] + 500) if (configFile["firstFrame"] + 500) < (max_l - 1) else (max_l - 1)
  
  configFile["noBoutsDetection"] = 0
  configFile["trackTail"]                   = 0
  configFile["adjustDetectMovWithRawVideo"] = 1
  configFile["reloadWellPositions"]         = 1
  
  if "thresForDetectMovementWithRawVideo" in configFile:
    if configFile["thresForDetectMovementWithRawVideo"] == 0:
      configFile["thresForDetectMovementWithRawVideo"] = 1
  else:
    configFile["thresForDetectMovementWithRawVideo"] = 1
  
  with app.busyCursor():
    try:
      storeH5 = configFile.get('storeH5')
      configFile['storeH5'] = 1
      ZebraZoomVideoAnalysis(pathToVideo, videoName, videoExt, configFile, ["outputFolder", app.ZZoutputLocation]).run()
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
  del configFile["trackTail"]
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
  
  del configFile["reloadBackground"]
  
  configFile["fillGapFrameNb"] = 2 # We would need to try to improve this in the future
  
  return configFile
