import zebrazoom.code.paths as paths
from zebrazoom.dataAnalysis.datasetcreation.createDataFrame import createDataFrame
from zebrazoom.dataAnalysis.dataanalysis.populationComparaison import populationComparaison
from zebrazoom.dataAnalysis.postProcessingFromCommandLine.postProcessingFromCommandLine import calculateNumberOfSfsVsTurnsBasedOnMaxAmplitudeThreshold
from zebrazoom.dataAnalysis.datasetcreation.generatePklDataFileForVideo import generatePklDataFileForVideo
import os

def kinematicParametersAnalysisCenterOfMassOnlyNoBoutsDetection(sys):
  
  pathToExcelFile                           = sys.argv[3]
  saveRawDataInAllBoutsSuperStructure       = int(sys.argv[4]) if len(sys.argv) > 4 else 0
  saveAllBoutsSuperStructuresInMatlabFormat = int(sys.argv[5]) if len(sys.argv) > 5 else 0
  forcePandasDfRecreation                   = int(sys.argv[6]) if len(sys.argv) > 6 else 0
  ZZoutputLocation                          =     sys.argv[7]  if len(sys.argv) > 7 else ""
  frameStepForDistanceCalculation           = int(sys.argv[8]) if len(sys.argv) > 8 else 4
  minimumFrameToFrameDistanceToBeConsideredAsMoving = float(sys.argv[9]) if len(sys.argv) > 9 else 1
  
  addMedianPerGenotype = 0

  nameWithExt = os.path.split(pathToExcelFile)[1]
  
  dataframeOptions = {
    'pathToExcelFile'                   : os.path.split(pathToExcelFile)[0],
    'fileExtension'                     : os.path.splitext(nameWithExt)[1],
    'resFolder'                         : os.path.join(paths.getDataAnalysisFolder(), 'data'),
    'nameOfFile'                        : os.path.splitext(nameWithExt)[0],
    'smoothingFactorDynaParam'          : 0,
    'nbFramesTakenIntoAccount'          : 28,
    'numberOfBendsIncludedForMaxDetect' : -1,
    'minNbBendForBoutDetect'            : 0,
    'keepSpeedDistDurWhenLowNbBends'    : 1,
    'defaultZZoutputFolderPath'         : paths.getDefaultZZoutputFolder() if ZZoutputLocation == "" else ZZoutputLocation,
    'computeTailAngleParamForCluster'   : False,
    'computeMassCenterParamForCluster'  : False,
    'frameStepForDistanceCalculation'   : str(frameStepForDistanceCalculation),
    'tailAngleKinematicParameterCalculation'    : 0,
    'saveRawDataInAllBoutsSuperStructure'       : saveRawDataInAllBoutsSuperStructure,
    'saveAllBoutsSuperStructuresInMatlabFormat' : saveAllBoutsSuperStructuresInMatlabFormat,
    'minimumFrameToFrameDistanceToBeConsideredAsMoving' : minimumFrameToFrameDistanceToBeConsideredAsMoving
  }
  
  # The line below should be added again in the future !!!
  # generatePklDataFileForVideo(os.path.join(os.path.split(pathToExcelFile)[0], nameWithExt), os.path.join(cur_dir_path, 'ZZoutput') if ZZoutputLocation == "" else ZZoutputLocation, frameStepForDistanceCalculation)
  
  [conditions, genotypes, nbFramesTakenIntoAccount, globParam] = createDataFrame(dataframeOptions, '', forcePandasDfRecreation, ['percentOfMovingFramesBasedOnDistance'], minimumFrameToFrameDistanceToBeConsideredAsMoving)
  
  # Mixing up all the bouts
  populationComparaison(dataframeOptions['nameOfFile'], dataframeOptions['resFolder'], globParam, conditions, genotypes, os.path.join(paths.getDataAnalysisFolder(), 'resultsKinematic'), 0, True)
  
  populationComparaison(dataframeOptions['nameOfFile'], dataframeOptions['resFolder'], globParam, conditions, genotypes, os.path.join(paths.getDataAnalysisFolder(), 'resultsKinematic'), 0, False)
  
  # Median per well for each kinematic parameter
  populationComparaison(dataframeOptions['nameOfFile'], dataframeOptions['resFolder'], globParam, conditions, genotypes, os.path.join(paths.getDataAnalysisFolder(), 'resultsKinematic'), 1, True)
  
  populationComparaison(dataframeOptions['nameOfFile'], dataframeOptions['resFolder'], globParam, conditions, genotypes, os.path.join(paths.getDataAnalysisFolder(), 'resultsKinematic'), 1, False)
  
  # Median per genotype for each kinematic parameter
  if addMedianPerGenotype:
    populationComparaison(dataframeOptions['nameOfFile'], dataframeOptions['resFolder'], globParam, conditions, genotypes, os.path.join(paths.getDataAnalysisFolder(), 'resultsKinematic'), 0, True, 0, 1)
    
    populationComparaison(dataframeOptions['nameOfFile'], dataframeOptions['resFolder'], globParam, conditions, genotypes, os.path.join(paths.getDataAnalysisFolder(), 'resultsKinematic'), 0, False, 0, 1)
  
  print("")
  print("")
  print("The data has been saved in the folder:", os.path.join(paths.getDataAnalysisFolder(), 'resultsKinematic', dataframeOptions['nameOfFile']))
  print("The raw data has also been saved in:", dataframeOptions['resFolder'])
