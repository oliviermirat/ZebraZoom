import atexit
import contextlib
import json
import math
import os
import subprocess
import sys
import webbrowser
from packaging import version

import matplotlib
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qtagg import FigureCanvas
from matplotlib.figure import Figure

from PyQt5.QtCore import pyqtSignal, Qt, QDir, QEvent, QLine, QObject, QPoint, QPointF, QRect, QSize, QSortFilterProxyModel, QTimer, QUrl
from PyQt5.QtGui import QColor, QCursor, QFont, QFontMetrics, QPainter, QPainterPath, QPolygonF
from PyQt5.QtNetwork import QNetworkAccessManager, QNetworkReply, QNetworkRequest
from PyQt5.QtWidgets import QApplication, QLabel, QWidget, QFileSystemModel, QFrame, QGridLayout, QHeaderView, QPushButton, QSizePolicy, QHBoxLayout, QVBoxLayout, QCheckBox, QScrollArea, QSpinBox, QComboBox, QTreeView, QToolTip
PYQT6 = False

import zebrazoom
import zebrazoom.code.paths as paths
import zebrazoom.code.util as util
from zebrazoom.code.readValidationVideo import readValidationVideo
from zebrazoom.code.checkConsistencyOfParameters import checkConsistencyOfParameters
from zebrazoom.code.GUI.GUI_InitialFunctions import chooseConfigFile, launchZebraZoom

LARGE_FONT= QFont("Verdana", 12)


class _FlowchartWidget(QWidget):
  circleHovered = pyqtSignal(int, int)

  _ARROW_SIZE = 10
  _TEXTS = ('Create Configuration File', 'Run Tracking', 'View Tracking Results', 'Analyze Behavior')

  def __init__(self):
    super().__init__()
    self._circleRects = []
    self._lines = []
    font = QFont()
    font.setPixelSize(16)
    fm = QFontMetrics(font)
    stepMinimumWidth = fm.boundingRect('Good Results').width() + self._ARROW_SIZE * 2 + 4  # add 4 pixels to ensure some spacing
    self.setFixedHeight(200)
    self.setContentsMargins(0, 4, 0, 4)
    self.setMouseTracking(True)

  def resizeEvent(self, evt):
    super().resizeEvent(evt)
    del self._circleRects[:]
    del self._lines[:]
    size = self.contentsRect()
    yOffset = 100
    midHeight = (size.height() - yOffset) // 2 + size.y() + yOffset
    stepSize = size.width() // 8
    for step, startPos in enumerate(range(size.x() + stepSize // 2, size.width() - stepSize, stepSize)):
      if step % 2:
        self._lines.append(QLine(startPos + stepSize, midHeight, startPos, midHeight))
      else:
        self._circleRects.append(QRect(startPos, size.y() + yOffset, stepSize, size.height() - yOffset))

  def iterCircleRects(self):
    yield from self._circleRects

  def _getArrow(self, p1, p2, angle):
    p1 = QPointF(p1)
    p2 = QPointF(p2)
    arrowP1 = p1 + QPointF(math.sin(angle + math.pi / 3) * self._ARROW_SIZE, math.cos(angle + math.pi / 3) * self._ARROW_SIZE)
    arrowP2 = p1 + QPointF(math.sin(angle + math.pi - math.pi / 3) * self._ARROW_SIZE, math.cos(angle + math.pi - math.pi / 3) * self._ARROW_SIZE)

    arrowHead = QPolygonF()
    arrowHead.clear()
    arrowHead.append(p1)
    arrowHead.append(arrowP1)
    arrowHead.append(arrowP2)
    return arrowHead

  def paintEvent(self, evt):
    super().paintEvent(evt)
    qp = QPainter()
    qp.begin(self)
    qp.setRenderHint(QPainter.RenderHint.Antialiasing, True)
    font = QFont()
    font.setPixelSize(16)
    qp.setFont(font)

    qp.setBrush(QColor(util.LIGHT_YELLOW))
    for rect, text in zip(self._circleRects, self._TEXTS):
      qp.drawEllipse(rect)
      qp.drawText(rect, Qt.AlignmentFlag.AlignCenter | Qt.TextFlag.TextWordWrap, text)

    qp.setBrush(QColor('black'))
    for line in self._lines:
      qp.drawLine(line)
      qp.drawPolygon(self._getArrow(line.p1(), line.p2(), math.atan2(-line.dy(), line.dx())))

    fontHeight = qp.fontMetrics().height() + 4  # add 4 pixels to ensure some spacing
    qp.setPen(QColor('green'))
    qp.drawText(QRect(QPoint(line.p1().x(), line.p1().y() - fontHeight), QPoint(line.p2().x() - self._ARROW_SIZE, line.p2().y())), Qt.AlignmentFlag.AlignCenter, 'Good Results')
    qp.setPen(QColor('red'))
    qp.drawText(QRect(QPoint(self._circleRects[1].x(), self.contentsRect().y()), QPoint(self._circleRects[1].x() + self._circleRects[1].width(), fontHeight)), Qt.AlignmentFlag.AlignCenter, 'Bad Results')

    qp.setPen(QColor('black'))
    p1 = QPointF(self._circleRects[0].x() + self._circleRects[0].width() // 2, self._circleRects[0].y())
    p2 = QPointF(self._circleRects[2].x() + self._circleRects[2].width() // 2, self._circleRects[2].y())
    c1 = QPointF(self._circleRects[0].width() // 2 + self._circleRects[0].x(), self.contentsRect().y())
    c2 = QPointF(self._circleRects[2].width() // 2 + self._circleRects[2].x(), self.contentsRect().y())
    path = QPainterPath(p1)
    path.cubicTo(c1, c2, p2)
    qp.drawPolygon(self._getArrow(p1, p2, math.radians(path.angleAtPercent(self._ARROW_SIZE / path.length()))))
    qp.setBrush(Qt.BrushStyle.NoBrush)
    qp.drawPath(path)
    qp.end()


class _ConfigurationDetails(QFrame):
  def __init__(self):
    super().__init__()
    self.setFrameShape(QFrame.Shape.WinPanel)
    self.setVisible(False)

    app = QApplication.instance()
    layout = QVBoxLayout()
    prepareConfigBtn = util.apply_style(QPushButton("Prepare initial configuration\nfile for tracking", self), background_color=util.LIGHT_YELLOW)
    prepareConfigBtn.clicked.connect(lambda: util.addToHistory(app.show_frame)("ChooseVideoToCreateConfigFileFor"))
    layout.addWidget(prepareConfigBtn, alignment=Qt.AlignmentFlag.AlignCenter)
    optimizeConfigBtn = util.apply_style(QPushButton("Optimize a previously\ncreated configuration file", self), background_color=util.LIGHT_YELLOW)
    optimizeConfigBtn.clicked.connect(lambda: app.chooseVideoToCreateConfigFileFor(app, True) and util.addToHistory(app.optimizeConfigFile)())
    layout.addWidget(optimizeConfigBtn, alignment=Qt.AlignmentFlag.AlignCenter)
    openConfigFolderBtn = util.apply_style(QPushButton("Open configuration file\nfolder", self), background_color=util.LIGHT_YELLOW)
    openConfigFolderBtn.clicked.connect(lambda: app.openConfigurationFileFolder(app.homeDirectory))
    layout.addWidget(openConfigFolderBtn, alignment=Qt.AlignmentFlag.AlignCenter)
    label = QLabel('A configuration file can be used to track not only the video that was used to create it, but also all videos similar enough to it.')
    label.setWordWrap(True)
    layout.addWidget(label, alignment=Qt.AlignmentFlag.AlignCenter)
    self.setLayout(layout)


class _TrackingDetails(QFrame):
  def __init__(self):
    super().__init__()
    self.setFrameShape(QFrame.Shape.WinPanel)
    self.setVisible(False)

    app = QApplication.instance()
    layout = QVBoxLayout()
    runTrackingOneVideoBtn = util.apply_style(QPushButton("Run ZebraZoom's Tracking\non a video", self), background_color=util.LIGHT_YELLOW)
    runTrackingOneVideoBtn.clicked.connect(lambda: app.show_frame("VideoToAnalyze"))
    layout.addWidget(runTrackingOneVideoBtn, alignment=Qt.AlignmentFlag.AlignCenter)
    oneVideoLabel = QLabel('Once your configuration file is ready, use it to run the tracking on one video.')
    oneVideoLabel.setWordWrap(True)
    layout.addWidget(oneVideoLabel, alignment=Qt.AlignmentFlag.AlignCenter)
    runTrackingMultipleVideosBtn = util.apply_style(QPushButton("Run ZebraZoom's Tracking\non several videos", self), background_color=util.LIGHT_YELLOW)
    runTrackingMultipleVideosBtn.clicked.connect(lambda: app.show_frame("SeveralVideos"))
    layout.addWidget(runTrackingMultipleVideosBtn, alignment=Qt.AlignmentFlag.AlignCenter)
    multipleVideosLabel = QLabel('If you got good tracking results for one video, you can then run the tracking on multiple videos as a batch.')
    multipleVideosLabel.setWordWrap(True)
    layout.addWidget(multipleVideosLabel, alignment=Qt.AlignmentFlag.AlignCenter)
    self.setLayout(layout)


class _VisualizationDetails(QFrame):
  def __init__(self):
    super().__init__()
    self.setFrameShape(QFrame.Shape.WinPanel)
    self.setVisible(False)

    app = QApplication.instance()
    layout = QVBoxLayout()
    self._visualizeOutputBtn = util.apply_style(QPushButton("Visualize tracking results", self), background_color=util.LIGHT_YELLOW)
    self._visualizeOutputBtn.clicked.connect(lambda: app.showViewParameters())
    layout.addWidget(self._visualizeOutputBtn, alignment=Qt.AlignmentFlag.AlignCenter)
    label = QLabel('Make sure that the tracking results are good enough. If they are not, adjust/optimize the configuration file you used.')
    label.setWordWrap(True)
    layout.addWidget(label, alignment=Qt.AlignmentFlag.AlignCenter)
    self._enhanceOutputBtn = util.apply_style(QPushButton("Enhance ZebraZoom's output", self), background_color=util.LIGHT_YELLOW)
    self._enhanceOutputBtn.clicked.connect(lambda: app.show_frame("EnhanceZZOutput"))
    layout.addWidget(self._enhanceOutputBtn, alignment=Qt.AlignmentFlag.AlignCenter)
    self.setLayout(layout)


class _AnalysisDetails(QFrame):
  def __init__(self):
    super().__init__()
    self.setFrameShape(QFrame.Shape.WinPanel)
    self.setVisible(False)

    app = QApplication.instance()
    layout = QVBoxLayout()
    self._analyzeOutputBtn = util.apply_style(QPushButton("Analyze ZebraZoom's output"), background_color=util.LIGHT_YELLOW)
    self._analyzeOutputBtn.clicked.connect(lambda: app.show_frame("CreateExperimentOrganizationExcel"))
    layout.addWidget(self._analyzeOutputBtn, alignment=Qt.AlignmentFlag.AlignCenter)
    analyzeOutputLabel = QLabel('Kinematic parameters analysis and unsupervised clustering are available right from the GUI!')
    analyzeOutputLabel.setWordWrap(True)
    layout.addWidget(analyzeOutputLabel, alignment=Qt.AlignmentFlag.AlignCenter)
    self._outputFolderBtn = util.apply_style(QPushButton("Open ZebraZoom's\noutput folder"), background_color=util.LIGHT_YELLOW)
    self._outputFolderBtn.clicked.connect(lambda: app.openZZOutputFolder(app.homeDirectory))
    layout.addWidget(self._outputFolderBtn, alignment=Qt.AlignmentFlag.AlignCenter)
    outputFolderLabel = QLabel('Go one step further: access the raw data and do your own analysis!')
    outputFolderLabel.setWordWrap(True)
    layout.addWidget(outputFolderLabel, alignment=Qt.AlignmentFlag.AlignCenter)
    self.setLayout(layout)


class StartPage(QWidget):
    def __init__(self, controller):
        super().__init__(controller.window)
        self.controller = controller
        self.setMouseTracking(True)
        self._detailsWidgets = (_ConfigurationDetails(), _TrackingDetails(), _VisualizationDetails(), _AnalysisDetails())
        self._shownDetail = None

        layout = QGridLayout()
        layout.setVerticalSpacing(20)
        self._titleLabel = util.apply_style(QLabel("Welcome to ZebraZoom!"), font=controller.title_font, color='purple')
        self._titleLabel.setSizePolicy(QSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed))
        layout.addWidget(self._titleLabel, 0, 0, 1, 4, Qt.AlignmentFlag.AlignHCenter)
        self._flowchart = _FlowchartWidget()
        layout.addWidget(self._flowchart, 1, 0, 1, 4)
        for idx, widget in enumerate(self._detailsWidgets):
          layout.addWidget(widget, 2, idx, alignment=Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop)
        for idx in range(layout.columnCount()):
          layout.setColumnStretch(idx, 1)

        bottomLayout = QHBoxLayout()
        self._selectZZoutputFolder = QPushButton("Select output folder")
        self._selectZZoutputFolder.clicked.connect(controller.askForZZoutputLocation)
        bottomLayout.addWidget(self._selectZZoutputFolder)
        self._troubleshootBtn = QPushButton("Troubleshoot")
        self._troubleshootBtn.clicked.connect(lambda: controller.show_frame("ChooseVideoToTroubleshootSplitVideo"))
        bottomLayout.addWidget(self._troubleshootBtn)
        self._documentationBtn = QPushButton("Documentation")
        self._documentationBtn.clicked.connect(lambda: webbrowser.open_new("https://zebrazoom.org/documentation/docs/intro/"))
        bottomLayout.addWidget(self._documentationBtn)
        self._updateStatusLabel = QLabel("Regularly update your version of ZebraZoom with: 'pip install zebrazoom --upgrade'!")
        bottomLayout.addWidget(self._updateStatusLabel)
        if getattr(sys, 'frozen', False):  # running an installed executable
            self._networkManager = QNetworkAccessManager()
            self._updateBtn = QPushButton('')
            bottomLayout.addWidget(self._updateBtn)
            QTimer.singleShot(0, self._checkForUpdates)
        layout.addLayout(bottomLayout, 2, 0, 1, 4, alignment=Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignBottom)

        self.setLayout(layout)

    def mouseMoveEvent(self, evt):
        super().mouseMoveEvent(evt)
        flowchartPos = self._flowchart.mapFromGlobal(evt.globalPosition() if PYQT6 else evt.globalPos())
        maxDetailY = max(map(lambda widget: widget.sizeHint().height(), self._detailsWidgets))

        for idx, circle in enumerate(self._flowchart.iterCircleRects()):
            if circle.y() <= flowchartPos.y() <= circle.y() + circle.height() + maxDetailY and \
                    circle.x() <= flowchartPos.x() <= circle.x() + circle.width():
                if self._shownDetail is not self._detailsWidgets[idx]:
                    if self._shownDetail is not None:
                        self._shownDetail.hide()
                    self._shownDetail = self._detailsWidgets[idx]
                    self._shownDetail.show()
                break
        else:
            if self._shownDetail is not None:
                self._shownDetail.hide()
                self._shownDetail = None

    def _launchUpdate(self):
        installationFolder = os.path.dirname(sys.executable)
        if sys.platform.startswith('win'):
          atexit.register(subprocess.Popen, os.path.join(installationFolder, 'updater', 'updater.exe'), shell=True)
        else:
          updaterExecutable = 'updater/updater'
          atexit.register(os.execl, updaterExecutable, updaterExecutable)
          atexit.register(os.chdir, installationFolder)
        sys.exit(0)

    def _refreshUpdateStatus(self):
        if self._reply.error() != QNetworkReply.NetworkError.NoError:
            self._updateStatusLabel.setText("Could not check for updates.")
            util.apply_style(self._updateStatusLabel, color='red')
            self._updateBtn.setText("Retry")
            self._updateBtn.show()
            self._updateBtn.disconnect()
            self._updateBtn.clicked.connect(self._checkForUpdates)
            self._reply = None
            return
        latestVersion = self._reply.url().toString().split('/')[-1]
        self._reply = None
        if version.parse(latestVersion) <= version.parse(zebrazoom.__version__):
            self._updateStatusLabel.setText("Using ZebraZoom version %s, no updates available." % zebrazoom.__version__)
            util.apply_style(self._updateStatusLabel, color='green')
            self._updateBtn.hide()
            return
        self._updateStatusLabel.setText("Using ZebraZoom version %s, updates are available (%s)." % (zebrazoom.__version__, latestVersion))
        util.apply_style(self._updateStatusLabel, color='red')
        self._updateBtn.setText("Update")
        self._updateBtn.show()
        self._updateBtn.disconnect()
        self._updateBtn.clicked.connect(self._launchUpdate)

    def _checkForUpdates(self):
        self._updateBtn.hide()
        self._updateStatusLabel.setText("Checking for updates...")
        util.apply_style(self._updateStatusLabel, color='orange')
        updaterExecutable = 'updater/updater.exe' if sys.platform.startswith('win') else 'updater/updater'
        updatedUpdater = updaterExecutable + '.new'
        if os.path.exists(updatedUpdater):
            os.replace(updatedUpdater, updaterExecutable)
        request = QNetworkRequest(QUrl('https://github.com/oliviermirat/ZebraZoom/releases/latest'))
        request.setAttribute(QNetworkRequest.Attribute.RedirectPolicyAttribute, QNetworkRequest.RedirectPolicy.NoLessSafeRedirectPolicy)
        self._reply = self._networkManager.get(request)
        self._reply.finished.connect(self._refreshUpdateStatus)


class SeveralVideos(QWidget):
    def __init__(self, controller):
        super().__init__(controller.window)
        self.controller = controller
        self.preferredSize = (900, 600)

        layout = QVBoxLayout()
        layout.addWidget(util.apply_style(QLabel("Run ZebraZoom on several videos", self), font=controller.title_font), alignment=Qt.AlignmentFlag.AlignCenter)

        button1 = util.apply_style(QPushButton("Run ZebraZoom on several videos", self), background_color=util.DEFAULT_BUTTON_COLOR)
        button1.clicked.connect(lambda: controller.show_frame("FolderToAnalyze"))
        layout.addWidget(button1, alignment=Qt.AlignmentFlag.AlignCenter)

        advancedOptionsLayout = QVBoxLayout()

        sublayout1 = QVBoxLayout()
        button2 = util.apply_style(QPushButton("Manual first frame tail extremity for head embedded", self), background_color=util.LIGHT_YELLOW)
        button2.clicked.connect(lambda: controller.show_frame("TailExtremityHE"))
        sublayout1.addWidget(button2, alignment=Qt.AlignmentFlag.AlignCenter)
        sublayout1.addWidget(QLabel("This button allows you to only manually select the tail extremities,", self), alignment=Qt.AlignmentFlag.AlignCenter)
        sublayout1.addWidget(QLabel("you will be able to run the tracking on multiple videos without interruptions with the 'Run ZebraZoom on an entire folder' button above afterwards.", self), alignment=Qt.AlignmentFlag.AlignCenter)
        sublayout1.addWidget(util.apply_style(QLabel("", self), font=controller.title_font), alignment=Qt.AlignmentFlag.AlignCenter)
        advancedOptionsLayout.addLayout(sublayout1)

        sublayout2 = QVBoxLayout()
        button3 = util.apply_style(QPushButton("Only select the regions of interest", self), background_color=util.LIGHT_YELLOW)
        button3.clicked.connect(lambda: controller.show_frame("FolderMultipleROIInitialSelect"))
        sublayout2.addWidget(button3, alignment=Qt.AlignmentFlag.AlignCenter)
        sublayout2.addWidget(QLabel("This is for the 'Multiple rectangular regions of interest chosen at runtime' option.", self), alignment=Qt.AlignmentFlag.AlignCenter)
        sublayout2.addWidget(QLabel("This button allows you to only select the ROIs,", self), alignment=Qt.AlignmentFlag.AlignCenter)
        sublayout2.addWidget(QLabel("you will be able to run the tracking on multiple videos without interruptions with the 'Run ZebraZoom on an entire folder' button above afterwards.", self), alignment=Qt.AlignmentFlag.AlignCenter)
        sublayout2.addWidget(util.apply_style(QLabel("", self), font=controller.title_font), alignment=Qt.AlignmentFlag.AlignCenter)
        advancedOptionsLayout.addLayout(sublayout2)

        sublayout3 = QVBoxLayout()
        button4 = util.apply_style(QPushButton("'Grid System' wells detection coordinates pre-selection", self), background_color=util.LIGHT_YELLOW)
        button4.clicked.connect(lambda: controller.show_frame("FolderMultipleROIInitialSelect"))
        sublayout3.addWidget(button4, alignment=Qt.AlignmentFlag.AlignCenter)
        sublayout3.addWidget(QLabel("This button allows you to only select the coordinates relative to the 'grid system',", self), alignment=Qt.AlignmentFlag.AlignCenter)
        sublayout3.addWidget(QLabel("you will be able to run the tracking on multiple videos without interruptions with the 'Run ZebraZoom on an entire folder' button above afterwards.", self), alignment=Qt.AlignmentFlag.AlignCenter)
        sublayout3.addWidget(util.apply_style(QLabel("", self), font=controller.title_font), alignment=Qt.AlignmentFlag.AlignCenter)
        advancedOptionsLayout.addLayout(sublayout3)

        layout.addWidget(util.Expander(self, "Show advanced options", advancedOptionsLayout))

        start_page_btn = QPushButton("Go to the start page", self)
        start_page_btn.clicked.connect(lambda: controller.show_frame("StartPage"))
        layout.addWidget(start_page_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        self.setLayout(layout)


class VideoToAnalyze(QWidget):
    def __init__(self, controller):
        super().__init__(controller.window)
        self.controller = controller
        self.preferredSize = (900, 450)

        layout = QVBoxLayout()
        layout.addWidget(util.apply_style(QLabel("Choose video.", self), font=controller.title_font), alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(QLabel("Look for the video you want to analyze.", self), alignment=Qt.AlignmentFlag.AlignCenter)
        button = util.apply_style(QPushButton("Choose file", self), background_color=util.DEFAULT_BUTTON_COLOR)
        button.clicked.connect(lambda: controller.chooseVideoToAnalyze(just_extract_checkbox.isChecked(), no_validation_checkbox.isChecked(), chooseFramesCheckbox.isChecked()))
        layout.addWidget(button, alignment=Qt.AlignmentFlag.AlignCenter)
        chooseFramesCheckbox = QCheckBox("Choose the first and the last frames on which the tracking should run (tracking results will be saved)", self)
        layout.addWidget(chooseFramesCheckbox, alignment=Qt.AlignmentFlag.AlignCenter)

        advancedOptionsLayout = QVBoxLayout()

        button = util.apply_style(QPushButton("Click here if you prefer to run the tracking from the command line", self), background_color='green')
        button.clicked.connect(lambda: webbrowser.open_new("https://zebrazoom.org/documentation/docs/tracking/launchingTracking#launching-the-tracking-through-the-command-line"))
        advancedOptionsLayout.addWidget(button, alignment=Qt.AlignmentFlag.AlignCenter)

        just_extract_checkbox = util.apply_style(QCheckBox("I ran the tracking already, I only want to redo the extraction of parameters.", self), color='purple')
        advancedOptionsLayout.addWidget(just_extract_checkbox, alignment=Qt.AlignmentFlag.AlignCenter)
        advancedOptionsLayout.addWidget(QLabel("", self), alignment=Qt.AlignmentFlag.AlignCenter)
        no_validation_checkbox = util.apply_style(QCheckBox("Don't (re)generate a validation video (for speed efficiency).", self), color='purple')
        advancedOptionsLayout.addWidget(no_validation_checkbox, alignment=Qt.AlignmentFlag.AlignCenter)
        advancedOptionsLayout.addWidget(QLabel("", self), alignment=Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(util.Expander(self, "Show advanced options", advancedOptionsLayout))

        start_page_btn = QPushButton("Go to the start page", self)
        start_page_btn.clicked.connect(lambda: controller.show_frame("StartPage"))
        layout.addWidget(start_page_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        self.setLayout(layout)


class FolderToAnalyze(QWidget):
    def __init__(self, controller):
        super().__init__(controller.window)
        self.controller = controller

        layout = QVBoxLayout()
        layout.addWidget(util.apply_style(QLabel("Run ZebraZoom on several videos", self), font=controller.title_font), alignment=Qt.AlignmentFlag.AlignCenter)
        button = util.apply_style(QPushButton("Choose videos", self), background_color=util.DEFAULT_BUTTON_COLOR)
        button.clicked.connect(lambda: controller.chooseFolderToAnalyze(just_extract_checkbox.isChecked(), no_validation_checkbox.isChecked(), expert_checkbox.isChecked()))
        layout.addWidget(button, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(QLabel("", self), alignment=Qt.AlignmentFlag.AlignCenter)

        advancedOptionsLayout = QVBoxLayout()

        just_extract_checkbox = QCheckBox("I ran the tracking already, I only want to redo the extraction of parameters.", self)
        advancedOptionsLayout.addWidget(just_extract_checkbox, alignment=Qt.AlignmentFlag.AlignCenter)
        advancedOptionsLayout.addWidget(QLabel("", self), alignment=Qt.AlignmentFlag.AlignCenter)
        no_validation_checkbox = QCheckBox("Don't (re)generate a validation video (for speed efficiency).", self)
        advancedOptionsLayout.addWidget(no_validation_checkbox, alignment=Qt.AlignmentFlag.AlignCenter)
        advancedOptionsLayout.addWidget(QLabel("", self), alignment=Qt.AlignmentFlag.AlignCenter)
        expert_checkbox = QCheckBox("Expert use (don't click here unless you know what you're doing): Only generate a script to launch all videos in parallel with sbatch.", self)
        advancedOptionsLayout.addWidget(expert_checkbox, alignment=Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(util.Expander(self, "Show advanced options", advancedOptionsLayout))

        start_page_btn = QPushButton("Go to the start page", self)
        start_page_btn.clicked.connect(lambda: controller.show_frame("StartPage"))
        layout.addWidget(start_page_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        self.setLayout(layout)


class TailExtremityHE(QWidget):
    def __init__(self, controller):
        super().__init__(controller.window)
        self.controller = controller

        layout = QVBoxLayout()
        layout.addWidget(util.apply_style(QLabel("Manually label tail extremities", self), font=controller.title_font), alignment=Qt.AlignmentFlag.AlignCenter)
        button = util.apply_style(QPushButton("Choose videos", self), background_color=util.DEFAULT_BUTTON_COLOR)
        button.clicked.connect(controller.chooseFolderForTailExtremityHE)
        layout.addWidget(button, alignment=Qt.AlignmentFlag.AlignCenter)

        start_page_btn = QPushButton("Go to the start page", self)
        start_page_btn.clicked.connect(lambda: controller.show_frame("StartPage"))
        layout.addWidget(start_page_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        self.setLayout(layout)


class FolderMultipleROIInitialSelect(QWidget):
    def __init__(self, controller):
        super().__init__(controller.window)
        self.controller = controller

        layout = QVBoxLayout()
        layout.addWidget(util.apply_style(QLabel("Define regions of interest", self), font=controller.title_font), alignment=Qt.AlignmentFlag.AlignCenter)
        button = util.apply_style(QPushButton("Choose videos", self), background_color=util.DEFAULT_BUTTON_COLOR)
        button.clicked.connect(lambda: controller.chooseFolderForMultipleROIs(not sameCoordinatesForAllCheckbox.isChecked()))
        layout.addWidget(button, alignment=Qt.AlignmentFlag.AlignCenter)
        sameCoordinatesForAllCheckbox = QCheckBox("Use the same coordinates for all videos")
        layout.addWidget(sameCoordinatesForAllCheckbox, alignment=Qt.AlignmentFlag.AlignCenter)

        start_page_btn = QPushButton("Go to the start page", self)
        start_page_btn.clicked.connect(lambda: controller.show_frame("StartPage"))
        layout.addWidget(start_page_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        self.setLayout(layout)


class ConfigFilePromp(QWidget):
    def __init__(self, controller):
        super().__init__(controller.window)
        self.controller = controller
        self.preferredSize = (300, 300)
        self._ZZargs = ()
        self._ZZkwargs = {}

        layout = QVBoxLayout()
        layout.addWidget(util.apply_style(QLabel("Choose configuration file.", self), font=controller.title_font), alignment=Qt.AlignmentFlag.AlignCenter)
        button = util.apply_style(QPushButton("Choose file", self), background_color=util.DEFAULT_BUTTON_COLOR)
        button.clicked.connect(lambda: chooseConfigFile(self._ZZargs, self._ZZkwargs))
        layout.addWidget(button, alignment=Qt.AlignmentFlag.AlignCenter)
        start_page_btn = QPushButton("Go to the start page", self)
        start_page_btn.clicked.connect(lambda: controller.show_frame("StartPage"))
        layout.addWidget(start_page_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        self.setLayout(layout)

    def setArgs(self, args, kwargs):
        self._ZZargs = args
        self._ZZkwargs = kwargs


class Patience(QWidget):
    def __init__(self, controller):
        super().__init__(controller.window)
        self.controller = controller
        self.preferredSize = (300, 100)
        self._ZZargs = ()
        self._ZZkwargs = {}

        layout = QVBoxLayout()
        button = util.apply_style(QPushButton("Launch ZebraZoom on your video(s)", self), background_color=util.DEFAULT_BUTTON_COLOR)
        button.clicked.connect(lambda: launchZebraZoom(*self._ZZargs, **self._ZZkwargs))
        layout.addWidget(button, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(QLabel("After clicking on the button above, please wait for ZebraZoom to run, you can look at the console outside of the GUI to check on the progress of ZebraZoom.", self), alignment=Qt.AlignmentFlag.AlignCenter)

        self.setLayout(layout)

    def setArgs(self, args, kwargs):
        self._ZZargs = args
        self._ZZkwargs = kwargs


class ZZoutro(QWidget):
    def __init__(self, controller):
        super().__init__(controller.window)
        self.controller = controller
        self.preferredSize = (150, 100)

        layout = QVBoxLayout()
        layout.addWidget(QLabel("Finished.", self), alignment=Qt.AlignmentFlag.AlignCenter)
        button = util.apply_style(QPushButton("Go to the start page", self), background_color=util.DEFAULT_BUTTON_COLOR)
        button.clicked.connect(lambda: controller.show_frame("StartPage"))
        layout.addWidget(button, alignment=Qt.AlignmentFlag.AlignCenter)

        self.setLayout(layout)


class ZZoutroSbatch(QWidget):
    def __init__(self, controller):
        super().__init__(controller.window)
        self.controller = controller

        layout = QVBoxLayout()
        layout.addWidget(QLabel("Two files and one folder have been generated in the folder %s:" % paths.getRootDataFolder(), self), alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(QLabel("launchZZ.sh, commands.txt and configFiles", self), alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(QLabel("Place these two files and the folder on your server and type: 'sbatch launchZZ.sh' to launch the analysis on all videos in parallel", self), alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(QLabel("Before launching the parrallel tracking with sbatch, you may need to type: 'chmod +x launchZZ.sh'", self), alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(QLabel("You can follow the progress with the commands 'squeueme' and by looking into the slurm* file being generated with 'cat slurm*'", self), alignment=Qt.AlignmentFlag.AlignCenter)

        startPageBtn = util.apply_style(QPushButton("Go to the start page", self), background_color=util.DEFAULT_BUTTON_COLOR)
        startPageBtn.clicked.connect(lambda: controller.show_frame("StartPage"))
        layout.addWidget(startPageBtn, alignment=Qt.AlignmentFlag.AlignCenter)
        self.setLayout(layout)


class EnhanceZZOutput(QWidget):
    def __init__(self, controller):
        super().__init__(controller.window)

        layout = QVBoxLayout()
        layout.addWidget(util.apply_style(QLabel("Tips on how to correct/enhance ZebraZoom's output when necessary", self), font=controller.title_font), alignment=Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(util.apply_style(QLabel("Movement Flagging System:", self), font_size='16px'), alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(QLabel("You can see the results obtained from ZebraZoom's tracking thanks to the button 'Visualize ZebraZoom's output' in the main menu.", self), alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(QLabel("If one of the movements detected by ZebraZoom seems false or if you want to ignore it, you can click on the 'flag' button for that movement:", self), alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(QLabel("that will save a flag for that movement in the raw data obtained for that video,", self), alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(QLabel("and if you use 'Analyze ZebraZoom's outputs' (in the main menu) each movement flagged will be ignored from that analysis.", self), alignment=Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(util.apply_style(QLabel("Speed and Distance traveled Parameter Check:", self), font_size='16px'), alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(QLabel("If you are interested in comparing the speed and distance traveled between different populations,", self), alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(QLabel("then you need to make sure that the (x, y) coordinates were correctly calculated for every frame.", self), alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(QLabel("To do this, from the 'Analyze ZebraZoom's outputs' menu, you can click on 'Change Right Side Plot' until you see the 'Body Coordinates' plot.", self), alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(QLabel("You can then check on this plot that the body coordinates never goes to the (0, 0) coordinate (in which case a error occurred).", self), alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(QLabel("If an error occurred, one option can be to use the flagging system described above to ignore that movement.", self), alignment=Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(util.apply_style(QLabel("Bend detection for zebrafish:", self), font_size='16px'), alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(QLabel("If you are tracking zebrafish larvae and trying to detect local maximums and minimums of the tail angle (called 'bends'),", self), alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(QLabel("then you might need to further adjust the parameters related to the bends detection (if these bends are not being detected right).", self), alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(QLabel("You can check if the bends are being detected right with the 'Visualize ZebraZoom's output' in the main menu.", self), alignment=Qt.AlignmentFlag.AlignCenter)

        linkBtn2 = QPushButton("View tips on bends detection", self)
        linkBtn2.clicked.connect(lambda: webbrowser.open_new("https://zebrazoom.org/documentation/docs/configurationFile/advanced/angleSmoothBoutsAndBendsDetection"))
        layout.addWidget(linkBtn2, alignment=Qt.AlignmentFlag.AlignCenter)
        self.setLayout(layout)
        startPageBtn = QPushButton("Go to the start page", self)
        startPageBtn.clicked.connect(lambda: controller.show_frame("StartPage"))
        layout.addWidget(startPageBtn, alignment=Qt.AlignmentFlag.AlignCenter)

        self.setLayout(layout)


class _TooltipHelper(QObject):
  def eventFilter(self, obj, evt):
    if evt.type() != QEvent.Type.ToolTip:
      return False
    view = obj.parent()
    if view is None:
      return False

    index = view.indexAt(evt.pos())
    if not index.isValid():
      return False
    rect = view.visualRect(index)
    if view.sizeHintForColumn(index.column()) > rect.width():
      QToolTip.showText(evt.globalPos(), view.model().data(index), view, rect)
      return True
    else:
      QToolTip.hideText()
      return True
    return False


class ViewParameters(util.CollapsibleSplitter):
    def __init__(self, controller):
        super().__init__(controller.window)
        self.controller = controller
        self._headEmbedded = False
        self.visualization = 0

        model = QFileSystemModel()
        model.setFilter(QDir.Filter.NoDotAndDotDot | QDir.Filter.Dirs)
        model.setRootPath(self.controller.ZZoutputLocation)
        model.setReadOnly(True)
        proxyModel = QSortFilterProxyModel()

        def filterModel(row, parent):
          index = model.index(row, 0, parent)
          if os.path.normpath(model.filePath(index)) == os.path.normpath(self.controller.ZZoutputLocation):
            return True
          return bool(self._findResultsFile(model.fileName(index)))
        proxyModel.filterAcceptsRow = filterModel
        proxyModel.setSourceModel(model)
        self._tree = tree = QTreeView()
        tree.viewport().installEventFilter(_TooltipHelper(tree))
        tree.sizeHint = lambda: QSize(150, 1)
        tree.setModel(proxyModel)
        tree.setRootIsDecorated(False)
        tree.header().setSectionResizeMode(QHeaderView.ResizeMode.Fixed)
        for idx in range(1, model.columnCount()):
          tree.hideColumn(idx)
        tree.resizeEvent = lambda evt: tree.setColumnWidth(0, evt.size().width())
        selectionModel = tree.selectionModel()
        selectionModel.currentRowChanged.connect(lambda current, previous: current.row() == -1 or self.setFolder(model.fileName(current)))

        layout = QGridLayout()

        optimizeLayout = QHBoxLayout()
        message = util.apply_style(QLabel("We ran the test tracking on your video, you can visualize the results on this page. If you think the tracking results are not good enough, "
                                          "click on the 'Optimize' button to improve the configuration file used for tracking.", self), color="red", font_size="14px")
        message.setWordWrap(True)
        optimizeLayout.addWidget(message)
        optimizeLayout.setStretch(0, 1)
        optimizeBtn = util.apply_style(QPushButton("Optimize configuration file", self), background_color=util.LIGHT_YELLOW)
        optimizeBtn.clicked.connect(lambda: util.addToHistory(controller.optimizeConfigFile)())
        optimizeLayout.addWidget(optimizeBtn, alignment=Qt.AlignmentFlag.AlignLeft)
        layout.addLayout(optimizeLayout, 1, 1, 1, 7)
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        layout.addWidget(line, 2, 1, 1, 7)

        self._wholeVideoBtn = QPushButton("View video for all wells together", self)
        self._wholeVideoBtn.clicked.connect(lambda: self.showValidationVideo(-1, self.numPoiss(), 0, -1))
        layout.addWidget(self._wholeVideoBtn, 3, 1, Qt.AlignmentFlag.AlignCenter)

        self._viewBtn = QPushButton("", self)
        self._viewBtn.clicked.connect(lambda: self.showGraphForAllBoutsCombined(self.numWell(), self.numPoiss(), self.dataRef, self.visualization, self.graphScaling))
        layout.addWidget(self._viewBtn, 3, 2, 1, 5, Qt.AlignmentFlag.AlignCenter)

        self.title_label = util.apply_style(QLabel('', self), font_size='16px')
        layout.addWidget(self.title_label, 0, 0, 1, 8, Qt.AlignmentFlag.AlignCenter)
        self._wellNumberLabel = QLabel("Well number:", self)
        layout.addWidget(self._wellNumberLabel, 4, 1, Qt.AlignmentFlag.AlignCenter)
        self.spinbox1 = QSpinBox(self)
        self.spinbox1.setStyleSheet(util.SPINBOX_STYLESHEET)
        self.spinbox1.setMinimumWidth(70)
        self.spinbox1.valueChanged.connect(self._wellChanged)
        self.numWell = self.spinbox1.value
        layout.addWidget(self.spinbox1, 4, 2, Qt.AlignmentFlag.AlignCenter)

        self.zoomed_video_btn = QPushButton("", self)
        self.zoomed_video_btn.clicked.connect(lambda: self.showValidationVideo(self.numWell(), self.numPoiss(), 1, -1))
        layout.addWidget(self.zoomed_video_btn, 5, 2, Qt.AlignmentFlag.AlignCenter)

        self._plotComboBox = QComboBox(self)
        self._plotComboBox.addItems(("Tail angle smoothed", "Tail angle raw", "All tail angles smoothed", "All tail angles raw", "Body coordinates"))
        self._plotComboBox.currentIndexChanged.connect(lambda idx: setattr(self, "visualization", idx) or self._printSomeResults())
        layout.addWidget(self._plotComboBox, 5, 4, Qt.AlignmentFlag.AlignCenter)

        self._fishNumberLabel = QLabel("Fish number:", self)
        layout.addWidget(self._fishNumberLabel, 6, 1, Qt.AlignmentFlag.AlignCenter)
        self.spinbox2 = QSpinBox(self)
        self.spinbox2.setStyleSheet(util.SPINBOX_STYLESHEET)
        self.spinbox2.setMinimumWidth(70)
        self.spinbox2.valueChanged.connect(self._poissChanged)
        self.numPoiss = self.spinbox2.value
        layout.addWidget(self.spinbox2, 6, 2, Qt.AlignmentFlag.AlignCenter)

        self._zoomBtn = util.apply_style(QPushButton("", self), background_color=util.LIGHT_GREEN)
        self._zoomBtn.clicked.connect(lambda: setattr(self, "graphScaling", not self.graphScaling) or self._printSomeResults())
        layout.addWidget(self._zoomBtn, 6, 4, Qt.AlignmentFlag.AlignCenter)

        layout.addWidget(QLabel("Bout number:", self), 7, 1, Qt.AlignmentFlag.AlignCenter)
        self.spinbox3 = QSpinBox(self)
        self.spinbox3.setStyleSheet(util.SPINBOX_STYLESHEET)
        self.spinbox3.setMinimumWidth(70)
        self.spinbox3.valueChanged.connect(self._mouvChanged)
        self.numMouv = self.spinbox3.value
        layout.addWidget(self.spinbox3, 7, 2, Qt.AlignmentFlag.AlignCenter)

        button1 = QPushButton("View bout's angle", self)
        button1.clicked.connect(lambda: self._printSomeResults())
        layout.addWidget(button1, 8, 2, Qt.AlignmentFlag.AlignCenter)

        self.flag_movement_btn = QPushButton("", self)
        self.flag_movement_btn.clicked.connect(self.flagMove)
        layout.addWidget(self.flag_movement_btn, 8, 4, Qt.AlignmentFlag.AlignCenter)

        self.prev_btn = QPushButton("Previous Bout", self)
        self.prev_btn.clicked.connect(self.printPreviousResults)
        layout.addWidget(self.prev_btn, 9, 1, Qt.AlignmentFlag.AlignCenter)
        self.next_btn = QPushButton("Next Bout", self)
        self.next_btn.clicked.connect(self.printNextResults)
        layout.addWidget(self.next_btn, 9, 2, Qt.AlignmentFlag.AlignCenter)

        kine_btn = QPushButton("Check kinematic parameters\n(beta version)", self)
        kine_btn.clicked.connect(lambda: checkConsistencyOfParameters([self.currentResultFolder]))
        layout.addWidget(kine_btn, 10, 2, Qt.AlignmentFlag.AlignCenter)

        self._startPageBtn = QPushButton("Go to the start page", self)
        self._startPageBtn.clicked.connect(lambda: controller.show_frame("StartPage"))
        layout.addWidget(self._startPageBtn, 10, 1, Qt.AlignmentFlag.AlignCenter)

        def _updateConfigWidgets():
          if controller.configFile:  # page shown while testing config
            message.show()
            line.show()
            optimizeBtn.show()
            tree.hide()
          else:
            message.hide()
            line.hide()
            optimizeBtn.hide()
            tree.show()
        self._updateConfigWidgets = _updateConfigWidgets

        self.well_video_btn = QPushButton("", self)
        self.well_video_btn.clicked.connect(lambda: self.showValidationVideo(self.numWell(), self.numPoiss(), 0, self.begMove))
        layout.addWidget(self.well_video_btn, 5, 1, Qt.AlignmentFlag.AlignCenter)
        self.bout_video_btn = QPushButton("View bout's video" , self)
        self.bout_video_btn.clicked.connect(lambda: self.showValidationVideo(self.numWell(), self.numPoiss(), not self._headEmbedded, self.begMove))
        layout.addWidget(self.bout_video_btn, 8, 1, Qt.AlignmentFlag.AlignCenter)
        self.graph_title_label = util.apply_style(QLabel('', font=LARGE_FONT))
        layout.addWidget(self.graph_title_label, 3, 7, Qt.AlignmentFlag.AlignCenter)

        self.superstruct_btn = util.apply_style(QPushButton("Save SuperStruct" , self), background_color='orange')
        self.superstruct_btn.clicked.connect(self.saveSuperStruct)
        layout.addWidget(self.superstruct_btn, 9, 4, Qt.AlignmentFlag.AlignCenter)

        f = Figure(figsize=(5,5), dpi=100)
        self.a = f.add_subplot(111)
        self.canvas = FigureCanvas(f)
        canvasWrapper = QWidget()
        canvasWrapperLayout = QVBoxLayout()
        canvasWrapperLayout.addWidget(self.canvas, alignment=Qt.AlignmentFlag.AlignCenter)
        canvasWrapper.resizeEvent = lambda evt: self.canvas.resize(min(evt.size().width(), evt.size().height()), min(evt.size().width(), evt.size().height()))
        canvasWrapper.setLayout(canvasWrapperLayout)
        canvasSize = self.canvas.size()
        canvasWrapper.sizeHint = lambda *args: canvasSize
        layout.addWidget(canvasWrapper, 4, 7, 7, 1, Qt.AlignmentFlag.AlignCenter)
        sizeHint = layout.totalSizeHint().width() + canvasSize.width()

        centralWidget = QWidget()
        centralWidget.sizeHint = lambda *args: QSize(sizeHint + 200, 768)
        centralWidget.setLayout(layout)
        self.addWidget(tree)
        self._centralWidget = wrapperWidget = QWidget()
        wrapperWidget.showChildren = lambda: [child.show() for child in centralWidget.findChildren(QWidget) if child is not self._startPageBtn]
        wrapperWidget.hideChildren = lambda: [child.hide() for child in centralWidget.findChildren(QWidget) if child is not self._startPageBtn]
        wrapperLayout = QHBoxLayout()
        wrapperLayout.addWidget(centralWidget, alignment=Qt.AlignmentFlag.AlignCenter)
        wrapperWidget.setLayout(wrapperLayout)
        scrollArea = QScrollArea()
        scrollArea.setFrameShape(QFrame.Shape.NoFrame)
        scrollArea.setWidgetResizable(True)
        scrollArea.setWidget(wrapperWidget)
        self.addWidget(scrollArea)
        self.setStretchFactor(1, 1)
        self.setChildrenCollapsible(False)
        tree.hide()

    def _findResultsFile(self, folder):
        reference = os.path.join(self.controller.ZZoutputLocation, os.path.join(folder, 'results_' + folder + '.txt'))
        if os.path.exists(reference):
          return reference
        mypath = os.path.join(self.controller.ZZoutputLocation, folder)
        if not os.path.exists(mypath):
          return None
        resultsFile = next((f for f in os.listdir(mypath) if os.path.isfile(os.path.join(mypath, f)) and f.startswith('results_')), None)
        if resultsFile is None:
          return None
        return os.path.join(self.controller.ZZoutputLocation, os.path.join(folder, resultsFile))

    def setFolder(self, name):
        self.title_label.setText(name)
        if name is None:
          self._tree.hide()
          filesystemModel = self._tree.model().sourceModel()
          filesystemModel.setRootPath(None)
          filesystemModel.setRootPath(self.controller.ZZoutputLocation)  # force refresh of the model
          self._tree.setRootIndex(self._tree.model().mapFromSource(filesystemModel.index(filesystemModel.rootPath())))
          self._centralWidget.hideChildren()
          self._tree.selectionModel().reset()
          self._tree.show()
          self._updateConfigWidgets()
          return
        else:
          self._centralWidget.showChildren()
        self.currentResultFolder = name

        try:
          with open(os.path.join(self.controller.ZZoutputLocation, name, 'configUsed.json')) as config:
            self._headEmbedded = bool(json.load(config).get("headEmbeded", False))
        except (EnvironmentError, json.JSONDecodeError) as e:
          self._headEmbedded = False
        with open(self._findResultsFile(name)) as ff:
          self.dataRef = json.load(ff)

        self.spinbox1.setValue(0)
        self.spinbox2.setValue(0)
        self.spinbox3.setValue(0)
        self.nbWells = len(self.dataRef["wellPoissMouv"])
        self.nbPoiss = len(self.dataRef["wellPoissMouv"][self.numWell()])
        self.nbMouv = len(self.dataRef["wellPoissMouv"][self.numWell()][self.numPoiss()])
        self.graphScaling = False
        self.spinbox1.setRange(0, self.nbWells - 1)
        self.spinbox2.setRange(0, self.nbPoiss - 1)
        self.spinbox3.setRange(0, self.nbMouv - 1)
        self.superstruct_btn.hide()
        defaultGraphIndex = 0 if self._headEmbedded else 4
        if self._plotComboBox.currentIndex() == defaultGraphIndex:
            self._printSomeResults()
        else:
            self._plotComboBox.setCurrentIndex(defaultGraphIndex)

        if self._headEmbedded:
          self.spinbox1.hide()
          self.spinbox2.hide()
          self.zoomed_video_btn.hide()
          self._wholeVideoBtn.setText("View the whole video")
          self._wellNumberLabel.hide()
          self._fishNumberLabel.hide()
        else:
          self.spinbox1.show()
          self.spinbox2.show()
          self.zoomed_video_btn.show()
          self._wholeVideoBtn.setText("View video for all wells together")
          self._wellNumberLabel.show()
          self._fishNumberLabel.show()

    def _updateGraph(self):
        self.a.clear()
        if self.nbMouv > 0:
            self.begMove = self.dataRef["wellPoissMouv"][self.numWell()][self.numPoiss()][self.numMouv()]["BoutStart"]
            endMove = self.dataRef["wellPoissMouv"][self.numWell()][self.numPoiss()][self.numMouv()]["BoutEnd"]

            self._plotComboBox.model().item(0).setEnabled("TailAngle_smoothed" in self.dataRef["wellPoissMouv"][self.numWell()][self.numPoiss()][self.numMouv()])
            self._plotComboBox.model().item(1).setEnabled("TailAngle_Raw" in self.dataRef["wellPoissMouv"][self.numWell()][self.numPoiss()][self.numMouv()])
            self._plotComboBox.model().item(2).setEnabled("allTailAnglesSmoothed" in self.dataRef["wellPoissMouv"][self.numWell()][self.numPoiss()][self.numMouv()])
            self._plotComboBox.model().item(3).setEnabled("allTailAngles" in self.dataRef["wellPoissMouv"][self.numWell()][self.numPoiss()][self.numMouv()])

            newIndex = self.visualization
            while not self._plotComboBox.model().item(newIndex).isEnabled():
                newIndex += 1
            if newIndex != self.visualization:
                block = self._plotComboBox.blockSignals(True)
                self._plotComboBox.setCurrentIndex(newIndex)
                self.visualization = newIndex
                self._plotComboBox.blockSignals(block)

            # if self.visualization == 2 and not((len(np.unique(self.dataRef["wellPoissMouv"][self.numWell()][self.numPoiss()][self.numMouv()]["HeadX"])) > 1) and (len(np.unique(self.dataRef["wellPoissMouv"][self.numWell()][self.numPoiss()][self.numMouv()]["HeadY"])) > 1)):
                # self.visualization = 0

            if self.visualization == 0:

              tailAngleSmoothed = self.dataRef["wellPoissMouv"][self.numWell()][self.numPoiss()][self.numMouv()]["TailAngle_smoothed"].copy()

              for ind,val in enumerate(tailAngleSmoothed):
                tailAngleSmoothed[ind]=tailAngleSmoothed[ind]*(180/(math.pi))

              if "Bend_Timing" in self.dataRef["wellPoissMouv"][self.numWell()][self.numPoiss()][self.numMouv()]:
                freqX = self.dataRef["wellPoissMouv"][self.numWell()][self.numPoiss()][self.numMouv()]["Bend_Timing"]
                freqY = self.dataRef["wellPoissMouv"][self.numWell()][self.numPoiss()][self.numMouv()]["Bend_Amplitude"]
              else:
                freqX = []
                freqY = []
              if type(freqY)==int or type(freqY)==float:
                freqY = freqY * (180/(math.pi))
              else:
                if "Bend_Timing" in self.dataRef["wellPoissMouv"][self.numWell()][self.numPoiss()][self.numMouv()]:
                  freqX = self.dataRef["wellPoissMouv"][self.numWell()][self.numPoiss()][self.numMouv()]["Bend_Timing"].copy()
                  freqY = self.dataRef["wellPoissMouv"][self.numWell()][self.numPoiss()][self.numMouv()]["Bend_Amplitude"].copy()
                else:
                  freqX = []
                  freqY = []
                for ind,val in enumerate(freqY):
                  freqY[ind]=freqY[ind]*(180/(math.pi))
              fx = [self.begMove]
              fy = [0]
              if (type(freqX) is int) or (type(freqX) is float):
                freqX = [freqX]
                freqY = [freqY]
              for idx,x in enumerate(freqX):
                idx2 = idx - 1
                fx.append(freqX[idx2] - 1 + self.begMove)
                fx.append(freqX[idx2] - 1 + self.begMove)
                fx.append(freqX[idx2] - 1 + self.begMove)
                fy.append(0)
                fy.append(freqY[idx2])
                fy.append(0)

              if not(self.graphScaling):
                self.a.set_ylim(-140, 140)

              if len(tailAngleSmoothed):
                tailAngle, = self.a.plot([i for i in range(self.begMove,endMove+1)],tailAngleSmoothed)
                bend, = self.a.plot(fx,fy)
                self.a.plot([i for i in range(self.begMove,endMove+1)],[0 for i in range(0,len(tailAngleSmoothed))])
                self.a.legend([tailAngle, bend], ['Tail angle', 'Bend'])
            elif self.visualization == 1:

              tailAngleSmoothed = self.dataRef["wellPoissMouv"][self.numWell()][self.numPoiss()][self.numMouv()]["TailAngle_Raw"].copy()
              for ind,val in enumerate(tailAngleSmoothed):
                tailAngleSmoothed[ind]=tailAngleSmoothed[ind]*(180/(math.pi))

              if not(self.graphScaling):
                self.a.set_ylim(-140, 140)

              self.a.plot([i for i in range(self.begMove,endMove+1)],tailAngleSmoothed)
              self.a.plot([i for i in range(self.begMove,endMove+1)],[0 for i in range(0,len(tailAngleSmoothed))])

            elif self.visualization == 2:
              
              if not(self.graphScaling):
                self.a.set_ylim(-140, 140)
              pointsToTakeIntoAccountStart = 9 - 8
              bStart = self.dataRef["wellPoissMouv"][self.numWell()][self.numPoiss()][self.numMouv()]["BoutStart"]
              bEnd   = self.dataRef["wellPoissMouv"][self.numWell()][self.numPoiss()][self.numMouv()]["BoutEnd"]
              tailAngles = self.dataRef["wellPoissMouv"][self.numWell()][self.numPoiss()][self.numMouv()]["allTailAnglesSmoothed"][pointsToTakeIntoAccountStart:]
              if len(tailAngles) <= 10:
                for tailAngle in tailAngles:
                  if bEnd - bStart + 1 == len(tailAngle):
                    self.a.plot([i for i in range(bStart, bEnd + 1)], [t*(180/math.pi) for t in tailAngle])
              else:
                for angleNum in range(0, len(tailAngles), int(len(tailAngles) / 10) + 1):
                  tailAngle = tailAngles[angleNum]
                  if bEnd - bStart + 1 == len(tailAngle):
                    self.a.plot([i for i in range(bStart, bEnd + 1)], [t*(180/math.pi) for t in tailAngle])

            elif self.visualization == 3:
              
              if not(self.graphScaling):
                self.a.set_ylim(-140, 140)
              pointsToTakeIntoAccountStart = 9 - 8
              bStart = self.dataRef["wellPoissMouv"][self.numWell()][self.numPoiss()][self.numMouv()]["BoutStart"]
              bEnd   = self.dataRef["wellPoissMouv"][self.numWell()][self.numPoiss()][self.numMouv()]["BoutEnd"]
              tailAngles = self.dataRef["wellPoissMouv"][self.numWell()][self.numPoiss()][self.numMouv()]["allTailAngles"][pointsToTakeIntoAccountStart:]
              if len(tailAngles) <= 10:
                for tailAngle in tailAngles:
                  if bEnd - bStart + 1 == len(tailAngle):
                    self.a.plot([i for i in range(bStart, bEnd + 1)], [t*(180/math.pi) for t in tailAngle])
              else:
                for angleNum in range(0, len(tailAngles), int(len(tailAngles) / 10) + 1):
                  tailAngle = tailAngles[angleNum]
                  if bEnd - bStart + 1 == len(tailAngle):
                    self.a.plot([i for i in range(bStart, bEnd + 1)], [t*(180/math.pi) for t in tailAngle])

            else:
              headX = self.dataRef["wellPoissMouv"][self.numWell()][self.numPoiss()][self.numMouv()]["HeadX"].copy()
              headY = self.dataRef["wellPoissMouv"][self.numWell()][self.numPoiss()][self.numMouv()]["HeadY"].copy()


              if not(self.graphScaling):
                lengthX  = self.dataRef["wellPositions"][self.numWell()]["lengthX"]
                lengthY  = self.dataRef["wellPositions"][self.numWell()]["lengthY"]
                self.a.set_xlim(0, lengthX)
                self.a.set_ylim(lengthY, 0)

              self.a.plot(headX, headY)
              if self.graphScaling:
                self.a.set_ylim(self.a.get_ylim()[::-1])
        else:
            tailAngleSmoothed = [i for i in range(0,1)]
            self.a.plot([i for i in range(0,len(tailAngleSmoothed))],tailAngleSmoothed)
            self.a.text(0.5, 0.5, 'No bout detected for well %d' % self.numWell(), horizontalalignment='center', verticalalignment='center', transform=self.a.transAxes)
        self.canvas.draw()

    def _updateWidgets(self):
        self.zoomed_video_btn.setText("View zoomed video for well %d" % self.numWell())
        self.next_btn.setEnabled(self.numMouv() < self.nbMouv - 1 or self.numPoiss() < self.nbPoiss - 1 or self.numWell() < self.nbWells - 1)
        self.prev_btn.setEnabled(self.numMouv() or self.numPoiss() or self.numWell())
        if self.nbMouv:
          if self.dataRef["wellPoissMouv"][self.numWell()][self.numPoiss()][self.numMouv()].get("flag"):
            util.apply_style(self.flag_movement_btn, background_color='red').setText("UnFlag Movement")
          else:
            util.apply_style(self.flag_movement_btn).setText("Flag Movement")
          self.flag_movement_btn.show()
          if not self._headEmbedded:
            self.well_video_btn.setText("View video for well %d" % self.numWell())
            self.well_video_btn.show()
          else:
            self.well_video_btn.hide()
          self.bout_video_btn.show()
          if self.visualization == 0:
            text = "Tail Angle Smoothed and amplitudes for "
          elif self.visualization == 1:
            text = "Tail Angle Raw for "
          elif self.visualization == 2:
            text = "All Tail Angles Smoothed for "
          elif self.visualization == 3:
            text = "All Tail Angles Raw for "
          else:
            text = "Body Coordinates for "
          if self._headEmbedded:
            text += "bout %d" % self.numMouv()
          else:
            text += "well %d, fish %d, bout %d" % (self.numWell() , self.numPoiss(), self.numMouv())
          self.graph_title_label.setText(text)
          self.graph_title_label.show()
        else:
          self.flag_movement_btn.hide()
          self.well_video_btn.hide()
          self.bout_video_btn.hide()
          self.graph_title_label.hide()

    def flagMove(self):
        self.dataRef["wellPoissMouv"][self.numWell()][self.numPoiss()][self.numMouv()]["flag"] = int(not self.dataRef["wellPoissMouv"][self.numWell()][self.numPoiss()][self.numMouv()].get("flag", False));
        if self.dataRef["wellPoissMouv"][self.numWell()][self.numPoiss()][self.numMouv()]["flag"]:
            util.apply_style(self.flag_movement_btn, background_color='red').setText("UnFlag Movement")
        else:
            util.apply_style(self.flag_movement_btn).setText("Flag Movement")
        self.superstruct_btn.show()

    def _printSomeResults(self):
        buttonLabel = "View "
        if self.graphScaling:
          buttonLabel = buttonLabel + "Zoomed In "
        else:
          buttonLabel = buttonLabel + "Zoomed Out "
        if self.visualization == 0:
          buttonLabel = buttonLabel + "tail angle smoothed"
        elif self.visualization == 1:
          buttonLabel = buttonLabel + "tail angle raw"
        elif self.visualization == 2:
          buttonLabel = buttonLabel + "all tail angles smoothed"
        elif self.visualization == 3:
          buttonLabel = buttonLabel + "all tail angles raw"
        else:
          buttonLabel = buttonLabel + "body coordinates"
        self._viewBtn.setText(buttonLabel + " for all bouts combined")
        self._zoomBtn.setText("Zoom out Graph" if self.graphScaling else "Zoom in Graph")
        self._updateGraph()
        self._updateWidgets()
        self._updateConfigWidgets()

    def showValidationVideo(self, numWell, numAnimal, zoom, deb):
        filepath = os.path.join(self.controller.ZZoutputLocation, self.currentResultFolder, 'pathToVideo.txt')

        if os.path.exists(filepath):
            with open(filepath) as fp:
               videoPath = fp.readline()
            videoPath = videoPath[:len(videoPath)-1]
        else:
            videoPath = ""

        win = readValidationVideo(videoPath, self.currentResultFolder, '.txt', numWell, numAnimal, zoom, deb, ZZoutputLocation=self.controller.ZZoutputLocation)

    def showGraphForAllBoutsCombined(self, numWell, numPoiss, dataRef, visualization, graphScaling):

      plt.ion()
      if (visualization == 0) or (visualization == 1):

        tailAngleFinal = []
        xaxisFinal = []
        if "firstFrame" in dataRef and "lastFrame" in dataRef:
          begMove = 0
          endMove = dataRef["wellPoissMouv"][numWell][numPoiss][0]["BoutStart"]
          xaxis     = [i for i in range(begMove, endMove)]
          tailAngle = [0 for i in range(begMove, endMove)]
          tailAngleFinal = tailAngleFinal + tailAngle
          xaxisFinal = xaxisFinal + xaxis
        for numMouv in range(0, len(dataRef["wellPoissMouv"][numWell][numPoiss])):
          if (visualization == 0):
            tailAngle = dataRef["wellPoissMouv"][numWell][numPoiss][numMouv]["TailAngle_smoothed"].copy()
          else:
            tailAngle = dataRef["wellPoissMouv"][numWell][numPoiss][numMouv]["TailAngle_Raw"].copy()
          for ind,val in enumerate(tailAngle):
            tailAngle[ind]=tailAngle[ind]*(180/(math.pi))
          begMove = dataRef["wellPoissMouv"][numWell][numPoiss][numMouv]["BoutStart"]
          endMove = begMove + len(tailAngle)
          xaxis = [i for i in range(begMove-1,endMove+1)]
          tailAngle.append(0)
          tailAngle.insert(0, 0)
          tailAngleFinal = tailAngleFinal + tailAngle
          xaxisFinal = xaxisFinal + xaxis
        if "firstFrame" in dataRef and "lastFrame" in dataRef:
          begMove = endMove
          endMove = dataRef["lastFrame"] - 1
          xaxis     = [i for i in range(begMove, endMove)]
          tailAngle = [0 for i in range(begMove, endMove)]
          tailAngleFinal = tailAngleFinal + tailAngle
          xaxisFinal = xaxisFinal + xaxis
        if "fps" in dataRef:
          plt.plot([xaxisFinalVal / dataRef["fps"] for xaxisFinalVal in xaxisFinal], tailAngleFinal)
        else:
          plt.plot(xaxisFinal, tailAngleFinal)
        if not(graphScaling):
          plt.ylim(-140, 140)
        if "firstFrame" in dataRef and "lastFrame" in dataRef:
          if "fps" in dataRef:
            plt.xlim(dataRef["firstFrame"] / dataRef["fps"], dataRef["lastFrame"] / dataRef["fps"])
          else:
            plt.xlim(dataRef["firstFrame"], dataRef["lastFrame"])
        plt.show()

      else:

        headXFinal = []
        headYFinal = []
        for numMouv in range(0, len(dataRef["wellPoissMouv"][numWell][numPoiss])):
          headXFinal.extend(dataRef["wellPoissMouv"][numWell][numPoiss][numMouv]["HeadX"])
          headYFinal.extend(dataRef["wellPoissMouv"][numWell][numPoiss][numMouv]["HeadY"])
        plt.plot(headXFinal, headYFinal)
        if not(graphScaling):
          plt.xlim(0, dataRef["wellPositions"][numWell]["lengthX"])
          plt.ylim(dataRef["wellPositions"][numWell]["lengthY"], 0)
        else:
          plt.ylim(plt.ylim()[::-1])
        plt.show()

    def printNextResults(self):
        if self.numMouv() + 1 < self.nbMouv:
            self.spinbox3.setValue(self.numMouv() + 1)
        elif self.numPoiss() + 1 < self.nbPoiss:
            self.spinbox2.setValue(self.numPoiss() + 1)
            self.spinbox3.setValue(0)
        else:
            self.spinbox1.setValue(self.numWell() + 1)
            self.spinbox2.setValue(0)
            self.spinbox3.setValue(0)

    def printPreviousResults(self):
        if self.numMouv() - 1 >= 0:
            self.spinbox3.setValue(self.numMouv() - 1)
        elif self.numPoiss() - 1 >= 0:
            self.spinbox2.setValue(self.numPoiss() - 1)
            self.spinbox3.setValue(self.nbMouv - 1)
        else:
            self.spinbox1.setValue(self.numWell() - 1)
            self.spinbox2.setValue(self.nbPoiss - 1)
            self.spinbox3.setValue(self.nbMouv - 1)

    def saveSuperStruct(self):
        reference = os.path.join(self._findResultsFile(self.currentResultFolder))
        print("reference:", reference)

        with open(reference,'w') as out:
           json.dump(self.dataRef, out)

        self.superstruct_btn.hide()

    def _wellChanged(self):
        self.nbPoiss = len(self.dataRef["wellPoissMouv"][self.numWell()])
        self.spinbox2.setRange(0, self.nbPoiss - 1)
        self.nbMouv = len(self.dataRef["wellPoissMouv"][self.numWell()][self.numPoiss()])
        self.spinbox3.setRange(0, self.nbMouv - 1)
        self._updateGraph()
        self._updateWidgets()

    def _poissChanged(self):
        self.nbMouv = len(self.dataRef["wellPoissMouv"][self.numWell()][self.numPoiss()])
        self.spinbox3.setRange(0, self.nbMouv - 1)
        self._updateGraph()
        self._updateWidgets()

    def _mouvChanged(self):
        self._updateGraph()
        self._updateWidgets()


class Error(QWidget):
    def __init__(self, controller):
        super().__init__(controller.window)
        self.controller = controller

        layout = QVBoxLayout()
        layout.addWidget(QLabel("There was an error somewhere.", self), alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(QLabel("Check the command line to see what the error was.", self), alignment=Qt.AlignmentFlag.AlignCenter)

        startPageBtn = QPushButton("Go to the start page", self)
        startPageBtn.clicked.connect(lambda: controller.show_frame("StartPage"))
        layout.addWidget(startPageBtn, alignment=Qt.AlignmentFlag.AlignCenter)
        self.setLayout(layout)
