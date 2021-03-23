from zebrazoom.code.dataPostProcessing.generateAllTimeTailAngleGraph import generateAllTimeTailAngleGraph
from zebrazoom.code.dataPostProcessing.perBoutOutput import perBoutOutput
from zebrazoom.code.dataPostProcessing.computeEyesHeadingPlot import computeEyesHeadingPlot

def dataPostProcessing(outputFolderVideo, superStruct, hyperparameters, videoName):

  if hyperparameters["generateAllTimeTailAngleGraph"]:
    generateAllTimeTailAngleGraph(outputFolderVideo, superStruct, hyperparameters["generateAllTimeTailAngleGraphLineWidth"])  
  
  if hyperparameters["perBoutOutput"]:
    perBoutOutput(superStruct, hyperparameters, videoName)
  
  if hyperparameters["computeEyesHeadingPlot"]:
    computeEyesHeadingPlot(superStruct, hyperparameters, videoName)
