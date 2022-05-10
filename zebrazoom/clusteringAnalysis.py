import zebrazoom.code.paths as paths
from zebrazoom.dataAnalysis.datasetcreation.createDataFrame import createDataFrame
from zebrazoom.dataAnalysis.dataanalysis.applyClustering import applyClustering
from zebrazoom.dataAnalysis.datasetcreation.generatePklDataFileForVideo import generatePklDataFileForVideo

import os

def clusteringAnalysis(sys):

  pathToExcelFile                 = sys.argv[3]
  
  freelySwimming   = int(sys.argv[4]) if len(sys.argv) > 4 else 1
  nbClustersToFind = int(sys.argv[5]) if len(sys.argv) > 5 else 3
  minNbBendForBoutDetect = int(sys.argv[6]) if len(sys.argv) > 6 else 3
  modelUsedForClustering = sys.argv[7] if len(sys.argv) > 7 else 'KMeans'
  removeOutliers         = int(sys.argv[8]) if len(sys.argv) > 8 else 0
  frameStepForDistanceCalculation = int(sys.argv[9]) if len(sys.argv) > 9 else 4
  removeBoutsContainingNanValuesInParametersUsedForClustering = int(sys.argv[10]) if len(sys.argv) > 10 else 1
  forcePandasRecreation = int(sys.argv[11]) if len(sys.argv) > 11 else 0

  nameWithExt = os.path.split(pathToExcelFile)[1]
  
  # Creating the dataframe on which the clustering will be applied
  dataframeOptions = {
    'pathToExcelFile'                   : os.path.split(pathToExcelFile)[0],
    'fileExtension'                     : os.path.splitext(nameWithExt)[1],
    'resFolder'                         : os.path.join(paths.getDataAnalysisFolder(), 'data'),
    'nameOfFile'                        : os.path.splitext(nameWithExt)[0],
    'smoothingFactorDynaParam'          : 0,   # 0.001
    'nbFramesTakenIntoAccount'          : -1, #28,
    'numberOfBendsIncludedForMaxDetect' : -1,
    'minNbBendForBoutDetect'            : minNbBendForBoutDetect, # THIS NEEDS TO BE CHANGED IF FPS IS LOW (default: 3)
    'defaultZZoutputFolderPath'         : paths.getDefaultZZoutputFolder(),
    'tailAngleKinematicParameterCalculation' : 1,
    'getTailAngleSignMultNormalized'    : 1,
    'computeTailAngleParamForCluster'   : True,
    'computeMassCenterParamForCluster'  : False
  }
  
  if int(freelySwimming):
    dataframeOptions['computeMassCenterParamForCluster'] = True
  
  generatePklDataFileForVideo(os.path.join(os.path.split(pathToExcelFile)[0], nameWithExt), paths.getDefaultZZoutputFolder(), frameStepForDistanceCalculation, forcePandasRecreation)
  
  [conditions, genotypes, nbFramesTakenIntoAccount, globParam] = createDataFrame(dataframeOptions, "", forcePandasRecreation, [])
  
  # Applying the clustering on this dataframe
  clusteringOptions = {
    'analyzeAllWellsAtTheSameTime' : 0, # put this to 1 for head-embedded videos, and to 0 for multi-well videos
    'pathToVideos' : paths.getDefaultZZoutputFolder(),
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
    'resFolder'  : os.path.join(paths.getDataAnalysisFolder(), 'data/'),
    'nameOfFile' : os.path.splitext(nameWithExt)[0],
    'modelUsedForClustering' : modelUsedForClustering,
    'removeOutliers'  : removeOutliers,
    'removeBoutsContainingNanValuesInParametersUsedForClustering' : removeBoutsContainingNanValuesInParametersUsedForClustering
  }
  if int(freelySwimming):
    clusteringOptions['useAnglesSpeedHeading'] = True
    # clusteringOptions['useAngleAnd3GlobalParameters'] = True
    # clusteringOptions['useFreqAmpAsym'] = True
  else:
    clusteringOptions['useAngles'] = True
  
  # Applies the clustering
  [allBouts, classifier] = applyClustering(clusteringOptions, 0, os.path.join(paths.getDataAnalysisFolder(), 'resultsClustering/'))
  
  print("The data has been saved in the folder:", os.path.join(paths.getDataAnalysisFolder(), 'resultsClustering', dataframeOptions['nameOfFile']))
  print("The raw data has also been saved in:", dataframeOptions['resFolder'])
