import zebrazoom.code.paths as paths
from zebrazoom.dataAnalysis.datasetcreation.createDataFramePerFrame import createDataFramePerFrame
from zebrazoom.dataAnalysis.dataanalysis.applyClusteringPerFrame import applyClusteringPerFrame

import os

def clusteringAnalysisPerFrame(sys):

  pathToExcelFile                 = sys.argv[3]
  
  freelySwimming   = int(sys.argv[4]) if len(sys.argv) >= 5 else 1
  nbClustersToFind = int(sys.argv[5]) if len(sys.argv) >= 6 else 3

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
    'minNbBendForBoutDetect'            : 3, # THIS NEEDS TO BE CHANGED IF FPS IS LOW (default: 3)
    'defaultZZoutputFolderPath'         : paths.getDefaultZZoutputFolder(),
    'tailAngleKinematicParameterCalculation' : 1,
    'getTailAngleSignMultNormalized'    : 1,
    'computeTailAngleParamForCluster'   : True,
    'computeMassCenterParamForCluster'  : False
  }
  if int(freelySwimming):
    dataframeOptions['computeMassCenterParamForCluster'] = True
    
  [conditions, genotypes, nbFramesTakenIntoAccount] = createDataFramePerFrame(dataframeOptions)
  
  
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
    'globalParametersCalculations' : False,
    'nbVideosToSave' : 10,
    'resFolder'  : os.path.join(paths.getDataAnalysisFolder(), 'data/'),
    'nameOfFile' : os.path.splitext(nameWithExt)[0]
  }
  if int(freelySwimming):
    clusteringOptions['useFreqAmpAsymSpeedHeadingDisp'] = True
  else:
    clusteringOptions['useFreqAmpAsym'] = True
  
  
  # Applies the clustering
  [allBouts, classifier] = applyClusteringPerFrame(clusteringOptions, 0, os.path.join(paths.getDataAnalysisFolder(), 'resultsClustering/'))
  
  print("The data has been saved in the folder:", os.path.join(paths.getDataAnalysisFolder(), 'resultsClustering', dataframeOptions['nameOfFile']))
  print("The raw data has also been saved in:", dataframeOptions['resFolder'])
