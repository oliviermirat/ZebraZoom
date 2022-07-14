from sklearn.svm import SVC
from sklearn.neighbors import KNeighborsClassifier
from sklearn.naive_bayes import GaussianNB
from sklearn.cluster import KMeans
from sklearn.mixture import GaussianMixture
from zebrazoom.dataAnalysis.dataanalysis.visualizeClusters import visualizeClusters
import matplotlib.pyplot as plt
import numpy as np
import pickle
import shutil
import json
import os
import sys


def prepareForActiveLearning(proportions, sortedRepresentativeBouts, outputFolderResult, nbCluster, pca_result, dfParam, sortedRepresentativeBoutsIndex, tailAngles):
  
  outputFolderResult2 = os.path.join(outputFolderResult, 'activeLearning')
  if os.path.exists(outputFolderResult2):
    shutil.rmtree(outputFolderResult2)
  os.mkdir(outputFolderResult2)
  
  optimalLength = 12
  nbIterations  = 5
  
  # Plotting bouts one by one for each cluster and writing bout indices in txt file
  outF = open(os.path.join(outputFolderResult2, 'boutIndices.txt'), "w")
  for classed in range(0, len(proportions[0])):
    indices = sortedRepresentativeBouts[classed].index
    beginningMiddleEnd = False
    if beginningMiddleEnd:
      for j in range(0, 3):
        ind2size = optimalLength if len(indices) >= 3*optimalLength else max(1, int(len(indices) / 3))
        if j == 0:
          indices2 = indices[0:ind2size]
        elif j == 1:
          indices2 = indices[int(len(indices)/2) - int(ind2size/2) : int(len(indices)/2) + int(ind2size/2)]
        else:
          indices2 = indices[len(indices) - ind2size : len(indices)]
        # Plot
        fig, tabAx3 = plt.subplots(4, 3, figsize=(22.9, 8.8))
        for k in range(0, len(indices2)):
          tailAnglestab = dfParam.loc[indices2[k], tailAngles].tolist()
          tabAx3[int(k / 3), k % 3].plot(tailAnglestab, 'b', label = str(indices2[k]))
          tabAx3[int(k / 3), k % 3].legend()
          tabAx3[int(k / 3), k % 3].title.set_text(str(indices2[k]))
        region = 'mostRepresentative' if j == 0 else 'inBetween' if j == 1 else 'leastRepresentative'
        plt.savefig(os.path.join(outputFolderResult2, 'cluster' + str(classed + 1) + '_' + region + '.png'))
        # Saving indices in txt
        line = 'cluster' + str(classed) + '_' + region + ' = [' + ', '.join([str(ind) for ind in indices2]) + "]\n"
        outF.write(line)
    else:
      for j in range(0, nbIterations):
        ind2size = optimalLength if len(indices) >= 3*optimalLength else max(1, int(len(indices) / 3))
        if (j+1)*ind2size < len(indices):
          indices2 = indices[j*ind2size:(j+1)*ind2size]
          # Plot
          fig, tabAx3 = plt.subplots(4, 3, figsize=(22.9, 8.8))
          for k in range(0, len(indices2)):
            tailAnglestab = dfParam.loc[indices2[k], tailAngles].tolist()
            tabAx3[int(k / 3), k % 3].plot(tailAnglestab, 'b', label = str(indices2[k]))
            tabAx3[int(k / 3), k % 3].legend()
            tabAx3[int(k / 3), k % 3].title.set_text(str(indices2[k]))
          region = 'mostRepresentative'
          plt.savefig(os.path.join(outputFolderResult2, 'cluster' + str(classed + 1) + '_' + region + '_' + str(j*ind2size) + '_' + str((j+1)*ind2size) + '.png'))
          # Saving indices in txt
          line = 'cluster' + str(classed) + '_' + region + '_' + str(j*ind2size) + '_' + str((j+1)*ind2size) + ' = [' + ', '.join([str(ind) for ind in indices2]) + "]\n"
          outF.write(line)
      for j in range(0, nbIterations):
        ind2size = optimalLength if len(indices) >= 3*optimalLength else max(1, int(len(indices) / 3))
        if len(indices)-(j+1)*ind2size > 0:
          indices2 = indices[len(indices)-(j+1)*ind2size:len(indices)-j*ind2size]
          # Plot
          fig, tabAx3 = plt.subplots(4, 3, figsize=(22.9, 8.8))
          for k in range(0, len(indices2)):
            tailAnglestab = dfParam.loc[indices2[k], tailAngles].tolist()
            tabAx3[int(k / 3), k % 3].plot(tailAnglestab, 'b', label = str(indices2[k]))
            tabAx3[int(k / 3), k % 3].legend()
            tabAx3[int(k / 3), k % 3].title.set_text(str(indices2[k]))
          region = 'leastRepresentative'
          plt.savefig(os.path.join(outputFolderResult2, 'cluster' + str(classed + 1) + '_' + region + '_' + str(len(indices)-(j+1)*ind2size) + '_' + str(len(indices)-j*ind2size) + '.png'))
          # Saving indices in txt
          line = 'cluster' + str(classed) + '_' + region + '_' + str(len(indices)-(j+1)*ind2size) + '_' + str(len(indices)-j*ind2size) + ' = [' + ', '.join([str(ind) for ind in indices2]) + "]\n"
          outF.write(line)
  outF.close()
  
  pickle.dump({'pca_result': pca_result.tolist(), 'dfParam': dfParam}, open(os.path.join(outputFolderResult2, 'boutParameters.pkl'), 'wb'))


def activeLearning(modelUsed, nbConditions, nbCluster, outputFolderResult, N_QUERIES, manualClassicationPath):
  from PyQt5.QtWidgets import QInputDialog

  from modAL.models import ActiveLearner
  
  nbFramesTakenIntoAccount = 24
  scaleGraphs   = 1
  showFigures   = 0
  
  with open(os.path.join(outputFolderResult, 'boutParameters.pkl'), 'rb') as pickle_file:
    data = pickle.load(pickle_file)
  with open(manualClassicationPath, 'rb') as classification_file:
    manualClassifications = json.load(classification_file)
  
  pca_result = np.array(data['pca_result'])
  dfParam    = data['dfParam']

  y_train    = np.array([])
  ind_train  = []
  for ind in manualClassifications:
    classIndIndices = manualClassifications[ind]
    ind_train       = ind_train + classIndIndices
    y_train         = np.concatenate((y_train, np.array([int(ind) for i in range(0, len(classIndIndices))])))
  X_train = pca_result[ind_train, :]
  
  X_pool   = np.delete(pca_result, ind_train, axis=0)
  ind_pool = np.delete(np.array([ind for ind in range(0, len(pca_result))]), ind_train, axis=0)
  tailAngles = ['tailAngles' + str(i) for i in range(1, 25)]
  tailAngles_pool = np.array(dfParam.loc[ind_pool, tailAngles])
  
  # Learning (and predicting) first model
  
  if modelUsed == 'KNeighborsClassifier':
    model = KNeighborsClassifier(n_neighbors = nbCluster)
  elif modelUsed == 'SVC':
    model = SVC()
  elif modelUsed == 'GaussianNB':
    model = GaussianNB()
  elif modelUsed == 'KMeans':
    model = KMeans(n_clusters = nbCluster)
  elif modelUsed == 'GaussianMixture':
    model = GaussianMixture(n_components = nbCluster)
  else:
    model = KMeans(n_clusters = nbCluster)
  
  learner = ActiveLearner(estimator=model, X_training=X_train, y_training=y_train)
  
  predictions = learner.predict(pca_result)
  
  print("Prediction after first training:")
  print(predictions)
  
  # Actual active learning start
  
  for index in range(N_QUERIES):
    
    query_index, query_instance = learner.query(X_pool)
    
    plt.plot(tailAngles_pool[query_index][0])
    plt.show()
    
    userInput, _ok = QInputDialog.getInt(None, "Cluster Number", "Enter the cluster number of this bout:")
    
    X, y = X_pool[query_index].reshape(1, -1), np.array([userInput])
    
    learner.teach(X=X, y=y)
    
    # Remove the queried instance from the unlabeled pool. # Add tail angle remove
    X_pool = np.delete(X_pool, query_index, axis=0)
    tailAngles_pool = np.delete(tailAngles_pool, query_index, axis=0)
  
  # See new results
  
  predictions = learner.predict(pca_result)
  
  print("Prediction after second training:")
  print(predictions)
  
  outputFolderResult3 = os.path.join(outputFolderResult, 'activeLearnOutput' + str(1))
  if os.path.exists(outputFolderResult3):
    shutil.rmtree(outputFolderResult3)
  os.mkdir(outputFolderResult3)
  
  predictedProb = []
  
  visualizeClusters(dfParam, predictions, predictedProb, modelUsed, nbConditions, nbCluster, nbFramesTakenIntoAccount, scaleGraphs, showFigures, outputFolderResult3, 0, 1)
  
  