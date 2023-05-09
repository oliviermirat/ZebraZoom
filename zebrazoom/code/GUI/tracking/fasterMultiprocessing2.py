import cv2

from zebrazoom.code.adjustHyperparameters import adjustFreelySwimTrackingParams, adjustFreelySwimTrackingAutoParams
from zebrazoom.code.tracking.fasterMultiprocessing2 import FasterMultiprocessing2
from zebrazoom.code.tracking import register_tracking_method
from ._base import BaseGUITrackingMethod


class GUIFasterMultiprocessing2(FasterMultiprocessing2, BaseGUITrackingMethod):
  def _adjustParameters(self, i, back, frame, initialCurFrame, widgets):
    if self._hyperparameters["adjustFreelySwimTracking"]:
      i, widgets = adjustFreelySwimTrackingParams(self._nbTailPoints, i, self._firstFrame, self._trackingHeadTailAllAnimalsList[self._firstWell], self._trackingHeadingAllAnimalsList[self._firstWell], frame, frame, self._hyperparameters, widgets)
    elif self._hyperparameters["adjustFreelySwimTrackingAutomaticParameters"]:
      # Preparing image to show
      if self._hyperparameters["recalculateForegroundImageBasedOnBodyArea"] and "minPixelDiffForBackExtractBody" in self._hyperparameters:
          minPixelDiffForBackExtract = self._hyperparameters["minPixelDiffForBackExtractBody"]
      else:
        if self._hyperparameters["adjustMinPixelDiffForBackExtract_nbBlackPixelsMax"] and "minPixelDiffForBackExtractHead" in self._hyperparameters:
          minPixelDiffForBackExtract = self._hyperparameters["minPixelDiffForBackExtractHead"]
          del self._hyperparameters["minPixelDiffForBackExtractHead"] # Not sure why this is necessary: need to check the code to make sure there isn't a bug somewhere
        else:
          minPixelDiffForBackExtract = self._hyperparameters["minPixelDiffForBackExtract"]
      curFrame = initialCurFrame.copy()
      putToWhite = (curFrame.astype('int32') >= (back.astype('int32') - minPixelDiffForBackExtract) )
      curFrame[putToWhite] = 255
      ret, frame2 = cv2.threshold(curFrame, self._hyperparameters["thresholdForBlobImg"], 255, cv2.THRESH_BINARY)
      # Showing current image and waiting for next parameter/frame change
      i, widgets = adjustFreelySwimTrackingAutoParams(self._nbTailPoints, i, self._firstFrame, self._trackingHeadTailAllAnimalsList[self._firstWell], self._trackingHeadingAllAnimalsList[self._firstWell], frame, frame2, self._hyperparameters, widgets)
      # Puts hyperparameters values to accepted values
      self._hyperparameters["recalculateForegroundImageBasedOnBodyArea"] = 0 if self._hyperparameters["recalculateForegroundImageBasedOnBodyArea"] < 0.5 else 1
      if self._hyperparameters["adjustMinPixelDiffForBackExtract_nbBlackPixelsMax"] < 0:
        self._hyperparameters["adjustMinPixelDiffForBackExtract_nbBlackPixelsMax"] = 0
      if self._hyperparameters["minPixelDiffForBackExtract"] < 0:
        self._hyperparameters["minPixelDiffForBackExtract"] = 0
      else:
        if self._hyperparameters["minPixelDiffForBackExtract"] > 255:
          self._hyperparameters["minPixelDiffForBackExtract"] = 255
      self._hyperparameters["minPixelDiffForBackExtract"] = int(self._hyperparameters["minPixelDiffForBackExtract"])
    else:
      return None
    return i, widgets


register_tracking_method('fasterMultiprocessing2', GUIFasterMultiprocessing2)
