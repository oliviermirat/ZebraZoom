import os
import math
import shutil
import matplotlib.pyplot as plt
import pickle

def populationComparaison(nameOfFile, resFolder, globParam, conditions, genotypes):

  if os.path.exists('resultsKinematic/'+nameOfFile):
    shutil.rmtree('resultsKinematic/'+nameOfFile)
  os.mkdir('resultsKinematic/'+nameOfFile)

  infile = open(resFolder + nameOfFile,'rb')
  dfParam = pickle.load(infile)
  infile.close()
  
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
    tabAx[int(idx/3), idx%3].set_title(parameter)
    tabAx[int(idx/3), idx%3].boxplot(concatenatedValues)
    tabAx[int(idx/3), idx%3].set_xticklabels(labels)  
  plt.savefig('resultsKinematic/'+nameOfFile+'/globalParametersInsideCategories.png')
