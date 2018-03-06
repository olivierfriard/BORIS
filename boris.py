#!/usr/bin/env python3

"""
BORIS
Behavioral Observation Research Interactive Software
Copyright 2012-2018 Olivier Friard

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
import platform
import logging
from optparse import OptionParser
import time
import json
from decimal import *
import re
import numpy as np
import hashlib
import subprocess
import sqlite3
import urllib.parse
import urllib.request
import urllib.error
import tempfile
import glob
import statistics
import datetime
import multiprocessing
import socket
import copy
import pathlib

try:
    from PyQt5.QtCore import *
    from PyQt5.QtGui import *
    from PyQt5.QtWidgets import *
    from boris_ui5 import *
except:
    logging.info("PyQt5 not installed!\nTrying with PyQt4")
    try:
        from PyQt4.QtCore import *
        from PyQt4.QtGui import *
        from boris_ui import *
    except:
        logging.critical("PyQt4 not installed!\nTry PyQt4")
        sys.exit()


import matplotlib
matplotlib.use("Qt4Agg" if QT_VERSION_STR[0] == "4" else "Qt5Agg")
import matplotlib.pyplot as plt
import matplotlib.transforms as mtransforms
from matplotlib import dates

import select_observations
import dialog
from edit_event import *
from project import *
import preferences
import param_panel
import observation
import modifiers_coding_map
import map_creator
import behav_coding_map_creator
import select_modifiers
from utilities import *
import tablib
import observations_list
import plot_spectrogram
import coding_pad
import subjects_pad
import transitions
import recode_widget
from config import *
import qrc_boris
from time_budget_widget import timeBudgetResults
import select_modifiers
import behaviors_coding_map
import plot_events
import project_functions
import plot_data_module
import measurement_widget
import irr
import db_functions
import export_observation


__version__ = "6.1.1"
__version_date__ = "2018-03-01"

if platform.python_version() < "3.4":
    logging.critical("BORIS requires Python 3.4+! You are using v. {}")
    sys.exit()

if sys.platform == "darwin":  # for MacOS
    os.environ["LC_ALL"] = "en_US.UTF-8"

# check if argument
usage = "usage: %prog [options] [PROJECT_PATH] [\"OBSERVATION ID\"]"
parser = OptionParser(usage=usage)

parser.add_option("-d", "--debug", action="store_true", default=False, dest="debug", help="Verbose mode for debugging")
parser.add_option("-v", "--version", action="store_true", default=False, dest="version", help="Print version")
parser.add_option("-n", "--nosplashscreen", action="store_true", default=False, help="No splash screen")
parser.add_option("-p", "--project", action="store", help="Project file")
parser.add_option("-o", "--observation", action="store",  help="Observation id")
'''
parser.add_option("-i", "--project-info", action="store_true", default=False, help="Project information")
parser.add_option("-l", "--observations-list", action="store_true", default=False, help="List of observations")
parser.add_option("-a", "--action", action="store",  help="action")
'''

(options, args) = parser.parse_args()

# set logging parameters
if options.debug:
    logging.basicConfig(level=logging.DEBUG)
else:
    logging.basicConfig(level=logging.INFO)

if options.version:
    print("version {0} release date: {1}".format(__version__, __version_date__))
    sys.exit(0)

video, live = 0, 1
FLAG_MATPLOTLIB_INSTALLED = True


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
        self.signal.emit({"URL": "{}:{}".format(s.getsockname()[0], s.getsockname()[1])})

        s.listen(5)
        while True:
            try:
                c, addr = s.accept()
                logging.debug("Got connection from {}".format(addr))
            except socket.timeout:
                s.close()
                logging.debug("Project server timeout")
                self.signal.emit({"MESSAGE": "Project server timeout"})
                return

            rq = c.recv(BUFFER_SIZE)
            logging.debug("request: {}".format(rq))

            if rq == b"get":
                msg = self.message
                while msg:
                    c.send(msg[0:BUFFER_SIZE])
                    msg = msg[BUFFER_SIZE:]
                c.close()
                logging.debug("Project sent")
                self.signal.emit({"MESSAGE": "Project sent to {}".format(addr[0])})

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
                self.signal.emit({"RECEIVED": "{}".format(rq2.decode("utf-8")), "SENDER": addr})


class TempDirCleanerThread(QThread):
    """
    class for cleaning image cache directory with qthread
    """
    def __init__(self, parent=None):
        QThread.__init__(self, parent)
        self.exiting = False
        self.tempdir = ""
        self.ffmpeg_cache_dir_max_size = 0

    def run(self):
        while self.exiting is False:
            if sum(os.path.getsize(self.tempdir + f) for f in os.listdir(self.tempdir)
                    if "BORIS@" in f and os.path.isfile(self.tempdir + f)) > self.ffmpeg_cache_dir_max_size:
                fl = sorted((os.path.getctime(self.tempdir + f), self.tempdir + f) for f in os.listdir(self.tempdir)
                            if "BORIS@" in f and os.path.isfile(self.tempdir + f))
                for ts, f in fl[0:int(len(fl) / 10)]:
                    os.remove(f)
            time.sleep(30)
            logging.debug("cleaning frame cache directory")

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
    ffmpeg_recode_process = None
    observationId = ""   # current observation id
    timeOffset = 0.0
    wrongTimeResponse = ""

    confirmSound = False               # if True each keypress will be confirmed by a beep
    embedPlayer = True                 # if True the VLC player will be embedded in the main window
    detachFrameViewer = False          # if True frame are displayed in a separate window (frameViewer class in dialog)

    spectrogramHeight = 80
    spectrogram_color_map = SPECTROGRAM_DEFAULT_COLOR_MAP

    frame_bitmap_format = FRAME_DEFAULT_BITMAT_FORMAT

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

    frame_viewer1_mem_geometry = None
    frame_viewer2_mem_geometry = None

    projectFileName = ""
    mediaTotalLength = None

    saveMediaFilePath = True

    beep_every = 0

    plot_colors = BEHAVIORS_PLOT_COLORS

    measurement_w = None
    memPoints = []   # memory of clicked points for measurement tool

    behaviouralStringsSeparator = "|"

    duration = []
    duration2 = []

    simultaneousMedia = False  # if second player was created

    # time laps
    fast = 10

    currentStates = {}
    flag_slow = False
    play_rate = 1

    play_rate_step = 0.1

    currentSubject = ""  # contains the current subject of observation

    detailedObs = {}

    codingMapWindowGeometry = 0

    projectWindowGeometry = 0   # memorize size of project window

    imageDirectory = ""   # image cache directory

    # FFmpeg
    allowFrameByFrame = False
    memx, memy = -1, -1

    # path for ffmpeg/ffmpeg.exe program
    ffmpeg_bin = ""
    ffmpeg_cache_dir = ""
    ffmpeg_cache_dir_max_size = 0
    frame_resize = 0

    # dictionary for FPS storing
    fps, fps2 = {}, {}

    playerType = ""   # VLC, LIVE, VIEWER
    playMode = VLC    # player mode can be VLC of FMPEG (for frame-by-frame mode)

    # spectrogram
    chunk_length = 60  # spectrogram chunk length in seconds

    memMedia = ""
    close_the_same_current_event = False
    tcp_port = 0
    cleaningThread = TempDirCleanerThread()
    bcm_dict = {}
    recent_projects = []


    def __init__(self, availablePlayers, ffmpeg_bin, parent=None):

        super(MainWindow, self).__init__(parent)
        self.setupUi(self)

        self.availablePlayers = availablePlayers
        self.ffmpeg_bin = ffmpeg_bin
        # set icons
        self.setWindowIcon(QIcon(":/logo.png"))
        self.actionPlay.setIcon(QIcon(":/play.png"))
        self.actionPause.setIcon(QIcon(":/pause.png"))
        self.actionReset.setIcon(QIcon(":/reset.png"))
        self.actionJumpBackward.setIcon(QIcon(":/jump_backward.png"))
        self.actionJumpForward.setIcon(QIcon(":/jump_forward.png"))

        self.actionFaster.setIcon(QIcon(":/faster.png"))
        self.actionSlower.setIcon(QIcon(":/slower.png"))
        self.actionNormalSpeed.setIcon(QIcon(":/normal_speed.png"))

        self.actionPrevious.setIcon(QIcon(":/previous.png"))
        self.actionNext.setIcon(QIcon(":/next.png"))

        self.actionSnapshot.setIcon(QIcon(":/snapshot.png"))

        self.actionFrame_by_frame.setIcon(QIcon(":/frame_mode"))
        self.actionFrame_backward.setIcon(QIcon(":/frame_backward"))
        self.actionFrame_forward.setIcon(QIcon(":/frame_forward"))

        self.setWindowTitle("{} ({})".format(programName, __version__))

        if os.path.isfile(sys.path[0]):  # for pyinstaller
            datadir = os.path.dirname(sys.path[0])
        else:
            datadir = sys.path[0]

        self.lbLogoBoris.setPixmap(QPixmap(datadir + "/logo_boris_500px.png"))
        self.lbLogoBoris.setScaledContents(False)
        self.lbLogoBoris.setAlignment(Qt.AlignCenter)

        self.lbLogoUnito.setPixmap(QPixmap(datadir + "/dbios_unito.png"))
        self.lbLogoUnito.setScaledContents(False)
        self.lbLogoUnito.setAlignment(Qt.AlignCenter)

        self.toolBar.setEnabled(False)
        # remove default page from toolBox
        self.toolBox.removeItem(0)
        self.toolBox.setVisible(False)

        # start with dock widget invisible
        self.dwObservations.setVisible(False)
        self.dwEthogram.setVisible(False)
        self.dwSubjects.setVisible(False)
        self.lb_current_media_time.setVisible(False)
        self.lbFocalSubject.setVisible(False)
        self.lbCurrentStates.setVisible(False)

        self.lb_current_media_time.setText("")
        self.lbFocalSubject.setText("")
        self.lbCurrentStates.setText("")

        self.lbFocalSubject.setText(NO_FOCAL_SUBJECT)

        font = QFont()
        font.setPointSize(15)
        self.lb_current_media_time.setFont(font)
        self.lbFocalSubject.setFont(font)
        self.lbCurrentStates.setFont(font)

        # Statusbar initialisation
        # add label to status bar
        self.lbTime = QLabel()
        self.lbTime.setFrameStyle(QFrame.StyledPanel)
        self.lbTime.setMinimumWidth(160)
        self.statusbar.addPermanentWidget(self.lbTime)

        # current subjects
        self.lbSubject = QLabel()
        self.lbSubject.setFrameStyle(QFrame.StyledPanel)
        self.lbSubject.setMinimumWidth(160)
        self.statusbar.addPermanentWidget(self.lbSubject)

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

        self.imagesList = set()
        self.FFmpegGlobalFrame = 0

        self.menu_options()

        self.connections()


    def create_live_tab(self):
        """
        create tab with widget for live observation
        """

        self.liveLayout = QGridLayout()
        self.textButton = QPushButton("Start live observation")
        self.textButton.setMinimumHeight(60)
        self.textButton.clicked.connect(self.start_live_observation)
        self.liveLayout.addWidget(self.textButton)
        self.lbTimeLive = QLabel()
        self.lbTimeLive.setAlignment(Qt.AlignCenter)

        font = QFont("Monospace")
        font.setPointSize(48)
        self.lbTimeLive.setFont(font)
        if self.timeFormat == HHMMSS:
            self.lbTimeLive.setText("00:00:00.000")
        if self.timeFormat == S:
            self.lbTimeLive.setText("0.000")

        self.liveLayout.addWidget(self.lbTimeLive)
        self.liveTab = QWidget()
        self.liveTab.setLayout(self.liveLayout)
        self.toolBox.insertItem(2, self.liveTab, "Live")


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
                    pn = "Unnamed project ({})".format(self.projectFileName)
                else:
                    pn = "Unnamed project"

        self.setWindowTitle("{}{}{}".format(self.observationId + " - " * (self.observationId != ""),
                                            pn + (" - " * (pn != "")), programName))

        # project menu
        for w in [self.actionEdit_project, self.actionSave_project, self.actionSave_project_as,
                  self.actionClose_project, self.actionSend_project, self.actionNew_observation,
                  self.actionRemove_path_from_media_files]:
            w.setEnabled(flag)

        # observations

        # enabled if project
        self.actionOpen_observation.setEnabled(self.pj[OBSERVATIONS] != {})
        self.actionEdit_observation_2.setEnabled(self.pj[OBSERVATIONS] != {})
        self.actionObservationsList.setEnabled(self.pj[OBSERVATIONS] != {})

        # enabled if observation
        flagObs = self.observationId != ""

        self.actionAdd_event.setEnabled(flagObs)
        self.actionClose_observation.setEnabled(flagObs)
        self.actionLoad_observations_file.setEnabled(flag)

        self.actionExportEvents.setEnabled(flag)
        self.actionExport_aggregated_events.setEnabled(flag)

        self.actionExportEventString.setEnabled(flag)
        self.actionExport_events_as_Praat_TextGrid.setEnabled(flag)
        self.actionExtract_events_from_media_files.setEnabled(flag)

        self.actionDelete_all_observations.setEnabled(flagObs)
        self.actionSelect_observations.setEnabled(flagObs)
        self.actionDelete_selected_observations.setEnabled(flagObs)
        self.actionEdit_event.setEnabled(flagObs)
        self.actionEdit_selected_events.setEnabled(flagObs)
        self.actionFind_events.setEnabled(flagObs)
        self.actionFind_replace_events.setEnabled(flagObs)

        self.actionCheckStateEvents.setEnabled(flag)
        self.actionCheckStateEventsSingleObs.setEnabled(flag)
        self.actionRunEventOutside.setEnabled(flag)

        self.actionMedia_file_information.setEnabled(flagObs)
        self.actionMedia_file_information.setEnabled(self.playerType == VLC)
        self.menuCreate_subtitles_2.setEnabled(flag)

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
                zv = self.mediaplayer.video_get_scale()
                self.actionZoom1_fitwindow.setChecked(zv == 0)
                self.actionZoom1_1_1.setChecked(zv == 1)
                self.actionZoom1_1_2.setChecked(zv == 0.5)
                self.actionZoom1_1_4.setChecked(zv == 0.25)
                self.actionZoom1_2_1.setChecked(zv == 2)
            except:
                pass
    
            if self.simultaneousMedia:
                self.menuZoom2.setEnabled((self.playerType == VLC) and (self.playMode == VLC))
                try:
                    zv = self.mediaplayer2.video_get_scale()
                    self.actionZoom2_fitwindow.setChecked(zv == 0)
                    self.actionZoom2_1_1.setChecked(zv == 1)
                    self.actionZoom2_1_2.setChecked(zv == 0.5)
                    self.actionZoom2_1_4.setChecked(zv == 0.25)
                    self.actionZoom2_2_1.setChecked(zv == 2)
                except:
                    pass

        self.actionPlay.setEnabled(self.playerType == VLC)
        self.actionPause.setEnabled(self.playerType == VLC)
        self.actionReset.setEnabled(self.playerType == VLC)
        self.actionFaster.setEnabled(self.playerType == VLC)
        self.actionSlower.setEnabled(self.playerType == VLC)
        self.actionNormalSpeed.setEnabled(self.playerType == VLC)
        self.actionPrevious.setEnabled(self.playerType == VLC)
        self.actionNext.setEnabled(self.playerType == VLC)
        self.actionSnapshot.setEnabled(self.playerType == VLC)
        self.actionFrame_by_frame.setEnabled(True)

        self.actionFrame_backward.setEnabled(flagObs and (self.playMode == FFMPEG))
        self.actionFrame_forward.setEnabled(flagObs and (self.playMode == FFMPEG))

        # Tools
        self.actionShow_spectrogram.setEnabled(self.playerType == VLC)
        self.actionShow_data_files.setEnabled(self.playerType == VLC)
        # geometric measurements
        self.actionDistance.setEnabled(flagObs and (self.playMode == FFMPEG))
        self.actionCoding_pad.setEnabled(flagObs)
        self.actionSubjects_pad.setEnabled(flagObs)
        self.actionBehaviors_coding_map.setEnabled(flagObs)

        # Analysis
        for w in [self.actionTime_budget, self.actionTime_budget_by_behaviors_category, self.actionTime_budget_report]: 
            w.setEnabled(self.pj[OBSERVATIONS] != {})
        # plot events
        self.menuPlot_events.setEnabled(FLAG_MATPLOTLIB_INSTALLED and self.pj[OBSERVATIONS] != {})
        # IRR
        self.menuInter_rater_reliability.setEnabled(self.pj[OBSERVATIONS] != {})
        #self.actionCohen_s_kappa.setEnabled(self.pj[OBSERVATIONS] != {})

        self.menuCreate_transitions_matrix.setEnabled(self.pj[OBSERVATIONS] != {})

        # statusbar label
        for w in [self.lbTime, self.lbSubject, self.lbTimeOffset, self.lbSpeed]:
            w.setVisible(self.playerType == VLC)

    def connections(self):

        # menu file
        self.actionNew_project.triggered.connect(self.new_project_activated)
        self.actionOpen_project.triggered.connect(self.open_project_activated)
        self.actionEdit_project.triggered.connect(self.edit_project_activated)
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
        self.actionView_observation.triggered.connect(lambda: self.open_observation("view"))
        self.actionEdit_observation_2.triggered.connect(self.edit_observation)
        self.actionObservationsList.triggered.connect(self.observations_list)

        self.actionClose_observation.triggered.connect(self.close_observation)

        self.actionAdd_event.triggered.connect(self.add_event)
        self.actionEdit_event.triggered.connect(self.edit_event)

        self.actionCheckStateEvents.triggered.connect(lambda: self.check_state_events("all"))
        self.actionCheckStateEventsSingleObs.triggered.connect(lambda: self.check_state_events("current"))
        self.actionRunEventOutside.triggered.connect(self.run_event_outside)

        self.actionSelect_observations.triggered.connect(self.select_events_between_activated)

        self.actionEdit_selected_events.triggered.connect(self.edit_selected_events)
        self.actionFind_events.triggered.connect(self.find_events)
        self.actionFind_replace_events.triggered.connect(self.find_replace_events)
        self.actionDelete_all_observations.triggered.connect(self.delete_all_events)
        self.actionDelete_selected_observations.triggered.connect(self.delete_selected_events)

        self.actionMedia_file_information.triggered.connect(self.media_file_info)

        self.actionLoad_observations_file.triggered.connect(self.import_observations)

        self.actionExportEvents.triggered.connect(self.export_tabular_events)
        self.actionExportEventString.triggered.connect(self.export_string_events)
        self.actionExport_aggregated_events.triggered.connect(self.export_aggregated_events)
        self.actionExport_events_as_Praat_TextGrid.triggered.connect(self.export_state_events_as_textgrid)

        self.actionExtract_events_from_media_files.triggered.connect(self.extract_events)

        self.actionCohen_s_kappa.triggered.connect(self.irr_cohen_kappa)

        self.actionAll_transitions.triggered.connect(lambda: self.transitions_matrix("frequency"))
        self.actionNumber_of_transitions.triggered.connect(lambda: self.transitions_matrix("number"))
        self.actionFrequencies_of_transitions_after_behaviors.triggered.connect(lambda: self.transitions_matrix(
                                                                                        "frequencies_after_behaviors"))

        # menu playback
        self.actionJumpTo.triggered.connect(self.jump_to)

        # menu Tools
        self.action_create_modifiers_coding_map.triggered.connect(self.modifiers_coding_map_creator)
        self.action_create_behaviors_coding_map.triggered.connect(self.behaviors_coding_map_creator)

        self.actionShow_spectrogram.triggered.connect(self.show_spectrogram)
        self.actionShow_data_files.triggered.connect(self.show_data_files)
        self.actionDistance.triggered.connect(self.distance)
        self.actionBehaviors_coding_map.triggered.connect(self.show_behaviors_coding_map)

        self.actionCoding_pad.triggered.connect(self.show_coding_pad)
        self.actionSubjects_pad.triggered.connect(self.show_subjects_pad)
        
        self.actionRecode_resize_video.triggered.connect(self.recode_resize_video)
        self.actionMedia_file_information_2.triggered.connect(self.media_file_info)

        self.actionCreate_transitions_flow_diagram.triggered.connect(self.transitions_dot_script)
        self.actionCreate_transitions_flow_diagram_2.triggered.connect(self.transitions_flow_diagram)

        #self.actionConverters_manager.triggered.connect(self.converters_manager)

        # menu Analyze
        self.actionTime_budget.triggered.connect(lambda: self.time_budget("by_behavior"))
        self.actionTime_budget_by_behaviors_category.triggered.connect(lambda: self.time_budget("by_category"))
        self.actionTime_budget_report.triggered.connect(lambda: self.time_budget("synthetic"))

        self.actionPlot_events1.triggered.connect(self.plot_events1_triggered)
        self.actionPlot_events2.triggered.connect(self.plot_events2_triggered)

        # menu Help
        self.actionUser_guide.triggered.connect(self.actionUser_guide_triggered)
        self.actionAbout.triggered.connect(self.actionAbout_activated)
        self.actionCheckUpdate.triggered.connect(self.actionCheckUpdate_activated)

        # toolbar
        self.actionPlay.triggered.connect(self.play_activated)
        self.actionPause.triggered.connect(self.pause_video)
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

        # table Widget double click
        self.twEvents.itemDoubleClicked.connect(self.twEvents_doubleClicked)
        self.twEthogram.itemDoubleClicked.connect(self.twEthogram_doubleClicked)
        self.twSubjects.itemDoubleClicked.connect(self.twSubjects_doubleClicked)

        # Actions for twEthogram context menu
        self.twEthogram.setContextMenuPolicy(Qt.ActionsContextMenu)

        self.actionViewBehavior.triggered.connect(self.view_behavior)
        self.twEthogram.addAction(self.actionViewBehavior)

        self.actionFilterBehaviors.triggered.connect(self.filter_behaviors)
        self.twEthogram.addAction(self.actionFilterBehaviors)

        self.actionShowAllBehaviors.triggered.connect(self.show_all_behaviors)
        self.twEthogram.addAction(self.actionShowAllBehaviors)

        # Actions for twSubjects context menu
        self.twSubjects.setContextMenuPolicy(Qt.ActionsContextMenu)
        self.actionFilterSubjects.triggered.connect(self.filter_subjects)
        self.twSubjects.addAction(self.actionFilterSubjects)

        self.actionShowAllSubjects.triggered.connect(self.show_all_subjects)
        self.twSubjects.addAction(self.actionShowAllSubjects)

        # Actions for twEvents context menu
        self.twEvents.setContextMenuPolicy(Qt.ActionsContextMenu)

        self.twEvents.addAction(self.actionAdd_event)
        self.twEvents.addAction(self.actionEdit_selected_events)
        self.twEvents.addAction(self.actionFind_events)
        self.twEvents.addAction(self.actionFind_replace_events)

        separator2 = QAction(self)
        separator2.setSeparator(True)
        self.twEvents.addAction(separator2)

        self.twEvents.addAction(self.actionCheckStateEventsSingleObs)
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
        self.timer_spectro = QTimer(self)
        # TODO check value of interval
        self.timer_spectro.setInterval(200)
        self.timer_spectro.timeout.connect(self.timer_spectro_out)


        # timer for timing the live observation
        self.liveTimer = QTimer(self)
        self.liveTimer.timeout.connect(self.liveTimer_out)

        self.readConfigFile()

        # timer for automatic backup
        self.automaticBackupTimer = QTimer(self)
        self.automaticBackupTimer.timeout.connect(self.automatic_backup)
        if self.automaticBackup:
            self.automaticBackupTimer.start(self.automaticBackup * 60000)


    def remove_media_files_path(self):
        """
        remove path of media files
        """

        if dialog.MessageDialog(programName, ("Removing the path of media files from the project file is irreversible.<br>"
                                              "Are you sure to continue?"),
                                              [YES, NO]) == NO:
            return

        self.pj = project_functions.remove_media_files_path(self.pj)
        self.projectChanged = True


    def irr_cohen_kappa(self):
        """
        calculate the Inter-Rater Reliability index - Cohen's Kappa of 2 observations
        https://en.wikipedia.org/wiki/Cohen%27s_kappa
        """

        # ask user observations to analyze
        result, selected_observations = self.selectObservations(MULTIPLE)
        if not selected_observations:
            return
        if len(selected_observations) < 2:
            QMessageBox.information(self, programName, "Select almost 2 observations for IRR analysis")
            return

        plot_parameters = self.choose_obs_subj_behav_category(selected_observations,
                                                              maxTime=0,
                                                              flagShowIncludeModifiers=True,
                                                              flagShowExcludeBehaviorsWoEvents=False)

        if not plot_parameters["selected subjects"] or not plot_parameters["selected behaviors"]:
            return

        # ask for time slice
        i, ok = QInputDialog.getDouble(self, "IRR", "Time slice (in seconds):", 1.0, 0.001, 86400, 3)
        if not ok:
            return
        interval = float2decimal(i)

        ok, msg, db_connector = db_functions.load_aggregated_events_in_db(self.pj,
                                                           plot_parameters["selected subjects"],
                                                           selected_observations,
                                                           plot_parameters["selected behaviors"])

        if not ok:
            self.results = dialog.ResultsWidget()
            self.results.setWindowTitle("Check state events")
            self.results.ptText.clear()
            self.results.ptText.setReadOnly(True)
            self.results.ptText.appendHtml(msg)
            self.results.show()
            return

        cursor = db_connector.cursor()
        out = ("Cohen's Kappa - Index of Inter-rater Reliability\n\n"
               "Interval time: {interval:.3f} s\n"
               "Selected subjects: {selected_subjects}\n\n").format(interval=interval,
                                                                    selected_subjects=", ".join(plot_parameters["selected subjects"]))
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
                                             plot_parameters["selected subjects"],
                                             plot_parameters["include modifiers"])
                    irr_results[selected_observations.index(obs_id1), selected_observations.index(obs_id2)] = K
                    irr_results[selected_observations.index(obs_id2), selected_observations.index(obs_id1)] = K
                    out += msg + "\n=============\n"
                    mem_done.append(set([obs_id1, obs_id2]))

        out2 = "\t{}\n".format("\t".join(list(selected_observations)))
        for r in range(irr_results.shape[0]):
            out2 += "{}\t".format(selected_observations[r])
            out2 += "\t".join(["%8.6f" % x for x in irr_results[r,:]]) + "\n"

        self.results = dialog.ResultsWidget()
        self.results.setWindowTitle(programName + " - IRR - Cohen's Kappa analysis results")
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
                            modifiers += "<br>Name: {}<br>Type: {}<br>".format(behav[MODIFIERS][idx]["name"]
                                                                               if behav[MODIFIERS][idx]["name"] else "-",
                                                                               MODIFIERS_STR[behav[MODIFIERS][idx]["type"]])

                        if behav[MODIFIERS][idx]["values"]:
                            modifiers += "Values:<br>"
                            for m in behav[MODIFIERS][idx]["values"]:
                                modifiers += "{}, ".format(m)
                            modifiers = modifiers.strip(" ,") + "<br>"
                else:
                    modifiers = "-"

                self.results = dialog.ResultsWidget()
                self.results.setWindowTitle("View behavior")
                self.results.ptText.clear()
                self.results.ptText.setReadOnly(True)

                txt = ("Code: <b>{}</b><br>"
                       "Type: {}<br>"
                       "Key: <b>{}</b><br><br>"
                       "Description: {}<br><br>"
                       "Category: {}<br><br>"
                       "Exclude: {}<br><br><br>"
                       "Modifiers:<br>{}").format(behav["code"],
                                                  behav["type"],
                                                  behav["key"],
                                                  behav["description"],
                                                  behav["category"] if behav["category"] else "-",
                                                  behav["excluded"],
                                                  modifiers)

                self.results.ptText.appendHtml(txt)
                self.results.show()


    def send_project_via_socket(self):
        """
        send project to a device via socket
        """

        def receive_signal(msg_dict):

            if "RECEIVED" in msg_dict:
                try:
                    sent_obs = json.loads(msg_dict["RECEIVED"][:-5])  # cut final
                except:
                    logging.debug("error receiving observation")
                    del self.w
                    self.actionSend_project.setText("Project server")
                    return

                logging.debug("decoded {} length: {}".format(type(sent_obs), len(sent_obs)))

                flag_msg = False
                mem_obsid = ""
                for obsId in sent_obs:

                    self.w.lwi.addItem(QListWidgetItem("{}: Observation {} received".format(
                                                    datetime.datetime.now().isoformat(),
                                                    obsId)))
                    self.w.lwi.scrollToBottom()

                    if obsId in self.pj[OBSERVATIONS]:
                        flag_msg = True
                        response = dialog.MessageDialog(programName, ("An observation with the same id<br><b>{}</b><br>"
                                                                      "received from<br><b>{}</b><br>"
                                                                      "already exists in the current project.").format(
                                                                                         obsId, msg_dict["SENDER"][0]),
                                                        ["Overwrite it", "Rename received observation",
                                                        CANCEL])
                        if response == CANCEL:
                            return
                        self.projectChanged = True
                        if response == "Overwrite it":
                            self.pj[OBSERVATIONS][obsId] = dict(sent_obs[obsId])

                        if response == "Rename received observation":
                            new_id = obsId
                            while new_id in self.pj[OBSERVATIONS]:
                                new_id, ok = QInputDialog.getText(self,
                                                                  "Rename observation received from {}".format(
                                                                                               msg_dict["SENDER"][0]),
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
                self.w.label.setText("Project server URL:<br><b>{}</b><br><br>Timeout: 30 minutes".format(msg_dict["URL"]))

            else:
                if "stopped" in msg_dict["MESSAGE"] or "timeout" in msg_dict["MESSAGE"]:
                    del self.w
                    self.actionSend_project.setText("Project server")
                else:
                    self.w.lwi.addItem(QListWidgetItem("{}: {}".format(datetime.datetime.now().isoformat(), msg_dict["MESSAGE"])))
                    self.w.lwi.scrollToBottom()

        if "server" in self.actionSend_project.text():

            include_obs = NO
            if self.pj[OBSERVATIONS]:
                include_obs = dialog.MessageDialog(programName, "Include observations?", [YES, NO, CANCEL])
                if include_obs == CANCEL:
                    return

            self.w = recode_widget.Info_widget()
            self.w.resize(450, 100)
            self.w.setWindowFlags(Qt.WindowStaysOnTopHint)
            self.w.setWindowTitle("Project server")
            self.w.label.setText("")
            self.w.show()
            app.processEvents()

            cp_project = copy.deepcopy(self.pj)
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


    def recode_resize_video(self):
        """
        re-encode video with ffmpeg
        """

        timerFFmpegRecoding = QTimer()

        def timerFFmpegRecoding_timeout():
            """
            check if process finished
            """
            if not self.ffmpeg_recode_process.is_alive():
                timerFFmpegRecoding.stop()
                self.w.hide()
                del(self.w)
                self.ffmpeg_recode_process = None

        if self.ffmpeg_recode_process:
            QMessageBox.warning(self, programName, "BORIS is already re-encoding a video...")
            return

        fn = QFileDialog(self).getOpenFileNames(self, "Select one or more media files to re-encode/resize", "", "Media files (*)")
        fileNames = fn[0] if type(fn) is tuple else fn

        if fileNames:

            horiz_resol, ok = QInputDialog.getInt(self, "", ("Horizontal resolution (in pixels)\nThe aspect ratio will be maintained"),
                                                  1024, 352, 2048, 20)
            if not ok:
                return

            # check if recoded files already exist
            files_list = []
            for file_name in fileNames:
                if os.path.isfile("{input}.re-encoded.{horiz_resol}px.avi".format(input=file_name,
                                                                                  horiz_resol=horiz_resol)):
                    files_list.append("{input}.re-encoded.{horiz_resol}px.avi".format(input=file_name,
                                                                                      horiz_resol=horiz_resol))
            if files_list:
                response = dialog.MessageDialog(programName, "Some file(s) already exist.\n\n" + "\n".join(files_list),
                                                ["Overwrite all",
                                                CANCEL])
                if response == CANCEL:
                    return

            self.w = recode_widget.Info_widget()
            self.w.lwi.setVisible(False)
            self.w.resize(350, 100)
            self.w.setWindowFlags(Qt.WindowStaysOnTopHint)
            self.w.setWindowTitle("Re-encoding and resizing with FFmpeg")
            self.w.label.setText("This operation can be long. Be patient...\n\n" + "\n".join(fileNames))
            self.w.show()

            # check in platform win and program frozen by pyinstaller
            if sys.platform.startswith("win") and getattr(sys, "frozen", False):
                app.processEvents()
                ffmpeg_recode(fileNames, horiz_resol, ffmpeg_bin)
                self.w.hide()
            else:

                self.ffmpeg_recode_process = multiprocessing.Process(target=ffmpeg_recode,
                                                                     args=(fileNames, horiz_resol, ffmpeg_bin,))
                self.ffmpeg_recode_process.start()

                timerFFmpegRecoding.timeout.connect(timerFFmpegRecoding_timeout)
                timerFFmpegRecoding.start(15000)


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
            self.codingpad.compose()
            self.codingpad.show()
            self.codingpad.setGeometry(self.codingpad_geometry_memory.x(),
                                       self.codingpad_geometry_memory.y(),
                                       self.codingpad_geometry_memory.width(),
                                       self.codingpad_geometry_memory.height())

        else:
            filtered_behaviors = [self.twEthogram.item(i, 1).text() for i in range(self.twEthogram.rowCount())]
            self.codingpad = coding_pad.CodingPad(self.pj, filtered_behaviors)
            self.codingpad.setWindowFlags(Qt.WindowStaysOnTopHint)
            #self.codingpad.sendEventSignal.connect(self.signal_from_coding_pad)
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
            self.subjects_pad.compose()
            self.subjects_pad.show()
            self.subjects_pad.setGeometry(self.subjectspad_geometry_memory.x(),
                                          self.subjectspad_geometry_memory.y(),
                                          self.subjectspad_geometry_memory.width(),
                                          self.subjectspad_geometry_memory.height())
        else:
            filtered_subjects = [self.twSubjects.item(i, SUBJECT_NAME_FIELD_IDX).text()
                                 for i in range(self.twSubjects.rowCount())]
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
        self.load_behaviors_in_twEthogram([self.pj[ETHOGRAM][x]["code"] for x in self.pj[ETHOGRAM]])


    def show_all_subjects(self):
        """
        show all subjects in subjects list
        """
        self.load_subjects_in_twSubjects([self.pj[SUBJECTS][x]["name"] for x in self.pj[SUBJECTS]])


    def filter_behaviors(self):
        """
        allow user to filter behaviors in ethogram
        """

        if not self.pj[ETHOGRAM]:
            return

        paramPanelWindow = param_panel.Param_panel()
        paramPanelWindow.setMaximumHeight(800)
        paramPanelWindow.setMaximumWidth(600)
        paramPanelWindow.setWindowTitle("Select the behaviors to show in the ethogram table")
        for w in [paramPanelWindow.lwSubjects, paramPanelWindow.pbSelectAllSubjects, paramPanelWindow.pbUnselectAllSubjects,
                  paramPanelWindow.pbReverseSubjectsSelection, paramPanelWindow.lbSubjects, paramPanelWindow.cbIncludeModifiers,
                  paramPanelWindow.cbExcludeBehaviors, paramPanelWindow.frm_time]:
            w.setVisible(False)

        # behaviors filtered
        filtered_behaviors = [self.twEthogram.item(i, 1).text() for i in range(self.twEthogram.rowCount())]

        if BEHAVIORAL_CATEGORIES in self.pj:
            categories = self.pj[BEHAVIORAL_CATEGORIES][:]
            # check if behavior not included in a category
            if "" in [self.pj[ETHOGRAM][idx]["category"] for idx in self.pj[ETHOGRAM]
                      if "category" in self.pj[ETHOGRAM][idx]]:
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

            for behavior in [self.pj[ETHOGRAM][x]["code"] for x in sorted_keys(self.pj[ETHOGRAM])]:

                if ((categories == ["###no category###"]) or
                   (behavior in [self.pj[ETHOGRAM][x]["code"] for x in self.pj[ETHOGRAM]
                                 if "category" in self.pj[ETHOGRAM][x] and
                                    self.pj[ETHOGRAM][x]["category"] == category])):

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
            self.load_behaviors_in_twEthogram(paramPanelWindow.selectedBehaviors)
            # update subjects pad
            if hasattr(self, "codingpad"):
                self.codingpad.filtered_behaviors = [self.twEthogram.item(i, 1).text() for i in range(self.twEthogram.rowCount())]
                self.codingpad.compose()

    def filter_subjects(self):
        """
        allow user to select subjects to show in the subjects list
        """

        paramPanelWindow = param_panel.Param_panel()
        paramPanelWindow.setMaximumHeight(800)
        paramPanelWindow.setMaximumWidth(600)
        paramPanelWindow.setWindowTitle("Select the subjects to show in the subjects list")
        paramPanelWindow.lbBehaviors.setText("Subjects")

        for w in [paramPanelWindow.lwSubjects, paramPanelWindow.pbSelectAllSubjects, paramPanelWindow.pbUnselectAllSubjects,
                  paramPanelWindow.pbReverseSubjectsSelection, paramPanelWindow.lbSubjects, paramPanelWindow.cbIncludeModifiers,
                  paramPanelWindow.cbExcludeBehaviors, paramPanelWindow.frm_time]:
            w.setVisible(False)

        # subjects filtered
        filtered_subjects = [self.twSubjects.item(i, SUBJECT_NAME_FIELD_IDX).text() for i in range(self.twSubjects.rowCount())]

        for subject in [self.pj[SUBJECTS][x]["name"] for x in sorted_keys(self.pj[SUBJECTS])]:

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
            # update subjects pad
            if hasattr(self, "subjects_pad"):
                self.subjects_pad.filtered_subjects = [self.twSubjects.item(i, SUBJECT_NAME_FIELD_IDX).text()
                                                       for i in range(self.twSubjects.rowCount())]
                self.subjects_pad.compose()


    def extract_events(self):
        """
        extract sequences from media file corresponding to coded events with FFmpeg
        in case of point event, from -n to +n seconds are extracted (n = self.repositioningTimeOffset)
        """
        result, selectedObservations = self.selectObservations(MULTIPLE)

        if not selectedObservations:
            return

        plot_parameters = self.choose_obs_subj_behav_category(selectedObservations, maxTime=0,
                                                              flagShowIncludeModifiers=False,
                                                              flagShowExcludeBehaviorsWoEvents=False)

        if not plot_parameters["selected subjects"] or not plot_parameters["selected behaviors"]:
            return

        exportDir = QFileDialog(self).getExistingDirectory(self, "Choose a directory to extract events",
                                                           os.path.expanduser("~"),
                                                           options=QFileDialog(self).ShowDirsOnly)
        if not exportDir:
            return

        # check self.repositioningTimeOffset
        text, ok = QInputDialog.getDouble(self, "Offset to substract/add to start/stop times",
                                          "Time offset (in seconds):", 0.0, 0.0, 86400, 1)
        if not ok:
            return
        try:
            timeOffset = float2decimal(text)
        except:
            QMessageBox.warning(self, programName, "<b>{}</b> is not recognized as time offset".format(text))
            return

        flagUnpairedEventFound = False

        cursor = db_functions.load_events_in_db(self.pj, plot_parameters["selected subjects"],
                                                selectedObservations, plot_parameters["selected behaviors"])

        for obsId in selectedObservations:

            for nplayer in [PLAYER1, PLAYER2]:

                if not self.pj[OBSERVATIONS][obsId][FILE][nplayer]:
                    continue

                duration1 = []   # in seconds
                for mediaFile in self.pj[OBSERVATIONS][obsId][FILE][nplayer]:
                    duration1.append(self.pj[OBSERVATIONS][obsId]["media_info"]["length"][mediaFile])

                logging.debug("duration player {}: {}".format(nplayer, duration1))

                for subject in plot_parameters["selected subjects"]:

                    for behavior in plot_parameters["selected behaviors"]:

                        cursor.execute("SELECT occurence FROM events WHERE observation = ? AND subject = ? AND code = ?",
                                       (obsId, subject, behavior))
                        rows = [{"occurence": float2decimal(r["occurence"])} for r in cursor.fetchall()]

                        if STATE in self.eventType(behavior).upper() and len(rows) % 2:  # unpaired events
                            flagUnpairedEventFound = True
                            continue

                        for idx, row in enumerate(rows):

                            mediaFileIdx = [idx1 for idx1, x in enumerate(duration1)
                                            if row["occurence"] >= sum(duration1[0:idx1])][-1]

                            globalStart = Decimal("0.000") if row["occurence"] < timeOffset else round(
                                                                                       row["occurence"] - timeOffset, 3)
                            start = round(row["occurence"] - timeOffset - float2decimal(sum(duration1[0:mediaFileIdx])), 3)
                            if start < timeOffset:
                                start = Decimal("0.000")

                            if POINT in self.eventType(behavior).upper():

                                globalStop = round(row["occurence"] + timeOffset, 3)

                                stop = round(row["occurence"] + timeOffset - float2decimal(sum(duration1[0:mediaFileIdx])), 3)

                                ffmpeg_command = ('"{ffmpeg_bin}" -i "{input}" -y -ss {start} -to {stop}'
                                                  ' "{dir}{sep}{obsId}_{player}_{subject}_{behavior}_{globalStart}'
                                                  '-{globalStop}{extension}" ').format(
                                                          ffmpeg_bin=ffmpeg_bin,
                                                          input=self.pj[OBSERVATIONS][obsId][FILE][nplayer][mediaFileIdx],
                                                          start=start,
                                                          stop=stop,
                                                          globalStart=globalStart,
                                                          globalStop=globalStop,
                                                          dir=exportDir,
                                                          sep=os.sep,
                                                          obsId=obsId,
                                                          player="PLAYER{}".format(nplayer),
                                                          subject=subject,
                                                          behavior=behavior,
                                                          extension=".mp4")

                                logging.debug("ffmpeg command: {}".format(ffmpeg_command))
                                p = subprocess.Popen(ffmpeg_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                                     shell=True)
                                out, error = p.communicate()

                            if STATE in self.eventType(behavior).upper():
                                if idx % 2 == 0:

                                    globalStop = round(rows[idx + 1]["occurence"] + timeOffset, 3)

                                    stop = round(rows[idx + 1]["occurence"] + timeOffset -
                                                 float2decimal(sum(duration1[0:mediaFileIdx])), 3)

                                    # check if start after length of media
                                    if start > self.pj[OBSERVATIONS][obsId]["media_info"]["length"][self.pj[OBSERVATIONS]
                                                                                                           [obsId][FILE]
                                                                                                           [nplayer]
                                                                                                           [mediaFileIdx]]:
                                        continue

                                    ffmpeg_command = ('"{ffmpeg_bin}" -i "{input}" -y -ss {start} -to {stop} '
                                                      '"{dir}{sep}{obsId}_{player}_{subject}_{behavior}_{globalStart}'
                                                      '-{globalStop}{extension}" ').format(
                                                      ffmpeg_bin=ffmpeg_bin,
                                                      input=self.pj[OBSERVATIONS][obsId][FILE][nplayer][mediaFileIdx],
                                                      start=start,
                                                      stop=stop,
                                                      globalStart=globalStart,
                                                      globalStop=globalStop,
                                                      dir=exportDir,
                                                      sep=os.sep,
                                                      obsId=obsId,
                                                      player="PLAYER{}".format(nplayer),
                                                      subject=subject,
                                                      behavior=behavior,
                                                      extension=".mp4")

                                    logging.debug("ffmpeg command: {}".format(ffmpeg_command))
                                    p = subprocess.Popen(ffmpeg_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                                         shell=True)
                                    out, error = p.communicate()


    def generate_spectrogram(self):
        """
        generate spectrogram of all media files loaded in player #1
        """

        # check temp dir for images from ffmpeg
        tmp_dir = self.ffmpeg_cache_dir if self.ffmpeg_cache_dir else tempfile.gettempdir()

        w = recode_widget.Info_widget()
        w.lwi.setVisible(False)
        w.resize(350, 100)
        w.setWindowFlags(Qt.WindowStaysOnTopHint)
        w.setWindowTitle(programName)
        w.label.setText("Generating spectrogram. Please wait...")

        for media in self.pj[OBSERVATIONS][self.observationId][FILE][PLAYER1]:
            if os.path.isfile(media):
                process = plot_spectrogram.create_spectrogram_multiprocessing(mediaFile=media,
                                                                              tmp_dir=tmp_dir,
                                                                              chunk_size=self.chunk_length,
                                                                              ffmpeg_bin=self.ffmpeg_bin,
                                                                              spectrogramHeight=self.spectrogramHeight,
                                                                              spectrogram_color_map=self.spectrogram_color_map)

                if process:
                    w.show()
                    while True:
                        app.processEvents()
                        if not process.is_alive():
                            w.hide()
                            break

            else:
                QMessageBox.warning(self, programName, "<b>{}</b> file not found".format(media))


    def show_spectrogram(self):
        """
        show spectrogram window if any
        """

        if self.playerType == LIVE:
            QMessageBox.warning(self, programName, "The spectrogram visualization is not available for live observations")
            return

        if self.playerType == VIEWER:
            QMessageBox.warning(self, programName, "The spectrogram visualization is not available in <b>VIEW</b> mode")
            return

        if hasattr(self, "spectro"):
            self.spectro.show()
        else:
            logging.debug("spectro show not OK")

            # remember if player paused
            if self.playerType == VLC and self.playMode == VLC:
                flagPaused = self.mediaListPlayer.get_state() == vlc.State.Paused

            self.pause_video()

            if dialog.MessageDialog(programName, ("You choose to visualize the spectrogram during this observation.<br>"
                                                  "Choose YES to generate the spectrogram.\n\n"
                                                  "Spectrogram generation can take some time for long media, be patient"),
                                    [YES, NO]) == YES:

                self.generate_spectrogram()

                if not self.ffmpeg_cache_dir:
                    tmp_dir = tempfile.gettempdir()
                else:
                    tmp_dir = self.ffmpeg_cache_dir

                currentMediaTmpPath = tmp_dir + os.sep + os.path.basename(url2path(self.mediaplayer.get_media().get_mrl()))

                logging.debug("currentMediaTmpPath {}".format(currentMediaTmpPath))

                self.pj[OBSERVATIONS][self.observationId]["visualize_spectrogram"] = True

                self.spectro = plot_spectrogram.Spectrogram("{}.wav.0-{}.{}.{}.spectrogram.png".format(currentMediaTmpPath,
                                                                                                       self.chunk_length,
                                                                                                       self.spectrogram_color_map,
                                                                                                       self.spectrogramHeight))

                # connect signal from spectrogram class to testsignal function to receive keypress events
                self.spectro.setWindowFlags(Qt.WindowStaysOnTopHint)
                self.spectro.sendEvent.connect(self.signal_from_widget)
                self.spectro.show()
                self.timer_spectro.start()

            if self.playerType == VLC and self.playMode == VLC and not flagPaused:
                self.play_video()


    def timer_spectro_out(self):
        """
        timer for spectrogram visualization
        """

        if not hasattr(self, "spectro"):
            return

        if ("visualize_spectrogram" not in self.pj[OBSERVATIONS][self.observationId] or
                not self.pj[OBSERVATIONS][self.observationId]["visualize_spectrogram"]):
            return

        if self.playerType == LIVE:
            QMessageBox.warning(self, programName, "The spectrogram visualization is not available for live observations")
            return

        if self.playerType == VLC:
            if self.playMode == VLC:
                currentMediaTime = self.mediaplayer.get_time()

            if self.playMode == FFMPEG:
                # get time in current media
                currentMedia, frameCurrentMedia = self.getCurrentMediaByFrame(PLAYER1, self.FFmpegGlobalFrame,
                                                                              list(self.fps.values())[0])
                currentMediaTime = frameCurrentMedia / list(self.fps.values())[0] * 1000

        currentChunk = int(currentMediaTime / 1000 / self.chunk_length)

        if currentChunk != self.spectro.memChunk:
            try:
                self.spectro.scene.removeItem(self.spectro.item)
            except:
                pass

            if not self.ffmpeg_cache_dir:
                tmp_dir = tempfile.gettempdir()
            else:
                tmp_dir = self.ffmpeg_cache_dir

            currentMediaTmpPath = tmp_dir + os.sep + os.path.basename(url2path(self.mediaplayer.get_media().get_mrl()))

            currentChunkFileName = "{}.wav.{}-{}.{}.{}.spectrogram.png".format(currentMediaTmpPath,
                                                                               currentChunk * self.chunk_length,
                                                                               (currentChunk + 1) * self.chunk_length,
                                                                               self.spectrogram_color_map,
                                                                               self.spectrogramHeight
                                                                               )

            if not os.path.isfile(currentChunkFileName):
                self.timer_spectro.stop()

                if dialog.MessageDialog(programName, ("Spectrogram file not found.<br>"
                                                      "Do you want to generate it now?<br>"
                                                      "Spectrogram generation can take some time for long media,"
                                                      "be patient"), [YES, NO]) == YES:

                    self.generate_spectrogram()
                    self.timer_spectro.start()

                return

            logging.debug("current chunk file name: {}".format(currentChunkFileName))
            self.spectro.pixmap.load(currentChunkFileName)

            self.spectro.setWindowTitle("Spectrogram - {}".format(
                                                  os.path.basename(url2path(self.mediaplayer.get_media().get_mrl()))))

            self.spectro.w, self.spectro.h = self.spectro.pixmap.width(), self.spectro.pixmap.height()

            self.spectro.item = QGraphicsPixmapItem(self.spectro.pixmap)

            self.spectro.scene.addItem(self.spectro.item)
            self.spectro.item.setPos(self.spectro.scene.width() // 2, 0)

        get_time = (currentMediaTime % (self.chunk_length * 1000) / (self.chunk_length*1000))

        self.spectro.item.setPos(self.spectro.scene.width() // 2 - int(get_time * self.spectro.w), 0)

        self.spectro.memChunk = currentChunk


    def show_data_files(self):
        """
        show plot of data files (if any)
        """
        for idx in self.plot_data:
            self.plot_data[idx].show()


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
                                                     "with the same name (<b>{}</b>)").format(behav_coding_map["name"]),
                                 QMessageBox.Ok | QMessageBox.Default,
                                 QMessageBox.NoButton)
            return
        
        self.pj["behaviors_coding_map"].append(behav_coding_map)
        QMessageBox.information(self, programName, "The behaviors coding map <b>{}</b> was added to current project".format(behav_coding_map["name"]))
        self.projectChanged = True


    def behaviors_coding_map_creator(self):
        """
        show behaviors coding map creator window and hide program main window
        """

        if not self.project:
            QMessageBox.warning(self, programName, "No project found",
                                QMessageBox.Ok | QMessageBox.Default,
                                QMessageBox.NoButton)
            return
        
        codes_list = []
        for key in self.pj[ETHOGRAM]:
            codes_list.append(self.pj[ETHOGRAM][key]["code"])
        
        self.mapCreatorWindow = behav_coding_map_creator.BehaviorsMapCreatorWindow(codes_list)
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
                        "view"  to start observation
        """

        if obsId in self.pj[OBSERVATIONS]:

            self.observationId = obsId
            self.loadEventsInTW(self.observationId)

            if self.pj[OBSERVATIONS][self.observationId][TYPE] == LIVE:
                self.playerType = LIVE
                self.initialize_new_live_observation()

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
            self.dwObservations.setWindowTitle("Events for “{}” observation".format(self.observationId))
            return ""

        else:
            return "Error: Observation not found"


    def open_observation(self, mode):
        """
        start an observation
        
        Args:
            mode (str): "start" to start observation
                        "view" to start observation
        """

        # check if current observation must be closed to open a new one
        if self.observationId:
            response = dialog.MessageDialog(programName,
                                            "The current observation will be closed. Do you want to continue?",
                                            [YES, NO])
            if response == NO:
                return ""
            else:
                self.close_observation()

        result, selectedObs = self.selectObservations(OPEN)

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
            if dialog.MessageDialog(programName,
                                    "The current observation will be closed. Do you want to continue?",
                                    [YES, NO]) == NO:
                return
            else:
                self.close_observation()

        result, selectedObs = self.selectObservations(EDIT)

        if selectedObs:
            self.new_observation(mode=EDIT, obsId=selectedObs[0])


    def check_state_events(self, mode="all"):
        """
        check state events for each subject
        use check_state_events_obs function
        
        Args:
            mode (str): current: check current observation / all: ask user to select observations
        """

        tot_out = ""
        if mode == "current":
            if self.observationId:
                r, msg = project_functions.check_state_events_obs(self.observationId, self.pj[ETHOGRAM],
                                                                  self.pj[OBSERVATIONS][self.observationId], self.timeFormat)
                
                tot_out = "Observation: <strong>{}</strong><br>{}<br><br>".format(self.observationId, msg)

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

                tot_out += "<strong>{}</strong><br>{}<br>".format(obsId, msg)

        self.results = dialog.ResultsWidget()
        self.results.setWindowTitle("Check state events")
        self.results.ptText.clear()
        self.results.ptText.setReadOnly(True)
        self.results.ptText.appendHtml(tot_out)
        self.results.show()


    def observations_list(self):
        """
        view all observations
        """
        # check if an observation is running
        if self.observationId:
            QMessageBox.critical(self, programName, "You must close the running observation before.")
            return

        result, selectedObs = self.selectObservations(SINGLE)

        if selectedObs:
            if result == OPEN:
                self.observationId = selectedObs[0]
                self.loadEventsInTW(self.observationId)

                if self.pj[OBSERVATIONS][self.observationId][TYPE] == LIVE:
                    self.playerType = LIVE
                    self.initialize_new_live_observation()

                if self.pj[OBSERVATIONS][self.observationId][TYPE] in [MEDIA]:

                    if not self.initialize_new_observation_vlc():
                        self.observationId = ''
                        self.twEvents.setRowCount(0)
                        self.menu_options()

                self.menu_options()
                # title of dock widget
                self.dwObservations.setWindowTitle("Events for “{}” observation".format(self.observationId))

            if result == EDIT:
                if self.observationId != selectedObs[0]:
                    self.new_observation(mode=EDIT, obsId=selectedObs[0])   # observation id to edit
                else:
                    QMessageBox.warning(self, programName,
                                        ("The observation <b>{}</b> is running!<br>"
                                         "Close it before editing.").format(self.observationId))


    def actionCheckUpdate_activated(self, flagMsgOnlyIfNew=False):
        """
        check BORIS web site for updates
        """
        try:
            versionURL = "http://www.boris.unito.it/static/ver4.dat"
            lastVersion = urllib.request.urlopen(versionURL).read().strip().decode("utf-8")
            if versiontuple(lastVersion) > versiontuple(__version__):
                msg = ("""A new version is available: v. <b>{}</b><br>"""
                       """Go to <a href="http://www.boris.unito.it">"""
                       """http://www.boris.unito.it</a> to install it.""").format(lastVersion)
            else:
                msg = "The version you are using is the last one: <b>{}</b>".format(__version__)
            newsURL = "http://www.boris.unito.it/static/news.dat"
            news = urllib.request.urlopen(newsURL).read().strip().decode("utf-8")
            self.saveConfigFile(lastCheckForNewVersion=int(time.mktime(time.localtime())))
            QMessageBox.information(self, programName, msg)
            if news:
                QMessageBox.information(self, programName, news)
        except:
            QMessageBox.warning(self, programName, "Can not check for updates...")


    def jump_to(self):
        """
        jump to the user specified media position
        """

        jt = dialog.JumpTo(self.timeFormat)

        if jt.exec_():
            if self.timeFormat == HHMMSS:
                newTime = int(time2seconds(jt.te.time().toString(HHMMSSZZZ)) * 1000)
            else:
                newTime = int(jt.te.value() * 1000)

            if self.playerType == VLC:
                if self.playMode == FFMPEG:
                    frameDuration = Decimal(1000 / list(self.fps.values())[0])
                    currentFrame = round(newTime / frameDuration)
                    self.FFmpegGlobalFrame = currentFrame

                    if self.second_player():
                        currentFrame2 = round(newTime / frameDuration)
                        self.FFmpegGlobalFrame2 = currentFrame2

                    if self.FFmpegGlobalFrame > 0:
                        self.FFmpegGlobalFrame -= 1
                        if self.second_player() and self.FFmpegGlobalFrame2 > 0:
                            self.FFmpegGlobalFrame2 -= 1
                    self.ffmpegTimerOut()

                else:  # play mode VLC

                    if self.media_list.count() == 1:

                        if newTime < self.mediaplayer.get_length():
                            self.mediaplayer.set_time(newTime)
                            if self.simultaneousMedia:
                                self.mediaplayer2.set_time(int(self.mediaplayer.get_time() -
                                                           self.pj[OBSERVATIONS][self.observationId]
                                                                  [TIME_OFFSET_SECOND_PLAYER] * 1000))

                        else:
                            QMessageBox.warning(self, programName, "The indicated position is behind the end of media ({})".
                                                                   format(seconds2time(self.mediaplayer.get_length()/1000)))

                    elif self.media_list.count() > 1:

                        if newTime < sum(self.duration):

                            # remember if player paused (go previous will start playing)
                            flagPaused = self.mediaListPlayer.get_state() == vlc.State.Paused

                            tot = 0
                            for idx, d in enumerate(self.duration):
                                if newTime >= tot and newTime < tot + d:
                                    self.mediaListPlayer.play_item_at_index(idx)

                                    # wait until media is played
                                    while True:
                                        if self.mediaListPlayer.get_state() in [vlc.State.Playing, vlc.State.Ended]:
                                            break

                                    if flagPaused:
                                        self.mediaListPlayer.pause()

                                    self.mediaplayer.set_time(newTime -
                                                              sum(self.duration[0: self.media_list.index_of_item(
                                                                                     self.mediaplayer.get_media())]))

                                    break
                                tot += d
                        else:
                            QMessageBox.warning(self, programName,
                                                "The indicated position is behind the total media duration ({})".format(
                                                      seconds2time(sum(self.duration)/1000)))

                    self.timer_out()
                    self.timer_spectro_out()
                    #self.timer_plot_data_out()


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
                    if self.FFmpegGlobalFrame < self.duration[idx + 1]:
                        self.FFmpegGlobalFrame = self.duration[idx - 1]
                        break
                self.FFmpegGlobalFrame -= 1
                self.ffmpegTimerOut()

            else:

                # check if media not first media
                if self.media_list.index_of_item(self.mediaplayer.get_media()) > 0:

                    # remember if player paused (go previous will start playing)
                    flagPaused = self.mediaListPlayer.get_state() == vlc.State.Paused
                    self.mediaListPlayer.previous()

                    while True:
                        if self.mediaListPlayer.get_state() in [vlc.State.Playing, vlc.State.Ended]:
                            break

                    if flagPaused:
                        self.mediaListPlayer.pause()
                else:

                    if self.media_list.count() == 1:
                        self.statusbar.showMessage("There is only one media file", 5000)
                    else:
                        if self.media_list.index_of_item(self.mediaplayer.get_media()) == 0:
                            self.statusbar.showMessage("The first media is playing", 5000)

                self.timer_out()
                self.timer_spectro_out()
                #self.timer_plot_data_out()

                # no subtitles
                # self.mediaplayer.video_set_spu(0)

            if hasattr(self, "spectro"):
                self.spectro.memChunk = -1


    def next_media_file(self):
        """
        go to next media file (if any)
        """
        if len(self.pj[OBSERVATIONS][self.observationId][FILE][PLAYER1]) == 1:
            return

        if self.playerType == VLC:

            if self.playMode == FFMPEG:
                for idx, media in enumerate(self.pj[OBSERVATIONS][self.observationId][FILE][PLAYER1]):
                    if self.FFmpegGlobalFrame < self.duration[idx + 1]:
                        self.FFmpegGlobalFrame = self.duration[idx + 1]
                        break
                self.FFmpegGlobalFrame -= 1
                self.ffmpegTimerOut()

            else:

                # check if media not last media
                if self.media_list.index_of_item(self.mediaplayer.get_media()) < self.media_list.count() - 1:

                    # remember if player paused (go previous will start playing)
                    flagPaused = self.mediaListPlayer.get_state() == vlc.State.Paused

                    next(self.mediaListPlayer)

                    # wait until media is played
                    while True:
                        if self.mediaListPlayer.get_state() in [vlc.State.Playing, vlc.State.Ended]:
                            break

                    if flagPaused:
                        logging.info("media player state: {0}".format(self.mediaListPlayer.get_state()))
                        self.mediaListPlayer.pause()

                else:
                    if self.media_list.count() == 1:
                        self.statusbar.showMessage("There is only one media file", 5000)
                    else:
                        if self.media_list.index_of_item(self.mediaplayer.get_media()) == self.media_list.count() - 1:
                            self.statusbar.showMessage("The last media is playing", 5000)

                self.timer_out()
                self.timer_spectro_out()
                #self.timer_plot_data_out()
                # no subtitles
                # self.mediaplayer.video_set_spu(0)

            if hasattr(self, "spectro"):
                self.spectro.memChunk = -1


    def setVolume(self):
        """
        set volume for player #1
        """

        self.mediaplayer.audio_set_volume(self.volumeslider.value())


    def setVolume2(self):
        """
        set volume for player #2
        """

        self.mediaplayer2.audio_set_volume(self.volumeslider2.value())


    def automatic_backup(self):
        """
        save project every x minutes if current observation
        """

        if self.observationId:
            logging.info("automatic backup")
            self.save_project_activated()


    def update_subject(self, subject):
        """
        update the current subject
        """
        if not subject or (self.currentSubject == subject):
            self.currentSubject = ""
            self.lbSubject.setText("<b>{}</b>".format(NO_FOCAL_SUBJECT))
            self.lbFocalSubject.setText(NO_FOCAL_SUBJECT)
        else:
            self.currentSubject = subject
            self.lbSubject.setText("Subject: <b>{}</b>".format(self.currentSubject))
            self.lbFocalSubject.setText(" Focal subject: <b>{}</b>".format(self.currentSubject))


    def preferences(self):
        """
        show preferences window
        """

        preferencesWindow = preferences.Preferences()
        preferencesWindow.tabWidget.setCurrentIndex(0)

        if self.timeFormat == S:
            preferencesWindow.cbTimeFormat.setCurrentIndex(0)

        if self.timeFormat == HHMMSS:
            preferencesWindow.cbTimeFormat.setCurrentIndex(1)

        preferencesWindow.sbffSpeed.setValue(self.fast)
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

        # embed player
        if sys.platform == "darwin":
            self.embedPlayer = False
            preferencesWindow.cbEmbedPlayer.setEnabled(False)

        preferencesWindow.cbEmbedPlayer.setChecked(self.embedPlayer)
        # alert no focal subject
        preferencesWindow.cbAlertNoFocalSubject.setChecked(self.alertNoFocalSubject)
        # tracking cursor above event
        preferencesWindow.cbTrackingCursorAboveEvent.setChecked(self.trackingCursorAboveEvent)
        # check for new version
        preferencesWindow.cbCheckForNewVersion.setChecked(self.checkForNewVersion)
        
        # pause before add event
        preferencesWindow.cb_pause_before_addevent.setChecked(self.pause_before_addevent)

        # FFmpeg for frame by frame mode
        preferencesWindow.lbFFmpegPath.setText("FFmpeg path: {}".format(self.ffmpeg_bin))
        preferencesWindow.leFFmpegCacheDir.setText(self.ffmpeg_cache_dir)
        preferencesWindow.sbFFmpegCacheDirMaxSize.setValue(self.ffmpeg_cache_dir_max_size)

        # frame-by-frame mode
        preferencesWindow.sbFrameResize.setValue(self.frame_resize)
        mem_frame_resize = self.frame_resize

        preferencesWindow.cbFrameBitmapFormat.clear()
        preferencesWindow.cbFrameBitmapFormat.addItems(FRAME_BITMAP_FORMAT_LIST)

        try:
            preferencesWindow.cbFrameBitmapFormat.setCurrentIndex(FRAME_BITMAP_FORMAT_LIST.index(self.frame_bitmap_format))
        except:
            preferencesWindow.cbFrameBitmapFormat.setCurrentIndex(FRAME_BITMAP_FORMAT_LIST.index(FRAME_DEFAULT_BITMAT_FORMAT))

        preferencesWindow.cbDetachFrameViewer.setChecked(self.detachFrameViewer)

        # spectrogram
        preferencesWindow.sbSpectrogramHeight.setValue(self.spectrogramHeight)
        preferencesWindow.cbSpectrogramColorMap.clear()
        preferencesWindow.cbSpectrogramColorMap.addItems(SPECTROGRAM_COLOR_MAPS)
        try:
            preferencesWindow.cbSpectrogramColorMap.setCurrentIndex(SPECTROGRAM_COLOR_MAPS.index(self.spectrogram_color_map))
        except:
            preferencesWindow.cbSpectrogramColorMap.setCurrentIndex(SPECTROGRAM_COLOR_MAPS.index(SPECTROGRAM_DEFAULT_COLOR_MAP))

        # plot colors
        if not self.plot_colors:
            self.plot_colors = BEHAVIORS_PLOT_COLORS
        preferencesWindow.te_plot_colors.setPlainText("\n".join(self.plot_colors))

        if preferencesWindow.exec_():

            if preferencesWindow.cbTimeFormat.currentIndex() == 0:
                self.timeFormat = S

            if preferencesWindow.cbTimeFormat.currentIndex() == 1:
                self.timeFormat = HHMMSS

            self.fast = preferencesWindow.sbffSpeed.value()

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

            self.embedPlayer = preferencesWindow.cbEmbedPlayer.isChecked()

            self.alertNoFocalSubject = preferencesWindow.cbAlertNoFocalSubject.isChecked()

            self.trackingCursorAboveEvent = preferencesWindow.cbTrackingCursorAboveEvent.isChecked()

            self.checkForNewVersion = preferencesWindow.cbCheckForNewVersion.isChecked()

            self.pause_before_addevent = preferencesWindow.cb_pause_before_addevent.isChecked()

            if self.observationId:
                self.loadEventsInTW(self.observationId)
                self.display_timeoffset_statubar(self.pj[OBSERVATIONS][self.observationId][TIME_OFFSET])

            self.ffmpeg_cache_dir = preferencesWindow.leFFmpegCacheDir.text()
            self.ffmpeg_cache_dir_max_size = preferencesWindow.sbFFmpegCacheDirMaxSize.value()

            # frame-by-frame
            self.frame_resize = preferencesWindow.sbFrameResize.value()

            # delete files in imageDirectory f frame_resize changed
            if self.frame_resize != mem_frame_resize:
                # check temp dir for images from ffmpeg
                if not self.ffmpeg_cache_dir:
                    self.imageDirectory = tempfile.gettempdir()
                else:
                    self.imageDirectory = self.ffmpeg_cache_dir

                for f in [x for x in os.listdir(self.imageDirectory)
                          if "BORIS@" in x and os.path.isfile(self.imageDirectory + os.sep + x)]:
                    try:
                        os.remove(self.imageDirectory + os.sep + f)
                    except:
                        pass

            self.frame_bitmap_format = preferencesWindow.cbFrameBitmapFormat.currentText()

            # detach frame viewer
            self.detachFrameViewer = preferencesWindow.cbDetachFrameViewer.isChecked()

            # spectrogram
            self.spectrogram_color_map = preferencesWindow.cbSpectrogramColorMap.currentText()
            self.spectrogramHeight = preferencesWindow.sbSpectrogramHeight.value()

            if self.playMode == FFMPEG:

                if self.detachFrameViewer:
                    if hasattr(self, "measurement_w") and self.measurement_w is not None and self.measurement_w.isVisible():
                        QMessageBox.warning(self, programName, "The frame viewer can not be detached when geometric measurements are active")
                        self.detachFrameViewer = False
                    else:
                        if hasattr(self, "lbFFmpeg"):
                            self.lbFFmpeg.clear()
                        if self.observationId and self.playerType == VLC and self.playMode == FFMPEG:
                            self.create_frame_viewer()
                            self.FFmpegGlobalFrame -= 1
                            self.ffmpegTimerOut()
                else: # attach frame viewer
                    if hasattr(self, "frame_viewer1"):
                        self.frame_viewer1_mem_geometry = self.frame_viewer1.geometry()
                        del self.frame_viewer1
                    self.FFmpegGlobalFrame -= 1

                    if self.second_player():
                        if hasattr(self, "frame_viewer2"):
                            self.frame_viewer2_mem_geometry = self.frame_viewer2.geometry()
                            del self.frame_viewer2
                        self.FFmpegGlobalFrame2 -= 1

                    self.ffmpegTimerOut()

            # plot colors
            self.plot_colors = preferencesWindow.te_plot_colors.toPlainText().split()

            self.menu_options()

            self.saveConfigFile()


    def getCurrentMediaByFrame(self, player, requiredFrame, fps):
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
            if requiredFrame * frameMs < sum(self.duration[0:idx + 1]):
                currentMedia = media
                frameCurrentMedia = requiredFrame - sum(self.duration[0:idx]) / frameMs
                break
        return currentMedia, round(frameCurrentMedia)


    def getCurrentMediaByTime(self, player, obsId, globalTime):
        """
        get:
        player
        globalTime

        returns:
        currentMedia
        frameCurrentMedia
        """
        currentMedia, currentMediaTime = '', 0
        globalTimeMs = globalTime * 1000

        for idx, media in enumerate(self.pj[OBSERVATIONS][obsId][FILE][player]):
            if globalTimeMs < sum(self.duration[0:idx + 1]):
                currentMedia = media
                currentMediaTime = globalTimeMs - sum(self.duration[0:idx])
                break

        return currentMedia, round(currentMediaTime/1000, 3)


    def second_player(self):
        """

        Returns:
            bool: True if second player else False
        """
        if not self.observationId:
            return False
        if (PLAYER2 in self.pj[OBSERVATIONS][self.observationId][FILE] and
                self.pj[OBSERVATIONS][self.observationId][FILE][PLAYER2]):
            return True
        else:
            return False


    def create_frame_viewer(self):
        """
        create frame viewer
        if 2nd player 2nd frame viewer is created
        """
        if not hasattr(self, "frame_viewer1"):
            self.frame_viewer1 = dialog.FrameViewer()
            self.frame_viewer1.setWindowTitle("Frame viewer #1")
            self.frame_viewer1.setWindowFlags(Qt.WindowStaysOnTopHint)
            if self.frame_viewer1_mem_geometry:
                self.frame_viewer1.setGeometry(self.frame_viewer1_mem_geometry)
            else:
                self.frame_viewer1.setGeometry(100, 100, 256, 256)

        if self.second_player():
            if not hasattr(self, "frame_viewer2"):
                self.frame_viewer2 = dialog.FrameViewer()
                self.frame_viewer2.setWindowTitle("Frame viewer #2")
                self.frame_viewer2.setWindowFlags(Qt.WindowStaysOnTopHint)
                if self.frame_viewer2_mem_geometry:
                    self.frame_viewer2.setGeometry(self.frame_viewer2_mem_geometry)
                else:
                    self.frame_viewer2.setGeometry(150, 150, 256, 256)


    def ffmpegTimerOut(self):
        """
        triggered when frame-by-frame mode is activated:
        read next frame and update image
        """

        logging.debug("FFmpegTimerOut function")

        fps = list(self.fps.values())[0]

        logging.debug("fps {}".format(fps))

        frameMs = 1000 / fps

        logging.debug("framMs {}".format(frameMs))

        requiredFrame = self.FFmpegGlobalFrame + 1

        logging.debug("required frame 1: {}".format(requiredFrame))
        logging.debug("sum self.duration1 {}".format(sum(self.duration)))

        # check if end of last media
        if requiredFrame * frameMs >= sum(self.duration):
            logging.debug("end of last media 1 frame: {}".format(requiredFrame))
            return

        currentMedia, frameCurrentMedia = self.getCurrentMediaByFrame(PLAYER1, requiredFrame, fps)

        current_media_full_path = project_functions.media_full_path(currentMedia, self.projectFileName)

        logging.debug("current media 1: {}".format(currentMedia))
        logging.debug("frame current media 1: {}".format(frameCurrentMedia))

        # plot spectro
        self.timer_spectro_out()

        # plot external data files

        md5FileName = hashlib.md5(currentMedia.encode("utf-8")).hexdigest()

        if "BORIS@{md5FileName}-{second}".format(md5FileName=md5FileName,
                                                 second=int((frameCurrentMedia -1)/ fps)) not in self.imagesList:

            extract_frames(self.ffmpeg_bin,
                           int((frameCurrentMedia -1) / fps),
                           current_media_full_path,
                           str(round(fps) + 1),
                           self.imageDirectory,
                           md5FileName,
                           self.frame_bitmap_format.lower(),
                           self.frame_resize)

            self.imagesList.update([f.replace(self.imageDirectory + os.sep, "").split("_")[0]
                                    for f in glob.glob(self.imageDirectory + os.sep + "BORIS@*")])

        logging.debug("images 1 list: {}".format(self.imagesList))

        second1 = int((frameCurrentMedia - 1) / fps)
        frame1 = round((frameCurrentMedia - int((frameCurrentMedia - 1) / fps) * fps))
        if frame1 == 0:
            frame1 += 1
        logging.debug("second1: {}  frame1: {}".format(second1, frame1))

        img = "{imageDir}{sep}BORIS@{fileName}-{second}_{frame}.{extension}".format(imageDir=self.imageDirectory,
                                                                                    sep=os.sep,
                                                                                    fileName=md5FileName,
                                                                                    second=second1,
                                                                                    frame=frame1,
                                                                                    extension=self.frame_bitmap_format.lower())

        logging.debug("image1: {}".format(img))
        if not os.path.isfile(img):
            logging.warning("image 1 not found: {} {} {}".format(img, frameCurrentMedia, int(frameCurrentMedia / fps)))
            extract_frames(self.ffmpeg_bin,
                           int(frameCurrentMedia / fps),
                           current_media_full_path,
                           str(round(fps) + 1),
                           self.imageDirectory,
                           md5FileName,
                           self.frame_bitmap_format.lower(),
                           self.frame_resize)
            if not os.path.isfile(img):
                logging.warning("image 1 still not found: {0}".format(img))
                return

        self.pixmap = QPixmap(img)
        # check if jpg filter available if not use png
        if self.pixmap.isNull():
            self.frame_bitmap_format = "PNG"

        if self.second_player():

            requiredFrame2 = self.FFmpegGlobalFrame2 + 1

            if TIME_OFFSET_SECOND_PLAYER in self.pj[OBSERVATIONS][self.observationId]:

                # sync 2nd player on 1st player when no offset
                if self.pj[OBSERVATIONS][self.observationId][TIME_OFFSET_SECOND_PLAYER] == 0:
                    self.FFmpegGlobalFrame2 = self.FFmpegGlobalFrame
                    requiredFrame2 = requiredFrame

                if self.pj[OBSERVATIONS][self.observationId][TIME_OFFSET_SECOND_PLAYER] > 0:

                    if requiredFrame < self.pj[OBSERVATIONS][self.observationId][TIME_OFFSET_SECOND_PLAYER] * fps:
                        requiredFrame2 = 1
                    else:
                        requiredFrame2 = int(requiredFrame -
                                             self.pj[OBSERVATIONS][self.observationId][TIME_OFFSET_SECOND_PLAYER] * fps)

                if self.pj[OBSERVATIONS][self.observationId][TIME_OFFSET_SECOND_PLAYER] < 0:

                    if requiredFrame2 < abs(self.pj[OBSERVATIONS][self.observationId][TIME_OFFSET_SECOND_PLAYER] * fps):
                        requiredFrame = 1
                    else:
                        requiredFrame = int(requiredFrame2 +
                                            self.pj[OBSERVATIONS][self.observationId][TIME_OFFSET_SECOND_PLAYER] * fps)

            currentMedia2, frameCurrentMedia2 = self.getCurrentMediaByFrame(PLAYER2, requiredFrame2, fps)
            current_media_full_path2 = project_functions.media_full_path(currentMedia2, self.projectFileName)
            
            md5FileName2 = hashlib.md5(currentMedia2.encode("utf-8")).hexdigest()
            if "BORIS@{md5FileName}-{second}".format(md5FileName=md5FileName2,
                                                     second=int(frameCurrentMedia2 / fps)) not in self.imagesList:
                extract_frames(self.ffmpeg_bin, int(frameCurrentMedia2 / fps), current_media_full_path2, str(round(fps) + 1),
                               self.imageDirectory, md5FileName2, self.frame_bitmap_format.lower(), self.frame_resize)

                self.imagesList.update([f.replace(self.imageDirectory + os.sep, "").split("_")[0] for f in
                                        glob.glob(self.imageDirectory + os.sep + "BORIS@*")])

            second2 = int((frameCurrentMedia2 - 1) / fps)
            frame2 = round((frameCurrentMedia2 - int((frameCurrentMedia2 - 1) / fps) * fps))
            if frame2 == 0:
                frame2 += 1

            img2 = "{imageDir}{sep}BORIS@{fileName}-{second}_{frame}.{extension}".format(imageDir=self.imageDirectory,
                                                                                         sep=os.sep,
                                                                                         fileName=md5FileName2,
                                                                                         second=second2,
                                                                                         frame=frame2,
                                                                                         extension=self.frame_bitmap_format.lower())
            if not os.path.isfile(img2):
                logging.warning("image 2 not found: {0}".format(img2))
                extract_frames(self.ffmpeg_bin,
                               int(frameCurrentMedia2 / fps),
                               current_media_full_path2,
                               str(round(fps) + 1),
                               self.imageDirectory,
                               md5FileName2,
                               self.frame_bitmap_format.lower(),
                               self.frame_resize)
                if not os.path.isfile(img2):
                    logging.warning("image 2 still not found: {0}".format(img2))
                    return
            self.pixmap2 = QPixmap(img2)

        if self.detachFrameViewer or self.second_player():   # frame viewer detached or 2 players
            self.create_frame_viewer()

            self.frame_viewer1.show()
            if self.second_player():
                self.frame_viewer2.show()

            self.frame_viewer1.lbFrame.setPixmap(self.pixmap.scaled(self.frame_viewer1.lbFrame.size(), Qt.KeepAspectRatio))
            if self.second_player():
                self.frame_viewer2.lbFrame.setPixmap(self.pixmap2.scaled(self.frame_viewer2.lbFrame.size(), Qt.KeepAspectRatio))

        elif not self.detachFrameViewer:
            self.lbFFmpeg.setPixmap(self.pixmap.scaled(self.lbFFmpeg.size(), Qt.KeepAspectRatio))

        # redraw measurements from previous frames

        if hasattr(self, "measurement_w") and self.measurement_w is not None and self.measurement_w.isVisible():
            if self.measurement_w.cbPersistentMeasurements.isChecked():
                for frame in self.measurement_w.draw_mem:

                    if frame == self.FFmpegGlobalFrame + 1:
                        elementsColor = "lime"
                    else:
                        elementsColor = "red"

                    for element in self.measurement_w.draw_mem[frame]:
                        if element[0] == "line":
                            x1, y1, x2, y2 = element[1:]
                            self.draw_line(x1, y1, x2, y2, elementsColor)
                            self.draw_point(x1, y1, elementsColor)
                            self.draw_point(x2, y2, elementsColor)
                        if element[0] == "angle":
                            x1, y1 = element[1][0]
                            x2, y2 = element[1][1]
                            x3, y3 = element[1][2]
                            self.draw_line(x1, y1, x2, y2, elementsColor)
                            self.draw_line(x1, y1, x3, y3, elementsColor)
                            self.draw_point(x1, y1, elementsColor)
                            self.draw_point(x2, y2, elementsColor)
                            self.draw_point(x3, y3, elementsColor)
                        if element[0] == "polygon":
                            polygon = QPolygon()
                            for point in element[1]:
                                polygon.append(QPoint(point[0], point[1]))
                            painter = QPainter()
                            painter.begin(self.lbFFmpeg.pixmap())
                            painter.setPen(QColor(elementsColor))
                            painter.drawPolygon(polygon)
                            painter.end()
                            self.lbFFmpeg.update()
            else:
                self.measurement_w.draw_mem = []

        self.FFmpegGlobalFrame = requiredFrame
        if self.second_player():
            self.FFmpegGlobalFrame2 = requiredFrame2

        currentTime = self.getLaps() * 1000

        time_str = "{currentMediaName}: <b>{currentTime} / {totalTime}</b> frame: <b>{currentFrame}</b>".format(
                             currentMediaName=os.path.basename(currentMedia),
                             currentTime=self.convertTime(currentTime / 1000),
                             totalTime=self.convertTime(Decimal(self.mediaplayer.get_length() / 1000)),
                             currentFrame=round(self.FFmpegGlobalFrame)
                             )
        self.lbTime.setText(time_str)
        self.lb_current_media_time.setText(time_str)

        # extract State events
        StateBehaviorsCodes = [self.pj[ETHOGRAM][x]["code"] for x in [y for y in self.pj[ETHOGRAM]
                               if "State" in self.pj[ETHOGRAM][y][TYPE]]]

        self.currentStates = {}

        # add states for no focal subject
        self.currentStates[""] = []
        for sbc in StateBehaviorsCodes:
            if len([x[pj_obs_fields["code"]] for x in self.pj[OBSERVATIONS][self.observationId][EVENTS]
                    if x[pj_obs_fields["subject"]] == "" and
                    x[pj_obs_fields["code"]] == sbc and
                    x[pj_obs_fields["time"]] <= currentTime / 1000]) % 2:  # test if odd
                self.currentStates[""].append(sbc)

        # add states for all configured subjects
        for idx in self.pj[SUBJECTS]:

            # add subject index
            self.currentStates[idx] = []
            for sbc in StateBehaviorsCodes:
                if len([x[pj_obs_fields["code"]] for x in self.pj[OBSERVATIONS][self.observationId][EVENTS]
                        if x[pj_obs_fields["subject"]] == self.pj[SUBJECTS][idx]["name"] and
                        x[pj_obs_fields["code"]] == sbc and
                        x[pj_obs_fields["time"]] <= currentTime / 1000]) % 2:  # test if odd
                    self.currentStates[idx].append(sbc)

        # show current states
        if self.currentSubject:
            # get index of focal subject (by name)
            idx = [idx for idx in self.pj[SUBJECTS] if self.pj[SUBJECTS][idx]["name"] == self.currentSubject][0]
            self.lbCurrentStates.setText("%s" % (", ".join(self.currentStates[idx])))
        else:
            self.lbCurrentStates.setText("%s" % (", ".join(self.currentStates[""])))

        # show selected subjects
        self.show_current_states_in_subjects_table()
        '''
        for idx in sorted_keys(self.pj[SUBJECTS]):
            self.twSubjects.item(int(idx), len(subjectsFields)).setText(",".join(self.currentStates[idx]))
        '''

        # show tracking cursor
        self.get_events_current_row()


    def close_measurement_widget(self):
        self.measurement_w.close()


    def clear_measurements(self):
        if self.FFmpegGlobalFrame > 1:
            self.FFmpegGlobalFrame -= 1
            self.ffmpegTimerOut()


    def distance(self):
        """
        active the geometric measurement window
        """
        
        if self.detachFrameViewer:
            QMessageBox.warning(self, programName, ("The geometric measurement is only available when the frames viewer is not detached\n"
                                                    "See Preferences > Frame-by-frame mode > Detach frame viewer") )
            return

        self.measurement_w = measurement_widget.wgMeasurement(logging.getLogger().getEffectiveLevel())
        self.measurement_w.draw_mem = {}
        self.measurement_w.setWindowFlags(Qt.WindowStaysOnTopHint)
        self.measurement_w.closeSignal.connect(self.close_measurement_widget)
        self.measurement_w.clearSignal.connect(self.clear_measurements)

        self.measurement_w.show()

    def draw_point(self, x, y, color):
        """
        draw point on frame-by-frame image
        """
        RADIUS = 6
        painter = QPainter()
        painter.begin(self.lbFFmpeg.pixmap())
        painter.setPen(QColor(color))
        painter.drawEllipse(QPoint(x, y), RADIUS, RADIUS)
        # cross inside circle
        painter.drawLine(x - RADIUS, y, x + RADIUS, y)
        painter.drawLine(x, y - RADIUS, x, y + RADIUS)
        painter.end()
        self.lbFFmpeg.update()


    def draw_line(self, x1, y1, x2, y2, color):
        """
        draw line on frame-by-frame image
        """
        painter = QPainter()
        painter.begin(self.lbFFmpeg.pixmap())
        painter.setPen(QColor(color))
        painter.drawLine(x1, y1, x2, y2)
        painter.end()
        self.lbFFmpeg.update()


    def getPoslbFFmpeg(self, event):
        """
        return click position on frame and distance between 2 last clicks
        """
        #if self.measurement_w:

        if hasattr(self, "measurement_w") and self.measurement_w is not None and self.measurement_w.isVisible():
            x = event.pos().x()
            y = event.pos().y()

            # distance
            if self.measurement_w.rbDistance.isChecked():
                if event.button() == 1:   # left
                    self.draw_point(x, y, "lime")
                    self.memx, self.memy = x, y

                if event.button() == 2 and self.memx != -1 and self.memy != -1:
                    self.draw_point(x, y, "lime")
                    self.draw_line(self.memx, self.memy, x, y, "lime")

                    if self.FFmpegGlobalFrame in self.measurement_w.draw_mem:
                        self.measurement_w.draw_mem[self.FFmpegGlobalFrame].append(["line", self.memx, self.memy, x, y])
                    else:
                        self.measurement_w.draw_mem[self.FFmpegGlobalFrame] = [["line", self.memx, self.memy, x, y]]

                    d = ((x - self.memx) ** 2 + (y - self.memy) ** 2) ** 0.5
                    try:
                        d = d / float(self.measurement_w.lePx.text()) * float(self.measurement_w.leRef.text())
                    except:
                        QMessageBox.critical(self, programName,
                                             "Check reference and pixel values! Values must be numeric.",
                                             QMessageBox.Ok | QMessageBox.Default, QMessageBox.NoButton)

                    self.measurement_w.pte.appendPlainText("Time: {}\tFrame: {}\tDistance: {}".format(self.getLaps(),
                                                                                                      self.FFmpegGlobalFrame,
                                                                                                      round(d, 1)))
                    self.measurement_w.flagSaved = False
                    self.memx, self.memy = -1, -1

            # angle 1st clic -> vertex
            if self.measurement_w.rbAngle.isChecked():
                if event.button() == 1:   # left for vertex
                    self.draw_point(x, y, "lime")
                    self.memPoints = [(x, y)]

                if event.button() == 2 and len(self.memPoints):
                    self.draw_point(x, y, "lime")
                    self.draw_line(self.memPoints[0][0], self.memPoints[0][1], x, y, "lime")

                    self.memPoints.append((x, y))

                    if len(self.memPoints) == 3:
                        self.measurement_w.pte.appendPlainText("Time: {}\tFrame: {}\tAngle: {}".format(self.getLaps(),
                                                                                                       self.FFmpegGlobalFrame,
                                                                                                       round(angle(self.memPoints[0],
                                                                                                                   self.memPoints[1],
                                                                                                                   self.memPoints[2]),
                                                                                                             1)
                                                                                                       ))
                        self.measurement_w.flagSaved = False
                        if self.FFmpegGlobalFrame in self.measurement_w.draw_mem:
                            self.measurement_w.draw_mem[self.FFmpegGlobalFrame].append(["angle", self.memPoints])
                        else:
                            self.measurement_w.draw_mem[self.FFmpegGlobalFrame] = [["angle", self.memPoints]]

                        self.memPoints = []

            # Area
            if self.measurement_w.rbArea.isChecked():
                if event.button() == 1:   # left
                    self.draw_point(x, y, "lime")
                    if len(self.memPoints):
                        self.draw_line(self.memPoints[-1][0], self.memPoints[-1][1], x, y, "lime")
                    self.memPoints.append((x, y))

                if event.button() == 2 and len(self.memPoints) >= 2:
                    self.draw_point(x, y, "lime")
                    self.draw_line(self.memPoints[-1][0], self.memPoints[-1][1], x, y, "lime")
                    self.memPoints.append((x, y))
                    # close polygon
                    self.draw_line(self.memPoints[-1][0], self.memPoints[-1][1], self.memPoints[0][0], self.memPoints[0][1], "lime")
                    a = polygon_area(self.memPoints)

                    if self.FFmpegGlobalFrame in self.measurement_w.draw_mem:
                        self.measurement_w.draw_mem[self.FFmpegGlobalFrame].append(["polygon", self.memPoints])
                    else:
                        self.measurement_w.draw_mem[self.FFmpegGlobalFrame] = [["polygon", self.memPoints]]
                    try:
                        a = a / (float(self.measurement_w.lePx.text())**2) * float(self.measurement_w.leRef.text())**2
                    except:
                        QMessageBox.critical(self, programName,
                                             "Check reference and pixel values! Values must be numeric.",
                                             QMessageBox.Ok | QMessageBox.Default, QMessageBox.NoButton)

                    self.measurement_w.pte.appendPlainText("Time: {}\tFrame: {}\tArea: {}".format(self.getLaps(),
                                                                                                  self.FFmpegGlobalFrame,
                                                                                                  round(a, 1)))

                    self.memPoints = []

    def initialize_video_tab(self):
        # creating a basic vlc instance
        self.instance = vlc.Instance()

        # creating an empty vlc media player
        self.mediaplayer = self.instance.media_player_new()
        self.mediaListPlayer = self.instance.media_list_player_new()
        self.mediaListPlayer.set_media_player(self.mediaplayer)

        self.media_list = self.instance.media_list_new()

        # video will be drawn in this widget
        '''
        if sys.platform == "darwin":  # for MacOS
            self.videoframe = QMacCocoaViewContainer(0)
        else:
            self.videoframe = QFrame()
        '''

        self.videoframe = QFrame()

        self.palette = self.videoframe.palette()
        self.palette.setColor(QPalette.Window, QColor(0, 0, 0))
        self.videoframe.setPalette(self.palette)
        self.videoframe.setAutoFillBackground(True)

        self.volumeslider = QSlider(QtCore.Qt.Vertical, self)
        self.volumeslider.setMaximum(100)
        self.volumeslider.setValue(self.mediaplayer.audio_get_volume())
        self.volumeslider.setToolTip("Volume")
        self.volumeslider.sliderMoved.connect(self.setVolume)

        self.hsVideo = QSlider(QtCore.Qt.Horizontal, self)
        self.hsVideo.setMaximum(slider_maximum)
        self.hsVideo.sliderMoved.connect(self.hsVideo_sliderMoved)

        self.video1layout = QHBoxLayout()
        self.video1layout.addWidget(self.videoframe)
        self.video1layout.addWidget(self.volumeslider)

        self.vboxlayout = QVBoxLayout()

        self.vboxlayout.addLayout(self.video1layout)

        self.vboxlayout.addWidget(self.hsVideo)
        self.hsVideo.setVisible(True)

        self.videoTab = QWidget()

        self.videoTab.setLayout(self.vboxlayout)

        self.toolBox.insertItem(VIDEO_TAB, self.videoTab, "Audio/Video")

        self.actionFrame_by_frame.setEnabled(False)

        self.ffmpegLayout = QHBoxLayout()
        self.lbFFmpeg = QLabel(self)
        self.lbFFmpeg.setAlignment(Qt.AlignLeft | Qt.AlignTop)
        self.lbFFmpeg.setBackgroundRole(QPalette.Base)
        self.lbFFmpeg.mousePressEvent = self.getPoslbFFmpeg

        self.ffmpegLayout.addWidget(self.lbFFmpeg)

        self.ffmpegTab = QWidget()
        self.ffmpegTab.setLayout(self.ffmpegLayout)

        self.toolBox.insertItem(FRAME_TAB, self.ffmpegTab, "Frame by frame")
        self.toolBox.setItemEnabled(FRAME_TAB, False)

        self.actionFrame_by_frame.setEnabled(True)

    def initialize_2nd_video_tab(self):
        """
        initialize second video player (use only if first player initialized)
        """
        self.mediaplayer2 = self.instance.media_player_new()

        self.media_list2 = self.instance.media_list_new()

        self.mediaListPlayer2 = self.instance.media_list_player_new()
        self.mediaListPlayer2.set_media_player(self.mediaplayer2)

        app.processEvents()

        '''
        if sys.platform == "darwin":  # for MacOS
            self.videoframe2 = QMacCocoaViewContainer(0)
        else:
            self.videoframe2 = QFrame()
        '''

        self.videoframe2 = QFrame()
        
        self.palette2 = self.videoframe2.palette()
        self.palette2.setColor(QPalette.Window, QColor(0, 0, 0))
        self.videoframe2.setPalette(self.palette2)
        self.videoframe2.setAutoFillBackground(True)

        self.volumeslider2 = QSlider(QtCore.Qt.Vertical, self)
        self.volumeslider2.setMaximum(100)
        self.volumeslider2.setValue(self.mediaplayer2.audio_get_volume())
        self.volumeslider2.setToolTip("Volume")

        self.volumeslider2.sliderMoved.connect(self.setVolume2)

        self.video2layout = QHBoxLayout()
        self.video2layout.addWidget(self.videoframe2)
        self.video2layout.addWidget(self.volumeslider2)

        self.vboxlayout.insertLayout(1, self.video2layout)


    def check_if_media_in_project_directory(self):

        try:
            for player in ALL_PLAYERS:
                for mediaFile in self.pj[OBSERVATIONS][self.observationId][FILE][player]:
                    if not os.path.isfile(os.path.dirname(self.projectFileName) + os.sep + os.path.basename(mediaFile)):
                        return False
        except:
            return False
        return True

        

    def initialize_new_observation_vlc(self):
        """
        initialize new observation for VLC
        """

        logging.debug("initialize new observation for VLC")

        useMediaFromProjectDirectory = NO

        #if not self.check_if_media_available():
        ok, msg = project_functions.check_if_media_available(self.pj[OBSERVATIONS][self.observationId],
                                                          self.projectFileName)
        if not ok:

            '''
            if self.check_if_media_in_project_directory():

                useMediaFromProjectDirectory = dialog.MessageDialog(programName, ("Media file was/were not found in its/their original path(s) "
                                                                                  "but in project directory.<br> "
                                                                                  "Do you want to convert media file paths?"), [YES, NO])

                if useMediaFromProjectDirectory == NO:
                    QMessageBox.warning(self, programName, ("The observation will be opened in VIEW mode.<br>"
                                                            "It will not be possible to log events.<br>"
                                                            "Modify the media path to point an existing media file "
                                                            "to log events or copy media file in the BORIS project "
                                                            "directory."),
                                        QMessageBox.Ok | QMessageBox.Default, QMessageBox.NoButton)

                    self.playerType = VIEWER
                    self.playMode = ""
                    self.dwObservations.setVisible(True)
                    return True

            else:
            '''
            QMessageBox.critical(self, programName, msg + ("<br><br>The observation will be opened in VIEW mode.<br>"
                                                         "It will not be possible to log events.<br>"
                                                         "Modify the media path to point an existing media file "
                                                         "to log events or copy media file in the BORIS project directory."),
                                 QMessageBox.Ok | QMessageBox.Default,
                                 QMessageBox.NoButton)

            self.playerType = VIEWER
            self.playMode = ""
            self.dwObservations.setVisible(True)
            return True

        # check if media list player 1 contains more than 1 media
        if (len(self.pj[OBSERVATIONS][self.observationId][FILE][PLAYER1]) > 1 and
                PLAYER2 in self.pj[OBSERVATIONS][self.observationId][FILE] and
                self.pj[OBSERVATIONS][self.observationId][FILE][PLAYER2]):
            QMessageBox.warning(self, programName, ("It is not yet possible to play a second media when more media"
                                                    "are loaded in the first media player"))
            return False

        self.playerType, self.playMode = VLC, VLC
        self.fps = {}
        self.toolBar.setEnabled(False)
        self.dwObservations.setVisible(True)
        self.toolBox.setVisible(True)
        self.lb_current_media_time.setVisible(True)
        self.lbFocalSubject.setVisible(True)
        self.lbCurrentStates.setVisible(True)

        # init duration of media file and FPS
        self.duration.clear()
        self.duration2.clear()
        self.fps.clear()
        self.fps2.clear()

        # add all media files to media list
        self.simultaneousMedia = False

        '''
        if useMediaFromProjectDirectory == YES:
            for idx, mediaFile in enumerate(self.pj[OBSERVATIONS][self.observationId][FILE][PLAYER1]):
                self.pj[OBSERVATIONS][self.observationId][FILE][PLAYER1][idx] = (os.path.dirname(self.projectFileName) +
                                                                                 os.sep +
                                                                                 os.path.basename(mediaFile))
                self.projectChanged = True
        '''

        for mediaFile in self.pj[OBSERVATIONS][self.observationId][FILE][PLAYER1]:
            logging.debug("media file: {}".format(mediaFile))
            try:
                self.instance
            except AttributeError:
                self.initialize_video_tab()

            media_full_path = project_functions.media_full_path(mediaFile, self.projectFileName)
            media = self.instance.media_new(media_full_path)
            media.parse()

            # media duration
            try:
                mediaLength = self.pj[OBSERVATIONS][self.observationId]["media_info"]["length"][mediaFile] * 1000
                mediaFPS = self.pj[OBSERVATIONS][self.observationId]["media_info"]["fps"][mediaFile]
            except:
                logging.debug("media_info key not found")
                nframe, videoTime, videoDuration, fps, hasVideo, hasAudio = accurate_media_analysis(self.ffmpeg_bin, media_full_path)
                if "media_info" not in self.pj[OBSERVATIONS][self.observationId]:
                    self.pj[OBSERVATIONS][self.observationId]["media_info"] = {"length": {}, "fps": {}}
                    if "length" not in self.pj[OBSERVATIONS][self.observationId]["media_info"]:
                        self.pj[OBSERVATIONS][self.observationId]["media_info"]["length"] = {}
                    if "fps" not in self.pj[OBSERVATIONS][self.observationId]["media_info"]:
                        self.pj[OBSERVATIONS][self.observationId]["media_info"]["fps"] = {}

                self.pj[OBSERVATIONS][self.observationId]["media_info"]["length"][mediaFile] = videoDuration
                self.pj[OBSERVATIONS][self.observationId]["media_info"]["fps"][mediaFile] = fps

                mediaLength = videoDuration * 1000
                mediaFPS = fps

                self.projectChanged = True

            self.duration.append(int(mediaLength))
            self.fps[mediaFile] = mediaFPS
            self.media_list.add_media(media)

        # add media list to media player list
        self.mediaListPlayer.set_media_list(self.media_list)

        # display media player in videoframe
        if self.embedPlayer:

            if sys.platform.startswith("linux"):  # for Linux using the X Server
                self.mediaplayer.set_xwindow(self.videoframe.winId())

            elif sys.platform.startswith("win"):  # for Windows
                self.mediaplayer.set_hwnd(int(self.videoframe.winId()))

        # for mac always embed player
        if sys.platform == "darwin":  # for MacOS
            self.mediaplayer.set_nsobject(int(self.videoframe.winId()))


        # check if fps changes between media
        """
        TODO: check
        if FFMPEG in self.availablePlayers:
            if len(set( self.fps.values())) != 1:
                QMessageBox.critical(self, programName, ("The frame-by-frame mode will not be available because the "
                "video files have different frame rates (%s).") % (", ".join([str(i) for i in list(self.fps.values())])),\
                 QMessageBox.Ok | QMessageBox.Default, QMessageBox.NoButton)
        """

        # show first frame of video
        logging.debug("playing media #{0}".format(0))

        self.mediaListPlayer.play_item_at_index(0)

        # play mediaListPlayer for a while to obtain media information
        while True:
            if self.mediaListPlayer.get_state() in [vlc.State.Playing, vlc.State.Ended]:
                break

        self.mediaListPlayer.pause()
        while True:
            if self.mediaListPlayer.get_state() in [vlc.State.Paused, vlc.State.Ended]:
                break
        self.mediaplayer.set_time(0)

        # no subtitles
        # self.mediaplayer.video_set_spu(0)

        self.FFmpegTimer = QTimer(self)
        self.FFmpegTimer.timeout.connect(self.ffmpegTimerOut)
        try:
            self.FFmpegTimerTick = int(1000 / list(self.fps.values())[0])
        except:
            # default value 40 ms (25 frames / s)
            self.FFmpegTimerTick = 40

        self.FFmpegTimer.setInterval(self.FFmpegTimerTick)

        # check for second media to be played together
        if PLAYER2 in self.pj[OBSERVATIONS][self.observationId][FILE] and self.pj[OBSERVATIONS][self.observationId][FILE][PLAYER2]:

                if useMediaFromProjectDirectory == YES:
                    for idx, mediaFile in enumerate(self.pj[OBSERVATIONS][self.observationId][FILE][PLAYER2]):
                        self.pj[OBSERVATIONS][self.observationId][FILE][PLAYER2][idx] = (os.path.dirname(self.projectFileName) +
                                                                                         os.sep +
                                                                                         os.path.basename(mediaFile))
                        self.projectChanged = True

                # create 2nd mediaplayer
                self.simultaneousMedia = True
                self.initialize_2nd_video_tab()

                # add media file
                for mediaFile in self.pj[OBSERVATIONS][self.observationId][FILE][PLAYER2]:

                    media_full_path = project_functions.media_full_path(mediaFile, self.projectFileName)
                    media = self.instance.media_new(media_full_path)
                    media.parse()

                    # media duration
                    try:
                        mediaLength = self.pj[OBSERVATIONS][self.observationId]["media_info"]["length"][mediaFile] * 1000
                        mediaFPS = self.pj[OBSERVATIONS][self.observationId]["media_info"]["fps"][mediaFile]
                    except:
                        logging.debug("media_info key not found")
                        nframe, videoTime, videoDuration, fps, hasVideo, hasAudio = accurate_media_analysis(self.ffmpeg_bin, media_full_path)
                        if "media_info" not in self.pj[OBSERVATIONS][self.observationId]:
                            self.pj[OBSERVATIONS][self.observationId]["media_info"] = {"length": {}, "fps": {}}
                            if "length" not in self.pj[OBSERVATIONS][self.observationId]["media_info"]:
                                self.pj[OBSERVATIONS][self.observationId]["media_info"]["length"] = {}
                            if "fps" not in self.pj[OBSERVATIONS][self.observationId]["media_info"]:
                                self.pj[OBSERVATIONS][self.observationId]["media_info"]["fps"] = {}

                        self.pj[OBSERVATIONS][self.observationId]["media_info"]["length"][mediaFile] = videoDuration
                        self.pj[OBSERVATIONS][self.observationId]["media_info"]["fps"][mediaFile] = fps

                        mediaLength = videoDuration * 1000
                        mediaFPS = fps
                        self.projectChanged = True

                    self.duration2.append(int(mediaLength))
                    self.fps2[mediaFile] = mediaFPS

                    self.media_list2.add_media(media)

                self.mediaListPlayer2.set_media_list(self.media_list2)

                if self.embedPlayer:
                    if sys.platform.startswith("linux"):  # for Linux using the X Server
                        self.mediaplayer2.set_xwindow(self.videoframe2.winId())

                    elif sys.platform.startswith("win32"):  # for Windows
                        self.mediaplayer2.set_hwnd(int(self.videoframe2.winId()))

                # for mac always embed player
                if sys.platform == "darwin":  # for MacOS
                    self.mediaplayer2.set_nsobject(int(self.videoframe2.winId()))

                # show first frame of video
                app.processEvents()

                self.mediaListPlayer2.play()
                app.processEvents()

                while True:
                    if self.mediaListPlayer2.get_state() in [vlc.State.Playing, vlc.State.Ended]:
                        break

                self.mediaListPlayer2.pause()
                app.processEvents()

                self.mediaplayer2.set_time(0)
                '''
                if TIME_OFFSET_SECOND_PLAYER in self.pj[OBSERVATIONS][self.observationId] \
                    and self.pj[OBSERVATIONS][self.observationId][TIME_OFFSET_SECOND_PLAYER]:
                    if self.pj[OBSERVATIONS][self.observationId][TIME_OFFSET_SECOND_PLAYER] > 0:
                        self.mediaplayer2.set_time( int( self.pj[OBSERVATIONS][self.observationId][TIME_OFFSET_SECOND_PLAYER] *1000))
                '''

                # no subtitles
                # self.mediaplayer2.video_set_spu(0)

        self.videoTab.setEnabled(True)

        self.toolBox.setCurrentIndex(VIDEO_TAB)
        self.toolBox.setItemEnabled(VIDEO_TAB, False)

        self.toolBar.setEnabled(True)

        self.display_timeoffset_statubar(self.pj[OBSERVATIONS][self.observationId][TIME_OFFSET])

        self.memMedia, self.currentSubject = "", ""

        self.timer_out()

        self.lbSpeed.setText("x{:.3f}".format(self.play_rate))

        if window.focusWidget():
            window.focusWidget().installEventFilter(self)

        '''
        if app.focusWidget():
            app.focusWidget().installEventFilter(self)
        '''

        # spectrogram
        if ("visualize_spectrogram" in self.pj[OBSERVATIONS][self.observationId] and
                self.pj[OBSERVATIONS][self.observationId]["visualize_spectrogram"]):

            if not self.ffmpeg_cache_dir:
                tmp_dir = tempfile.gettempdir()
            else:
                tmp_dir = self.ffmpeg_cache_dir

            currentMediaTmpPath = tmp_dir + os.sep + os.path.basename(urllib.parse.unquote(url2path(self.mediaplayer.get_media().get_mrl())))

            if not os.path.isfile("{}.wav.0-{}.{}.{}.spectrogram.png".format(currentMediaTmpPath,
                                                                             self.chunk_length,
                                                                             self.spectrogram_color_map,
                                                                             self.spectrogramHeight)):
                if dialog.MessageDialog(programName, ("Spectrogram file not found.\n"
                                                      "Do you want to generate it now?\n"
                                                      "Spectrogram generation can take some time for long media, be patient"),
                                        [YES, NO]) == YES:

                    self.generate_spectrogram()
                else:
                    self.pj[OBSERVATIONS][self.observationId]["visualize_spectrogram"] = False
                    return True

            self.spectro = plot_spectrogram.Spectrogram("{}.wav.0-{}.{}.{}.spectrogram.png".format(currentMediaTmpPath,
                                                                                                   self.chunk_length,
                                                                                                   self.spectrogram_color_map,
                                                                                                   self.spectrogramHeight))
            # connect signal from spectrogram class to testsignal function to receive keypress events
            self.spectro.setWindowFlags(Qt.WindowStaysOnTopHint)
            self.spectro.sendEvent.connect(self.signal_from_widget)
            self.spectro.show()
            self.timer_spectro.start()



        # external data plot
        if PLOT_DATA in self.pj[OBSERVATIONS][self.observationId] and self.pj[OBSERVATIONS][self.observationId][PLOT_DATA]:

            self.plot_data = {}
            self.ext_data_timer_list = []

            count = 0

            for idx in self.pj[OBSERVATIONS][self.observationId][PLOT_DATA]:
                
                if count == 0:
                    
                    w1 = plot_data_module.Plot_data(self.pj[OBSERVATIONS][self.observationId][PLOT_DATA][idx]["file_path"],
                                                                 int(self.pj[OBSERVATIONS][self.observationId][PLOT_DATA][idx]["time_interval"]),
                                                                 int(self.pj[OBSERVATIONS][self.observationId][PLOT_DATA][idx]["time_offset"]),
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
                        QMessageBox.critical(self, programName, "Impossibile to plot data from file {}:\n{}".format(os.path.basename(self.pj[OBSERVATIONS][self.observationId][PLOT_DATA][idx]["file_path"]),
                                                                                                             w1.error_msg))
                        del w1
                        return False

                    w1.setWindowFlags(Qt.WindowStaysOnTopHint)
                    w1.sendEvent.connect(self.signal_from_widget)

                    w1.show()

                    self.ext_data_timer_list.append(QTimer())
                    self.ext_data_timer_list[-1].setInterval(w1.time_out)
                    self.ext_data_timer_list[-1].timeout.connect(lambda: self.timer_plot_data_out(w1))
                    self.ext_data_timer_list[-1].start()
                    
                    self.plot_data[count] = w1

                
                if count == 1:
                    w2 = plot_data_module.Plot_data(self.pj[OBSERVATIONS][self.observationId][PLOT_DATA][idx]["file_path"],
                                                                 int(self.pj[OBSERVATIONS][self.observationId][PLOT_DATA][idx]["time_interval"]),
                                                                 int(self.pj[OBSERVATIONS][self.observationId][PLOT_DATA][idx]["time_offset"]),
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
                        QMessageBox.critical(self, programName, "Impossibile to plot data from file {}:\n{}".format(os.path.basename(self.pj[OBSERVATIONS][self.observationId][PLOT_DATA][idx]["file_path"]),
                                                                                                             w2.error_msg))
                        del w2
                        return False

                    w2.setWindowFlags(Qt.WindowStaysOnTopHint)
                    w2.sendEvent.connect(self.signal_from_widget)

                    w2.show()
                    self.ext_data_timer_list.append(QTimer())
                    self.ext_data_timer_list[-1].setInterval(w2.time_out)
                    self.ext_data_timer_list[-1].timeout.connect(lambda: self.timer_plot_data_out(w2))
                    self.ext_data_timer_list[-1].start()
                    
                    self.plot_data[count] = w2


                count += 1

        # check if "filtered behaviors"
        if FILTERED_BEHAVIORS in self.pj[OBSERVATIONS][self.observationId]:
            self.load_behaviors_in_twEthogram(self.pj[OBSERVATIONS][self.observationId][FILTERED_BEHAVIORS])

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


    def eventFilter(self, source, event):
        """
        send event from widget to mainwindow
        """

        if event.type() == QtCore.QEvent.KeyPress:
            key = event.key()
            if key in [Qt.Key_Up, Qt.Key_Down, Qt.Key_Left, Qt.Key_Right, Qt.Key_PageDown, Qt.Key_PageUp]:
                self.keyPressEvent(event)

        return QMainWindow.eventFilter(self, source, event)


    def loadEventsInTW(self, obsId):
        """
        load events in table widget and update START/STOP
        """

        self.twEvents.setRowCount(len(self.pj[OBSERVATIONS][obsId][EVENTS]))
        row = 0

        for event in self.pj[OBSERVATIONS][obsId][EVENTS]:

            for field_type in tw_events_fields:

                if field_type in pj_events_fields:

                    field = event[pj_obs_fields[field_type]]
                    if field_type == "time":
                        field = str(self.convertTime(field))

                    twi = QTableWidgetItem(field)
                    self.twEvents.setItem(row, tw_obs_fields[field_type], twi)

                else:
                    self.twEvents.setItem(row, tw_obs_fields[field_type], QTableWidgetItem(""))

            row += 1

        self.update_events_start_stop()


    def selectObservations(self, mode):
        """
        show observations list window
        mode: accepted values: OPEN, EDIT, SINGLE, MULTIPLE, SELECT1
        """
        resultStr, selectedObs = select_observations.select_observations(self.pj, mode)
        
        return resultStr, selectedObs


    def initialize_new_live_observation(self):
        """
        initialize new live observation
        """

        self.playerType = LIVE
        self.playMode = LIVE

        self.create_live_tab()

        self.toolBox.setVisible(True)

        self.dwObservations.setVisible(True)

        self.simultaneousMedia = False

        self.lbFocalSubject.setVisible(True)
        self.lbCurrentStates.setVisible(True)

        self.liveTab.setEnabled(True)
        self.toolBox.setItemEnabled(0, True)   # enable tab
        self.toolBox.setCurrentIndex(0)  # show tab

        self.toolBar.setEnabled(False)

        self.liveObservationStarted = False
        self.textButton.setText("Start live observation")
        if self.timeFormat == HHMMSS:
            self.lbTimeLive.setText("00:00:00.000")
        if self.timeFormat == S:
            self.lbTimeLive.setText("0.000")

        self.liveStartTime = None
        self.liveTimer.stop()


    def new_observation_triggered(self):
        self.new_observation(mode=NEW, obsId="")


    def new_observation(self, mode=NEW, obsId=""):
        """
        define a new observation or edit an existing observation
        """
        # check if current observation must be closed to create a new one
        if mode == NEW and self.observationId:
            if dialog.MessageDialog(programName, "The current observation will be closed. Do you want to continue?", 
                                    [YES, NO]) == NO:
                return
            else:
                self.close_observation()


        observationWindow = observation.Observation(self.ffmpeg_cache_dir if self.ffmpeg_cache_dir else tempfile.gettempdir(),
                                                    converters=self.pj[CONVERTERS] if CONVERTERS in self.pj else {},
                                                    log_level=logging.getLogger().getEffectiveLevel())

        observationWindow.pj = self.pj
        observationWindow.mode = mode
        observationWindow.mem_obs_id = obsId
        observationWindow.chunk_length = self.chunk_length
        observationWindow.ffmpeg_cache_dir = self.ffmpeg_cache_dir
        observationWindow.dteDate.setDateTime(QDateTime.currentDateTime())
        observationWindow.FLAG_MATPLOTLIB_INSTALLED = FLAG_MATPLOTLIB_INSTALLED
        observationWindow.ffmpeg_bin = self.ffmpeg_bin
        observationWindow.spectrogramHeight = self.spectrogramHeight
        observationWindow.spectrogram_color_map = self.spectrogram_color_map

        # add indepvariables
        if INDEPENDENT_VARIABLES in self.pj:

            observationWindow.twIndepVariables.setRowCount(0)
            for i in sorted_keys(self.pj[INDEPENDENT_VARIABLES]):

                observationWindow.twIndepVariables.setRowCount(observationWindow.twIndepVariables.rowCount() + 1)

                # label
                item = QTableWidgetItem()
                indepVarLabel = self.pj[INDEPENDENT_VARIABLES][i]['label']
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
            observationWindow.teTimeOffset.setVisible(False)
            observationWindow.teTimeOffset_2.setVisible(False)

        if self.timeFormat == HHMMSS:
            observationWindow.leTimeOffset.setVisible(False)
            observationWindow.leTimeOffset_2.setVisible(False)

        if mode == EDIT:

            observationWindow.setWindowTitle("""Edit observation "{}" """.format(obsId))
            mem_obs_id = obsId
            observationWindow.leObservationId.setText(obsId)
            observationWindow.dteDate.setDateTime(QDateTime.fromString(self.pj[OBSERVATIONS][obsId]["date"], "yyyy-MM-ddThh:mm:ss"))
            observationWindow.teDescription.setPlainText(self.pj[OBSERVATIONS][obsId]["description"])

            try:
                observationWindow.mediaDurations = self.pj[OBSERVATIONS][obsId]["media_info"]["length"]
                observationWindow.mediaFPS = self.pj[OBSERVATIONS][obsId]["media_info"]["fps"]
            except:
                observationWindow.mediaDurations = {}
                observationWindow.mediaFPS = {}

            try:
                if "hasVideo" in self.pj[OBSERVATIONS][obsId]["media_info"]:
                    observationWindow.mediaHasVideo = self.pj[OBSERVATIONS][obsId]["media_info"]["hasVideo"]
                if "hasAudio" in self.pj[OBSERVATIONS][obsId]["media_info"]:
                    observationWindow.mediaHasAudio = self.pj[OBSERVATIONS][obsId]["media_info"]["hasAudio"]
            except:
                logging.info("No Video/Audio information")

            # offset
            if self.timeFormat == S:

                observationWindow.leTimeOffset.setText(self.convertTime(abs(self.pj[OBSERVATIONS][obsId]["time offset"])))

                if "time offset second player" in self.pj[OBSERVATIONS][obsId]:
                    observationWindow.leTimeOffset_2.setText(self.convertTime(abs(self.pj[OBSERVATIONS][obsId]["time offset second player"])))

                    if self.pj[OBSERVATIONS][obsId]["time offset second player"] <= 0:
                        observationWindow.rbEarlier.setChecked(True)
                    else:
                        observationWindow.rbLater.setChecked(True)

            if self.timeFormat == HHMMSS:
                time = QTime()
                h, m, s_dec = seconds2time(abs(self.pj[OBSERVATIONS][obsId]["time offset"])).split(":")
                s, ms = s_dec.split(".")
                time.setHMS(int(h), int(m), int(s), int(ms))
                observationWindow.teTimeOffset.setTime(time)

                if "time offset second player" in self.pj[OBSERVATIONS][obsId]:
                    time = QTime()
                    h, m, s_dec = seconds2time(abs(self.pj[OBSERVATIONS][obsId]["time offset second player"])).split(':')
                    s, ms = s_dec.split(".")
                    time.setHMS(int(h), int(m), int(s), int(ms))
                    observationWindow.teTimeOffset_2.setTime(time)

                    if self.pj[OBSERVATIONS][obsId]["time offset second player"] <= 0:
                        observationWindow.rbEarlier.setChecked(True)
                    else:
                        observationWindow.rbLater.setChecked(True)

            if self.pj[OBSERVATIONS][obsId]["time offset"] < 0:
                observationWindow.rbSubstract.setChecked(True)
                
            for player, twVideo in zip([PLAYER1, PLAYER2], [observationWindow.twVideo1, observationWindow.twVideo2]):

                if player in self.pj[OBSERVATIONS][obsId][FILE] and self.pj[OBSERVATIONS][obsId][FILE][player]:
                    twVideo.setRowCount(0)
                    for mediaFile in self.pj[OBSERVATIONS][obsId][FILE] and self.pj[OBSERVATIONS][obsId][FILE][player]:
                        twVideo.setRowCount(twVideo.rowCount() + 1)
                        twVideo.setItem(twVideo.rowCount() - 1, 0, QTableWidgetItem(mediaFile))
                        try:
                            twVideo.setItem(twVideo.rowCount() - 1, 1,
                                QTableWidgetItem(seconds2time(self.pj[OBSERVATIONS][obsId]["media_info"]["length"][mediaFile])))
                            twVideo.setItem(twVideo.rowCount() - 1, 2,
                                QTableWidgetItem("{}".format(self.pj[OBSERVATIONS][obsId]["media_info"]["fps"][mediaFile])))
                        except:
                            pass
                        try:
                            twVideo.setItem(twVideo.rowCount() - 1, 3,
                                QTableWidgetItem("{}".format(self.pj[OBSERVATIONS][obsId]["media_info"]["hasVideo"][mediaFile])))
                            twVideo.setItem(twVideo.rowCount() - 1, 4,
                                QTableWidgetItem("{}".format(self.pj[OBSERVATIONS][obsId]["media_info"]["hasAudio"][mediaFile])))
                        except:
                            pass


            if self.pj[OBSERVATIONS][obsId]["type"] in [MEDIA]:
                observationWindow.tabProjectType.setCurrentIndex(video)

            if self.pj[OBSERVATIONS][obsId]["type"] in [LIVE]:
                observationWindow.tabProjectType.setCurrentIndex(live)
                if "scan_sampling_time" in self.pj[OBSERVATIONS][obsId]:
                    observationWindow.sbScanSampling.setValue(self.pj[OBSERVATIONS][obsId]["scan_sampling_time"])


             # spectrogram
            observationWindow.cbVisualizeSpectrogram.setEnabled(True)
            if "visualize_spectrogram" in self.pj[OBSERVATIONS][obsId]:
                observationWindow.cbVisualizeSpectrogram.setChecked(self.pj[OBSERVATIONS][obsId]["visualize_spectrogram"])

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
                                combobox.setCurrentIndex(DATA_PLOT_STYLES.index(self.pj[OBSERVATIONS][obsId][PLOT_DATA][idx2][DATA_PLOT_FIELDS[idx3]]))

                                observationWindow.tw_data_files.setCellWidget(observationWindow.tw_data_files.rowCount() - 1,
                                                                              PLOT_DATA_PLOTCOLOR_IDX, combobox)
                            elif idx3 == PLOT_DATA_SUBSTRACT1STVALUE_IDX:
                                combobox2 = QComboBox()
                                combobox2.addItems(["False","True"])
                                combobox2.setCurrentIndex(["False", "True"].index(self.pj[OBSERVATIONS][obsId][PLOT_DATA][idx2][DATA_PLOT_FIELDS[idx3]]))

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
                                observationWindow.tw_data_files.setItem(observationWindow.tw_data_files.rowCount() - 1, idx3, 
                                                                        QTableWidgetItem(str(self.pj[OBSERVATIONS][obsId][PLOT_DATA][idx2][DATA_PLOT_FIELDS[idx3]])))

                            else:
                                observationWindow.tw_data_files.setItem(observationWindow.tw_data_files.rowCount() - 1, idx3,
                                    QTableWidgetItem(self.pj[OBSERVATIONS][obsId][PLOT_DATA][idx2][DATA_PLOT_FIELDS[idx3]]))


            # cbCloseCurrentBehaviorsBetweenVideo
            observationWindow.cbCloseCurrentBehaviorsBetweenVideo.setEnabled(True)
            if CLOSE_BEHAVIORS_BETWEEN_VIDEOS in self.pj[OBSERVATIONS][obsId]:
                observationWindow.cbCloseCurrentBehaviorsBetweenVideo.setChecked(self.pj[OBSERVATIONS][obsId][CLOSE_BEHAVIORS_BETWEEN_VIDEOS])

        # spectrogram
        #observationWindow.cbVisualizeSpectrogram.setEnabled(FLAG_MATPLOTLIB_INSTALLED)

        rv = observationWindow.exec_()

        if rv:

            self.projectChanged = True

            new_obs_id = observationWindow.leObservationId.text()

            if mode == NEW:
                self.observationId = new_obs_id
                self.pj[OBSERVATIONS][self.observationId] = {FILE: [], TYPE: "",  "date": "", "description": "", "time offset": 0, "events": []}

            # check if id changed
            if mode == EDIT and new_obs_id != obsId:

                logging.info("observation id {} changed in {}".format(obsId, new_obs_id))

                self.pj[OBSERVATIONS][new_obs_id] = self.pj[OBSERVATIONS][obsId]
                del self.pj[OBSERVATIONS][obsId]

            # observation date
            self.pj[OBSERVATIONS][new_obs_id]["date"] = observationWindow.dteDate.dateTime().toString(Qt.ISODate)

            self.pj[OBSERVATIONS][new_obs_id]["description"] = observationWindow.teDescription.toPlainText()

            # observation type: read project type from tab text
            self.pj[OBSERVATIONS][new_obs_id][TYPE] = observationWindow.tabProjectType.tabText(observationWindow.tabProjectType.currentIndex()).upper()

            # independent variables for observation
            self.pj[OBSERVATIONS][new_obs_id][INDEPENDENT_VARIABLES] = {}
            for r in range(observationWindow.twIndepVariables.rowCount()):

                # set dictionary as label (col 0) => value (col 2)
                if observationWindow.twIndepVariables.item(r, 1).text() == SET_OF_VALUES:
                    self.pj[OBSERVATIONS][new_obs_id][INDEPENDENT_VARIABLES][observationWindow.twIndepVariables.item(r, 0).text()] = observationWindow.twIndepVariables.cellWidget(r, 2).currentText()
                elif observationWindow.twIndepVariables.item(r, 1).text() == TIMESTAMP:
                    self.pj[OBSERVATIONS][new_obs_id][INDEPENDENT_VARIABLES][observationWindow.twIndepVariables.item(r, 0).text()] = observationWindow.twIndepVariables.cellWidget(r, 2).dateTime().toString(Qt.ISODate)
                else:
                    self.pj[OBSERVATIONS][new_obs_id][INDEPENDENT_VARIABLES][observationWindow.twIndepVariables.item(r, 0).text()] = observationWindow.twIndepVariables.item(r, 2).text()

            # observation time offset
            if self.timeFormat == HHMMSS:
                self.pj[OBSERVATIONS][new_obs_id][TIME_OFFSET] = time2seconds(observationWindow.teTimeOffset.time().toString(HHMMSSZZZ))
                self.pj[OBSERVATIONS][new_obs_id][TIME_OFFSET_SECOND_PLAYER] = time2seconds(observationWindow.teTimeOffset_2.time().toString(HHMMSSZZZ))

            if self.timeFormat == S:
                self.pj[OBSERVATIONS][new_obs_id][TIME_OFFSET] = abs(Decimal(observationWindow.leTimeOffset.text()))
                self.pj[OBSERVATIONS][new_obs_id][TIME_OFFSET_SECOND_PLAYER] = abs(Decimal(observationWindow.leTimeOffset_2.text()))

            if observationWindow.rbSubstract.isChecked():
                self.pj[OBSERVATIONS][new_obs_id][TIME_OFFSET] = - self.pj[OBSERVATIONS][new_obs_id][TIME_OFFSET]

            if observationWindow.rbEarlier.isChecked():
                self.pj[OBSERVATIONS][new_obs_id][TIME_OFFSET_SECOND_PLAYER] = - self.pj[OBSERVATIONS][new_obs_id][TIME_OFFSET_SECOND_PLAYER]


            self.display_timeoffset_statubar(self.pj[OBSERVATIONS][new_obs_id][TIME_OFFSET])

            # visualize spectrogram
            self.pj[OBSERVATIONS][new_obs_id]["visualize_spectrogram"] = observationWindow.cbVisualizeSpectrogram.isChecked()
            
            # plot data
            if observationWindow.tw_data_files.rowCount():
                self.pj[OBSERVATIONS][new_obs_id][PLOT_DATA] = {}
                for row in range(observationWindow.tw_data_files.rowCount()):
                    self.pj[OBSERVATIONS][new_obs_id][PLOT_DATA][str(row)] = {}
                    for idx2 in DATA_PLOT_FIELDS:
                        if idx2 in [PLOT_DATA_PLOTCOLOR_IDX, PLOT_DATA_SUBSTRACT1STVALUE_IDX]:
                            self.pj[OBSERVATIONS][new_obs_id][PLOT_DATA][str(row)][DATA_PLOT_FIELDS[idx2]] = observationWindow.tw_data_files.cellWidget(row, idx2).currentText()

                        elif idx2 == PLOT_DATA_CONVERTERS_IDX:
                            if observationWindow.tw_data_files.item(row, idx2).text():
                                self.pj[OBSERVATIONS][new_obs_id][PLOT_DATA][str(row)][DATA_PLOT_FIELDS[idx2]] = eval(observationWindow.tw_data_files.item(row, idx2).text())
                            else:
                                self.pj[OBSERVATIONS][new_obs_id][PLOT_DATA][str(row)][DATA_PLOT_FIELDS[idx2]] = {}

                        else:
                            self.pj[OBSERVATIONS][new_obs_id][PLOT_DATA][str(row)][DATA_PLOT_FIELDS[idx2]] = observationWindow.tw_data_files.item(row, idx2).text()


            # cbCloseCurrentBehaviorsBetweenVideo
            self.pj[OBSERVATIONS][new_obs_id][CLOSE_BEHAVIORS_BETWEEN_VIDEOS] = observationWindow.cbCloseCurrentBehaviorsBetweenVideo.isChecked()

            if self.pj[OBSERVATIONS][new_obs_id][TYPE] in [LIVE]:
                self.pj[OBSERVATIONS][new_obs_id]["scan_sampling_time"] = observationWindow.sbScanSampling.value()

            # media file
            fileName = {}

            # media
            if self.pj[OBSERVATIONS][new_obs_id][TYPE] in [MEDIA]:

                fileName[PLAYER1] = []
                if observationWindow.twVideo1.rowCount():

                    for row in range(observationWindow.twVideo1.rowCount()):
                        fileName[PLAYER1].append(observationWindow.twVideo1.item(row, 0).text())

                fileName[PLAYER2] = []

                if observationWindow.twVideo2.rowCount():

                    for row in range(observationWindow.twVideo2.rowCount()):
                        fileName[PLAYER2].append(observationWindow.twVideo2.item(row, 0).text())

                self.pj[OBSERVATIONS][new_obs_id][FILE] = fileName

                self.pj[OBSERVATIONS][new_obs_id]["media_info"] = {"length": observationWindow.mediaDurations,
                                                                  "fps":  observationWindow.mediaFPS}

                try:
                    self.pj[OBSERVATIONS][new_obs_id]["media_info"]["hasVideo"] = observationWindow.mediaHasVideo
                    self.pj[OBSERVATIONS][new_obs_id]["media_info"]["hasAudio"] = observationWindow.mediaHasAudio
                except:
                    logging.info("error with media_info information")


                logging.debug("media_info: {0}".format(self.pj[OBSERVATIONS][new_obs_id]['media_info']))

                '''
                if not 'project_media_file_info' in self.pj:
                    self.pj['project_media_file_info'] = {}


                for h in observationWindow.media_file_info:
                    self.pj['project_media_file_info'][h] = observationWindow.media_file_info[h]
                logging.info('pj: {0}'.format(  self.pj))
                '''

            #if mode == NEW:

            if rv == 1:  # save
                self.observationId = ""
                self.menu_options()

            if rv == 2:  # start
                self.observationId = new_obs_id

                # title of dock widget
                self.dwObservations.setWindowTitle("""Events for "{}" observation""".format(self.observationId))

                if self.pj[OBSERVATIONS][self.observationId][TYPE] in [LIVE]:

                    self.playerType = LIVE
                    self.initialize_new_live_observation()

                else:
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

            for x in self.ext_data_timer_list:
                x.stop()
        except:
            pass

        try:
            for pd in self.plot_data:
                #pd.plot_data_timer.stop()
                self.plot_data[pd].close_plot()
                #pd.hide()

        except:
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
            except:
                pass

        
        if hasattr(self, "codingpad"):
            try:
                self.codingpad.close()
                del self.codingpad
            except:
                pass

        if hasattr(self, "subjects_pad"):
            try:
                self.subjects_pad.close()
                del self.subjects_pad
            except:
                pass

        if hasattr(self, "spectro"):
            try:
                self.spectro.close()
                del self.spectro
            except:
                pass

        if hasattr(self, "frame_viewer1"):
            try:
                self.frame_viewer1.close()
                del self.frame_viewer1
            except:
                pass

        if hasattr(self, "frame_viewer2"):
            try:
                self.frame_viewer2.close()
                del self.frame_viewer2
            except:
                pass

        if hasattr(self, "results"):
            try:
                self.results.close()
                del self.results
            except:
                pass

        if hasattr(self, "mapCreatorWindow"):
            try:
                self.mapCreatorWindow.close()
                del self.mapCreatorWindow
            except:
                pass
            
        for idx in self.bcm_dict:
            self.bcm_dict[idx].close()
            if idx in self.bcm_dict:
                del self.bcm_dict[idx]
            


    def close_observation(self):
        """
        close current observation
        """

        logging.info("Close observation {}".format(self.playerType))

        logging.debug("del self.plot_data")
        
        if PLOT_DATA in self.pj[OBSERVATIONS][self.observationId] and self.pj[OBSERVATIONS][self.observationId][PLOT_DATA]:

            for x in self.ext_data_timer_list:
                x.stop()

            for pd in self.plot_data:
                #pd.plot_data_timer.stop()
                self.plot_data[pd].close_plot()
                #pd.hide()

            del self.plot_data


        self.observationId = ""

        self.close_tool_windows()

        if self.playerType == LIVE:

            self.liveObservationStarted = False
            self.liveStartTime = None
            self.liveTimer.stop()
            self.toolBox.removeItem(0)
            self.liveTab.deleteLater()

        if self.playerType == VLC:

            self.timer.stop()
            self.timer_spectro.stop()

            self.mediaplayer.stop()
            del self.mediaplayer
            del self.mediaListPlayer

            # empty media list
            while self.media_list.count():
                self.media_list.remove_index(0)

            del self.media_list

            while self.video1layout.count():
                item = self.video1layout.takeAt(0)
                item.widget().deleteLater()

            if self.simultaneousMedia:
                self.mediaplayer2.stop()
                while self.media_list2.count():
                    self.media_list2.remove_index(0)
                del self.mediaplayer2

                while self.video2layout.count():
                    item = self.video2layout.takeAt(0)
                    item.widget().deleteLater()

                self.simultaneousMedia = False

                del self.media_list2

            del self.instance

            self.videoTab.deleteLater()
            self.actionFrame_by_frame.setChecked(False)
            self.playMode = VLC

            try:
                self.spectro.close()
                del self.spectro
            except:
                pass

            try:
                self.ffmpegLayout.deleteLater()
                self.lbFFmpeg.deleteLater()
                self.ffmpegTab.deleteLater()
                self.FFmpegTimer.stop()
                self.FFmpegGlobalFrame = 0
                self.imagesList = set()
            except:
                pass


        self.statusbar.showMessage("", 0)

        # delete layout
        self.toolBar.setEnabled(False)
        self.dwObservations.setVisible(False)
        self.toolBox.setVisible(False)
        self.lb_current_media_time.setVisible(False)
        self.lbFocalSubject.setVisible(False)
        self.lbCurrentStates.setVisible(False)

        self.twEvents.setRowCount(0)

        self.lbTime.clear()
        self.lb_current_media_time.clear()
        self.lbSubject.clear()
        self.lbFocalSubject.setText(NO_FOCAL_SUBJECT)

        self.lbTimeOffset.clear()
        self.lbSpeed.clear()

        self.playerType = ""

        self.menu_options()


    def set_recent_projects_menu(self):
        """
        set the recent projects submenu
        """
        self.menuRecent_projects.clear()
        for project_file_path in self.recent_projects:
            action = QAction(self, visible=False, triggered=self.open_project_activated)
            action.setText(project_file_path)
            action.setVisible(True)
            self.menuRecent_projects.addAction(action)


    def readConfigFile(self):
        """
        read config file
        """

        logging.debug("read config file")

        iniFilePath = str(pathlib.Path(os.path.expanduser("~")) / ".boris")

        if os.path.isfile(iniFilePath):
            settings = QSettings(iniFilePath, QSettings.IniFormat)

            size = settings.value("MainWindow/Size")
            if size:
                self.resize(size)
                self.move(settings.value("MainWindow/Position"))

            self.timeFormat = HHMMSS
            try:
                self.timeFormat = settings.value("Time/Format")
            except:
                self.timeFormat = HHMMSS

            self.fast = 10
            try:
                self.fast = int(settings.value("Time/fast_forward_speed"))

            except:
                self.fast = 10

            self.repositioningTimeOffset = 0
            try:
                self.repositioningTimeOffset = int(settings.value("Time/Repositioning_time_offset"))

            except:
                self.repositioningTimeOffset = 0

            self.play_rate_step = 0.1
            try:
                self.play_rate_step = float(settings.value("Time/play_rate_step"))

            except:
                self.play_rate_step = 0.1

            #self.saveMediaFilePath = True

            self.automaticBackup = 0
            try:
                self.automaticBackup  = int(settings.value("Automatic_backup"))
            except:
                self.automaticBackup = 0

            self.behaviouralStringsSeparator = "|"
            try:
                self.behaviouralStringsSeparator = settings.value("behavioural_strings_separator")
                if not self.behaviouralStringsSeparator:
                    self.behaviouralStringsSeparator = "|"
            except:
                self.behaviouralStringsSeparator = "|"

            self.close_the_same_current_event = False
            try:
                self.close_the_same_current_event = (settings.value("close_the_same_current_event") == "true")
            except:
                self.close_the_same_current_event = False

            self.confirmSound = False
            try:
                self.confirmSound = (settings.value("confirm_sound") == "true")
            except:
                self.confirmSound = False

            self.embedPlayer = True
            try:
                self.embedPlayer = (settings.value("embed_player") == "true")
            except:
                self.embedPlayer = True

            if sys.platform == "darwin":
                self.embedPlayer = False

            self.alertNoFocalSubject = False
            try:
                self.alertNoFocalSubject = (settings.value('alert_nosubject') == "true")
            except:
                self.alertNoFocalSubject = False

            try:
                self.beep_every = int(settings.value("beep_every"))
            except:
                self.beep_every = 0

            self.trackingCursorAboveEvent = False
            try:
                self.trackingCursorAboveEvent = (settings.value('tracking_cursor_above_event') == "true")
            except:
                self.trackingCursorAboveEvent = False

            # check for new version
            self.checkForNewVersion = False
            try:
                if settings.value("check_for_new_version") == None:
                    self.checkForNewVersion = (dialog.MessageDialog(programName,
                                                                    ("Allow BORIS to automatically check for new version and news?\n"
                                                                     "(An internet connection is required)\n"
                                                                     "You can change this option in the Preferences (File > Preferences)"),
                                                                    [YES, NO]) == YES)
                else:
                    self.checkForNewVersion = (settings.value("check_for_new_version") == "true")
            except:
                self.checkForNewVersion = False

            # pause before add event
            self.pause_before_addevent = False
            try:
                self.pause_before_addevent = (settings.value("pause_before_addevent") == 'true')
            except:
                self.pause_before_addevent = False

            if self.checkForNewVersion:
                if (settings.value("last_check_for_new_version") and
                 int(time.mktime(time.localtime())) - int(settings.value("last_check_for_new_version")) > CHECK_NEW_VERSION_DELAY):
                    self.actionCheckUpdate_activated(flagMsgOnlyIfNew = True)

            self.ffmpeg_cache_dir = ""
            try:
                self.ffmpeg_cache_dir = settings.value("ffmpeg_cache_dir")
                if not self.ffmpeg_cache_dir:
                    self.ffmpeg_cache_dir = ""
            except:
                self.ffmpeg_cache_dir = ""

            self.ffmpeg_cache_dir_max_size = 0
            try:
                self.ffmpeg_cache_dir_max_size = int(settings.value("ffmpeg_cache_dir_max_size"))
                if not self.ffmpeg_cache_dir_max_size:
                    self.ffmpeg_cache_dir_max_size = 0
            except:
                self.ffmpeg_cache_dir_max_size = 0

            # frame-by-frame
            try:
                self.frame_resize = int(settings.value("frame_resize"))
                if not self.frame_resize:
                    self.frame_resize = 0
            except:
                self.frame_resize = 0

            try:
                self.frame_bitmap_format = settings.value("frame_bitmap_format")
                if not self.frame_bitmap_format:
                    self.frame_bitmap_format = FRAME_DEFAULT_BITMAT_FORMAT
            except:
                self.frame_bitmap_format = FRAME_DEFAULT_BITMAT_FORMAT


            try:
                self.detachFrameViewer = (settings.value("detach_frame_viewer") == "true")
            except:
                self.detachFrameViewer = False

            # spectrogram
            self.spectrogramHeight = 80
            try:
                self.spectrogramHeight = int(settings.value("spectrogram_height"))
                if not self.spectrogramHeight:
                    self.spectrogramHeight = 80
            except:
                self.spectrogramHeight = 80

            try:
                self.spectrogram_color_map = settings.value("spectrogram_color_map")
                if self.spectrogram_color_map is None:
                    self.spectrogram_color_map = SPECTROGRAM_DEFAULT_COLOR_MAP
            except:
                self.spectrogram_color_map = SPECTROGRAM_DEFAULT_COLOR_MAP
            
            # plot colors
            try:
                self.plot_colors = settings.value("plot_colors").split("|")
            except:
                self.plot_colors = BEHAVIORS_PLOT_COLORS

            if ("white" in self.plot_colors 
                or "azure" in self.plot_colors
                or "snow" in self.plot_colors):
                if dialog.MessageDialog(programName, ("The colors list contain colors that are very light.\n"
                                                   "Do you want to reload the default colors list?"),
                                                    [NO, YES]) == YES:
                    self.plot_colors = BEHAVIORS_PLOT_COLORS


        else: # no .boris file found
            # ask user for checking for new version
            self.checkForNewVersion = (dialog.MessageDialog(programName, ("Allow BORIS to automatically check for new version?\n"
                                                                          "(An internet connection is required)\n"
                                                                          "You can change this option in the"
                                                                          " Preferences (File > Preferences)"),
                                                            [NO, YES]) == YES)

        # recent projects
        logging.info("read recent projects")
        iniFilePath = str(pathlib.Path(os.path.expanduser("~")) / ".boris_recent_projects")
        if os.path.isfile(iniFilePath):
            settings = QSettings(iniFilePath, QSettings.IniFormat)
            self.recent_projects = settings.value("recent_projects").split("|||")
            while "" in self.recent_projects:
                self.recent_projects.remove("")
            self.set_recent_projects_menu()
        else:
            self.recent_projects = []



    def saveConfigFile(self, lastCheckForNewVersion=0):
        """
        save config file
        """

        logging.info("save config file")

        iniFilePath = str(pathlib.Path(os.path.expanduser("~")) / ".boris")

        settings = QSettings(iniFilePath, QSettings.IniFormat)
        settings.setValue("MainWindow/Size", self.size())
        settings.setValue("MainWindow/Position", self.pos())
        settings.setValue("Time/Format", self.timeFormat)
        settings.setValue("Time/Repositioning_time_offset", self.repositioningTimeOffset)
        settings.setValue("Time/fast_forward_speed", self.fast)
        settings.setValue("Time/play_rate_step", self.play_rate_step)
        settings.setValue("Save_media_file_path", self.saveMediaFilePath)
        settings.setValue("Automatic_backup", self.automaticBackup)
        settings.setValue("behavioural_strings_separator", self.behaviouralStringsSeparator)
        settings.setValue("close_the_same_current_event", self.close_the_same_current_event)
        settings.setValue("confirm_sound", self.confirmSound)
        settings.setValue("beep_every", self.beep_every)
        settings.setValue("embed_player", self.embedPlayer)
        settings.setValue("alert_nosubject", self.alertNoFocalSubject)
        settings.setValue("tracking_cursor_above_event", self.trackingCursorAboveEvent)
        settings.setValue("check_for_new_version", self.checkForNewVersion)
        settings.setValue("pause_before_addevent", self.pause_before_addevent)
        
        if lastCheckForNewVersion:
            settings.setValue("last_check_for_new_version", lastCheckForNewVersion)

        # FFmpeg
        settings.setValue("ffmpeg_cache_dir", self.ffmpeg_cache_dir)
        settings.setValue("ffmpeg_cache_dir_max_size", self.ffmpeg_cache_dir_max_size)
        # frame-by-frame
        settings.setValue("frame_resize", self.frame_resize)

        settings.setValue("frame_bitmap_format", self.frame_bitmap_format)
        settings.setValue("detach_frame_viewer", self.detachFrameViewer)
        # spectrogram
        settings.setValue("spectrogram_height", self.spectrogramHeight)
        settings.setValue("spectrogram_color_map", self.spectrogram_color_map)
        # plot colors
        settings.setValue("plot_colors", "|".join(self.plot_colors))

        # recent projects
        logging.info("save recent projects")
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



    def display_timeoffset_statubar(self, timeOffset):
        """
        display offset in status bar
        """

        if timeOffset:
            self.lbTimeOffset.setText("Time offset: <b>{}</b>".format(timeOffset if self.timeFormat == S else seconds2time(timeOffset)))
        else:
            self.lbTimeOffset.clear()


    def eventType(self, code):
        """
        returns type of event for code
        """
        for idx in self.pj[ETHOGRAM]:
            if self.pj[ETHOGRAM][idx]['code'] == code:
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
                                       selectedObservations,
                                       maxTime=0,
                                       flagShowIncludeModifiers=True,
                                       flagShowExcludeBehaviorsWoEvents=True,
                                       by_category=False,
                                       show_time=False):

        """
        show window for:
        - selection of subjects
        - selection of behaviors (based on selected subjects)
        - selection of time interval
        - inclusion/exclusion of modifiers
        - inclusion/exclusion of behaviors without events (flagShowExcludeBehaviorsWoEvents == True)

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
        paramPanelWindow.resize(600, 500)
        paramPanelWindow.setWindowTitle("Select subjects and behaviors")
        paramPanelWindow.selectedObservations = selectedObservations
        paramPanelWindow.pj = self.pj
        paramPanelWindow.extract_observed_behaviors = self.extract_observed_behaviors

        if not flagShowIncludeModifiers:
            paramPanelWindow.cbIncludeModifiers.setVisible(False)
        if not flagShowExcludeBehaviorsWoEvents:
            paramPanelWindow.cbExcludeBehaviors.setVisible(False)

        if by_category:
            paramPanelWindow.cbIncludeModifiers.setVisible(False)
            paramPanelWindow.cbExcludeBehaviors.setVisible(False)

        paramPanelWindow.frm_time_interval.setEnabled(False)
        if self.timeFormat == HHMMSS:
            paramPanelWindow.teStartTime.setTime(QtCore.QTime.fromString("00:00:00.000", "hh:mm:ss.zzz"))
            paramPanelWindow.teEndTime.setTime(QtCore.QTime.fromString(seconds2time(maxTime), "hh:mm:ss.zzz"))
            paramPanelWindow.dsbStartTime.setVisible(False)
            paramPanelWindow.dsbEndTime.setVisible(False)

        if self.timeFormat == S:
            paramPanelWindow.dsbStartTime.setValue(0.0)
            paramPanelWindow.dsbEndTime.setValue(maxTime)
            paramPanelWindow.teStartTime.setVisible(False)
            paramPanelWindow.teEndTime.setVisible(False)

        # hide max time
        if not maxTime:
            paramPanelWindow.frm_time.setVisible(False)

        observedSubjects = project_functions.extract_observed_subjects(self.pj, selectedObservations)
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

        all_subjects = [self.pj[SUBJECTS][x]["name"] for x in sorted_keys(self.pj[SUBJECTS])]

        for subject in all_subjects:
            paramPanelWindow.item = QListWidgetItem(paramPanelWindow.lwSubjects)
            paramPanelWindow.ch = QCheckBox()
            paramPanelWindow.ch.setText(subject)
            paramPanelWindow.ch.stateChanged.connect(paramPanelWindow.cb_changed)
            if subject in observedSubjects:
                selectedSubjects.append(subject)
                paramPanelWindow.ch.setChecked(True)

            paramPanelWindow.lwSubjects.setItemWidget(paramPanelWindow.item, paramPanelWindow.ch)

        logging.debug('selectedSubjects: {0}'.format(selectedSubjects))

        observedBehaviors = self.extract_observed_behaviors(selectedObservations, selectedSubjects) # not sorted

        logging.debug('observed behaviors: {0}'.format(observedBehaviors))

        if BEHAVIORAL_CATEGORIES in self.pj:
            categories = self.pj[BEHAVIORAL_CATEGORIES][:]
            # check if behavior not included in a category
            try:
                if "" in [self.pj[ETHOGRAM][idx]["category"] for idx in self.pj[ETHOGRAM] if "category" in self.pj[ETHOGRAM][idx]]:
                    categories += [""]
            except:
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

            for behavior in [self.pj[ETHOGRAM][x]["code"] for x in sorted_keys(self.pj[ETHOGRAM])]:

                if ((categories == ["###no category###"])
                or (behavior in [self.pj[ETHOGRAM][x]["code"] for x in self.pj[ETHOGRAM] if "category" in self.pj[ETHOGRAM][x] and self.pj[ETHOGRAM][x]["category"] == category])):

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


        if not paramPanelWindow.exec_():
            return {"selected subjects": [],
                    "selected behaviors": []}

        selectedSubjects = paramPanelWindow.selectedSubjects
        selectedBehaviors = paramPanelWindow.selectedBehaviors

        logging.debug("selected subjects: {}".format(selectedSubjects))
        logging.debug("selected behaviors: {}".format(selectedBehaviors))

        if self.timeFormat == HHMMSS:
            startTime = time2seconds(paramPanelWindow.teStartTime.time().toString(HHMMSSZZZ))
            endTime = time2seconds(paramPanelWindow.teEndTime.time().toString(HHMMSSZZZ))
        if self.timeFormat == S:
            startTime = Decimal(paramPanelWindow.dsbStartTime.value())
            endTime = Decimal(paramPanelWindow.dsbEndTime.value())
        if startTime > endTime:
            QMessageBox.warning(None, programName, "The start time is after the end time", QMessageBox.Ok | QMessageBox.Default, QMessageBox.NoButton)
            return {"selected subjects": [], "selected behaviors": []}

        if paramPanelWindow.rb_full.isChecked():
            time_param = TIME_FULL_OBS
        if paramPanelWindow.rb_limit.isChecked():
            time_param = TIME_EVENTS
        if paramPanelWindow.rb_interval.isChecked():
            time_param = TIME_ARBITRARY_INTERVAL

        return {"selected subjects": selectedSubjects,
                "selected behaviors": selectedBehaviors,
                "include modifiers": paramPanelWindow.cbIncludeModifiers.isChecked(),
                "exclude behaviors": paramPanelWindow.cbExcludeBehaviors.isChecked(),
                "time": time_param,
                "start time": startTime,
                "end time": endTime
                }


    def time_budget(self, mode):
        """
        time budget (by behavior or category)
        mode must be in ("by_behavior", "by_category", "synthetic")
        """

        def time_budget_analysis(cursor, plot_parameters, by_category=False):
            """
            extract number of occurrences, total duration, mean ...
            if start_time = 0 and end_time = 0 all events are extracted
            """

            categories, out = {}, []
            for subject in plot_parameters["selected subjects"]:
                out_cat, categories[subject] = [], {}

                for behavior in plot_parameters["selected behaviors"]:

                    if plot_parameters["include modifiers"]:

                        cursor.execute("SELECT distinct modifiers FROM events WHERE subject = ? AND code = ?", (subject, behavior))
                        distinct_modifiers = list(cursor.fetchall())

                        if not distinct_modifiers:
                            if not plot_parameters["exclude behaviors"]:

                                if {self.pj[ETHOGRAM][idx]["type"] for idx in self.pj[ETHOGRAM] if self.pj[ETHOGRAM][idx]["code"] == behavior} == {"State event"}:
                                    out.append({"subject": subject,
                                            "behavior": behavior,
                                            "modifiers": "-",
                                            "duration": 0,
                                            "duration_mean": 0,
                                            "duration_stdev": "NA",
                                            "number": "0",
                                            "inter_duration_mean": "NA",
                                            "inter_duration_stdev": "NA"})
                                else: # point 
                                    out.append({"subject": subject,
                                            "behavior": behavior,
                                            "modifiers": "-",
                                            "duration": "NA",
                                            "duration_mean": "NA",
                                            "duration_stdev": "NA",
                                            "number": "0",
                                            "inter_duration_mean": "NA",
                                            "inter_duration_stdev": "NA"})
                            continue

                        if POINT in self.eventType(behavior).upper():
                            for modifier in distinct_modifiers:

                                cursor.execute(("SELECT occurence, observation FROM events "
                                                "WHERE subject = ? "
                                                "AND code = ? "
                                                "AND modifiers = ? "
                                                "ORDER BY observation, occurence"),
                                               (subject, behavior, modifier[0]))

                                '''
                                if not plot_parameters["start time"] and not plot_parameters["end time"]:
                                    cursor.execute("""SELECT occurence, observation FROM events
                                                        WHERE subject = ? 
                                                            AND code = ? 
                                                            AND modifiers = ? 
                                                            ORDER BY observation, occurence""",
                                                   (subject, behavior, modifier[0]))

                                else:
                                    cursor.execute("""SELECT occurence,observation FROM events 
                                                        WHERE subject = ? 
                                                            AND code = ?
                                                            AND modifiers = ?
                                                            AND occurence BETWEEN ? and ? 
                                                            ORDER BY observation, occurence""",
                                                   (subject, behavior, modifier[0], str(plot_parameters["start time"]), str(plot_parameters["end time"])))
                                '''

                                rows = cursor.fetchall()

                                # inter events duration
                                all_event_interdurations = []
                                for idx, row in enumerate(rows):
                                    if idx and row[1] == rows[idx - 1][1]:
                                        all_event_interdurations.append(float(row[0]) - float(rows[idx - 1][0]))

                                out_cat.append({"subject": subject,
                                            "behavior": behavior,
                                            "modifiers": modifier[0],
                                            "duration": "NA",
                                            "duration_mean": "NA",
                                            "duration_stdev": "NA",
                                            "number": len(rows),
                                            "inter_duration_mean": round(statistics.mean(all_event_interdurations), 3) if len(all_event_interdurations) else "NA",
                                            "inter_duration_stdev": round(statistics.stdev(all_event_interdurations), 3) if len(all_event_interdurations) > 1 else "NA"
                                            })


                        if STATE in self.eventType(behavior).upper():
                            for modifier in distinct_modifiers:

                                cursor.execute(("SELECT occurence, observation FROM events "
                                                 "WHERE subject = ? "
                                                 "AND code = ? "
                                                 "AND modifiers = ? "
                                                 "ORDER BY observation, occurence"),
                                               (subject, behavior, modifier[0]))


                                '''
                                if not plot_parameters["start time"] and not plot_parameters["end time"]:
                                    cursor.execute("""SELECT occurence, observation FROM events
                                                        WHERE subject = ? 
                                                            AND code = ? 
                                                            AND modifiers = ? 
                                                            ORDER BY observation, occurence""",
                                                   (subject, behavior, modifier[0]))

                                else:
                                    cursor.execute("""SELECT occurence,observation FROM events 
                                                        WHERE subject = ? 
                                                            AND code = ?
                                                            AND modifiers = ?
                                                            AND occurence BETWEEN ? and ? 
                                                            ORDER BY observation, occurence""",
                                                   (subject, behavior, modifier[0], str(plot_parameters["start time"]), str(plot_parameters["end time"])))
                                '''

                                rows = list(cursor.fetchall())
                                if len(rows) % 2:
                                    out.append({"subject": subject, "behavior": behavior,
                                                "modifiers": modifier[0], "duration": UNPAIRED,
                                                "duration_mean": UNPAIRED, "duration_stdev": UNPAIRED,
                                                "number": UNPAIRED, "inter_duration_mean": UNPAIRED,
                                                "inter_duration_stdev": UNPAIRED})
                                else:
                                    all_event_durations, all_event_interdurations = [], []
                                    for idx, row in enumerate(rows):
                                        # event
                                        if idx % 2 == 0:
                                            new_init, new_end = float(row[0]), float(rows[idx + 1][0])
                                            
                                            '''
                                            if len(selectedObservations) == 1:
                                                if (new_init < plot_parameters["start time"] and new_end < plot_parameters["start time"]) \
                                                   or \
                                                   (new_init > plot_parameters["end time"] and new_end > plot_parameters["end time"]):
                                                    continue

                                                if new_init < plot_parameters["start time"]:
                                                    new_init = float(plot_parameters["start time"])
                                                if new_end > plot_parameters["end time"]:
                                                    new_end = float(plot_parameters["end time"])
                                            '''

                                            all_event_durations.append(new_end - new_init)

                                        # inter event if same observation
                                        if idx % 2 and idx != len(rows) - 1 and row[1] == rows[idx + 1][1]:
                                            if plot_parameters["start time"] <= row[0] <= plot_parameters["end time"] and plot_parameters["start time"] <= rows[idx + 1][0] <= plot_parameters["end time"]:
                                                all_event_interdurations.append(float(rows[idx + 1][0]) - float(row[0]))

                                            #all_event_interdurations.append(float(rows[idx + 1][0]) - float(row[0]))

                                    out_cat.append({"subject": subject,
                                                "behavior": behavior,
                                                "modifiers": modifier[0],
                                                "duration": round(sum(all_event_durations), 3),
                                                "duration_mean": round(statistics.mean(all_event_durations), 3) if len(all_event_durations) else "NA",
                                                "duration_stdev": round(statistics.stdev(all_event_durations), 3) if len(all_event_durations) > 1 else "NA",
                                                "number": len(all_event_durations),
                                                "inter_duration_mean": round(statistics.mean(all_event_interdurations), 3) if len(all_event_interdurations) else "NA",
                                                "inter_duration_stdev": round(statistics.stdev(all_event_interdurations), 3) if len(all_event_interdurations) > 1 else "NA"
                                                })

                    else:  # no modifiers

                        if POINT in self.eventType(behavior).upper():

                            #if len(selectedObservations) > 1:
                            cursor.execute("SELECT occurence,observation FROM events WHERE subject = ? AND code = ? ORDER BY observation, occurence", (subject, behavior))
                            '''
                            if not plot_parameters["start time"] and not plot_parameters["end time"]:
                                cursor.execute("SELECT occurence,observation FROM events WHERE subject = ? AND code = ? ORDER BY observation, occurence", (subject, behavior))
                            else:
                                cursor.execute("SELECT occurence,observation FROM events WHERE subject = ? AND code = ? AND occurence BETWEEN ? and ? ORDER BY observation, occurence",
                                               (subject, behavior, str(plot_parameters["start time"]), str(plot_parameters["end time"])))
                            '''

                            rows = list(cursor.fetchall())

                            if len(selectedObservations) == 1:
                                new_rows = []
                                for occurence, observation in rows:
                                    new_occurence = max(float(plot_parameters["start time"]), occurence)
                                    new_occurence = min(new_occurence, float(plot_parameters["end time"]))
                                    new_rows.append([new_occurence, observation])
                                rows = list(new_rows)

                            if not len(rows):
                                if not plot_parameters["exclude behaviors"]:

                                    if {self.pj[ETHOGRAM][idx]["type"] for idx in self.pj[ETHOGRAM] if self.pj[ETHOGRAM][idx]["code"] == behavior} == {"State event"}:
                                        out.append({"subject": subject,
                                                "behavior": behavior,
                                                "modifiers": "",
                                                "duration": 0,
                                                "duration_mean": 0,
                                                "duration_stdev": "NA",
                                                "number": "0",
                                                "inter_duration_mean": "NA",
                                                "inter_duration_stdev": "NA"})
                                    else: # point 
                                        out.append({"subject": subject,
                                                "behavior": behavior,
                                                "modifiers": "",
                                                "duration": "NA",
                                                "duration_mean": "NA",
                                                "duration_stdev": "NA",
                                                "number": "0",
                                                "inter_duration_mean": "NA",
                                                "inter_duration_stdev": "NA"})
                                continue

                            # inter events duration
                            all_event_interdurations = []
                            for idx, row in enumerate(rows):
                                if idx and row[1] == rows[idx - 1][1]:
                                    all_event_interdurations.append(float(row[0]) - float(rows[idx - 1][0]))

                            out_cat.append({"subject": subject,
                                            "behavior": behavior,
                                            "modifiers": "-",
                                            "duration": "NA",
                                            "duration_mean": "NA",
                                            "duration_stdev": "NA",
                                            "number": len(rows),
                                            "inter_duration_mean": round(statistics.mean(all_event_interdurations), 3) if len(all_event_interdurations) else "NA",
                                            "inter_duration_stdev": round(statistics.stdev(all_event_interdurations), 3) if len(all_event_interdurations) > 1 else "NA"
                                            })

                        if STATE in self.eventType(behavior).upper():

                            cursor.execute("SELECT occurence, observation FROM events WHERE subject = ? AND code = ? ORDER BY observation, occurence", (subject, behavior))
                            '''
                            if not plot_parameters["start time"] and not plot_parameters["end time"]:
                                cursor.execute("SELECT occurence, observation FROM events WHERE subject = ? AND code = ? ORDER BY observation, occurence", (subject, behavior))
                            else:
                                cursor.execute("SELECT occurence, observation FROM events WHERE subject = ? AND code = ? AND occurence BETWEEN ? and ? ORDER BY observation, occurence",
                                               (subject, behavior, str(plot_parameters["start time"]), str(plot_parameters["end time"])))
                            '''

                            rows = list(cursor.fetchall())
                            if not len(rows):
                                if not plot_parameters["exclude behaviors"]: # include behaviors without events
                                    out.append({"subject": subject, "behavior": behavior,
                                                "modifiers": "-", "duration": 0, "duration_mean": 0,
                                                "duration_stdev": "NA", "number": 0, "inter_duration_mean": "-",
                                                "inter_duration_stdev": "-"})
                                continue

                            if len(rows) % 2:
                                out.append({"subject": subject, "behavior": behavior, "modifiers": "NA",
                                            "duration": UNPAIRED, "duration_mean": UNPAIRED, "duration_stdev": UNPAIRED,
                                            "number": UNPAIRED, "inter_duration_mean": UNPAIRED,
                                            "inter_duration_stdev": UNPAIRED})
                            else:
                                all_event_durations, all_event_interdurations = [], []
                                for idx, row in enumerate(rows):
                                    # event
                                    if idx % 2 == 0:
                                        new_init, new_end = float(row[0]), float(rows[idx + 1][0])
                                        
                                        '''
                                        if len(selectedObservations) == 1:
                                            if ((new_init < plot_parameters["start time"] and new_end < plot_parameters["start time"])
                                               or
                                               (new_init > plot_parameters["end time"] and new_end > plot_parameters["end time"])):
                                                continue

                                            if new_init < plot_parameters["start time"]:
                                                new_init = float(plot_parameters["start time"])
                                            if new_end > plot_parameters["end time"]:
                                                new_end = float(plot_parameters["end time"])
                                        '''

                                        all_event_durations.append(new_end - new_init)

                                    # inter event if same observation
                                    if idx % 2 and idx != len(rows) - 1 and row[1] == rows[idx + 1][1]:
                                        if plot_parameters["start time"] <= row[0] <= plot_parameters["end time"] and plot_parameters["start time"] <= rows[idx + 1][0] <= plot_parameters["end time"]:
                                            all_event_interdurations.append(float(rows[idx + 1][0]) - float(row[0]))

                                out_cat.append({"subject": subject,
                                            "behavior": behavior,
                                            "modifiers": "-",
                                            "duration": round(sum(all_event_durations), 3),
                                            "duration_mean": round(statistics.mean(all_event_durations), 3) if len(all_event_durations) else "NA",
                                            "duration_stdev": round(statistics.stdev(all_event_durations), 3) if len(all_event_durations) > 1 else "NA",
                                            "number": len(all_event_durations),
                                            "inter_duration_mean": round(statistics.mean(all_event_interdurations), 3) if len(all_event_interdurations) else "NA",
                                            "inter_duration_stdev": round(statistics.stdev(all_event_interdurations), 3) if len(all_event_interdurations) > 1 else "NA"
                                            })

                out += out_cat

                if by_category: # and flagCategories:

                    for behav in out_cat:

                        try:
                            category = [self.pj[ETHOGRAM][x]["category"] for x in self.pj[ETHOGRAM] if "category" in self.pj[ETHOGRAM][x] and self.pj[ETHOGRAM][x]["code"] == behav['behavior']][0]
                        except:
                            category = ""

                        if category in categories[subject]:
                            if behav["duration"] != "-" and categories[subject][category]["duration"] != "-":
                                categories[subject][category]["duration"] += behav["duration"]
                            else:
                                categories[subject][category]["duration"] = "-"
                            categories[subject][category]["number"] += behav["number"]
                        else:
                            categories[subject][category] = {"duration": behav["duration"], "number": behav["number"]}

            out_sorted = []
            for subject in plot_parameters["selected subjects"]:
                for behavior in plot_parameters["selected behaviors"]:
                    for row in out:
                        if row["subject"] == subject and row["behavior"] == behavior:
                            out_sorted.append(row)


            ### http://stackoverflow.com/questions/673867/python-arbitrary-order-by
            return out_sorted, categories


        def default_value(behav, param):
            """
            return value for duration in case of point event
            """
            default_value_ = 0
            if ({self.pj[ETHOGRAM][idx]["type"] for idx in self.pj[ETHOGRAM] if self.pj[ETHOGRAM][idx]["code"] == behav} == {"Point event"} 
               and param in ["duration"]):
                   default_value_ = "-"
            return default_value_


        def init_behav_modif():
            """
            initialize dictionary with subject, behaviors and modifiers
            """
            behaviors = {}
            for subj in plot_parameters["selected subjects"]:
                behaviors[subj] = {}
                for behav_modif in distinct_behav_modif:
                    behav, modif = behav_modif
                    if behav not in behaviors[subj]:
                        behaviors[subj][behav] = {}
                    if not plot_parameters["include modifiers"]:
                        for param in parameters:
                            behaviors[subj][behav][param[0]] = default_value(behav, param[0])

                    if plot_parameters["include modifiers"]:
                        behaviors[subj][behav][modif] = {}
                        for param in parameters:
                            behaviors[subj][behav][modif][param[0]] = default_value(behav, param[0])

            return behaviors


        result, selectedObservations = self.selectObservations(MULTIPLE)

        logging.debug("Selected observations: {}".format(selectedObservations))

        if not selectedObservations:
            return

        flagGroup = False
        if len(selectedObservations) > 1 and mode != "synthetic":
            flagGroup = dialog.MessageDialog(programName, "Group observations in one time budget analysis?", [YES, NO]) == YES

        # check if state events are paired
        out = ""
        for obsId in selectedObservations:
            r, msg = project_functions.check_state_events_obs(obsId, self.pj[ETHOGRAM],
                                                              self.pj[OBSERVATIONS][obsId], self.timeFormat)

            if not r:
                out += "Observation: <strong>{obsId}</strong><br>{msg}<br>".format(obsId=obsId, msg=msg)

        if out:
            self.results = dialog.ResultsWidget()
            
            self.results.setWindowTitle(programName + " - Check selected observations")
            self.results.ptText.setReadOnly(True)
            self.results.ptText.appendHtml(out)
            self.results.show()


        selectedObsTotalMediaLength = Decimal("0.0")
        max_obs_length = 0
        for obsId in selectedObservations:
            obs_length =project_functions.observation_total_length(self.pj[OBSERVATIONS][obsId])

            logging.debug("media length for {0}: {1}".format(obsId, obs_length))

            if obs_length in [0, -1]:
                selectedObsTotalMediaLength = -1
                break
            max_obs_length = max(max_obs_length, obs_length)

            selectedObsTotalMediaLength += obs_length

        # an observation media length is not available
        if selectedObsTotalMediaLength == -1:
            # propose to user to use max event time
            if dialog.MessageDialog(programName, "A media length is not available.<br>Use last event time as media length?", [YES, NO]) == YES:
                maxTime = 0 # max length for all events all subjects
                for obsId in selectedObservations:
                    if self.pj[OBSERVATIONS][obsId][EVENTS]:
                        maxTime += max(self.pj[OBSERVATIONS][obsId][EVENTS])[0]
                logging.debug("max time all events all subjects: {}".format(maxTime))
                selectedObsTotalMediaLength = maxTime
            else:
                selectedObsTotalMediaLength = 0

        logging.debug("selectedObsTotalMediaLength: {}".format(selectedObsTotalMediaLength))

        if mode in ["by_behavior", "by_category"]:

            if len(selectedObservations) > 1:
                plot_parameters = self.choose_obs_subj_behav_category(selectedObservations,
                                                                      maxTime=max_obs_length,
                                                                      by_category=(mode == "by_category"))
            else:
                plot_parameters = self.choose_obs_subj_behav_category(selectedObservations,
                                                                      maxTime=selectedObsTotalMediaLength,
                                                                      by_category=(mode == "by_category"))

        if mode == "synthetic":
            plot_parameters = self.choose_obs_subj_behav_category(selectedObservations,
                                                                  maxTime=max_obs_length,
                                                                  flagShowExcludeBehaviorsWoEvents=False,
                                                                  by_category=False)

        if not plot_parameters["selected subjects"] or not plot_parameters["selected behaviors"]:
            return

        # check if time_budget window must be used
        if mode in ["by_behavior", "by_category"] and (flagGroup or len(selectedObservations) == 1):

            '''
            cursor = self.loadEventsInDB(plot_parameters["selected subjects"], selectedObservations, plot_parameters["selected behaviors"])
            '''
            cursor = db_functions.load_events_in_db(self.pj, plot_parameters["selected subjects"], selectedObservations, plot_parameters["selected behaviors"])

            total_observation_time = 0
            for obsId in selectedObservations:

                '''TO BE REMOVED  obs_length = self.observationTotalMediaLength(obsId)'''
                
                obs_length = project_functions.observation_total_length(self.pj[OBSERVATIONS][obsId])
                
                if obs_length == -1:
                    obs_length = 0

                if plot_parameters["time"] == TIME_FULL_OBS:
                    min_time = float(0)
                    max_time = float(obs_length)

                if plot_parameters["time"] == TIME_EVENTS:
                    try:
                        min_time = float(self.pj[OBSERVATIONS][obsId]["events"][0][0])
                    except:
                        min_time = float(0)
                    try:
                        max_time = float(self.pj[OBSERVATIONS][obsId]["events"][-1][0])
                    except:
                        max_time = float(obs_length)
    
                if plot_parameters["time"] == TIME_ARBITRARY_INTERVAL:
                    min_time = float(plot_parameters["start time"])
                    max_time = float(plot_parameters["end time"])

                    # check intervals
                    for subj in plot_parameters["selected subjects"]:
                        for behav in plot_parameters["selected behaviors"]:
                            if POINT in self.eventType(behav).upper():
                                continue
                            # extract modifiers
                            #if plot_parameters["include modifiers"]:

                            cursor.execute("SELECT distinct modifiers FROM events WHERE observation = ? AND subject = ? AND code = ?", (obsId, subj, behav))
                            distinct_modifiers = list(cursor.fetchall())
                            
                            logging.debug("distinct_modifiers: {}".format(distinct_modifiers))

                            for modifier in distinct_modifiers:

                                #if not modifier[0]:
                                #    continue

                                logging.debug("modifier #{}#".format(modifier[0]))

                                if len(cursor.execute("""SELECT * FROM events WHERE observation = ? AND subject = ? AND code = ? AND modifiers = ? AND occurence < ?""",
                                               (obsId, subj, behav, modifier[0], min_time)).fetchall()) % 2:

                                    cursor.execute("INSERT INTO events (observation, subject, code, type, modifiers, occurence) VALUES (?,?,?,?,?,?)",
                                                   (obsId, subj, behav, "STATE", modifier[0], min_time))

                                if len(cursor.execute("""SELECT * FROM events WHERE observation = ? AND subject = ? AND code = ? AND modifiers = ? AND occurence > ?""",
                                               (obsId, subj, behav, modifier[0], max_time)).fetchall()) % 2:

                                    cursor.execute("INSERT INTO events (observation, subject, code, type, modifiers, occurence) VALUES (?,?,?,?,?,?)",
                                                   (obsId, subj, behav, "STATE", modifier[0], max_time))
                            try:
                                cursor.execute("COMMIT")
                            except:
                                pass

                total_observation_time += (max_time - min_time)

                cursor.execute("""DELETE FROM events WHERE observation = ? AND (occurence < ? OR occurence > ?)""", (obsId, min_time, max_time))
#                cursor.execute("commit")

            out, categories = time_budget_analysis(cursor, plot_parameters, by_category=(mode == "by_category"))

            # widget for results visualization
            self.tb = timeBudgetResults(logging.getLogger().getEffectiveLevel(), self.pj)

            # observations list
            self.tb.label.setText("Selected observations")
            for obs in selectedObservations:
                self.tb.lw.addItem(obs)
    
            # media length
            if len(selectedObservations) > 1:
                if total_observation_time:
                    if self.timeFormat == HHMMSS:
                        self.tb.lbTotalObservedTime.setText("Total observation length: {}".format(seconds2time(total_observation_time)))
                    if self.timeFormat == S:
                        self.tb.lbTotalObservedTime.setText("Total observation length: {:0.3f}".format(float(total_observation_time)))
                else:
                    self.tb.lbTotalObservedTime.setText("Total observation length: not available")
            else:
                if self.timeFormat == HHMMSS:
                    self.tb.lbTotalObservedTime.setText("Analysis from {} to {}".format(seconds2time(min_time), seconds2time(max_time)))
                if self.timeFormat == S:
                    self.tb.lbTotalObservedTime.setText("Analysis from {:0.3f} to {:0.3f} s".format(float(min_time), float(max_time)))
    
            if mode == "by_behavior":

                tb_fields = ["Subject", "Behavior", "Modifiers", "Total number", "Total duration (s)",
                             "Duration mean (s)", "Duration std dev", "inter-event intervals mean (s)",
                             "inter-event intervals std dev", "% of total length"]
    
                fields = ["subject", "behavior",  "modifiers", "number", "duration", "duration_mean", "duration_stdev", "inter_duration_mean", "inter_duration_stdev"]
                self.tb.twTB.setColumnCount(len(tb_fields))
                self.tb.twTB.setHorizontalHeaderLabels(tb_fields)
    
                for row in out:
                    self.tb.twTB.setRowCount(self.tb.twTB.rowCount() + 1)
                    column = 0
                    for field in fields:
                        item = QTableWidgetItem(str(row[field]).replace(" ()", ""))
                        # no modif allowed
                        item.setFlags(Qt.ItemIsEnabled)
                        self.tb.twTB.setItem(self.tb.twTB.rowCount() - 1, column, item)
                        column += 1
    
                    # % of total time
                    if row["duration"] not in ["NA", "-", UNPAIRED, 0] and selectedObsTotalMediaLength:
                        item = QTableWidgetItem(str(round(row["duration"] / float(total_observation_time) * 100, 1)))
                    else:
                        item = QTableWidgetItem("NA")
    
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
                            item = QTableWidgetItem(str(categories[subject][category][field]))
                            item.setFlags(Qt.ItemIsEnabled)
                            item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                            self.tb.twTB.setItem(self.tb.twTB.rowCount() - 1, column, item)
    
            self.tb.twTB.resizeColumnsToContents()
    
            self.tb.show()



        if mode in ["by_behavior", "by_category"] and (not flagGroup and len(selectedObservations) > 1) or mode == "synthetic":

            if mode in ["by_behavior", "by_category"]:
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

            if mode in ["by_behavior", "by_category"] and "workbook" in outputFormat:
                workbook = tablib.Databook()
                flagWorkBook = True
                if "xls" in outputFormat:
                    filters = "Microsoft Excel Workbook *.xlsx (*.xlsx);;All files (*)"
                if "od" in outputFormat:
                    filters = "Open Document Workbook *.ods (*.ods);;All files (*)"
                
                if QT_VERSION_STR[0] == "4":
                    WBfileName, filter_ = QFileDialog(self).getSaveFileNameAndFilter(self, "Save Time budget analysis", "", filters)
                else:
                    WBfileName, filter_ = QFileDialog(self).getSaveFileName(self, "Save Time budget analysis", "", filters)
                if not WBfileName:
                    return

            if mode in ["by_behavior", "by_category"] and "workbook" not in outputFormat: # not workbook
                exportDir = QFileDialog(self).getExistingDirectory(self, "Choose a directory to save the time budget analysis",
                                                                   os.path.expanduser("~"), options=QFileDialog.ShowDirsOnly)
                if not exportDir:
                    return

            if mode == "synthetic":

                formats_str = ("Tab Separated Values *.txt, *.tsv (*.txt *.tsv);;"
                       "Comma Separated Values *.txt *.csv (*.txt *.csv);;"
                       "Open Document Spreadsheet *.ods (*.ods);;"
                       "Microsoft Excel Spreadsheet *.xlsx (*.xlsx);;"
                       #"Pandas dataframe (*.df);;"
                       "Legacy Microsoft Excel Spreadsheet *.xls (*.xls);;"
                       "HTML *.html (*.html);;"
                       "All files (*)")

                while True:
                    if QT_VERSION_STR[0] == "4":
                        fileName, filter_ = QFileDialog(self).getSaveFileNameAndFilter(self, "Save Time budget report", "", formats_str)
                    else:
                        fileName, filter_ = QFileDialog(self).getSaveFileName(self, "Save Time budget report", "", formats_str)

                    if not fileName:
                        return

                    extension = ""
                    availableFormats = ("tsv", "csv", "ods", "xlsx)", "xls)", "html") # ) is added to distinguish between xls and xlsx
                    for fileExtension in availableFormats:
                        if fileExtension in filter_:
                            extension = fileExtension.replace(")", "")
                    if not extension:
                        QMessageBox.warning(self, programName, "Choose a file format", QMessageBox.Ok | QMessageBox.Default, QMessageBox.NoButton)
                    else:
                        break

                data_report = tablib.Dataset()
                data_report.title = "Synthetic time budget"
                
                parameters = [["duration", "Total duration"], ["number", "Number of occurrences"]]
                
                '''
                cursor = self.loadEventsInDB(plot_parameters["selected subjects"], selectedObservations, plot_parameters["selected behaviors"])
                '''

                cursor = db_functions.load_events_in_db(self.pj, plot_parameters["selected subjects"], selectedObservations, plot_parameters["selected behaviors"])
                
                cursor.execute("SELECT distinct code, modifiers FROM events WHERE subject in ({})".format(",".join("?" * len(plot_parameters["selected subjects"]))),
                               (plot_parameters["selected subjects"]))
                
                distinct_behav_modif = [[rows["code"], rows["modifiers"]] for rows in cursor.fetchall()]
                
                # add selected behaviors that are not observed
                for behav in plot_parameters["selected behaviors"]:
                    if [x for x in distinct_behav_modif if x[0] == behav] == []:
                        distinct_behav_modif.append([behav, "-"])
    
                behaviors = init_behav_modif()
                
                subj_header, behav_header, modif_header, param_header = ["", ""], ["", ""], ["", ""], ["", "Total length (s)"]
                #subj_header, behav_header, modif_header, param_header = [""], [""], [""], [""]
                for subj in plot_parameters["selected subjects"]:
                    for behav in plot_parameters["selected behaviors"]:
                        if not plot_parameters["include modifiers"]:
                            for param in parameters:
                                subj_header.append(subj)
                                behav_header.append(behav)
                                param_header.append(param[1])
                                
                        if plot_parameters["include modifiers"]:
                            for modif in sorted(list(behaviors[subj][behav].keys())):
                                for param in parameters:
                                    subj_header.append(subj)
                                    behav_header.append(behav)
                                    modif_header.append(modif)
                                    param_header.append(param[1])
    
                data_report.append(subj_header)
                data_report.append(behav_header)
                if plot_parameters["include modifiers"]:
                    data_report.append(modif_header)
                data_report.append(param_header)

            if mode == "by_behavior":
                fields = ["subject", "behavior",  "modifiers", "number",
                          "duration", "duration_mean", "duration_stdev",
                          "inter_duration_mean", "inter_duration_stdev"]

            if mode == "by_category":
                fields = ["subject", "category",  "number", "duration"]


            for obsId in selectedObservations:

                cursor = db_functions.load_events_in_db(self.pj, plot_parameters["selected subjects"], [obsId], plot_parameters["selected behaviors"])

                '''TO BE REMOVED  obs_length = self.observationTotalMediaLength(obsId)'''
                
                obs_length = project_functions.observation_total_length(self.pj[OBSERVATIONS][obsId])
                
                if obs_length == -1:
                    obs_length = 0

                if plot_parameters["time"] == TIME_FULL_OBS:
                    min_time = float(0)
                    max_time = float(obs_length)
    
                if plot_parameters["time"] == TIME_EVENTS:
                    try:
                        min_time = float(self.pj[OBSERVATIONS][obsId]["events"][0][0])
                    except:
                        min_time = float(0)
                    try:
                        max_time = float(self.pj[OBSERVATIONS][obsId]["events"][-1][0])
                    except:
                        max_time = float(obs_length)

                if plot_parameters["time"] == TIME_ARBITRARY_INTERVAL:
                    min_time = float(plot_parameters["start time"])
                    max_time = float(plot_parameters["end time"])

                    # check intervals
                    for subj in plot_parameters["selected subjects"]:
                        for behav in plot_parameters["selected behaviors"]:
                            if POINT in self.eventType(behav).upper():
                                continue
                            # extract modifiers
                            #if plot_parameters["include modifiers"]:

                            cursor.execute("SELECT distinct modifiers FROM events WHERE observation = ? AND subject = ? AND code = ?", (obsId, subj, behav))
                            distinct_modifiers = list(cursor.fetchall())

                            for modifier in distinct_modifiers:

                                if len(cursor.execute("""SELECT * FROM events WHERE observation = ? AND subject = ? AND code = ? AND modifiers = ? AND occurence < ?""",
                                               (obsId, subj, behav, modifier[0], min_time)).fetchall()) % 2:
                                    cursor.execute("INSERT INTO events (observation, subject, code, type, modifiers, occurence) VALUES (?,?,?,?,?,?)",
                                                   (obsId, subj, behav, "STATE", modifier[0], min_time))
                                if len(cursor.execute("""SELECT * FROM events WHERE observation = ? AND subject = ? AND code = ? AND modifiers = ? AND occurence > ?""",
                                               (obsId, subj, behav, modifier[0], max_time)).fetchall()) % 2:
                                    cursor.execute("INSERT INTO events (observation, subject, code, type, modifiers, occurence) VALUES (?,?,?,?,?,?)",
                                                   (obsId, subj, behav, "STATE", modifier[0], max_time))
                            try:
                                cursor.execute("COMMIT")
                            except:
                                pass

                cursor.execute("""DELETE FROM events WHERE observation = ? AND (occurence < ? OR occurence > ?)""", (obsId, min_time,max_time))

                out, categories = time_budget_analysis(cursor, plot_parameters, by_category=(mode == "by_category"))

                if mode == "synthetic":

                    behaviors = init_behav_modif()

                    for element in out:
                        for param in parameters:
                            if not plot_parameters["include modifiers"]:
                                try:
                                    behaviors[element["subject"]][element["behavior"]][param[0]] = element[param[0]]
                                except:
                                    pass
                            if plot_parameters["include modifiers"]:
                                try:
                                    behaviors[element["subject"]][element["behavior"]][element["modifiers"]][param[0]] = element[param[0]]
                                except:
                                    pass

                    columns = []
                    columns.append(obsId)
                    columns.append("{:0.3f}".format(max_time - min_time))
                    #columns.append([obsId])

                    for subj in plot_parameters["selected subjects"]:
                        for behav in plot_parameters["selected behaviors"]:
                            if not plot_parameters["include modifiers"]:
                                for param in parameters:
                                    columns.append(behaviors[subj][behav][param[0]])
                            if plot_parameters["include modifiers"]:
                                for modif in sorted(list(behaviors[subj][behav].keys())):
                                    for param in parameters:
                                        columns.append(behaviors[subj][behav][modif][param[0]])

                    data_report.append(columns)

                if mode in ["by_behavior", "by_category"]:
                    rows = []
                    # observation id
                    rows.append(["Observation id", obsId])
                    rows.append([""])
    
                    #indep variables
                    '''
                    if INDEPENDENT_VARIABLES in self.pj[OBSERVATIONS][obsId]:
                        rows.append(["Independent variables:"])
                        for var in self.pj[OBSERVATIONS][obsId][INDEPENDENT_VARIABLES]:
                            rows.append([var, self.pj[OBSERVATIONS][obsId][INDEPENDENT_VARIABLES][var]])
                    '''
                    labels = ["Independent variables"]
                    values = [""]
                    if INDEPENDENT_VARIABLES in self.pj and self.pj[INDEPENDENT_VARIABLES]:
                        for idx in self.pj[INDEPENDENT_VARIABLES]:
                            labels.append(self.pj[INDEPENDENT_VARIABLES][idx]["label"])
                            if (INDEPENDENT_VARIABLES in self.pj[OBSERVATIONS][obsId]
                                and self.pj[INDEPENDENT_VARIABLES][idx]["label"] in self.pj[OBSERVATIONS][obsId][INDEPENDENT_VARIABLES]):
                                values.append(self.pj[OBSERVATIONS][obsId][INDEPENDENT_VARIABLES][self.pj[INDEPENDENT_VARIABLES][idx]["label"]])
                    rows.append(labels)
                    rows.append(values)
                    rows.append([""])

                    rows.append(["Analysis from", "{:0.3f}".format(float(min_time)),"to", "{:0.3f}".format(float(max_time))])
                    rows.append(["Total length (s)", "{:0.3f}".format(float(max_time - min_time))])
                    rows.append([""])
                    rows.append(["Time budget"])
    
                    if mode == "by_behavior":
    
                        rows.append(fields + ["% of total length"])
                        #data.headers = fields + ["% of total media length"]
    
                        for row in out:
                            values = []
                            for field in fields:
                                values.append(str(row[field]).replace(" ()", ""))
    
                            # % of total time
                            if row["duration"] not in ["NA", "-", UNPAIRED, 0] and selectedObsTotalMediaLength:
                            #if row["duration"] != "-" and row["duration"] != 0 and row["duration"] != UNPAIRED and selectedObsTotalMediaLength:
                                values.append(round(row["duration"] / float(max_time - min_time) * 100, 1))
                                '''
                                if len(selectedObservations) > 1:
                                    values.append(round(row["duration"] / float(selectedObsTotalMediaLength) * 100, 1))
                                else:
                                    values.append(round(row["duration"] / float(max_time - min_time) * 100, 1))
                                '''
                            else:
                                values.append("-")

                            rows.append(values)
    
                    if mode == "by_category":
                        rows.append = fields
                        #data.headers = fields # + ["% of total media length"]
                        for subject in categories:
    
                            for category in categories[subject]:
                                values = []
                                values.append(subject)
                                if category == "":
                                    values.append("No category")
                                else:
                                    values.append(category)
    
                                values.append(categories[subject][category]["number"])
                                values.append(categories[subject][category]["duration"])
    
                                rows.append(values)
    
                    data = tablib.Dataset()
                    data.title = obsId
                    for row in rows:
                        data.append(complete(row, max([len(r) for r in rows])))

                    if "xls" in outputFormat:
                        for forbidden_char in EXCEL_FORBIDDEN_CHARACTERS:
                            data.title = data.title.replace(forbidden_char, " ")
    
                    if flagWorkBook:
                        for forbidden_char in EXCEL_FORBIDDEN_CHARACTERS:
                            data.title = data.title.replace(forbidden_char, " ")
                        if "xls" in outputFormat:
                            if len(data.title) > 31:
                                data.title = data.title[:31]
                        workbook.add_sheet(data)
    
                    else:
    
                        fileName = exportDir + os.sep + safeFileName(obsId) + "." + extension

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
                            if len(data.title) > 31:
                                data.title = data.title[:31]
                                QMessageBox.warning(None, programName, ("The worksheet name <b>{0}</b> was shortened to <b>{1}</b> due to XLS format limitations.\n"
                                                                        "The limit on worksheet name length is 31 characters").format(obsId, data.title),
                                                    QMessageBox.Ok | QMessageBox.Default, QMessageBox.NoButton)
    
                            with open(fileName, "wb") as f:
                                f.write(data.xls)

            if mode == "synthetic":
                if extension in ["tsv", "csv", "html"]:
                    with open(fileName, "wb") as f:
                        f.write(str.encode(data_report.export(extension)))
                if extension in ["ods", "xlsx", "xls"]:
                    with open(fileName, "wb") as f:
                         f.write(data_report.export(extension))

            if mode in ["by_behavior", "by_category"] and flagWorkBook:
                if "xls" in outputFormat:
                    with open(WBfileName, "wb") as f:
                        f.write(workbook.xlsx)
                if "od" in outputFormat:
                    with open(WBfileName, "wb") as f:
                        f.write(workbook.ods)


    def plot_events1_triggered(self):
        """
        plot events with matplotlib (legacy version)
        """

        result, selectedObservations = self.selectObservations(SELECT1)

        if not selectedObservations:
            return

        if not self.pj[OBSERVATIONS][selectedObservations[0]][EVENTS]:
            QMessageBox.warning(self, programName, "There are no events in the selected observation")
            return

        for obsId in selectedObservations:
            
            totalMediaLength = project_functions.observation_total_length(self.pj[OBSERVATIONS][obsId])

        if totalMediaLength == -1:
            totalMediaLength = 0

        plot_parameters = self.choose_obs_subj_behav_category(selectedObservations, totalMediaLength)

        totalMediaLength = int(totalMediaLength)

        if not plot_parameters["selected subjects"] or not plot_parameters["selected behaviors"]:
            return

        cursor = db_functions.load_events_in_db(self.pj, plot_parameters["selected subjects"], selectedObservations, plot_parameters["selected behaviors"])

        o = {}

        for subject in plot_parameters["selected subjects"]:

            o[subject] = {}

            for behavior in plot_parameters["selected behaviors"]:

                if plot_parameters["include modifiers"]:

                    cursor.execute("SELECT distinct modifiers FROM events WHERE subject = ? AND code = ?", (subject, behavior))
                    distinct_modifiers = list(cursor.fetchall())

                    for modifier in distinct_modifiers:
                        cursor.execute("SELECT occurence FROM events WHERE subject = ? AND code = ? AND modifiers = ? ORDER BY observation, occurence",
                                      (subject, behavior, modifier[0]))

                        rows = cursor.fetchall()

                        if modifier[0]:
                            behaviorOut = [behavior, modifier[0].replace("|", ",")]

                        else:
                            behaviorOut = [behavior]

                        behaviorOut_json = json.dumps(behaviorOut)

                        if not behaviorOut_json in o[subject]:
                            o[subject][behaviorOut_json] = []

                        for idx, row in enumerate(rows):
                            if POINT in self.eventType(behavior).upper():
                                o[subject][behaviorOut_json].append([row[0], row[0]])  # for point event start = end

                            if STATE in self.eventType(behavior).upper():
                                if idx % 2 == 0:
                                    try:
                                        o[subject][behaviorOut_json].append([row[0], rows[idx + 1][0]])
                                    except:
                                        if NO_FOCAL_SUBJECT in subject:
                                            sbj = ""
                                        else:
                                            sbj = "for subject <b>{0}</b>".format(subject)
                                        QMessageBox.critical(self, programName,
                                            "The STATE behavior <b>{0}</b> is not paired {1}".format(behaviorOut, sbj))
                else:
                    cursor.execute("SELECT occurence FROM events WHERE subject = ? AND code = ?  ORDER BY observation, occurence",
                                  (subject, behavior))
                    rows = list(cursor.fetchall())

                    if not len(rows) and plot_parameters["exclude behaviors"]:
                        continue

                    if STATE in self.eventType(behavior).upper() and len(rows) % 2:
                        continue

                    behaviorOut = [behavior]
                    behaviorOut_json = json.dumps(behaviorOut)

                    if not behaviorOut_json in o[subject]:
                        o[subject][behaviorOut_json] = []

                    for idx, row in enumerate(rows):
                        if POINT in self.eventType(behavior).upper():
                            o[subject][behaviorOut_json].append([row[0], row[0]])   # for point event start = end
                        if STATE in self.eventType(behavior).upper():
                            if idx % 2 == 0:
                                o[subject][behaviorOut_json].append([row[0], rows[idx + 1][0]])

        if not plot_events.plot_time_ranges(self.pj,
                                              self.timeFormat,
                                              self.plot_colors,
                                              o,
                                selectedObservations[0],
                                plot_parameters["start time"],
                                plot_parameters["end time"],
                                plot_parameters["exclude behaviors"],
                                line_width=10):
            QMessageBox.warning(self, programName, "Check events")

        

    def plot_events2_triggered(self):
        """
        new plot events with matplotlib 
        """

        result, selectedObservations = self.selectObservations(MULTIPLE)

        if not selectedObservations:
            return

        # check if state events are paired
        out = ""
        not_paired_obs_list = []
        for obsId in selectedObservations:
            r, msg = project_functions.check_state_events_obs(obsId, self.pj[ETHOGRAM],
                                                              self.pj[OBSERVATIONS][obsId], self.timeFormat)

            if not r:
                out += "Observation: <strong>{obsId}</strong><br>{msg}<br>".format(obsId=obsId, msg=msg)
                not_paired_obs_list.append(obsId)

        if out:
            self.results = dialog.ResultsWidget()
            self.results.setWindowTitle(programName + " - Check selected observations")
            self.results.ptText.setReadOnly(True)
            self.results.ptText.appendHtml(out)
            self.results.show()

        selectedObservations = [x for x in selectedObservations if x not in not_paired_obs_list]
        if not selectedObservations:
            return

        # check if almost one selected observation has events
        flag_no_events = True
        for obsId in selectedObservations:
            if self.pj[OBSERVATIONS][obsId][EVENTS]:
                flag_no_events = False
                break
        if flag_no_events:
            QMessageBox.warning(self, programName, "No events found in the selected observations")
            return

        max_obs_length = -1
        for obsId in selectedObservations:
            totalMediaLength = project_functions.observation_total_length(self.pj[OBSERVATIONS][obsId])

            if totalMediaLength == -1:
                totalMediaLength = 0

            max_obs_length = max(max_obs_length, totalMediaLength)

        if len(selectedObservations) == 1:
            plot_parameters = self.choose_obs_subj_behav_category(selectedObservations, maxTime=totalMediaLength)
        else:
            plot_parameters = self.choose_obs_subj_behav_category(selectedObservations, maxTime=0)


        if not plot_parameters["selected subjects"] or not plot_parameters["selected behaviors"]:
            QMessageBox.warning(self, programName, "Select subject(s) and behavior(s) to plot")
            return

        if len(selectedObservations) > 1:
            plot_directory = QFileDialog(self).getExistingDirectory(self, "Choose a directory to save events' plots",
                                                                    os.path.expanduser("~"),
                                                                    options=QFileDialog(self).ShowDirsOnly)

            if not plot_directory:
                return

            item, ok = QInputDialog.getItem(self, "Select the file format", "Available formats", ["PNG", "SVG", "PDF", "EPS", "PS"], 0, False)
            if ok and item:
                file_format = item.lower()
            else:
                return

        totalMediaLength = int(totalMediaLength)

        cursor = db_functions.load_events_in_db(self.pj, plot_parameters["selected subjects"], selectedObservations, plot_parameters["selected behaviors"])

        for obsId in selectedObservations:

            obs_length = project_functions.observation_total_length(self.pj[OBSERVATIONS][obsId])

            if obs_length == -1:
                obs_length = 0

            o = {}
    
            for subject in plot_parameters["selected subjects"]:
    
                o[subject] = {}
    
                for behavior in plot_parameters["selected behaviors"]:
    
                    if plot_parameters["include modifiers"]:
    
                        cursor.execute("SELECT distinct modifiers FROM events WHERE observation = ? AND subject = ? AND code = ?",
                                       (obsId, subject, behavior))
                        distinct_modifiers = list(cursor.fetchall())
    
                        for modifier in distinct_modifiers:
                          
                            cursor.execute(("SELECT occurence FROM events WHERE observation = ? AND subject = ? AND code = ? AND modifiers = ? "
                                            "ORDER BY observation, occurence"),
                                          (obsId, subject, behavior, modifier[0]))
    
                            rows = cursor.fetchall()
    
                            if modifier[0]:
                                behaviorOut = [behavior, modifier[0]]
                            else:
                                behaviorOut = [behavior]
    
                            behaviorOut_json = json.dumps(behaviorOut)
    
                            if not behaviorOut_json in o[subject]:
                                o[subject][behaviorOut_json] = []
    
                            for idx, row in enumerate(rows):
                                if POINT in self.eventType(behavior).upper():
                                    o[subject][behaviorOut_json].append([row[0], row[0]])  # for point event start = end
    
                                if STATE in self.eventType(behavior).upper():
                                    if idx % 2 == 0:  # only 1 occurence of 2
                                        try:
                                            o[subject][behaviorOut_json].append([row[0], rows[idx + 1][0]])
                                        except:
                                            QMessageBox.critical(self, programName, "Error on observation <b>{}</b>".format(obsId))
    
                    else:  # do not include modifiers
    
                        cursor.execute(("SELECT occurence FROM events WHERE observation = ? AND subject = ? AND code = ? "
                                        "ORDER BY observation, occurence"),
                                      (obsId, subject, behavior))
                        rows = list(cursor.fetchall())
    
                        if not len(rows) and plot_parameters["exclude behaviors"]:
                            continue
    
                        if STATE in self.eventType(behavior).upper() and len(rows) % 2:
                            continue
    
                        behaviorOut_json = json.dumps([behavior])
    
                        if not behaviorOut_json in o[subject]:
                            o[subject][behaviorOut_json] = []
    
                        for idx, row in enumerate(rows):
                            if POINT in self.eventType(behavior).upper():
                                o[subject][behaviorOut_json].append([row[0], row[0]])   # for point event start = end

                            if STATE in self.eventType(behavior).upper():
                                if idx % 2 == 0:  # only 1 occurence of 2
                                    try:
                                        o[subject][behaviorOut_json].append([row[0], rows[idx + 1][0]])
                                    except:
                                        QMessageBox.critical(self, programName, "Error on observation <b>{}</b>".format(obsId))

            if plot_parameters["time"] == TIME_FULL_OBS:
                min_time = float(0)
                max_time = float(obs_length)

            if plot_parameters["time"] == TIME_EVENTS:
                try:
                    min_time = float(self.pj[OBSERVATIONS][obsId]["events"][0][0])
                except:
                    min_time = float(0)
                try:
                    max_time = float(self.pj[OBSERVATIONS][obsId]["events"][-1][0])
                except:
                    max_time = float(obs_length)

            if plot_parameters["time"] == TIME_ARBITRARY_INTERVAL:
                min_time = float(plot_parameters["start time"])
                max_time = float(plot_parameters["end time"])

            if len(selectedObservations) > 1:
                output_file_name = str(pathlib.Path(pathlib.Path(plot_directory) / safeFileName(obsId)).with_suffix("." + file_format))
            else:
                output_file_name = ""

            ret = plot_events.create_events_plot2(o,
                                                  all_behaviors=[self.pj[ETHOGRAM][idx]["code"] for idx in sorted_keys(self.pj[ETHOGRAM])],
                                                  all_subjects=[NO_FOCAL_SUBJECT] + [self.pj[SUBJECTS][idx]["name"] for idx in sorted_keys(self.pj[SUBJECTS])],
                                                  exclude_behaviors_wo_events=plot_parameters["exclude behaviors"],
                                                  min_time=min_time,
                                                  max_time=max_time,
                                                  output_file_name=output_file_name,
                                                  plot_colors=self.plot_colors)

            if ret["error code"]:
                QMessageBox.critical(self, programName, ret["msg"])


    def load_project(self, project_path, project_changed, pj):
        """
        load specified project
        """
        self.pj = copy.deepcopy(pj)
        memProjectChanged = project_changed
        self.initialize_new_project()
        self.projectChanged = True
        self.projectChanged = memProjectChanged
        self.load_behaviors_in_twEthogram([self.pj[ETHOGRAM][x]["code"] for x in self.pj[ETHOGRAM]])
        self.load_subjects_in_twSubjects([self.pj[SUBJECTS][x]["name"] for x in self.pj[SUBJECTS]])
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
            fn = QFileDialog(self).getOpenFileName(self, "Open project", "", "Project files (*.boris);;All files (*)")
            fileName = fn[0] if type(fn) is tuple else fn

        else: # recent project
            fileName = action.text()

        if fileName:
            project_path, project_changed, pj, msg = project_functions.open_project_json(fileName)

            if "error" in pj:
                logging.debug(pj["error"])
                QMessageBox.critical(self, programName, pj["error"])
            else:
                if msg:
                    QMessageBox.information(self, programName, msg)

                self.load_project(project_path, project_changed, pj)


    def initialize_new_project(self, flag_new=True):
        """
        initialize interface and variables for a new or edited project
        """
        logging.debug("initialize new project...")

        self.lbLogoUnito.setVisible(not flag_new)
        self.lbLogoBoris.setVisible(not flag_new)
        self.dwEthogram.setVisible(flag_new)
        self.dwSubjects.setVisible(flag_new)


    def close_project(self):
        """
        close current project
        """

        # check if current observation
        if self.observationId:
            response = dialog.MessageDialog(programName, "There is a current observation. What do you want to do?",
                                            ["Close observation", "Continue observation"])
            if response == "Close observation":
                self.close_observation()
            if response == "Continue observation":
                return

        if self.projectChanged:
            response = dialog.MessageDialog(programName, "What to do about the current unsaved project?", [SAVE, DISCARD, CANCEL])

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

        self.lb_current_media_time.setVisible(False)
        self.lbFocalSubject.setVisible(False)
        self.lbCurrentStates.setVisible(False)


    def convertTime(self, sec):
        """
        convert time in base of current format
        
        Args:
            sec: time in seconds

        Returns:
            string: time in base of current format (self.timeFormat S or HHMMSS)
        """

        if self.timeFormat == S:
            return '%.3f' % sec

        if self.timeFormat == HHMMSS:
            return seconds2time(sec)


    def edit_project(self, mode):
        """
        project management
        
        Args:
            mode (str): new/edit 
        """

        logging.debug("self.projectChanged: {}".format(self.projectChanged))

        if self.observationId:
            QMessageBox.warning(self, programName, ("You must close the current observation before creating"
                                                    " a new project or modifying the current project."))
            return

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

        newProjectWindow = projectDialog(logging.getLogger().getEffectiveLevel())

        # pass copy of self.pj
        newProjectWindow.pj = copy.deepcopy(self.pj)

        if self.projectWindowGeometry:
            newProjectWindow.restoreGeometry(self.projectWindowGeometry)
        else:
            newProjectWindow.resize(800, 400)

        newProjectWindow.setWindowTitle(mode + " project")
        newProjectWindow.tabProject.setCurrentIndex(0)   # project information

        newProjectWindow.obs = newProjectWindow.pj[ETHOGRAM]
        newProjectWindow.subjects_conf = newProjectWindow.pj[SUBJECTS]

        if newProjectWindow.pj["time_format"] == S:
            newProjectWindow.rbSeconds.setChecked(True)

        if newProjectWindow.pj["time_format"] == HHMMSS:
            newProjectWindow.rbHMS.setChecked(True)

        if mode == NEW:
            newProjectWindow.dteDate.setDateTime(QDateTime.currentDateTime())
            newProjectWindow.lbProjectFilePath.setText("")

        if mode == EDIT:

            if newProjectWindow.pj["project_name"]:
                newProjectWindow.leProjectName.setText(newProjectWindow.pj["project_name"])

            newProjectWindow.lbProjectFilePath.setText("Project file path: " + self.projectFileName)

            if newProjectWindow.pj["project_description"]:
                newProjectWindow.teDescription.setPlainText(newProjectWindow.pj["project_description"])

            if newProjectWindow.pj["project_date"]:
                newProjectWindow.dteDate.setDateTime(QDateTime.fromString(newProjectWindow.pj["project_date"], "yyyy-MM-ddThh:mm:ss"))
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

                    item = QTableWidgetItem(obs)
                    newProjectWindow.twObservations.setItem(newProjectWindow.twObservations.rowCount() - 1, 0, item)

                    item = QTableWidgetItem(newProjectWindow.pj[OBSERVATIONS][obs]["date"].replace("T", " "))
                    newProjectWindow.twObservations.setItem(newProjectWindow.twObservations.rowCount() - 1, 1, item)

                    item = QTableWidgetItem(newProjectWindow.pj[OBSERVATIONS][obs]["description"])
                    newProjectWindow.twObservations.setItem(newProjectWindow.twObservations.rowCount() - 1, 2, item)

                    mediaList = []
                    if newProjectWindow.pj[OBSERVATIONS][obs][TYPE] in [MEDIA]:
                        for idx in newProjectWindow.pj[OBSERVATIONS][obs][FILE]:
                            for media in newProjectWindow.pj[OBSERVATIONS][obs][FILE][idx]:
                                mediaList.append("#{}: {}".format(idx, media))

                    elif newProjectWindow.pj[OBSERVATIONS][obs][TYPE] in [LIVE]:
                        mediaList = [LIVE]

                    item = QTableWidgetItem("\n".join(mediaList))
                    newProjectWindow.twObservations.setItem(newProjectWindow.twObservations.rowCount() - 1, 3, item)

                newProjectWindow.twObservations.resizeColumnsToContents()

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

                        newProjectWindow.twBehaviors.setItem(newProjectWindow.twBehaviors.rowCount() - 1, behavioursFields[field], item)

                newProjectWindow.twBehaviors.resizeColumnsToContents()

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
                    newProjectWindow.twBehavCodingMap.setItem(newProjectWindow.twBehavCodingMap.rowCount() - 1, 0, QTableWidgetItem(bcm["name"]))
                    codes = ", ".join([bcm["areas"][idx]["code"] for idx in bcm["areas"]])
                    newProjectWindow.twBehavCodingMap.setItem(newProjectWindow.twBehavCodingMap.rowCount() - 1, 1, QTableWidgetItem(codes))

            # time converters
            if CONVERTERS in newProjectWindow.pj:
                newProjectWindow.converters = newProjectWindow.pj[CONVERTERS]
                newProjectWindow.load_converters_in_table()

        newProjectWindow.dteDate.setDisplayFormat("yyyy-MM-dd hh:mm:ss")

        if mode == NEW:
            newProjectWindow.pj = copy.deepcopy(EMPTY_PROJECT)

        if newProjectWindow.exec_():  # button OK returns True

            if mode == NEW:
                self.projectFileName = ""
                self.projectChanged = True

            if mode == EDIT:
                self.projectChanged = dict(self.pj) != dict(newProjectWindow.pj)

            # retrieve project dict from window
            self.pj = copy.deepcopy(newProjectWindow.pj)
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
                self.twEthogram.setRowCount(0)
                self.load_behaviors_in_twEthogram([self.pj[ETHOGRAM][x]["code"] for x in self.pj[ETHOGRAM]])

                # subjects
                self.load_subjects_in_twSubjects([self.pj[SUBJECTS][x]["name"] for x in self.pj[SUBJECTS]])

            self.initialize_new_project()

            self.menu_options()

        self.projectWindowGeometry = newProjectWindow.saveGeometry()

        del newProjectWindow


    def new_project_activated(self):
        """
        new project
        """
        self.edit_project(NEW)


    def save_project_json(self, projectFileName):
        """
        save project to JSON file

        convert Decimal type in float
        """

        logging.debug("save project json {0}:".format(projectFileName))

        self.pj["project_format_version"] = project_format_version

        try:
            f = open(projectFileName, "w")
            f.write(json.dumps(self.pj, indent=1, separators=(',', ':'), default=decimal_default))
            f.close()

            self.projectChanged = False
            return ""

        except:
            logging.critical("The project file can not be saved.\nError: {}".format(sys.exc_info()[0]))
            QMessageBox.critical(self, programName, "The project file can not be saved! {}".format(sys.exc_info()[0]))
            return "not saved"


    def save_project_as_activated(self):
        """
        save current project asking for a new file name
        """
        if QT_VERSION_STR[0] == "4":
            projectNewFileName, filtr = QFileDialog(self).getSaveFileNameAndFilter(self, "Save project as", os.path.dirname(self.projectFileName), "Projects file (*.boris);;All files (*)")
        else:
            projectNewFileName, filtr = QFileDialog(self).getSaveFileName(self, "Save project as", os.path.dirname(self.projectFileName), "Projects file (*.boris);;All files (*)")
        if not projectNewFileName:
            return "Not saved"
        else:

            # add .boris if filter = 'Projects file (*.boris)'
            if  filtr == "Projects file (*.boris)" and os.path.splitext(projectNewFileName)[1] != ".boris":
                projectNewFileName += ".boris"

            self.save_project_json(projectNewFileName)
            self.projectFileName = projectNewFileName


    def save_project_activated(self):
        """
        save current project
        """
        logging.debug("Project file name: {}".format(self.projectFileName))

        if not self.projectFileName:
            if not self.pj["project_name"]:
                txt = "NONAME.boris"
            else:
                txt = self.pj['project_name'] + '.boris'
            os.chdir(os.path.expanduser("~"))
            if QT_VERSION_STR[0] == "4":
                self.projectFileName, filtr = QFileDialog(self).getSaveFileNameAndFilter(self, 'Save project', txt, 'Projects file (*.boris);;All files (*)')
            else:
                self.projectFileName, filtr = QFileDialog(self).getSaveFileName(self, 'Save project', txt, 'Projects file (*.boris);;All files (*)')

            if not self.projectFileName:
                return "not saved"

            # add .boris if filter = 'Projects file (*.boris)'
            if filtr == 'Projects file (*.boris)' and os.path.splitext(self.projectFileName)[1] != '.boris':
                self.projectFileName += '.boris'

            return self.save_project_json(self.projectFileName)

        else:
            return self.save_project_json(self.projectFileName)

        return ""


    def liveTimer_out(self):
        """
        timer for live observation
        """

        currentTime = self.getLaps()
        self.lbTimeLive.setText(self.convertTime(currentTime))

        # extract State events
        StateBehaviorsCodes = [self.pj[ETHOGRAM][x]['code'] for x in [y for y in self.pj[ETHOGRAM] if 'State' in self.pj[ETHOGRAM][y][TYPE]]]

        self.currentStates = {}
        # add states for no focal subject

        self.currentStates = self.get_current_states_by_subject(StateBehaviorsCodes,
                                                                self.pj[OBSERVATIONS][self.observationId][EVENTS],
                                                                dict(self.pj[SUBJECTS], **{"": {"name": ""}}),
                                                                currentTime)


        # add states for all configured subjects
        for idx in self.pj[SUBJECTS]:
            # add subject index
            self.currentStates[idx] = []
            for sbc in StateBehaviorsCodes:
                if len([x[pj_obs_fields['code']] for x in self.pj[OBSERVATIONS][self.observationId][EVENTS] if x[pj_obs_fields['subject']] == self.pj[SUBJECTS][idx]['name'] and x[pj_obs_fields['code']] == sbc and x[pj_obs_fields['time']] <= currentTime]) % 2: # test if odd
                    self.currentStates[idx].append(sbc)

        # show current states
        if self.currentSubject:
            # get index of focal subject (by name)
            idx = [idx for idx in self.pj[SUBJECTS] if self.pj[SUBJECTS][idx]['name'] == self.currentSubject][0]
            self.lbCurrentStates.setText(', '.join(self.currentStates[idx]))
        else:
            self.lbCurrentStates.setText(', '.join(self.currentStates['']))

        
        self.show_current_states_in_subjects_table()

        '''
        for idx in sorted_keys(self.pj[SUBJECTS]):
            self.twSubjects.item(int(idx), len(subjectsFields)).setText(','.join(self.currentStates[idx]))
        '''

        # check scan sampling

        if "scan_sampling_time" in self.pj[OBSERVATIONS][self.observationId]:
            if self.pj[OBSERVATIONS][self.observationId]["scan_sampling_time"]:
                if  int(currentTime) % self.pj[OBSERVATIONS][self.observationId]["scan_sampling_time"] == 0:
                    app.beep()
                    self.liveTimer.stop()
                    self.textButton.setText("Live observation stopped (scan sampling)")


    def start_live_observation(self):
        """
        activate the live observation mode (without media file)
        """

        logging.debug("start live observation, self.liveObservationStarted: {}".format(self.liveObservationStarted))

        if "scan sampling" in self.textButton.text():
            self.textButton.setText("Stop live observation")
            self.liveTimer.start(100)
            return


        if not self.liveObservationStarted:

            if self.twEvents.rowCount():

                if dialog.MessageDialog(programName, "Delete the current events?", [YES, NO]) == YES:
                    self.twEvents.setRowCount(0)
                    self.pj[OBSERVATIONS][self.observationId][EVENTS] = []
                self.projectChanged = True
            self.textButton.setText("Stop live observation")
            self.liveStartTime = QTime()
            # set to now
            self.liveStartTime.start()
            # start timer
            self.liveTimer.start(100)
        else:

            self.textButton.setText("Start live observation")
            self.liveStartTime = None
            self.liveTimer.stop()

            if self.timeFormat == HHMMSS:
                self.lbTimeLive.setText("00:00:00.000")
            if self.timeFormat == S:
                self.lbTimeLive.setText("0.000")

        self.liveObservationStarted = not self.liveObservationStarted


    def create_subtitles(self):
        """
        create subtitles for selected observations, subjects and behaviors
        """

        result, selected_observations = self.selectObservations(MULTIPLE)
        if not selected_observations:
            return

        parameters = self.choose_obs_subj_behav_category(selected_observations, 0)
        if not parameters["selected subjects"] or not parameters["selected behaviors"]:
            return
        export_dir = QFileDialog(self).getExistingDirectory(self, "Choose a directory to save subtitles", os.path.expanduser("~"),
                                                            options=QFileDialog(self).ShowDirsOnly)
        if not export_dir:
            return
        ok, msg = project_functions.create_subtitles(self.pj, selected_observations, parameters, export_dir)
        if not ok:
            logging.critical(msg)
            QMessageBox.critical(None, programName, msg, QMessageBox.Ok | QMessageBox.Default, QMessageBox.NoButton)


    def export_aggregated_events(self):
        """
        export aggregated events.
        Formats can be SQL (sql), SDIS (sds) or Tabular format (tsv, csv, ods, xlsx, xls, html)
        format is selected using the filename extension
        """

        result, selectedObservations = self.selectObservations(MULTIPLE)
        if not selectedObservations:
            return

        # check if state events are paired
        out, not_paired_obs_list = "", []
        for obsId in selectedObservations:
            r, msg = project_functions.check_state_events_obs(obsId, self.pj[ETHOGRAM],
                                                              self.pj[OBSERVATIONS][obsId], self.timeFormat)
            if not r:
                out += "Observation: <strong>{obsId}</strong><br>{msg}<br>".format(obsId=obsId, msg=msg)
                not_paired_obs_list.append(obsId)
        if out:
            self.results = dialog.ResultsWidget()
            self.results.setWindowTitle(programName + " - Check selected observations")
            self.results.ptText.setReadOnly(True)
            self.results.ptText.appendHtml(out)
            self.results.show()
            return

        parameters = self.choose_obs_subj_behav_category(selectedObservations, maxTime=0, flagShowIncludeModifiers=False,
                                                         flagShowExcludeBehaviorsWoEvents=False)

        if not parameters["selected subjects"] or not parameters["selected behaviors"]:
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
            file_formats = ["tsv", "csv", "ods", "xlsx", "xls", "html", "sds", "sql"] # must be in same order than extended_file_formats
    
            if QT_VERSION_STR[0] == "4":
                fileName, filter_ = QFileDialog(self).getSaveFileNameAndFilter(self,
                                                                               "Export aggregated events",
                                                                               "", ";;".join(extended_file_formats))
            else:
                fileName, filter_ = QFileDialog(self).getSaveFileName(self, "Export aggregated events", "",
                                                                      ";;".join(extended_file_formats))

            if not fileName:
                return
    
            outputFormat = file_formats[extended_file_formats.index(filter_)]
            if pathlib.Path(fileName).suffix != "." + outputFormat:
                fileName = str(pathlib.Path(fileName)) + "." + outputFormat

        else: # not grouping

            items = ("Tab Separated Values (*.tsv)",
                     "Comma Separated values (*.csv)",
                     "Open Document Spreadsheet (*.ods)",
                     "Microsoft Excel Spreadsheet XLSX (*.xlsx)",
                     "Legacy Microsoft Excel Spreadsheet XLS (*.xls)",
                     "HTML (*.html)")
            item, ok = QInputDialog.getItem(self, "Export events format", "Available formats", items, 0, False)
            if not ok:
                return
            outputFormat = re.sub(".* \(\*\.", "", item)[:-1]

            exportDir = QFileDialog(self).getExistingDirectory(self, "Choose a directory to export events", os.path.expanduser("~"),
                                                               options=QFileDialog.ShowDirsOnly)
            if not exportDir:
                return

        if outputFormat == "sql":
            _, _, conn = db_functions.load_aggregated_events_in_db(self.pj,
                                                             parameters["selected subjects"],
                                                             selectedObservations,
                                                             parameters["selected behaviors"])
            try:
                with open(fileName, "w") as f:
                    for line in conn.iterdump():
                        f.write("{}\n".format(line))
            except:
                errorMsg = sys.exc_info()[1]
                logging.critical(errorMsg)
                QMessageBox.critical(None, programName, str(errorMsg), QMessageBox.Ok | QMessageBox.Default, QMessageBox.NoButton)
            return

        data_header = tablib.Dataset()
        data_header.title = "Aggregated events"
        header = ["Observation id", "Observation date", "Media file", "Total length", "FPS"]
        if INDEPENDENT_VARIABLES in self.pj:
            for idx in sorted_keys(self.pj[INDEPENDENT_VARIABLES]):
                header.append(self.pj[INDEPENDENT_VARIABLES][idx]["label"])
        header.extend(["Subject", "Behavior"])
        header.extend(["Modifiers"]) 
        header.extend(["Behavior type", "Start (s)", "Stop (s)", "Duration (s)", "Comment start", "Comment stop"])
        data_header.append(header)

        data = copy.deepcopy(data_header)
        for obsId in selectedObservations:
            d = export_observation.export_aggregated_events(self.pj, parameters, obsId)
            data.extend(d)

            if not flag_group:
                fileName = str(pathlib.Path(pathlib.Path(exportDir) / safeFileName(obsId)).with_suffix("." + outputFormat))
                r, msg = export_observation.dataset_write(data, fileName, outputFormat)
                if not r:
                    QMessageBox.warning(None, programName, msg, QMessageBox.Ok | QMessageBox.Default, QMessageBox.NoButton)
                data = copy.deepcopy(data_header)


        if outputFormat == "sds": # SDIS format
            out = "% SDIS file created by BORIS (www.boris.unito.it) at {}\nTimed <seconds>;\n".format(datetime_iso8601())
            for obsId in selectedObservations:
                # observation id
                out += "\n<{}>\n".format(obsId)
                dataList = list(data[1:])
                for event in sorted(dataList, key=lambda x: x[-4]):  # sort events by start time
                    if event[0] == obsId:
                        behavior = event[-7]
                        # replace various char by _
                        for char in [" ", "-", "/"]:
                            behavior = behavior.replace(char, "_")
                        subject = event[-8]
                        # replace various char by _
                        for char in [" ", "-", "/"]:
                            subject = subject.replace(char, "_")
                        event_start = "{0:.3f}".format(round(event[-4], 3))  # start event (from end for independent variables)
                        if not event[-3]:  # stop event (from end)
                            event_stop = "{0:.3f}".format(round(event[-4] + 0.001, 3))
                        else:
                            event_stop = "{0:.3f}".format(round(event[-3], 3))
                        out += "{subject}_{behavior},{start}-{stop} ".format(subject=subject, behavior=behavior, start=event_start, stop=event_stop)
                out += "/\n\n"
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

        plot_parameters = self.choose_obs_subj_behav_category(selectedObservations, maxTime=0, flagShowIncludeModifiers=False,
                                                              flagShowExcludeBehaviorsWoEvents=False)

        if not plot_parameters["selected subjects"] or not plot_parameters["selected behaviors"]:
            return

        exportDir = QFileDialog(self).getExistingDirectory(self, "Export events as TextGrid", os.path.expanduser('~'),
                                                           options=QFileDialog(self).ShowDirsOnly)
        if not exportDir:
            return

        for obsId in selectedObservations:

            out = """File type = "ooTextFile"
Object class = "TextGrid"

xmin = 0
xmax = 98.38814058956916
tiers? <exists>
size = {subjectNum}
item []:
"""
            subjectheader = """    item [{subjectIdx}]:
        class = "IntervalTier"
        name = "{subject}"
        xmin = {intervalsMin}
        xmax = {intervalsMax}
        intervals: size = {intervalsSize}
"""

            template = """        intervals [{count}]:
            xmin = {xmin}
            xmax = {xmax}
            text = "{name}"
"""

            flagUnpairedEventFound = False
            '''TO BE REMOVED  totalMediaDuration = round(self.observationTotalMediaLength(obsId), 3)'''
            totalMediaDuration = round(project_functions.observation_total_length(self.pj[OBSERVATIONS][obsId]), 3)

            cursor = db_functions.load_events_in_db(self.pj, plot_parameters["selected subjects"], selectedObservations, plot_parameters["selected behaviors"])

            cursor.execute(("SELECT count(distinct subject) FROM events "
                            "WHERE observation = '{}' AND subject in ('{}') AND type = 'STATE' ").format(obsId, "','".join(plot_parameters["selected subjects"])))
            subjectsNum = int(list(cursor.fetchall())[0][0])

            subjectsMin, subjectsMax = 0, totalMediaDuration

            out = """File type = "ooTextFile"
Object class = "TextGrid"

xmin = {subjectsMin}
xmax = {subjectsMax}
tiers? <exists>
size = {subjectsNum}
item []:
""".format(subjectsNum=subjectsNum, subjectsMin=subjectsMin, subjectsMax=subjectsMax)

            subjectIdx = 0
            for subject in plot_parameters["selected subjects"]:

                subjectIdx += 1

                cursor.execute("SELECT count(*) FROM events WHERE observation = ? AND subject = ? AND type = 'STATE' ", (obsId, subject))
                intervalsSize = int(list(cursor.fetchall())[0][0] / 2)

                intervalsMin, intervalsMax = 0, totalMediaDuration

                out += subjectheader

                cursor.execute("SELECT occurence, code FROM events WHERE observation = ? AND subject = ? AND type = 'STATE' order by occurence", (obsId, subject))

                rows = [{"occurence": float2decimal(r["occurence"]), "code": r["code"]}  for r in cursor.fetchall()]
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
                            QMessageBox.critical(None, programName, "The events are interlaced. It is not possible to produce the Praat TextGrid file", QMessageBox.Ok | QMessageBox.Default, QMessageBox.NoButton)
                            return

                        count += 1
                        out += template.format(count=count, name=row["code"], xmin=row["occurence"], xmax=rows[idx + 1]["occurence"])

                        # check if difference is > 0.001
                        if len(rows) > idx + 2:
                            if rows[idx + 2]["occurence"] - rows[idx + 1]["occurence"] > 0.001:

                                logging.debug("difference: {}-{}={}".format(rows[idx + 2]["occurence"], rows[idx + 1]["occurence"], rows[idx + 2]["occurence"] - rows[idx + 1]["occurence"]))

                                out += template.format(count=count + 1, name="null", xmin=rows[idx + 1]["occurence"], xmax=rows[idx + 2]["occurence"])
                                count += 1
                            else:
                                logging.debug("difference <=0.001: {} - {} = {}".format(rows[idx + 2]["occurence"], rows[idx + 1]["occurence"], rows[idx + 2]["occurence"] - rows[idx + 1]["occurence"]))
                                rows[idx + 2]["occurence"] = rows[idx + 1]["occurence"]
                                logging.debug("difference after: {} - {} = {}".format(rows[idx + 2]["occurence"], rows[idx + 1]["occurence"], rows[idx + 2]["occurence"] - rows[idx + 1]["occurence"]))

                # check if last event ends at the end of media file
                '''TO BE REMOVED  if rows[-1]["occurence"] < self.observationTotalMediaLength(obsId):'''
                if rows[-1]["occurence"] < project_functions.observation_total_length(self.pj[OBSERVATIONS][obsId]):
                    count += 1
                    out += template.format(count=count, name="null", xmin=rows[-1]["occurence"], xmax=totalMediaDuration)

                # add info
                out = out.format(subjectIdx=subjectIdx, subject=subject, intervalsSize=count, intervalsMin=intervalsMin, intervalsMax=intervalsMax)

            try:
                with open("{exportDir}{sep}{obsId}.textGrid".format(exportDir=exportDir, sep=os.sep, obsId=obsId), "w") as f:
                    f.write(out)

                if flagUnpairedEventFound:
                    QMessageBox.warning(self, programName, "Some state events are not paired. They were excluded from export",\
                            QMessageBox.Ok | QMessageBox.Default, QMessageBox.NoButton)

                self.statusbar.showMessage("Events exported successfully", 10000)

            except:
                errorMsg = sys.exc_info()[1]
                logging.critical(errorMsg)
                QMessageBox.critical(None, programName, str(errorMsg), QMessageBox.Ok | QMessageBox.Default, QMessageBox.NoButton)


    def media_file_info(self):
        """
        show info about media file (current media file if observation opened)
        """

        if self.observationId and self.playerType == VLC:

            media = self.mediaplayer.get_media()

            logging.info("State: {}".format(self.mediaplayer.get_state()))
            logging.info("Media (get_mrl): {}".format(bytes_to_str(media.get_mrl())))
            logging.info("media.get_meta(0): {}".format(media.get_meta(0)))
            logging.info("Track: {}/{}".format(self.mediaplayer.video_get_track(), self.mediaplayer.video_get_track_count()))
            logging.info("number of media in media list: {}".format(self.media_list.count()))
            logging.info("get time: {}  duration: {}".format(self.mediaplayer.get_time(), media.get_duration()))
            logging.info("Position: {} %".format(self.mediaplayer.get_position()))
            logging.info("FPS: {}".format(self.mediaplayer.get_fps()))
            logging.info("Rate: {}".format(self.mediaplayer.get_rate()))
            logging.info("Video size: {}".format(self.mediaplayer.video_get_size(0)))
            logging.info("Scale: {}".format(self.mediaplayer.video_get_scale()))
            logging.info("Aspect ratio: {}".format(self.mediaplayer.video_get_aspect_ratio()))
            logging.info("is seekable? {0}".format(self.mediaplayer.is_seekable()))
            logging.info("has_vout? {0}".format(self.mediaplayer.has_vout()))

            vlc_output = ("State: {}<br>"
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
                          "has_vout? {}<br>").format(self.mediaplayer.get_state(),
                                                     bytes_to_str(media.get_mrl()),
                                                     media.get_meta(0),
                                                     self.mediaplayer.video_get_track(),
                                                     self.mediaplayer.video_get_track_count(),
                                                     self.media_list.count(),
                                                     self.mediaplayer.get_time(),
                                                     self.convertTime(media.get_duration()/1000),
                                                     self.mediaplayer.get_position(),
                                                     self.mediaplayer.get_fps(),
                                                     self.mediaplayer.get_rate(),
                                                     self.mediaplayer.video_get_size(0),
                                                     self.mediaplayer.video_get_scale(),
                                                     self.mediaplayer.video_get_aspect_ratio(),
                                                     "Yes" if self.mediaplayer.is_seekable() else "No",
                                                     "Yes" if self.mediaplayer.has_vout() else "No"
                                                     )

            self.results = dialog.ResultsWidget()
            self.results.setWindowTitle(programName + " - Media file information")
            self.results.ptText.setReadOnly(True)

            self.results.ptText.appendHtml("<b>VLC analysis</b><hr>" + vlc_output)

            # FFmpeg analysis
            self.results.ptText.appendHtml("<br><b>FFmpeg analysis</b><hr>")
            for nplayer in self.pj[OBSERVATIONS][self.observationId][FILE]:
                for filePath in self.pj[OBSERVATIONS][self.observationId][FILE][nplayer]:
                    media_full_path = project_functions.media_full_path(filePath, self.projectFileName)
                    nframes, duration_ms, duration, fps, hasVideo, hasAudio = accurate_media_analysis(self.ffmpeg_bin, media_full_path)
                    if nframes == -1:
                        self.results.ptText.appendHtml("File path: {filePath}<br><br>{error}<br><br>".format(filePath=media_full_path,
                                                                                                             error=duration_ms))
                    else:
                        self.results.ptText.appendHtml("File path: {}<br>Duration: {}<br>FPS: {}<br>Has video: {}<br>Has audio: {}<br><br>".
                            format(media_full_path, self.convertTime(duration), fps, hasVideo, hasAudio))

            self.results.ptText.appendHtml("Total duration: {} (hh:mm:ss.sss)".
                format(self.convertTime(sum(self.duration) / 1000)))

            self.results.show()

        else:

            fn = QFileDialog(self).getOpenFileName(self, "Select a media file", "", "Media files (*)")
            filePath = fn[0] if type(fn) is tuple else fn

            if filePath:
                self.results = dialog.ResultsWidget()
                self.results.setWindowTitle(programName + " - Media file information")
                self.results.ptText.setReadOnly(True)
                self.results.ptText.appendHtml("<br><b>FFmpeg analysis</b><hr>")
                nframes, duration_ms, duration, fps, hasVideo, hasAudio = accurate_media_analysis(self.ffmpeg_bin, filePath)
                if nframes == -1:
                    self.results.ptText.appendHtml("File path: {filePath}<br><br>{error}<br><br>".format(filePath=filePath, error=duration_ms))
                else:
                    self.results.ptText.appendHtml("File path: {}<br>Duration: {}<br>FPS: {}<br>Has video: {}<br>Has audio: {}<br><br>".
                        format(filePath, self.convertTime(duration), fps, hasVideo, hasAudio))
                self.results.show()


    def switch_playing_mode(self):
        """
        switch between frame mode and VLC mode
        triggered by frame by frame button and toolbox item change
        """

        if self.playerType != VLC:
            return

        if self.playMode == FFMPEG:  # return to VLC mode

            self.playMode = VLC

            if hasattr(self, "frame_viewer1"):
                self.frame_viewer1_mem_geometry = self.frame_viewer1.geometry()
                del self.frame_viewer1
            if self.second_player():
                if hasattr(self, "frame_viewer2"):
                    self.frame_viewer2_mem_geometry = self.frame_viewer2.geometry()
                    del self.frame_viewer2

            globalCurrentTime = int(self.FFmpegGlobalFrame * (1000 / list(self.fps.values())[0]))

            # set on media player end
            currentMediaTime = int(sum(self.duration))

            for idx, media in enumerate(self.pj[OBSERVATIONS][self.observationId][FILE][PLAYER1]):
                if globalCurrentTime < sum(self.duration[0:idx + 1]):
                    self.mediaListPlayer.play_item_at_index(idx)
                    while True:
                        if self.mediaListPlayer.get_state() in [vlc.State.Playing, vlc.State.Ended]:
                            break
                    self.mediaListPlayer.pause()
                    currentMediaTime = int(globalCurrentTime - sum(self.duration[0:idx]))
                    break

            self.mediaplayer.set_time(currentMediaTime)

            if self.second_player():

                # set on media player2 end
                currentMediaTime2 = int(sum(self.duration2))
                globalCurrentTime2 = int(self.FFmpegGlobalFrame2 * (1000 / list(self.fps2.values())[0]))
                for idx, media in enumerate(self.pj[OBSERVATIONS][self.observationId][FILE][PLAYER2]):
                    if globalCurrentTime2 < sum(self.duration2[0:idx + 1]):
                        self.mediaListPlayer2.play_item_at_index(idx)
                        while True:
                            if self.mediaListPlayer2.get_state() in [vlc.State.Playing, vlc.State.Ended]:
                                break
                        self.mediaListPlayer2.pause()
                        currentMediaTime2 = int(globalCurrentTime2 - sum(self.duration2[0:idx]))
                        break
                self.mediaplayer2.set_time(currentMediaTime2)

            self.toolBox.setCurrentIndex(VIDEO_TAB)

            self.FFmpegTimer.stop()

            logging.info("ffmpeg timer stopped")

            # set thread for cleaning temp directory
            if self.ffmpeg_cache_dir_max_size:
                self.cleaningThread.exiting = True

        # go to frame by frame mode
        else:

            if list(self.fps.values())[0] == 0:
                logging.warning("The frame per second value is not available. Frame-by-frame mode will not be available")
                QMessageBox.critical(None, programName, "The frame per second value is not available. Frame-by-frame mode will not be available",
                    QMessageBox.Ok | QMessageBox.Default, QMessageBox.NoButton)
                self.actionFrame_by_frame.setChecked(False)
                return

            if len(set(self.fps.values())) != 1:
                logging.warning("The frame-by-frame mode will not be available because the video files have different frame rates")
                QMessageBox.warning(self, programName, ("The frame-by-frame mode will not be available"
                                                        " because the video files have different frame rates ({}).".format(
                                                         ", ".join([str(i) for i in list(self.fps.values())]))),
                    QMessageBox.Ok | QMessageBox.Default, QMessageBox.NoButton)
                self.actionFrame_by_frame.setChecked(False)
                return

            # check if FPS media player 1 != FPS media player 2
            if self.second_player():
                if list(self.fps.values())[0] != list(self.fps2.values())[0]:
                    logging.warning("The frame-by-frame mode will not be available because the video files in player #1 and player #2 have different frame rates")
                    QMessageBox.warning(self, programName, ("The frame-by-frame mode will not be available"
                                                            " because the video files have different frame rates ({} and {} FPS).".format(
                                                             list(self.fps.values())[0], list(self.fps2.values())[0])),
                                         QMessageBox.Ok | QMessageBox.Default, QMessageBox.NoButton)
                    self.actionFrame_by_frame.setChecked(False)
                    return

            self.pause_video()
            self.playMode = FFMPEG

            # check temp dir for images from ffmpeg
            if not self.ffmpeg_cache_dir:
                self.imageDirectory = tempfile.gettempdir()
            else:
                self.imageDirectory = self.ffmpeg_cache_dir

            # load list of images in a set
            if not self.imagesList:
                self.imagesList.update([f.replace(self.imageDirectory + os.sep, "").split("_")[0] for f in glob.glob(self.imageDirectory + os.sep + "BORIS@*")])

            # show frame-by_frame tab
            self.toolBox.setCurrentIndex(1)

            globalTime = (sum(self.duration[0: self.media_list.index_of_item(self.mediaplayer.get_media())]) + self.mediaplayer.get_time())

            fps = list(self.fps.values())[0]

            globalCurrentFrame = round(globalTime / (1000/fps))

            self.FFmpegGlobalFrame = globalCurrentFrame

            if self.second_player():
                globalTime2 = (sum(self.duration2[0: self.media_list2.index_of_item(self.mediaplayer2.get_media())]) + self.mediaplayer2.get_time())
                globalCurrentFrame2 = round(globalTime2 / (1000/fps))
                self.FFmpegGlobalFrame2 = globalCurrentFrame2

            if self.FFmpegGlobalFrame > 0:
                self.FFmpegGlobalFrame -= 1
            if self.second_player():
                if self.FFmpegGlobalFrame2 > 0:
                    self.FFmpegGlobalFrame2 -= 1

            self.ffmpegTimerOut()

            # set thread for cleaning temp directory
            if self.ffmpeg_cache_dir_max_size:
                self.cleaningThread.exiting = False
                self.cleaningThread.ffmpeg_cache_dir_max_size = self.ffmpeg_cache_dir_max_size * 1024 * 1024
                self.cleaningThread.tempdir = self.imageDirectory + os.sep
                self.cleaningThread.start()


        # enable/disable speed button
        self.actionNormalSpeed.setEnabled(self.playMode == VLC)
        self.actionFaster.setEnabled(self.playMode == VLC)
        self.actionSlower.setEnabled(self.playMode == VLC)

        logging.info("new play mode: {0}".format(self.playMode))

        self.menu_options()


    def snapshot(self):
        """
        take snapshot of current video
        snapshot is saved on media path
        """

        if self.pj[OBSERVATIONS][self.observationId][TYPE] in [MEDIA]:

            if self.playerType == VLC:

                if self.playMode == FFMPEG:

                    for idx, media in enumerate(self.pj[OBSERVATIONS][self.observationId][FILE][PLAYER1]):
                        if self.FFmpegGlobalFrame < sum(self.duration[0:idx + 1]):

                            p = pathlib.Path(media)
                            snapshotFilePath = str(p.parent / "{}_{}.png".format(p.stem, self.FFmpegGlobalFrame))

                            if self.detachFrameViewer or self.second_player():
                                self.frame_viewer1.lbFrame.pixmap().save(snapshotFilePath)
                            elif not self.detachFrameViewer:
                                self.lbFFmpeg.pixmap().save(snapshotFilePath)
                            self.statusbar.showMessage("Snapshot player #1 saved in {}".format(snapshotFilePath), 0)
                            break

                    if self.second_player():
                        for idx, media in enumerate(self.pj[OBSERVATIONS][self.observationId][FILE][PLAYER2]):
                            if self.FFmpegGlobalFrame2 < sum(self.duration2[0:idx + 1]):

                                p = pathlib.Path(media)
                                snapshotFilePath = str(p.parent / "{}_{}.png".format(p.stem, self.FFmpegGlobalFrame2))

                                self.frame_viewer2.lbFrame.pixmap().save(snapshotFilePath)
                                self.statusbar.showMessage("Snapshot player #2 saved in {}".format(snapshotFilePath), 0)
                                break

                else:  # VLC

                    current_media_path = url2path(self.mediaplayer.get_media().get_mrl())
                    # TODO: replace with pathlib
                    dirName, fileName = os.path.split(current_media_path)
                    self.mediaplayer.video_take_snapshot(0, "{dirName}{sep}{fileNameWOExt}_{time}.png".format(
                                                              dirName=dirName,
                                                              sep=os.sep,
                                                              fileNameWOExt=os.path.splitext(fileName)[0],
                                                              time=self.mediaplayer.get_time()),
                                                              0, 0)

                    # check if multi mode
                    # second video together
                    if self.simultaneousMedia:

                        current_media_path = url2path(self.mediaplayer2.get_media().get_mrl())

                        dirName, fileName = os.path.split(current_media_path)
                        self.mediaplayer2.video_take_snapshot(0, "{dirName}{sep}{fileNameWOExt}_{time}.png".format(
                                                              dirName=dirName,
                                                              sep=os.sep,
                                                              fileNameWOExt=os.path.splitext(fileName)[0],
                                                              time=self.mediaplayer2.get_time()),
                                                              0, 0)


    def video_zoom(self, player, zoom_value):
        """
        change video zoom
        """
        try:
            if player == 1:
                self.mediaplayer.video_set_scale(zoom_value)
            if player == 2 and self.simultaneousMedia:
                self.mediaplayer2.video_set_scale(zoom_value)
        except:
            pass

        try:
            if player == 1:
                zv = self.mediaplayer.video_get_scale()
                self.actionZoom1_fitwindow.setChecked(zv == 0)
                self.actionZoom1_1_1.setChecked(zv == 1)
                self.actionZoom1_1_2.setChecked(zv == 0.5)
                self.actionZoom1_1_4.setChecked(zv == 0.25)
                self.actionZoom1_2_1.setChecked(zv == 2)
            if player == 2 and self.simultaneousMedia:
                zv = self.mediaplayer2.video_get_scale()
                self.actionZoom2_fitwindow.setChecked(zv == 0)
                self.actionZoom2_1_1.setChecked(zv == 1)
                self.actionZoom2_1_2.setChecked(zv == 0.5)
                self.actionZoom2_1_4.setChecked(zv == 0.25)
                self.actionZoom2_2_1.setChecked(zv == 2)

        except:
            pass


    def video_normalspeed_activated(self):
        """
        set playing speed at normal speed
        """

        if self.playerType == VLC and self.playMode == VLC:
            self.play_rate = 1
            self.mediaplayer.set_rate(self.play_rate)
            # second video together
            if self.simultaneousMedia:
                self.mediaplayer2.set_rate(self.play_rate)
            self.lbSpeed.setText('x{:.3f}'.format(self.play_rate))
            logging.info('play rate: {:.3f}'.format(self.play_rate))


    def video_faster_activated(self):
        """
        increase playing speed by play_rate_step value
        """

        if self.playerType == VLC and self.playMode == VLC:

            if self.play_rate + self.play_rate_step <= 8:
                self.play_rate += self.play_rate_step
                self.mediaplayer.set_rate(self.play_rate)

                # second video together
                if self.simultaneousMedia:
                    self.mediaplayer2.set_rate(self.play_rate)
                self.lbSpeed.setText('x{:.3f}'.format(self.play_rate))

            logging.info('play rate: {:.3f}'.format(self.play_rate))


    def video_slower_activated(self):
        """
        decrease playing speed by play_rate_step value
        """

        if self.playerType == VLC and self.playMode == VLC:

            if self.play_rate - self.play_rate_step >= 0.1:
                self.play_rate -= self.play_rate_step
                self.mediaplayer.set_rate(self.play_rate)

                # second video together
                if self.simultaneousMedia:
                    self.mediaplayer2.set_rate(self.play_rate)

                self.lbSpeed.setText('x{:.3f}'.format(self.play_rate))

            logging.info('play rate: {:.3f}'.format(self.play_rate))


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
                    else:
                        memState = self.mediaListPlayer.get_state()
                        if memState == vlc.State.Playing:
                            self.pause_video()

        laps = self.getLaps()

        if not self.pj[ETHOGRAM]:
            QMessageBox.warning(self, programName, "The ethogram is not set!")
            return

        editWindow = DlgEditEvent(logging.getLogger().getEffectiveLevel())
        editWindow.setWindowTitle("Add a new event")

        # send pj to edit_event window
        editWindow.pj = self.pj

        if self.timeFormat == HHMMSS:
            editWindow.dsbTime.setVisible(False)
            editWindow.teTime.setTime(QtCore.QTime.fromString(seconds2time(laps), HHMMSSZZZ))

        if self.timeFormat == S:
            editWindow.teTime.setVisible(False)
            editWindow.dsbTime.setValue(float(laps))

        sortedSubjects = [""] + sorted([self.pj[SUBJECTS][x]["name"] for x in self.pj[SUBJECTS]])

        editWindow.cobSubject.addItems(sortedSubjects)

        sortedCodes = sorted([self.pj[ETHOGRAM][x]["code"] for x in self.pj[ETHOGRAM]])

        editWindow.cobCode.addItems(sortedCodes)

        # activate signal
        #editWindow.cobCode.currentIndexChanged.connect(editWindow.codeChanged)

        editWindow.currentModifier = ""

        if editWindow.exec_():  #button OK

            if self.timeFormat == HHMMSS:
                newTime = time2seconds(editWindow.teTime.time().toString(HHMMSSZZZ))

            if self.timeFormat == S:
                newTime = Decimal(editWindow.dsbTime.value())

            for obs_idx in self.pj[ETHOGRAM]:
                if self.pj[ETHOGRAM][obs_idx]["code"] == editWindow.cobCode.currentText():

                    event = self.full_event(obs_idx)

                    event["subject"] = editWindow.cobSubject.currentText()
                    if editWindow.leComment.toPlainText():
                        event["comment"] = editWindow.leComment.toPlainText()

                    self.writeEvent(event, newTime)
                    break

        if self.pause_before_addevent:
            # restart media
            if self.pj[OBSERVATIONS][self.observationId][TYPE] in [MEDIA]:
                if self.playerType == VLC:
                    if self.playMode == FFMPEG:
                        if memState:
                            self.play_video()
                    else:
                        if memState == vlc.State.Playing:
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
                durations.append(self.pj[OBSERVATIONS][self.observationId]["media_info"]["length"][mediaFile])

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
                                                                MEDIA_PATH='"{}"'.format(media_path),
                                                                MEDIA_BASENAME='"{}"'.format(os.path.basename(media_path)),
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
            args = [ex, "-f",os.path.abspath(fn),"--seekmsec",str(int(eventtimeS*1000)),*q,*("--size 1 --track 1 --redetect 100").split(" ")]
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
        edit each event items from the selected row
        """
        if not self.observationId:
            self.no_observation()
            return

        if self.twEvents.selectedItems():

            editWindow = DlgEditEvent(logging.getLogger().getEffectiveLevel())
            editWindow.setWindowTitle("Edit event parameters")

            # pass project to window
            editWindow.pj = self.pj
            editWindow.currentModifier = ""

            row = self.twEvents.selectedItems()[0].row()

            if self.timeFormat == HHMMSS:
                editWindow.dsbTime.setVisible(False)
                editWindow.teTime.setTime(QtCore.QTime.fromString(seconds2time(self.pj[OBSERVATIONS][self.observationId][EVENTS][row][0]), HHMMSSZZZ))

            if self.timeFormat == S:
                editWindow.teTime.setVisible(False)
                editWindow.dsbTime.setValue(self.pj[OBSERVATIONS][self.observationId][EVENTS][row][0])

            sortedSubjects = [""] + sorted([self.pj[SUBJECTS][x]["name"] for x in self.pj[SUBJECTS]])

            editWindow.cobSubject.addItems(sortedSubjects)

            if self.pj[OBSERVATIONS][self.observationId][EVENTS][row][EVENT_SUBJECT_FIELD_IDX] in sortedSubjects:
                editWindow.cobSubject.setCurrentIndex(sortedSubjects.index(self.pj[OBSERVATIONS][self.observationId][EVENTS][row][EVENT_SUBJECT_FIELD_IDX]))
            else:
                QMessageBox.warning(self, programName, "The subject <b>{}</b> does not exist more in the subject's list".
                    format(self.pj[OBSERVATIONS][self.observationId][EVENTS][row][EVENT_SUBJECT_FIELD_IDX]))
                editWindow.cobSubject.setCurrentIndex(0)

            sortedCodes = sorted([self.pj[ETHOGRAM][x]["code"] for x in self.pj[ETHOGRAM]])

            editWindow.cobCode.addItems(sortedCodes)

            # check if selected code is in code's list (no modification of codes)
            if self.pj[OBSERVATIONS][self.observationId][EVENTS][row][EVENT_BEHAVIOR_FIELD_IDX] in sortedCodes:
                editWindow.cobCode.setCurrentIndex(sortedCodes.index(self.pj[OBSERVATIONS][self.observationId][EVENTS][row][EVENT_BEHAVIOR_FIELD_IDX]))
            else:
                logging.warning("The behaviour <b>{0}</b> does not exists more in the ethogram".
                    format(self.pj[OBSERVATIONS][self.observationId][EVENTS][row][EVENT_BEHAVIOR_FIELD_IDX]))
                QMessageBox.warning(self, programName, "The behaviour <b>{}</b> does not exist more in the ethogram".
                    format(self.pj[OBSERVATIONS][self.observationId][EVENTS][row][EVENT_BEHAVIOR_FIELD_IDX]))
                editWindow.cobCode.setCurrentIndex(0)

            logging.debug("original modifiers: {}".
                format(self.pj[OBSERVATIONS][self.observationId][EVENTS][row][EVENT_MODIFIER_FIELD_IDX]))

            # comment
            editWindow.leComment.setPlainText(self.pj[OBSERVATIONS][self.observationId][EVENTS][row][EVENT_COMMENT_FIELD_IDX])

            if editWindow.exec_():  #button OK

                self.projectChanged = True

                if self.timeFormat == HHMMSS:
                    newTime = time2seconds(editWindow.teTime.time().toString(HHMMSSZZZ))

                if self.timeFormat == S:
                    newTime = Decimal(str(editWindow.dsbTime.value()))

                for key in self.pj[ETHOGRAM]:
                    if self.pj[ETHOGRAM][key]["code"] == editWindow.cobCode.currentText():
                        event = self.full_event(key)
                        event["subject"] = editWindow.cobSubject.currentText()
                        event["comment"] = editWindow.leComment.toPlainText()
                        event["row"] = row
                        event["original_modifiers"] = self.pj[OBSERVATIONS][self.observationId][EVENTS][row][pj_obs_fields["modifier"]]

                        self.writeEvent(event, newTime)
                        break

        else:
            QMessageBox.warning(self, programName, "Select an event to edit")


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
            if self.twEthogram.selectedIndexes():
                ethogramRow = self.twEthogram.selectedIndexes()[0].row()
                code = self.twEthogram.item(ethogramRow, 1).text()
                event = self.full_event(str(ethogramRow))
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
                behavior_idx = [key for key in  self.pj[ETHOGRAM] if self.pj[ETHOGRAM][key]["code"] == code][0]
            except:
                QMessageBox.critical(self, programName, "The code <b>{}</b> of behavior coding map do not exists in ethogram.".format(code))
                return

            event = self.full_event(behavior_idx)
            self.writeEvent(event, self.getLaps())


    def keypress_signal_from_behaviors_coding_map(self, event):
        """
        receive signal from behaviors coding map
        """
        self.keyPressEvent(event)


    def close_behaviors_coding_map(self, coding_map_name):
        
        del self.bcm_dict[coding_map_name]
        
        if hasattr(self, "bcm"):
            '''
            print("del bcm")

            self.bcm.clickSignal.disconnect()
            self.bcm.keypressSignal.disconnect()
            self.bcm.close_signal.disconnect()
            
            self.bcm.deleteLater()
            #del self.bcm
            '''
            """TO DO: fix this"""
            print('hasattr(self, "bcm")', hasattr(self, "bcm"))


    def show_behaviors_coding_map(self):
        """
        show a behavior coding map
        """

        if BEHAVIORS_CODING_MAP not in self.pj or not self.pj[BEHAVIORS_CODING_MAP]:
            QMessageBox.warning(self, programName, "No behaviors coding map found in current project")
            return

        items = [x["name"] for x in  self.pj[BEHAVIORS_CODING_MAP]]   
        if len(items) == 1:
            coding_map_name = items[0]
        else:
            item, ok = QInputDialog.getItem(self, "Select a coding map", "list of coding maps", items, 0, False)
            if ok and item:
                coding_map_name = item
            else:
                return
        
        if coding_map_name in self.bcm_dict:
            self.bcm_dict[coding_map_name].show()
        else:
            self.bcm_dict[coding_map_name] = behaviors_coding_map.BehaviorsCodingMapWindowClass(
                                                        self.pj[BEHAVIORS_CODING_MAP][items.index(coding_map_name)],
                                                        idx=items.index(coding_map_name))

            self.bcm_dict[coding_map_name].clickSignal.connect(self.click_signal_from_behaviors_coding_map)

            self.bcm_dict[coding_map_name].close_signal.connect(self.close_behaviors_coding_map)

            self.bcm_dict[coding_map_name].resize(CODING_MAP_RESIZE_W, CODING_MAP_RESIZE_W)
            self.bcm_dict[coding_map_name].setWindowFlags(Qt.WindowStaysOnTopHint)
            self.bcm_dict[coding_map_name].show()


    def actionAbout_activated(self):
        """
        About dialog
        """

        ver = 'v. {0}'.format(__version__)

        players = []
        players.append("VLC media player")
        players.append("version {}".format(bytes_to_str(vlc.libvlc_get_version())))
        if vlc.plugin_path:
            players.append("VLC libraries path: {}".format(vlc.plugin_path))

        players.append("\nFFmpeg")
        players.append(subprocess.getoutput('"{}" -version'.format(self.ffmpeg_bin)).split("\n")[0])
        if self.ffmpeg_bin == "ffmpeg" and sys.platform.startswith("linux"):
            ffmpeg_true_path = subprocess.getoutput("which ffmpeg")
        else:
            ffmpeg_true_path = self.ffmpeg_bin
        players.append("Path: {}".format(ffmpeg_true_path))

        # matplotlib
        players.append("\nMatplotlib")
        players.append("version {}".format(matplotlib.__version__))

        # graphviz
        gv_result = subprocess.getoutput("dot -V")
        gv_version = gv_result if "graphviz" in gv_result else "not installed"
        players.append("\nGraphViz")
        players.append(gv_version)

        about_dialog = msg = QMessageBox()
        about_dialog.setIconPixmap(QPixmap(os.path.dirname(os.path.realpath(__file__)) + "/logo_eye.128px.png"))
        about_dialog.setWindowTitle("About " + programName)
        about_dialog.setStandardButtons(QMessageBox.Ok)
        about_dialog.setDefaultButton(QMessageBox.Ok)
        about_dialog.setEscapeButton(QMessageBox.Ok)

        about_dialog.setInformativeText(("<b>{prog_name}</b> {ver} - {date}"
        "<p>Copyright &copy; 2012-2018 Olivier Friard - Marco Gamba<br>"
        "Department of Life Sciences and Systems Biology<br>"
        "University of Torino - Italy<br>"
        "<br>"
        """BORIS is released under the <a href="http://www.gnu.org/copyleft/gpl.html">GNU General Public License</a><br>"""
        """See <a href="http://www.boris.unito.it">www.boris.unito.it</a> for more details.<br>"""
        "<br>"
        "The authors would like to acknowledge Sergio Castellano, Valentina Matteucci and Laura Ozella for their precious help."
        "<hr>"
        "How to cite BORIS:<br>"
        "Friard, O. and Gamba, M. (2016), BORIS: a free, versatile open-source event-logging software for video/audio "
        "coding and live observations. Methods Ecol Evol, 7: 1325–1330.<br>"
        "DOI:10.1111/2041-210X.12584").format(prog_name=programName,
                                              ver=ver,
                                              date=__version_date__,
                                              python_ver=platform.python_version()
                                              ))

        details = ("Python {python_ver} ({architecture}) - Qt {qt_ver} - PyQt{pyqt_ver} on {system}\n"
        "CPU type: {cpu_info}\n\n"
        "{players}").format(python_ver=platform.python_version(),
                            architecture="64-bit" if sys.maxsize > 2**32 else "32-bit",
                            pyqt_ver=PYQT_VERSION_STR,
                            system=platform.system(),
                            qt_ver=QT_VERSION_STR,
                            cpu_info=platform.machine(),
                            players="\n".join(players))

        about_dialog.setDetailedText(details)

        _ = about_dialog.exec_()


    def hsVideo_sliderMoved(self):
        """
        media position slider moved
        adjust media position
        """

        if self.pj[OBSERVATIONS][self.observationId][TYPE] in [MEDIA]:

            if self.playerType == VLC and self.playMode == VLC:
                sliderPos = self.hsVideo.value() / (slider_maximum - 1)
                videoPosition = sliderPos * self.mediaplayer.get_length()
                self.mediaplayer.set_time(int(videoPosition))
                # second video together
                if self.simultaneousMedia:
                    # synchronize 2nd player
                    self.mediaplayer2.set_time(int(self.mediaplayer.get_time()
                                   - self.pj[OBSERVATIONS][self.observationId][TIME_OFFSET_SECOND_PLAYER] * 1000))
                self.timer_out(scrollSlider=False)
                self.timer_spectro_out()


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
                         if x[0] <= ct and self.pj[OBSERVATIONS][self.observationId][EVENTS][idx+1][0] > ct]

                if cr_list:
                    ROW = cr_list[0]
                    if not self.trackingCursorAboveEvent:
                        ROW +=  1
                else:
                    ROW = -1

            self.twEvents.setItemDelegate(StyledItemDelegateTriangle(self.twEvents))
            self.twEvents.scrollToItem(self.twEvents.item(ROW, 0))


    def get_current_states_by_subject(self, stateBehaviorsCodes, events, subjects, time):
        """
        get current states for subjects at given time
        Args:
            stateBehaviorsCodes (list): list of behavior codes defined as STATE event
            events (list): list of events
            subjects (list): list of subjects
            time (Decimal): time

        Returns:
            dict: current states by subject. dict of list
        """
        currentStates = {}
        for idx in subjects:
            currentStates[idx] = []
            for sbc in stateBehaviorsCodes:
                if len([x[EVENT_BEHAVIOR_FIELD_IDX] for x in events
                                                       if x[EVENT_SUBJECT_FIELD_IDX] == subjects[idx]["name"]
                                                          and x[EVENT_BEHAVIOR_FIELD_IDX] == sbc
                                                          and x[EVENT_TIME_FIELD_IDX] <= time]) % 2: # test if odd
                    currentStates[idx].append(sbc)
        return currentStates


    def show_current_states_in_subjects_table(self):
        for idx in sorted_keys(self.pj[SUBJECTS]):
            for j in range(self.twSubjects.rowCount()):
                if self.twSubjects.item(j, 1).text() == self.pj[SUBJECTS][idx]["name"]:
                    self.twSubjects.item(j, len(subjectsFields)).setText(",".join(self.currentStates[idx]))


    def timer_out(self, scrollSlider=True):
        """
        indicate the video current position and total length for VLC player
        scroll video slider to video position
        Time offset is NOT added!
        triggered by timer
        """

        if not self.observationId:
            return

        if self.pj[OBSERVATIONS][self.observationId][TYPE] in [MEDIA]:

            # cumulative time
            currentTime = self.getLaps() * 1000

            if self.beep_every:
                if currentTime % (self.beep_every * 1000) <= 300:
                    self.beep(" -f 555 -l 460")

            # current media time
            try:
                mediaTime = self.mediaplayer.get_time()
            except:
                return

            # highlight current event in tw events and scroll event list
            self.get_events_current_row()

            # check if second video
            if self.simultaneousMedia:

                if TIME_OFFSET_SECOND_PLAYER in self.pj[OBSERVATIONS][self.observationId]:

                    # sync 2nd player on 1st player when no offset
                    if self.pj[OBSERVATIONS][self.observationId][TIME_OFFSET_SECOND_PLAYER] == 0:
                        t1, t2 = self.mediaplayer.get_time(), self.mediaplayer2.get_time()
                        if abs(t1 - t2) >= 300:
                            self.mediaplayer2.set_time(t1)

                    if self.pj[OBSERVATIONS][self.observationId][TIME_OFFSET_SECOND_PLAYER] > 0:

                        if mediaTime < self.pj[OBSERVATIONS][self.observationId][TIME_OFFSET_SECOND_PLAYER] * 1000:

                            if self.mediaListPlayer2.get_state() == vlc.State.Playing:
                                self.mediaplayer2.set_time(0)
                                self.mediaListPlayer2.pause()
                        else:
                            if self.mediaListPlayer.get_state() == vlc.State.Playing:
                                t1, t2 = self.mediaplayer.get_time(), self.mediaplayer2.get_time()
                                if abs((t1 - t2) - self.pj[OBSERVATIONS][self.observationId][TIME_OFFSET_SECOND_PLAYER] * 1000) >= 300:  # synchr if diff >= 300 ms
                                    self.mediaplayer2.set_time(int(t1 - self.pj[OBSERVATIONS][self.observationId][TIME_OFFSET_SECOND_PLAYER] * 1000))
                                self.mediaListPlayer2.play()

                    if self.pj[OBSERVATIONS][self.observationId][TIME_OFFSET_SECOND_PLAYER] < 0:
                        mediaTime2 = self.mediaplayer2.get_time()

                        if mediaTime2 < abs(self.pj[OBSERVATIONS][self.observationId][TIME_OFFSET_SECOND_PLAYER] * 1000):

                            if self.mediaListPlayer.get_state() == vlc.State.Playing:
                                self.mediaplayer.set_time(0)
                                self.mediaListPlayer.pause()
                        else:
                            if self.mediaListPlayer2.get_state() == vlc.State.Playing:
                                t1, t2 = self.mediaplayer.get_time(), self.mediaplayer2.get_time()
                                if abs((t2 - t1) + self.pj[OBSERVATIONS][self.observationId][TIME_OFFSET_SECOND_PLAYER] * 1000) >= 300:  # synchr if diff >= 300 ms
                                    self.mediaplayer.set_time(int(t2 + self.pj[OBSERVATIONS][self.observationId][TIME_OFFSET_SECOND_PLAYER] * 1000))
                                self.mediaListPlayer.play()

            currentTimeOffset = Decimal(currentTime / 1000) + Decimal(self.pj[OBSERVATIONS][self.observationId][TIME_OFFSET])

            totalGlobalTime = sum(self.duration)

            mediaName = ""

            if self.mediaplayer.get_length():

                self.mediaTotalLength = self.mediaplayer.get_length() / 1000
                
                '''
                if abs(self.mediaTotalLength - totalGlobalTime / 1000) > 10:
                    self.timer.stop()
                    #self.pause_video()
                    if not self.wrongTimeResponse:
                        self.wrongTimeResponse = dialog.MessageDialog(programName,
                                                                      ("The VLC media file duration seems to be wrong:<br>"
                                                                      "{} instead of {}.<br><br>"
                                                                      "It should be safer to close the current observation"
                                                                      " and re-encode your media file with the BORIS tool<br>"
                                                                      "See Tools > Re-encode / resize video").
                                                                        format(self.convertTime(self.mediaTotalLength),
                                                                               self.convertTime(totalGlobalTime/1000)), [OK])

                    """
                    if response == "Close observation":
                        try:
                            self.close_observation()
                            return False
                        except:
                            pass
                    """
                '''
                # current state(s)
                # extract State events
                StateBehaviorsCodes = state_behavior_codes(self.pj[ETHOGRAM])

                self.currentStates = {}

                # add current states for all subject and for "no focal subject"

                self.currentStates = self.get_current_states_by_subject(StateBehaviorsCodes,
                                                                        self.pj[OBSERVATIONS][self.observationId][EVENTS],
                                                                        dict(self.pj[SUBJECTS], **{"": {"name": ""}}),
                                                                        currentTimeOffset)

                # show current subject
                cm = {}
                if self.currentSubject:
                    # get index of focal subject (by name)
                    idx = [idx for idx in self.pj[SUBJECTS] if self.pj[SUBJECTS][idx]["name"] == self.currentSubject][0]
                else:
                    idx = ""

                # show current state(s)
                txt = []
                for cs in self.currentStates[idx]:
                    for ev in self.pj[OBSERVATIONS][self.observationId][EVENTS]:
                        if ev[EVENT_TIME_FIELD_IDX] > currentTimeOffset:
                            break
                        if ev[EVENT_SUBJECT_FIELD_IDX] == self.currentSubject:
                            if ev[EVENT_BEHAVIOR_FIELD_IDX] == cs:
                                cm[cs] = ev[EVENT_MODIFIER_FIELD_IDX]
                    # state and modifiers (if any)
                    txt.append(cs + " ({}) ".format(cm[cs])*(cm[cs] != ""))

                txt = ", ".join(txt)

                self.lbCurrentStates.setText(re.sub(" \(.*\)", "", txt))

                # show current states in subjects table
                self.show_current_states_in_subjects_table()

                mediaName = self.mediaplayer.get_media().get_meta(0)

                # update status bar
                msg = ""
                if self.mediaListPlayer.get_state() == vlc.State.Playing or self.mediaListPlayer.get_state() == vlc.State.Paused:
                    msg = "{media_name}: <b>{time} / {total_time}</b>".format(media_name=mediaName,
                                                                              time=self.convertTime(Decimal(mediaTime / 1000)),
                                                                              total_time=self.convertTime(Decimal(self.mediaTotalLength)))

                    if self.media_list.count() > 1:
                        msg += " | total: <b>%s / %s</b>" % ((self.convertTime(Decimal(currentTime / 1000)),
                                                               self.convertTime(Decimal(totalGlobalTime / 1000))))
                    if self.mediaListPlayer.get_state() == vlc.State.Paused:
                        msg += " (paused)"

                if msg:
                    # show time
                    self.lbTime.setText(msg)
                    self.lb_current_media_time.setText(msg)

                    # set video scroll bar
                    if scrollSlider:
                        self.hsVideo.setValue(mediaTime / self.mediaplayer.get_length() * (slider_maximum - 1))
            else:
                self.statusbar.showMessage("Media length not available now", 0)

            if (self.memMedia and mediaName != self.memMedia) or (self.mediaListPlayer.get_state() == vlc.State.Ended and self.timer.isActive()):

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

                            '''event = {"subject": subjName, "code": behav, "modifiers": cm, "comment": "", "excluded": ""}'''

                            end_time = currentTime / 1000 - Decimal("0.001")

                            self.pj[OBSERVATIONS][self.observationId][EVENTS].append([end_time, subjName, behav, cm, ""])
                            self.loadEventsInTW(self.observationId)
                            item = self.twEvents.item([i for i, t in enumerate(self.pj[OBSERVATIONS][self.observationId][EVENTS]) if t[0] == end_time][0], 0)
                            self.twEvents.scrollToItem(item)
                            self.projectChanged = True

            self.memMedia = mediaName

            if self.mediaListPlayer.get_state() == vlc.State.Ended:
                self.timer.stop()


    def load_behaviors_in_twEthogram(self, behaviorsToShow):
        """
        fill ethogram table with ethogram from pj
        """

        self.twEthogram.setRowCount(0)
        if self.pj[ETHOGRAM]:
            for idx in sorted_keys(self.pj[ETHOGRAM]):
                if self.pj[ETHOGRAM][idx]["code"] in behaviorsToShow:
                    self.twEthogram.setRowCount(self.twEthogram.rowCount() + 1)
                    for col in sorted(behav_fields_in_mainwindow.keys()):
                        field = behav_fields_in_mainwindow[col]
                        self.twEthogram.setItem(self.twEthogram.rowCount() - 1, col, QTableWidgetItem(str(self.pj[ETHOGRAM][idx][field])))
        if self.twEthogram.rowCount() < len(self.pj[ETHOGRAM].keys()):
            self.dwEthogram.setWindowTitle("Ethogram (filtered {0}/{1})".format(self.twEthogram.rowCount(), len(self.pj[ETHOGRAM].keys())))

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

        self.twSubjects.setRowCount(0)
        if self.pj[SUBJECTS]:
            for idx in sorted_keys(self.pj[SUBJECTS]):
                if self.pj[SUBJECTS][idx]["name"] in subjects_to_show:

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

        stateEventsList = [self.pj[ETHOGRAM][x][BEHAVIOR_CODE] for x in self.pj[ETHOGRAM] if STATE in self.pj[ETHOGRAM][x][TYPE].upper()]

        for row in range(0, self.twEvents.rowCount()):

            t = self.twEvents.item(row, tw_obs_fields["time"]).text()

            if ":" in t:
                time = time2seconds(t)
            else:
                time = Decimal(t)

            subject = self.twEvents.item(row, tw_obs_fields["subject"]).text()
            code = self.twEvents.item(row, tw_obs_fields["code"]).text()
            modifier = self.twEvents.item(row, tw_obs_fields["modifier"]).text()

            # check if code is state
            if code in stateEventsList:
                # how many code before with same subject?
                nbEvents = len([event[EVENT_BEHAVIOR_FIELD_IDX] for event in self.pj[OBSERVATIONS][self.observationId][EVENTS]
                                                                  if event[EVENT_BEHAVIOR_FIELD_IDX] == code
                                                                     and event[EVENT_TIME_FIELD_IDX] < time
                                                                     and event[EVENT_SUBJECT_FIELD_IDX] == subject
                                                                     and event[EVENT_MODIFIER_FIELD_IDX] == modifier])

                if nbEvents and (nbEvents % 2): # test >0 and  odd
                    self.twEvents.item(row, tw_obs_fields[TYPE]).setText(STOP)
                else:
                    self.twEvents.item(row, tw_obs_fields[TYPE]).setText(START)


    def checkSameEvent(self, obsId, time, subject, code):
        """
        check if a same event is already in events list (time, subject, code)
        """
        return [time, subject, code] in [[x[EVENT_TIME_FIELD_IDX], x[EVENT_SUBJECT_FIELD_IDX], x[EVENT_BEHAVIOR_FIELD_IDX]]
                                            for x in self.pj[OBSERVATIONS][obsId][EVENTS]]


    def writeEvent(self, event, memTime):
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

        logging.debug("write event - event: {0}  memtime: {1}".format(event, memTime))
        try:
            if event is None:
                return
    
            # add time offset if not from editing
            if "row" not in event:
                memTime += Decimal(self.pj[OBSERVATIONS][self.observationId][TIME_OFFSET]).quantize(Decimal(".001"))
    
            # check if a same event is already in events list (time, subject, code)
            # "row" present in case of event editing
    
            if "row" not in event and self.checkSameEvent(self.observationId, memTime, self.currentSubject, event["code"]):
                _ = dialog.MessageDialog(programName, "The same event already exists (same time, behavior code and subject).", [OK])
                return
    
            if not "from map" in event:   # modifiers only for behaviors without coding map
                # check if event has modifiers
                modifier_str = ""
    
                if event["modifiers"]:
                    # pause media
                    if self.pj[OBSERVATIONS][self.observationId][TYPE] in [MEDIA]:
                        if self.playerType == VLC:
                            if self.playMode == FFMPEG:
                                memState = self.FFmpegTimer.isActive()
                                if memState:
                                    self.pause_video()
                            else:
                                memState = self.mediaListPlayer.get_state()
                                if memState == vlc.State.Playing:
                                    self.pause_video()
    
                    # check if editing (original_modifiers key)
                    currentModifiers = event["original_modifiers"] if "original_modifiers" in event else ""
    
                    modifierSelector = select_modifiers.ModifiersList(event["code"], eval(str(event["modifiers"])), currentModifiers)
    
                    if modifierSelector.exec_():
                        selected_modifiers = modifierSelector.getModifiers()
    
                        modifier_str = ""
                        for idx in sorted_keys(selected_modifiers):
                            if modifier_str:
                                modifier_str += "|"
                            if selected_modifiers[idx]["type"] in [SINGLE_SELECTION, MULTI_SELECTION]:
                                modifier_str += ",".join(selected_modifiers[idx]["selected"])
                            if selected_modifiers[idx]["type"] in [NUMERIC_MODIFIER]:
                                modifier_str += selected_modifiers[idx]["selected"]
                    else:
                        modifier_str = currentModifiers
    
                    # restart media
                    if self.pj[OBSERVATIONS][self.observationId][TYPE] in [MEDIA]:
                        if self.playerType == VLC:
                            if self.playMode == FFMPEG:
                                if memState:
                                    self.play_video()
                            else:
                                if memState == vlc.State.Playing:
                                    self.play_video()
    
            else:
                modifier_str = event["from map"]
    
            # update current state
            if "row" not in event: # no editing
                if self.currentSubject:
                    csj = []
                    for idx in self.currentStates:
                        if idx in self.pj[SUBJECTS] and self.pj[SUBJECTS][idx]["name"] == self.currentSubject:
                            csj = self.currentStates[idx]
                            break
    
                else:  # no focal subject
                    try:
                        csj = self.currentStates[""]
                    except:
                        csj = []
    
                cm = {} # modifiers for current behaviors
                for cs in csj:
                    for ev in self.pj[OBSERVATIONS][self.observationId][EVENTS]:
                        if ev[EVENT_TIME_FIELD_IDX] > memTime:
                            break
    
                        if ev[EVENT_SUBJECT_FIELD_IDX] == self.currentSubject:
                            if ev[EVENT_BEHAVIOR_FIELD_IDX] == cs:
                                cm[cs] = ev[EVENT_MODIFIER_FIELD_IDX]

                for cs in csj:
                    # close state if same state without modifier
                    if self.close_the_same_current_event and (event["code"] == cs) and modifier_str.replace("None", "").replace("|", "") == "":
                        modifier_str = cm[cs]
                        continue
    
                    if (event["excluded"] and cs in event["excluded"].split(",")) or (event["code"] == cs and cm[cs] != modifier_str):
                        # add excluded state event to observations (= STOP them)
                        self.pj[OBSERVATIONS][self.observationId][EVENTS].append([memTime - Decimal("0.001"), self.currentSubject, cs, cm[cs], ""])

            # remove key code from modifiers
            modifier_str = re.sub(" \(.*\)", "", modifier_str)
    
            comment = event["comment"] if "comment" in event else ""
            subject = event["subject"] if "subject" in event else ""
    
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
            item = self.twEvents.item([i for i, t in enumerate(self.pj[OBSERVATIONS][self.observationId][EVENTS]) if t[0] == memTime][0], 0)
            self.twEvents.scrollToItem(item)
            self.projectChanged = True
        except:
            dialog.MessageDialog(programName, "Even can not be recorded.\nError: {}".format(sys.exc_info()[1]) , [OK])
            


    def fill_lwDetailed(self, obs_key, memLaps):
        """
        fill listwidget with all events coded by key
        return index of behaviour
        """

        # check if key duplicated
        items = []
        for idx in self.pj[ETHOGRAM]:
            if self.pj[ETHOGRAM][idx]["key"] == obs_key:

                code_descr = self.pj[ETHOGRAM][idx]["code"]
                if  self.pj[ETHOGRAM][idx]["description"]:
                    code_descr += " - " + self.pj[ETHOGRAM][idx]["description"]
                items.append(code_descr)
                self.detailedObs[code_descr] = idx

        items.sort()

        dbc = dialog.DuplicateBehaviorCode("The <b>{}</b> key codes more behaviors.<br>Choose the correct one:".format(obs_key), items)
        if dbc.exec_():
            code = dbc.getCode()
            if code:
                return self.detailedObs[code]
            else:
                return None


    def getLaps(self):
        """Cumulative laps time from begining of observation
        no more add time offset!

        Args:
        
        Returns:
            decimal: cumulative time in seconds

        """

        if self.pj[OBSERVATIONS][self.observationId]["type"] in [LIVE]:

            if self.liveObservationStarted:
                now = QTime()
                now.start()  # current time
                memLaps = Decimal(str(round(self.liveStartTime.msecsTo(now) / 1000, 3)))
                return memLaps
            else:
                return Decimal("0.0")

        if self.pj[OBSERVATIONS][self.observationId]["type"] in [MEDIA]:

            if self.playerType == VIEWER:
                return Decimal(0)

            if self.playerType == VLC:
                if self.playMode == FFMPEG:
                    # cumulative time
                    memLaps = Decimal(self.FFmpegGlobalFrame * (1000 / list(self.fps.values())[0]) / 1000).quantize(Decimal(".001"))
                    return memLaps
                else: # playMode == VLC
                    # cumulative time
                    memLaps = Decimal(str(round((sum(self.duration[0: self.media_list.index_of_item(self.mediaplayer.get_media())]) +
                              self.mediaplayer.get_time()) / 1000, 3)))
                    return memLaps


    def full_event(self, behavior_idx):
        """
        input: behavior index in ethogram
        return: event (dict)

        ask modifiers from coding map if configured and add them under 'from map' key
        """

        event = dict(self.pj[ETHOGRAM][behavior_idx])
        # check if coding map
        if "coding map" in self.pj[ETHOGRAM][behavior_idx] and self.pj[ETHOGRAM][behavior_idx]["coding map"]:

            # pause if media and media playing
            if self.pj[OBSERVATIONS][self.observationId][TYPE] in [MEDIA]:
                if self.playerType == VLC:
                    memState = self.mediaListPlayer.get_state()
                    if memState == vlc.State.Playing:
                        self.pause_video()

            self.codingMapWindow = modifiers_coding_map.ModifiersCodingMapWindowClass(self.pj["coding_map"][self.pj[ETHOGRAM][behavior_idx]["coding map"]])

            self.codingMapWindow.resize(CODING_MAP_RESIZE_W, CODING_MAP_RESIZE_H)
            if self.codingMapWindowGeometry:
                 self.codingMapWindow.restoreGeometry(self.codingMapWindowGeometry)

            if not self.codingMapWindow.exec_():
                return

            self.codingMapWindowGeometry = self.codingMapWindow.saveGeometry()

            event["from map"] = self.codingMapWindow.getCodes()

            # restart media
            if self.pj[OBSERVATIONS][self.observationId][TYPE] in [MEDIA]:
                if self.playerType == VLC:
                    if memState == vlc.State.Playing:
                        self.play_video()

        return event


    def frame_backward(self):
        """
        go one frame back
        """

        if self.playMode == FFMPEG:
            logging.debug("current frame {0}".format(self.FFmpegGlobalFrame))
            if self.FFmpegGlobalFrame > 1:
                self.FFmpegGlobalFrame -= 2
                self.ffmpegTimerOut()
                logging.debug("new frame {0}".format(self.FFmpegGlobalFrame))


    def frame_forward(self):
        """
        go one frame forward
        """
        if self.playMode == FFMPEG:
            self.ffmpegTimerOut()


    def beep(self, parameters):
        """
        emit beep on various platform
        """
        if sys.platform.startswith("linux"):
            #os.system("beep {}".format(parameters))
            app.beep()
        else:
            app.beep()

    def keyPressEvent(self, event):

        logging.debug("text #{0}#  event key: {1} ".format(event.text(), event.key()))

        '''
        if (event.modifiers() & Qt.ShiftModifier):   # SHIFT

        QApplication.keyboardModifiers()

        http://qt-project.org/doc/qt-5.0/qtcore/qt.html#Key-enum

        ESC: 16777216
        '''

        if self.playMode == VLC:
            self.timer_out()

        if not self.observationId:
            return

        # beep
        if self.confirmSound:
            self.beep("")

        if self.playerType == VLC and self.mediaListPlayer.get_state() != vlc.State.Paused:
            flagPlayerPlaying = True
        else:
            flagPlayerPlaying = False


        # check if media ever played

        if self.playerType == VLC:
            if self.mediaListPlayer.get_state() == vlc.State.NothingSpecial:
                return

        ek = event.key()

        logging.debug("key event {0}".format(ek))

        if ek in [Qt.Key_Tab, Qt.Key_Shift, Qt.Key_Control, Qt.Key_Meta, Qt.Key_Alt, Qt.Key_AltGr]:
            return

        if self.playerType == VIEWER:
            QMessageBox.critical(self, programName, ("The current observation is opened in VIEW mode.\n"
                                                     "It is not allowed to log events in this mode."))
            return

        if ek == Qt.Key_Escape:
            self.switch_playing_mode()
            return

        # play / pause with space bar
        if ek == Qt.Key_Space and self.pj[OBSERVATIONS][self.observationId][TYPE] in [MEDIA]:
            if self.mediaListPlayer.get_state() != vlc.State.Paused:
                self.pause_video()
            else:
                self.play_video()
            return

        # frame-by-frame mode
        if self.playMode == FFMPEG:
            if ek == 47 or ek == Qt.Key_Left:   # /   one frame back

                logging.debug("current frame {0}".format(self.FFmpegGlobalFrame))
                if self.FFmpegGlobalFrame > 1:
                    self.FFmpegGlobalFrame -= 2
                    newTime = 1000 * self.FFmpegGlobalFrame / list(self.fps.values())[0]
                    self.ffmpegTimerOut()
                    logging.debug("new frame {0}".format(self.FFmpegGlobalFrame))
                return

            if ek == 42 or ek == Qt.Key_Right:  # *  read next frame
                logging.debug("(next) current frame {0}".format(self.FFmpegGlobalFrame))
                self.ffmpegTimerOut()
                logging.debug("(next) new frame {0}".format(self.FFmpegGlobalFrame))
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

        # get video time
        if (self.pj[OBSERVATIONS][self.observationId][TYPE] in [LIVE]
           and "scan_sampling_time" in self.pj[OBSERVATIONS][self.observationId]
           and self.pj[OBSERVATIONS][self.observationId]["scan_sampling_time"]):
            if self.timeFormat == HHMMSS:
                memLaps = Decimal(int(time2seconds(self.lbTimeLive.text())))
            if self.timeFormat == S:
                memLaps = Decimal(int(Decimal(self.lbTimeLive.text())))

        else:
            memLaps = self.getLaps()

        if memLaps == None:
            return

        if (((ek in range(33, 256)) and (ek not in [Qt.Key_Plus, Qt.Key_Minus])) or
           (ek in function_keys) or
           (ek == Qt.Key_Enter and event.text())):  # click from coding pad or subjects pad

            obs_idx, subj_idx  = -1, -1
            count = 0

            if (ek in function_keys):
                ek_unichr = function_keys[ek]
            elif ek != Qt.Key_Enter:
                ek_unichr = chr(ek)

            if ek == Qt.Key_Enter and event.text():  # click from coding pad or subjects pad
                ek_unichr = ""

                if "#subject#" in event.text():
                    for idx in self.pj[SUBJECTS]:
                        if self.pj[SUBJECTS][idx]["name"] == event.text().replace("#subject#", ""):
                            subj_idx = idx
                            '''
                            if self.currentSubject == self.pj[SUBJECTS][subj_idx]["name"]:
                                self.update_subject("")
                            else:
                                self.update_subject(self.pj[SUBJECTS][subj_idx]["name"])
                            '''
                            self.update_subject(self.pj[SUBJECTS][subj_idx]["name"])
                            return


                else: # behavior
                    for o in self.pj[ETHOGRAM]:
                        if self.pj[ETHOGRAM][o]["code"] == event.text():
                            obs_idx = o
                            count += 1
            else:
                # count key occurence in ethogram
                for o in self.pj[ETHOGRAM]:
                    if self.pj[ETHOGRAM][o]["key"] == ek_unichr:
                        obs_idx = o
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
                    if self.mediaListPlayer.get_state() != vlc.State.Paused:
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
                        if self.mediaListPlayer.get_state() != vlc.State.Paused:
                            flagPlayerPlaying = True
                            self.pause_video()

                # let user choose event
                obs_idx = self.fill_lwDetailed(ek_unichr, memLaps)

                logging.debug("obs_idx: {}".format(obs_idx))

                if obs_idx:
                    count = 1

            if self.playerType == VLC and flagPlayerPlaying:
                self.play_video()

            if count == 1:
                # check if focal subject is defined
                if not self.currentSubject and self.alertNoFocalSubject:
                    if self.pj[OBSERVATIONS][self.observationId][TYPE] in [MEDIA]:
                        if self.playerType == VLC:
                            if self.mediaListPlayer.get_state() != vlc.State.Paused:
                                flagPlayerPlaying = True
                                self.pause_video()

                    response = dialog.MessageDialog(programName, ("The focal subject is not defined. Do you want to continue?\n"
                                                                  "Use Preferences menu option to modify this behaviour."), [YES, NO])

                    if self.pj[OBSERVATIONS][self.observationId][TYPE] in [MEDIA] and flagPlayerPlaying:
                        self.play_video()

                    if response == NO:
                        return

                event = self.full_event(obs_idx)

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
                            self.update_subject(self.pj[SUBJECTS][idx]["name"])

                if not flag_subject:
                    self.statusbar.showMessage("Key not assigned ({})".format(ek_unichr), 5000)


    def twEvents_doubleClicked(self):
        """
        seek video to double clicked position (add self.repositioningTimeOffset value)
        substract time offset if any
        """

        if self.twEvents.selectedIndexes():

            row = self.twEvents.selectedIndexes()[0].row()

            if ":" in self.twEvents.item(row, 0).text():
                time_ = time2seconds(self.twEvents.item(row, 0).text())
            else:
                time_  = Decimal(self.twEvents.item(row, 0).text())

            # substract time offset
            time_ -= self.pj[OBSERVATIONS][self.observationId][TIME_OFFSET]

            if time_ + self.repositioningTimeOffset >= 0:
                newTime = (time_ + self.repositioningTimeOffset) * 1000
            else:
                newTime = 0

            if self.playMode == VLC:
                
                print("new time", newTime)
                
                flag_pause = (self.mediaListPlayer.get_state() in [vlc.State.Paused]
                              or self.mediaListPlayer2.get_state() in [vlc.State.Paused])

                if len(self.duration) == 1:
                    '''print(self.mediaplayer.get_media().get_duration())'''
                    if self.mediaListPlayer.get_state() == vlc.State.Ended and time_ < self.mediaplayer.get_media().get_duration() / 1000:
                        #self.play_video()
                        
                        self.mediaListPlayer.play()
                        while True:
                            if self.mediaListPlayer.get_state() in [vlc.State.Playing, vlc.State.Ended]:
                                break

                        if flag_pause:
                            self.mediaListPlayer.pause()
                            while True:
                                if self.mediaListPlayer.get_state() in [vlc.State.Paused, vlc.State.Ended]:
                                    break

                        '''self.pause_video()'''

                    if time_ >= self.mediaplayer.get_media().get_duration() / 1000:
                        print("set to ",self.mediaplayer.get_media().get_duration())
                        self.mediaplayer.set_time(self.mediaplayer.get_media().get_duration()-100)
                        #self.mediaplayer.stop()
                    else:
                        self.mediaplayer.set_time(int(newTime))


                    if self.simultaneousMedia:
                        # synchronize 2nd player
                        '''
                        if self.mediaListPlayer2.get_state() == vlc.State.Ended and time_ < self.mediaplayer.get_media().get_duration()/1000:
                            self.play_video()
                            while True:
                                if self.mediaListPlayer2.get_state() in [vlc.State.Playing, vlc.State.Ended]:
                                    break
                            self.pause_video()
                        '''
    
                        self.mediaplayer2.set_time(int(self.mediaplayer.get_time() -
                                                       self.pj[OBSERVATIONS][self.observationId][TIME_OFFSET_SECOND_PLAYER] * 1000))

                else: # more media in player 1

                    # remember if player paused (go previous will start playing)
                    flagPaused = self.mediaListPlayer.get_state() == vlc.State.Paused

                    tot = 0
                    for idx, d in enumerate(self.duration):
                        if newTime >= tot and newTime < tot + d:
                            self.mediaListPlayer.play_item_at_index(idx)

                            # wait until media is played
                            while True:
                                if self.mediaListPlayer.get_state() in [vlc.State.Playing, vlc.State.Ended]:
                                    break

                            if flagPaused:
                                self.mediaListPlayer.pause()

                            self.mediaplayer.set_time(newTime -
                                                      sum(self.duration[0: self.media_list.index_of_item(self.mediaplayer.get_media())]))
                            break

                        tot += d

                self.timer_out()
                self.timer_spectro_out()


            if self.playMode == FFMPEG:
                frameDuration = Decimal(1000 / list(self.fps.values())[0])
                currentFrame = round(newTime / frameDuration)
                self.FFmpegGlobalFrame = currentFrame
                if self.FFmpegGlobalFrame > 0:
                    self.FFmpegGlobalFrame -= 1
                self.ffmpegTimerOut()


    def twSubjects_doubleClicked(self):
        """
        select subject by double-click
        """

        if self.observationId:
            if self.twSubjects.selectedIndexes():

                row = self.twSubjects.selectedIndexes()[0].row()

                # select or deselect current subject
                '''
                if self.currentSubject == self.twSubjects.item(row, 1).text():
                    self.update_subject("")
                else:
                    self.update_subject(self.twSubjects.item(row, 1).text())
                '''
                self.update_subject(self.twSubjects.item(row, 1).text())
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
            text, ok = QInputDialog.getText(self, "Select events in time interval", "Interval: (example: 12.5-14.7 or 02:45.780-03:15.120)",
                                            QLineEdit.Normal, "")

            if ok and text != '':

                if not "-" in text:
                    QMessageBox.critical(self, programName, "Use minus sign (-) to separate initial value from final value")
                    return

                while " " in text:
                    text = text.replace(" ", "")

                from_, to_ = text.split("-")[0:2]
                from_sec = parseTime(from_)
                if not from_sec:
                    QMessageBox.critical(self, programName, "Time value not recognized: {}".format(from_))
                    return
                to_sec = parseTime(to_)
                if not to_sec:
                    QMessageBox.critical(self, programName, "Time value not recognized: {}".format(to_))
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
        delete all events in current observation
        """

        if not self.observationId:
            self.no_observation()
            return

        if not self.pj[OBSERVATIONS][self.observationId][EVENTS]:
            QMessageBox.warning(self, programName, "No events to delete")
            return

        if dialog.MessageDialog(programName, "Do you really want to delete all events from the current observation?", [YES, NO]) == YES:
            self.pj[OBSERVATIONS][self.observationId][EVENTS] = []
            self.projectChanged = True
            self.loadEventsInTW(self.observationId)


    def delete_selected_events(self):
        """
        delete selected observations
        """

        if not self.observationId:
            self.no_observation()
            return

        if not self.twEvents.selectedIndexes():
            QMessageBox.warning(self, programName, "No event selected!")
        else:
            # list of rows to delete (set for unique)
            try:
                rows = set([item.row() for item in self.twEvents.selectedIndexes()])
                self.pj[OBSERVATIONS][self.observationId][EVENTS] = [event
                                                                     for idx, event in enumerate(self.pj[OBSERVATIONS][self.observationId][EVENTS])
                                                                     if idx not in rows]
                self.projectChanged = True
                self.loadEventsInTW(self.observationId)
            except:
                QMessageBox.critical(self, programName, "Problem during event deletion!")


    def edit_selected_events(self):
        """
        edit one or more selected events for subject, behavior and/or comment
        """
        # list of rows to edit
        rowsToEdit = set([item.row() for item in self.twEvents.selectedIndexes()])

        if not len(rowsToEdit):
            QMessageBox.warning(self, programName, "No event selected!")
        elif len(rowsToEdit) == 1:  # 1 event selected
            self.edit_event()
        else:  # editing of more events
            dialogWindow = dialog.EditSelectedEvents()
            dialogWindow.all_behaviors = [self.pj[ETHOGRAM][str(k)]["code"] for k in sorted([int(x) for x in self.pj[ETHOGRAM].keys()])]
            dialogWindow.all_subjects = [self.pj[SUBJECTS][str(k)]["name"] for k in sorted([int(x) for x in self.pj[SUBJECTS].keys()])]

            if dialogWindow.exec_():
                for idx, event in enumerate(self.pj[OBSERVATIONS][self.observationId][EVENTS]):
                    if idx in rowsToEdit:
                        if dialogWindow.rbSubject.isChecked():
                            event[EVENT_SUBJECT_FIELD_IDX] = dialogWindow.newText.selectedItems()[0].text()
                        if dialogWindow.rbBehavior.isChecked():
                            event[EVENT_BEHAVIOR_FIELD_IDX] = dialogWindow.newText.selectedItems()[0].text()
                        if dialogWindow.rbComment.isChecked():
                            event[EVENT_COMMENT_FIELD_IDX] = dialogWindow.commentText.text()

                        self.pj[OBSERVATIONS][self.observationId][EVENTS][idx] = event
                        self.projectChanged = True
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
            fields_list.append(EVENT_MODIFIER_FIELD_IDX)
        if self.find_dialog.cbComment.isChecked():
            fields_list.append(EVENT_COMMENT_FIELD_IDX)
        if not fields_list:
            self.find_dialog.lb_message.setText('<font color="red">No fields selected!</font>')
            return
        if not self.find_dialog.findText.text():
            self.find_dialog.lb_message.setText('<font color="red">Nothing to search!</font>')
            return

        for event_idx, event in enumerate(self.pj[OBSERVATIONS][self.observationId][EVENTS]):
            if event_idx <= self.find_dialog.currentIdx:
                continue
            if ((not self.find_dialog.cbFindInSelectedEvents.isChecked()) or (self.find_dialog.cbFindInSelectedEvents.isChecked() 
                and event_idx in self.find_dialog.rowsToFind)):
                for idx in fields_list:
                    if self.find_dialog.findText.text() in event[idx]:
                        self.find_dialog.currentIdx = event_idx
                        self.twEvents.scrollToItem(self.twEvents.item(event_idx, 0))
                        self.twEvents.selectRow(event_idx)
                        return

        if msg != "FIND_FROM_BEGINING":
            if dialog.MessageDialog(programName, "<b>{}</b> not found. Search from beginning?".format(self.find_dialog.findText.text()),
                                [YES, NO]) == YES:
                self.find_dialog.currentIdx = -1
                self.click_signal_find_in_events("FIND_FROM_BEGINING")
            else:
                self.find_dialog.close()
        else:
            if self.find_dialog.currentIdx == -1:
                self.find_dialog.lb_message.setText("<b>{}</b> not found".format(self.find_dialog.findText.text()))



    def find_events(self):
        """
        find  in events
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
        for event_idx, event in enumerate(self.pj[OBSERVATIONS][self.observationId][EVENTS]):

            if event_idx < self.find_replace_dialog.currentIdx:
                continue

            if (not self.find_replace_dialog.cbFindInSelectedEvents.isChecked()) or (self.find_replace_dialog.cbFindInSelectedEvents.isChecked() and event_idx in self.find_replace_dialog.rowsToFind):
                for idx1 in fields_list:
                    if idx1 <= self.find_replace_dialog.currentIdx_idx:
                        continue
                    if self.find_replace_dialog.findText.text() in event[idx1]:
                        number_replacement += 1
                        self.find_replace_dialog.currentIdx = event_idx
                        self.find_replace_dialog.currentIdx_idx = idx1
                        event[idx1] = event[idx1].replace(self.find_replace_dialog.findText.text(), self.find_replace_dialog.replaceText.text())
                        self.pj[OBSERVATIONS][self.observationId][EVENTS][event_idx] = event
                        self.loadEventsInTW(self.observationId)
                        self.twEvents.scrollToItem(self.twEvents.item(event_idx, 0))
                        self.twEvents.selectRow(event_idx)
                        self.projectChanged = True

                        if msg == "FIND_REPLACE":
                            return

                self.find_replace_dialog.currentIdx_idx = -1

        if msg == "FIND_REPLACE":
            if dialog.MessageDialog(programName, "{} not found.\nRestart find/replace from the beginning?".format(self.find_replace_dialog.findText.text()),
                                    [YES, NO]) == YES:
                self.find_replace_dialog.currentIdx = -1
            else:
                self.find_replace_dialog.close()
        if msg == "FIND_REPLACE_ALL":
            dialog.MessageDialog(programName, "{} substitution(s).".format(number_replacement), [OK])
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


    def export_tabular_events(self):
        """
        export events from selected observations in various formats: TSV, CSV, ODS, XLSX, XLS, HTML
        """

        # ask user observations to analyze
        result, selectedObservations = self.selectObservations(MULTIPLE)

        if not selectedObservations:
            return

        parameters = self.choose_obs_subj_behav_category(selectedObservations,
                                                         maxTime=0,
                                                         flagShowIncludeModifiers=False,
                                                         flagShowExcludeBehaviorsWoEvents=False)

        if not parameters["selected subjects"] or not parameters["selected behaviors"]:
            return

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

            exportDir = QFileDialog(self).getExistingDirectory(self, "Choose a directory to export events", os.path.expanduser("~"),
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


            if QT_VERSION_STR[0] == "4":
                filediag_func = QFileDialog(self).getSaveFileNameAndFilter
            else:
                filediag_func = QFileDialog(self).getSaveFileName

            fileName, filter_ = filediag_func(self, "Export events", "", ";;".join(extended_file_formats))

            if not fileName:
                return

            outputFormat = file_formats[extended_file_formats.index(filter_)]
            if pathlib.Path(fileName).suffix != "." + outputFormat:
                fileName = str(pathlib.Path(fileName)) + "." + outputFormat

        for obsId in selectedObservations:
            if len(selectedObservations) > 1:
                fileName = str(pathlib.Path(pathlib.Path(exportDir) / safeFileName(obsId)).with_suffix("." + outputFormat))

            r, msg = export_observation.export_events(parameters, obsId, self.pj[OBSERVATIONS][obsId], self.pj[ETHOGRAM],
                                                      fileName, outputFormat)
            if not r:
                QMessageBox.critical(None, programName, msg, QMessageBox.Ok | QMessageBox.Default, QMessageBox.NoButton)


    def create_behavioral_strings(self, obsId, subj, plot_parameters):
        """
        return the behavioral string for subject in obsId
        """

        s = ""
        currentStates = []
        eventsWithStatus = project_function.events_start_stop(self.pj[ETHOGRAM], self.pj[OBSERVATIONS][obsId][EVENTS])

        for event in eventsWithStatus:
            if event[EVENT_SUBJECT_FIELD_IDX] == subj or (subj == NO_FOCAL_SUBJECT and event[EVENT_SUBJECT_FIELD_IDX] == ""):

                if event[-1] == POINT:
                    if currentStates:
                        s += "+".join(currentStates) + "+" + event[EVENT_BEHAVIOR_FIELD_IDX]
                    else:
                        s += event[EVENT_BEHAVIOR_FIELD_IDX]

                    if plot_parameters["include modifiers"]:
                        s += "&" + event[EVENT_MODIFIER_FIELD_IDX].replace("|", "+")

                    s += self.behaviouralStringsSeparator

                if event[-1] == START:
                    currentStates.append(event[EVENT_BEHAVIOR_FIELD_IDX])
                    s += "+".join(currentStates)

                    if plot_parameters["include modifiers"]:
                        s += "&" + event[EVENT_MODIFIER_FIELD_IDX].replace("|", "+")
                    s += self.behaviouralStringsSeparator

                if event[-1] == STOP:

                    if event[EVENT_BEHAVIOR_FIELD_IDX] in currentStates:
                        currentStates.remove(event[EVENT_BEHAVIOR_FIELD_IDX])

                    if currentStates:
                        s += "+".join(currentStates)

                        if plot_parameters["include modifiers"]:
                            s += "&" + event[EVENT_MODIFIER_FIELD_IDX].replace("|", "+")
                        s += self.behaviouralStringsSeparator

        # remove last separator (if separator not empty)
        if self.behaviouralStringsSeparator:
            s = s[0: -len(self.behaviouralStringsSeparator)]

        return s

    def export_string_events(self):
        """
        export events from selected observations by subject as behavioral strings (plain text file)
        behaviors are separated by character specified in self.behaviouralStringsSeparator (usually pipe |)
        for use with Behatrix (see http://www.boris.unito.it/pages/behatrix)
        """

        # ask user observations to analyze
        result, selectedObservations = self.selectObservations(MULTIPLE)
        if not selectedObservations:
            return

        plot_parameters = self.choose_obs_subj_behav_category(selectedObservations, maxTime=0, flagShowIncludeModifiers=True,
                                                              flagShowExcludeBehaviorsWoEvents=False)

        if not plot_parameters["selected subjects"] or not plot_parameters["selected behaviors"]:
            return

        fn = QFileDialog(self).getSaveFileName(self, "Export events as strings", "", "Events file (*.txt *.tsv);;All files (*)")
        fileName = fn[0] if type(fn) is tuple else fn

        if fileName:

            response = dialog.MessageDialog(programName, "Include observation(s) information?", [YES, NO])

            try:
                with open(fileName, "w", encoding="utf-8") as outFile:
                    for obsId in selectedObservations:
                        # observation id
                        outFile.write("\n# observation id: {}\n".format(obsId))
                        # observation descrition
                        outFile.write("# observation description: {}\n".format(
                                                                self.pj[OBSERVATIONS][obsId]["description"].replace(os.linesep, " ")))
                        # media file name
                        if self.pj[OBSERVATIONS][obsId][TYPE] in [MEDIA]:
                            outFile.write("# Media file name: {0}{1}{1}".format(", ".join([os.path.basename(x)
                                                                                           for x in self.pj[OBSERVATIONS]
                                                                                           [obsId]
                                                                                           [FILE][PLAYER1]]), os.linesep))
                        if self.pj[OBSERVATIONS][obsId][TYPE] in [LIVE]:
                            outFile.write("# Live observation{0}{0}".format(os.linesep))

                        # independent variables
                        if "independent_variables" in self.pj[OBSERVATIONS][obsId]:
                            outFile.write("# Independent variables\n")

                            # rows.append(["variable", "value"])
                            for variable in self.pj[OBSERVATIONS][obsId]["independent_variables"]:
                                outFile.write("# {0}: {1}\n".format(variable,
                                                                    self.pj[OBSERVATIONS][obsId]["independent_variables"][variable]))
                        outFile.write("\n")

                        # selected subjects
                        for subj in plot_parameters["selected subjects"]:
                            if subj:
                                subj_str = "\n# {}:\n".format(subj)
                            else:
                                subj_str = "\n# No focal subject:\n"
                            outFile.write(subj_str)

                            out = self.create_behavioral_strings(obsId, subj, plot_parameters)
                            if out:
                                outFile.write(out + "\n")

            except:
                errorMsg = sys.exc_info()[1]
                logging.critical(errorMsg)
                QMessageBox.critical(None, programName, str(errorMsg), QMessageBox.Ok | QMessageBox.Default, QMessageBox.NoButton)


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
        if len(plot_parameters["selected subjects"]) == 1:

            fn = QFileDialog(self).getSaveFileName(self, "Create matrix of transitions " + mode, "",
                                                   "Transitions matrix files (*.txt *.tsv);;All files (*)")
            fileName = fn[0] if type(fn) is tuple else fn

        else:
            exportDir = QFileDialog(self).getExistingDirectory(self, "Choose a directory to save the transitions matrices",
                                                               os.path.expanduser("~"), options=QFileDialog(self).ShowDirsOnly)
            if not exportDir:
                return
            flagMulti = True

        for subject in plot_parameters["selected subjects"]:

            logging.debug("subjects: {}".format(subject))

            strings_list = []
            for obsId in selectedObservations:
                strings_list.append(self.create_behavioral_strings(obsId, subject, plot_parameters))

            sequences, observed_behaviors = transitions.behavioral_strings_analysis(strings_list, self.behaviouralStringsSeparator)

            observed_matrix = transitions.observed_transitions_matrix(sequences,
                                                                      sorted(list(set(observed_behaviors +
                                                                                      plot_parameters["selected behaviors"]))),
                                                                      mode=mode)

            if not observed_matrix:
                QMessageBox.warning(self, programName, "No transitions found for <b>{}</b>".format(subject))
                continue

            logging.debug("observed_matrix {}:\n{}".format(mode, observed_matrix))

            if flagMulti:
                try:

                    nf = "{exportDir}{sep}{subject}_transitions_{mode}_matrix.tsv".format(exportDir=exportDir,
                                                                                          sep=os.sep,
                                                                                          subject=subject,
                                                                                          mode=mode)

                    if os.path.isfile(nf):
                        if dialog.MessageDialog(programName,
                                                "A file with same name already exists.<br><b>{}</b>".format(nf),
                                                ["Overwrite", CANCEL]) == CANCEL:
                            continue

                    with open(nf, "w") as outfile:
                        outfile.write(observed_matrix)
                except:
                    QMessageBox.critical(self, programName, "The file {} can not be saved".format(nf))
            else:
                try:
                    with open(fileName, "w") as outfile:
                        outfile.write(observed_matrix)

                except:
                    QMessageBox.critical(self, programName, "The file {} can not be saved".format(fileName))


    def transitions_dot_script(self):
        """
        create dot script (graphviz language) from transitions frequencies matrix
        """

        fn = QFileDialog(self).getOpenFileNames(self, "Select one or more transitions matrix files", "",
                                                "Transitions matrix files (*.txt *.tsv);;All files (*)")
        fileNames = fn[0] if type(fn) is tuple else fn

        out = ""
        for fileName in fileNames:
            with open(fileName, "r") as infile:
                try:
                    gv = transitions.create_transitions_gv_from_matrix(infile.read(),
                                                                       cutoff_all=0,
                                                                       cutoff_behavior=0,
                                                                       edge_label="percent_node")
                    with open(fileName + ".gv", "w") as f:
                        f.write(gv)

                    out += "<b>{}</b> created<br>".format(fileName + ".gv")
                except:
                    QMessageBox.information(self, programName, "Error during dot script creation.\n{}".format(str(sys.exc_info()[0])))

        if out:
            QMessageBox.information(self, programName,
                                    out + "<br><br>The DOT scripts can be used with Graphviz or WebGraphviz to generate diagram")


    def transitions_flow_diagram(self):
        """
        create flow diagram with graphviz (if installed) from transitions matrix
        """

        # check if dot present in path
        result = subprocess.getoutput("dot -V")
        if "graphviz" not in result:
            QMessageBox.critical(self, programName, ("The GraphViz package is not installed.<br>"
                                                     "The <b>dot</b> program was not found in the path.<br><br>"
                                                     """Go to <a href="http://www.graphviz.org">"""
                                                     """http://www.graphviz.org</a> for information"""))
            return

        fn = QFileDialog(self).getOpenFileNames(self, "Select one or more transitions matrix files", "",
                                                "Transitions matrix files (*.txt *.tsv);;All files (*)")
        fileNames = fn[0] if type(fn) is tuple else fn

        out = ""
        for fileName in fileNames:
            with open(fileName, "r") as infile:
                try:
                    gv = transitions.create_transitions_gv_from_matrix(infile.read(),
                                                                       cutoff_all=0,
                                                                       cutoff_behavior=0,
                                                                       edge_label="percent_node")

                    with open(tempfile.gettempdir() + os.sep + os.path.basename(fileName) + ".tmp.gv", "w") as f:
                        f.write(gv)
                    result = subprocess.getoutput("""dot -Tpng -o "{0}.png" "{1}" """.format(fileName,
                                                                                             tempfile.gettempdir() +
                                                                                             os.sep + os.path.basename(fileName) +
                                                                                             ".tmp.gv"))
                    if not result:
                        out += "<b>{}</b> created<br>".format(fileName + ".png")
                    else:
                        out += "Problem with <b>{}</b><br>".format(fileName)
                except:
                    QMessageBox.information(self, programName, "Error during flow diagram creation.\n{}".format(str(sys.exc_info()[0])))

        if out:
            QMessageBox.information(self, programName, out)


    def closeEvent(self, event):
        """
        check if current project is saved
        close coding pad window if it exists
        close spectrogram window if it exists
         and close program
        """

        # check if re-encoding
        if self.ffmpeg_recode_process:
            QMessageBox.warning(self, programName, "BORIS is re-encoding/resizing a video. Please wait before closing.")
            event.ignore()

        if self.projectChanged:
            response = dialog.MessageDialog(programName, "What to do about the current unsaved project?", [SAVE, DISCARD, CANCEL])

            if response == SAVE:
                if self.save_project_activated() == "not saved":
                    event.ignore()

            if response == CANCEL:
                event.ignore()

        self.saveConfigFile()

        self.close_tool_windows()


    def actionQuit_activated(self):
        self.close()


    def import_observations(self):
        """
        import observations from project file
        """

        fn = QFileDialog(self).getOpenFileName(self, "Choose a BORIS project file", "", "Project files (*.boris);;All files (*)")
        fileName = fn[0] if type(fn) is tuple else fn

        if self.projectFileName and fileName == self.projectFileName:
            QMessageBox.critical(None, programName,
                                 "This project is already open", QMessageBox.Ok | QMessageBox.Default, QMessageBox.NoButton)
            return

        if fileName:
            try:
                fromProject = json.loads(open(fileName, "r").read())
            except:
                QMessageBox.critical(self, programName, "This project file seems corrupted")
                return

            # transform time to decimal
            fromProject = convert_time_to_decimal(fromProject)  # function in utilities.py

            dbc = dialog.ChooseObservationsToImport("Choose the observations to import:", sorted(list(fromProject[OBSERVATIONS].keys())))

            if dbc.exec_():

                selected_observations = dbc.get_selected_observations()
                if selected_observations:
                    flagImported = False

                    # set of behaviors in current projet ethogram
                    behav_set = set([self.pj[ETHOGRAM][idx]["code"] for idx in self.pj[ETHOGRAM]])

                    # set of subjects in current projet
                    subjects_set = set([self.pj[SUBJECTS][idx]["name"] for idx in self.pj[SUBJECTS]])

                    for obsId in selected_observations:

                        # check if behaviors are in current project ethogram
                        new_behav_set = set([event[EVENT_BEHAVIOR_FIELD_IDX] for event in fromProject[OBSERVATIONS][obsId][EVENTS]
                                             if event[EVENT_BEHAVIOR_FIELD_IDX] not in behav_set])
                        if new_behav_set:
                            diag_result = dialog.MessageDialog(programName,
                                                               ("Some coded behaviors in <b>{}</b> are"
                                                                "not in the ethogram:<br><b>{}</b>").format(obsId,
                                                                                                            ", ".join(new_behav_set)),
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
                                                               ("Some coded subjects in <b>{}</b> are not defined in the project:<br>"
                                                                "<b>{}</b>").format(obsId,
                                                                                    ", ".join(new_subject_set)),
                                                               ["Interrupt import", "Skip observation", "Import observation"])

                            if diag_result == "Interrupt import":
                                return

                            if diag_result == "Skip observation":
                                continue

                        if obsId in self.pj[OBSERVATIONS].keys():
                            diag_result = dialog.MessageDialog(programName,
                                                               ("The observation <b>{}</b>"
                                                                "already exists in the current project.<br>").format(obsId),
                                                               ["Interrupt import", "Skip observation", "Rename observation"])
                            if diag_result == "Interrupt import":
                                return

                            if diag_result == "Rename observation":
                                self.pj[OBSERVATIONS]["{} (imported at {})".format(obsId,
                                                                                   datetime_iso8601()
                                                                                   )] = dict(fromProject[OBSERVATIONS][obsId])
                                flagImported = True
                        else:
                            self.pj[OBSERVATIONS][obsId] = dict(fromProject[OBSERVATIONS][obsId])
                            flagImported = True

                    if flagImported:
                        QMessageBox.information(self, programName, "Observations imported successfully")


    def play_video(self):
        """
        play video
        """

        if self.playerType == VLC:
            if self.playMode == FFMPEG:
                self.FFmpegTimer.start()
            else:
                self.mediaListPlayer.play()
                # second video together
                if self.simultaneousMedia:
                    self.mediaListPlayer2.play()

                self.timer.start(200)
                self.timer_spectro.start()


    def pause_video(self):
        """
        pause media
        does not pause media if already paused (to prevent that media will be played)
        """

        if self.playerType == VLC:
            if self.playMode == FFMPEG:
                self.FFmpegTimer.stop()
            else:
                if self.mediaListPlayer.get_state() != vlc.State.Paused:

                    self.timer.stop()
                    self.timer_spectro.stop()

                    self.mediaListPlayer.pause()
                    # wait for pause

                    # wait until video is paused or ended
                    while True:
                        if self.mediaListPlayer.get_state() in [vlc.State.Paused, vlc.State.Ended]:
                            break

                # second video together
                if self.simultaneousMedia:
                    if self.mediaListPlayer2.get_state() != vlc.State.Paused:
                        self.mediaListPlayer2.pause()

                logging.debug("pause_video: player #1 state: {}".format(self.mediaListPlayer.get_state()))
                if self.simultaneousMedia:
                    logging.debug('pause_video: player #2 state {}'.format(self.mediaListPlayer2.get_state()))
                    pass

                time.sleep(1)
                self.timer_out()
                self.timer_spectro_out()


    def play_activated(self):
        """
        button 'play' activated
        """
        if self.observationId and self.pj[OBSERVATIONS][self.observationId][TYPE] in [MEDIA]:
            self.play_video()


    def jumpBackward_activated(self):
        '''
        rewind from current position
        '''
        if self.playerType == VLC:

            if self.playMode == FFMPEG:
                currentTime = self.FFmpegGlobalFrame / list(self.fps.values())[0]
                if int((currentTime - self.fast) * list(self.fps.values())[0]) > 0:
                    self.FFmpegGlobalFrame = int((currentTime - self.fast) * list(self.fps.values())[0])
                else:
                    self.FFmpegGlobalFrame = 0   # position to init
                if self.second_player():
                    currentTime2 = self.FFmpegGlobalFrame2 / list(self.fps2.values())[0]
                    if int((currentTime2 - self.fast) * list(self.fps2.values())[0]) > 0:
                        self.FFmpegGlobalFrame2 = int((currentTime2 - self.fast) * list(self.fps2.values())[0])
                    else:
                        self.FFmpegGlobalFrame2 = 0   # position to init
                self.ffmpegTimerOut()
            else:
                if self.media_list.count() == 1:
                    if self.mediaplayer.get_time() >= self.fast * 1000:
                        self.mediaplayer.set_time(self.mediaplayer.get_time() - self.fast * 1000)
                    else:
                        self.mediaplayer.set_time(0)
                    if self.simultaneousMedia:
                        self.mediaplayer2.set_time(int(self.mediaplayer.get_time() -
                                                   self.pj[OBSERVATIONS][self.observationId][TIME_OFFSET_SECOND_PLAYER] * 1000))

                elif self.media_list.count() > 1:

                    newTime = (sum(self.duration[0: self.media_list.index_of_item(self.mediaplayer.get_media())]) +
                               self.mediaplayer.get_time()) - self.fast * 1000
                    if newTime < self.fast * 1000:
                        newTime = 0

                    # remember if player paused (go previous will start playing)
                    flagPaused = self.mediaListPlayer.get_state() == vlc.State.Paused

                    tot = 0
                    for idx, d in enumerate(self.duration):
                        if newTime >= tot and newTime < tot+d:
                            self.mediaListPlayer.play_item_at_index(idx)

                            # wait until media is played
                            while True:
                                if self.mediaListPlayer.get_state() in [vlc.State.Playing, vlc.State.Ended]:
                                    break

                            if flagPaused:
                                self.mediaListPlayer.pause()

                            self.mediaplayer.set_time(newTime -
                                                      sum(self.duration[0: self.media_list.index_of_item(self.mediaplayer.get_media())]))

                            break
                        tot += d

                else:
                    self.no_media()

                self.timer_out()
                self.timer_spectro_out()

                # no subtitles
                # self.mediaplayer.video_set_spu(0)


    def jumpForward_activated(self):
        """
        forward from current position
        """

        if self.playerType == VLC:

            if self.playMode == FFMPEG:

                self.FFmpegGlobalFrame += self.fast * list(self.fps.values())[0]

                if self.FFmpegGlobalFrame * (1000 / list(self.fps.values())[0]) >= sum(self.duration):
                    logging.debug("end of last media")
                    self.FFmpegGlobalFrame = int(sum(self.duration) * list(self.fps.values())[0] / 1000)-1
                    logging.debug("FFmpegGlobalFrame {}  sum duration {}".format(self.FFmpegGlobalFrame, sum(self.duration)))

                if self.FFmpegGlobalFrame > 0:
                    self.FFmpegGlobalFrame -= 1

                if self.second_player():

                    self.FFmpegGlobalFrame2 += self.fast * list(self.fps2.values())[0]
                    if self.FFmpegGlobalFrame2 * (1000 / list(self.fps2.values())[0]) >= sum(self.duration2):
                        logging.debug("end of last media")
                        self.FFmpegGlobalFrame2 = int(sum(self.duration2) * list(self.fps2.values())[0] / 1000)-1
                        logging.debug("FFmpegGlobalFrame2 {}  sum duration2 {}".format(self.FFmpegGlobalFrame2, sum(self.duration2)))

                    if self.FFmpegGlobalFrame2 > 0:
                        self.FFmpegGlobalFrame2 -= 1

                self.ffmpegTimerOut()

            else:
                if self.media_list.count() == 1:
                    if self.mediaplayer.get_time() >= self.mediaplayer.get_length() - self.fast * 1000:
                        self.mediaplayer.set_time(self.mediaplayer.get_length())
                    else:
                        self.mediaplayer.set_time(self.mediaplayer.get_time() + self.fast * 1000)

                    if self.simultaneousMedia:
                        self.mediaplayer2.set_time(int(self.mediaplayer.get_time() -
                                                   self.pj[OBSERVATIONS][self.observationId][TIME_OFFSET_SECOND_PLAYER] * 1000))

                elif self.media_list.count() > 1:

                    newTime = (sum(self.duration[0: self.media_list.index_of_item(self.mediaplayer.get_media())]) +
                               self.mediaplayer.get_time()) + self.fast * 1000
                    if newTime < sum(self.duration):
                        # remember if player paused (go previous will start playing)
                        flagPaused = self.mediaListPlayer.get_state() == vlc.State.Paused

                        tot = 0
                        for idx, d in enumerate(self.duration):
                            if newTime >= tot and newTime < tot + d:
                                self.mediaListPlayer.play_item_at_index(idx)
                                app.processEvents()
                                # wait until media is played
                                while True:
                                    if self.mediaListPlayer.get_state() in [vlc.State.Playing, vlc.State.Ended]:
                                        break

                                if flagPaused:
                                    self.mediaListPlayer.pause()

                                self.mediaplayer.set_time(newTime - sum(
                                    self.duration[0: self.media_list.index_of_item(self.mediaplayer.get_media())]))

                                break
                            tot += d

                else:
                    self.no_media()

                self.timer_out()
                self.timer_spectro_out()


    def reset_activated(self):
        """
        reset video to beginning
        """
        logging.debug("Reset activated")

        if self.playerType == VLC:

            self.pause_video()
            if self.playMode == FFMPEG:

                self.FFmpegGlobalFrame = 0   # position to init
                if self.simultaneousMedia:
                    self.FFmpegGlobalFrame2 = 0   # position to init

                self.ffmpegTimerOut()

            else:  # playmode VLC

                self.mediaplayer.set_time(0)

                # second video together
                if self.simultaneousMedia:
                    self.mediaplayer2.set_time(0)

                self.timer_out()
                self.timer_spectro_out()


    def changedFocusSlot(self, old, now):
        """
        connect events filter when app gains focus
        """
        if window.focusWidget():
            window.focusWidget().installEventFilter(self)


if __name__ == "__main__":

    app = QApplication(sys.argv)

    # splashscreen
    if (not options.nosplashscreen):
        start = time.time()
        splash = QSplashScreen(QPixmap(os.path.dirname(os.path.realpath(__file__)) + "/splash.png"))
        splash.show()
        splash.raise_()
        while time.time() - start < 1:
            time.sleep(0.001)
            app.processEvents()

    availablePlayers = []

    # load VLC
    import vlc
    if vlc.dll is None:
        logging.critical("VLC media player not found")
        QMessageBox.critical(None, programName, "This program requires the VLC media player.<br>Go to http://www.videolan.org/vlc",
                             QMessageBox.Ok | QMessageBox.Default, QMessageBox.NoButton)
        sys.exit(1)

    availablePlayers.append(VLC)

    logging.debug("VLC version {}".format(vlc.libvlc_get_version().decode("utf-8")))
    if vlc.libvlc_get_version().decode("utf-8") < VLC_MIN_VERSION:
        QMessageBox.critical(None, programName, ("The VLC media player seems very old ({}).<br>"
                                                 "Go to http://www.videolan.org/vlc to update it").format(vlc.libvlc_get_version()),
                             QMessageBox.Ok | QMessageBox.Default, QMessageBox.NoButton)

        logging.critical(("The VLC media player seems a little bit old... ({})."
                          "Go to http://www.videolan.org/vlc to update it").format(vlc.libvlc_get_version()))
        sys.exit(2)

    # check FFmpeg
    ret, msg = check_ffmpeg_path()
    if not ret:
        QMessageBox.critical(None, programName, "FFmpeg is not available.<br>Go to http://www.ffmpeg.org to download it",
                             QMessageBox.Ok | QMessageBox.Default, QMessageBox.NoButton)
        sys.exit(3)
    else:
        ffmpeg_bin = msg

    # check matplotlib
    if not FLAG_MATPLOTLIB_INSTALLED:
        QMessageBox.warning(None, programName,
                            ("Some functions (plot events and spectrogram) require the Matplotlib module."
                             """<br>See <a href="http://matplotlib.org">http://matplotlib.org</a>"""),
                            QMessageBox.Ok | QMessageBox.Default, QMessageBox.NoButton)

    app.setApplicationName(programName)
    window = MainWindow(availablePlayers, ffmpeg_bin)

    # open project/start observation on command line
    project_to_open = ""
    observation_to_open = ""
    if options.project:
        project_to_open = options.project

    logging.debug("args: {}".format(args))
    if args and len(args) > 0:
       project_to_open = args[0]

    if options.observation:
        if not project_to_open:
            print("No project file!")
            sys.exit()
        observation_to_open = options.observation

    if args and len(args) > 1:
        if not project_to_open:
            print("No project file!")
            sys.exit()
        observation_to_open = args[1]

    if project_to_open:

        project_path, project_changed, pj, msg = project_functions.open_project_json(project_to_open)

        if "error" in pj:
            logging.debug(pj["error"])
            QMessageBox.critical(window, programName, pj["error"])
        else:
            if msg:
                QMessageBox.information(window, programName, msg)
            window.load_project(project_path, project_changed, pj)

    if observation_to_open:
        r = window.load_observation(observation_to_open)
        if r:
            QMessageBox.warning(None, programName, "Error opening observation: <b>{}</b><br>{}".format(observation_to_open, r.split(":")[1]),
                                QMessageBox.Ok | QMessageBox.Default, QMessageBox.NoButton)

    window.show()
    window.raise_()

    # connect events filter when app focus changes
    app.focusChanged.connect(window.changedFocusSlot)

    if not options.nosplashscreen:
        splash.finish(window)

    sys.exit(app.exec_())
