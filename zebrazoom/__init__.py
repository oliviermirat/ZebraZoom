import os

from zebrazoom.extractZZParametersFromTailAngle import extractZZParametersFromTailAngle
from zebrazoom.dataAnalysis.datasetcreation.createDataFrame import createDataFrame
from zebrazoom.dataAnalysis.dataanalysis.populationComparaison import populationComparaison
from zebrazoom.dataAnalysis.dataanalysis.applyClustering import applyClustering


with open(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'version.txt'), 'r') as f:
  __version__ = f.read().strip()
