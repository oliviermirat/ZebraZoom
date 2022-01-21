import webbrowser

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QIntValidator
from PyQt6.QtWidgets import QLabel, QWidget, QPushButton, QLineEdit, QCheckBox, QVBoxLayout, QRadioButton, QButtonGroup


LIGHT_CYAN = '#E0FFFF'
GOLD = '#FFD700'


def apply_style(widget, **kwargs):
    if (font := kwargs.pop('font', None)) is not None:
        widget.setFont(font)
    widget.setStyleSheet(';'.join('%s: %s' % (prop.replace('_', '-'), val)  for prop, val in kwargs.items()))
    return widget


class ChooseVideoToTroubleshootSplitVideo(QWidget):
  def __init__(self, controller):
    super().__init__(controller.window)
    self.controller = controller

    layout = QVBoxLayout()
    layout.addWidget(apply_style(QLabel("Troubleshooting.", self), font=controller.title_font), alignment=Qt.AlignmentFlag.AlignCenter)
    linkBtn = apply_style(QPushButton("First View Tracking Troubleshooting Tips", self), background_color=GOLD)
    linkBtn.clicked.connect(lambda: webbrowser.open_new("https://github.com/oliviermirat/ZebraZoom/blob/master/TrackingTroubleshooting.md"))
    layout.addWidget(linkBtn, alignment=Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(QLabel("If the previous tracking troubleshooting tips where not enough to solve the issue, you can create a smaller sub-video to send to ZebraZoom's developers for troubleshooting.", self), alignment=Qt.AlignmentFlag.AlignCenter)

    selectVideoBtn = QPushButton("Select the video to troubleshoot.", self)
    selectVideoBtn.clicked.connect(lambda: controller.chooseVideoToTroubleshootSplitVideo(controller))
    layout.addWidget(selectVideoBtn, alignment=Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(apply_style(QLabel("If you are having issues running the tracking on a video or creating a good configuration file for a video", self), font=QFont("Helvetica", 10)), alignment=Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(apply_style(QLabel("you can create a sub-video centered around a bout of movement and send this smaller sub-video to info@zebrazoom.org in order for us to help troubleshoot.", self), font=QFont("Helvetica", 10)), alignment=Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(apply_style(QLabel("Click on the button above to start this process.", self), font=QFont("Helvetica", 10)), alignment=Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(apply_style(QLabel("(if your video is light enough you can also send it to info@zebrazoom.org without reducing its size)", self), font=QFont("Helvetica", 10)), alignment=Qt.AlignmentFlag.AlignCenter)

    startPageBtn = apply_style(QPushButton("Go to the start page", self), background_color=LIGHT_CYAN)
    startPageBtn.clicked.connect(lambda: controller.show_frame("StartPage"))
    layout.addWidget(startPageBtn, alignment=Qt.AlignmentFlag.AlignCenter)

    self.setLayout(layout)


class VideoToTroubleshootSplitVideo(QWidget):
  def __init__(self, controller):
    super().__init__(controller.window)
    self.controller = controller

    layout = QVBoxLayout()
    layout.addWidget(apply_style(QLabel("Ok, your sub-video has been saved in the folder you chose. You can now send that sub-video to info@zebrazoom.org", self), font=QFont("Helvetica", 10)), alignment=Qt.AlignmentFlag.AlignCenter)
    startPageBtn = apply_style(QPushButton("Go to the start page", self), background_color=LIGHT_CYAN)
    startPageBtn.clicked.connect(lambda: controller.show_frame("StartPage"))
    layout.addWidget(startPageBtn, alignment=Qt.AlignmentFlag.AlignCenter)

    self.setLayout(layout)
