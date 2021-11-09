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


class AdujstParamInsideAlgoFreelySwimAutomaticParameters(tk.Frame):

  def __init__(self, parent, controller):
  
    tk.Frame.__init__(self, parent)
    self.controller = controller
    label = tk.Label(self, text="Fish tail tracking parameters adjustment", font=controller.title_font, pady=30)
    label.grid(row=0,column=0, columnspan = 2)
    
    tk.Label(self, text="Well number used to adjust parameters (leave blank to get the default value of 0)", font=("Helvetica", 10)).grid(row=1,column=0)
    wellNumber = tk.Entry(self)
    wellNumber.grid(row=2,column=0)
    
    tk.Label(self, text="Recalculate background using this number of images: (default is 60)", font=("Helvetica", 10)).grid(row=1,column=1)
    nbImagesForBackgroundCalculation = tk.Entry(self)
    nbImagesForBackgroundCalculation.grid(row=2,column=1)
    tk.Button(self, text="Recalculate", command=lambda: controller.calculateBackgroundFreelySwim(controller, nbImagesForBackgroundCalculation.get(), False, True)).grid(row=3,column=1)
    
    # tk.Label(self, text="", pady=5).grid(row=1,column=0)
    firstFrameParamAdjust = IntVar()
    adjustOnWholeVideo    = IntVar()
    Checkbutton(self, text="Choose the first frame for parameter adjustment (for both bouts detection and tracking)", variable=firstFrameParamAdjust).grid(row=3,column=0)
    Checkbutton(self, text="I want to adjust parameters over the entire video, not only on 500 frames at a time.", variable=adjustOnWholeVideo).grid(row=4,column=0)
    # tk.Label(self, text="", pady=5).pack()
    
    tk.Label(self, text="", pady=8).grid(row=6,column=1)
    tk.Button(self, text="Adjust Tracking", command=lambda: controller.adjustFreelySwimTrackingAutomaticParameters(controller, wellNumber.get(), firstFrameParamAdjust.get(), adjustOnWholeVideo.get())).grid(row=7,column=0, columnspan = 2)
    tk.Label(self, text="").grid(row=8,column=1)
    tk.Label(self, text="The tracking of ZebraZoom can rely on three different background extraction methods:").grid(row=9,column=0, columnspan = 2)
    tk.Label(self, text="Method 1: background extraction is based on a simple threshold on pixel intensity. This method is the fastest.").grid(row=10,column=0, columnspan = 2)
    tk.Label(self, text="Method 2: the background extraction threshold is automatically chosen in order for the fish body area to be close to a predefined area. This method is slower but often more accurate.").grid(row=11,column=0, columnspan = 2)
    tk.Label(self, text="Method 3: the background extraction threshold is automatically chosen on a ROI in order for the fish body area to be close to a predefined area. This method is the slowest but often the most accurate.").grid(row=12,column=0, columnspan = 2)
    tk.Label(self, text="It is usually advise to choose the method 3, but there are many circumstances in which method 1 or 2 are better.").grid(row=13,column=0, columnspan = 2)
    tk.Label(self, text="The 'Adjust Tracking' method above will allow you to choose which method you want to use and to adjust parameters related to this method.").grid(row=14,column=0, columnspan = 2)
    tk.Label(self, text="WARNING: only click the button above if you've tried to track without adjusting these parameters first. Trying to adjust these could make the tracking worse.", font=("Helvetica", 10)).grid(row=15,column=0, columnspan = 2)
    
    tk.Label(self, text="", font=("Helvetica", 10), pady=5).grid(row=16,column=0, columnspan = 2)
    tk.Button(self, text="Save New Configuration File", command=lambda: controller.show_frame("FinishConfig")).grid(row=17,column=0, columnspan = 2)
    tk.Label(self, text="", font=("Helvetica", 10), pady=5).grid(row=18,column=0, columnspan = 2)

    tk.Button(self, text="Go to the start page", bg="light cyan", command=lambda: controller.show_frame("StartPage")).grid(row=19,column=0, columnspan = 2)


class AdujstBoutDetectionOnly(tk.Frame):

  def __init__(self, parent, controller):
  
    tk.Frame.__init__(self, parent)
    self.controller = controller
    label = tk.Label(self, text="Bout detection configuration file parameters adjustments", font=controller.title_font)
    label.pack(side="top", fill="x", pady=10)
    
    tk.Label(self, text="Well number used to adjust parameters (leave blank to get the default value of 0)", font=("Helvetica", 10)).pack(side="top", fill="x", pady=10)
    wellNumber = tk.Entry(self)
    wellNumber.pack()
    
    tk.Label(self, text="Recalculate background using this number of images: (default is 60)", font=("Helvetica", 10)).pack(side="top", fill="x", pady=10)
    nbImagesForBackgroundCalculation = tk.Entry(self)
    nbImagesForBackgroundCalculation.pack()
    tk.Button(self, text="Recalculate", command=lambda: controller.calculateBackgroundFreelySwim(controller, nbImagesForBackgroundCalculation.get(), False, False, True)).pack()
    
    tk.Label(self, text="", pady=5).pack()
    firstFrameParamAdjust = IntVar()
    adjustOnWholeVideo    = IntVar()
    Checkbutton(self, text="Choose the first frame for parameter adjustment (for both bouts detection and tracking)", variable=firstFrameParamAdjust).pack()
    Checkbutton(self, text="I want to adjust parameters over the entire video, not only on 500 frames at a time.", variable=adjustOnWholeVideo).pack()
    tk.Label(self, text="", pady=5).pack()
    
    tk.Button(self, text="Adjust Bouts Detection", command=lambda: controller.detectBouts(controller, wellNumber.get(), firstFrameParamAdjust.get(), adjustOnWholeVideo.get())).pack()
    tk.Label(self, text="The aim here is to adjust parameters in order for the red dot on the top left of the image to appear when and only when movement is occurring.", font=("Helvetica", 10)).pack(side="top", fill="x", pady=10)
    
    tk.Label(self, text="", font=("Helvetica", 0)).pack(side="top", fill="x", pady=0)
    tk.Label(self, text="Important: Bouts Merging:", font=("Helvetica", 0)).pack(side="top", fill="x", pady=0)
    fillGapFrameNb = tk.Entry(self)
    fillGapFrameNb.pack()
    tk.Button(self, text="With the box above, update the 'fillGapFrameNb' parameter that controls the distance (in number frames) under which two subsquent bouts are merged into one.", command=lambda: controller.updateFillGapFrameNb(fillGapFrameNb.get())).pack()    
    tk.Label(self, text="", font=("Helvetica", 0)).pack(side="top", fill="x", pady=0)
    
    tk.Button(self, text="Next", command=lambda: controller.show_frame("FinishConfig")).pack()
    
    tk.Button(self, text="Go to the start page", bg="light cyan", command=lambda: controller.show_frame("StartPage")).pack()