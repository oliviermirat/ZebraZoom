from zebrazoom.code.adjustHyperparameters import adjustFreelySwimTrackingParams
from zebrazoom.code.tracking.fasterMultiprocessing import FasterMultiprocessing
from zebrazoom.code.tracking import register_tracking_method
from ._base import BaseGUITrackingMethod


class GUIFasterMultiprocessing(FasterMultiprocessing, BaseGUITrackingMethod):
  def _adjustParameters(self, i, frame, widgets):
    if self._hyperparameters["adjustFreelySwimTracking"]:
      i, widgets = adjustFreelySwimTrackingParams(self._nbTailPoints, i, self._firstFrame, self._trackingHeadTailAllAnimalsList[self._firstWell], self._trackingHeadingAllAnimalsList[self._firstWell], frame, frame, self._hyperparameters, widgets)
    else:
      return None
    return i, widgets


register_tracking_method('fasterMultiprocessing', GUIFasterMultiprocessing)
