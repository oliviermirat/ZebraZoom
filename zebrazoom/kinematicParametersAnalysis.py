from zebrazoom.dataAnalysis.datasetcreation.createDataFrame import createDataFrame
from zebrazoom.dataAnalysis.dataanalysis.populationComparaison import populationComparaison
from zebrazoom.dataAnalysis.postProcessingFromCommandLine.postProcessingFromCommandLine import calculateNumberOfSfsVsTurnsBasedOnMaxAmplitudeThreshold
import os
from pathlib import Path

def kinematicParametersAnalysis(sys):

  pathToExcelFile                 = sys.argv[3]
  
  frameStepForDistanceCalculation = int(sys.argv[4]) if len(sys.argv) >= 5 else 4

  if len(sys.argv) >= 7:
    minNbBendForBoutDetect = int(sys.argv[5])
    keep                   = int(sys.argv[6])
  else:
    minNbBendForBoutDetect = -1
    keep                   = 1

  angleThreshSFSvsTurns  = int(sys.argv[7]) if len(sys.argv) >= 8 else -1
  
  tailAngleKinematicParameterCalculation    = int(sys.argv[8]) if len(sys.argv) >= 9 else 1
  
  saveRawDataInAllBoutsSuperStructure       = int(sys.argv[9]) if len(sys.argv) >= 10 else 1
  
  saveAllBoutsSuperStructuresInMatlabFormat = int(sys.argv[10]) if len(sys.argv) >= 11 else 1


  cur_dir_path = os.path.dirname(os.path.realpath(__file__))
  cur_dir_path = Path(cur_dir_path)
  cur_dir_path = cur_dir_path

  nameWithExt = os.path.split(pathToExcelFile)[1]

  dataframeOptions = {
    'pathToExcelFile'                   : os.path.split(pathToExcelFile)[0],
    'fileExtension'                     : os.path.splitext(nameWithExt)[1],
    'resFolder'                         : os.path.join(cur_dir_path, os.path.join('dataAnalysis', 'data')),
    'nameOfFile'                        : os.path.splitext(nameWithExt)[0],
    'smoothingFactorDynaParam'          : 0,
    'nbFramesTakenIntoAccount'          : 28,
    'numberOfBendsIncludedForMaxDetect' : -1,
    'minNbBendForBoutDetect'            : minNbBendForBoutDetect,
    'keepSpeedDistDurWhenLowNbBends'    : keep,
    'defaultZZoutputFolderPath'         : os.path.join(cur_dir_path, 'ZZoutput'),
    'computeTailAngleParamForCluster'   : False,
    'computeMassCenterParamForCluster'  : False,
    'frameStepForDistanceCalculation'   : str(frameStepForDistanceCalculation),
    'tailAngleKinematicParameterCalculation'    : tailAngleKinematicParameterCalculation,
    'saveRawDataInAllBoutsSuperStructure'       : saveRawDataInAllBoutsSuperStructure,
    'saveAllBoutsSuperStructuresInMatlabFormat' : saveAllBoutsSuperStructuresInMatlabFormat
  }

  [conditions, genotypes, nbFramesTakenIntoAccount, globParam] = createDataFrame(dataframeOptions)
  
  # Mixing up all the bouts
  populationComparaison(dataframeOptions['nameOfFile'], dataframeOptions['resFolder'], globParam, conditions, genotypes, os.path.join(cur_dir_path, os.path.join('dataAnalysis', 'resultsKinematic')), 0)
  
  # First median per well for each kinematic parameter
  populationComparaison(dataframeOptions['nameOfFile'], dataframeOptions['resFolder'], globParam, conditions, genotypes, os.path.join(cur_dir_path, os.path.join('dataAnalysis', 'resultsKinematic')), 1)
  
  if False:
    if angleThreshSFSvsTurns != -1:
      calculateNumberOfSfsVsTurnsBasedOnMaxAmplitudeThreshold(cur_dir_path, dataframeOptions['nameOfFile'], angleThreshSFSvsTurns)
  
  print("The data has been saved in the folder:", os.path.join(os.path.join(cur_dir_path, os.path.join('dataAnalysis', 'resultsKinematic')), dataframeOptions['nameOfFile']))
  print("The raw data has also been saved in:", dataframeOptions['resFolder'])
