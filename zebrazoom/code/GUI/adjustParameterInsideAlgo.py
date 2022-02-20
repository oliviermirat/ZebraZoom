try:
  from PyQt6.QtCore import Qt, QPointF, QRect, QRectF, QSizeF
  from PyQt6.QtGui import QColor, QFont, QIntValidator, QPainter, QPolygon, QPolygonF, QTransform
  from PyQt6.QtWidgets import QApplication, QLabel, QLineEdit, QCheckBox, QPushButton, QVBoxLayout, QWidget
except ImportError:
  from PyQt5.QtCore import Qt, pyqtSignal, QPointF, QRect, QRectF, QSizeF
  from PyQt5.QtGui import QColor, QFont, QIntValidator, QPainter, QPolygon, QPolygonF, QTransform
  from PyQt5.QtWidgets import QApplication, QLabel, QLineEdit, QCheckBox, QPushButton, QVBoxLayout, QWidget

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


def _showPage(layout, labelInfo, exitButtons):
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
  for btn in exitButtons:
    btn.clicked.connect(lambda: _cleanup(app, page))


def adjustParamInsideAlgoPage():
  app = QApplication.instance()

  layout = QVBoxLayout()
  layout.addWidget(util.apply_style(QLabel("Advanced Parameter adjustment"), font=util.TITLE_FONT), alignment=Qt.AlignmentFlag.AlignCenter)

  cap = zzVideoReading.VideoCapture(app.videoToCreateConfigFileFor)

  firstFrame = app.configFile.get("firstFrame", 1)
  frameSlider = util.SliderWithSpinbox(firstFrame, 0, cap.get(7) - 1, name="Frame")

  def getFrame():
    cap.set(1, frameSlider.value())
    ret, img = cap.read()
    return img
  frameSlider.valueChanged.connect(lambda: util.setPixmapFromCv(getFrame(), video))

  img = getFrame()
  height, width = img.shape[:2]
  video = _WellSelectionLabel(width, height)
  layout.setStretch(1, 1)
  layout.addWidget(video, alignment=Qt.AlignmentFlag.AlignCenter)
  layout.addWidget(frameSlider, alignment=Qt.AlignmentFlag.AlignCenter)

  layout.addWidget(util.apply_style(QLabel("Recalculate background using this number of images: (default is 60)"), font=QFont("Helvetica", 10)), alignment=Qt.AlignmentFlag.AlignCenter)
  nbImagesForBackgroundCalculation = QLineEdit()
  nbImagesForBackgroundCalculation.setValidator(QIntValidator(nbImagesForBackgroundCalculation))
  nbImagesForBackgroundCalculation.validator().setBottom(0)
  layout.addWidget(nbImagesForBackgroundCalculation, alignment=Qt.AlignmentFlag.AlignCenter)
  recalculateBtn = QPushButton("Recalculate")
  recalculateBtn.clicked.connect(lambda: app.calculateBackground(app, nbImagesForBackgroundCalculation.text()))
  layout.addWidget(recalculateBtn, alignment=Qt.AlignmentFlag.AlignCenter)

  adjustOnWholeVideoCheckbox = QCheckBox("I want to adjust parameters over the entire video, not only on 500 frames at a time.")
  layout.addWidget(adjustOnWholeVideoCheckbox, alignment=Qt.AlignmentFlag.AlignCenter)

  adjustBoutsBtn = QPushButton("Adjust Bouts Detection")
  adjustBoutsBtn.clicked.connect(lambda: app.detectBouts(app, video.getWell(), frameSlider.value(), adjustOnWholeVideoCheckbox.isChecked()))
  layout.addWidget(adjustBoutsBtn, alignment=Qt.AlignmentFlag.AlignCenter)
  layout.addWidget(util.apply_style(QLabel("The aim here is to adjust parameters in order for the red dot on the top left of the image to appear when and only when movement is occurring."), font=QFont("Helvetica", 10)), alignment=Qt.AlignmentFlag.AlignCenter)
  layout.addWidget(util.apply_style(QLabel("WARNING: if you don't want ZebraZoom to detect bouts, don't click on the button above."), font=QFont("Helvetica", 10)), alignment=Qt.AlignmentFlag.AlignCenter)

  adjustTrackingBtn = QPushButton("Adjust Tracking")
  adjustTrackingBtn.clicked.connect(lambda: app.adjustHeadEmbededTracking(app, video.getWell(), frameSlider.value(), adjustOnWholeVideoCheckbox.isChecked()))
  layout.addWidget(adjustTrackingBtn, alignment=Qt.AlignmentFlag.AlignCenter)
  layout.addWidget(util.apply_style(QLabel("WARNING: only click the button above if you've tried to track without adjusting these parameters first. Trying to adjust these could make the tracking worse."), font=QFont("Helvetica", 10)), alignment=Qt.AlignmentFlag.AlignCenter)
  layout.addWidget(util.apply_style(QLabel('Warning: for some of the "overwrite" parameters, you will need to change the initial value for the "overwrite" to take effect.'), font=QFont("Helvetica", 10)), alignment=Qt.AlignmentFlag.AlignCenter)

  nextBtn = QPushButton("Next")
  nextBtn.clicked.connect(lambda: app.show_frame("FinishConfig"))
  layout.addWidget(nextBtn, alignment=Qt.AlignmentFlag.AlignCenter)

  _showPage(layout, (img, video), (nextBtn,))


def adjustParamInsideAlgoFreelySwimPage():
  app = QApplication.instance()

  layout = QVBoxLayout()
  layout.addWidget(util.apply_style(QLabel("Advanced Parameter adjustment"), font=util.TITLE_FONT), alignment=Qt.AlignmentFlag.AlignCenter)

  cap = zzVideoReading.VideoCapture(app.videoToCreateConfigFileFor)

  firstFrame = app.configFile.get("firstFrame", 1)
  frameSlider = util.SliderWithSpinbox(firstFrame, 0, cap.get(7) - 1, name="Frame")

  def getFrame():
    cap.set(1, frameSlider.value())
    ret, img = cap.read()
    return img
  frameSlider.valueChanged.connect(lambda: util.setPixmapFromCv(getFrame(), video))

  img = getFrame()
  height, width = img.shape[:2]
  video = _WellSelectionLabel(width, height)
  layout.setStretch(1, 1)
  layout.addWidget(video, alignment=Qt.AlignmentFlag.AlignCenter)
  layout.addWidget(frameSlider, alignment=Qt.AlignmentFlag.AlignCenter)

  layout.addWidget(util.apply_style(QLabel("Recalculate background using this number of images: (default is 60)"), font=QFont("Helvetica", 10)), alignment=Qt.AlignmentFlag.AlignCenter)
  nbImagesForBackgroundCalculation = QLineEdit()
  nbImagesForBackgroundCalculation.setValidator(QIntValidator(nbImagesForBackgroundCalculation))
  nbImagesForBackgroundCalculation.validator().setBottom(0)
  layout.addWidget(nbImagesForBackgroundCalculation, alignment=Qt.AlignmentFlag.AlignCenter)
  recalculateBtn = QPushButton("Recalculate")
  recalculateBtn.clicked.connect(lambda: app.calculateBackgroundFreelySwim(app, nbImagesForBackgroundCalculation.text()))
  layout.addWidget(recalculateBtn, alignment=Qt.AlignmentFlag.AlignCenter)

  adjustOnWholeVideoCheckbox = QCheckBox("I want to adjust parameters over the entire video, not only on 500 frames at a time.")
  layout.addWidget(adjustOnWholeVideoCheckbox, alignment=Qt.AlignmentFlag.AlignCenter)

  adjustBoutsBtn = QPushButton("Adjust Bouts Detection")
  adjustBoutsBtn.clicked.connect(lambda: app.detectBouts(app, video.getWell(), frameSlider.value(), adjustOnWholeVideoCheckbox.isChecked()))
  layout.addWidget(adjustBoutsBtn, alignment=Qt.AlignmentFlag.AlignCenter)
  layout.addWidget(util.apply_style(QLabel("The aim here is to adjust parameters in order for the red dot on the top left of the image to appear when and only when movement is occurring."), font=QFont("Helvetica", 10)), alignment=Qt.AlignmentFlag.AlignCenter)
  layout.addWidget(util.apply_style(QLabel("WARNING: if you don't want ZebraZoom to detect bouts, don't click on the button above."), font=QFont("Helvetica", 10)), alignment=Qt.AlignmentFlag.AlignCenter)

  adjustTrackingBtn = QPushButton("Adjust Tracking")
  adjustTrackingBtn.clicked.connect(lambda: app.adjustFreelySwimTracking(app, video.getWell(), frameSlider.value(), adjustOnWholeVideoCheckbox.isChecked()))
  layout.addWidget(adjustTrackingBtn, alignment=Qt.AlignmentFlag.AlignCenter)
  layout.addWidget(util.apply_style(QLabel("WARNING: only click the button above if you've tried to track without adjusting these parameters first. Trying to adjust these could make the tracking worse."), font=QFont("Helvetica", 10)), alignment=Qt.AlignmentFlag.AlignCenter)

  nextBtn = QPushButton("Next")
  nextBtn.clicked.connect(lambda: app.show_frame("FinishConfig"))
  layout.addWidget(nextBtn, alignment=Qt.AlignmentFlag.AlignCenter)

  _showPage(layout, (img, video), (nextBtn,))


def adjustParamInsideAlgoFreelySwimAutomaticParametersPage():
  app = QApplication.instance()

  layout = QVBoxLayout()
  layout.addWidget(util.apply_style(QLabel("Fish tail tracking parameters adjustment"), font=util.TITLE_FONT), alignment=Qt.AlignmentFlag.AlignCenter)

  cap = zzVideoReading.VideoCapture(app.videoToCreateConfigFileFor)

  firstFrame = app.configFile.get("firstFrame", 1)
  frameSlider = util.SliderWithSpinbox(firstFrame, 0, cap.get(7) - 1, name="Frame")

  def getFrame():
    cap.set(1, frameSlider.value())
    ret, img = cap.read()
    return img
  frameSlider.valueChanged.connect(lambda: util.setPixmapFromCv(getFrame(), video))

  img = getFrame()
  height, width = img.shape[:2]
  video = _WellSelectionLabel(width, height)
  layout.setStretch(1, 1)
  layout.addWidget(video, alignment=Qt.AlignmentFlag.AlignCenter)
  layout.addWidget(frameSlider, alignment=Qt.AlignmentFlag.AlignCenter)

  layout.addWidget(util.apply_style(QLabel("Recalculate background using this number of images: (default is 60)"), font=QFont("Helvetica", 10)), alignment=Qt.AlignmentFlag.AlignCenter)
  nbImagesForBackgroundCalculation = QLineEdit()
  nbImagesForBackgroundCalculation.setValidator(QIntValidator(nbImagesForBackgroundCalculation))
  nbImagesForBackgroundCalculation.validator().setBottom(0)
  layout.addWidget(nbImagesForBackgroundCalculation, alignment=Qt.AlignmentFlag.AlignCenter)
  recalculateBtn = QPushButton("Recalculate")
  recalculateBtn.clicked.connect(lambda: app.calculateBackgroundFreelySwim(app, nbImagesForBackgroundCalculation.text(), False, True))
  layout.addWidget(recalculateBtn, alignment=Qt.AlignmentFlag.AlignCenter)

  adjustOnWholeVideoCheckbox = QCheckBox("I want to adjust parameters over the entire video, not only on 500 frames at a time.")
  layout.addWidget(adjustOnWholeVideoCheckbox, alignment=Qt.AlignmentFlag.AlignCenter)

  adjustTrackingBtn = QPushButton("Adjust Tracking")
  adjustTrackingBtn.clicked.connect(lambda: app.adjustFreelySwimTrackingAutomaticParameters(app, video.getWell(), frameSlider.value(), adjustOnWholeVideoCheckbox.isChecked()))
  layout.addWidget(adjustTrackingBtn, alignment=Qt.AlignmentFlag.AlignCenter)

  nextBtn = QPushButton("Save New Configuration File")
  nextBtn.clicked.connect(lambda: app.show_frame("FinishConfig"))
  layout.addWidget(nextBtn, alignment=Qt.AlignmentFlag.AlignCenter)

  startPageBtn = util.apply_style(QPushButton("Go to the start page"), background_color=util.LIGHT_CYAN)
  startPageBtn.clicked.connect(lambda: app.show_frame("StartPage"))
  layout.addWidget(startPageBtn, alignment=Qt.AlignmentFlag.AlignCenter)

  _showPage(layout, (img, video), (nextBtn, startPageBtn))


def adjustBoutDetectionOnlyPage():
  app = QApplication.instance()

  layout = QVBoxLayout()
  layout.addWidget(util.apply_style(QLabel("Bout detection configuration file parameters adjustments"), font=util.TITLE_FONT), alignment=Qt.AlignmentFlag.AlignCenter)

  cap = zzVideoReading.VideoCapture(app.videoToCreateConfigFileFor)

  firstFrame = app.configFile.get("firstFrame", 1)
  frameSlider = util.SliderWithSpinbox(firstFrame, 0, cap.get(7) - 1, name="Frame")

  def getFrame():
    cap.set(1, frameSlider.value())
    ret, img = cap.read()
    return img
  frameSlider.valueChanged.connect(lambda: util.setPixmapFromCv(getFrame(), video))

  img = getFrame()
  height, width = img.shape[:2]
  video = _WellSelectionLabel(width, height)
  layout.setStretch(1, 1)
  layout.addWidget(video, alignment=Qt.AlignmentFlag.AlignCenter)
  layout.addWidget(frameSlider, alignment=Qt.AlignmentFlag.AlignCenter)

  layout.addWidget(util.apply_style(QLabel("Recalculate background using this number of images: (default is 60)"), font=QFont("Helvetica", 10)), alignment=Qt.AlignmentFlag.AlignCenter)
  nbImagesForBackgroundCalculation = QLineEdit()
  nbImagesForBackgroundCalculation.setValidator(QIntValidator(nbImagesForBackgroundCalculation))
  nbImagesForBackgroundCalculation.validator().setBottom(0)
  layout.addWidget(nbImagesForBackgroundCalculation, alignment=Qt.AlignmentFlag.AlignCenter)
  recalculateBtn = QPushButton("Recalculate")
  recalculateBtn.clicked.connect(lambda: app.calculateBackgroundFreelySwim(app, nbImagesForBackgroundCalculation.text(), False, False, True))
  layout.addWidget(recalculateBtn, alignment=Qt.AlignmentFlag.AlignCenter)

  adjustOnWholeVideoCheckbox = QCheckBox("I want to adjust parameters over the entire video, not only on 500 frames at a time.")
  layout.addWidget(adjustOnWholeVideoCheckbox, alignment=Qt.AlignmentFlag.AlignCenter)

  adjustBoutsBtn = QPushButton("Adjust Bouts Detection")
  adjustBoutsBtn.clicked.connect(lambda: app.detectBouts(app, video.getWell(), frameSlider.value(), adjustOnWholeVideoCheckbox.isChecked()))
  layout.addWidget(adjustBoutsBtn, alignment=Qt.AlignmentFlag.AlignCenter)
  layout.addWidget(util.apply_style(QLabel("The aim here is to adjust parameters in order for the red dot on the top left of the image to appear when and only when movement is occurring."), font=QFont("Helvetica", 10)), alignment=Qt.AlignmentFlag.AlignCenter)

  layout.addWidget(util.apply_style(QLabel("Important: Bouts Merging:"), font=QFont("Helvetica", 0)), alignment=Qt.AlignmentFlag.AlignCenter)
  fillGapFrameNb = QLineEdit()
  fillGapFrameNb.setValidator(QIntValidator(fillGapFrameNb))
  fillGapFrameNb.validator().setBottom(0)
  layout.addWidget(fillGapFrameNb, alignment=Qt.AlignmentFlag.AlignCenter)
  updateFillGapBtn = QPushButton("With the box above, update the 'fillGapFrameNb' parameter that controls the distance (in number frames) under which two subsquent bouts are merged into one.")
  updateFillGapBtn.clicked.connect(lambda: app.updateFillGapFrameNb(fillGapFrameNb.text()))
  layout.addWidget(updateFillGapBtn, alignment=Qt.AlignmentFlag.AlignCenter)

  nextBtn = QPushButton("Next")
  nextBtn.clicked.connect(lambda: app.show_frame("FinishConfig"))
  layout.addWidget(nextBtn, alignment=Qt.AlignmentFlag.AlignCenter)
  startPageBtn = util.apply_style(QPushButton("Go to the start page"), background_color=util.LIGHT_CYAN)
  startPageBtn.clicked.connect(lambda: app.show_frame("StartPage"))
  layout.addWidget(startPageBtn, alignment=Qt.AlignmentFlag.AlignCenter)

  _showPage(layout, (img, video), (nextBtn, startPageBtn))
