import zebrazoom.code.paths as paths
from zebrazoom.dataAnalysis.datasetcreation.createDataFrame import createDataFrame
import pandas as pd
import os

def createPandasDataFrameOfParameters(hyperparameters, videoName, videoExtension, ZZoutputLocation='', supstructOverwrite={}):
  
  print("Creating pandas dataframe of parameters")
  
  nbWells = hyperparameters["nbWells"]
    
  excelFileDataFrame = pd.DataFrame(data=[["defaultZZoutputFolder", videoName, hyperparameters["videoFPS"], hyperparameters["videoPixelSize"], str([1 for i in range(nbWells)]), str([1 for i in range(nbWells)]), str([1 for i in range(nbWells)])]], columns=['path', 'trial_id', 'fq', 'pixelsize', 'condition', 'genotype', 'include'])
  
  if hyperparameters["frameStepForDistanceCalculation"] and hyperparameters["frameStepForDistanceCalculation"] != -1:
    frameStepForDistanceCalculation = int(hyperparameters["frameStepForDistanceCalculation"])
  else:
    frameStepForDistanceCalculation = 4 #int(hyperparameters["videoFPS"] / 100) * 4 if int(hyperparameters["videoFPS"]) >= 100 else 2
  
  print("Parameter: frameStepForDistanceCalculation:", frameStepForDistanceCalculation)
  
  if len(ZZoutputLocation) == 0:
    cur_dir_path = paths.getDefaultZZoutputFolder()
  else:
    cur_dir_path = ZZoutputLocation

  dataframeOptions = {
    'pathToExcelFile'                   : "",
    'fileExtension'                     : videoExtension,
    'resFolder'                         : os.path.join(cur_dir_path, videoName),
    'nameOfFile'                        : videoName,
    'smoothingFactorDynaParam'          : 0,
    'nbFramesTakenIntoAccount'          : -2, ## nbFramesTakenIntoAccount will be 100 minimum
    'numberOfBendsIncludedForMaxDetect' : -1,
    'minNbBendForBoutDetect'            : -1,
    'keepSpeedDistDurWhenLowNbBends'    : 1,
    'defaultZZoutputFolderPath'         : cur_dir_path,
    'getTailAngleSignMultNormalized'    : 1,
    'computeTailAngleParamForCluster'   : True,
    'computeMassCenterParamForCluster'  : True,
    'frameStepForDistanceCalculation'   : str(frameStepForDistanceCalculation),
    'tailAngleKinematicParameterCalculation'    : 1,
    'saveRawDataInAllBoutsSuperStructure'       : 1,
    'saveAllBoutsSuperStructuresInMatlabFormat' : 0
  }
  
  # forcePandasDfRecreation (third parameter) is set to True here
  [conditions, genotypes, nbFramesTakenIntoAccount, globParam] = createDataFrame(dataframeOptions, excelFileDataFrame, 1, [], 0, supstructOverwrite)
  