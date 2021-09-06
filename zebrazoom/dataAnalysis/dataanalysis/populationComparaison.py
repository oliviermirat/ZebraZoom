import os
import math
import shutil
import matplotlib.pyplot as plt
import pickle
import numpy as np
import pandas as pd
import json

def populationComparaison(nameOfFile, resFolder, globParam, conditions, genotypes, outputFolder, medianPerWellFirstForEachKinematicParameter = 0, plotOutliersAndMean = True, saveDataPlottedInJson = 0):

  outputFolderResult = os.path.join(outputFolder, nameOfFile)
  if not(os.path.exists(outputFolderResult)):
    os.mkdir(outputFolderResult)
    
  if medianPerWellFirstForEachKinematicParameter:
    outputFolderResult = os.path.join(outputFolderResult, 'medianPerWellFirst')
  else:
    outputFolderResult = os.path.join(outputFolderResult, 'allBoutsMixed')
  
  if plotOutliersAndMean: # This is a little bit of a hack because the creation of folders relies on the order in which the populationComparaison function is called (relative to the plotOutliersAndMean parameter)
    if os.path.exists(outputFolderResult): 
      shutil.rmtree(outputFolderResult)
    while True:
      try:
        os.mkdir(outputFolderResult)
        break
      except:
        print("waiting to create folder:", outputFolderResult)
  else:
    outputFolderResult = os.path.join(outputFolderResult, 'noMeanAndOutliersPlotted')
    os.mkdir(outputFolderResult)
  
  dataPlotted = {}
  
  if os.path.exists(os.path.join(resFolder, nameOfFile + '.pkl')):
    infile = open(os.path.join(resFolder, nameOfFile + '.pkl'),'rb')
  else:
    infile = open(os.path.join(resFolder, nameOfFile),'rb') # This is just to insure compatibility with previous versions, should remove this line in the future
  dfParam = pickle.load(infile)
  infile.close()
  
  columnsForRawDataExport = ['Trial_ID', 'Well_ID', 'NumBout', 'BoutStart', 'BoutEnd', 'Condition', 'Genotype'] + globParam
  
  if medianPerWellFirstForEachKinematicParameter:
    dfKinematicValues = dfParam[columnsForRawDataExport]
    dfKinematicValues = dfKinematicValues.astype({param: float for param in globParam})
    dfKinematicValues = dfKinematicValues.groupby(['Trial_ID', 'Well_ID']).median()
    dfCondGeno = dfParam[['Trial_ID', 'Well_ID', 'Condition', 'Genotype']]
    dfCondGeno = dfCondGeno.groupby(['Trial_ID', 'Well_ID']).first()
    dfCount = dfParam[['Trial_ID', 'Well_ID']].copy()
    dfCount['numberOfBouts_NoBoutsRemovedBasedOnBends'] = [0 for i in range(len(dfCount['Trial_ID']))]
    dfCount = dfCount.groupby(['Trial_ID', 'Well_ID']).count()
    dfParam = pd.concat([dfCondGeno, dfKinematicValues], axis=1)
    dfParam = pd.concat([dfParam, dfCount], axis=1)
    globParam = globParam + ['numberOfBouts_NoBoutsRemovedBasedOnBends']
  else:
    dfParam  = dfParam[columnsForRawDataExport]
  
  if plotOutliersAndMean:
    dfParam.to_excel(os.path.join(outputFolderResult, 'globalParametersInsideCategories.xlsx'))
  
  nbGraphs = int(len(globParam)/6) if len(globParam) % 6 == 0 else int(len(globParam)/6) + 1
  color = ['b', 'r', 'c', 'm', 'y', 'k']
  for i in range(nbGraphs):
    globParamForPlot = [globParam[elem] for elem in range(6*i, min(6*(i+1), len(globParam)))]
    nbLines   = int(math.sqrt(len(globParamForPlot)))
    nbColumns = math.ceil(len(globParamForPlot) / nbLines)
    fig, tabAx = plt.subplots(nbLines, nbColumns, figsize=(22.9, 8.8))
    for idx, parameter in enumerate(globParamForPlot):
      print("plotting parameter:", parameter)
      concatenatedValues = []
      labels = []
      for condition in conditions:
        for genotype in genotypes:
          indicesCondition = dfParam.index[dfParam['Condition'] == condition].tolist()
          indicesGenotype  = dfParam.index[dfParam['Genotype']  == genotype].tolist()
          indices = [ind for ind in indicesCondition if ind in indicesGenotype]
          values  = dfParam.loc[indices, parameter].values
          concatenatedValues.append(values)
          labels.append(str(condition) + '\n' + str(genotype))
      
      concatenatedValuesWithoutNans = []
      for toConcat in concatenatedValues:
        concatenatedValuesWithoutNans.append(np.array([x for x in toConcat if not(math.isnan(x))]))
      concatenatedValues = concatenatedValuesWithoutNans
      
      if saveDataPlottedInJson:
        dataPlotted[parameter] = {}
        for idx2, label in enumerate(labels):
          dataPlotted[parameter][label] = concatenatedValues[idx2].tolist()
      
      if nbLines == 1:
        if nbColumns == 1:
          tabAx.set_title(parameter)
          tabAx.boxplot(concatenatedValues, showmeans=plotOutliersAndMean, showfliers=plotOutliersAndMean)
          if plotOutliersAndMean and (medianPerWellFirstForEachKinematicParameter or len(concatenatedValues[0]) < 100):
            for idx2, values in enumerate(concatenatedValues):
              tabAx.plot(np.random.normal(idx2+1, 0.005*len(concatenatedValues), size=len(values)), values, 'b.', alpha=0.3, c=color[idx2] if idx2 < len(color) else 'b')
          tabAx.set_xticklabels(labels)
        else:
          tabAx[idx%nbColumns].set_title(parameter)
          tabAx[idx%nbColumns].boxplot(concatenatedValues, showmeans=plotOutliersAndMean, showfliers=plotOutliersAndMean)
          if plotOutliersAndMean and (medianPerWellFirstForEachKinematicParameter or len(concatenatedValues[0]) < 100):
            for idx2, values in enumerate(concatenatedValues):
              tabAx[idx%nbColumns].plot(np.random.normal(idx2+1, 0.005*len(concatenatedValues), size=len(values)), values, 'b.', alpha=0.3, c=color[idx2] if idx2 < len(color) else 'b')
          tabAx[idx%nbColumns].set_xticklabels(labels)
      else:
        tabAx[int(idx/nbColumns), idx%nbColumns].set_title(parameter)
        tabAx[int(idx/nbColumns), idx%nbColumns].boxplot(concatenatedValues, showmeans=plotOutliersAndMean, showfliers=plotOutliersAndMean)
        if plotOutliersAndMean and (medianPerWellFirstForEachKinematicParameter or len(concatenatedValues[0]) < 100):
          for idx2, values in enumerate(concatenatedValues):
            tabAx[int(idx/nbColumns), idx%nbColumns].plot(np.random.normal(idx2+1, 0.005*len(concatenatedValues), size=len(values)), values, 'b.', alpha=0.3, c=color[idx2] if idx2 < len(color) else 'b')
        tabAx[int(idx/nbColumns), idx%nbColumns].set_xticklabels(labels)
    plt.savefig(os.path.join(outputFolderResult, 'globalParametersInsideCategories_' + str(i+1) + '.png'))
  
  if saveDataPlottedInJson:
    outputFile = open(os.path.join(outputFolderResult, 'dataPlotted.txt'), 'w')
    outputFile.write(json.dumps(dataPlotted))
    outputFile.close()