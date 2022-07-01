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

def createDataFrame(dataframeOptions, excelFileDataFrame="", forcePandasDfRecreation=0, addToGlobalParameters=0, minimumFrameToFrameDistanceToBeConsideredAsMoving=0, supstructOverwrite={}):

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
  
  # If nbFramesTakenIntoAccount was not specified, finds an appropriate value for it
  nbFramesTakenIntoAccount          = dataframeOptions['nbFramesTakenIntoAccount']
  if len(pathToExcelFile):
    excelFile = pd.read_excel(os.path.join(pathToExcelFile, nameOfFile + fileExtension))
  elif type(excelFileDataFrame) != str:
    excelFile = excelFileDataFrame
  else:
    print("You must provide either an excel file or a video name to create a dataframe of parameters.")
  
  if nbFramesTakenIntoAccount <= -1:
    boutNbFrames = []
    boutTakenIntoAcccount = 0
    videoId = 0
    if excelFile.loc[videoId, 'path'] == "defaultZZoutputFolder":
      path    = os.path.join(defaultZZoutputFolderPath, excelFile.loc[videoId, 'trial_id'])
    else:
      path    = os.path.join(excelFile.loc[videoId, 'path'], excelFile.loc[videoId, 'trial_id'])
    trial_id  = excelFile.loc[videoId, 'trial_id']
    include   = [bool(int(val.strip())) for val in excelFile.loc[videoId, 'include'][1:-1].split(',')]
    if len(supstructOverwrite):
      supstruct = supstructOverwrite
    else:
      with open(os.path.join(path, 'results_' + trial_id + '.txt')) as f:
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
    if len(boutNbFrames):
      if nbFramesTakenIntoAccount == -1:
        nbFramesTakenIntoAccount = int(np.median(boutNbFrames))
      else:
        nbFramesTakenIntoAccount = 3 * int(np.median(boutNbFrames)) if 3 * int(np.median(boutNbFrames)) >= 100 else 100
    else:
      # There are not bouts in the dataset...
      return [[], [], 0, []]
  
  # Creating labels of columns of dataframe
  # General basic information
  basicInformation = ['Trial_ID', 'Well_ID', 'NumBout', 'BoutStart', 'BoutEnd', 'Condition', 'Genotype', 'videoDuration']
  # Global parameters
  if tailAngleKinematicParameterCalculation:
    globParam  = ['BoutDuration', 'TotalDistance', 'Speed', 'maxOfInstantaneousTBF', 'meanOfInstantaneousTBF', 'medianOfInstantaneousTBF', 'maxBendAmplitude', 'maxBendAmplitudeSigned', 'meanBendAmplitude', 'medianBendAmplitude', 'medianBendAmplitudeSigned', 'NumberOfOscillations', 'meanTBF', 'maxTailAngleAmplitude', 'deltaHead', 'firstBendTime', 'firstBendAmplitude', 'firstBendAmplitudeSigned', 'IBI', 'xmean', 'ymean', 'binaryClass25degMaxTailAngle', 'tailAngleIntegralSigned', 'BoutFrameNumberStart', 'tailAngleSymmetry', 'secondBendAmpDividedByFirst', 'tailAngleIntegral', 'maxInstantaneousSpeed']
  else:
    globParam  = ['BoutDuration', 'TotalDistance', 'Speed']
  
  if type(addToGlobalParameters) == list:
    globParam = globParam + addToGlobalParameters  
  
  # Initial raw data
  if saveRawDataInAllBoutsSuperStructure:
    if tailAngleKinematicParameterCalculation:
      rawData = ['HeadX', 'HeadY', 'Heading', 'TailAngle_Raw', 'TailAngle_smoothed', 'Bend_Timing', 'Bend_TimingAbsolute', 'Bend_Amplitude', 'TailBeatFrequency', 'curvature']
    else:
      rawData = ['HeadX', 'HeadY', 'Heading']
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
  dfCols = basicInformation + globParam
  if computeTailAngleParamForCluster:
    dfCols = dfCols + tailAngles
  if saveRawDataInAllBoutsSuperStructure:
    dfCols = dfCols + rawData
  if computeTailAngleParamForCluster:
    dfCols = dfCols + instaTBF + instaAmp + instaAsym
  if computeMassCenterParamForCluster:
    dfCols = dfCols + instaSpeed + instaHeadingDiff + instaHorizDispl
  if computetailAnglesRecalculatedParamsForCluster:
    dfCols = dfCols + ['tailLength', 'tailLengthFromRecalculatedAngles'] + tailAnglesRecalculated + tailAnglesRecalculated2
  if computeTailAngleParamForCluster or computeMassCenterParamForCluster or computetailAnglesRecalculatedParamsForCluster:
    dfCols = dfCols + ['classification']
  numberOfParameters = len(dfCols)
  
  # Creating an empty dataframe then filling it with the parameters for the whole set of videos
  print("Calculating and storing all parameters:")
  dfParam = pd.DataFrame(columns=dfCols)
  genotypes  = []
  conditions = []
  # This is for the potential reload from previously calculated parameters (stored in the pkl file)
  if keepSpeedDistDurWhenLowNbBends == 1:
    onlyKeepTheseColumns = basicInformation + ['BoutDuration', 'TotalDistance', 'Speed', 'IBI']
  else:
    onlyKeepTheseColumns = basicInformation
  removeColumnsWhenAppropriate = [col for col in dfCols if not(col in onlyKeepTheseColumns)]
  # Going through each video listed in the excel file
  for videoId in range(0, len(excelFile)):
    
    if excelFile.loc[videoId, 'path'] == "defaultZZoutputFolder":
      path    = os.path.join(defaultZZoutputFolderPath, excelFile.loc[videoId, 'trial_id'])
    else:
      path    = os.path.join(excelFile.loc[videoId, 'path'], excelFile.loc[videoId, 'trial_id'])
    trial_id  = excelFile.loc[videoId, 'trial_id']
    fq        = excelFile.loc[videoId, 'fq']
    pixelsize = excelFile.loc[videoId, 'pixelsize']
    condition = [val.strip('\'" ') for val in excelFile.loc[videoId, 'condition'][1:-1].split(',')]
    genotype  = [val.strip('\'" ') for val in excelFile.loc[videoId, 'genotype'][1:-1].split(',')]
    include   = [bool(int(val.strip())) for val in excelFile.loc[videoId, 'include'][1:-1].split(',')]
    
    if (not(os.path.exists(os.path.join(path, trial_id + '.pkl'))) or forcePandasDfRecreation):
      if len(supstructOverwrite):
        supstruct = supstructOverwrite
      else:
        with open(os.path.join(path, 'results_' + trial_id + '.txt')) as f:
          supstruct = json.load(f)
      firstFrame = supstruct["firstFrame"]
      lastFrame  = supstruct["lastFrame"]
      with open(os.path.join(path, 'parametersUsedForCalculation.json'), 'w') as outfile:
        print('frameStepForDistanceCalculation', frameStepForDistanceCalculation)
        print('videoFPS', excelFile.loc[videoId, 'fq'])
        print('videoPixelSize', excelFile.loc[videoId, 'pixelsize'])
        json.dump({'frameStepForDistanceCalculation': int(frameStepForDistanceCalculation), 'videoFPS': float(excelFile.loc[videoId, 'fq']), 'videoPixelSize': float(excelFile.loc[videoId, 'pixelsize'])}, outfile)
    else:
      print("reloading previously calculated parameters")
      dfReloadedVid = pd.read_pickle(os.path.join(path, trial_id + '.pkl'))
      
      nbFramesTakenIntoAccountReloaded = max([np.sum(['instaTBF' in param for param in dfReloadedVid.columns.tolist()]), np.sum(['tailAnglesRecalculated' in param for param in dfReloadedVid.columns.tolist()]), np.sum(['instaSpeed' in param for param in dfReloadedVid.columns.tolist()])])
      if nbFramesTakenIntoAccountReloaded < nbFramesTakenIntoAccount:
        raise ValueError("nbFramesTakenIntoAccount was too low when pre-generating the pkl file of a video:" + str(np.sum(['instaTBF' in param for param in dfReloadedVid.columns.tolist()])) + " , " + str(np.sum(['tailAnglesRecalculated' in param for param in dfReloadedVid.columns.tolist()])) + " , " + str(np.sum(['instaSpeed' in param for param in dfReloadedVid.columns.tolist()])) + " ; nbFramesTakenIntoAccount :" + str(nbFramesTakenIntoAccount))
        
      for idx, cond in enumerate(condition):
        indForWellId = (dfReloadedVid['Well_ID'] == idx)
        if include[idx]:
          dfReloadedVid.loc[indForWellId, 'Condition'] = cond
          dfReloadedVid.loc[indForWellId, 'Genotype']  = genotype[idx]
          if minNbBendForBoutDetect > 0:
            ind           = (dfReloadedVid['NumberOfOscillations'] < minNbBendForBoutDetect/2)
            dfReloadedVid.loc[ind, removeColumnsWhenAppropriate] = float('NaN')
          if not(genotype[idx] in genotypes):
            genotypes.append(genotype[idx])
          if not(condition[idx] in conditions):
            conditions.append(condition[idx])
        else:
          dfReloadedVid = dfReloadedVid.drop([idx2 for idx2, belongsToWell in enumerate(indForWellId) if belongsToWell])
          if 'level_0' in dfReloadedVid.columns:
            dfReloadedVid = dfReloadedVid.drop(['level_0'], axis=1)
          dfReloadedVid = dfReloadedVid.reset_index()
          
      dfParam = pd.concat([dfParam, dfReloadedVid])
    
    # Going through each well of the video
    for Well_ID, Cond in enumerate(condition):
      # Not going through this loop if we've already reloaded parameters
      if include[Well_ID] and (not(os.path.exists(os.path.join(path, trial_id + '.pkl'))) or forcePandasDfRecreation):
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
                toPutInDataFrame       = [trial_id, Well_ID, NumBout, dataForBout['BoutStart'], dataForBout['BoutEnd'], condition[Well_ID], genotype[Well_ID], (lastFrame - firstFrame) / fq]
                
                if not(genotype[Well_ID] in genotypes):
                  genotypes.append(genotype[Well_ID])
                if not(condition[Well_ID] in conditions):
                  conditions.append(condition[Well_ID])
                
                # Calculates the global kinematic parameters and stores them the dataframe
                
                previousBoutEnd = supstruct["wellPoissMouv"][Well_ID][fishId][NumBout-1]["BoutEnd"] if NumBout > 0 else 0
                listOfGlobalParameters = getGlobalParameters(dataForBout, fq, pixelsize, frameStepForDistanceCalculation, previousBoutEnd, globParam, firstFrame, lastFrame, minimumFrameToFrameDistanceToBeConsideredAsMoving)
                
                toPutInDataFrameColumn = toPutInDataFrameColumn + globParam
                toPutInDataFrame       = toPutInDataFrame       + listOfGlobalParameters
                
                # Raw data
                
                if saveRawDataInAllBoutsSuperStructure:
                  toPutInDataFrameColumn = toPutInDataFrameColumn + rawData
                  toPutInDataFrame       = toPutInDataFrame       + gatherInitialRawData(dataForBout, rawData, fq)
                
                # Tail angles
                
                if getTailAngleSignMultNormalized:
                  toPutInDataFrameColumn = toPutInDataFrameColumn + tailAngles
                  toPutInDataFrame       = toPutInDataFrame       + getTailAngles(dataForBout, smoothingFactor, nbFramesTakenIntoAccount, numberOfBendsIncludedForMaxDetect)
                
                # Calculate "dynamic" tail angle related parameters for clustering
                
                if computeTailAngleParamForCluster:
                
                  toPutInDataFrameColumn = toPutInDataFrameColumn + instaTBF + instaAmp + instaAsym
                  toPutInDataFrame       = toPutInDataFrame       + getDynamicParameters(dataForBout, smoothingFactor, nbFramesTakenIntoAccount, numberOfBendsIncludedForMaxDetect)
                
                # Calculate "dynamic" center of mass related parameters for clustering
                
                if computeMassCenterParamForCluster:
                
                  instaSpeedVal       = getInstaSpeed(dataForBout, nbFramesTakenIntoAccount)
                  instaHeadingDiffVal = getInstaHeadingDiff(dataForBout, nbFramesTakenIntoAccount)
                  instaHorizDisplVal  = getInstaHorizontalDisplacement(dataForBout, nbFramesTakenIntoAccount)
                  
                  toPutInDataFrameColumn = toPutInDataFrameColumn + instaSpeed + instaHeadingDiff + instaHorizDispl
                  toPutInDataFrame       = toPutInDataFrame       + instaSpeedVal + instaHeadingDiffVal + instaHorizDisplVal
                  
                # Recalculates tail angles and calculates 
                
                if computetailAnglesRecalculatedParamsForCluster:

                  tailLength = getTailLength(dataForBout)
                  tailAnglesRecalculatedData  = getTailAngleRecalculated(dataForBout, nbFramesTakenIntoAccount, numberOfBendsIncludedForMaxDetect)
                  tailLengthFromRecalculatedAngles = getTailLength2(tailAnglesRecalculatedData)
                  tailAnglesRecalculatedData2 = getTailAngleRecalculated2(dataForBout, nbFramesTakenIntoAccount, numberOfBendsIncludedForMaxDetect)
                  
                  toPutInDataFrameColumn = toPutInDataFrameColumn + ['tailLength', 'tailLengthFromRecalculatedAngles'] + tailAnglesRecalculated + tailAnglesRecalculated2
                  toPutInDataFrame       = toPutInDataFrame       + [tailLength, tailLengthFromRecalculatedAngles] + tailAnglesRecalculatedData + tailAnglesRecalculatedData2.tolist()
                
                # Adding bout parameters to the dataframe created for the current well
                dfParamForWell.loc[curBoutId, toPutInDataFrameColumn] = toPutInDataFrame
                curBoutId = curBoutId + 1
              
              else:
                
                # Initial basic information
                
                toPutInDataFrameColumn = basicInformation
                toPutInDataFrame       = [trial_id, Well_ID, NumBout, dataForBout['BoutStart'], dataForBout['BoutEnd'], condition[Well_ID], genotype[Well_ID], (lastFrame - firstFrame) / fq]
                
                if not(genotype[Well_ID] in genotypes):
                  genotypes.append(genotype[Well_ID])
                if not(condition[Well_ID] in conditions):
                  conditions.append(condition[Well_ID])
                
                if keepSpeedDistDurWhenLowNbBends:
                  
                  # Calculating the global kinematic parameters and more and stores them the dataframe
                  
                  previousBoutEnd = supstruct["wellPoissMouv"][Well_ID][fishId][NumBout-1]["BoutEnd"] if NumBout > 0 else 0
                  listOfGlobalParameters = getGlobalParameters(dataForBout, fq, pixelsize, frameStepForDistanceCalculation, previousBoutEnd, ['BoutDuration', 'TotalDistance', 'Speed', 'IBI'] + addToGlobalParameters, firstFrame, lastFrame, minimumFrameToFrameDistanceToBeConsideredAsMoving)
                  
                  toPutInDataFrameColumn = toPutInDataFrameColumn + ['BoutDuration', 'TotalDistance', 'Speed', 'IBI'] + addToGlobalParameters
                  toPutInDataFrame       = toPutInDataFrame       + listOfGlobalParameters
                  
                # Adding bout parameters to the dataframe created for the current well
                
                dfParamForWell.loc[curBoutId, toPutInDataFrameColumn] = toPutInDataFrame
                curBoutId = curBoutId + 1
      
        # Adding dataframe created for the current frame to the dataframe for the whole set of videos
        dfParam = pd.concat([dfParam, dfParamForWell])
  
  # Saving the dataframe  
  if 'level_0' in dfParam.columns:
    dfParam = dfParam.drop(['level_0'], axis=1)
  dfParam = dfParam.reset_index()
  
  # Saving dataframe for the whole set of videos as a pickle file
  outfile = open(os.path.join(resFolder, nameOfFile + '.pkl'), 'wb')
  pickle.dump(dfParam,outfile)
  outfile.close()
  
  # Saving dataframe for the whole set of videos as a matlab file
  if saveAllBoutsSuperStructuresInMatlabFormat:
    scipy.io.savemat(os.path.join(resFolder, nameOfFile + '.mat'), {'struct1':dfParam.to_dict("list")})
    
  return [conditions, genotypes, nbFramesTakenIntoAccount, globParam]
