from zebrazoom.dataAnalysis.datasetcreation.createDataFrame import createDataFrame
from pathlib import Path
import pandas as pd
import os

def createPandasDataFrameOfParameters(hyperparameters, videoName, videoExtension, ZZoutputLocation=''):
  
  print("Creating pandas dataframe of parameters")
  
  nbWells = hyperparameters["nbWells"]
    
  excelFileDataFrame = pd.DataFrame(data=[["defaultZZoutputFolder", videoName, hyperparameters["videoFPS"], hyperparameters["videoPixelSize"], str([1 for i in range(nbWells)]), str([1 for i in range(nbWells)]), str([1 for i in range(nbWells)])]], columns=['path', 'trial_id', 'fq', 'pixelsize', 'condition', 'genotype', 'include'])
  
  if hyperparameters["frameStepForDistanceCalculation"]:
    frameStepForDistanceCalculation = int(hyperparameters["frameStepForDistanceCalculation"])
  else:
    frameStepForDistanceCalculation = int(hyperparameters["videoFPS"] / 100) * 4 if int(hyperparameters["videoFPS"]) >= 100 else 2
  
  print("Parameter: frameStepForDistanceCalculation:", frameStepForDistanceCalculation)
  
  if len(ZZoutputLocation) == 0:
    cur_dir_path = Path(os.path.dirname(os.path.realpath(__file__))).parent.parent
    cur_dir_path = os.path.join(cur_dir_path, 'ZZoutput')
  else:
    cur_dir_path = ZZoutputLocation

  dataframeOptions = {
    'pathToExcelFile'                   : "",
    'fileExtension'                     : videoExtension,
    'resFolder'                         : os.path.join(cur_dir_path, videoName),
    'nameOfFile'                        : videoName,
    'smoothingFactorDynaParam'          : 0,
    'nbFramesTakenIntoAccount'          : 28,
    'numberOfBendsIncludedForMaxDetect' : -1,
    'minNbBendForBoutDetect'            : -1,
    'keepSpeedDistDurWhenLowNbBends'    : 1,
    'defaultZZoutputFolderPath'         : cur_dir_path,
    'computeTailAngleParamForCluster'   : True,
    'computeMassCenterParamForCluster'  : True,
    'frameStepForDistanceCalculation'   : str(frameStepForDistanceCalculation),
    'tailAngleKinematicParameterCalculation'    : 1,
    'saveRawDataInAllBoutsSuperStructure'       : 1,
    'saveAllBoutsSuperStructuresInMatlabFormat' : 0
  }

  [conditions, genotypes, nbFramesTakenIntoAccount, globParam] = createDataFrame(dataframeOptions, excelFileDataFrame)
  