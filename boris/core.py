"""
BORIS
Behavioral Observation Research Interactive Software
Copyright 2012-2024 Olivier Friard

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

import os
import sys

os.environ["PATH"] = os.path.dirname(__file__) + os.sep + "misc" + os.pathsep + os.environ["PATH"]

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), ".")))
import qdarkstyle

import datetime

import json
import logging
import pathlib as pl
import platform
import re
import PIL.Image
import PIL.ImageEnhance
import subprocess

import locale
import tempfile
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Union, Tuple

from decimal import Decimal as dec
from decimal import ROUND_DOWN
import gzip
from collections import deque

import matplotlib
import zipfile
import shutil

matplotlib.use("Qt5Agg")

from PyQt5.QtCore import (
    Qt,
    QPoint,
    pyqtSignal,
    QEvent,
    QDateTime,
    QTime,
    QUrl,
    QAbstractTableModel,
    QT_VERSION_STR,
    PYQT_VERSION_STR,
)
from PyQt5.QtGui import QIcon, QPixmap, QFont, QKeyEvent, QDesktopServices, QColor, QPainter, QPolygon
from PyQt5.QtMultimedia import QSound
from PyQt5.QtWidgets import (
    QLabel,
    QMessageBox,
    QMainWindow,
    QListWidgetItem,
    QFileDialog,
    QInputDialog,
    QTableWidgetItem,
    QFrame,
    QDockWidget,
    QApplication,
    QAction,
    QAbstractItemView,
    QSplashScreen,
    QHeaderView,
)
from PIL.ImageQt import Image

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

from . import project
from . import utilities as util

from . import menu_options as menu_options
from . import connections as connections
from . import config_file
from . import select_subj_behav
from . import observation_operations
from . import write_event


# matplotlib.pyplot.switch_backend("Qt5Agg")

__version__ = version.__version__
__version_date__ = version.__version_date__

# check minimal version of python
if util.versiontuple(platform.python_version()) < util.versiontuple("3.8"):
    msg = f"BORIS requires Python 3.8+! You are using Python v. {platform.python_version()}\n"
    logging.critical(msg)
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


logging.debug("BORIS started")
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


class TableModel(QAbstractTableModel):
    """
    class for populating table view with events
    """

    def __init__(self, data, header: list, time_format: str, observation_type: str, parent=None):
        super(TableModel, self).__init__(parent)
        self._data = data
        self.header = header
        self.time_format = time_format
        self.observation_type = observation_type

    def headerData(self, section: int, orientation: Qt.Orientation, role: int):
        if role == Qt.DisplayRole:
            if orientation == Qt.Horizontal:
                return self.header[section]
            else:
                return str(section + 1)

    def rowCount(self, parent=None):
        return len(self._data)

    def columnCount(self, parent=None):
        return len(self._data[0]) if self.rowCount() else 0

    def data(self, index, role=Qt.DisplayRole):
        if role == Qt.DisplayRole:
            row = index.row()
            if 0 <= row < self.rowCount():
                column = index.column()

                # print(self._data[:3])
                if cfg.TW_EVENTS_FIELDS[self.observation_type][column] == "type":
                    return self._data[row][-1]
                else:
                    event_idx = cfg.PJ_OBS_FIELDS[self.observation_type][cfg.TW_EVENTS_FIELDS[self.observation_type][column]]
                    if column == 0:  # time
                        return util.convertTime(self.time_format, self._data[row][event_idx])
                    elif column < self.columnCount():
                        return self._data[row][event_idx]


class MainWindow(QMainWindow, Ui_MainWindow):
    """
    Main BORIS window
    """

    # check first launch dialog
    no_first_launch_dialog = options.no_first_launch_dialog

    pj: dict = dict(cfg.EMPTY_PROJECT)
    project: bool = False  # project is loaded?
    geometric_measurements_mode = False  # geometric measurement mode active?

    state_behaviors_codes: tuple = tuple()

    time_observer_signal = pyqtSignal(float)
    mpv_eof_reached_signal = pyqtSignal(float)
    video_click_signal = pyqtSignal(int, str)

    processes: list = []  # list of QProcess processes
    overlays: dict = {}  # dict for storing video overlays

    undo_queue = deque()
    undo_description = deque()

    current_player: int = 0  # id of the selected (left click) video player

    mem_media_name: str = ""  # record current media name. Use to check if media changed
    mem_playlist_index: Union[int, None] = None
    saved_state = None
    user_move_slider: bool = False
    observationId: str = ""  # current observation id
    timeOffset: float = 0.0
    confirmSound: bool = False  # if True each keypress will be confirmed by a beep
    spectrogramHeight: int = 80
    spectrogram_time_interval = cfg.SPECTROGRAM_DEFAULT_TIME_INTERVAL
    spectrogram_color_map = cfg.SPECTROGRAM_DEFAULT_COLOR_MAP
    alertNoFocalSubject: bool = False  # if True an alert will show up if no focal subject
    trackingCursorAboveEvent: bool = False  # if True the cursor will appear above the current event in events table
    checkForNewVersion: bool = False  # if True BORIS will check for new version every 15 days
    pause_before_addevent: bool = False  # pause before "Add event" command CTRL + A
    timeFormat: str = cfg.HHMMSS  # 's' or 'hh:mm:ss'
    repositioningTimeOffset = 0
    automaticBackup: int = 0  # automatic backup interval (0 no backup)
    events_current_row: int = -1
    projectChanged: bool = False  # store if project was changed
    liveObservationStarted = False
    # data structures for external data plot
    plot_data: dict = {}
    ext_data_timer_list: list = []
    projectFileName: str = ""
    mediaTotalLength = None
    beep_every = 0

    plot_colors = cfg.BEHAVIORS_PLOT_COLORS
    behav_category_colors = cfg.CATEGORY_COLORS_LIST

    measurement_w = None
    current_image_size = None

    media_scan_sampling_mem: list = []
    behav_seq_separator: str = "|"
    # time laps
    fast = 10

    currentStates: dict = {}
    subject_name_index = {}
    flag_slow = False
    play_rate: float = 1
    play_rate_step: float = 0.1
    currentSubject: str = ""  # contains the current subject of observation
    coding_map_window_geometry = 0

    # FFmpeg
    memx, memy, mem_player = -1, -1, -1

    # path for ffmpeg/ffmpeg.exe program
    ffmpeg_bin = ""
    ffmpeg_cache_dir = ""

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

    mem_hash_obs: int = 0

    '''
    def add_button_menu(self, data, menu_obj):
        """
        add menu option from dictionary
        """
        if isinstance(data, dict):
            for k, v in data.items():
                sub_menu = QMenu(k, menu_obj)
                menu_obj.addMenu(sub_menu)
                self.add_button_menu(v, sub_menu)
        elif isinstance(data, list):
            for element in data:
                self.add_button_menu(element, menu_obj)
        else:
            action = menu_obj.addAction(data.split("|")[1])
            # tips are used to discriminate the menu option
            action.setStatusTip(data.split("|")[0])
            action.setIconVisibleInMenu(False)

    def behavior(self, action: str):
        """
        behavior menu
        """
        if action == "new":
            self.add_behavior()
        if action == "clone":
            self.clone_behavior()
        if action == "remove":
            self.remove_behavior()
        if action == "remove all":
            self.remove_all_behaviors()
        if action == "lower":
            self.convert_behaviors_keys_to_lower_case()
    '''

    def __init__(self, ffmpeg_bin, parent=None):
        super(MainWindow, self).__init__(parent)
        self.setupUi(self)

        sys.excepthook = self.excepthook

        self.ffmpeg_bin = ffmpeg_bin
        # set icons
        self.setWindowIcon(QIcon(":/small_logo"))
        """
        self.tb_export = QToolButton()
        self.tb_export.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.tb_export.setIcon(QIcon(":/export"))
        self.tb_export.setFocusPolicy(Qt.NoFocus)
        self.toolBar.addWidget(self.tb_export)

        behavior_button_items = [
            "new|Add new behavior",
            "clone|Clone behavior",
            "remove|Remove behavior",
            "remove all|Remove all behaviors",
            "lower|Convert keys to lower case",
        ]
        self.menu = QMenu()
        self.menu.triggered.connect(lambda x: self.behavior(action=x.statusTip()))
        self.add_button_menu(behavior_button_items, self.menu)
        self.tb_export.setMenu(self.menu)
        """

        gui_utilities.set_icons(self)

        self.setWindowTitle(f"{cfg.programName} ({__version__})")

        self.w_obs_info.setVisible(False)

        self.lbLogoBoris.setPixmap(QPixmap(":/logo"))

        self.lbLogoBoris.setScaledContents(False)
        self.lbLogoBoris.setAlignment(Qt.AlignCenter)

        # self.lbLogoUnito.setPixmap(QPixmap(":/dbios_unito"))
        # self.lbLogoUnito.setScaledContents(False)
        # self.lbLogoUnito.setAlignment(Qt.AlignCenter)

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
        for w in (
            self.lb_player_status,
            self.lb_current_media_time,
            self.lb_video_info,
            self.lb_zoom_level,
            self.lbFocalSubject,
            self.lbCurrentStates,
        ):
            w.clear()
            w.setFont(font)
        self.lbFocalSubject.setText(cfg.NO_FOCAL_SUBJECT)

        # statusbat font
        self.statusBar().setFont(font)

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

        # play rate are now displayed in the main info widget
        """
        # SPEED
        self.lbSpeed = QLabel()
        self.lbSpeed.setFrameStyle(QFrame.StyledPanel)
        self.lbSpeed.setMinimumWidth(40)
        self.statusbar.addPermanentWidget(self.lbSpeed)
        """

        # set painter for twEvents to highlight current row
        # self.twEvents.setItemDelegate(events_cursor.StyledItemDelegateTriangle(self.events_current_row))
        self.tv_events.setItemDelegate(events_cursor.StyledItemDelegateTriangle(self.events_current_row))

        connections.connections(self)
        self.config_param = cfg.INIT_PARAM
        config_file.read(self)
        menu_options.update_menu(self)

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
            "Check project integrity",
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
            self.results = dialog.Results_dialog()
            self.results.setWindowTitle("Check project integrity")
            self.results.ptText.clear()
            self.results.ptText.appendHtml(msg)
            self.results.show()
        else:
            QMessageBox.information(self, cfg.programName, "The current project has no issues")

    def project_changed(self):
        """
        project was changed
        """
        self.projectChanged = True
        menu_options.update_windows_title(self)

    def remove_media_files_path(self):
        """
        remove path of media files and images directories
        """

        if (
            dialog.MessageDialog(
                cfg.programName,
                (
                    "Removing the path of media files and image directories from the project file is irreversible.<br>"
                    "Are you sure to continue?"
                ),
                [cfg.YES, cfg.NO],
            )
            == cfg.NO
        ):
            return

        if project_functions.remove_media_files_path(self.pj, self.projectFileName):
            self.project_changed()

    def remove_data_files_path(self):
        """
        remove data files path
        """

        if (
            dialog.MessageDialog(
                cfg.programName,
                ("Removing the path of external data files is irreversible.<br>" "Are you sure to continue?"),
                [cfg.YES, cfg.NO],
            )
            == cfg.NO
        ):
            return

        if project_functions.remove_data_files_path(self.pj, self.projectFileName):
            self.project_changed()

    def set_media_files_path_relative_to_project_dir(self):
        """
        ask user confirmation for setting path from media files and path of images directory relative to the project directory
        """

        if (
            dialog.MessageDialog(
                cfg.programName,
                ("Are you sure to continue?"),
                [cfg.YES, cfg.NO],
            )
            == cfg.NO
        ):
            return
        if project_functions.set_media_paths_relative_to_project_dir(self.pj, self.projectFileName):
            self.project_changed()

    def set_data_files_path_relative_to_project_dir(self):
        """
        ask user confirmation for setting path from data files and path of images directory relative to the project directory
        """

        if (
            dialog.MessageDialog(
                cfg.programName,
                ("Are you sure to continue?"),
                [cfg.YES, cfg.NO],
            )
            == cfg.NO
        ):
            return

        if project_functions.set_data_paths_relative_to_project_dir(self.pj, self.projectFileName):
            self.project_changed()

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

    def click_signal_from_coding_pad(self, behaviorCode):
        """
        handle click received from coding pad
        """
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
            QMessageBox.warning(
                self,
                cfg.programName,
                "The subjects pad is not available in <b>VIEW</b> mode",
            )
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
            filtered_subjects = [self.twSubjects.item(i, cfg.EVENT_SUBJECT_FIELD_IDX).text() for i in range(self.twSubjects.rowCount())]
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

        if self.twEthogram.rowCount() != len(self.pj[cfg.ETHOGRAM]):
            self.project_changed()

        self.load_behaviors_in_twEthogram([self.pj[cfg.ETHOGRAM][x][cfg.BEHAVIOR_CODE] for x in self.pj[cfg.ETHOGRAM]])

        # update coding pad
        if hasattr(self, "codingpad"):
            self.codingpad.filtered_behaviors = [self.twEthogram.item(i, 1).text() for i in range(self.twEthogram.rowCount())]
            self.codingpad.compose()

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
    ) -> Tuple[bool, list]:
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
            True, []

        behavior_type = [x.upper() for x in behavior_type]

        paramPanelWindow = param_panel.Param_panel()
        paramPanelWindow.setWindowTitle(title)
        paramPanelWindow.lbBehaviors.setText(text)
        for w in (
            paramPanelWindow.lwSubjects,
            paramPanelWindow.pbSelectAllSubjects,
            paramPanelWindow.pbUnselectAllSubjects,
            paramPanelWindow.pbReverseSubjectsSelection,
            paramPanelWindow.lbSubjects,
            paramPanelWindow.cbIncludeModifiers,
            paramPanelWindow.cbExcludeBehaviors,
            paramPanelWindow.frm_time,
            paramPanelWindow.frm_time_bin_size,
        ):
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
            for behavior in [self.pj[cfg.ETHOGRAM][x][cfg.BEHAVIOR_CODE] for x in util.sorted_keys(self.pj[cfg.ETHOGRAM])]:
                if project_functions.event_type(behavior, self.pj[cfg.ETHOGRAM]) not in behavior_type:
                    continue

                if (categories == ["###no category###"]) or (
                    behavior
                    in [
                        self.pj[cfg.ETHOGRAM][x][cfg.BEHAVIOR_CODE]
                        for x in self.pj[cfg.ETHOGRAM]
                        if cfg.BEHAVIOR_CATEGORY in self.pj[cfg.ETHOGRAM][x] and self.pj[cfg.ETHOGRAM][x][cfg.BEHAVIOR_CATEGORY] == category
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
                self.project_changed()

            gui_utilities.save_geometry(paramPanelWindow, "filter behaviors")

            if table == cfg.ETHOGRAM:
                self.load_behaviors_in_twEthogram(paramPanelWindow.selectedBehaviors)
                # update coding pad
                if hasattr(self, "codingpad"):
                    self.codingpad.filtered_behaviors = [self.twEthogram.item(i, 1).text() for i in range(self.twEthogram.rowCount())]
                    self.codingpad.compose()
                return False, []
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
        filtered_subjects = [self.twSubjects.item(i, cfg.EVENT_SUBJECT_FIELD_IDX).text() for i in range(self.twSubjects.rowCount())]

        for subject in [self.pj[cfg.SUBJECTS][x][cfg.SUBJECT_NAME] for x in util.sorted_keys(self.pj[cfg.SUBJECTS])]:
            paramPanelWindow.item = QListWidgetItem(subject)
            if subject in filtered_subjects:
                paramPanelWindow.item.setCheckState(Qt.Checked)
            else:
                paramPanelWindow.item.setCheckState(Qt.Unchecked)

            paramPanelWindow.lwBehaviors.addItem(paramPanelWindow.item)

        if paramPanelWindow.exec_():
            if self.observationId and set(paramPanelWindow.selectedBehaviors) != set(filtered_subjects):
                self.project_changed()

            self.load_subjects_in_twSubjects(paramPanelWindow.selectedBehaviors)

            gui_utilities.save_geometry(paramPanelWindow, "filter subjects")

            # update subjects pad
            if hasattr(self, "subjects_pad"):
                self.subjects_pad.filtered_subjects = [
                    self.twSubjects.item(i, cfg.EVENT_SUBJECT_FIELD_IDX).text() for i in range(self.twSubjects.rowCount())
                ]
                self.subjects_pad.compose()

    def generate_wav_file_from_media(self):
        """
        extract wav from all media files loaded in player #1
        """

        logging.debug("function: create wav file from media")

        # check temp dir for images from ffmpeg
        tmp_dir = self.ffmpeg_cache_dir if self.ffmpeg_cache_dir and os.path.isdir(self.ffmpeg_cache_dir) else tempfile.gettempdir()

        w = dialog.Info_widget()
        w.lwi.setVisible(False)
        w.resize(350, 100)
        w.setWindowFlags(Qt.WindowStaysOnTopHint)
        w.setWindowTitle(cfg.programName)
        w.label.setText("Extracting WAV from media files...")

        for media in self.pj[cfg.OBSERVATIONS][self.observationId][cfg.FILE][cfg.PLAYER1]:
            media_file_path = project_functions.full_path(media, self.projectFileName)
            if os.path.isfile(media_file_path):
                w.show()
                QApplication.processEvents()

                if util.extract_wav(self.ffmpeg_bin, media_file_path, tmp_dir) == "":
                    QMessageBox.critical(
                        self,
                        cfg.programName,
                        f"Error during extracting WAV of the media file {media_file_path}",
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

        if plot_type not in (cfg.WAVEFORM_PLOT, cfg.SPECTROGRAM_PLOT, cfg.EVENTS_PLOT):
            logging.critical(f"Error on plot type: {plot_type}")
            return

        if ((self.playerType == cfg.LIVE) or (self.playerType in cfg.VIEWERS)) and plot_type in (
            cfg.WAVEFORM_PLOT,
            cfg.SPECTROGRAM_PLOT,
        ):
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
                    # media_file_path = project_functions.full_path(media, self.projectFileName)

                    if not project_functions.has_audio(self.pj[cfg.OBSERVATIONS][self.observationId], media):
                        QMessageBox.critical(
                            self,
                            cfg.programName,
                            f"The media file {media} does not have an audio track. Plotting the spectrogram will not be possible.",
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

                tmp_dir = self.ffmpeg_cache_dir if self.ffmpeg_cache_dir and os.path.isdir(self.ffmpeg_cache_dir) else tempfile.gettempdir()

                wav_file_path = (
                    pl.Path(tmp_dir)
                    / pl.Path(self.dw_player[0].player.playlist[self.dw_player[0].player.playlist_pos]["filename"] + ".wav").name
                )

                self.spectro = plot_spectrogram_rt.Plot_spectrogram_RT()

                self.spectro.setWindowFlags(Qt.WindowStaysOnTopHint)
                self.spectro.setWindowFlags(self.spectro.windowFlags() & ~Qt.WindowMinimizeButtonHint)

                self.spectro.interval = self.spectrogram_time_interval
                self.spectro.cursor_color = cfg.REALTIME_PLOT_CURSOR_COLOR

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
                    # media_file_path = project_functions.full_path(media, self.projectFileName)

                    if not project_functions.has_audio(self.pj[cfg.OBSERVATIONS][self.observationId], media):
                        QMessageBox.critical(
                            self,
                            cfg.programName,
                            f"The media file {media} does not have an audio track. Plotting the waveform will not be possible.",
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

                tmp_dir = self.ffmpeg_cache_dir if self.ffmpeg_cache_dir and os.path.isdir(self.ffmpeg_cache_dir) else tempfile.gettempdir()

                wav_file_path = (
                    pl.Path(tmp_dir)
                    / pl.Path(self.dw_player[0].player.playlist[self.dw_player[0].player.playlist_pos]["filename"] + ".wav").name
                )

                self.waveform = plot_waveform_rt.Plot_waveform_RT()

                self.waveform.setWindowFlags(Qt.WindowStaysOnTopHint)
                self.waveform.setWindowFlags(self.waveform.windowFlags() & ~Qt.WindowMinimizeButtonHint)

                self.waveform.interval = self.spectrogram_time_interval
                self.waveform.cursor_color = cfg.REALTIME_PLOT_CURSOR_COLOR

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
                logging.debug("create real-time events plot widget")

                self.plot_events = plot_events_rt.Plot_events_RT()

                self.plot_events.setWindowFlags(Qt.WindowStaysOnTopHint)
                self.plot_events.setWindowFlags(self.plot_events.windowFlags() & ~Qt.WindowMinimizeButtonHint)

                self.plot_events.groupby = "behaviors"
                self.plot_events.interval = 60  # time interval for x axe
                self.plot_events.cursor_color = cfg.REALTIME_PLOT_CURSOR_COLOR
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
                    """
                    behav_key = [
                        k for k in self.pj[cfg.ETHOGRAM] if self.pj[cfg.ETHOGRAM][k][cfg.BEHAVIOR_CODE] == behavior
                    ][0]
                    """

                    col = util.behavior_user_color(self.pj[cfg.ETHOGRAM], behavior)
                    if col is not None:
                        self.plot_events.behav_color[behavior] = col
                    else:
                        self.plot_events.behav_color[behavior] = cfg.BEHAVIORS_PLOT_COLORS[idx]

                self.plot_events.sendEvent.connect(self.signal_from_widget)

                self.plot_events.show()

                self.update_realtime_plot(force_plot=True)

                if not self.dw_player[0].player.pause:
                    self.plot_timer.start()

    def update_realtime_plot(self, force_plot: bool = False):
        """
        update real-time events plot (if any)
        """
        if hasattr(self, "plot_events"):
            if not self.plot_events.visibleRegion().isEmpty():
                self.plot_events.events_list = self.pj[cfg.OBSERVATIONS][self.observationId][cfg.EVENTS]
                self.plot_events.plot_events(float(self.getLaps()), force_plot)

    def plot_timer_out(self):
        """
        timer for plotting visualizations: spectrogram, waveform, plot events
        """

        self.update_realtime_plot()

        if self.playerType != cfg.MEDIA:
            return

        current_media_time = self.dw_player[0].player.time_pos

        tmp_dir = self.ffmpeg_cache_dir if self.ffmpeg_cache_dir and os.path.isdir(self.ffmpeg_cache_dir) else tempfile.gettempdir()

        try:
            wav_file_path = str(
                pl.Path(tmp_dir)
                / pl.Path(self.dw_player[0].player.playlist[self.dw_player[0].player.playlist_pos]["filename"] + ".wav").name
            )
        except Exception:
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
                self,
                cfg.programName,
                "No project found",
                QMessageBox.Ok | QMessageBox.Default,
                QMessageBox.NoButton,
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
        self.project_changed()

    def actionCheckUpdate_activated(self, flagMsgOnlyIfNew=False):
        """
        check BORIS web site for updates
        ask user for updating
        """

        versionURL = "https://www.boris.unito.it/static/ver4.dat"
        try:
            last_version = urllib.request.urlopen(versionURL).read().strip().decode("utf-8")
        except Exception:
            QMessageBox.warning(self, cfg.programName, "Can not check for updates...")
            return

        # record check timestamp
        config_file.save(self, lastCheckForNewVersion=int(time.mktime(time.localtime())))

        if util.versiontuple(last_version) > util.versiontuple(__version__):
            if (
                dialog.MessageDialog(
                    cfg.programName,
                    (
                        f"A new version is available: v. {last_version}.<br><br>"
                        'For updating manually go to <a href="https://www.boris.unito.it">https://www.boris.unito.it</a>.<br>'
                    ),
                    (cfg.CANCEL, "Update automatically"),
                )
                == cfg.CANCEL
            ):
                return

        else:
            msg = f"The version you are using is the last one: <b>{__version__}</b>"
            QMessageBox.information(self, cfg.programName, msg)

            # any news?
            newsURL = "https://www.boris.unito.it/static/news.dat"
            news = urllib.request.urlopen(newsURL).read().strip().decode("utf-8")
            if news:
                QMessageBox.information(self, cfg.programName, news)
            return

        # check if a .git is present
        if (pl.Path(__file__).parent.parent / pl.Path(".git")).is_dir():
            QMessageBox.critical(self, cfg.programName, "A .git directory is present, BORIS cannot be automatically updated.")
            return

        # download zip archive
        try:
            zip_content = urllib.request.urlopen(f"https://github.com/olivierfriard/BORIS/archive/refs/tags/v{last_version}.zip").read()
        except Exception:
            QMessageBox.critical(self, cfg.programName, "Cannot download the new version")
            return

        temp_zip = tempfile.NamedTemporaryFile(suffix=".zip")
        try:
            with open(temp_zip.name, "wb") as f_out:
                f_out.write(zip_content)
        except Exception:
            QMessageBox.critical(self, cfg.programName, "A problem occurred during saving the new version of BORIS.")
            return

        # extract to temp dir
        try:
            temp_dir = tempfile.TemporaryDirectory()
            with zipfile.ZipFile(temp_zip.name, "r") as zip_ref:
                zip_ref.extractall(temp_dir.name)
        except Exception:
            QMessageBox.critical(self, cfg.programName, "A problem occurred during the unzip of the new version.")
            return

        # copy from temp dir to current BORIS dir
        try:
            shutil.copytree(f"{temp_dir.name}/BORIS-{last_version}", pl.Path(__file__).parent.parent, dirs_exist_ok=True)
        except Exception:
            QMessageBox.critical(self, cfg.programName, "A problem occurred during the copy the new version of BORIS.")
            return

        QMessageBox.information(self, cfg.programName, f"BORIS was updated to v. {last_version}. Restart the program to apply the changes.")

    def seek_mediaplayer(self, new_time: dec, player=0) -> int:
        """
        change media position in player

        Args:
            new_time (dec): time in seconds

        Returns:
            int: error code:
                0 OK
                1 time greater than duration

        """
        flag_paused = self.is_playing()

        logging.debug(f"paused? {flag_paused}")

        if not self.dw_player[player].player.playlist_count:
            return

        # one media
        if self.dw_player[player].player.playlist_count == 1:
            if new_time < self.dw_player[player].player.duration:
                self.dw_player[player].player.seek(new_time, "absolute+exact")

                if player == 0 and not self.user_move_slider:
                    self.video_slider.setValue(
                        round(self.dw_player[0].player.time_pos / self.dw_player[0].player.duration * (cfg.SLIDER_MAXIMUM - 1))
                    )
                return 0
            else:
                return 1

        # many media
        else:
            if new_time < self.dw_player[player].cumul_media_durations_sec[-1]:
                for idx, d in enumerate(self.dw_player[player].cumul_media_durations_sec[:-1]):
                    if d <= new_time < self.dw_player[player].cumul_media_durations_sec[idx + 1]:
                        self.dw_player[player].player.playlist_pos = idx
                        time.sleep(0.5)

                        self.dw_player[player].player.seek(
                            round(
                                float(new_time)
                                - sum(self.dw_player[player].media_durations[0 : self.dw_player[player].player.playlist_pos]) / 1000,
                                3,
                            ),
                            "absolute+exact",
                        )

                        break

                if player == 0 and not self.user_move_slider:
                    self.video_slider.setValue(
                        round(self.dw_player[0].player.time_pos / self.dw_player[0].player.duration * (cfg.SLIDER_MAXIMUM - 1))
                    )
                return 0
            else:
                QMessageBox.warning(
                    self,
                    cfg.programName,
                    (
                        "The indicated position is greater than the total media duration "
                        f"({util.seconds2time(self.dw_player[player].cumul_media_durations_sec[-1])})"
                    ),
                )
                return 1

    def jump_to(self) -> None:
        """
        jump to the user specified media position
        """

        if self.playerType != cfg.MEDIA:
            return

        jt = dialog.Ask_time(0)
        jt.setWindowTitle("Jump to specific time")
        jt.label.setText("Set the time")

        if jt.exec_():
            new_time = jt.time_widget.get_time()
            if new_time < 0:
                return
            self.seek_mediaplayer(new_time)
            self.update_visualizations()

    def previous_media_file(self):
        """
        go to previous media file (if any)
        """

        logging.debug("previous media file")

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

        logging.debug("next media file")

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

    def set_mute(self, nplayer):
        """
        set mute on/off for player nplayer

        Args:
            nplayer (str): player to mute
        """
        if self.playerType == cfg.MEDIA:
            self.dw_player[nplayer].player.mute = not self.dw_player[nplayer].player.mute
            logging.debug(f"{nplayer} set mute {'ON' if self.dw_player[nplayer].player.mute else 'OFF'}")

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
                (f"project not autosaved: " f"observation id: {self.observationId} " f"project file name: {self.projectFileName}")
            )

    def update_subject(self, subject: str) -> None:
        """
        update the self.currentSubject variable with subject
        update label lbFocalSubject with subject

        Args:
            subject (str): subject
        """
        if (not subject) or (subject == cfg.NO_FOCAL_SUBJECT) or (self.currentSubject == subject):
            self.currentSubject = ""
            self.lbFocalSubject.setText(cfg.NO_FOCAL_SUBJECT)
        else:
            self.currentSubject = subject
            self.lbFocalSubject.setText(f" Focal subject: <b>{self.currentSubject}</b>")

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
                frameCurrentMedia = requiredFrame - sum(self.dw_player[int(player) - 1].media_durations[0:idx]) / frameMs
                break
        return currentMedia, round(frameCurrentMedia)

    def extract_exif_DateTimeOriginal(self, file_path: str) -> int:
        """
        extract the exif extract_exif_DateTimeOriginal tag
        return epoch time
        if the tag is not available return -1
        """
        try:
            with open(file_path, "rb") as f_in:
                tags = exifread.process_file(f_in, details=False, stop_tag="EXIF DateTimeOriginal")
                if "EXIF DateTimeOriginal" in tags:
                    date_time_original = (
                        f'{tags["EXIF DateTimeOriginal"].values[:4]}-'
                        f'{tags["EXIF DateTimeOriginal"].values[5:7]}-'
                        f'{tags["EXIF DateTimeOriginal"].values[8:10]} '
                        f'{tags["EXIF DateTimeOriginal"].values.split(" ")[-1]}'
                    )
                    return int(datetime.datetime.strptime(date_time_original, "%Y-%m-%d %H:%M:%S").timestamp())
                else:
                    try:
                        # read from file name (YYYY-MM-DD_HHMMSS)
                        return int(datetime.datetime.strptime(pl.Path(file_path).stem, "%Y-%m-%d_%H%M%S").timestamp())
                    except Exception:
                        # read from file name (YYYY-MM-DD_HH:MM:SS)
                        return int(datetime.datetime.strptime(pl.Path(file_path).stem, "%Y-%m-%d_%H:%M:%S").timestamp())

        except Exception:
            return -1

    def extract_frame(self, dw):
        """
        for MEDIA obs: extract frame from video and visualize it in frame_viewer
        for IMAGES obs: load picture and visualize it in frame_viewer, extract EXIF Date/Time Original tag if available
        """

        logging.debug("extract_frame")

        if self.playerType == cfg.MEDIA:
            time.sleep(0.3)  # required for correct frame number

            dw.frame_viewer.setPixmap(
                util.pil2pixmap(dw.player.screenshot_raw()).scaled(dw.frame_viewer.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            )

        if self.playerType == cfg.IMAGES:
            pixmap = QPixmap(self.images_list[self.image_idx])
            self.current_image_size = (pixmap.size().width(), pixmap.size().height())

            msg = f"Image index: <b>{self.image_idx + 1} / {len(self.images_list)}</b>"

            # extract EXIF tag
            if self.pj[cfg.OBSERVATIONS][self.observationId].get(cfg.USE_EXIF_DATE, False):
                date_time_original = self.extract_exif_DateTimeOriginal(self.images_list[self.image_idx])
                if date_time_original != -1:
                    msg += f"<br>EXIF Date/Time Original: <b>{datetime.datetime.fromtimestamp(date_time_original):%Y-%m-%d %H:%M:%S}</b>"
                else:
                    msg += "<br>EXIF Date/Time Original: <b>NA</b>"

                # self.image_time_ref = 0
                if self.image_idx == 0 and date_time_original != -1:
                    self.image_time_ref = date_time_original

                if date_time_original != -1:
                    if self.image_time_ref is not None:
                        seconds_from_1st = date_time_original - self.image_time_ref

                    if self.timeFormat == cfg.HHMMSS:
                        seconds_from_1st_formated = util.seconds2time(seconds_from_1st).split(".")[0]  # remove milliseconds
                    else:
                        seconds_from_1st_formated = seconds_from_1st

                else:
                    seconds_from_1st_formated = cfg.NA

                msg += f"<br>Time from 1st image: <b>{seconds_from_1st_formated}</b>"

            # image path
            msg += f"<br><br>Directory: <b>{pl.Path(self.images_list[self.image_idx]).parent}</b>"
            msg += f"<br>File name: <b>{pl.Path(self.images_list[self.image_idx]).name}</b>"
            msg += f"<br><small>Image resolution: <b>{pixmap.size().width()}x{pixmap.size().height()}</b></small>"

            self.lb_current_media_time.setText(msg)

            dw.frame_viewer.setPixmap(pixmap.scaled(dw.frame_viewer.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation))

        self.get_events_current_row()

        # index of current subject selected by observer
        subject_idx = self.subject_name_index[self.currentSubject] if self.currentSubject else ""

        self.currentStates = util.get_current_states_modifiers_by_subject(
            self.state_behaviors_codes,
            self.pj[cfg.OBSERVATIONS][self.observationId][cfg.EVENTS],
            dict(self.pj[cfg.SUBJECTS], **{"": {"name": ""}}),
            self.getLaps(),
            include_modifiers=True,
        )

        self.lbCurrentStates.setText(f"Observed behaviors: {', '.join(self.currentStates[subject_idx])}")
        # show current states in subjects table
        self.show_current_states_in_subjects_table()

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

    def reload_frame(self):
        """
        receive signal to reload frames from geometric measurements
        """

        # reload frame
        if self.playerType == cfg.IMAGES:
            if self.image_idx < len(self.images_list) - 1:
                self.extract_frame(self.dw_player[0])

        if self.playerType == cfg.MEDIA:
            for dw in self.dw_player:
                self.extract_frame(dw)

        geometric_measurement.redraw_measurements(self)

    def save_picture_with_measurements(self, mode: str):
        """
        receive signal to save picture from geometric measurements
        """

        def draw_element(painter, element):
            RADIUS = 6

            def draw_point(x, y, RADIUS):
                painter.drawEllipse(QPoint(x, y), RADIUS, RADIUS)
                # cross inside circle
                painter.drawLine(x - RADIUS, y, x + RADIUS, y)
                painter.drawLine(x, y - RADIUS, x, y + RADIUS)

            painter.setPen(QColor(element["color"]))

            if element["object_type"] == cfg.POINT_OBJECT:
                x, y = element["coordinates"][0]
                draw_point(x, y, RADIUS)

            if element["object_type"] in (cfg.ANGLE_OBJECT, cfg.ORIENTED_ANGLE_OBJECT):
                x1, y1 = element["coordinates"][0]
                x2, y2 = element["coordinates"][1]
                x3, y3 = element["coordinates"][2]
                painter.drawLine(x1, y1, x2, y2)
                painter.drawLine(x1, y1, x3, y3)
                draw_point(x1, y1, RADIUS)

            if element["object_type"] == cfg.POLYGON_OBJECT:
                polygon = QPolygon()
                for x, y in element["coordinates"]:
                    x, y = [x, y]
                    polygon.append(QPoint(x, y))
                painter.drawPolygon(polygon)

            if element["object_type"] == cfg.POLYLINE_OBJECT:
                for idx1, p1 in enumerate(element["coordinates"][:-1]):
                    x1, y1 = p1
                    x2, y2 = element["coordinates"][idx1 + 1]
                    painter.drawLine(x1, y1, x2, y2)

            return painter

        output_dir = QFileDialog().getExistingDirectory(
            self,
            "Select a directory to save the frames",
            os.path.expanduser("~"),
            options=QFileDialog().ShowDirsOnly,
        )
        if not output_dir:
            return

        if mode == "current":
            if self.pj[cfg.OBSERVATIONS][self.observationId][cfg.TYPE] == cfg.IMAGES:
                pixmap = QPixmap(self.images_list[self.image_idx])
                # draw measurements
                RADIUS = 6
                painter = QPainter()
                painter.begin(pixmap)
                for element in self.measurement_w.draw_mem.get(self.image_idx, []):
                    painter = draw_element(painter, element)
                painter.end()

                image_file_path = str(pl.Path(output_dir) / f"{pl.Path(self.images_list[self.image_idx]).stem}.jpg")
                # check if file already exists
                if pl.Path(image_file_path).is_file():
                    if (
                        dialog.MessageDialog(cfg.programName, f"The file {image_file_path} already exists.", (cfg.CANCEL, cfg.OVERWRITE))
                        == cfg.CANCEL
                    ):
                        return

                pixmap.save(image_file_path, "JPG")

            if self.pj[cfg.OBSERVATIONS][self.observationId][cfg.TYPE] == cfg.MEDIA:
                for n_player, dw in enumerate(self.dw_player):
                    pixmap = util.pil2pixmap(dw.player.screenshot_raw())

                    p = pl.Path(dw.player.playlist[dw.player.playlist_pos]["filename"])
                    image_file_path = str(pl.Path(output_dir) / f"{p.stem}_{n_player}_{dw.player.estimated_frame_number:06}.jpg")

                    # draw measurements
                    RADIUS = 6
                    painter = QPainter()
                    painter.begin(pixmap)

                    for element in self.measurement_w.draw_mem.get(dw.player.estimated_frame_number, []):
                        if element["player"] != n_player:
                            continue
                        painter = draw_element(painter, element)

                    painter.end()
                    # check if file already exists
                    if pl.Path(image_file_path).is_file():
                        if (
                            dialog.MessageDialog(
                                cfg.programName, f"The file {image_file_path} already exists.", (cfg.CANCEL, cfg.OVERWRITE)
                            )
                            == cfg.CANCEL
                        ):
                            return

                    pixmap.save(image_file_path, "JPG")

        if mode == "all":
            if self.pj[cfg.OBSERVATIONS][self.observationId][cfg.TYPE] == cfg.IMAGES:
                for frame_idx in self.measurement_w.draw_mem:
                    pixmap = QPixmap(self.images_list[frame_idx])

                    # draw measurements
                    RADIUS = 6
                    painter = QPainter()
                    painter.begin(pixmap)
                    for element in self.measurement_w.draw_mem.get(frame_idx, []):
                        painter = draw_element(painter, element)
                    painter.end()

                    image_file_path = str(pl.Path(output_dir) / f"{pl.Path(self.images_list[frame_idx]).stem}.jpg")
                    # check if file already exists
                    if pl.Path(image_file_path).is_file():
                        if (
                            dialog.MessageDialog(
                                cfg.programName, f"The file {image_file_path} already exists.", (cfg.CANCEL, cfg.OVERWRITE)
                            )
                            == cfg.CANCEL
                        ):
                            return

                    pixmap.save(image_file_path, "JPG")

            if self.pj[cfg.OBSERVATIONS][self.observationId][cfg.TYPE] == cfg.MEDIA:
                d: dict = {}
                for frame_idx in self.measurement_w.draw_mem:
                    if frame_idx not in d:
                        d[frame_idx] = {}
                    for element in self.measurement_w.draw_mem[frame_idx]:
                        if element["player"] not in d[frame_idx]:
                            d[frame_idx][element["player"]] = []
                        d[frame_idx][element["player"]].append(element)

                for frame_idx in d:
                    for n_player in d[frame_idx]:
                        media_path = pl.Path(
                            self.dw_player[n_player - 1].player.playlist[self.dw_player[n_player - 1].player.playlist_pos]["filename"]
                        )
                        file_name = pl.Path(f"{media_path.stem}_{element['player']}_{frame_idx:06}")

                        ffmpeg_command = [
                            self.ffmpeg_bin,
                            "-y",
                            "-i",
                            str(media_path),
                            "-vf",
                            rf"select=gte(n\, {frame_idx})",
                            "-frames:v",
                            "1",
                            str(pl.Path(output_dir) / file_name.with_suffix(".jpg")),
                        ]

                        p = subprocess.Popen(ffmpeg_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE)  # do not use shell=True!
                        out, error = p.communicate()

                        pixmap = QPixmap(str(pl.Path(output_dir) / file_name.with_suffix(".jpg")))
                        RADIUS = 6
                        painter = QPainter()
                        painter.begin(pixmap)

                        for element in d[frame_idx][n_player]:
                            painter = draw_element(painter, element)

                        painter.end()
                        # check if file already exists
                        if (pl.Path(output_dir) / file_name.with_suffix(".jpg")).is_file():
                            answer = dialog.MessageDialog(
                                cfg.programName,
                                f"The file {pl.Path(output_dir) / file_name.with_suffix('.jpg')} already exists.",
                                (cfg.CANCEL, cfg.OVERWRITE, "Abort"),
                            )
                            if answer == cfg.CANCEL:
                                continue
                            if answer == "Abort":
                                return

                        pixmap.save(str(pl.Path(output_dir) / file_name.with_suffix(".jpg")), "JPG")

    def resize_dw(self, dw_id):
        """
        dockwidget was resized. Adapt overlay if any
        """

        def reduce_opacity(im, opacity):
            """
            Returns an image with reduced opacity.
            opacity = 1 -> 0% transparent
            opacity = 0 -> 100% transparent
            """
            if im.mode != "RGBA":
                im = im.convert("RGBA")
            else:
                im = im.copy()
            alpha = im.split()[3]
            alpha = PIL.ImageEnhance.Brightness(alpha).enhance(opacity)
            im.putalpha(alpha)
            return im

        if self.geometric_measurements_mode:
            pass

        if self.playerType not in (cfg.MEDIA):
            return

        if not self.observationId:
            return

        if not self.pj[cfg.OBSERVATIONS][self.observationId][cfg.MEDIA_INFO].get(cfg.OVERLAY, {}):
            return

        try:
            img = Image.open(self.pj[cfg.OBSERVATIONS][self.observationId][cfg.MEDIA_INFO][cfg.OVERLAY][str(dw_id + 1)]["file name"])
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

        opacity = -1 / 100 * self.pj[cfg.OBSERVATIONS][self.observationId][cfg.MEDIA_INFO][cfg.OVERLAY][str(dw_id + 1)]["transparency"] + 1

        img_resized = reduce_opacity(img_resized, opacity)

        # check position
        x_offset, y_offset = 0, 0
        if self.pj[cfg.OBSERVATIONS][self.observationId][cfg.MEDIA_INFO][cfg.OVERLAY][str(dw_id + 1)]["overlay position"]:
            try:
                x_offset = int(
                    self.pj[cfg.OBSERVATIONS][self.observationId][cfg.MEDIA_INFO][cfg.OVERLAY][str(dw_id + 1)]["overlay position"]
                    .split(",")[0]
                    .strip()
                )
                y_offset = int(
                    self.pj[cfg.OBSERVATIONS][self.observationId][cfg.MEDIA_INFO][cfg.OVERLAY][str(dw_id + 1)]["overlay position"]
                    .split(",")[1]
                    .strip()
                )
            except Exception:
                logging.warning("error in overlay position")

        try:
            self.overlays[dw_id].remove()
        except Exception:
            logging.debug("error removing overlay")
        try:
            self.overlays[dw_id].update(img_resized, pos=(x1 + x_offset, y1 + y_offset))
        except Exception:
            logging.debug("error updating overlay")

    def player_clicked(self, player_id: int, cmd: str) -> None:
        """
        receive signal from dock widget when player clicked.
        """

        def get_pan_for_zoom_in_clicked_coordinates(player, videoframe, zoom, pan_x, pan_y, new_zoom):
            """
            returns the pan (pan_x, pan_y) necessary to zoom in or zoom out in the clicked coordinates
            actual zoom is 2**zoom
            """
            # video width and height
            vw = player.width
            vh = player.height

            # dockable window width and height
            dw = videoframe.size().width()
            dh = videoframe.size().height()

            # click coordinates in dialog reference frame
            dx = player.mouse_pos["x"]
            dy = player.mouse_pos["y"]

            # convert to float for operations
            vw = float(vw)
            vh = float(vh)
            dw = float(dw)
            dh = float(dh)
            dx = float(dx)
            dy = float(dy)

            if dw / dh >= vw / vh:  # vertical black lanes
                dialog_to_video_ratio = dh / vh
            else:  # horizontal black lanes
                dialog_to_video_ratio = dw / vw

            # clicked coordinates in video reference frame for the current zoom/pan
            actual_zoom = 2**zoom
            vx = (dx - dw / 2) / dialog_to_video_ratio / actual_zoom - pan_x * vw + vw / 2
            vy = (dy - dh / 2) / dialog_to_video_ratio / actual_zoom - pan_y * vh + vh / 2

            # new pan to zoom in or out in the clicked coordinates
            actual_zoom = 2**new_zoom
            pan_x = ((dx - dw / 2) / dialog_to_video_ratio / actual_zoom - vx + vw / 2) / vw
            pan_y = ((dy - dh / 2) / dialog_to_video_ratio / actual_zoom - vy + vh / 2) / vh

            return pan_x, pan_y

        def get_current_pan_and_zoom():
            # CURRENT PAN/ZOOM
            pan_x = self.dw_player[player_id].player.video_pan_x
            pan_y = self.dw_player[player_id].player.video_pan_y
            zoom = self.dw_player[player_id].player.video_zoom
            return pan_x, pan_y, zoom

        def set_and_update_pan_and_zoom(pan_x, pan_y, zoom):
            # SET
            self.dw_player[player_id].player.video_pan_x = pan_x
            self.dw_player[player_id].player.video_pan_y = pan_y
            self.dw_player[player_id].player.video_zoom = zoom
            # UPDATE
            self.update_project_zoom_pan_values()

        def do_zoom_in_clicked_coords(zoom_increment):
            """
            The video is zoomed at the clicked coords X 2**zoom_increment
            eg.
                zoom_increment=+1 -> zoom in,  x 2
                zoom_increment=-1 -> zoom out,  x (1/2)

            """
            # CURRENT PAN/ZOOM
            pan_x, pan_y, zoom = get_current_pan_and_zoom()
            # NEW ZOOM (ZOOM IN by a factor of 2)
            new_zoom = zoom + zoom_increment
            # COMPUTE NEW PAN
            new_pan_x, new_pan_y = get_pan_for_zoom_in_clicked_coordinates(
                self.dw_player[player_id].player, self.dw_player[player_id].videoframe, zoom, pan_x, pan_y, new_zoom
            )
            # SET NEW VALUES AND UPDATE
            set_and_update_pan_and_zoom(new_pan_x, new_pan_y, new_zoom)

        def do_pan_in_clicked_coords(pan_x_increment, pan_y_increment):
            """
            The video is panned at the clicked coords
            pan_x and pan_y are relative to width and height
            eg.
                pan_x_increment=0.01 -> pan to the right 1% of video_width
            """
            # CURRENT PAN/ZOOM
            pan_x, pan_y, zoom = get_current_pan_and_zoom()

            new_pan_x = pan_x + pan_x_increment
            new_pan_y = pan_y + pan_y_increment
            new_zoom = zoom

            # SET NEW VALUES AND UPDATE
            set_and_update_pan_and_zoom(new_pan_x, new_pan_y, new_zoom)

        if cmd == "MBTN_LEFT_DBL":
            print("left dbl")
            # ZOOM IN x2
            do_zoom_in_clicked_coords(zoom_increment=1)
            return
        if cmd == "MBTN_RIGHT_DBL":
            # ZOOM OUT x2
            do_zoom_in_clicked_coords(zoom_increment=-1)
            return
        if cmd == "Ctrl+WHEEL_UP":
            # ZOOM IN (3 wheel steps to zoom X2)
            do_zoom_in_clicked_coords(zoom_increment=1.0 / 3.0)
            return
        if cmd == "Ctrl+WHEEL_DOWN":
            # ZOOM OUT (3 wheel steps to zoom X2)
            do_zoom_in_clicked_coords(zoom_increment=-1.0 / 3.0)
            return
        if cmd == "WHEEL_UP":
            # PAN UP (VIDEO MOVES DOWN)
            do_pan_in_clicked_coords(pan_x_increment=0, pan_y_increment=+0.01)
            return
        if cmd == "WHEEL_DOWN":
            # PAN DOWN (VIDEO MOVES UP)
            do_pan_in_clicked_coords(pan_x_increment=0, pan_y_increment=-0.01)
            return
        if cmd == "Shift+WHEEL_UP":
            # PAN LEFT (VIDEO MOVES TO THE RIGHT)
            do_pan_in_clicked_coords(pan_x_increment=+0.01, pan_y_increment=0)
            return
        if cmd == "Shift+WHEEL_DOWN":
            # PAN RIGHT (VIDEO MOVES TO THE LEFT)
            do_pan_in_clicked_coords(pan_x_increment=-0.01, pan_y_increment=0)
            return
        if cmd == "Shift+MBTN_LEFT":
            # RESET PAN AND ZOOM TO DEFAULT
            set_and_update_pan_and_zoom(pan_x=0, pan_y=0, zoom=0)
            return

    # def read_tw_event_field(self, row_idx: int, player_type: str, field_type: str) -> Union[str, None, int, dec]:
    #    """
    #    return value of field for event in TW or NA if not available
    #    """
    #    if field_type not in cfg.TW_EVENTS_FIELDS[player_type]:
    #        return None
    #
    #    return self.twEvents.item(row_idx, cfg.TW_OBS_FIELD[player_type][field_type]).text()

    # def configure_twevents_columns(self):
    #    """
    #    configure the visible columns of twEvent tablewidget
    #    configuration for playerType is recorded in self.config_param[f"{self.playerType} tw fields"]
    #    """

    #    dlg = dialog.Input_dialog(
    #        label_caption="Select the columns to show",
    #        elements_list=[
    #            (
    #                "cb",
    #                x,
    #                # default state
    #                x
    #                in self.config_param.get(
    #                    f"{self.playerType} tw fields",
    #                    cfg.TW_EVENTS_FIELDS[self.playerType],
    #                ),
    #            )
    #            for x in cfg.TW_EVENTS_FIELDS[self.playerType]
    #        ],
    #        title="Select the column to show",
    #    )
    #    if not dlg.exec_():
    #        return

    #    self.config_param[f"{self.playerType} tw fields"] = tuple(
    #        field for field in cfg.TW_EVENTS_FIELDS[self.playerType] if dlg.elements[field].isChecked()
    #    )

    #    self.load_tw_events(self.observationId)

    def configure_tvevents_columns(self):
        """
        configure the visible columns of tv_events tableview
        configuration for playerType is recorded in self.config_param[f"{self.playerType} tw fields"]
        """
        QMessageBox.information(
            None,
            cfg.programName,
            ("This function is not yet implemented"),
            QMessageBox.Ok | QMessageBox.Default,
            QMessageBox.NoButton,
        )

        return
        # TODO: implement
        dlg = dialog.Input_dialog(
            label_caption="Select the columns to show",
            elements_list=[
                (
                    "cb",
                    x,
                    # default state
                    x
                    in self.config_param.get(
                        f"{self.playerType} tw fields",
                        cfg.TW_EVENTS_FIELDS[self.playerType],
                    ),
                )
                for x in cfg.TW_EVENTS_FIELDS[self.playerType]
            ],
            title="Select the column to show",
        )
        if not dlg.exec_():
            return

        self.config_param[f"{self.playerType} tw fields"] = tuple(
            field for field in cfg.TW_EVENTS_FIELDS[self.playerType] if dlg.elements[field].isChecked()
        )

        self.load_tw_events(self.observationId)

    def populate_tv_events(self, obs_id: str, header: list, time_format: str, behaviors_filter=tuple(), subjects_filter=tuple()) -> None:
        """
        populate table view with events
        """
        model = self.tv_events.model()
        if model is not None:
            self.tv_events.setModel(None)
            model.deleteLater()

        # add behavior type (POINT, START, STOP)
        mem_behav: dict = {}
        state_events_list = util.state_behavior_codes(self.pj[cfg.ETHOGRAM])

        state = [""] * len(self.pj[cfg.OBSERVATIONS][obs_id][cfg.EVENTS])

        for idx, row in enumerate(self.pj[cfg.OBSERVATIONS][obs_id][cfg.EVENTS]):
            code = row[cfg.PJ_OBS_FIELDS[self.playerType][cfg.BEHAVIOR_CODE]]

            # check if code is state
            if code in state_events_list:
                subject = row[cfg.PJ_OBS_FIELDS[self.playerType][cfg.SUBJECT]]
                modifier = row[cfg.PJ_OBS_FIELDS[self.playerType][cfg.MODIFIER]]

                if f"{subject}|{code}|{modifier}" in mem_behav and mem_behav[f"{subject}|{code}|{modifier}"]:
                    state[idx] = cfg.STOP
                else:
                    state[idx] = cfg.START

                if f"{subject}|{code}|{modifier}" in mem_behav:
                    mem_behav[f"{subject}|{code}|{modifier}"] = not mem_behav[f"{subject}|{code}|{modifier}"]
                else:
                    mem_behav[f"{subject}|{code}|{modifier}"] = 1

        self.event_state: list = []
        self.tv_idx2events_idx: list = []
        for idx, row in enumerate(self.pj[cfg.OBSERVATIONS][obs_id][cfg.EVENTS]):
            # filter
            if subjects_filter and row[cfg.PJ_OBS_FIELDS[self.playerType][cfg.SUBJECT]] not in subjects_filter:
                continue
            if behaviors_filter and row[cfg.PJ_OBS_FIELDS[self.playerType][cfg.BEHAVIOR_CODE]] not in behaviors_filter:
                continue

            if self.playerType in (cfg.MEDIA, cfg.VIEWER_MEDIA) and len(row) == 5:
                # add frame index if not present
                self.event_state.append(row[:] + [dec("NaN")] + [state[idx]])
            else:
                self.event_state.append(row[:] + [state[idx]])
            self.tv_idx2events_idx.append(idx)

        self.tv_events.setSortingEnabled(False)
        model = TableModel(
            self.event_state,
            header,
            time_format,
            self.playerType,
            self.tv_events,
        )
        self.tv_events.setModel(model)

        # column width
        # https://doc.qt.io/qtforpython-5/PySide2/QtWidgets/QHeaderView.html#more
        self.tv_events.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)

        # self.table.setSortingEnabled(True)
        # self.table.sortByColumn(0, Qt.AscendingOrder)

    def load_tw_events(self, obs_id):
        """
        load events in table view and update START/STOP

        if self.filtered_behaviors is populated and event not in self.filtered_behaviors then the event is not shown
        if self.filtered_subjects is populated and event not in self.filtered_subjects then the event is not shown

        Args:
            obsId (str): observation to load
        """

        logging.debug(f"begin load events from obs in tableView: {obs_id}")

        # t1 = time.time()
        self.populate_tv_events(
            obs_id,
            [s.capitalize() for s in cfg.TW_EVENTS_FIELDS[self.playerType]],
            self.timeFormat,
            self.filtered_behaviors,
            self.filtered_subjects,
        )

        # print("load table view:", time.time() - t1)

        return

        """
        DISABLED tableview component is used
        
        logging.debug(f"begin load events from obs in tablewidget: {obs_id}")

        t1 = time.time()

        self.twEvents.clear()

        self.twEvents.setColumnCount(len(cfg.TW_EVENTS_FIELDS[self.playerType]))
        self.twEvents.setHorizontalHeaderLabels([s.capitalize() for s in cfg.TW_EVENTS_FIELDS[self.playerType]])

        for idx, field in enumerate(cfg.TW_EVENTS_FIELDS[self.playerType]):
            if field not in self.config_param.get(f"{self.playerType} tw fields", cfg.TW_EVENTS_FIELDS[self.playerType]):
                self.twEvents.horizontalHeader().hideSection(idx)
            else:
                self.twEvents.horizontalHeader().showSection(idx)

        self.twEvents.setRowCount(len(self.pj[cfg.OBSERVATIONS][obs_id][cfg.EVENTS]))
        if self.filtered_behaviors or self.filtered_subjects:
            self.twEvents.setRowCount(0)
        row = 0

        for event_idx, event in enumerate(self.pj[cfg.OBSERVATIONS][obs_id][cfg.EVENTS]):
            if self.filtered_behaviors and event[cfg.PJ_OBS_FIELDS[self.playerType][cfg.BEHAVIOR_CODE]] not in self.filtered_behaviors:
                continue

            if self.filtered_subjects and event[cfg.PJ_OBS_FIELDS[self.playerType][cfg.SUBJECT]] not in self.filtered_subjects:
                continue

            if self.filtered_behaviors or self.filtered_subjects:
                self.twEvents.insertRow(self.twEvents.rowCount())

            for field_type in cfg.TW_EVENTS_FIELDS[self.playerType]:
                if field_type in cfg.PJ_EVENTS_FIELDS[self.playerType]:
                    field = event_operations.read_event_field(event, self.playerType, field_type)

                    if field_type == cfg.TIME:
                        item = QTableWidgetItem(str(util.convertTime(self.timeFormat, field)))

                        # add index of project events
                        item.setData(Qt.UserRole, event_idx)
                        self.twEvents.setItem(row, cfg.TW_OBS_FIELD[self.playerType][field_type], item)
                        continue

                    if field_type in (cfg.IMAGE_INDEX, cfg.FRAME_INDEX):
                        field = str(field)

                    self.twEvents.setItem(
                        row,
                        cfg.TW_OBS_FIELD[self.playerType][field_type],
                        QTableWidgetItem(field),
                    )

                else:
                    self.twEvents.setItem(
                        row,
                        cfg.TW_OBS_FIELD[self.playerType][field_type],
                        QTableWidgetItem(""),
                    )

            row += 1

        self.update_events_start_stop()

        print("load twevent:", time.time() - t1)

        logging.debug("end load events from obs")
        """

    def close_tool_windows(self):
        """
        close tool windows:
            spectrogram
            measurements
            coding pad
            video_equalizer
        """

        logging.debug("function: close_tool_windows")
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
                if self.pj[cfg.OBSERVATIONS][obs_id][cfg.OBSERVATION_TIME_INTERVAL] != [
                    0,
                    0,
                ]:
                    if self.timeFormat == cfg.HHMMSS:
                        start_time = util.seconds2time(self.pj[cfg.OBSERVATIONS][obs_id][cfg.OBSERVATION_TIME_INTERVAL][0])
                        stop_time = util.seconds2time(self.pj[cfg.OBSERVATIONS][obs_id][cfg.OBSERVATION_TIME_INTERVAL][1])
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
        all_events = [self.pj[cfg.OBSERVATIONS][x][cfg.EVENTS] for x in self.pj[cfg.OBSERVATIONS] if x in selected_observations]

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

        Args:
            mode (str): current or list
        """

        if mode == "list":
            _, selected_observations = select_observations.select_observations2(
                self,
                cfg.MULTIPLE,
                windows_title="Select observations for plotting events",
            )

            if not selected_observations:
                return

        if mode == "current":
            if self.observationId:
                selected_observations = [self.observationId]
            else:
                return

        # check if coded behaviors are defined in ethogram
        if project_functions.check_coded_behaviors_in_obs_list(self.pj, selected_observations):
            return

        # check if state events are paired
        not_ok, selected_observations = project_functions.check_state_events(self.pj, selected_observations)
        if not_ok or not selected_observations:
            return

        (max_obs_length, _) = observation_operations.observation_length(self.pj, selected_observations)
        if max_obs_length == dec(-1):  # media length not available, user choose to not use events
            return

        # exit with message if events do not have timestamp
        if max_obs_length.is_nan():
            QMessageBox.critical(
                None,
                cfg.programName,
                ("This function is not available for observations with events that do not have timestamp"),
                QMessageBox.Ok | QMessageBox.Default,
                QMessageBox.NoButton,
            )
            return

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
                self,
                "Select the file format",
                "Available formats",
                ["PNG", "SVG", "PDF", "EPS", "PS"],
                0,
                False,
            )
            if ok and item:
                file_format = item.lower()
            else:
                return
        start_coding, end_coding, _ = observation_operations.coding_time(self.pj[cfg.OBSERVATIONS], selected_observations)

        parameters = select_subj_behav.choose_obs_subj_behav_category(
            self,
            selected_observations,
            start_coding=start_coding,
            end_coding=end_coding,
            maxTime=max_obs_length,
            flagShowExcludeBehaviorsWoEvents=True,
            by_category=False,
            n_observations=len(selected_observations),
        )
        if parameters == {}:
            return

        if not parameters[cfg.SELECTED_SUBJECTS] or not parameters[cfg.SELECTED_BEHAVIORS]:
            QMessageBox.warning(self, cfg.programName, "Select subject(s) and behavior(s) to plot")
            return

        plot_events.create_events_plot(
            self,
            selected_observations,
            parameters,
            plot_colors=self.plot_colors,
            plot_directory=plot_directory,
            file_format=file_format,
        )

    def behaviors_bar_plot(self, mode: str = "list"):
        """
        plot time budget (bar plot)

        Args:
            mode (str): current or list

        """
        if mode == "list":
            _, selected_observations = select_observations.select_observations2(
                self,
                cfg.MULTIPLE,
                windows_title="Select observation(s) for time budget bar plot",
            )

            if not selected_observations:
                return

        if mode == "current":
            if self.observationId:
                selected_observations = [self.observationId]
            else:
                return

        # check if coded behaviors are defined in ethogram
        if project_functions.check_coded_behaviors_in_obs_list(self.pj, selected_observations):
            return

        # check if state events are paired
        not_ok, selected_observations = project_functions.check_state_events(self.pj, selected_observations)
        if not_ok or not selected_observations:
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

        (
            max_obs_length,
            selectedObsTotalMediaLength,
        ) = observation_operations.observation_length(self.pj, selected_observations)

        if max_obs_length == dec(-1):  # media length not available, user choose to not use events
            QMessageBox.warning(
                None,
                cfg.programName,
                ("The duration of one or more observation is not available"),
                QMessageBox.Ok | QMessageBox.Default,
                QMessageBox.NoButton,
            )
            return

        logging.debug(f"max_obs_length: {max_obs_length}, selectedObsTotalMediaLength: {selectedObsTotalMediaLength}")

        # exit with message if events do not have timestamp
        if max_obs_length.is_nan():
            QMessageBox.critical(
                None,
                cfg.programName,
                ("This function is not available for observations with events that do not have timestamp"),
                QMessageBox.Ok | QMessageBox.Default,
                QMessageBox.NoButton,
            )
            return

        start_coding, end_coding, _ = observation_operations.coding_time(self.pj[cfg.OBSERVATIONS], selected_observations)

        parameters = select_subj_behav.choose_obs_subj_behav_category(
            self,
            selected_observations,
            start_coding=start_coding,
            end_coding=end_coding,
            maxTime=max_obs_length if len(selected_observations) > 1 else selectedObsTotalMediaLength,
            flagShowIncludeModifiers=False,
            flagShowExcludeBehaviorsWoEvents=True,
            n_observations=len(selected_observations),
        )

        if parameters == {}:
            return

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
                self,
                "Select the file format",
                "Available formats",
                ["PNG", "SVG", "PDF", "EPS", "PS"],
                0,
                False,
            )
            if ok and item:
                output_format = item.lower()
            else:
                return

        r = plot_events.create_behaviors_bar_plot(
            self.pj,
            selected_observations,
            parameters,
            plot_directory,
            output_format,
            plot_colors=self.plot_colors,
        )
        if "error" in r:
            QMessageBox.warning(self, cfg.programName, r.get("message", "Error on time budget bar plot"))

    def load_project(self, project_path: str, project_changed, pj: dict):
        """
        load project from pj dict

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
                cfg.programName,
                "What to do about the current unsaved project?",
                [cfg.SAVE, cfg.DISCARD, cfg.CANCEL],
            )

            if response == cfg.SAVE:
                if self.save_project_activated() == "not saved":
                    return

            if response == cfg.CANCEL:
                return

        if action.text() == "Open project":
            fn = QFileDialog().getOpenFileName(
                self,
                "Open project",
                "",
                ("Project files (*.boris *.boris.gz);;" "All files (*)"),
            )
            file_name = fn[0] if type(fn) is tuple else fn

        else:  # recent project
            file_name = action.text()

        if not file_name:
            return

        (
            project_path,
            project_changed,
            pj,
            msg,
        ) = project_functions.open_project_json(file_name)

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
                        for modifier_set in pj[cfg.ETHOGRAM][idx][cfg.MODIFIERS]:
                            try:
                                for idx2, value in enumerate(pj[cfg.ETHOGRAM][idx][cfg.MODIFIERS][modifier_set]["values"]):
                                    if re.findall(r"\((\w+)\)", value):
                                        pj[cfg.ETHOGRAM][idx][cfg.MODIFIERS][modifier_set]["values"][idx2] = (
                                            value.split("(")[0]
                                            + "("
                                            + re.findall(r"\((\w+)\)", value)[0].lower()
                                            + ")"
                                            + value.split(")")[-1]
                                        )
                            except Exception:
                                logging.warning("error during convertion of modifier short cut to lower case")

                    for idx in pj[cfg.SUBJECTS]:
                        pj[cfg.SUBJECTS][idx]["key"] = pj[cfg.SUBJECTS][idx]["key"].lower()

            self.load_project(project_path, project_changed, pj)
            del pj

    def import_project_from_observer_template(self):
        """
        import a project from a Noldus Observer (OTX/OTB or ODX)
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
                cfg.programName,
                "What to do about the current unsaved project?",
                [cfg.SAVE, cfg.DISCARD, cfg.CANCEL],
            )

            if response == cfg.SAVE:
                if self.save_project_activated() == "not saved":
                    return

            if response == cfg.CANCEL:
                return

        fn = QFileDialog().getOpenFileName(
            self,
            "Import project from Noldus The Observer",
            "",
            "Noldus Observer files (*.otx *.otb *.odx);;All files (*)",
        )
        file_name = fn[0] if type(fn) is tuple else fn

        if not file_name:
            return
        pj, error_list = otx_parser.otx_to_boris(file_name)
        if error_list or "fatal" in pj:
            self.results = dialog.Results_dialog()
            self.results.setWindowTitle("Import project from Noldus the Observer XT")
            self.results.ptText.clear()
            self.results.ptText.appendHtml("<br>".join(error_list))
            self.results.show()

        if "fatal" in pj:
            return
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
                cfg.programName,
                "What to do about the current unsaved project?",
                [cfg.SAVE, cfg.DISCARD, cfg.CANCEL],
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
            for w in (self.twEthogram, self.twSubjects):
                w.setRowCount(0)

        newProjectWindow = project.projectDialog()

        # pass copy of self.pj
        newProjectWindow.pj = dict(self.pj)

        # pass config_param
        newProjectWindow.config_param = dict(self.config_param)

        gui_utilities.restore_geometry(newProjectWindow, "project window", (800, 400))

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

            newProjectWindow.lb_project_format_version.setText(f"Project format version: {newProjectWindow.pj[cfg.PROJECT_VERSION]}")

            if newProjectWindow.pj[cfg.PROJECT_DESCRIPTION]:
                newProjectWindow.teDescription.setPlainText(newProjectWindow.pj[cfg.PROJECT_DESCRIPTION])

            if newProjectWindow.pj[cfg.PROJECT_DATE]:
                newProjectWindow.dteDate.setDateTime(QDateTime.fromString(newProjectWindow.pj[cfg.PROJECT_DATE], "yyyy-MM-ddThh:mm:ss"))
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
                            if field == cfg.MODIFIERS:
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
                        if field in (
                            cfg.TYPE,
                            "category",
                            "excluded",
                            "coding map",
                            cfg.MODIFIERS,
                        ):
                            item.setFlags(Qt.ItemIsEnabled)
                            item.setBackground(QColor(230, 230, 230))
                        if field == cfg.COLOR:
                            item.setFlags(Qt.ItemIsEnabled)
                            if QColor(newProjectWindow.pj[cfg.ETHOGRAM][i].get(field, "")).isValid():
                                item.setBackground(QColor(newProjectWindow.pj[cfg.ETHOGRAM][i][field]))
                            else:
                                item.setBackground(QColor(230, 230, 230))

                        newProjectWindow.twBehaviors.setItem(
                            newProjectWindow.twBehaviors.rowCount() - 1,
                            cfg.behavioursFields[field],
                            item,
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
                        newProjectWindow.twBehavCodingMap.rowCount() - 1,
                        0,
                        QTableWidgetItem(bcm["name"]),
                    )
                    codes = ", ".join([bcm["areas"][idx]["code"] for idx in bcm["areas"]])
                    newProjectWindow.twBehavCodingMap.setItem(
                        newProjectWindow.twBehavCodingMap.rowCount() - 1,
                        1,
                        QTableWidgetItem(codes),
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
                self.project_changed()

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
                self.load_behaviors_in_twEthogram([self.pj[cfg.ETHOGRAM][x][cfg.BEHAVIOR_CODE] for x in self.pj[cfg.ETHOGRAM]])
                # subjects
                self.load_subjects_in_twSubjects([self.pj[cfg.SUBJECTS][x][cfg.SUBJECT_NAME] for x in self.pj[cfg.SUBJECTS]])

            self.clear_interface()

            menu_options.update_menu(self)

        gui_utilities.save_geometry(newProjectWindow, "project window")

        del newProjectWindow

    def save_project_json(self, projectFileName: str) -> int:
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
            logging.warning("Function save_project_json already launched")
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

        # project file indentation
        file_indentation = self.config_param.get(cfg.PROJECT_FILE_INDENTATION, cfg.PROJECT_FILE_INDENTATION_DEFAULT_VALUE)
        try:
            if projectFileName.endswith(".boris.gz"):
                with gzip.open(projectFileName, mode="wt", encoding="utf-8") as f_out:
                    f_out.write(
                        json.dumps(
                            self.pj,
                            default=util.decimal_default,
                            indent=file_indentation,
                        )
                    )
            else:  # .boris and other extensions
                with open(projectFileName, "w") as f_out:
                    f_out.write(
                        json.dumps(
                            self.pj,
                            default=util.decimal_default,
                            indent=file_indentation,
                        )
                    )

            self.projectChanged = False
            menu_options.update_windows_title(self)
            self.save_project_json_started = False

            logging.debug("end save_project_json function")
            return 0

        except PermissionError:
            QMessageBox.critical(
                None,
                cfg.programName,
                "Permission denied to save the project file. Try another directory",
                QMessageBox.Ok | QMessageBox.Default,
                QMessageBox.NoButton,
            )
            self.save_project_json_started = False
            return 1

        except OSError:
            _, value, _ = sys.exc_info()
            QMessageBox.critical(None, cfg.programName, f"Error saving the project file: {value}", QMessageBox.Ok)
            self.save_project_json_started = False
            return 4

        except Exception:
            _, value, _ = sys.exc_info()
            QMessageBox.critical(None, cfg.programName, f"Error saving the project file: {value}", QMessageBox.Ok)
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
            if filtr == "Compressed project files (*.boris.gz)" and os.path.splitext(project_new_file_name)[1] != ".boris.gz":
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
                # update windows title
                menu_options.update_windows_title(self)
            else:
                return "Not saved"

    def save_project_activated(self):
        """
        save current project
        """
        logging.debug("function: save project activated")
        logging.debug(f"Project file name: {self.projectFileName}")

        if not self.projectFileName:
            if not self.pj[cfg.PROJECT_NAME]:
                txt = "NONAME.boris"
            else:
                txt = self.pj[cfg.PROJECT_NAME] + ".boris"
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
            if filtr == "Compressed project files (*.boris.gz)" and os.path.splitext(self.projectFileName)[1] != ".boris.gz":
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
            current_time = dec(time.time())
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
        self.lbCurrentStates.setText(f"Observed behaviors: {', '.join(self.currentStates[idx])}")
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
            if current_time >= self.pj[cfg.OBSERVATIONS][self.observationId].get(cfg.OBSERVATION_TIME_INTERVAL, [0, 0])[1]:
                self.beep("beep")
                self.liveTimer.stop()
                self.liveObservationStarted = False
                self.pb_live_obs.setText("Live observation finished")

    def start_live_observation(self):
        """
        activate the live observation mode
        """

        if "scan sampling" in self.pb_live_obs.text():
            self.pb_live_obs.setText("Stop live observation")
            self.liveTimer.start(50)
            return

        if self.liveObservationStarted:
            # stop live obs
            self.pb_live_obs.setText("Start live observation")

            self.liveTimer.stop()

            self.liveStartTime = None

            if self.timeFormat == cfg.HHMMSS:
                if self.pj[cfg.OBSERVATIONS][self.observationId].get(cfg.START_FROM_CURRENT_TIME, False):
                    self.lb_current_media_time.setText(datetime.datetime.now().isoformat(" ").split(" ")[1][:12])
                elif self.pj[cfg.OBSERVATIONS][self.observationId].get(cfg.START_FROM_CURRENT_EPOCH_TIME, False):
                    self.lb_current_media_time.setText(
                        datetime.datetime.fromtimestamp(time.time()).isoformat(sep=" ", timespec="milliseconds")
                    )
                else:
                    self.lb_current_media_time.setText("00:00:00.000")

            if self.timeFormat == cfg.S:
                self.lb_current_media_time.setText("0.000")

        else:
            if self.pj[cfg.OBSERVATIONS][self.observationId][cfg.EVENTS]:
                if dialog.MessageDialog(cfg.programName, "Delete the current events?", (cfg.YES, cfg.NO)) == cfg.YES:
                    self.pj[cfg.OBSERVATIONS][self.observationId][cfg.EVENTS] = []
                self.project_changed()
                self.load_tw_events(self.observationId)

            self.pb_live_obs.setText("Stop live observation")

            self.liveStartTime = QTime()
            # set to now
            self.liveStartTime.start()
            # start timer
            self.liveTimer.start(50)

        self.liveObservationStarted = not self.liveObservationStarted

    def create_subtitles(self):
        """
        create subtitles for selected observations, subjects and behaviors
        """

        _, selected_observations = select_observations.select_observations2(
            self,
            cfg.MULTIPLE,
            windows_title="Select observations for creating subtitles",
        )

        if not selected_observations:
            return

        # remove observations that are not from media file or live
        selected_observations = [
            obs_id for obs_id in selected_observations if self.pj[cfg.OBSERVATIONS][obs_id][cfg.TYPE] in (cfg.LIVE, cfg.MEDIA)
        ]

        if not selected_observations:
            QMessageBox.warning(
                None,
                cfg.programName,
                "This function requires observations from media file(s)",
            )
            return

        # check if state events are paired
        not_ok, selected_observations = project_functions.check_state_events(self.pj, selected_observations)
        if not_ok or not selected_observations:
            return

        max_media_duration_all_obs, _ = observation_operations.media_duration(self.pj[cfg.OBSERVATIONS], selected_observations)

        start_coding, end_coding, _ = observation_operations.coding_time(self.pj[cfg.OBSERVATIONS], selected_observations)

        if start_coding.is_nan():
            QMessageBox.critical(
                None,
                cfg.programName,
                ("This function is not available for observations with events that do not have timestamp"),
                QMessageBox.Ok | QMessageBox.Default,
                QMessageBox.NoButton,
            )
            return

        parameters = select_subj_behav.choose_obs_subj_behav_category(
            self,
            selected_observations,
            start_coding=start_coding,
            end_coding=end_coding,
            maxTime=max_media_duration_all_obs,
            flagShowIncludeModifiers=False,
            flagShowExcludeBehaviorsWoEvents=False,
            n_observations=len(selected_observations),
        )
        if parameters == {}:
            return

        if not parameters[cfg.SELECTED_SUBJECTS] or not parameters[cfg.SELECTED_BEHAVIORS]:
            QMessageBox.warning(
                None,
                cfg.programName,
                "Select subject(s) and behavior(s) to include in subtitles",
            )
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

    def next_frame(self) -> None:
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
                if self.geometric_measurements_mode:
                    self.extract_frame(dw)

                self.plot_timer_out()
                for idx in self.plot_data:
                    self.timer_plot_data_out(self.plot_data[idx])

        if self.geometric_measurements_mode:
            geometric_measurement.redraw_measurements(self)

            self.actionPlay.setIcon(QIcon(":/play"))

    def previous_frame(self) -> None:
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
                if self.geometric_measurements_mode:
                    self.extract_frame(dw)

                self.plot_timer_out()
                for idx in self.plot_data:
                    self.timer_plot_data_out(self.plot_data[idx])

        if self.geometric_measurements_mode:
            geometric_measurement.redraw_measurements(self)

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

            # MEDIA
            if self.pj[cfg.OBSERVATIONS][self.observationId][cfg.TYPE] == cfg.MEDIA:
                event[cfg.FRAME_INDEX] = self.get_frame_index()

            write_event.write_event(self, event, self.getLaps())

    def get_frame_index(self, player_idx: int = 0) -> Union[int, str]:
        """
        returns frame index for player player_idx
        """
        estimated_frame_number = self.dw_player[player_idx].player.estimated_frame_number
        if estimated_frame_number is not None:
            return estimated_frame_number
        else:
            return cfg.NA

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
            QDesktopServices.openUrl(QUrl("https://www.boris.unito.it/user_guide"))

    def click_signal_from_behaviors_coding_map(self, bcm_name, behavior_codes_list: list):
        """
        handle click signal from BehaviorsCodingMapWindowClass widget
        """

        for code in behavior_codes_list:
            try:
                behavior_idx = [key for key in self.pj[cfg.ETHOGRAM] if self.pj[cfg.ETHOGRAM][key][cfg.BEHAVIOR_CODE] == code][0]
            except Exception:
                QMessageBox.critical(
                    self,
                    cfg.programName,
                    f"The code <b>{code}</b> of behavior coding map does not exist in ethogram.",
                )
                return

            event = self.full_event(behavior_idx)

            # IMAGES
            if self.pj[cfg.OBSERVATIONS][self.observationId][cfg.TYPE] == cfg.IMAGES:
                event[cfg.IMAGE_INDEX] = self.image_idx + 1
                event[cfg.IMAGE_PATH] = self.images_list[self.image_idx]

            # MEDIA
            if self.pj[cfg.OBSERVATIONS][self.observationId][cfg.TYPE] == cfg.MEDIA:
                event[cfg.FRAME_INDEX] = self.get_frame_index()

            write_event.write_event(self.event, self.getLaps())

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

        if self.pj[cfg.OBSERVATIONS][self.observationId][cfg.TYPE] == cfg.MEDIA:
            self.user_move_slider = True
            slider_position = self.video_slider.value() / (cfg.SLIDER_MAXIMUM - 1)
            if self.dw_player[0].player.duration is None:
                return
            video_position = slider_position * self.dw_player[0].player.duration
            self.dw_player[0].player.command("seek", str(video_position), "absolute")

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
        paint tv_events with tracking cursor (red triangle)
        scroll to corresponding event
        """

        # logging.debug("get_events_current_row")

        if not self.pj[cfg.OBSERVATIONS][self.observationId][cfg.EVENTS]:
            return
        ct = self.getLaps()

        if ct.is_nan():
            self.events_current_row = -1
            return

        # check if NaN in time column for observation from images
        if self.pj[cfg.OBSERVATIONS][self.observationId][cfg.TYPE] == cfg.IMAGES:
            for event in self.pj[cfg.OBSERVATIONS][self.observationId][cfg.EVENTS]:
                if event[0].is_nan():
                    return

        # add time offset if any
        ct += dec(self.pj[cfg.OBSERVATIONS][self.observationId][cfg.TIME_OFFSET])

        if ct >= self.pj[cfg.OBSERVATIONS][self.observationId][cfg.EVENTS][-1][cfg.TW_OBS_FIELD[self.playerType][cfg.TIME]]:
            self.events_current_row = len(self.pj[cfg.OBSERVATIONS][self.observationId][cfg.EVENTS])

            self.tv_events.scrollToBottom()
            self.tv_events.setItemDelegate(events_cursor.StyledItemDelegateTriangle(len(self.tv_idx2events_idx)))

            return
        else:
            cr_list = [
                idx
                for idx, x in enumerate(self.pj[cfg.OBSERVATIONS][self.observationId][cfg.EVENTS][:-1])
                if x[0] <= ct
                and self.pj[cfg.OBSERVATIONS][self.observationId][cfg.EVENTS][idx + 1][cfg.TW_OBS_FIELD[self.playerType][cfg.TIME]] > ct
            ]

            if cr_list:
                self.events_current_row = cr_list[0]
                if not self.trackingCursorAboveEvent:
                    self.events_current_row += 1
            else:
                self.events_current_row = -1

        # print(f"{self.events_current_row=}")

        # self.twEvents.setItemDelegate(events_cursor.StyledItemDelegateTriangle(self.events_current_row))
        self.tv_events.setItemDelegate(events_cursor.StyledItemDelegateTriangle(self.events_current_row))

        # print(f"{self.twEvents.item(self.events_current_row, 0)=}")

        # if self.twEvents.item(self.events_current_row, 0):
        #    self.twEvents.scrollToItem(
        #        self.twEvents.item(self.events_current_row, 0),
        #        QAbstractItemView.EnsureVisible,
        #    )

        index = self.tv_events.model().index(self.events_current_row, 0)
        self.tv_events.scrollTo(index, QAbstractItemView.EnsureVisible)

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

    def media_player_enabled(self, n_player: int, enable: bool):
        """
        enable or disable video if any and audio if any
        """
        # if video
        # print(f"{n_player=} {enable=}")
        # print(f"{self.dw_player[n_player].player.video_format=}")
        # print(f"{self.dw_player[n_player].player.audio_bitrate=}")

        # self.pj[cfg.OBSERVATIONS][self.observationId][cfg.MEDIA_INFO][cfg.HAS_VIDEO][]
        # if self.dw_player[n_player].player.playlist_pos is not None:
        #    print(self.dw_player[n_player].player.playlist[self.dw_player[n_player].player.playlist_pos]["filename"])

        if self.dw_player[n_player].player.video_format:
            self.dw_player[n_player].stack.setCurrentIndex(1 if not enable else 0)
        # if audio
        if self.dw_player[n_player].player.audio_bitrate:
            self.dw_player[n_player].player.mute = True if not enable else False

    def sync_time(self, n_player: int, new_time: float) -> None:
        """
        synchronize player n_player to time new_time
        if required load the media file corresponding to cumulative time in player

        Args:
            n_player (int): player
            new_time (int): new time in ms
        """

        if self.dw_player[n_player].player.playlist_count == 1:
            if self.pj[cfg.OBSERVATIONS][self.observationId][cfg.MEDIA_INFO][cfg.OFFSET][str(n_player + 1)]:
                if self.pj[cfg.OBSERVATIONS][self.observationId][cfg.MEDIA_INFO][cfg.OFFSET][str(n_player + 1)] > 0:
                    if new_time < self.pj[cfg.OBSERVATIONS][self.observationId][cfg.MEDIA_INFO][cfg.OFFSET][str(n_player + 1)]:
                        # hide video and mute audio if time < offset
                        self.media_player_enabled(n_player, enable=False)
                    else:
                        if new_time - dec(
                            self.pj[cfg.OBSERVATIONS][self.observationId][cfg.MEDIA_INFO][cfg.OFFSET][str(n_player + 1)]
                        ) > sum(self.dw_player[n_player].media_durations):
                            # hide video and mute audio if required time > video time + offset
                            self.media_player_enabled(n_player, enable=False)
                        else:
                            # show video and enable audio
                            self.media_player_enabled(n_player, enable=True)
                            self.seek_mediaplayer(
                                new_time
                                - dec(self.pj[cfg.OBSERVATIONS][self.observationId][cfg.MEDIA_INFO][cfg.OFFSET][str(n_player + 1)]),
                                player=n_player,
                            )

                elif self.pj[cfg.OBSERVATIONS][self.observationId][cfg.MEDIA_INFO][cfg.OFFSET][str(n_player + 1)] < 0:
                    if new_time - dec(self.pj[cfg.OBSERVATIONS][self.observationId][cfg.MEDIA_INFO][cfg.OFFSET][str(n_player + 1)]) > sum(
                        self.dw_player[n_player].media_durations
                    ):
                        # hide video and mute audio if required time > video time + offset
                        self.media_player_enabled(n_player, enable=False)
                    else:
                        self.media_player_enabled(n_player, enable=True)
                        self.seek_mediaplayer(
                            new_time - dec(self.pj[cfg.OBSERVATIONS][self.observationId][cfg.MEDIA_INFO][cfg.OFFSET][str(n_player + 1)]),
                            player=n_player,
                        )

            else:  # no offset
                self.seek_mediaplayer(new_time, player=n_player)

        elif self.dw_player[n_player].player.playlist_count > 1:
            # check if new time is before the end of last video
            """
            TODO: use cumul_media_durations
            if new_time < self.dw_player[n_player].cumul_media_durations[-1]:
                media_idx = self.dw_player[n_player].player.playlist_pos
            """

            if new_time < sum(self.dw_player[n_player].media_durations):
                media_idx = self.dw_player[n_player].player.playlist_pos

                if (
                    sum(self.dw_player[n_player].media_durations[0:media_idx])
                    < new_time
                    < sum(self.dw_player[n_player].media_durations[0 : media_idx + 1])
                ):
                    # in current media
                    logging.debug(f"{n_player + 1} correct media")
                    self.seek_mediaplayer(
                        new_time - sum(self.dw_player[n_player].media_durations[0:media_idx]),
                        player=n_player,
                    )
                else:  # out of current media
                    logging.debug(f"{n_player + 1} not correct media")

                    flag_paused = self.dw_player[n_player].player.pause
                    tot = 0
                    for idx, d in enumerate(self.dw_player[n_player].media_durations):
                        if tot <= new_time < tot + d:
                            self.dw_player[n_player].player.playing_pos = idx
                            if flag_paused:
                                self.dw_player[n_player].player.pause = True
                            self.seek_mediaplayer(
                                new_time - self.dw_player[n_player].media_durations[0:idx],
                                player=n_player,
                            )
                            break
                        tot += d

            else:  # end of media list
                logging.debug(f"{n_player + 1} end of media")
                self.dw_player[n_player].player.playlist_pos = self.dw_player[n_player].player.playlist_count - 1
                self.seek_mediaplayer(self.dw_player[n_player].media_durations[-1], player=n_player)

    def mpv_timer_out(self, value: Union[float, None], scroll_slider=True):
        """
        print the media current position and total length for MPV player
        scroll video slider to video position
        Time offset is NOT added!
        """

        if not self.observationId:
            return

        cumulative_time_pos = self.getLaps()
        # get frame index
        frame_idx = self.get_frame_index()
        # frame_idx = 0

        if value is None:
            current_media_time_pos = 0
        else:
            current_media_time_pos = value

        # observation time interval
        if self.pj[cfg.OBSERVATIONS][self.observationId].get(cfg.OBSERVATION_TIME_INTERVAL, [0, 0])[1]:
            if cumulative_time_pos >= self.pj[cfg.OBSERVATIONS][self.observationId].get(cfg.OBSERVATION_TIME_INTERVAL, [0, 0])[1]:
                if self.is_playing():
                    self.pause_video("End of observation interval reached. Player paused")
                    self.beep("beep")

        # alarm
        if self.beep_every:
            if cumulative_time_pos % (self.beep_every) <= 1:
                self.beep("beep")

        # scan sampling
        if self.pj[cfg.OBSERVATIONS][self.observationId].get(cfg.MEDIA_SCAN_SAMPLING_DURATION, 0):
            while self.media_scan_sampling_mem and (self.media_scan_sampling_mem[-1] > cumulative_time_pos):
                self.media_scan_sampling_mem.pop(-1)

            if int(cumulative_time_pos) % self.pj[cfg.OBSERVATIONS][self.observationId][cfg.MEDIA_SCAN_SAMPLING_DURATION] == 0:
                scan_sampling_step = (
                    int(cumulative_time_pos / self.pj[cfg.OBSERVATIONS][self.observationId][cfg.MEDIA_SCAN_SAMPLING_DURATION])
                    * self.pj[cfg.OBSERVATIONS][self.observationId][cfg.MEDIA_SCAN_SAMPLING_DURATION]
                )

                if scan_sampling_step not in self.media_scan_sampling_mem:
                    self.media_scan_sampling_mem.append(scan_sampling_step)
                    self.media_scan_sampling_mem.sort()

                    self.pause_video(msg=f"Player paused. Scan sampling at {scan_sampling_step} s")

        # highlight current event in tw events and scroll event list
        self.get_events_current_row()

        ct0 = cumulative_time_pos

        if self.dw_player[0].player.time_pos is not None:
            for n_player in range(1, len(self.dw_player)):
                ct = self.getLaps(n_player=n_player)

                # sync players 2..8 if time diff >= 1 s
                if abs(ct0 - (ct + dec(self.pj[cfg.OBSERVATIONS][self.observationId][cfg.MEDIA_INFO][cfg.OFFSET][str(n_player + 1)]))) >= 1:
                    self.sync_time(n_player, ct0)  # self.seek_mediaplayer(ct0, n_player)

        currentTimeOffset = dec(cumulative_time_pos + self.pj[cfg.OBSERVATIONS][self.observationId][cfg.TIME_OFFSET])

        all_media_duration = sum(self.dw_player[0].media_durations) / 1000
        current_media_duration = self.dw_player[0].player.duration  # mediaplayer_length
        self.mediaTotalLength = current_media_duration

        # current state(s)
        self.currentStates: dict = {}

        # index of current subject selected by observer
        subject_idx = self.subject_name_index[self.currentSubject] if self.currentSubject else ""

        # t1 = time.time()
        self.currentStates = util.get_current_states_modifiers_by_subject(
            self.state_behaviors_codes,
            self.pj[cfg.OBSERVATIONS][self.observationId][cfg.EVENTS],
            dict(self.pj[cfg.SUBJECTS], **{"": {"name": ""}}),
            currentTimeOffset,
            include_modifiers=True,
        )
        # print("get_current_states_modifiers_by_subject:", time.time() - t1)

        self.lbCurrentStates.setText(f"Observed behaviors: {', '.join(self.currentStates[subject_idx])}")

        # show current states in subjects table
        self.show_current_states_in_subjects_table()

        # current media name
        if self.dw_player[0].player.playlist_pos is not None:
            current_media_name = pl.Path(self.dw_player[0].player.playlist[self.dw_player[0].player.playlist_pos]["filename"]).name
            current_playlist_index = self.dw_player[0].player.playlist_pos
        else:
            current_media_name = ""
            current_playlist_index = None

        # check for ongoing state events between media or at the end of last media

        if (
            self.pj[cfg.OBSERVATIONS][self.observationId][cfg.CLOSE_BEHAVIORS_BETWEEN_VIDEOS]
            and self.mem_playlist_index is not None
            and current_playlist_index != self.mem_playlist_index
        ):
            min_ = self.dw_player[0].cumul_media_durations_sec[self.dw_player[0].player.playlist_pos - 1]
            max_ = self.dw_player[0].cumul_media_durations_sec[self.dw_player[0].player.playlist_pos]

            events = [event for event in self.pj[cfg.OBSERVATIONS][self.observationId][cfg.EVENTS] if min_ <= event[0] < max_]

            time_to_stop = self.dw_player[0].cumul_media_durations_sec[self.dw_player[0].player.playlist_pos] - dec("0.001")

            events_to_add = project_functions.fix_unpaired_state_events2(self.pj[cfg.ETHOGRAM], events, time_to_stop)

            if events_to_add:
                self.statusbar.showMessage("The media changed. Some ongoing state events were stopped automatically", 0)

                self.pj[cfg.OBSERVATIONS][self.observationId][cfg.EVENTS].extend(events_to_add)
                self.project_changed()
                self.pj[cfg.OBSERVATIONS][self.observationId][cfg.EVENTS].sort()

                self.load_tw_events(self.observationId)

                self.pause_video()

                self.update_visualizations()

        self.mem_media_name = current_media_name
        self.mem_playlist_index = current_playlist_index

        playlist_length = len(self.dw_player[0].player.playlist)

        # update observation info
        msg = ""
        if self.dw_player[0].player.time_pos is not None:  # check if video
            msg = f"Current media name: <b>{current_media_name}</b> (#{self.dw_player[0].player.playlist_pos + 1} / {playlist_length})<br>"

            msg += (
                f"Media position: <b>{util.convertTime(self.timeFormat, current_media_time_pos)}</b> / "
                f"{util.convertTime(self.timeFormat, current_media_duration)} frame: <b>{frame_idx}</b>"
            )

            # with time offset
            if self.pj[cfg.OBSERVATIONS][self.observationId][cfg.TIME_OFFSET]:
                msg += (
                    "<br>Media position with offset: "
                    f"<b>{util.convertTime(self.timeFormat, current_media_time_pos + float(self.pj[cfg.OBSERVATIONS][self.observationId][cfg.TIME_OFFSET]))}</b> / "
                    f"{util.convertTime(self.timeFormat, current_media_duration + float(self.pj[cfg.OBSERVATIONS][self.observationId][cfg.TIME_OFFSET]))}"
                )

            # if many media files
            if self.dw_player[0].player.playlist_count > 1:
                msg += (
                    f"<br>Total: <b>{util.convertTime(self.timeFormat,cumulative_time_pos)} / "
                    f"{util.convertTime(self.timeFormat, all_media_duration)}</b>"
                )

        else:  # player ended
            self.plot_timer.stop()

            # stop all timer for plotting data
            for data_timer in self.ext_data_timer_list:
                data_timer.stop()

            self.actionPlay.setIcon(QIcon(":/play"))

        if msg:
            self.lb_current_media_time.setText(msg)

            # set video scroll bar

            if scroll_slider and not self.user_move_slider:
                self.video_slider.setValue(round(current_media_time_pos / current_media_duration * (cfg.SLIDER_MAXIMUM - 1)))

    def mpv_eof_reached(self):
        """
        mpv file or playlist is at end
        close all started state events if option activated
        """

        logging.info("Media end reached")

        """
        print(f"{self.dw_player[0].player.time_pos=}")
        print(f"{self.dw_player[0].player.pause=}")
        print(f"{self.dw_player[0].player.core_idle=}")
        print(f"{self.dw_player[0].player.eof_reached=}")
        print(f"{self.dw_player[0].player.playlist_pos=}")
        """

        if self.pj[cfg.OBSERVATIONS][self.observationId][cfg.CLOSE_BEHAVIORS_BETWEEN_VIDEOS]:
            if self.dw_player[0].player.eof_reached and self.dw_player[0].player.core_idle:
                if self.dw_player[0].player.playlist_pos == len(self.dw_player[0].player.playlist) - 1:
                    logging.debug("End of playlist reached")

                    self.pause_video()

                    self.lb_player_status.setText("End of playlist reached")

                    """
                    cmd = [round(dec(x / 1000), 3) for x in self.dw_player[0].cumul_media_durations]
                    print(f"{cmd=}")
                    """

                    min_ = self.dw_player[0].cumul_media_durations_sec[self.dw_player[0].player.playlist_pos]
                    """max_ =  self.dw_player[0].cumul_media_durations_sec[self.dw_player[0].player.playlist_pos + 1]"""

                    # print(f"{min_=} ")

                    events = [event for event in self.pj[cfg.OBSERVATIONS][self.observationId][cfg.EVENTS] if min_ <= event[0]]

                    # print(f"{events=}")

                    time_to_stop = self.dw_player[0].cumul_media_durations_sec[-1]

                    events_to_add = project_functions.fix_unpaired_state_events2(self.pj[cfg.ETHOGRAM], events, time_to_stop)

                    # print(f"{events_to_add=}")

                    if events_to_add:
                        self.statusbar.showMessage("The playlist has finished. Some ongoing state events were stopped automatically", 0)

                        self.pj[cfg.OBSERVATIONS][self.observationId][cfg.EVENTS].extend(events_to_add)
                        self.project_changed()
                        self.pj[cfg.OBSERVATIONS][self.observationId][cfg.EVENTS].sort()

                        self.load_tw_events(self.observationId)

                        self.update_visualizations()

    def load_behaviors_in_twEthogram(self, behaviors_to_show: list) -> None:
        """
        fill ethogram table with ethogram from pj
        """

        self.twEthogram.setRowCount(0)
        if self.pj[cfg.ETHOGRAM]:
            for idx in util.sorted_keys(self.pj[cfg.ETHOGRAM]):
                if self.pj[cfg.ETHOGRAM][idx][cfg.BEHAVIOR_CODE] in behaviors_to_show:
                    self.twEthogram.setRowCount(self.twEthogram.rowCount() + 1)
                    for idx_col in cfg.ETHOGRAM_TABLE_COLUMNS:
                        field = cfg.ETHOGRAM_TABLE_COLUMNS[idx_col]
                        if field == cfg.COLOR:
                            item = QTableWidgetItem("")
                            if QColor(self.pj[cfg.ETHOGRAM][idx].get(field, "")).isValid():
                                item.setBackground(QColor(self.pj[cfg.ETHOGRAM][idx].get(field, "")))
                            self.twEthogram.setItem(self.twEthogram.rowCount() - 1, idx_col, item)
                        else:
                            self.twEthogram.setItem(
                                self.twEthogram.rowCount() - 1,
                                idx_col,
                                QTableWidgetItem(str(self.pj[cfg.ETHOGRAM][idx].get(field, ""))),
                            )
        if self.twEthogram.rowCount() < len(self.pj[cfg.ETHOGRAM].keys()):
            self.dwEthogram.setWindowTitle(f"Ethogram (filtered {self.twEthogram.rowCount()}/{len(self.pj[cfg.ETHOGRAM].keys())})")

            if self.observationId:
                self.pj[cfg.OBSERVATIONS][self.observationId]["filtered behaviors"] = behaviors_to_show
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
                            self.twSubjects.rowCount() - 1,
                            idx2,
                            QTableWidgetItem(self.pj[cfg.SUBJECTS][idx][field]),
                        )

                    # add cell for current state(s) after last subject field
                    self.twSubjects.setItem(
                        self.twSubjects.rowCount() - 1,
                        len(cfg.subjectsFields),
                        QTableWidgetItem(""),
                    )

    # def update_events_start_stop(self) -> None:
    #    """
    #    update status start/stop of state events in Events table
    #    take consideration of subject and modifiers
    #    twEvents must be ordered by time asc
    #
    #    does not return value
    #    """
    #    state_events_list = util.state_behavior_codes(self.pj[cfg.ETHOGRAM])
    #    mem_behav: dict = {}
    #    for row in range(self.twEvents.rowCount()):
    #        code = self.twEvents.item(row, cfg.TW_OBS_FIELD[self.playerType][cfg.BEHAVIOR_CODE]).text()
    #        # check if code is state
    #        if code in state_events_list:
    #            subject = self.twEvents.item(row, cfg.TW_OBS_FIELD[self.playerType][cfg.SUBJECT]).text()
    #            modifier = self.twEvents.item(row, cfg.TW_OBS_FIELD[self.playerType][cfg.MODIFIER]).text()
    #            if f"{subject}|{code}|{modifier}" in mem_behav and mem_behav[f"{subject}|{code}|{modifier}"]:
    #                self.twEvents.item(row, cfg.TW_OBS_FIELD[self.playerType][cfg.TYPE]).setText(cfg.STOP)
    #            else:
    #                self.twEvents.item(row, cfg.TW_OBS_FIELD[self.playerType][cfg.TYPE]).setText(cfg.START)
    #            if f"{subject}|{code}|{modifier}" in mem_behav:
    #                mem_behav[f"{subject}|{code}|{modifier}"] = not mem_behav[f"{subject}|{code}|{modifier}"]
    #            else:
    #                mem_behav[f"{subject}|{code}|{modifier}"] = 1

    def checkSameEvent(self, obs_id: str, time: dec, subject: str, code: str) -> bool:
        """
        check if a same event is already in events list (time, subject, code)
        """

        if self.pj[cfg.OBSERVATIONS][obs_id][cfg.TYPE] in (cfg.MEDIA, cfg.LIVE):
            return (time, subject, code) in (
                (
                    x[cfg.PJ_OBS_FIELDS[self.pj[cfg.OBSERVATIONS][obs_id][cfg.TYPE]][cfg.TIME]],
                    x[cfg.PJ_OBS_FIELDS[self.pj[cfg.OBSERVATIONS][obs_id][cfg.TYPE]][cfg.SUBJECT]],
                    x[cfg.PJ_OBS_FIELDS[self.pj[cfg.OBSERVATIONS][obs_id][cfg.TYPE]][cfg.BEHAVIOR_CODE]],
                )
                for x in self.pj[cfg.OBSERVATIONS][obs_id][cfg.EVENTS]
            )

        if self.pj[cfg.OBSERVATIONS][obs_id][cfg.TYPE] == cfg.IMAGES:
            return (time, subject, code) in (
                (
                    x[cfg.PJ_OBS_FIELDS[self.pj[cfg.OBSERVATIONS][obs_id][cfg.TYPE]][cfg.IMAGE_INDEX]],
                    x[cfg.PJ_OBS_FIELDS[self.pj[cfg.OBSERVATIONS][obs_id][cfg.TYPE]][cfg.SUBJECT]],
                    x[cfg.PJ_OBS_FIELDS[self.pj[cfg.OBSERVATIONS][obs_id][cfg.TYPE]][cfg.BEHAVIOR_CODE]],
                )
                for x in self.pj[cfg.OBSERVATIONS][obs_id][cfg.EVENTS]
            )

    def choose_behavior(self, obs_key) -> Union[None, str]:
        """
        fill listwidget with all behaviors coded by key

        Returns:
            index of selected behaviour
        """

        # check if key duplicated
        items: list = []
        code_idx: dict = {}
        for idx in self.pj[cfg.ETHOGRAM]:
            if self.pj[cfg.ETHOGRAM][idx]["key"] == obs_key:
                code_descr = self.pj[cfg.ETHOGRAM][idx][cfg.BEHAVIOR_CODE]
                if self.pj[cfg.ETHOGRAM][idx][cfg.DESCRIPTION]:
                    code_descr += " - " + self.pj[cfg.ETHOGRAM][idx][cfg.DESCRIPTION]
                items.append(code_descr)
                code_idx[code_descr] = idx

        items.sort()

        dbc = dialog.Duplicate_items(
            f"The <b>{obs_key}</b> key codes many behaviors.<br>Choose one:",
            items,
        )
        if dbc.exec_():
            code = dbc.getCode()
            if code:
                return code_idx[code]
            else:
                return None

    def choose_subject(self, subject_key) -> Union[None, str]:
        """
        fill listwidget with all subjects coded by key

        Returns:
            index of selected subject
        """

        # check if key duplicated
        items: list = []
        subject_idx: dict = {}
        for idx in self.pj[cfg.SUBJECTS]:
            if self.pj[cfg.SUBJECTS][idx]["key"] == subject_key:
                subject_descr = self.pj[cfg.SUBJECTS][idx][cfg.SUBJECT_NAME]
                if self.pj[cfg.SUBJECTS][idx][cfg.DESCRIPTION]:
                    subject_descr += " - " + self.pj[cfg.SUBJECTS][idx][cfg.DESCRIPTION]
                items.append(subject_descr)
                subject_idx[subject_descr] = idx

        items.sort()

        dbc = dialog.Duplicate_items(
            f"The <b>{subject_key}</b> key codes many subjects.<br>Choose one:",
            items,
        )
        if dbc.exec_():
            subject = dbc.getCode()
            if subject:
                return subject_idx[subject]
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
            if "Live observation finished" in self.pb_live_obs.text():
                return dec("NaN")
            if self.liveObservationStarted:
                now = QTime()
                now.start()  # current time
                memLaps = dec(str(round(self.liveStartTime.msecsTo(now) / 1000, 3)))
                return memLaps
            else:
                return dec("0")

        if self.pj[cfg.OBSERVATIONS][self.observationId][cfg.TYPE] == cfg.IMAGES:
            if self.playerType == cfg.VIEWER_IMAGES:
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
                mem_laps = sum(self.dw_player[n_player].media_durations[0 : self.dw_player[n_player].player.playlist_pos]) + (
                    0 if self.dw_player[n_player].player.time_pos is None else self.dw_player[n_player].player.time_pos * 1000
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
        # check if coding map for modifiers
        if util.has_coding_map(self.pj[cfg.ETHOGRAM], behavior_idx):
            # pause if media and media playing
            if self.pj[cfg.OBSERVATIONS][self.observationId][cfg.TYPE] == cfg.MEDIA:
                if self.playerType == cfg.MEDIA:
                    if self.is_playing():
                        flag_player_playing = True
                        self.pause_video()

            self.codingMapWindow = modifiers_coding_map.ModifiersCodingMapWindowClass(
                self.pj[cfg.CODING_MAP][self.pj[cfg.ETHOGRAM][behavior_idx]["coding map"]]
            )

            self.codingMapWindow.resize(cfg.CODING_MAP_RESIZE_W, cfg.CODING_MAP_RESIZE_H)

            gui_utilities.restore_geometry(self.codingMapWindow, "coding map window", (600, 400))

            if self.codingMapWindow.exec_():
                event["from map"] = self.codingMapWindow.getCodes()
            else:
                event["from map"] = ""

            gui_utilities.save_geometry(self.codingMapWindow, "coding map window")

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

        if self.playerType != cfg.MEDIA:
            return False
        if self.dw_player[0].player.pause:
            return False
        elif self.dw_player[0].player.time_pos is not None:
            return True
        else:
            return False

    def update_project_zoom_pan_values(self):
        """
        update values of video zoom and video pan in project
        """
        for k in (cfg.ZOOM_LEVEL, cfg.PAN_X, cfg.PAN_Y):
            if k not in self.pj[cfg.OBSERVATIONS][self.observationId][cfg.MEDIA_INFO]:
                self.pj[cfg.OBSERVATIONS][self.observationId][cfg.MEDIA_INFO][k] = {}

        self.pj[cfg.OBSERVATIONS][self.observationId][cfg.MEDIA_INFO][cfg.ZOOM_LEVEL][str(self.current_player + 1)] = (
            2 ** self.dw_player[self.current_player].player.video_zoom
        )
        self.pj[cfg.OBSERVATIONS][self.observationId][cfg.MEDIA_INFO][cfg.PAN_X][str(self.current_player + 1)] = self.dw_player[
            self.current_player
        ].player.video_pan_x
        self.pj[cfg.OBSERVATIONS][self.observationId][cfg.MEDIA_INFO][cfg.PAN_Y][str(self.current_player + 1)] = self.dw_player[
            self.current_player
        ].player.video_pan_y

        self.project_changed()
        video_operations.display_zoom_level(self)

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

        ek, ek_text = event.key(), event.text()

        logging.debug(f"text #{ek_text}#  event key: {ek} Modifier: {modifier}")

        # undo (CTRL + Z)
        if ek == 90 and modifier == cfg.CTRL_KEY:
            event_operations.undo_event_operation(self)
            return

        if ek in (
            Qt.Key_Tab,
            Qt.Key_Shift,
            Qt.Key_Control,
            Qt.Key_Meta,
            Qt.Key_Alt,
            Qt.Key_AltGr,
        ):
            return

        if self.playerType in cfg.VIEWERS:
            if event.key() == Qt.Key_CapsLock:
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

        if self.pj[cfg.OBSERVATIONS][self.observationId][cfg.TYPE] == cfg.MEDIA:
            # speed down
            if ek == Qt.Key_End:
                video_operations.video_slower_activated(self)
                return

            # speed up
            if ek == Qt.Key_Home:
                video_operations.video_faster_activated(self)
                return

            # speed normal
            if ek == Qt.Key_Backspace:
                video_operations.video_normalspeed_activated(self)
                return

            # play / pause with space bar
            if ek == Qt.Key_Space:
                if flagPlayerPlaying:
                    self.pause_video()
                else:
                    self.play_video()
                return

            #  jump backward
            if modifier != cfg.CTRL_KEY and ek == Qt.Key_Down:
                self.jumpBackward_activated()
                return

            # jump forward
            if modifier != cfg.CTRL_KEY and ek == Qt.Key_Up:
                self.jumpForward_activated()
                return

            if modifier == cfg.CTRL_KEY:
                # video zoom
                if ek == 48:  # no zoom Ctrl + 0
                    self.dw_player[self.current_player].player.video_zoom = 0
                    self.dw_player[self.current_player].player.video_pan_x = 0
                    self.dw_player[self.current_player].player.video_pan_y = 0
                zoom_step = 0.1
                if ek == Qt.Key_Plus:  # zoom in with minus key
                    self.dw_player[self.current_player].player.video_zoom += zoom_step
                if ek == Qt.Key_Minus:  # zoom out with plus key
                    self.dw_player[self.current_player].player.video_zoom -= zoom_step

                # video pan
                pan_step = 0.05
                if ek == Qt.Key_Left:
                    self.dw_player[self.current_player].player.video_pan_x -= pan_step
                if ek == Qt.Key_Right:
                    self.dw_player[self.current_player].player.video_pan_x += pan_step
                if ek == Qt.Key_Up:
                    self.dw_player[self.current_player].player.video_pan_y -= pan_step
                if ek == Qt.Key_Down:
                    self.dw_player[self.current_player].player.video_pan_y += pan_step

                if ek in (48, Qt.Key_Plus, Qt.Key_Minus, Qt.Key_Left, Qt.Key_Right, Qt.Key_Up, Qt.Key_Down):
                    self.update_project_zoom_pan_values()

        # frame-by-frame mode
        if ek == 47 or (ek == Qt.Key_Left and modifier != cfg.CTRL_KEY):  # / one frame back
            self.previous_frame()
            return

        if ek == 42 or (ek == Qt.Key_Right and modifier != cfg.CTRL_KEY):  # *  read next frame
            self.next_frame()
            return

        if self.playerType in (cfg.MEDIA, cfg.IMAGES):
            # next media file (page up)
            if ek == Qt.Key_PageUp:
                self.next_media_file()

            # previous media file (page down)
            if ek == Qt.Key_PageDown:
                self.previous_media_file()

        if not self.pj[cfg.ETHOGRAM]:
            QMessageBox.warning(self, cfg.programName, "The ethogram is not configured")
            return

        """ to be removed 2024-01-29
        obs_key = None

        # check if key is function key
        if ek in cfg.function_keys:
            if cfg.function_keys[ek] in [self.pj[cfg.ETHOGRAM][x]["key"] for x in self.pj[cfg.ETHOGRAM]]:
                obs_key = cfg.function_keys[ek]
        """

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
                    memLaps = util.seconds_of_day(datetime.datetime.now())
                elif self.pj[cfg.OBSERVATIONS][self.observationId].get(cfg.START_FROM_CURRENT_EPOCH_TIME, False):
                    memLaps = dec(time.time())
                else:
                    memLaps = self.getLaps()

        if self.pj[cfg.OBSERVATIONS][self.observationId][cfg.TYPE] in (
            cfg.MEDIA,
            cfg.IMAGES,
        ):
            memLaps = self.getLaps()

        if memLaps is None:
            return

        if (
            ((ek in range(33, 256)) and (ek not in [Qt.Key_Plus, Qt.Key_Minus]))
            or (ek in cfg.function_keys)
            or (ek == Qt.Key_Enter and event.text())
        ):  # click from coding pad or subjects pad
            if ek in cfg.function_keys:
                ek_unichr = cfg.function_keys[ek]
            elif ek != Qt.Key_Enter:
                ek_unichr = ek_text
            elif ek == Qt.Key_Enter and event.text():  # click from coding pad or subjects pad
                ek_unichr = ek_text

            logging.debug(f"{ek_unichr = }")

            if ek == Qt.Key_Enter and event.text():  # click from coding pad or subjects pad
                ek_unichr = ""

                if "#subject#" in event.text():
                    for idx in self.pj[cfg.SUBJECTS]:
                        if self.pj[cfg.SUBJECTS][idx][cfg.SUBJECT_NAME] == event.text().replace("#subject#", ""):
                            self.update_subject(self.pj[cfg.SUBJECTS][idx][cfg.SUBJECT_NAME])
                            return

                else:  # behavior
                    for idx in self.pj[cfg.ETHOGRAM]:
                        if self.pj[cfg.ETHOGRAM][idx][cfg.BEHAVIOR_CODE] == event.text():
                            event = self.full_event(idx)

                            if self.playerType == cfg.IMAGES:
                                event[cfg.IMAGE_PATH] = self.images_list[self.image_idx]
                                event[cfg.IMAGE_INDEX] = self.image_idx + 1

                            if self.playerType == cfg.MEDIA:
                                event[cfg.FRAME_INDEX] = self.get_frame_index()

                            write_event.write_event(self, event, memLaps)
                            return

            # count key occurence in subjects
            subject_matching_idx = [idx for idx in self.pj[cfg.SUBJECTS] if ek_unichr == self.pj[cfg.SUBJECTS][idx]["key"]]

            ethogram_matching_idx = [idx for idx in self.pj[cfg.ETHOGRAM] if self.pj[cfg.ETHOGRAM][idx]["key"] == ek_unichr]

            subject_idx = None
            behavior_idx = None

            # select between behavior and subject
            if subject_matching_idx and ethogram_matching_idx:
                r = dialog.MessageDialog(
                    cfg.programName,
                    "This key defines a behavior and a subject. Choose one",
                    ["&Behavior", "&Subject", cfg.CANCEL],
                )
                if r == cfg.CANCEL:
                    return

                if r == "&Subject":
                    ethogram_matching_idx = []

                if r == "&Behavior":
                    subject_matching_idx = []

            if ethogram_matching_idx:
                if len(ethogram_matching_idx) == 1:
                    behavior_idx = ethogram_matching_idx[0]
                else:
                    if self.playerType == cfg.MEDIA:
                        if self.is_playing():
                            flagPlayerPlaying = True
                            self.pause_video()
                    behavior_idx = self.choose_behavior(ek_unichr)
                    if behavior_idx is None:
                        return

            if subject_matching_idx:
                if len(subject_matching_idx) == 1:
                    subject_idx = subject_matching_idx[0]
                else:
                    if self.playerType == cfg.MEDIA:
                        if self.is_playing():
                            flagPlayerPlaying = True
                            self.pause_video()
                    subject_idx = self.choose_subject(ek_unichr)
                    if subject_idx is None:
                        return

            if self.playerType == cfg.MEDIA and flagPlayerPlaying:
                self.play_video()

            if behavior_idx is not None:
                # check if focal subject is defined
                if not self.currentSubject and self.alertNoFocalSubject:
                    if self.pj[cfg.OBSERVATIONS][self.observationId][cfg.TYPE] == cfg.MEDIA:
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

                    if self.pj[cfg.OBSERVATIONS][self.observationId][cfg.TYPE] == cfg.MEDIA and flagPlayerPlaying:
                        self.play_video()

                    if response == cfg.NO:
                        return

                event = self.full_event(behavior_idx)

                if self.playerType == cfg.IMAGES:
                    event[cfg.IMAGE_PATH] = self.images_list[self.image_idx]
                    event[cfg.IMAGE_INDEX] = self.image_idx + 1

                if self.playerType == cfg.MEDIA:
                    event[cfg.FRAME_INDEX] = self.get_frame_index()

                write_event.write_event(self, event, memLaps)

            elif subject_idx is not None:
                self.update_subject(self.pj[cfg.SUBJECTS][subject_idx][cfg.SUBJECT_NAME])

            else:
                logging.debug(f"Key not assigned ({ek_unichr})")
                self.statusbar.showMessage(f"Key not assigned ({ek_unichr})", 5000)

    def tv_events_doubleClicked(self):
        """
        manage a double click on the events table
        """
        if not self.tv_events.selectionModel().selectedIndexes():
            return

        if self.playerType == cfg.MEDIA:
            # get tv_events cell content
            index = self.tv_events.selectionModel().selectedIndexes()[0]
            time_str = index.sibling(index.row(), cfg.TW_OBS_FIELD[self.playerType]["time"]).data()

            time_ = util.time2seconds(time_str) if ":" in time_str else dec(time_str)

            # substract time offset
            time_ -= self.pj[cfg.OBSERVATIONS][self.observationId][cfg.TIME_OFFSET]

            # substract media creation time
            if self.pj[cfg.OBSERVATIONS][self.observationId].get(cfg.MEDIA_CREATION_DATE_AS_OFFSET, False):
                if len(self.dw_player[0].player.playlist) > 1:
                    QMessageBox.information(
                        self,
                        cfg.programName,
                        (
                            "This function is not yet implemented for this type of observation "
                            "(media time creation as offset with many media files)"
                        ),
                    )
                    return
                media_file_name = self.dw_player[0].player.playlist[self.dw_player[0].player.playlist_pos]["filename"]

                time_ -= self.pj[cfg.OBSERVATIONS][self.observationId][cfg.MEDIA_INFO][cfg.MEDIA_CREATION_TIME][media_file_name]

            if time_ + self.repositioningTimeOffset >= 0:
                new_time = time_ + self.repositioningTimeOffset
            else:
                new_time = 0

            self.seek_mediaplayer(new_time)
            self.update_visualizations()

        if self.playerType == cfg.IMAGES:
            index = self.tv_events.selectionModel().selectedIndexes()[0]
            index_str = index.sibling(index.row(), cfg.TW_OBS_FIELD[self.playerType][cfg.IMAGE_INDEX]).data()

            """index_str = self.twEvents.item(row, cfg.TW_OBS_FIELD[self.playerType][cfg.IMAGE_INDEX]).text()"""
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

    def click_signal_find_in_events(self, msg: str):
        """
        find in events when "Find" button of find dialog box is pressed
        """

        if msg == "CLOSE":
            self.find_dialog.close()
            return

        self.find_dialog.lb_message.setText("")

        fields_list: list = []
        if self.find_dialog.cbSubject.isChecked():
            fields_list.append(cfg.PJ_OBS_FIELDS[self.playerType][cfg.SUBJECT])
        if self.find_dialog.cbBehavior.isChecked():
            fields_list.append(cfg.PJ_OBS_FIELDS[self.playerType][cfg.BEHAVIOR_CODE])
        if self.find_dialog.cbModifier.isChecked():
            fields_list.append(cfg.PJ_OBS_FIELDS[self.playerType][cfg.MODIFIER])
        if self.find_dialog.cbComment.isChecked():
            fields_list.append(cfg.PJ_OBS_FIELDS[self.playerType][cfg.COMMENT])
        if not fields_list:
            self.find_dialog.lb_message.setText('<font color="red">No fields selected!</font>')
            return
        if not self.find_dialog.findText.text():
            self.find_dialog.lb_message.setText('<font color="red">Nothing to search!</font>')
            return

        # print(f"{fields_list=}")

        # search in twevents

        # for event_idx in range(self.twEvents.rowCount()):
        #    if event_idx <= self.find_dialog.currentIdx:
        #        continue
        #
        #    if (not self.find_dialog.cbFindInSelectedEvents.isChecked()) or (
        #        self.find_dialog.cbFindInSelectedEvents.isChecked() and event_idx in self.find_dialog.rowsToFind
        #    ):
        #        for idx in fields_list:
        #            if (
        #                self.find_dialog.cb_case_sensitive.isChecked()
        #                and self.find_dialog.findText.text() in self.twEvents.item(event_idx, idx).text()
        #            ) or (
        #                not self.find_dialog.cb_case_sensitive.isChecked()
        #                and self.find_dialog.findText.text().upper() in self.twEvents.item(event_idx, idx).text().upper()
        #            ):
        #                self.find_dialog.currentIdx = event_idx
        #                self.twEvents.scrollToItem(self.twEvents.item(event_idx, 0))
        #                self.twEvents.selectRow(event_idx)
        #                return

        for event_idx, event in enumerate(self.pj[cfg.OBSERVATIONS][self.observationId][cfg.EVENTS]):
            if event_idx <= self.find_dialog.currentIdx:
                continue

            if (not self.find_dialog.cbFindInSelectedEvents.isChecked()) or (
                self.find_dialog.cbFindInSelectedEvents.isChecked() and event_idx in self.find_dialog.rowsToFind
            ):
                print(f"{event=}")

                # search only on filtered events
                if event_idx not in self.tv_idx2events_idx:
                    continue

                for idx in fields_list:
                    print(f"{idx=}")
                    if (self.find_dialog.cb_case_sensitive.isChecked() and self.find_dialog.findText.text() in event[idx]) or (
                        not self.find_dialog.cb_case_sensitive.isChecked()
                        and self.find_dialog.findText.text().upper() in event[idx].upper()
                    ):
                        self.find_dialog.currentIdx = event_idx

                        # self.twEvents.scrollToItem(self.twEvents.item(event_idx, 0))
                        index = self.tv_events.model().index(event_idx, 0)
                        self.tv_events.scrollTo(index, QAbstractItemView.EnsureVisible)
                        self.tv_events.selectRow(event_idx)
                        # self.twEvents.selectRow(event_idx)
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

    def click_signal_find_replace_in_events(self, msg: str):
        """
        find/replace in events when "Find" button of find dialog box is pressed
        """

        if msg == "CANCEL":
            self.find_replace_dialog.close()
            return
        if self.find_replace_dialog.combo_fields.currentIndex() == 0:  # choose a field
            dialog.MessageDialog(cfg.programName, "Choose a field.", ["OK"])
            return

        if not self.find_replace_dialog.findText.text():
            dialog.MessageDialog(cfg.programName, "There is nothing to find.", ["OK"])
            return

        if self.find_replace_dialog.cbFindInSelectedEvents.isChecked() and not len(self.find_replace_dialog.rowsToFind):
            dialog.MessageDialog(cfg.programName, "There are no selected events", [cfg.OK])
            return

        fields_list: list = []
        if self.find_replace_dialog.combo_fields.currentText() == "Subject":
            # check if find and replace contain valid behavior codes
            for bh in (self.find_replace_dialog.findText.text(), self.find_replace_dialog.replaceText.text()):
                if bh not in util.all_subjects(self.pj[cfg.SUBJECTS]):
                    dialog.MessageDialog(cfg.programName, f"<b>{bh}</b> is not a valid subject name", [cfg.OK])
                    return
            fields_list.append(cfg.PJ_OBS_FIELDS[self.playerType][cfg.SUBJECT])

        if self.find_replace_dialog.combo_fields.currentText() == "Behavior":
            # check if find and replace contain valid behavior codes
            for bh in (self.find_replace_dialog.findText.text(), self.find_replace_dialog.replaceText.text()):
                if bh not in util.all_behaviors(self.pj[cfg.ETHOGRAM]):
                    dialog.MessageDialog(cfg.programName, f"<b>{bh}</b> is not a valid behavior code", [cfg.OK])
                    return
            fields_list.append(cfg.PJ_OBS_FIELDS[self.playerType][cfg.BEHAVIOR_CODE])

        if self.find_replace_dialog.combo_fields.currentText() == "Modifiers":
            fields_list.append(cfg.PJ_OBS_FIELDS[self.playerType][cfg.MODIFIER])
        if self.find_replace_dialog.combo_fields.currentText() == "Comment":
            fields_list.append(cfg.PJ_OBS_FIELDS[self.playerType][cfg.COMMENT])

        # if self.find_replace_dialog.cbSubject.isChecked():
        #    fields_list.append(cfg.PJ_OBS_FIELDS[self.playerType][cfg.SUBJECT])
        # if self.find_replace_dialog.cbBehavior.isChecked():
        #    fields_list.append(cfg.PJ_OBS_FIELDS[self.playerType][cfg.BEHAVIOR_CODE])
        # if self.find_replace_dialog.cbModifier.isChecked():
        #    fields_list.append(cfg.PJ_OBS_FIELDS[self.playerType][cfg.MODIFIER])
        # if self.find_replace_dialog.cbComment.isChecked():
        #    fields_list.append(cfg.PJ_OBS_FIELDS[self.playerType][cfg.COMMENT])

        number_replacement: int = 0
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
                self.find_replace_dialog.cbFindInSelectedEvents.isChecked() and event_idx in self.find_replace_dialog.rowsToFind
            ):
                # search only on selected events
                if event_idx not in self.tv_idx2events_idx:
                    continue

                for idx1 in fields_list:
                    if idx1 <= self.find_replace_dialog.currentIdx_idx:
                        continue

                    if (
                        self.find_replace_dialog.cb_case_sensitive.isChecked() and self.find_replace_dialog.findText.text() in event[idx1]
                    ) or (
                        not self.find_replace_dialog.cb_case_sensitive.isChecked()
                        and self.find_replace_dialog.findText.text().upper() in event[idx1].upper()
                    ):
                        number_replacement += 1
                        self.find_replace_dialog.currentIdx = event_idx
                        self.find_replace_dialog.currentIdx_idx = idx1
                        if self.find_replace_dialog.cb_case_sensitive.isChecked():
                            event[idx1] = event[idx1].replace(
                                self.find_replace_dialog.findText.text(),
                                self.find_replace_dialog.replaceText.text(),
                            )
                        if not self.find_replace_dialog.cb_case_sensitive.isChecked():
                            event[idx1] = insensitive_re.sub(self.find_replace_dialog.replaceText.text(), event[idx1])

                        self.pj[cfg.OBSERVATIONS][self.observationId][cfg.EVENTS][event_idx] = event

                        self.load_tw_events(self.observationId)
                        # self.twEvents.scrollToItem(self.twEvents.item(event_idx, 0))
                        # self.twEvents.selectRow(event_idx)

                        index = self.tv_events.model().index(event_idx, 0)
                        self.tv_events.scrollTo(index, QAbstractItemView.EnsureVisible)
                        self.tv_events.selectRow(event_idx)

                        self.project_changed()

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
                    cfg.programName,
                    "BORIS is doing some job. What do you want to do?",
                    ["Wait", "Quit BORIS"],
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
                cfg.programName,
                "What to do about the current unsaved project?",
                [cfg.SAVE, cfg.DISCARD, cfg.CANCEL],
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

            self.statusbar.showMessage("", 0)

            self.plot_timer.start()

            # start all timer for plotting data
            for data_timer in self.ext_data_timer_list:
                data_timer.start()

            self.actionPlay.setIcon(QIcon(":/pause"))
            self.actionPlay.setText("Pause")

            return True

    def pause_video(self, msg: str = "Player paused"):
        """
        pause media
        does not pause media if already paused (to prevent media played again)
        """

        if self.playerType != cfg.MEDIA:
            return

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

        self.lb_player_status.setText(msg)

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

        if self.observationId and self.pj[cfg.OBSERVATIONS][self.observationId][cfg.TYPE] == cfg.MEDIA:
            if not self.is_playing():
                self.play_video()
            else:
                self.pause_video()

    def jumpBackward_activated(self):
        """
        rewind from current position
        """
        if self.playerType == cfg.MEDIA:
            logging.debug("jump backward")

            decrement = self.fast * self.play_rate if self.config_param.get(cfg.ADAPT_FAST_JUMP, cfg.ADAPT_FAST_JUMP_DEFAULT) else self.fast

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

        if self.playerType == cfg.MEDIA:
            increment = self.fast * self.play_rate if self.config_param.get(cfg.ADAPT_FAST_JUMP, cfg.ADAPT_FAST_JUMP_DEFAULT) else self.fast

            logging.info(f"Jump forward for {increment} seconds")

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

        self.plot_timer_out()  # real-time, waveform, spectrogram
        for idx in self.plot_data:
            self.timer_plot_data_out(self.plot_data[idx])

    def reset_activated(self):
        """
        reset video to beginning
        """
        logging.info("Video reset activated")

        if self.playerType == cfg.MEDIA:
            self.pause_video()

            if cfg.OBSERVATION_TIME_INTERVAL in self.pj[cfg.OBSERVATIONS][self.observationId]:
                self.seek_mediaplayer(int(self.pj[cfg.OBSERVATIONS][self.observationId][cfg.OBSERVATION_TIME_INTERVAL][0]))
            else:
                self.seek_mediaplayer(0)

            self.update_visualizations()

        if self.playerType == cfg.IMAGES:
            self.image_idx = 0
            self.extract_frame(self.dw_player[0])


def main():
    # QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)

    app = QApplication(sys.argv)

    locale.setlocale(locale.LC_NUMERIC, "C")

    # splashscreen
    # no splashscreen for Mac because it can mask the first use dialog box

    if (not options.nosplashscreen) and (sys.platform != "darwin"):
        start = time.time()
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

    if window.config_param.get(cfg.DARK_MODE, cfg.DARK_MODE_DEFAULT_VALUE):
        app.setStyleSheet(qdarkstyle.load_stylesheet(qt_api="pyqt5"))

    # open project/start observation on command line

    project_to_open: str = ""
    observation_to_open: str = ""
    if options.project:
        project_to_open = options.project
        # hook for Mac bundle created with pyinstaller
        if sys.platform == "darwin" and "sn_0_" in project_to_open:
            project_to_open = ""

    logging.debug(f"command line arguments: {args}")

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

    window.show()
    window.raise_()

    if observation_to_open and "error" not in pj:
        r = observation_operations.load_observation(window, obs_id=observation_to_open, mode=cfg.OBS_START)
        if r:
            QMessageBox.warning(
                None,
                cfg.programName,
                (f"Error opening observation: <b>{observation_to_open}</b><br>{r.split(':')[1]}"),
                QMessageBox.Ok | QMessageBox.Default,
                QMessageBox.NoButton,
            )

    if not options.nosplashscreen and (sys.platform != "darwin"):
        splash.finish(window)

    return_code = app.exec_()

    del window

    sys.exit(return_code)
