import tkinter as tk
from tkinter import font  as tkfont
from tkinter import filedialog
from tkinter import ttk
from tkinter import *
import re
import os
import json
import subprocess
import matplotlib
matplotlib.use("TkAgg")
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import math
import scipy.io as sio
from zebrazoom.code.readValidationVideo import readValidationVideo

from zebrazoom.mainZZ import mainZZ
from zebrazoom.getTailExtremityFirstFrame import getTailExtremityFirstFrame
import zebrazoom.code.popUpAlgoFollow as popUpAlgoFollow

import zebrazoom.code.GUI.configFilePrepareFunctions as configFilePrepareFunctions
import zebrazoom.code.GUI.GUI_InitialFunctions as GUI_InitialFunctions
import zebrazoom.code.GUI.configFileZebrafishFunctions as configFileZebrafishFunctions
import zebrazoom.code.GUI.adjustParameterInsideAlgoFunctions as adjustParameterInsideAlgoFunctions
import zebrazoom.code.GUI.dataAnalysisGUIFunctions as dataAnalysisGUIFunctions
import zebrazoom.code.GUI.troubleshootingFunction as troubleshootingFunction
from zebrazoom.code.GUI.GUI_InitialClasses import FullScreenApp, StartPage, SeveralVideos, VideoToAnalyze, FolderToAnalyze, TailExtremityHE, FolderMultipleROIInitialSelect, ConfigFilePromp, Patience, ZZoutro, ZZoutroSbatch, ResultsVisualization, EnhanceZZOutput, ViewParameters, Error
from zebrazoom.code.GUI.configFilePrepare import ChooseVideoToCreateConfigFileFor, ChooseGeneralExperiment, FreelySwimmingExperiment, WellOrganisation, NbRegionsOfInterest, CircularOrRectangularWells, HomegeneousWellsLayout, NumberOfAnimals, NumberOfAnimals2, NumberOfAnimalsCenterOfMass, IdentifyHeadCenter, IdentifyBodyExtremity, FinishConfig, ChooseCircularWellsLeft, ChooseCircularWellsRight, GoToAdvanceSettings
from zebrazoom.code.GUI.configFileZebrafish import HeadEmbeded
from zebrazoom.code.GUI.adjustParameterInsideAlgo import AdujstParamInsideAlgo, AdujstParamInsideAlgoFreelySwim
from zebrazoom.code.GUI.dataAnalysisGUI import CreateExperimentOrganizationExcel, ChooseExperimentOrganizationExcel, ChooseDataAnalysisMethod, PopulationComparison, BoutClustering, AnalysisOutputFolderPopulation, AnalysisOutputFolderClustering
from zebrazoom.code.GUI.troubleshooting import ChooseVideoToTroubleshootSplitVideo, VideoToTroubleshootSplitVideo


LARGE_FONT= ("Verdana", 12)

def getCurrentResultFolder():
  return currentResultFolder

class SampleApp(tk.Tk):

    def __init__(self, *args, **kwargs):
        tk.Tk.__init__(self, *args, **kwargs)
        self.title("ZebraZoom")
        self.currentResultFolder = "abc"
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
        
        self.numWell = 0
        self.numPoiss = 0
        self.numMouv = 0
        self.visualization = 2
        self.graphScaling = True
        self.justEnteredViewParameter = 0
        self.dataRef = {}
        self.title_font = tkfont.Font(family='Helvetica', size=18, weight="bold", slant="italic")   
        FullScreenApp(self)
        container = tk.Frame(self)
        container.pack(side="top", fill="both", expand=True)
        container.grid_rowconfigure(0, weight=1)
        container.grid_columnconfigure(0, weight=1) 
        self.container = container
        self.frames = {}
        for F in (StartPage, SeveralVideos, VideoToAnalyze, ChooseVideoToCreateConfigFileFor, ChooseGeneralExperiment, FreelySwimmingExperiment, WellOrganisation, NbRegionsOfInterest, CircularOrRectangularWells, HomegeneousWellsLayout, NumberOfAnimals, NumberOfAnimals2, NumberOfAnimalsCenterOfMass, IdentifyHeadCenter, IdentifyBodyExtremity, ChooseCircularWellsLeft, ChooseCircularWellsRight, FinishConfig, FolderToAnalyze, TailExtremityHE, FolderMultipleROIInitialSelect, ConfigFilePromp, Patience, ZZoutro, ZZoutroSbatch, ResultsVisualization, EnhanceZZOutput, ViewParameters, Error, HeadEmbeded, AdujstParamInsideAlgo, AdujstParamInsideAlgoFreelySwim, GoToAdvanceSettings, CreateExperimentOrganizationExcel, ChooseExperimentOrganizationExcel, ChooseDataAnalysisMethod, PopulationComparison, BoutClustering, AnalysisOutputFolderPopulation, AnalysisOutputFolderClustering, ChooseVideoToTroubleshootSplitVideo, VideoToTroubleshootSplitVideo):
            page_name = F.__name__
            frame = F(parent=container, controller=self)
            self.frames[page_name] = frame
            frame.grid(row=0, column=0, sticky="nsew")
        self.show_frame("StartPage")
    
    def askForZZoutputLocation(self):
        
        folderName = ''
        folderName = filedialog.askdirectory(initialdir = os.path.expanduser("~"),title = "Select ZZoutput folder")
        self.ZZoutputLocation = folderName
    
    def show_frame(self, page_name):
        '''Show a frame for the given page name'''
        frame = self.frames[page_name]
        frame.tkraise()
        
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
        self.frames['ResultsVisualization'].destroy()
        frame = ResultsVisualization(parent=self.container,controller=self)
        frame.grid(row=0, column=0, sticky="nsew")
        self.frames['ResultsVisualization'] = frame
        self.show_frame("ResultsVisualization")

    def showValidationVideo(self, numWell, numAnimal, zoom, deb):
        GUI_InitialFunctions.showValidationVideo(self, numWell, numAnimal, zoom, deb)

    def printSomeResults(self, numWell, numPoiss, numMouv, changeVisualization=False, changeScaling=False):
        if changeVisualization:
            self.visualization = int(self.visualization + 1) % 3
        if changeScaling:
            self.graphScaling = not(self.graphScaling)
        self.numWell  = int(numWell)
        self.numPoiss = int(numPoiss)
        self.numMouv  = int(numMouv)
        if self.numWell < 0:
            self.numWell = 0
        if self.numPoiss < 0:
            self.numPoiss = 0
        if self.numMouv < 0:
            self.numMouv = 0
        self.frames['ViewParameters'].destroy()
        frame = ViewParameters(parent=self.container,controller=self)
        frame.grid(row=0, column=0, sticky="nsew")
        self.frames['ViewParameters']=frame
        self.show_frame("ViewParameters")
    
    def showGraphForAllBoutsCombined(self, numWell, numPoiss, dataRef, visualization, graphScaling):
        GUI_InitialFunctions.showGraphForAllBoutsCombined(self, numWell, numPoiss, dataRef, visualization, graphScaling)

    def exploreResultFolder(self, currentResultFolder):
        GUI_InitialFunctions.exploreResultFolder(self, currentResultFolder)
        
    def printNextResults(self, numWell, numPoiss, numMouv, nbWells, nbPoiss, nbMouv):
        GUI_InitialFunctions.printNextResults(self, numWell, numPoiss, numMouv, nbWells, nbPoiss, nbMouv)

    def printPreviousResults(self, numWell, numPoiss, numMouv, nbWells, nbPoiss, nbMouv):
        GUI_InitialFunctions.printPreviousResults(self, numWell, numPoiss, numMouv, nbWells, nbPoiss, nbMouv)

    def flagMove(self, numWell, numPoiss, numMouv):
        GUI_InitialFunctions.flagMove(self, numWell, numPoiss, numMouv)

    def saveSuperStruct(self, numWell, numPoiss, numMouv):
        GUI_InitialFunctions.saveSuperStruct(self, numWell, numPoiss, numMouv)
        
    def openConfigurationFileFolder(self, homeDirectory):
        GUI_InitialFunctions.openConfigurationFileFolder(self, homeDirectory)
        
    def openZZOutputFolder(self, homeDirectory):
        GUI_InitialFunctions.openZZOutputFolder(self, homeDirectory)
        
    # Config File preparation functions
    
    def chooseVideoToCreateConfigFileFor(self, controller):
        configFilePrepareFunctions.chooseVideoToCreateConfigFileFor(self, controller)
    
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

    def headEmbededGUI(self, controller, blackBack, whiteBack, noBoutDetect, boutDetection, optionExtendedDescentSearchOption, 
optionBackgroundExtractionOption):
        configFileZebrafishFunctions.headEmbededGUI(self, controller, blackBack, whiteBack, noBoutDetect, boutDetection, optionExtendedDescentSearchOption, optionBackgroundExtractionOption)

    def detectBouts(self, controller, wellNumber, firstFrameParamAdjust, adjustOnWholeVideo):
      adjustParameterInsideAlgoFunctions.detectBouts(self, controller, wellNumber, firstFrameParamAdjust, adjustOnWholeVideo)
      
    def adjustHeadEmbededTracking(self, controller, wellNumber, firstFrameParamAdjust, adjustOnWholeVideo):
      adjustParameterInsideAlgoFunctions.adjustHeadEmbededTracking(self, controller, wellNumber, firstFrameParamAdjust, adjustOnWholeVideo)
    
    def adjustFreelySwimTracking(self, controller, wellNumber, firstFrameParamAdjust, adjustOnWholeVideo):
      adjustParameterInsideAlgoFunctions.adjustFreelySwimTracking(self, controller, wellNumber, firstFrameParamAdjust, adjustOnWholeVideo)

    def calculateBackground(self, controller, nbImagesForBackgroundCalculation):
      adjustParameterInsideAlgoFunctions.calculateBackground(self, controller, nbImagesForBackgroundCalculation)
      
    def calculateBackgroundFreelySwim(self, controller, nbImagesForBackgroundCalculation, morePreciseFastScreen=False):
      adjustParameterInsideAlgoFunctions.calculateBackgroundFreelySwim(self, controller, nbImagesForBackgroundCalculation, morePreciseFastScreen)
    
    def chooseVideoToCreateConfigFileFor(self, controller, reloadConfigFile):
      configFilePrepareFunctions.chooseVideoToCreateConfigFileFor(self, controller, reloadConfigFile)

    def goToAdvanceSettings(self, controller, yes, no):
      configFilePrepareFunctions.goToAdvanceSettings(self, controller, yes, no)
      
    def openExperimentOrganizationExcelFolder(self, homeDirectory):
      dataAnalysisGUIFunctions.openExperimentOrganizationExcelFolder(self, homeDirectory)
    
    def chooseExperimentOrganizationExcel(self, controller):
      dataAnalysisGUIFunctions.chooseExperimentOrganizationExcel(self, controller)
  
    def populationComparison(self, controller, TailTrackingParameters, saveInMatlabFormat, saveRawData, minNbBendForBoutDetect, discard, keep, frameStepForDistanceCalculation):
      dataAnalysisGUIFunctions.populationComparison(self, controller, TailTrackingParameters, saveInMatlabFormat, saveRawData, minNbBendForBoutDetect, discard, keep, frameStepForDistanceCalculation)
      
    def boutClustering(self, controller, nbClustersToFind, FreelySwimming, HeadEmbeded):
      dataAnalysisGUIFunctions.boutClustering(self, controller, nbClustersToFind, FreelySwimming, HeadEmbeded)
    
    def openAnalysisFolder(self, homeDirectory, specificDirectory):
      dataAnalysisGUIFunctions.openAnalysisFolder(self, homeDirectory, specificDirectory)
    
    def chooseVideoToTroubleshootSplitVideo(self, controller):
      troubleshootingFunction.chooseVideoToTroubleshootSplitVideo(self, controller)
