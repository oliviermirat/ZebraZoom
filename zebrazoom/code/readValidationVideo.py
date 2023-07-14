import math
import os
import sys

import cv2
import json
import numpy as np

from PyQt5.QtCore import Qt, QSize, QTimer
from PyQt5.QtWidgets import QApplication, QCheckBox, QFileDialog, QMessageBox, QLabel, QSlider, QStyleOptionSlider, QVBoxLayout

import zebrazoom.code.paths as paths
import zebrazoom.code.util as util
import zebrazoom.videoFormatConversion.zzVideoReading as zzVideoReading
from zebrazoom.code.createValidationVideo import calculateInfoFrame, drawInfoFrame
from zebrazoom.code.getHyperparameters import getHyperparametersSimple
from zebrazoom.code.preprocessImage import preprocessImage


def getFramesCallback(videoPath, folderName, numWell, numAnimal, zoom, start, framesToShow=0, ZZoutputLocation='', supstruct=None, config=None):
  s1  = "ZZoutput"
  s2  = folderName
  s3b = "results_"
  s4  = folderName
  s5  = ".avi"
  s5b = ".txt"

  if len(ZZoutputLocation):
    initialPath = ZZoutputLocation
  else:
    initialPath = paths.getDefaultZZoutputFolder()

  if config is None:
    with open(os.path.join(initialPath, os.path.join(s2, 'configUsed.json'))) as f:
      config = json.load(f)
  hyperparameters = getHyperparametersSimple(config)

  if os.path.splitext(folderName)[1] != '.h5':
    folderPath = os.path.join(initialPath, folderName)
    resultFile = next((f for f in os.listdir(folderPath) if os.path.isfile(os.path.join(folderPath, f)) and os.path.splitext(f)[1] == '.txt' and f.startswith('results_')), None)
    if resultFile is None:
      return
    resultsPath = os.path.join(initialPath, folderName, resultFile)
    if supstruct is None:
      with open(resultsPath) as f:
        supstruct = json.load(f)
  else:
    resultsPath = os.path.join(initialPath, folderName)
  
  if "pathToOriginalVideo" in supstruct:
    videoPath = supstruct["pathToOriginalVideo"]
    if not os.path.exists(videoPath):
      app = QApplication.instance()
      if QMessageBox.critical(app.window, "Video not found", "Cannot display the validation video because the video used to run the tracking can no longer be found. Would you like to update the video path stored in the results file?",
                              buttons=QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, defaultButton=QMessageBox.StandardButton.Yes) != QMessageBox.StandardButton.Yes:
        return None
      videoName, _ = QFileDialog.getOpenFileName(app.window, 'Select video', os.path.expanduser("~"))
      if not videoName:
        return
      videoPath = supstruct["pathToOriginalVideo"] = videoName
      if os.path.splitext(resultsPath)[1] != '.h5':
        with open(resultsPath, 'w') as f:
          json.dump(supstruct, f)
      else:
        import h5py
        with h5py.File(resultsPath, 'a') as results:
          results.attrs['pathToOriginalVideo'] = videoName
  else:
    if hyperparameters["copyOriginalVideoToOutputFolderForValidation"] and os.path.exists(os.path.join(initialPath, os.path.join(s1, os.path.join(s2, 'originalVideoWithoutAnyTrackingDisplayed_pleaseUseTheGUIToVisualizeTrackingPoints.avi')))):
      # The "exist" check above is only to insure compatibility with videos tracked prior to this update
      if os.path.splitext(resultsPath)[1] != '.h5':
        videoPath = os.path.join(initialPath, os.path.join(s2, 'originalVideoWithoutAnyTrackingDisplayed_pleaseUseTheGUIToVisualizeTrackingPoints.avi'))
      else:
        videoPath = f'{os.path.splitext(resultsPath)[0]}_originalVideoWithoutAnyTrackingDisplayed_pleaseUseTheGUIToVisualizeTrackingPoints.avi'
    else:
      if os.path.splitext(resultsPath)[1] != '.h5':
        videoPath = os.path.join(initialPath, os.path.join(s2, s4 + s5))
      else:
        videoPath = f'{os.path.splitext(resultsPath)[0]}.avi'

  if not(os.path.exists(videoPath)) and os.path.splitext(resultsPath)[1] != '.h5':
    mypath = os.path.join(initialPath, s2)
    onlyfiles = [f for f in os.listdir(mypath) if os.path.isfile(os.path.join(mypath, f))]
    resultFile = ''
    for fileName in onlyfiles:
      if '.avi' in fileName:
        resultFile = fileName
    videoPath = os.path.join(initialPath, os.path.join(s2, resultFile))

  if not os.path.isfile(videoPath):
    app = QApplication.instance()
    QMessageBox.critical(app.window, "Video not found", "Cannot display the validation video because it could not be found.")
    return

  cap = zzVideoReading.VideoCapture(videoPath)

  nx    = int(cap.get(3))
  ny    = int(cap.get(4))
  max_l = int(cap.get(7))
  if max_l == 1:
    return None
  frameRange = (supstruct["firstFrame"], supstruct["lastFrame"] - 1) if hyperparameters["copyOriginalVideoToOutputFolderForValidation"] or "pathToOriginalVideo" in supstruct else (0, max_l -1)

  if not("firstFrame" in supstruct):
    supstruct["firstFrame"] = 1
    print("supstruct['firstFrame'] not found")

  infoWells = []

  HeadX = np.zeros(max_l + supstruct["firstFrame"])
  HeadY = np.zeros(max_l + supstruct["firstFrame"])

  if ((numWell != -1) and (zoom)):
    lastEnd = 0
    lastXpos = supstruct["wellPoissMouv"][numWell][numAnimal][0]["HeadX"][0]
    lastYpos = supstruct["wellPoissMouv"][numWell][numAnimal][0]["HeadY"][0]
    for k in range(0,len(supstruct["wellPoissMouv"][numWell][numAnimal])):
      beg = supstruct["wellPoissMouv"][numWell][numAnimal][k]["BoutStart"]
      end = supstruct["wellPoissMouv"][numWell][numAnimal][k]["BoutEnd"]
      for l in range(lastEnd, beg):
        HeadX[l] = lastXpos
        HeadY[l] = lastYpos
      for l in range(beg, end):
        HeadX[l]  = supstruct["wellPoissMouv"][numWell][numAnimal][k]["HeadX"][l-beg]
        HeadY[l]  = supstruct["wellPoissMouv"][numWell][numAnimal][k]["HeadY"][l-beg]
      lastEnd = end
      lastXpos = supstruct["wellPoissMouv"][numWell][numAnimal][k]["HeadX"][end-1-beg]
      lastYpos = supstruct["wellPoissMouv"][numWell][numAnimal][k]["HeadY"][end-1-beg]

    for l in range(lastEnd, max_l + supstruct["firstFrame"]):
      HeadX[l] = lastXpos
      HeadY[l] = lastYpos

  # /* Getting the info about well positions */
  analyzeAllWellsAtTheSameTime = 0
  if (analyzeAllWellsAtTheSameTime == 0):
    for i in range(0, len(supstruct["wellPositions"])):
      x = 0
      y = 0
      lengthX = 0
      lengthY = 0
      rectangleWellArea = 1
      if (rectangleWellArea == 0): # circular wells
        x = supstruct["wellPositions"][i]["topLeftX"]
        y = supstruct["wellPositions"][i]["topLeftY"]
        r = supstruct["wellPositions"][i]["diameter"]
        lengthX = 300 # wellOutputVideoDiameter;
        lengthY = 300 # wellOutputVideoDiameter;
      else:
        x = supstruct["wellPositions"][i]["topLeftX"]
        y = supstruct["wellPositions"][i]["topLeftY"]
        lengthX = supstruct["wellPositions"][i]["lengthX"]
        lengthY = supstruct["wellPositions"][i]["lengthY"]
      if (x < 0):
        x = 0
      if (y < 0):
        y = 0
      infoWells.append([x, y, lengthX, lengthY])
  else:
    infoWells.append([0, 0, nx, ny])
  
  infoFrame = None
  if hyperparameters["copyOriginalVideoToOutputFolderForValidation"] or "pathToOriginalVideo" in supstruct:
    infoFrame, colorModifTab = calculateInfoFrame(supstruct, hyperparameters, max_l)
  
  x = 0
  y = 0
  lengthX = 0
  lengthY = 0
  if (numWell != -1):
    x = infoWells[numWell][0]
    y = infoWells[numWell][1]
    lengthX = infoWells[numWell][2]
    lengthY = infoWells[numWell][3]
  else:
    lengthX = nx
    lengthY = ny

  l = start - supstruct["firstFrame"] + 1 if start > 0 else 0
  if hyperparameters["copyOriginalVideoToOutputFolderForValidation"] or "pathToOriginalVideo" in supstruct:
    l += supstruct["firstFrame"]

  xOriginal = x
  yOriginal = y

  def getFrame(frameSlider, timer=None, plotTrackingPointsCheckbox=None, stopTimer=True):
    nonlocal x
    nonlocal y
    nonlocal lengthX
    nonlocal lengthY

    l = frameSlider.value()
    if timer is not None and timer.isActive() and (l == frameSlider.maximum() or stopTimer):
      timer.stop()

    cap.set(1, l)
    ret, img = cap.read()
    
    if hyperparameters["imagePreProcessMethod"]:
      img = preprocessImage(img, hyperparameters)
    
    if infoFrame is not None and plotTrackingPointsCheckbox is not None and plotTrackingPointsCheckbox.isChecked():
      drawInfoFrame(l, img, infoFrame, colorModifTab, hyperparameters)

    if numWell != -1 and zoom:
      length = 250
      xmin = int(HeadX[l + supstruct["firstFrame"] - 1] - length/2)
      xmax = int(HeadX[l + supstruct["firstFrame"] - 1] + length/2)
      ymin = int(HeadY[l + supstruct["firstFrame"] - 1] - length/2)
      ymax = int(HeadY[l + supstruct["firstFrame"] - 1] + length/2)

      x = max(xmin + xOriginal, 0)
      y = max(ymin + yOriginal, 0)
      lengthX = xmax - xmin
      lengthY = ymax - ymin

      if y + lengthY >= len(img):
        lengthY = len(img) - y - 1
      if x + lengthX >= len(img[0]):
        lengthX = len(img[0]) - x - 1

    if (numWell != -1):
      img = img[y:y+lengthY, x:x+lengthX]

    frameNumber = l if hyperparameters["copyOriginalVideoToOutputFolderForValidation"] or "pathToOriginalVideo" in supstruct else (l + supstruct["firstFrame"])
    if lengthX > 100 and lengthY > 100:
      font = cv2.FONT_HERSHEY_SIMPLEX
      cv2.putText(img,str(frameNumber),(int(lengthX-110), int(lengthY-30)),font,1,(0,255,0))
    else:
      blank_image = np.zeros((len(img)+30, len(img[0]), 3), np.uint8)
      blank_image[0:len(img), 0:len(img[0])] = img
      img = blank_image
      font = cv2.FONT_HERSHEY_SIMPLEX
      cv2.putText(img, str(frameNumber), (int(0), int(lengthY+25)), font, 1, (0,255,0))

    return img

  wellShape = None if config.get("noWellDetection", False) or (hyperparameters["headEmbeded"] and not hyperparameters["oneWellManuallyChosenTopLeft"]) else 'rectangle' if config.get("wellsAreRectangles", False) or len(config.get("oneWellManuallyChosenTopLeft", '')) or int(config.get("multipleROIsDefinedDuringExecution", 0)) or config.get("groupOfMultipleSameSizeAndShapeEquallySpacedWells", False) else 'circle'
  return getFrame, frameRange, l, infoFrame is not None, supstruct['wellPositions'], wellShape


def readValidationVideo(videoPath, folderName, numWell, numAnimal, zoom, start, framesToShow=0, ZZoutputLocation='', supstruct=None, config=None):
  frameInfo = getFramesCallback(videoPath, folderName, numWell, numAnimal, zoom, start, framesToShow=framesToShow, ZZoutputLocation=ZZoutputLocation, supstruct=supstruct, config=config)
  if frameInfo is None:
    return
  getFrame, frameRange, frame, toggleTrackingPoints, _, _ = frameInfo
  layout = QVBoxLayout()

  video = QLabel()
  layout.addWidget(video, stretch=1)

  frameSlider = QSlider(Qt.Orientation.Horizontal)
  frameSlider.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
  frameSlider.setPageStep(50)
  frameSlider.setRange(*frameRange)
  frameSlider.setValue(frame)
  frameSlider.valueChanged.connect(lambda: util.setPixmapFromCv(getFrame(frameSlider, timer, plotTrackingPointsCheckbox, stopTimer), video))
  layout.addWidget(frameSlider)
  shortcutsLabel = QLabel("Left Arrow, Right Arrow, Page Up, Page Down, Home and End keys can be used to navigate through the video.")
  shortcutsLabel.setWordWrap(True)
  layout.addWidget(shortcutsLabel)
  plotTrackingPointsCheckbox = None
  if toggleTrackingPoints:
    plotTrackingPointsCheckbox = QCheckBox("Display tracking points")
    plotTrackingPointsCheckbox.setChecked(True)
    plotTrackingPointsCheckbox.toggled.connect(lambda: timer.isActive() or util.setPixmapFromCv(getFrame(frameSlider, timer, plotTrackingPointsCheckbox, stopTimer), video))
    layout.addWidget(plotTrackingPointsCheckbox)

  stopTimer = True
  timer = QTimer()
  timer.setInterval(1)

  def nextFrame():
    nonlocal stopTimer
    stopTimer = False
    frameSlider.setValue(frameSlider.value() + 1)
    stopTimer = True
  timer.timeout.connect(nextFrame)

  startFrame = getFrame(frameSlider, timer, plotTrackingPointsCheckbox, stopTimer)
  timer.start()
  util.showDialog(layout, title="Video", labelInfo=(startFrame, video))
  timer.stop()
  del getFrame
