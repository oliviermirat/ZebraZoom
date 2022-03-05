from pathlib import Path
import pandas as pd
import subprocess
import json
import sys
import os

from zebrazoom.kinematicParametersAnalysis import kinematicParametersAnalysis

def checkConsistencyOfParameters(listOfVideosToCheckConsistencyOn):
  
  cur_dir_path = os.path.dirname(os.path.realpath(__file__))
  cur_dir_path = Path(cur_dir_path)
  zebrazoom_path = cur_dir_path.parent
  
  data = []
  
  # Get these two from first vid in list if exists and tell user it will be applied for all videos
  # If not present in first video ask user for it
  videoFPS_forAllVideos       = -1
  videoPixelSize_forAllVideos = -1
  with open(os.path.join(os.path.join(os.path.join(zebrazoom_path, 'ZZoutput'), listOfVideosToCheckConsistencyOn[0]), 'configUsed.json')) as f:
    configFileFirstVideo = json.load(f)
  if not("videoFPS" in configFileFirstVideo):
    videoFPS_forAllVideos       = -1 # Need to prompt the user for input
  if not("videoPixelSize" in configFileFirstVideo):
    videoPixelSize_forAllVideos = -1 # Need to prompt the user for input
  
  for videoName in listOfVideosToCheckConsistencyOn:
    with open(os.path.join(os.path.join(os.path.join(zebrazoom_path, 'ZZoutput'), videoName), 'configUsed.json')) as f:
      configFile = json.load(f)
    nbWells        = configFile["nbWells"]
    videoFPS       = configFile["videoFPS"] if "videoFPS" in configFile else videoFPS_forAllVideos
    videoPixelSize = configFile["videoPixelSize"] if "videoPixelSize" in configFile else videoPixelSize_forAllVideos
    if videoFPS == -1 or videoPixelSize == -1:
      raise ValueError("videoFPS or videoPixelSize undefined: videoFPS:", str(videoFPS), ", videoPixelSize:", str(videoPixelSize))
    vidTab  = ["defaultZZoutputFolder", videoName, videoFPS, videoPixelSize, str([1 for i in range(nbWells)]), str(['Your data' for i in range(nbWells)]), str([1 for i in range(nbWells)])]
    data.append(vidTab)
  
  data.append(["defaultZZoutputFolder", 'standardValueFreelySwimZebrafishLarvae', 25, 1, str([1, 1, 1]), str(['StandardValue' for i in range(3)]), str([1 for i in range(3)])])
  
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
