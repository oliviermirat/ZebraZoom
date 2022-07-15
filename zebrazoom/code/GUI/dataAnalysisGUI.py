import math
import os
import sys
import pickle
import webbrowser

import json
import pandas as pd
import seaborn as sns
from matplotlib.figure import Figure
from matplotlib.backends.backend_qtagg import FigureCanvas

from PyQt5.QtCore import pyqtSignal, Qt, QAbstractTableModel, QDir, QEvent, QItemSelectionModel, QModelIndex, QObject, QPoint, QPointF, QRect, QRectF, QSize, QSizeF, QSortFilterProxyModel, QStringListModel, QUrl
from PyQt5.QtGui import QColor, QDesktopServices, QFont, QFontMetrics, QIntValidator, QPainter, QPixmap, QPolygon, QPolygonF, QTransform
from PyQt5.QtWidgets import QAction, QAbstractItemView, QApplication, QComboBox, QCompleter, QDoubleSpinBox, QFileDialog, QFileSystemModel, QFrame, QGridLayout, QHeaderView, QHBoxLayout, QLabel, QListView, QMessageBox, QSpacerItem, QTextEdit, QToolButton, QWidget, QPushButton, QLineEdit, QCheckBox, QVBoxLayout, QRadioButton, QButtonGroup, QScrollArea, QTableView, QToolTip, QTreeView
PYQT6 = False

import zebrazoom.videoFormatConversion.zzVideoReading as zzVideoReading
import zebrazoom.code.paths as paths
import zebrazoom.code.util as util
from zebrazoom.dataAnalysis.dataanalysis.populationComparaison import populationComparaison
from zebrazoom.dataAnalysis.datasetcreation.createDataFrame import createDataFrame
from zebrazoom.dataAnalysis.datasetcreation.generatePklDataFileForVideo import generatePklDataFileForVideo


class _ExperimentFilesModel(QFileSystemModel):
  def __init__(self):
    super().__init__()
    self.setReadOnly(False)
    self.setNameFilterDisables(False)
    self.setNameFilters(("*.xls", "*.xlsx"))

  def data(self, index, role=Qt.ItemDataRole.DisplayRole):
    data = super().data(index, role=role)
    if role == Qt.ItemDataRole.EditRole:
      return os.path.splitext(data)[0]
    return data

  def setData(self, index, value, role=None):
    extension = os.path.splitext(self.data(index))[1]
    return super().setData(index, "%s%s" % (value, extension), role=role)


class _ExperimentTreeView(QTreeView):
  def __init__(self):
    super().__init__()
    self.sizeHint = lambda: QSize(150, 1)
    self.header().setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
    self.setRootIsDecorated(False)

  def resizeEvent(self, evt):
    super().resizeEvent(evt)
    self.setColumnWidth(0, evt.size().width())

  def flags(self, index):
    return super().flags(index) | Qt.ItemFlag.ItemIsEditable


class _WellsSelectionLabel(QLabel):
  wellsChanged = pyqtSignal(set)

  def __init__(self):
    super().__init__()
    self._wells = set()
    self._hoveredWells = set()
    self._wellPositions = None
    self._wellInfos = None
    self._size = None
    self._originalPixmap = None
    self._clickedPosition = None
    self._hoveredPosition = None
    self._expandExisting = False
    self.wellShape = None

  def setWellPositions(self, wellPositions):
    self.setMouseTracking(wellPositions is not None)
    self._wellPositions = wellPositions
    self._wellInfos = None

  def setWellInfos(self, wellInfos):
    self._wellInfos = wellInfos
    self.update()

  def setOriginalPixmap(self, pixmap):
    self._originalPixmap = pixmap
    self._wells.clear()
    if pixmap is not None:
      self.setMaximumSize(pixmap.size())
      self.setMinimumSize(300, 300)
      self.setPixmap(pixmap)
      self.hide()
      self.show()
    self._updateImage()

  def mouseMoveEvent(self, evt):
    app = QApplication.instance()
    if not self._wellPositions:
      return
    oldHovered = self._hoveredWells
    if evt.buttons() == Qt.MouseButton.LeftButton:
      self._hoveredPosition = evt.pos()
    if self.wellShape == 'rectangle':
      def test_func(shape, x, y, width, height):
        if isinstance(shape, QPoint):
          return QRect(x, y, width, height).contains(shape)
        else:
          assert isinstance(shape, QRect)
          return QRect(x, y, width, height).intersects(shape)
    else:
      assert self.wellShape == 'circle'
      def test_func(shape, x, y, width, height):
        if isinstance(shape, QPoint):
          radius = width / 2
          centerX = x + radius
          centerY = y + radius
          dx = abs(shape.x() - centerX)
          if dx > radius:
            return False
          dy = abs(shape.y() - centerY)
          if dy > radius:
            return False
          if dx + dy <= radius:
            return True
          return dx * dx + dy * dy <= radius * radius
        else:
          radius = width / 2
          centerX = x + radius
          centerY = y + radius
          Dx = max(shape.x(), min(centerX, shape.x() + shape.width())) - centerX
          Dy = max(shape.y(), min(centerY, shape.y() + shape.height())) - centerY
          return (Dx ** 2 + Dy ** 2) <= radius ** 2

    hoveredWells = set()
    for idx, positions in enumerate(self._wellPositions):
      point = self._transformToOriginal.map(evt.pos())
      if test_func(point if self._clickedPosition is None else QRect(self._transformToOriginal.map(self._clickedPosition), point).normalized(), *positions):
        hoveredWells.add(idx)
    self._hoveredWells = hoveredWells
    if self._hoveredWells != oldHovered or self._hoveredPosition is not None:
      self.update()

  def mousePressEvent(self, evt):
    if not self._wellPositions:
      return
    self._expandExisting = evt.modifiers() & Qt.KeyboardModifier.ControlModifier
    self._clickedPosition = evt.pos()
    if not self._expandExisting:
      if self._hoveredWells:
        self._wells = self._hoveredWells.copy()
      else:
        self._wells.clear()
      self.wellsChanged.emit(self._wells)
    self.update()

  def mouseReleaseEvent(self, evt):
    if self._expandExisting:
      self._wells ^= self._hoveredWells
    else:
      self._wells = self._hoveredWells.copy()
    self.wellsChanged.emit(self._wells)
    self._hoveredWells.clear()
    self._expandExisting = False
    self._clickedPosition = None
    self._hoveredPosition = None
    self.update()
    self.mouseMoveEvent(evt)

  def enterEvent(self, evt):
    QApplication.setOverrideCursor(Qt.CursorShape.CrossCursor)

  def leaveEvent(self, evt):
    QApplication.restoreOverrideCursor()
    self._hoveredWells.clear()
    self.update()

  def _elideText(self, text, rect):
    if not text:
      return text
    fm = QFontMetrics(QFont())
    elidedText = fm.elidedText(text, Qt.TextElideMode.ElideRight, rect.width())
    if elidedText:
      return elidedText
    return text[0]

  def paintEvent(self, evt):
    super().paintEvent(evt)
    app = QApplication.instance()
    if not self._wellPositions:
      return
    qp = QPainter()
    qp.begin(self)
    factory = qp.drawRect if self.wellShape == 'rectangle' else qp.drawEllipse
    for idx, positions in enumerate(self._wellPositions):
      if idx in self._wells:
        if idx in self._hoveredWells and self._expandExisting:
          qp.setPen(QColor(0, 0, 255))
        else:
          qp.setPen(QColor(255, 0, 0))
      elif idx in self._hoveredWells:
        qp.setPen(QColor(0, 255, 0))
      else:
        qp.setPen(QColor(0, 0, 255))
      rect = self._transformFromOriginal.map(QPolygon(QRect(*positions))).boundingRect()
      font = QFont()
      font.setPointSize(16)
      font.setWeight(QFont.Weight.Bold)
      qp.setFont(font)
      qp.drawText(rect, Qt.AlignmentFlag.AlignCenter, str(idx))
      factory(rect)
      if self._wellInfos is not None:
        rect.adjust(10, rect.height() // 2, -10, -10)
        qp.setFont(QFont())
        qp.setClipping(True)
        qp.setClipRect(rect)
        qp.drawText(rect, Qt.AlignmentFlag.AlignCenter, "\n".join(map(lambda text: self._elideText(text, rect), self._wellInfos[idx])))
        qp.setClipping(False)
    if self._hoveredPosition is not None and self._clickedPosition is not None:
      qp.setPen(QColor(70, 70, 140))
      qp.setBrush(QColor(127, 127, 255, 70))
      qp.drawRect(QRect(self._clickedPosition, self._hoveredPosition))
    qp.end()

  def _updateImage(self):
    self._size = self.size()
    if self._originalPixmap is None:
      self.clear()
      return
    originalRect = QRectF(QPointF(0, 0), QSizeF(self._originalPixmap.size()))
    currentRect = QRectF(QPointF(0, 0), QSizeF(self._size))
    self._transformToOriginal = QTransform()
    QTransform.quadToQuad(QPolygonF((currentRect.topLeft(), currentRect.topRight(), currentRect.bottomLeft(), currentRect.bottomRight())),
                          QPolygonF((originalRect.topLeft(), originalRect.topRight(), originalRect.bottomLeft(), originalRect.bottomRight())),
                          self._transformToOriginal)
    self._transformFromOriginal = QTransform()
    QTransform.quadToQuad(QPolygonF((originalRect.topLeft(), originalRect.topRight(), originalRect.bottomLeft(), originalRect.bottomRight())),
                          QPolygonF((currentRect.topLeft(), currentRect.topRight(), currentRect.bottomLeft(), currentRect.bottomRight())),
                          self._transformFromOriginal)
    scaling = self.devicePixelRatio() if PYQT6 else self.devicePixelRatioF()
    size = self._originalPixmap.size().scaled(self.size(), Qt.AspectRatioMode.KeepAspectRatio)
    img = self._originalPixmap.scaled(int(size.width() * scaling), int(size.height() * scaling))
    img.setDevicePixelRatio(scaling)
    self.setPixmap(img)
    blocked = self.blockSignals(True)
    self.setMinimumSize(size)
    self.setMaximumSize(size)
    self.blockSignals(blocked)

  def resizeEvent(self, evt):
    super().resizeEvent(evt)
    self._updateImage()

  def getWells(self):
    return self._wells if self._wellPositions is not None else {0}

  def totalWells(self):
    return len(self._wellPositions) if self._wellPositions is not None else 1


class _DummyFullSet(object):
  def __contains__(self, item):
    return True


class _ExperimentOrganizationModel(QAbstractTableModel):
  _COLUMN_NAMES = ["path", "trial_id", "fq", "pixelsize", "condition", "genotype", "include"]
  _COLUMN_TITLES = [None, "Video", "FPS", "Pixel Size", "Condition", "Genotype", "Include"]
  _DEFAULT_ZZOUTPUT = paths.getDefaultZZoutputFolder()

  def __init__(self, filename):
    super().__init__()
    self._data = pd.read_excel(filename)
    self._data = self._data.loc[:, ~self._data.columns.str.contains('^Unnamed')]

  def rowCount(self, parent=None):
    return self._data.shape[0]

  def columnCount(self, parent=None):
    return len(self._COLUMN_NAMES)

  def updateNumericValue(self, rows, column, newValue):
    dataColIdx = self._data.columns.get_loc(self._COLUMN_NAMES[column])
    for row in rows:
      self._data.iloc[row, dataColIdx] = float(newValue)
      index = self.index(row, column)
      self.dataChanged.emit(index, index)

  def updateArrayValues(self, rows, column, indices, newValue):
    dataColIdx = self._data.columns.get_loc(self._COLUMN_NAMES[column])
    for row in rows:
      self._data.iloc[row, dataColIdx] = "[%s]" % ", ".join(val.strip() if idx not in indices else str(newValue)
                                                            for idx, val in enumerate(self._data.iloc[row, dataColIdx][1:-1].split(",")))
      index = self.index(row, column)
      self.dataChanged.emit(index, index)

  def data(self, index, role=Qt.ItemDataRole.DisplayRole):
    if index.isValid() and role in (Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole, Qt.ItemDataRole.ToolTipRole):
      return str(self._data.iloc[index.row(), self._data.columns.get_loc(self._COLUMN_NAMES[index.column()])])
    return None

  def headerData(self, col, orientation, role):
    if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
      return self._COLUMN_TITLES[col]
    return None

  def setData(self, index, value, role=None):
    if not index.isValid():
      return False
    self._data.iloc[index.row(), self._data.columns.get_loc(self._COLUMN_NAMES[index.column()])] = value
    self.dataChanged.emit(index, index)
    return True

  def flags(self, index):
    return super().flags(index) if index.column() == 1 else super().flags(index) | Qt.ItemFlag.ItemIsEditable

  def saveFile(self, filename):
    self._data.to_excel(filename, index=False)

  def videoPath(self, row):
    path, folderName = self._data.iloc[row, list(map(self._data.columns.get_loc, self._COLUMN_NAMES[:2]))]
    if path == "defaultZZoutputFolder":
      path = self._DEFAULT_ZZOUTPUT
    return os.path.join(path, folderName)

  def addVideo(self, videoData):
    if os.path.normpath(videoData["path"][0]) == os.path.normpath(self._DEFAULT_ZZOUTPUT):
      videoData["path"][0] = "defaultZZoutputFolder"
    self.beginInsertRows(QModelIndex(), self.rowCount(), self.rowCount())
    self._data = pd.concat([self._data, pd.DataFrame.from_dict(videoData)], ignore_index=True)
    self.endInsertRows()

  def removeSelectedRows(self, idxs):
    self.beginResetModel()
    self._data = self._data.drop(idxs).reset_index(drop=True,)
    self.endResetModel()

  def getFPS(self, rows):
    colIdx = self._data.columns.get_loc("fq")
    return sorted({str(self._data.iloc[row, colIdx]) for row in rows})

  def getPixelSizes(self, rows):
    colIdx = self._data.columns.get_loc("pixelsize")
    return sorted({str(self._data.iloc[row, colIdx]) for row in rows})

  def getExistingConditions(self, rows=None, wells=None, includeEmpty=False):
    if rows is None:
      rows = range(self.rowCount())
    if wells is None:
      wells = _DummyFullSet()
    colIdx = self._data.columns.get_loc("condition")
    return sorted({val.strip() for row in rows for idx, val in enumerate(self._data.iloc[row, colIdx][1:-1].split(",")) if idx in wells and (includeEmpty or val.strip())})

  def getExistingGenotypes(self, rows=None, wells=None, includeEmpty=False):
    if rows is None:
      rows = range(self.rowCount())
    if wells is None:
      wells = _DummyFullSet()
    colIdx = self._data.columns.get_loc("genotype")
    return sorted({val.strip() for row in rows for idx, val in enumerate(self._data.iloc[row, colIdx][1:-1].split(",")) if idx in wells and (includeEmpty or val.strip())})

  def getInclude(self, rows, wells):
    return {val.strip() for row in rows for idx, val in enumerate(self._data.iloc[row, self._data.columns.get_loc("include")][1:-1].split(",")) if idx in wells}

  def hasUnsavedChanges(self, filename):
    if not os.path.exists(filename):  # file was deleted
      return False
    fileData = pd.read_excel(filename)
    fileData = fileData.loc[:, ~fileData.columns.str.contains('^Unnamed')]
    return not self._data.equals(fileData)

  def getErrors(self, getWellPositionsCb, resultsFileCb):
    fileData = self._data
    errors = []
    fpsCol = fileData.columns.get_loc("fq")
    pixelSizeCol = fileData.columns.get_loc("pixelsize")
    conditionCol = fileData.columns.get_loc("condition")
    genotypeCol = fileData.columns.get_loc("genotype")
    includeCol = fileData.columns.get_loc("include")
    rowCount = self.rowCount()
    if not rowCount:
      return ["File is empty."]
    for row in range(rowCount):
      path = self.videoPath(row)
      if resultsFileCb(path) is None:
        errors.append("Row %d: '%s' is not a valid results folder." % (row, path))
        continue
      errorParts = ["Row %d: " % row]
      if not fileData.iloc[row, fpsCol]:
        errorParts.append("fps is empty")
      wellPositions = getWellPositionsCb(path)
      if wellPositions is None:
        errorParts.append("wells file is corrupt")
        errors.append("%s%s." % (errorParts[0], ', '.join(errorParts[1:])))
        continue
      numWells = 1 if not wellPositions else len(wellPositions)
      for arr, col in (("condition", conditionCol), ("genotype", genotypeCol), ("include", includeCol)):
        value = fileData.iloc[row, col]
        if value[0] != '[' or value[-1] != ']':
          errorParts.append("%s array is missing square brackets" % arr)
          continue
        values = value[1:-1].split(",")
        if len(values) != numWells:
          errorParts.append("the number of elements in %s array does not match the number of wells in the video" % arr)
        if not all(val.strip() for val in values):
          errorParts.append("some elements in the array %s are empty" % arr)
      if len(errorParts) > 1:
        errors.append("%s%s." % (errorParts[0], ', '.join(errorParts[1:])))
    return errors


class _ExperimentOrganizationSelectionModel(QItemSelectionModel):
  def __init__(self, window, table, *args):
    super().__init__(*args)
    self._window = window
    self._table = table
    self._blockSelection = False

  def setCurrentIndex(self, index, command):
    if index != self.currentIndex() and self._table.model() is not None and self._table.model().hasUnsavedChanges(self.model().filePath(self.currentIndex())) and \
        QMessageBox.question(self._window, "Unsaved changes", "Are you sure you want to proceed? Unsaved changes will be lost.",
                             defaultButton=QMessageBox.StandardButton.No) != QMessageBox.StandardButton.Yes:
      self._blockSelection = True
      return None
    return super().setCurrentIndex(index, command)

  def select(self, index, command):
    if self._blockSelection:
      self._blockSelection = False
      return None
    return super().select(index, command)


class CreateExperimentOrganizationExcel(QWidget):
  _POTENTIAL_WELLS_FILENAMES = ("intermediaryWellPosition.txt", "intermediaryWellPositionReloadNoMatterWhat.txt")

  def __init__(self, controller):
    super().__init__(controller.window)
    self.controller = controller
    self._shownVideo = None
    self._previousSelection = {}

    layout = QVBoxLayout()
    layout.addWidget(util.apply_style(QLabel("Prepare experiment organization excel file"), font=controller.title_font), alignment=Qt.AlignmentFlag.AlignCenter)

    folderPath = os.path.join(paths.getDataAnalysisFolder(), 'experimentOrganizationExcel')
    model = _ExperimentFilesModel()
    model.setRootPath(folderPath)

    self._tree = tree = _ExperimentTreeView()
    tree.setModel(model)
    for idx in range(1, model.columnCount()):
      tree.hideColumn(idx)
    tree.setRootIndex(model.index(model.rootPath()))
    self._table = QTableView()
    selectionModel = _ExperimentOrganizationSelectionModel(controller.window, self._table, model)
    tree.setSelectionModel(selectionModel)
    selectionModel.currentRowChanged.connect(lambda current, previous: current.row() == -1 or self._fileSelected(model.filePath(current)))

    treeLayout = QVBoxLayout()
    self._newExperimentBtn = QPushButton("New experiment")
    self._newExperimentBtn.clicked.connect(self._newExperiment)
    treeLayout.addWidget(self._newExperimentBtn, alignment=Qt.AlignmentFlag.AlignLeft)
    treeLayout.addWidget(tree, stretch=1)
    treeWidget = QWidget()
    treeLayout.setContentsMargins(0, 0, 0, 0)
    treeWidget.setLayout(treeLayout)
    horizontalSplitter = util.CollapsibleSplitter()
    horizontalSplitter.addWidget(treeWidget)
    verticalSplitter = util.CollapsibleSplitter()
    verticalSplitter.setOrientation(Qt.Orientation.Vertical)
    verticalSplitter.setChildrenCollapsible(False)
    tableLayout = QVBoxLayout()
    tableButtonsLayout = QHBoxLayout()
    self._addVideosBtn = QPushButton("Add video(s)")
    self._addVideosBtn.clicked.connect(self._addVideos)
    tableButtonsLayout.addWidget(self._addVideosBtn, alignment=Qt.AlignmentFlag.AlignLeft)
    removeVideosBtn = QPushButton("Remove selected videos")
    removeVideosBtn.clicked.connect(self._removeVideos)
    tableButtonsLayout.addWidget(removeVideosBtn, alignment=Qt.AlignmentFlag.AlignLeft)
    saveChangesBtn = QPushButton("Save changes")
    saveChangesBtn.clicked.connect(lambda: self._table.model().saveFile(self._tree.model().filePath(selectionModel.currentIndex())) or QMessageBox.information(self.controller.window, "Experiment saved", "Changes made to the experiment were saved."))
    tableButtonsLayout.addWidget(saveChangesBtn, alignment=Qt.AlignmentFlag.AlignLeft)
    deleteExperimentBtn = QPushButton("Delete experiment")
    deleteExperimentBtn.clicked.connect(self._removeExperiment)
    tableButtonsLayout.addWidget(deleteExperimentBtn, alignment=Qt.AlignmentFlag.AlignLeft)
    openExperimentFolderBtn = QPushButton("Open experiment folder")
    openExperimentFolderBtn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(folderPath)))
    tableButtonsLayout.addWidget(openExperimentFolderBtn, alignment=Qt.AlignmentFlag.AlignLeft)
    self._runExperimentBtn = util.apply_style(QPushButton("Run analysis"), background_color=util.LIGHT_YELLOW)
    self._runExperimentBtn.clicked.connect(self._unsavedChangesWarning(lambda *_: self._runExperiment(), forceSave=True))
    tableButtonsLayout.addWidget(self._runExperimentBtn, alignment=Qt.AlignmentFlag.AlignLeft)
    tableButtonsLayout.addStretch()
    tableLayout.addLayout(tableButtonsLayout)
    tableLayout.addWidget(self._table, stretch=1)
    self._mainWidget = QWidget()
    self._mainWidget.setVisible(False)
    tableLayout.setContentsMargins(0, 0, 0, 0)
    self._mainWidget.setLayout(tableLayout)
    verticalSplitter.addWidget(self._mainWidget)
    self._frame = _WellsSelectionLabel()
    self._frame.setVisible(False)
    self._frame.wellsChanged.connect(self._wellsSelected)
    detailsLayout = QVBoxLayout()
    detailsLayout.addWidget(self._frame, stretch=1)
    videoDetailsLayout = QGridLayout()
    videoDetailsLayout.addWidget(QLabel("FPS:"), 0, 0, alignment=Qt.AlignmentFlag.AlignLeft)
    self._FPSLineEdit = QLineEdit()
    self._FPSLineEdit.editingFinished.connect(self._FPSChanged)
    videoDetailsLayout.addWidget(self._FPSLineEdit, 0, 1, alignment=Qt.AlignmentFlag.AlignLeft)
    videoDetailsLayout.addWidget(QLabel("Pixel size:"), 1, 0, alignment=Qt.AlignmentFlag.AlignLeft)
    self._pixelSizeLineEdit = QLineEdit()
    self._pixelSizeLineEdit.editingFinished.connect(self._pixelSizeChanged)
    videoDetailsLayout.addWidget(self._pixelSizeLineEdit, 1, 1, alignment=Qt.AlignmentFlag.AlignLeft)
    videoDetailsLayout.addWidget(QLabel("Condition:"), 2, 0, alignment=Qt.AlignmentFlag.AlignLeft)
    self._conditionLineEdit = QLineEdit()
    conditionCompleter = QCompleter()
    conditionCompleter.setModel(QStringListModel())
    conditionCompleter.setCompletionMode(QCompleter.CompletionMode.UnfilteredPopupCompletion)
    self._conditionLineEdit.setCompleter(conditionCompleter)
    self._conditionLineEdit.editingFinished.connect(self._conditionChanged)
    videoDetailsLayout.addWidget(self._conditionLineEdit, 2, 1, alignment=Qt.AlignmentFlag.AlignLeft)
    videoDetailsLayout.addWidget(QLabel("Genotype:"), 3, 0, alignment=Qt.AlignmentFlag.AlignLeft)
    self._genotypeLineEdit = QLineEdit()
    genotypeCompleter = QCompleter()
    genotypeCompleter.setModel(QStringListModel())
    genotypeCompleter.setCompletionMode(QCompleter.CompletionMode.UnfilteredPopupCompletion)
    self._genotypeLineEdit.setCompleter(genotypeCompleter)
    self._genotypeLineEdit.editingFinished.connect(self._genotypeChanged)
    videoDetailsLayout.addWidget(self._genotypeLineEdit, 3, 1, alignment=Qt.AlignmentFlag.AlignLeft)
    self._includeCheckbox = QCheckBox("Include in analysis")
    self._includeCheckbox.stateChanged.connect(self._includeChanged)
    videoDetailsLayout.addWidget(self._includeCheckbox, 4, 0, 1, 2, alignment=Qt.AlignmentFlag.AlignLeft)
    videoDetailsLayout.setRowStretch(5, 1)
    self._detailsWidget = QWidget()
    self._detailsWidget.setLayout(videoDetailsLayout)
    self._detailsWidget.setVisible(False)
    detailsLayout.addWidget(self._detailsWidget, alignment=Qt.AlignmentFlag.AlignLeft)
    self._placeholderDetail = QLabel("Select one or more wells to edit the information for those wells in all selected videos.")
    self._placeholderDetail.setVisible(False)
    self._placeholderDetail.sizeHint = self._detailsWidget.sizeHint
    detailsLayout.addWidget(self._placeholderDetail, alignment=Qt.AlignmentFlag.AlignCenter)
    self._placeholderVideo = QLabel()
    detailsLayout.addWidget(self._placeholderVideo, alignment=Qt.AlignmentFlag.AlignCenter)
    detailsWidget = QWidget()
    detailsWidget.setLayout(detailsLayout)
    detailsScrollArea = QScrollArea()
    detailsScrollArea.setFrameShape(QFrame.Shape.NoFrame)
    detailsScrollArea.setWidgetResizable(True)
    detailsScrollArea.setWidget(detailsWidget)
    verticalSplitter.addWidget(detailsScrollArea)
    verticalSplitter.setStretchFactor(1, 100)
    scrollArea = QScrollArea()
    scrollArea.setFrameShape(QFrame.Shape.NoFrame)
    scrollArea.setWidgetResizable(True)
    scrollArea.setWidget(verticalSplitter)
    horizontalSplitter.addWidget(scrollArea)
    horizontalSplitter.setStretchFactor(1, 1)
    horizontalSplitter.setChildrenCollapsible(False)
    layout.addWidget(horizontalSplitter, stretch=1)

    buttonsLayout = QHBoxLayout()
    buttonsLayout.addStretch()
    startPageBtn = util.apply_style(QPushButton("Go to the start page"), background_color=util.LIGHT_CYAN)
    startPageBtn.clicked.connect(self._unsavedChangesWarning(lambda *_: controller.show_frame("StartPage")))
    buttonsLayout.addWidget(startPageBtn, alignment=Qt.AlignmentFlag.AlignCenter)
    previousParameterResultsBtn = util.apply_style(QPushButton("View previous kinematic parameter analysis results"), background_color=util.LIGHT_YELLOW)
    previousParameterResultsBtn.clicked.connect(lambda: _showKinematicParametersVisualization())
    buttonsLayout.addWidget(previousParameterResultsBtn, alignment=Qt.AlignmentFlag.AlignCenter)
    previousClusteringResultsBtn = util.apply_style(QPushButton("View previous clustering analysis results"), background_color=util.LIGHT_YELLOW)
    previousClusteringResultsBtn.clicked.connect(lambda: controller.show_frame("AnalysisOutputFolderClustering"))
    buttonsLayout.addWidget(previousClusteringResultsBtn, alignment=Qt.AlignmentFlag.AlignCenter)
    buttonsLayout.addStretch()
    layout.addLayout(buttonsLayout)

    self.setLayout(layout)

  def _unsavedChangesWarning(self, fn, forceSave=False):
    def inner(*args, **kwargs):
      if forceSave:
        text = "Do you want to save the changes and proceed?"
      else:
        text = "Are you sure you want to proceed? Unsaved changes will be lost."
      filename = self._tree.model().filePath(self._tree.selectionModel().currentIndex())
      if self._table.model() is not None and self._table.model().hasUnsavedChanges(filename):
        if QMessageBox.question(self.controller.window, "Unsaved changes", text, defaultButton=QMessageBox.StandardButton.No) != QMessageBox.StandardButton.Yes:
          return
        elif forceSave:
          self._table.model().saveFile(filename)
      return fn(*args, **kwargs)
    return inner

  def _updateConditionCompletion(self):
    self._conditionLineEdit.completer().model().setStringList(self._table.model().getExistingConditions())

  def _updateGenotypeCompletion(self):
    self._genotypeLineEdit.completer().model().setStringList(self._table.model().getExistingGenotypes())

  def _updateWellInfos(self):
    rows = set(map(lambda idx: idx.row(), self._table.selectionModel().selectedIndexes()))
    formatList = lambda s: '[%s]' % ', '.join(s) if len(s) != 1 else s.pop()
    self._frame.setWellInfos([(formatList(self._table.model().getExistingConditions(rows=rows, wells=[well], includeEmpty=True)),
                               formatList(self._table.model().getExistingGenotypes(rows=rows, wells=[well], includeEmpty=True)),
                               formatList(self._table.model().getInclude(rows, [well]))) for well in range(self._frame.totalWells())])

  def _FPSChanged(self):
    self._table.model().updateNumericValue(sorted(set(map(lambda idx: idx.row(), self._table.selectionModel().selectedIndexes()))), 2, self._FPSLineEdit.text())

  def _pixelSizeChanged(self):
    self._table.model().updateNumericValue(sorted(set(map(lambda idx: idx.row(), self._table.selectionModel().selectedIndexes()))), 3, self._pixelSizeLineEdit.text())

  def _conditionChanged(self):
    condition = self._conditionLineEdit.text()
    self._table.model().updateArrayValues(sorted(set(map(lambda idx: idx.row(), self._table.selectionModel().selectedIndexes()))), 4, self._frame.getWells(), condition)
    self._updateConditionCompletion()
    self._updateWellInfos()

  def _genotypeChanged(self):
    genotype = self._genotypeLineEdit.text()
    self._table.model().updateArrayValues(sorted(set(map(lambda idx: idx.row(), self._table.selectionModel().selectedIndexes()))), 5, self._frame.getWells(), genotype)
    self._updateGenotypeCompletion()
    self._updateWellInfos()

  def _includeChanged(self, state):
    checked = int(state == Qt.CheckState.Checked)
    self._table.model().updateArrayValues(sorted(set(map(lambda idx: idx.row(), self._table.selectionModel().selectedIndexes()))), 6, self._frame.getWells(), checked)
    self._includeCheckbox.setTristate(False)
    self._updateWellInfos()

  def _fileSelected(self, filename):
    self._mainWidget.show()
    self._table.setModel(_ExperimentOrganizationModel(filename))
    self._updateConditionCompletion()
    self._updateGenotypeCompletion()
    self._table.setColumnHidden(0, True)
    self._table.horizontalHeader().resizeSections(QHeaderView.ResizeMode.Stretch)
    self._table.selectionModel().selectionChanged.connect(lambda *_: self._videoSelected(sorted(set(map(lambda idx: idx.row(), self._table.selectionModel().selectedIndexes())))))
    self._videoSelected(None)

  def _getWellPositions(self, resultsFolder):
    wellsFile = next(filter(os.path.exists, (os.path.join(resultsFolder, fname) for fname in self._POTENTIAL_WELLS_FILENAMES)), None)
    if wellsFile is None:
      return []
    else:
      try:
        with open(wellsFile, 'rb') as f:
          return pickle.load(f)
      except Exception:
        QMessageBox.critical(self.controller.window, "Could not read well positions", "Well positions file could not be read.")
    return None

  def _findValidationVideo(self, folder):
    expectedName = os.path.join(folder, '%s.avi' % os.path.basename(folder))
    if os.path.exists(expectedName):
      return expectedName
    return next((os.path.join(folder, f) for f in os.listdir(folder) if os.path.isfile(os.path.join(folder, f)) if f.endswith('.avi')), None)

  def _videoSelected(self, rows):
    if not rows:
      self._detailsWidget.hide()
      self._frame.setOriginalPixmap(None)
      self._frame.hide()
      self._placeholderDetail.hide()
      self._placeholderVideo.setText("Select one or more videos in the table above to edit the information for those videos.")
      self._placeholderVideo.show()
      self._shownVideo = None
      self._previousSelection.clear()
      return
    paths = set(map(self._table.model().videoPath, rows))
    newSelection = {videoPath: (self._previousSelection[videoPath] if videoPath in self._previousSelection else self._getWellPositions(videoPath))
                    for videoPath in paths}
    oldWellLengths = {len(wells) if wells is not None else None for wells in self._previousSelection.values()}
    newWellLengths = {len(wells) if wells is not None else None for wells in newSelection.values()}
    self._previousSelection = newSelection
    videoToShow = self._table.model().videoPath(rows[0])
    validationVideo = self._findValidationVideo(videoToShow)
    self._wellsSelected()
    if len(rows) > 1:
      if (newWellLengths == oldWellLengths and self._shownVideo is not None and validationVideo is None == self._findValidationVideo(self._shownVideo) is None) or \
          (len(newWellLengths) > 1 and len(oldWellLengths) > 1):
        return
      if len(newWellLengths) > 1:
        self._detailsWidget.hide()
        self._frame.setOriginalPixmap(None)
        self._frame.hide()
        self._placeholderDetail.hide()
        self._placeholderVideo.setText("Cannot edit the information because some of the selected videos don't have the same number of wells.")
        self._placeholderVideo.show()
        self._shownVideo = None
        return
    if self._shownVideo == videoToShow:
      return
    self._shownVideo = videoToShow
    wellPositions = self._previousSelection[videoToShow]
    if wellPositions is None:
      return
    elif not wellPositions:
      self._frame.setWellPositions(None)
      self._frame.wellShape = None
      self._placeholderDetail.hide()
      self._detailsWidget.show()
    else:
      self._frame.setWellPositions([(position['topLeftX'], position['topLeftY'], position['lengthX'], position['lengthY'])
                                    for idx, position in enumerate(wellPositions)])
      self._updateWellInfos()
      with open(os.path.join(videoToShow, 'configUsed.json')) as f:
        config = json.load(f)
      self._frame.wellShape = 'rectangle' if config.get("wellsAreRectangles", False) or len(config.get("oneWellManuallyChosenTopLeft", '')) or int(config.get("multipleROIsDefinedDuringExecution", 0)) or config.get("noWellDetection", False) or config.get("groupOfMultipleSameSizeAndShapeEquallySpacedWells", False) else 'circle'
    if validationVideo is None:
      self._placeholderVideo.setText("Validation video not found. Data must be modified manually in the table.")
      self._placeholderDetail.hide()
      self._placeholderVideo.show()
      self._detailsWidget.hide()
      self._frame.hide()
      self._frame.setOriginalPixmap(None)
    else:
      self._placeholderVideo.hide()
      self._frame.setOriginalPixmap(QPixmap(util._cvToPixmap(zzVideoReading.VideoCapture(validationVideo).read()[1])))
      self._wellsSelected()

  def _findResultsFile(self, path):
    if not os.path.exists(path):
      return None
    folder = os.path.basename(path)
    reference = os.path.join(path, 'results_' + folder + '.txt')
    if os.path.exists(reference):
      return reference
    resultsFile = next((f for f in os.listdir(path) if os.path.isfile(os.path.join(path, f)) if f.startswith('results_')), None)
    if resultsFile is None:
      return None
    return os.path.join(path, resultsFile)

  def _getMultipleFolders(self):
    dialog = QFileDialog()
    dialog.setWindowTitle('Select one or more results folders (use Ctrl or Shift key to select multiple folders)')
    dialog.setDirectory(self.controller.ZZoutputLocation)
    dialog.setFileMode(QFileDialog.FileMode.Directory)
    dialog.setOption(QFileDialog.Option.DontUseNativeDialog, True)
    dialog.setOption(QFileDialog.Option.ShowDirsOnly, True)
    listView = dialog.findChild(QListView, 'listView')
    if listView:
      listView.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)
    treeView = dialog.findChild(QTreeView)
    if treeView:
      treeView.setSelectionMode(QAbstractItemView.SelectionMode.ExtendedSelection)

    if not dialog.exec():
      return None
    return dialog.selectedFiles()

  def _addVideos(self):
    selectedFolders = self._getMultipleFolders()
    if selectedFolders is None:
      return
    invalidFolders = []
    for selectedFolder in selectedFolders:
      if self._findResultsFile(selectedFolder) is None:
        invalidFolders.append(selectedFolder)
        continue
      wellPositions = self._getWellPositions(selectedFolder)
      if wellPositions is None:
        invalidFolders.append(selectedFolder)
        continue
      numWells = 1 if not wellPositions else len(wellPositions)
      emptyArray = ["[%s]" % ','.join(" " for _ in range(numWells))]
      includeArray = ["[%s]" % ', '.join("1" for _ in range(numWells))]
      model = self._table.model()
      model.addVideo({"path": [os.path.dirname(selectedFolder)], "trial_id": [os.path.basename(selectedFolder)], "fq": [" "], "pixelsize": [" "], "condition": emptyArray, "genotype": emptyArray, "include": includeArray})
      model.insertRow(model.rowCount())
      self._table.selectionModel().setCurrentIndex(model.index(model.rowCount() - 1, 1), QItemSelectionModel.SelectionFlag.ClearAndSelect)
    if invalidFolders:
      warning = QMessageBox(self.controller.window)
      warning.setIcon(QMessageBox.Icon.Warning)
      warning.setWindowTitle("Invalid folders selected")
      warning.setText("Some of the selected folders were ignored because they are not valid results folders.")
      warning.setDetailedText("\n".join(invalidFolders))
      warning.exec()

  def _removeVideos(self):
    selectedIdxs = sorted(set(map(lambda idx: idx.row(), self._table.selectionModel().selectedIndexes())))
    self._table.model().removeSelectedRows(selectedIdxs)
    self._videoSelected(None)

  def _newExperiment(self):
    number = 1
    while os.path.exists(os.path.join(self._tree.model().rootPath(), 'Experiment %d.xlsx' % number)):
      number += 1
    path = os.path.join(self._tree.model().rootPath(), 'Experiment %d.xlsx' % number)
    pd.DataFrame(columns=_ExperimentOrganizationModel._COLUMN_NAMES).to_excel(path, index=False)
    index = self._tree.model().index(path)
    self._tree.selectionModel().setCurrentIndex(index, QItemSelectionModel.SelectionFlag.ClearAndSelect)
    self._tree.edit(index)

  def _removeExperiment(self):
    if QMessageBox.question(self.controller.window, "Delete experiment", "Are you sure you want to delete the experiment? This action removes the file from disk and cannot be undone.",
                            defaultButton=QMessageBox.StandardButton.No) != QMessageBox.StandardButton.Yes:
      return
    pathToRemove = self._tree.model().filePath(self._tree.selectionModel().currentIndex())
    self._tree.model().remove(self._tree.selectionModel().currentIndex())
    if pathToRemove == self._tree.model().filePath(self._tree.selectionModel().currentIndex()):  # last valid file removed
      self._mainWidget.hide()

  def _wellsSelected(self):
    wells = self._frame.getWells()
    wellsSelected = bool(wells)
    self._detailsWidget.setVisible(wellsSelected)
    self._placeholderDetail.setVisible(not wellsSelected)
    if not wellsSelected:
      return
    rows = set(map(lambda idx: idx.row(), self._table.selectionModel().selectedIndexes()))
    FPS = self._table.model().getFPS(rows)
    if len(FPS) == 1:
      self._FPSLineEdit.setText(FPS[0])
      self._FPSLineEdit.setPlaceholderText('')
      self._FPSLineEdit.setToolTip(None)
    else:
      self._FPSLineEdit.setText('')
      text = '[%s]' % ', '.join(FPS)
      self._FPSLineEdit.setPlaceholderText(text)
      self._FPSLineEdit.setToolTip(text)
    pixelSizes = self._table.model().getPixelSizes(rows)
    if len(pixelSizes) == 1:
      self._pixelSizeLineEdit.setText(pixelSizes[0])
      self._pixelSizeLineEdit.setPlaceholderText('')
      self._pixelSizeLineEdit.setToolTip(None)
    else:
      self._pixelSizeLineEdit.setText('')
      text = '[%s]' % ', '.join(pixelSizes)
      self._pixelSizeLineEdit.setPlaceholderText(text)
      self._pixelSizeLineEdit.setToolTip(text)
    conditions = self._table.model().getExistingConditions(rows=rows, wells=wells, includeEmpty=True)
    if len(conditions) == 1:
      self._conditionLineEdit.setText(conditions[0])
      self._conditionLineEdit.setPlaceholderText('')
      self._conditionLineEdit.setToolTip(None)
    else:
      self._conditionLineEdit.setText('')
      text = '[%s]' % ', '.join(conditions)
      self._conditionLineEdit.setPlaceholderText(text)
      self._conditionLineEdit.setToolTip(text)
    genotypes = self._table.model().getExistingGenotypes(rows=rows, wells=wells, includeEmpty=True)
    if len(genotypes) == 1:
      self._genotypeLineEdit.setText(genotypes[0])
      self._genotypeLineEdit.setPlaceholderText('')
      self._genotypeLineEdit.setToolTip(None)
    else:
      self._genotypeLineEdit.setText('')
      text = '[%s]' % ', '.join(genotypes)
      self._genotypeLineEdit.setPlaceholderText(text)
      self._genotypeLineEdit.setToolTip(text)
    include = self._table.model().getInclude(rows, wells)
    blocked = self._includeCheckbox.blockSignals(True)
    self._includeCheckbox.setCheckState(Qt.CheckState.PartiallyChecked if len(include) > 1 else Qt.CheckState.Checked if include.pop() == "1" else Qt.CheckState.Unchecked)
    self._includeCheckbox.blockSignals(blocked)
    self._updateWellInfos()

  def _runExperiment(self):
    errors = self._table.model().getErrors(self._getWellPositions, self._findResultsFile)
    if errors:
      error = QMessageBox(self.controller.window)
      error.setIcon(QMessageBox.Icon.Critical)
      error.setWindowTitle("Excel file contains errors")
      error.setText("Experiment organization file contains some errors. Please fix them before running analysis.")
      error.setDetailedText("\n".join(errors))
      textEdit = error.findChild(QTextEdit)
      textEdit.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
      layout = error.layout()
      layout.addItem(QSpacerItem(600, 0), layout.rowCount(), 0, 1, layout.columnCount())
      error.exec()
      return
    path = self._tree.model().filePath(self._tree.selectionModel().currentIndex())
    self.controller.experimentOrganizationExcel = os.path.basename(path)
    self.controller.experimentOrganizationExcelFileAndFolder = os.path.dirname(path)
    self.controller.show_frame("ChooseDataAnalysisMethod")


class ChooseDataAnalysisMethod(QWidget):
  def __init__(self, controller):
    super().__init__(controller.window)
    self.controller = controller

    layout = QVBoxLayout()
    layout.addWidget(util.apply_style(QLabel("Choose the analysis you want to perform:"), font=controller.title_font), alignment=Qt.AlignmentFlag.AlignCenter)

    self._compareBtn = util.apply_style(QPushButton("Compare populations with kinematic parameters"), background_color=util.LIGHT_YELLOW)
    self._compareBtn.clicked.connect(lambda: controller.show_frame("PopulationComparison"))
    layout.addWidget(self._compareBtn, alignment=Qt.AlignmentFlag.AlignCenter)
    self._clusterBtn = util.apply_style(QPushButton("Cluster bouts of movements  (for zebrafish only)"), background_color=util.LIGHT_YELLOW)
    self._clusterBtn.clicked.connect(lambda: controller.show_frame("BoutClustering"))
    layout.addWidget(self._clusterBtn, alignment=Qt.AlignmentFlag.AlignCenter)

    self._startPageBtn = util.apply_style(QPushButton("Go to the start page"), background_color=util.LIGHT_CYAN)
    self._startPageBtn.clicked.connect(lambda: controller.show_frame("StartPage"))
    layout.addWidget(self._startPageBtn, alignment=Qt.AlignmentFlag.AlignCenter)

    self.setLayout(layout)


class PopulationComparison(QWidget):
  def __init__(self, controller):
    super().__init__(controller.window)
    self.controller = controller
    self.preferredSize = (1152, 768)

    layout = QVBoxLayout()
    layout.addWidget(util.apply_style(QLabel("Population Comparison:"), font=controller.title_font), alignment=Qt.AlignmentFlag.AlignCenter)

    self._tailTrackingParametersCheckbox = QCheckBox("I want fish tail tracking related kinematic parameters (number of oscillation, tail beat frequency, etc..) to be calculated.")
    layout.addWidget(self._tailTrackingParametersCheckbox, alignment=Qt.AlignmentFlag.AlignCenter)

    advancedOptionsLayout = QVBoxLayout()
    self._saveInMatlabFormatCheckbox = QCheckBox("The result structure is always saved in the pickle format. Also save it in the matlab format.")
    advancedOptionsLayout.addWidget(self._saveInMatlabFormatCheckbox, alignment=Qt.AlignmentFlag.AlignCenter)
    self._saveRawDataCheckbox = QCheckBox("Save original raw data in result structure.")
    self._saveRawDataCheckbox.setVisible(False)  # XXX: hidden from the moment because of a bug, unhide it once it's fixed
    advancedOptionsLayout.addWidget(self._saveRawDataCheckbox, alignment=Qt.AlignmentFlag.AlignCenter)
    self._forcePandasRecreation = QCheckBox("Force recalculation of all parameters even if they have already been calculated and saved.")
    advancedOptionsLayout.addWidget(self._forcePandasRecreation, alignment=Qt.AlignmentFlag.AlignCenter)

    advancedOptionsLayout.addWidget(util.apply_style(QLabel("Number of frames between each frame used for distance calculation (to avoid noise due to close-by subsequent points) (default value is 4):"), font=QFont("Helvetica", 10)), alignment=Qt.AlignmentFlag.AlignCenter)
    self._frameStepForDistanceCalculation = QLineEdit()
    self._frameStepForDistanceCalculation.setValidator(QIntValidator())
    self._frameStepForDistanceCalculation.validator().setBottom(0)
    advancedOptionsLayout.addWidget(self._frameStepForDistanceCalculation, alignment=Qt.AlignmentFlag.AlignCenter)

    advancedOptionsLayout.addWidget(util.apply_style(QLabel("If you are calculating fish tail tracking related kinematic parameters:"), font_size="16px"), alignment=Qt.AlignmentFlag.AlignCenter)
    advancedOptionsLayout.addWidget(util.apply_style(QLabel("What's the minimum number of bends a bout should have to be taken into account for the analysis?"), font=QFont("Helvetica", 10)), alignment=Qt.AlignmentFlag.AlignCenter)
    advancedOptionsLayout.addWidget(util.apply_style(QLabel("(the default value is 3) (put 0 if you want all bends to be taken into account)"), font=QFont("Helvetica", 10)), alignment=Qt.AlignmentFlag.AlignCenter)
    self._minNbBendForBoutDetect = QLineEdit()
    self._minNbBendForBoutDetect.setValidator(QIntValidator())
    self._minNbBendForBoutDetect.validator().setBottom(0)
    advancedOptionsLayout.addWidget(self._minNbBendForBoutDetect, alignment=Qt.AlignmentFlag.AlignCenter)

    advancedOptionsLayout.addWidget(util.apply_style(QLabel("If, for a bout, the tail tracking related kinematic parameters are being discarded because of a low amount of bends,"), font=QFont("Helvetica", 10)), alignment=Qt.AlignmentFlag.AlignCenter)
    advancedOptionsLayout.addWidget(util.apply_style(QLabel("should the BoutDuration, TotalDistance, Speed and IBI also be discarded for that bout?"), font=QFont("Helvetica", 10)), alignment=Qt.AlignmentFlag.AlignCenter)
    self._discardRadioButton = QRadioButton("Yes, discard BoutDuration, TotalDistance, Speed and IBI in that situation")
    self._discardRadioButton.setChecked(True)
    advancedOptionsLayout.addWidget(self._discardRadioButton, alignment=Qt.AlignmentFlag.AlignCenter)
    self._keepRadioButton = QRadioButton("No, keep BoutDuration, TotalDistance, Speed and IBI in that situation")
    advancedOptionsLayout.addWidget(self._keepRadioButton, alignment=Qt.AlignmentFlag.AlignCenter)
    advancedOptionsLayout.addWidget(util.apply_style(QLabel("Please ignore the two questions above if you're only looking at BoutDuration, TotalDistance, Speed and IBI."), font=QFont("Helvetica", 10)), alignment=Qt.AlignmentFlag.AlignCenter)

    self._advancedOptionsExpander = util.Expander(self, "Show advanced options", advancedOptionsLayout)
    layout.addWidget(self._advancedOptionsExpander)

    self._launchBtn = util.apply_style(QPushButton("Launch Analysis"), background_color=util.LIGHT_YELLOW)
    self._launchBtn.clicked.connect(lambda: self._populationComparison(self._tailTrackingParametersCheckbox.isChecked(), self._saveInMatlabFormatCheckbox.isChecked(), self._saveRawDataCheckbox.isChecked(), self._forcePandasRecreation.isChecked(), self._minNbBendForBoutDetect.text(), self._discardRadioButton.isChecked(), self._keepRadioButton.isChecked(), self._frameStepForDistanceCalculation.text()))
    layout.addWidget(self._launchBtn, alignment=Qt.AlignmentFlag.AlignCenter)
    self._startPageBtn = util.apply_style(QPushButton("Go to the start page"), background_color=util.LIGHT_CYAN)
    self._startPageBtn.clicked.connect(lambda: controller.show_frame("StartPage"))
    layout.addWidget(self._startPageBtn, alignment=Qt.AlignmentFlag.AlignCenter)

    self.setLayout(layout)

  def _populationComparison(self, TailTrackingParameters=0, saveInMatlabFormat=0, saveRawData=0, forcePandasRecreation=0, minNbBendForBoutDetect=3, discard=0, keep=1, frameStepForDistanceCalculation='4'):
    if len(frameStepForDistanceCalculation) == 0:
      frameStepForDistanceCalculation = '4'

    if discard == 0 and keep == 0:
      keep = 1

    if len(minNbBendForBoutDetect) == 0:
      minNbBendForBoutDetect = 3

    if len(self.controller.ZZoutputLocation) == 0:
      ZZoutputLocation = paths.getDefaultZZoutputFolder()
    else:
      ZZoutputLocation = self.controller.ZZoutputLocation

    # Creating the dataframe

    dataframeOptions = {
      'pathToExcelFile'                   : self.controller.experimentOrganizationExcelFileAndFolder, #os.path.join(cur_dir_path, os.path.join('dataAnalysis', 'experimentOrganizationExcel/')),
      'fileExtension'                     : '.' + self.controller.experimentOrganizationExcel.split(".")[1],
      'resFolder'                         : os.path.join(paths.getDataAnalysisFolder(), 'data'),
      'nameOfFile'                        : self.controller.experimentOrganizationExcel.split(".")[0],
      'smoothingFactorDynaParam'          : 0,   # 0.001
      'nbFramesTakenIntoAccount'          : 0,
      'numberOfBendsIncludedForMaxDetect' : -1,
      'minNbBendForBoutDetect'            : int(minNbBendForBoutDetect),
      'keepSpeedDistDurWhenLowNbBends'    : int(keep),
      'defaultZZoutputFolderPath'         : ZZoutputLocation,
      'computeTailAngleParamForCluster'   : False,
      'computeMassCenterParamForCluster'  : False,
      'tailAngleKinematicParameterCalculation'    : TailTrackingParameters,
      'saveRawDataInAllBoutsSuperStructure'       : saveRawData,
      'saveAllBoutsSuperStructuresInMatlabFormat' : saveInMatlabFormat,
      'frameStepForDistanceCalculation'           : frameStepForDistanceCalculation
    }

    generatePklDataFileForVideo(os.path.join(self.controller.experimentOrganizationExcelFileAndFolder, self.controller.experimentOrganizationExcel), ZZoutputLocation, frameStepForDistanceCalculation, forcePandasRecreation)

    [conditions, genotypes, nbFramesTakenIntoAccount, globParam] = createDataFrame(dataframeOptions, "", forcePandasRecreation, [])

    # Plotting for the different conditions
    nameOfFile = dataframeOptions['nameOfFile']
    resFolder  = dataframeOptions['resFolder']

    # Mixing up all the bouts
    populationComparaison(nameOfFile, resFolder, globParam, conditions, genotypes, os.path.join(paths.getDataAnalysisFolder(), 'resultsKinematic'), 0, True)

    allParameters, allData = populationComparaison(nameOfFile, resFolder, globParam, conditions, genotypes, os.path.join(paths.getDataAnalysisFolder(), 'resultsKinematic'), 0, False)

    # First median per well for each kinematic parameter
    populationComparaison(nameOfFile, resFolder, globParam, conditions, genotypes, os.path.join(paths.getDataAnalysisFolder(), 'resultsKinematic'), 1, True)

    medianParameters, medianData = populationComparaison(nameOfFile, resFolder, globParam, conditions, genotypes, os.path.join(paths.getDataAnalysisFolder(), 'resultsKinematic'), 1, False)

    _showKinematicParametersVisualization((nameOfFile, allParameters, medianParameters, allData, medianData))


def _showKinematicParametersVisualization(data=None):
  app = QApplication.instance()
  layout = app.window.centralWidget().layout()
  page = KinematicParametersVisualization(data)
  layout.addWidget(page)
  layout.setCurrentWidget(page)
  def cleanup():
    layout.removeWidget(page)
    layout.currentChanged.disconnect(cleanup)
  layout.currentChanged.connect(cleanup)


class BoutClustering(QWidget):
  def __init__(self, controller):
    super().__init__(controller.window)
    self.controller = controller
    self.preferredSize = (1152, 768)

    layout = QVBoxLayout()
    layout.addWidget(util.apply_style(QLabel("Bout Clustering:", self), font=controller.title_font), alignment=Qt.AlignmentFlag.AlignCenter)

    layout.addWidget(QLabel("Choose number of cluster to find:", self), alignment=Qt.AlignmentFlag.AlignCenter)
    nbClustersToFind = QLineEdit(controller.window)
    nbClustersToFind.setValidator(QIntValidator(nbClustersToFind))
    nbClustersToFind.validator().setBottom(0)
    layout.addWidget(nbClustersToFind, alignment=Qt.AlignmentFlag.AlignCenter)

    layout.addWidget(QLabel("Choose one of the options below:", self), alignment=Qt.AlignmentFlag.AlignCenter)
    freelySwimmingRadioButton = QRadioButton("Freely swimming fish with tail tracking", self)
    freelySwimmingRadioButton.setChecked(True)
    layout.addWidget(freelySwimmingRadioButton, alignment=Qt.AlignmentFlag.AlignCenter)
    headEmbeddedRadioButton = QRadioButton("Head embeded fish with tail tracking", self)
    layout.addWidget(headEmbeddedRadioButton, alignment=Qt.AlignmentFlag.AlignCenter)

    advancedOptionsLayout = QVBoxLayout()
    advancedOptionsLayout.addWidget(util.apply_style(QLabel("What's the minimum number of bends a bout should have to be taken into account for the analysis?", self), font=QFont("Helvetica", 10)), alignment=Qt.AlignmentFlag.AlignCenter)
    advancedOptionsLayout.addWidget(util.apply_style(QLabel("(the default value is 3) (put 0 if you want all bends to be taken into account)", self), font=QFont("Helvetica", 10)), alignment=Qt.AlignmentFlag.AlignCenter)
    minNbBendForBoutDetect = QLineEdit(controller.window)
    minNbBendForBoutDetect.setValidator(QIntValidator(minNbBendForBoutDetect))
    minNbBendForBoutDetect.validator().setBottom(0)
    advancedOptionsLayout.addWidget(minNbBendForBoutDetect, alignment=Qt.AlignmentFlag.AlignCenter)

    advancedOptionsLayout.addWidget(util.apply_style(QLabel("Optional: generate videos containing the most representative bouts for each cluster: enter below the number of bouts for each video:", self), font=QFont("Helvetica", 10)), alignment=Qt.AlignmentFlag.AlignCenter)
    advancedOptionsLayout.addWidget(util.apply_style(QLabel("(leave blank if you don't want any such cluster validation videos to be generated)", self), font=QFont("Helvetica", 10)), alignment=Qt.AlignmentFlag.AlignCenter)
    nbVideosToSave = QLineEdit(controller.window)
    nbVideosToSave.setValidator(QIntValidator(nbVideosToSave))
    nbVideosToSave.validator().setBottom(0)
    advancedOptionsLayout.addWidget(nbVideosToSave, alignment=Qt.AlignmentFlag.AlignCenter)

    modelUsedForClusteringCheckbox = QCheckBox("Use GMM clustering method instead of Kmeans (clustering method used by default)", self)
    advancedOptionsLayout.addWidget(modelUsedForClusteringCheckbox, alignment=Qt.AlignmentFlag.AlignCenter)
    removeOutliersCheckbox = QCheckBox("Remove outliers before clustering", self)
    advancedOptionsLayout.addWidget(removeOutliersCheckbox, alignment=Qt.AlignmentFlag.AlignCenter)

    advancedOptionsLayout.addWidget(util.apply_style(QLabel("Number of frames between each frame used for distance calculation (to avoid noise due to close-by subsequent points) (default value is 4):", self), font=QFont("Helvetica", 10)), alignment=Qt.AlignmentFlag.AlignCenter)
    frameStepForDistanceCalculation = QLineEdit(controller.window)
    frameStepForDistanceCalculation.setValidator(QIntValidator(frameStepForDistanceCalculation))
    frameStepForDistanceCalculation.validator().setBottom(0)
    advancedOptionsLayout.addWidget(frameStepForDistanceCalculation, alignment=Qt.AlignmentFlag.AlignCenter)
    
    removeBoutsContainingNanValuesInParametersUsedForClustering = QCheckBox("Remove bouts containing nan values in parameters used for clustering", self)
    removeBoutsContainingNanValuesInParametersUsedForClustering.setChecked(True)
    advancedOptionsLayout.addWidget(removeBoutsContainingNanValuesInParametersUsedForClustering, alignment=Qt.AlignmentFlag.AlignCenter)
    advancedOptionsLayout.addWidget(util.apply_style(QLabel("If the box above is un-checked, the nan values will be replaced by zeros and no bouts will be removed.", self), font=QFont("Helvetica", 10)), alignment=Qt.AlignmentFlag.AlignCenter)
    
    self._forcePandasRecreation = QCheckBox("Force recalculation of all parameters even if they have already been calculated and saved.", self)
    advancedOptionsLayout.addWidget(self._forcePandasRecreation, alignment=Qt.AlignmentFlag.AlignCenter)

    layout.addWidget(util.Expander(self, "Show advanced options", advancedOptionsLayout))

    launchBtn = util.apply_style(QPushButton("Launch Analysis", self), background_color=util.LIGHT_YELLOW)
    launchBtn.clicked.connect(lambda: controller.boutClustering(controller, nbClustersToFind.text(), freelySwimmingRadioButton.isChecked(), headEmbeddedRadioButton.isChecked(), minNbBendForBoutDetect.text(), nbVideosToSave.text(), modelUsedForClusteringCheckbox.isChecked(), removeOutliersCheckbox.isChecked(), frameStepForDistanceCalculation.text(), removeBoutsContainingNanValuesInParametersUsedForClustering.isChecked(), self._forcePandasRecreation.isChecked()))
    layout.addWidget(launchBtn, alignment=Qt.AlignmentFlag.AlignCenter)
    startPageBtn = util.apply_style(QPushButton("Go to the start page", self), background_color=util.LIGHT_CYAN)
    startPageBtn.clicked.connect(lambda: controller.show_frame("StartPage"))
    layout.addWidget(startPageBtn, alignment=Qt.AlignmentFlag.AlignCenter)

    self.setLayout(layout)


class AnalysisOutputFolderClustering(QWidget):
  def __init__(self, controller):
    super().__init__(controller.window)
    self.controller = controller

    layout = QVBoxLayout()
    layout.addWidget(util.apply_style(QLabel("View Analysis Output:", self), font=controller.title_font), alignment=Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(QLabel("Click the button below to open the folder that contains the results of the analysis.", self), alignment=Qt.AlignmentFlag.AlignCenter)

    viewProcessedBtn = util.apply_style(QPushButton("View plots and processed data folder", self), background_color=util.LIGHT_YELLOW)
    viewProcessedBtn.clicked.connect(lambda: controller.openAnalysisFolder(controller.homeDirectory, 'resultsClustering'))
    layout.addWidget(viewProcessedBtn, alignment=Qt.AlignmentFlag.AlignCenter)
    viewRawBtn = util.apply_style(QPushButton("View raw data folders", self), background_color=util.LIGHT_YELLOW)
    viewRawBtn.clicked.connect(lambda: controller.openAnalysisFolder(controller.homeDirectory, 'data'))
    layout.addWidget(viewRawBtn, alignment=Qt.AlignmentFlag.AlignCenter)

    startPageBtn = util.apply_style(QPushButton("Go to the start page", self), background_color=util.LIGHT_CYAN)
    startPageBtn.clicked.connect(lambda: controller.show_frame("StartPage"))
    layout.addWidget(startPageBtn, alignment=Qt.AlignmentFlag.AlignCenter)

    self.setLayout(layout)


class _TooltipHelper(QObject):
  def eventFilter(self, obj, evt):
    if evt.type() != QEvent.Type.ToolTip:
      return False
    view = obj.parent()
    if view is None:
      return False

    index = view.indexAt(evt.pos())
    if not index.isValid():
      return False
    rect = view.visualRect(index)
    if view.sizeHintForColumn(index.column()) > rect.width():
      QToolTip.showText(evt.globalPos(), view.model().data(index), view, rect)
      return True
    else:
      QToolTip.hideText()
      return True
    return False


class _ParameterFilter(QWidget):
  changed = pyqtSignal()

  def __init__(self, params, removeCallback):
    super().__init__()
    layout = QGridLayout()
    self._nameComboBox = QComboBox()
    self._nameComboBox.addItems(params)
    self._nameComboBox.currentTextChanged.connect(self.changed.emit)
    layout.addWidget(self._nameComboBox, 0, 0, 1, 5, Qt.AlignmentFlag.AlignLeft)
    layout.addWidget(QLabel('Min:'), 1, 0, Qt.AlignmentFlag.AlignLeft)
    self._minimumSpinbox = QDoubleSpinBox()
    self._minimumSpinbox.setMaximum(sys.float_info.max)
    self._minimumSpinbox.valueChanged.connect(self.changed.emit)
    self._minimumSpinbox.setMinimumWidth(self._minimumSpinbox.minimumSizeHint().width() // 2)
    layout.addWidget(self._minimumSpinbox, 1, 1, Qt.AlignmentFlag.AlignLeft)
    layout.addWidget(QLabel('Max:'), 1, 2, Qt.AlignmentFlag.AlignLeft)
    self._maximumSpinbox = QDoubleSpinBox()
    self._maximumSpinbox.setMaximum(sys.float_info.max)
    self._maximumSpinbox.valueChanged.connect(self.changed.emit)
    self._maximumSpinbox.setMinimumWidth(self._maximumSpinbox.minimumSizeHint().width() // 2)
    layout.addWidget(self._maximumSpinbox, 1, 3, Qt.AlignmentFlag.AlignLeft)
    removeBtn = QPushButton('Remove')
    removeBtn.clicked.connect(removeCallback)
    layout.addWidget(removeBtn, 1, 4, Qt.AlignmentFlag.AlignLeft)
    self.setLayout(layout)

  def updateParams(self, params):
    blocked = self._nameComboBox.blockSignals(True)
    text = self._nameComboBox.currentText()
    self._nameComboBox.clear()
    self._nameComboBox.addItems(params)
    self._nameComboBox.setCurrentText(text)
    self._nameComboBox.blockSignals(blocked)

  def name(self):
    return self._nameComboBox.currentText()

  def minimum(self):
    return self._minimumSpinbox.value()

  def maximum(self):
    return self._maximumSpinbox.value()


class KinematicParametersVisualization(util.CollapsibleSplitter):
  _IGNORE_COLUMNS = {'Trial_ID', 'Well_ID', 'NumBout', 'BoutStart', 'BoutEnd', 'Condition', 'Genotype', 'videoDuration'}
  _FILENAME = 'globalParametersInsideCategories'
  _CHART_SIZE = QSize(580, 435)

  def __init__(self, data):
    super().__init__()
    if data is None:
      data = (None, [], [], [], [])
    experimentName, allParameters, medianParameters, allData, medianData = data
    self._allParameters = allParameters
    self._medianParameters = medianParameters
    self._allData = allData
    self._medianData = medianData
    self._chartScaleFactor = 1
    self._filters = []

    model = QFileSystemModel()
    model.setFilter(QDir.Filter.NoDotAndDotDot | QDir.Filter.Dirs)
    folderPath = os.path.join(paths.getDataAnalysisFolder(), 'resultsKinematic')
    model.setRootPath(folderPath)
    model.setReadOnly(True)
    proxyModel = QSortFilterProxyModel()

    def filterModel(row, parent):
      index = model.index(row, 0, parent)
      if os.path.normpath(model.filePath(index)) == os.path.normpath(folderPath):
        return True
      return bool(self._findResultsFiles(model.fileName(index)))
    proxyModel.filterAcceptsRow = filterModel
    proxyModel.setSourceModel(model)
    self._tree = tree = QTreeView()
    tree.viewport().installEventFilter(_TooltipHelper(tree))
    tree.sizeHint = lambda: QSize(150, 1)
    tree.setModel(proxyModel)
    tree.setRootIsDecorated(False)
    tree.setRootIndex(proxyModel.mapFromSource(model.index(folderPath)))
    tree.header().setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
    for idx in range(1, model.columnCount()):
      tree.hideColumn(idx)
    tree.resizeEvent = lambda evt: tree.setColumnWidth(0, evt.size().width())
    selectionModel = tree.selectionModel()
    if experimentName is not None:
      selectionModel.setCurrentIndex(proxyModel.mapFromSource(model.index(os.path.join(paths.getDataAnalysisFolder(), 'resultsKinematic', experimentName))),
                                     QItemSelectionModel.SelectionFlag.ClearAndSelect)
    selectionModel.currentRowChanged.connect(lambda current, previous: current.row() == -1 or self._readResults(model.fileName(current)))

    self.addWidget(tree)
    self._recreateMainWidget()
    self.setChildrenCollapsible(False)

  def _addFilter(self):
    fltr = _ParameterFilter(self._medianParameters if self._medianPerWellRadioBtn.isChecked() else self._allParameters, lambda: self._removeFilter(fltr))
    fltr.changed.connect(lambda: self._update(clearFigures=True))
    self._filters.append(fltr)
    self._checkboxesLayout.addWidget(fltr, alignment=Qt.AlignmentFlag.AlignLeft)

  def _removeFilter(self, fltr):
    self._filters.remove(fltr)
    self._checkboxesLayout.removeWidget(fltr)
    fltr.setParent(None)
    self._update(clearFigures=True)

  def _recreateMainWidget(self):
    app = QApplication.instance()
    self._paramCheckboxes = {}
    self._figures = {'median': {True: {}, False: {}}, 'all': {True: {}, False: {}}}
    self._filters = []

    layout = QVBoxLayout()
    layout.addWidget(util.apply_style(QLabel("Visualize Kinematic Parameters"), font=app.title_font), alignment=Qt.AlignmentFlag.AlignCenter)

    if self._tree.selectionModel().currentIndex().row() == -1:
      layout.addWidget(QLabel("Select an experiment to visualize kinematic parameters."), alignment=Qt.AlignmentFlag.AlignCenter, stretch=1)
      buttonsLayout = QHBoxLayout()
      buttonsLayout.addStretch(1)
      self._viewProcessedBtn = util.apply_style(QPushButton("View 'plots and processed data' folders"), background_color=util.LIGHT_YELLOW)
      self._viewProcessedBtn.clicked.connect(lambda: app.openAnalysisFolder(app.homeDirectory, 'resultsKinematic'))
      buttonsLayout.addWidget(self._viewProcessedBtn, alignment=Qt.AlignmentFlag.AlignCenter)
      self._viewRawBtn = util.apply_style(QPushButton("View raw data"), background_color=util.LIGHT_YELLOW)
      self._viewRawBtn.clicked.connect(lambda: app.openAnalysisFolder(app.homeDirectory, 'data'))
      buttonsLayout.addWidget(self._viewRawBtn, alignment=Qt.AlignmentFlag.AlignCenter)
      self._linkBtn = util.apply_style(QPushButton("Video data analysis online documentation"), background_color=util.LIGHT_YELLOW)
      self._linkBtn.clicked.connect(lambda: webbrowser.open_new("https://zebrazoom.org/documentation/docs/behaviorAnalysis/behaviorAnalysisGUI"))
      buttonsLayout.addWidget(self._linkBtn, alignment=Qt.AlignmentFlag.AlignCenter)
      self._startPageBtn = util.apply_style(QPushButton("Go to the start page"), background_color=util.LIGHT_CYAN)
      self._startPageBtn.clicked.connect(lambda: app.show_frame("StartPage"))
      buttonsLayout.addWidget(self._startPageBtn, alignment=Qt.AlignmentFlag.AlignCenter)
      buttonsLayout.addStretch(1)
      layout.addLayout(buttonsLayout)

      replace = hasattr(self, '_mainWidget')
      self._mainWidget = QWidget()
      self._mainWidget.setLayout(layout)
      if replace:
        self.replaceWidget(1, self._mainWidget)
      else:
        self.addWidget(self._mainWidget)
      self.setStretchFactor(1, 1)
      return

    middleLayout = QHBoxLayout()
    self._checkboxesLayout = checkboxesLayout = QVBoxLayout()

    checkboxesLayout.addWidget(util.apply_style(QLabel("Visualization options"), font_size='16px'), alignment=Qt.AlignmentFlag.AlignLeft)
    chartScalingLayout = QHBoxLayout()
    chartScalingLayout.addWidget(QLabel('Chart size'), alignment=Qt.AlignmentFlag.AlignLeft)
    self._decreaseScalingBtn = QToolButton()
    self._decreaseScalingBtn.setDefaultAction(QAction('-'))
    self._decreaseScalingBtn.clicked.connect(lambda: setattr(self, '_chartScaleFactor', self._chartScaleFactor * 0.8) or self._update())
    chartScalingLayout.addWidget(self._decreaseScalingBtn, alignment=Qt.AlignmentFlag.AlignLeft)
    self._increaseScalingBtn = QToolButton()
    self._decreaseScalingBtn.sizeHint = self._increaseScalingBtn.sizeHint
    self._increaseScalingBtn.setDefaultAction(QAction('+'))
    self._increaseScalingBtn.clicked.connect(lambda: setattr(self, '_chartScaleFactor', self._chartScaleFactor * 1.25) or self._update())
    chartScalingLayout.addWidget(self._increaseScalingBtn, alignment=Qt.AlignmentFlag.AlignLeft)
    chartScalingLayout.addStretch(1)
    checkboxesLayout.addLayout(chartScalingLayout)
    self._allBoutsRadioBtn = QRadioButton("All bouts")
    self._allBoutsRadioBtn.toggled.connect(lambda: self._update(visualizationOptionsChanged=True))
    checkboxesLayout.addWidget(self._allBoutsRadioBtn, alignment=Qt.AlignmentFlag.AlignLeft)
    self._medianPerWellRadioBtn = QRadioButton("Median per well")
    self._medianPerWellRadioBtn.setChecked(True)
    self._medianPerWellRadioBtn.toggled.connect(lambda: self._update(visualizationOptionsChanged=True))
    checkboxesLayout.addWidget(self._medianPerWellRadioBtn, alignment=Qt.AlignmentFlag.AlignLeft)
    self._plotOutliersAndMeanCheckbox = QCheckBox("Plot outliers and mean")
    self._plotOutliersAndMeanCheckbox.toggled.connect(lambda: self._update(visualizationOptionsChanged=True))
    checkboxesLayout.addWidget(self._plotOutliersAndMeanCheckbox, alignment=Qt.AlignmentFlag.AlignLeft)

    checkboxesLayout.addWidget(util.apply_style(QLabel("Parameters"), font_size='16px'), alignment=Qt.AlignmentFlag.AlignLeft)
    self._selectAllCheckbox = util.apply_style(QCheckBox('Select all'), font_weight='bold')
    self._selectAllCheckbox.stateChanged.connect(self._checkOrUncheckAll)
    checkboxesLayout.addWidget(self._selectAllCheckbox, alignment=Qt.AlignmentFlag.AlignLeft)
    precheckedParams = {'BoutDuration', 'TotalDistance', 'Speed', 'NumberOfOscillations', 'meanTBF', 'maxTailAngleAmplitude'}
    for param in self._allParameters + self._medianParameters:
      if param in self._paramCheckboxes:
        continue
      checkbox = QCheckBox(param)
      if param in precheckedParams:
        checkbox.setChecked(True)
      checkbox.toggled.connect(lambda: self._update())
      self._paramCheckboxes[param] = checkbox
      checkboxesLayout.addWidget(checkbox, alignment=Qt.AlignmentFlag.AlignLeft)

    filtersLayout = QHBoxLayout()
    filtersLayout.addWidget(util.apply_style(QLabel("Filters"), font_size='16px'), alignment=Qt.AlignmentFlag.AlignLeft)
    addFilterBtn = QPushButton("Add new")
    addFilterBtn.clicked.connect(self._addFilter)
    filtersLayout.addWidget(addFilterBtn, alignment=Qt.AlignmentFlag.AlignCenter)
    filtersLayout.addStretch()
    checkboxesLayout.addLayout(filtersLayout)

    checkboxesLayout.addStretch(1)
    checkboxesWidget = QWidget()
    checkboxesWidget.setLayout(checkboxesLayout)
    checkboxesScrollArea = QScrollArea()
    checkboxesScrollArea.setWidgetResizable(True)
    checkboxesScrollArea.setWidget(checkboxesWidget)
    middleLayout.addWidget(checkboxesScrollArea)

    for params, typeDict in zip((self._medianParameters, self._allParameters), self._figures.values()):
      for figuresDict in typeDict.values():
        for param in params:
          figuresDict[param] = FigureCanvas(Figure(figsize=(5.8, 4.35), tight_layout=True))

    self._chartsScrollArea = QScrollArea()
    middleLayout.addWidget(self._chartsScrollArea, stretch=1)
    layout.addLayout(middleLayout)

    buttonsLayout = QHBoxLayout()
    buttonsLayout.addStretch(1)
    self._viewProcessedBtn = util.apply_style(QPushButton("View 'plots and processed data' folders"), background_color=util.LIGHT_YELLOW)
    self._viewProcessedBtn.clicked.connect(lambda: app.openAnalysisFolder(app.homeDirectory, 'resultsKinematic'))
    buttonsLayout.addWidget(self._viewProcessedBtn, alignment=Qt.AlignmentFlag.AlignCenter)
    self._viewRawBtn = util.apply_style(QPushButton("View raw data"), background_color=util.LIGHT_YELLOW)
    self._viewRawBtn.clicked.connect(lambda: app.openAnalysisFolder(app.homeDirectory, 'data'))
    buttonsLayout.addWidget(self._viewRawBtn, alignment=Qt.AlignmentFlag.AlignCenter)
    self._linkBtn = util.apply_style(QPushButton("Video data analysis online documentation"), background_color=util.LIGHT_YELLOW)
    self._linkBtn.clicked.connect(lambda: webbrowser.open_new("https://zebrazoom.org/documentation/docs/behaviorAnalysis/behaviorAnalysisGUI"))
    buttonsLayout.addWidget(self._linkBtn, alignment=Qt.AlignmentFlag.AlignCenter)
    self._startPageBtn = util.apply_style(QPushButton("Go to the start page"), background_color=util.LIGHT_CYAN)
    self._startPageBtn.clicked.connect(lambda: app.show_frame("StartPage"))
    buttonsLayout.addWidget(self._startPageBtn, alignment=Qt.AlignmentFlag.AlignCenter)
    buttonsLayout.addStretch(1)
    layout.addLayout(buttonsLayout)

    replace = hasattr(self, '_mainWidget')
    self._mainWidget = QWidget()
    self._mainWidget.setLayout(layout)
    if replace:
      self.replaceWidget(1, self._mainWidget)
    else:
      self.addWidget(self._mainWidget)
    self.setStretchFactor(1, 1)
    self._update(visualizationOptionsChanged=True)

  def _findResultsFiles(self, folder):
    allBoutsMixedXlsx = os.path.join(paths.getDataAnalysisFolder(), 'resultsKinematic', folder, 'allBoutsMixed', self._FILENAME + '.xlsx')
    allBoutsMixedCsv = os.path.join(paths.getDataAnalysisFolder(), 'resultsKinematic', folder, 'allBoutsMixed', self._FILENAME + '.csv')
    medianPerWellXlsx = os.path.join(paths.getDataAnalysisFolder(), 'resultsKinematic', folder, 'medianPerWellFirst', self._FILENAME + '.xlsx')
    medianPerWellCsv = os.path.join(paths.getDataAnalysisFolder(), 'resultsKinematic', folder, 'medianPerWellFirst', self._FILENAME + '.csv')
    allBouts = allBoutsMixedCsv if os.path.exists(allBoutsMixedCsv) else allBoutsMixedXlsx if os.path.exists(allBoutsMixedXlsx) else None
    median = medianPerWellCsv if os.path.exists(medianPerWellCsv) else medianPerWellXlsx if os.path.exists(medianPerWellXlsx) else None
    if allBouts is None or median is None:
      return None
    return allBouts, median

  def _readResults(self, folder):
    allBoutsMixed, medianPerWell = self._findResultsFiles(folder)
    self._allData = pd.read_csv(allBoutsMixed) if allBoutsMixed.endswith('.csv') else pd.read_excel(allBoutsMixed)
    self._allData = self._allData.loc[:, ~self._allData.columns.str.contains('^Unnamed')]
    self._allParameters = [param for param in self._allData.columns if param not in self._IGNORE_COLUMNS]
    self._medianData = pd.read_csv(medianPerWell) if medianPerWell.endswith('.csv') else pd.read_excel(medianPerWell)
    self._medianData = self._medianData.loc[:, ~self._medianData.columns.str.contains('^Unnamed')]
    self._medianParameters = [param for param in self._medianData.columns if param not in self._IGNORE_COLUMNS]
    self._recreateMainWidget()

  def _createChartsWidget(self, figures):
    if not figures:
      self._chartsScrollArea.setAlignment(Qt.AlignmentFlag.AlignCenter)
      return QLabel("Select one or more parameters to visualize.")
    data = self._medianData if self._medianPerWellRadioBtn.isChecked() else self._allData
    if self._filters:
      data = data.query(' & '.join('%s >= %s & %s <= %s' % (fltr.name(), fltr.minimum(), fltr.name(), fltr.maximum()) for fltr in self._filters))
    if not len(data.index):
      self._chartsScrollArea.setAlignment(Qt.AlignmentFlag.AlignCenter)
      return QLabel("No data found, try adjusting the filters.")
    chartsLayout = QGridLayout()
    chartsWidget = QWidget()
    chartsWidget.setLayout(chartsLayout)
    availableHeight = self._chartsScrollArea.size().height() - 10  # subtract 10 for padding
    chartSize = self._CHART_SIZE * self._chartScaleFactor
    chartHeight = chartSize.height()
    rows = max(1, availableHeight // chartHeight)
    cols = math.ceil(len(figures) / rows)
    row = 0
    col = 0
    for param, figure in figures:
      figure.setFixedSize(chartSize)
      chartsLayout.addWidget(figure, row, col)
      if col < cols - 1:
        col += 1
      else:
        row += 1
        col = 0
      figure.setVisible(True)
      if not figure.figure.get_axes():  # check whether we've already plotted it
        self._plotFigure(param, figure.figure, data)
    self._chartsScrollArea.setAlignment(Qt.AlignmentFlag.AlignLeft)
    return chartsWidget

  def _plotFigure(self, param, figure, data):
    plotOutliersAndMean = self._plotOutliersAndMeanCheckbox.isChecked()
    ax = figure.add_subplot(111)
    b = sns.boxplot(ax=ax, data=data, x="Condition", y=param, hue="Genotype", showmeans=plotOutliersAndMean, showfliers=plotOutliersAndMean)
    b.set_ylabel('', fontsize=0)
    b.set_xlabel('', fontsize=0)
    b.axes.set_title(param, fontsize=20)
    figure.figure.canvas.draw()

  def _iterAllFigures(self):
    for typeDict in self._figures.values():
      for figuresDict in typeDict.values():
        yield from figuresDict.values()

  def _checkOrUncheckAll(self, state):
    self._selectAllCheckbox.setTristate(False)
    checked = state == Qt.CheckState.Checked
    params = self._medianParameters if self._medianPerWellRadioBtn.isChecked() else self._allParameters
    for param in params:
      blocked = self._paramCheckboxes[param].blockSignals(True)
      self._paramCheckboxes[param].setChecked(checked)
      self._paramCheckboxes[param].blockSignals(blocked)
    self._update()

  def _update(self, visualizationOptionsChanged=False, clearFigures=False):
    params = self._medianParameters if self._medianPerWellRadioBtn.isChecked() else self._allParameters
    paramsSet = set(params)
    if visualizationOptionsChanged:
      for param, checkbox in self._paramCheckboxes.items():
        checkbox.setVisible(param in paramsSet)
      for fltr in self._filters[:]:
        if fltr.name() not in paramsSet:
          self._filters.remove(fltr)
          self._checkboxesLayout.removeWidget(fltr)
          fltr.setParent(None)
        else:
          fltr.updateParams(params)
    for figure in self._iterAllFigures():
      if clearFigures:  # nuke cache if filters have changed
        figure.figure.clear()
      figure.hide()
      figure.setParent(None)
    selectedParameters = {param for param, checkbox in self._paramCheckboxes.items() if checkbox.isChecked()}
    allParams = self._medianParameters if self._medianPerWellRadioBtn.isChecked() else self._allParameters
    state = Qt.CheckState.Unchecked if not selectedParameters else Qt.CheckState.Checked if len(selectedParameters) == len(allParams) else Qt.CheckState.PartiallyChecked
    blocked = self._selectAllCheckbox.blockSignals(True)
    self._selectAllCheckbox.setCheckState(state)
    self._selectAllCheckbox.blockSignals(blocked)
    shownFigures = [(param, figure) for param, figure in
                    self._figures['median' if self._medianPerWellRadioBtn.isChecked() else 'all'][self._plotOutliersAndMeanCheckbox.isChecked()].items()
                    if param in selectedParameters]
    self._chartsScrollArea.setWidget(self._createChartsWidget(shownFigures))
