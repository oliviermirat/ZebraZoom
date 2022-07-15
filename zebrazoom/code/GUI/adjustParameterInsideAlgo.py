import os
import pickle

import cv2

import numpy as np

from PyQt5.QtCore import Qt, pyqtSignal, QPoint, QPointF, QRect, QRectF, QSizeF, QTimer
from PyQt5.QtGui import QColor, QFont, QIntValidator, QPainter, QPolygon, QPolygonF, QTransform
from PyQt5.QtWidgets import QApplication, QGridLayout, QLabel, QLineEdit, QCheckBox, QMessageBox, QPushButton, QHBoxLayout, QSlider, QSpinBox, QVBoxLayout, QWidget

import zebrazoom.videoFormatConversion.zzVideoReading as zzVideoReading
import zebrazoom.code.paths as paths
import zebrazoom.code.util as util
from zebrazoom.mainZZ import mainZZ
from zebrazoom.code.getHyperparameters import getHyperparametersSimple
from zebrazoom.code.getImage.headEmbededFrame import headEmbededFrame
from zebrazoom.code.getImage.headEmbededFrameBackExtract import headEmbededFrameBackExtract


class _WellSelectionLabel(QLabel):
  def __init__(self, width, height):
    super().__init__()
    self._width = width
    self._height = height
    self._well = 0
    self._hoveredWell = None
    if QApplication.instance().wellPositions:
      self.setMouseTracking(True)

  def mouseMoveEvent(self, evt):
    app = QApplication.instance()
    if not app.wellPositions:
      return
    oldHovered = self._hoveredWell
    if app.wellShape == 'rectangle':
      def test_func(point, x, y, width, height):
        return QRect(x, y, width, height).contains(point)
    else:
      assert app.wellShape == 'circle'
      def test_func(point, x, y, width, height):
        radius = width / 2;
        centerX = x + radius;
        centerY = y + radius;
        dx = abs(point.x() - centerX)
        if dx > radius:
          return False
        dy = abs(point.y() - centerY)
        if dy > radius:
          return False
        if dx + dy <= radius:
          return True
        return dx * dx + dy * dy <= radius * radius
    for idx, positions in enumerate(app.wellPositions):
      if test_func(self._transformToOriginal.map(evt.pos()), *positions):
        self._hoveredWell = idx
        break
    else:
      self._hoveredWell = None
    if self._hoveredWell != oldHovered:
      self.update()

  def mousePressEvent(self, evt):
    if not QApplication.instance().wellPositions:
      return
    if self._hoveredWell is not None:
      self._well = self._hoveredWell
      self.update()

  def enterEvent(self, evt):
    QApplication.setOverrideCursor(Qt.CursorShape.CrossCursor)

  def leaveEvent(self, evt):
    QApplication.restoreOverrideCursor()
    self._hoveredWell = None
    self.update()

  def paintEvent(self, evt):
    super().paintEvent(evt)
    app = QApplication.instance()
    if not app.wellPositions:
      return
    qp = QPainter()
    qp.begin(self)
    factory = qp.drawRect if app.wellShape == 'rectangle' else qp.drawEllipse
    font = QFont()
    font.setPointSize(16)
    font.setWeight(QFont.Weight.Bold)
    qp.setFont(font)
    for idx, positions in enumerate(app.wellPositions):
      if idx == self._well:
        qp.setPen(QColor(255, 0, 0))
      elif idx == self._hoveredWell:
        qp.setPen(QColor(0, 255, 0))
      else:
        qp.setPen(QColor(0, 0, 255))
      rect = self._transformFromOriginal.map(QPolygon(QRect(*positions))).boundingRect()
      qp.drawText(rect, Qt.AlignmentFlag.AlignCenter, str(idx))
      factory(rect)
    qp.end()

  def resizeEvent(self, evt):
    super().resizeEvent(evt)
    self._size = self.size()
    originalRect = QRectF(QPointF(0, 0), QSizeF(self._width, self._height))
    currentRect = QRectF(QPointF(0, 0), QSizeF(self._size))
    self._transformToOriginal = QTransform()
    QTransform.quadToQuad(QPolygonF((currentRect.topLeft(), currentRect.topRight(), currentRect.bottomLeft(), currentRect.bottomRight())),
                          QPolygonF((originalRect.topLeft(), originalRect.topRight(), originalRect.bottomLeft(), originalRect.bottomRight())),
                          self._transformToOriginal)
    self._transformFromOriginal = QTransform()
    QTransform.quadToQuad(QPolygonF((originalRect.topLeft(), originalRect.topRight(), originalRect.bottomLeft(), originalRect.bottomRight())),
                          QPolygonF((currentRect.topLeft(), currentRect.topRight(), currentRect.bottomLeft(), currentRect.bottomRight())),
                          self._transformFromOriginal)

  def getWell(self):
    return self._well


def _cleanup(app, page):
  app.window.centralWidget().layout().removeWidget(page)
  if hasattr(app, "wellPositions"):
    del app.wellPositions
  if hasattr(app, "wellShape"):
    del app.wellShape
  if hasattr(app, "background"):
    del app.background


def _showPage(layout, labelInfo):
  app = QApplication.instance()
  page = QWidget()
  page.setLayout(layout)
  stackedLayout = app.window.centralWidget().layout()
  stackedLayout.addWidget(page)
  oldWidget = stackedLayout.currentWidget()
  with app.suppressBusyCursor():
    stackedLayout.setCurrentWidget(page)
    if labelInfo is not None:
      img, label = labelInfo
      label.setMinimumSize(1, 1)
      label.show()
      util.setPixmapFromCv(img, label)
  return page


class _InteractiveCVLabelLine(QLabel):
  lineSelected = pyqtSignal(bool)
  proceed = pyqtSignal()

  def __init__(self, width, height, frame, thickness):
    super().__init__()
    self._width = width
    self._height = height
    self._startPoint = None
    self._endPoint = None
    self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
    self.setMouseTracking(True)
    self._thickness = thickness
    self._frame = frame

  def keyPressEvent(self, evt):
    if self._endPoint is not None and (evt.key() == Qt.Key.Key_Enter or evt.key() == Qt.Key.Key_Return):
      self.proceed.emit()
      return
    super().keyPressEvent(evt)

  def updateFrame(self, frame=None):
    if frame is not None:
      self._frame = frame
    else:
      (startPointX, startPointY), (endPointX, endPointY) = self.getPoints()
      cv2.line(self._frame, (startPointX, startPointY), (endPointX, endPointY), (255, 255, 255), self._thickness)
    util.setPixmapFromCv(self._frame, self)
    self._startPoint = None
    self._endPoint = None
    self.lineSelected.emit(False)

  def setThickness(self, thickness):
    self._thickness = thickness
    if self._endPoint is None:
      return
    startPoint = self._startPoint
    endPoint = self._endPoint
    if self._size.height() != self._height or self._size.width() != self._width:
      startPoint = util.transformCoordinates(QRectF(QPointF(0, 0), QSizeF(self._size)), QRectF(QPointF(0, 0), QSizeF(self._width, self._height)), startPoint)
      endPoint = util.transformCoordinates(QRectF(QPointF(0, 0), QSizeF(self._size)), QRectF(QPointF(0, 0), QSizeF(self._width, self._height)), endPoint)
    util.setPixmapFromCv(cv2.line(self._frame.copy(), (startPoint.x(), startPoint.y()), (endPoint.x(), endPoint.y()), (255, 255, 255), self._thickness), self)

  def mouseMoveEvent(self, evt):
    if self._endPoint is not None or self._startPoint is None:
      return
    startPoint = self._startPoint
    endPoint = evt.pos()
    if self._size.height() != self._height or self._size.width() != self._width:
      startPoint = util.transformCoordinates(QRectF(QPointF(0, 0), QSizeF(self._size)), QRectF(QPointF(0, 0), QSizeF(self._width, self._height)), startPoint)
      endPoint = util.transformCoordinates(QRectF(QPointF(0, 0), QSizeF(self._size)), QRectF(QPointF(0, 0), QSizeF(self._width, self._height)), endPoint)
    util.setPixmapFromCv(cv2.line(self._frame.copy(), (startPoint.x(), startPoint.y()), (endPoint.x(), endPoint.y()), (255, 255, 255), self._thickness), self)

  def mousePressEvent(self, evt):
    if self._endPoint is None and self._startPoint is not None:
      self._endPoint = evt.pos()
      self.lineSelected.emit(True)
    else:
      self._startPoint = evt.pos()
      self._endPoint = None
      self.lineSelected.emit(False)
      util.setPixmapFromCv(self._frame, self)

  def enterEvent(self, evt):
    QApplication.setOverrideCursor(Qt.CursorShape.CrossCursor)

  def leaveEvent(self, evt):
    QApplication.restoreOverrideCursor()
    if self._endPoint is None:
      util.setPixmapFromCv(self._frame, self)

  def resizeEvent(self, evt):
    super().resizeEvent(evt)
    self._size = self.size()

  def getPoints(self):
    if self._endPoint is None:
      return None
    startPoint = self._startPoint
    endPoint = self._endPoint
    if self._size.height() != self._height or self._size.width() != self._width:
      startPoint = util.transformCoordinates(QRectF(QPointF(0, 0), QSizeF(self._size)), QRectF(QPointF(0, 0), QSizeF(self._width, self._height)), self._startPoint)
      endPoint = util.transformCoordinates(QRectF(QPointF(0, 0), QSizeF(self._size)), QRectF(QPointF(0, 0), QSizeF(self._width, self._height)), self._endPoint)
    return (startPoint.x(), startPoint.y()), (endPoint.x(), endPoint.y())


def _addBlackSegments(config, videoPath, frameNumber, wellNumber, cap):
  app = QApplication.instance()
  wellPositions = [dict(zip(("topLeftX", "topLeftY", "lengthX", "lengthY"), app.wellPositions[wellNumber]))] if app.wellPositions else \
    [{"topLeftX":0, "topLeftY":0, "lengthX": int(cap.get(3)), "lengthY": int(cap.get(4))}]
  tmpConfig = config.copy()

  def getFrame():
    hyperparameters = getHyperparametersSimple(tmpConfig)
    if hyperparameters["headEmbededRemoveBack"] == 0 and hyperparameters["headEmbededAutoSet_BackgroundExtractionOption"] == 0:
      frame, thresh1 = headEmbededFrame(videoPath, frameNumber, wellNumber, wellPositions, hyperparameters)
    else:
      hyperparameters["headEmbededRemoveBack"] = 1
      hyperparameters["minPixelDiffForBackExtract"] = hyperparameters["headEmbededAutoSet_BackgroundExtractionOption"]
      frame, thresh1 = headEmbededFrameBackExtract(videoPath, QApplication.instance().background, hyperparameters, frameNumber, wellNumber, wellPositions)

    quartileChose = hyperparameters["outputValidationVideoContrastImprovementQuartile"]
    lowVal  = int(np.quantile(frame, quartileChose))
    highVal = int(np.quantile(frame, 1 - quartileChose))
    frame[frame < lowVal]  = lowVal
    frame[frame > highVal] = highVal
    frame -= lowVal
    return (frame * (255 / np.max(frame))).astype('uint8')

  frame = getFrame()

  imagePreProcessMethod = config.get("imagePreProcessMethod", None)
  imagePreProcessParameters = config.get("imagePreProcessParameters", None)
  if isinstance(imagePreProcessMethod, list) and isinstance(imagePreProcessParameters, list) and \
      len(imagePreProcessMethod) == len(imagePreProcessParameters):
    imagePreProcessMethod = imagePreProcessMethod[:]
    imagePreProcessParameters = imagePreProcessParameters[:]
  else:
    imagePreProcessMethod = []
    imagePreProcessParameters = []
  tmpConfig["imagePreProcessMethod"] = imagePreProcessMethod
  tmpConfig["imagePreProcessParameters"] = imagePreProcessParameters

  layout = QVBoxLayout()
  layout.addWidget(QLabel("Enter/Return keys can be used instead of clicking Add another segment."), alignment=Qt.AlignmentFlag.AlignCenter)
  height, width = frame.shape[:2]
  blackSegmentsLineWidth = QSpinBox()
  blackSegmentsLineWidth.setMinimum(1)
  blackSegmentsLineWidth.valueChanged.connect(lambda value: label.setThickness(value))
  blackSegmentsLineWidth.setValue(config.get("addBlackLineToImg_Width", 1))
  label = _InteractiveCVLabelLine(width, height, frame, blackSegmentsLineWidth.value())
  layout.addWidget(label, alignment=Qt.AlignmentFlag.AlignCenter, stretch=1)
  blackSegmentWidthLayout = QHBoxLayout()
  blackSegmentWidthLayout.addStretch(1)
  blackSegmentWidthLayout.addWidget(QLabel("Black segment line width:"))
  blackSegmentWidthLayout.addWidget(blackSegmentsLineWidth)
  blackSegmentWidthLayout.addStretch(1)
  layout.addLayout(blackSegmentWidthLayout)

  buttonsLayout = QHBoxLayout()
  buttonsLayout.addStretch(1)
  addSegmentBtn = QPushButton("Add another segment")
  addSegmentBtn.setEnabled(False)

  def storeSegment():
    (startPointX, startPointY), (endPointX, endPointY) = label.getPoints()
    imagePreProcessMethod.append("setImageLineToBlack")
    imagePreProcessParameters.append([startPointX, startPointY, endPointX, endPointY, blackSegmentsLineWidth.value()])
    label.updateFrame()
  addSegmentBtn.clicked.connect(storeSegment)
  label.proceed.connect(storeSegment)
  label.lineSelected.connect(lambda selected: addSegmentBtn.setEnabled(selected))
  buttonsLayout.addWidget(addSegmentBtn)
  removeAllSegmentsBtn = QPushButton("Remove all segments")

  def removeSegments():
    for idx in reversed(range(len(imagePreProcessMethod))):
      if imagePreProcessMethod[idx] != "setImageLineToBlack":
        continue
      del imagePreProcessMethod[idx]
      del imagePreProcessParameters[idx]
    label.updateFrame(getFrame())
  removeAllSegmentsBtn.clicked.connect(removeSegments)
  buttonsLayout.addWidget(removeAllSegmentsBtn)
  buttonsLayout.addStretch(1)
  layout.addLayout(buttonsLayout)

  def saveClicked():
    if label.getPoints() is not None:
      storeSegment()
    if not imagePreProcessMethod:
      if "imagePreProcessMethod" in config:
        del config["imagePreProcessMethod"]
    else:
      config["imagePreProcessMethod"] = imagePreProcessMethod
    if not imagePreProcessParameters:
      if "imagePreProcessParameters" in config:
        del config["imagePreProcessMethod"]
    else:
      config["imagePreProcessParameters"] = imagePreProcessParameters
  buttons = (("Done! Save changes!", saveClicked), ("Discard changes.", None))
  util.showBlockingPage(layout, labelInfo=(frame, label), title="Click in the beginning and end of segment to set to black pixels", buttons=buttons)


def _selectROI(config, getFrame):
  save = False
  def saveClicked():
    nonlocal save
    save = True
  buttons = (("Done! Save changes!", saveClicked, True), ("Discard changes.", None, True))
  topLeft = config.get("oneWellManuallyChosenTopLeft")
  bottomRight = config.get("oneWellManuallyChosenBottomRight")
  initialRect = None if topLeft is None or bottomRight is None else (QPoint(*topLeft), QPoint(*bottomRight))
  checkbox = QCheckBox('Improve contrast')
  improveContrast = bool(config.get("outputValidationVideoContrastImprovement", False))
  checkbox.setChecked(improveContrast)
  coords = util.getRectangle(getFrame(), "Click on the top left and bottom right of the region of interest", buttons=buttons,
                             initialRect=initialRect, allowEmpty=True, contrastCheckbox=checkbox, getFrame=getFrame)
  if save:
    app = QApplication.instance()
    if coords == ([0, 0], [0, 0]):
      if "oneWellManuallyChosenTopLeft" in config:
        del config["oneWellManuallyChosenTopLeft"]
      if "oneWellManuallyChosenBottomRight" in config:
        del config["oneWellManuallyChosenBottomRight"]
      del app.wellPositions[:]
    else:
      config["oneWellManuallyChosenTopLeft"], config["oneWellManuallyChosenBottomRight"] = coords
      topLeftX, topLeftY = config["oneWellManuallyChosenTopLeft"]
      bottomRightX, bottomRightY = config["oneWellManuallyChosenBottomRight"]
      app.wellPositions = [(topLeftX, topLeftY, bottomRightX - topLeftX, bottomRightY - topLeftY)]
      app.wellShape = 'rectangle'
    config["nbWells"] = 1


def _adjustEyeTracking(firstFrame, totalFrames, ellipse=False):
  app = QApplication.instance()

  pathToVideo = os.path.dirname(app.videoToCreateConfigFileFor)
  videoName, videoExt = os.path.basename(app.videoToCreateConfigFileFor).split('.')
  argv = []

  originalConfig = app.configFile.copy()
  app.configFile["adjustHeadEmbeddedEyeTracking"] = 1
  app.configFile["onlyTrackThisOneWell"] = 0
  app.configFile["reloadBackground"] = 1
  app.configFile["eyeTracking"] = 1
  if ellipse:
    app.configFile["eyeTrackingHeadEmbeddedWithEllipse"] = 1
    if "eyeTrackingHeadEmbeddedWithSegment" in app.configFile:
      del app.configFile["eyeTrackingHeadEmbeddedWithSegment"]
  else:
    app.configFile["eyeTrackingHeadEmbeddedWithSegment"] = 1
    if "eyeTrackingHeadEmbeddedWithEllipse" in app.configFile:
      del app.configFile["eyeTrackingHeadEmbeddedWithEllipse"]
  app.configFile["firstFrame"] = firstFrame
  app.configFile["lastFrame"] = min(firstFrame + 500, app.configFile.get("lastFrame", totalFrames - 1))

  saved = False
  try:
    if "lastFrame" in app.configFile and "firstFrame" in app.configFile and app.configFile["lastFrame"] < app.configFile["firstFrame"]:
      del app.configFile["lastFrame"]
    mainZZ(pathToVideo, videoName, videoExt, app.configFile, argv)
  except ValueError:
    saved = True
  except NameError:
    print("Configuration file parameters changes discarded.")

  app.configFile = originalConfig
  if saved:
    newhyperparameters = pickle.load(open(os.path.join(paths.getRootDataFolder(), 'newhyperparameters'), 'rb'))
    for index in newhyperparameters:
      app.configFile[index] = newhyperparameters[index]
    app.configFile["eyeTracking"] = 1
    if ellipse:
      app.configFile["eyeTrackingHeadEmbeddedWithEllipse"] = 1
      if "eyeTrackingHeadEmbeddedWithSegment" in app.configFile:
        del app.configFile["eyeTrackingHeadEmbeddedWithSegment"]
    else:
      app.configFile["eyeTrackingHeadEmbeddedWithSegment"] = 1
      if "eyeTrackingHeadEmbeddedWithEllipse" in app.configFile:
        del app.configFile["eyeTrackingHeadEmbeddedWithEllipse"]


def _addEyeTracking(firstFrame, totalFrames):
  app = QApplication.instance()
  layout = QVBoxLayout()

  originalInvertColorsForHeadEmbeddedEyeTracking = app.configFile.get('invertColorsForHeadEmbeddedEyeTracking')
  invertColorsCheckbox = QCheckBox("Invert colors for eye tracking")

  def invertColorsCheckboxToggled(checked):
    if not checked:
      if originalInvertColorsForHeadEmbeddedEyeTracking is None:
        if 'invertColorsForHeadEmbeddedEyeTracking' in app.configFile:
          del app.configFile['invertColorsForHeadEmbeddedEyeTracking']
      else:
        app.configFile['invertColorsForHeadEmbeddedEyeTracking'] = 0
    else:
      app.configFile['invertColorsForHeadEmbeddedEyeTracking'] = 1
  invertColorsCheckbox.toggled.connect(invertColorsCheckboxToggled)
  if originalInvertColorsForHeadEmbeddedEyeTracking:
    invertColorsCheckbox.setChecked(True)
  layout.addWidget(invertColorsCheckbox, alignment=Qt.AlignmentFlag.AlignCenter)

  originalImproveContrastForEyeDetectionOfHeadEmbedded = app.configFile.get('improveContrastForEyeDetectionOfHeadEmbedded')
  improveContrastCheckbox = QCheckBox("Improve contrast for eye detection")

  def improveContrastCheckboxToggled(checked):
    if not checked:
      if originalImproveContrastForEyeDetectionOfHeadEmbedded is None:
        if 'improveContrastForEyeDetectionOfHeadEmbedded' in app.configFile:
          del app.configFile['improveContrastForEyeDetectionOfHeadEmbedded']
      else:
        app.configFile['improveContrastForEyeDetectionOfHeadEmbedded'] = 0
    else:
      app.configFile['improveContrastForEyeDetectionOfHeadEmbedded'] = 1
  improveContrastCheckbox.toggled.connect(improveContrastCheckboxToggled)
  if originalImproveContrastForEyeDetectionOfHeadEmbedded or originalImproveContrastForEyeDetectionOfHeadEmbedded is None:
    improveContrastCheckbox.setChecked(True)
  layout.addWidget(improveContrastCheckbox, alignment=Qt.AlignmentFlag.AlignCenter)

  layout.addSpacing(50)
  ellipseBtn = QPushButton("Add eye tracking with ellipse method")
  ellipseBtn.clicked.connect(lambda: _adjustEyeTracking(firstFrame, totalFrames, ellipse=True))
  layout.addWidget(ellipseBtn, alignment=Qt.AlignmentFlag.AlignCenter)
  layout.addWidget(QLabel("Recommended for high quality images (eyes clearly differentiated from swim bladder)"), alignment=Qt.AlignmentFlag.AlignCenter)
  layout.addSpacing(50)
  segmentBtn = QPushButton("Add eye tracking with segment method")
  segmentBtn.clicked.connect(lambda: _adjustEyeTracking(firstFrame, totalFrames, ellipse=False))
  layout.addWidget(segmentBtn, alignment=Qt.AlignmentFlag.AlignCenter)
  layout.addWidget(QLabel("Recommended for poorer quality images"), alignment=Qt.AlignmentFlag.AlignCenter)
  layout.addSpacing(50)

  def removeTracking():
    app = QApplication.instance()
    if "eyeTracking" in app.configFile:
      del app.configFile["eyeTracking"]
    if "eyeTrackingHeadEmbeddedWithSegment" in app.configFile:
      del app.configFile["eyeTrackingHeadEmbeddedWithSegment"]
    if "eyeTrackingHeadEmbeddedWithEllipse" in app.configFile:
      del app.configFile["eyeTrackingHeadEmbeddedWithEllipse"]
    QMessageBox.information(app.window, "Eye tracking removed", "Eye tracking was removed from the config.")
  removeBtn = QPushButton("Remove eye tracking")
  removeBtn.clicked.connect(removeTracking)
  layout.addWidget(removeBtn, alignment=Qt.AlignmentFlag.AlignCenter)
  layout.addSpacing(50)

  buttons = (("Done! Save changes!", None),)
  util.showBlockingPage(layout, title="Add eye tracking", buttons=buttons)


class _AlignedLabel(QWidget):  # this will mimick the alignment of SliderWithSpinbox's labels
  def __init__(self, text, extraWidget=None):
    super().__init__()

    layout = QGridLayout()
    layout.setRowStretch(0, 1)
    layout.setColumnStretch(0, 1)
    layout.setRowStretch(3, 1)
    layout.setColumnStretch(4, 1)
    layout.setVerticalSpacing(0)

    label = QLabel(text)
    layout.addWidget(label, 1, 1)
    slider = QSlider(Qt.Orientation.Horizontal)
    policy = slider.sizePolicy()
    policy.setRetainSizeWhenHidden(True)
    slider.setSizePolicy(policy)
    slider.setFixedWidth(0)
    slider.setVisible(False)
    layout.addWidget(slider, 2, 2)
    spinbox = QSpinBox()
    policy = slider.sizePolicy()
    policy.setRetainSizeWhenHidden(True)
    spinbox.setSizePolicy(policy)
    spinbox.setFixedWidth(0)
    spinbox.setVisible(False)
    layout.addWidget(spinbox, 2, 3)
    if extraWidget is not None:
      layout.addWidget(extraWidget, 2, 1)

    layout.setContentsMargins(20, 5, 20, 5)
    self.setLayout(layout)


def adjustParamInsideAlgoPage(useNext=True):
  app = QApplication.instance()

  layout = QVBoxLayout()
  title = "Select %sframe range for advanced parameter adjustment" % ("well and " if app.wellPositions else "")
  layout.addWidget(util.apply_style(QLabel(title), font=util.TITLE_FONT), alignment=Qt.AlignmentFlag.AlignCenter)

  cap = zzVideoReading.VideoCapture(app.videoToCreateConfigFileFor)

  firstFrame = app.configFile.get("firstFrame", 1)
  maxFrame = cap.get(7) - 1
  frameSlider = util.SliderWithSpinbox(firstFrame, 0, maxFrame, name="First frame")

  def getFrame(improveContrast=None):
    cap.set(1, frameSlider.value())
    ret, frame = cap.read()
    hyperparameters = getHyperparametersSimple(app.configFile)
    if improveContrast is None:
      improveContrast = hyperparameters["outputValidationVideoContrastImprovement"]
    if improveContrast:
      frame = util.improveContrast(frame, hyperparameters["outputValidationVideoContrastImprovementQuartile"])
    return frame
  frameSlider.valueChanged.connect(lambda: util.setPixmapFromCv(getFrame(), video))

  img = getFrame()
  height, width = img.shape[:2]
  video = _WellSelectionLabel(width, height)
  layout.addWidget(video, alignment=Qt.AlignmentFlag.AlignCenter, stretch=1)

  if useNext:
    originalOutputValidationVideoContrastImprovement = app.configFile.get('outputValidationVideoContrastImprovement')
    def contrastCheckboxToggled(checked):
      if checked:
        app.configFile["outputValidationVideoContrastImprovement"] = 1
      elif originalOutputValidationVideoContrastImprovement is None:
        if "outputValidationVideoContrastImprovement" in app.configFile:
          del app.configFile["outputValidationVideoContrastImprovement"]
      else:
        app.configFile["outputValidationVideoContrastImprovement"] = 0
      util.setPixmapFromCv(getFrame(), video)
    contrastCheckbox = QCheckBox("Improve contrast on validation video")
    contrastCheckbox.toggled.connect(contrastCheckboxToggled)
    QTimer.singleShot(0, lambda: contrastCheckbox.setChecked(True))
    layout.addWidget(contrastCheckbox, alignment=Qt.AlignmentFlag.AlignCenter)

  sublayout = QHBoxLayout()
  sublayout.addStretch(1)
  sublayout.addWidget(_AlignedLabel("Select frame range:"), alignment=Qt.AlignmentFlag.AlignRight)
  sublayout.addWidget(frameSlider, alignment=Qt.AlignmentFlag.AlignCenter)
  if maxFrame > 1000:
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
  lastFrameLabel = QLabel(str(min(frameSlider.value() + 500, int(maxFrame))))
  sublayout.addWidget(_AlignedLabel("Last frame:", lastFrameLabel), alignment=Qt.AlignmentFlag.AlignLeft)
  sublayout.addStretch(1)
  layout.addLayout(sublayout)

  recalculateLayout = QHBoxLayout()
  recalculateLayout.addStretch()
  recalculateLayout.addWidget(util.apply_style(QLabel("Recalculate background using this number of images:"), font=QFont("Helvetica", 10)), alignment=Qt.AlignmentFlag.AlignCenter)
  nbImagesForBackgroundCalculation = QLineEdit()
  nbImagesForBackgroundCalculation.setValidator(QIntValidator(nbImagesForBackgroundCalculation))
  nbImagesForBackgroundCalculation.validator().setBottom(0)
  nbImagesForBackgroundCalculation.setText("60")
  nbImagesForBackgroundCalculation.setFixedWidth(50)
  recalculateLayout.addWidget(nbImagesForBackgroundCalculation, alignment=Qt.AlignmentFlag.AlignCenter)
  recalculateBtn = QPushButton("Recalculate")
  recalculateBtn.clicked.connect(lambda: app.calculateBackground(app, nbImagesForBackgroundCalculation.text(), useNext=useNext))
  recalculateLayout.addWidget(recalculateBtn, alignment=Qt.AlignmentFlag.AlignCenter)
  recalculateLayout.addStretch()
  layout.addLayout(recalculateLayout)

  adjustButtonsLayout = QHBoxLayout()
  adjustButtonsLayout.addStretch()
  adjustBoutsBtn = QPushButton("Adjust Bouts Detection")
  adjustBoutsBtn.clicked.connect(lambda: app.detectBouts(app, video.getWell(), frameSlider.value(), False, reloadWellPositions=False))
  adjustBoutsBtn.setToolTip("The aim here is to adjust parameters in order for the red dot on the top left of the image to appear when and only when movement is occurring.\n"
                            "WARNING: if you don't want ZebraZoom to detect bouts, don't click on this button.")
  adjustButtonsLayout.addWidget(adjustBoutsBtn, alignment=Qt.AlignmentFlag.AlignCenter)
  adjustTrackingBtn = QPushButton("Adjust Tracking")
  adjustTrackingBtn.clicked.connect(lambda: app.adjustHeadEmbededTracking(app, video.getWell(), frameSlider.value(), False))
  adjustTrackingBtn.setToolTip('WARNING: only click this button if you\'ve tried to track without adjusting these parameters first. Trying to adjust these could make the tracking worse.\n'
                               'Warning: for some of the "overwrite" parameters, you will need to change the initial value for the "overwrite" to take effect.')
  adjustButtonsLayout.addWidget(adjustTrackingBtn, alignment=Qt.AlignmentFlag.AlignCenter)
  addBlackSegmentsBtn = QPushButton("Add Black Segments on Artefacts")
  addBlackSegmentsBtn.clicked.connect(lambda: _addBlackSegments(app.configFile, app.videoToCreateConfigFileFor, frameSlider.value(), video.getWell(), cap))
  adjustButtonsLayout.addWidget(addBlackSegmentsBtn, alignment=Qt.AlignmentFlag.AlignCenter)
  selectROIBtn = QPushButton("Select a Region of Interest")
  selectROIBtn.clicked.connect(lambda: _selectROI(app.configFile, getFrame))
  adjustButtonsLayout.addWidget(selectROIBtn, alignment=Qt.AlignmentFlag.AlignCenter)
  addEyeTrackingBtn = QPushButton("Add Eye Tracking")
  addEyeTrackingBtn.clicked.connect(lambda: _addEyeTracking(frameSlider.value(), int(cap.get(7))))
  adjustButtonsLayout.addWidget(addEyeTrackingBtn, alignment=Qt.AlignmentFlag.AlignCenter)
  adjustButtonsLayout.addStretch()
  layout.addLayout(adjustButtonsLayout)

  buttonsLayout = QHBoxLayout()
  buttonsLayout.addStretch()
  backBtn = QPushButton("Back" if useNext else "Done! Save changes!")
  backBtn.clicked.connect(lambda: app.configFileHistory[-2](restoreConfig=useNext))
  backBtn.clicked.connect(lambda: _cleanup(app, page))
  buttonsLayout.addWidget(backBtn, alignment=Qt.AlignmentFlag.AlignCenter)
  startPageBtn = util.apply_style(QPushButton("Go to the start page"), background_color=util.LIGHT_CYAN)
  startPageBtn.clicked.connect(lambda: app.show_frame("StartPage") or _cleanup(app, page))
  buttonsLayout.addWidget(startPageBtn, alignment=Qt.AlignmentFlag.AlignCenter)
  if useNext:
    nextBtn = QPushButton("Next")
    nextBtn.clicked.connect(lambda: util.addToHistory(app.show_frame)("FinishConfig") or _cleanup(app, page))
    buttonsLayout.addWidget(nextBtn, alignment=Qt.AlignmentFlag.AlignCenter)
  buttonsLayout.addStretch()
  layout.addLayout(buttonsLayout)

  page = _showPage(layout, (img, video))


def adjustParamInsideAlgoFreelySwimPage(useNext=True):
  app = QApplication.instance()

  layout = QVBoxLayout()
  title = "Select %sframe range for advanced parameter adjustment" % ("well and " if app.wellPositions else "")
  layout.addWidget(util.apply_style(QLabel(title), font=util.TITLE_FONT), alignment=Qt.AlignmentFlag.AlignCenter)

  cap = zzVideoReading.VideoCapture(app.videoToCreateConfigFileFor)

  firstFrame = app.configFile.get("firstFrame", 1)
  maxFrame = cap.get(7) - 1
  frameSlider = util.SliderWithSpinbox(firstFrame, 0, maxFrame, name="First frame")

  def getFrame():
    cap.set(1, frameSlider.value())
    ret, img = cap.read()
    return img
  frameSlider.valueChanged.connect(lambda: util.setPixmapFromCv(getFrame(), video))

  img = getFrame()
  height, width = img.shape[:2]
  video = _WellSelectionLabel(width, height)
  layout.addWidget(video, alignment=Qt.AlignmentFlag.AlignCenter, stretch=1)

  sublayout = QHBoxLayout()
  sublayout.addStretch(1)
  sublayout.addWidget(_AlignedLabel("Select frame range:"), alignment=Qt.AlignmentFlag.AlignRight)
  sublayout.addWidget(frameSlider, alignment=Qt.AlignmentFlag.AlignCenter)
  if maxFrame > 1000:
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
  lastFrameLabel = QLabel(str(min(frameSlider.value() + 500, int(maxFrame))))
  sublayout.addWidget(_AlignedLabel("Last frame:", lastFrameLabel), alignment=Qt.AlignmentFlag.AlignLeft)
  sublayout.addStretch(1)
  layout.addLayout(sublayout)

  recalculateLayout = QHBoxLayout()
  recalculateLayout.addStretch()
  recalculateLayout.addWidget(util.apply_style(QLabel("Recalculate background using this number of images:"), font=QFont("Helvetica", 10)), alignment=Qt.AlignmentFlag.AlignCenter)
  nbImagesForBackgroundCalculation = QLineEdit()
  nbImagesForBackgroundCalculation.setValidator(QIntValidator(nbImagesForBackgroundCalculation))
  nbImagesForBackgroundCalculation.validator().setBottom(0)
  nbImagesForBackgroundCalculation.setText("60")
  nbImagesForBackgroundCalculation.setFixedWidth(50)
  recalculateLayout.addWidget(nbImagesForBackgroundCalculation, alignment=Qt.AlignmentFlag.AlignCenter)
  recalculateBtn = QPushButton("Recalculate")
  recalculateBtn.clicked.connect(lambda: app.calculateBackgroundFreelySwim(app, nbImagesForBackgroundCalculation.text(), useNext=useNext))
  recalculateLayout.addWidget(recalculateBtn, alignment=Qt.AlignmentFlag.AlignCenter)
  recalculateLayout.addStretch()
  layout.addLayout(recalculateLayout)

  adjustButtonsLayout = QHBoxLayout()
  adjustButtonsLayout.addStretch()
  adjustBoutsBtn = QPushButton("Adjust Bouts Detection")
  adjustBoutsBtn.clicked.connect(lambda: app.detectBouts(app, video.getWell(), frameSlider.value(), False))
  adjustBoutsBtn.setToolTip("The aim here is to adjust parameters in order for the red dot on the top left of the image to appear when and only when movement is occurring.\n"
                            "WARNING: if you don't want ZebraZoom to detect bouts, don't click on this button.")
  adjustButtonsLayout.addWidget(adjustBoutsBtn, alignment=Qt.AlignmentFlag.AlignCenter)
  adjustTrackingBtn = QPushButton("Adjust Tracking")
  adjustTrackingBtn.clicked.connect(lambda: app.adjustFreelySwimTracking(app, video.getWell(), frameSlider.value(), False))
  adjustTrackingBtn.setToolTip("WARNING: only click this button if you've tried to track without adjusting these parameters first. Trying to adjust these could make the tracking worse.")
  adjustButtonsLayout.addWidget(adjustTrackingBtn, alignment=Qt.AlignmentFlag.AlignCenter)
  adjustButtonsLayout.addStretch()
  layout.addLayout(adjustButtonsLayout)

  buttonsLayout = QHBoxLayout()
  buttonsLayout.addStretch()
  backBtn = QPushButton("Back" if useNext else "Done! Save changes!")
  backBtn.clicked.connect(lambda: app.configFileHistory[-2](restoreConfig=useNext))
  backBtn.clicked.connect(lambda: _cleanup(app, page))
  buttonsLayout.addWidget(backBtn, alignment=Qt.AlignmentFlag.AlignCenter)
  startPageBtn = util.apply_style(QPushButton("Go to the start page"), background_color=util.LIGHT_CYAN)
  startPageBtn.clicked.connect(lambda: app.show_frame("StartPage") or _cleanup(app, page))
  buttonsLayout.addWidget(startPageBtn, alignment=Qt.AlignmentFlag.AlignCenter)
  if useNext:
    nextBtn = QPushButton("Next")
    nextBtn.clicked.connect(lambda: util.addToHistory(app.show_frame)("FinishConfig") or _cleanup(app, page))
    buttonsLayout.addWidget(nextBtn, alignment=Qt.AlignmentFlag.AlignCenter)
  buttonsLayout.addStretch()
  layout.addLayout(buttonsLayout)

  page = _showPage(layout, (img, video))


def adjustParamInsideAlgoFreelySwimAutomaticParametersPage(useNext=True):
  app = QApplication.instance()

  layout = QVBoxLayout()
  title = "Select %sframe range for fish tail tracking parameters adjustment" % ("well and " if app.wellPositions else "")
  layout.addWidget(util.apply_style(QLabel(title), font=util.TITLE_FONT), alignment=Qt.AlignmentFlag.AlignCenter)

  cap = zzVideoReading.VideoCapture(app.videoToCreateConfigFileFor)

  firstFrame = app.configFile.get("firstFrame", 1)
  maxFrame = cap.get(7) - 1
  frameSlider = util.SliderWithSpinbox(firstFrame, 0, maxFrame, name="First frame")

  def getFrame():
    cap.set(1, frameSlider.value())
    ret, img = cap.read()
    return img
  frameSlider.valueChanged.connect(lambda: util.setPixmapFromCv(getFrame(), video))

  img = getFrame()
  height, width = img.shape[:2]
  video = _WellSelectionLabel(width, height)
  layout.addWidget(video, alignment=Qt.AlignmentFlag.AlignCenter, stretch=1)

  sublayout = QHBoxLayout()
  sublayout.addStretch(1)
  sublayout.addWidget(_AlignedLabel("Select frame range:"), alignment=Qt.AlignmentFlag.AlignRight)
  sublayout.addWidget(frameSlider, alignment=Qt.AlignmentFlag.AlignCenter)
  if maxFrame > 1000:
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
  lastFrameLabel = QLabel(str(min(frameSlider.value() + 500, int(maxFrame))))
  sublayout.addWidget(_AlignedLabel("Last frame:", lastFrameLabel), alignment=Qt.AlignmentFlag.AlignLeft)
  sublayout.addStretch(1)
  layout.addLayout(sublayout)

  recalculateLayout = QHBoxLayout()
  recalculateLayout.addStretch()
  recalculateLayout.addWidget(util.apply_style(QLabel("Recalculate background using this number of images:"), font=QFont("Helvetica", 10)), alignment=Qt.AlignmentFlag.AlignCenter)
  nbImagesForBackgroundCalculation = QLineEdit()
  nbImagesForBackgroundCalculation.setValidator(QIntValidator(nbImagesForBackgroundCalculation))
  nbImagesForBackgroundCalculation.validator().setBottom(0)
  nbImagesForBackgroundCalculation.setText("60")
  nbImagesForBackgroundCalculation.setFixedWidth(50)
  recalculateLayout.addWidget(nbImagesForBackgroundCalculation, alignment=Qt.AlignmentFlag.AlignCenter)
  recalculateBtn = QPushButton("Recalculate")
  recalculateBtn.clicked.connect(lambda: app.calculateBackgroundFreelySwim(app, nbImagesForBackgroundCalculation.text(), False, True, useNext=useNext))
  recalculateLayout.addWidget(recalculateBtn, alignment=Qt.AlignmentFlag.AlignCenter)
  recalculateLayout.addStretch()
  layout.addLayout(recalculateLayout)

  adjustTrackingBtn = QPushButton("Adjust Tracking")
  adjustTrackingBtn.clicked.connect(lambda: app.adjustFreelySwimTrackingAutomaticParameters(app, video.getWell(), frameSlider.value(), False))
  layout.addWidget(adjustTrackingBtn, alignment=Qt.AlignmentFlag.AlignCenter)

  buttonsLayout = QHBoxLayout()
  buttonsLayout.addStretch()
  backBtn = QPushButton("Back" if useNext else "Done! Save changes!")
  backBtn.clicked.connect(lambda: app.configFileHistory[-2](restoreConfig=useNext))
  backBtn.clicked.connect(lambda: _cleanup(app, page))
  buttonsLayout.addWidget(backBtn, alignment=Qt.AlignmentFlag.AlignCenter)
  startPageBtn = util.apply_style(QPushButton("Go to the start page"), background_color=util.LIGHT_CYAN)
  startPageBtn.clicked.connect(lambda: app.show_frame("StartPage") or _cleanup(app, page))
  buttonsLayout.addWidget(startPageBtn, alignment=Qt.AlignmentFlag.AlignCenter)
  if useNext:
    nextBtn = QPushButton("Next")
    nextBtn.clicked.connect(lambda: util.addToHistory(app.show_frame)("FinishConfig") or _cleanup(app, page))
    buttonsLayout.addWidget(nextBtn, alignment=Qt.AlignmentFlag.AlignCenter)
  buttonsLayout.addStretch()
  layout.addLayout(buttonsLayout)

  page = _showPage(layout, (img, video))


def adjustBoutDetectionOnlyPage(useNext=True):
  app = QApplication.instance()

  layout = QVBoxLayout()
  title = "Select %sframe range for bout detection parameters adjustments" % ("well and " if app.wellPositions else "")
  layout.addWidget(util.apply_style(QLabel(title), font=util.TITLE_FONT), alignment=Qt.AlignmentFlag.AlignCenter)

  cap = zzVideoReading.VideoCapture(app.videoToCreateConfigFileFor)

  firstFrame = app.configFile.get("firstFrame", 1)
  maxFrame = cap.get(7) - 1
  frameSlider = util.SliderWithSpinbox(firstFrame, 0, maxFrame, name="First frame")

  def getFrame():
    cap.set(1, frameSlider.value())
    ret, img = cap.read()
    return img
  frameSlider.valueChanged.connect(lambda: util.setPixmapFromCv(getFrame(), video) or lastFrameLabel.setText(str(min(frameSlider.value() + 500, int(maxFrame)))))

  img = getFrame()
  height, width = img.shape[:2]
  video = _WellSelectionLabel(width, height)
  layout.addWidget(video, alignment=Qt.AlignmentFlag.AlignCenter, stretch=1)

  sublayout = QHBoxLayout()
  sublayout.addStretch(1)
  sublayout.addWidget(_AlignedLabel("Select frame range:"), alignment=Qt.AlignmentFlag.AlignRight)
  sublayout.addWidget(frameSlider, alignment=Qt.AlignmentFlag.AlignCenter)
  if maxFrame > 1000:
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
  lastFrameLabel = QLabel(str(min(frameSlider.value() + 500, int(maxFrame))))
  sublayout.addWidget(_AlignedLabel("Last frame:", lastFrameLabel), alignment=Qt.AlignmentFlag.AlignLeft)
  sublayout.addStretch(1)
  layout.addLayout(sublayout)

  recalculateLayout = QHBoxLayout()
  recalculateLayout.addStretch()
  recalculateLayout.addWidget(util.apply_style(QLabel("Recalculate background using this number of images:"), font=QFont("Helvetica", 10)), alignment=Qt.AlignmentFlag.AlignCenter)
  nbImagesForBackgroundCalculation = QLineEdit()
  nbImagesForBackgroundCalculation.setValidator(QIntValidator(nbImagesForBackgroundCalculation))
  nbImagesForBackgroundCalculation.validator().setBottom(0)
  nbImagesForBackgroundCalculation.setText("60")
  nbImagesForBackgroundCalculation.setFixedWidth(50)
  recalculateLayout.addWidget(nbImagesForBackgroundCalculation, alignment=Qt.AlignmentFlag.AlignCenter)
  recalculateBtn = QPushButton("Recalculate")
  recalculateBtn.clicked.connect(lambda: app.calculateBackgroundFreelySwim(app, nbImagesForBackgroundCalculation.text(), False, True, useNext=useNext))
  recalculateLayout.addWidget(recalculateBtn, alignment=Qt.AlignmentFlag.AlignCenter)
  recalculateLayout.addStretch()
  layout.addLayout(recalculateLayout)

  coordinatesOnlyBoutDetectCheckbox = QCheckBox("Use only the body coordinates to detect bouts (faster, but potentially less accurate)")
  originalCoordinatesOnlyBoutDetection = app.configFile.get("coordinatesOnlyBoutDetection", None)
  def coordinatesOnlyBoutDetectCheckboxToggled(checked):
    if checked:
      app.configFile["coordinatesOnlyBoutDetection"] = 1
    elif originalCoordinatesOnlyBoutDetection is not None:
      app.configFile["coordinatesOnlyBoutDetection"] = 0
    elif "coordinatesOnlyBoutDetection" in app.configFile:
      del app.configFile["coordinatesOnlyBoutDetection"]
    minDistLabel.setVisible(checked)
    minDistLineEdit.setVisible(checked)
    adjustBoutsBtn.setVisible(not checked)
    frameGapSlider.setVisible(checked)
  coordinatesOnlyBoutDetectCheckbox.toggled.connect(coordinatesOnlyBoutDetectCheckboxToggled)
  trackingMethod = app.configFile.get("trackingMethod", None)
  coordinatesOnlyBoutDetectCheckbox.setVisible(trackingMethod == "fastCenterOfMassTracking_KNNbackgroundSubtraction" or trackingMethod == "fastCenterOfMassTracking_ClassicalBackgroundSubtraction")
  layout.addWidget(coordinatesOnlyBoutDetectCheckbox, alignment=Qt.AlignmentFlag.AlignCenter)

  minDistLayout = QHBoxLayout()
  minDistLayout.addStretch()
  originalMinDist = app.configFile.get("coordinatesOnlyBoutDetectionMinDist", None)
  minDistLineEdit = QLineEdit()
  minDistLineEdit.setValidator(QIntValidator())
  minDistLineEdit.validator().setBottom(0)
  minDistLineEdit.setText(str(originalMinDist) if originalMinDist is not None else '0')

  def updateMinDist(text):
    if text:
      app.configFile["coordinatesOnlyBoutDetectionMinDist"] = int(text)
    elif originalMinDist is not None:
      app.configFile["coordinatesOnlyBoutDetectionMinDist"] = 0
    elif "coordinatesOnlyBoutDetectionMinDist" in app.configFile:
      del app.configFile["coordinatesOnlyBoutDetectionMinDist"]
  minDistLineEdit.textChanged.connect(updateMinDist)
  minDistLabel = QPushButton("coordinatesOnlyBoutDetectionMinDist:")

  def adjustMinDistForBoutDetect():
    cancelled = False
    def cancel():
      nonlocal cancelled
      cancelled = True
    center, radius = util.getCircle(getFrame(), 'Click on the center of an animal and select the minimum distance it should travel to consider it has moved', backBtnCb=cancel, zoomable=True)
    if not cancelled:
      minDistLineEdit.setText(str(radius))
  minDistLabel.clicked.connect(adjustMinDistForBoutDetect)
  minDistLabel.setVisible(False)
  minDistLayout.addWidget(minDistLabel, alignment=Qt.AlignmentFlag.AlignCenter)
  minDistLineEdit.setVisible(False)
  minDistLayout.addWidget(minDistLineEdit, alignment=Qt.AlignmentFlag.AlignCenter)
  minDistLayout.addStretch()
  layout.addLayout(minDistLayout)

  adjustBoutsBtn = QPushButton("Adjust Bouts Detection")
  adjustBoutsBtn.setToolTip("The aim here is to adjust parameters in order for the red dot on the top left of the image to appear when and only when movement is occurring.")
  adjustBoutsBtn.clicked.connect(lambda: app.detectBouts(app, video.getWell(), frameSlider.value(), False))
  layout.addWidget(adjustBoutsBtn, alignment=Qt.AlignmentFlag.AlignCenter)

  frameGapSlider = util.SliderWithSpinbox(app.configFile.get("frameGapComparision", 1), 1, 15, name="frameGapComparision")
  frameGapSlider.setVisible(False)

  def frameGapComparisonChanged(value):
    app.configFile["frameGapComparision"] = value
  frameGapSlider.valueChanged.connect(frameGapComparisonChanged)
  layout.addWidget(frameGapSlider, alignment=Qt.AlignmentFlag.AlignCenter)

  coordinatesOnlyBoutDetectCheckbox.setChecked(coordinatesOnlyBoutDetectCheckbox.isVisible() and app.configFile.get("coordinatesOnlyBoutDetection", False))

  fillGapLayout = QHBoxLayout()
  fillGapLayout.addStretch()
  fillGapLabel = util.apply_style(QLabel("Important: Bouts Merging: fillGapFrameNb:"), font=QFont("Helvetica", 0))
  fillGapLabel.setToolTip("'fillGapFrameNb' parameter controls the distance (in number frames) under which two subsequent bouts are merged into one.")
  fillGapLayout.addWidget(fillGapLabel, alignment=Qt.AlignmentFlag.AlignCenter)
  fillGapFrameNb = QLineEdit()
  fillGapFrameNb.setValidator(QIntValidator(nbImagesForBackgroundCalculation))
  fillGapFrameNb.validator().setBottom(0)
  if "fillGapFrameNb" in app.configFile:
    fillGapFrameNb.setText(str(app.configFile["fillGapFrameNb"]))
  fillGapFrameNb.setFixedWidth(50)

  def updateFillGapFrameNb(text):
    if not text:
      del app.configFile["fillGapFrameNb"]
    else:
      app.configFile["fillGapFrameNb"] = int(text)
  fillGapFrameNb.textChanged.connect(updateFillGapFrameNb)
  fillGapFrameNb.setToolTip("'fillGapFrameNb' parameter controls the distance (in number frames) under which two subsequent bouts are merged into one.")
  fillGapLayout.addWidget(fillGapFrameNb, alignment=Qt.AlignmentFlag.AlignCenter)
  fillGapLayout.addStretch()
  layout.addLayout(fillGapLayout)

  buttonsLayout = QHBoxLayout()
  buttonsLayout.addStretch()
  backBtn = QPushButton("Back" if useNext else "Done! Save changes!")
  backBtn.clicked.connect(lambda: app.configFileHistory[-2](restoreConfig=useNext))
  backBtn.clicked.connect(lambda: _cleanup(app, page))
  buttonsLayout.addWidget(backBtn, alignment=Qt.AlignmentFlag.AlignCenter)
  startPageBtn = util.apply_style(QPushButton("Go to the start page"), background_color=util.LIGHT_CYAN)
  startPageBtn.clicked.connect(lambda: app.show_frame("StartPage") or _cleanup(app, page))
  buttonsLayout.addWidget(startPageBtn, alignment=Qt.AlignmentFlag.AlignCenter)
  if useNext:
    nextBtn = QPushButton("Next")
    nextBtn.clicked.connect(lambda: util.addToHistory(app.show_frame)("FinishConfig") or _cleanup(app, page))
    buttonsLayout.addWidget(nextBtn, alignment=Qt.AlignmentFlag.AlignCenter)
  buttonsLayout.addStretch()
  layout.addLayout(buttonsLayout)

  page = _showPage(layout, (img, video))
