import os
import webbrowser

try:
  from PyQt6.QtCore import Qt, QSize
  from PyQt6.QtGui import QCursor, QFont, QIntValidator, QPixmap
  from PyQt6.QtWidgets import QApplication, QFrame, QLabel, QWidget, QGridLayout, QPushButton, QHBoxLayout, QVBoxLayout, QCheckBox, QRadioButton, QLineEdit, QButtonGroup
except ImportError:
  from PyQt5.QtCore import Qt, QSize
  from PyQt5.QtGui import QCursor, QFont, QIntValidator, QPixmap
  from PyQt5.QtWidgets import QApplication, QFrame, QLabel, QWidget, QGridLayout, QPushButton, QHBoxLayout, QVBoxLayout, QCheckBox, QRadioButton, QLineEdit, QButtonGroup

import zebrazoom.code.util as util


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
    selectVideoBtn = util.apply_style(QPushButton("Select the video you want to create a configuration file for.", self), background_color=util.LIGHT_YELLOW)
    selectVideoBtn.clicked.connect(lambda: controller.chooseVideoToCreateConfigFileFor(controller, reloadCheckbox.isChecked()) or util.addToHistory(controller.show_frame)("ChooseGeneralExperiment"))
    sublayout1.addWidget(selectVideoBtn, alignment=Qt.AlignmentFlag.AlignCenter)
    sublayout1.addWidget(QLabel("(you will be able to use the configuration file you create for all videos that are similar to that video)", self), alignment=Qt.AlignmentFlag.AlignCenter)
    layout.addLayout(sublayout1)

    sublayout2 = QVBoxLayout()
    startPageBtn = util.apply_style(QPushButton("Go to the start page", self), background_color=util.LIGHT_CYAN)
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

    layout = QVBoxLayout()
    layout.addWidget(util.apply_style(QLabel("Optimize previously created configuration file", self), font=controller.title_font), alignment=Qt.AlignmentFlag.AlignCenter)

    sublayout = QVBoxLayout()
    sublayout.addWidget(QLabel("In many cases, the configuration file previously generated will give good tracking results.", self), alignment=Qt.AlignmentFlag.AlignCenter)
    sublayout.addWidget(QLabel("Always start by testing your newly created configuration file by using the 'Run ZebraZoom's Tracking on a video' option from the main menu of the GUI.", self), alignment=Qt.AlignmentFlag.AlignCenter)
    sublayout.addWidget(QLabel("If after the test, you notice that the tracking has issues, you can use some of the options listed below to improve your configuration file.", self), alignment=Qt.AlignmentFlag.AlignCenter)
    layout.addLayout(sublayout)

    self._optimizeFreelySwimmingBtn = util.apply_style(QPushButton("Optimize fish freely swimming tail tracking configuration file parameters", self), background_color=util.LIGHT_YELLOW)
    self._optimizeFreelySwimmingBtn.clicked.connect(lambda: util.addToHistory(controller.calculateBackgroundFreelySwim)(controller, 0, automaticParameters=True, useNext=False))
    layout.addWidget(self._optimizeFreelySwimmingBtn, alignment=Qt.AlignmentFlag.AlignCenter)
    self._optimizeHeadEmbeddedBtn = util.apply_style(QPushButton("Optimize head embedded tracking configuration file parameters", self), background_color=util.LIGHT_YELLOW)
    self._optimizeHeadEmbeddedBtn.clicked.connect(lambda: util.addToHistory(controller.calculateBackground)(controller, 0, useNext=False))
    layout.addWidget(self._optimizeHeadEmbeddedBtn, alignment=Qt.AlignmentFlag.AlignCenter)
    optimizeBoutBtn = util.apply_style(QPushButton("Optimize/Add bouts detection (only for one animal per well)", self), background_color=util.LIGHT_YELLOW)
    optimizeBoutBtn.clicked.connect(lambda: util.addToHistory(controller.calculateBackgroundFreelySwim)(controller, 0, boutDetectionsOnly=True, useNext=False))
    layout.addWidget(optimizeBoutBtn, alignment=Qt.AlignmentFlag.AlignCenter)

    def updateOutputValidationVideoContrastImprovement(checked):
      if checked:
        controller.configFile["outputValidationVideoContrastImprovement"] = 1
      elif self._originalOutputValidationVideoContrastImprovement is None:
        del controller.configFile["outputValidationVideoContrastImprovement"]
      else:
        controller.configFile["outputValidationVideoContrastImprovement"] = 0

    self._improveContrastCheckbox = QCheckBox("Improve contrast on validation video", self)
    self._improveContrastCheckbox.toggled.connect(updateOutputValidationVideoContrastImprovement)
    layout.addWidget(self._improveContrastCheckbox, alignment=Qt.AlignmentFlag.AlignCenter)

    self._problemSolvingLayout = gridLayout = QGridLayout()
    gridLayout.setColumnStretch(0, 1)
    gridLayout.setColumnStretch(6, 1)
    frame = QFrame(self)
    frame.setFrameShape(QFrame.Shape.VLine)
    gridLayout.addWidget(frame, 0, 3, 3, 1)

    gridLayout.addWidget(util.apply_style(QLabel("Solve issues near the borders of the wells/tanks/arenas"), font_size='16px'), 0, 1, 1, 2, Qt.AlignmentFlag.AlignLeft)
    self._backgroundPreProcessParameters = backgroundPreProcessParameters = QLineEdit(controller.window)
    backgroundPreProcessParameters.setValidator(QIntValidator(backgroundPreProcessParameters))
    backgroundPreProcessParameters.validator().setBottom(0)

    def updateBackgroundPreProcessParameters(text):
      if text:
        controller.configFile["backgroundPreProcessMethod"] = ["erodeThenMin"]
        controller.configFile["backgroundPreProcessParameters"] = [[int(text)]]
      else:
        if self._originalBackgroundPreProcessMethod is not None:
          controller.configFile["backgroundPreProcessParameters"] = self._originalBackgroundPreProcessMethod
        elif "backgroundPreProcessMethod" in controller.configFile:
          del controller.configFile["backgroundPreProcessMethod"]
        if self._originalBackgroundPreProcessParameters is not None:
          controller.configFile["backgroundPreProcessParameters"] = self._originalBackgroundPreProcessParameters
        elif "backgroundPreProcessParameters" in controller.configFile:
          del controller.configFile["backgroundPreProcessParameters"]
    backgroundPreProcessParameters.textChanged.connect(updateBackgroundPreProcessParameters)
    gridLayout.addWidget(QLabel("backgroundPreProcessParameters:"), 1, 1, Qt.AlignmentFlag.AlignCenter)
    gridLayout.addWidget(backgroundPreProcessParameters, 1, 2, Qt.AlignmentFlag.AlignCenter)

    postProcessTrajectoriesLabel = util.apply_style(QLabel("Post-process animal center trajectories"), font_size='16px')
    postProcessTrajectoriesLabel.setToolTip("Trajectories post-processing can help solve problems with animal 'disapearing' and/or temporarily 'jumping' to a distant (and incorrect) location.")
    gridLayout.addWidget(postProcessTrajectoriesLabel, 0, 4, 1, 2, Qt.AlignmentFlag.AlignLeft)
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
    gridLayout.addWidget(QLabel("postProcessMaxDistanceAuthorized:"), 1, 4, Qt.AlignmentFlag.AlignCenter)
    gridLayout.addWidget(postProcessMaxDistanceAuthorized, 1, 5, Qt.AlignmentFlag.AlignCenter)

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
    gridLayout.addWidget(QLabel("postProcessMaxDisapearanceFrames:"), 2, 4, Qt.AlignmentFlag.AlignCenter)
    gridLayout.addWidget(postProcessMaxDisapearanceFrames, 2, 5, Qt.AlignmentFlag.AlignCenter)
    layout.addLayout(gridLayout)

    testBtn = util.apply_style(QPushButton("Test Tracking", self), background_color=util.LIGHT_YELLOW)
    testBtn.clicked.connect(lambda: controller.testConfig())
    layout.addWidget(testBtn, alignment=Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignBottom)
    saveBtn = util.apply_style(QPushButton("Save Config File", self), background_color=util.LIGHT_YELLOW)
    saveBtn.clicked.connect(lambda: controller.finishConfig(testCheckbox.isChecked()))
    layout.addWidget(saveBtn, alignment=Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignTop)

    linkBtn3 = util.apply_style(QPushButton("Speed up tracking for 'Track heads and tails of freely swimming fish'", self), background_color=util.LIGHT_YELLOW)
    linkBtn3.clicked.connect(lambda: webbrowser.open_new("https://github.com/oliviermirat/ZebraZoom/blob/master/TrackingSpeedOptimization.md"))
    layout.addWidget(linkBtn3, alignment=Qt.AlignmentFlag.AlignCenter)
    linkBtn4 = util.apply_style(QPushButton("View More Tracking Troubleshooting Tips", self), background_color=util.GOLD)
    linkBtn4.clicked.connect(lambda: webbrowser.open_new("https://github.com/oliviermirat/ZebraZoom/blob/master/TrackingTroubleshooting.md"))
    layout.addWidget(linkBtn4, alignment=Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(QLabel("If you don't manage to get a good configuration file that fits your needs, email us at info@zebrazoom.org.", self), alignment=Qt.AlignmentFlag.AlignCenter)

    startPageBtn = util.apply_style(QPushButton("Go to the start page", self), background_color=util.LIGHT_CYAN)
    startPageBtn.clicked.connect(lambda: controller.show_frame("StartPage"))
    layout.addWidget(startPageBtn, alignment=Qt.AlignmentFlag.AlignCenter)

    centralWidget = QWidget()
    centralWidget.sizeHint = lambda *args: QSize(1152, 768)
    centralWidget.setLayout(layout)
    wrapperLayout = QVBoxLayout()
    wrapperLayout.addWidget(centralWidget, alignment=Qt.AlignmentFlag.AlignCenter)
    self.setLayout(wrapperLayout)

  def refresh(self):
    app = QApplication.instance()
    if app.configFile.get("headEmbeded", False):
      self._improveContrastCheckbox.show()
      self._optimizeFreelySwimmingBtn.hide()
      self._optimizeHeadEmbeddedBtn.show()
      for idx in range(self._problemSolvingLayout.count()):
        self._problemSolvingLayout.itemAt(idx).widget().hide()
    else:
      self._improveContrastCheckbox.hide()
      self._optimizeFreelySwimmingBtn.show()
      self._optimizeHeadEmbeddedBtn.hide()
      for idx in range(self._problemSolvingLayout.count()):
        self._problemSolvingLayout.itemAt(idx).widget().show()

    self._originalBackgroundPreProcessMethod = app.configFile.get("backgroundPreProcessMethod")
    self._originalBackgroundPreProcessParameters = app.configFile.get("backgroundPreProcessParameters")
    if self._originalBackgroundPreProcessParameters is not None:
      self._backgroundPreProcessParameters.setText(str(self._originalBackgroundPreProcessParameters[0][0]))
    else:
      self._backgroundPreProcessParameters.setText('')
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

class ChooseGeneralExperiment(QWidget):
  def __init__(self, controller):
    super().__init__(controller.window)
    self.controller = controller
    self.preferredSize = (1152, 768)

    layout = QVBoxLayout()
    layout.addWidget(util.apply_style(QLabel("Prepare Config File", self), font=controller.title_font), alignment=Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(util.apply_style(QLabel("Choose only one of the options below:", self), font=QFont("Helvetica", 12)), alignment=Qt.AlignmentFlag.AlignCenter)
    fastScreenRadioButton = QRadioButton("Fast and easy screen for any kind of animal.", self)
    fastScreenRadioButton.setChecked(True)
    layout.addWidget(fastScreenRadioButton, alignment=Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(QLabel("Only one animal per well/tank/arena. Center of mass tracking only. Very fast Tracking. Good for genetic and drug screens.", self), alignment=Qt.AlignmentFlag.AlignCenter)
    freeZebraRadioButton = QRadioButton("Track heads and tails of freely swimming fish.", self)
    layout.addWidget(freeZebraRadioButton, alignment=Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(QLabel("Multiple fish can be tracked in the same well but the tail tracking can be mediocre when fish collide. Each well should contain the same number of fish.", self), alignment=Qt.AlignmentFlag.AlignCenter)
    headEmbZebraRadioButton = QRadioButton("Track tail of one head embedded zebrafish larva.", self)
    layout.addWidget(headEmbZebraRadioButton, alignment=Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(QLabel("", self), alignment=Qt.AlignmentFlag.AlignCenter)
    otherRadioButton = QRadioButton("Track centers of mass of any kind of animal.", self)
    layout.addWidget(otherRadioButton, alignment=Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(QLabel('Several animals can be tracked at once in the same well/tank/arena. Each well should contain the same number of animals.', self), alignment=Qt.AlignmentFlag.AlignCenter)

    buttonsLayout = QHBoxLayout()
    buttonsLayout.addStretch()
    backBtn = util.apply_style(QPushButton("Back", self), background_color=util.LIGHT_YELLOW)
    backBtn.setObjectName("back")
    buttonsLayout.addWidget(backBtn, alignment=Qt.AlignmentFlag.AlignCenter)
    startPageBtn = util.apply_style(QPushButton("Go to the start page", self), background_color=util.LIGHT_CYAN)
    startPageBtn.clicked.connect(lambda: controller.show_frame("StartPage"))
    buttonsLayout.addWidget(startPageBtn, alignment=Qt.AlignmentFlag.AlignCenter)
    nextBtn = util.apply_style(QPushButton("Next", self), background_color=util.LIGHT_YELLOW)
    nextBtn.clicked.connect(lambda: controller.chooseGeneralExperimentFirstStep(controller, freeZebraRadioButton.isChecked(), headEmbZebraRadioButton.isChecked(), False, False, otherRadioButton.isChecked(), fastScreenRadioButton.isChecked()))
    buttonsLayout.addWidget(nextBtn, alignment=Qt.AlignmentFlag.AlignCenter)
    buttonsLayout.addStretch()
    layout.addLayout(buttonsLayout)

    self.setLayout(layout)


class FreelySwimmingExperiment(QWidget):
  def __init__(self, controller):
    super().__init__(controller.window)
    self.controller = controller
    self.preferredSize = (750, 500)

    layout = QVBoxLayout()
    layout.addWidget(util.apply_style(QLabel("Prepare Config File for Freely Swimming Fish:", self), font=controller.title_font), alignment=Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(util.apply_style(QLabel("Choose only one of the options below:", self), font=QFont("Helvetica", 12)), alignment=Qt.AlignmentFlag.AlignCenter)
    freeZebra2RadioButton = QRadioButton("Recommended method: Automatic Parameters Setting", self)
    freeZebra2RadioButton.setChecked(True)
    layout.addWidget(freeZebra2RadioButton, alignment=Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(QLabel("This method will work well on most videos. One exception can be for fish of very different sizes.", self), alignment=Qt.AlignmentFlag.AlignCenter)
    freeZebraRadioButton = QRadioButton("Alternative method: Manual Parameters Setting", self)
    layout.addWidget(freeZebraRadioButton, alignment=Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(QLabel("It's more difficult to create a configuration file with this method, but it can sometimes be useful as an alternative.", self), alignment=Qt.AlignmentFlag.AlignCenter)

    buttonsLayout = QHBoxLayout()
    buttonsLayout.addStretch()
    backBtn = util.apply_style(QPushButton("Back", self), background_color=util.LIGHT_YELLOW)
    backBtn.setObjectName("back")
    buttonsLayout.addWidget(backBtn, alignment=Qt.AlignmentFlag.AlignCenter)
    startPageBtn = util.apply_style(QPushButton("Go to the start page", self), background_color=util.LIGHT_CYAN)
    startPageBtn.clicked.connect(lambda: controller.show_frame("StartPage"))
    buttonsLayout.addWidget(startPageBtn, alignment=Qt.AlignmentFlag.AlignCenter)
    nextBtn = util.apply_style(QPushButton("Next", self), background_color=util.LIGHT_YELLOW)
    nextBtn.clicked.connect(lambda: util.addToHistory(controller.chooseGeneralExperiment)(controller, freeZebraRadioButton.isChecked(), 0, 0, 0, 0, freeZebra2RadioButton.isChecked()))
    buttonsLayout.addWidget(nextBtn, alignment=Qt.AlignmentFlag.AlignCenter)
    buttonsLayout.addStretch()
    layout.addLayout(buttonsLayout)

    self.setLayout(layout)


class WellOrganisation(QWidget):
  def __init__(self, controller):
    super().__init__(controller.window)
    self.controller = controller
    self.preferredSize = (1152, 768)

    layout = QVBoxLayout()
    layout.addWidget(util.apply_style(QLabel("Prepare Config File", self), font=controller.title_font), alignment=Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(util.apply_style(QLabel("Choose only one of the options below:", self), font=QFont("Helvetica", 12)), alignment=Qt.AlignmentFlag.AlignCenter)
    multipleROIsRadioButton = QRadioButton("Multiple rectangular regions of interest chosen at runtime", self)
    multipleROIsRadioButton.setChecked(True)
    layout.addWidget(multipleROIsRadioButton, alignment=Qt.AlignmentFlag.AlignCenter)
    otherRadioButton = QRadioButton("Whole video", self)
    layout.addWidget(otherRadioButton, alignment=Qt.AlignmentFlag.AlignCenter)
    roiRadioButton = QRadioButton("One rectangular region of interest fixed in the configuration file", self)
    layout.addWidget(roiRadioButton, alignment=Qt.AlignmentFlag.AlignCenter)
    groupSameSizeAndShapeEquallySpacedWellsRadioButton = QRadioButton("Group of multiple same size and shape equally spaced wells", self)
    layout.addWidget(groupSameSizeAndShapeEquallySpacedWellsRadioButton, alignment=Qt.AlignmentFlag.AlignCenter)
    circularRadioButton = QRadioButton("Circular wells (beta version)", self)
    layout.addWidget(circularRadioButton, alignment=Qt.AlignmentFlag.AlignCenter)
    rectangularRadioButton = QRadioButton("Rectangular wells (beta version)", self)
    layout.addWidget(rectangularRadioButton, alignment=Qt.AlignmentFlag.AlignCenter)

    buttonsLayout = QHBoxLayout()
    buttonsLayout.addStretch()
    backBtn = util.apply_style(QPushButton("Back", self), background_color=util.LIGHT_YELLOW)
    backBtn.setObjectName("back")
    buttonsLayout.addWidget(backBtn, alignment=Qt.AlignmentFlag.AlignCenter)
    startPageBtn = util.apply_style(QPushButton("Go to the start page", self), background_color=util.LIGHT_CYAN)
    startPageBtn.clicked.connect(lambda: controller.show_frame("StartPage"))
    buttonsLayout.addWidget(startPageBtn, alignment=Qt.AlignmentFlag.AlignCenter)
    nextBtn = util.apply_style(QPushButton("Next", self), background_color=util.LIGHT_YELLOW)
    nextBtn.clicked.connect(lambda: controller.wellOrganisation(controller, circularRadioButton.isChecked(), rectangularRadioButton.isChecked(), roiRadioButton.isChecked(), otherRadioButton.isChecked(), multipleROIsRadioButton.isChecked(), groupSameSizeAndShapeEquallySpacedWellsRadioButton.isChecked()))
    buttonsLayout.addWidget(nextBtn, alignment=Qt.AlignmentFlag.AlignCenter)
    buttonsLayout.addStretch()
    layout.addLayout(buttonsLayout)

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
    backBtn = util.apply_style(QPushButton("Back", self), background_color=util.LIGHT_YELLOW)
    backBtn.setObjectName("back")
    buttonsLayout.addWidget(backBtn, alignment=Qt.AlignmentFlag.AlignCenter)
    startPageBtn = util.apply_style(QPushButton("Go to the start page", self), background_color=util.LIGHT_CYAN)
    startPageBtn.clicked.connect(lambda: controller.show_frame("StartPage"))
    buttonsLayout.addWidget(startPageBtn, alignment=Qt.AlignmentFlag.AlignCenter)
    nextBtn = util.apply_style(QPushButton("Next", self), background_color=util.LIGHT_YELLOW)
    nextBtn.clicked.connect(lambda: controller.regionsOfInterest(controller, int(nbwells.text())))
    buttonsLayout.addWidget(nextBtn, alignment=Qt.AlignmentFlag.AlignCenter)
    buttonsLayout.addStretch()
    layout.addLayout(buttonsLayout)

    self.setLayout(layout)


class HomegeneousWellsLayout(QWidget):
  def __init__(self, controller):
    super().__init__(controller.window)
    self.controller = controller
    self.preferredSize = (1152, 768)

    layout = QVBoxLayout()
    layout.addWidget(util.apply_style(QLabel("Prepare Config File", self), font=controller.title_font), alignment=Qt.AlignmentFlag.AlignCenter)

    layout.addWidget(util.apply_style(QLabel("How many wells are there in your video?", self), font=QFont("Helvetica", 10)), alignment=Qt.AlignmentFlag.AlignCenter)
    nbwells = QLineEdit(controller.window)
    nbwells.setValidator(QIntValidator(nbwells))
    nbwells.validator().setBottom(0)
    layout.addWidget(nbwells, alignment=Qt.AlignmentFlag.AlignCenter)

    layout.addWidget(util.apply_style(QLabel("How many rows of wells are there in your video? (leave blank for default of 1)", self), font=QFont("Helvetica", 10)), alignment=Qt.AlignmentFlag.AlignCenter)
    nbRowsOfWells = QLineEdit(controller.window)
    nbRowsOfWells.setValidator(QIntValidator(nbRowsOfWells))
    nbRowsOfWells.validator().setBottom(0)
    layout.addWidget(nbRowsOfWells, alignment=Qt.AlignmentFlag.AlignCenter)

    layout.addWidget(util.apply_style(QLabel("How many wells are there per row on your video? (leave blank for default of 4)", self), font=QFont("Helvetica", 10)), alignment=Qt.AlignmentFlag.AlignCenter)
    nbWellsPerRows = QLineEdit(controller.window)
    nbWellsPerRows.setValidator(QIntValidator(nbWellsPerRows))
    nbWellsPerRows.validator().setBottom(0)
    layout.addWidget(nbWellsPerRows, alignment=Qt.AlignmentFlag.AlignCenter)

    finishBtn = util.apply_style(QPushButton("Finish now", self), background_color=util.LIGHT_YELLOW)
    finishBtn.clicked.connect(lambda: controller.homegeneousWellsLayout(controller, nbwells.text(), nbRowsOfWells.text(), nbWellsPerRows.text()))
    layout.addWidget(finishBtn, alignment=Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(QLabel('The tracking will work nicely in many cases when choosing this option.', self), alignment=Qt.AlignmentFlag.AlignCenter)

    adjustBtn = util.apply_style(QPushButton("Adjust Parameters futher", self), background_color=util.LIGHT_YELLOW)
    adjustBtn.clicked.connect(lambda: controller.morePreciseFastScreen(controller, nbwells.text(), nbRowsOfWells.text(), nbWellsPerRows.text()))
    layout.addWidget(adjustBtn, alignment=Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(QLabel('Choosing this option will lead to a higher probability that the tracking will work well.', self), alignment=Qt.AlignmentFlag.AlignCenter)

    linkBtn1 = util.apply_style(QPushButton("Alternative", self), background_color=util.GOLD)
    linkBtn1.clicked.connect(lambda: webbrowser.open_new("https://github.com/oliviermirat/ZebraZoom/blob/master/FastScreenTrackingGuidlines.md"))
    layout.addWidget(linkBtn1, alignment=Qt.AlignmentFlag.AlignCenter)

    buttonsLayout = QHBoxLayout()
    buttonsLayout.addStretch()
    backBtn = util.apply_style(QPushButton("Back", self), background_color=util.LIGHT_YELLOW)
    backBtn.setObjectName("back")
    buttonsLayout.addWidget(backBtn, alignment=Qt.AlignmentFlag.AlignCenter)
    startPageBtn = util.apply_style(QPushButton("Go to the start page", self), background_color=util.LIGHT_CYAN)
    startPageBtn.clicked.connect(lambda: controller.show_frame("StartPage"))
    buttonsLayout.addWidget(startPageBtn, alignment=Qt.AlignmentFlag.AlignCenter)
    buttonsLayout.addStretch()
    layout.addLayout(buttonsLayout)

    self.setLayout(layout)


class CircularOrRectangularWells(QWidget):
  def __init__(self, controller):
    super().__init__(controller.window)
    self.controller = controller
    self.preferredSize = (750, 500)

    layout = QVBoxLayout()
    layout.addWidget(util.apply_style(QLabel("Prepare Config File", self), font=controller.title_font), alignment=Qt.AlignmentFlag.AlignCenter)

    layout.addWidget(util.apply_style(QLabel("How many wells are there in your video?", self), font=QFont("Helvetica", 10)), alignment=Qt.AlignmentFlag.AlignCenter)
    nbwells = QLineEdit(controller.window)
    nbwells.setValidator(QIntValidator(nbwells))
    nbwells.validator().setBottom(0)
    layout.addWidget(nbwells, alignment=Qt.AlignmentFlag.AlignCenter)

    layout.addWidget(util.apply_style(QLabel("How many rows of wells are there in your video? (leave blank for default of 1)", self), font=QFont("Helvetica", 10)), alignment=Qt.AlignmentFlag.AlignCenter)
    nbRowsOfWells = QLineEdit(controller.window)
    nbRowsOfWells.setValidator(QIntValidator(nbRowsOfWells))
    nbRowsOfWells.validator().setBottom(0)
    layout.addWidget(nbRowsOfWells, alignment=Qt.AlignmentFlag.AlignCenter)

    layout.addWidget(util.apply_style(QLabel("How many wells are there per row on your video? (leave blank for default of 4)", self), font=QFont("Helvetica", 10)), alignment=Qt.AlignmentFlag.AlignCenter)
    nbWellsPerRows = QLineEdit(controller.window)
    nbWellsPerRows.setValidator(QIntValidator(nbWellsPerRows))
    nbWellsPerRows.validator().setBottom(0)
    layout.addWidget(nbWellsPerRows, alignment=Qt.AlignmentFlag.AlignCenter)

    buttonsLayout = QHBoxLayout()
    buttonsLayout.addStretch()
    backBtn = util.apply_style(QPushButton("Back", self), background_color=util.LIGHT_YELLOW)
    backBtn.setObjectName("back")
    buttonsLayout.addWidget(backBtn, alignment=Qt.AlignmentFlag.AlignCenter)
    startPageBtn = util.apply_style(QPushButton("Go to the start page", self), background_color=util.LIGHT_CYAN)
    startPageBtn.clicked.connect(lambda: controller.show_frame("StartPage"))
    buttonsLayout.addWidget(startPageBtn, alignment=Qt.AlignmentFlag.AlignCenter)
    nextBtn = util.apply_style(QPushButton("Next", self), background_color=util.LIGHT_YELLOW)
    nextBtn.clicked.connect(lambda: controller.circularOrRectangularWells(controller, nbwells.text(), nbRowsOfWells.text(), nbWellsPerRows.text()))
    buttonsLayout.addWidget(nextBtn, alignment=Qt.AlignmentFlag.AlignCenter)
    buttonsLayout.addStretch()
    layout.addLayout(buttonsLayout)

    self.setLayout(layout)


class ChooseCircularWellsLeft(QWidget):
  def __init__(self, controller):
    super().__init__(controller.window)
    self.controller = controller

    layout = QVBoxLayout()
    layout.addWidget(util.apply_style(QLabel("Prepare Config File", self), font=controller.title_font), alignment=Qt.AlignmentFlag.AlignCenter)

    button = QPushButton("Click on the left inner border of the top left well", self)
    button.clicked.connect(lambda: controller.chooseCircularWellsLeft(controller))
    layout.addWidget(button, alignment=Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(util.apply_style(QLabel("Example:", self), font=QFont("Helvetica", 10)), alignment=Qt.AlignmentFlag.AlignCenter)
    cur_dir_path = os.path.dirname(os.path.realpath(__file__))
    image = QLabel(self)
    image.setPixmap(QPixmap(os.path.join(cur_dir_path, 'leftborder.png')))
    layout.addWidget(image, alignment=Qt.AlignmentFlag.AlignCenter)

    buttonsLayout = QHBoxLayout()
    buttonsLayout.addStretch()
    backBtn = util.apply_style(QPushButton("Back", self), background_color=util.LIGHT_YELLOW)
    backBtn.setObjectName("back")
    buttonsLayout.addWidget(backBtn, alignment=Qt.AlignmentFlag.AlignCenter)
    startPageBtn = util.apply_style(QPushButton("Go to the start page", self), background_color=util.LIGHT_CYAN)
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

    button = QPushButton("Click on the right inner border of the top left well", self)
    button.clicked.connect(lambda: controller.chooseCircularWellsRight(controller))
    layout.addWidget(button, alignment=Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(util.apply_style(QLabel("Example:", self), font=QFont("Helvetica", 10)), alignment=Qt.AlignmentFlag.AlignCenter)
    cur_dir_path = os.path.dirname(os.path.realpath(__file__))
    image = QLabel(self)
    image.setPixmap(QPixmap(os.path.join(cur_dir_path, 'rightborder.png')))
    layout.addWidget(image, alignment=Qt.AlignmentFlag.AlignCenter)

    buttonsLayout = QHBoxLayout()
    buttonsLayout.addStretch()
    backBtn = util.apply_style(QPushButton("Back", self), background_color=util.LIGHT_YELLOW)
    backBtn.setObjectName("back")
    buttonsLayout.addWidget(backBtn, alignment=Qt.AlignmentFlag.AlignCenter)
    startPageBtn = util.apply_style(QPushButton("Go to the start page", self), background_color=util.LIGHT_CYAN)
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
    backBtn = util.apply_style(QPushButton("Back", self), background_color=util.LIGHT_YELLOW)
    backBtn.setObjectName("back")
    buttonsLayout.addWidget(backBtn, alignment=Qt.AlignmentFlag.AlignCenter)
    startPageBtn = util.apply_style(QPushButton("Go to the start page", self), background_color=util.LIGHT_CYAN)
    startPageBtn.clicked.connect(lambda: controller.show_frame("StartPage"))
    buttonsLayout.addWidget(startPageBtn, alignment=Qt.AlignmentFlag.AlignCenter)
    nextBtn = util.apply_style(QPushButton("Next", self), background_color=util.LIGHT_YELLOW)
    nextBtn.clicked.connect(lambda: controller.numberOfAnimals(controller, nbanimals.text(), yesRadioButton.isChecked(), noRadioButton.isChecked(), forceBlobMethodForHeadTrackingCheckbox.isChecked(), 0, 0, 0, 0, 0, 0, 0))
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

    layout.addWidget(util.apply_style(QLabel("What's the total number of animals in your video?", self), font_size='16px'), 1, 0, Qt.AlignmentFlag.AlignCenter)
    nbanimals = QLineEdit(controller.window)
    nbanimals.setValidator(QIntValidator(nbanimals))
    nbanimals.validator().setBottom(0)
    layout.addWidget(nbanimals, 2, 0, Qt.AlignmentFlag.AlignCenter)

    layout.addWidget(util.apply_style(QLabel("Are all of those animals ALWAYS visible throughout the video?", self), font_size='16px'), 1, 1, Qt.AlignmentFlag.AlignCenter)
    btnGroup1 = QButtonGroup(self)
    yesRadioButton = QRadioButton("Yes", self)
    btnGroup1.addButton(yesRadioButton)
    yesRadioButton.setChecked(True)
    layout.addWidget(yesRadioButton, 2, 1, Qt.AlignmentFlag.AlignCenter)
    noRadioButton = QRadioButton("No", self)
    btnGroup1.addButton(noRadioButton)
    layout.addWidget(noRadioButton, 3, 1, Qt.AlignmentFlag.AlignCenter)

    layout.addWidget(util.apply_style(QLabel("Do you want bouts of movement to be detected?", self), font_size='16px'), 4, 0, Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(QLabel("Warning: at the moment, the parameters related to the bouts detection are a little challenging to set.", self), 5, 0, Qt.AlignmentFlag.AlignCenter)
    btnGroup2 = QButtonGroup(self)
    yesBoutsRadioButton = QRadioButton("Yes", self)
    btnGroup2.addButton(yesBoutsRadioButton)
    yesBoutsRadioButton.setChecked(True)
    layout.addWidget(yesBoutsRadioButton, 6, 0, Qt.AlignmentFlag.AlignCenter)
    noBoutsRadioButton = QRadioButton("No", self)
    btnGroup2.addButton(noBoutsRadioButton)
    layout.addWidget(noBoutsRadioButton, 7, 0, Qt.AlignmentFlag.AlignCenter)

    layout.addWidget(util.apply_style(QLabel("Do you want bends and associated paramaters to be calculated?", self), font_size='16px'), 4, 1, Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(QLabel("Bends are the local minimum and maximum of the tail angle.", self), 5, 1, Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(QLabel("Bends are used to calculate parameters such as tail beat frequency.", self), 6, 1, Qt.AlignmentFlag.AlignCenter)

    linkBtn1 = QPushButton("You may need to further adjust these parameters afterwards: see documentation.", self)
    linkBtn1.clicked.connect(lambda: webbrowser.open_new("https://github.com/oliviermirat/ZebraZoom#hyperparametersTailAngleSmoothBoutsAndBendsDetect"))
    layout.addWidget(linkBtn1, 7, 1, Qt.AlignmentFlag.AlignCenter)
    btnGroup3 = QButtonGroup(self)
    yesBendsRadioButton = QRadioButton("Yes", self)
    btnGroup3.addButton(yesBendsRadioButton)
    yesBendsRadioButton.setChecked(True)
    layout.addWidget(yesBendsRadioButton, 8, 1, Qt.AlignmentFlag.AlignCenter)
    noBendsRadioButton = QRadioButton("No", self)
    btnGroup3.addButton(noBendsRadioButton)
    layout.addWidget(noBendsRadioButton, 9, 1, Qt.AlignmentFlag.AlignCenter)

    layout.addWidget(util.apply_style(QLabel("Tail tracking: Choose an option below:", self), font_size='16px'), 8, 0, Qt.AlignmentFlag.AlignCenter)
    btnGroup4 = QButtonGroup(self)
    recommendedMethodRadioButton = QRadioButton("Recommended Method: Fast Tracking but tail tip might be detected too soon along the tail", self)
    btnGroup4.addButton(recommendedMethodRadioButton)
    recommendedMethodRadioButton.setChecked(True)
    layout.addWidget(recommendedMethodRadioButton, 9, 0, Qt.AlignmentFlag.AlignCenter)
    alternativeMethodRadioButton = QRadioButton("Alternative Method: Slower Tracker but tail tip MIGHT be detected more acurately", self)
    btnGroup4.addButton(alternativeMethodRadioButton)
    layout.addWidget(alternativeMethodRadioButton, 10, 0, Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(util.apply_style(QLabel("Once your configuration is created, you can switch from one method to the other", self), font=QFont("Helvetica", 10)), 11, 0, Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(util.apply_style(QLabel("by changing the value of the parameter recalculateForegroundImageBasedOnBodyArea", self), font=QFont("Helvetica", 10)), 12, 0, Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(util.apply_style(QLabel("in your config file between 0 and 1.", self), font=QFont("Helvetica", 10)), 13, 0, Qt.AlignmentFlag.AlignCenter)

    layout.addWidget(util.apply_style(QLabel("Tracking: Choose an option below:", self), font_size='16px'), 10, 1, Qt.AlignmentFlag.AlignCenter)
    btnGroup5 = QButtonGroup(self)
    recommendedTrackingMethodRadioButton = QRadioButton("Recommended Method in most cases: Slower Tracking but often more accurate.", self)
    btnGroup5.addButton(recommendedTrackingMethodRadioButton)
    recommendedTrackingMethodRadioButton.setChecked(True)
    layout.addWidget(recommendedTrackingMethodRadioButton, 11, 1, Qt.AlignmentFlag.AlignCenter)
    alternativeTrackingMethodRadioButton = QRadioButton("Alternative Method: Faster tracking, sometimes less accurate.", self)
    btnGroup5.addButton(alternativeTrackingMethodRadioButton)
    layout.addWidget(alternativeTrackingMethodRadioButton, 12, 1, Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(util.apply_style(QLabel("The alternative method can also work better for animals of different sizes.", self), font=QFont("Helvetica", 10)), 13, 1, Qt.AlignmentFlag.AlignCenter)

    buttonsLayout = QHBoxLayout()
    buttonsLayout.addStretch()
    backBtn = util.apply_style(QPushButton("Back", self), background_color=util.LIGHT_YELLOW)
    backBtn.setObjectName("back")
    buttonsLayout.addWidget(backBtn, alignment=Qt.AlignmentFlag.AlignCenter)
    startPageBtn = util.apply_style(QPushButton("Go to the start page", self), background_color=util.LIGHT_CYAN)
    startPageBtn.clicked.connect(lambda: controller.show_frame("StartPage"))
    buttonsLayout.addWidget(startPageBtn, alignment=Qt.AlignmentFlag.AlignCenter)
    nextBtn = util.apply_style(QPushButton("Ok, next step", self), background_color=util.LIGHT_YELLOW)
    nextBtn.clicked.connect(lambda: controller.numberOfAnimals(controller, nbanimals.text(), yesRadioButton.isChecked(), noRadioButton.isChecked(), 0, yesBoutsRadioButton.isChecked(), noBoutsRadioButton.isChecked(), recommendedMethodRadioButton.isChecked(), alternativeMethodRadioButton.isChecked(), yesBendsRadioButton.isChecked(), noBendsRadioButton.isChecked(), recommendedTrackingMethodRadioButton.isChecked()))
    buttonsLayout.addWidget(nextBtn, alignment=Qt.AlignmentFlag.AlignCenter)
    buttonsLayout.addStretch()
    layout.addLayout(buttonsLayout, 14, 0, 1, 2)

    self.setLayout(layout)


class NumberOfAnimalsCenterOfMass(QWidget):
  def __init__(self, controller):
    super().__init__(controller.window)
    self.controller = controller
    self.preferredSize = (1152, 768)

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

    method1Btn = QPushButton("Automatic Parameters Setting, Method 1: Slower tracking but often more accurate", self)
    method1Btn.clicked.connect(lambda: controller.numberOfAnimals(controller, nbanimals.text(), yesRadioButton.isChecked(), noRadioButton.isChecked(), 0, 0, 0, 1, 0, 0, 0, 1))
    layout.addWidget(method1Btn, alignment=Qt.AlignmentFlag.AlignCenter)
    method2Btn = QPushButton("Automatic Parameters Setting, Method 2: Faster tracking but often less accurate", self)
    method2Btn.clicked.connect(lambda: controller.numberOfAnimals(controller, nbanimals.text(), yesRadioButton.isChecked(), noRadioButton.isChecked(), 0, 0, 0, 1, 0, 0, 0, 0))
    layout.addWidget(method2Btn, alignment=Qt.AlignmentFlag.AlignCenter)
    manualBtn = QPushButton("Manual Parameters Setting: More control over the choice of parameters", self)
    manualBtn.clicked.connect(lambda: controller.numberOfAnimals(controller, nbanimals.text(), yesRadioButton.isChecked(), noRadioButton.isChecked(), 0, 0, 0, 0, 1, 0, 0, 0))
    layout.addWidget(manualBtn, alignment=Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(util.apply_style(QLabel("Try the 'Automatic Parameters Setting, Method 1' first. If it doesn't work, try the other methods.", self), font=QFont("Helvetica", 10)), alignment=Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(util.apply_style(QLabel("The 'Manual Parameter Settings' makes setting parameter slightly more challenging but offers more control over the choice of parameters.", self), font=QFont("Helvetica", 10)), alignment=Qt.AlignmentFlag.AlignCenter)

    buttonsLayout = QHBoxLayout()
    buttonsLayout.addStretch()
    backBtn = util.apply_style(QPushButton("Back", self), background_color=util.LIGHT_YELLOW)
    backBtn.setObjectName("back")
    buttonsLayout.addWidget(backBtn, alignment=Qt.AlignmentFlag.AlignCenter)
    startPageBtn = util.apply_style(QPushButton("Go to the start page", self), background_color=util.LIGHT_CYAN)
    startPageBtn.clicked.connect(lambda: controller.show_frame("StartPage"))
    buttonsLayout.addWidget(startPageBtn, alignment=Qt.AlignmentFlag.AlignCenter)
    buttonsLayout.addStretch()
    layout.addLayout(buttonsLayout)

    self.setLayout(layout)


class IdentifyHeadCenter(QWidget):
  def __init__(self, controller):
    super().__init__(controller.window)
    self.controller = controller

    layout = QVBoxLayout()
    layout.addWidget(util.apply_style(QLabel("Prepare Config File", self), font=controller.title_font), alignment=Qt.AlignmentFlag.AlignCenter)

    button = QPushButton("Click on the center of the head of a zebrafish", self)
    button.clicked.connect(lambda: controller.chooseHeadCenter(controller))
    layout.addWidget(button, alignment=Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(util.apply_style(QLabel("Example:", self), font=QFont("Helvetica", 10)), alignment=Qt.AlignmentFlag.AlignCenter)
    cur_dir_path = os.path.dirname(os.path.realpath(__file__))
    image = QLabel(self)
    image.setPixmap(QPixmap(os.path.join(cur_dir_path, 'blobCenter.png')))
    layout.addWidget(image, alignment=Qt.AlignmentFlag.AlignCenter)

    buttonsLayout = QHBoxLayout()
    buttonsLayout.addStretch()
    backBtn = util.apply_style(QPushButton("Back", self), background_color=util.LIGHT_YELLOW)
    backBtn.setObjectName("back")
    buttonsLayout.addWidget(backBtn, alignment=Qt.AlignmentFlag.AlignCenter)
    startPageBtn = util.apply_style(QPushButton("Go to the start page", self), background_color=util.LIGHT_CYAN)
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

    button = QPushButton("Click on the tip of the tail of the same zebrafish.", self)
    button.clicked.connect(lambda: controller.chooseBodyExtremity(controller))
    layout.addWidget(button, alignment=Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(util.apply_style(QLabel("Example:", self), font=QFont("Helvetica", 10)), alignment=Qt.AlignmentFlag.AlignCenter)
    cur_dir_path = os.path.dirname(os.path.realpath(__file__))
    image = QLabel(self)
    image.setPixmap(QPixmap(os.path.join(cur_dir_path, 'blobExtremity.png')))
    layout.addWidget(image, alignment=Qt.AlignmentFlag.AlignCenter)

    buttonsLayout = QHBoxLayout()
    buttonsLayout.addStretch()
    backBtn = util.apply_style(QPushButton("Back", self), background_color=util.LIGHT_YELLOW)
    backBtn.setObjectName("back")
    buttonsLayout.addWidget(backBtn, alignment=Qt.AlignmentFlag.AlignCenter)
    startPageBtn = util.apply_style(QPushButton("Go to the start page", self), background_color=util.LIGHT_CYAN)
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
    backBtn = util.apply_style(QPushButton("Back", self), background_color=util.LIGHT_YELLOW)
    backBtn.setObjectName("back")
    buttonsLayout.addWidget(backBtn, alignment=Qt.AlignmentFlag.AlignCenter)
    startPageBtn = util.apply_style(QPushButton("Go to the start page", self), background_color=util.LIGHT_CYAN)
    startPageBtn.clicked.connect(lambda: controller.show_frame("StartPage"))
    buttonsLayout.addWidget(startPageBtn, alignment=Qt.AlignmentFlag.AlignCenter)
    nextBtn = util.apply_style(QPushButton("Next", self), background_color=util.LIGHT_YELLOW)
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
    testCheckbox = QCheckBox("Test tracking after saving config", self)
    testCheckbox.setChecked(True)
    testCheckbox.clearFocus()
    layout.addWidget(testCheckbox, alignment=Qt.AlignmentFlag.AlignCenter)
    saveBtn = util.apply_style(QPushButton("Save Config File", self), background_color=util.LIGHT_YELLOW)
    saveBtn.clicked.connect(lambda: controller.finishConfig(testCheckbox.isChecked()))
    layout.addWidget(saveBtn, alignment=Qt.AlignmentFlag.AlignCenter)
    buttonsLayout = QHBoxLayout()
    buttonsLayout.addStretch()
    backBtn = util.apply_style(QPushButton("Back", self), background_color=util.LIGHT_YELLOW)
    backBtn.setObjectName("back")
    buttonsLayout.addWidget(backBtn, alignment=Qt.AlignmentFlag.AlignCenter)
    startPageBtn = util.apply_style(QPushButton("Go to the start page", self), background_color=util.LIGHT_CYAN)
    startPageBtn.clicked.connect(lambda: controller.show_frame("StartPage"))
    buttonsLayout.addWidget(startPageBtn, alignment=Qt.AlignmentFlag.AlignCenter)
    buttonsLayout.addStretch()
    layout.addStretch()
    layout.addLayout(buttonsLayout)

    self.setLayout(layout)
