from zebrazoom.dataAnalysis.datasetcreation.createDataFrame import createDataFrame
from zebrazoom.dataAnalysis.dataanalysis.applyClustering import applyClustering

import os
from pathlib import Path

def clusteringAnalysis(sys):

  pathToExcelFile                 = sys.argv[3]
  
  freelySwimming   = int(sys.argv[4]) if len(sys.argv) >= 5 else 1
  nbClustersToFind = int(sys.argv[5]) if len(sys.argv) >= 6 else 3
  minNbBendForBoutDetect = int(sys.argv[6]) if len(sys.argv) >= 7 else 3
  
  cur_dir_path = os.path.dirname(os.path.realpath(__file__))
  cur_dir_path = Path(cur_dir_path)
  cur_dir_path = cur_dir_path

  nameWithExt = os.path.split(pathToExcelFile)[1]
  
  # Creating the dataframe on which the clustering will be applied
  dataframeOptions = {
    'pathToExcelFile'                   : os.path.split(pathToExcelFile)[0],
    'fileExtension'                     : os.path.splitext(nameWithExt)[1],
    'resFolder'                         : os.path.join(cur_dir_path, os.path.join('dataAnalysis', 'data')),
    'nameOfFile'                        : os.path.splitext(nameWithExt)[0],
    'smoothingFactorDynaParam'          : 0,   # 0.001
    'nbFramesTakenIntoAccount'          : -1, #28,
    'numberOfBendsIncludedForMaxDetect' : -1,
    'minNbBendForBoutDetect'            : minNbBendForBoutDetect, # THIS NEEDS TO BE CHANGED IF FPS IS LOW (default: 3)
    'defaultZZoutputFolderPath'         : os.path.join(cur_dir_path, 'ZZoutput'),
    'tailAngleKinematicParameterCalculation' : 1,
    'getTailAngleSignMultNormalized'    : 1,
    'computeTailAngleParamForCluster'   : True,
    'computeMassCenterParamForCluster'  : False
  }
  if int(freelySwimming):
    dataframeOptions['computeMassCenterParamForCluster'] = True
    
  [conditions, genotypes, nbFramesTakenIntoAccount, globParam] = createDataFrame(dataframeOptions)
  # Applying the clustering on this dataframe
  clusteringOptions = {
    'analyzeAllWellsAtTheSameTime' : 0, # put this to 1 for head-embedded videos, and to 0 for multi-well videos
    'pathToVideos' : os.path.join(cur_dir_path, 'ZZoutput'),
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
    'resFolder'  : os.path.join(os.path.join(cur_dir_path, 'dataAnalysis'),'data/'),
    'nameOfFile' : os.path.splitext(nameWithExt)[0]
  }
  if int(freelySwimming):
    clusteringOptions['useAnglesSpeedHeading'] = True
  else:
    clusteringOptions['useAngles'] = True
  
  # Applies the clustering
  [allBouts, classifier] = applyClustering(clusteringOptions, 0, os.path.join(os.path.join(cur_dir_path, 'dataAnalysis'),'resultsClustering/'))
  
  print("The data has been saved in the folder:", os.path.join(os.path.join(cur_dir_path, os.path.join('dataAnalysis', 'resultsClustering')), dataframeOptions['nameOfFile']))
  print("The raw data has also been saved in:", dataframeOptions['resFolder'])
