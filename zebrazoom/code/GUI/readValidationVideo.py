import contextlib
import collections
import math
import os
import random
import sys

import av
import cv2
import json
import numpy as np

from PyQt5.QtCore import pyqtSignal, Qt, QSize, QTimer
from PyQt5.QtGui import QColor, QFont, QFontMetrics, QPainter
from PyQt5.QtWidgets import QApplication, QButtonGroup, QCheckBox, QFileDialog, QGridLayout, QHBoxLayout, QMessageBox, QLabel, QProgressDialog, QPushButton, QRadioButton, QSizePolicy, QSlider, QSpinBox, QStyleOptionSlider, QVBoxLayout

import zebrazoom.code.paths as paths
import zebrazoom.code.util as util
import zebrazoom.videoFormatConversion.zzVideoReading as zzVideoReading
from zebrazoom.code.createValidationVideo import calculateInfoFrameForFrame, drawInfoFrame, improveContrast
from zebrazoom.code.getHyperparameters import getHyperparametersSimple
from zebrazoom.code.preprocessImage import preprocessImage
from zebrazoom.code.GUI.adjustParameterInsideAlgo import adjustFastFishTrackingPage


class _CustomTimer(QTimer):
  started = pyqtSignal()
  stopped = pyqtSignal()

  def start(self):
    super().start()
    self.started.emit()

  def stop(self):
    super().stop()
    self.stopped.emit()


class FrameSlider(QSlider):
  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    self.firstSaveFrame = None

  def paintEvent(self, event):
    if self.firstSaveFrame is not None:
      style = self.style()
      opt = QStyleOptionSlider()
      self.initStyleOption(opt)
      available = style.pixelMetric(style.PM_SliderSpaceAvailable, opt, self)
      minimum = self.minimum()
      maximum = self.maximum()
      qp = QPainter(self)
      qp.translate(opt.rect.x(), opt.rect.y())
      start = style.sliderPositionFromValue(minimum, maximum, self.firstSaveFrame, available, opt.upsideDown)
      end = style.sliderPositionFromValue(minimum, maximum, self.value(), available, opt.upsideDown)
      qp.fillRect(start, 0, end - start + 1, event.rect().height(), QColor('red'))
    super().paintEvent(event)


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

  cap = zzVideoReading.VideoCapture(videoPath, hyperparameters)

  nx    = int(cap.get(3))
  ny    = int(cap.get(4))
  max_l = int(cap.get(7)) if int(cap.get(7)) != -1 else hyperparameters["lastFrame"] # The "if" is to deal with eventBased data reading
  if max_l == 1:
    return None

  if not("firstFrame" in supstruct):
    supstruct["firstFrame"] = 1
    print("supstruct['firstFrame'] not found")

  if "lastFrame" not in supstruct:
    supstruct["lastFrame"] = max_l - 1
    print("supstruct['lastFrame'] not found")

  frameRange = (supstruct["firstFrame"], supstruct["lastFrame"] - 1)

  infoWells = []

  HeadX = np.zeros(max_l)
  HeadY = np.zeros(max_l)

  if ((numWell != -1) and (zoom)):
    lastEnd = 0
    lastXpos = supstruct["wellPoissMouv"][numWell][numAnimal][0]["HeadX"][0]
    lastYpos = supstruct["wellPoissMouv"][numWell][numAnimal][0]["HeadY"][0]
    for bout in supstruct["wellPoissMouv"][numWell][numAnimal]:
      beg = bout["BoutStart"]
      end = bout["BoutEnd"]
      if not (hyperparameters["copyOriginalVideoToOutputFolderForValidation"] or "pathToOriginalVideo" in supstruct):
        beg -= supstruct["firstFrame"]
        end -= supstruct["firstFrame"]
      HeadX[lastEnd:beg] = lastXpos
      HeadX[beg:end+1] = bout['HeadX'][:None if end + 1 <= max_l else max_l - beg]
      HeadY[lastEnd:beg] = lastYpos
      HeadY[beg:end+1] = bout['HeadY'][:None if end + 1 <= max_l else max_l - beg]
      lastEnd = end + 1
      lastXpos = bout["HeadX"][end-1-beg]
      lastYpos = bout["HeadY"][end-1-beg]

    HeadX[lastEnd:] = lastXpos
    HeadY[lastEnd:] = lastYpos

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

  boutMap = None
  if hyperparameters["copyOriginalVideoToOutputFolderForValidation"] or "pathToOriginalVideo" in supstruct:
    boutMap = collections.defaultdict(list)
    for wellIdx, well in enumerate(supstruct["wellPoissMouv"]):
      for animalIdx, animal in enumerate(well):
        for boutIdx, bout in enumerate(animal):
          for frame in range(bout['BoutStart'], bout['BoutEnd'] + 1):
            boutMap[frame].append((wellIdx, animalIdx, boutIdx))
    colorModifTab = [{"red": random.randrange(255), "green": random.randrange(255), "blue": random.randrange(255)} for i in range(1, hyperparameters["nbAnimalsPerWell"])]
    colorModifTab.insert(0, {"red": 0, "green": 0, "blue": 0})

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

  xOriginal = x
  yOriginal = y

  def getFrame(frameSlider, timer=None, trackingPointsGroup=None, stopTimer=True, returnHeadPos=False, returnOffsets=False, frameIdx=None, returnFPS=False, topLeftCircleCb=None):
    nonlocal x
    nonlocal y
    nonlocal lengthX
    nonlocal lengthY

    l = frameSlider.value() if frameIdx is None else frameIdx
    if timer is not None and timer.isActive() and (l == frameSlider.maximum() or stopTimer):
      timer.stop()

    if not (hyperparameters["copyOriginalVideoToOutputFolderForValidation"] or "pathToOriginalVideo" in supstruct):
      l -= supstruct['firstFrame']

    cap.set(1, l)
    ret, img = cap.read()
    if type(img[0][0]) != np.ndarray:
      img = cv2.cvtColor(img, cv2.COLOR_GRAY2RGB)

    if hyperparameters["imagePreProcessMethod"]:
      img = preprocessImage(img, hyperparameters)
    if hyperparameters["outputValidationVideoContrastImprovement"]:
      img = improveContrast(img, hyperparameters)

    if boutMap is not None and l in boutMap and trackingPointsGroup is not None and trackingPointsGroup.checkedId():
      hyperparameters["plotOnlyOneTailPointForVisu"] = trackingPointsGroup.checkedId() == 1
      infoFrame = [info for args in boutMap[l] for info in calculateInfoFrameForFrame(supstruct, hyperparameters, *args, l, colorModifTab)]
      drawInfoFrame(img, infoFrame, colorModifTab, hyperparameters)

    if numWell != -1 and zoom:
      length = 250
      xmin = int(HeadX[l] - length/2)
      xmax = int(HeadX[l] + length/2)
      ymin = int(HeadY[l] - length/2)
      ymax = int(HeadY[l] + length/2)

      x = max(xmin + xOriginal, 0)
      y = max(ymin + yOriginal, 0)
      if returnHeadPos:
        return HeadX[l] - x + xOriginal, HeadY[l] - y + yOriginal
      if returnOffsets:
        return x - xOriginal, y - yOriginal
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

    if trackingPointsGroup is not None and not trackingPointsGroup.checkedId() and topLeftCircleCb is not None and topLeftCircleCb():
      cv2.circle(img, (20, 20), 20, (0, 0, 255), -1)

    return (img, int(cap.get(5) if not hyperparameters['outputValidationVideoFps'] > 0 else hyperparameters['outputValidationVideoFps'])) if returnFPS else img

  wellShape = None if config.get("noWellDetection", False) or (hyperparameters["headEmbeded"] and not hyperparameters["oneWellManuallyChosenTopLeft"]) else 'rectangle' if config.get("wellsAreRectangles", False) or len(config.get("oneWellManuallyChosenTopLeft", '')) or int(config.get("multipleROIsDefinedDuringExecution", 0)) or config.get("groupOfMultipleSameSizeAndShapeEquallySpacedWells", False) else 'circle'
  return getFrame, frameRange, start if start > 0 else 0, boutMap is not None, supstruct['wellPositions'], wellShape, hyperparameters, videoPath if hyperparameters["copyOriginalVideoToOutputFolderForValidation"] or "pathToOriginalVideo" in supstruct else None


class _ElidedLabel(QLabel):
  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    self._value = None
    self._fm = QFontMetrics(QFont())

  def setValue(self, value, formatCb):
    self._value = value
    self.setText('' if value is None else self._fm.elidedText(formatCb(value), Qt.TextElideMode.ElideRight, self.size().width()))

  def getValue(self):
    return self._value


def readValidationVideo(videoPath, folderName, numWell, numAnimal, zoom, start, framesToShow=0, ZZoutputLocation='', supstruct=None, config=None):
  frameInfo = getFramesCallback(videoPath, folderName, numWell, numAnimal, zoom, start, framesToShow=framesToShow, ZZoutputLocation=ZZoutputLocation, supstruct=supstruct, config=config)
  if frameInfo is None:
    return
  getFrame, frameRange, frame, toggleTrackingPoints, wellPositions, wellShape, hyperparameters, originalVideoPath = frameInfo
  if wellShape is None:
    wellShape = 'rectangle'
  layout = QVBoxLayout()

  video = QLabel()
  if zoom:
    video.setAlignment(Qt.AlignmentFlag.AlignCenter)
    video.minimumSizeHint = lambda: QSize(250, 250)
  sizePolicy = QSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
  sizePolicy.setRetainSizeWhenHidden(True)
  video.setSizePolicy(sizePolicy)
  topLeftCircleCb = None
  if zoom and folderName.endswith('.h5'):
    videoLayout = QHBoxLayout()
    videoLayout.addWidget(video, stretch=1)
    layout.addLayout(videoLayout, stretch=1)
    validationLayout = QGridLayout()
    validationLayout.setColumnStretch(2, 1)
    validationLayout.setRowStretch(5, 1)
    bendCheckbox = QCheckBox('Bend')
    bendCheckbox.toggled.connect(lambda checked: saveChanges() or clearButton.setEnabled(True) or util.setPixmapFromCv(getFrame(frameSlider, timer, btnGroup, stopTimer, topLeftCircleCb=topLeftCircleCb), video))
    validationLayout.addWidget(bendCheckbox, 1, 0, 1, 2)
    headingButton = QPushButton('Heading:')

    def updateHeading():
      from zebrazoom.code.extractParameters import calculateAngle
      exitSignals = [frameSlider.valueChanged, manualValidationWidget.expanded, headingButton.clicked, tailExtremityButton.clicked]
      if toggleTrackingPoints:
        exitSignals.extend([btnGroup.idToggled, sizeSpinbox.valueChanged, contrastCheckbox.toggled])
      points = util.getPointOnFrame(getFrame(frameSlider, timer, btnGroup, stopTimer), video, basePoint=getFrame(frameSlider, returnHeadPos=True), exitSignals=exitSignals)
      if points is None:
        return
      headingLabel.setValue(calculateAngle(*points), str)
      saveChanges()
      clearButton.setEnabled(True)

    headingButton.clicked.connect(lambda: QTimer.singleShot(0, updateHeading))
    validationLayout.addWidget(headingButton, 2, 0)
    headingLabel = _ElidedLabel()
    validationLayout.addWidget(headingLabel, 2, 1, 1, 2)
    tailExtremityButton = QPushButton('Tail extremity:')

    def updateTailExtremity():
      exitSignals = [frameSlider.valueChanged, manualValidationWidget.expanded, headingButton.clicked, tailExtremityButton.clicked]
      if toggleTrackingPoints:
        exitSignals.extend([btnGroup.idToggled, sizeSpinbox.valueChanged, contrastCheckbox.toggled])
      point = util.getPointOnFrame(getFrame(frameSlider, timer, btnGroup, stopTimer), video, exitSignals=exitSignals)
      if point is None:
        return
      tailExtremityLabel.setValue(tuple(map(sum, zip(point, getFrame(frameSlider, returnOffsets=True)))), lambda point: ', '.join(map(str, point)))
      saveChanges()
      clearButton.setEnabled(True)

    tailExtremityButton.clicked.connect(lambda: QTimer.singleShot(0, updateTailExtremity))
    validationLayout.addWidget(tailExtremityButton, 3, 0)
    tailExtremityLabel = _ElidedLabel()
    validationLayout.addWidget(tailExtremityLabel, 3, 1, 1, 2)
    clearButton = QPushButton('Clear values')
    clearButton.setEnabled(False)
    clearButton.clicked.connect(lambda: updateWidgets(False, np.nan, (-1, -1)) or saveChanges() or clearButton.setEnabled(False) or util.setPixmapFromCv(getFrame(frameSlider, timer, btnGroup, stopTimer, topLeftCircleCb=topLeftCircleCb), video))
    validationLayout.addWidget(clearButton, 4, 0, 1, 3, alignment=Qt.AlignmentFlag.AlignCenter)

    def saveChanges():
      import h5py
      filePath = os.path.join(ZZoutputLocation if ZZoutputLocation else paths.getDefaultZZoutputFolder(), folderName)
      with h5py.File(filePath, 'r+') as results:
        firstFrame = results.attrs['firstFrame']
        arraySize = results.attrs['lastFrame'] - firstFrame + 1
        perFrameGroup = results[f'dataForWell{numWell}'][f'dataForAnimal{numAnimal}']['dataPerFrame']
        if 'manualBend' not in perFrameGroup:
          perFrameGroup.create_dataset('manualBend', data=np.full(arraySize, False, dtype=bool))
        if 'manualHeading' not in perFrameGroup:
          perFrameGroup.create_dataset('manualHeading', data=np.full(arraySize, np.nan))
        if 'manualTailExtremity' not in perFrameGroup:
          perFrameGroup.create_dataset('manualTailExtremity', data=np.full(arraySize, -1, dtype=[('X', int), ('Y', int)]))  # float array is required in order to support nan
          perFrameGroup['manualTailExtremity'].attrs['columns'] = ('X', 'Y')
        idx = frameSlider.value() - firstFrame
        bend = bendCheckbox.isChecked()
        perFrameGroup['manualBend'][idx] = bend if bend != -1 else np.nan
        heading = headingLabel.getValue()
        perFrameGroup['manualHeading'][idx] = heading if heading is not None else np.nan
        tailExtremity = tailExtremityLabel.getValue()
        perFrameGroup['manualTailExtremity'][idx] = tailExtremity if tailExtremity is not None else (-1, -1)

    manualValidationWidget = util.Expander(None, 'Manual validation', validationLayout, retainWidth=True)

    def updateWidgets(bend, heading, tailExtremity):
      blocked = bendCheckbox.blockSignals(True)
      bendCheckbox.setChecked(bend)
      bendCheckbox.blockSignals(blocked)
      headingLabel.setValue(heading if not np.isnan(heading) else None, str)
      tailExtremityLabel.setValue(tailExtremity if tailExtremity != (-1, -1) else None, lambda tailExtremity: ', '.join(map(str, tailExtremity)))

    def manualValidationExpanded(expanded):
      timer.stop()
      if not expanded:
        util.setPixmapFromCv(getFrame(frameSlider, timer, btnGroup, stopTimer, topLeftCircleCb=topLeftCircleCb), video)
        return
      import h5py
      filePath = os.path.join(ZZoutputLocation if ZZoutputLocation else paths.getDefaultZZoutputFolder(), folderName)
      with h5py.File(filePath, 'r+') as results:
        idx = frameSlider.value() - results.attrs['firstFrame']
        perFrameGroup = results[f'dataForWell{numWell}'][f'dataForAnimal{numAnimal}']['dataPerFrame']
        bend = perFrameGroup['manualBend'][idx] if 'manualBend' in perFrameGroup else False
        heading = perFrameGroup['manualHeading'][idx] if 'manualHeading' in perFrameGroup else np.nan
        tailExtremity = tuple(perFrameGroup['manualTailExtremity'][idx]) if 'manualTailExtremity' in perFrameGroup else (-1, -1)
      updateWidgets(bend, heading, tailExtremity)
      clearButton.setEnabled(bool(tailExtremityLabel.text() or headingLabel.text() or bendCheckbox.isChecked()))
      util.setPixmapFromCv(getFrame(frameSlider, timer, btnGroup, stopTimer, topLeftCircleCb=topLeftCircleCb), video)

    manualValidationWidget.expanded.connect(manualValidationExpanded)
    videoLayout.addWidget(manualValidationWidget, alignment=Qt.AlignmentFlag.AlignTop)
    topLeftCircleCb = lambda: manualValidationWidget.isExpanded() and bendCheckbox.isChecked()
  else:
    layout.addWidget(video, stretch=1)

  sliderLayout = QHBoxLayout()
  frameSlider = FrameSlider(Qt.Orientation.Horizontal)
  frameSlider.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
  frameSlider.setPageStep(50)
  frameSlider.setRange(*frameRange)
  frameSlider.setValue(frame)

  def updateManualValidationWidgets(value):
    blocked = frameSpinbox.blockSignals(True)
    frameSpinbox.setValue(frameSlider.value())
    frameSpinbox.blockSignals(blocked)
    if zoom and folderName.endswith('.h5'):
      if not manualValidationWidget.isExpanded():
        return
      manualValidationExpanded(True)
  frameSlider.valueChanged.connect(updateManualValidationWidgets)

  frameSlider.valueChanged.connect(lambda: util.setPixmapFromCv(getFrame(frameSlider, timer, btnGroup, stopTimer, topLeftCircleCb=topLeftCircleCb), video))
  sliderLayout.addWidget(frameSlider)

  frameSpinbox = QSpinBox()
  frameSpinbox.setRange(*frameRange)
  frameSpinbox.setStyleSheet(util.SPINBOX_STYLESHEET)
  frameSpinbox.setMinimumWidth(70)
  frameSpinbox.valueChanged.connect(lambda value: timer.stop() or frameSlider.setValue(value))
  sliderLayout.addWidget(frameSpinbox)

  playBtn = QPushButton()
  style = playBtn.style()
  playIcon = style.standardIcon(style.SP_MediaPlay)
  pauseIcon = style.standardIcon(style.SP_MediaPause)
  playBtn.setIcon(playIcon)
  playBtn.clicked.connect(lambda: timer.stop() if timer.isActive() else timer.start())
  sliderLayout.addWidget(playBtn)

  layout.addLayout(sliderLayout)
  shortcutsLabel = QLabel("Left Arrow, Right Arrow, Page Up, Page Down, Home and End keys can be used to navigate through the video.")
  shortcutsLabel.setWordWrap(True)
  layout.addWidget(shortcutsLabel)
  btnGroup = None
  trackingPointsLayout = QHBoxLayout()
  if toggleTrackingPoints:
    plotTrackingPointsLabel = QLabel("Tracking points:")
    trackingPointsLayout.addWidget(plotTrackingPointsLabel)
    btnGroup = QButtonGroup()
    allPointsRadioButton = QRadioButton('All')
    allPointsRadioButton.setChecked(True)
    trackingPointsLayout.addWidget(allPointsRadioButton)
    btnGroup.addButton(allPointsRadioButton, id=2)
    minimalPointsRadioButton = QRadioButton('Minimal')
    minimalPointsRadioButton.setChecked(bool(hyperparameters['plotOnlyOneTailPointForVisu']))
    trackingPointsLayout.addWidget(minimalPointsRadioButton)
    btnGroup.addButton(minimalPointsRadioButton, id=1)
    noPointsRadioButton = QRadioButton('None')
    trackingPointsLayout.addWidget(noPointsRadioButton)
    btnGroup.addButton(noPointsRadioButton, id=0)
    btnGroup.idToggled.connect(lambda: timer.isActive() or util.setPixmapFromCv(getFrame(frameSlider, timer, btnGroup, stopTimer, topLeftCircleCb=topLeftCircleCb), video))
    trackingPointsLayout.addWidget(QLabel('Size:'))
    sizeSpinbox = QSpinBox()
    sizeSpinbox.setMinimum(1)
    sizeSpinbox.setValue(hyperparameters["trackingPointSizeDisplay"])
    sizeSpinbox.valueChanged.connect(lambda value: hyperparameters.update({"trackingPointSizeDisplay": value}))
    sizeSpinbox.valueChanged.connect(lambda: timer.isActive() or util.setPixmapFromCv(getFrame(frameSlider, timer, btnGroup, stopTimer, topLeftCircleCb=topLeftCircleCb), video))
    trackingPointsLayout.addWidget(sizeSpinbox)
    contrastCheckbox = QCheckBox('Contrast')
    contrastCheckbox.setChecked(bool(hyperparameters['outputValidationVideoContrastImprovement']))
    contrastCheckbox.toggled.connect(lambda checked: hyperparameters.update({"outputValidationVideoContrastImprovement": int(checked)}))
    contrastCheckbox.toggled.connect(lambda: timer.isActive() or util.setPixmapFromCv(getFrame(frameSlider, timer, btnGroup, stopTimer, topLeftCircleCb=topLeftCircleCb), video))
    trackingPointsLayout.addWidget(contrastCheckbox)
    saveButton = QPushButton('Start save')

    def saveVideo():
      if frameSlider.firstSaveFrame is None:
        frameSlider.firstSaveFrame = frameSlider.value()
        timer.stop()
        saveButton.setText('End save')
        return

      app = QApplication.instance()
      question = QMessageBox(QMessageBox.Icon.Question, "Choose video compression", "What kind of compression would you like to use for the video?\n\nUsing advanced compression will produce significantly smaller files, but might lead to some loss of quality.", parent=app.window, buttons=QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel)
      question.button(QMessageBox.StandardButton.Yes).setText('Default')
      question.button(QMessageBox.StandardButton.No).setText('Advanced')
      response = question.exec()
      newFormat = False if response == QMessageBox.StandardButton.Yes else True if response == QMessageBox.StandardButton.No else None
      if newFormat is None:
        return

      filename, _ = QFileDialog.getSaveFileName(app.window, 'Select file', os.path.expanduser('~'), "Matroska (*.mkv)")
      if not filename:
        return

      lastSaveFrame = frameSlider.value()
      if lastSaveFrame < frameSlider.firstSaveFrame:
        frameSlider.firstSaveFrame, lastSaveFrame = lastSaveFrame, frameSlider.firstSaveFrame
      progressDialog = QProgressDialog("Saving video...", "Cancel", frameSlider.firstSaveFrame, lastSaveFrame, app.window, Qt.WindowType.WindowTitleHint | Qt.WindowType.WindowCloseButtonHint)
      progressDialog.setWindowTitle('Saving Video')
      progressDialog.setAutoClose(False)
      progressDialog.setAutoReset(False)
      progressDialog.setWindowModality(Qt.WindowModality.ApplicationModal)
      progressDialog.setMinimumDuration(0)
      frame, videoFPS = getFrame(frameSlider, trackingPointsGroup=btnGroup, frameIdx=frameSlider.firstSaveFrame, returnFPS=True)
      height, width = frame.shape[:2] if not zoom else (250, 250)
      height += height % 2  # x265 requires width and height to be even numbers, so we might need to add one pixel
      width += width % 2

      @contextlib.contextmanager
      def cv2CM():
        cap = cv2.VideoWriter(filename, cv2.VideoWriter_fourcc(*'MJPG'), videoFPS, (width, height))
        yield cap
        cap.release()

      with av.open(filename, 'w') if newFormat else cv2CM() as output:
        if hasattr(output, 'mux'):
          outstream = output.add_stream('libx265', rate=videoFPS)
          outstream.width = width
          outstream.height = height
          outstream.options = {'crf': '20'}

        for frameIdx in range(frameSlider.firstSaveFrame, lastSaveFrame + 1):
          progressDialog.setValue(frameIdx)
          progressDialog.setLabelText(f'Saving frame {frameIdx}...')
          frame = getFrame(frameSlider, trackingPointsGroup=btnGroup, frameIdx=frameIdx)
          frameHeight, frameWidth = frame.shape[:2]
          if frameHeight < height or frameWidth < width:
            xOffset = (width - frameWidth) // 2
            yOffset = (height - frameHeight) // 2
            copy = cv2.resize(frame, (width, height))
            copy[:] = 0
            copy[yOffset:yOffset+frameHeight, xOffset:xOffset+frameWidth] = frame
            frame = copy
          if newFormat:
            output.mux(outstream.encode(av.VideoFrame.from_ndarray(frame, format='bgr24')))
          else:
            output.write(frame)
          if progressDialog.wasCanceled():
            break
        progressDialog.setLabelText('Saving video...')
        if newFormat:
          output.mux(outstream.encode(None))

      progressDialog.close()
      saveButton.setText('Start save')
      frameSlider.firstSaveFrame = None

    saveButton.clicked.connect(saveVideo)
    trackingPointsLayout.addWidget(saveButton)

  adjustButton = None
  if config is not None and (numWell != -1 or config.get("headEmbeded", False)) and ('trackingImplementation' not in config or config['trackingImplementation'] == 'fastFishTracking.tracking') and not config.get("trackingMethod"):
    adjustButton = QPushButton('Adjust parameters')
    def adjustParametrsClicked():
      app = QApplication.instance()
      app.configFile = {key: val for key, val in config.items() if key != 'popUpAlgoFollow'}
      app.savedConfigFile = app.configFile.copy()
      if originalVideoPath is None:
        app.videoToCreateConfigFileFor, _ = QFileDialog.getOpenFileName(app.window, "Select video to create config file for", os.path.expanduser("~"),
                                                                        filter=f'Videos ({" ".join("*%s" % ext for ext in util.VIDEO_EXTENSIONS)});; All files (*.*)')
      else:
        app.videoToCreateConfigFileFor = originalVideoPath.replace('\\', '/')
      if not app.videoToCreateConfigFileFor:
        app.configFile.clear()
        return
      util.addToHistory(app.optimizeConfigFile)()
      if app.configFile.get("trackingImplementation") == "fastFishTracking.tracking":
        util.addToHistory(adjustFastFishTrackingPage)(useNext=False, wellPositions=wellPositions, wellShape=wellShape, wellIdx=numWell, frameIdx=frameSlider.value())
      else:
        trackingMethod = app.configFile.get("trackingMethod")
        if not trackingMethod:
          if app.configFile.get("headEmbeded", False):
            util.addToHistory(app.calculateBackground)(app, 0, useNext=False, wellPositions=wellPositions, wellShape=wellShape, frameIdx=frameSlider.value())
          else:
            util.addToHistory(app.calculateBackgroundFreelySwim)(app, 0, automaticParameters=True, useNext=False, wellPositions=wellPositions, wellShape=wellShape, wellIdx=numWell, frameIdx=frameSlider.value())
    QTimer.singleShot(0, lambda: adjustButton.clicked.connect(adjustParametrsClicked))
    trackingPointsLayout.addWidget(adjustButton)

  trackingPointsLayout.addStretch(1)
  layout.addLayout(trackingPointsLayout)

  stopTimer = True
  timer = _CustomTimer()
  timer.started.connect(lambda: playBtn.setIcon(pauseIcon))
  timer.stopped.connect(lambda: playBtn.setIcon(playIcon))
  timer.setInterval(1)

  def nextFrame():
    nonlocal stopTimer
    stopTimer = False
    frameSlider.setValue(frameSlider.value() + 1)
    stopTimer = True
  timer.timeout.connect(nextFrame)

  startFrame = getFrame(frameSlider, timer, btnGroup, stopTimer, topLeftCircleCb=topLeftCircleCb)
  timer.start()
  focusWidgets = {frameSlider}
  focusWidgets.add(frameSpinbox)
  QTimer.singleShot(0, lambda: frameSlider.setFocus())
  util.showDialog(layout, title="Video", labelInfo=(startFrame, video), focusWidgets=focusWidgets, exitSignals=(adjustButton.clicked,) if adjustButton is not None else ())
  timer.stop()
  del getFrame
