from PyQt5.QtCore import Qt
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import QLabel, QWidget, QPushButton, QHBoxLayout, QVBoxLayout, QRadioButton, QButtonGroup

import zebrazoom.code.util as util


class HeadEmbeded(QWidget):
  def __init__(self, controller):
    super().__init__(controller.window)
    self.controller = controller
    self.preferredSize = (1152, 768)

    layout = QVBoxLayout()
    layout.addWidget(util.apply_style(QLabel("Prepare Config File", self), font=controller.title_font), alignment=Qt.AlignmentFlag.AlignCenter)

    layout.addWidget(util.apply_style(QLabel("Choose only one of the options below:", self), font=QFont("Helvetica", 12)), alignment=Qt.AlignmentFlag.AlignCenter)
    btnGroup1 = QButtonGroup(self)
    blackBackRadioButton = QRadioButton("Black background, white zebrafish.", self)
    btnGroup1.addButton(blackBackRadioButton)
    blackBackRadioButton.setChecked(True)
    layout.addWidget(blackBackRadioButton, alignment=Qt.AlignmentFlag.AlignCenter)
    whiteBackRadioButton = QRadioButton("White background, black zebrafish.", self)
    btnGroup1.addButton(whiteBackRadioButton)
    layout.addWidget(whiteBackRadioButton, alignment=Qt.AlignmentFlag.AlignCenter)

    layout.addWidget(util.apply_style(QLabel("Do you want ZebraZoom to detect bouts of movement?", self), font=QFont("Helvetica", 12)), alignment=Qt.AlignmentFlag.AlignCenter)
    btnGroup2 = QButtonGroup(self)
    noBoutDetectRadioButton = QRadioButton("No. I want the tracking data for all frames of the videos.", self)
    btnGroup2.addButton(noBoutDetectRadioButton)
    noBoutDetectRadioButton.setChecked(True)
    layout.addWidget(noBoutDetectRadioButton, alignment=Qt.AlignmentFlag.AlignCenter)
    boutDetectionRadioButton = QRadioButton("Yes. I want the tracking data only when the fish is moving.", self)
    btnGroup2.addButton(boutDetectionRadioButton)
    layout.addWidget(boutDetectionRadioButton, alignment=Qt.AlignmentFlag.AlignCenter)

    layout.addWidget(util.apply_style(QLabel("Do you want to try to tweak tracking parameters further?", self), font=QFont("Helvetica", 12)), alignment=Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(QLabel("Warning: further tweaking tracking parameters could make tracking results worse; please try without this option first.", self), alignment=Qt.AlignmentFlag.AlignCenter)
    btnGroup3 = QButtonGroup(self)
    tweakTrackingParamsYesRadioButton = QRadioButton("Yes", self)
    btnGroup3.addButton(tweakTrackingParamsYesRadioButton)
    tweakTrackingParamsYesRadioButton.setChecked(True)
    layout.addWidget(tweakTrackingParamsYesRadioButton, alignment=Qt.AlignmentFlag.AlignCenter)
    tweakTrackingParamsNoRadioButton = QRadioButton("No", self)
    btnGroup3.addButton(tweakTrackingParamsNoRadioButton)
    layout.addWidget(tweakTrackingParamsNoRadioButton, alignment=Qt.AlignmentFlag.AlignCenter)

    buttonsLayout = QHBoxLayout()
    buttonsLayout.addStretch()
    backBtn = QPushButton("Back", self)
    backBtn.setObjectName("back")
    buttonsLayout.addWidget(backBtn, alignment=Qt.AlignmentFlag.AlignCenter)
    startPageBtn = QPushButton("Go to the start page", self)
    startPageBtn.clicked.connect(lambda: controller.show_frame("StartPage"))
    buttonsLayout.addWidget(startPageBtn, alignment=Qt.AlignmentFlag.AlignCenter)
    nextBtn = util.apply_style(QPushButton("Next", self), background_color=util.DEFAULT_BUTTON_COLOR)
    nextBtn.clicked.connect(lambda: controller.headEmbededGUI(controller, blackBackRadioButton.isChecked(), whiteBackRadioButton.isChecked(), noBoutDetectRadioButton.isChecked(), boutDetectionRadioButton.isChecked(), tweakTrackingParamsYesRadioButton.isChecked(), tweakTrackingParamsNoRadioButton.isChecked()))
    buttonsLayout.addWidget(nextBtn, alignment=Qt.AlignmentFlag.AlignCenter)
    buttonsLayout.addStretch()
    layout.addLayout(buttonsLayout)

    self.setLayout(layout)
