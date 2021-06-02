import os
import tkinter as tk
from tkinter import font  as tkfont
from tkinter import filedialog
from tkinter import ttk
from tkinter import *
import webbrowser
from zebrazoom.code.vars import getGlobalVariables
globalVariables = getGlobalVariables()


class ChooseVideoToCreateConfigFileFor(tk.Frame):

  def __init__(self, parent, controller):
  
    tk.Frame.__init__(self, parent)
    self.controller = controller
    label = tk.Label(self, text="Prepare Config File", font=controller.title_font)
    label.pack(side="top", fill="x", pady=10)
    
    reloadConfigFile = IntVar()
    Checkbutton(self, text="Click here to start from a configuration file previously created (instead of from scratch).", variable=reloadConfigFile).pack()
    
    tk.Button(self, text="Select the video you want to create a configuration file for.", bg="light yellow", command=lambda: controller.chooseVideoToCreateConfigFileFor(controller, reloadConfigFile.get())).pack()
    
    tk.Label(self, text='').pack()
    tk.Label(self, text="(you will be able to use the configuration file you create for all videos that are similar to that video)").pack()
    tk.Label(self, text="").pack()
    
    tk.Button(self, text="Go to the start page", bg="light cyan", command=lambda: controller.show_frame("StartPage")).pack()
    
    tk.Label(self, text='').pack()
    tk.Label(self, text='Warning: This procedure to create configuration files is incomplete.').pack()
    tk.Label(self, text='You may not succeed at making a good configuration file to analyze your video.').pack()
    tk.Label(self, text="If you don't manage to get a good configuration file that fits your needs, email us at info@zebrazoom.org.").pack()
    tk.Label(self, text='').pack()
    
    def callback(url):
      webbrowser.open_new(url)
    
    link2 = tk.Button(self, text="View Tracking Troubleshooting Tips", bg="gold")
    link2.pack()
    link2.bind("<Button-1>", lambda e: callback("https://github.com/oliviermirat/ZebraZoom/blob/master/TrackingTroubleshooting.md"))


class ChooseGeneralExperiment(tk.Frame):

  def __init__(self, parent, controller):
  
    tk.Frame.__init__(self, parent)
    self.controller = controller
    label = tk.Label(self, text="Prepare Config File", font=controller.title_font)
    label.pack(side="top", fill="x", pady=10)
    
    tk.Label(self, text="Choose only one of the options below:", font=("Helvetica", 12)).pack(side="top", fill="x", pady=10)
    
    freeZebra = IntVar()
    Checkbutton(self, text="Track heads and tails of freely swimming fish.", variable=freeZebra).pack()
    tk.Label(self, text="The fish must be in one well of any shape or in several circular wells. Each well should contain the same number of fish.").pack()
    tk.Label(self, text="").pack()
    
    headEmbZebra = IntVar()
    Checkbutton(self, text="Track tail of one head embedded zebrafish larva.", variable=headEmbZebra).pack()
    tk.Label(self, text="").pack()
    
    drosophilia = IntVar()
    rodent = IntVar()
    other = IntVar()
    Checkbutton(self, text="Track centers of mass of any kind of animal.", variable=other).pack()
    tk.Label(self, text='Several animals can be tracked at once. The animals must be "darker" than the background and the background must be still.').pack()
    tk.Label(self, text="").pack()
    
    tk.Button(self, text="Next", bg="light yellow", command=lambda: controller.chooseGeneralExperimentFirstStep(controller, freeZebra.get(), headEmbZebra.get(), drosophilia.get(), rodent.get(), other.get())).pack()
    
    tk.Button(self, text="Go to the start page", bg="light cyan", command=lambda: controller.show_frame("StartPage")).pack()


class FreelySwimmingExperiment(tk.Frame):

  def __init__(self, parent, controller):
  
    tk.Frame.__init__(self, parent)
    self.controller = controller
    label = tk.Label(self, text="Prepare Config File for Freely Swimming Fish:", font=controller.title_font)
    label.pack(side="top", fill="x", pady=10)
    
    tk.Label(self, text="Choose only one of the options below:", font=("Helvetica", 12)).pack(side="top", fill="x", pady=10)
    
    freeZebra2 = IntVar()
    Checkbutton(self, text="Recommended method: Automatic Parameters Setting", variable=freeZebra2).pack()
    tk.Label(self, text="This method will work well on most videos. One exception can be for fish of very different sizes.").pack()
    tk.Label(self, text="").pack()
    
    freeZebra = IntVar()
    Checkbutton(self, text="Alternative method: Manual Parameters Setting", variable=freeZebra).pack()
    tk.Label(self, text="It's more difficult to create a configuration file with this method, but it can sometimes be useful as an alternative.").pack()
    tk.Label(self, text="").pack()
    
    tk.Button(self, text="Next", bg="light yellow", command=lambda: controller.chooseGeneralExperiment(controller, freeZebra.get(), 0, 0, 0, 0, freeZebra2.get())).pack()
    
    tk.Button(self, text="Go to the start page", bg="light cyan", command=lambda: controller.show_frame("StartPage")).pack()


class WellOrganisation(tk.Frame):

  def __init__(self, parent, controller):
  
    tk.Frame.__init__(self, parent)
    self.controller = controller
    label = tk.Label(self, text="Prepare Config File", font=controller.title_font)
    label.pack(side="top", fill="x", pady=10)
    
    tk.Label(self, text="Choose only one of the options below:", font=("Helvetica", 12)).pack(side="top", fill="x", pady=10)
    
    multipleROIs = IntVar()
    Checkbutton(self, text="Multiple rectangular regions of interest chosen at runtime", variable=multipleROIs).pack()
    
    other = IntVar()
    Checkbutton(self, text="Whole video", variable=other).pack()
    
    roi = IntVar()
    Checkbutton(self, text="One rectangular region of interest fixed in the configuration file", variable=roi).pack()
    
    circular = IntVar()
    Checkbutton(self, text="Circular wells (beta version)", variable=circular).pack()
    
    rectangular = IntVar()
    Checkbutton(self, text="Rectangular wells (beta version)", variable=rectangular).pack()
    
    tk.Button(self, text="Next", bg="light yellow", command=lambda: controller.wellOrganisation(controller, circular.get(), rectangular.get(), roi.get(), other.get(), multipleROIs.get())).pack()
    
    tk.Button(self, text="Go to the start page", bg="light cyan", command=lambda: controller.show_frame("StartPage")).pack()


class NbRegionsOfInterest(tk.Frame):

  def __init__(self, parent, controller):
  
    tk.Frame.__init__(self, parent)
    self.controller = controller
    label = tk.Label(self, text="Prepare Config File", font=controller.title_font)
    label.pack(side="top", fill="x", pady=10)
    
    tk.Label(self, text="How many regions of interest / wells are there in your video?", font=("Helvetica", 10)).pack(side="top", fill="x", pady=10)
    nbwells = tk.Entry(self)
    nbwells.pack()
    
    tk.Button(self, text="Next", bg="light yellow", command=lambda: controller.regionsOfInterest(controller, nbwells.get())).pack()
    
    tk.Button(self, text="Go to the start page", bg="light cyan", command=lambda: controller.show_frame("StartPage")).pack()


class CircularOrRectangularWells(tk.Frame):

  def __init__(self, parent, controller):
  
    tk.Frame.__init__(self, parent)
    self.controller = controller
    label = tk.Label(self, text="Prepare Config File", font=controller.title_font)
    label.pack(side="top", fill="x", pady=10)
    
    tk.Label(self, text="How many wells are there in your video?", font=("Helvetica", 10)).pack(side="top", fill="x", pady=10)
    nbwells = tk.Entry(self)
    nbwells.pack()
    
    tk.Label(self, text="How many rows of wells are there in your video? (leave blank for default of 1)", font=("Helvetica", 10)).pack(side="top", fill="x", pady=10)
    nbRowsOfWells = tk.Entry(self)
    nbRowsOfWells.pack()
    
    tk.Label(self, text="How many wells are there per row on your video? (leave blank for default of 4)", font=("Helvetica", 10)).pack(side="top", fill="x", pady=10)
    nbWellsPerRows = tk.Entry(self)
    nbWellsPerRows.pack()
    
    tk.Button(self, text="Next", bg="light yellow", command=lambda: controller.circularOrRectangularWells(controller, nbwells.get(), nbRowsOfWells.get(), nbWellsPerRows.get())).pack()
    
    tk.Button(self, text="Go to the start page", bg="light cyan", command=lambda: controller.show_frame("StartPage")).pack()


class ChooseCircularWellsLeft(tk.Frame):

  def __init__(self, parent, controller):
  
    tk.Frame.__init__(self, parent)
    self.controller = controller
    label = tk.Label(self, text="Prepare Config File", font=controller.title_font)
    label.pack(side="top", fill="x", pady=10)
    
    tk.Button(self, text="Click on the left inner border of the top left well", command=lambda: controller.chooseCircularWellsLeft(controller)).pack()
    
    tk.Label(self, text="Example:", font=("Helvetica", 10)).pack(side="top", fill="x", pady=10)
    
    canvas = Canvas(self, width=2500, height=2000)
    canvas.pack()
    cur_dir_path = os.path.dirname(os.path.realpath(__file__))
    img = PhotoImage(file=os.path.join(cur_dir_path, 'leftborder.png'))
    self.img = img
    canvas.create_image(20, 20, anchor=NW, image=img)
    
    tk.Button(self, text="Go to the start page", bg="light cyan", command=lambda: controller.show_frame("StartPage")).pack()


class ChooseCircularWellsRight(tk.Frame):

  def __init__(self, parent, controller):
  
    tk.Frame.__init__(self, parent)
    self.controller = controller
    label = tk.Label(self, text="Prepare Config File", font=controller.title_font)
    label.pack(side="top", fill="x", pady=10)
    
    tk.Button(self, text="Click on the right inner border of the top left well", command=lambda: controller.chooseCircularWellsRight(controller)).pack()
    
    tk.Label(self, text="Example:", font=("Helvetica", 10)).pack(side="top", fill="x", pady=10)
    
    canvas = Canvas(self, width=2500, height=2000)
    canvas.pack()
    cur_dir_path = os.path.dirname(os.path.realpath(__file__))
    img = PhotoImage(file=os.path.join(cur_dir_path, 'rightborder.png'))
    self.img = img
    canvas.create_image(20, 20, anchor=NW, image=img)
    
    tk.Button(self, text="Go to the start page", bg="light cyan", command=lambda: controller.show_frame("StartPage")).pack()


class NumberOfAnimals(tk.Frame):

  def __init__(self, parent, controller):
  
    tk.Frame.__init__(self, parent)
    self.controller = controller
    label = tk.Label(self, text="Prepare Config File", font=controller.title_font)
    label.pack(side="top", fill="x", pady=10)
    
    tk.Label(self, text="What's the total number of animals in your video?", font=("Helvetica", 10)).pack(side="top", fill="x", pady=10)
    
    nbanimals = tk.Entry(self)
    nbanimals.pack()
    
    tk.Label(self, text="", font=("Helvetica", 10)).pack(side="top", fill="x", pady=10)
    tk.Label(self, text="Are all of those animals ALWAYS visible throughout the video?", font=("Helvetica", 10)).pack(side="top", fill="x", pady=10)
    
    yes = IntVar()
    Checkbutton(self, text="Yes", variable=yes).pack()
    noo = IntVar()
    Checkbutton(self, text="No", variable=noo).pack()
    
    tk.Label(self, text="", font=("Helvetica", 10)).pack(side="top", fill="x", pady=10)
    forceBlobMethodForHeadTracking = IntVar()
    Checkbutton(self, text="Blob method for head tracking of fish", variable=forceBlobMethodForHeadTracking).pack()
    tk.Label(self, text="Only click the box above if you tried the tracking without this option and the head tracking was suboptimal (an eye was detected instead of the head for example).", font=("Helvetica", 10)).pack(side="top", fill="x")
    
    
    tk.Label(self, text="", font=("Helvetica", 10)).pack(side="top", fill="x", pady=10)
    tk.Button(self, text="Next", command=lambda: controller.numberOfAnimals(controller, nbanimals.get(), yes.get(), noo.get(), forceBlobMethodForHeadTracking.get(), 0, 0, 0, 0, 0, 0, 0)).pack()
    tk.Label(self, text="", font=("Helvetica", 10)).pack(side="top", fill="x", pady=10)
    tk.Button(self, text="Go to the start page", bg="light cyan", command=lambda: controller.show_frame("StartPage")).pack()
    
class NumberOfAnimals2(tk.Frame):

  def __init__(self, parent, controller):
  
    tk.Frame.__init__(self, parent)
    self.controller = controller
    
    tk.Label(self, text="Prepare Config File", font=controller.title_font).grid(row=0, column=0, columnspan = 2, pady=10)
    
    tk.Label(self, text="What's the total number of animals in your video?", font = "bold").grid(row=1, column=0, pady=10)
    nbanimals = tk.Entry(self)
    nbanimals.grid(row=2, column=0)
    
    tk.Label(self, text="Are all of those animals ALWAYS visible throughout the video?", font = "bold").grid(row=1, column=1, pady=10)
    yes = IntVar()
    Checkbutton(self, text="Yes", variable=yes).grid(row=2, column=1)
    noo = IntVar()
    Checkbutton(self, text="No", variable=noo).grid(row=3, column=1)
    
    tk.Label(self, text="Do you want bouts of movement to be detected?", font = "bold").grid(row=4, column=0, pady=10)
    tk.Label(self, text="Warning: at the moment, the parameters related to the bouts detection are a little challenging to set.").grid(row=5, column=0)
    yesBouts = IntVar()
    Checkbutton(self, text="Yes", variable=yesBouts).grid(row=6, column=0)
    nooBouts = IntVar()
    Checkbutton(self, text="No", variable=nooBouts).grid(row=7, column=0)
    
    tk.Label(self, text="Do you want bends and associated paramaters to be calculated?", font = "bold").grid(row=4, column=1, pady=10)
    tk.Label(self, text="Bends are the local minimum and maximum of the tail angle.").grid(row=5, column=1)
    tk.Label(self, text="Bends are used to calculate parameters such as tail beat frequency.").grid(row=6, column=1)
    
    def callback(url):
      webbrowser.open_new(url)
    
    link1 = tk.Button(self, text="You may need to further adjust these parameters afterwards: see documentation.")
    link1.grid(row=7, column=1)
    link1.bind("<Button-1>", lambda e: callback("https://github.com/oliviermirat/ZebraZoom#hyperparametersTailAngleSmoothBoutsAndBendsDetect"))
    
    yesBends = IntVar()
    Checkbutton(self, text="Yes", variable=yesBends).grid(row=8, column=1)
    nooBends = IntVar()
    Checkbutton(self, text="No", variable=nooBends).grid(row=9, column=1)
    
    tk.Label(self, text="Tail tracking: Choose an option below:", font = "bold").grid(row=8, column=0, pady=10)
    recommendedMethod = IntVar()
    Checkbutton(self, text="Recommended Method: Fast Tracking but tail tip might be detected too soon along the tail", variable=recommendedMethod).grid(row=9, column=0)
    alternativeMethod = IntVar()
    Checkbutton(self, text="Alternative Method: Slower Tracker but tail tip MIGHT be detected more acurately", variable=alternativeMethod).grid(row=10, column=0)
    tk.Label(self, text="Once your configuration is created, you can switch from one method to the other", font=("Helvetica", 10)).grid(row=11, column=0)
    tk.Label(self, text="by changing the value of the parameter recalculateForegroundImageBasedOnBodyArea", font=("Helvetica", 10)).grid(row=12, column=0)
    tk.Label(self, text="in your config file between 0 and 1.", font=("Helvetica", 10)).grid(row=13, column=0)
    
    tk.Label(self, text="Tracking: Choose an option below:", font = "bold").grid(row=10, column=1, pady=10)
    recommendedTrackingMethod = IntVar()
    Checkbutton(self, text="Recommended Method in most cases: Slower Tracking but often more accurate.", variable=recommendedTrackingMethod).grid(row=11, column=1)
    alternativeTrackingMethod = IntVar()
    Checkbutton(self, text="Alternative Method: Faster tracking, sometimes less accurate.", variable=alternativeTrackingMethod).grid(row=12, column=1)
    tk.Label(self, text="The alternative method can also work better for animals of different sizes.", font=("Helvetica", 10)).grid(row=13, column=1)
    
    tk.Button(self, text="Ok, next step", bg="light yellow", command=lambda: controller.numberOfAnimals(controller, nbanimals.get(), yes.get(), noo.get(), 0, yesBouts.get(), nooBouts.get(), recommendedMethod.get(), alternativeMethod.get(), yesBends.get(), nooBends.get(), recommendedTrackingMethod.get())).grid(row=14, column=0, columnspan = 2)
    tk.Button(self, text="Go to the start page", bg="light cyan", command=lambda: controller.show_frame("StartPage")).grid(row=15, column=0, columnspan = 2)


class NumberOfAnimalsCenterOfMass(tk.Frame):

  def __init__(self, parent, controller):
  
    tk.Frame.__init__(self, parent)
    self.controller = controller
    label = tk.Label(self, text="Prepare Config File", font=controller.title_font)
    label.pack(side="top", fill="x", pady=10)
    
    tk.Label(self, text="What's the total number of animals in your video?", font=("Helvetica", 10)).pack(side="top", fill="x", pady=10)
    
    nbanimals = tk.Entry(self)
    nbanimals.pack()
    
    tk.Label(self, text="", font=("Helvetica", 10)).pack(side="top", fill="x", pady=10)
    tk.Label(self, text="Are all of those animals ALWAYS visible throughout the video?", font=("Helvetica", 10)).pack(side="top", fill="x", pady=10)
    
    yes = IntVar()
    Checkbutton(self, text="Yes", variable=yes).pack()
    noo = IntVar()
    Checkbutton(self, text="No", variable=noo).pack()
    
    tk.Label(self, text="", font=("Helvetica", 10)).pack(side="top", fill="x", pady=10)
    
    tk.Button(self, text="Automatic Parameters Setting, Method 1: Slower tracking but often more accurate", command=lambda: controller.numberOfAnimals(controller, nbanimals.get(), yes.get(), noo.get(), 0, 0, 0, 1, 0, 0, 0, 1)).pack()
    tk.Button(self, text="Automatic Parameters Setting, Method 2: Faster tracking but often less accurate", command=lambda: controller.numberOfAnimals(controller, nbanimals.get(), yes.get(), noo.get(), 0, 0, 0, 1, 0, 0, 0, 0)).pack()
    tk.Label(self, text="", font=("Helvetica", 10)).pack()
    tk.Button(self, text="Manual Parameters Setting: More control over the choice of parameters", command=lambda: controller.numberOfAnimals(controller, nbanimals.get(), yes.get(), noo.get(), 0, 0, 0, 0, 1, 0, 0, 0)).pack()
    tk.Label(self, text="Try the 'Automatic Parameters Setting, Method 1' first. If it doesn't work, try the other methods.", font=("Helvetica", 10)).pack()
    tk.Label(self, text="The 'Manual Parameter Settings' makes setting parameter slightly more challenging but offers more control over the choice of parameters.", font=("Helvetica", 10)).pack(side="top", fill="x", pady=10)
    
    tk.Label(self, text="", font=("Helvetica", 10)).pack(side="top", fill="x", pady=10)
    tk.Button(self, text="Go to the start page", bg="light cyan", command=lambda: controller.show_frame("StartPage")).pack()


class IdentifyHeadCenter(tk.Frame):

  def __init__(self, parent, controller):
  
    tk.Frame.__init__(self, parent)
    self.controller = controller
    label = tk.Label(self, text="Prepare Config File", font=controller.title_font)
    label.pack(side="top", fill="x", pady=10)
    
    tk.Button(self, text="Click on the center of the head of a zebrafish", command=lambda: controller.chooseHeadCenter(controller)).pack()
    
    tk.Label(self, text="Example:", font=("Helvetica", 10)).pack(side="top", fill="x", pady=10)
    
    canvas = Canvas(self, width=2500, height=2000)
    canvas.pack()
    cur_dir_path = os.path.dirname(os.path.realpath(__file__))
    img = PhotoImage(file=os.path.join(cur_dir_path, 'blobCenter.png'))
    self.img = img
    canvas.create_image(20, 20, anchor=NW, image=img)
    
    tk.Button(self, text="Go to the start page", bg="light cyan", command=lambda: controller.show_frame("StartPage")).pack()

    
class IdentifyBodyExtremity(tk.Frame):

  def __init__(self, parent, controller):
  
    tk.Frame.__init__(self, parent)
    self.controller = controller
    label = tk.Label(self, text="Prepare Config File", font=controller.title_font)
    label.pack(side="top", fill="x", pady=10)
    
    tk.Button(self, text="Click on the tip of the tail of the same zebrafish.", command=lambda: controller.chooseBodyExtremity(controller)).pack()
    
    tk.Label(self, text="Example:", font=("Helvetica", 10)).pack(side="top", fill="x", pady=10)
    
    canvas = Canvas(self, width=2500, height=2000)
    canvas.pack()
    cur_dir_path = os.path.dirname(os.path.realpath(__file__))
    img = PhotoImage(file=os.path.join(cur_dir_path, 'blobExtremity.png'))
    self.img = img
    canvas.create_image(20, 20, anchor=NW, image=img)
    
    tk.Button(self, text="Go to the start page", bg="light cyan", command=lambda: controller.show_frame("StartPage")).pack()


class GoToAdvanceSettings(tk.Frame):

  def __init__(self, parent, controller):
  
    tk.Frame.__init__(self, parent)
    self.controller = controller
    label = tk.Label(self, text="Prepare Config File", font=controller.title_font)
    label.pack(side="top", fill="x", pady=10)
    
    tk.Label(self, text="Do you want to detect bouts movements and/or further adjust tracking parameters?", font=("Helvetica", 12)).pack(side="top", fill="x", pady=10)
    
    yes = IntVar()
    Checkbutton(self, text="Yes", variable=yes).pack()
    tk.Label(self, text="").pack()
    
    no = IntVar()
    Checkbutton(self, text="No", variable=no).pack()
    tk.Label(self, text="").pack()
    
    tk.Button(self, text="Next", bg="light yellow", command=lambda: controller.goToAdvanceSettings(controller, yes.get(), no.get())).pack()
    
    tk.Button(self, text="Go to the start page", bg="light cyan", command=lambda: controller.show_frame("StartPage")).pack()


class FinishConfig(tk.Frame):

  def __init__(self, parent, controller):
  
    tk.Frame.__init__(self, parent)
    self.controller = controller
    
    tk.Label(self, text="Choose a name for the config file you want to create. Don't put any file extension here. For example, you could type: myconfig", font=("Helvetica", 10)).pack(side="top", fill="x", pady=10)
    
    configFileNameToSave = tk.Entry(self)
    configFileNameToSave.pack()
    
    if (globalVariables["mac"] or globalVariables["lin"]):
      tk.Button(self, text="Save Config File (this will also close this window, restart it afterwards)", bg="light yellow", command=lambda: controller.finishConfig(controller, configFileNameToSave.get())).pack()
    else:
      tk.Button(self, text="Save Config File", bg="light yellow", command=lambda: controller.finishConfig(controller, configFileNameToSave.get())).pack()

