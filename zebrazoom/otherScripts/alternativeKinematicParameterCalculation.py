import matplotlib.pyplot as plt
import pandas as pd
import numpy as np
import json
import os

def alternativeKinematicParameterCalculation(args):

  if os.path.exists(os.path.join('zebrazoom/dataAnalysis/experimentOrganizationExcel', args.nameOfExperiment + '.xls')):
    excelOrganizationFilePath = os.path.join('zebrazoom/dataAnalysis/experimentOrganizationExcel', args.nameOfExperiment + '.xls')
  elif os.path.exists(os.path.join('zebrazoom/dataAnalysis/experimentOrganizationExcel', args.nameOfExperiment + '.xlsx')):
    excelOrganizationFilePath = os.path.join('zebrazoom/dataAnalysis/experimentOrganizationExcel', args.nameOfExperiment + '.xlsx')
  else:
    print("Excel organization file not found, is its extension .xls or .xlsx?")
    return
  
  excelOrganizationFile = pd.read_excel(excelOrganizationFilePath)

  allGenotypes  = []
  allConditions = []
  for videoId in range(len(excelOrganizationFile)):
    path      = excelOrganizationFile.loc[videoId]['path']
    trial_id  = excelOrganizationFile.loc[videoId]['trial_id']
    fq        = excelOrganizationFile.loc[videoId]['fq']
    pixelsize = excelOrganizationFile.loc[videoId]['pixelsize']
    genotype  = [gen.replace("'", "").replace('"', "").replace(' ', "") for gen in excelOrganizationFile.loc[videoId]['genotype'][1:-1].split(",")]
    condition = [cond.replace("'", "").replace('"', "").replace(' ', "") for cond in excelOrganizationFile.loc[videoId]['condition'][1:-1].split(",")]
    include   = [int(incl) for incl in excelOrganizationFile.loc[videoId]['include'][1:-1].split(",")]
    allGenotypes.append(genotype)
    allConditions.append(condition)
    if len(include) != len(condition) or len(include) != len(genotype) or len(genotype) != len(condition):
      print("inconsistent include, condition, genotype!!!")
      print(len(include), len(condition), len(genotype))
      return
  allGenotypes  = np.unique(allGenotypes).tolist()
  allConditions = np.unique(allConditions).tolist()

  GenXCondDictAllBouts  = {}
  GenXCondDictPerAnimal = {}
  for gen in allGenotypes:
    GenXCondDictAllBouts[gen] = {}
    GenXCondDictPerAnimal[gen] = {}
    for cond in allConditions:
      GenXCondDictAllBouts[gen][cond] = []
      GenXCondDictPerAnimal[gen][cond] = []
  
  for videoId in range(len(excelOrganizationFile)):
    path      = excelOrganizationFile.loc[videoId]['path']
    trial_id  = excelOrganizationFile.loc[videoId]['trial_id']
    fq        = excelOrganizationFile.loc[videoId]['fq']
    pixelsize = excelOrganizationFile.loc[videoId]['pixelsize']
    genotype  = [gen.replace("'", "").replace('"', "").replace(' ', "") for gen in excelOrganizationFile.loc[videoId]['genotype'][1:-1].split(",")]
    condition = [cond.replace("'", "").replace('"', "").replace(' ', "") for cond in excelOrganizationFile.loc[videoId]['condition'][1:-1].split(",")]
    include   = [int(incl) for incl in excelOrganizationFile.loc[videoId]['include'][1:-1].split(",")]
    pathToResultFile = os.path.join(os.path.join('zebrazoom/ZZoutput', trial_id), 'results_' + trial_id + '.txt') if path == "defaultZZoutputFolder" else os.path.join(path, 'results_' + trial_id + '.txt')
    with open(pathToResultFile) as f:
      supstruct = json.load(f)
      for numWell in range(0, len(supstruct['wellPoissMouv'])):
        if include[numWell]:
          for numAnimal in range(0, len(supstruct['wellPoissMouv'][numWell])):
            perAnimal = []
            for numBout in range(0, len(supstruct['wellPoissMouv'][numWell][numAnimal])):
              gen  = genotype[numWell]
              cond = condition[numWell]
              bout = supstruct['wellPoissMouv'][numWell][numAnimal][numBout]
              BoutStart  = bout['BoutStart']
              BoutEnd    = bout['BoutEnd']
              BoutLength = (BoutEnd - BoutStart + 1) / fq
              GenXCondDictAllBouts[gen][cond].append(BoutLength)
              perAnimal.append(BoutLength)
            GenXCondDictPerAnimal[gen][cond].append(perAnimal)
  
  if 'WT' in allGenotypes:
    allGenotypes.remove('WT')
    allGenotypes.insert(0, 'WT')
  
  # All bouts combined plot
  
  allLabels = []
  allData   = [] 
  for cond in allConditions:
    for gen in allGenotypes:
      allLabels.append(gen + '_' + cond)
      allData.append(GenXCondDictAllBouts[gen][cond])
  
  fig, ax = plt.subplots()
  bp = ax.boxplot(allData)
  ax.set_xticklabels(allLabels)
  ax.set_ylabel('Duration')
  ax.set_title('All bouts combined')
  plt.show()
  
  # Median per fish plot
  
  allLabels = []
  allData   = [] 
  for cond in allConditions:
    for gen in allGenotypes:
      allLabels.append(gen + '_' + cond)
      allData.append([np.median(arr) for arr in GenXCondDictPerAnimal[gen][cond]])
  
  fig, ax = plt.subplots()
  bp = ax.boxplot(allData)
  ax.set_xticklabels(allLabels)
  ax.set_ylabel('Duration')
  ax.set_title('Median per fish')
  plt.show()  
