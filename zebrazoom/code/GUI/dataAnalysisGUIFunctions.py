import numpy as np
import tkinter as tk
from tkinter import font  as tkfont
from tkinter import filedialog
from tkinter import ttk
from tkinter import *
import json
import cv2
import math
import cvui
from vars import getGlobalVariables
import json
import os
import subprocess
globalVariables = getGlobalVariables()

import sys
sys.path.insert(1, './dataAnalysis/datasetcreation/')
sys.path.insert(1, './dataAnalysis/')
sys.path.insert(1, './dataAnalysis/dataanalysis/')
from createDataFrame import createDataFrame
from populationComparaison import populationComparaison
from applyClustering import applyClustering

def openExperimentOrganizationExcelFolder(self, homeDirectory):
  dir_path = os.path.join(homeDirectory,'dataAnalysis/experimentOrganizationExcel/')
  if sys.platform == "win32":
    os.startfile(dir_path)
  else:
    opener ="open" if sys.platform == "darwin" else "xdg-open"
    subprocess.call([opener, dir_path])
    

def openPopulationAnalysisFolder(self, homeDirectory):
  dir_path = os.path.join(homeDirectory,'dataAnalysis/resultsKinematic/')
  if sys.platform == "win32":
    os.startfile(dir_path)
  else:
    opener ="open" if sys.platform == "darwin" else "xdg-open"
    subprocess.call([opener, dir_path])
    

def openClusteringAnalysisFolder(self, homeDirectory):
  dir_path = os.path.join(homeDirectory,'dataAnalysis/resultsClustering/')
  if sys.platform == "win32":
    os.startfile(dir_path)
  else:
    opener ="open" if sys.platform == "darwin" else "xdg-open"
    subprocess.call([opener, dir_path])


def chooseExperimentOrganizationExcel(self, controller):
  if globalVariables["mac"]:
    experimentOrganizationExcel = filedialog.askopenfilename(initialdir = "./dataAnalysis/experimentOrganizationExcel/", title = "Select the excel file describing your experiments")
  else:
    experimentOrganizationExcel = filedialog.askopenfilename(initialdir = "./dataAnalysis/experimentOrganizationExcel/", title = "Select the excel file describing your experiments",filetypes = (("video","*.*"),("all files","*.*")))
  
  array = os.path.split(experimentOrganizationExcel)
  
  self.experimentOrganizationExcel = array[len(array)-1]
  
  controller.show_frame("ChooseDataAnalysisMethod")


def populationComparison(self, controller, BoutDuration, TotalDistance, Speed, NumberOfOscillations, meanTBF, maxAmplitude):

  # Creating the dataframe

  dataframeOptions = {
    'pathToExcelFile'                   : './dataAnalysis/experimentOrganizationExcel/',
    'fileExtension'                     : '.' + self.experimentOrganizationExcel.split(".")[1],
    'resFolder'                         : './dataAnalysis/data/',
    'nameOfFile'                        : self.experimentOrganizationExcel.split(".")[0],
    'smoothingFactorDynaParam'          : 0,   # 0.001
    'nbFramesTakenIntoAccount'          : 28,
    'numberOfBendsIncludedForMaxDetect' : -1,
    'minNbBendForBoutDetect'            : 3,
    'defaultZZoutputFolderPath'         : './ZZoutput/',
    'computeTailAngleParamForCluster'   : False,
    'computeMassCenterParamForCluster'  : False
  }

  [conditions, genotypes, nbFramesTakenIntoAccount] = createDataFrame(dataframeOptions)

  # Plotting for the different conditions
  nameOfFile = dataframeOptions['nameOfFile']
  resFolder  = dataframeOptions['resFolder']
  
  globParam = []
  if int(BoutDuration):
    globParam.append('BoutDuration')
  if int(TotalDistance):
    globParam.append('TotalDistance')
  if int(Speed):
    globParam.append('Speed')
  if int(NumberOfOscillations):
    globParam.append('NumberOfOscillations')
  if int(meanTBF):
    globParam.append('meanTBF')
  if int(maxAmplitude):
    globParam.append('maxAmplitude')

  populationComparaison(nameOfFile, resFolder, globParam, conditions, genotypes, './dataAnalysis/resultsKinematic/')
  
  controller.show_frame("AnalysisOutputFolderPopulation")


def boutClustering(self, controller, nbClustersToFind, FreelySwimming, HeadEmbeded):

  # Creating the dataframe on which the clustering will be applied
  dataframeOptions = {
    'pathToExcelFile'                   : './dataAnalysis/experimentOrganizationExcel/',
    'fileExtension'                     : '.' + self.experimentOrganizationExcel.split(".")[1],
    'resFolder'                         : './dataAnalysis/data/',
    'nameOfFile'                        : self.experimentOrganizationExcel.split(".")[0],
    'smoothingFactorDynaParam'          : 0,   # 0.001
    'nbFramesTakenIntoAccount'          : -1, #28,
    'numberOfBendsIncludedForMaxDetect' : -1,
    'minNbBendForBoutDetect'            : 3, # THIS NEEDS TO BE CHANGED IF FPS IS LOW (default: 3)
    'defaultZZoutputFolderPath'         : './ZZoutput/',
    'computeTailAngleParamForCluster'   : True,
    'computeMassCenterParamForCluster'  : False
  }
  if int(FreelySwimming):
    dataframeOptions['computeMassCenterParamForCluster'] = True
    
  [conditions, genotypes, nbFramesTakenIntoAccount] = createDataFrame(dataframeOptions)
  # Applying the clustering on this dataframe
  clusteringOptions = {
    'analyzeAllWellsAtTheSameTime' : 0, # put this to 1 for head-embedded videos, and to 0 for multi-well videos
    'pathToVideos' : './ZZoutput/',
    'nbCluster' : int(nbClustersToFind),
    #'nbPcaComponents' : 30,
    'nbFramesTakenIntoAccount' : nbFramesTakenIntoAccount,
    'scaleGraphs' : True,
    'showFigures' : False,
    'useFreqAmpAsym' : False,
    'useAngles' : False,
    'useAnglesSpeedHeadingDisp' : False,
    'useAnglesSpeedHeading' : False,
    'useAnglesSpeed' : False,
    'useAnglesHeading' : False,
    'useAnglesHeadingDisp' : False,
    'useFreqAmpAsymSpeedHeadingDisp' : False,
    'videoSaveFirstTenBouts' : False,
    'globalParametersCalculations' : True,
    'nbVideosToSave' : 10,
    'resFolder' : './dataAnalysis/data/',
    'nameOfFile' : self.experimentOrganizationExcel.split(".")[0]
  }
  if int(FreelySwimming):
    clusteringOptions['useAnglesSpeedHeading'] = True
  if int(HeadEmbeded):
    clusteringOptions['useAngles'] = True
  # Applies the clustering
  [allBouts, classifier] = applyClustering(clusteringOptions, 0, './dataAnalysis/resultsClustering/')
  # Saves the classifier
  controller.show_frame("AnalysisOutputFolderClustering")

