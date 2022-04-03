import os
import pickle
import webbrowser
from pathlib import Path

import json
import pandas as pd

try:
  from PyQt6.QtCore import pyqtSignal, Qt, QAbstractTableModel, QDir, QItemSelectionModel, QModelIndex, QPoint, QPointF, QRect, QRectF, QSize, QSizeF, QStringListModel
  from PyQt6.QtGui import QColor, QFont, QIntValidator, QPainter, QPixmap, QPolygon, QPolygonF, QTransform
  from PyQt6.QtWidgets import QApplication, QCompleter, QFileDialog, QFileSystemModel, QFrame, QGridLayout, QHeaderView, QHBoxLayout, QLabel, QMessageBox, QWidget, QPushButton, QLineEdit, QCheckBox, QVBoxLayout, QRadioButton, QButtonGroup, QScrollArea, QSplitter, QTableView, QTreeView
  PYQT6 = True
except ImportError:
  from PyQt5.QtCore import pyqtSignal, Qt, QAbstractTableModel, QDir, QItemSelectionModel, QModelIndex, QPoint, QPointF, QRect, QRectF, QSize, QSizeF, QStringListModel
  from PyQt5.QtGui import QColor, QFont, QIntValidator, QPainter, QPixmap, QPolygon, QPolygonF, QTransform
  from PyQt5.QtWidgets import QApplication, QCompleter, QFileDialog, QFileSystemModel, QFrame, QGridLayout, QHeaderView, QHBoxLayout, QLabel, QMessageBox, QWidget, QPushButton, QLineEdit, QCheckBox, QVBoxLayout, QRadioButton, QButtonGroup, QScrollArea, QSplitter, QTableView, QTreeView
  PYQT6 = False

import zebrazoom.videoFormatConversion.zzVideoReading as zzVideoReading
import zebrazoom.code.util as util


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
    self._size = None
    self._originalPixmap = None
    self._clickedPosition = None
    self._hoveredPosition = None
    self._expandExisting = False
    self.wellShape = None

  def setWellPositions(self, wellPositions):
    self.setMouseTracking(wellPositions is not None)
    self._wellPositions = wellPositions

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

  def paintEvent(self, evt):
    super().paintEvent(evt)
    app = QApplication.instance()
    if not self._wellPositions:
      return
    qp = QPainter()
    qp.begin(self)
    factory = qp.drawRect if self.wellShape == 'rectangle' else qp.drawEllipse
    font = QFont()
    font.setPointSize(16)
    font.setWeight(QFont.Weight.Bold)
    qp.setFont(font)
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
      qp.drawText(rect, Qt.AlignmentFlag.AlignCenter, str(idx))
      factory(rect)
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


class _DummyFullSet(object):
  def __contains__(self, item):
    return True


class _ExperimentOrganizationModel(QAbstractTableModel):
  _COLUMN_NAMES = ["path", "trial_id", "fq", "pixelsize", "condition", "genotype", "include"]
  _COLUMN_TITLES = [None, "Video", "FPS", "Pixel Size", "Condition", "Genotype", "Include"]
  _DEFAULT_ZZOUTPUT = os.path.join(Path(os.path.dirname(os.path.realpath(__file__))).parent.parent, 'ZZoutput')

  def __init__(self, filename):
    super().__init__()
    self._filename = filename
    self._data = pd.read_excel(filename)

  def rowCount(self, parent=None):
    return self._data.shape[0]

  def columnCount(self, parent=None):
    return len(self._COLUMN_NAMES)

  def updateValues(self, rows, column, indices, newValue):
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

  def saveFile(self):
    self._data.to_excel(self._filename)

  def videoPath(self, row):
    path, folderName = self._data.iloc[row, list(map(self._data.columns.get_loc, self._COLUMN_NAMES[:2]))]
    if path == "defaultZZoutputFolder":
      path = self._DEFAULT_ZZOUTPUT
    return os.path.join(path, folderName)

  def addVideo(self, videoData):
    if videoData["path"] == self._DEFAULT_ZZOUTPUT:
      videoData["path"] = "defaultZZoutputFolder"
    self.beginInsertRows(QModelIndex(), self.rowCount(), self.rowCount())
    self._data = pd.concat([self._data, pd.DataFrame.from_dict(videoData)], ignore_index=True)
    self.endInsertRows()

  def removeSelectedRows(self, idxs):
    self.beginResetModel()
    self._data = self._data.drop(idxs).reset_index(drop=True,)
    self.endResetModel()

  def getExistingConditions(self, rows=None, wells=None):
    if rows is None:
      rows = range(self.rowCount())
    if wells is None:
      wells = _DummyFullSet()
    return sorted({val.strip() for row in rows for idx, val in enumerate(self._data.iloc[row, self._data.columns.get_loc("condition")][1:-1].split(",")) if idx in wells and val.strip()})

  def getExistingGenotypes(self, rows=None, wells=None):
    if rows is None:
      rows = range(self.rowCount())
    if wells is None:
      wells = _DummyFullSet()
    return sorted({val.strip() for row in rows for idx, val in enumerate(self._data.iloc[row, self._data.columns.get_loc("genotype")][1:-1].split(",")) if idx in wells and val.strip()})

  def getInclude(self, rows, wells):
    return {val.strip() for row in rows for idx, val in enumerate(self._data.iloc[row, self._data.columns.get_loc("include")][1:-1].split(",")) if idx in wells}


class CreateExperimentOrganizationExcel(QWidget):
  _POTENTIAL_WELLS_FILENAMES = ("intermediaryWellPosition.txt", "intermediaryWellPositionReloadNoMatterWhat.txt")

  def __init__(self, controller):
    super().__init__(controller.window)
    self.controller = controller
    self._shownVideo = None
    self._previousSelection = {}

    layout = QVBoxLayout()
    layout.addWidget(util.apply_style(QLabel("Prepare experiment organization excel file", self), font=controller.title_font), alignment=Qt.AlignmentFlag.AlignCenter)

    folderPath = os.path.join(Path(os.path.dirname(os.path.realpath(__file__))).parent.parent, 'dataAnalysis' ,'experimentOrganizationExcel')
    model = _ExperimentFilesModel()
    model.setRootPath(folderPath)

    self._tree = tree = _ExperimentTreeView()
    tree.setModel(model)
    for idx in range(1, model.columnCount()):
      tree.hideColumn(idx)
    tree.setRootIndex(model.index(model.rootPath()))
    selectionModel = tree.selectionModel()
    selectionModel.currentRowChanged.connect(lambda current, previous: current.row() == -1 or self._fileSelected(model.filePath(current)))

    treeLayout = QVBoxLayout()
    newExperimentBtn = QPushButton("New experiment")
    newExperimentBtn.clicked.connect(self._newExperiment)
    treeLayout.addWidget(newExperimentBtn, alignment=Qt.AlignmentFlag.AlignLeft)
    treeLayout.addWidget(tree, stretch=1)
    treeWidget = QWidget()
    treeLayout.setContentsMargins(0, 0, 0, 0)
    treeWidget.setLayout(treeLayout)
    horizontalSplitter = QSplitter()
    horizontalSplitter.addWidget(treeWidget)
    verticalSplitter = QSplitter()
    verticalSplitter.setOrientation(Qt.Orientation.Vertical)
    verticalSplitter.setChildrenCollapsible(False)
    tableLayout = QVBoxLayout()
    tableButtonsLayout = QHBoxLayout()
    addVideosBtn = QPushButton("Add video(s)")
    addVideosBtn.clicked.connect(self._addVideos)
    tableButtonsLayout.addWidget(addVideosBtn, alignment=Qt.AlignmentFlag.AlignLeft)
    removeVideosBtn = QPushButton("Remove selected videos")
    removeVideosBtn.clicked.connect(self._removeVideos)
    tableButtonsLayout.addWidget(removeVideosBtn, alignment=Qt.AlignmentFlag.AlignLeft)
    saveChangesBtn = QPushButton("Save changes")
    saveChangesBtn.clicked.connect(lambda: self._table.model().saveFile() or QMessageBox.information(self.controller.window, "Experiment saved", "Changes made to the experiment were saved."))
    tableButtonsLayout.addWidget(saveChangesBtn, alignment=Qt.AlignmentFlag.AlignLeft)
    deleteExperimentBtn = QPushButton("Delete experiment")
    deleteExperimentBtn.clicked.connect(self._removeExperiment)
    tableButtonsLayout.addWidget(deleteExperimentBtn, alignment=Qt.AlignmentFlag.AlignLeft)
    runExperimentBtn = util.apply_style(QPushButton("Run analysis"), background_color=util.LIGHT_YELLOW)
    runExperimentBtn.clicked.connect(self._runExperiment)
    tableButtonsLayout.addWidget(runExperimentBtn, alignment=Qt.AlignmentFlag.AlignLeft)
    tableButtonsLayout.addStretch()
    tableLayout.addLayout(tableButtonsLayout)
    self._table = QTableView()
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
    videoDetailsLayout.addWidget(QLabel("Condition:"), 0, 0, alignment=Qt.AlignmentFlag.AlignLeft)
    self._conditionLineEdit = QLineEdit()
    conditionCompleter = QCompleter()
    conditionCompleter.setModel(QStringListModel())
    conditionCompleter.setCompletionMode(QCompleter.CompletionMode.UnfilteredPopupCompletion)
    self._conditionLineEdit.setCompleter(conditionCompleter)
    self._conditionLineEdit.editingFinished.connect(self._conditionChanged)
    videoDetailsLayout.addWidget(self._conditionLineEdit, 0, 1, alignment=Qt.AlignmentFlag.AlignLeft)
    videoDetailsLayout.addWidget(QLabel("Genotype:"), 1, 0, alignment=Qt.AlignmentFlag.AlignLeft)
    self._genotypeLineEdit = QLineEdit()
    genotypeCompleter = QCompleter()
    genotypeCompleter.setModel(QStringListModel())
    genotypeCompleter.setCompletionMode(QCompleter.CompletionMode.UnfilteredPopupCompletion)
    self._genotypeLineEdit.setCompleter(genotypeCompleter)
    self._genotypeLineEdit.editingFinished.connect(self._genotypeChanged)
    videoDetailsLayout.addWidget(self._genotypeLineEdit, 1, 1, alignment=Qt.AlignmentFlag.AlignLeft)
    self._includeCheckbox = QCheckBox("Include in analysis")
    self._includeCheckbox.stateChanged.connect(self._includeChanged)
    videoDetailsLayout.addWidget(self._includeCheckbox, 3, 0, 1, 2, alignment=Qt.AlignmentFlag.AlignLeft)
    videoDetailsLayout.setRowStretch(4, 1)
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
    startPageBtn = util.apply_style(QPushButton("Go to the start page", self), background_color=util.LIGHT_CYAN)
    startPageBtn.clicked.connect(lambda: controller.show_frame("StartPage"))
    buttonsLayout.addWidget(startPageBtn, alignment=Qt.AlignmentFlag.AlignCenter)
    previousParameterResultsBtn = util.apply_style(QPushButton("View previous kinematic parameter analysis results", self), background_color=util.LIGHT_YELLOW)
    previousParameterResultsBtn.clicked.connect(lambda: controller.show_frame("AnalysisOutputFolderPopulation"))
    buttonsLayout.addWidget(previousParameterResultsBtn, alignment=Qt.AlignmentFlag.AlignCenter)
    previousClusteringResultsBtn = util.apply_style(QPushButton("View previous clustering analysis results", self), background_color=util.LIGHT_YELLOW)
    previousClusteringResultsBtn.clicked.connect(lambda: controller.show_frame("AnalysisOutputFolderClustering"))
    buttonsLayout.addWidget(previousClusteringResultsBtn, alignment=Qt.AlignmentFlag.AlignCenter)
    buttonsLayout.addStretch()
    layout.addLayout(buttonsLayout)

    self.setLayout(layout)

  def _updateConditionCompletion(self):
    self._conditionLineEdit.completer().model().setStringList(self._table.model().getExistingConditions())

  def _updateGenotypeCompletion(self):
    self._genotypeLineEdit.completer().model().setStringList(self._table.model().getExistingGenotypes())

  def _conditionChanged(self):
    condition = self._conditionLineEdit.text()
    self._table.model().updateValues(sorted(set(map(lambda idx: idx.row(), self._table.selectionModel().selectedIndexes()))), 4, self._frame.getWells(), condition)
    self._updateConditionCompletion()

  def _genotypeChanged(self):
    genotype = self._genotypeLineEdit.text()
    self._table.model().updateValues(sorted(set(map(lambda idx: idx.row(), self._table.selectionModel().selectedIndexes()))), 5, self._frame.getWells(), genotype)
    self._updateGenotypeCompletion()

  def _includeChanged(self, state):
    checked = int(state == Qt.CheckState.Checked)
    self._table.model().updateValues(sorted(set(map(lambda idx: idx.row(), self._table.selectionModel().selectedIndexes()))), 6, self._frame.getWells(), checked)
    self._includeCheckbox.setTristate(False)

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

  def _addVideos(self):
    selectedFolder = QFileDialog.getExistingDirectory(self.controller.window, "Select a results folder", self.controller.ZZoutputLocation)
    if not selectedFolder:
      return
    wellPositions = self._getWellPositions(selectedFolder)
    if wellPositions is None:
      return
    numWells = 1 if not wellPositions else len(wellPositions)
    emptyArray = ["[%s]" % ','.join(" " for _ in range(numWells))]
    includeArray = ["[%s]" % ', '.join("1" for _ in range(numWells))]
    model = self._table.model()
    model.addVideo({"path": [os.path.dirname(selectedFolder)], "trial_id": [os.path.basename(selectedFolder)], "fq": [" "], "pixelsize": [" "], "condition": emptyArray, "genotype": emptyArray, "include": includeArray})
    model.insertRow(model.rowCount())
    self._table.selectionModel().setCurrentIndex(model.index(model.rowCount() - 1, 1), QItemSelectionModel.SelectionFlag.ClearAndSelect)

  def _removeVideos(self):
    selectedIdxs = sorted(set(map(lambda idx: idx.row(), self._table.selectionModel().selectedIndexes())))
    self._table.model().removeSelectedRows(selectedIdxs)
    self._videoSelected(None)

  def _newExperiment(self):
    number = 1
    while os.path.exists(os.path.join(self._tree.model().rootPath(), 'Experiment %d.xls' % number)):
      number += 1
    path = os.path.join(self._tree.model().rootPath(), 'Experiment %d.xls' % number)
    pd.DataFrame(columns=_ExperimentOrganizationModel._COLUMN_NAMES).to_excel(path)
    index = self._tree.model().index(path)
    self._tree.selectionModel().setCurrentIndex(index, QItemSelectionModel.SelectionFlag.ClearAndSelect)
    self._tree.edit(index)

  def _removeExperiment(self):
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
    conditions = self._table.model().getExistingConditions(rows, wells) or ['']
    if len(conditions) == 1:
      self._conditionLineEdit.setText(conditions[0])
      self._conditionLineEdit.setPlaceholderText('')
      self._conditionLineEdit.setToolTip(None)
    else:
      self._conditionLineEdit.setText('')
      text = '[%s]' % ', '.join(conditions)
      self._conditionLineEdit.setPlaceholderText(text)
      self._conditionLineEdit.setToolTip(text)
    genotypes = self._table.model().getExistingGenotypes(rows, wells) or ['']
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

  def _runExperiment(self):
    path = self._tree.model().filePath(self._tree.selectionModel().currentIndex())
    self.controller.experimentOrganizationExcel = os.path.basename(path)
    self.controller.experimentOrganizationExcelFileAndFolder = os.path.dirname(path)
    self.controller.show_frame("ChooseDataAnalysisMethod")


class ChooseDataAnalysisMethod(QWidget):
  def __init__(self, controller):
    super().__init__(controller.window)
    self.controller = controller

    layout = QVBoxLayout()
    layout.addWidget(util.apply_style(QLabel("Choose the analysis you want to perform:", self), font=controller.title_font), alignment=Qt.AlignmentFlag.AlignCenter)

    compareBtn = util.apply_style(QPushButton("Compare populations with kinematic parameters", self), background_color=util.LIGHT_YELLOW)
    compareBtn.clicked.connect(lambda: controller.show_frame("PopulationComparison"))
    layout.addWidget(compareBtn, alignment=Qt.AlignmentFlag.AlignCenter)
    clusterBtn = util.apply_style(QPushButton("Cluster bouts of movements  (for zebrafish only)", self), background_color=util.LIGHT_YELLOW)
    clusterBtn.clicked.connect(lambda: controller.show_frame("BoutClustering"))
    layout.addWidget(clusterBtn, alignment=Qt.AlignmentFlag.AlignCenter)

    startPageBtn = util.apply_style(QPushButton("Go to the start page", self), background_color=util.LIGHT_CYAN)
    startPageBtn.clicked.connect(lambda: controller.show_frame("StartPage"))
    layout.addWidget(startPageBtn, alignment=Qt.AlignmentFlag.AlignCenter)

    self.setLayout(layout)


class PopulationComparison(QWidget):
  def __init__(self, controller):
    super().__init__(controller.window)
    self.controller = controller

    layout = QVBoxLayout()
    layout.addWidget(util.apply_style(QLabel("Population Comparison:", self), font=controller.title_font), alignment=Qt.AlignmentFlag.AlignCenter)

    tailTrackingParametersCheckbox = QCheckBox("I want fish tail tracking related kinematic parameters (number of oscillation, tail beat frequency, etc..) to be calculated.", self)
    layout.addWidget(tailTrackingParametersCheckbox, alignment=Qt.AlignmentFlag.AlignCenter)
    saveInMatlabFormatCheckbox = QCheckBox("The result structure is always saved in the pickle format. Also save it in the matlab format.", self)
    layout.addWidget(saveInMatlabFormatCheckbox, alignment=Qt.AlignmentFlag.AlignCenter)
    saveRawDataCheckbox = QCheckBox("Save original raw data in result structure.", self)
    layout.addWidget(saveRawDataCheckbox, alignment=Qt.AlignmentFlag.AlignCenter)
    forcePandasRecreation = QCheckBox("Force recalculation of all parameters even if they have already been calculated and saved.", self)
    layout.addWidget(forcePandasRecreation, alignment=Qt.AlignmentFlag.AlignCenter)

    layout.addWidget(util.apply_style(QLabel("Number of frames between each frame used for distance calculation (to avoid noise due to close-by subsequent points) (default value is 4):", self), font=QFont("Helvetica", 10)), alignment=Qt.AlignmentFlag.AlignCenter)
    frameStepForDistanceCalculation = QLineEdit(controller.window)
    frameStepForDistanceCalculation.setValidator(QIntValidator(frameStepForDistanceCalculation))
    frameStepForDistanceCalculation.validator().setBottom(0)
    layout.addWidget(frameStepForDistanceCalculation, alignment=Qt.AlignmentFlag.AlignCenter)

    layout.addWidget(util.apply_style(QLabel("If you are calculating fish tail tracking related kinematic parameters:", self), font_size="16px"), alignment=Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(util.apply_style(QLabel("What's the minimum number of bends a bout should have to be taken into account for the analysis?", self), font=QFont("Helvetica", 10)), alignment=Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(util.apply_style(QLabel("(the default value is 3) (put 0 if you want all bends to be taken into account)", self), font=QFont("Helvetica", 10)), alignment=Qt.AlignmentFlag.AlignCenter)
    minNbBendForBoutDetect = QLineEdit(controller.window)
    minNbBendForBoutDetect.setValidator(QIntValidator(minNbBendForBoutDetect))
    minNbBendForBoutDetect.validator().setBottom(0)
    layout.addWidget(minNbBendForBoutDetect, alignment=Qt.AlignmentFlag.AlignCenter)

    layout.addWidget(util.apply_style(QLabel("If, for a bout, the tail tracking related kinematic parameters are being discarded because of a low amount of bends,", self), font=QFont("Helvetica", 10)), alignment=Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(util.apply_style(QLabel("should the BoutDuration, TotalDistance, Speed and IBI also be discarded for that bout?", self), font=QFont("Helvetica", 10)), alignment=Qt.AlignmentFlag.AlignCenter)
    discardRadioButton = QRadioButton("Yes, discard BoutDuration, TotalDistance, Speed and IBI in that situation", self)
    discardRadioButton.setChecked(True)
    layout.addWidget(discardRadioButton, alignment=Qt.AlignmentFlag.AlignCenter)
    keepRadioButton = QRadioButton("No, keep BoutDuration, TotalDistance, Speed and IBI in that situation", self)
    layout.addWidget(keepRadioButton, alignment=Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(util.apply_style(QLabel("Please ignore the two questions above if you're only looking at BoutDuration, TotalDistance, Speed and IBI.", self), font=QFont("Helvetica", 10)), alignment=Qt.AlignmentFlag.AlignCenter)

    launchBtn = util.apply_style(QPushButton("Launch Analysis", self), background_color=util.LIGHT_YELLOW)
    launchBtn.clicked.connect(lambda: controller.populationComparison(controller, tailTrackingParametersCheckbox.isChecked(), saveInMatlabFormatCheckbox.isChecked(), saveRawDataCheckbox.isChecked(), forcePandasRecreation.isChecked(), minNbBendForBoutDetect.text(), discardRadioButton.isChecked(), keepRadioButton.isChecked(), frameStepForDistanceCalculation.text()))
    layout.addWidget(launchBtn, alignment=Qt.AlignmentFlag.AlignCenter)
    startPageBtn = util.apply_style(QPushButton("Go to the start page", self), background_color=util.LIGHT_CYAN)
    startPageBtn.clicked.connect(lambda: controller.show_frame("StartPage"))
    layout.addWidget(startPageBtn, alignment=Qt.AlignmentFlag.AlignCenter)

    self.setLayout(layout)


class BoutClustering(QWidget):
  def __init__(self, controller):
    super().__init__(controller.window)
    self.controller = controller

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


    layout.addWidget(util.apply_style(QLabel("What's the minimum number of bends a bout should have to be taken into account for the analysis?", self), font=QFont("Helvetica", 10)), alignment=Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(util.apply_style(QLabel("(the default value is 3) (put 0 if you want all bends to be taken into account)", self), font=QFont("Helvetica", 10)), alignment=Qt.AlignmentFlag.AlignCenter)
    minNbBendForBoutDetect = QLineEdit(controller.window)
    minNbBendForBoutDetect.setValidator(QIntValidator(minNbBendForBoutDetect))
    minNbBendForBoutDetect.validator().setBottom(0)
    layout.addWidget(minNbBendForBoutDetect, alignment=Qt.AlignmentFlag.AlignCenter)

    layout.addWidget(util.apply_style(QLabel("Optional: generate videos containing the most representative bouts for each cluster: enter below the number of bouts for each video:", self), font=QFont("Helvetica", 10)), alignment=Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(util.apply_style(QLabel("(leave blank if you don't want any such cluster validation videos to be generated)", self), font=QFont("Helvetica", 10)), alignment=Qt.AlignmentFlag.AlignCenter)
    nbVideosToSave = QLineEdit(controller.window)
    nbVideosToSave.setValidator(QIntValidator(nbVideosToSave))
    nbVideosToSave.validator().setBottom(0)
    layout.addWidget(nbVideosToSave, alignment=Qt.AlignmentFlag.AlignCenter)

    modelUsedForClusteringCheckbox = QCheckBox("Use GMM clustering method instead of Kmeans (clustering method used by default)", self)
    layout.addWidget(modelUsedForClusteringCheckbox, alignment=Qt.AlignmentFlag.AlignCenter)
    removeOutliersCheckbox = QCheckBox("Remove outliers before clustering", self)
    layout.addWidget(removeOutliersCheckbox, alignment=Qt.AlignmentFlag.AlignCenter)

    layout.addWidget(util.apply_style(QLabel("Number of frames between each frame used for distance calculation (to avoid noise due to close-by subsequent points) (default value is 4):", self), font=QFont("Helvetica", 10)), alignment=Qt.AlignmentFlag.AlignCenter)
    frameStepForDistanceCalculation = QLineEdit(controller.window)
    frameStepForDistanceCalculation.setValidator(QIntValidator(frameStepForDistanceCalculation))
    frameStepForDistanceCalculation.validator().setBottom(0)
    layout.addWidget(frameStepForDistanceCalculation, alignment=Qt.AlignmentFlag.AlignCenter)
    
    removeBoutsContainingNanValuesInParametersUsedForClustering = QCheckBox("Remove bouts containing nan values in parameters used for clustering", self)
    removeBoutsContainingNanValuesInParametersUsedForClustering.setChecked(True)
    layout.addWidget(removeBoutsContainingNanValuesInParametersUsedForClustering, alignment=Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(util.apply_style(QLabel("If the box above is un-checked, the nan values will be replaced by zeros and no bouts will be removed.", self), font=QFont("Helvetica", 10)), alignment=Qt.AlignmentFlag.AlignCenter)
    
    forcePandasRecreation = QCheckBox("Force recalculation of all parameters even if they have already been calculated and saved.", self)
    layout.addWidget(forcePandasRecreation, alignment=Qt.AlignmentFlag.AlignCenter)

    launchBtn = util.apply_style(QPushButton("Launch Analysis", self), background_color=util.LIGHT_YELLOW)
    launchBtn.clicked.connect(lambda: controller.boutClustering(controller, nbClustersToFind.text(), freelySwimmingRadioButton.isChecked(), headEmbeddedRadioButton.isChecked(), minNbBendForBoutDetect.text(), nbVideosToSave.text(), modelUsedForClusteringCheckbox.isChecked(), removeOutliersCheckbox.isChecked(), frameStepForDistanceCalculation.text(), removeBoutsContainingNanValuesInParametersUsedForClustering.isChecked(), forcePandasRecreation.isChecked()))
    layout.addWidget(launchBtn, alignment=Qt.AlignmentFlag.AlignCenter)
    startPageBtn = util.apply_style(QPushButton("Go to the start page", self), background_color=util.LIGHT_CYAN)
    startPageBtn.clicked.connect(lambda: controller.show_frame("StartPage"))
    layout.addWidget(startPageBtn, alignment=Qt.AlignmentFlag.AlignCenter)

    self.setLayout(layout)


class AnalysisOutputFolderPopulation(QWidget):
  def __init__(self, controller):
    super().__init__(controller.window)
    self.controller = controller

    layout = QVBoxLayout()
    layout.addWidget(util.apply_style(QLabel("View Analysis Output:", self), font=controller.title_font), alignment=Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(QLabel("Click the button below to open the folder that contains the results of the analysis.", self), alignment=Qt.AlignmentFlag.AlignCenter)

    viewProcessedBtn = util.apply_style(QPushButton("View 'plots and processed data' folders", self), background_color=util.LIGHT_YELLOW)
    viewProcessedBtn.clicked.connect(lambda: controller.openAnalysisFolder(controller.homeDirectory, 'resultsKinematic'))
    layout.addWidget(viewProcessedBtn, alignment=Qt.AlignmentFlag.AlignCenter)
    viewRawBtn = util.apply_style(QPushButton("View raw data", self), background_color=util.LIGHT_YELLOW)
    viewRawBtn.clicked.connect(lambda: controller.openAnalysisFolder(controller.homeDirectory, 'data'))
    layout.addWidget(viewRawBtn, alignment=Qt.AlignmentFlag.AlignCenter)
    startPageBtn = util.apply_style(QPushButton("Go to the start page", self), background_color=util.LIGHT_CYAN)
    startPageBtn.clicked.connect(lambda: controller.show_frame("StartPage"))
    layout.addWidget(startPageBtn, alignment=Qt.AlignmentFlag.AlignCenter)

    linkBtn = util.apply_style(QPushButton("Video data analysis online documentation", self), background_color=util.LIGHT_YELLOW)
    linkBtn.clicked.connect(lambda: webbrowser.open_new("https://zebrazoom.org/documentation/docs/behaviorAnalysis/behaviorAnalysisGUI"))
    layout.addWidget(linkBtn, alignment=Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(QLabel("(read the 'Further analyzing ZebraZoom's output through the Graphical User Interface' section)", self), alignment=Qt.AlignmentFlag.AlignCenter)

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
