import cv2

import zebrazoom.code.tracking
from zebrazoom.code.adjustHyperparameters import adjustHyperparameters


baseClass = zebrazoom.code.tracking.get_tracking_method('multipleCenterOfMassTracking')


class GUITracking(baseClass):
  def _adjustParameters(self, i, frame, unprocessedFrame, widgets):
    if not self._hyperparameters['adjustFreelySwimTracking']:
      return None

    hyperparametersListNames = ["backgroundSubtractorKNN_history", "backgroundSubtractorKNN_dist2Threshold", "paramGaussianBlur", "localMinimumDarkestThreshold", "headSize"]
    organizationTab = [
    [1, 30, "Number of previous frames taken into account to construct background model."],
    [1, 400, "Threshold for foreground pixel detection: increase to detect less foreground pixels."],
    [1, 50, "Window of gaussian filter applied on the image."],
    [1, 400, "Decrease to detect smaller animals, increase to avoid detecting them."],
    [1, self._hyperparameters['headSize'] * 1.3, "Minimum radius of animal, increase if multiple animals are detected where only one is present."],]
    title = "Adjust parameters in order for the background to be white and the animals to be gray/black."

    frame2 = unprocessedFrame if widgets is not None and 'unprocessedFrameCheckbox' in widgets and widgets['unprocessedFrameCheckbox'].isChecked() else cv2.cvtColor(frame, cv2.COLOR_GRAY2RGB)

    zoomInCheckbox = None if widgets is None or 'zoomInCheckbox' not in widgets else widgets['zoomInCheckbox']
    zoomInCoordinates = None
    for wellIdx in range(self._firstWell, self._lastWell + 1):
      for k in range(0, self._hyperparameters["nbAnimalsPerWell"]):
        output = self._trackingHeadTailAllAnimalsList[wellIdx][k]
        x = int(output[i-self._firstFrame][0][0])
        y = int(output[i-self._firstFrame][0][1])
        cv2.circle(frame2, (x, y), 2, (0, 0, 255),   -1)
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


zebrazoom.code.tracking.register_tracking_method('multipleCenterOfMassTracking', GUITracking)