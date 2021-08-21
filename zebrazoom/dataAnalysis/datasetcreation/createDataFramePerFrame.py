import os
import scipy.io
import pandas as pd
import json
import numpy as np
np.warnings.filterwarnings('ignore', category=np.VisibleDeprecationWarning)
from zebrazoom.dataAnalysis.datasetcreation.getDynamicParameters import getDynamicParameters
from zebrazoom.dataAnalysis.datasetcreation.getTailAngles import getTailAngles
from zebrazoom.dataAnalysis.datasetcreation.getInstaSpeed import getInstaSpeed
from zebrazoom.dataAnalysis.datasetcreation.getInstaHeadingDiff import getInstaHeadingDiff
from zebrazoom.dataAnalysis.datasetcreation.getInstaHorizontalDisplacement import getInstaHorizontalDisplacement
from zebrazoom.dataAnalysis.datasetcreation.getGlobalParameters import getGlobalParameters
from zebrazoom.dataAnalysis.datasetcreation.getTailLength  import getTailLength
from zebrazoom.dataAnalysis.datasetcreation.getTailLength2 import getTailLength2
from zebrazoom.dataAnalysis.datasetcreation.getTailAngleRecalculated import getTailAngleRecalculated
from zebrazoom.dataAnalysis.datasetcreation.getTailAngleRecalculated2 import getTailAngleRecalculated2
from zebrazoom.dataAnalysis.datasetcreation.gatherInitialRawData import gatherInitialRawData
import pickle

def createDataFramePerFrame(dataframeOptions):

  # Gathering user-inputed information about how to create the dataframe of parameters for the whole set of videos
  
  pathToExcelFile                   = dataframeOptions['pathToExcelFile']
  nameOfFile                        = dataframeOptions['nameOfFile']
  fileExtension                     = dataframeOptions['fileExtension']
  smoothingFactor                   = dataframeOptions['smoothingFactorDynaParam']
  resFolder                         = dataframeOptions['resFolder']
  numberOfBendsIncludedForMaxDetect = dataframeOptions['numberOfBendsIncludedForMaxDetect']
  minNbBendForBoutDetect            = dataframeOptions['minNbBendForBoutDetect']
  computeTailAngleParamForCluster   = dataframeOptions['computeTailAngleParamForCluster']
  computeMassCenterParamForCluster  = dataframeOptions['computeMassCenterParamForCluster']
  
  defaultZZoutputFolderPath = dataframeOptions['defaultZZoutputFolderPath'] if 'defaultZZoutputFolderPath' in dataframeOptions else ''
  
  computetailAnglesRecalculatedParamsForCluster = dataframeOptions["computetailAnglesRecalculatedParamsForCluster"] if 'computetailAnglesRecalculatedParamsForCluster' in dataframeOptions else False
  
  keepSpeedDistDurWhenLowNbBends = int(dataframeOptions['keepSpeedDistDurWhenLowNbBends']) if 'keepSpeedDistDurWhenLowNbBends' in dataframeOptions else 1
  
  frameStepForDistanceCalculation = int(dataframeOptions['frameStepForDistanceCalculation']) if ('frameStepForDistanceCalculation' in dataframeOptions) and len(dataframeOptions['frameStepForDistanceCalculation']) else 4
  
  tailAngleKinematicParameterCalculation = int(dataframeOptions['tailAngleKinematicParameterCalculation']) if 'tailAngleKinematicParameterCalculation' in dataframeOptions else 0
  
  saveRawDataInAllBoutsSuperStructure = int(dataframeOptions['saveRawDataInAllBoutsSuperStructure']) if 'saveRawDataInAllBoutsSuperStructure' in dataframeOptions else 0
  
  saveAllBoutsSuperStructuresInMatlabFormat = int(dataframeOptions['saveAllBoutsSuperStructuresInMatlabFormat']) if 'saveAllBoutsSuperStructuresInMatlabFormat' in dataframeOptions else 0
  
  getTailAngleSignMultNormalized = int(dataframeOptions['getTailAngleSignMultNormalized']) if 'getTailAngleSignMultNormalized' in dataframeOptions else 0
  
  
  excelFile = pd.read_excel(os.path.join(pathToExcelFile, nameOfFile + fileExtension))
  
  # Creating labels of columns of dataframe
  # General basic information
  basicInformation = ['numFrame', 'Trial_ID', 'Well_ID', 'NumBout', 'BoutStart', 'BoutEnd', 'Condition', 'Genotype']
  # Tail angle related parameters for clustering
  instaTBF   = ['instaTBF']
  instaAmp   = ['instaAmp']
  instaAsym  = ['instaAsym']
  tailAngles = ['tailAngles']
  # Center of mass related parameters for clustering
  instaSpeed       = ['instaSpeed']
  instaHeadingDiff = ['instaHeadingDiff']
  instaHorizDispl  = ['instaHorizDispl']
  # Assembling columns
  dfCols = basicInformation + tailAngles

  if computeTailAngleParamForCluster:
    dfCols = dfCols + instaTBF + instaAmp + instaAsym
  if computeMassCenterParamForCluster:
    dfCols = dfCols + instaSpeed + instaHeadingDiff + instaHorizDispl

  if computeTailAngleParamForCluster or computeMassCenterParamForCluster or computetailAnglesRecalculatedParamsForCluster:
    dfCols = dfCols + ['classification']
  numberOfParameters = len(dfCols)
  
  # Creating an empty dataframe then filling it with the parameters for the whole set of videos
  print("Calculating and storing all parameters:")
  dfParam = pd.DataFrame(columns=dfCols)
  genotypes  = []
  conditions = []
  # Going through each video listed in the excel file
  for videoId in range(0, len(excelFile)):
    if excelFile.loc[videoId, 'path'] == "defaultZZoutputFolder":
      path    = os.path.join(defaultZZoutputFolderPath, excelFile.loc[videoId, 'trial_id'])
    else:
      path    = os.path.join(excelFile.loc[videoId, 'path'], excelFile.loc[videoId, 'trial_id'])
    trial_id  = excelFile.loc[videoId, 'trial_id']
    fq        = excelFile.loc[videoId, 'fq']
    pixelsize = excelFile.loc[videoId, 'pixelsize']
    condition = excelFile.loc[videoId, 'condition']
    condition = eval('[' + condition + ']')
    condition = condition[0]
    genotype  = excelFile.loc[videoId, 'genotype']
    genotype = eval('[' + genotype + ']')
    genotype = genotype[0]
    include   = excelFile.loc[videoId, 'include']
    include = eval('[' + include + ']')
    include = include[0]
    
    with open(os.path.join(path, 'results_' + trial_id + '.txt')) as f:
      supstruct = json.load(f)
    
    # Going through each well of the video
    for Well_ID, Cond in enumerate(condition):
      if include[Well_ID]:
        print("trial_id:", trial_id, " ; Well_ID:", Well_ID)
        dfParamForWell = pd.DataFrame(columns=dfCols)
        curBoutId = 0
        # Going through each animal present in the well
        for fishId in range(0, len(supstruct["wellPoissMouv"][Well_ID])):
          # Going through each bout performed by the animal
          for NumBout, dataForBout in enumerate(supstruct["wellPoissMouv"][Well_ID][fishId]):
            if not("flag" in dataForBout) or dataForBout["flag"] == 0:
              # Calculating specified parameters for that bout
              if "Bend_Timing" in dataForBout and type(dataForBout["Bend_Timing"]) == list and len(dataForBout["Bend_Timing"]) >= minNbBendForBoutDetect:
                
                # Initial basic information
                
                toPutInDataFrameColumn = basicInformation
                
                if not(genotype[Well_ID] in genotypes):
                  genotypes.append(genotype[Well_ID])
                if not(condition[Well_ID] in conditions):
                  conditions.append(condition[Well_ID])
                
                nbFramesTakenIntoAccount = dataForBout['BoutEnd'] - dataForBout['BoutStart']
                
                # Tail angles
                
                if getTailAngleSignMultNormalized:
                  
                  toPutInDataFrameColumn = toPutInDataFrameColumn + tailAngles
                  
                  tailAnglesData         = getTailAngles(dataForBout, smoothingFactor, nbFramesTakenIntoAccount, numberOfBendsIncludedForMaxDetect)
                
                # Calculate "dynamic" tail angle related parameters for clustering
                
                if computeTailAngleParamForCluster:
                
                  toPutInDataFrameColumn = toPutInDataFrameColumn + instaTBF + instaAmp + instaAsym
                  
                  tailAngleParamForCluster = getDynamicParameters(dataForBout, smoothingFactor, nbFramesTakenIntoAccount, numberOfBendsIncludedForMaxDetect)
                
                # Calculate "dynamic" center of mass related parameters for clustering
                
                if computeMassCenterParamForCluster:
                
                  toPutInDataFrameColumn = toPutInDataFrameColumn + instaSpeed + instaHeadingDiff + instaHorizDispl
                  
                  instaSpeedVal       = getInstaSpeed(dataForBout, nbFramesTakenIntoAccount)
                  instaHeadingDiffVal = getInstaHeadingDiff(dataForBout, nbFramesTakenIntoAccount)
                  instaHorizDisplVal  = getInstaHorizontalDisplacement(dataForBout, nbFramesTakenIntoAccount)
                
                # Adding bout parameters to the dataframe created for the current well
                
                for idx in range(nbFramesTakenIntoAccount):
                  if computeMassCenterParamForCluster:
                    dfParamForWell.loc[curBoutId, toPutInDataFrameColumn] = [dataForBout['BoutStart']+idx, trial_id, Well_ID, NumBout, dataForBout['BoutStart'], dataForBout['BoutEnd'], condition[Well_ID], genotype[Well_ID], tailAnglesData[idx], tailAngleParamForCluster[idx], tailAngleParamForCluster[nbFramesTakenIntoAccount+idx], tailAngleParamForCluster[2*nbFramesTakenIntoAccount+idx], instaSpeedVal[idx], instaHeadingDiffVal[idx], instaHorizDisplVal[idx]]
                  else:
                    dfParamForWell.loc[curBoutId, toPutInDataFrameColumn] = [dataForBout['BoutStart']+idx, trial_id, Well_ID, NumBout, dataForBout['BoutStart'], dataForBout['BoutEnd'], condition[Well_ID], genotype[Well_ID], tailAnglesData[idx], tailAngleParamForCluster[idx], tailAngleParamForCluster[nbFramesTakenIntoAccount+idx], tailAngleParamForCluster[2*nbFramesTakenIntoAccount+idx]]
                  curBoutId = curBoutId + 1
        
        # Adding dataframe created for the current frame to the dataframe for the whole set of videos
        dfParam = pd.concat([dfParam, dfParamForWell])
  
  # Saving the dataframe
  dfParam = dfParam.reset_index()
  
  # Saving dataframe for the whole set of videos as a pickle file
  outfile = open(os.path.join(resFolder, nameOfFile), 'wb')
  pickle.dump(dfParam,outfile)
  outfile.close()
  
  return [conditions, genotypes, nbFramesTakenIntoAccount]
