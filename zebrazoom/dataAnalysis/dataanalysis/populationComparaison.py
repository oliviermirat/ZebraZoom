import os
import math
import shutil
import matplotlib.pyplot as plt
import pickle
import numpy as np

def populationComparaison(nameOfFile, resFolder, globParam, conditions, genotypes, outputFolder):

  outputFolderResult = os.path.join(outputFolder, nameOfFile)

  if os.path.exists(outputFolderResult):
    shutil.rmtree(outputFolderResult)
  os.mkdir(outputFolderResult)

  infile = open(os.path.join(resFolder, nameOfFile),'rb')
  dfParam = pickle.load(infile)
  infile.close()
  
  columnsForRawDataExport = ['index', 'Trial_ID', 'Well_ID', 'NumBout', 'BoutStart', 'BoutEnd', 'Condition', 'Genotype'] + globParam
  dfParam[columnsForRawDataExport].to_excel(os.path.join(outputFolderResult, 'globalParametersInsideCategories.xlsx'))
  
  nbLines   = int(math.sqrt(len(globParam)))
  nbColumns = math.ceil(len(globParam) / nbLines)
  fig, tabAx = plt.subplots(nbLines, nbColumns, figsize=(22.9, 8.8))
  for idx, parameter in enumerate(globParam):
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
    
    if nbLines == 1:
      tabAx[idx%nbColumns].set_title(parameter)
      tabAx[idx%nbColumns].boxplot(concatenatedValues)
      tabAx[idx%nbColumns].set_xticklabels(labels)    
    else:
      tabAx[int(idx/nbColumns), idx%nbColumns].set_title(parameter)
      tabAx[int(idx/nbColumns), idx%nbColumns].boxplot(concatenatedValues)
      tabAx[int(idx/nbColumns), idx%nbColumns].set_xticklabels(labels)
  plt.savefig(os.path.join(outputFolderResult, 'globalParametersInsideCategories.png'))
