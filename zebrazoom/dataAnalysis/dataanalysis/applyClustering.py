import scipy.io
import numpy as np
import pandas as pd
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler
import matplotlib.pyplot as plt
from sklearn.manifold import TSNE
from sklearn.cluster import KMeans
from sklearn.mixture import GaussianMixture
from zebrazoom.dataAnalysis.dataanalysis.visualizeClusters import visualizeClusters
from zebrazoom.dataAnalysis.dataanalysis.outputValidationVideo import outputValidationVideo
from zebrazoom.dataAnalysis.dataanalysis.activeLearning import prepareForActiveLearning
from scipy.stats import chi2
import cv2
import os
import shutil
import pickle

def applyClustering(clusteringOptions, classifier, outputFolder, ZZoutputLocation=''):

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
  useAngleAnd3GlobalParameters   = clusteringOptions['useAngleAnd3GlobalParameters'] if 'useAngleAnd3GlobalParameters' in clusteringOptions else 0
  videoSaveFirstTenBouts         = clusteringOptions['videoSaveFirstTenBouts']
  nbVideosToSave                 = clusteringOptions['nbVideosToSave']
  resFolder                      = clusteringOptions['resFolder']
  nameOfFile                     = clusteringOptions['nameOfFile']
  globalParametersCalculations   = clusteringOptions['globalParametersCalculations']
  
  modelUsedForClustering = clusteringOptions['modelUsedForClustering'] if 'modelUsedForClustering' in clusteringOptions else 'KMeans'
  
  removeOutliers = clusteringOptions['removeOutliers'] if 'removeOutliers' in clusteringOptions else False
  
  removeBoutsContainingNanValuesInParametersUsedForClustering = clusteringOptions['removeBoutsContainingNanValuesInParametersUsedForClustering'] if 'removeBoutsContainingNanValuesInParametersUsedForClustering' in clusteringOptions else True
  
  instaTBF   = ['instaTBF'+str(i)  for i in range(1,nbFramesTakenIntoAccount+1)]
  instaAmp   = ['instaAmp'+str(i)  for i in range(1,nbFramesTakenIntoAccount+1)]
  instaAsym  = ['instaAsym'+str(i) for i in range(1,nbFramesTakenIntoAccount+1)]

  tailAngles = ['tailAngles'+str(i) for i in range(1,nbFramesTakenIntoAccount+1)]

  instaSpeed       = ['instaSpeed'       + str(i) for i in range(1,nbFramesTakenIntoAccount+1)]
  instaHeadingDiff = ['instaHeadingDiff' + str(i) for i in range(1,nbFramesTakenIntoAccount+1)]
  instaHorizDispl  = ['instaHorizDispl'  + str(i) for i in range(1,nbFramesTakenIntoAccount+1)]
  
  allInstas  = instaTBF + instaAmp + instaAsym

  allInstas2 = tailAngles + instaSpeed + instaHeadingDiff + instaHorizDispl

  xaxis    = [0, 30]
  freqAxis = [0, 0.5]
  ampAxis  = [0, 1.6]
  asymAxis = [0, 0.8]
  angAxis  = [0, 1.5]

  possibleColors = ['b', 'r', 'g', 'k', 'c', 'm', 'y']
  possibleColorsNames = ['blue', 'red', 'green', 'black', 'cyan', 'magenta', 'yellow']
  
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
  
  if useAngleAnd3GlobalParameters:
    allInstaValues = dfParam[tailAngles].values
  
  # if modelUsedForClustering == 'KMeans':
  scaler = StandardScaler()
  allInstaValues = scaler.fit_transform(allInstaValues)
  
  if removeBoutsContainingNanValuesInParametersUsedForClustering:
    allInstaValuesLenBef = len(allInstaValues)
    try:
      dfParam = dfParam.drop([idx for idx, val in enumerate(~np.isnan(allInstaValues).any(axis=1)) if not(val)])
    except:
      scaler = StandardScaler()
      allInstaValues = scaler.fit_transform(allInstaValues)
      dfParam = dfParam.drop([idx for idx, val in enumerate(~np.isnan(allInstaValues).any(axis=1)) if not(val)])
    allInstaValues = allInstaValues[~np.isnan(allInstaValues).any(axis=1)]
    allInstaValuesLenAft = len(allInstaValues)
    if allInstaValuesLenBef - allInstaValuesLenAft > 0:
      print(allInstaValuesLenBef - allInstaValuesLenAft, " bouts (out of ", allInstaValuesLenBef, " ) were deleted because they contained NaN values")
    else:
      print("all bouts were kept (no nan values)")
  else:
    dfParam = dfParam.fillna(0)
    allInstaValues = np.nan_to_num(allInstaValues)
    print("nan values replaced by zeros")
  
  if 'level_0' in dfParam.columns:
    dfParam = dfParam.drop(['level_0'], axis=1)
  
  dfParam = dfParam.reset_index()
  if removeOutliers:
    covariance  = np.cov(allInstaValues , rowvar=False)
    covariance_pm1 = np.linalg.matrix_power(covariance, -1)
    centerpoint = np.mean(allInstaValues , axis=0)
    distances = []
    for i, val in enumerate(allInstaValues):
      p1 = val
      p2 = centerpoint
      distance = (p1-p2).T.dot(covariance_pm1).dot(p1-p2)
      distances.append(distance)
    distances = np.array(distances)
    cutoff = chi2.ppf(0.95, allInstaValues.shape[1])
    outlierIndexes = np.where(distances < cutoff )
    nbBoutsBefore = len(dfParam)
    print("Number of bouts before outliers removal:", len(dfParam))
    dfParam = dfParam.drop([idx for idx, val in enumerate(distances >= cutoff) if val])
    nbBoutsAfter = len(dfParam)
    print("Number of bouts after outliers removal:", len(dfParam))
    print("Percentage of bouts removed:", ((nbBoutsBefore-nbBoutsAfter)/nbBoutsBefore)*100, "%")
    allInstaValues = allInstaValues[ distances < cutoff , :]
  if classifier == 0:
    print("creating pca transform and applying it on the data")
    pca_result = pca.fit_transform(allInstaValues)
  else:
    print("applying pca (reloaded)")
    pca_result = pca.transform(allInstaValues)
    
  dfParam = dfParam.drop(['level_0'], axis=1)
  dfParam = dfParam.reset_index()
  
  if useAngleAnd3GlobalParameters:
    pca_result = pca_result[:, 0:3]
    pca_result = np.concatenate((pca_result, dfParam[['deltaHead', 'Speed', 'tailAngleIntegral']].values), axis=1)
    scaler     = StandardScaler()
    pca_result = scaler.fit_transform(pca_result)  

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
  
  [proportions, sortedRepresentativeBouts, sortedRepresentativeBoutsIndex] = visualizeClusters(dfParam, labels2, [], modelUsedForClustering, nbConditions, nbCluster, nbFramesTakenIntoAccount, scaleGraphs, showFigures, outputFolderResult, 0, 1)
  
  if False:
    prepareForActiveLearning(proportions, sortedRepresentativeBouts, outputFolderResult, nbCluster, pca_result, dfParam, sortedRepresentativeBoutsIndex, tailAngles)
  else:
    outputFolderResult2 = os.path.join(outputFolderResult, 'savedRawData')
    if os.path.exists(outputFolderResult2):
      shutil.rmtree(outputFolderResult2)
    os.mkdir(outputFolderResult2)
    pickle.dump({'pca_result': pca_result.tolist(), 'dfParam': dfParam}, open(os.path.join(outputFolderResult2, 'boutParameters.pkl'), 'wb'))
  
  return [dfParam, [pca, model]]
