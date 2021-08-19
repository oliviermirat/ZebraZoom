import zebrazoom

# Creating the dataframe

dataframeOptions = {
  'pathToExcelFile'                   : './experimentOrganizationExcel/',
  'fileExtension'                     : '.xls',
  'resFolder'                         : 'data',
  'nameOfFile'                        : 'example',
  'smoothingFactorDynaParam'          : 0,   # 0.001
  'nbFramesTakenIntoAccount'          : 28,
  'numberOfBendsIncludedForMaxDetect' : -1,
  'minNbBendForBoutDetect'            : 3,
  'defaultZZoutputFolderPath'         : '../ZZoutput/',
  'computeTailAngleParamForCluster'   : False,
  'computeMassCenterParamForCluster'  : False
}

[conditions, genotypes, nbFramesTakenIntoAccount, globParam] = zebrazoom.createDataFrame(dataframeOptions)


# Plotting for the different conditions
nameOfFile = dataframeOptions['nameOfFile']
resFolder  = dataframeOptions['resFolder']
globParam = ['BoutDuration', 'TotalDistance', 'Speed', 'NumberOfOscillations', 'meanTBF', 'maxAmplitude']

zebrazoom.populationComparaison(nameOfFile, resFolder, globParam, conditions, genotypes, 'resultsKinematic')

