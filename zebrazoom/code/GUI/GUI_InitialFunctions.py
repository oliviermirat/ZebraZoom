import cv2
import re
import os
import json
import shutil
import sys
import subprocess
from matplotlib.figure import Figure
import math
import scipy.io as sio
from zebrazoom.code.vars import getGlobalVariables
globalVariables = getGlobalVariables()

from zebrazoom.mainZZ import mainZZ
from zebrazoom.getTailExtremityFirstFrame import getTailExtremityFirstFrame
import zebrazoom.code.paths as paths
import zebrazoom.code.util as util

from PyQt5.QtCore import Qt, QAbstractTableModel, QModelIndex
from PyQt5.QtWidgets import QApplication, QCheckBox, QFileDialog, QHBoxLayout, QHeaderView, QLabel, QMessageBox, QPushButton, QTableView, QVBoxLayout, QWidget


LARGE_FONT= ("Verdana", 12)

def chooseVideoToAnalyze(self, justExtractParams, noValidationVideo, chooseFrames, testMode):
    videoName, _ = QFileDialog.getOpenFileName(self.window, 'Select file', os.path.expanduser("~"))
    if not videoName:
      return
    ZZargs = ([videoName],)
    ZZkwargs = {'justExtractParams': justExtractParams, 'noValidationVideo': noValidationVideo, 'testMode': testMode}

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


class _VideosModel(QAbstractTableModel):
  _COLUMN_TITLES = ["Video", "Config"]
  _DEFAULT_ZZOUTPUT = paths.getDefaultZZoutputFolder()

  def __init__(self):
    super().__init__()
    self._videos = []
    self._configs = []

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


class _VideoSelectionPage(QWidget):
  def __init__(self, ZZkwargs):
    super().__init__()
    self._ZZkwargs = ZZkwargs

    app = QApplication.instance()

    layout = QVBoxLayout()
    layout.addWidget(util.apply_style(QLabel("Select videos and corresponding config files"), font=app.title_font), alignment=Qt.AlignmentFlag.AlignCenter)

    self._table = QTableView()
    self._table.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
    self._table.setModel(_VideosModel())

    tableLayout = QVBoxLayout()
    tableButtonsLayout = QHBoxLayout()
    self._addVideosBtn = QPushButton("Add video(s)")
    self._addVideosBtn.clicked.connect(lambda: self._table.model().addVideos(QFileDialog.getOpenFileNames(app.window, 'Select one or more videos', os.path.expanduser("~"))[0]))
    tableButtonsLayout.addWidget(self._addVideosBtn, alignment=Qt.AlignmentFlag.AlignLeft)
    removeVideosBtn = QPushButton("Choose config for selected videos")
    removeVideosBtn.clicked.connect(lambda: self._table.model().setConfigs(sorted(set(map(lambda idx: idx.row(), self._table.selectionModel().selectedIndexes()))),
                                                                           QFileDialog.getOpenFileName(app.window, 'Select config file', paths.getConfigurationFolder(), "JSON (*.json)")[0]))
    tableButtonsLayout.addWidget(removeVideosBtn, alignment=Qt.AlignmentFlag.AlignLeft)
    removeVideosBtn = QPushButton("Remove selected videos")
    removeVideosBtn.clicked.connect(lambda: self._table.model().removeSelectedRows(sorted(set(map(lambda idx: idx.row(), self._table.selectionModel().selectedIndexes())))))
    tableButtonsLayout.addWidget(removeVideosBtn, alignment=Qt.AlignmentFlag.AlignLeft)
    self._runExperimentBtn = util.apply_style(QPushButton("Run tracking"), background_color=util.LIGHT_YELLOW)
    self._runExperimentBtn.clicked.connect(self._runTracking)
    tableButtonsLayout.addWidget(self._runExperimentBtn, alignment=Qt.AlignmentFlag.AlignLeft)
    tableButtonsLayout.addStretch()
    tableLayout.addLayout(tableButtonsLayout)
    tableLayout.addWidget(self._table, stretch=1)
    layout.addLayout(tableLayout)

    buttonsLayout = QHBoxLayout()
    buttonsLayout.addStretch()
    startPageBtn = util.apply_style(QPushButton("Go to the start page"), background_color=util.LIGHT_CYAN)
    startPageBtn.clicked.connect(lambda: app.show_frame("StartPage"))
    buttonsLayout.addWidget(startPageBtn, alignment=Qt.AlignmentFlag.AlignCenter)
    buttonsLayout.addStretch()
    layout.addLayout(buttonsLayout)

    self.setLayout(layout)

  def _runTracking(self):
    app = QApplication.instance()
    app.show_frame("Patience")
    app.window.centralWidget().layout().currentWidget().setArgs(self._table.model().getData(), self._ZZkwargs)


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


def launchZebraZoom(videos, configs, headEmbedded=False, sbatchMode=False, justExtractParams=False, noValidationVideo=False, testMode=False,
                    findMultipleROIs=False, askCoordinatesForAll=True, firstFrame=None, lastFrame=None, backgroundExtractionForceUseAllVideoFrames=None):
  app = QApplication.instance()

  if testMode:
    with open(configs[0]) as f:
      app.configFile = json.load(f)
    videoToCreateConfigFileFor = videos[0]
    app.testConfig(addToHistory=False)
    return

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

  for idx, (videoPath, config) in enumerate(zip(videos, configs)):

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
          commandsFile.write('python -m zebrazoom ' + ' '.join(tabParams[1:4]).replace('\\', '/').replace('//lexport/iss02.', '/network/lustre/iss02/') + ' configFiles/%s\n' % os.path.basename(config))
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
    for video in videosGenerator:
      folderPath = os.path.join(app.ZZoutputLocation, os.path.splitext(os.path.basename(video))[0])
      if not os.path.exists(folderPath):
        os.makedirs(folderPath)
      shutil.copy2(coordinatesFile, os.path.join(folderPath, 'intermediaryWellPositionReloadNoMatterWhat.txt'))
      shutil.copy2(coordinatesFile, os.path.join(folderPath, 'configUsed.json'))

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
