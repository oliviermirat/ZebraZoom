import os
import tkinter as tk
from tkinter import font  as tkfont
from tkinter import filedialog
from tkinter import ttk
from tkinter import *
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
    
    tk.Button(self, text="Select the video you want to create a configuration file for.", command=lambda: controller.chooseVideoToCreateConfigFileFor(controller, reloadConfigFile.get())).pack()
    
    tk.Label(self, text='').pack()
    tk.Label(self, text="(you will be able to use the configuration file you create for all videos that are similar to that video)").pack()
    tk.Label(self, text="").pack()
    
    tk.Button(self, text="Go to the start page", command=lambda: controller.show_frame("StartPage")).pack()
    
    tk.Label(self, text='').pack()
    tk.Label(self, text='Warning: This procedure to create configuration files is incomplete.').pack()
    tk.Label(self, text='You may not succeed at making a good configuration file to analyze your video.').pack()
    tk.Label(self, text="If you don't manage to get a good configuration file that fits your needs, email us at info@zebrazoom.org.").pack()


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

    freeZebra2 = IntVar()
    Checkbutton(self, text="NEW BETA VERSION: Track heads and tails of freely swimming fish.", variable=freeZebra2).pack()
    tk.Label(self, text="The fish must be in one well of any shape or in several circular wells. Each well should contain the same number of fish.").pack()
    tk.Label(self, text="").pack()
    
    tk.Button(self, text="Next", command=lambda: controller.chooseGeneralExperiment(controller, freeZebra.get(), headEmbZebra.get(), drosophilia.get(), rodent.get(), other.get(), freeZebra2.get())).pack()
    
    tk.Button(self, text="Go to the start page", command=lambda: controller.show_frame("StartPage")).pack()


class WellOrganisation(tk.Frame):

  def __init__(self, parent, controller):
  
    tk.Frame.__init__(self, parent)
    self.controller = controller
    label = tk.Label(self, text="Prepare Config File", font=controller.title_font)
    label.pack(side="top", fill="x", pady=10)
    
    tk.Label(self, text="Choose only one of the options below:", font=("Helvetica", 12)).pack(side="top", fill="x", pady=10)
    
    circular = IntVar()
    Checkbutton(self, text="Circular Wells", variable=circular).pack()
    
    rectangular = IntVar()
    Checkbutton(self, text="Rectangular Wells", variable=rectangular).pack()
    
    roi = IntVar()
    Checkbutton(self, text="Choose Region of Interest", variable=roi).pack()
    other = IntVar()
    Checkbutton(self, text="Whole video", variable=other).pack()
    
    
    tk.Button(self, text="Next", command=lambda: controller.wellOrganisation(controller, circular.get(), rectangular.get(), roi.get(), other.get())).pack()
    
    tk.Button(self, text="Go to the start page", command=lambda: controller.show_frame("StartPage")).pack()


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
    
    tk.Button(self, text="Next", command=lambda: controller.circularOrRectangularWells(controller, nbwells.get(), nbRowsOfWells.get(), nbWellsPerRows.get())).pack()
    
    tk.Button(self, text="Go to the start page", command=lambda: controller.show_frame("StartPage")).pack()


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
    
    tk.Button(self, text="Go to the start page", command=lambda: controller.show_frame("StartPage")).pack()


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
    
    tk.Button(self, text="Go to the start page", command=lambda: controller.show_frame("StartPage")).pack()


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
    tk.Button(self, text="Next", command=lambda: controller.numberOfAnimals(controller, nbanimals.get(), yes.get(), noo.get(), forceBlobMethodForHeadTracking.get())).pack()
    tk.Label(self, text="", font=("Helvetica", 10)).pack(side="top", fill="x", pady=10)
    tk.Button(self, text="Go to the start page", command=lambda: controller.show_frame("StartPage")).pack()


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
    
    tk.Button(self, text="Go to the start page", command=lambda: controller.show_frame("StartPage")).pack()

    
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
    
    tk.Button(self, text="Go to the start page", command=lambda: controller.show_frame("StartPage")).pack()


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
    
    tk.Button(self, text="Next", command=lambda: controller.goToAdvanceSettings(controller, yes.get(), no.get())).pack()
    
    tk.Button(self, text="Go to the start page", command=lambda: controller.show_frame("StartPage")).pack()


class FinishConfig(tk.Frame):

  def __init__(self, parent, controller):
  
    tk.Frame.__init__(self, parent)
    self.controller = controller
    
    tk.Label(self, text="Choose a name for the config file you want to create. Don't put any file extension here. For example, you could type: myconfig", font=("Helvetica", 10)).pack(side="top", fill="x", pady=10)
    
    configFileNameToSave = tk.Entry(self)
    configFileNameToSave.pack()
    
    if (globalVariables["mac"] or globalVariables["lin"]):
      tk.Button(self, text="Save Config File (this will also close this window, restart it afterwards)", command=lambda: controller.finishConfig(controller, configFileNameToSave.get())).pack()
    else:
      tk.Button(self, text="Save Config File", command=lambda: controller.finishConfig(controller, configFileNameToSave.get())).pack()

