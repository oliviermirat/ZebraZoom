import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
import numpy as np

def plotLatencyVsAmplitude(config):
  
  onlyKeepBoutsWithLatencySmallerThan = config["onlyKeepBoutsWithLatencySmallerThan"]
  onlyKeepBoutsWithLatencyBiggerThan  = config["onlyKeepBoutsWithLatencyBiggerThan"]
  onlyKeepBoutsWithFirstBendAmpOver   = config["onlyKeepBoutsWithFirstBendAmpOver"]
  plotTrialNumberWithSize             = config["plotTrialNumberWithSize"]
  plotLatencyOrAmpDependingOnSize     = config["plotLatencyOrAmpDependingOnSize"] if 'plotLatencyOrAmpDependingOnSize' in config else False
  genotypeOrCondition = config["genotypeOrCondition"]
  kinematicParametersExcelFile = config['kinematicParametersExcelFile']
  fps = config["fps"]
  simulationTimeSeconds = config["simulationTimeSeconds"]
  xAxisParameterName = config['xAxisParameterName']
  genotypeOrConditionToRemove = config['genotypeOrConditionToRemove']
  latencyCutOffForProportionsCalculation = config['latencyCutOffForProportionsCalculation']
  
  data = pd.read_excel(kinematicParametersExcelFile)
  
  print(data)

  dataToPlot = data[["BoutStart", xAxisParameterName, genotypeOrCondition, "Trial_ID"]]

  dataToPlot['BoutStart'] = dataToPlot['BoutStart']/fps - simulationTimeSeconds
  
  print("")
  print(len(dataToPlot), "bouts initially")
  
  datasetSizeBefore = len(dataToPlot)
  if onlyKeepBoutsWithLatencySmallerThan < 1:
    dataToPlot = dataToPlot[dataToPlot['BoutStart'] <= onlyKeepBoutsWithLatencySmallerThan]
  datasetSizeAfter = len(dataToPlot)
  print(datasetSizeBefore - datasetSizeAfter, "bouts removed because latency was too high (above", onlyKeepBoutsWithLatencySmallerThan, ")")
  
  datasetSizeBefore = len(dataToPlot)
  if onlyKeepBoutsWithLatencyBiggerThan > -1:
    dataToPlot = dataToPlot[dataToPlot['BoutStart'] >= onlyKeepBoutsWithLatencyBiggerThan]
  datasetSizeAfter = len(dataToPlot)
  print(datasetSizeBefore - datasetSizeAfter, "bouts removed because latency was too small (bellow", onlyKeepBoutsWithLatencyBiggerThan, ")")
  
  datasetSizeBefore = len(dataToPlot)
  if onlyKeepBoutsWithFirstBendAmpOver > -1:
    dataToPlot = dataToPlot[dataToPlot[xAxisParameterName] >= onlyKeepBoutsWithFirstBendAmpOver]
  datasetSizeAfter = len(dataToPlot)
  print(datasetSizeBefore - datasetSizeAfter, "bouts removed because first bend amplitude was too small (bellow", onlyKeepBoutsWithFirstBendAmpOver, ")")
  
  print("")
  print(len(dataToPlot), "bouts in total after removal procedures. Of which there are:")
  allPossibleGenCondOptions = np.unique(dataToPlot[genotypeOrCondition])
  for possibleGenCondOption in allPossibleGenCondOptions:
    print(len(dataToPlot[dataToPlot[genotypeOrCondition] == possibleGenCondOption]), possibleGenCondOption, "bouts (", (len(dataToPlot[dataToPlot[genotypeOrCondition] == possibleGenCondOption]) / len(dataToPlot)) * 100, "%)")
  
  # Calculating proportions for lower and upper clusters
  if latencyCutOffForProportionsCalculation != -1:
    print("")
    dataLowerCluster = dataToPlot[dataToPlot['BoutStart'] < latencyCutOffForProportionsCalculation]
    nbBoutsInLowerCluster = len(dataLowerCluster)
    print(nbBoutsInLowerCluster, "bouts in the lower cluster")
    allPossibleGenCondOptions = np.unique(dataLowerCluster[genotypeOrCondition])
    for possibleGenCondOption in allPossibleGenCondOptions:
      proportionOfBoutsOfGenCondInLowerCluster = (len(dataLowerCluster[dataLowerCluster[genotypeOrCondition] == possibleGenCondOption]) / nbBoutsInLowerCluster) * 100
      print(proportionOfBoutsOfGenCondInLowerCluster, "% of", possibleGenCondOption, "(", len(dataLowerCluster[dataLowerCluster[genotypeOrCondition] == possibleGenCondOption]), "bouts )")
    print("")
    dataUpperCluster = dataToPlot[dataToPlot['BoutStart'] >= latencyCutOffForProportionsCalculation]
    nbBoutsInUpperCluster = len(dataUpperCluster)
    print(nbBoutsInUpperCluster, "bouts in the upper cluster")
    allPossibleGenCondOptions = np.unique(dataUpperCluster[genotypeOrCondition])
    for possibleGenCondOption in allPossibleGenCondOptions:
      proportionOfBoutsOfGenCondInLowerCluster = (len(dataUpperCluster[dataUpperCluster[genotypeOrCondition] == possibleGenCondOption]) / nbBoutsInUpperCluster) * 100
      print(proportionOfBoutsOfGenCondInLowerCluster, "% of", possibleGenCondOption, "(", len(dataUpperCluster[dataUpperCluster[genotypeOrCondition] == possibleGenCondOption]), "bouts )")
    
  # print(len(dataToPlot[dataToPlot['Condition'] == 'WT']), "bouts remain out of", 74*2, "bouts that should be triggered. Or", (len(dataToPlot[dataToPlot['Condition'] == 'WT']) / (74*2)) * 100, "%")
  # print(len(dataToPlot[dataToPlot['Condition'] == 'Parkinson']), "bouts remain out of", 74*2, "bouts that should be triggered. Or", (len(dataToPlot[dataToPlot['Condition'] == 'Parkinson']) / (74*2)) * 100, "%")
  
  if len(genotypeOrConditionToRemove):
    dataToPlot = dataToPlot[dataToPlot[genotypeOrCondition] != genotypeOrConditionToRemove]
    print("")
    print(len(dataToPlot), "bouts after removal of", genotypeOrConditionToRemove)
  
  dataToPlot = dataToPlot.reset_index()
  
  if plotTrialNumberWithSize:
    
    dataToPlot['TrialNumber'] = 0
    for i in range(0, len(dataToPlot)):
      textLength = len(dataToPlot['Trial_ID'][i])
      characterNminusOne = dataToPlot['Trial_ID'][i][textLength-2:textLength-1]
      trialNumber = ''
      if characterNminusOne == "_" or characterNminusOne == "t" or characterNminusOne == ".":
        trialNumber = dataToPlot['Trial_ID'][i][textLength-1:textLength]
      else:
        trialNumber = dataToPlot['Trial_ID'][i][textLength-2:textLength]
      dataToPlot['TrialNumber'][i] = int(trialNumber)
    
    sns.relplot(data=dataToPlot, x=xAxisParameterName, y="BoutStart", hue=genotypeOrCondition, size="TrialNumber")
    
    if plotLatencyOrAmpDependingOnSize:
      sns.relplot(data=dataToPlot, x="TrialNumber", y="BoutStart", hue=genotypeOrCondition)
      sns.relplot(data=dataToPlot, x="TrialNumber", y="BoutStart", hue=genotypeOrCondition, kind="line")
      sns.relplot(data=dataToPlot, x="TrialNumber", y=xAxisParameterName, hue=genotypeOrCondition)
      sns.relplot(data=dataToPlot, x="TrialNumber", y=xAxisParameterName, hue=genotypeOrCondition, kind="line")
      
  else:
    
    sns.relplot(data=dataToPlot, x=xAxisParameterName, y="BoutStart", hue=genotypeOrCondition)

  plt.show()


configRemoveSomeBouts = {
  'kinematicParametersExcelFile' : 'globalParametersInsideCategories.xlsx', #'globalParametersInsideCategories.xlsx',
  'genotypeOrCondition' : "Genotype", # Set this to either "Genotype" or "Condition"
  'genotypeOrConditionToRemove' : 'Het', # Set to name of condition or genotype to remove a specific condition or genotype from your dataset; or otherwise set to '' to keep all
  'fps' : 650, # fps at which the video was recorded
  'simulationTimeSeconds' : 0.212, # Time in second when the stimuli was applied
  'xAxisParameterName' : 'maxTailAngleAmplitude',   # Name of the parameter to plot on the x axis (amplitude related)
  'onlyKeepBoutsWithLatencySmallerThan' : 0.1,   # Set to 1 to keep all bouts (unit in seconds)
  'onlyKeepBoutsWithLatencyBiggerThan' : 0, # Set to -1 to keep all bouts (unit in seconds)
  'onlyKeepBoutsWithFirstBendAmpOver' : 50,      # Set to -1 to keep all bouts (unit in degrees)
  'latencyCutOffForProportionsCalculation' : 0.02, # Set to a value >0 to calculate proportion of each genotype/condition in both the lower and upper clusters; Set to -1 otherwise
  'plotTrialNumberWithSize' : False 
}

plotLatencyVsAmplitude(configRemoveSomeBouts)
