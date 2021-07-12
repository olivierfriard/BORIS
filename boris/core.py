"""
BORIS
Behavioral Observation Research Interactive Software
Copyright 2012-2021 Olivier Friard

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

import hashlib
import json
import logging
import os
import pathlib
import platform
import re
import socket
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
import matplotlib.pyplot as plt
import matplotlib.transforms as mtransforms
import numpy as np
import tablib
from matplotlib import dates
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtMultimedia import QSound
from PyQt5.QtWidgets import *

from boris import behav_coding_map_creator
from boris import behaviors_coding_map
from boris import coding_pad
from boris import db_functions
from boris import dialog
from boris import export_observation
from boris import gui_utilities
from boris import behavior_binary_table
from boris import irr
from boris import map_creator
from boris import measurement_widget
from boris import modifiers_coding_map
from boris import observation
from boris import observations_list
from boris import advanced_event_filtering
from boris import otx_parser
from boris import param_panel
from boris import plot_data_module
from boris import plot_events
from boris import plot_spectrogram_rt
from boris import plot_waveform_rt
from boris import preferences
from boris import project_functions
from boris import qrc_boris
from boris import select_modifiers
from boris import select_observations
from boris import subjects_pad
from boris import time_budget_functions
from boris import transitions
from boris import utilities
from boris import version
from boris.boris_ui import *
from boris.config import *
from boris.edit_event import DlgEditEvent, EditSelectedEvents
from boris.project import *
from boris.time_budget_widget import timeBudgetResults
from boris.utilities import *
from boris import player_dock_widget


__version__ = version.__version__
__version_date__ = version.__version_date__


if platform.python_version() < "3.6":
    logging.critical(f"BORIS requires Python 3.6+! You are using Python v. {platform.python_version()}")
    sys.exit()

if sys.platform == "darwin":  # for MacOS
    os.environ["LC_ALL"] = "en_US.UTF-8"

# check if argument
usage = "usage: %prog [options] [-p PROJECT_PATH] [-o \"OBSERVATION ID\"]"
parser = OptionParser(usage=usage)


'''
parser.add_option("-d", "--debug", action="store", default="", dest="debug",
                  help="one: log to BORIS.log, new: log to new file")
'''
parser.add_option("-d", "--debug", action="store_true", default=False, dest="debug", help="Use debugging mode")
parser.add_option("-v", "--version", action="store_true", default=False, dest="version", help="Print version")
parser.add_option("-n", "--nosplashscreen", action="store_true", default=False, help="No splash screen")
parser.add_option("-p", "--project", action="store", default="", dest="project", help="Project file")
parser.add_option("-o", "--observation", action="store", default="", dest="observation", help="Observation id")

(options, args) = parser.parse_args()

# set logging parameters
if options.debug:
    logging.basicConfig(format="%(asctime)s,%(msecs)d  %(module)s l.%(lineno)d %(levelname)s %(message)s",
                        datefmt="%H:%M:%S",
                        level=logging.DEBUG)
'''
if options.debug in ["one", "new", "stdout"]:
    if options.debug == "new":
        log_file_name = str(pathlib.Path(os.path.expanduser("~"))
                            / f"BORIS_{datetime.datetime.now().replace(microsecond=0).isoformat().replace(':', '-')}.log")
        file_mode = "w"
    if options.debug == "one":
        log_file_name = str(pathlib.Path(os.path.expanduser("~")) / "BORIS.log")
        file_mode = "a"
    if options.debug in ["one", "new"]:
        logging.basicConfig(filename=log_file_name,
                            filemode=file_mode,
                            format="%(asctime)s,%(msecs)d  %(module)s l.%(lineno)d %(levelname)s %(message)s",
                            datefmt="%H:%M:%S",
                            level=logging.DEBUG)
    if options.debug in ["stdout"]:
        logging.basicConfig(format="%(asctime)s,%(msecs)d  %(module)s l.%(lineno)d %(levelname)s %(message)s",
                            datefmt="%H:%M:%S",
                            level=logging.DEBUG)
else:
    logging.basicConfig(format="%(asctime)s,%(msecs)d  %(module)s l.%(lineno)d %(levelname)s %(message)s",
                        datefmt="%H:%M:%S",
                        level=logging.INFO)
'''
if options.version:
    print(f"version {__version__} release date: {__version_date__}")
    sys.exit(0)

logging.debug("BORIS started")
logging.debug(f"BORIS version {__version__} release date: {__version_date__}")
#logging.debug(f"VLC version {vlc.libvlc_get_version().decode('utf-8')}")

current_system = platform.uname()

logging.debug(f"Operating system: {current_system.system} {current_system.release} {current_system.version}")
logging.debug(f"CPU: {current_system.machine} {current_system.processor}")
logging.debug(f"Python {platform.python_version()} ({'64-bit' if sys.maxsize > 2**32 else '32-bit'})")
logging.debug(f"Qt {QT_VERSION_STR} - PyQt{PYQT_VERSION_STR}")

r, memory = utilities.mem_info()
if not r:
    logging.debug((f"Memory (RAM)  Total: {memory.get('total_memory', 'Not available'):.2f} Mb  "
                   f"Free: {memory.get('free_memory', 'Not available'):.2f} Mb")
                 )


video, live = 0, 1


class ProjectServerThread(QThread):
    """
    thread for serving project to BORIS mobile app
    """

    signal = pyqtSignal(dict)

    def __init__(self, message):
        QThread.__init__(self)
        self.message = message

    def __del__(self):
        self.wait()

    def run(self):

        BUFFER_SIZE = 1024

        s = socket.socket()
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.settimeout(1800)

        s.bind((get_ip_address(), 0))
        self.signal.emit({"URL": f"{s.getsockname()[0]}:{s.getsockname()[1]}"})

        s.listen(5)
        while 1:
            try:
                c, addr = s.accept()

                logging.debug(f"Got connection from {addr}")

            except socket.timeout:
                s.close()

                logging.debug("Project server timeout")

                self.signal.emit({"MESSAGE": "Project server timeout"})
                return

            rq = c.recv(BUFFER_SIZE)

            logging.debug(f"request: {rq}")

            if rq == b"get":
                msg = self.message
                while msg:
                    c.send(msg[0:BUFFER_SIZE])
                    msg = msg[BUFFER_SIZE:]
                c.close()

                logging.debug("Project sent")

                self.signal.emit({"MESSAGE": f"Project sent to {addr[0]}"})

            if rq == b"stop":
                c.close()

                logging.debug("server stopped")

                self.signal.emit({"MESSAGE": "The server is now stopped"})
                return

            # receive an observation
            if rq == b"put":
                c.send(b"SEND")
                c.close()
                c2, addr = s.accept()
                rq2 = b""
                while 1:
                    d = c2.recv(BUFFER_SIZE)
                    if d:
                        rq2 += d
                        if rq2.endswith(b"#####"):
                            break
                    else:
                        break
                c2.close()
                self.signal.emit({"RECEIVED": f"{rq2.decode('utf-8')}", "SENDER": addr})


class TempDirCleanerThread(QThread):
    """
    class for cleaning image cache directory with qthread

    The temporary directory is checked every 30 s.
    If the total size of frames files is greater than the limit fixed by user 1/10 of the files is deleted
    """

    def __init__(self, parent=None):
        QThread.__init__(self, parent)
        self.exiting = False
        self.tempdir = ""
        self.ffmpeg_cache_dir_max_size = 0

    def run(self):
        while self.exiting is False:
            boris_frames_total_size = sum(os.path.getsize(self.tempdir + f) for f in os.listdir(self.tempdir)
                                          if "BORIS@" in f and os.path.isfile(self.tempdir + f))
            if boris_frames_total_size > self.ffmpeg_cache_dir_max_size:
                fl = sorted((os.path.getctime(self.tempdir + f), self.tempdir + f) for f in os.listdir(self.tempdir)
                            if "BORIS@" in f and os.path.isfile(self.tempdir + f))
                for ts, f in fl[0:int(len(fl) / 10)]:
                    os.remove(f)
            time.sleep(30)

            logging.debug((f"Cleaning frame cache directory. ffmpeg_cache_dir_max_size: {self.ffmpeg_cache_dir_max_size} "
                           f"boris_frames_total_size: {boris_frames_total_size}"))


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

    # 2020-03-18
    #instance = vlc.Instance()   # "--avcodec-hw=none"

    pj = dict(EMPTY_PROJECT)
    project = False

    processes = []  # list of QProcess processes
    frames_cache = {}
    frames_buffer = QBuffer()
    frames_buffer.open(QIODevice.ReadWrite)

    saved_state = None

    observationId = ""   # current observation id
    timeOffset = 0.0

    confirmSound = False               # if True each keypress will be confirmed by a beep

    spectrogramHeight = 80
    spectrogram_time_interval = SPECTROGRAM_DEFAULT_TIME_INTERVAL
    spectrogram_color_map = SPECTROGRAM_DEFAULT_COLOR_MAP

    frame_bitmap_format = FRAME_DEFAULT_BITMAP_FORMAT

    fbf_cache_size = FRAME_DEFAULT_CACHE_SIZE

    alertNoFocalSubject = False        # if True an alert will show up if no focal subject
    trackingCursorAboveEvent = False   # if True the cursor will appear above the current event in events table
    checkForNewVersion = False         # if True BORIS will check for new version every 15 days

    pause_before_addevent = False      # pause before "Add event" command CTRL + A

    timeFormat = HHMMSS                # 's' or 'hh:mm:ss'
    repositioningTimeOffset = 0
    automaticBackup = 0                # automatic backup interval (0 no backup)

    projectChanged = False
    liveObservationStarted = False

    # data structures for external data plot
    plot_data = {}
    ext_data_timer_list = []

    projectFileName = ""
    mediaTotalLength = None

    beep_every = 0

    plot_colors = BEHAVIORS_PLOT_COLORS

    measurement_w = None
    memPoints = []   # memory of clicked points for measurement tool

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

    projectWindowGeometry = 0   # memorize size of project window

    imageDirectory = ""   # image cache directory

    # FFmpeg
    memx, memy, mem_player = -1, -1, -1

    # path for ffmpeg/ffmpeg.exe program
    ffmpeg_bin = ""
    ffmpeg_cache_dir = ""
    ffmpeg_cache_dir_max_size = 0
    frame_resize = 0

    # dictionary for FPS storing
    fps = 0

    playerType: str = ""   # VLC, LIVE, VIEWER
    playMode = VLC    # player mode can be VLC of FMPEG (for frame-by-frame mode)

    # spectrogram
    chunk_length = 60  # spectrogram chunk length in seconds

    memMedia = ""
    close_the_same_current_event = False
    tcp_port = 0
    cleaningThread = TempDirCleanerThread()
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

        # 2020-03-18
        from boris import vlc

        if vlc.dll is None:
            msg = "This program requires the VLC media player.\nGo to http://www.videolan.org/vlc"
            QMessageBox.critical(None, programName, msg, QMessageBox.Ok | QMessageBox.Default, QMessageBox.NoButton)
            logging.critical(msg)
            sys.exit(1)

        if vlc.libvlc_get_version().decode("utf-8") < VLC_MIN_VERSION:
            msg = (f"The VLC media player seems very old ({vlc.libvlc_get_version()}). "
                "Go to http://www.videolan.org/vlc to update it")
            QMessageBox.critical(None, programName, msg, QMessageBox.Ok | QMessageBox.Default, QMessageBox.NoButton)
            logging.critical(msg)
            sys.exit(2)

        self.instance = vlc.Instance()   # "--avcodec-hw=none"
        self.vlc_paused = vlc.State.Paused
        self.vlc_ended = vlc.State.Ended
        self.vlc_playing = vlc.State.Playing
        self.vlc_NothingSpecial = vlc.State.NothingSpecial
        self.vlc_stopped = vlc.State.Stopped

        super(MainWindow, self).__init__(parent)
        self.setupUi(self)

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

        self.actionFrame_by_frame.setIcon(QIcon(":/frame_mode"))
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

        self.lb_current_media_time.setText("")
        self.lbFocalSubject.setText("")
        self.lbCurrentStates.setText("")

        self.lbFocalSubject.setText(NO_FOCAL_SUBJECT)

        font = QFont()
        font.setPointSize(15)
        self.lb_current_media_time.setFont(font)
        self.lbFocalSubject.setFont(font)
        self.lbCurrentStates.setFont(font)

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

        self.FFmpegGlobalFrame = 0

        self.config_param = INIT_PARAM

        self.menu_options()
        self.connections()
        self.readConfigFile()


    def menu_options(self):
        """
        enable/disable menu option
        """
        logging.debug("menu_options function")

        flag = self.project

        if not self.project:
            pn = ""
        else:
            if self.pj["project_name"]:
                pn = self.pj["project_name"]
            else:
                if self.projectFileName:
                    pn = f"Unnamed project ({self.projectFileName})"
                else:
                    pn = "Unnamed project"

        self.setWindowTitle("{}{}{}".format(self.observationId + " - " * (self.observationId != ""),
                                            pn + (" - " * (pn != "")),
                                            programName))

        # project menu
        for w in [self.actionEdit_project, self.actionSave_project, self.actionSave_project_as, self.actionCheck_project,
                  self.actionClose_project, self.actionSend_project, self.actionNew_observation,
                  self.actionRemove_path_from_media_files, self.action_obs_list,
                  ]:
            w.setEnabled(flag)

        # observations

        # enabled if observations
        for w in [self.actionOpen_observation, self.actionEdit_observation_2, self.actionView_observation,
                  self.actionObservationsList, self.action_obs_list, self.actionExport_observations_list,
                  self.actionCheckStateEvents, self.actionExplore_project, self.actionClose_unpaired_events,
                  self.menuExport_events, self.menuCreate_subtitles_2, self.actionExtract_events_from_media_files,
                  self.actionExtract_frames_from_media_files]:
            w.setEnabled(self.pj[OBSERVATIONS] != {})

        # enabled if observation
        flagObs = self.observationId != ""

        self.actionAdd_event.setEnabled(flagObs)
        self.actionClose_observation.setEnabled(flagObs)
        self.actionLoad_observations_file.setEnabled(flag)

        self.actionExportEvents_2.setEnabled(flag)
        self.actionExport_aggregated_events.setEnabled(flag)

        # self.actionExportEventString.setEnabled(flag)
        self.menuas_behavioural_sequences.setEnabled(flag)
        self.actionExport_events_as_Praat_TextGrid.setEnabled(flag)
        self.actionJWatcher.setEnabled(flag)

        self.actionDelete_all_observations.setEnabled(flagObs)
        self.actionSelect_observations.setEnabled(flagObs)
        self.actionDelete_selected_observations.setEnabled(flagObs)
        self.actionEdit_event.setEnabled(flagObs)
        self.actionEdit_selected_events.setEnabled(flagObs)
        self.actionEdit_event_time.setEnabled(flagObs)
        self.actionCopy_events.setEnabled(flagObs)
        self.actionPaste_events.setEnabled(flagObs)

        self.actionFind_events.setEnabled(flagObs)
        self.actionFind_replace_events.setEnabled(flagObs)

        self.actionCheckStateEventsSingleObs.setEnabled(flag)
        self.actionRunEventOutside.setEnabled(flag)

        self.actionMedia_file_information.setEnabled(flagObs)
        self.actionMedia_file_information.setEnabled(self.playerType == VLC)

        self.actionJumpForward.setEnabled(self.playerType == VLC)
        self.actionJumpBackward.setEnabled(self.playerType == VLC)
        self.actionJumpTo.setEnabled(self.playerType == VLC)

        if sys.platform == "darwin":
            self.menuZoom1.setEnabled(False)
            self.menuZoom2.setEnabled(False)
        else:
            self.menuZoom1.setEnabled((self.playerType == VLC) and (self.playMode == VLC))
            self.menuZoom2.setEnabled(False)
            try:
                # FIXME
                zv = self.mediaplayer.video_get_scale()
                self.actionZoom1_fitwindow.setChecked(zv == 0)
                self.actionZoom1_1_1.setChecked(zv == 1)
                self.actionZoom1_1_2.setChecked(zv == 0.5)
                self.actionZoom1_1_4.setChecked(zv == 0.25)
                self.actionZoom1_2_1.setChecked(zv == 2)
            except Exception:
                pass

        # toolbar
        self.actionPlay.setEnabled(self.playerType == VLC)
        self.actionPause.setEnabled(self.playerType == VLC)
        self.actionReset.setEnabled(self.playerType == VLC)
        self.actionFaster.setEnabled(self.playerType == VLC)
        self.actionSlower.setEnabled(self.playerType == VLC)
        self.actionNormalSpeed.setEnabled(self.playerType == VLC)
        self.actionPrevious.setEnabled(self.playerType == VLC)
        self.actionNext.setEnabled(self.playerType == VLC)
        self.actionSnapshot.setEnabled(self.playerType == VLC)
        self.actionFrame_by_frame.setEnabled(self.playerType == VLC)
        self.actionFrame_backward.setEnabled(flagObs and (self.playMode == FFMPEG))
        self.actionFrame_forward.setEnabled(flagObs and (self.playMode == FFMPEG))

        for w in [self.actionCloseObs, self.actionCurrent_Time_Budget,
                  self.actionPlot_current_observation, self.actionFind_in_current_obs]:
            w.setEnabled(flagObs)

        # Tools
        self.actionShow_spectrogram.setEnabled(self.playerType == VLC)
        self.actionShow_the_sound_waveform.setEnabled(self.playerType == VLC)
        self.actionShow_data_files.setEnabled(self.playerType == VLC)
        self.menuImage_overlay_on_video.setEnabled(self.playerType == VLC)
        '''
        self.actionAdd_image_overlay_on_video.setEnabled(self.playerType == VLC)
        self.actionRemove_image_overlay.setEnabled(self.playerType == VLC)
        '''
        # geometric measurements
        self.actionDistance.setEnabled(flagObs and (self.playMode == FFMPEG))
        self.actionCoding_pad.setEnabled(flagObs)
        self.actionSubjects_pad.setEnabled(flagObs)
        self.actionBehaviors_coding_map.setEnabled(flagObs)

        # Analysis
        for w in [self.actionTime_budget, self.actionTime_budget_by_behaviors_category, self.actionTime_budget_report,
                  self.action_behavior_binary_table, self.action_advanced_event_filtering, self.menuPlot_events,
                  self.menuInter_rater_reliability, self.menuSimilarities, self.menuCreate_transitions_matrix,
                  self.actionSynthetic_binned_time_budget]:
            w.setEnabled(self.pj[OBSERVATIONS] != {})

        # statusbar labels
        for w in [self.lbTimeOffset, self.lbSpeed, self.lb_obs_time_interval]:
            w.setVisible(self.playerType == VLC)


    def connections(self):

        # menu file
        self.actionNew_project.triggered.connect(self.new_project_activated)
        self.actionOpen_project.triggered.connect(self.open_project_activated)
        self.actionNoldus_Observer_template.triggered.connect(self.import_project_from_observer_template)
        self.actionEdit_project.triggered.connect(self.edit_project_activated)
        self.actionCheck_project.triggered.connect(self.check_project_integrity)
        self.actionSave_project.triggered.connect(self.save_project_activated)
        self.actionSave_project_as.triggered.connect(self.save_project_as_activated)
        self.actionClose_project.triggered.connect(self.close_project)

        self.actionRemove_path_from_media_files.triggered.connect(self.remove_media_files_path)
        self.actionSend_project.triggered.connect(self.send_project_via_socket)

        self.menuCreate_subtitles_2.triggered.connect(self.create_subtitles)

        self.actionPreferences.triggered.connect(self.preferences)

        self.actionQuit.triggered.connect(self.actionQuit_activated)

        # menu observations
        self.actionNew_observation.triggered.connect(self.new_observation_triggered)
        self.actionOpen_observation.triggered.connect(lambda: self.open_observation("start"))
        self.actionView_observation.triggered.connect(lambda: self.open_observation(VIEW))
        self.actionEdit_observation_2.triggered.connect(self.edit_observation)
        self.actionObservationsList.triggered.connect(self.observations_list)

        self.actionClose_observation.triggered.connect(self.close_observation)

        self.actionAdd_event.triggered.connect(self.add_event)
        self.actionEdit_event.triggered.connect(self.edit_event)
        self.actionFilter_events.triggered.connect(self.filter_events)
        self.actionShow_all_events.triggered.connect(self.show_all_events)

        self.actionExport_observations_list.triggered.connect(self.export_observations_list_clicked)

        self.actionCheckStateEvents.triggered.connect(lambda: self.check_state_events("all"))
        self.actionCheckStateEventsSingleObs.triggered.connect(lambda: self.check_state_events("current"))
        self.actionClose_unpaired_events.triggered.connect(self.fix_unpaired_events)
        self.actionRunEventOutside.triggered.connect(self.run_event_outside)

        self.actionSelect_observations.triggered.connect(self.select_events_between_activated)

        self.actionEdit_selected_events.triggered.connect(self.edit_selected_events)
        self.actionEdit_event_time.triggered.connect(self.edit_time_selected_events)

        self.actionCopy_events.triggered.connect(self.copy_selected_events)
        self.actionPaste_events.triggered.connect(self.paste_clipboard_to_events)

        self.actionExplore_project.triggered.connect(self.explore_project)
        self.actionFind_events.triggered.connect(self.find_events)
        self.actionFind_replace_events.triggered.connect(self.find_replace_events)
        self.actionDelete_all_observations.triggered.connect(self.delete_all_events)
        self.actionDelete_selected_observations.triggered.connect(self.delete_selected_events)

        self.actionMedia_file_information.triggered.connect(self.media_file_info)

        self.actionLoad_observations_file.triggered.connect(self.import_observations)

        self.actionExportEvents_2.triggered.connect(lambda: self.export_tabular_events("tabular"))

        # behavioral sequences
        # self.actionExportEventString.triggered.connect(lambda: self.export_events_as_behavioral_sequences(timed=False))
        self.actionseparated_subjects.triggered.connect(lambda: self.export_events_as_behavioral_sequences(separated_subjects=True, timed=False))
        self.actiongrouped_subjects.triggered.connect(lambda: self.export_events_as_behavioral_sequences(separated_subjects=False, timed=False))

        self.actionExport_aggregated_events.triggered.connect(self.export_aggregated_events)
        self.actionExport_events_as_Praat_TextGrid.triggered.connect(self.export_state_events_as_textgrid)
        self.actionJWatcher.triggered.connect(lambda: self.export_tabular_events("jwatcher"))

        self.actionExtract_events_from_media_files.triggered.connect(self.extract_events)
        self.actionExtract_frames_from_media_files.triggered.connect(self.events_snapshots)

        self.actionCohen_s_kappa.triggered.connect(self.irr_cohen_kappa)
        self.actionNeedleman_Wunsch.triggered.connect(self.needleman_wunch)

        self.actionAll_transitions.triggered.connect(lambda: self.transitions_matrix("frequency"))
        self.actionNumber_of_transitions.triggered.connect(lambda: self.transitions_matrix("number"))

        self.actionFrequencies_of_transitions_after_behaviors.triggered.connect(
            lambda: self.transitions_matrix("frequencies_after_behaviors")
        )

        # menu playback
        self.actionJumpTo.triggered.connect(self.jump_to)

        # menu Tools

        self.action_block_dockwidgets.triggered.connect(self.block_dockwidgets)

        self.action_create_modifiers_coding_map.triggered.connect(self.modifiers_coding_map_creator)
        self.action_create_behaviors_coding_map.triggered.connect(self.behaviors_coding_map_creator)

        self.actionShow_spectrogram.triggered.connect(lambda: self.show_sound_signal_widget("spectrogram"))
        self.actionShow_the_sound_waveform.triggered.connect(lambda: self.show_sound_signal_widget("waveform"))
        self.actionShow_data_files.triggered.connect(self.show_data_files)
        self.actionDistance.triggered.connect(self.geometric_measurements)
        self.actionBehaviors_coding_map.triggered.connect(self.show_behaviors_coding_map)

        self.actionCoding_pad.triggered.connect(self.show_coding_pad)
        self.actionSubjects_pad.triggered.connect(self.show_subjects_pad)

        # image overlay on video
        self.actionAdd_image_overlay_on_video.triggered.connect(self.add_image_overlay)
        self.actionRemove_image_overlay.triggered.connect(self.remove_image_overlay)

        self.actionRecode_resize_video.triggered.connect(lambda: self.ffmpeg_process("reencode_resize"))
        self.actionRotate_video.triggered.connect(lambda: self.ffmpeg_process("rotate"))
        self.actionMedia_file_information_2.triggered.connect(self.media_file_info)

        self.actionCreate_transitions_flow_diagram.triggered.connect(self.transitions_dot_script)
        self.actionCreate_transitions_flow_diagram_2.triggered.connect(self.transitions_flow_diagram)

        # menu Analysis
        self.actionTime_budget.triggered.connect(lambda: self.time_budget(mode="by_behavior"))
        self.actionTime_budget_by_behaviors_category.triggered.connect(lambda: self.time_budget(mode="by_category"))

        self.actionTime_budget_report.triggered.connect(self.synthetic_time_budget)
        self.actionSynthetic_binned_time_budget.triggered.connect(self.synthetic_binned_time_budget)

        self.actionBehavior_bar_plot.triggered.connect(self.behaviors_bar_plot)
        self.actionBehavior_bar_plot.setVisible(True)

        self.actionPlot_events1.setVisible(False)
        self.actionPlot_events2.triggered.connect(lambda: self.plot_events_triggered(mode="list"))

        self.action_behavior_binary_table.triggered.connect(self.create_behavior_binary_table)

        self.action_advanced_event_filtering.triggered.connect(self.advanced_event_filtering)

        # menu Help
        self.actionUser_guide.triggered.connect(self.actionUser_guide_triggered)
        self.actionAbout.triggered.connect(self.actionAbout_activated)
        self.actionCheckUpdate.triggered.connect(self.actionCheckUpdate_activated)

        # toolbar
        self.action_obs_list.triggered.connect(self.observations_list)
        self.actionPlay.triggered.connect(self.play_activated)
        self.actionReset.triggered.connect(self.reset_activated)
        self.actionJumpBackward.triggered.connect(self.jumpBackward_activated)
        self.actionJumpForward.triggered.connect(self.jumpForward_activated)

        self.actionZoom1_fitwindow.triggered.connect(lambda: self.video_zoom(1, 0))
        self.actionZoom1_1_1.triggered.connect(lambda: self.video_zoom(1, 1))
        self.actionZoom1_1_2.triggered.connect(lambda: self.video_zoom(1, 0.5))
        self.actionZoom1_1_4.triggered.connect(lambda: self.video_zoom(1, 0.25))
        self.actionZoom1_2_1.triggered.connect(lambda: self.video_zoom(1, 2))

        self.actionZoom2_fitwindow.triggered.connect(lambda: self.video_zoom(2, 0))
        self.actionZoom2_1_1.triggered.connect(lambda: self.video_zoom(2, 1))
        self.actionZoom2_1_2.triggered.connect(lambda: self.video_zoom(2, 0.5))
        self.actionZoom2_1_4.triggered.connect(lambda: self.video_zoom(2, 0.25))
        self.actionZoom2_2_1.triggered.connect(lambda: self.video_zoom(2, 2))

        self.actionFaster.triggered.connect(self.video_faster_activated)
        self.actionSlower.triggered.connect(self.video_slower_activated)
        self.actionNormalSpeed.triggered.connect(self.video_normalspeed_activated)

        self.actionPrevious.triggered.connect(self.previous_media_file)
        self.actionNext.triggered.connect(self.next_media_file)

        self.actionSnapshot.triggered.connect(self.snapshot)

        self.actionFrame_by_frame.triggered.connect(self.switch_playing_mode)

        self.actionFrame_backward.triggered.connect(self.frame_backward)
        self.actionFrame_forward.triggered.connect(self.frame_forward)
        self.actionCloseObs.triggered.connect(self.close_observation)
        self.actionCurrent_Time_Budget.triggered.connect(lambda: self.time_budget(mode="by_behavior", mode2="current"))
        self.actionPlot_current_observation.triggered.connect(lambda: self.plot_events_triggered(mode="current"))
        self.actionFind_in_current_obs.triggered.connect(self.find_events)

        # table Widget double click
        self.twEvents.itemDoubleClicked.connect(self.twEvents_doubleClicked)
        self.twEthogram.itemDoubleClicked.connect(self.twEthogram_doubleClicked)
        self.twSubjects.itemDoubleClicked.connect(self.twSubjects_doubleClicked)

        # Actions for twEthogram context menu
        self.twEthogram.setContextMenuPolicy(Qt.ActionsContextMenu)
        self.twEthogram.horizontalHeader().sortIndicatorChanged.connect(self.twEthogram_sorted)

        self.actionViewBehavior.triggered.connect(self.view_behavior)
        self.twEthogram.addAction(self.actionViewBehavior)

        self.actionFilterBehaviors.triggered.connect(lambda: self.filter_behaviors(table=ETHOGRAM))
        self.twEthogram.addAction(self.actionFilterBehaviors)

        self.actionShowAllBehaviors.triggered.connect(self.show_all_behaviors)
        self.twEthogram.addAction(self.actionShowAllBehaviors)

        # Actions for twSubjects context menu
        self.twSubjects.setContextMenuPolicy(Qt.ActionsContextMenu)
        self.twSubjects.horizontalHeader().sortIndicatorChanged.connect(self.sort_twSubjects)
        self.actionFilterSubjects.triggered.connect(self.filter_subjects)
        self.twSubjects.addAction(self.actionFilterSubjects)

        self.actionShowAllSubjects.triggered.connect(self.show_all_subjects)
        self.twSubjects.addAction(self.actionShowAllSubjects)

        # Actions for twEvents menu
        self.twEvents.setContextMenuPolicy(Qt.ActionsContextMenu)

        self.twEvents.addAction(self.actionAdd_event)
        self.twEvents.addAction(self.actionEdit_selected_events)
        self.twEvents.addAction(self.actionEdit_event_time)

        self.twEvents.addAction(self.actionCopy_events)
        self.twEvents.addAction(self.actionPaste_events)

        separator2 = QAction(self)
        separator2.setSeparator(True)
        self.twEvents.addAction(separator2)

        self.twEvents.addAction(self.actionFind_events)
        self.twEvents.addAction(self.actionFind_replace_events)

        separator2 = QAction(self)
        separator2.setSeparator(True)
        self.twEvents.addAction(separator2)

        self.twEvents.addAction(self.actionFilter_events)
        self.twEvents.addAction(self.actionShow_all_events)

        separator2 = QAction(self)
        separator2.setSeparator(True)
        self.twEvents.addAction(separator2)

        self.twEvents.addAction(self.actionCheckStateEventsSingleObs)
        self.twEvents.addAction(self.actionClose_unpaired_events)

        self.twEvents.addAction(self.actionRunEventOutside)

        separator2 = QAction(self)
        separator2.setSeparator(True)
        self.twEvents.addAction(separator2)

        self.twEvents.addAction(self.actionDelete_selected_observations)
        self.twEvents.addAction(self.actionDelete_all_observations)

        # Actions for twSubjects context menu
        self.actionDeselectCurrentSubject.triggered.connect(lambda: self.update_subject(""))

        self.twSubjects.setContextMenuPolicy(Qt.ActionsContextMenu)
        self.twSubjects.addAction(self.actionDeselectCurrentSubject)

        # subjects

        # timer for playing
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.timer_out)

        # timer for spectrogram visualization
        self.timer_sound_signal = QTimer(self)
        # TODO check value of interval
        self.timer_sound_signal.setInterval(SPECTRO_TIMER)
        self.timer_sound_signal.timeout.connect(self.timer_sound_signal_out)

        # timer for timing the live observation
        self.liveTimer = QTimer(self)
        self.liveTimer.timeout.connect(self.liveTimer_out)

        # timer for automatic backup
        self.automaticBackupTimer = QTimer(self)
        self.automaticBackupTimer.timeout.connect(self.automatic_backup)
        if self.automaticBackup:
            self.automaticBackupTimer.start(self.automaticBackup * 60000)

        self.pb_live_obs.clicked.connect(self.start_live_observation)


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


    def create_behavior_binary_table(self):
        """
        create behavior binary table
        """

        QMessageBox.warning(self, programName,
                            ("Depending of the length of your observations "
                            "the execution of this function may be very long.<br>"
                            "The program interface may freeze, be patient. <br>"
                             ))

        behavior_binary_table.behavior_binary_table(self.pj)


    def advanced_event_filtering(self):
        """
        advanced filter for coded event
        """

        advanced_event_filtering.event_filtering(self.pj)


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

        extended_file_formats = ["Tab Separated Values (*.tsv)",
                                 "Comma Separated Values (*.csv)",
                                 "Open Document Spreadsheet ODS (*.ods)",
                                 "Microsoft Excel Spreadsheet XLSX (*.xlsx)",
                                 "Legacy Microsoft Excel Spreadsheet XLS (*.xls)",
                                 "HTML (*.html)"]
        file_formats = ["tsv", "csv", "ods", "xlsx", "xls", "html"]

        file_name, filter_ = QFileDialog().getSaveFileName(self, "Export list of selected observations",
                                                           "", ";;".join(extended_file_formats))

        if file_name:
            output_format = file_formats[extended_file_formats.index(filter_)]
            if pathlib.Path(file_name).suffix != "." + output_format:
                file_name = str(pathlib.Path(file_name)) + "." + output_format
                # check if file name with extension already exists
                if pathlib.Path(file_name).is_file():
                    if dialog.MessageDialog(programName,
                                            f"The file {file_name} already exists.",
                                            [CANCEL, OVERWRITE]) == CANCEL:
                        return

            if not project_functions.export_observations_list(self.pj, selected_observations, file_name, output_format):
                QMessageBox.warning(self, programName, "File not created due to an error")



    def check_project_integrity(self):
        """
        launch check project integrity function
        """

        ib = dialog.Input_dialog("Select the elements to be checked",
                                 [("cb", "Test media file accessibility", True),
                                 ])
        if not ib.exec_():
            return

        msg = project_functions.check_project_integrity(self.pj,
                                                        self.timeFormat,
                                                        self.projectFileName,
                                                        media_file_available=ib.elements["Test media file accessibility"].isChecked())
        if msg:
            msg = f"Some issues were found in the project<br><br>{msg}"
            self.results = dialog.ResultsWidget()
            self.results.setWindowTitle("Check project integrity")
            self.results.ptText.clear()
            self.results.ptText.setReadOnly(True)
            self.results.ptText.appendHtml(msg)
            self.results.show()
        else:
            QMessageBox.information(self, programName, "The current project has no issues")


    def remove_media_files_path(self):
        """
        remove path of media files
        """

        if dialog.MessageDialog(programName,
                                ("Removing the path of media files from the project file is irreversible.<br>"
                                 "Are you sure to continue?"),
                                [YES, NO]) == NO:
            return

        self.pj = project_functions.remove_media_files_path(self.pj)
        self.projectChanged = True


    def irr_cohen_kappa(self):
        """
        calculate the Inter-Rater Reliability index - Cohen's Kappa of 2 or more observations
        https://en.wikipedia.org/wiki/Cohen%27s_kappa
        """

        # ask user observations to analyze
        result, selected_observations = self.selectObservations(MULTIPLE)
        if not selected_observations:
            return
        if len(selected_observations) < 2:
            QMessageBox.information(self, programName, "Select almost 2 observations for IRR analysis")
            return

        # check if state events are paired
        out = ""
        not_paired_obs_list = []
        for obsId in selected_observations:
            r, msg = project_functions.check_state_events_obs(obsId,
                                                              self.pj[ETHOGRAM],
                                                              self.pj[OBSERVATIONS][obsId],
                                                              self.timeFormat)

            if not r:
                out += f"Observation: <strong>{obsId}</strong><br>{msg}<br>"
                not_paired_obs_list.append(obsId)

        if out:
            out = "The observations with UNPAIRED state events will be removed from the analysis<br><br>" + out
            results = dialog.Results_dialog()
            results.setWindowTitle(programName + " - Check selected observations")
            results.ptText.setReadOnly(True)
            results.ptText.appendHtml(out)
            results.pbSave.setVisible(False)
            results.pbCancel.setVisible(True)

            if not results.exec_():
                return

        # remove observations with unpaired state events
        selected_observations = [x for x in selected_observations if x not in not_paired_obs_list]
        if not selected_observations:
            return

        plot_parameters = self.choose_obs_subj_behav_category(selected_observations,
                                                              maxTime=0,
                                                              flagShowIncludeModifiers=True,
                                                              flagShowExcludeBehaviorsWoEvents=False)

        if not plot_parameters[SELECTED_SUBJECTS] or not plot_parameters[SELECTED_BEHAVIORS]:
            return

        # ask for time slice
        i, ok = QInputDialog.getDouble(self, "IRR - Cohen's Kappa (time-unit)",
                                       "Time unit (in seconds):", 1.0, 0.001, 86400, 3)
        if not ok:
            return
        interval = float2decimal(i)

        ok, msg, db_connector = db_functions.load_aggregated_events_in_db(self.pj,
                                                                          plot_parameters[SELECTED_SUBJECTS],
                                                                          selected_observations,
                                                                          plot_parameters[SELECTED_BEHAVIORS])

        cursor = db_connector.cursor()
        out = ("Index of Inter-rater Reliability - Cohen's Kappa\n\n"
               f"Interval time: {interval:.3f} s\n"
               f"Selected subjects: {', '.join(plot_parameters[SELECTED_SUBJECTS])}\n\n")

        mem_done = []
        irr_results = np.ones((len(selected_observations), len(selected_observations)))

        for obs_id1 in selected_observations:
            for obs_id2 in selected_observations:
                if obs_id1 == obs_id2:
                    continue
                if set([obs_id1, obs_id2]) not in mem_done:
                    K, msg = irr.cohen_kappa(cursor,
                                             obs_id1, obs_id2,
                                             interval,
                                             plot_parameters[SELECTED_SUBJECTS],
                                             plot_parameters[INCLUDE_MODIFIERS])
                    irr_results[selected_observations.index(obs_id1), selected_observations.index(obs_id2)] = K
                    irr_results[selected_observations.index(obs_id2), selected_observations.index(obs_id1)] = K
                    out += msg + "\n=============\n"
                    mem_done.append(set([obs_id1, obs_id2]))

        out2 = "\t{}\n".format('\t'.join(list(selected_observations)))
        for r in range(irr_results.shape[0]):
            out2 += f"{selected_observations[r]}\t"
            out2 += "\t".join(["%8.6f" % x for x in irr_results[r, :]]) + "\n"

        self.results = dialog.ResultsWidget()
        self.results.setWindowTitle(f"BORIS - IRR - Cohen's Kappa (time-unit) analysis results")
        self.results.ptText.setReadOnly(True)
        if len(selected_observations) == 2:
            self.results.ptText.appendPlainText(out)
        else:
            self.results.ptText.appendPlainText(out2)
        self.results.show()


    def needleman_wunch(self):
        """
        calculate the Needleman-Wunsch similarity for 2 or more observations
        """

        # ask user observations to analyze
        result, selected_observations = self.selectObservations(MULTIPLE)
        if not selected_observations:
            return
        if len(selected_observations) < 2:
            QMessageBox.information(self, programName,
                                    "You have to select at least 2 observations for Needleman-Wunsch similarity")
            return

        # check if state events are paired
        out = ""
        not_paired_obs_list = []
        for obsId in selected_observations:
            r, msg = project_functions.check_state_events_obs(obsId,
                                                              self.pj[ETHOGRAM],
                                                              self.pj[OBSERVATIONS][obsId],
                                                              self.timeFormat)

            if not r:
                out += f"Observation: <strong>{obsId}</strong><br>{msg}<br>"
                not_paired_obs_list.append(obsId)

        if out:
            out = "The observations with UNPAIRED state events will be removed from the analysis<br><br>" + out
            results = dialog.Results_dialog()
            results.setWindowTitle(programName + " - Check selected observations")
            results.ptText.setReadOnly(True)
            results.ptText.appendHtml(out)
            results.pbSave.setVisible(False)
            results.pbCancel.setVisible(True)

            if not results.exec_():
                return

        # remove observations with unpaired state events
        selected_observations = [x for x in selected_observations if x not in not_paired_obs_list]
        if not selected_observations:
            return

        plot_parameters = self.choose_obs_subj_behav_category(selected_observations,
                                                              maxTime=0,
                                                              flagShowIncludeModifiers=True,
                                                              flagShowExcludeBehaviorsWoEvents=False)

        if not plot_parameters[SELECTED_SUBJECTS] or not plot_parameters[SELECTED_BEHAVIORS]:
            return

        # ask for time slice

        i, ok = QInputDialog.getDouble(self, "Needleman-Wunsch similarity",
                                       "Time unit (in seconds):", 1.0, 0.001, 86400, 3)
        if not ok:
            return
        interval = float2decimal(i)


        ok, msg, db_connector = db_functions.load_aggregated_events_in_db(self.pj,
                                                                          plot_parameters[SELECTED_SUBJECTS],
                                                                          selected_observations,
                                                                          plot_parameters[SELECTED_BEHAVIORS])

        cursor = db_connector.cursor()
        out = ("Needleman-Wunsch similarity\n\n"
               f"Time unit: {interval:.3f} s\n"
               f"Selected subjects: {', '.join(plot_parameters[SELECTED_SUBJECTS])}\n\n")
        mem_done = []
        nws_results = np.ones((len(selected_observations), len(selected_observations)))

        for obs_id1 in selected_observations:
            for obs_id2 in selected_observations:
                if obs_id1 == obs_id2:
                    continue
                if set([obs_id1, obs_id2]) not in mem_done:
                    similarity, msg = irr.needleman_wunsch_identity(cursor,
                                                                    obs_id1, obs_id2,
                                                                    interval,
                                                                    plot_parameters[SELECTED_SUBJECTS],
                                                                    plot_parameters[INCLUDE_MODIFIERS])
                    nws_results[selected_observations.index(obs_id1), selected_observations.index(obs_id2)] = similarity
                    nws_results[selected_observations.index(obs_id2), selected_observations.index(obs_id1)] = similarity
                    out += msg + "\n=============\n"
                    mem_done.append(set([obs_id1, obs_id2]))

        out2 = "\t{}\n".format("\t".join(list(selected_observations)))
        for r in range(nws_results.shape[0]):
            out2 += f"{selected_observations[r]}\t"
            out2 += "\t".join([f"{x:8.6f}" for x in nws_results[r, :]]) + "\n"

        self.results = dialog.ResultsWidget()
        self.results.setWindowTitle(programName + " - Needleman-Wunsch similarity")
        self.results.ptText.setReadOnly(True)
        if len(selected_observations) == 2:
            self.results.ptText.appendPlainText(out)
        else:
            self.results.ptText.appendPlainText(out2)
        self.results.show()


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
                            modifiers += (f"<br>Name: {behav[MODIFIERS][idx]['name'] if behav[MODIFIERS][idx]['name'] else '-'}"
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


    def send_project_via_socket(self):
        """
        send project to a device via socket
        """

        def receive_signal(msg_dict):

            if "RECEIVED" in msg_dict:
                try:
                    sent_obs = json.loads(msg_dict["RECEIVED"][:-5])  # cut final
                except Exception:
                    logging.debug("error receiving observation")
                    del self.w
                    self.actionSend_project.setText("Project server")
                    return

                logging.debug(f"decoded {type(sent_obs)} length: {len(sent_obs)}")

                flag_msg = False
                mem_obsid = ""
                for obsId in sent_obs:

                    self.w.lwi.addItem(
                        QListWidgetItem(f"{datetime.datetime.now().isoformat()}: Observation {obsId} received")
                    )
                    self.w.lwi.scrollToBottom()

                    if obsId in self.pj[OBSERVATIONS]:
                        flag_msg = True
                        response = dialog.MessageDialog(
                            programName,
                            (f"An observation with the same id<br><b>{obsId}</b><br>"
                             f"received from<br><b>{msg_dict['SENDER'][0]}</b><br>"
                             "already exists in the current project."),
                            [OVERWRITE, "Rename received observation", CANCEL])

                        if response == CANCEL:
                            return
                        self.projectChanged = True
                        if response == OVERWRITE:
                            self.pj[OBSERVATIONS][obsId] = dict(sent_obs[obsId])

                        if response == "Rename received observation":
                            new_id = obsId
                            while new_id in self.pj[OBSERVATIONS]:
                                new_id, ok = QInputDialog.getText(self,
                                                                  f"Rename observation received from {msg_dict['SENDER'][0]}",
                                                                  "New observation id:",
                                                                  QLineEdit.Normal,
                                                                  new_id)

                            self.pj[OBSERVATIONS][new_id] = dict(sent_obs[obsId])

                    else:
                        self.pj[OBSERVATIONS][obsId] = dict(sent_obs[obsId])
                        self.projectChanged = True
                        mem_obsid = obsId

            elif "URL" in msg_dict:
                self.tcp_port = int(msg_dict["URL"].split(":")[-1])
                self.w.label.setText(f"Project server URL:<br><b>{msg_dict['URL']}</b><br><br>Timeout: 30 minutes")

            else:
                if "stopped" in msg_dict["MESSAGE"] or "timeout" in msg_dict["MESSAGE"]:
                    del self.w
                    self.actionSend_project.setText("Project server")
                else:
                    self.w.lwi.addItem(QListWidgetItem(f"{datetime.datetime.now().isoformat()}: {msg_dict['MESSAGE']}"))
                    self.w.lwi.scrollToBottom()

        if "server" in self.actionSend_project.text():

            include_obs = NO
            if self.pj[OBSERVATIONS]:
                include_obs = dialog.MessageDialog(programName, "Include observations?", [YES, NO, CANCEL])
                if include_obs == CANCEL:
                    return

            self.w = dialog.Info_widget()
            self.w.resize(450, 100)
            self.w.setWindowFlags(Qt.WindowStaysOnTopHint)
            self.w.setWindowTitle("Project server")
            self.w.label.setText("")
            self.w.show()
            QApplication.processEvents()

            cp_project = dict(self.pj)
            if include_obs == NO:
                cp_project[OBSERVATIONS] = {}

            self.server_thread = ProjectServerThread(message=str.encode(str(json.dumps(cp_project,
                                                                            indent=None,
                                                                            separators=(",", ":"),
                                                                            default=decimal_default))))
            self.server_thread.signal.connect(receive_signal)

            self.server_thread.start()

            self.actionSend_project.setText("Stop serving project")

        # send stop msg to project server
        elif "serving" in self.actionSend_project.text():

            s = socket.socket()
            s.connect((get_ip_address(), self.tcp_port))
            s.send(str.encode("stop"))
            received = ""
            while 1:
                data = s.recv(20)  # BUFFER_SIZE = 20
                if not data:
                    break
                received += data
            s.close


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
                                                 "Done: {done} of {tot}"
                                                ).format(done=self.processes_widget.number_of_files - len(self.processes),
                                                         tot=self.processes_widget.number_of_files))
            self.processes_widget.lwi.clear()
            self.processes_widget.lwi.addItems([self.processes[idx - 1][1][2],
                                                self.processes[idx - 1][0].readAllStandardOutput().data().decode("utf-8")
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

                ib = dialog.Input_dialog("Set the parameters for re-encoding / resizing",
                                 [("sb", "Horizontal resolution (in pixel)", 352, 3840, 100, current_resolution),
                                  ("sb", "Video quality (bitrate)", 100, 1000000, 500, current_bitrate),
                                 ])
                if not ib.exec_():
                    return

                if len(fileNames) > 1:
                    if dialog.MessageDialog(programName,
                                            "All the selected video files will be re-encoded / resized with these parameters",
                                            [OK, CANCEL]) == CANCEL:
                        return


                horiz_resol = ib.elements["Horizontal resolution (in pixel)"].value()
                video_quality = ib.elements["Video quality (bitrate)"].value()


            if action == "rotate":
                rotation_items = ("Rotate 90 clockwise", "Rotate 90 counter clockwise", "rotate 180")

                rotation, ok = QInputDialog.getItem(self, "Rotate media file(s)", "Type of rotation", rotation_items, 0, False)

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
                    args = ["-y",
                            "-i", f"{file_name}",
                            "-vf", f"scale={horiz_resol}:-1",
                            "-b:v", f"{video_quality}k",
                            f"{file_name}.re-encoded.{horiz_resol}px.{video_quality}k.avi"
                           ]

                if action == "rotate":

                    # check bitrate
                    r = accurate_media_analysis(self.ffmpeg_bin, file_name)
                    if "error" not in r and r["bitrate"] != -1:
                        video_quality = r["bitrate"]
                    else:
                        video_quality = 2000

                    if rotation_idx in [1, 2]:
                        args = ["-y",
                                "-i", f"{file_name}",
                                "-vf", f"transpose={rotation_idx}",
                                "-codec:a", "copy",
                                "-b:v", f"{video_quality}k",
                                f"{file_name}.rotated{['', '90', '-90'][rotation_idx]}.avi"
                               ]

                    if rotation_idx == 3:  # 180
                        args = ["-y",
                                "-i", f"{file_name}",
                                "-vf", "transpose=2,transpose=2",
                                "-codec:a", "copy",
                                "-b:v", f"{video_quality}k",
                                f"{file_name}.rotated180.avi"
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


    def close_signal_from_coding_pad(self, geom):
        """
        save coding pad geometry after close
        """
        self.codingpad_geometry_memory = geom


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


    def show_coding_pad(self):
        """
        show coding pad window
        """
        if self.playerType == VIEWER:
            QMessageBox.warning(self, programName, "The coding pad is not available in <b>VIEW</b> mode")
            return

        if hasattr(self, "codingpad"):
            self.codingpad.filtered_behaviors = [self.twEthogram.item(i, 1).text() for i in range(self.twEthogram.rowCount())]
            if not self.codingpad.filtered_behaviors:
                QMessageBox.warning(self, programName, "No behaviors to show!")
                return
            self.codingpad.compose()
            self.codingpad.show()
            self.codingpad.setGeometry(self.codingpad_geometry_memory.x(),
                                       self.codingpad_geometry_memory.y(),
                                       self.codingpad_geometry_memory.width(),
                                       self.codingpad_geometry_memory.height())

        else:
            filtered_behaviors = [self.twEthogram.item(i, 1).text() for i in range(self.twEthogram.rowCount())]
            if not filtered_behaviors:
                QMessageBox.warning(self, programName, "No behaviors to show!")
                return
            self.codingpad = coding_pad.CodingPad(self.pj, filtered_behaviors)
            self.codingpad.setWindowFlags(Qt.WindowStaysOnTopHint)
            self.codingpad.sendEventSignal.connect(self.signal_from_widget)
            self.codingpad.clickSignal.connect(self.click_signal_from_coding_pad)
            self.codingpad.close_signal.connect(self.close_signal_from_coding_pad)
            self.codingpad.show()


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
            self.subjects_pad.filtered_subjects = [self.twSubjects.item(i, SUBJECT_NAME_FIELD_IDX).text()
                                                   for i in range(self.twSubjects.rowCount())]
            if not self.subjects_pad.filtered_subjects:
                QMessageBox.warning(self, programName, "No subjects to show")
                return
            self.subjects_pad.compose()
            self.subjects_pad.show()
            self.subjects_pad.setGeometry(self.subjectspad_geometry_memory.x(),
                                          self.subjectspad_geometry_memory.y(),
                                          self.subjectspad_geometry_memory.width(),
                                          self.subjectspad_geometry_memory.height())
        else:
            filtered_subjects = [self.twSubjects.item(i, SUBJECT_NAME_FIELD_IDX).text()
                                 for i in range(self.twSubjects.rowCount())]
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




    def filter_behaviors(self,
                         title="Select the behaviors to show in the ethogram table",
                         text="Behaviors to show in ethogram list",
                         table=ETHOGRAM,
                         behavior_type=[STATE_EVENT, POINT_EVENT]):
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
        for w in [paramPanelWindow.lwSubjects, paramPanelWindow.pbSelectAllSubjects, paramPanelWindow.pbUnselectAllSubjects,
                  paramPanelWindow.pbReverseSubjectsSelection, paramPanelWindow.lbSubjects, paramPanelWindow.cbIncludeModifiers,
                  paramPanelWindow.cbExcludeBehaviors, paramPanelWindow.frm_time, paramPanelWindow.frm_time_bin_size]:
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
            if "" in [self.pj[ETHOGRAM][idx][BEHAVIOR_CATEGORY] for idx in self.pj[ETHOGRAM]
                      if BEHAVIOR_CATEGORY in self.pj[ETHOGRAM][idx]]:
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


                if ((categories == ["###no category###"]) or
                   (behavior in [self.pj[ETHOGRAM][x][BEHAVIOR_CODE] for x in self.pj[ETHOGRAM]
                                 if BEHAVIOR_CATEGORY in self.pj[ETHOGRAM][x] and
                                    self.pj[ETHOGRAM][x][BEHAVIOR_CATEGORY] == category])):

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
                    self.codingpad.filtered_behaviors = [self.twEthogram.item(i, 1).text() for i in range(self.twEthogram.rowCount())]
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

        for w in [paramPanelWindow.lwSubjects, paramPanelWindow.pbSelectAllSubjects, paramPanelWindow.pbUnselectAllSubjects,
                  paramPanelWindow.pbReverseSubjectsSelection, paramPanelWindow.lbSubjects, paramPanelWindow.cbIncludeModifiers,
                  paramPanelWindow.cbExcludeBehaviors, paramPanelWindow.frm_time, paramPanelWindow.frm_time_bin_size]:
            w.setVisible(False)

        gui_utilities.restore_geometry(paramPanelWindow, "filter subjects", (800, 600))

        # subjects filtered
        filtered_subjects = [self.twSubjects.item(i, SUBJECT_NAME_FIELD_IDX).text() for i in range(self.twSubjects.rowCount())]

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
                self.subjects_pad.filtered_subjects = [self.twSubjects.item(i, SUBJECT_NAME_FIELD_IDX).text()
                                                       for i in range(self.twSubjects.rowCount())]
                self.subjects_pad.compose()


    def events_snapshots(self):
        """
        create snapshots corresponding to coded events
        if observations are from media file and media files have video
        """

        result, selected_observations = self.selectObservations(MULTIPLE)
        if not selected_observations:
            return

        # check if obs are MEDIA
        live_obs_list = []
        for obs_id in selected_observations:
            if self.pj[OBSERVATIONS][obs_id][TYPE] in [LIVE]:
                live_obs_list.append(obs_id)
        if live_obs_list:
            out = "The following observations are live observations and will be removed from the analysis<br><br>"
            out += "<br>".join(live_obs_list)
            results = dialog.Results_dialog()
            results.setWindowTitle(programName)
            results.ptText.setReadOnly(True)
            results.ptText.appendHtml(out)
            results.pbSave.setVisible(False)
            results.pbCancel.setVisible(True)
            if not results.exec_():
                return

        # remove live  observations
        selected_observations = [x for x in selected_observations if x not in live_obs_list]
        if not selected_observations:
            return

        # check if state events are paired
        out = ""
        not_paired_obs_list = []
        for obsId in selected_observations:
            r, msg = project_functions.check_state_events_obs(obsId,
                                                              self.pj[ETHOGRAM],
                                                              self.pj[OBSERVATIONS][obsId],
                                                              self.timeFormat)

            if not r:
                out += f"Observation: <strong>{obsId}</strong><br>{msg}<br>"
                not_paired_obs_list.append(obsId)

        if out:
            out = "The observations with UNPAIRED state events will be removed from the analysis<br><br>" + out
            results = dialog.Results_dialog()
            results.setWindowTitle(f"{programName} - Check selected observations")
            results.ptText.setReadOnly(True)
            results.ptText.appendHtml(out)
            results.pbSave.setVisible(False)
            results.pbCancel.setVisible(True)

            if not results.exec_():
                return

        # remove observations with unpaired state events
        selected_observations = [x for x in selected_observations if x not in not_paired_obs_list]
        if not selected_observations:
            return

        parameters = self.choose_obs_subj_behav_category(selected_observations, maxTime=0,
                                                         flagShowIncludeModifiers=False,
                                                         flagShowExcludeBehaviorsWoEvents=False)

        if not parameters[SELECTED_SUBJECTS] or not parameters[SELECTED_BEHAVIORS]:
            return

        # Ask for time interval around the event
        while True:
            text, ok = QInputDialog.getDouble(self, "Time interval around the events",
                                              "Time (in seconds):", 0.0, 0.0, 86400, 1)
            if not ok:
                return
            try:
                time_interval = float2decimal(text)
                break
            except Exception:
                QMessageBox.warning(self, programName, f"<b>{text}</b> is not recognized as time")

        # directory for saving frames
        exportDir = QFileDialog().getExistingDirectory(self, "Choose a directory to extract events",
                                                       os.path.expanduser("~"),
                                                       options=QFileDialog(self).ShowDirsOnly)
        if not exportDir:
            return

        cursor = db_functions.load_events_in_db(self.pj,
                                                parameters[SELECTED_SUBJECTS],
                                                selected_observations,
                                                parameters[SELECTED_BEHAVIORS],
                                                time_interval=TIME_FULL_OBS)

        try:
            for obsId in selected_observations:

                for nplayer in self.pj[OBSERVATIONS][obsId][FILE]:

                    if not self.pj[OBSERVATIONS][obsId][FILE][nplayer]:
                        continue
                    duration1 = []   # in seconds
                    for mediaFile in self.pj[OBSERVATIONS][obsId][FILE][nplayer]:
                        duration1.append(self.pj[OBSERVATIONS][obsId][MEDIA_INFO][LENGTH][mediaFile])

                    for subject in parameters[SELECTED_SUBJECTS]:

                        for behavior in parameters[SELECTED_BEHAVIORS]:

                            cursor.execute("SELECT occurence FROM events WHERE observation = ? AND subject = ? AND code = ?",
                                           (obsId, subject, behavior))
                            rows = [{"occurence": float2decimal(r["occurence"])} for r in cursor.fetchall()]

                            behavior_state = project_functions.event_type(behavior, self.pj[ETHOGRAM])

                            for idx, row in enumerate(rows):

                                mediaFileIdx = [idx1 for idx1, x in enumerate(duration1)
                                                if row["occurence"] >= sum(duration1[0:idx1])][-1]

                                # check if media has video
                                flag_no_video = False
                                try:
                                    flag_no_video = not self.pj[OBSERVATIONS][obsId][MEDIA_INFO][HAS_VIDEO][self.pj[OBSERVATIONS][obsId][FILE][nplayer][mediaFileIdx]]
                                except Exception:
                                    flag_no_video = True

                                if flag_no_video:
                                    logging.debug(f"Media {self.pj[OBSERVATIONS][obsId][FILE][nplayer][mediaFileIdx]} does not have video")
                                    flag_no_video = True
                                    response = dialog.MessageDialog(programName,
                                                                    ("The following media file does not have video.<br>"
                                                                     f"{self.pj[OBSERVATIONS][obsId][FILE][nplayer][mediaFileIdx]}"),
                                                                    [OK, "Abort"])
                                    if response == OK:
                                        continue
                                    if response == "Abort":
                                        return

                                # check FPS
                                mediafile_fps = 0
                                try:
                                    if self.pj[OBSERVATIONS][obsId][MEDIA_INFO][FPS][self.pj[OBSERVATIONS][obsId][FILE][nplayer][mediaFileIdx]]:
                                        mediafile_fps = float2decimal(self.pj[OBSERVATIONS][obsId][MEDIA_INFO][FPS][self.pj[OBSERVATIONS][obsId][FILE][nplayer][mediaFileIdx]])
                                except Exception:
                                    mediafile_fps = 0

                                if not mediafile_fps:
                                    logging.debug(f"FPS not found for {self.pj[OBSERVATIONS][obsId][FILE][nplayer][mediaFileIdx]}")
                                    response = dialog.MessageDialog(programName,
                                                                    ("The FPS was not found for the following media file:<br>"
                                                                     f"{self.pj[OBSERVATIONS][obsId][FILE][nplayer][mediaFileIdx]}"),
                                                                    [OK, "Abort"])
                                    if response == OK:
                                        continue
                                    if response == "Abort":
                                        return

                                globalStart = Decimal("0.000") if row["occurence"] < time_interval else round(
                                    row["occurence"] - time_interval, 3)
                                start = round(row["occurence"]
                                              - time_interval
                                              - float2decimal(sum(duration1[0:mediaFileIdx]))
                                              - self.pj[OBSERVATIONS][obsId][TIME_OFFSET],
                                              3)
                                if start < time_interval:
                                    start = Decimal("0.000")

                                if POINT in behavior_state:

                                    media_path = project_functions.media_full_path(self.pj[OBSERVATIONS][obsId][FILE][nplayer][mediaFileIdx],
                                                                                   self.projectFileName)

                                    vframes = 1 if not time_interval else int(mediafile_fps * time_interval * 2)
                                    ffmpeg_command = (f'"{self.ffmpeg_bin}" '
                                                      f'-ss {start:.3f} '
                                                      f'-i "{media_path}" '
                                                      f'-vframes {vframes} '
                                                      # f'-vf scale=1024{frame_resize}:-1 '
                                                      f'"{exportDir}{os.sep}'
                                                      f'{utilities.safeFileName(obsId)}'
                                                      f'_PLAYER{nplayer}'
                                                      f'_{utilities.safeFileName(subject)}'
                                                      f'_{utilities.safeFileName(behavior)}'
                                                      f'_{start:.3f}_%08d.{self.frame_bitmap_format.lower()}"')


                                    logging.debug(f"ffmpeg command: {ffmpeg_command}")

                                    p = subprocess.Popen(ffmpeg_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                                         shell=True)
                                    out, error = p.communicate()


                                if STATE in behavior_state:
                                    if idx % 2 == 0:

                                        # check if stop is on same media file
                                        if mediaFileIdx != [idx1 for idx1, x in enumerate(duration1)
                                                            if rows[idx + 1]["occurence"] >= sum(duration1[0:idx1])][-1]:
                                            response = dialog.MessageDialog(programName,
                                                                            ("The event extends on 2 video. "
                                                                             "At the moment it no possible to extract frames "
                                                                             "for this type of event.<br>"),
                                                                             [OK, "Abort"])
                                            if response == OK:
                                                continue
                                            if response == "Abort":
                                                return

                                        globalStop = round(rows[idx + 1]["occurence"] + time_interval, 3)

                                        stop = round(rows[idx + 1]["occurence"]
                                                     + time_interval
                                                     - float2decimal(sum(duration1[0:mediaFileIdx]))
                                                     - self.pj[OBSERVATIONS][obsId][TIME_OFFSET],
                                                     3)

                                        # check if start after length of media
                                        try:
                                            if start > self.pj[OBSERVATIONS][obsId][MEDIA_INFO][LENGTH][self.pj[OBSERVATIONS]
                                                                                                               [obsId][FILE]
                                                                                                               [nplayer]
                                                                                                               [mediaFileIdx]]:
                                                continue
                                        except Exception:
                                            continue

                                        media_path = project_functions.media_full_path(self.pj[OBSERVATIONS][obsId][FILE][nplayer][mediaFileIdx],
                                                                                       self.projectFileName)

                                        extension = "png"
                                        vframes = int((stop - start) * mediafile_fps + time_interval * mediafile_fps * 2)
                                        ffmpeg_command = (f'"{self.ffmpeg_bin}" -ss {start:.3f} '
                                                          f'-i "{media_path}" '
                                                          f'-vframes {vframes} '
                                                          # f'-vf scale=1024{frame_resize}:-1 '
                                                          f'"{exportDir}{os.sep}'
                                                          f'{utilities.safeFileName(obsId)}'
                                                          f'_PLAYER{nplayer}'
                                                          f'_{utilities.safeFileName(subject)}'
                                                          f'_{utilities.safeFileName(behavior)}'
                                                          f'_{start:.3f}_%08d.{self.frame_bitmap_format.lower()}"')

                                        logging.debug(f"ffmpeg command: {ffmpeg_command}")

                                        p = subprocess.Popen(ffmpeg_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                                             shell=True)
                                        out, error = p.communicate()

        except Exception:
            dialog.error_message("Export during frame extraction", sys.exc_info())


    def extract_events(self):
        """
        extract sub-sequences from media files corresponding to coded events with FFmpeg
        in case of point event, from -n to +n seconds are extracted (n is asked to user)
        """

        result, selected_observations = self.selectObservations(MULTIPLE)
        if not selected_observations:
            return

        # check if obs are MEDIA
        live_obs_list = []
        for obs_id in selected_observations:
            if self.pj[OBSERVATIONS][obs_id][TYPE] in [LIVE]:
                live_obs_list.append(obs_id)
        if live_obs_list:
            out = "The following observations are live observations and will be removed from analysis<br><br>"
            out += "<br>".join(live_obs_list)
            results = dialog.Results_dialog()
            results.setWindowTitle(programName)
            results.ptText.setReadOnly(True)
            results.ptText.appendHtml(out)
            results.pbSave.setVisible(False)
            results.pbCancel.setVisible(True)
            if not results.exec_():
                return

        # remove live observations
        selected_observations = [x for x in selected_observations if x not in live_obs_list]
        if not selected_observations:
            return

        parameters = self.choose_obs_subj_behav_category(selected_observations, maxTime=0,
                                                         flagShowIncludeModifiers=False,
                                                         flagShowExcludeBehaviorsWoEvents=False)

        if not parameters[SELECTED_SUBJECTS] or not parameters[SELECTED_BEHAVIORS]:
            return

        # check if state events are paired
        out = ""
        not_paired_obs_list = []
        for obsId in selected_observations:
            r, msg = project_functions.check_state_events_obs(obsId,
                                                              self.pj[ETHOGRAM],
                                                              self.pj[OBSERVATIONS][obsId],
                                                              self.timeFormat)

            if not r:
                # check if unpaired behavior is included in behaviors to extract
                for behav in parameters[SELECTED_BEHAVIORS]:
                    if f"behavior <b>{behav}</b>" in msg:
                        out += f"Observation: <strong>{obsId}</strong><br>{msg}<br>"
                        not_paired_obs_list.append(obsId)

        if out:
            out = "The observations with UNPAIRED state events will be removed from the analysis<br><br>" + out
            results = dialog.Results_dialog()
            results.setWindowTitle(f"{programName} - Check selected observations and selected behaviors")
            results.ptText.setReadOnly(True)
            results.ptText.appendHtml(out)
            results.pbSave.setVisible(False)
            results.pbCancel.setVisible(True)

            if not results.exec_():
                return

        # remove observations with unpaired state events
        selected_observations = [x for x in selected_observations if x not in not_paired_obs_list]
        if not selected_observations:
            return



        # Ask for time interval around the event
        while True:
            text, ok = QInputDialog.getDouble(self, "Time interval around the events",
                                              "Time (in seconds):", 0.0, 0.0, 86400, 1)
            if not ok:
                return
            try:
                timeOffset = float2decimal(text)
                break
            except Exception:
                QMessageBox.warning(self, programName, f"<b>{text}</b> is not recognized as time")

        # ask for video / audio extraction
        items_to_extract, ok = QInputDialog.getItem(self, "Tracks to extract",
                                                    "Tracks",
                                                    ("Video and audio", "Only video", "Only audio"),
                                                    0, False)
        if not ok:
            return

        exportDir = QFileDialog().getExistingDirectory(self, "Choose a directory to extract events",
                                                           os.path.expanduser("~"),
                                                           options=QFileDialog(self).ShowDirsOnly)
        if not exportDir:
            return


        flagUnpairedEventFound = False

        cursor = db_functions.load_events_in_db(self.pj,
                                                parameters[SELECTED_SUBJECTS],
                                                selected_observations,
                                                parameters[SELECTED_BEHAVIORS],
                                                time_interval=TIME_FULL_OBS)

        ffmpeg_extract_command = ('"{ffmpeg_bin}" -i "{input_}" -y -ss {start} -to {stop} {codecs} '
                                  ' "{dir_}{sep}{obsId}_{player}_{subject}_{behavior}_{globalStart}'
                                  '-{globalStop}{extension}" ')

        try:
            for obsId in selected_observations:

                for nplayer in self.pj[OBSERVATIONS][obsId][FILE]:

                    if not self.pj[OBSERVATIONS][obsId][FILE][nplayer]:
                        continue

                    duration1 = []   # in seconds
                    for mediaFile in self.pj[OBSERVATIONS][obsId][FILE][nplayer]:
                        duration1.append(self.pj[OBSERVATIONS][obsId][MEDIA_INFO][LENGTH][mediaFile])

                    for subject in parameters[SELECTED_SUBJECTS]:

                        for behavior in parameters[SELECTED_BEHAVIORS]:

                            cursor.execute("SELECT occurence FROM events WHERE observation = ? AND subject = ? AND code = ?",
                                           (obsId, subject, behavior))
                            rows = [{"occurence": float2decimal(r["occurence"])} for r in cursor.fetchall()]

                            behavior_state = project_functions.event_type(behavior, self.pj[ETHOGRAM])
                            if STATE in behavior_state and len(rows) % 2:  # unpaired events
                                flagUnpairedEventFound = True
                                continue

                            for idx, row in enumerate(rows):

                                mediaFileIdx = [idx1 for idx1, x in enumerate(duration1)
                                                if row["occurence"] >= sum(duration1[0:idx1])][-1]

                                # check if media has video
                                try:
                                    if self.pj[OBSERVATIONS][obsId][MEDIA_INFO][HAS_VIDEO][self.pj[OBSERVATIONS][obsId][FILE][nplayer][mediaFileIdx]]:
                                        codecs = "-acodec copy -vcodec copy"
                                        # extract extension from video file
                                        extension = pathlib.Path(self.pj[OBSERVATIONS][obsId][FILE][nplayer][mediaFileIdx]).suffix
                                        if not extension:
                                            extension = ".mp4"
                                    else:
                                        codecs = "-vn"
                                        extension = ".wav"

                                        logging.debug(f"Media {self.pj[OBSERVATIONS][obsId][FILE][nplayer][mediaFileIdx]} does not have video")

                                except Exception:

                                    logging.debug(f"has_video not found for: {self.pj[OBSERVATIONS][obsId][FILE][nplayer][mediaFileIdx]}")

                                    continue

                                globalStart = Decimal("0.000") if row["occurence"] < timeOffset else round(
                                    row["occurence"] - timeOffset, 3)
                                start = round(row["occurence"]
                                              - timeOffset
                                              - float2decimal(sum(duration1[0:mediaFileIdx]))
                                              - self.pj[OBSERVATIONS][obsId][TIME_OFFSET],
                                              3)
                                if start < timeOffset:
                                    start = Decimal("0.000")

                                if POINT in behavior_state:

                                    globalStop = round(row["occurence"] + timeOffset, 3)

                                    stop = round(row["occurence"]
                                                 + timeOffset
                                                 - float2decimal(sum(duration1[0:mediaFileIdx]))
                                                 - self.pj[OBSERVATIONS][obsId][TIME_OFFSET],
                                                 3)

                                    ffmpeg_command = ffmpeg_extract_command.format(
                                        ffmpeg_bin=self.ffmpeg_bin,
                                        input_=project_functions.media_full_path(self.pj[OBSERVATIONS][obsId][FILE][nplayer][mediaFileIdx],
                                                                                 self.projectFileName),
                                        start=start,
                                        stop=stop,
                                        codecs=codecs,
                                        globalStart=globalStart,
                                        globalStop=globalStop,
                                        dir_=exportDir,
                                        sep=os.sep,
                                        obsId=utilities.safeFileName(obsId),
                                        player="PLAYER{}".format(nplayer),
                                        subject=utilities.safeFileName(subject),
                                        behavior=utilities.safeFileName(behavior),
                                        extension=extension)

                                    logging.debug(f"ffmpeg command: {ffmpeg_command}")

                                    p = subprocess.Popen(ffmpeg_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                                         shell=True)
                                    out, error = p.communicate()

                                if STATE in behavior_state:
                                    if idx % 2 == 0:

                                        # check if stop is on same media file
                                        if mediaFileIdx != [idx1 for idx1, x in enumerate(duration1)
                                                            if rows[idx + 1]["occurence"] >= sum(duration1[0:idx1])][-1]:
                                            response = dialog.MessageDialog(programName,
                                                                ("The event extends on 2 successive video. "
                                                                 " At the moment it is not possible to extract this type of event.<br>"),
                                                                [OK, "Abort"])
                                            if response == OK:
                                                continue
                                            if response == "Abort":
                                                return

                                        globalStop = round(rows[idx + 1]["occurence"] + timeOffset, 3)

                                        stop = round(rows[idx + 1]["occurence"] + timeOffset -
                                                     float2decimal(sum(duration1[0:mediaFileIdx])), 3)

                                        # check if start after length of media
                                        if start > self.pj[OBSERVATIONS][obsId][MEDIA_INFO][LENGTH][self.pj[OBSERVATIONS]
                                                                                                               [obsId][FILE]
                                                                                                               [nplayer]
                                                                                                               [mediaFileIdx]]:
                                            continue

                                        ffmpeg_command = ffmpeg_extract_command.format(
                                            ffmpeg_bin=self.ffmpeg_bin,
                                            input_=project_functions.media_full_path(self.pj[OBSERVATIONS][obsId][FILE][nplayer][mediaFileIdx],
                                                                                     self.projectFileName),
                                            start=start,
                                            stop=stop,
                                            codecs=codecs,
                                            globalStart=globalStart,
                                            globalStop=globalStop,
                                            dir_=exportDir,
                                            sep=os.sep,
                                            obsId=utilities.safeFileName(obsId),
                                            player=f"PLAYER{nplayer}",
                                            subject=utilities.safeFileName(subject),
                                            behavior=utilities.safeFileName(behavior),
                                            extension=extension)

                                        logging.debug("ffmpeg command: {}".format(ffmpeg_command))
                                        p = subprocess.Popen(ffmpeg_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                                             shell=True)
                                        out, error = p.communicate()

        except Exception:
            dialog.error_message("Error during subvideo extraction", sys.exc_info())


    def generate_wav_file_from_media(self):
        """
        extract wav from all media files loaded in player #1
        """

        # check temp dir for images from ffmpeg
        tmp_dir = self.ffmpeg_cache_dir if self.ffmpeg_cache_dir and os.path.isdir(self.ffmpeg_cache_dir) else tempfile.gettempdir()

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


    def show_sound_signal_widget(self, plot_type):
        """
        show spectrogram window if any
        """
        if plot_type not in ["waveform", "spectrogram"]:
            logging.critical("error on plot type")
            return

        if self.playerType == LIVE:
            QMessageBox.warning(self, programName, "The sound signal visualization is not available for live observations")
            return

        if self.playerType == VIEWER:
            QMessageBox.warning(self, programName, "The sound signal visualization is not available in <b>VIEW</b> mode")
            return

        if plot_type == "spectrogram":
            if hasattr(self, "spectro"):
                self.spectro.show()
            else:
                logging.debug("spectro show not OK")

                # remember if player paused
                if self.playerType == VLC and self.playMode == VLC:
                    flagPaused = self.dw_player[0].mediaListPlayer.get_state() == self.vlc_paused

                self.pause_video()

                if dialog.MessageDialog(programName, ("You choose to visualize the spectrogram during this observation.<br>"
                                                      "Spectrogram generation can take some time for long media, be patient"),
                                        [YES, NO]) == YES:

                    self.generate_wav_file_from_media()

                    tmp_dir = self.ffmpeg_cache_dir if self.ffmpeg_cache_dir and os.path.isdir(self.ffmpeg_cache_dir) else tempfile.gettempdir()

                    wav_file_path = pathlib.Path(tmp_dir) / pathlib.Path(
                        urllib.parse.unquote(url2path(self.dw_player[0].mediaplayer.get_media().get_mrl())) + ".wav"
                        ).name

                    self.spectro = plot_spectrogram_rt.Plot_spectrogram_RT()

                    self.spectro.setWindowFlags(Qt.WindowStaysOnTopHint)

                    self.spectro.interval = self.spectrogram_time_interval
                    self.spectro.cursor_color = "red"

                    r = self.spectro.load_wav(str(wav_file_path))
                    if "error" in r:
                        logging.warning(f"spectro_load_wav error: {r['error']}")
                        QMessageBox.warning(self, programName, f"Error in spectrogram generation: {r['error']}",
                                            QMessageBox.Ok | QMessageBox.Default,
                                            QMessageBox.NoButton)
                        del self.spectro
                        return

                    self.pj[OBSERVATIONS][self.observationId][VISUALIZE_SPECTROGRAM] = True
                    self.spectro.sendEvent.connect(self.signal_from_widget)
                    self.spectro.sb_freq_min.setValue(0)
                    self.spectro.sb_freq_max.setValue(int(self.spectro.frame_rate / 2))
                    self.spectro.show()
                    self.timer_sound_signal.start()

                if self.playerType == VLC and self.playMode == VLC and not flagPaused:
                    self.play_video()

        if plot_type == "waveform":
            if hasattr(self, "waveform"):
                self.waveform.show()
            else:
                logging.debug("waveform not shown")

                # remember if player paused
                if self.playerType == VLC and self.playMode == VLC:
                    flagPaused = self.dw_player[0].mediaListPlayer.get_state() == self.vlc_paused

                self.pause_video()

                if dialog.MessageDialog(programName, ("You choose to visualize the waveform during this observation.<br>"
                                                      "The waveform generation can take some time for long media, be patient"),
                                        [YES, NO]) == YES:

                    self.generate_wav_file_from_media()

                    tmp_dir = self.ffmpeg_cache_dir if self.ffmpeg_cache_dir and os.path.isdir(self.ffmpeg_cache_dir) else tempfile.gettempdir()

                    wav_file_path = pathlib.Path(tmp_dir) / pathlib.Path(
                        urllib.parse.unquote(url2path(self.dw_player[0].mediaplayer.get_media().get_mrl())) + ".wav"
                        ).name

                    self.waveform = plot_waveform_rt.Plot_waveform_RT()

                    self.waveform.setWindowFlags(Qt.WindowStaysOnTopHint)

                    self.waveform.interval = self.spectrogram_time_interval
                    self.waveform.cursor_color = "red"

                    r = self.waveform.load_wav(str(wav_file_path))
                    if "error" in r:
                        logging.warning(f"waveform_load_wav error: {r['error']}")
                        QMessageBox.warning(self, programName, f"Error in waveform generation: {r['error']}",
                                            QMessageBox.Ok | QMessageBox.Default,
                                            QMessageBox.NoButton)
                        del self.waveform
                        return

                    self.pj[OBSERVATIONS][self.observationId][VISUALIZE_WAVEFORM] = True
                    self.waveform.sendEvent.connect(self.signal_from_widget)
                    '''
                    self.waveform.sb_freq_min.setValue(0)
                    self.waveform.sb_freq_max.setValue(int(self.spectro.frame_rate / 2))
                    '''
                    self.waveform.show()
                    self.timer_sound_signal.start()

                if self.playerType == VLC and self.playMode == VLC and not flagPaused:
                    self.play_video()


    def show_waveform(self):
        """
        show waveform window if any
        """

        if self.playerType == LIVE:
            QMessageBox.warning(self, programName, "The waveform visualization is not available for live observations")
            return

        if self.playerType == VIEWER:
            QMessageBox.warning(self, programName, "The waveform visualization is not available in <b>VIEW</b> mode")
            return

        if hasattr(self, "waveform"):
            self.waveform.show()
        else:
            logging.debug("waveform not shown")

            # remember if player paused
            if self.playerType == VLC and self.playMode == VLC:
                flagPaused = self.dw_player[0].mediaListPlayer.get_state() == self.vlc_paused

            self.pause_video()

            if dialog.MessageDialog(programName, ("You choose to visualize the waveform during this observation.<br>"
                                                  "Spectrogram generation can take some time for long media, be patient"),
                                    [YES, NO]) == YES:

                self.generate_wav_file_from_media()

                tmp_dir = self.ffmpeg_cache_dir if self.ffmpeg_cache_dir and os.path.isdir(self.ffmpeg_cache_dir) else tempfile.gettempdir()

                wav_file_path = pathlib.Path(tmp_dir) / pathlib.Path(
                    urllib.parse.unquote(url2path(self.dw_player[0].mediaplayer.get_media().get_mrl())) + ".wav"
                    ).name

                self.waveform = plot_waveform_rt.Plot_waveform_RT()

                self.waveform.setWindowFlags(Qt.WindowStaysOnTopHint)

                self.waveform.interval = self.spectrogram_time_interval
                self.waveform.cursor_color = "red"

                r = self.waveform.load_wav(str(wav_file_path))
                if "error" in r:
                    logging.warning("waveform_load_wav error: {}".format(r["error"]))
                    QMessageBox.warning(self, programName, "Error in waveform generation: " + r["error"],
                                        QMessageBox.Ok | QMessageBox.Default,
                                        QMessageBox.NoButton)
                    del self.waveform
                    return

                self.pj[OBSERVATIONS][self.observationId][VISUALIZE_SPECTROGRAM] = True
                self.waveform.sendEvent.connect(self.signal_from_widget)
                '''
                self.waveform.sb_freq_min.setValue(0)
                self.waveform.sb_freq_max.setValue(int(self.spectro.frame_rate / 2))
                '''
                self.waveform.show()
                self.timer_waveform.start()

            if self.playerType == VLC and self.playMode == VLC and not flagPaused:
                self.play_video()


    def timer_sound_signal_out(self):
        """
        timer for sound signal visualization: spectrogram and/or waveform
        """

        '''
        if (VISUALIZE_SPECTROGRAM not in self.pj[OBSERVATIONS][self.observationId] or
                not self.pj[OBSERVATIONS][self.observationId][VISUALIZE_SPECTROGRAM]):
            return
        '''

        if self.playerType == LIVE:
            QMessageBox.warning(self, programName, "The sound signal visualization is not available for live observations")
            return

        if self.playerType == VLC:
            if self.playMode == VLC:
                current_media_time = self.dw_player[0].mediaplayer.get_time() / 1000

            if self.playMode == FFMPEG:
                # get time in current media
                currentMedia, frameCurrentMedia = self.getCurrentMediaByFrame(PLAYER1, self.FFmpegGlobalFrame,
                                                                              self.fps)
                current_media_time = float(frameCurrentMedia / self.fps)

            tmp_dir = self.ffmpeg_cache_dir if self.ffmpeg_cache_dir and os.path.isdir(self.ffmpeg_cache_dir) else tempfile.gettempdir()

            wav_file_path = str(pathlib.Path(tmp_dir) / pathlib.Path(self.dw_player[0].mediaplayer.get_media().get_mrl() + ".wav").name)

            # waveform
            if self.pj[OBSERVATIONS][self.observationId].get(VISUALIZE_WAVEFORM, False):

                if not hasattr(self, "waveform"):
                    return

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
            QMessageBox.warning(self, programName, "No project found",
                                QMessageBox.Ok | QMessageBox.Default,
                                QMessageBox.NoButton)
            return

        if "behaviors_coding_map" not in self.pj:
            self.pj["behaviors_coding_map"] = []

        if [bcm for bcm in self.pj["behaviors_coding_map"] if bcm["name"] == behav_coding_map["name"]]:
            QMessageBox.critical(self, programName, ("The current project already contains a behaviors coding map "
                                                     f"with the same name (<b>{behav_coding_map['name']}</b>)"),
                                 QMessageBox.Ok | QMessageBox.Default,
                                 QMessageBox.NoButton)
            return

        self.pj["behaviors_coding_map"].append(behav_coding_map)
        QMessageBox.information(self, programName,
                                f"The behaviors coding map <b>{behav_coding_map['name']}</b> was added to current project")
        self.projectChanged = True


    def behaviors_coding_map_creator(self):
        """
        show behaviors coding map creator window
        """

        if not self.project:
            QMessageBox.warning(self, programName, "No project found",
                                QMessageBox.Ok | QMessageBox.Default,
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
                    if not self.initialize_new_observation_vlc():
                        self.observationId = ""
                        self.twEvents.setRowCount(0)
                        self.menu_options()
                        return "Error: loading observation problem"

                if mode == "view":
                    self.playerType = VIEWER
                    self.playMode = ""
                    self.dwObservations.setVisible(True)

            self.menu_options()
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
            if dialog.MessageDialog(programName,
                                    "The current observation will be closed. Do you want to continue?",
                                    [YES, NO]) == NO:
                self.show_data_files()
                return
            else:
                self.close_observation()

        result, selected_observations = self.selectObservations(EDIT)

        if selected_observations:
            self.new_observation(mode=EDIT, obsId=selected_observations[0])


    def check_state_events(self, mode="all"):
        """
        check state events for each subject
        use check_state_events_obs function in project_functions.py

        Args:
            mode (str): current: check current observation / all: ask user to select observations
        """

        tot_out = ""
        if mode == "current":
            if self.observationId:
                r, msg = project_functions.check_state_events_obs(self.observationId, self.pj[ETHOGRAM],
                                                                  self.pj[OBSERVATIONS][self.observationId], self.timeFormat)
                tot_out = f"Observation: <strong>{self.observationId}</strong><br>{msg}<br><br>"

        if mode == "all":
            if not self.pj[OBSERVATIONS]:
                QMessageBox.warning(self, programName, "The project does not contain any observation",
                                    QMessageBox.Ok | QMessageBox.Default,
                                    QMessageBox.NoButton)
                return

            # ask user observations to analyze
            _, selectedObservations = self.selectObservations(MULTIPLE)
            if not selectedObservations:
                return

            for obsId in sorted(selectedObservations):
                r, msg = project_functions.check_state_events_obs(obsId, self.pj[ETHOGRAM],
                                                                  self.pj[OBSERVATIONS][obsId], self.timeFormat)

                tot_out += f"<strong>{obsId}</strong><br>{msg}<br>"

        results = dialog.Results_dialog()
        results.setWindowTitle("Check state events")
        results.ptText.clear()
        results.ptText.setReadOnly(True)
        results.ptText.appendHtml(tot_out)
        results.exec_()


    def fix_unpaired_events(self):
        """
        fix unpaired state events
        """

        if self.observationId:

            r, msg = project_functions.check_state_events_obs(self.observationId, self.pj[ETHOGRAM],
                                                              self.pj[OBSERVATIONS][self.observationId])
            if "not PAIRED" not in msg:
                QMessageBox.information(self, programName, "All state events are already paired",
                                        QMessageBox.Ok | QMessageBox.Default, QMessageBox.NoButton)
                return

            w = dialog.Ask_time(self.timeFormat)
            w.setWindowTitle("Fix UNPAIRED state events")
            w.label.setText("Fix UNPAIRED events at time")

            if w.exec_():
                fix_at_time = w.time_widget.get_time()

                events_to_add = project_functions.fix_unpaired_state_events(
                    self.observationId,
                    self.pj[ETHOGRAM],
                    self.pj[OBSERVATIONS][self.observationId],
                    fix_at_time - Decimal("0.001"))

                if events_to_add:
                    self.pj[OBSERVATIONS][self.observationId][EVENTS].extend(events_to_add)
                    self.projectChanged = True
                    self.pj[OBSERVATIONS][self.observationId][EVENTS].sort()
                    self.loadEventsInTW(self.observationId)
                    item = self.twEvents.item([i for i, t in enumerate(self.pj[OBSERVATIONS][self.observationId][EVENTS])
                                               if t[0] == fix_at_time][0], 0)
                    self.twEvents.scrollToItem(item)

        # selected observations
        else:
            result, selected_observations = self.selectObservations(MULTIPLE)
            if not selected_observations:
                return

            # check if state events are paired
            out = ""
            not_paired_obs_list = []
            for obs_id in selected_observations:
                r, msg = project_functions.check_state_events_obs(obs_id, self.pj[ETHOGRAM],
                                                                  self.pj[OBSERVATIONS][obs_id])
                if "NOT PAIRED" in msg.upper():
                    fix_at_time = max(x[0] for x in self.pj[OBSERVATIONS][obs_id][EVENTS])
                    events_to_add = project_functions.fix_unpaired_state_events(obs_id,
                                                                                self.pj[ETHOGRAM],
                                                                                self.pj[OBSERVATIONS][obs_id],
                                                                                fix_at_time)
                    if events_to_add:
                        events_backup = self.pj[OBSERVATIONS][obs_id][EVENTS][:]
                        self.pj[OBSERVATIONS][obs_id][EVENTS].extend(events_to_add)

                        # check if modified obs if fixed
                        r, msg = project_functions.check_state_events_obs(obs_id, self.pj[ETHOGRAM],
                                                                          self.pj[OBSERVATIONS][obs_id])
                        if "NOT PAIRED" in msg.upper():
                            out += f"The observation <b>{obs_id}</b> can not be automatically fixed.<br><br>"
                            self.pj[OBSERVATIONS][obs_id][EVENTS] = events_backup
                        else:
                            out += f"<b>{obs_id}</b><br>"
                            self.projectChanged = True
            if out:
                out = "The following observations were modified to fix the unpaired state events:<br><br>" + out
                self.results = dialog.Results_dialog()
                self.results.setWindowTitle(programName + " - Fixed observations")
                self.results.ptText.setReadOnly(True)
                self.results.ptText.appendHtml(out)
                self.results.pbSave.setVisible(False)
                self.results.pbCancel.setVisible(True)
                self.results.exec_()
            else:
                QMessageBox.information(self, programName, "All state events are already paired",
                                        QMessageBox.Ok | QMessageBox.Default, QMessageBox.NoButton)


    def observations_list(self):
        """
        show list of all observations of current project
        """

        if self.playerType == VIEWER:
            self.close_observation()
        # check if an observation is running
        if self.observationId:
            # hide data plot
            self.hide_data_files()
            if dialog.MessageDialog(programName, "The current observation will be closed. Do you want to continue?",
                                    [YES, NO]) == NO:

                self.show_data_files()
                return
            else:
                self.close_observation()

        result, selected_obs = self.selectObservations(SINGLE)

        if selected_obs:
            if result == OPEN:
                self.load_observation(selected_obs[0], "start")

            if result == VIEW:
                self.load_observation(selected_obs[0], VIEW)

            if result == EDIT:
                if self.observationId != selected_obs[0]:
                    self.new_observation(mode=EDIT, obsId=selected_obs[0])   # observation id to edit
                else:
                    QMessageBox.warning(self, programName,
                                        (f"The observation <b>{self.observationId}</b> is running!<br>"
                                         "Close it before editing."))


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
            self.saveConfigFile(lastCheckForNewVersion=int(time.mktime(time.localtime())))
            QMessageBox.information(self, programName, msg)
            if news:
                QMessageBox.information(self, programName, news)
        except Exception:
            QMessageBox.warning(self, programName, "Can not check for updates...")


    def seek_mediaplayer(self, new_time: int, player=0):
        """
        change media position in player

        Args:
            new_time (int): time in milliseconds

        """
        logging.debug(f"seek mediaplayer in player #{player} to {new_time}")
        logging.debug(f"self.dw_player[player].mediaplayer.get_state() #{player} {self.dw_player[player].mediaplayer.get_state()}")


        if sys.platform != "darwin":  # for MacOS
            if self.dw_player[player].mediaListPlayer.get_state() == self.vlc_ended:
                # if video is stopped play and pause it
                self.dw_player[player].mediaListPlayer.play()
                time.sleep(0.5)

                logging.debug(f"self.dw_player[player].mediaListPlayer.get_state() #{player} {self.dw_player[player].mediaListPlayer.get_state()}")

                while True:
                    if self.dw_player[player].mediaListPlayer.get_state() == self.vlc_playing:
                        break

                logging.debug(f"after play self.dw_player[player].mediaListPlayer.get_state() #{player} {self.dw_player[player].mediaListPlayer.get_state()}")

                self.dw_player[player].mediaListPlayer.pause()
                while True:
                    if self.dw_player[player].mediaListPlayer.get_state() == self.vlc_paused:
                        break
                logging.debug(f"after pause self.dw_player[player].mediaListPlayer.get_state() #{player} {self.dw_player[player].mediaListPlayer.get_state()}")

        flag_paused = (self.dw_player[player].mediaListPlayer.get_state() in [self.vlc_paused, self.vlc_ended])

        logging.debug(f"paused? {flag_paused}")

        if self.dw_player[player].media_list.count() == 1:

            if new_time < self.dw_player[player].mediaplayer.get_length():
                self.dw_player[player].stack.setCurrentIndex(0)
                self.dw_player[player].mediaplayer.set_time(new_time)

                if sys.platform != "darwin":  # for MacOS
                    if flag_paused:

                        logging.debug(f"play")

                        self.dw_player[player].mediaListPlayer.play()
                        while True:
                            if self.dw_player[player].mediaListPlayer.get_state() in [self.vlc_playing, self.vlc_ended]:
                                break

                        logging.debug(f"time sleep")

                        time.sleep(0.2)
                        self.dw_player[player].mediaplayer.set_time(new_time)

                        self.dw_player[player].mediaListPlayer.pause()

                        logging.debug(f"pause")

                        while True:
                            if self.dw_player[player].mediaListPlayer.get_state() in [self.vlc_paused, self.vlc_ended]:
                                break

                        logging.debug(f"set new time")

                        self.dw_player[player].mediaplayer.set_time(new_time)

                if player == 0:
                    try:
                        self.video_slider.setValue(self.dw_player[0].mediaplayer.get_time() / self.dw_player[0].mediaplayer.get_length() * (slider_maximum - 1))
                    except Exception:
                        pass
                        #dialog.error_message("set video slider value", sys.exc_info())

            else:
                self.dw_player[player].stack.setCurrentIndex(1)
                '''
                QMessageBox.warning(self, programName,
                                    ("The indicated position is behind the end of media "
                                     f"({seconds2time(self.dw_player[player].mediaplayer.get_length() / 1000)})"))
                '''

        elif self.dw_player[player].media_list.count() > 1:

            if new_time < sum(self.dw_player[player].media_durations):
                self.dw_player[player].stack.setCurrentIndex(0)

                # remember if player paused (go previous will start playing)
                flagPaused = self.dw_player[player].mediaListPlayer.get_state() == self.vlc_paused

                tot = 0
                for idx, d in enumerate(self.dw_player[player].media_durations):
                    if new_time >= tot and new_time < tot + d:
                        self.dw_player[player].mediaListPlayer.play_item_at_index(idx)
                        time.sleep(0.2)
                        # wait until media is played
                        while True:
                            if self.dw_player[player].mediaListPlayer.get_state() in [self.vlc_playing, self.vlc_ended]:
                                break
                        time.sleep(0.2)
                        self.dw_player[player].mediaplayer.set_time(
                            new_time - sum(
                                self.dw_player[player].media_durations[0: self.dw_player[player].media_list.index_of_item(
                                    self.dw_player[player].mediaplayer.get_media())]))

                        if sys.platform != "darwin":  # for MacOS
                            if flagPaused:
                                time.sleep(0.2)
                                self.dw_player[player].mediaListPlayer.pause()
                                while True:
                                    if self.dw_player[player].mediaListPlayer.get_state() in [self.vlc_paused, self.vlc_ended]:
                                        break
                                self.dw_player[player].mediaplayer.set_time(
                                    new_time
                                    - sum(
                                        self.dw_player[player].media_durations[
                                            0 : self.dw_player[player].media_list.index_of_item(self.dw_player[player].mediaplayer.get_media())
                                        ]
                                    )
                                )

                        break
                    tot += d
                if player == 0:
                    try:
                        self.video_slider.setValue(self.dw_player[0].mediaplayer.get_time() / self.dw_player[0].mediaplayer.get_length() * (slider_maximum - 1))
                    except Exception:
                        pass
                        #dialog.error_message("set video slider value", sys.exc_info())

            else:
                self.dw_player[player].stack.setCurrentIndex(1)
                '''
                QMessageBox.warning(self, programName,
                                    ("The indicated position is behind the total media duration "
                                     f"({seconds2time(sum(self.dw_player[player].media_durations) / 1000)})"))
                '''


    def jump_to(self):
        """
        jump to the user specified media position
        """

        jt = dialog.Ask_time(self.timeFormat)
        jt.setWindowTitle("Jump to specific time")
        jt.time_widget.set_time(0)

        if jt.exec_():
            newTime = int(jt.time_widget.get_time() * 1000)
            if newTime < 0:
                return

            if self.playerType == VLC:
                if self.playMode == FFMPEG:
                    frameDuration = Decimal(1000 / self.fps)
                    currentFrame = round(newTime / frameDuration)
                    self.FFmpegGlobalFrame = currentFrame

                    if self.FFmpegGlobalFrame > 0:
                        self.FFmpegGlobalFrame -= 1
                    self.ffmpeg_timer_out()

                elif self.playMode == VLC:  # play mode VLC

                    self.seek_mediaplayer(newTime)

                    self.update_visualizations()


    def previous_media_file(self):
        """
        go to previous media file (if any)
        """
        if len(self.pj[OBSERVATIONS][self.observationId][FILE][PLAYER1]) == 1:
            return

        if self.playerType == VLC:

            if self.playMode == FFMPEG:

                currentMedia = ""
                for idx, media in enumerate(self.pj[OBSERVATIONS][self.observationId][FILE][PLAYER1]):
                    if self.FFmpegGlobalFrame < self.dw_player[0].media_durations[idx + 1]:
                        self.FFmpegGlobalFrame = self.dw_player[0].media_durations[idx - 1]
                        break
                self.FFmpegGlobalFrame -= 1
                self.ffmpeg_timer_out()

            elif self.playMode == VLC:

                # check if media not first media
                if self.dw_player[0].media_list.index_of_item(self.dw_player[0].mediaplayer.get_media()) > 0:

                    # remember if player paused (go previous will start playing)
                    flagPaused = self.dw_player[0].mediaListPlayer.get_state() == self.vlc_paused
                    self.dw_player[0].mediaListPlayer.previous()

                    while True:
                        if self.dw_player[0].mediaListPlayer.get_state() in [self.vlc_playing, self.vlc_ended]:
                            break

                    if flagPaused:
                        self.dw_player[0].mediaListPlayer.pause()
                else:

                    if self.dw_player[0].media_list.count() == 1:
                        self.statusbar.showMessage("There is only one media file", 5000)
                    else:
                        if self.dw_player[0].media_list.index_of_item(self.dw_player[0].mediaplayer.get_media()) == 0:
                            self.statusbar.showMessage("The first media is playing", 5000)

                self.update_visualizations()

                # subtitles
                st_track_number = 0 if self.config_param[DISPLAY_SUBTITLES] else -1
                for player in self.dw_player:
                    player.mediaplayer.video_set_spu(st_track_number)

            if hasattr(self, "spectro"):
                self.spectro.memChunk = -1


    def next_media_file(self):
        """
        go to next media file (if any) in first player
        """

        if len(self.pj[OBSERVATIONS][self.observationId][FILE][PLAYER1]) == 1:
            return

        if self.playerType == VLC:

            if self.playMode == FFMPEG:
                for idx, media in enumerate(self.pj[OBSERVATIONS][self.observationId][FILE][PLAYER1]):
                    if self.FFmpegGlobalFrame < self.dw_player[0].media_durations[idx + 1]:
                        self.FFmpegGlobalFrame = self.dw_player[0].media_durations[idx + 1]
                        break
                self.FFmpegGlobalFrame -= 1
                self.ffmpeg_timer_out()

            elif self.playMode == VLC:

                # check if media not last media
                if (self.dw_player[0].media_list.index_of_item(self.dw_player[0].mediaplayer.get_media()) <
                        len(self.pj[OBSERVATIONS][self.observationId][FILE][PLAYER1]) - 1):

                    # remember if player paused (go previous will start playing)
                    flagPaused = self.dw_player[0].mediaListPlayer.get_state() == self.vlc_paused

                    self.dw_player[0].mediaListPlayer.next()

                    # wait until media is played
                    while True:
                        if self.dw_player[0].mediaListPlayer.get_state() in [self.vlc_playing, self.vlc_ended]:
                            break

                    if flagPaused:
                        logging.info("media player state: {0}".format(self.dw_player[0].mediaListPlayer.get_state()))
                        self.dw_player[0].mediaListPlayer.pause()

                else:
                    if self.dw_player[0].media_list.count() == 1:
                        self.statusbar.showMessage("There is only one media file", 5000)
                    else:
                        if (self.dw_player[0].media_list.index_of_item(self.dw_player[0].mediaplayer.get_media()) ==
                                self.dw_player[0].media_list.count() - 1):
                            self.statusbar.showMessage("The last media is playing", 5000)

                self.update_visualizations()

            if hasattr(self, "spectro"):
                self.spectro.memChunk = -1


    def setVolume(self, nplayer, new_volume):
        """
        set volume for player

        Args:
            nplayer (str): player to set
            new_volume (int): volume to set
        """
        self.dw_player[nplayer].mediaplayer.audio_set_volume(new_volume)


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
            self.timer_out()
        except Exception:
            logging.critical("error in update_subject function")


    def preferences(self):
        """
        show preferences window
        """

        try:
            preferencesWindow = preferences.Preferences()
            preferencesWindow.tabWidget.setCurrentIndex(0)

            if self.timeFormat == S:
                preferencesWindow.cbTimeFormat.setCurrentIndex(0)

            if self.timeFormat == HHMMSS:
                preferencesWindow.cbTimeFormat.setCurrentIndex(1)

            preferencesWindow.sbffSpeed.setValue(self.fast)
            preferencesWindow.cb_adapt_fast_jump.setChecked(self.config_param.get(ADAPT_FAST_JUMP, False))
            preferencesWindow.sbRepositionTimeOffset.setValue(self.repositioningTimeOffset)
            preferencesWindow.sbSpeedStep.setValue(self.play_rate_step)
            # automatic backup
            preferencesWindow.sbAutomaticBackup.setValue(self.automaticBackup)
            # separator for behavioural strings
            preferencesWindow.leSeparator.setText(self.behaviouralStringsSeparator)
            # close same event indep of modifiers
            preferencesWindow.cbCloseSameEvent.setChecked(self.close_the_same_current_event)
            # confirm sound
            preferencesWindow.cbConfirmSound.setChecked(self.confirmSound)
            # beep every
            preferencesWindow.sbBeepEvery.setValue(self.beep_every)
            # alert no focal subject
            preferencesWindow.cbAlertNoFocalSubject.setChecked(self.alertNoFocalSubject)
            # tracking cursor above event
            preferencesWindow.cbTrackingCursorAboveEvent.setChecked(self.trackingCursorAboveEvent)
            # check for new version
            preferencesWindow.cbCheckForNewVersion.setChecked(self.checkForNewVersion)
            # display subtitles
            preferencesWindow.cb_display_subtitles.setChecked(self.config_param[DISPLAY_SUBTITLES])
            # pause before add event
            preferencesWindow.cb_pause_before_addevent.setChecked(self.pause_before_addevent)

            preferencesWindow.cb_compact_time_budget.setChecked(self.config_param.get(TIME_BUDGET_FORMAT,
                                                                                      DEFAULT_TIME_BUDGET_FORMAT) == COMPACT_TIME_BUDGET_FORMAT)

            # FFmpeg for frame by frame mode
            preferencesWindow.lbFFmpegPath.setText(f"FFmpeg path: {self.ffmpeg_bin}")
            preferencesWindow.leFFmpegCacheDir.setText(self.ffmpeg_cache_dir)
            preferencesWindow.sbFFmpegCacheDirMaxSize.setValue(self.ffmpeg_cache_dir_max_size)

            # frame-by-frame mode
            if self.config_param.get(SAVE_FRAMES, DEFAULT_FRAME_MODE) == MEMORY:
                preferencesWindow.rb_save_frames_in_mem.setChecked(True)
            if self.config_param.get(SAVE_FRAMES, DEFAULT_FRAME_MODE) == DISK:
                preferencesWindow.rb_save_frames_on_disk.setChecked(True)
            for w in [preferencesWindow.lb_memory_frames, preferencesWindow.sb_frames_memory_size, preferencesWindow.lb_memory_info]:
                w.setEnabled(preferencesWindow.rb_save_frames_in_mem.isChecked())
            for w in [preferencesWindow.lb_storage_dir]:
                w.setEnabled(preferencesWindow.rb_save_frames_on_disk.isChecked())

            preferencesWindow.sb_frames_memory_size.setValue(self.config_param.get(MEMORY_FOR_FRAMES, DEFAULT_MEMORY_FOR_FRAMES))

            r, mem = utilities.mem_info()
            if not r:
                preferencesWindow.lb_memory_info.setText((f"Total memory: {mem.get('total_memory', 'Not available')} Mb"
                                                          f"<br>Free memory: {mem.get('free_memory', 'Not available')} Mb"))
            else:
                preferencesWindow.lb_memory_info.setText("Memory information not available")

            # frames buffer
            preferencesWindow.lb_memory_info.setText((f"{preferencesWindow.lb_memory_info.text()} "
                                                      f"<br>Frames buffer size {self.frames_buffer.size()/1024/1024:.1f} Mb"
                                                     )
                                                    )

            preferencesWindow.sbFrameResize.setValue(self.frame_resize)
            mem_frame_resize = self.frame_resize
            # frame-by-frame cache size (in seconds)
            preferencesWindow.sb_fbf_cache_size.setValue(self.fbf_cache_size)

            preferencesWindow.cbFrameBitmapFormat.clear()
            preferencesWindow.cbFrameBitmapFormat.addItems(FRAME_BITMAP_FORMAT_LIST)

            try:
                preferencesWindow.cbFrameBitmapFormat.setCurrentIndex(FRAME_BITMAP_FORMAT_LIST.index(self.frame_bitmap_format))
            except Exception:
                preferencesWindow.cbFrameBitmapFormat.setCurrentIndex(FRAME_BITMAP_FORMAT_LIST.index(FRAME_DEFAULT_BITMAP_FORMAT))

            # spectrogram
            preferencesWindow.cbSpectrogramColorMap.clear()
            preferencesWindow.cbSpectrogramColorMap.addItems(SPECTROGRAM_COLOR_MAPS)
            try:
                preferencesWindow.cbSpectrogramColorMap.setCurrentIndex(SPECTROGRAM_COLOR_MAPS.index(self.spectrogram_color_map))
            except Exception:
                preferencesWindow.cbSpectrogramColorMap.setCurrentIndex(SPECTROGRAM_COLOR_MAPS.index(SPECTROGRAM_DEFAULT_COLOR_MAP))

            try:
                preferencesWindow.cbSpectrogramColorMap.setCurrentIndex(SPECTROGRAM_COLOR_MAPS.index(self.spectrogram_color_map))
            except Exception:
                preferencesWindow.cbSpectrogramColorMap.setCurrentIndex(SPECTROGRAM_COLOR_MAPS.index(SPECTROGRAM_DEFAULT_COLOR_MAP))

            try:
                preferencesWindow.sb_time_interval.setValue(self.spectrogram_time_interval)
            except Exception:
                preferencesWindow.sb_time_interval.setValue(SPECTROGRAM_DEFAULT_TIME_INTERVAL)

            # plot colors
            if not self.plot_colors:
                self.plot_colors = BEHAVIORS_PLOT_COLORS
            preferencesWindow.te_plot_colors.setPlainText("\n".join(self.plot_colors))

            gui_utilities.restore_geometry(preferencesWindow, "preferences", (700, 500))

            if preferencesWindow.exec_():

                gui_utilities.save_geometry(preferencesWindow, "preferences")

                if preferencesWindow.flag_refresh:
                    # refresh preferences remove the config file

                    logging.debug("flag refresh ")

                    self.config_param["refresh_preferences"] = True
                    self.close()
                    # check if refresh canceled for not saved project
                    if "refresh_preferences" in self.config_param:
                        if (pathlib.Path.home() / ".boris").exists():
                            os.remove(pathlib.Path.home() / ".boris")
                        sys.exit()

                if preferencesWindow.cbTimeFormat.currentIndex() == 0:
                    self.timeFormat = S

                if preferencesWindow.cbTimeFormat.currentIndex() == 1:
                    self.timeFormat = HHMMSS

                self.fast = preferencesWindow.sbffSpeed.value()

                self.config_param[ADAPT_FAST_JUMP] = preferencesWindow.cb_adapt_fast_jump.isChecked()

                self.repositioningTimeOffset = preferencesWindow.sbRepositionTimeOffset.value()

                self.play_rate_step = preferencesWindow.sbSpeedStep.value()

                self.automaticBackup = preferencesWindow.sbAutomaticBackup.value()
                if self.automaticBackup:
                    self.automaticBackupTimer.start(self.automaticBackup * 60000)
                else:
                    self.automaticBackupTimer.stop()

                self.behaviouralStringsSeparator = preferencesWindow.leSeparator.text()

                self.close_the_same_current_event = preferencesWindow.cbCloseSameEvent.isChecked()

                self.confirmSound = preferencesWindow.cbConfirmSound.isChecked()

                self.beep_every = preferencesWindow.sbBeepEvery.value()

                self.alertNoFocalSubject = preferencesWindow.cbAlertNoFocalSubject.isChecked()

                self.trackingCursorAboveEvent = preferencesWindow.cbTrackingCursorAboveEvent.isChecked()

                self.checkForNewVersion = preferencesWindow.cbCheckForNewVersion.isChecked()

                self.config_param[DISPLAY_SUBTITLES] = preferencesWindow.cb_display_subtitles.isChecked()
                st_track_number = 0 if self.config_param[DISPLAY_SUBTITLES] else -1
                for player in self.dw_player:
                    player.mediaplayer.video_set_spu(st_track_number)

                self.pause_before_addevent = preferencesWindow.cb_pause_before_addevent.isChecked()

                if self.observationId:
                    self.loadEventsInTW(self.observationId)
                    self.display_statusbar_info(self.observationId)

                # result
                if preferencesWindow.cb_compact_time_budget.isChecked():
                    self.config_param[TIME_BUDGET_FORMAT] = COMPACT_TIME_BUDGET_FORMAT
                else:
                    self.config_param[TIME_BUDGET_FORMAT] = DEFAULT_TIME_BUDGET_FORMAT

                self.ffmpeg_cache_dir = preferencesWindow.leFFmpegCacheDir.text()
                self.ffmpeg_cache_dir_max_size = preferencesWindow.sbFFmpegCacheDirMaxSize.value()

                # frame-by-frame
                if preferencesWindow.flag_reset_frames_memory:
                    self.initialize_frames_buffer()
                self.config_param[SAVE_FRAMES] = DEFAULT_FRAME_MODE
                if preferencesWindow.rb_save_frames_in_mem.isChecked():
                    self.config_param[SAVE_FRAMES] = MEMORY
                if preferencesWindow.rb_save_frames_on_disk.isChecked():
                    self.config_param[SAVE_FRAMES] = DISK
                self.config_param[MEMORY_FOR_FRAMES] = preferencesWindow.sb_frames_memory_size.value()
                if self.frames_buffer.size() / 1048576 > self.config_param[MEMORY_FOR_FRAMES]:
                    self.initialize_frames_buffer()

                self.frame_resize = preferencesWindow.sbFrameResize.value()

                # clear frames memory cache if frames saved on disk
                if self.config_param.get(SAVE_FRAMES, DEFAULT_FRAME_MODE) == DISK:
                    self.initialize_frames_buffer()

                # frames cache
                # clear cache (mem or files) if frame_resize changed
                if self.frame_resize != mem_frame_resize:

                    if self.config_param.get(SAVE_FRAMES, DEFAULT_FRAME_MODE) == MEMORY:
                        self.initialize_frames_buffer()

                    if self.config_param.get(SAVE_FRAMES, DEFAULT_FRAME_MODE) == DISK:
                        # check temp dir for images from ffmpeg
                        self.imageDirectory = self.ffmpeg_cache_dir if self.ffmpeg_cache_dir and os.path.isdir(self.ffmpeg_cache_dir) else tempfile.gettempdir()

                        for f in [x for x in os.listdir(self.imageDirectory)
                                if "BORIS@" in x and os.path.isfile(self.imageDirectory + os.sep + x)]:
                            try:
                                os.remove(self.imageDirectory + os.sep + f)
                            except Exception:
                                pass

                self.frame_bitmap_format = preferencesWindow.cbFrameBitmapFormat.currentText()

                # frame-by-frame cache size (in seconds)
                self.fbf_cache_size = preferencesWindow.sb_fbf_cache_size.value()

                # spectrogram
                self.spectrogram_color_map = preferencesWindow.cbSpectrogramColorMap.currentText()
                # self.spectrogramHeight = preferencesWindow.sbSpectrogramHeight.value()
                self.spectrogram_time_interval = preferencesWindow.sb_time_interval.value()

                if self.playMode == FFMPEG:
                    self.FFmpegGlobalFrame -= 1
                    self.ffmpeg_timer_out()

                # plot colors
                self.plot_colors = preferencesWindow.te_plot_colors.toPlainText().split()

                self.menu_options()

                self.saveConfigFile()

        except Exception:
            dialog.error_message("Error ", sys.exc_info())


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
                frameCurrentMedia = requiredFrame - sum(self.dw_player[int(player) - 1].media_durations[0:idx]) / frameMs
                break
        return currentMedia, round(frameCurrentMedia)


    def extract_frames_mem(self,
                           start_frame: int,
                           second: float,
                           current_media_path,
                           fps: float,
                           resolution: tuple,
                           bitmap_format: str,
                           frame_resize: int,
                           number_of_seconds: int,
                           bitmap_quality: int = 100) -> dict:

        """
        extract frames from video to a QBuffer and save references (start and size) in dictionary
        """

        def toQImage(frame, copy=False):
            if frame is None:
                return QImage()
            im = np.asarray(frame)
            return QImage(im.data, im.shape[1], im.shape[0], im.strides[0], QImage.Format_RGB888)

        try:
            new_h_resolution, new_v_resolution = resolution

            command = [self.ffmpeg_bin,
                        '-i', current_media_path,
                        "-ss", str((start_frame - 1) / fps),
                        '-vframes', str(int(fps * number_of_seconds)),
                        '-vf', f'scale={new_h_resolution}:-1',
                        '-f', 'image2pipe',
                        '-pix_fmt', 'rgb24',
                        '-vcodec', 'rawvideo', '-']

            pipe = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=10**8)

            # go to buffer end
            self.frames_buffer.seek(self.frames_buffer.size())
            frame_idx = start_frame
            while True:
                raw_image = pipe.stdout.read(new_v_resolution * new_h_resolution * 3)
                if not raw_image:
                    return False, ""
                if frame_idx in self.frames_cache[current_media_path]:
                    frame_idx += 1
                    continue
                np_array = np.fromstring(raw_image, dtype="uint8").reshape((new_v_resolution, new_h_resolution, 3))
                qimage = toQImage(np_array)
                pixmap = QPixmap.fromImage(qimage)
                '''
                pixmap = QPixmap.fromImage(toQImage(np.fromstring(raw_image, dtype="uint8").reshape((new_v_resolution, new_h_resolution, 3))))
                '''
                start = self.frames_buffer.pos()

                pixmap.save(self.frames_buffer, bitmap_format, bitmap_quality)

                self.frames_cache[current_media_path][frame_idx] = (start, self.frames_buffer.size() - start)
                frame_idx += 1

        except Exception:

            error_type, error_file_name, error_lineno = utilities.error_info(sys.exc_info())
            logging.critical(f"Error during frame extraction: {error_type} {error_file_name} {error_lineno}")
            return True, sys.exc_info()


    def initialize_frames_buffer(self):
        """
        initialize the memory buffer for saving frames
        """
        self.frames_buffer = QBuffer()
        self.frames_buffer.open(QIODevice.ReadWrite)
        self.frames_cache = {}


    def ffmpeg_timer_out(self):
        """
        triggered when frame-by-frame mode is activated:
        read next frame and update image
        frames are read from disk or from memory
        """

        logging.debug("ffmpeg_timer_out function")
        logging.debug(f"fps {self.fps}")

        frameMs = 1000 / self.fps

        logging.debug(f"frame Ms {frameMs}")

        requiredFrame = self.FFmpegGlobalFrame + 1

        logging.debug(f"required frame 1: {requiredFrame}")
        logging.debug(f"sum self.duration1 {sum(self.dw_player[0].media_durations)}")

        # check if end of last media
        if requiredFrame * frameMs >= sum(self.dw_player[0].media_durations):

            logging.debug(f"end of last media 1 frame: {requiredFrame}")

            return

        for i, player in enumerate(self.dw_player):

            n_player = str(i + 1)

            if (n_player not in self.pj[OBSERVATIONS][self.observationId][FILE]
               or not self.pj[OBSERVATIONS][self.observationId][FILE][n_player]):
                continue

            # check if an offset is set on player n_player
            if self.pj[OBSERVATIONS][self.observationId][MEDIA_INFO]["offset"][n_player]:
                requiredFrame_w_offset = int(requiredFrame - self.pj[OBSERVATIONS][self.observationId][MEDIA_INFO]["offset"][n_player] * self.fps)
                currentMedia, frameCurrentMedia = self.getCurrentMediaByFrame(n_player, requiredFrame_w_offset, self.fps)
                if frameCurrentMedia <= 0:
                    player.frame_viewer.setPixmap(QPixmap(""))
                    continue
            else:
                currentMedia, frameCurrentMedia = self.getCurrentMediaByFrame(n_player, requiredFrame, self.fps)

            current_media_full_path = project_functions.media_full_path(currentMedia, self.projectFileName)

            logging.debug(f"current media 1: {currentMedia}")
            logging.debug(f"frame current media 1: {frameCurrentMedia}")

            if self.config_param.get(SAVE_FRAMES, DEFAULT_FRAME_MODE) == DISK:

                md5FileName = hashlib.md5(current_media_full_path.encode("utf-8")).hexdigest()

                frame_image_path = pathlib.Path(self.imageDirectory) / pathlib.Path((f"BORIS@{md5FileName}_{frameCurrentMedia:08}"
                                                                                      f".{self.frame_bitmap_format.lower()}"))

                logging.debug(f"frame_image_path: {frame_image_path}")
                logging.debug(f"frame_image_path is file: {os.path.isfile(frame_image_path)}")

                if os.path.isfile(frame_image_path):
                    self.pixmap = QPixmap(str(frame_image_path))

                    # check if jpg filter available. If not use png
                    if self.pixmap.isNull():
                        self.frame_bitmap_format = "PNG"
                else:
                    ''' disabled because change focus when it closes
                    self.iw = dialog.Info_widget()
                    self.iw.lwi.setVisible(False)
                    self.iw.resize(350, 200)
                    self.iw.setWindowFlags(Qt.WindowStaysOnTopHint)

                    logging.debug(f"Extracting frame to disk")

                    self.iw.setWindowTitle("Extracting frames to disk...")
                    self.iw.label.setText("Extracting frames to disk... This operation can be long. Be patient...")
                    self.iw.show()
                    app.processEvents()
                    '''
                    self.statusbar.showMessage("Extracting frames to disk", 0)
                    QApplication.processEvents()

                    utilities.extract_frames(self.ffmpeg_bin,
                                             frameCurrentMedia,
                                             (frameCurrentMedia - 1) / self.fps,
                                             current_media_full_path,
                                             round(self.fps),
                                             self.imageDirectory,
                                             md5FileName,
                                             self.frame_bitmap_format.lower(),
                                             self.frame_resize,
                                             self.fbf_cache_size)
                    '''
                    self.iw.hide()
                    '''
                    self.statusbar.showMessage("", 0)

                    if not os.path.isfile(frame_image_path):

                        logging.warning(f"frame not found: {frame_image_path} {frameCurrentMedia} {int(frameCurrentMedia / self.fps)}")

                        return

                    self.pixmap = QPixmap(str(frame_image_path))
                    # check if jpg filter available if not use png
                    if self.pixmap.isNull():
                        self.frame_bitmap_format = "PNG"

                player.frame_viewer.setPixmap(self.pixmap.scaled(player.frame_viewer.size(), Qt.KeepAspectRatio))


            if self.config_param.get(SAVE_FRAMES, DEFAULT_FRAME_MODE) == MEMORY:

                logging.debug(f"frame current media: {frameCurrentMedia}")

                if (current_media_full_path not in self.frames_cache
                        or frameCurrentMedia not in self.frames_cache[current_media_full_path]):

                    if current_media_full_path not in self.frames_cache:
                        self.frames_cache[current_media_full_path] = {}

                    # check free mem size
                    r, mem = utilities.mem_info()
                    if not r:
                        # no free mem
                        if mem.get("free_memory", 0) < 200:
                            # reset buffer
                            #del self.frames_buffer

                            logging.debug(f"free memory < 200 Mb. Reset buffer")

                            self.initialize_frames_buffer()
                            self.frames_cache[current_media_full_path] = {}

                            if mem.get("free_memory", 0) < 200:
                                self.statusbar.showMessage(("The free memory is very low.\n"
                                                            "You should change the frame-by-frame mode from memory to disk.\n"
                                                            "See File > Preferences"), 0)
                                return
                        # check buffer size
                        if self.frames_buffer.size() > self.config_param[MEMORY_FOR_FRAMES] * 1024 * 1024:
                            # reset buffer
                            #del self.frames_buffer

                            logging.debug(f"buffer size > {self.config_param[MEMORY_FOR_FRAMES] * 1024 * 1024}. Reset buffer")

                            self.initialize_frames_buffer()
                            self.frames_cache[current_media_full_path] = {}
                    else:
                        self.statusbar.showMessage(f"Free memory not available ({mem.get('msg', '')})", 0)

                    self.statusbar.showMessage(f"Extracting frames in memory {int(self.frames_buffer.size()/1024/1024)}", 0)
                    QApplication.processEvents()

                    '''
                    logging.debug(f"frame_viewer size: {player.frame_viewer.size().width()}x{player.frame_viewer.size().height()}")
                    logging.debug(f"videoframe size: {player.videoframe.size().width()}x{player.videoframe.size().height()}")
                    logging.debug(f"videoframe resolution: {player.videoframe.h_resolution}x{player.videoframe.v_resolution}")
                    '''

                    if self.frame_resize:
                        frame_width = self.frame_resize
                        frame_height = int(player.videoframe.v_resolution * (self.frame_resize / player.videoframe.h_resolution) + 0.5)
                    else:
                        # check frame size
                        ratio = player.videoframe.h_resolution / player.videoframe.v_resolution
                        if (player.frame_viewer.size().width() / player.frame_viewer.size().height()) <= ratio:
                            frame_width = player.frame_viewer.size().width()
                            frame_height = int(player.frame_viewer.size().width() / ratio + 0.5)
                        else:
                            frame_height = player.frame_viewer.size().height()
                            frame_width = int(player.frame_viewer.size().height() * ratio + 0.5)


                    # message
                    '''
                    self.iw = dialog.Info_widget()
                    self.iw.lwi.setVisible(False)
                    self.iw.resize(350, 100)
                    self.iw.setWindowFlags(Qt.WindowStaysOnTopHint)

                    logging.debug(f"Extracting frame to memory")

                    self.iw.setWindowTitle("Extracting frames to memory...")
                    self.iw.label.setText("Extracting frames to memory... This operation can be long. Be patient...")
                    self.iw.show()
                    app.processEvents()
                    '''

                    r, msg = self.extract_frames_mem(frameCurrentMedia,
                                                     (frameCurrentMedia - 1) / self.fps,
                                            current_media_full_path,
                                            round(self.fps),
                                            (frame_width, frame_height),
                                            self.frame_bitmap_format.lower(),
                                            0,
                                            self.fbf_cache_size,
                                            bitmap_quality=100)

                    '''
                    self.iw.hide()
                    '''
                    if r:
                        dialog.error_message(" frame extraction in memory", msg)
                        return
                    '''
                    logging.debug(f"frames buffer size: {self.frames_buffer.size()/1024/1024}")
                    logging.debug(f"frames # {sorted(list(self.frames_cache[current_media_full_path].keys()))}")
                    '''

                    self.statusbar.showMessage("", 0)

                if frameCurrentMedia in self.frames_cache[current_media_full_path]:
                    self.frames_buffer.seek(self.frames_cache[current_media_full_path][frameCurrentMedia][0])
                    px = QPixmap()
                    px.loadFromData(self.frames_buffer.read(self.frames_cache[current_media_full_path][frameCurrentMedia][1]))
                    player.frame_viewer.setPixmap(px)
                else:
                    self.statusbar.showMessage(f"Error for frame #{frameCurrentMedia}", 0)

            # redraw measurements from previous frames
            if hasattr(self, "measurement_w") and self.measurement_w is not None and self.measurement_w.isVisible():
                if self.measurement_w.cbPersistentMeasurements.isChecked():

                    logging.debug("Redraw measurements")

                    for frame in self.measurement_w.draw_mem:

                        if frame == self.FFmpegGlobalFrame + 1:
                            elementsColor = ACTIVE_MEASUREMENTS_COLOR
                        else:
                            elementsColor = PASSIVE_MEASUREMENTS_COLOR

                        for element in self.measurement_w.draw_mem[frame]:
                            if element[0] == i:
                                if element[1] == "point":
                                    x, y = element[2:]
                                    self.draw_point(x, y, elementsColor, n_player=i)

                                if element[1] == "line":
                                    x1, y1, x2, y2 = element[2:]
                                    self.draw_line(x1, y1, x2, y2, elementsColor, n_player=i)
                                    self.draw_point(x1, y1, elementsColor, n_player=i)
                                    self.draw_point(x2, y2, elementsColor, n_player=i)
                                if element[1] == "angle":
                                    x1, y1 = element[2][0]
                                    x2, y2 = element[2][1]
                                    x3, y3 = element[2][2]
                                    self.draw_line(x1, y1, x2, y2, elementsColor, n_player=i)
                                    self.draw_line(x1, y1, x3, y3, elementsColor, n_player=i)
                                    self.draw_point(x1, y1, elementsColor, n_player=i)
                                    self.draw_point(x2, y2, elementsColor, n_player=i)
                                    self.draw_point(x3, y3, elementsColor, n_player=i)
                                if element[1] == "polygon":
                                    polygon = QPolygon()
                                    for point in element[2]:
                                        polygon.append(QPoint(point[0], point[1]))
                                    painter = QPainter()
                                    painter.begin(self.dw_player[i].frame_viewer.pixmap())
                                    painter.setPen(QColor(elementsColor))
                                    painter.drawPolygon(polygon)
                                    painter.end()
                                    self.dw_player[i].frame_viewer.update()
                else:
                    self.measurement_w.draw_mem = []


        # update spectro plot
        self.timer_sound_signal_out()
        # update data plot
        for idx in self.plot_data:
            self.timer_plot_data_out(self.plot_data[idx])


        self.FFmpegGlobalFrame = requiredFrame

        currentTime = self.getLaps() * 1000

        time_str = (f"{os.path.basename(currentMedia)}: "
                    f"<b>{self.convertTime(currentTime / 1000)} / "
                    f"{self.convertTime(self.dw_player[0].mediaplayer.get_length() / 1000)}</b> "
                    f"frame: <b>{round(self.FFmpegGlobalFrame)}</b>")

        self.lb_current_media_time.setText(time_str)

        # observation time interval
        if self.pj[OBSERVATIONS][self.observationId].get(OBSERVATION_TIME_INTERVAL, [0, 0])[1]:
            if currentTime >= self.pj[OBSERVATIONS][self.observationId].get(OBSERVATION_TIME_INTERVAL, [0, 0])[1] * 1000:
                if self.is_playing():
                    self.pause_video()
                    self.beep("beep")

        # video slider
        self.video_slider.setValue(currentTime / self.dw_player[0].mediaplayer.get_length() * (slider_maximum - 1))

        # extract State events
        StateBehaviorsCodes = utilities.state_behavior_codes(self.pj[ETHOGRAM])

        self.currentStates = {}
        self.currentStates = utilities.get_current_states_modifiers_by_subject(StateBehaviorsCodes,
                                                                             self.pj[OBSERVATIONS][self.observationId][EVENTS],
                                                                             dict(self.pj[SUBJECTS], **{"": {"name": ""}}),
                                                                             currentTime / 1000,
                                                                             include_modifiers=True)

        # show current states
        subject_idx = self.subject_name_index[self.currentSubject] if self.currentSubject else ""
        self.lbCurrentStates.setText(", ".join(self.currentStates[subject_idx]))

        # show selected subjects
        self.show_current_states_in_subjects_table()

        # show tracking cursor
        self.get_events_current_row()


    def close_measurement_widget(self):
        self.measurement_w.close()


    def clear_measurements(self):
        if self.FFmpegGlobalFrame > 1:
            self.FFmpegGlobalFrame -= 1
            self.ffmpeg_timer_out()


    def geometric_measurements(self):
        """
        active the geometric measurement widget
        """

        self.measurement_w = measurement_widget.wgMeasurement()
        self.measurement_w.draw_mem = {}
        self.measurement_w.setWindowFlags(Qt.WindowStaysOnTopHint)
        self.measurement_w.closeSignal.connect(self.close_measurement_widget)
        self.measurement_w.clearSignal.connect(self.clear_measurements)
        self.measurement_w.show()


    def draw_point(self, x, y, color, n_player=0):
        """
        draw point on frame-by-frame image
        """
        RADIUS = 6
        painter = QPainter()
        painter.begin(self.dw_player[n_player].frame_viewer.pixmap())
        painter.setPen(QColor(color))
        painter.drawEllipse(QPoint(x, y), RADIUS, RADIUS)
        # cross inside circle
        painter.drawLine(x - RADIUS, y, x + RADIUS, y)
        painter.drawLine(x, y - RADIUS, x, y + RADIUS)
        painter.end()
        self.dw_player[n_player].frame_viewer.update()


    def draw_line(self, x1, y1, x2, y2, color, n_player=0):
        """
        draw line on frame-by-frame image
        """
        painter = QPainter()
        painter.begin(self.dw_player[n_player].frame_viewer.pixmap())
        painter.setPen(QColor(color))
        painter.drawLine(x1, y1, x2, y2)
        painter.end()
        self.dw_player[n_player].frame_viewer.update()


    def getPoslbFFmpeg(self, n_player, event):
        """
        geometric measurements on frame

        Args:
            n_player (int): id of clicked player
            event (Qevent): event (mousepressed)
        """

        if self.mem_player != -1 and n_player != self.mem_player:
            self.mem_player = n_player
            return

        self.mem_player = n_player
        if hasattr(self, "measurement_w") and self.measurement_w is not None and self.measurement_w.isVisible():
            x, y = event.pos().x(), event.pos().y()

            # convert label coordinates in pixmap coordinates
            x = int(x - (self.dw_player[n_player].frame_viewer.width() - self.dw_player[n_player].frame_viewer.pixmap().width()) / 2)
            y = int(y - (self.dw_player[n_player].frame_viewer.height() - self.dw_player[n_player].frame_viewer.pixmap().height()) / 2)

            # point
            if self.measurement_w.rbPoint.isChecked():
                if event.button() == 1:   # left
                    self.draw_point(x, y, ACTIVE_MEASUREMENTS_COLOR, n_player)
                    if self.FFmpegGlobalFrame in self.measurement_w.draw_mem:
                        self.measurement_w.draw_mem[self.FFmpegGlobalFrame].append([n_player, "point", x, y])
                    else:
                        self.measurement_w.draw_mem[self.FFmpegGlobalFrame] = [[n_player, "point", x, y]]

                    self.measurement_w.pte.appendPlainText((f"Time: {self.getLaps()}\tPlayer: {n_player + 1}\t"
                                                            f"Frame: {self.FFmpegGlobalFrame}\tPoint: {x},{y}"))


            # distance
            if self.measurement_w.rbDistance.isChecked():
                if event.button() == 1:   # left
                    self.draw_point(x, y, ACTIVE_MEASUREMENTS_COLOR, n_player)
                    self.memx, self.memy = x, y

                if event.button() == 2 and self.memx != -1 and self.memy != -1:
                    self.draw_point(x, y, ACTIVE_MEASUREMENTS_COLOR, n_player)
                    self.draw_line(self.memx, self.memy, x, y, ACTIVE_MEASUREMENTS_COLOR, n_player)

                    if self.FFmpegGlobalFrame in self.measurement_w.draw_mem:
                        self.measurement_w.draw_mem[self.FFmpegGlobalFrame].append([n_player, "line", self.memx, self.memy, x, y])
                    else:
                        self.measurement_w.draw_mem[self.FFmpegGlobalFrame] = [[n_player, "line", self.memx, self.memy, x, y]]

                    d = ((x - self.memx) ** 2 + (y - self.memy) ** 2) ** 0.5
                    try:
                        d = d / float(self.measurement_w.lePx.text()) * float(self.measurement_w.leRef.text())
                    except Exception:
                        QMessageBox.critical(self, programName,
                                             "Check reference and pixel values! Values must be numeric.",
                                             QMessageBox.Ok | QMessageBox.Default, QMessageBox.NoButton)

                    self.measurement_w.pte.appendPlainText((f"Time: {self.getLaps()}\tPlayer: {n_player + 1}\t"
                                                            f"Frame: {self.FFmpegGlobalFrame}\tDistance: {round(d, 1)}"))
                    self.measurement_w.flagSaved = False
                    self.memx, self.memy = -1, -1

            # angle 1st clic -> vertex
            if self.measurement_w.rbAngle.isChecked():
                if event.button() == 1:   # left for vertex
                    self.draw_point(x, y, ACTIVE_MEASUREMENTS_COLOR, n_player)
                    self.memPoints = [(x, y)]

                if event.button() == 2 and len(self.memPoints):
                    self.draw_point(x, y, ACTIVE_MEASUREMENTS_COLOR, n_player)
                    self.draw_line(self.memPoints[0][0], self.memPoints[0][1], x, y, ACTIVE_MEASUREMENTS_COLOR, n_player)

                    self.memPoints.append((x, y))

                    if len(self.memPoints) == 3:
                        self.measurement_w.pte.appendPlainText(
                            (f"Time: {self.getLaps()}\tPlayer: {n_player + 1}\t"
                             f"Frame: {self.FFmpegGlobalFrame}\t"
                             f"Angle: {round(angle(self.memPoints[0], self.memPoints[1], self.memPoints[2]), 1)}"))
                        self.measurement_w.flagSaved = False
                        if self.FFmpegGlobalFrame in self.measurement_w.draw_mem:
                            self.measurement_w.draw_mem[self.FFmpegGlobalFrame].append([n_player, "angle", self.memPoints])
                        else:
                            self.measurement_w.draw_mem[self.FFmpegGlobalFrame] = [[n_player, "angle", self.memPoints]]

                        self.memPoints = []

            # Area
            if self.measurement_w.rbArea.isChecked():
                if event.button() == 1:   # left
                    self.draw_point(x, y, ACTIVE_MEASUREMENTS_COLOR)
                    if len(self.memPoints):
                        self.draw_line(self.memPoints[-1][0], self.memPoints[-1][1], x, y, ACTIVE_MEASUREMENTS_COLOR, n_player)
                    self.memPoints.append((x, y))

                if event.button() == 2 and len(self.memPoints) >= 2:
                    self.draw_point(x, y, ACTIVE_MEASUREMENTS_COLOR, n_player)
                    self.draw_line(self.memPoints[-1][0], self.memPoints[-1][1], x, y, ACTIVE_MEASUREMENTS_COLOR, n_player)
                    self.memPoints.append((x, y))
                    # close polygon
                    self.draw_line(self.memPoints[-1][0], self.memPoints[-1][1],
                                   self.memPoints[0][0], self.memPoints[0][1], ACTIVE_MEASUREMENTS_COLOR, n_player)
                    a = polygon_area(self.memPoints)

                    if self.FFmpegGlobalFrame in self.measurement_w.draw_mem:
                        self.measurement_w.draw_mem[self.FFmpegGlobalFrame].append([n_player, "polygon", self.memPoints])
                    else:
                        self.measurement_w.draw_mem[self.FFmpegGlobalFrame] = [[n_player, "polygon", self.memPoints]]
                    try:
                        a = a / (float(self.measurement_w.lePx.text())**2) * float(self.measurement_w.leRef.text())**2
                    except Exception:
                        QMessageBox.critical(self, programName,
                                             "Check reference and pixel values! Values must be numeric.",
                                             QMessageBox.Ok | QMessageBox.Default, QMessageBox.NoButton)

                    self.measurement_w.pte.appendPlainText((f"Time: {self.getLaps()}\tPlayer: {n_player + 1}\t"
                                                            f"Frame: {self.FFmpegGlobalFrame}\tArea: {round(a, 1)}"))
                    self.memPoints = []

        else:  # no measurements
            QMessageBox.warning(self, programName,
                                "The Focus area function is not yet available in frame-by-frame mode.",
                                QMessageBox.Ok | QMessageBox.Default, QMessageBox.NoButton)


    def initialize_new_observation_vlc(self):
        """
        initialize new observation for VLC
        """

        logging.debug("function: initialize new observation for VLC")

        ok, msg = project_functions.check_if_media_available(self.pj[OBSERVATIONS][self.observationId],
                                                             self.projectFileName)
        if not ok:
            QMessageBox.critical(self, programName,
                                 (f"{msg}<br><br>The observation will be opened in VIEW mode.<br>"
                                  "It will not be possible to log events.<br>"
                                  "Modify the media path to point an existing media file "
                                  "to log events or copy media file in the BORIS project directory."),
                                 QMessageBox.Ok | QMessageBox.Default,
                                 QMessageBox.NoButton)

            self.playerType = VIEWER
            self.playMode = ""
            for dw in [self.dwEthogram, self.dwSubjects, self.dwObservations]:
                dw.setVisible(True)
            return True

        self.playerType, self.playMode = VLC, VLC
        self.fps = 0
        for dw in [self.dwEthogram, self.dwSubjects, self.dwObservations]:
            dw.setVisible(True)

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
        for i in range(N_PLAYER):
            n_player = str(i + 1)
            if (n_player not in self.pj[OBSERVATIONS][self.observationId][FILE]
               or not self.pj[OBSERVATIONS][self.observationId][FILE][n_player]):
                continue

            self.dw_player.append(player_dock_widget.DW(i))
            self.dw_player[-1].setFloating(False)
            self.dw_player[-1].setVisible(False)
            self.dw_player[-1].setFeatures(QDockWidget.DockWidgetFloatable | QDockWidget.DockWidgetMovable)

            # place 4 players at the top of the main window and 4 at the bottom
            if i < 4:
                self.addDockWidget(Qt.TopDockWidgetArea if i < 4 else Qt.BottomDockWidgetArea, self.dw_player[-1])

            self.dw_player[i].setVisible(True)

            # for receiving mouse event from frame viewer
            self.dw_player[i].frame_viewer.mouse_pressed_signal.connect(self.getPoslbFFmpeg)
            # for receiving key event from dock widget
            self.dw_player[i].key_pressed_signal.connect(self.signal_from_widget)
            # for receiving event from volume slider
            self.dw_player[i].volume_slider_moved_signal.connect(self.setVolume)
            # for receiving event resize and clicked (Zoom - crop)
            self.dw_player[i].view_signal.connect(self.signal_from_dw)

            self.dw_player[i].mediaplayer = self.instance.media_player_new()
            self.dw_player[i].mediaplayer.video_set_key_input(False)
            self.dw_player[i].mediaplayer.video_set_mouse_input(False)

            if self.config_param[DISPLAY_SUBTITLES]:
                self.dw_player[i].mediaplayer.video_set_spu(0)
            else:
                self.dw_player[i].mediaplayer.video_set_spu(-1)

            self.dw_player[i].mediaListPlayer = self.instance.media_list_player_new()

            self.dw_player[i].mediaListPlayer.set_media_player(self.dw_player[i].mediaplayer)

            self.dw_player[i].media_list = self.instance.media_list_new()

            # add durations list
            self.dw_player[i].media_durations = []
            # add fps list
            self.dw_player[i].fps = {}

            for mediaFile in self.pj[OBSERVATIONS][self.observationId][FILE][n_player]:

                logging.debug(f"media file: {mediaFile}")

                media_full_path = project_functions.media_full_path(mediaFile, self.projectFileName)

                logging.debug(f"media_full_path: {media_full_path}")

                media = self.instance.media_new(pathlib.Path(media_full_path).as_uri())
                media.parse()

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

                        # check if duration not found
                        '''
                        if r["duration"] == 0:

                            instance = vlc.Instance()
                            media = instance.media_new(pathlib.Path(media_full_path).as_uri())
                            media.parse()

                            mediaplayer = instance.media_player_new()
                            mediaplayer.set_media(media)
                            mediaplayer.play()
                            time.sleep(3)
                            mediaplayer.stop()

                            r["duration"] = Decimal(media.get_duration() / 1000)
                        '''

                        self.pj[OBSERVATIONS][self.observationId][MEDIA_INFO][LENGTH][mediaFile] = r["duration"]
                        self.pj[OBSERVATIONS][self.observationId][MEDIA_INFO][FPS][mediaFile] = r["fps"]

                        mediaLength = r["duration"] * 1000
                        mediaFPS = r["fps"]

                        self.projectChanged = True

                self.dw_player[i].media_durations.append(int(mediaLength))
                self.dw_player[i].fps[mediaFile] = mediaFPS
                self.dw_player[i].media_list.add_media(media)

            # add media list to media player list
            self.dw_player[i].mediaListPlayer.set_media_list(self.dw_player[i].media_list)

            if sys.platform.startswith("linux"):  # for Linux using the X Server
                self.dw_player[i].mediaplayer.set_xwindow(self.dw_player[i].videoframe.winId())
            elif sys.platform == "win32":  # for Windows
                self.dw_player[i].mediaplayer.set_hwnd(self.dw_player[i].videoframe.winId())
            elif sys.platform == "darwin":  # for MacOS
                self.dw_player[i].mediaplayer.set_nsobject(int(self.dw_player[i].videoframe.winId()))

            # show first frame of video
            logging.debug(f"playing media #0")

            self.dw_player[i].mediaListPlayer.play_item_at_index(0)

            # play mediaListPlayer for a while to obtain media information
            if sys.platform != "darwin":
                while True:
                    if self.dw_player[i].mediaListPlayer.get_state() in [self.vlc_playing, self.vlc_ended]:
                        break

            self.dw_player[i].mediaListPlayer.pause()

            if sys.platform != "darwin":
                while True:
                    if self.dw_player[i].mediaListPlayer.get_state() in [self.vlc_paused, self.vlc_ended]:
                        break

            # position media
            if OBSERVATION_TIME_INTERVAL in self.pj[OBSERVATIONS][self.observationId]:
                self.seek_mediaplayer(int(self.pj[OBSERVATIONS][self.observationId][OBSERVATION_TIME_INTERVAL][0] * 1000),
                                      player=i)
            else:
                self.seek_mediaplayer(0, player=i)

            (self.dw_player[i].videoframe.h_resolution,
             self.dw_player[i].videoframe.v_resolution) = self.dw_player[i].mediaplayer.video_get_size(0)


        self.FFmpegTimer = QTimer(self)
        self.FFmpegTimer.timeout.connect(self.ffmpeg_timer_out)
        try:
            '''self.FFmpegTimerTick = int(1000 / self.fps)'''
            fps_list = list(set(self.dw_player[0].fps.values()))
            if not fps_list:
                raise Exception
            self.FFmpegTimerTick = round(1000 / fps_list[0])

        except Exception:
            # default value 40 ms (25 frames / s)
            logging.error(f"FPS not available. Set ffmpegtimer to default value (40 ms)")
            self.FFmpegTimerTick = 40

        self.FFmpegTimer.setInterval(self.FFmpegTimerTick)

        self.menu_options()

        self.actionPlay.setIcon(QIcon(":/play"))

        self.display_statusbar_info(self.observationId)

        self.memMedia, self.currentSubject = "", ""

        self.timer_out()

        self.lbSpeed.setText(f"x{self.play_rate:.3f}")

        ''' 2019-12-12
        if window.focusWidget():
            window.focusWidget().installEventFilter(self)
        '''


        # spectrogram
        if (VISUALIZE_SPECTROGRAM in self.pj[OBSERVATIONS][self.observationId] and
                self.pj[OBSERVATIONS][self.observationId][VISUALIZE_SPECTROGRAM]):

            tmp_dir = self.ffmpeg_cache_dir if self.ffmpeg_cache_dir and os.path.isdir(self.ffmpeg_cache_dir) else tempfile.gettempdir()

            wav_file_path = pathlib.Path(tmp_dir) / pathlib.Path(
                urllib.parse.unquote(url2path(self.dw_player[0].mediaplayer.get_media().get_mrl())) + ".wav"
                ).name

            if not wav_file_path.is_file():
                self.generate_wav_file_from_media()

            self.spectro = plot_spectrogram_rt.Plot_spectrogram_RT()

            self.spectro.setWindowFlags(Qt.WindowStaysOnTopHint)

            self.spectro.interval = self.spectrogram_time_interval
            self.spectro.cursor_color = "red"
            try:
                self.spectro.spectro_color_map = matplotlib.pyplot.get_cmap(self.spectrogram_color_map)
            except ValueError:
                self.spectro.spectro_color_map = matplotlib.pyplot.get_cmap("viridis")

            r = self.spectro.load_wav(str(wav_file_path))
            if "error" in r:
                logging.warning("spectro_load_wav error: {}".format(r["error"]))
                QMessageBox.warning(self, programName, "Error in spectrogram generation: " + r["error"],
                                    QMessageBox.Ok | QMessageBox.Default,
                                    QMessageBox.NoButton)
                del self.spectro
                return

            self.spectro.sendEvent.connect(self.signal_from_widget)
            self.spectro.sb_freq_min.setValue(0)
            self.spectro.sb_freq_max.setValue(int(self.spectro.frame_rate / 2))
            self.spectro.show()
            self.timer_sound_signal.start()

        # waveform
        if (VISUALIZE_WAVEFORM in self.pj[OBSERVATIONS][self.observationId] and
                self.pj[OBSERVATIONS][self.observationId][VISUALIZE_WAVEFORM]):

            tmp_dir = self.ffmpeg_cache_dir if self.ffmpeg_cache_dir and os.path.isdir(self.ffmpeg_cache_dir) else tempfile.gettempdir()

            wav_file_path = pathlib.Path(tmp_dir) / pathlib.Path(
                urllib.parse.unquote(url2path(self.dw_player[0].mediaplayer.get_media().get_mrl())) + ".wav"
                ).name

            if not wav_file_path.is_file():
                self.generate_wav_file_from_media()

            self.waveform = plot_waveform_rt.Plot_waveform_RT()

            self.waveform.setWindowFlags(Qt.WindowStaysOnTopHint)

            # TODO fix time interval
            self.waveform.interval = self.spectrogram_time_interval
            self.waveform.cursor_color = "red"
            '''
            try:
                self.spectro.spectro_color_map = matplotlib.pyplot.get_cmap(self.spectrogram_color_map)
            except ValueError:
                self.spectro.spectro_color_map = matplotlib.pyplot.get_cmap("viridis")
            '''

            r = self.waveform.load_wav(str(wav_file_path))
            if "error" in r:
                logging.warning("waveform_load_wav error: {}".format(r["error"]))
                QMessageBox.warning(self, programName, "Error in waveform generation: " + r["error"],
                                    QMessageBox.Ok | QMessageBox.Default,
                                    QMessageBox.NoButton)
                del self.waveform
                return

            self.waveform.sendEvent.connect(self.signal_from_widget)
            '''
            self.waveform.sb_freq_min.setValue(0)
            self.waveform.sb_freq_max.setValue(int(self.waveform.frame_rate / 2))
            '''
            self.waveform.show()
            self.timer_sound_signal.start()

        # external data plot
        if PLOT_DATA in self.pj[OBSERVATIONS][self.observationId] and self.pj[OBSERVATIONS][self.observationId][PLOT_DATA]:

            self.plot_data = {}
            self.ext_data_timer_list = []
            count = 0
            for idx in self.pj[OBSERVATIONS][self.observationId][PLOT_DATA]:
                if count == 0:

                    data_file_path = project_functions.media_full_path(
                        self.pj[OBSERVATIONS][self.observationId][PLOT_DATA][idx]["file_path"],
                        self.projectFileName)
                    if not data_file_path:
                        QMessageBox.critical(
                            self, programName,
                            "Data file not found:\n{}".format(
                                self.pj[OBSERVATIONS][self.observationId][PLOT_DATA][idx]["file_path"]))
                        return False

                    w1 = plot_data_module.Plot_data(data_file_path,
                                                    int(self.pj[OBSERVATIONS][self.observationId][PLOT_DATA][idx]["time_interval"]),
                                                    str(self.pj[OBSERVATIONS][self.observationId][PLOT_DATA][idx]["time_offset"]),
                                                    self.pj[OBSERVATIONS][self.observationId][PLOT_DATA][idx]["color"],
                                                    self.pj[OBSERVATIONS][self.observationId][PLOT_DATA][idx]["title"],
                                                    self.pj[OBSERVATIONS][self.observationId][PLOT_DATA][idx]["variable_name"],
                                                    self.pj[OBSERVATIONS][self.observationId][PLOT_DATA][idx]["columns"],
                                                    self.pj[OBSERVATIONS][self.observationId][PLOT_DATA][idx]["substract_first_value"],
                                                    self.pj[CONVERTERS] if CONVERTERS in self.pj else {},
                                                    self.pj[OBSERVATIONS][self.observationId][PLOT_DATA][idx]["converters"],
                                                    log_level=logging.getLogger().getEffectiveLevel()
                                                    )

                    if w1.error_msg:
                        QMessageBox.critical(
                            self, programName,
                            (f"Impossible to plot data from file {os.path.basename(self.pj[OBSERVATIONS][self.observationId][PLOT_DATA][idx]['file_path'])}:\n"
                             f"{w1.error_msg}"))
                        del w1
                        return False

                    w1.setWindowFlags(Qt.WindowStaysOnTopHint)
                    w1.sendEvent.connect(self.signal_from_widget)  # keypress event

                    w1.show()

                    self.ext_data_timer_list.append(QTimer())
                    self.ext_data_timer_list[-1].setInterval(w1.time_out)
                    self.ext_data_timer_list[-1].timeout.connect(lambda: self.timer_plot_data_out(w1))
                    self.timer_plot_data_out(w1)
                    # self.ext_data_timer_list[-1].start()

                    self.plot_data[count] = w1

                if count == 1:

                    data_file_path = project_functions.media_full_path(
                        self.pj[OBSERVATIONS][self.observationId][PLOT_DATA][idx]["file_path"],
                        self.projectFileName)
                    if not data_file_path:
                        QMessageBox.critical(
                            self, programName,
                            "Data file not found:\n{}".format(
                                self.pj[OBSERVATIONS][self.observationId][PLOT_DATA][idx]["file_path"]))
                        return False

                    w2 = plot_data_module.Plot_data(data_file_path,
                                                    int(self.pj[OBSERVATIONS][self.observationId][PLOT_DATA][idx]["time_interval"]),
                                                    str(self.pj[OBSERVATIONS][self.observationId][PLOT_DATA][idx]["time_offset"]),
                                                    self.pj[OBSERVATIONS][self.observationId][PLOT_DATA][idx]["color"],
                                                    self.pj[OBSERVATIONS][self.observationId][PLOT_DATA][idx]["title"],
                                                    self.pj[OBSERVATIONS][self.observationId][PLOT_DATA][idx]["variable_name"],
                                                    self.pj[OBSERVATIONS][self.observationId][PLOT_DATA][idx]["columns"],
                                                    self.pj[OBSERVATIONS][self.observationId][PLOT_DATA][idx]["substract_first_value"],
                                                    self.pj[CONVERTERS] if CONVERTERS in self.pj else {},
                                                    self.pj[OBSERVATIONS][self.observationId][PLOT_DATA][idx]["converters"],
                                                    log_level=logging.getLogger().getEffectiveLevel()
                                                    )

                    if w2.error_msg:
                        QMessageBox.critical(self, programName, "Impossible to plot data from file {}:\n{}".format(
                            os.path.basename(self.pj[OBSERVATIONS][self.observationId][PLOT_DATA][idx]["file_path"]),
                            w2.error_msg))
                        del w2
                        return False

                    w2.setWindowFlags(Qt.WindowStaysOnTopHint)
                    w2.sendEvent.connect(self.signal_from_widget)

                    w2.show()
                    self.ext_data_timer_list.append(QTimer())
                    self.ext_data_timer_list[-1].setInterval(w2.time_out)
                    self.ext_data_timer_list[-1].timeout.connect(lambda: self.timer_plot_data_out(w2))
                    self.timer_plot_data_out(w2)
                    # self.ext_data_timer_list[-1].start()

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


    def signal_from_dw(self, id_, msg, button):
        """
        receive signal from dock widget: clicked or resized
        """

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

        logging.debug("load events from obs: {}".format(obs_id))

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

        self.menu_options()

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

        '''
        if self.timeFormat == HHMMSS:

            if self.pj[OBSERVATIONS][self.observationId].get(START_FROM_CURRENT_TIME, False):
                self.lb_current_media_time.setText(datetime.datetime.now().isoformat(" ").split(" ")[1][:12])
            else:
                self.lb_current_media_time.setText("00:00:00.000")

        if self.timeFormat == S:
            self.lb_current_media_time.setText("0.000")
        '''

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
            if dialog.MessageDialog(programName, "The current observation will be closed. Do you want to continue?",
                                    [YES, NO]) == NO:

                # show data plot
                self.show_data_files()
                return
            else:
                self.close_observation()

        observationWindow = observation.Observation(tmp_dir=self.ffmpeg_cache_dir if (self.ffmpeg_cache_dir and os.path.isdir(self.ffmpeg_cache_dir)) else tempfile.gettempdir(),
                                                    project_path=self.projectFileName,
                                                    converters=self.pj[CONVERTERS] if CONVERTERS in self.pj else {},
                                                    time_format=self.timeFormat)

        observationWindow.pj = dict(self.pj)
        observationWindow.mode = mode
        observationWindow.mem_obs_id = obsId
        observationWindow.chunk_length = self.chunk_length
        observationWindow.dteDate.setDateTime(QDateTime.currentDateTime())
        observationWindow.ffmpeg_bin = self.ffmpeg_bin
        observationWindow.project_file_name = self.projectFileName

        # add indepvariables
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
                item.setFlags(Qt.ItemIsEnabled)   # not modifiable
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
                        comboBox.setCurrentIndex(self.pj[INDEPENDENT_VARIABLES][i]["possible values"].split(",").index(txt))
                    observationWindow.twIndepVariables.setCellWidget(observationWindow.twIndepVariables.rowCount() - 1, 2, comboBox)

                elif self.pj[INDEPENDENT_VARIABLES][i]["type"] == TIMESTAMP:
                    cal = QDateTimeEdit()
                    cal.setDisplayFormat("yyyy-MM-dd hh:mm:ss")
                    cal.setCalendarPopup(True)
                    if txt:
                        cal.setDateTime(QDateTime.fromString(txt, "yyyy-MM-ddThh:mm:ss"))
                    observationWindow.twIndepVariables.setCellWidget(observationWindow.twIndepVariables.rowCount() - 1, 2, cal)
                else:
                    item.setText(txt)
                    observationWindow.twIndepVariables.setItem(observationWindow.twIndepVariables.rowCount() - 1, 2, item)

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

            observationWindow.dteDate.setDateTime(QDateTime.fromString(self.pj[OBSERVATIONS][obsId]["date"], "yyyy-MM-ddThh:mm:ss"))
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
                                observationWindow.twVideo1.rowCount() - 1, 1, QTableWidgetItem(
                                    str(self.pj[OBSERVATIONS][obsId][MEDIA_INFO]["offset"][player])))
                        except Exception:
                            observationWindow.twVideo1.setItem(observationWindow.twVideo1.rowCount() - 1, 1, QTableWidgetItem("0.0"))

                        # duration and FPS
                        try:
                            item = QTableWidgetItem(seconds2time(
                                    self.pj[OBSERVATIONS][obsId][MEDIA_INFO][LENGTH][mediaFile]))
                            item.setFlags(Qt.ItemIsEnabled)
                            observationWindow.twVideo1.setItem(
                                observationWindow.twVideo1.rowCount() - 1, 3, item)

                            item = QTableWidgetItem(f"{self.pj[OBSERVATIONS][obsId][MEDIA_INFO][FPS][mediaFile]:.2f}")
                            item.setFlags(Qt.ItemIsEnabled)
                            observationWindow.twVideo1.setItem(
                                observationWindow.twVideo1.rowCount() - 1, 4, item)
                        except Exception:
                            pass

                        # has_video has_audio
                        try:
                            item = QTableWidgetItem(str(self.pj[OBSERVATIONS][obsId][MEDIA_INFO]["hasVideo"][mediaFile]))
                            item.setFlags(Qt.ItemIsEnabled)
                            observationWindow.twVideo1.setItem(
                                observationWindow.twVideo1.rowCount() - 1, 5, item)

                            item = QTableWidgetItem(str(self.pj[OBSERVATIONS][obsId][MEDIA_INFO]["hasAudio"][mediaFile]))
                            item.setFlags(Qt.ItemIsEnabled)
                            observationWindow.twVideo1.setItem(
                                observationWindow.twVideo1.rowCount() - 1, 6, item)
                        except Exception:
                            pass

            if self.pj[OBSERVATIONS][obsId]["type"] in [MEDIA]:
                observationWindow.tabProjectType.setCurrentIndex(video)

            if self.pj[OBSERVATIONS][obsId]["type"] in [LIVE]:
                observationWindow.tabProjectType.setCurrentIndex(live)
                # sampling time
                observationWindow.sbScanSampling.setValue(self.pj[OBSERVATIONS][obsId].get(SCAN_SAMPLING_TIME, 0))
                # start from current time
                observationWindow.cb_start_from_current_time.setChecked(self.pj[OBSERVATIONS][obsId].get(START_FROM_CURRENT_TIME, False)
                                                                        or self.pj[OBSERVATIONS][obsId].get(START_FROM_CURRENT_EPOCH_TIME, False))
                # day/epoch time
                observationWindow.rb_day_time.setChecked(self.pj[OBSERVATIONS][obsId].get(START_FROM_CURRENT_TIME, False))
                observationWindow.rb_epoch_time.setChecked(self.pj[OBSERVATIONS][obsId].get(START_FROM_CURRENT_EPOCH_TIME, False))

            # spectrogram
            observationWindow.cbVisualizeSpectrogram.setEnabled(True)
            observationWindow.cbVisualizeSpectrogram.setChecked(self.pj[OBSERVATIONS][obsId].get(VISUALIZE_SPECTROGRAM, False))

            # waveform
            observationWindow.cb_visualize_waveform.setEnabled(True)
            observationWindow.cb_visualize_waveform.setChecked(self.pj[OBSERVATIONS][obsId].get(VISUALIZE_WAVEFORM, False))

            # observation time interval
            observationWindow.cb_observation_time_interval.setEnabled(True)
            if self.pj[OBSERVATIONS][obsId].get(OBSERVATION_TIME_INTERVAL, [0, 0]) != [0, 0]:
                observationWindow.cb_observation_time_interval.setChecked(True)
                observationWindow.observation_time_interval = self.pj[OBSERVATIONS][obsId].get(OBSERVATION_TIME_INTERVAL, [0, 0])
                observationWindow.cb_observation_time_interval.setText(("Limit observation to a time interval: "
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
                                    DATA_PLOT_STYLES.index(self.pj[OBSERVATIONS][obsId][PLOT_DATA][idx2][DATA_PLOT_FIELDS[idx3]]))

                                observationWindow.tw_data_files.setCellWidget(observationWindow.tw_data_files.rowCount() - 1,
                                                                              PLOT_DATA_PLOTCOLOR_IDX, combobox)
                            elif idx3 == PLOT_DATA_SUBSTRACT1STVALUE_IDX:
                                combobox2 = QComboBox()
                                combobox2.addItems(["False", "True"])
                                combobox2.setCurrentIndex(
                                    ["False", "True"].index(self.pj[OBSERVATIONS][obsId][PLOT_DATA][idx2][DATA_PLOT_FIELDS[idx3]]))

                                observationWindow.tw_data_files.setCellWidget(observationWindow.tw_data_files.rowCount() - 1,
                                                                              PLOT_DATA_SUBSTRACT1STVALUE_IDX, combobox2)
                            elif idx3 == PLOT_DATA_CONVERTERS_IDX:
                                # convert dict to str
                                '''
                                s = ""
                                for conv in self.pj[OBSERVATIONS][obsId][PLOT_DATA][idx2][DATA_PLOT_FIELDS[idx3]]:
                                    s += "," if s else ""
                                    s += "{}:{}".format(conv, self.pj[OBSERVATIONS][obsId][PLOT_DATA][idx2][DATA_PLOT_FIELDS[idx3]][conv])
                                '''
                                observationWindow.tw_data_files.setItem(
                                    observationWindow.tw_data_files.rowCount() - 1, idx3, QTableWidgetItem(
                                        str(self.pj[OBSERVATIONS][obsId][PLOT_DATA][idx2][DATA_PLOT_FIELDS[idx3]])))

                            else:
                                observationWindow.tw_data_files.setItem(
                                    observationWindow.tw_data_files.rowCount() - 1,
                                    idx3,
                                    QTableWidgetItem(self.pj[OBSERVATIONS][obsId][PLOT_DATA][idx2][DATA_PLOT_FIELDS[idx3]])
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
                self.pj[OBSERVATIONS][self.observationId] = {FILE: [],
                                                             TYPE: "",
                                                             "date": "",
                                                             DESCRIPTION: "",
                                                             TIME_OFFSET: 0,
                                                             EVENTS: [],
                                                             OBSERVATION_TIME_INTERVAL: [0, 0]
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
                        r, 0).text()] = observationWindow.twIndepVariables.cellWidget(r, 2).dateTime().toString(Qt.ISODate)
                else:
                    self.pj[OBSERVATIONS][new_obs_id][INDEPENDENT_VARIABLES][observationWindow.twIndepVariables.item(
                        r, 0).text()] = observationWindow.twIndepVariables.item(r, 2).text()

            # observation time offset
            self.pj[OBSERVATIONS][new_obs_id][TIME_OFFSET] = observationWindow.obs_time_offset.get_time()

            if observationWindow.cb_observation_time_interval.isChecked():
                self.pj[OBSERVATIONS][new_obs_id][OBSERVATION_TIME_INTERVAL] = observationWindow.observation_time_interval

            self.display_statusbar_info(new_obs_id)

            # visualize spectrogram
            self.pj[OBSERVATIONS][new_obs_id][VISUALIZE_SPECTROGRAM] = observationWindow.cbVisualizeSpectrogram.isChecked()
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
                            self.pj[OBSERVATIONS][new_obs_id][PLOT_DATA][str(row)][DATA_PLOT_FIELDS[
                                idx2]] = observationWindow.tw_data_files.cellWidget(row, idx2).currentText()

                        elif idx2 == PLOT_DATA_CONVERTERS_IDX:
                            if observationWindow.tw_data_files.item(row, idx2).text():
                                self.pj[OBSERVATIONS][new_obs_id][PLOT_DATA][str(row)][DATA_PLOT_FIELDS[
                                    idx2]] = eval(observationWindow.tw_data_files.item(row, idx2).text())
                            else:
                                self.pj[OBSERVATIONS][new_obs_id][PLOT_DATA][str(row)][DATA_PLOT_FIELDS[idx2]] = {}

                        else:
                            self.pj[OBSERVATIONS][new_obs_id][PLOT_DATA][str(
                                row)][DATA_PLOT_FIELDS[idx2]] = observationWindow.tw_data_files.item(
                                    row, idx2).text()


            # Close current behaviors between video
            # disabled due to problem when video goes back
            # self.pj[OBSERVATIONS][new_obs_id][CLOSE_BEHAVIORS_BETWEEN_VIDEOS] =
            # observationWindow.cbCloseCurrentBehaviorsBetweenVideo.isChecked()
            self.pj[OBSERVATIONS][new_obs_id][CLOSE_BEHAVIORS_BETWEEN_VIDEOS] = False

            if self.pj[OBSERVATIONS][new_obs_id][TYPE] in [LIVE]:
                self.pj[OBSERVATIONS][new_obs_id][SCAN_SAMPLING_TIME] = observationWindow.sbScanSampling.value()
                self.pj[OBSERVATIONS][new_obs_id][START_FROM_CURRENT_TIME] = (observationWindow.cb_start_from_current_time.isChecked()
                                                                              and observationWindow.rb_day_time.isChecked())
                self.pj[OBSERVATIONS][new_obs_id][START_FROM_CURRENT_EPOCH_TIME] = (observationWindow.cb_start_from_current_time.isChecked()
                                                                              and observationWindow.rb_epoch_time.isChecked())

            # media file
            self.pj[OBSERVATIONS][new_obs_id][FILE] = {}

            # media
            if self.pj[OBSERVATIONS][new_obs_id][TYPE] in [MEDIA]:

                self.pj[OBSERVATIONS][new_obs_id][MEDIA_INFO] = {LENGTH: observationWindow.mediaDurations,
                                                                 FPS: observationWindow.mediaFPS}

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
                    self.pj[OBSERVATIONS][new_obs_id][FILE][observationWindow.twVideo1.cellWidget(row, 0).currentText()].append(
                        observationWindow.twVideo1.item(row, 2).text()
                    )
                    # store offset for media player
                    self.pj[OBSERVATIONS][new_obs_id][MEDIA_INFO][
                        "offset"
                    ][observationWindow.twVideo1.cellWidget(row, 0).currentText()] = float(observationWindow.twVideo1.item(row, 1).text())

            if rv == 1:  # save
                self.observationId = ""
                self.menu_options()

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

                    self.initialize_new_observation_vlc()

                self.menu_options()


    def close_tool_windows(self):
        """
        close tool windows: spectrogram, measurements, coding pad
        """

        logging.debug("function: close_tool_windows")
        '''
        for w in [self.measurement_w, self.codingpad, self.subjects_pad, self.spectro,
                  self.frame_viewer1, self.frame_viewer2, self.results,
                  self.mapCreatorWindow]:
            try:
                w.close()
            except:
                pass
        '''
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

        '''
        while self.plot_data:
            self.plot_data[0].close_plot()
            time.sleep(1)
            del self.plot_data[0]
        '''

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

        # delete behavior coding map
        try:
            for idx in self.bcm_dict:
                if self.bcm_dict[idx] is not None:
                    self.bcm_dict[idx].close()
                self.bcm_dict[idx] = None
        except Exception:
            dialog.error_message(f"closing behavior coding map: {idx}", sys.exc_info())



    def close_observation(self):
        """
        close current observation
        """

        logging.info(f"Close observation {self.playerType}")

        try:
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
                        events_to_add = project_functions.fix_unpaired_state_events(self.observationId,
                                                                                    self.pj[ETHOGRAM],
                                                                                    self.pj[OBSERVATIONS][self.observationId],
                                                                                    fix_at_time - Decimal("0.001")
                                                                                    )
                        if events_to_add:
                            self.pj[OBSERVATIONS][self.observationId][EVENTS].extend(events_to_add)
                            self.projectChanged = True
                            self.pj[OBSERVATIONS][self.observationId][EVENTS].sort()

                            self.loadEventsInTW(self.observationId)
                            item = self.twEvents.item([i for i, t in enumerate(self.pj[OBSERVATIONS][self.observationId][EVENTS])
                                                    if t[0] == fix_at_time][0], 0)
                            self.twEvents.scrollToItem(item)
                            return
                    else:
                        return

            self.saved_state = self.saveState()

            if self.playerType == VLC:
                self.timer.stop()
                self.FFmpegTimer.stop()
                self.timer_sound_signal.stop()

                for i, player in enumerate(self.dw_player):
                    if (str(i + 1) in self.pj[OBSERVATIONS][self.observationId][FILE]
                            and self.pj[OBSERVATIONS][self.observationId][FILE][str(i + 1)]):
                        player.mediaplayer.stop()

                self.verticalLayout_3.removeWidget(self.video_slider)

                if self.video_slider is not None:
                    self.video_slider.deleteLater()
                    self.video_slider = None

            if self.playerType == LIVE:
                self.liveTimer.stop()
                self.w_live.setVisible(False)
                self.liveObservationStarted = False
                self.liveStartTime = None

            if PLOT_DATA in self.pj[OBSERVATIONS][self.observationId] and self.pj[OBSERVATIONS][self.observationId][PLOT_DATA]:
                for x in self.ext_data_timer_list:
                    x.stop()
                for pd in self.plot_data:
                    self.plot_data[pd].close_plot()

            self.close_tool_windows()

            if self.playerType == VLC:

                for i, player in enumerate(self.dw_player):
                    player.setVisible(False)
                    player.deleteLater()

                self.dw_player = []

                self.actionFrame_by_frame.setChecked(False)
                self.playMode = VLC

                ''' TO BE DELETED 2019-11-26
                try:
                    self.spectro.close()
                    del self.spectro
                except Exception:
                    pass
                '''

                try:
                    self.FFmpegTimer.stop()
                    self.FFmpegGlobalFrame = 0
                except Exception:
                    pass

            self.observationId = ""

            # buffer no more deleted when observation is closed
            # self.initialize_frames_buffer()

            self.statusbar.showMessage("", 0)

            self.dwObservations.setVisible(False)

            self.w_obs_info.setVisible(False)

            self.twEvents.setRowCount(0)

            self.lb_current_media_time.clear()
            self.currentSubject = ""
            self.lbFocalSubject.setText(NO_FOCAL_SUBJECT)

            # clear current state(s) column in subjects table
            for i in range(self.twSubjects.rowCount()):
                self.twSubjects.item(i, len(subjectsFields)).setText("")

            for w in [self.lbTimeOffset, self.lbSpeed, self.lb_obs_time_interval]:
                w.clear()
            self.play_rate, self.playerType = 1, ""

            self.menu_options()
        except Exception:
            dialog.error_message("Close observation", sys.exc_info())


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


    def readConfigFile(self):
        """
        read config file
        """

        iniFilePath = pathlib.Path.home() / pathlib.Path(".boris")

        logging.debug(f"read config file: {iniFilePath}")

        if iniFilePath.is_file():
            settings = QSettings(str(iniFilePath), QSettings.IniFormat)

            try:
                self.config_param = settings.value("config")
            except Exception:
                self.config_param = None
                pass
            if self.config_param is None:
                self.config_param = INIT_PARAM

                # for back compatibility
                # display subtitles
                try:
                    self.config_param[DISPLAY_SUBTITLES] = (settings.value(DISPLAY_SUBTITLES) == 'true')
                except Exception:
                    self.config_param[DISPLAY_SUBTITLES] = False

                logging.debug(f"{DISPLAY_SUBTITLES}: {self.config_param[DISPLAY_SUBTITLES]}")

            try:
                logging.debug("restore geometry")

                self.restoreGeometry(settings.value("geometry"))
            except Exception:
                logging.warning("Error restoring geometry")
                pass

            self.saved_state = settings.value("dockwidget_positions")
            if not isinstance(self.saved_state, QByteArray):
                self.saved_state = None

            logging.debug(f"saved state: {self.saved_state}")

            for dw in [self.dwEthogram, self.dwSubjects, self.dwObservations]:
                dw.setVisible(False)

            self.timeFormat = HHMMSS
            try:
                self.timeFormat = settings.value("Time/Format")
            except Exception:
                self.timeFormat = HHMMSS

            logging.debug(f"time format: {self.timeFormat}")

            self.fast = 10
            try:
                self.fast = int(settings.value("Time/fast_forward_speed"))
            except Exception:
                self.fast = 10

            logging.debug(f"Time/fast_forward_speed: {self.fast}")

            self.repositioningTimeOffset = 0
            try:
                self.repositioningTimeOffset = int(settings.value("Time/Repositioning_time_offset"))
            except Exception:
                self.repositioningTimeOffset = 0

            logging.debug(f"Time/Repositioning_time_offset: {self.repositioningTimeOffset}")

            self.play_rate_step = 0.1
            try:
                self.play_rate_step = float(settings.value("Time/play_rate_step"))
            except Exception:
                self.play_rate_step = 0.1

            logging.debug(f"Time/play_rate_step: {self.play_rate_step}")

            self.automaticBackup = 0
            try:
                self.automaticBackup = int(settings.value("Automatic_backup"))
            except Exception:
                self.automaticBackup = 0

            # activate or desactivate autosave timer
            if self.automaticBackup:
                self.automaticBackupTimer.start(self.automaticBackup * 60000)
            else:
                self.automaticBackupTimer.stop()

            logging.debug(f"Autosave: {self.automaticBackup}")

            self.behaviouralStringsSeparator = "|"
            try:
                self.behaviouralStringsSeparator = settings.value("behavioural_strings_separator")
                if not self.behaviouralStringsSeparator:
                    self.behaviouralStringsSeparator = "|"
            except Exception:
                self.behaviouralStringsSeparator = "|"

            logging.debug(f"behavioural_strings_separator: {self.behaviouralStringsSeparator}")

            self.close_the_same_current_event = False
            try:
                self.close_the_same_current_event = (settings.value("close_the_same_current_event") == "true")
            except Exception:
                self.close_the_same_current_event = False

            logging.debug(f"close_the_same_current_event: {self.close_the_same_current_event}")

            self.confirmSound = False
            try:
                self.confirmSound = (settings.value("confirm_sound") == "true")
            except Exception:
                self.confirmSound = False

            logging.debug(f"confirm_sound: {self.confirmSound}")

            self.alertNoFocalSubject = False
            try:
                self.alertNoFocalSubject = (settings.value("alert_nosubject") == "true")
            except Exception:
                self.alertNoFocalSubject = False
            logging.debug(f"alert_nosubject: {self.alertNoFocalSubject}")

            try:
                self.beep_every = int(settings.value("beep_every"))
            except Exception:
                self.beep_every = 0
            logging.debug(f"beep_every: {self.beep_every}")

            self.trackingCursorAboveEvent = False
            try:
                self.trackingCursorAboveEvent = (settings.value("tracking_cursor_above_event") == "true")
            except Exception:
                self.trackingCursorAboveEvent = False
            logging.debug(f"tracking_cursor_above_event: {self.trackingCursorAboveEvent}")

            # check for new version
            self.checkForNewVersion = False
            try:
                if settings.value("check_for_new_version") is None:
                    self.checkForNewVersion = (dialog.MessageDialog(programName,
                                                                    ("Allow BORIS to automatically check for new version and news?\n"
                                                                     "(An internet connection is required)\n"
                                                                     "You can change this option in the Preferences (File > Preferences)"),
                                                                    [YES, NO]) == YES)
                else:
                    self.checkForNewVersion = (settings.value("check_for_new_version") == "true")
            except Exception:
                self.checkForNewVersion = False
            logging.debug(f"check_for_new_version: {self.checkForNewVersion}")


            # pause before add event
            self.pause_before_addevent = False
            try:
                self.pause_before_addevent = (settings.value("pause_before_addevent") == 'true')
            except Exception:
                self.pause_before_addevent = False

            logging.debug(f"pause_before_addevent: {self.pause_before_addevent}")

            if self.checkForNewVersion:
                if (settings.value("last_check_for_new_version")
                        and (int(time.mktime(time.localtime())) - int(
                            settings.value("last_check_for_new_version")) >
                            CHECK_NEW_VERSION_DELAY)):
                    self.actionCheckUpdate_activated(flagMsgOnlyIfNew=True)
            logging.debug(f"last_check_for_new_version: {settings.value('last_check_for_new_version')}")

            self.ffmpeg_cache_dir = ""
            try:
                self.ffmpeg_cache_dir = settings.value("ffmpeg_cache_dir")
                if not self.ffmpeg_cache_dir:
                    self.ffmpeg_cache_dir = ""
            except Exception:
                self.ffmpeg_cache_dir = ""
            logging.debug(f"ffmpeg_cache_dir: {self.ffmpeg_cache_dir}")

            self.ffmpeg_cache_dir_max_size = 0
            try:
                self.ffmpeg_cache_dir_max_size = int(settings.value("ffmpeg_cache_dir_max_size"))
                if not self.ffmpeg_cache_dir_max_size:
                    self.ffmpeg_cache_dir_max_size = 0
            except Exception:
                self.ffmpeg_cache_dir_max_size = 0
            logging.debug(f"ffmpeg_cache_dir_max_size: {self.ffmpeg_cache_dir_max_size}")

            try:
                self.frame_resize = int(settings.value("frame_resize"))
                if not self.frame_resize:
                    self.frame_resize = 0
            except Exception:
                self.frame_resize = 0

            logging.debug(f"frame_resize: {self.frame_resize}")

            try:
                self.frame_bitmap_format = settings.value("frame_bitmap_format")
                if not self.frame_bitmap_format:
                    self.frame_bitmap_format = FRAME_DEFAULT_BITMAP_FORMAT
            except Exception:
                self.frame_bitmap_format = FRAME_DEFAULT_BITMAP_FORMAT

            logging.debug(f"frame_bitmap_format: {self.frame_bitmap_format}")

            try:
                self.fbf_cache_size = int(settings.value("frame_cache_size"))
                if not self.fbf_cache_size:
                    self.fbf_cache_size = FRAME_DEFAULT_CACHE_SIZE
            except Exception:
                self.fbf_cache_size = FRAME_DEFAULT_CACHE_SIZE

            logging.debug(f"frame_cache_size: {self.fbf_cache_size}")

            # spectrogram
            self.spectrogramHeight = 80

            try:
                self.spectrogram_color_map = settings.value("spectrogram_color_map")
                if self.spectrogram_color_map is None:
                    self.spectrogram_color_map = SPECTROGRAM_DEFAULT_COLOR_MAP
            except Exception:
                self.spectrogram_color_map = SPECTROGRAM_DEFAULT_COLOR_MAP

            try:
                self.spectrogram_time_interval = int(settings.value("spectrogram_time_interval"))
                if not self.spectrogram_time_interval:
                    self.spectrogram_time_interval = SPECTROGRAM_DEFAULT_TIME_INTERVAL
            except Exception:
                self.spectrogram_time_interval = SPECTROGRAM_DEFAULT_TIME_INTERVAL

            # plot colors
            try:
                self.plot_colors = settings.value("plot_colors").split("|")
            except Exception:
                self.plot_colors = BEHAVIORS_PLOT_COLORS

            if ("white" in self.plot_colors
                    or "azure" in self.plot_colors
                    or "snow" in self.plot_colors):
                if dialog.MessageDialog(programName, ("The colors list contain colors that are very light.\n"
                                                      "Do you want to reload the default colors list?"),
                                        [NO, YES]) == YES:
                    self.plot_colors = BEHAVIORS_PLOT_COLORS


        else:  # no .boris file found
            logging.info("No config file found")
            # ask user for checking for new version
            self.checkForNewVersion = (dialog.MessageDialog(programName, ("Allow BORIS to automatically check for new version?\n"
                                                                          "(An internet connection is required)\n"
                                                                          "You can change this option in the"
                                                                          " Preferences (File > Preferences)"),
                                                            [NO, YES]) == YES)

        # recent projects
        logging.info("read recent projects")
        iniFilePath = str(pathlib.Path.home() / ".boris_recent_projects")
        if os.path.isfile(iniFilePath):
            settings = QSettings(iniFilePath, QSettings.IniFormat)
            try:
                self.recent_projects = settings.value("recent_projects").split("|||")
                while "" in self.recent_projects:
                    self.recent_projects.remove("")
                self.set_recent_projects_menu()
            except Exception:
                self.recent_projects = []
        else:
            self.recent_projects = []


    def saveConfigFile(self, lastCheckForNewVersion=0):
        """
        save config file
        """

        iniFilePath = pathlib.Path.home() / pathlib.Path(".boris")

        logging.debug(f"save config file: {iniFilePath}")

        settings = QSettings(str(iniFilePath), QSettings.IniFormat)

        settings.setValue("config", self.config_param)

        settings.setValue("geometry", self.saveGeometry())

        if self.saved_state:
            settings.setValue("dockwidget_positions", self.saved_state)

        settings.setValue("Time/Format", self.timeFormat)
        settings.setValue("Time/Repositioning_time_offset", self.repositioningTimeOffset)
        settings.setValue("Time/fast_forward_speed", self.fast)
        settings.setValue("Time/play_rate_step", self.play_rate_step)
        '''settings.setValue("Save_media_file_path", self.saveMediaFilePath)'''
        settings.setValue("Automatic_backup", self.automaticBackup)
        settings.setValue("behavioural_strings_separator", self.behaviouralStringsSeparator)
        settings.setValue("close_the_same_current_event", self.close_the_same_current_event)
        settings.setValue("confirm_sound", self.confirmSound)
        settings.setValue("beep_every", self.beep_every)
        settings.setValue("alert_nosubject", self.alertNoFocalSubject)
        settings.setValue("tracking_cursor_above_event", self.trackingCursorAboveEvent)
        settings.setValue("check_for_new_version", self.checkForNewVersion)
        # settings.setValue(DISPLAY_SUBTITLES, self.config_param[DISPLAY_SUBTITLES])
        settings.setValue("pause_before_addevent", self.pause_before_addevent)

        if lastCheckForNewVersion:
            settings.setValue("last_check_for_new_version", lastCheckForNewVersion)

        # FFmpeg
        settings.setValue("ffmpeg_cache_dir", self.ffmpeg_cache_dir)
        settings.setValue("ffmpeg_cache_dir_max_size", self.ffmpeg_cache_dir_max_size)
        '''
        # frame-by-frame
        for value in [SAVE_FRAMES, MEMORY_FOR_FRAMES]:
            settings.setValue(value, self.config_param[value])
        '''

        settings.setValue("frame_resize", self.frame_resize)
        settings.setValue("frame_bitmap_format", self.frame_bitmap_format)
        settings.setValue("frame_cache_size", self.fbf_cache_size)
        # spectrogram
        settings.setValue("spectrogram_color_map", self.spectrogram_color_map)
        settings.setValue("spectrogram_time_interval", self.spectrogram_time_interval)
        # plot colors
        settings.setValue("plot_colors", "|".join(self.plot_colors))

        # recent projects
        logging.debug("save recent projects")
        iniFilePath = str(pathlib.Path(os.path.expanduser("~")) / ".boris_recent_projects")
        settings = QSettings(iniFilePath, QSettings.IniFormat)
        settings.setValue("recent_projects", "|||".join(self.recent_projects))


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

                    self.lb_obs_time_interval.setText(("Observation time interval: "
                                                       f"{start_time} - {stop_time}"))
                else:
                    self.lb_obs_time_interval.clear()
            else:
                self.lb_obs_time_interval.clear()
        except Exception:
            logging.debug("error in observation time interval")
            pass



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
                if (event[EVENT_SUBJECT_FIELD_IDX] in selectedSubjects or
                   (not event[EVENT_SUBJECT_FIELD_IDX] and NO_FOCAL_SUBJECT in selectedSubjects)):
                    observed_behaviors.append(event[EVENT_BEHAVIOR_FIELD_IDX])

        # remove duplicate
        observed_behaviors = list(set(observed_behaviors))

        return observed_behaviors


    def choose_obs_subj_behav_category(self,
                                       selected_observations,
                                       min_time=0,
                                       maxTime=0,
                                       flagShowIncludeModifiers=True,
                                       flagShowExcludeBehaviorsWoEvents=True,
                                       by_category=False,
                                       show_time=False,
                                       show_time_bin_size=False):

        """
        show window for:
        - selection of subjects
        - selection of behaviors (based on selected subjects)
        - selection of time interval
        - inclusion/exclusion of modifiers
        - inclusion/exclusion of behaviors without events (flagShowExcludeBehaviorsWoEvents == True)
        - selection of time bin size (show_time_bin_size == True)

        Returns:
            dict: {"selected subjects": selectedSubjects,
                "selected behaviors": selectedBehaviors,
                "include modifiers": True/False,
                "exclude behaviors": True/False,
                "time": TIME_FULL_OBS / TIME_EVENTS / TIME_ARBITRARY_INTERVAL
                "start time": startTime,
                "end time": endTime
                }

        """

        paramPanelWindow = param_panel.Param_panel()
        #paramPanelWindow.resize(600, 500)
        paramPanelWindow.setWindowTitle("Select subjects and behaviors")
        paramPanelWindow.selectedObservations = selected_observations
        paramPanelWindow.pj = self.pj
        paramPanelWindow.extract_observed_behaviors = self.extract_observed_behaviors

        paramPanelWindow.cbIncludeModifiers.setVisible(flagShowIncludeModifiers)
        paramPanelWindow.cbExcludeBehaviors.setVisible(flagShowExcludeBehaviorsWoEvents)
        # show_time_bin_size:
        paramPanelWindow.frm_time_bin_size.setVisible(show_time_bin_size)

        if by_category:
            paramPanelWindow.cbIncludeModifiers.setVisible(False)
            paramPanelWindow.cbExcludeBehaviors.setVisible(False)

        # start and end time
        paramPanelWindow.frm_time_interval.setEnabled(False)
        paramPanelWindow.start_time.set_format(self.timeFormat)
        paramPanelWindow.end_time.set_format(self.timeFormat)
        paramPanelWindow.start_time.set_time(min_time)
        paramPanelWindow.end_time.set_time(maxTime)

        # hide max time
        if not maxTime:
            paramPanelWindow.frm_time.setVisible(False)

        if selected_observations:
            observedSubjects = project_functions.extract_observed_subjects(self.pj, selected_observations)
        else:
            # load all subjects and "No focal subject"
            observedSubjects = [self.pj[SUBJECTS][x][SUBJECT_NAME] for x in self.pj[SUBJECTS]] + [""]
        selectedSubjects = []

        # add 'No focal subject'
        if "" in observedSubjects:
            selectedSubjects.append(NO_FOCAL_SUBJECT)
            paramPanelWindow.item = QListWidgetItem(paramPanelWindow.lwSubjects)
            paramPanelWindow.ch = QCheckBox()
            paramPanelWindow.ch.setText(NO_FOCAL_SUBJECT)
            paramPanelWindow.ch.stateChanged.connect(paramPanelWindow.cb_changed)
            paramPanelWindow.ch.setChecked(True)
            paramPanelWindow.lwSubjects.setItemWidget(paramPanelWindow.item, paramPanelWindow.ch)

        all_subjects = [self.pj[SUBJECTS][x][SUBJECT_NAME] for x in sorted_keys(self.pj[SUBJECTS])]

        for subject in all_subjects:
            paramPanelWindow.item = QListWidgetItem(paramPanelWindow.lwSubjects)
            paramPanelWindow.ch = QCheckBox()
            paramPanelWindow.ch.setText(subject)
            paramPanelWindow.ch.stateChanged.connect(paramPanelWindow.cb_changed)
            if subject in observedSubjects:
                selectedSubjects.append(subject)
                paramPanelWindow.ch.setChecked(True)

            paramPanelWindow.lwSubjects.setItemWidget(paramPanelWindow.item, paramPanelWindow.ch)

        logging.debug(f'selectedSubjects: {selectedSubjects}')

        if selected_observations:
            observedBehaviors = self.extract_observed_behaviors(selected_observations, selectedSubjects)  # not sorted
        else:
            # load all behaviors
            observedBehaviors = [self.pj[ETHOGRAM][x][BEHAVIOR_CODE] for x in self.pj[ETHOGRAM]]

        logging.debug(f'observed behaviors: {observedBehaviors}')

        if BEHAVIORAL_CATEGORIES in self.pj:
            categories = self.pj[BEHAVIORAL_CATEGORIES][:]
            # check if behavior not included in a category
            try:
                if "" in [self.pj[ETHOGRAM][idx][BEHAVIOR_CATEGORY] for idx in self.pj[ETHOGRAM] if BEHAVIOR_CATEGORY in self.pj[ETHOGRAM][idx]]:
                    categories += [""]
            except Exception:
                categories = ["###no category###"]

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

            for behavior in [self.pj[ETHOGRAM][x][BEHAVIOR_CODE] for x in sorted_keys(self.pj[ETHOGRAM])]:

                if ((categories == ["###no category###"])
                    or (behavior in [self.pj[ETHOGRAM][x][BEHAVIOR_CODE] for x in self.pj[ETHOGRAM]
                        if BEHAVIOR_CATEGORY in self.pj[ETHOGRAM][x] and self.pj[ETHOGRAM][x][BEHAVIOR_CATEGORY] == category])):

                    paramPanelWindow.item = QListWidgetItem(behavior)
                    if behavior in observedBehaviors:
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

        gui_utilities.restore_geometry(paramPanelWindow, "param panel", (600, 500))

        if not paramPanelWindow.exec_():
            return {"selected subjects": [],
                    "selected behaviors": []}

        gui_utilities.save_geometry(paramPanelWindow, "param panel")

        selectedSubjects = paramPanelWindow.selectedSubjects
        selectedBehaviors = paramPanelWindow.selectedBehaviors

        logging.debug(f"selected subjects: {selectedSubjects}")
        logging.debug(f"selected behaviors: {selectedBehaviors}")

        startTime = paramPanelWindow.start_time.get_time()
        endTime = paramPanelWindow.end_time.get_time()
        '''
        if self.timeFormat == HHMMSS:
            startTime = time2seconds(paramPanelWindow.teStartTime.time().toString(HHMMSSZZZ))
            endTime = time2seconds(paramPanelWindow.teEndTime.time().toString(HHMMSSZZZ))
        if self.timeFormat == S:
            startTime = Decimal(paramPanelWindow.dsbStartTime.value())
            endTime = Decimal(paramPanelWindow.dsbEndTime.value())
        '''
        if startTime > endTime:
            QMessageBox.warning(None, programName, "The start time is after the end time",
                                QMessageBox.Ok | QMessageBox.Default, QMessageBox.NoButton)
            return {"selected subjects": [], "selected behaviors": []}

        if paramPanelWindow.rb_full.isChecked():
            time_param = TIME_FULL_OBS
        if paramPanelWindow.rb_limit.isChecked():
            time_param = TIME_EVENTS
        if paramPanelWindow.rb_interval.isChecked():
            time_param = TIME_ARBITRARY_INTERVAL

        return {SELECTED_SUBJECTS: selectedSubjects,
                SELECTED_BEHAVIORS: selectedBehaviors,
                INCLUDE_MODIFIERS: paramPanelWindow.cbIncludeModifiers.isChecked(),
                EXCLUDE_BEHAVIORS: paramPanelWindow.cbExcludeBehaviors.isChecked(),
                "time": time_param,
                START_TIME: startTime,
                END_TIME: endTime,
                TIME_BIN_SIZE: paramPanelWindow.sb_time_bin_size.value()
                }


    def synthetic_time_budget(self):
        """
        Synthetic time budget
        """

        result, selected_observations = self.selectObservations(MULTIPLE)
        if not selected_observations:
            return

        out = ""
        # check if coded behaviors are defined in ethogram
        ethogram_behavior_codes = {self.pj[ETHOGRAM][idx][BEHAVIOR_CODE] for idx in self.pj[ETHOGRAM]}
        behaviors_not_defined = []
        out = "" # will contain the output
        for obs_id in selected_observations:
            for event in self.pj[OBSERVATIONS][obs_id][EVENTS]:
                if event[EVENT_BEHAVIOR_FIELD_IDX] not in ethogram_behavior_codes:
                    behaviors_not_defined.append(event[EVENT_BEHAVIOR_FIELD_IDX])
        if set(sorted(behaviors_not_defined)):
            out += f"The following behaviors are not defined in the ethogram: <b>{', '.join(set(sorted(behaviors_not_defined)))}</b><br><br>"

        # check if state events are paired
        not_paired_obs_list = []
        for obs_id in selected_observations:
            r, msg = project_functions.check_state_events_obs(obs_id, self.pj[ETHOGRAM],
                                                              self.pj[OBSERVATIONS][obs_id],
                                                              self.timeFormat)
            if not r:
                out += f"Observation: <strong>{obs_id}</strong><br>{msg}<br>"
                not_paired_obs_list.append(obs_id)

        if out:
            if not_paired_obs_list:
                out += "<br>The observations with UNPAIRED state events will be removed from the analysis"
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

        selectedObsTotalMediaLength = Decimal("0.0")
        max_obs_length = 0
        for obsId in selected_observations:
            obs_length = project_functions.observation_total_length(self.pj[OBSERVATIONS][obsId])

            logging.debug(f"media length for {obsId}: {obs_length}")

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
                for obsId in selected_observations:
                    if self.pj[OBSERVATIONS][obsId][EVENTS]:
                        maxTime += max(self.pj[OBSERVATIONS][obsId][EVENTS])[0]

                logging.debug(f"max time all events all subjects: {maxTime}")

                selectedObsTotalMediaLength = maxTime
            else:
                selectedObsTotalMediaLength = 0

        synth_tb_param = self.choose_obs_subj_behav_category(selected_observations,
                                                             maxTime=max_obs_length,
                                                             flagShowExcludeBehaviorsWoEvents=False,
                                                             by_category=False)

        if not synth_tb_param[SELECTED_SUBJECTS] or not synth_tb_param[SELECTED_BEHAVIORS]:
            return

        # ask for excluding behaviors durations from total time
        cancel_pressed, synth_tb_param[EXCLUDED_BEHAVIORS] = self.filter_behaviors(title="Select behaviors to exclude",
                                                                                   text=("The duration of the selected behaviors will "
                                                                                         "be subtracted from the total time"),
                                                                                   table="",
                                                                                   behavior_type=[STATE_EVENT])

        if cancel_pressed:
            return

        extended_file_formats = ["Tab Separated Values (*.tsv)",
                                 "Comma Separated Values (*.csv)",
                                 "Open Document Spreadsheet ODS (*.ods)",
                                 "Microsoft Excel Spreadsheet XLSX (*.xlsx)",
                                 "Legacy Microsoft Excel Spreadsheet XLS (*.xls)",
                                 "HTML (*.html)"]
        file_formats = ["tsv", "csv", "ods", "xlsx", "xls", "html"]

        file_name, filter_ = QFileDialog().getSaveFileName(self, "Synthetic time budget", "", ";;".join(extended_file_formats))
        if not file_name:
            return

        output_format = file_formats[extended_file_formats.index(filter_)]
        if pathlib.Path(file_name).suffix != "." + output_format:
            file_name = str(pathlib.Path(file_name)) + "." + output_format
            if pathlib.Path(file_name).is_file():
                    if dialog.MessageDialog(programName,
                                            f"The file {file_name} already exists.",
                                            [CANCEL, OVERWRITE]) == CANCEL:
                        return

        ok, msg, data_report = time_budget_functions.synthetic_time_budget(self.pj,
                                                                           selected_observations,
                                                                           synth_tb_param
                                                                           )
        if not ok:
            results = dialog.Results_dialog()
            results.setWindowTitle("Synthetic time budget")
            results.ptText.clear()
            results.ptText.setReadOnly(True)
            results.ptText.appendHtml(msg.replace("\n", "<br>"))
            results.exec_()
            return

        if output_format in ["tsv", "csv", "html"]:
            with open(file_name, "wb") as f:
                f.write(str.encode(data_report.export(output_format)))
        if output_format in ["ods", "xlsx", "xls"]:
            with open(file_name, "wb") as f:
                f.write(data_report.export(output_format))


    def synthetic_binned_time_budget(self):
        """
        Synthetic time budget with time bin
        """

        QMessageBox.warning(None,
                            programName,
                            (f"This function is experimental. Please test it and report any bug at <br>"
                             '<a href="https://github.com/olivierfriard/BORIS/issues">'
                             'https://github.com/olivierfriard/BORIS/issues</a><br>'
                             "or by email (See the About page on the BORIS web site.<br><br>"
                             "Thank you for your collaboration!"
                             ),
                            QMessageBox.Ok | QMessageBox.Default, QMessageBox.NoButton
                            )

        result, selected_observations = self.selectObservations(MULTIPLE)
        if not selected_observations:
            return

        out = ""
        # check if coded behaviors are defined in ethogram
        ethogram_behavior_codes = {self.pj[ETHOGRAM][idx][BEHAVIOR_CODE] for idx in self.pj[ETHOGRAM]}
        behaviors_not_defined = []
        out = "" # will contain the output
        for obs_id in selected_observations:
            for event in self.pj[OBSERVATIONS][obs_id][EVENTS]:
                if event[EVENT_BEHAVIOR_FIELD_IDX] not in ethogram_behavior_codes:
                    behaviors_not_defined.append(event[EVENT_BEHAVIOR_FIELD_IDX])
        if set(sorted(behaviors_not_defined)):
            out += f"The following behaviors are not defined in the ethogram: <b>{', '.join(set(sorted(behaviors_not_defined)))}</b><br><br>"

        # check if state events are paired
        not_paired_obs_list = []
        for obs_id in selected_observations:
            r, msg = project_functions.check_state_events_obs(obs_id, self.pj[ETHOGRAM],
                                                              self.pj[OBSERVATIONS][obs_id],
                                                              self.timeFormat)
            if not r:
                out += f"Observation: <strong>{obs_id}</strong><br>{msg}<br>"
                not_paired_obs_list.append(obs_id)

        if out:
            if not_paired_obs_list:
                out += "<br>The observations with UNPAIRED state events will be removed from the analysis"
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

        selectedObsTotalMediaLength = Decimal("0.0")
        max_obs_length = 0
        for obsId in selected_observations:
            obs_length = project_functions.observation_total_length(self.pj[OBSERVATIONS][obsId])

            logging.debug(f"media length for {obsId}: {obs_length}")

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
                for obsId in selected_observations:
                    if self.pj[OBSERVATIONS][obsId][EVENTS]:
                        maxTime += max(self.pj[OBSERVATIONS][obsId][EVENTS])[0]

                logging.debug(f"max time all events all subjects: {maxTime}")

                selectedObsTotalMediaLength = maxTime
            else:
                selectedObsTotalMediaLength = 0

        synth_tb_param = self.choose_obs_subj_behav_category(selected_observations,
                                                             maxTime=max_obs_length,
                                                             flagShowExcludeBehaviorsWoEvents=False,
                                                             by_category=False,
                                                             show_time_bin_size=True)

        if not synth_tb_param[SELECTED_SUBJECTS] or not synth_tb_param[SELECTED_BEHAVIORS]:
            return

        # ask for excluding behaviors durations from total time
        cancel_pressed, synth_tb_param[EXCLUDED_BEHAVIORS] = self.filter_behaviors(title="Select behaviors to exclude",
                                                                      text=("The duration of the selected behaviors will "
                                                                            "be subtracted from the total time"),
                                                                      table="",
                                                                      behavior_type=[STATE_EVENT])
        if cancel_pressed:
            return

        extended_file_formats = ["Tab Separated Values (*.tsv)",
                                 "Comma Separated Values (*.csv)",
                                 "Open Document Spreadsheet ODS (*.ods)",
                                 "Microsoft Excel Spreadsheet XLSX (*.xlsx)",
                                 "Legacy Microsoft Excel Spreadsheet XLS (*.xls)",
                                 "HTML (*.html)"]
        file_formats = ["tsv", "csv", "ods", "xlsx", "xls", "html"]

        file_name, filter_ = QFileDialog().getSaveFileName(self, "Synthetic time budget", "", ";;".join(extended_file_formats))
        if not file_name:
            return

        output_format = file_formats[extended_file_formats.index(filter_)]
        if pathlib.Path(file_name).suffix != "." + output_format:
            file_name = str(pathlib.Path(file_name)) + "." + output_format
            if pathlib.Path(file_name).is_file():
                    if dialog.MessageDialog(programName,
                                            f"The file {file_name} already exists.",
                                            [CANCEL, OVERWRITE]) == CANCEL:
                        return

        ok, data_report = time_budget_functions.synthetic_time_budget_bin(self.pj,
                                                                           selected_observations,
                                                                           synth_tb_param
                                                                           )

        if not ok:
            results = dialog.Results_dialog()
            results.setWindowTitle("Synthetic time budget with time bin")
            results.ptText.clear()
            results.ptText.setReadOnly(True)
            results.ptText.appendHtml(msg.replace("\n", "<br>"))
            results.exec_()
            return

        if output_format in ["tsv", "csv", "html"]:
            with open(file_name, "wb") as f:
                f.write(str.encode(data_report.export(output_format)))
        if output_format in ["ods", "xlsx", "xls"]:
            with open(file_name, "wb") as f:
                f.write(data_report.export(output_format))



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
            if dialog.MessageDialog(programName,
                                    (f"A media length is not available for the observation <b>{obs_id}</b>.<br>"
                                     "Use last event time as media length?"),
                                    [YES, NO]) == YES:
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


    def time_budget(self, mode:str, mode2:str = "list"):
        """
        time budget (by behavior or category)

        Args:
            mode (str): ["by_behavior", "by_category"]
            mode2 (str): must be in ["list", "current"]
        """

        if mode2 == "current" and self.observationId:
            selectedObservations = [self.observationId]
        if mode2 == "list":
            result, selectedObservations = self.selectObservations(MULTIPLE)
            if not selectedObservations:
                return

        # check if coded behaviors are defined in ethogram
        ethogram_behavior_codes = {self.pj[ETHOGRAM][idx][BEHAVIOR_CODE] for idx in self.pj[ETHOGRAM]}
        behaviors_not_defined = []
        out = ""  # will contain the output
        for obs_id in selectedObservations:
            for event in self.pj[OBSERVATIONS][obs_id][EVENTS]:
                if event[EVENT_BEHAVIOR_FIELD_IDX] not in ethogram_behavior_codes:
                    behaviors_not_defined.append(event[EVENT_BEHAVIOR_FIELD_IDX])
        if set(sorted(behaviors_not_defined)):
            out += ("The following behaviors are not defined in the ethogram: "
                    f"<b>{', '.join(set(sorted(behaviors_not_defined)))}</b><br><br>")

        # check if state events are paired
        not_paired_obs_list = []
        for obs_id in selectedObservations:
            r, msg = project_functions.check_state_events_obs(obs_id,
                                                              self.pj[ETHOGRAM],
                                                              self.pj[OBSERVATIONS][obs_id],
                                                              self.timeFormat)

            if not r:
                out += f"Observation: <strong>{obs_id}</strong><br>{msg}<br>"
                not_paired_obs_list.append(obs_id)

        if out:
            out = f"Some selected observations have issues:<br><br>{out}"
            self.results = dialog.Results_dialog()
            self.results.setWindowTitle(f"{programName} - Check selected observations")
            self.results.ptText.setReadOnly(True)
            self.results.ptText.appendHtml(out)
            self.results.pbSave.setVisible(False)
            self.results.pbCancel.setVisible(True)

            if not self.results.exec_():
                return

        flagGroup = False
        if len(selectedObservations) > 1:
            flagGroup = dialog.MessageDialog(programName,
                                             "Group observations in one time budget analysis?",
                                             [YES, NO]) == YES

        max_obs_length, selectedObsTotalMediaLength = self.observation_length(selectedObservations)
        if max_obs_length == -1: # media length not available, user choose to not use events
            return

        logging.debug(f"max_obs_length: {max_obs_length}, selectedObsTotalMediaLength: {selectedObsTotalMediaLength}")

        parameters = self.choose_obs_subj_behav_category(selectedObservations,
                                                         maxTime=max_obs_length if len(selectedObservations) > 1 else selectedObsTotalMediaLength,
                                                         by_category=(mode == "by_category"))

        if not parameters[SELECTED_SUBJECTS] or not parameters[SELECTED_BEHAVIORS]:
            return

        # ask for excluding behaviors durations from total time
        cancel_pressed, parameters[EXCLUDED_BEHAVIORS] = self.filter_behaviors(title="Select behaviors to exclude",
                                                                   text=("The duration of the selected behaviors will "
                                                                         "be subtracted from the total time"),
                                                                   table="",
                                                                   behavior_type=[STATE_EVENT])
        if cancel_pressed:
            return

        # check if time_budget window must be used
        if flagGroup or len(selectedObservations) == 1:

            cursor = db_functions.load_events_in_db(self.pj,
                                                    parameters[SELECTED_SUBJECTS],
                                                    selectedObservations,
                                                    parameters[SELECTED_BEHAVIORS],
                                                    time_interval=TIME_FULL_OBS)

            total_observation_time = 0
            for obsId in selectedObservations:

                obs_length = project_functions.observation_total_length(self.pj[OBSERVATIONS][obsId])

                if obs_length == Decimal("-1"): # media length not available
                    parameters[TIME_INTERVAL] = TIME_EVENTS

                if parameters[TIME_INTERVAL] == TIME_FULL_OBS:
                    min_time = float(0)
                    # check if the last event is recorded after media file length
                    try:
                        if float(self.pj[OBSERVATIONS][obsId][EVENTS][-1][0]) > float(obs_length):
                            max_time = float(self.pj[OBSERVATIONS][obsId][EVENTS][-1][0])
                        else:
                            max_time = float(obs_length)
                    except Exception:
                        max_time = float(obs_length)

                if parameters[TIME_INTERVAL] == TIME_EVENTS:
                    try:
                        min_time = float(self.pj[OBSERVATIONS][obsId][EVENTS][0][0])  # first event
                    except Exception:
                        min_time = float(0)
                    try:
                        max_time = float(self.pj[OBSERVATIONS][obsId][EVENTS][-1][0])  # last event
                    except Exception:
                        max_time = float(obs_length)

                if parameters[TIME_INTERVAL] == TIME_ARBITRARY_INTERVAL:
                    min_time = float(parameters[START_TIME])
                    max_time = float(parameters[END_TIME])

                    # check intervals
                    for subj in parameters[SELECTED_SUBJECTS]:
                        for behav in parameters[SELECTED_BEHAVIORS]:
                            if POINT in self.eventType(behav).upper():
                                continue
                            # extract modifiers

                            cursor.execute("SELECT distinct modifiers FROM events WHERE observation = ? AND subject = ? AND code = ?",
                                           (obsId, subj, behav))
                            distinct_modifiers = list(cursor.fetchall())

                            # logging.debug("distinct_modifiers: {}".format(distinct_modifiers))

                            for modifier in distinct_modifiers:

                                # logging.debug("modifier #{}#".format(modifier[0]))

                                # insert events at boundaries of time interval
                                if len(cursor.execute(("SELECT * FROM events "
                                                       "WHERE observation = ? AND subject = ? AND code = ? AND modifiers = ? "
                                                       "AND occurence < ?"),
                                                      (obsId, subj, behav, modifier[0], min_time)).fetchall()) % 2:

                                    cursor.execute(("INSERT INTO events (observation, subject, code, type, modifiers, occurence) "
                                                    "VALUES (?,?,?,?,?,?)"),
                                                   (obsId, subj, behav, "STATE", modifier[0], min_time))

                                if len(cursor.execute(("SELECT * FROM events WHERE observation = ? AND subject = ? AND code = ? "
                                                       "AND modifiers = ? AND occurence > ?"),
                                                      (obsId, subj, behav, modifier[0], max_time)).fetchall()) % 2:

                                    cursor.execute(("INSERT INTO events (observation, subject, code, type, modifiers, occurence) "
                                                    "VALUES (?,?,?,?,?,?)"),
                                                   (obsId, subj, behav, "STATE", modifier[0], max_time))
                            try:
                                cursor.execute("COMMIT")
                            except Exception:
                                pass

                total_observation_time += (max_time - min_time)

                # delete all events out of time interval from db
                cursor.execute("DELETE FROM events WHERE observation = ? AND (occurence < ? OR occurence > ?)",
                               (obsId, min_time, max_time))

            out, categories = time_budget_functions.time_budget_analysis(self.pj[ETHOGRAM],
                                                                         cursor,
                                                                         selectedObservations,
                                                                         parameters,
                                                                         by_category=(mode == "by_category"))

            # check excluded behaviors
            excl_behaviors_total_time = {}
            for element in out:
                if element["subject"] not in excl_behaviors_total_time:
                    excl_behaviors_total_time[element["subject"]] = 0
                if element["behavior"] in parameters[EXCLUDED_BEHAVIORS]:
                    excl_behaviors_total_time[element["subject"]] += element["duration"] if not isinstance(element["duration"], str) else 0

            # widget for results visualization
            self.tb = timeBudgetResults(self.pj, self.config_param)

            # add min and max time
            self.tb.min_time = min_time
            self.tb.max_time = max_time

            # observations list
            self.tb.label.setText("Selected observations")
            for obs_id in selectedObservations:
                # self.tb.lw.addItem(f"{obs_id}  {self.pj[OBSERVATIONS][obs_id]['date']}  {self.pj[OBSERVATIONS][obs_id]['description']}")
                self.tb.lw.addItem(obs_id)

            # media length
            if len(selectedObservations) > 1:
                if total_observation_time:
                    if self.timeFormat == HHMMSS:
                        self.tb.lbTotalObservedTime.setText(f"Total observation length: {seconds2time(total_observation_time)}")
                    if self.timeFormat == S:
                        self.tb.lbTotalObservedTime.setText(f"Total observation length: {float(total_observation_time):0.3f}")
                else:
                    self.tb.lbTotalObservedTime.setText("Total observation length: not available")
            else:
                if self.timeFormat == HHMMSS:
                    self.tb.lbTotalObservedTime.setText(f"Analysis from {seconds2time(min_time)} to {seconds2time(max_time)}")
                if self.timeFormat == S:
                    self.tb.lbTotalObservedTime.setText(f"Analysis from {float(min_time):0.3f} to {float(max_time):0.3f} s")

            # behaviors excluded from total time
            if parameters[EXCLUDED_BEHAVIORS]:
                self.tb.excluded_behaviors_list.setText("Behaviors excluded from total time: "
                                                        + (", ".join(parameters[EXCLUDED_BEHAVIORS])))
            else:
                self.tb.excluded_behaviors_list.setVisible(False)

            if mode == "by_behavior":

                tb_fields = ["Subject", "Behavior", "Modifiers", "Total number of occurences", "Total duration (s)",
                             "Duration mean (s)", "Duration std dev", "inter-event intervals mean (s)",
                             "inter-event intervals std dev", "% of total length"]
                fields = ["subject", "behavior", "modifiers", "number", "duration", "duration_mean",
                          "duration_stdev", "inter_duration_mean", "inter_duration_stdev"]

                self.tb.twTB.setColumnCount(len(tb_fields))
                self.tb.twTB.setHorizontalHeaderLabels(tb_fields)

                for row in out:
                    self.tb.twTB.setRowCount(self.tb.twTB.rowCount() + 1)
                    column = 0
                    for field in fields:
                        '''
                        if field == "duration":
                            item = QTableWidgetItem("{:0.3f}".format(row[field]))
                        else:
                        '''
                        item = QTableWidgetItem(str(row[field]).replace(" ()", ""))
                        # no modif allowed
                        item.setFlags(Qt.ItemIsEnabled)
                        self.tb.twTB.setItem(self.tb.twTB.rowCount() - 1, column, item)
                        column += 1

                    # % of total time
                    if row["duration"] in [0, NA]:
                        item = QTableWidgetItem(str(row["duration"]))
                    elif row["duration"] not in ["-", UNPAIRED] and selectedObsTotalMediaLength:
                        tot_time = float(total_observation_time)
                        # substract time of excluded behaviors from the total for the subject
                        if (row["subject"] in excl_behaviors_total_time and row["behavior"] not in parameters[EXCLUDED_BEHAVIORS]):
                            tot_time -= excl_behaviors_total_time[row["subject"]]
                        item = QTableWidgetItem(str(round(row["duration"] / tot_time * 100, 1)) if tot_time > 0 else "-")
                    else:
                        item = QTableWidgetItem("-")

                    item.setFlags(Qt.ItemIsEnabled)
                    self.tb.twTB.setItem(self.tb.twTB.rowCount() - 1, column, item)

            if mode == "by_category":

                tb_fields = ["Subject", "Category", "Total number", "Total duration (s)"]
                fields = ["number", "duration"]

                self.tb.twTB.setColumnCount(len(tb_fields))
                self.tb.twTB.setHorizontalHeaderLabels(tb_fields)

                for subject in categories:

                    for category in categories[subject]:

                        self.tb.twTB.setRowCount(self.tb.twTB.rowCount() + 1)

                        column = 0
                        item = QTableWidgetItem(subject)
                        item.setFlags(Qt.ItemIsEnabled)
                        self.tb.twTB.setItem(self.tb.twTB.rowCount() - 1, column, item)

                        column = 1
                        if category == "":
                            item = QTableWidgetItem("No category")
                        else:
                            item = QTableWidgetItem(category)
                        item.setFlags(Qt.ItemIsEnabled)
                        self.tb.twTB.setItem(self.tb.twTB.rowCount() - 1, column, item)

                        for field in fields:
                            column += 1

                            if field == "duration":
                                try:
                                    item = QTableWidgetItem("{:0.3f}".format(categories[subject][category][field]))
                                except Exception:
                                    item = QTableWidgetItem(categories[subject][category][field])
                            else:
                                item = QTableWidgetItem(str(categories[subject][category][field]))
                            item.setFlags(Qt.ItemIsEnabled)
                            item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                            self.tb.twTB.setItem(self.tb.twTB.rowCount() - 1, column, item)

            self.tb.twTB.resizeColumnsToContents()

            gui_utilities.restore_geometry(self.tb, "time budget", (0, 0))

            self.tb.show()



        if len(selectedObservations) > 1 and not flagGroup:

            items = ("Tab Separated Values (*.tsv)",
                     "Comma separated values (*.csv)",
                     "OpenDocument Spreadsheet (*.ods)",
                     "OpenDocument Workbook (*.ods)",
                     "Microsoft Excel Spreadsheet (*.xlsx)",
                     "Microsoft Excel Workbook (*.xlsx)",
                     "HTML (*.html)",
                     "Legacy Microsoft Excel Spreadsheet (*.xls)")

            formats = ["tsv", "csv", "od spreadsheet", "od workbook", "xlsx spreadsheet", "xlsx workbook", "html", "xls legacy"]

            item, ok = QInputDialog.getItem(self, "Time budget analysis format", "Available formats", items, 0, False)
            if not ok:
                return

            outputFormat = formats[items.index(item)]
            extension = re.sub(".* \(\*\.", "", item)[:-1]

            flagWorkBook = False

            if "workbook" in outputFormat:
                workbook = tablib.Databook()
                flagWorkBook = True
                if "xls" in outputFormat:
                    filters = "Microsoft Excel Workbook *.xlsx (*.xlsx);;All files (*)"
                if "od" in outputFormat:
                    filters = "Open Document Workbook *.ods (*.ods);;All files (*)"

                WBfileName, filter_ = QFileDialog(self).getSaveFileName(self, "Save Time budget analysis", "", filters)
                if not WBfileName:
                    return

            else:  # not workbook
                exportDir = QFileDialog(self).getExistingDirectory(self, "Choose a directory to save the time budget analysis",
                                                                   os.path.expanduser("~"), options=QFileDialog.ShowDirsOnly)
                if not exportDir:
                    return

            if mode == "by_behavior":

                tb_fields = ["Subject", "Behavior", "Modifiers", "Total number of occurences", "Total duration (s)",
                             "Duration mean (s)", "Duration std dev", "inter-event intervals mean (s)",
                             "inter-event intervals std dev", "% of total length"]
                fields = ["subject", "behavior", "modifiers", "number",
                          "duration", "duration_mean", "duration_stdev",
                          "inter_duration_mean", "inter_duration_stdev"]

            if mode == "by_category":

                tb_fields = ["Subject", "Category", "Total number of occurences", "Total duration (s)"]
                fields = ["subject", "category", "number", "duration"]

            mem_command = ""
            for obsId in selectedObservations:

                cursor = db_functions.load_events_in_db(self.pj,
                                                        parameters[SELECTED_SUBJECTS],
                                                        [obsId],
                                                        parameters[SELECTED_BEHAVIORS])

                obs_length = project_functions.observation_total_length(self.pj[OBSERVATIONS][obsId])

                if obs_length == -1:
                    obs_length = 0

                if parameters["time"] == TIME_FULL_OBS:
                    min_time = float(0)
                    # check if the last event is recorded after media file length
                    try:
                        if float(self.pj[OBSERVATIONS][obsId][EVENTS][-1][0]) > float(obs_length):
                            max_time = float(self.pj[OBSERVATIONS][obsId][EVENTS][-1][0])
                        else:
                            max_time = float(obs_length)
                    except Exception:
                        max_time = float(obs_length)

                if parameters["time"] == TIME_EVENTS:
                    try:
                        min_time = float(self.pj[OBSERVATIONS][obsId][EVENTS][0][0])
                    except Exception:
                        min_time = float(0)
                    try:
                        max_time = float(self.pj[OBSERVATIONS][obsId][EVENTS][-1][0])
                    except Exception:
                        max_time = float(obs_length)

                if parameters["time"] == TIME_ARBITRARY_INTERVAL:
                    min_time = float(parameters[START_TIME])
                    max_time = float(parameters[END_TIME])

                    # check intervals
                    for subj in parameters[SELECTED_SUBJECTS]:
                        for behav in parameters[SELECTED_BEHAVIORS]:
                            if POINT in project_functions.event_type(behav, self.pj[ETHOGRAM]):  # self.eventType(behav).upper():
                                continue
                            # extract modifiers
                            # if plot_parameters["include modifiers"]:

                            cursor.execute("SELECT distinct modifiers FROM events WHERE observation = ? AND subject = ? AND code = ?",
                                           (obsId, subj, behav))
                            distinct_modifiers = list(cursor.fetchall())

                            for modifier in distinct_modifiers:

                                if len(cursor.execute(("SELECT * FROM events "
                                                       "WHERE observation = ? AND subject = ? "
                                                       "AND code = ? AND modifiers = ? AND occurence < ?"),
                                                      (obsId, subj, behav, modifier[0], min_time)).fetchall()) % 2:
                                    cursor.execute(("INSERT INTO events (observation, subject, code, type, modifiers, occurence) "
                                                    "VALUES (?,?,?,?,?,?)"), (obsId, subj, behav, "STATE", modifier[0], min_time))
                                if len(cursor.execute(("SELECT * FROM events WHERE observation = ? AND subject = ? AND code = ?"
                                                       " AND modifiers = ? AND occurence > ?"),
                                                      (obsId, subj, behav, modifier[0], max_time)).fetchall()) % 2:
                                    cursor.execute(("INSERT INTO events (observation, subject, code, type, modifiers, occurence) "
                                                    "VALUES (?,?,?,?,?,?)"), (obsId, subj, behav, STATE, modifier[0], max_time))
                            try:
                                cursor.execute("COMMIT")
                            except Exception:
                                pass

                cursor.execute("DELETE FROM events WHERE observation = ? AND (occurence < ? OR occurence > ?)",
                               (obsId, min_time, max_time))

                out, categories = time_budget_functions.time_budget_analysis(self.pj[ETHOGRAM],
                                                                             cursor,
                                                                             [obsId],
                                                                             parameters,
                                                                             by_category=(mode == "by_category"))

                # check excluded behaviors
                excl_behaviors_total_time = {}
                for element in out:
                    if element["subject"] not in excl_behaviors_total_time:
                        excl_behaviors_total_time[element["subject"]] = 0
                    if element["behavior"] in parameters[EXCLUDED_BEHAVIORS]:
                        excl_behaviors_total_time[element["subject"]] += element["duration"] if element["duration"] != "NA" else 0

                # compact format
                if self.config_param.get(TIME_BUDGET_FORMAT, DEFAULT_TIME_BUDGET_FORMAT) == COMPACT_TIME_BUDGET_FORMAT:
                    rows = []
                    col1 = []
                    # observation id
                    col1.append(obsId)
                    col1.append(self.pj[OBSERVATIONS][obsId].get("date", ""))
                    col1.append(utilities.eol2space(self.pj[OBSERVATIONS][obsId].get(DESCRIPTION, "")))
                    header = ["Observation id", "Observation date", "Description"]

                    indep_var_label = []
                    indep_var_values = []
                    if INDEPENDENT_VARIABLES in self.pj and self.pj[INDEPENDENT_VARIABLES]:
                        for idx in self.pj[INDEPENDENT_VARIABLES]:
                            indep_var_label.append(self.pj[INDEPENDENT_VARIABLES][idx]["label"])

                            if (INDEPENDENT_VARIABLES in self.pj[OBSERVATIONS][obsId]
                                    and self.pj[INDEPENDENT_VARIABLES][idx]["label"] in self.
                                    pj[OBSERVATIONS][obsId][INDEPENDENT_VARIABLES]):
                                indep_var_values.append(self.pj[OBSERVATIONS][obsId][INDEPENDENT_VARIABLES][
                                    self.pj[INDEPENDENT_VARIABLES][idx]["label"]])

                    header.extend(indep_var_label)
                    col1.extend(indep_var_values)

                    # interval analysis
                    col1.extend([f"{min_time:0.3f}", f"{max_time:0.3f}", f"{max_time - min_time:0.3f}"])
                    header.extend(["Time budget start", "Time budget stop", "Time budget duration"])

                    if mode == "by_behavior":

                        # header
                        rows.append(header + tb_fields)

                        for row in out:
                            values = []
                            for field in fields:
                                values.append(str(row[field]).replace(" ()", ""))
                            # % of total time
                            if row["duration"] in [0, NA]:
                                values.append(row["duration"])
                            elif row["duration"] not in ["-", UNPAIRED] and selectedObsTotalMediaLength:
                                tot_time = float(max_time - min_time)
                                # substract duration of excluded behaviors from total time for each subject
                                if (row["subject"] in excl_behaviors_total_time and row["behavior"] not in parameters[EXCLUDED_BEHAVIORS]):
                                    tot_time -= excl_behaviors_total_time[row["subject"]]
                                # % of tot time
                                values.append(round(row["duration"] / tot_time * 100, 1) if tot_time > 0 else "-")
                            else:
                                values.append("-")

                            rows.append(col1 + values)

                    if mode == "by_category":
                        rows.append(header + tb_fields)

                        for subject in categories:

                            for category in categories[subject]:
                                values = []
                                values.append(subject)
                                if category == "":
                                    values.append("No category")
                                else:
                                    values.append(category)

                                values.append(categories[subject][category]["number"])
                                try:
                                    values.append(f"{categories[subject][category]['duration']:0.3f}")
                                except Exception:
                                    values.append(categories[subject][category]["duration"])

                                rows.append(col1 + values)

                # long format
                if self.config_param.get(TIME_BUDGET_FORMAT, DEFAULT_TIME_BUDGET_FORMAT) == LONG_TIME_BUDGET_FORMAT:

                    rows = []
                    # observation id
                    rows.append(["Observation id", obsId])
                    rows.append([""])

                    labels = ["Independent variables"]
                    values = [""]
                    if INDEPENDENT_VARIABLES in self.pj and self.pj[INDEPENDENT_VARIABLES]:
                        for idx in self.pj[INDEPENDENT_VARIABLES]:
                            labels.append(self.pj[INDEPENDENT_VARIABLES][idx]["label"])

                            if (INDEPENDENT_VARIABLES in self.pj[OBSERVATIONS][obsId]
                                    and self.pj[INDEPENDENT_VARIABLES][idx]["label"] in self.
                                    pj[OBSERVATIONS][obsId][INDEPENDENT_VARIABLES]):
                                values.append(self.pj[OBSERVATIONS][obsId][INDEPENDENT_VARIABLES][
                                    self.pj[INDEPENDENT_VARIABLES][idx]["label"]])

                    rows.append(labels)
                    rows.append(values)
                    rows.append([""])

                    rows.append(["Analysis from", f"{min_time:0.3f}", "to", f"{max_time:0.3f}"])
                    rows.append(["Total length (s)", f"{max_time - min_time:0.3f}"])
                    rows.append([""])
                    rows.append(["Time budget"])

                    if mode == "by_behavior":

                        rows.append(tb_fields)

                        for row in out:
                            values = []
                            for field in fields:
                                values.append(str(row[field]).replace(" ()", ""))
                            # % of total time
                            if row["duration"] in [0, NA]:
                                values.append(row["duration"])
                            elif row["duration"] not in ["-", UNPAIRED] and selectedObsTotalMediaLength:
                                tot_time = float(max_time - min_time)
                                # substract duration of excluded behaviors from total time for each subject
                                if (row["subject"] in excl_behaviors_total_time and row["behavior"] not in parameters[EXCLUDED_BEHAVIORS]):
                                    tot_time -= excl_behaviors_total_time[row["subject"]]
                                values.append(round(row["duration"] / tot_time * 100, 1) if tot_time > 0 else "-")
                            else:
                                values.append("-")

                            rows.append(values)

                    if mode == "by_category":
                        rows.append(tb_fields)

                        for subject in categories:

                            for category in categories[subject]:
                                values = []
                                values.append(subject)
                                if category == "":
                                    values.append("No category")
                                else:
                                    values.append(category)

                                values.append(categories[subject][category]["number"])
                                try:
                                    values.append(f"{categories[subject][category]['duration']:0.3f}")
                                except Exception:
                                    values.append(categories[subject][category]["duration"])

                                rows.append(values)

                data = tablib.Dataset()
                data.title = obsId
                for row in rows:
                    data.append(complete(row, max([len(r) for r in rows])))

                # check worksheet/workbook title for forbidden char (excel)
                data.title = utilities.safe_xl_worksheet_title(data.title, extension)

                '''
                if "xls" in outputFormat:
                    for forbidden_char in EXCEL_FORBIDDEN_CHARACTERS:
                        data.title = data.title.replace(forbidden_char, " ")
                '''

                if flagWorkBook:
                    '''
                    for forbidden_char in EXCEL_FORBIDDEN_CHARACTERS:
                        data.title = data.title.replace(forbidden_char, " ")
                    if "xls" in outputFormat:
                        if len(data.title) > 31:
                            data.title = data.title[:31]
                    '''
                    workbook.add_sheet(data)

                else:

                    fileName = f"{pathlib.Path(exportDir) / pathlib.Path(safeFileName(obsId))}.{extension}"
                    if mem_command != OVERWRITE_ALL and pathlib.Path(fileName).is_file():
                        if mem_command == "Skip all":
                            continue
                        mem_command = dialog.MessageDialog(programName,
                                                        f"The file {fileName} already exists.",
                                                        [OVERWRITE, OVERWRITE_ALL, "Skip", "Skip all", CANCEL])
                        if mem_command == CANCEL:
                            return
                        if mem_command in ["Skip", "Skip all"]:
                            continue

                    if outputFormat in ["tsv", "csv", "html"]:
                        with open(fileName, "wb") as f:
                            f.write(str.encode(data.export(outputFormat)))

                    if outputFormat == "od spreadsheet":
                        with open(fileName, "wb") as f:
                            f.write(data.ods)

                    if outputFormat == "xlsx spreadsheet":
                        with open(fileName, "wb") as f:
                            f.write(data.xlsx)

                    if outputFormat == "xls legacy":
                        '''
                        if len(data.title) > 31:
                            data.title = data.title[:31]
                            QMessageBox.warning(
                                None,
                                programName,
                                (f"The worksheet name <b>{obsId}</b> was shortened to <b>{data.title}</b> due to XLS format limitations.\n"
                                 "The limit on worksheet name length is 31 characters"),
                                QMessageBox.Ok | QMessageBox.Default, QMessageBox.NoButton
                            )
                        '''

                        with open(fileName, "wb") as f:
                            f.write(data.xls)

            if flagWorkBook:
                if "xls" in outputFormat:
                    with open(WBfileName, "wb") as f:
                        f.write(workbook.xlsx)
                if "od" in outputFormat:
                    with open(WBfileName, "wb") as f:
                        f.write(workbook.ods)


    def plot_events_triggered(self, mode:str = "list"):
        """
        plot events in time diagram
        """
        if mode == "list":
            result, selected_observations = self.selectObservations(MULTIPLE)

            if not selected_observations:
                return
        if mode == "current" and self.observationId:
            selected_observations = [self.observationId]
        # check if state events are paired
        out = ""
        not_paired_obs_list = []
        for obs_id in selected_observations:
            r, msg = project_functions.check_state_events_obs(obs_id, self.pj[ETHOGRAM],
                                                              self.pj[OBSERVATIONS][obs_id], self.timeFormat)

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
        '''
        flag_no_events = True
        for obs_id in selected_observations:
            if self.pj[OBSERVATIONS][obs_id][EVENTS]:
                flag_no_events = False
                break
        if flag_no_events:
            QMessageBox.warning(self, programName, "No events found in the selected observations")
            return
        '''
        # select dir if many observations
        plot_directory = ""
        file_format = "png"
        if len(selected_observations) > 1:
            plot_directory = QFileDialog().getExistingDirectory(self, "Choose a directory to save the plots",
                                                                os.path.expanduser("~"),
                                                                options=QFileDialog(self).ShowDirsOnly)

            if not plot_directory:
                return

            item, ok = QInputDialog.getItem(self, "Select the file format", "Available formats",
                                            ["PNG", "SVG", "PDF", "EPS", "PS"], 0, False)
            if ok and item:
                file_format = item.lower()
            else:
                return


        max_obs_length, selectedObsTotalMediaLength = self.observation_length(selected_observations)
        if max_obs_length == -1: # media length not available, user choose to not use events
            return

        '''
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
        '''

        parameters = self.choose_obs_subj_behav_category(selected_observations,
                                                         maxTime=max_obs_length,
                                                         flagShowExcludeBehaviorsWoEvents=True,
                                                         by_category=False)

        if not parameters[SELECTED_SUBJECTS] or not parameters[SELECTED_BEHAVIORS]:
            QMessageBox.warning(self, programName, "Select subject(s) and behavior(s) to plot")
            return

        plot_events.create_events_plot(self.pj,
                                       selected_observations,
                                       parameters,
                                       plot_colors=self.plot_colors,
                                       plot_directory=plot_directory,
                                       file_format=file_format)


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
            r, msg = project_functions.check_state_events_obs(obsId, self.pj[ETHOGRAM],
                                                              self.pj[OBSERVATIONS][obsId], self.timeFormat)

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
            parameters = self.choose_obs_subj_behav_category(selected_observations,
                                                             maxTime=totalMediaLength,
                                                             flagShowIncludeModifiers=False,
                                                             flagShowExcludeBehaviorsWoEvents=True)
        else:
            parameters = self.choose_obs_subj_behav_category(selected_observations,
                                                             maxTime=0,
                                                             flagShowIncludeModifiers=False,
                                                             flagShowExcludeBehaviorsWoEvents=True
                                                             )

        if not parameters[SELECTED_SUBJECTS] or not parameters[SELECTED_BEHAVIORS]:
            QMessageBox.warning(self, programName, "Select subject(s) and behavior(s) to plot")
            return

        plot_directory = ""
        output_format = ""
        if len(selected_observations) > 1:
            plot_directory = QFileDialog().getExistingDirectory(self, "Choose a directory to save the plots",
                                                                os.path.expanduser("~"),
                                                                options=QFileDialog(self).ShowDirsOnly)
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
                                                  plot_colors=self.plot_colors
                                                 )
        if "error" in r:
            if "exception" in r:
                dialog.error_message("Time budget bar plot", r["exception"])
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
        self.menu_options()


    def open_project_activated(self):
        """
        open a project
        triggered by Open project menu and recent projects submenu
        """

        action = self.sender()

         # check if current observation
        if self.observationId:
            if dialog.MessageDialog(programName, "There is a current observation. What do you want to do?",
                                    ["Close observation", "Continue observation"]) == "Close observation":
                self.close_observation()
            else:
                return

        if self.projectChanged:
            response = dialog.MessageDialog(programName, "What to do about the current unsaved project?", [SAVE, DISCARD, CANCEL])

            if response == SAVE:
                if self.save_project_activated() == "not saved":
                    return

            if response == CANCEL:
                return

        if action.text() == "Open project":
            fn = QFileDialog().getOpenFileName(self, "Open project", "",
                                               ("Project files (*.boris *.boris.gz);;"
                                                "All files (*)")
                                              )
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

                    if flag_all_upper and dialog.MessageDialog(
                            programName,
                            ("It is now possible to use <b>lower keys</b> to code behaviors, subjects and modifiers.<br><br>"
                             "In this project all the behavior and subject keys are upper case.<br>"
                             "Do you want to convert them in lower case?"),
                            [YES, NO]) == YES:
                        for idx in pj[ETHOGRAM]:
                            pj[ETHOGRAM][idx]["key"] = pj[ETHOGRAM][idx]["key"].lower()
                            # convert modifier short cuts to lower case
                            for modifier_set in pj[ETHOGRAM][idx]["modifiers"]:
                                try:
                                    for idx2, value in enumerate(pj[ETHOGRAM][idx]["modifiers"][modifier_set]["values"]):
                                        if re.findall(r'\((\w+)\)', value):
                                            pj[ETHOGRAM][idx]["modifiers"][modifier_set]["values"][idx2] = value.split("(")[0] + "(" + re.findall(r'\((\w+)\)', value)[0].lower() + ")" + value.split(")")[-1]
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
            if dialog.MessageDialog(programName, "There is a current observation. What do you want to do?",
                                    ["Close observation", "Continue observation"]) == "Close observation":
                self.close_observation()
            else:
                return

        if self.projectChanged:
            response = dialog.MessageDialog(programName, "What to do about the current unsaved project?", [SAVE, DISCARD, CANCEL])

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
            response = dialog.MessageDialog(programName,
                                            "There is a current observation. What do you want to do?",
                                            ["Close observation", "Continue observation"])
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
        self.readConfigFile()
        self.menu_options()

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
                    w.setRowCount(0)   # behaviors

            newProjectWindow = projectDialog()

            # pass copy of self.pj
            newProjectWindow.pj = dict(self.pj)

            if self.projectWindowGeometry:
                newProjectWindow.restoreGeometry(self.projectWindowGeometry)
            else:
                newProjectWindow.resize(800, 400)

            newProjectWindow.setWindowTitle(mode + " project")
            newProjectWindow.tabProject.setCurrentIndex(0)   # project information

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
                    newProjectWindow.dteDate.setDateTime(QDateTime.fromString(newProjectWindow.pj[PROJECT_DATE],
                                                        "yyyy-MM-ddThh:mm:ss"))
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
                        newProjectWindow.twObservations.setItem(newProjectWindow.twObservations.rowCount() - 1,
                                                                0,
                                                                QTableWidgetItem(obs))
                        # observation date
                        newProjectWindow.twObservations.setItem(newProjectWindow.twObservations.rowCount() - 1,
                                                                1,
                                                                QTableWidgetItem(
                                                                    newProjectWindow.pj[OBSERVATIONS][obs]["date"].replace("T", " ")))
                        # observation description
                        newProjectWindow.twObservations.setItem(newProjectWindow.twObservations.rowCount() - 1,
                                                                2,
                                                                QTableWidgetItem(
                                                                    utilities.eol2space(newProjectWindow.pj[OBSERVATIONS][obs][DESCRIPTION])))

                        mediaList = []
                        if newProjectWindow.pj[OBSERVATIONS][obs][TYPE] in [MEDIA]:
                            for idx in newProjectWindow.pj[OBSERVATIONS][obs][FILE]:
                                for media in newProjectWindow.pj[OBSERVATIONS][obs][FILE][idx]:
                                    mediaList.append(f"#{idx}: {media}")

                        elif newProjectWindow.pj[OBSERVATIONS][obs][TYPE] in [LIVE]:
                            mediaList = [LIVE]

                        media_separator = " " if len(mediaList) > 8 else "\n"
                        newProjectWindow.twObservations.setItem(newProjectWindow.twObservations.rowCount() - 1,
                                                                3,
                                                                QTableWidgetItem(media_separator.join(mediaList)))

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

                if dialog.MessageDialog(programName,
                                    ("Please note that editing the project may interfere with the coded events in your previous observations.<br>"
                                    "For example modifying a behavior code, renaming a subject or modifying the modifiers sets "
                                    "can unvalidate your previous observations.<br>"
                                    "Remember to make a backup of your project."),
                                    [CANCEL, "Edit"]) == CANCEL:
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

                self.menu_options()

            self.projectWindowGeometry = newProjectWindow.saveGeometry()

            del newProjectWindow

        except Exception:
            dialog.error_message("Close observation", sys.exc_info())


    def new_project_activated(self):
        """
        new project
        """
        self.edit_project(NEW)


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
            QMessageBox.critical(None, programName, f"Permission denied to save the project file. Try another directory",
                                 QMessageBox.Ok | QMessageBox.Default, QMessageBox.NoButton)
            self.save_project_json_started = False
            return 1

        except Exception:
            dialog.error_message("save_project_json", sys.exc_info())

            self.save_project_json_started = False
            return 2


    def save_project_as_activated(self):
        """
        save current project asking for a new file name
        """
        logging.debug("function: save_project_as_activated")

        project_new_file_name, filtr = QFileDialog().getSaveFileName(self,
                                                                     "Save project as",
                                                                     os.path.dirname(self.projectFileName),
                                                                     ("Project files (*.boris);;"
                                                                     "Compressed project files (*.boris.gz);;"
                                                                     "All files (*)")
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
                    if dialog.MessageDialog(programName,
                                            f"The file {project_new_file_name} already exists.",
                                            [CANCEL, OVERWRITE]) == CANCEL:
                        return "Not saved"
            # add .boris.gz if filter is .boris.gz
            if filtr == "Compressed project files (*.boris.gz)" and os.path.splitext(project_new_file_name)[1] != ".boris.gz":
                if project_new_file_name.endswith(".boris"):
                    project_new_file_name = os.path.splitext(project_new_file_name)[0]
                project_new_file_name += ".boris.gz"
                # check if file name with extension already exists
                if pathlib.Path(project_new_file_name).is_file():
                    if dialog.MessageDialog(programName,
                                            f"The file {project_new_file_name} already exists.",
                                            [CANCEL, OVERWRITE]) == CANCEL:
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

            self.projectFileName, filtr = QFileDialog().getSaveFileName(self, "Save project", txt,
                                                                        ("Project files (*.boris);;"
                                                                         "Compressed project files (*.boris.gz);;"
                                                                         "All files (*)")
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
                    if dialog.MessageDialog(programName,
                                            f"The file {self.projectFileName} already exists.",
                                            [CANCEL, OVERWRITE]) == CANCEL:
                        self.projectFileName = ""
                        return ""

            # add .boris.gz if filter is .boris.gz
            if filtr == "Compressed project files (*.boris.gz)" and os.path.splitext(self.projectFileName)[1] != ".boris.gz":
                if self.projectFileName.endswith(".boris"):
                    self.projectFileName = os.path.splitext(self.projectFileName)[0]

                self.projectFileName += ".boris.gz"
                # check if file name with extension already exists
                if pathlib.Path(self.projectFileName).is_file():
                    if dialog.MessageDialog(programName,
                                            f"The file {self.projectFileName} already exists.",
                                            [CANCEL, OVERWRITE]) == CANCEL:
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

        self.currentStates = utilities.get_current_states_modifiers_by_subject(utilities.state_behavior_codes(self.pj[ETHOGRAM]),
                                                                               self.pj[OBSERVATIONS][self.observationId][EVENTS],
                                                                               dict(self.pj[SUBJECTS], **{"": {SUBJECT_NAME: ""}}),
                                                                               current_time,
                                                                               include_modifiers=True)

        # show current states
        # index of current subject
        idx = self.subject_name_index[self.currentSubject] if self.currentSubject else ""
        self.lbCurrentStates.setText(", ".join(self.currentStates[idx]))
        self.show_current_states_in_subjects_table()

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
            r, msg = project_functions.check_state_events_obs(obsId, self.pj[ETHOGRAM],
                                                              self.pj[OBSERVATIONS][obsId], self.timeFormat)

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

        parameters = self.choose_obs_subj_behav_category(selected_observations, 0)
        if not parameters[SELECTED_SUBJECTS] or not parameters[SELECTED_BEHAVIORS]:
            return
        export_dir = QFileDialog().getExistingDirectory(self, "Choose a directory to save subtitles", os.path.expanduser("~"),
                                                            options=QFileDialog(self).ShowDirsOnly)
        if not export_dir:
            return
        ok, msg = project_functions.create_subtitles(self.pj, selected_observations, parameters, export_dir)
        if not ok:
            logging.critical(f"Error creating subtitles. {msg}")
            QMessageBox.critical(None, programName, f"Error creating subtitles: {msg}",
                                 QMessageBox.Ok | QMessageBox.Default, QMessageBox.NoButton)


    def export_aggregated_events(self):
        """
        export aggregated events.
        Formats can be SQL (sql), SDIS (sds) or Tabular format (tsv, csv, ods, xlsx, xls, html)
        """

        result, selectedObservations = select_observations.select_observations(self.pj, MULTIPLE,
                                                                               "Select observations for exporting events")
        if not selectedObservations:
            return

        # check if state events are paired
        out, not_paired_obs_list = "", []
        for obsId in selectedObservations:
            r, msg = project_functions.check_state_events_obs(obsId, self.pj[ETHOGRAM],
                                                              self.pj[OBSERVATIONS][obsId], self.timeFormat)
            if not r:
                out += f"Observation: <strong>{obsId}</strong><br>{msg}<br>"
                not_paired_obs_list.append(obsId)
        if out:
            self.results = dialog.ResultsWidget()
            self.results.setWindowTitle(f"{programName} - Check selected observations")
            self.results.ptText.setReadOnly(True)
            self.results.ptText.appendHtml(out)
            self.results.show()
            return

        max_obs_length, selectedObsTotalMediaLength = self.observation_length(selectedObservations)

        logging.debug(f"max_obs_length:{max_obs_length}  selectedObsTotalMediaLength:{selectedObsTotalMediaLength}")

        if max_obs_length == -1:
            return

        parameters = self.choose_obs_subj_behav_category(selectedObservations,
                                                         maxTime=max_obs_length if len(selectedObservations) > 1 else selectedObsTotalMediaLength,
                                                         flagShowIncludeModifiers=False,
                                                         flagShowExcludeBehaviorsWoEvents=False)

        if not parameters[SELECTED_SUBJECTS] or not parameters[SELECTED_BEHAVIORS]:
            return

        # check for grouping results
        flag_group = True
        if len(selectedObservations) > 1:
            flag_group = dialog.MessageDialog(programName, "Group events from selected observations in one file?", [YES, NO]) == YES

        extended_file_formats = ["Tab Separated Values (*.tsv)",
                                 "Comma Separated Values (*.csv)",
                                 "Open Document Spreadsheet ODS (*.ods)",
                                 "Microsoft Excel Spreadsheet XLSX (*.xlsx)",
                                 "Legacy Microsoft Excel Spreadsheet XLS (*.xls)",
                                 "HTML (*.html)",
                                 "SDIS (*.sds)",
                                 "SQL dump file (*.sql)"]

        if flag_group:
            file_formats = ["tsv", "csv", "ods", "xlsx", "xls", "html", "sds", "sql"]  # must be in same order than extended_file_formats

            fileName, filter_ = QFileDialog().getSaveFileName(self, "Export aggregated events", "",
                                                              ";;".join(extended_file_formats))

            if not fileName:
                return

            outputFormat = file_formats[extended_file_formats.index(filter_)]
            if pathlib.Path(fileName).suffix != "." + outputFormat:
                # check if file with new extension already exists
                fileName = str(pathlib.Path(fileName)) + "." + outputFormat
                if pathlib.Path(fileName).is_file():
                        if dialog.MessageDialog(programName,
                                                f"The file {fileName} already exists.",
                                                [CANCEL, OVERWRITE]) == CANCEL:
                            return

        else:  # not grouping

            items = ("Tab Separated Values (*.tsv)",
                     "Comma Separated values (*.csv)",
                     "Open Document Spreadsheet (*.ods)",
                     "Microsoft Excel Spreadsheet XLSX (*.xlsx)",
                     "Legacy Microsoft Excel Spreadsheet XLS (*.xls)",
                     "HTML (*.html)",
                     "SDIS (*.sds)",
                     "Timed Behavioral Sequences (*.tbs)",
                     )
            item, ok = QInputDialog.getItem(self, "Export events format", "Available formats", items, 0, False)
            if not ok:
                return
            outputFormat = re.sub(".* \(\*\.", "", item)[:-1]

            exportDir = QFileDialog().getExistingDirectory(self, "Choose a directory to export events", os.path.expanduser("~"),
                                                           options=QFileDialog.ShowDirsOnly)
            if not exportDir:
                return

        if outputFormat == "sql":
            _, _, conn = db_functions.load_aggregated_events_in_db(self.pj,
                                                                   parameters[SELECTED_SUBJECTS],
                                                                   selectedObservations,
                                                                   parameters[SELECTED_BEHAVIORS])
            try:
                with open(fileName, "w") as f:
                    for line in conn.iterdump():
                        f.write(f"{line}\n")
            except Exception:

                errorMsg = sys.exc_info()[1]
                logging.critical(errorMsg)
                QMessageBox.critical(None, programName, str(errorMsg), QMessageBox.Ok | QMessageBox.Default, QMessageBox.NoButton)
            return

        header = ["Observation id", "Observation date", "Description", "Media file", "Total length", "FPS"]
        if INDEPENDENT_VARIABLES in self.pj:
            for idx in sorted_keys(self.pj[INDEPENDENT_VARIABLES]):
                header.append(self.pj[INDEPENDENT_VARIABLES][idx]["label"])

        header.extend(["Subject", "Behavior", "Behavioral category"])
        header.extend(["Modifiers"])
        header.extend(["Behavior type", "Start (s)", "Stop (s)", "Duration (s)", "Comment start", "Comment stop"])

        data = tablib.Dataset()
        # sort by start time
        start_idx = -5
        stop_idx = -4

        mem_command = ""  # remember user choice when file already exists
        for obsId in selectedObservations:
            d = export_observation.export_aggregated_events(self.pj, parameters, obsId)
            data.extend(d)

            if not flag_group and outputFormat not in ["sds", "tbs"]:
                '''
                fileName = str(pathlib.Path(pathlib.Path(exportDir) / safeFileName(obsId)).with suffix("." + outputFormat))
                '''
                fileName = f"{pathlib.Path(exportDir) / safeFileName(obsId)}.{outputFormat}"
                # check if file with new extension already exists
                if mem_command != OVERWRITE_ALL and pathlib.Path(fileName).is_file():
                    if mem_command == "Skip all":
                        continue
                    mem_command = dialog.MessageDialog(programName,
                                                       f"The file {fileName} already exists.",
                                                       [OVERWRITE, OVERWRITE_ALL, "Skip", "Skip all", CANCEL])
                    if mem_command == CANCEL:
                        return
                    if mem_command in ["Skip" "Skip all"] :
                        continue

                data = tablib.Dataset(*sorted(list(data), key=lambda x: float(x[start_idx])), headers=header)
                data.title = obsId
                r, msg = export_observation.dataset_write(data, fileName, outputFormat)
                if not r:
                    QMessageBox.warning(None, programName, msg, QMessageBox.Ok | QMessageBox.Default, QMessageBox.NoButton)
                data = tablib.Dataset()

        data = tablib.Dataset(*sorted(list(data), key=lambda x: float(x[start_idx])), headers=header)
        data.title = "Aggregated events"

        # TODO: finish
        if outputFormat == "tbs":  # Timed behavioral sequences
            out = ""
            for obsId in selectedObservations:
                # observation id
                out += f"# {obsId}\n"

                for event in list(data):
                    if event[0] == obsId:
                        behavior = event[-8]
                        # replace various char by _
                        for char in [" ", "-", "/"]:
                            behavior = behavior.replace(char, "_")
                        subject = event[-9]
                        # replace various char by _
                        for char in [" ", "-", "/"]:
                            subject = subject.replace(char, "_")
                        event_start = "{0:.3f}".format(float(event[start_idx]))  # start event (from end for independent variables)
                        if not event[stop_idx]:  # stop event (from end)
                            event_stop = "{0:.3f}".format(float(event[start_idx]) + 0.001)
                        else:
                            event_stop = "{0:.3f}".format(float(event[stop_idx]))

                        bs_timed = ([f"{subject}_{behavior}"] *
                                    round((float(event_stop) - float(event_start)) * 100))
                        out += "|".join(bs_timed)

                out += "\n"

                if not flag_group:
                    '''
                    fileName = str(pathlib.Path(pathlib.Path(exportDir) / safeFileName(obsId)).with suffix("." + outputFormat))
                    '''
                    fileName = f"{pathlib.Path(exportDir) / safeFileName(obsId)}.{outputFormat}"
                    with open(fileName, "wb") as f:
                        f.write(str.encode(out))
                    out = ""

            if flag_group:
                with open(fileName, "wb") as f:
                    f.write(str.encode(out))
            return

        if outputFormat == "sds":  # SDIS format
            out = ("% SDIS file created by BORIS (www.boris.unito.it) "
                   "at {}\nTimed <seconds>;\n").format(datetime_iso8601(datetime.datetime.now()))
            for obsId in selectedObservations:
                # observation id
                out += "\n<{}>\n".format(obsId)

                for event in list(data):
                    if event[0] == obsId:
                        behavior = event[-8]
                        # replace various char by _
                        for char in [" ", "-", "/"]:
                            behavior = behavior.replace(char, "_")
                        subject = event[-9]
                        # replace various char by _
                        for char in [" ", "-", "/"]:
                            subject = subject.replace(char, "_")
                        event_start = "{0:.3f}".format(float(event[start_idx]))  # start event (from end for independent variables)
                        if not event[stop_idx]:  # stop event (from end)
                            event_stop = "{0:.3f}".format(float(event[start_idx]) + 0.001)
                        else:
                            event_stop = "{0:.3f}".format(float(event[stop_idx]))
                        out += f"{subject}_{behavior},{event_start}-{event_stop} "

                out += "/\n\n"
                if not flag_group:
                    '''
                    fileName = str(pathlib.Path(pathlib.Path(exportDir) / safeFileName(obsId)).with suffix("." + outputFormat))
                    '''
                    fileName = f"{pathlib.Path(exportDir) / safeFileName(obsId)}.{outputFormat}"
                    with open(fileName, "wb") as f:
                        f.write(str.encode(out))
                    out = ("% SDIS file created by BORIS (www.boris.unito.it) "
                           f"at {datetime_iso8601(datetime.datetime.now())}\nTimed <seconds>;\n")

            if flag_group:
                with open(fileName, "wb") as f:
                    f.write(str.encode(out))
            return

        if flag_group:
            r, msg = export_observation.dataset_write(data, fileName, outputFormat)
            if not r:
                QMessageBox.warning(None, programName, msg, QMessageBox.Ok | QMessageBox.Default, QMessageBox.NoButton)


    def export_state_events_as_textgrid(self):
        """
        export state events as Praat textgrid
        """

        result, selectedObservations = self.selectObservations(MULTIPLE)

        if not selectedObservations:
            return

        plot_parameters = self.choose_obs_subj_behav_category(selectedObservations,
                                                              maxTime=0,
                                                              flagShowIncludeModifiers=False,
                                                              flagShowExcludeBehaviorsWoEvents=False)

        if not plot_parameters[SELECTED_SUBJECTS] or not plot_parameters[SELECTED_BEHAVIORS]:
            return

        # check if state events are paired
        out = ""
        not_paired_obs_list = []
        for obsId in selectedObservations:
            r, msg = project_functions.check_state_events_obs(obsId,
                                                              self.pj[ETHOGRAM],
                                                              self.pj[OBSERVATIONS][obsId],
                                                              self.timeFormat)

            if not r:
                # check if unpaired behavior is included in behaviors to extract
                for behav in plot_parameters[SELECTED_BEHAVIORS]:
                    if f"behavior <b>{behav}</b>" in msg:
                        out += f"Observation: <strong>{obsId}</strong><br>{msg}<br>"
                        not_paired_obs_list.append(obsId)

        if out:
            out = "The observations with UNPAIRED state events will be removed from the analysis<br><br>" + out
            results = dialog.Results_dialog()
            results.setWindowTitle(f"{programName} - Check selected observations and selected behaviors")
            results.ptText.setReadOnly(True)
            results.ptText.appendHtml(out)
            results.pbSave.setVisible(False)
            results.pbCancel.setVisible(True)

            if not results.exec_():
                return

        # remove observations with unpaired state events
        selectedObservations = [x for x in selectedObservations if x not in not_paired_obs_list]
        if not selectedObservations:
            return

        exportDir = QFileDialog(self).getExistingDirectory(self, "Export events as Praat TextGrid", os.path.expanduser('~'),
                                                           options=QFileDialog(self).ShowDirsOnly)
        if not exportDir:
            return

        try:
            mem_command = ""
            for obsId in selectedObservations:

                subjectheader = ('    item [{subjectIdx}]:\n'
                                '        class = "IntervalTier"\n'
                                '        name = "{subject}"\n'
                                '        xmin = {intervalsMin}\n'
                                '        xmax = {intervalsMax}\n'
                                '        intervals: size = {intervalsSize}\n')


                template = ('        intervals [{count}]:\n'
                            '            xmin = {xmin}\n'
                            '            xmax = {xmax}\n'
                            '            text = "{name}"\n')

                flagUnpairedEventFound = False

                totalMediaDuration = round(project_functions.observation_total_length(self.pj[OBSERVATIONS][obsId]), 3)

                cursor = db_functions.load_events_in_db(self.pj,
                                                        plot_parameters[SELECTED_SUBJECTS],
                                                        selectedObservations,
                                                        plot_parameters[SELECTED_BEHAVIORS],
                                                        time_interval=TIME_FULL_OBS)

                cursor.execute(
                    ("SELECT count(distinct subject) FROM events "
                    "WHERE observation = ? AND subject IN ({}) AND type = 'STATE' ".format(",".join(["?"] * len(plot_parameters[SELECTED_SUBJECTS])))
                    ),
                    [obsId] + plot_parameters[SELECTED_SUBJECTS]
                )

                subjectsNum = int(list(cursor.fetchall())[0][0])

                subjectsMin, subjectsMax = 0, totalMediaDuration

                out = ('File type = "ooTextFile"\n'
                    'Object class = "TextGrid"\n'
                    '\n'
                    f'xmin = {subjectsMin}\n'
                    f'xmax = {subjectsMax}\n'
                    'tiers? <exists>\n'
                    f'size = {subjectsNum}\n'
                    'item []:\n')

                subjectIdx = 0
                for subject in plot_parameters[SELECTED_SUBJECTS]:
                    if subject not in [x[EVENT_SUBJECT_FIELD_IDX] for x in self.pj[OBSERVATIONS][obsId][EVENTS]]:
                        continue

                    subjectIdx += 1

                    cursor.execute("SELECT count(*) FROM events WHERE observation = ? AND subject = ? AND type = 'STATE' ", (obsId, subject))
                    intervalsSize = int(list(cursor.fetchall())[0][0] / 2)

                    intervalsMin, intervalsMax = 0, totalMediaDuration

                    out += subjectheader

                    cursor.execute(("SELECT occurence, code FROM events "
                                    "WHERE observation = ? AND subject = ? AND type = 'STATE' order by occurence"), (obsId, subject))

                    rows = [{"occurence": float2decimal(r["occurence"]), "code": r["code"]} for r in cursor.fetchall()]
                    if not rows:
                        continue

                    count = 0

                    # check if 1st behavior starts at the beginning

                    if rows[0]["occurence"] > 0:
                        count += 1
                        out += template.format(count=count, name="null", xmin=0.0, xmax=rows[0]["occurence"])

                    for idx, row in enumerate(rows):
                        if idx % 2 == 0:

                            # check if events not interlacced
                            if row["code"] != rows[idx + 1]["code"]:
                                QMessageBox.critical(None, programName,
                                                    "The events are interlaced. It is not possible to produce the Praat TextGrid file",
                                                    QMessageBox.Ok | QMessageBox.Default, QMessageBox.NoButton)
                                return

                            count += 1
                            out += template.format(count=count, name=row["code"], xmin=row["occurence"], xmax=rows[idx + 1]["occurence"])

                            # check if difference is > 0.001
                            if len(rows) > idx + 2:
                                if rows[idx + 2]["occurence"] - rows[idx + 1]["occurence"] > 0.001:

                                    out += template.format(count=count + 1, name="null",
                                                        xmin=rows[idx + 1]["occurence"], xmax=rows[idx + 2]["occurence"])
                                    count += 1
                                else:
                                    rows[idx + 2]["occurence"] = rows[idx + 1]["occurence"]

                    # check if last event ends at the end of media file
                    if rows[-1]["occurence"] < project_functions.observation_total_length(self.pj[OBSERVATIONS][obsId]):
                        count += 1
                        out += template.format(count=count, name="null", xmin=rows[-1]["occurence"], xmax=totalMediaDuration)

                    # add info
                    out = out.format(
                        subjectIdx=subjectIdx, subject=subject, intervalsSize=count, intervalsMin=intervalsMin, intervalsMax=intervalsMax
                    )

                # check if file already exists
                if mem_command != OVERWRITE_ALL and pathlib.Path(f"{pathlib.Path(exportDir) / safeFileName(obsId)}.textGrid").is_file():
                    if mem_command == "Skip all":
                        continue
                    mem_command = dialog.MessageDialog(programName,
                                                    f"The file <b>{pathlib.Path(exportDir) / safeFileName(obsId)}.textGrid</b> already exists.",
                                                    [OVERWRITE, OVERWRITE_ALL, "Skip", "Skip all", CANCEL])
                    if mem_command == CANCEL:
                        return
                    if mem_command in ["Skip", "Skip all"]:
                        continue

                try:
                    with open(f"{pathlib.Path(exportDir) / safeFileName(obsId)}.textGrid", "w") as f:
                        f.write(out)

                    if flagUnpairedEventFound:
                        QMessageBox.warning(self, programName, "Some state events are not paired. They were excluded from export",
                                            QMessageBox.Ok | QMessageBox.Default, QMessageBox.NoButton)

                except Exception:
                    dialog.error_message("Export textGrid", sys.exc_info())

        except Exception:
            dialog.error_message("Export textGrid", sys.exc_info())


    def media_file_info(self):
        """
        show info about media file (current media file if observation opened)
        """

        if self.observationId and self.playerType == VLC:

            tot_output = ""

            for i, player in enumerate(self.dw_player):
                if not (str(i + 1) in self.pj[OBSERVATIONS][self.observationId][FILE] and
                        self.pj[OBSERVATIONS][self.observationId][FILE][str(i + 1)]):
                    continue

                media = player.mediaplayer.get_media()

                logging.info(f"State: {player.mediaplayer.get_state()}")
                logging.info("Media (get_mrl): {}".format(bytes_to_str(media.get_mrl())))
                logging.info("media.get_meta(0): {}".format(media.get_meta(0)))
                logging.info("Track: {}/{}".format(player.mediaplayer.video_get_track(),
                                                   player.mediaplayer.video_get_track_count()))
                logging.info("number of media in media list: {}".format(player.media_list.count()))
                logging.info("get time: {}  duration: {}".format(player.mediaplayer.get_time(), media.get_duration()))
                logging.info("Position: {} %".format(player.mediaplayer.get_position()))
                logging.info("FPS: {}".format(player.mediaplayer.get_fps()))
                logging.info("Rate: {}".format(player.mediaplayer.get_rate()))
                logging.info("Video size: {}".format(player.mediaplayer.video_get_size(0)))
                logging.info("Scale: {}".format(player.mediaplayer.video_get_scale()))
                logging.info("Aspect ratio: {}".format(player.mediaplayer.video_get_aspect_ratio()))
                logging.info("is seekable? {0}".format(player.mediaplayer.is_seekable()))
                logging.info("has_vout? {0}".format(player.mediaplayer.has_vout()))

                vlc_output = ("<b>VLC analysis</b><br>"
                              "State: {}<br>"
                              "Media Resource Location: {}<br>"
                              "File name: {}<br>"
                              "Track: {}/{}<br>"
                              "Number of media in media list: {}<br>"
                              "get time: {}<br>"
                              "duration: {}<br>"
                              "Position: {} %<br>"
                              "FPS: {}<br>"
                              "Rate: {}<br>"
                              "Video size: {}<br>"
                              "Scale: {}<br>"
                              "Aspect ratio: {}<br>"
                              "is seekable? {}<br>"
                              "has_vout? {}<br>").format(player.mediaplayer.get_state(),
                                                         bytes_to_str(media.get_mrl()),
                                                         media.get_meta(0),
                                                         player.mediaplayer.video_get_track(),
                                                         player.mediaplayer.video_get_track_count(),
                                                         player.media_list.count(),
                                                         player.mediaplayer.get_time(),
                                                         self.convertTime(media.get_duration() / 1000),
                                                         player.mediaplayer.get_position(),
                                                         player.mediaplayer.get_fps(),
                                                         player.mediaplayer.get_rate(),
                                                         player.mediaplayer.video_get_size(0),
                                                         player.mediaplayer.video_get_scale(),
                                                         player.mediaplayer.video_get_aspect_ratio(),
                                                         "Yes" if player.mediaplayer.is_seekable() else "No",
                                                         "Yes" if player.mediaplayer.has_vout() else "No"
                                                         )

                # FFmpeg analysis
                ffmpeg_output = "<br><b>FFmpeg analysis</b><br>"

                for filePath in self.pj[OBSERVATIONS][self.observationId][FILE][str(i + 1)]:
                    media_full_path = project_functions.media_full_path(filePath, self.projectFileName)
                    r = utilities.accurate_media_analysis(self.ffmpeg_bin, media_full_path)
                    nframes = r["frames_number"]
                    if "error" in r:
                        ffmpeg_output += "File path: {filePath}<br><br>{error}<br><br>".format(filePath=media_full_path,
                                                                                               error=r["error"])
                    else:
                        ffmpeg_output += ("File path: {}<br>Duration: {}<br>Bitrate: {}k<br>"
                                          "FPS: {}<br>Has video: {}<br>Has audio: {}<br><br>").format(
                            media_full_path,
                            self.convertTime(r["duration"]), r["bitrate"], r["fps"], r["has_video"], r["has_audio"]
                        )

                    ffmpeg_output += "Total duration: {} (hh:mm:ss.sss)".format(
                        self.convertTime(sum(self.dw_player[i].media_durations) / 1000)
                    )

                tot_output += vlc_output + ffmpeg_output + "<br><hr>"

            self.results = dialog.ResultsWidget()
            self.results.setWindowTitle(programName + " - Media file information")
            self.results.ptText.setReadOnly(True)

            self.results.ptText.appendHtml(tot_output)

            self.results.show()

        else:  # no open observation

            fn = QFileDialog().getOpenFileName(self, "Select a media file", "", "Media files (*)")
            filePath = fn[0] if type(fn) is tuple else fn

            if filePath:
                self.results = dialog.ResultsWidget()
                self.results.setWindowTitle(programName + " - Media file information")
                self.results.ptText.setReadOnly(True)
                self.results.ptText.appendHtml("<br><b>FFmpeg analysis</b><hr>")
                r = utilities.accurate_media_analysis(self.ffmpeg_bin, filePath)
                if "error" in r:
                    self.results.ptText.appendHtml("File path: {filePath}<br><br>{error}<br><br>".format(filePath=filePath,
                                                                                                         error=r["error"]))
                else:
                    self.results.ptText.appendHtml(
                        ("File path: {}<br>Duration: {}<br>Bitrate: {}k<br>"
                         "FPS: {}<br>Has video: {}<br>Has audio: {}<br><br>").format(
                            filePath,
                            self.convertTime(r["duration"]),
                            r["bitrate"],
                            r["fps"],
                            r["has_video"],
                            r["has_audio"])
                    )

                self.results.show()


    def switch_playing_mode(self):
        """
        switch between frame mode (FFMPEG) and VLC mode
        triggered by frame by frame button and toolbox item change
        """

        if self.playerType != VLC:
            return

        if self.playMode == FFMPEG:  # return to VLC mode

            self.playMode = VLC

            globalCurrentTime = int(self.FFmpegGlobalFrame * (1000 / self.fps))

            # set on media player end
            currentMediaTime = int(sum(self.dw_player[0].media_durations))
            for idx, media in enumerate(self.pj[OBSERVATIONS][self.observationId][FILE][PLAYER1]):
                if globalCurrentTime < sum(self.dw_player[0].media_durations[0:idx + 1]):
                    self.dw_player[0].mediaListPlayer.play_item_at_index(idx)
                    while True:
                        if self.dw_player[0].mediaListPlayer.get_state() in [self.vlc_playing, self.vlc_ended]:
                            break
                    self.dw_player[0].mediaListPlayer.pause()
                    currentMediaTime = int(globalCurrentTime - sum(self.dw_player[0].media_durations[0:idx]))
                    break

            self.dw_player[0].mediaplayer.set_time(currentMediaTime)

            self.timer_out()

            for n_player, player in enumerate(self.dw_player):
                if (str(n_player + 1) not in self.pj[OBSERVATIONS][self.observationId][FILE]
                   or not self.pj[OBSERVATIONS][self.observationId][FILE][str(n_player + 1)]):
                    continue
                player.frame_viewer.clear()
                player.stack.setCurrentIndex(0)
                '''
                player.frame_viewer.setVisible(False)
                player.videoframe.setVisible(True)
                player.volume_slider.setVisible(True)
                '''

            self.FFmpegTimer.stop()

            logging.info("ffmpeg timer stopped")

            # stop thread for cleaning temp directory
            if self.config_param.get(SAVE_FRAMES, DISK) == DISK and self.ffmpeg_cache_dir_max_size:
                self.cleaningThread.exiting = True

        # go to frame by frame mode
        elif self.playMode == VLC:

            # FIXME check if FPS are compatible for frame-by-frame mode

            all_fps = []
            for i, player in enumerate(self.dw_player):
                if (str(i + 1) in self.pj[OBSERVATIONS][self.observationId][FILE] and
                        self.pj[OBSERVATIONS][self.observationId][FILE][str(i + 1)]):
                    all_fps.extend(list(player.fps.values()))

            if len(set(all_fps)) != 1:
                logging.warning("The frame-by-frame mode will not be available because the video files have different frame rates")
                QMessageBox.warning(self, programName, ("The frame-by-frame mode will not be available"
                                                        " because the video files have different frame rates ({})."
                                                        ).format(", ".join(map(str, all_fps))),
                                    QMessageBox.Ok | QMessageBox.Default,
                                    QMessageBox.NoButton)
                self.actionFrame_by_frame.setChecked(False)
                return


            self.pause_video()
            self.playMode = FFMPEG

            # make visible frame viewer(s)
            for player in self.dw_player:
                player.stack.setCurrentIndex(1)
                '''
                player.frame_viewer.setVisible(True)
                player.videoframe.setVisible(False)
                player.volume_slider.setVisible(False)
                '''


            # check temp dir for images from ffmpeg
            self.imageDirectory = self.ffmpeg_cache_dir if self.ffmpeg_cache_dir and os.path.isdir(self.ffmpeg_cache_dir) else tempfile.gettempdir()

            globalTime = (sum(
                self.dw_player[0].media_durations[0:self.dw_player[0].media_list.
                                                  index_of_item(self.dw_player[0].
                                                                mediaplayer.get_media())]) +
                          self.dw_player[0].mediaplayer.get_time())

            self.fps = all_fps[0]

            globalCurrentFrame = round(globalTime / (1000 / self.fps))

            self.FFmpegGlobalFrame = globalCurrentFrame

            if self.FFmpegGlobalFrame > 0:
                self.FFmpegGlobalFrame -= 1

            self.ffmpeg_timer_out()

            # set thread for cleaning temp directory
            if self.config_param.get(SAVE_FRAMES, DEFAULT_FRAME_MODE) == DISK and self.ffmpeg_cache_dir_max_size:
                self.cleaningThread.exiting = False
                self.cleaningThread.ffmpeg_cache_dir_max_size = self.ffmpeg_cache_dir_max_size * 1024 * 1024
                self.cleaningThread.tempdir = self.imageDirectory + os.sep
                self.cleaningThread.start()


        # enable/disable speed button
        self.actionNormalSpeed.setEnabled(self.playMode == VLC)
        self.actionFaster.setEnabled(self.playMode == VLC)
        self.actionSlower.setEnabled(self.playMode == VLC)

        logging.info(f"new play mode: {self.playMode}")

        self.menu_options()


    def snapshot(self):
        """
        take snapshot of current video at current position
        snapshot is saved on media path
        """

        if self.pj[OBSERVATIONS][self.observationId][TYPE] in [MEDIA]:

            if self.playerType == VLC:
                if self.playMode == FFMPEG:
                    for n_player, player in enumerate(self.dw_player):
                        if (str(n_player + 1) not in self.pj[OBSERVATIONS][self.observationId][FILE]
                           or not self.pj[OBSERVATIONS][self.observationId][FILE][str(n_player + 1)]):
                            continue

                        for idx, media in enumerate(self.pj[OBSERVATIONS][self.observationId][FILE][str(n_player + 1)]):
                            if self.FFmpegGlobalFrame < sum(player.media_durations[0:idx + 1]):
                                p = pathlib.Path(media)
                                snapshot_file_path = str(p.parent / f"{p.stem}_{self.FFmpegGlobalFrame}.png")
                                player.frame_viewer.pixmap().save(snapshot_file_path)
                                self.statusbar.showMessage(f"Snapshot player #1 saved in {snapshot_file_path}", 0)
                                break

                elif self.playMode == VLC:

                    for i, player in enumerate(self.dw_player):
                        if (str(i + 1) in self.pj[OBSERVATIONS][self.observationId][FILE] and
                                self.pj[OBSERVATIONS][self.observationId][FILE][str(i + 1)]):
                            current_media_path = url2path(player.mediaplayer.get_media().get_mrl())
                            p = pathlib.Path(current_media_path)
                            snapshot_file_path = str(p.parent / f"{p.stem}_{player.mediaplayer.get_time()}.png")
                            player.mediaplayer.video_take_snapshot(0, snapshot_file_path, 0, 0)


    def video_zoom(self, player, zoom_value):
        """
        change video zoom
        """
        try:
            self.dw_player[player - 1].mediaplayer.video_set_scale(zoom_value)
        except Exception:
            logging.warning("Zoom error")

        try:
            zv = self.dw_player[player - 1].mediaplayer.video_get_scale()
            self.actionZoom1_fitwindow.setChecked(zv == 0)
            self.actionZoom1_1_1.setChecked(zv == 1)
            self.actionZoom1_1_2.setChecked(zv == 0.5)
            self.actionZoom1_1_4.setChecked(zv == 0.25)
            self.actionZoom1_2_1.setChecked(zv == 2)

        except Exception:
            pass


    def video_normalspeed_activated(self):
        """
        set playing speed at normal speed (1x)
        """

        if self.playerType == VLC and self.playMode == VLC:
            self.play_rate = 1
            for i, player in enumerate(self.dw_player):
                if (str(i + 1) in self.pj[OBSERVATIONS][self.observationId][FILE] and
                        self.pj[OBSERVATIONS][self.observationId][FILE][str(i + 1)]):
                    player.mediaplayer.set_rate(self.play_rate)
            self.lbSpeed.setText(f"x{self.play_rate:.3f}")

            logging.debug(f"play rate: {self.play_rate:.3f}")


    def video_faster_activated(self):
        """
        increase playing speed by play_rate_step value
        """

        if self.playerType == VLC and self.playMode == VLC:

            if self.play_rate + self.play_rate_step <= 30:
                self.play_rate += self.play_rate_step
                for i, player in enumerate(self.dw_player):
                    if (str(i + 1) in self.pj[OBSERVATIONS][self.observationId][FILE] and
                            self.pj[OBSERVATIONS][self.observationId][FILE][str(i + 1)]):
                        player.mediaplayer.set_rate(self.play_rate)
                self.lbSpeed.setText(f"x{self.play_rate:.3f}")

                logging.debug(f"play rate: {self.play_rate:.3f}")


    def video_slower_activated(self):
        """
        decrease playing speed by play_rate_step value
        """

        if self.playerType == VLC and self.playMode == VLC:

            if self.play_rate - self.play_rate_step >= 0.1:
                self.play_rate -= self.play_rate_step

                for i, player in enumerate(self.dw_player):
                    if (str(i + 1) in self.pj[OBSERVATIONS][self.observationId][FILE] and
                            self.pj[OBSERVATIONS][self.observationId][FILE][str(i + 1)]):
                        player.mediaplayer.set_rate(self.play_rate)

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
                    if self.playMode == FFMPEG:
                        memState = self.FFmpegTimer.isActive()
                        if memState:
                            self.pause_video()
                    elif self.playMode == VLC:
                        memState = self.dw_player[0].mediaListPlayer.get_state()
                        if memState == self.vlc_playing:
                            self.pause_video()

        laps = self.getLaps()

        if not self.pj[ETHOGRAM]:
            QMessageBox.warning(self, programName, "The ethogram is not set!")
            return

        editWindow = DlgEditEvent(logging.getLogger().getEffectiveLevel(),
                                  time_value=0,
                                  current_time=0,
                                  time_format=self.timeFormat,
                                  show_set_current_time=False)
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
                dict(self.pj[SUBJECTS], **{"": {"name": ""}}),  # add no focal subject
                newTime,
                include_modifiers=True
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
                    else:
                        if memState == self.vlc_playing:
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


            durations = []   # in seconds

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

            external_command = external_command_template.format(OBS_ID=self.observationId,
                                                                MEDIA_PATH=f'"{media_path}"',
                                                                MEDIA_BASENAME=f'"{os.path.basename(media_path)}"',
                                                                START_S=eventtime_onmedia_s,
                                                                END_S=eventtime_onmedia_e,
                                                                START_MS=eventtime_onmedia_s * 1000,
                                                                END_MS=eventtime_onmedia_e * 1000,
                                                                DURATION_S=eventtime_onmedia_e - eventtime_onmedia_s,
                                                                DURATION_MS=(eventtime_onmedia_e - eventtime_onmedia_s) * 1000)

            print(external_command)
            '''
            p = subprocess.Popen(external_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
            '''


            '''
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
            '''


            # Extract Information:
            #   videoname of current observation
            #   timeinterval
            #   custom execution


    def edit_event(self):
        """
        edit event corresponding to the selected row in twEvents
        """

        if not self.observationId:
            self.no_observation()
            return

        if not self.twEvents.selectedItems():
            QMessageBox.warning(self, programName, "Select an event to edit")
            return

        try:
            twEvents_row = self.twEvents.selectedItems()[0].row()

            tsb_to_edit = [time2seconds(self.twEvents.item(twEvents_row, EVENT_TIME_FIELD_IDX).text())
                                       if self.timeFormat == HHMMSS else Decimal(self.twEvents.item(twEvents_row, EVENT_TIME_FIELD_IDX).text()),
                            self.twEvents.item(twEvents_row, EVENT_SUBJECT_FIELD_IDX).text(),
                            self.twEvents.item(twEvents_row, EVENT_BEHAVIOR_FIELD_IDX).text()]

            row = [idx for idx, event in enumerate(self.pj[OBSERVATIONS][self.observationId][EVENTS])
                   if [event[EVENT_TIME_FIELD_IDX], event[EVENT_SUBJECT_FIELD_IDX], event[EVENT_BEHAVIOR_FIELD_IDX]] == tsb_to_edit][0]

            editWindow = DlgEditEvent(logging.getLogger().getEffectiveLevel(),
                                      time_value=self.pj[OBSERVATIONS][self.observationId][EVENTS][row][0],
                                      current_time=self.getLaps(),
                                      time_format=self.timeFormat,
                                      show_set_current_time=True)
            editWindow.setWindowTitle("Edit event")

            sortedSubjects = [""] + sorted([self.pj[SUBJECTS][x][SUBJECT_NAME] for x in self.pj[SUBJECTS]])

            editWindow.cobSubject.addItems(sortedSubjects)

            if self.pj[OBSERVATIONS][self.observationId][EVENTS][row][EVENT_SUBJECT_FIELD_IDX] in sortedSubjects:
                editWindow.cobSubject.setCurrentIndex(sortedSubjects.index(self.pj[OBSERVATIONS][self.observationId][EVENTS]
                                                                                  [row][EVENT_SUBJECT_FIELD_IDX]))
            else:
                QMessageBox.warning(self,
                                    programName,
                                    (f"The subject <b>{self.pj[OBSERVATIONS][self.observationId][EVENTS][row][EVENT_SUBJECT_FIELD_IDX]}</b> "
                                     "does not exist more in the subject's list")
                                    )
                editWindow.cobSubject.setCurrentIndex(0)

            sortedCodes = sorted([self.pj[ETHOGRAM][x][BEHAVIOR_CODE] for x in self.pj[ETHOGRAM]])
            editWindow.cobCode.addItems(sortedCodes)

            # check if selected code is in code's list (no modification of codes)
            if self.pj[OBSERVATIONS][self.observationId][EVENTS][row][EVENT_BEHAVIOR_FIELD_IDX] in sortedCodes:
                editWindow.cobCode.setCurrentIndex(
                    sortedCodes.index(self.pj[OBSERVATIONS][self.observationId][EVENTS][row]
                                      [EVENT_BEHAVIOR_FIELD_IDX]))
            else:
                logging.warning((f"The behaviour {self.pj[OBSERVATIONS][self.observationId][EVENTS][row][EVENT_BEHAVIOR_FIELD_IDX]} "
                                "does not exist more in the ethogram"))
                QMessageBox.warning(self,
                                    programName,
                                    (f"The behaviour <b>{self.pj[OBSERVATIONS][self.observationId][EVENTS][row][EVENT_BEHAVIOR_FIELD_IDX]}</b> "
                                     "does not exist more in the ethogram"))
                editWindow.cobCode.setCurrentIndex(0)

            logging.debug(f"original modifiers: {self.pj[OBSERVATIONS][self.observationId][EVENTS][row][EVENT_MODIFIER_FIELD_IDX]}")

            # comment
            editWindow.leComment.setPlainText(self.pj[OBSERVATIONS][self.observationId][EVENTS][row][EVENT_COMMENT_FIELD_IDX])

            if editWindow.exec_():  # button OK

                self.projectChanged = True

                newTime = editWindow.time_widget.get_time()

                for key in self.pj[ETHOGRAM]:
                    if self.pj[ETHOGRAM][key][BEHAVIOR_CODE] == editWindow.cobCode.currentText():
                        event = self.full_event(key)
                        event["subject"] = editWindow.cobSubject.currentText()
                        event["comment"] = editWindow.leComment.toPlainText()
                        event["row"] = row
                        event["original_modifiers"] = self.pj[OBSERVATIONS][self.observationId][EVENTS][row][pj_obs_fields["modifier"]]

                        self.writeEvent(event, newTime)
                        break

        except Exception:
            dialog.error_message("editing the event", sys.exc_info())


    def show_all_events(self):
        """
        show all events
        """
        self.filtered_subjects = []
        self.filtered_behaviors = []
        self.loadEventsInTW(self.observationId)
        self.dwObservations.setWindowTitle(f"Events for “{self.observationId}” observation")


    def filter_events(self):
        """
        filter coded events and subjects
        """
        parameters = self.choose_obs_subj_behav_category([],  # empty selection of observations for selecting all subjects and behaviors
                                                         maxTime=0,
                                                         flagShowIncludeModifiers=False,
                                                         flagShowExcludeBehaviorsWoEvents=False,
                                                         by_category=False,
                                                         show_time=False)

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
                QMessageBox.critical(self, programName, ("The current observation is opened in VIEW mode.\n"
                                                         "It is not allowed to log events in this mode."))
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
                QMessageBox.critical(self,
                                     programName,
                                     f"The code <b>{code}</b> of behavior coding map does not exist in ethogram.")
                return

            event = self.full_event(behavior_idx)
            self.writeEvent(event, self.getLaps())


    def keypress_signal_from_behaviors_coding_map(self, event):
        """
        receive signal from behaviors coding map
        """
        self.keyPressEvent(event)

    '''
    def close_behaviors_coding_map(self, coding_map_name):

        try:

            logging.debug(f"deleting behavior coding map: {coding_map_name} {self.bcm_dict[coding_map_name]}")

            # del self.bcm_dict[coding_map_name]
            self.bcm_dict[coding_map_name].deleteLater()
        except Exception:
            dialog.error_message("deleting behavior coding map", sys.exc_info())
    '''


    def show_behaviors_coding_map(self):
        """
        show a behavior coding map
        """

        if BEHAVIORS_CODING_MAP not in self.pj or not self.pj[BEHAVIORS_CODING_MAP]:
            QMessageBox.warning(self, programName, "No behaviors coding map found in current project")
            return

        items = [x["name"] for x in self.pj[BEHAVIORS_CODING_MAP]]
        if len(items) == 1:
            coding_map_name = items[0]
        else:
            item, ok = QInputDialog.getItem(self, "Select a coding map", "list of coding maps", items, 0, False)
            if ok and item:
                coding_map_name = item
            else:
                return

        if self.bcm_dict.get(coding_map_name, None) is not None:
        #if coding_map_name in self.bcm_dict and :
            self.bcm_dict[coding_map_name].show()
        else:
            self.bcm_dict[coding_map_name] = behaviors_coding_map.BehaviorsCodingMapWindowClass(
                self.pj[BEHAVIORS_CODING_MAP][items.index(coding_map_name)],
                idx=items.index(coding_map_name)
            )

            self.bcm_dict[coding_map_name].clickSignal.connect(self.click_signal_from_behaviors_coding_map)

            # self.bcm_dict[coding_map_name].close_signal.connect(self.close_behaviors_coding_map)

            self.bcm_dict[coding_map_name].resize(CODING_MAP_RESIZE_W, CODING_MAP_RESIZE_W)
            self.bcm_dict[coding_map_name].setWindowFlags(Qt.WindowStaysOnTopHint)
            self.bcm_dict[coding_map_name].show()


    def actionAbout_activated(self):
        """
        About dialog
        """

        programs_versions = ["VLC media player"]
        from boris.vlc import libvlc_get_version, plugin_path
        programs_versions.append(f"version {bytes_to_str(libvlc_get_version())}")

        #if plugin_path:
        programs_versions.append(f"VLC plugin path: {plugin_path}")

        # ffmpeg
        if self.ffmpeg_bin == "ffmpeg" and sys.platform.startswith("linux"):
            ffmpeg_true_path = subprocess.getoutput("which ffmpeg")
        else:
            ffmpeg_true_path = self.ffmpeg_bin
        programs_versions.extend(["\nFFmpeg",
                                  subprocess.getoutput(f'"{self.ffmpeg_bin}" -version').split("\n")[0],
                                  f"Path: {ffmpeg_true_path}",
                                  "https://www.ffmpeg.org"])

        # matplotlib
        programs_versions.extend(["\nMatplotlib", f"version {matplotlib.__version__}", "https://matplotlib.org"])

        # graphviz
        gv_result = subprocess.getoutput("dot -V")
        programs_versions.extend(["\nGraphViz", gv_result if "graphviz" in gv_result else "not installed", "https://www.graphviz.org/"])

        about_dialog = QMessageBox()
        about_dialog.setIconPixmap(QPixmap(":/small_logo"))

        about_dialog.setWindowTitle("About " + programName)
        about_dialog.setStandardButtons(QMessageBox.Ok)
        about_dialog.setDefaultButton(QMessageBox.Ok)
        about_dialog.setEscapeButton(QMessageBox.Ok)

        about_dialog.setInformativeText((
            f"<b>{programName}</b> v. {__version__} - {__version_date__}"
            "<p>Copyright &copy; 2012-2021 Olivier Friard - Marco Gamba<br>"
            "Department of Life Sciences and Systems Biology<br>"
            "University of Torino - Italy<br>"
            "<br>"
            'BORIS is released under the <a href="http://www.gnu.org/copyleft/gpl.html">GNU General Public License</a><br>'
            'See <a href="http://www.boris.unito.it">www.boris.unito.it</a> for more details.<br>'
            "<br>"
            "The authors would like to acknowledge Valentina Matteucci for her precious help."
            "<hr>"
            "How to cite BORIS:<br>"
            "Friard, O. and Gamba, M. (2016), BORIS: a free, versatile open-source event-logging software for video/audio "
            "coding and live observations. Methods Ecol Evol, 7: 1325–1330.<br>"
            '<a href="http://onlinelibrary.wiley.com/doi/10.1111/2041-210X.12584/abstract">DOI:10.1111/2041-210X.12584</a>'
        ))
        n = "\n"
        current_system = platform.uname()
        details = (f"Operating system: {current_system.system} {current_system.release} {current_system.version} \n"
                   f"CPU: {current_system.machine} {current_system.processor}\n\n"
                   f"Python {platform.python_version()} ({'64-bit' if sys.maxsize > 2**32 else '32-bit'})"
                   f" - Qt {QT_VERSION_STR} - PyQt{PYQT_VERSION_STR}\n\n"
                  )

        r, memory = utilities.mem_info()
        if not r:
            details += (f"Memory (RAM)  Total: {memory.get('total_memory', 'Not available'):.2f} Mb  "
                        f"Free: {memory.get('free_memory', 'Not available'):.2f} Mb\n\n")

        details += n.join(programs_versions)
        '''
        memory_in_use = f"{utilities.rss_memory_used(self.pid)} Mb" if utilities.rss_memory_used(self.pid) != -1 else "Not available"
        percent_memory_in_use = (f"({utilities.rss_memory_percent_used(self.pid):.1f} % of total memory)"
                                 if utilities.rss_memory_percent_used(self.pid) != -1
                                 else "")
        '''

        '''
        f"Total memory: {psutil.virtual_memory().total / 1024 / 1024 / 1024:.1f} Gb "
        f"({100 - psutil.virtual_memory().percent :.1f} % available){n}"
        f"Memory in use by BORIS: {memory_in_use} {percent_memory_in_use}{n}{n}"
        '''

        about_dialog.setDetailedText(details)

        _ = about_dialog.exec_()


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

            file_name = w.le_file_path.text()
            overlay_position = w.le_overlay_position.text()

            idx = w.cb_player.currentIndex()

            self.dw_player[idx].mediaplayer.video_set_logo_string(1, str(pathlib.Path(file_name)))

            # overlay position
            if overlay_position:
                try:
                    self.dw_player[idx].mediaplayer.video_set_logo_int(2, int(overlay_position.split(",")[0].strip()))
                    self.dw_player[idx].mediaplayer.video_set_logo_int(3, int(overlay_position.split(",")[1].strip()))
                except Exception:
                    logging.warning(f"error in overlay position")
                    pass

            self.dw_player[idx].mediaplayer.video_set_logo_int(6, w.sb_overlay_transparency.value())

            self.dw_player[idx].mediaplayer.video_set_logo_int(0, 1)

        except Exception:
            logging.critical("error in add_image_overlay function")


    def remove_image_overlay(self):
        """
        remove image overlay from all players
        """
        for i, _ in enumerate(self.dw_player):
            self.dw_player[i].mediaplayer.video_set_logo_int(0, 0)


    def video_slider_sliderMoved(self):
        """
        media position slider moved
        adjust media position
        """

        logging.debug(f"video_slider moved: {self.video_slider.value() / (slider_maximum - 1)}")

        if self.pj[OBSERVATIONS][self.observationId][TYPE] in [MEDIA]:
            if self.playerType == VLC:

                if self.playMode == VLC:
                    sliderPos = self.video_slider.value() / (slider_maximum - 1)
                    videoPosition = sliderPos * self.dw_player[0].mediaplayer.get_length()
                    self.dw_player[0].mediaplayer.set_time(int(videoPosition))
                    self.update_visualizations(scroll_slider=False)

                '''
                if self.playMode == FFMPEG:
                    sliderPos = self.video_slider.value() / (slider_maximum - 1)
                    media_position_s = sliderPos * self.dw_player[0].mediaplayer.get_length() / 1000
                    frame_to_display = round(media_position_s * self.fps)
                    logging.debug(f"video slider moved: Frame to display: {frame_to_display}")
                    self.FFmpegGlobalFrame = frame_to_display - 1
                    self.ffmpeg_timer_out()
                '''


    def video_slider_sliderReleased(self):
        """
        adjust frame when slider is moved by user
        """

        logging.debug(f"video_slider released: {self.video_slider.value() / (slider_maximum - 1)}")

        if self.pj[OBSERVATIONS][self.observationId][TYPE] in [MEDIA]:
            if self.playerType == VLC:

                if self.playMode == FFMPEG:
                    sliderPos = self.video_slider.value() / (slider_maximum - 1)
                    media_position_s = sliderPos * self.dw_player[0].mediaplayer.get_length() / 1000
                    frame_to_display = round(media_position_s * self.fps)
                    logging.debug(f"video slider released: Frame to display: {frame_to_display}")
                    self.FFmpegGlobalFrame = frame_to_display - 1
                    self.ffmpeg_timer_out()


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
                cr_list = [idx for idx, x in enumerate(self.pj[OBSERVATIONS][self.observationId][EVENTS][: -1])
                           if x[0] <= ct and self.pj[OBSERVATIONS][self.observationId][EVENTS][idx + 1][0] > ct]

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
                    self.twSubjects.item(i, len(subjectsFields)).setText(
                        ",".join(self.currentStates[self.subject_name_index[self.twSubjects.item(i, 1).text()]])
                    )
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

        if self.dw_player[n_player].media_list.count() == 1:

                # try:
                if self.pj[OBSERVATIONS][self.observationId][MEDIA_INFO]["offset"][str(n_player + 1)]:

                    if self.pj[OBSERVATIONS][self.observationId][MEDIA_INFO]["offset"][str(n_player + 1)] > 0:

                        if new_time < self.pj[OBSERVATIONS][self.observationId][MEDIA_INFO]["offset"][str(n_player + 1)] * 1000:
                            # hide video if time < offset
                            self.dw_player[n_player].stack.setCurrentIndex(1)
                        else:

                            if (new_time - Decimal(self.pj[OBSERVATIONS][self.observationId][MEDIA_INFO]
                                                   ["offset"][str(n_player + 1)] * 1000) > sum(
                                                       self.dw_player[n_player].media_durations)):
                                # hide video if required time > video time + offset
                                self.dw_player[n_player].stack.setCurrentIndex(1)
                            else:
                                # show video
                                self.dw_player[n_player].stack.setCurrentIndex(0)


                                self.seek_mediaplayer(new_time - Decimal(self.pj[OBSERVATIONS][self.observationId][MEDIA_INFO]
                                                       ["offset"][str(n_player + 1)] * 1000),
                                                       player=n_player)

                    elif self.pj[OBSERVATIONS][self.observationId][MEDIA_INFO]["offset"][str(n_player + 1)] < 0:

                        if (new_time - Decimal(self.pj[OBSERVATIONS][self.observationId][MEDIA_INFO]
                                               ["offset"][str(n_player + 1)] * 1000) > sum(
                                                   self.dw_player[n_player].media_durations)):
                            # hide video if required time > video time + offset
                            self.dw_player[n_player].stack.setCurrentIndex(1)
                        else:
                            self.dw_player[n_player].stack.setCurrentIndex(0)

                            self.seek_mediaplayer(new_time - Decimal(self.pj[OBSERVATIONS][self.observationId][MEDIA_INFO]
                                                   ["offset"][str(n_player + 1)] * 1000),
                                                    player=n_player)

                else:  # no offset
                    self.seek_mediaplayer(new_time, player=n_player)


        elif self.dw_player[n_player].media_list.count() > 1:

            if new_time < sum(self.dw_player[n_player].media_durations):

                media_idx = self.dw_player[n_player].media_list.index_of_item(self.dw_player[n_player].mediaplayer.get_media())

                if sum(self.dw_player[n_player].media_durations[0:media_idx]) < new_time < sum(
                        self.dw_player[n_player].media_durations[0:media_idx + 1]):
                    # correct media

                    logging.debug(f"{n_player + 1} correct media")

                    self.dw_player[n_player].mediaplayer.set_time(new_time - sum(
                        self.dw_player[n_player].media_durations[0: media_idx])
                    )
                else:

                    logging.debug(f"{n_player + 1} not correct media")

                    flagPaused = self.dw_player[n_player].mediaListPlayer.get_state() == self.vlc_paused
                    tot = 0
                    for idx, d in enumerate(self.dw_player[n_player].media_durations):
                        if tot <= new_time < tot + d:
                            self.dw_player[n_player].mediaListPlayer.play_item_at_index(idx)
                            QApplication.processEvents()
                            # wait until media is played
                            while True:
                                if self.dw_player[n_player].mediaListPlayer.get_state() in [self.vlc_playing, self.vlc_ended]:
                                    break

                            if flagPaused:
                                self.dw_player[n_player].mediaListPlayer.pause()

                            self.dw_player[n_player].mediaplayer.set_time(new_time - sum(
                                self.dw_player[n_player].media_durations[0: self.dw_player[n_player].media_list.index_of_item(
                                    self.dw_player[n_player].mediaplayer.get_media()
                                )]))
                            break
                        tot += d

            else:  # end of media list

                logging.debug(f"{n_player + 1} end of media")

                self.dw_player[n_player].mediaListPlayer.play_item_at_index(len(self.dw_player[n_player].media_durations) - 1)
                QApplication.processEvents()
                # wait until media is played
                while True:
                    if self.dw_player[n_player].mediaListPlayer.get_state() in [self.vlc_playing, self.vlc_ended]:
                        break
                self.dw_player[n_player].mediaplayer.set_time(self.dw_player[n_player].media_durations[-1])



    def timer_out(self, scroll_slider=True):
        """
        indicate the video current position and total length for VLC player
        scroll video slider to video position
        Time offset is NOT added!
        triggered by timer
        """

        # logging.debug("function: timer_out")

        if not self.observationId:
            return

        if self.pj[OBSERVATIONS][self.observationId][TYPE] in [MEDIA]:

            # cumulative time
            currentTime = self.getLaps() * 1000

            # observation time interval
            if self.pj[OBSERVATIONS][self.observationId].get(OBSERVATION_TIME_INTERVAL, [0, 0])[1]:
                if currentTime >= self.pj[OBSERVATIONS][self.observationId].get(OBSERVATION_TIME_INTERVAL, [0, 0])[1] * 1000:
                    if self.is_playing():
                        self.pause_video()
                        self.beep("beep")

            if self.beep_every:
                if currentTime % (self.beep_every * 1000) <= 300:
                    self.beep("beep")

            # current media time
            try:
                mediaTime = self.dw_player[0].mediaplayer.get_time()  # time of FIRST media player
                ''' improvement of displayed time
                if self.play_rate == 1:
                    interpolated_media_time = mediaTime
                    time_ms = round(time.time()*1000)

                    if (self.lastPlayTime == interpolated_media_time and self.lastPlayTime != 0):
                        interpolated_media_time += time_ms - self.lastPlayTimeGlobal;
                    else:
                        self.lastPlayTime = interpolated_media_time
                        self.lastPlayTimeGlobal = time_ms
                else:
                    self.lastPlayTime, self.lastPlayTimeGlobal = 0, 0
                '''

            except Exception:
                logging.warning("error on get time in timer_out function")
                return

            # highlight current event in tw events and scroll event list
            self.get_events_current_row()

            '''
            FIXME 2019-11-25
            if self.dw_player[0].mediaplayer.get_state() == self.vlc_ended:
                self.dw_player[0].frame_viewer.setVisible(True)
                self.dw_player[0].videoframe.setVisible(False)
                self.dw_player[0].volume_slider.setVisible(False)
            else:
                self.dw_player[0].frame_viewer.setVisible(False)
                self.dw_player[0].videoframe.setVisible(True)
                self.dw_player[0].volume_slider.setVisible(True)
            '''

            t0 = mediaTime
            ct0 = self.getLaps() * 1000

            if self.dw_player[0].mediaplayer.get_state() != self.vlc_ended:
                # FIXME enumerate(self.dw_player)
                for i in range(1, N_PLAYER):
                    if (str(i + 1) in self.pj[OBSERVATIONS][self.observationId][FILE]
                            and self.pj[OBSERVATIONS][self.observationId][FILE][str(i + 1)]):
                        t = self.dw_player[i].mediaplayer.get_time()
                        ct = self.getLaps(n_player=i) * 1000

                        if abs(ct0 -
                               (ct + Decimal(self.pj[OBSERVATIONS][self.observationId][MEDIA_INFO]
                                             ["offset"][str(i + 1)]) * 1000)) >= 300:

                            self.sync_time(i, ct0)
                            #self.seek_mediaplayer(ct0, player=i)

            currentTimeOffset = Decimal(currentTime / 1000 + self.pj[OBSERVATIONS][self.observationId][TIME_OFFSET])

            totalGlobalTime = sum(self.dw_player[0].media_durations)

            mediaName = ""

            mediaplayer_length = self.dw_player[0].mediaplayer.get_length()
            if mediaplayer_length:

                self.mediaTotalLength = mediaplayer_length / 1000

                # current state(s)
                # extract State events
                StateBehaviorsCodes = utilities.state_behavior_codes(self.pj[ETHOGRAM])

                self.currentStates = {}

                # index of current subject
                subject_idx = self.subject_name_index[self.currentSubject] if self.currentSubject else ""

                self.currentStates = utilities.get_current_states_modifiers_by_subject(StateBehaviorsCodes,
                                                                             self.pj[OBSERVATIONS][self.observationId][EVENTS],
                                                                             dict(self.pj[SUBJECTS], **{"": {"name": ""}}),
                                                                             currentTimeOffset,
                                                                             include_modifiers=True)

                self.lbCurrentStates.setText(", ".join(self.currentStates[subject_idx]))

                # show current states in subjects table
                self.show_current_states_in_subjects_table()

                mediaName = self.dw_player[0].mediaplayer.get_media().get_meta(0)

                # update media info
                msg = ""
                media_list_player_state = self.dw_player[0].mediaListPlayer.get_state()
                if media_list_player_state in [self.vlc_playing, self.vlc_paused]:

                    msg = (f"{mediaName}: <b>{self.convertTime(mediaTime / 1000)} / "
                           f"{self.convertTime(self.mediaTotalLength)}</b>")

                    '''
                    if self.play_rate != 1:
                        msg = (f"{mediaName}: <b>{self.convertTime(mediaTime / 1000)} / "
                               f"{self.convertTime(self.mediaTotalLength)}</b>")
                    else:

                        msg = (f"{mediaName}: <b>{self.convertTime(interpolated_media_time / 1000)} / "
                               f"{self.convertTime(self.mediaTotalLength)}</b>")
                    '''

                    if self.dw_player[0].media_list.count() > 1:
                        msg += (f" | total: <b>{self.convertTime(currentTime / 1000)} / "
                                f"{self.convertTime(totalGlobalTime / 1000)}</b>")

                    if media_list_player_state == self.vlc_paused:
                        msg += " (paused)"

                else:  # player ended
                    self.timer.stop()
                    self.timer_sound_signal.stop()
                    #self.dw_player[0].mediaplayer.stop()

                    # stop all timer for plotting data
                    for data_timer in self.ext_data_timer_list:
                        data_timer.stop()

                    self.actionPlay.setIcon(QIcon(":/play"))


                if msg:
                    # show time
                    self.lb_current_media_time.setText(msg)

                    # set video scroll bar
                    if scroll_slider:
                        self.video_slider.setValue(mediaTime / mediaplayer_length * (slider_maximum - 1))

            else:
                self.statusbar.showMessage("Media length not available now", 0)

            ''' # stop behaviors between media files
            # DISABLED because it is not working well
            if ((self.memMedia and mediaName != self.memMedia)
                    or (self.dw_player[0].mediaListPlayer.get_state() == self.vlc_ended and self.timer.isActive())):

                if (CLOSE_BEHAVIORS_BETWEEN_VIDEOS in self.pj[OBSERVATIONS][self.observationId]
                        and self.pj[OBSERVATIONS][self.observationId][CLOSE_BEHAVIORS_BETWEEN_VIDEOS]):

                    logging.debug("video changed")
                    logging.debug("current states: {}".format(self.currentStates))

                    for subjIdx in self.currentStates:
                        if subjIdx:
                            subjName = self.pj[SUBJECTS][subjIdx]["name"]
                        else:
                            subjName = ""
                        for behav in self.currentStates[subjIdx]:
                            cm = ""
                            for ev in self.pj[OBSERVATIONS][self.observationId][EVENTS]:
                                if ev[EVENT_TIME_FIELD_IDX] > currentTime / 1000:  # time
                                    break
                                if ev[EVENT_SUBJECT_FIELD_IDX] == subjName:  # current subject name
                                    if ev[EVENT_BEHAVIOR_FIELD_IDX] == behav:   # code
                                        cm = ev[EVENT_MODIFIER_FIELD_IDX]

                            end_time = currentTime / 1000 - Decimal("0.001")

                            self.pj[OBSERVATIONS][self.observationId][EVENTS].append([end_time, subjName, behav, cm, ""])
                            self.loadEventsInTW(self.observationId)
                            item = self.twEvents.item([i for i, t in enumerate(self.pj[OBSERVATIONS][self.observationId][EVENTS])
                                                       if t[0] == end_time][0], 0)
                            self.twEvents.scrollToItem(item)
                            self.projectChanged = True

            self.memMedia = mediaName
            '''



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
                        self.twEthogram.setItem(self.twEthogram.rowCount() - 1, col, QTableWidgetItem(str(self.pj[ETHOGRAM][idx][field])))
        if self.twEthogram.rowCount() < len(self.pj[ETHOGRAM].keys()):
            self.dwEthogram.setWindowTitle(f"Ethogram (filtered {self.twEthogram.rowCount()}/{len(self.pj[ETHOGRAM].keys())})")

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

        self.subject_name_index = {}    # dict([(self.pj[SUBJECTS][x]["name"], x) for x in self.pj[SUBJECTS]])

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
                        self.twSubjects.setItem(self.twSubjects.rowCount() - 1, idx2, QTableWidgetItem(self.pj[SUBJECTS][idx][field]))

                    # add cell for current state(s) after last subject field
                    self.twSubjects.setItem(self.twSubjects.rowCount() - 1, len(subjectsFields), QTableWidgetItem(""))


    def update_events_start_stop(self):
        """
        update status start/stop of events in Events table
        take consideration of subject and modifiers

        does not return value
        """

        try:
            stateEventsList = [self.pj[ETHOGRAM][x][BEHAVIOR_CODE] for x in self.pj[ETHOGRAM] if STATE in self.pj[ETHOGRAM][x][TYPE].upper()]

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
                        if event[EVENT_BEHAVIOR_FIELD_IDX] == code
                        and event[EVENT_TIME_FIELD_IDX] < time and event[EVENT_SUBJECT_FIELD_IDX] ==
                        subject and event[EVENT_MODIFIER_FIELD_IDX] == modifier
                    ])

                    if nbEvents and (nbEvents % 2):  # test >0 and  odd
                        self.twEvents.item(row, tw_obs_fields[TYPE]).setText(STOP)
                    else:
                        self.twEvents.item(row, tw_obs_fields[TYPE]).setText(START)
        except Exception:
            dialog.error_message("update_events_start_stop", sys.exc_info())


    def checkSameEvent(self, obsId: str, time: Decimal, subject: str, code: str):
        """
        check if a same event is already in events list (time, subject, code)
        """

        return [time, subject, code] in [[x[EVENT_TIME_FIELD_IDX], x[EVENT_SUBJECT_FIELD_IDX], x[EVENT_BEHAVIOR_FIELD_IDX]]
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

            if ("row" not in event) and self.checkSameEvent(self.observationId,
                                                            memTime,
                                                            event["subject"] if "subject" in event else self.currentSubject,
                                                            event["code"]):
                _ = dialog.MessageDialog(programName, "The same event already exists (same time, behavior code and subject).", [OK])
                return

            if "from map" not in event:   # modifiers only for behaviors without coding map
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
                                if self.playMode == FFMPEG:
                                    memState = self.FFmpegTimer.isActive()
                                    if memState:
                                        self.pause_video()
                                elif self.playMode == VLC:
                                    memState = self.dw_player[0].mediaListPlayer.get_state()
                                    if memState == self.vlc_playing:
                                        self.pause_video()

                        # check if editing (original_modifiers key)
                        currentModifiers = event.get("original_modifiers", "")

                        modifiers_selector = select_modifiers.ModifiersList(event["code"], eval(str(event["modifiers"])), currentModifiers)

                        r = modifiers_selector.exec_()
                        if r:
                            selected_modifiers = modifiers_selector.get_modifiers()

                        # restart media
                        if self.pj[OBSERVATIONS][self.observationId][TYPE] in [MEDIA]:
                            if self.playerType == VLC:
                                if self.playMode == FFMPEG:
                                    if memState:
                                        self.play_video()
                                else:
                                    if memState == self.vlc_playing:
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

            current_states = utilities.get_current_states_modifiers_by_subject(StateBehaviorsCodes,
                                                                         self.pj[OBSERVATIONS][self.observationId][EVENTS],
                                                                         dict(self.pj[SUBJECTS], **{"": {"name": ""}}),
                                                                         memTime,
                                                                         include_modifiers=False)

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
                    if (self.close_the_same_current_event and
                            (event["code"] == cs) and modifier_str.replace("None", "").replace("|", "") == ""):
                        modifier_str = cm[cs]
                        continue

                    if (event["excluded"] and cs in event["excluded"].split(",")) or (event["code"] == cs and cm[cs] != modifier_str):
                        # add excluded state event to observations (= STOP them)
                        self.pj[OBSERVATIONS][self.observationId][EVENTS].append(
                            [memTime - Decimal("0.001"), self.currentSubject, cs, cm[cs], ""]
                        )

            # remove key code from modifiers
            modifier_str = re.sub(" \(.*\)", "", modifier_str)
            comment = event.get("comment", "")
            subject = event.get("subject", self.currentSubject)

            # add event to pj
            if "row" in event:
                # modifying event
                self.pj[OBSERVATIONS][self.observationId][EVENTS][event["row"]] = [memTime, subject, event["code"], modifier_str, comment]
            else:
                # add event
                self.pj[OBSERVATIONS][self.observationId][EVENTS].append([memTime, subject, event["code"], modifier_str, comment])

            # sort events in pj
            self.pj[OBSERVATIONS][self.observationId][EVENTS].sort()

            # reload all events in tw
            self.loadEventsInTW(self.observationId)

            position_in_events = [i for i, t in enumerate(self.pj[OBSERVATIONS][self.observationId][EVENTS]) if t[0] == memTime][0]

            if position_in_events == len(self.pj[OBSERVATIONS][self.observationId][EVENTS]) - 1:
                self.twEvents.scrollToBottom()
            else:
                self.twEvents.scrollToItem(self.twEvents.item(position_in_events, 0), QAbstractItemView.EnsureVisible)

            self.projectChanged = True
        except Exception:
            dialog.error_message("Event can not be recorded", sys.exc_info())


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

        dbc = dialog.DuplicateBehaviorCode(f"The <b>{obs_key}</b> key codes more behaviors.<br>Choose the correct one:", items)
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
                return Decimal(0)

            if self.playerType == VLC:
                if self.playMode == FFMPEG:
                    # cumulative time
                    memLaps = Decimal(self.FFmpegGlobalFrame * (1000 / self.fps) / 1000).quantize(Decimal(".001"))
                    return memLaps
                elif self.playMode == VLC:
                    # cumulative time
                    memLaps = Decimal(
                        str(
                            round((sum(self.dw_player[n_player].media_durations[
                                0:self.dw_player[n_player].media_list.
                                index_of_item(self.dw_player[n_player].mediaplayer.get_media())]) +
                                self.dw_player[n_player].mediaplayer.get_time()) / 1000, 3)))



                    return memLaps


    def full_event(self, behavior_idx):
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


    def frame_backward(self):
        """
        go to previous frame (frame backward)
        """

        if self.playMode == FFMPEG:

            logging.debug(f"current frame {self.FFmpegGlobalFrame}")

            if self.FFmpegGlobalFrame > 1:
                self.FFmpegGlobalFrame -= 2
                self.ffmpeg_timer_out()
                logging.debug(f"new frame {self.FFmpegGlobalFrame}")


    def frame_forward(self):
        """
        go one frame forward
        """
        if self.playMode == FFMPEG:
            self.ffmpeg_timer_out()


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
            if self.playMode == VLC:
                return self.dw_player[0].mediaplayer.get_state() == self.vlc_playing
            if self.playMode == FFMPEG:
                return self.FFmpegTimer.isActive()
            # FIXME exit without return value
        else:
            return False


    def keyPressEvent(self, event):

        logging.debug(f"text #{event.text()}#  event key: {event.key()} ")

        '''
        if (event.modifiers() & Qt.ShiftModifier):   # SHIFT

        QApplication.keyboardModifiers()

        http://qt-project.org/doc/qt-5.0/qtcore/qt.html#Key-enum
        https://github.com/pyqt/python-qt5/blob/master/PyQt5/qml/builtins.qmltypes

        ESC: 16777216
        '''

        if self.playerType == VIEWER:
            if event.key() in [Qt.Key_Shift, Qt.Key_Control, Qt.Key_Alt, Qt.Key_CapsLock, Qt.Key_AltGr]:
                return
            QMessageBox.critical(self, programName, ("The current observation is opened in VIEW mode.\n"
                                                     "It is not allowed to log events in this mode."))
            return

        if self.playMode == VLC:
            self.timer_out()

        if not self.observationId:
            return

        # beep
        if self.confirmSound:
            self.beep("key_sound")

        flagPlayerPlaying = self.is_playing()

        # check if media ever played

        if self.playerType == VLC:
            if self.dw_player[0].mediaListPlayer.get_state() == self.vlc_NothingSpecial:
                return

        ek, ek_text = event.key(), event.text()

        if ek in [Qt.Key_Tab, Qt.Key_Shift, Qt.Key_Control, Qt.Key_Meta, Qt.Key_Alt, Qt.Key_AltGr]:
            return

        if ek == Qt.Key_Escape:
            self.switch_playing_mode()
            return

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
        if self.playMode == FFMPEG:
            if ek == 47 or ek == Qt.Key_Left:  # / one frame back

                logging.debug(f"Current frame {self.FFmpegGlobalFrame}")

                if self.FFmpegGlobalFrame > 1:
                    self.FFmpegGlobalFrame -= 2
                    newTime = 1000 * self.FFmpegGlobalFrame / self.fps
                    self.ffmpeg_timer_out()

                    logging.debug(f"New frame {self.FFmpegGlobalFrame}")

                return

            if ek == 42 or ek == Qt.Key_Right:  # *  read next frame

                logging.debug(f"(next) current frame {self.FFmpegGlobalFrame}")

                self.ffmpeg_timer_out()

                logging.debug(f"(next) new frame {self.FFmpegGlobalFrame}")

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
        if (ek in function_keys):
            if function_keys[ek] in [self.pj[ETHOGRAM][x]["key"] for x in self.pj[ETHOGRAM]]:
                obs_key = function_keys[ek]

        # get time
        if self.pj[OBSERVATIONS][self.observationId][TYPE] == LIVE:
            if self.pj[OBSERVATIONS][self.observationId].get(SCAN_SAMPLING_TIME, 0):
                if self.timeFormat == HHMMSS:
                    memLaps = Decimal(int(time2seconds(self.lb_current_media_time.text())))
                if self.timeFormat == S:
                    memLaps = Decimal(int(Decimal(self.lb_current_media_time.text())))
            else: # no scan sampling
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

        if (((ek in range(33, 256)) and (ek not in [Qt.Key_Plus, Qt.Key_Minus])) or
           (ek in function_keys) or
           (ek == Qt.Key_Enter and event.text())):  # click from coding pad or subjects pad

            ethogram_idx, subj_idx, count = -1, -1, 0

            if (ek in function_keys):
                ek_unichr = function_keys[ek]
            elif ek != Qt.Key_Enter:
                ek_unichr = ek_text
            elif (ek == Qt.Key_Enter and event.text()):  # click from coding pad or subjects pad
                ek_unichr = ek_text

            logging.debug(f"ek_unichr {ek_unichr}")

            if ek == Qt.Key_Enter and event.text():  # click from coding pad or subjects pad
                ek_unichr = ""

                if "#subject#" in event.text():
                    for idx in self.pj[SUBJECTS]:
                        if self.pj[SUBJECTS][idx][SUBJECT_NAME] == event.text().replace("#subject#", ""):
                            subj_idx = idx
                            '''
                            if self.currentSubject == self.pj[SUBJECTS][subj_idx]["name"]:
                                self.update_subject("")
                            else:
                                self.update_subject(self.pj[SUBJECTS][subj_idx]["name"])
                            '''
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

                r = dialog.MessageDialog(programName, "This key defines a behavior and a subject. Choose one", ["&Behavior", "&Subject"])
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

                    response = dialog.MessageDialog(programName, ("The focal subject is not defined. Do you want to continue?\n"
                                                                  "Use Preferences menu option to modify this behaviour."), [YES, NO])

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
                            '''
                            if self.currentSubject == self.pj[SUBJECTS][idx]["name"]:
                                self.update_subject("")
                            else:
                                self.update_subject(self.pj[SUBJECTS][idx]["name"])
                            '''
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
                newTime = (time_ + self.repositioningTimeOffset) * 1000
            else:
                newTime = 0

            if self.playMode == VLC:

                self.seek_mediaplayer(newTime)

                '''
                flag_paused = (self.dw_player[0].mediaListPlayer.get_state() in [self.vlc_paused, self.vlc_ended])
                if len(self.dw_player[0].media_durations) == 1:

                    if (self.dw_player[0].mediaListPlayer.get_state() == self.vlc_ended and
                       time_ < self.dw_player[0].mediaplayer.get_media().get_duration() / 1000):

                        self.dw_player[0].mediaListPlayer.play()
                        while True:
                            if self.dw_player[0].mediaListPlayer.get_state() in [self.vlc_playing, self.vlc_ended]:
                                break

                        if flag_paused:
                            self.dw_player[0].mediaListPlayer.pause()
                            while True:
                                if self.dw_player[0].mediaListPlayer.get_state() in [self.vlc_paused, self.vlc_ended]:
                                    break

                    if time_ < self.dw_player[0].mediaplayer.get_media().get_duration() / 1000:
                        self.dw_player[0].mediaplayer.set_time(int(newTime))
                    else:
                        self.dw_player[0].mediaplayer.set_time(self.dw_player[0].mediaplayer.get_media().get_duration() - 100)

                else:  # more media in player 1

                    tot = 0
                    for idx, d in enumerate(self.dw_player[0].media_durations):
                        if newTime >= tot and newTime < tot + d:
                            self.dw_player[0].mediaListPlayer.play_item_at_index(idx)

                            # wait until media is played
                            while True:
                                if self.dw_player[0].mediaListPlayer.get_state() in [self.vlc_playing, self.vlc_ended]:
                                    break

                            if flag_paused:
                                self.dw_player[0].mediaListPlayer.pause()

                            self.dw_player[0].mediaplayer.set_time(newTime - sum(
                                self.dw_player[0].media_durations[0:self.dw_player[0].media_list.
                                                                  index_of_item(self.dw_player[0].
                                                                                mediaplayer.get_media())]))
                            break

                        tot += d

                '''
                self.update_visualizations()


            if self.playMode == FFMPEG:
                frameDuration = Decimal(1000 / self.fps)
                currentFrame = round(newTime / frameDuration)
                self.FFmpegGlobalFrame = currentFrame
                if self.FFmpegGlobalFrame > 0:
                    self.FFmpegGlobalFrame -= 1
                self.ffmpeg_timer_out()


    def twSubjects_doubleClicked(self):
        """
        select subject by double-click on the subjects table
        """

        if self.observationId:
            if self.twSubjects.selectedIndexes():
                self.update_subject(self.twSubjects.item(self.twSubjects.selectedIndexes()[0].row(), 1).text())
        else:
            self.no_observation()


    def select_events_between_activated(self):
        """
        select events between a time interval
        """

        def parseTime(txt):
            """
            parse time in string (should be 00:00:00.000 or in seconds)
            """
            if ':' in txt:
                qtime = QTime.fromString(txt, "hh:mm:ss.zzz")

                if qtime.toString():
                    timeSeconds = time2seconds(qtime.toString("hh:mm:ss.zzz"))
                else:
                    return None
            else:
                try:
                    timeSeconds = Decimal(txt)
                except InvalidOperation:
                    return None
            return timeSeconds

        if self.twEvents.rowCount():
            text, ok = QInputDialog.getText(self, "Select events in time interval",
                                            "Interval: (example: 12.5-14.7 or 02:45.780-03:15.120)",
                                            QLineEdit.Normal, "")

            if ok and text != '':

                if "-" not in text:
                    QMessageBox.critical(self, programName, "Use minus sign (-) to separate initial value from final value")
                    return

                while " " in text:
                    text = text.replace(" ", "")

                from_, to_ = text.split("-")[0:2]
                from_sec = parseTime(from_)
                if not from_sec:
                    QMessageBox.critical(self, programName, f"Time value not recognized: {from_}")
                    return
                to_sec = parseTime(to_)
                if not to_sec:
                    QMessageBox.critical(self, programName, f"Time value not recognized: {to_}")
                    return
                if to_sec < from_sec:
                    QMessageBox.critical(self, programName, "The initial time is greater than the final time")
                    return
                self.twEvents.clearSelection()
                self.twEvents.setSelectionMode(QAbstractItemView.MultiSelection)
                for r in range(0, self.twEvents.rowCount()):
                    if ':' in self.twEvents.item(r, 0).text():
                        time = time2seconds(self.twEvents.item(r, 0).text())
                    else:
                        time = Decimal(self.twEvents.item(r, 0).text())
                    if from_sec <= time <= to_sec:
                        self.twEvents.selectRow(r)

        else:
            QMessageBox.warning(self, programName, "There are no events to select")


    def delete_all_events(self):
        """
        delete all (filtered) events in current observation
        """

        if not self.observationId:
            self.no_observation()
            return

        if not self.twEvents.rowCount():
            QMessageBox.warning(self, programName, "No events to delete")
            return

        if dialog.MessageDialog(programName,
                                ("Confirm the deletion of all (filtered) events in the current observation?<br>"
                                 "Filters do not apply!"),
                                [YES, NO]) == YES:
            rows_to_delete = []
            for row in range(self.twEvents.rowCount()):
                rows_to_delete.append([time2seconds(self.twEvents.item(row, EVENT_TIME_FIELD_IDX).text())
                                       if self.timeFormat == HHMMSS else Decimal(self.twEvents.item(row, EVENT_TIME_FIELD_IDX).text()),
                                       self.twEvents.item(row, EVENT_SUBJECT_FIELD_IDX).text(),
                                       self.twEvents.item(row, EVENT_BEHAVIOR_FIELD_IDX).text()])

            self.pj[OBSERVATIONS][self.observationId][EVENTS] = [
                    event for idx, event in enumerate(self.pj[OBSERVATIONS][self.observationId][EVENTS])
                    if [event[EVENT_TIME_FIELD_IDX], event[EVENT_SUBJECT_FIELD_IDX], event[EVENT_BEHAVIOR_FIELD_IDX]] not in rows_to_delete
                ]

            self.projectChanged = True
            self.loadEventsInTW(self.observationId)


    def delete_selected_events(self):
        """
        delete selected events
        """

        if not self.observationId:
            self.no_observation()
            return
        if not self.twEvents.selectedIndexes():
            QMessageBox.warning(self, programName, "No event selected!")
        else:
            # list of rows to delete (set for unique)
            try:
                rows_to_delete = []
                for row in set([item.row() for item in self.twEvents.selectedIndexes()]):
                    rows_to_delete.append([time2seconds(self.twEvents.item(row, EVENT_TIME_FIELD_IDX).text())
                                           if self.timeFormat == HHMMSS else Decimal(self.twEvents.item(row, EVENT_TIME_FIELD_IDX).text()),
                                           self.twEvents.item(row, EVENT_SUBJECT_FIELD_IDX).text(),
                                           self.twEvents.item(row, EVENT_BEHAVIOR_FIELD_IDX).text()])

                self.pj[OBSERVATIONS][self.observationId][EVENTS] = [
                    event for idx, event in enumerate(self.pj[OBSERVATIONS][self.observationId][EVENTS])
                    if [event[EVENT_TIME_FIELD_IDX], event[EVENT_SUBJECT_FIELD_IDX], event[EVENT_BEHAVIOR_FIELD_IDX]] not in rows_to_delete
                ]

                self.projectChanged = True
                self.loadEventsInTW(self.observationId)
            except Exception:
                QMessageBox.critical(self, programName, "Problem during event deletion!")


    def edit_selected_events(self):
        """
        edit one or more selected events for subject, behavior and/or comment
        """
        # list of rows to edit
        twEvents_rows_to_edit = set([item.row() for item in self.twEvents.selectedIndexes()])

        if not len(twEvents_rows_to_edit):
            QMessageBox.warning(self, programName, "No event selected!")
        elif len(twEvents_rows_to_edit) == 1:  # 1 event selected
            self.edit_event()
        else:  # editing of more events
            dialogWindow = EditSelectedEvents()
            dialogWindow.all_behaviors = sorted([self.pj[ETHOGRAM][x][BEHAVIOR_CODE] for x in self.pj[ETHOGRAM]])

            dialogWindow.all_subjects = [self.pj[SUBJECTS][str(k)][SUBJECT_NAME]
                                         for k in sorted([int(x) for x in self.pj[SUBJECTS].keys()])]

            if dialogWindow.exec_():

                tsb_to_edit = []
                for row in twEvents_rows_to_edit:
                    tsb_to_edit.append([time2seconds(self.twEvents.item(row, EVENT_TIME_FIELD_IDX).text())
                                           if self.timeFormat == HHMMSS else Decimal(self.twEvents.item(row, EVENT_TIME_FIELD_IDX).text()),
                                           self.twEvents.item(row, EVENT_SUBJECT_FIELD_IDX).text(),
                                           self.twEvents.item(row, EVENT_BEHAVIOR_FIELD_IDX).text()])

                for idx, event in enumerate(self.pj[OBSERVATIONS][self.observationId][EVENTS]):
                    if [event[EVENT_TIME_FIELD_IDX], event[EVENT_SUBJECT_FIELD_IDX], event[EVENT_BEHAVIOR_FIELD_IDX]] in tsb_to_edit:
                        if dialogWindow.rbSubject.isChecked():
                            event[EVENT_SUBJECT_FIELD_IDX] = dialogWindow.newText.selectedItems()[0].text()
                        if dialogWindow.rbBehavior.isChecked():
                            event[EVENT_BEHAVIOR_FIELD_IDX] = dialogWindow.newText.selectedItems()[0].text()
                        if dialogWindow.rbComment.isChecked():
                            event[EVENT_COMMENT_FIELD_IDX] = dialogWindow.commentText.text()

                        self.pj[OBSERVATIONS][self.observationId][EVENTS][idx] = event
                        self.projectChanged = True
                self.loadEventsInTW(self.observationId)


    def edit_time_selected_events(self):
        """
        edit time of one or more selected events
        """
        # list of rows to edit
        twEvents_rows_to_shift = set([item.row() for item in self.twEvents.selectedIndexes()])

        if not len(twEvents_rows_to_shift):
            QMessageBox.warning(self, programName, "No event selected!")
            return

        d, ok = QInputDialog.getDouble(self, "Time value", "Value to add or subtract (use negative value):", 0, -86400, 86400, 3)
        if ok and d:
            if dialog.MessageDialog(programName,
                                    (f"Confirm the {'addition' if d > 0 else 'subtraction'} of {abs(d)} seconds "
                                     "to all selected events in the current observation?"),
                                    [YES, NO]) == NO:
                return

            tsb_to_shift = []
            for row in twEvents_rows_to_shift:
                tsb_to_shift.append([time2seconds(self.twEvents.item(row, EVENT_TIME_FIELD_IDX).text())
                                     if self.timeFormat == HHMMSS else Decimal(self.twEvents.item(row, EVENT_TIME_FIELD_IDX).text()),
                                     self.twEvents.item(row, EVENT_SUBJECT_FIELD_IDX).text(),
                                     self.twEvents.item(row, EVENT_BEHAVIOR_FIELD_IDX).text()])

            for idx, event in enumerate(self.pj[OBSERVATIONS][self.observationId][EVENTS]):
                '''if idx in rows_to_edit:'''
                if [event[EVENT_TIME_FIELD_IDX], event[EVENT_SUBJECT_FIELD_IDX], event[EVENT_BEHAVIOR_FIELD_IDX]] in tsb_to_shift:
                    self.pj[OBSERVATIONS][self.observationId][EVENTS][idx][EVENT_TIME_FIELD_IDX] += Decimal(f"{d:.3f}")
                    self.projectChanged = True

            self.pj[OBSERVATIONS][self.observationId][EVENTS] = sorted(self.pj[OBSERVATIONS][self.observationId][EVENTS])
            self.loadEventsInTW(self.observationId)


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
            tsb_to_copy.append([time2seconds(self.twEvents.item(row, EVENT_TIME_FIELD_IDX).text())
                                 if self.timeFormat == HHMMSS else Decimal(self.twEvents.item(row, EVENT_TIME_FIELD_IDX).text()),
                                 self.twEvents.item(row, EVENT_SUBJECT_FIELD_IDX).text(),
                                 self.twEvents.item(row, EVENT_BEHAVIOR_FIELD_IDX).text()])

        copied_events = []
        for idx, event in enumerate(self.pj[OBSERVATIONS][self.observationId][EVENTS]):
            if [event[EVENT_TIME_FIELD_IDX], event[EVENT_SUBJECT_FIELD_IDX], event[EVENT_BEHAVIOR_FIELD_IDX]] in tsb_to_copy:
                copied_events.append("\t".join([str(x) for x in self.pj[OBSERVATIONS][self.observationId][EVENTS][idx]]))

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
        for row in cb_text_splitted:
            if row:  # skip if row is empty
                length.append(len(row.split("\t")))
                content.append(row.split("\t"))

        if set(length) != set([5]):
            QMessageBox.warning(self, programName, ("The clipboard does not contain events!\n"
                                                    "Events must be organized in 5 columns separated by TAB character"))
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
            '''fields_list.append(EVENT_MODIFIER_FIELD_IDX )'''
            fields_list.append(4)

        if self.find_dialog.cbComment.isChecked():
            '''fields_list.append(EVENT_COMMENT_FIELD_IDX)'''
            fields_list.append(5)
        if not fields_list:
            self.find_dialog.lb_message.setText('<font color="red">No fields selected!</font>')
            return
        if not self.find_dialog.findText.text():
            self.find_dialog.lb_message.setText('<font color="red">Nothing to search!</font>')
            return

        '''for event_idx, event in enumerate(self.pj[OBSERVATIONS][self.observationId][EVENTS]):'''
        for event_idx in range(self.twEvents.rowCount()):
            if event_idx <= self.find_dialog.currentIdx:
                continue

            # find only in filtered events
            '''
            if self.filtered_subjects:
                if self.pj[OBSERVATIONS][self.observationId][EVENTS][event_idx][EVENT_SUBJECT_FIELD_IDX] not in self.filtered_subjects:
                    continue
            if self.filtered_behaviors:
                if self.pj[OBSERVATIONS][self.observationId][EVENTS][event_idx][EVENT_BEHAVIOR_FIELD_IDX] not in self.filtered_behaviors:
                    continue
            '''

            if ((not self.find_dialog.cbFindInSelectedEvents.isChecked())
                 or (self.find_dialog.cbFindInSelectedEvents.isChecked() and event_idx in self.find_dialog.rowsToFind)):

                for idx in fields_list:
                    '''
                    if (self.find_dialog.cb_case_sensitive.isChecked() and self.find_dialog.findText.text() in event[idx]) \
                       or (not self.find_dialog.cb_case_sensitive.isChecked() and
                           self.find_dialog.findText.text().upper() in event[idx].upper()):
                    '''
                    if (self.find_dialog.cb_case_sensitive.isChecked() and \
                        self.find_dialog.findText.text() in self.twEvents.item(event_idx, idx).text()) \
                        or (not self.find_dialog.cb_case_sensitive.isChecked() and
                            self.find_dialog.findText.text().upper() in self.twEvents.item(event_idx, idx).text().upper()):

                        self.find_dialog.currentIdx = event_idx
                        self.twEvents.scrollToItem(self.twEvents.item(event_idx, 0))
                        self.twEvents.selectRow(event_idx)
                        return

        if msg != "FIND_FROM_BEGINING":
            if dialog.MessageDialog(programName,
                                    f"<b>{self.find_dialog.findText.text()}</b> not found. Search from beginning?",
                                    [YES, NO]) == YES:
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
            nb_fields = ((explore_dialog.find_subject.text() != "") +
                         (explore_dialog.find_behavior.text() != "") +
                         (explore_dialog.find_modifier.text() != "") +
                         (explore_dialog.find_comment.text() != ""))

            for obs_id in sorted(self.pj[OBSERVATIONS]):
                for event_idx, event in enumerate(self.pj[OBSERVATIONS][obs_id][EVENTS]):
                    nb_results = 0
                    for text, idx in [(explore_dialog.find_subject.text(), EVENT_SUBJECT_FIELD_IDX),
                                      (explore_dialog.find_behavior.text(), EVENT_BEHAVIOR_FIELD_IDX),
                                      (explore_dialog.find_modifier.text(), EVENT_MODIFIER_FIELD_IDX),
                                      (explore_dialog.find_comment.text(), EVENT_COMMENT_FIELD_IDX)]:
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
                if self.pj[OBSERVATIONS][self.observationId][EVENTS][event_idx][EVENT_SUBJECT_FIELD_IDX] not in self.filtered_subjects:
                    continue
            # apply modif only to filtered behaviors
            if self.filtered_behaviors:
                if self.pj[OBSERVATIONS][self.observationId][EVENTS][event_idx][EVENT_BEHAVIOR_FIELD_IDX] not in self.filtered_behaviors:
                    continue

            if event_idx < self.find_replace_dialog.currentIdx:
                continue

            if ((not self.find_replace_dialog.cbFindInSelectedEvents.isChecked()) or
               (self.find_replace_dialog.cbFindInSelectedEvents.isChecked() and event_idx in self.find_replace_dialog.rowsToFind)):
                for idx1 in fields_list:
                    if idx1 <= self.find_replace_dialog.currentIdx_idx:
                        continue

                    if ((self.find_replace_dialog.cb_case_sensitive.isChecked() and self.find_replace_dialog.findText.text() in event[idx1])
                       or (not self.find_replace_dialog.cb_case_sensitive.isChecked() and
                       self.find_replace_dialog.findText.text().upper() in event[idx1].upper())):

                        number_replacement += 1
                        self.find_replace_dialog.currentIdx = event_idx
                        self.find_replace_dialog.currentIdx_idx = idx1
                        if self.find_replace_dialog.cb_case_sensitive.isChecked():
                            event[idx1] = event[idx1].replace(
                                self.find_replace_dialog.findText.text(), self.find_replace_dialog.replaceText.text()
                            )
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
            if dialog.MessageDialog(programName,
                                    f"{self.find_replace_dialog.findText.text()} not found.\nRestart find/replace from the beginning?",
                                    [YES, NO]) == YES:
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


    def export_tabular_events(self, mode: str = "tabular"):
        """
        export events from selected observations in various formats: TSV, CSV, ODS, XLSX, XLS, HTML

        Args:
            mode (str): export mode: must be ["tabular", "jwatcher"]
        """

        # ask user observations to analyze
        result, selectedObservations = self.selectObservations(MULTIPLE)
        if not selectedObservations:
            return

        out = ""
        # check if coded behaviors are defined in ethogram
        ethogram_behavior_codes = {self.pj[ETHOGRAM][idx][BEHAVIOR_CODE] for idx in self.pj[ETHOGRAM]}
        behaviors_not_defined = []
        out = ""  # will contain the output
        for obs_id in selectedObservations:
            for event in self.pj[OBSERVATIONS][obs_id][EVENTS]:
                if event[EVENT_BEHAVIOR_FIELD_IDX] not in ethogram_behavior_codes:
                    behaviors_not_defined.append(event[EVENT_BEHAVIOR_FIELD_IDX])
        if set(sorted(behaviors_not_defined)):
            out += ("The following behaviors are not defined in the ethogram: "
                    f"<b>{', '.join(set(sorted(behaviors_not_defined)))}</b><br><br>")


        # check if state events are paired
        not_paired_obs_list = []
        for obsId in selectedObservations:
            r, msg = project_functions.check_state_events_obs(obsId, self.pj[ETHOGRAM],
                                                              self.pj[OBSERVATIONS][obsId], self.timeFormat)

            if not r:
                out += f"Observation: <strong>{obsId}</strong><br>{msg}<br>"
                not_paired_obs_list.append(obsId)

        if out:
            out = f"Some observations have UNPAIRED state events<br><br>{out}"
            self.results = dialog.Results_dialog()
            self.results.setWindowTitle(f"{programName} - Check selected observations")
            self.results.ptText.setReadOnly(True)
            self.results.ptText.appendHtml(out)
            self.results.pbSave.setVisible(False)
            self.results.pbCancel.setVisible(True)

            if not self.results.exec_():
                return

        parameters = self.choose_obs_subj_behav_category(selectedObservations,
                                                         maxTime=0,
                                                         flagShowIncludeModifiers=False,
                                                         flagShowExcludeBehaviorsWoEvents=False)

        if not parameters["selected subjects"] or not parameters["selected behaviors"]:
            return

        if mode == "tabular":
            if len(selectedObservations) > 1:  # choose directory for exporting observations

                items = ("Tab Separated Values (*.tsv)",
                         "Comma separated values (*.csv)",
                         "Open Document Spreadsheet (*.ods)",
                         "Microsoft Excel Spreadsheet XLSX (*.xlsx)",
                         "Legacy Microsoft Excel Spreadsheet XLS (*.xls)",
                         "HTML (*.html)")
                item, ok = QInputDialog.getItem(self, "Export events format", "Available formats", items, 0, False)
                if not ok:
                    return
                outputFormat = re.sub(".* \(\*\.", "", item)[:-1]

                exportDir = QFileDialog().getExistingDirectory(self, "Choose a directory to export events", os.path.expanduser("~"),
                                                               options=QFileDialog.ShowDirsOnly)
                if not exportDir:
                    return

            if len(selectedObservations) == 1:
                extended_file_formats = ["Tab Separated Values (*.tsv)",
                                         "Comma Separated Values (*.csv)",
                                         "Open Document Spreadsheet ODS (*.ods)",
                                         "Microsoft Excel Spreadsheet XLSX (*.xlsx)",
                                         "Legacy Microsoft Excel Spreadsheet XLS (*.xls)",
                                         "HTML (*.html)"]
                file_formats = ["tsv", "csv", "ods", "xlsx", "xls", "html"]

                fileName, filter_ = QFileDialog().getSaveFileName(self, "Export events", "", ";;".join(extended_file_formats))
                if not fileName:
                    return

                outputFormat = file_formats[extended_file_formats.index(filter_)]
                if pathlib.Path(fileName).suffix != "." + outputFormat:
                    fileName = str(pathlib.Path(fileName)) + "." + outputFormat
                    # check if file with new extension already exists
                    if pathlib.Path(fileName).is_file():
                        if dialog.MessageDialog(programName,
                                                f"The file {fileName} already exists.",
                                                [CANCEL, OVERWRITE]) == CANCEL:
                            return

        if mode == "jwatcher":
            exportDir = QFileDialog().getExistingDirectory(self, "Choose a directory to export events",
                                                           os.path.expanduser("~"),
                                                           options=QFileDialog.ShowDirsOnly)
            if not exportDir:
                return

            outputFormat = "dat"

        mem_command = ""  # remember user choice when file already exists
        for obsId in selectedObservations:
            if (len(selectedObservations) > 1 or mode == "jwatcher"):

                '''
                fileName = str(pathlib.Path(pathlib.Path(exportDir) / safeFileName(obsId)).with suffix("." + outputFormat))
                '''
                fileName = f"{pathlib.Path(exportDir) / safeFileName(obsId)}.{outputFormat}"
                # check if file with new extension already exists
                if mem_command != "Overwrite all" and pathlib.Path(fileName).is_file():
                    if mem_command == "Skip all":
                        continue
                    mem_command = dialog.MessageDialog(programName,
                                                       f"The file {fileName} already exists.",
                                                       [OVERWRITE, "Overwrite all", "Skip", "Skip all", CANCEL])
                    if mem_command == CANCEL:
                        return
                    if mem_command in ["Skip", "Skip all"]:
                        continue

            if mode == "tabular":
                export_function = export_observation.export_events
            if mode == "jwatcher":
                export_function = export_observation.export_events_jwatcher

            r, msg = export_function(parameters,
                                     obsId,
                                     self.pj[OBSERVATIONS][obsId],
                                     self.pj[ETHOGRAM],
                                     fileName,
                                     outputFormat)

            if not r and msg:
                QMessageBox.critical(None, programName, msg, QMessageBox.Ok | QMessageBox.Default, QMessageBox.NoButton)


    def export_events_as_behavioral_sequences(self, separated_subjects=False, timed=False):
        """
        export events from selected observations by subject as behavioral sequences (plain text file)
        behaviors are separated by character specified in self.behaviouralStringsSeparator (usually pipe |)
        for use with Behatrix (see http://www.boris.unito.it/pages/behatrix)

        Args:
            separated_subjects (bool):
            timed (bool):
        """

        # ask user for observations to analyze
        result, selected_observations = select_observations.select_observations(self.pj,
                                                                                MULTIPLE,
                                                                                "Select observations to export as behavioral sequences")

        if not selected_observations:
            return

        parameters = self.choose_obs_subj_behav_category(selected_observations,
                                                         maxTime=0,
                                                         flagShowIncludeModifiers=True,
                                                         flagShowExcludeBehaviorsWoEvents=False)

        if not parameters[SELECTED_SUBJECTS] or not parameters[SELECTED_BEHAVIORS]:
            return

        fn = QFileDialog().getSaveFileName(self, "Export events as behavioral sequences", "", "Text files (*.txt);;All files (*)")
        file_name = fn[0] if type(fn) is tuple else fn

        if file_name:
            r, msg = export_observation.observation_to_behavioral_sequences(pj=self.pj,
                                                                            selected_observations=selected_observations,
                                                                            parameters=parameters,
                                                                            behaviors_separator=self.behaviouralStringsSeparator,
                                                                            separated_subjects= separated_subjects,
                                                                            timed=timed,
                                                                            file_name=file_name)
            if not r:
                logging.critical(f"Error while exporting events as behavioral sequences: {msg}")
                QMessageBox.critical(None, programName, f"Error while exporting events as behavioral sequences:<br>{msg}",
                                     QMessageBox.Ok | QMessageBox.Default, QMessageBox.NoButton)


    def transitions_matrix(self, mode):
        """
        create transitions frequencies matrix with selected observations, subjects and behaviors
        mode:
        * frequency
        * number
        * frequencies_after_behaviors
        """
        # ask user observations to analyze
        result, selectedObservations = self.selectObservations(MULTIPLE)
        if not selectedObservations:
            return

        plot_parameters = self.choose_obs_subj_behav_category(selectedObservations, maxTime=0, flagShowIncludeModifiers=True,
                                                              flagShowExcludeBehaviorsWoEvents=False)

        if not plot_parameters["selected subjects"] or not plot_parameters["selected behaviors"]:
            return

        flagMulti = False
        if len(plot_parameters[SELECTED_SUBJECTS]) == 1:

            fn = QFileDialog().getSaveFileName(self, "Create matrix of transitions " + mode, "",
                                               "Transitions matrix files (*.txt *.tsv);;All files (*)")
            fileName = fn[0] if type(fn) is tuple else fn  # PyQt4/5

        else:
            exportDir = QFileDialog(self).getExistingDirectory(self, "Choose a directory to save the transitions matrices",
                                                               os.path.expanduser("~"), options=QFileDialog(self).ShowDirsOnly)
            if not exportDir:
                return
            flagMulti = True

        flag_overwrite_all = False
        for subject in plot_parameters[SELECTED_SUBJECTS]:

            logging.debug(f"subjects: {subject}")

            strings_list = []
            for obsId in selectedObservations:
                strings_list.append(export_observation.events_to_behavioral_sequences(self.pj, obsId, subject,
                                                                                      plot_parameters,
                                                                                      self.behaviouralStringsSeparator))

            sequences, observed_behaviors = transitions.behavioral_strings_analysis(strings_list, self.behaviouralStringsSeparator)

            observed_matrix = transitions.observed_transitions_matrix(sequences,
                                                                      sorted(list(set(observed_behaviors +
                                                                                      plot_parameters[SELECTED_BEHAVIORS]))),
                                                                      mode=mode)

            if not observed_matrix:
                QMessageBox.warning(self, programName, f"No transitions found for <b>{subject}</b>")
                continue

            logging.debug(f"observed_matrix {mode}:\n{observed_matrix}")

            if flagMulti:
                try:

                    nf = f"{exportDir}{os.sep}{subject}_transitions_{mode}_matrix.tsv"

                    if os.path.isfile(nf) and not flag_overwrite_all:
                        answer = dialog.MessageDialog(programName, f"A file with same name already exists.<br><b>{nf}</b>",
                                                      ["Overwrite", "Overwrite all", CANCEL])
                        if answer == CANCEL:
                            continue
                        if answer == "Overwrite all":
                            flag_overwrite_all = True

                    with open(nf, "w") as outfile:
                        outfile.write(observed_matrix)
                except Exception:
                    QMessageBox.critical(self, programName, f"The file {nf} can not be saved")
            else:
                try:
                    with open(fileName, "w") as outfile:
                        outfile.write(observed_matrix)

                except Exception:
                    QMessageBox.critical(self, programName, f"The file {fileName} can not be saved")


    def transitions_dot_script(self):
        """
        create dot script (graphviz language) from transitions frequencies matrix
        """

        fn = QFileDialog().getOpenFileNames(self, "Select one or more transitions matrix files", "",
                                            "Transitions matrix files (*.txt *.tsv);;All files (*)")
        fileNames = fn[0] if type(fn) is tuple else fn

        out = ""
        try:
            for fileName in fileNames:
                with open(fileName, "r") as infile:
                    gv = transitions.create_transitions_gv_from_matrix(infile.read(),
                                                                        cutoff_all=0,
                                                                        cutoff_behavior=0,
                                                                        edge_label="percent_node")
                    with open(fileName + ".gv", "w") as f:
                        f.write(gv)

                    out += f"<b>{fileName}.gv</b> created<br>"

        except Exception:
            dialog.error_message("Error during dot script creation", sys.exc_info())

        if out:
            QMessageBox.information(self, programName,
                                    (f"{out}<br><br>The DOT scripts can be used with Graphviz or WebGraphviz "
                                     "to generate diagram"))


    def transitions_flow_diagram(self):
        """
        create flow diagram with graphviz (if installed) from transitions matrix
        """

        # check if dot present in path
        result = subprocess.getoutput("dot -V")
        if "graphviz" not in result:
            QMessageBox.critical(self, programName, ("The GraphViz package is not installed.<br>"
                                                     "The <b>dot</b> program was not found in the path.<br><br>"
                                                     'Go to <a href="http://www.graphviz.org">'
                                                     "http://www.graphviz.org</a> for information"))
            return

        fn = QFileDialog(self).getOpenFileNames(self, "Select one or more transitions matrix files", "",
                                                "Transitions matrix files (*.txt *.tsv);;All files (*)")
        fileNames = fn[0] if type(fn) is tuple else fn

        out = ""
        try:
            for fileName in fileNames:
                with open(fileName, "r") as infile:
                    gv = transitions.create_transitions_gv_from_matrix(infile.read(),
                                                                        cutoff_all=0,
                                                                        cutoff_behavior=0,
                                                                        edge_label="percent_node")

                    with open(tempfile.gettempdir() + os.sep + os.path.basename(fileName) + ".tmp.gv", "w") as f:
                        f.write(gv)
                    result = subprocess.getoutput((f'dot -Tpng -o "{fileName}.png" '
                                                    f'"{tempfile.gettempdir() + os.sep + os.path.basename(fileName)}.tmp.gv"'))
                    if not result:
                        out += f"<b>{fileName}.png</b> created<br>"
                    else:
                        out += f"Problem with <b>{fileName}</b><br>"
        except Exception:
            dialog.error_message("Error during flow diagram creation", sys.exc_info())

        if out:
            QMessageBox.information(self, programName, out)


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
            if dialog.MessageDialog(programName, "BORIS is doing some job. What do you want to do?",
                                    ["Wait", "Quit BORIS"]) == "Wait":
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
            self.saveConfigFile()

        self.close_tool_windows()


    def actionQuit_activated(self):
        self.close()


    def import_observations(self):
        """
        import observations from project file
        """

        fn = QFileDialog(self).getOpenFileName(self, "Choose a BORIS project file", "",
                                               "Project files (*.boris);;All files (*)")
        fileName = fn[0] if type(fn) is tuple else fn

        if self.projectFileName and fileName == self.projectFileName:
            QMessageBox.critical(None, programName,
                                 "This project is already open",
                                 QMessageBox.Ok | QMessageBox.Default, QMessageBox.NoButton)
            return

        if fileName:
            try:
                fromProject = json.loads(open(fileName, "r").read())
            except Exception:
                QMessageBox.critical(self, programName, "This project file seems corrupted")
                return

            # transform time to decimal
            fromProject = convert_time_to_decimal(fromProject)  # function in utilities.py

            dbc = dialog.ChooseObservationsToImport("Choose the observations to import:",
                                                    sorted(list(fromProject[OBSERVATIONS].keys())))

            if dbc.exec_():

                selected_observations = dbc.get_selected_observations()
                if selected_observations:
                    flagImported = False

                    # set of behaviors in current projet ethogram
                    behav_set = set([self.pj[ETHOGRAM][idx][BEHAVIOR_CODE] for idx in self.pj[ETHOGRAM]])

                    # set of subjects in current projet
                    subjects_set = set([self.pj[SUBJECTS][idx][SUBJECT_NAME] for idx in self.pj[SUBJECTS]])

                    for obsId in selected_observations:

                        # check if behaviors are in current project ethogram
                        new_behav_set = set([event[EVENT_BEHAVIOR_FIELD_IDX] for event in fromProject[OBSERVATIONS][obsId][EVENTS]
                                             if event[EVENT_BEHAVIOR_FIELD_IDX] not in behav_set])
                        if new_behav_set:
                            diag_result = dialog.MessageDialog(programName,
                                                               (f"Some coded behaviors in <b>{obsId}</b> are"
                                                                f"not in the ethogram:<br><b>{', '.join(new_behav_set)}</b>"),
                                                               ["Interrupt import", "Skip observation", "Import observation"])
                            if diag_result == "Interrupt import":
                                return
                            if diag_result == "Skip observation":
                                continue

                        # check if subjects are in current project
                        new_subject_set = set([event[EVENT_SUBJECT_FIELD_IDX] for event in fromProject[OBSERVATIONS][obsId][EVENTS]
                                               if event[EVENT_SUBJECT_FIELD_IDX] not in subjects_set])
                        if new_subject_set and new_subject_set != {""}:
                            diag_result = dialog.MessageDialog(programName,
                                                               (f"Some coded subjects in <b>{obsId}</b> are not defined in the project:<br>"
                                                                f"<b>{', '.join(new_subject_set)}</b>"),
                                                               ["Interrupt import", "Skip observation", "Import observation"])

                            if diag_result == "Interrupt import":
                                return

                            if diag_result == "Skip observation":
                                continue

                        if obsId in self.pj[OBSERVATIONS].keys():
                            diag_result = dialog.MessageDialog(programName,
                                                               (f"The observation <b>{obsId}</b>"
                                                                "already exists in the current project.<br>"),
                                                               ["Interrupt import", "Skip observation", "Rename observation"])
                            if diag_result == "Interrupt import":
                                return

                            if diag_result == "Rename observation":
                                self.pj[OBSERVATIONS][f"{obsId} (imported at {datetime_iso8601(datetime.datetime.now())})"] = dict(fromProject[OBSERVATIONS][obsId])
                                flagImported = True
                        else:
                            self.pj[OBSERVATIONS][obsId] = dict(fromProject[OBSERVATIONS][obsId])
                            flagImported = True

                    if flagImported:
                        QMessageBox.information(self, programName, "Observations imported successfully")


    def play_video(self):
        """
        play video
        check if first player ended
        """
        logging.debug(f"player #0 state: {self.dw_player[0].mediaplayer.get_state()}")
        logging.debug(f"position: {self.getLaps()}")

        if self.playerType == VLC:

            if self.playMode == FFMPEG:
                self.FFmpegTimer.start()
                self.actionPlay.setIcon(QIcon(":/pause"))
                return True

            elif self.playMode == VLC:
                # check if player 1 is ended
                '''  disabled 2019-12-11
                if self.dw_player[0].mediaplayer.get_state() == self.vlc_ended:
                    QMessageBox.information(self, programName, "The media file is ended, Use reset to play it again")
                    return False
                '''

                for i, player in enumerate(self.dw_player):
                    if (str(i + 1) in self.pj[OBSERVATIONS][self.observationId][FILE]
                       and self.pj[OBSERVATIONS][self.observationId][FILE][str(i + 1)]):
                        player.mediaListPlayer.play()

                self.timer.start(VLC_TIMER_OUT)
                self.timer_sound_signal.start()

                # start all timer for plotting data
                for data_timer in self.ext_data_timer_list:
                    data_timer.start()

                self.actionPlay.setIcon(QIcon(":/pause"))
                return True


    def pause_video(self):
        """
        pause media
        does not pause media if already paused (to prevent media played again)
        """

        if self.playerType == VLC:
            if self.playMode == FFMPEG:
                self.FFmpegTimer.stop()
            elif self.playMode == VLC:
                for i, player in enumerate(self.dw_player):
                    if (str(i + 1) in self.pj[OBSERVATIONS][self.observationId][FILE]
                            and self.pj[OBSERVATIONS][self.observationId][FILE][str(i + 1)]):
                        if player.mediaListPlayer.get_state() != self.vlc_paused:

                            self.timer.stop()
                            self.timer_sound_signal.stop()
                            # stop all timer for plotting data

                            for data_timer in self.ext_data_timer_list:
                                data_timer.stop()

                            player.mediaListPlayer.pause()
                            # wait until video is paused or ended
                            while True:
                                if player.mediaListPlayer.get_state() in [self.vlc_paused, self.vlc_ended, self.vlc_stopped]:
                                    break

                time.sleep(1)
                self.timer_out()

            self.timer_sound_signal_out()
            for idx in self.plot_data:
                self.timer_plot_data_out(self.plot_data[idx])

            self.actionPlay.setIcon(QIcon(":/play"))


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

            decrement = self.fast * self.play_rate if self.config_param.get(ADAPT_FAST_JUMP, ADAPT_FAST_JUMP_DEFAULT) else self.fast
            if self.playMode == FFMPEG:
                currentTime = self.FFmpegGlobalFrame / self.fps

                if int((currentTime - decrement) * self.fps) > 0:
                    self.FFmpegGlobalFrame = int((currentTime - decrement) * self.fps)
                else:
                    self.FFmpegGlobalFrame = 0   # position to init
                self.ffmpeg_timer_out()

            elif self.playMode == VLC:

                newTime = (sum(
                    self.dw_player[0].media_durations[0:self.dw_player[0].media_list.
                                                      index_of_item(self.dw_player[0].
                                                                    mediaplayer.get_media())]) +
                           self.dw_player[0].mediaplayer.get_time() - round(decrement * 1000))

                if newTime < decrement * 1000:
                    newTime = 0

                self.seek_mediaplayer(newTime)

                self.update_visualizations()

                # subtitles
                st_track_number = 0 if self.config_param[DISPLAY_SUBTITLES] else -1
                for player in self.dw_player:
                    player.mediaplayer.video_set_spu(st_track_number)


    def jumpForward_activated(self):
        """
        forward from current position
        """
        logging.debug("function: jumpForward_activated")

        if self.playerType == VLC:

            increment = self.fast * self.play_rate if self.config_param.get(ADAPT_FAST_JUMP, ADAPT_FAST_JUMP_DEFAULT) else self.fast
            if self.playMode == FFMPEG:

                self.FFmpegGlobalFrame += increment * self.fps

                if self.FFmpegGlobalFrame * (1000 / self.fps) >= sum(self.dw_player[0].media_durations):

                    logging.debug("end of last media")

                    self.FFmpegGlobalFrame = int(sum(self.dw_player[0].media_durations) * self.fps / 1000) - 1

                    logging.debug(f"FFmpegGlobalFrame {self.FFmpegGlobalFrame}  sum duration {sum(self.dw_player[0].media_durations)}")

                if self.FFmpegGlobalFrame > 0:
                    self.FFmpegGlobalFrame -= 1

                self.ffmpeg_timer_out()

            elif self.playMode == VLC:

                newTime = (sum(
                    self.dw_player[0].media_durations[0:self.dw_player[0].media_list.
                                                      index_of_item(self.dw_player[0].
                                                                    mediaplayer.get_media())])
                                               + self.dw_player[0].mediaplayer.get_time() + round(increment * 1000))

                self.seek_mediaplayer(newTime)

                self.update_visualizations()


    def update_visualizations(self, scroll_slider=False):
        """
        update visualization of video position, spectrogram and data
        """
        self.timer_out(scroll_slider)
        self.timer_sound_signal_out()
        for idx in self.plot_data:
            self.timer_plot_data_out(self.plot_data[idx])


    def reset_activated(self):
        """
        reset video to beginning
        """
        logging.debug("Reset activated")

        if self.playerType == VLC:

            self.pause_video()
            if self.playMode == FFMPEG:
                self.FFmpegGlobalFrame = 0   # position to init
                self.ffmpeg_timer_out()

            elif self.playMode == VLC:

                if OBSERVATION_TIME_INTERVAL in self.pj[OBSERVATIONS][self.observationId]:
                    self.seek_mediaplayer(int(self.pj[OBSERVATIONS][self.observationId][OBSERVATION_TIME_INTERVAL][0] * 1000))
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


    #from boris import vlc
    # check VLC
    '''
    if vlc.dll is None:
        msg = "This program requires the VLC media player.\nGo to http://www.videolan.org/vlc"
        QMessageBox.critical(None, programName, msg, QMessageBox.Ok | QMessageBox.Default, QMessageBox.NoButton)
        logging.critical(msg)
        sys.exit(1)

    if vlc.libvlc_get_version().decode("utf-8") < VLC_MIN_VERSION:
        msg = (f"The VLC media player seems very old ({vlc.libvlc_get_version()}). "
               "Go to http://www.videolan.org/vlc to update it")
        QMessageBox.critical(None, programName, msg, QMessageBox.Ok | QMessageBox.Default, QMessageBox.NoButton)
        logging.critical(msg)
        sys.exit(2)
    '''
    # check FFmpeg
    ret, msg = check_ffmpeg_path()
    if not ret:
        QMessageBox.critical(None, programName, "FFmpeg is not available.<br>Go to http://www.ffmpeg.org to download it",
                             QMessageBox.Ok | QMessageBox.Default, QMessageBox.NoButton)
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

    # QMessageBox.critical(window, programName, f"options.project: #{options.project}#")

    logging.debug(f"args: {args}")

    '''
    if args and len(args) > 0:
        project_to_open = args[0]
    '''

    if options.observation:
        if not project_to_open:
            print("No project file!")
            sys.exit()
        observation_to_open = options.observation

    '''
    if args and len(args) > 1:
        if not project_to_open:
            print("No project file!")
            sys.exit()
        observation_to_open = args[1]
    '''

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
    '''2019-12-12
    app.focusChanged.connect(window.changedFocusSlot)
    '''

    if not options.nosplashscreen and (sys.platform != "darwin"):
        splash.finish(window)

    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
