import scipy.io
import pandas as pd
import json
import numpy as np
from getDynamicParameters import getDynamicParameters
from getTailAngles import getTailAngles
from getInstaSpeed import getInstaSpeed
from getInstaHeadingDiff import getInstaHeadingDiff
from getInstaHorizontalDisplacement import getInstaHorizontalDisplacement
from getGlobalParameters import getGlobalParameters
from getDeltaHead import getDeltaHead
from getTailLength  import getTailLength
from getTailLength2 import getTailLength2
from getTailAngleRecalculated import getTailAngleRecalculated
from getTailAngleRecalculated2 import getTailAngleRecalculated2
import pickle

def createDataFrame(dataframeOptions):

  pathToExcelFile                   = dataframeOptions['pathToExcelFile']
  nameOfFile                        = dataframeOptions['nameOfFile']
  fileExtension                     = dataframeOptions['fileExtension']
  smoothingFactor                   = dataframeOptions['smoothingFactorDynaParam']
  resFolder                         = dataframeOptions['resFolder']
  numberOfBendsIncludedForMaxDetect = dataframeOptions['numberOfBendsIncludedForMaxDetect']
  minNbBendForBoutDetect            = dataframeOptions['minNbBendForBoutDetect']
  computeTailAngleParamForCluster   = dataframeOptions['computeTailAngleParamForCluster']
  computeMassCenterParamForCluster  = dataframeOptions['computeMassCenterParamForCluster']
  if 'defaultZZoutputFolderPath' in dataframeOptions:
    defaultZZoutputFolderPath       = dataframeOptions['defaultZZoutputFolderPath']
  else:
    defaultZZoutputFolderPath       = ''
  computetailAnglesRecalculatedParamsForCluster = False
  if 'computetailAnglesRecalculatedParamsForCluster' in dataframeOptions:
    computetailAnglesRecalculatedParamsForCluster = dataframeOptions["computetailAnglesRecalculatedParamsForCluster"]
  else:
    computetailAnglesRecalculatedParamsForCluster = False
  
  nbFramesTakenIntoAccount          = dataframeOptions['nbFramesTakenIntoAccount']
  excelFile = pd.read_excel(pathToExcelFile + nameOfFile + fileExtension)
  if nbFramesTakenIntoAccount == -1:
    boutNbFrames = []
    boutTakenIntoAcccount = 0
    videoId = 0
    if excelFile.loc[videoId, 'path'] == "defaultZZoutputFolder":
      path    = defaultZZoutputFolderPath + excelFile.loc[videoId, 'trial_id'] + '/'
    else:
      path    = excelFile.loc[videoId, 'path'] + excelFile.loc[videoId, 'trial_id'] + '/'
    trial_id  = excelFile.loc[videoId, 'trial_id']
    include   = excelFile.loc[videoId, 'include']
    include = eval('[' + include + ']')
    include = include[0]
    with open(path+'results_'+trial_id+'.txt') as f:
      supstruct = json.load(f)
    for Well_ID, Cond in enumerate(include):
      if include[Well_ID]:
        for NumBout, dataForBout in enumerate(supstruct["wellPoissMouv"][Well_ID][0]):
          boutNbFrames.append(len(dataForBout["HeadX"]))
          boutTakenIntoAcccount = boutTakenIntoAcccount + 1
          if boutTakenIntoAcccount > 100:
            break;
      if boutTakenIntoAcccount > 100:
        break;
    nbFramesTakenIntoAccount = int(np.median(boutNbFrames))
  
  genotypes  = []
  conditions = []
  
  # Creating labels of columns of dataframe
  # Global parameters
  globParam  = ['Well_ID', 'NumBout', 'BoutStart', 'BoutEnd', 'Condition', 'Genotype', 'BoutDuration', 'TotalDistance', 'Speed', 'NumberOfOscillations', 'meanTBF', 'maxAmplitude', 'deltaHead', 'xstart', 'xend', 'xmean', 'firstBendTime', 'firstBendAmplitude']
  # Tail angle related parameters for clustering
  instaTBF   = ['instaTBF'  + str(i) for i in range(1,nbFramesTakenIntoAccount+1)]
  instaAmp   = ['instaAmp'  + str(i) for i in range(1,nbFramesTakenIntoAccount+1)]
  instaAsym  = ['instaAsym' + str(i) for i in range(1,nbFramesTakenIntoAccount+1)]
  tailAngles = ['tailAngles'+ str(i) for i in range(1,nbFramesTakenIntoAccount+1)]
  tailAnglesRecalculated = ['tailAnglesRecalculated'+ str(i) for i in range(1,nbFramesTakenIntoAccount+1)]
  tailAnglesRecalculated2 = ['tailAnglesRecalculated2_'+ str(i) for i in range(1, 7*nbFramesTakenIntoAccount+1)]
  # Center of mass related parameters for clustering
  instaSpeed       = ['instaSpeed'       + str(i) for i in range(1,nbFramesTakenIntoAccount+1)]
  instaHeadingDiff = ['instaHeadingDiff' + str(i) for i in range(1,nbFramesTakenIntoAccount+1)]
  instaHorizDispl  = ['instaHorizDispl'  + str(i) for i in range(1,nbFramesTakenIntoAccount+1)]
  # Assembling columns
  dfCols = ['Trial_ID'] + globParam + tailAngles
  if computeTailAngleParamForCluster:
    dfCols = dfCols + instaTBF + instaAmp + instaAsym
  if computeMassCenterParamForCluster:
    dfCols = dfCols + instaSpeed + instaHeadingDiff + instaHorizDispl
  if computetailAnglesRecalculatedParamsForCluster:
    dfCols = dfCols + ['tailLength', 'tailLengthFromRecalculatedAngles'] + tailAnglesRecalculated + tailAnglesRecalculated2
  if computeTailAngleParamForCluster or computeMassCenterParamForCluster or computetailAnglesRecalculatedParamsForCluster:
    dfCols = dfCols + ['classification']
  numberOfParameters = len(dfCols)
  
  # Creating an empty dataframe
  params = np.zeros((0, numberOfParameters))
  dfParam = pd.DataFrame(params,columns=dfCols)
  trialidstab = []
  
  # Filling in the dataframe
  # curBoutId = 0
  print("Calculating and storing all parameters:")
  for videoId in range(0, len(excelFile)):
    if excelFile.loc[videoId, 'path'] == "defaultZZoutputFolder":
      path    = defaultZZoutputFolderPath + excelFile.loc[videoId, 'trial_id'] + '/'
    else:
      path    = excelFile.loc[videoId, 'path'] + excelFile.loc[videoId, 'trial_id'] + '/'
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
    
    with open(path+'results_'+trial_id+'.txt') as f:
      supstruct = json.load(f)
    
    for Well_ID, Cond in enumerate(condition):
      if include[Well_ID]:
        print("trial_id:", trial_id, " ; Well_ID:", Well_ID)
        dfParamSub = pd.DataFrame(params,columns=dfCols)
        curBoutId = 0
        for fishId in range(0, len(supstruct["wellPoissMouv"][Well_ID])):
          for NumBout, dataForBout in enumerate(supstruct["wellPoissMouv"][Well_ID][fishId]):
            if type(dataForBout["Bend_Timing"]) == list and len(dataForBout["Bend_Timing"]) >= minNbBendForBoutDetect and (not("flag" in dataForBout) or dataForBout["flag"] == 0):
            
              trialidstab.append(trial_id)
              if not(genotype[Well_ID] in genotypes):
                genotypes.append(genotype[Well_ID])
              if not(condition[Well_ID] in conditions):
                conditions.append(condition[Well_ID])
              
              # Calculating the global kinematic parameters and more and stores them the dataframe
              
              [BoutDuration, TotalDistance, Speed, NumberOfOscillations, meanTBF, maxAmplitude, xstart, xend, xmean, firstBendTime, firstBendAmplitude] = getGlobalParameters(dataForBout, fq, pixelsize)
              
              deltahead  = abs(getDeltaHead(dataForBout))
              tailLength = getTailLength(dataForBout)
              
              tailAnglesRecalculatedData  = getTailAngleRecalculated(dataForBout, nbFramesTakenIntoAccount, numberOfBendsIncludedForMaxDetect)
              
              # tailLengthFromRecalculatedAngles = getTailLength2(tailAnglesRecalculatedData)
              
              toPutInDataFrameColumn = []
              toPutInDataFrame       = []
              
              toPutInDataFrameColumn = toPutInDataFrameColumn + globParam
              toPutInDataFrame       = toPutInDataFrame + [Well_ID, NumBout, dataForBout['BoutStart'], dataForBout['BoutEnd'], condition[Well_ID], genotype[Well_ID], BoutDuration, TotalDistance, Speed, NumberOfOscillations, meanTBF, maxAmplitude, deltahead, xstart, xend, xmean, firstBendTime, firstBendAmplitude]
              
              toPutInDataFrameColumn = toPutInDataFrameColumn + tailAngles
              toPutInDataFrame       = toPutInDataFrame + getTailAngles(dataForBout, smoothingFactor, nbFramesTakenIntoAccount, numberOfBendsIncludedForMaxDetect)
              
              
              # Calculate "dynamic" tail angle related parameters for clustering
              
              if computeTailAngleParamForCluster:
              
                toPutInDataFrameColumn = toPutInDataFrameColumn + instaTBF + instaAmp + instaAsym
                toPutInDataFrame       = toPutInDataFrame + getDynamicParameters(dataForBout, smoothingFactor, nbFramesTakenIntoAccount, numberOfBendsIncludedForMaxDetect)
              
              # Calculate "dynamic" center of mass related parameters for clustering
              
              if computeMassCenterParamForCluster:
              
                instaSpeedVal       = getInstaSpeed(dataForBout, nbFramesTakenIntoAccount)
                instaHeadingDiffVal = getInstaHeadingDiff(dataForBout, nbFramesTakenIntoAccount)
                instaHorizDisplVal  = getInstaHorizontalDisplacement(dataForBout, nbFramesTakenIntoAccount)
                
                toPutInDataFrameColumn = toPutInDataFrameColumn + instaSpeed + instaHeadingDiff + instaHorizDispl
                toPutInDataFrame       = toPutInDataFrame + instaSpeedVal + instaHeadingDiffVal + instaHorizDisplVal
                
              # Recalculates tail angles and calculates 
              
              if computetailAnglesRecalculatedParamsForCluster:

                tailLength = getTailLength(dataForBout)
                
                tailAnglesRecalculatedData  = getTailAngleRecalculated(dataForBout, nbFramesTakenIntoAccount, numberOfBendsIncludedForMaxDetect)
                
                tailLengthFromRecalculatedAngles = getTailLength2(tailAnglesRecalculatedData)
              
                tailAnglesRecalculatedData2 = getTailAngleRecalculated2(dataForBout, nbFramesTakenIntoAccount, numberOfBendsIncludedForMaxDetect)
                
                toPutInDataFrameColumn = toPutInDataFrameColumn + ['tailLength', 'tailLengthFromRecalculatedAngles'] + tailAnglesRecalculated + tailAnglesRecalculated2
                toPutInDataFrame       = toPutInDataFrame + [tailLength, tailLengthFromRecalculatedAngles] + tailAnglesRecalculatedData + tailAnglesRecalculatedData2.tolist()
              
              dfParamSub.loc[curBoutId, toPutInDataFrameColumn] = toPutInDataFrame
              
              curBoutId = curBoutId + 1
        
        dfParam = pd.concat([dfParam, dfParamSub])
  
  # Saving the dataframe
  dfParam = dfParam.reset_index()
  dfParam['Trial_ID'][:] = trialidstab
  outfile = open(resFolder + nameOfFile,'wb')
  pickle.dump(dfParam,outfile)
  outfile.close()
  
  return [conditions, genotypes, nbFramesTakenIntoAccount]
