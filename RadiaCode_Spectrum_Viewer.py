import typing
from configparser import ConfigParser
import os.path
import sys
import xml.etree.ElementTree as ET
from datetime import datetime
from typing import TextIO
import numpy as np
import pyqtgraph as pg
from PySide6.QtCore import Qt, QStandardPaths
from PySide6.QtGui import QGuiApplication, QIcon
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                               QLabel, QPushButton, QCheckBox, QMessageBox, QSlider, QFrame, QFileDialog)
from scipy.signal import find_peaks

# TODO: Plot legend for plot only screenshots
# TODO: Warn if 103G -> wrong compensation
# TODO: Peak detection on background
# TODO: Unload file / clear plot button
# TODO: Error logging into file


APP_NAME = "RadiaCode Spectrum Viewer"
VERSION = "0.99.3.1"
LAST_CHANGED = datetime.date(datetime.now())

config = ConfigParser()

config.read("config.ini")

# Needed, as Pycharm complains about config.write(f) otherwise
if typing.TYPE_CHECKING:
    from _typeshed import SupportsWrite


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.best_mother_nuclide = None
        self.best_isotopes = None
        self.isotopes_data = None
        self.intern_bg_energies = None
        self.intern_bg_dps = None
        self.intern_bg_coeffs = None
        self.contains_bg_data = None
        self.show_original_result_plot = False
        self.show_compensated_result_plot = False
        self.black_white_plot = None
        self.result_dps = None
        self.original_normalized_bg_dp = None
        self.original_normalized_dp = None

        self.plot_bg_dps = []
        self.show_original_plot = config.getboolean("Settings", "show_original_plot")
        self.show_compensated_plot = config.getboolean("Settings", "show_compensated_plot")
        self.show_original_bg_plot = False
        self.show_compensated_bg_plot = False
        self.bg_loaded = False
        self.bg_energies = []
        self.bg_coeffs = []
        self.bg_dps = []
        self.parsed_bg_data = {}
        self.plot_bg_data = {}
        self.parsed_data = {}
        self.log_x = False
        self.log_y = False
        self.peak_energy = []
        self.peak_dp_source = []
        self.plot_title = ""
        self.last_open_directory = ""
        self.last_save_directory = ""
        self.original_data_points = []
        self.original_serial_number = ""
        self.coeffs = []
        self.screenshot_name = ""
        self.file_loaded = False
        self.data_points = []
        self.original_plot = None
        self.compensated_plot = None
        self.theme = ""
        self.time_seconds = 0
        self.parsed_xml = None
        self.plot_data_points = []
        self.energies = []

        self.setWindowTitle("RadiaCode Spectrum Viewer " + VERSION)
        self.setWindowIcon(QIcon("rsv_logo.png"))
        app_x_size = 1300
        app_y_size = 800
        self.resize(app_x_size, app_y_size)
        screen = QGuiApplication.primaryScreen().availableGeometry()
        screen_center = screen.center()
        x = screen_center.x() - app_x_size // 2
        y = screen_center.y() - app_y_size // 2
        self.move(x, y)

        self.main_widget = QWidget()
        self.setCentralWidget(self.main_widget)
        self.layout = QHBoxLayout(self.main_widget)

        self.left_row = QVBoxLayout()
        self.layout.addLayout(self.left_row)

        self.counts_value_label = QLabel("")
        self.counts_value_label.setObjectName("counts_value_label")
        self.counts_value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.left_row.addWidget(self.counts_value_label)

        self.counts_label = QLabel("Total Counts")
        self.counts_label.setObjectName("counts_label")
        self.counts_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.left_row.addWidget(self.counts_label)

        self.line = QFrame()
        self.line.setFrameShape(QFrame.Shape.HLine)
        self.line.setFixedWidth(150)
        self.left_row.addWidget(self.line)

        self.cps_value_label = QLabel("")
        self.cps_value_label.setObjectName("cps_value_label")
        self.cps_value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.left_row.addWidget(self.cps_value_label)

        self.cps_label = QLabel("CPS Average")
        self.cps_label.setObjectName("cps_label")
        self.cps_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.left_row.addWidget(self.cps_label)

        self.line = QFrame()
        self.line.setFrameShape(QFrame.Shape.HLine)
        self.line.setFixedWidth(150)
        self.left_row.addWidget(self.line)

        self.duration_value_label = QLabel("")
        self.duration_value_label.setObjectName("duration_value_label")
        self.duration_value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.left_row.addWidget(self.duration_value_label)

        self.duration_label = QLabel("Duration")
        self.duration_label.setObjectName("duration_label")
        self.duration_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.left_row.addWidget(self.duration_label)

        self.line = QFrame()
        self.line.setFrameShape(QFrame.Shape.HLine)
        self.line.setFixedWidth(150)
        self.left_row.addWidget(self.line)

        self.start_value_label = QLabel("")
        self.start_value_label.setObjectName("start_value_label")
        self.start_value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.left_row.addWidget(self.start_value_label)

        self.start_label = QLabel("Start Time UTC")
        self.start_label.setObjectName("start_label")
        self.start_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.left_row.addWidget(self.start_label)

        self.line = QFrame()
        self.line.setFrameShape(QFrame.Shape.HLine)
        self.line.setFixedWidth(150)
        self.left_row.addWidget(self.line)

        self.end_value_label = QLabel("")
        self.end_value_label.setObjectName("end_value_label")
        self.end_value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.left_row.addWidget(self.end_value_label)

        self.end_label = QLabel("End Time UTC")
        self.end_label.setObjectName("end_label")
        self.end_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.left_row.addWidget(self.end_label)

        self.line = QFrame()
        self.line.setFrameShape(QFrame.Shape.HLine)
        self.line.setFixedWidth(150)
        self.left_row.addWidget(self.line)

        self.device_value_label = QLabel("")
        self.device_value_label.setObjectName("device_value_label")
        self.device_value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.left_row.addWidget(self.device_value_label)

        self.device_label = QLabel("Device")
        self.device_label.setObjectName("device_label")
        self.device_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.left_row.addWidget(self.device_label)

        self.line = QFrame()
        self.line.setFrameShape(QFrame.Shape.HLine)
        self.line.setFixedWidth(150)
        self.left_row.addWidget(self.line)

        self.serial_value_label = QLabel("")
        self.serial_value_label.setObjectName("serial_value_label")
        self.serial_value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.left_row.addWidget(self.serial_value_label)

        self.serial_label = QLabel("Serial Number")
        self.serial_label.setObjectName("serial_label")
        self.serial_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.left_row.addWidget(self.serial_label)

        self.line = QFrame()
        self.line.setFrameShape(QFrame.Shape.HLine)
        self.line.setFixedWidth(150)
        self.left_row.addWidget(self.line)

        self.theme_setting_checkbox = QCheckBox("Dark Theme")
        self.theme_setting_checkbox.setObjectName("theme_setting_checkbox")
        self.theme_setting_checkbox.checkStateChanged.connect(self.toggle_theme)
        self.left_row.addWidget(self.theme_setting_checkbox)

        self.line = QFrame()
        self.line.setFrameShape(QFrame.Shape.HLine)
        self.line.setFixedWidth(150)
        self.left_row.addWidget(self.line)

        self.open_button = QPushButton("Open File")
        self.open_button.setObjectName("open_button")
        self.open_button.clicked.connect(self.open_file)
        self.left_row.addWidget(self.open_button)

        self.reset_plot_button = QPushButton("Reset Plot")
        self.reset_plot_button.setObjectName("reset_plot_button")
        self.reset_plot_button.clicked.connect(self.reset_plot)
        self.left_row.addWidget(self.reset_plot_button)

        self.screenshot_app_button = QPushButton("App Screenshot")
        self.screenshot_app_button.setObjectName("screenshot_app_button")
        self.screenshot_app_button.clicked.connect(self.screenshot_app)
        self.left_row.addWidget(self.screenshot_app_button)

        self.screenshot_plot_button = QPushButton("Plot Screenshot")
        self.screenshot_plot_button.setObjectName("screenshot_plot_button")
        self.screenshot_plot_button.setDisabled(True)
        self.screenshot_plot_button.clicked.connect(self.screenshot_plot)
        self.left_row.addWidget(self.screenshot_plot_button)

        self.about_button = QPushButton("About")
        self.about_button.setObjectName("about_button")
        self.about_button.clicked.connect(self.about)
        self.left_row.addWidget(self.about_button)

        self.plot = pg.PlotWidget()
        self.plot_bg_color = ""
        self.plot_title_color = ""
        self.plot_line_color = ""
        self.plot_line_width = config.getint("Settings", "plt_line_width")
        self.plot_background_color = ""
        self.plot_x_label_color = ""
        self.plot_y_label_color = ""
        self.original_plot_color = ""
        self.compensated_plot_color = ""
        self.compensated_bg_plot_color = ""
        self.original_result_plot_color = ""
        self.compensated_result_plot_color = ""
        self.original_bg_plot_color = ""
        self.annotation_color = ""
        self.annotation_bg_color = ""
        self.layout.addWidget(self.plot)
        self.show()

        self.line = QFrame()
        self.line.setFrameShape(QFrame.Shape.HLine)
        self.line.setFixedWidth(150)
        self.left_row.addWidget(self.line)

        self.right_row = QVBoxLayout()
        self.layout.addLayout(self.right_row)

        self.original_plot_checkbox = QCheckBox("Original Plot")
        self.original_plot_checkbox.setChecked(config.getboolean("Settings", "show_original_plot"))
        self.original_plot_checkbox.setObjectName("original_plot_checkbox")
        self.original_plot_checkbox.setDisabled(True)
        self.original_plot_checkbox.clicked.connect(self.toggle_original_plot)
        self.right_row.addWidget(self.original_plot_checkbox)

        self.compensated_plot_checkbox = QCheckBox("Compensated Plot")
        self.compensated_plot_checkbox.setChecked(config.getboolean("Settings", "show_compensated_plot"))
        self.compensated_plot_checkbox.setObjectName("compensated_plot_checkbox")
        self.compensated_plot_checkbox.setDisabled(True)
        self.compensated_plot_checkbox.clicked.connect(self.toggle_compensated_plot)
        self.right_row.addWidget(self.compensated_plot_checkbox)

        self.original_bg_plot_checkbox = QCheckBox("Original BG Plot")
        self.original_bg_plot_checkbox.setObjectName("original_bg_plot_checkbox")
        self.original_bg_plot_checkbox.setChecked(False)
        self.original_bg_plot_checkbox.setDisabled(True)
        self.original_bg_plot_checkbox.clicked.connect(self.toggle_original_bg_plot)
        self.right_row.addWidget(self.original_bg_plot_checkbox)

        self.compensated_bg_plot_checkbox = QCheckBox("Compensated BG Plot")
        self.compensated_bg_plot_checkbox.setObjectName("compensated_bg_plot_checkbox")
        self.compensated_bg_plot_checkbox.setChecked(False)
        self.compensated_bg_plot_checkbox.setDisabled(True)
        self.compensated_bg_plot_checkbox.clicked.connect(self.toggle_compensated_bg_plot)
        self.right_row.addWidget(self.compensated_bg_plot_checkbox)

        self.black_on_white_plot_checkbox = QCheckBox("Black On White Plot")
        self.black_on_white_plot_checkbox.setChecked(config.getboolean("Dynamic", "show_black_on_white_plot"))
        self.black_on_white_plot_checkbox.setObjectName("black_on_white_plot_checkbox")
        self.black_on_white_plot_checkbox.setDisabled(True)
        self.black_on_white_plot_checkbox.checkStateChanged.connect(self.toggle_black_white_plot)
        self.right_row.addWidget(self.black_on_white_plot_checkbox)

        self.line = QFrame()
        self.line.setFrameShape(QFrame.Shape.HLine)
        self.line.setFixedWidth(150)
        self.right_row.addWidget(self.line)

        self.log_x_checkbox = QCheckBox("Logarithmic X-Axis")
        self.log_x_checkbox.setObjectName("log_x_checkbox")
        self.log_x_checkbox.setDisabled(True)
        self.log_x_checkbox.checkStateChanged.connect(self.toggle_log_x)
        self.right_row.addWidget(self.log_x_checkbox)

        self.log_y_checkbox = QCheckBox("Logarithmic Y-Axis")
        self.log_y_checkbox.setObjectName("log_y_checkbox")
        self.log_y_checkbox.setDisabled(True)
        self.log_y_checkbox.checkStateChanged.connect(self.toggle_log_y)
        self.right_row.addWidget(self.log_y_checkbox)

        self.line = QFrame()
        self.line.setFrameShape(QFrame.Shape.HLine)
        self.line.setFixedWidth(150)
        self.right_row.addWidget(self.line)

        self.low_smooth_label = QLabel("Low Energy Smoothing")
        self.low_smooth_label.setObjectName("low_smooth_label")
        self.low_smooth_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.right_row.addWidget(self.low_smooth_label)

        self.low_smooth_slider = QSlider(Qt.Orientation.Horizontal)
        self.low_smooth_slider.setObjectName("low_smooth_slider")
        low_smooth_min = config.getint("Settings", "low_smooth_slider_min")
        low_smooth_max = config.getint("Settings", "low_smooth_slider_max")
        low_smooth_default = config.getint("Settings", "low_smooth_slider_default")
        self.low_smooth_slider.setRange(low_smooth_min, low_smooth_max)
        self.low_smooth_slider.setValue(low_smooth_default)
        self.low_smooth_slider.setMaximumWidth(150)
        self.low_smooth_slider.valueChanged.connect(self.low_smooth_slider_changed)
        self.right_row.addWidget(self.low_smooth_slider)

        self.high_smooth_label = QLabel("High Energy Smoothing")
        self.high_smooth_label.setObjectName("high_smooth_label")
        self.high_smooth_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.right_row.addWidget(self.high_smooth_label)

        self.high_smooth_slider = QSlider(Qt.Orientation.Horizontal)
        self.high_smooth_slider.setObjectName("max_smoothing_slider")
        high_smooth_min = config.getint("Settings", "high_smooth_slider_min")
        high_smooth_max = config.getint("Settings", "high_smooth_slider_max")
        high_smooth_default = config.getint("Settings", "high_smooth_slider_default")
        self.high_smooth_slider.setRange(high_smooth_min, high_smooth_max)
        self.high_smooth_slider.setValue(high_smooth_default)
        self.high_smooth_slider.setMaximumWidth(150)
        self.high_smooth_slider.valueChanged.connect(self.high_smooth_slider_changed)
        self.right_row.addWidget(self.high_smooth_slider)

        self.line = QFrame()
        self.line.setFrameShape(QFrame.Shape.HLine)
        self.line.setFixedWidth(150)
        self.right_row.addWidget(self.line)

        self.peak_detection_checkbox = QCheckBox("Peak Detection")
        self.peak_detection_checkbox.setObjectName("peak_detection_checkbox")
        self.peak_detection_checkbox.checkStateChanged.connect(self.toggle_peak_detection)
        self.peak_detection_checkbox.setDisabled(True)
        self.right_row.addWidget(self.peak_detection_checkbox)

        self.activate_peak_detection = config.getboolean("Dynamic", "activate_peak_detection")
        if self.activate_peak_detection:
            self.peak_detection_checkbox.setChecked(True)
        else:
            self.peak_detection_checkbox.setChecked(False)

        self.min_height_label = QLabel("Minimal Peak Height")
        self.min_height_label.setObjectName("peak_height_label")
        self.min_height_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.right_row.addWidget(self.min_height_label)

        self.min_height_slider = QSlider(Qt.Orientation.Horizontal)
        self.min_height_slider.setObjectName("peak_height_slider")
        self.min_height_slider.setRange(0, 100)
        self.min_height_slider.setValue(config.getint("Settings", "height_slider_default"))
        self.min_height_slider.setMaximumWidth(150)
        self.min_height_slider.valueChanged.connect(self.peak_height_slider_changed)
        self.right_row.addWidget(self.min_height_slider)

        self.prominence_label = QLabel("Minimal Peak Prominence")
        self.prominence_label.setObjectName("peak_prominence_label")
        self.prominence_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.right_row.addWidget(self.prominence_label)

        self.prominence_slider = QSlider(Qt.Orientation.Horizontal)
        self.prominence_slider.setObjectName("peak_prominence_slider")
        prominence_min = config.getint("Settings", "prominence_slider_min")
        prominence_max = config.getint("Settings", "prominence_slider_max")
        prominence_default = config.getint("Settings", "prominence_slider_default")
        self.prominence_slider.setRange(prominence_min, prominence_max)
        self.prominence_slider.setValue(prominence_default)
        self.prominence_slider.setMaximumWidth(150)
        self.prominence_slider.valueChanged.connect(self.peak_prominence_slider_changed)
        self.right_row.addWidget(self.prominence_slider)

        self.distance_label = QLabel("Minimal Peak Distance")
        self.distance_label.setObjectName("distance_label")
        self.distance_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.right_row.addWidget(self.distance_label)

        self.distance_slider = QSlider(Qt.Orientation.Horizontal)
        self.distance_slider.setObjectName("distance_slider")
        min_distance = config.getint("Settings", "distance_slider_min")
        max_distance = config.getint("Settings", "distance_slider_max")
        default_distance = config.getint("Settings", "distance_slider_default")
        self.distance_slider.setRange(min_distance, max_distance)
        self.distance_slider.setValue(default_distance)
        self.distance_slider.setMaximumWidth(150)
        self.distance_slider.valueChanged.connect(self.peak_distance_slider_changed)
        self.right_row.addWidget(self.distance_slider)

        self.line = QFrame()
        self.line.setFrameShape(QFrame.Shape.HLine)
        self.line.setFixedWidth(150)
        self.right_row.addWidget(self.line)

        self.show_included_bg_button = QPushButton("Show included BG")
        self.show_included_bg_button.setObjectName("show_included_bg")
        self.show_included_bg_button.setDisabled(False)
        self.show_included_bg_button.clicked.connect(self.show_included_bg)
        self.show_included_bg_button.setVisible(False)
        self.right_row.addWidget(self.show_included_bg_button)

        self.load_bg_button = QPushButton("Load Background")
        self.load_bg_button.setObjectName("load_background_button")
        self.load_bg_button.setDisabled(True)
        self.load_bg_button.clicked.connect(self.open_bg_file)
        self.right_row.addWidget(self.load_bg_button)

        self.subtract_bg_button = QPushButton("Subtract Background")
        self.subtract_bg_button.setObjectName("subtract_bg_button")
        self.subtract_bg_button.clicked.connect(self.subtract_bg)
        self.subtract_bg_button.setDisabled(True)
        self.right_row.addWidget(self.subtract_bg_button)

        self.line = QFrame()
        self.line.setFrameShape(QFrame.Shape.HLine)
        self.line.setFixedWidth(150)
        self.right_row.addWidget(self.line)

        self.right_row.setAlignment(Qt.AlignmentFlag.AlignTop)

        check_theme = config.get("Dynamic", "theme")
        if check_theme == "light":
            self.theme_setting_checkbox.setChecked(False)
        elif check_theme == "dark":
            self.theme_setting_checkbox.setChecked(True)

    def show_included_bg(self):
        self.bg_loaded = False
        self.bg_coeffs = self.intern_bg_coeffs.copy()
        self.bg_dps = self.intern_bg_dps.copy()
        self.plot_bg_dps = self.bg_dps.copy()
        self.bg_energies = self.get_energies(self.bg_coeffs, self.bg_dps)

        self.show_original_bg_plot = True
        self.show_compensated_bg_plot = True
        self.subtract_bg_button.setDisabled(False)

        self.bg_loaded = True
        self.original_bg_plot_checkbox.setDisabled(False)
        self.compensated_bg_plot_checkbox.setDisabled(False)
        self.original_bg_plot_checkbox.setChecked(True)
        self.compensated_bg_plot_checkbox.setChecked(True)

        self.plot_data()

    def subtract_bg(self):

        self.show_original_plot = False
        self.show_compensated_plot = False
        self.show_original_bg_plot = False
        self.show_compensated_bg_plot = False
        self.original_plot_checkbox.setChecked(False)
        self.compensated_plot_checkbox.setChecked(False)
        self.original_bg_plot_checkbox.setChecked(False)
        self.compensated_bg_plot_checkbox.setChecked(False)

        self.result_dps = []
        result_dp_list = []
        orig_dps = self.original_normalized_dp
        dps_to_subtract = self.original_normalized_bg_dp

        if orig_dps is None or dps_to_subtract is None:
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Icon.Critical)
            msg_box.setWindowTitle("Error")
            msg_box.setText("Something went wrong, please restart the app.\n"
                            "Original Data and/or Subtract data can't be found.")
            msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
            msg_box.exec()
            return

        if len(orig_dps) != len(dps_to_subtract):
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Icon.Critical)
            msg_box.setWindowTitle("Error")
            msg_box.setText("Foreground and background spectra\n"
                            "don't have the same number of datapoints.")
            msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
            msg_box.exec()
            return
        else:
            for i in range(len(orig_dps)):
                dps = orig_dps[i] - dps_to_subtract[i]
                result_dp_list.append(dps)

            # Make negative values 0
            result_dp_list = [i if i > 0 else 0 for i in result_dp_list]

            # Get the biggest number in the list
            maximum_value = max(result_dp_list)

            # Normalize the list so that the maximum value is 1
            try:
                self.result_dps = [x / maximum_value for x in result_dp_list]
            except ZeroDivisionError:
                msg_box = QMessageBox()
                msg_box.setIcon(QMessageBox.Icon.Critical)
                msg_box.setWindowTitle("Error")
                msg_box.setText("Division by zero error!\n"
                                " Probably identical fore- and background?")
                msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
                msg_box.exec()
                return

            self.show_original_result_plot = True
            self.show_compensated_result_plot = True

            self.load_bg_button.setDisabled(True)
            self.open_button.setDisabled(True)

            self.subtract_bg_button.setText("Back")
            self.subtract_bg_button.clicked.disconnect()
            self.subtract_bg_button.clicked.connect(self.previous_plots)

            self.plot_data()

    def previous_plots(self):
        self.show_original_plot = True
        self.show_compensated_plot = True
        self.show_original_bg_plot = True
        self.show_compensated_bg_plot = True
        self.show_original_result_plot = False
        self.show_compensated_result_plot = False

        self.original_plot_checkbox.setChecked(True)
        self.compensated_plot_checkbox.setChecked(True)
        self.original_bg_plot_checkbox.setChecked(True)
        self.compensated_bg_plot_checkbox.setChecked(True)

        self.load_bg_button.setDisabled(False)
        self.open_button.setDisabled(False)

        self.subtract_bg_button.setText("Subtract Background")
        self.subtract_bg_button.clicked.disconnect()
        self.subtract_bg_button.clicked.connect(self.subtract_bg)

        self.plot_data()

    def open_bg_file(self):
        self.bg_loaded = False
        bg_xml_file = None

        last_bg_directory = config.get("Paths", "last_bg_directory")
        if last_bg_directory is None:
            last_bg_directory = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DesktopLocation)
        else:
            last_bg_directory = str(last_bg_directory)

        file_dialog = QFileDialog()
        file_dialog.setFileMode(QFileDialog.FileMode.ExistingFile)
        file_dialog.setNameFilter("XML Files (*.xml)")
        file_dialog.setViewMode(QFileDialog.ViewMode.Detail)
        file_dialog.setDirectory(last_bg_directory)

        if file_dialog.exec():
            bg_xml_file = file_dialog.selectedFiles()[0]
            last_bg_directory = file_dialog.directory().path()
            config.set('Paths', 'last_bg_directory', str(last_bg_directory))
            with open("config.ini", "w", encoding="utf8") as f:  # type: SupportsWrite
                config.write(f)

        if bg_xml_file is None:
            msgbox = QMessageBox()
            msgbox.setIcon(QMessageBox.Icon.Warning)
            msgbox.setText("Background file not loaded correctly")
            msgbox.setWindowTitle("Warning")
            msgbox.exec()
            return
        else:
            self.bg_loaded = True
            self.original_bg_plot_checkbox.setDisabled(False)
            self.compensated_bg_plot_checkbox.setDisabled(False)
            self.original_bg_plot_checkbox.setChecked(True)
            self.compensated_bg_plot_checkbox.setChecked(True)
        self.parse_bg(bg_xml_file)

    def parse_bg(self, bg_xml_file):
        root = None
        result_data = None
        if bg_xml_file is not None:
            tree = ET.parse(bg_xml_file)
            root = tree.getroot()
        try:
            result_data = root.find("ResultDataList/ResultData")
        except (Exception,):
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Icon.Critical)
            msg_box.setWindowTitle("Error")
            msg_box.setText("The selected file is not a valid XML file.")
            msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
            msg_box.exec()
        try:
            serial_number = result_data.find("EnergySpectrum/SerialNumber").text
        except (Exception,):
            serial_number = None

        if serial_number is not None and serial_number.startswith("RC"):
            try:
                if serial_number[6] == "G":
                    device = "RC-103G"
                else:
                    device = serial_number[:6]
            except (Exception,):
                device = "Unknown"
        else:
            device = "Unknown"

        coeffs = [float(C.text) for C in result_data.find("EnergySpectrum/EnergyCalibration/Coefficients")]
        if len(coeffs) < 3:
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Icon.Critical)
            msg_box.setWindowTitle("Error")
            msg_box.setText("The selected file has less than 3 coefficients.")
            msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
            msg_box.exec()
            return
        if len(coeffs) > 3:
            coeffs = coeffs[:3]
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Icon.Information)
            msg_box.setWindowTitle("Information")
            msg_box.setText("XML has more than 3 coefficients.\n"
                            "Only the first 3 will be used.")
            msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
            msg_box.exec()

        if device == "RC-103G":
            if coeffs[0] < 0:
                msg_box = QMessageBox()
                msg_box.setIcon(QMessageBox.Icon.Warning)
                msg_box.setWindowTitle("Warning")
                msg_box.setText("The selected file has a negative coefficient a0.\n"
                                "This is no value a proper calibrated RC-103G would have.\n"
                                "Data is still displayed, but the results might be incorrect.")
                msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
                msg_box.exec()
        else:
            if coeffs[0] < -20:
                msg_box = QMessageBox()
                msg_box.setIcon(QMessageBox.Icon.Warning)
                msg_box.setWindowTitle("Warning")
                msg_box.setText("The selected file has coefficient a0  < -20\n"
                                "This is no value a proper calibrated device would have.\n"
                                "Data is still displayed, but the results might be incorrect.")
                msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
                msg_box.exec()

        if coeffs[0] > 30:
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Icon.Warning)
            msg_box.setWindowTitle("Warning")
            msg_box.setText("The selected file has coefficient a0 > 30\n"
                            "This is no value a proper calibrated device would have.\n"
                            "Data is still displayed, but the results might be incorrect.")
            msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
            msg_box.exec()

        data_points = [int(DP.text) for DP in result_data.find("EnergySpectrum/Spectrum")]

        if not config.getboolean("Settings", "include_channel_1023"):
            data_points = data_points[:-1]

        # self.parsed_bg_data = {
        #     "serial_number": serial_number,
        #     "coeffs": coeffs,
        #     "data_points": data_points,
        # }

        for coeff in self.coeffs:
            if coeff == 0:
                msg_box = QMessageBox()
                msg_box.setIcon(QMessageBox.Icon.Critical)
                msg_box.setWindowTitle("Error")
                msg_box.setText("The selected file has one or more coefficients with a value of 0.\n"
                                "Please check the coefficients in the file.")
                msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
                msg_box.exec()
                return

        self.bg_coeffs = coeffs.copy()
        self.bg_dps = data_points
        self.plot_bg_dps = self.bg_dps.copy()
        self.bg_energies = self.get_energies(self.bg_coeffs, self.bg_dps)

        self.show_original_bg_plot = True
        self.show_compensated_bg_plot = True

        self.subtract_bg_button.setDisabled(False)

        self.plot_data()

    def open_file(self):
        self.subtract_bg_button.setDisabled(True)
        self.file_loaded = False
        xml_file = None

        last_open_directory = config.get("Paths", "last_open_directory")
        if last_open_directory is None:
            last_open_directory = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DesktopLocation)
        else:
            last_open_directory = str(last_open_directory)

        file_dialog = QFileDialog()
        file_dialog.setFileMode(QFileDialog.FileMode.ExistingFile)
        file_dialog.setNameFilter("XML Files (*.xml)")
        file_dialog.setViewMode(QFileDialog.ViewMode.Detail)
        file_dialog.setDirectory(last_open_directory)

        if file_dialog.exec():
            xml_file = file_dialog.selectedFiles()[0]
            last_open_directory = file_dialog.directory().path()
            config.set('Paths', 'last_open_directory', str(last_open_directory))
            with open("config.ini", "w", encoding="utf8") as f:  # type: SupportsWrite
                config.write(f)

        if xml_file is None:
            msgbox = QMessageBox()
            msgbox.setIcon(QMessageBox.Icon.Warning)
            msgbox.setText("File not loaded correctly")
            msgbox.setWindowTitle("Warning")
            msgbox.exec()
            return
        else:
            self.file_loaded = True
            self.peak_detection_checkbox.setDisabled(False)

        self.parse_xml(xml_file)

    def parse_xml(self, xml_file):
        root = None
        result_data = None
        if xml_file is not None:
            tree = ET.parse(xml_file)
            root = tree.getroot()
        try:
            result_data = root.find("ResultDataList/ResultData")
        except (Exception,):
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Icon.Critical)
            msg_box.setWindowTitle("Error")
            msg_box.setText("The selected file is not a valid XML file.")
            msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
            msg_box.exec()

        self.show_included_bg_button.setVisible(False)

        background_data = root.find("ResultDataList/ResultData/BackgroundEnergySpectrum")
        if background_data is not None:
            self.contains_bg_data = True

            bg_coeffs = [float(i.text) for i in background_data.find("EnergyCalibration/Coefficients")]

            if len(bg_coeffs) < 3:
                msg_box = QMessageBox()
                msg_box.setIcon(QMessageBox.Icon.Critical)
                msg_box.setWindowTitle("Error")
                msg_box.setText("The internal background has less than 3 coefficients.")
                msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
                msg_box.exec()
                return
            if len(bg_coeffs) > 3:
                bg_coeffs = bg_coeffs[:3]
                msg_box = QMessageBox()
                msg_box.setIcon(QMessageBox.Icon.Information)
                msg_box.setWindowTitle("Information")
                msg_box.setText("The background has more than 3 coefficients.\n"
                                "Only the first 3 will be used.")
                msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
                msg_box.exec()

            if config.getboolean("Settings", "include_channel_1023"):
                bg_dps = [int(DP.text) for DP in background_data.find("Spectrum")]
            else:
                bg_dps = [int(DP.text) for DP in background_data.find("Spectrum")[:-1]]

            self.intern_bg_coeffs = bg_coeffs.copy()
            self.intern_bg_dps = bg_dps.copy()
            self.show_included_bg_button.setVisible(True)

            self.intern_bg_energies = self.get_energies(self.intern_bg_coeffs, self.intern_bg_dps)
        else:
            self.contains_bg_data = False

        try:
            serial_number = result_data.find("EnergySpectrum/SerialNumber").text
        except (Exception,):
            serial_number = None

        file_name = os.path.basename(xml_file)
        sample_name = os.path.splitext(file_name)[0]

        if serial_number is not None and serial_number.startswith("RC"):
            try:
                if serial_number[6] == "G":
                    device = "RC-103G"
                else:
                    device = serial_number[:6]
            except (Exception,):
                device = "Unknown"
        else:
            device = "Unknown"

        coeffs = [float(C.text) for C in result_data.find("EnergySpectrum/EnergyCalibration/Coefficients")]
        if len(coeffs) < 3:
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Icon.Critical)
            msg_box.setWindowTitle("Error")
            msg_box.setText("The selected file has less than 3 coefficients.")
            msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
            msg_box.exec()
            return
        if len(coeffs) > 3:
            coeffs = coeffs[:3]
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Icon.Information)
            msg_box.setWindowTitle("Information")
            msg_box.setText("XML has more than 3 coefficients.\n"
                            "Only the first 3 will be used.")
            msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
            msg_box.exec()

        if device == "RC-103G":
            if coeffs[0] < 0:
                msg_box = QMessageBox()
                msg_box.setIcon(QMessageBox.Icon.Warning)
                msg_box.setWindowTitle("Warning")
                msg_box.setText("The selected file has a negative coefficient a0.\n"
                                "This is no value a proper calibrated RC-103G would have.\n"
                                "Data is still displayed, but the results might be incorrect.")
                msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
                msg_box.exec()
        else:
            if coeffs[0] < -20:
                msg_box = QMessageBox()
                msg_box.setIcon(QMessageBox.Icon.Warning)
                msg_box.setWindowTitle("Warning")
                msg_box.setText("The selected file has coefficient a0  < -20\n"
                                "This is no value a proper calibrated device would have.\n"
                                "Data is still displayed, but the results might be incorrect.")
                msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
                msg_box.exec()

        if coeffs[0] > 30:
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Icon.Warning)
            msg_box.setWindowTitle("Warning")
            msg_box.setText("The selected file has coefficient a0 > 30\n"
                            "This is no value a proper calibrated device would have.\n"
                            "Data is still displayed, but the results might be incorrect.")
            msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
            msg_box.exec()

        data_points = [int(DP.text) for DP in result_data.find("EnergySpectrum/Spectrum")]
        start_time = result_data.find('StartTime').text[:19]
        end_time = result_data.find('EndTime').text[:19]
        start_dt = datetime.strptime(start_time, '%Y-%m-%dT%H:%M:%S')
        end_dt = datetime.strptime(end_time, '%Y-%m-%dT%H:%M:%S')
        duration = end_dt - start_dt
        duration_txt = str(duration)
        time_seconds = duration.total_seconds()
        start_time_formatted = start_time.replace("T", " ")
        end_time_formatted = end_time.replace("T", " ")

        if not config.getboolean("Settings", "include_channel_1023"):
            data_points = data_points[:-1]

        self.parsed_data = {
            "sample_name": sample_name,
            "serial_number": serial_number,
            "device": device,
            "coeffs": coeffs,
            "data_points": data_points,
            "seconds": time_seconds,
            "duration": duration_txt,
            "start_time": start_time_formatted,
            "end_time": end_time_formatted
        }

        self.fill_data(self.parsed_data)

    def fill_data(self, parsed_xml):

        self.original_plot_checkbox.setDisabled(False)
        self.compensated_plot_checkbox.setDisabled(False)
        self.black_on_white_plot_checkbox.setDisabled(False)
        self.screenshot_plot_button.setDisabled(False)

        self.load_bg_button.setDisabled(False)

        self.log_y_checkbox.setDisabled(False)
        self.log_x_checkbox.setDisabled(False)

        self.data_points = parsed_xml["data_points"]
        self.coeffs = parsed_xml["coeffs"]
        self.time_seconds = parsed_xml["seconds"]
        self.plot_title = parsed_xml["sample_name"]
        self.device_value_label.setText(parsed_xml["device"])
        self.serial_value_label.setText(parsed_xml["serial_number"])
        self.start_value_label.setText(parsed_xml["start_time"])
        self.end_value_label.setText(parsed_xml["end_time"])
        self.duration_value_label.setText(parsed_xml["duration"])
        self.counts_value_label.setText(f"{sum(self.data_points): ,}".replace(',', ' '))
        self.cps_value_label.setText(str(round(sum(self.data_points) / int(self.time_seconds), 2)))

        # Copy the data points and the coefficients for the plot calculations
        self.plot_data_points = self.data_points.copy()
        for coeff in self.coeffs:
            if coeff == 0:
                msg_box = QMessageBox()
                msg_box.setIcon(QMessageBox.Icon.Critical)
                msg_box.setWindowTitle("Error")
                msg_box.setText("The selected file has one or more coefficients with a value of 0.\n"
                                "Please check the coefficients in the file.")
                msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
                msg_box.exec()
                return

        self.coeffs = self.coeffs.copy()
        self.energies = self.get_energies(self.coeffs, self.plot_data_points)

        self.plot_data()

    @staticmethod
    def get_energies(coeffs, data_points):
        energies = []
        for point in range(len(data_points)):
            energy = coeffs[0] + coeffs[1] * point + coeffs[2] * point ** 2
            energies.append(energy)
        return energies

    def get_compensated_dp(self, coeffs, data_points):
        energies = self.get_energies(coeffs, data_points)

        if energies[0] <= 0:
            energy_offset = abs(energies[0]) + 0.1
            energies = [(x + energy_offset) / 1000 for x in self.energies]
        else:
            energies = [x / 1000 for x in self.energies]

        efficiency = [
            np.exp(
                -4.09527
                - 2.34638 * np.log(E)
                + 0.228436 * np.log(E) ** 2
                + 0.31551 * np.log(E) ** 3
                + 0.0383176 * np.log(E) ** 4
            )
            for E in energies
        ]
        return [data_point / eff for data_point, eff in zip(data_points, efficiency)]

    @staticmethod
    def get_smoothed_data(energies, compensated_dp, low_smooth, high_smooth):
        smoothed_dp = []
        min_energy = min(energies)
        max_energy = max(energies)

        # Energy list has the same length as the data points
        for i in range(len(energies)):
            # Normalize the energy values
            normalized_energy = (energies[i] - min_energy) / (max_energy - min_energy)
            # Interpolate the smoothing value between min_smoothing and max_smoothing
            # Calculate the moving average centered on the current point
            smooth_value = int(low_smooth + (high_smooth - low_smooth) * normalized_energy)
            half_window = smooth_value // 2
            start_index = max(0, i - half_window)
            end_index = min(len(compensated_dp), i + half_window + 1)
            smoothed_dp.append(np.mean(compensated_dp[start_index:end_index]))
        return smoothed_dp

    @staticmethod
    def normalize_data(data):
        min_data = min(data)
        max_data = max(data)
        return [(x - min_data) / (max_data - min_data) for x in data]

    @staticmethod
    def detect_peaks(data, energies, height_slider, prominence_slider, distance_slider):
        height_slider /= 100
        prominence_slider /= 100
        distance_slider = int(distance_slider)
        peaks, _ = find_peaks(data, height=height_slider, prominence=prominence_slider, distance=distance_slider)
        peak_energies = [round(energies[i], 1) for i in np.array(peaks)]
        return peak_energies

    def plot_data(self):
        self.plot.clear()

        if self.black_on_white_plot_checkbox.isChecked():
            self.original_plot_color = "black"
            self.compensated_plot_color = "black"
            self.original_bg_plot_color = "black"
            self.compensated_bg_plot_color = "black"
            self.original_result_plot_color = "black"
            self.compensated_result_plot_color = "black"
            self.annotation_color = "black"
            self.annotation_bg_color = "white"
            self.plot_title_color = "black"
            self.plot_background_color = "white"
            self.plot_x_label_color = "black"
            self.plot_y_label_color = "black"
            self.plot.setBackground(self.plot_background_color)

        else:
            if self.theme == "light":
                self.apply_light_stylesheet()
                config.set("Dynamic", "theme", "light")
                with open("config.ini", "w", encoding="utf8") as f:  # type: SupportsWrite
                    config.write(f)

            elif self.theme == "dark":
                self.apply_dark_stylesheet()
                config.set("Dynamic", "theme", "dark")
                with open("config.ini", "w", encoding="utf8") as f:  # type: SupportsWrite
                    config.write(f)

        max_plot_title_length = config.getint("Settings", "max_plot_title_length")
        self.plot.setTitle(self.plot_title[:max_plot_title_length], color=self.plot_title_color)
        self.plot.setLabel("left", "Normalized Data", color=self.plot_y_label_color)
        self.plot.setLabel("bottom", "Energy (keV)", color=self.plot_x_label_color)

        self.plot.showGrid(x=True, y=True, alpha=0.4)

        # Not in compensated plot, because it is needed for the peak detection
        # even when the compensated plot is not active
        compensated_dp = self.get_compensated_dp(self.coeffs, self.data_points)
        smoothed_dp = self.get_smoothed_data(self.energies, compensated_dp, self.low_smooth_slider.value(),
                                             self.high_smooth_slider.value())
        compensated_normalized_dp = self.normalize_data(smoothed_dp)
        self.peak_dp_source = compensated_normalized_dp

        compensated_normalized_bg_dp = []

        if self.show_compensated_bg_plot:
            compensated_bg_dp = self.get_compensated_dp(self.bg_coeffs, self.bg_dps)
            smoothed_bg_dp = self.get_smoothed_data(self.bg_energies, compensated_bg_dp, self.low_smooth_slider.value(),
                                                    self.high_smooth_slider.value())
            compensated_normalized_bg_dp = self.normalize_data(smoothed_bg_dp)

        if self.show_compensated_result_plot:
            compensated_result_dp = self.get_compensated_dp(self.coeffs, self.result_dps)
            smoothed_result_dp = self.get_smoothed_data(self.energies, compensated_result_dp,
                                                        self.low_smooth_slider.value(),
                                                        self.high_smooth_slider.value())
            compensated_normalized_result_dp = self.normalize_data(smoothed_result_dp)
        else:
            compensated_normalized_result_dp = []

        # ORIGINAL PLOT
        if self.show_original_plot:
            self.original_normalized_dp = self.normalize_data(self.plot_data_points)
            self.plot.plot(self.energies, self.original_normalized_dp,
                           pen=pg.mkPen(color=self.original_plot_color, width=self.plot_line_width))

        # COMPENSATED PLOT
        if self.show_compensated_plot:
            self.plot.plot(self.energies, compensated_normalized_dp,
                           pen=pg.mkPen(color=self.compensated_plot_color, width=self.plot_line_width))

        # ORIGINAL BG PLOT
        if self.show_original_bg_plot:
            self.original_normalized_bg_dp = self.normalize_data(self.plot_bg_dps)
            self.plot.plot(self.bg_energies, self.original_normalized_bg_dp,
                           pen=pg.mkPen(color=self.original_bg_plot_color, width=self.plot_line_width))

        # BACKGROUND COMPENSATED PLOT
        if self.show_compensated_bg_plot:
            self.plot.plot(self.bg_energies, compensated_normalized_bg_dp,
                           pen=pg.mkPen(color=self.compensated_bg_plot_color, width=self.plot_line_width))

        # ORIGINAL RESULT PLOT (SUBTRACTED)
        if self.show_original_result_plot:
            self.plot.plot(self.energies, self.result_dps,
                           pen=pg.mkPen(color=self.original_result_plot_color, width=self.plot_line_width))

        # COMPENSATED RESULT PLOT (SUBTRACTED)
        if self.show_compensated_result_plot:
            self.plot.plot(self.energies, compensated_normalized_result_dp,
                           pen=pg.mkPen(color=self.compensated_result_plot_color, width=self.plot_line_width))

        # ANNOTATIONS
        if config.getboolean("Dynamic", "activate_peak_detection"):

            self.peak_energy = self.detect_peaks(self.peak_dp_source,
                                                 self.energies,
                                                 self.min_height_slider.value(),
                                                 self.prominence_slider.value(),
                                                 self.distance_slider.value())

            if self.black_on_white_plot_checkbox.isChecked():
                ann_line_color = "black"
                ann_text_color = "black"
                app_bg_color = "white"
            else:
                ann_line_color = config.get(f"{self.theme.title()}Theme", "plt_annotation_line_color")
                ann_text_color = config.get(f"{self.theme.title()}Theme", "plt_annotation_text_color")
                app_bg_color = config.get(f"{self.theme.title()}Theme", "app_bg_color")

            ann_line_width = config.getint("Settings", "plt_annotation_line_width")

            # PEAK DETECTION ANNOTATION
            for i, peak_energy in enumerate(self.peak_energy):
                energy_index = np.argmin(np.abs(np.array(self.energies) - peak_energy))

                # Get the corresponding data point value at the peak energy
                if self.show_compensated_plot and self.show_original_plot:
                    peak_value = compensated_normalized_dp[energy_index]
                elif self.show_compensated_plot and not self.show_original_plot:
                    peak_value = compensated_normalized_dp[energy_index]
                elif not self.show_compensated_plot and self.show_original_plot:
                    peak_value = self.original_normalized_dp[energy_index]
                elif self.show_original_result_plot and self.show_compensated_result_plot:
                    peak_value = compensated_normalized_result_dp[energy_index]
                else:
                    return

                if self.log_x_checkbox.isChecked():
                    peak_energy_log = np.log10(peak_energy)
                else:
                    peak_energy_log = peak_energy

                if self.log_y_checkbox.isChecked():
                    y_upper_limit = np.log10(1.1)
                else:
                    y_upper_limit = 1.1

                if self.log_y:
                    line = pg.PlotDataItem([peak_energy, peak_energy], [peak_value, 1.5],
                                           pen=pg.mkPen(color=ann_line_color, width=ann_line_width))
                    self.plot.addItem(line)

                    text = pg.TextItem(f"{peak_energy}", anchor=(0.5, 0.5), color=ann_text_color,
                                       fill=app_bg_color,
                                       border=ann_text_color)
                    text.setPos(peak_energy_log, y_upper_limit + 0.2)
                    self.plot.addItem(text)
                else:
                    line = pg.PlotDataItem([peak_energy, peak_energy], [peak_value, 1.1],
                                           pen=pg.mkPen(color=ann_line_color, width=ann_line_width))
                    self.plot.addItem(line)

                    # Display the daughter nuclide instead of the energy value
                    text = pg.TextItem(f"{peak_energy}", anchor=(0.5, 0.5), color=ann_text_color,
                                       fill=app_bg_color,
                                       border=ann_text_color)
                    text.setPos(peak_energy_log, y_upper_limit)
                    self.plot.addItem(text)

    def toggle_log_y(self):
        if self.file_loaded:
            if self.log_y_checkbox.isChecked():
                self.plot.setLogMode(y=True)
                self.log_y = True
                self.plot_data()
            else:
                self.plot.setLogMode(y=False)
                self.log_y = False
                self.plot_data()

    def toggle_log_x(self):
        if self.file_loaded:
            if self.log_x_checkbox.isChecked():
                self.plot.setLogMode(x=True)
                self.log_x = True
                self.plot_data()
            else:
                self.plot.setLogMode(x=False)
                self.log_x = False
                self.plot_data()

    def reset_plot(self):
        if self.file_loaded and self.plot is not None:
            self.plot.autoRange()

    def screenshot_plot(self):
        screenshot = self.plot.grab()
        suggested_name = f"{self.plot_title}_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.png"
        save_dir = config.get("Paths", "last_save_directory")
        if not save_dir:
            save_dir = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DesktopLocation)
        else:
            save_dir = os.path.abspath(save_dir)

        save_name = os.path.join(save_dir, suggested_name)
        save_dialog, _ = QFileDialog.getSaveFileName(self, "Save Screenshot", save_name, "PNG Files (*.png)")
        if save_dialog:
            if not save_dialog.endswith(".png"):
                save_dialog += ".png"
            screenshot.save(save_dialog, "png")

            # Update the last save directory in the config file
            new_save_dir = os.path.dirname(save_dialog)
            config.set("Paths", "last_save_directory", new_save_dir)
            with open("config.ini", "w", encoding="utf8") as f:  # type: SupportsWrite
                config.write(f)

    def screenshot_app(self):
        screenshot = QGuiApplication.primaryScreen().grabWindow(self.winId())
        suggested_name = f"{self.plot_title}_{datetime.now().strftime('%Y-%m-%d_%H-%M-%S')}.png"
        save_dir = config.get("Paths", "last_save_directory")
        if not save_dir:
            save_dir = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.DesktopLocation)
        else:
            save_dir = os.path.abspath(save_dir)

        save_name = os.path.join(save_dir, suggested_name)
        save_dialog, _ = QFileDialog.getSaveFileName(self, "Save Screenshot", save_name, "PNG Files (*.png)")
        if save_dialog:
            if not save_dialog.endswith(".png"):
                save_dialog += ".png"
            screenshot.save(save_dialog, "png")

            # Update the last save directory in the config file
            new_save_dir = os.path.dirname(save_dialog)
            config.set("Paths", "last_save_directory", new_save_dir)
            with open("config.ini", "w", encoding="utf8") as f:  # type: SupportsWrite
                config.write(f)

    @staticmethod
    def about():
        msg_box = QMessageBox()
        msg_box.setWindowTitle("About RadiaCode Spectrum Viewer")
        msg_box.setTextFormat(Qt.TextFormat.RichText)  # Set text format to RichText
        msg_box.setText("This program is a hobby project to learn Python / PySide.<br>"
                        "It is not connected to, or developed by <a href='https://radiacode.com/'>"
                        "the RadiaCode Company</a>,<br>"
                        "but I got very valuable help and feedback from them.<br>"
                        "Special thanks to Arsenii from the RadiaCode team!<br><br>"
                        "RadiaCode Spectrum Viewer uses the PySide6 framework.<br>"
                        "<a href='https://pypi.org/project/PySide6/'>https://pypi.org/project/PySide6/</a><br>"
                        "You can find and change the PySide6 files in the application directory.<br>"
                        "You also can find a copy of the LGPL license there.<br>"
                        "PySide6 framework sourcecode, instructions and documentation:<br>"
                        "<a href='https://github.com/qtproject/pyside-pyside-setup'>"
                        "https://github.com/qtproject/pyside-pyside-setup</a><br><br>"
                        "Packages used in this application:<br>"
                        "Numpy - <a href='https://numpy.org/'>https://numpy.org/</a><br>"
                        "<a href='https://numpy.org/doc/stable/license.html'>"
                        "https://numpy.org/doc/stable/license.html</a><br>"
                        "PyQtGraph - <a href='https://www.pyqtgraph.org/'>https://www.pyqtgraph.org/</a><br>"
                        "<a href='https://github.com/pyqtgraph/pyqtgraph/blob/master/LICENSE.txt'>"
                        "https://github.com/pyqtgraph/pyqtgraph/blob/master/LICENSE.txt</a><br>"
                        "SciPy - <a href='https://www.scipy.org/'>https://www.scipy.org/</a><br>"
                        "<a href='https://projects.scipy.org/scipylib/license.html'>"
                        "https://projects.scipy.org/scipylib/license.html</a><br>"
                        "Nuitka - <a href='https://nuitka.net/'>https://nuitka.net/</a><br>"
                        "<a href='https://github.com/Nuitka/Nuitka/blob/develop/LICENSE.txt'>"
                        "https://github.com/Nuitka/Nuitka/blob/develop/LICENSE.txt</a><br><br>"
                        "Crystal efficiency formula by opengeiger<br>"
                        "<a href='https://opengeiger.de'>https://opengeiger.de</a><br>"
                        "<a href='https://www.geigerzaehlerforum.de/index.php/topic,647.2070.html'>"
                        "https://www.geigerzaehlerforum.de/index.php/topic,647.2070.html</a><br><br>"
                        "Special thanks to Shafigh for confirming calculations.<br>"
                        "Special thanks to Jeremiah-KK0TX/WRWV921 for beta testing and mental support :)<br>"
                        "Special thanks to Cristian Arezzini for beta testing and feature requests.<br><br>"
                        "Author of the RSV: Promethium<br>"
                        "<a href='https://sourceforge.net/u/promethium/profile/'>"
                        "https://sourceforge.net/u/promethium/profile/</a><br>"
                        "<a href='https://github.com/Promethium147'>https://github.com/Promethium147</a><br><br>"
                        "License: CC-BY-NC-SA 4.0<br>"
                        "<a href='https://creativecommons.org/licenses/by-nc-sa/4.0/deed.en'>"
                        "License in human readable form</a><br><br>"
                        "Error reports, suggestions and feedback are welcome!<br>"
                        "Contact: <a href='mailto:pm147_software@pm.me'>pm147_software@pm.me</a><br><br>"
                        )
        msg_box.setStandardButtons(QMessageBox.StandardButton.Ok)
        msg_box.exec()

    def toggle_theme(self):
        current_theme = config.get("Dynamic", "theme")

        if current_theme == "light":
            self.apply_dark_stylesheet()
            self.theme_setting_checkbox.setChecked(True)
            config.set("Dynamic", "theme", "dark")

            with open("config.ini", "w", encoding="utf8") as f:  # type: SupportsWrite
                config.write(f)

            if self.file_loaded:
                self.plot_data()

        elif current_theme == "dark":
            self.apply_light_stylesheet()
            self.theme_setting_checkbox.setChecked(False)
            config.set("Dynamic", "theme", "light")
            with open("config.ini", "w", encoding="utf8") as f:  # type: SupportsWrite
                config.write(f)
            if self.file_loaded:
                self.plot_data()

    def toggle_original_plot(self):
        if self.file_loaded:
            if self.show_original_plot:
                self.show_original_plot = False
                self.original_plot_checkbox.setChecked(False)
                self.plot_data()
            else:
                self.show_original_plot = True
                self.original_plot_checkbox.setChecked(True)
                self.plot_data()

    def toggle_compensated_plot(self):
        if self.file_loaded:
            if self.show_compensated_plot:
                self.show_compensated_plot = False
                self.compensated_plot_checkbox.setChecked(False)
                self.plot_data()
            else:
                self.show_compensated_plot = True
                self.compensated_plot_checkbox.setChecked(True)
                self.plot_data()

    def toggle_original_bg_plot(self):
        if self.bg_loaded:
            if self.show_original_bg_plot:
                self.show_original_bg_plot = False
                self.original_bg_plot_checkbox.setChecked(False)
                self.plot_data()
            else:
                self.show_original_bg_plot = True
                self.original_bg_plot_checkbox.setChecked(True)
                self.plot_data()

    def toggle_compensated_bg_plot(self):
        if self.bg_loaded:
            if self.show_compensated_bg_plot:
                self.show_compensated_bg_plot = False
                self.compensated_bg_plot_checkbox.setChecked(False)
                self.plot_data()

            else:
                self.show_compensated_bg_plot = True
                self.compensated_bg_plot_checkbox.setChecked(True)
                self.plot_data()

    def toggle_black_white_plot(self):
        if self.file_loaded:
            show_black_on_white_plot = config.getboolean("Dynamic", "show_black_on_white_plot")
            if show_black_on_white_plot:
                self.black_white_plot = False
                self.black_on_white_plot_checkbox.setChecked(False)
                config.set("Dynamic", "show_black_on_white_plot", "False")
                with open("config.ini", "w", encoding="utf8") as f:  # type: SupportsWrite
                    config.write(f)
                self.plot_data()
            else:
                self.black_white_plot = True
                self.black_on_white_plot_checkbox.setChecked(True)
                config.set("Dynamic", "show_black_on_white_plot", "True")
                with open("config.ini", "w", encoding="utf8") as f:  # type: SupportsWrite
                    config.write(f)
                self.plot_data()

    def low_smooth_slider_changed(self):
        if self.file_loaded:
            self.plot_data()

    def high_smooth_slider_changed(self):
        if self.file_loaded:
            self.plot_data()

    def toggle_peak_detection(self):
        if self.file_loaded:
            if self.plot is not None:
                activate_peak_detection = config.getboolean("Dynamic", "activate_peak_detection")
                if activate_peak_detection:
                    config.set("Dynamic", "activate_peak_detection", "False")
                    with open("config.ini", "w", encoding="utf8") as f:  # type: SupportsWrite
                        config.write(f)
                    self.plot_data()
                else:
                    config.set("Dynamic", "activate_peak_detection", "True")
                    with open("config.ini", "w", encoding="utf8") as f:  # type: SupportsWrite
                        config.write(f)
                    self.plot_data()

    def peak_height_slider_changed(self):
        if self.file_loaded:
            self.peak_energy = self.detect_peaks(self.peak_dp_source,
                                                 self.energies,
                                                 self.min_height_slider.value(),
                                                 self.prominence_slider.value(),
                                                 self.distance_slider.value())
            self.plot_data()

    def peak_prominence_slider_changed(self):
        if self.file_loaded:
            self.peak_energy = self.detect_peaks(self.peak_dp_source,
                                                 self.energies,
                                                 self.min_height_slider.value(),
                                                 self.prominence_slider.value(),
                                                 self.distance_slider.value())
            self.plot_data()

    def peak_distance_slider_changed(self):
        if self.file_loaded:
            self.peak_energy = self.detect_peaks(self.peak_dp_source,
                                                 self.energies,
                                                 self.min_height_slider.value(),
                                                 self.prominence_slider.value(),
                                                 self.distance_slider.value())
            self.plot_data()

    def apply_light_stylesheet(self):
        self.theme = "light"
        self.theme_setting_checkbox.setChecked(False)
        config.set("Dynamic", "theme", "light")

        with open("config.ini", "w", encoding="utf8") as f:  # type: SupportsWrite
            config.write(f)

        self.plot_bg_color = config.get("LightTheme", "plt_bg_color")
        self.plot.setBackground(self.plot_bg_color)
        self.plot_title_color = config.get("LightTheme", "plt_title_color")
        self.plot_x_label_color = config.get("LightTheme", "plt_x_label_color")
        self.plot_y_label_color = config.get("LightTheme", "plt_y_label_color")
        self.compensated_plot_color = config.get("LightTheme", "plt_compensated_color")
        self.original_plot_color = config.get("LightTheme", "plt_original_color")
        self.original_bg_plot_color = config.get("LightTheme", "plt_original_bg_color")
        self.compensated_bg_plot_color = config.get("LightTheme", "plt_compensated_bg_color")
        self.original_result_plot_color = config.get("LightTheme", "plt_original_result_color")
        self.compensated_result_plot_color = config.get("LightTheme", "plt_compensated_result_color")

        colors = {
            "{{app_bg_color}}": config.get("LightTheme", "app_bg_color"),
            "{{label_color}}": config.get("LightTheme", "label_color"),
            "{{label_value_color}}": config.get("LightTheme", "label_value_color"),
            "{{section_line_color}}": config.get("LightTheme", "section_line_color"),
            "{{button_text_color}}": config.get("LightTheme", "button_text_color"),
            "{{button_bg_color}}": config.get("LightTheme", "button_bg_color"),
            "{{button_border_color}}": config.get("LightTheme", "button_border_color"),
            "{{button_text_color_disabled}}": config.get("LightTheme", "button_text_color_disabled"),
            "{{button_bg_color_disabled}}": config.get("LightTheme", "button_bg_color_disabled"),
            "{{button_border_color_disabled}}": config.get("LightTheme", "button_border_color_disabled"),
            "{{button_text_color_hover}}": config.get("LightTheme", "button_text_color_hover"),
            "{{button_bg_color_hover}}": config.get("LightTheme", "button_bg_color_hover"),
            "{{button_border_color_hover}}": config.get("LightTheme", "button_border_color_hover"),
            "{{button_text_color_pressed}}": config.get("LightTheme", "button_text_color_pressed"),
            "{{button_bg_color_pressed}}": config.get("LightTheme", "button_bg_color_pressed"),
            "{{button_border_color_pressed}}": config.get("LightTheme", "button_border_color_pressed"),
            "{{checkbox_label_color}}": config.get("LightTheme", "checkbox_label_color"),
            "{{checkbox_square_color}}": config.get("LightTheme", "checkbox_square_color"),
            "{{checkbox_square_color_disabled}}": config.get("LightTheme", "checkbox_square_color_disabled"),
            "{{checkbox_color}}": config.get("LightTheme", "checkbox_color"),
            "{{slider_color}}": config.get("LightTheme", "slider_color"),
            "{{slider_groove_color}}": config.get("LightTheme", "slider_groove_color"),
            "{{slider_handle_color}}": config.get("LightTheme", "slider_handle_color"),
            "{{original_plot_checkbox_color}}": config.get("LightTheme", "plt_original_color"),
            "{{compensated_plot_checkbox_color}}": config.get("LightTheme", "plt_compensated_color"),
            "{{original_bg_plot_checkbox_color}}": config.get("LightTheme", "plt_original_bg_color"),
            "{{compensated_bg_plot_checkbox_color}}": config.get("LightTheme", "plt_compensated_bg_color"),
            "{{section_label_color}}": config.get("LightTheme", "section_label_color"),
            "{{peak_detection_checkbox_color}}": config.get("LightTheme", "peak_detection_checkbox_color"),
        }

        # Load the QSS file
        with open("style.qss", "r", encoding="utf-8") as f:  # type: TextIO
            qss = f.read()

        with open("config.ini", "w", encoding="utf8") as f:  # type: SupportsWrite
            config.write(f)

        for placeholder, color in colors.items():
            qss = qss.replace(placeholder, color)

        self.setStyleSheet(qss)

    def apply_dark_stylesheet(self):
        self.theme = "dark"
        self.theme_setting_checkbox.setChecked(True)
        config.set("Dynamic", "theme", "dark")

        with open("config.ini", "w", encoding="utf8") as f:  # type: SupportsWrite
            config.write(f)

        self.plot_bg_color = config.get("DarkTheme", "plt_bg_color")
        self.plot.setBackground(self.plot_bg_color)
        self.plot_title_color = config.get("DarkTheme", "plt_title_color")
        self.plot_x_label_color = config.get("DarkTheme", "plt_x_label_color")
        self.plot_y_label_color = config.get("DarkTheme", "plt_y_label_color")
        self.original_plot_color = config.get("DarkTheme", "plt_original_color")
        self.compensated_plot_color = config.get("DarkTheme", "plt_compensated_color")
        self.original_bg_plot_color = config.get("DarkTheme", "plt_original_bg_color")
        self.compensated_bg_plot_color = config.get("DarkTheme", "plt_compensated_bg_color")
        self.original_result_plot_color = config.get("DarkTheme", "plt_original_result_color")
        self.compensated_result_plot_color = config.get("DarkTheme", "plt_compensated_result_color")

        colors = {
            "{{app_bg_color}}": config.get("DarkTheme", "app_bg_color"),
            "{{label_color}}": config.get("DarkTheme", "label_color"),
            "{{label_value_color}}": config.get("DarkTheme", "label_value_color"),
            "{{section_line_color}}": config.get("DarkTheme", "section_line_color"),
            "{{section_label_color}}": config.get("DarkTheme", "section_label_color"),
            "{{button_bg_color}}": config.get("DarkTheme", "button_bg_color"),
            "{{button_text_color}}": config.get("DarkTheme", "button_text_color"),
            "{{button_border_color}}": config.get("DarkTheme", "button_border_color"),
            "{{button_text_color_disabled}}": config.get("DarkTheme", "button_text_color_disabled"),
            "{{button_bg_color_disabled}}": config.get("DarkTheme", "button_bg_color_disabled"),
            "{{button_border_color_disabled}}": config.get("DarkTheme", "button_border_color_disabled"),
            "{{button_text_color_hover}}": config.get("DarkTheme", "button_text_color_hover"),
            "{{button_bg_color_hover}}": config.get("DarkTheme", "button_bg_color_hover"),
            "{{button_border_color_hover}}": config.get("DarkTheme", "button_border_color_hover"),
            "{{button_text_color_pressed}}": config.get("DarkTheme", "button_text_color_pressed"),
            "{{button_bg_color_pressed}}": config.get("DarkTheme", "button_bg_color_pressed"),
            "{{button_border_color_pressed}}": config.get("DarkTheme", "button_border_color_pressed"),
            "{{checkbox_label_color}}": config.get("DarkTheme", "checkbox_label_color"),
            "{{checkbox_square_color}}": config.get("DarkTheme", "checkbox_square_color"),
            "{{checkbox_square_color_disabled}}": config.get("DarkTheme", "checkbox_square_color_disabled"),
            "{{checkbox_color}}": config.get("DarkTheme", "checkbox_color"),
            "{{slider_color}}": config.get("DarkTheme", "slider_color"),
            "{{slider_groove_color}}": config.get("DarkTheme", "slider_groove_color"),
            "{{slider_handle_color}}": config.get("DarkTheme", "slider_handle_color"),
            "{{original_plot_checkbox_color}}": config.get("DarkTheme", "plt_original_color"),
            "{{original_bg_plot_checkbox_color}}": config.get("DarkTheme", "plt_original_bg_color"),
            "{{compensated_bg_plot_checkbox_color}}": config.get("DarkTheme", "plt_compensated_bg_color"),
            "{{compensated_plot_checkbox_color}}": config.get("DarkTheme", "plt_compensated_color"),
            "{{peak_detection_checkbox_color}}": config.get("DarkTheme", "peak_detection_checkbox_color"),
        }

        # Load the QSS file
        with open("style.qss", "r") as f:  # type: TextIO
            qss = f.read()

        for placeholder, color in colors.items():
            qss = qss.replace(placeholder, color)

        self.setStyleSheet(qss)


if __name__ == "__main__":

    if not QApplication.instance():
        app = QApplication(sys.argv)
    else:
        app = QApplication.instance()
    theme = config.get("Dynamic", "theme")

    if theme == "light":
        window = MainWindow()
        window.apply_light_stylesheet()
        window.show()
    elif theme == "dark":
        window = MainWindow()
        window.apply_dark_stylesheet()
        window.show()

    sys.exit(app.exec())
