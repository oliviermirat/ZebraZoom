import math

import cv2

import zebrazoom.code.tracking
import zebrazoom.code.tracking.customTrackingImplementations
from zebrazoom.code.tracking.customTrackingImplementations.fastFishTracking.utilities import calculateAngle
from zebrazoom.code.adjustHyperparameters import adjustHyperparameters


baseClass = zebrazoom.code.tracking.get_tracking_method('fastFishTracking.tracking')


class GUITracking(baseClass):
  def _adjustParameters(self, i, frame, widgets):
    if not self._hyperparameters['adjustFreelySwimTracking']:
      return None # TODO: ensure chooseListOfWells param is temporarily set to 0; ensure this for bout detection too?
    assert self._hyperparameters['onlyTrackThisOneWell'] != -1
    hyperparametersListNames = ["maxDepth", "paramGaussianBlur"]
    organizationTab = [
    [1, max(50, int(self._hyperparameters["maxDepth"] * 1.33)), "Should be set to the length (in pixels) of the fish."],
    [1, 30, "Window of the gaussian filter applied on the fish."],]

    title = "Adjust parameters in order for the background to be white and the animals to be gray/black."

    frame2 = cv2.cvtColor(frame,cv2.COLOR_GRAY2RGB)
    wellNumber = self._hyperparameters['onlyTrackThisOneWell']
    nbTailPoints = self._hyperparameters['nbTailPoints']
    for k in range(0, self._hyperparameters["nbAnimalsPerWell"]):
      output = self._trackingDataPerWell[wellNumber]
      if self._hyperparameters["trackTail"] == 1:
        for j in range(0, nbTailPoints):
          x = int(output[k, i-self._firstFrame][j][0])
          y = int(output[k, i-self._firstFrame][j][1])
          cv2.circle(frame2, (x, y), 1, (0, 255, 0),   -1)
      x = int(output[k, i-self._firstFrame][nbTailPoints-1][0])
      y = int(output[k, i-self._firstFrame][nbTailPoints-1][1])
      cv2.circle(frame2, (x, y), 2, (0, 0, 255),   -1)
      x = output[k, i-self._firstFrame][0][0]
      y = output[k, i-self._firstFrame][0][1]

    return adjustHyperparameters(i, self._hyperparameters, hyperparametersListNames, frame2, title, organizationTab, widgets)


zebrazoom.code.tracking.register_tracking_method('fastFishTracking.tracking', GUITracking)