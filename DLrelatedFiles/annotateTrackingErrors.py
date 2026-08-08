"""
annotateTrackingErrors.py

Standalone PyQt5 GUI to manually review a ZebraZoom tracking run and log
false positive / false negative tracking errors to a CSV file.

Usage (run from inside the DLrelatedFiles folder):

    python annotateTrackingErrors.py

Workflow:
  1. Click "Load HDF5 results..." (top left) and choose one of the .h5
     results files in ZZoutput.
  2. The associated video is displayed together with every tracking point
     found by the tracking, for the current frame.
  3. Move through the video with the slider below it, or with the keyboard's
     Left/Right arrow keys (one press = one frame).
  4. Choose whether you are about to flag a false negative or a false
     positive with the two radio buttons above the video.
  5. Click on the video at the relevant location: a row (frame, x, y, label)
     is appended to a CSV file named after the video, saved next to the
     loaded results file.

Below the video, "Tracking points" lets you hide the tracking points
(useful to judge the raw footage on its own) and "Contrast" applies the
same contrast-enhancement used by ZebraZoom's own validation video viewer,
to make faint fish easier to see.

The "Annotation" text box near the top lets you jot down a free-text note
(e.g. "now reviewing frames 100-200") and save it as its own row (with x/y
left blank) by clicking "Save annotation" or pressing Enter -- so a typical
session looks like: write a note, click a few points across a few frames,
write another note, click a few more points, and so on, all logged to the
same CSV in the order you did them.
"""

import csv
import os
import sys

# Make the zebrazoom package importable regardless of the current working
# directory this script is launched from (it lives one folder above this
# script, in the repository root).
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import cv2
import h5py
import numpy as np

from PyQt5.QtCore import QEvent, Qt
from PyQt5.QtGui import QImage, QPixmap
from PyQt5.QtWidgets import (
    QApplication,
    QButtonGroup,
    QCheckBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QRadioButton,
    QSizePolicy,
    QSlider,
    QVBoxLayout,
    QWidget,
)

from zebrazoom.code.createValidationVideo import improveContrast
from zebrazoom.code.paths import getDefaultZZoutputFolder
from zebrazoom.videoFormatConversion.zzVideoReading import VideoCapture


FALSE_NEGATIVE_LABEL = "False negative: a fish should be detected here but isn't"
FALSE_POSITIVE_LABEL = "False positive: a fish was detected here even though there shouldn't be one"

# Tracking points are drawn as a filled circle with a thin outline so they
# stay visible regardless of the underlying frame's brightness.
POINT_RADIUS = 4
POINT_FILL_COLOR_BGR = (0, 255, 0)
POINT_OUTLINE_COLOR_BGR = (0, 0, 0)

# These match cv2.VideoCapture's numeric property ids, used here directly
# because they are also understood by zebrazoom's own VideoCapture wrapper
# (which falls back to specialized readers for .seq/.tif/.bias videos that
# only implement this small numeric subset of the OpenCV interface).
CAP_PROP_POS_FRAMES = 1
CAP_PROP_FRAME_WIDTH = 3
CAP_PROP_FRAME_HEIGHT = 4

# Passed to improveContrast, which expects a hyperparameters-style mapping;
# 0.01 is the same default ZebraZoom itself uses for the validation video's
# "Contrast" checkbox (outputValidationVideoContrastImprovementQuartile).
CONTRAST_HYPERPARAMETERS = {"outputValidationVideoContrastImprovementQuartile": 0.01}


class VideoDisplay(QLabel):
    """
    QLabel that shows a video frame scaled as large as possible while
    preserving its aspect ratio, and translates mouse clicks/moves on it
    into coordinates expressed in the ORIGINAL (unscaled) video frame's
    pixel space -- the same coordinate system the tracking data uses.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignCenter)
        self.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.setMinimumSize(1, 1)
        self.setMouseTracking(True)
        self.setStyleSheet("background-color: black;")
        # (offsetX, offsetY, displayedWidth, displayedHeight) of the currently
        # shown pixmap within this label; None until a frame has been shown.
        self._displayedRect = None
        self._frameSize = None  # (frameWidth, frameHeight) of the last frame shown

        # Callbacks set by the main window.
        self.onClick = None  # called with (frameX, frameY)
        self.onHover = None  # called with (frameX, frameY) or None
        self.onResize = None  # called with no arguments

    def showFrame(self, bgrImage):
        frameHeight, frameWidth = bgrImage.shape[:2]
        self._frameSize = (frameWidth, frameHeight)

        labelWidth = max(self.width(), 1)
        labelHeight = max(self.height(), 1)
        scale = min(labelWidth / frameWidth, labelHeight / frameHeight)
        displayedWidth = max(int(frameWidth * scale), 1)
        displayedHeight = max(int(frameHeight * scale), 1)

        resized = cv2.resize(bgrImage, (displayedWidth, displayedHeight), interpolation=cv2.INTER_AREA)
        rgb = np.ascontiguousarray(cv2.cvtColor(resized, cv2.COLOR_BGR2RGB))
        qImage = QImage(rgb.data, displayedWidth, displayedHeight, rgb.strides[0], QImage.Format_RGB888)
        # .copy() forces Qt to own its own copy of the pixel data, since `rgb`
        # (and the buffer QImage originally points to) goes out of scope right after.
        self.setPixmap(QPixmap.fromImage(qImage.copy()))

        offsetX = (labelWidth - displayedWidth) // 2
        offsetY = (labelHeight - displayedHeight) // 2
        self._displayedRect = (offsetX, offsetY, displayedWidth, displayedHeight)

    def _widgetPosToFramePoint(self, pos):
        if self._displayedRect is None or self._frameSize is None:
            return None
        offsetX, offsetY, displayedWidth, displayedHeight = self._displayedRect
        relX = pos.x() - offsetX
        relY = pos.y() - offsetY
        if relX < 0 or relY < 0 or relX >= displayedWidth or relY >= displayedHeight:
            return None  # click/hover landed outside the actual video frame (letterbox area)
        frameWidth, frameHeight = self._frameSize
        return relX * frameWidth / displayedWidth, relY * frameHeight / displayedHeight

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton and self.onClick is not None:
            point = self._widgetPosToFramePoint(event.pos())
            if point is not None:
                self.onClick(*point)
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self.onHover is not None:
            self.onHover(self._widgetPosToFramePoint(event.pos()))
        super().mouseMoveEvent(event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        if self.onResize is not None:
            self.onResize()


class AnnotationWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ZebraZoom Tracking Error Annotation Tool")
        self.resize(1300, 850)

        self._videoCapture = None
        self._csvPath = None
        self._firstFrame = 0
        self._lastFrame = 0
        # If True, this video file starts at frame 0 corresponding to
        # firstFrame (a trimmed validation-video copy) so firstFrame must be
        # subtracted before seeking. If False, the video's own frame
        # numbering already matches firstFrame/lastFrame directly (the
        # original video, or a full untouched copy of it).
        self._videoStartsAtFirstFrame = False
        # One entry per well: {'offset': (x, y), 'animals': [(xArray, yArray), ...]}
        self._pointsByWell = []

        centralWidget = QWidget()
        self.setCentralWidget(centralWidget)
        rootLayout = QVBoxLayout(centralWidget)

        topBarLayout = QHBoxLayout()
        self.loadButton = QPushButton("Load HDF5 results...")
        self.loadButton.clicked.connect(self.loadResults)
        topBarLayout.addWidget(self.loadButton)
        topBarLayout.addStretch(1)
        rootLayout.addLayout(topBarLayout)

        annotationLayout = QHBoxLayout()
        annotationLayout.addWidget(QLabel("Annotation:"))
        self.annotationTextBox = QLineEdit()
        self.annotationTextBox.setPlaceholderText(
            "Free-text description/annotation, e.g. \"Now reviewing frames 100-200, looking for false negatives near the rock\""
        )
        self.annotationTextBox.returnPressed.connect(self._saveTextAnnotation)
        annotationLayout.addWidget(self.annotationTextBox, stretch=1)
        self.saveAnnotationButton = QPushButton("Save annotation")
        self.saveAnnotationButton.clicked.connect(self._saveTextAnnotation)
        annotationLayout.addWidget(self.saveAnnotationButton)
        rootLayout.addLayout(annotationLayout)

        radioLayout = QHBoxLayout()
        self.falseNegativeRadio = QRadioButton(FALSE_NEGATIVE_LABEL)
        self.falsePositiveRadio = QRadioButton(FALSE_POSITIVE_LABEL)
        self.falseNegativeRadio.setChecked(True)
        self.annotationTypeGroup = QButtonGroup(self)
        self.annotationTypeGroup.addButton(self.falseNegativeRadio)
        self.annotationTypeGroup.addButton(self.falsePositiveRadio)
        radioLayout.addWidget(self.falseNegativeRadio)
        radioLayout.addWidget(self.falsePositiveRadio)
        radioLayout.addStretch(1)
        rootLayout.addLayout(radioLayout)

        self.videoDisplay = VideoDisplay()
        self.videoDisplay.onClick = self._handleVideoClick
        self.videoDisplay.onHover = self._handleVideoHover
        self.videoDisplay.onResize = self._redrawCurrentFrame
        rootLayout.addWidget(self.videoDisplay, stretch=1)

        sliderLayout = QHBoxLayout()
        self.frameSlider = QSlider(Qt.Horizontal)
        self.frameSlider.valueChanged.connect(lambda _value: self._redrawCurrentFrame())
        sliderLayout.addWidget(self.frameSlider, stretch=1)
        self.frameLabel = QLabel("Frame: -")
        self.frameLabel.setMinimumWidth(160)
        sliderLayout.addWidget(self.frameLabel)
        rootLayout.addLayout(sliderLayout)

        displayOptionsLayout = QHBoxLayout()
        displayOptionsLayout.addWidget(QLabel("Tracking points:"))
        self.allPointsRadio = QRadioButton("All")
        self.noPointsRadio = QRadioButton("None")
        self.allPointsRadio.setChecked(True)
        self.trackingPointsGroup = QButtonGroup(self)
        self.trackingPointsGroup.addButton(self.allPointsRadio)
        self.trackingPointsGroup.addButton(self.noPointsRadio)
        self.trackingPointsGroup.buttonToggled.connect(lambda _button, _checked: self._redrawCurrentFrame())
        displayOptionsLayout.addWidget(self.allPointsRadio)
        displayOptionsLayout.addWidget(self.noPointsRadio)
        self.contrastCheckbox = QCheckBox("Contrast")
        self.contrastCheckbox.toggled.connect(lambda _checked: self._redrawCurrentFrame())
        displayOptionsLayout.addWidget(self.contrastCheckbox)
        displayOptionsLayout.addStretch(1)
        rootLayout.addLayout(displayOptionsLayout)

        self.hoverLabel = QLabel("Mouse: -")
        rootLayout.addWidget(self.hoverLabel)

        self.statusBar().showMessage("Load an HDF5 results file to begin.")

        # Left/Right arrow keys should move the frame by one no matter which
        # widget currently has keyboard focus, so they are intercepted at the
        # application level rather than relying on a single widget's own
        # keyPressEvent.
        QApplication.instance().installEventFilter(self)

    def eventFilter(self, watchedObject, event):
        if event.type() == QEvent.KeyPress and event.key() in (Qt.Key_Left, Qt.Key_Right):
            step = 1 if event.key() == Qt.Key_Right else -1
            self.frameSlider.setValue(self.frameSlider.value() + step)
            return True
        return super().eventFilter(watchedObject, event)

    def closeEvent(self, event):
        if self._videoCapture is not None:
            self._videoCapture.release()
        super().closeEvent(event)

    # ------------------------------------------------------------------
    # Loading a results file
    # ------------------------------------------------------------------

    def loadResults(self):
        startDir = getDefaultZZoutputFolder()
        if not os.path.isdir(startDir):
            startDir = os.path.expanduser("~")
        h5Path, _ = QFileDialog.getOpenFileName(self, "Choose a ZebraZoom HDF5 results file", startDir, "HDF5 results (*.h5)")
        if not h5Path:
            return
        try:
            self._loadResultsFile(h5Path)
        except Exception as exc:
            QMessageBox.critical(self, "Could not load results", f"An error occurred while loading this results file:\n\n{exc}")

    def _loadResultsFile(self, h5Path):
        with h5py.File(h5Path, "r") as results:
            firstFrame = int(results.attrs.get("firstFrame", 0))
            lastFrame = int(results.attrs.get("lastFrame", firstFrame))
            pathToOriginalVideo = results.attrs.get("pathToOriginalVideo", None)
            if isinstance(pathToOriginalVideo, bytes):
                pathToOriginalVideo = pathToOriginalVideo.decode("utf-8")

            pointsByWell = []
            wellNames = sorted(
                (name for name in results.keys() if name.startswith("dataForWell")),
                key=lambda name: int(name[len("dataForWell"):]),
            )
            for wellName in wellNames:
                wellIndex = int(wellName[len("dataForWell"):])
                wellGroup = results[wellName]

                offsetX, offsetY = 0, 0
                wellPositionGroup = results.get(f"wellPositions/well{wellIndex}")
                if wellPositionGroup is not None:
                    offsetX = int(wellPositionGroup.attrs.get("topLeftX", 0))
                    offsetY = int(wellPositionGroup.attrs.get("topLeftY", 0))

                animalArrays = []
                animalNames = sorted(
                    (name for name in wellGroup.keys() if name.startswith("dataForAnimal")),
                    key=lambda name: int(name[len("dataForAnimal"):]),
                )
                for animalName in animalNames:
                    headPosDataset = wellGroup.get(f"{animalName}/dataPerFrame/HeadPos")
                    if headPosDataset is None:
                        continue
                    headPos = headPosDataset[:]
                    animalArrays.append((np.asarray(headPos["X"], dtype=float), np.asarray(headPos["Y"], dtype=float)))

                pointsByWell.append({"offset": (offsetX, offsetY), "animals": animalArrays})

        videoPath, videoStartsAtFirstFrame = self._resolveVideoPath(h5Path, pathToOriginalVideo)
        if videoPath is None:
            return  # user cancelled the manual video selection

        videoCapture = VideoCapture(videoPath)
        if not videoCapture.isOpened():
            QMessageBox.critical(self, "Could not open video", f"Could not open the video file:\n{videoPath}")
            return

        if self._videoCapture is not None:
            self._videoCapture.release()

        self._videoCapture = videoCapture
        self._firstFrame = firstFrame
        self._lastFrame = lastFrame
        self._videoStartsAtFirstFrame = videoStartsAtFirstFrame
        self._pointsByWell = pointsByWell

        videoBaseName = os.path.splitext(os.path.basename(videoPath))[0]
        self._csvPath = os.path.join(os.path.dirname(h5Path), f"{videoBaseName}.csv")

        self.frameSlider.blockSignals(True)
        self.frameSlider.setMinimum(firstFrame)
        self.frameSlider.setMaximum(max(lastFrame, firstFrame))
        self.frameSlider.setValue(firstFrame)
        self.frameSlider.blockSignals(False)
        self.frameSlider.setFocus()

        self.setWindowTitle(f"ZebraZoom Tracking Error Annotation Tool - {os.path.basename(h5Path)}")
        self.statusBar().showMessage(
            f"Loaded {os.path.basename(h5Path)}  |  video: {videoPath}  |  annotations saved to: {self._csvPath}"
        )

        self._redrawCurrentFrame()

    def _resolveVideoPath(self, h5Path, pathToOriginalVideo):
        """
        Figures out which video file to display for this results file, and
        whether that file's own frame numbering already matches
        firstFrame/lastFrame (the original video, or a full untouched copy
        of it) or starts at 0 for firstFrame (a trimmed validation-video
        copy, ZebraZoom's default when the original video isn't available).

        Returns (videoPath, videoStartsAtFirstFrame), or (None, None) if no
        video could be found and the user cancelled manual selection.
        """
        if pathToOriginalVideo and os.path.exists(pathToOriginalVideo):
            return pathToOriginalVideo, False

        h5Base, _ = os.path.splitext(h5Path)

        fullCopyPath = f"{h5Base}_originalVideoWithoutAnyTrackingDisplayed_pleaseUseTheGUIToVisualizeTrackingPoints.avi"
        if os.path.exists(fullCopyPath):
            return fullCopyPath, False

        trimmedCopyPath = f"{h5Base}.avi"
        if os.path.exists(trimmedCopyPath):
            return trimmedCopyPath, True

        QMessageBox.information(
            self,
            "Video not found",
            "The video associated with this results file could not be found automatically "
            "(neither the original video path stored in the results file, nor a validation "
            "video copy next to it, could be located). Please locate the video file manually.",
        )
        manualPath, _ = QFileDialog.getOpenFileName(self, "Select the video for this results file", os.path.dirname(h5Path))
        if not manualPath:
            return None, None
        return manualPath, False

    # ------------------------------------------------------------------
    # Displaying frames
    # ------------------------------------------------------------------

    def _redrawCurrentFrame(self):
        if self._videoCapture is None:
            return

        frameNumber = self.frameSlider.value()
        arrayIndex = frameNumber - self._firstFrame
        seekIndex = arrayIndex if self._videoStartsAtFirstFrame else frameNumber

        self._videoCapture.set(CAP_PROP_POS_FRAMES, seekIndex)
        ret, frame = self._videoCapture.read()
        if not ret or frame is None:
            self.frameLabel.setText(f"Frame: {frameNumber} (could not be read)")
            return

        if frame.ndim == 2:
            frame = cv2.cvtColor(frame, cv2.COLOR_GRAY2BGR)
        frame = frame.copy()

        if self.contrastCheckbox.isChecked():
            # Applied before the tracking points are drawn, same as ZebraZoom's own
            # validation video viewer, so the points themselves aren't washed out by it.
            frame = improveContrast(frame, CONTRAST_HYPERPARAMETERS)

        if self.allPointsRadio.isChecked():
            for wellData in self._pointsByWell:
                offsetX, offsetY = wellData["offset"]
                for xArray, yArray in wellData["animals"]:
                    if arrayIndex < 0 or arrayIndex >= len(xArray):
                        continue
                    x, y = xArray[arrayIndex], yArray[arrayIndex]
                    if x == 0 and y == 0:
                        continue  # (0, 0) is the "no detection this frame" convention used throughout ZebraZoom
                    point = (int(round(x + offsetX)), int(round(y + offsetY)))
                    cv2.circle(frame, point, POINT_RADIUS, POINT_FILL_COLOR_BGR, -1)
                    cv2.circle(frame, point, POINT_RADIUS, POINT_OUTLINE_COLOR_BGR, 1)

        self.videoDisplay.showFrame(frame)
        self.frameLabel.setText(f"Frame: {frameNumber} / {self._lastFrame}")

    # ------------------------------------------------------------------
    # Mouse interaction / CSV logging
    # ------------------------------------------------------------------

    def _handleVideoHover(self, point):
        if point is None:
            self.hoverLabel.setText("Mouse: -")
            return
        x, y = point
        self.hoverLabel.setText(f"Mouse: ({x:.1f}, {y:.1f})")

    def _handleVideoClick(self, x, y):
        if self._csvPath is None:
            return
        frameNumber = self.frameSlider.value()
        label = FALSE_NEGATIVE_LABEL if self.falseNegativeRadio.isChecked() else FALSE_POSITIVE_LABEL
        if not self._appendCsvRow(frameNumber, x, y, label):
            return
        self.statusBar().showMessage(f"Logged: frame {frameNumber}, ({round(x, 1)}, {round(y, 1)}), {label}", 5000)

    def _saveTextAnnotation(self):
        if self._csvPath is None:
            QMessageBox.information(self, "No results loaded", "Load an HDF5 results file first.")
            return
        text = self.annotationTextBox.text().strip()
        if not text:
            return
        frameNumber = self.frameSlider.value()
        # x/y are left blank: a free-text annotation isn't tied to a specific point, just to
        # wherever the review currently is in the video -- unlike the click-based rows above,
        # which always carry an exact (x, y) position on top of the frame number.
        if not self._appendCsvRow(frameNumber, None, None, text):
            return
        self.annotationTextBox.clear()
        self.statusBar().showMessage(f"Logged annotation at frame {frameNumber}: {text}", 5000)

    def _appendCsvRow(self, frameNumber, x, y, label):
        fileAlreadyExists = os.path.exists(self._csvPath)
        try:
            with open(self._csvPath, "a", newline="", encoding="utf-8") as csvFile:
                writer = csv.writer(csvFile)
                if not fileAlreadyExists:
                    writer.writerow(["frame", "x", "y", "label"])
                writer.writerow([frameNumber, "" if x is None else round(x, 1), "" if y is None else round(y, 1), label])
        except OSError as exc:
            QMessageBox.critical(self, "Could not write annotation", f"Failed to write to:\n{self._csvPath}\n\n{exc}")
            return False
        return True


def main():
    app = QApplication(sys.argv)
    window = AnnotationWindow()
    window.show()
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
