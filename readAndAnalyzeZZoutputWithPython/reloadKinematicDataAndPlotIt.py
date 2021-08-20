import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt

# The type of excel files referenced below can be found in the 'plots and processed data' folders, which are accessible through the GUI by clicking, from the main menu of the GUI, on: 'Analyze ZebraZoom's output' -> 'View previous kinematic parameter analysis results' -> 'View 'plot and processed data' folders'
# Choosing the excel file in the 'allBoutsMixed' folder or in the 'medianPerWellFirst' folders will result in different results as in the first case all bouts from all experiments are mixed up together whereas in the second case the median of each variable is taken for each videoName and well first (this only makes a difference if bouts of movements are being detected in your video of course)

filename = "globalParametersInsideCategories.xlsx"

dfParam = pd.read_excel(filename)

# Alternatively, you could also reload the data from the pickled (or matlab) raw data present in the 'raw data folder', which is accessible through the GUI by clicking, from the main menu of the GUI, on: 'Analyze ZebraZoom's output' -> 'View previous kinematic parameter analysis results' -> 'View 'raw data' folder'

nbLines   = 2
nbColumns = 3
fig, axes = plt.subplots(nbLines, nbColumns, sharex=True)

sns.set_theme(style="whitegrid")

# Choose in the array below the parameters that you want to plot
parameter = ['BoutDuration', 'TotalDistance', 'Speed', 'NumberOfOscillations', 'maxTailAngleAmplitude', 'meanTBF']
for idx, param in enumerate(parameter):
  # The "barplot" function below could be replaced, for example, by functions such as "boxplot" or "violinplot", depending on how you want the data to be plotted
  sns.barplot(ax=axes[int(idx/nbColumns)][int(idx%nbColumns)], x='Genotype', hue='Condition', y=param, data=dfParam)
  # axes[int(idx/nbColumns)][int(idx%nbColumns)].set_title(param) # Uncomment this line to get the title on the top of the graph

plt.show()
