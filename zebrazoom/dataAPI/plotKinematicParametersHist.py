from zebrazoom.code.dataPostProcessing.createPandasDataFrameOfParameters import createPandasDataFrameOfParameters
from zebrazoom.code.getHyperparameters import getHyperparametersSimple

from ._createSuperStructFromH5 import createSuperStructFromH5
from ._openResultsFile import openResultsFile

import matplotlib.pyplot as plt
import numpy as np
import math

def remove_outliers(data, threshold=3):
  mean_value = sum(data) / len(data)
  std_dev = (sum((x - mean_value) ** 2 for x in data) / len(data)) ** 0.5
  # Define a range beyond which values are considered outliers
  lower_bound = mean_value - threshold * std_dev
  upper_bound = mean_value + threshold * std_dev
  # Filter out values outside the defined range
  filtered_data = [x for x in data if lower_bound <= x <= upper_bound]
  return filtered_data


def plotKinematicParametersHist(videoName: str, kinematicParameterName: str, outlierRemoval=False) -> dict:
  
  parameter = []
  with openResultsFile(videoName, 'r+') as results:
    for numWell in range(len(results['wellPositions'])):
      for numAnimal in range(len(results['dataForWell' + str(numWell)])):
        animalPath = f'dataForWell{numWell}/dataForAnimal{numAnimal}'
        if animalPath not in results:
          raise ValueError(f"data for animal {numAnimal} in well {numWell} doesn't exist")
        animalGroup = results[animalPath]
        dataset = animalGroup['kinematicParametersPerBout']
        numberOfBouts, = dataset.shape
        for numBout in range(numberOfBouts):
          parameter.append(dataset[kinematicParameterName][numBout])
  
  if outlierRemoval:
    plt.hist(remove_outliers(parameter), bins=50)
    hist, edges = np.histogram([x for x in parameter if not math.isnan(x)], bins=50)
  else:
    plt.hist(parameter, bins=50)
    hist, edges = np.histogram([x for x in parameter if not math.isnan(x)], bins=50)
  
  max_bin_index = np.argmax(hist)
  max_bin_range = (edges[max_bin_index], edges[max_bin_index + 1])
  print(kinematicParameterName, "; Max bin range:", max_bin_range)
  # print("Median:", np.median([x for x in parameter if not math.isnan(x)]))
  # print("Mean:", np.mean([x for x in parameter if not math.isnan(x)]))
  
  plt.title(kinematicParameterName)
  plt.show()
  
  return parameter, max_bin_range
  