import tkinter as tk
from tkinter import font  as tkfont
from tkinter import filedialog
from tkinter import ttk
from tkinter import *
import webbrowser
from zebrazoom.code.vars import getGlobalVariables
globalVariables = getGlobalVariables()


class CreateExperimentOrganizationExcel(tk.Frame):

  def __init__(self, parent, controller):
  
    tk.Frame.__init__(self, parent)
    self.controller = controller
    label = tk.Label(self, text="Prepare experiment organization excel file:", font=controller.title_font)
    label.pack(side="top", fill="x", pady=10)
    
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
    
    tk.Label(self, text="").pack()
    tk.Label(self, text="If you already analyzed data and you just want to view previous results, click on one of the button above:").pack()
    tk.Button(self, text="View previous kinematic parameter analysis results", bg="light yellow", command=lambda: controller.show_frame("AnalysisOutputFolderPopulation")).pack()
    tk.Button(self, text="View previous clustering analysis results", bg="light yellow", command=lambda: controller.show_frame("AnalysisOutputFolderClustering")).pack()


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
    
    TailTrackingParameters = IntVar()
    Checkbutton(self, text="I want fish tail tracking related kinematic parameters (number of oscillation, tail beat frequency, etc..) to be calculated.", variable=TailTrackingParameters).pack()
    tk.Label(self, text="").pack()
    
    saveInMatlabFormat = IntVar()
    Checkbutton(self, text="The result structure is always saved in the pickle format. Also save it in the matlab format.", variable=saveInMatlabFormat).pack()
    tk.Label(self, text="").pack()
    
    saveRawData = IntVar()
    Checkbutton(self, text="Save original raw data in result structure.", variable=saveRawData).pack()
    tk.Label(self, text="").pack()
    
    tk.Label(self, text="Number of frames between each frame used for distance calculation (to avoid noise due to close-by subsequent points) (default value is 4):", font=("Helvetica", 10)).pack(side="top", fill="x")
    frameStepForDistanceCalculation = tk.Entry(self)
    frameStepForDistanceCalculation.pack()
    tk.Label(self, text="").pack()
    
    tk.Label(self, text="If you are calculating fish tail tracking related kinematic parameters:", font="bold").pack(side="top", fill="x")
    tk.Label(self, text="What's the minimum number of bends a bout should have to be taken into account for the analysis?", font=("Helvetica", 10)).pack(side="top", fill="x")
    tk.Label(self, text="(the default value is 3) (put 0 if you want all bends to be taken into account)", font=("Helvetica", 10)).pack(side="top", fill="x")
    minNbBendForBoutDetect = tk.Entry(self)
    minNbBendForBoutDetect.pack()
    tk.Label(self, text="If, for a bout, the tail tracking related kinematic parameters are being discarded because of a low amount of bends,", font=("Helvetica", 10)).pack(side="top", fill="x")
    tk.Label(self, text="should the BoutDuration, TotalDistance, Speed and IBI also be discarded for that bout?", font=("Helvetica", 10)).pack(side="top", fill="x")
    discard = IntVar()
    Checkbutton(self, text="Yes, discard BoutDuration, TotalDistance, Speed and IBI in that situation", variable=discard).pack()
    keep = IntVar()
    Checkbutton(self, text="No, keep BoutDuration, TotalDistance, Speed and IBI in that situation", variable=keep).pack()
    tk.Label(self, text="Please ignore the two questions above if you're only looking at BoutDuration, TotalDistance, Speed and IBI.", font=("Helvetica", 10)).pack(side="top", fill="x", pady=10)
    
    tk.Button(self, text="Launch Analysis", bg="light yellow", command=lambda: controller.populationComparison(controller, TailTrackingParameters.get(), saveInMatlabFormat.get(), saveRawData.get(), minNbBendForBoutDetect.get(), discard.get(), keep.get(), frameStepForDistanceCalculation.get())).pack()
    
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
    tk.Label(self, text="").pack()
    
    tk.Label(self, text="Choose one of the options below:").pack()
    FreelySwimming = IntVar()
    Checkbutton(self, text="Freely swimming fish with tail tracking", variable=FreelySwimming).pack()
    HeadEmbeded = IntVar()
    Checkbutton(self, text="Head embeded fish with tail tracking", variable=HeadEmbeded).pack()
    tk.Label(self, text="").pack()
    
    tk.Label(self, text="What's the minimum number of bends a bout should have to be taken into account for the analysis?", font=("Helvetica", 10)).pack(side="top", fill="x")
    tk.Label(self, text="(the default value is 3) (put 0 if you want all bends to be taken into account)", font=("Helvetica", 10)).pack(side="top", fill="x")
    minNbBendForBoutDetect = tk.Entry(self)
    minNbBendForBoutDetect.pack()
    tk.Label(self, text="").pack()
    
    tk.Label(self, text="Optional: generate videos containing the most representative bouts for each cluster: enter below the number of bouts for each video:", font=("Helvetica", 10)).pack(side="top", fill="x")
    tk.Label(self, text="(leave blank if you don't want any such cluster validation videos to be generated)", font=("Helvetica", 10)).pack(side="top", fill="x")
    nbVideosToSave = tk.Entry(self)
    nbVideosToSave.pack()
    tk.Label(self, text="").pack()
    
    modelUsedForClustering = IntVar()
    Checkbutton(self, text="Use GMM clustering method instead of Kmeans (clustering method used by default)", variable=modelUsedForClustering).pack()
    tk.Label(self, text="")
    
    removeOutliers = IntVar()
    Checkbutton(self, text="Remove outliers before clustering", variable=removeOutliers).pack()
    tk.Label(self, text="")
    
    tk.Label(self, text="Number of frames between each frame used for distance calculation (to avoid noise due to close-by subsequent points) (default value is 4):", font=("Helvetica", 10)).pack(side="top", fill="x")
    frameStepForDistanceCalculation = tk.Entry(self)
    frameStepForDistanceCalculation.pack()
    tk.Label(self, text="").pack()
    
    tk.Button(self, text="Launch Analysis", bg="light yellow", command=lambda: controller.boutClustering(controller, nbClustersToFind.get(), FreelySwimming.get(), HeadEmbeded.get(), minNbBendForBoutDetect.get(), nbVideosToSave.get(), modelUsedForClustering.get(), removeOutliers.get(), frameStepForDistanceCalculation.get())).pack()
    
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
    
    tk.Button(self, text="View 'plots and processed data' folders", bg="light yellow", command=lambda: controller.openAnalysisFolder(controller.homeDirectory, 'resultsKinematic')).pack()
    tk.Label(self, text="").pack()
    
    tk.Button(self, text="View raw data", bg="light yellow", command=lambda: controller.openAnalysisFolder(controller.homeDirectory, 'data')).pack()
    tk.Label(self, text="").pack()
    
    tk.Button(self, text="Go to the start page", bg="light cyan", command=lambda: controller.show_frame("StartPage")).pack()
    tk.Label(self, text="").pack()
    
    def callback(url):
      webbrowser.open_new(url)
    link1 = tk.Button(self, text="Video data analysis online documentation", bg="light yellow")
    link1.pack()
    link1.bind("<Button-1>", lambda e: callback("https://github.com/oliviermirat/ZebraZoom#GUIanalysis"))
    tk.Label(self, text="(read the 'Further analyzing ZebraZoom's output through the Graphical User Interface' section)").pack()


class AnalysisOutputFolderClustering(tk.Frame):

  def __init__(self, parent, controller):
    
    tk.Frame.__init__(self, parent)
    self.controller = controller
    label = tk.Label(self, text="View Analysis Output:", font=controller.title_font)
    label.pack(side="top", fill="x", pady=10)
    
    tk.Label(self, text="").pack()
    tk.Label(self, text="Click the button below to open the folder that contains the results of the analysis.").pack()
    tk.Label(self, text="").pack()
    
    tk.Button(self, text="View plots and processed data folder", bg="light yellow", command=lambda: controller.openAnalysisFolder(controller.homeDirectory, 'resultsClustering')).pack()
    tk.Label(self, text="").pack()
    
    tk.Button(self, text="View raw data folders", bg="light yellow", command=lambda: controller.openAnalysisFolder(controller.homeDirectory, 'data')).pack()
    tk.Label(self, text="").pack()
    
    tk.Button(self, text="Go to the start page", bg="light cyan", command=lambda: controller.show_frame("StartPage")).pack()

