Look at the script populationCompare_UsageExample for an example of how to compare different populations of fish.

Look at the script cluster_1a_UsageExample for an example of how to cluster bouts. After this script is executed, a result folder will appear in the boutsClustering folder. The variable allBouts will also contain the classification for each bout.

You can also look at the script cluster_1b_UsageExampleReloadClassifier.py for an example of how to classify bouts with a classifier that you've previously created and saved in the past.

The script createDataFrame.py creates a pandas dataframe that can then be used to either compare populations or cluster bouts.
The script populationComparaison.py compares different population
The script applyClustering.py applies the clustering on the dataframe of bouts and adds a classification for each bout. It also returns the classifier created, which can be used again in the future if necessary.


Some useful options to change:

- for dataframeOptions:

  nameOfFile: name of the excel file (located inside the folder "pathToExcelFile") describing the different videos on which you want to do the clustering
  
  nbFramesTakenIntoAccount: number of frames used as input to the clustering algorithm (the frames 0 until nbFramesTakenIntoAccount-1 are used)
  
- for clusteringOptions:

  nameOfFile: same as for dataframeOptions
  
  videoSaveFirstTenBouts: if set to True, the script will generate validation videos for each cluster (it will take a little bit more time for the script to run however)

  
NB:
Also less important, but for dataframeOptions, you can look at:
  numberOfBendsIncludedForMaxDetect: the tailAngle is transformed to -tailAngle when the maximum absolute value of the first numberOfBendsIncludedForMaxDetect bends is negative (not in absolute value). If numberOfBendsIncludedForMaxDetect is set to -1, then all bends are used
