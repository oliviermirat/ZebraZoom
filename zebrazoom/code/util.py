import sys

import cv2

from PyQt6.QtCore import pyqtSignal, Qt, QEventLoop, QPointF, QRectF, QSize, QSizeF, QTimer
from PyQt6.QtGui import QColor, QFont, QImage, QPainter, QPixmap, QPolygonF, QTransform
from PyQt6.QtWidgets import QApplication, QLabel, QLayout, QHBoxLayout, QPushButton, QSlider, QSpinBox, QToolTip, QVBoxLayout, QWidget

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
    if (font := kwargs.pop('font', None)) is not None:
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


def pageOrDialog(layout, title=None, buttons=(), dialog=False, labelInfo=None, signalsForExit=(), timeout=None):
  loop = QEventLoop()
  for signal in signalsForExit:
    signal.connect(lambda *args, **kwargs: loop.exit())
  mainLayout = QVBoxLayout()
  if title is not None and not dialog:
    mainLayout.addWidget(apply_style(QLabel(title), font=TITLE_FONT), alignment=Qt.AlignmentFlag.AlignCenter)
  mainLayout.addLayout(layout)
  buttonsLayout = QHBoxLayout()
  buttonsLayout.addStretch()

  def callback(cb):
    if cb is not None:
      cb()
    if dialog:
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
    if enabledSignal:
      button.setEnabled(False)
      enabledSignal.connect(lambda enabled: button.setEnabled(enabled))
    if exitLoop:
      button.clicked.connect(lambda *args, cb=cb: callback(cb))
    else:
      button.clicked.connect(cb)
    buttonsLayout.addWidget(button, alignment=Qt.AlignmentFlag.AlignCenter)
  buttonsLayout.addStretch()
  mainLayout.addLayout(buttonsLayout)

  app = QApplication.instance()
  if not dialog:
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
  else:
    dialog = QWidget()
    if app is not None:
      app.registerWindow(dialog)
    else:
      app = QApplication(sys.argv)
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
      pixmapSize = label.pixmap().size()
      extraWidth = layoutSize.width() - width
      extraHeight = layoutSize.height() - height
    else:
      layoutSize = mainLayout.totalSizeHint()
    screenSize = QApplication.instance().primaryScreen().availableSize()
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
  scaling = label.devicePixelRatio()
  if label.pixmap().isNull():
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

  def __init__(self, value, minimum, maximum):
    super().__init__()

    layout = QHBoxLayout()
    layout.addStretch()

    slider = QSlider(Qt.Orientation.Horizontal)
    slider.setMinimumWidth(350)
    slider.setRange(minimum, maximum)
    slider.setValue(value)
    layout.addWidget(slider, alignment=Qt.AlignmentFlag.AlignCenter)

    spinbox = QSpinBox()
    spinbox.setStyleSheet(SPINBOX_STYLESHEET)
    spinbox.setMinimumWidth(70)
    spinbox.setRange(minimum, maximum)
    spinbox.setValue(value)
    layout.addWidget(spinbox, alignment=Qt.AlignmentFlag.AlignCenter)
    layout.addStretch()

    def spinboxValueChanged():
      value = spinbox.value()
      slider.setValue(value)
      self.valueChanged.emit(value)
    spinbox.valueChanged.connect(spinboxValueChanged)
    slider.valueChanged.connect(lambda: spinbox.setValue(slider.value()))

    self.setLayout(layout)

    self.value = spinbox.value
    self.setMinimum = lambda min_: spinbox.setMinimum(min_) or slider.setMinimum(min_)
    self.setMaximum = lambda max_: spinbox.setMaximum(max_) or slider.setMaximum(max_)
    self.setRange = lambda min_, max_: spinbox.setRange(min_, max_) or slider.setRange(min_, max_)


def _chooseFrameLayout(cap, spinboxValues):
  layout = QVBoxLayout()

  video = QLabel()
  layout.addWidget(video, alignment=Qt.AlignmentFlag.AlignCenter)
  layout.addWidget(QLabel("Frame:"), alignment=Qt.AlignmentFlag.AlignCenter)

  sliderWithSpinbox = SliderWithSpinbox(*spinboxValues)

  def valueChanged():
    value = sliderWithSpinbox.value()
    cap.set(1, value)
    ret, frame = cap.read()
    setPixmapFromCv(frame, video)
  sliderWithSpinbox.valueChanged.connect(valueChanged)
  layout.addWidget(sliderWithSpinbox)

  return layout, video, sliderWithSpinbox

def chooseBeginning(app, videoPath, title, chooseFrameBtnText, allowWholeVideo=False):
  cap = zzVideoReading.VideoCapture(videoPath)
  cap.set(1, 1)
  ret, frame = cap.read()
  layout, label, valueWidget = _chooseFrameLayout(cap, (1, 0, cap.get(7) - 2))
  buttons = [(chooseFrameBtnText, lambda: app.configFile.update({"firstFrame": valueWidget.value()}))]

  wholeVideo = False
  def trackWholeVideo():
    nonlocal wholeVideo
    wholeVideo = True

  if allowWholeVideo:
    buttons.append(("I want the tracking to run on the entire video!", trackWholeVideo))
  pageOrDialog(layout, title=title, buttons=buttons, dialog=False, labelInfo=(frame, label))
  return not wholeVideo


def chooseEnd(app, videoPath, title, chooseFrameBtnText):
  cap = zzVideoReading.VideoCapture(videoPath)
  maximum = cap.get(7) - 2
  cap.set(1, maximum)
  ret, frame = cap.read()
  layout, label, valueWidget = _chooseFrameLayout(cap, (maximum, app.configFile["firstFrame"] + 1, maximum))
  buttons = [(chooseFrameBtnText, lambda: app.configFile.update({"lastFrame": valueWidget.value()}))]
  pageOrDialog(layout, title=title, buttons=buttons, dialog=False, labelInfo=(frame, label))


class _InteractiveLabelPoint(QLabel):
  pointSelected = pyqtSignal(bool)

  def __init__(self, width, height):
    super().__init__()
    self._width = width
    self._height = height
    self._point = None

  def mousePressEvent(self, evt):
    self._point = evt.pos()
    self.update()
    self.pointSelected.emit(True)

  def mouseReleaseEvent(self, evt):
    if self._point is not None:
      QToolTip.showText(self.mapToGlobal(self._point), "If you aren't satisfied with the selection, click again.", msecShowTime=2000)

  def enterEvent(self, evt):
    QApplication.setOverrideCursor(Qt.CursorShape.CrossCursor)

  def leaveEvent(self, evt):
    QApplication.restoreOverrideCursor()

  def paintEvent(self, evt):
    super().paintEvent(evt)
    if self._point is None:
      return
    qp = QPainter()
    qp.begin(self)
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


def getPoint(frame, title, extraButtons=()):
  height, width = frame.shape[:2]

  layout = QVBoxLayout()

  video = _InteractiveLabelPoint(width, height)
  extraButtons = tuple((text, lambda: cb(video), exitLoop, video.pointSelected) for text, cb, exitLoop in extraButtons)
  layout.addWidget(video, alignment=Qt.AlignmentFlag.AlignCenter)
  pageOrDialog(layout, title=title, buttons=(("Next", None),) + extraButtons, labelInfo=(frame, video))

  return video.getCoordinates()


class _InteractiveLabelRect(QLabel):
  regionSelected = pyqtSignal(bool)

  def __init__(self, width, height):
    super().__init__()
    self._width = width
    self._height = height
    self._topLeft = None
    self._tmpBottomRight = None
    self._bottomRight = None
    self._size = None
    self.setMouseTracking(True)

  def mousePressEvent(self, evt):
    if self._topLeft is None or self._bottomRight is not None:
      self._topLeft = evt.pos()
      self._bottomRight = None
      self._tmpBottomRight = None
      self.regionSelected.emit(False)
    else:
      self._bottomRight = evt.pos()
      self.regionSelected.emit(True)
    self.update()

  def mouseReleaseEvent(self, evt):
    if self._bottomRight is not None:
      QToolTip.showText(self.mapToGlobal(self._bottomRight), "If you aren't satisfied with the selection, click again.", msecShowTime=2000)

  def mouseMoveEvent(self, evt):
    if self._topLeft is None or self._bottomRight is not None or self._tmpBottomRight == evt.pos():
      return
    self._tmpBottomRight = evt.pos()
    self.update()

  def enterEvent(self, evt):
    QApplication.setOverrideCursor(Qt.CursorShape.CrossCursor)

  def leaveEvent(self, evt):
    QApplication.restoreOverrideCursor()
    self._tmpBottomRight = None
    self.update()

  def paintEvent(self, evt):
    super().paintEvent(evt)
    if self._topLeft is None:
      return
    qp = QPainter()
    qp.begin(self)
    qp.setPen(QColor(0, 0, 255))
    x = self._topLeft.x()
    y = self._topLeft.y()
    bottomRight = self._bottomRight or self._tmpBottomRight
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


def getRectangle(frame, title):
  height, width, _ = frame.shape

  layout = QVBoxLayout()

  video = _InteractiveLabelRect(width, height)
  layout.addWidget(video, alignment=Qt.AlignmentFlag.AlignCenter)
  pageOrDialog(layout, title=title, buttons=(("Next", None, True, video.regionSelected),), labelInfo=(frame, video))

  return video.getCoordinates()