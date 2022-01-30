from zebrazoom.code.getHyperparameters import getHyperparametersSimple
import zebrazoom.videoFormatConversion.zzVideoReading as zzVideoReading
import json
import numpy as np
import sys
import os
import cv2
from pathlib import Path

from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QImage, QPixmap
from PyQt6.QtWidgets import QApplication, QLabel, QSlider, QVBoxLayout, QWidget


class VideoWindow(QWidget):
  def __init__(self, cap, l, max_l, x, y, lengthX, lengthY, frameToPosToPlot, numWell, zoom, HeadX, HeadY, supstruct):
    super().__init__()
    self.cap = cap
    self.xOriginal = x
    self.x = x
    self.yOriginal = y
    self.y = y
    self.lengthX = lengthX
    self.lengthY = lengthY
    self.frameToPosToPlot = frameToPosToPlot
    self.numWell = numWell
    self.zoom = zoom
    self.HeadX = HeadX
    self.HeadY = HeadY
    self.supstruct = supstruct

    layout = QVBoxLayout()

    self.video = QLabel(self)
    self.video.setMinimumSize(1, 1)
    layout.addWidget(self.video, alignment=Qt.AlignmentFlag.AlignCenter)

    self.frameSlider = QSlider(Qt.Orientation.Horizontal, self)
    self.frameSlider.setRange(0, max_l - 1)
    self.frameSlider.setValue(l)
    self.frameSlider.valueChanged.connect(self._refreshVideo)
    layout.addWidget(self.frameSlider)

    self.setLayout(layout)

    self.stopTimer = False
    self.timer = QTimer(self)
    self.timer.setInterval(1)
    self.timer.timeout.connect(lambda: setattr(self, "stopTimer", False) or self.frameSlider.setValue(self.frameSlider.value() + 1) or setattr(self, "stopTimer", True))
    self._refreshVideo()

    self.setWindowTitle("Video")
    self.setWindowModality(Qt.WindowModality.ApplicationModal)
    self.move(0, 0)
    layoutSize = layout.totalSizeHint()
    screenSize = QApplication.instance().primaryScreen().availableSize()
    if layoutSize.width() > screenSize.width() or layoutSize.height() > screenSize.height():
      layoutSize.scale(screenSize, Qt.AspectRatioMode.KeepAspectRatio)
    self.setFixedSize(layoutSize)

    self.show()
    self.timer.start()

  def _refreshVideo(self):
    l = self.frameSlider.value()
    if self.timer.isActive() and (l == self.frameSlider.maximum() or self.stopTimer):
      self.timer.stop()

    self.cap.set(1, l)
    ret, img = self.cap.read()

    if self.frameToPosToPlot is not None:
      if l in self.frameToPosToPlot:
        for pos in self.frameToPosToPlot[l]:
          cv2.circle(img, (pos[0], pos[1]), self.hyperparameters["trackingPointSizeDisplay"], (0, 255, 0), -1)

    if self.numWell != -1 and self.zoom:
      length = 250
      xmin = int(self.HeadX[l + self.supstruct["firstFrame"] - 1] - length/2)
      xmax = int(self.HeadX[l + self.supstruct["firstFrame"] - 1] + length/2)
      ymin = int(self.HeadY[l + self.supstruct["firstFrame"] - 1] - length/2)
      ymax = int(self.HeadY[l + self.supstruct["firstFrame"] - 1] + length/2)

      self.x = max(xmin + self.xOriginal, 0)
      self.y = max(ymin + self.yOriginal, 0)
      self.lengthX = xmax - xmin
      self.lengthY = ymax - ymin

      if self.y + self.lengthY >= len(img):
        self.lengthY = len(img) - self.y - 1
      if self.x + self.lengthX >= len(img[0]):
        self.lengthX = len(img[0]) - self.x - 1

    if (self.numWell != -1):
      img = img[self.y:self.y+self.lengthY, self.x:self.x+self.lengthX]

    if self.lengthX > 100 and self.lengthY > 100:
      font = cv2.FONT_HERSHEY_SIMPLEX
      cv2.putText(img,str(l + self.supstruct["firstFrame"] - 1),(int(self.lengthX-110), int(self.lengthY-30)),font,1,(0,255,0))
    else:
      blank_image = np.zeros((len(img)+30, len(img[0]), 3), np.uint8)
      blank_image[0:len(img), 0:len(img[0])] = img
      img = blank_image
      font = cv2.FONT_HERSHEY_SIMPLEX
      cv2.putText(img, str(l + self.supstruct["firstFrame"] - 1), (int(0), int(self.lengthY+25)), font, 1, (0,255,0))

    scaling = self.devicePixelRatio()
    if self.video.isVisible():
      size = self.video.size()
      img = cv2.resize(img, (int(size.width() * scaling), int(size.height() * scaling)))
    height, width, channels = img.shape
    bytesPerLine = channels * width
    pixmap = QPixmap.fromImage(QImage(img.data.tobytes(), width, height, bytesPerLine, QImage.Format.Format_RGB888))
    if self.video.isVisible():
      pixmap.setDevicePixelRatio(scaling)
    self.video.setPixmap(pixmap)


def readValidationVideo(videoPath, folderName, configFilePath, numWell, numAnimal, zoom, start, framesToShow=0, ZZoutputLocation=''):
  s1  = "ZZoutput"
  s2  = folderName
  s3b = "results_"
  s4  = folderName
  s5  = ".avi"
  s5b = ".txt"

  cur_dir_path = os.path.dirname(os.path.realpath(__file__))
  initialPath  = Path(cur_dir_path)
  initialPath  = initialPath.parent
  initialPath  = os.path.join(initialPath, s1)
  if len(ZZoutputLocation):
    initialPath = ZZoutputLocation

  with open(os.path.join(initialPath, os.path.join(s2, 'configUsed.json'))) as f:
    configTemp = json.load(f)
  hyperparameters = getHyperparametersSimple(configTemp)

  if hyperparameters["copyOriginalVideoToOutputFolderForValidation"] and os.path.exists(os.path.join(initialPath, os.path.join(s1, os.path.join(s2, 'originalVideoWithoutAnyTrackingDisplayed_pleaseUseTheGUIToVisualizeTrackingPoints.avi')))):
    # The "exist" check above is only to insure compatibility with videos tracked prior to this update
    videoPath = os.path.join(initialPath, os.path.join(s2, 'originalVideoWithoutAnyTrackingDisplayed_pleaseUseTheGUIToVisualizeTrackingPoints.avi'))
  else:
    videoPath = os.path.join(initialPath, os.path.join(s2, s4 + s5))

  resultsPath = os.path.join(initialPath, os.path.join(s2, s3b + s4 + s5b))

  if not(os.path.exists(videoPath)):
    mypath = os.path.join(initialPath, s2)
    onlyfiles = [f for f in os.listdir(mypath) if os.path.isfile(os.path.join(mypath, f))]
    resultFile = ''
    for fileName in onlyfiles:
      if '.avi' in fileName:
        resultFile = fileName
    videoPath = os.path.join(initialPath, os.path.join(s2, resultFile))

  if not(os.path.exists(resultsPath)):
    mypath = os.path.join(initialPath, s2)
    onlyfiles = [f for f in os.listdir(mypath) if os.path.isfile(os.path.join(mypath, f))]
    resultFile = ''
    for fileName in onlyfiles:
      if 'results_' in fileName:
        resultFile = fileName
    resultsPath = os.path.join(initialPath, os.path.join(s2, resultFile))

  cap = zzVideoReading.VideoCapture(videoPath)

  nx    = int(cap.get(3))
  ny    = int(cap.get(4))
  max_l = int(cap.get(7))

  with open(resultsPath) as f:
    supstruct = json.load(f)

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

  frameToPosToPlot = None
  if hyperparameters["copyOriginalVideoToOutputFolderForValidation"]:
    frameToPosToPlot = {}
    for frameNumber in range(l, max_l + 400):
      frameToPosToPlot[frameNumber] = []
    for numWell in range(0, len(supstruct["wellPoissMouv"])):
      for numAnimal in range(0, len(supstruct["wellPoissMouv"][numWell])):
        for numBout in range(0, len(supstruct["wellPoissMouv"][numWell][numAnimal])):
          boutStart = supstruct["wellPoissMouv"][numWell][numAnimal][numAnimal]["BoutStart"]
          for i in range(0, len(supstruct["wellPoissMouv"][numWell][numAnimal][numAnimal]["HeadX"])):
            if boutStart + i in frameToPosToPlot:
              if (type(framesToShow) != np.ndarray) or (framesToShow[boutStart + i][numWell]):
                xPos = int(supstruct["wellPositions"][numWell]["topLeftX"] + supstruct["wellPoissMouv"][numWell][numAnimal][numAnimal]["HeadX"][i])
                yPos = int(supstruct["wellPositions"][numWell]["topLeftY"] + supstruct["wellPoissMouv"][numWell][numAnimal][numAnimal]["HeadY"][i])
                frameToPosToPlot[boutStart + i].append([xPos, yPos])

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

  app = QApplication.instance()
  app.registerWindow(VideoWindow(cap, l, max_l, x, y, lengthX, lengthY, frameToPosToPlot, numWell, zoom, HeadX, HeadY, supstruct))
