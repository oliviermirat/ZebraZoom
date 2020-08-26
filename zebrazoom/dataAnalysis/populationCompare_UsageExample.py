import sys
sys.path.insert(1, './datasetcreation/')
sys.path.insert(1, './dataanalysis/')
from createDataFrame import createDataFrame
from populationComparaison import populationComparaison

# Creating the dataframe

dataframeOptions = {
  'pathToExcelFile'                   : './experimentOrganizationExcel/',
  'fileExtension'                     : '.xls',
  'resFolder'                         : './data/',
  'nameOfFile'                        : 'example',
  'smoothingFactorDynaParam'          : 0,   # 0.001
  'nbFramesTakenIntoAccount'          : 28,
  'numberOfBendsIncludedForMaxDetect' : -1,
  'minNbBendForBoutDetect'            : 3,
  'computeTailAngleParamForCluster'   : False,
  'computeMassCenterParamForCluster'  : False
}

[conditions, genotypes] = createDataFrame(dataframeOptions)


# Plotting for the different conditions
nameOfFile = dataframeOptions['nameOfFile']
resFolder  = dataframeOptions['resFolder']
globParam = ['BoutDuration', 'TotalDistance', 'Speed', 'NumberOfOscillations', 'meanTBF', 'maxAmplitude']

populationComparaison(nameOfFile, resFolder, globParam, conditions, genotypes)

