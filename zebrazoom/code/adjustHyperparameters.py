import cv2
import cvui
import numpy as np
import pickle
import math
import tkinter as tk

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QApplication, QGridLayout, QLabel, QVBoxLayout

import zebrazoom.code.util as util


def initializeAdjustHyperparametersWindows(WINDOW_NAME):
  if QApplication.instance() is not None:
    return
  cv2.destroyAllWindows()
  WINDOW_NAME_CTRL = "Adjust Parameters."
  cvui.init(WINDOW_NAME)
  cv2.moveWindow(WINDOW_NAME, 0, 0)
  cvui.init(WINDOW_NAME_CTRL)
  cv2.moveWindow(WINDOW_NAME_CTRL, 0, 300)


def _createWidget(layout, status, values, info, name, signalsForExit):
  minn, maxx, hint = info
  sublayout = QVBoxLayout()

  sublayout.addWidget(QLabel(name), alignment=Qt.AlignmentFlag.AlignCenter)
  slider = util.SliderWithSpinbox(values[name], minn, maxx)
  signalsForExit.append(slider.valueChanged)

  def showHint(fn):
    def inner(evt):
      status.setText(hint)
      return fn(evt)
    return inner
  slider.enterEvent = showHint(slider.enterEvent)

  def hideHint(fn):
    def inner(evt):
      status.setText(None)
      return fn(evt)
    return inner
  slider.leaveEvent = hideHint(slider.leaveEvent)

  def valueChanged():
    values[name] = slider.value()
  slider.valueChanged.connect(valueChanged)
  sublayout.addWidget(slider, alignment=Qt.AlignmentFlag.AlignCenter)

  if name != "Frame number":
    if (values[name] - minn) > (maxx - minn) * 0.9:
      maxx = minn + (values[name] - minn) * 1.25
    if maxx - minn > 255:
      if values[name] < minn + (maxx - minn) * 0.1:
        maxx = minn + (maxx - minn) * 0.9
    info[1] = maxx

    elements = layout.count() - 3  # frame, status, frameSlider
    row = elements // 2 + 3
    col = elements % 2
    if len(values) == 1:
      layout.addLayout(sublayout, row, col, 1, 2, Qt.AlignmentFlag.AlignCenter)
    else:
      layout.addLayout(sublayout, row, col, Qt.AlignmentFlag.AlignLeft if col else Qt.AlignmentFlag.AlignRight)
  else:
    layout.addLayout(sublayout, 2, 0, 1, 2, Qt.AlignmentFlag.AlignCenter)


def printStuffOnCtrlImg(frameCtrl, frameNum, x, y, l, minn, maxx, name, hint):
  cvui.text(frameCtrl, x, y, name)
  
  status = cvui.iarea(x, y, 350, 60)
  if status == cvui.OVER:
    cvui.text(frameCtrl, 4, 15, hint)
    
  if name != "Frame number":
    if (frameNum[0] - minn) > (maxx - minn) * 0.9:
      maxx = minn + (frameNum[0] - minn) * 1.25
    if maxx - minn > 255:
      if frameNum[0] < minn + (maxx - minn) * 0.1:
        maxx = minn + (maxx - minn) * 0.9

  cvui.trackbar(frameCtrl, x,      y+10, l, frameNum, minn, maxx)
  cvui.counter(frameCtrl,  x+l+10, y+20,    frameNum)
  
  return [minn, maxx]


def _adjustHyperparametersQt(l, hyperparameters, hyperparametersListNames, frameToShow, title, organizationTab):
  frameNum = {"Frame number": l}
  newhyperparameters = {name: hyperparameters[name] for name in hyperparametersListNames}

  layout = QGridLayout()
  frame = QLabel()
  layout.addWidget(frame, 0, 0, 1, 2, Qt.AlignmentFlag.AlignCenter)
  status = QLabel()
  layout.addWidget(status, 1, 0, 1, 2, Qt.AlignmentFlag.AlignCenter)

  signalsForExit = []
  _createWidget(layout, status, frameNum, (hyperparameters["firstFrame"], hyperparameters["lastFrame"] - 1, "You can also go through the video with the keys left arrow (backward); right arrow (forward); page down (fast backward); page up (fast forward)"), "Frame number", signalsForExit)
  for info, name in zip(organizationTab, hyperparametersListNames):
    _createWidget(layout, status, newhyperparameters, info, name, signalsForExit)

  saved = False
  discarded = False
  def saveClicked():
    nonlocal saved
    saved = True
  def discardClicked():
    nonlocal discarded
    discarded = True
  buttons = (("Done! Save changes!", saveClicked), ("Discard changes.", discardClicked))
  util.pageOrDialog(layout, title=title, buttons=buttons, dialog=False, labelInfo=(frameToShow, frame), signalsForExit=signalsForExit)

  hyperparameters.update(newhyperparameters)
  if saved:
    pickle.dump(newhyperparameters, open('newhyperparameters', 'wb'))
    raise ValueError
  if discarded:
    raise NameError

  return [frameNum["Frame number"], hyperparameters, organizationTab]


def adjustHyperparameters(l, hyperparameters, hyperparametersListNames, frameToShow, WINDOW_NAME, organizationTab):
  if QApplication.instance() is not None:
    return _adjustHyperparametersQt(l, hyperparameters, hyperparametersListNames, frameToShow, WINDOW_NAME, organizationTab)

  root = tk.Tk()
  horizontal = root.winfo_screenwidth()
  vertical   = root.winfo_screenheight()
  if len(frameToShow[0]) > horizontal or len(frameToShow) > vertical:
    frameToShow = cv2.resize(frameToShow, (int(horizontal*0.8), int(vertical*0.8)))
  root.destroy()
  
  WINDOW_NAME_CTRL = "Adjust Parameters."
  frameNum            = [l]
  hyperparametersList = [[hyperparameters[name]] for name in hyperparametersListNames]
  frameCtrlLengthY = math.ceil((len(hyperparametersListNames) + 2)/2) * 70 + 20
  
  buttonclicked = False
  buttonclicked2 = False
  while frameNum[0] == l and hyperparametersList == [[hyperparameters[name]] for name in hyperparametersListNames] and not(buttonclicked) and not(buttonclicked2):
    
    frameCtrl = np.full((frameCtrlLengthY, 1100), 100).astype('uint8')
    printStuffOnCtrlImg(frameCtrl, frameNum, 1, 35, 350, hyperparameters["firstFrame"], hyperparameters["lastFrame"], "Frame number", "You can also go through the video with the keys a or 4 (backward); d or 6 (forward); f or g (fast backward); h or j (fast forward)")
    for idx, hyperParamCurVal in enumerate(hyperparametersList):
      [minn, maxx] = printStuffOnCtrlImg(frameCtrl, hyperParamCurVal, organizationTab[idx][0], organizationTab[idx][1], organizationTab[idx][2], organizationTab[idx][3], organizationTab[idx][4], hyperparametersListNames[idx], organizationTab[idx][5])
      organizationTab[idx][3] = minn
      organizationTab[idx][4] = maxx
    
    buttonclicked = cvui.button(frameCtrl, organizationTab[len(organizationTab)-1][0], organizationTab[len(organizationTab)-1][1], "Done! Save changes!")
    buttonclicked2 = cvui.button(frameCtrl, organizationTab[len(organizationTab)-1][0]+170, organizationTab[len(organizationTab)-1][1], "Discard changes.")
    # cvui.text(frameCtrl, 100, 245, 'Warning: for some of the "overwrite" parameters, you will need to change the initial value for the "overwrite" to take effect.')
    cvui.imshow(WINDOW_NAME, frameToShow)
    cvui.imshow(WINDOW_NAME_CTRL, frameCtrl)
    r = cv2.waitKey(20)
    if (r == 54) or (r == 100) or (r == 0):
      frameNum[0] = frameNum[0] + 1
    elif (r == 52) or (r == 97) or (r == 113):
      frameNum[0] = frameNum[0] - 1
  l = int(frameNum[0])
  if l >= hyperparameters["lastFrame"]:
    l = hyperparameters["lastFrame"] - 1
  if l <= hyperparameters["firstFrame"]:
    l = hyperparameters["firstFrame"]
  
  for idx, hyperParamCurVal in enumerate(hyperparametersList):
    hyperparameters[hyperparametersListNames[idx]] = hyperParamCurVal[0]
  if buttonclicked:
    newhyperparameters = {}
    for idx, hyperparameterName in enumerate(hyperparametersListNames):
      newhyperparameters[hyperparameterName] = hyperparameters[hyperparameterName]
    pickle.dump(newhyperparameters, open('newhyperparameters', 'wb'))
    cv2.destroyAllWindows()
    raise ValueError
  if buttonclicked2:
    cv2.destroyAllWindows()
    raise NameError

  return [l, hyperparameters, organizationTab]


def _getDetectMouvRawVideosParamsForHyperParamAdjustsQt(img, res, l, totDiff, hyperparameters):
  hyperparametersListNames = ["frameGapComparision", "thresForDetectMovementWithRawVideo", "halfDiameterRoiBoutDetect", "minNbPixelForDetectMovementWithRawVideo"]
  organizationTab = [
  [0, 15,  "Increase if small movements are not detected. An increase that's too big could lead to a detection of bout that's too early however."],
  [0, 255, "Increase if too much movement is being detected."],
  [0, 500, "Controls the size of the images on which pixel change from image to the next are counted."],
  [0, 50,  "Increase if too much movement is being detected."],]
  WINDOW_NAME = "Red dot must appear only when movement is occuring"
  frameToShow = np.concatenate((img, res),axis=1)
  frameToShow = cv2.cvtColor(frameToShow,cv2.COLOR_GRAY2RGB)

  minDimension    = min(len(frameToShow), len(frameToShow[0]))
  redDotDimension = 20
  if minDimension < 200:
    redDotDimension = int(minDimension / 10)

  fontSize = redDotDimension/20
  tickness = int(3*fontSize) if int(3*fontSize) != 0 else 1
  frameToShow = cv2.putText(frameToShow, str(l), (2*redDotDimension, redDotDimension), cv2.FONT_HERSHEY_SIMPLEX, fontSize, (0,255,0), tickness)

  if totDiff > hyperparameters["minNbPixelForDetectMovementWithRawVideo"]:
    cv2.circle(frameToShow, (redDotDimension, redDotDimension), redDotDimension, (0,0,255), -1)
  return [hyperparametersListNames, frameToShow, WINDOW_NAME, organizationTab]


def getDetectMouvRawVideosParamsForHyperParamAdjusts(img, res, l, totDiff, hyperparameters):
  if QApplication.instance() is not None:
    return _getDetectMouvRawVideosParamsForHyperParamAdjustsQt(img, res, l, totDiff, hyperparameters)
  hyperparametersListNames = ["frameGapComparision", "thresForDetectMovementWithRawVideo", "halfDiameterRoiBoutDetect", "minNbPixelForDetectMovementWithRawVideo"]
  marginX = 30
  organizationTab = [\
  [470,  marginX + 5,  350,  0, 15,  "Increase if small movements are not detected. An increase that's too big could lead to a detection of bout that's too early however."],
  [1,    marginX + 71, 350,  0, 255, "Increase if too much movement is being detected."],
  [470,  marginX + 71, 350,  0, 500, "Controls the size of the images on which pixel change from image to the next are counted."],
  [1,   marginX + 137, 350,  0, 50,  "Increase if too much movement is being detected."],
  [470, marginX + 137,  -1, -1, -1,  "Click here once the red dot appears on enough images where movement is occurring."]]
  WINDOW_NAME = "Red dot must appear only when movement is occuring"
  frameToShow = np.concatenate((img, res),axis=1)
  frameToShow = cv2.cvtColor(frameToShow,cv2.COLOR_GRAY2RGB)
  
  minDimension    = min(len(frameToShow), len(frameToShow[0]))
  redDotDimension = 20
  if minDimension < 200:
    redDotDimension = int(minDimension / 10)
  
  fontSize = redDotDimension/20
  tickness = int(3*fontSize) if int(3*fontSize) != 0 else 1
  frameToShow = cv2.putText(frameToShow, str(l), (2*redDotDimension, redDotDimension), cv2.FONT_HERSHEY_SIMPLEX, fontSize, (0,255,0), tickness)
  
  if totDiff > hyperparameters["minNbPixelForDetectMovementWithRawVideo"]:
    cv2.circle(frameToShow, (redDotDimension, redDotDimension), redDotDimension, (0,0,255), -1)
  return [hyperparametersListNames, frameToShow, WINDOW_NAME, organizationTab]


def _getHeadEmbededTrackingParamsForHyperParamAdjustsQt(nbTailPoints, i, firstFrame, output, outputHeading, frame, frame2, hyperparameters):
  # hyperparametersListNames = ["headEmbededAutoSet_BackgroundExtractionOption", "overwriteFirstStepValue", "overwriteLastStepValue", "overwriteNbOfStepValues", "headEmbededParamTailDescentPixThreshStopOverwrite", "authorizedRelativeLengthTailEnd"]
  hyperparametersListNames = ["headEmbededAutoSet_BackgroundExtractionOption", "overwriteFirstStepValue", "overwriteLastStepValue", "headEmbededParamTailDescentPixThreshStopOverwrite", "authorizedRelativeLengthTailEnd", "overwriteHeadEmbededParamGaussianBlur"]
  organizationTab = [
  [0, 20, "Transforms non-background pixels to black. Can be useful when the tail isn't very different from the background."],
  [0, 80, "Increase this to avoid having the tracking points go on the head instead of the tail."],
  [1, 80, 'Increase this if the tail tracking is getting off track "mid-tail". Decrease if the tail tracking is going too far (further than the tip).'],
  # [1, 50, "This is set automatically when you change either overwriteFirstStepValue or overwriteLastStepValue. Decrease to make the tracking faster."],
  [0, 255, "Decrease if the tail tracking is going too far (further than the tip of the tail). Increase if the tail if not going far enough (stops before the tip)."],
  [0, 1, 'Relative length along the "normal lenght" of the tail where the tracking is "allowed" to stop. Decrease if the tail becomes invisible "mid-tail".'],
  [0, 100, 'Try to find the right balance between too much and too little gaussian smoothing of the image.'],]
  WINDOW_NAME = "Tracking"

  # frame2 = np.concatenate((frame2, frame),axis=1)

  frame2 = cv2.cvtColor(frame2,cv2.COLOR_GRAY2RGB)
  for k in range(0, hyperparameters["nbAnimalsPerWell"]):
    for j in range(0, nbTailPoints):
      x = int(output[k, i-firstFrame][j][0])
      y = int(output[k, i-firstFrame][j][1])
      cv2.circle(frame2, (x, y), 1, (0, 255, 0),   -1)
    x = int(output[k, i-firstFrame][nbTailPoints-1][0])
    y = int(output[k, i-firstFrame][nbTailPoints-1][1])
    cv2.circle(frame2, (x, y), 2, (0, 0, 255),   -1)
    x = output[k, i-firstFrame][0][0]
    y = output[k, i-firstFrame][0][1]

  return [hyperparametersListNames, frame2, WINDOW_NAME, organizationTab]


def getHeadEmbededTrackingParamsForHyperParamAdjusts(nbTailPoints, i, firstFrame, output, outputHeading, frame, frame2, hyperparameters):
  if QApplication.instance() is not None:
    return _getHeadEmbededTrackingParamsForHyperParamAdjustsQt(nbTailPoints, i, firstFrame, output, outputHeading, frame, frame2, hyperparameters)
  
  # hyperparametersListNames = ["headEmbededAutoSet_BackgroundExtractionOption", "overwriteFirstStepValue", "overwriteLastStepValue", "overwriteNbOfStepValues", "headEmbededParamTailDescentPixThreshStopOverwrite", "authorizedRelativeLengthTailEnd"]
  hyperparametersListNames = ["headEmbededAutoSet_BackgroundExtractionOption", "overwriteFirstStepValue", "overwriteLastStepValue", "headEmbededParamTailDescentPixThreshStopOverwrite", "authorizedRelativeLengthTailEnd", "overwriteHeadEmbededParamGaussianBlur"]
  marginX = 30
  organizationTab = [\
  [470,   marginX + 5, 350,  0,  20, "Transforms non-background pixels to black. Can be useful when the tail isn't very different from the background."],
  [1,    marginX + 71, 350,  0,  80, "Increase this to avoid having the tracking points go on the head instead of the tail."],
  [470,  marginX + 71, 350,  1,  80, 'Increase this if the tail tracking is getting off track "mid-tail". Decrease if the tail tracking is going too far (further than the tip).'],
  # [1,   marginX + 137, 350,  1,  50, "This is set automatically when you change either overwriteFirstStepValue or overwriteLastStepValue. Decrease to make the tracking faster."],
  [1,   marginX + 137, 350,  0, 255, "Decrease if the tail tracking is going too far (further than the tip of the tail). Increase if the tail if not going far enough (stops before the tip)."],
  [470, marginX + 137, 350,  0, 1, 'Relative length along the "normal lenght" of the tail where the tracking is "allowed" to stop. Decrease if the tail becomes invisible "mid-tail".'],
  [1, marginX + 208,  350, 0, 100, 'Try to find the right balance between too much and too little gaussian smoothing of the image.'],
  [470, marginX + 208,  -1, -1,  -1, "Click here if you're done adjusting these parameters."]]
  WINDOW_NAME = "Tracking"
  
  # frame2 = np.concatenate((frame2, frame),axis=1)
  
  frame2 = cv2.cvtColor(frame2,cv2.COLOR_GRAY2RGB)
  for k in range(0, hyperparameters["nbAnimalsPerWell"]):
    for j in range(0, nbTailPoints):
      x = int(output[k, i-firstFrame][j][0])
      y = int(output[k, i-firstFrame][j][1])
      cv2.circle(frame2, (x, y), 1, (0, 255, 0),   -1)
    x = int(output[k, i-firstFrame][nbTailPoints-1][0])
    y = int(output[k, i-firstFrame][nbTailPoints-1][1])
    cv2.circle(frame2, (x, y), 2, (0, 0, 255),   -1)
    x = output[k, i-firstFrame][0][0]
    y = output[k, i-firstFrame][0][1]
  
  return [hyperparametersListNames, frame2, WINDOW_NAME, organizationTab]


def _getFreelySwimTrackingParamsForHyperParamAdjustsQt(nbTailPoints, i, firstFrame, output, outputHeading, frame, frame2, hyperparameters):
  if hyperparameters["trackTail"] == 1:
    hyperparametersListNames = ["minPixelDiffForBackExtract", "maxAreaBody", "minTailSize", "maxTailSize"]
    organizationTab = [
    [0, 20, "Increase this if some of the background is not completely white. Decrease if you can't see all of the fish. "],
    [0, 20, "Try increasing this if no tracking is showing."],
    [0, 20, "Try increasing this if no tracking is showing."],
    [0, 20, "Try decreasing this if no tracking is showing."],]
  else:
    hyperparametersListNames = ["minPixelDiffForBackExtract"]
    # The gaussian image filter should be added below, and maybe also the trajectories post-processing option
    organizationTab = [
    [0, 20, "Increase this if some of the background is not completely white. Decrease if you can't see all of the fish. "],]

  WINDOW_NAME = "Tracking"

  frame2 = cv2.cvtColor(frame2,cv2.COLOR_GRAY2RGB)
  for k in range(0, hyperparameters["nbAnimalsPerWell"]):
    if hyperparameters["trackTail"] == 1:
      for j in range(0, nbTailPoints):
        x = int(output[k, i-firstFrame][j][0])
        y = int(output[k, i-firstFrame][j][1])
        cv2.circle(frame2, (x, y), 1, (0, 255, 0),   -1)
    x = int(output[k, i-firstFrame][nbTailPoints-1][0])
    y = int(output[k, i-firstFrame][nbTailPoints-1][1])
    cv2.circle(frame2, (x, y), 2, (0, 0, 255),   -1)
    x = output[k, i-firstFrame][0][0]
    y = output[k, i-firstFrame][0][1]

  return [hyperparametersListNames, frame2, WINDOW_NAME, organizationTab]


def getFreelySwimTrackingParamsForHyperParamAdjusts(nbTailPoints, i, firstFrame, output, outputHeading, frame, frame2, hyperparameters):
  if QApplication.instance() is not None:
    return _getFreelySwimTrackingParamsForHyperParamAdjustsQt(nbTailPoints, i, firstFrame, output, outputHeading, frame, frame2, hyperparameters)
  
  if hyperparameters["trackTail"] == 1:
    hyperparametersListNames = ["minPixelDiffForBackExtract", "maxAreaBody", "minTailSize", "maxTailSize"]
    marginX = 30
    organizationTab = [\
    [470,   marginX + 5, 350,  0,  20, "Increase this if some of the background is not completely white. Decrease if you can't see all of the fish. "],
    [1,    marginX + 71, 350,  0,  20, "Try increasing this if no tracking is showing."],
    [470,  marginX + 71, 350,  0,  20, "Try increasing this if no tracking is showing."],
    [1,   marginX + 137, 350,  0,  20, "Try decreasing this if no tracking is showing."],
    [470, marginX + 137, -1,  -1, "Click here if you're done adjusting these parameters."]]
  else:
    hyperparametersListNames = ["minPixelDiffForBackExtract"]
    marginX = 30
    # The gaussian image filter should be added below, and maybe also the trajectories post-processing option
    organizationTab = [\
    [470,  marginX + 5, 350,  0,  20, "Increase this if some of the background is not completely white. Decrease if you can't see all of the fish. "],
    [1,   marginX + 71, -1,  -1, "Click here if you're done adjusting these parameters."]]
  
  WINDOW_NAME = "Tracking"
  
  frame2 = cv2.cvtColor(frame2,cv2.COLOR_GRAY2RGB)
  for k in range(0, hyperparameters["nbAnimalsPerWell"]):
    if hyperparameters["trackTail"] == 1:
      for j in range(0, nbTailPoints):
        x = int(output[k, i-firstFrame][j][0])
        y = int(output[k, i-firstFrame][j][1])
        cv2.circle(frame2, (x, y), 1, (0, 255, 0),   -1)
    x = int(output[k, i-firstFrame][nbTailPoints-1][0])
    y = int(output[k, i-firstFrame][nbTailPoints-1][1])
    cv2.circle(frame2, (x, y), 2, (0, 0, 255),   -1)
    x = output[k, i-firstFrame][0][0]
    y = output[k, i-firstFrame][0][1]
  
  return [hyperparametersListNames, frame2, WINDOW_NAME, organizationTab]


def _getFreelySwimTrackingAutoParamsForHyperParamAdjustsQt(nbTailPoints, i, firstFrame, output, outputHeading, frame, frame2, hyperparameters):
  hyperparametersListNames = ["recalculateForegroundImageBasedOnBodyArea", "adjustMinPixelDiffForBackExtract_nbBlackPixelsMax", "minPixelDiffForBackExtract"]
  organizationTab = [
  [0, 1, "Set to 1 for Method 3 and to 0 for Method 1 or 2"],
  [0, 20, "Set to 0 for Method 1. For method 2 and 3: increase if the tip of tail is detected to soon, decrease if the tracking looks messy."],
  [0, 20, "For method 1: decrease if the tip of tail is detected to soon, increase if the tracking looks messy"],]

  WINDOW_NAME = "Tracking"

  frame2 = cv2.cvtColor(frame2,cv2.COLOR_GRAY2RGB)
  for k in range(0, hyperparameters["nbAnimalsPerWell"]):
    if hyperparameters["trackTail"] == 1:
      for j in range(0, nbTailPoints):
        x = int(output[k, i-firstFrame][j][0])
        y = int(output[k, i-firstFrame][j][1])
        cv2.circle(frame2, (x, y), 1, (0, 255, 0),   -1)
    x = int(output[k, i-firstFrame][nbTailPoints-1][0])
    y = int(output[k, i-firstFrame][nbTailPoints-1][1])
    cv2.circle(frame2, (x, y), 2, (0, 0, 255),   -1)
    x = output[k, i-firstFrame][0][0]
    y = output[k, i-firstFrame][0][1]

  return [hyperparametersListNames, frame2, WINDOW_NAME, organizationTab]


def getFreelySwimTrackingAutoParamsForHyperParamAdjusts(nbTailPoints, i, firstFrame, output, outputHeading, frame, frame2, hyperparameters):
  if QApplication.instance() is not None:
    return _getFreelySwimTrackingAutoParamsForHyperParamAdjustsQt(nbTailPoints, i, firstFrame, output, outputHeading, frame, frame2, hyperparameters)
  
  hyperparametersListNames = ["recalculateForegroundImageBasedOnBodyArea", "adjustMinPixelDiffForBackExtract_nbBlackPixelsMax", "minPixelDiffForBackExtract"]
  marginX = 30
  organizationTab = [\
  [470,   marginX + 5, 350,  0,  20, "Set to 1 for Method 3 and to 0 for Method 1 or 2"],
  [1,    marginX + 71, 350,  0,  20, "Set to 0 for Method 1. For method 2 and 3: increase if the tip of tail is detected to soon, decrease if the tracking looks messy."],
  [470,  marginX + 71, 350,  0,  20, "For method 1: decrease if the tip of tail is detected to soon, increase if the tracking looks messy"],
  [1,   marginX + 137, -1,  -1, "Click here if you're done adjusting these parameters."]]
  
  WINDOW_NAME = "Tracking"
  
  frame2 = cv2.cvtColor(frame2,cv2.COLOR_GRAY2RGB)
  for k in range(0, hyperparameters["nbAnimalsPerWell"]):
    if hyperparameters["trackTail"] == 1:
      for j in range(0, nbTailPoints):
        x = int(output[k, i-firstFrame][j][0])
        y = int(output[k, i-firstFrame][j][1])
        cv2.circle(frame2, (x, y), 1, (0, 255, 0),   -1)
    x = int(output[k, i-firstFrame][nbTailPoints-1][0])
    y = int(output[k, i-firstFrame][nbTailPoints-1][1])
    cv2.circle(frame2, (x, y), 2, (0, 0, 255),   -1)
    x = output[k, i-firstFrame][0][0]
    y = output[k, i-firstFrame][0][1]
  
  return [hyperparametersListNames, frame2, WINDOW_NAME, organizationTab]
