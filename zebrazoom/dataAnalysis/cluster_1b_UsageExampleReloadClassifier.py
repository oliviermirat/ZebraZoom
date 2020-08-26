import sys
sys.path.insert(1, './dataanalysis/')
import pickle
from applyClustering import applyClustering


# Applying the clustering on this dataframe

clusteringOptions = {
  'analyzeAllWellsAtTheSameTime' : 0, # put this to 1 for head-embedded videos, and to 0 for multi-well videos
  'pathToVideos' : '../ZZoutput/',
  'nbCluster' : 3,
  #'nbPcaComponents' : 30,
  'nbFramesTakenIntoAccount' : 28,
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

# Reloads the classifier previously created
infile = open('classifiers/classifier_'+clusteringOptions['nameOfFile']+'.txt','rb')
classifier = pickle.load(infile)
infile.close()

# Classifies bouts based on the clustering previously obtained
[allBouts, c] = applyClustering(clusteringOptions, classifier)

