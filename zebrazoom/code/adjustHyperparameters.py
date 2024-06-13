import cv2
import numpy as np
import os
import pickle
import webbrowser


MAX_INT32 = 2 ** 31 - 1


def __calculateSteps(maxDepth, numberOfSteps):
  steps = [maxDepth / 1.8, maxDepth / 2.4, maxDepth / 3.6]
  if numberOfSteps <= 3:
    return reversed(steps[:numberOfSteps])
  if numberOfSteps > 3:
    steps.extend((maxDepth / (3.6 + 0.2 * (numberOfSteps - i)) for i in reversed(range(numberOfSteps - 3))))
  return reversed(steps)


def __createComboBox(layout, status, values, info, names, widgets, nameIdx):
  from PyQt5.QtWidgets import QComboBox, QGridLayout, QWidget

  name, choices, callback, getCurrentIndex = info
  combobox = QComboBox()
  combobox.setContentsMargins(20, 5, 20, 5)
  combobox.addItems(choices)
  combobox.setCurrentIndex(getCurrentIndex(values))
  listView = combobox.view()
  listView.setWordWrap(True)
  listView.adjustSize()
  combobox.currentIndexChanged.connect(lambda idx: callback(idx, values))
  combobox.currentIndexChanged.connect(lambda idx: widgets['loop'].exit())

  layout = QGridLayout()  # this is required to align combobox with sliders
  layout.setColumnStretch(0, 1)
  layout.setRowStretch(0, 1)
  layout.setColumnStretch(2, 1)
  layout.setVerticalSpacing(0)
  layout.setContentsMargins(20, 5, 20, 5)
  layout.addWidget(combobox, 1, 1)
  wrapperWidget = QWidget()
  wrapperWidget.setLayout(layout)

  return name, wrapperWidget


def __createSlider(layout, status, values, info, names, widgets, hasCheckbox, nameIdx, widgetPosition=None):
  from PyQt5.QtCore import QAbstractListModel

  import zebrazoom.code.util as util

  stepIdx = None
  if isinstance(names, QAbstractListModel):
    stepsIdx = names.itemlist.index('steps')
    stepCount = len(values['steps'])
    names.updateSteps(stepCount)
    if stepsIdx < nameIdx <= stepsIdx + stepCount:
      stepIdx = nameIdx - (stepsIdx + 1)
      nameIdx = stepsIdx
      name = f'Step {stepIdx + 1}'
    else:
      name = names.itemlist[nameIdx]
      if nameIdx > stepsIdx:
        nameIdx -= stepCount
    minn, maxx, hint = info[nameIdx]
  else:
    name = names
    minn, maxx, hint = info
  if name not in values:
    assert name.startswith('Step')
    value = values['steps'][stepIdx]
    minn = 0.01
    maxx = max(values['maxDepth'], value * 1.33)
  else:
    value = values[name] if name != 'steps' else len(values[name])
    if value < minn:
      minn = int(value)
    if value > maxx:
      maxx = int(value * 1.33)
  double = name in ("authorizedRelativeLengthTailEnd", "authorizedRelativeLengthTailEnd2", "maxDepth", "thetaDiffAccept", "thetaDiffAcceptAfterAuthorizedRelativeLengthTailEnd", "thetaDiffAcceptAfterAuthorizedRelativeLengthTailEnd2") or name not in values
  if isinstance(names, QAbstractListModel):
    slider = util.SliderWithSpinbox(value, minn, maxx, name=name, double=double, choices=names)

    def choiceChanged(idx):
      if not slider.isVisible():
        return
      choiceIdx = idx // 2
      if names.itemlist[choiceIdx] in widgets:
        widget = widgets[names.itemlist[choiceIdx]]
        blocked = widget.blockSignals(True)
        widget.setChoice(idx)
        widget.blockSignals(blocked)
        layout.replaceWidget(slider, widget)
        slider.hide()
        widget.show()
      else:
        layout.removeWidget(slider)
        slider.hide()
        _createWidget(layout, status, values, info, names, widgets, hasCheckbox, nameIdx=choiceIdx, widgetPosition=widgetPosition)
    slider.choiceChanged.connect(choiceChanged)
  else:
    slider = util.SliderWithSpinbox(value, minn, maxx, name=name, double=double)
  if name == "eyeFilterKernelSize" or name == "paramGaussianBlur":
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
    if name == 'paramGaussianBlur' and not slider.value() % 2:
      slider.setValue(slider.value() + 1)
      return
    if name == 'paramGaussianBlurForHeadPosition' and slider.value() and not slider.value() % 2:
      slider.setValue(slider.value() + 1)
      return
    if name not in values:
      assert name.startswith('Step ')
      values['steps'][stepIdx] = slider.value()
    elif name == 'steps':
      newSteps = slider.value()
      currentSteps = len(values[name])
      difference = newSteps - currentSteps
      if difference > 0:
        newValues = []
        for idx in range(difference):
          stepName = f'Step {idx + 1}'
          defaultSteps = list(__calculateSteps(values['maxDepth'], newSteps))
          newValues.append(defaultSteps[idx])
        values[name][:0] = newValues
      elif difference < 0:
        del values[name][:-difference]
      names.updateSteps(len(values[name]))
    else:
      values[name] = slider.value()
    if name == 'headEmbededParamTailDescentPixThreshStop':
      values['maximumMedianValueOfAllPointsAlongTheTail'] = slider.value()
      values['minimumHeadPixelValue'] = slider.value()
    widgets['loop'].exit()
  slider.valueChanged.connect(valueChanged)
  return name, slider

def _createWidget(layout, status, values, info, names, widgets, hasCheckbox, nameIdx=0, widgetPosition=None):
  from PyQt5.QtCore import Qt

  if isinstance(names, tuple):
    name, widget = __createComboBox(layout, status, values, info, names, widgets, nameIdx)
  else:
    name, widget = __createSlider(layout, status, values, info, names, widgets, hasCheckbox, nameIdx, widgetPosition=layout.count()if widgetPosition is None else widgetPosition)

  if name != "Frame number":
    elements = (widgetPosition if widgetPosition is not None else layout.count()) - (4 if hasCheckbox else 3)  # frame, status, checkbox, frameSlider
    row = elements // 2 + (4 if hasCheckbox else 3)
    col = elements % 2
    if len(values) == 1:
      layout.addWidget(widget, row, col, 1, 2, Qt.AlignmentFlag.AlignCenter)
    else:
      layout.addWidget(widget, row, col, Qt.AlignmentFlag.AlignLeft if col else Qt.AlignmentFlag.AlignRight)
    widgets[name] = widget
  else:
    widgets['frameSlider'] = widget
    layout.addWidget(widget, 3 if hasCheckbox else 2, 0, 1, 2, Qt.AlignmentFlag.AlignCenter)


def adjustHyperparameters(l, hyperparameters, hyperparametersListNames, frameToShow, title, organizationTab, widgets, documentationLink=None, addContrastCheckbox=False, addZoomCheckbox=False, addUnprocessedFrameCheckbox=False):
  from PyQt5.QtCore import Qt, QAbstractListModel, QEventLoop, QTimer
  from PyQt5.QtGui import QCursor
  from PyQt5.QtWidgets import QApplication, QCheckBox, QGridLayout, QHBoxLayout, QLabel, QPushButton, QSpinBox, QVBoxLayout, QWidget

  import zebrazoom.code.paths as paths
  import zebrazoom.code.util as util

  app = QApplication.instance()
  stackedLayout = app.window.centralWidget().layout()
  timers = []

  hasCheckbox = addContrastCheckbox or addZoomCheckbox or addUnprocessedFrameCheckbox

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

    if hasCheckbox:
      checkboxesLayout = QHBoxLayout()
      checkboxesLayout.addStretch(1)
      if addContrastCheckbox:
        checkbox = QCheckBox('Improve contrast')
        widgets['contrastCheckbox'] = checkbox
        checkbox.toggled.connect(lambda: widgets['loop'].exit())
        QTimer.singleShot(0, lambda: checkbox.setChecked(hyperparameters["outputValidationVideoContrastImprovement"]))
        checkboxesLayout.addWidget(checkbox, alignment=Qt.AlignmentFlag.AlignCenter)
      if addUnprocessedFrameCheckbox:
        checkbox = QCheckBox('Show unprocessed frame')
        widgets['unprocessedFrameCheckbox'] = checkbox
        checkbox.toggled.connect(lambda: widgets['loop'].exit())
        checkboxesLayout.addWidget(checkbox, alignment=Qt.AlignmentFlag.AlignCenter)
      if addZoomCheckbox:
        numberOfAnimals = hyperparameters.get('nbAnimalsPerWell', 1)
        checkbox = QCheckBox('Zoom in to animal')
        checkbox.getAnimalIdx = lambda: animalSpinbox.value() if numberOfAnimals > 1 else 0
        widgets['zoomInCheckbox'] = checkbox
        checkbox.toggled.connect(lambda: widgets['loop'].exit())
        checkboxesLayout.addWidget(checkbox, alignment=Qt.AlignmentFlag.AlignCenter)
        if numberOfAnimals > 1:
          animalSpinbox = QSpinBox()
          animalSpinbox.setRange(0, numberOfAnimals - 1)
          animalSpinbox.valueChanged.connect(lambda: widgets['loop'].exit())
          checkboxesLayout.addWidget(animalSpinbox, alignment=Qt.AlignmentFlag.AlignLeft)
      checkboxesLayout.addStretch(1)
      layout.addLayout(checkboxesLayout, 2, 0, 1, 2, Qt.AlignmentFlag.AlignCenter)

    if l is not None:
      _createWidget(layout, status, widgets, (hyperparameters["firstFrame"], hyperparameters["lastFrame"] - 1, "You can also go through the video with the keys left arrow (backward); right arrow (forward); page down (fast backward); page up (fast forward)"), "Frame number", widgets, hasCheckbox)
    else:
      layout.addWidget(QWidget())
    for info, name in zip(organizationTab, hyperparametersListNames):
      _createWidget(layout, status, hyperparameters, info, name, widgets, hasCheckbox)

    mainLayout = QVBoxLayout()
    titleLabel = util.apply_style(QLabel(title), font=util.TITLE_FONT)
    titleLabel.setMinimumSize(1, 1)
    titleLabel.resizeEvent = lambda evt: titleLabel.setMinimumWidth(evt.size().width()) or titleLabel.setWordWrap(evt.size().width() <= titleLabel.sizeHint().width())
    mainLayout.addWidget(titleLabel, alignment=Qt.AlignmentFlag.AlignCenter)
    mainLayout.addLayout(layout)
    buttonsLayout = QHBoxLayout()
    buttonsLayout.addStretch()
    if documentationLink is not None:
      documentationBtn = util.apply_style(QPushButton("Help"), background_color="red")
      documentationBtn.clicked.connect(lambda: webbrowser.open_new(documentationLink))
      buttonsLayout.addWidget(documentationBtn, alignment=Qt.AlignmentFlag.AlignCenter)

    def saveClicked():
      widgets['saved'] = True
      widgets['loop'].exit()
    def discardClicked():
      widgets['discarded'] = True
      widgets['loop'].exit()
    for text, cb, color in (("Discard changes.", discardClicked, None), ("Done! Save changes!", saveClicked, util.DEFAULT_BUTTON_COLOR)):
      button = QPushButton(text) if color is None else util.apply_style(QPushButton(text), background_color=color)
      button.clicked.connect(cb)
      buttonsLayout.addWidget(button, alignment=Qt.AlignmentFlag.AlignCenter)
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
    flattenedList = []
    for name in hyperparametersListNames:
      if isinstance(name, QAbstractListModel):
        flattenedList.extend((n for n in name.itemlist if n in hyperparameters))
      else:
        flattenedList.append(name)
    if 'steps' in hyperparameters:
      for idx in range(len(hyperparameters['steps'])):
        name = f'Step {idx + 1}'
        if name not in widgets:
          continue
        slider = widgets[name]
        value = hyperparameters['steps'][idx]
        if slider.value() != value:
          slider.setValue(value)
        minn = slider.minimum()
        maxx = slider.maximum()
        if (value - minn) > (maxx - minn) * 0.9:
          maxx = int(minn + (value - minn) * 1.1)
        elif maxx - minn > 255 and value < minn + (maxx - minn) * 0.1:
          maxx = int(minn + (maxx - minn) * 0.9)
        else:
          continue
        maxx = min(maxx, MAX_INT32)
        slider.setMaximum(maxx)
    for name in flattenedList:
      if name not in widgets:
        continue
      slider = widgets[name]
      value = len(hyperparameters[name]) if name == 'steps' else hyperparameters[name]
      if slider.value() != value:
        slider.setValue(value)
      if name.startswith("authorizedRelativeLengthTailEnd") or name.startswith("thetaDiffAccept") or name == "eyeBinaryThreshold":
        continue
      minn = slider.minimum()
      maxx = slider.maximum()
      if name == "frameGapComparision" and maxx == hyperparameters["lastFrame"] - hyperparameters["firstFrame"] - 1:
        continue
      if (value - minn) > (maxx - minn) * 0.9:
        maxx = int(minn + (value - minn) * 1.1)
      elif maxx - minn > 255 and value < minn + (maxx - minn) * 0.1:
        maxx = int(minn + (maxx - minn) * 0.9)
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
        newPosition = int(min(localCursorX / slider.sliderWidth(), 1) * maxx)
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
    newParams = {}
    for name in hyperparametersListNames:
      if isinstance(name, QAbstractListModel):
        for name in name.itemlist:
          if name in hyperparameters:
            newParams[name] = hyperparameters[name]
      elif isinstance(name, tuple):
        for n in name:
          if hyperparameters.get(n, False):
            newParams[n] = hyperparameters[n]
      else:
        newParams[name] = hyperparameters[name]
    pickle.dump(newParams, open(os.path.join(paths.getRootDataFolder(), 'newhyperparameters'), 'wb'))
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
