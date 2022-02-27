import numpy as np

import zebrazoom.code.util as util


@util.addToHistory
def headEmbededGUI(self, controller, blackBack, whiteBack, noBoutDetect, boutDetection, tweakTrackingParamsYes,
tweakTrackingParamsNo):

  self.configFile["invertBlackWhiteOnImages"] = int(whiteBack)
  self.configFile["extractBackWhiteBackground"] = 0

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
    # self.configFile["noBoutsDetection"] = 0
    self.configFile["extractAdvanceZebraParameters"] = 1
    self.calculateBackground(controller, 0)
  else:
    self.configFile["noBoutsDetection"] = 1
    controller.show_frame("FinishConfig")
