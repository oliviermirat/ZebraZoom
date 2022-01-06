from zebrazoom.dataAnalysis.dataanalysis.reapplyClustering import reapplyClustering

def launchReapplyClustering():

  outputFolderResult = 'zebrazoom/dataAnalysis/resultsClustering/parkinsonFreelySwimForClustering_OutliersRemoved_BASSstyleParam2/activeLearning/'
  nbConditions  = 2
  nbCluster     = 4

  for modelUsed in ['KMeans', 'GaussianMixture', 'BIRCH', 'DBSCAN', 'MeanShift', 'SpectralClustering', 'Ward', 'AgglomerativeClustering', 'OPTICS', 'AffinityPropagation']:
    try:
      reapplyClustering(modelUsed, nbConditions, nbCluster, outputFolderResult)
    except:
      print(modelUsed, "failed")
