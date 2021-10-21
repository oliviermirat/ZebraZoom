import scipy.io
import numpy as np
import pandas as pd
from sklearn.decomposition import PCA
from sklearn.preprocessing import StandardScaler
import matplotlib.pyplot as plt
from sklearn.manifold import TSNE
from sklearn.cluster import KMeans
from sklearn.mixture import GaussianMixture
from zebrazoom.dataAnalysis.dataanalysis.readValidationVideoDataAnalysis import readValidationVideoDataAnalysis
from zebrazoom.dataAnalysis.dataanalysis.outputValidationVideo import outputValidationVideo
import cv2
import os
import shutil
import pickle

def applyClustering(clusteringOptions, classifier, outputFolder):

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

  # Calculating proportions of each conditions in each class

  df2 = dfParam[['Condition','classification']]
  proportions = np.zeros((nbConditions, nbCluster))
  for idxCond, cond in enumerate(np.unique(dfParam['Condition'].values)):
    for classed in range(0, len(proportions[0])):
      proportions[idxCond, classed] = len(df2.loc[(df2['Condition'] == cond) & (df2['classification'] == classed)])

  for i in range(0, nbConditions):
    proportions[i, :] = proportions[i, :] / sum(proportions[i, :])
    
  outF = open(os.path.join(outputFolderResult, 'proportions.txt'), "w")
  labelX = ""
  for i in range(0, nbCluster):
    labelX = labelX + "Cluster " + str(i+1) + " : \n"
    for j, cond in enumerate(np.unique(dfParam['Condition'].values)):
      labelX = labelX + cond + ": " + str(round(proportions[j,i]*100*100)/100) + "%, "
      labelX = labelX + "\n"
    labelX = labelX + "\n"
  outF.write(labelX)
  outF.write("\n")
  outF.close()

  # Plotting each cluster one by one

  mostRepresentativeBout = np.zeros((nbConditions,nbCluster))

  # fig2 = matplotlib.pyplot.figure(figsize=(8.0, 5.0))

  fig, tabAx = plt.subplots(4, len(proportions[0]), figsize=(22.9, 8.8))

  for idxCond, cond in enumerate(np.unique(dfParam['Condition'].values)):
    for classed in range(0, len(proportions[0])):
      dfTemp = dfParam.loc[(dfParam['Condition'] == cond) & (dfParam['classification'] == classed)]
      instaTBFtab   = dfTemp[instaTBF]
      instaAmptab   = dfTemp[instaAmp]
      instaAsymtab  = dfTemp[instaAsym]
      tailAnglestab = dfTemp[tailAngles]
      color = possibleColors[idxCond]
      tabAx[0, classed].plot(instaTBFtab.median().values,  color, label=cond)
      tabAx[1, classed].plot(instaAmptab.median().values,  color)
      tabAx[2, classed].plot(instaAsymtab.median().values, color)
      tabAx[3, classed].plot(tailAnglestab.median().values, color)
      
      instaTBFmedian  = instaTBFtab.median().values
      instaAmpmedian  = instaAmptab.median().values
      instaAsymmedian = instaAsymtab.median().values
      
      dist = abs(instaTBFtab-instaTBFmedian).sum(axis=1)/abs(instaTBFmedian).sum() + abs(instaAmptab-instaAmpmedian).sum(axis=1)/abs(instaAmpmedian).sum() + abs(instaAsymtab-instaAsymmedian).sum(axis=1)/abs(instaAsymmedian).sum()
      if len(dist):
        idMinDist = dist.idxmin()
      else:
        idMinDist = -1
      mostRepresentativeBout[idxCond, classed] = idMinDist
  
  if scaleGraphs:
    for classed in range(0, len(proportions[0])):
      tabAx[0, classed].scatter(xaxis, freqAxis, None, 'w')
      tabAx[1, classed].scatter(xaxis, ampAxis, None, 'w')
      tabAx[2, classed].scatter(xaxis, asymAxis, None, 'w')
      tabAx[3, classed].scatter(xaxis, angAxis, None, 'w')
  tabAx[0, 0].legend()
  tabAx[0, 0].set_ylabel('Avg Insta Frequency')
  tabAx[1, 0].set_ylabel('Avg Insta Amplitude')
  tabAx[2, 0].set_ylabel('Avg Insta Asymetry')
  tabAx[3, 0].set_ylabel('Avg Angle')
  for i in range(0, nbCluster):
    labelX = "Cluster " + str(i+1) + "\n"
    for j, condName in enumerate(np.unique(dfParam['Condition'].values)):
      labelX = labelX + "for " + condName + " :  " + str(round(proportions[j,i]*100*100)/100) + "%\n"
    tabAx[3, i].set_xlabel(labelX)
  plt.savefig(os.path.join(outputFolderResult, 'medianValuesUsedForClusteringForEachClusterAndCondition.png'))
  if showFigures:
    plt.show()

  # Plot most representative bout for each cluster
  fig, tabAx2 = plt.subplots(4, len(proportions[0]), figsize=(22.9, 8.8))
  for cond in range(0, len(proportions)):
    for classed in range(0, len(proportions[0])):
      idMinDist = mostRepresentativeBout[cond, classed]
      if idMinDist != -1 and not(np.isnan(idMinDist)):
        instaTBFtab   = dfParam.loc[idMinDist, instaTBF]
        instaAmptab   = dfParam.loc[idMinDist, instaAmp]
        instaAsymtab  = dfParam.loc[idMinDist, instaAsym]
        tailAnglestab = dfParam.loc[idMinDist, tailAngles]
        color = possibleColors[cond]
        tabAx2[0, classed].plot(instaTBFtab.values,  color)
        tabAx2[1, classed].plot(instaAmptab.values,  color)
        tabAx2[2, classed].plot(instaAsymtab.values, color)
        tabAx2[3, classed].plot(tailAnglestab.values, color)
  if scaleGraphs:
    for classed in range(0, len(proportions[0])):
      tabAx2[0, classed].scatter(xaxis, freqAxis, None, 'w')
      tabAx2[1, classed].scatter(xaxis, ampAxis, None, 'w')
      tabAx2[2, classed].scatter(xaxis, asymAxis, None, 'w')
      tabAx2[3, classed].scatter(xaxis, angAxis, None, 'w')
  tabAx2[0, 0].set_ylabel('Avg Insta Frequency')
  tabAx2[1, 0].set_ylabel('Avg Insta Amplitude')
  tabAx2[2, 0].set_ylabel('Avg Insta Asymetry')
  tabAx2[3, 0].set_ylabel('Avg Angle')
  for i in range(0, nbCluster):
    labelX = "Most representative bout of cluster "+ str(i+1) + ":\n"
    for j, condName in enumerate(np.unique(dfParam['Condition'].values)):
      labelX = labelX + "for " + condName + " (in " + possibleColorsNames[j] + ")\n"
    tabAx2[3, i].set_xlabel(labelX)
  plt.savefig(os.path.join(outputFolderResult, 'mostRepresentativeBoutForEachClusterAndCondition.png'))
  if showFigures:
    plt.show()

  # Getting most representative sorted bouts
  sortedRepresentativeBouts = []
  for classed in range(0, len(proportions[0])):
    dfTemp = dfParam.loc[(dfParam['classification'] == classed)]
    instaTBFtab   = dfTemp[instaTBF]
    instaAmptab   = dfTemp[instaAmp]
    instaAsymtab  = dfTemp[instaAsym]
    tailAnglestab = dfTemp[tailAngles]
    
    instaTBFmedian  = instaTBFtab.median().values
    instaAmpmedian  = instaAmptab.median().values
    instaAsymmedian = instaAsymtab.median().values

    dist = abs(instaTBFtab-instaTBFmedian).sum(axis=1)/abs(instaTBFmedian).sum() + abs(instaAmptab-instaAmpmedian).sum(axis=1)/abs(instaAmpmedian).sum() + abs(instaAsymtab-instaAsymmedian).sum(axis=1)/abs(instaAsymmedian).sum()
    
    sortedRepresentativeBouts.append(dfParam.loc[dist.index.values[dist.values.argsort()], tailAngles])

  # Plot most representative bouts
  nbOfMostRepresentativeBoutsToPlot = 10000000000000
  for classed in range(0, len(proportions[0])):
    nb = len(sortedRepresentativeBouts[classed].index)
    if nb < nbOfMostRepresentativeBoutsToPlot:
      nbOfMostRepresentativeBoutsToPlot = nb
  if nbOfMostRepresentativeBoutsToPlot > 100:
    nbOfMostRepresentativeBoutsToPlot = 100
  fig, tabAx3 = plt.subplots(len(proportions[0]),1, figsize=(22.9, 8.8))
  for classed in range(0, len(proportions[0])):
    indices = sortedRepresentativeBouts[classed].index
    for j in range(0, nbOfMostRepresentativeBoutsToPlot):
      tailAnglestab = sortedRepresentativeBouts[classed].loc[indices[j]].values
      color = 'b'
      tabAx3[classed].plot(tailAnglestab, color)
  for i in range(0,len(proportions[0])):
    tabAx3[i].set_ylabel('Cluster '+str(i+1))
  tabAx3[len(proportions[0])-1].set_xlabel("Tail angle over time for the\n"+str(nbOfMostRepresentativeBoutsToPlot)+' most representative bouts for each cluster')
  plt.savefig(os.path.join(outputFolderResult, str(nbOfMostRepresentativeBoutsToPlot) + 'mostRepresentativeBoutsForEachCluster.png'))
  if showFigures:
    plt.show()

  # Plot most representative bouts - second plot
  fig, tabAx3 = plt.subplots(len(proportions[0]),1, figsize=(22.9, 8.8))
  for classed in range(0, len(proportions[0])):
    nbOfMostRepresentativeBoutsToPlot = 10000000000000
    nbOfMostRepresentativeBoutsToPlot = len(sortedRepresentativeBouts[classed].index)
    if nbOfMostRepresentativeBoutsToPlot > 100:
      nbOfMostRepresentativeBoutsToPlot = 100
    indices = sortedRepresentativeBouts[classed].index
    for j in range(0, nbOfMostRepresentativeBoutsToPlot):
      tailAnglestab = sortedRepresentativeBouts[classed].loc[indices[j]].values
      color = 'b'
      tabAx3[classed].plot(tailAnglestab, color)
      
  for i in range(0,len(proportions[0])):
    tabAx3[i].set_ylabel('Cluster '+str(i+1))
  tabAx3[len(proportions[0])-1].set_xlabel("Tail angle over time for the most representative bouts for each cluster")
  plt.savefig(os.path.join(outputFolderResult, 'mostRepresentativeBoutsForEachCluster.png'))
  if showFigures:
    plt.show()

  # Creating validation videos: Beginning, middle, and end. (10 movements each)
  if False:
    length = 150
    for boutCategory in range(0, nbCluster):
      print("boutCategory:",boutCategory)
      out = cv2.VideoWriter(os.path.join(outputFolderResult, 'cluster' + str(boutCategory) + '.avi'),cv2.VideoWriter_fourcc('M','J','P','G'), 10, (length,length))
      indices = sortedRepresentativeBouts[boutCategory].index
      print("total:",len(indices))
      r = [i for i in range(0, 10)] + [i for i in range(int(len(indices)/2)-10, int(len(indices)/2))] + [i for i in range(len(indices)-10, len(indices))]
      for num in r:
        print("num:",num)
        BoutStart = int(dfParam.loc[indices[num],'BoutStart'])
        BoutEnd   = int(dfParam.loc[indices[num],'BoutEnd'])
        Well_ID   = int(dfParam.loc[indices[num],'Well_ID']) - 1
        Trial_ID  = dfParam.loc[indices[num],'Trial_ID']
        out = outputValidationVideo(pathToVideos, Trial_ID, '.txt', Well_ID, 1, BoutStart, BoutEnd, out, length, analyzeAllWellsAtTheSameTime)
      out.release()
      
  # Creating validation videos: Beginning (10 movements each)
  if videoSaveFirstTenBouts:
    length = 150
    for boutCategory in range(0, nbCluster):
      print("boutCategory:",boutCategory+1)
      out = cv2.VideoWriter(os.path.join(outputFolderResult, 'cluster' + str(boutCategory+1) + '.avi'),cv2.VideoWriter_fourcc('M','J','P','G'), 10, (length,length))
      indices = sortedRepresentativeBouts[boutCategory].index
      nbTemp = len(indices)
      if nbTemp < nbVideosToSave:
        nbVideosToSave = nbTemp
      
      r = [i for i in range(0, nbVideosToSave)]
      for num in r:
        print("num:",num)
        BoutStart = int(dfParam.loc[indices[num],'BoutStart'])
        BoutEnd   = int(dfParam.loc[indices[num],'BoutEnd'])
        Well_ID   = int(dfParam.loc[indices[num],'Well_ID'])
        Trial_ID  = dfParam.loc[indices[num],'Trial_ID']
        out = outputValidationVideo(pathToVideos, Trial_ID, '.txt', Well_ID, 1, BoutStart, BoutEnd, out, length, analyzeAllWellsAtTheSameTime)
      out.release()
  
  # Looking into global parameters
  if globalParametersCalculations:
    globParam = ['BoutDuration', 'TotalDistance', 'Speed', 'NumberOfOscillations', 'meanTBF', 'maxTailAngleAmplitude']
    fig, tabAx = plt.subplots(2, 3, figsize=(22.9, 8.8))
    for idx, parameter in enumerate(globParam):
      concatenatedValues = []
      for boutCategory in range(0, nbCluster):
        indices = sortedRepresentativeBouts[boutCategory].index
        values  = dfParam.loc[indices[:],parameter].values
        concatenatedValues.append(values)
      tabAx[int(idx/3), idx%3].set_title(parameter)
      tabAx[int(idx/3), idx%3].boxplot(concatenatedValues)
    plt.savefig(os.path.join(outputFolderResult, 'globalParametersforEachCluster.png'))
    if showFigures:
      plt.plot()
      plt.show()
  
  # Saves classifications
  dfParam[['Trial_ID','Well_ID','NumBout','classification']].to_csv(os.path.join(os.path.join(outputFolder, clusteringOptions['nameOfFile']), 'classifications.txt'))
  
  return [dfParam, [pca, model]]
