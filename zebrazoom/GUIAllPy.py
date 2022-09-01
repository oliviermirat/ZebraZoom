import contextlib
import os
import sys
import traceback
import tempfile
from datetime import datetime

import json

from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QFont, QIcon
from PyQt5.QtWidgets import QWidget, QButtonGroup, QCheckBox, QDialog, QFileDialog, QHBoxLayout, QApplication, QLabel, QMainWindow, QRadioButton, QStackedLayout, QVBoxLayout, QMessageBox, QTextEdit, QSpacerItem, QPushButton
QApplication.setAttribute(Qt.AA_EnableHighDpiScaling, True)
QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps, True)
QApplication.setHighDpiScaleFactorRoundingPolicy(Qt.HighDpiScaleFactorRoundingPolicy.PassThrough)
PYQT6 = False

import zebrazoom.videoFormatConversion.zzVideoReading as zzVideoReading
import zebrazoom.code.paths as paths
import zebrazoom.code.util as util
import zebrazoom.code.GUI.configFilePrepareFunctions as configFilePrepareFunctions
import zebrazoom.code.GUI.GUI_InitialFunctions as GUI_InitialFunctions
import zebrazoom.code.GUI.configFileZebrafishFunctions as configFileZebrafishFunctions
import zebrazoom.code.GUI.adjustParameterInsideAlgoFunctions as adjustParameterInsideAlgoFunctions
import zebrazoom.code.GUI.dataAnalysisGUIFunctions as dataAnalysisGUIFunctions
import zebrazoom.code.GUI.troubleshootingFunction as troubleshootingFunction
from zebrazoom.mainZZ import mainZZ
from zebrazoom.code.GUI.GUI_InitialClasses import StartPage, VideoToAnalyze, ConfigFilePromp, Patience, ZZoutro, ZZoutroSbatch, SeveralVideos, FolderToAnalyze, TailExtremityHE, FolderMultipleROIInitialSelect, EnhanceZZOutput, ViewParameters, Error
from zebrazoom.code.GUI.configFilePrepare import ChooseVideoToCreateConfigFileFor, OptimizeConfigFile, ChooseGeneralExperiment, ChooseCenterOfMassTracking, WellOrganisation, FreelySwimmingExperiment, NbRegionsOfInterest, HomegeneousWellsLayout, CircularOrRectangularWells, NumberOfAnimals, NumberOfAnimals2, NumberOfAnimalsCenterOfMass, IdentifyHeadCenter, IdentifyBodyExtremity, FinishConfig, ChooseCircularWellsLeft, ChooseCircularWellsRight, GoToAdvanceSettings
from zebrazoom.code.GUI.configFileZebrafish import HeadEmbeded
from zebrazoom.code.GUI.dataAnalysisGUI import CreateExperimentOrganizationExcel, ChooseDataAnalysisMethod, PopulationComparison, BoutClustering, AnalysisOutputFolderClustering
from zebrazoom.code.GUI.troubleshooting import ChooseVideoToTroubleshootSplitVideo, VideoToTroubleshootSplitVideo


LARGE_FONT= ("Verdana", 12)


def getCurrentResultFolder():
  return currentResultFolder


def excepthook(excType, excValue, traceback_):
  app = QApplication.instance()
  errorMessage = QMessageBox(app.window)
  errorMessage.setIcon(QMessageBox.Icon.Critical)
  errorMessage.setWindowTitle("Error")
  formattedTraceback = traceback.format_exception(excType, excValue, traceback_)
  errorMessage.setText("An error has ocurred: %s" % formattedTraceback[-1])
  informativeText = 'Please report the issue on <a href="https://github.com/oliviermirat/ZebraZoom/issues">Github</a>.'
  if app.configFile and app.savedConfigFile != {k: v for k, v in app.configFile.items() if k != "firstFrame" and k != "lastFrame"}:
    configDir = paths.getConfigurationFolder()
    videoName = os.path.splitext(os.path.basename(app.videoToCreateConfigFileFor))[0]
    configFilename = os.path.join(configDir, '%s_%s_unfinished.json' % (videoName, datetime.now().strftime("%Y_%m_%d-%H_%M_%S")))
    with open(configFilename, 'w') as f:
      json.dump({k: v for k, v in app.configFile.items() if k != "firstFrame" and k != "lastFrame"}, f)
    informativeText += '\nConfig file that was being modified when the error happened was saved to %s.' % configFilename
  errorMessage.setInformativeText(informativeText)
  errorMessage.setDetailedText("    %s" % "    ".join(formattedTraceback))
  errorMessage.setStandardButtons(QMessageBox.StandardButton.Ok | QMessageBox.StandardButton.Cancel)
  errorMessage.setDefaultButton(QMessageBox.StandardButton.Cancel)
  errorMessage.button(QMessageBox.StandardButton.Ok).setText("Continue")
  errorMessage.button(QMessageBox.StandardButton.Cancel).setText("Exit")
  textEdit = errorMessage.findChild(QTextEdit)
  textEdit.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
  textEdit.setMarkdown(textEdit.toPlainText())
  layout = errorMessage.layout()
  layout.addItem(QSpacerItem(600, 0), layout.rowCount(), 0, 1, layout.columnCount())
  try:
    if errorMessage.exec() != QMessageBox.StandardButton.Ok:
      sys.exit(1)
  finally:
    sys.__excepthook__(excType, excValue, traceback_)


sys.excepthook = excepthook


class PlainApplication(QApplication):
    def __init__(self, args):
        super().__init__(args)
        if not PYQT6 and sys.platform.startswith('win'):  # qt5 uses deprecated windows API to determine the system font, this works around that issuue
            self.setFont(QApplication.font("QMessageBox"))


class ZebraZoomApp(PlainApplication):
    def __init__(self, args):
        super().__init__(args)

        self.homeDirectory = paths.getRootDataFolder()

        self.savedConfigFile = None
        self.configFile = {}
        self.videoToCreateConfigFileFor = ''
        self.wellLeftBorderX = 0
        self.wellLeftBorderY = 0
        self.headCenterX = 0
        self.headCenterY = 0
        self.organism = ''

        self.configFileHistory = []

        self.ZZoutputLocation = paths.getDefaultZZoutputFolder()

        self.title_font = QFont('Helvetica', 18, QFont.Weight.Bold, True)

        self._busyCursor = False

        self._windows = set()
        self.window = QMainWindow()
        self.window.setWindowIcon(QIcon('icon.ico'))
        self.window.closeEvent = self._windowClosed(self.window, self.window.closeEvent)
        layout = QStackedLayout()
        self.frames = {}
        for idx, F in enumerate((StartPage, VideoToAnalyze, ConfigFilePromp, Patience, ZZoutro, ZZoutroSbatch, SeveralVideos, FolderToAnalyze, EnhanceZZOutput, TailExtremityHE, FolderMultipleROIInitialSelect, ViewParameters, Error, ChooseVideoToCreateConfigFileFor, OptimizeConfigFile, ChooseGeneralExperiment, ChooseCenterOfMassTracking, WellOrganisation, FreelySwimmingExperiment, NbRegionsOfInterest, HomegeneousWellsLayout, CircularOrRectangularWells, NumberOfAnimals, NumberOfAnimals2, NumberOfAnimalsCenterOfMass, IdentifyHeadCenter, IdentifyBodyExtremity, FinishConfig, ChooseCircularWellsLeft, ChooseCircularWellsRight, GoToAdvanceSettings, HeadEmbeded, ChooseDataAnalysisMethod, PopulationComparison, BoutClustering, AnalysisOutputFolderClustering, ChooseVideoToTroubleshootSplitVideo, VideoToTroubleshootSplitVideo)):
            self.frames[F.__name__] = idx
            page = F(self)
            if hasattr(page, 'preferredSize'):
                layout.addWidget(self._wrapWidget(page))
            else:
                layout.addWidget(page)
        central_widget = QWidget(self.window)
        central_widget.setLayout(layout)
        self.window.setWindowTitle('ZebraZoom')
        self.window.setCentralWidget(central_widget)
        layout.currentChanged.connect(self._currentPageChanged)
        self.window.showMaximized()

    def askForZZoutputLocation(self):
        selectedFolder = QFileDialog.getExistingDirectory(self.window, "Select ZZoutput folder", os.path.expanduser("~"))
        if selectedFolder:
          self.ZZoutputLocation = selectedFolder

    def _wrapWidget(self, page):
        page.sizeHint = lambda *args, page=page: QSize(*page.preferredSize)
        wrapperWidget = QWidget()
        wrapperLayout = QVBoxLayout()
        wrapperLayout.addWidget(page, alignment=Qt.AlignmentFlag.AlignCenter)
        wrapperWidget.setLayout(wrapperLayout)
        if hasattr(page, 'setArgs'):
          wrapperWidget.setArgs = page.setArgs
        return wrapperWidget

    def _currentPageChanged(self):
        backBtn = self.window.centralWidget().layout().currentWidget().findChild(QPushButton, "back")
        if backBtn is not None and self.configFileHistory:
            try:
                backBtn.clicked.disconnect()
            except TypeError:  # nothing connected
                pass
            backBtn.clicked.connect(self.configFileHistory[-2])

    def show_frame(self, page_name):
        '''Show a frame for the given page name'''
        if page_name == "StartPage":
            if self.configFile and self.savedConfigFile != {k: v for k, v in self.configFile.items() if k != "firstFrame" and k != "lastFrame"}:
                reply = QMessageBox.question(self.window, "Unsaved Changes",
                                             "Are you sure you want to go back to the start page? Changes made to the config will be lost.",
                                             QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                if reply != QMessageBox.StandardButton.Yes:
                    return True
            self.configFile.clear()
            self.savedConfigFile = None
            self.videoToCreateConfigFileFor = ''
            self.wellLeftBorderX = 0
            self.wellLeftBorderY = 0
            self.headCenterX = 0
            self.headCenterY = 0
            self.organism = ''
            del self.configFileHistory[:]
        if page_name == "CreateExperimentOrganizationExcel":
          page = CreateExperimentOrganizationExcel(self)
          layout = self.window.centralWidget().layout()
          layout.addWidget(page)
          layout.setCurrentWidget(page)
          def cleanup():
            layout.removeWidget(page)
            layout.currentChanged.disconnect(cleanup)
          layout.currentChanged.connect(cleanup)
        else:
          self.window.centralWidget().layout().setCurrentIndex(self.frames[page_name])

    def _windowClosed(self, window, fn):
        def inner(*args, **kwargs):
            if window is self.window:
                for win in tuple(self._windows):
                    win.close()
                sys.exit(0)
            else:
                if window in self._windows:
                    self._windows.remove(window)
            return fn(*args, **kwargs)
        return inner

    def registerWindow(self, window):
        self._windows.add(window)
        window.closeEvent = self._windowClosed(window, window.closeEvent)

    @contextlib.contextmanager
    def busyCursor(self):
        self.setOverrideCursor(Qt.CursorShape.BusyCursor)
        self._busyCursor = True
        yield
        self.restoreOverrideCursor()
        self._busyCursor = False

    @contextlib.contextmanager
    def suppressBusyCursor(self):
        if self._busyCursor:
            self.restoreOverrideCursor()
        yield
        if self._busyCursor:
            self.setOverrideCursor(Qt.CursorShape.BusyCursor)

    def chooseVideoToAnalyze(self, justExtractParams, noValidationVideo, chooseFrames):
        GUI_InitialFunctions.chooseVideoToAnalyze(self, justExtractParams, noValidationVideo, chooseFrames)

    def chooseFolderToAnalyze(self, justExtractParams, noValidationVideo, sbatchMode):
        GUI_InitialFunctions.chooseFolderToAnalyze(self, justExtractParams, noValidationVideo, sbatchMode)

    def chooseFolderForTailExtremityHE(self):
        GUI_InitialFunctions.chooseFolderForTailExtremityHE(self)

    def chooseFolderForMultipleROIs(self, askCoordinatesForAll):
        GUI_InitialFunctions.chooseFolderForMultipleROIs(self, askCoordinatesForAll)

    def showViewParameters(self, folder=None):
        self.show_frame("ViewParameters")
        self.window.centralWidget().layout().currentWidget().setFolder(folder)

    def openConfigurationFileFolder(self, homeDirectory):
        GUI_InitialFunctions.openConfigurationFileFolder(self, homeDirectory)

    def optimizeConfigFile(self):
        self.show_frame("OptimizeConfigFile")
        self.window.centralWidget().layout().currentWidget().refresh()

    def openZZOutputFolder(self, homeDirectory):
        GUI_InitialFunctions.openZZOutputFolder(self, homeDirectory)

    # Config File preparation functions

    def chooseVideoToCreateConfigFileFor(self, controller, reloadConfigFile):
        return configFilePrepareFunctions.chooseVideoToCreateConfigFileFor(self, controller, reloadConfigFile)

    def chooseGeneralExperimentFirstStep(self, controller, freeZebra, headEmbZebra, drosophilia, rodent, other, fastScreen):
        configFilePrepareFunctions.chooseGeneralExperimentFirstStep(self, controller, freeZebra, headEmbZebra, drosophilia, rodent, other, fastScreen)

    def chooseGeneralExperiment(self, controller, freeZebra, headEmbZebra, drosophilia, rodent, other, freeZebra2):
        configFilePrepareFunctions.chooseGeneralExperiment(self, controller, freeZebra, headEmbZebra, drosophilia, rodent, other, freeZebra2)

    def wellOrganisation(self, controller, circular, rectangular, roi, other, multipleROIs, groupSameSizeAndShapeEquallySpacedWells):
        configFilePrepareFunctions.wellOrganisation(self, controller, circular, rectangular, roi, other, multipleROIs, groupSameSizeAndShapeEquallySpacedWells)

    def regionsOfInterest(self, controller, nbwells):
        configFilePrepareFunctions.regionsOfInterest(self, controller, nbwells)

    def homegeneousWellsLayout(self, controller, nbRowsOfWells, nbWellsPerRows, detectBouts):
        configFilePrepareFunctions.homegeneousWellsLayout(self, controller, nbRowsOfWells, nbWellsPerRows, detectBouts)

    def morePreciseFastScreen(self, controller, nbRowsOfWells, nbWellsPerRows, detectBouts):
        configFilePrepareFunctions.morePreciseFastScreen(self, controller, nbRowsOfWells, nbWellsPerRows, detectBouts)

    def circularOrRectangularWells(self, controller, nbRowsOfWells, nbWellsPerRows, nbanimals):
        configFilePrepareFunctions.circularOrRectangularWells(self, controller, nbRowsOfWells, nbWellsPerRows, nbanimals)

    def finishConfig(self, testConfig=False):
        suggestedName = '%s_%s' % (os.path.splitext(os.path.basename(self.videoToCreateConfigFileFor))[0], datetime.now().strftime("%Y_%m_%d-%H_%M_%S"))
        configDir = paths.getConfigurationFolder()
        reference, _ = QFileDialog.getSaveFileName(self.window, "Save config", os.path.join(configDir, suggestedName), "JSON (*.json)")
        if not reference:
          return
        # Ideally would like to remove these four lines below, once the problem with wrong 'firstFrame' and 'lastFrame' being saved in the configuration file is solved
        if "lastFrame" in self.configFile:
          # del self.configFile["lastFrame"]
          self.configFile["lastFrameForBackExtract"] = self.configFile["lastFrame"]
        if "firstFrame" in self.configFile:
          # del self.configFile["firstFrame"]
          self.configFile["firstFrameForBackExtract"] = self.configFile["firstFrame"]
        
        with open(reference, 'w') as outfile:
          json.dump(self.configFile, outfile)

        self.savedConfigFile = self.configFile.copy()

        if testConfig:
          self.testConfig()
        else:
          self.show_frame("StartPage")

    def chooseCircularWellsLeft(self, controller):
        configFilePrepareFunctions.chooseCircularWellsLeft(self, controller)

    def chooseCircularWellsRight(self, controller):
        configFilePrepareFunctions.chooseCircularWellsRight(self, controller)

    def chooseHeadCenter(self, controller):
        configFilePrepareFunctions.chooseHeadCenter(self, controller)

    def chooseBodyExtremity(self, controller):
        configFilePrepareFunctions.chooseBodyExtremity(self, controller)

    def headEmbededGUI(self, controller, blackBack, whiteBack, noBoutDetect, boutDetection, optionExtendedDescentSearchOption, optionBackgroundExtractionOption):
        configFileZebrafishFunctions.headEmbededGUI(self, controller, blackBack, whiteBack, noBoutDetect, boutDetection, optionExtendedDescentSearchOption, optionBackgroundExtractionOption)

    def detectBouts(self, controller, wellNumber, firstFrameParamAdjust, adjustOnWholeVideo, reloadWellPositions=True):
      adjustParameterInsideAlgoFunctions.detectBouts(self, controller, wellNumber, firstFrameParamAdjust, adjustOnWholeVideo, reloadWellPositions=reloadWellPositions)

    def adjustHeadEmbededTracking(self, controller, wellNumber, firstFrameParamAdjust, adjustOnWholeVideo):
      adjustParameterInsideAlgoFunctions.adjustHeadEmbededTracking(self, controller, wellNumber, firstFrameParamAdjust, adjustOnWholeVideo)

    def adjustFreelySwimTracking(self, controller, wellNumber, firstFrameParamAdjust, adjustOnWholeVideo):
      adjustParameterInsideAlgoFunctions.adjustFreelySwimTracking(self, controller, wellNumber, firstFrameParamAdjust, adjustOnWholeVideo)

    def adjustFreelySwimTrackingAutomaticParameters(self, controller, wellNumber, firstFrameParamAdjust, adjustOnWholeVideo):
      adjustParameterInsideAlgoFunctions.adjustFreelySwimTrackingAutomaticParameters(self, controller, wellNumber, firstFrameParamAdjust, adjustOnWholeVideo)

    def calculateBackground(self, controller, nbImagesForBackgroundCalculation, useNext=True):
      adjustParameterInsideAlgoFunctions.calculateBackground(self, controller, nbImagesForBackgroundCalculation, useNext)

    def calculateBackgroundFreelySwim(self, controller, nbImagesForBackgroundCalculation, morePreciseFastScreen=False, automaticParameters=False, boutDetectionsOnly=False, useNext=True, nextCb=None, reloadWellPositions=False):
      adjustParameterInsideAlgoFunctions.calculateBackgroundFreelySwim(self, controller, nbImagesForBackgroundCalculation, morePreciseFastScreen, automaticParameters, boutDetectionsOnly, useNext, nextCb, reloadWellPositions=reloadWellPositions)

    def goToAdvanceSettings(self, controller, yes, no):
      configFilePrepareFunctions.goToAdvanceSettings(self, controller, yes, no)
      
    def boutClustering(self, controller, nbClustersToFind, FreelySwimming, HeadEmbeded, minNbBendForBoutDetect=3, nbVideosToSave=0, modelUsedForClustering='', removeOutliers=False, frameStepForDistanceCalculation='4', removeBoutsContainingNanValuesInParametersUsedForClustering=True, forcePandasRecreation=0):
      dataAnalysisGUIFunctions.boutClustering(self, controller, nbClustersToFind, FreelySwimming, HeadEmbeded, minNbBendForBoutDetect, nbVideosToSave, modelUsedForClustering, removeOutliers, frameStepForDistanceCalculation, removeBoutsContainingNanValuesInParametersUsedForClustering, forcePandasRecreation)

    def openAnalysisFolder(self, homeDirectory, specificDirectory):
      dataAnalysisGUIFunctions.openAnalysisFolder(self, homeDirectory, specificDirectory)

    def chooseVideoToTroubleshootSplitVideo(self, controller):
      troubleshootingFunction.chooseVideoToTroubleshootSplitVideo(self, controller)

    def testConfig(self, addToHistory=True):
      videoPath = self.videoToCreateConfigFileFor
      pathToVideo  = os.path.dirname(videoPath)
      videoName, videoExt = os.path.splitext(os.path.basename(videoPath))
      videoExt = videoExt.lstrip('.')

      def callback():
        firstFrame = self.configFile["firstFrame"]
        self.configFile.clear()
        self.configFile.update(configFile)
        lastFrame = min(firstFrame + maximumFramesButtonGroup.checkedId(), int(zzVideoReading.VideoCapture(videoPath).get(7)) - 1)
        tempDir = tempfile.TemporaryDirectory()
        outputLocation = self.ZZoutputLocation
        self.ZZoutputLocation = tempDir.name
        del self.configFileHistory[:]
        with self.busyCursor():
          try:
            tabParams = ["mainZZ", pathToVideo, videoName, videoExt, self.configFile,
                         "firstFrame", firstFrame, "lastFrame", lastFrame, "freqAlgoPosFollow", 100,
                         "popUpAlgoFollow", 1, "outputFolder", self.ZZoutputLocation,
                         "backgroundExtractionForceUseAllVideoFrames", int(backgroundExtractionForceUseAllVideoFramesCheckbox.isChecked())]
            mainZZ(pathToVideo, videoName, videoExt, self.configFile, tabParams)
          except NameError:
            self.show_frame("Error")
            self.ZZoutputLocation = outputLocation
            tempDir.cleanup()
            return
          finally:
            self.configFile.clear()
            self.configFile.update(configFile)
        (self.showViewParameters if not addToHistory else util.addToHistory(self.showViewParameters))(videoName)
        layout = self.window.centralWidget().layout()
        def cleanup():
          self.ZZoutputLocation = outputLocation
          tempDir.cleanup()
          layout.currentChanged.disconnect(cleanup)
        layout.currentChanged.connect(cleanup)
      configFile = self.configFile.copy()

      layout = QVBoxLayout()
      backgroundExtractionForceUseAllVideoFramesCheckbox = QCheckBox("Use all frames to calculate background")
      backgroundExtractionForceUseAllVideoFramesCheckbox.setChecked(True)
      layout.addWidget(backgroundExtractionForceUseAllVideoFramesCheckbox, alignment=Qt.AlignmentFlag.AlignCenter)
      maximumFramesLayout = QHBoxLayout()
      maximumFramesLayout.addStretch()
      maximumFramesLayout.addWidget(QLabel("Maximum number of frames used for tracking:"))
      maximumFramesButtonGroup = QButtonGroup()
      for value in (50, 100, 200, 300, 500):
        btn = QRadioButton(str(value))
        maximumFramesLayout.addWidget(btn)
        maximumFramesButtonGroup.addButton(btn, id=value)
      maximumFramesButtonGroup.button(500).setChecked(True)
      maximumFramesLayout.addStretch()
      layout.addLayout(maximumFramesLayout)
      cb = util.chooseBeginningPage if not addToHistory else util.addToHistory(util.chooseBeginningPage)
      cb(self, videoPath, "We will test the tracking on the video you provided, with the configuration file you just created. We will do this test only on the selected number of frames (maximum) and the tracking will start at the frame you select below (so please choose a section of the video where the animal is moving).",
         "Ok, I want the tracking to start at this frame!", callback, additionalLayout=layout, titleStyle={'color': 'red', 'font': QFont('Helvetica', 14, QFont.Weight.Bold, True)})
