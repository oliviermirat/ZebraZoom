import os

from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QWidget, QFileDialog, QApplication, QMainWindow, QStackedLayout

import zebrazoom.code.GUI.configFilePrepareFunctions as configFilePrepareFunctions
import zebrazoom.code.GUI.GUI_InitialFunctions as GUI_InitialFunctions
import zebrazoom.code.GUI.configFileZebrafishFunctions as configFileZebrafishFunctions
import zebrazoom.code.GUI.adjustParameterInsideAlgoFunctions as adjustParameterInsideAlgoFunctions
import zebrazoom.code.GUI.dataAnalysisGUIFunctions as dataAnalysisGUIFunctions
import zebrazoom.code.GUI.troubleshootingFunction as troubleshootingFunction
from zebrazoom.code.GUI.GUI_InitialClasses import StartPage, VideoToAnalyze, ConfigFilePromp, Patience, ZZoutro, ZZoutroSbatch, SeveralVideos, FolderToAnalyze, TailExtremityHE, FolderMultipleROIInitialSelect, EnhanceZZOutput, ResultsVisualization, ViewParameters, Error
from zebrazoom.code.GUI.configFilePrepare import ChooseVideoToCreateConfigFileFor, OptimizeConfigFile, ChooseGeneralExperiment, WellOrganisation, FreelySwimmingExperiment, NbRegionsOfInterest, HomegeneousWellsLayout, CircularOrRectangularWells, NumberOfAnimals, NumberOfAnimals2, NumberOfAnimalsCenterOfMass, IdentifyHeadCenter, IdentifyBodyExtremity, FinishConfig, ChooseCircularWellsLeft, ChooseCircularWellsRight, GoToAdvanceSettings
from zebrazoom.code.GUI.configFileZebrafish import HeadEmbeded
from zebrazoom.code.GUI.adjustParameterInsideAlgo import AdujstParamInsideAlgo, AdujstParamInsideAlgoFreelySwim, AdujstParamInsideAlgoFreelySwimAutomaticParameters, AdujstBoutDetectionOnly
from zebrazoom.code.GUI.dataAnalysisGUI import CreateExperimentOrganizationExcel, ChooseExperimentOrganizationExcel, ChooseDataAnalysisMethod, PopulationComparison, BoutClustering, AnalysisOutputFolderPopulation, AnalysisOutputFolderClustering
from zebrazoom.code.GUI.troubleshooting import ChooseVideoToTroubleshootSplitVideo, VideoToTroubleshootSplitVideo


LARGE_FONT= ("Verdana", 12)


def getCurrentResultFolder():
  return currentResultFolder


class ZebraZoomApp(QApplication):
    def __init__(self, args):
        super().__init__(args)
        self.homeDirectory = os.path.dirname(os.path.realpath(__file__))

        self.configFile = {}
        self.videoToCreateConfigFileFor = ''
        self.wellLeftBorderX = 0
        self.wellLeftBorderY = 0
        self.headCenterX = 0
        self.headCenterY = 0
        self.organism = ''

        curZZoutputPath = os.path.dirname(os.path.realpath(__file__))
        curZZoutputPath = os.path.join(curZZoutputPath, 'ZZoutput')
        self.ZZoutputLocation = curZZoutputPath

        self.title_font = QFont('Helvetica', 18, QFont.Weight.Bold, True)

        self.window = QMainWindow()
        layout = QStackedLayout()
        self.frames = {}
        for idx, F in enumerate((StartPage, VideoToAnalyze, ConfigFilePromp, Patience, ZZoutro, ZZoutroSbatch, SeveralVideos, FolderToAnalyze, EnhanceZZOutput, TailExtremityHE, FolderMultipleROIInitialSelect, ResultsVisualization, ViewParameters, Error, ChooseVideoToCreateConfigFileFor, OptimizeConfigFile, ChooseGeneralExperiment, WellOrganisation, FreelySwimmingExperiment, NbRegionsOfInterest, HomegeneousWellsLayout, CircularOrRectangularWells, NumberOfAnimals, NumberOfAnimals2, NumberOfAnimalsCenterOfMass, IdentifyHeadCenter, IdentifyBodyExtremity, FinishConfig, ChooseCircularWellsLeft, ChooseCircularWellsRight, GoToAdvanceSettings, HeadEmbeded, AdujstParamInsideAlgo, AdujstParamInsideAlgoFreelySwim, AdujstParamInsideAlgoFreelySwimAutomaticParameters, AdujstBoutDetectionOnly, CreateExperimentOrganizationExcel, ChooseExperimentOrganizationExcel, ChooseDataAnalysisMethod, PopulationComparison, BoutClustering, AnalysisOutputFolderPopulation, AnalysisOutputFolderClustering, ChooseVideoToTroubleshootSplitVideo, VideoToTroubleshootSplitVideo)):
            self.frames[F.__name__] = idx
            layout.addWidget(F(self))
        central_widget = QWidget(self.window)
        central_widget.setLayout(layout)
        self.window.setWindowTitle('ZebraZoom')
        self.window.setCentralWidget(central_widget)
        self.window.showMaximized()

    def askForZZoutputLocation(self):
        self.ZZoutputLocation = QFileDialog.getExistingDirectory(self.window, "Select ZZoutput folder", os.path.expanduser("~"))

    def show_frame(self, page_name):
        '''Show a frame for the given page name'''
        self.window.centralWidget().layout().setCurrentIndex(self.frames[page_name])

    def chooseVideoToAnalyze(self, justExtractParams, noValidationVideo, debugMode):
        GUI_InitialFunctions.chooseVideoToAnalyze(self, justExtractParams, noValidationVideo, debugMode)

    def chooseFolderToAnalyze(self, justExtractParams, noValidationVideo, sbatchMode):
        GUI_InitialFunctions.chooseFolderToAnalyze(self, justExtractParams, noValidationVideo, sbatchMode)

    def chooseFolderForTailExtremityHE(self):
        GUI_InitialFunctions.chooseFolderForTailExtremityHE(self)

    def chooseFolderForMultipleROIs(self):
        GUI_InitialFunctions.chooseFolderForMultipleROIs(self)

    def chooseConfigFile(self):
        GUI_InitialFunctions.chooseConfigFile(self)

    def launchZebraZoom(self):
        GUI_InitialFunctions.launchZebraZoom(self)

    def showResultsVisualization(self):
        self.show_frame("ResultsVisualization")
        self.window.centralWidget().layout().currentWidget().refresh()

    def showViewParameters(self, folder):
        self.show_frame("ViewParameters")
        self.window.centralWidget().layout().currentWidget().setFolder(folder)

    def openConfigurationFileFolder(self, homeDirectory):
        GUI_InitialFunctions.openConfigurationFileFolder(self, homeDirectory)

    def openZZOutputFolder(self, homeDirectory):
        GUI_InitialFunctions.openZZOutputFolder(self, homeDirectory)

    # Config File preparation functions

    def chooseVideoToCreateConfigFileFor(self, controller, reloadConfigFile, freelySwimAutomaticParameters=False, boutDetectionsOnly=False):
        configFilePrepareFunctions.chooseVideoToCreateConfigFileFor(self, controller, reloadConfigFile, freelySwimAutomaticParameters, boutDetectionsOnly)

    def chooseGeneralExperimentFirstStep(self, controller, freeZebra, headEmbZebra, drosophilia, rodent, other, fastScreen):
        configFilePrepareFunctions.chooseGeneralExperimentFirstStep(self, controller, freeZebra, headEmbZebra, drosophilia, rodent, other, fastScreen)

    def chooseGeneralExperiment(self, controller, freeZebra, headEmbZebra, drosophilia, rodent, other, freeZebra2):
        configFilePrepareFunctions.chooseGeneralExperiment(self, controller, freeZebra, headEmbZebra, drosophilia, rodent, other, freeZebra2)

    def wellOrganisation(self, controller, circular, rectangular, roi, other, multipleROIs, groupSameSizeAndShapeEquallySpacedWells):
        configFilePrepareFunctions.wellOrganisation(self, controller, circular, rectangular, roi, other, multipleROIs, groupSameSizeAndShapeEquallySpacedWells)

    def regionsOfInterest(self, controller, nbwells):
        configFilePrepareFunctions.regionsOfInterest(self, controller, nbwells)

    def homegeneousWellsLayout(self, controller, nbwells, nbRowsOfWells, nbWellsPerRows):
        configFilePrepareFunctions.homegeneousWellsLayout(self, controller, nbwells, nbRowsOfWells, nbWellsPerRows)

    def morePreciseFastScreen(self, controller, nbwells, nbRowsOfWells, nbWellsPerRows):
        configFilePrepareFunctions.morePreciseFastScreen(self, controller, nbwells, nbRowsOfWells, nbWellsPerRows)

    def circularOrRectangularWells(self, controller, nbwells, nbRowsOfWells, nbWellsPerRows):
        configFilePrepareFunctions.circularOrRectangularWells(self, controller, nbwells, nbRowsOfWells, nbWellsPerRows)

    def finishConfig(self, controller, configFileNameToSave):
        configFilePrepareFunctions.finishConfig(self, controller, configFileNameToSave)

    def chooseCircularWellsLeft(self, controller):
        configFilePrepareFunctions.chooseCircularWellsLeft(self, controller)

    def chooseCircularWellsRight(self, controller):
        configFilePrepareFunctions.chooseCircularWellsRight(self, controller)

    def numberOfAnimals(self, controller, nbanimals, yes, noo, forceBlobMethodForHeadTracking, yesBouts, nooBouts, recommendedMethod, alternativeMethod, yesBends, nooBends, adjustBackgroundExtractionBasedOnNumberOfBlackPixels):
      configFilePrepareFunctions.numberOfAnimals(self, controller, nbanimals, yes, noo, forceBlobMethodForHeadTracking, yesBouts, nooBouts, recommendedMethod, alternativeMethod, yesBends, nooBends, adjustBackgroundExtractionBasedOnNumberOfBlackPixels)

    def chooseHeadCenter(self, controller):
        configFilePrepareFunctions.chooseHeadCenter(self, controller)

    def chooseBodyExtremity(self, controller):
        configFilePrepareFunctions.chooseBodyExtremity(self, controller)

    def chooseBeginningAndEndOfVideo(self, controller):
        configFilePrepareFunctions.chooseBeginningAndEndOfVideo(self, controller)

    def headEmbededGUI(self, controller, blackBack, whiteBack, noBoutDetect, boutDetection, optionExtendedDescentSearchOption, optionBackgroundExtractionOption):
        configFileZebrafishFunctions.headEmbededGUI(self, controller, blackBack, whiteBack, noBoutDetect, boutDetection, optionExtendedDescentSearchOption, optionBackgroundExtractionOption)

    def detectBouts(self, controller, wellNumber, firstFrameParamAdjust, adjustOnWholeVideo):
      adjustParameterInsideAlgoFunctions.detectBouts(self, controller, wellNumber, firstFrameParamAdjust, adjustOnWholeVideo)

    def adjustHeadEmbededTracking(self, controller, wellNumber, firstFrameParamAdjust, adjustOnWholeVideo):
      adjustParameterInsideAlgoFunctions.adjustHeadEmbededTracking(self, controller, wellNumber, firstFrameParamAdjust, adjustOnWholeVideo)

    def adjustFreelySwimTracking(self, controller, wellNumber, firstFrameParamAdjust, adjustOnWholeVideo):
      adjustParameterInsideAlgoFunctions.adjustFreelySwimTracking(self, controller, wellNumber, firstFrameParamAdjust, adjustOnWholeVideo)

    def adjustFreelySwimTrackingAutomaticParameters(self, controller, wellNumber, firstFrameParamAdjust, adjustOnWholeVideo):
      adjustParameterInsideAlgoFunctions.adjustFreelySwimTrackingAutomaticParameters(self, controller, wellNumber, firstFrameParamAdjust, adjustOnWholeVideo)

    def calculateBackground(self, controller, nbImagesForBackgroundCalculation):
      adjustParameterInsideAlgoFunctions.calculateBackground(self, controller, nbImagesForBackgroundCalculation)

    def calculateBackgroundFreelySwim(self, controller, nbImagesForBackgroundCalculation, morePreciseFastScreen=False, automaticParameters=False, boutDetectionsOnly=False):
      adjustParameterInsideAlgoFunctions.calculateBackgroundFreelySwim(self, controller, nbImagesForBackgroundCalculation, morePreciseFastScreen, automaticParameters, boutDetectionsOnly)

    def updateFillGapFrameNb(self, fillGapFrameNb):
      adjustParameterInsideAlgoFunctions.updateFillGapFrameNb(self, fillGapFrameNb)

    def goToAdvanceSettings(self, controller, yes, no):
      configFilePrepareFunctions.goToAdvanceSettings(self, controller, yes, no)

    def openExperimentOrganizationExcelFolder(self, homeDirectory):
      dataAnalysisGUIFunctions.openExperimentOrganizationExcelFolder(self, homeDirectory)

    def chooseExperimentOrganizationExcel(self, controller):
      dataAnalysisGUIFunctions.chooseExperimentOrganizationExcel(self, controller)

    def populationComparison(self, controller, TailTrackingParameters, saveInMatlabFormat, saveRawData, minNbBendForBoutDetect, discard, keep, frameStepForDistanceCalculation):
      dataAnalysisGUIFunctions.populationComparison(self, controller, TailTrackingParameters, saveInMatlabFormat, saveRawData, minNbBendForBoutDetect, discard, keep, frameStepForDistanceCalculation)
      
    def boutClustering(self, controller, nbClustersToFind, FreelySwimming, HeadEmbeded, minNbBendForBoutDetect=3, nbVideosToSave=0, modelUsedForClustering='', removeOutliers=False, frameStepForDistanceCalculation='4'):
      dataAnalysisGUIFunctions.boutClustering(self, controller, nbClustersToFind, FreelySwimming, HeadEmbeded, minNbBendForBoutDetect, nbVideosToSave, modelUsedForClustering, removeOutliers, frameStepForDistanceCalculation)

    def openAnalysisFolder(self, homeDirectory, specificDirectory):
      dataAnalysisGUIFunctions.openAnalysisFolder(self, homeDirectory, specificDirectory)

    def chooseVideoToTroubleshootSplitVideo(self, controller):
      troubleshootingFunction.chooseVideoToTroubleshootSplitVideo(self, controller)
