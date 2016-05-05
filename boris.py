#!/usr/bin/env python3


"""
BORIS
Behavioral Observation Research Interactive Software
Copyright 2012-2016 Olivier Friard

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


__version__ = "2.97"
__version_date__ = "2016-05-05"
__DEV__ = False
BITMAP_EXT = "png"

import sys
import logging
import platform

if int(platform.python_version_tuple()[0]) < 3:
    logging.critical("BORIS requires Python 3+!")
    sys.exit()

try:
    from PyQt4.QtCore import *
    from PyQt4.QtGui import *
except:
    logging.critical("PyQt4 not installed!")
    sys.exit()

import qrc_boris
from config import *

video, live = 0, 1

import time
import os
import json
from decimal import *
import re
import hashlib
import subprocess
import sqlite3
import urllib.parse
import urllib.request
import urllib.error
import tempfile
import glob
import statistics

import dialog
from boris_ui import *
from edit_event import *
from project import *
import preferences
import param_panel
import observation
import coding_map
import map_creator
import select_modifiers
from utilities import *
import tablib
import obs_list2
import plot_spectrogram

def bytes_to_str(b):
    """
    Translate bytes to string.
    """
    if isinstance(b, bytes):
        fileSystemEncoding = sys.getfilesystemencoding()
        # hack for PyInstaller
        if fileSystemEncoding == None:
            fileSystemEncoding = "UTF-8"
        return b.decode( fileSystemEncoding )
    else:
        return b

from time_budget_widget import *
import select_modifiers

class TempDirCleanerThread(QThread):
    """
    class for cleaning image cache directory with thread
    """
    def __init__(self, parent = None):
        QThread.__init__(self, parent)
        self.exiting = False
        self.tempdir = ""
        self.ffmpeg_cache_dir_max_size = 0

    def run(self):
        while self.exiting == False:
            if sum(os.path.getsize(self.tempdir+f) for f in os.listdir(self.tempdir) if "BORIS_" in f and os.path.isfile(self.tempdir + f)) > self.ffmpeg_cache_dir_max_size:
                fl = sorted((os.path.getctime(self.tempdir + f),self.tempdir + f) for f in os.listdir(self.tempdir) if "BORIS_" in f and os.path.isfile(self.tempdir + f))
                for ts,f in fl[0:int(len(fl)/10)]:
                    os.remove(f)
            time.sleep(30)



ROW = -1

class StyledItemDelegateTriangle(QtGui.QStyledItemDelegate):
    """
    painter for twEvents with current time highlighting
    """
    def __init__(self, parent=None):
        super(StyledItemDelegateTriangle, self).__init__(parent)

    def paint(self, painter, option, index):

        super(StyledItemDelegateTriangle, self).paint(painter, option, index)

        if ROW != -1:

            if index.row() == ROW:

                polygonTriangle = QtGui.QPolygon(3)
                polygonTriangle.setPoint(0, QtCore.QPoint(option.rect.x()+15, option.rect.y()))
                polygonTriangle.setPoint(1, QtCore.QPoint(option.rect.x(), option.rect.y()-5))
                polygonTriangle.setPoint(2, QtCore.QPoint(option.rect.x(), option.rect.y()+5))

                painter.save()
                painter.setRenderHint(painter.Antialiasing)
                painter.setBrush(QtGui.QBrush(QtGui.QColor(QtCore.Qt.red)))
                painter.setPen(QtGui.QPen(QtGui.QColor(QtCore.Qt.red)))
                painter.drawPolygon(polygonTriangle)
                painter.restore()


class MainWindow(QMainWindow, Ui_MainWindow):

    pj = {"time_format": HHMMSS, "project_date": "", "project_name": "", "project_description": "", SUBJECTS : {}, "behaviors_conf": {}, OBSERVATIONS: {} , "coding_map":{} }
    project = False

    observationId = ''   # current observation id

    timeOffset = 0.0

    confirmSound = False               # if True each keypress will be confirmed by a beep
    embedPlayer = True                 # if True the VLC player will be embedded in the main window
    alertNoFocalSubject = False        # if True an alert will show up if no focal subject
    trackingCursorAboveEvent = False   # if True the cursor will appear above the current event in events table
    checkForNewVersion = False         # if True BORIS will check for new version every 15 days
    timeFormat = HHMMSS                # 's' or 'hh:mm:ss'
    repositioningTimeOffset = 0
    automaticBackup = 0                # automatic backup interval (0 no backup)

    #ObservationsChanged = False
    projectChanged = False

    liveObservationStarted = False

    projectFileName = ''
    mediaTotalLength = None

    saveMediaFilePath = True

    measurement_w = None
    memPoints = []   # memory of clicke points for measurement tool

    behaviouralStringsSeparator = '|'

    duration = []

    simultaneousMedia = False # if second player was created

    # time laps
    fast = 10

    currentStates = {}
    flag_slow = False
    play_rate = 1

    play_rate_step = 0.1

    currentSubject = ''  # contains the current subject of observation

    detailedObs = {}

    codingMapWindowGeometry = 0

    projectWindowGeometry = 0   # memorize size of project window

    imageDirectory = ""   # image cache directory

    # FFmpeg
    allowFrameByFrame = False

    memx, memy = -1, -1

    # path for ffmpeg/ffmpeg.exe program
    ffmpeg_bin = ''
    ffmpeg_cache_dir = ''
    ffmpeg_cache_dir_max_size = 0

    # dictionary for FPS storing
    fps = {}

    playerType = ""   # player type can be VLC for video mode LIVE for live observation
    playMode = VLC    # player mode can be VLC of FMPEG (for frame-by-frame mode)

    # spectrogram
    chunk_length = 60  # spectrogram chunk length in seconds

    memMedia = ""

    cleaningThread = TempDirCleanerThread()


    def __init__(self, availablePlayers, ffmpeg_bin, parent = None):

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

        try:
            datadir = sys._MEIPASS
        except Exception:
            datadir = os.path.dirname(os.path.realpath(__file__))

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
        self.dwConfiguration.setVisible(False)
        self.dwSubjects.setVisible(False)
        self.lbFocalSubject.setVisible(False)
        self.lbCurrentStates.setVisible(False)

        self.lbFocalSubject.setText('')
        self.lbCurrentStates.setText('')

        self.lbFocalSubject.setText( NO_FOCAL_SUBJECT )

        font = QFont()
        font.setPointSize(15)
        self.lbFocalSubject.setFont(font)
        self.lbCurrentStates.setFont(font)

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

        self.twEvents.setColumnCount( len(tw_events_fields) )
        self.twEvents.setHorizontalHeaderLabels(tw_events_fields)

        self.imagesList = set()
        self.FFmpegGlobalFrame = 0

        self.menu_options()

        self.connections()


    def create_live_tab(self):
        """
        create tab with widget for live observation
        """

        self.liveLayout = QtGui.QGridLayout()
        self.textButton = QPushButton("Start live observation")
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

        self.liveTab = QtGui.QWidget()
        self.liveTab.setLayout(self.liveLayout)

        self.toolBox.insertItem(2, self.liveTab, 'Live')


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
                pn = "Unnamed project"

        self.setWindowTitle("{}{}{}".format(self.observationId + " - "*(self.observationId != ""), pn+(" - "*(pn != "")), programName))


        # project menu
        self.actionEdit_project.setEnabled(flag)
        self.actionSave_project.setEnabled(flag)
        self.actionSave_project_as.setEnabled(flag)
        self.actionClose_project.setEnabled(flag)

        # observations

        # enabled if project
        self.actionNew_observation.setEnabled(flag)

        self.actionOpen_observation.setEnabled( self.pj[OBSERVATIONS] != {})
        self.actionEdit_observation_2.setEnabled( self.pj[OBSERVATIONS] != {})
        self.actionObservationsList.setEnabled( self.pj[OBSERVATIONS] != {})

        # enabled if observation
        flagObs = self.observationId != ''

        self.actionAdd_event.setEnabled(flagObs)
        self.actionClose_observation.setEnabled(flagObs)
        #self.actionLoad_observations_file.setEnabled(flagObs)
        self.actionLoad_observations_file.setEnabled(False)  # not yet implemented

        self.menuExport_events.setEnabled(flag)
        self.menuExport_aggregated_events.setEnabled(flag)
        self.actionExportEventString.setEnabled(flag)
        self.actionExport_events_as_Praat_TextGrid.setEnabled(flag)
        self.actionExtract_events_from_media_files.setEnabled(flag)

        self.actionDelete_all_observations.setEnabled(flagObs)
        self.actionSelect_observations.setEnabled(flagObs)
        self.actionDelete_selected_observations.setEnabled(flagObs)
        self.actionEdit_event.setEnabled(flagObs)
        self.actionEdit_selected_events.setEnabled(flagObs)
        self.actionCheckStateEvents.setEnabled(flagObs)

        self.actionShow_spectrogram.setEnabled(flagObs)
        self.actionDistance.setEnabled(flagObs and (self.playMode == FFMPEG))


        self.actionMedia_file_information.setEnabled(flagObs)
        self.actionMedia_file_information.setEnabled(self.playerType == VLC)
        self.menuCreate_subtitles_2.setEnabled(flag)

        self.actionJumpForward.setEnabled( self.playerType == VLC)
        self.actionJumpBackward.setEnabled( self.playerType == VLC)
        self.actionJumpTo.setEnabled( self.playerType == VLC)
        self.actionPlay.setEnabled( self.playerType == VLC)
        self.actionPause.setEnabled( self.playerType == VLC)
        self.actionReset.setEnabled( self.playerType == VLC)
        self.actionFaster.setEnabled( self.playerType == VLC)
        self.actionSlower.setEnabled( self.playerType == VLC)
        self.actionNormalSpeed.setEnabled( self.playerType == VLC)
        self.actionPrevious.setEnabled( self.playerType == VLC)
        self.actionNext.setEnabled(self.playerType == VLC)
        self.actionSnapshot.setEnabled(self.playerType == VLC)
        self.actionFrame_by_frame.setEnabled(True)

        self.actionFrame_backward.setEnabled(flagObs and (self.playMode == FFMPEG))
        self.actionFrame_forward.setEnabled(flagObs and (self.playMode == FFMPEG))

        # statusbar label
        self.lbTime.setVisible( self.playerType == VLC )
        self.lbSubject.setVisible( self.playerType == VLC )
        self.lbTimeOffset.setVisible( self.playerType == VLC )
        self.lbSpeed.setVisible( self.playerType == VLC )

        self.actionTime_budget.setEnabled( self.pj[OBSERVATIONS] != {} )
        self.actionVisualize_data.setEnabled( self.pj[OBSERVATIONS] != {} )


    def connections(self):

        # menu file
        self.actionNew_project.triggered.connect(self.new_project_activated)
        self.actionOpen_project.triggered.connect(self.open_project_activated)
        self.actionEdit_project.triggered.connect(self.edit_project_activated)
        self.actionSave_project.triggered.connect(self.save_project_activated)
        self.actionSave_project_as.triggered.connect(self.save_project_as_activated)
        self.actionClose_project.triggered.connect(self.close_project)

        self.actionMedia_file_information.triggered.connect(self.media_file_info)
        self.menuCreate_subtitles_2.triggered.connect(self.create_subtitles)

        self.actionPreferences.triggered.connect(self.preferences)

        self.actionQuit.triggered.connect(self.actionQuit_activated)

        # menu observations
        self.actionNew_observation.triggered.connect(self.new_observation_triggered)
        self.actionOpen_observation.triggered.connect(self.open_observation)
        self.actionEdit_observation_2.triggered.connect(self.edit_observation )
        self.actionObservationsList.triggered.connect(self.observations_list)

        self.actionClose_observation.triggered.connect(self.close_observation)


        self.actionAdd_event.triggered.connect(self.add_event)
        self.actionEdit_event.triggered.connect(self.edit_event)

        self.actionCheckStateEvents.triggered.connect(self.check_state_events)

        self.actionSelect_observations.triggered.connect(self.select_events_between_activated)

        self.actionEdit_selected_events.triggered.connect(self.edit_selected_events)
        self.actionDelete_all_observations.triggered.connect(self.delete_all_events)
        self.actionDelete_selected_observations.triggered.connect(self.delete_selected_events)


        self.actionLoad_observations_file.triggered.connect(self.import_observations)

        self.actionExportEventTabular_TSV.triggered.connect(lambda: self.export_tabular_events("tsv"))
        self.actionExportEventTabular_ODS.triggered.connect(lambda: self.export_tabular_events("ods"))
        self.actionExportEventTabular_XLS.triggered.connect(lambda: self.export_tabular_events("xls"))

        self.actionExportEventString.triggered.connect(self.export_string_events)

        self.actionExportEventsSQL.triggered.connect(lambda: self.export_aggregated_events("sql"))
        self.actionAggregatedEventsTabularFormat.triggered.connect(lambda: self.export_aggregated_events("tab"))

        self.actionExport_events_as_Praat_TextGrid.triggered.connect(self.export_state_events_as_textgrid)

        self.actionExtract_events_from_media_files.triggered.connect(self.extract_events)

        # menu playback
        self.actionJumpTo.triggered.connect(self.jump_to)

        # menu Tools
        self.actionMapCreator.triggered.connect(self.map_creator)
        self.actionShow_spectrogram.triggered.connect(self.show_spectrogram)
        self.actionDistance.triggered.connect(self.distance)

        # menu Analyze
        self.actionTime_budget.triggered.connect(self.time_budget)
        self.actionVisualize_data.triggered.connect(self.plot_events)

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
        self.twConfiguration.itemDoubleClicked.connect(self.twEthogram_doubleClicked)
        self.twSubjects.itemDoubleClicked.connect(self.twSubjects_doubleClicked)

        # Actions for twEvents context menu
        self.twEvents.setContextMenuPolicy(Qt.ActionsContextMenu)

        #self.twEvents.addAction(self.actionEdit_event)

        #separator1 = QAction(self)
        #separator1.setSeparator(True)
        #self.twEvents.addAction(separator1)

        self.twEvents.addAction(self.actionEdit_selected_events)
        separator2 = QAction(self)
        separator2.setSeparator(True)
        self.twEvents.addAction(separator2)

        self.twEvents.addAction(self.actionDelete_selected_observations)
        self.twEvents.addAction(self.actionDelete_all_observations)


        # Actions for twSubjects context menu
        self.actionDeselectCurrentSubject.triggered.connect(self.deselectSubject)

        self.twSubjects.setContextMenuPolicy(Qt.ActionsContextMenu)
        self.twSubjects.addAction(self.actionDeselectCurrentSubject)

        # subjects

        # timer for playing
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.timer_out)

        # timer for spectrogram visualization
        self.timer_spectro = QTimer(self)
        self.timer_spectro.setInterval(50)
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


    def extract_events(self):
        """
        extract sequences from media file corresponding to coded events
        in case of point event, from -n to +n seconds are extracted (n = self.repositioningTimeOffset)
        """
        result, selectedObservations = self.selectObservations(MULTIPLE)

        if not selectedObservations:
            return

        plot_parameters = self.choose_obs_subj_behav(selectedObservations, maxTime=0, flagShowIncludeModifiers=False, flagShowExcludeBehaviorsWoEvents=False)

        if not plot_parameters["selected subjects"] or not plot_parameters["selected behaviors"]:
            return

        exportDir = QFileDialog(self).getExistingDirectory(self, "Choose a directory to extract events", os.path.expanduser("~"), options=QFileDialog(self).ShowDirsOnly)
        if not exportDir:
            return

        # check self.repositioningTimeOffset
        text, ok = QtGui.QInputDialog.getDouble(self, "Offset to substract/add to start/stop times", "Time offset (in seconds):", 0.0, 0.0, 86400, 1)
        if not ok:
            return
        try:
            timeOffset = float2decimal(text)
        except:
            print("time offset not recognized!")
            return

        flagUnpairedEventFound = False

        cursor = self.loadEventsInDB(plot_parameters["selected subjects"], selectedObservations, plot_parameters["selected behaviors"])

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

                        cursor.execute("SELECT occurence FROM events WHERE observation = ? AND subject = ? AND code = ?", (obsId, subject, behavior))
                        rows = [{"occurence":float2decimal(r["occurence"])}  for r in cursor.fetchall()]

                        if STATE in self.eventType(behavior).upper() and len(rows) % 2:  # unpaired events
                            flagUnpairedEventFound = True
                            continue

                        for idx, row in enumerate(rows):

                            mediaFileIdx = [idx1 for idx1, x in enumerate(duration1) if row["occurence"] >= sum(duration1[0:idx1])][-1]

                            globalStart = Decimal("0.000") if row["occurence"] < timeOffset else round(row["occurence"] - timeOffset, 3)
                            start = round(row["occurence"] - timeOffset - sum(duration1[0:mediaFileIdx]), 3)
                            if start < timeOffset:
                                start = Decimal("0.000")

                            if POINT in self.eventType(behavior).upper():

                                #globalStart = Decimal("0.000") if row["occurence"] < timeOffset else round(row["occurence"] - timeOffset, 3)
                                globalStop = round(row["occurence"] + timeOffset, 3)

                                #start = round(row["occurence"] - timeOffset - sum(duration1[0:mediaFileIdx]), 3)
                                #if start < timeOffset:
                                #    start = Decimal("0.000")
                                stop = round(row["occurence"] + timeOffset - sum(duration1[0:mediaFileIdx]))

                                ffmpeg_command = """{ffmpeg_bin} -i "{input}" -y -ss {start} -to {stop} "{dir}{sep}{obsId}_{player}_{subject}_{behavior}_{globalStart}-{globalStop}{extension}" """\
                                .format(ffmpeg_bin=ffmpeg_bin,
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
                                        extension=os.path.splitext(self.pj[OBSERVATIONS][obsId][FILE][nplayer][mediaFileIdx])[-1])

                                logging.debug("ffmpeg command: {}".format( ffmpeg_command ))
                                p = subprocess.Popen(ffmpeg_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
                                out, error = p.communicate()


                            if STATE in self.eventType(behavior).upper():
                                if idx % 2 == 0:

                                    #globalStart = round(row["occurence"], 3)
                                    globalStop = round(rows[idx + 1]["occurence"] + timeOffset, 3)

                                    #start = round(row["occurence"] - sum( duration1[0:mediaFileIdx]), 3)
                                    stop = round(rows[idx + 1]["occurence"] + timeOffset - sum( duration1[0:mediaFileIdx]))

                                    ffmpeg_command = """{ffmpeg_bin} -i "{input}" -y -ss {start} -to {stop} "{dir}{sep}{obsId}_{player}_{subject}_{behavior}_{globalStart}-{globalStop}{extension}" """.format(ffmpeg_bin=ffmpeg_bin,
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
                                    extension=os.path.splitext(self.pj[OBSERVATIONS][obsId][FILE][nplayer][mediaFileIdx])[-1])

                                    logging.debug("ffmpeg command: {}".format(ffmpeg_command))
                                    p = subprocess.Popen(ffmpeg_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
                                    out, error = p.communicate()

        self.statusbar.showMessage("Sequences extracted to {} directory".format(exportDir), 0)


    def generate_spectrogram(self):
        """
        generate spectrogram of all media files loaded in player #1
        """

        # check temp dir for images from ffmpeg
        if not self.ffmpeg_cache_dir:
            tmp_dir = tempfile.gettempdir()
        else:
            tmp_dir = self.ffmpeg_cache_dir

        import plot_spectrogram
        for media in self.pj[OBSERVATIONS][self.observationId][FILE][PLAYER1]:
            if os.path.isfile(media):
                _ = plot_spectrogram.graph_spectrogram(mediaFile=media, tmp_dir=tmp_dir, chunk_size=self.chunk_length, ffmpeg_bin=self.ffmpeg_bin)  # return first chunk PNG file (not used)


    def show_spectrogram(self):
        """
        show spectrogram window if any
        """
        try:
            self.spectro.show()
        except:
            logging.debug("spectro show not OK")
            # remember if player paused
            flagPaused = self.mediaListPlayer.get_state() == vlc.State.Paused
            self.pause_video()


            if dialog.MessageDialog(programName, ("You chose to visualize the spectrogram during this observation.<br>"
                                                  "Choose YES to generate the spectrogram.\n\n"
                                                  "Spectrogram generation can take some time for long media, be patient"), [YES, NO ]) == YES:

                self.generate_spectrogram()

                if not self.ffmpeg_cache_dir:
                    tmp_dir = tempfile.gettempdir()
                else:
                    tmp_dir = self.ffmpeg_cache_dir

                currentMediaTmpPath = tmp_dir + os.sep + os.path.basename(url2path(self.mediaplayer.get_media().get_mrl()))
                logging.debug('currentMediaTmpPath', currentMediaTmpPath)

                self.pj[OBSERVATIONS][self.observationId]["visualize_spectrogram"] = True

                self.spectro = plot_spectrogram.Spectrogram("{}.wav.0-{}.spectrogram.png".format(currentMediaTmpPath, self.chunk_length))
                # connect signal from spectrogram class to testsignal function to receive keypress events
                self.spectro.setWindowFlags(Qt.WindowStaysOnTopHint)
                self.spectro.sendEvent.connect(self.signal_from_spectrogram)
                self.spectro.show()
                self.timer_spectro.start()

            if not flagPaused:
                self.play_video()


    def timer_spectro_out(self):
        """
        timer for spectrogram visualization
        """

        if not "visualize_spectrogram" in self.pj[OBSERVATIONS][self.observationId] or not self.pj[OBSERVATIONS][self.observationId]["visualize_spectrogram"]:
            return

        if self.playerType == LIVE:
            QMessageBox.warning(self, programName, "The spectrogram visualization is not available for live observations")
            return

        if self.playerType == VLC:
            if self.playMode == VLC:

                currentMediaTime = self.mediaplayer.get_time()

            if self.playMode == FFMPEG:
                # get time in current media
                currentMedia, frameCurrentMedia = self.getCurrentMediaByFrame(PLAYER1, self.FFmpegGlobalFrame, list(self.fps.values())[0] )

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

            currentChunkFileName = "{}.wav.{}-{}.spectrogram.png".format(currentMediaTmpPath, currentChunk * self.chunk_length, (currentChunk + 1) * self.chunk_length)

            if not os.path.isfile(currentChunkFileName):
                self.timer_spectro.stop()

                if dialog.MessageDialog(programName, ("Spectrogram file not found.<br>"
                                                      "Do you want to generate it now?<br>"
                                                      "Spectrogram generation can take some time for long media, be patient"), [YES, NO ]) == YES:

                    self.generate_spectrogram()
                    self.timer_spectro.start()

                return

            self.spectro.pixmap.load(currentChunkFileName)
            self.spectro.w, self.spectro.h = self.spectro.pixmap.width(), self.spectro.pixmap.height()

            self.spectro.item = QGraphicsPixmapItem(self.spectro.pixmap)

            self.spectro.scene.addItem(self.spectro.item)
            self.spectro.item.setPos(0, 0)

        get_time = (currentMediaTime % (self.chunk_length * 1000) / (self.chunk_length*1000))

        self.spectro.item.setPos(-int(get_time * self.spectro.w), 0 )

        self.spectro.memChunk = currentChunk


    def map_creator(self):
        """
        show map creator window and hide program main window
        """
        self.mapCreatorWindow = map_creator.MapCreatorWindow()
        self.mapCreatorWindow.move(self.pos())
        self.mapCreatorWindow.resize(640, 640)
        self.mapCreatorWindow.closed.connect(self.show)
        self.mapCreatorWindow.show()
        self.hide()


    def open_observation(self):
        """
        open an observation
        """

        # check if current observation must be closed to open a new one
        if self.observationId:
            response = dialog.MessageDialog(programName, "The current observation will be closed. Do you want to continue?", [YES, NO])
            if response == NO:
                return
            else:
                self.close_observation()

        result, selectedObs = self.selectObservations( OPEN )

        if selectedObs:
            self.observationId = selectedObs[0]

            # load events in table widget
            self.loadEventsInTW(self.observationId)

            if self.pj[OBSERVATIONS][self.observationId][ TYPE ] == LIVE:
                self.playerType = LIVE
                self.initialize_new_live_observation()

            if self.pj[OBSERVATIONS][self.observationId][ TYPE ] in [MEDIA]:

                if not self.initialize_new_observation_vlc():
                    self.observationId = ""
                    self.twEvents.setRowCount(0)
                    self.menu_options()

            self.menu_options()
            # title of dock widget  “  ”
            self.dwObservations.setWindowTitle("Events for “{}” observation".format(self.observationId))


    def edit_observation(self):
        """
        edit observation
        """

        # check if current observation must be closed to open a new one
        if self.observationId:
            if dialog.MessageDialog(programName, "The current observation will be closed. Do you want to continue?", [YES, NO]) == NO:
                return
            else:
                self.close_observation()

        result, selectedObs = self.selectObservations(EDIT)

        if selectedObs:
            self.new_observation(mode=EDIT, obsId=selectedObs[0])

    def check_state_events(self):
        """
        check state events for each subject in current observation
        check if number is odd
        """

        out = ''
        flagStateEvent = False
        subjects = [subject for _, subject, _, _, _ in  self.pj[OBSERVATIONS][self.observationId][EVENTS]]
        for subject in sorted(set(subjects)):
            behaviors = [behavior for _, subj, behavior, _, _ in  self.pj[OBSERVATIONS][self.observationId][EVENTS] if subj == subject ]
            for behavior in sorted(set(behaviors)):
                if "STATE" in self.eventType(behavior).upper():
                    flagStateEvent = True
                    behavior_modifiers = [behav + "@@@" + mod for _, subj, behav, mod, _ in  self.pj[OBSERVATIONS][self.observationId][EVENTS] if behav == behavior and subj == subject]
                    for behavior_modifier in set(behavior_modifiers):
                        if behavior_modifiers.count(behavior_modifier) % 2:
                            if subject:
                                subject = " for subject <b>{}</b>".format(subject)
                            modifier = behavior_modifier.split("@@@")[1]
                            if modifier:
                                modifier = "(modifier <b>{}</b>)".format(modifier)
                            out += "The behavior <b>{0}</b> {1} is not PAIRED {2}<br>".format(behavior, modifier, subject)

        if not out:
            out = "State events are PAIRED"
        if flagStateEvent:
            QMessageBox.warning(self, programName + " - State events check", out)
        else:
            QMessageBox.warning(self, programName + " - State events check", "No state events in current observation")



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

                # load events in table widget
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
                    self.new_observation( mode=EDIT, obsId=selectedObs[0])   # observation id to edit
                else:
                    QMessageBox.warning(self, programName , 'The observation <b>%s</b> is running!<br>Close it before editing.' % self.observationId)


    def actionCheckUpdate_activated(self, flagMsgOnlyIfNew = False):
        """
        check BORIS web site for updates
        """
        try:
            versionURL = "http://www.boris.unito.it/static/ver.dat"
            lastVersion = Decimal(urllib.request.urlopen( versionURL ).read().strip().decode("utf-8"))
            self.saveConfigFile(lastCheckForNewVersion = int(time.mktime(time.localtime())))

            if lastVersion > Decimal(__version__):
                msg = """A new version is available: v. <b>{}</b><br>Go to <a href="http://www.boris.unito.it">http://www.boris.unito.it</a> to install it.""".format(lastVersion)
            else:
                msg = "The version you are using is the last one: <b>{}</b>".format(__version__)

            QMessageBox.information(self, programName, msg)

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
                newTime = int( jt.te.value() * 1000)

            if self.playerType == VLC:

                if self.playMode == FFMPEG:
                    frameDuration = Decimal(1000 / list(self.fps.values())[0])
                    currentFrame = round( newTime/ frameDuration )
                    self.FFmpegGlobalFrame = currentFrame
                    if self.FFmpegGlobalFrame > 0:
                        self.FFmpegGlobalFrame -= 1
                    self.FFmpegTimerOut()

                else: # play mode VLC

                    if self.media_list.count() == 1:

                        if newTime < self.mediaplayer.get_length():
                            self.mediaplayer.set_time( newTime )
                            if self.simultaneousMedia:
                                self.mediaplayer2.set_time( int(self.mediaplayer.get_time()  - self.pj[OBSERVATIONS][self.observationId][TIME_OFFSET_SECOND_PLAYER] * 1000) )

                        else:
                            QMessageBox.warning(self, programName , "The indicated position is behind the end of media ({})".format(seconds2time(self.mediaplayer.get_length()/1000)))

                    elif self.media_list.count() > 1:

                        if newTime  < sum(self.duration):

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

                                    self.mediaplayer.set_time(newTime - sum(self.duration[0 : self.media_list.index_of_item(self.mediaplayer.get_media())]))

                                    break
                                tot += d
                        else:
                            QMessageBox.warning(self, programName, "The indicated position is behind the total media duration ({})".format(seconds2time(sum(self.duration)/1000)))

                    self.timer_out()
                    self.timer_spectro_out()


    def previous_media_file(self):
        """
        go to previous media file (if any)
        """
        if self.playerType == VLC:

            if self.playMode == FFMPEG:

                currentMedia = ""
                for idx,media in enumerate(self.pj[OBSERVATIONS][self.observationId][FILE][PLAYER1]):
                    if self.FFmpegGlobalFrame < self.duration[idx + 1]:
                        self.FFmpegGlobalFrame = self.duration[idx - 1]
                        break
                self.FFmpegGlobalFrame -= 1
                self.FFmpegTimerOut()

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

                # no subtitles
                #self.mediaplayer.video_set_spu(0)

    def next_media_file(self):
        '''
        go to next media file (if any)
        '''
        if self.playerType == VLC:

            if self.playMode == FFMPEG:
                for idx,media in enumerate(self.pj[OBSERVATIONS][self.observationId][FILE][PLAYER1]):
                    if self.FFmpegGlobalFrame < self.duration[idx + 1]:
                        self.FFmpegGlobalFrame = self.duration[idx + 1]
                        break
                self.FFmpegGlobalFrame -= 1
                self.FFmpegTimerOut()

            else:

                # check if media not last media
                if self.media_list.index_of_item(self.mediaplayer.get_media()) <  self.media_list.count() - 1:

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
                # no subtitles
                #self.mediaplayer.video_set_spu(0)


    def setVolume(self):
        """
        set volume for player #1
        """

        self.mediaplayer.audio_set_volume( self.volumeslider.value())

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


    def deselectSubject(self):
        '''
        deselect the current subject
        '''
        self.currentSubject = ""
        self.lbSubject.setText( "<b>{}</b>".format(NO_FOCAL_SUBJECT))
        self.lbFocalSubject.setText(NO_FOCAL_SUBJECT)

    def selectSubject(self, subject):
        '''
        deselect the current subject
        '''
        self.currentSubject = subject
        self.lbSubject.setText("Subject: <b>{}</b>".format(self.currentSubject))
        self.lbFocalSubject.setText(" Focal subject: <b>{}</b>".format(self.currentSubject))

    def preferences(self):
        """
        show preferences window
        """

        preferencesWindow = preferences.Preferences()

        if self.timeFormat == S:
            preferencesWindow.cbTimeFormat.setCurrentIndex(0)

        if self.timeFormat == HHMMSS:
            preferencesWindow.cbTimeFormat.setCurrentIndex(1)

        preferencesWindow.sbffSpeed.setValue( self.fast )
        preferencesWindow.sbRepositionTimeOffset.setValue(self.repositioningTimeOffset)
        preferencesWindow.sbSpeedStep.setValue( self.play_rate_step)
        # automatic backup
        preferencesWindow.sbAutomaticBackup.setValue( self.automaticBackup )
        # separator for behavioural strings
        preferencesWindow.leSeparator.setText( self.behaviouralStringsSeparator )
        # confirm sound
        preferencesWindow.cbConfirmSound.setChecked( self.confirmSound )
        # embed player
        preferencesWindow.cbEmbedPlayer.setChecked( self.embedPlayer )
        # alert no focal subject
        preferencesWindow.cbAlertNoFocalSubject.setChecked( self.alertNoFocalSubject )
        # tracking cursor above event
        preferencesWindow.cbTrackingCursorAboveEvent.setChecked( self.trackingCursorAboveEvent )
        # check for new version
        preferencesWindow.cbCheckForNewVersion.setChecked( self.checkForNewVersion )

        # FFmpeg for frame by frame mode
        '''
        preferencesWindow.pbBrowseFFmpeg.setEnabled( preferencesWindow.cbAllowFrameByFrameMode.isChecked() )
        preferencesWindow.lbFFmpeg.setEnabled( preferencesWindow.cbAllowFrameByFrameMode.isChecked() )
        preferencesWindow.leFFmpegPath.setEnabled( preferencesWindow.cbAllowFrameByFrameMode.isChecked() )

        preferencesWindow.pbBrowseFFmpegCacheDir.setEnabled( preferencesWindow.cbAllowFrameByFrameMode.isChecked() )
        preferencesWindow.lbFFmpegCacheDir.setEnabled( preferencesWindow.cbAllowFrameByFrameMode.isChecked() )
        preferencesWindow.leFFmpegCacheDir.setEnabled( preferencesWindow.cbAllowFrameByFrameMode.isChecked() )

        preferencesWindow.lbFFmpegCacheDirMaxSize.setEnabled( preferencesWindow.cbAllowFrameByFrameMode.isChecked() )
        preferencesWindow.sbFFmpegCacheDirMaxSize.setEnabled( preferencesWindow.cbAllowFrameByFrameMode.isChecked() )
        '''
        preferencesWindow.lbFFmpegPath.setText("FFmpeg path: {}".format(self.ffmpeg_bin))
        preferencesWindow.leFFmpegCacheDir.setText(self.ffmpeg_cache_dir)
        preferencesWindow.sbFFmpegCacheDirMaxSize.setValue(self.ffmpeg_cache_dir_max_size)

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
                self.automaticBackupTimer.start( self.automaticBackup * 60000 )
            else:
                self.automaticBackupTimer.stop()

            self.behaviouralStringsSeparator = preferencesWindow.leSeparator.text()

            self.confirmSound = preferencesWindow.cbConfirmSound.isChecked()

            self.embedPlayer = preferencesWindow.cbEmbedPlayer.isChecked()

            self.alertNoFocalSubject = preferencesWindow.cbAlertNoFocalSubject.isChecked()

            self.trackingCursorAboveEvent = preferencesWindow.cbTrackingCursorAboveEvent.isChecked()

            self.checkForNewVersion = preferencesWindow.cbCheckForNewVersion.isChecked()

            if self.observationId:
                self.loadEventsInTW( self.observationId )
                self.display_timeoffset_statubar( self.pj[OBSERVATIONS][self.observationId][TIME_OFFSET] )

            self.ffmpeg_cache_dir = preferencesWindow.leFFmpegCacheDir.text()
            self.ffmpeg_cache_dir_max_size = preferencesWindow.sbFFmpegCacheDirMaxSize.value()

            self.menu_options()

            self.saveConfigFile()

    def getCurrentMediaByFrame(self, player, requiredFrame, fps):
        """
        get:
        player
        required frame
        fps

        returns:
        currentMedia
        frameCurrentMedia
        """
        currentMedia, frameCurrentMedia = '', 0
        frameMs = 1000 / fps
        for idx, media in enumerate(self.pj[OBSERVATIONS][self.observationId][FILE][player]):
            if requiredFrame * frameMs < sum(self.duration[0:idx + 1 ]):
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

        print('globalTimeMs',globalTimeMs)
        print( self.duration )

        for idx, media in enumerate(self.pj[OBSERVATIONS][obsId][FILE][player]):
            if globalTimeMs < sum(self.duration[0:idx + 1]):
                currentMedia = media
                currentMediaTime = globalTimeMs - sum(self.duration[0:idx])
                break

        return currentMedia, round(currentMediaTime/1000,3)



    def FFmpegTimerOut(self):
        """
        triggered when frame-by-frame mode is activated:
        read next frame and update image
        """

        logging.debug("FFmpegTimerOut function")

        fps = list(self.fps.values())[0]

        logging.debug("fps {0}".format(fps))

        frameMs = 1000 / fps

        logging.debug("framMs {0}".format(frameMs))

        requiredFrame = self.FFmpegGlobalFrame + 1

        logging.debug("required frame: {0}".format( requiredFrame ))
        logging.debug("sum self.duration {0}".format( sum(self.duration)))

        # check if end of last media
        if requiredFrame * frameMs >= sum(self.duration):
            logging.debug("end of last media")
            return

        currentMedia, frameCurrentMedia = self.getCurrentMediaByFrame(PLAYER1, requiredFrame, fps)

        if "visualize_spectrogram" in self.pj[OBSERVATIONS][self.observationId] and self.pj[OBSERVATIONS][self.observationId]["visualize_spectrogram"]:
            self.timer_spectro_out()


        md5FileName = hashlib.md5(currentMedia.encode("utf-8")).hexdigest()

        #logging.debug('imagesList {0}'.format(self.imagesList))
        logging.debug('image {0}'.format( '%s-%d' % (md5FileName, int(frameCurrentMedia / fps))))

        ffmpeg_command = '"{ffmpeg_bin}" -ss {pos} -loglevel quiet -i "{currentMedia}" -vframes {fps} -qscale:v 2 "{imageDir}{sep}BORIS_{fileName}-{pos}_%d.{extension}"'.format(
        ffmpeg_bin=self.ffmpeg_bin,
        pos=int(frameCurrentMedia / fps),
        currentMedia=currentMedia,
        fps=str(round(fps) +1),
        imageDir=self.imageDirectory,
        sep=os.sep,
        fileName=md5FileName,
        extension=BITMAP_EXT)

        logging.debug('ffmpeg command: {0}'.format(ffmpeg_command))

        p = subprocess.Popen(ffmpeg_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True )
        out, error = p.communicate()
        out = out.decode('utf-8')
        error = error.decode('utf-8')

        if error:
            logging.debug('ffmpeg error: {0}'.format( error ))

        self.imagesList.update( [ '%s-%d' % (md5FileName, int(frameCurrentMedia/ fps)) ] )


        img = '%(imageDir)s%(sep)sBORIS_%(fileName)s-%(second)d_%(frame)d.%(extension)s' % \
              {'imageDir': self.imageDirectory, 'sep': os.sep, 'fileName': md5FileName, 'second':  int(frameCurrentMedia / fps),
               'frame':( frameCurrentMedia - int(frameCurrentMedia / fps) * fps) + 1,
               'extension': BITMAP_EXT}

        if not os.path.isfile(img):
            logging.warning("image not found: {0}".format(img))
            return

        self.pixmap = QtGui.QPixmap(img)
        self.lbFFmpeg.setPixmap(self.pixmap.scaled(self.lbFFmpeg.size(), Qt.KeepAspectRatio))
        self.FFmpegGlobalFrame = requiredFrame

        currentTime = self.getLaps() * 1000

        self.lbTime.setText( "{currentMediaName}: <b>{currentTime} / {totalTime}</b> frame: <b>{currentFrame}</b>".format(
                             currentMediaName=currentMedia,
                             currentTime=self.convertTime(currentTime / 1000),
                             totalTime=self.convertTime(Decimal(self.mediaplayer.get_length() / 1000)),
                             currentFrame=round(self.FFmpegGlobalFrame)
                             ))

        # extract State events
        StateBehaviorsCodes = [self.pj[ETHOGRAM][x]['code'] for x in [y for y in self.pj[ETHOGRAM]
                                if 'State' in self.pj[ETHOGRAM][y][TYPE]]]

        self.currentStates = {}

        # add states for no focal subject
        self.currentStates[ '' ] = []
        for sbc in StateBehaviorsCodes:
            if len([x[ pj_obs_fields['code']] for x in self.pj[OBSERVATIONS][self.observationId][EVENTS]
                       if x[pj_obs_fields['subject']] == '' and x[pj_obs_fields['code']] == sbc and x[pj_obs_fields['time']] <= currentTime /1000]) % 2: # test if odd
                self.currentStates[''].append(sbc)

        # add states for all configured subjects
        for idx in self.pj[SUBJECTS]:

            # add subject index
            self.currentStates[ idx ] = []
            for sbc in StateBehaviorsCodes:
                if len( [ x[ pj_obs_fields['code'] ] for x in self.pj[OBSERVATIONS][self.observationId][EVENTS ]
                           if x[ pj_obs_fields['subject'] ] == self.pj[SUBJECTS][idx]['name'] and x[ pj_obs_fields['code'] ] == sbc and x[ pj_obs_fields['time'] ] <= currentTime / 1000 ] ) % 2: # test if odd
                    self.currentStates[idx].append(sbc)

        # show current states
        if self.currentSubject:
            # get index of focal subject (by name)
            idx = [idx for idx in self.pj[SUBJECTS] if self.pj[SUBJECTS][idx]['name'] == self.currentSubject][0]
            self.lbCurrentStates.setText("%s" % (", ".join(self.currentStates[ idx ])))
        else:
            self.lbCurrentStates.setText("%s" % (", ".join(self.currentStates[""])))

        # show selected subjects
        for idx in [str(x) for x in sorted([int(x) for x in self.pj[SUBJECTS].keys() ])]:
            self.twSubjects.item(int(idx), len( subjectsFields ) ).setText(",".join(self.currentStates[idx]) )

        # show tracking cursor
        self.get_events_current_row()

    def close_measurement_widget(self):
        self.measurement_w.close()
        self.measurement_w = None

    def distance(self):
        import measurement_widget
        self.measurement_w = measurement_widget.wgMeasurement(logging.getLogger().getEffectiveLevel())
        self.measurement_w.setWindowFlags(Qt.WindowStaysOnTopHint)
        self.measurement_w.closeSignal.connect(self.close_measurement_widget)
        self.measurement_w.show()


    def getPoslbFFmpeg(self, event):
        """
        return click position on frame and distance between 2 last clicks
        """

        def draw_point(x, y, color):
            RADIUS = 6
            painter	= QPainter()
            painter.begin(self.lbFFmpeg.pixmap())
            painter.setPen(QColor(color))
            painter.drawEllipse(QPoint(x, y), RADIUS, RADIUS)
            # cross inside circle
            painter.drawLine(x - RADIUS, y, x + RADIUS, y)
            painter.drawLine(x, y - RADIUS, x, y + RADIUS)
            painter.end()
            self.lbFFmpeg.update()

        def draw_line(x1, y1, x2, y2, color):
            painter	= QPainter()
            painter.begin(self.lbFFmpeg.pixmap())
            painter.setPen(QColor(color))
            painter.drawLine(x1, y1, x2, y2)
            painter.end()
            self.lbFFmpeg.update()


        if self.measurement_w:
            x = event.pos().x()
            y = event.pos().y()

            # distance
            if self.measurement_w.rbDistance.isChecked():
                if event.button() == 1:   # left
                    draw_point(x ,y, "blue")
                    self.memx, self.memy = x, y

                if event.button() == 2 and self.memx != -1 and self.memy != -1:
                    draw_point(x, y, "red")
                    draw_line(self.memx, self.memy, x, y, "red")

                    d = ((x - self.memx)**2 + (y - self.memy)**2)**0.5
                    try:
                        d = d / float(self.measurement_w.lePx.text()) * float(self.measurement_w.leRef.text())
                    except:
                        QMessageBox.critical(self, programName, "Check reference and pixel values! Values must be numeric.", QMessageBox.Ok | QMessageBox.Default, QMessageBox.NoButton)

                    self.measurement_w.pte.appendPlainText("Time: {}\tFrame: {}\tDistance: {}".format(self.getLaps(),
                                                                                                         self.FFmpegGlobalFrame,
                                                                                                         round(d, 1)))
                    self.measurement_w.flagSaved = False
                    self.memx, self.memy = -1, -1

            # angle 1st clic -> vertex
            if self.measurement_w.rbAngle.isChecked():
                if event.button() == 1:   # left for vertex
                    draw_point(x, y, "red")
                    self.memPoints = [(x, y)]

                if event.button() == 2 and len(self.memPoints):
                    draw_point(x, y, "blue")
                    draw_line(self.memPoints[0][0], self.memPoints[0][1], x, y, "blue")

                    self.memPoints.append((x, y))

                    if len( self.memPoints ) == 3:
                        self.measurement_w.pte.appendPlainText("Time: {}\tFrame: {}\tAngle: {}".format(self.getLaps(),
                                                                                                      self.FFmpegGlobalFrame,
                                                                                                      round(angle(self.memPoints[0], self.memPoints[1], self.memPoints[2]), 1)
                                                                                                      )
                                                                                                      )
                        self.measurement_w.flagSaved = False
                        self.memPoints = []

            # Area
            if self.measurement_w.rbArea.isChecked():
                if event.button() == 1:   # left
                    draw_point(x, y, "blue")
                    if len(self.memPoints):
                        draw_line(self.memPoints[-1][0], self.memPoints[-1][1], x, y, "blue")
                    self.memPoints.append((x, y))

                if event.button() == 2 and len(self.memPoints) >= 2:
                    draw_point(x, y, "red")
                    draw_line(self.memPoints[-1][0], self.memPoints[-1][1], x, y, "blue")
                    self.memPoints.append((x, y))
                    # close polygon
                    draw_line(self.memPoints[-1][0], self.memPoints[-1][1], self.memPoints[0][0], self.memPoints[0][1], "blue")
                    a = polygon_area(self.memPoints)
                    try:
                        a = a / (float(self.measurement_w.lePx.text())**2) * float(self.measurement_w.leRef.text())**2
                    except:
                        QMessageBox.critical(self, programName, """Check reference and pixel values! Values must be numeric.""", QMessageBox.Ok | QMessageBox.Default, QMessageBox.NoButton)

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
        self.videoframe = QtGui.QFrame()
        self.palette = self.videoframe.palette()
        self.palette.setColor (QtGui.QPalette.Window, QtGui.QColor(0, 0, 0))
        self.videoframe.setPalette(self.palette)
        self.videoframe.setAutoFillBackground(True)

        self.volumeslider = QtGui.QSlider(QtCore.Qt.Vertical, self)
        self.volumeslider.setMaximum(100)
        self.volumeslider.setValue(self.mediaplayer.audio_get_volume())
        self.volumeslider.setToolTip("Volume")
        self.volumeslider.sliderMoved.connect(self.setVolume)

        self.hsVideo = QSlider(QtCore.Qt.Horizontal, self)
        self.hsVideo.setMaximum(slider_maximum)
        self.hsVideo.sliderMoved.connect(self.hsVideo_sliderMoved)

        self.video1layout = QtGui.QHBoxLayout()
        self.video1layout.addWidget(self.videoframe)
        self.video1layout.addWidget(self.volumeslider)

        self.vboxlayout = QtGui.QVBoxLayout()

        self.vboxlayout.addLayout(self.video1layout)

        self.vboxlayout.addWidget(self.hsVideo)
        self.hsVideo.setVisible(True)

        self.videoTab = QWidget()

        self.videoTab.setLayout(self.vboxlayout)

        self.toolBox.insertItem(VIDEO_TAB, self.videoTab, "Audio/Video")

        self.actionFrame_by_frame.setEnabled(False)


        self.ffmpegLayout = QHBoxLayout()
        self.lbFFmpeg = QLabel(self)
        self.lbFFmpeg.setAlignment(Qt.AlignLeft | Qt.AlignTop  )
        self.lbFFmpeg.setBackgroundRole(QPalette.Base)
        self.lbFFmpeg.mousePressEvent = self.getPoslbFFmpeg

        self.ffmpegLayout.addWidget(self.lbFFmpeg)

        self.ffmpegTab = QtGui.QWidget()
        self.ffmpegTab.setLayout(self.ffmpegLayout)

        self.toolBox.insertItem(FRAME_TAB, self.ffmpegTab, "Frame by frame")
        self.toolBox.setItemEnabled (FRAME_TAB, False)

        self.actionFrame_by_frame.setEnabled(True)

    def initialize_2nd_video_tab(self):
        '''
        initialize second video player (use only if first player initialized)
        '''
        self.mediaplayer2 = self.instance.media_player_new()

        self.media_list2 = self.instance.media_list_new()

        self.mediaListPlayer2 = self.instance.media_list_player_new()
        self.mediaListPlayer2.set_media_player(self.mediaplayer2)

        app.processEvents()

        self.videoframe2 = QtGui.QFrame()
        self.palette2 = self.videoframe2.palette()
        self.palette2.setColor (QtGui.QPalette.Window, QtGui.QColor(0,0,0))
        self.videoframe2.setPalette(self.palette2)
        self.videoframe2.setAutoFillBackground(True)

        self.volumeslider2 = QtGui.QSlider(QtCore.Qt.Vertical, self)
        self.volumeslider2.setMaximum(100)
        self.volumeslider2.setValue(self.mediaplayer2.audio_get_volume())
        self.volumeslider2.setToolTip("Volume")

        self.volumeslider2.sliderMoved.connect(self.setVolume2)

        self.video2layout = QtGui.QHBoxLayout()
        self.video2layout.addWidget(self.videoframe2)
        self.video2layout.addWidget(self.volumeslider2)

        self.vboxlayout.insertLayout(1, self.video2layout)


    def check_if_media_available(self):
        '''
        check if every media available for observationId
        '''

        if not PLAYER1 in self.pj[OBSERVATIONS][self.observationId][FILE]:
            return False

        if type(self.pj[OBSERVATIONS][self.observationId][FILE][PLAYER1]) != type([]):
            return False

        if not self.pj[OBSERVATIONS][self.observationId][FILE][PLAYER1]:
            return False

        for mediaFile in self.pj[OBSERVATIONS][self.observationId][FILE][PLAYER1]:
            if not os.path.isfile( mediaFile ):
                return False

        if PLAYER2 in self.pj[OBSERVATIONS][self.observationId][FILE]:

            if type(self.pj[OBSERVATIONS][self.observationId][FILE][PLAYER2]) != type([]):
                return False

            if self.pj[OBSERVATIONS][self.observationId][FILE][PLAYER2]:
                for mediaFile in self.pj[OBSERVATIONS][self.observationId][FILE][PLAYER2]:
                    if not os.path.isfile( mediaFile ):
                        return False
        return True

    def check_if_media_in_project_directory(self):

        try:
            for player in [PLAYER1, PLAYER2]:
                for mediaFile in self.pj[OBSERVATIONS][self.observationId][FILE][player]:
                    if not os.path.isfile( os.path.dirname(self.projectFileName) +os.sep+ os.path.basename(mediaFile) ):
                        return False
        except:
            return False
        return True


    def initialize_new_observation_vlc(self):
        '''
        initialize new observation for VLC
        '''

        logging.debug('initialize new observation for VLC')

        useMediaFromProjectDirectory = NO

        if not self.check_if_media_available():

            if self.check_if_media_in_project_directory():

                useMediaFromProjectDirectory = dialog.MessageDialog(programName, """Media file was/were not found in its/their original path(s) but in project directory.<br>
                Do you want to convert media file paths?""", [YES, NO ])

                if useMediaFromProjectDirectory == NO:
                    QMessageBox.warning(self, programName, """The observation will be opened in VIEW mode.<br>
                    It will not be allowed to log events.<br>Modify the media path to point an existing media file to log events or copy media file in the BORIS project directory.""",
                    QMessageBox.Ok | QMessageBox.Default, QMessageBox.NoButton)

                    self.playerType = VIEWER
                    self.playMode = ''
                    self.dwObservations.setVisible(True)
                    return True

            else:
                QMessageBox.critical(self, programName, """A media file was not found!<br>The observation will be opened in VIEW mode.<br>
                It will not be allowed to log events.<br>Modify the media path to point an existing media file to log events or copy media file in the BORIS project directory.""",
                QMessageBox.Ok | QMessageBox.Default, QMessageBox.NoButton)

                self.playerType = VIEWER
                self.playMode = ''
                self.dwObservations.setVisible(True)
                return True

        # check if media list player 1 contains more than 1 media
        if len(self.pj[OBSERVATIONS][self.observationId][FILE][PLAYER1]) > 1 \
            and \
           PLAYER2 in self.pj[OBSERVATIONS][self.observationId][FILE] and  self.pj[OBSERVATIONS][self.observationId][FILE][PLAYER2]:

               QMessageBox.warning(self, programName, "It is not yet possible to play a second media when more media are loaded in the first media player")
               return False

        self.playerType = VLC
        self.playMode = VLC

        self.fps = {}

        self.toolBar.setEnabled(False)
        self.dwObservations.setVisible(True)
        self.toolBox.setVisible(True)
        self.lbFocalSubject.setVisible(True)
        self.lbCurrentStates.setVisible(True)

        # init duration of media file
        del self.duration[0: len(self.duration)]

        # add all media files to media list
        self.simultaneousMedia = False

        if useMediaFromProjectDirectory == YES:
            for idx, mediaFile in enumerate(self.pj[OBSERVATIONS][self.observationId][FILE][PLAYER1]):
                self.pj[OBSERVATIONS][self.observationId][FILE][PLAYER1][idx] = os.path.dirname(self.projectFileName) +os.sep+ os.path.basename(mediaFile)
                self.projectChanged = True

        for mediaFile in self.pj[OBSERVATIONS][self.observationId][FILE][PLAYER1]:
            logging.debug("media file: {}".format(mediaFile))
            try:
                self.instance
            except AttributeError:
                self.initialize_video_tab()

            media = self.instance.media_new(mediaFile)
            media.parse()

            # media duration
            try:
                mediaLength = self.pj[OBSERVATIONS][self.observationId]["media_info"]["length"][mediaFile] * 1000
                mediaFPS = self.pj[OBSERVATIONS][self.observationId]["media_info"]["fps"][mediaFile]
            except:
                logging.debug("media_info key not found")
                nframe, videoTime, videoDuration, fps, hasVideo, hasAudio = accurate_media_analysis( self.ffmpeg_bin, mediaFile)
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

            logging.debug("mediaLength: {}".format( mediaLength ))
            logging.debug("mediaFPS: {}".format( mediaFPS ))

            self.duration.append(int(mediaLength))
            self.fps[mediaFile] = mediaFPS

            logging.debug("self.duration: {}".format( self.duration ))
            logging.debug("self.fps: {}".format( self.fps ))

            self.media_list.add_media(media)

        # add media list to media player list
        self.mediaListPlayer.set_media_list(self.media_list)

        # display media player in videoframe
        if self.embedPlayer:

            if sys.platform.startswith("linux"): # for Linux using the X Server
                self.mediaplayer.set_xwindow(self.videoframe.winId())

            elif sys.platform.startswith("win"): # for Windows
                self.mediaplayer.set_hwnd( int(self.videoframe.winId()) )

        # for mac always embed player
        if sys.platform == "darwin": # for MacOS
            self.mediaplayer.set_nsobject(self.videoframe.winId())

        # check if fps changes between media
        """
        TODO: check
        if FFMPEG in self.availablePlayers:
            if len(set( self.fps.values() )) != 1:
                QMessageBox.critical(self, programName, "The frame-by-frame mode will not be available because the video files have different frame rates (%s)." % (", ".join([str(i) for i in list(self.fps.values())])),\
                 QMessageBox.Ok | QMessageBox.Default, QMessageBox.NoButton)
        """

        # show first frame of video
        logging.debug("playing media #{0}".format( 0 ))

        self.mediaListPlayer.play_item_at_index( 0 )
        app.processEvents()

        # play mediaListPlayer for a while to obtain media information
        while True:
            if self.mediaListPlayer.get_state() in [vlc.State.Playing, vlc.State.Ended]:
                break

        self.mediaListPlayer.pause()

        app.processEvents()

        self.mediaplayer.set_time(0)

        # no subtitles
        #self.mediaplayer.video_set_spu(0)

        self.FFmpegTimer = QTimer(self)
        self.FFmpegTimer.timeout.connect(self.FFmpegTimerOut)

        print( self.fps.values() )
        try:
            self.FFmpegTimerTick = int(1000 / list(self.fps.values())[0])
        except:
            self.FFmpegTimerTick = 40

        self.FFmpegTimer.setInterval(self.FFmpegTimerTick)

        # check for second media to be played together
        if PLAYER2 in self.pj[OBSERVATIONS][self.observationId][FILE] and  self.pj[OBSERVATIONS][self.observationId][FILE][PLAYER2]:

                if useMediaFromProjectDirectory == YES:
                    for idx, mediaFile in enumerate(self.pj[OBSERVATIONS][self.observationId][FILE][PLAYER2]):
                        self.pj[OBSERVATIONS][self.observationId][FILE][PLAYER2][idx] = os.path.dirname(self.projectFileName) +os.sep+ os.path.basename(mediaFile)
                        self.projectChanged = True

                # create 2nd mediaplayer
                self.simultaneousMedia = True

                self.initialize_2nd_video_tab()

                # add media file
                for mediaFile in self.pj[OBSERVATIONS][self.observationId][FILE][PLAYER2]:

                    media = self.instance.media_new( mediaFile )
                    media.parse()

                    logging.debug("media file 2 {0}  duration {1}".format(mediaFile, media.get_duration()))

                    self.media_list2.add_media(media)

                self.mediaListPlayer2.set_media_list(self.media_list2)

                if self.embedPlayer:
                    if sys.platform.startswith("linux"): # for Linux using the X Server
                        self.mediaplayer2.set_xwindow(self.videoframe2.winId())

                    elif sys.platform.startswith("win32"): # for Windows
                        self.mediaplayer2.set_hwnd( int(self.videoframe2.winId()) )

                        # self.mediaplayer.set_hwnd(self.videoframe.winId())

                # for mac always embed player
                if sys.platform == "darwin": # for MacOS
                    self.mediaplayer2.set_nsobject(self.videoframe2.winId())

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
                if TIME_OFFSET_SECOND_PLAYER in self.pj[OBSERVATIONS][self.observationId] \
                    and self.pj[OBSERVATIONS][self.observationId][TIME_OFFSET_SECOND_PLAYER]:
                    if self.pj[OBSERVATIONS][self.observationId][TIME_OFFSET_SECOND_PLAYER] > 0:
                        self.mediaplayer2.set_time( int( self.pj[OBSERVATIONS][self.observationId][TIME_OFFSET_SECOND_PLAYER] *1000) )

                # no subtitles
                #self.mediaplayer2.video_set_spu(0)


        self.videoTab.setEnabled(True)

        self.toolBox.setCurrentIndex(VIDEO_TAB)
        self.toolBox.setItemEnabled (VIDEO_TAB, False)

        self.toolBar.setEnabled(True)

        self.display_timeoffset_statubar( self.pj[OBSERVATIONS][self.observationId][TIME_OFFSET])

        self.memMedia, self.currentSubject = "", ""

        self.timer_out()

        self.lbSpeed.setText("x{:.3f}".format(self.play_rate))

        if window.focusWidget():
            window.focusWidget().installEventFilter(self)

        # spectrogram

        if "visualize_spectrogram" in self.pj[OBSERVATIONS][self.observationId] and self.pj[OBSERVATIONS][self.observationId]["visualize_spectrogram"]:

            #self.memChunk = ''
            if not self.ffmpeg_cache_dir:
                tmp_dir = tempfile.gettempdir()
            else:
                tmp_dir = self.ffmpeg_cache_dir

            currentMediaTmpPath = tmp_dir + os.sep + os.path.basename(urllib.parse.unquote(url2path(self.mediaplayer.get_media().get_mrl())))

            if not os.path.isfile("{}.wav.0-{}.spectrogram.png".format(currentMediaTmpPath, self.chunk_length)):
                if dialog.MessageDialog(programName, ("Spectrogram file not found.\n"
                                                      "Do you want to generate it now?\n"
                                                      "Spectrogram generation can take some time for long media, be patient"), [YES, NO ]) == YES:

                    self.generate_spectrogram()
                else:
                    self.pj[OBSERVATIONS][self.observationId]["visualize_spectrogram"] = False
                    return True

            self.spectro = plot_spectrogram.Spectrogram("{}.wav.0-{}.spectrogram.png".format(currentMediaTmpPath, self.chunk_length))
            # connect signal from spectrogram class to testsignal function to receive keypress events
            self.spectro.setWindowFlags(Qt.WindowStaysOnTopHint)
            self.spectro.sendEvent.connect(self.signal_from_spectrogram)
            self.spectro.show()
            self.timer_spectro.start()

        return True

    def signal_from_spectrogram(self, event):
        """
        receive signal from spectrogram widget
        """
        self.keyPressEvent(event)

    def eventFilter(self, source, event):
        """
        send event from class (QScrollArea) to mainwindow
        """
        if event.type() == QtCore.QEvent.KeyPress:
            key = event.key()
            if key in [Qt.Key_Up, Qt.Key_Down, Qt.Key_Left, Qt.Key_Right, Qt.Key_PageDown, Qt.Key_PageUp]:
                self.keyPressEvent(event)

        return QMainWindow.eventFilter(self, source, event)


    def loadEventsInTW(self, obsId):
        """
        load events in table widget
        """

        self.twEvents.setRowCount(len(self.pj[OBSERVATIONS][obsId][EVENTS]))
        row = 0

        for event in self.pj[OBSERVATIONS][obsId][EVENTS]:

            for field_type in tw_events_fields:

                if field_type in pj_events_fields:

                    field = event[ pj_obs_fields[field_type] ]
                    if field_type == "time":
                        field = str( self.convertTime( field) )

                    twi = QTableWidgetItem(field )
                    self.twEvents.setItem(row, tw_obs_fields[field_type], twi)

                else:
                    self.twEvents.setItem(row, tw_obs_fields[field_type], QTableWidgetItem(""))

            row += 1

        self.update_events_start_stop()


    def selectObservations(self, mode):
        '''
        show observations list window
        mode: accepted values: OPEN, EDIT, SINGLE, MULTIPLE, SELECT1
        '''

        obsList = obs_list2.observationsList_widget()

        obsList.pbOpen.setVisible(False)
        obsList.pbEdit.setVisible(False)
        obsList.pbSelect.setVisible(False)
        obsList.pbSelectAll.setVisible(False)
        obsList.pbUnSelectAll.setVisible(False)
        obsList.mode = mode

        if mode == OPEN:
            obsList.view.setSelectionMode( QAbstractItemView.SingleSelection )
            obsList.pbOpen.setVisible(True)
            #obsList.pbEdit.setVisible(True)

        if mode == EDIT:
            obsList.view.setSelectionMode( QAbstractItemView.SingleSelection )
            obsList.pbEdit.setVisible(True)

        if mode == SINGLE:
            obsList.view.setSelectionMode( QAbstractItemView.SingleSelection )
            obsList.pbOpen.setVisible(True)
            obsList.pbEdit.setVisible(True)

        if mode == MULTIPLE:
            obsList.view.setSelectionMode( QAbstractItemView.MultiSelection )
            obsList.pbSelect.setVisible(True)
            obsList.pbSelectAll.setVisible(True)
            obsList.pbUnSelectAll.setVisible(True)

        if mode == SELECT1:
            obsList.view.setSelectionMode( QAbstractItemView.SingleSelection )
            obsList.pbSelect.setVisible(True)

        obsListFields = ['id', 'date', 'description', 'subjects', 'media']
        indepVarHeader = []

        if INDEPENDENT_VARIABLES in self.pj:
            for idx in [str(x) for x in sorted([int(x) for x in self.pj[INDEPENDENT_VARIABLES].keys() ])]:

                indepVarHeader.append(  self.pj[ INDEPENDENT_VARIABLES ][ idx ]['label'] )

        obsList.model.setHorizontalHeaderLabels(obsListFields + indepVarHeader)
        obsList.comboBox.addItems(obsListFields + indepVarHeader)

        for obs in sorted( list(self.pj[OBSERVATIONS].keys()) ):

            date = self.pj[OBSERVATIONS][obs]['date'].replace('T',' ')
            descr = self.pj[OBSERVATIONS][obs]['description']

            # subjects
            observedSubjects = self.extract_observed_subjects( [obs] )

            # remove when No focal subject
            if '' in observedSubjects:
                observedSubjects.remove('')
            subjectsList = ', '.join( observedSubjects )

            mediaList = []
            if self.pj[OBSERVATIONS][obs][TYPE] in [MEDIA]:
                if self.pj[OBSERVATIONS][obs][FILE]:
                    for player in sorted(self.pj[OBSERVATIONS][obs][FILE].keys()):
                        for media in self.pj[OBSERVATIONS][obs][FILE][player]:
                            mediaList.append("#{0}: {1}".format(player, media))

                media = os.linesep.join( mediaList )
            elif self.pj[OBSERVATIONS][obs][TYPE] in [LIVE]:
                media = LIVE

            # independent variable
            indepVar = []
            if INDEPENDENT_VARIABLES in self.pj[OBSERVATIONS][obs]:
                for var in indepVarHeader:
                    if var in self.pj[OBSERVATIONS][obs][ INDEPENDENT_VARIABLES ]:
                        indepVar.append( QStandardItem( self.pj[OBSERVATIONS][obs][ INDEPENDENT_VARIABLES ][var] ) )

            obsList.model.invisibleRootItem().appendRow( [ QStandardItem(obs), QStandardItem(date), QStandardItem(descr) , QStandardItem( subjectsList ), QStandardItem( media )]  +  indepVar )

        #obsList.view.horizontalHeader().setStretchLastSection(True)
        obsList.view.resizeColumnsToContents()

        obsList.view.setEditTriggers(QAbstractItemView.NoEditTriggers);
        obsList.label.setText( '%d observation(s)' % obsList.model.rowCount())

        obsList.resize(900, 600)

        selectedObs = []

        result = obsList.exec_()

        if result:
            if obsList.view.selectedIndexes():
                for idx in obsList.view.selectedIndexes():
                    if idx.column() == 0:   # first column
                        selectedObs.append( idx.data() )


        if result == 0:  # cancel
            resultStr = ""
        if result == 1:   # select
            resultStr = "ok"
        if result == 2:   # open
            resultStr = OPEN
        if result == 3:   # edit
            resultStr = EDIT

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
        self.toolBox.setItemEnabled (0, True)   # enable tab
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
            if dialog.MessageDialog(programName, "The current observation will be closed. Do you want to continue?", [YES, NO]) == NO:
                return
            else:
                self.close_observation()

        observationWindow = observation.Observation(logging.getLogger().getEffectiveLevel())

        observationWindow.pj = self.pj
        observationWindow.mode = mode
        observationWindow.mem_obs_id = obsId
        observationWindow.chunk_length = self.chunk_length
        observationWindow.ffmpeg_cache_dir = self.ffmpeg_cache_dir
        observationWindow.dteDate.setDateTime(QDateTime.currentDateTime())

        observationWindow.ffmpeg_bin = self.ffmpeg_bin

        # add indepvariables
        if INDEPENDENT_VARIABLES in self.pj:

            observationWindow.twIndepVariables.setRowCount(0)
            for i in [str(x) for x in sorted([int(x) for x in self.pj[INDEPENDENT_VARIABLES].keys() ])]:

                observationWindow.twIndepVariables.setRowCount(observationWindow.twIndepVariables.rowCount() + 1)

                # label
                item = QTableWidgetItem()
                indepVarLabel = self.pj[INDEPENDENT_VARIABLES][i]['label']
                item.setText( indepVarLabel )
                item.setFlags(Qt.ItemIsEnabled)
                observationWindow.twIndepVariables.setItem(observationWindow.twIndepVariables.rowCount() - 1, 0, item)

                # var type
                item = QTableWidgetItem()
                item.setText( self.pj[INDEPENDENT_VARIABLES][i][TYPE]  )
                item.setFlags(Qt.ItemIsEnabled)   # not modifiable
                observationWindow.twIndepVariables.setItem(observationWindow.twIndepVariables.rowCount() - 1, 1, item)

                # var value
                item = QTableWidgetItem()
                # check if obs has independent variables and var label is a key
                if mode == EDIT and INDEPENDENT_VARIABLES in self.pj[OBSERVATIONS][obsId] and indepVarLabel in self.pj[OBSERVATIONS][obsId][INDEPENDENT_VARIABLES]:
                    txt = self.pj[OBSERVATIONS][obsId][INDEPENDENT_VARIABLES][indepVarLabel]

                elif mode == NEW:
                    txt = self.pj[INDEPENDENT_VARIABLES][i]["default value"]
                else:
                    txt = ''

                item.setText( txt )
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
            observationWindow.dteDate.setDateTime( QDateTime.fromString( self.pj[OBSERVATIONS][obsId]["date"], "yyyy-MM-ddThh:mm:ss") )
            observationWindow.teDescription.setPlainText( self.pj[OBSERVATIONS][obsId]["description"] )

            try:
                observationWindow.mediaDurations = self.pj[OBSERVATIONS][obsId]["media_info"]["length"]
                observationWindow.mediaFPS = self.pj[OBSERVATIONS][obsId]["media_info"]["fps"]
            except:
                observationWindow.mediaDurations = {}
                observationWindow.mediaFPS = {}

            '''
            TODO: fix
            observationWindow.mediaHasVideo = self.pj[OBSERVATIONS][obsId]["media_info"]["hasVideo"]
            observationWindow.mediaHasAudio = self.pj[OBSERVATIONS][obsId]["media_info"]["hasAudio"]
            '''

            # offset
            if self.timeFormat == S:

                observationWindow.leTimeOffset.setText( self.convertTime( abs(self.pj[OBSERVATIONS][obsId]["time offset"]) ))

                if "time offset second player" in self.pj[OBSERVATIONS][obsId]:
                    observationWindow.leTimeOffset_2.setText( self.convertTime( abs(self.pj[OBSERVATIONS][obsId]["time offset second player"]) ))

                    if self.pj[OBSERVATIONS][obsId]["time offset second player"] <= 0:
                        observationWindow.rbEarlier.setChecked(True)
                    else:
                        observationWindow.rbLater.setChecked(True)

            if self.timeFormat == HHMMSS:

                time = QTime()
                h,m,s_dec = seconds2time(abs(self.pj[OBSERVATIONS][obsId]["time offset"])).split(":")
                s, ms = s_dec.split(".")
                time.setHMS(int(h), int(m), int(s), int(ms))
                observationWindow.teTimeOffset.setTime(time)

                if "time offset second player" in self.pj[OBSERVATIONS][obsId]:
                    time = QTime()
                    h,m,s_dec = seconds2time(abs(self.pj[OBSERVATIONS][obsId]["time offset second player"])).split(':')
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
                            twVideo.setItem(twVideo.rowCount() - 1, 1, QTableWidgetItem(seconds2time(self.pj[OBSERVATIONS][obsId]["media_info"]["length"][mediaFile])))
                            twVideo.setItem(twVideo.rowCount() - 1, 2, QTableWidgetItem("{}".format(self.pj[OBSERVATIONS][obsId]["media_info"]["fps"][mediaFile])))
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

            # cbCloseCurrentBehaviorsBetweenVideo
            observationWindow.cbCloseCurrentBehaviorsBetweenVideo.setEnabled(True)
            if CLOSE_BEHAVIORS_BETWEEN_VIDEOS in self.pj[OBSERVATIONS][obsId]:
                observationWindow.cbCloseCurrentBehaviorsBetweenVideo.setChecked(self.pj[OBSERVATIONS][obsId][CLOSE_BEHAVIORS_BETWEEN_VIDEOS])



        rv = observationWindow.exec_()

        if rv:

            self.projectChanged = True

            new_obs_id = observationWindow.leObservationId.text()

            if mode == NEW:
                self.observationId = new_obs_id
                self.pj[OBSERVATIONS][self.observationId] = { FILE: [], TYPE: '' ,  'date': '', 'description': '','time offset': 0, 'events': [] }

            # check if id changed
            if mode == EDIT and new_obs_id != obsId:

                logging.info("observation id {} changed in {}".format(obsId, new_obs_id))

                self.pj[OBSERVATIONS][new_obs_id] = self.pj[OBSERVATIONS][obsId]
                del self.pj[OBSERVATIONS][obsId]

            # observation date
            self.pj[OBSERVATIONS][new_obs_id]['date'] = observationWindow.dteDate.dateTime().toString(Qt.ISODate)

            self.pj[OBSERVATIONS][new_obs_id]['description'] = observationWindow.teDescription.toPlainText()

            # observation type: read project type from tab text
            self.pj[OBSERVATIONS][new_obs_id][TYPE] = observationWindow.tabProjectType.tabText( observationWindow.tabProjectType.currentIndex() ).upper()

            # independent variables for observation
            self.pj[OBSERVATIONS][new_obs_id][INDEPENDENT_VARIABLES] = {}
            for r in range(0, observationWindow.twIndepVariables.rowCount()):

                # set dictionary as label (col 0) => value (col 2)
                self.pj[OBSERVATIONS][new_obs_id][INDEPENDENT_VARIABLES][ observationWindow.twIndepVariables.item(r, 0).text() ] = observationWindow.twIndepVariables.item(r, 2).text()

            # observation time offset
            if self.timeFormat == HHMMSS:
                self.pj[OBSERVATIONS][new_obs_id][TIME_OFFSET] = time2seconds(observationWindow.teTimeOffset.time().toString('hh:mm:ss.zzz'))
                self.pj[OBSERVATIONS][new_obs_id][TIME_OFFSET_SECOND_PLAYER] = time2seconds(observationWindow.teTimeOffset_2.time().toString('hh:mm:ss.zzz'))

            if self.timeFormat == S:
                self.pj[OBSERVATIONS][new_obs_id][TIME_OFFSET] = abs(Decimal( observationWindow.leTimeOffset.text() ))
                self.pj[OBSERVATIONS][new_obs_id][TIME_OFFSET_SECOND_PLAYER] = abs(Decimal( observationWindow.leTimeOffset_2.text() ))

            if observationWindow.rbSubstract.isChecked():
                self.pj[OBSERVATIONS][new_obs_id][TIME_OFFSET] = - self.pj[OBSERVATIONS][new_obs_id][TIME_OFFSET]

            if observationWindow.rbEarlier.isChecked():
                self.pj[OBSERVATIONS][new_obs_id][TIME_OFFSET_SECOND_PLAYER] = - self.pj[OBSERVATIONS][new_obs_id][TIME_OFFSET_SECOND_PLAYER]


            self.display_timeoffset_statubar(self.pj[OBSERVATIONS][new_obs_id][TIME_OFFSET])

            # visualize spectrogram
            self.pj[OBSERVATIONS][new_obs_id]["visualize_spectrogram"] = observationWindow.cbVisualizeSpectrogram.isChecked()

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

                logging.debug("media_info: {0}".format(  self.pj[OBSERVATIONS][new_obs_id]['media_info'] ))

                '''
                if not 'project_media_file_info' in self.pj:
                    self.pj['project_media_file_info'] = {}


                for h in observationWindow.media_file_info:
                    self.pj['project_media_file_info'][h] = observationWindow.media_file_info[h]
                logging.info('pj: {0}'.format(  self.pj ))
                '''

            #if mode == NEW:

            if rv == 1: # save
                self.observationId = ""
                self.menu_options()

            if rv == 2:  # launch
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


    def close_observation(self):
        """
        close current observation
        """

        logging.info("Close observation {}".format(self.playerType))

        self.observationId = ""

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

        self.statusbar.showMessage('',0)

        # delete layout
        self.toolBar.setEnabled(False)
        self.dwObservations.setVisible(False)
        self.toolBox.setVisible(False)
        self.lbFocalSubject.setVisible(False)
        self.lbCurrentStates.setVisible(False)

        self.twEvents.setRowCount(0)

        self.lbTime.clear()
        self.lbSubject.clear()
        self.lbFocalSubject.setText( NO_FOCAL_SUBJECT )

        self.lbTimeOffset.clear()
        self.lbSpeed.clear()

        self.playerType = ''

        self.menu_options()



    def readConfigFile(self):
        """
        read config file
        """

        logging.info("read config file")

        if __version__ == 'DEV':
            iniFilePath = os.path.expanduser('~') + os.sep + '.boris_dev'
        else:
            iniFilePath = os.path.expanduser('~') + os.sep + '.boris'

        if os.path.isfile(iniFilePath):
            settings = QSettings(iniFilePath, QSettings.IniFormat)

            size = settings.value('MainWindow/Size')
            if size:
                self.resize(size)
                self.move(settings.value('MainWindow/Position'))

            self.timeFormat = HHMMSS
            try:
                self.timeFormat = settings.value('Time/Format')
            except:
                self.timeFormat = HHMMSS

            self.fast = 10
            try:
                self.fast = int(settings.value('Time/fast_forward_speed'))

            except:
                self.fast = 10

            self.repositioningTimeOffset = 0
            try:
                self.repositioningTimeOffset = int(settings.value('Time/Repositioning_time_offset'))

            except:
                self.repositioningTimeOffset = 0

            self.play_rate_step = 0.1
            try:
                self.play_rate_step = float(settings.value('Time/play_rate_step'))

            except:
                self.play_rate_step = 0.1

            #self.saveMediaFilePath = True

            self.automaticBackup = 0
            try:
                self.automaticBackup  = int(settings.value('Automatic_backup'))
            except:
                self.automaticBackup = 0

            self.behaviouralStringsSeparator = '|'
            try:
                self.behaviouralStringsSeparator = settings.value('behavioural_strings_separator')
                if not self.behaviouralStringsSeparator:
                    self.behaviouralStringsSeparator = '|'
            except:

                self.behaviouralStringsSeparator = '|'

            self.confirmSound = False
            try:
                self.confirmSound = (settings.value('confirm_sound') == 'true')
            except:
                self.confirmSound = False

            self.embedPlayer = True
            try:
                self.embedPlayer = ( settings.value('embed_player') == 'true' )
            except:
                self.embedPlayer = True

            self.alertNoFocalSubject = False
            try:
                self.alertNoFocalSubject = ( settings.value('alert_nosubject') == 'true' )
            except:
                self.alertNoFocalSubject = False

            self.trackingCursorAboveEvent = False
            try:
                self.trackingCursorAboveEvent = (settings.value('tracking_cursor_above_event') == 'true')
            except:
                self.trackingCursorAboveEvent = False

            # check for new version
            self.checkForNewVersion = False
            try:
                if settings.value('check_for_new_version') == None:
                    self.checkForNewVersion = ( dialog.MessageDialog(programName, 'Allow BORIS to automatically check for new version?', [YES, NO ]) == YES )
                else:
                    self.checkForNewVersion = (settings.value('check_for_new_version') == 'true')
            except:
                self.checkForNewVersion = False

            if self.checkForNewVersion:
                if settings.value("last_check_for_new_version") and  int(time.mktime(time.localtime())) - int(settings.value('last_check_for_new_version')) > CHECK_NEW_VERSION_DELAY:
                    self.actionCheckUpdate_activated(flagMsgOnlyIfNew = True)

            self.ffmpeg_cache_dir = ''
            try:
                self.ffmpeg_cache_dir = settings.value("ffmpeg_cache_dir")
                if not self.ffmpeg_cache_dir:
                    self.ffmpeg_cache_dir = ''
            except:
                self.ffmpeg_cache_dir = ''

            self.ffmpeg_cache_dir_max_size = 0
            try:
                self.ffmpeg_cache_dir_max_size = int(settings.value("ffmpeg_cache_dir_max_size"))
                if not self.ffmpeg_cache_dir_max_size:
                    self.ffmpeg_cache_dir_max_size = 0
            except:
                self.ffmpeg_cache_dir_max_size = 0


    def saveConfigFile(self, lastCheckForNewVersion=0):
        """
        save config file
        """

        logging.info("save config file")

        if __version__ == "DEV":
            iniFilePath = os.path.expanduser("~") + os.sep + ".boris_dev"
        else:
            iniFilePath = os.path.expanduser("~") + os.sep + ".boris"

        settings = QSettings(iniFilePath, QSettings.IniFormat)
        settings.setValue("MainWindow/Size", self.size())
        settings.setValue("MainWindow/Position", self.pos())
        settings.setValue("Time/Format", self.timeFormat )
        settings.setValue("Time/Repositioning_time_offset", self.repositioningTimeOffset )
        settings.setValue("Time/fast_forward_speed", self.fast )
        settings.setValue("Time/play_rate_step", self.play_rate_step)
        settings.setValue("Save_media_file_path", self.saveMediaFilePath )
        settings.setValue("Automatic_backup", self.automaticBackup )
        settings.setValue("behavioural_strings_separator", self.behaviouralStringsSeparator )
        settings.setValue("confirm_sound", self.confirmSound)
        settings.setValue("embed_player", self.embedPlayer)
        settings.setValue("alert_nosubject", self.alertNoFocalSubject)
        settings.setValue("tracking_cursor_above_event", self.trackingCursorAboveEvent)
        settings.setValue("check_for_new_version", self.checkForNewVersion)
        if lastCheckForNewVersion:
            settings.setValue("last_check_for_new_version", lastCheckForNewVersion)

        settings.setValue("ffmpeg_cache_dir", self.ffmpeg_cache_dir)
        settings.setValue("ffmpeg_cache_dir_max_size", self.ffmpeg_cache_dir_max_size)



    def edit_project_activated(self):
        """
        edit project menu option triggered
        """
        if self.project:
            self.edit_project(EDIT)
        else:
            QMessageBox.warning(self, programName, 'There is no project to edit')



    def display_timeoffset_statubar(self, timeOffset):
        """
        display offset in status bar
        """

        if timeOffset:
            self.lbTimeOffset.setText("Time offset: <b>{}</b>".format( timeOffset if self.timeFormat == S else  seconds2time(timeOffset)  ))
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



    def loadEventsInDB(self, selectedSubjects, selectedObservations, selectedBehaviors):
        """
        populate the db databse with events from selectedObservations, selectedSubjects and selectedBehaviors
        """
        db = sqlite3.connect(":memory:")
        db.row_factory = sqlite3.Row

        cursor = db.cursor()

        cursor.execute("CREATE TABLE events (observation TEXT, subject TEXT, code TEXT, type TEXT, modifiers TEXT, occurence FLOAT, comment TEXT);")

        for subject_to_analyze in selectedSubjects:

            for obsId in selectedObservations:

                for event in self.pj[OBSERVATIONS][obsId][EVENTS]:

                    if event[2] in selectedBehaviors:

                        # extract time, code, modifier and comment ( time:0, subject:1, code:2, modifier:3, comment:4 )
                        if (subject_to_analyze == NO_FOCAL_SUBJECT and event[1] == '') \
                            or ( event[1] == subject_to_analyze ):

                            subjectStr = NO_FOCAL_SUBJECT if event[1] == "" else  event[1]

                            eventType = STATE if STATE in self.eventType(event[2]).upper() else POINT

                            r = cursor.execute("""INSERT INTO events (observation, subject, code, type, modifiers, occurence, comment) VALUES (?,?,?,?,?,?,?)""", \
                            (obsId, subjectStr, event[2], eventType, event[3], str(event[0]), event[4]))

        db.commit()
        return cursor




    def extract_observed_subjects(self, selected_observations):
        """
        extract unique subjects from obs_id observation
        """

        observed_subjects = []

        # extract events from selected observations
        all_events =   [ self.pj[OBSERVATIONS][x][EVENTS] for x in self.pj[OBSERVATIONS] if x in selected_observations]
        for events in all_events:
            for event in events:
                observed_subjects.append( event[pj_obs_fields['subject']] )

        # remove duplicate
        observed_subjects = list( set( observed_subjects ) )

        return observed_subjects


    def extract_observed_behaviors(self, selected_observations, selectedSubjects):
        '''
        extract unique behaviors from obs_id observation
        '''

        observed_behaviors = []

        # extract events from selected observations
        all_events =   [ self.pj[OBSERVATIONS][x][EVENTS] for x in self.pj[OBSERVATIONS] if x in selected_observations]

        for events in all_events:
            for event in events:
                if event[1] in selectedSubjects or ( not event[1] and NO_FOCAL_SUBJECT in selectedSubjects):
                    observed_behaviors.append( event[pj_obs_fields["code"]] )


        # remove duplicate
        observed_behaviors = list( set( observed_behaviors ) )

        return observed_behaviors


    def choose_obs_subj_behav(self, selectedObservations, maxTime, flagShowIncludeModifiers=True, flagShowExcludeBehaviorsWoEvents=True):
        """
        show param window for selection subjects and behaviors
        for plot user can select the max time (if media length is known)
        """

        paramPanelWindow = param_panel.Param_panel()
        paramPanelWindow.selectedObservations = selectedObservations
        paramPanelWindow.pj = self.pj
        paramPanelWindow.extract_observed_behaviors = self.extract_observed_behaviors

        if not flagShowIncludeModifiers:
            paramPanelWindow.cbIncludeModifiers.setVisible(False)
        if not flagShowExcludeBehaviorsWoEvents:
            paramPanelWindow.cbExcludeBehaviors.setVisible(False)
        # hide max time
        if maxTime:
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

        else:
            paramPanelWindow.lbStartTime.setVisible(False)
            paramPanelWindow.lbEndTime.setVisible(False)

            paramPanelWindow.teStartTime.setVisible(False)
            paramPanelWindow.teEndTime.setVisible(False)

            paramPanelWindow.dsbStartTime.setVisible(False)
            paramPanelWindow.dsbEndTime.setVisible(False)


        # extract subjects present in observations
        observedSubjects = self.extract_observed_subjects(selectedObservations)
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

        all_subjects = sorted([self.pj[SUBJECTS][x]["name"] for x in self.pj[SUBJECTS]])

        for subject in all_subjects:
            paramPanelWindow.item = QListWidgetItem(paramPanelWindow.lwSubjects)
            paramPanelWindow.ch = QCheckBox()
            paramPanelWindow.ch.setText( subject )
            paramPanelWindow.ch.stateChanged.connect(paramPanelWindow.cb_changed)
            if subject in observedSubjects:
                selectedSubjects.append(subject)
                paramPanelWindow.ch.setChecked(True)

            paramPanelWindow.lwSubjects.setItemWidget(paramPanelWindow.item, paramPanelWindow.ch)

        logging.debug('selectedSubjects: {0}'.format(selectedSubjects))

        allBehaviors = sorted( [  self.pj[ETHOGRAM][x]["code"] for x in self.pj[ETHOGRAM]])
        logging.debug('allBehaviors: {0}'.format(allBehaviors))

        observedBehaviors = self.extract_observed_behaviors( selectedObservations, selectedSubjects )
        logging.debug('observed behaviors: {0}'.format(observedBehaviors))

        for behavior in allBehaviors:

            paramPanelWindow.item = QListWidgetItem(paramPanelWindow.lwBehaviors)
            paramPanelWindow.ch = QCheckBox()
            paramPanelWindow.ch.setText(behavior)

            if behavior in observedBehaviors:
                paramPanelWindow.ch.setChecked(True)

            paramPanelWindow.lwBehaviors.setItemWidget(paramPanelWindow.item, paramPanelWindow.ch)

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


        return {"selected subjects": selectedSubjects,
                "selected behaviors": selectedBehaviors,
                "include modifiers": paramPanelWindow.cbIncludeModifiers.isChecked(),
                "exclude behaviors": paramPanelWindow.cbExcludeBehaviors.isChecked(),
                "start time": startTime,
                "end time": endTime
                }

    def time_budget(self):
        """
        time budget
        """

        result, selectedObservations = self.selectObservations(MULTIPLE)

        logging.debug("Selected observations: {0}".format(selectedObservations))

        if not selectedObservations:
            return

        selectedObsTotalMediaLength = Decimal("0.0")

        for obsId in selectedObservations:
            if self.pj[OBSERVATIONS][ obsId ][TYPE] == MEDIA:
                totalMediaLength = self.observationTotalMediaLength(obsId)
                logging.debug("media length for {0} : {1}".format(obsId,totalMediaLength ))
            else: # LIVE
                if self.pj[OBSERVATIONS][obsId][EVENTS]:
                    totalMediaLength = max(self.pj[OBSERVATIONS][ obsId ][EVENTS])[0]
                else:
                    totalMediaLength = Decimal("0.0")
            if totalMediaLength in [0, -1]:
                selectedObsTotalMediaLength = -1
                break
            selectedObsTotalMediaLength += totalMediaLength

        if selectedObsTotalMediaLength == -1: # an observation media length is not available
            # propose to user to use max event time
            if dialog.MessageDialog(programName, "A media length is not available.<br>Use last event time as media length?", [YES, NO]) == YES:
                maxTime = 0 # max length for all events all subjects
                for obsId in selectedObservations:
                    maxTime += max(self.pj[OBSERVATIONS][obsId][EVENTS])[0]
                logging.debug("max time all events all subjects: {0}".format(maxTime))
                selectedObsTotalMediaLength = maxTime
            else:
                selectedObsTotalMediaLength = 0

        logging.debug("selectedObsTotalMediaLength: {}".format(selectedObsTotalMediaLength))

        if len(selectedObservations) > 1:
            plot_parameters = self.choose_obs_subj_behav(selectedObservations, maxTime=0)
        else:
            plot_parameters = self.choose_obs_subj_behav(selectedObservations, maxTime=selectedObsTotalMediaLength)

        if not plot_parameters["selected subjects"] or not plot_parameters["selected behaviors"]:
            return

        cursor = self.loadEventsInDB(plot_parameters["selected subjects"], selectedObservations, plot_parameters["selected behaviors"] )

        out = []
        for subject in plot_parameters["selected subjects"]:

            for behavior in plot_parameters["selected behaviors"]:

                if plot_parameters["include modifiers"]:

                    cursor.execute("SELECT distinct modifiers FROM events WHERE subject = ? AND code = ?", (subject, behavior))
                    distinct_modifiers = list(cursor.fetchall())

                    if not distinct_modifiers:
                        if not plot_parameters["exclude behaviors"]:
                            out.append({"subject": subject,
                                        "behavior": behavior,
                                        "modifiers": "-",
                                        "duration": "-",
                                        "duration_mean": "-",
                                        "duration_stdev": "-",
                                        "number": 0,
                                        "inter_duration_mean": "-",
                                        "inter_duration_stdev": "-"})
                        continue

                    if POINT in self.eventType(behavior).upper():
                        for modifier in distinct_modifiers:
                            if len(selectedObservations) > 1:
                                cursor.execute("SELECT occurence,observation FROM events WHERE subject = ? AND code = ? AND modifiers = ? ORDER BY observation, occurence",
                                               (subject, behavior, modifier[0]))
                            else:
                                cursor.execute("SELECT occurence,observation FROM events WHERE subject = ? AND code = ? AND modifiers = ? AND occurence BETWEEN ? and ? ORDER BY observation, occurence",
                                               (subject, behavior, modifier[0], str(plot_parameters["start time"]), str(plot_parameters["end time"])))

                            rows = cursor.fetchall()

                            # inter events duration
                            all_event_interdurations = []
                            for idx, row in enumerate(rows):
                                if idx and row[1] == rows[idx - 1][1]:
                                    all_event_interdurations.append(float(row[0]) - float(rows[idx - 1][0]))

                            out.append({"subject": subject,
                                        "behavior": behavior,
                                        "modifiers": modifier[0],
                                        "duration": "-",
                                        "duration_mean": "-",
                                        "duration_stdev": "-",
                                        "number": len(rows),
                                        "inter_duration_mean": round(statistics.mean(all_event_interdurations), 3) if len(all_event_interdurations) else "NA",
                                        "inter_duration_stdev": round(statistics.stdev(all_event_interdurations), 3) if len(all_event_interdurations) > 1 else "NA"
                                        })


                    if STATE in self.eventType(behavior).upper():
                        for modifier in distinct_modifiers:
                            cursor.execute("SELECT occurence,observation FROM events WHERE subject = ? AND code = ? AND modifiers = ? ORDER BY observation, occurence",
                                          (subject, behavior, modifier[0]))
                            '''
                            if len(selectedObservations) > 1:
                                cursor.execute("SELECT occurence,observation FROM events WHERE subject = ? AND code = ? AND modifiers = ? ORDER BY observation, occurence",
                                               (subject, behavior, modifier[0]))
                            else:
                                cursor.execute("SELECT occurence,observation FROM events WHERE subject = ? AND code = ? AND modifiers = ? AND occurence BETWEEN ? and ? ORDER BY observation, occurence",
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
                                        if len(selectedObservations) == 1:
                                            if (new_init < plot_parameters["start time"] and new_end < plot_parameters["start time"]) \
                                               or \
                                               (new_init > plot_parameters["end time"] and new_end > plot_parameters["end time"]):
                                                continue

                                            if new_init < plot_parameters["start time"]:
                                                new_init = float(plot_parameters["start time"])
                                            if new_end > plot_parameters["end time"]:
                                                new_end = float(plot_parameters["end time"])

                                        all_event_durations.append( new_end - new_init)

                                    # inter event if same observation
                                    if idx % 2 and idx != len(rows) - 1 and row[1] == rows[idx + 1][1]:
                                        if plot_parameters["start time"] <= row[0] <= plot_parameters["end time"] and plot_parameters["start time"] <= rows[idx + 1][0] <= plot_parameters["end time"]:
                                            all_event_interdurations.append(float(rows[idx + 1][0]) - float(row[0]))

                                        #all_event_interdurations.append(float( rows[idx + 1][0]) - float(row[0]))

                                out.append({"subject": subject,
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

                        if len(selectedObservations) > 1:
                            cursor.execute("SELECT occurence,observation FROM events WHERE subject = ? AND code = ? ORDER BY observation, occurence", (subject, behavior))
                        else:
                            cursor.execute("SELECT occurence,observation FROM events WHERE subject = ? AND code = ? AND occurence BETWEEN ? and ? ORDER BY observation, occurence",
                                           (subject, behavior, str(plot_parameters["start time"]), str(plot_parameters["end time"])))

                        rows = list(cursor.fetchall())

                        if len(selectedObservations) == 1:
                            new_rows = []
                            for occurence, observation in rows:
                                new_occurence = max(float(plot_parameters["start time"]), occurence)
                                new_occurence = min( new_occurence, float( plot_parameters["end time"]) )
                                new_rows.append( [new_occurence, observation])
                            rows = list(new_rows)

                        if not len(rows):
                            if not plot_parameters["exclude behaviors"]:
                                out.append({"subject": subject, "behavior": behavior, "modifiers": "NA",
                                            "duration": "-", "duration_mean": "-", "duration_stdev": "-", "number": 0,
                                            "inter_duration_mean": "-", "inter_duration_stdev": "-"})
                            continue

                        # inter events duration
                        all_event_interdurations = []
                        for idx, row in enumerate(rows):
                            if idx and row[1] == rows[idx - 1][1]:
                                all_event_interdurations.append(float(row[0]) - float(rows[idx-1][0]))

                        out.append({"subject": subject,
                                    "behavior": behavior,
                                    "modifiers": "NA",
                                    "duration": "-",
                                    "duration_mean": "-",
                                    "duration_stdev": "-",
                                    "number": len(rows),
                                    "inter_duration_mean" : round(statistics.mean(all_event_interdurations), 3) if len(all_event_interdurations) else "NA",
                                    "inter_duration_stdev": round(statistics.stdev(all_event_interdurations), 3) if len(all_event_interdurations) > 1 else "NA"
                                    })


                    if STATE in self.eventType(behavior).upper():
                        cursor.execute( "SELECT occurence,observation FROM events where subject = ? AND code = ? ORDER BY observation, occurence", (subject, behavior))
                        rows = list(cursor.fetchall())

                        if not len(rows):
                            if not plot_parameters["exclude behaviors"]: # include behaviors without events
                                out.append({"subject": subject , "behavior": behavior,
                                            "modifiers": "NA", "duration": 0, "duration_mean": 0,
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
                                    if len(selectedObservations) == 1:
                                        if (new_init < plot_parameters["start time"] and new_end < plot_parameters["start time"]) \
                                           or \
                                           (new_init > plot_parameters["end time"] and new_end > plot_parameters["end time"]):
                                            continue

                                        if new_init < plot_parameters["start time"]:
                                            new_init = float(plot_parameters["start time"])
                                        if new_end > plot_parameters["end time"]:
                                            new_end = float(plot_parameters["end time"])

                                    all_event_durations.append( new_end - new_init)

                                # inter event if same observation
                                if idx % 2 and idx != len(rows) - 1 and row[1] == rows[idx + 1][1]:
                                    if plot_parameters["start time"] <= row[0] <= plot_parameters["end time"] and plot_parameters["start time"] <= rows[idx + 1][0] <= plot_parameters["end time"]:
                                        all_event_interdurations.append(float(rows[idx + 1][0]) - float(row[0]))

                            out.append({"subject": subject,
                                        "behavior": behavior,
                                        "modifiers": "NA",
                                        "duration": round(sum(all_event_durations), 3),
                                        "duration_mean": round(statistics.mean(all_event_durations), 3) if len(all_event_durations) else "NA",
                                        "duration_stdev": round(statistics.stdev(all_event_durations), 3) if len(all_event_durations) > 1 else "NA",
                                        "number": len(all_event_durations),
                                        "inter_duration_mean": round(statistics.mean(all_event_interdurations), 3) if len(all_event_interdurations) else "NA",
                                        "inter_duration_stdev": round(statistics.stdev(all_event_interdurations), 3) if len(all_event_interdurations) > 1 else "NA"
                                        })

        # widget for results visualization
        self.tb = timeBudgetResults(logging.getLogger().getEffectiveLevel(), self.pj)

        # observations list
        self.tb.label.setText("Selected observations")
        for obs in selectedObservations:
            self.tb.lw.addItem(obs)

        if len(selectedObservations) > 1:
            if selectedObsTotalMediaLength:
                self.tb.lbTotalObservedTime.setText("Total media length: {0}".format(seconds2time(selectedObsTotalMediaLength)))
            else:
                self.tb.lbTotalObservedTime.setText("Total media length: not available")
        else:
            self.tb.lbTotalObservedTime.setText("Analysis from {} to {}".format(seconds2time(plot_parameters["start time"]), seconds2time(plot_parameters["end time"])))

        tb_fields = ["Subject", "Behavior", "Modifiers", "Total number", "Total duration (s)",
                     "Duration mean (s)", "Duration std dev", "inter-event intervals mean (s)",
                     "inter-event intervals std dev", "% of total media length"]
        self.tb.twTB.setColumnCount(len(tb_fields))
        self.tb.twTB.setHorizontalHeaderLabels(tb_fields)

        fields = ["subject", "behavior",  "modifiers", "number", "duration", "duration_mean", "duration_stdev", "inter_duration_mean", "inter_duration_stdev"]

        for row in out:
            self.tb.twTB.setRowCount(self.tb.twTB.rowCount() + 1)
            column = 0
            for field in fields:
                item = QTableWidgetItem(str(row[field]).replace(" ()", ""))
                # no modif allowed
                item.setFlags(Qt.ItemIsEnabled)
                self.tb.twTB.setItem(self.tb.twTB.rowCount() - 1, column , item)
                column += 1

            # % of total time
            if row["duration"] != "-" and row["duration"] != 0 and row["duration"] != UNPAIRED and selectedObsTotalMediaLength:
                if len(selectedObservations) > 1:
                    item = QTableWidgetItem(str(round(row["duration"] / float(selectedObsTotalMediaLength) * 100, 1)))
                else:
                    item = QTableWidgetItem(str(round(row["duration"] / float(plot_parameters["end time"] - plot_parameters["start time"]) * 100, 1)))
            else:
                item = QTableWidgetItem("-")

            item.setFlags(Qt.ItemIsEnabled)
            self.tb.twTB.setItem(self.tb.twTB.rowCount() - 1, column, item)

        self.tb.twTB.resizeColumnsToContents()

        self.tb.show()


    def observationTotalMediaLength(self, obsId):
        '''
        total media length for observation
        if media length not available return 0

        return total media length in s
        '''

        totalMediaLength, totalMediaLength1, totalMediaLength2 = Decimal("0.0"), Decimal("0.0"), Decimal("0.0")

        for mediaFile in self.pj[OBSERVATIONS][obsId][FILE][PLAYER1]:
            mediaLength = 0
            try:
                mediaLength = self.pj[OBSERVATIONS][obsId]["media_info"]["length"][mediaFile]
            except:
                nframe, videoTime, videoDuration, fps, hasVideo, hasAudio = accurate_media_analysis( self.ffmpeg_bin, mediaFile)
                if "media_info" not in self.pj[OBSERVATIONS][obsId]:
                    self.pj[OBSERVATIONS][obsId]["media_info"] = {"length": {}, "fps": {}}
                    if "length" not in self.pj[OBSERVATIONS][obsId]["media_info"]:
                        self.pj[OBSERVATIONS][obsId]["media_info"]["length"] = {}
                    if "fps" not in self.pj[OBSERVATIONS][obsId]["media_info"]:
                        self.pj[OBSERVATIONS][obsId]["media_info"]["fps"] = {}

                self.pj[OBSERVATIONS][obsId]["media_info"]["length"][mediaFile] = videoDuration
                self.pj[OBSERVATIONS][obsId]["media_info"]["fps"][mediaFile] = fps

                mediaLength = videoDuration

                '''
                try:
                    fileContentMD5 = hashfile( mediaFile , hashlib.md5())                  # md5 sum of file content
                    mediaLength = self.pj["project_media_file_info"][fileContentMD5]["video_length"] / 1000
                except:
                    if os.path.isfile(mediaFile):
                        try:
                            instance = vlc.Instance()
                            media = instance.media_new(mediaFile)
                            media.parse()
                            mediaLength = media.get_duration()/1000
                        except:
                            totalMediaLength1 = -1
                            break
                    else:
                        totalMediaLength1 = -1
                        break
                '''

            totalMediaLength1 += Decimal(mediaLength)

        for mediaFile in self.pj[OBSERVATIONS][obsId][FILE][PLAYER2]:
            mediaLength = 0
            try:
                mediaLength = self.pj[OBSERVATIONS][obsId]["media_info"]["length"][mediaFile]
            except:
                nframe, videoTime, videoDuration, fps, hasVideo, hasAudio = accurate_media_analysis( self.ffmpeg_bin, mediaFile)
                if "media_info" not in self.pj[OBSERVATIONS][obsId]:
                    self.pj[OBSERVATIONS][obsId]["media_info"] = {"length": {}, "fps": {}}
                    if "length" not in self.pj[OBSERVATIONS][obsId]["media_info"]:
                        self.pj[OBSERVATIONS][obsId]["media_info"]["length"] = {}
                    if "fps" not in self.pj[OBSERVATIONS][obsId]["media_info"]:
                        self.pj[OBSERVATIONS][obsId]["media_info"]["fps"] = {}

                self.pj[OBSERVATIONS][obsId]["media_info"]["length"][mediaFile] = videoDuration
                self.pj[OBSERVATIONS][obsId]["media_info"]["fps"][mediaFile] = fps

                mediaLength = videoDuration



                '''
                try:
                    fileContentMD5 = hashfile( mediaFile , hashlib.md5())                 # md5 sum of file content
                    mediaLength = self.pj['project_media_file_info'][fileContentMD5]['video_length']/1000
                except:
                    if os.path.isfile(mediaFile):
                        try:
                            instance = vlc.Instance()
                            media = instance.media_new(mediaFile)
                            media.parse()
                            mediaLength = media.get_duration()/1000
                        except:
                            totalMediaLength2 = -1
                            break
                    else:
                        totalMediaLength2 = -1
                        break
                '''

            totalMediaLength2 += Decimal(mediaLength)

        if  totalMediaLength1  == -1 or totalMediaLength2 == -1:
            totalMediaLength = -1
        else:
            totalMediaLength = max( totalMediaLength1, totalMediaLength2 )

        return totalMediaLength


    def plot_events(self):
        """
        plot events with matplotlib
        """

        try:
            import matplotlib.pyplot as plt
            import matplotlib.transforms as mtransforms
            #import matplotlib.colors as matcolors
            from matplotlib import dates
            import numpy as np
            import datetime
        except:
            logging.warning("matplotlib plotting library not installed")
            QMessageBox.warning(None, programName, """The "Plot events" function requires the Matplotlib module.<br>See <a href="http://matplotlib.org">http://matplotlib.org</a>""",
            QMessageBox.Ok | QMessageBox.Default, QMessageBox.NoButton)
            return

        def plot_time_ranges(obs, obsId, minTime, videoLength, excludeBehaviorsWithoutEvents, line_width):
            """
            create "hlines" matplotlib plot
            """

            LINE_WIDTH = line_width
            #colors = list(matcolors.cnames.keys())
            colors = ["blue","green","red","cyan","magenta","yellow","lime",
                      "darksalmon", "purple", "orange", "maroon", "silver",
                      "slateblue", "hotpink", "steelblue", "darkgoldenrod"]
            all_behaviors, observedBehaviors = [], []
            maxTime = 0  # max time in all events of all subjects

            for subject in sorted(list(obs.keys())):

                for behavior in sorted(list(obs[subject].keys())):

                    if not excludeBehaviorsWithoutEvents:
                        observedBehaviors.append(behavior)
                    else:
                        if obs[subject][behavior]:
                            observedBehaviors.append(behavior)

                    if not behavior in all_behaviors:
                        all_behaviors.append(behavior)
                    for t1, t2 in obs[subject][behavior]:
                        maxTime = max(maxTime, t1, t2)
                observedBehaviors.append("")

            all_behaviors = sorted(all_behaviors)

            if excludeBehaviorsWithoutEvents:
                lbl = observedBehaviors[:]
            else:
                all_behaviors.append("")
                lbl = all_behaviors[:] * len(obs)

            lbl = lbl[:-1]  # remove last empty line

            #fig = plt.figure(figsize=(20, int(len( lbl )/18*10)))
            fig = plt.figure(figsize=(20, int(len(lbl) * .8)))

            fig.suptitle("Time diagram of observation {}".format(obsId), fontsize=14)

            ax = fig.add_subplot(111)
            labels = ax.set_yticklabels(lbl)

            ax.set_ylabel("Behaviors")

            if self.timeFormat == HHMMSS:
                fmtr = dates.DateFormatter("%H:%M:%S") # %H:%M:%S:%f
                ax.xaxis.set_major_formatter(fmtr)
                ax.set_xlabel("Time (hh:mm:ss)")
            else:
                ax.set_xlabel("Time (s)")

            plt.ylim(len(lbl), -0.5)

            if not videoLength:
                videoLength = maxTime

            if self.pj[OBSERVATIONS][obsId]["time offset"]:
                t0 = round(self.pj[OBSERVATIONS][obsId]["time offset"] + minTime)
                t1 = round(self.pj[OBSERVATIONS][obsId]["time offset"] + videoLength + 2)
            else:
                t0 = round(minTime)
                t1 = round(videoLength)
            subjectPosition = t0 + (t1-t0) * 0.05

            if self.timeFormat == HHMMSS:
                t0d = datetime.datetime(1970, 1, 1, int(t0 / 3600), int((t0 - int(t0 / 3600) * 3600)/60), int(t0 % 60), round(round(t0 % 1,3)*1000000))
                t1d = datetime.datetime(1970, 1, 1, int(t1 / 3600), int((t1 - int(t1 / 3600) * 3600)/60), int(t1 % 60), round(round(t1 % 1,3)*1000000))
                subjectPositiond = datetime.datetime(1970, 1, 1, int(subjectPosition / 3600), int((subjectPosition - int(subjectPosition / 3600) * 3600)/60), int(subjectPosition % 60), round(round(subjectPosition % 1,3)*1000000))

            if self.timeFormat == S:
                t0d = t0
                t1d = t1
                subjectPositiond = subjectPosition

            plt.xlim(t0d, t1d)

            plt.yticks(range(len(lbl) + 1), np.array(lbl))

            count = 0
            flagFirstSubject = True

            for subject in sorted( list(obs.keys())):

                if not flagFirstSubject:
                    if excludeBehaviorsWithoutEvents:
                        count += 1
                    ax.axhline(y=(count-1), linewidth=1, color="black")
                    ax.hlines(np.array([count]), np.array([0]), np.array([0]), lw=LINE_WIDTH, color=col)
                else:
                    flagFirstSubject = False

                ax.text( subjectPositiond, count - 0.5, subject)

                behaviors = obs[subject]

                x1, x2, y, col, pointsx, pointsy, guide = [], [], [], [], [], [], []
                col_count = 0

                for b in all_behaviors:

                    if b in obs[subject]:
                        if obs[subject][ b ]:
                            for t1, t2 in obs[subject][ b ]:
                                if t1 == t2:
                                    pointsx.append(t1)
                                    pointsy.append(count)
                                    ax.axhline(y=count, linewidth=1, color="lightgray", zorder=-1)
                                else:
                                    x1.append(t1)
                                    x2.append(t2)
                                    y.append(count)
                                    col.append( colors[ col_count % len(colors)])
                                    ax.axhline(y=count ,linewidth=1, color="lightgray", zorder=-1)
                            count += 1
                        else:
                            x1.append(0)
                            x2.append(0)
                            y.append(count)
                            col.append('white')
                            ax.axhline(y=count ,linewidth=1, color='lightgray', zorder=-1)
                            count += 1

                    else:
                        if not excludeBehaviorsWithoutEvents:
                            x1.append(0)
                            x2.append(0)
                            y.append(count)
                            col.append("white")
                            ax.axhline(y=count ,linewidth=1, color='lightgray', zorder=-1)
                            count += 1

                    col_count += 1

                if self.timeFormat == HHMMSS:
                    ax.hlines(np.array(y), np.array([datetime.datetime(1970, 1, 1, int(p/3600), int((p-int(p/3600)*3600)/60), int(p%60), round(round(p%1,3)*1e6)) for p in x1]),
                    np.array([datetime.datetime(1970, 1, 1, int(p/3600), int((p-int(p/3600)*3600)/60), int(p%60), round(round(p%1,3)*1e6)) for p in x2]),
                    lw=LINE_WIDTH, color=col)

                if self.timeFormat == S:
                    ax.hlines(np.array(y), np.array(x1), np.array(x2), lw=LINE_WIDTH, color=col)

                if self.timeFormat == HHMMSS:
                    ax.plot(np.array([datetime.datetime(1970, 1, 1, int(p/3600), int((p-int(p/3600)*3600)/60), int(p%60), round(round(p%1,3)*1e6)) for p in pointsx]), pointsy, "r^")

                if self.timeFormat == S:
                    ax.plot(pointsx,pointsy, "r^" )

                #ax.axhline(y=y[-1] + 0.5,linewidth=1, color='black')

            def on_draw(event):

                # http://matplotlib.org/faq/howto_faq.html#move-the-edge-of-an-axes-to-make-room-for-tick-labels
                bboxes = []
                for label in labels:
                    bbox = label.get_window_extent()
                    bboxi = bbox.inverse_transformed(fig.transFigure)
                    bboxes.append(bboxi)

                bbox = mtransforms.Bbox.union(bboxes)
                if fig.subplotpars.left < bbox.width:
                    fig.subplots_adjust(left=1.1*bbox.width)
                    fig.canvas.draw()
                return False

            fig.canvas.mpl_connect('draw_event', on_draw)

            plt.show()

            return True

        result, selectedObservations = self.selectObservations(SELECT1)

        logging.debug("Selected observations: {0}".format(selectedObservations))

        if not selectedObservations:
            return

        if not self.pj[OBSERVATIONS][ selectedObservations[0] ][EVENTS]:
            QMessageBox.warning(self, programName, "There are no events in the selected observation")
            return

        for obsId in selectedObservations:
            if self.pj[OBSERVATIONS][ obsId ][TYPE] == MEDIA:
                totalMediaLength = self.observationTotalMediaLength(obsId)
            else: # LIVE
                if self.pj[OBSERVATIONS][ obsId ][EVENTS]:
                    totalMediaLength = max(self.pj[OBSERVATIONS][ obsId ][EVENTS])[0]
                else:
                    totalMediaLength = Decimal("0.0")

        if totalMediaLength == -1 :
            totalMediaLength = 0

        logging.debug("totalMediaLength: {0}".format(totalMediaLength))

        '''
        return {"selected subjects": selectedSubjects,
                "selected behaviors": selectedBehaviors,
                "include modifiers": paramPanelWindow.cbIncludeModifiers.isChecked(),
                "exclude behaviors": paramPanelWindow.cbExcludeBehaviors.isChecked(),
                "start time": time2seconds(paramPanelWindow.teStartTime.time().toString(HHMMSSZZZ)),
                "end time": time2seconds(paramPanelWindow.teEndTime.time().toString(HHMMSSZZZ))
                }
        '''
        plot_parameters = self.choose_obs_subj_behav(selectedObservations, totalMediaLength)

        logging.debug("totalMediaLength: {0} s".format(totalMediaLength))

        totalMediaLength = int(totalMediaLength)

        if not plot_parameters["selected subjects"] or not plot_parameters["selected behaviors"]:
            return

        cursor = self.loadEventsInDB(plot_parameters["selected subjects"], selectedObservations, plot_parameters["selected behaviors"])

        o = {}

        for subject in plot_parameters["selected subjects"]:

            o[subject] = {}

            for behavior in plot_parameters["selected behaviors"]:

                if plot_parameters["include modifiers"]:

                    cursor.execute( "SELECT distinct modifiers FROM events WHERE subject = ? AND code = ?", (subject, behavior) )
                    distinct_modifiers = list(cursor.fetchall())

                    for modifier in distinct_modifiers:
                        cursor.execute("SELECT occurence FROM events WHERE subject = ? AND code = ? AND modifiers = ? ORDER BY observation, occurence",
                                      (subject, behavior, modifier[0]))

                        rows = cursor.fetchall()

                        if modifier[0]:
                            behaviorOut = "{0} ({1})".format(behavior, modifier[0].replace("|", ","))
                        else:
                            behaviorOut = "{0}".format(behavior)

                        if not behaviorOut in o[subject]:
                            o[subject][behaviorOut] = []

                        for idx, row in enumerate(rows):
                            if POINT in self.eventType(behavior).upper():
                                o[subject][behaviorOut].append([row[0], row[0]])  # for point event start = end

                            if STATE in self.eventType(behavior).upper():
                                if idx % 2 == 0:
                                    try:
                                        o[subject][behaviorOut].append([row[0], rows[idx + 1][0]])
                                    except:
                                        if NO_FOCAL_SUBJECT in subject:
                                            sbj = ""
                                        else:
                                            sbj = "for subject <b>{0}</b>".format(subject)
                                        QMessageBox.critical(self, programName, "The STATE behavior <b>{0}</b> is not paired {1}".format(behaviorOut, sbj) )
                else:
                    cursor.execute("SELECT occurence FROM events WHERE subject = ? AND code = ?  ORDER BY observation, occurence",
                                  (subject, behavior ))
                    rows = list(cursor.fetchall())

                    if not len(rows) and plot_parameters["exclude behaviors"]:
                        continue

                    if STATE in self.eventType(behavior).upper() and len(rows) % 2:
                        continue

                    behaviorOut = "{0}".format(behavior)

                    if not behaviorOut in o[subject]:
                        o[subject][behaviorOut] = []

                    for idx, row in enumerate(rows):
                        if POINT in self.eventType(behavior).upper():
                            o[subject][behaviorOut].append([row[0], row[0]])   # for point event start = end
                        if STATE in self.eventType(behavior).upper():
                            if idx % 2 == 0:
                                o[subject][behaviorOut].append([row[0], rows[idx + 1][0]])

                '''
                new_o = []
                for idx, interval in enumerate(o[subject][behaviorOut]):

                    new_init, new_end = interval
                    if interval[0] < plot_parameters["start time"]:
                        new_init = float(plot_parameters["start time"])

                    if interval[1] > plot_parameters["end time"]:
                        new_end = float(plot_parameters["end time"])

                    if  plot_parameters["start time"] <= new_init <= plot_parameters["end time"]  and plot_parameters["start time"] <= new_end <= plot_parameters["end time"]:
                        new_o.append( [new_init, new_end])

                o[subject][behaviorOut] = list(new_o)
                '''



        logging.debug("intervals: {}".format(o))
        logging.debug("totalMediaLength: {}".format(plot_parameters["end time"]))
        logging.debug("excludeBehaviorsWithoutEvents: {}".format(plot_parameters["exclude behaviors"]))

        if not plot_time_ranges(o, selectedObservations[0], plot_parameters["start time"], plot_parameters["end time"], plot_parameters["exclude behaviors"], line_width=10):
            QMessageBox.warning(self, programName, "Check events")


    def open_project_json(self, projectFileName):
        """
        open project json
        """
        logging.info("open project: {0}".format(projectFileName))
        if not os.path.isfile(projectFileName):
            QMessageBox.warning(self, programName, "File not found")
            return

        s = open(projectFileName, "r").read()

        try:
            self.pj = json.loads(s)
        except:
            QMessageBox.critical(self, programName, "This project file seems corrupted")
            return

        self.projectChanged = False

        # transform time to decimal
        for obs in self.pj[OBSERVATIONS]:
            self.pj[OBSERVATIONS][obs]["time offset"] = Decimal(str(self.pj[OBSERVATIONS][obs]["time offset"]) )

            for idx,event in enumerate(self.pj[OBSERVATIONS][obs][EVENTS]):
                self.pj[OBSERVATIONS][obs][EVENTS][idx][pj_obs_fields["time"]] = Decimal(str(self.pj[OBSERVATIONS][obs][EVENTS][idx][pj_obs_fields["time"]]))

        # add coding_map key to old project files
        if not "coding_map" in self.pj:
            self.pj["coding_map"] = {}
            self.projectChanged = True

        # add subject description
        if 'project_format_version' in self.pj:
            for idx in [x for x in self.pj[SUBJECTS]]:
                if not 'description' in self.pj[SUBJECTS][ idx ] :
                    self.pj[SUBJECTS][ idx ]['description'] = ""
                    self.projectChanged = True

        # check if project file version is newer than current BORIS project file version
        if 'project_format_version' in self.pj and Decimal(self.pj['project_format_version']) > Decimal(project_format_version):
            QMessageBox.critical(self, programName, "This project file was created with a more recent version of BORIS.\nUpdate your version of BORIS to load it")
            self.pj = {"time_format": "hh:mm:ss",
            "project_date": "",
            "project_name": "",
            "project_description": "",
            "subjects_conf" : {},
            "behaviors_conf": {},
            "observations": {}}
            return


        # check if old version  v. 0 *.obs
        if 'project_format_version' not in self.pj:

            # convert VIDEO, AUDIO -> MEDIA
            self.pj['project_format_version'] = project_format_version
            self.projectChanged = True

            for obs in [x for x in self.pj[OBSERVATIONS]]:

                # remove 'replace audio' key
                if 'replace audio' in self.pj[OBSERVATIONS][obs]:
                    del self.pj[OBSERVATIONS][obs]['replace audio']

                if self.pj[OBSERVATIONS][obs][TYPE] in ['VIDEO','AUDIO']:
                    self.pj[OBSERVATIONS][obs][TYPE] = MEDIA

                # convert old media list in new one
                if len( self.pj[OBSERVATIONS][obs][FILE] ):
                    d1 = { PLAYER1:  [self.pj[OBSERVATIONS][obs][FILE][0]] }

                if len( self.pj[OBSERVATIONS][obs][FILE] ) == 2:
                    d1[PLAYER2] =  [self.pj[OBSERVATIONS][obs][FILE][1]]

                self.pj[OBSERVATIONS][obs][FILE] = d1

            # convert VIDEO, AUDIO -> MEDIA
            for idx in [x for x in self.pj[SUBJECTS]]:
                key, name = self.pj[SUBJECTS][idx]
                self.pj[SUBJECTS][idx] = {"key": key, "name": name, "description": ""}
            QMessageBox.information(self, programName, "The project file was converted to the new format (v. %s) in use with your version of BORIS.<br>Choose a new file name for saving it." % project_format_version)
            projectFileName = ''

        '''
        if not 'project_media_file_info' in self.pj:
            self.pj['project_media_file_info'] = {}
            self.projectChanged = True

        if not 'project_media_file_info' in self.pj:
            for obs in self.pj[OBSERVATIONS]:
                if 'media_file_info' in self.pj[OBSERVATIONS][obs]:
                    for h in self.pj[OBSERVATIONS][obs]['media_file_info']:
                        self.pj['project_media_file_info'][h] = self.pj[OBSERVATIONS][obs]['media_file_info'][h]
                        self.projectChanged = True
        '''

        for obs in self.pj[OBSERVATIONS]:
            if not "time offset second player" in self.pj[OBSERVATIONS][obs]:
                self.pj[OBSERVATIONS][obs]["time offset second player"] = Decimal("0.0")
                self.projectChanged = True

        # if one file is present in player #1 -> set "media_info" key with value of media_file_info
        '''
        for obs in self.pj[OBSERVATIONS]:
            try:
                if not 'media_info' in self.pj[OBSERVATIONS][obs] \
                    and len(self.pj[OBSERVATIONS][obs]['media_file_info']) == 1 \
                    and len(self.pj[OBSERVATIONS][obs]['file'][PLAYER1]) == 1 \
                    and len(self.pj[OBSERVATIONS][obs]['file'][PLAYER2]) == 0:
                        self.pj[OBSERVATIONS][obs]['media_info'] = \
                            {'length': {self.pj[OBSERVATIONS][obs]['file'][PLAYER1][0]:
                               self.pj[OBSERVATIONS][obs]['media_file_info'][list(self.pj[OBSERVATIONS][obs]['media_file_info'].keys())[0]]['video_length']/1000} }
                        # FPS
                        if 'nframe' in self.pj[OBSERVATIONS][obs]['media_file_info'][list(self.pj[OBSERVATIONS][obs]['media_file_info'].keys())[0]]:
                            self.pj[OBSERVATIONS][obs]['media_info']['fps'] = { self.pj[OBSERVATIONS][obs]['file'][PLAYER1][0]:
                                self.pj[OBSERVATIONS][obs]['media_file_info'][list(self.pj[OBSERVATIONS][obs]['media_file_info'].keys())[0]]['nframe'] / ( self.pj[OBSERVATIONS][obs]['media_file_info'][list(self.pj[OBSERVATIONS][obs]['media_file_info'].keys())[0]]['video_length']/1000 )
                                 }
                        self.projectChanged = True

            except:
                pass
        '''

        # check program version
        memProjectChanged = self.projectChanged

        self.initialize_new_project()

        self.projectChanged = memProjectChanged

        self.load_obs_in_lwConfiguration()

        self.load_subjects_in_twSubjects()

        self.projectFileName = projectFileName

        self.project = True

        self.menu_options()


    def open_project_activated(self):

        # check if current observation
        if self.observationId:
            if dialog.MessageDialog(programName, "There is a current observation. What do you want to do?", ["Close observation", "Continue observation"]) == "Close observation":
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

        fd = QFileDialog(self)
        fileName = fd.getOpenFileName(self, "Open project", "", "Project files (*.boris);;Old project files (*.obs);;All files (*)")

        if fileName:
            self.open_project_json(fileName)


    def initialize_new_project(self):
        """
        initialize interface and variables for a new project
        """
        logging.info("initialize new project...")

        self.lbLogoUnito.setVisible(False)
        self.lbLogoBoris.setVisible(False)

        self.dwConfiguration.setVisible(True)
        self.dwSubjects.setVisible(True)

        self.projectChanged = True


    def close_project(self):
        """
        close current project
        """

        # check if current observation
        if self.observationId:
            response = dialog.MessageDialog(programName, "There is a current observation. What do you want to do?", ["Close observation", "Continue observation"])
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

        self.dwConfiguration.setVisible(False)
        self.dwSubjects.setVisible(False)

        self.projectChanged = False
        self.setWindowTitle(programName)

        self.pj = {"time_format": self.timeFormat, "project_date": "", "project_name": "", "project_description": "", "subjects_conf" : {}, "behaviors_conf": {}, "observations": {}  }
        self.project = False

        self.readConfigFile()

        self.menu_options()

        self.lbLogoUnito.setVisible(True)
        self.lbLogoBoris.setVisible(True)

        self.lbFocalSubject.setVisible(False)
        self.lbCurrentStates.setVisible(False)


    def convertTime(self, sec):
        '''
        convert time in base of current format
        return string
        '''

        if self.timeFormat == S:
            return '%.3f' % sec

        if self.timeFormat == HHMMSS:
            return seconds2time(sec)


    def edit_project(self, mode):
        """
        project management
        mode: new/edit
        """

        if self.observationId:
            QMessageBox.warning(self, programName , "Close the running observation before creating/modifying the project.")
            return

        if mode == NEW:

            if self.projectChanged:
                response = dialog.MessageDialog(programName, "What to do about the current unsaved project?", [SAVE, DISCARD, CANCEL])

                if response == SAVE:
                    self.save_project_activated()

                if response == CANCEL:
                    return

            # empty main window tables
            self.twConfiguration.setRowCount(0)   # behaviors
            self.twSubjects.setRowCount(0)
            self.twEvents.setRowCount(0)


        newProjectWindow = projectDialog(logging.getLogger().getEffectiveLevel())

        if self.projectWindowGeometry:
            newProjectWindow.restoreGeometry( self.projectWindowGeometry)

        newProjectWindow.setWindowTitle(mode + ' project')
        newProjectWindow.tabProject.setCurrentIndex(0)   # project information

        newProjectWindow.obs = self.pj[ETHOGRAM]
        newProjectWindow.subjects_conf = self.pj[SUBJECTS]

        if self.pj['time_format'] == S:
            newProjectWindow.rbSeconds.setChecked(True)

        if self.pj['time_format'] == HHMMSS:
            newProjectWindow.rbHMS.setChecked(True)

        if mode == NEW:

            newProjectWindow.dteDate.setDateTime(QDateTime.currentDateTime())
            newProjectWindow.lbProjectFilePath.setText("")

        if mode == EDIT:

            if self.pj['project_name']:
                newProjectWindow.leProjectName.setText(self.pj["project_name"])

            newProjectWindow.lbProjectFilePath.setText( 'Project file path: ' + self.projectFileName )

            if self.pj['project_description']:
                newProjectWindow.teDescription.setPlainText(self.pj["project_description"])

            if self.pj['project_date']:

                q = QDateTime.fromString(self.pj['project_date'], 'yyyy-MM-ddThh:mm:ss')

                newProjectWindow.dteDate.setDateTime( q )
            else:
                newProjectWindow.dteDate.setDateTime( QDateTime.currentDateTime() )


            # load subjects in editor
            if self.pj[SUBJECTS]:

                for idx in [str(x) for x in sorted([int(x) for x in self.pj[SUBJECTS].keys() ])]:
                    newProjectWindow.twSubjects.setRowCount(newProjectWindow.twSubjects.rowCount() + 1)
                    for i, field in enumerate( subjectsFields ):
                        item = QTableWidgetItem(self.pj[SUBJECTS][idx][field])
                        newProjectWindow.twSubjects.setItem(newProjectWindow.twSubjects.rowCount() - 1, i ,item)

                newProjectWindow.twSubjects.resizeColumnsToContents()


            # load observation in project window
            newProjectWindow.twObservations.setRowCount(0)
            if self.pj[OBSERVATIONS]:

                for obs in sorted( self.pj[OBSERVATIONS].keys() ):

                    newProjectWindow.twObservations.setRowCount(newProjectWindow.twObservations.rowCount() + 1)

                    item = QTableWidgetItem(obs)
                    newProjectWindow.twObservations.setItem(newProjectWindow.twObservations.rowCount() - 1, 0, item)

                    item = QTableWidgetItem( self.pj[OBSERVATIONS][obs]['date'].replace('T',' ') )
                    newProjectWindow.twObservations.setItem(newProjectWindow.twObservations.rowCount() - 1, 1, item)

                    item = QTableWidgetItem( self.pj[OBSERVATIONS][obs]['description'] )
                    newProjectWindow.twObservations.setItem(newProjectWindow.twObservations.rowCount() - 1, 2, item)

                    mediaList = []
                    if self.pj[OBSERVATIONS][obs][TYPE] in [MEDIA]:
                        for idx in self.pj[OBSERVATIONS][obs][FILE]:
                            for media in self.pj[OBSERVATIONS][obs][FILE][idx]:
                                mediaList.append('#%s: %s' % (idx , media))

                    elif self.pj[OBSERVATIONS][obs][TYPE] in [LIVE]:
                        mediaList = [LIVE]

                    item = QTableWidgetItem('\n'.join( mediaList ))
                    newProjectWindow.twObservations.setItem(newProjectWindow.twObservations.rowCount() - 1, 3, item)

                newProjectWindow.twObservations.resizeColumnsToContents()

            # configuration of behaviours
            if self.pj[ETHOGRAM]:

                newProjectWindow.signalMapper = QSignalMapper(self)
                newProjectWindow.comboBoxes = []

                for i in [str(x) for x in sorted([int(x) for x in self.pj[ETHOGRAM].keys()])]:

                    newProjectWindow.twBehaviors.setRowCount(newProjectWindow.twBehaviors.rowCount() + 1)

                    for field in fields:

                        item = QTableWidgetItem()

                        if field == TYPE:

                            # add combobox with event type
                            newProjectWindow.comboBoxes.append(QComboBox())
                            newProjectWindow.comboBoxes[-1].addItems(observation_types)
                            newProjectWindow.comboBoxes[-1].setCurrentIndex(observation_types.index(self.pj[ETHOGRAM][i][field]))

                            newProjectWindow.signalMapper.setMapping(newProjectWindow.comboBoxes[-1], newProjectWindow.twBehaviors.rowCount() - 1)
                            newProjectWindow.comboBoxes[-1].currentIndexChanged['int'].connect(newProjectWindow.signalMapper.map)

                            newProjectWindow.twBehaviors.setCellWidget(newProjectWindow.twBehaviors.rowCount() - 1, fields[field], newProjectWindow.comboBoxes[-1])

                        else:
                            if field in self.pj[ETHOGRAM][i]:
                                item.setText(self.pj[ETHOGRAM][i][field])
                            else:
                                item.setText("")

                            if field in ['excluded', 'coding map', 'modifiers']:
                                item.setFlags(Qt.ItemIsEnabled)

                            newProjectWindow.twBehaviors.setItem(newProjectWindow.twBehaviors.rowCount() - 1, fields[field] ,item)

                newProjectWindow.signalMapper.mapped["int"].connect(newProjectWindow.comboBoxChanged)

                newProjectWindow.twBehaviors.resizeColumnsToContents()



            # load independent variables
            if INDEPENDENT_VARIABLES in self.pj:
                for i in [str(x) for x in sorted([int(x) for x in self.pj[INDEPENDENT_VARIABLES].keys()])]:
                    newProjectWindow.twVariables.setRowCount(newProjectWindow.twVariables.rowCount() + 1)

                    for idx, field in enumerate(tw_indVarFields):

                        if field == TYPE:

                            comboBox = QComboBox()
                            comboBox.addItems([NUMERIC, TEXT])

                            comboBox.setCurrentIndex( 0 )
                            if self.pj[ INDEPENDENT_VARIABLES ][i][field] == TEXT:
                                comboBox.setCurrentIndex( 1 )

                            newProjectWindow.twVariables.setCellWidget(newProjectWindow.twVariables.rowCount() - 1, 2, comboBox)

                        else:

                            item = QTableWidgetItem()
                            item.setText( self.pj[INDEPENDENT_VARIABLES][i][field] )
                            newProjectWindow.twVariables.setItem(newProjectWindow.twVariables.rowCount() - 1, idx,item)

                newProjectWindow.twVariables.resizeColumnsToContents()


        newProjectWindow.dteDate.setDisplayFormat("yyyy-MM-dd hh:mm:ss")

        if mode == NEW:

            self.pj = {"time_format": HHMMSS,\
            "project_date": "", \
            "project_name": "", \
            "project_description": "", \
            SUBJECTS : {},\
            ETHOGRAM: {}, \
            OBSERVATIONS: {},
            "coding_map": {} }

        # pass copy of self.pj
        newProjectWindow.pj = dict(self.pj)


        if newProjectWindow.exec_():  #button OK

            # retrieve project dict from window
            self.pj = dict( newProjectWindow.pj )

            if mode == NEW:
                self.projectFileName = ''

            self.project = True

            self.pj['project_name'] = newProjectWindow.leProjectName.text()
            self.pj['project_date'] = newProjectWindow.dteDate.dateTime().toString(Qt.ISODate)
            self.pj['project_description'] = newProjectWindow.teDescription.toPlainText()

            # time format
            if newProjectWindow.rbSeconds.isChecked():
                self.timeFormat = S

            if newProjectWindow.rbHMS.isChecked():
                self.timeFormat = HHMMSS

            self.pj['time_format'] = self.timeFormat

            # configuration
            if newProjectWindow.lbObservationsState.text() != '':
                QMessageBox.warning(self, programName, newProjectWindow.lbObservationsState.text())
            else:

                self.twConfiguration.setRowCount(0)

                self.pj[ETHOGRAM] =  newProjectWindow.obs

                self.load_obs_in_lwConfiguration()

                self.pj[SUBJECTS] =  newProjectWindow.subjects_conf

                self.load_subjects_in_twSubjects()

                # load variables
                self.pj[ INDEPENDENT_VARIABLES ] =  newProjectWindow.indVar

            self.initialize_new_project()
            self.menu_options()

        self.projectWindowGeometry = newProjectWindow.saveGeometry()


    def new_project_activated(self):
        """
        new project
        """
        self.edit_project(NEW)


    def save_project_json(self, projectFileName):
        """
        save project to JSON file
        """
        def decimal_default(obj):
            if isinstance(obj, Decimal):
                return float(obj)
            raise TypeError

        logging.debug("save project json {0}:".format(projectFileName))

        self.pj["project_format_version"] = project_format_version

        try:
            f = open(projectFileName, "w")
            f.write(json.dumps(self.pj, indent=1, default=decimal_default))
            f.close()
        except:
            logging.critical("The project file can not be saved")
            QMessageBox.critical(self, programName, "The project file can not be saved!")
            return

        self.projectChanged = False


    def save_project_as_activated(self):
        """
        save current project asking for a new file name
        """
        self.projectFileName, filtr = QFileDialog(self).getSaveFileNameAndFilter(self, "Save project as", os.path.dirname(self.projectFileName), "Projects file (*.boris);;All files (*)")

        if not self.projectFileName:
            return "Not saved"

        # add .boris if filter = 'Projects file (*.boris)'
        if  filtr == "Projects file (*.boris)" and os.path.splitext(self.projectFileName)[1] != ".boris":
            self.projectFileName += ".boris"

        self.save_project_json(self.projectFileName)


    def save_project_activated(self):
        '''
        save current project
        '''

        if not self.projectFileName:
            if not self.pj['project_name']:
                txt = 'NONAME.boris'
            else:
                txt = self.pj['project_name'] + '.boris'
            os.chdir( os.path.expanduser("~")  )
            self.projectFileName, filtr = QFileDialog(self).getSaveFileNameAndFilter(self, 'Save project', txt, 'Projects file (*.boris);;All files (*)')

            if not self.projectFileName:
                return 'not saved'

            # add .boris if filter = 'Projects file (*.boris)'
            if  filtr == 'Projects file (*.boris)' and os.path.splitext(self.projectFileName)[1] != '.boris':
                self.projectFileName += '.boris'

            self.save_project_json(self.projectFileName)

        else:
            self.save_project_json(self.projectFileName)

        return ''


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

        # TODO: replace with function (see timerout)

        self.currentStates = self.get_current_states_by_subject(StateBehaviorsCodes,
                                                                self.pj[OBSERVATIONS][self.observationId][EVENTS],
                                                                dict(self.pj[SUBJECTS], **{"": {"name": ""}}),
                                                                currentTime)

        '''
        self.currentStates[""] = []
        for sbc in StateBehaviorsCodes:
            if len([x[pj_obs_fields['code']] for x in self.pj[OBSERVATIONS][self.observationId][EVENTS ] if x[ pj_obs_fields['subject'] ] == '' and x[ pj_obs_fields['code'] ] == sbc and x[ pj_obs_fields['time'] ] <= currentTime  ] ) % 2: # test if odd
                self.currentStates[''].append(sbc)
        '''

        # add states for all configured subjects
        for idx in self.pj[SUBJECTS]:
            # add subject index
            self.currentStates[idx] = []
            for sbc in StateBehaviorsCodes:
                if len([x[pj_obs_fields['code']] for x in self.pj[OBSERVATIONS][self.observationId][EVENTS ] if x[ pj_obs_fields['subject']] == self.pj[SUBJECTS][idx]['name'] and x[ pj_obs_fields['code'] ] == sbc and x[ pj_obs_fields['time'] ] <= currentTime  ] ) % 2: # test if odd
                    self.currentStates[idx].append(sbc)

        # show current states
        if self.currentSubject:
            # get index of focal subject (by name)
            idx = [idx for idx in self.pj[SUBJECTS] if self.pj[SUBJECTS][idx]['name'] == self.currentSubject][0]
            self.lbCurrentStates.setText('%s' % (', '.join(self.currentStates[ idx ])))
        else:
            self.lbCurrentStates.setText('%s' % (', '.join(self.currentStates[ '' ])))

        # show selected subjects
        for idx in [str(x) for x in sorted([int(x) for x in self.pj[SUBJECTS].keys() ])]:
            self.twSubjects.item(int(idx), len(subjectsFields) ).setText(','.join(self.currentStates[idx]))

        # check scan sampling
        #print(int(currentTime))

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

        result, selectedObservations = self.selectObservations(MULTIPLE)

        logging.debug("Selected observations: {0}".format(selectedObservations))

        if not selectedObservations:
            return

        plot_parameters = self.choose_obs_subj_behav(selectedObservations, 0)

        if not plot_parameters["selected subjects"] or not plot_parameters["selected behaviors"]:
            return

        exportDir = QFileDialog(self).getExistingDirectory(self, "Choose a directory to save subtitles", os.path.expanduser("~"), options=QFileDialog(self).ShowDirsOnly)
        if not exportDir:
            return

        cursor = self.loadEventsInDB(plot_parameters["selected subjects"], selectedObservations, plot_parameters["selected behaviors"])

        flagUnpairedEventFound = False

        for obsId in selectedObservations:

            for nplayer in [PLAYER1, PLAYER2]:

                if not self.pj[OBSERVATIONS][obsId][FILE][nplayer]:
                    continue

                duration1 = []   # in seconds
                for mediaFile in self.pj[OBSERVATIONS][obsId][FILE][nplayer]:
                    duration1.append(self.pj[OBSERVATIONS][obsId]["media_info"]["length"][mediaFile])

                subtitles = {}
                for subject in plot_parameters["selected subjects"]:

                    for behavior in plot_parameters["selected behaviors"]:

                        cursor.execute( "SELECT occurence, modifiers FROM events where observation = ? AND subject = ? AND  code = ? ORDER BY code, occurence", (obsId, subject, behavior) )
                        rows = list(cursor.fetchall() )
                        if STATE in self.eventType(behavior).upper() and len( rows ) % 2:
                            #continue
                            flagUnpairedEventFound = True
                            continue

                        for idx, row in enumerate(rows):

                            print( row["occurence"] )

                            mediaFileIdx = [idx1 for idx1, x in enumerate(duration1) if row["occurence"] >= sum(duration1[0:idx1])][-1]
                            if mediaFileIdx not in subtitles:
                                subtitles[mediaFileIdx] = []

                            # subtitle color
                            if subject == NO_FOCAL_SUBJECT:
                                col = "white"
                            else:
                                col = subtitlesColors[plot_parameters["selected subjects"].index(subject) % len(subtitlesColors)]

                            behaviorStr = behavior
                            if plot_parameters["include modifiers"] and row[1]:
                                behaviorStr += " ({0})".format(row[1].replace("|", ", "))

                            if POINT in self.eventType(behavior).upper():
                                laps =  "{0} --> {1}".format(seconds2time(row["occurence"]).replace(".", ","), seconds2time(row["occurence"] + 0.5).replace(".", ",") )
                                subtitles[mediaFileIdx].append( [laps, """<font color="{0}">{1}: {2}</font>""".format(col, subject, behaviorStr) ] )

                            if STATE in self.eventType(behavior).upper():
                                if idx % 2 == 0:

                                    start = seconds2time(round(row["occurence"] - sum( duration1[0:mediaFileIdx]), 3)).replace(".", ",")
                                    stop = seconds2time(round(rows[idx + 1]["occurence"] - sum( duration1[0:mediaFileIdx]), 3)).replace(".", ",")

                                    laps =  "{start} --> {stop}".format(start=start, stop=stop)
                                    subtitles[mediaFileIdx].append( [laps, """<font color="{0}">{1}: {2}</font>""".format(col, subject, behaviorStr) ] )

                #print(subtitles)
                try:
                    for mediaIdx in subtitles:
                        #print(mediaIdx, mediaIdx)
                        subtitles[mediaIdx].sort()
                        with open( "{exportDir}{sep}{fileName}.srt".format(exportDir=exportDir, sep=os.sep, fileName=os.path.basename(self.pj[OBSERVATIONS][obsId][FILE][nplayer][mediaIdx])), "w") as f:
                            for idx, sub in enumerate(subtitles[mediaIdx]):
                                f.write("{0}{3}{1}{3}{2}{3}{3}".format(idx + 1, sub[0], sub[1], os.linesep))
                except:
                    errorMsg = sys.exc_info()[1].strerror
                    logging.critical(errorMsg)
                    QMessageBox.critical(None, programName, errorMsg, QMessageBox.Ok | QMessageBox.Default, QMessageBox.NoButton)


        self.statusbar.showMessage("Subtitles file(s) created in {} directory".format(exportDir), 0)


    def export_aggregated_events(self, format_):
        """
        export aggregated events in SQL (sql) or Tabular format (tab)
        """

        result, selectedObservations = self.selectObservations(MULTIPLE)

        if not selectedObservations:
            return

        plot_parameters = self.choose_obs_subj_behav(selectedObservations, maxTime=0, flagShowIncludeModifiers=False, flagShowExcludeBehaviorsWoEvents=False)

        if not plot_parameters["selected subjects"] or not plot_parameters["selected behaviors"]:
            return

        includeMediaInfo = dialog.MessageDialog(programName, "Include media info?", [YES, NO])

        if format_ == "sql":
            fileName = QFileDialog(self).getSaveFileName(self, "Export aggregated events in SQL format", "", "SQL dump file file (*.sql);;All files (*)")
            if includeMediaInfo == NO:
                out = "CREATE TABLE events (id INTEGER PRIMARY KEY ASC, observation TEXT, date DATE, subject TEXT, behavior TEXT, modifiers TEXT, event_type TEXT, start FLOAT, stop FLOAT, comment_start TEXT, comment_stop TEXT);" + os.linesep
            else:
                pass # TODO
            out += "BEGIN TRANSACTION;" + os.linesep
            template = """INSERT INTO events ( observation, date, subject, behavior, modifiers, event_type, start, stop, comment_start, comment_stop ) VALUES ("{observation}","{date}","{subject}","{behavior}","{modifiers}","{event_type}",{start},{stop},"{comment_start}","{comment_stop}");""" + os.linesep

        if format_ == "tab":
            fileName = QFileDialog(self).getSaveFileName(self, "Export aggregated events in tabular format", "" , "Events file (*.tsv *.txt);;All files (*)")
            if includeMediaInfo == YES:
                out = "Observation id{0}Observation date{0}Media file{0}Total media length{0}FPS{0}Subject{0}Behavior{0}Modifiers{0}Behavior type{0}Start{0}Stop{0}Comment start{0}Comment stop{1}".format("\t", os.linesep)
                template = "{observation}\t{date}\t{media_file}\t{total_length}\t{fps}\t{subject}\t{behavior}\t{modifiers}\t{event_type}\t{start}\t{stop}\t{comment_start}\t{comment_stop}" + os.linesep
            else:
                out = "Observation id{0}Observation date{0}Subject{0}Behavior{0}Modifiers{0}Behavior type{0}Start{0}Stop{0}Comment start{0}Comment stop{1}".format("\t", os.linesep)
                template = "{observation}\t{date}\t{subject}\t{behavior}\t{modifiers}\t{event_type}\t{start}\t{stop}\t{comment_start}\t{comment_stop}" + os.linesep

        if not fileName:
            return

        self.statusbar.showMessage("Exporting aggregated events", 0)
        flagUnpairedEventFound = False

        for obsId in selectedObservations:
            duration1 = []   # in seconds
            for mediaFile in self.pj[OBSERVATIONS][obsId][FILE][PLAYER1]:
                duration1.append(self.pj[OBSERVATIONS][obsId]["media_info"]["length"][mediaFile])

            cursor = self.loadEventsInDB(plot_parameters["selected subjects"], selectedObservations, plot_parameters["selected behaviors"])

            for subject in plot_parameters["selected subjects"]:

                for behavior in plot_parameters["selected behaviors"]:

                    cursor.execute("SELECT occurence, modifiers, comment FROM events WHERE observation = ? AND subject = ? AND code = ? ", (obsId, subject, behavior))
                    rows = list(cursor.fetchall())

                    if STATE in self.eventType(behavior).upper() and len(rows) % 2:  # unpaired events
                        flagUnpairedEventFound = True
                        continue

                    for idx, row in enumerate(rows):

                        mediaFileIdx = [idx1 for idx1, x in enumerate(duration1) if row["occurence"] >= sum(duration1[0:idx1])][-1]

                        if POINT in self.eventType(behavior).upper():

                            out += template.format( observation=obsId,
                                                    date=self.pj[OBSERVATIONS][obsId]["date"].replace("T", " "),
                                                    media_file=self.pj[OBSERVATIONS][obsId][FILE][PLAYER1][mediaFileIdx],
                                                    total_length=sum(duration1),
                                                    fps=self.pj[OBSERVATIONS][obsId]["media_info"]["fps"][self.pj[OBSERVATIONS][obsId][FILE][PLAYER1][mediaFileIdx]],
                                                    subject=subject,
                                                    behavior=behavior,
                                                    modifiers=row["modifiers"],
                                                    event_type=POINT,
                                                    start=row["occurence"],
                                                    stop=0,
                                                    comment_start=row["comment"],
                                                    comment_stop="")

                        if STATE in self.eventType(behavior).upper():
                            if idx % 2 == 0:
                                out += template.format( observation=obsId,
                                                        date=self.pj[OBSERVATIONS][obsId]["date"].replace("T", " "),
                                                        media_file=self.pj[OBSERVATIONS][obsId][FILE][PLAYER1][mediaFileIdx],
                                                        total_length=sum(duration1),
                                                        fps=self.pj[OBSERVATIONS][obsId]["media_info"]["fps"][self.pj[OBSERVATIONS][obsId][FILE][PLAYER1][mediaFileIdx]],
                                                        subject=subject,
                                                        behavior=behavior,
                                                        modifiers=row["modifiers"],
                                                        event_type=STATE,
                                                        start=row["occurence"],
                                                        stop=rows[idx + 1]["occurence"],
                                                        comment_start=row["comment"],
                                                        comment_stop=rows[idx + 1]["comment"])

        if format_ == "sql":
            out += "END TRANSACTION;" + os.linesep

        try:
            with open(fileName, "w") as f:
                f.write( out )
        except:
            errorMsg = sys.exc_info()[1].strerror
            logging.critical(errorMsg)
            QMessageBox.critical(None, programName, errorMsg, QMessageBox.Ok | QMessageBox.Default, QMessageBox.NoButton)


        if flagUnpairedEventFound:
            QMessageBox.warning(self, programName, "Some state events are not paired. They were excluded from export",\
                    QMessageBox.Ok | QMessageBox.Default, QMessageBox.NoButton)

        self.statusbar.showMessage("Aggregated events exported successfully", 0)



    def export_state_events_as_textgrid(self):
        """
        export state events as Praat textgrid
        """

        result, selectedObservations = self.selectObservations(MULTIPLE)

        if not selectedObservations:
            return

        plot_parameters = self.choose_obs_subj_behav(selectedObservations, maxTime=0, flagShowIncludeModifiers=False, flagShowExcludeBehaviorsWoEvents=False)

        if not plot_parameters["selected subjects"] or not plot_parameters["selected behaviors"]:
            return

        exportDir = QFileDialog(self).getExistingDirectory(self, "Export events as TextGrid", os.path.expanduser('~'), options=QFileDialog(self).ShowDirsOnly)
        if not exportDir:
            return

        self.statusbar.showMessage("Exporting events as TextGrid", 0)

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
            totalMediaDuration = round(self.observationTotalMediaLength(obsId), 3)
            cursor = self.loadEventsInDB(plot_parameters["selected subjects"], selectedObservations, plot_parameters["selected behaviors"])
            cursor.execute( "SELECT count(distinct subject) FROM events WHERE observation = '{}' AND subject in ('{}') AND type = 'STATE' ".format(obsId, "','".join(plot_parameters["selected subjects"])))
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
                    out += template.format(count=count, name="null", xmin=0.0, xmax=rows[0]["occurence"] )

                for idx, row in enumerate(rows):
                    if idx % 2 == 0:

                        # check if events not interlacced
                        if row["code"] != rows[idx + 1]["code"]:
                            QMessageBox.critical(None, programName, "The events are interlaced. It is not possible to produce the Praat TextGrid file", QMessageBox.Ok | QMessageBox.Default, QMessageBox.NoButton)
                            return

                        count += 1
                        out += template.format(count=count, name=row["code"], xmin=row["occurence"], xmax=rows[idx + 1]["occurence"] )

                        # check if difference is > 0.001
                        if len(rows) > idx + 2:
                            if rows[idx + 2]["occurence"] - rows[idx + 1]["occurence"] > 0.001:

                                logging.debug( type(rows[idx + 2]["occurence"]) )

                                logging.debug("difference: {}-{}={}".format( rows[idx + 2]["occurence"], rows[idx + 1]["occurence"], rows[idx + 2]["occurence"] - rows[idx + 1]["occurence"] ))

                                out += template.format(count=count + 1, name="null", xmin=rows[idx + 1]["occurence"], xmax=rows[idx + 2]["occurence"] )
                                count += 1
                            else:
                                logging.debug("difference <=0.001: {} - {} = {}".format( rows[idx + 2]["occurence"], rows[idx + 1]["occurence"], rows[idx + 2]["occurence"] - rows[idx + 1]["occurence"] ))
                                rows[idx + 2]["occurence"] = rows[idx + 1]["occurence"]
                                logging.debug("difference after: {} - {} = {}".format( rows[idx + 2]["occurence"], rows[idx + 1]["occurence"], rows[idx + 2]["occurence"] - rows[idx + 1]["occurence"] ))

                # check if last event ends at the end of media file
                if rows[-1]["occurence"] < self.observationTotalMediaLength(obsId):
                    count += 1
                    out += template.format(count=count, name="null", xmin=rows[-1]["occurence"], xmax=totalMediaDuration )

                # add info
                out = out.format(subjectIdx=subjectIdx, subject=subject, intervalsSize=count, intervalsMin=intervalsMin, intervalsMax=intervalsMax)


            try:
                with open( "{exportDir}{sep}{obsId}.textGrid".format( exportDir=exportDir, sep=os.sep, obsId=obsId ), "w") as f:
                    f.write(out)

                if flagUnpairedEventFound:
                    QMessageBox.warning(self, programName, "Some state events are not paired. They were excluded from export",\
                            QMessageBox.Ok | QMessageBox.Default, QMessageBox.NoButton)

                self.statusbar.showMessage("Events exported successfully", 10000)

            except:
                errorMsg = sys.exc_info()[1].strerror
                logging.critical(errorMsg)
                QMessageBox.critical(None, programName, errorMsg, QMessageBox.Ok | QMessageBox.Default, QMessageBox.NoButton)



    def media_file_info(self):
        """
        show info about current video
        """
        if self.observationId and self.playerType == VLC:

            media = self.mediaplayer.get_media()

            logging.info("State: {}".format(self.mediaplayer.get_state()))
            logging.info("Media (get_mrl): {}".format(bytes_to_str(media.get_mrl())))
            logging.info("media.get_meta(0): {}".format(media.get_meta(0)))
            logging.info("Track: {}/{}".format(self.mediaplayer.video_get_track(), self.mediaplayer.video_get_track_count()))
            logging.info("number of media in media list: {}".format(self.media_list.count()))
            logging.info(('get time: %s  duration: %s' % (self.mediaplayer.get_time(), media.get_duration())))
            logging.info(('Position: %s %%' % self.mediaplayer.get_position()))
            logging.info(('FPS: %s' % (self.mediaplayer.get_fps())))
            logging.info(('Rate: %s' % self.mediaplayer.get_rate()))
            logging.info(('Video size: %s' % str(self.mediaplayer.video_get_size(0))))  # num=0
            logging.info(('Scale: %s' % self.mediaplayer.video_get_scale()))
            logging.info(('Aspect ratio: %s' % self.mediaplayer.video_get_aspect_ratio()))
            logging.info('is seekable? {0}'.format(self.mediaplayer.is_seekable()))
            logging.info('has_vout? {0}'.format(self.mediaplayer.has_vout()))

            if platform.system() in ['Linux', 'Darwin']:
                out = ""
                for idx in self.pj[OBSERVATIONS][self.observationId][FILE]:
                    for file_ in self.pj[OBSERVATIONS][self.observationId][FILE][idx]:

                        #r = os.system( 'file -b "{}"'.format(file_) )
                        #if not r:
                        out +=  "<b>{}</b><br>".format(os.path.basename(file_))
                        out += subprocess.getoutput('file -b "{}"'.format(file_) ) + '<br>'
            else:
                out = "Current media file name: <b>{}</b><br>".format(url2path(media.get_mrl()))

            QMessageBox.about(self, programName + " - Media file information", "{}<br><br>Total duration: {} s".format(out, self.convertTime(sum(self.duration)/1000)))


    def switch_playing_mode(self):
        """
        switch between frame mode and VLC mode
        triggered by frame by frame button and toolbox item change
        """

        if self.playerType != VLC:
            return

        if self.playMode == FFMPEG:  # return to VLC mode

            self.playMode = VLC

            globalCurrentTime = int( self.FFmpegGlobalFrame  * (1000 / list(self.fps.values())[0]))

            logging.debug("switch_playing_mode new global current time: {} {}".format( globalCurrentTime, type(globalCurrentTime) ))

            # seek VLC on current time from FFmpeg mode

            logging.debug("globalCurrentTime: {0}".format(globalCurrentTime))
            logging.debug("self.duration: {0}".format(self.duration))

            for idx, media in enumerate(self.pj[OBSERVATIONS][self.observationId][FILE][PLAYER1]):
                if globalCurrentTime < sum(self.duration[0:idx + 1]):

                    self.mediaListPlayer.play_item_at_index( idx )

                    while True:
                        if self.mediaListPlayer.get_state() in [vlc.State.Playing, vlc.State.Ended]:
                            break

                    self.mediaListPlayer.pause()

                    currentMediaTime = int(globalCurrentTime - sum(self.duration[0:idx]))
                    break

            logging.debug("current media time: {0}".format(currentMediaTime))
            self.mediaplayer.set_time( currentMediaTime )

            self.toolBox.setCurrentIndex(VIDEO_TAB)

            self.FFmpegTimer.stop()

            logging.info("ffmpeg timer stopped")

            # set thread for cleaning temp directory
            if self.ffmpeg_cache_dir_max_size:
                self.cleaningThread.exiting = True

        #elif FFMPEG in self.availablePlayers:  # return to frame-by-frame
        else:

            # second video together
            if self.simultaneousMedia:
                logging.warning("Frame-by-frame mode is not available in multi-player mode")
                app.beep()
                self.actionFrame_by_frame.setChecked(False)
                self.statusbar.showMessage("Frame-by-frame mode is not available in multi-player mode", 5000)
                return

            if list(self.fps.values())[0] == 0:
                logging.warning("The frame per second value is not available. Frame-by-frame mode will not be available")
                QMessageBox.critical(None, programName, "The frame per second value is not available. Frame-by-frame mode will not be available",
                    QMessageBox.Ok | QMessageBox.Default, QMessageBox.NoButton)
                self.actionFrame_by_frame.setChecked(False)
                return

            if len(set( self.fps.values() )) != 1:
                logging.warning("The frame-by-frame mode will not be available because the video files have different frame rates")
                QMessageBox.warning(self, programName, "The frame-by-frame mode will not be available because the video files have different frame rates (%s)." % (', '.join([str(i) for i in list(self.fps.values())])),\
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
                self.imagesList.update([f.replace( self.imageDirectory + os.sep, '').split('_')[0] for f in glob.glob(self.imageDirectory + os.sep + '*')])

            logging.debug("frame-by-frame mode activated. Image directory {0}".format(self.imageDirectory))

            # show frame-by_frame tab
            self.toolBox.setCurrentIndex(1)

            globalTime = (sum(self.duration[0 : self.media_list.index_of_item(self.mediaplayer.get_media())]) + self.mediaplayer.get_time())

            logging.debug("switch_playing_mode  globalTime {0} s".format( globalTime/1000 ))

            fps = list(self.fps.values())[0]

            globalCurrentFrame = round(globalTime / (1000/fps))

            self.FFmpegGlobalFrame = globalCurrentFrame

            if self.FFmpegGlobalFrame > 0:
                self.FFmpegGlobalFrame -= 1

            self.FFmpegTimerOut()

            # set thread for cleaning temp directory
            if self.ffmpeg_cache_dir_max_size:
                self.cleaningThread.exiting = False
                self.cleaningThread.ffmpeg_cache_dir_max_size = self.ffmpeg_cache_dir_max_size * 1024 * 1024
                self.cleaningThread.tempdir = self.imageDirectory + os.sep
                self.cleaningThread.start()


        # enable/disable speed button
        self.actionNormalSpeed.setEnabled( self.playMode == VLC)
        self.actionFaster.setEnabled( self.playMode == VLC)
        self.actionSlower.setEnabled( self.playMode == VLC)

        logging.info( 'new play mode: {0}'.format( self.playMode ))

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

                            dirName, fileName = os.path.split(media)

                            snapshotFilePath = dirName + os.sep + os.path.splitext(fileName)[0] + "_" + str(self.FFmpegGlobalFrame) + ".png"

                            self.lbFFmpeg.pixmap().save(snapshotFilePath)
                            self.statusbar.showMessage("Snapshot saved in {}".format(snapshotFilePath), 0)
                            break

                else:  # VLC

                    current_media_path = url2path(self.mediaplayer.get_media().get_mrl())
                    dirName, fileName = os.path.split(current_media_path)
                    self.mediaplayer.video_take_snapshot(0, "{dirName}{sep}{fileNameWOExt}_{time}.png".format(
                                                              dirName=dirName,
                                                              sep=os.sep,
                                                              fileNameWOExt=os.path.splitext(fileName)[0],
                                                              time=self.mediaplayer.get_time())
                                                        ,0,0)

                    # check if multi mode
                    # second video together
                    if self.simultaneousMedia:

                        current_media_path = url2path(self.mediaplayer2.get_media().get_mrl())

                        dirName, fileName = os.path.split( current_media_path )
                        self.mediaplayer2.video_take_snapshot(0, "{dirName}{sep}{fileNameWOExt}_{time}.png".format(
                                                              dirName=dirName,
                                                              sep=os.sep,
                                                              fileNameWOExt=os.path.splitext(fileName)[0],
                                                              time=self.mediaplayer2.get_time()) ,0,0)


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
            editWindow.teTime.setTime(QtCore.QTime.fromString(seconds2time(laps), HHMMSSZZZ) )

        if self.timeFormat == S:
            editWindow.teTime.setVisible(False)
            editWindow.dsbTime.setValue(float(laps))

        sortedSubjects = [""] + sorted([self.pj[SUBJECTS][x]["name"] for x in self.pj[SUBJECTS]])

        editWindow.cobSubject.addItems(sortedSubjects)

        sortedCodes = sorted([self.pj[ETHOGRAM][x]['code'] for x in self.pj[ETHOGRAM]])

        editWindow.cobCode.addItems(sortedCodes)

        # activate signal
        #editWindow.cobCode.currentIndexChanged.connect(editWindow.codeChanged)

        editWindow.currentModifier = ""

        if editWindow.exec_():  #button OK

            if self.timeFormat == HHMMSS:
                newTime = time2seconds(editWindow.teTime.time().toString(HHMMSSZZZ))

            if self.timeFormat == S:
                newTime = Decimal(editWindow.dsbTime.value())

            """memTime = newTime"""

            # get modifier(s)
            # check mod type (QPushButton or QDialog)
            '''
            if type(editWindow.mod)  is select_modifiers.ModifiersRadioButton:
                modifiers = editWindow.mod.getModifiers()

                if len(modifiers) == 1:
                    modifier_str = modifiers[0]
                    if modifier_str == 'None':
                        modifier_str = ''
                else:
                    modifier_str = '|'.join( modifiers )

            #QPushButton coding map
            if type(editWindow.mod)  is QPushButton:
                modifier_str = editWindow.mod.text().split('\n')[1].replace('Area(s): ','')
            '''

            for obs_idx in self.pj[ETHOGRAM]:
                if self.pj[ETHOGRAM][obs_idx]['code'] == editWindow.cobCode.currentText():

                    event = self.full_event(obs_idx)

                    event['subject'] = editWindow.cobSubject.currentText()
                    if editWindow.leComment.toPlainText():
                        event['comment'] = editWindow.leComment.toPlainText()

                    self.writeEvent(event, newTime)
                    break


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
                editWindow.teTime.setTime(QtCore.QTime.fromString(seconds2time( self.pj[OBSERVATIONS][self.observationId][EVENTS][row][ 0 ] ), "hh:mm:ss.zzz") )

            if self.timeFormat == S:
                editWindow.teTime.setVisible(False)
                editWindow.dsbTime.setValue(self.pj[OBSERVATIONS][self.observationId][EVENTS][row][0])

            sortedSubjects = [""] + sorted([self.pj[SUBJECTS][x]["name"] for x in self.pj[SUBJECTS]])

            editWindow.cobSubject.addItems(sortedSubjects)

            if self.pj[OBSERVATIONS][self.observationId][EVENTS][row][SUBJECT_EVENT_FIELD] in sortedSubjects:
                editWindow.cobSubject.setCurrentIndex( sortedSubjects.index( self.pj[OBSERVATIONS][self.observationId][EVENTS][row][ SUBJECT_EVENT_FIELD ] ) )
            else:
                QMessageBox.warning(self, programName, "The subject <b>{}</b> do not exists more in the subject's list".format(self.pj[OBSERVATIONS][self.observationId][EVENTS][row][ pj_obs_fields['subject']]))
                editWindow.cobSubject.setCurrentIndex(0)

            sortedCodes = sorted( [ self.pj[ETHOGRAM][x]["code"] for x in self.pj[ETHOGRAM]])

            editWindow.cobCode.addItems( sortedCodes )

            # check if selected code is in code's list (no modification of codes)
            if self.pj[OBSERVATIONS][self.observationId][EVENTS][row][ pj_obs_fields["code"] ] in sortedCodes:
                editWindow.cobCode.setCurrentIndex( sortedCodes.index( self.pj[OBSERVATIONS][self.observationId][EVENTS][row][ pj_obs_fields["code"] ] ) )
            else:
                logging.warning("The behaviour <b>{0}</b> do not exists more in the ethogram".format(self.pj[OBSERVATIONS][self.observationId][EVENTS][row][ pj_obs_fields["code"] ] ) )
                QMessageBox.warning(self, programName, "The behaviour <b>%s</b> do not exists more in the ethogram" % self.pj[OBSERVATIONS][self.observationId][EVENTS][row][ pj_obs_fields["code"]])
                editWindow.cobCode.setCurrentIndex(0)


            logging.debug("original modifiers: {}".format(self.pj[OBSERVATIONS][self.observationId][EVENTS][row][ pj_obs_fields['modifier'] ]))
            # pass current modifier(s) to window
            """
            editWindow.currentModifier = self.pj[OBSERVATIONS][self.observationId][EVENTS][row][ pj_obs_fields['modifier'] ]
            """

            # comment
            editWindow.leComment.setPlainText( self.pj[OBSERVATIONS][self.observationId][EVENTS][row][ pj_obs_fields['comment'] ])

            # load modifiers
            """
            editWindow.codeChanged()
            """

            # activate signal
            """
            editWindow.cobCode.currentIndexChanged.connect(editWindow.codeChanged)
            """

            if editWindow.exec_():  #button OK

                self.projectChanged = True

                if self.timeFormat == HHMMSS:
                    newTime = time2seconds(editWindow.teTime.time().toString(HHMMSSZZZ))

                if self.timeFormat == S:
                    newTime = Decimal(editWindow.dsbTime.value())

                for obs_idx in self.pj[ETHOGRAM]:

                    if self.pj[ETHOGRAM][obs_idx]["code"] == editWindow.cobCode.currentText():
                        event = self.full_event(obs_idx)
                        event["subject"] = editWindow.cobSubject.currentText()
                        event["comment"] = editWindow.leComment.toPlainText()
                        event["row"] = row
                        event["original_modifiers"] = self.pj[OBSERVATIONS][self.observationId][EVENTS][row][ pj_obs_fields['modifier'] ]

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
        '''
        add event by double-clicking in ethogram list
        '''
        if self.observationId:
            if self.twConfiguration.selectedIndexes():

                ethogramRow = self.twConfiguration.selectedIndexes()[0].row()

                logging.debug('ethogram row: {0}'.format(ethogramRow  ))
                logging.debug(self.pj[ETHOGRAM][str(ethogramRow)])

                code = self.twConfiguration.item(ethogramRow, 1).text()

                event = self.full_event( str(ethogramRow) )

                logging.debug('event: {0}'.format( event ))

                self.writeEvent( event , self.getLaps())

        else:
            self.no_observation()



    def actionUser_guide_triggered(self):
        """
        open user guide URL if it exists otherwise open user guide URL
        """
        userGuideFile = os.path.dirname(os.path.realpath(__file__)) + "/boris_user_guide.pdf"
        if os.path.isfile(userGuideFile) :
            if sys.platform.startswith("linux"):
                subprocess.call(["xdg-open", userGuideFile])
            else:
                os.startfile(userGuideFile)
        else:
            QDesktopServices.openUrl(QUrl("http://boris.readthedocs.org"))


    def actionAbout_activated(self):
        """ about dialog """

        if __version__ == 'DEV':
            ver = 'DEVELOPMENT VERSION'
        else:
            ver = 'v. {0}'.format(__version__)

        players = []
        players.append("VLC media player v. {}".format(bytes_to_str(vlc.libvlc_get_version())))
        players.append("VLC libraries path: {}".format(vlc.plugin_path))
        players.append("FFmpeg path: {}".format(self.ffmpeg_bin))


        QMessageBox.about(self, "About " + programName,"""<b>{prog_name}</b> {ver} - {date}
        <p>Copyright &copy; 2012-2016 Olivier Friard - Marco Gamba<br>
        Department of Life Sciences and Systems Biology<br>
        University of Torino - Italy<br>
        <br>
        BORIS is released under the <a href="http://www.gnu.org/copyleft/gpl.html">GNU General Public License</a><br>
        <br>
        The authors would like to acknowledge Sergio Castellano, Valentina Matteucci and Laura Ozella for their precious help.<br>
        <br>
        See <a href="http://www.boris.unito.it">www.boris.unito.it</a> for more details.<br>
        <p>Python {python_ver} - Qt {qt_ver} - PyQt4 {pyqt_ver} on {system}<br><br>
        {players}""".format(prog_name=programName,
                            ver=ver,
                            date=__version_date__,
                            python_ver=platform.python_version(),
                            pyqt_ver=PYQT_VERSION_STR,
                            system=platform.system(),
                            qt_ver=QT_VERSION_STR,
                            players="<br>".join(players)))


    def hsVideo_sliderMoved(self):
        """
        media position slider moved
        adjust media position
        """

        if self.pj[OBSERVATIONS][self.observationId][TYPE] in [MEDIA]:

            if self.playerType == VLC and self.playMode == VLC:
                sliderPos = self.hsVideo.value() / (slider_maximum - 1)
                videoPosition = sliderPos * self.mediaplayer.get_length()
                self.mediaplayer.set_time( int(videoPosition) )
                # second video together
                if self.simultaneousMedia:
                    # synchronize 2nd player
                    self.mediaplayer2.set_time( int(self.mediaplayer.get_time()  - self.pj[OBSERVATIONS][self.observationId][TIME_OFFSET_SECOND_PLAYER] * 1000) )
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
                ROW = len( self.pj[OBSERVATIONS][self.observationId][EVENTS] )
            else:
                cr_list =  [idx for idx, x in enumerate(self.pj[OBSERVATIONS][self.observationId][EVENTS][:-1]) if x[0] <= ct and self.pj[OBSERVATIONS][self.observationId][EVENTS][idx+1][0] > ct ]

                if cr_list:
                    ROW = cr_list[0]
                    if not self.trackingCursorAboveEvent:
                        ROW +=  1
                else:
                    ROW = -1

            self.twEvents.setItemDelegate(StyledItemDelegateTriangle(self.twEvents))
            self.twEvents.scrollToItem( self.twEvents.item(ROW, 0) )

    def get_current_states_by_subject(self, stateBehaviorsCodes, events, subjects, time):
        """
        get current states for subjects at given time

        """
        currentStates = {}
        for idx in subjects:
            currentStates[idx] = []
            for sbc in stateBehaviorsCodes:
                if len([x[ EVENT_BEHAVIOR_FIELD_IDX ] for x in events
                                                       if x[EVENT_SUBJECT_FIELD_IDX] == subjects[idx]["name"]
                                                          and x[EVENT_BEHAVIOR_FIELD_IDX] == sbc
                                                          and x[EVENT_TIME_FIELD_IDX] <= time]) % 2: # test if odd
                    currentStates[idx].append(sbc)
        return currentStates



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

            # current media time
            mediaTime = self.mediaplayer.get_time()

            # highlight current event in tw events and scroll event list
            self.get_events_current_row()

            # check if second video
            if self.simultaneousMedia:

                if self.pj[OBSERVATIONS][self.observationId][TIME_OFFSET_SECOND_PLAYER] == 0:
                    t1, t2 = self.mediaplayer.get_time(), self.mediaplayer2.get_time()
                    if abs(t1 - t2) >= 300:
                        self.mediaplayer2.set_time( t1 )

                if TIME_OFFSET_SECOND_PLAYER in self.pj[OBSERVATIONS][self.observationId]:

                    if self.pj[OBSERVATIONS][self.observationId][TIME_OFFSET_SECOND_PLAYER] > 0:

                        if mediaTime < self.pj[OBSERVATIONS][self.observationId][TIME_OFFSET_SECOND_PLAYER] *1000:

                            if self.mediaListPlayer2.get_state() == vlc.State.Playing:
                                self.mediaplayer2.set_time(0)
                                self.mediaListPlayer2.pause()
                        else:
                            if self.mediaListPlayer.get_state() == vlc.State.Playing:
                                t1, t2 = self.mediaplayer.get_time(), self.mediaplayer2.get_time()
                                if abs((t1-t2) - self.pj[OBSERVATIONS][self.observationId][TIME_OFFSET_SECOND_PLAYER] * 1000) >= 300 :  # synchr if diff >= 300 ms
                                    self.mediaplayer2.set_time( int(t1 - self.pj[OBSERVATIONS][self.observationId][TIME_OFFSET_SECOND_PLAYER] * 1000) )
                                self.mediaListPlayer2.play()

                    if self.pj[OBSERVATIONS][self.observationId][TIME_OFFSET_SECOND_PLAYER] < 0:
                        mediaTime2 = self.mediaplayer2.get_time()

                        if mediaTime2 < abs(self.pj[OBSERVATIONS][self.observationId][TIME_OFFSET_SECOND_PLAYER] *1000):

                            if self.mediaListPlayer.get_state() == vlc.State.Playing:
                                self.mediaplayer.set_time(0)
                                self.mediaListPlayer.pause()
                        else:
                            if self.mediaListPlayer2.get_state() == vlc.State.Playing:
                                t1, t2 = self.mediaplayer.get_time(), self.mediaplayer2.get_time()
                                if abs((t2-t1) + self.pj[OBSERVATIONS][self.observationId][TIME_OFFSET_SECOND_PLAYER] * 1000) >= 300 :  # synchr if diff >= 300 ms
                                    self.mediaplayer.set_time( int(t2 + self.pj[OBSERVATIONS][self.observationId][TIME_OFFSET_SECOND_PLAYER] * 1000) )
                                self.mediaListPlayer.play()


            currentTimeOffset = Decimal(currentTime / 1000) + Decimal(self.pj[OBSERVATIONS][self.observationId][TIME_OFFSET])

            totalGlobalTime = sum(self.duration)

            if self.mediaplayer.get_length():

                self.mediaTotalLength = self.mediaplayer.get_length() / 1000

                # current state(s)

                # extract State events
                StateBehaviorsCodes = [self.pj[ETHOGRAM][x]['code'] for x in [y for y in self.pj[ETHOGRAM] if STATE in self.pj[ETHOGRAM][y][TYPE].upper()]]

                self.currentStates = {}

                # add current states for all subject and for "no focal subject"

                self.currentStates = self.get_current_states_by_subject(StateBehaviorsCodes, self.pj[OBSERVATIONS][self.observationId][EVENTS], dict(self.pj[SUBJECTS], **{"": {"name": ""}}), currentTimeOffset)
                '''
                subjects_and_nofocal = dict(self.pj[SUBJECTS], **{"": {"name": ""}})  # add "" for NO FOCAL SUBJECT
                for idx in subjects_and_nofocal:
                    self.currentStates[idx] = []
                    for sbc in StateBehaviorsCodes:
                        if len([x[ pj_obs_fields["code"]] for x in self.pj[OBSERVATIONS][self.observationId][EVENTS]
                                                               if x[ pj_obs_fields["subject"]] == subjects_and_nofocal[idx]["name"]
                                                                  and x[ pj_obs_fields["code"]] == sbc
                                                                  and x[ pj_obs_fields["time"]] <= currentTimeOffset  ] ) % 2: # test if odd
                            self.currentStates[idx].append(sbc)
                '''

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
                for idx in [str(x) for x in sorted([int(x) for x in self.pj[SUBJECTS].keys()])]:
                    self.twSubjects.item(int(idx), len(subjectsFields)).setText(",".join(self.currentStates[idx]))

                mediaName = self.mediaplayer.get_media().get_meta(0)

                # update status bar
                msg = ''
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
                    # show time on status bar
                    self.lbTime.setText( msg )

                    # set video scroll bar
                    if scrollSlider:
                        self.hsVideo.setValue(mediaTime / self.mediaplayer.get_length() * (slider_maximum - 1))
            else:
                self.statusbar.showMessage("Media length not available now", 0)

            if (self.memMedia and mediaName != self.memMedia) or (self.mediaListPlayer.get_state() == vlc.State.Ended and self.timer.isActive()):

                if CLOSE_BEHAVIORS_BETWEEN_VIDEOS in self.pj[OBSERVATIONS][self.observationId] and self.pj[OBSERVATIONS][self.observationId][CLOSE_BEHAVIORS_BETWEEN_VIDEOS] :

                    logging.debug('video changed')
                    logging.debug('current states: {}'.format( self.currentStates))

                    for subjIdx in self.currentStates:

                        if subjIdx:
                            subjName = self.pj[SUBJECTS][subjIdx]["name"]
                        else:
                            subjName = ''

                        for behav in self.currentStates[subjIdx]:

                            cm = ''
                            for ev in self.pj[OBSERVATIONS][self.observationId][EVENTS]:
                                if ev[EVENT_TIME_FIELD_IDX] > currentTime / 1000:  # time
                                    break

                                if ev[EVENT_SUBJECT_FIELD_IDX] == subjName:  # current subject name
                                    if ev[EVENT_BEHAVIOR_FIELD_IDX] == behav:   # code
                                        cm = ev[EVENT_MODIFIER_FIELD_IDX]

                            #self.pj[OBSERVATIONS][self.observationId][EVENTS].append([currentTime / 1000 - Decimal('0.001'), subjName, behav, cm, ''] )

                            event = {"subject": subjName, "code": behav, "modifiers": cm, "comment": "", "excluded": ""}

                            self.writeEvent(event, currentTime / 1000 - Decimal("0.001"))

                            #self.loadEventsInTW(self.observationId)

            self.memMedia = mediaName

            if self.mediaListPlayer.get_state() == vlc.State.Ended:
                self.timer.stop()


    def load_obs_in_lwConfiguration(self):
        """
        fill ethogram table with ethogram from pj
        """

        self.twConfiguration.setRowCount(0)

        if self.pj[ETHOGRAM]:

            for idx in [str(x) for x in sorted([int(x) for x in self.pj[ETHOGRAM].keys() ])]:

                self.twConfiguration.setRowCount(self.twConfiguration.rowCount() + 1)

                for col, field in enumerate(["key", "code", "type", "description", "modifiers", "excluded"]):
                    self.twConfiguration.setItem(self.twConfiguration.rowCount() - 1, col , QTableWidgetItem( self.pj[ETHOGRAM][idx][field] ))


    def load_subjects_in_twSubjects(self):
        """
        fill subjects table widget with subjects from self.subjects_conf
        """

        self.twSubjects.setRowCount(0)


        for idx in [str(x) for x in sorted([int(x) for x in self.pj[SUBJECTS].keys() ])]:

            self.twSubjects.setRowCount(self.twSubjects.rowCount() + 1)

            for idx2, field in enumerate( subjectsFields ):
                self.twSubjects.setItem(self.twSubjects.rowCount() - 1, idx2 , QTableWidgetItem( self.pj[SUBJECTS][ idx ][field] ))

            # add cell for current state(s) after last subject field
            self.twSubjects.setItem(self.twSubjects.rowCount() - 1, len(subjectsFields) , QTableWidgetItem( '' ))



    def update_events_start_stop(self):
        """
        update status start/stop of events in Events table
        take consideration of subject

        do not return value
        """

        stateEventsList = [self.pj[ETHOGRAM][x]['code'] for x in self.pj[ETHOGRAM] if STATE in self.pj[ETHOGRAM][x][TYPE].upper()]

        for row in range(0, self.twEvents.rowCount()):

            t = self.twEvents.item(row, tw_obs_fields['time'] ).text()

            if ":" in t:
                time = time2seconds(t)
            else:
                time = Decimal(t)

            code = self.twEvents.item(row, tw_obs_fields['code'] ).text()
            subject = self.twEvents.item(row, tw_obs_fields['subject'] ).text()

            # check if code is state
            if code in stateEventsList:
                # how many code before with same subject?
                if len([x[pj_obs_fields['code']] for x in self.pj[OBSERVATIONS][self.observationId][EVENTS] if x[pj_obs_fields["code"]] == code and x[pj_obs_fields["time"]] < time and x[pj_obs_fields["subject"]] == subject]) % 2: # test if odd
                    self.twEvents.item(row, tw_obs_fields[TYPE]).setText(STOP)
                else:
                    self.twEvents.item(row, tw_obs_fields[TYPE]).setText(START)


    def update_events_start_stop2(self, events):
        """
        returns events with status (START/STOP or POINT)
        take consideration of subject

        """

        stateEventsList = [self.pj[ETHOGRAM][x]["code"] for x in self.pj[ETHOGRAM] if STATE in self.pj[ETHOGRAM][x][TYPE].upper()]

        eventsFlagged = []
        for event in events:

            time, subject, code = event[0:3]

            # check if code is state
            if code in stateEventsList:

                # how many code before with same subject?
                if len([x[pj_obs_fields['code']] for x in events if x[pj_obs_fields['code']] == code and x[ pj_obs_fields['time']] < time and x[pj_obs_fields['subject']] == subject]) % 2: # test if odd
                    flag = STOP
                else:
                    flag = START

            else:
                flag = POINT

            eventsFlagged.append(event + [flag])

        return eventsFlagged


    def checkSameEvent(self, obsId, time, subject, code ):
        """
        check if a same event is already in events list (time, subject, code)
        """
        return [ time, subject, code ] in [[x[0],x[1],x[2]] for x in self.pj[OBSERVATIONS][obsId][EVENTS]]



    def writeEvent(self, event, memTime):
        """
        add event from pressed key to observation

        offset is added to event time

        ask for modifiers if configured

        load events in tableview

        scroll to active event
        """

        logging.debug("write event - event: {0}".format( event ))

        # add time offset
        memTime += Decimal(self.pj[OBSERVATIONS][self.observationId][TIME_OFFSET]).quantize(Decimal('.001'))

        # check if a same event is already in events list (time, subject, code)
        # "row" present in case of event editing
        if not "row" in event and self.checkSameEvent( self.observationId, memTime, self.currentSubject, event['code'] ):
            QMessageBox.warning(self, programName, "The same event already exists!\nSame time, code and subject.")
            return

        if not "from map" in event:   # modifiers only for behaviors without coding map
            # check if event has modifiers
            modifier_str = ''

            if event["modifiers"]:

                # pause media
                if self.pj[OBSERVATIONS][self.observationId][TYPE] in [MEDIA]:

                    if self.playerType == VLC:

                        if self.playMode == FFMPEG:
                            memState = self.FFmpegTimerOut.isActive()
                            if memState:
                                self.pause_video()
                        else:

                            memState = self.mediaListPlayer.get_state()
                            if memState == vlc.State.Playing:
                                self.pause_video()

                modifiersList = []
                if "|" in event["modifiers"]:
                    modifiersStringsList = event["modifiers"].split("|")
                    for modifiersString in modifiersStringsList:
                        modifiersList.append([s.strip() for s in modifiersString.split(",")])
                else:
                    modifiersList.append([s.strip() for s in event["modifiers"].split(",")])

                # check if editing (original_modifiers key)
                currentModifiers = event["original_modifiers"] if "original_modifiers" in event else ""

                modifierSelector = select_modifiers.ModifiersRadioButton(event["code"], modifiersList, currentModifiers)

                if modifierSelector.exec_():
                    modifiers = modifierSelector.getModifiers()
                    if len(modifiers) == 1:
                        modifier_str = modifiers[0]
                        if modifier_str == "None":
                            modifier_str = ""
                    else:
                        modifier_str = "|".join( modifiers )
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
        if not "row" in event:
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

            # current modifiers
            cm = {}
            for cs in csj :
                for ev in self.pj[OBSERVATIONS][self.observationId][EVENTS ]:
                    if ev[0] > memTime:  # time
                        break

                    if ev[1] == self.currentSubject:  # current subject name
                        if ev[2] == cs:   # code
                            cm[cs] = ev[3]

            for cs in csj :
                if (event['excluded'] and cs in event['excluded'].split(',')) or ( event['code'] == cs and cm[cs] != modifier_str):
                    # add excluded state event to observations (= STOP them)
                    self.pj[OBSERVATIONS][self.observationId][EVENTS].append([memTime - Decimal("0.001"), self.currentSubject, cs, cm[cs], ""])


        # remove key code from modifiers
        modifier_str = re.sub(" \(.*\)", "", modifier_str)

        if "comment" in event:
            comment = event["comment"]
        else:
            comment = ""

        if "subject" in event:
            subject = event["subject"]
        else:
            subject = self.currentSubject

        # add event to pj
        if "row" in event:
            self.pj[OBSERVATIONS][self.observationId][EVENTS][event['row']] =  [memTime, subject, event['code'], modifier_str, comment]
        else:
            self.pj[OBSERVATIONS][self.observationId][EVENTS].append( [memTime, subject, event['code'], modifier_str, comment] )

        # sort events in pj
        self.pj[OBSERVATIONS][self.observationId][EVENTS].sort()

        # reload all events in tw

        self.loadEventsInTW(self.observationId)

        item = self.twEvents.item([i for i,t in enumerate( self.pj[OBSERVATIONS][self.observationId][EVENTS]) if t[0] == memTime][0], 0)

        self.twEvents.scrollToItem( item )

        self.projectChanged = True




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

        item, ok = QInputDialog.getItem(self, programName, "The <b>{}</b> key codes more behaviors.<br>Choose the correct one:".format(obs_key), items, 0, False)

        if ok and item:
            obs_idx = self.detailedObs[item]
            return obs_idx
        else:
            return None


    def getLaps(self):
        """
        return cumulative laps time from begining of observation
        as Decimal in seconds
        no more add time offset!
        """

        if self.pj[OBSERVATIONS][self.observationId]["type"] in [LIVE]:

            if self.liveObservationStarted:
                now = QTime()
                now.start()  # current time
                memLaps = Decimal(str(round( self.liveStartTime.msecsTo(now) / 1000, 3)))
                return memLaps
            else:
                return Decimal("0.0")

        if self.pj[OBSERVATIONS][self.observationId]["type"] in [MEDIA]:

            if self.playerType == VIEWER:
                return Decimal(0)

            if self.playerType == VLC:

                if self.playMode == FFMPEG:
                    # cumulative time

                    memLaps = Decimal( self.FFmpegGlobalFrame * ( 1000 / list(self.fps.values())[0]) / 1000).quantize(Decimal(".001"))

                    return memLaps

                else: # playMode == VLC

                    # cumulative time
                    memLaps = Decimal(str(round(( sum(self.duration[0 : self.media_list.index_of_item(self.mediaplayer.get_media()) ]) \
                              + self.mediaplayer.get_time()) / 1000 , 3)))

                    return memLaps


    def full_event(self, obs_idx):
        """
        ask modifiers from coding if configured and add them under 'from map' key
        """

        event = dict(self.pj[ETHOGRAM][obs_idx])
        # check if coding map
        if "coding map" in self.pj[ETHOGRAM][obs_idx] and self.pj[ETHOGRAM][obs_idx]["coding map"]:

            # pause if media and media playing
            if self.pj[OBSERVATIONS][self.observationId][TYPE] in [MEDIA]:
                if self.playerType == VLC:
                    memState = self.mediaListPlayer.get_state()
                    if memState == vlc.State.Playing:
                        self.pause_video()

            self.codingMapWindow = coding_map.codingMapWindowClass( self.pj["coding_map"][ self.pj[ETHOGRAM][obs_idx]["coding map"] ] )

            self.codingMapWindow.resize(640, 640)
            if self.codingMapWindowGeometry:
                 self.codingMapWindow.restoreGeometry( self.codingMapWindowGeometry )

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
            logging.debug("current frame {0}".format( self.FFmpegGlobalFrame ))
            if self.FFmpegGlobalFrame > 1:
                self.FFmpegGlobalFrame -= 2
                #newTime = 1000 * self.FFmpegGlobalFrame / list(self.fps.values())[0]
                self.FFmpegTimerOut()
                logging.debug("new frame {0}".format(self.FFmpegGlobalFrame))

    def frame_forward(self):
        """
        go one frame forward
        """
        if self.playMode == FFMPEG:
            self.FFmpegTimerOut()


    def keyPressEvent(self, event):
        '''
        if (event.modifiers() & Qt.ShiftModifier):   # SHIFT

        QApplication.keyboardModifiers()

        http://qt-project.org/doc/qt-5.0/qtcore/qt.html#Key-enum

        ESC: 16777216
        '''

        '''print("focus", window.focusWidget() )'''

        self.timer_out()

        if not self.observationId:
            return

        # beep
        if self.confirmSound:
            app.beep()

        if self.playerType == VLC and self.mediaListPlayer.get_state() != vlc.State.Paused:
            flagPlayerPlaying = True
        else:
            flagPlayerPlaying = False

        if self.playerType == VIEWER:
            QMessageBox.critical(self, programName, "The current observation is opened in VIEW mode.\nIt is not allowed to log events in this mode.")
            return

        # check if media ever played

        if self.playerType == VLC:
            if self.mediaListPlayer.get_state() == vlc.State.NothingSpecial:
                return

        ek = event.key()

        logging.debug("key event {0}".format( ek ))

        if ek in [16777248, 16777249, 16777217, 16781571]: # shift tab ctrl
            return

        if ek == 16777216: # ESC
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

                logging.debug("current frame {0}".format( self.FFmpegGlobalFrame))
                if self.FFmpegGlobalFrame > 1:
                    self.FFmpegGlobalFrame -= 2
                    newTime = 1000 * self.FFmpegGlobalFrame / list(self.fps.values())[0]
                    self.FFmpegTimerOut()
                    logging.debug("new frame {0}".format(self.FFmpegGlobalFrame))
                return

            if ek == 42 or ek == Qt.Key_Right:  # *  read next frame

                logging.debug("(next) current frame {0}".format( self.FFmpegGlobalFrame))
                self.FFmpegTimerOut()
                logging.debug("(next) new frame {0}".format( self.FFmpegGlobalFrame))
                return


        if self.playerType == VLC:
            #  jump backward
            if ek == Qt.Key_Down:
                logging.debug('jump backward')
                self.jumpBackward_activated()
                return

            # jump forward
            if ek == Qt.Key_Up:
                logging.debug('jump forward')
                self.jumpForward_activated()
                return

            # next media file (page up)
            if ek == Qt.Key_PageUp:
                logging.debug('next media file')
                self.next_media_file()

            # previous media file (page down)
            if ek == Qt.Key_PageDown:
                logging.debug('previous media file')
                self.previous_media_file()


        if not self.pj[ETHOGRAM]:
            QMessageBox.warning(self, programName, 'Behaviours are not configured')
            return

        obs_key = None

        # check if key is function key
        if (ek in function_keys):
            if function_keys[ek] in [self.pj[ETHOGRAM][x]['key'] for x in self.pj[ETHOGRAM]]:
                obs_key = function_keys[ek]

        # get video time


        if self.pj[OBSERVATIONS][self.observationId][TYPE] in [LIVE] and "scan_sampling_time" in self.pj[OBSERVATIONS][self.observationId] and self.pj[OBSERVATIONS][self.observationId]["scan_sampling_time"]:
            if self.timeFormat == HHMMSS:
                memLaps = Decimal(int(time2seconds(self.lbTimeLive.text())))
            if self.timeFormat == S:
                memLaps = Decimal(int(Decimal(self.lbTimeLive.text())))

        else:
            memLaps = self.getLaps()

        if memLaps == None:
            return

        if (ek in function_keys) or ((ek in range(33, 256)) and (ek not in [Qt.Key_Plus, Qt.Key_Minus])):

            obs_idx, subj_idx  = -1, -1
            count = 0

            if (ek in function_keys):
                ek_unichr = function_keys[ek]
            else:
                ek_unichr = chr(ek)

            # count key occurence in ethogram
            for o in self.pj[ETHOGRAM]:
                if self.pj[ETHOGRAM][o]["key"] == ek_unichr:
                    obs_idx = o
                    count += 1

            # check if key defines a suject
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

                    response = dialog.MessageDialog(programName, "The focal subject is not defined. Do you want to continue?\nUse Preferences menu option to modify this behaviour.", [YES, NO])

                    if self.pj[OBSERVATIONS][self.observationId][TYPE] in [MEDIA] and flagPlayerPlaying:
                        self.play_video()

                    if response == NO:
                        return

                event = self.full_event(obs_idx)

                self.writeEvent( event, memLaps)

            elif count == 0:

                # check if key defines a suject
                flag_subject = False
                for idx in self.pj[SUBJECTS]:
                    if ek_unichr == self.pj[SUBJECTS][idx]['key']:
                        flag_subject = True

                        # select or deselect current subject
                        if self.currentSubject == self.pj[SUBJECTS][idx]['name']:
                            self.deselectSubject()
                        else:
                            self.selectSubject( self.pj[SUBJECTS][idx]['name'] )

                if not flag_subject:
                    self.statusbar.showMessage("Key not assigned ({})".format(ek_unichr), 5000)




    def twEvents_doubleClicked(self):
        """
        seek video to double clicked position ( add self.repositioningTimeOffset value)
        substract time offset if any
        """

        if self.twEvents.selectedIndexes():

            row = self.twEvents.selectedIndexes()[0].row()

            if ':' in self.twEvents.item(row, 0).text():
                time_ = time2seconds(  self.twEvents.item(row, 0).text()  )
            else:
                time_  = Decimal( self.twEvents.item(row, 0).text() )

            # substract time offset
            time_ -= self.pj[OBSERVATIONS][self.observationId][TIME_OFFSET]

            if time_ + self.repositioningTimeOffset >= 0:
                newTime = (time_ + self.repositioningTimeOffset ) * 1000
            else:
                newTime = 0


            if self.playMode == VLC:

                if len(self.duration) == 1:

                    self.mediaplayer.set_time( int(newTime) )

                    if self.simultaneousMedia:
                        # synchronize 2nd player
                        self.mediaplayer2.set_time( int(self.mediaplayer.get_time()  - self.pj[OBSERVATIONS][self.observationId][TIME_OFFSET_SECOND_PLAYER] * 1000) )

                else: # more media in player 1

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

                            '''while self.mediaListPlayer.get_state() != vlc.State.Playing and self.mediaListPlayer.get_state() != vlc.State.Ended:
                                pass'''

                            if flagPaused:
                                self.mediaListPlayer.pause()

                            self.mediaplayer.set_time( newTime -  sum(self.duration[0 : self.media_list.index_of_item(self.mediaplayer.get_media()) ]))
                            break

                        tot += d

                self.timer_out()
                self.timer_spectro_out()


            if self.playMode == FFMPEG:

                frameDuration = Decimal(1000 / list(self.fps.values())[0])

                currentFrame = round( newTime/ frameDuration )

                self.FFmpegGlobalFrame = currentFrame

                if self.FFmpegGlobalFrame > 0:
                    self.FFmpegGlobalFrame -= 1

                self.FFmpegTimerOut()



    def twSubjects_doubleClicked(self):
        '''
        select subject by double-click
        '''

        if self.observationId:
            if self.twSubjects.selectedIndexes():

                row = self.twSubjects.selectedIndexes()[0].row()

                # select or deselect current subject
                if self.currentSubject == self.twSubjects.item(row, 1).text():
                    self.deselectSubject()
                else:
                    self.selectSubject(self.twSubjects.item(row, 1).text())
        else:
            self.no_observation()


    def select_events_between_activated(self):
        '''
        select events between a time interval
        '''

        def parseTime(txt):
            '''
            parse time in string (should be 00:00:00.000 or in seconds)
            '''
            if ':' in txt:
                qtime = QTime.fromString(txt, "hh:mm:ss.zzz")    #timeRegExp(from_)

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
            text, ok = QInputDialog.getText(self, "Select events in time interval", "Interval: (example: 12.5-14.7 or 02:45.780-03:15.120 )", QLineEdit.Normal, "")

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
                self.twEvents.setSelectionMode( QAbstractItemView.MultiSelection )
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
        '''
        delete all events in current observation
        '''

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
        '''
        delete selected observations
        '''

        if not self.observationId:
            self.no_observation()
            return

        if not self.twEvents.selectedIndexes():
            QMessageBox.warning(self, programName, "No event selected!")
        else:
            # list of rows to delete (set for unique)
            rows = set([item.row() for item in self.twEvents.selectedIndexes()])
            self.pj[OBSERVATIONS][self.observationId][EVENTS] = [event for idx, event in enumerate(self.pj[OBSERVATIONS][self.observationId][EVENTS]) if not idx in rows]
            self.projectChanged = True
            self.loadEventsInTW( self.observationId )


    def edit_selected_events(self):
        '''
        edit selected events for subject or comment
        '''
        # list of rows to edit
        rowsToEdit = set([item.row() for item in self.twEvents.selectedIndexes()])

        if not len(rowsToEdit):
            QMessageBox.warning(self, programName, "No event selected!")
        elif len(rowsToEdit) == 1:  # 1 event selected
            self.edit_event()
        else:
            dialogWindow = dialog.EditSelectedEvents()
            dialogWindow.all_behaviors = [self.pj[ETHOGRAM][k]["code"].upper() for k in self.pj[ETHOGRAM]]
            dialogWindow.all_subjects = [self.pj[SUBJECTS][k]["name"].upper() for k in self.pj[SUBJECTS]]

            if dialogWindow.exec_():
                for idx, event in enumerate(self.pj[OBSERVATIONS][self.observationId][EVENTS]):
                    if idx in rowsToEdit:
                        if dialogWindow.rbSubject.isChecked():
                            event[SUBJECT_EVENT_FIELD] = dialogWindow.leText.text()
                        if dialogWindow.rbBehavior.isChecked():
                            event[BEHAVIOR_EVENT_FIELD] = dialogWindow.leText.text()
                        if dialogWindow.rbComment.isChecked():
                            event[COMMENT_EVENT_FIELD] = dialogWindow.leText.text()
                        self.pj[OBSERVATIONS][self.observationId][EVENTS][idx] = event
                        self.projectChanged = True
                self.loadEventsInTW(self.observationId)


    def export_tabular_events(self, outputFormat):
        """
        export events from selected observations in various formats: ODS, TSV, XLS
        """

        def complete(l, max):
            """
            complete list with empty string until len = max
            """
            while len(l) < max:
                l.append("")
            return l

        # ask user observations to analyze
        result, selectedObservations = self.selectObservations(MULTIPLE)

        if not selectedObservations:
            return

        plot_parameters = self.choose_obs_subj_behav(selectedObservations, maxTime=0, flagShowIncludeModifiers=False, flagShowExcludeBehaviorsWoEvents=False)

        if not plot_parameters["selected subjects"] or not plot_parameters["selected behaviors"]:
            return

        includeMediaInfo = dialog.MessageDialog(programName, "Include media info?", [YES, NO])

        fd = QFileDialog(self)
        if len(selectedObservations) > 1:  # choose directory for exporting more observations
            exportDir = fd.getExistingDirectory(self, "Choose a directory to export events", os.path.expanduser("~"), options=fd.ShowDirsOnly)
            if not exportDir:
                return

        for obsId in selectedObservations:

            if len(selectedObservations) == 1:
                if outputFormat == "tsv":
                    defaultFilter = "Tab Separated Values (*.tsv);;All files (*)"
                if outputFormat == "ods":
                    defaultFilter = "Open Document Spreadsheet (*.ods);;All files (*)"
                if outputFormat == "xls":
                    defaultFilter = "Microsoft Excel (*.xls);;All files (*)"

                defaultName = obsId + "." + outputFormat

                fileName = fd.getSaveFileName(self, "Export events", defaultName, defaultFilter)
                if not fileName:
                    return
            else:
                fileName = exportDir + os.sep + safeFileName(obsId) + "." + outputFormat

            eventsWithStatus = self.update_events_start_stop2(self.pj[OBSERVATIONS][obsId][EVENTS])

            max_modifiers = 0
            for event in eventsWithStatus:
                for c in pj_events_fields:
                    if c == "modifier" and event[pj_obs_fields[c]]:
                        max_modifiers = max(max_modifiers, len(event[pj_obs_fields[c]].split('|')))

            # media file number
            mediaNb = 0
            if self.pj[OBSERVATIONS][obsId]["type"] in [MEDIA]:
                for idx in self.pj[OBSERVATIONS][obsId][FILE]:
                    for media in self.pj[OBSERVATIONS][obsId][FILE][idx]:
                        mediaNb += 1

            rows = []

            # observation id
            rows.append(["Observation id", obsId])
            rows.append([""])

            # media file name
            if self.pj[OBSERVATIONS][obsId]["type"] in [MEDIA]:
                rows.append(["Media file(s)"])
            else:
                rows.append(["Live observation"])
            rows.append([""])

            if self.pj[OBSERVATIONS][obsId][TYPE] in [MEDIA]:

                for idx in self.pj[OBSERVATIONS][obsId][FILE]:
                    for media in self.pj[OBSERVATIONS][obsId][FILE][idx]:
                        rows.append(["Player #{0}".format(idx), media])
            rows.append([""])

            # date
            if "date" in self.pj[OBSERVATIONS][obsId]:
                rows.append(["Observation date", self.pj[OBSERVATIONS][obsId]["date"].replace('T', ' ')])
            rows.append([""])

            # description
            if "description" in self.pj[OBSERVATIONS][obsId]:
                rows.append(["Description", eol2space(self.pj[OBSERVATIONS][obsId]["description"])])
            rows.append([""])

            # time offset
            if "time offset" in self.pj[OBSERVATIONS][obsId]:
                rows.append(["Time offset (s)", self.pj[OBSERVATIONS][obsId]["time offset"]])
            rows.append([""])

            # independant variables
            if "independent_variables" in self.pj[OBSERVATIONS][obsId]:
                rows.append(["independent variables"])

                rows.append(["variable", "value"])

                for variable in self.pj[OBSERVATIONS][obsId]["independent_variables"]:
                    rows.append(  [ variable, self.pj[OBSERVATIONS][obsId]["independent_variables"][variable] ])

            rows.append([""])

            # write table header
            col = 0
            header = ["Time"]
            if includeMediaInfo == YES:
                header.extend(["Media file path", "Media total length", "FPS"])

            header.extend(["Subject", "Behavior"])
            for x in range(1, max_modifiers + 1):
                header.append("Modifier {}".format(x))
            header.extend(["Comment", "Status"])

            '''
            for c in pj_events_fields:
                if c == "modifier":
                    for x in range(1, max_modifiers + 1):
                        header.append("Modifier {}".format(x))
                else:
                    header.append(c)


            header.append("status")
            '''
            rows.append(header)

            duration1 = []   # in seconds
            for mediaFile in self.pj[OBSERVATIONS][obsId][FILE][PLAYER1]:
                duration1.append(self.pj[OBSERVATIONS][obsId]["media_info"]["length"][mediaFile])

            for event in eventsWithStatus:

                if ((event[SUBJECT_EVENT_FIELD] in plot_parameters["selected subjects"]) \
                   or (event[SUBJECT_EVENT_FIELD] == "" and NO_FOCAL_SUBJECT in plot_parameters["selected subjects"])) \
                   and (event[BEHAVIOR_EVENT_FIELD] in plot_parameters["selected behaviors"]):

                    fields = []
                    fields.append(float(event[EVENT_TIME_FIELD_IDX]))

                    if includeMediaInfo == YES:
                        mediaFileIdx = [idx1 for idx1, x in enumerate(duration1) if event[EVENT_TIME_FIELD_IDX] >= sum(duration1[0:idx1])][-1]
                        fields.append(self.pj[OBSERVATIONS][obsId][FILE][PLAYER1][mediaFileIdx])
                        # media total length
                        fields.append(str(sum(duration1)))
                        # fps
                        fields.append(self.pj[OBSERVATIONS][obsId]["media_info"]["fps"][self.pj[OBSERVATIONS][obsId][FILE][PLAYER1][mediaFileIdx]])

                    fields.append(event[EVENT_SUBJECT_FIELD_IDX])
                    fields.append(event[EVENT_BEHAVIOR_FIELD_IDX])
                    fields.append(event[COMMENT_EVENT_FIELD_IDX].replace(os.linesep, " "))
                    # status
                    fields.append(event[-1])

                    '''
                    for c in pj_events_fields:

                        if c == "modifier":
                            if event[pj_obs_fields[c]]:
                                modifiers = event[pj_obs_fields[c]].split("|")
                                while len(modifiers) < max_modifiers:
                                    modifiers.append("")

                                for m in modifiers:
                                    fields.append(m)
                            else:
                                for dummy in range(max_modifiers):
                                    fields.append("")

                        elif c == 'time':
                            fields.append(float(event[pj_obs_fields[c]]))

                        elif c == 'comment':
                            fields.append(event[pj_obs_fields[c]].replace(os.linesep, ' '))

                        else:
                            fields.append(event[pj_obs_fields[c]])


                    # append status START/STOP
                    fields.append( event[-1] )
                    '''
                    rows.append( fields )

            maxLen = max( [len(r) for r in rows])
            data = tablib.Dataset()
            data.title = obsId

            for row in rows:
                data.append( complete(row, maxLen))

            try:
                if outputFormat == "tsv":
                    with open(fileName, "w") as f:
                        f.write(data.tsv)
                if outputFormat == "ods":
                    with open(fileName, "wb") as f:
                        f.write(data.ods)
                if outputFormat == "xls":
                    with open(fileName, "wb") as f:
                        f.write(data.xls)
            except:
                errorMsg = sys.exc_info()[1].strerror
                logging.critical(errorMsg)
                QMessageBox.critical(None, programName, errorMsg, QMessageBox.Ok | QMessageBox.Default, QMessageBox.NoButton)

            del data

        self.statusbar.showMessage("Events exported", 0)




    def export_string_events(self):
        """
        export events from selected observations by subject in string format to plain text file
        behaviors are separated by character specified in self.behaviouralStringsSeparator (usually pipe |)
        for use with BSA (see http://penelope.unito.it/bsa)
        """

        def replace_spaces(l):
            return [x.replace(" ", "_") for x in l]

        # ask user observations to analyze
        result, selectedObservations = self.selectObservations(MULTIPLE)

        if not selectedObservations:
            return

        '''selectedSubjects, selectedBehaviors, _, _, _ = self.choose_obs_subj_behav(selectedObservations, maxTime=0,
                                                                                  flagShowIncludeModifiers=False,
                                                                                  flagShowExcludeBehaviorsWoEvents=False)

        if not selectedSubjects or not selectedBehaviors:
            return'''

        plot_parameters = self.choose_obs_subj_behav(selectedObservations, maxTime=0, flagShowIncludeModifiers=False, flagShowExcludeBehaviorsWoEvents=False)

        if not plot_parameters["selected subjects"] or not plot_parameters["selected behaviors"]:
            return


        fileName = QFileDialog(self).getSaveFileName(self, "Export events as strings", "", "Events file (*.txt *.tsv);;All files (*)")

        #cursor = self.loadEventsInDB(selectedSubjects, selectedObservations, selectedBehaviors)

        if fileName:
            try:
                with open(fileName, "w") as outFile:
                    for obsId in selectedObservations:
                        # observation id
                        outFile.write("# observation id: {0}{1}".format(obsId, os.linesep) )
                        # observation descrition
                        outFile.write("# observation description: {0}{1}".format(self.pj[OBSERVATIONS][obsId]["description"].replace(os.linesep, " "), os.linesep))
                        # media file name
                        if self.pj[OBSERVATIONS][obsId][TYPE] in [MEDIA]:
                            outFile.write("# Media file name: {0}{1}{1}".format(", ".join([os.path.basename(x) for x in self.pj[OBSERVATIONS][obsId][FILE][PLAYER1]]), os.linesep))
                        if self.pj[OBSERVATIONS][obsId][TYPE] in [LIVE]:
                            outFile.write("# Live observation{0}{0}".format(os.linesep))

                    for subj in plot_parameters["selected subjects"]:
                        if subj:
                            subj_str = "{0}{1}:{0}".format(os.linesep, subj)
                        else:
                            subj_str = "{0}No focal subject:{0}".format(os.linesep)
                        outFile.write(subj_str)


                        for obsId in selectedObservations:
                            s = ""

                            currentStates = []

                            eventsWithStatus = self.update_events_start_stop2(self.pj[OBSERVATIONS][obsId][EVENTS])

                            for event in eventsWithStatus:

                                if event[EVENT_SUBJECT_FIELD_IDX] == subj or (subj == NO_FOCAL_SUBJECT and event[EVENT_SUBJECT_FIELD_IDX] == ""):

                                    if event[-1] == POINT:
                                        if currentStates:
                                            s += "+".join(replace_spaces(currentStates)) + "+" + event[EVENT_BEHAVIOR_FIELD_IDX].replace(" ", "_")
                                        else:
                                            s += event[EVENT_BEHAVIOR_FIELD_IDX].replace(" ", "_")
                                        s += self.behaviouralStringsSeparator

                                    if event[-1] == "START":
                                        currentStates.append(event[EVENT_BEHAVIOR_FIELD_IDX])
                                        s += "+".join(replace_spaces(currentStates)) + self.behaviouralStringsSeparator

                                    if event[-1] == "STOP":
                                        if event[EVENT_BEHAVIOR_FIELD_IDX] in currentStates:
                                            currentStates.remove( event[EVENT_BEHAVIOR_FIELD_IDX])
                                        if currentStates:
                                            s += "+".join(replace_spaces(currentStates)) + self.behaviouralStringsSeparator


                            '''
                            for event in self.pj[OBSERVATIONS][obsId][EVENTS]:

                                if event[ pj_obs_fields["subject"]] == subj or (subj == NO_FOCAL_SUBJECT and event[pj_obs_fields["subject"]] == ""):
                                    s += event[pj_obs_fields["code"]].replace(" ", "_") + self.behaviouralStringsSeparator
                            '''

                            # remove last separator (if separator not empty)
                            if self.behaviouralStringsSeparator:
                                s = s[0 : -len(self.behaviouralStringsSeparator)]
                            if s:
                                outFile.write(s + os.linesep)
            except:
                errorMsg = sys.exc_info()[1].strerror
                logging.critical(errorMsg)
                QMessageBox.critical(None, programName, errorMsg, QMessageBox.Ok | QMessageBox.Default, QMessageBox.NoButton)


    def closeEvent(self, event):
        """
        check if current project is saved and close program
        """
        if self.projectChanged:
            response = dialog.MessageDialog(programName, "What to do about the current unsaved project?", ['Save', 'Discard', CANCEL])

            if response == "Save":
                if self.save_project_activated() == "not saved":
                    event.ignore()

            if response == CANCEL:
                event.ignore()

        self.saveConfigFile()

        try:
            self.spectro.close()
        except:
            pass

    def actionQuit_activated(self):
        self.close()



    def import_observations(self):
        """
        import events from file
        """

        logging.debug("""Function "import observation" not yet implemented""")
        QMessageBox.warning(None, programName, """Function "import observation" not yet implemented""",
            QMessageBox.Ok | QMessageBox.Default, QMessageBox.NoButton)

        self.statusbar.showMessage("Function not yet implemented", 5000)



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
        do not pause media if already paused (otherwise media will be played)
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

                    logging.debug("pause_video: player #1 state: {0}".format(self.mediaListPlayer.get_state()))
                    # second video together
                    if self.simultaneousMedia:
                        self.mediaListPlayer2.pause()
                        logging.debug('pause_video: player #2 state {0}'.format(  self.mediaListPlayer2.get_state()))

                    # wait until video is paused or ended
                    while True:
                        if self.mediaListPlayer.get_state() in [vlc.State.Paused, vlc.State.Ended]:
                            break


                    '''while self.mediaListPlayer.get_state() != vlc.State.Paused and self.mediaListPlayer.get_state() != vlc.State.Ended:
                        pass'''

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
                if int((currentTime - self.fast ) * list(self.fps.values())[0]) > 0:
                    self.FFmpegGlobalFrame = int((currentTime - self.fast ) * list(self.fps.values())[0])
                else:
                    self.FFmpegGlobalFrame = 0   # position to init
                self.FFmpegTimerOut()
            else:
                if self.media_list.count() == 1:
                    if self.mediaplayer.get_time() >= self.fast * 1000:
                        self.mediaplayer.set_time( self.mediaplayer.get_time() - self.fast * 1000 )
                    else:
                        self.mediaplayer.set_time( 0 )
                    if self.simultaneousMedia:
                        self.mediaplayer2.set_time( int(self.mediaplayer.get_time()  - self.pj[OBSERVATIONS][self.observationId][TIME_OFFSET_SECOND_PLAYER] * 1000) )



                elif self.media_list.count() > 1:

                    newTime = (sum(self.duration[0 : self.media_list.index_of_item(self.mediaplayer.get_media()) ]) + self.mediaplayer.get_time()) - self.fast * 1000
                    if newTime < self.fast * 1000:
                        newTime = 0

                    logging.debug( 'newTime: {0}'.format(newTime))
                    logging.debug( 'sum self.duration: {0}'.format(sum(self.duration)))

                    # remember if player paused (go previous will start playing)
                    flagPaused = self.mediaListPlayer.get_state() == vlc.State.Paused

                    logging.debug('flagPaused: {0}'.format(flagPaused))

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

                            self.mediaplayer.set_time( newTime -  sum(self.duration[0 : self.media_list.index_of_item(self.mediaplayer.get_media()) ]))

                            break
                        tot += d

                else:
                    self.no_media()

                self.timer_out()
                self.timer_spectro_out()

                # no subtitles
                #self.mediaplayer.video_set_spu(0)


    def jumpForward_activated(self):
        '''
        forward from current position
        '''
        logging.debug('jump forward activated')
        logging.debug('play mode {0}'.format(self.playMode ))

        if self.playerType == VLC:

            if self.playMode == FFMPEG:

                currentTime = self.FFmpegGlobalFrame / list(self.fps.values())[0]
                self.FFmpegGlobalFrame =  int((currentTime + self.fast )  * list(self.fps.values())[0])
                self.FFmpegTimerOut()

            else:

                if self.media_list.count() == 1:
                    if self.mediaplayer.get_time() >= self.mediaplayer.get_length() - self.fast * 1000:
                        self.mediaplayer.set_time(self.mediaplayer.get_length())
                    else:
                        self.mediaplayer.set_time( self.mediaplayer.get_time() + self.fast * 1000 )

                    if self.simultaneousMedia:
                        self.mediaplayer2.set_time( int(self.mediaplayer.get_time()  - self.pj[OBSERVATIONS][self.observationId][TIME_OFFSET_SECOND_PLAYER] * 1000) )

                elif self.media_list.count() > 1:

                    logging.debug('self.fast: {0}'.format(self.fast))

                    newTime = (sum(self.duration[0 : self.media_list.index_of_item(self.mediaplayer.get_media()) ]) + self.mediaplayer.get_time()) + self.fast * 1000

                    if newTime < sum(self.duration):

                        # remember if player paused (go previous will start playing)
                        flagPaused = self.mediaListPlayer.get_state() == vlc.State.Paused

                        logging.debug('flagPaused {0}'.format( flagPaused))

                        tot = 0
                        for idx, d in enumerate(self.duration):
                            if newTime >= tot and newTime < tot+d:
                                self.mediaListPlayer.play_item_at_index(idx)
                                app.processEvents()

                                # wait until media is played
                                while True:
                                    if self.mediaListPlayer.get_state() in [vlc.State.Playing, vlc.State.Ended]:
                                        break

                                if flagPaused:
                                    self.mediaListPlayer.pause()

                                self.mediaplayer.set_time( newTime -  sum(self.duration[0 : self.media_list.index_of_item(self.mediaplayer.get_media()) ]))

                                break
                            tot += d

                else:
                    self.no_media()

                self.timer_out()
                self.timer_spectro_out()

                # no subtitles
                '''
                logging.debug('no subtitle')
                self.mediaplayer.video_set_spu(0)
                logging.debug('no subtitle done')
                '''


    def reset_activated(self):
        '''
        reset video to beginning
        '''
        logging.debug('Reset activated')

        if self.playerType == VLC:

            self.pause_video()
            if self.playMode == FFMPEG:

                self.FFmpegGlobalFrame = 0   # position to init
                self.FFmpegTimerOut()

            else: #playmode VLC

                self.mediaplayer.set_time(0)

                # second video together
                if self.simultaneousMedia:
                    self.mediaplayer2.set_time(0)

                self.timer_out()
                self.timer_spectro_out()



if __name__=="__main__":

    # check if argument
    from optparse import OptionParser
    usage = "usage: %prog [options]"
    parser = OptionParser(usage=usage)

    parser.add_option("-d", "--debug", action = "store_true", default = False, dest = "debug", help = "Verbose mode for debugging")
    parser.add_option("-v", "--version", action = "store_true", default = False, dest = "version", help = "Print version")
    parser.add_option("-n", "--nosplashscreen", action = "store_true", default = False, help = "No splash screen")

    (options, args) = parser.parse_args()

    if options.version:
        print("version: {0}".format(__version__))
        sys.exit(0)

    app = QApplication(sys.argv)

    # splashscreen

    if not options.nosplashscreen:
        start = time.time()
        splash = QSplashScreen(QPixmap( os.path.dirname(os.path.realpath(__file__)) + "/splash.png"))
        splash.show()
        splash.raise_()
        while time.time() - start < 1:
            time.sleep(0.001)
            app.processEvents()

    if options.debug:
        logging.basicConfig(level=logging.DEBUG)
    else:
        logging.basicConfig(level=logging.INFO)

    availablePlayers = []

    # load VLC
    import vlc
    if vlc.dll is None:
        logging.critical("VLC media player not found")
        QMessageBox.critical(None, programName, "This program requires the VLC media player.<br>Go to http://www.videolan.org/vlc",
             QMessageBox.Ok | QMessageBox.Default, QMessageBox.NoButton)
        sys.exit(1)

    availablePlayers.append(VLC)

    logging.info("VLC version {}".format(vlc.libvlc_get_version().decode("utf-8")))
    if vlc.libvlc_get_version().decode("utf-8") < VLC_MIN_VERSION:
        QMessageBox.critical(None, programName, "The VLC media player seems very old ({}).<br>Go to http://www.videolan.org/vlc to update it".format(
            vlc.libvlc_get_version()), QMessageBox.Ok | QMessageBox.Default, QMessageBox.NoButton)

        logging.critical("The VLC media player seems old ({}). Go to http://www.videolan.org/vlc to update it".format(vlc.libvlc_get_version()))
        sys.exit(2)

    # check FFmpeg
    ffmpeg_bin = check_ffmpeg_path()
    if not ffmpeg_bin:
        sys.exit(3)

    app.setApplicationName(programName)
    window = MainWindow(availablePlayers, ffmpeg_bin)

    if args:
        logging.debug("args[0]: " + os.path.abspath(args[0]))
        window.open_project_json(os.path.abspath(args[0]))

    window.show()
    window.raise_()
    if not options.nosplashscreen:
        splash.finish(window)

    sys.exit(app.exec_())
