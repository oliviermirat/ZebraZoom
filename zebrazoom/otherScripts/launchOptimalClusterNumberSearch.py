from zebrazoom.dataAnalysis.dataanalysis.reapplyClustering import reapplyClustering
import matplotlib.pyplot as plt
import numpy as np
import pickle

def launchOptimalClusterNumberSearch():

  outputFolderResult = 'zebrazoom/dataAnalysis/resultsClustering/parkinsonFreelySwimForClustering_OutliersRemoved_BASSstyleParam2/activeLearning/'
  nbConditions    = 2
  nbClusterToTest = 7

  KMeans = {'silhouetteScore':       np.array([-1. for i in range(0, 2 + nbClusterToTest)]),
            'calinskiHarabaszScore': np.array([-1. for i in range(0, 2 + nbClusterToTest)]),
            'daviesBouldinScore':    np.array([-1. for i in range(0, 2 + nbClusterToTest)]),
            'elbowMethod':           np.array([-1. for i in range(0, 2 + nbClusterToTest)])}

  GaussianMixture = {'silhouetteScore':       np.array([-1. for i in range(0, 2 + nbClusterToTest)]),
                     'calinskiHarabaszScore': np.array([-1. for i in range(0, 2 + nbClusterToTest)]),
                     'daviesBouldinScore':    np.array([-1. for i in range(0, 2 + nbClusterToTest)]),
                     'elbowMethod':           np.array([-1. for i in range(0, 2 + nbClusterToTest)])}

  modelUsed = 'KMeans'
  for nbCluster in range(2, nbClusterToTest + 2):
    [silhouetteScore, calinskiHarabaszScore, daviesBouldinScore, elbowMethod] = reapplyClustering(modelUsed, nbConditions, nbCluster, outputFolderResult)
    KMeans['silhouetteScore'][nbCluster]       = silhouetteScore
    KMeans['calinskiHarabaszScore'][nbCluster] = calinskiHarabaszScore
    KMeans['daviesBouldinScore'][nbCluster]    = daviesBouldinScore
    KMeans['elbowMethod'][nbCluster]           = elbowMethod

  modelUsed = 'GaussianMixture'
  for nbCluster in range(2, nbClusterToTest + 2):
    [silhouetteScore, calinskiHarabaszScore, daviesBouldinScore, elbowMethod] = reapplyClustering(modelUsed, nbConditions, nbCluster, outputFolderResult)
    GaussianMixture['silhouetteScore'][nbCluster]       = silhouetteScore
    GaussianMixture['calinskiHarabaszScore'][nbCluster] = calinskiHarabaszScore
    GaussianMixture['daviesBouldinScore'][nbCluster]    = daviesBouldinScore
    GaussianMixture['elbowMethod'][nbCluster]           = elbowMethod

  with open('scoresComparaison.pkl', 'wb') as handle:
    pickle.dump([KMeans, GaussianMixture], handle, protocol=pickle.HIGHEST_PROTOCOL)

  # with open('scoresComparaison.pkl', 'rb') as handle:
    # b = pickle.load(handle)
  # KMeans = b[0]
  # GaussianMixture = b[1]

  fig, tabAx = plt.subplots(2, 2, figsize=(22.9, 8.8))

  tabAx[0, 0].plot([i for i in range(2, nbClusterToTest + 2)], KMeans['silhouetteScore'][2:nbClusterToTest + 2], label='KMeans')
  tabAx[0, 1].plot([i for i in range(2, nbClusterToTest + 2)], KMeans['calinskiHarabaszScore'][2:nbClusterToTest + 2], label='KMeans')
  tabAx[1, 0].plot([i for i in range(2, nbClusterToTest + 2)], KMeans['daviesBouldinScore'][2:nbClusterToTest + 2], label='KMeans')
  tabAx[1, 1].plot([i for i in range(2, nbClusterToTest + 2)], KMeans['elbowMethod'][2:nbClusterToTest + 2], label='KMeans')

  tabAx[0, 0].plot([i for i in range(2, nbClusterToTest + 2)], GaussianMixture['silhouetteScore'][2:nbClusterToTest + 2], label='GaussianMixture')
  tabAx[0, 1].plot([i for i in range(2, nbClusterToTest + 2)], GaussianMixture['calinskiHarabaszScore'][2:nbClusterToTest + 2], label='GaussianMixture')
  tabAx[1, 0].plot([i for i in range(2, nbClusterToTest + 2)], GaussianMixture['daviesBouldinScore'][2:nbClusterToTest + 2], label='GaussianMixture')
  # tabAx[1, 1].plot([i for i in range(2, nbClusterToTest + 2)], GaussianMixture['elbowMethod'][2:nbClusterToTest + 2], label='GaussianMixture')
  
  tabAx[0, 0].set_title("Silhouette Score")
  tabAx[0, 1].set_title("Calinski Harabasz Score")
  tabAx[1, 0].set_title("Davies Bouldin Score")
  tabAx[1, 1].set_title("Elbow Method")
  
  plt.legend()
  
  plt.savefig('scoresComparaison.png')
