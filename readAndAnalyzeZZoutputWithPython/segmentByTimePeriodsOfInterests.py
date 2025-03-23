import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np
import math
import re


# Parameters to adjust if necessary

pklFileName = 'example'

computeMedianValuesForEachVideoWellTimeframe = True

fps = 25

timePeriodsOfInterest = [{"periodName": "First10mins",
                          "start":   0 * 60 * fps,         # the unit is in frame number
                          "finish": 10 * 60 * fps}, # the unit is in frame number
                         {"periodName": "Last10mins",
                          "start":  20 * 60 * fps,        # the unit is in frame number
                          "finish": 30 * 60 * fps}] # the unit is in frame number

globParamForPlot = ['Bout Duration (s)', 'Bout Distance (mm)', 'Bout Speed (mm/s)', 'Angular Velocity (deg/s)', 'Absolute Yaw (deg) (from heading vals)', 'headingRangeWidth']


# Loading data and setting the condition column to the time period

kinematicParameters = pd.read_pickle(pklFileName + '.pkl')

_ALPHABET_REGEX = re.compile(r'[^a-zA-Z]+')
_SORT_PRIORITY = {'wt': 0, 'ctrl': 0, 'ctrls': 0, 'controls': 0, 'control': 0, 'wildtype': 0, 'wildtypes': 0,
                  'het': 1, 'heterozygote': 1, 'heterozygotes': 1,
                  'mut': 2, 'mutant': 2, 'mutants': 2}

def sortGenotypes(genotypes):
  def key(genotype):
    if not isinstance(genotype, str):
      return float('inf'), genotype
    return _SORT_PRIORITY.get(re.sub(_ALPHABET_REGEX, '', genotype).casefold(), float('inf')), genotype
  return sorted(genotypes, key=key)

kinematicParameters['Condition'] = None
for period in timePeriodsOfInterest:
  period_name = period['periodName']
  start_time = period['start']
  finish_time = period['finish']
  condition_rows = kinematicParameters[(kinematicParameters['BoutStart'] >= start_time) & 
                                       (kinematicParameters['BoutStart'] <= finish_time)]
  kinematicParameters.loc[condition_rows.index, 'Condition'] = period_name
kinematicParameters = kinematicParameters.dropna(subset=['Condition'])


# Getting medians of parameters within each group

if computeMedianValuesForEachVideoWellTimeframe:
  group_columns = ['Trial_ID', 'Well_ID', 'Condition', 'Genotype']
  median_df = kinematicParameters.groupby(group_columns)[globParamForPlot].median().reset_index()
  kinematicParameters = median_df


# Plotting

plotMean = True
plotOutliers = False

genotypes = kinematicParameters["Genotype"].unique().tolist()
palette = dict(zip(sortGenotypes(genotypes), sns.color_palette(n_colors=len(genotypes))))

nbLines   = int(math.sqrt(len(globParamForPlot)))
nbColumns = math.ceil(len(globParamForPlot) / nbLines)
fig, tabAx = plt.subplots(nbLines, nbColumns, figsize=(22.9, 8.8))
fig.tight_layout(pad=4.0)
for idx, parameter in enumerate(globParamForPlot):
  print("plotting parameter:", parameter)
  
  tabToPlot = 0
  if nbLines == 1:
    if nbColumns == 1:
      tabToPlot = tabAx
    else:
      tabToPlot = tabAx[idx%nbColumns]
  else:
    tabToPlot = tabAx[int(idx/nbColumns), idx%nbColumns]

  if kinematicParameters[parameter].dropna().empty:
    tabToPlot.text(.5, .5, 'Data could not be plotted.', ha='center')
    tabToPlot.axis('off')
    b = tabToPlot
  else:
    b = sns.boxplot(ax=tabToPlot, data=kinematicParameters, x="Condition", y=parameter, hue="Genotype", showmeans=plotMean, showfliers=plotOutliers, palette=palette, hue_order=palette.keys(), medianprops={"color": "r"})
  
  
  b.set_ylabel('', fontsize=0)
  b.set_xlabel('', fontsize=0)
  b.axes.set_title(parameter,fontsize=10)

plt.show()
