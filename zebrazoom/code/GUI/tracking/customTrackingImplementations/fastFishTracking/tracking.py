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
    name = self.itemlist[index.row() // 2]
    return util.PRETTY_PARAMETER_NAMES.get(name, name)

  def updateSteps(self, newSteps):
    listSize = len(self.itemlist)
    currentSteps = listSize - (self.itemlist.index('steps') + 1)
    difference = newSteps - currentSteps
    if difference > 0:
      self.beginInsertRows(QModelIndex(), listSize * 2 - 1, (listSize + difference) * 2 - 1)
      self.itemlist.extend((f'Step {currentSteps + 1 + idx}' for idx in range(difference)))
      self.endInsertRows()
    elif difference < 0:
      self.beginRemoveRows(QModelIndex(), listSize * 2 - 1 + difference * 2, listSize * 2 - 2)
      del self.itemlist[difference:]
      self.endRemoveRows()


class GUITracking(baseClass):
  def _adjustParameters(self, i, frame, widgets):
    if not self._hyperparameters['adjustFreelySwimTracking']:
      return None
    assert self._hyperparameters['onlyTrackThisOneWell'] != -1
    hyperparametersListNames = ["maxDepth", "paramGaussianBlur", "headEmbededParamTailDescentPixThreshStop", _CustomListModel(["thetaDiffAccept", "thetaDiffAcceptAfterAuthorizedRelativeLengthTailEnd", "thetaDiffAcceptAfterAuthorizedRelativeLengthTailEnd2", 'nbList', 'nbListAfterAuthorizedRelativeLengthTailEnd', 'nbListAfterAuthorizedRelativeLengthTailEnd2', 'authorizedRelativeLengthTailEnd', 'authorizedRelativeLengthTailEnd2', 'maximumMedianValueOfAllPointsAlongTheTail', 'minimumHeadPixelValue', 'nbTailPoints', 'steps'])]
    organizationTab = [
    [1, 50, "Target length of the tail"],
    [1, 30, "Window of gaussian blur filter applied on the image"],
    [1, 300, "Maximum pixel intensity authorized for a pixel to be considered inside the tail"],
    ([1, 6, 'Maximum authorized angle difference between two subsequent segments in the first portion of the tail (in radians)'],
     [1, 6, 'Maximum authorized angle difference between two subsequent segments in the second portion of the tail  (in radians)'],
     [1, 6, 'Maximum authorized angle difference between two subsequent segments in the third portion of the tail  (in radians)'],
     [1, 30, 'Number of "candidates" points considered for next point along the tail in the first portion of the tail'],
     [1, 30, 'Number of "candidates" points considered for next point along the tail in the second portion of the tail'],
     [1, 30, 'Number of "candidates" points considered for next point along the tail in the third portion of the tail'],
     [0, 1, 'Cut off relative location between first and second tail segment (between 0 and 1)'],
     [0, 1, 'Cut off relative location between second and third tail segment (between 0 and 1)'],
     [1, 300, 'Maximum median pixel value of all points along the tail in order for the tail tracking to be accepted'],
     [1, 300, 'Maximum pixel value authorized for a point to be considered as the head of the animal'],
     [1, 20, 'Number of points along the tail in the output data'],
     [1, 10, 'List of possible number of pixels between two subsequent points along the tail'],),]

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