import cv2
import numpy as np
import os
import pickle
import webbrowser


MAX_INT32 = 2 ** 31 - 1


def _createWidget(layout, status, values, info, name, widgets, hasCheckbox):
  from PyQt5.QtCore import Qt

  import zebrazoom.code.util as util

  minn, maxx, hint = info
  double = name == "authorizedRelativeLengthTailEnd"
  slider = util.SliderWithSpinbox(values[name], minn, maxx, name=name, double=double)
  if name == "eyeFilterKernelSize":
    slider.setSingleStep(2)

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
    widgets['loop'].exit()
  slider.valueChanged.connect(valueChanged)

  if name != "Frame number":
    elements = layout.count() - (4 if hasCheckbox else 3)  # frame, status, checkbox, frameSlider
    row = elements // 2 + (4 if hasCheckbox else 3)
    col = elements % 2
    if len(values) == 1:
      layout.addWidget(slider, row, col, 1, 2, Qt.AlignmentFlag.AlignCenter)
    else:
      layout.addWidget(slider, row, col, Qt.AlignmentFlag.AlignLeft if col else Qt.AlignmentFlag.AlignRight)
    widgets[name] = slider
  else:
    widgets['frameSlider'] = slider
    layout.addWidget(slider, 3 if hasCheckbox else 2, 0, 1, 2, Qt.AlignmentFlag.AlignCenter)


def adjustHyperparameters(l, hyperparameters, hyperparametersListNames, frameToShow, title, organizationTab, widgets, documentationLink=None, addContrastCheckbox=False):
  from PyQt5.QtCore import Qt, QEventLoop, QTimer
  from PyQt5.QtGui import QCursor
  from PyQt5.QtWidgets import QApplication, QCheckBox, QGridLayout, QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

  import zebrazoom.code.paths as paths
  import zebrazoom.code.util as util

  app = QApplication.instance()
  stackedLayout = app.window.centralWidget().layout()
  timers = []

  if widgets is None:
    widgets = {'Frame number': l, 'saved': False, 'discarded': False, 'loop': QEventLoop()}
    layout = QGridLayout()
    layout.setVerticalSpacing(0)
    frame = QLabel()
    widgets['frame'] = frame
    layout.addWidget(frame, 0, 0, 1, 2, Qt.AlignmentFlag.AlignCenter)
    layout.setRowStretch(0, 1)
    status = QLabel()
    layout.addWidget(status, 1, 0, 1, 2, Qt.AlignmentFlag.AlignCenter)

    if addContrastCheckbox:
      checkbox = QCheckBox('Improve contrast')
      widgets['contrastCheckbox'] = checkbox
      checkbox.toggled.connect(lambda: widgets['loop'].exit())
      QTimer.singleShot(0, lambda: checkbox.setChecked(hyperparameters["outputValidationVideoContrastImprovement"]))
      layout.addWidget(checkbox, 2, 0, 1, 2, Qt.AlignmentFlag.AlignCenter)

    if l is not None:
      _createWidget(layout, status, widgets, (hyperparameters["firstFrame"], hyperparameters["lastFrame"] - 1, "You can also go through the video with the keys left arrow (backward); right arrow (forward); page down (fast backward); page up (fast forward)"), "Frame number", widgets, addContrastCheckbox)
    else:
      layout.addWidget(QWidget())
    for info, name in zip(organizationTab, hyperparametersListNames):
      _createWidget(layout, status, hyperparameters, info, name, widgets, addContrastCheckbox)

    mainLayout = QVBoxLayout()
    titleLabel = util.apply_style(QLabel(title), font=util.TITLE_FONT)
    titleLabel.setMinimumSize(1, 1)
    titleLabel.resizeEvent = lambda evt: titleLabel.setMinimumWidth(evt.size().width()) or titleLabel.setWordWrap(evt.size().width() <= titleLabel.sizeHint().width())
    mainLayout.addWidget(titleLabel, alignment=Qt.AlignmentFlag.AlignCenter)
    mainLayout.addLayout(layout)
    buttonsLayout = QHBoxLayout()
    buttonsLayout.addStretch()

    def saveClicked():
      widgets['saved'] = True
      widgets['loop'].exit()
    def discardClicked():
      widgets['discarded'] = True
      widgets['loop'].exit()
    for text, cb in (("Done! Save changes!", saveClicked), ("Discard changes.", discardClicked)):
      button = QPushButton(text)
      button.clicked.connect(cb)
      buttonsLayout.addWidget(button, alignment=Qt.AlignmentFlag.AlignCenter)
    if documentationLink is not None:
      documentationBtn = util.apply_style(QPushButton("Help"), background_color="red")
      documentationBtn.clicked.connect(lambda: webbrowser.open_new(documentationLink))
      buttonsLayout.addWidget(documentationBtn, alignment=Qt.AlignmentFlag.AlignCenter)
    buttonsLayout.addStretch()
    mainLayout.addLayout(buttonsLayout)
    temporaryPage = QWidget()
    temporaryPage.setLayout(mainLayout)
    stackedLayout.addWidget(temporaryPage)
    widgets['oldWidget'] = stackedLayout.currentWidget()
    stackedLayout.setCurrentWidget(temporaryPage)
    frame.setMinimumSize(1, 1)
    frame.show()
    util.setPixmapFromCv(frameToShow, frame)
  else:
    for name in hyperparametersListNames:
      slider = widgets[name]
      if slider.value() != hyperparameters[name]:
        slider.setValue(hyperparameters[name])
      if name == "authorizedRelativeLengthTailEnd" or name == "eyeBinaryThreshold":
        continue
      minn = slider.minimum()
      maxx = slider.maximum()
      if name == "frameGapComparision" and maxx == hyperparameters["lastFrame"] - hyperparameters["firstFrame"] - 1:
        continue
      if (hyperparameters[name] - minn) > (maxx - minn) * 0.9:
        maxx = minn + (hyperparameters[name] - minn) * 1.1
      elif maxx - minn > 255 and hyperparameters[name] < minn + (maxx - minn) * 0.1:
        maxx = minn + (maxx - minn) * 0.9
      else:
        continue
      if name == "frameGapComparision":
        maxx = min(maxx, hyperparameters["lastFrame"] - hyperparameters["firstFrame"] - 1)
      else:
        maxx = min(maxx, MAX_INT32)
      slider.setMaximum(maxx)
      localCursorX = slider.mapFromGlobal(QCursor.pos()).x()
      sliderLowerX = slider.sliderWidth() // 10
      sliderUpperX = slider.sliderWidth() - sliderLowerX
      if slider.isSliderDown() and (localCursorX <= sliderLowerX or localCursorX >= sliderUpperX):
        timer = QTimer()
        timers.append(timer)
        timer.setSingleShot(True)
        newPosition = min(localCursorX / slider.sliderWidth(), 1) * maxx
        timer.timeout.connect(lambda slider=slider: (slider.setPosition(newPosition) if newPosition > 0 else widgets['loop'].exit()) or timers.remove(timer))
        timer.start(30)
    if 'frameSlider' in widgets:
      widgets['frameSlider'].setValue(l)
    widgets['frame'].clear()
    widgets['Frame number'] = l
    util.setPixmapFromCv(frameToShow, widgets['frame'])

  with app.suppressBusyCursor():
    widgets['loop'].exec()
  for timer in timers:
    timer.stop()

  if widgets['saved']:
    pickle.dump({name: hyperparameters[name] for name in hyperparametersListNames}, open(os.path.join(paths.getRootDataFolder(), 'newhyperparameters'), 'wb'))
    temporaryPage = stackedLayout.currentWidget()
    stackedLayout.setCurrentWidget(widgets['oldWidget'])
    stackedLayout.removeWidget(temporaryPage)
    raise ValueError
  if widgets['discarded']:
    temporaryPage = stackedLayout.currentWidget()
    stackedLayout.setCurrentWidget(widgets['oldWidget'])
    stackedLayout.removeWidget(temporaryPage)
    raise NameError

  return widgets['Frame number'], widgets


def adjustDetectMouvRawVideosParams(img, res, l, totDiff, hyperparameters, widgets):
  documentationLink = "https://zebrazoom.org/documentation/docs/configurationFile/throughGUI/boutsDetection"
  hyperparametersListNames = ["frameGapComparision", "thresForDetectMovementWithRawVideo", "halfDiameterRoiBoutDetect", "minNbPixelForDetectMovementWithRawVideo"]
  organizationTab = [
  [0, 15,  "Increase if small movements are not detected. An increase that's too big could lead to a detection of bout that's too early however."],
  [0, 255, "Increase if too much movement is being detected."],
  [0, 500, "Controls the size of the images on which pixel change from image to the next are counted."],
  [0, 50,  "Increase if too much movement is being detected."],]
  title = "Red dot must appear only when movement is occuring"
  if widgets is not None and "contrastCheckbox" in widgets and widgets["contrastCheckbox"].isChecked():
    import zebrazoom.code.util as util
    img = util.improveContrast(img, hyperparameters["outputValidationVideoContrastImprovementQuartile"])
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
  return adjustHyperparameters(l, hyperparameters, hyperparametersListNames, frameToShow, title, organizationTab, widgets, documentationLink=documentationLink, addContrastCheckbox=hyperparameters['headEmbeded'])


def adjustHeadEmbededTrackingParams(nbTailPoints, i, firstFrame, output, outputHeading, frame, frame2, hyperparameters, widgets):
  documentationLink = "https://zebrazoom.org/documentation/docs/configurationFile/throughGUI/headEmbeddedSwimming"
  # hyperparametersListNames = ["headEmbededAutoSet_BackgroundExtractionOption", "overwriteFirstStepValue", "overwriteLastStepValue", "overwriteNbOfStepValues", "headEmbededParamTailDescentPixThreshStopOverwrite", "authorizedRelativeLengthTailEnd"]
  hyperparametersListNames = ["headEmbededAutoSet_BackgroundExtractionOption", "overwriteFirstStepValue", "overwriteLastStepValue", "headEmbededParamTailDescentPixThreshStopOverwrite", "authorizedRelativeLengthTailEnd", "overwriteHeadEmbededParamGaussianBlur"]
  organizationTab = [
  [0, 20, "Transforms non-background pixels to black. Can be useful when the tail isn't very different from the background."],
  [0, 80, "Increase this to avoid having the tracking points go on the head instead of the tail."],
  [1, 80, 'Increase this if the tail tracking is getting off track "mid-tail". Decrease if the tail tracking is going too far (further than the tip).'],
  # [1, 50, "This is set automatically when you change either overwriteFirstStepValue or overwriteLastStepValue. Decrease to make the tracking faster."],
  [0, 255, "ALMOST ALWAYS IGNORE THIS PARAMETER. Decrease if the tail tracking is going too far (further than the tip of the tail). Increase if the tail if not going far enough (stops before the tip)."],
  [0, 1, 'ALMOST ALWAYS IGNORE THIS PARAMETER. Relative length along the "normal lenght" of the tail where the tracking is "allowed" to stop. Decrease if the tail becomes invisible "mid-tail".'],
  [0, 100, 'THIS PARAMETER CAN USUALLY BE IGNORED. Try to find the right balance between too much and too little gaussian smoothing of the image.'],]
  title = "Tracking"

  # frame2 = np.concatenate((frame2, frame),axis=1)

  if widgets is not None and widgets["contrastCheckbox"].isChecked():
    import zebrazoom.code.util as util
    frame2 = util.improveContrast(frame2, hyperparameters["outputValidationVideoContrastImprovementQuartile"])

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

  return adjustHyperparameters(i, hyperparameters, hyperparametersListNames, frame2, title, organizationTab, widgets, documentationLink=documentationLink, addContrastCheckbox=True)


def adjustFreelySwimTrackingParams(nbTailPoints, i, firstFrame, output, outputHeading, frame, frame2, hyperparameters, widgets):
  if hyperparameters["trackTail"] == 1:
    hyperparametersListNames = ["minPixelDiffForBackExtract", "maxAreaBody", "minTailSize", "maxTailSize"]
    organizationTab = [
    [0, 20, "Increase this if some of the background is not completely white. Decrease if you can't see all of the animals. "],
    [0, 20, "Try increasing this if no tracking is showing."],
    [0, 20, "Try increasing this if no tracking is showing."],
    [0, 20, "Try decreasing this if no tracking is showing."],]
  else:
    hyperparametersListNames = ["minPixelDiffForBackExtract"]
    # The gaussian image filter should be added below, and maybe also the trajectories post-processing option
    organizationTab = [
    [0, 20, "Increase this if some of the background is not completely white. Decrease if you can't see all of the animals. "],]

  title = "Adjust parameters in order for the background to be white and the animals to be gray/black."

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

  return adjustHyperparameters(i, hyperparameters, hyperparametersListNames, frame2, title, organizationTab, widgets)


def adjustFreelySwimTrackingAutoParams(nbTailPoints, i, firstFrame, output, outputHeading, frame, frame2, hyperparameters, widgets):
  documentationLink = "https://zebrazoom.org/documentation/docs/configurationFile/throughGUI/trackingFreelySwimming"
  hyperparametersListNames = ["recalculateForegroundImageBasedOnBodyArea", "adjustMinPixelDiffForBackExtract_nbBlackPixelsMax", "minPixelDiffForBackExtract"]
  organizationTab = [
  [0, 1, "Set to 1 for Method 3 and to 0 for Method 1 or 2"],
  [0, 20, "Set to 0 for Method 1. For method 2 and 3: increase if the tip of tail is detected to soon, decrease if the tracking looks messy."],
  [0, 20, "For method 1: decrease if the tip of tail is detected to soon, increase if the tracking looks messy"],]

  title = "Adjust parameters in order for the background to be white and the animals to be gray/black."

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

  return adjustHyperparameters(i, hyperparameters, hyperparametersListNames, frame2, title, organizationTab, widgets, documentationLink=documentationLink)


def adjustHeadEmbeddedEyeTrackingParamsSegment(i, frame, hyperparameters, widgets):
  documentationLink = None
  hyperparametersListNames = ["eyeTrackingHeadEmbeddedHalfDiameter", "eyeTrackingHeadEmbeddedWidth"]
  organizationTab = [
  [1, 255, ""],
  [1, 255, ""],]
  title = "Eye Tracking"

  return adjustHyperparameters(i, hyperparameters, hyperparametersListNames, frame, title, organizationTab, widgets, documentationLink=documentationLink)


def adjustHeadEmbeddedEyeTrackingParamsEllipse(i, frame, hyperparameters, widgets):
  documentationLink = None
  hyperparametersListNames = ["eyeBinaryThreshold", "eyeFilterKernelSize", "eyeTrackingHeadEmbeddedHalfDiameter"]
  organizationTab = [
  [0, 255, ""],
  [1, 255, ""],
  [1, 255, ""],]
  title = "Eye Tracking"

  return adjustHyperparameters(i, hyperparameters, hyperparametersListNames, frame, title, organizationTab, widgets, documentationLink=documentationLink)
