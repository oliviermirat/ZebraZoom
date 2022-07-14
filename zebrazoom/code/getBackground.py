import numpy as np
import cv2
from zebrazoom.code.preprocessImage import preprocessImage, preprocessBackgroundImage
import zebrazoom.videoFormatConversion.zzVideoReading as zzVideoReading


def getBackground(videoPath, hyperparameters):
  
  cap   = zzVideoReading.VideoCapture(videoPath)
  max_l = int(cap.get(7))

  backCalculationStep = hyperparameters["backCalculationStep"]
  if ("firstFrame" in hyperparameters) and (hyperparameters["backgroundExtractionForceUseAllVideoFrames"] == 0):
    firstFrame = hyperparameters["firstFrame"]
  else:
    firstFrame = 1
  if ("lastFrame" in hyperparameters) and (hyperparameters["backgroundExtractionForceUseAllVideoFrames"] == 0):
    lastFrame  = hyperparameters["lastFrame"]
  else:
    lastFrame  = max_l - 10
  debugExtractBack    = hyperparameters["debugExtractBack"]
  
  if backCalculationStep == -1:
    backCalculationStep = int((lastFrame - firstFrame) / hyperparameters["nbImagesForBackgroundCalculation"])
    if backCalculationStep <= 1:
      backCalculationStep = 1
  
  ret, back = cap.read()
  if ret and hyperparameters["invertBlackWhiteOnImages"]:
    back = 255 - back
  back = cv2.cvtColor(back, cv2.COLOR_BGR2GRAY)
  if hyperparameters["backgroundExtractionWithOnlyTwoFrames"] == 0:
    for k in range(firstFrame,lastFrame):
      if (k % backCalculationStep == 0):
        cap.set(1, k)
        ret, frame = cap.read()
        if ret and hyperparameters["invertBlackWhiteOnImages"]:
          frame = 255 - frame
        if debugExtractBack:
          print(k)
        if ret:
          frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
          if hyperparameters["extractBackWhiteBackground"]:
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
          if hyperparameters["invertBlackWhiteOnImages"]:
            frame = 255 - frame
          frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
          diff  = np.sum(np.abs(frame - back))
          if diff > maxDiff:
            maxDiff    = diff
            indMaxDiff = k
    cap.set(1, indMaxDiff)
    ret, frame = cap.read()
    if ret:
      if hyperparameters["invertBlackWhiteOnImages"]:
        frame = 255 - frame
      frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
      if hyperparameters["extractBackWhiteBackground"]:
        back = cv2.max(frame, back)
      else:
        back = cv2.min(frame, back)
    else:
      print("couldn't use the frame", k, "for the background extraction")
  
  if hyperparameters["backgroundPreProcessMethod"]:
    back = preprocessBackgroundImage(back, hyperparameters)
  
  if hyperparameters["checkThatMovementOccurInVideo"]:
    cap.set(1, firstFrame)
    ret, frame = cap.read()
    if ret:
      if hyperparameters["invertBlackWhiteOnImages"]:
        frame = 255 - frame
      frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
      if hyperparameters["imagePreProcessMethod"]:
        frame = preprocessBackgroundImage(frame, hyperparameters)
      if type(frame[0][0]) == np.ndarray:
        frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
      putToWhite = (frame.astype('int32') >= (back.astype('int32')-hyperparameters["minPixelDiffForBackExtract"]))
      frame[putToWhite] = 255
    firstImage = frame
    maxDiff    = 0
    indMaxDiff = firstFrame
    for k in range(firstFrame,lastFrame):
      if (k % backCalculationStep == 0):
        cap.set(1, k)
        ret, frame = cap.read()
        if ret:
          if hyperparameters["invertBlackWhiteOnImages"]:
            frame = 255 - frame
          frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
          if hyperparameters["imagePreProcessMethod"]:
            frame = preprocessBackgroundImage(frame, hyperparameters)
          if type(frame[0][0]) == np.ndarray:
            frame = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
          putToWhite = (frame.astype('int32') >= (back.astype('int32')-hyperparameters["minPixelDiffForBackExtract"]))
          frame[putToWhite] = 255
          if hyperparameters["checkThatMovementOccurInVideoMedianFilterWindow"]:
            diff  = np.sum(cv2.medianBlur(np.abs(frame - firstImage), hyperparameters["checkThatMovementOccurInVideoMedianFilterWindow"]))
          else:
            diff  = np.sum(np.abs(frame - firstImage))
          if diff > maxDiff:
            maxDiff    = diff
            indMaxDiff = k
    print("checkThatMovementOccurInVideo: max difference is:", maxDiff)
    if maxDiff < hyperparameters["checkThatMovementOccurInVideo"]:
      back[:, :] = 0 # TODO: tracking should NOT RUN after background is set to 0 as it is here
  
  if hyperparameters["setBackgroundToImageMedian"]:
    back[:, :] = np.median(back)
  
  if debugExtractBack:
    from PyQt5.QtCore import Qt
    from PyQt5.QtWidgets import QLabel, QVBoxLayout

    import zebrazoom.code.util as util

    label = QLabel()
    label.setMinimumSize(1, 1)
    layout = QVBoxLayout()
    layout.addWidget(label, alignment=Qt.AlignmentFlag.AlignCenter)
    timeout = 3000 if hyperparameters["exitAfterBackgroundExtraction"] else None
    util.showDialog(layout, title="Background Extracted", labelInfo=(back, label), timeout=timeout)
  cap.release()
  
  print("Background Extracted")
  if hyperparameters["popUpAlgoFollow"]:
    import zebrazoom.code.popUpAlgoFollow as popUpAlgoFollow
    popUpAlgoFollow.prepend("Background Extracted")
  
  return back
