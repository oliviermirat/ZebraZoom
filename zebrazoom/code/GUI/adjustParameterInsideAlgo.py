from PyQt5.QtCore import Qt, pyqtSignal, QPointF, QRect, QRectF, QSizeF
from PyQt5.QtGui import QColor, QFont, QIntValidator, QPainter, QPolygon, QPolygonF, QTransform
from PyQt5.QtWidgets import QApplication, QLabel, QLineEdit, QCheckBox, QPushButton, QHBoxLayout, QVBoxLayout, QWidget

import zebrazoom.videoFormatConversion.zzVideoReading as zzVideoReading
import zebrazoom.code.util as util


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


def adjustParamInsideAlgoPage(useNext=True):
  app = QApplication.instance()

  layout = QVBoxLayout()
  title = "Select %sfirst frame for advanced parameter adjustment" % ("well and " if app.wellPositions else "")
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
    sublayout.addLayout(adjustLayout, stretch=1)
  else:
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
  recalculateBtn.clicked.connect(lambda: app.calculateBackgroundFreelySwim(app, nbImagesForBackgroundCalculation.text()))
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
  adjustTrackingBtn.clicked.connect(lambda: app.adjustHeadEmbededTracking(app, video.getWell(), frameSlider.value(), False))
  adjustTrackingBtn.setToolTip('WARNING: only click this button if you\'ve tried to track without adjusting these parameters first. Trying to adjust these could make the tracking worse.\n'
                               'Warning: for some of the "overwrite" parameters, you will need to change the initial value for the "overwrite" to take effect.')
  adjustButtonsLayout.addWidget(adjustTrackingBtn, alignment=Qt.AlignmentFlag.AlignCenter)
  adjustButtonsLayout.addStretch()
  layout.addLayout(adjustButtonsLayout)

  buttonsLayout = QHBoxLayout()
  buttonsLayout.addStretch()
  backBtn = QPushButton("Back")
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
  title = "Select %sfirst frame for advanced parameter adjustment" % ("well and " if app.wellPositions else "")
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
    sublayout.addLayout(adjustLayout, stretch=1)
  else:
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
  recalculateBtn.clicked.connect(lambda: app.calculateBackgroundFreelySwim(app, nbImagesForBackgroundCalculation.text()))
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
  backBtn = QPushButton("Back")
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
  title = "Select %sfirst frame for fish tail tracking parameters adjustment" % ("well and " if app.wellPositions else "")
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
    sublayout.addLayout(adjustLayout, stretch=1)
  else:
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
  recalculateBtn.clicked.connect(lambda: app.calculateBackgroundFreelySwim(app, nbImagesForBackgroundCalculation.text(), False, True))
  recalculateLayout.addWidget(recalculateBtn, alignment=Qt.AlignmentFlag.AlignCenter)
  recalculateLayout.addStretch()
  layout.addLayout(recalculateLayout)

  adjustTrackingBtn = QPushButton("Adjust Tracking")
  adjustTrackingBtn.clicked.connect(lambda: app.adjustFreelySwimTrackingAutomaticParameters(app, video.getWell(), frameSlider.value(), False))
  layout.addWidget(adjustTrackingBtn, alignment=Qt.AlignmentFlag.AlignCenter)

  buttonsLayout = QHBoxLayout()
  buttonsLayout.addStretch()
  backBtn = QPushButton("Back")
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
  title = "Select %sfirst frame for bout detection parameters adjustments" % ("well and " if app.wellPositions else "")
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
    sublayout.addLayout(adjustLayout, stretch=1)
  else:
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
  recalculateBtn.clicked.connect(lambda: app.calculateBackgroundFreelySwim(app, nbImagesForBackgroundCalculation.text(), False, True))
  recalculateLayout.addWidget(recalculateBtn, alignment=Qt.AlignmentFlag.AlignCenter)
  recalculateLayout.addStretch()
  layout.addLayout(recalculateLayout)

  adjustBoutsBtn = QPushButton("Adjust Bouts Detection")
  adjustBoutsBtn.setToolTip("The aim here is to adjust parameters in order for the red dot on the top left of the image to appear when and only when movement is occurring.")
  adjustBoutsBtn.clicked.connect(lambda: app.detectBouts(app, video.getWell(), frameSlider.value(), False))
  layout.addWidget(adjustBoutsBtn, alignment=Qt.AlignmentFlag.AlignCenter)

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
  backBtn = QPushButton("Back")
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
