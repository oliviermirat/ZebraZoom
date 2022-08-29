import shutil

import zebrazoom.code.paths as paths
from zebrazoom.dataAnalysis.datasetcreation.createDataFrame import createDataFrame
from zebrazoom.dataAnalysis.dataanalysis.populationComparaison import populationComparaison
from zebrazoom.dataAnalysis.postProcessingFromCommandLine.postProcessingFromCommandLine import calculateNumberOfSfsVsTurnsBasedOnMaxAmplitudeThreshold
from zebrazoom.dataAnalysis.datasetcreation.generatePklDataFileForVideo import generatePklDataFileForVideo
import os

def kinematicParametersAnalysis(sys, addMedianPerGenotype=0, checkConsistencyOfParameters=False):
  
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
  
  forcePandasDfRecreation                   = int(sys.argv[11]) if len(sys.argv) >= 12 else 0
  
  nameWithExt = os.path.split(pathToExcelFile)[1]

  dataframeOptions = {
    'pathToExcelFile'                   : os.path.split(pathToExcelFile)[0],
    'fileExtension'                     : os.path.splitext(nameWithExt)[1],
    'resFolder'                         : os.path.join(paths.getDataAnalysisFolder(), 'data'),
    'nameOfFile'                        : os.path.splitext(nameWithExt)[0],
    'smoothingFactorDynaParam'          : 0,
    'nbFramesTakenIntoAccount'          : 0,
    'numberOfBendsIncludedForMaxDetect' : -1,
    'minNbBendForBoutDetect'            : minNbBendForBoutDetect,
    'keepSpeedDistDurWhenLowNbBends'    : keep,
    'defaultZZoutputFolderPath'         : paths.getDefaultZZoutputFolder(),
    'computeTailAngleParamForCluster'   : False,
    'computeMassCenterParamForCluster'  : False,
    'frameStepForDistanceCalculation'   : str(frameStepForDistanceCalculation),
    'tailAngleKinematicParameterCalculation'    : tailAngleKinematicParameterCalculation,
    'saveRawDataInAllBoutsSuperStructure'       : saveRawDataInAllBoutsSuperStructure,
    'saveAllBoutsSuperStructuresInMatlabFormat' : saveAllBoutsSuperStructuresInMatlabFormat
  }
  
  generatePklDataFileForVideo(os.path.join(os.path.split(pathToExcelFile)[0], nameWithExt), paths.getDefaultZZoutputFolder(), frameStepForDistanceCalculation, forcePandasDfRecreation)
  
  [conditions, genotypes, nbFramesTakenIntoAccount, globParam] = createDataFrame(dataframeOptions, '', forcePandasDfRecreation, [])

  outputFolder = os.path.join(paths.getDataAnalysisFolder(), 'resultsKinematic')
  resultFolder = os.path.join(outputFolder, dataframeOptions['nameOfFile'])
  if os.path.exists(resultFolder):
    shutil.rmtree(resultFolder)  # if the result folder exists, remove it manually, since populationComparaison only removes it if plotOutliersAndMean argument is True

  outliersRemoved = minNbBendForBoutDetect
  # Mixing up all the bouts
  if not outliersRemoved:  # check if outliers are already removed from results
    populationComparaison(dataframeOptions['nameOfFile'], dataframeOptions['resFolder'], globParam, conditions, genotypes, outputFolder, 0, True, 0, 0, int(checkConsistencyOfParameters))
  
  if not(checkConsistencyOfParameters):
    populationComparaison(dataframeOptions['nameOfFile'], dataframeOptions['resFolder'], globParam, conditions, genotypes, outputFolder, 0, False, 0, 0, int(checkConsistencyOfParameters))
  
  # Median per well for each kinematic parameter
  if not outliersRemoved:  # check if outliers are already removed from results
    populationComparaison(dataframeOptions['nameOfFile'], dataframeOptions['resFolder'], globParam, conditions, genotypes, outputFolder, 1, True, 0, 0, int(checkConsistencyOfParameters))
  
  if not(checkConsistencyOfParameters):
    populationComparaison(dataframeOptions['nameOfFile'], dataframeOptions['resFolder'], globParam, conditions, genotypes, outputFolder, 1, False, 0, 0, int(checkConsistencyOfParameters))
  
  # Median per genotype for each kinematic parameter
  if addMedianPerGenotype:
    populationComparaison(dataframeOptions['nameOfFile'], dataframeOptions['resFolder'], globParam, conditions, genotypes, outputFolder, 0, True, 0, 1, int(checkConsistencyOfParameters))
    
    if not(checkConsistencyOfParameters):
      populationComparaison(dataframeOptions['nameOfFile'], dataframeOptions['resFolder'], globParam, conditions, genotypes, outputFolder, 0, False, 0, 1, int(checkConsistencyOfParameters))
  
  if angleThreshSFSvsTurns != -1:
    calculateNumberOfSfsVsTurnsBasedOnMaxAmplitudeThreshold(paths.getRootDataFolder(), dataframeOptions['nameOfFile'], angleThreshSFSvsTurns)
  
  print("")
  print("")
  print("The data has been saved in the folder:", resultFolder)
  print("The raw data has also been saved in:", dataframeOptions['resFolder'])
