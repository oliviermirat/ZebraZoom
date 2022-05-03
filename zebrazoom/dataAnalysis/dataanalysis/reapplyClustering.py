from sklearn import metrics
from sklearn.cluster import KMeans
from sklearn.mixture import GaussianMixture
from modAL.models import ActiveLearner
from zebrazoom.dataAnalysis.dataanalysis.visualizeClusters import visualizeClusters
import matplotlib.pyplot as plt
from sklearn import cluster
import numpy as np
import pickle
import shutil
import json
import os

def reapplyClustering(modelUsed, nbConditions, nbCluster, outputFolderResult):
  
  nbFramesTakenIntoAccount = 24
  scaleGraphs   = 1
  showFigures   = 0
  nbPCAComp     = -1 #10 # Default: -1: all components
  
  with open(os.path.join(outputFolderResult, 'boutParameters.pkl'), 'rb') as pickle_file:
    data = pickle.load(pickle_file)
  
  pca_result = np.array(data['pca_result'])
  dfParam    = data['dfParam']
  
  if nbPCAComp != -1:
    pca_result = pca_result[:, 0:nbPCAComp]
  
  if False:
    from matplotlib.pyplot import hist2d
    from scipy.stats import chi2
    hist2d(pca_result[:, 0], pca_result[:, 1], bins=500)
    plt.show()
  
  # Learning (and predicting) first model
  
  if modelUsed == 'KMeans':
    
    model = KMeans(n_clusters = nbCluster)
  
  elif modelUsed == 'AffinityPropagation':
  
    model = cluster.AffinityPropagation(damping=0.9, preference=-200, random_state=0)  
  
  elif modelUsed == 'MeanShift':
    
    bandwidth = cluster.estimate_bandwidth(pca_result, quantile=0.3)
    model = cluster.MeanShift(bandwidth=bandwidth, bin_seeding=True)
  
  elif modelUsed == 'SpectralClustering':
    
    model = cluster.SpectralClustering(n_clusters=nbCluster, eigen_solver="arpack", affinity="nearest_neighbors")
    
  elif modelUsed == 'Ward':
    
    from sklearn.neighbors import kneighbors_graph
    connectivity = kneighbors_graph(pca_result, n_neighbors= 10, include_self=False)
    connectivity = 0.5 * (connectivity + connectivity.T)
    model = cluster.AgglomerativeClustering(n_clusters=nbCluster, linkage="ward", connectivity=connectivity)
  
  elif modelUsed == 'AgglomerativeClustering':
  
    from sklearn.neighbors import kneighbors_graph
    connectivity = kneighbors_graph(pca_result, n_neighbors= 10, include_self=False)
    connectivity = 0.5 * (connectivity + connectivity.T)
    model = cluster.AgglomerativeClustering(linkage="average", affinity="cityblock", n_clusters=nbCluster,  connectivity=connectivity)
  
  elif modelUsed == 'DBSCAN':
    
    model = cluster.DBSCAN(eps=4)  
  
  elif modelUsed == 'OPTICS':
  
    model = cluster.OPTICS(min_samples=20, xi=0.05, min_cluster_size=0.1)
    
  elif modelUsed == 'BIRCH':
    
    model = cluster.Birch(n_clusters=nbCluster)
    
  elif modelUsed == 'GaussianMixture':
    
    model = GaussianMixture(n_components = nbCluster)
  
  else:
    
    model = 0 # KMeans(n_clusters = nbCluster)
  
  if type(model) != int:
  
    model.fit(pca_result)
    
    if modelUsed == 'DBSCAN':
      labels = model.labels_
      print("Labels:", np.unique(labels))
      nbCluster = len(np.unique(labels))
      model.labels_[model.labels_ == -1] = nbCluster - 1
    else:
      labels = model.predict(pca_result)
  
  else:
    
    labels = np.zeros(len(pca_result))
    
    for i in range(0, nbCluster):
      quantileBef = np.quantile(dfParam[modelUsed], i/nbCluster)
      quantileAft = np.quantile(dfParam[modelUsed], (i+1)/nbCluster)
      print("i, quantileBef, quantileAft:", i, quantileBef, quantileAft)
      labels[np.logical_and(dfParam[modelUsed] > quantileBef, dfParam[modelUsed] <= quantileAft)] = i
      print("median", str(i), " : ", np.median(dfParam[np.logical_and(dfParam[modelUsed] > quantileBef, dfParam[modelUsed] <= quantileAft)][modelUsed]))
    
    if False:
      import seaborn as sns
      dfParamWT        = dfParam[dfParam["Condition"] == "WT"]
      dfParamParkinson = dfParam[dfParam["Condition"] == "Parkinson"]
      plt.hist(dfParamWT["maxTailAngleAmplitude"].tolist(), 100)
      plt.show()
      plt.hist(dfParamParkinson["maxTailAngleAmplitude"].tolist(), 100)
      plt.show()
      # sns.histplot(data = dfParam, y=modelUsed, hue = "Condition")
    
  
  if modelUsed == 'GaussianMixture':
    predictedProbas = model.predict_proba(pca_result)
  
  # Sorting labels
  if type(model) != int:
    nbLabels       = nbCluster
    labels2        = np.zeros(len(labels))
    nbElemPerClass = np.zeros(nbLabels) 
    for i in range(0, nbLabels):
      nbElemPerClass[i] = labels.tolist().count(i)
    sortedIndices = (-nbElemPerClass).argsort()
    
    for i in range(0, len(labels)):
      labels2[i] = np.where(sortedIndices==labels[i])[0][0]
  else:
    labels2 = labels
  
  dfParam['classification'] = labels2
  
  if modelUsed == 'GaussianMixture':
    for j in range(0, nbLabels):
      probasClassJ = predictedProbas[:, sortedIndices[j]]
      dfParam['classProba' + str(j)] = probasClassJ
  
  
  print("Prediction:")
  print(labels2)
  
  predictedProb = []
  
  outputFolderResult3 = os.path.join(outputFolderResult, 'reaplyClustering_' + modelUsed[0:10] + '_' + str(nbCluster))
  if os.path.exists(outputFolderResult3):
    shutil.rmtree(outputFolderResult3)
  os.mkdir(outputFolderResult3)
  
  visualizeClusters(dfParam, labels2, predictedProb, modelUsed, nbConditions, nbCluster, nbFramesTakenIntoAccount, scaleGraphs, showFigures, outputFolderResult3, 0, 1)
  
  ###
  
  print("Silhouette Score:")
  silhouetteScore = metrics.silhouette_score(pca_result, labels2, metric='euclidean')
  print(silhouetteScore)
  print("")
  print("Calinski Harabasz Score:")
  calinskiHarabaszScore = metrics.calinski_harabasz_score(pca_result, labels2)
  print(calinskiHarabaszScore)
  print("")
  print("Davies Bouldin Score:")
  daviesBouldinScore = metrics.davies_bouldin_score(pca_result, labels2)
  print(daviesBouldinScore)
  
  if modelUsed == 'KMeans':
    elbowMethod = model.inertia_
  else:
    elbowMethod = -1
  
  return [silhouetteScore, calinskiHarabaszScore, daviesBouldinScore, elbowMethod]