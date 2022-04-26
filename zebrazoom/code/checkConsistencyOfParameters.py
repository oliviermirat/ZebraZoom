import sys

from PyQt5.QtCore import Qt, QEventLoop
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QWidget, QApplication, QLabel, QPushButton, QLineEdit, QGridLayout, QRadioButton

from pathlib import Path
import pandas as pd
import subprocess
import json
import sys
import os

from zebrazoom.kinematicParametersAnalysis import kinematicParametersAnalysis

def getVideoFPSandPixelSizeThroughGUI(initialFPS, initialPixelSize, videoName):
  
  loop = QEventLoop()
  window = QWidget()
  window.setWindowTitle('Choose video fps and pixel size')
  window.setGeometry(100, 100, 280, 80)
  window.move(60, 15)

  layout = QGridLayout()
  videoFPS = QLineEdit(str(initialFPS))
  videoPixelSize = QLineEdit(str(initialPixelSize))
  setSameForAll = QRadioButton('set all videos to the same video fps and pixel size')
  okbutton = QPushButton('Ok')
  okbutton.clicked.connect(lambda: loop.exit())

  layout.addWidget(QLabel('<center><h3>' + videoName + '</h3></center>'), 0, 0, 1, 3)
  layout.addWidget(QLabel('videoFPS:'), 1, 0)
  layout.addWidget(videoFPS, 1, 1)
  layout.addWidget(QLabel('in Hz (1/second)'), 1, 2)
  layout.addWidget(QLabel('videoPixelSize:'), 2, 0)
  layout.addWidget(videoPixelSize, 2, 1)
  layout.addWidget(QLabel('in mm/pixel'), 2, 2)
  layout.addWidget(setSameForAll, 3, 0, 1, 3)
  layout.addWidget(okbutton, 4, 0, 1, 3)
  window.setLayout(layout)
  window.show()
  loop.exec()
  window.close()
  return [float(videoFPS.text()), float(videoPixelSize.text()), int(setSameForAll.isChecked())]

def checkConsistencyOfParameters(listOfVideosToCheckConsistencyOn):
  
  cur_dir_path = os.path.dirname(os.path.realpath(__file__))
  cur_dir_path = Path(cur_dir_path)
  zebrazoom_path = cur_dir_path.parent
  app = QApplication.instance()
  ZZoutputFolder = os.path.join(zebrazoom_path, 'ZZoutput') if app is None else app.ZZoutputLocation
  
  data = []
  
  videoFPS_forAllVideos       = -1
  videoPixelSize_forAllVideos = -1
  setSameForAll = False
  for videoName in listOfVideosToCheckConsistencyOn:
    with open(os.path.join(ZZoutputFolder, videoName, 'configUsed.json')) as f:
      configFile = json.load(f)
    nbWells        = configFile["nbWells"]
    # Checking / getting information about videoFPS and videoPixelSize
    if not(setSameForAll):
      videoFPS       = configFile["videoFPS"] if "videoFPS" in configFile else videoFPS_forAllVideos
      videoPixelSize = configFile["videoPixelSize"] if "videoPixelSize" in configFile else videoPixelSize_forAllVideos
      [videoFPS, videoPixelSize, setSameForAll] = getVideoFPSandPixelSizeThroughGUI(videoFPS, videoPixelSize, videoName)
      if setSameForAll:
        videoFPS_forAllVideos       = videoFPS
        videoPixelSize_forAllVideos = videoPixelSize
    else:
      videoFPS       = videoFPS_forAllVideos
      videoPixelSize = videoPixelSize_forAllVideos
    # Setting the videoFPS and videoPixelSize values inside the excel file
    vidTab  = ["defaultZZoutputFolder" if app is None else ZZoutputFolder, videoName, videoFPS, videoPixelSize, str([1 for i in range(nbWells)]), str(['Your data' for i in range(nbWells)]), str([1 for i in range(nbWells)])]
    data.append(vidTab)
  
  nbWellsStandardValues = 100
  data.append(["defaultZZoutputFolder", 'standardValueFreelySwimZebrafishLarvae', 1, 1, str([1 for i in range(nbWellsStandardValues)]), str(['StandardValues' for i in range(nbWellsStandardValues)]), str([1 for i in range(nbWellsStandardValues)])])
  excelFileDataFrame = pd.DataFrame(data=data, columns=['path', 'trial_id', 'fq', 'pixelsize', 'condition', 'genotype', 'include'])
  excelFileDataFrame.to_excel(os.path.join(os.path.join(os.path.join(zebrazoom_path, 'dataAnalysis'), 'experimentOrganizationExcel'), 'tempExcelFileForParametersConsistencyCheck.xls'))
  class sysSimulation:
    argv = []
  sysSimul = sysSimulation()
  sysSimul.argv = ['', '', '', os.path.join(os.path.join(os.path.join(zebrazoom_path, 'dataAnalysis'), 'experimentOrganizationExcel'), 'tempExcelFileForParametersConsistencyCheck.xls'), 4, -1, 1, -1, 0]
  kinematicParametersAnalysis(sysSimul, 0, True)
  dir_path = os.path.join(os.path.join(os.path.join(zebrazoom_path, 'dataAnalysis'), 'resultsKinematic'), 'tempExcelFileForParametersConsistencyCheck')
  if sys.platform == "win32":
    os.startfile(dir_path)
  else:
    opener ="open" if sys.platform == "darwin" else "xdg-open"
    subprocess.call([opener, dir_path])
