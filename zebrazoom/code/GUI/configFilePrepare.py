import os
import webbrowser

import cv2

from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QCursor, QFont, QIcon, QDoubleValidator, QIntValidator, QPixmap
from PyQt5.QtWidgets import QApplication, QFrame, QLabel, QWidget, QGridLayout, QPushButton, QHBoxLayout, QVBoxLayout, QCheckBox, QRadioButton, QLineEdit, QButtonGroup, QSpacerItem
PYQT6 = False

import zebrazoom.videoFormatConversion.zzVideoReading as zzVideoReading
import zebrazoom.code.util as util
from zebrazoom.code.GUI.configFilePrepareFunctions import numberOfAnimals


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


class OptimizeConfigFile(QWidget):
  def __init__(self, controller):
    super().__init__(controller.window)
    self.controller = controller
    self._originalBackgroundPreProcessMethod = None
    self._originalBackgroundPreProcessParameters = None
    self._originalPostProcessMultipleTrajectories = None
    self._originalPostProcessMaxDistanceAuthorized = None
    self._originalPostProcessMaxDisapearanceFrames = None
    self._originalOutputValidationVideoContrastImprovement = None
    self._originalRecalculateForegroundImageBasedOnBodyArea = None
    self._originalPlotOnlyOneTailPointForVisu = None

    self._headEmbeddedWidgets = set()
    self._freelySwimmingWidgets = set()
    self._fastCenterOfMassWidgets = set()
    self._centerOfMassWidgets = set()

    layout = QVBoxLayout()
    layout.addWidget(util.apply_style(QLabel("Optimize previously created configuration file", self), font=controller.title_font), alignment=Qt.AlignmentFlag.AlignCenter)

    optimizeButtonsLayout = QHBoxLayout()
    optimizeButtonsLayout.addStretch()
    optimizeFreelySwimmingBtn = util.apply_style(QPushButton("Optimize fish freely swimming tail tracking configuration file parameters", self), background_color=util.LIGHT_YELLOW)
    optimizeFreelySwimmingBtn.clicked.connect(lambda: util.addToHistory(controller.calculateBackgroundFreelySwim)(controller, 0, automaticParameters=True, useNext=False))
    optimizeButtonsLayout.addWidget(optimizeFreelySwimmingBtn, alignment=Qt.AlignmentFlag.AlignCenter)
    self._freelySwimmingWidgets.add(optimizeFreelySwimmingBtn)
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

    advancedOptionsLayout = QGridLayout()
    vframe = QFrame(self)
    vframe.setFrameShape(QFrame.Shape.VLine)
    advancedOptionsLayout.addWidget(vframe, 0, 2, 22, 1)
    self._freelySwimmingWidgets.add(vframe)
    self._fastCenterOfMassWidgets.add(vframe)
    self._centerOfMassWidgets.add(vframe)
    self._headEmbeddedWidgets.add(vframe)
    hframe = QFrame(self)
    hframe.setFrameShape(QFrame.Shape.HLine)
    advancedOptionsLayout.addWidget(hframe, 4, 0, 1, 5)
    self._freelySwimmingWidgets.add(hframe)
    self._fastCenterOfMassWidgets.add(hframe)
    self._centerOfMassWidgets.add(hframe)

    solveIssuesLabel = util.apply_style(QLabel("Solve issues near the borders of the wells/tanks/arenas"), font_size='16px')
    advancedOptionsLayout.addWidget(solveIssuesLabel, 0, 0, 1, 2, Qt.AlignmentFlag.AlignCenter)
    self._freelySwimmingWidgets.add(solveIssuesLabel)
    self._fastCenterOfMassWidgets.add(solveIssuesLabel)
    self._centerOfMassWidgets.add(solveIssuesLabel)
    solveIssuesInfoLabel = QLabel("backgroundPreProcessParameters should be an odd positive integer. Higher value filters more pixels on the borders of the wells/tanks/arenas.")
    solveIssuesInfoLabel.setMinimumSize(1, 1)
    solveIssuesInfoLabel.resizeEvent = lambda evt: solveIssuesInfoLabel.setMinimumWidth(evt.size().width()) or solveIssuesInfoLabel.setWordWrap(evt.size().width() <= solveIssuesInfoLabel.sizeHint().width())
    advancedOptionsLayout.addWidget(solveIssuesInfoLabel, 1, 0, 1, 2, Qt.AlignmentFlag.AlignCenter)
    self._freelySwimmingWidgets.add(solveIssuesInfoLabel)
    self._fastCenterOfMassWidgets.add(solveIssuesInfoLabel)
    self._centerOfMassWidgets.add(solveIssuesInfoLabel)
    self._backgroundPreProcessParameters = backgroundPreProcessParameters = QLineEdit(controller.window)
    backgroundPreProcessParameters.setValidator(QIntValidator(backgroundPreProcessParameters))
    backgroundPreProcessParameters.validator().setBottom(0)

    def updateBackgroundPreProcessParameters(text):
      if text:
        controller.configFile["backgroundPreProcessMethod"] = ["erodeThenMin"]
        controller.configFile["backgroundPreProcessParameters"] = [[int(text)]]
      else:
        if self._originalBackgroundPreProcessMethod is not None:
          controller.configFile["backgroundPreProcessMethod"] = self._originalBackgroundPreProcessMethod
        elif "backgroundPreProcessMethod" in controller.configFile:
          del controller.configFile["backgroundPreProcessMethod"]
        if self._originalBackgroundPreProcessParameters is not None:
          controller.configFile["backgroundPreProcessParameters"] = self._originalBackgroundPreProcessParameters
        elif "backgroundPreProcessParameters" in controller.configFile:
          del controller.configFile["backgroundPreProcessParameters"]
    backgroundPreProcessParameters.textChanged.connect(updateBackgroundPreProcessParameters)
    backgroundPreProcessParametersLabel = QLabel("backgroundPreProcessParameters:")
    advancedOptionsLayout.addWidget(backgroundPreProcessParametersLabel, 2, 0, Qt.AlignmentFlag.AlignCenter)
    self._freelySwimmingWidgets.add(backgroundPreProcessParametersLabel)
    self._fastCenterOfMassWidgets.add(backgroundPreProcessParametersLabel)
    self._centerOfMassWidgets.add(backgroundPreProcessParametersLabel)
    advancedOptionsLayout.addWidget(backgroundPreProcessParameters, 2, 1, Qt.AlignmentFlag.AlignLeft)
    self._freelySwimmingWidgets.add(backgroundPreProcessParameters)
    self._fastCenterOfMassWidgets.add(backgroundPreProcessParameters)
    self._centerOfMassWidgets.add(backgroundPreProcessParameters)

    postProcessTrajectoriesLabel = util.apply_style(QLabel("Post-process animal center trajectories"), font_size='16px')
    advancedOptionsLayout.addWidget(postProcessTrajectoriesLabel, 0, 3, 1, 2, Qt.AlignmentFlag.AlignCenter)
    self._freelySwimmingWidgets.add(postProcessTrajectoriesLabel)
    self._fastCenterOfMassWidgets.add(postProcessTrajectoriesLabel)
    self._centerOfMassWidgets.add(postProcessTrajectoriesLabel)
    postProcessTrajectoriesInfoLabel = QLabel("postProcessMaxDistanceAuthorized is the maximum distance in pixels above which it is considered that an animal was detected incorrectly (click on the button to adjust it visually). postProcessMaxDisapearanceFrames is the maximum number of frames for which the post-processing will consider that an animal can be incorrectly detected.")
    postProcessTrajectoriesInfoLabel.setMinimumSize(1, 1)
    postProcessTrajectoriesInfoLabel.resizeEvent = lambda evt: postProcessTrajectoriesInfoLabel.setMinimumWidth(evt.size().width()) or postProcessTrajectoriesInfoLabel.setWordWrap(evt.size().width() <= postProcessTrajectoriesInfoLabel.sizeHint().width())
    advancedOptionsLayout.addWidget(postProcessTrajectoriesInfoLabel, 1, 3, 1, 2, Qt.AlignmentFlag.AlignCenter)
    self._freelySwimmingWidgets.add(postProcessTrajectoriesInfoLabel)
    self._fastCenterOfMassWidgets.add(postProcessTrajectoriesInfoLabel)
    self._centerOfMassWidgets.add(postProcessTrajectoriesInfoLabel)
    self._postProcessMaxDistanceAuthorized = postProcessMaxDistanceAuthorized = QLineEdit(controller.window)
    postProcessMaxDistanceAuthorized.setValidator(QIntValidator(postProcessMaxDistanceAuthorized))
    postProcessMaxDistanceAuthorized.validator().setBottom(0)

    def updatePostProcessMaxDistanceAuthorized(text):
      if text:
        controller.configFile["postProcessMaxDistanceAuthorized"] = int(text)
        controller.configFile["postProcessMultipleTrajectories"] = 1
      else:
        if not postProcessMaxDisapearanceFrames.text():
          if self._originalPostProcessMultipleTrajectories is not None:
            controller.configFile["postProcessMultipleTrajectories"] = self._originalPostProcessMultipleTrajectories
          elif "postProcessMultipleTrajectories" in controller.configFile:
            del controller.configFile["postProcessMultipleTrajectories"]
        if self._originalPostProcessMaxDistanceAuthorized is not None:
          controller.configFile["postProcessMaxDistanceAuthorized"] = self._originalPostProcessMaxDistanceAuthorized
        elif "postProcessMaxDistanceAuthorized" in controller.configFile:
          del controller.configFile["postProcessMaxDistanceAuthorized"]
    postProcessMaxDistanceAuthorized.textChanged.connect(updatePostProcessMaxDistanceAuthorized)
    postProcessMaxDistanceAuthorizedLabel = QPushButton("postProcessMaxDistanceAuthorized:")

    def modifyPostProcessMaxDistanceAuthorized():
      cap = zzVideoReading.VideoCapture(controller.videoToCreateConfigFileFor)
      cap.set(1, controller.configFile.get("firstFrame", 1))
      ret, frame = cap.read()
      cancelled = False
      def cancel():
        nonlocal cancelled
        cancelled = True
      center, radius = util.getCircle(frame, 'Click on the center of an animal and select the distance which it can realistically travel', cancel)
      if not cancelled:
        postProcessMaxDistanceAuthorized.setText(str(radius))
    postProcessMaxDistanceAuthorizedLabel.clicked.connect(modifyPostProcessMaxDistanceAuthorized)
    advancedOptionsLayout.addWidget(postProcessMaxDistanceAuthorizedLabel, 2, 3, Qt.AlignmentFlag.AlignCenter)
    self._freelySwimmingWidgets.add(postProcessMaxDistanceAuthorizedLabel)
    self._fastCenterOfMassWidgets.add(postProcessMaxDistanceAuthorizedLabel)
    self._centerOfMassWidgets.add(postProcessMaxDistanceAuthorizedLabel)
    advancedOptionsLayout.addWidget(postProcessMaxDistanceAuthorized, 2, 4, Qt.AlignmentFlag.AlignLeft)
    self._freelySwimmingWidgets.add(postProcessMaxDistanceAuthorized)
    self._fastCenterOfMassWidgets.add(postProcessMaxDistanceAuthorized)
    self._centerOfMassWidgets.add(postProcessMaxDistanceAuthorized)

    self._postProcessMaxDisapearanceFrames = postProcessMaxDisapearanceFrames = QLineEdit(controller.window)
    postProcessMaxDisapearanceFrames.setValidator(QIntValidator(postProcessMaxDisapearanceFrames))
    postProcessMaxDisapearanceFrames.validator().setBottom(0)

    def updatePostProcessMaxDisapearanceFrames(text):
      if text:
        controller.configFile["postProcessMaxDisapearanceFrames"] = int(text)
        controller.configFile["postProcessMultipleTrajectories"] = 1
      else:
        if not postProcessMaxDistanceAuthorized.text():
          if self._originalPostProcessMultipleTrajectories is not None:
            controller.configFile["postProcessMultipleTrajectories"] = self._originalPostProcessMultipleTrajectories
          elif "postProcessMultipleTrajectories" in controller.configFile:
            del controller.configFile["postProcessMultipleTrajectories"]
        if self._originalPostProcessMaxDisapearanceFrames is not None:
          controller.configFile["postProcessMaxDisapearanceFrames"] = self._originalPostProcessMaxDisapearanceFrames
        elif "postProcessMaxDisapearanceFrames" in controller.configFile:
          del controller.configFile["postProcessMaxDisapearanceFrames"]
    postProcessMaxDisapearanceFrames.textChanged.connect(updatePostProcessMaxDisapearanceFrames)
    postProcessMaxDisapearanceFramesLabel = QLabel("postProcessMaxDisapearanceFrames:")
    advancedOptionsLayout.addWidget(postProcessMaxDisapearanceFramesLabel, 3, 3, Qt.AlignmentFlag.AlignCenter)
    self._freelySwimmingWidgets.add(postProcessMaxDisapearanceFramesLabel)
    self._fastCenterOfMassWidgets.add(postProcessMaxDisapearanceFramesLabel)
    self._centerOfMassWidgets.add(postProcessMaxDisapearanceFramesLabel)
    advancedOptionsLayout.addWidget(postProcessMaxDisapearanceFrames, 3, 4, Qt.AlignmentFlag.AlignLeft)
    self._freelySwimmingWidgets.add(postProcessMaxDisapearanceFrames)
    self._fastCenterOfMassWidgets.add(postProcessMaxDisapearanceFrames)
    self._centerOfMassWidgets.add(postProcessMaxDisapearanceFrames)

    optimizeDataAnalysisLabel = util.apply_style(QLabel("Optimize data analysis"), font_size='16px')
    advancedOptionsLayout.addWidget(optimizeDataAnalysisLabel, 5, 0, 1, 2, Qt.AlignmentFlag.AlignCenter)
    self._headEmbeddedWidgets.add(optimizeDataAnalysisLabel)
    self._freelySwimmingWidgets.add(optimizeDataAnalysisLabel)
    self._fastCenterOfMassWidgets.add(optimizeDataAnalysisLabel)
    self._centerOfMassWidgets.add(optimizeDataAnalysisLabel)

    plotOnlyOneTailPointForVisuLabel = util.apply_style(QLabel("Validation video options"), font_size='16px')
    advancedOptionsLayout.addWidget(plotOnlyOneTailPointForVisuLabel, 5, 3, 1, 2, Qt.AlignmentFlag.AlignCenter)
    self._freelySwimmingWidgets.add(plotOnlyOneTailPointForVisuLabel)
    self._headEmbeddedWidgets.add(plotOnlyOneTailPointForVisuLabel)
    def updatePlotOnlyOneTailPointForVisu(checked):
      if checked:
        controller.configFile["plotOnlyOneTailPointForVisu"] = 1
      elif self._originalPlotOnlyOneTailPointForVisu is None:
        if "plotOnlyOneTailPointForVisu" in controller.configFile:
          del controller.configFile["plotOnlyOneTailPointForVisu"]
      else:
        controller.configFile["plotOnlyOneTailPointForVisu"] = 0
    self._plotOnlyOneTailPointForVisu = QCheckBox("Display tracking point only on the tail tip in validation videos", self)
    self._plotOnlyOneTailPointForVisu.toggled.connect(updatePlotOnlyOneTailPointForVisu)
    advancedOptionsLayout.addWidget(self._plotOnlyOneTailPointForVisu, 6, 3, 1, 2, Qt.AlignmentFlag.AlignCenter)
    self._freelySwimmingWidgets.add(self._plotOnlyOneTailPointForVisu)
    self._headEmbeddedWidgets.add(self._plotOnlyOneTailPointForVisu)

    def speedUpAnalysisToggled(checked):
      analysisInfoWidget.setVisible(checked)
      if not checked:
        if "createPandasDataFrameOfParameters" in controller.configFile:
          del controller.configFile["createPandasDataFrameOfParameters"]
        if "videoFPS" in controller.configFile:
          del controller.configFile["videoFPS"]
        if "videoPixelSize" in controller.configFile:
          del controller.configFile["videoPixelSize"]
      else:
        controller.configFile["createPandasDataFrameOfParameters"] = 1
        if videoFPS.text():
          controller.configFile["videoFPS"] = float(videoFPS.text())
        if videoPixelSize.text():
          controller.configFile["videoPixelSize"] = float(videoPixelSize.text())
    self._speedUpAnalysisCheckbox = speedUpAnalysisCheckbox = QCheckBox("Speed up final ZebraZoom behavior analysis", self)
    speedUpAnalysisCheckbox.toggled.connect(speedUpAnalysisToggled)
    advancedOptionsLayout.addWidget(speedUpAnalysisCheckbox, 6, 0, 1, 2, Qt.AlignmentFlag.AlignCenter)
    self._headEmbeddedWidgets.add(speedUpAnalysisCheckbox)
    self._freelySwimmingWidgets.add(speedUpAnalysisCheckbox)
    self._fastCenterOfMassWidgets.add(speedUpAnalysisCheckbox)
    self._centerOfMassWidgets.add(speedUpAnalysisCheckbox)

    analysisInfoLayout = QGridLayout()
    analysisInfoLayout.addWidget(QLabel("videoFPS:"), 0, 0, Qt.AlignmentFlag.AlignLeft)
    self._videoFPS = videoFPS = QLineEdit(self)
    videoFPS.setValidator(QDoubleValidator(videoFPS))
    videoFPS.validator().setBottom(0)

    def videoFPSChanged(text):
      if text:
        controller.configFile["videoFPS"] = float(text)
      elif "videoFPS" in controller.configFile:
          del controller.configFile["videoFPS"]
    videoFPS.textChanged.connect(videoFPSChanged)
    analysisInfoLayout.addWidget(videoFPS, 0, 1, Qt.AlignmentFlag.AlignLeft)
    analysisInfoLayout.addWidget(QLabel("videoPixelSize:"), 1, 0, Qt.AlignmentFlag.AlignLeft)
    self._videoPixelSize = videoPixelSize = QLineEdit(self)
    videoPixelSize.setValidator(QDoubleValidator(videoPixelSize))
    videoPixelSize.validator().setBottom(0)

    def videoPixelSizeChanged(text):
      if text:
        controller.configFile["videoPixelSize"] = float(text)
      elif "videoPixelSize" in controller.configFile:
          del controller.configFile["videoPixelSize"]
    videoPixelSize.textChanged.connect(videoPixelSizeChanged)
    analysisInfoLayout.addWidget(videoPixelSize, 1, 1, Qt.AlignmentFlag.AlignLeft)
    helpBtn = QPushButton("Help", self)
    helpBtn.clicked.connect(lambda: webbrowser.open_new("https://zebrazoom.org/documentation/docs/behaviorAnalysis/optimizingSpeedOfFinalAnalysis"))
    analysisInfoLayout.addWidget(helpBtn, 2, 0, 1, 2, Qt.AlignmentFlag.AlignCenter)
    self._analysisInfoWidget = analysisInfoWidget = QWidget(self)
    analysisInfoWidget.setLayout(analysisInfoLayout)
    advancedOptionsLayout.addWidget(analysisInfoWidget, 7, 0, 3, 2, Qt.AlignmentFlag.AlignCenter)
    self._headEmbeddedWidgets.add(analysisInfoWidget)
    self._freelySwimmingWidgets.add(analysisInfoWidget)
    self._fastCenterOfMassWidgets.add(analysisInfoWidget)
    self._centerOfMassWidgets.add(analysisInfoWidget)

    tailTrackingLabel = util.apply_style(QLabel("Tail tracking quality"), font_size='16px')
    advancedOptionsLayout.addWidget(tailTrackingLabel, 11, 0, 1, 2, Qt.AlignmentFlag.AlignCenter)
    self._freelySwimmingWidgets.add(tailTrackingLabel)
    tailTrackingInfoLabel = QLabel("Checking this increases quality, but makes tracking slower.")
    advancedOptionsLayout.addWidget(tailTrackingInfoLabel, 12, 0, 1, 2, Qt.AlignmentFlag.AlignCenter)
    self._freelySwimmingWidgets.add(tailTrackingInfoLabel)
    self._recalculateForegroundImageBasedOnBodyArea = QCheckBox("recalculateForegroundImageBasedOnBodyArea")

    def updateRecalculateForegroundImageBasedOnBodyArea(checked):
      if checked:
        controller.configFile["recalculateForegroundImageBasedOnBodyArea"] = 1
      elif self._originalRecalculateForegroundImageBasedOnBodyArea is None:
        if "recalculateForegroundImageBasedOnBodyArea" in controller.configFile:
          del controller.configFile["recalculateForegroundImageBasedOnBodyArea"]
      else:
        controller.configFile["recalculateForegroundImageBasedOnBodyArea"] = 0
    self._recalculateForegroundImageBasedOnBodyArea.toggled.connect(updateRecalculateForegroundImageBasedOnBodyArea)
    advancedOptionsLayout.addWidget(self._recalculateForegroundImageBasedOnBodyArea, 13, 0, 1, 2, Qt.AlignmentFlag.AlignCenter)
    self._freelySwimmingWidgets.add(self._recalculateForegroundImageBasedOnBodyArea)

    hframe = QFrame(self)
    hframe.setFrameShape(QFrame.Shape.HLine)
    advancedOptionsLayout.addWidget(hframe, 10, 0, 1, 5)
    self._freelySwimmingWidgets.add(hframe)
    videoRotationLabel = util.apply_style(QLabel("Video rotation"), font_size='16px')
    advancedOptionsLayout.addWidget(videoRotationLabel, 11, 3, 1, 2, Qt.AlignmentFlag.AlignCenter)
    self._freelySwimmingWidgets.add(videoRotationLabel)
    rotationAngleLabel = QPushButton("Rotation angle (degrees):")
    def modifyRotationAngle():
      cap = zzVideoReading.VideoCapture(controller.videoToCreateConfigFileFor)
      cap.set(1, controller.configFile.get("firstFrame", 1))
      ret, frame = cap.read()

      try:
        angle = float(self._rotationAngleLineEdit.text())
      except ValueError:
        angle = 0.

      angle = util.getRotationAngle(frame, angle)
      if angle is not None:
        self._rotationAngleLineEdit.setText("{:.2f}".format(angle))
    rotationAngleLabel.clicked.connect(modifyRotationAngle)
    advancedOptionsLayout.addWidget(rotationAngleLabel, 12, 3, Qt.AlignmentFlag.AlignCenter)
    self._freelySwimmingWidgets.add(rotationAngleLabel)
    self._rotationAngleLineEdit = QLineEdit()
    def updateRotationAngle(text):
      if text:
        try:
          value = float(text)
        except ValueError:
          return
        controller.configFile["backgroundPreProcessMethod"] = ["rotate"]
        controller.configFile["imagePreProcessMethod"] = ["rotate"]
        controller.configFile["backgroundPreProcessParameters"] = [[value]]
        controller.configFile["imagePreProcessParameters"] = [[value]]
      else:
        if self._originalBackgroundPreProcessMethod is not None:
          controller.configFile["backgroundPreProcessMethod"] = self._originalBackgroundPreProcessMethod
        elif "backgroundPreProcessMethod" in controller.configFile:
          del controller.configFile["backgroundPreProcessMethod"]
        if self._originalBackgroundPreProcessParameters is not None:
          controller.configFile["backgroundPreProcessParameters"] = self._originalBackgroundPreProcessParameters
        elif "backgroundPreProcessParameters" in controller.configFile:
          del controller.configFile["backgroundPreProcessParameters"]
        if self._originalImagePreProcessMethod is not None:
          controller.configFile["imagePreProcessMethod"] = self._originalImagePreProcessMethod
        elif "imagePreProcessMethod" in controller.configFile:
          del controller.configFile["imagePreProcessMethod"]
        if self._originalImagePreProcessParameters is not None:
          controller.configFile["imagePreProcessParameters"] = self._originalImagePreProcessParameters
        elif "imagePreProcessParameters" in controller.configFile:
          del controller.configFile["imagePreProcessParameters"]
    self._rotationAngleLineEdit.textChanged.connect(updateRotationAngle)
    advancedOptionsLayout.addWidget(self._rotationAngleLineEdit, 12, 4, Qt.AlignmentFlag.AlignLeft)
    self._freelySwimmingWidgets.add(self._rotationAngleLineEdit)

    hframe = QFrame(self)
    hframe.setFrameShape(QFrame.Shape.HLine)
    advancedOptionsLayout.addWidget(hframe, 14, 0, 1, 5)
    self._freelySwimmingWidgets.add(hframe)
    nonStationaryBackgroundLabel = util.apply_style(QLabel("Non stationary background"), font_size='16px')
    advancedOptionsLayout.addWidget(nonStationaryBackgroundLabel, 15, 0, 1, 2, Qt.AlignmentFlag.AlignCenter)
    self._freelySwimmingWidgets.add(nonStationaryBackgroundLabel)
    self._updateBackgroundOnEveryFrameCheckbox = QCheckBox("Update background on every frame")
    def updateBackroundOnEveryFrame(checked):
      if checked:
        controller.configFile["updateBackgroundAtInterval"] = 1
        controller.configFile["useFirstFrameAsBackground"] = 1
      else:
        if self._originalUpdateBackgroundAtInterval is None:
          if "updateBackgroundAtInterval" in controller.configFile:
            del controller.configFile["updateBackgroundAtInterval"]
        else:
          controller.configFile["updateBackgroundAtInterval"] = 0
        if self._originalUseFirstFrameAsBackground is None:
          if "useFirstFrameAsBackground" in controller.configFile:
            del controller.configFile["useFirstFrameAsBackground"]
        else:
          controller.configFile["useFirstFrameAsBackground"] = 0
    self._updateBackgroundOnEveryFrameCheckbox.toggled.connect(updateBackroundOnEveryFrame)
    advancedOptionsLayout.addWidget(self._updateBackgroundOnEveryFrameCheckbox, 16, 0, 1, 2, Qt.AlignmentFlag.AlignCenter)
    self._freelySwimmingWidgets.add(self._updateBackgroundOnEveryFrameCheckbox)

    noMultiprocessingOverWellsLabel = util.apply_style(QLabel("No multiprocessing over wells"), font_size='16px')
    advancedOptionsLayout.addWidget(noMultiprocessingOverWellsLabel, 15, 3, 1, 2, Qt.AlignmentFlag.AlignCenter)
    self._freelySwimmingWidgets.add(noMultiprocessingOverWellsLabel)
    self._noMultiprocessingCheckbox = QCheckBox("No multiprocessing over wells")
    def noMultiprocessingToggled(checked):
      if checked:
        controller.configFile["fasterMultiprocessing"] = 2
      else:
        if self._originalNoMultiprocessing is None:
          if "fasterMultiprocessing" in controller.configFile:
            del controller.configFile["fasterMultiprocessing"]
        else:
          controller.configFile["fasterMultiprocessing"] = 0
    self._noMultiprocessingCheckbox.toggled.connect(noMultiprocessingToggled)
    advancedOptionsLayout.addWidget(self._noMultiprocessingCheckbox, 16, 3, 1, 2, Qt.AlignmentFlag.AlignCenter)
    self._freelySwimmingWidgets.add(self._noMultiprocessingCheckbox)

    hframe = QFrame(self)
    hframe.setFrameShape(QFrame.Shape.HLine)
    advancedOptionsLayout.addWidget(hframe, 17, 0, 1, 5)
    self._freelySwimmingWidgets.add(hframe)
    advancedOptionsLabel = util.apply_style(QLabel("Documentation links"), font_size='16px')
    advancedOptionsLayout.addWidget(advancedOptionsLabel, 18, 0, 1, 2, Qt.AlignmentFlag.AlignCenter)
    self._freelySwimmingWidgets.add(advancedOptionsLabel)
    speedUpTrackingBtn = QPushButton("Speed up tracking for 'Track heads and tails of freely swimming fish'", self)
    speedUpTrackingBtn.clicked.connect(lambda: webbrowser.open_new("https://github.com/oliviermirat/ZebraZoom/blob/master/TrackingSpeedOptimization.md"))
    advancedOptionsLayout.addWidget(speedUpTrackingBtn, 19, 0, 1, 2, Qt.AlignmentFlag.AlignCenter)
    self._freelySwimmingWidgets.add(speedUpTrackingBtn)
    documentationBtn = QPushButton("Help", self)
    documentationBtn.clicked.connect(lambda: webbrowser.open_new("https://zebrazoom.org/documentation/docs/configurationFile/throughGUI/trackingFreelySwimmingConfigOptimization"))
    advancedOptionsLayout.addWidget(documentationBtn, 20, 0, 1, 2, Qt.AlignmentFlag.AlignCenter)
    self._freelySwimmingWidgets.add(documentationBtn)

    for idx in range(advancedOptionsLayout.columnCount()):
      advancedOptionsLayout.setColumnStretch(idx, 1)
    self._expander = util.Expander(self, 'Show advanced options', advancedOptionsLayout, showFrame=True, addScrollbars=True)
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

  def refresh(self):
    app = QApplication.instance()
    trackingMethod = app.configFile.get("trackingMethod", None)
    if not trackingMethod:
      if app.configFile.get("headEmbeded", False):
        visibleWidgets = self._headEmbeddedWidgets
      else:
        visibleWidgets = self._freelySwimmingWidgets
    elif trackingMethod == "fastCenterOfMassTracking_KNNbackgroundSubtraction" or \
        trackingMethod == "fastCenterOfMassTracking_ClassicalBackgroundSubtraction":
      visibleWidgets = self._fastCenterOfMassWidgets
    else:
      assert trackingMethod == "classicCenterOfMassTracking"
      visibleWidgets = self._centerOfMassWidgets
    for widget in self._freelySwimmingWidgets | self._headEmbeddedWidgets | self._fastCenterOfMassWidgets | self._centerOfMassWidgets:
      if widget in visibleWidgets:
        widget.show()
      else:
        widget.hide()
    self._expander.hide()
    maximumHeight = self._expander.maximumHeight()
    self._expander.setMaximumHeight(self.height())
    layout = self.layout().itemAt(0).widget().layout()
    layout.setStretchFactor(self._expander, 1)
    self._expander.show()
    availableHeight = self._expander.size().height()
    layout.setStretchFactor(self._expander, 0)
    self._expander.setMaximumHeight(maximumHeight)
    self._expander.refresh(availableHeight=availableHeight)

    self._originalBackgroundPreProcessMethod = app.configFile.get("backgroundPreProcessMethod")
    self._originalBackgroundPreProcessParameters = app.configFile.get("backgroundPreProcessParameters")
    if self._originalBackgroundPreProcessParameters is not None and self._originalBackgroundPreProcessMethod is not None:
      if self._originalBackgroundPreProcessMethod[0] == 'erodeThenMin':
        self._backgroundPreProcessParameters.setText(str(self._originalBackgroundPreProcessParameters[0][0]))
      elif self._originalBackgroundPreProcessMethod[0] == 'rotate':
        self._rotationAngleLineEdit.setText(str(self._originalBackgroundPreProcessParameters[0][0]))
      else:
        self._backgroundPreProcessParameters.setText('')
        self._rotationAngleLineEdit.setText('')
    else:
      self._backgroundPreProcessParameters.setText('')
      self._rotationAngleLineEdit.setText('')
    self._originalImagePreProcessMethod = app.configFile.get("imagePreProcessMethod")
    self._originalImagePreProcessParameters = app.configFile.get("imagePreProcessParameters")
    if self._originalImagePreProcessParameters is not None and self._originalImagePreProcessMethod is not None and self._originalBackgroundPreProcessMethod[0] == 'rotate':
      self._rotationAngleLineEdit.setText(str(self._originalImagePreProcessParameters[0][0]))
    else:
      self._rotationAngleLineEdit.setText('')
    self._originalPostProcessMultipleTrajectories = app.configFile.get("postProcessMultipleTrajectories")
    self._originalPostProcessMaxDistanceAuthorized = app.configFile.get("postProcessMaxDistanceAuthorized")
    if self._originalPostProcessMaxDistanceAuthorized is not None:
      self._postProcessMaxDistanceAuthorized.setText(str(self._originalPostProcessMaxDistanceAuthorized))
    else:
      self._postProcessMaxDistanceAuthorized.setText('')
    self._originalPostProcessMaxDisapearanceFrames = app.configFile.get("postProcessMaxDisapearanceFrames")
    if self._originalPostProcessMaxDisapearanceFrames is not None:
      self._postProcessMaxDisapearanceFrames.setText(str(self._originalPostProcessMaxDisapearanceFrames))
    else:
      self._postProcessMaxDisapearanceFrames.setText('')
    self._originalOutputValidationVideoContrastImprovement = app.configFile.get("outputValidationVideoContrastImprovement")
    if self._originalOutputValidationVideoContrastImprovement is not None:
      self._improveContrastCheckbox.setChecked(bool(self._originalOutputValidationVideoContrastImprovement))
    else:
      self._improveContrastCheckbox.setChecked(False)
    self._originalRecalculateForegroundImageBasedOnBodyArea = app.configFile.get("recalculateForegroundImageBasedOnBodyArea")
    if self._originalRecalculateForegroundImageBasedOnBodyArea is not None:
      self._recalculateForegroundImageBasedOnBodyArea.setChecked(bool(self._originalRecalculateForegroundImageBasedOnBodyArea))
    else:
      self._recalculateForegroundImageBasedOnBodyArea.setChecked(False)
    self._originalUpdateBackgroundAtInterval = app.configFile.get("updateBackgroundAtInterval")
    self._originalUseFirstFrameAsBackground = app.configFile.get("useFirstFrameAsBackground")
    if self._originalUpdateBackgroundAtInterval is not None and self._originalUseFirstFrameAsBackground is not None:
      self._updateBackgroundOnEveryFrameCheckbox.setChecked(self._originalUpdateBackgroundAtInterval and self._originalUseFirstFrameAsBackground)
    else:
      self._updateBackgroundOnEveryFrameCheckbox.setChecked(False)
    self._originalPlotOnlyOneTailPointForVisu = app.configFile.get("plotOnlyOneTailPointForVisu")
    if self._originalPlotOnlyOneTailPointForVisu is not None:
      self._plotOnlyOneTailPointForVisu.setChecked(bool(self._originalPlotOnlyOneTailPointForVisu))
    else:
      self._plotOnlyOneTailPointForVisu.setChecked(False)
    self._originalNoMultiprocessing = app.configFile.get("fasterMultiprocessing")
    if self._originalNoMultiprocessing is not None:
      self._noMultiprocessingCheckbox.setChecked(self._originalNoMultiprocessing == 2)
    else:
      self._noMultiprocessingCheckbox.setChecked(False)
    if "createPandasDataFrameOfParameters" in app.configFile:
      self._speedUpAnalysisCheckbox.setChecked(app.configFile["createPandasDataFrameOfParameters"])
    else:
      self._speedUpAnalysisCheckbox.setChecked(False)
    self._analysisInfoWidget.setVisible(self._speedUpAnalysisCheckbox.isChecked())
    if "videoFPS" in app.configFile:
      self._videoFPS.setText(str(app.configFile["videoFPS"]))
    if "videoPixelSize" in app.configFile:
      self._videoPixelSize.setText(str(app.configFile["videoPixelSize"]))


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

    layout = QVBoxLayout()
    layout.addWidget(util.apply_style(QLabel("Prepare Config File", self), font=controller.title_font), alignment=Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(util.apply_style(QLabel("How many regions of interest / wells are there in your video?", self), font=QFont("Helvetica", 10)), alignment=Qt.AlignmentFlag.AlignCenter)
    nbwells = QLineEdit(controller.window)
    nbwells.setValidator(QIntValidator(nbwells))
    nbwells.validator().setBottom(0)
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

    layout.addWidget(util.apply_style(QLabel("What's the total number of animals in your video?", self), font=QFont("Helvetica", 10)), alignment=Qt.AlignmentFlag.AlignCenter)
    nbanimals = QLineEdit(controller.window)
    nbanimals.setValidator(QIntValidator(nbanimals))
    nbanimals.validator().setBottom(0)
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


class NumberOfAnimals2(QWidget):
  def __init__(self, controller):
    super().__init__(controller.window)
    self.controller = controller
    self.preferredSize = (1152, 768)

    layout = QGridLayout()
    layout.addWidget(util.apply_style(QLabel("Prepare Config File", self), font=controller.title_font), 0, 0, 1, 2, Qt.AlignmentFlag.AlignCenter)

    self._nbanimalsLabel = util.apply_style(QLabel("What's the total number of animals in your video?", self), font_size='16px')
    layout.addWidget(self._nbanimalsLabel, 1, 0, 1, 2, Qt.AlignmentFlag.AlignCenter)
    self._nbanimals = nbanimals = QLineEdit(controller.window)
    nbanimals.setValidator(QIntValidator(nbanimals))
    nbanimals.validator().setBottom(0)
    layout.addWidget(nbanimals, 2, 0, 1, 2, Qt.AlignmentFlag.AlignCenter)

    layout.addWidget(util.apply_style(QLabel("Tracking: Choose an option below:", self), font_size='16px'), 3, 1, Qt.AlignmentFlag.AlignCenter)
    btnGroup5 = QButtonGroup(self)
    recommendedTrackingMethodRadioButton = QRadioButton("Original algorithm:\nSlow tracking, but thoroughly tested, might be more accurate in some cases.", self)
    btnGroup5.addButton(recommendedTrackingMethodRadioButton)
    layout.addWidget(recommendedTrackingMethodRadioButton, 4, 1, Qt.AlignmentFlag.AlignLeft)
    alternativeTrackingMethodRadioButton = QRadioButton("New algorithm:\nMuch faster tracking, but not thoroughly tested yet.", self)
    btnGroup5.addButton(alternativeTrackingMethodRadioButton)
    alternativeTrackingMethodRadioButton.setChecked(True)
    layout.addWidget(alternativeTrackingMethodRadioButton, 5, 1, Qt.AlignmentFlag.AlignLeft)
    # layout.addWidget(util.apply_style(QLabel("The alternative method can also work better for animals of different sizes.", self), font=QFont("Helvetica", 10)), 6, 1, Qt.AlignmentFlag.AlignCenter)

    layout.addWidget(util.apply_style(QLabel("Do you want bouts of movement to be detected?", self), font_size='16px'), 3, 0, Qt.AlignmentFlag.AlignCenter)
    yesNoLayout2 = QHBoxLayout()
    yesNoLayout2.addStretch()
    btnGroup2 = QButtonGroup(self)
    slowBoutDetectionRadioButton = QRadioButton("Yes, with slow but more accurate bout detection", self)
    btnGroup2.addButton(slowBoutDetectionRadioButton, id=1)
    yesNoLayout2.addWidget(slowBoutDetectionRadioButton, alignment=Qt.AlignmentFlag.AlignCenter)
    fastBoutDetectionRadioButton = QRadioButton("Yes, with fast but less accurate bout detection", self)
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
    advancedOptionsLayout.addLayout(yesNoLayout1, 6, 1, Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(util.Expander(self, "Show advanced options", advancedOptionsLayout), 7, 0, 1, 2)

    buttonsLayout = QHBoxLayout()
    buttonsLayout.addStretch()
    backBtn = QPushButton("Back", self)
    backBtn.setObjectName("back")
    buttonsLayout.addWidget(backBtn, alignment=Qt.AlignmentFlag.AlignCenter)
    startPageBtn = QPushButton("Go to the start page", self)
    startPageBtn.clicked.connect(lambda: controller.show_frame("StartPage"))
    buttonsLayout.addWidget(startPageBtn, alignment=Qt.AlignmentFlag.AlignCenter)
    nextBtn = util.apply_style(QPushButton("Ok, next step", self), background_color=util.DEFAULT_BUTTON_COLOR)
    nextBtn.clicked.connect(lambda: numberOfAnimals(nbanimals.text() if nbanimals.isVisible() else None, yesRadioButton.isChecked(), False, btnGroup2.checkedId(), recommendedMethodRadioButton.isChecked(), yesBendsRadioButton.isChecked(), recommendedTrackingMethodRadioButton.isChecked()))
    buttonsLayout.addWidget(nextBtn, alignment=Qt.AlignmentFlag.AlignCenter)
    buttonsLayout.addStretch()
    layout.addLayout(buttonsLayout, 8, 0, 1, 2)

    self.setLayout(layout)

  def showEvent(self, evt):
    self._nbanimals.setVisible(self.controller.shape not in ('groupSameSizeAndShapeEquallySpacedWells', 'circular', 'rectangular'))
    self._nbanimalsLabel.setVisible(self.controller.shape not in ('groupSameSizeAndShapeEquallySpacedWells', 'circular', 'rectangular'))
    super().showEvent(evt)


class NumberOfAnimalsCenterOfMass(QWidget):
  def __init__(self, controller):
    super().__init__(controller.window)
    self.controller = controller
    self.preferredSize = (1152, 768)

    layout = QVBoxLayout()
    layout.addWidget(util.apply_style(QLabel("Prepare Config File", self), font=controller.title_font), alignment=Qt.AlignmentFlag.AlignCenter)

    self._nbanimalsLabel = util.apply_style(QLabel("What's the total number of animals in your video?", self), font=QFont("Helvetica", 10))
    layout.addWidget(self._nbanimalsLabel, alignment=Qt.AlignmentFlag.AlignCenter)
    self._nbanimals = nbanimals = QLineEdit(controller.window)
    nbanimals.setValidator(QIntValidator(nbanimals))
    nbanimals.validator().setBottom(0)
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
        controller.configFile["savePathToOriginalVideoForValidationVideo"] = 1
      else:
        if "fasterMultiprocessing" in controller.configFile:
          del controller.configFile["fasterMultiprocessing"]
        if "detectMovementWithRawVideoInsideTracking" in controller.configFile:
          del controller.configFile["detectMovementWithRawVideoInsideTracking"]
        if "savePathToOriginalVideoForValidationVideo" in controller.configFile:
          del controller.configFile["savePathToOriginalVideoForValidationVideo"]
    self._fasterTrackingCheckbox.toggled.connect(fasterTrackingToggled)
    layout.addWidget(self._fasterTrackingCheckbox, alignment=Qt.AlignmentFlag.AlignCenter)

    self._changingBackgroundCheckbox = QCheckBox("Check this box if the background of your video changes over time")
    def changingBackgroundToggled(checked):
      if checked:
        controller.configFile["updateBackgroundAtInterval"] = 1
        controller.configFile["useFirstFrameAsBackground"] = 1
      else:
        if "updateBackgroundAtInterval" in controller.configFile:
          del controller.configFile["updateBackgroundAtInterval"]
        if "useFirstFrameAsBackground" in controller.configFile:
          del controller.configFile["useFirstFrameAsBackground"]
    self._changingBackgroundCheckbox.toggled.connect(changingBackgroundToggled)
    layout.addWidget(self._changingBackgroundCheckbox, alignment=Qt.AlignmentFlag.AlignCenter)

    self._alwaysSaveCheckbox = QCheckBox("Save coordinates and tail angle even when fish isn't moving")
    def alwaysSaveToggled(checked):
      if checked:
        controller.configFile["saveAllDataEvenIfNotInBouts"] = 1
      else:
        if "saveAllDataEvenIfNotInBouts" in controller.configFile:
          del controller.configFile["saveAllDataEvenIfNotInBouts"]
    self._alwaysSaveCheckbox.toggled.connect(alwaysSaveToggled)
    layout.addWidget(self._alwaysSaveCheckbox, alignment=Qt.AlignmentFlag.AlignCenter)

    def speedUpAnalysisToggled(checked):
      analysisInfoWidget.setVisible(checked)
      if not checked:
        if "createPandasDataFrameOfParameters" in controller.configFile:
          del controller.configFile["createPandasDataFrameOfParameters"]
        if "videoFPS" in controller.configFile:
          del controller.configFile["videoFPS"]
        if "videoPixelSize" in controller.configFile:
          del controller.configFile["videoPixelSize"]
      else:
        controller.configFile["createPandasDataFrameOfParameters"] = 1
        if videoFPS.text():
          controller.configFile["videoFPS"] = float(videoFPS.text())
        if videoPixelSize.text():
          controller.configFile["videoPixelSize"] = float(videoPixelSize.text())
    speedUpAnalysisCheckbox = QCheckBox("Pre-calculate kinematic parameters during tracking", self)
    speedUpAnalysisCheckbox.toggled.connect(speedUpAnalysisToggled)
    speedUpAnalysisCheckbox.toggled.connect(updateSaveBtn)
    layout.addWidget(speedUpAnalysisCheckbox, alignment=Qt.AlignmentFlag.AlignCenter)

    analysisInfoLayout = QGridLayout()
    analysisInfoLayout.addWidget(QLabel("videoFPS:"), 0, 0, Qt.AlignmentFlag.AlignLeft)
    videoFPS = QLineEdit(self)
    videoFPS.setValidator(QDoubleValidator(videoFPS))
    videoFPS.validator().setBottom(0)
    videoFPS.textChanged.connect(lambda text: text and controller.configFile.update({"videoFPS": float(text)}))
    videoFPS.textChanged.connect(updateSaveBtn)
    analysisInfoLayout.addWidget(videoFPS, 0, 1, Qt.AlignmentFlag.AlignLeft)
    analysisInfoLayout.addWidget(QLabel("videoPixelSize:"), 1, 0, Qt.AlignmentFlag.AlignLeft)
    videoPixelSize = QLineEdit(self)
    videoPixelSize.setValidator(QDoubleValidator(videoPixelSize))
    videoPixelSize.validator().setBottom(0)
    videoPixelSize.textChanged.connect(lambda text: text and controller.configFile.update({"videoPixelSize": float(text)}))
    videoPixelSize.textChanged.connect(updateSaveBtn)
    analysisInfoLayout.addWidget(videoPixelSize, 1, 1, Qt.AlignmentFlag.AlignLeft)
    helpBtn = QPushButton("Help", self)
    helpBtn.clicked.connect(lambda: webbrowser.open_new("https://zebrazoom.org/documentation/docs/behaviorAnalysis/optimizingSpeedOfFinalAnalysis"))
    analysisInfoLayout.addWidget(helpBtn, 2, 0, 1, 2, Qt.AlignmentFlag.AlignCenter)
    analysisInfoWidget = QWidget(self)
    analysisInfoWidget.setLayout(analysisInfoLayout)
    analysisInfoWidget.setVisible(False)
    layout.addWidget(analysisInfoWidget, alignment=Qt.AlignmentFlag.AlignCenter)

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
    for widget in (self._fasterTrackingCheckbox, self._changingBackgroundCheckbox, self._alwaysSaveCheckbox):
      widget.setChecked(False)
      widget.setVisible(freelySwimming)
    if freelySwimming:
      self._fasterTrackingCheckbox.setVisible(showFasterTracking)
      self._fasterTrackingCheckbox.setChecked(showFasterTracking)
    if (trackingMethod == "fastCenterOfMassTracking_KNNbackgroundSubtraction" or trackingMethod == "fastCenterOfMassTracking_ClassicalBackgroundSubtraction") and \
        not self.controller.configFile.get("noBoutsDetection", False) and not self.controller.configFile.get("coordinatesOnlyBoutDetection", False):
      self.controller.configFile["detectMovementWithRawVideoInsideTracking"] = 1

  def showEvent(self, evt):
    self.refreshPage()
    super().showEvent(evt)
