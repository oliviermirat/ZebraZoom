import pickle

import zebrazoom

# Applying the clustering on this dataframe

clusteringOptions = {
  'analyzeAllWellsAtTheSameTime' : 0, # put this to 1 for head-embedded videos, and to 0 for multi-well videos
  'pathToVideos' : '../zebrazoom/ZZoutput/',
  'nbCluster' : 3,
  'modelUsedForClustering' : 'KMeans', # put either 'KMeans' or 'GaussianMixture' here
  #'nbPcaComponents' : 30,
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
  'resFolder' : '../zebrazoom/dataanalysis/data',
  'nameOfFile' : 'example'
}

# Reloads the classifier previously created and get the nbFramesTakenIntoAccount value
infile = open('../zebrazoom/dataanalysis/classifiers/classifier_'+clusteringOptions['nameOfFile']+'.txt','rb')
[classifier, nbFramesTakenIntoAccount] = pickle.load(infile)
infile.close()
clusteringOptions['nbFramesTakenIntoAccount'] = nbFramesTakenIntoAccount

# Classifies bouts based on the clustering previously obtained
[allBouts, c] = zebrazoom.applyClustering(clusteringOptions, classifier, '../zebrazoom/dataanalysis/resultsClustering')

