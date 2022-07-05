from zebrazoom.code.dataPostProcessing.generateAllTimeTailAngleGraph import generateAllTimeTailAngleGraph
from zebrazoom.code.dataPostProcessing.perBoutOutput import perBoutOutput
from zebrazoom.code.dataPostProcessing.computeEyesHeadingPlot import computeEyesHeadingPlot
from zebrazoom.code.dataPostProcessing.tailAnglesHeatmap import tailAnglesHeatMap
from zebrazoom.code.dataPostProcessing.createPandasDataFrameOfParameters import createPandasDataFrameOfParameters

def dataPostProcessing(outputFolderVideo, superStruct, hyperparameters, videoName, videoExtension):

  if hyperparameters["generateAllTimeTailAngleGraph"]:
    generateAllTimeTailAngleGraph(outputFolderVideo, superStruct, hyperparameters["generateAllTimeTailAngleGraphLineWidth"])  
  
  if hyperparameters["perBoutOutput"]:
    superStruct = perBoutOutput(superStruct, hyperparameters, videoName)
  
  if hyperparameters["computeEyesHeadingPlot"]:
    computeEyesHeadingPlot(superStruct, hyperparameters, videoName)

  if hyperparameters["tailAnglesHeatMap"]:
    tailAnglesHeatMap(superStruct, hyperparameters, videoName)
  
  if hyperparameters["createPandasDataFrameOfParameters"] and hyperparameters["videoFPS"] and hyperparameters["videoPixelSize"]:
    createPandasDataFrameOfParameters(hyperparameters, videoName, videoExtension, hyperparameters["outputFolder"], superStruct)
  
  return superStruct