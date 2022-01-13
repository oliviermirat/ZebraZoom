from zebrazoom.dataAnalysis.dataanalysis.reapplyClustering import reapplyClustering

def launchReapplyClustering():

  # outputFolderResult = 'zebrazoom/dataAnalysis/resultsClustering/parkinsonFreelySwimForClustering_OutliersRemoved_BASSstyleParam2/activeLearning/'
  outputFolderResult = 'zebrazoom/dataAnalysis/resultsClustering/copied/savedRawData/'
  nbConditions  = 2
  nbCluster     = 4

  if False:
    
    for modelUsed in ['KMeans', 'GaussianMixture', 'BIRCH', 'DBSCAN', 'MeanShift', 'SpectralClustering', 'Ward', 'AgglomerativeClustering', 'OPTICS', 'AffinityPropagation']:
      try:
        reapplyClustering(modelUsed, nbConditions, nbCluster, outputFolderResult)
      except:
        print(modelUsed, "failed")
    
  else:
    
    reapplyClustering('KMeans', nbConditions, nbCluster, outputFolderResult)
    