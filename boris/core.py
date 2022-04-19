"""
BORIS
Behavioral Observation Research Interactive Software
Copyright 2012-2022 Olivier Friard

This file is part of BORIS.

  BORIS is free software; you can redistribute it and/or modify
  it under the terms of the GNU General Public License as published by
  the Free Software Foundation; either version 3 of the License, or
  any later version.

  BORIS is distributed in the hope that it will be useful,
  but WITHOUT ANY WARRANTY; without even the implied warranty of
  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
  GNU General Public License for more details.

  You should have received a copy of the GNU General Public License
  along with this program; if not see <http://www.gnu.org/licenses/>.

"""

import datetime

from math import log2
import json
import logging
import os
import pathlib
import platform
import re
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from decimal import *
from optparse import OptionParser
import gzip

import matplotlib

matplotlib.use("Qt5Agg")
# import matplotlib.pyplot as plt
import matplotlib.transforms as mtransforms
import numpy as np
import tablib
from matplotlib import dates
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtMultimedia import QSound
from PyQt5.QtWidgets import *
from PIL.ImageQt import ImageQt, Image

from boris import behav_coding_map_creator
from boris import behaviors_coding_map
from boris import dialog
from boris import gui_utilities

from boris import map_creator
from boris import geometric_measurement
from boris import modifiers_coding_map
from boris import observation
from boris import advanced_event_filtering
from boris import otx_parser
from boris import param_panel
from boris import plot_data_module
from boris import plot_events
from boris import plot_spectrogram_rt
from boris import plot_waveform_rt
from boris import plot_events_rt
from boris import project_functions
from boris import core_qrc
from boris import select_modifiers
from boris import select_observations
from boris import subjects_pad
from boris import utilities
from boris import version
from boris.core_ui import *
from boris.config import *
import boris.config as cfg
from boris.edit_event import DlgEditEvent, EditSelectedEvents
from boris.project import *
from boris.time_budget_widget import timeBudgetResults
from boris.utilities import *
from boris import player_dock_widget

from . import menu_options as menu_options
from . import connections as connections
from . import config_file
from . import select_subj_behav

__version__ = version.__version__
__version_date__ = version.__version_date__

if platform.python_version() < "3.6":
    logging.critical(f"BORIS requires Python 3.6+! You are using Python v. {platform.python_version()}")
    sys.exit()

if sys.platform == "darwin":  # for MacOS
    os.environ["LC_ALL"] = "en_US.UTF-8"

# check if argument
usage = 'usage: %prog [options] [-p PROJECT_PATH] [-o "OBSERVATION ID"]'
parser = OptionParser(usage=usage)

parser.add_option("-d", "--debug", action="store_true", default=False, dest="debug", help="Use debugging mode")
parser.add_option("-v", "--version", action="store_true", default=False, dest="version", help="Print version")
parser.add_option("-n", "--nosplashscreen", action="store_true", default=False, help="No splash screen")
parser.add_option("-p", "--project", action="store", default="", dest="project", help="Project file")
parser.add_option("-o", "--observation", action="store", default="", dest="observation", help="Observation id")

(options, args) = parser.parse_args()

# set logging parameters
if options.debug:
    logging.basicConfig(
        format="%(asctime)s,%(msecs)d  %(module)s l.%(lineno)d %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
        level=logging.DEBUG,
    )

if options.version:
    print(f"version {__version__} release date: {__version_date__}")
    sys.exit(0)

logging.debug("BORIS started")
logging.debug(f"BORIS version {__version__} release date: {__version_date__}")

current_system = platform.uname()

logging.debug(f"Operating system: {current_system.system} {current_system.release} {current_system.version}")
logging.debug(f"CPU: {current_system.machine} {current_system.processor}")
logging.debug(f"Python {platform.python_version()} ({'64-bit' if sys.maxsize > 2**32 else '32-bit'})")
logging.debug(f"Qt {QT_VERSION_STR} - PyQt{PYQT_VERSION_STR}")

r, memory = utilities.mem_info()
if not r:
    logging.debug((f"Memory (RAM)  Total: {memory.get('total_memory', 'Not available'):.2f} Mb  "
                   f"Free: {memory.get('free_memory', 'Not available'):.2f} Mb"))

video = 0

ROW = -1  # red triangle


class StyledItemDelegateTriangle(QStyledItemDelegate):
    """
    painter for twEvents with current time highlighting
    """

    def __init__(self, parent=None):
        super(StyledItemDelegateTriangle, self).__init__(parent)

    def paint(self, painter, option, index):

        super(StyledItemDelegateTriangle, self).paint(painter, option, index)

        if ROW != -1:
            if index.row() == ROW:
                polygonTriangle = QPolygon(3)
                polygonTriangle.setPoint(0, QtCore.QPoint(option.rect.x() + 15, option.rect.y()))
                polygonTriangle.setPoint(1, QtCore.QPoint(option.rect.x(), option.rect.y() - 5))
                polygonTriangle.setPoint(2, QtCore.QPoint(option.rect.x(), option.rect.y() + 5))
                painter.save()
                painter.setRenderHint(painter.Antialiasing)
                painter.setBrush(QBrush(QColor(QtCore.Qt.red)))
                painter.setPen(QPen(QColor(QtCore.Qt.red)))
                painter.drawPolygon(polygonTriangle)
                painter.restore()


class MainWindow(QMainWindow, Ui_MainWindow):

    pj = dict(EMPTY_PROJECT)
    project = False
    geometric_measurements_mode = False

    time_observer_signal = pyqtSignal(float)

    processes = []  # list of QProcess processes
    overlays = {}  # dict for storing video overlays

    saved_state = None

    user_move_slider = False

    observationId = ""  # current observation id
    timeOffset = 0.0

    confirmSound = False  # if True each keypress will be confirmed by a beep

    spectrogramHeight = 80
    spectrogram_time_interval = SPECTROGRAM_DEFAULT_TIME_INTERVAL
    spectrogram_color_map = SPECTROGRAM_DEFAULT_COLOR_MAP

    frame_bitmap_format = FRAME_DEFAULT_BITMAP_FORMAT

    alertNoFocalSubject = False  # if True an alert will show up if no focal subject
    trackingCursorAboveEvent = False  # if True the cursor will appear above the current event in events table
    checkForNewVersion = False  # if True BORIS will check for new version every 15 days

    pause_before_addevent = False  # pause before "Add event" command CTRL + A

    timeFormat = HHMMSS  # 's' or 'hh:mm:ss'
    repositioningTimeOffset = 0
    automaticBackup = 0  # automatic backup interval (0 no backup)

    projectChanged = False
    liveObservationStarted = False

    # data structures for external data plot
    plot_data = {}
    ext_data_timer_list = []

    projectFileName = ""
    mediaTotalLength = None

    beep_every = 0

    plot_colors = BEHAVIORS_PLOT_COLORS
    behav_category_colors = CATEGORY_COLORS_LIST

    measurement_w = None
    memPoints = []  # memory of clicked points for measurement tool
    memPoints_video = []  # memory of clicked points for measurement tool

    behaviouralStringsSeparator = "|"

    # time laps
    fast = 10

    currentStates = {}
    subject_name_index = {}
    flag_slow = False
    play_rate = 1

    play_rate_step = 0.1

    currentSubject = ""  # contains the current subject of observation

    detailedObs = {}

    codingMapWindowGeometry = 0

    projectWindowGeometry = 0  # memorize size of project window

    imageDirectory = ""  # image cache directory

    # FFmpeg
    memx, memy, mem_player = -1, -1, -1

    # path for ffmpeg/ffmpeg.exe program
    ffmpeg_bin = ""
    ffmpeg_cache_dir = ""
    ffmpeg_cache_dir_max_size = 0

    # dictionary for FPS storing
    fps = 0

    playerType: str = ""  # VLC, LIVE, VIEWER
    playMode = MPV  # player mode can be MPV
    frame_mode: bool = False  # player in frame-by-frame mode

    # spectrogram
    chunk_length = 60  # spectrogram chunk length in seconds

    memMedia = ""
    close_the_same_current_event = False
    tcp_port = 0
    bcm_dict = {}  # handle behavior coding map
    recent_projects = []

    filtered_subjects = []
    filtered_behaviors = []

    dw_player = []

    save_project_json_started = False

    # interpolated time
    lastPlayTime = 0
    lastPlayTimeGlobal = 0

    def __init__(self, ffmpeg_bin, parent=None):

        super(MainWindow, self).__init__(parent)
        self.setupUi(self)

        sys.excepthook = self.excepthook

        self.ffmpeg_bin = ffmpeg_bin
        # set icons
        self.setWindowIcon(QIcon(":/small_logo"))

        self.action_obs_list.setIcon(QIcon(":/observations_list"))
        self.actionPlay.setIcon(QIcon(":/play"))
        self.actionReset.setIcon(QIcon(":/reset"))
        self.actionJumpBackward.setIcon(QIcon(":/jump_backward"))
        self.actionJumpForward.setIcon(QIcon(":/jump_forward"))

        self.actionFaster.setIcon(QIcon(":/faster"))
        self.actionSlower.setIcon(QIcon(":/slower"))
        self.actionNormalSpeed.setIcon(QIcon(":/normal_speed"))

        self.actionPrevious.setIcon(QIcon(":/previous"))
        self.actionNext.setIcon(QIcon(":/next"))

        self.actionSnapshot.setIcon(QIcon(":/snapshot"))

        self.actionFrame_backward.setIcon(QIcon(":/frame_backward"))
        self.actionFrame_forward.setIcon(QIcon(":/frame_forward"))
        self.actionCloseObs.setIcon(QIcon(":/close_observation"))
        self.actionCurrent_Time_Budget.setIcon(QIcon(":/time_budget"))
        self.actionPlot_current_observation.setIcon(QIcon(":/plot_current"))
        self.actionFind_in_current_obs.setIcon(QIcon(":/find"))

        self.setWindowTitle(f"{programName} ({__version__})")

        self.w_obs_info.setVisible(False)

        self.lbLogoBoris.setPixmap(QPixmap(":/logo"))

        self.lbLogoBoris.setScaledContents(False)
        self.lbLogoBoris.setAlignment(Qt.AlignCenter)

        self.lbLogoUnito.setPixmap(QPixmap(":/dbios_unito"))
        self.lbLogoUnito.setScaledContents(False)
        self.lbLogoUnito.setAlignment(Qt.AlignCenter)

        self.toolBar.setEnabled(True)

        # start with dock widget invisible
        for w in [self.dwObservations, self.dwEthogram, self.dwSubjects]:
            w.setVisible(False)
            w.keyPressEvent = self.keyPressEvent

        # if BORIS is running on Mac lock all dockwidget features
        # because Qdockwidgets may have a strange behavior
        if sys.platform == "darwin":
            self.action_block_dockwidgets.setChecked(True)
            self.block_dockwidgets()

        font = QFont()
        font.setPointSize(15)
        for w in (self.lb_player_status, self.lb_current_media_time, self.lbFocalSubject, self.lbCurrentStates):
            w.clear()
            w.setFont(font)
        self.lbFocalSubject.setText(NO_FOCAL_SUBJECT)

        # observation time interval
        self.lb_obs_time_interval = QLabel()
        self.lb_obs_time_interval.setFrameStyle(QFrame.StyledPanel)
        self.lb_obs_time_interval.setMinimumWidth(160)
        self.statusbar.addPermanentWidget(self.lb_obs_time_interval)

        # time offset
        self.lbTimeOffset = QLabel()
        self.lbTimeOffset.setFrameStyle(QFrame.StyledPanel)
        self.lbTimeOffset.setMinimumWidth(160)
        self.statusbar.addPermanentWidget(self.lbTimeOffset)

        # speed
        self.lbSpeed = QLabel()
        self.lbSpeed.setFrameStyle(QFrame.StyledPanel)
        self.lbSpeed.setMinimumWidth(40)
        self.statusbar.addPermanentWidget(self.lbSpeed)

        # set painter for twEvents to highlight current row
        self.twEvents.setItemDelegate(StyledItemDelegateTriangle(self.twEvents))

        self.twEvents.setColumnCount(len(tw_events_fields))
        self.twEvents.setHorizontalHeaderLabels(tw_events_fields)

        self.config_param = INIT_PARAM

        menu_options.update_menu(self)
        connections.connections(self)
        config_file.read(self)

        # 1 / 0

    def excepthook(self, exception_type, exception_value, traceback_object):
        """
        error management
        """
        dialog.error_message3(exception_type, exception_value, traceback_object)

    def block_dockwidgets(self):
        """
        allow to block Qdockwidgets on main window because they can have a strange behavior specially on Mac
        """
        for w in [self.dwObservations, self.dwEthogram, self.dwSubjects]:
            if self.action_block_dockwidgets.isChecked():
                w.setFloating(False)
                w.setFeatures(QDockWidget.NoDockWidgetFeatures)
            else:
                w.setFeatures(QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetFloatable)

    def advanced_event_filtering(self):
        """
        advanced filter for coded event
        """

        advanced_event_filtering.event_filtering(self)

    def twEthogram_sorted(self, index, order):
        """
        Sort ethogram widget
        """

        self.twEthogram.sortItems(index, order)

    def sort_twSubjects(self, index, order):
        """
        Sort subjects widget
        """

        self.twSubjects.sortItems(index, order)

    def export_observations_list_clicked(self):
        """
        export the list of observations
        """

        resultStr, selected_observations = select_observations.select_observations(self.pj, MULTIPLE)
        if not resultStr or not selected_observations:
            return

        extended_file_formats = [
            "Tab Separated Values (*.tsv)",
            "Comma Separated Values (*.csv)",
            "Open Document Spreadsheet ODS (*.ods)",
            "Microsoft Excel Spreadsheet XLSX (*.xlsx)",
            "Legacy Microsoft Excel Spreadsheet XLS (*.xls)",
            "HTML (*.html)",
        ]
        file_formats = ["tsv", "csv", "ods", "xlsx", "xls", "html"]

        file_name, filter_ = QFileDialog().getSaveFileName(self, "Export list of selected observations", "",
                                                           ";;".join(extended_file_formats))

        if file_name:
            output_format = file_formats[extended_file_formats.index(filter_)]
            if pathlib.Path(file_name).suffix != "." + output_format:
                file_name = str(pathlib.Path(file_name)) + "." + output_format
                # check if file name with extension already exists
                if pathlib.Path(file_name).is_file():
                    if (dialog.MessageDialog(cfg.programName, f"The file {file_name} already exists.",
                                             [cfg.CANCEL, cfg.OVERWRITE]) == cfg.CANCEL):
                        return

            if not project_functions.export_observations_list(self.pj, selected_observations, file_name, output_format):
                QMessageBox.warning(self, cfg.programName, "File not created due to an error")

    def check_project_integrity(self):
        """
        launch check project integrity function
        """

        ib = dialog.Input_dialog(
            "Select the elements to be checked",
            [
                ("cb", "Test media file accessibility", True),
            ],
        )
        if not ib.exec_():
            return

        msg = project_functions.check_project_integrity(
            self.pj,
            self.timeFormat,
            self.projectFileName,
            media_file_available=ib.elements["Test media file accessibility"].isChecked(),
        )
        if msg:
            msg = f"Some issues were found in the project<br><br>{msg}"
            self.results = dialog.ResultsWidget()
            self.results.setWindowTitle("Check project integrity")
            self.results.ptText.clear()
            self.results.ptText.setReadOnly(True)
            self.results.ptText.appendHtml(msg)
            self.results.show()
        else:
            QMessageBox.information(self, cfg.programName, "The current project has no issues")

    def remove_media_files_path(self):
        """
        remove path of media files
        """

        if (dialog.MessageDialog(
                cfg.programName,
            ("Removing the path of media files from the project file is irreversible.<br>"
             "Are you sure to continue?"),
            [YES, NO],
        ) == NO):
            return

        self.pj = project_functions.remove_media_files_path(self.pj)
        self.projectChanged = True

    # TODO: externalize function

    def view_behavior(self):
        """
        show details of selected behavior
        """
        if self.project:
            if self.twEthogram.selectedIndexes():
                ethogramRow = self.twEthogram.selectedIndexes()[0].row()
                behav = dict(self.pj[ETHOGRAM][str(self.twEthogram.selectedIndexes()[0].row())])
                if behav[MODIFIERS]:
                    modifiers = ""
                    for idx in sorted_keys(behav[MODIFIERS]):
                        if behav[MODIFIERS][idx]["name"]:
                            modifiers += (
                                f"<br>Name: {behav[MODIFIERS][idx]['name'] if behav[MODIFIERS][idx]['name'] else '-'}"
                                f"<br>Type: {MODIFIERS_STR[behav[MODIFIERS][idx]['type']]}<br>")

                        if behav[MODIFIERS][idx]["values"]:
                            modifiers += "Values:<br>"
                            for m in behav[MODIFIERS][idx]["values"]:
                                modifiers += f"{m}, "
                            modifiers = modifiers.strip(" ,") + "<br>"
                else:
                    modifiers = "-"

                results = dialog.Results_dialog()
                results.setWindowTitle("View behavior")
                results.ptText.clear()
                results.ptText.setReadOnly(True)
                txt = (f"Code: <b>{behav['code']}</b><br>"
                       f"Type: {behav['type']}<br>"
                       f"Key: <b>{behav['key']}</b><br><br>"
                       f"Description: {behav['description']}<br><br>"
                       f"Category: {behav['category'] if behav['category'] else '-'}<br><br>"
                       f"Exclude: {behav['excluded']}<br><br><br>"
                       f"Modifiers:<br>{modifiers}")
                results.ptText.appendHtml(txt)
                results.exec_()

    def ffmpeg_process(self, action: str):
        """
        launch ffmpeg process

        Args:
            action (str): "reencode_resize, rotate
        """
        if action not in ["reencode_resize", "rotate"]:
            return

        def readStdOutput(idx):

            self.processes_widget.label.setText(("This operation can be long. Be patient...\n\n"
                                                 "Done: {done} of {tot}").format(
                                                     done=self.processes_widget.number_of_files - len(self.processes),
                                                     tot=self.processes_widget.number_of_files,
                                                 ))
            self.processes_widget.lwi.clear()
            self.processes_widget.lwi.addItems([
                self.processes[idx - 1][1][2],
                self.processes[idx - 1][0].readAllStandardOutput().data().decode("utf-8"),
            ])

        def qprocess_finished(idx):
            """
            function triggered when process finished
            """
            if self.processes:
                del self.processes[idx - 1]
            if self.processes:
                self.processes[-1][0].start(self.processes[-1][1][0], self.processes[-1][1][1])
            else:
                self.processes_widget.hide()
                del self.processes_widget

        if self.processes:
            QMessageBox.warning(self, programName, "BORIS is already doing some job.")
            return

        fn = QFileDialog().getOpenFileNames(self, "Select one or more media files to process", "", "Media files (*)")
        fileNames = fn[0] if type(fn) is tuple else fn

        if fileNames:
            if action == "reencode_resize":
                current_bitrate = 2000
                current_resolution = 1024

                r = utilities.accurate_media_analysis(self.ffmpeg_bin, fileNames[0])
                if "error" in r:
                    QMessageBox.warning(self, programName, f"{fileNames[0]}. {r['error']}")
                elif r["has_video"]:
                    try:
                        current_bitrate = r["bitrate"]
                    except Exception:
                        pass
                    try:
                        current_resolution = int(r["resolution"].split("x")[0])
                    except Exception:
                        pass

                ib = dialog.Input_dialog(
                    "Set the parameters for re-encoding / resizing",
                    [
                        ("sb", "Horizontal resolution (in pixel)", 352, 3840, 100, current_resolution),
                        ("sb", "Video quality (bitrate)", 100, 1000000, 500, current_bitrate),
                    ],
                )
                if not ib.exec_():
                    return

                if len(fileNames) > 1:
                    if (dialog.MessageDialog(
                            programName,
                            "All the selected video files will be re-encoded / resized with these parameters",
                        [OK, CANCEL],
                    ) == CANCEL):
                        return

                horiz_resol = ib.elements["Horizontal resolution (in pixel)"].value()
                video_quality = ib.elements["Video quality (bitrate)"].value()

            if action == "rotate":
                rotation_items = ("Rotate 90 clockwise", "Rotate 90 counter clockwise", "rotate 180")

                rotation, ok = QInputDialog.getItem(self, "Rotate media file(s)", "Type of rotation", rotation_items, 0,
                                                    False)

                if not ok:
                    return
                rotation_idx = rotation_items.index(rotation) + 1

            # check if processed files already exist
            files_list = []
            for file_name in fileNames:
                if action == "reencode_resize":
                    fn = f"{file_name}.re-encoded.{horiz_resol}px.{video_quality}k.avi"
                if action == "rotate":
                    fn = f"{file_name}.rotated{['', '90', '-90', '180'][rotation_idx]}.avi"
                if os.path.isfile(fn):
                    files_list.append(fn)

            if files_list:
                response = dialog.MessageDialog(programName, "Some file(s) already exist.\n\n" + "\n".join(files_list),
                                                [OVERWRITE_ALL, CANCEL])
                if response == CANCEL:
                    return

            self.processes_widget = dialog.Info_widget()
            self.processes_widget.resize(350, 100)
            self.processes_widget.setWindowFlags(Qt.WindowStaysOnTopHint)
            if action == "reencode_resize":
                self.processes_widget.setWindowTitle("Re-encoding and resizing with FFmpeg")
            if action == "rotate":
                self.processes_widget.setWindowTitle("Rotating the video with FFmpeg")

            self.processes_widget.label.setText("This operation can be long. Be patient...\n\n")
            self.processes_widget.number_of_files = len(fileNames)
            self.processes_widget.show()

            for file_name in fileNames:

                if action == "reencode_resize":
                    args = [
                        "-y",
                        "-i",
                        f"{file_name}",
                        "-vf",
                        f"scale={horiz_resol}:-1",
                        "-b:v",
                        f"{video_quality}k",
                        f"{file_name}.re-encoded.{horiz_resol}px.{video_quality}k.avi",
                    ]

                if action == "rotate":

                    # check bitrate
                    r = accurate_media_analysis(self.ffmpeg_bin, file_name)
                    if "error" not in r and r["bitrate"] != -1:
                        video_quality = r["bitrate"]
                    else:
                        video_quality = 2000

                    if rotation_idx in [1, 2]:
                        args = [
                            "-y",
                            "-i",
                            f"{file_name}",
                            "-vf",
                            f"transpose={rotation_idx}",
                            "-codec:a",
                            "copy",
                            "-b:v",
                            f"{video_quality}k",
                            f"{file_name}.rotated{['', '90', '-90'][rotation_idx]}.avi",
                        ]

                    if rotation_idx == 3:  # 180
                        args = [
                            "-y",
                            "-i",
                            f"{file_name}",
                            "-vf",
                            "transpose=2,transpose=2",
                            "-codec:a",
                            "copy",
                            "-b:v",
                            f"{video_quality}k",
                            f"{file_name}.rotated180.avi",
                        ]

                self.processes.append([QProcess(self), [self.ffmpeg_bin, args, file_name]])
                self.processes[-1][0].setProcessChannelMode(QProcess.MergedChannels)
                self.processes[-1][0].readyReadStandardOutput.connect(lambda: readStdOutput(len(self.processes)))
                self.processes[-1][0].readyReadStandardError.connect(lambda: readStdOutput(len(self.processes)))
                self.processes[-1][0].finished.connect(lambda: qprocess_finished(len(self.processes)))

            self.processes[-1][0].start(self.processes[-1][1][0], self.processes[-1][1][1])

    def click_signal_from_coding_pad(self, behaviorCode):
        """
        handle click received from coding pad
        """
        sendEventSignal = pyqtSignal(QEvent)
        q = QKeyEvent(QEvent.KeyPress, Qt.Key_Enter, Qt.NoModifier, text=behaviorCode)
        self.keyPressEvent(q)

    def close_signal_from_coding_pad(self, geometry, preferences):
        """
        save coding pad geometry after close
        """
        self.config_param[CODING_PAD_GEOMETRY] = geometry
        self.config_param[CODING_PAD_CONFIG] = preferences

    def click_signal_from_subjects_pad(self, subject):
        """
        handle click received from subjects pad
        """
        sendEventSignal = pyqtSignal(QEvent)
        q = QKeyEvent(QEvent.KeyPress, Qt.Key_Enter, Qt.NoModifier, text="#subject#" + subject)
        self.keyPressEvent(q)

    def signal_from_subjects_pad(self, event):
        """
        receive signal from subjects pad
        """
        self.keyPressEvent(event)

    def close_signal_from_subjects_pad(self, geom):
        """
        save subjects pad geometry after close
        """
        self.subjectspad_geometry_memory = geom

    def show_subjects_pad(self):
        """
        show subjects pad window
        """
        if not self.pj[SUBJECTS]:
            QMessageBox.warning(self, programName, "No subjects are defined")
            return

        if self.playerType == VIEWER:
            QMessageBox.warning(self, programName, "The subjects pad is not available in <b>VIEW</b> mode")
            return

        if hasattr(self, "subjects_pad"):
            self.subjects_pad.filtered_subjects = [
                self.twSubjects.item(i, SUBJECT_NAME_FIELD_IDX).text() for i in range(self.twSubjects.rowCount())
            ]
            if not self.subjects_pad.filtered_subjects:
                QMessageBox.warning(self, programName, "No subjects to show")
                return
            self.subjects_pad.compose()
            self.subjects_pad.show()
            self.subjects_pad.setGeometry(
                self.subjectspad_geometry_memory.x(),
                self.subjectspad_geometry_memory.y(),
                self.subjectspad_geometry_memory.width(),
                self.subjectspad_geometry_memory.height(),
            )
        else:
            filtered_subjects = [
                self.twSubjects.item(i, SUBJECT_NAME_FIELD_IDX).text() for i in range(self.twSubjects.rowCount())
            ]
            if not filtered_subjects:
                QMessageBox.warning(self, programName, "No subjects to show")
                return
            self.subjects_pad = subjects_pad.SubjectsPad(self.pj, filtered_subjects)
            self.subjects_pad.setWindowFlags(Qt.WindowStaysOnTopHint)
            self.subjects_pad.sendEventSignal.connect(self.signal_from_subjects_pad)
            self.subjects_pad.clickSignal.connect(self.click_signal_from_subjects_pad)
            self.subjects_pad.close_signal.connect(self.close_signal_from_subjects_pad)
            self.subjects_pad.show()

    def show_all_behaviors(self):
        """
        show all behaviors in ethogram
        """
        self.load_behaviors_in_twEthogram([self.pj[ETHOGRAM][x][BEHAVIOR_CODE] for x in self.pj[ETHOGRAM]])

    def show_all_subjects(self):
        """
        show all subjects in subjects list
        """
        self.load_subjects_in_twSubjects([self.pj[SUBJECTS][x][SUBJECT_NAME] for x in self.pj[SUBJECTS]])

    def filter_behaviors(
        self,
        title="Select the behaviors to show in the ethogram table",
        text="Behaviors to show in ethogram list",
        table=ETHOGRAM,
        behavior_type=[STATE_EVENT, POINT_EVENT],
    ):
        """
        allow user to:
            filter behaviors in ethogram widget
            or
            select behaviors to remove from the total time

        Args:
            title (str): title of dialog box
            text (str): text of dialog box
            table (str): table where behaviors will be filtered

        Returns:
            (None if table = ETHOGRAM)
            boolean: True if Cancel button pressed else False
            list: list of selected behaviors
        """

        if not self.pj[ETHOGRAM]:
            return

        behavior_type = [x.upper() for x in behavior_type]

        paramPanelWindow = param_panel.Param_panel()
        paramPanelWindow.setWindowTitle(title)
        paramPanelWindow.lbBehaviors.setText(text)
        for w in [
                paramPanelWindow.lwSubjects,
                paramPanelWindow.pbSelectAllSubjects,
                paramPanelWindow.pbUnselectAllSubjects,
                paramPanelWindow.pbReverseSubjectsSelection,
                paramPanelWindow.lbSubjects,
                paramPanelWindow.cbIncludeModifiers,
                paramPanelWindow.cbExcludeBehaviors,
                paramPanelWindow.frm_time,
                paramPanelWindow.frm_time_bin_size,
        ]:
            w.setVisible(False)

        gui_utilities.restore_geometry(paramPanelWindow, "filter behaviors", (800, 600))

        # behaviors filtered
        if table == ETHOGRAM:
            filtered_behaviors = [self.twEthogram.item(i, 1).text() for i in range(self.twEthogram.rowCount())]
        else:
            filtered_behaviors = []

        if BEHAVIORAL_CATEGORIES in self.pj:
            categories = self.pj[BEHAVIORAL_CATEGORIES][:]
            # check if behavior not included in a category
            if "" in [
                    self.pj[ETHOGRAM][idx][BEHAVIOR_CATEGORY]
                    for idx in self.pj[ETHOGRAM]
                    if BEHAVIOR_CATEGORY in self.pj[ETHOGRAM][idx]
            ]:
                categories += [""]
        else:
            categories = ["###no category###"]

        for category in categories:

            if category != "###no category###":

                if category == "":
                    paramPanelWindow.item = QListWidgetItem("No category")
                    paramPanelWindow.item.setData(34, "No category")
                else:
                    paramPanelWindow.item = QListWidgetItem(category)
                    paramPanelWindow.item.setData(34, category)

                font = QFont()
                font.setBold(True)
                paramPanelWindow.item.setFont(font)
                paramPanelWindow.item.setData(33, "category")
                paramPanelWindow.item.setData(35, False)

                paramPanelWindow.lwBehaviors.addItem(paramPanelWindow.item)

            # check if behavior type must be shown
            for behavior in [self.pj[ETHOGRAM][x][BEHAVIOR_CODE] for x in sorted_keys(self.pj[ETHOGRAM])]:
                if project_functions.event_type(behavior, self.pj[ETHOGRAM]) not in behavior_type:
                    continue

                if (categories == ["###no category###"]) or (behavior in [
                        self.pj[ETHOGRAM][x][BEHAVIOR_CODE]
                        for x in self.pj[ETHOGRAM]
                        if BEHAVIOR_CATEGORY in self.pj[ETHOGRAM][x] and
                        self.pj[ETHOGRAM][x][BEHAVIOR_CATEGORY] == category
                ]):

                    paramPanelWindow.item = QListWidgetItem(behavior)
                    if behavior in filtered_behaviors:
                        paramPanelWindow.item.setCheckState(Qt.Checked)
                    else:
                        paramPanelWindow.item.setCheckState(Qt.Unchecked)

                    if category != "###no category###":
                        paramPanelWindow.item.setData(33, "behavior")
                        if category == "":
                            paramPanelWindow.item.setData(34, "No category")
                        else:
                            paramPanelWindow.item.setData(34, category)

                    paramPanelWindow.lwBehaviors.addItem(paramPanelWindow.item)

        if paramPanelWindow.exec_():
            if self.observationId and set(paramPanelWindow.selectedBehaviors) != set(filtered_behaviors):
                self.projectChanged = True

            gui_utilities.save_geometry(paramPanelWindow, "filter behaviors")

            if table == ETHOGRAM:
                self.load_behaviors_in_twEthogram(paramPanelWindow.selectedBehaviors)
                # update coding pad
                if hasattr(self, "codingpad"):
                    self.codingpad.filtered_behaviors = [
                        self.twEthogram.item(i, 1).text() for i in range(self.twEthogram.rowCount())
                    ]
                    self.codingpad.compose()
                return None
            else:
                return False, paramPanelWindow.selectedBehaviors
        else:
            return True, []

    def filter_subjects(self):
        """
        allow user to select subjects to show in the subjects widget
        """

        paramPanelWindow = param_panel.Param_panel()
        paramPanelWindow.setWindowTitle("Select the subjects to show in the subjects list")
        paramPanelWindow.lbBehaviors.setText("Subjects")

        for w in [
                paramPanelWindow.lwSubjects,
                paramPanelWindow.pbSelectAllSubjects,
                paramPanelWindow.pbUnselectAllSubjects,
                paramPanelWindow.pbReverseSubjectsSelection,
                paramPanelWindow.lbSubjects,
                paramPanelWindow.cbIncludeModifiers,
                paramPanelWindow.cbExcludeBehaviors,
                paramPanelWindow.frm_time,
                paramPanelWindow.frm_time_bin_size,
        ]:
            w.setVisible(False)

        gui_utilities.restore_geometry(paramPanelWindow, "filter subjects", (800, 600))

        # subjects filtered
        filtered_subjects = [
            self.twSubjects.item(i, SUBJECT_NAME_FIELD_IDX).text() for i in range(self.twSubjects.rowCount())
        ]

        for subject in [self.pj[SUBJECTS][x][SUBJECT_NAME] for x in sorted_keys(self.pj[SUBJECTS])]:

            paramPanelWindow.item = QListWidgetItem(subject)
            if subject in filtered_subjects:
                paramPanelWindow.item.setCheckState(Qt.Checked)
            else:
                paramPanelWindow.item.setCheckState(Qt.Unchecked)

            paramPanelWindow.lwBehaviors.addItem(paramPanelWindow.item)

        if paramPanelWindow.exec_():
            if self.observationId and set(paramPanelWindow.selectedBehaviors) != set(filtered_subjects):
                self.projectChanged = True
            self.load_subjects_in_twSubjects(paramPanelWindow.selectedBehaviors)

            gui_utilities.save_geometry(paramPanelWindow, "filter subjects")

            # update subjects pad
            if hasattr(self, "subjects_pad"):
                self.subjects_pad.filtered_subjects = [
                    self.twSubjects.item(i, SUBJECT_NAME_FIELD_IDX).text() for i in range(self.twSubjects.rowCount())
                ]
                self.subjects_pad.compose()

    def generate_wav_file_from_media(self):
        """
        extract wav from all media files loaded in player #1
        """

        logging.debug("function: create wav file from media")

        # check temp dir for images from ffmpeg
        tmp_dir = (self.ffmpeg_cache_dir
                   if self.ffmpeg_cache_dir and os.path.isdir(self.ffmpeg_cache_dir) else tempfile.gettempdir())

        w = dialog.Info_widget()
        w.lwi.setVisible(False)
        w.resize(350, 100)
        w.setWindowFlags(Qt.WindowStaysOnTopHint)
        w.setWindowTitle(programName)
        w.label.setText("Extracting WAV from media files...")

        for media in self.pj[OBSERVATIONS][self.observationId][FILE][PLAYER1]:
            media_file_path = project_functions.media_full_path(media, self.projectFileName)
            if os.path.isfile(media_file_path):

                w.show()
                QApplication.processEvents()

                if utilities.extract_wav(self.ffmpeg_bin, media_file_path, tmp_dir) == "":
                    QMessageBox.critical(self, programName,
                                         f"Error during extracting WAV of the media file {media_file_path}")
                    break

                w.hide()

            else:
                QMessageBox.warning(self, programName, f"<b>{media_file_path}</b> file not found")

    def show_plot_widget(self, plot_type: str, warning: bool = False):
        """
        show plot widgets (spectrogram, waveform, plot events)
        if plot does not exist it is created

        Args:
            plot_type (str): type of plot ("spectrogram", "waveform", "plot_events")
            warning (bool): Display message if True
        """

        if plot_type not in ["waveform", "spectrogram", "plot_events"]:
            logging.critical("error on plot type")
            return

        if self.playerType in [LIVE, VIEWER] and plot_type in ["waveform", "spectrogram"]:
            QMessageBox.warning(self, programName,
                                f"The sound signal visualization is not available in <b>{self.playerType}</b> mode")
            return

        if plot_type == "spectrogram":
            if hasattr(self, "spectro"):
                self.spectro.show()
            else:
                logging.debug("create spectrogram plot")

                # remember if player paused
                if warning:
                    if self.playerType == VLC and self.playMode == MPV:
                        flag_paused = self.is_playing()

                self.pause_video()

                if (warning and dialog.MessageDialog(
                        programName,
                    (f"You choose to visualize the {plot_type} during this observation.<br>"
                     f"{plot_type} generation can take some time for long media, be patient"),
                    [YES, NO],
                ) == NO):
                    if self.playerType == VLC and self.playMode == MPV and not flag_paused:
                        self.play_video()
                    return

                self.generate_wav_file_from_media()

                tmp_dir = (self.ffmpeg_cache_dir
                           if self.ffmpeg_cache_dir and os.path.isdir(self.ffmpeg_cache_dir) else tempfile.gettempdir())

                wav_file_path = (
                    pathlib.Path(tmp_dir) /
                    pathlib.Path(self.dw_player[0].player.playlist[self.dw_player[0].player.playlist_pos]["filename"] +
                                 ".wav").name)

                self.spectro = plot_spectrogram_rt.Plot_spectrogram_RT()

                self.spectro.setWindowFlags(Qt.WindowStaysOnTopHint)
                self.spectro.setWindowFlags(self.spectro.windowFlags() & ~Qt.WindowMinimizeButtonHint)

                self.spectro.interval = self.spectrogram_time_interval
                self.spectro.cursor_color = "red"

                # color palette
                try:
                    self.spectro.spectro_color_map = matplotlib.pyplot.get_cmap(self.spectrogram_color_map)
                except ValueError:
                    self.spectro.spectro_color_map = matplotlib.pyplot.get_cmap("viridis")

                r = self.spectro.load_wav(str(wav_file_path))
                if "error" in r:
                    logging.warning(f"spectro_load_wav error: {r['error']}")
                    QMessageBox.warning(
                        self,
                        programName,
                        f"Error in spectrogram generation: {r['error']}",
                        QMessageBox.Ok | QMessageBox.Default,
                        QMessageBox.NoButton,
                    )
                    del self.spectro
                    return

                self.pj[OBSERVATIONS][self.observationId][VISUALIZE_SPECTROGRAM] = True
                self.spectro.sendEvent.connect(self.signal_from_widget)
                self.spectro.sb_freq_min.setValue(0)
                self.spectro.sb_freq_max.setValue(int(self.spectro.frame_rate / 2))
                self.spectro.show()

                self.plot_timer_out()

                if warning:
                    if self.playerType == VLC and self.playMode == MPV and not flag_paused:
                        self.play_video()

        if plot_type == "waveform":
            if hasattr(self, "waveform"):
                self.waveform.show()
            else:
                logging.debug("create waveform plot")

                # remember if player paused
                if warning:
                    if self.playerType == VLC and self.playMode == MPV:
                        flag_paused = self.is_playing()

                self.pause_video()

                if (warning and dialog.MessageDialog(
                        programName,
                    ("You choose to visualize the waveform during this observation.<br>"
                     "The waveform generation can take some time for long media, be patient"),
                    [YES, NO],
                ) == NO):
                    if self.playerType == VLC and self.playMode == MPV and not flag_paused:
                        self.play_video()
                    return

                self.generate_wav_file_from_media()

                tmp_dir = (self.ffmpeg_cache_dir
                           if self.ffmpeg_cache_dir and os.path.isdir(self.ffmpeg_cache_dir) else tempfile.gettempdir())

                wav_file_path = (
                    pathlib.Path(tmp_dir) /
                    pathlib.Path(self.dw_player[0].player.playlist[self.dw_player[0].player.playlist_pos]["filename"] +
                                 ".wav").name)

                self.waveform = plot_waveform_rt.Plot_waveform_RT()

                self.waveform.setWindowFlags(Qt.WindowStaysOnTopHint)
                self.waveform.setWindowFlags(self.waveform.windowFlags() & ~Qt.WindowMinimizeButtonHint)

                self.waveform.interval = self.spectrogram_time_interval
                self.waveform.cursor_color = "red"

                r = self.waveform.load_wav(str(wav_file_path))
                if "error" in r:
                    logging.warning(f"waveform_load_wav error: {r['error']}")
                    QMessageBox.warning(
                        self,
                        programName,
                        f"Error in waveform generation: {r['error']}",
                        QMessageBox.Ok | QMessageBox.Default,
                        QMessageBox.NoButton,
                    )
                    del self.waveform
                    return

                self.pj[OBSERVATIONS][self.observationId][VISUALIZE_WAVEFORM] = True
                self.waveform.sendEvent.connect(self.signal_from_widget)
                self.waveform.show()

                self.plot_timer.start()

                if warning:
                    if self.playerType == VLC and self.playMode == MPV and not flag_paused:
                        self.play_video()

        if plot_type == "plot_events":
            if hasattr(self, "plot_events"):
                self.plot_events.show()
            else:
                logging.debug("create plot events")

                try:
                    self.plot_events = plot_events_rt.Plot_events_RT()

                    self.plot_events.setWindowFlags(Qt.WindowStaysOnTopHint)
                    self.plot_events.setWindowFlags(self.plot_events.windowFlags() & ~Qt.WindowMinimizeButtonHint)

                    self.plot_events.groupby = "behaviors"
                    self.plot_events.interval = 60  # self.spectrogram_time_interval
                    self.plot_events.cursor_color = "red"
                    self.plot_events.observation_type = self.playerType

                    self.plot_events.point_event_plot_duration = POINT_EVENT_PLOT_DURATION
                    self.plot_events.point_event_plot_color = POINT_EVENT_PLOT_COLOR

                    self.plot_events.state_events_list = utilities.state_behavior_codes(self.pj[ETHOGRAM])

                    self.plot_events.events_list = self.pj[OBSERVATIONS][self.observationId][EVENTS]
                    self.plot_events.events = self.plot_events.aggregate_events(
                        self.pj[OBSERVATIONS][self.observationId][EVENTS], 0, 60)

                    # behavior colors
                    self.plot_events.behav_color = {}
                    for idx, behavior in enumerate(utilities.all_behaviors(self.pj[ETHOGRAM])):
                        self.plot_events.behav_color[behavior] = BEHAVIORS_PLOT_COLORS[idx]

                    self.plot_events.sendEvent.connect(self.signal_from_widget)

                    self.plot_events.show()

                    # self.plot_timer_out()
                    self.plot_timer.start()

                except Exception:
                    dialog.error_message2()

    def plot_timer_out(self):
        """
        timer for plot visualization: spectrogram, waveform, plot events
        """
        """
        if (VISUALIZE_SPECTROGRAM not in self.pj[OBSERVATIONS][self.observationId] or
                not self.pj[OBSERVATIONS][self.observationId][VISUALIZE_SPECTROGRAM]):
            return
        """
        """
        if self.playerType == LIVE:
            QMessageBox.warning(self, programName, "The sound signal visualization is not available for live observations")
            return
        """

        logging.debug(f"plot_timer_out")

        if hasattr(self, "plot_events"):

            if not self.plot_events.visibleRegion().isEmpty():
                self.plot_events.events_list = self.pj[OBSERVATIONS][self.observationId][EVENTS]
                self.plot_events.plot_events(float(self.getLaps()))

        if self.playerType == VLC:

            current_media_time = self.dw_player[0].player.time_pos

            tmp_dir = (self.ffmpeg_cache_dir
                       if self.ffmpeg_cache_dir and os.path.isdir(self.ffmpeg_cache_dir) else tempfile.gettempdir())

            try:
                wav_file_path = str(
                    pathlib.Path(tmp_dir) /
                    pathlib.Path(self.dw_player[0].player.playlist[self.dw_player[0].player.playlist_pos]["filename"] +
                                 ".wav").name)
            except TypeError:
                return

            # waveform
            if self.pj[OBSERVATIONS][self.observationId].get(VISUALIZE_WAVEFORM, False):

                if not hasattr(self, "waveform"):
                    return

                if not self.waveform.visibleRegion().isEmpty():

                    if self.waveform.wav_file_path == wav_file_path:
                        self.waveform.plot_waveform(current_media_time)
                    else:
                        r = self.waveform.load_wav(wav_file_path)
                        if "error" not in r:
                            self.waveform.plot_waveform(current_media_time)
                        else:
                            logging.warning("waveform_load_wav error: {}".format(r["error"]))

            # spectrogram
            if self.pj[OBSERVATIONS][self.observationId].get(VISUALIZE_SPECTROGRAM, False):

                if not hasattr(self, "spectro"):
                    return

                if not self.spectro.visibleRegion().isEmpty():

                    if self.spectro.wav_file_path == wav_file_path:
                        self.spectro.plot_spectro(current_media_time)
                    else:
                        r = self.spectro.load_wav(wav_file_path)
                        if "error" not in r:
                            self.spectro.plot_spectro(current_media_time)
                        else:
                            logging.warning("spectro_load_wav error: {}".format(r["error"]))

    def show_data_files(self):
        """
        show plot of data files (if any)
        """
        for idx in self.plot_data:
            self.plot_data[idx].show()

    def hide_data_files(self):
        """
        hide plot of data files (if any)
        """
        for idx in self.plot_data:
            self.plot_data[idx].hide()

    def modifiers_coding_map_creator(self):
        """
        show modifiers coding map creator window and hide program main window
        """
        self.mapCreatorWindow = map_creator.ModifiersMapCreatorWindow()
        self.mapCreatorWindow.move(self.pos())
        self.mapCreatorWindow.resize(CODING_MAP_RESIZE_W, CODING_MAP_RESIZE_H)
        self.mapCreatorWindow.show()

    def behaviors_coding_map_creator_signal_addtoproject(self, behav_coding_map):
        """
        add the behav coding map received from behav_coding_map_creator to current project

        Args:
            behav_coding_map (dict):
        """

        if not self.project:
            QMessageBox.warning(self, programName, "No project found", QMessageBox.Ok | QMessageBox.Default,
                                QMessageBox.NoButton)
            return

        if "behaviors_coding_map" not in self.pj:
            self.pj["behaviors_coding_map"] = []

        if [bcm for bcm in self.pj["behaviors_coding_map"] if bcm["name"] == behav_coding_map["name"]]:
            QMessageBox.critical(
                self,
                programName,
                ("The current project already contains a behaviors coding map "
                 f"with the same name (<b>{behav_coding_map['name']}</b>)"),
                QMessageBox.Ok | QMessageBox.Default,
                QMessageBox.NoButton,
            )
            return

        self.pj["behaviors_coding_map"].append(behav_coding_map)
        QMessageBox.information(
            self,
            programName,
            f"The behaviors coding map <b>{behav_coding_map['name']}</b> was added to current project",
        )
        self.projectChanged = True

    def behaviors_coding_map_creator(self):
        """
        show behaviors coding map creator window
        """

        if not self.project:
            QMessageBox.warning(self, programName, "No project found", QMessageBox.Ok | QMessageBox.Default,
                                QMessageBox.NoButton)
            return

        codes_list = []
        for key in self.pj[ETHOGRAM]:
            codes_list.append(self.pj[ETHOGRAM][key][BEHAVIOR_CODE])

        self.mapCreatorWindow = behav_coding_map_creator.BehaviorsMapCreatorWindow(codes_list)
        # behaviors coding map list
        self.mapCreatorWindow.bcm_list = [x["name"].upper() for x in self.pj.get(BEHAVIORS_CODING_MAP, [])]
        self.mapCreatorWindow.signal_add_to_project.connect(self.behaviors_coding_map_creator_signal_addtoproject)
        self.mapCreatorWindow.move(self.pos())
        self.mapCreatorWindow.resize(CODING_MAP_RESIZE_W, CODING_MAP_RESIZE_H)
        self.mapCreatorWindow.show()

    def load_observation(self, obsId, mode="start"):
        """
        load observation obsId

        Args:
            obsId (str): observation id
            mode (str): "start" to start observation
                        "view"  to view observation
        """

        if obsId in self.pj[OBSERVATIONS]:

            self.observationId = obsId
            self.loadEventsInTW(self.observationId)

            if self.pj[OBSERVATIONS][self.observationId][TYPE] == LIVE:
                if mode == "start":
                    self.playerType = LIVE
                    self.initialize_new_live_observation()
                if mode == "view":
                    self.playerType = VIEWER
                    self.playMode = ""
                    self.dwObservations.setVisible(True)

            if self.pj[OBSERVATIONS][self.observationId][TYPE] in [MEDIA]:

                if mode == "start":
                    if not self.initialize_new_observation_mpv():
                        self.observationId = ""
                        self.twEvents.setRowCount(0)
                        menu_options.update_menu(self)
                        return "Error: loading observation problem"

                if mode == "view":
                    self.playerType = VIEWER
                    self.playMode = ""
                    self.dwObservations.setVisible(True)

            menu_options.update_menu(self)
            # title of dock widget  “  ”
            self.dwObservations.setWindowTitle(f"Events for “{self.observationId}” observation")
            return ""

        else:
            return "Error: Observation not found"

    def open_observation(self, mode):
        """
        start or view an observation

        Args:
            mode (str): "start" to start observation
                        "view" to view observation
        """

        # check if current observation must be closed to open a new one
        if self.observationId:

            self.hide_data_files()
            response = dialog.MessageDialog(programName,
                                            "The current observation will be closed. Do you want to continue?",
                                            [YES, NO])
            if response == NO:
                self.show_data_files()
                return ""
            else:
                self.close_observation()

        if mode == "start":
            result, selectedObs = self.selectObservations(OPEN)
        if mode == VIEW:
            result, selectedObs = self.selectObservations(VIEW)

        if selectedObs:
            return self.load_observation(selectedObs[0], mode)
        else:
            return ""

    def edit_observation(self):
        """
        edit observation
        """

        # check if current observation must be closed to open a new one
        if self.observationId:
            # hide data plot
            self.hide_data_files()
            if (dialog.MessageDialog(programName, "The current observation will be closed. Do you want to continue?",
                                     [YES, NO]) == NO):
                # restore plots
                self.show_data_files()
                return
            else:
                self.close_observation()

        result, selected_observations = self.selectObservations(EDIT)

        if selected_observations:
            self.new_observation(mode=EDIT, obsId=selected_observations[0])

    def observations_list(self):
        """
        show list of all observations of current project
        """

        if self.playerType == VIEWER:
            self.close_observation()

        result, selected_obs = self.selectObservations(SINGLE)

        if selected_obs:
            if result in [OPEN, VIEW, EDIT] and self.observationId:
                self.close_observation()
            if result == OPEN:
                self.load_observation(selected_obs[0], "start")
            if result == VIEW:
                self.load_observation(selected_obs[0], VIEW)
            if result == EDIT:
                if self.observationId != selected_obs[0]:
                    self.new_observation(mode=EDIT, obsId=selected_obs[0])  # observation id to edit
                else:
                    QMessageBox.warning(
                        self,
                        programName,
                        (f"The observation <b>{self.observationId}</b> is running!<br>"
                         "Close it before editing."),
                    )

    def actionCheckUpdate_activated(self, flagMsgOnlyIfNew=False):
        """
        check BORIS web site for updates
        """

        try:
            versionURL = "http://www.boris.unito.it/static/ver4.dat"
            lastVersion = urllib.request.urlopen(versionURL).read().strip().decode("utf-8")
            if versiontuple(lastVersion) > versiontuple(__version__):
                msg = (f"A new version is available: v. <b>{lastVersion}</b><br>"
                       'Go to <a href="http://www.boris.unito.it">'
                       "http://www.boris.unito.it</a> to install it.")
            else:
                msg = f"The version you are using is the last one: <b>{__version__}</b>"
            newsURL = "http://www.boris.unito.it/static/news.dat"
            news = urllib.request.urlopen(newsURL).read().strip().decode("utf-8")
            config_file.save(self, lastCheckForNewVersion=int(time.mktime(time.localtime())))
            QMessageBox.information(self, programName, msg)
            if news:
                QMessageBox.information(self, programName, news)
        except Exception:
            QMessageBox.warning(self, programName, "Can not check for updates...")

    def seek_mediaplayer(self, new_time: int, player=0):
        """
        change media position in player

        Args:
            new_time (int): time in seconds

        """
        flag_paused = self.is_playing()

        logging.debug(f"paused? {flag_paused}")

        if self.dw_player[player].player.playlist_count == 1:

            if new_time < self.dw_player[player].player.duration:

                self.dw_player[player].player.seek(new_time, "absolute+exact")

                if player == 0 and not self.user_move_slider:
                    try:
                        self.video_slider.setValue(self.dw_player[0].player.time_pos /
                                                   self.dw_player[0].player.duration * (slider_maximum - 1))
                    except Exception:
                        pass
            else:
                pass

        elif self.dw_player[player].player.playlist_count > 1:

            if new_time < sum(self.dw_player[player].media_durations) / 1000:
                # remember if player paused (go previous will start playing)
                flagPaused = self.is_playing()

                tot = 0
                for idx, d in enumerate(self.dw_player[player].media_durations):
                    """if new_time >= tot and new_time < tot + d / 1000:"""
                    if tot <= new_time < tot + d / 1000:

                        if idx == self.dw_player[player].player.playlist_pos + 1:
                            self.dw_player[player].player.playlist_next()
                            time.sleep(1)
                        if idx == self.dw_player[player].player.playlist_pos - 1:
                            self.dw_player[player].player.playlist_prev()
                            time.sleep(1)

                        self.dw_player[player].player.seek(
                            round(
                                float(new_time) -
                                sum(self.dw_player[player].media_durations[0:self.dw_player[player].player.playlist_pos]
                                   ) / 1000,
                                3,
                            ),
                            "absolute+exact",
                        )

                        break
                    tot += d / 1000

                if player == 0 and not self.user_move_slider:
                    try:
                        self.video_slider.setValue(self.dw_player[0].player.time_pos /
                                                   self.dw_player[0].player.duration * (slider_maximum - 1))
                    except Exception:
                        pass
                        # dialog.error_message2()

            else:
                QMessageBox.warning(
                    self,
                    programName,
                    ("The indicated position is behind the total media duration "
                     f"({seconds2time(sum(self.dw_player[player].media_durations))})"),
                )

    def jump_to(self):
        """
        jump to the user specified media position
        """

        jt = dialog.Ask_time(self.timeFormat)
        jt.setWindowTitle("Jump to specific time")
        jt.time_widget.set_time(0)

        if jt.exec_():
            new_time = int(jt.time_widget.get_time())
            if new_time < 0:
                return

            if self.playerType == VLC:

                if self.playMode == MPV:  # play mode VLC

                    self.seek_mediaplayer(new_time)

                    self.update_visualizations()

    def previous_media_file(self):
        """
        go to previous media file (if any)
        """
        if len(self.pj[OBSERVATIONS][self.observationId][FILE][PLAYER1]) == 1:
            return

        if self.playerType == VLC:

            if self.playMode == MPV:
                # check if media not first media
                if self.dw_player[0].player.playlist_pos > 0:
                    flagPaused = self.is_playing()
                    self.dw_player[0].player.playlist_prev()

                elif self.dw_player[0].player.playlist_count == 1:
                    self.statusbar.showMessage("There is only one media file", 5000)

            if hasattr(self, "spectro"):
                self.spectro.memChunk = -1

    def next_media_file(self):
        """
        go to next media file (if any) in first player
        """

        if len(self.pj[OBSERVATIONS][self.observationId][FILE][PLAYER1]) == 1:
            return

        if self.playerType == VLC:

            # check if media not last media
            if self.dw_player[0].player.playlist_pos < self.dw_player[0].player.playlist_count - 1:

                # remember if player paused (go previous will start playing)
                flagPaused = self.is_playing()

                self.dw_player[0].player.playlist_next()

            else:
                if self.dw_player[0].player.playlist_count == 1:
                    self.statusbar.showMessage("There is only one media file", 5000)

            self.update_visualizations()

            if hasattr(self, "spectro"):
                self.spectro.memChunk = -1

    def set_volume(self, nplayer, new_volume):
        """
        set volume for player nplayer

        Args:
            nplayer (str): player to set
            new_volume (int): volume to set
        """

        logging.debug(f"set volume to {new_volume}")
        self.dw_player[nplayer].player.volume = new_volume

    def automatic_backup(self):
        """
        save project every x minutes if observation is running
        and if the project file name is defined
        """

        if self.observationId and self.projectFileName:

            logging.info("autosave project")

            self.save_project_activated()
        else:
            logging.debug((f"project not autosaved: "
                           f"observation id: {self.observationId} "
                           f"project file name: {self.projectFileName}"))

    def update_subject(self, subject):
        """
        update the current subject

        Args:
            subject (str): subject
        """
        try:
            if (not subject) or (subject == NO_FOCAL_SUBJECT) or (self.currentSubject == subject):
                self.currentSubject = ""
                self.lbFocalSubject.setText(NO_FOCAL_SUBJECT)
            else:
                self.currentSubject = subject
                self.lbFocalSubject.setText(f" Focal subject: <b>{self.currentSubject}</b>")

        except Exception:
            logging.critical("error in update_subject function")

    def getCurrentMediaByFrame(self, player: str, requiredFrame: int, fps: float):
        """
        Args:
            player (str): player
            requiredFrame (int): required frame
            fps (float): FPS

        returns:
            currentMedia
            frameCurrentMedia
        """
        currentMedia, frameCurrentMedia = "", 0
        frameMs = 1000 / fps
        for idx, media in enumerate(self.pj[OBSERVATIONS][self.observationId][FILE][player]):
            if requiredFrame * frameMs < sum(self.dw_player[int(player) - 1].media_durations[0:idx + 1]):
                currentMedia = media
                frameCurrentMedia = (requiredFrame -
                                     sum(self.dw_player[int(player) - 1].media_durations[0:idx]) / frameMs)
                break
        return currentMedia, round(frameCurrentMedia)

    def redraw_measurements(self):
        """
        redraw measurements from previous frames
        """
        for idx, dw in enumerate(self.dw_player):
            if hasattr(self, "measurement_w") and self.measurement_w is not None and self.measurement_w.isVisible():
                if self.measurement_w.cbPersistentMeasurements.isChecked():

                    logging.debug("Redraw measurements")

                    for frame in self.measurement_w.draw_mem:

                        if frame == dw.player.estimated_frame_number + 1:
                            elementsColor = ACTIVE_MEASUREMENTS_COLOR
                        else:
                            elementsColor = PASSIVE_MEASUREMENTS_COLOR

                        for element in self.measurement_w.draw_mem[frame]:
                            if element[0] == idx:
                                if element[1] == "point":
                                    x, y = element[2:]
                                    geometric_measurement.draw_point(self, x, y, elementsColor, n_player=idx)

                                if element[1] == "line":
                                    x1, y1, x2, y2 = element[2:]
                                    geometric_measurement.draw_line(self, x1, y1, x2, y2, elementsColor, n_player=idx)
                                    geometric_measurement.draw_point(self, x1, y1, elementsColor, n_player=idx)
                                    geometric_measurement.draw_point(self, x2, y2, elementsColor, n_player=idx)
                                if element[1] == "angle":
                                    x1, y1 = element[2][0]
                                    x2, y2 = element[2][1]
                                    x3, y3 = element[2][2]
                                    geometric_measurement.draw_line(self, x1, y1, x2, y2, elementsColor, n_player=idx)
                                    geometric_measurement.draw_line(self, x1, y1, x3, y3, elementsColor, n_player=idx)
                                    geometric_measurement.draw_point(self, x1, y1, elementsColor, n_player=idx)
                                    geometric_measurement.draw_point(self, x2, y2, elementsColor, n_player=idx)
                                    geometric_measurement.draw_point(self, x3, y3, elementsColor, n_player=idx)
                                if element[1] == "polygon":
                                    polygon = QPolygon()
                                    for point in element[2]:
                                        polygon.append(QPoint(point[0], point[1]))
                                    painter = QPainter()
                                    painter.begin(self.dw_player[idx].frame_viewer.pixmap())
                                    painter.setPen(QColor(elementsColor))
                                    painter.drawPolygon(polygon)
                                    painter.end()
                                    dw.frame_viewer.update()
                else:
                    self.measurement_w.draw_mem = []

    def extract_frame(self, dw):
        """
        extract frame from video and visualize it in frame_viewer
        """
        qim = ImageQt(dw.player.screenshot_raw())
        pixmap = QPixmap.fromImage(qim)
        dw.frame_viewer.setPixmap(pixmap.scaled(dw.frame_viewer.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def frame_image_clicked(self, n_player, event):
        geometric_measurement.image_clicked(self, n_player, event)

    def initialize_new_observation_mpv(self):
        """
        initialize new observation for MPV
        """

        logging.debug("function: initialize new observation for MPV")

        ok, msg = project_functions.check_if_media_available(self.pj[OBSERVATIONS][self.observationId],
                                                             self.projectFileName)

        for dw in [self.dwEthogram, self.dwSubjects, self.dwObservations]:
            dw.setVisible(True)

        if not ok:
            QMessageBox.critical(
                self,
                programName,
                (f"{msg}<br><br>The observation will be opened in VIEW mode.<br>"
                 "It will not be possible to log events.<br>"
                 "Modify the media path to point an existing media file "
                 "to log events or copy media file in the BORIS project directory."),
                QMessageBox.Ok | QMessageBox.Default,
                QMessageBox.NoButton,
            )
            self.playerType = VIEWER
            self.playMode = ""
            return True

        self.playerType, self.playMode = VLC, MPV
        self.fps = 0

        self.w_obs_info.setVisible(True)
        self.w_live.setVisible(False)

        font = QFont()
        font.setPointSize(15)
        self.lb_current_media_time.setFont(font)

        # initialize video slider
        self.video_slider = QSlider(QtCore.Qt.Horizontal, self)
        self.video_slider.setFocusPolicy(Qt.NoFocus)
        self.video_slider.setMaximum(slider_maximum)
        self.video_slider.sliderMoved.connect(self.video_slider_sliderMoved)
        self.video_slider.sliderReleased.connect(self.video_slider_sliderReleased)
        self.verticalLayout_3.addWidget(self.video_slider)

        # add all media files to media lists
        self.setDockOptions(QMainWindow.AnimatedDocks | QMainWindow.AllowNestedDocks)
        self.dw_player = []
        # create dock widgets for players

        self.time_observer_signal.connect(self.timer_out2)

        for i in range(N_PLAYER):
            n_player = str(i + 1)
            if (n_player not in self.pj[OBSERVATIONS][self.observationId][FILE] or
                    not self.pj[OBSERVATIONS][self.observationId][FILE][n_player]):
                continue

            if i == 0:  # first player
                p = player_dock_widget.DW2(i)
                self.dw_player.append(p)

                @p.player.property_observer("time-pos")
                def time_observer(_name, value):
                    if value is not None:
                        self.time_observer_signal.emit(value)

            else:
                self.dw_player.append(player_dock_widget.DW2(i))
            self.dw_player[-1].setFloating(False)
            self.dw_player[-1].setVisible(False)
            self.dw_player[-1].setFeatures(QDockWidget.DockWidgetFloatable | QDockWidget.DockWidgetMovable)

            # place 4 players at the top of the main window and 4 at the bottom
            self.addDockWidget(Qt.TopDockWidgetArea if i < 4 else Qt.BottomDockWidgetArea, self.dw_player[-1])

            self.dw_player[i].setVisible(True)

            # for receiving mouse event from frame viewer
            """
            self.dw_player[i].frame_viewer.mouse_pressed_signal.connect(
                lambda: geometric_measurement.image_clicked(self, n_player, event)
            )
            """
            self.dw_player[i].frame_viewer.mouse_pressed_signal.connect(self.frame_image_clicked)

            # for receiving key event from dock widget
            self.dw_player[i].key_pressed_signal.connect(self.signal_from_widget)
            # for receiving event from volume slider
            self.dw_player[i].volume_slider_moved_signal.connect(self.set_volume)
            # for receiving resize event from dock widget
            self.dw_player[i].resize_signal.connect(self.resize_dw)
            """
            # for receiving event resize and clicked (Zoom - crop)
            self.dw_player[i].view_signal.connect(self.signal_from_dw)
            """

            # add durations list
            self.dw_player[i].media_durations = []
            # add fps list
            self.dw_player[i].fps = {}

            for mediaFile in self.pj[OBSERVATIONS][self.observationId][FILE][n_player]:

                logging.debug(f"media file: {mediaFile}")

                media_full_path = project_functions.media_full_path(mediaFile, self.projectFileName)

                logging.debug(f"media_full_path: {media_full_path}")

                # media duration
                try:
                    mediaLength = self.pj[OBSERVATIONS][self.observationId][MEDIA_INFO][LENGTH][mediaFile] * 1000
                    mediaFPS = self.pj[OBSERVATIONS][self.observationId][MEDIA_INFO][FPS][mediaFile]
                except Exception:

                    logging.debug("media_info key not found")

                    r = utilities.accurate_media_analysis(self.ffmpeg_bin, media_full_path)
                    if "error" not in r:
                        if MEDIA_INFO not in self.pj[OBSERVATIONS][self.observationId]:
                            self.pj[OBSERVATIONS][self.observationId][MEDIA_INFO] = {LENGTH: {}, FPS: {}}
                            if LENGTH not in self.pj[OBSERVATIONS][self.observationId][MEDIA_INFO]:
                                self.pj[OBSERVATIONS][self.observationId][MEDIA_INFO][LENGTH] = {}
                            if FPS not in self.pj[OBSERVATIONS][self.observationId][MEDIA_INFO]:
                                self.pj[OBSERVATIONS][self.observationId][MEDIA_INFO][FPS] = {}

                        self.pj[OBSERVATIONS][self.observationId][MEDIA_INFO][LENGTH][mediaFile] = r["duration"]
                        self.pj[OBSERVATIONS][self.observationId][MEDIA_INFO][FPS][mediaFile] = r["fps"]

                        mediaLength = r["duration"] * 1000
                        mediaFPS = r["fps"]

                        self.projectChanged = True

                self.dw_player[i].media_durations.append(int(mediaLength))
                self.dw_player[i].fps[mediaFile] = mediaFPS

                self.dw_player[i].player.playlist_append(media_full_path)
                # self.dw_player[i].player.loadfile(media_full_path)
                # self.dw_player[i].player.pause = True

            self.dw_player[i].player.hwdec = "auto-safe"
            self.dw_player[i].player.playlist_pos = 0
            self.dw_player[i].player.wait_until_playing()
            self.dw_player[i].player.pause = True
            self.dw_player[i].player.wait_until_paused()
            self.dw_player[i].player.seek(0, "absolute")
            # do not close when playing finished
            self.dw_player[i].player.keep_open = True
            self.dw_player[i].player.keep_open_pause = False

            # position media
            if OBSERVATION_TIME_INTERVAL in self.pj[OBSERVATIONS][self.observationId]:
                self.seek_mediaplayer(int(self.pj[OBSERVATIONS][self.observationId][OBSERVATION_TIME_INTERVAL][0]),
                                      player=i)

            # restore zoom level
            if ZOOM_LEVEL in self.pj[OBSERVATIONS][self.observationId][MEDIA_INFO]:
                self.dw_player[i].player.video_zoom = log2(
                    self.pj[OBSERVATIONS][self.observationId][MEDIA_INFO][ZOOM_LEVEL].get(n_player, 0))

            # restore subtitle visibility
            if DISPLAY_MEDIA_SUBTITLES in self.pj[OBSERVATIONS][self.observationId][MEDIA_INFO]:
                self.dw_player[i].player.sub_visibility = self.pj[OBSERVATIONS][
                    self.observationId][MEDIA_INFO][DISPLAY_MEDIA_SUBTITLES].get(n_player, True)

            # restore overlays
            if OVERLAY in self.pj[OBSERVATIONS][self.observationId][MEDIA_INFO]:
                if n_player in self.pj[OBSERVATIONS][self.observationId][MEDIA_INFO][OVERLAY]:
                    self.overlays[i] = self.dw_player[i].player.create_image_overlay()
                    self.resize_dw(i)

        menu_options.update_menu(self)

        self.actionPlay.setIcon(QIcon(":/play"))

        self.display_statusbar_info(self.observationId)

        self.memMedia, self.currentSubject = "", ""

        self.lbSpeed.setText(f"Player rate: x{self.play_rate:.3f}")

        # spectrogram
        if (VISUALIZE_SPECTROGRAM in self.pj[OBSERVATIONS][self.observationId] and
                self.pj[OBSERVATIONS][self.observationId][VISUALIZE_SPECTROGRAM]):

            tmp_dir = (self.ffmpeg_cache_dir
                       if self.ffmpeg_cache_dir and os.path.isdir(self.ffmpeg_cache_dir) else tempfile.gettempdir())

            wav_file_path = (
                pathlib.Path(tmp_dir) /
                pathlib.Path(self.dw_player[0].player.playlist[self.dw_player[0].player.playlist_pos]["filename"] +
                             ".wav").name)

            if not wav_file_path.is_file():
                self.generate_wav_file_from_media()

            self.show_plot_widget("spectrogram", warning=False)

        # waveform
        if (VISUALIZE_WAVEFORM in self.pj[OBSERVATIONS][self.observationId] and
                self.pj[OBSERVATIONS][self.observationId][VISUALIZE_WAVEFORM]):

            tmp_dir = (self.ffmpeg_cache_dir
                       if self.ffmpeg_cache_dir and os.path.isdir(self.ffmpeg_cache_dir) else tempfile.gettempdir())

            wav_file_path = (
                pathlib.Path(tmp_dir) /
                pathlib.Path(self.dw_player[0].player.playlist[self.dw_player[0].player.playlist_pos]["filename"] +
                             ".wav").name)

            if not wav_file_path.is_file():
                self.generate_wav_file_from_media()

            self.show_plot_widget("waveform", warning=False)

        # external data plot
        if (PLOT_DATA in self.pj[OBSERVATIONS][self.observationId] and
                self.pj[OBSERVATIONS][self.observationId][PLOT_DATA]):

            self.plot_data = {}
            self.ext_data_timer_list = []
            count = 0
            for idx in self.pj[OBSERVATIONS][self.observationId][PLOT_DATA]:
                if count == 0:

                    data_file_path = project_functions.media_full_path(
                        self.pj[OBSERVATIONS][self.observationId][PLOT_DATA][idx]["file_path"], self.projectFileName)
                    if not data_file_path:
                        QMessageBox.critical(
                            self,
                            programName,
                            "Data file not found:\n{}".format(
                                self.pj[OBSERVATIONS][self.observationId][PLOT_DATA][idx]["file_path"]),
                        )
                        return False

                    w1 = plot_data_module.Plot_data(
                        data_file_path,
                        int(self.pj[OBSERVATIONS][self.observationId][PLOT_DATA][idx]["time_interval"]),
                        str(self.pj[OBSERVATIONS][self.observationId][PLOT_DATA][idx]["time_offset"]),
                        self.pj[OBSERVATIONS][self.observationId][PLOT_DATA][idx]["color"],
                        self.pj[OBSERVATIONS][self.observationId][PLOT_DATA][idx]["title"],
                        self.pj[OBSERVATIONS][self.observationId][PLOT_DATA][idx]["variable_name"],
                        self.pj[OBSERVATIONS][self.observationId][PLOT_DATA][idx]["columns"],
                        self.pj[OBSERVATIONS][self.observationId][PLOT_DATA][idx]["substract_first_value"],
                        self.pj[CONVERTERS] if CONVERTERS in self.pj else {},
                        self.pj[OBSERVATIONS][self.observationId][PLOT_DATA][idx]["converters"],
                        log_level=logging.getLogger().getEffectiveLevel(),
                    )

                    if w1.error_msg:
                        QMessageBox.critical(
                            self,
                            programName,
                            (f"Impossible to plot data from file {os.path.basename(self.pj[OBSERVATIONS][self.observationId][PLOT_DATA][idx]['file_path'])}:\n"
                             f"{w1.error_msg}"),
                        )
                        del w1
                        return False

                    w1.setWindowFlags(Qt.WindowStaysOnTopHint)
                    w1.sendEvent.connect(self.signal_from_widget)  # keypress event

                    w1.show()

                    self.ext_data_timer_list.append(QTimer())
                    self.ext_data_timer_list[-1].setInterval(w1.time_out)
                    self.ext_data_timer_list[-1].timeout.connect(lambda: self.timer_plot_data_out(w1))
                    self.timer_plot_data_out(w1)

                    self.plot_data[count] = w1

                if count == 1:

                    data_file_path = project_functions.media_full_path(
                        self.pj[OBSERVATIONS][self.observationId][PLOT_DATA][idx]["file_path"], self.projectFileName)
                    if not data_file_path:
                        QMessageBox.critical(
                            self,
                            programName,
                            "Data file not found:\n{}".format(
                                self.pj[OBSERVATIONS][self.observationId][PLOT_DATA][idx]["file_path"]),
                        )
                        return False

                    w2 = plot_data_module.Plot_data(
                        data_file_path,
                        int(self.pj[OBSERVATIONS][self.observationId][PLOT_DATA][idx]["time_interval"]),
                        str(self.pj[OBSERVATIONS][self.observationId][PLOT_DATA][idx]["time_offset"]),
                        self.pj[OBSERVATIONS][self.observationId][PLOT_DATA][idx]["color"],
                        self.pj[OBSERVATIONS][self.observationId][PLOT_DATA][idx]["title"],
                        self.pj[OBSERVATIONS][self.observationId][PLOT_DATA][idx]["variable_name"],
                        self.pj[OBSERVATIONS][self.observationId][PLOT_DATA][idx]["columns"],
                        self.pj[OBSERVATIONS][self.observationId][PLOT_DATA][idx]["substract_first_value"],
                        self.pj[CONVERTERS] if CONVERTERS in self.pj else {},
                        self.pj[OBSERVATIONS][self.observationId][PLOT_DATA][idx]["converters"],
                        log_level=logging.getLogger().getEffectiveLevel(),
                    )

                    if w2.error_msg:
                        QMessageBox.critical(
                            self,
                            programName,
                            "Impossible to plot data from file {}:\n{}".format(
                                os.path.basename(
                                    self.pj[OBSERVATIONS][self.observationId][PLOT_DATA][idx]["file_path"]),
                                w2.error_msg,
                            ),
                        )
                        del w2
                        return False

                    w2.setWindowFlags(Qt.WindowStaysOnTopHint)
                    w2.sendEvent.connect(self.signal_from_widget)

                    w2.show()
                    self.ext_data_timer_list.append(QTimer())
                    self.ext_data_timer_list[-1].setInterval(w2.time_out)
                    self.ext_data_timer_list[-1].timeout.connect(lambda: self.timer_plot_data_out(w2))
                    self.timer_plot_data_out(w2)

                    self.plot_data[count] = w2

                count += 1

        # check if "filtered behaviors"
        if FILTERED_BEHAVIORS in self.pj[OBSERVATIONS][self.observationId]:
            self.load_behaviors_in_twEthogram(self.pj[OBSERVATIONS][self.observationId][FILTERED_BEHAVIORS])

        # restore windows state: dockwidget positions ...
        if self.saved_state is None:
            self.saved_state = self.saveState()
            self.restoreState(self.saved_state)
        else:
            try:
                self.restoreState(self.saved_state)
            except TypeError:
                logging.critical("state not restored: Type error")
                self.saved_state = self.saveState()
                self.restoreState(self.saved_state)

        for player in self.dw_player:
            player.setVisible(True)

        # inital synchro
        for n_player in range(1, len(self.dw_player)):
            self.sync_time(n_player, 0)

        return True

    def timer_plot_data_out(self, w):
        """
        update plot in w (Plot_data class)
        triggered by timers in self.ext_data_timer_list
        """
        w.update_plot(self.getLaps())

    def signal_from_widget(self, event):
        """
        receive signal from widget
        """
        self.keyPressEvent(event)

    def resize_dw(self, dw_id):
        """
        dockwidget was resized. Adpat overlay if any
        """
        try:
            img = Image.open(self.pj[OBSERVATIONS][self.observationId][MEDIA_INFO][OVERLAY][str(dw_id +
                                                                                                1)]["file name"])
        except:
            return

        w = self.dw_player[dw_id].player.width
        h = self.dw_player[dw_id].player.height

        fw = self.dw_player[dw_id].videoframe.size().width()
        fh = self.dw_player[dw_id].videoframe.size().height()

        if fw / fh <= w / h:
            w_r = fw
            h_r = w_r / (w / h)
            x1 = 0
            y1 = int((fh - h_r) / 2)
            x2 = int(w_r)
            y2 = int(y1 + h_r)

        if fw / fh > w / h:
            h_r = fh
            w_r = h_r * (w / h)
            x1 = int((fw - w_r) / 2)
            y1 = 0
            x2 = int(x1 + w_r)
            y2 = int(h_r)

        img_resized = img.resize((x2 - x1, y2 - y1))
        # disabled due to a problem setting trasnparency to 0% with an image with transparent background
        # and img_resized.putalpha(int((100 - self.pj[OBSERVATIONS][self.observationId][MEDIA_INFO][OVERLAY][str(dw_id + 1)]["transparency"]) * 2.55))  # 0 means 100% transparency

        # check position
        x_offset, y_offset = 0, 0
        if self.pj[OBSERVATIONS][self.observationId][MEDIA_INFO][OVERLAY][str(dw_id + 1)]["overlay position"]:
            try:
                x_offset = int(self.pj[OBSERVATIONS][self.observationId][MEDIA_INFO][OVERLAY][str(dw_id + 1)]
                               ["overlay position"].split(",")[0].strip())
                y_offset = int(self.pj[OBSERVATIONS][self.observationId][MEDIA_INFO][OVERLAY][str(dw_id + 1)]
                               ["overlay position"].split(",")[1].strip())
            except Exception:
                logging.warning(f"error in overlay position")

        try:
            self.overlays[dw_id].remove()
        except:
            logging.debug("error removing overlay")
        try:
            self.overlays[dw_id].update(img_resized, pos=(x1 + x_offset, y1 + y_offset))
        except:
            logging.debug("error updating overlay")

    def signal_from_dw(self, id_, msg, button):
        """
        receive signal from dock widget: clicked or resized
        """
        return  # function disabled

        if msg == "clicked_out_of_video":
            self.dw_player[id_].mediaplayer.video_set_crop_geometry(None)
            self.dw_player[id_].zoomed = False

            return

        x_center = self.dw_player[id_].videoframe.x_click
        y_center = self.dw_player[id_].videoframe.y_click

        fw = self.dw_player[id_].videoframe.geometry().width()
        fh = self.dw_player[id_].videoframe.geometry().height()

        left = int(x_center - fw / 2)
        top = int(y_center - fh / 2)

        right = left + fw
        bottom = top + fh

        if msg == "clicked" and button == Qt.LeftButton:
            if not self.dw_player[id_].zoomed:
                self.dw_player[id_].mediaplayer.video_set_crop_geometry(f"{right}x{bottom}+{left}+{top}")
                self.dw_player[id_].zoomed = True
            else:
                self.dw_player[id_].mediaplayer.video_set_crop_geometry(None)
                self.dw_player[id_].zoomed = False

        elif msg == "resized":

            if self.dw_player[id_].zoomed:
                self.dw_player[id_].mediaplayer.video_set_crop_geometry(f"{right}x{bottom}+{left}+{top}")

    ''' 2019-12-12
    def eventFilter(self, source, event):
        """
        send event from widget to mainwindow
        """

        #logging.debug("event filter {}".format(event.type()))


        if event.type() == QtCore.QEvent.KeyPress:
            key = event.key()
            if key in [Qt.Key_Up, Qt.Key_Down, Qt.Key_Left, Qt.Key_Right, Qt.Key_PageDown, Qt.Key_PageUp]:
                self.keyPressEvent(event)

        return QMainWindow.eventFilter(self, source, event)
    '''

    def loadEventsInTW(self, obs_id):
        """
        load events in table widget and update START/STOP

        if self.filtered_behaviors is populated and event not in self.filtered_behaviors then the event is not shown
        if self.filtered_subjects is populated and event not in self.filtered_subjects then the event is not shown

        Args:
            obsId (str): observation to load
        """

        logging.debug("begin load events from obs: {}".format(obs_id))

        self.twEvents.setRowCount(len(self.pj[OBSERVATIONS][obs_id][EVENTS]))
        if self.filtered_behaviors or self.filtered_subjects:
            self.twEvents.setRowCount(0)
        row = 0

        for event in self.pj[OBSERVATIONS][obs_id][EVENTS]:

            if self.filtered_behaviors and event[pj_obs_fields["code"]] not in self.filtered_behaviors:
                continue

            if self.filtered_subjects and event[pj_obs_fields["subject"]] not in self.filtered_subjects:
                continue

            if self.filtered_behaviors or self.filtered_subjects:
                self.twEvents.insertRow(self.twEvents.rowCount())

            for field_type in tw_events_fields:

                if field_type in pj_events_fields:

                    field = event[pj_obs_fields[field_type]]
                    if field_type == "time":
                        field = str(self.convertTime(field))

                    self.twEvents.setItem(row, tw_obs_fields[field_type], QTableWidgetItem(field))

                else:
                    self.twEvents.setItem(row, tw_obs_fields[field_type], QTableWidgetItem(""))

            row += 1

        self.update_events_start_stop()

        logging.debug("end load events from obs")

    def selectObservations(self, mode, windows_title=""):
        """
        show observations list window
        mode: accepted values: OPEN, EDIT, SINGLE, MULTIPLE, SELECT1
        """
        result_str, selected_obs = select_observations.select_observations(self.pj, mode, windows_title=windows_title)

        return result_str, selected_obs

    def initialize_new_live_observation(self):
        """
        initialize a new live observation
        """
        logging.debug(f"function: initialize new live obs: {self.observationId}")

        self.playerType, self.playMode = LIVE, LIVE

        self.w_live.setVisible(True)

        self.pb_live_obs.setMinimumHeight(60)

        # font = QFont("Monospace")
        font = QFont()
        font.setPointSize(48)
        self.lb_current_media_time.setFont(font)

        self.dwObservations.setVisible(True)

        self.w_obs_info.setVisible(True)

        menu_options.update_menu(self)

        self.liveObservationStarted = False
        self.pb_live_obs.setText("Start live observation")

        if self.pj[OBSERVATIONS][self.observationId].get(START_FROM_CURRENT_TIME, False):
            current_time = utilities.seconds_of_day(datetime.datetime.now())
        elif self.pj[OBSERVATIONS][self.observationId].get(START_FROM_CURRENT_EPOCH_TIME, False):
            current_time = time.mktime(datetime.datetime.now().timetuple())
        else:
            current_time = 0

        self.lb_current_media_time.setText(self.convertTime(current_time))

        # display observation time interval (if any)
        self.lb_obs_time_interval.setVisible(True)
        self.display_statusbar_info(self.observationId)
        """
        if self.timeFormat == HHMMSS:

            if self.pj[OBSERVATIONS][self.observationId].get(START_FROM_CURRENT_TIME, False):
                self.lb_current_media_time.setText(datetime.datetime.now().isoformat(" ").split(" ")[1][:12])
            else:
                self.lb_current_media_time.setText("00:00:00.000")

        if self.timeFormat == S:
            self.lb_current_media_time.setText("0.000")
        """

        self.lbCurrentStates.setText("")

        self.liveStartTime = None
        self.liveTimer.stop()

        # restore windows state: dockwidget positions ...
        if self.saved_state is None:
            self.saved_state = self.saveState()
            self.restoreState(self.saved_state)
        else:
            self.restoreState(self.saved_state)

    def new_observation_triggered(self):
        self.new_observation(mode=NEW, obsId="")

    def new_observation(self, mode=NEW, obsId=""):
        """
        define a new observation or edit an existing observation
        """
        # check if current observation must be closed to create a new one
        if mode == NEW and self.observationId:
            # hide data plot
            self.hide_data_files()
            if (dialog.MessageDialog(programName, "The current observation will be closed. Do you want to continue?",
                                     [YES, NO]) == NO):

                # show data plot
                self.show_data_files()
                return
            else:
                self.close_observation()

        observationWindow = observation.Observation(
            tmp_dir=self.ffmpeg_cache_dir if
            (self.ffmpeg_cache_dir and os.path.isdir(self.ffmpeg_cache_dir)) else tempfile.gettempdir(),
            project_path=self.projectFileName,
            converters=self.pj[CONVERTERS] if CONVERTERS in self.pj else {},
            time_format=self.timeFormat,
        )

        observationWindow.pj = dict(self.pj)
        observationWindow.mode = mode
        observationWindow.mem_obs_id = obsId
        observationWindow.chunk_length = self.chunk_length
        observationWindow.dteDate.setDateTime(QDateTime.currentDateTime())
        observationWindow.ffmpeg_bin = self.ffmpeg_bin
        observationWindow.project_file_name = self.projectFileName

        # add independent variables
        if INDEPENDENT_VARIABLES in self.pj:

            observationWindow.twIndepVariables.setRowCount(0)
            for i in sorted_keys(self.pj[INDEPENDENT_VARIABLES]):

                observationWindow.twIndepVariables.setRowCount(observationWindow.twIndepVariables.rowCount() + 1)

                # label
                item = QTableWidgetItem()
                indepVarLabel = self.pj[INDEPENDENT_VARIABLES][i]["label"]
                item.setText(indepVarLabel)
                item.setFlags(Qt.ItemIsEnabled)
                observationWindow.twIndepVariables.setItem(observationWindow.twIndepVariables.rowCount() - 1, 0, item)

                # var type
                item = QTableWidgetItem()
                item.setText(self.pj[INDEPENDENT_VARIABLES][i]["type"])
                item.setFlags(Qt.ItemIsEnabled)  # not modifiable
                observationWindow.twIndepVariables.setItem(observationWindow.twIndepVariables.rowCount() - 1, 1, item)

                # var value
                item = QTableWidgetItem()
                # check if obs has independent variables and var label is a key
                if (mode == EDIT and INDEPENDENT_VARIABLES in self.pj[OBSERVATIONS][obsId] and
                        indepVarLabel in self.pj[OBSERVATIONS][obsId][INDEPENDENT_VARIABLES]):
                    txt = self.pj[OBSERVATIONS][obsId][INDEPENDENT_VARIABLES][indepVarLabel]

                elif mode == NEW:
                    txt = self.pj[INDEPENDENT_VARIABLES][i]["default value"]
                else:
                    txt = ""

                if self.pj[INDEPENDENT_VARIABLES][i]["type"] == SET_OF_VALUES:
                    comboBox = QComboBox()
                    comboBox.addItems(self.pj[INDEPENDENT_VARIABLES][i]["possible values"].split(","))
                    if txt in self.pj[INDEPENDENT_VARIABLES][i]["possible values"].split(","):
                        comboBox.setCurrentIndex(
                            self.pj[INDEPENDENT_VARIABLES][i]["possible values"].split(",").index(txt))
                    observationWindow.twIndepVariables.setCellWidget(observationWindow.twIndepVariables.rowCount() - 1,
                                                                     2, comboBox)

                elif self.pj[INDEPENDENT_VARIABLES][i]["type"] == TIMESTAMP:
                    cal = QDateTimeEdit()
                    cal.setDisplayFormat("yyyy-MM-dd hh:mm:ss")
                    cal.setCalendarPopup(True)
                    if txt:
                        cal.setDateTime(QDateTime.fromString(txt, "yyyy-MM-ddThh:mm:ss"))
                    observationWindow.twIndepVariables.setCellWidget(observationWindow.twIndepVariables.rowCount() - 1,
                                                                     2, cal)
                else:
                    item.setText(txt)
                    observationWindow.twIndepVariables.setItem(observationWindow.twIndepVariables.rowCount() - 1, 2,
                                                               item)

            observationWindow.twIndepVariables.resizeColumnsToContents()

        # adapt time offset for current time format
        if self.timeFormat == S:
            observationWindow.obs_time_offset.set_format_s()
        if self.timeFormat == HHMMSS:
            observationWindow.obs_time_offset.set_format_hhmmss()

        if mode == EDIT:

            observationWindow.setWindowTitle(f'Edit observation "{obsId}"')
            mem_obs_id = obsId
            observationWindow.leObservationId.setText(obsId)

            # check date format for old versions of BORIS app
            try:
                time.strptime(self.pj[OBSERVATIONS][obsId]["date"], "%Y-%m-%d %H:%M")
                self.pj[OBSERVATIONS][obsId]["date"] = self.pj[OBSERVATIONS][obsId]["date"].replace(" ", "T") + ":00"
            except ValueError:
                pass

            observationWindow.dteDate.setDateTime(
                QDateTime.fromString(self.pj[OBSERVATIONS][obsId]["date"], "yyyy-MM-ddThh:mm:ss"))
            observationWindow.teDescription.setPlainText(self.pj[OBSERVATIONS][obsId][DESCRIPTION])

            try:
                observationWindow.mediaDurations = self.pj[OBSERVATIONS][obsId][MEDIA_INFO]["length"]
                observationWindow.mediaFPS = self.pj[OBSERVATIONS][obsId][MEDIA_INFO]["fps"]
            except Exception:
                observationWindow.mediaDurations = {}
                observationWindow.mediaFPS = {}

            try:
                if "hasVideo" in self.pj[OBSERVATIONS][obsId][MEDIA_INFO]:
                    observationWindow.mediaHasVideo = self.pj[OBSERVATIONS][obsId][MEDIA_INFO]["hasVideo"]
                if "hasAudio" in self.pj[OBSERVATIONS][obsId][MEDIA_INFO]:
                    observationWindow.mediaHasAudio = self.pj[OBSERVATIONS][obsId][MEDIA_INFO]["hasAudio"]
            except Exception:
                logging.info("No Video/Audio information")

            # offset
            observationWindow.obs_time_offset.set_time(self.pj[OBSERVATIONS][obsId][TIME_OFFSET])

            observationWindow.twVideo1.setRowCount(0)
            for player in self.pj[OBSERVATIONS][obsId][FILE]:
                if player in self.pj[OBSERVATIONS][obsId][FILE] and self.pj[OBSERVATIONS][obsId][FILE][player]:
                    for mediaFile in self.pj[OBSERVATIONS][obsId][FILE][player]:
                        observationWindow.twVideo1.setRowCount(observationWindow.twVideo1.rowCount() + 1)

                        combobox = QComboBox()
                        combobox.addItems(ALL_PLAYERS)
                        combobox.setCurrentIndex(int(player) - 1)
                        observationWindow.twVideo1.setCellWidget(observationWindow.twVideo1.rowCount() - 1, 0, combobox)

                        item = QTableWidgetItem(mediaFile)
                        item.setFlags(Qt.ItemIsEnabled)
                        observationWindow.twVideo1.setItem(observationWindow.twVideo1.rowCount() - 1, 2, item)

                        # set offset
                        try:
                            observationWindow.twVideo1.setItem(
                                observationWindow.twVideo1.rowCount() - 1,
                                1,
                                QTableWidgetItem(str(self.pj[OBSERVATIONS][obsId][MEDIA_INFO]["offset"][player])),
                            )
                        except Exception:
                            observationWindow.twVideo1.setItem(observationWindow.twVideo1.rowCount() - 1, 1,
                                                               QTableWidgetItem("0.0"))

                        # duration and FPS
                        try:
                            item = QTableWidgetItem(
                                seconds2time(self.pj[OBSERVATIONS][obsId][MEDIA_INFO][LENGTH][mediaFile]))
                            item.setFlags(Qt.ItemIsEnabled)
                            observationWindow.twVideo1.setItem(observationWindow.twVideo1.rowCount() - 1, 3, item)

                            item = QTableWidgetItem(f"{self.pj[OBSERVATIONS][obsId][MEDIA_INFO][FPS][mediaFile]:.2f}")
                            item.setFlags(Qt.ItemIsEnabled)
                            observationWindow.twVideo1.setItem(observationWindow.twVideo1.rowCount() - 1, 4, item)
                        except Exception:
                            pass

                        # has_video has_audio
                        try:
                            item = QTableWidgetItem(str(
                                self.pj[OBSERVATIONS][obsId][MEDIA_INFO]["hasVideo"][mediaFile]))
                            item.setFlags(Qt.ItemIsEnabled)
                            observationWindow.twVideo1.setItem(observationWindow.twVideo1.rowCount() - 1, 5, item)

                            item = QTableWidgetItem(str(
                                self.pj[OBSERVATIONS][obsId][MEDIA_INFO]["hasAudio"][mediaFile]))
                            item.setFlags(Qt.ItemIsEnabled)
                            observationWindow.twVideo1.setItem(observationWindow.twVideo1.rowCount() - 1, 6, item)
                        except Exception:
                            pass

            if self.pj[OBSERVATIONS][obsId]["type"] in [MEDIA]:
                observationWindow.tabProjectType.setCurrentIndex(MEDIA_TAB_IDX)

            if self.pj[OBSERVATIONS][obsId]["type"] in [LIVE]:
                observationWindow.tabProjectType.setCurrentIndex(LIVE_TAB_IDX)
                # sampling time
                observationWindow.sbScanSampling.setValue(self.pj[OBSERVATIONS][obsId].get(SCAN_SAMPLING_TIME, 0))
                # start from current time
                observationWindow.cb_start_from_current_time.setChecked(
                    self.pj[OBSERVATIONS][obsId].get(START_FROM_CURRENT_TIME, False) or
                    self.pj[OBSERVATIONS][obsId].get(START_FROM_CURRENT_EPOCH_TIME, False))
                # day/epoch time
                observationWindow.rb_day_time.setChecked(self.pj[OBSERVATIONS][obsId].get(
                    START_FROM_CURRENT_TIME, False))
                observationWindow.rb_epoch_time.setChecked(self.pj[OBSERVATIONS][obsId].get(
                    START_FROM_CURRENT_EPOCH_TIME, False))

            # spectrogram
            observationWindow.cbVisualizeSpectrogram.setEnabled(True)
            observationWindow.cbVisualizeSpectrogram.setChecked(self.pj[OBSERVATIONS][obsId].get(
                VISUALIZE_SPECTROGRAM, False))

            # waveform
            observationWindow.cb_visualize_waveform.setEnabled(True)
            observationWindow.cb_visualize_waveform.setChecked(self.pj[OBSERVATIONS][obsId].get(
                VISUALIZE_WAVEFORM, False))

            # observation time interval
            observationWindow.cb_observation_time_interval.setEnabled(True)
            if self.pj[OBSERVATIONS][obsId].get(OBSERVATION_TIME_INTERVAL, [0, 0]) != [0, 0]:
                observationWindow.cb_observation_time_interval.setChecked(True)
                observationWindow.observation_time_interval = self.pj[OBSERVATIONS][obsId].get(
                    OBSERVATION_TIME_INTERVAL, [0, 0])
                observationWindow.cb_observation_time_interval.setText(
                    ("Limit observation to a time interval: "
                     f"{self.pj[OBSERVATIONS][obsId][OBSERVATION_TIME_INTERVAL][0]} - "
                     f"{self.pj[OBSERVATIONS][obsId][OBSERVATION_TIME_INTERVAL][1]}"))

            # plot data
            if PLOT_DATA in self.pj[OBSERVATIONS][obsId]:
                if self.pj[OBSERVATIONS][obsId][PLOT_DATA]:

                    observationWindow.tw_data_files.setRowCount(0)
                    for idx2 in sorted_keys(self.pj[OBSERVATIONS][obsId][PLOT_DATA]):
                        observationWindow.tw_data_files.setRowCount(observationWindow.tw_data_files.rowCount() + 1)
                        for idx3 in DATA_PLOT_FIELDS:
                            if idx3 == PLOT_DATA_PLOTCOLOR_IDX:
                                combobox = QComboBox()
                                combobox.addItems(DATA_PLOT_STYLES)
                                combobox.setCurrentIndex(
                                    DATA_PLOT_STYLES.index(
                                        self.pj[OBSERVATIONS][obsId][PLOT_DATA][idx2][DATA_PLOT_FIELDS[idx3]]))

                                observationWindow.tw_data_files.setCellWidget(
                                    observationWindow.tw_data_files.rowCount() - 1, PLOT_DATA_PLOTCOLOR_IDX, combobox)
                            elif idx3 == PLOT_DATA_SUBSTRACT1STVALUE_IDX:
                                combobox2 = QComboBox()
                                combobox2.addItems(["False", "True"])
                                combobox2.setCurrentIndex(["False", "True"].index(
                                    self.pj[OBSERVATIONS][obsId][PLOT_DATA][idx2][DATA_PLOT_FIELDS[idx3]]))

                                observationWindow.tw_data_files.setCellWidget(
                                    observationWindow.tw_data_files.rowCount() - 1,
                                    PLOT_DATA_SUBSTRACT1STVALUE_IDX,
                                    combobox2,
                                )
                            elif idx3 == PLOT_DATA_CONVERTERS_IDX:
                                # convert dict to str
                                """
                                s = ""
                                for conv in self.pj[OBSERVATIONS][obsId][PLOT_DATA][idx2][DATA_PLOT_FIELDS[idx3]]:
                                    s += "," if s else ""
                                    s += "{}:{}".format(conv, self.pj[OBSERVATIONS][obsId][PLOT_DATA][idx2][DATA_PLOT_FIELDS[idx3]][conv])
                                """
                                observationWindow.tw_data_files.setItem(
                                    observationWindow.tw_data_files.rowCount() - 1,
                                    idx3,
                                    QTableWidgetItem(
                                        str(self.pj[OBSERVATIONS][obsId][PLOT_DATA][idx2][DATA_PLOT_FIELDS[idx3]])),
                                )

                            else:
                                observationWindow.tw_data_files.setItem(
                                    observationWindow.tw_data_files.rowCount() - 1,
                                    idx3,
                                    QTableWidgetItem(
                                        self.pj[OBSERVATIONS][obsId][PLOT_DATA][idx2][DATA_PLOT_FIELDS[idx3]]),
                                )

            # disabled due to problem when video goes back
            # if CLOSE_BEHAVIORS_BETWEEN_VIDEOS in self.pj[OBSERVATIONS][obsId]:
            #    observationWindow.cbCloseCurrentBehaviorsBetweenVideo.setChecked(self.pj[OBSERVATIONS][obsId][CLOSE_BEHAVIORS_BETWEEN_VIDEOS])

        rv = observationWindow.exec_()

        if rv:

            self.projectChanged = True

            new_obs_id = observationWindow.leObservationId.text().strip()

            if mode == NEW:
                self.observationId = new_obs_id
                self.pj[OBSERVATIONS][self.observationId] = {
                    FILE: [],
                    TYPE: "",
                    "date": "",
                    DESCRIPTION: "",
                    TIME_OFFSET: 0,
                    EVENTS: [],
                    OBSERVATION_TIME_INTERVAL: [0, 0],
                }

            # check if id changed
            if mode == EDIT and new_obs_id != obsId:

                logging.info(f"observation id {obsId} changed in {new_obs_id}")

                self.pj[OBSERVATIONS][new_obs_id] = dict(self.pj[OBSERVATIONS][obsId])
                del self.pj[OBSERVATIONS][obsId]

            # observation date
            self.pj[OBSERVATIONS][new_obs_id]["date"] = observationWindow.dteDate.dateTime().toString(Qt.ISODate)
            self.pj[OBSERVATIONS][new_obs_id][DESCRIPTION] = observationWindow.teDescription.toPlainText()
            # observation type: read project type from tab text
            self.pj[OBSERVATIONS][new_obs_id][TYPE] = observationWindow.tabProjectType.tabText(
                observationWindow.tabProjectType.currentIndex()).upper()

            # independent variables for observation
            self.pj[OBSERVATIONS][new_obs_id][INDEPENDENT_VARIABLES] = {}
            for r in range(observationWindow.twIndepVariables.rowCount()):

                # set dictionary as label (col 0) => value (col 2)
                if observationWindow.twIndepVariables.item(r, 1).text() == SET_OF_VALUES:
                    self.pj[OBSERVATIONS][new_obs_id][INDEPENDENT_VARIABLES][observationWindow.twIndepVariables.item(
                        r, 0).text()] = observationWindow.twIndepVariables.cellWidget(r, 2).currentText()
                elif observationWindow.twIndepVariables.item(r, 1).text() == TIMESTAMP:
                    self.pj[OBSERVATIONS][new_obs_id][INDEPENDENT_VARIABLES][observationWindow.twIndepVariables.item(
                        r,
                        0).text()] = (observationWindow.twIndepVariables.cellWidget(r,
                                                                                    2).dateTime().toString(Qt.ISODate))
                else:
                    self.pj[OBSERVATIONS][new_obs_id][INDEPENDENT_VARIABLES][observationWindow.twIndepVariables.item(
                        r, 0).text()] = observationWindow.twIndepVariables.item(r, 2).text()

            # observation time offset
            self.pj[OBSERVATIONS][new_obs_id][TIME_OFFSET] = observationWindow.obs_time_offset.get_time()

            if observationWindow.cb_observation_time_interval.isChecked():
                self.pj[OBSERVATIONS][new_obs_id][
                    OBSERVATION_TIME_INTERVAL] = observationWindow.observation_time_interval

            self.display_statusbar_info(new_obs_id)

            # visualize spectrogram
            self.pj[OBSERVATIONS][new_obs_id][
                VISUALIZE_SPECTROGRAM] = observationWindow.cbVisualizeSpectrogram.isChecked()
            # visualize spectrogram
            self.pj[OBSERVATIONS][new_obs_id][VISUALIZE_WAVEFORM] = observationWindow.cb_visualize_waveform.isChecked()
            # time interval for observation
            self.pj[OBSERVATIONS][new_obs_id][OBSERVATION_TIME_INTERVAL] = observationWindow.observation_time_interval

            # plot data
            if observationWindow.tw_data_files.rowCount():
                self.pj[OBSERVATIONS][new_obs_id][PLOT_DATA] = {}
                for row in range(observationWindow.tw_data_files.rowCount()):
                    self.pj[OBSERVATIONS][new_obs_id][PLOT_DATA][str(row)] = {}
                    for idx2 in DATA_PLOT_FIELDS:
                        if idx2 in [PLOT_DATA_PLOTCOLOR_IDX, PLOT_DATA_SUBSTRACT1STVALUE_IDX]:
                            self.pj[OBSERVATIONS][new_obs_id][PLOT_DATA][
                                str(row)][DATA_PLOT_FIELDS[idx2]] = observationWindow.tw_data_files.cellWidget(
                                    row, idx2).currentText()

                        elif idx2 == PLOT_DATA_CONVERTERS_IDX:
                            if observationWindow.tw_data_files.item(row, idx2).text():
                                self.pj[OBSERVATIONS][new_obs_id][PLOT_DATA][str(row)][DATA_PLOT_FIELDS[idx2]] = eval(
                                    observationWindow.tw_data_files.item(row, idx2).text())
                            else:
                                self.pj[OBSERVATIONS][new_obs_id][PLOT_DATA][str(row)][DATA_PLOT_FIELDS[idx2]] = {}

                        else:
                            self.pj[OBSERVATIONS][new_obs_id][PLOT_DATA][str(row)][
                                DATA_PLOT_FIELDS[idx2]] = observationWindow.tw_data_files.item(row, idx2).text()

            # Close current behaviors between video
            # disabled due to problem when video goes back
            # self.pj[OBSERVATIONS][new_obs_id][CLOSE_BEHAVIORS_BETWEEN_VIDEOS] =
            # observationWindow.cbCloseCurrentBehaviorsBetweenVideo.isChecked()
            self.pj[OBSERVATIONS][new_obs_id][CLOSE_BEHAVIORS_BETWEEN_VIDEOS] = False

            if self.pj[OBSERVATIONS][new_obs_id][TYPE] in [LIVE]:
                self.pj[OBSERVATIONS][new_obs_id][SCAN_SAMPLING_TIME] = observationWindow.sbScanSampling.value()
                self.pj[OBSERVATIONS][new_obs_id][START_FROM_CURRENT_TIME] = (
                    observationWindow.cb_start_from_current_time.isChecked() and
                    observationWindow.rb_day_time.isChecked())
                self.pj[OBSERVATIONS][new_obs_id][START_FROM_CURRENT_EPOCH_TIME] = (
                    observationWindow.cb_start_from_current_time.isChecked() and
                    observationWindow.rb_epoch_time.isChecked())

            # media file
            self.pj[OBSERVATIONS][new_obs_id][FILE] = {}

            # media
            if self.pj[OBSERVATIONS][new_obs_id][TYPE] in [MEDIA]:

                self.pj[OBSERVATIONS][new_obs_id][MEDIA_INFO] = {
                    LENGTH: observationWindow.mediaDurations,
                    FPS: observationWindow.mediaFPS,
                }

                try:
                    self.pj[OBSERVATIONS][new_obs_id][MEDIA_INFO]["hasVideo"] = observationWindow.mediaHasVideo
                    self.pj[OBSERVATIONS][new_obs_id][MEDIA_INFO]["hasAudio"] = observationWindow.mediaHasAudio
                except Exception:
                    logging.info("error with media_info information")

                self.pj[OBSERVATIONS][new_obs_id][MEDIA_INFO]["offset"] = {}

                logging.debug(f"media_info: {self.pj[OBSERVATIONS][new_obs_id][MEDIA_INFO]}")

                for i in range(N_PLAYER):
                    self.pj[OBSERVATIONS][new_obs_id][FILE][str(i + 1)] = []

                for row in range(observationWindow.twVideo1.rowCount()):
                    self.pj[OBSERVATIONS][new_obs_id][FILE][observationWindow.twVideo1.cellWidget(
                        row, 0).currentText()].append(observationWindow.twVideo1.item(row, 2).text())
                    # store offset for media player
                    self.pj[OBSERVATIONS][new_obs_id][MEDIA_INFO]["offset"][observationWindow.twVideo1.cellWidget(
                        row, 0).currentText()] = float(observationWindow.twVideo1.item(row, 1).text())

            if rv == 1:  # save
                self.observationId = ""
                menu_options.update_menu(self)

            if rv == 2:  # start
                self.observationId = new_obs_id

                # title of dock widget
                self.dwObservations.setWindowTitle(f'Events for "{self.observationId}" observation')

                if self.pj[OBSERVATIONS][self.observationId][TYPE] in [LIVE]:

                    self.playerType = LIVE
                    self.initialize_new_live_observation()

                elif self.pj[OBSERVATIONS][self.observationId][TYPE] in [MEDIA]:
                    self.playerType = VLC
                    # load events in table widget
                    if mode == EDIT:
                        self.loadEventsInTW(self.observationId)

                    self.initialize_new_observation_mpv()

                menu_options.update_menu(self)

    def close_tool_windows(self):
        """
        close tool windows:
            spectrogram
            measurements
            coding pad
            video_equalizer
        """

        logging.debug("function: close_tool_windows")
        """
        for w in [self.measurement_w, self.codingpad, self.subjects_pad, self.spectro,
                  self.frame_viewer1, self.frame_viewer2, self.results,
                  self.mapCreatorWindow]:
            try:
                w.close()
            except:
                pass
        """
        try:
            del self.iw
        except Exception:
            pass

        try:
            del self.tb
        except Exception:
            pass
        try:
            for x in self.ext_data_timer_list:
                x.stop()
        except Exception:
            pass

        try:
            for pd in self.plot_data:
                self.plot_data[pd].close_plot()

        except Exception:
            pass
        """
        while self.plot_data:
            self.plot_data[0].close_plot()
            time.sleep(1)
            del self.plot_data[0]
        """

        if hasattr(self, "measurement_w"):
            try:
                self.measurement_w.close()
                del self.codingpad
            except Exception:
                pass

        if hasattr(self, "codingpad"):
            try:
                self.codingpad.close()
                del self.codingpad
            except Exception:
                pass

        if hasattr(self, "subjects_pad"):
            try:
                self.subjects_pad.close()
                del self.subjects_pad
            except Exception:
                pass

        if hasattr(self, "spectro"):
            try:
                self.spectro.close()
                del self.spectro
            except Exception:
                pass

        if hasattr(self, "waveform"):
            try:
                self.waveform.close()
                del self.waveform
            except Exception:
                pass

        if hasattr(self, "plot_events"):
            try:
                self.plot_events.close()
                del self.plot_events
            except Exception:
                pass

        if hasattr(self, "results"):
            try:
                self.results.close()
                del self.results
            except Exception:
                pass

        if hasattr(self, "mapCreatorWindow"):
            try:
                self.mapCreatorWindow.close()
                del self.mapCreatorWindow
            except Exception:
                pass

        if hasattr(self, "video_equalizer_wgt"):
            try:
                self.video_equalizer_wgt.close()
                del self.video_equalizer_wgt
            except Exception:
                pass

        # delete behavior coding map
        try:
            for idx in self.bcm_dict:
                if self.bcm_dict[idx] is not None:
                    self.bcm_dict[idx].close()
                self.bcm_dict[idx] = None
        except Exception:
            dialog.error_message2()

    logging.debug("function: close_tool_windows finished")

    def close_observation(self):
        """
        close current observation
        """

        logging.info(f"Close observation {self.playerType}")

        try:

            logging.info(f"Check state events")

            # check observation events
            flag_ok, msg = project_functions.check_state_events_obs(self.observationId,
                                                                    self.pj[ETHOGRAM],
                                                                    self.pj[OBSERVATIONS][self.observationId],
                                                                    time_format=HHMMSS)

            if not flag_ok:

                out = f"The current observation has state event(s) that are not PAIRED:<br><br>{msg}"
                results = dialog.Results_dialog()
                results.setWindowTitle(f"{programName} - Check selected observations")
                results.ptText.setReadOnly(True)
                results.ptText.appendHtml(out)
                results.pbSave.setVisible(False)
                results.pbCancel.setText("Close observation")
                results.pbCancel.setVisible(True)
                results.pbOK.setText("Fix unpaired state events")

                if results.exec_():  # fix events

                    w = dialog.Ask_time(self.timeFormat)
                    w.setWindowTitle("Fix UNPAIRED state events")
                    w.label.setText("Fix UNPAIRED events at time")

                    if w.exec_():
                        fix_at_time = w.time_widget.get_time()
                        events_to_add = project_functions.fix_unpaired_state_events(
                            self.observationId,
                            self.pj[ETHOGRAM],
                            self.pj[OBSERVATIONS][self.observationId],
                            fix_at_time - Decimal("0.001"),
                        )
                        if events_to_add:
                            self.pj[OBSERVATIONS][self.observationId][EVENTS].extend(events_to_add)
                            self.projectChanged = True
                            self.pj[OBSERVATIONS][self.observationId][EVENTS].sort()

                            self.loadEventsInTW(self.observationId)
                            item = self.twEvents.item(
                                [
                                    i for i, t in enumerate(self.pj[OBSERVATIONS][self.observationId][EVENTS])
                                    if t[0] == fix_at_time
                                ][0],
                                0,
                            )
                            self.twEvents.scrollToItem(item)
                            return
                    else:
                        return

            logging.info(f"Check state events done")

            self.saved_state = self.saveState()

            if self.playerType == VLC:

                logging.info(f"Stop plot timer")
                self.plot_timer.stop()

                if self.playMode == MPV:
                    for i, player in enumerate(self.dw_player):
                        if (str(i + 1) in self.pj[OBSERVATIONS][self.observationId][FILE] and
                                self.pj[OBSERVATIONS][self.observationId][FILE][str(i + 1)]):
                            logging.info(f"Stop player {i + 1}")
                            player.player.stop()

                self.verticalLayout_3.removeWidget(self.video_slider)

                if self.video_slider is not None:
                    self.video_slider.setVisible(False)
                    self.video_slider.deleteLater()
                    self.video_slider = None

            if self.playerType == LIVE:
                self.liveTimer.stop()
                self.w_live.setVisible(False)
                self.liveObservationStarted = False
                self.liveStartTime = None

            if (PLOT_DATA in self.pj[OBSERVATIONS][self.observationId] and
                    self.pj[OBSERVATIONS][self.observationId][PLOT_DATA]):
                for x in self.ext_data_timer_list:
                    x.stop()
                for pd in self.plot_data:
                    self.plot_data[pd].close_plot()

            logging.info(f"close tool window")

            self.close_tool_windows()

            if self.playerType == VLC:

                for dw in self.dw_player:

                    logging.info(f"remove dock widget")
                    self.removeDockWidget(dw)
                    # dw.player.quit()
                    dw.deleteLater()

                self.dw_player = []
                self.playMode = VLC

            # return

            self.observationId = ""

            self.statusbar.showMessage("", 0)

            self.dwObservations.setVisible(False)

            self.w_obs_info.setVisible(False)

            self.twEvents.setRowCount(0)

            self.lb_current_media_time.clear()
            self.lb_player_status.clear()

            self.currentSubject = ""
            self.lbFocalSubject.setText(NO_FOCAL_SUBJECT)

            # clear current state(s) column in subjects table
            for i in range(self.twSubjects.rowCount()):
                self.twSubjects.item(i, len(subjectsFields)).setText("")

            for w in [self.lbTimeOffset, self.lbSpeed, self.lb_obs_time_interval]:
                w.clear()
            self.play_rate, self.playerType = 1, ""

            menu_options.update_menu(self)

        except Exception:
            dialog.error_message2()

    def set_recent_projects_menu(self):
        """
        set the recent projects submenu
        """
        self.menuRecent_projects.clear()
        for project_file_path in self.recent_projects:
            if pathlib.Path(project_file_path).is_file():
                action = QAction(self, visible=False, triggered=self.open_project_activated)
                action.setText(project_file_path)
                action.setVisible(True)
                self.menuRecent_projects.addAction(action)

    def edit_project_activated(self):
        """
        edit project menu option triggered
        """
        if self.project:
            self.edit_project(EDIT)
        else:
            QMessageBox.warning(self, programName, "There is no project to edit")

    def display_statusbar_info(self, obs_id: str):
        """
        display information about obs_id observation in status bar:
        time offset, observation time interval
        """

        logging.debug(f"function: display statusbar info: {obs_id}")

        try:
            if self.pj[OBSERVATIONS][obs_id][TIME_OFFSET]:
                time_offset = 0
                if self.timeFormat == S:
                    time_offset = self.pj[OBSERVATIONS][obs_id][TIME_OFFSET]
                if self.timeFormat == HHMMSS:
                    time_offset = seconds2time(self.pj[OBSERVATIONS][obs_id][TIME_OFFSET])
                self.lbTimeOffset.setText(f"Time offset: <b>{time_offset}</b>")
            else:
                self.lbTimeOffset.clear()
        except Exception:
            logging.debug("error in time offset display")
            pass

        try:
            if OBSERVATION_TIME_INTERVAL in self.pj[OBSERVATIONS][obs_id]:
                if self.pj[OBSERVATIONS][obs_id][OBSERVATION_TIME_INTERVAL] != [0, 0]:

                    if self.timeFormat == HHMMSS:
                        start_time = utilities.seconds2time(self.pj[OBSERVATIONS][obs_id][OBSERVATION_TIME_INTERVAL][0])
                        stop_time = utilities.seconds2time(self.pj[OBSERVATIONS][obs_id][OBSERVATION_TIME_INTERVAL][1])
                    if self.timeFormat == S:
                        start_time = f"{self.pj[OBSERVATIONS][obs_id][OBSERVATION_TIME_INTERVAL][0]:.3f}"
                        stop_time = f"{self.pj[OBSERVATIONS][obs_id][OBSERVATION_TIME_INTERVAL][1]:.3f}"

                    self.lb_obs_time_interval.setText(("Observation time interval: " f"{start_time} - {stop_time}"))
                else:
                    self.lb_obs_time_interval.clear()
            else:
                self.lb_obs_time_interval.clear()
        except Exception:
            logging.debug("error in observation time interval")

    # TODO: replace by event_type in project_functions
    def eventType(self, code):
        """
        returns type of event for code
        """
        for idx in self.pj[ETHOGRAM]:
            if self.pj[ETHOGRAM][idx][BEHAVIOR_CODE] == code:
                return self.pj[ETHOGRAM][idx][TYPE]
        return None

    def extract_observed_behaviors(self, selected_observations, selectedSubjects):
        """
        extract unique behaviors codes from obs_id observation
        """

        observed_behaviors = []

        # extract events from selected observations
        all_events = [self.pj[OBSERVATIONS][x][EVENTS] for x in self.pj[OBSERVATIONS] if x in selected_observations]

        for events in all_events:
            for event in events:
                if event[EVENT_SUBJECT_FIELD_IDX] in selectedSubjects or (not event[EVENT_SUBJECT_FIELD_IDX] and
                                                                          NO_FOCAL_SUBJECT in selectedSubjects):
                    observed_behaviors.append(event[EVENT_BEHAVIOR_FIELD_IDX])

        # remove duplicate
        observed_behaviors = list(set(observed_behaviors))

        return observed_behaviors

    def observation_length(self, selected_observations: list) -> tuple:
        """
        max length of selected observations
        total media length

        Args:
            selected_observations (list): list of selected observations

        Returns:
            float: maximum media length for all observations
            float: total media length for all observations
        """
        selectedObsTotalMediaLength = Decimal("0.0")
        max_obs_length = 0
        for obs_id in selected_observations:
            obs_length = project_functions.observation_total_length(self.pj[OBSERVATIONS][obs_id])
            if obs_length in [Decimal("0"), Decimal("-1")]:
                selectedObsTotalMediaLength = -1
                break
            max_obs_length = max(max_obs_length, obs_length)
            selectedObsTotalMediaLength += obs_length

        # an observation media length is not available
        if selectedObsTotalMediaLength == -1:
            # propose to user to use max event time
            if (dialog.MessageDialog(
                    programName,
                (f"A media length is not available for the observation <b>{obs_id}</b>.<br>"
                 "Use last event time as media length?"),
                [YES, NO],
            ) == YES):
                maxTime = 0  # max length for all events all subjects
                max_length = 0
                for obs_id in selected_observations:
                    if self.pj[OBSERVATIONS][obs_id][EVENTS]:
                        maxTime += max(self.pj[OBSERVATIONS][obs_id][EVENTS])[0]
                        max_length = max(max_length, max(self.pj[OBSERVATIONS][obs_id][EVENTS])[0])

                logging.debug(f"max time all events all subjects: {maxTime}")

                max_obs_length = max_length
                selectedObsTotalMediaLength = maxTime

            else:
                max_obs_length = -1
                selectedObsTotalMediaLength = Decimal("-1")

        return max_obs_length, selectedObsTotalMediaLength

    def plot_events_triggered(self, mode: str = "list"):
        """
        plot events in time diagram
        """
        if mode == "list":
            _, selected_observations = self.selectObservations(MULTIPLE)

            if not selected_observations:
                return
        if mode == "current" and self.observationId:
            selected_observations = [self.observationId]
        # check if state events are paired
        out = ""
        not_paired_obs_list = []
        for obs_id in selected_observations:
            r, msg = project_functions.check_state_events_obs(obs_id, self.pj[ETHOGRAM], self.pj[OBSERVATIONS][obs_id],
                                                              self.timeFormat)

            if not r:
                out += f"Observation: <strong>{obs_id}</strong><br>{msg}<br>"
                not_paired_obs_list.append(obs_id)

        if out:
            out = "The observations with UNPAIRED state events will be removed from the plot<br><br>" + out
            self.results = dialog.Results_dialog()
            self.results.setWindowTitle(programName + " - Check selected observations")
            self.results.ptText.setReadOnly(True)
            self.results.ptText.appendHtml(out)
            self.results.pbSave.setVisible(False)
            self.results.pbCancel.setVisible(True)

            if not self.results.exec_():
                return
        selected_observations = [x for x in selected_observations if x not in not_paired_obs_list]
        if not selected_observations:
            return

        # check if almost one selected observation has events
        """
        flag_no_events = True
        for obs_id in selected_observations:
            if self.pj[OBSERVATIONS][obs_id][EVENTS]:
                flag_no_events = False
                break
        if flag_no_events:
            QMessageBox.warning(self, programName, "No events found in the selected observations")
            return
        """
        # select dir if many observations
        plot_directory = ""
        file_format = "png"
        if len(selected_observations) > 1:
            plot_directory = QFileDialog().getExistingDirectory(
                self,
                "Choose a directory to save the plots",
                os.path.expanduser("~"),
                options=QFileDialog(self).ShowDirsOnly,
            )

            if not plot_directory:
                return

            item, ok = QInputDialog.getItem(self, "Select the file format", "Available formats",
                                            ["PNG", "SVG", "PDF", "EPS", "PS"], 0, False)
            if ok and item:
                file_format = item.lower()
            else:
                return

        max_obs_length, selectedObsTotalMediaLength = self.observation_length(selected_observations)
        if max_obs_length == -1:  # media length not available, user choose to not use events
            return
        """
        selectedObsTotalMediaLength = Decimal("0.0")
        max_obs_length = 0
        for obs_id in selected_observations:
            obs_length = project_functions.observation_total_length(self.pj[OBSERVATIONS][obs_id])

            logging.debug("media length for {0}: {1}".format(obs_id, obs_length))

            if obs_length in [0, -1]:
                selectedObsTotalMediaLength = -1
                break

            max_obs_length = max(max_obs_length, obs_length)
            selectedObsTotalMediaLength += obs_length
        # an observation media length is not available
        if selectedObsTotalMediaLength == -1:
            # propose to user to use max event time
            if dialog.MessageDialog(programName, "A media length is not available.<br>Use last event time as media length?",
                                    [YES, NO]) == YES:
                maxTime = 0  # max length for all events all subjects
                for obs_id in selected_observations:
                    if self.pj[OBSERVATIONS][obs_id][EVENTS]:
                        maxTime += max(self.pj[OBSERVATIONS][obs_id][EVENTS])[0]
                logging.debug("max time all events all subjects: {}".format(maxTime))
                selectedObsTotalMediaLength = maxTime
            else:
                selectedObsTotalMediaLength = 0
        """

        parameters = select_subj_behav.choose_obs_subj_behav_category(
            self,
            selected_observations,
            maxTime=max_obs_length,
            flagShowExcludeBehaviorsWoEvents=True,
            by_category=False,
        )

        if not parameters[SELECTED_SUBJECTS] or not parameters[SELECTED_BEHAVIORS]:
            QMessageBox.warning(self, programName, "Select subject(s) and behavior(s) to plot")
            return

        plot_events.create_events_plot(
            self.pj,
            selected_observations,
            parameters,
            plot_colors=self.plot_colors,
            plot_directory=plot_directory,
            file_format=file_format,
        )

    def behaviors_bar_plot(self):
        """
        bar plot of behaviors durations
        """

        result, selected_observations = self.selectObservations(MULTIPLE)
        if not selected_observations:
            return

        # check if state events are paired
        out = ""
        not_paired_obs_list = []
        for obsId in selected_observations:
            r, msg = project_functions.check_state_events_obs(obsId, self.pj[ETHOGRAM], self.pj[OBSERVATIONS][obsId],
                                                              self.timeFormat)

            if not r:
                out += f"Observation: <strong>{obsId}</strong><br>{msg}<br>"
                not_paired_obs_list.append(obsId)

        if out:
            out = "The observations with UNPAIRED state events will be removed from the plot<br>br>" + out
            results = dialog.Results_dialog()
            results.setWindowTitle(programName + " - Check selected observations")
            results.ptText.setReadOnly(True)
            results.ptText.appendHtml(out)
            if not results.exec_():
                return

        selected_observations = [x for x in selected_observations if x not in not_paired_obs_list]
        if not selected_observations:
            return

        # check if almost one selected observation has events
        flag_no_events = True
        for obsId in selected_observations:
            if self.pj[OBSERVATIONS][obsId][EVENTS]:
                flag_no_events = False
                break
        if flag_no_events:
            QMessageBox.warning(self, programName, "No events found in the selected observations")
            return

        max_obs_length = -1
        for obsId in selected_observations:
            totalMediaLength = project_functions.observation_total_length(self.pj[OBSERVATIONS][obsId])
            if totalMediaLength == -1:
                totalMediaLength = 0
            max_obs_length = max(max_obs_length, totalMediaLength)

        if len(selected_observations) == 1:
            parameters = select_subj_behav.choose_obs_subj_behav_category(
                self,
                selected_observations,
                maxTime=totalMediaLength,
                flagShowIncludeModifiers=False,
                flagShowExcludeBehaviorsWoEvents=True,
            )
        else:
            parameters = select_subj_behav.choose_obs_subj_behav_category(
                self,
                selected_observations,
                maxTime=0,
                flagShowIncludeModifiers=False,
                flagShowExcludeBehaviorsWoEvents=True,
            )

        if not parameters[SELECTED_SUBJECTS] or not parameters[SELECTED_BEHAVIORS]:
            QMessageBox.warning(self, programName, "Select subject(s) and behavior(s) to plot")
            return

        plot_directory = ""
        output_format = ""
        if len(selected_observations) > 1:
            plot_directory = QFileDialog().getExistingDirectory(
                self,
                "Choose a directory to save the plots",
                os.path.expanduser("~"),
                options=QFileDialog(self).ShowDirsOnly,
            )
            if not plot_directory:
                return

            item, ok = QInputDialog.getItem(self, "Select the file format", "Available formats",
                                            ["PNG", "SVG", "PDF", "EPS", "PS"], 0, False)
            if ok and item:
                output_format = item.lower()
            else:
                return

        r = plot_events.create_behaviors_bar_plot(self.pj,
                                                  selected_observations,
                                                  parameters,
                                                  plot_directory,
                                                  output_format,
                                                  plot_colors=self.plot_colors)
        if "error" in r:
            if "exception" in r:
                dialog.error_message2()
            else:
                QMessageBox.warning(self, programName, r.get("message", "Error on time budget bar plot"))

    def load_project(self, project_path, project_changed, pj):
        """
        load specified project

        Args:
            project_path (str): path of project file
            project_changed (bool): project has changed?
            pj (dict): BORIS project

        Returns:
            None
        """
        self.pj = dict(pj)
        memProjectChanged = project_changed
        self.initialize_new_project()
        self.projectChanged = True
        self.projectChanged = memProjectChanged
        self.load_behaviors_in_twEthogram([self.pj[ETHOGRAM][x][BEHAVIOR_CODE] for x in self.pj[ETHOGRAM]])
        self.load_subjects_in_twSubjects([self.pj[SUBJECTS][x][SUBJECT_NAME] for x in self.pj[SUBJECTS]])
        self.projectFileName = str(pathlib.Path(project_path).absolute())
        self.project = True
        if str(self.projectFileName) not in self.recent_projects:
            self.recent_projects = [str(self.projectFileName)] + self.recent_projects
            self.recent_projects = self.recent_projects[:10]
            self.set_recent_projects_menu()
        menu_options.update_menu(self)

    def open_project_activated(self):
        """
        open a project
        triggered by Open project menu and recent projects submenu
        """

        action = self.sender()

        # check if current observation
        if self.observationId:
            if (dialog.MessageDialog(
                    programName,
                    "There is a current observation. What do you want to do?",
                ["Close observation", "Continue observation"],
            ) == "Close observation"):
                self.close_observation()
            else:
                return

        if self.projectChanged:
            response = dialog.MessageDialog(programName, "What to do about the current unsaved project?",
                                            [SAVE, DISCARD, CANCEL])

            if response == SAVE:
                if self.save_project_activated() == "not saved":
                    return

            if response == CANCEL:
                return

        if action.text() == "Open project":
            fn = QFileDialog().getOpenFileName(self, "Open project", "", ("Project files (*.boris *.boris.gz);;"
                                                                          "All files (*)"))
            file_name = fn[0] if type(fn) is tuple else fn

        else:  # recent project
            file_name = action.text()

        if file_name:
            project_path, project_changed, pj, msg = project_functions.open_project_json(file_name)

            if "error" in pj:
                logging.debug(pj["error"])
                QMessageBox.critical(self, programName, pj["error"])
            else:
                if msg:
                    QMessageBox.information(self, programName, msg)

                # check behavior keys
                if project_changed:
                    flag_all_upper = True
                    if pj[ETHOGRAM]:
                        for idx in pj[ETHOGRAM]:
                            if pj[ETHOGRAM][idx]["key"].islower():
                                flag_all_upper = False

                    if pj[SUBJECTS]:
                        for idx in pj[SUBJECTS]:
                            if pj[SUBJECTS][idx]["key"].islower():
                                flag_all_upper = False

                    if (flag_all_upper and dialog.MessageDialog(
                            programName,
                        ("It is now possible to use <b>lower keys</b> to code behaviors, subjects and modifiers.<br><br>"
                         "In this project all the behavior and subject keys are upper case.<br>"
                         "Do you want to convert them in lower case?"),
                        [YES, NO],
                    ) == YES):
                        for idx in pj[ETHOGRAM]:
                            pj[ETHOGRAM][idx]["key"] = pj[ETHOGRAM][idx]["key"].lower()
                            # convert modifier short cuts to lower case
                            for modifier_set in pj[ETHOGRAM][idx]["modifiers"]:
                                try:
                                    for idx2, value in enumerate(
                                            pj[ETHOGRAM][idx]["modifiers"][modifier_set]["values"]):
                                        if re.findall(r"\((\w+)\)", value):
                                            pj[ETHOGRAM][idx]["modifiers"][modifier_set]["values"][idx2] = (
                                                value.split("(")[0] + "(" + re.findall(r"\((\w+)\)", value)[0].lower() +
                                                ")" + value.split(")")[-1])
                                except Exception:
                                    logging.warning("error during converion of modifier short cut to lower case")

                        for idx in pj[SUBJECTS]:
                            pj[SUBJECTS][idx]["key"] = pj[SUBJECTS][idx]["key"].lower()

                self.load_project(project_path, project_changed, pj)
                del pj

    def import_project_from_observer_template(self):
        """
        import a project from a Noldus Observer template
        """
        # check if current observation
        if self.observationId:
            if (dialog.MessageDialog(
                    programName,
                    "There is a current observation. What do you want to do?",
                ["Close observation", "Continue observation"],
            ) == "Close observation"):
                self.close_observation()
            else:
                return

        if self.projectChanged:
            response = dialog.MessageDialog(programName, "What to do about the current unsaved project?",
                                            [SAVE, DISCARD, CANCEL])

            if response == SAVE:
                if self.save_project_activated() == "not saved":
                    return

            if response == CANCEL:
                return

        fn = QFileDialog().getOpenFileName(self, "Import project from template", "",
                                           "Noldus Observer templates (*.otx *.otb);;All files (*)")
        file_name = fn[0] if type(fn) is tuple else fn

        if file_name:
            pj = otx_parser.otx_to_boris(file_name)
            if "error" in pj:
                QMessageBox.critical(self, programName, pj["error"])
            else:
                if "msg" in pj:
                    QMessageBox.warning(self, programName, pj["msg"])
                    del pj["msg"]
                self.load_project("", True, pj)

    def initialize_new_project(self, flag_new=True):
        """
        initialize interface and variables for a new or edited project
        """
        logging.debug("initialize new project...")

        self.w_logo.setVisible(not flag_new)
        self.dwEthogram.setVisible(flag_new)
        self.dwSubjects.setVisible(flag_new)

    def close_project(self):
        """
        close current project
        """

        # check if current observation
        if self.observationId:
            response = dialog.MessageDialog(
                programName,
                "There is a current observation. What do you want to do?",
                ["Close observation", "Continue observation"],
            )
            if response == "Close observation":
                self.close_observation()
            if response == "Continue observation":
                return

        if self.projectChanged:
            response = dialog.MessageDialog(programName, "What to do about the current unsaved project?",
                                            [SAVE, DISCARD, CANCEL])
            if response == SAVE:
                if self.save_project_activated() == "not saved":
                    return

            if response == CANCEL:
                return

        self.projectChanged = False
        self.setWindowTitle(programName)

        self.pj = dict(EMPTY_PROJECT)

        self.project = False
        config_file.read(self)
        menu_options.update_menu(self)

        self.initialize_new_project(flag_new=False)

        self.w_obs_info.setVisible(False)

    def convertTime(self, sec) -> str:
        """
        convert time in base of current format

        Args:
            sec: time in seconds

        Returns:
            string: time in base of current format (self.timeFormat S or HHMMSS)
        """

        if self.timeFormat == S:
            return f"{sec:.3f}"

        if self.timeFormat == HHMMSS:
            return utilities.seconds2time(sec)

    def edit_project(self, mode: str):
        """
        project management

        Args:
            mode (str): new/edit
        """

        try:
            # ask if current observation should be closed to edit the project
            if self.observationId:
                # hide data plot
                self.hide_data_files()
                response = dialog.MessageDialog(programName,
                                                "The current observation will be closed. Do you want to continue?",
                                                [YES, NO])
                if response == NO:
                    self.show_data_files()
                    return
                else:
                    self.close_observation()

            if mode == NEW:
                if self.projectChanged:
                    response = dialog.MessageDialog(programName, "What to do with the current unsaved project?",
                                                    [SAVE, DISCARD, CANCEL])

                    if response == SAVE:
                        self.save_project_activated()

                    if response == CANCEL:
                        return

                # empty main window tables
                for w in [self.twEthogram, self.twSubjects, self.twEvents]:
                    w.setRowCount(0)  # behaviors

            newProjectWindow = projectDialog()

            # pass copy of self.pj
            newProjectWindow.pj = dict(self.pj)

            if self.projectWindowGeometry:
                newProjectWindow.restoreGeometry(self.projectWindowGeometry)
            else:
                newProjectWindow.resize(800, 400)

            newProjectWindow.setWindowTitle(mode + " project")
            newProjectWindow.tabProject.setCurrentIndex(0)  # project information

            newProjectWindow.obs = newProjectWindow.pj[ETHOGRAM]
            newProjectWindow.subjects_conf = newProjectWindow.pj[SUBJECTS]

            newProjectWindow.rbSeconds.setChecked(newProjectWindow.pj[TIME_FORMAT] == S)
            newProjectWindow.rbHMS.setChecked(newProjectWindow.pj[TIME_FORMAT] == HHMMSS)

            if mode == NEW:
                newProjectWindow.dteDate.setDateTime(QDateTime.currentDateTime())
                newProjectWindow.lbProjectFilePath.setText("")

            if mode == EDIT:

                if newProjectWindow.pj[PROJECT_NAME]:
                    newProjectWindow.leProjectName.setText(newProjectWindow.pj[PROJECT_NAME])

                newProjectWindow.lbProjectFilePath.setText("Project file path: " + self.projectFileName)

                if newProjectWindow.pj[PROJECT_DESCRIPTION]:
                    newProjectWindow.teDescription.setPlainText(newProjectWindow.pj[PROJECT_DESCRIPTION])

                if newProjectWindow.pj[PROJECT_DATE]:
                    newProjectWindow.dteDate.setDateTime(
                        QDateTime.fromString(newProjectWindow.pj[PROJECT_DATE], "yyyy-MM-ddThh:mm:ss"))
                else:
                    newProjectWindow.dteDate.setDateTime(QDateTime.currentDateTime())

                # load subjects in editor
                if newProjectWindow.pj[SUBJECTS]:
                    for idx in sorted_keys(newProjectWindow.pj[SUBJECTS]):
                        newProjectWindow.twSubjects.setRowCount(newProjectWindow.twSubjects.rowCount() + 1)
                        for i, field in enumerate(subjectsFields):
                            item = QTableWidgetItem(newProjectWindow.pj[SUBJECTS][idx][field])
                            newProjectWindow.twSubjects.setItem(newProjectWindow.twSubjects.rowCount() - 1, i, item)

                    newProjectWindow.twSubjects.resizeColumnsToContents()

                # load observation in project window
                newProjectWindow.twObservations.setRowCount(0)

                if newProjectWindow.pj[OBSERVATIONS]:

                    for obs in sorted(newProjectWindow.pj[OBSERVATIONS].keys()):

                        newProjectWindow.twObservations.setRowCount(newProjectWindow.twObservations.rowCount() + 1)

                        # observation id
                        newProjectWindow.twObservations.setItem(newProjectWindow.twObservations.rowCount() - 1, 0,
                                                                QTableWidgetItem(obs))
                        # observation date
                        newProjectWindow.twObservations.setItem(
                            newProjectWindow.twObservations.rowCount() - 1,
                            1,
                            QTableWidgetItem(newProjectWindow.pj[OBSERVATIONS][obs]["date"].replace("T", " ")),
                        )
                        # observation description
                        newProjectWindow.twObservations.setItem(
                            newProjectWindow.twObservations.rowCount() - 1,
                            2,
                            QTableWidgetItem(utilities.eol2space(newProjectWindow.pj[OBSERVATIONS][obs][DESCRIPTION])),
                        )

                        mediaList = []
                        if newProjectWindow.pj[OBSERVATIONS][obs][TYPE] in [MEDIA]:
                            for idx in newProjectWindow.pj[OBSERVATIONS][obs][FILE]:
                                for media in newProjectWindow.pj[OBSERVATIONS][obs][FILE][idx]:
                                    mediaList.append(f"#{idx}: {media}")

                        elif newProjectWindow.pj[OBSERVATIONS][obs][TYPE] in [LIVE]:
                            mediaList = [LIVE]

                        media_separator = " " if len(mediaList) > 8 else "\n"
                        newProjectWindow.twObservations.setItem(
                            newProjectWindow.twObservations.rowCount() - 1,
                            3,
                            QTableWidgetItem(media_separator.join(mediaList)),
                        )

                    newProjectWindow.twObservations.resizeColumnsToContents()
                    newProjectWindow.twObservations.resizeRowsToContents()

                # configuration of behaviours
                if newProjectWindow.pj[ETHOGRAM]:
                    for i in sorted_keys(newProjectWindow.pj[ETHOGRAM]):
                        newProjectWindow.twBehaviors.setRowCount(newProjectWindow.twBehaviors.rowCount() + 1)
                        for field in behavioursFields:
                            item = QTableWidgetItem()
                            if field == TYPE:
                                item.setText(DEFAULT_BEHAVIOR_TYPE)
                            if field in newProjectWindow.pj[ETHOGRAM][i]:
                                item.setText(str(newProjectWindow.pj[ETHOGRAM][i][field]))  # str for modifiers dict
                            else:
                                item.setText("")
                            if field in [TYPE, "category", "excluded", "coding map", "modifiers"]:
                                item.setFlags(Qt.ItemIsEnabled)
                                item.setBackground(QColor(230, 230, 230))

                            newProjectWindow.twBehaviors.setItem(newProjectWindow.twBehaviors.rowCount() - 1,
                                                                 behavioursFields[field], item)

                # load independent variables
                if INDEPENDENT_VARIABLES in newProjectWindow.pj:
                    for i in sorted_keys(newProjectWindow.pj[INDEPENDENT_VARIABLES]):
                        newProjectWindow.twVariables.setRowCount(newProjectWindow.twVariables.rowCount() + 1)
                        for idx, field in enumerate(tw_indVarFields):
                            item = QTableWidgetItem("")
                            if field in newProjectWindow.pj[INDEPENDENT_VARIABLES][i]:
                                item.setText(newProjectWindow.pj[INDEPENDENT_VARIABLES][i][field])

                            newProjectWindow.twVariables.setItem(newProjectWindow.twVariables.rowCount() - 1, idx, item)

                    newProjectWindow.twVariables.resizeColumnsToContents()

                # behaviors coding map
                if BEHAVIORS_CODING_MAP in newProjectWindow.pj:
                    for bcm in newProjectWindow.pj[BEHAVIORS_CODING_MAP]:
                        newProjectWindow.twBehavCodingMap.setRowCount(newProjectWindow.twBehavCodingMap.rowCount() + 1)
                        newProjectWindow.twBehavCodingMap.setItem(newProjectWindow.twBehavCodingMap.rowCount() - 1, 0,
                                                                  QTableWidgetItem(bcm["name"]))
                        codes = ", ".join([bcm["areas"][idx]["code"] for idx in bcm["areas"]])
                        newProjectWindow.twBehavCodingMap.setItem(newProjectWindow.twBehavCodingMap.rowCount() - 1, 1,
                                                                  QTableWidgetItem(codes))

                # time converters
                if CONVERTERS in newProjectWindow.pj:
                    newProjectWindow.converters = newProjectWindow.pj[CONVERTERS]
                    newProjectWindow.load_converters_in_table()

            newProjectWindow.dteDate.setDisplayFormat("yyyy-MM-dd hh:mm:ss")

            if mode == NEW:
                newProjectWindow.pj = dict(EMPTY_PROJECT)

            # warning
            if mode == EDIT and self.pj[OBSERVATIONS]:

                if (dialog.MessageDialog(
                        programName,
                    ("Please note that editing the project may interfere with the coded events in your previous observations.<br>"
                     "For example modifying a behavior code, renaming a subject or modifying the modifiers sets "
                     "can unvalidate your previous observations.<br>"
                     "Remember to make a backup of your project."),
                    [CANCEL, "Edit"],
                ) == CANCEL):
                    return

            if newProjectWindow.exec_():  # button OK returns True

                if mode == NEW:
                    self.projectFileName = ""
                    self.projectChanged = True

                if mode == EDIT:
                    if not self.projectChanged:
                        self.projectChanged = dict(self.pj) != dict(newProjectWindow.pj)

                # retrieve project dict from window
                self.pj = dict(newProjectWindow.pj)
                self.project = True

                # time format
                if newProjectWindow.rbSeconds.isChecked():
                    self.timeFormat = S

                if newProjectWindow.rbHMS.isChecked():
                    self.timeFormat = HHMMSS

                # configuration
                if newProjectWindow.lbObservationsState.text() != "":
                    QMessageBox.warning(self, programName, newProjectWindow.lbObservationsState.text())
                else:
                    # ethogram
                    self.load_behaviors_in_twEthogram([self.pj[ETHOGRAM][x][BEHAVIOR_CODE] for x in self.pj[ETHOGRAM]])
                    # subjects
                    self.load_subjects_in_twSubjects([self.pj[SUBJECTS][x][SUBJECT_NAME] for x in self.pj[SUBJECTS]])

                self.initialize_new_project()

                menu_options.update_menu(self)

            self.projectWindowGeometry = newProjectWindow.saveGeometry()

            del newProjectWindow

        except Exception:
            dialog.error_message2()

    def save_project_json(self, projectFileName):
        """
        save project to JSON file
        convert Decimal type in float

        Args:
            projectFileName (str): path of project to save

        Returns:
            str:
        """

        logging.debug(f"init save_project_json function {projectFileName}")

        if self.save_project_json_started:
            logging.warning(f"Function save_project_json already launched")
            return

        self.save_project_json_started = True

        self.pj["project_format_version"] = project_format_version

        try:
            if projectFileName.endswith(".boris.gz"):
                with gzip.open(projectFileName, mode="wt", encoding="utf-8") as f_out:
                    f_out.write(json.dumps(self.pj, default=decimal_default))
            else:  # .boris and other extensions
                with open(projectFileName, "w") as f_out:
                    # f_out.write(json.dumps(self.pj, indent=1, separators=(",", ":"), default=decimal_default))
                    f_out.write(json.dumps(self.pj, default=decimal_default))

            self.projectChanged = False
            self.save_project_json_started = False

            logging.debug(f"end save_project_json function")
            return 0

        except PermissionError:
            QMessageBox.critical(
                None,
                programName,
                f"Permission denied to save the project file. Try another directory",
                QMessageBox.Ok | QMessageBox.Default,
                QMessageBox.NoButton,
            )
            self.save_project_json_started = False
            return 1

        except Exception:
            dialog.error_message2()

            self.save_project_json_started = False
            return 2

    def save_project_as_activated(self):
        """
        save current project asking for a new file name
        """
        logging.debug("function: save_project_as_activated")

        project_new_file_name, filtr = QFileDialog().getSaveFileName(
            self,
            "Save project as",
            os.path.dirname(self.projectFileName),
            ("Project files (*.boris);;"
             "Compressed project files (*.boris.gz);;"
             "All files (*)"),
        )

        if not project_new_file_name:
            return "Not saved"
        else:
            # add .boris if filter is .boris
            if filtr == "Project files (*.boris)" and os.path.splitext(project_new_file_name)[1] != ".boris":
                if project_new_file_name.endswith(".boris.gz"):
                    project_new_file_name = os.path.splitext(os.path.splitext(project_new_file_name)[0])[0]
                project_new_file_name += ".boris"
                # check if file name with extension already exists
                if pathlib.Path(project_new_file_name).is_file():
                    if (dialog.MessageDialog(programName, f"The file {project_new_file_name} already exists.",
                                             [CANCEL, OVERWRITE]) == CANCEL):
                        return "Not saved"
            # add .boris.gz if filter is .boris.gz
            if (filtr == "Compressed project files (*.boris.gz)" and
                    os.path.splitext(project_new_file_name)[1] != ".boris.gz"):
                if project_new_file_name.endswith(".boris"):
                    project_new_file_name = os.path.splitext(project_new_file_name)[0]
                project_new_file_name += ".boris.gz"
                # check if file name with extension already exists
                if pathlib.Path(project_new_file_name).is_file():
                    if (dialog.MessageDialog(programName, f"The file {project_new_file_name} already exists.",
                                             [CANCEL, OVERWRITE]) == CANCEL):
                        return "Not saved"

            if self.save_project_json(project_new_file_name) == 0:
                self.projectFileName = project_new_file_name
            else:
                return "Not saved"

    def save_project_activated(self):
        """
        save current project
        """
        logging.debug("function: save project activated")
        logging.debug(f"Project file name: {self.projectFileName}")

        if not self.projectFileName:
            if not self.pj["project_name"]:
                txt = "NONAME.boris"
            else:
                txt = self.pj["project_name"] + ".boris"
            os.chdir(os.path.expanduser("~"))

            self.projectFileName, filtr = QFileDialog().getSaveFileName(
                self,
                "Save project",
                txt,
                ("Project files (*.boris);;"
                 "Compressed project files (*.boris.gz);;"
                 "All files (*)"),
            )

            if not self.projectFileName:
                return "not saved"

            # add .boris if filter = 'Projects file (*.boris)'
            if filtr == "Project files (*.boris)" and os.path.splitext(self.projectFileName)[1] != ".boris":
                if self.projectFileName.endswith(".boris.gz"):
                    self.projectFileName = os.path.splitext(os.path.splitext(self.projectFileName)[0])[0]
                self.projectFileName += ".boris"
                # check if file name with extension already exists
                if pathlib.Path(self.projectFileName).is_file():
                    if (dialog.MessageDialog(programName, f"The file {self.projectFileName} already exists.",
                                             [CANCEL, OVERWRITE]) == CANCEL):
                        self.projectFileName = ""
                        return ""

            # add .boris.gz if filter is .boris.gz
            if (filtr == "Compressed project files (*.boris.gz)" and
                    os.path.splitext(self.projectFileName)[1] != ".boris.gz"):
                if self.projectFileName.endswith(".boris"):
                    self.projectFileName = os.path.splitext(self.projectFileName)[0]

                self.projectFileName += ".boris.gz"
                # check if file name with extension already exists
                if pathlib.Path(self.projectFileName).is_file():
                    if (dialog.MessageDialog(programName, f"The file {self.projectFileName} already exists.",
                                             [CANCEL, OVERWRITE]) == CANCEL):
                        self.projectFileName = ""
                        return ""

            r = self.save_project_json(self.projectFileName)
            if r:
                self.projectFileName = ""
                return r
        else:
            return self.save_project_json(self.projectFileName)

        return ""

    def liveTimer_out(self):
        """
        timer for live observation
        """

        if self.pj[OBSERVATIONS][self.observationId].get(START_FROM_CURRENT_TIME, False):
            current_time = utilities.seconds_of_day(datetime.datetime.now())
        elif self.pj[OBSERVATIONS][self.observationId].get(START_FROM_CURRENT_EPOCH_TIME, False):
            current_time = time.time()
        else:
            current_time = self.getLaps()

        self.lb_current_media_time.setText(self.convertTime(current_time))

        # extract State events
        self.currentStates = {}
        # add states for no focal subject

        self.currentStates = utilities.get_current_states_modifiers_by_subject(
            utilities.state_behavior_codes(self.pj[ETHOGRAM]),
            self.pj[OBSERVATIONS][self.observationId][EVENTS],
            dict(self.pj[SUBJECTS], **{"": {
                SUBJECT_NAME: ""
            }}),
            current_time,
            include_modifiers=True,
        )

        # show current states
        # index of current subject
        idx = self.subject_name_index[self.currentSubject] if self.currentSubject else ""
        self.lbCurrentStates.setText(", ".join(self.currentStates[idx]))
        self.show_current_states_in_subjects_table()

        self.plot_timer_out()

        # check scan sampling
        if self.pj[OBSERVATIONS][self.observationId].get(SCAN_SAMPLING_TIME, 0):
            if int(current_time) % self.pj[OBSERVATIONS][self.observationId][SCAN_SAMPLING_TIME] == 0:
                self.beep("beep")
                self.liveTimer.stop()
                self.pb_live_obs.setText("Live observation stopped (scan sampling)")

        # observation time interval
        if self.pj[OBSERVATIONS][self.observationId].get(OBSERVATION_TIME_INTERVAL, [0, 0])[1]:
            if current_time >= self.pj[OBSERVATIONS][self.observationId].get(OBSERVATION_TIME_INTERVAL, [0, 0])[1]:
                self.beep("beep")
                self.liveTimer.stop()
                self.pb_live_obs.setText("Live observation finished")

    def start_live_observation(self):
        """
        activate the live observation mode (without media file)
        """

        logging.debug(f"start live observation, self.liveObservationStarted: {self.liveObservationStarted}")

        if "scan sampling" in self.pb_live_obs.text():
            self.pb_live_obs.setText("Stop live observation")
            self.liveTimer.start(100)
            return

        if self.liveObservationStarted:
            # stop live obs
            self.pb_live_obs.setText("Start live observation")
            self.liveStartTime = None
            self.liveTimer.stop()

            if self.timeFormat == HHMMSS:
                if self.pj[OBSERVATIONS][self.observationId].get(START_FROM_CURRENT_TIME, False):
                    self.lb_current_media_time.setText(datetime.datetime.now().isoformat(" ").split(" ")[1][:12])
                elif self.pj[OBSERVATIONS][self.observationId].get(START_FROM_CURRENT_EPOCH_TIME, False):
                    self.lb_current_media_time.setText(datetime.datetime.fromtimestamp(time.time()))
                else:
                    self.lb_current_media_time.setText("00:00:00.000")

            if self.timeFormat == S:
                self.lb_current_media_time.setText("0.000")

        else:
            if self.twEvents.rowCount():
                if dialog.MessageDialog(programName, "Delete the current events?", [YES, NO]) == YES:
                    self.twEvents.setRowCount(0)
                    self.pj[OBSERVATIONS][self.observationId][EVENTS] = []
                self.projectChanged = True

            self.pb_live_obs.setText("Stop live observation")

            self.liveStartTime = QTime()
            # set to now
            self.liveStartTime.start()
            # start timer
            self.liveTimer.start(100)

        self.liveObservationStarted = not self.liveObservationStarted

    def create_subtitles(self):
        """
        create subtitles for selected observations, subjects and behaviors
        """

        result, selected_observations = self.selectObservations(MULTIPLE)
        if not selected_observations:
            return

        # check if state events are paired
        out = ""
        not_paired_obs_list = []
        for obsId in selected_observations:
            r, msg = project_functions.check_state_events_obs(obsId, self.pj[ETHOGRAM], self.pj[OBSERVATIONS][obsId],
                                                              self.timeFormat)

            if not r:
                out += f"Observation: <strong>{obsId}</strong><br>{msg}<br>"
                not_paired_obs_list.append(obsId)

        if out:
            out = "The observations with UNPAIRED state events will be removed from the plot<br><br>" + out
            self.results = dialog.Results_dialog()
            self.results.setWindowTitle(programName + " - Check selected observations")
            self.results.ptText.setReadOnly(True)
            self.results.ptText.appendHtml(out)
            self.results.pbSave.setVisible(False)
            self.results.pbCancel.setVisible(True)

            if not self.results.exec_():
                return

        selected_observations = [x for x in selected_observations if x not in not_paired_obs_list]
        if not selected_observations:
            return

        parameters = select_subj_behav.choose_obs_subj_behav_category(self, selected_observations, 0)
        if not parameters[SELECTED_SUBJECTS] or not parameters[SELECTED_BEHAVIORS]:
            return
        export_dir = QFileDialog().getExistingDirectory(
            self,
            "Choose a directory to save subtitles",
            os.path.expanduser("~"),
            options=QFileDialog(self).ShowDirsOnly,
        )
        if not export_dir:
            return
        ok, msg = project_functions.create_subtitles(self.pj, selected_observations, parameters, export_dir)
        if not ok:
            logging.critical(f"Error creating subtitles. {msg}")
            QMessageBox.critical(
                None,
                programName,
                f"Error creating subtitles: {msg}",
                QMessageBox.Ok | QMessageBox.Default,
                QMessageBox.NoButton,
            )

    def next_frame(self):
        """
        show next frame
        """
        for n_player, dw in enumerate(self.dw_player):
            dw.player.frame_step()
            self.plot_timer_out()
            for idx in self.plot_data:
                self.timer_plot_data_out(self.plot_data[idx])

            if self.geometric_measurements_mode:
                self.extract_frame(dw)

        if self.geometric_measurements_mode:
            self.redraw_measurements()

        self.actionPlay.setIcon(QIcon(":/play"))

    def previous_frame(self):
        """
        show previous frame
        """
        for n_player, dw in enumerate(self.dw_player):
            dw.player.frame_back_step()
            self.plot_timer_out()
            for idx in self.plot_data:
                self.timer_plot_data_out(self.plot_data[idx])

            if self.geometric_measurements_mode:
                self.extract_frame(dw)

        if self.geometric_measurements_mode:
            self.redraw_measurements()

        self.actionPlay.setIcon(QIcon(":/play"))

    def snapshot(self):
        """
        take snapshot of current video at current position
        snapshot is saved on media path
        """

        if self.pj[OBSERVATIONS][self.observationId][TYPE] in [MEDIA]:

            if self.playerType == VLC:

                for i, player in enumerate(self.dw_player):
                    if (str(i + 1) in self.pj[OBSERVATIONS][self.observationId][FILE] and
                            self.pj[OBSERVATIONS][self.observationId][FILE][str(i + 1)]):

                        p = pathlib.Path(
                            self.dw_player[0].player.playlist[self.dw_player[0].player.playlist_pos]["filename"])

                        snapshot_file_path = str(p.parent / f"{p.stem}_{player.player.time_pos}.png")

                        player.player.screenshot_to_file(snapshot_file_path)

    def zoom_level(self):
        """
        display dialog for zoom level
        """
        players_list = []
        for idx, dw in enumerate(self.dw_player):
            zoom_levels = []
            for choice in [2, 1, 0.5, 0.25]:
                zoom_levels.append((str(choice), "selected" if log2(choice) == dw.player.video_zoom else ""))
            players_list.append(("il", f"Player #{idx + 1}", zoom_levels))

        zl = dialog.Input_dialog("Select the zoom level", players_list)
        if not zl.exec_():
            return

        if ZOOM_LEVEL not in self.pj[OBSERVATIONS][self.observationId][MEDIA_INFO]:
            self.pj[OBSERVATIONS][self.observationId][MEDIA_INFO][ZOOM_LEVEL] = {}

        for idx, dw in enumerate(self.dw_player):
            if self.pj[OBSERVATIONS][self.observationId][MEDIA_INFO][ZOOM_LEVEL].get(
                    str(idx + 1), dw.player.video_zoom) != float(zl.elements[f"Player #{idx + 1}"].currentText()):
                dw.player.video_zoom = log2(float(zl.elements[f"Player #{idx + 1}"].currentText()))
                self.pj[OBSERVATIONS][self.observationId][MEDIA_INFO][ZOOM_LEVEL][str(idx + 1)] = float(
                    zl.elements[f"Player #{idx + 1}"].currentText())
                self.projectChanged = True

    def display_subtitles(self):
        """
        display dialog for subtitles display
        """
        players_list = []
        for idx, dw in enumerate(self.dw_player):
            if DISPLAY_MEDIA_SUBTITLES in self.pj[OBSERVATIONS][self.observationId][MEDIA_INFO]:
                default = self.pj[OBSERVATIONS][self.observationId][MEDIA_INFO][DISPLAY_MEDIA_SUBTITLES].get(
                    str(idx + 1), dw.player.sub_visibility)
            else:
                default = dw.player.sub_visibility
            players_list.append(("cb", f"Player #{idx + 1}", default))

        st = dialog.Input_dialog("Display subtitles", players_list)
        if not st.exec_():
            return

        if DISPLAY_MEDIA_SUBTITLES not in self.pj[OBSERVATIONS][self.observationId][MEDIA_INFO]:
            self.pj[OBSERVATIONS][self.observationId][MEDIA_INFO][DISPLAY_MEDIA_SUBTITLES] = {}

        for idx, dw in enumerate(self.dw_player):
            if (self.pj[OBSERVATIONS][self.observationId][MEDIA_INFO][DISPLAY_MEDIA_SUBTITLES].get(
                    str(idx + 1), dw.player.sub_visibility) != st.elements[f"Player #{idx + 1}"].isChecked()):
                dw.player.sub_visibility = st.elements[f"Player #{idx + 1}"].isChecked()
                self.pj[OBSERVATIONS][self.observationId][MEDIA_INFO][DISPLAY_MEDIA_SUBTITLES][str(
                    idx + 1)] = st.elements[f"Player #{idx + 1}"].isChecked()
                self.projectChanged = True

    def video_normalspeed_activated(self):
        """
        set playing speed at normal speed (1x)
        """

        if self.playerType == VLC and self.playMode == MPV:
            self.play_rate = 1
            for i, player in enumerate(self.dw_player):
                if (str(i + 1) in self.pj[OBSERVATIONS][self.observationId][FILE] and
                        self.pj[OBSERVATIONS][self.observationId][FILE][str(i + 1)]):
                    player.player.speed = self.play_rate

            self.lbSpeed.setText(f"x{self.play_rate:.3f}")

            logging.debug(f"play rate: {self.play_rate:.3f}")

    def video_faster_activated(self):
        """
        increase playing speed by play_rate_step value
        """

        if self.playerType == VLC and self.playMode == MPV:

            if self.play_rate + self.play_rate_step <= 60:
                self.play_rate += self.play_rate_step
                for i, player in enumerate(self.dw_player):
                    if (str(i + 1) in self.pj[OBSERVATIONS][self.observationId][FILE] and
                            self.pj[OBSERVATIONS][self.observationId][FILE][str(i + 1)]):
                        player.player.speed = self.play_rate
                self.lbSpeed.setText(f"x{self.play_rate:.3f}")

                logging.debug(f"play rate: {self.play_rate:.3f}")

    def video_slower_activated(self):
        """
        decrease playing speed by play_rate_step value
        """

        if self.playerType == VLC and self.playMode == MPV:

            if self.play_rate - self.play_rate_step >= 0.1:
                self.play_rate -= self.play_rate_step

                for i, player in enumerate(self.dw_player):
                    player.player.speed = round(self.play_rate, 3)

                self.lbSpeed.setText(f"x{self.play_rate:.3f}")

                logging.debug(f"play rate: {self.play_rate:.3f}")

    def add_event(self):
        """
        manually add event to observation
        """

        if not self.observationId:
            self.no_observation()
            return

        if self.pause_before_addevent:
            # pause media
            if self.pj[OBSERVATIONS][self.observationId][TYPE] in [MEDIA]:
                if self.playerType == VLC:
                    if self.playMode == MPV:
                        memState = self.is_playing()
                        if memState:
                            self.pause_video()

        laps = self.getLaps()

        if not self.pj[ETHOGRAM]:
            QMessageBox.warning(self, programName, "The ethogram is not set!")
            return

        editWindow = DlgEditEvent(
            logging.getLogger().getEffectiveLevel(),
            time_value=0,
            current_time=0,
            time_format=self.timeFormat,
            show_set_current_time=False,
        )
        editWindow.setWindowTitle("Add a new event")

        sortedSubjects = [""] + sorted([self.pj[SUBJECTS][x][SUBJECT_NAME] for x in self.pj[SUBJECTS]])

        editWindow.cobSubject.addItems(sortedSubjects)
        editWindow.cobSubject.setCurrentIndex(editWindow.cobSubject.findText(self.currentSubject, Qt.MatchFixedString))

        sortedCodes = sorted([self.pj[ETHOGRAM][x][BEHAVIOR_CODE] for x in self.pj[ETHOGRAM]])

        editWindow.cobCode.addItems(sortedCodes)

        if editWindow.exec_():  # button OK

            newTime = editWindow.time_widget.get_time()

            for idx in self.pj[ETHOGRAM]:
                if self.pj[ETHOGRAM][idx][BEHAVIOR_CODE] == editWindow.cobCode.currentText():

                    event = self.full_event(idx)

                    event["subject"] = editWindow.cobSubject.currentText()
                    if editWindow.leComment.toPlainText():
                        event["comment"] = editWindow.leComment.toPlainText()

                    self.writeEvent(event, newTime)
                    break

            self.currentStates = utilities.get_current_states_modifiers_by_subject(
                utilities.state_behavior_codes(self.pj[ETHOGRAM]),
                self.pj[OBSERVATIONS][self.observationId][EVENTS],
                dict(self.pj[SUBJECTS], **{"": {
                    "name": ""
                }}),  # add no focal subject
                newTime,
                include_modifiers=True,
            )

            subject_idx = self.subject_name_index[self.currentSubject] if self.currentSubject else ""
            self.lbCurrentStates.setText(", ".join(self.currentStates[subject_idx]))

            self.show_current_states_in_subjects_table()

        if self.pause_before_addevent:
            # restart media
            if self.pj[OBSERVATIONS][self.observationId][TYPE] in [MEDIA]:
                if self.playerType == VLC:
                    if self.playMode == FFMPEG:
                        if memState:
                            self.play_video()
                    elif self.playMode == MPV:
                        if memState:
                            self.play_video()

    def run_event_outside(self):
        """
        run external prog with events information
        """
        QMessageBox.warning(self, programName, "Function not yet implemented")
        return

        if not self.observationId:
            self.no_observation()
            return

        if self.twEvents.selectedItems():
            row_s = self.twEvents.selectedItems()[0].row()
            row_e = self.twEvents.selectedItems()[-1].row()
            eventtime_s = self.pj[OBSERVATIONS][self.observationId][EVENTS][row_s][0]
            eventtime_e = self.pj[OBSERVATIONS][self.observationId][EVENTS][row_e][0]

            durations = []  # in seconds

            # TODO: check for 2nd player
            for mediaFile in self.pj[OBSERVATIONS][self.observationId][FILE][PLAYER1]:
                durations.append(self.pj[OBSERVATIONS][self.observationId][MEDIA_INFO]["length"][mediaFile])

            mediaFileIdx_s = [idx1 for idx1, x in enumerate(durations) if eventtime_s >= sum(durations[0:idx1])][-1]
            media_path_s = self.pj[OBSERVATIONS][self.observationId][FILE][PLAYER1][mediaFileIdx_s]

            mediaFileIdx_e = [idx1 for idx1, x in enumerate(durations) if eventtime_e >= sum(durations[0:idx1])][-1]
            media_path_e = self.pj[OBSERVATIONS][self.observationId][FILE][PLAYER1][mediaFileIdx_e]

            # calculate time for current media file in case of many queued media files

            print(mediaFileIdx_s)
            print(type(eventtime_s))
            print(durations)

            eventtime_onmedia_s = round(eventtime_s - float2decimal(sum(durations[0:mediaFileIdx_s])), 3)
            eventtime_onmedia_e = round(eventtime_e - float2decimal(sum(durations[0:mediaFileIdx_e])), 3)

            print(row_s, media_path_s, eventtime_s, eventtime_onmedia_s)
            print(self.pj[OBSERVATIONS][self.observationId][EVENTS][row_s])

            print(row_e, media_path_e, eventtime_e, eventtime_onmedia_e)
            print(self.pj[OBSERVATIONS][self.observationId][EVENTS][row_e])

            if media_path_s != media_path_e:
                print("events are located on 2 different media files")
                return

            media_path = media_path_s

            # example of external command defined in environment:
            # export BORISEXTERNAL="myprog -i {MEDIA_PATH} -s {START_S} -e {END_S} {DURATION_MS} --other"

            if "BORISEXTERNAL" in os.environ:
                external_command_template = os.environ["BORISEXTERNAL"]
            else:
                print("BORISEXTERNAL env var not defined")
                return

            external_command = external_command_template.format(
                OBS_ID=self.observationId,
                MEDIA_PATH=f'"{media_path}"',
                MEDIA_BASENAME=f'"{os.path.basename(media_path)}"',
                START_S=eventtime_onmedia_s,
                END_S=eventtime_onmedia_e,
                START_MS=eventtime_onmedia_s * 1000,
                END_MS=eventtime_onmedia_e * 1000,
                DURATION_S=eventtime_onmedia_e - eventtime_onmedia_s,
                DURATION_MS=(eventtime_onmedia_e - eventtime_onmedia_s) * 1000,
            )

            print(external_command)
            """
            p = subprocess.Popen(external_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
            """
            """
            if eventtimeS == eventtimeE:
                q = []
            else:
                durationsec = eventtimeE-eventtimeS
                q = ["--durationmsec",str(int(durationsec*1000))]
            args = [ex, "-f",os.path.abspath(fn),"--seekmsec",str(int(eventtimeS*1000)),*q,*("--size 1 --track 1 --redetect 100")
            .split(" ")]
            if os.path.split(fn)[1].split("_")[0] in set(["A1","A2","A3","A4","A5","A6","A7","A8","A9","A10"]):
                args.append("--flip")
                args.append("2")
            print (os.path.split(fn)[1].split("_")[0])
            print ("running",ex,"with",args,"in",os.path.split(ex)[0])
            #pid = subprocess.Popen(args,executable=ex,cwd=os.path.split(ex)[0])
            """

    def show_all_events(self):
        """
        show all events (disable filter)
        """
        self.filtered_subjects = []
        self.filtered_behaviors = []
        self.loadEventsInTW(self.observationId)
        self.dwObservations.setWindowTitle(f"Events for “{self.observationId}” observation")

    def filter_events(self):
        """
        filter coded events and subjects
        """
        parameters = select_subj_behav.choose_obs_subj_behav_category(
            self,
            [],  # empty selection of observations for selecting all subjects and behaviors
            maxTime=0,
            flagShowIncludeModifiers=False,
            flagShowExcludeBehaviorsWoEvents=False,
            by_category=False,
            show_time=False,
        )

        self.filtered_subjects = parameters["selected subjects"][:]
        if NO_FOCAL_SUBJECT in self.filtered_subjects:
            self.filtered_subjects.append("")
        self.filtered_behaviors = parameters["selected behaviors"][:]

        logging.debug(f"self.filtered_behaviors: {self.filtered_behaviors}")

        self.loadEventsInTW(self.observationId)
        self.dwObservations.setWindowTitle(f"Events for “{self.observationId}” observation (filtered)")

    def no_media(self):
        QMessageBox.warning(self, programName, "There is no media available")

    def no_project(self):
        QMessageBox.warning(self, programName, "There is no project")

    def no_observation(self):
        QMessageBox.warning(self, programName, "There is no current observation")

    def twEthogram_doubleClicked(self):
        """
        add event by double-clicking in ethogram list
        """
        if self.observationId:
            if self.playerType == VIEWER:
                QMessageBox.critical(
                    self,
                    programName,
                    ("The current observation is opened in VIEW mode.\n"
                     "It is not allowed to log events in this mode."),
                )
                return

            if self.twEthogram.selectedIndexes():
                ethogram_row = self.twEthogram.selectedIndexes()[0].row()
                code = self.twEthogram.item(ethogram_row, 1).text()

                ethogram_idx = [x for x in self.pj[ETHOGRAM] if self.pj[ETHOGRAM][x][BEHAVIOR_CODE] == code][0]

                event = self.full_event(ethogram_idx)
                self.writeEvent(event, self.getLaps())
        else:
            self.no_observation()

    def actionUser_guide_triggered(self):
        """
        open user guide URL if it exists otherwise open user guide URL
        """
        userGuideFile = os.path.dirname(os.path.realpath(__file__)) + "/boris_user_guide.pdf"
        if os.path.isfile(userGuideFile):
            if sys.platform.startswith("linux"):
                subprocess.call(["xdg-open", userGuideFile])
            else:
                os.startfile(userGuideFile)
        else:
            QDesktopServices.openUrl(QUrl("http://boris.readthedocs.org"))

    def click_signal_from_behaviors_coding_map(self, bcm_name, behavior_codes_list):
        """
        handle click signal from BehaviorsCodingMapWindowClass widget
        """

        for code in behavior_codes_list:
            try:
                behavior_idx = [key for key in self.pj[ETHOGRAM] if self.pj[ETHOGRAM][key][BEHAVIOR_CODE] == code][0]
            except Exception:
                QMessageBox.critical(self, programName,
                                     f"The code <b>{code}</b> of behavior coding map does not exist in ethogram.")
                return

            event = self.full_event(behavior_idx)
            self.writeEvent(event, self.getLaps())

    def keypress_signal_from_behaviors_coding_map(self, event):
        """
        receive signal from behaviors coding map
        """
        self.keyPressEvent(event)

    """
    def close_behaviors_coding_map(self, coding_map_name):

        try:

            logging.debug(f"deleting behavior coding map: {coding_map_name} {self.bcm_dict[coding_map_name]}")

            # del self.bcm_dict[coding_map_name]
            self.bcm_dict[coding_map_name].deleteLater()
        except Exception:
            dialog.error_message2()
    """

    def add_image_overlay(self):
        """
        add an image overlay on video
        """

        logging.debug(f"function add_image_overlay")

        try:
            w = dialog.Video_overlay_dialog()
            items = list([f"Player #{i + 1}" for i, _ in enumerate(self.dw_player)])
            w.cb_player.addItems(items)
            if not w.exec_():
                return

            idx = w.cb_player.currentIndex()

            if OVERLAY not in self.pj[OBSERVATIONS][self.observationId][MEDIA_INFO]:
                self.pj[OBSERVATIONS][self.observationId][MEDIA_INFO][OVERLAY] = {}
            self.pj[OBSERVATIONS][self.observationId][MEDIA_INFO][OVERLAY][str(idx + 1)] = {
                "file name": w.le_file_path.text(),
                "overlay position": w.le_overlay_position.text(),
                "transparency": w.sb_overlay_transparency.value(),
            }
            self.overlays[idx] = self.dw_player[idx].player.create_image_overlay()
            self.projectChanged = True
            self.resize_dw(idx)

        except Exception:
            logging.debug("error in add_image_overlay function")

    def remove_image_overlay(self):
        """
        remove image overlay from all players
        """
        keys_to_delete = []
        for n_player in self.pj[OBSERVATIONS][self.observationId][MEDIA_INFO].get(OVERLAY, {}):
            keys_to_delete.append(n_player)
            try:
                self.overlays[int(n_player) - 1].remove()
            except:
                logging.debug("error removing overlay")
        for n_player in keys_to_delete:
            del self.pj[OBSERVATIONS][self.observationId][MEDIA_INFO][OVERLAY][n_player]

    def video_slider_sliderMoved(self):
        """
        media position slider moved
        adjust media position
        """

        logging.debug(f"video_slider moved: {self.video_slider.value() / (slider_maximum - 1)}")

        if self.pj[OBSERVATIONS][self.observationId][TYPE] in [MEDIA]:
            if self.playerType == VLC:

                self.user_move_slider = True
                sliderPos = self.video_slider.value() / (slider_maximum - 1)
                videoPosition = sliderPos * self.dw_player[0].player.duration
                self.dw_player[0].player.command("seek", str(videoPosition), "absolute")

    def video_slider_sliderReleased(self):
        """
        adjust frame when slider is moved by user
        """

        logging.debug(f"video_slider released: {self.video_slider.value() / (slider_maximum - 1)}")
        self.user_move_slider = False

    def get_events_current_row(self):
        """
        get events current row corresponding to video/frame-by-frame position
        paint twEvents with tracking cursor
        scroll to corresponding event
        """

        global ROW

        if self.pj[OBSERVATIONS][self.observationId][EVENTS]:
            ct = self.getLaps()
            if ct >= self.pj[OBSERVATIONS][self.observationId][EVENTS][-1][0]:
                ROW = len(self.pj[OBSERVATIONS][self.observationId][EVENTS])
            else:
                cr_list = [
                    idx for idx, x in enumerate(self.pj[OBSERVATIONS][self.observationId][EVENTS][:-1])
                    if x[0] <= ct and self.pj[OBSERVATIONS][self.observationId][EVENTS][idx + 1][0] > ct
                ]

                if cr_list:
                    ROW = cr_list[0]
                    if not self.trackingCursorAboveEvent:
                        ROW += 1
                else:
                    ROW = -1

            self.twEvents.setItemDelegate(StyledItemDelegateTriangle(self.twEvents))

            if self.twEvents.item(ROW, 0):
                self.twEvents.scrollToItem(self.twEvents.item(ROW, 0), QAbstractItemView.EnsureVisible)

    def show_current_states_in_subjects_table(self):
        """
        show current state(s) for all subjects (including "No focal subject") in subjects table
        """

        for i in range(self.twSubjects.rowCount()):
            try:
                if self.twSubjects.item(i, 1).text() == NO_FOCAL_SUBJECT:
                    self.twSubjects.item(i, len(subjectsFields)).setText(",".join(self.currentStates[""]))
                else:
                    self.twSubjects.item(i, len(subjectsFields)).setText(",".join(
                        self.currentStates[self.subject_name_index[self.twSubjects.item(i, 1).text()]]))
            except KeyError:
                self.twSubjects.item(i, len(subjectsFields)).setText("")

    def sync_time(self, n_player: int, new_time: float) -> None:
        """
        synchronize player n_player to time new_time
        if required load the media file corresponding to cumulative time in player

        Args:
            n_player (int): player
            new_time (int): new time in ms
        """

        if self.dw_player[n_player].player.playlist_count == 1:

            if self.pj[OBSERVATIONS][self.observationId][MEDIA_INFO]["offset"][str(n_player + 1)]:

                if self.pj[OBSERVATIONS][self.observationId][MEDIA_INFO]["offset"][str(n_player + 1)] > 0:

                    if new_time < self.pj[OBSERVATIONS][self.observationId][MEDIA_INFO]["offset"][str(n_player + 1)]:
                        # hide video if time < offset
                        self.dw_player[n_player].stack.setCurrentIndex(1)
                    else:

                        if new_time - Decimal(self.pj[OBSERVATIONS][self.observationId][MEDIA_INFO]["offset"][str(
                                n_player + 1)]) > sum(self.dw_player[n_player].media_durations):
                            # hide video if required time > video time + offset
                            self.dw_player[n_player].stack.setCurrentIndex(1)
                        else:
                            # show video
                            self.dw_player[n_player].stack.setCurrentIndex(0)

                            self.seek_mediaplayer(
                                new_time - Decimal(
                                    self.pj[OBSERVATIONS][self.observationId][MEDIA_INFO]["offset"][str(n_player + 1)]),
                                player=n_player,
                            )

                elif self.pj[OBSERVATIONS][self.observationId][MEDIA_INFO]["offset"][str(n_player + 1)] < 0:

                    if new_time - Decimal(
                            self.pj[OBSERVATIONS][self.observationId][MEDIA_INFO]["offset"][str(n_player + 1)]) > sum(
                                self.dw_player[n_player].media_durations):
                        # hide video if required time > video time + offset
                        self.dw_player[n_player].stack.setCurrentIndex(1)
                    else:
                        self.dw_player[n_player].stack.setCurrentIndex(0)
                        self.seek_mediaplayer(
                            new_time -
                            Decimal(self.pj[OBSERVATIONS][self.observationId][MEDIA_INFO]["offset"][str(n_player + 1)]),
                            player=n_player,
                        )

            else:  # no offset
                self.seek_mediaplayer(new_time, player=n_player)

        elif self.dw_player[n_player].player.playlist_count > 1:

            if new_time < sum(self.dw_player[n_player].media_durations):
                """media_idx = self.dw_player[n_player].media_list.index_of_item(self.dw_player[n_player].mediaplayer.get_media())"""
                media_idx = self.dw_player[n_player].player.playlist_pos

                if (sum(self.dw_player[n_player].media_durations[0:media_idx]) < new_time < sum(
                        self.dw_player[n_player].media_durations[0:media_idx + 1])):
                    # in current media
                    logging.debug(f"{n_player + 1} correct media")
                    self.seek_mediaplayer(new_time -
                                          sum(self.dw_player[n_player].media_durations[0:media_idx], player=n_player))
                else:

                    logging.debug(f"{n_player + 1} not correct media")

                    flag_paused = self.dw_player[n_player].player.pause
                    tot = 0
                    for idx, d in enumerate(self.dw_player[n_player].media_durations):
                        if tot <= new_time < tot + d:

                            self.dw_player[n_player].player.playing_pos = idx
                            if flag_paused:
                                self.dw_player[n_player].player.pause = True
                            self.seek_mediaplayer(new_time - self.dw_player[n_player].media_durations[0:idx],
                                                  player=n_player)
                            break
                        tot += d

            else:  # end of media list

                logging.debug(f"{n_player + 1} end of media")
                self.dw_player[n_player].player.playlist_pos = self.dw_player[n_player].player.playlist_count - 1
                self.seek_mediaplayer(self.dw_player[n_player].media_durations[-1], player=n_player)

    def timer_out2(self, value, scroll_slider=True):
        """
        indicate the video current position and total length for MPV player
        scroll video slider to video position
        Time offset is NOT added!
        """

        try:
            cumulative_time_pos = self.getLaps()

            if value is None:
                current_media_time_pos = 0
            else:
                current_media_time_pos = value

            current_media_frame = round(value * self.dw_player[0].player.container_fps) + 1

            # observation time interval
            if self.pj[OBSERVATIONS][self.observationId].get(OBSERVATION_TIME_INTERVAL, [0, 0])[1]:
                if (cumulative_time_pos >= self.pj[OBSERVATIONS][self.observationId].get(
                        OBSERVATION_TIME_INTERVAL, [0, 0])[1]):
                    if self.is_playing():
                        self.pause_video()
                        self.beep("beep")

            if self.beep_every:
                if cumulative_time_pos % (self.beep_every) <= 1:
                    self.beep("beep")

            # highlight current event in tw events and scroll event list
            self.get_events_current_row()

            ct0 = cumulative_time_pos

            if self.dw_player[0].player.time_pos is not None:

                for n_player in range(1, len(self.dw_player)):

                    ct = self.getLaps(n_player=n_player)

                    # sync players 2..8 if time diff >= 1 s
                    if (abs(ct0 -
                            (ct + Decimal(self.pj[OBSERVATIONS][self.observationId][MEDIA_INFO]["offset"][str(n_player +
                                                                                                              1)]))) >=
                            1):
                        self.sync_time(n_player, ct0)  # self.seek_mediaplayer(ct0, n_player)

            currentTimeOffset = Decimal(cumulative_time_pos + self.pj[OBSERVATIONS][self.observationId][TIME_OFFSET])

            all_media_duration = sum(self.dw_player[0].media_durations) / 1000
            mediaName = ""
            current_media_duration = self.dw_player[0].player.duration  # mediaplayer_length
            self.mediaTotalLength = current_media_duration

            # current state(s)
            # extract State events
            StateBehaviorsCodes = utilities.state_behavior_codes(self.pj[ETHOGRAM])
            self.currentStates = {}

            # index of current subject
            subject_idx = self.subject_name_index[self.currentSubject] if self.currentSubject else ""

            self.currentStates = utilities.get_current_states_modifiers_by_subject(
                StateBehaviorsCodes,
                self.pj[OBSERVATIONS][self.observationId][EVENTS],
                dict(self.pj[SUBJECTS], **{"": {
                    "name": ""
                }}),
                currentTimeOffset,
                include_modifiers=True,
            )

            self.lbCurrentStates.setText(", ".join(self.currentStates[subject_idx]))

            # show current states in subjects table
            self.show_current_states_in_subjects_table()

            if self.dw_player[0].player.playlist_pos is not None:
                current_media_name = pathlib.Path(
                    self.dw_player[0].player.playlist[self.dw_player[0].player.playlist_pos]["filename"]).name
            else:
                current_media_name = ""
            playlist_length = len(self.dw_player[0].player.playlist)

            # update media info
            msg = ""

            if self.dw_player[0].player.time_pos is not None:

                msg = (f"{current_media_name}: <b>{self.convertTime(current_media_time_pos)} / "
                       f"{self.convertTime(current_media_duration)}</b> frame: {current_media_frame}")

                if self.dw_player[0].player.playlist_count > 1:
                    msg += (f"<br>Total: <b>{self.convertTime(cumulative_time_pos)} / "
                            f"{self.convertTime(all_media_duration)}</b>")

                self.lb_player_status.setText("Player paused" if self.dw_player[0].player.pause else "")

                msg += f"<br>media #{self.dw_player[0].player.playlist_pos + 1} / {playlist_length}"

            else:  # player ended
                # self.timer.stop()
                self.plot_timer.stop()

                # stop all timer for plotting data
                for data_timer in self.ext_data_timer_list:
                    data_timer.stop()

                self.actionPlay.setIcon(QIcon(":/play"))

            if msg:
                # show time
                self.lb_current_media_time.setText(msg)

                # set video scroll bar
                if scroll_slider and not self.user_move_slider:
                    self.video_slider.setValue(current_media_time_pos / current_media_duration * (slider_maximum - 1))

        except Exception:
            error_type, error_file_name, error_lineno = utilities.error_info(sys.exc_info())
            logging.critical(f"Error during time_out2: {error_type} in {error_file_name} at line #{error_lineno}")

    def load_behaviors_in_twEthogram(self, behaviorsToShow):
        """
        fill ethogram table with ethogram from pj
        """

        self.twEthogram.setRowCount(0)
        if self.pj[ETHOGRAM]:
            for idx in sorted_keys(self.pj[ETHOGRAM]):
                if self.pj[ETHOGRAM][idx][BEHAVIOR_CODE] in behaviorsToShow:
                    self.twEthogram.setRowCount(self.twEthogram.rowCount() + 1)
                    for col in sorted(behav_fields_in_mainwindow.keys()):
                        field = behav_fields_in_mainwindow[col]
                        self.twEthogram.setItem(self.twEthogram.rowCount() - 1, col,
                                                QTableWidgetItem(str(self.pj[ETHOGRAM][idx][field])))
        if self.twEthogram.rowCount() < len(self.pj[ETHOGRAM].keys()):
            self.dwEthogram.setWindowTitle(
                f"Ethogram (filtered {self.twEthogram.rowCount()}/{len(self.pj[ETHOGRAM].keys())})")

            if self.observationId:
                self.pj[OBSERVATIONS][self.observationId]["filtered behaviors"] = behaviorsToShow
        else:
            self.dwEthogram.setWindowTitle("Ethogram")

    def load_subjects_in_twSubjects(self, subjects_to_show):
        """
        fill subjects table widget with subjects from subjects_to_show

        Args:
            subjects_to_show (list): list of subject to be shown
        """

        self.subject_name_index = {}

        # no focal subject
        self.twSubjects.setRowCount(1)
        for idx, s in enumerate(["", NO_FOCAL_SUBJECT, "", ""]):
            self.twSubjects.setItem(0, idx, QTableWidgetItem(s))

        if self.pj[SUBJECTS]:
            for idx in sorted_keys(self.pj[SUBJECTS]):

                self.subject_name_index[self.pj[SUBJECTS][idx][SUBJECT_NAME]] = idx

                if self.pj[SUBJECTS][idx][SUBJECT_NAME] in subjects_to_show:

                    self.twSubjects.setRowCount(self.twSubjects.rowCount() + 1)

                    for idx2, field in enumerate(subjectsFields):
                        self.twSubjects.setItem(self.twSubjects.rowCount() - 1, idx2,
                                                QTableWidgetItem(self.pj[SUBJECTS][idx][field]))

                    # add cell for current state(s) after last subject field
                    self.twSubjects.setItem(self.twSubjects.rowCount() - 1, len(subjectsFields), QTableWidgetItem(""))

    def update_events_start_stop_old(self) -> None:
        """
        update status start/stop of events in Events table
        take consideration of subject and modifiers

        """

        try:
            stateEventsList = [
                self.pj[ETHOGRAM][x][BEHAVIOR_CODE]
                for x in self.pj[ETHOGRAM]
                if STATE in self.pj[ETHOGRAM][x][TYPE].upper()
            ]

            for row in range(self.twEvents.rowCount()):

                t = self.twEvents.item(row, tw_obs_fields["time"]).text()

                time = time2seconds(t) if ":" in t else Decimal(t)

                subject = self.twEvents.item(row, tw_obs_fields["subject"]).text()
                code = self.twEvents.item(row, tw_obs_fields["code"]).text()
                modifier = self.twEvents.item(row, tw_obs_fields["modifier"]).text()

                # check if code is state
                if code in stateEventsList:
                    # how many code before with same subject?

                    nbEvents = len([
                        event[EVENT_BEHAVIOR_FIELD_IDX]
                        for event in self.pj[OBSERVATIONS][self.observationId][EVENTS]
                        if event[EVENT_BEHAVIOR_FIELD_IDX] == code and event[EVENT_TIME_FIELD_IDX] < time and
                        event[EVENT_SUBJECT_FIELD_IDX] == subject and event[EVENT_MODIFIER_FIELD_IDX] == modifier
                    ])

                    if nbEvents and (nbEvents % 2):  # test >0 and  odd
                        self.twEvents.item(row, tw_obs_fields[TYPE]).setText(STOP)
                    else:
                        self.twEvents.item(row, tw_obs_fields[TYPE]).setText(START)
        except Exception:
            dialog.error_message2()

    def update_events_start_stop(self):
        """
        update status start/stop of events in Events table
        take consideration of subject and modifiers
        twEvents must be ordered by time asc

        does not return value
        """

        try:
            state_events_list = utilities.state_behavior_codes(self.pj[ETHOGRAM])
            mem_behav = {}

            for row in range(self.twEvents.rowCount()):

                subject = self.twEvents.item(row, tw_obs_fields["subject"]).text()
                code = self.twEvents.item(row, tw_obs_fields["code"]).text()
                modifier = self.twEvents.item(row, tw_obs_fields["modifier"]).text()

                # check if code is state
                if code in state_events_list:

                    if f"{subject}|{code}|{modifier}" in mem_behav and mem_behav[f"{subject}|{code}|{modifier}"]:
                        self.twEvents.item(row, tw_obs_fields[TYPE]).setText(STOP)
                    else:
                        self.twEvents.item(row, tw_obs_fields[TYPE]).setText(START)

                    if f"{subject}|{code}|{modifier}" in mem_behav:
                        mem_behav[f"{subject}|{code}|{modifier}"] = not mem_behav[f"{subject}|{code}|{modifier}"]
                    else:
                        mem_behav[f"{subject}|{code}|{modifier}"] = 1

        except Exception:
            dialog.error_message2()

    def checkSameEvent(self, obsId: str, time: Decimal, subject: str, code: str):
        """
        check if a same event is already in events list (time, subject, code)
        """

        return [time, subject,
                code] in [[x[EVENT_TIME_FIELD_IDX], x[EVENT_SUBJECT_FIELD_IDX], x[EVENT_BEHAVIOR_FIELD_IDX]]
                          for x in self.pj[OBSERVATIONS][obsId][EVENTS]]

    def writeEvent(self, event: dict, memTime: Decimal) -> None:
        """
        add event from pressed key to observation
        offset is added to event time
        ask for modifiers if configured
        load events in tableview
        scroll to active event

        Args:
            event (dict): event parameters
            memTime (Decimal): time

        """

        logging.debug(f"write event - event: {event}  memtime: {memTime}")
        try:
            if event is None:
                return

            # add time offset if not from editing
            if "row" not in event:
                memTime += Decimal(self.pj[OBSERVATIONS][self.observationId][TIME_OFFSET]).quantize(Decimal(".001"))

            # check if a same event is already in events list (time, subject, code)
            # "row" present in case of event editing

            if ("row" not in event) and self.checkSameEvent(
                    self.observationId,
                    memTime,
                    event["subject"] if "subject" in event else self.currentSubject,
                    event["code"],
            ):
                _ = dialog.MessageDialog(programName,
                                         "The same event already exists (same time, behavior code and subject).", [OK])
                return

            if "from map" not in event:  # modifiers only for behaviors without coding map
                # check if event has modifiers
                modifier_str = ""

                if event["modifiers"]:

                    selected_modifiers, modifiers_external_data = {}, {}
                    # check if modifiers are from external data
                    for idx in event["modifiers"]:

                        if event["modifiers"][idx]["type"] == EXTERNAL_DATA_MODIFIER:

                            if "row" not in event:  # no edit
                                for idx2 in self.plot_data:
                                    if self.plot_data[idx2].y_label.upper() == event["modifiers"][idx]["name"].upper():
                                        modifiers_external_data[idx] = dict(event["modifiers"][idx])
                                        modifiers_external_data[idx]["selected"] = self.plot_data[idx2].lb_value.text()
                            else:  # edit
                                original_modifiers_list = event.get("original_modifiers", "").split("|")
                                modifiers_external_data[idx] = dict(event["modifiers"][idx])
                                modifiers_external_data[idx]["selected"] = original_modifiers_list[int(idx)]

                    # check if modifiers are in single, multiple or numeric
                    if [x for x in event["modifiers"] if event["modifiers"][x]["type"] != EXTERNAL_DATA_MODIFIER]:

                        # pause media
                        if self.pj[OBSERVATIONS][self.observationId][TYPE] in [MEDIA]:
                            if self.playerType == VLC:
                                if self.dw_player[0].player.pause:
                                    memState = "paused"
                                elif self.dw_player[0].player.time_pos is not None:
                                    memState = "playing"
                                else:
                                    memState = "stopped"
                                if memState == "playing":
                                    self.pause_video()

                        # check if editing (original_modifiers key)
                        currentModifiers = event.get("original_modifiers", "")

                        modifiers_selector = select_modifiers.ModifiersList(event["code"],
                                                                            eval(str(event["modifiers"])),
                                                                            currentModifiers)

                        r = modifiers_selector.exec_()
                        if r:
                            selected_modifiers = modifiers_selector.get_modifiers()

                        # restart media
                        if self.pj[OBSERVATIONS][self.observationId][TYPE] in [MEDIA]:
                            if self.playerType == VLC:
                                if memState == "playing":
                                    self.play_video()
                        if not r:  # cancel button pressed
                            return

                    all_modifiers = {**selected_modifiers, **modifiers_external_data}

                    modifier_str = ""
                    for idx in sorted_keys(all_modifiers):
                        if modifier_str:
                            modifier_str += "|"
                        if all_modifiers[idx]["type"] in [SINGLE_SELECTION, MULTI_SELECTION]:
                            modifier_str += ",".join(all_modifiers[idx].get("selected", ""))
                        if all_modifiers[idx]["type"] in [NUMERIC_MODIFIER, EXTERNAL_DATA_MODIFIER]:
                            modifier_str += all_modifiers[idx].get("selected", "NA")

            else:
                modifier_str = event["from map"]

            # update current state
            # TODO: verify event["subject"] / self.currentSubject

            # extract State events
            StateBehaviorsCodes = utilities.state_behavior_codes(self.pj[ETHOGRAM])

            # index of current subject
            subject_idx = self.subject_name_index[self.currentSubject] if self.currentSubject else ""

            current_states = utilities.get_current_states_modifiers_by_subject(
                StateBehaviorsCodes,
                self.pj[OBSERVATIONS][self.observationId][EVENTS],
                dict(self.pj[SUBJECTS], **{"": {
                    "name": ""
                }}),
                memTime,
                include_modifiers=False,
            )

            logging.debug(f"self.currentSubject {self.currentSubject}")
            logging.debug(f"current_states {current_states}")

            if "row" not in event:  # no editing
                if self.currentSubject:
                    csj = []
                    for idx in current_states:
                        if idx in self.pj[SUBJECTS] and self.pj[SUBJECTS][idx][SUBJECT_NAME] == self.currentSubject:
                            csj = current_states[idx]
                            break

                else:  # no focal subject
                    try:
                        csj = current_states[""]
                    except Exception:
                        csj = []

                logging.debug(f"csj {csj}")

                cm = {}  # modifiers for current behaviors
                for cs in csj:
                    for ev in self.pj[OBSERVATIONS][self.observationId][EVENTS]:
                        if ev[EVENT_TIME_FIELD_IDX] > memTime:
                            break

                        if ev[EVENT_SUBJECT_FIELD_IDX] == self.currentSubject:
                            if ev[EVENT_BEHAVIOR_FIELD_IDX] == cs:
                                cm[cs] = ev[EVENT_MODIFIER_FIELD_IDX]

                logging.debug(f"cm {cm}")

                for cs in csj:
                    # close state if same state without modifier
                    if (self.close_the_same_current_event and (event["code"] == cs) and
                            modifier_str.replace("None", "").replace("|", "") == ""):
                        modifier_str = cm[cs]
                        continue

                    if (event["excluded"] and cs in event["excluded"].split(",")) or (event["code"] == cs and
                                                                                      cm[cs] != modifier_str):
                        # add excluded state event to observations (= STOP them)
                        self.pj[OBSERVATIONS][self.observationId][EVENTS].append(
                            # [memTime - Decimal("0.001"), self.currentSubject, cs, cm[cs], ""]
                            [memTime, self.currentSubject, cs, cm[cs], ""])

            # remove key code from modifiers
            modifier_str = re.sub(" \(.*\)", "", modifier_str)
            comment = event.get("comment", "")
            subject = event.get("subject", self.currentSubject)

            # add event to pj
            if "row" in event:
                # modifying event
                self.pj[OBSERVATIONS][self.observationId][EVENTS][event["row"]] = [
                    memTime,
                    subject,
                    event["code"],
                    modifier_str,
                    comment,
                ]
            else:
                # add event
                self.pj[OBSERVATIONS][self.observationId][EVENTS].append(
                    [memTime, subject, event["code"], modifier_str, comment])

            # sort events in pj
            self.pj[OBSERVATIONS][self.observationId][EVENTS].sort()

            # reload all events in tw
            self.loadEventsInTW(self.observationId)

            position_in_events = [
                i for i, t in enumerate(self.pj[OBSERVATIONS][self.observationId][EVENTS]) if t[0] == memTime
            ][0]

            if position_in_events == len(self.pj[OBSERVATIONS][self.observationId][EVENTS]) - 1:
                self.twEvents.scrollToBottom()
            else:
                self.twEvents.scrollToItem(self.twEvents.item(position_in_events, 0), QAbstractItemView.EnsureVisible)

            self.projectChanged = True
        except Exception:
            dialog.error_message2()

    def fill_lwDetailed(self, obs_key, memLaps):
        """
        fill listwidget with all events coded by key
        return index of behaviour
        """

        # check if key duplicated
        items = []
        for idx in self.pj[ETHOGRAM]:
            if self.pj[ETHOGRAM][idx]["key"] == obs_key:

                code_descr = self.pj[ETHOGRAM][idx][BEHAVIOR_CODE]
                if self.pj[ETHOGRAM][idx][DESCRIPTION]:
                    code_descr += " - " + self.pj[ETHOGRAM][idx][DESCRIPTION]
                items.append(code_descr)
                self.detailedObs[code_descr] = idx

        items.sort()

        dbc = dialog.DuplicateBehaviorCode(f"The <b>{obs_key}</b> key codes more behaviors.<br>Choose the correct one:",
                                           items)
        if dbc.exec_():
            code = dbc.getCode()
            if code:
                return self.detailedObs[code]
            else:
                return None

    def getLaps(self, n_player: int = 0) -> Decimal:
        """
        Cumulative laps time from begining of observation
        no more add time offset!

        Args:
            n_player (int): player
        Returns:
            decimal: cumulative time in seconds

        """

        if not self.observationId:
            return Decimal("0")

        if self.pj[OBSERVATIONS][self.observationId]["type"] == LIVE:

            if self.liveObservationStarted:
                now = QTime()
                now.start()  # current time
                memLaps = Decimal(str(round(self.liveStartTime.msecsTo(now) / 1000, 3)))
                return memLaps
            else:
                return Decimal("0.0")

        if self.pj[OBSERVATIONS][self.observationId]["type"] == MEDIA:

            if self.playerType == VIEWER:
                return Decimal("0.0")

            if self.playerType == VLC:
                # cumulative time
                mem_laps = sum(
                    self.dw_player[n_player].media_durations[0:self.dw_player[n_player].player.playlist_pos]) + (
                        0 if self.dw_player[n_player].player.time_pos is None else
                        self.dw_player[n_player].player.time_pos * 1000)

                return Decimal(str(round(mem_laps / 1000, 3)))

    def full_event(self, behavior_idx: str) -> dict:
        """
        get event as dict
        ask modifiers from coding map if configured and add them under 'from map' key

        Args:
            behavior_idx (str): behavior index in ethogram
        Returns:
            dict: event

        """

        event = dict(self.pj[ETHOGRAM][behavior_idx])
        # check if coding map
        if "coding map" in self.pj[ETHOGRAM][behavior_idx] and self.pj[ETHOGRAM][behavior_idx]["coding map"]:

            # pause if media and media playing
            if self.pj[OBSERVATIONS][self.observationId][TYPE] in [MEDIA]:
                if self.playerType == VLC:
                    memState = self.dw_player[0].mediaListPlayer.get_state()
                    if memState == self.vlc_playing:
                        self.pause_video()

            self.codingMapWindow = modifiers_coding_map.ModifiersCodingMapWindowClass(
                self.pj[CODING_MAP][self.pj[ETHOGRAM][behavior_idx]["coding map"]])

            self.codingMapWindow.resize(CODING_MAP_RESIZE_W, CODING_MAP_RESIZE_H)
            if self.codingMapWindowGeometry:
                self.codingMapWindow.restoreGeometry(self.codingMapWindowGeometry)

            if self.codingMapWindow.exec_():
                event["from map"] = self.codingMapWindow.getCodes()
            else:
                event["from map"] = ""

            self.codingMapWindowGeometry = self.codingMapWindow.saveGeometry()

            # restart media
            if self.pj[OBSERVATIONS][self.observationId][TYPE] in [MEDIA]:
                if self.playerType == VLC:
                    if memState == self.vlc_playing:
                        self.play_video()

        return event

    def beep(self, sound_type: str):
        """
        emit beep on various platform

        Args:
            sound_type (str): type of sound
        """

        QSound.play(f":/{sound_type}")

    def is_playing(self):
        """
        check if first media player is playing for VLC or FFMPEG modes

        Returns:
            bool: True if playing else False
        """

        if self.playerType == VLC:

            if self.dw_player[0].player.pause:
                return False
            elif self.dw_player[0].player.time_pos is not None:
                return True
            else:
                return False

            return not self.dw_player[0].player.pause

        else:
            return False

    def keyPressEvent(self, event):

        logging.debug(f"text #{event.text()}#  event key: {event.key()} ")
        """
        if (event.modifiers() & Qt.ShiftModifier):   # SHIFT

        QApplication.keyboardModifiers()

        http://qt-project.org/doc/qt-5.0/qtcore/qt.html#Key-enum
        https://github.com/pyqt/python-qt5/blob/master/PyQt5/qml/builtins.qmltypes

        ESC: 16777216
        """

        if self.playerType == VIEWER:
            if event.key() in [Qt.Key_Shift, Qt.Key_Control, Qt.Key_Alt, Qt.Key_CapsLock, Qt.Key_AltGr]:
                return
            QMessageBox.critical(
                self,
                programName,
                ("The current observation is opened in VIEW mode.\n"
                 "It is not allowed to log events in this mode."),
            )
            return

        if not self.observationId:
            return

        # beep
        if self.confirmSound:
            self.beep("key_sound")

        flagPlayerPlaying = self.is_playing()

        ek, ek_text = event.key(), event.text()

        if ek in [Qt.Key_Tab, Qt.Key_Shift, Qt.Key_Control, Qt.Key_Meta, Qt.Key_Alt, Qt.Key_AltGr]:
            return
        """
        if ek == Qt.Key_Escape:
            self.switch_playing_mode()
            return
        """

        # speed down
        if ek == Qt.Key_End:
            if self.pj[OBSERVATIONS][self.observationId][TYPE] in [MEDIA]:
                self.video_slower_activated()
            return
        # speed up
        if ek == Qt.Key_Home:
            if self.pj[OBSERVATIONS][self.observationId][TYPE] in [MEDIA]:
                self.video_faster_activated()
            return
        # speed normal
        if ek == Qt.Key_Backspace:
            if self.pj[OBSERVATIONS][self.observationId][TYPE] in [MEDIA]:
                self.video_normalspeed_activated()
            return

        # play / pause with space bar
        if ek == Qt.Key_Space:
            if self.pj[OBSERVATIONS][self.observationId][TYPE] in [MEDIA]:
                if flagPlayerPlaying:
                    self.pause_video()
                else:
                    self.play_video()
            return

        # frame-by-frame mode
        # if self.playMode == FFMPEG:
        if ek == 47 or ek == Qt.Key_Left:  # / one frame back
            self.previous_frame()
            return

        if ek == 42 or ek == Qt.Key_Right:  # *  read next frame
            self.next_frame()
            return

        if self.playerType == VLC:
            #  jump backward
            if ek == Qt.Key_Down:

                logging.debug("jump backward")

                self.jumpBackward_activated()
                return

            # jump forward
            if ek == Qt.Key_Up:

                logging.debug("jump forward")

                self.jumpForward_activated()
                return

            # next media file (page up)
            if ek == Qt.Key_PageUp:

                logging.debug("next media file")

                self.next_media_file()

            # previous media file (page down)
            if ek == Qt.Key_PageDown:

                logging.debug("previous media file")

                self.previous_media_file()

        if not self.pj[ETHOGRAM]:
            QMessageBox.warning(self, programName, "The ethogram is not configured")
            return

        obs_key = None

        # check if key is function key
        if ek in function_keys:
            if function_keys[ek] in [self.pj[ETHOGRAM][x]["key"] for x in self.pj[ETHOGRAM]]:
                obs_key = function_keys[ek]

        # get time
        if self.pj[OBSERVATIONS][self.observationId][TYPE] == LIVE:
            if self.pj[OBSERVATIONS][self.observationId].get(SCAN_SAMPLING_TIME, 0):
                if self.timeFormat == HHMMSS:
                    memLaps = Decimal(int(time2seconds(self.lb_current_media_time.text())))
                if self.timeFormat == S:
                    memLaps = Decimal(int(Decimal(self.lb_current_media_time.text())))
            else:  # no scan sampling
                if self.pj[OBSERVATIONS][self.observationId].get(START_FROM_CURRENT_TIME, False):
                    memLaps = Decimal(str(utilities.seconds_of_day(datetime.datetime.now())))
                elif self.pj[OBSERVATIONS][self.observationId].get(START_FROM_CURRENT_EPOCH_TIME, False):
                    memLaps = Decimal(time.time())
                else:
                    memLaps = self.getLaps()

        else:
            memLaps = self.getLaps()

        if memLaps is None:
            return

        if (((ek in range(33, 256)) and (ek not in [Qt.Key_Plus, Qt.Key_Minus])) or (ek in function_keys) or
            (ek == Qt.Key_Enter and event.text())):  # click from coding pad or subjects pad

            ethogram_idx, subj_idx, count = -1, -1, 0

            if ek in function_keys:
                ek_unichr = function_keys[ek]
            elif ek != Qt.Key_Enter:
                ek_unichr = ek_text
            elif ek == Qt.Key_Enter and event.text():  # click from coding pad or subjects pad
                ek_unichr = ek_text

            logging.debug(f"ek_unichr {ek_unichr}")

            if ek == Qt.Key_Enter and event.text():  # click from coding pad or subjects pad
                ek_unichr = ""

                if "#subject#" in event.text():
                    for idx in self.pj[SUBJECTS]:
                        if self.pj[SUBJECTS][idx][SUBJECT_NAME] == event.text().replace("#subject#", ""):
                            subj_idx = idx
                            self.update_subject(self.pj[SUBJECTS][subj_idx][SUBJECT_NAME])
                            return

                else:  # behavior
                    for idx in self.pj[ETHOGRAM]:
                        if self.pj[ETHOGRAM][idx][BEHAVIOR_CODE] == event.text():
                            ethogram_idx = idx
                            count += 1
            else:
                # count key occurence in ethogram
                for idx in self.pj[ETHOGRAM]:
                    if self.pj[ETHOGRAM][idx]["key"] == ek_unichr:
                        ethogram_idx = idx
                        count += 1

            # check if key defines a suject
            if subj_idx == -1:  # subject not selected with subjects pad
                flag_subject = False
                for idx in self.pj[SUBJECTS]:
                    if ek_unichr == self.pj[SUBJECTS][idx]["key"]:
                        subj_idx = idx

            # select between code and subject
            if subj_idx != -1 and count:
                if self.playerType == VLC:
                    if self.is_playing():
                        flagPlayerPlaying = True
                        self.pause_video()

                r = dialog.MessageDialog(programName, "This key defines a behavior and a subject. Choose one",
                                         ["&Behavior", "&Subject"])
                if r == "&Subject":
                    count = 0
                if r == "&Behavior":
                    subj_idx = -1

            # check if key codes more events
            if subj_idx == -1 and count > 1:
                if self.pj[OBSERVATIONS][self.observationId][TYPE] in [MEDIA]:
                    if self.playerType == VLC:
                        if self.is_playing():
                            flagPlayerPlaying = True
                            self.pause_video()

                # let user choose event
                ethogram_idx = self.fill_lwDetailed(ek_unichr, memLaps)

                if ethogram_idx:
                    count = 1

            if self.playerType == VLC and flagPlayerPlaying:
                self.play_video()

            if count == 1:
                # check if focal subject is defined
                if not self.currentSubject and self.alertNoFocalSubject:
                    if self.pj[OBSERVATIONS][self.observationId][TYPE] in [MEDIA]:
                        if self.playerType == VLC:
                            if self.dw_player[0].mediaListPlayer.get_state() == self.vlc_playing:
                                flagPlayerPlaying = True
                                self.pause_video()

                    response = dialog.MessageDialog(
                        programName,
                        ("The focal subject is not defined. Do you want to continue?\n"
                         "Use Preferences menu option to modify this behaviour."),
                        [YES, NO],
                    )

                    if self.pj[OBSERVATIONS][self.observationId][TYPE] in [MEDIA] and flagPlayerPlaying:
                        self.play_video()

                    if response == NO:
                        return

                event = self.full_event(ethogram_idx)

                self.writeEvent(event, memLaps)

            elif count == 0:

                if subj_idx != -1:
                    # check if key defines a suject
                    flag_subject = False
                    for idx in self.pj[SUBJECTS]:
                        if ek_unichr == self.pj[SUBJECTS][idx]["key"]:
                            flag_subject = True
                            # select or deselect current subject
                            self.update_subject(self.pj[SUBJECTS][idx][SUBJECT_NAME])

                if not flag_subject:
                    logging.debug(f"Key not assigned ({ek_unichr})")
                    self.statusbar.showMessage(f"Key not assigned ({ek_unichr})", 5000)

    def twEvents_doubleClicked(self):
        """
        seek media to double clicked position (add self.repositioningTimeOffset value)
        substract time offset if defined
        """

        if self.twEvents.selectedIndexes():

            row = self.twEvents.selectedIndexes()[0].row()

            if ":" in self.twEvents.item(row, 0).text():
                time_ = time2seconds(self.twEvents.item(row, 0).text())
            else:
                time_ = Decimal(self.twEvents.item(row, 0).text())

            # substract time offset
            time_ -= self.pj[OBSERVATIONS][self.observationId][TIME_OFFSET]

            if time_ + self.repositioningTimeOffset >= 0:
                newTime = time_ + self.repositioningTimeOffset
            else:
                newTime = 0

            if self.playMode == MPV:
                self.seek_mediaplayer(newTime)
                self.update_visualizations()

    def twSubjects_doubleClicked(self):
        """
        select subject by double-click on the subjects table
        """

        if self.observationId:
            if self.twSubjects.selectedIndexes():
                self.update_subject(self.twSubjects.item(self.twSubjects.selectedIndexes()[0].row(), 1).text())
        else:
            self.no_observation()

    '''
    def edit_time_selected_events(self):
        """
        edit time of one or more selected events
        """
        # list of rows to edit
        twEvents_rows_to_shift = set([item.row() for item in self.twEvents.selectedIndexes()])

        if not len(twEvents_rows_to_shift):
            QMessageBox.warning(self, programName, "No event selected!")
            return

        d, ok = QInputDialog.getDouble(self, "Time value", "Value to add or subtract (use negative value):", 0, -86400,
                                       86400, 3)
        if ok and d:
            if (dialog.MessageDialog(
                    programName,
                (f"Confirm the {'addition' if d > 0 else 'subtraction'} of {abs(d)} seconds "
                 "to all selected events in the current observation?"),
                [YES, NO],
            ) == NO):
                return

            tsb_to_shift = []
            for row in twEvents_rows_to_shift:
                tsb_to_shift.append([
                    time2seconds(self.twEvents.item(row, EVENT_TIME_FIELD_IDX).text())
                    if self.timeFormat == HHMMSS else Decimal(self.twEvents.item(row, EVENT_TIME_FIELD_IDX).text()),
                    self.twEvents.item(row, EVENT_SUBJECT_FIELD_IDX).text(),
                    self.twEvents.item(row, EVENT_BEHAVIOR_FIELD_IDX).text(),
                ])

            for idx, event in enumerate(self.pj[OBSERVATIONS][self.observationId][EVENTS]):
                """if idx in rows_to_edit:"""
                if [
                        event[EVENT_TIME_FIELD_IDX],
                        event[EVENT_SUBJECT_FIELD_IDX],
                        event[EVENT_BEHAVIOR_FIELD_IDX],
                ] in tsb_to_shift:
                    self.pj[OBSERVATIONS][self.observationId][EVENTS][idx][EVENT_TIME_FIELD_IDX] += Decimal(f"{d:.3f}")
                    self.projectChanged = True

            self.pj[OBSERVATIONS][self.observationId][EVENTS] = sorted(
                self.pj[OBSERVATIONS][self.observationId][EVENTS])
            self.loadEventsInTW(self.observationId)
    '''

    def copy_selected_events(self):
        """
        copy selected events to clipboard
        """
        twEvents_rows_to_copy = set([item.row() for item in self.twEvents.selectedIndexes()])
        if not len(twEvents_rows_to_copy):
            QMessageBox.warning(self, programName, "No event selected!")
            return

        tsb_to_copy = []
        for row in twEvents_rows_to_copy:
            tsb_to_copy.append([
                time2seconds(self.twEvents.item(row, EVENT_TIME_FIELD_IDX).text())
                if self.timeFormat == HHMMSS else Decimal(self.twEvents.item(row, EVENT_TIME_FIELD_IDX).text()),
                self.twEvents.item(row, EVENT_SUBJECT_FIELD_IDX).text(),
                self.twEvents.item(row, EVENT_BEHAVIOR_FIELD_IDX).text(),
            ])

        copied_events = []
        for idx, event in enumerate(self.pj[OBSERVATIONS][self.observationId][EVENTS]):
            if [
                    event[EVENT_TIME_FIELD_IDX],
                    event[EVENT_SUBJECT_FIELD_IDX],
                    event[EVENT_BEHAVIOR_FIELD_IDX],
            ] in tsb_to_copy:
                copied_events.append("\t".join([str(x) for x in self.pj[OBSERVATIONS][self.observationId][EVENTS][idx]
                                               ]))

        cb = QApplication.clipboard()
        cb.clear(mode=cb.Clipboard)
        cb.setText("\n".join(copied_events), mode=cb.Clipboard)

    def paste_clipboard_to_events(self):
        """
        paste clipboard to events
        """

        cb = QApplication.clipboard()
        cb_text = cb.text()
        cb_text_splitted = cb_text.split("\n")
        length = []
        content = []
        for l in cb_text_splitted:
            length.append(len(l.split("\t")))
            content.append(l.split("\t"))
        if set(length) != set([5]):
            QMessageBox.warning(
                self,
                programName,
                ("The clipboard does not contain events!\n"
                 "Events must be organized in 5 columns separated by TAB character"),
            )
            return

        for event in content:
            event[0] = Decimal(event[0])
            if event in self.pj[OBSERVATIONS][self.observationId][EVENTS]:
                continue
            self.pj[OBSERVATIONS][self.observationId][EVENTS].append(event)
            self.projectChanged = True

        self.pj[OBSERVATIONS][self.observationId][EVENTS] = sorted(self.pj[OBSERVATIONS][self.observationId][EVENTS])
        self.loadEventsInTW(self.observationId)

    def click_signal_find_in_events(self, msg):
        """
        find in events when "Find" button of find dialog box is pressed
        """

        if msg == "CLOSE":
            self.find_dialog.close()
            return

        self.find_dialog.lb_message.setText("")
        fields_list = []
        if self.find_dialog.cbSubject.isChecked():
            fields_list.append(EVENT_SUBJECT_FIELD_IDX)
        if self.find_dialog.cbBehavior.isChecked():
            fields_list.append(EVENT_BEHAVIOR_FIELD_IDX)
        if self.find_dialog.cbModifier.isChecked():
            """fields_list.append(EVENT_MODIFIER_FIELD_IDX )"""
            fields_list.append(4)

        if self.find_dialog.cbComment.isChecked():
            """fields_list.append(EVENT_COMMENT_FIELD_IDX)"""
            fields_list.append(5)
        if not fields_list:
            self.find_dialog.lb_message.setText('<font color="red">No fields selected!</font>')
            return
        if not self.find_dialog.findText.text():
            self.find_dialog.lb_message.setText('<font color="red">Nothing to search!</font>')
            return
        """for event_idx, event in enumerate(self.pj[OBSERVATIONS][self.observationId][EVENTS]):"""
        for event_idx in range(self.twEvents.rowCount()):
            if event_idx <= self.find_dialog.currentIdx:
                continue

            # find only in filtered events
            """
            if self.filtered_subjects:
                if self.pj[OBSERVATIONS][self.observationId][EVENTS][event_idx][EVENT_SUBJECT_FIELD_IDX] not in self.filtered_subjects:
                    continue
            if self.filtered_behaviors:
                if self.pj[OBSERVATIONS][self.observationId][EVENTS][event_idx][EVENT_BEHAVIOR_FIELD_IDX] not in self.filtered_behaviors:
                    continue
            """

            if (not self.find_dialog.cbFindInSelectedEvents.isChecked()) or (
                    self.find_dialog.cbFindInSelectedEvents.isChecked() and event_idx in self.find_dialog.rowsToFind):

                for idx in fields_list:
                    """
                    if (self.find_dialog.cb_case_sensitive.isChecked() and self.find_dialog.findText.text() in event[idx]) \
                       or (not self.find_dialog.cb_case_sensitive.isChecked() and
                           self.find_dialog.findText.text().upper() in event[idx].upper()):
                    """
                    if (self.find_dialog.cb_case_sensitive.isChecked() and
                            self.find_dialog.findText.text() in self.twEvents.item(
                                event_idx, idx).text()) or (not self.find_dialog.cb_case_sensitive.isChecked() and
                                                            self.find_dialog.findText.text().upper()
                                                            in self.twEvents.item(event_idx, idx).text().upper()):

                        self.find_dialog.currentIdx = event_idx
                        self.twEvents.scrollToItem(self.twEvents.item(event_idx, 0))
                        self.twEvents.selectRow(event_idx)
                        return

        if msg != "FIND_FROM_BEGINING":
            if (dialog.MessageDialog(
                    programName,
                    f"<b>{self.find_dialog.findText.text()}</b> not found. Search from beginning?",
                [YES, NO],
            ) == YES):
                self.find_dialog.currentIdx = -1
                self.click_signal_find_in_events("FIND_FROM_BEGINING")
            else:
                self.find_dialog.close()
        else:
            if self.find_dialog.currentIdx == -1:
                self.find_dialog.lb_message.setText(f"<b>{self.find_dialog.findText.text()}</b> not found")

    def explore_project(self):
        """
        search various elements (subjects, behaviors, modifiers, comments) in all observations
        """

        explore_dialog = dialog.explore_project_dialog()
        if explore_dialog.exec_():
            results = []
            nb_fields = ((explore_dialog.find_subject.text() != "") + (explore_dialog.find_behavior.text() != "") +
                         (explore_dialog.find_modifier.text() != "") + (explore_dialog.find_comment.text() != ""))

            for obs_id in sorted(self.pj[OBSERVATIONS]):
                for event_idx, event in enumerate(self.pj[OBSERVATIONS][obs_id][EVENTS]):
                    nb_results = 0
                    for text, idx in [
                        (explore_dialog.find_subject.text(), EVENT_SUBJECT_FIELD_IDX),
                        (explore_dialog.find_behavior.text(), EVENT_BEHAVIOR_FIELD_IDX),
                        (explore_dialog.find_modifier.text(), EVENT_MODIFIER_FIELD_IDX),
                        (explore_dialog.find_comment.text(), EVENT_COMMENT_FIELD_IDX),
                    ]:
                        if text:
                            if explore_dialog.cb_case_sensitive.isChecked() and text in event[idx]:
                                nb_results += 1
                            if not explore_dialog.cb_case_sensitive.isChecked() and text.upper() in event[idx].upper():
                                nb_results += 1

                    if nb_results == nb_fields:
                        results.append((obs_id, event_idx + 1))

            if results:
                self.results_dialog = dialog.View_explore_project_results()
                self.results_dialog.setWindowFlags(Qt.WindowStaysOnTopHint)
                self.results_dialog.double_click_signal.connect(self.double_click_explore_project)
                self.results_dialog.lb.setText(f"{len(results)} results")
                self.results_dialog.tw.setColumnCount(2)
                self.results_dialog.tw.setRowCount(len(results))
                self.results_dialog.tw.setHorizontalHeaderLabels(["Observation id", "row index"])

                for row, result in enumerate(results):
                    for i in range(0, 2):
                        self.results_dialog.tw.setItem(row, i, QTableWidgetItem(str(result[i])))
                        self.results_dialog.tw.item(row, i).setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)

                self.results_dialog.show()

            else:
                QMessageBox.information(self, programName, "No events found")

    def double_click_explore_project(self, obs_id, event_idx):
        """
        manage double-click on tablewidget of explore project results
        """
        self.load_observation(obs_id, VIEW)
        self.twEvents.scrollToItem(self.twEvents.item(event_idx - 1, 0))
        self.twEvents.selectRow(event_idx - 1)

    def find_events(self):
        """
        find in events
        """

        self.find_dialog = dialog.FindInEvents()
        # list of rows to find
        self.find_dialog.rowsToFind = set([item.row() for item in self.twEvents.selectedIndexes()])
        self.find_dialog.currentIdx = -1
        self.find_dialog.clickSignal.connect(self.click_signal_find_in_events)
        self.find_dialog.setWindowFlags(Qt.WindowStaysOnTopHint)
        self.find_dialog.show()

    def click_signal_find_replace_in_events(self, msg):
        """
        find/replace in events when "Find" button of find dialog box is pressed
        """

        if msg == "CANCEL":
            self.find_replace_dialog.close()
            return
        if not self.find_replace_dialog.findText.text():
            dialog.MessageDialog(programName, "There is nothing to find.", ["OK"])
            return

        if self.find_replace_dialog.cbFindInSelectedEvents.isChecked() and not len(self.find_replace_dialog.rowsToFind):
            dialog.MessageDialog(programName, "There are no selected events", [OK])
            return

        fields_list = []
        if self.find_replace_dialog.cbSubject.isChecked():
            fields_list.append(EVENT_SUBJECT_FIELD_IDX)
        if self.find_replace_dialog.cbBehavior.isChecked():
            fields_list.append(EVENT_BEHAVIOR_FIELD_IDX)
        if self.find_replace_dialog.cbModifier.isChecked():
            fields_list.append(EVENT_MODIFIER_FIELD_IDX)
        if self.find_replace_dialog.cbComment.isChecked():
            fields_list.append(EVENT_COMMENT_FIELD_IDX)

        number_replacement = 0
        insensitive_re = re.compile(re.escape(self.find_replace_dialog.findText.text()), re.IGNORECASE)
        for event_idx, event in enumerate(self.pj[OBSERVATIONS][self.observationId][EVENTS]):

            # apply modif only to filtered subjects
            if self.filtered_subjects:
                if (self.pj[OBSERVATIONS][self.observationId][EVENTS][event_idx][EVENT_SUBJECT_FIELD_IDX]
                        not in self.filtered_subjects):
                    continue
            # apply modif only to filtered behaviors
            if self.filtered_behaviors:
                if (self.pj[OBSERVATIONS][self.observationId][EVENTS][event_idx][EVENT_BEHAVIOR_FIELD_IDX]
                        not in self.filtered_behaviors):
                    continue

            if event_idx < self.find_replace_dialog.currentIdx:
                continue

            if (not self.find_replace_dialog.cbFindInSelectedEvents.isChecked()) or (
                    self.find_replace_dialog.cbFindInSelectedEvents.isChecked() and
                    event_idx in self.find_replace_dialog.rowsToFind):
                for idx1 in fields_list:
                    if idx1 <= self.find_replace_dialog.currentIdx_idx:
                        continue

                    if (self.find_replace_dialog.cb_case_sensitive.isChecked() and
                            self.find_replace_dialog.findText.text() in event[idx1]) or (
                                not self.find_replace_dialog.cb_case_sensitive.isChecked() and
                                self.find_replace_dialog.findText.text().upper() in event[idx1].upper()):

                        number_replacement += 1
                        self.find_replace_dialog.currentIdx = event_idx
                        self.find_replace_dialog.currentIdx_idx = idx1
                        if self.find_replace_dialog.cb_case_sensitive.isChecked():
                            event[idx1] = event[idx1].replace(self.find_replace_dialog.findText.text(),
                                                              self.find_replace_dialog.replaceText.text())
                        if not self.find_replace_dialog.cb_case_sensitive.isChecked():
                            event[idx1] = insensitive_re.sub(self.find_replace_dialog.replaceText.text(), event[idx1])

                        self.pj[OBSERVATIONS][self.observationId][EVENTS][event_idx] = event
                        self.loadEventsInTW(self.observationId)
                        self.twEvents.scrollToItem(self.twEvents.item(event_idx, 0))
                        self.twEvents.selectRow(event_idx)
                        self.projectChanged = True

                        if msg == "FIND_REPLACE":
                            return

                self.find_replace_dialog.currentIdx_idx = -1

        if msg == "FIND_REPLACE":
            if (dialog.MessageDialog(
                    programName,
                    f"{self.find_replace_dialog.findText.text()} not found.\nRestart find/replace from the beginning?",
                [YES, NO],
            ) == YES):
                self.find_replace_dialog.currentIdx = -1
            else:
                self.find_replace_dialog.close()
        if msg == "FIND_REPLACE_ALL":
            dialog.MessageDialog(programName, f"{number_replacement} substitution(s).", [OK])
            self.find_replace_dialog.close()

    def find_replace_events(self):
        """
        find and replace in events
        """
        self.find_replace_dialog = dialog.FindReplaceEvents()
        self.find_replace_dialog.currentIdx = -1
        self.find_replace_dialog.currentIdx_idx = -1
        # list of rows to find/replace
        self.find_replace_dialog.rowsToFind = set([item.row() for item in self.twEvents.selectedIndexes()])
        self.find_replace_dialog.clickSignal.connect(self.click_signal_find_replace_in_events)
        self.find_replace_dialog.setWindowFlags(Qt.WindowStaysOnTopHint)
        self.find_replace_dialog.show()

    def closeEvent(self, event):
        """
        check if current project is saved
        close coding pad window if it exists
        close spectrogram window if it exists
         and close program
        """
        logging.debug("function: closeEvent")

        # check if re-encoding
        if self.processes:
            if (dialog.MessageDialog(programName, "BORIS is doing some job. What do you want to do?",
                                     ["Wait", "Quit BORIS"]) == "Wait"):
                event.ignore()
                return
            for ps in self.processes:
                ps[0].terminate()
                # Wait for Xms and then elevate the situation to terminate
                if not ps[0].waitForFinished(5000):
                    ps[0].kill()

        if self.observationId:
            self.close_observation()

        if self.projectChanged:
            response = dialog.MessageDialog(programName, "What to do about the current unsaved project?",
                                            [SAVE, DISCARD, CANCEL])

            if response == SAVE:
                if self.save_project_activated() == "not saved":
                    event.ignore()

            if response == CANCEL:
                try:
                    del self.config_param["refresh_preferences"]
                except KeyError:
                    logging.warning("no refresh_preferences key")
                event.ignore()

        if "refresh_preferences" not in self.config_param:
            config_file.save(self)

        self.close_tool_windows()

    def actionQuit_activated(self):
        self.close()

    def play_video(self):
        """
        play video
        check if first player ended
        """

        if self.playerType == VLC:

            # check if player 1 is ended
            for i, dw in enumerate(self.dw_player):
                if (str(i + 1) in self.pj[OBSERVATIONS][self.observationId][FILE] and
                        self.pj[OBSERVATIONS][self.observationId][FILE][str(i + 1)]):
                    dw.player.pause = False

            self.lb_player_status.clear()

            # if self.pj[OBSERVATIONS][self.observationId].get(VISUALIZE_WAVEFORM, False) \
            #    or self.pj[OBSERVATIONS][self.observationId].get(VISUALIZE_SPECTROGRAM, False):

            self.plot_timer.start()

            # start all timer for plotting data
            for data_timer in self.ext_data_timer_list:
                data_timer.start()

            self.actionPlay.setIcon(QIcon(":/pause"))
            self.actionPlay.setText("Pause")

            self.frame_mode = False

            return True

    def pause_video(self):
        """
        pause media
        does not pause media if already paused (to prevent media played again)
        """

        if self.playerType == VLC:

            for i, player in enumerate(self.dw_player):
                if (str(i + 1) in self.pj[OBSERVATIONS][self.observationId][FILE] and
                        self.pj[OBSERVATIONS][self.observationId][FILE][str(i + 1)]):

                    if not player.player.pause:

                        self.plot_timer.stop()
                        # stop all timer for plotting data
                        for data_timer in self.ext_data_timer_list:
                            data_timer.stop()

                        player.player.pause = True

            self.lb_player_status.setText("Player paused")

            # adjust positions of plots
            self.plot_timer_out()
            for idx in self.plot_data:
                self.timer_plot_data_out(self.plot_data[idx])

            self.actionPlay.setIcon(QIcon(":/play"))
            self.actionPlay.setText("Play")

    def play_activated(self):
        """
        button 'play' activated
        """

        if self.observationId and self.pj[OBSERVATIONS][self.observationId][TYPE] in [MEDIA]:
            if not self.is_playing():
                self.play_video()
            else:
                self.pause_video()

    def jumpBackward_activated(self):
        """
        rewind from current position
        """
        if self.playerType == VLC:

            decrement = (self.fast * self.play_rate
                         if self.config_param.get(ADAPT_FAST_JUMP, ADAPT_FAST_JUMP_DEFAULT) else self.fast)

            new_time = (sum(self.dw_player[0].media_durations[0:self.dw_player[0].player.playlist_pos]) / 1000 +
                        self.dw_player[0].player.playback_time - decrement)

            if new_time < decrement:
                new_time = 0

            self.seek_mediaplayer(new_time)

            self.update_visualizations()

            # subtitles
            """
            st_track_number = 0 if self.config_param[DISPLAY_SUBTITLES] else -1
            for player in self.dw_player:
                player.mediaplayer.video_set_spu(st_track_number)
            """

    def jumpForward_activated(self):
        """
        forward from current position
        """
        logging.debug("function: jumpForward_activated")

        if self.playerType == VLC:

            increment = (self.fast * self.play_rate
                         if self.config_param.get(ADAPT_FAST_JUMP, ADAPT_FAST_JUMP_DEFAULT) else self.fast)

            new_time = (sum(self.dw_player[0].media_durations[0:self.dw_player[0].player.playlist_pos]) / 1000 +
                        self.dw_player[0].player.playback_time + increment)

            self.seek_mediaplayer(new_time)

            self.update_visualizations()

    def update_visualizations(self, scroll_slider=False):
        """
        update visualization of video position, spectrogram, waveform, plot events and data
        """

        self.plot_timer_out()
        for idx in self.plot_data:
            self.timer_plot_data_out(self.plot_data[idx])

    def reset_activated(self):
        """
        reset video to beginning
        """
        logging.debug("Reset activated")

        if self.playerType == VLC:

            self.pause_video()

            if OBSERVATION_TIME_INTERVAL in self.pj[OBSERVATIONS][self.observationId]:
                self.seek_mediaplayer(int(self.pj[OBSERVATIONS][self.observationId][OBSERVATION_TIME_INTERVAL][0]))
            else:
                self.seek_mediaplayer(0)

            self.update_visualizations()

    ''' 2019-12-12
    def changedFocusSlot(self, old, now):
        """
        connect events filter when app gains focus
        """
        if window.focusWidget():
            window.focusWidget().installEventFilter(self)
    '''


def main():

    app = QApplication(sys.argv)

    import locale

    locale.setlocale(locale.LC_NUMERIC, "C")

    # splashscreen
    # no splashscreen for Mac because it can mask the first use dialog box

    if (not options.nosplashscreen) and (sys.platform != "darwin"):
        start = time.time()
        datadir = os.path.dirname(sys.path[0]) if os.path.isfile(sys.path[0]) else sys.path[0]
        splash = QSplashScreen(QPixmap(":/splash"))
        splash.show()
        splash.raise_()
        app.processEvents()
        while time.time() - start < 1:
            time.sleep(0.001)

    # check FFmpeg
    ret, msg = check_ffmpeg_path()
    if not ret:
        QMessageBox.critical(
            None,
            programName,
            "FFmpeg is not available.<br>Go to http://www.ffmpeg.org to download it",
            QMessageBox.Ok | QMessageBox.Default,
            QMessageBox.NoButton,
        )
        sys.exit(3)
    else:
        ffmpeg_bin = msg

    app.setApplicationName(programName)
    window = MainWindow(ffmpeg_bin)

    # open project/start observation on command line

    project_to_open = ""
    observation_to_open = ""
    if options.project:
        project_to_open = options.project
        # hook for Mac bundle created with pyinstaller
        if sys.platform == "darwin" and "sn_0_" in project_to_open:
            project_to_open = ""

    logging.debug(f"args: {args}")

    if options.observation:
        if not project_to_open:
            print("No project file!")
            sys.exit()
        observation_to_open = options.observation

    if project_to_open:

        project_path, project_changed, pj, msg = project_functions.open_project_json(project_to_open)

        if "error" in pj:
            logging.debug(pj["error"])
            QMessageBox.critical(window, programName, pj["error"])
        else:
            if msg:
                QMessageBox.information(window, programName, msg)
            window.load_project(project_path, project_changed, pj)

    if observation_to_open and "error" not in pj:
        r = window.load_observation(observation_to_open)
        if r:
            QMessageBox.warning(
                None,
                programName,
                (f"Error opening observation: <b>{observation_to_open}</b><br>{r.split(':')[1]}"),
                QMessageBox.Ok | QMessageBox.Default,
                QMessageBox.NoButton,
            )

    window.show()
    window.raise_()

    # connect events filter when app focus changes
    """2019-12-12
    app.focusChanged.connect(window.changedFocusSlot)
    """

    if not options.nosplashscreen and (sys.platform != "darwin"):
        splash.finish(window)

    sys.exit(app.exec_())


if __name__ == "__main__":

    main()
