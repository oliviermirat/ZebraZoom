import math

import cv2

import zebrazoom.code.tracking
import zebrazoom.code.tracking.customTrackingImplementations
import zebrazoom.code.util as util
from zebrazoom.code.tracking.customTrackingImplementations.fastFishTracking.utilities import calculateAngle
from zebrazoom.code.adjustHyperparameters import adjustHyperparameters

from PyQt5.QtCore import Qt, QAbstractListModel, QModelIndex


baseClass = zebrazoom.code.tracking.get_tracking_method('fastFishTracking.tracking')


class _CustomListModel(QAbstractListModel):
  def __init__(self, list_, *args, **kwargs):
    super().__init__(*args, **kwargs)
    self.itemlist = list_
    self._baseItemCount = len(list_)

  def rowCount(self, parent=QModelIndex()):
    itemCount = len(self.itemlist)
    return itemCount * 2 - 1

  def data(self, index, role):
    if not index.isValid():
      return None
    if role == Qt.AccessibleDescriptionRole and index.row() % 2:
      return 'separator'
    if role != Qt.DisplayRole:
      return None
    idx = index.row() // 2
    currentSteps = len(self.itemlist) - self._baseItemCount
    stepIdx = idx - self.itemlist.index('steps')
    if 0 < stepIdx <= currentSteps:
      return f'Segment length between previous and next point: option {stepIdx}'
    name = self.itemlist[idx]
    return util.PRETTY_PARAMETER_NAMES.get(name, name)

  def updateSteps(self, newSteps):
    listSize = len(self.itemlist)
    currentSteps = listSize - self._baseItemCount
    lastStepIdx = self.itemlist.index('steps') + currentSteps
    difference = newSteps - currentSteps
    if difference > 0:
      startIdx = lastStepIdx * 2 - 1
      self.beginInsertRows(QModelIndex(), startIdx, startIdx + difference * 2 - 1)
      self.itemlist[lastStepIdx+1:lastStepIdx+1] = (f'Step {currentSteps + 1 + idx}' for idx in range(difference))
      self.endInsertRows()
    elif difference < 0:
      startIdx = (lastStepIdx + difference + 2) - 1
      self.beginRemoveRows(QModelIndex(), startIdx, startIdx - difference * 2 - 1)
      del self.itemlist[startIdx:startIdx-difference]
      self.endRemoveRows()


class GUITracking(baseClass):
  def _adjustParameters(self, i, frame, unprocessedFrame, widgets):
    if not self._hyperparameters['adjustFreelySwimTracking']:
      return None
    assert self._hyperparameters['onlyTrackThisOneWell'] != -1

    def trackingAlgorithmChanged(idx, hyperparameters):
      params = ('dualDirectionTailDetection', 'dualDirectionRemoveShortestDirectionFromHead')
      paramsToSet = {'dualDirectionTailDetection'} if idx == 1 else {'dualDirectionTailDetection', 'dualDirectionRemoveShortestDirectionFromHead'} if idx == 2 else set()
      for param in params:
        if param in paramsToSet:
          hyperparameters[param] = 1
        else:
          if param in hyperparameters:
            del hyperparameters[param]

    def getTrackingAlgorithmIndex(hyperparameters):
      params = (None, 'dualDirectionTailDetection', 'dualDirectionRemoveShortestDirectionFromHead')
      for param in reversed(params[1:]):
        if hyperparameters.get(param, False):
          return params.index(param)
      return 0

    hyperparametersListNames = ["maxDepth", "paramGaussianBlur", "headEmbededParamTailDescentPixThreshStop", _CustomListModel(['steps', "thetaDiffAccept", "thetaDiffAcceptAfterAuthorizedRelativeLengthTailEnd", "thetaDiffAcceptAfterAuthorizedRelativeLengthTailEnd2", 'nbList', 'nbListAfterAuthorizedRelativeLengthTailEnd', 'nbListAfterAuthorizedRelativeLengthTailEnd2', 'authorizedRelativeLengthTailEnd', 'authorizedRelativeLengthTailEnd2', 'maximumMedianValueOfAllPointsAlongTheTail', 'minimumHeadPixelValue', 'nbTailPoints', 'paramGaussianBlurForHeadPosition']), ('dualDirectionTailDetection', 'dualDirectionRemoveShortestDirectionFromHead')]
    organizationTab = [
    [1, 50, "Target length of the tail"],
    [1, 30, "Window of gaussian blur filter applied on the image"],
    [1, 300, "Maximum pixel intensity authorized for a pixel to be considered inside the tail"],
    ([1, 10, 'List of possible number of pixels between two subsequent points along the tail'],
     [0.01, 6, 'Maximum authorized angle difference between two subsequent segments in the first portion of the tail (in radians)'],
     [0.01, 6, 'Maximum authorized angle difference between two subsequent segments in the second portion of the tail  (in radians)'],
     [0.01, 6, 'Maximum authorized angle difference between two subsequent segments in the third portion of the tail  (in radians)'],
     [1, 30, 'Number of "candidates" points considered for next point along the tail in the first portion of the tail'],
     [1, 30, 'Number of "candidates" points considered for next point along the tail in the second portion of the tail'],
     [1, 30, 'Number of "candidates" points considered for next point along the tail in the third portion of the tail'],
     [0, 1, 'Cut off relative location between first and second tail segment (between 0 and 1)'],
     [0, 1, 'Cut off relative location between second and third tail segment (between 0 and 1)'],
     [1, 300, 'Maximum median pixel value of all points along the tail in order for the tail tracking to be accepted'],
     [1, 300, 'Maximum pixel value authorized for a point to be considered as the head of the animal'],
     [1, 20, 'Number of points along the tail in the output data'],
     [1, 30, "Window of gaussian blur filter applied on the image when calculating head position"],),
    ['Tracking algorithm', ('Default algorithm: tail descent by segments from head', 'Descent by segments from head in both directions', 'Descent by segments from head in both directions: remove the shortest direction'), trackingAlgorithmChanged, getTrackingAlgorithmIndex],]

    title = "Adjust parameters in order for the background to be white and the animals to be gray/black."

    frame2 = unprocessedFrame if widgets is not None and 'unprocessedFrameCheckbox' in widgets and widgets['unprocessedFrameCheckbox'].isChecked() else cv2.cvtColor(frame, cv2.COLOR_GRAY2RGB)
    zoomInCheckbox = None if widgets is None or 'zoomInCheckbox' not in widgets else widgets['zoomInCheckbox']
    zoomInCoordinates = None
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
      if zoomInCheckbox is not None and zoomInCheckbox.isChecked() and zoomInCheckbox.getAnimalIdx() == k:
        zoomInCoordinates = (x, y)

    if zoomInCoordinates is not None:
      x, y = zoomInCoordinates
      halfLength = 125.5
      xmin = int(x - halfLength)
      xmax = int(x + halfLength)
      ymin = int(y - halfLength)
      ymax = int(y + halfLength)

      x = max(xmin, 0)
      y = max(ymin, 0)
      lengthX = xmax - xmin
      lengthY = ymax - ymin

      frameHeight, frameWidth = frame.shape[:2]
      if y + lengthY >= frameHeight:
        lengthY = frameHeight - y - 1
      if x + lengthX >= frameWidth:
        lengthX = frameWidth - x - 1

      frame2 = frame2[y:y+lengthY, x:x+lengthX]

    return adjustHyperparameters(i, self._hyperparameters, hyperparametersListNames, frame2, title, organizationTab, widgets, addZoomCheckbox=True, addUnprocessedFrameCheckbox=True)


zebrazoom.code.tracking.register_tracking_method('fastFishTracking.tracking', GUITracking)