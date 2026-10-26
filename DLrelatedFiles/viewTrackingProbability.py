"""
Standalone viewer for ZebraZoom tracking results (.h5 files).

It shows the tracking on top of the video, the same way ZebraZoom's
"visualize results" video window does (slider, play/pause, keyboard
navigation, tracking points All/Minimal/None, size, contrast, identities,
save), and additionally prints, right next to each tracked animal, the
detection probability stored for that frame in
dataForWellX/dataForAnimalY/dataPerFrame/probabilityGoodDetection
(for YOLO-based tracking, this is the YOLO box confidence; it is only stored
when the tracking was run with "addGoodDetectionProbability": 1).

This script does not import anything from ZebraZoom. It only requires:
  PyQt5, opencv-python, h5py, numpy

Usage:
  python viewTrackingProbability.py                     -> pick a result in the default ZZoutput folder
  python viewTrackingProbability.py path/to/ZZoutput    -> pick a result in that folder
  python viewTrackingProbability.py path/to/result.h5   -> open that result directly

Mouse wheel over the video zooms in/out, left-click drag pans, double-click resets the zoom.
"""

import collections
import datetime
import importlib.util
import math
import os
import random
import sys

import cv2
import h5py
import numpy as np

from PyQt5.QtCore import Qt, QRectF, QSettings, QTimer, pyqtSignal
from PyQt5.QtGui import QColor, QImage, QKeySequence, QPainter
from PyQt5.QtWidgets import (QAbstractItemView, QApplication, QButtonGroup, QCheckBox, QDoubleSpinBox, QFileDialog,
                             QHBoxLayout, QHeaderView, QLabel, QLineEdit, QMainWindow, QMessageBox, QProgressDialog,
                             QPushButton, QRadioButton, QShortcut, QSizePolicy, QSlider, QSpinBox, QStackedWidget,
                             QStyleOptionSlider, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget)


# Default values of the ZebraZoom hyperparameters used for the display (from zebrazoom/code/getHyperparameters.py),
# used when the configuration stored inside the .h5 file does not set them.
ZZ_DEFAULTS = {
  "trackingPointSizeDisplay": 1,
  "plotOnlyOneTailPointForVisu": 0,
  "validationVideoPlotHeading": 1,
  "validationVideoPlotAnimalNumber": 0,
  "outputValidationVideoContrastImprovement": 0,
  "outputValidationVideoContrastImprovementQuartile": 0.01,
  "copyOriginalVideoToOutputFolderForValidation": 0,
}

ORIGINAL_VIDEO_COPY_SUFFIX = '_originalVideoWithoutAnyTrackingDisplayed_pleaseUseTheGUIToVisualizeTrackingPoints.avi'

# Probability text colour scale (when "Color by value" is checked): red at or below LOW, yellow halfway, green at or above HIGH.
PROBA_COLOR_LOW = 0.25
PROBA_COLOR_HIGH = 0.75

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))


# ---------------------------------------------------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------------------------------------------------

def _toPython(value):
  if isinstance(value, bytes):
    return value.decode(errors='replace')
  if isinstance(value, np.ndarray):
    return value.tolist()
  if isinstance(value, np.generic):
    return value.item()
  return value


def _ancestors(path):
  path = os.path.abspath(path)
  while True:
    yield path
    parent = os.path.dirname(path)
    if parent == path:
      return
    path = parent


def findDefaultZZoutputFolder():
  candidates = [os.path.join(SCRIPT_DIR, 'zebrazoom', 'ZZoutput'), os.path.join(SCRIPT_DIR, 'ZZoutput'),
                os.path.join(os.getcwd(), 'zebrazoom', 'ZZoutput'), os.path.join(os.getcwd(), 'ZZoutput')]
  try:
    spec = importlib.util.find_spec('zebrazoom')  # only locates the package, does not import it
    if spec is not None and spec.submodule_search_locations:
      candidates.append(os.path.join(list(spec.submodule_search_locations)[0], 'ZZoutput'))
  except Exception:
    pass
  return next((folder for folder in candidates if os.path.isdir(folder)), os.path.expanduser('~'))


def resolveVideoPath(h5Path, attrs, config):
  """Returns (videoPath or None, framesAreAbsolute), following the same rules as ZebraZoom's validation video window."""
  base = os.path.splitext(h5Path)[0]
  if 'pathToOriginalVideo' in attrs:
    storedPath = str(attrs['pathToOriginalVideo'])
    if os.path.isabs(storedPath):
      candidates = [storedPath]
    else:  # relative paths are relative to the folder ZebraZoom was launched from, which we don't know: try likely ones
      folders = [os.getcwd(), SCRIPT_DIR, *_ancestors(os.path.dirname(h5Path)), *_ancestors(SCRIPT_DIR)]
      candidates = [os.path.join(folder, storedPath) for folder in dict.fromkeys(folders)]
    candidates.append(os.path.join(os.path.dirname(h5Path), os.path.basename(storedPath.replace('\\', '/'))))
    return next((os.path.normpath(c) for c in candidates if os.path.isfile(c)), None), True
  if config.get("copyOriginalVideoToOutputFolderForValidation", 0) and os.path.isfile(base + ORIGINAL_VIDEO_COPY_SUFFIX):
    return base + ORIGINAL_VIDEO_COPY_SUFFIX, True
  if os.path.isfile(base + '.avi'):
    return base + '.avi', False
  return None, True


def improveContrast(frame, quartile):
  # Same as zebrazoom.code.createValidationVideo.improveContrast
  frame = 255 - frame
  gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
  lowVal = int(np.quantile(gray, quartile))
  highVal = int(np.quantile(gray, 1 - quartile))
  gray = np.clip(gray, lowVal, highVal) - lowVal
  mult = np.max(gray)
  if mult > 0:
    gray = gray * (255 / mult)
  return cv2.cvtColor(gray.astype('uint8'), cv2.COLOR_GRAY2BGR)


def probabilityColor(p):
  """BGR colour going from red (p <= PROBA_COLOR_LOW) to yellow to green (p >= PROBA_COLOR_HIGH)."""
  t = min(max((p - PROBA_COLOR_LOW) / (PROBA_COLOR_HIGH - PROBA_COLOR_LOW), 0.), 1.)
  if t < 0.5:
    return (0, int(255 * 2 * t), 255)
  return (0, 255, int(255 * (2 - 2 * t)))


# ---------------------------------------------------------------------------------------------------------------------
# Data
# ---------------------------------------------------------------------------------------------------------------------

class TrackingResults:
  """Per-frame tracking data of a ZebraZoom .h5 results file, read lazily by chunks of frames."""
  CHUNK_SIZE = 1000
  MAX_CACHED_CHUNKS = 4

  def __init__(self, path):
    self.path = path
    with h5py.File(path, 'r') as results:
      self.attrs = {key: _toPython(value) for key, value in results.attrs.items()}
      self.config = {key: _toPython(value) for key, value in results['configurationFileUsed'].attrs.items()} if 'configurationFileUsed' in results else {}
      self.wellOffsets = []
      if 'wellPositions' in results:
        for wellIdx in range(len(results['wellPositions'])):
          wellAttrs = results[f'wellPositions/well{wellIdx}'].attrs
          self.wellOffsets.append((float(wellAttrs.get('topLeftX', 0)), float(wellAttrs.get('topLeftY', 0))))
      else:
        self.wellOffsets.append((0., 0.))

      self.animals = []  # (wellIdx, animalIdx)
      self._perFramePaths = []
      bouts = []
      for wellIdx in range(len(self.wellOffsets)):
        wellGroup = results.get(f'dataForWell{wellIdx}')
        if wellGroup is None:
          continue
        for animalIdx in range(len(wellGroup)):
          animalGroup = wellGroup.get(f'dataForAnimal{animalIdx}')
          if animalGroup is None or 'dataPerFrame' not in animalGroup or 'HeadPos' not in animalGroup['dataPerFrame']:
            continue
          self.animals.append((wellIdx, animalIdx))
          self._perFramePaths.append(animalGroup['dataPerFrame'].name)
          animalBouts = []
          if 'listOfBouts' in animalGroup:
            listOfBouts = animalGroup['listOfBouts']
            for boutIdx in range(int(listOfBouts.attrs.get('numberOfBouts', 0))):
              boutAttrs = listOfBouts[f'bout{boutIdx}'].attrs
              animalBouts.append((int(boutAttrs['BoutStart']), int(boutAttrs['BoutEnd'])))
          bouts.append(animalBouts)
      if not self.animals:
        raise ValueError('No per-frame tracking data found in this file.')

      firstGroup = results[self._perFramePaths[0]]
      self.nbFrames = len(firstGroup['HeadPos'])
      self.nbTailPoints = len(self._columns(firstGroup['TailPosX'])) if 'TailPosX' in firstGroup else 0
      self.probabilityAnimalsCount = sum('probabilityGoodDetection' in results[path] for path in self._perFramePaths)

    self.firstFrame = int(self.attrs.get('firstFrame', 0))
    self.lastFrame = int(self.attrs.get('lastFrame', self.firstFrame + self.nbFrames - 1))
    self.hasProbability = self.probabilityAnimalsCount > 0

    self.inBout = np.zeros((len(self.animals), self.nbFrames), dtype=bool)
    for k, animalBouts in enumerate(bouts):
      for start, end in animalBouts:
        self.inBout[k, max(start - self.firstFrame, 0):max(end - self.firstFrame + 1, 0)] = True

    # Same random colour modifications as ZebraZoom (animal 0 keeps the default colour), but reproducible
    rng = random.Random(0)
    maxAnimalIdx = max(animalIdx for _, animalIdx in self.animals)
    self.colorModif = [(0, 0, 0)] + [(rng.randrange(255), rng.randrange(255), rng.randrange(255)) for _ in range(maxAnimalIdx)]
    self.maxAnimalIdx = maxAnimalIdx

    self._chunks = collections.OrderedDict()

  @staticmethod
  def _columns(dataset):
    return list(dataset.attrs['columns']) if 'columns' in dataset.attrs else list(dataset.dtype.names)

  def setting(self, key):
    return self.config.get(key, ZZ_DEFAULTS[key])

  def _loadChunk(self, chunkIdx):
    start = chunkIdx * self.CHUNK_SIZE
    end = min(start + self.CHUNK_SIZE, self.nbFrames)
    n = end - start
    nbAnimals = len(self.animals)
    head = np.full((nbAnimals, n, 2), np.nan, dtype=np.float32)
    tail = np.full((nbAnimals, n, self.nbTailPoints, 2), np.nan, dtype=np.float32)
    heading = np.full((nbAnimals, n), np.nan, dtype=np.float32)
    proba = np.full((nbAnimals, n), np.nan, dtype=np.float32)
    with h5py.File(self.path, 'r') as results:
      for k, path in enumerate(self._perFramePaths):
        group = results[path]
        headPos = group['HeadPos'][start:end]
        head[k, :len(headPos), 0] = headPos['X']
        head[k, :len(headPos), 1] = headPos['Y']
        if self.nbTailPoints and 'TailPosX' in group and 'TailPosY' in group:
          for coord, name in enumerate(('TailPosX', 'TailPosY')):
            data = group[name][start:end]
            columns = self._columns(group[name])[:self.nbTailPoints]
            tail[k, :len(data), :len(columns), coord] = np.stack([data[column] for column in columns], axis=-1)
        if 'Heading' in group:
          data = group['Heading'][start:end]
          heading[k, :len(data)] = data
        if 'probabilityGoodDetection' in group:
          data = group['probabilityGoodDetection'][start:end]
          proba[k, :len(data)] = data
    return head, tail, heading, proba

  def frameData(self, dataIdx):
    """Returns (head, tail, heading, proba, inBout) for all animals at index dataIdx (= frame - firstFrame)."""
    chunkIdx, offset = divmod(dataIdx, self.CHUNK_SIZE)
    if chunkIdx in self._chunks:
      self._chunks.move_to_end(chunkIdx)
    else:
      self._chunks[chunkIdx] = self._loadChunk(chunkIdx)
      while len(self._chunks) > self.MAX_CACHED_CHUNKS:
        self._chunks.popitem(last=False)
    head, tail, heading, proba = self._chunks[chunkIdx]
    return head[:, offset], tail[:, offset], heading[:, offset], proba[:, offset], self.inBout[:, dataIdx]


class VideoReader:
  def __init__(self, path):
    self.path = path
    self._cap = cv2.VideoCapture(path)
    self.width = int(self._cap.get(cv2.CAP_PROP_FRAME_WIDTH))
    self.height = int(self._cap.get(cv2.CAP_PROP_FRAME_HEIGHT))
    self.frameCount = int(self._cap.get(cv2.CAP_PROP_FRAME_COUNT))
    self.fps = self._cap.get(cv2.CAP_PROP_FPS) or 25.
    self._nextFrame = 0
    self._last = None  # (frameIdx, image)

  def isOpened(self):
    return self._cap.isOpened()

  def read(self, frameIdx):
    if self._last is not None and self._last[0] == frameIdx:
      return self._last[1].copy()
    if frameIdx != self._nextFrame:  # reading sequentially is faster (and more reliable) than seeking
      self._cap.set(cv2.CAP_PROP_POS_FRAMES, frameIdx)
    ret, img = self._cap.read()
    if not ret or img is None:
      self._nextFrame = -1
      img = np.zeros((max(self.height, 1), max(self.width, 1), 3), np.uint8)
      cv2.putText(img, f'Could not read video frame {frameIdx}', (20, 40), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 0, 255), 2)
    else:
      self._nextFrame = frameIdx + 1
      if img.ndim == 2:
        img = cv2.cvtColor(img, cv2.COLOR_GRAY2BGR)
    self._last = (frameIdx, img)
    return img.copy()

  def release(self):
    self._cap.release()


# ---------------------------------------------------------------------------------------------------------------------
# Drawing
# ---------------------------------------------------------------------------------------------------------------------

def drawTracking(img, results, frameData, opts):
  """Draws the tracking points (same look as ZebraZoom's validation video) and the probabilities. Returns stats."""
  head, tail, heading, proba, inBout = frameData
  size = opts['pointSize']
  mode = opts['pointsMode']  # 2: All, 1: Minimal, 0: None (same ids as in ZebraZoom)
  minimal = mode == 1
  labels = []
  shown = 0
  for k, (wellIdx, animalIdx) in enumerate(results.animals):
    if opts['animalFilter'] >= 0 and animalIdx != opts['animalFilter']:
      continue
    if opts['onlyDuringBouts'] and not inBout[k]:
      continue
    hxRaw, hyRaw = float(head[k, 0]), float(head[k, 1])
    if not (math.isfinite(hxRaw) and math.isfinite(hyRaw)):
      continue
    if opts['hideOrigin'] and hxRaw == 0 and hyRaw == 0:
      continue
    p = float(proba[k])
    if opts['minProbability'] is not None and not (math.isfinite(p) and p >= opts['minProbability']):
      continue
    offX, offY = results.wellOffsets[wellIdx]
    x, y = hxRaw + offX, hyRaw + offY
    cm = results.colorModif[animalIdx]
    animalColor = (0 + cm[0], 255 - cm[1], 0 + cm[2])
    shown += 1

    if opts['showIdentities']:
      cv2.putText(img, str(animalIdx), (int(x + 10), int(y + 10)), cv2.FONT_HERSHEY_SIMPLEX, 1, animalColor, 2)

    headRadius = size + (0 if minimal else 2)
    if mode:
      angle = float(heading[k])
      if opts['showHeading'] and math.isfinite(angle):
        cv2.line(img, (int(x), int(y)), (int(x + 20 * math.cos(angle)), int(y + 20 * math.sin(angle))), (255, 0, 0), size)
      cv2.circle(img, (int(x), int(y)), headRadius, (0, 100, 255), -1)
      points = [(hxRaw, hyRaw)] + [(float(px), float(py)) for px, py in tail[k]]
      last = len(points) - 1
      for m in ((0, last) if minimal else range(len(points))):
        px, py = points[m]
        if not (math.isfinite(px) and math.isfinite(py)) or (opts['hideOrigin'] and px == 0 and py == 0):
          continue
        if m == last:
          radius, color = size + (0 if minimal else 2), (0, 255, 0)
        else:
          radius, color = size, animalColor
        cv2.circle(img, (int(px + offX), int(py + offY)), radius, color, -1)

    if opts['showProbability'] and math.isfinite(p):
      labels.append((x, y, headRadius, p))

  # Probabilities are drawn last so that they are on top of every tracking point
  font = cv2.FONT_HERSHEY_SIMPLEX
  scale = opts['fontScale']
  thickness = max(1, int(round(scale * 2)))
  for x, y, radius, p in labels:
    text = f"{p:.{opts['decimals']}f}"
    (_, textHeight), _ = cv2.getTextSize(text, font, scale, thickness)
    position = (int(x + radius + 4), int(y - 12) if opts['showIdentities'] else int(y + textHeight / 2))
    color = (170, 170, 170) if p <= 0 else probabilityColor(p) if opts['colorByValue'] else (255, 255, 255)
    cv2.putText(img, text, position, font, scale, (0, 0, 0), thickness + 2, cv2.LINE_AA)
    cv2.putText(img, text, position, font, scale, color, thickness, cv2.LINE_AA)

  detected = [p for _, _, _, p in labels if p > 0]
  return {'shown': shown, 'detected': len(detected),
          'mean': float(np.mean(detected)) if detected else None,
          'min': min(detected) if detected else None,
          'max': max(detected) if detected else None}


# ---------------------------------------------------------------------------------------------------------------------
# Widgets
# ---------------------------------------------------------------------------------------------------------------------

class VideoView(QWidget):
  """Displays a frame scaled to fit; mouse wheel zooms around the cursor, drag pans, double-click resets."""

  def __init__(self, parent=None):
    super().__init__(parent)
    self._image = None
    self._zoom = 1.
    self._cx = self._cy = 0.
    self._dragPos = None
    self.setFocusPolicy(Qt.NoFocus)
    self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
    self.setMinimumSize(320, 200)

  def setFrame(self, bgr):
    rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
    h, w = rgb.shape[:2]
    if self._image is None or (self._image.width(), self._image.height()) != (w, h):
      self._zoom = 1.
      self._cx, self._cy = w / 2, h / 2
    self._image = QImage(rgb.data, w, h, 3 * w, QImage.Format_RGB888).copy()
    self.update()

  def clear(self):
    self._image = None
    self.update()

  def _scale(self):
    return min(self.width() / self._image.width(), self.height() / self._image.height()) * self._zoom

  def _clampCenter(self):
    s = self._scale()
    for attr, viewLength, imageLength in (('_cx', self.width() / s, self._image.width()), ('_cy', self.height() / s, self._image.height())):
      if viewLength >= imageLength:
        setattr(self, attr, imageLength / 2)
      else:
        setattr(self, attr, min(max(getattr(self, attr), viewLength / 2), imageLength - viewLength / 2))

  def paintEvent(self, event):
    painter = QPainter(self)
    painter.fillRect(self.rect(), QColor(30, 30, 30))
    if self._image is None:
      return
    self._clampCenter()
    s = self._scale()
    iw, ih = self._image.width(), self._image.height()
    ox = self.width() / 2 - self._cx * s
    oy = self.height() / 2 - self._cy * s
    x0, y0 = max(0., -ox / s), max(0., -oy / s)
    x1, y1 = min(float(iw), (self.width() - ox) / s), min(float(ih), (self.height() - oy) / s)
    if x1 <= x0 or y1 <= y0:
      return
    painter.setRenderHint(QPainter.SmoothPixmapTransform, s < 3)  # show crisp pixels when strongly zoomed in
    painter.drawImage(QRectF(ox + x0 * s, oy + y0 * s, (x1 - x0) * s, (y1 - y0) * s), self._image, QRectF(x0, y0, x1 - x0, y1 - y0))

  def wheelEvent(self, event):
    if self._image is None:
      return
    steps = event.angleDelta().y() / 120
    if not steps:
      return
    pos = event.pos()
    self._clampCenter()
    s = self._scale()
    imgX = self._cx + (pos.x() - self.width() / 2) / s
    imgY = self._cy + (pos.y() - self.height() / 2) / s
    self._zoom = min(max(self._zoom * 1.25 ** steps, 1.), 40.)
    s = self._scale()
    self._cx = imgX - (pos.x() - self.width() / 2) / s
    self._cy = imgY - (pos.y() - self.height() / 2) / s
    self.update()

  def mousePressEvent(self, event):
    if event.button() == Qt.LeftButton:
      self._dragPos = event.pos()
      self.setCursor(Qt.ClosedHandCursor)

  def mouseMoveEvent(self, event):
    if self._dragPos is None or self._image is None:
      return
    s = self._scale()
    self._cx -= (event.pos().x() - self._dragPos.x()) / s
    self._cy -= (event.pos().y() - self._dragPos.y()) / s
    self._dragPos = event.pos()
    self.update()

  def mouseReleaseEvent(self, event):
    self._dragPos = None
    self.unsetCursor()

  def mouseDoubleClickEvent(self, event):
    if self._image is not None:
      self._zoom = 1.
      self.update()


class FrameSlider(QSlider):
  """Slider showing in red the range being selected for saving (same as in ZebraZoom)."""

  def __init__(self, *args, **kwargs):
    super().__init__(*args, **kwargs)
    self.firstSaveFrame = None

  def paintEvent(self, event):
    if self.firstSaveFrame is not None:
      style = self.style()
      opt = QStyleOptionSlider()
      self.initStyleOption(opt)
      available = style.pixelMetric(style.PM_SliderSpaceAvailable, opt, self)
      painter = QPainter(self)
      painter.translate(opt.rect.x(), opt.rect.y())
      start = style.sliderPositionFromValue(self.minimum(), self.maximum(), self.firstSaveFrame, available, opt.upsideDown)
      end = style.sliderPositionFromValue(self.minimum(), self.maximum(), self.value(), available, opt.upsideDown)
      painter.fillRect(min(start, end), 0, abs(end - start) + 1, event.rect().height(), QColor('red'))
      painter.end()
    super().paintEvent(event)


class SelectionPage(QWidget):
  resultChosen = pyqtSignal(str)

  def __init__(self, folder, parent=None):
    super().__init__(parent)
    layout = QVBoxLayout(self)

    title = QLabel('Which tracking results would you like to look at?')
    font = title.font()
    font.setPointSize(font.pointSize() + 4)
    font.setBold(True)
    title.setFont(font)
    layout.addWidget(title)
    info = QLabel('Only .h5 results are listed: the detection probability (probabilityGoodDetection) is only stored in .h5 results, '
                  'and only when the tracking was run with "addGoodDetectionProbability": 1.')
    info.setWordWrap(True)
    layout.addWidget(info)

    folderLayout = QHBoxLayout()
    folderLayout.addWidget(QLabel('Results folder:'))
    self._folderEdit = QLineEdit(folder)
    self._folderEdit.editingFinished.connect(self.refresh)
    folderLayout.addWidget(self._folderEdit, stretch=1)
    browseBtn = QPushButton('Browse...')
    browseBtn.clicked.connect(self._browseFolder)
    folderLayout.addWidget(browseBtn)
    refreshBtn = QPushButton('Refresh')
    refreshBtn.clicked.connect(self.refresh)
    folderLayout.addWidget(refreshBtn)
    layout.addLayout(folderLayout)

    self._filterEdit = QLineEdit()
    self._filterEdit.setPlaceholderText('Filter by name...')
    self._filterEdit.setClearButtonEnabled(True)
    self._filterEdit.textChanged.connect(self._applyFilter)
    layout.addWidget(self._filterEdit)

    self._tree = QTreeWidget()
    self._tree.setHeaderLabels(['Name', 'Modified', 'Size'])
    self._tree.setRootIsDecorated(False)
    self._tree.setSelectionMode(QAbstractItemView.SingleSelection)
    self._tree.setSortingEnabled(True)
    self._tree.header().setSectionResizeMode(0, QHeaderView.Stretch)
    self._tree.header().setSectionResizeMode(1, QHeaderView.ResizeToContents)
    self._tree.header().setSectionResizeMode(2, QHeaderView.ResizeToContents)
    self._tree.itemDoubleClicked.connect(lambda item, column: self._openItem(item))
    self._tree.itemSelectionChanged.connect(lambda: self._openBtn.setEnabled(bool(self._tree.selectedItems())))
    layout.addWidget(self._tree, stretch=1)

    buttonsLayout = QHBoxLayout()
    otherBtn = QPushButton('Open another .h5 file...')
    otherBtn.clicked.connect(self._openOtherFile)
    buttonsLayout.addWidget(otherBtn)
    buttonsLayout.addStretch(1)
    self._openBtn = QPushButton('View selected result')
    self._openBtn.setEnabled(False)
    self._openBtn.setDefault(True)
    self._openBtn.clicked.connect(lambda: self._tree.selectedItems() and self._openItem(self._tree.selectedItems()[0]))
    buttonsLayout.addWidget(self._openBtn)
    layout.addLayout(buttonsLayout)

    self.refresh()

  def folder(self):
    return self._folderEdit.text().strip()

  def _browseFolder(self):
    folder = QFileDialog.getExistingDirectory(self, 'Select the folder containing the results', self.folder() or os.path.expanduser('~'))
    if folder:
      self._folderEdit.setText(os.path.normpath(folder))
      self.refresh()

  def _openOtherFile(self):
    path, _ = QFileDialog.getOpenFileName(self, 'Select a ZebraZoom results file', self.folder() or os.path.expanduser('~'), 'ZebraZoom results (*.h5)')
    if path:
      self.resultChosen.emit(os.path.normpath(path))

  def refresh(self):
    self._tree.clear()
    folder = self.folder()
    if not os.path.isdir(folder):
      return
    items = []
    for name in os.listdir(folder):
      path = os.path.join(folder, name)
      if not name.lower().endswith('.h5') or not os.path.isfile(path):
        continue
      stat = os.stat(path)
      item = _SortableItem([name, datetime.datetime.fromtimestamp(stat.st_mtime).strftime('%Y-%m-%d %H:%M:%S'), f'{stat.st_size / 1e6:.1f} MB'])
      item.setData(0, Qt.UserRole, path)
      item.setData(1, Qt.UserRole, stat.st_mtime)
      item.setData(2, Qt.UserRole, stat.st_size)
      item.setTextAlignment(2, Qt.AlignRight | Qt.AlignVCenter)
      items.append(item)
    self._tree.addTopLevelItems(items)
    self._tree.sortByColumn(1, Qt.DescendingOrder)  # most recent first
    self._applyFilter(self._filterEdit.text())

  def _applyFilter(self, text):
    text = text.lower()
    for idx in range(self._tree.topLevelItemCount()):
      item = self._tree.topLevelItem(idx)
      item.setHidden(text not in item.text(0).lower())

  def _openItem(self, item):
    self.resultChosen.emit(item.data(0, Qt.UserRole))


class _SortableItem(QTreeWidgetItem):
  def __lt__(self, other):
    column = self.treeWidget().sortColumn()
    if column in (1, 2):
      return self.data(column, Qt.UserRole) < other.data(column, Qt.UserRole)
    return self.text(column).lower() < other.text(column).lower()


class ViewerPage(QWidget):
  backRequested = pyqtSignal()

  def __init__(self, parent=None):
    super().__init__(parent)
    self._results = None
    self._video = None
    self._framesAreAbsolute = True
    self._advancing = False

    layout = QVBoxLayout(self)

    topLayout = QHBoxLayout()
    backBtn = QPushButton('< Choose another result')
    backBtn.setFocusPolicy(Qt.NoFocus)
    backBtn.clicked.connect(self.backRequested.emit)
    topLayout.addWidget(backBtn)
    self._titleLabel = QLabel()
    self._titleLabel.setTextInteractionFlags(Qt.TextSelectableByMouse)
    self._titleLabel.setWordWrap(True)
    topLayout.addWidget(self._titleLabel, stretch=1)
    layout.addLayout(topLayout)

    self._view = VideoView()
    layout.addWidget(self._view, stretch=1)

    self._statsLabel = QLabel()
    layout.addWidget(self._statsLabel)

    sliderLayout = QHBoxLayout()
    self._slider = FrameSlider(Qt.Horizontal)
    self._slider.setFocusPolicy(Qt.StrongFocus)
    self._slider.setPageStep(50)
    self._slider.valueChanged.connect(self._sliderChanged)
    sliderLayout.addWidget(self._slider)
    self._frameSpinbox = QSpinBox()
    self._frameSpinbox.setMinimumWidth(80)
    self._frameSpinbox.valueChanged.connect(lambda value: self._timer.stop() or self._slider.setValue(value))
    self._frameSpinbox.editingFinished.connect(self._slider.setFocus)
    sliderLayout.addWidget(self._frameSpinbox)
    self._playBtn = QPushButton()
    self._playBtn.setFocusPolicy(Qt.NoFocus)
    self._playIcon = self.style().standardIcon(self.style().SP_MediaPlay)
    self._pauseIcon = self.style().standardIcon(self.style().SP_MediaPause)
    self._playBtn.setIcon(self._playIcon)
    self._playBtn.clicked.connect(self._togglePlay)
    sliderLayout.addWidget(self._playBtn)
    sliderLayout.addWidget(QLabel('Playback FPS:'))
    self._fpsSpinbox = QSpinBox()
    self._fpsSpinbox.setRange(0, 1000)
    self._fpsSpinbox.setSpecialValueText('Max')
    self._fpsSpinbox.setToolTip('0 (Max) plays as fast as possible, like ZebraZoom does')
    self._fpsSpinbox.valueChanged.connect(self._updateTimerInterval)
    self._fpsSpinbox.editingFinished.connect(self._slider.setFocus)
    sliderLayout.addWidget(self._fpsSpinbox)
    layout.addLayout(sliderLayout)

    shortcutsLabel = QLabel('Left Arrow, Right Arrow, Page Up, Page Down, Home and End keys can be used to navigate through the video; '
                            'Space plays/pauses. Mouse wheel on the video zooms, drag pans, double-click resets the zoom.')
    shortcutsLabel.setWordWrap(True)
    layout.addWidget(shortcutsLabel)

    # Same controls as in ZebraZoom's validation video window
    pointsLayout = QHBoxLayout()
    pointsLayout.addWidget(QLabel('Tracking points:'))
    self._pointsGroup = QButtonGroup(self)
    for label, buttonId in (('All', 2), ('Minimal', 1), ('None', 0)):
      button = QRadioButton(label)
      button.setFocusPolicy(Qt.NoFocus)
      self._pointsGroup.addButton(button, buttonId)
      pointsLayout.addWidget(button)
    self._pointsGroup.buttonToggled.connect(lambda button, checked: checked and self._refresh())
    pointsLayout.addWidget(QLabel('Size:'))
    self._sizeSpinbox = QSpinBox()
    self._sizeSpinbox.setMinimum(1)
    self._sizeSpinbox.valueChanged.connect(self._refresh)
    self._sizeSpinbox.editingFinished.connect(self._slider.setFocus)
    pointsLayout.addWidget(self._sizeSpinbox)
    self._contrastCheckbox = self._checkbox('Contrast', pointsLayout)
    self._headingCheckbox = self._checkbox('Heading', pointsLayout)
    self._identitiesCheckbox = self._checkbox('Show Identities', pointsLayout)
    self._saveBtn = QPushButton('Start save')
    self._saveBtn.setFocusPolicy(Qt.NoFocus)
    self._saveBtn.clicked.connect(self._saveVideo)
    pointsLayout.addWidget(self._saveBtn)
    pointsLayout.addStretch(1)
    layout.addLayout(pointsLayout)

    # Probability display controls
    probaLayout = QHBoxLayout()
    self._probaCheckbox = self._checkbox('Show probability', probaLayout, checked=True)
    probaLayout.addWidget(QLabel('Text size:'))
    self._fontSpinbox = QDoubleSpinBox()
    self._fontSpinbox.setRange(0.2, 4.)
    self._fontSpinbox.setSingleStep(0.1)
    self._fontSpinbox.setValue(0.5)
    self._fontSpinbox.valueChanged.connect(self._refresh)
    self._fontSpinbox.editingFinished.connect(self._slider.setFocus)
    probaLayout.addWidget(self._fontSpinbox)
    probaLayout.addWidget(QLabel('Decimals:'))
    self._decimalsSpinbox = QSpinBox()
    self._decimalsSpinbox.setRange(1, 4)
    self._decimalsSpinbox.setValue(2)
    self._decimalsSpinbox.valueChanged.connect(self._refresh)
    self._decimalsSpinbox.editingFinished.connect(self._slider.setFocus)
    probaLayout.addWidget(self._decimalsSpinbox)
    self._colorCheckbox = self._checkbox('Color by value', probaLayout, checked=True)
    self._colorCheckbox.setToolTip(f'Red for a probability <= {PROBA_COLOR_LOW:g}, yellow halfway, green for >= {PROBA_COLOR_HIGH:g}')
    probaLayout.addStretch(1)
    layout.addLayout(probaLayout)

    filterLayout = QHBoxLayout()
    filterLayout.addWidget(QLabel('Animal:'))
    self._animalSpinbox = QSpinBox()
    self._animalSpinbox.setSpecialValueText('All')
    self._animalSpinbox.setMinimumWidth(80)
    self._animalSpinbox.setToolTip('Only display this animal number (in every well)')
    self._animalSpinbox.valueChanged.connect(self._refresh)
    self._animalSpinbox.editingFinished.connect(self._slider.setFocus)
    filterLayout.addWidget(self._animalSpinbox)
    self._boutsCheckbox = self._checkbox('Only during bouts', filterLayout)
    self._boutsCheckbox.setToolTip('ZebraZoom only draws animals during their detected bouts')
    self._originCheckbox = self._checkbox('Hide points at (0, 0)', filterLayout, checked=True)
    self._originCheckbox.setToolTip('Points at exactly (0, 0) usually mean "no position" (e.g. an empty animal slot)')
    self._minProbaCheckbox = self._checkbox('Only show detections with probability >=', filterLayout)
    self._minProbaCheckbox.setToolTip('Hides the tracking points and the probability of every animal whose probability is below this value in the current frame')
    self._minProbaSpinbox = QDoubleSpinBox()
    self._minProbaSpinbox.setRange(0., 1.)
    self._minProbaSpinbox.setDecimals(3)
    self._minProbaSpinbox.setSingleStep(0.05)
    self._minProbaSpinbox.setValue(0.5)
    self._minProbaSpinbox.setMinimumWidth(80)
    self._minProbaSpinbox.setEnabled(False)
    self._minProbaCheckbox.toggled.connect(self._minProbaSpinbox.setEnabled)
    self._minProbaSpinbox.valueChanged.connect(self._refresh)
    self._minProbaSpinbox.editingFinished.connect(self._slider.setFocus)
    filterLayout.addWidget(self._minProbaSpinbox)
    filterLayout.addStretch(1)
    layout.addLayout(filterLayout)

    legend = QLabel('The number next to each animal is the detection probability stored for that animal in that frame '
                    '(for YOLO tracking: the YOLO confidence). A grey 0.00 means no detection was assigned to that animal in that frame.')
    legend.setWordWrap(True)
    layout.addWidget(legend)

    self._timer = QTimer(self)
    self._timer.timeout.connect(self._nextFrame)
    self._updateTimerInterval()

    QShortcut(QKeySequence(Qt.Key_Space), self, self._togglePlay)

  def _checkbox(self, label, layout, checked=False):
    checkbox = QCheckBox(label)
    checkbox.setFocusPolicy(Qt.NoFocus)
    checkbox.setChecked(checked)
    checkbox.toggled.connect(self._refresh)
    layout.addWidget(checkbox)
    return checkbox

  # --- loading ---

  def load(self, results, video, framesAreAbsolute):
    self.unload()
    self._results = results
    self._video = video
    self._framesAreAbsolute = framesAreAbsolute

    widgets = (self._slider, self._frameSpinbox, self._sizeSpinbox, self._animalSpinbox, self._contrastCheckbox,
               self._headingCheckbox, self._identitiesCheckbox, *self._pointsGroup.buttons())
    blocked = [widget.blockSignals(True) for widget in widgets]
    self._sizeSpinbox.setValue(int(results.setting("trackingPointSizeDisplay")))
    self._contrastCheckbox.setChecked(bool(results.setting("outputValidationVideoContrastImprovement")))
    self._headingCheckbox.setChecked(bool(results.setting("validationVideoPlotHeading")))
    self._identitiesCheckbox.setChecked(bool(results.setting("validationVideoPlotAnimalNumber")))
    # Without the original video, ZebraZoom shows the validation video in which the points are already drawn
    pointsMode = 0 if not framesAreAbsolute else 1 if results.setting("plotOnlyOneTailPointForVisu") else 2
    self._pointsGroup.button(pointsMode).setChecked(True)
    self._animalSpinbox.setRange(-1, results.maxAnimalIdx)
    self._animalSpinbox.setValue(-1)

    first = results.firstFrame
    last = min(results.lastFrame, first + results.nbFrames - 1)
    if video.frameCount > 0:
      last = min(last, video.frameCount - 1 if framesAreAbsolute else first + video.frameCount - 1)
    last = max(last, first)
    self._slider.setRange(first, last)
    self._frameSpinbox.setRange(first, last)
    self._slider.setValue(first)
    self._frameSpinbox.setValue(first)
    self._slider.firstSaveFrame = None
    self._saveBtn.setText('Start save')
    for widget, wasBlocked in zip(widgets, blocked):
      widget.blockSignals(wasBlocked)

    probaInfo = (f'probability stored for {results.probabilityAnimalsCount}/{len(results.animals)} animals' if results.hasProbability
                 else 'NO probability stored in this file')
    self._titleLabel.setText(f'<b>{os.path.basename(results.path)}</b> &nbsp; | &nbsp; video: {video.path} &nbsp; | &nbsp; '
                             f'frames {first}-{last} &nbsp; | &nbsp; {len(results.wellOffsets)} well(s), '
                             f'{len(results.animals)} animal slot(s) &nbsp; | &nbsp; {probaInfo}')
    self._refresh()
    QTimer.singleShot(0, self._slider.setFocus)
    self._timer.start()  # ZebraZoom starts playing the video when the window opens

  def unload(self):
    self._timer.stop()
    self._playBtn.setIcon(self._playIcon)
    if self._video is not None:
      self._video.release()
    self._video = None
    self._results = None
    self._view.clear()

  # --- playback ---

  def _updateTimerInterval(self):
    fps = self._fpsSpinbox.value()
    self._timer.setInterval(int(round(1000 / fps)) if fps > 0 else 1)

  def _togglePlay(self):
    if self._results is None:
      return
    if self._timer.isActive():
      self._timer.stop()
      self._playBtn.setIcon(self._playIcon)
    else:
      if self._slider.value() >= self._slider.maximum():
        self._slider.setValue(self._slider.minimum())
      self._timer.start()
      self._playBtn.setIcon(self._pauseIcon)

  def _nextFrame(self):
    if self._slider.value() >= self._slider.maximum():
      self._timer.stop()
      self._playBtn.setIcon(self._playIcon)
      return
    self._advancing = True
    self._slider.setValue(self._slider.value() + 1)
    self._advancing = False

  def _sliderChanged(self, value):
    if not self._advancing and self._timer.isActive():  # any manual navigation stops the playback, as in ZebraZoom
      self._timer.stop()
    self._playBtn.setIcon(self._pauseIcon if self._timer.isActive() else self._playIcon)
    blocked = self._frameSpinbox.blockSignals(True)
    self._frameSpinbox.setValue(value)
    self._frameSpinbox.blockSignals(blocked)
    self._refresh()

  # --- rendering ---

  def _options(self):
    return {
      'pointsMode': self._pointsGroup.checkedId(),
      'pointSize': self._sizeSpinbox.value(),
      'showHeading': self._headingCheckbox.isChecked(),
      'showIdentities': self._identitiesCheckbox.isChecked(),
      'showProbability': self._probaCheckbox.isChecked(),
      'fontScale': self._fontSpinbox.value(),
      'decimals': self._decimalsSpinbox.value(),
      'colorByValue': self._colorCheckbox.isChecked(),
      'animalFilter': self._animalSpinbox.value(),
      'onlyDuringBouts': self._boutsCheckbox.isChecked(),
      'hideOrigin': self._originCheckbox.isChecked(),
      'minProbability': self._minProbaSpinbox.value() if self._minProbaCheckbox.isChecked() else None,
    }

  def _renderFrame(self, frame):
    results = self._results
    img = self._video.read(frame if self._framesAreAbsolute else frame - results.firstFrame)
    if self._contrastCheckbox.isChecked():
      img = improveContrast(img, results.setting("outputValidationVideoContrastImprovementQuartile"))
    stats = drawTracking(img, results, results.frameData(frame - results.firstFrame), self._options())
    h, w = img.shape[:2]
    if w > 100 and h > 100:
      cv2.putText(img, str(frame), (int(w - 110), int(h - 30)), cv2.FONT_HERSHEY_SIMPLEX, 1, (0, 255, 0))
    return img, stats

  def _refresh(self, *args):
    if self._results is None:
      return
    frame = self._slider.value()
    img, stats = self._renderFrame(frame)
    self._view.setFrame(img)
    text = f'Frame {frame}: {stats["shown"]} animal(s) displayed, {stats["detected"]} with a detection (probability > 0)'
    if stats['detected']:
      text += f' | probability mean {stats["mean"]:.3f}, min {stats["min"]:.3f}, max {stats["max"]:.3f}'
    self._statsLabel.setText(text)

  # --- saving ---

  def _saveVideo(self):
    if self._results is None:
      return
    if self._slider.firstSaveFrame is None:
      self._slider.firstSaveFrame = self._slider.value()
      self._timer.stop()
      self._playBtn.setIcon(self._playIcon)
      self._saveBtn.setText('End save')
      self._slider.update()
      return

    firstSaveFrame, lastSaveFrame = sorted((self._slider.firstSaveFrame, self._slider.value()))
    defaultName = os.path.splitext(os.path.basename(self._results.path))[0] + f'_withProbabilities_{firstSaveFrame}-{lastSaveFrame}.avi'
    filename, _ = QFileDialog.getSaveFileName(self, 'Save video', os.path.join(os.path.expanduser('~'), defaultName), 'AVI video (*.avi)')
    self._slider.firstSaveFrame = None
    self._saveBtn.setText('Start save')
    self._slider.update()
    if not filename:
      return

    img, _ = self._renderFrame(firstSaveFrame)
    height, width = img.shape[:2]
    writer = cv2.VideoWriter(filename, cv2.VideoWriter_fourcc(*'MJPG'), self._video.fps, (width, height))
    if not writer.isOpened():
      QMessageBox.critical(self, 'Cannot save video', f'Could not create {filename}.')
      return
    progress = QProgressDialog('Saving video...', 'Cancel', firstSaveFrame, lastSaveFrame, self)
    progress.setWindowTitle('Saving Video')
    progress.setWindowModality(Qt.ApplicationModal)
    progress.setMinimumDuration(0)
    progress.setAutoClose(False)
    try:
      for frame in range(firstSaveFrame, lastSaveFrame + 1):
        progress.setValue(frame)
        progress.setLabelText(f'Saving frame {frame}...')
        if progress.wasCanceled():
          break
        writer.write(self._renderFrame(frame)[0])
    finally:
      writer.release()
      progress.close()
    self._refresh()


class MainWindow(QMainWindow):
  def __init__(self, folder):
    super().__init__()
    self.setWindowTitle('ZebraZoom - tracking probability viewer')
    self._stack = QStackedWidget()
    self.setCentralWidget(self._stack)
    self._selection = SelectionPage(folder)
    self._selection.resultChosen.connect(self.openResults)
    self._stack.addWidget(self._selection)
    self._viewer = ViewerPage()
    self._viewer.backRequested.connect(self._back)
    self._stack.addWidget(self._viewer)

  def _back(self):
    self._viewer.unload()
    self._stack.setCurrentWidget(self._selection)
    self._selection.refresh()

  def openResults(self, path):
    QApplication.setOverrideCursor(Qt.WaitCursor)
    try:
      results = TrackingResults(path)
    except Exception as e:
      QApplication.restoreOverrideCursor()
      QMessageBox.critical(self, 'Cannot read the results', f'Could not read {path}:\n\n{e}')
      return
    QApplication.restoreOverrideCursor()

    videoPath, framesAreAbsolute = resolveVideoPath(path, results.attrs, results.config)
    if videoPath is None:
      storedPath = results.attrs.get('pathToOriginalVideo', '')
      message = (f'The video used for this tracking could not be found:\n{storedPath}\n\nWould you like to locate it?' if storedPath
                 else 'The video used for this tracking could not be found. Would you like to locate the original video?')
      if QMessageBox.question(self, 'Video not found', message) != QMessageBox.Yes:
        return
      startFolder = os.path.dirname(path)
      videoPath, _ = QFileDialog.getOpenFileName(self, 'Select the video used for the tracking', startFolder, 'Videos (*.avi *.mp4 *.mov *.mkv *.mpg *.mpeg *.wmv *.m4v);;All files (*.*)')
      if not videoPath:
        return
      framesAreAbsolute = True  # it's the original video: frame numbers are the ones stored in the results
    video = VideoReader(videoPath)
    if not video.isOpened():
      QMessageBox.critical(self, 'Cannot read the video', f'Could not open the video:\n{videoPath}')
      return

    if not results.hasProbability:
      QMessageBox.warning(self, 'No probability in this file',
                          'This result does not contain any probabilityGoodDetection data (the tracking was run without '
                          '"addGoodDetectionProbability": 1). The tracking will be displayed without probabilities.')

    QApplication.setOverrideCursor(Qt.WaitCursor)
    try:
      self._viewer.load(results, video, framesAreAbsolute)
    finally:
      QApplication.restoreOverrideCursor()
    self._stack.setCurrentWidget(self._viewer)

  def closeEvent(self, event):
    self._viewer.unload()
    try:
      QSettings('ZebraZoom', 'trackingProbabilityViewer').setValue('folder', self._selection.folder())
    except Exception:
      pass
    super().closeEvent(event)


def main():
  QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
  QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
  app = QApplication(sys.argv)

  argument = sys.argv[1] if len(sys.argv) > 1 else None
  folder = None
  if argument and os.path.isdir(argument):
    folder = os.path.abspath(argument)
  elif argument and os.path.isfile(argument):
    folder = os.path.dirname(os.path.abspath(argument))
  if folder is None:
    try:
      saved = QSettings('ZebraZoom', 'trackingProbabilityViewer').value('folder', '')
    except Exception:
      saved = ''
    folder = saved if saved and os.path.isdir(saved) else findDefaultZZoutputFolder()

  window = MainWindow(folder)
  available = app.primaryScreen().availableGeometry()
  window.resize(min(1300, int(available.width() * 0.95)), min(900, int(available.height() * 0.9)))
  window.show()
  if argument and os.path.isfile(argument):
    QTimer.singleShot(0, lambda: window.openResults(os.path.abspath(argument)))
  sys.exit(app.exec_())


if __name__ == '__main__':
  main()
