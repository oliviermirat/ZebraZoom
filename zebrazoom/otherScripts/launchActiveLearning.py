from zebrazoom.dataAnalysis.dataanalysis.activeLearning import activeLearning

def launchActiveLearning():

  modelUsed     = 'KNeighborsClassifier' # 'SVC'
  nbConditions  = 2
  nbCluster     = 4
  outputFolderResult = 'zebrazoom/dataAnalysis/resultsClustering/parkinsonFreelySwimForClustering_OutliersRemoved_BASSstyleParam2/activeLearning/'
  N_QUERIES     = 40
  manualClassicationPath = 'zebrazoom/dataAnalysis/resultsClustering/parkinsonFreelySwimForClustering_OutliersRemoved_BASSstyleParam2/manualClassifications.txt'

  activeLearning(modelUsed, nbConditions, nbCluster, outputFolderResult, N_QUERIES, manualClassicationPath)
