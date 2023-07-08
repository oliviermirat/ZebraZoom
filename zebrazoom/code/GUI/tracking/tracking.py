import json
import os

import cv2
import numpy as np

from PyQt5.QtWidgets import QApplication

import zebrazoom.code.util as util
from zebrazoom.code.adjustHyperparameters import adjustFreelySwimTrackingParams, adjustFreelySwimTrackingAutoParams, adjustHeadEmbededTrackingParams
from zebrazoom.code.tracking.tracking import Tracking
from zebrazoom.code.tracking import register_tracking_method
from ._base import BaseGUITrackingMethod


class GUITracking(Tracking, BaseGUITrackingMethod):
  def _adjustParameters(self, i, initialCurFrame, frame, frame2, back, widgets):
    if self._hyperparameters["adjustHeadEmbededTracking"] == 1:
      i, widgets = adjustHeadEmbededTrackingParams(self._nbTailPoints, i, self._firstFrame, self._trackingHeadTailAllAnimals, self._trackingHeadingAllAnimals, frame, frame2, self._hyperparameters, widgets)
      self._adjustHeadEmbededHyperparameters(frame)
    elif self._hyperparameters["adjustFreelySwimTracking"] == 1:
      i, widgets = adjustFreelySwimTrackingParams(self._nbTailPoints, i, self._firstFrame, self._trackingHeadTailAllAnimals, self._trackingHeadingAllAnimals, frame, frame2, self._hyperparameters, widgets)
    elif self._hyperparameters["adjustFreelySwimTrackingAutomaticParameters"] == 1:
      # Preparing image to show
      if self._hyperparameters["recalculateForegroundImageBasedOnBodyArea"] == 1:
        minPixelDiffForBackExtract = self._hyperparameters["minPixelDiffForBackExtractBody"]
      else:
        if self._hyperparameters["adjustMinPixelDiffForBackExtract_nbBlackPixelsMax"]:
          minPixelDiffForBackExtract = self._hyperparameters["minPixelDiffForBackExtractHead"]
          del self._hyperparameters["minPixelDiffForBackExtractHead"] # Not sure why this is necessary: need to check the code to make sure there isn't a bug somewhere
        else:
          minPixelDiffForBackExtract = self._hyperparameters["minPixelDiffForBackExtract"]
      curFrame = initialCurFrame
      putToWhite = (curFrame.astype('int32') >= (back.astype('int32') - minPixelDiffForBackExtract) )
      curFrame[putToWhite] = 255
      ret, frame2 = cv2.threshold(curFrame, self._hyperparameters["thresholdForBlobImg"], 255, cv2.THRESH_BINARY)
      # Showing current image and waiting for next parameter/frame change
      i, widgets = adjustFreelySwimTrackingAutoParams(self._nbTailPoints, i, self._firstFrame, self._trackingHeadTailAllAnimals, self._trackingHeadingAllAnimals, frame, frame2, self._hyperparameters, widgets)
      # Puts self._hyperparameters values to accepted values
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

  def _getCoordinates(self, frame, title, zoomable, dialog):
    return util.getPoint(frame, title, zoomable=zoomable, dialog=dialog)

  def _addBlackLineToImgSetParameters(self, frame):
    hyperparametersToSave = {"addBlackLineToImg_Width": 0}

    frame2 = frame.copy()
    # frame2 = 255 - frame2
    quartileChose = self._hyperparameters["outputValidationVideoContrastImprovementQuartile"]
    lowVal  = int(np.quantile(frame2, quartileChose))
    highVal = int(np.quantile(frame2, 1 - quartileChose))
    frame2[frame2 < lowVal]  = lowVal
    frame2[frame2 > highVal] = highVal
    frame2 = frame2 - lowVal
    mult  = np.max(frame2)
    frame2 = frame2 * (255/mult)
    frame2 = frame2.astype('uint8')

    addNewSegment  = True

    while addNewSegment:

      startPoint = self._getCoordinates(frame2, "Click on beginning of segment to set to black pixels", False, True)
      endPoint = util.getLine(frame2, "Click on the end of the segment to set to black pixels", self._hyperparameters["addBlackLineToImg_Width"], startPoint)

      if not("imagePreProcessMethod" in self._hyperparameters) or type(self._hyperparameters["imagePreProcessMethod"]) == int or len(self._hyperparameters["imagePreProcessMethod"]) == 0:
        self._hyperparameters["imagePreProcessMethod"]     = ["setImageLineToBlack"]
        self._hyperparameters["imagePreProcessParameters"] = [[startPoint[0], startPoint[1], endPoint[0], endPoint[1], self._hyperparameters["addBlackLineToImg_Width"]]]
        hyperparametersToSave["imagePreProcessMethod"]     = ["setImageLineToBlack"]
        hyperparametersToSave["imagePreProcessParameters"] = [[startPoint[0], startPoint[1], endPoint[0], endPoint[1], self._hyperparameters["addBlackLineToImg_Width"]]]
      else:
        self._hyperparameters["imagePreProcessMethod"] = self._hyperparameters["imagePreProcessMethod"] + ["setImageLineToBlack"]
        self._hyperparameters["imagePreProcessParameters"] += [[startPoint[0], startPoint[1], endPoint[0], endPoint[1], self._hyperparameters["addBlackLineToImg_Width"]]]
        hyperparametersToSave["imagePreProcessMethod"]     += ["setImageLineToBlack"]
        hyperparametersToSave["imagePreProcessParameters"] += [[startPoint[0], startPoint[1], endPoint[0], endPoint[1], self._hyperparameters["addBlackLineToImg_Width"]]]

      print('addBlackLineToImg_Width is at', self._hyperparameters["addBlackLineToImg_Width"],', so in the configuration file, "imagePreProcessMethod" has just been set to ["setImageLineToBlack"] and "imagePreProcessParameters" has just been set to', str(self._hyperparameters["imagePreProcessParameters"]))

      frame2 = cv2.line(frame2, (startPoint[0], startPoint[1]), (endPoint[0], endPoint[1]), (255, 255, 255), self._hyperparameters["addBlackLineToImg_Width"])

      def doneAddingSegments():
        nonlocal addNewSegment
        addNewSegment = False
      buttons = (("I want to add another segment.", None), ("I've added enough segments.", doneAddingSegments))
      self._debugFrame(frame2, title="Do you want to add another segment?", buttons=buttons)

  def findHeadPositionByUserInput(self, frame, frameNumber, wellNumber):
    plus = 0

    def tailNotStraight(frameWidget):
      nonlocal plus
      plus += 1
      util.setPixmapFromCv(self.headEmbededFrame(frameNumber + plus, wellNumber)[0], frameWidget, zoomable=True)
    return list(util.getPoint(np.uint8(frame * 255), "Click on the base of the tail", zoomable=True, extraButtons=(("Tail is not straight", tailNotStraight, False),),
                              dialog=not hasattr(QApplication.instance(), 'window')))

  def findTailTipByUserInput(self, frame, frameNumber, wellNumber):
    plus = 0

    def tailNotStraight(frameWidget):
      nonlocal plus
      plus += 1
      util.setPixmapFromCv(self.headEmbededFrame(frameNumber + plus, wellNumber)[0], frameWidget, zoomable=True)
    return list(util.getPoint(np.uint8(frame * 255), "Click on tail tip", zoomable=True, extraButtons=(("Tail is not straight", tailNotStraight, False),),
                              dialog=not hasattr(QApplication.instance(), 'window')))


register_tracking_method('tracking', GUITracking)
