import sys
sys.path.insert(1, './dataanalysis/')
sys.path.insert(1, './datasetcreation/')
import pickle
from createDataFrame import createDataFrame
from applyClustering import applyClustering


# Creating the dataframe on which the clustering will be applied

dataframeOptions = {
  'pathToExcelFile'                   : './experimentOrganizationExcel/',
  'fileExtension'                     : '.xls',
  'resFolder'                         : './data/',
  'nameOfFile'                        : 'example',
  'smoothingFactorDynaParam'          : 0,   # 0.001
  'nbFramesTakenIntoAccount'          : -1, #28,
  'numberOfBendsIncludedForMaxDetect' : -1,
  'minNbBendForBoutDetect'            : 3,
  'defaultZZoutputFolderPath'         : '../ZZoutput/',
  'computeTailAngleParamForCluster'   : True,
  'computeMassCenterParamForCluster'  : True
}

[conditions, genotypes, nbFramesTakenIntoAccount] = createDataFrame(dataframeOptions)


# Applying the clustering on this dataframe

clusteringOptions = {
  'analyzeAllWellsAtTheSameTime' : 0, # put this to 1 for head-embedded videos, and to 0 for multi-well videos
  'pathToVideos' : '../ZZoutput/',
  'nbCluster' : 3,
  #'nbPcaComponents' : 30,
  'nbFramesTakenIntoAccount' : nbFramesTakenIntoAccount,
  'scaleGraphs' : True,
  'showFigures' : False,
  'useFreqAmpAsym' : False,
  'useAngles' : False,
  'useAnglesSpeedHeadingDisp' : False,
  'useAnglesSpeedHeading' : True,
  'useAnglesSpeed' : False,
  'useAnglesHeading' : False,
  'useAnglesHeadingDisp' : False,
  'useFreqAmpAsymSpeedHeadingDisp' : False,
  'videoSaveFirstTenBouts' : False,
  'globalParametersCalculations' : True,
  'nbVideosToSave' : 10,
  'resFolder' : './data/',
  'nameOfFile' : 'example'
}


# Applies the clustering for the first time
[allBouts, classifier] = applyClustering(clusteringOptions, 0, './resultsClustering/')


# Saves the classifier
outfile = open('classifiers/classifier_' + clusteringOptions['nameOfFile'] + '.txt','wb')
pickle.dump([classifier, nbFramesTakenIntoAccount],outfile)
outfile.close()
