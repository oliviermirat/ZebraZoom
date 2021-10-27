import tkinter as tk
from tkinter import font  as tkfont
from tkinter import filedialog
from tkinter import ttk
from tkinter import *
import cv2
import re
import os
import json
import shutil
import sys
import subprocess
import matplotlib
matplotlib.use("TkAgg")
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import math
import scipy.io as sio
from pathlib import Path
from zebrazoom.code.readValidationVideo import readValidationVideo
from zebrazoom.code.vars import getGlobalVariables
globalVariables = getGlobalVariables()

from zebrazoom.mainZZ import mainZZ
from zebrazoom.getTailExtremityFirstFrame import getTailExtremityFirstFrame
import zebrazoom.code.popUpAlgoFollow as popUpAlgoFollow

LARGE_FONT= ("Verdana", 12)

def chooseVideoToAnalyze(self, justExtractParams, noValidationVideo, debugMode=0):
    
    if globalVariables["mac"]:
        tk.videoName =  filedialog.askopenfilename(initialdir = os.path.expanduser("~"),title = "Select file")
    else:
        tk.videoName =  filedialog.askopenfilename(initialdir = os.path.expanduser("~"),title = "Select file",filetypes = (("video","*.*"),("all files","*.*")))
    tk.folderName = ''
    tk.headEmbedded = 0
    tk.sbatchMode = 0
    
    tk.justExtractParams = int(justExtractParams)
    tk.noValidationVideo = int(noValidationVideo)
    tk.debugMode         = int(debugMode)
    tk.findMultipleROIs = 0
    
    self.show_frame("ConfigFilePromp")

def chooseFolderToAnalyze(self, justExtractParams, noValidationVideo, sbatchMode):
    tk.folderName =  filedialog.askdirectory(initialdir = os.path.expanduser("~"),title = "Select folder")
    tk.headEmbedded = 0
    tk.justExtractParams = int(justExtractParams)
    tk.noValidationVideo = int(noValidationVideo)
    tk.sbatchMode        = int(sbatchMode)
    tk.debugMode = 0
    tk.findMultipleROIs = 0
    self.show_frame("ConfigFilePromp")
    
def chooseFolderForTailExtremityHE(self):
    tk.folderName =  filedialog.askdirectory(initialdir = os.path.expanduser("~"),title = "Select folder")
    tk.sbatchMode = 0
    tk.headEmbedded = 1
    tk.justExtractParams = 0
    tk.noValidationVideo = 0
    tk.debugMode = 0
    tk.findMultipleROIs = 0
    self.show_frame("ConfigFilePromp")

def chooseFolderForMultipleROIs(self):
    tk.folderName =  filedialog.askdirectory(initialdir = os.path.expanduser("~"),title = "Select folder")
    tk.sbatchMode = 0
    tk.headEmbedded = 0
    tk.justExtractParams = 0
    tk.noValidationVideo = 0
    tk.debugMode = 0
    tk.findMultipleROIs = 1
    self.show_frame("ConfigFilePromp")

def chooseConfigFile(self):
    
  cur_dir_path = os.path.dirname(os.path.realpath(__file__))
  path = Path(cur_dir_path)
  path = path.parent.parent
  path = os.path.join(path, 'configuration')
  
  if globalVariables["mac"]:
    tk.configFile =  filedialog.askopenfilename(initialdir = path, title = "Select file")
  else:
    tk.configFile =  filedialog.askopenfilename(initialdir = path, title = "Select file", filetypes = (("json files","*.json"),("all files","*.*")))
  if len(tk.folderName) or globalVariables["mac"] or globalVariables["lin"]:
    self.show_frame("Patience")
  else:
    self.launchZebraZoom()

def findAllFilesRecursivelyInDirectories(folderName):
  
  allVideos = []
  
  for name in os.listdir(folderName):
    if os.path.isdir(os.path.join(folderName, name)):
      allVideos2 = findAllFilesRecursivelyInDirectories(os.path.join(folderName, name))
      allVideos = allVideos + allVideos2
    else:
      if len(name) > 3:
        ext = os.path.splitext(name)[1]
        if len(ext):
          if (ext in ['.264', '.3g2', '.3gp', '.3gp2', '.3gpp', '.3gpp2', '.3mm', '.3p2', '.60d', '.787', '.89', '.aaf', '.aec', '.aep', '.aepx', '.aet', '.aetx', '.ajp', '.ale', '.am', '.amc', '.amv', '.amx', '.anim', '.aqt', '.arcut', '.arf', '.asf', '.asx', '.avb', '.avc', '.avd', '.avi', '.avp', '.avs', '.avs', '.avv', '.axm', '.bdm', '.bdmv', '.bdt2', '.bdt3', '.bik', '.bix', '.bmk', '.bnp', '.box', '.bs4', '.bsf', '.bvr', '.byu', '.camproj', '.camrec', '.camv', '.ced', '.cel', '.cine', '.cip', '.clpi', '.cmmp', '.cmmtpl', '.cmproj', '.cmrec', '.cpi', '.cst', '.cvc', '.cx3', '.d2v', '.d3v', '.dat', '.dav', '.dce', '.dck', '.dcr', '.dcr', '.ddat', '.dif', '.dir', '.divx', '.dlx', '.dmb', '.dmsd', '.dmsd3d', '.dmsm', '.dmsm3d', '.dmss', '.dmx', '.dnc', '.dpa', '.dpg', '.dream', '.dsy', '.dv', '.dv-avi', '.dv4', '.dvdmedia', '.dvr', '.dvr-ms', '.dvx', '.dxr', '.dzm', '.dzp', '.dzt', '.edl', '.evo', '.eye', '.ezt', '.f4p', '.f4v', '.fbr', '.fbr', '.fbz', '.fcp', '.fcproject', '.ffd', '.flc', '.flh', '.fli', '.flv', '.flx', '.gfp', '.gl', '.gom', '.grasp', '.gts', '.gvi', '.gvp', '.h264', '.hdmov', '.hkm', '.ifo', '.imovieproj', '.imovieproject', '.ircp', '.irf', '.ism', '.ismc', '.ismv', '.iva', '.ivf', '.ivr', '.ivs', '.izz', '.izzy', '.jss', '.jts', '.jtv', '.k3g', '.kmv', '.ktn', '.lrec', '.lsf', '.lsx', '.m15', '.m1pg', '.m1v', '.m21', '.m21', '.m2a', '.m2p', '.m2t', '.m2ts', '.m2v', '.m4e', '.m4u', '.m4v', '.m75', '.mani', '.meta', '.mgv', '.mj2', '.mjp', '.mjpg', '.mk3d', '.mkv', '.mmv', '.mnv', '.mob', '.mod', '.modd', '.moff', '.moi', '.moov', '.mov', '.movie', '.mp21', '.mp21', '.mp2v', '.mp4', '.mp4v', '.mpe', '.mpeg', '.mpeg1', '.mpeg4', '.mpf', '.mpg', '.mpg2', '.mpgindex', '.mpl', '.mpl', '.mpls', '.mpsub', '.mpv', '.mpv2', '.mqv', '.msdvd', '.mse', '.msh', '.mswmm', '.mts', '.mtv', '.mvb', '.mvc', '.mvd', '.mve', '.mvex', '.mvp', '.mvp', '.mvy', '.mxf', '.mxv', '.mys', '.ncor', '.nsv', '.nut', '.nuv', '.nvc', '.ogm', '.ogv', '.ogx', '.osp', '.otrkey', '.pac', '.par', '.pds', '.pgi', '.photoshow', '.piv', '.pjs', '.playlist', '.plproj', '.pmf', '.pmv', '.pns', '.ppj', '.prel', '.pro', '.prproj', '.prtl', '.psb', '.psh', '.pssd', '.pva', '.pvr', '.pxv', '.qt', '.qtch', '.qtindex', '.qtl', '.qtm', '.qtz', '.r3d', '.rcd', '.rcproject', '.rdb', '.rec', '.rm', '.rmd', '.rmd', '.rmp', '.rms', '.rmv', '.rmvb', '.roq', '.rp', '.rsx', '.rts', '.rts', '.rum', '.rv', '.rvid', '.rvl', '.sbk', '.sbt', '.scc', '.scm', '.scm', '.scn', '.screenflow', '.sec', '.sedprj', '.seq', '.sfd', '.sfvidcap', '.siv', '.smi', '.smi', '.smil', '.smk', '.sml', '.smv', '.spl', '.sqz', '.srt', '.ssf', '.ssm', '.stl', '.str', '.stx', '.svi', '.swf', '.swi', '.swt', '.tda3mt', '.tdx', '.thp', '.tivo', '.tix', '.tod', '.tp', '.tp0', '.tpd', '.tpr', '.trp', '.ts', '.tsp', '.ttxt', '.tvs', '.usf', '.usm', '.vc1', '.vcpf', '.vcr', '.vcv', '.vdo', '.vdr', '.vdx', '.veg','.vem', '.vep', '.vf', '.vft', '.vfw', '.vfz', '.vgz', '.vid', '.video', '.viewlet', '.viv', '.vivo', '.vlab', '.vob', '.vp3', '.vp6', '.vp7', '.vpj', '.vro', '.vs4', '.vse', '.vsp', '.w32', '.wcp', '.webm', '.wlmp', '.wm', '.wmd', '.wmmp', '.wmv', '.wmx', '.wot', '.wp3', '.wpl', '.wtv', '.wve', '.wvx', '.xej', '.xel', '.xesc', '.xfl', '.xlmv', '.xmv', '.xvid', '.y4m', '.yog', '.yuv', '.zeg', '.zm1', '.zm2', '.zm3', '.zmv']):
            allVideos.append(os.path.join(folderName, name))
  
  return allVideos


def launchZebraZoom(self):
  
  last = 0
  allVideos = []
  
  if tk.sbatchMode:
    commandsFile = open("commands.txt", "w")
    nbVideosToLaunch = 0
  
  if len(tk.folderName):
  
    allVideos = findAllFilesRecursivelyInDirectories(tk.folderName)
    
  else:
    allVideos = [tk.videoName]
  
  print("allVideos:", allVideos)
  
  for idx, text in enumerate(allVideos):
    
    path        = os.path.split(text)[0]
    nameWithExt = os.path.split(text)[1]
    name        = os.path.splitext(nameWithExt)[0]
    videoExt    = os.path.splitext(nameWithExt)[1][1:]
    
    if tk.headEmbedded == 0:
      if len(allVideos) == 1:
        tabParams = ["mainZZ", path, name, videoExt, tk.configFile, "freqAlgoPosFollow", 100, "popUpAlgoFollow", 1, "outputFolder", self.ZZoutputLocation]
      else:
        tabParams = ["mainZZ", path, name, videoExt, tk.configFile, "freqAlgoPosFollow", 100, "outputFolder", self.ZZoutputLocation]
      if tk.justExtractParams == 1:
        tabParams = tabParams + ["reloadWellPositions", 1, "reloadBackground", 1, "debugPauseBetweenTrackAndParamExtract", "justExtractParamFromPreviousTrackData"]
      if tk.noValidationVideo == 1:
          tabParams = tabParams + ["createValidationVideo", 0]
      if tk.debugMode == 1:
        tabParams = tabParams + ["debugTracking", 1, "debugExtractBack", 1, "onlyTrackThisOneWell", 0, "lastFrame", 5, "backgroundExtractionForceUseAllVideoFrames", 1, "noBoutsDetection", 1, "thresForDetectMovementWithRawVideo", 0, "noChecksForBoutSelectionInExtractParams", 1]
      if tk.findMultipleROIs == 1:
        tabParams = tabParams + ["exitAfterWellsDetection", 1, "saveWellPositionsToBeReloadedNoMatterWhat", 1]
      try:
        if tk.sbatchMode:
          commandsFile.write('python -m zebrazoom ' + ' '.join(tabParams[1:4]) + ' configFile.json\n')
          nbVideosToLaunch = nbVideosToLaunch + 1
        else:
          mainZZ(path, name, videoExt, tk.configFile, tabParams)
      except ValueError:
        print("moving on to the next video for ROIs identification")
      except NameError:
        self.show_frame("Error")
        return
    else:
      if tk.debugMode == 1:
        tabParams = ["mainZZ", path, name, videoExt, tk.configFile, "freqAlgoPosFollow", 100, "debugTracking", 1, "debugExtractBack", 1, "onlyDoTheTrackingForThisNumberOfFrames", 3, "onlyTrackThisOneWell", 0, "outputFolder", self.ZZoutputLocation]
      else:
        tabParams = ["outputFolder", self.ZZoutputLocation]
      getTailExtremityFirstFrame(path, name, videoExt, tk.configFile, tabParams)
  
  tk.headEmbedded      = 0
  tk.justExtractParams = 0
  tk.noValidationVideo = 0
  tk.debugMode         = 0
  tk.findMultipleROIs  = 0
  
  if tk.sbatchMode:
    
    commandsFile.close()
    
    with open(tk.configFile) as f:
      jsonFile = json.load(f)
    nbWells = jsonFile["nbWells"]
    
    launchFile = open("launchZZ.sh", "w")
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
    
    shutil.copy(tk.configFile, 'configFile.json')
    
    self.show_frame("ZZoutroSbatch")
    
  else:
    
    self.show_frame("ZZoutro")


def showValidationVideo(self, numWell, numAnimal, zoom, deb):

    cur_dir_path = os.path.dirname(os.path.realpath(__file__))
    path = Path(cur_dir_path)
    path = path.parent.parent
    filepath = os.path.join(path, os.path.join('ZZoutput', os.path.join(self.currentResultFolder, 'pathToVideo.txt')))
    
    if os.path.exists(filepath):
        with open(filepath) as fp:
           videoPath = fp.readline()
        videoPath = videoPath[:len(videoPath)-1]
    else:
        videoPath = ""
    
    readValidationVideo(videoPath, self.currentResultFolder, '.txt', int(numWell), int(numAnimal), int(zoom), int(deb), ZZoutputLocation=self.ZZoutputLocation)


def showGraphForAllBoutsCombined(self, numWell, numPoiss, dataRef, visualization, graphScaling):
  
  if (visualization == 0) or (visualization == 1):
  
    tailAngleFinal = []
    xaxisFinal = []
    if "firstFrame" in dataRef and "lastFrame" in dataRef:
      begMove = 0
      endMove = dataRef["wellPoissMouv"][numWell][numPoiss][0]["BoutStart"]
      xaxis     = [i for i in range(begMove, endMove)]
      tailAngle = [0 for i in range(begMove, endMove)]
      tailAngleFinal = tailAngleFinal + tailAngle
      xaxisFinal = xaxisFinal + xaxis
    for numMouv in range(0, len(dataRef["wellPoissMouv"][numWell][numPoiss])):
      if (visualization == 0):
        tailAngle = dataRef["wellPoissMouv"][numWell][numPoiss][numMouv]["TailAngle_smoothed"].copy()
      else:
        tailAngle = dataRef["wellPoissMouv"][numWell][numPoiss][numMouv]["TailAngle_Raw"].copy()
      for ind,val in enumerate(tailAngle):
        tailAngle[ind]=tailAngle[ind]*(180/(math.pi))
      begMove = dataRef["wellPoissMouv"][numWell][numPoiss][numMouv]["BoutStart"]
      endMove = begMove + len(tailAngle)
      xaxis = [i for i in range(begMove-1,endMove+1)]
      tailAngle.append(0)
      tailAngle.insert(0, 0)
      tailAngleFinal = tailAngleFinal + tailAngle
      xaxisFinal = xaxisFinal + xaxis
    if "firstFrame" in dataRef and "lastFrame" in dataRef:
      begMove = endMove
      endMove = dataRef["lastFrame"] - 1
      xaxis     = [i for i in range(begMove, endMove)]
      tailAngle = [0 for i in range(begMove, endMove)]
      tailAngleFinal = tailAngleFinal + tailAngle
      xaxisFinal = xaxisFinal + xaxis
    if "fps" in dataRef:
      plt.plot([xaxisFinalVal / dataRef["fps"] for xaxisFinalVal in xaxisFinal], tailAngleFinal)
    else:
      plt.plot(xaxisFinal, tailAngleFinal)
    if not(graphScaling):
      plt.ylim(-140, 140)
    if "firstFrame" in dataRef and "lastFrame" in dataRef:
      if "fps" in dataRef:
        plt.xlim(dataRef["firstFrame"] / dataRef["fps"], dataRef["lastFrame"] / dataRef["fps"])
      else:
        plt.xlim(dataRef["firstFrame"], dataRef["lastFrame"])
    plt.show()
    
  else:
    
    headXFinal = []
    headYFinal = []
    for numMouv in range(0, len(dataRef["wellPoissMouv"][numWell][numPoiss])):
      headXFinal = headXFinal + dataRef["wellPoissMouv"][numWell][numPoiss][numMouv]["HeadX"].copy()
      headYFinal = headYFinal + dataRef["wellPoissMouv"][numWell][numPoiss][numMouv]["HeadY"].copy()
    plt.plot(headXFinal, headYFinal)
    if not(graphScaling):
      plt.xlim(0, dataRef["wellPositions"][numWell]["lengthX"])
      plt.ylim(0, dataRef["wellPositions"][numWell]["lengthY"])
    plt.show()


def exploreResultFolder(self, currentResultFolder):
    
    self.currentResultFolder = currentResultFolder
    self.superstructmodified = 0
    self.justEnteredViewParameter = 1
    self.printSomeResults(0, 0, 0)


def printNextResults(self, numWell, numPoiss, numMouv, nbWells, nbPoiss, nbMouv):

    numWell  = int(numWell)
    numPoiss = int(numPoiss)
    numMouv  = int(numMouv)
    nbWells  = int(nbWells)
    nbPoiss  = int(nbPoiss)
    nbMouv   = int(nbMouv)
    
    if numMouv + 1 >= nbMouv:
        if numPoiss + 1 >= nbPoiss:
            if numWell + 1 < nbWells:
              numWell  = numWell + 1
              numPoiss = 0
              numMouv  = 0
        else:
            numPoiss = numPoiss + 1
            numMouv  = 0
    else:
        numMouv = numMouv + 1

    self.printSomeResults(numWell, numPoiss, numMouv)


def printPreviousResults(self, numWell, numPoiss, numMouv, nbWells, nbPoiss, nbMouv):

    numWell  = int(numWell)
    numPoiss = int(numPoiss)
    numMouv  = int(numMouv)
    nbWells  = int(nbWells)
    nbPoiss  = int(nbPoiss)
    nbMouv   = int(nbMouv)
    
    if numMouv - 1 < 0:
        if numPoiss - 1 < 0:
            if numWell - 1 >= 0:
                numWell = numWell - 1
                numPoiss = 100000
                numMouv = 10000000
        else:
            numPoiss = numPoiss - 1
            numMouv  = 0
    else:
        numMouv = numMouv - 1

    self.printSomeResults(numWell, numPoiss, numMouv)


def flagMove(self, numWell, numPoiss, numMouv):

    self.superstructmodified = 1

    name = self.currentResultFolder

    dataRef = self.dataRef
    
    if "flag" in dataRef["wellPoissMouv"][int(numWell)][int(numPoiss)][int(numMouv)]:
      dataRef["wellPoissMouv"][int(numWell)][int(numPoiss)][int(numMouv)]["flag"] = int(not(dataRef["wellPoissMouv"][int(numWell)][int(numPoiss)][int(numMouv)]["flag"]));
    else:
      dataRef["wellPoissMouv"][int(numWell)][int(numPoiss)][int(numMouv)]["flag"] = 1;
    
    self.dataRef = dataRef
    
    self.printSomeResults(numWell, numPoiss, numMouv)


def saveSuperStruct(self, numWell, numPoiss, numMouv):
    
    self.superstructmodified = 0
    
    name = self.currentResultFolder
    dataRef = self.dataRef
    
    cur_dir_path = os.path.dirname(os.path.realpath(__file__))
    path = Path(cur_dir_path)
    path = path.parent.parent
    reference = os.path.join(self.ZZoutputLocation, os.path.join(name, 'results_' + name + '.txt'))
    print("reference:", reference)
    
    with open(reference,'w') as out:
       json.dump(dataRef, out)
    
    self.dataRef = dataRef
    
    self.printSomeResults(numWell, numPoiss, numMouv)


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
