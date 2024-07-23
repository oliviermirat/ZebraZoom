from zebrazoom.code.createValidationVideo import calculateInfoFrameForFrame, processFrame
from zebrazoom.code.getHyperparameters import getHyperparametersSimple

from ._createSuperStructFromH5 import createSuperStructFromH5
from ._openResultsFile import openResultsFile


def plotSingleFrameTrackingPoints(videoName: str):
  with openResultsFile(videoName, 'r') as results:
    hyperparameters = getHyperparametersSimple(dict(results['configurationFileUsed'].attrs))
    superStruct = createSuperStructFromH5(results)
    colorModifTab = [{"red": 0, "green": 0, "blue": 0}]
    colorModifTab.extend([{"red": random.randrange(255), "green": random.randrange(255), "blue": random.randrange(255)} for i in range(1, hyperparameters["nbAnimalsPerWell"])])
    infoFrame = []
    for i in range(len(superStruct["wellPoissMouv"])):
      for j in range(len(superStruct["wellPoissMouv"][i])):
        # assume we only have one bout
        bout = superStruct["wellPoissMouv"][i][j][0]
        infoFrame.extend(calculateInfoFrameForFrame(superStruct, hyperparameters, i, j, 0, bout["BoutStart"], colorModifTab))
    exampleFrame = results['exampleFrame'][:]
    if hyperparameters['invertBlackWhiteOnImages']:
      exampleFrame = 255 - exampleFrame
    return processFrame(exampleFrame, hyperparameters, infoFrame, colorModifTab)
