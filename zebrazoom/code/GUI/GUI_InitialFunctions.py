import cv2
import contextlib
import re
import os
import json
import shutil
import sys
import subprocess
from functools import partial
from multiprocessing import Pool

from matplotlib.figure import Figure
import math
import scipy.io as sio
import pandas as pd
from zebrazoom.code.vars import getGlobalVariables
globalVariables = getGlobalVariables()

from zebrazoom.mainZZ import mainZZ
from zebrazoom.getTailExtremityFirstFrame import getTailExtremityFirstFrame
import zebrazoom.code.paths as paths
import zebrazoom.code.util as util

from PyQt5.QtCore import Qt, QAbstractTableModel, QItemSelection, QItemSelectionModel, QModelIndex, QSize, QUrl
from PyQt5.QtGui import QDesktopServices
from PyQt5.QtWidgets import QAbstractItemView, QApplication, QCheckBox, QFileDialog, QFileSystemModel, QFrame, QHBoxLayout, QHeaderView, QLabel, QLineEdit, QListView, QMessageBox, QPushButton, QScrollArea, QSpacerItem, QSpinBox, QTableView, QTextEdit, QTreeView, QVBoxLayout, QWidget


LARGE_FONT= ("Verdana", 12)

def chooseVideoToAnalyze(self, justExtractParams, noValidationVideo, chooseFrames):
    videoName, _ = QFileDialog.getOpenFileName(self.window, 'Select file', os.path.expanduser("~"))
    if not videoName:
      return
    ZZargs = ([videoName],)
    ZZkwargs = {'justExtractParams': justExtractParams, 'noValidationVideo': noValidationVideo}

    if chooseFrames:
      def beginningAndEndChosen():
        if "firstFrame" in self.configFile:
          ZZkwargs['firstFrame'] = self.configFile["firstFrame"]
        if "lastFrame" in self.configFile:
          ZZkwargs['lastFrame'] = self.configFile["lastFrame"]
        self.configFile.clear()
        ZZkwargs['backgroundExtractionForceUseAllVideoFrames'] = backgroundExtractionForceUseAllVideoFramesCheckbox.isChecked()
        self.show_frame("ConfigFilePromp")
        self.window.centralWidget().layout().currentWidget().setArgs(ZZargs, ZZkwargs)
      layout = QVBoxLayout()
      backgroundExtractionForceUseAllVideoFramesCheckbox = QCheckBox("Use all frames to calculate background")
      backgroundExtractionForceUseAllVideoFramesCheckbox.setChecked(True)
      layout.addWidget(backgroundExtractionForceUseAllVideoFramesCheckbox, alignment=Qt.AlignmentFlag.AlignCenter)
      util.chooseBeginningPage(self, videoName, "Choose where the analysis of your video should start.", "Ok, I want the tracking to start at this frame!",
                               lambda: util.chooseEndPage(self, videoName, "Choose where the analysis of your video should end.", "Ok, I want the tracking to end at this frame!", beginningAndEndChosen),
                               additionalLayout=layout)
    else:
      self.show_frame("ConfigFilePromp")
      self.window.centralWidget().layout().currentWidget().setArgs(ZZargs, ZZkwargs)


class _VideoFilesModel(QFileSystemModel):
  def __init__(self):
    super().__init__()
    self.setReadOnly(False)
    self.setNameFilterDisables(False)
    self.setNameFilters(("*.csv",))

  def data(self, index, role=Qt.ItemDataRole.DisplayRole):
    data = super().data(index, role=role)
    if role == Qt.ItemDataRole.EditRole:
      return os.path.splitext(data)[0]
    return data

  def setData(self, index, value, role=None):
    extension = os.path.splitext(self.data(index))[1]
    return super().setData(index, "%s%s" % (value, extension), role=role)


class _TrackingConfigurationsTreeView(QTreeView):
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


class _VideosModel(QAbstractTableModel):
  _COLUMN_TITLES = ["Video", "Config"]
  _DEFAULT_ZZOUTPUT = paths.getDefaultZZoutputFolder()

  def __init__(self, filename):
    super().__init__()
    data = pd.read_csv(filename).fillna('')
    self._videos = data['Video'].tolist()
    self._configs = data['Config'].tolist()

  def rowCount(self, parent=None):
    return len(self._videos)

  def columnCount(self, parent=None):
    return len(self._COLUMN_TITLES)

  def data(self, index, role=Qt.ItemDataRole.DisplayRole):
    if index.isValid() and role in (Qt.ItemDataRole.DisplayRole, Qt.ItemDataRole.EditRole, Qt.ItemDataRole.ToolTipRole):
      return self._videos[index.row()] if index.column() == 0 else self._configs[index.row()]
    return None

  def headerData(self, col, orientation, role):
    if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
      return self._COLUMN_TITLES[col]
    return None

  def addVideos(self, videos):
    if videos is None:
      return
    videos = [video for video in videos if video not in self._videos]
    self.beginInsertRows(QModelIndex(), self.rowCount(), self.rowCount() + len(videos) - 1)
    self._videos.extend(videos)
    self._configs.extend([''] * len(videos))
    self.endInsertRows()

  def setConfigs(self, idxs, config):
    if config is None:
      return
    self.beginResetModel()
    for idx in idxs:
      self._configs[idx] = config
    self.endResetModel()

  def removeSelectedRows(self, idxs):
    self.beginResetModel()
    for idx in reversed(sorted(idxs)):
      del self._videos[idx]
      del self._configs[idx]
    self.endResetModel()

  def getData(self):
    return self._videos, self._configs

  def hasUnsavedChanges(self, filename):
    if not os.path.exists(filename):  # file was deleted
      return False
    fileData = pd.read_csv(filename).fillna('')
    return not (fileData['Video'].tolist() == self._videos and fileData['Config'].tolist() == self._configs)

  def saveFile(self, filename):
    pd.DataFrame(columns=_VideosModel._COLUMN_TITLES, data=zip(self._videos, self._configs)).to_csv(filename, index=False)


class _TrackingConfigurationsSelectionModel(QItemSelectionModel):
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


class _VideoSelectionPage(QWidget):
  _VIDEO_EXTENSIONS = {'.264', '.3g2', '.3gp', '.3gp2', '.3gpp', '.3gpp2', '.3mm', '.3p2', '.60d', '.787', '.89', '.aaf', '.aec', '.aep', '.aepx', '.aet', '.aetx', '.ajp',
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
                       '.wvx', '.xej', '.xel', '.xesc', '.xfl', '.xlmv', '.xmv', '.xvid', '.y4m', '.yog', '.yuv', '.zeg', '.zm1', '.zm2', '.zm3', '.zmv'}

  def __init__(self, ZZkwargs):
    super().__init__()
    self._ZZkwargs = ZZkwargs

    app = QApplication.instance()

    layout = QVBoxLayout()
    layout.addWidget(util.apply_style(QLabel("Select videos and corresponding config files"), font=app.title_font), alignment=Qt.AlignmentFlag.AlignCenter)

    if ZZkwargs.get('sbatchMode', False):
      replaceLayout = QHBoxLayout()
      replaceLayout.addWidget(QLabel('Replace'), alignment=Qt.AlignmentFlag.AlignCenter)
      self._originalLineEdit = QLineEdit()
      self._originalLineEdit.setText('//l2export/iss02.')
      replaceLayout.addWidget(self._originalLineEdit, alignment=Qt.AlignmentFlag.AlignCenter)
      replaceLayout.addWidget(QLabel('with'), alignment=Qt.AlignmentFlag.AlignCenter)
      self._replaceLineEdit = QLineEdit()
      self._replaceLineEdit.setText('/network/lustre/iss02/')
      replaceLayout.addWidget(self._replaceLineEdit, alignment=Qt.AlignmentFlag.AlignCenter)
      replaceLayout.addWidget(QLabel('in all paths'), alignment=Qt.AlignmentFlag.AlignCenter)
      replaceLayout.addStretch()
      layout.addLayout(replaceLayout)
    else:
      parallelTrackingLayout = QHBoxLayout()
      self._parallelTrackingCheckbox = QCheckBox("Track multiple videos in parallel")
      self._parallelTrackingCheckbox.setChecked(True)
      self._parallelTrackingCheckbox.toggled.connect(lambda checked: self._processesLabel.setVisible(checked) or self._processesSpinBox.setVisible(checked))
      self._parallelTrackingCheckbox.setVisible(False)
      parallelTrackingLayout.addWidget(self._parallelTrackingCheckbox, alignment=Qt.AlignmentFlag.AlignCenter)
      self._processesLabel = QLabel('Number of processes:')
      self._processesLabel.setVisible(False)
      parallelTrackingLayout.addWidget(self._processesLabel, alignment=Qt.AlignmentFlag.AlignCenter)
      self._processesSpinBox = QSpinBox()
      self._processesSpinBox.setVisible(False)
      self._processesSpinBox.setValue(4)
      self._processesSpinBox.setRange(1, os.cpu_count())
      parallelTrackingLayout.addWidget(self._processesSpinBox, alignment=Qt.AlignmentFlag.AlignCenter)
      parallelTrackingLayout.addStretch()
      layout.addLayout(parallelTrackingLayout)

    folderPath = os.path.join(paths.getRootDataFolder(), 'trackingConfigurations')
    if not os.path.exists(folderPath):
      os.makedirs(folderPath)
    model = _VideoFilesModel()
    model.setRootPath(folderPath)
    self._tree = tree = _TrackingConfigurationsTreeView()
    tree.setModel(model)
    for idx in range(1, model.columnCount()):
      tree.hideColumn(idx)
    tree.setRootIndex(model.index(model.rootPath()))
    self._table = QTableView()
    selectionModel = _TrackingConfigurationsSelectionModel(app.window, self._table, model)
    tree.setSelectionModel(selectionModel)
    selectionModel.currentRowChanged.connect(lambda current, previous: current.row() == -1 or self._fileSelected(model.filePath(current)))

    treeLayout = QVBoxLayout()
    self._newConfigurationBtn = QPushButton("New configuration")
    self._newConfigurationBtn.clicked.connect(self._newConfiguration)
    treeLayout.addWidget(self._newConfigurationBtn, alignment=Qt.AlignmentFlag.AlignLeft)
    treeLayout.addWidget(tree, stretch=1)
    treeWidget = QWidget()
    treeLayout.setContentsMargins(0, 0, 0, 0)
    treeWidget.setLayout(treeLayout)
    horizontalSplitter = util.CollapsibleSplitter()
    horizontalSplitter.addWidget(treeWidget)

    tableLayout = QVBoxLayout()
    tableButtonsLayout = QHBoxLayout()
    self._addVideosBtn = QPushButton("Add video(s)")
    self._addVideosBtn.clicked.connect(self._addVideos)
    self._addVideosBtn.clicked.connect(self._updateParallelTracking)
    tableButtonsLayout.addWidget(self._addVideosBtn, alignment=Qt.AlignmentFlag.AlignLeft)
    self._addFolderBtn = QPushButton("Add folder")
    self._addFolderBtn.clicked.connect(self._addFolder)
    self._addFolderBtn.clicked.connect(self._updateParallelTracking)
    tableButtonsLayout.addWidget(self._addFolderBtn, alignment=Qt.AlignmentFlag.AlignLeft)
    self._addMultipleFoldersBtn = QPushButton("Add multiple folders")
    self._addMultipleFoldersBtn.clicked.connect(self._addMultipleFolders)
    self._addMultipleFoldersBtn.clicked.connect(self._updateParallelTracking)
    tableButtonsLayout.addWidget(self._addMultipleFoldersBtn, alignment=Qt.AlignmentFlag.AlignLeft)
    chooseConfigsBtn = QPushButton("Choose config for selected videos")
    chooseConfigsBtn.clicked.connect(lambda: self._table.model().setConfigs(sorted(set(map(lambda idx: idx.row(), self._table.selectionModel().selectedIndexes()))),
                                                                           QFileDialog.getOpenFileName(app.window, 'Select config file', paths.getConfigurationFolder(), "JSON (*.json)")[0]))
    chooseConfigsBtn.clicked.connect(self._updateParallelTracking)
    tableButtonsLayout.addWidget(chooseConfigsBtn, alignment=Qt.AlignmentFlag.AlignLeft)
    removeVideosBtn = QPushButton("Remove selected videos")
    removeVideosBtn.clicked.connect(lambda: self._table.model().removeSelectedRows(sorted(set(map(lambda idx: idx.row(), self._table.selectionModel().selectedIndexes())))))
    removeVideosBtn.clicked.connect(self._updateParallelTracking)
    tableButtonsLayout.addWidget(removeVideosBtn, alignment=Qt.AlignmentFlag.AlignLeft)
    saveChangesBtn = QPushButton("Save changes")
    saveChangesBtn.clicked.connect(lambda: self._table.model().saveFile(self._tree.model().filePath(selectionModel.currentIndex())) or QMessageBox.information(app.window, "Configuration saved", "Changes made to the configuration were saved."))
    tableButtonsLayout.addWidget(saveChangesBtn, alignment=Qt.AlignmentFlag.AlignLeft)
    deleteConfigurationBtn = QPushButton("Delete configuration")
    deleteConfigurationBtn.clicked.connect(self._removeConfiguration)
    tableButtonsLayout.addWidget(deleteConfigurationBtn, alignment=Qt.AlignmentFlag.AlignLeft)
    openConfigurationsFolderBtn = QPushButton("Open configurations folder")
    openConfigurationsFolderBtn.clicked.connect(lambda: QDesktopServices.openUrl(QUrl.fromLocalFile(folderPath)))
    tableButtonsLayout.addWidget(openConfigurationsFolderBtn, alignment=Qt.AlignmentFlag.AlignLeft)
    self._runTrackingBtn = util.apply_style(QPushButton("Run tracking"), background_color=util.DEFAULT_BUTTON_COLOR)
    self._runTrackingBtn.clicked.connect(self._unsavedChangesWarning(lambda *_: self._runTracking(), forceSave=True))
    tableButtonsLayout.addWidget(self._runTrackingBtn, alignment=Qt.AlignmentFlag.AlignLeft)
    tableButtonsLayout.addStretch()
    tableLayout.addLayout(tableButtonsLayout)
    tableLayout.addWidget(self._table, stretch=1)

    self._mainWidget = QWidget()
    tableLayout.setContentsMargins(0, 0, 0, 0)
    self._mainWidget.setLayout(tableLayout)

    scrollArea = QScrollArea()
    scrollArea.setFrameShape(QFrame.Shape.NoFrame)
    scrollArea.setWidgetResizable(True)
    scrollArea.setWidget(self._mainWidget)
    horizontalSplitter.addWidget(scrollArea)
    horizontalSplitter.setStretchFactor(1, 1)
    horizontalSplitter.setChildrenCollapsible(False)
    layout.addWidget(horizontalSplitter, stretch=1)

    buttonsLayout = QHBoxLayout()
    buttonsLayout.addStretch()
    startPageBtn = QPushButton("Go to the start page")
    startPageBtn.clicked.connect(self._unsavedChangesWarning(lambda *_: app.show_frame("StartPage")))
    buttonsLayout.addWidget(startPageBtn, alignment=Qt.AlignmentFlag.AlignCenter)
    buttonsLayout.addStretch()
    layout.addLayout(buttonsLayout)

    self.setLayout(layout)
    self._mainWidget.hide()

  @contextlib.contextmanager
  def __selectAddedRows(self):
    app = QApplication.instance()
    model = self._table.model()
    firstNewRow = model.rowCount()
    yield
    if firstNewRow == model.rowCount():
      return  # no videos added
    addedRows = QItemSelection()
    addedRows.select(model.index(firstNewRow, 0), model.index(model.rowCount() - 1, 0))
    self._table.selectionModel().setCurrentIndex(model.index(firstNewRow, 0), QItemSelectionModel.SelectionFlag.ClearAndSelect | QItemSelectionModel.SelectionFlag.Rows)
    self._table.selectionModel().select(addedRows, QItemSelectionModel.SelectionFlag.ClearAndSelect | QItemSelectionModel.SelectionFlag.Rows)
    self._table.setFocus()

  def _addVideos(self):
    app = QApplication.instance()
    with self.__selectAddedRows():
      self._table.model().addVideos(QFileDialog.getOpenFileNames(app.window, 'Select one or more videos', os.path.expanduser("~"), "Video files (%s)" % ' '.join('*%s' % ext for ext in self._VIDEO_EXTENSIONS))[0])

  def _addFolder(self):
    app = QApplication.instance()
    selectedFolder = QFileDialog.getExistingDirectory(app.window, "Select a folder", os.path.expanduser("~"))
    if selectedFolder is None:
      return
    with self.__selectAddedRows():
      return self._table.model().addVideos([os.path.normpath(os.path.join(root, f)) for root, _dirs, files in os.walk(selectedFolder) for f in files if os.path.splitext(f)[1] in self._VIDEO_EXTENSIONS])

  def _addMultipleFolders(self):
    app = QApplication.instance()
    dialog = QFileDialog(app.window)
    dialog.setWindowTitle('Select one or more folders (use Ctrl or Shift key to select multiple)')
    dialog.setDirectory(os.path.expanduser("~"))
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
    with self.__selectAddedRows():
      self._table.model().addVideos([os.path.normpath(os.path.join(root, f)) for path in dialog.selectedFiles()
                                     for root, _dirs, files in os.walk(path) for f in files if os.path.splitext(f)[1] in self._VIDEO_EXTENSIONS])

  def _updateParallelTracking(self):
    if self._ZZkwargs.get('sbatchMode', False):
      return
    videos, configs = self._table.model().getData()
    enabled = bool(configs)
    for config in configs:
      if not os.path.exists(config):
        enabled = False
        break
      with open(config) as f:
        cfg = json.load(f)
      if not (cfg.get('fasterMultiprocessing', False) or cfg.get('headEmbeded', False)):
        enabled = False
        break
    self._parallelTrackingCheckbox.setVisible(enabled)
    self._processesLabel.setVisible(enabled and self._parallelTrackingCheckbox.isChecked())
    self._processesSpinBox.setVisible(enabled and self._parallelTrackingCheckbox.isChecked())

  def _unsavedChangesWarning(self, fn, forceSave=False):
    app = QApplication.instance()
    def inner(*args, **kwargs):
      if forceSave:
        text = "Do you want to save the changes and proceed?"
      else:
        text = "Are you sure you want to proceed? Unsaved changes will be lost."
      filename = self._tree.model().filePath(self._tree.selectionModel().currentIndex())
      if self._table.model() is not None and self._table.model().hasUnsavedChanges(filename):
        if QMessageBox.question(app.window, "Unsaved changes", text, defaultButton=QMessageBox.StandardButton.No) != QMessageBox.StandardButton.Yes:
          return
        elif forceSave:
          self._table.model().saveFile(filename)
      return fn(*args, **kwargs)
    return inner

  def _newConfiguration(self):
    number = 1
    while os.path.exists(os.path.join(self._tree.model().rootPath(), 'Configuration %d.csv' % number)):
      number += 1
    path = os.path.join(self._tree.model().rootPath(), 'Configuration %d.csv' % number)
    pd.DataFrame(columns=_VideosModel._COLUMN_TITLES).to_csv(path, index=False)
    index = self._tree.model().index(path)
    self._tree.selectionModel().setCurrentIndex(index, QItemSelectionModel.SelectionFlag.ClearAndSelect)
    self._tree.edit(index)

  def _removeConfiguration(self):
    app = QApplication.instance()
    if QMessageBox.question(app.window, "Delete configuration", "Are you sure you want to delete the configuration? This action removes the file from disk and cannot be undone.",
                            defaultButton=QMessageBox.StandardButton.No) != QMessageBox.StandardButton.Yes:
      return
    pathToRemove = self._tree.model().filePath(self._tree.selectionModel().currentIndex())
    self._tree.model().remove(self._tree.selectionModel().currentIndex())
    if pathToRemove == self._tree.model().filePath(self._tree.selectionModel().currentIndex()):  # last valid file removed
      self._mainWidget.hide()

  def _fileSelected(self, filename):
    self._mainWidget.show()
    self._table.setModel(_VideosModel(filename))
    self._table.horizontalHeader().resizeSections(QHeaderView.ResizeMode.Stretch)
    self._updateParallelTracking()

  def _runTracking(self):
    app = QApplication.instance()
    videos, configs = self._table.model().getData()
    errors = []
    for video, config in zip(videos, configs):
      if not config:
        errors.append('Config is not specified for video %s.' % video)
      elif not os.path.exists(config):
        errors.append('Config %s does not exist.' % config)
      if not os.path.exists(video):
        errors.append('Video %s does not exist.' % video)
    if errors:
      error = QMessageBox(app.window)
      error.setIcon(QMessageBox.Icon.Critical)
      error.setWindowTitle("Specification contains some error")
      error.setText("Cannot run tracking becase the specified video and config combinations contain some errors:")
      error.setDetailedText("\n".join(errors))
      textEdit = error.findChild(QTextEdit)
      textEdit.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
      layout = error.layout()
      layout.addItem(QSpacerItem(600, 0), layout.rowCount(), 0, 1, layout.columnCount())
      error.exec()
      return
    if self._ZZkwargs.get('sbatchMode', False):
      videos = [video.replace('\\', '/').replace(self._originalLineEdit.text(), self._replaceLineEdit.text()) for video in videos]
    elif self._processesSpinBox.isVisible():
      self._ZZkwargs['processes'] = self._processesSpinBox.value()
    defineWellsVideos = []
    headEmbeddedVideos = []
    for video, config in zip(videos, configs):
      if self._ZZkwargs.get('findMultipleROIs', False) or self._ZZkwargs.get('headEmbedded', False):
        break
      with open(config) as f:
        cfg = json.load(f)
      if (cfg.get("multipleROIsDefinedDuringExecution", False) or cfg.get("groupOfMultipleSameSizeAndShapeEquallySpacedWells", False)) and \
          not os.path.exists(os.path.join(app.ZZoutputLocation, os.path.splitext(os.path.basename(video))[0], 'intermediaryWellPositionReloadNoMatterWhat.txt')):
        defineWellsVideos.append((video, config))
      if cfg.get("headEmbeded", False) and (not os.path.exists('%s.csv' % video) or not os.path.exists('%sHP.csv' % video)):
        headEmbeddedVideos.append((video, config))
    if defineWellsVideos:
      text = 'Some of the videos do not have the regions defined. Would you like to define them before running tracking?'
      sameCoordinatesCheckbox = QCheckBox("Use the same coordinates for all videos")
      msgbox = QMessageBox(QMessageBox.Icon.Question, "Missing required coordinates", text, parent=app.window,
                           buttons=QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
      msgbox.setDefaultButton(QMessageBox.StandardButton.Yes)
      msgbox.setCheckBox(sameCoordinatesCheckbox)
      if msgbox.exec() == QMessageBox.StandardButton.Yes:
        ZZkwargs = self._ZZkwargs.copy()
        ZZkwargs.update({'findMultipleROIs': True, 'askCoordinatesForAll': not sameCoordinatesCheckbox.isChecked(), 'processes': 1})
        launchZebraZoom(*zip(*defineWellsVideos), **ZZkwargs)
    if headEmbeddedVideos:
      text = 'Some of the head-embedded videos do not have the required head and tail coordinates defined. Would you like to define them before running tracking?'
      msgbox = QMessageBox(QMessageBox.Icon.Question, "Missing required coordinates", text, parent=app.window,
                           buttons=QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
      msgbox.setDefaultButton(QMessageBox.StandardButton.Yes)
      if msgbox.exec() == QMessageBox.StandardButton.Yes:
        ZZkwargs = self._ZZkwargs.copy()
        ZZkwargs.update({'headEmbedded': True, 'processes': 1})
        launchZebraZoom(*zip(*headEmbeddedVideos), **ZZkwargs)
    app.show_frame("Patience")
    app.window.centralWidget().layout().currentWidget().setArgs((videos, configs), self._ZZkwargs)


def _showVideoSelectionPage(ZZkwargs):
  app = QApplication.instance()
  layout = app.window.centralWidget().layout()
  page = _VideoSelectionPage(ZZkwargs)
  layout.addWidget(page)
  layout.setCurrentWidget(page)
  def cleanup():
    layout.removeWidget(page)
    layout.currentChanged.disconnect(cleanup)
  layout.currentChanged.connect(cleanup)


def chooseFolderToAnalyze(self, justExtractParams, noValidationVideo, sbatchMode):
  ZZkwargs = {'justExtractParams': justExtractParams, 'noValidationVideo': noValidationVideo, 'sbatchMode': sbatchMode}
  _showVideoSelectionPage(ZZkwargs)


def chooseFolderForTailExtremityHE(self):
  ZZkwargs = {'headEmbedded': True}
  _showVideoSelectionPage(ZZkwargs)


def chooseFolderForMultipleROIs(self, askCoordinatesForAll):
  ZZkwargs = {'findMultipleROIs': True, 'askCoordinatesForAll': askCoordinatesForAll}
  _showVideoSelectionPage(ZZkwargs)


def chooseConfigFile(ZZargs, ZZkwargs):
  app = QApplication.instance()
  configFileName, _ = QFileDialog.getOpenFileName(app.window, 'Select file', paths.getConfigurationFolder(), "JSON (*.json)")
  if not configFileName:
    return
  ZZargs += ([configFileName],)
  if globalVariables["mac"] or globalVariables["lin"]:
    app.show_frame("Patience")
    app.window.centralWidget().layout().currentWidget().setArgs(ZZargs, ZZkwargs)
  else:
    launchZebraZoom(*ZZargs, **ZZkwargs)


def _runTracking(args, justExtractParams, noValidationVideo, ZZoutputLocation):
  videoPath, config = args
  path        = os.path.dirname(videoPath)
  nameWithExt = os.path.basename(videoPath)
  name        = os.path.splitext(nameWithExt)[0]
  videoExt    = os.path.splitext(nameWithExt)[1][1:]

  tabParams = ["mainZZ", path, name, videoExt, config, "freqAlgoPosFollow", 100, "outputFolder", ZZoutputLocation]
  if justExtractParams:
    tabParams.extend(["reloadWellPositions", 1, "reloadBackground", 1, "debugPauseBetweenTrackAndParamExtract", "justExtractParamFromPreviousTrackData"])
  if noValidationVideo:
    tabParams.extend(["createValidationVideo", 0])
  try:
    mainZZ(path, name, videoExt, config, tabParams)
  except ValueError:
    print("moving on to the next video for ROIs identification")
  except NameError:
    return


@util.showInProgressPage('Tracking')
def launchZebraZoom(videos, configs, headEmbedded=False, sbatchMode=False, justExtractParams=False, noValidationVideo=False, findMultipleROIs=False,
                    askCoordinatesForAll=True, firstFrame=None, lastFrame=None, backgroundExtractionForceUseAllVideoFrames=None, processes=1):
  app = QApplication.instance()

  if sbatchMode:
    commandsFile = open(os.path.join(paths.getRootDataFolder(), "commands.txt"), "w", newline='\n')
    nbVideosToLaunch = 0

  if len(videos) > 1:
    if not askCoordinatesForAll:
      videosGenerator = iter(videos)
      videos = [next(videosGenerator)]
  else:
    videoPath = videos[0]
    if (os.path.exists(videoPath + 'HP.csv') or os.path.exists(videoPath + '.csv')) and \
        QMessageBox.question(app.window, "Previously stored coordinates found", "Do you want to use the previously stored coordinates?",
                             defaultButton=QMessageBox.StandardButton.Yes) != QMessageBox.StandardButton.Yes:
      if os.path.exists(videoPath + 'HP.csv'):
        os.remove(videoPath + 'HP.csv')
      if os.path.exists(videoPath + '.csv'):
        os.remove(videoPath + '.csv')

  print("allVideos:", videos)

  if processes > 1 and len(videos) > 1 and not sbatchMode:
    with Pool(min(processes, len(videos))) as pool:
      pool.map(partial(_runTracking, justExtractParams=justExtractParams, noValidationVideo=noValidationVideo, ZZoutputLocation=app.ZZoutputLocation), zip(videos, configs))
  else:
    for videoPath, config in zip(videos, configs):

      path        = os.path.dirname(videoPath)
      nameWithExt = os.path.basename(videoPath)
      name        = os.path.splitext(nameWithExt)[0]
      videoExt    = os.path.splitext(nameWithExt)[1][1:]

      if not headEmbedded:
        if len(videos) == 1:
          tabParams = ["mainZZ", path, name, videoExt, config, "freqAlgoPosFollow", 100, "popUpAlgoFollow", 1, "outputFolder", app.ZZoutputLocation]
        else:
          tabParams = ["mainZZ", path, name, videoExt, config, "freqAlgoPosFollow", 100, "outputFolder", app.ZZoutputLocation]
        if backgroundExtractionForceUseAllVideoFrames is not None:
          tabParams.extend(["backgroundExtractionForceUseAllVideoFrames", int(backgroundExtractionForceUseAllVideoFrames)])
        if firstFrame is not None:
          tabParams.extend(["firstFrame", firstFrame])
        if lastFrame is not None:
          tabParams.extend(["lastFrame", lastFrame])
        if justExtractParams:
          tabParams = tabParams + ["reloadWellPositions", 1, "reloadBackground", 1, "debugPauseBetweenTrackAndParamExtract", "justExtractParamFromPreviousTrackData"]
        if noValidationVideo:
            tabParams = tabParams + ["createValidationVideo", 0]
        if findMultipleROIs:
          tabParams = tabParams + ["exitAfterWellsDetection", 1, "saveWellPositionsToBeReloadedNoMatterWhat", 1]
        try:
          if sbatchMode:
            commandsFile.write('python -m zebrazoom ' + ' '.join(tabParams[1:4]) + ' configFiles/%s\n' % os.path.basename(config))
            nbVideosToLaunch = nbVideosToLaunch + 1
          else:
            mainZZ(path, name, videoExt, config, tabParams)
        except ValueError:
          print("moving on to the next video for ROIs identification")
        except NameError:
          app.show_frame("Error")
          return
      else:
        tabParams = ["outputFolder", app.ZZoutputLocation]
        if backgroundExtractionForceUseAllVideoFrames is not None:
          tabParams.extend(["backgroundExtractionForceUseAllVideoFrames", int(backgroundExtractionForceUseAllVideoFrames)])
        if firstFrame is not None:
          tabParams.extend(["firstFrame", firstFrame])
        if lastFrame is not None:
          tabParams.extend(["lastFrame", lastFrame])
        getTailExtremityFirstFrame(path, name, videoExt, config, tabParams)

  if findMultipleROIs and not askCoordinatesForAll:
    coordinatesFile = os.path.join(app.ZZoutputLocation, os.path.splitext(os.path.basename(videos[0]))[0], 'intermediaryWellPositionReloadNoMatterWhat.txt')
    configUsedFile = os.path.join(app.ZZoutputLocation, os.path.splitext(os.path.basename(videos[0]))[0], 'intermediaryWellPositionReloadNoMatterWhat.txt')
    rotationFile = os.path.join(app.ZZoutputLocation, os.path.splitext(os.path.basename(videos[0]))[0], 'rotationAngle.txt')
    for video in videosGenerator:
      folderPath = os.path.join(app.ZZoutputLocation, os.path.splitext(os.path.basename(video))[0])
      if not os.path.exists(folderPath):
        os.makedirs(folderPath)
      shutil.copy2(coordinatesFile, os.path.join(folderPath, 'intermediaryWellPositionReloadNoMatterWhat.txt'))
      shutil.copy2(configUsedFile, os.path.join(folderPath, 'configUsed.json'))
      if os.path.exists(rotationFile):
        shutil.copy2(rotationFile, os.path.join(folderPath, 'rotationAngle.txt'))

  if sbatchMode:

    commandsFile.close()

    with open(configs[0]) as f:
      jsonFile = json.load(f)
    nbWells = jsonFile["nbWells"]
    if nbWells > 24:
      nbWells = 24

    launchFile = open(os.path.join(paths.getRootDataFolder(), "launchZZ.sh"), "w", newline='\n')
    linesToWrite = ['#!/bin/sh',
                    '#SBATCH --ntasks=1',
                    '#SBATCH --cpus-per-task='+str(nbWells),
                    '#SBATCH --array=1-'+str(nbVideosToLaunch),
                    '#SBATCH --mem=16G',
                    '#SBATCH --time=23:00:00',
                    '#SBATCH --partition=normal',
                    '#SBATCH --job-name="ZebraZoom-protocole"',
                    '',
                    'module load python/3.8',
                    'source activate zebrazoom',
                    '',
                    'date',
                    '',
                    'export CMD_FILE_PATH=./commands.txt',
                    '',
                    'export CMD=$(sed -n ${SLURM_ARRAY_TASK_ID}p ${CMD_FILE_PATH})',
                    '',
                    'echo $CMD',
                    'eval $CMD',
                    '',
                    'date']
    linesToWrite = [line + '\n' for line in linesToWrite]
    launchFile.writelines(linesToWrite)
    launchFile.close()

    configsFolder = os.path.join(paths.getRootDataFolder(), 'configFiles')
    if os.path.exists(configsFolder):
      shutil.rmtree(configsFolder)
    os.makedirs(configsFolder)
    for config in configs:
      shutil.copy2(config, configsFolder)

    app.show_frame("ZZoutroSbatch")

  else:

    app.show_frame("ZZoutro")


def openConfigurationFileFolder(self, homeDirectory):
  dir_path = os.path.join(homeDirectory,'configuration')
  if sys.platform == "win32":
    os.startfile(dir_path)
  else:
    opener ="open" if sys.platform == "darwin" else "xdg-open"
    subprocess.call([opener, dir_path])


def openZZOutputFolder(self, homeDirectory):
  if len(self.ZZoutputLocation):
    dir_path = self.ZZoutputLocation
  else:
    dir_path = os.path.join(homeDirectory,'ZZoutput')
  if sys.platform == "win32":
    os.startfile(dir_path)
  else:
    opener ="open" if sys.platform == "darwin" else "xdg-open"
    subprocess.call([opener, dir_path])
