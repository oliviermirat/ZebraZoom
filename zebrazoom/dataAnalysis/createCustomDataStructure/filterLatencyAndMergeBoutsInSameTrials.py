import json
import matplotlib.pyplot as plt
import cv2
import numpy as np
import math
from pathlib import Path

import pandas as pd
import os
import shutil
import time
import re

def filterLatencyAndMergeBoutsInSameTrials(nameOfExperiment, minFrameNumberBoutStart, maxFrameNumberBoutStart, calculationMethod, pathToZZoutput, dropDuplicates=False):

  pathToRoot = Path(pathToZZoutput).parent

  dropDuplicatesExtensionName = '_duplicateRemoved' if dropDuplicates else ''
  
  if os.path.exists(os.path.join(pathToRoot, os.path.join('dataAnalysis', os.path.join('resultsKinematic', nameOfExperiment + '_perFish_' + calculationMethod + dropDuplicatesExtensionName)))):
    shutil.rmtree(os.path.join(pathToRoot, os.path.join('dataAnalysis', os.path.join('resultsKinematic', nameOfExperiment + '_perFish_' + calculationMethod + dropDuplicatesExtensionName))))
    time.sleep(0.1)
  
  os.mkdir(os.path.join(pathToRoot, os.path.join('dataAnalysis', os.path.join('resultsKinematic', nameOfExperiment + '_perFish_' + calculationMethod + dropDuplicatesExtensionName))))
  os.mkdir(os.path.join(pathToRoot, os.path.join('dataAnalysis', os.path.join('resultsKinematic', os.path.join(nameOfExperiment + '_perFish_' + calculationMethod + dropDuplicatesExtensionName, 'allBoutsMixed')))))
  os.mkdir(os.path.join(pathToRoot, os.path.join('dataAnalysis', os.path.join('resultsKinematic', os.path.join(nameOfExperiment + '_perFish_' + calculationMethod + dropDuplicatesExtensionName, 'medianPerWellFirst')))))
  
  data = pd.read_excel(os.path.join(pathToRoot, os.path.join('dataAnalysis', os.path.join('resultsKinematic', os.path.join(nameOfExperiment, os.path.join('allBoutsMixed', 'globalParametersInsideCategories.xlsx'))))))
  
  data = data[data['BoutStart'] >= minFrameNumberBoutStart]
  data = data[data['BoutStart'] <= maxFrameNumberBoutStart]
  data = data.reset_index()
  
  if dropDuplicates:
    data = data.drop_duplicates(subset=['Trial_ID', 'Well_ID', 'Genotype', 'Condition'])
    data = data.reset_index()
    del data['level_0']
  
  for i in range(0, len(data)):
    data.loc[i, "Trial_ID"] = re.sub(r"Trial\d+", "", data.loc[i, "Trial_ID"])
  
  if calculationMethod == 'median' or calculationMethod == 'mean':
    data2 = data.copy()
    data2 = data2.groupby(['Trial_ID', 'Well_ID', 'Genotype', 'Condition']).count()
    if calculationMethod == 'median':
      data = data.groupby(['Trial_ID', 'Well_ID', 'Genotype', 'Condition']).median()
    elif calculationMethod == 'mean':
      data = data.groupby(['Trial_ID', 'Well_ID', 'Genotype', 'Condition']).mean()
    del data['index']
    del data['Unnamed: 0']
    data['count'] = data2['index']
  else:
    print("No mean or median applied")
  
  data.to_excel(os.path.join(pathToRoot, os.path.join('dataAnalysis', os.path.join('resultsKinematic', os.path.join(nameOfExperiment + '_perFish_' + calculationMethod + dropDuplicatesExtensionName, os.path.join('allBoutsMixed', 'globalParametersInsideCategories.xlsx'))))))
  
  data.to_csv(os.path.join(pathToRoot, os.path.join('dataAnalysis', os.path.join('resultsKinematic', os.path.join(nameOfExperiment + '_perFish_' + calculationMethod + dropDuplicatesExtensionName, os.path.join('allBoutsMixed', 'globalParametersInsideCategories.csv'))))))
  
  data.to_excel(os.path.join(pathToRoot, os.path.join('dataAnalysis', os.path.join('resultsKinematic', os.path.join(nameOfExperiment + '_perFish_' + calculationMethod + dropDuplicatesExtensionName, os.path.join('medianPerWellFirst', 'globalParametersInsideCategories.xlsx'))))))
  
  data.to_csv(os.path.join(pathToRoot, os.path.join('dataAnalysis', os.path.join('resultsKinematic', os.path.join(nameOfExperiment + '_perFish_' + calculationMethod + dropDuplicatesExtensionName, os.path.join('medianPerWellFirst', 'globalParametersInsideCategories.csv'))))))
