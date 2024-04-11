import numpy as np
import cv2

import zebrazoom.videoFormatConversion.zzVideoReading as zzVideoReading
from zebrazoom.code.preprocessImage import preprocessBackgroundImage


class GetBackgroundMixin:
  def _getBackground(self):
    cap   = zzVideoReading.VideoCapture(self._videoPath, self._hyperparameters)
    max_l = int(cap.get(7))

    backCalculationStep = self._hyperparameters["backCalculationStep"]
    if ("firstFrameForBackExtract" in self._hyperparameters) and ("lastFrameForBackExtract" in self._hyperparameters) and self._hyperparameters["firstFrameForBackExtract"] != -1 and self._hyperparameters["lastFrameForBackExtract"] != -1:
      firstFrame = self._hyperparameters["firstFrameForBackExtract"]
      lastFrame  = self._hyperparameters["lastFrameForBackExtract"]
    else:
      if ("firstFrame" in self._hyperparameters) and (self._hyperparameters["backgroundExtractionForceUseAllVideoFrames"] == 0):
        firstFrame = self._hyperparameters["firstFrame"]
      else:
        firstFrame = 1
      if ("lastFrame" in self._hyperparameters) and (self._hyperparameters["backgroundExtractionForceUseAllVideoFrames"] == 0):
        lastFrame  = self._hyperparameters["lastFrame"]
      else:
        lastFrame  = max_l - 10

    debugExtractBack    = self._hyperparameters["debugExtractBack"]

    if backCalculationStep == -1:
      backCalculationStep = int((lastFrame - firstFrame) / self._hyperparameters["nbImagesForBackgroundCalculation"])
      if backCalculationStep <= 1:
        backCalculationStep = 1

    cap.set(1, firstFrame)
    ret, back = cap.read()

    if self._hyperparameters["useFirstFrameAsBackground"]:
      if self._hyperparameters["invertBlackWhiteOnImages"]:
        back = 255 - back
      back = cv2.cvtColor(back, cv2.COLOR_BGR2GRAY)
      if self._hyperparameters["backgroundPreProcessMethod"]:
        back = preprocessBackgroundImage(back, self._hyperparameters)
      if debugExtractBack:
        self._debugFrame(back, title="Background Extracted", timeout = 3000 if self._hyperparameters["exitAfterBackgroundExtraction"] else None)
      cap.release()
      print("Background Extracted from first frame")
      return back
      
    if "lastFrameForInitialBackDetect" in self._hyperparameters and self._hyperparameters["lastFrameForInitialBackDetect"]:
      if int(self._hyperparameters["lastFrame"]) <= self._hyperparameters["lastFrameForInitialBackDetect"]:
        cap.set(cv2.CAP_PROP_POS_FRAMES, int(self._hyperparameters["lastFrame"]) - 1)
      else:
        cap.set(cv2.CAP_PROP_POS_FRAMES, self._hyperparameters["lastFrameForInitialBackDetect"])
      ret, frame = cap.read()
      back = cv2.max(frame, back)
      back = cv2.cvtColor(back, cv2.COLOR_BGR2GRAY)
      cap.release()
      print("Background Extracted from first frame and frame " + str(self._hyperparameters["lastFrameForInitialBackDetect"]))
      return back

    if ret and self._hyperparameters["invertBlackWhiteOnImages"]:
      back = 255 - back
    back = cv2.cvtColor(back, cv2.COLOR_BGR2GRAY)
    if self._hyperparameters["backgroundExtractionWithOnlyTwoFrames"] == 0:
      for k in range(firstFrame,lastFrame):
        if (k % backCalculationStep == 0):
          cap.set(1, k)
          ret, frame = cap.read()
          if ret and self._hyperparameters["invertBlackWhiteOnImages"]:
            frame = 255 - frame
          if debugExtractBack:
            print(k)
          if ret:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            if self._hyperparameters["extractBackWhiteBackground"]:
              back = cv2.max(frame, back)
            else:
              back = cv2.min(frame, back)
          else:
            print("couldn't use the frame", k, "for the background extraction")
    else:
      maxDiff    = 0
      indMaxDiff = firstFrame
      for k in range(firstFrame,lastFrame):
        if (k % backCalculationStep == 0):
          cap.set(1, k)
          ret, frame = cap.read()
          if ret:
            if self._hyperparameters["invertBlackWhiteOnImages"]:
              frame = 255 - frame
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            diff  = np.sum(np.abs(frame - back))
            if diff > maxDiff:
              maxDiff    = diff
              indMaxDiff = k
      cap.set(1, indMaxDiff)
      ret, frame = cap.read()
      if ret:
        if self._hyperparameters["invertBlackWhiteOnImages"]:
          frame = 255 - frame
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        if self._hyperparameters["extractBackWhiteBackground"]:
          back = cv2.max(frame, back)
        else:
          back = cv2.min(frame, back)
      else:
        print("couldn't use the frame", k, "for the background extraction")

    if self._hyperparameters["backgroundPreProcessMethod"]:
      back = preprocessBackgroundImage(back, self._hyperparameters)

    if self._hyperparameters["checkThatMovementOccurInVideo"]:
      cap.set(1, firstFrame)
      ret, frame = cap.read()
      if ret:
        if self._hyperparameters["invertBlackWhiteOnImages"]:
          frame = 255 - frame
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        if self._hyperparameters["imagePreProcessMethod"]:
          frame = preprocessBackgroundImage(frame, self._hyperparameters)
        if type(frame[0][0]) == np.ndarray:
          frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        putToWhite = (frame.astype('int32') >= (back.astype('int32')-self._hyperparameters["minPixelDiffForBackExtract"]))
        frame[putToWhite] = 255
      firstImage = frame
      maxDiff    = 0
      indMaxDiff = firstFrame
      for k in range(firstFrame,lastFrame):
        if (k % backCalculationStep == 0):
          cap.set(1, k)
          ret, frame = cap.read()
          if ret:
            if self._hyperparameters["invertBlackWhiteOnImages"]:
              frame = 255 - frame
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            if self._hyperparameters["imagePreProcessMethod"]:
              frame = preprocessBackgroundImage(frame, self._hyperparameters)
            if type(frame[0][0]) == np.ndarray:
              frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            putToWhite = (frame.astype('int32') >= (back.astype('int32')-self._hyperparameters["minPixelDiffForBackExtract"]))
            frame[putToWhite] = 255
            if self._hyperparameters["checkThatMovementOccurInVideoMedianFilterWindow"]:
              diff  = np.sum(cv2.medianBlur(np.abs(frame - firstImage), self._hyperparameters["checkThatMovementOccurInVideoMedianFilterWindow"]))
            else:
              diff  = np.sum(np.abs(frame - firstImage))
            if diff > maxDiff:
              maxDiff    = diff
              indMaxDiff = k
      print("checkThatMovementOccurInVideo: max difference is:", maxDiff)
      if maxDiff < self._hyperparameters["checkThatMovementOccurInVideo"]:
        back[:, :] = 0 # TODO: tracking should NOT RUN after background is set to 0 as it is here

    if self._hyperparameters["setBackgroundToImageMedian"]:
      back[:, :] = np.median(back)

    if debugExtractBack:
      self._debugFrame(back, title="Background Extracted", timeout = 3000 if self._hyperparameters["exitAfterBackgroundExtraction"] else None)
    cap.release()

    print("Background Extracted")
    if self._hyperparameters["popUpAlgoFollow"]:
      import zebrazoom.code.popUpAlgoFollow as popUpAlgoFollow
      popUpAlgoFollow.prepend("Background Extracted")

    return back


def getBackground(videoPath, hyperparameters):
  obj = GetBackgroundMixin()
  obj._videoPath = videoPath
  obj._hyperparameters = hyperparameters
  return obj._getBackground()
