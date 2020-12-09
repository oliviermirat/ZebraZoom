import tkinter as tk
from tkinter import font  as tkfont
from tkinter import filedialog
from tkinter import ttk
from tkinter import *


class HeadEmbeded(tk.Frame):

  def __init__(self, parent, controller):
  
    tk.Frame.__init__(self, parent)
    self.controller = controller
    label = tk.Label(self, text="Prepare Config File", font=controller.title_font)
    label.pack(side="top", fill="x", pady=10)
    
    #####
    
    tk.Label(self, text="Choose only one of the options below:", font=("Helvetica", 12)).pack(side="top", fill="x", pady=10)
    
    blackBack = IntVar()
    Checkbutton(self, text="Black background, white zebrafish.", variable=blackBack).pack()
    
    whiteBack = IntVar()
    Checkbutton(self, text="White background, black zebrafish.", variable=whiteBack).pack()
    
    tk.Label(self, text="").pack()
    
    #####
    
    tk.Label(self, text="Do you want ZebraZoom to detect bouts of movement?", font=("Helvetica", 12)).pack(side="top", fill="x", pady=10)
    
    noBoutDetect = IntVar()
    Checkbutton(self, text="No. I want the tracking data for all frames of the videos.", variable=noBoutDetect).pack()
    
    boutDetection = IntVar()
    Checkbutton(self, text="Yes. I want the tracking data only when the fish is moving.", variable=boutDetection).pack()
    
    tk.Label(self, text="").pack()
    
    #####

    tk.Label(self, text="Do you want to try to tweak tracking parameters further?", font=("Helvetica", 12)).pack(side="top", fill="x", pady=10)
    
    tk.Label(self, text="Warning: further tweaking tracking parameters could make tracking results worse; please try without this option first.").pack()
    
    tweakTrackingParamsYes = IntVar()
    Checkbutton(self, text="Yes", variable=tweakTrackingParamsYes).pack()
    
    tweakTrackingParamsNo  = IntVar()
    Checkbutton(self, text="No", variable=tweakTrackingParamsNo).pack()
    tk.Label(self, text="").pack()
    
    #####
    
    tk.Button(self, text="Next", command=lambda: controller.headEmbededGUI(controller, blackBack.get(), whiteBack.get(), noBoutDetect.get(), boutDetection.get(), tweakTrackingParamsYes.get(), tweakTrackingParamsNo.get())).pack()
    
    tk.Button(self, text="Go to the start page", command=lambda: controller.show_frame("StartPage")).pack()

