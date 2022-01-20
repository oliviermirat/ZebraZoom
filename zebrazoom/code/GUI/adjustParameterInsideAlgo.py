from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont, QIntValidator
from PyQt6.QtWidgets import QLabel, QGridLayout, QLineEdit, QWidget, QCheckBox, QPushButton, QVBoxLayout, QRadioButton, QButtonGroup


LIGHT_CYAN = '#E0FFFF'


def apply_style(widget, **kwargs):
    if (font := kwargs.pop('font', None)) is not None:
        widget.setFont(font)
    widget.setStyleSheet(';'.join('%s: %s' % (prop.replace('_', '-'), val)  for prop, val in kwargs.items()))
    return widget


class AdujstParamInsideAlgo(QWidget):
  def __init__(self, controller):
    super().__init__(controller.window)
    self.controller = controller

    layout = QVBoxLayout()
    layout.addWidget(apply_style(QLabel("Advanced Parameter adjustment", self), font=controller.title_font), alignment=Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(apply_style(QLabel("Recalculate background using this number of images: (default is 60)", self), font=QFont("Helvetica", 10)), alignment=Qt.AlignmentFlag.AlignCenter)
    nbImagesForBackgroundCalculation = QLineEdit(controller.window)
    nbImagesForBackgroundCalculation.setValidator(QIntValidator(nbImagesForBackgroundCalculation))
    nbImagesForBackgroundCalculation.validator().setBottom(0)
    layout.addWidget(nbImagesForBackgroundCalculation, alignment=Qt.AlignmentFlag.AlignCenter)
    recalculateBtn = QPushButton("Recalculate", self)
    recalculateBtn.clicked.connect(lambda: controller.calculateBackground(controller, nbImagesForBackgroundCalculation.text()))
    layout.addWidget(recalculateBtn, alignment=Qt.AlignmentFlag.AlignCenter)

    firstFrameParamAdjustCheckbox = QCheckBox("Choose the first frame for parameter adjustment (for both bouts detection and tracking)", self)
    layout.addWidget(firstFrameParamAdjustCheckbox, alignment=Qt.AlignmentFlag.AlignCenter)
    adjustOnWholeVideoCheckbox = QCheckBox("I want to adjust parameters over the entire video, not only on 500 frames at a time.", self)
    layout.addWidget(adjustOnWholeVideoCheckbox, alignment=Qt.AlignmentFlag.AlignCenter)

    adjustBoutsBtn = QPushButton("Adjust Bouts Detection", self)
    adjustBoutsBtn.clicked.connect(lambda: controller.detectBouts(controller, "0", firstFrameParamAdjustCheckbox.isChecked(), adjustOnWholeVideoCheckbox.isChecked()))
    layout.addWidget(adjustBoutsBtn, alignment=Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(apply_style(QLabel("The aim here is to adjust parameters in order for the red dot on the top left of the image to appear when and only when movement is occurring.", self), font=QFont("Helvetica", 10)), alignment=Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(apply_style(QLabel("WARNING: if you don't want ZebraZoom to detect bouts, don't click on the button above.", self), font=QFont("Helvetica", 10)), alignment=Qt.AlignmentFlag.AlignCenter)

    adjustTrackingBtn = QPushButton("Adjust Tracking", self)
    adjustTrackingBtn.clicked.connect(lambda: controller.adjustHeadEmbededTracking(controller, "0", firstFrameParamAdjustCheckbox.isChecked(), adjustOnWholeVideoCheckbox.isChecked()))
    layout.addWidget(adjustTrackingBtn, alignment=Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(apply_style(QLabel("WARNING: only click the button above if you've tried to track without adjusting these parameters first. Trying to adjust these could make the tracking worse.", self), font=QFont("Helvetica", 10)), alignment=Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(apply_style(QLabel('Warning: for some of the "overwrite" parameters, you will need to change the initial value for the "overwrite" to take effect.', self), font=QFont("Helvetica", 10)), alignment=Qt.AlignmentFlag.AlignCenter)

    nextBtn = QPushButton("Next", self)
    nextBtn.clicked.connect(lambda: controller.show_frame("FinishConfig"))
    layout.addWidget(nextBtn, alignment=Qt.AlignmentFlag.AlignCenter)

    self.setLayout(layout)


class AdujstParamInsideAlgoFreelySwim(QWidget):
  def __init__(self, controller):
    super().__init__(controller.window)
    self.controller = controller

    layout = QVBoxLayout()
    layout.addWidget(apply_style(QLabel("Advanced Parameter adjustment", self), font=controller.title_font), alignment=Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(apply_style(QLabel("Well number used to adjust parameters (leave blank to get the default value of 0)", self), font=QFont("Helvetica", 10)), alignment=Qt.AlignmentFlag.AlignCenter)
    wellNumber = QLineEdit(controller.window)
    wellNumber.setValidator(QIntValidator(wellNumber))
    wellNumber.validator().setBottom(0)
    layout.addWidget(wellNumber, alignment=Qt.AlignmentFlag.AlignCenter)

    layout.addWidget(apply_style(QLabel("Recalculate background using this number of images: (default is 60)", self), font=QFont("Helvetica", 10)), alignment=Qt.AlignmentFlag.AlignCenter)
    nbImagesForBackgroundCalculation = QLineEdit(controller.window)
    nbImagesForBackgroundCalculation.setValidator(QIntValidator(nbImagesForBackgroundCalculation))
    nbImagesForBackgroundCalculation.validator().setBottom(0)
    layout.addWidget(nbImagesForBackgroundCalculation, alignment=Qt.AlignmentFlag.AlignCenter)
    recalculateBtn = QPushButton("Recalculate", self)
    recalculateBtn.clicked.connect(lambda: controller.calculateBackgroundFreelySwim(controller, nbImagesForBackgroundCalculation.text()))
    layout.addWidget(recalculateBtn, alignment=Qt.AlignmentFlag.AlignCenter)

    firstFrameParamAdjustCheckbox = QCheckBox("Choose the first frame for parameter adjustment (for both bouts detection and tracking)", self)
    layout.addWidget(firstFrameParamAdjustCheckbox, alignment=Qt.AlignmentFlag.AlignCenter)
    adjustOnWholeVideoCheckbox = QCheckBox("I want to adjust parameters over the entire video, not only on 500 frames at a time.", self)
    layout.addWidget(adjustOnWholeVideoCheckbox, alignment=Qt.AlignmentFlag.AlignCenter)

    adjustBoutsBtn = QPushButton("Adjust Bouts Detection", self)
    adjustBoutsBtn.clicked.connect(lambda: controller.detectBouts(controller, wellNumber.text(), firstFrameParamAdjustCheckbox.isChecked(), adjustOnWholeVideoCheckbox.isChecked()))
    layout.addWidget(adjustBoutsBtn, alignment=Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(apply_style(QLabel("The aim here is to adjust parameters in order for the red dot on the top left of the image to appear when and only when movement is occurring.", self), font=QFont("Helvetica", 10)), alignment=Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(apply_style(QLabel("WARNING: if you don't want ZebraZoom to detect bouts, don't click on the button above.", self), font=QFont("Helvetica", 10)), alignment=Qt.AlignmentFlag.AlignCenter)

    adjustTrackingBtn = QPushButton("Adjust Tracking", self)
    adjustTrackingBtn.clicked.connect(lambda: controller.adjustFreelySwimTracking(controller, "0", firstFrameParamAdjustCheckbox.isChecked(), adjustOnWholeVideoCheckbox.isChecked()))
    layout.addWidget(adjustTrackingBtn, alignment=Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(apply_style(QLabel("WARNING: only click the button above if you've tried to track without adjusting these parameters first. Trying to adjust these could make the tracking worse.", self), font=QFont("Helvetica", 10)), alignment=Qt.AlignmentFlag.AlignCenter)

    nextBtn = QPushButton("Next", self)
    nextBtn.clicked.connect(lambda: controller.show_frame("FinishConfig"))
    layout.addWidget(nextBtn, alignment=Qt.AlignmentFlag.AlignCenter)

    self.setLayout(layout)


class AdujstParamInsideAlgoFreelySwimAutomaticParameters(QWidget):
  def __init__(self, controller):
    super().__init__(controller.window)
    self.controller = controller

    layout = QGridLayout()
    layout.addWidget(apply_style(QLabel("Fish tail tracking parameters adjustment", self), font=controller.title_font), 0, 0, 1, 2, Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(apply_style(QLabel("Well number used to adjust parameters (leave blank to get the default value of 0)", self), font=QFont("Helvetica", 10)), 1, 0, Qt.AlignmentFlag.AlignCenter)
    wellNumber = QLineEdit(controller.window)
    wellNumber.setValidator(QIntValidator(wellNumber))
    wellNumber.validator().setBottom(0)
    layout.addWidget(wellNumber, 2, 0, Qt.AlignmentFlag.AlignCenter)

    layout.addWidget(apply_style(QLabel("Recalculate background using this number of images: (default is 60)", self), font=QFont("Helvetica", 10)), 1, 1, Qt.AlignmentFlag.AlignCenter)
    nbImagesForBackgroundCalculation = QLineEdit(controller.window)
    nbImagesForBackgroundCalculation.setValidator(QIntValidator(nbImagesForBackgroundCalculation))
    nbImagesForBackgroundCalculation.validator().setBottom(0)
    layout.addWidget(nbImagesForBackgroundCalculation, 2, 1, Qt.AlignmentFlag.AlignCenter)
    recalculateBtn = QPushButton("Recalculate", self)
    recalculateBtn.clicked.connect(lambda: controller.calculateBackgroundFreelySwim(controller, nbImagesForBackgroundCalculation.text(), False, True))
    layout.addWidget(recalculateBtn, 3, 1, Qt.AlignmentFlag.AlignCenter)

    firstFrameParamAdjustCheckbox = QCheckBox("Choose the first frame for parameter adjustment (for both bouts detection and tracking)", self)
    layout.addWidget(firstFrameParamAdjustCheckbox, 3, 0, Qt.AlignmentFlag.AlignCenter)
    adjustOnWholeVideoCheckbox = QCheckBox("I want to adjust parameters over the entire video, not only on 500 frames at a time.", self)
    layout.addWidget(adjustOnWholeVideoCheckbox, 4, 0, Qt.AlignmentFlag.AlignCenter)

    adjustTrackingBtn = QPushButton("Adjust Tracking", self)
    adjustTrackingBtn.clicked.connect(lambda: controller.adjustFreelySwimTrackingAutomaticParameters(controller, wellNumber.text(), firstFrameParamAdjustCheckbox.isChecked(), adjustOnWholeVideoCheckbox.isChecked()))
    layout.addWidget(adjustTrackingBtn, 7, 0, 1, 2, Qt.AlignmentFlag.AlignCenter)

    layout.addWidget(QLabel("The tracking of ZebraZoom can rely on three different background extraction methods:", self), 9, 0, 1, 2, Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(QLabel("Method 1: background extraction is based on a simple threshold on pixel intensity. This method is the fastest.", self), 10, 0, 1, 2, Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(QLabel("Method 2: the background extraction threshold is automatically chosen in order for the fish body area to be close to a predefined area. This method is slower but often more accurate.", self), 11, 0, 1, 2, Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(QLabel("Method 3: the background extraction threshold is automatically chosen on a ROI in order for the fish body area to be close to a predefined area. This method is the slowest but often the most accurate.", self), 12, 0, 1, 2, Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(QLabel("It is usually advise to choose the method 3, but there are many circumstances in which method 1 or 2 are better.", self), 13, 0, 1, 2, Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(QLabel("The 'Adjust Tracking' method above will allow you to choose which method you want to use and to adjust parameters related to this method.", self), 14, 0, 1, 2, Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(QLabel("WARNING: only click the button above if you've tried to track without adjusting these parameters first. Trying to adjust these could make the tracking worse.", self), 15, 0, 1, 2, Qt.AlignmentFlag.AlignCenter)

    nextBtn = QPushButton("Save New Configuration File", self)
    nextBtn.clicked.connect(lambda: controller.show_frame("FinishConfig"))
    layout.addWidget(nextBtn, 17, 0, 1, 2, Qt.AlignmentFlag.AlignCenter)

    start_page_btn = apply_style(QPushButton("Go to the start page", self), background_color=LIGHT_CYAN)
    start_page_btn.clicked.connect(lambda: controller.show_frame("StartPage"))
    layout.addWidget(start_page_btn, 19, 0, 1, 2, Qt.AlignmentFlag.AlignCenter)

    self.setLayout(layout)


class AdujstBoutDetectionOnly(QWidget):
  def __init__(self, controller):
    super().__init__(controller.window)
    self.controller = controller

    layout = QVBoxLayout()
    layout.addWidget(apply_style(QLabel("Bout detection configuration file parameters adjustments", self), font=controller.title_font), alignment=Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(apply_style(QLabel("Well number used to adjust parameters (leave blank to get the default value of 0)", self), font=QFont("Helvetica", 10)), alignment=Qt.AlignmentFlag.AlignCenter)
    wellNumber = QLineEdit(controller.window)
    wellNumber.setValidator(QIntValidator(wellNumber))
    wellNumber.validator().setBottom(0)
    layout.addWidget(wellNumber, alignment=Qt.AlignmentFlag.AlignCenter)

    layout.addWidget(apply_style(QLabel("Recalculate background using this number of images: (default is 60)", self), font=QFont("Helvetica", 10)), alignment=Qt.AlignmentFlag.AlignCenter)
    nbImagesForBackgroundCalculation = QLineEdit(controller.window)
    nbImagesForBackgroundCalculation.setValidator(QIntValidator(nbImagesForBackgroundCalculation))
    nbImagesForBackgroundCalculation.validator().setBottom(0)
    layout.addWidget(nbImagesForBackgroundCalculation, alignment=Qt.AlignmentFlag.AlignCenter)
    recalculateBtn = QPushButton("Recalculate", self)
    recalculateBtn.clicked.connect(lambda: controller.calculateBackgroundFreelySwim(controller, nbImagesForBackgroundCalculation.text(), False, False, True))
    layout.addWidget(recalculateBtn, alignment=Qt.AlignmentFlag.AlignCenter)

    firstFrameParamAdjustCheckbox = QCheckBox("Choose the first frame for parameter adjustment (for both bouts detection and tracking)", self)
    layout.addWidget(firstFrameParamAdjustCheckbox, alignment=Qt.AlignmentFlag.AlignCenter)
    adjustOnWholeVideoCheckbox = QCheckBox("I want to adjust parameters over the entire video, not only on 500 frames at a time.", self)
    layout.addWidget(adjustOnWholeVideoCheckbox, alignment=Qt.AlignmentFlag.AlignCenter)

    adjustBoutsBtn = QPushButton("Adjust Bouts Detection", self)
    adjustBoutsBtn.clicked.connect(lambda: controller.detectBouts(controller, wellNumber.text(), firstFrameParamAdjustCheckbox.isChecked(), adjustOnWholeVideoCheckbox.isChecked()))
    layout.addWidget(adjustBoutsBtn, alignment=Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(apply_style(QLabel("The aim here is to adjust parameters in order for the red dot on the top left of the image to appear when and only when movement is occurring.", self), font=QFont("Helvetica", 10)), alignment=Qt.AlignmentFlag.AlignCenter)

    layout.addWidget(apply_style(QLabel("Important: Bouts Merging:", self), font=QFont("Helvetica", 0)), alignment=Qt.AlignmentFlag.AlignCenter)
    fillGapFrameNb = QLineEdit(controller.window)
    fillGapFrameNb.setValidator(QIntValidator(fillGapFrameNb))
    fillGapFrameNb.validator().setBottom(0)
    layout.addWidget(fillGapFrameNb, alignment=Qt.AlignmentFlag.AlignCenter)
    updateFillGapBtn = QPushButton("With the box above, update the 'fillGapFrameNb' parameter that controls the distance (in number frames) under which two subsquent bouts are merged into one.", self)
    updateFillGapBtn.clicked.connect(lambda: controller.updateFillGapFrameNb(fillGapFrameNb.text()))
    layout.addWidget(updateFillGapBtn, alignment=Qt.AlignmentFlag.AlignCenter)

    nextBtn = QPushButton("Next", self)
    nextBtn.clicked.connect(lambda: controller.show_frame("FinishConfig"))
    layout.addWidget(nextBtn, alignment=Qt.AlignmentFlag.AlignCenter)
    start_page_btn = apply_style(QPushButton("Go to the start page", self), background_color=LIGHT_CYAN)
    start_page_btn.clicked.connect(lambda: controller.show_frame("StartPage"))
    layout.addWidget(start_page_btn, alignment=Qt.AlignmentFlag.AlignCenter)

    self.setLayout(layout)
