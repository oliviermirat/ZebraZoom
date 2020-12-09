import tkinter as tk
from tkinter import font  as tkfont
from tkinter import filedialog
from tkinter import ttk
from tkinter import *
import re
import os
import json
import subprocess
import matplotlib
matplotlib.use("TkAgg")
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

def chooseVideoToAnalyze(self, justExtractParams, noValidationVideo):
    
    if globalVariables["mac"]:
        tk.videoName =  filedialog.askopenfilename(initialdir = os.path.expanduser("~"),title = "Select file")
    else:
        tk.videoName =  filedialog.askopenfilename(initialdir = os.path.expanduser("~"),title = "Select file",filetypes = (("video","*.*"),("all files","*.*")))
    tk.folderName = ''
    tk.headEmbedded = 0
    
    tk.justExtractParams = int(justExtractParams)
    tk.noValidationVideo = int(noValidationVideo)
    
    self.show_frame("ConfigFilePromp")

def chooseFolderToAnalyze(self, justExtractParams, noValidationVideo):
    tk.folderName =  filedialog.askdirectory(initialdir = os.path.expanduser("~"),title = "Select folder")
    tk.headEmbedded = 0
    tk.justExtractParams = int(justExtractParams)
    tk.noValidationVideo = int(noValidationVideo)
    self.show_frame("ConfigFilePromp")
    
def chooseFolderForTailExtremityHE(self):
    tk.folderName =  filedialog.askdirectory(initialdir = os.path.expanduser("~"),title = "Select folder")
    tk.headEmbedded = 1
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
    if globalVariables["mac"] or globalVariables["lin"]:
        self.show_frame("Patience")
    else:
        self.launchZebraZoom()

def launchZebraZoom(self):
  
  last = 0
  allVideos = []
  
  if len(tk.folderName):
    for name in os.listdir(tk.folderName):
      if len(name) > 3:
        ext = name[len(name)-3:len(name)]
        if (ext == 'mp4') or (ext == 'avi'):
          allVideos.append(tk.folderName+'/'+name)
  else:
    allVideos = [tk.videoName]
  
  for idx, text in enumerate(allVideos):
    for m in re.finditer('/', text):
      last = m.start()
    path        = text[:last+1]
    nameWithExt = text[last+1:]
    pointPos = nameWithExt.find('.')
    name     = nameWithExt[:pointPos]
    videoExt = nameWithExt[pointPos+1:]
    
    if tk.headEmbedded == 0:
      tabParams = ["mainZZ", path, name, videoExt, tk.configFile, "freqAlgoPosFollow", 100, "popUpAlgoFollow", 1]
      if tk.justExtractParams == 1:
        tabParams = tabParams + ["reloadWellPositions", 1, "reloadBackground", 1, "debugPauseBetweenTrackAndParamExtract", "justExtractParamFromPreviousTrackData"]
      if tk.noValidationVideo == 1:
          tabParams = tabParams + ["createValidationVideo", 0]
      mainZZ(path, name, videoExt, tk.configFile, tabParams)
    else:
      getTailExtremityFirstFrame(path, name, videoExt, tk.configFile, [])
  
  self.show_frame("ZZoutro")


def showValidationVideo(self, numWell, zoom, deb):

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
    
    readValidationVideo(videoPath, self.currentResultFolder, '.txt', int(numWell), int(zoom), int(deb))
    

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
    reference = os.path.join(path, os.path.join('ZZoutput', os.path.join(name, 'results_' + name + '.txt')))
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
  dir_path = os.path.join(homeDirectory,'ZZoutput')
  if sys.platform == "win32":
    os.startfile(dir_path)
  else:
    opener ="open" if sys.platform == "darwin" else "xdg-open"
    subprocess.call([opener, dir_path])  
