import math
import sys

import numpy as np

import cv2

from PyQt5.QtCore import pyqtSignal, Qt, QAbstractAnimation, QAbstractEventDispatcher, QEventLoop, QLine, QParallelAnimationGroup, QPoint, QPointF, QPropertyAnimation, QRect, QRectF, QSize, QSizeF, QStandardPaths, QTimer
from PyQt5.QtGui import QBrush, QColor, QFont, QImage, QPainter, QPen, QPixmap, QPolygon, QPolygonF, QTransform
from PyQt5.QtWidgets import QApplication, QComboBox, QDoubleSpinBox, QFrame, QGraphicsPixmapItem, QGraphicsScene, QGraphicsView, QGridLayout, QLabel, QLayout, QHBoxLayout, QPushButton, QScrollArea, QSizePolicy, QSlider, QSpinBox, QSplitter, QSplitterHandle, QToolButton, QToolTip, QVBoxLayout, QWidget
PYQT6 = False

import zebrazoom.videoFormatConversion.zzVideoReading as zzVideoReading


VIDEO_EXTENSIONS = {'.264', '.3g2', '.3gp', '.3gp2', '.3gpp', '.3gpp2', '.3mm', '.3p2', '.60d', '.787', '.89', '.aaf', '.aec', '.aep', '.aepx', '.aet', '.aetx', '.ajp',
                    '.ale', '.am', '.amc', '.amv', '.amx', '.anim', '.aqt', '.arcut', '.arf', '.asf', '.asx', '.avb', '.avc', '.avd', '.avi', '.avp', '.avs', '.avs',
                    '.avv', '.axm', '.bdm', '.bdmv', '.bdt2', '.bdt3', '.bik', '.bix', '.bmk', '.bnp', '.box', '.bs4', '.bsf', '.bvr', '.byu', '.camproj', '.camrec',
                    '.camv', '.ced', '.cel', '.cine', '.cip', '.clpi', '.cmmp', '.cmmtpl', '.cmproj', '.cmrec', '.cpi', '.cst', '.cvc', '.cx3', '.d2v', '.d3v', '.dat',
                    '.dav', '.dce', '.dck', '.dcr', '.dcr', '.ddat', '.dif', '.dir', '.divx', '.dlx', '.dmb', '.dmsd', '.dmsd3d', '.dmsm', '.dmsm3d', '.dmss', '.dmx', '.dnc',
                    '.dpa', '.dpg', '.dream', '.dsy', '.dv', '.dv-avi', '.dv4', '.dvdmedia', '.dvr', '.dvr-ms', '.dvx', '.dxr', '.dzm', '.dzp', '.dzt', '.edl', '.evo', '.eye',
                    '.ezt', '.f4p', '.f4v', '.fbr', '.fbr', '.fbz', '.fcp', '.fcproject', '.ffd', '.flc', '.flh', '.fli', '.flv', '.flx', '.gfp', '.gl', '.gom', '.grasp',
                    '.gts', '.gvi', '.gvp', '.h264', '.hdmov', '.hkm', '.ifo', '.imovieproj', '.imovieproject', '.ircp', '.irf', '.ism', '.ismc', '.ismv', '.iva', '.ivf',
                    '.ivr', '.ivs', '.izz', '.izzy', '.jss', '.jts', '.jtv', '.k3g', '.kmv', '.ktn', '.lrec', '.lsf', '.lsx', '.m15', '.m1pg', '.m1v', '.m21', '.m21', '.m2a',
                    '.m2p', '.m2t', '.m2ts', '.m2v', '.m4e', '.m4u', '.m4v', '.m75', '.mani', '.meta', '.mgv', '.mj2', '.mjp', '.mjpg', '.mk3d', '.mkv', '.mmv', '.mnv',
                    '.mob', '.mod', '.modd', '.moff', '.moi', '.moov', '.mov', '.movie', '.mp21', '.mp21', '.mp2v', '.mp4', '.mp4v', '.mpe', '.mpeg', '.mpeg1', '.mpeg4',
                    '.mpf', '.mpg', '.mpg2', '.mpgindex', '.mpl', '.mpl', '.mpls', '.mpsub', '.mpv', '.mpv2', '.mqv', '.msdvd', '.mse', '.msh', '.mswmm', '.mts', '.mtv',
                    '.mvb', '.mvc', '.mvd', '.mve', '.mvex', '.mvp', '.mvp', '.mvy', '.mxf', '.mxv', '.mys', '.ncor', '.nsv', '.nut', '.nuv', '.nvc', '.ogm', '.ogv', '.ogx',
                    '.osp', '.otrkey', '.pac', '.par', '.pds', '.pgi', '.photoshow', '.piv', '.pjs', '.playlist', '.plproj', '.pmf', '.pmv', '.pns', '.ppj', '.prel', '.pro',
                    '.prproj', '.prtl', '.psb', '.psh', '.pssd', '.pva', '.pvr', '.pxv', '.qt', '.qtch', '.qtindex', '.qtl', '.qtm', '.qtz', '.r3d', '.rcd', '.rcproject',
                    '.rdb', '.rec', '.rm', '.rmd', '.rmd', '.rmp', '.rms', '.rmv', '.rmvb', '.roq', '.rp', '.rsx', '.rts', '.rts', '.rum', '.rv', '.rvid', '.rvl', '.sbk',
                    '.sbt', '.scc', '.scm', '.scm', '.scn', '.screenflow', '.sec', '.sedprj', '.seq', '.sfd', '.sfvidcap', '.siv', '.smi', '.smi', '.smil', '.smk', '.sml',
                    '.smv', '.spl', '.sqz', '.srt', '.ssf', '.ssm', '.stl', '.str', '.stx', '.svi', '.swf', '.swi', '.swt', '.tda3mt', '.tdx', '.thp', '.tivo', '.tix',
                    '.tod', '.tp', '.tp0', '.tpd', '.tpr', '.trp', '.ts', '.tsp', '.ttxt', '.tvs', '.usf', '.usm', '.vc1', '.vcpf', '.vcr', '.vcv', '.vdo', '.vdr', '.vdx',
                    '.veg','.vem', '.vep', '.vf', '.vft', '.vfw', '.vfz', '.vgz', '.vid', '.video', '.viewlet', '.viv', '.vivo', '.vlab', '.vob', '.vp3', '.vp6', '.vp7',
                    '.vpj', '.vro', '.vs4', '.vse', '.vsp', '.w32', '.wcp', '.webm', '.wlmp', '.wm', '.wmd', '.wmmp', '.wmv', '.wmx', '.wot', '.wp3', '.wpl', '.wtv', '.wve',
                    '.wvx', '.xej', '.xel', '.xesc', '.xfl', '.xlmv', '.xmv', '.xvid', '.y4m', '.yog', '.yuv', '.zeg', '.zm1', '.zm2', '.zm3', '.zmv', '.tif', 'tiff', '.bias'}


PRETTY_PARAMETER_NAMES = {
  'frameGapComparision': 'Compare frame n with frame n+?',
  'thresForDetectMovementWithRawVideo': 'Threshold applied on frame n+? minus frame n',
  'halfDiameterRoiBoutDetect': 'Size of sub-frame used for the comparison',
  'minNbPixelForDetectMovementWithRawVideo': 'Minimum number of white pixels in frame n+? minus frame n for bout detection',
  'headEmbededAutoSet_BackgroundExtractionOption': 'Background Extraction',
  'overwriteFirstStepValue': 'Minimum number of pixels between subsequent points',
  'overwriteLastStepValue': 'Maximum number of pixels between subsequent points',
  'overwriteHeadEmbededParamGaussianBlur': 'Gaussian blur applied on the image',
  'steps': 'Segment length between previous and next point: number of options',
  'thetaDiffAccept': 'Maximum authorized angle difference between two subsequent segments in the first portion of the tail (in radians)',
  'thetaDiffAcceptAfterAuthorizedRelativeLengthTailEnd': 'Maximum authorized angle difference between two subsequent segments in the second portion of the tail  (in radians)',
  'thetaDiffAcceptAfterAuthorizedRelativeLengthTailEnd2': 'Maximum authorized angle difference between two subsequent segments in the third portion of the tail  (in radians)',
  'nbList': 'Number of "candidates" points considered for next point along the tail in the first portion of the tail',
  'nbListAfterAuthorizedRelativeLengthTailEnd': 'Number of "candidates" points considered for next point along the tail in the second portion of the tail',
  'nbListAfterAuthorizedRelativeLengthTailEnd2': 'Number of "candidates" points considered for next point along the tail in the third portion of the tail',
  'authorizedRelativeLengthTailEnd': 'Cut off relative location between first and second tail segment (between 0 and 1)',
  'authorizedRelativeLengthTailEnd2': 'Cut off relative location between second and third tail segment (between 0 and 1)',
  'maximumMedianValueOfAllPointsAlongTheTail': 'Maximum median pixel value of all points along the tail in order for the tail tracking to be accepted',
  'minimumHeadPixelValue': 'Maximum pixel value authorized for a point to be considered as the head of the animal',
  'nbTailPoints': 'Number of points along the tail in the output data',
}

TITLE_FONT = QFont('Helvetica', 18, QFont.Weight.Bold, True)
LIGHT_YELLOW = '#FFFFE0'
LIGHT_CYAN = '#E0FFFF'
LIGHT_GREEN = '#90ee90'
GOLD = '#FFD700'
DEFAULT_BUTTON_COLOR = LIGHT_GREEN
SPINBOX_STYLESHEET = '''
QSpinBox::down-button {
  subcontrol-origin: border;
  subcontrol-position: center left;
  height: 20;
  width: 20;
}

QSpinBox::up-button {
  subcontrol-origin: border;
  subcontrol-position: center right;
  height: 20;
  width: 20;
}

QDoubleSpinBox::down-button {
  subcontrol-origin: border;
  subcontrol-position: center left;
  height: 20;
  width: 20;
}

QDoubleSpinBox::up-button {
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
    enabledSignal = None
    color = None
    if len(args) == 1:
      cb, = args
      exitLoop = True
    elif len(args) == 2:
      cb, exitLoop = args
    elif len(args) == 3:
      cb, exitLoop, enabledSignal = args
    else:
      assert len(args) == 4
      cb, exitLoop, enabledSignal, color = args
    button = QPushButton(text) if color is None else apply_style(QPushButton(text), background_color=color)
    if enabledSignal is not None:
      button.setEnabled(False)
      enabledSignal.connect(lambda enabled, btn=button: btn.setEnabled(bool(enabled)))
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
    titleLabel = apply_style(QLabel(title), font=TITLE_FONT)
    titleLabel.setMinimumSize(1, 1)
    titleLabel.resizeEvent = lambda evt: titleLabel.setMinimumWidth(evt.size().width()) or titleLabel.setWordWrap(evt.size().width() <= titleLabel.sizeHint().width())
    mainLayout.addWidget(titleLabel, alignment=Qt.AlignmentFlag.AlignCenter)
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
      if len(labelInfo) == 2:
        img, label = labelInfo
        zoomable = False
      else:
        assert len(labelInfo) == 3
        img, label, zoomable = labelInfo
      label.setMinimumSize(1, 1)
      label.show()
      setPixmapFromCv(img, label, zoomable=zoomable)
    loop.exec()
    stackedLayout.setCurrentWidget(oldWidget)
  stackedLayout.removeWidget(temporaryPage)


def showInProgressPage(text):
  def decorator(fn):
    def inner(*args, **kwargs):
      app = QApplication.instance()
      layout = QVBoxLayout()
      layout.addWidget(apply_style(QLabel("%s in progress..." % text), font=TITLE_FONT), alignment=Qt.AlignmentFlag.AlignCenter)
      temporaryPage = QWidget()
      temporaryPage.setLayout(layout)
      stackedLayout = app.window.centralWidget().layout()
      oldWidget = stackedLayout.currentWidget()
      stackedLayout.addWidget(temporaryPage)
      stackedLayout.setCurrentWidget(temporaryPage)
      QAbstractEventDispatcher.instance().processEvents(QEventLoop.ProcessEventsFlag.AllEvents)  # XXX: this is ugly, but required to make sure the page is displayed before the function is executed, since the GUI will get blocked while the function is executing
      try:
        retval = fn(*args, **kwargs)  # XXX: GUI and non-GUI parts are still mixed so this function is expected to set the new page
      finally:
        stackedLayout.removeWidget(temporaryPage)
      return retval
    return inner
  return decorator


def showDialog(layout, title=None, buttons=(), labelInfo=None, timeout=None, exitSignals=(), focusWidgets=None):
  dialog = QWidget()
  for signal in exitSignals:
    signal.connect(lambda *args: dialog.close())
  loop = QEventLoop()
  mainLayout = QVBoxLayout()
  mainLayout.addLayout(layout)
  if buttons:
    mainLayout.addLayout(_getButtonsLayout(buttons, loop, dialog=dialog))
  app = QApplication.instance()
  if hasattr(app, 'registerWindow'):
    app.registerWindow(dialog)
  dialog.setWindowTitle(title)
  dialog.move(0, 0)
  dialog.setWindowModality(Qt.WindowModality.ApplicationModal)
  dialog.setLayout(mainLayout)
  screenSize = QApplication.primaryScreen().availableSize()
  if hasattr(app, 'window'):
    screenSize -= app.window.frameSize() - app.window.size()
  if labelInfo is not None:
    if len(labelInfo) == 2:
      img, label = labelInfo
      zoomable = False
    else:
      assert len(labelInfo) == 3
      img, label, zoomable = labelInfo
    height, width = img.shape[:2]
    label.setMinimumSize(width, height)
    layoutSize = mainLayout.totalSizeHint()
    widthDiff = layoutSize.width() - screenSize.width()
    heightDiff = layoutSize.height() - screenSize.height()
    if widthDiff > 0 or heightDiff > 0:
      dialog.adjustSize()
      labelSize = label.size()
      label.setFixedSize(labelSize.scaled(labelSize - QSize(widthDiff if widthDiff > 0 else 0, heightDiff if heightDiff > 0 else 0), Qt.AspectRatioMode.KeepAspectRatio))
      dialog.adjustSize()
      layoutSize = mainLayout.totalSizeHint()
      label.setMinimumSize(1, 1)
      label.setMaximumSize(screenSize)
  else:
    layoutSize = mainLayout.totalSizeHint()
    if layoutSize.width() > screenSize.width() or layoutSize.height() > screenSize.height():
      layoutSize.scale(screenSize, Qt.AspectRatioMode.KeepAspectRatio)
  dialog.setFixedSize(layoutSize)
  dialog.show()
  if labelInfo is not None:
    if len(labelInfo) == 2:
      img, label = labelInfo
      zoomable = False
    else:
      assert len(labelInfo) == 3
      img, label, zoomable = labelInfo
    setPixmapFromCv(img, label, preferredSize=QSize(width, height).scaled(label.size(), Qt.AspectRatioMode.KeepAspectRatio), zoomable=zoomable)
  dialog.closeEvent = _dialogClosed(loop, dialog.closeEvent)
  if timeout is not None:
    QTimer.singleShot(timeout, lambda: dialog.close())
  if focusWidgets is not None:
    for child in dialog.findChildren(QWidget):
      if child in focusWidgets or any(child.isAncestorOf(widget) for widget in focusWidgets) or any(widget.isAncestorOf(child) for widget in focusWidgets):
        continue
      child.setFocusPolicy(Qt.FocusPolicy.NoFocus)
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


class _ZoomableImage(QGraphicsView):
  def __init__(self, parent=None):
    super().__init__(parent)
    self._zoom = 0
    self._scene = QGraphicsScene(self)
    self._pixmap = QGraphicsPixmapItem()
    self._scene.addItem(self._pixmap)
    self.setScene(self._scene)
    self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
    self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
    self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
    self.setFrameShape(QFrame.Shape.NoFrame)
    self._dragging = False
    self._tooltipShown = False

  def fitInView(self):
    rect = QRectF(self._pixmap.pixmap().rect())
    self.setSceneRect(rect)
    unity = self.transform().mapRect(QRectF(0, 0, 1, 1))
    self.scale(1 / unity.width(), 1 / unity.height())
    viewrect = self.viewport().rect()
    scenerect = self.transform().mapRect(rect)
    factor = min(viewrect.width() / scenerect.width(),
                 viewrect.height() / scenerect.height())
    self.scale(factor, factor)
    self._zoom = 0

  def setPixmap(self, pixmap):
    self._zoom = 0
    self.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
    self._pixmap.setPixmap(pixmap)
    self.fitInView()

  def _update(self, scaleFactor):
    if self._zoom > 0:
      self.scale(scaleFactor, scaleFactor)
    elif self._zoom == 0:
      self.fitInView()
    else:
      self._zoom = 0

  def wheelEvent(self, evt):
    if evt.angleDelta().y() > 0:
      self._zoom += 1
      self._update(1.25)
    else:
      self._zoom -= 1
      self._update(0.8)

  def keyPressEvent(self, evt):
    if evt.modifiers() & Qt.KeyboardModifier.ControlModifier:
      if evt.key() == Qt.Key.Key_Plus:
        self._zoom += 1
        self._update(1.25)
        return
      if evt.key() == Qt.Key.Key_Minus:
        self._zoom -= 1
        self._update(0.8)
        return
    super().keyPressEvent(evt)

  def mouseMoveEvent(self, evt):
    if evt.buttons() == Qt.MouseButton.LeftButton and not self._dragging:
      self._dragging = True
      QApplication.setOverrideCursor(Qt.CursorShape.ClosedHandCursor)
    super().mouseMoveEvent(evt)

  def enterEvent(self, evt):
    QApplication.setOverrideCursor(Qt.CursorShape.CrossCursor)
    super().enterEvent(evt)

  def leaveEvent(self, evt):
    QApplication.restoreOverrideCursor()
    super().leaveEvent(evt)


class _ZoomableImagePoint(_ZoomableImage):
  pointSelected = pyqtSignal(QPoint)
  proceed = pyqtSignal()

  def __init__(self, parent=None):
    super().__init__(parent)
    self._point = None

  def keyPressEvent(self, evt):
    if self._point is not None and (evt.key() == Qt.Key.Key_Enter or evt.key() == Qt.Key.Key_Return):
      self.proceed.emit()
      return
    super().keyPressEvent(evt)

  def mouseReleaseEvent(self, evt):
    if not self._dragging:
      if self._pixmap.isUnderMouse():
        self._point = self.mapToScene(evt.pos()).toPoint()
        self.viewport().update()
        self.pointSelected.emit(self._point)
        if not self._tooltipShown and self._point is not None:
          QToolTip.showText(self.mapToGlobal(self._point), "If you aren't satisfied with the selection, click again.", self, self.rect(), 5000)
          self._tooltipShown = True
    else:
      self._dragging = False
      QApplication.restoreOverrideCursor()
    super().mouseReleaseEvent(evt)

  def paintEvent(self, evt):
    super().paintEvent(evt)
    if self._point is None:
      return
    qp = QPainter(self.viewport())
    if self._point is not None:
      qp.setBrush(QColor(255, 0, 0))
      qp.setPen(Qt.PenStyle.NoPen)
      qp.drawEllipse(self.mapFromScene(QPointF(self._point)), 2, 2)
    qp.end()


class _ZoomableImageCircle(_ZoomableImage):
  circleSelected = pyqtSignal(bool)

  def __init__(self):
    super().__init__()
    self._center = None
    self._currentPosition = None
    self._borderPoint = None
    self.viewport().setMouseTracking(True)

  def mouseReleaseEvent(self, evt):
    if not self._dragging:
      if self._pixmap.isUnderMouse():
        if self._center is None or self._borderPoint is not None:
          self._center = self.mapToScene(evt.pos()).toPoint()
          self._borderPoint = None
          self._currentPosition = None
          self.circleSelected.emit(False)
        else:
          self._borderPoint = self.mapToScene(evt.pos()).toPoint()
          self.circleSelected.emit(True)
        self.viewport().update()
        if not self._tooltipShown and self._center is not None and self._borderPoint is not None:
          QToolTip.showText(self.mapToGlobal(self._center), "If you aren't satisfied with the selection, click again.", self, self.rect(), 5000)
          self._tooltipShown = True
    else:
      self._dragging = False
      QApplication.restoreOverrideCursor()
    super().mouseReleaseEvent(evt)

  def mouseMoveEvent(self, evt):
    super().mouseMoveEvent(evt)
    if not self._dragging:
      self._currentPosition = self.mapToScene(evt.pos()).toPoint()
      self.viewport().update()

  def leaveEvent(self, evt):
    self._currentPosition = None
    self.viewport().update()
    super().leaveEvent(evt)

  def paintEvent(self, evt):
    super().paintEvent(evt)
    if self._currentPosition is None and self._center is None:
      return
    qp = QPainter(self.viewport())
    if self._center is not None:
      qp.setBrush(QColor(255, 0, 0))
      qp.setPen(Qt.PenStyle.NoPen)
      borderPoint = self._borderPoint if self._borderPoint is not None else self._currentPosition if self._currentPosition is not None else None
      mappedCenter = self.mapFromScene(self._center)
      qp.drawEllipse(mappedCenter, 2, 2)
      if borderPoint is not None:
        delta = self.mapFromScene(borderPoint) - mappedCenter
        radius = int(math.sqrt(delta.x() * delta.x() + delta.y() * delta.y()))
        qp.setBrush(Qt.BrushStyle.NoBrush)
        qp.setPen(QColor(0, 0, 255))
        qp.drawEllipse(mappedCenter, radius, radius)
    qp.end()


def setPixmapFromCv(img, label, preferredSize=None, zoomable=False):
  if img is None:
    img = np.zeros((1, 1, 3), np.uint8)
  originalPixmap = _cvToPixmap(img)
  if not label.isVisible():
    label.setPixmap(originalPixmap)
    return
  scaling = label.devicePixelRatio() if PYQT6 else label.devicePixelRatioF()
  if label.pixmap() is None or label.pixmap().isNull():
    label.hide()
    label.setPixmap(originalPixmap)
    label.show()
  if preferredSize is None:
    preferredSize = originalPixmap.size()
  labelSize = label.size()
  if preferredSize.height() > labelSize.height() or preferredSize.width() > labelSize.width():
    size = preferredSize.scaled(labelSize, Qt.AspectRatioMode.KeepAspectRatio)
  else:
    size = preferredSize
  if not zoomable:
    img = cv2.resize(img, (int(size.width() * scaling), int(size.height() * scaling)))
    pixmap = _cvToPixmap(img)
    pixmap.setDevicePixelRatio(scaling)
    label.setPixmap(pixmap)
  else:
    label.hide()
    image = _ZoomableImagePoint() if not isinstance(label, _InteractiveLabelCircle) else _ZoomableImageCircle()
    image.sizeHint = lambda: size
    image.setMaximumSize(size)
    image.viewport().setFixedSize(size)
    image.setPixmap(originalPixmap)
    label.parentWidget().layout().replaceWidget(label, image)
    image.setFocus()
    if hasattr(image, "pointSelected"):
      def pointSelected(point):
        label.pointSelected.emit(point)
        label.getCoordinates = lambda: (point.x(), point.y())
      image.pointSelected.connect(pointSelected)
      image.proceed.connect(label.proceed.emit)
    if hasattr(image, "circleSelected"):
      def circleSelected(selected):
        label.circleSelected.emit(selected)
      image.circleSelected.connect(circleSelected)
      def calculateRadius():
        if image._borderPoint is None or image._center is None:
          return None, None
        delta = image._borderPoint - image._center
        return image._center, int(math.sqrt(delta.x() * delta.x() + delta.y() * delta.y()))
      label.getInfo = calculateRadius


class _TemporaryZoomableImagePoint(_ZoomableImage):
  pointSelected = pyqtSignal(QPoint)
  abort = pyqtSignal()

  def __init__(self, parent=None, basePoint=None):
    super().__init__(parent)
    self._point = None
    self._basePoint = None if basePoint is None else QPoint(*map(int, basePoint))
    self._currentPosition = None
    self.setMouseTracking(True)

  def keyPressEvent(self, evt):
    if evt.key() == Qt.Key.Key_Escape:
      self.abort.emit()
      return
    super().keyPressEvent(evt)

  def mouseMoveEvent(self, evt):
    self._currentPosition = self.mapToScene(evt.pos()).toPoint()
    self.viewport().update()
    super().mouseMoveEvent(evt)

  def mouseReleaseEvent(self, evt):
    if not self._dragging:
      if self._pixmap.isUnderMouse():
        self._point = self.mapToScene(evt.pos()).toPoint()
        self.viewport().update()
        self.pointSelected.emit(self._point)
    else:
      self._dragging = False
      QApplication.restoreOverrideCursor()
    super().mouseReleaseEvent(evt)

  def leaveEvent(self, evt):
    QApplication.restoreOverrideCursor()
    self._currentPosition = None
    self.viewport().update()
    super().leaveEvent(evt)

  def paintEvent(self, evt):
    super().paintEvent(evt)
    if self._basePoint is None or self._currentPosition is None:
      return
    qp = QPainter(self.viewport())
    qp.setPen(QColor(255, 0, 0))
    qp.drawLine(self.mapFromScene(self._basePoint), self.mapFromScene(QPointF(self._currentPosition)))
    qp.end()

  def getCoordinates(self):
    return None if self._point is None else (self._point.x(), self._point.y()) if self._basePoint is None else ((self._basePoint.x(), self._basePoint.y()), (self._point.x(), self._point.y()))


def getPointOnFrame(frame, label, basePoint=None, exitSignals=()):
  label.hide()
  image = _TemporaryZoomableImagePoint(basePoint=basePoint)
  labelSize = label.size()
  pixmap = _cvToPixmap(frame)
  size = pixmap.size()
  if size.height() > labelSize.height() or size.width() > labelSize.width():
    size = size.scaled(labelSize, Qt.AspectRatioMode.KeepAspectRatio)
  widthDiff = labelSize.width() - size.width()
  heightDiff = labelSize.height() - size.height()
  horizontalMargin = widthDiff // 2
  verticalMargin = heightDiff // 2
  image.setViewportMargins(horizontalMargin + widthDiff % 2, verticalMargin + heightDiff % 2, horizontalMargin, verticalMargin)
  image.sizeHint = lambda: labelSize
  image.setMaximumSize(labelSize)
  image.viewport().setFixedSize(size)
  image.setPixmap(pixmap)
  label.parentWidget().layout().replaceWidget(label, image)
  image.setFocus()
  loop = QEventLoop()
  for signal in exitSignals:
    signal.connect(lambda *args: loop.exit())
  image.pointSelected.connect(lambda point: loop.exit())
  image.abort.connect(loop.exit)
  loop.exec()
  image.hide()
  image.parentWidget().layout().replaceWidget(image, label)
  label.show()
  return image.getCoordinates()


class _DoubleSlider(QSlider):
  _DECIMALS = 2

  def __init__(self, *args, **kargs):
    super().__init__( *args, **kargs)
    self._factor = 10 ** self._DECIMALS

  def value(self):
    return super().value() / self._factor

  def setMinimum(self, value):
    return super().setMinimum(int(value * self._factor))

  def setMaximum(self, value):
    return super().setMaximum(int(value * self._factor))

  def setRange(self, minimum, maximum):
    return super().setRange(int(minimum * self._factor), int(maximum * self._factor))

  def setValue(self, value):
    super().setValue(int(value * self._factor))


class SliderWithSpinbox(QWidget):
  valueChanged = pyqtSignal(int)
  choiceChanged = pyqtSignal(int)

  def __init__(self, value, minimum, maximum, name=None, double=False, choices=None):
    super().__init__()
    type_ = int if not double else float
    value = type_(value)
    minimum = type_(minimum)
    maximum = type_(maximum)
    formatMin = lambda x: (math.floor(x) if type_ is float else int(x))
    formatMax = lambda x: (math.ceil(x) if type_ is float else int(x))

    layout = QGridLayout()
    layout.setRowStretch(0, 1)
    layout.setColumnStretch(0, 1)
    layout.setRowStretch(3, 1)
    layout.setColumnStretch(5, 1)
    layout.setVerticalSpacing(0)

    minLabel = QLabel(str(formatMin(minimum)))
    layout.addWidget(minLabel, 1, 1, Qt.AlignmentFlag.AlignLeft)
    maxLabel = QLabel(str(formatMax(maximum)))
    layout.addWidget(maxLabel, 1, 3, Qt.AlignmentFlag.AlignRight)
    slider = QSlider(Qt.Orientation.Horizontal) if not double else _DoubleSlider(Qt.Orientation.Horizontal)
    slider.setMinimumWidth(350)
    slider.setRange(minimum, maximum)
    slider.setValue(value)
    layout.addWidget(slider, 2, 1, 1, 3)

    spinbox = QSpinBox() if not double else QDoubleSpinBox()
    if double:
      spinbox.setSingleStep(0.1)
    spinbox.setStyleSheet(SPINBOX_STYLESHEET)
    spinbox.setMinimumWidth(90)
    spinbox.setRange(minimum, maximum)
    spinbox.setValue(value)
    layout.addWidget(spinbox, 2, 4)

    def spinboxValueChanged():
      value = spinbox.value()
      blocked = slider.blockSignals(True)
      slider.setValue(value)
      slider.blockSignals(blocked)
      self.valueChanged.emit(value)
    spinbox.valueChanged.connect(spinboxValueChanged)
    slider.valueChanged.connect(lambda: spinbox.setValue(slider.value()))

    layout.setContentsMargins(20, 5, 20, 5)
    self.setLayout(layout)

    if name is not None:
      self.setFixedWidth(layout.totalSizeHint().width())
      if choices is not None:
        currentIdx = choices.itemlist.index(name) * 2
        titleLabel = QComboBox()
        titleLabel.setMaxVisibleItems(titleLabel.maxVisibleItems() * 2)
        titleLabel.setModel(choices)
        titleLabel.setCurrentIndex(currentIdx)
        listView = titleLabel.view()
        listView.setWordWrap(True)
        listView.adjustSize()
        titleLabel.currentIndexChanged.connect(lambda idx: self.choiceChanged.emit(idx))
      else:
        titleLabel = QLabel(PRETTY_PARAMETER_NAMES.get(name, name))
        titleLabel.setMinimumSize(1, 1)
        titleLabel.resizeEvent = lambda evt: titleLabel.setMinimumWidth(evt.size().width()) or titleLabel.setWordWrap(evt.size().width() <= titleLabel.sizeHint().width())
        slider.rangeChanged.connect(lambda: titleLabel.setMinimumWidth(1) or titleLabel.setWordWrap(False))
      layout.addWidget(titleLabel, 1, 2, Qt.AlignmentFlag.AlignCenter)

    self.value = spinbox.value
    self.minimum = spinbox.minimum
    self.maximum = spinbox.maximum
    self.setValue = lambda value: spinbox.setValue(value) or slider.setValue(value)
    self.setMinimum = lambda min_: spinbox.setMinimum(type_(min_)) or slider.setMinimum(type_(min_)) or minLabel.setText(str(formatMin(min_)))
    self.setMaximum = lambda max_: spinbox.setMaximum(type_(max_)) or slider.setMaximum(type_(max_)) or maxLabel.setText(str(formatMax(max_)))
    self.setRange = lambda min_, max_: spinbox.setRange(type_(min_), type_(max_)) or slider.setRange(type_(min_), type_(max_))
    self.setSingleStep = lambda step: spinbox.setSingleStep(step) or slider.setSingleStep(step)
    self.isSliderDown = slider.isSliderDown
    self.sliderWidth = slider.width
    self.setPosition = slider.setSliderPosition
    self.setChoice = lambda idx: titleLabel.setCurrentIndex(idx)


def _chooseFrameLayout(cap, spinboxValues, title, titleStyle=None):
  if titleStyle is None:
    titleStyle = {'font': TITLE_FONT}
  layout = QVBoxLayout()
  titleLabel = apply_style(QLabel(title), **titleStyle)
  titleLabel.setMinimumSize(1, 1)
  titleLabel.resizeEvent = lambda evt: titleLabel.setMinimumWidth(evt.size().width()) or titleLabel.setWordWrap(evt.size().width() <= titleLabel.sizeHint().width())
  layout.addWidget(titleLabel, alignment=Qt.AlignmentFlag.AlignCenter)
  video = QLabel()
  layout.addWidget(video, alignment=Qt.AlignmentFlag.AlignCenter, stretch=1)

  firstFrame, minFrame, maxFrame = spinboxValues
  frameSlider = SliderWithSpinbox(firstFrame, minFrame, maxFrame, name="Frame")

  def getFrame():
    cap.set(1, frameSlider.value())
    ret, img = cap.read()
    return img
  frameSlider.valueChanged.connect(lambda: setPixmapFromCv(getFrame(), video))

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

  return layout, video, frameSlider


def chooseFrame(app, videoPath, title, chooseFrameBtnText):
  cap = zzVideoReading.VideoCapture(videoPath)
  cap.set(1, 1)
  ret, frame = cap.read()
  layout, label, valueWidget = _chooseFrameLayout(cap, (1, 0, cap.get(7) - 2), title)

  frameIdx = None
  def chooseFrameBtnClicked():
    nonlocal frameIdx
    frameIdx = valueWidget.value()
  showBlockingPage(layout, buttons=(("Back", lambda: None, True), ("Next", chooseFrameBtnClicked, True, None, DEFAULT_BUTTON_COLOR)), labelInfo=(frame, label, False))
  if frameIdx is None:
    return None
  cap.set(1, frameIdx)
  return cap.read()[1]


def chooseBeginningPage(app, videoPath, title, chooseFrameBtnText, chooseFrameBtnCb, extraButtonInfo=None, titleStyle=None, additionalLayout=None, leftButtonInfo=None):
  cap = zzVideoReading.VideoCapture(videoPath)
  cap.set(1, 1)
  ret, frame = cap.read()
  layout, label, valueWidget = _chooseFrameLayout(cap, (1, 0, cap.get(7) - 2), title, titleStyle=titleStyle)
  if additionalLayout is not None:
    layout.addLayout(additionalLayout)

  buttonsLayout = QHBoxLayout()
  buttonsLayout.addStretch()
  if leftButtonInfo is not None:
    text, cb = leftButtonInfo
    leftBtn = QPushButton(text)
    leftBtn.clicked.connect(cb)
    buttonsLayout.addWidget(leftBtn)
  if app.configFileHistory:
    backBtn = QPushButton("Back")
    backBtn.setObjectName("back")
    buttonsLayout.addWidget(backBtn)
  chooseFrameBtn = QPushButton(chooseFrameBtnText) if extraButtonInfo is not None else apply_style(QPushButton(chooseFrameBtnText), background_color=DEFAULT_BUTTON_COLOR)
  def chooseFrameBtnClicked():
    app.configFile["firstFrame"] = valueWidget.value()
    app.configFile["firstFrameForBackExtract"] = valueWidget.value()
    chooseFrameBtnCb()
  chooseFrameBtn.clicked.connect(chooseFrameBtnClicked)
  buttonsLayout.addWidget(chooseFrameBtn)
  extraBtn = None
  if extraButtonInfo is not None:
    if len(extraButtonInfo) == 2:
      text, cb = extraButtonInfo
      styleKwargs = {}
    else:
      assert len(extraButtonInfo) == 3
      text, cb, styleKwargs = extraButtonInfo
    extraBtn = apply_style(QPushButton(text), **styleKwargs)
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
  buttons = []
  if app.configFileHistory:
    buttons.append(backBtn)
  buttons.append(chooseFrameBtn)
  if extraBtn is not None:
    buttons.append(extraBtn)
  for btn in buttons:
    btn.clicked.connect(lambda: stackedLayout.removeWidget(page))


def chooseEndPage(app, videoPath, title, chooseFrameBtnText, chooseFrameBtnCb, leftButtonInfo=None):
  cap = zzVideoReading.VideoCapture(videoPath)
  maximum = cap.get(7) - 2
  while True:
    cap.set(1, maximum)
    ret, frame = cap.read()
    if ret:
      break
    maximum -= 1
  layout, label, valueWidget = _chooseFrameLayout(cap, (maximum, app.configFile["firstFrame"] + 1, maximum), title)

  buttonsLayout = QHBoxLayout()
  buttonsLayout.addStretch()
  if leftButtonInfo is not None:
    text, cb = leftButtonInfo
    leftBtn = QPushButton(text)
    leftBtn.clicked.connect(cb)
    buttonsLayout.addWidget(leftBtn)
  if app.configFileHistory:
    backBtn = QPushButton("Back")
    backBtn.setObjectName("back")
    buttonsLayout.addWidget(backBtn)
  chooseFrameBtn = apply_style(QPushButton(chooseFrameBtnText), background_color=DEFAULT_BUTTON_COLOR)
  def chooseFrameBtnClicked():
    app.configFile["lastFrame"] = valueWidget.value()
    app.configFile["lastFrameForBackExtract"] = valueWidget.value()
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
  for btn in (backBtn, chooseFrameBtn) if app.configFileHistory else (chooseFrameBtn,):
    btn.clicked.connect(lambda: stackedLayout.removeWidget(page))


class _InteractiveLabelPoint(QLabel):
  pointSelected = pyqtSignal(QPoint)
  proceed = pyqtSignal()

  def __init__(self, width, height, selectingRegion):
    super().__init__()
    self._width = width
    self._height = height
    self._point = None
    self._selectingRegion = selectingRegion
    self._currentPosition = None
    self._tooltipShown = False
    self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
    if self._selectingRegion:
      self.setMouseTracking(True)

  def keyPressEvent(self, evt):
    if self._point is not None and (evt.key() == Qt.Key.Key_Enter or evt.key() == Qt.Key.Key_Return):
      self.proceed.emit()
      return
    super().keyPressEvent(evt)

  def mouseMoveEvent(self, evt):
    if self._selectingRegion:
      self._currentPosition = evt.pos()
      self.update()

  def mousePressEvent(self, evt):
    self._point = evt.pos()
    self.update()
    self.pointSelected.emit(self._point)

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


def getPoint(frame, title, extraButtons=(), selectingRegion=False, backBtnCb=None, zoomable=False, useNext=True, dialog=False):
  height, width = frame.shape[:2]

  layout = QVBoxLayout()
  additionalText = "Enter/Return keys can be used instead of clicking Next."
  if zoomable:
    controlModifier = 'Ctrl' if sys.platform != 'darwin' else 'Cmd'  # Qt documentation explicilty states this
    additionalText += "\nYou can zoom in/out using the mouse wheel or %s and +/- and drag the image." % controlModifier
  layout.addWidget(QLabel(additionalText), alignment=Qt.AlignmentFlag.AlignCenter)

  video = _InteractiveLabelPoint(width, height, selectingRegion)

  def callback(cb):
    if zoomable:
      zoomableImage = layout.itemAt(1).widget()
      layout.replaceWidget(zoomableImage, video)
      zoomableImage.hide()
      video.show()
    cb(video)

  def updateButton(args):
    text, cb, exitLoop = args[:3]
    retval = (text, lambda: callback(cb), exitLoop)
    if len(args) == 4:
      retval += (video.pointSelected,)
    return retval

  extraButtons = tuple(updateButton(button) for button in extraButtons)
  buttons = (("Back", backBtnCb, True),) if backBtnCb is not None else ()
  buttons += (("Next", None, True, video.pointSelected, DEFAULT_BUTTON_COLOR),) if useNext else ()
  layout.addWidget(video, alignment=Qt.AlignmentFlag.AlignCenter, stretch=1)
  if not useNext:
    video.pointSelected.connect(lambda: QApplication.restoreOverrideCursor())
  if not dialog:
    showBlockingPage(layout, title=title, buttons=extraButtons + buttons, labelInfo=(frame, video, zoomable), exitSignals=(video.proceed,) if useNext else (video.pointSelected,))
  else:
    showDialog(layout, title=title, buttons=extraButtons + buttons, labelInfo=(frame, video, zoomable), exitSignals=(video.proceed,) if useNext else (video.pointSelected,))
  return video.getCoordinates()


class _InteractiveLabelRect(QLabel):
  regionSelected = pyqtSignal(bool)

  def __init__(self, width, height, initialRect):
    super().__init__()
    self._width = width
    self._height = height
    self._currentPosition = None
    if initialRect is not None:
      self._initialRect = initialRect
    self._topLeft = None
    self._bottomRight = None
    self._size = self.size()
    self._tooltipShown = False
    self.setMouseTracking(True)

  def clearRectangle(self):
    self._topLeft = None
    self._bottomRight = None
    self.update()
    self.regionSelected.emit(False)

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
    if hasattr(self, '_initialRect'):
      self._topLeft, self._bottomRight = (transformCoordinates(QRectF(QPointF(0, 0), QSizeF(self._width, self._height)), QRectF(QPointF(0, 0), QSizeF(self.size())), point) for point in self._initialRect)
      del self._initialRect
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
    if self._topLeft is not None:
      self._topLeft = transformCoordinates(QRectF(QPointF(0, 0), QSizeF(self._size)), QRectF(QPointF(0, 0), QSizeF(evt.size())), self._topLeft)
    if self._bottomRight is not None:
      self._bottomRight = transformCoordinates(QRectF(QPointF(0, 0), QSizeF(self._size)), QRectF(QPointF(0, 0), QSizeF(evt.size())), self._bottomRight)
    if self._currentPosition:
      self._currentPosition = transformCoordinates(QRectF(QPointF(0, 0), QSizeF(self._size)), QRectF(QPointF(0, 0), QSizeF(evt.size())), self._currentPosition)
    self._size = self.size()

  def getCoordinates(self):
    if self._topLeft is None or self._bottomRight is None:
      return [0, 0], [0, 0]
    points = (self._topLeft, self._bottomRight)
    if self._size.height() != self._height or self._size.width() != self._width:
      points = (transformCoordinates(QRectF(QPointF(0, 0), QSizeF(self._size)), QRectF(QPointF(0, 0), QSizeF(self._width, self._height)), point) for point in points)
    return ([point.x(), point.y()] for point in points)


def getRectangle(frame, title, backBtnCb=None, dialog=False, buttons=None, initialRect=None, allowEmpty=False, contrastCheckbox=None, getFrame=None):
  height, width, _ = frame.shape

  layout = QVBoxLayout()

  video = _InteractiveLabelRect(width, height, initialRect)
  layout.addWidget(video, alignment=Qt.AlignmentFlag.AlignCenter, stretch=1)
  if contrastCheckbox is not None:
    assert getFrame is not None
    contrastCheckbox.toggled.connect(lambda checked: setPixmapFromCv(getFrame(checked), video))
    layout.addWidget(contrastCheckbox, alignment=Qt.AlignmentFlag.AlignCenter)
  if allowEmpty:
    clearRectangleBtn = QPushButton('Clear rectangle')
    clearRectangleBtn.clicked.connect(video.clearRectangle)
    clearRectangleBtn.setEnabled(initialRect is not None)
    layout.addWidget(clearRectangleBtn, alignment=Qt.AlignmentFlag.AlignCenter)
    video.regionSelected.connect(clearRectangleBtn.setEnabled)
  if buttons is None:
    if backBtnCb is not None:
      buttons = (("Back", backBtnCb, True), ("Next", None, True, video.regionSelected, DEFAULT_BUTTON_COLOR))
    else:
      buttons = (("Next", None, True, video.regionSelected, DEFAULT_BUTTON_COLOR),)
  else:
    assert backBtnCb is None
  if not dialog:
    showBlockingPage(layout, title=title, buttons=buttons, labelInfo=(frame, video))
  else:
    showDialog(layout, title=title, buttons=buttons, labelInfo=(frame, video))

  return video.getCoordinates()


class _CVLabelLine(QLabel):
  pointSelected = pyqtSignal(QPoint)
  proceed = pyqtSignal()

  def __init__(self, width, height, frame, thickness, startPoint):
    super().__init__()
    self._width = width
    self._height = height
    self._point = None
    self._currentPosition = None
    self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
    self.setMouseTracking(True)
    self._thickness = thickness
    self._startPoint = startPoint
    self._frame = frame

  def keyPressEvent(self, evt):
    if self._point is not None and (evt.key() == Qt.Key.Key_Enter or evt.key() == Qt.Key.Key_Return):
      self.proceed.emit()
      return
    super().keyPressEvent(evt)

  def mouseMoveEvent(self, evt):
    self._currentPosition = evt.pos()
    point = self._currentPosition
    if self._size.height() != self._height or self._size.width() != self._width:
      point = transformCoordinates(QRectF(QPointF(0, 0), QSizeF(self._size)), QRectF(QPointF(0, 0), QSizeF(self._width, self._height)), point)
    setPixmapFromCv(cv2.line(self._frame.copy(), (self._startPoint), (point.x(), point.y()), (255, 255, 255), self._thickness), self)

  def mousePressEvent(self, evt):
    self._point = evt.pos()
    self.pointSelected.emit(self._point)

  def enterEvent(self, evt):
    QApplication.setOverrideCursor(Qt.CursorShape.CrossCursor)

  def leaveEvent(self, evt):
    QApplication.restoreOverrideCursor()
    self._currentPosition = None

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


def getLine(frame, title, thickness, startPoint):
  height, width = frame.shape[:2]

  layout = QVBoxLayout()

  video = _CVLabelLine(width, height, frame, thickness, startPoint)
  layout.addWidget(video, alignment=Qt.AlignmentFlag.AlignCenter)
  buttons = (("Next", None, True),)
  showDialog(layout, title=title, buttons=buttons, labelInfo=(frame, video), exitSignals=(video.pointSelected,))

  return video.getCoordinates()


class _CVDrawLabel(QLabel):
  proceed = pyqtSignal()

  def __init__(self, width, height, frame):
    super().__init__()
    self._width = width
    self._height = height
    self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
    self._frame = frame

  def keyPressEvent(self, evt):
    if self._point is not None and (evt.key() == Qt.Key.Key_Enter or evt.key() == Qt.Key.Key_Return):
      self.proceed.emit()
      return
    super().keyPressEvent(evt)

  def mouseMoveEvent(self, evt):
    point = evt.pos()
    if self._size.height() != self._height or self._size.width() != self._width:
      point = transformCoordinates(QRectF(QPointF(0, 0), QSizeF(self._size)), QRectF(QPointF(0, 0), QSizeF(self._width, self._height)), point)
    self._frame = cv2.circle(self._frame, (point.x(), point.y()), 3, (255, 255, 255), -1)
    setPixmapFromCv(self._frame, self)

  def mousePressEvent(self, evt):
    point = evt.pos()
    if self._size.height() != self._height or self._size.width() != self._width:
      point = transformCoordinates(QRectF(QPointF(0, 0), QSizeF(self._size)), QRectF(QPointF(0, 0), QSizeF(self._width, self._height)), point)
    self._frame = cv2.circle(self._frame, (point.x(), point.y()), 3, (255, 255, 255), -1)
    setPixmapFromCv(self._frame, self)

  def enterEvent(self, evt):
    QApplication.setOverrideCursor(Qt.CursorShape.CrossCursor)

  def leaveEvent(self, evt):
    QApplication.restoreOverrideCursor()

  def resizeEvent(self, evt):
    super().resizeEvent(evt)
    self._size = self.size()

  def getFrame(self):
    return self._frame


def drawPoints(frame, title):
  height, width = frame.shape[:2]

  layout = QVBoxLayout()

  video = _CVDrawLabel(width, height, frame)
  layout.addWidget(video, alignment=Qt.AlignmentFlag.AlignCenter)
  buttons = (("Done", None, True),)
  showDialog(layout, title=title, buttons=buttons, labelInfo=(frame, video))
  return video.getFrame()


class _FrameLabel(QLabel):
  proceed = pyqtSignal()

  def keyPressEvent(self, evt):
    super().keyPressEvent(evt)
    self.proceed.emit()


def showFrame(frame, title='', buttons=(), timeout=None):
  label = _FrameLabel()
  label.setMinimumSize(1, 1)
  label.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
  layout = QVBoxLayout()
  layout.addWidget(label, alignment=Qt.AlignmentFlag.AlignCenter)
  showDialog(layout, title=title, buttons=buttons, labelInfo=(frame, label), timeout=timeout, exitSignals=(label.proceed,))


def addToHistory(fn):
  def inner(*args, **kwargs):
    app = QApplication.instance()
    configFileState = app.configFile.copy()
    def restoreState(restoreConfig=True):
      if restoreConfig:
        app.configFile.clear()
        app.configFile.update(configFileState)
      del app.configFileHistory[-1:]
      fn(*args, **kwargs)
    app.configFileHistory.append(restoreState)
    return fn(*args, **kwargs)
  return inner


class Expander(QWidget):
  expanded = pyqtSignal(bool)

  def __init__(self, parent, title, layout, animationDuration=200, showFrame=False, addScrollbars=False, retainWidth=False):
    super().__init__()

    self._retainWidth = retainWidth
    self._toggleButton = toggleButton = QToolButton()
    toggleButton.setStyleSheet("QToolButton { border: none; }")
    toggleButton.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonTextBesideIcon)
    toggleButton.setArrowType(Qt.ArrowType.RightArrow)
    toggleButton.setText(str(title))
    toggleButton.setCheckable(True)
    toggleButton.setChecked(False)

    self._contentArea = contentArea = QScrollArea()
    if not showFrame:
      contentArea.setFrameShape(QFrame.Shape.NoFrame)
    contentArea.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
    contentArea.setMaximumHeight(0)
    contentArea.setMinimumHeight(0)

    mainLayout = QGridLayout()
    mainLayout.setVerticalSpacing(0)
    mainLayout.setContentsMargins(0, 0, 0, 0)
    mainLayout.addWidget(toggleButton, 0, 0, 1, 3, Qt.AlignmentFlag.AlignHCenter)
    mainLayout.addWidget(contentArea, 1, 0, 1, 3)
    self.setLayout(mainLayout)

    if not addScrollbars:
      contentArea.setLayout(layout)
    else:
      widget = QWidget(self)
      widget.setLayout(layout)
      contentArea.setWidgetResizable(True)
      contentArea.setWidget(widget)
    self._collapseHeight = self.sizeHint().height() - contentArea.maximumHeight()
    contentHeight = layout.sizeHint().height()
    self._toggleAnimation = toggleAnimation = QParallelAnimationGroup()
    toggleAnimation.addAnimation(QPropertyAnimation(self, b"minimumHeight"))
    toggleAnimation.addAnimation(QPropertyAnimation(self, b"maximumHeight"))
    toggleAnimation.addAnimation(QPropertyAnimation(contentArea, b"maximumHeight"))
    for i in range(toggleAnimation.animationCount() - 1):
      spoilerAnimation = toggleAnimation.animationAt(i)
      spoilerAnimation.setDuration(animationDuration)
      spoilerAnimation.setStartValue(self._collapseHeight)
      spoilerAnimation.setEndValue(self._collapseHeight + contentHeight)
    contentAnimation = toggleAnimation.animationAt(toggleAnimation.animationCount() - 1)
    contentAnimation.setDuration(animationDuration)
    contentAnimation.setStartValue(0)
    contentAnimation.setEndValue(contentHeight)

    def startAnimation(checked):
      self.expanded.emit(checked)
      arrowType = Qt.ArrowType.DownArrow if checked else Qt.ArrowType.RightArrow
      direction = QAbstractAnimation.Direction.Forward if checked else QAbstractAnimation.Direction.Backward
      toggleButton.setArrowType(arrowType)
      toggleAnimation.setDirection(direction)
      toggleAnimation.start()
    toggleButton.clicked.connect(startAnimation)

  def updateLayout(self, layout):
    widget = self._contentArea.widget()
    if widget is None:
      return
    widget = QWidget(self)
    widget.setLayout(layout)
    self._contentArea.setWidget(widget)

  def refresh(self, availableHeight):
    layout = self._contentArea.layout()
    height = layout.sizeHint().height() if layout is not None else self._contentArea.widget().sizeHint().height() + 5
    contentHeight = min(height, availableHeight - self._collapseHeight - 10)
    if self._contentArea.maximumHeight():
      self._contentArea.setMaximumHeight(contentHeight)
      self.setMinimumHeight(self._collapseHeight + contentHeight)
      self.setMaximumHeight(self._collapseHeight + contentHeight)
    for i in range(self._toggleAnimation.animationCount() - 1):
      self._toggleAnimation.animationAt(i).setEndValue(self._collapseHeight + contentHeight)
    self._toggleAnimation.animationAt(self._toggleAnimation.animationCount() - 1).setEndValue(contentHeight)

  def sizeHint(self):
    hint = super().sizeHint()
    if not self._retainWidth or self._contentArea.layout() is None:
      return hint
    contentHint = self._contentArea.layout().sizeHint()
    return QSize(max(hint.width(), contentHint.width()), hint.height())

  def isExpanded(self):
    return self._toggleButton.isChecked()


class _InteractiveLabelCircle(QLabel):
  circleSelected = pyqtSignal(bool)

  def __init__(self, width, height):
    super().__init__()
    self._width = width
    self._height = height
    self._center = None
    self._currentPosition = None
    self._radius = None
    self._size = None
    self._tooltipShown = False
    self.setMouseTracking(True)

  def mousePressEvent(self, evt):
    if self._center is None or self._radius is not None:
      self._center = evt.pos()
      self._radius = None
      self._currentPosition = None
      self.circleSelected.emit(False)
    else:
      self._radius = QLine(self._center, evt.pos())
      self.circleSelected.emit(True)
    self.update()

  def mouseReleaseEvent(self, evt):
    if self._radius is not None and not self._tooltipShown:
      QToolTip.showText(evt.globalPosition() if PYQT6 else evt.globalPos(), "If you aren't satisfied with the selection, click again.", self, self.rect(), 5000)
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
    if self._currentPosition is None and self._center is None:
      return
    qp = QPainter()
    qp.begin(self)
    if self._center is not None:
      qp.setBrush(QColor(255, 0, 0))
      qp.setPen(Qt.PenStyle.NoPen)
      radius = self._radius if self._radius is not None else QLine(self._center, self._currentPosition) if self._currentPosition is not None else None
      qp.drawEllipse(self._center, 2, 2)
      if radius is not None:
        radius = math.sqrt(radius.dx() * radius.dx() + radius.dy() * radius.dy())
        qp.setBrush(Qt.BrushStyle.NoBrush)
        qp.setPen(QColor(0, 0, 255))
        qp.drawEllipse(self._center, radius, radius)
    qp.end()

  def resizeEvent(self, evt):
    super().resizeEvent(evt)
    self._size = self.size()

  def getInfo(self):
    if self._center is None or self._radius is None:
      return None, None
    if self._size.height() != self._height or self._size.width() != self._width:
      center = transformCoordinates(QRectF(QPointF(0, 0), QSizeF(self._size)), QRectF(QPointF(0, 0), QSizeF(self._width, self._height)), self._center)
      radius = transformCoordinates(QRectF(QPointF(0, 0), QSizeF(self._size)), QRectF(QPointF(0, 0), QSizeF(self._width, self._height)), self._radius)
    else:
      center = self._center
      radius = self._radius
    return center, int(math.sqrt(radius.dx() * radius.dx() + radius.dy() * radius.dy()))


def getCircle(frame, title, backBtnCb=None, zoomable=False):
  height, width, _ = frame.shape

  layout = QVBoxLayout()

  video = _InteractiveLabelCircle(width, height)
  layout.addWidget(video, alignment=Qt.AlignmentFlag.AlignCenter, stretch=1)
  if backBtnCb is not None:
    buttons = (("Cancel", backBtnCb, True), ("Ok", None, True, video.circleSelected, DEFAULT_BUTTON_COLOR))
  else:
    buttons = (("Ok", None, True, video.circleSelected, DEFAULT_BUTTON_COLOR),)
  showBlockingPage(layout, title=title, buttons=buttons, labelInfo=(frame, video, zoomable))
  return video.getInfo()


class _CollapseButton(QToolButton):
  def enterEvent(self, evt):
    QApplication.setOverrideCursor(Qt.CursorShape.ArrowCursor)
    super().enterEvent(evt)

  def leaveEvent(self, evt):
    QApplication.restoreOverrideCursor()
    super().leaveEvent(evt)


class CollapsibleSplitter(QSplitter):
  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    self.setHandleWidth(12)
    self._lastState = None

  def _collapseButtonClicked(self):
    self.setCollapsible(0, True)
    leftWidget = self.widget(0)
    orientation = self.orientation()
    if all(self.sizes()):
      self._lastState = self.saveState()
      self._collapseButton.setArrowType(Qt.ArrowType.RightArrow if orientation == Qt.Orientation.Horizontal else Qt.ArrowType.DownArrow)
      self.setSizes([0, 1])
    else:
      self._collapseButton.setArrowType(Qt.ArrowType.LeftArrow if orientation == Qt.Orientation.Horizontal else Qt.ArrowType.UpArrow)
      self.setSizes([1, 1])
      if self._lastState is not None:
        self.restoreState(self._lastState)
        self._lastState = None
    self.setCollapsible(0, False)
    self.splitterMoved.connect(self._splitterMoved)

  def _splitterMoved(self, pos, idx):
    assert idx == 1
    orientation = self.orientation()
    if pos and self._lastState is not None:
      self._collapseButton.setArrowType(Qt.ArrowType.LeftArrow if orientation == Qt.Orientation.Horizontal else Qt.ArrowType.UpArrow)
      self._lastState = None

  def createHandle(self):
    count = self.count()
    orientation = self.orientation()
    handle = QSplitterHandle(orientation, self)

    layout = QVBoxLayout() if orientation == Qt.Orientation.Horizontal else QHBoxLayout()
    layout.setContentsMargins(0, 0, 0, 0)

    self._collapseButton = _CollapseButton()
    self._collapseButton.setArrowType(Qt.ArrowType.LeftArrow if orientation == Qt.Orientation.Horizontal else Qt.ArrowType.UpArrow)
    self._collapseButton.clicked.connect(self._collapseButtonClicked)
    layout.addWidget(self._collapseButton)

    handle.setLayout(layout)
    return handle


def improveContrast(frame, quartile):
  frame = 255 - frame
  frameIsBGR = len(frame.shape) == 3
  if frameIsBGR:
    frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
  lowVal = int(np.quantile(frame, quartile))
  highVal = int(np.quantile(frame, 1 - quartile))
  frame[frame < lowVal] = lowVal
  frame[frame > highVal] = highVal
  frame = frame - lowVal
  mult = np.max(frame)
  frame = frame * (255 / mult)
  frame = frame.astype('uint8')
  if frameIsBGR:
    frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
  return frame


class _RotationAngleLabel(QLabel):
  def __init__(self):
    super().__init__()
    self._currentPosition = None
    self.setMouseTracking(True)

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
    if self._currentPosition is None:
      return
    qp = QPainter()
    qp.begin(self)
    qp.setPen(QColor(255, 0, 0))
    qp.drawLine(0, self._currentPosition.y(), self.width(), self._currentPosition.y())
    qp.drawLine(self._currentPosition.x(), 0, self._currentPosition.x(), self.height())
    qp.end()


def getRotationAngle(frame, angle, dialog=False):
  layout = QVBoxLayout()
  video = _RotationAngleLabel()
  layout.addWidget(video, alignment=Qt.AlignmentFlag.AlignCenter, stretch=1)

  frameSlider = SliderWithSpinbox(angle, -180, 180, name="Rotation angle (degrees)", double=True)

  def getFrame():
    nonlocal angle
    angle = frameSlider.value()
    return cv2.warpAffine(frame, cv2.getRotationMatrix2D(tuple(x / 2 for x in frame.shape[1::-1]), angle, 1.0), frame.shape[1::-1], flags=cv2.INTER_LINEAR)
  frameSlider.valueChanged.connect(lambda: setPixmapFromCv(getFrame(), video))
  layout.addWidget(frameSlider, alignment=Qt.AlignmentFlag.AlignCenter)

  cancelled = False
  def cancel():
    nonlocal cancelled
    cancelled = True
  buttons = (("Cancel", cancel, True), ("Ok", None, True))
  if not dialog:
    showBlockingPage(layout, title="Select the video rotation angle", buttons=buttons, labelInfo=(getFrame(), video), dialog=dialog)
  else:
    showDialog(layout, title="Select the video rotation angle", buttons=buttons, labelInfo=(getFrame(), video))
  return None if cancelled else angle


class WellSelectionLabel(QLabel):
  def __init__(self, width, height, selectedWell=0):
    super().__init__()
    self._width = width
    self._height = height
    self._well = selectedWell
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
