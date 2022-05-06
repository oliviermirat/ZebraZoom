import scipy.io
import numpy as np
import pandas as pd
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler
import matplotlib.pyplot as plt
from sklearn.manifold import TSNE
from sklearn.cluster import KMeans
from sklearn.mixture import GaussianMixture
from zebrazoom.dataAnalysis.dataanalysis.outputValidationVideo import outputValidationVideo
import cv2
import os
import shutil
import pickle

def applyClusteringPerFrame(clusteringOptions, classifier, outputFolder):

  pca = 0
  kme = 0
  if classifier:
    print("reloading classifier")
    pca = classifier[0]
    model  = classifier[1]

  analyzeAllWellsAtTheSameTime   = clusteringOptions['analyzeAllWellsAtTheSameTime']
  pathToVideos                   = clusteringOptions['pathToVideos']
  nbCluster                      = clusteringOptions['nbCluster']
  if 'nbPcaComponents' in clusteringOptions:
    nbPcaComponents              = clusteringOptions['nbPcaComponents']
  else:
    nbPcaComponents              = 0
  nbFramesTakenIntoAccount       = clusteringOptions['nbFramesTakenIntoAccount']
  scaleGraphs                    = clusteringOptions['scaleGraphs']
  showFigures                    = clusteringOptions['showFigures']
  useFreqAmpAsym                 = clusteringOptions['useFreqAmpAsym']
  useAngles                      = clusteringOptions['useAngles']
  useAnglesSpeedHeadingDisp      = clusteringOptions['useAnglesSpeedHeadingDisp']
  useAnglesSpeedHeading          = clusteringOptions['useAnglesSpeedHeading']
  useAnglesSpeed                 = clusteringOptions['useAnglesSpeed']
  useAnglesHeading               = clusteringOptions['useAnglesHeading']
  useAnglesHeadingDisp           = clusteringOptions['useAnglesHeadingDisp']
  useFreqAmpAsymSpeedHeadingDisp = clusteringOptions['useFreqAmpAsymSpeedHeadingDisp']
  videoSaveFirstTenBouts         = clusteringOptions['videoSaveFirstTenBouts']
  nbVideosToSave                 = clusteringOptions['nbVideosToSave']
  resFolder                      = clusteringOptions['resFolder']
  nameOfFile                     = clusteringOptions['nameOfFile']
  globalParametersCalculations   = clusteringOptions['globalParametersCalculations']
  
  if 'modelUsedForClustering' in clusteringOptions:
    modelUsedForClustering = clusteringOptions['modelUsedForClustering']
  else:
    modelUsedForClustering = 'KMeans'

  instaTBF   = ['instaTBF']
  instaAmp   = ['instaAmp']
  instaAsym  = ['instaAsym']

  tailAngles = ['tailAngles']

  instaSpeed       = ['instaSpeed']
  instaHeadingDiff = ['instaHeadingDiff']
  instaHorizDispl  = ['instaHorizDispl']
  
  allInstas  = instaTBF + instaAmp + instaAsym

  allInstas2 = tailAngles + instaSpeed + instaHeadingDiff + instaHorizDispl

  xaxis    = [0, 30]
  freqAxis = [0, 0.5]
  ampAxis  = [0, 1.6]
  asymAxis = [0, 0.8]
  angAxis  = [0, 1.5]

  possibleColors = ['b', 'r', 'g', 'k']
  possibleColorsNames = ['blue', 'red', 'green', 'black']
  
  outputFolderResult = os.path.join(outputFolder, nameOfFile)
  
  if os.path.exists(outputFolderResult):
    shutil.rmtree(outputFolderResult)
  os.mkdir(outputFolderResult)

  infile = open(os.path.join(resFolder, nameOfFile + '.pkl'),'rb')
  dfParam = pickle.load(infile)
  infile.close()

  nbConditions = len(np.unique(dfParam['Condition'].values))

  # Applying PCA
  if classifier == 0:
    print("creating pca object")
    if nbPcaComponents:
      pca = PCA(n_components = nbPcaComponents)
    else:
      pca = PCA()

  if useFreqAmpAsym:
    allInstaValues = dfParam[allInstas].values

  if useAngles:
    allInstaValues = dfParam[tailAngles].values

  if useAnglesSpeedHeadingDisp:
    allInstaValues = dfParam[tailAngles + instaSpeed + instaHeadingDiff + instaHorizDispl].values
    
  if useAnglesSpeedHeading:
    allInstaValues = dfParam[tailAngles + instaSpeed + instaHeadingDiff].values
    
  if useAnglesSpeed:
    allInstaValues = dfParam[tailAngles + instaSpeed].values

  if useAnglesHeading:
    allInstaValues = dfParam[tailAngles + instaHeadingDiff].values
    
  if useAnglesHeadingDisp:
    allInstaValues = dfParam[tailAngles + instaHeadingDiff + instaHorizDispl].values
    
  if useFreqAmpAsymSpeedHeadingDisp:
    allInstaValues = dfParam[allInstas + instaSpeed + instaHeadingDiff + instaHorizDispl].values

  if modelUsedForClustering == 'KMeans':
    scaler = StandardScaler()
    allInstaValues = scaler.fit_transform(allInstaValues)

  allInstaValuesLenBef = len(allInstaValues)
  dfParam = dfParam.drop([idx for idx, val in enumerate(~np.isnan(allInstaValues).any(axis=1)) if not(val)])
  allInstaValues = allInstaValues[~np.isnan(allInstaValues).any(axis=1)]
  allInstaValuesLenAft = len(allInstaValues)
  if allInstaValuesLenBef - allInstaValuesLenAft > 0:
    print(allInstaValuesLenBef - allInstaValuesLenAft, " bouts (out of ", allInstaValuesLenBef, " ) were deleted because they contained NaN values")
  else:
    print("all bouts were kept (no nan values)")

  if classifier == 0:
    print("creating pca transform and applying it on the data")
    pca_result = pca.fit_transform(allInstaValues)
  else:
    print("applying pca (reloaded)")
    pca_result = pca.transform(allInstaValues)
  
  ind = []
  for i in range(0,nbConditions):
    ind.append(dfParam.loc[(dfParam['Condition'] == i)].index.values)
    
  # KMean clustering
  if classifier == 0:
    if modelUsedForClustering == 'KMeans':
      model = KMeans(n_clusters = nbCluster)
    elif modelUsedForClustering == 'GaussianMixture':
      model = GaussianMixture(n_components = nbCluster)
    else:
      model = KMeans(n_clusters = nbCluster)
    model.fit(pca_result)
    
  labels = model.predict(pca_result)
  if modelUsedForClustering == 'GaussianMixture':
    predictedProbas = model.predict_proba(pca_result)

  # Sorting labels
  nbLabels       = clusteringOptions['nbCluster']
  labels2        = np.zeros(len(labels))
  nbElemPerClass = np.zeros(nbLabels) 
  for i in range(0, nbLabels):
    nbElemPerClass[i] = labels.tolist().count(i)
  sortedIndices = (-nbElemPerClass).argsort()
  for i in range(0, len(labels)):
    labels2[i] = np.where(sortedIndices==labels[i])[0][0]
  dfParam['classification'] = labels2
  
  
  if modelUsedForClustering == 'GaussianMixture':
    for j in range(0, nbLabels):
      probasClassJ = predictedProbas[:, sortedIndices[j]]
      dfParam['classProba' + str(j)] = probasClassJ
  
  # Saves classifications
  dfParam.to_excel(os.path.join(os.path.join(outputFolder, clusteringOptions['nameOfFile']), 'classifications.xlsx'))
  
  return [dfParam, [pca, model]]
