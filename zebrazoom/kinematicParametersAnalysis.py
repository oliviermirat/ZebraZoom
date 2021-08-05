from zebrazoom.dataAnalysis.datasetcreation.createDataFrame import createDataFrame
from zebrazoom.dataAnalysis.dataanalysis.populationComparaison import populationComparaison
from zebrazoom.dataAnalysis.postProcessingFromCommandLine.postProcessingFromCommandLine import calculateNumberOfSfsVsTurnsBasedOnMaxAmplitudeThreshold
import os
from pathlib import Path

def kinematicParametersAnalysis(sys):

  pathToExcelFile                 = sys.argv[3]
  frameStepForDistanceCalculation = int(sys.argv[4])

  if len(sys.argv) >= 7:
    minNbBendForBoutDetect = int(sys.argv[5])
    keep                   = int(sys.argv[6])
  else:
    minNbBendForBoutDetect = -1
    keep                   = -1

  if len(sys.argv) >= 8:
    angleThreshSFSvsTurns  = int(sys.argv[7])
  else:
    angleThreshSFSvsTurns  = -1

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
    'frameStepForDistanceCalculation'   : frameStepForDistanceCalculation
  }

  [conditions, genotypes, nbFramesTakenIntoAccount] = createDataFrame(dataframeOptions)

  if minNbBendForBoutDetect != -1:
    globParam = ['BoutDuration', 'TotalDistance', 'Speed', 'NumberOfOscillations', 'meanTBF', 'maxAmplitude', 'IBI']
  else:
    globParam = ['BoutDuration', 'TotalDistance', 'Speed']

  populationComparaison(dataframeOptions['nameOfFile'], dataframeOptions['resFolder'], globParam, conditions, genotypes, os.path.join(cur_dir_path, os.path.join('dataAnalysis', 'resultsKinematic')), 1)

  if angleThreshSFSvsTurns != -1:
    calculateNumberOfSfsVsTurnsBasedOnMaxAmplitudeThreshold(cur_dir_path, dataframeOptions['nameOfFile'], angleThreshSFSvsTurns)

  print("The data has been saved in folder:", os.path.join(os.path.join(cur_dir_path, os.path.join('dataAnalysis', 'resultsKinematic')), dataframeOptions['nameOfFile']))
  print("Pickle data has also been saved in:", dataframeOptions['resFolder'])