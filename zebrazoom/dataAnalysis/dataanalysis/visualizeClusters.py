import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np
import cv2
import os

def visualizeClusters(dfParam, classifications, predictedProbas, modelUsedForClustering, nbConditions, nbCluster, nbFramesTakenIntoAccount, scaleGraphs, showFigures, outputFolderResult, videoSaveFirstTenBouts, globalParametersCalculations):
  
  instaTBF   = ['instaTBF'+str(i)  for i in range(1, nbFramesTakenIntoAccount + 1)]
  instaAmp   = ['instaAmp'+str(i)  for i in range(1, nbFramesTakenIntoAccount + 1)]
  instaAsym  = ['instaAsym'+str(i) for i in range(1, nbFramesTakenIntoAccount + 1)]
  tailAngles = ['tailAngles'+str(i) for i in range(1, nbFramesTakenIntoAccount + 1)]
  
  instaSpeed       = ['instaSpeed'       + str(i) for i in range(1, nbFramesTakenIntoAccount + 1)]
  instaHeadingDiff = ['instaHeadingDiff' + str(i) for i in range(1, nbFramesTakenIntoAccount + 1)]
  instaHorizDispl  = ['instaHorizDispl'  + str(i) for i in range(1, nbFramesTakenIntoAccount + 1)]
  
  possibleColors = ['b', 'r', 'g', 'k', 'c', 'm', 'y']
  possibleColorsNames = ['blue', 'red', 'green', 'black', 'cyan', 'magenta', 'yellow']
  
  xaxis    = [0, 30]
  freqAxis = [0, 0.5]
  ampAxis  = [0, 1.6]
  asymAxis = [0, 0.8]
  angAxis  = [0, 1.5]
  
  dfParam['classification'] = classifications
  
  # if modelUsedForClustering == 'GaussianMixture':
    # for j in range(0, nbLabels):
      # probasClassJ = predictedProbas[:, sortedIndices[j]]
      # dfParam['classProba' + str(j)] = probasClassJ
  
  # Calculating proportions of each conditions in each class
  for clusterProportionsPerFish in [True, False]:
    proportions = np.zeros((nbConditions, nbCluster))
    if clusterProportionsPerFish:
      df2 = dfParam[['Trial_ID', 'Well_ID', 'Condition', 'classification']]
      for i in range(0, nbCluster):
        df2.loc[df2['classification'] == i, 'classifiedAs'+str(i)] = 1
        df2.loc[df2['classification'] != i, 'classifiedAs'+str(i)] = 0
      df2 = df2.groupby(['Trial_ID', 'Well_ID', 'Condition']).sum()
      df2['Condition'] = [elem[2] for elem in df2.index]
      df2['totalNbOfBouts'] = df2['classifiedAs0']
      if nbCluster >= 2:
        for i in range(1, nbCluster):
          df2['totalNbOfBouts'] = df2['totalNbOfBouts'] + df2['classifiedAs' + str(i)]
      df2['totalNbOfBouts'] = df2['totalNbOfBouts'].replace(0, 1)
      for i in range(0, nbCluster):
        df2['classifiedAs' + str(i)] = df2['classifiedAs' + str(i)] / df2['totalNbOfBouts']
      
      df2.to_excel(os.path.join(outputFolderResult, 'clusterProportionsPerAnimal.xlsx'))
      
      for idxCond, cond in enumerate(np.unique(dfParam['Condition'].values)):
        for classed in range(0, len(proportions[0])):
          proportions[idxCond, classed] = np.median(df2.loc[df2['Condition'] == cond]['classifiedAs' + str(classed)])
      
      fig, tabAx = plt.subplots(1, len(proportions[0]), figsize=(22.9, 8.8))
      for classed in range(0, len(proportions[0])):
        b = sns.boxplot(ax=tabAx[int(classed)], data=df2, x='Condition', y='classifiedAs' + str(classed), showmeans=1, showfliers=1)
        c = sns.stripplot(ax=tabAx[int(classed)], data=df2, x='Condition', y='classifiedAs' + str(classed), color='red', size=7)
        b.set_ylabel('', fontsize=0)
        b.set_xlabel('', fontsize=0)
        b.axes.set_title('Cluster ' + str(classed), fontsize=30)
      plt.savefig(os.path.join(outputFolderResult, 'clustersProportionsPerFish.png'))
      
    else:
      
      df2 = dfParam[['Condition','classification']]
      for idxCond, cond in enumerate(np.unique(dfParam['Condition'].values)):
        for classed in range(0, len(proportions[0])):
          proportions[idxCond, classed] = len(df2.loc[(df2['Condition'] == cond) & (df2['classification'] == classed)])
      for i in range(0, nbConditions):
        proportions[i, :] = proportions[i, :] / sum(proportions[i, :])
    
    if clusterProportionsPerFish:
      outF = open(os.path.join(outputFolderResult, 'proportionsPerFish.txt'), "w")
    else:
      outF = open(os.path.join(outputFolderResult, 'proportionsPerBout.txt'), "w")
    
    labelX = ""
    for i in range(0, nbCluster):
      labelX = labelX + "Cluster " + str(i+1) + " : \n"
      for j, cond in enumerate(np.unique(dfParam['Condition'].values)):
        labelX = labelX + str(cond) + ": " + str(round(proportions[j,i]*100*100)/100) + "%, "
        labelX = labelX + "\n"
      labelX = labelX + "\n"
    outF.write(labelX)
    outF.write("\n")
    outF.close()
  
  # Plotting each cluster one by one
  
  mostRepresentativeBout = np.zeros((nbConditions,nbCluster))
  
  fig, tabAx = plt.subplots(4, len(proportions[0]), figsize=(22.9, 8.8))
  
  for idxCond, cond in enumerate(np.unique(dfParam['Condition'].values)):
    for classed in range(0, len(proportions[0])):
      dfTemp = dfParam.loc[(dfParam['Condition'] == cond) & (dfParam['classification'] == classed)]
      instaTBFtab   = dfTemp[instaTBF]
      instaAmptab   = dfTemp[instaAmp]
      instaAsymtab  = dfTemp[instaAsym]
      tailAnglestab = dfTemp[tailAngles]
      color = possibleColors[idxCond]
      if nbCluster == 1:
        tabAx[0].plot(instaTBFtab.median().values,  color, label=cond)
        tabAx[1].plot(instaAmptab.median().values,  color)
        tabAx[2].plot(instaAsymtab.median().values, color)
        tabAx[3].plot(tailAnglestab.median().values, color)
      else:
        tabAx[0, classed].plot(instaTBFtab.median().values,  color, label=cond)
        tabAx[1, classed].plot(instaAmptab.median().values,  color)
        tabAx[2, classed].plot(instaAsymtab.median().values, color)
        tabAx[3, classed].plot(tailAnglestab.median().values, color)
      
      instaTBFmedian  = instaTBFtab.median().values
      instaAmpmedian  = instaAmptab.median().values
      instaAsymmedian = instaAsymtab.median().values
      
      dist = abs(instaTBFtab-instaTBFmedian).sum(axis=1)/abs(instaTBFmedian).sum() + abs(instaAmptab-instaAmpmedian).sum(axis=1)/abs(instaAmpmedian).sum() + abs(instaAsymtab-instaAsymmedian).sum(axis=1)/abs(instaAsymmedian).sum()
      
      # if modelUsedForClustering == 'GaussianMixture':
        # dist = 1 - dfTemp['classProba' + str(classed)]
        
      if len(dist):
        idMinDist = dist.idxmin()
      else:
        idMinDist = -1
      mostRepresentativeBout[idxCond, classed] = idMinDist
  
  if scaleGraphs:
    for classed in range(0, len(proportions[0])):
      if nbCluster == 1:
        tabAx[0].scatter(xaxis, freqAxis, None, 'w')
        tabAx[1].scatter(xaxis, ampAxis, None, 'w')
        tabAx[2].scatter(xaxis, asymAxis, None, 'w')
        tabAx[3].scatter(xaxis, angAxis, None, 'w')    
      else:
        tabAx[0, classed].scatter(xaxis, freqAxis, None, 'w')
        tabAx[1, classed].scatter(xaxis, ampAxis, None, 'w')
        tabAx[2, classed].scatter(xaxis, asymAxis, None, 'w')
        tabAx[3, classed].scatter(xaxis, angAxis, None, 'w')
  if nbCluster == 1:
    tabAx[0].legend()
    tabAx[0].set_ylabel('Avg Insta Frequency')
    tabAx[1].set_ylabel('Avg Insta Amplitude')
    tabAx[2].set_ylabel('Avg Insta Asymetry')
    tabAx[3].set_ylabel('Avg Angle')  
  else:
    tabAx[0, 0].legend()
    tabAx[0, 0].set_ylabel('Avg Insta Frequency')
    tabAx[1, 0].set_ylabel('Avg Insta Amplitude')
    tabAx[2, 0].set_ylabel('Avg Insta Asymetry')
    tabAx[3, 0].set_ylabel('Avg Angle')
  for i in range(0, nbCluster):
    labelX = "Cluster " + str(i+1) + "\n"
    for j, condName in enumerate(np.unique(dfParam['Condition'].values)):
      labelX = labelX + str(condName) + ": " + str(round(proportions[j,i]*100*100)/100) + "% (in " + possibleColorsNames[j] + ")\n"
    if nbCluster == 1:
      tabAx[3].set_xlabel(labelX)
    else:
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
        if nbCluster == 1:
          tabAx2[0].plot(instaTBFtab.values,  color)
          tabAx2[1].plot(instaAmptab.values,  color)
          tabAx2[2].plot(instaAsymtab.values, color)
          tabAx2[3].plot(tailAnglestab.values, color)
        else:
          tabAx2[0, classed].plot(instaTBFtab.values,  color)
          tabAx2[1, classed].plot(instaAmptab.values,  color)
          tabAx2[2, classed].plot(instaAsymtab.values, color)
          tabAx2[3, classed].plot(tailAnglestab.values, color)
  if scaleGraphs:
    for classed in range(0, len(proportions[0])):
      if nbCluster == 1:
        tabAx2[0].scatter(xaxis, freqAxis, None, 'w')
        tabAx2[1].scatter(xaxis, ampAxis, None, 'w')
        tabAx2[2].scatter(xaxis, asymAxis, None, 'w')
        tabAx2[3].scatter(xaxis, angAxis, None, 'w')      
      else:
        tabAx2[0, classed].scatter(xaxis, freqAxis, None, 'w')
        tabAx2[1, classed].scatter(xaxis, ampAxis, None, 'w')
        tabAx2[2, classed].scatter(xaxis, asymAxis, None, 'w')
        tabAx2[3, classed].scatter(xaxis, angAxis, None, 'w')
  if nbCluster == 1:
    tabAx2[0].set_ylabel('Avg Insta Frequency')
    tabAx2[1].set_ylabel('Avg Insta Amplitude')
    tabAx2[2].set_ylabel('Avg Insta Asymetry')
    tabAx2[3].set_ylabel('Avg Angle')  
  else:
    tabAx2[0, 0].set_ylabel('Avg Insta Frequency')
    tabAx2[1, 0].set_ylabel('Avg Insta Amplitude')
    tabAx2[2, 0].set_ylabel('Avg Insta Asymetry')
    tabAx2[3, 0].set_ylabel('Avg Angle')
  for i in range(0, nbCluster):
    labelX = "Most representative bout of cluster "+ str(i+1) + ":\n"
    for j, condName in enumerate(np.unique(dfParam['Condition'].values)):
      labelX = labelX + "for " + str(condName) + " (in " + possibleColorsNames[j] + ")\n"
    if nbCluster == 1:
      tabAx2[3].set_xlabel(labelX)
    else:
      tabAx2[3, i].set_xlabel(labelX)
  plt.savefig(os.path.join(outputFolderResult, 'mostRepresentativeBoutForEachClusterAndCondition.png'))
  if showFigures:
    plt.show()

  # Getting most representative sorted bouts
  sortedRepresentativeBouts = []
  sortedRepresentativeBoutsSpeed = []
  sortedRepresentativeBoutsHeadingDiff = []
  sortedRepresentativeBoutsIndex = []
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
    # if modelUsedForClustering == 'GaussianMixture':
      # dist = 1 - dfTemp['classProba' + str(classed)]
    
    if tailAngles[0] in dfParam.columns:
      sortedRepresentativeBouts.append(dfParam.loc[dist.index.values[dist.values.argsort()], tailAngles])
    if instaSpeed[0] in dfParam.columns:
      sortedRepresentativeBoutsSpeed.append(dfParam.loc[dist.index.values[dist.values.argsort()], instaSpeed])
    if instaHeadingDiff[0] in dfParam.columns:
      sortedRepresentativeBoutsHeadingDiff.append(dfParam.loc[dist.index.values[dist.values.argsort()], instaHeadingDiff])
    sortedRepresentativeBoutsIndex.append(dist.index.values[dist.values.argsort()])
  
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
      if nbCluster == 1:
        tabAx3.plot(tailAnglestab, color)
      else:
        tabAx3[classed].plot(tailAnglestab, color)
  for i in range(0,len(proportions[0])):
    if nbCluster == 1:
      tabAx3.set_ylabel('Cluster '+str(i+1))
    else:
      tabAx3[i].set_ylabel('Cluster '+str(i+1))
  if nbCluster == 1:
    tabAx3.set_xlabel("Tail angle over time for the\n"+str(nbOfMostRepresentativeBoutsToPlot)+' most representative bouts for each cluster')
  else:
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
      if nbCluster == 1:
        tabAx3.plot(tailAnglestab, color)
      else:
        tabAx3[classed].plot(tailAnglestab, color)
      
  for i in range(0,len(proportions[0])):
    if nbCluster == 1:
      tabAx3.set_ylabel('Cluster '+str(i+1))
    else:
      tabAx3[i].set_ylabel('Cluster '+str(i+1))
  if nbCluster == 1:
    tabAx3.set_xlabel("Tail angle over time for the most representative bouts for each cluster")
  else:
    tabAx3[len(proportions[0])-1].set_xlabel("Tail angle over time for the most representative bouts for each cluster")
  plt.savefig(os.path.join(outputFolderResult, 'mostRepresentativeBoutsForEachCluster.png'))
  if showFigures:
    plt.show()
  
  
  # Plot most representative bouts: Speed
  if len(sortedRepresentativeBoutsSpeed):
    nbOfMostRepresentativeBoutsToPlot = 10000000000000
    for classed in range(0, len(proportions[0])):
      nb = len(sortedRepresentativeBoutsSpeed[classed].index)
      if nb < nbOfMostRepresentativeBoutsToPlot:
        nbOfMostRepresentativeBoutsToPlot = nb
    if nbOfMostRepresentativeBoutsToPlot > 10:
      nbOfMostRepresentativeBoutsToPlot = 10
    fig, tabAx3 = plt.subplots(len(proportions[0]),1, figsize=(22.9, 8.8))
    for classed in range(0, len(proportions[0])):
      indices = sortedRepresentativeBoutsSpeed[classed].index
      for j in range(0, nbOfMostRepresentativeBoutsToPlot):
        tailAnglestab = sortedRepresentativeBoutsSpeed[classed].loc[indices[j]].values
        color = 'b'
        if nbCluster == 1:
          tabAx3.plot(tailAnglestab, color)
        else:
          tabAx3[classed].plot(tailAnglestab, color)
    for i in range(0,len(proportions[0])):
      if nbCluster == 1:
        tabAx3.set_ylabel('Cluster '+str(i+1))
      else:
        tabAx3[i].set_ylabel('Cluster '+str(i+1))
    if nbCluster == 1:
      tabAx3.set_xlabel("Tail angle over time for the\n"+str(nbOfMostRepresentativeBoutsToPlot)+' most representative bouts for each cluster')
    else:
      tabAx3[len(proportions[0])-1].set_xlabel("Tail angle over time for the\n"+str(nbOfMostRepresentativeBoutsToPlot)+' most representative bouts for each cluster')
    plt.savefig(os.path.join(outputFolderResult, str(nbOfMostRepresentativeBoutsToPlot) + 'mostRepresentativeBoutsForEachClusterSpeed.png'))
    if showFigures:
      plt.show()
  

  # Plot most representative bouts: Heading diff
  if len(sortedRepresentativeBoutsHeadingDiff):
    nbOfMostRepresentativeBoutsToPlot = 10000000000000
    for classed in range(0, len(proportions[0])):
      nb = len(sortedRepresentativeBoutsHeadingDiff[classed].index)
      if nb < nbOfMostRepresentativeBoutsToPlot:
        nbOfMostRepresentativeBoutsToPlot = nb
    if nbOfMostRepresentativeBoutsToPlot > 10:
      nbOfMostRepresentativeBoutsToPlot = 10
    fig, tabAx3 = plt.subplots(len(proportions[0]),1, figsize=(22.9, 8.8))
    for classed in range(0, len(proportions[0])):
      indices = sortedRepresentativeBoutsHeadingDiff[classed].index
      for j in range(0, nbOfMostRepresentativeBoutsToPlot):
        tailAnglestab = sortedRepresentativeBoutsHeadingDiff[classed].loc[indices[j]].values
        color = 'b'
        if nbCluster == 1:
          tabAx3.plot(tailAnglestab, color)
        else:
          tabAx3[classed].plot(tailAnglestab, color)
    for i in range(0,len(proportions[0])):
      if nbCluster == 1:
        tabAx3.set_ylabel('Cluster '+str(i+1))
      else:
        tabAx3[i].set_ylabel('Cluster '+str(i+1))
    if nbCluster == 1:
      tabAx3.set_xlabel("Tail angle over time for the\n"+str(nbOfMostRepresentativeBoutsToPlot)+' most representative bouts for each cluster')
    else:
      tabAx3[len(proportions[0])-1].set_xlabel("Tail angle over time for the\n"+str(nbOfMostRepresentativeBoutsToPlot)+' most representative bouts for each cluster')
    plt.savefig(os.path.join(outputFolderResult, str(nbOfMostRepresentativeBoutsToPlot) + 'mostRepresentativeBoutsForEachClusterHeadingDiff.png'))
    if showFigures:
      plt.show()
  
  
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
        NumBout   = dfParam.loc[indices[num],'NumBout']
        out = outputValidationVideo(pathToVideos, Trial_ID, '.txt', Well_ID, NumBout, 1, BoutStart, BoutEnd, out, length, analyzeAllWellsAtTheSameTime, ZZoutputLocation)
      
      out.release()
  
  # Looking into global parameters
  if globalParametersCalculations:
    
    for plotOutliersAndMean in [0, 1]:
      globParam1 = ['Bout Duration (s)', 'Bout Distance (mm)', 'Bout Speed (mm/s)', 'Number of Oscillations', 'meanTBF', 'maxTailAngleAmplitude']
      globParam2 = ['Max TBF (Hz)', 'Mean TBF (Hz)', 'medianOfInstantaneousTBF', 'Max absolute TBA (deg.)', 'Mean absolute TBA (deg.)', 'Median absolute TBA (deg.)']
      globParam3 = ['Absolute Yaw (deg)', 'TBA#1 timing (deg)', 'TBA#1 Amplitude (deg)', 'IBI (s)', 'xmean', 'ymean']
      globParam4 = ['binaryClass25degMaxTailAngle', 'BoutFrameNumberStart', 'tailAngleSymmetry', 'secondBendAmpDividedByFirst']
      
      for idxGlobParam, globParam in enumerate([globParam1, globParam2, globParam3, globParam4]):
        fig, tabAx = plt.subplots(2, 3, figsize=(22.9, 8.8))
        for idx, parameter in enumerate(globParam):
          concatenatedValues = []
          for boutCategory in range(0, nbCluster):
            indices = sortedRepresentativeBouts[boutCategory].index
            values  = dfParam.loc[indices[:],parameter].values
            concatenatedValues.append(values)
          tabAx[int(idx/3), idx%3].set_title(parameter)
          tabAx[int(idx/3), idx%3].boxplot(concatenatedValues, showmeans=1, showfliers=plotOutliersAndMean)
        globParamFileName = 'globalParametersforEachCluster' + str(idxGlobParam) + '.png' if plotOutliersAndMean else 'globalParametersforEachCluster_NoOutliers_' + str(idxGlobParam) + '.png'
        plt.savefig(os.path.join(outputFolderResult, globParamFileName))
        if showFigures:
          plt.plot()
          plt.show()
    
    ###
    
    globParam1 = ['Bout Duration (s)', 'Bout Distance (mm)', 'Bout Speed (mm/s)', 'Number of Oscillations', 'meanTBF', 'maxTailAngleAmplitude']
    globParam2 = ['Max TBF (Hz)', 'Mean TBF (Hz)', 'medianOfInstantaneousTBF', 'Max absolute TBA (deg.)', 'Mean absolute TBA (deg.)', 'Median absolute TBA (deg.)']
    globParam3 = ['Absolute Yaw (deg)', 'TBA#1 timing (deg)', 'TBA#1 Amplitude (deg)', 'IBI (s)', 'xmean', 'ymean']
    globParam4 = ['binaryClass25degMaxTailAngle', 'BoutFrameNumberStart', 'tailAngleSymmetry', 'secondBendAmpDividedByFirst']
    
    for calculateKinematicParametersPerFish in [True, False]:
    
      if calculateKinematicParametersPerFish:
        globParamTot = globParam1 + globParam2 + globParam3 + globParam4
        dfKinematicInsideCluster = dfParam[['Trial_ID', 'Well_ID', 'classification', 'Condition'] + globParamTot].astype({col: 'float' for col in globParamTot}).groupby(['Trial_ID', 'Well_ID', 'classification', 'Condition']).median()
        dfKinematicInsideCluster['classification'] = [elem[2] for elem in dfKinematicInsideCluster.index]
        dfKinematicInsideCluster['Condition']      = [elem[3] for elem in dfKinematicInsideCluster.index]
      else:
        dfKinematicInsideCluster = dfParam
      
      for idxGlobParam, globParam in enumerate([globParam1, globParam2, globParam3, globParam4]):
        fig, tabAx = plt.subplots(2, 3, figsize=(22.9, 8.8))
        fig.tight_layout(pad=3.0)
        for idx, parameter in enumerate(globParam):
          b = sns.boxplot(ax=tabAx[int(idx/3), idx%3], data=dfKinematicInsideCluster, x="classification", y=parameter, hue="Condition", showfliers = False)
          b.set_ylabel('', fontsize=0)
          b.set_xlabel('', fontsize=0)
          b.axes.set_title(parameter,fontsize=30)
        globParamFileName = 'globalParametersforEachCluster_Conditions_NoOutliers_' + str(idxGlobParam)
        if calculateKinematicParametersPerFish:
          globParamFileName = globParamFileName + '_PerFish.png'
        else:
          globParamFileName = globParamFileName + '_PerBout.png'
        plt.savefig(os.path.join(outputFolderResult, globParamFileName))
        if showFigures:
          plt.plot()
          plt.show()
  
  
  # Saves classifications
  if 'classProba0' in dfParam.columns.tolist():
    dfParam[['Trial_ID','Well_ID','NumBout','Condition', 'Genotype', 'classification'] + ['classProba' + str(j) for j in range(0, nbCluster)]].to_csv(os.path.join(outputFolderResult, 'classifications.txt'))
  else:
    dfParam[['Trial_ID','Well_ID','NumBout','Condition', 'Genotype', 'classification']].to_csv(os.path.join(outputFolderResult, 'classifications.txt'))
  
  
  # Plotting mostToLeastRepresentativeBoutsForEachCluster figure
  
  optimalLength = 12
  
  fig, tabAx3 = plt.subplots(3, len(proportions[0]), figsize=(22.9, 8.8))
  for classed in range(0, len(proportions[0])):
    indices = sortedRepresentativeBouts[classed].index
    for j in range(0, 3):
      ind2size = optimalLength if len(indices) >= 3*optimalLength else max(1, int(len(indices) / 3))
      if j == 0:
        indices2 = indices[0:ind2size]
      elif j == 1:
        indices2 = indices[int(len(indices)/2) - int(ind2size/2) : int(len(indices)/2) + int(ind2size/2)]
      else:
        indices2 = indices[len(indices) - ind2size : len(indices)]
      for k in range(0, len(indices2)):
        tailAnglestab = sortedRepresentativeBouts[classed].loc[indices2[k]].values
        color = 'b'
        if nbCluster == 1:
          tabAx3[j].plot(tailAnglestab, color)
        else:
          tabAx3[j, classed].plot(tailAnglestab, color)
  for i in range(0, len(proportions[0])):
    if nbCluster == 1:
      tabAx3[2].set_xlabel("Bouts of cluster 1")
    else:
      tabAx3[2, i].set_xlabel("Bouts of cluster " + str(i + 1))
  if nbCluster == 1:
    tabAx3[0].set_ylabel("Most representative bouts")
    tabAx3[1].set_ylabel("In between")
    tabAx3[2].set_ylabel("Least representative bouts")
  else:
    tabAx3[0, 0].set_ylabel("Most representative bouts")
    tabAx3[1, 0].set_ylabel("In between")
    tabAx3[2, 0].set_ylabel("Least representative bouts")
  plt.savefig(os.path.join(outputFolderResult, 'mostToLeastRepresentativeBoutsForEachCluster.png'))
  
  # Plotting bouts one by one for each cluster and writing bout indices in txt file
  if False:
    outF = open(os.path.join(outputFolderResult, 'boutIndices.txt'), "w")
    for classed in range(0, len(proportions[0])):
      indices = sortedRepresentativeBouts[classed].index
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
        plt.savefig(os.path.join(outputFolderResult, 'cluster' + str(classed + 1) + '_' + region + '.png'))

  return [proportions, sortedRepresentativeBouts, sortedRepresentativeBoutsIndex]