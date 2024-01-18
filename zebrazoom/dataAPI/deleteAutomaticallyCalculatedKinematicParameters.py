import numpy as np

from ._openResultsFile import openResultsFile


def deleteAutomaticallyCalculatedKinematicParameters(videoName: str):
  
  with openResultsFile(videoName, 'a') as results:

    for j in range(len(results["dataForWell0"])):
      del results["dataForWell0/dataForAnimal" + str(j) + "/kinematicParametersPerBout/"]
      for i in range(len(results["dataForWell0/dataForAnimal" + str(j) + "/listOfBouts/"].keys())):
        del results["dataForWell0/dataForAnimal" + str(j) + "/listOfBouts/bout" + str(i) + "/additionalKinematicParametersPerBout/"]
  