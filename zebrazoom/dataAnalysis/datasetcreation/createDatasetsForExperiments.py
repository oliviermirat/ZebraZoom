from createDataFrame import createDataFrame

dataframeOptions = {
  'pathToExcelFile'          : './experimentOrganizationExcel/',
  'fileExtension'            : '.xls',
  'resFolder'                : './data/',
  'nameOfFile'               : 'ctrlVsHomogenousPh',
  'smoothingFactorDynaParam' : 0,   # 0.001
  'nbFramesTakenIntoAccount' : 28
}

#####

dataframeOptions['nameOfFile'] = 'ctrlVsHomogenousPh'
dataframeOptions['nameOfFile'] = 'paramecia'
dataframeOptions['nameOfFile'] = 'pHCtrlVsParameciaCtrl'
dataframeOptions['nameOfFile'] = 'parameciaCtrlVsParameciaCtrl'
dataframeOptions['nameOfFile'] = 'parameciaSimple'

createDataFrame(pathToExcelFile, nameOfFile, fileExtension, smoothingFactorDynaParam, nbFramesTakenIntoAccount, resFolder)

#####

dataframeOptions['nameOfFile'] = 'ctrlVsSharpPh'
createDataFrame(pathToExcelFile, nameOfFile, fileExtension, smoothingFactorDynaParam, nbFramesTakenIntoAccount, resFolder)

dataframeOptions['nameOfFile'] = 'allCatamaran'
createDataFrame(pathToExcelFile, nameOfFile, fileExtension, smoothingFactorDynaParam, nbFramesTakenIntoAccount, resFolder)
