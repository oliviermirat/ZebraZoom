import zebrazoom

# Creating the dataframe

dataframeOptions = {
  'pathToExcelFile'                   : '../zebrazoom/dataanalysis/experimentOrganizationExcel/',
  'fileExtension'                     : '.xls',
  'resFolder'                         : '../zebrazoom/dataanalysis/data',
  'nameOfFile'                        : 'example',
  'smoothingFactorDynaParam'          : 0,   # 0.001
  'nbFramesTakenIntoAccount'          : 28,
  'numberOfBendsIncludedForMaxDetect' : -1,
  'minNbBendForBoutDetect'            : 3,
  'defaultZZoutputFolderPath'         : '../zebrazoom/ZZoutput/',
  'computeTailAngleParamForCluster'   : False,
  'computeMassCenterParamForCluster'  : False
}

[conditions, genotypes, nbFramesTakenIntoAccount, globParam] = zebrazoom.createDataFrame(dataframeOptions)


# Plotting for the different conditions
nameOfFile = dataframeOptions['nameOfFile']
resFolder  = dataframeOptions['resFolder']
globParam = ['BoutDuration', 'TotalDistance', 'Speed', 'NumberOfOscillations', 'meanTBF', 'maxAmplitude']

zebrazoom.populationComparaison(nameOfFile, resFolder, globParam, conditions, genotypes, '../zebrazoom/dataanalysis/resultsKinematic')
