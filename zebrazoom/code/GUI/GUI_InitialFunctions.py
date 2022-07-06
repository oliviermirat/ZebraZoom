import cv2
import re
import os
import json
import shutil
import sys
import subprocess
from matplotlib.figure import Figure
import math
import scipy.io as sio
from zebrazoom.code.vars import getGlobalVariables
globalVariables = getGlobalVariables()

from zebrazoom.mainZZ import mainZZ
from zebrazoom.getTailExtremityFirstFrame import getTailExtremityFirstFrame
import zebrazoom.code.paths as paths
import zebrazoom.code.util as util

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QCheckBox, QFileDialog, QMessageBox, QVBoxLayout


LARGE_FONT= ("Verdana", 12)

def chooseVideoToAnalyze(self, justExtractParams, noValidationVideo, chooseFrames, testMode):
    self.videoName, _ = QFileDialog.getOpenFileName(self.window, 'Select file', os.path.expanduser("~"))
    if not self.videoName:
      return
    self.folderName = ''
    self.headEmbedded = 0
    self.sbatchMode = 0

    self.justExtractParams = int(justExtractParams)
    self.noValidationVideo = int(noValidationVideo)
    self.testMode         = testMode
    self.findMultipleROIs = 0
    self.askCoordinatesForAll = 1

    if chooseFrames:
      def beginningAndEndChosen():
        if "firstFrame" in self.configFile:
          self.firstFrame = self.configFile["firstFrame"]
        if "lastFrame" in self.configFile:
          self.lastFrame = self.configFile["lastFrame"]
        self.configFile.clear()
        self.backgroundExtractionForceUseAllVideoFrames = int(backgroundExtractionForceUseAllVideoFramesCheckbox.isChecked())
        self.show_frame("ConfigFilePromp")
      layout = QVBoxLayout()
      backgroundExtractionForceUseAllVideoFramesCheckbox = QCheckBox("Use all frames to calculate background")
      backgroundExtractionForceUseAllVideoFramesCheckbox.setChecked(True)
      layout.addWidget(backgroundExtractionForceUseAllVideoFramesCheckbox, alignment=Qt.AlignmentFlag.AlignCenter)
      util.chooseBeginningPage(self, self.videoName, "Choose where the analysis of your video should start.", "Ok, I want the tracking to start at this frame!",
                               lambda: util.chooseEndPage(self, self.videoName, "Choose where the analysis of your video should end.", "Ok, I want the tracking to end at this frame!", beginningAndEndChosen),
                               additionalLayout=layout)
    else:
      self.show_frame("ConfigFilePromp")

def chooseFolderToAnalyze(self, justExtractParams, noValidationVideo, sbatchMode):
    self.folderName =  QFileDialog.getExistingDirectory(self.window, 'Select folder', os.path.expanduser("~"))
    if not self.folderName:
      return
    self.headEmbedded = 0
    self.justExtractParams = int(justExtractParams)
    self.noValidationVideo = int(noValidationVideo)
    self.sbatchMode        = int(sbatchMode)
    self.testMode = False
    self.findMultipleROIs = 0
    self.askCoordinatesForAll = 1
    self.show_frame("ConfigFilePromp")

def chooseFolderForTailExtremityHE(self):
    self.folderName =  QFileDialog.getExistingDirectory(self.window, 'Select folder', os.path.expanduser("~"))
    if not self.folderName:
      return
    self.sbatchMode = 0
    self.headEmbedded = 1
    self.justExtractParams = 0
    self.noValidationVideo = 0
    self.testMode = False
    self.findMultipleROIs = 0
    self.askCoordinatesForAll = 1
    self.show_frame("ConfigFilePromp")

def chooseFolderForMultipleROIs(self, askCoordinatesForAll):
    self.folderName =  QFileDialog.getExistingDirectory(self.window, 'Select folder', os.path.expanduser("~"))
    if not self.folderName:
      return
    self.sbatchMode = 0
    self.headEmbedded = 0
    self.justExtractParams = 0
    self.noValidationVideo = 0
    self.testMode = False
    self.findMultipleROIs = 1
    self.askCoordinatesForAll = askCoordinatesForAll
    self.show_frame("ConfigFilePromp")

def chooseConfigFile(self):

  self.configFileName, _ = QFileDialog.getOpenFileName(self.window, 'Select file', paths.getConfigurationFolder(), "JSON (*.json)")
  if not self.configFileName:
    return
  if len(self.folderName) or globalVariables["mac"] or globalVariables["lin"]:
    self.show_frame("Patience")
  else:
    self.launchZebraZoom()

def findAllFilesRecursivelyInDirectories(folderName):
  extensions = {'.264', '.3g2', '.3gp', '.3gp2', '.3gpp', '.3gpp2', '.3mm', '.3p2', '.60d', '.787', '.89', '.aaf', '.aec', '.aep', '.aepx', '.aet', '.aetx', '.ajp', '.ale', '.am', '.amc', '.amv', '.amx', '.anim', '.aqt', '.arcut', '.arf', '.asf', '.asx', '.avb', '.avc', '.avd', '.avi', '.avp', '.avs', '.avs', '.avv', '.axm', '.bdm', '.bdmv', '.bdt2', '.bdt3', '.bik', '.bix', '.bmk', '.bnp', '.box', '.bs4', '.bsf', '.bvr', '.byu', '.camproj', '.camrec', '.camv', '.ced', '.cel', '.cine', '.cip', '.clpi', '.cmmp', '.cmmtpl', '.cmproj', '.cmrec', '.cpi', '.cst', '.cvc', '.cx3', '.d2v', '.d3v', '.dat', '.dav', '.dce', '.dck', '.dcr', '.dcr', '.ddat', '.dif', '.dir', '.divx', '.dlx', '.dmb', '.dmsd', '.dmsd3d', '.dmsm', '.dmsm3d', '.dmss', '.dmx', '.dnc', '.dpa', '.dpg', '.dream', '.dsy', '.dv', '.dv-avi', '.dv4', '.dvdmedia', '.dvr', '.dvr-ms', '.dvx', '.dxr', '.dzm', '.dzp', '.dzt', '.edl', '.evo', '.eye', '.ezt', '.f4p', '.f4v', '.fbr', '.fbr', '.fbz', '.fcp', '.fcproject', '.ffd', '.flc', '.flh', '.fli', '.flv', '.flx', '.gfp', '.gl', '.gom', '.grasp', '.gts', '.gvi', '.gvp', '.h264', '.hdmov', '.hkm', '.ifo', '.imovieproj', '.imovieproject', '.ircp', '.irf', '.ism', '.ismc', '.ismv', '.iva', '.ivf', '.ivr', '.ivs', '.izz', '.izzy', '.jss', '.jts', '.jtv', '.k3g', '.kmv', '.ktn', '.lrec', '.lsf', '.lsx', '.m15', '.m1pg', '.m1v', '.m21', '.m21', '.m2a', '.m2p', '.m2t', '.m2ts', '.m2v', '.m4e', '.m4u', '.m4v', '.m75', '.mani', '.meta', '.mgv', '.mj2', '.mjp', '.mjpg', '.mk3d', '.mkv', '.mmv', '.mnv', '.mob', '.mod', '.modd', '.moff', '.moi', '.moov', '.mov', '.movie', '.mp21', '.mp21', '.mp2v', '.mp4', '.mp4v', '.mpe', '.mpeg', '.mpeg1', '.mpeg4', '.mpf', '.mpg', '.mpg2', '.mpgindex', '.mpl', '.mpl', '.mpls', '.mpsub', '.mpv', '.mpv2', '.mqv', '.msdvd', '.mse', '.msh', '.mswmm', '.mts', '.mtv', '.mvb', '.mvc', '.mvd', '.mve', '.mvex', '.mvp', '.mvp', '.mvy', '.mxf', '.mxv', '.mys', '.ncor', '.nsv', '.nut', '.nuv', '.nvc', '.ogm', '.ogv', '.ogx', '.osp', '.otrkey', '.pac', '.par', '.pds', '.pgi', '.photoshow', '.piv', '.pjs', '.playlist', '.plproj', '.pmf', '.pmv', '.pns', '.ppj', '.prel', '.pro', '.prproj', '.prtl', '.psb', '.psh', '.pssd', '.pva', '.pvr', '.pxv', '.qt', '.qtch', '.qtindex', '.qtl', '.qtm', '.qtz', '.r3d', '.rcd', '.rcproject', '.rdb', '.rec', '.rm', '.rmd', '.rmd', '.rmp', '.rms', '.rmv', '.rmvb', '.roq', '.rp', '.rsx', '.rts', '.rts', '.rum', '.rv', '.rvid', '.rvl', '.sbk', '.sbt', '.scc', '.scm', '.scm', '.scn', '.screenflow', '.sec', '.sedprj', '.seq', '.sfd', '.sfvidcap', '.siv', '.smi', '.smi', '.smil', '.smk', '.sml', '.smv', '.spl', '.sqz', '.srt', '.ssf', '.ssm', '.stl', '.str', '.stx', '.svi', '.swf', '.swi', '.swt', '.tda3mt', '.tdx', '.thp', '.tivo', '.tix', '.tod', '.tp', '.tp0', '.tpd', '.tpr', '.trp', '.ts', '.tsp', '.ttxt', '.tvs', '.usf', '.usm', '.vc1', '.vcpf', '.vcr', '.vcv', '.vdo', '.vdr', '.vdx', '.veg','.vem', '.vep', '.vf', '.vft', '.vfw', '.vfz', '.vgz', '.vid', '.video', '.viewlet', '.viv', '.vivo', '.vlab', '.vob', '.vp3', '.vp6', '.vp7', '.vpj', '.vro', '.vs4', '.vse', '.vsp', '.w32', '.wcp', '.webm', '.wlmp', '.wm', '.wmd', '.wmmp', '.wmv', '.wmx', '.wot', '.wp3', '.wpl', '.wtv', '.wve', '.wvx', '.xej', '.xel', '.xesc', '.xfl', '.xlmv', '.xmv', '.xvid', '.y4m', '.yog', '.yuv', '.zeg', '.zm1', '.zm2', '.zm3', '.zmv'}
  for name in os.listdir(folderName):
    if os.path.isdir(os.path.join(folderName, name)):
      yield from findAllFilesRecursivelyInDirectories(os.path.join(folderName, name))
    else:
      if len(name) > 3:
        ext = os.path.splitext(name)[1]
        if ext in extensions:
            yield os.path.join(folderName, name)


def launchZebraZoom(self):
  if self.testMode:
    with open(self.configFileName) as f:
      self.configFile = json.load(f)
    self.videoToCreateConfigFileFor = self.videoName
    self.testConfig(addToHistory=False)
    self.headEmbedded      = 0
    self.justExtractParams = 0
    self.noValidationVideo = 0
    self.testMode         = False
    self.findMultipleROIs  = 0
    self.configFileName = None
    self.videoName = None
    return

  last = 0
  allVideos = []

  if self.sbatchMode:
    commandsFile = open(os.path.join(paths.getRootDataFolder(), "commands.txt"), "w", newline='\n')
    nbVideosToLaunch = 0

  if len(self.folderName):
    if self.askCoordinatesForAll:
      allVideos = list(findAllFilesRecursivelyInDirectories(self.folderName))
    else:
      videosGenerator = findAllFilesRecursivelyInDirectories(self.folderName)
      allVideos = [next(videosGenerator)]

  else:
    if (os.path.exists(self.videoName + 'HP.csv') or os.path.exists(self.videoName + '.csv')) and \
        QMessageBox.question(self.window, "Previously stored coordinates found", "Do you want to use the previously stored coordinates?",
                             defaultButton=QMessageBox.StandardButton.Yes) != QMessageBox.StandardButton.Yes:
      if os.path.exists(self.videoName + 'HP.csv'):
        os.remove(self.videoName + 'HP.csv')
      if os.path.exists(self.videoName + '.csv'):
        os.remove(self.videoName + '.csv')
    allVideos = [self.videoName]

  print("allVideos:", allVideos)

  for idx, text in enumerate(allVideos):

    path        = os.path.split(text)[0]
    nameWithExt = os.path.split(text)[1]
    name        = os.path.splitext(nameWithExt)[0]
    videoExt    = os.path.splitext(nameWithExt)[1][1:]

    if self.headEmbedded == 0:
      if len(allVideos) == 1:
        tabParams = ["mainZZ", path, name, videoExt, self.configFileName, "freqAlgoPosFollow", 100, "popUpAlgoFollow", 1, "outputFolder", self.ZZoutputLocation]
      else:
        tabParams = ["mainZZ", path, name, videoExt, self.configFileName, "freqAlgoPosFollow", 100, "outputFolder", self.ZZoutputLocation]
      if hasattr(self, "backgroundExtractionForceUseAllVideoFrames"):
        tabParams.extend(["backgroundExtractionForceUseAllVideoFrames", self.backgroundExtractionForceUseAllVideoFrames])
      if hasattr(self, "firstFrame"):
        tabParams.extend(["firstFrame", self.firstFrame])
      if hasattr(self, "lastFrame"):
        tabParams.extend(["lastFrame", self.lastFrame])
      if self.justExtractParams == 1:
        tabParams = tabParams + ["reloadWellPositions", 1, "reloadBackground", 1, "debugPauseBetweenTrackAndParamExtract", "justExtractParamFromPreviousTrackData"]
      if self.noValidationVideo == 1:
          tabParams = tabParams + ["createValidationVideo", 0]
      if self.findMultipleROIs == 1:
        tabParams = tabParams + ["exitAfterWellsDetection", 1, "saveWellPositionsToBeReloadedNoMatterWhat", 1]
      try:
        if self.sbatchMode:
          commandsFile.write('python -m zebrazoom ' + ' '.join(tabParams[1:4]).replace('\\', '/').replace('//lexport/iss02.', '/network/lustre/iss02/') + ' configFile.json\n')
          nbVideosToLaunch = nbVideosToLaunch + 1
        else:
          mainZZ(path, name, videoExt, self.configFileName, tabParams)
      except ValueError:
        print("moving on to the next video for ROIs identification")
      except NameError:
        self.show_frame("Error")
        return
    else:
      tabParams = ["outputFolder", self.ZZoutputLocation]
      if hasattr(self, "backgroundExtractionForceUseAllVideoFrames"):
        tabParams.extend(["backgroundExtractionForceUseAllVideoFrames", self.backgroundExtractionForceUseAllVideoFrames])
      if hasattr(self, "firstFrame"):
        tabParams.extend(["firstFrame", self.firstFrame])
      if hasattr(self, "lastFrame"):
        tabParams.extend(["lastFrame", self.lastFrame])
      getTailExtremityFirstFrame(path, name, videoExt, self.configFileName, tabParams)

  if self.findMultipleROIs and not self.askCoordinatesForAll:
    coordinatesFile = os.path.join(self.ZZoutputLocation, os.path.splitext(os.path.basename(allVideos[0]))[0], 'intermediaryWellPositionReloadNoMatterWhat.txt')
    for video in videosGenerator:
      folderPath = os.path.join(self.ZZoutputLocation, os.path.splitext(os.path.basename(video))[0])
      if not os.path.exists(folderPath):
        os.makedirs(folderPath)
      shutil.copy2(coordinatesFile, os.path.join(folderPath, 'intermediaryWellPositionReloadNoMatterWhat.txt'))
      shutil.copy2(coordinatesFile, os.path.join(folderPath, 'configUsed.json'))

  self.headEmbedded      = 0
  self.justExtractParams = 0
  self.noValidationVideo = 0
  self.testMode         = False
  self.findMultipleROIs  = 0
  self.askCoordinatesForAll = 1
  if hasattr(self, "backgroundExtractionForceUseAllVideoFrames"):
    del self.backgroundExtractionForceUseAllVideoFrames
  if hasattr(self, "firstFrame"):
    del self.firstFrame
  if hasattr(self, "lastFrame"):
    del self.lastFrame

  if self.sbatchMode:

    commandsFile.close()

    with open(self.configFileName) as f:
      jsonFile = json.load(f)
    nbWells = jsonFile["nbWells"]
    if nbWells > 24:
      nbWells = 24

    launchFile = open(os.path.join(paths.getRootDataFolder(), "launchZZ.sh"), "w", newline='\n')
    linesToWrite = ['#!/bin/sh',
                    '#SBATCH --ntasks=1',
                    '#SBATCH --cpus-per-task='+str(nbWells),
                    '#SBATCH --array=1-'+str(nbVideosToLaunch),
                    '#SBATCH --mem=16G',
                    '#SBATCH --time=23:00:00',
                    '#SBATCH --partition=normal',
                    '#SBATCH --job-name="ZebraZoom-protocole"',
                    '',
                    'module load python/3.8',
                    'source activate zebrazoom',
                    '',
                    'date',
                    '',
                    'export CMD_FILE_PATH=./commands.txt',
                    '',
                    'export CMD=$(sed -n ${SLURM_ARRAY_TASK_ID}p ${CMD_FILE_PATH})',
                    '',
                    'echo $CMD',
                    'eval $CMD',
                    '',
                    'date']
    linesToWrite = [line + '\n' for line in linesToWrite]
    launchFile.writelines(linesToWrite)
    launchFile.close()

    shutil.copy(self.configFileName, os.path.join(paths.getRootDataFolder(), 'configFile.json'))

    self.show_frame("ZZoutroSbatch")

  else:

    self.show_frame("ZZoutro")


def openConfigurationFileFolder(self, homeDirectory):
  dir_path = os.path.join(homeDirectory,'configuration')
  if sys.platform == "win32":
    os.startfile(dir_path)
  else:
    opener ="open" if sys.platform == "darwin" else "xdg-open"
    subprocess.call([opener, dir_path])


def openZZOutputFolder(self, homeDirectory):
  if len(self.ZZoutputLocation):
    dir_path = self.ZZoutputLocation
  else:
    dir_path = os.path.join(homeDirectory,'ZZoutput')
  if sys.platform == "win32":
    os.startfile(dir_path)
  else:
    opener ="open" if sys.platform == "darwin" else "xdg-open"
    subprocess.call([opener, dir_path])
