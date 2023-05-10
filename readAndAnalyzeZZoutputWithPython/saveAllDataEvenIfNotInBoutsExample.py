import os

import matplotlib.pyplot as plt
import pandas as pd


def _readFPSAndPixelSize(fname):
  headerRows = 0
  with open(fname) as f:
    line = f.readline()
    if line.startswith('videoFPS'):  # If videoFPS is stored in the file, read it
      videoFPS = float(line.split()[1])
      headerRows += 1
      line = f.readline()
    else:
      videoFPS = 300  # This value will be used if videoFPS is not stored in the file
    if line.startswith('videoPixelSize'):  # If videoPixelSize is stored in the file, read it
      videoPixelSize = float(line.split()[1])
      headerRows += 1
    else:
      videoPixelSize = 0.02  # This value will be used if videoPixelSize is not stored in the file
  return videoFPS, videoPixelSize, headerRows


if __name__ == '__main__':
  # One csv file should have been generated for each animal in each well inside the output data folder if "saveAllDataEvenIfNotInBouts" was set to 1 in the configuration file
  # To load the data for the specific video, well and animal combination the following values should be modified:
  ZZoutputPath = r'D:\ZebraZoom\ZZoutput'
  videoName = 'videoName'
  wellNumber = 0
  animalNumber = 0

  fname = os.path.join(ZZoutputPath, videoName, f'allData_{videoName}_wellNumber{wellNumber}_animal{animalNumber}.csv')
  videoFPS, videoPixelSize, headerRows = _readFPSAndPixelSize(fname)  # To use custom videoFPS and videoPixelSize values instead of the ones found in the file, uncomment the lines below and modify the values
  # videoFPS = 300
  # videoPixelSize = 0.02

  data = pd.read_csv(fname, skiprows=headerRows)
  tailLength = data['TailLength']  # The complete list of available columns can be found in the file, each row contains values for one frame

  fig, ax = plt.subplots()
  ax.scatter(range(len(tailLength)), tailLength * videoPixelSize)
  ax.set(xlabel='Frame', ylabel='Tail Length (in mm)', title='Tail Length per Frame')
  plt.show()
