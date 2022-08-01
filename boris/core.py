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
import pathlib as pl
import platform
import re
import bisect
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request

# from decimal import *
from decimal import Decimal as dec
from decimal import ROUND_DOWN
import gzip
from collections import deque

import matplotlib

matplotlib.use("Qt5Agg")
from PyQt5.QtCore import (
    Qt,
    pyqtSignal,
    QEvent,
    QProcess,
    QDateTime,
    QTime,
    QUrl,
    QPoint,
    QT_VERSION_STR,
    PYQT_VERSION_STR,
)
from PyQt5.QtGui import QIcon, QPixmap, QFont, QKeyEvent, QPolygon, QPainter, QDesktopServices
from PyQt5.QtMultimedia import QSound
from PyQt5.QtWidgets import QMainWindow, QFrame, QDockWidget, QApplication, QAction, QAbstractItemView, QSplashScreen
from PIL.ImageQt import ImageQt, Image

from . import dialog
from . import gui_utilities
from . import events_cursor
from . import map_creator
from . import geometric_measurement
from . import modifiers_coding_map
from . import advanced_event_filtering
from . import otx_parser
from . import param_panel
from . import plot_events
from . import plot_spectrogram_rt
from . import plot_waveform_rt
from . import plot_events_rt
from . import project_functions
from . import select_modifiers
from . import select_observations
from . import subjects_pad
from . import version
from . import event_operations
from . import cmd_arguments
from . import core_qrc
from .core_ui import Ui_MainWindow
import exifread
from . import config as cfg
from . import video_operations

from .project import *
from . import utilities as util

from . import menu_options as menu_options
from . import connections as connections
from . import config_file
from . import select_subj_behav
from . import observation_operations

__version__ = version.__version__
__version_date__ = version.__version_date__

# check minimal version of python
if util.versiontuple(platform.python_version()) < util.versiontuple("3.6"):
    msg = f"BORIS requires Python 3.6+! You are using Python v. {platform.python_version()}\n"
    logging.critical(msg)
    # append to boris_error.log file
    with open(pl.Path("~").expanduser() / "boris_error.log", "a") as f_out:
        f_out.write(f"{datetime.datetime.now():%Y-%m-%d %H:%M}\n")
        f_out.write(msg)
        f_out.write("-" * 80 + "\n")
    sys.exit()

if sys.platform == "darwin":  # for MacOS
    os.environ["LC_ALL"] = "en_US.UTF-8"

# parse command line arguments
(options, args) = cmd_arguments.parse_arguments()

# set logging parameters
if options.debug:
    logging.basicConfig(
        format="%(asctime)s,%(msecs)d  %(module)s l.%(lineno)d %(levelname)s %(message)s",
        datefmt="%H:%M:%S",
        level=logging.DEBUG,
    )
else:
    logging.basicConfig(
        format="%(asctime)s,%(msecs)d  %(message)s",
        datefmt="%H:%M:%S",
        level=logging.INFO,
    )

if options.version:
    print(f"version {__version__} release date: {__version_date__}")
    sys.exit(0)

logging.info("BORIS started")
logging.info(f"BORIS version {__version__} release date: {__version_date__}")
logging.info(f"Operating system: {platform.uname().system} {platform.uname().release} {platform.uname().version}")
logging.info(f"CPU: {platform.uname().machine} {platform.uname().processor}")
logging.info(f"Python {platform.python_version()} ({'64-bit' if sys.maxsize > 2**32 else '32-bit'})")
logging.info(f"Qt {QT_VERSION_STR} - PyQt {PYQT_VERSION_STR}")

(r, memory) = util.mem_info()
if not r:
    logging.info(
        (
            f"Memory (RAM)  Total: {memory.get('total_memory', 'Not available'):.2f} Mb  "
            f"Free: {memory.get('free_memory', 'Not available'):.2f} Mb"
        )
    )


class MainWindow(QMainWindow, Ui_MainWindow):
    """
    Main BORIS window
    """

    pj = dict(cfg.EMPTY_PROJECT)
    project: bool = False  # project is loaded?
    geometric_measurements_mode = False  # geometric measurement modae active?

    time_observer_signal = pyqtSignal(float)

    processes = []  # list of QProcess processes
    overlays = {}  # dict for storing video overlays

    undo_queue = deque()
    undo_description = deque()

    saved_state = None
    user_move_slider = False
    observationId = ""  # current observation id
    timeOffset = 0.0
    confirmSound = False  # if True each keypress will be confirmed by a beep
    spectrogramHeight = 80
    spectrogram_time_interval = cfg.SPECTROGRAM_DEFAULT_TIME_INTERVAL
    spectrogram_color_map = cfg.SPECTROGRAM_DEFAULT_COLOR_MAP
    frame_bitmap_format = cfg.FRAME_DEFAULT_BITMAP_FORMAT
    alertNoFocalSubject = False  # if True an alert will show up if no focal subject
    trackingCursorAboveEvent = False  # if True the cursor will appear above the current event in events table
    checkForNewVersion = False  # if True BORIS will check for new version every 15 days
    pause_before_addevent = False  # pause before "Add event" command CTRL + A
    timeFormat = cfg.HHMMSS  # 's' or 'hh:mm:ss'
    repositioningTimeOffset = 0
    automaticBackup = 0  # automatic backup interval (0 no backup)
    events_current_row = -1
    projectChanged: bool = False  # store if project was changed
    liveObservationStarted = False
    # data structures for external data plot
    plot_data = {}
    ext_data_timer_list = []
    projectFileName = ""
    mediaTotalLength = None
    beep_every = 0

    plot_colors = cfg.BEHAVIORS_PLOT_COLORS
    behav_category_colors = cfg.CATEGORY_COLORS_LIST

    measurement_w = None
    memPoints = []  # memory of clicked points for measurement tool
    memPoints_video = []  # memory of clicked points for measurement tool

    behav_seq_separator = "|"
    # time laps
    fast = 10

    currentStates = {}
    subject_name_index = {}
    flag_slow = False
    play_rate = 1
    play_rate_step = 0.1
    currentSubject = ""  # contains the current subject of observation
    detailedObs = {}
    coding_map_window_geometry = 0
    project_window_geometry = 0  # memorize size of project window

    # FFmpeg
    memx, memy, mem_player = -1, -1, -1

    # path for ffmpeg/ffmpeg.exe program
    ffmpeg_bin = ""
    ffmpeg_cache_dir = ""
    ffmpeg_cache_dir_max_size = 0

    # dictionary for FPS storing
    fps = 0

    playerType: str = ""  # cfg.MEDIA, cfg.LIVE, cfg.VIEWER

    # spectrogram
    chunk_length = 60  # spectrogram chunk length in seconds

    close_the_same_current_event: bool = False
    tcp_port: int = 0
    bcm_dict: dict = {}  # handle behavior coding map
    recent_projects: list = []

    filtered_subjects: list = []
    filtered_behaviors: list = []

    dw_player: list = []

    save_project_json_started = False

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

        self.setWindowTitle(f"{cfg.programName} ({__version__})")

        self.w_obs_info.setVisible(False)

        self.lbLogoBoris.setPixmap(QPixmap(":/logo"))

        self.lbLogoBoris.setScaledContents(False)
        self.lbLogoBoris.setAlignment(Qt.AlignCenter)

        self.lbLogoUnito.setPixmap(QPixmap(":/dbios_unito"))
        self.lbLogoUnito.setScaledContents(False)
        self.lbLogoUnito.setAlignment(Qt.AlignCenter)

        self.toolBar.setEnabled(True)

        # start with dock widget invisible
        for w in [self.dwEvents, self.dwEthogram, self.dwSubjects]:
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
        self.lbFocalSubject.setText(cfg.NO_FOCAL_SUBJECT)

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

        # SPEED
        self.lbSpeed = QLabel()
        self.lbSpeed.setFrameStyle(QFrame.StyledPanel)
        self.lbSpeed.setMinimumWidth(40)
        self.statusbar.addPermanentWidget(self.lbSpeed)

        # set painter for twEvents to highlight current row
        self.twEvents.setItemDelegate(events_cursor.StyledItemDelegateTriangle(self.events_current_row))

        self.twEvents.setColumnCount(len(cfg.TW_EVENTS_FIELDS))
        self.twEvents.setHorizontalHeaderLabels(cfg.TW_EVENTS_FIELDS)

        self.config_param = cfg.INIT_PARAM

        menu_options.update_menu(self)
        connections.connections(self)
        config_file.read(self)

    def excepthook(self, exception_type, exception_value, traceback_object):
        """
        global error management
        """
        dialog.global_error_message(exception_type, exception_value, traceback_object)

    def block_dockwidgets(self):
        """
        allow to block Qdockwidgets on main window because they can have a strange behavior specially on Mac
        """
        for w in [self.dwEvents, self.dwEthogram, self.dwSubjects]:
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

    def project_changed(self):
        """ """
        self.projectChanged = True

    def remove_media_files_path(self):
        """
        remove path of media files
        """

        if (
            dialog.MessageDialog(
                cfg.programName,
                (
                    "Removing the path of media files from the project file is irreversible.<br>"
                    "Are you sure to continue?"
                ),
                [cfg.YES, cfg.NO],
            )
            == cfg.NO
        ):
            return

        self.pj = project_functions.remove_media_files_path(self.pj)
        self.projectChanged = True

    def view_behavior(self):
        """
        show details about the selected behavior
        """

        if self.twEthogram.selectedIndexes():
            behav = dict(self.pj[cfg.ETHOGRAM][str(self.twEthogram.selectedIndexes()[0].row())])
            if behav[cfg.MODIFIERS]:
                modifiers = ""
                for idx in util.sorted_keys(behav[cfg.MODIFIERS]):
                    if behav[cfg.MODIFIERS][idx]["name"]:
                        modifiers += (
                            f"<br>Name: {behav[cfg.MODIFIERS][idx]['name'] if behav[cfg.MODIFIERS][idx]['name'] else '-'}"
                            f"<br>Type: {cfg.MODIFIERS_STR[behav[cfg.MODIFIERS][idx]['type']]}<br>"
                        )

                    if behav[cfg.MODIFIERS][idx]["values"]:
                        modifiers += "Values:<br>"
                        for m in behav[cfg.MODIFIERS][idx]["values"]:
                            modifiers += f"{m}, "
                        modifiers = modifiers.strip(" ,") + "<br>"
            else:
                modifiers = "-"

            results = dialog.Results_dialog()
            results.setWindowTitle("View behavior")
            results.ptText.clear()
            results.ptText.setReadOnly(True)
            txt = (
                f"Code: <b>{behav['code']}</b><br>"
                f"Type: {behav['type']}<br>"
                f"Key: <b>{behav['key']}</b><br><br>"
                f"Description: {behav['description']}<br><br>"
                f"Category: {behav['category'] if behav['category'] else '-'}<br><br>"
                f"Exclude: {behav['excluded']}<br><br><br>"
                f"Modifiers:<br>{modifiers}"
            )
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

            self.processes_widget.label.setText(
                ("This operation can be long. Be patient...\n\n" "Done: {done} of {tot}").format(
                    done=self.processes_widget.number_of_files - len(self.processes),
                    tot=self.processes_widget.number_of_files,
                )
            )
            self.processes_widget.lwi.clear()
            self.processes_widget.lwi.addItems(
                [
                    self.processes[idx - 1][1][2],
                    self.processes[idx - 1][0].readAllStandardOutput().data().decode("utf-8"),
                ]
            )

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
            QMessageBox.warning(self, cfg.programName, "BORIS is already doing some job.")
            return

        fn = QFileDialog().getOpenFileNames(self, "Select one or more media files to process", "", "Media files (*)")
        fileNames = fn[0] if type(fn) is tuple else fn

        if fileNames:
            if action == "reencode_resize":
                current_bitrate = 2000
                current_resolution = 1024

                r = util.accurate_media_analysis(self.ffmpeg_bin, fileNames[0])
                if "error" in r:
                    QMessageBox.warning(self, cfg.programName, f"{fileNames[0]}. {r['error']}")
                elif r["has_video"]:
                    current_bitrate = r.get("bitrate", -1)
                    current_resolution = int(r["resolution"].split("x")[0]) if r["resolution"] is not None else None

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
                    if (
                        dialog.MessageDialog(
                            cfg.programName,
                            "All the selected video files will be re-encoded / resized with these parameters",
                            [cfg.OK, cfg.CANCEL],
                        )
                        == cfg.CANCEL
                    ):
                        return

                horiz_resol = ib.elements["Horizontal resolution (in pixel)"].value()
                video_quality = ib.elements["Video quality (bitrate)"].value()

            if action == "rotate":
                rotation_items = ("Rotate 90 clockwise", "Rotate 90 counter clockwise", "rotate 180")

                rotation, ok = QInputDialog.getItem(
                    self, "Rotate media file(s)", "Type of rotation", rotation_items, 0, False
                )

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
                response = dialog.MessageDialog(
                    cfg.programName,
                    "Some file(s) already exist.\n\n" + "\n".join(files_list),
                    [cfg.OVERWRITE_ALL, cfg.CANCEL],
                )
                if response == cfg.CANCEL:
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
                    r = util.accurate_media_analysis(self.ffmpeg_bin, file_name)
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
        self.config_param[cfg.CODING_PAD_GEOMETRY] = geometry
        self.config_param[cfg.CODING_PAD_CONFIG] = preferences

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
        if not self.pj[cfg.SUBJECTS]:
            QMessageBox.warning(self, cfg.programName, "No subjects are defined")
            return

        if self.playerType in cfg.VIEWERS:
            QMessageBox.warning(self, cfg.programName, "The subjects pad is not available in <b>VIEW</b> mode")
            return

        if hasattr(self, "subjects_pad"):
            self.subjects_pad.filtered_subjects = [
                self.twSubjects.item(i, cfg.EVENT_SUBJECT_FIELD_IDX).text() for i in range(self.twSubjects.rowCount())
            ]
            if not self.subjects_pad.filtered_subjects:
                QMessageBox.warning(self, cfg.programName, "No subjects to show")
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
                self.twSubjects.item(i, cfg.EVENT_SUBJECT_FIELD_IDX).text() for i in range(self.twSubjects.rowCount())
            ]
            if not filtered_subjects:
                QMessageBox.warning(self, cfg.programName, "No subjects to show")
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
        self.load_behaviors_in_twEthogram([self.pj[cfg.ETHOGRAM][x][cfg.BEHAVIOR_CODE] for x in self.pj[cfg.ETHOGRAM]])

    def show_all_subjects(self):
        """
        show all subjects in subjects list
        """
        self.load_subjects_in_twSubjects([self.pj[cfg.SUBJECTS][x][cfg.SUBJECT_NAME] for x in self.pj[cfg.SUBJECTS]])

    def filter_behaviors(
        self,
        title="Select the behaviors to show in the ethogram table",
        text="Behaviors to show in ethogram list",
        table=cfg.ETHOGRAM,
        behavior_type=[cfg.STATE_EVENT, cfg.POINT_EVENT],
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

        if not self.pj[cfg.ETHOGRAM]:
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
        if table == cfg.ETHOGRAM:
            filtered_behaviors = [self.twEthogram.item(i, 1).text() for i in range(self.twEthogram.rowCount())]
        else:
            filtered_behaviors = []

        if cfg.BEHAVIORAL_CATEGORIES in self.pj:
            categories = self.pj[cfg.BEHAVIORAL_CATEGORIES][:]
            # check if behavior not included in a category
            if "" in [
                self.pj[cfg.ETHOGRAM][idx][cfg.BEHAVIOR_CATEGORY]
                for idx in self.pj[cfg.ETHOGRAM]
                if cfg.BEHAVIOR_CATEGORY in self.pj[cfg.ETHOGRAM][idx]
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
            for behavior in [
                self.pj[cfg.ETHOGRAM][x][cfg.BEHAVIOR_CODE] for x in util.sorted_keys(self.pj[cfg.ETHOGRAM])
            ]:
                if project_functions.event_type(behavior, self.pj[cfg.ETHOGRAM]) not in behavior_type:
                    continue

                if (categories == ["###no category###"]) or (
                    behavior
                    in [
                        self.pj[cfg.ETHOGRAM][x][cfg.BEHAVIOR_CODE]
                        for x in self.pj[cfg.ETHOGRAM]
                        if cfg.BEHAVIOR_CATEGORY in self.pj[cfg.ETHOGRAM][x]
                        and self.pj[cfg.ETHOGRAM][x][cfg.BEHAVIOR_CATEGORY] == category
                    ]
                ):

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

            if table == cfg.ETHOGRAM:
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
            self.twSubjects.item(i, cfg.EVENT_SUBJECT_FIELD_IDX).text() for i in range(self.twSubjects.rowCount())
        ]

        for subject in [self.pj[cfg.SUBJECTS][x][cfg.SUBJECT_NAME] for x in util.sorted_keys(self.pj[cfg.SUBJECTS])]:

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
                    self.twSubjects.item(i, cfg.EVENT_SUBJECT_FIELD_IDX).text()
                    for i in range(self.twSubjects.rowCount())
                ]
                self.subjects_pad.compose()

    def generate_wav_file_from_media(self):
        """
        extract wav from all media files loaded in player #1
        """

        logging.debug("function: create wav file from media")

        # check temp dir for images from ffmpeg
        tmp_dir = (
            self.ffmpeg_cache_dir
            if self.ffmpeg_cache_dir and os.path.isdir(self.ffmpeg_cache_dir)
            else tempfile.gettempdir()
        )

        w = dialog.Info_widget()
        w.lwi.setVisible(False)
        w.resize(350, 100)
        w.setWindowFlags(Qt.WindowStaysOnTopHint)
        w.setWindowTitle(cfg.programName)
        w.label.setText("Extracting WAV from media files...")

        for media in self.pj[cfg.OBSERVATIONS][self.observationId][cfg.FILE][cfg.PLAYER1]:
            media_file_path = project_functions.media_full_path(media, self.projectFileName)
            if os.path.isfile(media_file_path):

                w.show()
                QApplication.processEvents()

                if util.extract_wav(self.ffmpeg_bin, media_file_path, tmp_dir) == "":
                    QMessageBox.critical(
                        self, cfg.programName, f"Error during extracting WAV of the media file {media_file_path}"
                    )
                    break

                w.hide()

            else:
                QMessageBox.warning(self, cfg.programName, f"<b>{media_file_path}</b> file not found")

    def show_plot_widget(self, plot_type: str, warning: bool = False):
        """
        show plot widgets (spectrogram, waveform, plot events)
        if plot does not exist it is created

        Args:
            plot_type (str): type of plot (cfg.SPECTROGRAM_PLOT, cfg.WAVEFORM_PLOT, cfg.EVENTS_PLOT)
            warning (bool): Display message if True
        """

        if plot_type not in [cfg.WAVEFORM_PLOT, cfg.SPECTROGRAM_PLOT, cfg.EVENTS_PLOT]:
            logging.critical(f"Error on plot type: {plot_type}")
            return

        if ((self.playerType == cfg.LIVE) or (self.playerType in cfg.VIEWERS)) and plot_type in [
            cfg.WAVEFORM_PLOT,
            cfg.SPECTROGRAM_PLOT,
        ]:
            QMessageBox.warning(
                self,
                cfg.programName,
                f"The sound signal visualization is not available in <b>{self.playerType}</b> mode",
            )
            return

        if plot_type == cfg.SPECTROGRAM_PLOT:
            if hasattr(self, "spectro"):
                self.spectro.show()
            else:
                logging.debug("create spectrogram plot")

                # check if first media in player #1 has audio
                for media in self.pj[cfg.OBSERVATIONS][self.observationId][cfg.FILE][cfg.PLAYER1]:
                    media_file_path = project_functions.media_full_path(media, self.projectFileName)

                    if not project_functions.has_audio(self.pj[cfg.OBSERVATIONS][self.observationId], media_file_path):
                        QMessageBox.critical(
                            self,
                            cfg.programName,
                            f"The media file {media_file_path} does not have an audio track",
                        )
                        return
                    break

                # remember if player paused
                if warning:
                    if self.playerType == cfg.MEDIA:
                        flag_paused = self.is_playing()

                self.pause_video()

                if (
                    warning
                    and dialog.MessageDialog(
                        cfg.programName,
                        (
                            f"You choose to visualize the {plot_type} during this observation.<br>"
                            f"{plot_type} generation can take some time for long media, be patient"
                        ),
                        [cfg.YES, cfg.NO],
                    )
                    == cfg.NO
                ):
                    if self.playerType == cfg.MEDIA and not flag_paused:
                        self.play_video()
                    return

                self.generate_wav_file_from_media()

                tmp_dir = (
                    self.ffmpeg_cache_dir
                    if self.ffmpeg_cache_dir and os.path.isdir(self.ffmpeg_cache_dir)
                    else tempfile.gettempdir()
                )

                wav_file_path = (
                    pl.Path(tmp_dir)
                    / pl.Path(
                        self.dw_player[0].player.playlist[self.dw_player[0].player.playlist_pos]["filename"] + ".wav"
                    ).name
                )

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
                        cfg.programName,
                        f"Error in spectrogram generation: {r['error']}",
                        QMessageBox.Ok | QMessageBox.Default,
                        QMessageBox.NoButton,
                    )
                    del self.spectro
                    return

                self.pj[cfg.OBSERVATIONS][self.observationId][cfg.VISUALIZE_SPECTROGRAM] = True
                self.spectro.sendEvent.connect(self.signal_from_widget)
                self.spectro.sb_freq_min.setValue(0)
                self.spectro.sb_freq_max.setValue(int(self.spectro.frame_rate / 2))
                self.spectro.show()

                self.plot_timer_out()

                if warning:
                    if self.playerType == cfg.MEDIA and not flag_paused:
                        self.play_video()

        if plot_type == cfg.WAVEFORM_PLOT:
            if hasattr(self, "waveform"):
                self.waveform.show()
            else:
                logging.debug("Create waveform plot")

                # check if first media in player #1 has audio
                for media in self.pj[cfg.OBSERVATIONS][self.observationId][cfg.FILE][cfg.PLAYER1]:
                    media_file_path = project_functions.media_full_path(media, self.projectFileName)

                    if not project_functions.has_audio(self.pj[cfg.OBSERVATIONS][self.observationId], media_file_path):
                        QMessageBox.critical(
                            self,
                            cfg.programName,
                            f"The media file {media_file_path} does not have an audio track",
                        )
                        return
                    break

                # remember if player paused
                if warning:
                    if self.playerType == cfg.MEDIA:
                        flag_paused = self.is_playing()

                self.pause_video()

                if (
                    warning
                    and dialog.MessageDialog(
                        cfg.programName,
                        (
                            "You choose to visualize the waveform during this observation.<br>"
                            "The waveform generation can take some time for long media, be patient"
                        ),
                        [cfg.YES, cfg.NO],
                    )
                    == cfg.NO
                ):
                    if self.playerType == cfg.MEDIA and not flag_paused:
                        self.play_video()
                    return

                self.generate_wav_file_from_media()

                tmp_dir = (
                    self.ffmpeg_cache_dir
                    if self.ffmpeg_cache_dir and os.path.isdir(self.ffmpeg_cache_dir)
                    else tempfile.gettempdir()
                )

                wav_file_path = (
                    pl.Path(tmp_dir)
                    / pl.Path(
                        self.dw_player[0].player.playlist[self.dw_player[0].player.playlist_pos]["filename"] + ".wav"
                    ).name
                )

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
                        cfg.programName,
                        f"Error in waveform generation: {r['error']}",
                        QMessageBox.Ok | QMessageBox.Default,
                        QMessageBox.NoButton,
                    )
                    del self.waveform
                    return

                self.pj[cfg.OBSERVATIONS][self.observationId][cfg.VISUALIZE_WAVEFORM] = True
                self.waveform.sendEvent.connect(self.signal_from_widget)
                self.waveform.show()

                self.plot_timer.start()

                if warning:
                    if self.playerType == cfg.MEDIA and not flag_paused:
                        self.play_video()

        if plot_type == cfg.EVENTS_PLOT:
            if hasattr(self, "plot_events"):
                self.plot_events.show()
            else:
                logging.debug("create plot events")

                self.plot_events = plot_events_rt.Plot_events_RT()

                self.plot_events.setWindowFlags(Qt.WindowStaysOnTopHint)
                self.plot_events.setWindowFlags(self.plot_events.windowFlags() & ~Qt.WindowMinimizeButtonHint)

                self.plot_events.groupby = "behaviors"
                self.plot_events.interval = 60  # time interval
                self.plot_events.cursor_color = "red"
                self.plot_events.observation_type = self.playerType

                self.plot_events.point_event_plot_duration = cfg.POINT_EVENT_PLOT_DURATION
                self.plot_events.point_event_plot_color = cfg.POINT_EVENT_PLOT_COLOR

                self.plot_events.state_events_list = util.state_behavior_codes(self.pj[cfg.ETHOGRAM])

                self.plot_events.events_list = self.pj[cfg.OBSERVATIONS][self.observationId][cfg.EVENTS]
                self.plot_events.events = self.plot_events.aggregate_events(
                    self.pj[cfg.OBSERVATIONS][self.observationId][cfg.EVENTS], 0, 60
                )

                # behavior colors
                self.plot_events.behav_color = {}
                for idx, behavior in enumerate(util.all_behaviors(self.pj[cfg.ETHOGRAM])):
                    self.plot_events.behav_color[behavior] = cfg.BEHAVIORS_PLOT_COLORS[idx]

                self.plot_events.sendEvent.connect(self.signal_from_widget)

                self.plot_events.show()

                # self.plot_timer_out()
                self.plot_timer.start()

    def plot_timer_out(self):
        """
        timer for plotting visualizations: spectrogram, waveform, plot events
        """
        """
        if (VISUALIZE_SPECTROGRAM not in self.pj[cfg.OBSERVATIONS][self.observationId] or
                not self.pj[cfg.OBSERVATIONS][self.observationId][VISUALIZE_SPECTROGRAM]):
            return
        """
        """
        if self.playerType == LIVE:
            QMessageBox.warning(self, cfg.programName, "The sound signal visualization is not available for live observations")
            return
        """

        if hasattr(self, "plot_events"):

            if not self.plot_events.visibleRegion().isEmpty():
                self.plot_events.events_list = self.pj[cfg.OBSERVATIONS][self.observationId][cfg.EVENTS]
                self.plot_events.plot_events(float(self.getLaps()))

        if self.playerType == cfg.MEDIA:

            current_media_time = self.dw_player[0].player.time_pos

            tmp_dir = (
                self.ffmpeg_cache_dir
                if self.ffmpeg_cache_dir and os.path.isdir(self.ffmpeg_cache_dir)
                else tempfile.gettempdir()
            )

            try:
                wav_file_path = str(
                    pl.Path(tmp_dir)
                    / pl.Path(
                        self.dw_player[0].player.playlist[self.dw_player[0].player.playlist_pos]["filename"] + ".wav"
                    ).name
                )
            except TypeError:
                return

            # waveform
            if self.pj[cfg.OBSERVATIONS][self.observationId].get(cfg.VISUALIZE_WAVEFORM, False):

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
            if self.pj[cfg.OBSERVATIONS][self.observationId].get(cfg.VISUALIZE_SPECTROGRAM, False):

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
        self.mapCreatorWindow.resize(cfg.CODING_MAP_RESIZE_W, cfg.CODING_MAP_RESIZE_H)
        self.mapCreatorWindow.show()

    def behaviors_coding_map_creator_signal_addtoproject(self, behav_coding_map):
        """
        add the behav coding map received from behav_coding_map_creator to current project

        Args:
            behav_coding_map (dict):
        """

        if not self.project:
            QMessageBox.warning(
                self, cfg.programName, "No project found", QMessageBox.Ok | QMessageBox.Default, QMessageBox.NoButton
            )
            return

        if cfg.BEHAVIORS_CODING_MAP not in self.pj:
            self.pj[cfg.BEHAVIORS_CODING_MAP] = []

        if [bcm for bcm in self.pj[cfg.BEHAVIORS_CODING_MAP] if bcm["name"] == behav_coding_map["name"]]:

            response = dialog.MessageDialog(
                "BORIS - Behaviors map creator",
                (
                    "The current project already contains a behaviors coding map "
                    f"with the same name (<b>{behav_coding_map['name']}</b>).<br>"
                    "What do you want to do?"
                ),
                ["Replace the coding map", cfg.CANCEL],
            )
            if response == cfg.CANCEL:
                return

            for idx, bcm in enumerate(self.pj[cfg.BEHAVIORS_CODING_MAP]):
                if bcm["name"] == behav_coding_map["name"]:
                    break
            self.pj[cfg.BEHAVIORS_CODING_MAP][idx] = dict(behav_coding_map)
            return

            """
            QMessageBox.critical(
                None,
                cfg.programName,
                (
                    "The current project already contains a behaviors coding map "
                    f"with the same name (<b>{behav_coding_map['name']}</b>)"
                ),
                QMessageBox.Ok | QMessageBox.Default,
                QMessageBox.NoButton,
            )

            return
            """

        self.pj[cfg.BEHAVIORS_CODING_MAP].append(behav_coding_map)
        QMessageBox.information(
            self,
            cfg.programName,
            f"The behaviors coding map <b>{behav_coding_map['name']}</b> was added to current project",
        )
        self.projectChanged = True

    def actionCheckUpdate_activated(self, flagMsgOnlyIfNew=False):
        """
        check BORIS web site for updates
        """

        try:
            versionURL = "http://www.boris.unito.it/static/ver4.dat"
            lastVersion = urllib.request.urlopen(versionURL).read().strip().decode("utf-8")
            if util.versiontuple(lastVersion) > util.versiontuple(__version__):
                msg = (
                    f"A new version is available: v. <b>{lastVersion}</b><br>"
                    'Go to <a href="http://www.boris.unito.it">'
                    "http://www.boris.unito.it</a> to install it."
                )
            else:
                msg = f"The version you are using is the last one: <b>{__version__}</b>"
            newsURL = "http://www.boris.unito.it/static/news.dat"
            news = urllib.request.urlopen(newsURL).read().strip().decode("utf-8")
            config_file.save(self, lastCheckForNewVersion=int(time.mktime(time.localtime())))
            QMessageBox.information(self, cfg.programName, msg)
            if news:
                QMessageBox.information(self, cfg.programName, news)
        except Exception:
            QMessageBox.warning(self, cfg.programName, "Can not check for updates...")

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
                        self.video_slider.setValue(
                            self.dw_player[0].player.time_pos
                            / self.dw_player[0].player.duration
                            * (cfg.SLIDER_MAXIMUM - 1)
                        )
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
                                float(new_time)
                                - sum(
                                    self.dw_player[player].media_durations[
                                        0 : self.dw_player[player].player.playlist_pos
                                    ]
                                )
                                / 1000,
                                3,
                            ),
                            "absolute+exact",
                        )

                        break
                    tot += d / 1000

                if player == 0 and not self.user_move_slider:
                    try:
                        self.video_slider.setValue(
                            self.dw_player[0].player.time_pos
                            / self.dw_player[0].player.duration
                            * (cfg.SLIDER_MAXIMUM - 1)
                        )
                    except Exception:
                        pass

            else:
                QMessageBox.warning(
                    self,
                    cfg.programName,
                    (
                        "The indicated position is behind the total media duration "
                        f"({util.seconds2time(sum(self.dw_player[player].media_durations))})"
                    ),
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

            if self.playerType == cfg.MEDIA:
                self.seek_mediaplayer(new_time)
                self.update_visualizations()

    def previous_media_file(self):
        """
        go to previous media file (if any)
        """

        if self.playerType == cfg.MEDIA:

            if len(self.pj[cfg.OBSERVATIONS][self.observationId][cfg.FILE][cfg.PLAYER1]) == 1:
                return

            # check if media not first media
            if self.dw_player[0].player.playlist_pos > 0:
                self.dw_player[0].player.playlist_prev()

            elif self.dw_player[0].player.playlist_count == 1:
                self.statusbar.showMessage("There is only one media file", 5000)

            if hasattr(self, "spectro"):
                self.spectro.memChunk = -1

        if self.playerType == cfg.IMAGES:

            if len(self.pj[cfg.OBSERVATIONS][self.observationId].get(cfg.DIRECTORIES_LIST, [])) <= 1:
                return
            if self.image_idx == 0:
                return

            current_dir = pl.Path(self.images_list[self.image_idx]).parent
            for image_path in self.images_list[self.image_idx - 1 :: -1]:
                if pl.Path(image_path).parent != current_dir:
                    self.image_idx = self.images_list.index(image_path)

                    # seek to first image of directory
                    current_dir2 = pl.Path(self.images_list[self.image_idx]).parent
                    for image_path2 in self.images_list[self.image_idx - 1 :: -1]:
                        if pl.Path(image_path2).parent != current_dir2:
                            self.image_idx = self.images_list.index(image_path2) + 1
                            break
                        if self.images_list.index(image_path2) == 0:
                            self.image_idx = 0
                            break

                    self.extract_frame(self.dw_player[0])
                    break

    def next_media_file(self):
        """
        go to next media file (if any) in first player
        """
        if self.playerType == cfg.MEDIA:

            if len(self.pj[cfg.OBSERVATIONS][self.observationId][cfg.FILE][cfg.PLAYER1]) == 1:
                return

            # check if media not last media
            if self.dw_player[0].player.playlist_pos < self.dw_player[0].player.playlist_count - 1:
                self.dw_player[0].player.playlist_next()

            else:
                if self.dw_player[0].player.playlist_count == 1:
                    self.statusbar.showMessage("There is only one media file", 5000)

            self.update_visualizations()

            if hasattr(self, "spectro"):
                self.spectro.memChunk = -1

        if self.playerType == cfg.IMAGES:

            if len(self.pj[cfg.OBSERVATIONS][self.observationId].get(cfg.DIRECTORIES_LIST, [])) <= 1:
                return
            current_dir = pl.Path(self.images_list[self.image_idx]).parent
            for image_path in self.images_list[self.image_idx + 1 :]:
                if pl.Path(image_path).parent != current_dir:
                    self.image_idx = self.images_list.index(image_path)
                    self.extract_frame(self.dw_player[0])
                    break

    def set_volume(self, nplayer, new_volume):
        """
        set volume for player nplayer

        Args:
            nplayer (str): player to set
            new_volume (int): volume to set
        """
        if self.playerType == cfg.MEDIA:
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
            logging.debug(
                (
                    f"project not autosaved: "
                    f"observation id: {self.observationId} "
                    f"project file name: {self.projectFileName}"
                )
            )

    def update_subject(self, subject):
        """
        update the current subject

        Args:
            subject (str): subject
        """
        try:
            if (not subject) or (subject == cfg.NO_FOCAL_SUBJECT) or (self.currentSubject == subject):
                self.currentSubject = ""
                self.lbFocalSubject.setText(cfg.NO_FOCAL_SUBJECT)
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
        for idx, media in enumerate(self.pj[cfg.OBSERVATIONS][self.observationId][cfg.FILE][player]):
            if requiredFrame * frameMs < sum(self.dw_player[int(player) - 1].media_durations[0 : idx + 1]):
                currentMedia = media
                frameCurrentMedia = (
                    requiredFrame - sum(self.dw_player[int(player) - 1].media_durations[0:idx]) / frameMs
                )
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
                            elementsColor = cfg.ACTIVE_MEASUREMENTS_COLOR
                        else:
                            elementsColor = cfg.PASSIVE_MEASUREMENTS_COLOR

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

    def extract_exif_DateTimeOriginal(self, file_path: str) -> int:
        """
        extract the exif extract_exif_DateTimeOriginal tag
        return epoch time
        if the tag is not available return -1
        """
        try:
            with open(file_path, "rb") as f_in:
                tags = exifread.process_file(f_in, details=False, stop_tag="EXIF DateTimeOriginal")
                date_time_original = f'{tags["EXIF DateTimeOriginal"].values[:4]}-{tags["EXIF DateTimeOriginal"].values[5:7]}-{tags["EXIF DateTimeOriginal"].values[8:10]} {tags["EXIF DateTimeOriginal"].values.split(" ")[-1]}'

                return int(datetime.datetime.strptime(date_time_original, "%Y-%m-%d %H:%M:%S").timestamp())
        except Exception:
            return -1

    def extract_frame(self, dw):
        """
        for MEDIA obs: extract frame from video and visualize it in frame_viewer
        for IMAGES obs: load picture and visualize it in frame_viewer, extract EXIF Date/Time Original tag if available
        """
        if self.playerType == cfg.MEDIA:
            pixmap = QPixmap.fromImage(ImageQt(dw.player.screenshot_raw()))

        if self.playerType == cfg.IMAGES:
            pixmap = QPixmap(self.images_list[self.image_idx])

            msg = f"Image index: <b>{self.image_idx + 1} / {len(self.images_list)}</b>"

            # extract EXIF tag
            if self.pj[cfg.OBSERVATIONS][self.observationId].get(cfg.USE_EXIF_DATE, False):

                date_time_original = self.extract_exif_DateTimeOriginal(self.images_list[self.image_idx])
                if date_time_original != -1:
                    msg += f"<br>EXIF Date/Time Original: <b>{datetime.datetime.fromtimestamp(date_time_original):%Y-%m-%d %H:%M:%S}</b>"
                else:
                    msg += f"<br>EXIF Date/Time Original: <b>NA</b>"

                if self.image_idx == 0 and date_time_original != -1:
                    self.image_time_ref = date_time_original

                if date_time_original != -1:
                    seconds_from_1st = date_time_original - self.image_time_ref

                    if self.timeFormat == cfg.HHMMSS:
                        seconds_from_1st_formated = util.seconds2time(seconds_from_1st).split(".")[
                            0
                        ]  # remove milliseconds
                    else:
                        seconds_from_1st_formated = seconds_from_1st

                else:
                    seconds_from_1st_formated = "NA"

                msg += f"<br>Time from 1st image: <b>{seconds_from_1st_formated}</b>"

            # image path
            msg += f"<br><br>Directory: <b>{pl.Path(self.images_list[self.image_idx]).parent}</b>"
            msg += f"<br>File name: <b>{pl.Path(self.images_list[self.image_idx]).name}</b>"

            self.lb_current_media_time.setText(msg)

        dw.frame_viewer.setPixmap(pixmap.scaled(dw.frame_viewer.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))

    def frame_image_clicked(self, n_player, event):
        geometric_measurement.image_clicked(self, n_player, event)

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
        dockwidget was resized. Adapt overlay if any
        """
        if self.geometric_measurements_mode:
            pass

        if self.playerType == cfg.MEDIA and not self.geometric_measurements_mode:
            try:
                img = Image.open(
                    self.pj[cfg.OBSERVATIONS][self.observationId][cfg.MEDIA_INFO][cfg.OVERLAY][str(dw_id + 1)][
                        "file name"
                    ]
                )
            except Exception:
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
            # and img_resized.putalpha(int((100 - self.pj[cfg.OBSERVATIONS][self.observationId][cfg.MEDIA_INFO][cfg.OVERLAY][str(dw_id + 1)]["transparency"]) * 2.55))  # 0 means 100% transparency

            # check position
            x_offset, y_offset = 0, 0
            if self.pj[cfg.OBSERVATIONS][self.observationId][cfg.MEDIA_INFO][cfg.OVERLAY][str(dw_id + 1)][
                "overlay position"
            ]:
                try:
                    x_offset = int(
                        self.pj[cfg.OBSERVATIONS][self.observationId][cfg.MEDIA_INFO][cfg.OVERLAY][str(dw_id + 1)][
                            "overlay position"
                        ]
                        .split(",")[0]
                        .strip()
                    )
                    y_offset = int(
                        self.pj[cfg.OBSERVATIONS][self.observationId][cfg.MEDIA_INFO][cfg.OVERLAY][str(dw_id + 1)][
                            "overlay position"
                        ]
                        .split(",")[1]
                        .strip()
                    )
                except Exception:
                    logging.warning(f"error in overlay position")

            try:
                self.overlays[dw_id].remove()
            except Exception:
                logging.debug("error removing overlay")
            try:
                self.overlays[dw_id].update(img_resized, pos=(x1 + x_offset, y1 + y_offset))
            except Exception:
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

    def load_tw_events(self, obs_id):
        """
        load events in table widget and update START/STOP

        if self.filtered_behaviors is populated and event not in self.filtered_behaviors then the event is not shown
        if self.filtered_subjects is populated and event not in self.filtered_subjects then the event is not shown

        Args:
            obsId (str): observation to load
        """

        logging.debug(f"begin load events from obs: {obs_id}")

        if self.pj[cfg.OBSERVATIONS][obs_id][cfg.TYPE] == cfg.MEDIA:
            self.twEvents.setColumnCount(len(cfg.MEDIA_TW_EVENTS_FIELDS))
            self.twEvents.setHorizontalHeaderLabels(cfg.MEDIA_TW_EVENTS_FIELDS)

        if self.pj[cfg.OBSERVATIONS][obs_id][cfg.TYPE] == cfg.LIVE:
            self.twEvents.setColumnCount(len(cfg.LIVE_TW_EVENTS_FIELDS))
            self.twEvents.setHorizontalHeaderLabels(cfg.LIVE_TW_EVENTS_FIELDS)

        if self.pj[cfg.OBSERVATIONS][obs_id][cfg.TYPE] == cfg.IMAGES:
            self.twEvents.setColumnCount(len(cfg.IMAGES_TW_EVENTS_FIELDS))
            self.twEvents.setHorizontalHeaderLabels(cfg.IMAGES_TW_EVENTS_FIELDS)

        self.twEvents.setRowCount(len(self.pj[cfg.OBSERVATIONS][obs_id][cfg.EVENTS]))
        if self.filtered_behaviors or self.filtered_subjects:
            self.twEvents.setRowCount(0)
        row = 0

        for event in self.pj[cfg.OBSERVATIONS][obs_id][cfg.EVENTS]:

            if (
                self.filtered_behaviors
                and event[cfg.PJ_OBS_FIELDS[self.playerType][cfg.BEHAVIOR_CODE]] not in self.filtered_behaviors
            ):
                continue

            if (
                self.filtered_subjects
                and event[cfg.PJ_OBS_FIELDS[self.playerType][cfg.SUBJECT]] not in self.filtered_subjects
            ):
                continue

            if self.filtered_behaviors or self.filtered_subjects:
                self.twEvents.insertRow(self.twEvents.rowCount())

            for field_type in cfg.TW_EVENTS_FIELDS[self.playerType]:

                if field_type in cfg.PJ_EVENTS_FIELDS[self.playerType]:

                    field = event[cfg.PJ_OBS_FIELDS[self.playerType][field_type]]
                    if field_type == "time":
                        field = str(util.convertTime(self.timeFormat, field))
                    if field_type == cfg.IMAGE_INDEX:
                        field = str(round(field))

                    self.twEvents.setItem(row, cfg.TW_OBS_FIELD[self.playerType][field_type], QTableWidgetItem(field))

                else:
                    self.twEvents.setItem(row, cfg.TW_OBS_FIELD[self.playerType][field_type], QTableWidgetItem(""))

            row += 1

        self.update_events_start_stop()

        logging.debug("end load events from obs")

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
        for idx in self.bcm_dict:
            if self.bcm_dict[idx] is not None:
                self.bcm_dict[idx].close()
            self.bcm_dict[idx] = None

        logging.debug("function: close_tool_windows finished")

    def set_recent_projects_menu(self):
        """
        set the recent projects submenu
        """
        self.menuRecent_projects.clear()
        for project_file_path in self.recent_projects:
            if pl.Path(project_file_path).is_file():
                action = QAction(self, visible=False, triggered=self.open_project_activated)
                action.setText(project_file_path)
                action.setVisible(True)
                self.menuRecent_projects.addAction(action)

    def edit_project_activated(self):
        """
        edit project menu option triggered
        """
        self.edit_project(cfg.EDIT)

    def display_statusbar_info(self, obs_id: str):
        """
        display information about obs_id observation in status bar:
        time offset, observation time interval
        """

        logging.debug(f"function: display statusbar info: {obs_id}")

        try:
            if self.pj[cfg.OBSERVATIONS][obs_id][cfg.TIME_OFFSET]:
                time_offset = 0
                if self.timeFormat == cfg.S:
                    time_offset = self.pj[cfg.OBSERVATIONS][obs_id][cfg.TIME_OFFSET]
                if self.timeFormat == cfg.HHMMSS:
                    time_offset = util.seconds2time(self.pj[cfg.OBSERVATIONS][obs_id][cfg.TIME_OFFSET])
                self.lbTimeOffset.setText(f"Time offset: <b>{time_offset}</b>")
            else:
                self.lbTimeOffset.clear()
        except Exception:
            logging.debug("error in time offset display")
            pass

        try:
            if cfg.OBSERVATION_TIME_INTERVAL in self.pj[cfg.OBSERVATIONS][obs_id]:
                if self.pj[cfg.OBSERVATIONS][obs_id][cfg.OBSERVATION_TIME_INTERVAL] != [0, 0]:

                    if self.timeFormat == cfg.HHMMSS:
                        start_time = util.seconds2time(
                            self.pj[cfg.OBSERVATIONS][obs_id][cfg.OBSERVATION_TIME_INTERVAL][0]
                        )
                        stop_time = util.seconds2time(
                            self.pj[cfg.OBSERVATIONS][obs_id][cfg.OBSERVATION_TIME_INTERVAL][1]
                        )
                    if self.timeFormat == cfg.S:
                        start_time = f"{self.pj[cfg.OBSERVATIONS][obs_id][cfg.OBSERVATION_TIME_INTERVAL][0]:.3f}"
                        stop_time = f"{self.pj[cfg.OBSERVATIONS][obs_id][cfg.OBSERVATION_TIME_INTERVAL][1]:.3f}"

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
        for idx in self.pj[cfg.ETHOGRAM]:
            if self.pj[cfg.ETHOGRAM][idx][cfg.BEHAVIOR_CODE] == code:
                return self.pj[cfg.ETHOGRAM][idx][cfg.TYPE]
        return None

    def extract_observed_behaviors(self, selected_observations, selectedSubjects):
        """
        extract unique behaviors codes from obs_id observation
        """

        observed_behaviors = []

        # extract events from selected observations
        all_events = [
            self.pj[cfg.OBSERVATIONS][x][cfg.EVENTS] for x in self.pj[cfg.OBSERVATIONS] if x in selected_observations
        ]

        for events in all_events:
            for event in events:
                if event[cfg.EVENT_SUBJECT_FIELD_IDX] in selectedSubjects or (
                    not event[cfg.EVENT_SUBJECT_FIELD_IDX] and cfg.NO_FOCAL_SUBJECT in selectedSubjects
                ):
                    observed_behaviors.append(event[cfg.EVENT_BEHAVIOR_FIELD_IDX])

        # remove duplicate
        observed_behaviors = list(set(observed_behaviors))

        return observed_behaviors

    def plot_events_triggered(self, mode: str = "list"):
        """
        plot events in time diagram
        """
        if mode == "list":
            _, selected_observations = select_observations.select_observations(
                self.pj, cfg.MULTIPLE, windows_title="Select observations for plotting events"
            )

            if not selected_observations:
                return
        if mode == "current" and self.observationId:
            selected_observations = [self.observationId]
        # check if state events are paired
        out = ""
        not_paired_obs_list = []
        for obs_id in selected_observations:
            r, msg = project_functions.check_state_events_obs(
                obs_id, self.pj[cfg.ETHOGRAM], self.pj[cfg.OBSERVATIONS][obs_id], self.timeFormat
            )

            if not r:
                out += f"Observation: <strong>{obs_id}</strong><br>{msg}<br>"
                not_paired_obs_list.append(obs_id)

        if out:
            out = "The observations with UNPAIRED state events will be removed from the plot<br><br>" + out
            self.results = dialog.Results_dialog()
            self.results.setWindowTitle(cfg.programName + " - Check selected observations")
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
            if self.pj[cfg.OBSERVATIONS][obs_id][cfg.EVENTS]:
                flag_no_events = False
                break
        if flag_no_events:
            QMessageBox.warning(self, cfg.programName, "No events found in the selected observations")
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

            item, ok = QInputDialog.getItem(
                self, "Select the file format", "Available formats", ["PNG", "SVG", "PDF", "EPS", "PS"], 0, False
            )
            if ok and item:
                file_format = item.lower()
            else:
                return

        (max_obs_length, _) = observation_operations.observation_length(self.pj, selected_observations)
        if max_obs_length == -1:  # media length not available, user choose to not use events
            return

        parameters = select_subj_behav.choose_obs_subj_behav_category(
            self,
            selected_observations,
            maxTime=max_obs_length,
            flagShowExcludeBehaviorsWoEvents=True,
            by_category=False,
        )

        if not parameters[cfg.SELECTED_SUBJECTS] or not parameters[cfg.SELECTED_BEHAVIORS]:
            QMessageBox.warning(self, cfg.programName, "Select subject(s) and behavior(s) to plot")
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

        _, selected_observations = select_observations.select_observations(
            self.pj, cfg.MULTIPLE, windows_title="Select one observation for behaviors bar plot"
        )

        if not selected_observations:
            return

        # check if state events are paired
        out = ""
        not_paired_obs_list = []
        for obsId in selected_observations:
            r, msg = project_functions.check_state_events_obs(
                obsId, self.pj[cfg.ETHOGRAM], self.pj[cfg.OBSERVATIONS][obsId], self.timeFormat
            )

            if not r:
                out += f"Observation: <strong>{obsId}</strong><br>{msg}<br>"
                not_paired_obs_list.append(obsId)

        if out:
            out = "The observations with UNPAIRED state events will be removed from the plot<br>br>" + out
            results = dialog.Results_dialog()
            results.setWindowTitle(cfg.programName + " - Check selected observations")
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
            if self.pj[cfg.OBSERVATIONS][obsId][cfg.EVENTS]:
                flag_no_events = False
                break
        if flag_no_events:
            QMessageBox.warning(self, cfg.programName, "No events found in the selected observations")
            return

        max_obs_length = -1
        for obsId in selected_observations:
            totalMediaLength = project_functions.observation_total_length(self.pj[cfg.OBSERVATIONS][obsId])
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
                maxTime=dec(0),
                flagShowIncludeModifiers=False,
                flagShowExcludeBehaviorsWoEvents=True,
            )

        if not parameters[cfg.SELECTED_SUBJECTS] or not parameters[cfg.SELECTED_BEHAVIORS]:
            QMessageBox.warning(self, cfg.programName, "Select subject(s) and behavior(s) to plot")
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

            item, ok = QInputDialog.getItem(
                self, "Select the file format", "Available formats", ["PNG", "SVG", "PDF", "EPS", "PS"], 0, False
            )
            if ok and item:
                output_format = item.lower()
            else:
                return

        r = plot_events.create_behaviors_bar_plot(
            self.pj, selected_observations, parameters, plot_directory, output_format, plot_colors=self.plot_colors
        )
        if "error" in r:
            QMessageBox.warning(self, cfg.programName, r.get("message", "Error on time budget bar plot"))

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
        self.clear_interface()
        self.projectChanged = True
        self.projectChanged = memProjectChanged
        self.load_behaviors_in_twEthogram([self.pj[cfg.ETHOGRAM][x][cfg.BEHAVIOR_CODE] for x in self.pj[cfg.ETHOGRAM]])
        self.load_subjects_in_twSubjects([self.pj[cfg.SUBJECTS][x][cfg.SUBJECT_NAME] for x in self.pj[cfg.SUBJECTS]])
        self.projectFileName = str(pl.Path(project_path).absolute())
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
            if (
                dialog.MessageDialog(
                    cfg.programName,
                    "There is a current observation. What do you want to do?",
                    ["Close observation", "Continue observation"],
                )
                == "Close observation"
            ):
                observation_operations.close_observation(self)
            else:
                return

        if self.projectChanged:
            response = dialog.MessageDialog(
                cfg.programName, "What to do about the current unsaved project?", [cfg.SAVE, cfg.DISCARD, cfg.CANCEL]
            )

            if response == cfg.SAVE:
                if self.save_project_activated() == "not saved":
                    return

            if response == cfg.CANCEL:
                return

        if action.text() == "Open project":
            fn = QFileDialog().getOpenFileName(
                self, "Open project", "", ("Project files (*.boris *.boris.gz);;" "All files (*)")
            )
            file_name = fn[0] if type(fn) is tuple else fn

        else:  # recent project
            file_name = action.text()

        if file_name:
            project_path, project_changed, pj, msg = project_functions.open_project_json(file_name)

            if "error" in pj:
                logging.debug(pj["error"])
                QMessageBox.critical(self, cfg.programName, pj["error"])
            else:
                if msg:
                    QMessageBox.information(self, cfg.programName, msg)

                # check behavior keys
                if project_changed:
                    flag_all_upper = True
                    if pj[cfg.ETHOGRAM]:
                        for idx in pj[cfg.ETHOGRAM]:
                            if pj[cfg.ETHOGRAM][idx]["key"].islower():
                                flag_all_upper = False

                    if pj[cfg.SUBJECTS]:
                        for idx in pj[cfg.SUBJECTS]:
                            if pj[cfg.SUBJECTS][idx]["key"].islower():
                                flag_all_upper = False

                    if (
                        flag_all_upper
                        and dialog.MessageDialog(
                            cfg.programName,
                            (
                                "It is now possible to use <b>lower keys</b> to code behaviors, subjects and modifiers.<br><br>"
                                "In this project all the behavior and subject keys are upper case.<br>"
                                "Do you want to convert them in lower case?"
                            ),
                            [cfg.YES, cfg.NO],
                        )
                        == cfg.YES
                    ):
                        for idx in pj[cfg.ETHOGRAM]:
                            pj[cfg.ETHOGRAM][idx]["key"] = pj[cfg.ETHOGRAM][idx]["key"].lower()
                            # convert modifier short cuts to lower case
                            for modifier_set in pj[cfg.ETHOGRAM][idx]["modifiers"]:
                                try:
                                    for idx2, value in enumerate(
                                        pj[cfg.ETHOGRAM][idx]["modifiers"][modifier_set]["values"]
                                    ):
                                        if re.findall(r"\((\w+)\)", value):
                                            pj[cfg.ETHOGRAM][idx]["modifiers"][modifier_set]["values"][idx2] = (
                                                value.split("(")[0]
                                                + "("
                                                + re.findall(r"\((\w+)\)", value)[0].lower()
                                                + ")"
                                                + value.split(")")[-1]
                                            )
                                except Exception:
                                    logging.warning("error during converion of modifier short cut to lower case")

                        for idx in pj[cfg.SUBJECTS]:
                            pj[cfg.SUBJECTS][idx]["key"] = pj[cfg.SUBJECTS][idx]["key"].lower()

                self.load_project(project_path, project_changed, pj)
                del pj

    def import_project_from_observer_template(self):
        """
        import a project from a Noldus Observer template
        """
        # check if current observation
        if self.observationId:
            if (
                dialog.MessageDialog(
                    cfg.programName,
                    "There is a current observation. What do you want to do?",
                    ["Close observation", "Continue observation"],
                )
                == "Close observation"
            ):
                observation_operations.close_observation(self)
            else:
                return

        if self.projectChanged:
            response = dialog.MessageDialog(
                cfg.programName, "What to do about the current unsaved project?", [cfg.SAVE, cfg.DISCARD, cfg.CANCEL]
            )

            if response == cfg.SAVE:
                if self.save_project_activated() == "not saved":
                    return

            if response == cfg.CANCEL:
                return

        fn = QFileDialog().getOpenFileName(
            self, "Import project from template", "", "Noldus Observer templates (*.otx *.otb);;All files (*)"
        )
        file_name = fn[0] if type(fn) is tuple else fn

        if file_name:
            pj = otx_parser.otx_to_boris(file_name)
            if "error" in pj:
                QMessageBox.critical(self, cfg.programName, pj["error"])
            else:
                if "msg" in pj:
                    QMessageBox.warning(self, cfg.programName, pj["msg"])
                    del pj["msg"]
                self.load_project("", True, pj)

    def clear_interface(self, flag_new: bool = True):
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
                cfg.programName,
                "There is a current observation. What do you want to do?",
                ["Close observation", "Continue observation"],
            )
            if response == "Close observation":
                observation_operations.close_observation(self)
            if response == "Continue observation":
                return

        if self.projectChanged:
            response = dialog.MessageDialog(
                cfg.programName, "What to do about the current unsaved project?", [cfg.SAVE, cfg.DISCARD, cfg.CANCEL]
            )
            if response == cfg.SAVE:
                if self.save_project_activated() == "not saved":
                    return

            if response == cfg.CANCEL:
                return

        self.projectChanged = False
        self.setWindowTitle(cfg.programName)

        self.pj = dict(cfg.EMPTY_PROJECT)

        self.project = False
        config_file.read(self)
        menu_options.update_menu(self)

        self.clear_interface(flag_new=False)

        self.w_obs_info.setVisible(False)

    def edit_project(self, mode: str):
        """
        project management

        Args:
            mode (str): new/edit
        """

        # ask if current observation should be closed to edit the project
        if self.observationId:
            # hide data plot
            self.hide_data_files()
            response = dialog.MessageDialog(
                cfg.programName,
                "The current observation will be closed. Do you want to continue?",
                [cfg.YES, cfg.NO],
            )
            if response == cfg.NO:
                self.show_data_files()
                return
            else:
                observation_operations.close_observation(self)

        if mode == cfg.NEW:
            if self.projectChanged:
                response = dialog.MessageDialog(
                    cfg.programName,
                    "What to do with the current unsaved project?",
                    [cfg.SAVE, cfg.DISCARD, cfg.CANCEL],
                )

                if response == cfg.SAVE:
                    self.save_project_activated()

                if response == cfg.CANCEL:
                    return

            # empty main window tables
            for w in [self.twEthogram, self.twSubjects, self.twEvents]:
                w.setRowCount(0)  # behaviors

        newProjectWindow = projectDialog()

        # pass copy of self.pj
        newProjectWindow.pj = dict(self.pj)

        if self.project_window_geometry:
            newProjectWindow.restoreGeometry(self.project_window_geometry)
        else:
            newProjectWindow.resize(800, 400)

        newProjectWindow.setWindowTitle(f"{mode} project")
        newProjectWindow.tabProject.setCurrentIndex(0)  # project information

        newProjectWindow.obs = newProjectWindow.pj[cfg.ETHOGRAM]
        newProjectWindow.subjects_conf = newProjectWindow.pj[cfg.SUBJECTS]

        newProjectWindow.rbSeconds.setChecked(newProjectWindow.pj[cfg.TIME_FORMAT] == cfg.S)
        newProjectWindow.rbHMS.setChecked(newProjectWindow.pj[cfg.TIME_FORMAT] == cfg.HHMMSS)

        if mode == cfg.NEW:
            newProjectWindow.dteDate.setDateTime(QDateTime.currentDateTime())
            newProjectWindow.lbProjectFilePath.setText("")
            newProjectWindow.lb_project_format_version.setText(f"Project format version: {cfg.project_format_version}")

        if mode == cfg.EDIT:

            if newProjectWindow.pj[cfg.PROJECT_NAME]:
                newProjectWindow.leProjectName.setText(newProjectWindow.pj[cfg.PROJECT_NAME])

            newProjectWindow.lbProjectFilePath.setText(f"Project file path: {self.projectFileName}")

            newProjectWindow.lb_project_format_version.setText(
                f"Project format version: {newProjectWindow.pj[cfg.PROJECT_VERSION]}"
            )

            if newProjectWindow.pj[cfg.PROJECT_DESCRIPTION]:
                newProjectWindow.teDescription.setPlainText(newProjectWindow.pj[cfg.PROJECT_DESCRIPTION])

            if newProjectWindow.pj[cfg.PROJECT_DATE]:
                newProjectWindow.dteDate.setDateTime(
                    QDateTime.fromString(newProjectWindow.pj[cfg.PROJECT_DATE], "yyyy-MM-ddThh:mm:ss")
                )
            else:
                newProjectWindow.dteDate.setDateTime(QDateTime.currentDateTime())

            # load subjects in editor
            if newProjectWindow.pj[cfg.SUBJECTS]:
                for idx in util.sorted_keys(newProjectWindow.pj[cfg.SUBJECTS]):
                    newProjectWindow.twSubjects.setRowCount(newProjectWindow.twSubjects.rowCount() + 1)
                    for i, field in enumerate(cfg.subjectsFields):
                        item = QTableWidgetItem(newProjectWindow.pj[cfg.SUBJECTS][idx][field])
                        newProjectWindow.twSubjects.setItem(newProjectWindow.twSubjects.rowCount() - 1, i, item)

                newProjectWindow.twSubjects.resizeColumnsToContents()

            # ethogram
            if newProjectWindow.pj[cfg.ETHOGRAM]:
                for i in util.sorted_keys(newProjectWindow.pj[cfg.ETHOGRAM]):
                    newProjectWindow.twBehaviors.setRowCount(newProjectWindow.twBehaviors.rowCount() + 1)
                    for field in cfg.behavioursFields:
                        item = QTableWidgetItem()
                        if field == cfg.TYPE:
                            item.setText(cfg.DEFAULT_BEHAVIOR_TYPE)
                        if field in newProjectWindow.pj[cfg.ETHOGRAM][i]:
                            if field == "modifiers":
                                item.setText(
                                    json.dumps(newProjectWindow.pj[cfg.ETHOGRAM][i][field])
                                    if newProjectWindow.pj[cfg.ETHOGRAM][i][field]
                                    else ""
                                )
                            else:
                                item.setText(newProjectWindow.pj[cfg.ETHOGRAM][i][field])
                        else:
                            item.setText("")
                        # cell with gray background (not editable but double-click needed to change value)
                        if field in [cfg.TYPE, "category", "excluded", "coding map", "modifiers"]:
                            item.setFlags(Qt.ItemIsEnabled)
                            item.setBackground(QColor(230, 230, 230))

                        newProjectWindow.twBehaviors.setItem(
                            newProjectWindow.twBehaviors.rowCount() - 1, cfg.behavioursFields[field], item
                        )

            # load independent variables
            if cfg.INDEPENDENT_VARIABLES in newProjectWindow.pj:
                for i in util.sorted_keys(newProjectWindow.pj[cfg.INDEPENDENT_VARIABLES]):
                    newProjectWindow.twVariables.setRowCount(newProjectWindow.twVariables.rowCount() + 1)
                    for idx, field in enumerate(cfg.tw_indVarFields):
                        item = QTableWidgetItem("")
                        if field in newProjectWindow.pj[cfg.INDEPENDENT_VARIABLES][i]:
                            item.setText(newProjectWindow.pj[cfg.INDEPENDENT_VARIABLES][i][field])

                        newProjectWindow.twVariables.setItem(newProjectWindow.twVariables.rowCount() - 1, idx, item)

                newProjectWindow.twVariables.resizeColumnsToContents()

            # behaviors coding map
            if cfg.BEHAVIORS_CODING_MAP in newProjectWindow.pj:
                for bcm in newProjectWindow.pj[cfg.BEHAVIORS_CODING_MAP]:
                    newProjectWindow.twBehavCodingMap.setRowCount(newProjectWindow.twBehavCodingMap.rowCount() + 1)
                    newProjectWindow.twBehavCodingMap.setItem(
                        newProjectWindow.twBehavCodingMap.rowCount() - 1, 0, QTableWidgetItem(bcm["name"])
                    )
                    codes = ", ".join([bcm["areas"][idx]["code"] for idx in bcm["areas"]])
                    newProjectWindow.twBehavCodingMap.setItem(
                        newProjectWindow.twBehavCodingMap.rowCount() - 1, 1, QTableWidgetItem(codes)
                    )

            # time converters
            if cfg.CONVERTERS in newProjectWindow.pj:
                newProjectWindow.converters = newProjectWindow.pj[cfg.CONVERTERS]
                newProjectWindow.load_converters_in_table()

        newProjectWindow.dteDate.setDisplayFormat("yyyy-MM-dd hh:mm:ss")

        if mode == cfg.NEW:
            newProjectWindow.pj = dict(cfg.EMPTY_PROJECT)

        # warning
        if mode == cfg.EDIT and self.pj[cfg.OBSERVATIONS]:

            if (
                dialog.MessageDialog(
                    cfg.programName,
                    (
                        "Please note that editing the project may interfere with the coded events in your previous observations.<br>"
                        "For example modifying a behavior code, renaming a subject or modifying the modifiers sets "
                        "can unvalidate your previous observations.<br>"
                        "Remember to make a backup of your project."
                    ),
                    [cfg.CANCEL, "Edit"],
                )
                == cfg.CANCEL
            ):
                return

        if newProjectWindow.exec_():  # button OK returns True

            if mode == cfg.NEW:
                self.projectFileName = ""
                self.projectChanged = True

            if mode == cfg.EDIT:
                if not self.projectChanged:
                    self.projectChanged = dict(self.pj) != dict(newProjectWindow.pj)

            # retrieve project dict from window
            self.pj = dict(newProjectWindow.pj)
            self.project = True

            # time format
            if newProjectWindow.rbSeconds.isChecked():
                self.timeFormat = cfg.S

            if newProjectWindow.rbHMS.isChecked():
                self.timeFormat = cfg.HHMMSS

            # configuration
            if newProjectWindow.lbObservationsState.text() != "":
                QMessageBox.warning(self, cfg.programName, newProjectWindow.lbObservationsState.text())
            else:
                # ethogram
                self.load_behaviors_in_twEthogram(
                    [self.pj[cfg.ETHOGRAM][x][cfg.BEHAVIOR_CODE] for x in self.pj[cfg.ETHOGRAM]]
                )
                # subjects
                self.load_subjects_in_twSubjects(
                    [self.pj[cfg.SUBJECTS][x][cfg.SUBJECT_NAME] for x in self.pj[cfg.SUBJECTS]]
                )

            self.clear_interface()

            menu_options.update_menu(self)

        self.project_window_geometry = newProjectWindow.saveGeometry()

        del newProjectWindow

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

        # check if project contains IMAGES observations
        flag_images_obs = False
        for obs_id in self.pj[cfg.OBSERVATIONS]:
            if self.pj[cfg.OBSERVATIONS][obs_id][cfg.TYPE] == cfg.IMAGES:
                flag_images_obs = True
                break

        if flag_images_obs:
            self.pj[cfg.PROJECT_VERSION] = ".".join((str(x) for x in cfg.IMAGES_OBS_PROJECT_MIN_VERSION))
        else:
            self.pj[cfg.PROJECT_VERSION] = cfg.project_format_version

        try:
            if projectFileName.endswith(".boris.gz"):
                with gzip.open(projectFileName, mode="wt", encoding="utf-8") as f_out:
                    f_out.write(json.dumps(self.pj, default=util.decimal_default))
            else:  # .boris and other extensions
                with open(projectFileName, "w") as f_out:
                    f_out.write(json.dumps(self.pj, default=util.decimal_default))

            self.projectChanged = False
            self.save_project_json_started = False

            logging.debug(f"end save_project_json function")
            return 0

        except PermissionError:
            QMessageBox.critical(
                None,
                cfg.programName,
                f"Permission denied to save the project file. Try another directory",
                QMessageBox.Ok | QMessageBox.Default,
                QMessageBox.NoButton,
            )
            self.save_project_json_started = False
            return 1

        except Exception:
            dialog.error_message()

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
            ("Project files (*.boris);;" "Compressed project files (*.boris.gz);;" "All files (*)"),
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
                if pl.Path(project_new_file_name).is_file():
                    if (
                        dialog.MessageDialog(
                            cfg.programName,
                            f"The file {project_new_file_name} already exists.",
                            [cfg.CANCEL, cfg.OVERWRITE],
                        )
                        == cfg.CANCEL
                    ):
                        return "Not saved"
            # add .boris.gz if filter is .boris.gz
            if (
                filtr == "Compressed project files (*.boris.gz)"
                and os.path.splitext(project_new_file_name)[1] != ".boris.gz"
            ):
                if project_new_file_name.endswith(".boris"):
                    project_new_file_name = os.path.splitext(project_new_file_name)[0]
                project_new_file_name += ".boris.gz"
                # check if file name with extension already exists
                if pl.Path(project_new_file_name).is_file():
                    if (
                        dialog.MessageDialog(
                            cfg.programName,
                            f"The file {project_new_file_name} already exists.",
                            [cfg.CANCEL, cfg.OVERWRITE],
                        )
                        == cfg.CANCEL
                    ):
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
                ("Project files (*.boris);;" "Compressed project files (*.boris.gz);;" "All files (*)"),
            )

            if not self.projectFileName:
                return "not saved"

            # add .boris if filter = 'Projects file (*.boris)'
            if filtr == "Project files (*.boris)" and os.path.splitext(self.projectFileName)[1] != ".boris":
                if self.projectFileName.endswith(".boris.gz"):
                    self.projectFileName = os.path.splitext(os.path.splitext(self.projectFileName)[0])[0]
                self.projectFileName += ".boris"
                # check if file name with extension already exists
                if pl.Path(self.projectFileName).is_file():
                    if (
                        dialog.MessageDialog(
                            cfg.programName,
                            f"The file {self.projectFileName} already exists.",
                            [cfg.CANCEL, cfg.OVERWRITE],
                        )
                        == cfg.CANCEL
                    ):
                        self.projectFileName = ""
                        return ""

            # add .boris.gz if filter is .boris.gz
            if (
                filtr == "Compressed project files (*.boris.gz)"
                and os.path.splitext(self.projectFileName)[1] != ".boris.gz"
            ):
                if self.projectFileName.endswith(".boris"):
                    self.projectFileName = os.path.splitext(self.projectFileName)[0]

                self.projectFileName += ".boris.gz"
                # check if file name with extension already exists
                if pl.Path(self.projectFileName).is_file():
                    if (
                        dialog.MessageDialog(
                            cfg.programName,
                            f"The file {self.projectFileName} already exists.",
                            [cfg.CANCEL, cfg.OVERWRITE],
                        )
                        == cfg.CANCEL
                    ):
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

        if self.pj[cfg.OBSERVATIONS][self.observationId].get(cfg.START_FROM_CURRENT_TIME, False):
            current_time = util.seconds_of_day(datetime.datetime.now())
        elif self.pj[cfg.OBSERVATIONS][self.observationId].get(cfg.START_FROM_CURRENT_EPOCH_TIME, False):
            current_time = time.time()
        else:
            current_time = self.getLaps()

        self.lb_current_media_time.setText(util.convertTime(self.timeFormat, current_time))

        # extract State events
        self.currentStates = {}
        # add states for no focal subject

        self.currentStates = util.get_current_states_modifiers_by_subject(
            util.state_behavior_codes(self.pj[cfg.ETHOGRAM]),
            self.pj[cfg.OBSERVATIONS][self.observationId][cfg.EVENTS],
            dict(self.pj[cfg.SUBJECTS], **{"": {cfg.SUBJECT_NAME: ""}}),
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
        if self.pj[cfg.OBSERVATIONS][self.observationId].get(cfg.SCAN_SAMPLING_TIME, 0):
            if int(current_time) % self.pj[cfg.OBSERVATIONS][self.observationId][cfg.SCAN_SAMPLING_TIME] == 0:
                self.beep("beep")
                self.liveTimer.stop()
                self.pb_live_obs.setText("Live observation stopped (scan sampling)")

        # observation time interval
        if self.pj[cfg.OBSERVATIONS][self.observationId].get(cfg.OBSERVATION_TIME_INTERVAL, [0, 0])[1]:
            if (
                current_time
                >= self.pj[cfg.OBSERVATIONS][self.observationId].get(cfg.OBSERVATION_TIME_INTERVAL, [0, 0])[1]
            ):
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

            if self.timeFormat == cfg.HHMMSS:
                if self.pj[cfg.OBSERVATIONS][self.observationId].get(cfg.START_FROM_CURRENT_TIME, False):
                    self.lb_current_media_time.setText(datetime.datetime.now().isoformat(" ").split(" ")[1][:12])
                elif self.pj[cfg.OBSERVATIONS][self.observationId].get(cfg.START_FROM_CURRENT_EPOCH_TIME, False):
                    self.lb_current_media_time.setText(datetime.datetime.fromtimestamp(time.time()))
                else:
                    self.lb_current_media_time.setText("00:00:00.000")

            if self.timeFormat == cfg.S:
                self.lb_current_media_time.setText("0.000")

        else:
            if self.twEvents.rowCount():
                if dialog.MessageDialog(cfg.programName, "Delete the current events?", [cfg.YES, cfg.NO]) == cfg.YES:
                    self.twEvents.setRowCount(0)
                    self.pj[cfg.OBSERVATIONS][self.observationId][cfg.EVENTS] = []
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

        _, selected_observations = select_observations.select_observations(
            self.pj, cfg.MULTIPLE, windows_title="Select observations for creating subtitles"
        )

        if not selected_observations:
            return

        # check if state events are paired
        out = ""
        not_paired_obs_list = []
        for obsId in selected_observations:
            r, msg = project_functions.check_state_events_obs(
                obsId, self.pj[cfg.ETHOGRAM], self.pj[cfg.OBSERVATIONS][obsId], self.timeFormat
            )

            if not r:
                out += f"Observation: <strong>{obsId}</strong><br>{msg}<br>"
                not_paired_obs_list.append(obsId)

        if out:
            out = "The observations with UNPAIRED state events will be removed from the plot<br><br>" + out
            self.results = dialog.Results_dialog()
            self.results.setWindowTitle(cfg.programName + " - Check selected observations")
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
        if not parameters[cfg.SELECTED_SUBJECTS] or not parameters[cfg.SELECTED_BEHAVIORS]:
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
                cfg.programName,
                f"Error creating subtitles: {msg}",
                QMessageBox.Ok | QMessageBox.Default,
                QMessageBox.NoButton,
            )

    def next_frame(self):
        """
        show next frame
        """
        if self.playerType == cfg.IMAGES:
            if self.image_idx < len(self.images_list) - 1:
                self.image_idx += 1
                self.extract_frame(self.dw_player[0])

        if self.playerType == cfg.MEDIA:
            for dw in self.dw_player:
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
        if self.playerType == cfg.IMAGES:
            if self.image_idx:
                self.image_idx -= 1
                self.extract_frame(self.dw_player[0])

        if self.playerType == cfg.MEDIA:
            for dw in self.dw_player:
                dw.player.frame_back_step()
                self.plot_timer_out()
                for idx in self.plot_data:
                    self.timer_plot_data_out(self.plot_data[idx])

                if self.geometric_measurements_mode:
                    self.extract_frame(dw)

            if self.geometric_measurements_mode:
                self.redraw_measurements()

            self.actionPlay.setIcon(QIcon(":/play"))

    def run_event_outside(self):
        """
        run external prog with events information
        """
        QMessageBox.warning(self, cfg.programName, "Function not yet implemented")
        return

        if not self.observationId:
            self.no_observation()
            return

        if self.twEvents.selectedItems():
            row_s = self.twEvents.selectedItems()[0].row()
            row_e = self.twEvents.selectedItems()[-1].row()
            eventtime_s = self.pj[cfg.OBSERVATIONS][self.observationId][cfg.EVENTS][row_s][0]
            eventtime_e = self.pj[cfg.OBSERVATIONS][self.observationId][cfg.EVENTS][row_e][0]

            durations = []  # in seconds

            # TODO: check for 2nd player
            for mediaFile in self.pj[cfg.OBSERVATIONS][self.observationId][cfg.FILE][cfg.PLAYER1]:
                durations.append(self.pj[cfg.OBSERVATIONS][self.observationId][cfg.MEDIA_INFO]["length"][mediaFile])

            mediaFileIdx_s = [idx1 for idx1, x in enumerate(durations) if eventtime_s >= sum(durations[0:idx1])][-1]
            media_path_s = self.pj[cfg.OBSERVATIONS][self.observationId][cfg.FILE][cfg.PLAYER1][mediaFileIdx_s]

            mediaFileIdx_e = [idx1 for idx1, x in enumerate(durations) if eventtime_e >= sum(durations[0:idx1])][-1]
            media_path_e = self.pj[cfg.OBSERVATIONS][self.observationId][cfg.FILE][cfg.PLAYER1][mediaFileIdx_e]

            # calculate time for current media file in case of many queued media files

            print(mediaFileIdx_s)
            print(type(eventtime_s))
            print(durations)

            eventtime_onmedia_s = round(eventtime_s - util.float2decimal(sum(durations[0:mediaFileIdx_s])), 3)
            eventtime_onmedia_e = round(eventtime_e - util.float2decimal(sum(durations[0:mediaFileIdx_e])), 3)

            print(row_s, media_path_s, eventtime_s, eventtime_onmedia_s)
            print(self.pj[cfg.OBSERVATIONS][self.observationId][cfg.EVENTS][row_s])

            print(row_e, media_path_e, eventtime_e, eventtime_onmedia_e)
            print(self.pj[cfg.OBSERVATIONS][self.observationId][cfg.EVENTS][row_e])

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

    def no_media(self):
        QMessageBox.warning(self, cfg.programName, "There is no media available")

    def no_project(self):
        QMessageBox.warning(self, cfg.programName, "There is no project")

    def no_observation(self):
        QMessageBox.warning(self, cfg.programName, "There is no current observation")

    def twEthogram_doubleClicked(self):
        """
        add event by double-clicking the ethogram list
        """
        if not self.observationId:
            self.no_observation()
            return
        if self.playerType in cfg.VIEWERS:
            QMessageBox.critical(
                self,
                cfg.programName,
                ("The current observation is opened in VIEW mode.\n" "It is not allowed to log events in this mode."),
            )
            return

        if self.twEthogram.selectedIndexes():
            ethogram_row = self.twEthogram.selectedIndexes()[0].row()
            code = self.twEthogram.item(ethogram_row, 1).text()

            ethogram_idx = [x for x in self.pj[cfg.ETHOGRAM] if self.pj[cfg.ETHOGRAM][x][cfg.BEHAVIOR_CODE] == code][0]

            event = self.full_event(ethogram_idx)
            # MEDIA / LIVE
            """
            if self.pj[cfg.OBSERVATIONS][self.observationId][cfg.TYPE] in (cfg.MEDIA, cfg.LIVE):
                time_ = self.getLaps()
            """

            # IMAGES
            if self.pj[cfg.OBSERVATIONS][self.observationId][cfg.TYPE] == cfg.IMAGES:
                event[cfg.IMAGE_INDEX] = self.image_idx + 1
                event[cfg.IMAGE_PATH] = self.images_list[self.image_idx]

            self.write_event(event, self.getLaps())

    def actionUser_guide_triggered(self):
        """
        open user guide URL if it exists otherwise open user guide URL
        """
        user_guide_file = os.path.dirname(os.path.realpath(__file__)) + "/boris_user_guide.pdf"
        if os.path.isfile(user_guide_file):
            if sys.platform.startswith("linux"):
                subprocess.call(["xdg-open", user_guide_file])
            else:
                os.startfile(user_guide_file)
        else:
            QDesktopServices.openUrl(QUrl("http://boris.readthedocs.org"))

    def click_signal_from_behaviors_coding_map(self, bcm_name, behavior_codes_list: list):
        """
        handle click signal from BehaviorsCodingMapWindowClass widget
        """

        for code in behavior_codes_list:
            try:
                behavior_idx = [
                    key for key in self.pj[cfg.ETHOGRAM] if self.pj[cfg.ETHOGRAM][key][cfg.BEHAVIOR_CODE] == code
                ][0]
            except Exception:
                QMessageBox.critical(
                    self, cfg.programName, f"The code <b>{code}</b> of behavior coding map does not exist in ethogram."
                )
                return

            event = self.full_event(behavior_idx)

            # IMAGES
            if self.pj[cfg.OBSERVATIONS][self.observationId][cfg.TYPE] == cfg.IMAGES:
                event[cfg.IMAGE_INDEX] = self.image_idx + 1
                event[cfg.IMAGE_PATH] = self.images_list[self.image_idx]

            self.write_event(event, self.getLaps())

    def keypress_signal_from_behaviors_coding_map(self, event):
        """
        receive signal from behaviors coding map
        """
        self.keyPressEvent(event)

    def video_slider_sliderMoved(self):
        """
        media position slider moved
        adjust media position
        """

        if self.playerType != cfg.MEDIA:
            return

        logging.debug(f"video_slider moved: {self.video_slider.value() / (cfg.SLIDER_MAXIMUM - 1)}")

        if self.pj[cfg.OBSERVATIONS][self.observationId][cfg.TYPE] in [cfg.MEDIA]:
            self.user_move_slider = True
            sliderPos = self.video_slider.value() / (cfg.SLIDER_MAXIMUM - 1)
            videoPosition = sliderPos * self.dw_player[0].player.duration
            self.dw_player[0].player.command("seek", str(videoPosition), "absolute")

            self.plot_timer_out()

    def video_slider_sliderReleased(self):
        """
        adjust frame when slider is moved by user
        """

        logging.debug(f"video_slider released: {self.video_slider.value() / (cfg.SLIDER_MAXIMUM - 1)}")
        self.user_move_slider = False

    def get_events_current_row(self):
        """
        get events current row corresponding to video/frame-by-frame position
        paint twEvents with tracking cursor
        scroll to corresponding event
        """

        if self.pj[cfg.OBSERVATIONS][self.observationId][cfg.EVENTS]:
            ct = self.getLaps()
            # add time offset if any
            ct += dec(self.pj[cfg.OBSERVATIONS][self.observationId][cfg.TIME_OFFSET])

            if (
                ct
                >= self.pj[cfg.OBSERVATIONS][self.observationId][cfg.EVENTS][-1][
                    cfg.TW_OBS_FIELD[self.playerType]["time"]
                ]
            ):
                self.events_current_row = len(self.pj[cfg.OBSERVATIONS][self.observationId][cfg.EVENTS])
            else:
                cr_list = [
                    idx
                    for idx, x in enumerate(self.pj[cfg.OBSERVATIONS][self.observationId][cfg.EVENTS][:-1])
                    if x[0] <= ct
                    and self.pj[cfg.OBSERVATIONS][self.observationId][cfg.EVENTS][idx + 1][
                        cfg.TW_OBS_FIELD[self.playerType]["time"]
                    ]
                    > ct
                ]

                if cr_list:
                    self.events_current_row = cr_list[0]
                    if not self.trackingCursorAboveEvent:
                        self.events_current_row += 1
                else:
                    self.events_current_row = -1

            self.twEvents.setItemDelegate(events_cursor.StyledItemDelegateTriangle(self.events_current_row))

            if self.twEvents.item(self.events_current_row, 0):
                self.twEvents.scrollToItem(
                    self.twEvents.item(self.events_current_row, 0), QAbstractItemView.EnsureVisible
                )

    def show_current_states_in_subjects_table(self):
        """
        show current state(s) for all subjects (including "No focal subject") in subjects table
        """

        for i in range(self.twSubjects.rowCount()):
            try:
                if self.twSubjects.item(i, 1).text() == cfg.NO_FOCAL_SUBJECT:
                    self.twSubjects.item(i, len(cfg.subjectsFields)).setText(",".join(self.currentStates[""]))
                else:
                    self.twSubjects.item(i, len(cfg.subjectsFields)).setText(
                        ",".join(self.currentStates[self.subject_name_index[self.twSubjects.item(i, 1).text()]])
                    )
            except KeyError:
                self.twSubjects.item(i, len(cfg.subjectsFields)).setText("")

    def sync_time(self, n_player: int, new_time: float) -> None:
        """
        synchronize player n_player to time new_time
        if required load the media file corresponding to cumulative time in player

        Args:
            n_player (int): player
            new_time (int): new time in ms
        """

        if self.dw_player[n_player].player.playlist_count == 1:

            if self.pj[cfg.OBSERVATIONS][self.observationId][cfg.MEDIA_INFO]["offset"][str(n_player + 1)]:

                if self.pj[cfg.OBSERVATIONS][self.observationId][cfg.MEDIA_INFO]["offset"][str(n_player + 1)] > 0:

                    if (
                        new_time
                        < self.pj[cfg.OBSERVATIONS][self.observationId][cfg.MEDIA_INFO]["offset"][str(n_player + 1)]
                    ):
                        # hide video if time < offset
                        self.dw_player[n_player].stack.setCurrentIndex(1)
                    else:

                        if new_time - dec(
                            self.pj[cfg.OBSERVATIONS][self.observationId][cfg.MEDIA_INFO]["offset"][str(n_player + 1)]
                        ) > sum(self.dw_player[n_player].media_durations):
                            # hide video if required time > video time + offset
                            self.dw_player[n_player].stack.setCurrentIndex(1)
                        else:
                            # show video
                            self.dw_player[n_player].stack.setCurrentIndex(0)

                            self.seek_mediaplayer(
                                new_time
                                - dec(
                                    self.pj[cfg.OBSERVATIONS][self.observationId][cfg.MEDIA_INFO]["offset"][
                                        str(n_player + 1)
                                    ]
                                ),
                                player=n_player,
                            )

                elif self.pj[cfg.OBSERVATIONS][self.observationId][cfg.MEDIA_INFO]["offset"][str(n_player + 1)] < 0:

                    if new_time - dec(
                        self.pj[cfg.OBSERVATIONS][self.observationId][cfg.MEDIA_INFO]["offset"][str(n_player + 1)]
                    ) > sum(self.dw_player[n_player].media_durations):
                        # hide video if required time > video time + offset
                        self.dw_player[n_player].stack.setCurrentIndex(1)
                    else:
                        self.dw_player[n_player].stack.setCurrentIndex(0)
                        self.seek_mediaplayer(
                            new_time
                            - dec(
                                self.pj[cfg.OBSERVATIONS][self.observationId][cfg.MEDIA_INFO]["offset"][
                                    str(n_player + 1)
                                ]
                            ),
                            player=n_player,
                        )

            else:  # no offset
                self.seek_mediaplayer(new_time, player=n_player)

        elif self.dw_player[n_player].player.playlist_count > 1:

            if new_time < sum(self.dw_player[n_player].media_durations):
                """media_idx = self.dw_player[n_player].media_list.index_of_item(self.dw_player[n_player].mediaplayer.get_media())"""
                media_idx = self.dw_player[n_player].player.playlist_pos

                if (
                    sum(self.dw_player[n_player].media_durations[0:media_idx])
                    < new_time
                    < sum(self.dw_player[n_player].media_durations[0 : media_idx + 1])
                ):
                    # in current media
                    logging.debug(f"{n_player + 1} correct media")
                    self.seek_mediaplayer(
                        new_time - sum(self.dw_player[n_player].media_durations[0:media_idx], player=n_player)
                    )
                else:

                    logging.debug(f"{n_player + 1} not correct media")

                    flag_paused = self.dw_player[n_player].player.pause
                    tot = 0
                    for idx, d in enumerate(self.dw_player[n_player].media_durations):
                        if tot <= new_time < tot + d:

                            self.dw_player[n_player].player.playing_pos = idx
                            if flag_paused:
                                self.dw_player[n_player].player.pause = True
                            self.seek_mediaplayer(
                                new_time - self.dw_player[n_player].media_durations[0:idx], player=n_player
                            )
                            break
                        tot += d

            else:  # end of media list

                logging.debug(f"{n_player + 1} end of media")
                self.dw_player[n_player].player.playlist_pos = self.dw_player[n_player].player.playlist_count - 1
                self.seek_mediaplayer(self.dw_player[n_player].media_durations[-1], player=n_player)

    def video_timer_out(self, value, scroll_slider=True):
        """
        indicate the video current position and total length for cfg.MPV player
        scroll video slider to video position
        Time offset is NOT added!
        """

        if not self.observationId:
            return

        cumulative_time_pos = self.getLaps()

        if value is None:
            current_media_time_pos = 0
        else:
            current_media_time_pos = value

        """
        CRITICAL:root:Traceback (most recent call last):
        File "/home/olivier/projects/BORIS/boris/core.py", line 4086, in timer_out2
            current_media_frame = round(value * self.dw_player[0].player.container_fps) + 1
        IndexError: list index out of range

        """

        # observation time interval
        if self.pj[cfg.OBSERVATIONS][self.observationId].get(cfg.OBSERVATION_TIME_INTERVAL, [0, 0])[1]:
            if (
                cumulative_time_pos
                >= self.pj[cfg.OBSERVATIONS][self.observationId].get(cfg.OBSERVATION_TIME_INTERVAL, [0, 0])[1]
            ):
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
                if (
                    abs(
                        ct0
                        - (
                            ct
                            + dec(
                                self.pj[cfg.OBSERVATIONS][self.observationId][cfg.MEDIA_INFO]["offset"][
                                    str(n_player + 1)
                                ]
                            )
                        )
                    )
                    >= 1
                ):
                    self.sync_time(n_player, ct0)  # self.seek_mediaplayer(ct0, n_player)

        currentTimeOffset = dec(cumulative_time_pos + self.pj[cfg.OBSERVATIONS][self.observationId][cfg.TIME_OFFSET])

        all_media_duration = sum(self.dw_player[0].media_durations) / 1000
        mediaName = ""
        current_media_duration = self.dw_player[0].player.duration  # mediaplayer_length
        self.mediaTotalLength = current_media_duration

        # current state(s)
        # extract State events
        StateBehaviorsCodes = util.state_behavior_codes(self.pj[cfg.ETHOGRAM])
        self.currentStates = {}

        # index of current subject
        subject_idx = self.subject_name_index[self.currentSubject] if self.currentSubject else ""
        self.currentStates = util.get_current_states_modifiers_by_subject(
            StateBehaviorsCodes,
            self.pj[cfg.OBSERVATIONS][self.observationId][cfg.EVENTS],
            dict(self.pj[cfg.SUBJECTS], **{"": {"name": ""}}),
            currentTimeOffset,
            include_modifiers=True,
        )
        self.lbCurrentStates.setText(", ".join(self.currentStates[subject_idx]))

        # show current states in subjects table
        self.show_current_states_in_subjects_table()

        if self.dw_player[0].player.playlist_pos is not None:
            current_media_name = pl.Path(
                self.dw_player[0].player.playlist[self.dw_player[0].player.playlist_pos]["filename"]
            ).name
        else:
            current_media_name = ""
        playlist_length = len(self.dw_player[0].player.playlist)

        # update media info
        msg = ""

        if self.dw_player[0].player.time_pos is not None:

            # check if video
            current_media_frame = (
                (round(value * self.dw_player[0].player.container_fps) + 1)
                if self.dw_player[0].player.container_fps is not None
                else "NA"
            )
            msg = (
                f"{current_media_name}: <b>{util.convertTime(self.timeFormat, current_media_time_pos)} / "
                f"{util.convertTime(self.timeFormat, current_media_duration)}</b> frame: {current_media_frame}"
            )

            if self.dw_player[0].player.playlist_count > 1:
                msg += (
                    f"<br>Total: <b>{util.convertTime(self.timeFormat,cumulative_time_pos)} / "
                    f"{util.convertTime(self.timeFormat, all_media_duration)}</b>"
                )

            self.lb_player_status.setText("Player paused" if self.dw_player[0].player.pause else "")

            msg += f"<br>media #{self.dw_player[0].player.playlist_pos + 1} / {playlist_length}"

        else:  # player ended
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
                self.video_slider.setValue(
                    round(current_media_time_pos / current_media_duration * (cfg.SLIDER_MAXIMUM - 1))
                )

    def load_behaviors_in_twEthogram(self, behaviorsToShow):
        """
        fill ethogram table with ethogram from pj
        """

        self.twEthogram.setRowCount(0)
        if self.pj[cfg.ETHOGRAM]:
            for idx in util.sorted_keys(self.pj[cfg.ETHOGRAM]):
                if self.pj[cfg.ETHOGRAM][idx][cfg.BEHAVIOR_CODE] in behaviorsToShow:
                    self.twEthogram.setRowCount(self.twEthogram.rowCount() + 1)
                    for col in sorted(cfg.behav_fields_in_mainwindow.keys()):
                        field = cfg.behav_fields_in_mainwindow[col]
                        self.twEthogram.setItem(
                            self.twEthogram.rowCount() - 1,
                            col,
                            QTableWidgetItem(str(self.pj[cfg.ETHOGRAM][idx][field])),
                        )
        if self.twEthogram.rowCount() < len(self.pj[cfg.ETHOGRAM].keys()):
            self.dwEthogram.setWindowTitle(
                f"Ethogram (filtered {self.twEthogram.rowCount()}/{len(self.pj[cfg.ETHOGRAM].keys())})"
            )

            if self.observationId:
                self.pj[cfg.OBSERVATIONS][self.observationId]["filtered behaviors"] = behaviorsToShow
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
        for idx, s in enumerate(["", cfg.NO_FOCAL_SUBJECT, "", ""]):
            self.twSubjects.setItem(0, idx, QTableWidgetItem(s))

        if self.pj[cfg.SUBJECTS]:
            for idx in util.sorted_keys(self.pj[cfg.SUBJECTS]):

                self.subject_name_index[self.pj[cfg.SUBJECTS][idx][cfg.SUBJECT_NAME]] = idx

                if self.pj[cfg.SUBJECTS][idx][cfg.SUBJECT_NAME] in subjects_to_show:

                    self.twSubjects.setRowCount(self.twSubjects.rowCount() + 1)

                    for idx2, field in enumerate(cfg.subjectsFields):
                        self.twSubjects.setItem(
                            self.twSubjects.rowCount() - 1, idx2, QTableWidgetItem(self.pj[cfg.SUBJECTS][idx][field])
                        )

                    # add cell for current state(s) after last subject field
                    self.twSubjects.setItem(
                        self.twSubjects.rowCount() - 1, len(cfg.subjectsFields), QTableWidgetItem("")
                    )

    def update_events_start_stop(self):
        """
        update status start/stop of state events in Events table
        take consideration of subject and modifiers
        twEvents must be ordered by time asc

        does not return value
        """

        state_events_list = util.state_behavior_codes(self.pj[cfg.ETHOGRAM])
        mem_behav = {}

        for row in range(self.twEvents.rowCount()):

            subject = self.twEvents.item(row, cfg.TW_OBS_FIELD[self.playerType][cfg.SUBJECT]).text()
            code = self.twEvents.item(row, cfg.TW_OBS_FIELD[self.playerType][cfg.BEHAVIOR_CODE]).text()
            modifier = self.twEvents.item(row, cfg.TW_OBS_FIELD[self.playerType]["modifier"]).text()

            # check if code is state
            if code in state_events_list:

                if f"{subject}|{code}|{modifier}" in mem_behav and mem_behav[f"{subject}|{code}|{modifier}"]:
                    self.twEvents.item(row, cfg.TW_OBS_FIELD[self.playerType][cfg.TYPE]).setText(cfg.STOP)
                else:
                    self.twEvents.item(row, cfg.TW_OBS_FIELD[self.playerType][cfg.TYPE]).setText(cfg.START)

                if f"{subject}|{code}|{modifier}" in mem_behav:
                    mem_behav[f"{subject}|{code}|{modifier}"] = not mem_behav[f"{subject}|{code}|{modifier}"]
                else:
                    mem_behav[f"{subject}|{code}|{modifier}"] = 1

    def checkSameEvent(self, obs_id: str, time: dec, subject: str, code: str) -> bool:
        """
        check if a same event is already in events list (time, subject, code)
        """

        if self.pj[cfg.OBSERVATIONS][obs_id][cfg.TYPE] in (cfg.MEDIA, cfg.LIVE):
            return (time, subject, code) in [
                (x[cfg.EVENT_TIME_FIELD_IDX], x[cfg.EVENT_SUBJECT_FIELD_IDX], x[cfg.EVENT_BEHAVIOR_FIELD_IDX])
                for x in self.pj[cfg.OBSERVATIONS][obs_id][cfg.EVENTS]
            ]

        if self.pj[cfg.OBSERVATIONS][obs_id][cfg.TYPE] == cfg.IMAGES:
            """
            print((time, subject, code))
            print(self.pj[cfg.OBSERVATIONS][obs_id][cfg.EVENTS])
            print(
                [
                    (
                        x[cfg.PJ_OBS_FIELDS[self.pj[cfg.OBSERVATIONS][obs_id][cfg.TYPE]]["image index"]],
                        x[cfg.EVENT_SUBJECT_FIELD_IDX],
                        x[cfg.EVENT_BEHAVIOR_FIELD_IDX],
                    )
                    for x in self.pj[cfg.OBSERVATIONS][obs_id][cfg.EVENTS]
                ]
            )
            """
            return (time, subject, code) in [
                (
                    x[cfg.PJ_OBS_FIELDS[self.pj[cfg.OBSERVATIONS][obs_id][cfg.TYPE]][cfg.IMAGE_INDEX]],
                    x[cfg.EVENT_SUBJECT_FIELD_IDX],
                    x[cfg.EVENT_BEHAVIOR_FIELD_IDX],
                )
                for x in self.pj[cfg.OBSERVATIONS][obs_id][cfg.EVENTS]
            ]

    def write_event(self, event: dict, mem_time: dec) -> None:
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

        logging.debug(f"write event - event: {event}  memtime: {mem_time}")

        if event is None:
            return

        editing_event = "row" in event

        # add time offset if not from editing
        if not editing_event:

            # add offset
            if self.pj[cfg.OBSERVATIONS][self.observationId][cfg.TYPE] in (cfg.MEDIA, cfg.LIVE):
                mem_time += dec(self.pj[cfg.OBSERVATIONS][self.observationId][cfg.TIME_OFFSET]).quantize(dec(".001"))

        # remove key code from modifiers
        subject = event.get(cfg.SUBJECT, self.currentSubject)
        comment = event.get(cfg.COMMENT, "")

        if self.playerType in (cfg.IMAGES, cfg.VIEWER_IMAGES):
            image_idx = event.get(cfg.IMAGE_INDEX, "")
            image_path = event.get(cfg.IMAGE_PATH, "")

        # check if a same event is already in events list (time, subject, code)

        if self.pj[cfg.OBSERVATIONS][self.observationId][cfg.TYPE] in (cfg.MEDIA, cfg.LIVE):
            # adding event
            if (not editing_event) and self.checkSameEvent(
                self.observationId,
                mem_time,
                subject,
                event[cfg.BEHAVIOR_CODE],
            ):
                _ = dialog.MessageDialog(
                    cfg.programName, "The same event already exists (same time, behavior code and subject).", [cfg.OK]
                )
                return 1

            # modifying event and time was changed
            if editing_event and mem_time != self.pj[cfg.OBSERVATIONS][self.observationId][cfg.EVENTS][event["row"]][0]:
                if self.checkSameEvent(
                    self.observationId,
                    mem_time,
                    subject,
                    event[cfg.BEHAVIOR_CODE],
                ):
                    _ = dialog.MessageDialog(
                        cfg.programName,
                        "The same event already exists (same time, behavior code and subject).",
                        [cfg.OK],
                    )
                return 1

        if self.pj[cfg.OBSERVATIONS][self.observationId][cfg.TYPE] == cfg.IMAGES:
            # adding event
            if (not editing_event) and self.checkSameEvent(
                self.observationId,
                image_idx,
                subject,
                event[cfg.BEHAVIOR_CODE],
            ):
                _ = dialog.MessageDialog(
                    cfg.programName,
                    "The same event already exists (same image index, behavior code and subject).",
                    [cfg.OK],
                )
                return 1

            # modifying event and time was changed
            if (
                editing_event
                and image_idx
                != self.pj[cfg.OBSERVATIONS][self.observationId][cfg.EVENTS][event["row"]][
                    cfg.PJ_OBS_FIELDS[cfg.IMAGES][cfg.IMAGE_INDEX]
                ]
            ):
                if self.checkSameEvent(
                    self.observationId,
                    image_idx,
                    subject,
                    event[cfg.BEHAVIOR_CODE],
                ):
                    _ = dialog.MessageDialog(
                        cfg.programName,
                        "The same event already exists (same image index, behavior code and subject).",
                        [cfg.OK],
                    )
                    return 1

        if "from map" not in event:  # modifiers only for behaviors without coding map
            # check if event has modifiers
            modifier_str = ""

            if event["modifiers"]:

                selected_modifiers, modifiers_external_data = {}, {}
                # check if modifiers are from external data
                for idx in event["modifiers"]:

                    if event["modifiers"][idx]["type"] == cfg.EXTERNAL_DATA_MODIFIER:

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
                if [x for x in event["modifiers"] if event["modifiers"][x]["type"] != cfg.EXTERNAL_DATA_MODIFIER]:

                    # pause media
                    if self.pj[cfg.OBSERVATIONS][self.observationId][cfg.TYPE] in [cfg.MEDIA]:
                        if self.playerType == cfg.MEDIA:
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

                    modifiers_selector = select_modifiers.ModifiersList(
                        event["code"], eval(str(event["modifiers"])), currentModifiers
                    )

                    r = modifiers_selector.exec_()
                    if r:
                        selected_modifiers = modifiers_selector.get_modifiers()

                    # restart media
                    if self.pj[cfg.OBSERVATIONS][self.observationId][cfg.TYPE] in [cfg.MEDIA]:
                        if self.playerType == cfg.MEDIA:
                            if memState == "playing":
                                self.play_video()
                    if not r:  # cancel button pressed
                        return

                all_modifiers = {**selected_modifiers, **modifiers_external_data}

                modifier_str = ""
                for idx in util.sorted_keys(all_modifiers):
                    if modifier_str:
                        modifier_str += "|"
                    if all_modifiers[idx]["type"] in [cfg.SINGLE_SELECTION, cfg.MULTI_SELECTION]:
                        modifier_str += ",".join(all_modifiers[idx].get("selected", ""))
                    if all_modifiers[idx]["type"] in [cfg.NUMERIC_MODIFIER, cfg.EXTERNAL_DATA_MODIFIER]:
                        modifier_str += all_modifiers[idx].get("selected", "NA")

        else:
            modifier_str = event["from map"]

        modifier_str = re.sub(" \(.*\)", "", modifier_str)

        # update current state
        # TODO: verify event["subject"] / self.currentSubject

        # extract State events
        state_behaviors_codes = util.state_behavior_codes(self.pj[cfg.ETHOGRAM])

        # index of current subject
        # subject_idx = self.subject_name_index[self.currentSubject] if self.currentSubject else ""

        # print(f"{self.pj[cfg.OBSERVATIONS][self.observationId][cfg.EVENTS]=}")

        if self.pj[cfg.OBSERVATIONS][self.observationId][cfg.TYPE] in (cfg.LIVE, cfg.MEDIA):
            position = mem_time
        if self.pj[cfg.OBSERVATIONS][self.observationId][cfg.TYPE] == cfg.IMAGES:
            position = image_idx

        current_states = util.get_current_states_modifiers_by_subject(
            state_behaviors_codes,
            self.pj[cfg.OBSERVATIONS][self.observationId][cfg.EVENTS],
            dict(self.pj[cfg.SUBJECTS], **{"": {"name": ""}}),
            position,
            include_modifiers=False,
        )

        # logging.debug(f"self.currentSubject {self.currentSubject}")
        # logging.debug(f"current_states {current_states}")

        # fill the undo list
        event_operations.fill_events_undo_list(
            self, "Undo last event edition" if editing_event else "Undo last event insertion"
        )

        logging.debug(f"save list of events for undo operation")

        if not editing_event:
            if self.currentSubject:
                csj = []
                for idx in current_states:
                    if (
                        idx in self.pj[cfg.SUBJECTS]
                        and self.pj[cfg.SUBJECTS][idx][cfg.SUBJECT_NAME] == self.currentSubject
                    ):
                        csj = current_states[idx]
                        break

            else:  # no focal subject
                try:
                    csj = current_states[""]
                except Exception:
                    csj = []

            logging.debug(f"csj {csj}")

            if self.pj[cfg.OBSERVATIONS][self.observationId][cfg.TYPE] in (cfg.LIVE, cfg.MEDIA):
                check_index = cfg.EVENT_TIME_FIELD_IDX
            if self.pj[cfg.OBSERVATIONS][self.observationId][cfg.TYPE] == cfg.IMAGES:
                check_index = cfg.PJ_OBS_FIELDS[cfg.IMAGES]["image index"]

            cm = {}  # modifiers for current behaviors
            for cs in csj:
                for ev in self.pj[cfg.OBSERVATIONS][self.observationId][cfg.EVENTS]:

                    if ev[check_index] > position:
                        break

                    if ev[cfg.EVENT_SUBJECT_FIELD_IDX] == self.currentSubject:
                        if ev[cfg.EVENT_BEHAVIOR_FIELD_IDX] == cs:
                            cm[cs] = ev[cfg.EVENT_MODIFIER_FIELD_IDX]

            for cs in csj:
                # close state if same state without modifier
                if (
                    self.close_the_same_current_event
                    and (event[cfg.BEHAVIOR_CODE] == cs)
                    and modifier_str.replace("None", "").replace("|", "") == ""
                ):
                    modifier_str = cm[cs]
                    continue

                if (event["excluded"] and cs in event["excluded"].split(",")) or (
                    event[cfg.BEHAVIOR_CODE] == cs and cm[cs] != modifier_str
                ):
                    # add excluded state event to observations (= STOP them)
                    self.pj[cfg.OBSERVATIONS][self.observationId][cfg.EVENTS].append(
                        [mem_time - dec("0.001"), self.currentSubject, cs, cm[cs], ""]
                    )

        # add event to pj
        if editing_event:  # modifying event

            if self.pj[cfg.OBSERVATIONS][self.observationId][cfg.TYPE] in (cfg.MEDIA, cfg.LIVE):
                self.pj[cfg.OBSERVATIONS][self.observationId][cfg.EVENTS][event["row"]] = [
                    mem_time,
                    subject,
                    event[cfg.BEHAVIOR_CODE],
                    modifier_str,
                    comment,
                ]
                # order by image index ASC
                self.pj[cfg.OBSERVATIONS][self.observationId][cfg.EVENTS].sort()

            elif self.pj[cfg.OBSERVATIONS][self.observationId][cfg.TYPE] == cfg.IMAGES:
                self.pj[cfg.OBSERVATIONS][self.observationId][cfg.EVENTS][event["row"]] = [
                    mem_time,
                    subject,
                    event[cfg.BEHAVIOR_CODE],
                    modifier_str,
                    comment,
                    image_idx,
                    image_path,
                ]
                # order by image index ASC
                self.pj[cfg.OBSERVATIONS][self.observationId][cfg.EVENTS].sort(
                    key=lambda x: x[cfg.PJ_OBS_FIELDS[self.playerType][cfg.IMAGE_INDEX]]
                )

        else:  # add event
            if self.pj[cfg.OBSERVATIONS][self.observationId][cfg.TYPE] in (cfg.MEDIA, cfg.LIVE):
                """
                # removed to use bisect
                self.pj[cfg.OBSERVATIONS][self.observationId][cfg.EVENTS].append(
                    [mem_time, subject, event[cfg.BEHAVIOR_CODE], modifier_str, comment]
                )
                """
                bisect.insort(
                    self.pj[cfg.OBSERVATIONS][self.observationId][cfg.EVENTS],
                    [mem_time, subject, event[cfg.BEHAVIOR_CODE], modifier_str, comment],
                )

            elif self.pj[cfg.OBSERVATIONS][self.observationId][cfg.TYPE] == cfg.IMAGES:
                self.pj[cfg.OBSERVATIONS][self.observationId][cfg.EVENTS].append(
                    [mem_time, subject, event[cfg.BEHAVIOR_CODE], modifier_str, comment, image_idx, image_path]
                )
                # order by image index ASC
                self.pj[cfg.OBSERVATIONS][self.observationId][cfg.EVENTS].sort(
                    key=lambda x: x[cfg.PJ_OBS_FIELDS[self.playerType][cfg.IMAGE_INDEX]]
                )

        """
        # removed to use bisect
        # sort events in pj
        if self.playerType in (cfg.MEDIA, cfg.LIVE):
            removed to use bisect
            self.pj[cfg.OBSERVATIONS][self.observationId][cfg.EVENTS].sort()
        """

        # reload all events in tw
        self.load_tw_events(self.observationId)

        if self.playerType in (cfg.MEDIA, cfg.LIVE):
            position_in_events = [
                i for i, t in enumerate(self.pj[cfg.OBSERVATIONS][self.observationId][cfg.EVENTS]) if t[0] == mem_time
            ][0]

            if position_in_events == len(self.pj[cfg.OBSERVATIONS][self.observationId][cfg.EVENTS]) - 1:
                self.twEvents.scrollToBottom()
            else:
                self.twEvents.scrollToItem(self.twEvents.item(position_in_events, 0), QAbstractItemView.EnsureVisible)

        self.projectChanged = True

        return 0

    def fill_lwDetailed(self, obs_key, memLaps):
        """
        fill listwidget with all events coded by key
        return index of behaviour
        """

        # check if key duplicated
        items = []
        for idx in self.pj[cfg.ETHOGRAM]:
            if self.pj[cfg.ETHOGRAM][idx]["key"] == obs_key:

                code_descr = self.pj[cfg.ETHOGRAM][idx][cfg.BEHAVIOR_CODE]
                if self.pj[cfg.ETHOGRAM][idx][cfg.DESCRIPTION]:
                    code_descr += " - " + self.pj[cfg.ETHOGRAM][idx][cfg.DESCRIPTION]
                items.append(code_descr)
                self.detailedObs[code_descr] = idx

        items.sort()

        dbc = dialog.DuplicateBehaviorCode(
            f"The <b>{obs_key}</b> key codes more behaviors.<br>Choose the correct one:", items
        )
        if dbc.exec_():
            code = dbc.getCode()
            if code:
                return self.detailedObs[code]
            else:
                return None

    def getLaps(self, n_player: int = 0) -> dec:
        """
        Cumulative laps time from begining of observation
        do not add time offset

        Args:
            n_player (int): player
        Returns:
            decimal: cumulative time in seconds

        """

        if not self.observationId:
            return dec("0")

        if self.pj[cfg.OBSERVATIONS][self.observationId][cfg.TYPE] == cfg.LIVE:

            if self.liveObservationStarted:
                now = QTime()
                now.start()  # current time
                memLaps = dec(str(round(self.liveStartTime.msecsTo(now) / 1000, 3)))
                return memLaps
            else:
                return dec(0)

        if self.pj[cfg.OBSERVATIONS][self.observationId][cfg.TYPE] == cfg.IMAGES:

            if self.playerType in [cfg.VIEWER_IMAGES]:
                return dec("NaN")

            if self.playerType == cfg.IMAGES:
                time_ = dec("NaN")
                if (
                    self.pj[cfg.OBSERVATIONS][self.observationId].get(cfg.USE_EXIF_DATE, False)
                    and self.extract_exif_DateTimeOriginal(self.images_list[self.image_idx]) != -1
                ):
                    time_ = self.extract_exif_DateTimeOriginal(self.images_list[self.image_idx]) - self.image_time_ref

                elif self.pj[cfg.OBSERVATIONS][self.observationId].get(cfg.TIME_LAPSE, 0):
                    time_ = (self.image_idx + 1) * self.pj[cfg.OBSERVATIONS][self.observationId].get(cfg.TIME_LAPSE, 0)

                return dec(time_).quantize(dec("0.001"), rounding=ROUND_DOWN)

        if self.pj[cfg.OBSERVATIONS][self.observationId][cfg.TYPE] == cfg.MEDIA:

            if self.playerType in [cfg.VIEWER_LIVE, cfg.VIEWER_MEDIA]:
                return dec(0)

            if self.playerType == cfg.MEDIA:
                # cumulative time
                mem_laps = sum(
                    self.dw_player[n_player].media_durations[0 : self.dw_player[n_player].player.playlist_pos]
                ) + (
                    0
                    if self.dw_player[n_player].player.time_pos is None
                    else self.dw_player[n_player].player.time_pos * 1000
                )

                return dec(str(round(mem_laps / 1000, 3)))

    def full_event(self, behavior_idx: str) -> dict:
        """
        get event as dict
        ask modifiers from coding map if configured and add them under 'from map' key

        Args:
            behavior_idx (str): behavior index in ethogram
        Returns:
            dict: event

        """

        event = dict(self.pj[cfg.ETHOGRAM][behavior_idx])
        # check if coding map
        if "coding map" in self.pj[cfg.ETHOGRAM][behavior_idx] and self.pj[cfg.ETHOGRAM][behavior_idx]["coding map"]:

            # pause if media and media playing
            if self.pj[cfg.OBSERVATIONS][self.observationId][cfg.TYPE] in [cfg.MEDIA]:
                if self.playerType == cfg.MEDIA:

                    if self.is_playing():
                        flag_player_playing = True
                        self.pause_video()

            self.codingMapWindow = modifiers_coding_map.ModifiersCodingMapWindowClass(
                self.pj[cfg.CODING_MAP][self.pj[cfg.ETHOGRAM][behavior_idx]["coding map"]]
            )

            self.codingMapWindow.resize(cfg.CODING_MAP_RESIZE_W, cfg.CODING_MAP_RESIZE_H)
            if self.coding_map_window_geometry:
                self.codingMapWindow.restoreGeometry(self.coding_map_window_geometry)

            if self.codingMapWindow.exec_():
                event["from map"] = self.codingMapWindow.getCodes()
            else:
                event["from map"] = ""

            self.coding_map_window_geometry = self.codingMapWindow.saveGeometry()

            # restart media
            if self.pj[cfg.OBSERVATIONS][self.observationId][cfg.TYPE] in [cfg.MEDIA]:
                if self.playerType == cfg.MEDIA:
                    if flag_player_playing:
                        self.play_video()

        return event

    def beep(self, sound_type: str) -> None:
        """
        emit beep on various platform

        Args:
            sound_type (str): type of sound
        """

        QSound.play(f":/{sound_type}")

    def is_playing(self) -> bool:
        """
        check if first media player is playing for cfg.MEDIA

        Returns:
            bool: True if playing else False
        """

        if self.playerType == cfg.MEDIA:

            if self.dw_player[0].player.pause:
                return False
            elif self.dw_player[0].player.time_pos is not None:
                return True
            else:
                return False

        else:
            return False

    def keyPressEvent(self, event) -> None:
        """
        http://qt-project.org/doc/qt-5.0/qtcore/qt.html#Key-enum
        https://github.com/pyqt/python-qt5/blob/master/PyQt5/qml/builtins.qmltypes

        ESC: 16777216
        """

        # get modifiers
        modifiers = QApplication.keyboardModifiers()
        modifier = ""

        if modifiers & Qt.ShiftModifier:
            modifier += "Shift"

        if modifiers & Qt.ControlModifier:
            modifier += "Ctrl"

        if modifiers & (Qt.AltModifier):
            modifier += "Alt"

        if modifiers & (Qt.MetaModifier):
            modifier += "Meta"

        logging.debug(f"text #{event.text()}#  event key: {event.key()} Modifier: {modifier}")

        if self.playerType in cfg.VIEWERS:
            if event.key() in [Qt.Key_Shift, Qt.Key_Control, Qt.Key_Alt, Qt.Key_CapsLock, Qt.Key_AltGr]:
                return
            QMessageBox.critical(
                self,
                cfg.programName,
                ("The current observation is opened in VIEW mode.\n" "It is not allowed to log events in this mode."),
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

        # speed down
        if ek == Qt.Key_End:
            if self.pj[cfg.OBSERVATIONS][self.observationId][cfg.TYPE] in [cfg.MEDIA]:
                video_operations.video_slower_activated(self)
            return

        # speed up
        if ek == Qt.Key_Home:
            if self.pj[cfg.OBSERVATIONS][self.observationId][cfg.TYPE] in [cfg.MEDIA]:
                video_operations.video_faster_activated(self)
            return

        # speed normal
        if ek == Qt.Key_Backspace:
            if self.pj[cfg.OBSERVATIONS][self.observationId][cfg.TYPE] in [cfg.MEDIA]:
                video_operations.video_normalspeed_activated(self)
            return

        # play / pause with space bar
        if ek == Qt.Key_Space:
            if self.pj[cfg.OBSERVATIONS][self.observationId][cfg.TYPE] in [cfg.MEDIA]:
                if flagPlayerPlaying:
                    self.pause_video()
                else:
                    self.play_video()
            return

        # frame-by-frame mode
        if ek == 47 or ek == Qt.Key_Left:  # / one frame back
            self.previous_frame()
            return

        if ek == 42 or ek == Qt.Key_Right:  # *  read next frame
            self.next_frame()
            return

        if self.playerType == cfg.MEDIA:
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

        if not self.pj[cfg.ETHOGRAM]:
            QMessageBox.warning(self, cfg.programName, "The ethogram is not configured")
            return

        obs_key = None

        # check if key is function key
        if ek in cfg.function_keys:
            if cfg.function_keys[ek] in [self.pj[cfg.ETHOGRAM][x]["key"] for x in self.pj[cfg.ETHOGRAM]]:
                obs_key = cfg.function_keys[ek]

        # get time
        memLaps = None
        if self.pj[cfg.OBSERVATIONS][self.observationId][cfg.TYPE] == cfg.LIVE:
            if self.pj[cfg.OBSERVATIONS][self.observationId].get(cfg.SCAN_SAMPLING_TIME, 0):
                if self.timeFormat == cfg.HHMMSS:
                    memLaps = dec(int(util.time2seconds(self.lb_current_media_time.text())))
                if self.timeFormat == cfg.S:
                    memLaps = dec(int(dec(self.lb_current_media_time.text())))
            else:  # no scan sampling
                if self.pj[cfg.OBSERVATIONS][self.observationId].get(cfg.START_FROM_CURRENT_TIME, False):
                    memLaps = dec(str(util.seconds_of_day(datetime.datetime.now())))
                elif self.pj[cfg.OBSERVATIONS][self.observationId].get(cfg.START_FROM_CURRENT_EPOCH_TIME, False):
                    memLaps = dec(time.time())
                else:
                    memLaps = self.getLaps()

        if self.pj[cfg.OBSERVATIONS][self.observationId][cfg.TYPE] in (cfg.MEDIA, cfg.IMAGES):
            memLaps = self.getLaps()

        if memLaps is None:
            return

        # undo
        if ek == 90 and modifier == cfg.CTRL_KEY:

            event_operations.undo_event_operation(self)

            """
            position_in_events = [
                i for i, t in enumerate(self.pj[cfg.OBSERVATIONS][self.observationId][cfg.EVENTS]) if t[0] >= memLaps
            ][-1]

            if position_in_events == len(self.pj[cfg.OBSERVATIONS][self.observationId][cfg.EVENTS]) - 1:
                self.twEvents.scrollToBottom()
            else:
                self.twEvents.scrollToItem(self.twEvents.item(position_in_events, 0), QAbstractItemView.EnsureVisible)
            """

            return

        if (
            ((ek in range(33, 256)) and (ek not in [Qt.Key_Plus, Qt.Key_Minus]))
            or (ek in cfg.function_keys)
            or (ek == Qt.Key_Enter and event.text())
        ):  # click from coding pad or subjects pad

            ethogram_idx, subj_idx, count = -1, -1, 0

            if ek in cfg.function_keys:
                ek_unichr = cfg.function_keys[ek]
            elif ek != Qt.Key_Enter:
                ek_unichr = ek_text
            elif ek == Qt.Key_Enter and event.text():  # click from coding pad or subjects pad
                ek_unichr = ek_text

            logging.debug(f"ek_unichr {ek_unichr}")

            if ek == Qt.Key_Enter and event.text():  # click from coding pad or subjects pad
                ek_unichr = ""

                if "#subject#" in event.text():
                    for idx in self.pj[cfg.SUBJECTS]:
                        if self.pj[cfg.SUBJECTS][idx][cfg.SUBJECT_NAME] == event.text().replace("#subject#", ""):
                            subj_idx = idx
                            self.update_subject(self.pj[cfg.SUBJECTS][subj_idx][cfg.SUBJECT_NAME])
                            return

                else:  # behavior
                    for idx in self.pj[cfg.ETHOGRAM]:
                        if self.pj[cfg.ETHOGRAM][idx][cfg.BEHAVIOR_CODE] == event.text():
                            ethogram_idx = idx
                            count += 1
            else:
                # count key occurence in ethogram
                for idx in self.pj[cfg.ETHOGRAM]:
                    if self.pj[cfg.ETHOGRAM][idx]["key"] == ek_unichr:
                        ethogram_idx = idx
                        count += 1

            # check if key defines a suject
            if subj_idx == -1:  # subject not selected with subjects pad
                flag_subject = False
                for idx in self.pj[cfg.SUBJECTS]:
                    if ek_unichr == self.pj[cfg.SUBJECTS][idx]["key"]:
                        subj_idx = idx

            # select between code and subject
            if subj_idx != -1 and count:
                if self.playerType == cfg.MEDIA:
                    if self.is_playing():
                        flagPlayerPlaying = True
                        self.pause_video()

                r = dialog.MessageDialog(
                    cfg.programName, "This key defines a behavior and a subject. Choose one", ["&Behavior", "&Subject"]
                )
                if r == "&Subject":
                    count = 0
                if r == "&Behavior":
                    subj_idx = -1

            # check if key codes more events
            if subj_idx == -1 and count > 1:
                if self.pj[cfg.OBSERVATIONS][self.observationId][cfg.TYPE] in [cfg.MEDIA]:
                    if self.playerType == cfg.MEDIA:
                        if self.is_playing():
                            flagPlayerPlaying = True
                            self.pause_video()

                # let user choose event
                ethogram_idx = self.fill_lwDetailed(ek_unichr, memLaps)

                if ethogram_idx:
                    count = 1

            if self.playerType == cfg.MEDIA and flagPlayerPlaying:
                self.play_video()

            if count == 1:
                # check if focal subject is defined
                if not self.currentSubject and self.alertNoFocalSubject:
                    if self.pj[cfg.OBSERVATIONS][self.observationId][cfg.TYPE] in [cfg.MEDIA]:
                        if self.playerType == cfg.MEDIA:
                            if self.is_playing():
                                flagPlayerPlaying = True
                                self.pause_video()

                    response = dialog.MessageDialog(
                        cfg.programName,
                        (
                            "The focal subject is not defined. Do you want to continue?\n"
                            "Use Preferences menu option to modify this behaviour."
                        ),
                        [cfg.YES, cfg.NO],
                    )

                    if self.pj[cfg.OBSERVATIONS][self.observationId][cfg.TYPE] in [cfg.MEDIA] and flagPlayerPlaying:
                        self.play_video()

                    if response == cfg.NO:
                        return

                event = self.full_event(ethogram_idx)

                if self.playerType == cfg.IMAGES:
                    event[cfg.IMAGE_PATH] = self.images_list[self.image_idx]
                    event[cfg.IMAGE_INDEX] = self.image_idx + 1

                self.write_event(event, memLaps)

            elif count == 0:

                if subj_idx != -1:
                    # check if key defines a suject
                    flag_subject = False
                    for idx in self.pj[cfg.SUBJECTS]:
                        if ek_unichr == self.pj[cfg.SUBJECTS][idx]["key"]:
                            flag_subject = True
                            # select or deselect current subject
                            self.update_subject(self.pj[cfg.SUBJECTS][idx][cfg.SUBJECT_NAME])

                if not flag_subject:
                    logging.debug(f"Key not assigned ({ek_unichr})")
                    self.statusbar.showMessage(f"Key not assigned ({ek_unichr})", 5000)

    def twEvents_doubleClicked(self):
        """
        seek media to double clicked position (add self.repositioningTimeOffset value)
        substract time offset if defined
        """

        if not self.twEvents.selectedIndexes():
            return

        row = self.twEvents.selectedIndexes()[0].row()  # first row selected

        if self.playerType == cfg.MEDIA:
            time_str = self.twEvents.item(row, cfg.TW_OBS_FIELD[self.playerType]["time"]).text()
            time_ = util.time2seconds(time_str) if ":" in time_str else dec(time_str)

            # substract time offset
            time_ -= self.pj[cfg.OBSERVATIONS][self.observationId][cfg.TIME_OFFSET]

            if time_ + self.repositioningTimeOffset >= 0:
                new_time = time_ + self.repositioningTimeOffset
            else:
                new_time = 0

            self.seek_mediaplayer(new_time)
            self.update_visualizations()

        if self.playerType == cfg.IMAGES:
            index_str = self.twEvents.item(row, cfg.TW_OBS_FIELD[self.playerType][cfg.IMAGE_INDEX]).text()
            self.image_idx = int(index_str) - 1
            self.extract_frame(self.dw_player[0])

    def twSubjects_doubleClicked(self):
        """
        select subject by double-click on the subjects table
        """

        if self.observationId:
            if self.twSubjects.selectedIndexes():
                self.update_subject(self.twSubjects.item(self.twSubjects.selectedIndexes()[0].row(), 1).text())
        else:
            self.no_observation()

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
            fields_list.append(cfg.EVENT_SUBJECT_FIELD_IDX)
        if self.find_dialog.cbBehavior.isChecked():
            fields_list.append(cfg.EVENT_BEHAVIOR_FIELD_IDX)
        if self.find_dialog.cbModifier.isChecked():
            # fields_list.append(cfg.EVENT_MODIFIER_FIELD_IDX )
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
        """for event_idx, event in enumerate(self.pj[cfg.OBSERVATIONS][self.observationId][cfg.EVENTS]):"""
        for event_idx in range(self.twEvents.rowCount()):
            if event_idx <= self.find_dialog.currentIdx:
                continue

            # find only in filtered events
            """
            if self.filtered_subjects:
                if self.pj[cfg.OBSERVATIONS][self.observationId][cfg.EVENTS][event_idx][EVENT_SUBJECT_FIELD_IDX] not in self.filtered_subjects:
                    continue
            if self.filtered_behaviors:
                if self.pj[cfg.OBSERVATIONS][self.observationId][cfg.EVENTS][event_idx][EVENT_BEHAVIOR_FIELD_IDX] not in self.filtered_behaviors:
                    continue
            """

            if (not self.find_dialog.cbFindInSelectedEvents.isChecked()) or (
                self.find_dialog.cbFindInSelectedEvents.isChecked() and event_idx in self.find_dialog.rowsToFind
            ):

                for idx in fields_list:
                    """
                    if (self.find_dialog.cb_case_sensitive.isChecked() and self.find_dialog.findText.text() in event[idx]) \
                       or (not self.find_dialog.cb_case_sensitive.isChecked() and
                           self.find_dialog.findText.text().upper() in event[idx].upper()):
                    """
                    if (
                        self.find_dialog.cb_case_sensitive.isChecked()
                        and self.find_dialog.findText.text() in self.twEvents.item(event_idx, idx).text()
                    ) or (
                        not self.find_dialog.cb_case_sensitive.isChecked()
                        and self.find_dialog.findText.text().upper()
                        in self.twEvents.item(event_idx, idx).text().upper()
                    ):

                        self.find_dialog.currentIdx = event_idx
                        self.twEvents.scrollToItem(self.twEvents.item(event_idx, 0))
                        self.twEvents.selectRow(event_idx)
                        return

        if msg != "FIND_FROM_BEGINING":
            if (
                dialog.MessageDialog(
                    cfg.programName,
                    f"<b>{self.find_dialog.findText.text()}</b> not found. Search from beginning?",
                    [cfg.YES, cfg.NO],
                )
                == cfg.YES
            ):
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
            nb_fields = (
                (explore_dialog.find_subject.text() != "")
                + (explore_dialog.find_behavior.text() != "")
                + (explore_dialog.find_modifier.text() != "")
                + (explore_dialog.find_comment.text() != "")
            )

            for obs_id in sorted(self.pj[cfg.OBSERVATIONS]):
                for event_idx, event in enumerate(self.pj[cfg.OBSERVATIONS][obs_id][cfg.EVENTS]):
                    nb_results = 0
                    for text, idx in [
                        (explore_dialog.find_subject.text(), cfg.EVENT_SUBJECT_FIELD_IDX),
                        (explore_dialog.find_behavior.text(), cfg.EVENT_BEHAVIOR_FIELD_IDX),
                        (explore_dialog.find_modifier.text(), cfg.EVENT_MODIFIER_FIELD_IDX),
                        (explore_dialog.find_comment.text(), cfg.EVENT_COMMENT_FIELD_IDX),
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
                QMessageBox.information(self, cfg.programName, "No events found")

    def double_click_explore_project(self, obs_id, event_idx):
        """
        manage double-click on tablewidget of explore project results
        """
        observation_operations.load_observation(self, obs_id, cfg.VIEW)
        self.twEvents.scrollToItem(self.twEvents.item(event_idx - 1, 0))
        self.twEvents.selectRow(event_idx - 1)

    def click_signal_find_replace_in_events(self, msg):
        """
        find/replace in events when "Find" button of find dialog box is pressed
        """

        if msg == "CANCEL":
            self.find_replace_dialog.close()
            return
        if not self.find_replace_dialog.findText.text():
            dialog.MessageDialog(cfg.programName, "There is nothing to find.", ["OK"])
            return

        if self.find_replace_dialog.cbFindInSelectedEvents.isChecked() and not len(self.find_replace_dialog.rowsToFind):
            dialog.MessageDialog(cfg.programName, "There are no selected events", [cfg.OK])
            return

        fields_list = []
        if self.find_replace_dialog.cbSubject.isChecked():
            fields_list.append(cfg.EVENT_SUBJECT_FIELD_IDX)
        if self.find_replace_dialog.cbBehavior.isChecked():
            fields_list.append(cfg.EVENT_BEHAVIOR_FIELD_IDX)
        if self.find_replace_dialog.cbModifier.isChecked():
            fields_list.append(cfg.EVENT_MODIFIER_FIELD_IDX)
        if self.find_replace_dialog.cbComment.isChecked():
            fields_list.append(cfg.EVENT_COMMENT_FIELD_IDX)

        number_replacement = 0
        insensitive_re = re.compile(re.escape(self.find_replace_dialog.findText.text()), re.IGNORECASE)
        for event_idx, event in enumerate(self.pj[cfg.OBSERVATIONS][self.observationId][cfg.EVENTS]):

            # apply modif only to filtered subjects
            if self.filtered_subjects:
                if (
                    self.pj[cfg.OBSERVATIONS][self.observationId][cfg.EVENTS][event_idx][cfg.EVENT_SUBJECT_FIELD_IDX]
                    not in self.filtered_subjects
                ):
                    continue
            # apply modif only to filtered behaviors
            if self.filtered_behaviors:
                if (
                    self.pj[cfg.OBSERVATIONS][self.observationId][cfg.EVENTS][event_idx][cfg.EVENT_BEHAVIOR_FIELD_IDX]
                    not in self.filtered_behaviors
                ):
                    continue

            if event_idx < self.find_replace_dialog.currentIdx:
                continue

            if (not self.find_replace_dialog.cbFindInSelectedEvents.isChecked()) or (
                self.find_replace_dialog.cbFindInSelectedEvents.isChecked()
                and event_idx in self.find_replace_dialog.rowsToFind
            ):
                for idx1 in fields_list:
                    if idx1 <= self.find_replace_dialog.currentIdx_idx:
                        continue

                    if (
                        self.find_replace_dialog.cb_case_sensitive.isChecked()
                        and self.find_replace_dialog.findText.text() in event[idx1]
                    ) or (
                        not self.find_replace_dialog.cb_case_sensitive.isChecked()
                        and self.find_replace_dialog.findText.text().upper() in event[idx1].upper()
                    ):

                        number_replacement += 1
                        self.find_replace_dialog.currentIdx = event_idx
                        self.find_replace_dialog.currentIdx_idx = idx1
                        if self.find_replace_dialog.cb_case_sensitive.isChecked():
                            event[idx1] = event[idx1].replace(
                                self.find_replace_dialog.findText.text(), self.find_replace_dialog.replaceText.text()
                            )
                        if not self.find_replace_dialog.cb_case_sensitive.isChecked():
                            event[idx1] = insensitive_re.sub(self.find_replace_dialog.replaceText.text(), event[idx1])

                        self.pj[cfg.OBSERVATIONS][self.observationId][cfg.EVENTS][event_idx] = event
                        self.load_tw_events(self.observationId)
                        self.twEvents.scrollToItem(self.twEvents.item(event_idx, 0))
                        self.twEvents.selectRow(event_idx)
                        self.projectChanged = True

                        if msg == "FIND_REPLACE":
                            return

                self.find_replace_dialog.currentIdx_idx = -1

        if msg == "FIND_REPLACE":
            if (
                dialog.MessageDialog(
                    cfg.programName,
                    f"{self.find_replace_dialog.findText.text()} not found.\nRestart find/replace from the beginning?",
                    [cfg.YES, cfg.NO],
                )
                == cfg.YES
            ):
                self.find_replace_dialog.currentIdx = -1
            else:
                self.find_replace_dialog.close()
        if msg == "FIND_REPLACE_ALL":
            dialog.MessageDialog(cfg.programName, f"{number_replacement} substitution(s).", [cfg.OK])
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
            if (
                dialog.MessageDialog(
                    cfg.programName, "BORIS is doing some job. What do you want to do?", ["Wait", "Quit BORIS"]
                )
                == "Wait"
            ):
                event.ignore()
                return
            for ps in self.processes:
                ps[0].terminate()
                # Wait for Xms and then elevate the situation to terminate
                if not ps[0].waitForFinished(5000):
                    ps[0].kill()

        if self.observationId:
            observation_operations.close_observation(self)

        if self.projectChanged:
            response = dialog.MessageDialog(
                cfg.programName, "What to do about the current unsaved project?", [cfg.SAVE, cfg.DISCARD, cfg.CANCEL]
            )

            if response == cfg.SAVE:
                if self.save_project_activated() == "not saved":
                    event.ignore()

            if response == cfg.CANCEL:
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

        if self.geometric_measurements_mode:
            return

        if self.playerType == cfg.MEDIA:

            # check if player 1 is ended
            for i, dw in enumerate(self.dw_player):
                if (
                    str(i + 1) in self.pj[cfg.OBSERVATIONS][self.observationId][cfg.FILE]
                    and self.pj[cfg.OBSERVATIONS][self.observationId][cfg.FILE][str(i + 1)]
                ):
                    dw.player.pause = False

            self.lb_player_status.clear()

            # if self.pj[cfg.OBSERVATIONS][self.observationId].get(cfg.VISUALIZE_WAVEFORM, False) \
            #    or self.pj[cfg.OBSERVATIONS][self.observationId].get(VISUALIZE_SPECTROGRAM, False):

            self.plot_timer.start()

            # start all timer for plotting data
            for data_timer in self.ext_data_timer_list:
                data_timer.start()

            self.actionPlay.setIcon(QIcon(":/pause"))
            self.actionPlay.setText("Pause")

            return True

    def pause_video(self):
        """
        pause media
        does not pause media if already paused (to prevent media played again)
        """

        if self.playerType == cfg.MEDIA:

            for i, player in enumerate(self.dw_player):
                if (
                    str(i + 1) in self.pj[cfg.OBSERVATIONS][self.observationId][cfg.FILE]
                    and self.pj[cfg.OBSERVATIONS][self.observationId][cfg.FILE][str(i + 1)]
                ):

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

        if self.observationId and self.pj[cfg.OBSERVATIONS][self.observationId][cfg.TYPE] in [cfg.MEDIA]:
            if not self.is_playing():
                self.play_video()
            else:
                self.pause_video()

    def jumpBackward_activated(self):
        """
        rewind from current position
        """
        if self.playerType == cfg.MEDIA:

            decrement = (
                self.fast * self.play_rate
                if self.config_param.get(cfg.ADAPT_FAST_JUMP, cfg.ADAPT_FAST_JUMP_DEFAULT)
                else self.fast
            )

            new_time = (
                sum(self.dw_player[0].media_durations[0 : self.dw_player[0].player.playlist_pos]) / 1000
                + self.dw_player[0].player.playback_time
                - decrement
            )

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

        if self.playerType == cfg.MEDIA:

            increment = (
                self.fast * self.play_rate
                if self.config_param.get(cfg.ADAPT_FAST_JUMP, cfg.ADAPT_FAST_JUMP_DEFAULT)
                else self.fast
            )

            new_time = (
                sum(self.dw_player[0].media_durations[0 : self.dw_player[0].player.playlist_pos]) / 1000
                + self.dw_player[0].player.playback_time
                + increment
            )

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

        if self.playerType == cfg.MEDIA:

            self.pause_video()

            if cfg.OBSERVATION_TIME_INTERVAL in self.pj[cfg.OBSERVATIONS][self.observationId]:
                self.seek_mediaplayer(
                    int(self.pj[cfg.OBSERVATIONS][self.observationId][cfg.OBSERVATION_TIME_INTERVAL][0])
                )
            else:
                self.seek_mediaplayer(0)

            self.update_visualizations()

        if self.playerType == cfg.IMAGES:
            self.image_idx = 0
            self.extract_frame(self.dw_player[0])

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
    ret, msg = util.check_ffmpeg_path()
    if not ret:
        QMessageBox.critical(
            None,
            cfg.programName,
            "FFmpeg is not available.<br>Go to http://www.ffmpeg.org to download it",
            QMessageBox.Ok | QMessageBox.Default,
            QMessageBox.NoButton,
        )
        sys.exit(3)
    else:
        ffmpeg_bin = msg

    app.setApplicationName(cfg.programName)
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
            QMessageBox.critical(window, cfg.programName, pj["error"])
        else:
            if msg:
                QMessageBox.information(window, cfg.programName, msg)
            window.load_project(project_path, project_changed, pj)

    if observation_to_open and "error" not in pj:
        r = observation_operations.load_observation(window, observation_to_open)
        if r:
            QMessageBox.warning(
                None,
                cfg.programName,
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
