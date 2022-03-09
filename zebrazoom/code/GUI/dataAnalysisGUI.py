import webbrowser

try:
  from PyQt6.QtCore import Qt
  from PyQt6.QtGui import QFont, QIntValidator
  from PyQt6.QtWidgets import QLabel, QWidget, QPushButton, QLineEdit, QCheckBox, QVBoxLayout, QRadioButton, QButtonGroup
except ImportError:
  from PyQt5.QtCore import Qt
  from PyQt5.QtGui import QFont, QIntValidator
  from PyQt5.QtWidgets import QLabel, QWidget, QPushButton, QLineEdit, QCheckBox, QVBoxLayout, QRadioButton, QButtonGroup

import zebrazoom.code.util as util


class CreateExperimentOrganizationExcel(QWidget):
  def __init__(self, controller):
    super().__init__(controller.window)
    self.controller = controller

    layout = QVBoxLayout()
    layout.addWidget(util.apply_style(QLabel("Prepare experiment organization excel file:", self), font=controller.title_font), alignment=Qt.AlignmentFlag.AlignCenter)

    layout.addWidget(QLabel("To further analyze the outputs of ZebraZoom you must create an excel file to describe how you organized your experiments.", self), alignment=Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(QLabel("Click on the button below to open the folder where you should store that excel file.", self), alignment=Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(QLabel("In this folder you will also find an file named 'example' showing an example of such an excel file.", self), alignment=Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(QLabel("In these excel files, set the columns as explained below:", self), alignment=Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(QLabel("If you haven't moved the output folders of ZebraZoom, leave defaultZZoutputFolder as the value for path.", self), alignment=Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(QLabel("fq needs to be set to the frequency of acquisition of your video and pixelSize needs to be set to the number microns in each pixel of your video.", self), alignment=Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(QLabel("condition and genotype need to be set to arrays for which each element represents a well and is set the condition/genotype of that well.", self), alignment=Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(QLabel("include is an array for which each element is set to 1 if the corresponding well should be included in the analysis and 0 otherwise.", self), alignment=Qt.AlignmentFlag.AlignCenter)

    openFolderBtn = QPushButton("Open experiment organization excel files folder", self)
    openFolderBtn.clicked.connect(lambda: controller.openExperimentOrganizationExcelFolder(controller.homeDirectory))
    layout.addWidget(openFolderBtn, alignment=Qt.AlignmentFlag.AlignCenter)

    layout.addWidget(QLabel("You have to create an excel file describing the organization of your experiment and you should place it inside the folder opened with the button above.", self), alignment=Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(QLabel("Once this is done, click on the button below:", self), alignment=Qt.AlignmentFlag.AlignCenter)

    okBtn = util.apply_style(QPushButton("Ok done!", self), background_color=util.LIGHT_YELLOW)
    okBtn.clicked.connect(lambda: controller.show_frame("ChooseExperimentOrganizationExcel"))
    layout.addWidget(okBtn, alignment=Qt.AlignmentFlag.AlignCenter)
    startPageBtn = util.apply_style(QPushButton("Go to the start page", self), background_color=util.LIGHT_CYAN)
    startPageBtn.clicked.connect(lambda: controller.show_frame("StartPage"))
    layout.addWidget(startPageBtn, alignment=Qt.AlignmentFlag.AlignCenter)

    layout.addWidget(QLabel("If you already analyzed data and you just want to view previous results, click on one of the button above:", self), alignment=Qt.AlignmentFlag.AlignCenter)
    previousParameterResultsBtn = util.apply_style(QPushButton("View previous kinematic parameter analysis results", self), background_color=util.LIGHT_YELLOW)
    previousParameterResultsBtn.clicked.connect(lambda: controller.show_frame("AnalysisOutputFolderPopulation"))
    layout.addWidget(previousParameterResultsBtn, alignment=Qt.AlignmentFlag.AlignCenter)
    previousClusteringResultsBtn = util.apply_style(QPushButton("View previous clustering analysis results", self), background_color=util.LIGHT_YELLOW)
    previousClusteringResultsBtn.clicked.connect(lambda: controller.show_frame("AnalysisOutputFolderClustering"))
    layout.addWidget(previousClusteringResultsBtn, alignment=Qt.AlignmentFlag.AlignCenter)

    self.setLayout(layout)


class ChooseExperimentOrganizationExcel(QWidget):
  def __init__(self, controller):
    super().__init__(controller.window)
    self.controller = controller

    layout = QVBoxLayout()
    layout.addWidget(util.apply_style(QLabel("Choose organization excel file:", self), font=controller.title_font), alignment=Qt.AlignmentFlag.AlignCenter)
    selectFileBtn = util.apply_style(QPushButton("Select the excel file describing the organization of your experiment.", self), background_color=util.LIGHT_YELLOW)
    selectFileBtn.clicked.connect(lambda: controller.chooseExperimentOrganizationExcel(controller))
    layout.addWidget(selectFileBtn, alignment=Qt.AlignmentFlag.AlignCenter)
    startPageBtn = util.apply_style(QPushButton("Go to the start page", self), background_color=util.LIGHT_CYAN)
    startPageBtn.clicked.connect(lambda: controller.show_frame("StartPage"))
    layout.addWidget(startPageBtn, alignment=Qt.AlignmentFlag.AlignCenter)

    self.setLayout(layout)


class ChooseDataAnalysisMethod(QWidget):
  def __init__(self, controller):
    super().__init__(controller.window)
    self.controller = controller

    layout = QVBoxLayout()
    layout.addWidget(util.apply_style(QLabel("Choose the analysis you want to perform:", self), font=controller.title_font), alignment=Qt.AlignmentFlag.AlignCenter)

    compareBtn = util.apply_style(QPushButton("Compare populations with kinematic parameters", self), background_color=util.LIGHT_YELLOW)
    compareBtn.clicked.connect(lambda: controller.show_frame("PopulationComparison"))
    layout.addWidget(compareBtn, alignment=Qt.AlignmentFlag.AlignCenter)
    clusterBtn = util.apply_style(QPushButton("Cluster bouts of movements  (for zebrafish only)", self), background_color=util.LIGHT_YELLOW)
    clusterBtn.clicked.connect(lambda: controller.show_frame("BoutClustering"))
    layout.addWidget(clusterBtn, alignment=Qt.AlignmentFlag.AlignCenter)

    startPageBtn = util.apply_style(QPushButton("Go to the start page", self), background_color=util.LIGHT_CYAN)
    startPageBtn.clicked.connect(lambda: controller.show_frame("StartPage"))
    layout.addWidget(startPageBtn, alignment=Qt.AlignmentFlag.AlignCenter)

    self.setLayout(layout)


class PopulationComparison(QWidget):
  def __init__(self, controller):
    super().__init__(controller.window)
    self.controller = controller

    layout = QVBoxLayout()
    layout.addWidget(util.apply_style(QLabel("Population Comparison:", self), font=controller.title_font), alignment=Qt.AlignmentFlag.AlignCenter)

    tailTrackingParametersCheckbox = QCheckBox("I want fish tail tracking related kinematic parameters (number of oscillation, tail beat frequency, etc..) to be calculated.", self)
    layout.addWidget(tailTrackingParametersCheckbox, alignment=Qt.AlignmentFlag.AlignCenter)
    saveInMatlabFormatCheckbox = QCheckBox("The result structure is always saved in the pickle format. Also save it in the matlab format.", self)
    layout.addWidget(saveInMatlabFormatCheckbox, alignment=Qt.AlignmentFlag.AlignCenter)
    saveRawDataCheckbox = QCheckBox("Save original raw data in result structure.", self)
    layout.addWidget(saveRawDataCheckbox, alignment=Qt.AlignmentFlag.AlignCenter)
    forcePandasRecreation = QCheckBox("Force recalculation of all parameters even if they have already been calculated and saved.", self)
    layout.addWidget(forcePandasRecreation, alignment=Qt.AlignmentFlag.AlignCenter)

    layout.addWidget(util.apply_style(QLabel("Number of frames between each frame used for distance calculation (to avoid noise due to close-by subsequent points) (default value is 4):", self), font=QFont("Helvetica", 10)), alignment=Qt.AlignmentFlag.AlignCenter)
    frameStepForDistanceCalculation = QLineEdit(controller.window)
    frameStepForDistanceCalculation.setValidator(QIntValidator(frameStepForDistanceCalculation))
    frameStepForDistanceCalculation.validator().setBottom(0)
    layout.addWidget(frameStepForDistanceCalculation, alignment=Qt.AlignmentFlag.AlignCenter)

    layout.addWidget(util.apply_style(QLabel("If you are calculating fish tail tracking related kinematic parameters:", self), font_size="16px"), alignment=Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(util.apply_style(QLabel("What's the minimum number of bends a bout should have to be taken into account for the analysis?", self), font=QFont("Helvetica", 10)), alignment=Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(util.apply_style(QLabel("(the default value is 3) (put 0 if you want all bends to be taken into account)", self), font=QFont("Helvetica", 10)), alignment=Qt.AlignmentFlag.AlignCenter)
    minNbBendForBoutDetect = QLineEdit(controller.window)
    minNbBendForBoutDetect.setValidator(QIntValidator(minNbBendForBoutDetect))
    minNbBendForBoutDetect.validator().setBottom(0)
    layout.addWidget(minNbBendForBoutDetect, alignment=Qt.AlignmentFlag.AlignCenter)

    layout.addWidget(util.apply_style(QLabel("If, for a bout, the tail tracking related kinematic parameters are being discarded because of a low amount of bends,", self), font=QFont("Helvetica", 10)), alignment=Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(util.apply_style(QLabel("should the BoutDuration, TotalDistance, Speed and IBI also be discarded for that bout?", self), font=QFont("Helvetica", 10)), alignment=Qt.AlignmentFlag.AlignCenter)
    discardRadioButton = QRadioButton("Yes, discard BoutDuration, TotalDistance, Speed and IBI in that situation", self)
    discardRadioButton.setChecked(True)
    layout.addWidget(discardRadioButton, alignment=Qt.AlignmentFlag.AlignCenter)
    keepRadioButton = QRadioButton("No, keep BoutDuration, TotalDistance, Speed and IBI in that situation", self)
    layout.addWidget(keepRadioButton, alignment=Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(util.apply_style(QLabel("Please ignore the two questions above if you're only looking at BoutDuration, TotalDistance, Speed and IBI.", self), font=QFont("Helvetica", 10)), alignment=Qt.AlignmentFlag.AlignCenter)

    launchBtn = util.apply_style(QPushButton("Launch Analysis", self), background_color=util.LIGHT_YELLOW)
    launchBtn.clicked.connect(lambda: controller.populationComparison(controller, tailTrackingParametersCheckbox.isChecked(), saveInMatlabFormatCheckbox.isChecked(), saveRawDataCheckbox.isChecked(), forcePandasRecreation.isChecked(), minNbBendForBoutDetect.text(), discardRadioButton.isChecked(), keepRadioButton.isChecked(), frameStepForDistanceCalculation.text()))
    layout.addWidget(launchBtn, alignment=Qt.AlignmentFlag.AlignCenter)
    startPageBtn = util.apply_style(QPushButton("Go to the start page", self), background_color=util.LIGHT_CYAN)
    startPageBtn.clicked.connect(lambda: controller.show_frame("StartPage"))
    layout.addWidget(startPageBtn, alignment=Qt.AlignmentFlag.AlignCenter)

    self.setLayout(layout)


class BoutClustering(QWidget):
  def __init__(self, controller):
    super().__init__(controller.window)
    self.controller = controller

    layout = QVBoxLayout()
    layout.addWidget(util.apply_style(QLabel("Bout Clustering:", self), font=controller.title_font), alignment=Qt.AlignmentFlag.AlignCenter)

    layout.addWidget(QLabel("Choose number of cluster to find:", self), alignment=Qt.AlignmentFlag.AlignCenter)
    nbClustersToFind = QLineEdit(controller.window)
    nbClustersToFind.setValidator(QIntValidator(nbClustersToFind))
    nbClustersToFind.validator().setBottom(0)
    layout.addWidget(nbClustersToFind, alignment=Qt.AlignmentFlag.AlignCenter)

    layout.addWidget(QLabel("Choose one of the options below:", self), alignment=Qt.AlignmentFlag.AlignCenter)
    freelySwimmingRadioButton = QRadioButton("Freely swimming fish with tail tracking", self)
    freelySwimmingRadioButton.setChecked(True)
    layout.addWidget(freelySwimmingRadioButton, alignment=Qt.AlignmentFlag.AlignCenter)
    headEmbeddedRadioButton = QRadioButton("Head embeded fish with tail tracking", self)
    layout.addWidget(headEmbeddedRadioButton, alignment=Qt.AlignmentFlag.AlignCenter)


    layout.addWidget(util.apply_style(QLabel("What's the minimum number of bends a bout should have to be taken into account for the analysis?", self), font=QFont("Helvetica", 10)), alignment=Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(util.apply_style(QLabel("(the default value is 3) (put 0 if you want all bends to be taken into account)", self), font=QFont("Helvetica", 10)), alignment=Qt.AlignmentFlag.AlignCenter)
    minNbBendForBoutDetect = QLineEdit(controller.window)
    minNbBendForBoutDetect.setValidator(QIntValidator(minNbBendForBoutDetect))
    minNbBendForBoutDetect.validator().setBottom(0)
    layout.addWidget(minNbBendForBoutDetect, alignment=Qt.AlignmentFlag.AlignCenter)

    layout.addWidget(util.apply_style(QLabel("Optional: generate videos containing the most representative bouts for each cluster: enter below the number of bouts for each video:", self), font=QFont("Helvetica", 10)), alignment=Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(util.apply_style(QLabel("(leave blank if you don't want any such cluster validation videos to be generated)", self), font=QFont("Helvetica", 10)), alignment=Qt.AlignmentFlag.AlignCenter)
    nbVideosToSave = QLineEdit(controller.window)
    nbVideosToSave.setValidator(QIntValidator(nbVideosToSave))
    nbVideosToSave.validator().setBottom(0)
    layout.addWidget(nbVideosToSave, alignment=Qt.AlignmentFlag.AlignCenter)

    modelUsedForClusteringCheckbox = QCheckBox("Use GMM clustering method instead of Kmeans (clustering method used by default)", self)
    layout.addWidget(modelUsedForClusteringCheckbox, alignment=Qt.AlignmentFlag.AlignCenter)
    removeOutliersCheckbox = QCheckBox("Remove outliers before clustering", self)
    layout.addWidget(removeOutliersCheckbox, alignment=Qt.AlignmentFlag.AlignCenter)

    layout.addWidget(util.apply_style(QLabel("Number of frames between each frame used for distance calculation (to avoid noise due to close-by subsequent points) (default value is 4):", self), font=QFont("Helvetica", 10)), alignment=Qt.AlignmentFlag.AlignCenter)
    frameStepForDistanceCalculation = QLineEdit(controller.window)
    frameStepForDistanceCalculation.setValidator(QIntValidator(frameStepForDistanceCalculation))
    frameStepForDistanceCalculation.validator().setBottom(0)
    layout.addWidget(frameStepForDistanceCalculation, alignment=Qt.AlignmentFlag.AlignCenter)
    
    removeBoutsContainingNanValuesInParametersUsedForClustering = QCheckBox("Remove bouts containing nan values in parameters used for clustering", self)
    removeBoutsContainingNanValuesInParametersUsedForClustering.setChecked(True)
    layout.addWidget(removeBoutsContainingNanValuesInParametersUsedForClustering, alignment=Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(util.apply_style(QLabel("If the box above is un-checked, the nan values will be replaced by zeros and no bouts will be removed.", self), font=QFont("Helvetica", 10)), alignment=Qt.AlignmentFlag.AlignCenter)
    
    forcePandasRecreation = QCheckBox("Force recalculation of all parameters even if they have already been calculated and saved.", self)
    layout.addWidget(forcePandasRecreation, alignment=Qt.AlignmentFlag.AlignCenter)

    launchBtn = util.apply_style(QPushButton("Launch Analysis", self), background_color=util.LIGHT_YELLOW)
    launchBtn.clicked.connect(lambda: controller.boutClustering(controller, nbClustersToFind.text(), freelySwimmingRadioButton.isChecked(), headEmbeddedRadioButton.isChecked(), minNbBendForBoutDetect.text(), nbVideosToSave.text(), modelUsedForClusteringCheckbox.isChecked(), removeOutliersCheckbox.isChecked(), frameStepForDistanceCalculation.text(), removeBoutsContainingNanValuesInParametersUsedForClustering.isChecked(), forcePandasRecreation.isChecked()))
    layout.addWidget(launchBtn, alignment=Qt.AlignmentFlag.AlignCenter)
    startPageBtn = util.apply_style(QPushButton("Go to the start page", self), background_color=util.LIGHT_CYAN)
    startPageBtn.clicked.connect(lambda: controller.show_frame("StartPage"))
    layout.addWidget(startPageBtn, alignment=Qt.AlignmentFlag.AlignCenter)

    self.setLayout(layout)


class AnalysisOutputFolderPopulation(QWidget):
  def __init__(self, controller):
    super().__init__(controller.window)
    self.controller = controller

    layout = QVBoxLayout()
    layout.addWidget(util.apply_style(QLabel("View Analysis Output:", self), font=controller.title_font), alignment=Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(QLabel("Click the button below to open the folder that contains the results of the analysis.", self), alignment=Qt.AlignmentFlag.AlignCenter)

    viewProcessedBtn = util.apply_style(QPushButton("View 'plots and processed data' folders", self), background_color=util.LIGHT_YELLOW)
    viewProcessedBtn.clicked.connect(lambda: controller.openAnalysisFolder(controller.homeDirectory, 'resultsKinematic'))
    layout.addWidget(viewProcessedBtn, alignment=Qt.AlignmentFlag.AlignCenter)
    viewRawBtn = util.apply_style(QPushButton("View raw data", self), background_color=util.LIGHT_YELLOW)
    viewRawBtn.clicked.connect(lambda: controller.openAnalysisFolder(controller.homeDirectory, 'data'))
    layout.addWidget(viewRawBtn, alignment=Qt.AlignmentFlag.AlignCenter)
    startPageBtn = util.apply_style(QPushButton("Go to the start page", self), background_color=util.LIGHT_CYAN)
    startPageBtn.clicked.connect(lambda: controller.show_frame("StartPage"))
    layout.addWidget(startPageBtn, alignment=Qt.AlignmentFlag.AlignCenter)

    linkBtn = util.apply_style(QPushButton("Video data analysis online documentation", self), background_color=util.LIGHT_YELLOW)
    linkBtn.clicked.connect(lambda: webbrowser.open_new("https://zebrazoom.org/documentation/docs/behaviorAnalysis/behaviorAnalysisGUI"))
    layout.addWidget(linkBtn, alignment=Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(QLabel("(read the 'Further analyzing ZebraZoom's output through the Graphical User Interface' section)", self), alignment=Qt.AlignmentFlag.AlignCenter)

    self.setLayout(layout)


class AnalysisOutputFolderClustering(QWidget):
  def __init__(self, controller):
    super().__init__(controller.window)
    self.controller = controller

    layout = QVBoxLayout()
    layout.addWidget(util.apply_style(QLabel("View Analysis Output:", self), font=controller.title_font), alignment=Qt.AlignmentFlag.AlignCenter)
    layout.addWidget(QLabel("Click the button below to open the folder that contains the results of the analysis.", self), alignment=Qt.AlignmentFlag.AlignCenter)

    viewProcessedBtn = util.apply_style(QPushButton("View plots and processed data folder", self), background_color=util.LIGHT_YELLOW)
    viewProcessedBtn.clicked.connect(lambda: controller.openAnalysisFolder(controller.homeDirectory, 'resultsClustering'))
    layout.addWidget(viewProcessedBtn, alignment=Qt.AlignmentFlag.AlignCenter)
    viewRawBtn = util.apply_style(QPushButton("View raw data folders", self), background_color=util.LIGHT_YELLOW)
    viewRawBtn.clicked.connect(lambda: controller.openAnalysisFolder(controller.homeDirectory, 'data'))
    layout.addWidget(viewRawBtn, alignment=Qt.AlignmentFlag.AlignCenter)

    startPageBtn = util.apply_style(QPushButton("Go to the start page", self), background_color=util.LIGHT_CYAN)
    startPageBtn.clicked.connect(lambda: controller.show_frame("StartPage"))
    layout.addWidget(startPageBtn, alignment=Qt.AlignmentFlag.AlignCenter)

    self.setLayout(layout)
