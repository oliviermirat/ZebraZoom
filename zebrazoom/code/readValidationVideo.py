import math
import os
import sys

import cv2
import json
import numpy as np

from PyQt5.QtCore import Qt, QSize, QTimer
from PyQt5.QtWidgets import QApplication, QFileDialog, QMessageBox, QLabel, QSlider, QVBoxLayout

import zebrazoom.code.paths as paths
import zebrazoom.code.util as util
import zebrazoom.videoFormatConversion.zzVideoReading as zzVideoReading
from zebrazoom.code.createValidationVideo import calculateInfoFrame, drawInfoFrame
from zebrazoom.code.getHyperparameters import getHyperparametersSimple
from zebrazoom.code.preprocessImage import preprocessImage


def readValidationVideo(videoPath, folderName, configFilePath, numWell, numAnimal, zoom, start, framesToShow=0, ZZoutputLocation=''):
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

  with open(os.path.join(initialPath, os.path.join(s2, 'configUsed.json'))) as f:
    configTemp = json.load(f)
  hyperparameters = getHyperparametersSimple(configTemp)
  
  resultsPath = os.path.join(initialPath, os.path.join(s2, s3b + s4 + s5b))

  if not(os.path.exists(resultsPath)):
    mypath = os.path.join(initialPath, s2)
    onlyfiles = [f for f in os.listdir(mypath) if os.path.isfile(os.path.join(mypath, f))]
    resultFile = ''
    for fileName in onlyfiles:
      if 'results_' in fileName:
        resultFile = fileName
    resultsPath = os.path.join(initialPath, os.path.join(s2, resultFile))

  with open(resultsPath) as f:
    supstruct = json.load(f)
  
  if hyperparameters["savePathToOriginalVideoForValidationVideo"]:
    videoPath = supstruct["pathToOriginalVideo"]
    if not os.path.exists(videoPath):
      app = QApplication.instance()
      if QMessageBox.critical(app.window, "Video not found", "Cannot display the validation video because the video used to run the tracking can no longer be found. Would you like to update the video path stored in the results file?",
                              buttons=QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No, defaultButton=QMessageBox.StandardButton.Yes) != QMessageBox.StandardButton.Yes:
        return
      videoName, _ = QFileDialog.getOpenFileName(app.window, 'Select video', os.path.expanduser("~"))
      videoPath = supstruct["pathToOriginalVideo"] = videoName
      with open(resultsPath, 'w') as f:
        json.dump(supstruct, f)
  else:
    if hyperparameters["copyOriginalVideoToOutputFolderForValidation"] and os.path.exists(os.path.join(initialPath, os.path.join(s1, os.path.join(s2, 'originalVideoWithoutAnyTrackingDisplayed_pleaseUseTheGUIToVisualizeTrackingPoints.avi')))):
      # The "exist" check above is only to insure compatibility with videos tracked prior to this update
      videoPath = os.path.join(initialPath, os.path.join(s2, 'originalVideoWithoutAnyTrackingDisplayed_pleaseUseTheGUIToVisualizeTrackingPoints.avi'))
    else:
      videoPath = os.path.join(initialPath, os.path.join(s2, s4 + s5))

  if not(os.path.exists(videoPath)):
    mypath = os.path.join(initialPath, s2)
    onlyfiles = [f for f in os.listdir(mypath) if os.path.isfile(os.path.join(mypath, f))]
    resultFile = ''
    for fileName in onlyfiles:
      if '.avi' in fileName:
        resultFile = fileName
    videoPath = os.path.join(initialPath, os.path.join(s2, resultFile))

  cap = zzVideoReading.VideoCapture(videoPath)

  nx    = int(cap.get(3))
  ny    = int(cap.get(4))
  max_l = int(cap.get(7))
  sliderRange = (supstruct["firstFrame"], supstruct["lastFrame"]) if hyperparameters["copyOriginalVideoToOutputFolderForValidation"] or hyperparameters["savePathToOriginalVideoForValidationVideo"] else (0, max_l -1)

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
  if hyperparameters["copyOriginalVideoToOutputFolderForValidation"] or hyperparameters["savePathToOriginalVideoForValidationVideo"]:
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
  if hyperparameters["copyOriginalVideoToOutputFolderForValidation"] or hyperparameters["savePathToOriginalVideoForValidationVideo"]:
    l += supstruct["firstFrame"]

  xOriginal = x
  yOriginal = y

  def getFrame():
    nonlocal x
    nonlocal y
    nonlocal lengthX
    nonlocal lengthY

    l = frameSlider.value()
    if timer.isActive() and (l == frameSlider.maximum() or stopTimer):
      timer.stop()

    cap.set(1, l)
    ret, img = cap.read()
    
    if hyperparameters["imagePreProcessMethod"]:
      img = preprocessImage(img, hyperparameters)
    
    if infoFrame is not None:
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

    frameNumber = l if hyperparameters["copyOriginalVideoToOutputFolderForValidation"] or hyperparameters["savePathToOriginalVideoForValidationVideo"] else (l + supstruct["firstFrame"])
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

  layout = QVBoxLayout()

  video = QLabel()
  layout.addWidget(video, stretch=1)

  frameSlider = QSlider(Qt.Orientation.Horizontal)
  frameSlider.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
  frameSlider.setPageStep(50)
  frameSlider.setRange(*sliderRange)
  frameSlider.setValue(l)
  frameSlider.valueChanged.connect(lambda: util.setPixmapFromCv(getFrame(), video))
  layout.addWidget(frameSlider)
  shortcutsLabel = QLabel("Left Arrow, Right Arrow, Page Up, Page Down, Home and End keys can be used to navigate through the video.")
  shortcutsLabel.setWordWrap(True)
  layout.addWidget(shortcutsLabel)

  stopTimer = True
  timer = QTimer()
  timer.setInterval(1)

  def nextFrame():
    nonlocal stopTimer
    stopTimer = False
    frameSlider.setValue(frameSlider.value() + 1)
    stopTimer = True
  timer.timeout.connect(nextFrame)

  startFrame = getFrame()
  timer.start()
  util.showDialog(layout, title="Video", labelInfo=(startFrame, video))
  timer.stop()
  cap.release()
