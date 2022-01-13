import webbrowser

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont
from PyQt6.QtWidgets import QLabel, QWidget, QGridLayout, QPushButton, QHBoxLayout, QVBoxLayout, QCheckBox


LARGE_FONT= ("Verdana", 12)
LIGHT_YELLOW = '#FFFFE0'
LIGHT_CYAN = '#E0FFFF'
GOLD = '#FFD700'


def apply_style(widget, **kwargs):
    if (font := kwargs.pop('font', None)) is not None:
        widget.setFont(font)
    widget.setStyleSheet(';'.join('%s: %s' % (prop.replace('_', '-'), val)  for prop, val in kwargs.items()))
    return widget


class StartPage(QWidget):
    def __init__(self, controller):
        super().__init__(controller.window)
        self.controller = controller

        layout = QGridLayout()
        # Add widgets to the layout
        layout.addWidget(apply_style(QLabel("Welcome to ZebraZoom!", self), font=controller.title_font, color='purple'), 0, 0, 1, 2, Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(apply_style(QLabel("1 - Create a Configuration File:", self), color='blue', font_size='16px'), 1, 0, Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(apply_style(QLabel("You first need to create a configuration file for each 'type' of video you want to track.", self), color='green'), 3, 0, Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(apply_style(QLabel("Access the folder where configuration files are saved with the button above.", self), color='green'), 5, 0, Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(QLabel("", self), 6, 0, Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(apply_style(QLabel("2 - Run the Tracking:", self), color='blue', font_size='16px'), 1, 1, Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(apply_style(QLabel("Once you have a configuration file, use it to track a video.", self), color='green'), 3, 1, Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(apply_style(QLabel("Or run the tracking on all videos inside a folder.", self), color='green'), 5, 1, Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(apply_style(QLabel("3 - Verify tracking results:", self), color='blue', font_size='16px'), 7, 0, Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(apply_style(QLabel("Visualize/Verify/Explore the tracking results with the button above.", self), color='green'), 9, 0, Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(apply_style(QLabel("Tips on how to correct/enhance ZebraZoom's output when necessary.", self), color='green'), 11, 0, Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(apply_style(QLabel("4 - Analyze behavior:", self), color='blue', font_size='16px'), 7, 1, Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(apply_style(QLabel("Compare populations based on either kinematic parameters or clustering of bouts.", self), color='green'), 9, 1, Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(apply_style(QLabel("Access the folder where the tracking results are saved with the button above.", self), color='green'), 11, 1, Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(QLabel("", self), 12, 0, 1, 2, Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(apply_style(QLabel("Regularly update your version of ZebraZoom with: 'pip install zebrazoom --upgrade'!", self), background_color=GOLD), 15, 0, 1, 2, Qt.AlignmentFlag.AlignCenter)

        open_config_folder_btn = apply_style(QPushButton("Open configuration file folder", self), background_color=LIGHT_YELLOW)
        open_config_folder_btn.clicked.connect(lambda: controller.openConfigurationFileFolder(controller.homeDirectory))
        layout.addWidget(open_config_folder_btn, 4, 0, Qt.AlignmentFlag.AlignCenter)
        run_tracking_on_video_btn = apply_style(QPushButton("Run ZebraZoom's Tracking on a video", self), background_color=LIGHT_YELLOW)
        run_tracking_on_video_btn.clicked.connect(lambda: controller.show_frame("VideoToAnalyze"))
        layout.addWidget(run_tracking_on_video_btn, 2, 1, Qt.AlignmentFlag.AlignCenter)
        run_tracking_on_videos_btn = apply_style(QPushButton("Run ZebraZoom's Tracking on several videos", self), background_color=LIGHT_YELLOW)
        run_tracking_on_videos_btn.clicked.connect(lambda: controller.show_frame("SeveralVideos"))
        layout.addWidget(run_tracking_on_videos_btn, 4, 1, Qt.AlignmentFlag.AlignCenter)
        visualize_output_btn = apply_style(QPushButton("Visualize ZebraZoom's output", self), background_color=LIGHT_YELLOW)
        visualize_output_btn.clicked.connect(lambda: controller.showResultsVisualization())
        layout.addWidget(visualize_output_btn, 8, 0, Qt.AlignmentFlag.AlignCenter)
        enhance_output_btn = apply_style(QPushButton("Enhance ZebraZoom's output", self), background_color=LIGHT_YELLOW)
        enhance_output_btn.clicked.connect(lambda: controller.show_frame("EnhanceZZOutput"))
        layout.addWidget(enhance_output_btn, 10, 0, Qt.AlignmentFlag.AlignCenter)
        analyze_output_btn = apply_style(QPushButton("Analyze ZebraZoom's outputs", self), background_color=LIGHT_YELLOW)
        analyze_output_btn.clicked.connect(lambda: controller.show_frame("CreateExperimentOrganizationExcel"))
        layout.addWidget(analyze_output_btn, 8, 1, Qt.AlignmentFlag.AlignCenter)
        open_output_folder_btn = apply_style(QPushButton("Open ZebraZoom's output folder: Access raw data", self), background_color=LIGHT_YELLOW)
        open_output_folder_btn.clicked.connect(lambda: controller.openZZOutputFolder(controller.homeDirectory))
        layout.addWidget(open_output_folder_btn, 10, 1, Qt.AlignmentFlag.AlignCenter)
        toubleshoot_btn = apply_style(QPushButton("Troubleshoot", self), background_color=LIGHT_CYAN)
        toubleshoot_btn.clicked.connect(lambda: controller.show_frame("ChooseVideoToTroubleshootSplitVideo"))
        layout.addWidget(toubleshoot_btn, 13, 0, 1, 2, Qt.AlignmentFlag.AlignCenter)
        video_documentation_btn = apply_style(QPushButton("Video online documentation", self), background_color=LIGHT_CYAN)
        video_documentation_btn.clicked.connect(lambda: webbrowser.open_new("https://github.com/oliviermirat/ZebraZoom#tableofcontent"))
        layout.addWidget(video_documentation_btn, 14, 0, 1, 2, Qt.AlignmentFlag.AlignCenter)

        hbox = QHBoxLayout()
        prepare_initial_config_btn = apply_style(QPushButton("Prepare initial configuration file for tracking", self), background_color=LIGHT_YELLOW)
        prepare_initial_config_btn.clicked.connect(lambda: controller.show_frame("ChooseVideoToCreateConfigFileFor"))
        hbox.addWidget(prepare_initial_config_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        optimize_config_file_btn = apply_style(QPushButton("Optimize a previously created configuration file", self), background_color=LIGHT_YELLOW)
        optimize_config_file_btn.clicked.connect(lambda: controller.show_frame("OptimizeConfigFile"))
        hbox.addWidget(optimize_config_file_btn, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addLayout(hbox, 2, 0, Qt.AlignmentFlag.AlignCenter)
        # Set the layout on the application's window
        self.setLayout(layout)


class VideoToAnalyze(QWidget):
    def __init__(self, controller):
        super().__init__(controller.window)
        self.controller = controller

        layout = QVBoxLayout()
        layout.addWidget(apply_style(QLabel("Choose video.", self), font=controller.title_font), alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(QLabel("Look for the video you want to analyze.", self), alignment=Qt.AlignmentFlag.AlignCenter)
        button = apply_style(QPushButton("Choose file", self), background_color=LIGHT_YELLOW)
        button.clicked.connect(lambda: controller.chooseVideoToAnalyze(just_extract_checkbox.isChecked(), no_validation_checkbox.isChecked(), debug_checkbox.isChecked()))
        layout.addWidget(button, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(QLabel("", self), alignment=Qt.AlignmentFlag.AlignCenter)

        debug_sublayout = QVBoxLayout()
        debug_checkbox = apply_style(QCheckBox("Run in debug mode.", self), background_color='red')
        debug_sublayout.addWidget(debug_checkbox, alignment=Qt.AlignmentFlag.AlignCenter)
        debug_sublayout.addWidget(QLabel("", self), alignment=Qt.AlignmentFlag.AlignCenter)
        debug_sublayout.addWidget(apply_style(QLabel("This option can be useful to test a new configuration file.", self), background_color='red'), alignment=Qt.AlignmentFlag.AlignCenter)
        debug_sublayout.addWidget(apply_style(QLabel("In this mode you will need to click on any key on each visualization windows.", self), background_color='red'), alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addLayout(debug_sublayout)
        layout.addWidget(QLabel("", self), alignment=Qt.AlignmentFlag.AlignCenter)

        text_sublayout = QVBoxLayout()
        text_sublayout.addWidget(QLabel("Alternatively, to test a new configuration file, you can temporarily manually add the parameter:", self), alignment=Qt.AlignmentFlag.AlignCenter)
        text_sublayout.addWidget(QLabel("'lastFrame': someSmallValue(for example 100)", self), alignment=Qt.AlignmentFlag.AlignCenter)
        text_sublayout.addWidget(QLabel("as well as the parameter:", self), alignment=Qt.AlignmentFlag.AlignCenter)
        text_sublayout.addWidget(QLabel("'backgroundExtractionForceUseAllVideoFrames': 1", self), alignment=Qt.AlignmentFlag.AlignCenter)
        text_sublayout.addWidget(QLabel("inside your configuration file to run the tracking on a small portion of the video in order to test the tracking.", self), alignment=Qt.AlignmentFlag.AlignCenter)
        text_sublayout.addWidget(QLabel("(if necessary, you can also add the parameter 'firstFrame' in your configuration file)", self), alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addLayout(text_sublayout)
        layout.addWidget(QLabel("", self), alignment=Qt.AlignmentFlag.AlignCenter)

        button = apply_style(QPushButton("Click here if you prefer to run the tracking from the command line", self), background_color='green')
        button.clicked.connect(lambda: webbrowser.open_new("https://github.com/oliviermirat/ZebraZoom#commandlinezebrazoom"))
        layout.addWidget(button, alignment=Qt.AlignmentFlag.AlignCenter)

        just_extract_checkbox = apply_style(QCheckBox("I ran the tracking already, I only want to redo the extraction of parameters.", self), color='purple')
        layout.addWidget(just_extract_checkbox, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(QLabel("", self), alignment=Qt.AlignmentFlag.AlignCenter)
        no_validation_checkbox = apply_style(QCheckBox("Don't (re)generate a validation video (for speed efficiency).", self), color='purple')
        layout.addWidget(no_validation_checkbox, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(QLabel("", self), alignment=Qt.AlignmentFlag.AlignCenter)

        start_page_btn = apply_style(QPushButton("Go to the start page", self), background_color=LIGHT_CYAN)
        start_page_btn.clicked.connect(lambda: controller.show_frame("StartPage"))
        layout.addWidget(start_page_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        self.setLayout(layout)


class ConfigFilePromp(QWidget):
    def __init__(self, controller):
        super().__init__(controller.window)
        self.controller = controller

        layout = QVBoxLayout()
        layout.addWidget(apply_style(QLabel("Choose configuration file.", self), font=controller.title_font), alignment=Qt.AlignmentFlag.AlignCenter)
        button = apply_style(QPushButton("Choose file", self), background_color=LIGHT_YELLOW)
        button.clicked.connect(lambda: controller.chooseConfigFile())
        layout.addWidget(button, alignment=Qt.AlignmentFlag.AlignCenter)
        start_page_btn = apply_style(QPushButton("Go to the start page", self), background_color=LIGHT_CYAN)
        start_page_btn.clicked.connect(lambda: controller.show_frame("StartPage"))
        layout.addWidget(start_page_btn, alignment=Qt.AlignmentFlag.AlignCenter)

        self.setLayout(layout)


class Patience(QWidget):
    def __init__(self, controller):
        super().__init__(controller.window)
        self.controller = controller

        layout = QVBoxLayout()
        button = apply_style(QPushButton("Launch ZebraZoom on your video(s)", self), background_color=LIGHT_YELLOW)
        button.clicked.connect(lambda: controller.launchZebraZoom())
        layout.addWidget(button, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(QLabel("After clicking on the button above, please wait for ZebraZoom to run, you can look at the console outside of the GUI to check on the progress of ZebraZoom.", self), alignment=Qt.AlignmentFlag.AlignCenter)

        self.setLayout(layout)


class ZZoutro(QWidget):
    def __init__(self, controller):
        super().__init__(controller.window)
        self.controller = controller

        layout = QVBoxLayout()
        layout.addWidget(QLabel("Finished.", self), alignment=Qt.AlignmentFlag.AlignCenter)
        button = apply_style(QPushButton("Go to the start page", self), background_color=LIGHT_YELLOW)
        button.clicked.connect(lambda: controller.show_frame("StartPage"))
        layout.addWidget(button, alignment=Qt.AlignmentFlag.AlignCenter)

        self.setLayout(layout)
