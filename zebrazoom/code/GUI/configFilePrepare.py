import os
import webbrowser

import cv2

from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QCursor, QFont, QIcon, QDoubleValidator, QIntValidator, QPixmap
from PyQt5.QtWidgets import QApplication, QFrame, QFormLayout, QLabel, QWidget, QGridLayout, QPushButton, QHBoxLayout, QVBoxLayout, QCheckBox, QRadioButton, QLineEdit, QButtonGroup, QSpacerItem
PYQT6 = False

import zebrazoom.videoFormatConversion.zzVideoReading as zzVideoReading
import zebrazoom.code.util as util
from zebrazoom.code.GUI.adjustParameterInsideAlgo import adjustFastFishTrackingPage
from zebrazoom.code.GUI.configFilePrepareFunctions import numberOfAnimals


class StoreValidationVideoWidget(QWidget):
  def __init__(self, showUseConfig=False):
    super().__init__()
    self._configFile = None
    btnGroup = QButtonGroup()
    layout = QVBoxLayout()
    layout.addWidget(util.apply_style(QLabel("The validation video (tracking points superimposed on the original video) should be:"), font_size='16px'), alignment=Qt.AlignmentFlag.AlignCenter)
    self._noValidationVideoRadioButton = QRadioButton("Visualizable from ZebraZoom's GUI\n(Recommended: faster tracking, less space taken on your hard drive)\n(only drawback: requires the original video to stay at the same location on the hard drive)")
    btnGroup.addButton(self._noValidationVideoRadioButton)
    layout.addWidget(self._noValidationVideoRadioButton, alignment=Qt.AlignmentFlag.AlignLeft)
    self._validationVideoRadioButton = QRadioButton("Saved on my hard drive\n(Not recommended: slower tracking, more space taken on your hard drive)")
    btnGroup.addButton(self._validationVideoRadioButton)
    layout.addWidget(self._validationVideoRadioButton, alignment=Qt.AlignmentFlag.AlignLeft)
    if showUseConfig:
      self._useConfigRadioButton = QRadioButton("Use the value from the configuration file")
      btnGroup.addButton(self._useConfigRadioButton)
      layout.addWidget(self._useConfigRadioButton, alignment=Qt.AlignmentFlag.AlignLeft)
      self._useConfigRadioButton.setChecked(True)
    else:
      self._noValidationVideoRadioButton.toggled.connect(self.__toggled)
    self.setLayout(layout)

  def __toggled(self, checked):
    if 'savePathToOriginalVideoForValidationVideo' in self._configFile:
      del self._configFile['savePathToOriginalVideoForValidationVideo']
    if checked:
      self._configFile['createValidationVideo'] = 0
    elif 'createValidationVideo' in self._configFile:
      del self._configFile['createValidationVideo']

  def refresh(self, configFile, videoPath=None):
    self._configFile = configFile
    blocked = self._noValidationVideoRadioButton.blockSignals(True)
    if not configFile.get('savePathToOriginalVideoForValidationVideo', False) and configFile.get('createValidationVideo', True):
      self._validationVideoRadioButton.setChecked(True)
    else:
      self._noValidationVideoRadioButton.setChecked(True)
    self._noValidationVideoRadioButton.blockSignals(blocked)

  def getOption(self):
    return 0 if self._noValidationVideoRadioButton.isChecked() else 1 if self._validationVideoRadioButton.isChecked() else None


class ChooseVideoToCreateConfigFileFor(QWidget):
  def __init__(self, controller):
    super().__init__(controller.window)
    self.controller = controller
    self.preferredSize = (350, 350)

    layout = QVBoxLayout()
    layout.addWidget(util.apply_style(QLabel("Prepare Config File", self), font=controller.title_font), alignment=Qt.AlignmentFlag.AlignCenter)
    reloadCheckbox = QCheckBox("Click here to start from a configuration file previously created (instead of from scratch).", self)
    layout.addWidget(reloadCheckbox, alignment=Qt.AlignmentFlag.AlignCenter)

    sublayout1 = QVBoxLayout()
    selectVideoBtn = util.apply_style(QPushButton("Select the video you want to create a configuration file for.", self), background_color=util.DEFAULT_BUTTON_COLOR)
    selectVideoBtn.clicked.connect(lambda: controller.chooseVideoToCreateConfigFileFor(controller, reloadCheckbox.isChecked()) and util.addToHistory(controller.show_frame)("ChooseGeneralExperiment"))
    sublayout1.addWidget(selectVideoBtn, alignment=Qt.AlignmentFlag.AlignCenter)
    sublayout1.addWidget(QLabel("(you will be able to use the configuration file you create for all videos that are similar to that video)", self), alignment=Qt.AlignmentFlag.AlignCenter)
    layout.addLayout(sublayout1)

    sublayout2 = QVBoxLayout()
    startPageBtn = QPushButton("Go to the start page", self)
    startPageBtn.clicked.connect(lambda: controller.show_frame("StartPage"))
    sublayout2.addWidget(startPageBtn, alignment=Qt.AlignmentFlag.AlignCenter)
    sublayout2.addWidget(QLabel('Warning: This procedure to create configuration files is incomplete.', self), alignment=Qt.AlignmentFlag.AlignCenter)
    sublayout2.addWidget(QLabel('You may not succeed at making a good configuration file to analyze your video.', self), alignment=Qt.AlignmentFlag.AlignCenter)
    sublayout2.addWidget(QLabel("If you don't manage to get a good configuration file that fits your needs, email us at info@zebrazoom.org.", self), alignment=Qt.AlignmentFlag.AlignCenter)
    layout.addLayout(sublayout2)

    self.setLayout(layout)


class _SolveIssuesNearBordersWidget(QWidget):
  def __init__(self):
    super().__init__()
    self._configFile = None
    layout = QVBoxLayout()
    layout.addWidget(util.apply_style(QLabel("Solve issues near the borders of the wells/tanks/arenas"), font_size='16px'), alignment=Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)
    solveIssuesInfoLabel = QLabel("backgroundPreProcessParameters should be an odd positive integer. Higher value filters more pixels on the borders of the wells/tanks/arenas.")
    solveIssuesInfoLabel.setMinimumSize(1, 1)
    solveIssuesInfoLabel.resizeEvent = lambda evt: solveIssuesInfoLabel.setMinimumWidth(evt.size().width()) or solveIssuesInfoLabel.setWordWrap(evt.size().width() <= solveIssuesInfoLabel.sizeHint().width())
    layout.addWidget(solveIssuesInfoLabel, alignment=Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)
    self._backgroundPreProcessParameters = backgroundPreProcessParameters = QLineEdit()
    backgroundPreProcessParameters.setValidator(QIntValidator(backgroundPreProcessParameters))
    backgroundPreProcessParameters.validator().setBottom(0)

    def updateBackgroundPreProcessParameters(text):
      if text:
        self._configFile["backgroundPreProcessMethod"] = ["erodeThenMin"]
        self._configFile["backgroundPreProcessParameters"] = [[int(text)]]
      else:
        if self._originalBackgroundPreProcessMethod is not None:
          self._configFile["backgroundPreProcessMethod"] = self._originalBackgroundPreProcessMethod
        elif "backgroundPreProcessMethod" in self._configFile:
          del self._configFile["backgroundPreProcessMethod"]
        if self._originalBackgroundPreProcessParameters is not None:
          self._configFile["backgroundPreProcessParameters"] = self._originalBackgroundPreProcessParameters
        elif "backgroundPreProcessParameters" in self._configFile:
          del self._configFile["backgroundPreProcessParameters"]
    backgroundPreProcessParameters.textChanged.connect(updateBackgroundPreProcessParameters)
    backgroundPreProcessParametersLayout = QFormLayout()
    backgroundPreProcessParametersLayout.setFormAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)
    backgroundPreProcessParametersLayout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.FieldsStayAtSizeHint)
    backgroundPreProcessParametersLayout.addRow("backgroundPreProcessParameters:", backgroundPreProcessParameters)
    layout.addLayout(backgroundPreProcessParametersLayout)
    self.setLayout(layout)

  def refresh(self, configFile, videoPath=None):
    self._configFile = configFile
    self._originalBackgroundPreProcessParameters = configFile.get("backgroundPreProcessParameters")
    self._originalBackgroundPreProcessMethod = configFile.get("backgroundPreProcessMethod")
    self._backgroundPreProcessParameters.setText('')
    if self._originalBackgroundPreProcessParameters is not None and self._originalBackgroundPreProcessMethod is not None:
      if self._originalBackgroundPreProcessMethod[0] == 'erodeThenMin':
        self._backgroundPreProcessParameters.setText(str(self._originalBackgroundPreProcessParameters[0][0]))


class _PostProcessTrajectoriesWidget(QWidget):
  def __init__(self):
    super().__init__()
    self._configFile = None
    layout = QVBoxLayout()
    layout.addWidget(util.apply_style(QLabel("Post-process animal center trajectories"), font_size='16px'), alignment=Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)
    postProcessTrajectoriesInfoLabel = QLabel("postProcessMaxDistanceAuthorized is the maximum distance in pixels above which it is considered that an animal was detected incorrectly (click on the button to adjust it visually). postProcessMaxDisapearanceFrames is the maximum number of frames for which the post-processing will consider that an animal can be incorrectly detected.")
    postProcessTrajectoriesInfoLabel.setMinimumSize(1, 1)
    postProcessTrajectoriesInfoLabel.resizeEvent = lambda evt: postProcessTrajectoriesInfoLabel.setMinimumWidth(evt.size().width()) or postProcessTrajectoriesInfoLabel.setWordWrap(evt.size().width() <= postProcessTrajectoriesInfoLabel.sizeHint().width())
    layout.addWidget(postProcessTrajectoriesInfoLabel, alignment=Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)

    formLayout = QFormLayout()
    formLayout.setFormAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)
    formLayout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.FieldsStayAtSizeHint)
    layout.addLayout(formLayout)
    self._postProcessMaxDistanceAuthorized = postProcessMaxDistanceAuthorized = QLineEdit()
    postProcessMaxDistanceAuthorized.setValidator(QIntValidator(postProcessMaxDistanceAuthorized))
    postProcessMaxDistanceAuthorized.validator().setBottom(0)

    def updatePostProcessMaxDistanceAuthorized(text):
      if text:
        self._configFile["postProcessMaxDistanceAuthorized"] = int(text)
        self._configFile["postProcessMultipleTrajectories"] = 1
      else:
        if not postProcessMaxDisapearanceFrames.text():
          if self._originalPostProcessMultipleTrajectories is not None:
            self._configFile["postProcessMultipleTrajectories"] = self._originalPostProcessMultipleTrajectories
          elif "postProcessMultipleTrajectories" in self._configFile:
            del self._configFile["postProcessMultipleTrajectories"]
        if self._originalPostProcessMaxDistanceAuthorized is not None:
          self._configFile["postProcessMaxDistanceAuthorized"] = self._originalPostProcessMaxDistanceAuthorized
        elif "postProcessMaxDistanceAuthorized" in self._configFile:
          del self._configFile["postProcessMaxDistanceAuthorized"]
    postProcessMaxDistanceAuthorized.textChanged.connect(updatePostProcessMaxDistanceAuthorized)
    postProcessMaxDistanceAuthorizedLabel = QPushButton("postProcessMaxDistanceAuthorized:")

    def modifyPostProcessMaxDistanceAuthorized():
      cap = zzVideoReading.VideoCapture(self._videoPath)
      cap.set(1, self._configFile.get("firstFrame", 1))
      ret, frame = cap.read()
      cancelled = False
      def cancel():
        nonlocal cancelled
        cancelled = True
      center, radius = util.getCircle(frame, 'Click on the center of an animal and select the distance which it can realistically travel', cancel)
      if not cancelled:
        postProcessMaxDistanceAuthorized.setText(str(radius))
    postProcessMaxDistanceAuthorizedLabel.clicked.connect(modifyPostProcessMaxDistanceAuthorized)
    formLayout.addRow(postProcessMaxDistanceAuthorizedLabel, postProcessMaxDistanceAuthorized)

    self._postProcessMaxDisapearanceFrames = postProcessMaxDisapearanceFrames = QLineEdit()
    postProcessMaxDisapearanceFrames.setValidator(QIntValidator(postProcessMaxDisapearanceFrames))
    postProcessMaxDisapearanceFrames.validator().setBottom(0)

    def updatePostProcessMaxDisapearanceFrames(text):
      if text:
        self._configFile["postProcessMaxDisapearanceFrames"] = int(text)
        self._configFile["postProcessMultipleTrajectories"] = 1
      else:
        if not postProcessMaxDistanceAuthorized.text():
          if self._originalPostProcessMultipleTrajectories is not None:
            self._configFile["postProcessMultipleTrajectories"] = self._originalPostProcessMultipleTrajectories
          elif "postProcessMultipleTrajectories" in self._configFile:
            del self._configFile["postProcessMultipleTrajectories"]
        if self._originalPostProcessMaxDisapearanceFrames is not None:
          self._configFile["postProcessMaxDisapearanceFrames"] = self._originalPostProcessMaxDisapearanceFrames
        elif "postProcessMaxDisapearanceFrames" in self._configFile:
          del self._configFile["postProcessMaxDisapearanceFrames"]
    postProcessMaxDisapearanceFrames.textChanged.connect(updatePostProcessMaxDisapearanceFrames)
    formLayout.addRow("postProcessMaxDisapearanceFrames:", postProcessMaxDisapearanceFrames)

    self.setLayout(layout)

  def refresh(self, configFile, videoPath=None):
    self._configFile = configFile
    self._videoPath = videoPath
    self._originalPostProcessMultipleTrajectories = configFile.get("postProcessMultipleTrajectories")
    self._originalPostProcessMaxDistanceAuthorized = configFile.get("postProcessMaxDistanceAuthorized")
    if self._originalPostProcessMaxDistanceAuthorized is not None:
      self._postProcessMaxDistanceAuthorized.setText(str(self._originalPostProcessMaxDistanceAuthorized))
    else:
      self._postProcessMaxDistanceAuthorized.setText('')
    self._originalPostProcessMaxDisapearanceFrames = configFile.get("postProcessMaxDisapearanceFrames")
    if self._originalPostProcessMaxDisapearanceFrames is not None:
      self._postProcessMaxDisapearanceFrames.setText(str(self._originalPostProcessMaxDisapearanceFrames))
    else:
      self._postProcessMaxDisapearanceFrames.setText('')


class _OptimizeDataAnalysisWidget(QWidget):
  def __init__(self):
    super().__init__()
    self._configFile = None
    layout = QVBoxLayout()
    layout.addWidget(util.apply_style(QLabel("Optimize data analysis"), font_size='16px'), alignment=Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)

    def speedUpAnalysisToggled(checked):
      analysisInfoWidget.setVisible(checked)
      if not checked:
        if "createPandasDataFrameOfParameters" in self._configFile:
          del self._configFile["createPandasDataFrameOfParameters"]
        if "videoFPS" in self._configFile:
          del self._configFile["videoFPS"]
        if "videoPixelSize" in self._configFile:
          del self._configFile["videoPixelSize"]
      else:
        self._configFile["createPandasDataFrameOfParameters"] = 1
        if videoFPS.text():
          self._configFile["videoFPS"] = float(videoFPS.text())
        if videoPixelSize.text():
          self._configFile["videoPixelSize"] = float(videoPixelSize.text())
    self._speedUpAnalysisCheckbox = speedUpAnalysisCheckbox = QCheckBox("Speed up final ZebraZoom behavior analysis")
    speedUpAnalysisCheckbox.toggled.connect(speedUpAnalysisToggled)
    layout.addWidget(speedUpAnalysisCheckbox, alignment=Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)

    analysisInfoLayout = QFormLayout()
    analysisInfoLayout.setFormAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)
    analysisInfoLayout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.FieldsStayAtSizeHint)
    self._videoFPS = videoFPS = QLineEdit()
    videoFPS.setValidator(QDoubleValidator(videoFPS))
    videoFPS.validator().setBottom(0)

    def videoFPSChanged(text):
      if text:
        self._configFile["videoFPS"] = float(text)
      elif "videoFPS" in self._configFile:
        del self._configFile["videoFPS"]
    videoFPS.textChanged.connect(videoFPSChanged)
    analysisInfoLayout.addRow('videoFPS:', videoFPS)
    self._videoPixelSize = videoPixelSize = QLineEdit()
    videoPixelSize.setValidator(QDoubleValidator(videoPixelSize))
    videoPixelSize.validator().setBottom(0)

    def videoPixelSizeChanged(text):
      if text:
        self._configFile["videoPixelSize"] = float(text)
      elif "videoPixelSize" in self._configFile:
        del self._configFile["videoPixelSize"]
    videoPixelSize.textChanged.connect(videoPixelSizeChanged)
    analysisInfoLayout.addRow('videoPixelSize', videoPixelSize)
    outerLayout = QVBoxLayout()
    outerLayout.addLayout(analysisInfoLayout)
    helpBtn = QPushButton("Help")
    helpBtn.clicked.connect(lambda: webbrowser.open_new("https://zebrazoom.org/documentation/docs/behaviorAnalysis/optimizingSpeedOfFinalAnalysis"))
    outerLayout.addWidget(helpBtn, alignment=Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)
    self._analysisInfoWidget = analysisInfoWidget = QWidget()
    analysisInfoWidget.setLayout(outerLayout)
    layout.addWidget(analysisInfoWidget, alignment=Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)
    self.setLayout(layout)

  def refresh(self, configFile, videoPath=None):
    self._configFile = configFile
    if "createPandasDataFrameOfParameters" in configFile:
      self._speedUpAnalysisCheckbox.setChecked(configFile["createPandasDataFrameOfParameters"])
    else:
      self._speedUpAnalysisCheckbox.setChecked(False)
    self._analysisInfoWidget.setVisible(self._speedUpAnalysisCheckbox.isChecked())
    if "videoFPS" in configFile:
      self._videoFPS.setText(str(configFile["videoFPS"]))
    if "videoPixelSize" in configFile:
      self._videoPixelSize.setText(str(configFile["videoPixelSize"]))


class _ValidationVideoOptionsWidget(QWidget):
  def __init__(self):
    super().__init__()
    self._configFile = None
    layout = QVBoxLayout()
    layout.addWidget(util.apply_style(QLabel("Validation video options"), font_size='16px'), alignment=Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)
    def updatePlotOnlyOneTailPointForVisu(checked):
      if checked:
        self._configFile["plotOnlyOneTailPointForVisu"] = 1
      elif self._originalPlotOnlyOneTailPointForVisu is None:
        if "plotOnlyOneTailPointForVisu" in self._configFile:
          del self._configFile["plotOnlyOneTailPointForVisu"]
      else:
        self._configFile["plotOnlyOneTailPointForVisu"] = 0
    self._plotOnlyOneTailPointForVisu = QCheckBox("Display tracking point only on the tail tip in validation videos")
    self._plotOnlyOneTailPointForVisu.toggled.connect(updatePlotOnlyOneTailPointForVisu)
    layout.addWidget(self._plotOnlyOneTailPointForVisu, alignment=Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)
    self.setLayout(layout)

  def refresh(self, configFile, videoPath=None):
    self._configFile = configFile
    self._originalPlotOnlyOneTailPointForVisu = configFile.get("plotOnlyOneTailPointForVisu")
    if self._originalPlotOnlyOneTailPointForVisu is not None:
      self._plotOnlyOneTailPointForVisu.setChecked(bool(self._originalPlotOnlyOneTailPointForVisu))
    else:
      self._plotOnlyOneTailPointForVisu.setChecked(False)


class _TailTrackingQualityWidget(QWidget):
  def __init__(self):
    super().__init__()
    self._configFile = None
    layout = QVBoxLayout()
    layout.addWidget(util.apply_style(QLabel("Tail tracking quality"), font_size='16px'), alignment=Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)
    layout.addWidget(QLabel("Checking this increases quality, but makes tracking slower."), alignment=Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)
    self._recalculateForegroundImageBasedOnBodyArea = QCheckBox("recalculateForegroundImageBasedOnBodyArea")

    def updateRecalculateForegroundImageBasedOnBodyArea(checked):
      if checked:
        self._configFile["recalculateForegroundImageBasedOnBodyArea"] = 1
      elif self._originalRecalculateForegroundImageBasedOnBodyArea is None:
        if "recalculateForegroundImageBasedOnBodyArea" in self._configFile:
          del self._configFile["recalculateForegroundImageBasedOnBodyArea"]
      else:
        self._configFile["recalculateForegroundImageBasedOnBodyArea"] = 0
    self._recalculateForegroundImageBasedOnBodyArea.toggled.connect(updateRecalculateForegroundImageBasedOnBodyArea)
    layout.addWidget(self._recalculateForegroundImageBasedOnBodyArea, alignment=Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)
    self.setLayout(layout)

  def refresh(self, configFile, videoPath=None):
    self._configFile = configFile
    self._originalRecalculateForegroundImageBasedOnBodyArea = configFile.get("recalculateForegroundImageBasedOnBodyArea")
    if self._originalRecalculateForegroundImageBasedOnBodyArea is not None:
      self._recalculateForegroundImageBasedOnBodyArea.setChecked(bool(self._originalRecalculateForegroundImageBasedOnBodyArea))
    else:
      self._recalculateForegroundImageBasedOnBodyArea.setChecked(False)


class _VideoRotationWidget(QWidget):
  def __init__(self):
    super().__init__()
    self._configFile = None
    layout = QVBoxLayout()
    layout.addWidget(util.apply_style(QLabel("Video rotation"), font_size='16px'), alignment=Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)
    formLayout = QFormLayout()
    formLayout.setFormAlignment(Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)
    formLayout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.FieldsStayAtSizeHint)
    layout.addLayout(formLayout)
    rotationAngleLabel = QPushButton("Rotation angle (degrees):")
    def modifyRotationAngle():
      cap = zzVideoReading.VideoCapture(self._videoPath)
      cap.set(1, self._configFile.get("firstFrame", 1))
      ret, frame = cap.read()

      try:
        angle = float(self._rotationAngleLineEdit.text())
      except ValueError:
        angle = 0.

      angle = util.getRotationAngle(frame, angle)
      if angle is not None:
        self._rotationAngleLineEdit.setText("{:.2f}".format(angle))
    rotationAngleLabel.clicked.connect(modifyRotationAngle)
    self._rotationAngleLineEdit = QLineEdit()
    def updateRotationAngle(text):
      if text:
        try:
          value = float(text)
        except ValueError:
          return
        self._configFile["backgroundPreProcessMethod"] = ["rotate"]
        self._configFile["imagePreProcessMethod"] = ["rotate"]
        self._configFile["backgroundPreProcessParameters"] = [[value]]
        self._configFile["imagePreProcessParameters"] = [[value]]
      else:
        if self._originalBackgroundPreProcessMethod is not None:
          self._configFile["backgroundPreProcessMethod"] = self._originalBackgroundPreProcessMethod
        elif "backgroundPreProcessMethod" in self._configFile:
          del self._configFile["backgroundPreProcessMethod"]
        if self._originalBackgroundPreProcessParameters is not None:
          self._configFile["backgroundPreProcessParameters"] = self._originalBackgroundPreProcessParameters
        elif "backgroundPreProcessParameters" in self._configFile:
          del self._configFile["backgroundPreProcessParameters"]
        if self._originalImagePreProcessMethod is not None:
          self._configFile["imagePreProcessMethod"] = self._originalImagePreProcessMethod
        elif "imagePreProcessMethod" in self._configFile:
          del self._configFile["imagePreProcessMethod"]
        if self._originalImagePreProcessParameters is not None:
          self._configFile["imagePreProcessParameters"] = self._originalImagePreProcessParameters
        elif "imagePreProcessParameters" in self._configFile:
          del self._configFile["imagePreProcessParameters"]
    self._rotationAngleLineEdit.textChanged.connect(updateRotationAngle)
    formLayout.addRow(rotationAngleLabel, self._rotationAngleLineEdit)
    self.setLayout(layout)

  def refresh(self, configFile, videoPath=None):
    self._configFile = configFile
    self._videoPath = videoPath
    self._originalBackgroundPreProcessMethod = configFile.get("backgroundPreProcessMethod")
    self._originalBackgroundPreProcessParameters = configFile.get("backgroundPreProcessParameters")
    if self._originalBackgroundPreProcessParameters is not None and self._originalBackgroundPreProcessMethod is not None:
      if self._originalBackgroundPreProcessMethod[0] == 'rotate':
        self._rotationAngleLineEdit.setText(str(self._originalBackgroundPreProcessParameters[0][0]))
      else:
        self._rotationAngleLineEdit.setText('')
    else:
      self._rotationAngleLineEdit.setText('')
    self._originalImagePreProcessMethod = configFile.get("imagePreProcessMethod")
    self._originalImagePreProcessParameters = configFile.get("imagePreProcessParameters")
    if self._originalImagePreProcessParameters is not None and self._originalBackgroundPreProcessMethod is not None and self._originalBackgroundPreProcessMethod[0] == 'rotate':
      self._rotationAngleLineEdit.setText(str(self._originalImagePreProcessParameters[0][0]))
    else:
      self._rotationAngleLineEdit.setText('')


class _NonStationaryBackgroundWidget(QWidget):
  def __init__(self):
    super().__init__()
    self._configFile = None
    layout = QVBoxLayout()
    layout.addWidget(util.apply_style(QLabel("Non stationary background"), font_size='16px'), alignment=Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)

    self._updateBackgroundOnEveryFrameCheckbox = QCheckBox("Update background on every frame")
    def updateBackroundOnEveryFrame(checked):
      if checked:
        self._configFile["updateBackgroundAtInterval"] = 1
      else:
        if self._originalUpdateBackgroundAtInterval is None:
          if "updateBackgroundAtInterval" in self._configFile:
            del self._configFile["updateBackgroundAtInterval"]
        else:
          self._configFile["updateBackgroundAtInterval"] = 0
    self._updateBackgroundOnEveryFrameCheckbox.toggled.connect(updateBackroundOnEveryFrame)
    layout.addWidget(self._updateBackgroundOnEveryFrameCheckbox, alignment=Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)

    self._useFirstFrameAsBackgroundCheckbox = QCheckBox("Use the first frame as background")
    def useFirstFrameAsBackground(checked):
      if checked:
        self._configFile["useFirstFrameAsBackground"] = 1
      else:
        if self._originalUseFirstFrameAsBackground is None:
          if "useFirstFrameAsBackground" in self._configFile:
            del self._configFile["useFirstFrameAsBackground"]
        else:
          self._configFile["useFirstFrameAsBackground"] = 0
    self._useFirstFrameAsBackgroundCheckbox.toggled.connect(useFirstFrameAsBackground)
    layout.addWidget(self._useFirstFrameAsBackgroundCheckbox, alignment=Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)

    formLayout = QFormLayout()
    formLayout.setFormAlignment(Qt.AlignmentFlag.AlignCenter)
    formLayout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.FieldsStayAtSizeHint)
    self._lastFrameForInitialBackDetect = lastFrameForInitialBackDetect = QLineEdit()
    lastFrameForInitialBackDetect.setValidator(QIntValidator(lastFrameForInitialBackDetect))
    lastFrameForInitialBackDetect.validator().setBottom(1)

    def updateLastFrameForInitialBackDetect(text):
      if text:
        self._configFile["lastFrameForInitialBackDetect"] = int(text)
      else:
          if self._originalLastFrameForInitialBackDetect is None:
            if 'lastFrameForInitialBackDetect' in self._configFile:
              del self._configFile['lastFrameForInitialBackDetect']
          else:
            self._configFile["lastFrameForInitialBackDetect"] = 0
    lastFrameForInitialBackDetect.textChanged.connect(updateLastFrameForInitialBackDetect)
    formLayout.addRow('Calculate background using the first frame and frame:', lastFrameForInitialBackDetect)
    layout.addLayout(formLayout)

    self.setLayout(layout)

  def refresh(self, configFile, videoPath=None):
    self._configFile = configFile
    self._originalUpdateBackgroundAtInterval = configFile.get("updateBackgroundAtInterval")
    self._originalUseFirstFrameAsBackground = configFile.get("useFirstFrameAsBackground")
    self._originalLastFrameForInitialBackDetect = configFile.get("lastFrameForInitialBackDetect")
    if self._originalUpdateBackgroundAtInterval is not None:
      self._updateBackgroundOnEveryFrameCheckbox.setChecked(self._originalUpdateBackgroundAtInterval)
    else:
      self._updateBackgroundOnEveryFrameCheckbox.setChecked(False)
    if self._originalUseFirstFrameAsBackground is not None:
      self._useFirstFrameAsBackgroundCheckbox.setChecked(self._originalUseFirstFrameAsBackground)
    else:
      self._useFirstFrameAsBackgroundCheckbox.setChecked(False)
    if self._originalLastFrameForInitialBackDetect is not None:
      self._lastFrameForInitialBackDetect.setText(str(self._originalLastFrameForInitialBackDetect))


class _NoMultiprocessingWidget(QWidget):
  def __init__(self):
    super().__init__()
    self._configFile = None
    layout = QVBoxLayout()
    layout.addWidget(util.apply_style(QLabel("No multiprocessing over wells"), font_size='16px'), alignment=Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)
    self._noMultiprocessingCheckbox = QCheckBox("No multiprocessing over wells")
    def noMultiprocessingToggled(checked):
      if checked:
        self._configFile["fasterMultiprocessing"] = 2
      else:
        if self._originalNoMultiprocessing is None:
          if "fasterMultiprocessing" in self._configFile:
            del self._configFile["fasterMultiprocessing"]
        else:
          self._configFile["fasterMultiprocessing"] = 0
    self._noMultiprocessingCheckbox.toggled.connect(noMultiprocessingToggled)
    layout.addWidget(self._noMultiprocessingCheckbox, alignment=Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)
    self.setLayout(layout)

  def refresh(self, configFile, videoPath=None):
    self._configFile = configFile
    self._originalNoMultiprocessing = configFile.get("fasterMultiprocessing")
    if self._originalNoMultiprocessing is not None:
      self._noMultiprocessingCheckbox.setChecked(self._originalNoMultiprocessing == 2)
    else:
      self._noMultiprocessingCheckbox.setChecked(False)


class _AdditionalCalculationsWidget(QWidget):
  def __init__(self):
    super().__init__()
    self._configFile = None
    layout = QVBoxLayout()
    layout.addWidget(util.apply_style(QLabel("Additional calculations"), font_size='16px'), alignment=Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)

    self._calculateCurvatureCheckbox = QCheckBox("Calculate curvature")
    def calculateCurvatureToggled(checked):
      if checked:
        self._configFile["perBoutOutput"] = 1
        nbTailPointsWidget.setVisible(True)
      else:
        if self._originalCalculateCurvature is None:
          if "perBoutOutput" in self._configFile:
            del self._configFile["perBoutOutput"]
        else:
          self._configFile["perBoutOutput"] = 0
        nbTailPointsWidget.setVisible(False)
    self._calculateCurvatureCheckbox.toggled.connect(calculateCurvatureToggled)
    layout.addWidget(self._calculateCurvatureCheckbox, alignment=Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)
    nbTailPointsLayout = QFormLayout()
    nbTailPointsLayout.setFormAlignment(Qt.AlignmentFlag.AlignCenter)
    nbTailPointsLayout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.FieldsStayAtSizeHint)
    self._nbTailPoints = QLineEdit()
    self._nbTailPoints.setValidator(QIntValidator(self._nbTailPoints))
    self._nbTailPoints.validator().setBottom(1)
    self._nbTailPoints.setPlaceholderText('10')
    def nbTailPointsChanged(text):
      if not text:
        if 'nbTailPoints' in self._configFile:
          del self._configFile['nbTailPoints']
      else:
        self._configFile['nbTailPoints'] = int(text)
    self._nbTailPoints.textChanged.connect(nbTailPointsChanged)
    nbTailPointsLayout.addRow('Number of tail points:', self._nbTailPoints)
    nbTailPointsWidget = QWidget()
    nbTailPointsWidget.setLayout(nbTailPointsLayout)
    nbTailPointsWidget.setVisible(False)
    layout.addWidget(nbTailPointsWidget, alignment=Qt.AlignmentFlag.AlignCenter)

    self._calculateTailAngleHeatmapCheckbox = QCheckBox("Calculate tail angle heatmap")
    def calculateTailAngleHeatmapToggled(checked):
      if checked:
        self._configFile["tailAnglesHeatMap"] = 1
      else:
        if self._originalCalculateTailAngleHeatmap is None:
          if "tailAnglesHeatMap" in self._configFile:
            del self._configFile["tailAnglesHeatMap"]
        else:
          self._configFile["tailAnglesHeatMap"] = 0
    self._calculateTailAngleHeatmapCheckbox.toggled.connect(calculateTailAngleHeatmapToggled)
    layout.addWidget(self._calculateTailAngleHeatmapCheckbox, alignment=Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)
    self.setLayout(layout)

  def refresh(self, configFile, videoPath=None):
    self._configFile = configFile
    self._originalCalculateCurvature = configFile.get("perBoutOutput")
    if self._originalCalculateCurvature is not None:
      self._calculateCurvatureCheckbox.setChecked(bool(self._originalCalculateCurvature))
    else:
      self._calculateCurvatureCheckbox.setChecked(False)
    self._originalCalculateTailAngleHeatmap = configFile.get("tailAnglesHeatMap")
    if self._originalCalculateTailAngleHeatmap is not None:
      self._calculateTailAngleHeatmapCheckbox.setChecked(bool(self._originalCalculateTailAngleHeatmap))
    else:
      self._calculateTailAngleHeatmapCheckbox.setChecked(False)
    self._nbTailPoints.setText(str(configFile.get("nbTailPoints", '')))


class _DocumentationLinksWidget(QWidget):
  def __init__(self):
    super().__init__()
    self._configFile = None
    layout = QVBoxLayout()
    layout.addWidget(util.apply_style(QLabel("Documentation links"), font_size='16px'), alignment=Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)
    speedUpTrackingBtn = QPushButton("Speed up tracking for 'Track heads and tails of freely swimming fish'")
    speedUpTrackingBtn.clicked.connect(lambda: webbrowser.open_new("https://github.com/oliviermirat/ZebraZoom/blob/master/TrackingSpeedOptimization.md"))
    layout.addWidget(speedUpTrackingBtn, alignment=Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)
    documentationBtn = QPushButton("Help")
    documentationBtn.clicked.connect(lambda: webbrowser.open_new("https://zebrazoom.org/documentation/docs/configurationFile/throughGUI/trackingFreelySwimmingConfigOptimization"))
    layout.addWidget(documentationBtn, alignment=Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)
    self.setLayout(layout)

  def refresh(self, configFile, videoPath=None):
    pass


class OptimizeConfigFile(QWidget):
  def __init__(self, controller):
    super().__init__(controller.window)
    self.controller = controller
    self._originalConfig = {}

    self._headEmbeddedWidgets = set()
    self._freelySwimmingWidgets = set()
    self._fastCenterOfMassWidgets = set()
    self._centerOfMassWidgets = set()
    self._fastFishTrackingWidgets = set()
    self._advancedHeadEmbeddedWidgets = [StoreValidationVideoWidget, _OptimizeDataAnalysisWidget, _ValidationVideoOptionsWidget, _AdditionalCalculationsWidget]
    self._advancedFreelySwimmingWidgets = [StoreValidationVideoWidget, _SolveIssuesNearBordersWidget, _PostProcessTrajectoriesWidget, _OptimizeDataAnalysisWidget, _ValidationVideoOptionsWidget, _TailTrackingQualityWidget,
                                           _VideoRotationWidget, _NonStationaryBackgroundWidget, _NoMultiprocessingWidget, _AdditionalCalculationsWidget, _DocumentationLinksWidget]
    self._advancedFastCenterOfMassWidgets = [StoreValidationVideoWidget, _SolveIssuesNearBordersWidget, _PostProcessTrajectoriesWidget, _OptimizeDataAnalysisWidget]
    self._advancedCenterOfMassWidgets = [StoreValidationVideoWidget, _SolveIssuesNearBordersWidget, _PostProcessTrajectoriesWidget, _OptimizeDataAnalysisWidget]
    self._advancedFastFishTrackingWidgets = [StoreValidationVideoWidget, _OptimizeDataAnalysisWidget, _AdditionalCalculationsWidget, _NonStationaryBackgroundWidget]

    layout = QVBoxLayout()
    layout.addWidget(util.apply_style(QLabel("Optimize previously created configuration file", self), font=controller.title_font), alignment=Qt.AlignmentFlag.AlignCenter)

    optimizeButtonsLayout = QHBoxLayout()
    optimizeButtonsLayout.addStretch()
    optimizeFreelySwimmingBtn = util.apply_style(QPushButton("Optimize fish freely swimming tail tracking configuration file parameters", self), background_color=util.LIGHT_YELLOW)
    optimizeFreelySwimmingBtn.clicked.connect(lambda: util.addToHistory(controller.calculateBackgroundFreelySwim)(controller, 0, automaticParameters=True, useNext=False))
    optimizeButtonsLayout.addWidget(optimizeFreelySwimmingBtn, alignment=Qt.AlignmentFlag.AlignCenter)
    self._freelySwimmingWidgets.add(optimizeFreelySwimmingBtn)
    optimizeFastFishTrackingBtn = util.apply_style(QPushButton("Optimize fast fish tracking and bout detection configuration file parameters", self), background_color=util.LIGHT_YELLOW)
    optimizeFastFishTrackingBtn.clicked.connect(lambda: util.addToHistory(adjustFastFishTrackingPage)(useNext=False))
    optimizeButtonsLayout.addWidget(optimizeFastFishTrackingBtn, alignment=Qt.AlignmentFlag.AlignCenter)
    self._fastFishTrackingWidgets.add(optimizeFastFishTrackingBtn)
    optimizeHeadEmbeddedBtn = util.apply_style(QPushButton("Optimize head embedded tracking configuration file parameters", self), background_color=util.LIGHT_YELLOW)
    optimizeHeadEmbeddedBtn.clicked.connect(lambda: util.addToHistory(controller.calculateBackground)(controller, 0, useNext=False))
    optimizeButtonsLayout.addWidget(optimizeHeadEmbeddedBtn, alignment=Qt.AlignmentFlag.AlignCenter)
    self._headEmbeddedWidgets.add(optimizeHeadEmbeddedBtn)
    optimizeBoutBtn = util.apply_style(QPushButton("Optimize/Add bouts detection (only for one animal per well)", self), background_color=util.LIGHT_YELLOW)
    optimizeBoutBtn.clicked.connect(lambda: util.addToHistory(controller.calculateBackgroundFreelySwim)(controller, 0, boutDetectionsOnly=True, useNext=False))
    optimizeButtonsLayout.addWidget(optimizeBoutBtn, alignment=Qt.AlignmentFlag.AlignCenter)
    self._freelySwimmingWidgets.add(optimizeBoutBtn)
    self._headEmbeddedWidgets.add(optimizeBoutBtn)
    self._fastCenterOfMassWidgets.add(optimizeBoutBtn)
    optimizeButtonsLayout.addStretch()
    layout.addLayout(optimizeButtonsLayout)

    def updateOutputValidationVideoContrastImprovement(checked):
      if checked:
        controller.configFile["outputValidationVideoContrastImprovement"] = 1
      elif self._originalOutputValidationVideoContrastImprovement is None:
        if "outputValidationVideoContrastImprovement" in controller.configFile:
          del controller.configFile["outputValidationVideoContrastImprovement"]
      else:
        controller.configFile["outputValidationVideoContrastImprovement"] = 0
    self._improveContrastCheckbox = QCheckBox("Improve contrast on validation video", self)
    self._improveContrastCheckbox.toggled.connect(updateOutputValidationVideoContrastImprovement)
    layout.addWidget(self._improveContrastCheckbox, alignment=Qt.AlignmentFlag.AlignCenter)
    self._headEmbeddedWidgets.add(self._improveContrastCheckbox)
    headEmbeddedDocumentationBtn = util.apply_style(QPushButton("Help", self), background_color=util.LIGHT_YELLOW)
    headEmbeddedDocumentationBtn.clicked.connect(lambda: webbrowser.open_new("https://zebrazoom.org/documentation/docs/configurationFile/throughGUI/trackingheadEmbeddedConfigOptimization"))
    layout.addWidget(headEmbeddedDocumentationBtn, alignment=Qt.AlignmentFlag.AlignCenter)
    self._headEmbeddedWidgets.add(headEmbeddedDocumentationBtn)

    self._expander = util.Expander(self, 'Show advanced options', QVBoxLayout(), showFrame=True, addScrollbars=True)
    layout.addWidget(self._expander)

    frame = QFrame()
    frame.setFrameShadow(QFrame.Shadow.Raised)
    frame.setFrameShape(QFrame.Shape.Box)
    frameLayout = QVBoxLayout()
    testCheckbox = QCheckBox("Test tracking after saving config", self)
    testCheckbox.setChecked(True)
    testCheckbox.clearFocus()
    frameLayout.addWidget(testCheckbox, alignment=Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignBottom)
    saveBtn = util.apply_style(QPushButton("Save Config File", self), background_color=util.DEFAULT_BUTTON_COLOR)
    saveBtn.clicked.connect(lambda: controller.finishConfig(testCheckbox.isChecked()))
    frameLayout.addWidget(saveBtn, alignment=Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignTop)
    frame.setLayout(frameLayout)
    layout.addWidget(frame, alignment=Qt.AlignmentFlag.AlignCenter)

    startPageBtn = QPushButton("Go to the start page", self)
    startPageBtn.clicked.connect(lambda: controller.show_frame("StartPage"))
    layout.addWidget(startPageBtn, alignment=Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(QLabel("If you don't manage to get a good configuration file that fits your needs, email us at info@zebrazoom.org.", self), alignment=Qt.AlignmentFlag.AlignCenter)

    centralWidget = QWidget()
    centralWidget.sizeHint = lambda *args: QSize(1152, 768)
    centralWidget.setLayout(layout)
    wrapperLayout = QVBoxLayout()
    wrapperLayout.addWidget(centralWidget, alignment=Qt.AlignmentFlag.AlignCenter)
    self.setLayout(wrapperLayout)

  def _calculateAdvancedOptionsLayout(self, visibleWidgets):
    rows = len(visibleWidgets) // 2 + len(visibleWidgets) % 2
    advancedOptionsLayout = QGridLayout()
    for idx in range(1, rows * 2 - 1, 2):
      hframe = QFrame()
      hframe.setFrameShape(QFrame.Shape.HLine)
      advancedOptionsLayout.addWidget(hframe, idx, 0, 1, 3)
    vframe = QFrame()
    vframe.setFrameShape(QFrame.Shape.VLine)
    advancedOptionsLayout.addWidget(vframe, 0, 1, rows * 2, 1)

    widgets = iter(visibleWidgets)
    for row in range(0, rows * 2, 2):
      for col in (0, 2):
        widget = next(widgets, None)
        if widget is None:
          continue
        advancedOptionsLayout.addWidget(widget, row, col, alignment=Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)

    for idx in range(advancedOptionsLayout.columnCount()):
      advancedOptionsLayout.setColumnStretch(idx, 1)

    return advancedOptionsLayout

  def _rebuildAdvancedOptions(self):
    app = QApplication.instance()
    if app.configFile.get("trackingImplementation") == "fastFishTracking.tracking":
      visibleWidgets = self._fastFishTrackingWidgets
      advancedWidgets = self._advancedFastFishTrackingWidgets
    else:
      trackingMethod = app.configFile.get("trackingMethod")
      if not trackingMethod:
        if app.configFile.get("headEmbeded", False):
          visibleWidgets = self._headEmbeddedWidgets
          advancedWidgets = self._advancedHeadEmbeddedWidgets
        else:
          visibleWidgets = self._freelySwimmingWidgets
          advancedWidgets = self._advancedFreelySwimmingWidgets
      elif trackingMethod == "fastCenterOfMassTracking_KNNbackgroundSubtraction" or \
          trackingMethod == "fastCenterOfMassTracking_ClassicalBackgroundSubtraction":
        visibleWidgets = self._fastCenterOfMassWidgets
        advancedWidgets = self._advancedFastCenterOfMassWidgets
      else:
        assert trackingMethod == "classicCenterOfMassTracking"
        visibleWidgets = self._centerOfMassWidgets
        advancedWidgets = self._advancedCenterOfMassWidgets
    for widget in self._freelySwimmingWidgets | self._headEmbeddedWidgets | self._fastCenterOfMassWidgets | self._centerOfMassWidgets | self._fastFishTrackingWidgets:
      if widget in visibleWidgets:
        widget.show()
      else:
        widget.hide()
    visibleWidgets = [type_() for type_ in advancedWidgets]
    for widget in visibleWidgets:
      widget.refresh(app.configFile, app.videoToCreateConfigFileFor)
    self._expander.hide()
    self._expander.updateLayout(self._calculateAdvancedOptionsLayout(visibleWidgets))
    maximumHeight = self._expander.maximumHeight()
    self._expander.setMaximumHeight(self.height())
    layout = self.layout().itemAt(0).widget().layout()
    layout.setStretchFactor(self._expander, 1)
    self._expander.show()
    availableHeight = self._expander.size().height()
    layout.setStretchFactor(self._expander, 0)
    self._expander.setMaximumHeight(maximumHeight)
    self._expander.refresh(availableHeight=availableHeight)

  def refresh(self):
    app = QApplication.instance()
    self._rebuildAdvancedOptions()
    self._originalOutputValidationVideoContrastImprovement = app.configFile.get("outputValidationVideoContrastImprovement")
    if self._originalOutputValidationVideoContrastImprovement is not None:
      self._improveContrastCheckbox.setChecked(bool(self._originalOutputValidationVideoContrastImprovement))
    else:
      self._improveContrastCheckbox.setChecked(False)


class _ClickableImageLabel(QLabel):
  def __init__(self, parent, pixmap, clickedCallback):
    super().__init__(parent)
    self._originalPixmap = pixmap
    self._clickedCallback = clickedCallback
    self.setMinimumSize(1, 1)

  def resizeEvent(self, evt):
    scaling = self.devicePixelRatio() if PYQT6 else self.devicePixelRatioF()
    size = self._originalPixmap.size().scaled(self.size(), Qt.AspectRatioMode.KeepAspectRatio)
    img = self._originalPixmap.scaled(int(size.width() * scaling), int(size.height() * scaling))
    img.setDevicePixelRatio(scaling)
    self.setPixmap(img)
    blocked = self.blockSignals(True)
    self.resize(size)
    self.blockSignals(blocked)

  def mousePressEvent(self, evt):
    QApplication.restoreOverrideCursor()
    self._clickedCallback()

  def enterEvent(self, evt):
    QApplication.setOverrideCursor(Qt.CursorShape.PointingHandCursor)

  def leaveEvent(self, evt):
    QApplication.restoreOverrideCursor()


class ChooseGeneralExperiment(QWidget):
  def __init__(self, controller):
    super().__init__(controller.window)
    self.controller = controller

    layout = QGridLayout()
    layout.setSpacing(2)
    layout.setRowStretch(3, 1)
    layout.setColumnStretch(0, 1)
    layout.setColumnStretch(2, 1)
    layout.setColumnStretch(4, 1)
    layout.addItem(QSpacerItem(16, 16), 4, 1)
    layout.addItem(QSpacerItem(16, 16), 4, 3)
    curDirPath = os.path.dirname(os.path.realpath(__file__))

    layout.addWidget(util.apply_style(QLabel("Prepare Config File", self), font=controller.title_font), 0, 0, 1, 5, Qt.AlignmentFlag.AlignCenter)
    freelySwimmingTitleLabel = util.apply_style(QLabel("Head and tail tracking of freely swimming fish", self), font=QFont('Helvetica', 14, QFont.Weight.Bold))
    freelySwimmingTitleLabel.setWordWrap(True)
    layout.addWidget(freelySwimmingTitleLabel, 1, 0)
    freelySwimmingLabel = QLabel("Multiple fish can be tracked in the same well but the tail tracking can be mediocre when fish collide. Each well should contain the same number of fish.", self)
    freelySwimmingLabel.setWordWrap(True)
    layout.addWidget(freelySwimmingLabel, 2, 0)
    freelySwimmingImage = _ClickableImageLabel(self, QPixmap(os.path.join(curDirPath, 'freelySwimming.png')), lambda: controller.chooseGeneralExperimentFirstStep(controller, True, False, False, False, False, False))
    layout.addWidget(freelySwimmingImage, 3, 0)

    headEmbeddedTitleLabel = util.apply_style(QLabel("Tail tracking of head-embedded fish", self), font=QFont('Helvetica', 14, QFont.Weight.Bold))
    headEmbeddedTitleLabel.setWordWrap(True)
    layout.addWidget(headEmbeddedTitleLabel, 1, 2)
    headEmbeddedImage = _ClickableImageLabel(self, QPixmap(os.path.join(curDirPath, 'headEmbedded.png')), lambda: controller.chooseGeneralExperimentFirstStep(controller, False, True, False, False, False, False))
    layout.addWidget(headEmbeddedImage, 3, 2)

    centerOfMassTitleLabel = util.apply_style(QLabel("Center of mass tracking for any kind of animal", self), font=QFont('Helvetica', 14, QFont.Weight.Bold))
    centerOfMassTitleLabel.setWordWrap(True)
    layout.addWidget(centerOfMassTitleLabel, 1, 4)
    centerOfMassImage = _ClickableImageLabel(self, QPixmap(os.path.join(curDirPath, 'centerOfMassAnyAnimal2.png')), lambda: util.addToHistory(controller.show_frame)("ChooseCenterOfMassTracking"))
    layout.addWidget(centerOfMassImage, 3, 4)

    buttonsLayout = QHBoxLayout()
    buttonsLayout.addStretch()
    backBtn = QPushButton("Back", self)
    backBtn.setObjectName("back")
    buttonsLayout.addWidget(backBtn, alignment=Qt.AlignmentFlag.AlignCenter)
    startPageBtn = QPushButton("Go to the start page", self)
    startPageBtn.clicked.connect(lambda: controller.show_frame("StartPage"))
    buttonsLayout.addWidget(startPageBtn, alignment=Qt.AlignmentFlag.AlignCenter)
    buttonsLayout.addStretch()
    layout.addLayout(buttonsLayout, 5, 0, 1, 5)

    self.setLayout(layout)


class ChooseCenterOfMassTracking(QWidget):
  def __init__(self, controller):
    super().__init__(controller.window)
    self.controller = controller

    layout = QGridLayout()
    layout.setSpacing(2)
    layout.setRowStretch(2, 1)
    layout.setColumnStretch(0, 1)
    layout.setColumnStretch(2, 1)
    layout.addItem(QSpacerItem(16, 16), 4, 1)
    curDirPath = os.path.dirname(os.path.realpath(__file__))

    layout.addWidget(util.apply_style(QLabel("Prepare Config File", self), font=controller.title_font), 0, 0, 1, 3, Qt.AlignmentFlag.AlignCenter)

    fastCenterOfMassTitleLabel = util.apply_style(QLabel("Center of mass tracking for only one animal per well", self), font=QFont('Helvetica', 14, QFont.Weight.Bold))
    fastCenterOfMassTitleLabel.setWordWrap(True)
    layout.addWidget(fastCenterOfMassTitleLabel, 1, 0)
    fastCenterOfMassImage = _ClickableImageLabel(self, QPixmap(os.path.join(curDirPath, 'screen.png')), lambda: controller.chooseGeneralExperimentFirstStep(controller, False, False, False, False, False, True))
    layout.addWidget(fastCenterOfMassImage, 2, 0)

    centerOfMassTitleLabel = util.apply_style(QLabel("Center of mass tracking for more than one animal per well", self), font=QFont('Helvetica', 14, QFont.Weight.Bold))
    centerOfMassTitleLabel.setWordWrap(True)
    layout.addWidget(centerOfMassTitleLabel, 1, 2)
    centerOfMassImage = _ClickableImageLabel(self, QPixmap(os.path.join(curDirPath, 'centerOfMassAnyAnimal.png')), lambda: controller.chooseGeneralExperimentFirstStep(controller, False, False, False, False, True, False))
    layout.addWidget(centerOfMassImage, 2, 2)

    buttonsLayout = QHBoxLayout()
    buttonsLayout.addStretch()
    backBtn = QPushButton("Back", self)
    backBtn.setObjectName("back")
    buttonsLayout.addWidget(backBtn, alignment=Qt.AlignmentFlag.AlignCenter)
    startPageBtn = QPushButton("Go to the start page", self)
    startPageBtn.clicked.connect(lambda: controller.show_frame("StartPage"))
    buttonsLayout.addWidget(startPageBtn, alignment=Qt.AlignmentFlag.AlignCenter)
    buttonsLayout.addStretch()
    layout.addLayout(buttonsLayout, 4, 0, 1, 3)

    self.setLayout(layout)


class FreelySwimmingExperiment(QWidget):
  def __init__(self, controller):
    super().__init__(controller.window)
    self.controller = controller
    self.preferredSize = (750, 500)

    layout = QVBoxLayout()
    layout.addWidget(util.apply_style(QLabel("Prepare Config File for Freely Swimming Fish:", self), font=controller.title_font), alignment=Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(util.apply_style(QLabel("Choose only one of the options below:", self), font=QFont("Helvetica", 12)), alignment=Qt.AlignmentFlag.AlignCenter)
    freeZebra2RadioButton = QRadioButton("Recommended method: Automatic Setting", self)
    freeZebra2RadioButton.setChecked(True)
    layout.addWidget(freeZebra2RadioButton, alignment=Qt.AlignmentFlag.AlignCenter)
    advancedOptionsLayout = QVBoxLayout()
    freeZebraRadioButton = QRadioButton("Alternative method: Manual Parameters Setting", self)
    advancedOptionsLayout.addWidget(freeZebraRadioButton, alignment=Qt.AlignmentFlag.AlignCenter)
    advancedOptionsLayout.addWidget(QLabel("It's more difficult to create a configuration file with this method, but it can sometimes be useful as an alternative.", self), alignment=Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(util.Expander(self, "Show advanced options", advancedOptionsLayout))

    buttonsLayout = QHBoxLayout()
    buttonsLayout.addStretch()
    backBtn = QPushButton("Back", self)
    backBtn.setObjectName("back")
    buttonsLayout.addWidget(backBtn, alignment=Qt.AlignmentFlag.AlignCenter)
    startPageBtn = QPushButton("Go to the start page", self)
    startPageBtn.clicked.connect(lambda: controller.show_frame("StartPage"))
    buttonsLayout.addWidget(startPageBtn, alignment=Qt.AlignmentFlag.AlignCenter)
    nextBtn = util.apply_style(QPushButton("Next", self), background_color=util.DEFAULT_BUTTON_COLOR)
    nextBtn.clicked.connect(lambda: util.addToHistory(controller.chooseGeneralExperiment)(controller, freeZebraRadioButton.isChecked(), 0, 0, 0, 0, freeZebra2RadioButton.isChecked()))
    buttonsLayout.addWidget(nextBtn, alignment=Qt.AlignmentFlag.AlignCenter)
    buttonsLayout.addStretch()
    layout.addLayout(buttonsLayout)

    self.setLayout(layout)


class WellOrganisation(QWidget):
  def __init__(self, controller):
    super().__init__(controller.window)
    self.controller = controller

    layout = QGridLayout()
    layout.setSpacing(2)
    layout.setRowStretch(3, 1)
    layout.setRowStretch(6, 1)
    layout.setColumnStretch(0, 1)
    layout.setColumnStretch(2, 1)
    layout.addItem(QSpacerItem(16, 16), 4, 1, 1, 1)
    curDirPath = os.path.dirname(os.path.realpath(__file__))

    titleLabel = util.apply_style(QLabel("ZebraZoom will run the tracking in parallel on different areas/wells of the video. How do you want these areas/wells to be detected?", self), font=controller.title_font)
    titleLabel.setMinimumSize(1, 1)
    titleLabel.resizeEvent = lambda evt: titleLabel.setMinimumWidth(evt.size().width()) or titleLabel.setWordWrap(evt.size().width() <= titleLabel.sizeHint().width())
    layout.addWidget(titleLabel, 0, 0, 1, 3, Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(util.apply_style(QLabel("General methods:", self), font=util.TITLE_FONT), 1, 0)
    layout.addWidget(util.apply_style(QLabel("Manually defined regions of interest:", self), font=util.TITLE_FONT), 1, 2)

    def labelResized(label, evt):
      scaling = label.devicePixelRatio() if PYQT6 else label.devicePixelRatioF()
      size = label.originalPixmap.size().scaled(label.size(), Qt.AspectRatioMode.KeepAspectRatio)
      img = label.originalPixmap.scaled(int(size.width() * scaling), int(size.height() * scaling))
      img.setDevicePixelRatio(scaling)
      label.setPixmap(img)

    gridSystemTitleLabel = util.apply_style(QLabel("Grid system (recommended in many cases)", self), font=QFont('Helvetica', 14, QFont.Weight.Bold))
    gridSystemTitleLabel.setWordWrap(True)
    layout.addWidget(gridSystemTitleLabel, 2, 0)
    gridSystemImage = _ClickableImageLabel(self, QPixmap(os.path.join(curDirPath, 'gridSystem.png')), lambda: controller.wellOrganisation(controller, False, False, False, False, False, True))
    layout.addWidget(gridSystemImage, 3, 0)

    multipleROITitleLabel = util.apply_style(QLabel("Chosen at runtime, right before tracking starts (multiple regions possible)", self), font=QFont('Helvetica', 14, QFont.Weight.Bold))
    multipleROITitleLabel.setWordWrap(True)
    layout.addWidget(multipleROITitleLabel, 2, 2)
    multipleROIImage = _ClickableImageLabel(self, QPixmap(os.path.join(curDirPath, 'runtimeROI.png')), lambda: controller.wellOrganisation(controller, False, False, False, False, True, False))
    layout.addWidget(multipleROIImage, 3, 2)

    wholeVideoTitleLabel = util.apply_style(QLabel("Whole video", self), font=QFont('Helvetica', 14, QFont.Weight.Bold))
    wholeVideoTitleLabel.setWordWrap(True)
    layout.addWidget(wholeVideoTitleLabel, 5, 0)
    wholeVideoImage = _ClickableImageLabel(self, QPixmap(os.path.join(curDirPath, 'wholeVideo.png')), lambda: controller.wellOrganisation(controller, False, False, False, True, False, False))
    layout.addWidget(wholeVideoImage, 6, 0)

    singleROITitleLabel = util.apply_style(QLabel("Fixed in the configuration file (only one region)", self), font=QFont('Helvetica', 14, QFont.Weight.Bold))
    singleROITitleLabel.setWordWrap(True)
    layout.addWidget(singleROITitleLabel, 5, 2)
    singleROIImage = _ClickableImageLabel(self, QPixmap(os.path.join(curDirPath, 'configFileROI.png')), lambda: controller.wellOrganisation(controller, False, False, True, False, False, False))
    layout.addWidget(singleROIImage, 6, 2)

    advancedOptionsLayout = QHBoxLayout()
    advancedOptionsLayout.addStretch()
    circularWellsBtn = QPushButton("Circular wells (beta version, unstable)")
    circularWellsBtn.clicked.connect(lambda: controller.wellOrganisation(controller, True, False, False, False, False, False))
    advancedOptionsLayout.addWidget(circularWellsBtn)
    rectangularWellsBtn = QPushButton("Rectangular wells (beta version, unstable)")
    rectangularWellsBtn.clicked.connect(lambda: controller.wellOrganisation(controller, False, True, False, False, False, False))
    advancedOptionsLayout.addWidget(rectangularWellsBtn)
    advancedOptionsLayout.addStretch()
    layout.addWidget(util.Expander(self, 'Show advanced options', advancedOptionsLayout), 7, 0, 1, 3)

    buttonsLayout = QHBoxLayout()
    buttonsLayout.addStretch()
    backBtn = QPushButton("Back", self)
    backBtn.setObjectName("back")
    buttonsLayout.addWidget(backBtn, alignment=Qt.AlignmentFlag.AlignCenter)
    startPageBtn = QPushButton("Go to the start page", self)
    startPageBtn.clicked.connect(lambda: controller.show_frame("StartPage"))
    buttonsLayout.addWidget(startPageBtn, alignment=Qt.AlignmentFlag.AlignCenter)
    buttonsLayout.addStretch()
    layout.addLayout(buttonsLayout, 8, 0, 1, 3)

    self.setLayout(layout)


class NbRegionsOfInterest(QWidget):
  def __init__(self, controller):
    super().__init__(controller.window)
    self.controller = controller
    self.preferredSize = (450, 300)

    def updateButtons():
      enabled = bool(nbwells.text())
      nextBtn.setEnabled(enabled)
      nextBtn.setToolTip("Values must be entered in all fields." if not enabled else None)
    self._updateButtons = updateButtons

    layout = QVBoxLayout()
    layout.addWidget(util.apply_style(QLabel("Prepare Config File", self), font=controller.title_font), alignment=Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(util.apply_style(QLabel("How many regions of interest / wells are there in your video?", self), font=QFont("Helvetica", 10)), alignment=Qt.AlignmentFlag.AlignCenter)
    nbwells = QLineEdit(controller.window)
    nbwells.setValidator(QIntValidator(nbwells))
    nbwells.validator().setBottom(0)
    nbwells.textChanged.connect(updateButtons)
    layout.addWidget(nbwells, alignment=Qt.AlignmentFlag.AlignCenter)

    buttonsLayout = QHBoxLayout()
    buttonsLayout.addStretch()
    backBtn = QPushButton("Back", self)
    backBtn.setObjectName("back")
    buttonsLayout.addWidget(backBtn, alignment=Qt.AlignmentFlag.AlignCenter)
    startPageBtn = QPushButton("Go to the start page", self)
    startPageBtn.clicked.connect(lambda: controller.show_frame("StartPage"))
    buttonsLayout.addWidget(startPageBtn, alignment=Qt.AlignmentFlag.AlignCenter)
    nextBtn = util.apply_style(QPushButton("Next", self), background_color=util.DEFAULT_BUTTON_COLOR)
    nextBtn.clicked.connect(lambda: controller.regionsOfInterest(controller, int(nbwells.text())))
    buttonsLayout.addWidget(nextBtn, alignment=Qt.AlignmentFlag.AlignCenter)
    buttonsLayout.addStretch()
    layout.addLayout(buttonsLayout)

    self.setLayout(layout)

  def showEvent(self, evt):
    self._updateButtons()


class HomegeneousWellsLayout(QWidget):
  def __init__(self, controller):
    super().__init__(controller.window)
    self.controller = controller

    layout = QVBoxLayout()
    layout.addWidget(util.apply_style(QLabel("Prepare Config File", self), font=controller.title_font), alignment=Qt.AlignmentFlag.AlignCenter)

    self._video = video = QLabel()
    video.setMinimumSize(1, 1)
    layout.addWidget(video, stretch=1)

    def updateButtons():
      enabled = bool(nbRowsOfWells.text() and nbWellsPerRows.text())
      for btn in (finishBtn, adjustBtn):
        btn.setEnabled(enabled)
        btn.setToolTip("Values must be entered in all fields." if not enabled else None)
    self._updateButtons = updateButtons

    self._frameSlider = frameSlider = util.SliderWithSpinbox(1, 0, 1, name="Frame")

    def frameChanged(frame):
      if self._cap is None:
        video.clear()
      else:
        self._cap.set(1, frame)
        ret, img = self._cap.read()
        util.setPixmapFromCv(img, video)
    frameSlider.valueChanged.connect(frameChanged)
    layout.addWidget(frameSlider, alignment=Qt.AlignmentFlag.AlignCenter)

    wellsSublayout = QHBoxLayout()
    wellsSublayout.addStretch(1)

    wellsSublayout.addWidget(util.apply_style(QLabel("How many rows of wells are there in your video?", self), font=QFont("Helvetica", 10)), alignment=Qt.AlignmentFlag.AlignCenter)
    nbRowsOfWells = QLineEdit(controller.window)
    nbRowsOfWells.setValidator(QIntValidator(nbRowsOfWells))
    nbRowsOfWells.validator().setBottom(1)
    nbRowsOfWells.textChanged.connect(updateButtons)
    wellsSublayout.addWidget(nbRowsOfWells, alignment=Qt.AlignmentFlag.AlignCenter)

    wellsSublayout.addWidget(util.apply_style(QLabel("How many wells are there per row on your video?", self), font=QFont("Helvetica", 10)), alignment=Qt.AlignmentFlag.AlignCenter)
    nbWellsPerRows = QLineEdit(controller.window)
    nbWellsPerRows.setValidator(QIntValidator(nbWellsPerRows))
    nbWellsPerRows.validator().setBottom(1)
    nbWellsPerRows.textChanged.connect(updateButtons)
    wellsSublayout.addWidget(nbWellsPerRows, alignment=Qt.AlignmentFlag.AlignCenter)
    wellsSublayout.addStretch(1)
    layout.addLayout(wellsSublayout)

    boutDetectCheckbox = QCheckBox("Detect bouts of movement")
    layout.addWidget(boutDetectCheckbox, alignment=Qt.AlignmentFlag.AlignCenter)

    finishBtn = util.apply_style(QPushButton("Use Method 1", self), background_color=util.DEFAULT_BUTTON_COLOR)
    finishBtn.clicked.connect(lambda: controller.homegeneousWellsLayout(controller, nbRowsOfWells.text(), nbWellsPerRows.text(), boutDetectCheckbox.isChecked()))
    layout.addWidget(finishBtn, alignment=Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(QLabel('Method 1 is usually best for "poor quality" video (poor contrast, changing background, etc...)', self), alignment=Qt.AlignmentFlag.AlignCenter)
    
    adjustBtn = util.apply_style(QPushButton("Use Method 2", self), background_color=util.DEFAULT_BUTTON_COLOR)
    adjustBtn.clicked.connect(lambda: controller.morePreciseFastScreen(controller, nbRowsOfWells.text(), nbWellsPerRows.text(), boutDetectCheckbox.isChecked()))
    layout.addWidget(adjustBtn, alignment=Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(QLabel('Method 2 will usually lead to more accurate results for "high quality" video (high contrast, strictly fixed background, no issues on borders, etc..).', self), alignment=Qt.AlignmentFlag.AlignCenter)
    
    layout.addWidget(QLabel('If you are unusure which method to use, it is highly recommended to simply try both.', self), alignment=Qt.AlignmentFlag.AlignCenter)
    
    # linkBtn1 = util.apply_style(QPushButton("Alternative", self), background_color=util.GOLD)
    # linkBtn1.clicked.connect(lambda: webbrowser.open_new("https://github.com/oliviermirat/ZebraZoom/blob/master/FastScreenTrackingGuidlines.md"))
    # layout.addWidget(linkBtn1, alignment=Qt.AlignmentFlag.AlignCenter)

    buttonsLayout = QHBoxLayout()
    buttonsLayout.addStretch()
    backBtn = QPushButton("Back", self)
    backBtn.setObjectName("back")
    buttonsLayout.addWidget(backBtn, alignment=Qt.AlignmentFlag.AlignCenter)
    startPageBtn = QPushButton("Go to the start page", self)
    startPageBtn.clicked.connect(lambda: controller.show_frame("StartPage"))
    buttonsLayout.addWidget(startPageBtn, alignment=Qt.AlignmentFlag.AlignCenter)
    buttonsLayout.addStretch()
    layout.addLayout(buttonsLayout)

    self.setLayout(layout)

  def showEvent(self, evt):
    if not evt.spontaneous():
      self._cap = zzVideoReading.VideoCapture(self.controller.videoToCreateConfigFileFor)
      self._frameSlider.setMaximum(self._cap.get(7) - 1)
      self._frameSlider.valueChanged.emit(self._frameSlider.value())
      self.layout().setAlignment(self._video, Qt.AlignmentFlag.AlignCenter)
      self._updateButtons()
    super().showEvent(evt)

  def hideEvent(self, evt):
    super().hideEvent(evt)
    if not evt.spontaneous():
      self._cap = None
      self._frameSlider.valueChanged.emit(self._frameSlider.value())
      self.layout().setAlignment(self._video, Qt.Alignment())


class CircularOrRectangularWells(QWidget):
  def __init__(self, controller):
    super().__init__(controller.window)
    self.controller = controller
    self._cap = None

    layout = QVBoxLayout()
    layout.addWidget(util.apply_style(QLabel("Prepare Config File", self), font=controller.title_font), alignment=Qt.AlignmentFlag.AlignCenter)

    self._video = video = QLabel()
    video.setMinimumSize(1, 1)
    layout.addWidget(video, stretch=1)

    def updateNextBtn():
      enabled = bool(nbRowsOfWells.text() and nbWellsPerRows.text() and nbanimals.text())
      nextBtn.setEnabled(enabled)
      nextBtn.setToolTip("Values must be entered in all fields." if not enabled else None)
    self._updateNextBtn = updateNextBtn

    self._frameSlider = frameSlider = util.SliderWithSpinbox(1, 0, 1, name="Frame")

    def frameChanged(frame):
      if self._cap is None:
        video.clear()
      else:
        self._cap.set(1, frame)
        ret, img = self._cap.read()
        util.setPixmapFromCv(img, video)
    frameSlider.valueChanged.connect(frameChanged)
    layout.addWidget(frameSlider, alignment=Qt.AlignmentFlag.AlignCenter)

    wellsSublayout = QHBoxLayout()
    wellsSublayout.addStretch(1)

    wellsSublayout.addWidget(util.apply_style(QLabel("How many rows of wells are there in your video?", self), font=QFont("Helvetica", 10)), alignment=Qt.AlignmentFlag.AlignCenter)
    nbRowsOfWells = QLineEdit(controller.window)
    nbRowsOfWells.setValidator(QIntValidator(nbRowsOfWells))
    nbRowsOfWells.validator().setBottom(1)
    nbRowsOfWells.textChanged.connect(updateNextBtn)
    wellsSublayout.addWidget(nbRowsOfWells, alignment=Qt.AlignmentFlag.AlignCenter)

    wellsSublayout.addWidget(util.apply_style(QLabel("How many wells are there per row on your video?", self), font=QFont("Helvetica", 10)), alignment=Qt.AlignmentFlag.AlignCenter)
    nbWellsPerRows = QLineEdit(controller.window)
    nbWellsPerRows.setValidator(QIntValidator(nbWellsPerRows))
    nbWellsPerRows.validator().setBottom(1)
    nbWellsPerRows.textChanged.connect(updateNextBtn)
    wellsSublayout.addWidget(nbWellsPerRows, alignment=Qt.AlignmentFlag.AlignCenter)
    wellsSublayout.addStretch(1)
    layout.addLayout(wellsSublayout)

    animalsSublayout = QHBoxLayout()
    animalsSublayout.addStretch(1)
    animalsSublayout.addWidget(util.apply_style(QLabel("What's the number of animals per well in your video?", self), font=QFont("Helvetica", 10)), alignment=Qt.AlignmentFlag.AlignCenter)
    nbanimals = QLineEdit(controller.window)
    nbanimals.setValidator(QIntValidator(nbanimals))
    nbanimals.validator().setBottom(1)
    nbanimals.textChanged.connect(updateNextBtn)
    animalsSublayout.addWidget(nbanimals, alignment=Qt.AlignmentFlag.AlignCenter)
    animalsSublayout.addWidget(util.apply_style(QLabel("ZebraZoom only supports videos which have the same number of animals in each well.", self), font=QFont("Helvetica", 10)), alignment=Qt.AlignmentFlag.AlignCenter)
    animalsSublayout.addStretch(1)
    layout.addLayout(animalsSublayout)

    buttonsLayout = QHBoxLayout()
    buttonsLayout.addStretch()
    backBtn = QPushButton("Back", self)
    backBtn.setObjectName("back")
    buttonsLayout.addWidget(backBtn, alignment=Qt.AlignmentFlag.AlignCenter)
    startPageBtn = QPushButton("Go to the start page", self)
    startPageBtn.clicked.connect(lambda: controller.show_frame("StartPage"))
    buttonsLayout.addWidget(startPageBtn, alignment=Qt.AlignmentFlag.AlignCenter)
    nextBtn = util.apply_style(QPushButton("Next", self), background_color=util.DEFAULT_BUTTON_COLOR)
    nextBtn.clicked.connect(lambda: controller.circularOrRectangularWells(controller, nbRowsOfWells.text(), nbWellsPerRows.text(), nbanimals.text()))
    buttonsLayout.addWidget(nextBtn, alignment=Qt.AlignmentFlag.AlignCenter)
    buttonsLayout.addStretch()
    layout.addLayout(buttonsLayout)

    self.setLayout(layout)

  def showEvent(self, evt):
    if not evt.spontaneous():
      self._cap = zzVideoReading.VideoCapture(self.controller.videoToCreateConfigFileFor)
      self._frameSlider.setMaximum(self._cap.get(7) - 1)
      self._frameSlider.valueChanged.emit(self._frameSlider.value())
      self.layout().setAlignment(self._video, Qt.AlignmentFlag.AlignCenter)
      self._updateNextBtn()
    super().showEvent(evt)

  def hideEvent(self, evt):
    super().hideEvent(evt)
    if not evt.spontaneous():
      self._cap = None
      self._frameSlider.valueChanged.emit(self._frameSlider.value())
      self.layout().setAlignment(self._video, Qt.Alignment())


class ChooseCircularWellsLeft(QWidget):
  def __init__(self, controller):
    super().__init__(controller.window)
    self.controller = controller

    layout = QVBoxLayout()
    layout.addWidget(util.apply_style(QLabel("Prepare Config File", self), font=controller.title_font), alignment=Qt.AlignmentFlag.AlignCenter)

    button = util.apply_style(QPushButton("Click on the left inner border of the top left well", self), background_color=util.DEFAULT_BUTTON_COLOR)
    button.clicked.connect(lambda: controller.chooseCircularWellsLeft(controller))
    layout.addWidget(button, alignment=Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(util.apply_style(QLabel("Example:", self), font=QFont("Helvetica", 10)), alignment=Qt.AlignmentFlag.AlignCenter)
    cur_dir_path = os.path.dirname(os.path.realpath(__file__))
    image = QLabel(self)
    image.setPixmap(QPixmap(os.path.join(cur_dir_path, 'leftborder.png')))
    layout.addWidget(image, alignment=Qt.AlignmentFlag.AlignCenter)

    buttonsLayout = QHBoxLayout()
    buttonsLayout.addStretch()
    backBtn = QPushButton("Back", self)
    backBtn.setObjectName("back")
    buttonsLayout.addWidget(backBtn, alignment=Qt.AlignmentFlag.AlignCenter)
    startPageBtn = QPushButton("Go to the start page", self)
    startPageBtn.clicked.connect(lambda: controller.show_frame("StartPage"))
    buttonsLayout.addWidget(startPageBtn, alignment=Qt.AlignmentFlag.AlignCenter)
    buttonsLayout.addStretch()
    layout.addLayout(buttonsLayout)

    self.setLayout(layout)


class ChooseCircularWellsRight(QWidget):
  def __init__(self, controller):
    super().__init__(controller.window)
    self.controller = controller

    layout = QVBoxLayout()
    layout.addWidget(util.apply_style(QLabel("Prepare Config File", self), font=controller.title_font), alignment=Qt.AlignmentFlag.AlignCenter)

    button = util.apply_style(QPushButton("Click on the right inner border of the top left well", self), background_color=util.DEFAULT_BUTTON_COLOR)
    button.clicked.connect(lambda: controller.chooseCircularWellsRight(controller))
    layout.addWidget(button, alignment=Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(util.apply_style(QLabel("Example:", self), font=QFont("Helvetica", 10)), alignment=Qt.AlignmentFlag.AlignCenter)
    cur_dir_path = os.path.dirname(os.path.realpath(__file__))
    image = QLabel(self)
    image.setPixmap(QPixmap(os.path.join(cur_dir_path, 'rightborder.png')))
    layout.addWidget(image, alignment=Qt.AlignmentFlag.AlignCenter)

    buttonsLayout = QHBoxLayout()
    buttonsLayout.addStretch()
    backBtn = QPushButton("Back", self)
    backBtn.setObjectName("back")
    buttonsLayout.addWidget(backBtn, alignment=Qt.AlignmentFlag.AlignCenter)
    startPageBtn = QPushButton("Go to the start page", self)
    startPageBtn.clicked.connect(lambda: controller.show_frame("StartPage"))
    buttonsLayout.addWidget(startPageBtn, alignment=Qt.AlignmentFlag.AlignCenter)
    buttonsLayout.addStretch()
    layout.addLayout(buttonsLayout)

    self.setLayout(layout)


class NumberOfAnimals(QWidget):
  def __init__(self, controller):
    super().__init__(controller.window)
    self.controller = controller
    self.preferredSize = (750, 500)

    layout = QVBoxLayout()
    layout.addWidget(util.apply_style(QLabel("Prepare Config File", self), font=controller.title_font), alignment=Qt.AlignmentFlag.AlignCenter)

    def updateButtons():
      if not bool(nbanimals.text()):
        nextBtn.setEnabled(False)
        nextBtn.setToolTip("Values must be entered in all fields.")
      elif int(nbanimals.text()) % controller.configFile["nbWells"]:
        nextBtn.setEnabled(False)
        nextBtn.setToolTip(f"Number of animals must be divisible by the number of regions of interest/wells ({controller.configFile['nbWells']}).")
      else:
        nextBtn.setEnabled(True)
        nextBtn.setToolTip(None)

    self._updateButtons = updateButtons

    layout.addWidget(util.apply_style(QLabel("What's the total number of animals in your video?", self), font=QFont("Helvetica", 10)), alignment=Qt.AlignmentFlag.AlignCenter)
    nbanimals = QLineEdit(controller.window)
    nbanimals.setValidator(QIntValidator(nbanimals))
    nbanimals.validator().setBottom(0)
    nbanimals.textChanged.connect(updateButtons)
    layout.addWidget(nbanimals, alignment=Qt.AlignmentFlag.AlignCenter)

    layout.addWidget(util.apply_style(QLabel("Are all of those animals ALWAYS visible throughout the video?", self), font=QFont("Helvetica", 10)), alignment=Qt.AlignmentFlag.AlignCenter)
    yesRadioButton = QRadioButton("Yes", self)
    yesRadioButton.setChecked(True)
    layout.addWidget(yesRadioButton, alignment=Qt.AlignmentFlag.AlignCenter)
    noRadioButton = QRadioButton("No", self)
    layout.addWidget(noRadioButton, alignment=Qt.AlignmentFlag.AlignCenter)

    forceBlobMethodForHeadTrackingCheckbox = QCheckBox("Blob method for head tracking of fish", self)
    layout.addWidget(forceBlobMethodForHeadTrackingCheckbox, alignment=Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(util.apply_style(QLabel("Only click the box above if you tried the tracking without this option and the head tracking was suboptimal (an eye was detected instead of the head for example).", self), font=QFont("Helvetica", 10)), alignment=Qt.AlignmentFlag.AlignCenter)

    buttonsLayout = QHBoxLayout()
    buttonsLayout.addStretch()
    backBtn = QPushButton("Back", self)
    backBtn.setObjectName("back")
    buttonsLayout.addWidget(backBtn, alignment=Qt.AlignmentFlag.AlignCenter)
    startPageBtn = QPushButton("Go to the start page", self)
    startPageBtn.clicked.connect(lambda: controller.show_frame("StartPage"))
    buttonsLayout.addWidget(startPageBtn, alignment=Qt.AlignmentFlag.AlignCenter)
    nextBtn = util.apply_style(QPushButton("Next", self), background_color=util.DEFAULT_BUTTON_COLOR)
    nextBtn.clicked.connect(lambda: numberOfAnimals(nbanimals.text(), yesRadioButton.isChecked(), forceBlobMethodForHeadTrackingCheckbox.isChecked(), 0, False, False, False))
    buttonsLayout.addWidget(nextBtn, alignment=Qt.AlignmentFlag.AlignCenter)
    buttonsLayout.addStretch()
    layout.addLayout(buttonsLayout)

    self.setLayout(layout)

  def showEvent(self, evt):
    self._updateButtons()


class NumberOfAnimals2(QWidget):
  def __init__(self, controller):
    super().__init__(controller.window)
    self.controller = controller
    self.preferredSize = (1152, 768)

    layout = QGridLayout()
    layout.addWidget(util.apply_style(QLabel("Prepare Config File", self), font=controller.title_font), 0, 0, 1, 2, Qt.AlignmentFlag.AlignCenter)

    def updateButtons():
      if nbanimals.isVisible() and not bool(nbanimals.text()):
        nextBtn.setEnabled(False)
        nextBtn.setToolTip("Values must be entered in all fields.")
      elif nbanimals.isVisible() and int(nbanimals.text()) % controller.configFile["nbWells"]:
        nextBtn.setEnabled(False)
        nextBtn.setToolTip(f"Number of animals must be divisible by the number of regions of interest/wells ({controller.configFile['nbWells']}).")
      else:
        nextBtn.setEnabled(True)
        nextBtn.setToolTip(None)
    self._updateButtons = updateButtons

    self._nbanimalsLabel = util.apply_style(QLabel("What's the total number of animals in your video?", self), font_size='16px')
    layout.addWidget(self._nbanimalsLabel, 1, 0, 1, 2, Qt.AlignmentFlag.AlignCenter)
    self._nbanimals = nbanimals = QLineEdit(controller.window)
    nbanimals.setValidator(QIntValidator(nbanimals))
    nbanimals.validator().setBottom(0)
    nbanimals.textChanged.connect(updateButtons)
    layout.addWidget(nbanimals, 2, 0, 1, 2, Qt.AlignmentFlag.AlignCenter)

    layout.addWidget(util.apply_style(QLabel("Tracking: Choose an option below:", self), font_size='16px'), 3, 1, Qt.AlignmentFlag.AlignCenter)
    btnGroup5 = QButtonGroup(self)
    recommendedTrackingMethodRadioButton = QRadioButton("Old legacy Algorithm:\nNot recommended in most cases", self)
    btnGroup5.addButton(recommendedTrackingMethodRadioButton, id=0)
    layout.addWidget(recommendedTrackingMethodRadioButton, 4, 1, Qt.AlignmentFlag.AlignLeft)
    defaultTrackingMethodRadioButton = QRadioButton("Default Algorithm", self)
    btnGroup5.addButton(defaultTrackingMethodRadioButton, id=1)
    defaultTrackingMethodRadioButton.setChecked(True)
    layout.addWidget(defaultTrackingMethodRadioButton, 5, 1, Qt.AlignmentFlag.AlignLeft)
    alternativeTrackingMethodRadioButton = QRadioButton("Fastest Algorithm:\nVery fast, but potentially still a little unstable in some situations", self)
    btnGroup5.addButton(alternativeTrackingMethodRadioButton, id=2)
    layout.addWidget(alternativeTrackingMethodRadioButton, 6, 1, Qt.AlignmentFlag.AlignLeft)
    # layout.addWidget(util.apply_style(QLabel("The alternative method can also work better for animals of different sizes.", self), font=QFont("Helvetica", 10)), 6, 1, Qt.AlignmentFlag.AlignCenter)

    layout.addWidget(util.apply_style(QLabel("Do you want bouts of movement to be detected?", self), font_size='16px'), 3, 0, Qt.AlignmentFlag.AlignCenter)
    yesNoLayout2 = QHBoxLayout()
    yesNoLayout2.addStretch()
    btnGroup2 = QButtonGroup(self)
    slowBoutDetectionRadioButton = QRadioButton("Yes, with slow but more accurate bout detection", self)
    btnGroup2.addButton(slowBoutDetectionRadioButton, id=1)
    yesNoLayout2.addWidget(slowBoutDetectionRadioButton, alignment=Qt.AlignmentFlag.AlignCenter)
    fastBoutDetectionRadioButton = QRadioButton("Yes, with fast but less accurate bout detection\nnot recommended in most cases", self)
    btnGroup2.addButton(fastBoutDetectionRadioButton, id=2)
    yesNoLayout2.addWidget(fastBoutDetectionRadioButton, alignment=Qt.AlignmentFlag.AlignCenter)
    noBoutsRadioButton = QRadioButton("No", self)
    btnGroup2.addButton(noBoutsRadioButton, id=0)
    yesNoLayout2.addWidget(noBoutsRadioButton, alignment=Qt.AlignmentFlag.AlignCenter)
    noBoutsRadioButton.setChecked(True)
    yesNoLayout2.addStretch()
    layout.addLayout(yesNoLayout2, 4, 0, Qt.AlignmentFlag.AlignCenter)

    advancedOptionsLayout = QGridLayout()
    advancedOptionsLayout.addWidget(util.apply_style(QLabel("Do you want bends and associated paramaters to be calculated?", self), font_size='16px'), 0, 1, Qt.AlignmentFlag.AlignCenter)
    advancedOptionsLayout.addWidget(QLabel("Bends are the local minimum and maximum of the tail angle.", self), 1, 1, Qt.AlignmentFlag.AlignCenter)
    advancedOptionsLayout.addWidget(QLabel("Bends are used to calculate parameters such as tail beat frequency.", self), 2, 1, Qt.AlignmentFlag.AlignCenter)

    linkBtn1 = QPushButton("You may need to further adjust these parameters afterwards: see documentation.", self)

    linkBtn1.clicked.connect(lambda: webbrowser.open_new("https://zebrazoom.org/documentation/docs/configurationFile/advanced/angleSmoothBoutsAndBendsDetection"))
    advancedOptionsLayout.addWidget(linkBtn1, 3, 1, Qt.AlignmentFlag.AlignCenter)
    yesNoLayout3 = QHBoxLayout()
    yesNoLayout3.addStretch()

    btnGroup3 = QButtonGroup(self)
    yesBendsRadioButton = QRadioButton("Yes", self)
    btnGroup3.addButton(yesBendsRadioButton)
    yesBendsRadioButton.setChecked(True)
    yesNoLayout3.addWidget(yesBendsRadioButton, alignment=Qt.AlignmentFlag.AlignCenter)
    noBendsRadioButton = QRadioButton("No", self)
    btnGroup3.addButton(noBendsRadioButton)
    yesNoLayout3.addWidget(noBendsRadioButton, alignment=Qt.AlignmentFlag.AlignCenter)
    yesNoLayout3.addStretch()
    advancedOptionsLayout.addLayout(yesNoLayout3, 4, 1, Qt.AlignmentFlag.AlignCenter)

    advancedOptionsLayout.addWidget(util.apply_style(QLabel("Tail tracking: Choose an option below:", self), font_size='16px'), 0, 0, Qt.AlignmentFlag.AlignCenter)
    btnGroup4 = QButtonGroup(self)
    recommendedMethodRadioButton = QRadioButton("Recommended Method: Fast Tracking but tail tip might be detected too soon along the tail", self)
    btnGroup4.addButton(recommendedMethodRadioButton)
    recommendedMethodRadioButton.setChecked(True)
    advancedOptionsLayout.addWidget(recommendedMethodRadioButton, 1, 0, Qt.AlignmentFlag.AlignCenter)
    alternativeMethodRadioButton = QRadioButton("Alternative Method: Slower Tracker but tail tip MIGHT be detected more acurately", self)
    btnGroup4.addButton(alternativeMethodRadioButton)
    advancedOptionsLayout.addWidget(alternativeMethodRadioButton, 2, 0, Qt.AlignmentFlag.AlignCenter)
    label = util.apply_style(QLabel("Once your configuration is created, you can switch from one method to the other "
                                    "by changing the value of the parameter recalculateForegroundImageBasedOnBodyArea "
                                    "in your config file between 0 and 1.", self), font=QFont("Helvetica", 10))
    label.setWordWrap(True)
    advancedOptionsLayout.addWidget(label, 3, 0, 2, 1)

    advancedOptionsLayout.addWidget(util.apply_style(QLabel("Are all animals ALWAYS visible throughout the video?", self), font_size='16px'), 5, 1, Qt.AlignmentFlag.AlignCenter)
    yesNoLayout1 = QHBoxLayout()
    yesNoLayout1.addStretch()
    btnGroup1 = QButtonGroup(self)
    yesRadioButton = QRadioButton("Yes", self)
    btnGroup1.addButton(yesRadioButton)
    yesRadioButton.setChecked(True)
    yesNoLayout1.addWidget(yesRadioButton, alignment=Qt.AlignmentFlag.AlignCenter)
    noRadioButton = QRadioButton("No", self)
    btnGroup1.addButton(noRadioButton)
    yesNoLayout1.addWidget(noRadioButton, alignment=Qt.AlignmentFlag.AlignCenter)
    yesNoLayout1.addStretch()
    advancedOptionsLayout.addLayout(yesNoLayout1, 7, 1, Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(util.Expander(self, "Show advanced options", advancedOptionsLayout), 8, 0, 1, 2)

    buttonsLayout = QHBoxLayout()
    buttonsLayout.addStretch()
    backBtn = QPushButton("Back", self)
    backBtn.setObjectName("back")
    buttonsLayout.addWidget(backBtn, alignment=Qt.AlignmentFlag.AlignCenter)
    startPageBtn = QPushButton("Go to the start page", self)
    startPageBtn.clicked.connect(lambda: controller.show_frame("StartPage"))
    buttonsLayout.addWidget(startPageBtn, alignment=Qt.AlignmentFlag.AlignCenter)
    nextBtn = util.apply_style(QPushButton("Ok, next step", self), background_color=util.DEFAULT_BUTTON_COLOR)
    nextBtn.clicked.connect(lambda: numberOfAnimals(nbanimals.text() if nbanimals.isVisible() else None, yesRadioButton.isChecked(), False, btnGroup2.checkedId(), btnGroup5.checkedId(), yesBendsRadioButton.isChecked(), recommendedMethodRadioButton.isChecked()))
    buttonsLayout.addWidget(nextBtn, alignment=Qt.AlignmentFlag.AlignCenter)
    buttonsLayout.addStretch()
    layout.addLayout(buttonsLayout, 9, 0, 1, 2)

    self.setLayout(layout)

  def showEvent(self, evt):
    self._nbanimals.setVisible(self.controller.shape not in ('groupSameSizeAndShapeEquallySpacedWells', 'circular', 'rectangular'))
    self._nbanimalsLabel.setVisible(self.controller.shape not in ('groupSameSizeAndShapeEquallySpacedWells', 'circular', 'rectangular'))
    self._updateButtons()
    super().showEvent(evt)


class NumberOfAnimalsCenterOfMass(QWidget):
  def __init__(self, controller):
    super().__init__(controller.window)
    self.controller = controller
    self.preferredSize = (1152, 768)

    layout = QVBoxLayout()
    layout.addWidget(util.apply_style(QLabel("Prepare Config File", self), font=controller.title_font), alignment=Qt.AlignmentFlag.AlignCenter)

    def updateButtons():
      if nbanimals.isVisible() and not bool(nbanimals.text()):
        enabled = False
        tooltip = "Values must be entered in all fields."
      elif nbanimals.isVisible() and int(nbanimals.text()) % controller.configFile["nbWells"]:
        enabled = False
        tooltip = f"Number of animals must be divisible by the number of regions of interest/wells ({controller.configFile['nbWells']})."
      else:
        enabled = True
        tooltip = None
      for btn in (method1Btn, method2Btn, manualBtn):
        btn.setEnabled(enabled)
        btn.setToolTip(tooltip)
    self._updateButtons = updateButtons

    self._nbanimalsLabel = util.apply_style(QLabel("What's the total number of animals in your video?", self), font=QFont("Helvetica", 10))
    layout.addWidget(self._nbanimalsLabel, alignment=Qt.AlignmentFlag.AlignCenter)
    self._nbanimals = nbanimals = QLineEdit(controller.window)
    nbanimals.setValidator(QIntValidator(nbanimals))
    nbanimals.validator().setBottom(0)
    nbanimals.textChanged.connect(updateButtons)
    layout.addWidget(nbanimals, alignment=Qt.AlignmentFlag.AlignCenter)

    layout.addWidget(util.apply_style(QLabel("Are all of those animals ALWAYS visible throughout the video?", self), font=QFont("Helvetica", 10)), alignment=Qt.AlignmentFlag.AlignCenter)
    yesRadioButton = QRadioButton("Yes", self)
    yesRadioButton.setChecked(True)
    layout.addWidget(yesRadioButton, alignment=Qt.AlignmentFlag.AlignCenter)
    noRadioButton = QRadioButton("No", self)
    layout.addWidget(noRadioButton, alignment=Qt.AlignmentFlag.AlignCenter)

    method1Btn = QPushButton("Automatic Parameters Setting, Method 1: Slower tracking but often more accurate", self)
    method1Btn.clicked.connect(lambda: numberOfAnimals(nbanimals.text() if nbanimals.isVisible() else None, yesRadioButton.isChecked(), False, 0, True, False, True))
    layout.addWidget(method1Btn, alignment=Qt.AlignmentFlag.AlignCenter)
    method2Btn = QPushButton("Automatic Parameters Setting, Method 2: Faster tracking but often less accurate", self)
    method2Btn.clicked.connect(lambda: numberOfAnimals(nbanimals.text() if nbanimals.isVisible() else None, yesRadioButton.isChecked(), False, 0, True, False, False))
    layout.addWidget(method2Btn, alignment=Qt.AlignmentFlag.AlignCenter)
    manualBtn = QPushButton("Manual Parameters Setting: More control over the choice of parameters", self)
    manualBtn.clicked.connect(lambda: numberOfAnimals(nbanimals.text() if nbanimals.isVisible() else None, yesRadioButton.isChecked(), False, 0, False, False, False))
    layout.addWidget(manualBtn, alignment=Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(util.apply_style(QLabel("Try the 'Automatic Parameters Setting, Method 1' first. If it doesn't work, try the other methods.", self), font=QFont("Helvetica", 10)), alignment=Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(util.apply_style(QLabel("The 'Manual Parameter Settings' makes setting parameter slightly more challenging but offers more control over the choice of parameters.", self), font=QFont("Helvetica", 10)), alignment=Qt.AlignmentFlag.AlignCenter)

    buttonsLayout = QHBoxLayout()
    buttonsLayout.addStretch()
    backBtn = QPushButton("Back", self)
    backBtn.setObjectName("back")
    buttonsLayout.addWidget(backBtn, alignment=Qt.AlignmentFlag.AlignCenter)
    startPageBtn = QPushButton("Go to the start page", self)
    startPageBtn.clicked.connect(lambda: controller.show_frame("StartPage"))
    buttonsLayout.addWidget(startPageBtn, alignment=Qt.AlignmentFlag.AlignCenter)
    buttonsLayout.addStretch()
    layout.addLayout(buttonsLayout)

    self.setLayout(layout)

  def showEvent(self, evt):
    self._nbanimals.setVisible(self.controller.shape not in ('groupSameSizeAndShapeEquallySpacedWells', 'circular', 'rectangular'))
    self._nbanimalsLabel.setVisible(self.controller.shape not in ('groupSameSizeAndShapeEquallySpacedWells', 'circular', 'rectangular'))
    self._updateButtons()
    super().showEvent(evt)


class IdentifyHeadCenter(QWidget):
  def __init__(self, controller):
    super().__init__(controller.window)
    self.controller = controller

    layout = QVBoxLayout()
    layout.addWidget(util.apply_style(QLabel("Prepare Config File", self), font=controller.title_font), alignment=Qt.AlignmentFlag.AlignCenter)

    button = util.apply_style(QPushButton("Click on the center of the head of a zebrafish", self), background_color=util.DEFAULT_BUTTON_COLOR)
    button.clicked.connect(lambda: controller.chooseHeadCenter(controller))
    layout.addWidget(button, alignment=Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(util.apply_style(QLabel("Example:", self), font=QFont("Helvetica", 10)), alignment=Qt.AlignmentFlag.AlignCenter)
    cur_dir_path = os.path.dirname(os.path.realpath(__file__))
    image = QLabel(self)
    image.setPixmap(QPixmap(os.path.join(cur_dir_path, 'blobCenter.png')))
    layout.addWidget(image, alignment=Qt.AlignmentFlag.AlignCenter)

    buttonsLayout = QHBoxLayout()
    buttonsLayout.addStretch()
    backBtn = QPushButton("Back", self)
    backBtn.setObjectName("back")
    buttonsLayout.addWidget(backBtn, alignment=Qt.AlignmentFlag.AlignCenter)
    startPageBtn = QPushButton("Go to the start page", self)
    startPageBtn.clicked.connect(lambda: controller.show_frame("StartPage"))
    buttonsLayout.addWidget(startPageBtn, alignment=Qt.AlignmentFlag.AlignCenter)
    buttonsLayout.addStretch()
    layout.addLayout(buttonsLayout)

    self.setLayout(layout)


class IdentifyBodyExtremity(QWidget):
  def __init__(self, controller):
    super().__init__(controller.window)
    self.controller = controller

    layout = QVBoxLayout()
    layout.addWidget(util.apply_style(QLabel("Prepare Config File", self), font=controller.title_font), alignment=Qt.AlignmentFlag.AlignCenter)

    button = util.apply_style(QPushButton("Click on the tip of the tail of the same zebrafish.", self), background_color=util.DEFAULT_BUTTON_COLOR)
    button.clicked.connect(lambda: controller.chooseBodyExtremity(controller))
    layout.addWidget(button, alignment=Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(util.apply_style(QLabel("Example:", self), font=QFont("Helvetica", 10)), alignment=Qt.AlignmentFlag.AlignCenter)
    cur_dir_path = os.path.dirname(os.path.realpath(__file__))
    image = QLabel(self)
    image.setPixmap(QPixmap(os.path.join(cur_dir_path, 'blobExtremity.png')))
    layout.addWidget(image, alignment=Qt.AlignmentFlag.AlignCenter)

    buttonsLayout = QHBoxLayout()
    buttonsLayout.addStretch()
    backBtn = QPushButton("Back", self)
    backBtn.setObjectName("back")
    buttonsLayout.addWidget(backBtn, alignment=Qt.AlignmentFlag.AlignCenter)
    startPageBtn = QPushButton("Go to the start page", self)
    startPageBtn.clicked.connect(lambda: controller.show_frame("StartPage"))
    buttonsLayout.addWidget(startPageBtn, alignment=Qt.AlignmentFlag.AlignCenter)
    buttonsLayout.addStretch()
    layout.addLayout(buttonsLayout)

    self.setLayout(layout)


class GoToAdvanceSettings(QWidget):
  def __init__(self, controller):
    super().__init__(controller.window)
    self.controller = controller
    self.preferredSize = (450, 300)

    layout = QVBoxLayout()
    layout.addWidget(util.apply_style(QLabel("Prepare Config File", self), font=controller.title_font), alignment=Qt.AlignmentFlag.AlignCenter)

    layout.addWidget(util.apply_style(QLabel("Do you want to detect bouts movements and/or further adjust tracking parameters?", self), font=QFont("Helvetica", 12)), alignment=Qt.AlignmentFlag.AlignCenter)
    yesRadioButton = QRadioButton("Yes", self)
    yesRadioButton.setChecked(True)
    layout.addWidget(yesRadioButton, alignment=Qt.AlignmentFlag.AlignCenter)
    noRadioButton = QRadioButton("No", self)
    layout.addWidget(noRadioButton, alignment=Qt.AlignmentFlag.AlignCenter)

    buttonsLayout = QHBoxLayout()
    buttonsLayout.addStretch()
    backBtn = QPushButton("Back", self)
    backBtn.setObjectName("back")
    buttonsLayout.addWidget(backBtn, alignment=Qt.AlignmentFlag.AlignCenter)
    startPageBtn = QPushButton("Go to the start page", self)
    startPageBtn.clicked.connect(lambda: controller.show_frame("StartPage"))
    buttonsLayout.addWidget(startPageBtn, alignment=Qt.AlignmentFlag.AlignCenter)
    nextBtn = util.apply_style(QPushButton("Next", self), background_color=util.DEFAULT_BUTTON_COLOR)
    nextBtn.clicked.connect(lambda: controller.goToAdvanceSettings(controller, yesRadioButton.isChecked(), noRadioButton.isChecked()))
    buttonsLayout.addWidget(nextBtn, alignment=Qt.AlignmentFlag.AlignCenter)
    buttonsLayout.addStretch()
    layout.addLayout(buttonsLayout)

    self.setLayout(layout)


class FinishConfig(QWidget):
  def __init__(self, controller):
    super().__init__(controller.window)
    self.controller = controller

    layout = QVBoxLayout()
    layout.addStretch()

    def updateSaveBtn():
      enabled = not speedUpAnalysisCheckbox.isChecked() or bool(videoFPS.text() and videoPixelSize.text())
      saveBtn.setEnabled(enabled)
      if not enabled:
        saveBtn.setToolTip("Video FPS and pixel size have to be filled in if speed up analysis option is checked.")
      else:
        saveBtn.setToolTip(None)

    self._fasterTrackingCheckbox = QCheckBox("Make tracking run faster")
    def fasterTrackingToggled(checked):
      if checked:
        controller.configFile["fasterMultiprocessing"] = 2
        controller.configFile["detectMovementWithRawVideoInsideTracking"] = 1
      else:
        if "fasterMultiprocessing" in controller.configFile:
          del controller.configFile["fasterMultiprocessing"]
        if "detectMovementWithRawVideoInsideTracking" in controller.configFile:
          del controller.configFile["detectMovementWithRawVideoInsideTracking"]
    self._fasterTrackingCheckbox.toggled.connect(fasterTrackingToggled)
    layout.addWidget(self._fasterTrackingCheckbox, alignment=Qt.AlignmentFlag.AlignCenter)

    self._changingBackgroundCheckbox = QCheckBox("Check this box if the background of your video changes over time")
    def changingBackgroundToggled(checked):
      if checked:
        controller.configFile["updateBackgroundAtInterval"] = 1
      else:
        if "updateBackgroundAtInterval" in controller.configFile:
          del controller.configFile["updateBackgroundAtInterval"]
      backgroundOptionsWidget.setVisible(checked)
    self._changingBackgroundCheckbox.toggled.connect(changingBackgroundToggled)
    layout.addWidget(self._changingBackgroundCheckbox, alignment=Qt.AlignmentFlag.AlignCenter)

    backgroundOptionsLayout = QVBoxLayout()
    useFirstFrameAsBackgroundCheckbox = QCheckBox('Use the first frame as background')
    def useFirstFrameAsBackground(checked):
      if checked:
        controller.configFile["useFirstFrameAsBackground"] = 1
      else:
        if 'useFirstFrameAsBackground' in controller.configFile:
          del controller.configFile["useFirstFrameAsBackground"]
    useFirstFrameAsBackgroundCheckbox.toggled.connect(useFirstFrameAsBackground)
    backgroundOptionsLayout.addWidget(useFirstFrameAsBackgroundCheckbox, alignment=Qt.AlignmentFlag.AlignCenter)
    lastFrameForInitialBackDetect = QLineEdit()
    lastFrameForInitialBackDetect.setValidator(QIntValidator(lastFrameForInitialBackDetect))
    lastFrameForInitialBackDetect.validator().setBottom(1)

    def updateLastFrameForInitialBackDetect(text):
      if text:
        controller.configFile["lastFrameForInitialBackDetect"] = int(text)
      else:
        if 'lastFrameForInitialBackDetect' in controller.configFile:
          del controller.configFile['lastFrameForInitialBackDetect']
    lastFrameForInitialBackDetect.textChanged.connect(updateLastFrameForInitialBackDetect)
    lastFrameForInitialBackDetectLayout = QFormLayout()
    lastFrameForInitialBackDetectLayout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.FieldsStayAtSizeHint)
    lastFrameForInitialBackDetectLayout.addRow('Calculate background using the first frame and frame:', lastFrameForInitialBackDetect)
    backgroundOptionsLayout.addLayout(lastFrameForInitialBackDetectLayout)
    backgroundOptionsWidget = QWidget()
    backgroundOptionsWidget.setVisible(False)
    backgroundOptionsWidget.setLayout(backgroundOptionsLayout)
    layout.addWidget(backgroundOptionsWidget, alignment=Qt.AlignmentFlag.AlignCenter)

    self._calculateCurvatureCheckbox = QCheckBox("Calculate curvature")
    def calculateCurvatureToggled(checked):
      if checked:
        controller.configFile["perBoutOutput"] = 1
        nbTailPointsWidget.setVisible(True)
      else:
        if "perBoutOutput" in controller.configFile:
          del controller.configFile["perBoutOutput"]
        nbTailPointsWidget.setVisible(False)
    self._calculateCurvatureCheckbox.toggled.connect(calculateCurvatureToggled)
    layout.addWidget(self._calculateCurvatureCheckbox, alignment=Qt.AlignmentFlag.AlignCenter)
    nbTailPointsLayout = QFormLayout()
    nbTailPointsLayout.setFormAlignment(Qt.AlignmentFlag.AlignCenter)
    nbTailPointsLayout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.FieldsStayAtSizeHint)
    self._nbTailPoints = QLineEdit()
    self._nbTailPoints.setValidator(QIntValidator(self._nbTailPoints))
    self._nbTailPoints.validator().setBottom(1)
    self._nbTailPoints.setPlaceholderText('10')
    def nbTailPointsChanged(text):
      if not text:
        if 'nbTailPoints' in controller.configFile:
          del controller.configFile['nbTailPoints']
      else:
        controller.configFile['nbTailPoints'] = int(text)
    self._nbTailPoints.textChanged.connect(nbTailPointsChanged)
    nbTailPointsLayout.addRow('Number of tail points:', self._nbTailPoints)
    nbTailPointsWidget = QWidget()
    nbTailPointsWidget.setLayout(nbTailPointsLayout)
    nbTailPointsWidget.setVisible(False)
    layout.addWidget(nbTailPointsWidget, alignment=Qt.AlignmentFlag.AlignCenter)

    self._calculateTailAngleHeatmapCheckbox = QCheckBox("Calculate tail angle heatmap")
    def calculateTailAngleHeatmapToggled(checked):
      if checked:
        controller.configFile["tailAnglesHeatMap"] = 1
      else:
        if "tailAnglesHeatMap" in controller.configFile:
          del controller.configFile["tailAnglesHeatMap"]
    self._calculateTailAngleHeatmapCheckbox.toggled.connect(calculateTailAngleHeatmapToggled)
    layout.addWidget(self._calculateTailAngleHeatmapCheckbox, alignment=Qt.AlignmentFlag.AlignCenter)

    def speedUpAnalysisToggled(checked):
      helpBtn.setVisible(checked)
      if not checked:
        if "createPandasDataFrameOfParameters" in controller.configFile:
          del controller.configFile["createPandasDataFrameOfParameters"]
      else:
        controller.configFile["createPandasDataFrameOfParameters"] = 1
    speedUpAnalysisCheckbox = QCheckBox("Pre-calculate kinematic parameters during tracking", self)
    speedUpAnalysisCheckbox.toggled.connect(speedUpAnalysisToggled)
    speedUpAnalysisCheckbox.toggled.connect(updateSaveBtn)
    layout.addWidget(speedUpAnalysisCheckbox, alignment=Qt.AlignmentFlag.AlignCenter)
    helpBtn = QPushButton("Help", self)
    helpBtn.clicked.connect(lambda: webbrowser.open_new("https://zebrazoom.org/documentation/docs/behaviorAnalysis/optimizingSpeedOfFinalAnalysis"))
    helpBtn.setVisible(False)
    layout.addWidget(helpBtn, alignment=Qt.AlignmentFlag.AlignCenter)

    videoInfoLayout = QFormLayout()
    videoInfoLayout.setFormAlignment(Qt.AlignmentFlag.AlignCenter)
    videoInfoLayout.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.FieldsStayAtSizeHint)
    videoFPS = QLineEdit(self)
    videoFPS.setValidator(QDoubleValidator(videoFPS))
    videoFPS.validator().setBottom(0)

    def videoFPSChanged(text):
      if text:
        controller.configFile["videoFPS"] = float(text)
      elif "videoFPS" in controller.configFile:
          del controller.configFile["videoFPS"]
    videoFPS.textChanged.connect(videoFPSChanged)
    videoFPS.textChanged.connect(updateSaveBtn)
    videoInfoLayout.addRow("videoFPS:", videoFPS)
    videoPixelSize = QLineEdit(self)
    videoPixelSize.setValidator(QDoubleValidator(videoPixelSize))
    videoPixelSize.validator().setBottom(0)

    def videoPixelSizeChanged(text):
      if text:
        controller.configFile["videoPixelSize"] = float(text)
      elif "videoPixelSize" in controller.configFile:
          del controller.configFile["videoPixelSize"]
    videoPixelSize.textChanged.connect(videoPixelSizeChanged)
    videoPixelSize.textChanged.connect(updateSaveBtn)
    videoInfoLayout.addRow("videoPixelSize:", videoPixelSize)
    layout.addLayout(videoInfoLayout)

    self._oldFormatCheckbox = QCheckBox("Save results in the legacy (json) format")
    def oldFormatToggled(checked):
      if checked:
        if "storeH5" in controller.configFile:
          del controller.configFile["storeH5"]
        if self._alwaysSaveCheckbox.isVisible():
          self._alwaysSaveCheckbox.setChecked(True)
        formatLabel.setText('Raw data will be saved in a json file')
      else:
        controller.configFile["storeH5"] = 1
        if self._alwaysSaveCheckbox.isVisible():
          self._alwaysSaveCheckbox.setChecked(False)
        formatLabel.setText('Raw data will be saved in an hdf5 file')
    self._oldFormatCheckbox.toggled.connect(oldFormatToggled)
    layout.addWidget(self._oldFormatCheckbox, alignment=Qt.AlignmentFlag.AlignCenter)

    formatLabel = QLabel('Raw data will be saved in an hdf5 file')
    layout.addWidget(formatLabel, alignment=Qt.AlignmentFlag.AlignCenter)

    self._alwaysSaveCheckbox = QCheckBox("Save coordinates and tail angle even when fish isn't moving (in csv/excel format)")
    def alwaysSaveToggled(checked):
      if checked:
        self._saveAllDataLabel.setText('One csv/excel file with one row of data for each frame will be created for each animal in each well.')
        controller.configFile["saveAllDataEvenIfNotInBouts"] = 1
      else:
        self._saveAllDataLabel.setText('Csv/excel files will not be created.')
        if "saveAllDataEvenIfNotInBouts" in controller.configFile:
          del controller.configFile["saveAllDataEvenIfNotInBouts"]
    self._alwaysSaveCheckbox.toggled.connect(alwaysSaveToggled)
    layout.addWidget(self._alwaysSaveCheckbox, alignment=Qt.AlignmentFlag.AlignCenter)

    self._saveAllDataLabel = QLabel('Csv/excel files will not be created.')
    layout.addWidget(self._saveAllDataLabel, alignment=Qt.AlignmentFlag.AlignCenter)

    self._validationVideoWidget = StoreValidationVideoWidget()
    layout.addWidget(self._validationVideoWidget, alignment=Qt.AlignmentFlag.AlignCenter)

    layout.addStretch()

    testCheckbox = QCheckBox("Test tracking after saving config", self)
    testCheckbox.setChecked(True)
    layout.addWidget(testCheckbox, alignment=Qt.AlignmentFlag.AlignCenter)
    saveBtn = util.apply_style(QPushButton("Save Config File", self), background_color=util.DEFAULT_BUTTON_COLOR)
    saveBtn.clicked.connect(lambda: controller.finishConfig(testCheckbox.isChecked()))
    layout.addWidget(saveBtn, alignment=Qt.AlignmentFlag.AlignCenter)
    buttonsLayout = QHBoxLayout()
    buttonsLayout.addStretch()
    backBtn = QPushButton("Back", self)
    backBtn.setObjectName("back")
    buttonsLayout.addWidget(backBtn, alignment=Qt.AlignmentFlag.AlignCenter)
    startPageBtn = QPushButton("Go to the start page", self)
    startPageBtn.clicked.connect(lambda: controller.show_frame("StartPage"))
    buttonsLayout.addWidget(startPageBtn, alignment=Qt.AlignmentFlag.AlignCenter)
    buttonsLayout.addStretch()
    layout.addStretch()
    layout.addLayout(buttonsLayout)

    self.setLayout(layout)

  def refreshPage(self, showFasterTracking=False):
    trackingMethod = self.controller.configFile.get("trackingMethod", None)
    freelySwimming = not trackingMethod and not self.controller.configFile.get("headEmbeded", False)
    for widget in (self._fasterTrackingCheckbox, self._changingBackgroundCheckbox):
      widget.setChecked(False)
      widget.setVisible(freelySwimming)
    if freelySwimming:
      self._fasterTrackingCheckbox.setVisible(showFasterTracking)
      self._fasterTrackingCheckbox.setChecked(showFasterTracking)
    if (trackingMethod == "fastCenterOfMassTracking_KNNbackgroundSubtraction" or trackingMethod == "fastCenterOfMassTracking_ClassicalBackgroundSubtraction") and \
        not self.controller.configFile.get("noBoutsDetection", False) and not self.controller.configFile.get("coordinatesOnlyBoutDetection", False):
      self.controller.configFile["detectMovementWithRawVideoInsideTracking"] = 1
    if trackingMethod:
      self._saveAllDataLabel.setVisible(False)
      for checkbox in (self._alwaysSaveCheckbox, self._calculateCurvatureCheckbox, self._calculateTailAngleHeatmapCheckbox):
        checkbox.setChecked(False)
        checkbox.setVisible(False)
    else:
      self._saveAllDataLabel.setVisible(True)
      for checkbox, param in zip((self._alwaysSaveCheckbox, self._calculateCurvatureCheckbox, self._calculateTailAngleHeatmapCheckbox), ('saveAllDataEvenIfNotInBouts', 'perBoutOutput', 'tailAnglesHeatMap')):
        checkbox.setVisible(True)
        if checkbox.isChecked():
          self.controller.configFile[param] = 1
    if 'storeH5' not in self.controller.configFile:
      self.controller.configFile['storeH5'] = 1
    storeLegacy = not self.controller.configFile['storeH5']
    if storeLegacy != self._oldFormatCheckbox.isChecked():
      self._oldFormatCheckbox.setChecked(storeLegacy)
    else:
      self._oldFormatCheckbox.toggled.emit(storeLegacy)
    if 'createValidationVideo' not in self.controller.configFile:
      self.controller.configFile['createValidationVideo'] = 0
    self._validationVideoWidget.refresh(self.controller.configFile)
    self._nbTailPoints.setText(str(self.controller.configFile.get('nbTailPoints', '')))

  def showEvent(self, evt):
    self.refreshPage()
    super().showEvent(evt)
