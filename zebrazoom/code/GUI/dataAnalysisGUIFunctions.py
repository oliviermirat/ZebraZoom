import numpy as np
import json
import cv2
import math
from zebrazoom.code.vars import getGlobalVariables
import json
import os
import subprocess
import sys
import pandas as pd
globalVariables = getGlobalVariables()

from PyQt5.QtWidgets import QFileDialog

import zebrazoom.code.paths as paths
from zebrazoom.dataAnalysis.datasetcreation.createDataFrame import createDataFrame
from zebrazoom.dataAnalysis.dataanalysis.applyClustering import applyClustering

from zebrazoom.dataAnalysis.datasetcreation.generatePklDataFileForVideo import generatePklDataFileForVideo


def openAnalysisFolder(self, homeDirectory, specificDirectory):
  dir_path = os.path.join(os.path.join(homeDirectory,'dataAnalysis'), specificDirectory)
  if sys.platform == "win32":
    os.startfile(dir_path)
  else:
    opener ="open" if sys.platform == "darwin" else "xdg-open"
    subprocess.call([opener, dir_path])


def boutClustering(self, controller, nbClustersToFind, FreelySwimming, HeadEmbeded, minNbBendForBoutDetect=3, nbVideosToSave=0, modelUsedForClustering=0, removeOutliers=False, frameStepForDistanceCalculation='4', removeBoutsContainingNanValuesInParametersUsedForClustering=True, forcePandasRecreation=0):

  if len(frameStepForDistanceCalculation) == 0:
    frameStepForDistanceCalculation = '4'
  
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


  if len(controller.ZZoutputLocation) == 0:
    ZZoutputLocation = paths.getDefaultZZoutputFolder()
  else:
    ZZoutputLocation = controller.ZZoutputLocation

  # Creating the dataframe on which the clustering will be applied
  dataframeOptions = {
    'pathToExcelFile'                   : self.experimentOrganizationExcelFileAndFolder, # os.path.join(cur_dir_path, os.path.join('dataAnalysis', 'experimentOrganizationExcel')),
    'fileExtension'                     : '.' + self.experimentOrganizationExcel.split(".")[1],
    'resFolder'                         : os.path.join(paths.getDataAnalysisFolder(), 'data'),
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
    
  generatePklDataFileForVideo(os.path.join(self.experimentOrganizationExcelFileAndFolder, self.experimentOrganizationExcel), ZZoutputLocation, frameStepForDistanceCalculation, forcePandasRecreation)
    
  [conditions, genotypes, nbFramesTakenIntoAccount, globParam] = createDataFrame(dataframeOptions, "", forcePandasRecreation, [])
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
    'resFolder' : os.path.join(paths.getDataAnalysisFolder(), 'data/'),
    'nameOfFile' : self.experimentOrganizationExcel.split(".")[0],
    'modelUsedForClustering' : modelUsedForClustering,
    'removeOutliers'         : removeOutliers,
    'removeBoutsContainingNanValuesInParametersUsedForClustering' : removeBoutsContainingNanValuesInParametersUsedForClustering
  }
  if int(FreelySwimming):
    clusteringOptions['useAnglesSpeedHeading'] = True
    # clusteringOptions['useAngleAnd3GlobalParameters'] = True
    # clusteringOptions['useFreqAmpAsym'] = True
  if int(HeadEmbeded):
    clusteringOptions['useAngles'] = True
  # Applies the clustering
  [allBouts, classifier] = applyClustering(clusteringOptions, 0, os.path.join(paths.getDataAnalysisFolder(), 'resultsClustering/'), self.ZZoutputLocation)
  # Saves the classifier
  controller.show_frame("AnalysisOutputFolderClustering")

