import numpy as np
import pandas as pd
import math
import os

def calculateNumberOfSfsVsTurnsBasedOnMaxAmplitudeThreshold(pathRootDirectory, experimentName, thresholdInDegrees):

  maxAmplitudeThreshold = thresholdInDegrees * (math.pi / 180)
  
  df = pd.read_excel(os.path.join(os.path.join(os.path.join(os.path.join(os.path.join(pathRootDirectory, 'dataAnalysis'), 'resultsKinematic'), experimentName), 'allBoutsMixed'), "globalParametersInsideCategories.xlsx"))
  
  outputFile = open(os.path.join(os.path.join(os.path.join(os.path.join(os.path.join(pathRootDirectory, 'dataAnalysis'), 'resultsKinematic'), experimentName), 'allBoutsMixed'), "numberOfSfsVsTurnsBasedOnMaxAmplitudeThreshold.txt"), "w")
  print("There's a total of", len(df), "bouts in this dataset.")
  outputFile.write("There's a total of " + str(len(df)) + " bouts in this dataset.\n")

  allConditionsNames = np.unique(df['Condition'].tolist()).tolist()
  allGenotypesNames  = np.unique(df['Genotype'].tolist()).tolist()

  for conditionName in allConditionsNames:
    dfCond = df.loc[df['Condition'] == conditionName]
    for genotypeName in allGenotypesNames:
      dfCondGeno = dfCond.loc[dfCond['Genotype'] == genotypeName]
      nbTurns = np.sum(dfCondGeno['maxTailAngleAmplitude'] > maxAmplitudeThreshold)
      nbSfs   = np.sum(dfCondGeno['maxTailAngleAmplitude'] <= maxAmplitudeThreshold)
      nbBouts = len(dfCondGeno)
      print("For the condition:", conditionName, "and the genotype:", genotypeName, "there are:", nbSfs, "sfs and", nbTurns, "turns, for a total of", nbBouts, "bouts")
      outputFile.write("For the condition: " + conditionName + " and the genotype: " + genotypeName + " there are: " + str(nbSfs) + " sfs and " + str(nbTurns) + " turns, for a total of " + str(nbBouts) + " bouts\n")
  
  outputFile.close()
