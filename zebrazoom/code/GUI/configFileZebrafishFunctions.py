import numpy as np
import tkinter as tk
from tkinter import font  as tkfont
from tkinter import filedialog
from tkinter import ttk
from tkinter import *

def headEmbededGUI(self, controller, blackBack, whiteBack, noBoutDetect, boutDetection, tweakTrackingParamsYes, 
tweakTrackingParamsNo):
  
  # self.configFile["invertBlackWhiteOnImages"] = int(whiteBack)
  # self.configFile["headEmbededAutoSet_ExtendedDescentSearchOption"] = int(optionExtendedDescentSearchOption)
  # self.configFile["headEmbededAutoSet_BackgroundExtractionOption" ] = int(optionBackgroundExtractionOption) * 7
  
  self.configFile["extractBackWhiteBackground"] = int(whiteBack)
  
  self.configFile["automaticallySetSomeOfTheHeadEmbededHyperparameters"] = 1
  self.configFile["findHeadPositionByUserInput"] = 1

  self.configFile["detectBoutMinDist"] = -1
  self.configFile["detectBoutMinNbFrames" ] = 5
  self.configFile["detectBoutMinAngleDiff"] = 0.01
  self.configFile["minDiffBetweenSubsequentBendAmp"] = 0.01
  self.configFile["windowForLocalBendMinMaxFind"] = 3
  
  self.configFile["fillGapFrameNb"] = 5
  self.configFile["tailAngleMedianFilter"] = 3
  
  self.configFile["nbWells"] = 1
  self.configFile["nbList" ] = 20
  self.configFile["headEmbeded"] = 1
  self.configFile["headingCalculationMethod"] = "calculatedWithMedianTailTip"
  
  if int(boutDetection) or int(tweakTrackingParamsYes):
    self.configFile["noBoutsDetection"] = 0
    self.configFile["extractAdvanceZebraParameters"] = 1
    self.calculateBackground(controller, 0)
    # controller.show_frame("AdujstParamInsideAlgo")
  else:
    self.configFile["noBoutsDetection"] = 1
    controller.show_frame("FinishConfig")
  
