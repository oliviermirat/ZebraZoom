from sklearn.preprocessing import MinMaxScaler
import zebrazoom.dataAPI as dataAPI
import matplotlib.pyplot as plt
import numpy as np
import pickle
import math

videoName = "C:/Users/mirat/Desktop/openZZ/ZebraZoom/zebrazoom/ZZoutput/23.05.19.ac-12-f-1-2-vert-long1_2024_03_09-15_38_53.h5"
numWell   = 0

videoFPS = 160
videoPixelSize = 0.128
dataAPI.setFPSandPixelSize(videoName, videoFPS, videoPixelSize)

saveFigs   = False
figsFormat = 'png' # 'svg'
angleOnlyWithPlusMinus90 = True

removeFishTooSmall = True
outlierRemovalForHeading = False

nbBins = 35

# Getting data
movementDataToExport = []
for numAnimal in [0, 1]:
  movementDataToExport.append(dataAPI.createExcelFileWithRawData(videoName, numWell, numAnimal, 1, 108288))

# Converting Heading to a more intuitive coordinate system
def convertHeadingToMoreIntuitiveCoordinateSystem(angle):
  angle = angle * (180 / math.pi)
  if not(angleOnlyWithPlusMinus90):
    if angle <= 180:
      return -angle
    else:
      return 360 - angle
  else:
    if angle <= 180:
      angle = -angle
    else:
      angle = 360 - angle
    if angle < -90:
      angle = -180 - angle
    if angle > 90:
      angle = 180 - angle
    return angle

for mov in movementDataToExport:
  mov['Heading'] = [convertHeadingToMoreIntuitiveCoordinateSystem(val) for val in mov['Heading'].tolist()]
  mov['TailAngle']          = (180 / math.pi) * mov['TailAngle']
  mov['TailAngle_smoothed'] = (180 / math.pi) * mov['TailAngle_smoothed']
  mov['HeadX']              = mov['HeadX'] * videoPixelSize
  mov['HeadY']              = ((90 / videoPixelSize) - mov['HeadY']) * videoPixelSize
  mov['TailLength']         = mov['TailLength'] * videoPixelSize

# Plot tail angles, heading and bad tracking / small fish indicators (tailLength and subsequentPointsDistance)
for fishNum, mov in enumerate(movementDataToExport):
  columns_to_plot = [['TailAngle', 'TailAngle_smoothed'], ['Heading'], ['TailLength', 'subsequentPointsDistance']]
  labels = [['Deflection angle', 'Smoothed deflection angle'], ['Pitch'], ['TailLength', 'Subsequent coordinates distance']]
  if saveFigs:
    fig, axs = plt.subplots(3, 1, figsize=(19, 10))
  else:
    fig, axs = plt.subplots(3, 1)
  for i, columns in enumerate(columns_to_plot):
    if 'TailLength' in columns:
      scaler = MinMaxScaler()
      scaled_data = scaler.fit_transform(mov[['TailLength', 'subsequentPointsDistance']])
      axs[i].plot(mov.index / videoFPS, scaled_data[:, 0], label='Scaled tail length')
      axs[i].scatter(mov.index / videoFPS, scaled_data[:, 1], label='Scaled subsequent coordinates distance', color='orange', marker='o')
      mov['Scaled_TailLength']               = scaled_data[:, 0]
      mov['Scaled_subsequentPointsDistance'] = scaled_data[:, 1]
    else:
      for j, column in enumerate(columns):
        axs[i].plot(mov.index / videoFPS, mov[column], label=labels[i][j])
    axs[i].set_title(', '.join(labels[i]))
    axs[i].legend()
  plt.tight_layout()
  if saveFigs:
    plt.savefig('Fish' + str(fishNum) + '_initial.' + figsFormat, format=figsFormat)
  else:
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
if removeFishTooSmall:
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

if outlierRemovalForHeading:
  for idx, mov in enumerate(movementDataToExport2):
    movementDataToExport2[idx]['Heading'] = replace_outliers_with_nan(movementDataToExport2[idx]['Heading'])

for idx, mov in enumerate(movementDataToExport2):
  columns_to_plot = [['TailAngle', 'TailAngle_smoothed'], ['Heading'], ['TailLength', 'subsequentPointsDistance']]
  labels = [['Deflection angle', 'Smoothed deflection angle'], ['Pitch'], ['TailLength', 'Subsequent coordinates distance']]
  if saveFigs:
    fig, axs = plt.subplots(3, 1, figsize=(19, 10))
  else:
    fig, axs = plt.subplots(3, 1)
  for i, columns in enumerate(columns_to_plot):
    if 'TailLength' in columns:
      axs[i].plot(mov.index / videoFPS,    mov['TailLength'],               label='Scaled TailLength')
      axs[i].scatter(mov.index / videoFPS, mov['subsequentPointsDistance'], label='Scaled subsequentPointsDistance', color='orange', marker='o')
    else:
      for j, column in enumerate(columns):
        axs[i].plot(mov.index / videoFPS, mov[column], label=labels[i][j])
    axs[i].set_title(', '.join(labels[i]))
    axs[i].legend()
  plt.tight_layout()
  if saveFigs:
    plt.savefig('Fish' + str(idx) + '_badPartsRemoved.' + figsFormat, format=figsFormat)
  else:
    plt.show()

for idx, mov in enumerate(movementDataToExport2):
  print(str((np.sum(~mov['Heading'].isna()) / len(mov)) * 100) + "% kept")

#####
#####
#####

from scipy.fft import fft, fftfreq

###

for idx, mov in enumerate(movementDataToExport2):
  columns_to_plot = [['TailAngle', 'TailAngle_smoothed'], ['Heading'], ['TailLength'], [ 'HeadY']]
  labels = [['Deflection angle', 'Smoothed deflection angle'], ['Pitch'], ['Tail length'], ['Vertical position']]
  if saveFigs:
    fig, axs = plt.subplots(4, 1, figsize=(19, 10))
  else:
    fig, axs = plt.subplots(4, 1)
  for i, columns in enumerate(columns_to_plot):
    for j, column in enumerate(columns):
      axs[i].plot(mov.index / videoFPS, mov[column], label=labels[i][j])
    axs[i].set_title(', '.join(labels[i]))
    axs[i].legend()
  plt.tight_layout()
  if saveFigs:
    plt.savefig('Fish' + str(idx) + '_badPartsRemoved2.' + figsFormat, format=figsFormat)
  else:
    plt.show()


def plotTailAngleFFT(plotNumber, animalNumber, startSection, endSection):
  
  mov = movementDataToExport2[animalNumber] #[startSection:endSection]
  columns_to_plot = [['HeadY', 'HeadX'], ['TailAngle', 'TailAngle_smoothed'], ['Heading'], ['TailLength']]
  labels = [['Vertical position', 'Horizontal position'], ['Deflection angle', 'Smoothed deflection angle'], ['Pitch'], ['TailLength']]
  if saveFigs:
    fig, axs = plt.subplots(4, 1, figsize=(19, 10))
  else:
    fig, axs = plt.subplots(4, 1)
  for i, columns in enumerate(columns_to_plot):
    for j, column in enumerate(columns):
      axs[i].plot(mov.index / videoFPS, mov[column], label=labels[i][j])
    axs[i].set_title(', '.join(labels[i]))
    axs[i].legend()
  plt.tight_layout()
  if saveFigs:
    plt.savefig('Fish' + str(animalNumber) + '_period' + str(plotNumber) + '_frames_' + str(startSection) + '_to_' + str(endSection) + '.' + figsFormat, format=figsFormat)
  else:
    plt.show()

  # Fourrier transform on not nan sections of the tail angle
  if saveFigs:
    fig, axs = plt.subplots(1, 1, figsize=(19, 10))
  else:
    fig, axs = plt.subplots(1, 1)
  notNanSections = ~np.isnan(mov['HeadY'])
  tailAngleNotNan = mov['TailAngle'][notNanSections].copy().tolist()
  N = len(tailAngleNotNan)
  T = 1/160
  xf = fftfreq(N, T)[:N//2]
  yf0 = fft(tailAngleNotNan)
  plt.plot(xf, 2.0/N * np.abs(yf0[0:N//2]))
  plt.grid()
  if saveFigs:
    plt.savefig('Fish' + str(animalNumber) + '_period' + str(plotNumber) + '_frames_' + str(startSection) + '_to_' + str(endSection) + '_FFT.' + figsFormat, format=figsFormat)
  else:
    plt.show()
  
  return mov['Heading']

Heading = []
Heading.append(movementDataToExport2[0]['Heading'].tolist())
Heading.append(movementDataToExport2[1]['Heading'].tolist())

def removeSubsection(animalNumber, startSection, endSection):
  Heading[animalNumber] = Heading[animalNumber][:startSection] + Heading[animalNumber][endSection:]

removeSubsection(0, 105540, 108000)
removeSubsection(0, 80530,  82600)
removeSubsection(0, 72690,  73180)
removeSubsection(0, 62800,  65580)
removeSubsection(0, 7850,   8340)

removeSubsection(1, 96550, 97775)
removeSubsection(1, 66100, 68750)
removeSubsection(1, 44750, 46220)
removeSubsection(1, 28600, 29770)
removeSubsection(1, 11950, 12900)


# All

if saveFigs:
  fig, axs = plt.subplots(1, 1, figsize=(19, 10))
else:
  fig, axs = plt.subplots(1, 1)
mov = Heading[0] + Heading[1]
mov = [x for x in mov if not math.isnan(x)]
print(len(mov))
plt.hist(mov, bins=nbBins, color='blue', edgecolor='black')
plt.xlabel('Pitch')
plt.ylabel('Frequency')
plt.title('Pitch')
if saveFigs:
  plt.savefig('PitchHistogramBothFish.' + figsFormat, format=figsFormat)
else:
  plt.show()
