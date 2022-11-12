import json
import matplotlib.pyplot as plt
import cv2
import numpy as np
import math

import pandas as pd
import os
import shutil
import time
import re

def filterLatencyAndMergeBoutsInSameTrials(nameOfExperiment, minFrameNumberBoutStart, maxFrameNumberBoutStart):
  
  if os.path.exists(os.path.join('zebrazoom', os.path.join('dataAnalysis', os.path.join('resultsKinematic', nameOfExperiment + '_perFish')))):
    shutil.rmtree(os.path.join('zebrazoom', os.path.join('dataAnalysis', os.path.join('resultsKinematic', nameOfExperiment + '_perFish'))))
    time.sleep(0.1)
  
  os.mkdir(os.path.join('zebrazoom', os.path.join('dataAnalysis', os.path.join('resultsKinematic', nameOfExperiment + '_perFish'))))
  os.mkdir(os.path.join('zebrazoom', os.path.join('dataAnalysis', os.path.join('resultsKinematic', os.path.join(nameOfExperiment + '_perFish', 'allBoutsMixed')))))
  os.mkdir(os.path.join('zebrazoom', os.path.join('dataAnalysis', os.path.join('resultsKinematic', os.path.join(nameOfExperiment + '_perFish', 'medianPerWellFirst')))))
  
  data = pd.read_excel(os.path.join('zebrazoom', os.path.join('dataAnalysis', os.path.join('resultsKinematic', os.path.join(nameOfExperiment, os.path.join('allBoutsMixed', 'globalParametersInsideCategories.xlsx'))))))
  
  data = data[data['BoutStart'] >= minFrameNumberBoutStart]
  data = data[data['BoutStart'] <= maxFrameNumberBoutStart]
  data = data.reset_index()
  
  for i in range(0, len(data)):
    data.loc[i, "Trial_ID"] = re.sub(r"Trial\d+", "", data.loc[i, "Trial_ID"])
  
  data = data.groupby(['Trial_ID', 'Well_ID', 'Genotype', 'Condition']).median()
  
  del data['index'] 
  del data['Unnamed: 0']
  
  data.to_excel(os.path.join('zebrazoom', os.path.join('dataAnalysis', os.path.join('resultsKinematic', os.path.join(nameOfExperiment + '_perFish', os.path.join('allBoutsMixed', 'globalParametersInsideCategories.xlsx'))))))
  
  data.to_csv(os.path.join('zebrazoom', os.path.join('dataAnalysis', os.path.join('resultsKinematic', os.path.join(nameOfExperiment + '_perFish', os.path.join('allBoutsMixed', 'globalParametersInsideCategories.csv'))))))
  
  data.to_excel(os.path.join('zebrazoom', os.path.join('dataAnalysis', os.path.join('resultsKinematic', os.path.join(nameOfExperiment + '_perFish', os.path.join('medianPerWellFirst', 'globalParametersInsideCategories.xlsx'))))))
  
  data.to_csv(os.path.join('zebrazoom', os.path.join('dataAnalysis', os.path.join('resultsKinematic', os.path.join(nameOfExperiment + '_perFish', os.path.join('medianPerWellFirst', 'globalParametersInsideCategories.csv'))))))
