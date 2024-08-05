import math
import os

import cv2
import numpy as np
from numpy import linspace
from scipy.interpolate import interp1d
from scipy.interpolate import splprep, splev
from scipy.optimize import curve_fit

from ._centerOfMassTailTracking import CenterOfMassTailTrackingMixin
from ._tailExtremityTracking import TailTrackingExtremityDetectMixin
from ._headEmbeddedTailTracking import HeadEmbeddedTailTrackingMixin
from ._headEmbeddedTailTrackingForImage import HeadEmbeddedTailTrackingForImageMixin
from ._headEmbeddedTailTrackingTeresaNicolson import HeadEmbeddedTailTrackingTeresaNicolsonMixin
from ._tailTrackingBlobDescent import TailTrackingBlobDescentMixin


class TailTrackingMixin(HeadEmbeddedTailTrackingMixin, CenterOfMassTailTrackingMixin, HeadEmbeddedTailTrackingTeresaNicolsonMixin, TailTrackingBlobDescentMixin, TailTrackingExtremityDetectMixin, HeadEmbeddedTailTrackingForImageMixin):
  def _tailTracking(self, animalId, i, frame, thresh1, threshForBlackFrames, thetaDiffAccept, trackingHeadTailAllAnimals, trackingHeadingAllAnimals, lastFirstTheta, maxDepth, tailTip, initialCurFrame, back, wellNumber=-1, xmin=0, ymin=0):
    headPosition = [trackingHeadTailAllAnimals[animalId, i-self._firstFrame][0][0]-xmin, trackingHeadTailAllAnimals[animalId, i-self._firstFrame][0][1]-ymin]
    heading      = trackingHeadingAllAnimals[animalId, i-self._firstFrame]

    if (self._hyperparameters["headEmbeded"] == 1):
      # through the "head embeded" method, either through "segment descent" or "center of mass descent"

      if self._hyperparameters["headEmbededTeresaNicolson"] == 1:
        oppHeading = (heading + math.pi) % (2 * math.pi)
        trackingHeadTailAllAnimalsI = self._headEmbededTailTrackingTeresaNicolson(headPosition, frame, maxDepth, tailTip, threshForBlackFrames)
      else:
        oppHeading = (heading + math.pi) % (2 * math.pi) # INSERTED FOR THE REFACTORING
        if self._hyperparameters["centerOfMassTailTracking"] == 0:
          if self._hyperparameters["headEmbededTailTrackingForImage"] == 0:
            trackingHeadTailAllAnimalsI = self._headEmbededTailTracking(headPosition, i, frame, maxDepth, tailTip)
          else:
            trackingHeadTailAllAnimalsI, headingNew = self._headEmbededTailTrackingForImage(headPosition, i, frame, maxDepth, tailTip)
            trackingHeadingAllAnimals[animalId, i-self._firstFrame] = headingNew
        else:
          trackingHeadTailAllAnimalsI = self._centerOfMassTailTracking(headPosition, frame, maxDepth)

      if len(trackingHeadTailAllAnimalsI[0]) == len(trackingHeadTailAllAnimals[animalId, i-self._firstFrame]):
        trackingHeadTailAllAnimals[animalId, i-self._firstFrame] = trackingHeadTailAllAnimalsI

    else:
      if self._hyperparameters["freeSwimmingTailTrackingMethod"] == "tailExtremityDetect":
        # through the tail extremity descent method (original C++ method)
        [trackingHeadTailAllAnimalsI, newHeading] = self._tailTrackingExtremityDetect(headPosition, i, thresh1, frame, self._hyperparameters["debugTrackingPtExtreme"], heading, initialCurFrame, back, wellNumber)
        trackingHeadTailAllAnimals[animalId, i-self._firstFrame] = trackingHeadTailAllAnimalsI
        if newHeading != -1:
          trackingHeadingAllAnimals[animalId, i-self._firstFrame] = newHeading
      elif self._hyperparameters["freeSwimmingTailTrackingMethod"] == "blobDescent":
        # through the "blob descent" method
        trackingHeadTailAllAnimals[animalId, i-self._firstFrame] = self._tailTrackingBlobDescent(headPosition, i, thresh1, frame, lastFirstTheta, self._hyperparameters["debugTrackingPtExtreme"], thetaDiffAccept)
      else: # self._hyperparameters["freeSwimmingTailTrackingMethod"] == "none"
        # only tracking the head, not the tail
        trackingHeadTailAllAnimals[animalId, i-self._firstFrame][0][0] = headPosition[0]
        trackingHeadTailAllAnimals[animalId, i-self._firstFrame][0][1] = headPosition[1]
