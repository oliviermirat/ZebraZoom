import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
import numpy as np
import math
import re


# Parameters to adjust if necessary

loadAndTransformPkl = True
plotData            = True
computeMedianValuesForEachVideoWellTimeframe = True

pklFileName = '../zebrazoom/dataAnalysis/data/madeByElim' # The pkl file referenced here is stored in the folder accessible from the button "View raw data" on the kinematic parameters visualization page

fps = 25

timePeriodsOfInterest = [{"periodName": "0minTo10min",
                          "start":   0 * 60 * fps,         # the unit is in frame number
                          "finish": 10 * 60 * fps}, # the unit is in frame number
                         {"periodName": "10minTo20min",
                          "start":  10 * 60 * fps,        # the unit is in frame number
                          "finish": 20 * 60 * fps}, 
                         {"periodName": "20minTo30min",
                          "start":  20 * 60 * fps,        # the unit is in frame number
                          "finish": 30 * 60 * fps}] # the unit is in frame number

globParamForPlot = ['Bout Duration (s)', 'Bout Distance (mm)', 'Bout Speed (mm/s)', 'Angular Velocity (deg/s)', 'Absolute Yaw (deg) (from heading vals)', 'headingRangeWidth']

SFSvsTurnsThreshold = 20

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


# Loading data and setting the condition column to the time period

if loadAndTransformPkl:

  kinematicParameters = pd.read_pickle(pklFileName + '.pkl')

  kinematicParameters['Condition'] = None
  for period in timePeriodsOfInterest:
    period_name = period['periodName']
    start_time = period['start']
    finish_time = period['finish']
    condition_rows = kinematicParameters[(kinematicParameters['BoutStart'] >= start_time) & 
                                         (kinematicParameters['BoutStart'] <= finish_time)]
    kinematicParameters.loc[condition_rows.index, 'Condition'] = period_name

  kinematicParameters['SFSvsTurns'+str(SFSvsTurnsThreshold)+'Thresh'] = kinematicParameters['Absolute Yaw (deg) (from heading vals)'].apply(
    lambda x: 'SFS' if pd.notna(x) and x < SFSvsTurnsThreshold else ('Turn' if pd.notna(x) else None)
  )

  # Create subset DataFrames
  kinematicParameters_subset = kinematicParameters[:3000]

  # Define genotype filters
  genotype_filters = {
      'all': lambda df: df,
      'WT': lambda df: df[df['Genotype'] == 'WT'],
      'HTZ': lambda df: df[df['Genotype'] == 'HTZ'],
      'MT': lambda df: df[df['Genotype'] == 'MT'],
  }

  # Save first Excel file with 3000 lines
  with pd.ExcelWriter('kinPar_3000lines_fastOpen.xlsx') as writer:
      for sheet_name, filter_func in genotype_filters.items():
          filtered_df = filter_func(kinematicParameters_subset)
          filtered_df.to_excel(writer, sheet_name=sheet_name, index=False)

  # Save full Excel file
  with pd.ExcelWriter('kinematicParameters.xlsx') as writer:
      for sheet_name, filter_func in genotype_filters.items():
          filtered_df = filter_func(kinematicParameters)
          filtered_df.to_excel(writer, sheet_name=sheet_name, index=False)


# Plotting

if plotData:

  if not(loadAndTransformPkl):
    kinematicParameters = pd.read_excel('kinematicParameters.xlsx', sheet_name='all')
    
  if computeMedianValuesForEachVideoWellTimeframe:
    group_columns = ['Trial_ID', 'Well_ID', 'Condition', 'Genotype']
    median_df = kinematicParameters.groupby(group_columns)[globParamForPlot].median().reset_index()
    kinematicParameters = median_df
  
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
      if not(computeMedianValuesForEachVideoWellTimeframe):
        b = sns.boxplot(ax=tabToPlot, data=kinematicParameters, x="Condition", y=parameter, hue="Genotype", showmeans=plotMean, showfliers=plotOutliers, palette=palette, hue_order=palette.keys(), medianprops={"color": "r"})
      else:
        b = sns.boxplot(ax=tabToPlot,
                data=kinematicParameters,
                x="Condition",
                y=parameter,
                hue="Genotype",
                showmeans=plotMean,
                showfliers=plotOutliers,
                palette=palette,
                hue_order=palette.keys(),
                medianprops={"color": "r"})
        # Overlay scatter plot
        sns.stripplot(ax=tabToPlot,
                      data=kinematicParameters,
                      x="Condition",
                      y=parameter,
                      hue="Genotype",
                      dodge=True,
                      jitter=True,
                      alpha=0.5,
                      palette=palette,
                      hue_order=palette.keys(),
                      marker='o',
                      size=3,
                      edgecolor='black',
                      linewidth=0.4,
                      legend=False)
        # Remove duplicate legend entries in the subplot
        if idx == 0:  # Do this once, for one subplot only
            handles, labels = tabToPlot.get_legend_handles_labels()
            fig.legend(handles[:len(palette)], labels[:len(palette)], loc='upper right')
        else:
            tabToPlot.get_legend().remove()

        
    b.set_ylabel('', fontsize=0)
    b.set_xlabel('', fontsize=0)
    b.axes.set_title(parameter,fontsize=10)

  plt.show()
