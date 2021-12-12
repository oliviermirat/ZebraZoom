from pathlib import Path
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
from zebrazoom.code.vars import getGlobalVariables
import json
import os
import subprocess
import sys
globalVariables = getGlobalVariables()

from zebrazoom.dataAnalysis.datasetcreation.createDataFrame import createDataFrame
from zebrazoom.dataAnalysis.dataanalysis.populationComparaison import populationComparaison
from zebrazoom.dataAnalysis.dataanalysis.applyClustering import applyClustering

def openExperimentOrganizationExcelFolder(self, homeDirectory):
  dir_path = os.path.join(homeDirectory,'dataAnalysis/experimentOrganizationExcel/')
  if sys.platform == "win32":
    os.startfile(dir_path)
  else:
    opener ="open" if sys.platform == "darwin" else "xdg-open"
    subprocess.call([opener, dir_path])
    

def openAnalysisFolder(self, homeDirectory, specificDirectory):
  dir_path = os.path.join(os.path.join(homeDirectory,'dataAnalysis'), specificDirectory)
  if sys.platform == "win32":
    os.startfile(dir_path)
  else:
    opener ="open" if sys.platform == "darwin" else "xdg-open"
    subprocess.call([opener, dir_path])


def chooseExperimentOrganizationExcel(self, controller):
  
  cur_dir_path = os.path.dirname(os.path.realpath(__file__))
  cur_dir_path = Path(cur_dir_path)
  cur_dir_path = cur_dir_path.parent.parent
  
  if globalVariables["mac"]:
    experimentOrganizationExcel = filedialog.askopenfilename(initialdir = os.path.join(cur_dir_path, 'dataAnalysis/experimentOrganizationExcel/'), title = "Select the excel file describing your experiments")
  else:
    experimentOrganizationExcel = filedialog.askopenfilename(initialdir = os.path.join(cur_dir_path, 'dataAnalysis/experimentOrganizationExcel/'), title = "Select the excel file describing your experiments",filetypes = (("video","*.*"),("all files","*.*")))
  
  array = os.path.split(experimentOrganizationExcel)
  
  self.experimentOrganizationExcel = array[len(array)-1]
  self.experimentOrganizationExcelFileAndFolder = ''.join(array[0:len(array)-1])
  
  controller.show_frame("ChooseDataAnalysisMethod")


def populationComparison(self, controller, TailTrackingParameters=0, saveInMatlabFormat=0, saveRawData=0, minNbBendForBoutDetect=3, discard=0, keep=1, frameStepForDistanceCalculation=4):

  if discard == 0 and keep == 0:
    keep = 1
  
  if len(minNbBendForBoutDetect) == 0:
    minNbBendForBoutDetect = 3
  
  cur_dir_path = os.path.dirname(os.path.realpath(__file__))
  cur_dir_path = Path(cur_dir_path)
  cur_dir_path = cur_dir_path.parent.parent

  if len(controller.ZZoutputLocation) == 0:
    ZZoutputLocation = os.path.join(cur_dir_path, 'ZZoutput')
  else:
    ZZoutputLocation = controller.ZZoutputLocation

  # Creating the dataframe

  dataframeOptions = {
    'pathToExcelFile'                   : self.experimentOrganizationExcelFileAndFolder, #os.path.join(cur_dir_path, os.path.join('dataAnalysis', 'experimentOrganizationExcel/')),
    'fileExtension'                     : '.' + self.experimentOrganizationExcel.split(".")[1],
    'resFolder'                         : os.path.join(cur_dir_path, os.path.join('dataAnalysis', 'data')),
    'nameOfFile'                        : self.experimentOrganizationExcel.split(".")[0],
    'smoothingFactorDynaParam'          : 0,   # 0.001
    'nbFramesTakenIntoAccount'          : 28,
    'numberOfBendsIncludedForMaxDetect' : -1,
    'minNbBendForBoutDetect'            : int(minNbBendForBoutDetect),
    'keepSpeedDistDurWhenLowNbBends'    : int(keep),
    'defaultZZoutputFolderPath'         : ZZoutputLocation,
    'computeTailAngleParamForCluster'   : False,
    'computeMassCenterParamForCluster'  : False,
    'tailAngleKinematicParameterCalculation'    : TailTrackingParameters,
    'saveRawDataInAllBoutsSuperStructure'       : saveInMatlabFormat,
    'saveAllBoutsSuperStructuresInMatlabFormat' : saveRawData,
    'frameStepForDistanceCalculation'           : frameStepForDistanceCalculation
  }

  [conditions, genotypes, nbFramesTakenIntoAccount, globParam] = createDataFrame(dataframeOptions)

  # Plotting for the different conditions
  nameOfFile = dataframeOptions['nameOfFile']
  resFolder  = dataframeOptions['resFolder']
  
  # Mixing up all the bouts
  populationComparaison(nameOfFile, resFolder, globParam, conditions, genotypes, os.path.join(cur_dir_path, os.path.join('dataAnalysis', 'resultsKinematic')), 0, True)
  
  populationComparaison(nameOfFile, resFolder, globParam, conditions, genotypes, os.path.join(cur_dir_path, os.path.join('dataAnalysis', 'resultsKinematic')), 0, False)
  
  # First median per well for each kinematic parameter
  populationComparaison(nameOfFile, resFolder, globParam, conditions, genotypes, os.path.join(cur_dir_path, os.path.join('dataAnalysis', 'resultsKinematic')), 1, True)
  
  populationComparaison(nameOfFile, resFolder, globParam, conditions, genotypes, os.path.join(cur_dir_path, os.path.join('dataAnalysis', 'resultsKinematic')), 1, False)
  
  controller.show_frame("AnalysisOutputFolderPopulation")


def boutClustering(self, controller, nbClustersToFind, FreelySwimming, HeadEmbeded, minNbBendForBoutDetect=3, nbVideosToSave=0, modelUsedForClustering=0):
  
  if modelUsedForClustering == 0:
    modelUsedForClustering = 'KMeans'
  else:
    modelUsedForClustering = 'GaussianMixture'
  
  if len(minNbBendForBoutDetect) == 0:
    minNbBendForBoutDetect = 3
  else:
    minNbBendForBoutDetect = int(minNbBendForBoutDetect)
  
  if len(nbVideosToSave) == 0:
    nbVideosToSave = 0
  else:
    nbVideosToSave = int(nbVideosToSave)
  
  videoSaveFirstTenBouts = True if nbVideosToSave else False
  
  cur_dir_path = os.path.dirname(os.path.realpath(__file__))
  cur_dir_path = Path(cur_dir_path)
  cur_dir_path = cur_dir_path.parent.parent

  if len(controller.ZZoutputLocation) == 0:
    ZZoutputLocation = os.path.join(cur_dir_path, 'ZZoutput')
  else:
    ZZoutputLocation = controller.ZZoutputLocation

  # Creating the dataframe on which the clustering will be applied
  dataframeOptions = {
    'pathToExcelFile'                   : self.experimentOrganizationExcelFileAndFolder, # os.path.join(cur_dir_path, os.path.join('dataAnalysis', 'experimentOrganizationExcel')),
    'fileExtension'                     : '.' + self.experimentOrganizationExcel.split(".")[1],
    'resFolder'                         : os.path.join(cur_dir_path, os.path.join('dataAnalysis', 'data')),
    'nameOfFile'                        : self.experimentOrganizationExcel.split(".")[0],
    'smoothingFactorDynaParam'          : 0,   # 0.001
    'nbFramesTakenIntoAccount'          : -1, #28,
    'numberOfBendsIncludedForMaxDetect' : -1,
    'minNbBendForBoutDetect'            : minNbBendForBoutDetect,
    'defaultZZoutputFolderPath'         : ZZoutputLocation,
    'tailAngleKinematicParameterCalculation' : 1,
    'getTailAngleSignMultNormalized'    : 1,
    'computeTailAngleParamForCluster'   : True,
    'computeMassCenterParamForCluster'  : False
  }
  if int(FreelySwimming):
    dataframeOptions['computeMassCenterParamForCluster'] = True
    
  [conditions, genotypes, nbFramesTakenIntoAccount, globParam] = createDataFrame(dataframeOptions)
  # Applying the clustering on this dataframe
  clusteringOptions = {
    'analyzeAllWellsAtTheSameTime' : 0, # put this to 1 for head-embedded videos, and to 0 for multi-well videos
    'pathToVideos' : ZZoutputLocation,
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
    'videoSaveFirstTenBouts' : videoSaveFirstTenBouts,
    'globalParametersCalculations' : True,
    'nbVideosToSave' : nbVideosToSave,
    'resFolder' : os.path.join(os.path.join(cur_dir_path, 'dataAnalysis'),'data/'),
    'nameOfFile' : self.experimentOrganizationExcel.split(".")[0],
    'modelUsedForClustering' : modelUsedForClustering
  }
  if int(FreelySwimming):
    clusteringOptions['useAnglesSpeedHeading'] = True
  if int(HeadEmbeded):
    clusteringOptions['useAngles'] = True
  # Applies the clustering
  [allBouts, classifier] = applyClustering(clusteringOptions, 0, os.path.join(os.path.join(cur_dir_path, 'dataAnalysis'),'resultsClustering/'), self.ZZoutputLocation)
  # Saves the classifier
  controller.show_frame("AnalysisOutputFolderClustering")

