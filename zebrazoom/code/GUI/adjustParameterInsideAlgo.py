import tkinter as tk
from tkinter import font  as tkfont
from tkinter import filedialog
from tkinter import ttk
from tkinter import *


class AdujstParamInsideAlgo(tk.Frame):

  def __init__(self, parent, controller):
  
    tk.Frame.__init__(self, parent)
    self.controller = controller
    label = tk.Label(self, text="Advanced Parameter adjustment", font=controller.title_font)
    label.pack(side="top", fill="x", pady=10)
    
    tk.Label(self, text="Recalculate background using this number of images: (default is 60)", font=("Helvetica", 10)).pack(side="top", fill="x", pady=10)
    nbImagesForBackgroundCalculation = tk.Entry(self)
    nbImagesForBackgroundCalculation.pack()
    tk.Button(self, text="Recalculate", command=lambda: controller.calculateBackground(controller, nbImagesForBackgroundCalculation.get())).pack()
    
    tk.Label(self, text="", pady=5).pack()
    firstFrameParamAdjust = IntVar()
    adjustOnWholeVideo    = IntVar()
    Checkbutton(self, text="Choose the first frame for parameter adjustment (for both bouts detection and tracking)", variable=firstFrameParamAdjust).pack()
    Checkbutton(self, text="I want to adjust parameters over the entire video, not only on 500 frames at a time.", variable=adjustOnWholeVideo).pack()
    tk.Label(self, text="", pady=5).pack()
    
    tk.Button(self, text="Adjust Bouts Detection", command=lambda: controller.detectBouts(controller, "0", firstFrameParamAdjust.get(), adjustOnWholeVideo.get())).pack()
    tk.Label(self, text="The aim here is to adjust parameters in order for the red dot on the top left of the image to appear when and only when movement is occurring.", font=("Helvetica", 10)).pack(side="top", fill="x", pady=10)
    tk.Label(self, text="WARNING: if you don't want ZebraZoom to detect bouts, don't click on the button above.", font=("Helvetica", 10)).pack(side="top", fill="x", pady=0)
    tk.Label(self, text="", font=("Helvetica", 0)).pack(side="top", fill="x", pady=0)
    
    tk.Button(self, text="Adjust Tracking", command=lambda: controller.adjustHeadEmbededTracking(controller, "0", firstFrameParamAdjust.get(), adjustOnWholeVideo.get())).pack()
    
    tk.Label(self, text="WARNING: only click the button above if you've tried to track without adjusting these parameters first. Trying to adjust these could make the tracking worse.", font=("Helvetica", 10)).pack(side="top", fill="x", pady=0)
    tk.Label(self, text='Warning: for some of the "overwrite" parameters, you will need to change the initial value for the "overwrite" to take effect.', font=("Helvetica", 10)).pack(side="top", fill="x", pady=0)
    tk.Label(self, text='', font=("Helvetica", 10)).pack(side="top", fill="x", pady=0)
    
    tk.Button(self, text="Next", command=lambda: controller.show_frame("FinishConfig")).pack()
    

class AdujstParamInsideAlgoFreelySwim(tk.Frame):

  def __init__(self, parent, controller):
  
    tk.Frame.__init__(self, parent)
    self.controller = controller
    label = tk.Label(self, text="Advanced Parameter adjustment", font=controller.title_font)
    label.pack(side="top", fill="x", pady=10)
    
    tk.Label(self, text="Well number used to adjust parameters (leave blank to get the default value of 0)", font=("Helvetica", 10)).pack(side="top", fill="x", pady=10)
    wellNumber = tk.Entry(self)
    wellNumber.pack()
    
    tk.Label(self, text="Recalculate background using this number of images: (default is 60)", font=("Helvetica", 10)).pack(side="top", fill="x", pady=10)
    nbImagesForBackgroundCalculation = tk.Entry(self)
    nbImagesForBackgroundCalculation.pack()
    tk.Button(self, text="Recalculate", command=lambda: controller.calculateBackgroundFreelySwim(controller, nbImagesForBackgroundCalculation.get())).pack()
    
    tk.Label(self, text="", pady=5).pack()
    firstFrameParamAdjust = IntVar()
    adjustOnWholeVideo    = IntVar()
    Checkbutton(self, text="Choose the first frame for parameter adjustment (for both bouts detection and tracking)", variable=firstFrameParamAdjust).pack()
    Checkbutton(self, text="I want to adjust parameters over the entire video, not only on 500 frames at a time.", variable=adjustOnWholeVideo).pack()
    tk.Label(self, text="", pady=5).pack()
    
    tk.Button(self, text="Adjust Bouts Detection", command=lambda: controller.detectBouts(controller, wellNumber.get(), firstFrameParamAdjust.get(), adjustOnWholeVideo.get())).pack()
    tk.Label(self, text="The aim here is to adjust parameters in order for the red dot on the top left of the image to appear when and only when movement is occurring.", font=("Helvetica", 10)).pack(side="top", fill="x", pady=10)
    tk.Label(self, text="WARNING: if you don't want ZebraZoom to detect bouts, don't click on the button above.", font=("Helvetica", 10)).pack(side="top", fill="x", pady=0)
    tk.Label(self, text="", font=("Helvetica", 0)).pack(side="top", fill="x", pady=0)
    
    tk.Button(self, text="Adjust Tracking", command=lambda: controller.adjustFreelySwimTracking(controller, wellNumber.get(), firstFrameParamAdjust.get(), adjustOnWholeVideo.get())).pack()
    tk.Label(self, text="WARNING: only click the button above if you've tried to track without adjusting these parameters first. Trying to adjust these could make the tracking worse.", font=("Helvetica", 10)).pack(side="top", fill="x", pady=0)
    tk.Label(self, text='', font=("Helvetica", 10)).pack(side="top", fill="x", pady=0)
    
    tk.Button(self, text="Next", command=lambda: controller.show_frame("FinishConfig")).pack()
