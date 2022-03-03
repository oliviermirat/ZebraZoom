import cv2

try:
  from PyQt6.QtCore import pyqtSignal, Qt, QEventLoop, QPointF, QRectF, QSize, QSizeF, QTimer
  from PyQt6.QtGui import QColor, QFont, QImage, QPainter, QPixmap, QPolygonF, QTransform
  from PyQt6.QtWidgets import QApplication, QGridLayout, QLabel, QLayout, QHBoxLayout, QPushButton, QSlider, QSpinBox, QToolTip, QVBoxLayout, QWidget
  PYQT6 = True
except ImportError:
  from PyQt5.QtCore import pyqtSignal, Qt, QEventLoop, QPointF, QRectF, QSize, QSizeF, QTimer
  from PyQt5.QtGui import QColor, QFont, QImage, QPainter, QPixmap, QPolygonF, QTransform
  from PyQt5.QtWidgets import QApplication, QGridLayout, QLabel, QLayout, QHBoxLayout, QPushButton, QSlider, QSpinBox, QToolTip, QVBoxLayout, QWidget
  PYQT6 = False

import zebrazoom.videoFormatConversion.zzVideoReading as zzVideoReading


TITLE_FONT = QFont('Helvetica', 18, QFont.Weight.Bold, True)
LIGHT_YELLOW = '#FFFFE0'
LIGHT_CYAN = '#E0FFFF'
LIGHT_GREEN = '#90ee90'
GOLD = '#FFD700'
SPINBOX_STYLESHEET = '''
QSpinBox::down-button  {
  subcontrol-origin: border;
  subcontrol-position: center left;
  height: 20;
  width: 20;
}

QSpinBox::up-button  {
  subcontrol-origin: border;
  subcontrol-position: center right;
  height: 20;
  width: 20;
}'''


def apply_style(widget, **kwargs):
    font = kwargs.pop('font', None)
    if font is not None:
        widget.setFont(font)
    widget.setStyleSheet(';'.join('%s: %s' % (prop.replace('_', '-'), val)  for prop, val in kwargs.items()))
    return widget


def transformCoordinates(fromRect, toRect, point):
  transform = QTransform()
  QTransform.quadToQuad(QPolygonF((fromRect.topLeft(), fromRect.topRight(), fromRect.bottomLeft(), fromRect.bottomRight())),
                        QPolygonF((toRect.topLeft(), toRect.topRight(), toRect.bottomLeft(), toRect.bottomRight())), transform)
  return transform.map(point)


def _dialogClosed(loop, fn):
  def inner(*args, **kwargs):
    loop.exit()
    return fn(*args, **kwargs)
  return inner


def _getButtonsLayout(buttons, loop, dialog=None):
  buttonsLayout = QHBoxLayout()
  buttonsLayout.addStretch()

  def callback(cb):
    if cb is not None:
      cb()
    if dialog is not None:
      dialog.close()
    else:
      loop.exit()

  for text, *args in buttons:
    if len(args) == 1:
      cb, = args
      exitLoop = True
      enabledSignal = None
    elif len(args) == 2:
      cb, exitLoop = args
      enabledSignal = None
    else:
      assert len(args) == 3
      cb, exitLoop, enabledSignal = args
    button = QPushButton(text)
    if enabledSignal is not None:
      button.setEnabled(False)
      enabledSignal.connect(lambda enabled, btn=button: btn.setEnabled(enabled))
    if exitLoop:
      button.clicked.connect(lambda *args, cb=cb: callback(cb))
    else:
      button.clicked.connect(cb)
    buttonsLayout.addWidget(button, alignment=Qt.AlignmentFlag.AlignCenter)
  buttonsLayout.addStretch()
  return buttonsLayout


def showBlockingPage(layout, title=None, buttons=(), dialog=False, labelInfo=None, exitSignals=()):
  loop = QEventLoop()
  for signal in exitSignals:
    signal.connect(lambda *args: loop.exit())
  mainLayout = QVBoxLayout()
  if title is not None:
    mainLayout.addWidget(apply_style(QLabel(title), font=TITLE_FONT), alignment=Qt.AlignmentFlag.AlignCenter)
  mainLayout.addLayout(layout)
  mainLayout.addLayout(_getButtonsLayout(buttons, loop))
  app = QApplication.instance()
  assert app is not None
  temporaryPage = QWidget()
  temporaryPage.setLayout(mainLayout)
  stackedLayout = app.window.centralWidget().layout()
  stackedLayout.addWidget(temporaryPage)
  oldWidget = stackedLayout.currentWidget()
  with app.suppressBusyCursor():
    stackedLayout.setCurrentWidget(temporaryPage)
    if labelInfo is not None:
      img, label = labelInfo
      label.setMinimumSize(1, 1)
      label.show()
      setPixmapFromCv(img, label)
    loop.exec()
    stackedLayout.setCurrentWidget(oldWidget)
  stackedLayout.removeWidget(temporaryPage)


def showDialog(layout, title=None, buttons=(), dialog=False, labelInfo=None, timeout=None):
  dialog = QWidget()
  loop = QEventLoop()
  mainLayout = QVBoxLayout()
  mainLayout.addLayout(layout)
  mainLayout.addLayout(_getButtonsLayout(buttons, loop, dialog=dialog))
  app = QApplication.instance()
  if app is not None:
    app.registerWindow(dialog)
  dialog.setWindowTitle(title)
  dialog.move(0, 0)
  dialog.setWindowModality(Qt.WindowModality.ApplicationModal)
  dialog.setLayout(mainLayout)
  if labelInfo is not None:
    img, label = labelInfo
    height, width = img.shape[:2]
    label.setMinimumSize(width, height)
    layoutSize = mainLayout.totalSizeHint()
    label.setMinimumSize(1, 1)
    extraWidth = layoutSize.width() - width
    extraHeight = layoutSize.height() - height
  else:
    layoutSize = mainLayout.totalSizeHint()
  screenSize = QApplication.primaryScreen().availableSize()
  if layoutSize.width() > screenSize.width() or layoutSize.height() > screenSize.height():
    layoutSize.scale(screenSize, Qt.AspectRatioMode.KeepAspectRatio)
  dialog.setFixedSize(layoutSize)
  dialog.show()
  if labelInfo is not None:
    setPixmapFromCv(*labelInfo, QSize(layoutSize.width() - extraWidth, layoutSize.height() - extraHeight))
  dialog.closeEvent = _dialogClosed(loop, dialog.closeEvent)
  if timeout is not None:
    QTimer.singleShot(timeout, lambda: dialog.close())
    loop.exec()

def _cvToPixmap(img):
  if len(img.shape) == 2:
    height, width = img.shape
    fmt = QImage.Format.Format_Grayscale8
    bytesPerLine = width
  else:
    assert len(img.shape) == 3
    height, width, channels = img.shape
    fmt = QImage.Format.Format_BGR888
    bytesPerLine = width * channels
  return QPixmap.fromImage(QImage(img.data.tobytes(), width, height, bytesPerLine, fmt))


def setPixmapFromCv(img, label, preferredSize=None):
  if not label.isVisible():
    label.setPixmap(_cvToPixmap(img))
    return
  scaling = label.devicePixelRatio() if PYQT6 else label.devicePixelRatioF()
  if label.pixmap() is None or label.pixmap().isNull():
    label.hide()
    label.setPixmap(_cvToPixmap(img))
    label.show()
  if preferredSize is None:
    preferredSize = label.pixmap().size()
  size = preferredSize.scaled(label.size(), Qt.AspectRatioMode.KeepAspectRatio)
  img = cv2.resize(img, (int(size.width() * scaling), int(size.height() * scaling)))
  pixmap = _cvToPixmap(img)
  pixmap.setDevicePixelRatio(scaling)
  label.setPixmap(pixmap)


class SliderWithSpinbox(QWidget):
  valueChanged = pyqtSignal(int)

  def __init__(self, value, minimum, maximum, name=None):
    super().__init__()
    minimum = int(minimum)
    maximum = int(maximum)

    layout = QGridLayout()
    layout.setRowStretch(0, 1)
    layout.setColumnStretch(0, 1)
    layout.setRowStretch(3, 1)
    layout.setColumnStretch(5, 1)
    layout.setVerticalSpacing(0)

    minLabel = QLabel(str(minimum))
    layout.addWidget(minLabel, 1, 1, Qt.AlignmentFlag.AlignLeft)
    if name is not None:
      layout.addWidget(QLabel(name), 1, 2, Qt.AlignmentFlag.AlignCenter)
    maxLabel = QLabel(str(maximum))
    layout.addWidget(maxLabel, 1, 3, Qt.AlignmentFlag.AlignRight)
    slider = QSlider(Qt.Orientation.Horizontal)
    slider.setMinimumWidth(350)
    slider.setRange(minimum, maximum)
    slider.setValue(value)
    layout.addWidget(slider, 2, 1, 1, 3)

    spinbox = QSpinBox()
    spinbox.setStyleSheet(SPINBOX_STYLESHEET)
    spinbox.setMinimumWidth(90)
    spinbox.setRange(minimum, maximum)
    spinbox.setValue(value)
    layout.addWidget(spinbox, 2, 4)

    def spinboxValueChanged():
      value = spinbox.value()
      slider.setValue(value)
      self.valueChanged.emit(value)
    spinbox.valueChanged.connect(spinboxValueChanged)
    slider.valueChanged.connect(lambda: spinbox.setValue(slider.value()))

    layout.setContentsMargins(20, 5, 20, 5)
    self.setLayout(layout)

    self.value = spinbox.value
    self.minimum = spinbox.minimum
    self.maximum = spinbox.maximum
    self.setValue = lambda value: spinbox.setValue(value) or slider.setValue(value)
    self.setMinimum = lambda min_: spinbox.setMinimum(min_) or slider.setMinimum(min_) or minLabel.setText(str(int(min_)))
    self.setMaximum = lambda max_: spinbox.setMaximum(max_) or slider.setMaximum(max_) or maxLabel.setText(str(int(max_)))
    self.setRange = lambda min_, max_: spinbox.setRange(min_, max_) or slider.setRange(min_, max_)
    self.isSliderDown = slider.isSliderDown
    self.sliderWidth = slider.width
    self.setPosition = slider.setSliderPosition


def _chooseFrameLayout(cap, spinboxValues):
  layout = QVBoxLayout()

  video = QLabel()
  layout.addWidget(video, alignment=Qt.AlignmentFlag.AlignCenter)
  layout.setStretch(0, 1)

  sliderWithSpinbox = SliderWithSpinbox(*spinboxValues, name="Frame")

  def valueChanged():
    value = sliderWithSpinbox.value()
    cap.set(1, value)
    ret, frame = cap.read()
    setPixmapFromCv(frame, video)
  sliderWithSpinbox.valueChanged.connect(valueChanged)
  layout.addWidget(sliderWithSpinbox)

  return layout, video, sliderWithSpinbox

def chooseBeginningPage(app, videoPath, title, chooseFrameBtnText, chooseFrameBtnCb, extraButtonInfo=None):
  cap = zzVideoReading.VideoCapture(videoPath)
  cap.set(1, 1)
  ret, frame = cap.read()
  layout, label, valueWidget = _chooseFrameLayout(cap, (1, 0, cap.get(7) - 2))

  chooseEnd = True
  def back():
    nonlocal chooseEnd
    chooseEnd = None
  def trackWholeVideo():
    nonlocal chooseEnd
    chooseEnd = False
  buttonsLayout = QHBoxLayout()
  buttonsLayout.addStretch()
  backBtn = QPushButton("Back")
  backBtn.setObjectName("back")
  buttonsLayout.addWidget(backBtn)
  chooseFrameBtn = QPushButton(chooseFrameBtnText)
  def chooseFrameBtnClicked():
    app.configFile["firstFrame"] = valueWidget.value()
    chooseFrameBtnCb()
  chooseFrameBtn.clicked.connect(chooseFrameBtnClicked)
  buttonsLayout.addWidget(chooseFrameBtn)
  extraBtn = None
  if extraButtonInfo is not None:
    text, cb = extraButtonInfo
    extraBtn = QPushButton(text)
    extraBtn.clicked.connect(cb)
    buttonsLayout.addWidget(extraBtn)
  buttonsLayout.addStretch()
  layout.addLayout(buttonsLayout)
  page = QWidget()
  page.setLayout(layout)
  stackedLayout = app.window.centralWidget().layout()
  stackedLayout.addWidget(page)
  oldWidget = stackedLayout.currentWidget()
  with app.suppressBusyCursor():
    stackedLayout.setCurrentWidget(page)
    label.setMinimumSize(1, 1)
    label.show()
    setPixmapFromCv(frame, label)
  for btn in (backBtn, chooseFrameBtn) + () if extraBtn is None else (extraBtn,):
    btn.clicked.connect(lambda: stackedLayout.removeWidget(page))


def chooseEndPage(app, videoPath, title, chooseFrameBtnText, chooseFrameBtnCb):
  cap = zzVideoReading.VideoCapture(videoPath)
  maximum = cap.get(7) - 2
  cap.set(1, maximum)
  ret, frame = cap.read()
  layout, label, valueWidget = _chooseFrameLayout(cap, (maximum, app.configFile["firstFrame"] + 1, maximum))
  proceed = True
  def back():
    nonlocal proceed
    proceed = False
  buttonsLayout = QHBoxLayout()
  buttonsLayout.addStretch()
  backBtn = QPushButton("Back")
  backBtn.setObjectName("back")
  buttonsLayout.addWidget(backBtn)
  chooseFrameBtn = QPushButton(chooseFrameBtnText)
  def chooseFrameBtnClicked():
    app.configFile["lastFrame"] = valueWidget.value()
    chooseFrameBtnCb()
  chooseFrameBtn.clicked.connect(chooseFrameBtnClicked)
  buttonsLayout.addWidget(chooseFrameBtn)
  buttonsLayout.addStretch()
  layout.addLayout(buttonsLayout)
  page = QWidget()
  page.setLayout(layout)
  stackedLayout = app.window.centralWidget().layout()
  stackedLayout.addWidget(page)
  oldWidget = stackedLayout.currentWidget()
  with app.suppressBusyCursor():
    stackedLayout.setCurrentWidget(page)
    label.setMinimumSize(1, 1)
    label.show()
    setPixmapFromCv(frame, label)
  for btn in (backBtn, chooseFrameBtn):
    btn.clicked.connect(lambda: stackedLayout.removeWidget(page))


class _InteractiveLabelPoint(QLabel):
  pointSelected = pyqtSignal(bool)

  def __init__(self, width, height, selectingRegion):
    super().__init__()
    self._width = width
    self._height = height
    self._point = None
    self._selectingRegion = selectingRegion
    self._currentPosition = None
    self._tooltipShown = False
    if self._selectingRegion:
      self.setMouseTracking(True)

  def mouseMoveEvent(self, evt):
    if self._selectingRegion:
      self._currentPosition = evt.pos()
      self.update()

  def mousePressEvent(self, evt):
    self._point = evt.pos()
    self.update()
    self.pointSelected.emit(True)

  def mouseReleaseEvent(self, evt):
    if self._point is not None and not self._tooltipShown:
      QToolTip.showText(self.mapToGlobal(self._point), "If you aren't satisfied with the selection, click again.", self, self.rect(), 5000)
      self._tooltipShown = True

  def enterEvent(self, evt):
    QApplication.setOverrideCursor(Qt.CursorShape.CrossCursor)

  def leaveEvent(self, evt):
    QApplication.restoreOverrideCursor()
    self._currentPosition = None
    self.update()

  def paintEvent(self, evt):
    super().paintEvent(evt)
    if self._currentPosition is None and self._point is None:
      return
    qp = QPainter()
    qp.begin(self)
    if self._currentPosition is not None:
      qp.setPen(QColor(255, 0, 0))
      qp.drawLine(0, self._currentPosition.y(), self.width(), self._currentPosition.y())
      qp.drawLine(self._currentPosition.x(), 0, self._currentPosition.x(), self.height())
    if self._point is not None:
      qp.setBrush(QColor(255, 0, 0))
      qp.setPen(Qt.PenStyle.NoPen)
      qp.drawEllipse(self._point, 2, 2)
    qp.end()

  def resizeEvent(self, evt):
    super().resizeEvent(evt)
    self._size = self.size()

  def getCoordinates(self):
    if self._point is None:
      return 0, 0
    point = self._point
    if self._size.height() != self._height or self._size.width() != self._width:
      point = transformCoordinates(QRectF(QPointF(0, 0), QSizeF(self._size)), QRectF(QPointF(0, 0), QSizeF(self._width, self._height)), self._point)
    return point.x(), point.y()


def getPoint(frame, title, extraButtons=(), selectingRegion=False, backBtnCb=None, useNext=True):
  height, width = frame.shape[:2]

  layout = QVBoxLayout()

  video = _InteractiveLabelPoint(width, height, selectingRegion)
  extraButtons = tuple((text, lambda: cb(video), exitLoop) for text, cb, exitLoop in extraButtons)
  buttons = (("Back", backBtnCb, True),) if backBtnCb is not None else ()
  buttons += (("Next", None, True, video.pointSelected),) if useNext else ()
  layout.addWidget(video, alignment=Qt.AlignmentFlag.AlignCenter)
  if not useNext:
    video.pointSelected.connect(lambda: QApplication.restoreOverrideCursor())
  showBlockingPage(layout, title=title, buttons=buttons + extraButtons, labelInfo=(frame, video), exitSignals=() if useNext else (video.pointSelected,))
  return video.getCoordinates()


class _InteractiveLabelRect(QLabel):
  regionSelected = pyqtSignal(bool)

  def __init__(self, width, height):
    super().__init__()
    self._width = width
    self._height = height
    self._topLeft = None
    self._currentPosition = None
    self._bottomRight = None
    self._size = None
    self._tooltipShown = False
    self.setMouseTracking(True)

  def mousePressEvent(self, evt):
    if self._topLeft is None or self._bottomRight is not None:
      self._topLeft = evt.pos()
      self._bottomRight = None
      self._currentPosition = None
      self.regionSelected.emit(False)
    else:
      self._bottomRight = evt.pos()
      self.regionSelected.emit(True)
    self.update()

  def mouseReleaseEvent(self, evt):
    if self._bottomRight is not None and not self._tooltipShown:
      QToolTip.showText(self.mapToGlobal(self._bottomRight), "If you aren't satisfied with the selection, click again.", self, self.rect(), 5000)
      self._tooltipShown = True

  def mouseMoveEvent(self, evt):
    self._currentPosition = evt.pos()
    self.update()

  def enterEvent(self, evt):
    QApplication.setOverrideCursor(Qt.CursorShape.CrossCursor)

  def leaveEvent(self, evt):
    QApplication.restoreOverrideCursor()
    self._currentPosition = None
    self.update()

  def paintEvent(self, evt):
    super().paintEvent(evt)
    if self._currentPosition is None and self._topLeft is None:
      return
    qp = QPainter()
    qp.begin(self)
    if self._currentPosition is not None and \
        (self._topLeft is None and self._bottomRight is None or self._bottomRight is not None):
      qp.setPen(QColor(255, 0, 0))
      qp.drawLine(0, self._currentPosition.y(), self.width(), self._currentPosition.y())
      qp.drawLine(self._currentPosition.x(), 0, self._currentPosition.x(), self.height())
    if self._topLeft is not None:
      qp.setPen(QColor(0, 0, 255))
      x = self._topLeft.x()
      y = self._topLeft.y()
      bottomRight = self._bottomRight or self._currentPosition
      if bottomRight is None:
        qp.drawPoint(x, y)
      else:
        width = bottomRight.x() - x
        height = bottomRight.y() - y
        qp.drawRect(x, y, width, height)
    qp.end()

  def resizeEvent(self, evt):
    super().resizeEvent(evt)
    self._size = self.size()

  def getCoordinates(self):
    if self._topLeft is None or self._bottomRight is None:
      return [0, 0], [0, 0]
    points = (self._topLeft, self._bottomRight)
    if self._size.height() != self._height or self._size.width() != self._width:
      points = (transformCoordinates(QRectF(QPointF(0, 0), QSizeF(self._size)), QRectF(QPointF(0, 0), QSizeF(self._width, self._height)), point) for point in points)
    return ([point.x(), point.y()] for point in points)


def getRectangle(frame, title, backBtnCb=None):
  height, width, _ = frame.shape

  layout = QVBoxLayout()

  video = _InteractiveLabelRect(width, height)
  layout.addWidget(video, alignment=Qt.AlignmentFlag.AlignCenter)
  if backBtnCb is not None:
    buttons = (("Back", backBtnCb, True), ("Next", None, True, video.regionSelected))
  else:
    buttons = (("Next", None, True, video.regionSelected),)
  showBlockingPage(layout, title=title, buttons=buttons, labelInfo=(frame, video))

  return video.getCoordinates()


def addToHistory(fn):
  def inner(*args, **kwargs):
    app = QApplication.instance()
    configFileState = app.configFile.copy()
    def restoreState():
      app.configFile.clear()
      app.configFile.update(configFileState)
      del app.configFileHistory[-1:]
      fn(*args, **kwargs)
    app.configFileHistory.append(restoreState)
    return fn(*args, **kwargs)
  return inner
