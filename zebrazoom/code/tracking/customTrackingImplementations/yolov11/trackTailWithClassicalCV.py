from zebrazoom.code.tracking.customTrackingImplementations.fastFishTracking.trackTail import trackTail
import cv2

def trackTailWithClassicalCV(self, frame, frameGaussianBlurForHeadPosition, xmin, ymin, xmax, ymax, wellNum, animalNum, frameNum):
  
  # import pdb
  # pdb.set_trace()
  margin = 30
  xmin = xmin - margin if xmin - margin >= 0 else 0
  ymin = ymin - margin if ymin - margin >= 0 else 0
  xmax = xmax + margin if xmax + margin < len(frame[0]) else len(frame[0]) - 1
  ymax = ymax + margin if ymax + margin < len(frame) else len(frame) - 1
  
  frameROIGaussianBlurForHeadPosition = frameGaussianBlurForHeadPosition[int(ymin):int(ymax), int(xmin):int(xmax)].copy()
  frameROIGaussianBlurForHeadPosition = cv2.cvtColor(frameROIGaussianBlurForHeadPosition, cv2.COLOR_BGR2GRAY)
  
  frameROI = frame[int(ymin):int(ymax), int(xmin):int(xmax)].copy()
  frameROI = cv2.cvtColor(frameROI, cv2.COLOR_BGR2GRAY)
  
  # import zebrazoom.code.util as util
  # util.showFrame(frameROI, title="tailTracking")
  
  (minVal, maxVal, headPosition, maxLoc) = cv2.minMaxLoc(frameROIGaussianBlurForHeadPosition)
  
  self._trackingHeadTailAllAnimalsList[wellNum][animalNum, frameNum-self._firstFrame][0][0] = headPosition[0] + xmin - self._wellPositions[wellNum]['topLeftX']
  self._trackingHeadTailAllAnimalsList[wellNum][animalNum, frameNum-self._firstFrame][0][1] = headPosition[1] + ymin - self._wellPositions[wellNum]['topLeftY']
  
  # Tail Tracking
  if not("onlyRecenterHeadPosition" in self._hyperparameters) or (self._hyperparameters["onlyRecenterHeadPosition"] == 0):
    a, self._lastFirstTheta[wellNum] = trackTail(self, frameROI, headPosition, self._hyperparameters, wellNum, frameNum, self._lastFirstTheta[wellNum])
    if len(a):
      a[0, :, 0] += int(xmin) - self._wellPositions[wellNum]['topLeftX']
      a[0, :, 1] += int(ymin) - self._wellPositions[wellNum]['topLeftY']
      self._trackingHeadTailAllAnimalsList[wellNum][animalNum][frameNum-self._firstFrame][:len(a[0])] = a
    else:
      self._trackingHeadTailAllAnimalsList[wellNum][animalNum][frameNum-self._firstFrame] = self._trackingHeadTailAllAnimalsList[wellNum][animalNum][frameNum-self._firstFrame-1]
      # animalNotTracked[animalId] = 1