import os
import math
import shutil
import matplotlib.pyplot as plt
import pickle
import numpy as np
import pandas as pd
import json
import seaborn as sns

def populationComparaison(nameOfFile, resFolder, globParam, conditions, genotypes, outputFolder, medianPerWellFirstForEachKinematicParameter = 0, plotOutliersAndMean = True, saveDataPlottedInJson = 0, medianPerGenotypeFirstForEachKinematicParameter=0, numberOfBoutsPerSecond=0):

  outputFolderResult = os.path.join(outputFolder, nameOfFile)
  if not(os.path.exists(outputFolderResult)):
    os.mkdir(outputFolderResult)
    
  if medianPerWellFirstForEachKinematicParameter:
    outputFolderResult = os.path.join(outputFolderResult, 'medianPerWellFirst')
  else:
    if medianPerGenotypeFirstForEachKinematicParameter:
      outputFolderResult = os.path.join(outputFolderResult, 'medianPerGenotypeFirst')
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
    outputFolderCharts = outputFolderResult
  else:
    outputFolderCharts = os.path.join(outputFolderResult, 'noMeanAndOutliersPlotted')
    os.makedirs(outputFolderCharts)
  
  dataPlotted = {}
  
  if os.path.exists(os.path.join(resFolder, nameOfFile + '.pkl')):
    infile = open(os.path.join(resFolder, nameOfFile + '.pkl'),'rb')
  else:
    infile = open(os.path.join(resFolder, nameOfFile),'rb') # This is just to insure compatibility with previous versions, should remove this line in the future
  dfParam = pickle.load(infile)
  infile.close()
  
  columnsForRawDataExport = ['Trial_ID', 'Well_ID', 'NumBout', 'BoutStart', 'BoutEnd', 'Condition', 'Genotype', 'videoDuration'] + globParam
  
  if medianPerWellFirstForEachKinematicParameter:
    dfKinematicValues = dfParam[columnsForRawDataExport]
    dfKinematicValues = dfKinematicValues.astype({param: float for param in globParam + ['videoDuration']})
    dfKinematicValues = dfKinematicValues.groupby(['Trial_ID', 'Well_ID']).median()
    dfCondGeno = dfParam[['Trial_ID', 'Well_ID', 'Condition', 'Genotype']]
    dfCondGeno = dfCondGeno.groupby(['Trial_ID', 'Well_ID']).first()
    dfCount = dfParam[['Trial_ID', 'Well_ID']].copy()
    dfCount['Bout Counts'] = dfParam['Bout Duration (s)']
    dfCount = dfCount.groupby(['Trial_ID', 'Well_ID']).count()
    dfCount['Bout Rate (bouts / s)'] = dfCount['Bout Counts'] / dfKinematicValues['videoDuration']
    dfTotalTimeMove = dfParam[['Trial_ID', 'Well_ID', 'Bout Duration (s)']].copy()
    dfTotalTimeMove = dfTotalTimeMove.groupby(['Trial_ID', 'Well_ID']).sum()
    dfKinematicValues['percentTimeSpentSwimming'] = (dfTotalTimeMove['Bout Duration (s)'] / dfKinematicValues['videoDuration']) * 100
    dfParam = pd.concat([dfCondGeno, dfKinematicValues], axis=1)
    dfParam = pd.concat([dfParam, dfCount], axis=1)
    globParam = globParam + ['percentTimeSpentSwimming', 'Bout Counts', 'Bout Rate (bouts / s)']
  elif medianPerGenotypeFirstForEachKinematicParameter:
    dfKinematicValues = dfParam[columnsForRawDataExport]
    dfKinematicValues = dfKinematicValues.astype({param: float for param in globParam})
    dfKinematicValues = dfKinematicValues.groupby(['Genotype', 'Well_ID']).median()
    dfCond = dfParam[['Genotype', 'Well_ID', 'Condition']]
    dfCond = dfCond.groupby(['Genotype', 'Well_ID']).first()
    dfCount = dfParam[['Genotype', 'Well_ID']].copy()
    dfCount['Bout Counts'] = [0 for i in range(len(dfCount['Genotype']))]
    dfCount = dfCount.groupby(['Genotype', 'Well_ID']).count()
    dfCount['Bout Rate (bouts / s)'] = dfCount['Bout Counts'] / dfKinematicValues['videoDuration']
    dfTotalTimeMove = dfParam[['Trial_ID', 'Well_ID', 'Bout Duration (s)']].copy()
    dfTotalTimeMove = dfTotalTimeMove.groupby(['Trial_ID', 'Well_ID']).sum()
    dfKinematicValues['percentTimeSpentSwimming'] = (dfTotalTimeMove['Bout Duration (s)'] / dfKinematicValues['videoDuration']) * 100
    dfParam = pd.concat([dfCond, dfKinematicValues], axis=1)
    dfParam = pd.concat([dfParam, dfCount], axis=1)
    globParam = globParam + ['percentTimeSpentSwimming', 'Bout Counts', 'Bout Rate (bouts / s)']
  else:
    dfParam  = dfParam[columnsForRawDataExport]
  
  if not os.path.exists(os.path.join(outputFolderResult, 'globalParametersInsideCategories.xlsx')):
    dfParam.to_excel(os.path.join(outputFolderResult, 'globalParametersInsideCategories.xlsx'))
    dfParam.to_csv(os.path.join(outputFolderResult, 'globalParametersInsideCategories.csv'), index=False)
  
  nbGraphs = int(len(globParam)/6) if len(globParam) % 6 == 0 else int(len(globParam)/6) + 1
  color = ['b', 'r', 'c', 'm', 'y', 'k']
  for i in range(nbGraphs):
    globParamForPlot = [globParam[elem] for elem in range(6*i, min(6*(i+1), len(globParam)))]
    nbLines   = int(math.sqrt(len(globParamForPlot)))
    nbColumns = math.ceil(len(globParamForPlot) / nbLines)
    fig, tabAx = plt.subplots(nbLines, nbColumns, figsize=(22.9, 8.8))
    fig.tight_layout(pad=4.0)
    for idx, parameter in enumerate(globParamForPlot):
      print("plotting parameter:", parameter)
      
      if True and not(medianPerGenotypeFirstForEachKinematicParameter):
        
        tabToPlot = 0
        if nbLines == 1:
          if nbColumns == 1:
            tabToPlot = tabAx
          else:
            tabToPlot = tabAx[idx%nbColumns]
        else:
          tabToPlot = tabAx[int(idx/nbColumns), idx%nbColumns]
        
        b = sns.boxplot(ax=tabToPlot, data=dfParam, x="Condition", y=parameter, hue="Genotype", showmeans=plotOutliersAndMean, showfliers=plotOutliersAndMean)
        # if plotOutliersAndMean and (medianPerWellFirstForEachKinematicParameter or medianPerGenotypeFirstForEachKinematicParameter): # or len(concatenatedValues[0]) < 100):
          # sns.stripplot(ax=tabToPlot, data=dfParam, x="Condition", y=parameter, hue="Genotype", color=".25")
        b.set_ylabel('', fontsize=0)
        b.set_xlabel('', fontsize=0)
        b.axes.set_title(parameter,fontsize=20)
        
      # else: # Old Method (TO REMOVE!!!), and for the medianPerGenotypeFirstForEachKinematicParameter option
      
        # concatenatedValues = []
        # labels = []
        # if not(medianPerGenotypeFirstForEachKinematicParameter):
          # for condition in conditions:
            # for genotype in genotypes:
              # indicesCondition = dfParam.index[dfParam['Condition'] == condition].tolist()
              # indicesGenotype  = dfParam.index[dfParam['Genotype']  == genotype].tolist()
              # indices = [ind for ind in indicesCondition if ind in indicesGenotype]
              # values  = dfParam.loc[indices, parameter].values
              # concatenatedValues.append(values)
              # labels.append(str(condition) + '\n' + str(genotype))
        # else:
          # for condition in conditions:
            # indicesCondition = dfParam.index[dfParam['Condition'] == condition].tolist()
            # values  = dfParam.loc[indicesCondition, parameter].values
            # concatenatedValues.append(values)
            # labels.append(str(condition))
        
        # concatenatedValuesWithoutNans = []
        # for toConcat in concatenatedValues:
          # concatenatedValuesWithoutNans.append(np.array([x for x in toConcat if not(math.isnan(x))]))
        # concatenatedValues = concatenatedValuesWithoutNans
        
        # if saveDataPlottedInJson:
          # dataPlotted[parameter] = {}
          # for idx2, label in enumerate(labels):
            # dataPlotted[parameter][label] = concatenatedValues[idx2].tolist()
        
        # if nbLines == 1:
          # if nbColumns == 1:
            # tabAx.set_title(parameter)
            # tabAx.boxplot(concatenatedValues, showmeans=plotOutliersAndMean, showfliers=plotOutliersAndMean)
            # if plotOutliersAndMean and (medianPerWellFirstForEachKinematicParameter or medianPerGenotypeFirstForEachKinematicParameter or len(concatenatedValues[0]) < 100):
              # for idx2, values in enumerate(concatenatedValues):
                # tabAx.plot(np.random.normal(idx2+1, 0.005*len(concatenatedValues), size=len(values)), values, 'b.', alpha=0.3, c=color[idx2] if idx2 < len(color) else 'b')
            # tabAx.set_xticklabels(labels)
          # else:
            # tabAx[idx%nbColumns].set_title(parameter)
            # tabAx[idx%nbColumns].boxplot(concatenatedValues, showmeans=plotOutliersAndMean, showfliers=plotOutliersAndMean)
            # if plotOutliersAndMean and (medianPerWellFirstForEachKinematicParameter or medianPerGenotypeFirstForEachKinematicParameter or len(concatenatedValues[0]) < 100):
              # for idx2, values in enumerate(concatenatedValues):
                # tabAx[idx%nbColumns].plot(np.random.normal(idx2+1, 0.005*len(concatenatedValues), size=len(values)), values, 'b.', alpha=0.3, c=color[idx2] if idx2 < len(color) else 'b')
            # tabAx[idx%nbColumns].set_xticklabels(labels)
        # else:
          # tabAx[int(idx/nbColumns), idx%nbColumns].set_title(parameter)
          # tabAx[int(idx/nbColumns), idx%nbColumns].boxplot(concatenatedValues, showmeans=plotOutliersAndMean, showfliers=plotOutliersAndMean)
          # if plotOutliersAndMean and (medianPerWellFirstForEachKinematicParameter or medianPerGenotypeFirstForEachKinematicParameter or len(concatenatedValues[0]) < 100):
            # for idx2, values in enumerate(concatenatedValues):
              # tabAx[int(idx/nbColumns), idx%nbColumns].plot(np.random.normal(idx2+1, 0.005*len(concatenatedValues), size=len(values)), values, 'b.', alpha=0.3, c=color[idx2] if idx2 < len(color) else 'b')
          # tabAx[int(idx/nbColumns), idx%nbColumns].set_xticklabels(labels)
    
    plt.savefig(os.path.join(outputFolderCharts, 'globalParametersInsideCategories_' + str(i+1) + '.png'))
    plt.close(fig)
  
  if saveDataPlottedInJson:
    outputFile = open(os.path.join(outputFolderCharts, 'dataPlotted.txt'), 'w')
    outputFile.write(json.dumps(dataPlotted))
    outputFile.close()
  return globParam, dfParam
