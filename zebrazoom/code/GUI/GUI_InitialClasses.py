from pathlib import Path
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
from zebrazoom.code.readValidationVideo import readValidationVideo
import numpy as np
import webbrowser

from zebrazoom.code.vars import getGlobalVariables
globalVariables = getGlobalVariables()

from zebrazoom.mainZZ import mainZZ
from zebrazoom.getTailExtremityFirstFrame import getTailExtremityFirstFrame
import zebrazoom.code.popUpAlgoFollow as popUpAlgoFollow

LARGE_FONT= ("Verdana", 12)


class FullScreenApp(object):
    def __init__(self, master, **kwargs):
        self.master=master
        pad=3
        self._geom='200x200+0+0'
        master.geometry("{0}x{1}+0+0".format(
            master.winfo_screenwidth()-pad, master.winfo_screenheight()-pad))
        master.bind('<Escape>',self.toggle_geom)            
    def toggle_geom(self,event):
        geom=self.master.winfo_geometry()
        print(geom,self._geom)
        self.master.geometry(self._geom)
        self._geom=geom


class StartPage(tk.Frame):

    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        self.controller = controller
        
        self.columnconfigure(0, weight=1)
        self.columnconfigure(1, weight=1)
        self.columnconfigure(2, weight=1)
        
        # tk.Label(self, text="Welcome to ZebraZoom!", font=controller.title_font).pack()
        
        # tk.Label(self, text="1 - Configuration File Creation", pady=10).pack()
        
        # tk.Button(self, text="Prepare configuration file for tracking", command=lambda: controller.show_frame("ChooseVideoToCreateConfigFileFor")).pack()
        # tk.Label(self, text="You first need to create a configuration file for each 'type' of video you want to track.").pack(side=tk.RIGHT)
        
        # tk.Button(self, text="Open configuration file folder", command=lambda: controller.openConfigurationFileFolder(controller.homeDirectory)).pack(side=tk.BOTTOM)
        # tk.Label(self, text="You can access the folder where configuration files are saved with this button.").pack(side=tk.RIGHT)

        tk.Label(self, text="Welcome to ZebraZoom!", font=controller.title_font, pady=20, fg="purple").grid(row=0,column=0, columnspan = 2)
        
        tk.Label(self, text="1 - Create a Configuration File:", font = "bold", pady=10, fg="blue").grid(row=1,column=0)
        tk.Button(self, text="Prepare configuration file for tracking", command=lambda: controller.show_frame("ChooseVideoToCreateConfigFileFor"), bg="light yellow").grid(row=2,column=0)
        tk.Label(self, text="You first need to create a configuration file for each 'type' of video you want to track.", pady=10, fg="green").grid(row=3,column=0)
        tk.Button(self, text="Open configuration file folder", command=lambda: controller.openConfigurationFileFolder(controller.homeDirectory), bg="light yellow").grid(row=4,column=0)
        tk.Label(self, text="Access the folder where configuration files are saved with the button above.", pady=10, fg="green").grid(row=5,column=0)
        tk.Label(self, text="").grid(row=6,column=0)
        
        tk.Label(self, text="2 - Run the Tracking:", font = "bold", pady=10, fg="blue").grid(row=1,column=1)
        tk.Button(self, text="Run ZebraZoom's Tracking on a video", command=lambda: controller.show_frame("VideoToAnalyze"), bg="light yellow").grid(row=2,column=1)
        tk.Label(self, text="Once you have a configuration file, use it to track a video.", pady=10, fg="green").grid(row=3,column=1)
        tk.Button(self, text="Run ZebraZoom's Tracking on several videos", command=lambda: controller.show_frame("SeveralVideos"), bg="light yellow").grid(row=4,column=1)
        tk.Label(self, text="Or run the tracking on all videos inside a folder.", pady=10, fg="green").grid(row=5,column=1)
        
        tk.Label(self, text="3 - Verify tracking results:", font = "bold", pady=10, fg="blue").grid(row=7,column=0)
        tk.Button(self, text="Open ZebraZoom's output folder", command=lambda: controller.openZZOutputFolder(controller.homeDirectory), bg="light yellow").grid(row=8,column=0)
        tk.Label(self, text="Access the folder where the tracking results are saved with the button above.", pady=10, fg="green").grid(row=9,column=0)
        tk.Button(self, text="Visualize ZebraZoom's output", command=lambda: controller.showResultsVisualization(), bg="light yellow").grid(row=10,column=0)
        tk.Label(self, text="Visualize/Verify/Explore the tracking results with the button above.", pady=10, fg="green").grid(row=11,column=0)
        
        tk.Label(self, text="4 - Analyze behavior:", font = "bold", pady=10, fg="blue").grid(row=7,column=1)
        tk.Button(self, text="Analyze ZebraZoom's outputs", command=lambda: controller.show_frame("CreateExperimentOrganizationExcel"), bg="light yellow").grid(row=8,column=1)
        tk.Label(self, text="Compare populations based on either kinematic parameters or clustering of bouts.", pady=10, fg="green").grid(row=9,column=1)
        
        tk.Label(self, text="").grid(row=12,column=0, columnspan = 2)
        tk.Button(self, text="Troubleshoot", command=lambda: controller.show_frame("ChooseVideoToTroubleshootSplitVideo"), bg="light cyan").grid(row=13,column=0, columnspan = 2)
        
        def callback(url):
            webbrowser.open_new(url)
        
        link1 = tk.Button(self, text="Video online documentation", bg="light cyan")
        link1.grid(row=14,column=0, columnspan = 2)
        link1.bind("<Button-1>", lambda e: callback("https://github.com/oliviermirat/ZebraZoom#tableofcontent"))
        

class SeveralVideos(tk.Frame):

    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        self.controller = controller
        label = tk.Label(self, text="Run ZebraZoom on several videos", font=controller.title_font)
        label.pack(side="top", fill="x", pady=10)
            
        button3 = tk.Button(self, text="Run ZebraZoom on an entire folder",
                            command=lambda: controller.show_frame("FolderToAnalyze")).pack()
        
        tk.Label(self, text="", font=controller.title_font).pack()
        
        button4 = tk.Button(self, text="Manual first frame tail extremity for head embedded",
                            command=lambda: controller.show_frame("TailExtremityHE")).pack()
        tk.Label(self, text="", font=controller.title_font).pack()
                            
        tk.Button(self, text="Go to the start page", command=lambda: controller.show_frame("StartPage")).pack()


class VideoToAnalyze(tk.Frame):

    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        self.controller = controller
        label = tk.Label(self, text="Choose video.", font=controller.title_font)
        label.pack(side="top", fill="x", pady=10)
        tk.Label(self, text="Look for the video you want to analyze.").pack(side="top", fill="x", pady=10)
        justExtractParams = IntVar()
        noValidationVideo = IntVar()
        button = tk.Button(self, text="Choose file",
                           command=lambda: controller.chooseVideoToAnalyze(justExtractParams.get(), noValidationVideo.get()))
        button.pack()
        
        Checkbutton(self, text="I ran the tracking already, I only want to redo the extraction of parameters.", variable=justExtractParams).pack()
        tk.Label(self, text="", pady=0).pack()
        Checkbutton(self, text="Don't (re)generate a validation video (for speed efficiency).", variable=noValidationVideo).pack()
        tk.Label(self, text="", pady=0).pack()
        
        tk.Button(self, text="Go to the start page", command=lambda: controller.show_frame("StartPage")).pack()


class FolderToAnalyze(tk.Frame):

    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        self.controller = controller
        label = tk.Label(self, text="Choose folder.", font=controller.title_font)
        label.pack(side="top", fill="x", pady=10)
        tk.Label(self, text="Look for the folder you want to analyze.").pack(side="top", fill="x", pady=10)
        justExtractParams = IntVar()
        noValidationVideo = IntVar()
        button = tk.Button(self, text="Choose folder",
                           command=lambda: controller.chooseFolderToAnalyze(justExtractParams.get(), noValidationVideo.get()))
        button.pack()
        
        Checkbutton(self, text="I ran the tracking already, I only want to redo the extraction of parameters.", variable=justExtractParams).pack()
        tk.Label(self, text="", pady=0).pack()
        
        Checkbutton(self, text="Don't (re)generate a validation video (for speed efficiency).", variable=noValidationVideo).pack()
        tk.Label(self, text="", pady=0).pack()
        
        tk.Button(self, text="Go to the start page", command=lambda: controller.show_frame("StartPage")).pack()


class TailExtremityHE(tk.Frame):

    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        self.controller = controller
        label = tk.Label(self, text="Choose folder.", font=controller.title_font)
        label.pack(side="top", fill="x", pady=10)
        tk.Label(self, text="Look for the folder of videos where you want to manually label tail extremities.").pack(side="top", fill="x", pady=10)
        button = tk.Button(self, text="Choose folder",
                           command=lambda: controller.chooseFolderForTailExtremityHE())
        button.pack()
        tk.Button(self, text="Go to the start page", command=lambda: controller.show_frame("StartPage")).pack()


class ConfigFilePromp(tk.Frame):

    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        self.controller = controller
        label = tk.Label(self, text="Choose configuration file.", font=controller.title_font)
        label.pack(side="top", fill="x", pady=10)
        
        button = tk.Button(self, text="Choose file", command=lambda: controller.chooseConfigFile())
        button.pack()
        
        tk.Button(self, text="Go to the start page", command=lambda: controller.show_frame("StartPage")).pack()


class Patience(tk.Frame):

    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        self.controller = controller
        tk.Button(self, text="Launch ZebraZoom on your video(s)", command=lambda: controller.launchZebraZoom()).pack()
        label2 = tk.Label(self, text="After clicking on the button above, please wait for ZebraZoom to run, you can look at the console outside of the GUI to check on the progress of ZebraZoom.")
        label2.pack(side="top", fill="x", pady=10)


class ZZoutro(tk.Frame):

    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        self.controller = controller
        label = tk.Label(self, text="Analysis is finished.")
        label.pack(side="top", fill="x", pady=10)
        button = tk.Button(self, text="Go to the start page",
                           command=lambda: controller.show_frame("StartPage"))
        button.pack()


class ResultsVisualization(tk.Frame):

    def __init__(self, parent, controller):
        nbLines = 15
        curLine = 1
        curCol  = 0
        
        tk.Frame.__init__(self, parent)
        self.controller = controller
        label = tk.Label(self, text="Choose the results you'd like to visualize", font=controller.title_font)
        label.grid(row=0,column=0)
        
        cur_dir_path = os.path.dirname(os.path.realpath(__file__))
        path = Path(cur_dir_path)
        path = path.parent.parent
        reference = os.path.join(path, 'ZZoutput')
        
        if not(os.path.exists(reference)):
          os.mkdir(reference)
        
        os.walk(reference)
        for x in sorted(next(os.walk(reference))[1]):
          tk.Button(self, text=x, command=lambda currentResultFolder=x : controller.exploreResultFolder(currentResultFolder)).grid(row=curLine,column=curCol)
          if (curLine > nbLines):
            curLine = 1
            curCol = curCol + 1
          else:
            curLine = curLine + 1
        
        button = tk.Button(self, text="Go to the start page",
                           command=lambda: controller.show_frame("StartPage"))
        button.grid(row=curLine,column=curCol)

        
class ViewParameters(tk.Frame):

    def __init__(self, parent, controller):
        tk.Frame.__init__(self, parent)
        self.controller = controller
                
        name = self.controller.currentResultFolder
        
        if name != "abc":
          
          cur_dir_path = os.path.dirname(os.path.realpath(__file__))
          path = Path(cur_dir_path)
          path = path.parent.parent
          reference = os.path.join(path, os.path.join('ZZoutput', os.path.join(name, 'results_' + name + '.txt')))
          
          if controller.justEnteredViewParameter == 1:
            with open(reference) as ff:
                dataRef = json.load(ff)
            controller.dataRef = dataRef
            controller.justEnteredViewParameter = 0
          else:
            dataRef = controller.dataRef
          
          nbWellsRef  = len(dataRef["wellPoissMouv"])
          
          numWell  = self.controller.numWell
          numPoiss = self.controller.numPoiss
          numMouv  = self.controller.numMouv
          
          nbWells = len(dataRef["wellPoissMouv"])
          if numWell >= nbWells:
            if nbWells == 0:
              numWell = 0
            else:
              numWell = nbWells - 1
          nbPoiss = len(dataRef["wellPoissMouv"][numWell])
          
          if numPoiss >= nbPoiss:
            if nbPoiss == 0:
              numPoiss = 0
            else:
              numPoiss = nbPoiss - 1
          nbMouv  = len(dataRef["wellPoissMouv"][numWell][numPoiss])
          
          if numMouv >= nbMouv:
            if nbMouv == 0:
              numMouv = 0
            else:
              numMouv = nbMouv - 1
          
          label = tk.Label(self, text="    ", font=LARGE_FONT)
          label.grid(row=1,column=6)
          
          ttk.Button(self, text="View video for all wells together", command=lambda: controller.showValidationVideo(-1,0,-1)).grid(row=1,column=1)
          
          label = tk.Label(self, text=name, font="bold", justify=LEFT, pady=10)
          label.grid(sticky=W, row=0, column=0, columnspan=8)
          
          label = tk.Label(self, text="Well number:")
          label.grid(row=2,column=1)
          e1 = tk.Entry(self)
          e1.insert(0,numWell)
          e1.grid(row=2,column=2)
          tk.Button(self, text="-", command=lambda: controller.printSomeResults(int(e1.get())-1,e2.get(),e3.get())).grid(row=2,column=3)
          tk.Button(self, text="+", command=lambda: controller.printSomeResults(int(e1.get())+1,e2.get(),e3.get())).grid(row=2,column=4)
          
          ttk.Button(self, text="View zoomed video for well "+str(numWell), command=lambda: controller.showValidationVideo(e1.get(),1,-1)).grid(row=3,column=2)
          
          def callback(url):
            webbrowser.open_new(url)
          
          link1 = tk.Button(self, text="Video viewing tips", cursor="hand2", bg = 'red')
          link1.grid(row=3,column=4)
          link1.bind("<Button-1>", lambda e: callback("https://zebrazoom.org/validationVideoReading.html"))
          
          label = tk.Label(self, text="Fish number:")
          label.grid(row=4,column=1)
          e2 = tk.Entry(self)
          e2.insert(0,numPoiss)
          e2.grid(row=4,column=2)
          tk.Button(self, text="-", command=lambda: controller.printSomeResults(e1.get(),int(e2.get())-1,e3.get())).grid(row=4,column=3)
          tk.Button(self, text="+", command=lambda: controller.printSomeResults(e1.get(),int(e2.get())+1,e3.get())).grid(row=4,column=4)
          
          label = tk.Label(self, text="Bout number:")
          label.grid(row=5,column=1)
          e3 = tk.Entry(self)
          e3.insert(0,numMouv)
          e3.grid(row=5,column=2)
          tk.Button(self, text="-", command=lambda: controller.printSomeResults(e1.get(),e2.get(),int(e3.get())-1)).grid(row=5,column=3)
          tk.Button(self, text="+", command=lambda: controller.printSomeResults(e1.get(),e2.get(),int(e3.get())+1)).grid(row=5,column=4)
          
          button1 = ttk.Button(self, text="View bout's angle",
                              command=lambda: controller.printSomeResults(e1.get(),e2.get(),e3.get()))
          button1.grid(row=6,column=2)
          
          
          if (len(dataRef["wellPoissMouv"][numWell][numPoiss]) > 0):
          
            if ("flag" in dataRef["wellPoissMouv"][numWell][numPoiss][numMouv]):
              if (dataRef["wellPoissMouv"][numWell][numPoiss][numMouv]["flag"]):
                flagTxt = "UnFlag Movement"
              else:
                flagTxt = "Flag Movement"
            else:
              flagTxt = "Flag Movement"
            
            button3 = tk.Button(self, text=flagTxt, command=lambda: controller.flagMove(e1.get(),e2.get(),e3.get()))
            if flagTxt == "UnFlag Movement":
              button3.configure(bg = 'red')
            button3.grid(row=6,column=4)

          
          prev = ttk.Button(self, text="Previous Bout",
                              command=lambda: controller.printPreviousResults(e1.get(),e2.get(),e3.get(), nbWells, nbPoiss, nbMouv))
          prev.grid(row=7,column=1)
          
          next = ttk.Button(self, text="Next Bout",
                              command=lambda: controller.printNextResults(e1.get(),e2.get(),e3.get(),nbWells,nbPoiss,nbMouv))
          next.grid(row=7,column=2)
          
          tk.Button(self, text="Go to the previous page", command=lambda: controller.show_frame("ResultsVisualization")).grid(row=8,column=1)
          
          tk.Button(self, text="Change Visualization", command=lambda: controller.printSomeResults(e1.get(), e2.get(), e3.get(), True)).grid(row=8,column=2)
          
          if (controller.superstructmodified == 1):
            button1 = tk.Button(self, text="Save SuperStruct", command=lambda: controller.saveSuperStruct(e1.get(),e2.get(),e3.get()))
            button1.configure(bg = 'orange')
            button1.grid(row=7,column=4)

          if nbMouv > 0:
              
              begMove = dataRef["wellPoissMouv"][numWell][numPoiss][numMouv]["BoutStart"]
              endMove = dataRef["wellPoissMouv"][numWell][numPoiss][numMouv]["BoutEnd"]
              
              ttk.Button(self, text="View video for well "+str(numWell), command=lambda: controller.showValidationVideo(e1.get(),0,begMove)).grid(row=3,column=1)
              
              ttk.Button(self, text="View bout's video", command=lambda: controller.showValidationVideo(e1.get(),1,begMove)).grid(row=6,column=1)
              
              if controller.visualization == 0 and not("TailAngle_smoothed" in dataRef["wellPoissMouv"][numWell][numPoiss][numMouv]):
                  controller.visualization = 1
              
              if controller.visualization == 1 and not("TailAngle_Raw" in dataRef["wellPoissMouv"][numWell][numPoiss][numMouv]):
                  controller.visualization = 2
              
              if controller.visualization == 2 and not((len(np.unique(dataRef["wellPoissMouv"][numWell][numPoiss][numMouv]["HeadX"])) > 1) and (len(np.unique(dataRef["wellPoissMouv"][numWell][numPoiss][numMouv]["HeadY"])) > 1)):
                  controller.visualization = 0
              
              if controller.visualization == 0:
                label = tk.Label(self, text="Tail Angle Smoothed and amplitudes for well "+str(numWell)+", fish "+str(numPoiss)+", bout "+str(numMouv), font=LARGE_FONT)
              elif controller.visualization == 1:
                label = tk.Label(self, text="Tail Angle Raw for well "+str(numWell)+", fish "+str(numPoiss)+", bout "+str(numMouv)+"                             ", font=LARGE_FONT)
              else:
                label = tk.Label(self, text="Body Coordinates for well "+str(numWell)+" , fish "+str(numPoiss)+" , bout "+str(numMouv), font=LARGE_FONT)
              label.grid(row=1,column=7)
              
              if controller.visualization == 0:
                
                tailAngleSmoothed = dataRef["wellPoissMouv"][numWell][numPoiss][numMouv]["TailAngle_smoothed"].copy()
                
                for ind,val in enumerate(tailAngleSmoothed):
                  tailAngleSmoothed[ind]=tailAngleSmoothed[ind]*(180/(math.pi))
                
                if "Bend_Timing" in dataRef["wellPoissMouv"][numWell][numPoiss][numMouv]:
                  freqX = dataRef["wellPoissMouv"][numWell][numPoiss][numMouv]["Bend_Timing"]
                  freqY = dataRef["wellPoissMouv"][numWell][numPoiss][numMouv]["Bend_Amplitude"]
                else:
                  freqX = []
                  freqY = []
                if type(freqY)==int or type(freqY)==float:
                  freqY = freqY * (180/(math.pi))
                else:
                  if "Bend_Timing" in dataRef["wellPoissMouv"][numWell][numPoiss][numMouv]:
                    freqX = dataRef["wellPoissMouv"][numWell][numPoiss][numMouv]["Bend_Timing"].copy()
                    freqY = dataRef["wellPoissMouv"][numWell][numPoiss][numMouv]["Bend_Amplitude"].copy()
                  else:
                    freqX = []
                    freqY = []
                  for ind,val in enumerate(freqY):
                    freqY[ind]=freqY[ind]*(180/(math.pi))
                fx = [begMove]
                fy = [0]
                if (type(freqX) is int) or (type(freqX) is float):
                  freqX = [freqX]
                  freqY = [freqY]
                for idx,x in enumerate(freqX):
                  idx2 = idx - 1
                  fx.append(freqX[idx2] - 1 + begMove)
                  fx.append(freqX[idx2] - 1 + begMove)
                  fx.append(freqX[idx2] - 1 + begMove)
                  fy.append(0)
                  fy.append(freqY[idx2])
                  fy.append(0)
                
                f = Figure(figsize=(5,5), dpi=100)
                a = f.add_subplot(111)
                
                if len(tailAngleSmoothed):
                  a.plot([i for i in range(begMove,endMove+1)],tailAngleSmoothed)
                  a.plot(fx,fy)
                  a.plot([i for i in range(begMove,endMove+1)],[0 for i in range(0,len(tailAngleSmoothed))])
                
              elif controller.visualization == 1:
                
                tailAngleSmoothed = dataRef["wellPoissMouv"][numWell][numPoiss][numMouv]["TailAngle_Raw"].copy()
                for ind,val in enumerate(tailAngleSmoothed):
                  tailAngleSmoothed[ind]=tailAngleSmoothed[ind]*(180/(math.pi))
              
                f = Figure(figsize=(5,5), dpi=100)
                a = f.add_subplot(111)
              
                a.plot([i for i in range(begMove,endMove+1)],tailAngleSmoothed)
                a.plot([i for i in range(begMove,endMove+1)],[0 for i in range(0,len(tailAngleSmoothed))])
                
              else:
                
                headX = dataRef["wellPoissMouv"][numWell][numPoiss][numMouv]["HeadX"].copy()
                headY = dataRef["wellPoissMouv"][numWell][numPoiss][numMouv]["HeadY"].copy()
                
                f = Figure(figsize=(5,5), dpi=100)
                a = f.add_subplot(111)
                
                a.plot(headX, headY)
              
              canvas = FigureCanvasTkAgg(f, self)
              canvas.draw()
              canvas.get_tk_widget().grid(row=2,column=7,rowspan=7)

          else:
          
              tailAngleSmoothed = [i for i in range(0,1)]
          
              f = Figure(figsize=(5,5), dpi=100)
              a = f.add_subplot(111)
              
              a.plot([i for i in range(0,len(tailAngleSmoothed))],tailAngleSmoothed)

              canvas = FigureCanvasTkAgg(f, self)
              canvas.draw()
              canvas.get_tk_widget().grid(row=2,column=7,rowspan=7)
              
              canvas = Canvas(self)
              canvas.create_text(100,10, text="No bout detected for well "+str(numWell))
              canvas.grid(row=2,column=7,rowspan=7)