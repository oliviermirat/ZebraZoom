import math
import cv2

class UpdateBackgroundAtIntervalMixin:
  def _updateBackgroundAtInterval(self, i, wellNumber, initialCurFrame, trackingHeadTailAllAnimals, frame):
    if i % self._hyperparameters["updateBackgroundAtInterval"] == 0:
      showImages = False
      firstFrameToShow = -1
      if showImages and i > firstFrameToShow:
        self._debugFrame(self._background, title='background before')
      xvalues = [trackingHeadTailAllAnimals[0, i-self._firstFrame][k][0] for k in range(0, len(trackingHeadTailAllAnimals[0, i-self._firstFrame]))]
      yvalues = [trackingHeadTailAllAnimals[0, i-self._firstFrame][k][1] for k in range(0, len(trackingHeadTailAllAnimals[0, i-self._firstFrame]))]
      xmin = min(xvalues)
      xmax = max(xvalues)
      ymin = min(yvalues)
      ymax = max(yvalues)
      dist = 1 * math.sqrt((xmax - xmin) ** 2 + (ymax - ymin) ** 2)
      xmin = int(xmin - dist) if xmin - dist >= 0 else 0
      xmax = int(xmax + dist) if xmax + dist < len(frame[0]) else len(frame[0]) - 1
      ymin = int(ymin - dist) if ymin - dist >= 0 else 0
      ymax = int(ymax + dist) if ymax + dist < len(frame) else len(frame) - 1
      if xmin != xmax and ymin != ymax:
        partOfBackgroundToSave = self._background[self._wellPositions[wellNumber]["topLeftY"]+ymin:self._wellPositions[wellNumber]["topLeftY"]+ymax, self._wellPositions[wellNumber]["topLeftX"]+xmin:self._wellPositions[wellNumber]["topLeftX"]+xmax].copy() # copy ???
        if showImages and i > firstFrameToShow:
          self._debugFrame(partOfBackgroundToSave, title='partOfBackgroundToSave')
      self._background[self._wellPositions[wellNumber]["topLeftY"]:self._wellPositions[wellNumber]["topLeftY"]+self._wellPositions[wellNumber]["lengthY"], self._wellPositions[wellNumber]["topLeftX"]:self._wellPositions[wellNumber]["topLeftX"]+self._wellPositions[wellNumber]["lengthX"]] = initialCurFrame.copy()
      if showImages and i > firstFrameToShow:
        self._debugFrame(self._background, title='background middle')
      if xmin != xmax and ymin != ymax:
        self._background[self._wellPositions[wellNumber]["topLeftY"]+ymin:self._wellPositions[wellNumber]["topLeftY"]+ymax, self._wellPositions[wellNumber]["topLeftX"]+xmin:self._wellPositions[wellNumber]["topLeftX"]+xmax] = partOfBackgroundToSave
      if showImages and i > firstFrameToShow:
        self._debugFrame(self._background, title='background after')

  def _updateBackgroundAtIntervalRememberLastFrame(self, i, wellNumber, initialCurFrame, lastFrameRememberedForBackgroundExtract):
    if (i - self._firstFrame) % self._hyperparameters["updateBackgroundAtIntervalRememberLastFrame"] == 0:
      if i != self._firstFrame:
        if self._hyperparameters["extractBackWhiteBackground"]:
          self._background = cv2.max(initialCurFrame, lastFrameRememberedForBackgroundExtract)
        else:
          self._background = cv2.min(initialCurFrame, lastFrameRememberedForBackgroundExtract)
      return initialCurFrame
    else:
      return lastFrameRememberedForBackgroundExtract
