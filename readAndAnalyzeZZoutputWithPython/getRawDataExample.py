from sklearn.preprocessing import MinMaxScaler
import zebrazoom.dataAPI as dataAPI
import matplotlib.pyplot as plt
import numpy as np
import pickle

videoName = "C:/Users/mirat/Desktop/openZZ/ZebraZoom/zebrazoom/ZZoutput/23.05.19.ac-12-f-1-2-vert-long1_2024_03_09-15_38_53.h5"
numWell   = 0

videoFPS = 160
videoPixelSize = 0.01
dataAPI.setFPSandPixelSize(videoName, videoFPS, videoPixelSize)

# Getting data
movementDataToExport = []
for numAnimal in [0, 1]:
  movementDataToExport.append(dataAPI.createExcelFileWithRawData(videoName, numWell, numAnimal, 1, 108288))

# Plot tail angles, heading and bad tracking / small fish indicators (tailLength and subsequentPointsDistance)
for mov in movementDataToExport:
  columns_to_plot = [['TailAngle', 'TailAngle_smoothed'], ['Heading'], ['TailLength', 'subsequentPointsDistance']]
  fig, axs = plt.subplots(3, 1)
  for i, columns in enumerate(columns_to_plot):
    if 'TailLength' in columns:
      scaler = MinMaxScaler()
      scaled_data = scaler.fit_transform(mov[['TailLength', 'subsequentPointsDistance']])
      axs[i].plot(mov.index, scaled_data[:, 0], label='Scaled TailLength')
      axs[i].scatter(mov.index, scaled_data[:, 1], label='Scaled subsequentPointsDistance', color='orange', marker='o')
      mov['Scaled_TailLength']               = scaled_data[:, 0]
      mov['Scaled_subsequentPointsDistance'] = scaled_data[:, 1]
    else:
      for column in columns:
        axs[i].plot(mov.index, mov[column], label=column)
    axs[i].set_title('Plot of ' + ', '.join(columns))
    axs[i].legend()
  plt.tight_layout()
  plt.show()

# Removing data for which the indicators are suggesting bad tracking / small fish
# for mov in movementDataToExport:
window_size = 5
for mov in movementDataToExport:
  new_column_values = []
  for i in range(len(mov)):
    start_index = max(0, int(i - window_size / 2))
    end_index = min(len(mov), int(i + window_size / 2))
    window_slice = mov[start_index:end_index]
    if any(window_slice['Scaled_TailLength'] < 0.45) or any(window_slice['Scaled_subsequentPointsDistance'] > 0.5):
      new_column_values.append(1)
    else:
      new_column_values.append(0)
  mov['fishTooSmall'] = new_column_values

movementDataToExport2 = movementDataToExport.copy()
for idx, mov in enumerate(movementDataToExport2):
  movementDataToExport2[idx].loc[mov['fishTooSmall'] != 0] = np.nan
  # rows_below_2_radians = movementDataToExport2[idx]['Heading'] < 2
  # movementDataToExport2[idx].loc[rows_below_2_radians, 'Heading'] += 2 * np.pi

def replace_outliers_with_nan(heading_series):
  window_size = 20
  heading_median = heading_series.rolling(window=window_size, center=True, min_periods=1).median()
  diff = np.abs(heading_series - heading_median)
  heading_series[diff >= 1.5] = np.nan
  return heading_series

for idx, mov in enumerate(movementDataToExport2):
  movementDataToExport2[idx]['Heading'] = replace_outliers_with_nan(movementDataToExport2[idx]['Heading'])

for idx, mov in enumerate(movementDataToExport2):
  columns_to_plot = [['TailAngle', 'TailAngle_smoothed'], ['Heading'], ['TailLength', 'subsequentPointsDistance']]
  fig, axs = plt.subplots(3, 1)
  for i, columns in enumerate(columns_to_plot):
    if 'TailLength' in columns:
      axs[i].plot(mov.index,    mov['TailLength'],               label='Scaled TailLength')
      axs[i].scatter(mov.index, mov['subsequentPointsDistance'], label='Scaled subsequentPointsDistance', color='orange', marker='o')
    else:
      for column in columns:
        axs[i].plot(mov.index, mov[column], label=column)
    axs[i].set_title('Plot of ' + ', '.join(columns))
    axs[i].legend()
  plt.tight_layout()
  plt.show()

for idx, mov in enumerate(movementDataToExport2):
  print(str((np.sum(~mov['Heading'].isna()) / len(mov)) * 100) + "% kept")
