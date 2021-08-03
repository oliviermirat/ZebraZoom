import tkinter as tk
from tkinter import font  as tkfont
from tkinter import filedialog
from tkinter import ttk
from tkinter import *
from zebrazoom.code.vars import getGlobalVariables
globalVariables = getGlobalVariables()


class CreateExperimentOrganizationExcel(tk.Frame):

  def __init__(self, parent, controller):
  
    tk.Frame.__init__(self, parent)
    self.controller = controller
    label = tk.Label(self, text="Prepare experiment organization excel file:", font=controller.title_font)
    label.pack(side="top", fill="x", pady=10)
    
    tk.Label(self, text="").pack()
    tk.Label(self, text="To further analyze the outputs of ZebraZoom you must create an excel file to describe how you organized your experiments.").pack()
    tk.Label(self, text="Click on the button below to open the folder where you should store that excel file.").pack()
    tk.Label(self, text="In this folder you will also find an file named 'example' showing an example of such an excel file.").pack()
    tk.Label(self, text="In these excel files, set the columns as explained below:").pack()
    tk.Label(self, text="If you haven't moved the output folders of ZebraZoom, leave defaultZZoutputFolder as the value for path.").pack()
    tk.Label(self, text="fq needs to be set to the frequency of acquisition of your video and pixelSize needs to be set to the number microns in each pixel of your video.").pack()
    tk.Label(self, text="condition and genotype need to be set to arrays for which each element represents a well and is set the condition/genotype of that well.").pack()
    tk.Label(self, text="include is an array for which each element is set to 1 if the corresponding well should be included in the analysis and 0 otherwise.").pack()
    tk.Label(self, text="").pack()
    
    tk.Button(self, text="Open experiment organization excel files folder", command=lambda: controller.openExperimentOrganizationExcelFolder(controller.homeDirectory)).pack()
    
    tk.Label(self, text="").pack()
    tk.Label(self, text="You have to create an excel file describing the organization of your experiment and you should place it inside the folder opened with the button above.").pack()
    tk.Label(self, text="Once this is done, click on the button below:").pack()
    tk.Label(self, text="").pack()
    
    tk.Button(self, text="Ok done!", bg="light yellow", command=lambda: controller.show_frame("ChooseExperimentOrganizationExcel")).pack()
    
    tk.Label(self, text="").pack()
    
    tk.Button(self, text="Go to the start page", bg="light cyan", command=lambda: controller.show_frame("StartPage")).pack()


class ChooseExperimentOrganizationExcel(tk.Frame):

  def __init__(self, parent, controller):
  
    tk.Frame.__init__(self, parent)
    self.controller = controller
    label = tk.Label(self, text="Choose organization excel file:", font=controller.title_font)
    label.pack(side="top", fill="x", pady=10)
    
    tk.Button(self, text="Select the excel file describing the organization of your experiment.", bg="light yellow", command=lambda: controller.chooseExperimentOrganizationExcel(controller)).pack()
    
    tk.Button(self, text="Go to the start page", bg="light cyan", command=lambda: controller.show_frame("StartPage")).pack()


class ChooseDataAnalysisMethod(tk.Frame):

  def __init__(self, parent, controller):
  
    tk.Frame.__init__(self, parent)
    self.controller = controller
    label = tk.Label(self, text="Choose the analysis you want to perform:", font=controller.title_font)
    label.pack(side="top", fill="x", pady=10)
    
    tk.Button(self, text="Compare populations with kinematic parameters", bg="light yellow", command=lambda: controller.show_frame("PopulationComparison")).pack()
    tk.Button(self, text="Cluster bouts of movements  (for zebrafish only)", bg="light yellow", command=lambda: controller.show_frame("BoutClustering")).pack()
    
    tk.Button(self, text="Go to the start page", bg="light cyan", command=lambda: controller.show_frame("StartPage")).pack()


class PopulationComparison(tk.Frame):

  def __init__(self, parent, controller):
  
    tk.Frame.__init__(self, parent)
    self.controller = controller
    label = tk.Label(self, text="Population Comparison:", font=controller.title_font)
    label.pack(side="top", fill="x", pady=10)
    
    BoutDuration = IntVar()
    Checkbutton(self, text="BoutDuration", variable=BoutDuration).pack()
    TotalDistance = IntVar()
    Checkbutton(self, text="TotalDistance", variable=TotalDistance).pack()
    Speed = IntVar()
    Checkbutton(self, text="Speed", variable=Speed).pack()
    NumberOfOscillations = IntVar()
    Checkbutton(self, text="NumberOfOscillations (for zebrafish only)", variable=NumberOfOscillations).pack()
    meanTBF = IntVar()
    Checkbutton(self, text="meanTBF (for zebrafish only)", variable=meanTBF).pack()
    maxAmplitude = IntVar()
    Checkbutton(self, text="maxAmplitude (for zebrafish only)", variable=maxAmplitude).pack()
    
    tk.Label(self, text="", font=("Helvetica", 10)).pack(side="top", fill="x", pady=10)
    tk.Label(self, text="If you are calculating one these three parameters: NumberOfOscillations, meanTBF, maxAmplitude:", font="bold").pack(side="top", fill="x")
    tk.Label(self, text="What's the minimum number of bends a bout should have to be taken into account for the analysis?", font=("Helvetica", 10)).pack(side="top", fill="x")
    tk.Label(self, text="(the default value is 3) (put 0 if you want all bends to be taken into account)", font=("Helvetica", 10)).pack(side="top", fill="x")
    minNbBendForBoutDetect = tk.Entry(self)
    minNbBendForBoutDetect.pack()
    tk.Label(self, text="If, for a bout, NumberOfOscillations, meanTBF and maxAmplitude are being discarded because of a low amount of bends,", font=("Helvetica", 10)).pack(side="top", fill="x")
    tk.Label(self, text="should the BoutDuration, TotalDistance and Speed also be discarded for that bout?", font=("Helvetica", 10)).pack(side="top", fill="x")
    discard = IntVar()
    Checkbutton(self, text="Yes, discard BoutDuration, TotalDistance and Speed in that situation", variable=discard).pack()
    keep = IntVar()
    Checkbutton(self, text="No, keep BoutDuration, TotalDistance and Speed in that situation", variable=keep).pack()
    tk.Label(self, text="Please ignore the two questions above if you're only looking at BoutDuration, TotalDistance and Speed.", font=("Helvetica", 10)).pack(side="top", fill="x", pady=10)
    
    tk.Button(self, text="Launch Analysis", bg="light yellow", command=lambda: controller.populationComparison(controller, BoutDuration.get(), TotalDistance.get(), Speed.get(), NumberOfOscillations.get(), meanTBF.get(), maxAmplitude.get(), minNbBendForBoutDetect.get(), discard.get(), keep.get())).pack()
    
    tk.Button(self, text="Go to the start page", bg="light cyan", command=lambda: controller.show_frame("StartPage")).pack()


class BoutClustering(tk.Frame):

  def __init__(self, parent, controller):
  
    tk.Frame.__init__(self, parent)
    self.controller = controller
    
    label = tk.Label(self, text="Bout Clustering:", font=controller.title_font)
    label.pack(side="top", fill="x", pady=10)
    
    tk.Label(self, text="Choose number of cluster to find:").pack()
    nbClustersToFind = tk.Entry(self)
    nbClustersToFind.pack()
    
    tk.Label(self, text="Choose one of the options below:").pack()
    FreelySwimming = IntVar()
    Checkbutton(self, text="Freely swimming fish with tail tracking", variable=FreelySwimming).pack()
    HeadEmbeded = IntVar()
    Checkbutton(self, text="Head embeded fish with tail tracking", variable=HeadEmbeded).pack()
    
    tk.Button(self, text="Launch Analysis", bg="light yellow", command=lambda: controller.boutClustering(controller, nbClustersToFind.get(), FreelySwimming.get(), HeadEmbeded.get())).pack()
    
    tk.Button(self, text="Go to the start page", bg="light cyan", command=lambda: controller.show_frame("StartPage")).pack()


class AnalysisOutputFolderPopulation(tk.Frame):

  def __init__(self, parent, controller):
    
    tk.Frame.__init__(self, parent)
    self.controller = controller
    label = tk.Label(self, text="View Analysis Output:", font=controller.title_font)
    label.pack(side="top", fill="x", pady=10)
    
    tk.Label(self, text="").pack()
    tk.Label(self, text="Click the button below to open the folder that contains the results of the analysis.").pack()
    tk.Label(self, text="").pack()
    
    tk.Button(self, text="View results folder", bg="light yellow", command=lambda: controller.openPopulationAnalysisFolder(controller.homeDirectory)).pack()
    
    tk.Button(self, text="Go to the start page", bg="light cyan", command=lambda: controller.show_frame("StartPage")).pack()


class AnalysisOutputFolderClustering(tk.Frame):

  def __init__(self, parent, controller):
    
    tk.Frame.__init__(self, parent)
    self.controller = controller
    label = tk.Label(self, text="View Analysis Output:", font=controller.title_font)
    label.pack(side="top", fill="x", pady=10)
    
    tk.Label(self, text="").pack()
    tk.Label(self, text="Click the button below to open the folder that contains the results of the analysis.").pack()
    tk.Label(self, text="").pack()
    
    tk.Button(self, text="View results folder", bg="light yellow", command=lambda: controller.openClusteringAnalysisFolder(controller.homeDirectory)).pack()
    
    tk.Button(self, text="Go to the start page", bg="light cyan", command=lambda: controller.show_frame("StartPage")).pack()

