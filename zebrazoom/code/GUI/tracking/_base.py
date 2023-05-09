import cv2
import numpy as np

import zebrazoom.code.util as util
from zebrazoom.code.adjustHyperparameters import adjustHeadEmbeddedEyeTrackingParamsEllipse, adjustHeadEmbeddedEyeTrackingParamsSegment
from zebrazoom.code.tracking import BaseZebraZoomTrackingMethod


class BaseGUITrackingMethod(BaseZebraZoomTrackingMethod):
  def _debugFrame(self, frame, title=None, buttons=(), timeout=None):
    util.showFrame(frame, title=title, buttons=buttons, timeout=timeout)

  def _debugTracking(self, frameNumber: int, output: list, outputHeading: list, frame2: np.array) -> None:
    if not self._hyperparameters["debugTracking"]:
      return

    if type(frame2[0][0]) == int or type(frame2[0][0]) == np.uint8:
      frame2 = cv2.cvtColor(frame2,cv2.COLOR_GRAY2RGB)

    for k in range(0, self._hyperparameters["nbAnimalsPerWell"]):
      for j in range(0, self._nbTailPoints):
        x = int(output[k, frameNumber-self._firstFrame][j][0])
        y = int(output[k, frameNumber-self._firstFrame][j][1])
        cv2.circle(frame2, (x, y), 1, (0, 255, 0),   -1)
      x = int(output[k, frameNumber-self._firstFrame][self._nbTailPoints-1][0]) # it used to be 10 instead of 9 here, not sure why
      y = int(output[k, frameNumber-self._firstFrame][self._nbTailPoints-1][1]) # it used to be 10 instead of 9 here, not sure why
      cv2.circle(frame2, (x, y), 2, (0, 0, 255),   -1)

      x = output[k, frameNumber-self._firstFrame][0][0]
      y = output[k, frameNumber-self._firstFrame][0][1]
      # cv2.line(frame2, (int(x / getRealValueCoefX), int(y / getRealValueCoefY)), (int((x+20*math.cos(outputHeading[k, i-self._firstFrame])) / getRealValueCoefX), int((y+20*math.sin(outputHeading[k, i-self._firstFrame])) / getRealValueCoefY)), (255,0,0), 3)

    if self._hyperparameters["debugTrackingPtExtremeLargeVerticals"]: # Put this to True for large resolution videos (to be able to see on your screen what's happening)
      frame2 = frame2[int(y-200):len(frame2), :]

    self._debugFrame(frame2, title='Tracked frame')

  def _adjustHeadEmbeddedEyeTrackingParamsSegment(self, i, colorFrame, widgets):
    return adjustHeadEmbeddedEyeTrackingParamsSegment(i, colorFrame, self._hyperparameters, widgets)

  def _adjustHeadEmbeddedEyeTrackingParamsEllipse(self, i, colorFrame, widgets):
    return adjustHeadEmbeddedEyeTrackingParamsEllipse(i, colorFrame, self._hyperparameters, widgets)
