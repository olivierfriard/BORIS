#!/usr/bin/env python3


"""
BORIS
Behavioral Observation Research Interactive Software
Copyright 2012-2015 Olivier Friard

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


# TODO: media offset in plot event function


__version__ = '2.6'
__version_date__ = '2015-10-08'
__DEV__ = False


import sys
import logging
import platform

if int(platform.python_version_tuple()[0]) < 3:
    logging.critical('BORIS requires Python 3!')
    sys.exit()

try:
    from PyQt4.QtCore import *
    from PyQt4.QtGui import *
except:
    logging.critical('PyQt4 not installed!')
    sys.exit()

import qrc_boris

from config import *

video, live = 0, 1
script_out = ''
script_fps = -2

import time
import os
from encodings import hex_codec
import json
from decimal import *
import re
import hashlib
import subprocess
import sqlite3
import urllib.parse
import urllib.request
import urllib.error
import urllib.parse
import PyQt4.QtNetwork
import PyQt4.QtWebKit
import tempfile
import glob

import subprocess

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


def bytes_to_str(b):
    '''
    Translate bytes to string.
    '''
    if isinstance(b, bytes):

        fileSystemEncoding = sys.getfilesystemencoding()

        # hack for PyInstaller
        if fileSystemEncoding == None:
            fileSystemEncoding = 'UTF-8'

        return b.decode( fileSystemEncoding )
    else:
        return b


from time_budget_widget import *

from diagram_widget import *

import select_modifiers



class TempDirCleanerThread(QThread):
        def __init__(self, parent = None):
            QThread.__init__(self, parent)
            self.exiting = False
            self.tempdir = ''
            self.ffmpeg_cache_dir_max_size = 0

        def run(self):
            while self.exiting==False:

                if sum(os.path.getsize(self.tempdir+f) for f in os.listdir(self.tempdir) if 'BORIS_' in f and os.path.isfile(self.tempdir + f)) > self.ffmpeg_cache_dir_max_size:

                    fl = sorted((os.path.getctime(self.tempdir+f),self.tempdir+f) for f in os.listdir(self.tempdir) if 'BORIS_' in f and os.path.isfile(self.tempdir + f))

                    for ts,f in fl[0:int(len(fl)/10)]:
                        os.remove(f)

                time.sleep(30)


class checkingBox_list(QDialog):
    '''
    class for selecting iems from a ListWidget
    '''

    def __init__(self):
        super(checkingBox_list, self).__init__()

        self.label = QLabel()
        self.label.setText('Available observations')

        self.lw = QListWidget()
        self.lw.doubleClicked.connect(self.pbOK_clicked)

        hbox = QVBoxLayout(self)

        hbox.addWidget(self.label)
        hbox.addWidget(self.lw)

        self.pbSelectAll = QPushButton('Select all')
        self.pbSelectAll.clicked.connect(self.pbSelectAll_clicked)

        self.pbUnSelectAll = QPushButton('Unselect all')
        self.pbUnSelectAll.clicked.connect(self.pbUnSelectAll_clicked)

        self.pbOK = QPushButton('OK')
        self.pbOK.clicked.connect(self.pbOK_clicked)

        self.pbCancel = QPushButton('Cancel')
        self.pbCancel.clicked.connect(self.pbCancel_clicked)

        hbox2 = QHBoxLayout(self)

        hbox2.addWidget(self.pbSelectAll)
        hbox2.addWidget(self.pbUnSelectAll)
        hbox2.addWidget(self.pbCancel)
        hbox2.addWidget(self.pbOK)

        hbox.addLayout(hbox2)

        self.setLayout(hbox)

        self.setWindowTitle('')

    def pbSelectAll_clicked(self):
        '''check all items'''
        for idx in range(self.lw.count()):
            self.lw.itemWidget(self.lw.item(idx)).setChecked(True)

    def pbUnSelectAll_clicked(self):
        '''uncheck all items'''
        for idx in range(self.lw.count()):
            self.lw.itemWidget(self.lw.item(idx)).setChecked(False)


    def pbOK_clicked(self):
        self.accept()

    def pbCancel_clicked(self):
        self.reject()


class JumpTo(QDialog):

    def __init__(self, timeFormat):
        super(JumpTo, self).__init__()

        hbox = QVBoxLayout(self)

        self.label = QLabel()
        self.label.setText('Go to time')
        hbox.addWidget(self.label)

        if timeFormat == 'hh:mm:ss':
            self.te = QTimeEdit()
            self.te.setDisplayFormat('hh:mm:ss.zzz')
        else:
            self.te = QDoubleSpinBox()
            self.te.setMinimum(0)
            self.te.setMaximum(86400)
            self.te.setDecimals(3)

        hbox.addWidget(self.te)

        self.pbOK = QPushButton('OK')
        self.pbOK.clicked.connect(self.pbOK_clicked)
        self.pbCancel = QPushButton('Cancel')
        self.pbCancel.clicked.connect(self.pbCancel_clicked)

        hbox2 = QHBoxLayout(self)

        hbox2.addWidget(self.pbCancel)
        hbox2.addWidget(self.pbOK)

        hbox.addLayout(hbox2)

        self.setLayout(hbox)

        self.setWindowTitle('Jump to spefific time')

    def pbOK_clicked(self):
        self.accept()

    def pbCancel_clicked(self):
        self.reject()

ROW = -1

class StyledItemDelegateTriangle(QtGui.QStyledItemDelegate):
    '''
    painter for twEvents with current time highlighting
    '''
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


    pj = {"time_format": HHMMSS, "project_date": "", "project_name": "", "project_description": "", SUBJECTS : {}, "behaviors_conf": {}, OBSERVATIONS: {} , 'coding_map':{} }
    project = False

    observationId = ''   # current observation id

    timeOffset = 0.0

    confirmSound = False          # if True each keypress will be confirmed by a beep
    embedPlayer = True            # if True the VLC player will be embedded in the main window
    alertNoFocalSubject = False   # if True an alert will show up if no focal subject
    trackingCursorAboveEvent = False

    timeFormat = HHMMSS       # 's' or 'hh:mm:ss'
    repositioningTimeOffset = 0

    #ObservationsChanged = False
    projectChanged = False

    liveObservationStarted = False

    projectFileName = ''
    mediaTotalLength = None

    automaticBackup = 0

    saveMediaFilePath = True

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

    imageDirectory = ''

    # FFmpeg
    allowFrameByFrame = False

    # path for ffmpeg/ffmpeg.exe program
    ffmpeg_bin = ''
    ffmpeg_cache_dir = ''
    ffmpeg_cache_dir_max_size = 0

    # dictionary for FPS storing
    fps = {}

    playerType = ''
    playMode = VLC

    cleaningThread = TempDirCleanerThread()


    def __init__(self, availablePlayers , parent = None):

        super(MainWindow, self).__init__(parent)
        self.setupUi(self)

        self.availablePlayers = availablePlayers
        '''self.installEventFilter(self)'''
        # set icons
        self.setWindowIcon(QIcon(':/logo.png'))
        self.actionPlay.setIcon(QIcon(':/play.png'))
        self.actionPause.setIcon(QIcon(':/pause.png'))
        self.actionReset.setIcon(QIcon(':/reset.png'))
        self.actionJumpBackward.setIcon(QIcon(':/jump_backward.png'))
        self.actionJumpForward.setIcon(QIcon(':/jump_forward.png'))

        self.actionFaster.setIcon(QIcon(':/faster.png'))
        self.actionSlower.setIcon(QIcon(':/slower.png'))
        self.actionNormalSpeed.setIcon(QIcon(':/normal_speed.png'))

        self.actionPrevious.setIcon(QIcon(':/previous.png'))
        self.actionNext.setIcon(QIcon(':/next.png'))

        self.actionSnapshot.setIcon(QIcon(':/snapshot.png'))
        self.actionFrame_by_frame.setIcon(QIcon(':/frame_mode'))

        self.setWindowTitle('%s (%s)' % (programName, __version__))

        try:
            datadir = sys._MEIPASS
        except Exception:
            datadir = os.path.dirname(os.path.realpath(__file__))

        self.lbLogoBoris.setPixmap(QPixmap( datadir + "/logo_boris_500px.png"))
        self.lbLogoBoris.setScaledContents(False)
        self.lbLogoBoris.setAlignment(Qt.AlignCenter)


        self.lbLogoUnito.setPixmap(QPixmap( datadir + "/dbios_unito.png"))
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
        '''
        create tab with widget for live observation
        '''

        self.liveLayout = QtGui.QGridLayout()
        self.textButton = QPushButton('Start live observation')
        self.textButton.clicked.connect(self.start_live_observation)
        self.liveLayout.addWidget(self.textButton)


        self.lbTimeLive = QLabel()
        self.lbTimeLive.setAlignment(Qt.AlignCenter)

        font = QFont('Monospace')
        font.setPointSize(48)
        self.lbTimeLive.setFont(font)
        self.lbTimeLive.setText('00:00:00.000')

        self.liveLayout.addWidget(self.lbTimeLive)

        self.liveTab = QtGui.QWidget()
        self.liveTab.setLayout(self.liveLayout)

        self.toolBox.insertItem(2, self.liveTab, 'Live')


    def menu_options(self):
        '''
        enable/disable menu option
        '''

        title = ''
        if self.observationId:
            title = self.observationId + ' - '
        if self.pj['project_name']:
            title += self.pj['project_name'] + ' - '

        title += programName

        self.setWindowTitle( title )

        flag = self.project

        # project menu
        self.actionEdit_project.setEnabled(flag)
        self.actionSave_project.setEnabled(flag)
        self.actionSave_project_as.setEnabled(flag)
        self.actionClose_project.setEnabled(flag)

        # observations

        # enabled if project
        self.actionNew_observation.setEnabled(flag)

        self.actionOpen_observation.setEnabled( self.pj[OBSERVATIONS] != {})
        self.actionObservationsList.setEnabled( self.pj[OBSERVATIONS] != {})


        # enabled if observation
        flagObs = self.observationId != ''

        self.actionAdd_event.setEnabled(flagObs)
        self.actionClose_observation.setEnabled(flagObs)
        self.actionLoad_observations_file.setEnabled(flagObs)

        self.menuExport_events.setEnabled(flag)
        self.menuExport_aggregated_events.setEnabled(flag)
        self.actionExportEventString.setEnabled(flag)

        self.actionDelete_all_observations.setEnabled(flagObs)
        self.actionSelect_observations.setEnabled(flagObs)
        self.actionDelete_selected_observations.setEnabled(flagObs)
        self.actionEdit_event.setEnabled(flagObs)
        self.actionMedia_file_information.setEnabled(flagObs)
        self.actionMedia_file_information.setEnabled(self.playerType == VLC)
        self.menuCreate_subtitles_2.setEnabled(flagObs)

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
        self.actionNext.setEnabled( self.playerType == VLC)
        self.actionSnapshot.setEnabled( self.playerType == VLC)

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

        self.actionSelect_observations.triggered.connect(self.select_events_between_activated)

        self.actionDelete_all_observations.triggered.connect(self.delete_all_events)
        self.actionDelete_selected_observations.triggered.connect(self.delete_selected_events)


        self.actionLoad_observations_file.triggered.connect(self.import_observations)

        self.actionExportEventTabular_TSV.triggered.connect(lambda: self.export_tabular_events('tsv'))
        self.actionExportEventTabular_ODS.triggered.connect(lambda: self.export_tabular_events('ods'))
        self.actionExportEventTabular_XLS.triggered.connect(lambda: self.export_tabular_events('xls'))

        self.actionExportEventString.triggered.connect(self.export_string_events)

        self.actionExportEventsSQL.triggered.connect(lambda: self.export_aggregated_events('sql'))
        self.actionAggregatedEventsTabularFormat.triggered.connect(lambda: self.export_aggregated_events('tab'))

        # menu playback
        self.actionJumpTo.triggered.connect(self.jump_to)

        # menu Tools
        self.actionMapCreator.triggered.connect(self.map_creator)

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

        # table Widget double click
        self.twEvents.itemDoubleClicked.connect(self.twEvents_doubleClicked)
        self.twConfiguration.itemDoubleClicked.connect(self.twEthogram_doubleClicked)
        self.twSubjects.itemDoubleClicked.connect(self.twSubjects_doubleClicked)

        # Actions for twEvents context menu
        self.twEvents.setContextMenuPolicy(Qt.ActionsContextMenu)

        self.twEvents.addAction(self.actionEdit_event)
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

        # timer for timing the live observation
        self.liveTimer = QTimer(self)
        self.liveTimer.timeout.connect(self.liveTimer_out)

        self.readConfigFile()

        # timer for automatic backup
        self.automaticBackupTimer = QTimer(self)
        self.automaticBackupTimer.timeout.connect(self.automatic_backup)
        if self.automaticBackup:
            self.automaticBackupTimer.start( self.automaticBackup * 60000 )

    def map_creator(self):
        '''
        show map creator window and hide program main window
        '''
        self.mapCreatorWindow = map_creator.MapCreatorWindow()
        self.mapCreatorWindow.move(self.pos())
        self.mapCreatorWindow.resize(640, 640)
        self.mapCreatorWindow.closed.connect(self.show)
        self.mapCreatorWindow.show()
        self.hide()


    def open_observation(self):
        '''
        open an observation
        '''

        # check if current observation must be closed to open a new one
        if self.observationId:
            response = dialog.MessageDialog(programName, 'The current observation will be closed. Do you want to continue?', [YES, NO])
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
                    self.observationId = ''
                    self.twEvents.setRowCount(0)
                    self.menu_options()

            self.menu_options()
            # title of dock widget
            self.dwObservations.setWindowTitle('Events for ' + self.observationId)


    def edit_observation(self):
        # check if current observation must be closed to open a new one
        if self.observationId:
            response = dialog.MessageDialog(programName, 'The current observation will be closed. Do you want to continue?', [YES, NO])
            if response == NO:
                return
            else:
                self.close_observation()

        result, selectedObs = self.selectObservations( EDIT )

        if selectedObs:
            self.new_observation( mode=EDIT, obsId=selectedObs[0])


    def observations_list(self):
        '''
        view all observations
        '''
        # check if an observation is running
        if self.observationId:
            QMessageBox.critical(self, programName , 'You must close the running observation before.' )
            return

        result, selectedObs = self.selectObservations( SINGLE )

        if selectedObs:

            if result == OPEN:

                self.observationId = selectedObs[0]

                # load events in table widget
                self.loadEventsInTW(self.observationId)

                if self.pj[OBSERVATIONS][self.observationId][ 'type' ] == LIVE:
                    self.playerType = LIVE
                    self.initialize_new_live_observation()

                if self.pj[OBSERVATIONS][self.observationId][ 'type' ] in [MEDIA]:

                    if not self.initialize_new_observation_vlc():
                        self.observationId = ''
                        self.twEvents.setRowCount(0)
                        self.menu_options()

                self.menu_options()
                # title of dock widget
                self.dwObservations.setWindowTitle('Events for ' + self.observationId)


            if result == EDIT:

                if self.observationId != selectedObs[0]:
                    self.new_observation( mode=EDIT, obsId=selectedObs[0])   # observation id to edit
                else:
                    QMessageBox.warning(self, programName , 'The observation <b>%s</b> is running!<br>Close it before editing.' % self.observationId)


    def actionCheckUpdate_activated(self):

        '''
        check BORIS web site for updates
        '''
        try:

            if __version__ == 'DEV':

                versionURL = 'http://penelope.unito.it/boris/static/ver_dev.dat'
                dev_date = urllib.request.urlopen( versionURL ).read().decode('utf-8').strip()
                if dev_date > __version_date__:
                    msg = 'A new development version is available.<br>Go to <a href="http://penelope.unito.it/boris">http://penelope.unito.it/boris</a> to install it.<br><br>Remember to report all bugs you will find! ;-)'
                else:
                    msg = 'You are using the last DEVELOPMENT version'

            else:
                versionURL = 'http://penelope.unito.it/boris/static/ver.dat'
                lastVersion = Decimal(urllib.request.urlopen( versionURL ).read().strip().decode('utf-8'))

                if lastVersion > Decimal(__version__):
                    msg = 'A new version is available: v. <b>%s</b><br>Go to <a href="http://penelope.unito.it/boris">http://penelope.unito.it/boris</a> to install it.' % str(lastVersion)
                else:
                    msg = 'The version you are using is the last one: <b>%s</b>' %  __version__

            QMessageBox.information(self, programName , msg)

        except:
            QMessageBox.warning(self, programName , 'Can not check for updates...')



    def jump_to(self):
        '''
        jump to the user specified media position
        '''

        jt = JumpTo(self.timeFormat)

        if jt.exec_():

            if self.timeFormat == HHMMSS:
                newTime = int(time2seconds(jt.te.time().toString('hh:mm:ss.zzz')) * 1000)
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
                        else:
                            QMessageBox.warning(self, programName , 'The indicated position is behind the end of media (%s)' % seconds2time(self.mediaplayer.get_length()/1000))

                    elif self.media_list.count() > 1:

                        if newTime  < sum(self.duration):

                            # remember if player paused (go previous will start playing)
                            flagPaused = self.mediaListPlayer.get_state() == vlc.State.Paused

                            tot = 0
                            for idx, d in enumerate(self.duration):
                                if newTime >= tot and newTime < tot+d:
                                    self.mediaListPlayer.play_item_at_index(idx)

                                    # wait until media is played
                                    while self.mediaListPlayer.get_state() != vlc.State.Playing:
                                        pass

                                    if flagPaused:
                                        self.mediaListPlayer.pause()

                                    #print( newTime -  sum(self.duration[0 : self.media_list.index_of_item(self.mediaplayer.get_media()) ])  )
                                    #print( type(newTime -  sum(self.duration[0 : self.media_list.index_of_item(self.mediaplayer.get_media()) ]) ) )
                                    self.mediaplayer.set_time( newTime -  sum(self.duration[0 : self.media_list.index_of_item(self.mediaplayer.get_media()) ]))

                                    break
                                tot += d
                        else:
                            QMessageBox.warning(self, programName , 'The indicated position is behind the total media duration (%s)' % seconds2time(sum(self.duration)/1000))

                    self.timer_out()


    def previous_media_file(self):
        '''
        go to previous media file (if any)
        '''
        if self.playerType == VLC:

            if self.playMode == FFMPEG:

                currentMedia = ''


                for idx,media in enumerate(self.pj[OBSERVATIONS][self.observationId][FILE][PLAYER1]):
                    if self.FFmpegGlobalFrame < self.duration[idx+1]:

                        self.FFmpegGlobalFrame = self.duration[idx-1 ]
                        break


                self.FFmpegGlobalFrame -= 1
                self.FFmpegTimerOut()

            else:

                # check if media not first media
                if self.media_list.index_of_item(self.mediaplayer.get_media()) > 0:

                    # remember if player paused (go previous will start playing)
                    flagPaused = self.mediaListPlayer.get_state() == vlc.State.Paused

                    self.mediaListPlayer.previous()

                    while self.mediaListPlayer.get_state() != vlc.State.Playing:
                        pass

                    if flagPaused:
                        self.mediaListPlayer.pause()
                else:

                    if self.media_list.count() == 1:
                        self.statusbar.showMessage('There is only one media file', 5000)
                    else:
                        if self.media_list.index_of_item(self.mediaplayer.get_media()) == 0:
                            self.statusbar.showMessage('The first media is playing', 5000)

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

                        self.FFmpegGlobalFrame = self.duration[idx + 1 ]
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
                    while self.mediaListPlayer.get_state() != vlc.State.Playing:
                        pass

                    if flagPaused:
                        logging.info('media player state: {0}'.format(self.mediaListPlayer.get_state()) )
                        self.mediaListPlayer.pause()

                else:
                    if self.media_list.count() == 1:
                        self.statusbar.showMessage('There is only one media file', 5000)
                    else:
                        if self.media_list.index_of_item(self.mediaplayer.get_media()) == self.media_list.count() - 1:
                            self.statusbar.showMessage('The last media is playing', 5000)

                # no subtitles
                #self.mediaplayer.video_set_spu(0)






    def setVolume(self):
        '''
        set volume for player #1
        '''

        self.mediaplayer.audio_set_volume( self.volumeslider.value() )

    def setVolume2(self):
        '''
        set volume for player #2
        '''

        self.mediaplayer2.audio_set_volume(self.volumeslider2.value() )


    def automatic_backup(self):
        '''
        save project every x minutes if current observation
        '''

        if self.observationId:
            logging.info('automatic backup')
            self.save_project_activated()


    def deselectSubject(self):
        '''
        deselect the current subject
        '''
        self.currentSubject = ''
        self.lbSubject.setText( '<b>%s</b>' % NO_FOCAL_SUBJECT )
        self.lbFocalSubject.setText( NO_FOCAL_SUBJECT )


    def selectSubject(self, subject):
        '''
        deselect the current subject
        '''
        self.currentSubject = subject
        self.lbSubject.setText( 'Subject: <b>%s</b>' % (self.currentSubject))
        self.lbFocalSubject.setText( ' Focal subject: <b>%s</b>' % (self.currentSubject) )


    def preferences(self):
        '''
        show preferences window
        '''

        preferencesWindow = preferences.Preferences()

        if self.timeFormat == S:
            preferencesWindow.cbTimeFormat.setCurrentIndex(0)

        if self.timeFormat == HHMMSS:
            preferencesWindow.cbTimeFormat.setCurrentIndex(1)

        preferencesWindow.sbffSpeed.setValue( self.fast )

        preferencesWindow.sbRepositionTimeOffset.setValue( self.repositioningTimeOffset )

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

        # FFmpeg for frame by frame mode
        preferencesWindow.pbBrowseFFmpeg.setEnabled( preferencesWindow.cbAllowFrameByFrameMode.isChecked() )
        preferencesWindow.lbFFmpeg.setEnabled( preferencesWindow.cbAllowFrameByFrameMode.isChecked() )
        preferencesWindow.leFFmpegPath.setEnabled( preferencesWindow.cbAllowFrameByFrameMode.isChecked() )

        preferencesWindow.pbBrowseFFmpegCacheDir.setEnabled( preferencesWindow.cbAllowFrameByFrameMode.isChecked() )
        preferencesWindow.lbFFmpegCacheDir.setEnabled( preferencesWindow.cbAllowFrameByFrameMode.isChecked() )
        preferencesWindow.leFFmpegCacheDir.setEnabled( preferencesWindow.cbAllowFrameByFrameMode.isChecked() )

        preferencesWindow.lbFFmpegCacheDirMaxSize.setEnabled( preferencesWindow.cbAllowFrameByFrameMode.isChecked() )
        preferencesWindow.sbFFmpegCacheDirMaxSize.setEnabled( preferencesWindow.cbAllowFrameByFrameMode.isChecked() )

        preferencesWindow.leFFmpegPath.setText( self.ffmpeg_bin )
        preferencesWindow.cbAllowFrameByFrameMode.setChecked( self.allowFrameByFrame )
        preferencesWindow.leFFmpegCacheDir.setText( self.ffmpeg_cache_dir )
        preferencesWindow.sbFFmpegCacheDirMaxSize.setValue( self.ffmpeg_cache_dir_max_size )

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

            self.trackingCursorAboveEvent= preferencesWindow.cbTrackingCursorAboveEvent.isChecked()

            if self.observationId:
                self.loadEventsInTW( self.observationId )
                self.display_timeoffset_statubar( self.pj[OBSERVATIONS][self.observationId][TIME_OFFSET] )

            self.allowFrameByFrame = preferencesWindow.cbAllowFrameByFrameMode.isChecked()
            self.ffmpeg_bin = preferencesWindow.leFFmpegPath.text()

            if self.ffmpeg_bin and preferencesWindow.cbAllowFrameByFrameMode.isChecked():
                self.availablePlayers.append(FFMPEG)

            if not preferencesWindow.cbAllowFrameByFrameMode.isChecked():
                if FFMPEG in self.availablePlayers:
                    self.availablePlayers.remove(FFMPEG)

            self.ffmpeg_cache_dir = preferencesWindow.leFFmpegCacheDir.text()
            self.ffmpeg_cache_dir_max_size = preferencesWindow.sbFFmpegCacheDirMaxSize.value()


            self.saveConfigFile()


    def FFmpegTimerOut(self):
        '''
        triggered when frame-by-frame mode:
        read next frame and update image
        '''

        logging.debug('FFmpegTimerOut function')

        fps = list(self.fps.values())[0]

        logging.debug('fps {0}'.format( fps ))

        frameMs = 1000/fps

        logging.debug('framMs {0}'.format( frameMs ))

        requiredFrame = self.FFmpegGlobalFrame + 1

        logging.debug('required frame: {0}'.format( requiredFrame ))
        logging.debug('sum self.duration {0}'.format( sum(self.duration)))

        # check if end of last media
        if requiredFrame * frameMs >= sum(self.duration):
            return

        currentMedia = ''
        currentIdx = -1

        for idx, media in enumerate(self.pj[OBSERVATIONS][self.observationId][FILE][PLAYER1]):
            if requiredFrame *frameMs < sum(self.duration[0:idx + 1 ]):
                currentMedia = media
                currentIdx = idx
                frameCurrentMedia = requiredFrame - sum(self.duration[0:idx]) / frameMs
                break

        md5FileName = hashlib.md5(currentMedia.encode('utf-8')).hexdigest()

        logging.debug('imagesList {0}'.format( self.imagesList ))
        logging.debug('image {0}'.format( '%s-%d' % (md5FileName, int(frameCurrentMedia/ fps)) ))

        if True:

            ffmpeg_command = '"{ffmpeg_bin}" -ss {pos} -loglevel quiet -i "{currentMedia}" -vframes {fps} -qscale:v 2 "{imageDir}{sep}BORIS_{fileName}-{pos}_%d.{extension}"'.format(
            ffmpeg_bin=self.ffmpeg_bin,
            pos=int(frameCurrentMedia / fps),
            currentMedia=currentMedia,
            fps=str(round(fps) +1),
            imageDir=self.imageDirectory,
            sep=os.sep,
            fileName=md5FileName,
            extension='jpg' )

            logging.debug('ffmpeg command: {0}'.format( ffmpeg_command ))

            p = subprocess.Popen( ffmpeg_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True )
            out, error = p.communicate()
            out = out.decode('utf-8')
            error = error.decode('utf-8')

            if error:
                logging.debug('ffmpeg error: {0}'.format( error ))

            self.imagesList.update( [ '%s-%d' % (md5FileName, int(frameCurrentMedia/ fps)) ] )

        logging.debug('frame current media: {0}'.format( frameCurrentMedia ))

        img = '%(imageDir)s%(sep)sBORIS_%(fileName)s-%(second)d_%(frame)d.%(extension)s' % \
              {'imageDir': self.imageDirectory, 'sep': os.sep, 'fileName': md5FileName, 'second':  int(frameCurrentMedia / fps),
               'frame':( frameCurrentMedia - int(frameCurrentMedia / fps)*fps)+1,
               'extension': 'jpg'}

        if not os.path.isfile(img):
            logging.warning('image not found: {0}'.format( img ))
            return

        pixmap = QtGui.QPixmap( img )

        self.lbFFmpeg.setPixmap( pixmap.scaled(self.lbFFmpeg.size(), Qt.KeepAspectRatio))

        self.FFmpegGlobalFrame = requiredFrame

        currentTime = self.getLaps() * 1000

        self.lbTime.setText( '{currentMediaName}: <b>{currentTime} / {totalTime}</b> frame: <b>{currentFrame}</b>'.format(
                             currentMediaName=self.mediaplayer.get_media().get_meta(0),
                             currentTime=self.convertTime( currentTime /1000),
                             totalTime=self.convertTime(Decimal(self.mediaplayer.get_length() / 1000)),
                             currentFrame=round(self.FFmpegGlobalFrame)
                             ))

        # extract State events
        StateBehaviorsCodes = [ self.pj['behaviors_conf'][x]['code'] for x in [y for y in self.pj['behaviors_conf']
                                if 'State' in self.pj['behaviors_conf'][y]['type']] ]

        self.currentStates = {}

        # add states for no focal subject
        self.currentStates[ '' ] = []
        for sbc in StateBehaviorsCodes:
            if len(  [ x[ pj_obs_fields['code'] ] for x in self.pj[OBSERVATIONS][self.observationId][EVENTS ]
                       if x[ pj_obs_fields['subject'] ] == '' and x[ pj_obs_fields['code'] ] == sbc and x[ pj_obs_fields['time'] ] <= currentTime /1000 ] ) % 2: # test if odd
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
            self.lbCurrentStates.setText(  '%s' % (', '.join(self.currentStates[ idx ])))
        else:
            self.lbCurrentStates.setText(  '%s' % (', '.join(self.currentStates[ '' ])))

        # show selected subjects
        for idx in [str(x) for x in sorted([int(x) for x in self.pj[SUBJECTS].keys() ])]:
            self.twSubjects.item(int(idx), len( subjectsFields ) ).setText( ','.join(self.currentStates[idx]) )

        # show tracking cursor
        self.get_events_current_row()


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
        self.palette.setColor (QtGui.QPalette.Window, QtGui.QColor(0,0,0))
        self.videoframe.setPalette(self.palette)
        self.videoframe.setAutoFillBackground(True)

        self.volumeslider = QtGui.QSlider(QtCore.Qt.Vertical, self)
        self.volumeslider.setMaximum(100)
        self.volumeslider.setValue(self.mediaplayer.audio_get_volume())
        self.volumeslider.setToolTip('Volume')
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

        self.toolBox.insertItem(VIDEO_TAB, self.videoTab, 'Audio/Video')

        self.actionFrame_by_frame.setEnabled(False)

        if FFMPEG in self.availablePlayers:

            self.ffmpegLayout = QHBoxLayout()
            self.lbFFmpeg = QLabel(self)
            self.lbFFmpeg.setBackgroundRole(QPalette.Base)

            self.ffmpegLayout.addWidget(self.lbFFmpeg)

            self.ffmpegTab = QtGui.QWidget()
            self.ffmpegTab.setLayout(self.ffmpegLayout)

            self.toolBox.insertItem(FRAME_TAB, self.ffmpegTab, 'Frame by frame')
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

                    self.playerType = 'VIEWER'
                    self.playMode = ''
                    self.dwObservations.setVisible(True)
                    return True

            else:
                QMessageBox.critical(self, programName, """A media file was not found!<br>The observation will be opened in VIEW mode.<br>
                It will not be allowed to log events.<br>Modify the media path to point an existing media file to log events or copy media file in the BORIS project directory.""",
                QMessageBox.Ok | QMessageBox.Default, QMessageBox.NoButton)

                self.playerType = 'VIEWER'
                self.playMode = ''
                self.dwObservations.setVisible(True)
                return True

        # check if media list player 1 contains more than 1 media
        if len(self.pj[OBSERVATIONS][self.observationId][FILE][PLAYER1]) > 1 \
            and \
           PLAYER2 in self.pj[OBSERVATIONS][self.observationId][FILE] and  self.pj[OBSERVATIONS][self.observationId][FILE][PLAYER2]:

               QMessageBox.warning(self, programName , 'It is not yet possible to play a second media when more media are loaded in the first media player' )
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
            logging.debug('media file {}'.format(mediaFile))
            try:
                self.instance
            except AttributeError:
                self.initialize_video_tab()

            media = self.instance.media_new( mediaFile )
            media.parse()

            # media duration
            mediaLength = 0  # in ms
            mediaFPS = 0

            try:
                mediaLength = self.pj[OBSERVATIONS][self.observationId]['media_info']['length'][mediaFile] * 1000
                #self.duration.append(self.pj[OBSERVATIONS][self.observationId]['media_info']['length'][mediaFile]*1000)
                #logging.debug('self.duration 1 {}'.format(self.duration))

                mediaFPS = self.pj[OBSERVATIONS][self.observationId]['media_info']['fps'][mediaFile]
                #self.fps[mediaFile] = self.pj[OBSERVATIONS][self.observationId]['media_info']['fps'][mediaFile]

            except:
                # md5 sum of file content
                fileContentMD5 = hashfile( mediaFile , hashlib.md5())

                try:
                    mediaLength = self.pj['project_media_file_info'][fileContentMD5]['video_length']
                    #self.duration.append( self.pj['project_media_file_info'][fileContentMD5]['video_length'] )
                except:
                    mediaLength = media.get_duration()
                    #self.duration.append(media.get_duration())

                # media FPS
                try:
                    mediaFPS = round( self.pj['project_media_file_info'][fileContentMD5]['nframe'] / ( self.pj['project_media_file_info'][fileContentMD5]['video_length']/1000 ) , 3)
                    #self.fps[fileContentMD5] = round( self.pj['project_media_file_info'][fileContentMD5]['nframe'] / ( self.pj['project_media_file_info'][fileContentMD5]['video_length']/1000 ) , 3)
                except:
                    '''
                    try:
                        self.fps[fileContentMD5] = round( self.pj[OBSERVATIONS][self.observationId][MEDIA_FILE_INFO][fileContentMD5]['nframe'] \
                               / (self.pj[OBSERVATIONS][self.observationId][MEDIA_FILE_INFO][fileContentMD5]['video_length'] /1000) , 3)

                        # add parameter 'media_file_info' to 'project_media_file_info'
                        if not 'project_media_file_info' in self.pj:
                            self.pj['project_media_file_info'] = {}
                        self.pj['project_media_file_info'][fileContentMD5] = self.pj[OBSERVATIONS][self.observationId][MEDIA_FILE_INFO][fileContentMD5]
                        self.projectChanged = True
                    except:
                        # if every thing fail try to extract parameter playing media with VLC for few seconds
                    '''
                    try:
                        logging.debug('playing with VLC')
                        out, fps = playWithVLC(mediaFile)

                        logging.debug('out from vlc: {}'.format( out ))
                        logging.debug('fps from vlc: {}'.format( fps ))

                        mediaLength = int(out)
                        mediaFPS = fps
                        #self.fps[fileContentMD5] = script_fps

                        # insert in 'project_media_file_info' dictionary
                        if not 'project_media_file_info' in self.pj:
                            self.pj['project_media_file_info'] = {}

                        if not fileContentMD5 in self.pj['project_media_file_info']:
                            self.pj['project_media_file_info'][fileContentMD5] = {}

                        self.pj['project_media_file_info'][fileContentMD5]['video_length'] = int(out)
                        self.pj['project_media_file_info'][fileContentMD5]['nframe'] = int(fps * int(out)/1000)
                        self.projectChanged = True
                    except:
                        mediaFPS = 0
                        #self.fps[fileContentMD5] = 0

                    if mediaFPS == 0:
                        if FFMPEG in self.availablePlayers:
                            response = dialog.MessageDialog(programName, 'BORIS is not able to determine the frame rate of the video.\nLaunch accurate video analysis?\nThis analysis may be long (half time of video)', [YES, NO ])
                            if response == YES:
                                nframe, videoTime = accurate_video_analysis( self.ffmpeg_bin, mediaFile )
                                if nframe:
                                    mediaLength = int(videoTime)   # ms
                                    mediaFPS = nframe / (int(videoTime)/1000)

            logging.debug('mediaLength: {}'.format( mediaLength ))
            logging.debug('mediaFPS: {}'.format( mediaFPS ))

            self.duration.append( int(mediaLength) )
            self.fps[mediaFile] = mediaFPS

            logging.debug('self.duration: {}'.format( self.duration ))
            logging.debug('self.fps: {}'.format( self.fps ))

            if not 'media_info' in self.pj[OBSERVATIONS][self.observationId]:
                self.pj[OBSERVATIONS][self.observationId]['media_info'] = {"length":{}, "fps":{}}

            self.pj[OBSERVATIONS][self.observationId]['media_info']['length'][mediaFile] = mediaLength/1000
            self.pj[OBSERVATIONS][self.observationId]['media_info']['fps'][mediaFile] = mediaFPS

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
        if FFMPEG in self.availablePlayers:
            if len(set( self.fps.values() )) != 1:
                QMessageBox.critical(self, programName, 'The frame-by-frame mode will not be available because the video files have different frame rates (%s).' % (', '.join([str(i) for i in list(self.fps.values())])),\
                 QMessageBox.Ok | QMessageBox.Default, QMessageBox.NoButton)

        # show first frame of video
        logging.debug('playing media #{0}'.format( 0 ))

        self.mediaListPlayer.play_item_at_index( 0 )
        app.processEvents()

        # play mediaListPlayer for a while to obtain media information
        while self.mediaListPlayer.get_state() != vlc.State.Playing:
            time.sleep(3)

        self.mediaListPlayer.pause()

        app.processEvents()


        self.mediaplayer.set_time(0)

        # no subtitles
        #self.mediaplayer.video_set_spu(0)


        if FFMPEG in self.availablePlayers:
            self.FFmpegTimer = QTimer(self)
            self.FFmpegTimer.timeout.connect(self.FFmpegTimerOut)

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

                    logging.debug( 'media file 2 {0}  duration {1}'.format(mediaFile, media.get_duration()))

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

                while self.mediaListPlayer2.get_state() != vlc.State.Playing:
                    time.sleep(3)

                self.mediaListPlayer2.pause()
                app.processEvents()

                self.mediaplayer2.set_time(0)
                if TIME_OFFSET_SECOND_PLAYER in self.pj[OBSERVATIONS][self.observationId] \
                    and self.pj[OBSERVATIONS][self.observationId][TIME_OFFSET_SECOND_PLAYER]:
                    if self.pj[OBSERVATIONS][self.observationId][TIME_OFFSET_SECOND_PLAYER] > 0:
                        self.mediaplayer2.set_time( int( self.pj[OBSERVATIONS][self.observationId][TIME_OFFSET_SECOND_PLAYER] *1000) )


                # no subtitles
                #self.mediaplayer2.video_set_spu(0)


        '''self.initialize_video_tab()'''

        self.videoTab.setEnabled(True)

        self.toolBox.setCurrentIndex(VIDEO_TAB)
        self.toolBox.setItemEnabled (VIDEO_TAB, False)

        self.toolBar.setEnabled(True)

        self.display_timeoffset_statubar( self.pj[OBSERVATIONS][self.observationId][TIME_OFFSET] )

        #self.timer.start(200)
        self.timer_out()

        self.lbSpeed.setText('x{:.3f}'.format(self.play_rate))

        if window.focusWidget():
            window.focusWidget().installEventFilter(self)

        return True



    def eventFilter(self, source, event):
        '''
        send event from class (QScrollArea) to mainwindow
        '''
        if event.type() == QtCore.QEvent.KeyPress:
            key = event.key()
            if key in [Qt.Key_Up, Qt.Key_Down, Qt.Key_Left, Qt.Key_Right, Qt.Key_PageDown, Qt.Key_PageUp]:
                self.keyPressEvent( event )

        return QMainWindow.eventFilter(self, source, event)


    def loadEventsInTW(self, obsId):
        '''
        load events in table widget
        '''

        self.twEvents.setRowCount(len( self.pj[OBSERVATIONS][obsId][EVENTS] ))
        row = 0

        for event in self.pj[OBSERVATIONS][obsId][EVENTS]:

            for field_type in tw_events_fields:

                if field_type in pj_events_fields:

                    field = event[ pj_obs_fields[field_type] ]
                    if field_type == 'time':
                        field = str( self.convertTime( field) )

                    twi = QTableWidgetItem(  field )
                    self.twEvents.setItem(row, tw_obs_fields[field_type] , twi )

                else:
                    self.twEvents.setItem(row, tw_obs_fields[field_type] , QTableWidgetItem(''))

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
                for player in sorted(self.pj[OBSERVATIONS][obs][FILE].keys()):
                    for media in self.pj[OBSERVATIONS][obs][FILE][player]:
                        mediaList.append('#{0}: {1}'.format(player, media))

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
            resultStr = ''
        if result == 1:   # select
            resultStr = 'ok'
        if result == 2:   # open
            resultStr = OPEN
        if result == 3:   # edit
            resultStr = EDIT

        return resultStr, selectedObs


    def initialize_new_live_observation(self):
        '''
        initialize new live observation
        '''

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
        self.textButton.setText('Start live observation')
        self.lbTimeLive.setText('00:00:00.000')

        self.liveStartTime = None
        self.liveTimer.stop()

    def new_observation_triggered(self):
        self.new_observation(mode=NEW, obsId='')


    def new_observation(self, mode=NEW, obsId=''):
        '''
        define a new observation or edit an existing observation
        '''
        # check if current observation must be closed to create a new one
        if mode == NEW and self.observationId:
            response = dialog.MessageDialog(programName, 'The current observation will be closed. Do you want to continue?', [YES, NO])
            if response == NO:
                return
            else:
                self.close_observation()


        observationWindow = observation.Observation()

        observationWindow.setGeometry(self.pos().x() + 100, self.pos().y() + 130, 600, 400)
        observationWindow.pj = self.pj
        observationWindow.instance = vlc.Instance()
        observationWindow.mode = mode
        observationWindow.mem_obs_id = obsId
        observationWindow.availablePlayers = self.availablePlayers
        observationWindow.dteDate.setDateTime( QDateTime.currentDateTime() )
        if FFMPEG in self.availablePlayers:
            observationWindow.ffmpeg_bin = self.ffmpeg_bin
        else:
            observationWindow.ffmpeg_bin = ''

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
                item.setText( self.pj[INDEPENDENT_VARIABLES][i]['type']  )
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

            observationWindow.setWindowTitle('Edit observation ' + obsId )
            mem_obs_id = obsId
            observationWindow.leObservationId.setText( obsId )
            observationWindow.dteDate.setDateTime( QDateTime.fromString( self.pj[OBSERVATIONS][obsId]['date'], 'yyyy-MM-ddThh:mm:ss') )
            observationWindow.teDescription.setPlainText( self.pj[OBSERVATIONS][obsId]['description'] )

            if self.timeFormat == S:

                observationWindow.leTimeOffset.setText( self.convertTime( abs(self.pj[OBSERVATIONS][obsId]['time offset']) ))

                if "time offset second player" in self.pj[OBSERVATIONS][obsId]:
                    observationWindow.leTimeOffset_2.setText( self.convertTime( abs(self.pj[OBSERVATIONS][obsId]["time offset second player"]) ))

                    if self.pj[OBSERVATIONS][obsId]["time offset second player"] <= 0:
                        observationWindow.rbEarlier.setChecked(True)
                    else:
                        observationWindow.rbLater.setChecked(True)

            if self.timeFormat == HHMMSS:

                time = QTime()
                h,m,s_dec = seconds2time( abs(self.pj[OBSERVATIONS][obsId]['time offset'])).split(':')
                s, ms = s_dec.split('.')
                time.setHMS(int(h),int(m),int(s),int(ms))
                observationWindow.teTimeOffset.setTime( time )

                if "time offset second player" in self.pj[OBSERVATIONS][obsId]:
                    time = QTime()
                    h,m,s_dec = seconds2time( abs(self.pj[OBSERVATIONS][obsId]["time offset second player"])).split(':')
                    s, ms = s_dec.split('.')
                    time.setHMS(int(h),int(m),int(s),int(ms))
                    observationWindow.teTimeOffset_2.setTime( time )

                    if self.pj[OBSERVATIONS][obsId]["time offset second player"] <= 0:
                        observationWindow.rbEarlier.setChecked(True)
                    else:
                        observationWindow.rbLater.setChecked(True)


            if self.pj[OBSERVATIONS][obsId]['time offset'] < 0:
                observationWindow.rbSubstract.setChecked(True)

            if PLAYER1 in self.pj[OBSERVATIONS][obsId][FILE] and self.pj[OBSERVATIONS][obsId][FILE][PLAYER1]:

                observationWindow.lwVideo.addItems( self.pj[OBSERVATIONS][obsId][FILE][PLAYER1] )
                if 'media_durations' in self.pj[OBSERVATIONS][obsId]:
                    observationWindow.mediaDurations = self.pj[OBSERVATIONS][obsId]['media_durations']

            # check if simultaneous 2nd media
            if PLAYER2 in self.pj[OBSERVATIONS][obsId][FILE] and self.pj[OBSERVATIONS][obsId][FILE][PLAYER2]:   # media for 2nd player

                observationWindow.lwVideo_2.addItems( self.pj[OBSERVATIONS][obsId][FILE][PLAYER2] )

            if self.pj[OBSERVATIONS][obsId]['type'] in [MEDIA]:
                observationWindow.tabProjectType.setCurrentIndex(video)


            if self.pj[OBSERVATIONS][obsId]['type'] in [LIVE]:
                observationWindow.tabProjectType.setCurrentIndex(live)


        if observationWindow.exec_():

            self.projectChanged = True

            new_obs_id = observationWindow.leObservationId.text()

            if mode == NEW:
                self.observationId = new_obs_id
                self.pj[OBSERVATIONS][self.observationId] = { FILE: [], 'type': '' ,  'date': '', 'description': '','time offset': 0, 'events': [] }

            # check if id changed
            if mode == EDIT and new_obs_id != obsId:

                logging.info('observation id {0} changed in {1}'.format(obsId, new_obs_id))

                self.pj[OBSERVATIONS][ new_obs_id ] = self.pj[OBSERVATIONS][ obsId ]
                del self.pj[OBSERVATIONS][ obsId ]

            # observation date
            self.pj[OBSERVATIONS][new_obs_id]['date'] = observationWindow.dteDate.dateTime().toString(Qt.ISODate)

            self.pj[OBSERVATIONS][new_obs_id]['description'] = observationWindow.teDescription.toPlainText()

            # observation type: read project type from tab text
            self.pj[OBSERVATIONS][new_obs_id]['type'] = observationWindow.tabProjectType.tabText( observationWindow.tabProjectType.currentIndex() ).upper()

            # independent variables for observation
            self.pj[OBSERVATIONS][new_obs_id][INDEPENDENT_VARIABLES] = {}
            for r in range(0, observationWindow.twIndepVariables.rowCount()):

                # set dictionary as label (col 0) => value (col 2)
                self.pj[OBSERVATIONS][new_obs_id][INDEPENDENT_VARIABLES][ observationWindow.twIndepVariables.item(r, 0).text() ] = observationWindow.twIndepVariables.item(r, 2).text()

            # observation time offset
            if self.timeFormat == HHMMSS:
                self.pj[OBSERVATIONS][new_obs_id][TIME_OFFSET]  = time2seconds(observationWindow.teTimeOffset.time().toString('hh:mm:ss.zzz'))
                self.pj[OBSERVATIONS][new_obs_id][TIME_OFFSET_SECOND_PLAYER] = time2seconds(observationWindow.teTimeOffset_2.time().toString('hh:mm:ss.zzz'))

            if self.timeFormat == S:
                self.pj[OBSERVATIONS][new_obs_id][TIME_OFFSET] =  abs(Decimal( observationWindow.leTimeOffset.text() ))
                self.pj[OBSERVATIONS][new_obs_id][TIME_OFFSET_SECOND_PLAYER] =  abs(Decimal( observationWindow.leTimeOffset_2.text() ))

            if observationWindow.rbSubstract.isChecked():
                self.pj[OBSERVATIONS][new_obs_id][TIME_OFFSET]  = - self.pj[OBSERVATIONS][new_obs_id][TIME_OFFSET]

            if observationWindow.rbEarlier.isChecked():
                self.pj[OBSERVATIONS][new_obs_id][TIME_OFFSET_SECOND_PLAYER]  = - self.pj[OBSERVATIONS][new_obs_id][TIME_OFFSET_SECOND_PLAYER]


            self.display_timeoffset_statubar(self.pj[OBSERVATIONS][new_obs_id][TIME_OFFSET])

            # media file
            fileName = {}

            # media
            if self.pj[OBSERVATIONS][new_obs_id]['type'] in [MEDIA]:

                fileName[PLAYER1] = []
                if observationWindow.lwVideo.count():

                    for i in range(observationWindow.lwVideo.count()):

                        if self.saveMediaFilePath:
                            # save full path
                            fileName[PLAYER1].append( observationWindow.lwVideo.item(i).text() )
                        else:
                            fileName[PLAYER1].append( os.path.basename( observationWindow.lwVideo.item(i).text() ) )

                fileName[PLAYER2] = []

                if observationWindow.lwVideo_2.count():

                    for i in range(observationWindow.lwVideo_2.count()):

                        if self.saveMediaFilePath:
                            # save full path
                            fileName[PLAYER2].append (  observationWindow.lwVideo_2.item(i).text() )
                        else:
                            fileName[PLAYER2].append ( os.path.basename( observationWindow.lwVideo_2.item(i).text() ) )

                self.pj[OBSERVATIONS][new_obs_id][FILE] = fileName

                self.pj[OBSERVATIONS][new_obs_id]['media_info'] = {"length": observationWindow.mediaDurations,
                                                                  "fps":  observationWindow.mediaFPS}

                logging.debug('media_info: {0}'.format(  self.pj[OBSERVATIONS][new_obs_id]['media_info'] ))

                logging.debug('media file info: {0}'.format(  observationWindow.media_file_info ))

                # add parameters to project_media_file_info
                if not 'project_media_file_info' in self.pj:
                    self.pj['project_media_file_info'] = {}

                for h in observationWindow.media_file_info:
                    self.pj['project_media_file_info'][h] = observationWindow.media_file_info[h]
                logging.info('pj: {0}'.format(  self.pj ))

            if mode == NEW:

                # title of dock widget
                self.dwObservations.setWindowTitle('Events for ' + self.observationId)

                if self.pj[OBSERVATIONS][self.observationId]['type'] in [LIVE]:

                    self.playerType = LIVE
                    self.initialize_new_live_observation()

                else:
                    self.playerType = VLC
                    self.initialize_new_observation_vlc()

                self.menu_options()


    def close_observation(self):
        '''
        close current observation
        '''

        logging.info('Close observation {0}'.format(self.playerType))

        self.observationId = ''

        if self.playerType == LIVE:

            self.liveObservationStarted = False
            self.liveStartTime = None
            self.liveTimer.stop()
            self.toolBox.removeItem(0)
            self.liveTab.deleteLater()


        if self.playerType == VLC:

            self.timer.stop()

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


            # FFMPEG
            if FFMPEG in self.availablePlayers:
                self.ffmpegLayout.deleteLater()
                self.lbFFmpeg.deleteLater()
                self.ffmpegTab.deleteLater()

                self.FFmpegTimer.stop()
                self.FFmpegGlobalFrame = 0
                self.imagesList = set()


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

        self.lbTimeOffset.clear()
        self.lbSpeed.clear()

        self.playerType = ''

        self.menu_options()



    def readConfigFile(self):
        '''
        read config file
        '''

        logging.info('read config file')

        if __version__ == 'DEV':
            iniFilePath = os.path.expanduser('~') + os.sep + '.boris_dev'
        else:
            iniFilePath = os.path.expanduser('~') + os.sep + '.boris'

        if os.path.isfile( iniFilePath ):
            settings = QSettings(iniFilePath , QSettings.IniFormat)

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

            # frame-by-frame tab
            self.allowFrameByFrame = False
            try:
                self.allowFrameByFrame = ( settings.value('allow_frame_by_frame') == 'true' )
            except:
                self.allowFrameByFrame = False

            if not self.ffmpeg_bin:
                try:
                    self.ffmpeg_bin = settings.value('ffmpeg_bin')
                    if not self.ffmpeg_bin:
                        self.ffmpeg_bin = ''
                except:
                    self.ffmpeg_bin = ''

            if self.allowFrameByFrame:
                r, msg = test_ffmpeg_path(self.ffmpeg_bin)
                if r:
                    self.availablePlayers.append(FFMPEG)
                else:
                    self.allowFrameByFrame = False
                    logging.warning(msg)

            self.ffmpeg_cache_dir = ''
            try:
                self.ffmpeg_cache_dir = settings.value('ffmpeg_cache_dir')
                if not self.ffmpeg_cache_dir:
                    self.ffmpeg_cache_dir = ''
            except:
                self.ffmpeg_cache_dir = ''

            self.ffmpeg_cache_dir_max_size = 0
            try:
                self.ffmpeg_cache_dir_max_size = int(settings.value('ffmpeg_cache_dir_max_size'))
                if not self.ffmpeg_cache_dir_max_size:
                    self.ffmpeg_cache_dir_max_size = 0
            except:
                self.ffmpeg_cache_dir_max_size = 0





        # test if FFmpeg embedded to allow frame-by-frame mode
        if not self.ffmpeg_bin:
            if sys.platform.startswith('win') and os.path.isfile(os.path.dirname(os.path.realpath(__file__)) + os.sep + 'ffmpeg.exe' ):
                self.allowFrameByFrame = True
                self.ffmpeg_bin = os.path.dirname(os.path.realpath(__file__)) + os.sep + 'ffmpeg.exe'

            elif sys.platform.startswith('linux'):

                logging.debug('ffmpeg embedded {}'.format(os.path.isfile(os.path.dirname(os.path.realpath(__file__)) + os.sep + 'ffmpeg' )))
                if os.path.isfile(os.path.dirname(os.path.realpath(__file__)) + os.sep + 'ffmpeg' ):
                    self.allowFrameByFrame = True
                    self.ffmpeg_bin = os.path.dirname(os.path.realpath(__file__)) + os.sep + 'ffmpeg'

                # test if FFmpeg installed on path
                if not self.ffmpeg_bin:
                    r, msg = test_ffmpeg_path('ffmpeg')
                    if r:
                        self.allowFrameByFrame = True
                        self.ffmpeg_bin = 'ffmpeg'

            if self.ffmpeg_bin:
                self.availablePlayers.append(FFMPEG)

        logging.debug( 'available players: {}'.format(self.availablePlayers ))



    def saveConfigFile(self):
        '''
        save config file
        '''

        logging.info('save config file')

        if __version__ == 'DEV':
            iniFilePath = os.path.expanduser('~') + os.sep + '.boris_dev'
        else:
            iniFilePath = os.path.expanduser('~') + os.sep + '.boris'

        settings = QSettings(iniFilePath, QSettings.IniFormat)

        #settings.setValue('MainWindow/State', self.saveState())
        settings.setValue('MainWindow/Size', self.size())
        settings.setValue('MainWindow/Position', self.pos())

        settings.setValue('Time/Format', self.timeFormat )
        settings.setValue('Time/Repositioning_time_offset', self.repositioningTimeOffset )
        settings.setValue('Time/fast_forward_speed', self.fast )
        settings.setValue('Time/play_rate_step', self.play_rate_step)

        settings.setValue('Save_media_file_path', self.saveMediaFilePath )

        settings.setValue('Automatic_backup', self.automaticBackup )

        settings.setValue('behavioural_strings_separator', self.behaviouralStringsSeparator )

        settings.setValue('confirm_sound', self.confirmSound)

        settings.setValue('embed_player', self.embedPlayer)

        settings.setValue('alert_nosubject', self.alertNoFocalSubject)
        settings.setValue('tracking_cursor_above_event', self.trackingCursorAboveEvent)

        # frame-by-frame
        settings.setValue('allow_frame_by_frame', self.allowFrameByFrame)
        settings.setValue( 'ffmpeg_bin', self.ffmpeg_bin )
        settings.setValue( 'ffmpeg_cache_dir', self.ffmpeg_cache_dir )
        settings.setValue( 'ffmpeg_cache_dir_max_size', self.ffmpeg_cache_dir_max_size )


    def edit_project_activated(self):

        if self.project:
            self.edit_project(EDIT)
        else:
            QMessageBox.warning(self, programName, 'There is no project to edit')



    def display_timeoffset_statubar(self, timeOffset):
        '''
        display offset in status bar
        '''

        if timeOffset:

            if self.timeFormat == S:
                r = str( timeOffset )
            elif self.timeFormat == HHMMSS:

                r = seconds2time( timeOffset )

            self.lbTimeOffset.setText('Time offset: <b>%s</b>' % r )
        else:
            self.lbTimeOffset.clear()


    def eventType(self, code):
        '''
        returns type of event for code
        '''

        for idx in self.pj['behaviors_conf']:
            if self.pj['behaviors_conf'][idx]['code'] == code:
                return self.pj['behaviors_conf'][idx]['type']
        return None



    def loadEventsInDB(self, selectedSubjects, selectedObservations, selectedBehaviors):
        '''
        populate the db databse with events from selectedObservations, selectedSubjects and selectedBehaviors
        '''
        db = sqlite3.connect(':memory:')

        cursor = db.cursor()

        cursor.execute("CREATE TABLE events ( observation TEXT, subject TEXT, code TEXT, type TEXT, modifiers TEXT, occurence FLOAT);")

        for subject_to_analyze in selectedSubjects:

            for obsId in selectedObservations:

                for event in self.pj[OBSERVATIONS][obsId][EVENTS]:

                    if event[2] in selectedBehaviors:

                        # extract time, code and modifier  ( time0, subject1, code2, modifier3 )
                        if (subject_to_analyze == NO_FOCAL_SUBJECT and event[1] == '') \
                            or ( event[1] == subject_to_analyze ):

                            if event[1] == '':
                                subjectStr = NO_FOCAL_SUBJECT
                            else:
                                subjectStr = event[1]

                            if 'STATE' in self.eventType(event[2]).upper():
                                eventType = 'STATE'
                            else:
                                eventType = 'POINT'

                            r = cursor.execute('''INSERT INTO events (observation, subject, code, type, modifiers, occurence) VALUES (?,?,?,?,?,?)''', \
                            (obsId, subjectStr, event[2], eventType, event[3], str(event[0])))

        db.commit()
        return cursor




    def extract_observed_subjects(self, selected_observations):
        '''
        extract unique subjects from obs_id observation
        '''

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



    def select_subjects(self, observed_subjects):
        '''
        allow user to select subjects
        add no subject if observations do no contain subject
        '''

        subjectsSelection = checkingBox_list()

        # add 'No focal subject'
        if '' in observed_subjects:
            subjectsSelection.item = QListWidgetItem(subjectsSelection.lw)
            subjectsSelection.ch = QCheckBox()
            subjectsSelection.ch.setText( NO_FOCAL_SUBJECT )
            subjectsSelection.ch.setChecked(True)
            subjectsSelection.lw.setItemWidget(subjectsSelection.item, subjectsSelection.ch)

        all_subjects = sorted( [  self.pj[SUBJECTS][x][ 'name' ]  for x in self.pj[SUBJECTS] ] )

        for subject in all_subjects:
            subjectsSelection.item = QListWidgetItem(subjectsSelection.lw)
            subjectsSelection.ch = QCheckBox()
            subjectsSelection.ch.setText( subject )

            if subject in observed_subjects:
                subjectsSelection.ch.setChecked(True)

            subjectsSelection.lw.setItemWidget(subjectsSelection.item, subjectsSelection.ch)

        subjectsSelection.setWindowTitle('Select subjects to analyze')
        subjectsSelection.label.setText('Available subjects')

        subj_sel = []

        if subjectsSelection.exec_():

            for idx in range(subjectsSelection.lw.count()):

                check_box = subjectsSelection.lw.itemWidget(subjectsSelection.lw.item(idx))
                if check_box.isChecked():
                    subj_sel.append( check_box.text() )

            return subj_sel
        else:
            return []

    def select_behaviors(self, observedBehaviors):
        '''
        allow user to select behaviors
        preselection in observedBehaviors
        '''

        behaviorsSelection = checkingBox_list()

        allBehaviors = sorted( [  self.pj['behaviors_conf'][x][ 'code' ]  for x in self.pj['behaviors_conf'] ] )

        for behavior in allBehaviors:

            logging.debug('behavior: {0}'.format(behavior))

            behaviorsSelection.item = QListWidgetItem(behaviorsSelection.lw)
            behaviorsSelection.ch = QCheckBox()
            behaviorsSelection.ch.setText( behavior )

            if behavior in observedBehaviors:
                behaviorsSelection.ch.setChecked(True)

            behaviorsSelection.lw.setItemWidget(behaviorsSelection.item, behaviorsSelection.ch)

        behaviorsSelection.setWindowTitle('Select behaviors to analyze')
        behaviorsSelection.label.setText('Available behaviors')

        behav_sel = []

        if behaviorsSelection.exec_():

            for idx in range(behaviorsSelection.lw.count()):
                check_box = behaviorsSelection.lw.itemWidget(behaviorsSelection.lw.item(idx))
                if check_box.isChecked():
                    behav_sel.append( check_box.text() )

            return behav_sel
        else:
            return []


    def choose_obs_subj_behav(self, selectedObservations, maxTime):

        paramPanelWindow = param_panel.Param_panel()
        paramPanelWindow.selectedObservations = selectedObservations
        paramPanelWindow.pj = self.pj
        paramPanelWindow.extract_observed_behaviors = self.extract_observed_behaviors

        # extract subjects present in observations
        observedSubjects = self.extract_observed_subjects( selectedObservations )
        selectedSubjects = []

        # add 'No focal subject'
        if '' in observedSubjects:
            selectedSubjects.append(NO_FOCAL_SUBJECT)
            paramPanelWindow.item = QListWidgetItem(paramPanelWindow.lwSubjects)
            paramPanelWindow.ch = QCheckBox()
            paramPanelWindow.ch.setText( NO_FOCAL_SUBJECT )
            paramPanelWindow.ch.stateChanged.connect(paramPanelWindow.cb_changed)
            paramPanelWindow.ch.setChecked(True)
            paramPanelWindow.lwSubjects.setItemWidget(paramPanelWindow.item, paramPanelWindow.ch)

        all_subjects = sorted( [  self.pj[SUBJECTS][x][ 'name' ]  for x in self.pj[SUBJECTS] ] )

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

        allBehaviors = sorted( [  self.pj['behaviors_conf'][x][ 'code' ]  for x in self.pj['behaviors_conf'] ] )
        logging.debug('allBehaviors: {0}'.format(allBehaviors))

        observedBehaviors = self.extract_observed_behaviors( selectedObservations, selectedSubjects )
        logging.debug('observed behaviors: {0}'.format(observedBehaviors))

        for behavior in allBehaviors:

            paramPanelWindow.item = QListWidgetItem(paramPanelWindow.lwBehaviors)
            paramPanelWindow.ch = QCheckBox()
            paramPanelWindow.ch.setText( behavior )

            if behavior in observedBehaviors:
                paramPanelWindow.ch.setChecked(True)

            paramPanelWindow.lwBehaviors.setItemWidget(paramPanelWindow.item, paramPanelWindow.ch)

        # hide max time
        if not maxTime:
            paramPanelWindow.sbMaxTime.setVisible(False)
            paramPanelWindow.lbMaxTime.setVisible(False)
        else:
            paramPanelWindow.sbMaxTime.setValue(maxTime)

        if not paramPanelWindow.exec_():
            return [],[],YES,False,0

        selectedSubjects = paramPanelWindow.selectedSubjects
        selectedBehaviors = paramPanelWindow.selectedBehaviors

        logging.debug( selectedSubjects )
        logging.debug( selectedBehaviors )

        if paramPanelWindow.cbIncludeModifiers.isChecked():
            includeModifiers = YES
        else:
            includeModifiers = NO

        return selectedSubjects, selectedBehaviors, includeModifiers, paramPanelWindow.cbExcludeBehaviors.isChecked(), paramPanelWindow.sbMaxTime.value()


    def time_budget(self):
        '''
        time budget
        '''
        logging.debug("Time budget function")

        result, selectedObservations = self.selectObservations( MULTIPLE )

        logging.debug("Selected observations: {0}".format(selectedObservations))

        if not selectedObservations:
            return

        #maxTime = Decimal("0.0")
        #flagOK = True

        selectedObsTotalMediaLength = Decimal("0.0")

        for obsId in selectedObservations:

            if self.pj[OBSERVATIONS][ obsId ][TYPE] == MEDIA:

                totalMediaLength = self.observationTotalMediaLength( obsId )

            else: # LIVE
                if self.pj[OBSERVATIONS][ obsId ][EVENTS]:
                    totalMediaLength = max(self.pj[OBSERVATIONS][ obsId ][EVENTS])[0]
                else:
                    totalMediaLength = Decimal("0.0")

            if totalMediaLength == -1:
                selectedObsTotalMediaLength = -1
                break

            selectedObsTotalMediaLength += totalMediaLength

        if selectedObsTotalMediaLength == -1: # an observation media length is not available
            selectedObsTotalMediaLength = 0

        logging.debug('selectedObsTotalMediaLength: {}'.format(selectedObsTotalMediaLength))

        selectedSubjects, selectedBehaviors, includeModifiers, excludeBehaviorsWoEvents, _ = self.choose_obs_subj_behav(selectedObservations, 0)

        if not selectedSubjects or not selectedBehaviors:
            return

        cursor = self.loadEventsInDB( selectedSubjects, selectedObservations, selectedBehaviors )

        out = []
        for subject in selectedSubjects:

            for behavior in selectedBehaviors:

                if includeModifiers == YES:

                    cursor.execute( "SELECT distinct modifiers FROM events WHERE subject = ? AND code = ?", (subject, behavior) )
                    distinct_modifiers = list(cursor.fetchall() )

                    if not distinct_modifiers:
                        if not excludeBehaviorsWoEvents:
                            out.append(  { 'subject': subject , 'behavior': behavior, 'modifiers': '-' , 'duration': '-', 'mean': '-', 'number': 0, 'inter_duration_mean': '-' } )
                        continue
                    if 'POINT' in self.eventType(behavior).upper():

                        for modifier in distinct_modifiers:
                            cursor.execute( "SELECT occurence FROM events WHERE subject = ? AND code = ? AND modifiers = ? ORDER BY observation, occurence", ( subject, behavior, modifier[0] ))
                            rows = cursor.fetchall()
                            inter_duration = 0
                            for idx, row in enumerate(rows):
                                if idx:
                                    inter_duration += float(row[0]) - float(rows[idx-1][0])

                            if len(selectedObservations) > 1 or inter_duration == 0:
                                inter_duration =  'NA'
                            else:
                                inter_duration = round(inter_duration/(len(rows) - 1),3)

                            out.append(  { 'subject': subject , 'behavior': behavior, 'modifiers': modifier[0] , 'duration': '-', 'mean': '-', 'number': len(rows), 'inter_duration_mean': inter_duration } )


                    if 'STATE' in self.eventType(behavior).upper():
                        for modifier in distinct_modifiers:
                            cursor.execute( "SELECT occurence FROM events WHERE subject = ? AND code = ? AND modifiers = ? ORDER BY observation, occurence", (subject, behavior, modifier[0]) )
                            rows = list(cursor.fetchall() )

                            if len( rows ) % 2:
                                out.append( { 'subject': subject , 'behavior': behavior, 'modifiers': modifier[0], 'duration': UNPAIRED, 'mean': UNPAIRED,\
                                           'number': UNPAIRED, 'inter_duration_mean': UNPAIRED } )
                            else:
                                occurences = []
                                tot_duration = 0
                                inter_duration = 0
                                for idx, row in enumerate(rows):
                                    if idx % 2 == 0:
                                        tot_duration += float( rows[idx+1][0]) - float( row[0])
                                    if idx % 2 and idx != len(rows) - 1:
                                        inter_duration += float( rows[idx+1][0]) - float( row[0])

                                if len(selectedObservations) > 1 or inter_duration == 0:
                                    inter_duration = 'NA'
                                else:
                                    inter_duration = round(inter_duration/ (len(rows)/2-1),3)
                                out.append( { 'subject': subject , 'behavior': behavior, 'modifiers': modifier[0], 'duration': round(tot_duration,3), 'mean': round(tot_duration/(len(rows)/2),3),\
                                               'number': int(len(rows)/2), 'inter_duration_mean': inter_duration } )

                else:  # no modifiers
                    if 'POINT' in self.eventType(behavior).upper():
                        cursor.execute( "SELECT occurence FROM events WHERE subject = ? AND code = ?  order by observation, occurence", ( subject, behavior ) )
                        rows =  cursor.fetchall()

                        if not len( rows ):
                            if not excludeBehaviorsWoEvents:
                                out.append({ 'subject': subject , 'behavior': behavior, 'modifiers': 'NA', 'duration': '-', 'mean': '-', 'number': 0, 'inter_duration_mean': '-'})
                            continue

                        inter_duration = 0
                        for idx,row in enumerate(rows):
                            if idx > 0:
                                inter_duration += float(row[0]) - float(rows[idx - 1][0])

                        if len(selectedObservations) > 1 or inter_duration == 0:
                            inter_duration =  'NA'
                        else:
                            inter_duration = round(inter_duration/(len(rows) - 1),3)

                        out.append(  { 'subject': subject , 'behavior': behavior, 'modifiers': 'NA', 'duration': '-', 'mean': '-', 'number': len(rows), 'inter_duration_mean': inter_duration}  )


                    if 'STATE' in self.eventType(behavior).upper():
                        cursor.execute( "SELECT occurence FROM events where subject = ? AND code = ? order by observation, occurence", (subject, behavior) )
                        rows = list(cursor.fetchall() )

                        logging.debug('occurences: {0}'.format(rows))

                        if not len( rows ):
                            if not excludeBehaviorsWoEvents:
                                out.append({ 'subject': subject , 'behavior': behavior, 'modifiers': 'NA', 'duration': 0, 'mean': 0, 'number': 0, 'inter_duration_mean': '-'})
                            continue
                        if len( rows ) % 2:
                            out.append( { 'subject': subject , 'behavior': behavior, 'modifiers': 'NA', 'duration': UNPAIRED, 'mean': UNPAIRED,\
                                           'number': UNPAIRED, 'inter_duration_mean': UNPAIRED } )
                        else:
                            occurences = []
                            tot_duration = 0
                            inter_duration = 0
                            for idx, row in enumerate(rows):
                                if idx % 2 == 0:
                                    tot_duration += float( rows[idx+1][0]) - float( row[0])
                                if idx % 2 and idx != len(rows) - 1:
                                    inter_duration += float( rows[idx+1][0]) - float( row[0])

                            if len(selectedObservations) > 1 or inter_duration == 0:
                                inter_duration = 'NA'
                                inter_duration_mean = '-'
                            else:
                                inter_duration_mean = round(inter_duration / (len(rows) / 2 - 1), 3)

                            out.append( { 'subject': subject , 'behavior': behavior, 'modifiers': 'NA', 'duration': round(tot_duration,3), 'mean': round(tot_duration / (len(rows)/2),3),\
                                           'number': int(len(rows)/2), \
                                           'inter_duration_mean': inter_duration_mean } )


        # widget for results visualization
        self.tb = timeBudgetResults( logging.getLogger().getEffectiveLevel(), self.pj)

        # observations list
        self.tb.label.setText("Selected observations")
        for obs in selectedObservations:
            self.tb.lw.addItem(obs)

        if selectedObsTotalMediaLength:
            self.tb.lbTotalObservedTime.setText( "Total media length: {0} s  (~ {1} min)".format(round(selectedObsTotalMediaLength,3),round(selectedObsTotalMediaLength/60)) )
        else:
            self.tb.lbTotalObservedTime.setText( "Total media length: not available")


        tb_fields = ['Subject', 'Behavior', 'Modifiers', 'Total number', 'Total duration (s)', 'Duration mean (s)', 'inter-event intervals mean (s)', '% of total media length']
        self.tb.twTB.setColumnCount( len( tb_fields ) )
        self.tb.twTB.setHorizontalHeaderLabels(tb_fields)

        fields = ['subject', 'behavior',  'modifiers', 'number', 'duration', 'mean', 'inter_duration_mean']

        for row in out:
            self.tb.twTB.setRowCount(self.tb.twTB.rowCount() + 1)

            column = 0

            for field in fields:
                item = QTableWidgetItem(str( row[field]).replace(' ()','' ))
                # no modif allowed
                item.setFlags(Qt.ItemIsEnabled)
                self.tb.twTB.setItem(self.tb.twTB.rowCount() - 1, column , item)
                column += 1

            # % of total time

            if row['duration'] != '-' and row['duration'] != 0 and row['duration'] != UNPAIRED and selectedObsTotalMediaLength:
                item = QTableWidgetItem(str( round( row['duration'] / float(selectedObsTotalMediaLength) * 100,1)  ) )
            else:
                item = QTableWidgetItem( '-' )

            item.setFlags(Qt.ItemIsEnabled)
            self.tb.twTB.setItem(self.tb.twTB.rowCount() - 1, column , item)

        self.tb.twTB.resizeColumnsToContents()

        self.tb.show()


    def observationTotalMediaLength(self, obsId ):
        '''
        total media length for observation
        if media length not available return 0

        return total media length in s
        '''

        totalMediaLength = Decimal("0.0")

        totalMediaLength1 = Decimal("0.0")
        totalMediaLength2 = Decimal("0.0")

        for mediaFile in self.pj[OBSERVATIONS][obsId][FILE][PLAYER1]:

            mediaLength = 0
            try:
                mediaLength = self.pj[OBSERVATIONS][obsId]['media_info']['length'][mediaFile]
            except:
                # md5 sum of file content
                fileContentMD5 = hashfile( mediaFile , hashlib.md5())
                try:
                    mediaLength = self.pj['project_media_file_info'][fileContentMD5]['video_length']/1000
                except:
                    try:
                        instance = vlc.Instance()
                        media = instance.media_new(mediaFile)
                        media.parse()

                        mediaLength = media.get_duration()/1000
                    except:
                        totalMediaLength1 = -1
                        break

            totalMediaLength1 += Decimal(mediaLength)

        for mediaFile in self.pj[OBSERVATIONS][obsId][FILE][PLAYER2]:

            mediaLength = 0
            try:
                mediaLength = self.pj[OBSERVATIONS][obsId]['media_info']['length'][mediaFile]
            except:
                # md5 sum of file content
                fileContentMD5 = hashfile( mediaFile , hashlib.md5())
                try:
                    mediaLength = self.pj['project_media_file_info'][fileContentMD5]['video_length']/1000
                except:
                    try:
                        instance = vlc.Instance()
                        media = instance.media_new(mediaFile)
                        media.parse()

                        mediaLength = media.get_duration()/1000
                    except:
                        totalMediaLength2 = -1
                        break

            totalMediaLength2 += Decimal(mediaLength)

        if  totalMediaLength1  == -1 or totalMediaLength2 == -1:
            totalMediaLength = -1
        else:
            totalMediaLength = max( totalMediaLength1, totalMediaLength2 )

        return totalMediaLength


    def plot_events(self):
        '''
        plot events
        '''
        try:
            import matplotlib.pyplot as plt
            import matplotlib.transforms as mtransforms
            import numpy as np
        except:
            logging.warning('matplotlib plotting library not installed')
            QMessageBox.warning(None, programName, 'The "Plot events" function requires the Matplotlib module.<br>See <a href="http://matplotlib.org">http://matplotlib.org</a>',\
            QMessageBox.Ok | QMessageBox.Default, QMessageBox.NoButton)
            return

        def plot_time_ranges(obs, obsId, videoLength):

            colors = ['blue','green','red','cyan','magenta','yellow','#7A68A6','#81b1d2','#afeeee','#FBC15E','#e5ae38','#8EBA42','#fa8174','#6d904f']
            count = 0
            lbl = []
            maxTime = 0
            for subject_idx, subject in enumerate( sorted( list(obs.keys()) )   ):
                behaviors = obs[subject]
                for k in sorted(list(behaviors.keys())):
                    lbl.append(k)
                    for t1,t2 in behaviors[k]:
                        maxTime = max(maxTime,t1,t2)
                    count += 1

            fig = plt.figure()
            fig.suptitle('Time diagram of observation {}'.format(obsId), fontsize=14)

            ax = fig.add_subplot(111)
            labels = ax.set_yticklabels(lbl)
            ax.set_xlabel('Time (s)')
            ax.set_ylabel('Behaviors')

            plt.ylim( count, -0.5)

            if not videoLength:
                videoLength = maxTime

            plt.xlim( 0, round(videoLength) + 2)

            plt.yticks(range(count + 1), np.array(lbl))

            count = 0

            for subject_idx, subject in enumerate(sorted( list(obs.keys()) )):

                ax.text(round(float(videoLength) * 0.05), count - 0.2 , subject)

                behaviors = obs[subject]

                x1, x2, y, col = [], [], [], []

                col_count = 0
                for k in sorted(list(behaviors.keys())):
                    if not behaviors[k]:
                        x1.append(0)
                        x2.append(0)
                        y.append(count)
                        col.append( colors[ col_count % len(colors) ] )
                    else:
                        for t1,t2 in behaviors[k]:
                            x1.append( t1 )
                            x2.append( t2 )
                            y.append(count)
                            col.append( colors[ col_count % len(colors) ] )
                    count += 1
                    col_count += 1

                if not y:
                    return False

                x1 = np.array(x1)
                x2 = np.array(x2)
                y = np.array(y)

                ax.hlines(y, x1, x2, lw = 10, color = col)

                ax.axhline(y=y[-1] + 0.5,linewidth=1, color='black')

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

        result, selectedObservations = self.selectObservations( SELECT1 )

        logging.debug('Selected observations: {0}'.format(selectedObservations))

        if not selectedObservations:
            return

        if not self.pj[OBSERVATIONS][ selectedObservations[0] ][EVENTS]:
            QMessageBox.warning(self, programName, 'There are no events in the selected observation')
            return

        for obsId in selectedObservations:

            if self.pj[OBSERVATIONS][ obsId ][TYPE] == MEDIA:

                totalMediaLength = self.observationTotalMediaLength( obsId )

            else: # LIVE
                if self.pj[OBSERVATIONS][ obsId ][EVENTS]:
                    totalMediaLength = max(self.pj[OBSERVATIONS][ obsId ][EVENTS])[0]
                else:
                    totalMediaLength = Decimal("0.0")

        if totalMediaLength == -1:
            totalMediaLength = 0


        logging.debug('totalMediaLength: {0}'.format(totalMediaLength))

        selectedSubjects, selectedBehaviors, includeModifiers, excludeBehaviorsWoEvents, totalMediaLength = self.choose_obs_subj_behav(selectedObservations, totalMediaLength)

        logging.debug('totalMediaLength: {0}'.format(totalMediaLength))

        if not selectedSubjects or not selectedBehaviors:
            return

        cursor = self.loadEventsInDB( selectedSubjects, selectedObservations, selectedBehaviors )

        o = {}

        for subject in selectedSubjects:

            o[subject] = {}

            for behavior in selectedBehaviors:

                if includeModifiers == YES:

                    cursor.execute( "SELECT distinct modifiers FROM events WHERE subject = ? AND code = ?", (subject, behavior) )
                    distinct_modifiers = list(cursor.fetchall() )

                    for modifier in distinct_modifiers:
                        cursor.execute( "SELECT occurence FROM events WHERE subject = ? AND code = ? AND modifiers = ? ORDER BY observation, occurence", ( subject, behavior, modifier[0] ))
                        rows = cursor.fetchall()

                        if modifier[0]:
                            behaviorOut = '{0} ({1})'.format(behavior, modifier[0].replace('|',','))
                        else:
                            behaviorOut = '{0}'.format(behavior)

                        if not behaviorOut in o[subject]:
                            o[subject][behaviorOut] = []

                        for idx, row in enumerate(rows):
                            if 'POINT' in self.eventType(behavior).upper():
                                o[subject][behaviorOut].append( [row[0],row[0] + 1] )  ### FIXME 1 second? for point event

                            if 'STATE' in self.eventType(behavior).upper():
                                if idx % 2 == 0:
                                    try:
                                        o[subject][behaviorOut].append( [ row[0], rows[idx + 1][0] ]  )
                                    except:
                                        if NO_FOCAL_SUBJECT in subject:
                                            sbj = ''
                                        else:
                                            sbj =  'for subject <b>{0}</b>'.format( subject )
                                        QMessageBox.critical(self, programName, 'The STATE behavior <b>{0}</b> is not paired{1}'.format(behaviorOut, sbj) )

                else:

                    cursor.execute( "SELECT occurence FROM events WHERE subject = ? AND code = ? ORDER BY observation, occurence", (subject, behavior) )
                    rows = list(cursor.fetchall() )

                    if not len( rows ) and excludeBehaviorsWoEvents:
                        continue

                    if 'STATE' in self.eventType(behavior).upper() and len( rows ) % 2:
                        continue

                    behaviorOut = '{0}'.format(behavior)

                    if not behaviorOut in o[subject]:
                        o[subject][behaviorOut] = []

                    for idx, row in enumerate(rows):

                        if 'POINT' in self.eventType(behavior).upper():
                            o[subject][behaviorOut].append( [row[0],row[0] + 1]  )   ### FIXME 1 second? for point event

                        if 'STATE' in self.eventType(behavior).upper():
                            if idx % 2 == 0:
                                o[subject][behaviorOut].append( [ row[0], rows[idx + 1][0] ]  )


        logging.debug('intervals: {}'.format(o))
        if not plot_time_ranges(o, selectedObservations[0], totalMediaLength):
            QMessageBox.warning(self, programName , 'Check events')



    def open_project_json(self, projectFileName):
        '''
        open project  json
        '''
        logging.info('open project: {0}'.format(projectFileName))
        if not os.path.isfile(projectFileName):
            QMessageBox.warning(self, programName , 'File not found')
            return

        s = open(projectFileName, 'r').read()

        try:
            self.pj = json.loads(s)
        except:
            QMessageBox.critical(self, programName , 'This project file seems corrupted' )
            return

        # transform time to decimal
        for obs in self.pj[OBSERVATIONS]:
            self.pj[OBSERVATIONS][obs]['time offset'] = Decimal( str(self.pj[OBSERVATIONS][obs]['time offset']) )

            for idx,event in enumerate(self.pj[OBSERVATIONS][obs][EVENTS]):
                self.pj[OBSERVATIONS][obs][EVENTS][idx][ pj_obs_fields['time'] ] = Decimal(str(self.pj[OBSERVATIONS][obs][EVENTS][idx][ pj_obs_fields['time'] ]))

        # add coding_map key to old project files
        if not 'coding_map' in self.pj:
            self.pj['coding_map'] = {}

        # add subject description
        if 'project_format_version' in self.pj:
            for idx in [x for x in self.pj[SUBJECTS]]:
                if not 'description' in self.pj[SUBJECTS][ idx ] :
                    self.pj[SUBJECTS][ idx ]['description'] = ''

        # check if project file version is newer than current BORIS project file version
        if 'project_format_version' in self.pj and Decimal(self.pj['project_format_version']) > Decimal(project_format_version):
            QMessageBox.critical(self, programName , 'This project file was created with a more recent version of BORIS.\nUpdate your version of BORIS to load it' )
            self.pj = {"time_format": "hh:mm:ss",\
            "project_date": "",\
            "project_name": "",\
            "project_description": "",\
            "subjects_conf" : {},\
            "behaviors_conf": {},\
            "observations": {} }
            return


        # check if old version  v. 0 *.obs
        if 'project_format_version' not in self.pj:

            # convert VIDEO, AUDIO -> MEDIA
            self.pj['project_format_version'] = project_format_version

            for obs in [x for x in self.pj[OBSERVATIONS]]:

                # remove 'replace audio' key
                if 'replace audio' in self.pj[OBSERVATIONS][obs]:
                    del self.pj[OBSERVATIONS][obs]['replace audio']

                if self.pj[OBSERVATIONS][obs]['type'] in ['VIDEO','AUDIO']:
                    self.pj[OBSERVATIONS][obs]['type'] = MEDIA

                # convert old media list in new one
                if len( self.pj[OBSERVATIONS][obs][FILE] ):
                    d1 = { PLAYER1:  [self.pj[OBSERVATIONS][obs][FILE][0]] }

                if len( self.pj[OBSERVATIONS][obs][FILE] ) == 2:
                    d1['2'] =  [self.pj[OBSERVATIONS][obs][FILE][1]]

                self.pj[OBSERVATIONS][obs][FILE] = d1

            # convert VIDEO, AUDIO -> MEDIA

            for idx in [x for x in self.pj['subjects_conf']]:

                key, name = self.pj[SUBJECTS][idx]
                self.pj[SUBJECTS][idx] = {'key': key, 'name': name, 'description':''}

            QMessageBox.information(self, programName , 'The project file was converted to the new format (v. %s) in use with your version of BORIS.<br>Choose a new file name for saving it.' % project_format_version)

            projectFileName = ''

        # check program version
        '''
        if 'program_version' in self.pj:
            if float(self.pj['program_version']) <  :
        '''

        self.initialize_new_project()

        self.load_obs_in_lwConfiguration()

        self.load_subjects_in_twSubjects()

        self.projectFileName = projectFileName

        self.project = True

        self.menu_options()

        self.projectChanged = False



    def open_project_activated(self):

        # check if current observation
        if self.observationId:
            response = dialog.MessageDialog(programName, 'There is a current observation. What do you want to do?', ['Close observation', 'Continue observation' ])
            if response == 'Close observation':
                self.close_observation()
            if response == 'Continue observation':
                return

        if self.projectChanged:
            response = dialog.MessageDialog(programName, 'What to do about the current unsaved project?', ['Save', 'Discard', 'Cancel'])

            if response == 'Save':
                if self.save_project_activated() == 'not saved':
                    return

            if response == 'Cancel':
                return


        fd = QFileDialog(self)
        fileName = fd.getOpenFileName(self, 'Open project', '', 'Project files (*.boris);;Old project files (*.obs);;All files (*)')

        if fileName:
            self.open_project_json(fileName)


    def initialize_new_project(self):
        '''
        initialize interface and variables for a new project
        '''
        logging.info('initialize new project')

        self.lbLogoUnito.setVisible(False)
        self.lbLogoBoris.setVisible(False)

        self.dwConfiguration.setVisible(True)
        self.dwSubjects.setVisible(True)

        self.projectChanged = True

        if self.pj['project_name']:
            self.setWindowTitle(programName + ' - ' + self.pj['project_name'])


    def close_project(self):
        '''
        close current project
        '''

        # check if current observation
        if self.observationId:
            response = dialog.MessageDialog(programName, 'There is a current observation. What do you want to do?', ['Close observation', 'Continue observation' ])
            if response == 'Close observation':
                self.close_observation()
            if response == 'Continue observation':
                return

        if self.projectChanged:
            response = dialog.MessageDialog(programName, 'What to do about the current unsaved project?', ['Save', 'Discard', 'Cancel'])

            if response == 'Save':
                if self.save_project_activated() == 'not saved':
                    return

            if response == 'Cancel':
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
        '''

        if self.timeFormat == S:

            return '%.3f' % sec

        if self.timeFormat == HHMMSS:
            return seconds2time(sec)


    def edit_project(self, mode):
        '''
        project management
        mode: new/edit
        '''

        if self.observationId:
            QMessageBox.critical(self, programName , 'Close the running observation before creating/modifying the project.' )
            return

        if mode == NEW:

            if self.projectChanged:
                response = dialog.MessageDialog(programName, 'What to do about the current unsaved project?', ['Save', 'Discard', 'Cancel'])

                if response == 'Save':
                    self.save_project_activated()

                if response == 'Cancel':
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

        newProjectWindow.obs = self.pj['behaviors_conf']
        newProjectWindow.subjects_conf = self.pj['subjects_conf']

        if self.pj['time_format'] == S:
            newProjectWindow.rbSeconds.setChecked(True)

        if self.pj['time_format'] == HHMMSS:
            newProjectWindow.rbHMS.setChecked(True)

        if mode == NEW:

            newProjectWindow.dteDate.setDateTime( QDateTime.currentDateTime() )
            newProjectWindow.lbProjectFilePath.setText( '')

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
                    if self.pj[OBSERVATIONS][obs]['type'] in [MEDIA]:
                        for idx in self.pj[OBSERVATIONS][obs][FILE]:
                            for media in self.pj[OBSERVATIONS][obs][FILE][idx]:
                                mediaList.append('#%s: %s' % (idx , media))

                    elif self.pj[OBSERVATIONS][obs]['type'] in [LIVE]:
                        mediaList = [LIVE]


                    item = QTableWidgetItem('\n'.join( mediaList ))
                    newProjectWindow.twObservations.setItem(newProjectWindow.twObservations.rowCount() - 1, 3, item)

                newProjectWindow.twObservations.resizeColumnsToContents()


            # configuration of behaviours
            if self.pj[ETHOGRAM]:

                newProjectWindow.signalMapper = QSignalMapper(self)
                newProjectWindow.comboBoxes = []

                for i in [str(x) for x in sorted([int(x) for x in self.pj[ETHOGRAM].keys() ])]:

                    newProjectWindow.twBehaviors.setRowCount(newProjectWindow.twBehaviors.rowCount() + 1)

                    for field in fields:

                        item = QTableWidgetItem()

                        if field == 'type':

                            # add combobox with event type
                            newProjectWindow.comboBoxes.append(QComboBox())
                            newProjectWindow.comboBoxes[-1].addItems(observation_types)
                            newProjectWindow.comboBoxes[-1].setCurrentIndex( observation_types.index(self.pj[ETHOGRAM][i][field]) )

                            newProjectWindow.signalMapper.setMapping(newProjectWindow.comboBoxes[-1], newProjectWindow.twBehaviors.rowCount() - 1)
                            newProjectWindow.comboBoxes[-1].currentIndexChanged['int'].connect(newProjectWindow.signalMapper.map)

                            newProjectWindow.twBehaviors.setCellWidget(newProjectWindow.twBehaviors.rowCount() - 1, fields[field], newProjectWindow.comboBoxes[-1])

                        else:
                            if field in self.pj[ETHOGRAM][i]:
                                item.setText( self.pj[ETHOGRAM][i][field] )
                            else:
                                item.setText( '' )

                            if field in ['excluded', 'coding map', 'modifiers']:
                                item.setFlags(Qt.ItemIsEnabled)

                            newProjectWindow.twBehaviors.setItem(newProjectWindow.twBehaviors.rowCount() - 1, fields[field] ,item)

                newProjectWindow.signalMapper.mapped['int'].connect(newProjectWindow.comboBoxChanged)

                newProjectWindow.twBehaviors.resizeColumnsToContents()



            # load independent variables
            if INDEPENDENT_VARIABLES in self.pj:
                for i in [str(x) for x in sorted([int(x) for x in self.pj[INDEPENDENT_VARIABLES].keys() ])]:
                    newProjectWindow.twVariables.setRowCount(newProjectWindow.twVariables.rowCount() + 1)

                    for idx, field in enumerate( tw_indVarFields ):

                        if field == 'type':

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


        newProjectWindow.dteDate.setDisplayFormat('yyyy-MM-dd hh:mm:ss')

        if mode == NEW:

            self.pj = {'time_format': HHMMSS,\
            'project_date': '', \
            'project_name': '', \
            'project_description': '', \
            SUBJECTS : {},\
            ETHOGRAM: {}, \
            OBSERVATIONS: {},
            'coding_map': {} }

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
        '''
        new project
        '''

        self.edit_project(NEW)


    def save_project_json(self, projectFileName):
        '''
        save project to JSON file
        '''
        def decimal_default(obj):
            if isinstance(obj, Decimal):
                return float(obj)
            raise TypeError

        logging.debug('save project json {0}:'.format(projectFileName))

        self.pj['project_format_version'] = project_format_version

        try:
            f = open(projectFileName, 'w')
            f.write(json.dumps(self.pj, indent=4, default=decimal_default))
            f.close()
        except:
            logging.critical( 'The project file can not be saved' )
            QMessageBox.critical(self, programName, 'The project file can not be saved!')
            return

        self.projectChanged = False



    def save_project_as_activated(self):
        '''
        save current project asking for a new file name
        '''

        fd = QFileDialog(self)
        self.projectFileName, filtr = fd.getSaveFileNameAndFilter(self, 'Save project as', os.path.dirname(self.projectFileName), 'Projects file (*.boris);;All files (*)')

        if not self.projectFileName:
            return 'Not saved'

        # add .boris if filter = 'Projects file (*.boris)'
        if  filtr == 'Projects file (*.boris)' and os.path.splitext(self.projectFileName)[1] != '.boris':
            self.projectFileName += '.boris'

        self.save_project_json(self.projectFileName)



    def save_project_activated(self):
        '''
        save current project
        '''

        if not self.projectFileName:

            fd = QFileDialog(self)

            if not self.pj['project_name']:
                txt = 'NONAME.boris'
            else:
                txt = self.pj['project_name'] + '.boris'

            os.chdir( os.path.expanduser("~")  )

            self.projectFileName, filtr = fd.getSaveFileNameAndFilter(self, 'Save project', txt, 'Projects file (*.boris);;All files (*)')

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

        currentTime = self.getLaps()

        t = seconds2time(currentTime)

        self.lbTimeLive.setText(t)

        # current state(s)

        # extract State events
        StateBehaviorsCodes = [ self.pj['behaviors_conf'][x]['code'] for x in [y for y in self.pj['behaviors_conf'] if 'State' in self.pj['behaviors_conf'][y]['type']] ]

        self.currentStates = {}

        # add states for no focal subject
        self.currentStates[ '' ] = []
        for sbc in StateBehaviorsCodes:
            if len(  [ x[ pj_obs_fields['code'] ] for x in self.pj[OBSERVATIONS][self.observationId][EVENTS ] if x[ pj_obs_fields['subject'] ] == '' and x[ pj_obs_fields['code'] ] == sbc and x[ pj_obs_fields['time'] ] <= currentTime  ] ) % 2: # test if odd
                self.currentStates[''].append(sbc)

        # add states for all configured subjects
        for idx in self.pj['subjects_conf']:

            # add subject index
            self.currentStates[ idx ] = []
            for sbc in StateBehaviorsCodes:
                if len(  [ x[ pj_obs_fields['code'] ] for x in self.pj[OBSERVATIONS][self.observationId][EVENTS ] if x[ pj_obs_fields['subject'] ] == self.pj['subjects_conf'][idx]['name'] and x[ pj_obs_fields['code'] ] == sbc and x[ pj_obs_fields['time'] ] <= currentTime  ] ) % 2: # test if odd
                    self.currentStates[idx].append(sbc)


        # show current states
        if self.currentSubject:
            # get index of focal subject (by name)
            idx = [idx for idx in self.pj['subjects_conf'] if self.pj['subjects_conf'][idx]['name'] == self.currentSubject][0]
            self.lbCurrentStates.setText(  '%s' % (', '.join(self.currentStates[ idx ])))
        else:
            self.lbCurrentStates.setText(  '%s' % (', '.join(self.currentStates[ '' ])))

        # show selected subjects

        for idx in [str(x) for x in sorted([int(x) for x in self.pj[SUBJECTS].keys() ])]:
            self.twSubjects.item(int(idx), len(subjectsFields) ).setText( ','.join(self.currentStates[idx]) )



    def start_live_observation(self):
        '''
        activate the live observation mode (without media file)
        '''

        logging.debug('start live observation, self.liveObservationStarted: {0}'.format(self.liveObservationStarted))

        if not self.liveObservationStarted:

            if self.twEvents.rowCount():
                response = dialog.MessageDialog(programName, 'The current events will be deleted. Do you want to continue?', [YES, NO])
                if response == NO:
                    return

                self.twEvents.setRowCount(0)

                self.pj[OBSERVATIONS][self.observationId][EVENTS] = []
                self.projectChanged = True
                #self.loadEventsInTW(self.observationId)



            self.liveObservationStarted = True
            self.textButton.setText('Stop live observation')

            self.liveStartTime = QTime()
            # set to now
            self.liveStartTime.start()

            # start timer
            self.liveTimer.start(100)

        else:

            self.liveObservationStarted = False
            self.textButton.setText('Start live observation')

            self.liveStartTime = None
            self.liveTimer.stop()

            self.lbTimeLive.setText('00:00:00.000')


    def create_subtitles(self):
        '''
        create subtitles for selected observations, subjects and behaviors
        '''

        result, selectedObservations = self.selectObservations( MULTIPLE )

        logging.debug('Selected observations: {0}'.format(selectedObservations))

        if not selectedObservations:
            return

        selectedSubjects, selectedBehaviors, includeModifiers, excludeBehaviorsWoEvents, _ = self.choose_obs_subj_behav(selectedObservations, 0)

        if not selectedSubjects or not selectedBehaviors:
            return

        cursor = self.loadEventsInDB( selectedSubjects, selectedObservations, selectedBehaviors )

        for obsId in selectedObservations:

            # extract file name of first video of first player

            for media in self.pj[OBSERVATIONS][ obsId ][FILE][PLAYER1]:

                if os.path.isfile( media ):
                    fileName = media + '.srt'
                else:

                    response = dialog.MessageDialog(programName, '{0} not found!\nDo you want to choose another place to save subtitles? '.format(media), [YES, NO])
                    if response == YES:
                        fd = QFileDialog(self)
                        fileName = fd.getSaveFileName(self, 'Save subtitles file', '','Subtitles files (*.srt *.txt);;All files (*)')
                        if not fileName:
                            continue
                    else:
                        continue

                # TODO add subtitle for enqueued media

                subtitles = []
                for subject in selectedSubjects:

                    for behavior in selectedBehaviors:

                        cursor.execute( "SELECT occurence, modifiers FROM events where observation = ? AND subject = ? AND  code = ? ORDER BY code, occurence", (obsId, subject, behavior) )
                        rows = list(cursor.fetchall() )
                        if 'STATE' in self.eventType(behavior).upper() and len( rows ) % 2:
                            continue

                        for idx, row in enumerate(rows):

                            # subtitle color
                            if subject == NO_FOCAL_SUBJECT:
                                col = 'white'
                            else:
                                col = subtitlesColors[  selectedSubjects.index( subject ) % len(subtitlesColors) ]

                            behaviorStr = behavior
                            if includeModifiers == YES and row[1]:
                                behaviorStr += ' ({0})'.format(row[1].replace('|',', '))

                            if 'POINT' in self.eventType(behavior).upper():
                                laps =  '{0} --> {1}'.format(seconds2time(row[0]).replace('.',','), seconds2time(row[0] + 0.5).replace('.',',') )
                                subtitles.append( [laps, '<font color="{0}">{1}: {2}</font>'.format(col, subject, behaviorStr) ] )

                            if 'STATE' in self.eventType(behavior).upper():
                                if idx % 2 == 0:
                                    laps =  '{0} --> {1}'.format(seconds2time(row[0]).replace('.',','), seconds2time(rows[idx + 1][0]).replace('.',','))
                                    subtitles.append( [laps, '<font color="{0}">{1}: {2}</font>'.format(col, subject, behaviorStr) ] )

                subtitles.sort()

                with open(fileName, 'w') as f:
                    for idx, sub in enumerate(subtitles):
                        f.write( '{0}{3}{1}{3}{2}{3}{3}'.format(idx + 1, sub[0], sub[1], os.linesep ))

        QMessageBox.information(self, programName , 'subtitles file(s) created in media files path')



    def export_aggregated_events(self, format_):
        '''
        export aggregated events in SQL (sql) or Tabular format (tab)
        '''

        result, selectedObservations = self.selectObservations( MULTIPLE )

        if not selectedObservations:
            return

        selectedSubjects, selectedBehaviors, includeModifiers, excludeBehaviorsWoEvents, _ = self.choose_obs_subj_behav(selectedObservations, 0)

        if not selectedSubjects or not selectedBehaviors:
            return

        fd = QFileDialog(self)

        if format_ == 'sql':
            fileName = fd.getSaveFileName(self, 'Export aggregated events in SQL format', '' , 'SQL dump file file (*.sql);;All files (*)')

            out = '''CREATE TABLE events (id INTEGER PRIMARY KEY ASC, observation TEXT, date DATE, subject TEXT, behavior TEXT, modifiers TEXT, event_type TEXT, start FLOAT, stop FLOAT);''' + os.linesep
            out += 'BEGIN TRANSACTION;'

            sqlTemplate = '''INSERT INTO events ( observation, date, subject, behavior, modifiers, event_type, start, stop ) VALUES ("{0}","{1}","{2}","{3}","{4}","{5}",{6},{7} );'''+ os.linesep

        if format_ == 'tab':
            fileName = fd.getSaveFileName(self, 'Export aggregated events in tabular format', '' , 'Events file (*.tsv *.txt);;All files (*)')
            out = 'Observation id{0}Observation date{0}Subject{0}Behavior{0}Modifiers{0}Behavior type{0}Start{0}Stop{1}'.format('\t', os.linesep)
            tabTemplate = '''{0}\t{1}\t{2}\t{3}\t{4}\t{5}\t{6}\t{7}'''+ os.linesep

        if not fileName:
            return

        app.processEvents()
        self.statusbar.showMessage('Exporting aggregated events', 0)
        app.processEvents()

        for obsId in selectedObservations:

            cursor = self.loadEventsInDB( selectedSubjects, selectedObservations, selectedBehaviors )

            for subject in selectedSubjects:

                for behavior in selectedBehaviors:

                    cursor.execute( "SELECT occurence, modifiers FROM events WHERE observation = ? AND subject = ? AND code = ? ", (obsId, subject, behavior) )
                    rows = list(cursor.fetchall() )

                    if 'STATE' in self.eventType(behavior).upper() and len( rows ) % 2:
                        continue

                    for idx, row in enumerate(rows):

                        if 'POINT' in self.eventType(behavior).upper():

                            if format_ == 'sql':
                                template = sqlTemplate
                            if format_ == 'tab':
                                template = tabTemplate

                            out += template.format( obsId , self.pj[OBSERVATIONS][obsId]['date'].replace('T',' '), subject, behavior, row[1], 'POINT', row[0], 0 )

                        if 'STATE' in self.eventType(behavior).upper():
                            if idx % 2 == 0:

                                if format_ == 'sql':
                                    template = sqlTemplate
                                if format_ == 'tab':
                                    template = tabTemplate

                                out += template.format( obsId, self.pj[OBSERVATIONS][obsId]['date'].replace('T',' '), subject, behavior, row[1], 'STATE', row[0],  rows[idx + 1][0] )


        if format_ == 'sql':
            out += 'END TRANSACTION;'


        with open(fileName, 'w') as f:
            f.write( out )

        self.statusbar.showMessage('Aggregated events exported successfully', 0)


    def media_file_info(self):
        '''
        show info about current video
        '''
        if self.observationId and self.playerType == VLC:
            out = ''

            if platform.system() in ['Linux', 'Darwin']:
                for idx in self.pj[OBSERVATIONS][self.observationId][FILE]:
                    for file_ in self.pj[OBSERVATIONS][self.observationId][FILE][idx]:

                        r = os.system( 'file -b ' + file_ )
                        if not r:
                            out += '<b>' + os.path.basename(file_) + '</b><br>'
                            out += subprocess.getoutput('file -b ' + file_ ) + '<br>'

            media = self.mediaplayer.get_media()
            if self.pj[OBSERVATIONS][self.observationId]['type'] in [MEDIA]:

                logging.info(('State: %s' % self.mediaplayer.get_state()))
                logging.info(('Media: %s' % bytes_to_str(media.get_mrl())))
                logging.info(('Track: %s/%s' % (self.mediaplayer.video_get_track(), self.mediaplayer.video_get_track_count())))

                logging.info('number of media in media list: %d' % self.media_list.count() )

                logging.info(('get time: %s  duration: %s' % (self.mediaplayer.get_time(), media.get_duration())))
                logging.info(('Position: %s %%' % self.mediaplayer.get_position()))
                logging.info(('FPS: %s' % (self.mediaplayer.get_fps())))
                logging.info(('Rate: %s' % self.mediaplayer.get_rate()))
                logging.info(('Video size: %s' % str(self.mediaplayer.video_get_size(0))))  # num=0
                logging.info(('Scale: %s' % self.mediaplayer.video_get_scale()))
                logging.info(('Aspect ratio: %s' % self.mediaplayer.video_get_aspect_ratio()))
                logging.info('is seekable? {0}'.format(self.mediaplayer.is_seekable()))

                QMessageBox.about(self, programName + ' - Media file information', out + '<br><br>Total duration: %s s' % (self.convertTime( sum(self.duration)/1000 )  ) )


    def switch_playing_mode(self):
        '''
        switch between frame mode and VLC mode
        triggered by frame by frame button and toolbox item change
        '''
        if self.playerType != VLC:
            return

        if self.playMode == FFMPEG:

            self.playMode = VLC

            globalCurrentTime = int( self.FFmpegGlobalFrame  * (1000/list(self.fps.values())[0]))
            logging.debug('new global current time: {0}'.format( globalCurrentTime ))

            # seek VLC on current time from FFmpeg mode
            for idx, media in enumerate(self.pj[OBSERVATIONS][self.observationId][FILE][PLAYER1]):
                if globalCurrentTime < sum(self.duration[0:idx + 1]):

                    logging.debug('idx: {0}'.format(idx))

                    self.mediaListPlayer.play_item_at_index( idx )
                    app.processEvents()
                    while self.mediaListPlayer.get_state() != vlc.State.Playing:
                        time.sleep(0.5)
                        pass

                    self.mediaListPlayer.pause()

                    currentMediaTime = int(globalCurrentTime - sum(self.duration[0:idx]))
                    break

            logging.debug('current media time: {0}'.format(   currentMediaTime ))
            self.mediaplayer.set_time( currentMediaTime )

            self.toolBox.setCurrentIndex(VIDEO_TAB)

            self.FFmpegTimer.stop()

            logging.info( 'ffmpeg timer stopped')

            # set thread for cleaning temp directory
            if self.ffmpeg_cache_dir_max_size:
                self.cleaningThread.exiting = True

            #self.timer.start()

        elif FFMPEG in self.availablePlayers:

            # second video together
            if self.simultaneousMedia:
                logging.warning( 'Frame-by-frame mode is not available in multi-player mode' )
                app.beep()
                self.actionFrame_by_frame.setChecked(False)
                self.statusbar.showMessage('Frame-by-frame mode is not available in multi-player mode', 5000)
                return

            if list(self.fps.values())[0] == 0:
                logging.warning( 'The frame per second value is not available. Frame-by-frame mode will not be available' )
                QMessageBox.critical(None, programName, 'The frame per second value is not available. Frame-by-frame mode will not be available',
                    QMessageBox.Ok | QMessageBox.Default, QMessageBox.NoButton)
                self.actionFrame_by_frame.setChecked(False)
                return

            if len(set( self.fps.values() )) != 1:
                logging.warning( 'The frame-by-frame mode will not be available because the video files have different frame rates' )
                QMessageBox.warning(self, programName, 'The frame-by-frame mode will not be available because the video files have different frame rates (%s).' % (', '.join([str(i) for i in list(self.fps.values())])),\
                    QMessageBox.Ok | QMessageBox.Default, QMessageBox.NoButton)
                self.actionFrame_by_frame.setChecked(False)
                return

            self.playMode = FFMPEG

            '''
            if self.mediaListPlayer.get_state() == vlc.State.Playing:
                self.mediaListPlayer.pause()
            '''

            self.pause_video()
            self.timer.stop()

            # check temp dir for images from ffmpeg
            if not self.ffmpeg_cache_dir:
                self.imageDirectory = tempfile.gettempdir()
            else:
                self.imageDirectory = self.ffmpeg_cache_dir

            # load list of images in a set
            if not self.imagesList:
                self.imagesList.update(  [ f.replace( self.imageDirectory + os.sep, '' ).split('_')[0] for f in glob.glob(self.imageDirectory + os.sep + '*')  ] )

            logging.debug('frame-by-frame mode activated. Image directory {0}'.format( self.imageDirectory ))

            # show frame-by_frame tab
            self.toolBox.setCurrentIndex(1)


            '''
            currentTime = self.mediaplayer.get_time()
            logging.debug('current media time {0}'.format( currentTime ))
            currentFrame = round(currentTime / 40 )
            logging.debug('current media frame {0}'.format( currentFrame ))
            '''


            globalTime = (sum(self.duration[0 : self.media_list.index_of_item(self.mediaplayer.get_media()) ]) + self.mediaplayer.get_time())
            logging.debug('globalTime {0} s'.format( globalTime/1000 ))

            fps = list(self.fps.values())[0]

            globalCurrentFrame = globalTime / (1000/fps)


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

        else:
            QMessageBox.critical(None, programName, 'The frame-by-frame mode requires the FFmpeg multimedia framework. See https://www.ffmpeg.org', QMessageBox.Ok | QMessageBox.Default, QMessageBox.NoButton)

        # enable/disable speed button
        self.actionNormalSpeed.setEnabled( self.playMode == VLC )
        self.actionFaster.setEnabled( self.playMode == VLC )
        self.actionSlower.setEnabled( self.playMode == VLC )

        logging.info( 'new play mode: {0}'.format( self.playMode ))


    def snapshot(self):
        '''
        take snapshot of current video
        snapshot is saved on media path
        '''

        if self.pj[OBSERVATIONS][self.observationId]['type'] in [MEDIA]:

            if self.playerType == VLC:

                if self.playMode == FFMPEG:

                    for idx,media in enumerate(self.pj[OBSERVATIONS][self.observationId][FILE][PLAYER1]):
                        if self.FFmpegGlobalFrame < sum(self.duration[0:idx + 1]):

                            dirName, fileName = os.path.split( media )
                            self.lbFFmpeg.pixmap().save(dirName + os.sep + os.path.splitext( fileName )[0] +  '_'+ str(self.FFmpegGlobalFrame) +'.png')
                            break

                else:  # VLC

                    current_media_path = url2path( self.mediaplayer.get_media().get_mrl() )
                    dirName, fileName = os.path.split( current_media_path )
                    time = str(self.mediaplayer.get_time())
                    self.mediaplayer.video_take_snapshot(0, dirName + os.sep + os.path.splitext( fileName )[0] +  '_'+ time +'.png' ,0,0)

                    # check if multi mode
                    # second video together
                    if self.simultaneousMedia:

                        current_media_path = url2path(self.mediaplayer2.get_media().get_mrl())

                        dirName, fileName = os.path.split( current_media_path )
                        time = str(self.mediaplayer2.get_time())
                        self.mediaplayer2.video_take_snapshot(0, dirName + os.sep + os.path.splitext( fileName )[0] +  '_'+ time +'.png' ,0,0)



    def video_normalspeed_activated(self):
        '''
        set playing speed at normal speed
        '''


        '''
        if self.playMode == FFMPEG:

            if self.FFmpegTimer.interval() > 0:
                self.FFmpegTimer.setInterval( int( 1000/list(self.fps.values())[0] )  )
            self.lbSpeed.setText('x{:.3f}'.format(1.0))

        else:
        '''
        if self.playerType == VLC and self.playMode == VLC:

            self.play_rate = 1

            self.mediaplayer.set_rate(self.play_rate)

            # second video together
            if self.simultaneousMedia:

                self.mediaplayer2.set_rate(self.play_rate)

            self.lbSpeed.setText('x{:.3f}'.format(self.play_rate))

            logging.info('play rate: {:.3f}'.format(self.play_rate))



    def video_faster_activated(self):
        '''
        increase playing speed by play_rate_step value
        '''

        '''
        if self.playMode == FFMPEG:

            if self.FFmpegTimer.interval() > 0:
                self.FFmpegTimer.setInterval( self.FFmpegTimer.interval() - 2 )
            self.lbSpeed.setText('x%.3f' %  (1/self.FFmpegTimer.interval()/ (list(self.fps.values())[0]/1000)))

        else:
        '''
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
        '''
        decrease playing speed by play_rate_step value
        '''

        '''
        if self.playMode == FFMPEG:

            if self.FFmpegTimer.interval() < 10000:
                self.FFmpegTimer.setInterval( self.FFmpegTimer.interval() + 2 )

            self.lbSpeed.setText('x%.3f' %  (1/self.FFmpegTimer.interval()/ (  list(self.fps.values())[0]/1000  )))

        else:
        '''

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
        '''
        manually add event to observation
        '''

        if not self.observationId:
            self.no_observation()
            return

        editWindow = DlgEditEvent(logging.getLogger().getEffectiveLevel())
        editWindow.setWindowTitle('Add a new event')

        # send pj to edit_event window
        editWindow.pj = self.pj

        if self.timeFormat == HHMMSS:
            editWindow.dsbTime.setVisible(False)
            editWindow.teTime.setTime(QtCore.QTime.fromString(seconds2time( self.getLaps() ), "hh:mm:ss.zzz") )

        if self.timeFormat == S:
            editWindow.teTime.setVisible(False)
            editWindow.dsbTime.setValue( float( self.getLaps() ) )


        sortedSubjects = [''] + sorted( [ self.pj['subjects_conf'][x]['name'] for x in self.pj['subjects_conf'] ])

        editWindow.cobSubject.addItems( sortedSubjects )

        sortedCodes = sorted( [ self.pj['behaviors_conf'][x]['code'] for x in self.pj['behaviors_conf'] ])

        editWindow.cobCode.addItems( sortedCodes )

        # activate signal
        #editWindow.cobCode.currentIndexChanged.connect(editWindow.codeChanged)

        editWindow.currentModifier = ''

        if editWindow.exec_():  #button OK

            if self.timeFormat == HHMMSS:
                newTime = time2seconds(editWindow.teTime.time().toString('hh:mm:ss.zzz'))

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

                    self.writeEvent( event, newTime)
                    break

            '''
            new_event = { 'time': newTime, \
            'subject': editWindow.cobSubject.currentText(), \
            'code': editWindow.cobCode.currentText() ,\
            'type': '',\
            'modifier': modifier_str,\
            'comment': editWindow.leComment.toPlainText() }

            print('new event', new_event)
            '''
            '''
            if self.checkSameEvent(self.observationId, newTime, editWindow.cobSubject.currentText(), editWindow.cobCode.currentText()):
                QMessageBox.warning(self, programName, 'The same event already exists!\nSame time, code and subject.')
                return

            self.pj[OBSERVATIONS][self.observationId][EVENTS].append( [ newTime, editWindow.cobSubject.currentText(),  editWindow.cobCode.currentText() , modifier_str, editWindow.leComment.toPlainText()]  )

            self.pj[OBSERVATIONS][self.observationId][EVENTS].sort()

            self.loadEventsInTW( self.observationId )

            # get item from twEvents at memTime row position
            item = self.twEvents.item(  [i for i,t in enumerate( self.pj[OBSERVATIONS][self.observationId][EVENTS] ) if t[0] == memTime][0], 0  )

            self.twEvents.scrollToItem( item )

            self.projectChanged = True
            '''




    def edit_event(self):
        '''
        edit each event items from the selected row
        '''
        if not self.observationId:
            self.no_observation()
            return

        if self.twEvents.selectedItems():

            editWindow = DlgEditEvent(logging.getLogger().getEffectiveLevel())
            editWindow.setWindowTitle('Edit event parameters')

            # pass project to window
            editWindow.pj = self.pj
            editWindow.currentModifier = ''

            row = self.twEvents.selectedItems()[0].row()

            if self.timeFormat == HHMMSS:
                editWindow.dsbTime.setVisible(False)
                editWindow.teTime.setTime(QtCore.QTime.fromString(seconds2time( self.pj[OBSERVATIONS][self.observationId][EVENTS][row][ 0 ] ), "hh:mm:ss.zzz") )

            if self.timeFormat == S:
                editWindow.teTime.setVisible(False)
                editWindow.dsbTime.setValue( self.pj[OBSERVATIONS][self.observationId][EVENTS][row][ 0 ] )

            sortedSubjects = [''] + sorted( [ self.pj[SUBJECTS][x]['name'] for x in self.pj[SUBJECTS] ])

            editWindow.cobSubject.addItems( sortedSubjects )

            if self.pj[OBSERVATIONS][self.observationId][EVENTS][row][ pj_obs_fields['subject'] ] in sortedSubjects:
                editWindow.cobSubject.setCurrentIndex( sortedSubjects.index( self.pj[OBSERVATIONS][self.observationId][EVENTS][row][ pj_obs_fields['subject'] ] ) )
            else:
                QMessageBox.warning(self, programName, 'The subject <b>%s</b> do not exists more in the subject\'s list' %   self.pj[OBSERVATIONS][self.observationId][EVENTS][row][ pj_obs_fields['subject'] ]  )
                editWindow.cobSubject.setCurrentIndex( 0 )

            sortedCodes = sorted( [ self.pj['behaviors_conf'][x]['code'] for x in self.pj['behaviors_conf'] ])

            editWindow.cobCode.addItems( sortedCodes )

            # check if selected code is in code's list (no modification of codes)
            if self.pj[OBSERVATIONS][self.observationId][EVENTS][row][ pj_obs_fields['code'] ] in sortedCodes:
                editWindow.cobCode.setCurrentIndex( sortedCodes.index( self.pj[OBSERVATIONS][self.observationId][EVENTS][row][ pj_obs_fields['code'] ] ) )
            else:
                logging.warning("The code <b>{0}</b> do not exists more in the code's list".format(self.pj[OBSERVATIONS][self.observationId][EVENTS][row][ pj_obs_fields['code'] ] ) )
                QMessageBox.warning(self, programName, "The code <b>%s</b> do not exists more in the code's list" % self.pj[OBSERVATIONS][self.observationId][EVENTS][row][ pj_obs_fields['code'] ])
                editWindow.cobCode.setCurrentIndex( 0 )


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
                    newTime = time2seconds(editWindow.teTime.time().toString('hh:mm:ss.zzz'))

                if self.timeFormat == S:
                    newTime = editWindow.dsbTime.value()

                for obs_idx in self.pj[ETHOGRAM]:

                    if self.pj[ETHOGRAM][obs_idx]['code'] == editWindow.cobCode.currentText():
                        event = self.full_event(obs_idx)
                        event['subject'] = editWindow.cobSubject.currentText()
                        event['comment'] = editWindow.leComment.toPlainText()
                        event['row'] = row
                        self.writeEvent( event, newTime)
                        break


                # check mod type (QPushButton or QDialog)
                """
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
                """

                """
                self.pj[OBSERVATIONS][self.observationId][EVENTS][row] = [newTime, editWindow.cobSubject.currentText(),
                 editWindow.cobCode.currentText(),
                  modifier_str ,
                  editWindow.leComment.toPlainText()]

                self.pj[OBSERVATIONS][self.observationId][EVENTS].sort()
                self.loadEventsInTW( self.observationId )
                """

        else:
            QMessageBox.warning(self, programName, 'Select an event to edit')


    def no_media(self):
        QMessageBox.warning(self, programName, 'There is no media available')


    def no_project(self):
        QMessageBox.warning(self, programName, 'There is no project')


    def no_observation(self):
        QMessageBox.warning(self, programName, 'There is no current observation')


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
        ''' open user guide URL'''
        QDesktopServices.openUrl(QUrl('http://boris.readthedocs.org'))

    def actionAbout_activated(self):
        ''' about window '''

        if __version__ == 'DEV':
            ver = 'DEVELOPMENT VERSION'
        else:
            ver = 'v. {0}'.format(__version__)

        players = []
        players.append( "VLC media player v. {0}".format( bytes_to_str(vlc.libvlc_get_version())))

        if FFMPEG in self.availablePlayers:
            players.append("FFmpeg for frame-by-frame mode")

        QMessageBox.about(self, "About " + programName,"""<b>{prog_name}</b> {ver} - {date}
        <p>Copyright &copy; 2012-2015 Olivier Friard - Marco Gamba<br>
        Department of Life Sciences and Systems Biology - University of Torino - Italy<br>
        <br>
        The author would like to acknowledge Sergio Castellano, Valentina Matteucci and Laura Ozella for their precious help.<br>
        <br>
        See <a href="http://penelope.unito.it/boris">penelope.unito.it/boris</a> for more details.<br>
        <p>Python {python_ver} - Qt {qt_ver} - PyQt4 {pyqt_ver} on {system}<br><br>
        Available media players:<br>{players}""".format( prog_name=programName,
         ver=ver, date=__version_date__, python_ver=platform.python_version(),
         pyqt_ver=PYQT_VERSION_STR, system=platform.system(), qt_ver=QT_VERSION_STR,
         players='<br>'.join(players)))


    def hsVideo_sliderMoved(self):
        '''
        media position slider moved
        adjust media position
        '''

        if self.pj[OBSERVATIONS][self.observationId]['type'] in [MEDIA]:

            if self.playerType == VLC and self.playMode == VLC:

                sliderPos = self.hsVideo.value() / (slider_maximum - 1)

                videoPosition = sliderPos * self.mediaplayer.get_length()

                self.mediaplayer.set_time( int(videoPosition) )

                # second video together
                # TODO: add second video offset
                if self.simultaneousMedia:

                    if videoPosition <= self.mediaplayer2.get_length():
                        self.mediaplayer2.set_time( int(videoPosition) )
                    else:
                        self.mediaplayer2.set_time( self.mediaplayer2.get_length() )

                self.timer_out(scrollSlider=False)


    def get_events_current_row(self):
        '''
        get events current row corresponding to video/frame-by-frame position
        paint twEvents with tracking cursor
        scroll to corresponding event
        '''

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



    def timer_out(self, scrollSlider=True):
        '''
        indicate the video current position and total length for VLC player
        scroll video slider to video position
        Time offset is NOT added!
        triggered by timer
        '''

        if self.pj[OBSERVATIONS][self.observationId]['type'] in [MEDIA]:

            # cumulative time
            currentTime = self.getLaps() * 1000

            # current media time
            mediaTime = self.mediaplayer.get_time()

            #highlight current event in tw events and scroll event list
            self.get_events_current_row()

            # check if second video
            if self.simultaneousMedia:

                if TIME_OFFSET_SECOND_PLAYER in self.pj[OBSERVATIONS][self.observationId]:

                    if self.pj[OBSERVATIONS][self.observationId][TIME_OFFSET_SECOND_PLAYER] > 0:

                        if mediaTime < self.pj[OBSERVATIONS][self.observationId][TIME_OFFSET_SECOND_PLAYER] *1000:

                            if self.mediaListPlayer2.get_state() == vlc.State.Playing:

                                self.mediaplayer2.set_time( 0 )
                                self.mediaListPlayer2.pause()
                        else:
                            if self.mediaListPlayer.get_state() == vlc.State.Playing:
                                self.mediaListPlayer2.play()

                    mediaTime2 = self.mediaplayer2.get_time()
                    if self.pj[OBSERVATIONS][self.observationId][TIME_OFFSET_SECOND_PLAYER] < 0:

                        if mediaTime2 < abs(self.pj[OBSERVATIONS][self.observationId][TIME_OFFSET_SECOND_PLAYER] *1000):

                            if self.mediaListPlayer.get_state() == vlc.State.Playing:

                                self.mediaplayer.set_time( 0 )
                                self.mediaListPlayer.pause()
                        else:
                            if self.mediaListPlayer2.get_state() == vlc.State.Playing:
                                self.mediaListPlayer.play()


            currentTimeOffset = Decimal(currentTime /1000) + Decimal(self.pj[OBSERVATIONS][self.observationId][TIME_OFFSET])

            totalGlobalTime = sum(self.duration)

            if self.mediaplayer.get_length():

                self.mediaTotalLength = self.mediaplayer.get_length() / 1000

                # current state(s)

                # extract State events
                StateBehaviorsCodes = [ self.pj['behaviors_conf'][x]['code'] for x in [y for y in self.pj['behaviors_conf'] if 'STATE' in self.pj['behaviors_conf'][y]['type'].upper()] ]

                self.currentStates = {}

                # add states for no focal subject
                self.currentStates[ '' ] = []
                for sbc in StateBehaviorsCodes:
                    if len(  [ x[ pj_obs_fields['code'] ] for x in self.pj[OBSERVATIONS][self.observationId][EVENTS ] if x[ pj_obs_fields['subject'] ] == '' and x[ pj_obs_fields['code'] ] == sbc and x[ pj_obs_fields['time'] ] <= currentTimeOffset  ] ) % 2: # test if odd
                        self.currentStates[''].append(sbc)

                # add states for all configured subjects
                for idx in self.pj['subjects_conf']:

                    # add subject index
                    self.currentStates[ idx ] = []
                    for sbc in StateBehaviorsCodes:
                        if len(  [ x[ pj_obs_fields['code'] ] for x in self.pj[OBSERVATIONS][self.observationId][EVENTS ] if x[ pj_obs_fields['subject'] ] == self.pj['subjects_conf'][idx]['name'] and x[ pj_obs_fields['code'] ] == sbc and x[ pj_obs_fields['time'] ] <= currentTimeOffset  ] ) % 2: # test if odd
                            self.currentStates[idx].append(sbc)

                # show current states
                cm = {}
                if self.currentSubject:
                    # get index of focal subject (by name)
                    idx = [idx for idx in self.pj['subjects_conf'] if self.pj['subjects_conf'][idx]['name'] == self.currentSubject][0]
                else:
                    idx = ''

                txt = []
                for cs in self.currentStates[idx]:
                    for ev in self.pj[OBSERVATIONS][self.observationId][EVENTS ]:
                        if ev[0] > currentTimeOffset :   # time
                            break

                        if ev[1] == self.currentSubject:   # subject
                            if ev[2] == cs:       # code
                                cm[cs] = ev[3]    # current modifier for current state
                    # state and modifiers (if any)
                    txt.append( cs + (' (%s) ' %  cm[cs])*(cm[cs] != '') )

                txt = ', '.join(txt)

                # remove key code
                self.lbCurrentStates.setText( re.sub(' \(.\)', '', txt) )

                # show selected subjects
                for idx in [str(x) for x in sorted([int(x) for x in self.pj[SUBJECTS].keys() ])]:
                    self.twSubjects.item(int(idx), len( subjectsFields ) ).setText( ','.join(self.currentStates[idx]) )

                # update status bar
                msg = ''

                if self.mediaListPlayer.get_state() == vlc.State.Playing or self.mediaListPlayer.get_state() == vlc.State.Paused:
                    msg = '%s: <b>%s / %s</b>' % ( self.mediaplayer.get_media().get_meta(0),\
                                                   self.convertTime(Decimal(mediaTime / 1000)  ),\
                                                   self.convertTime(Decimal(self.mediaplayer.get_length() / 1000) ) )

                    if self.media_list.count() > 1:
                        msg += ' | total: <b>%s / %s</b>' % ( (self.convertTime( Decimal(currentTime/1000) ),\
                                                               self.convertTime( Decimal(totalGlobalTime / 1000) ) ) )
                    if self.mediaListPlayer.get_state() == vlc.State.Paused:
                        msg += ' (paused)'

                if msg:
                    # show time on status bar
                    self.lbTime.setText( msg )

                    # set video scroll bar
                    if scrollSlider:
                        self.hsVideo.setValue(mediaTime / self.mediaplayer.get_length() * (slider_maximum - 1))

            else:

                self.statusbar.showMessage('Media length not available now', 0)



    def load_obs_in_lwConfiguration(self):
        '''
        fill ethogram table with ethogram from pj
        '''

        self.twConfiguration.setRowCount(0)

        if self.pj[ETHOGRAM]:

            for idx in [str(x) for x in sorted([int(x) for x in self.pj[ETHOGRAM].keys() ])]:

                self.twConfiguration.setRowCount(self.twConfiguration.rowCount() + 1)

                for col, field in enumerate(['key','code','type','description','modifiers','excluded']):
                    self.twConfiguration.setItem(self.twConfiguration.rowCount() - 1, col , QTableWidgetItem( self.pj[ETHOGRAM][idx][field] ))


    def load_subjects_in_twSubjects(self):
        '''
        fill subjects table widget with subjects from self.subjects_conf
        '''

        self.twSubjects.setRowCount(0)


        for idx in [str(x) for x in sorted([int(x) for x in self.pj[SUBJECTS].keys() ])]:

            self.twSubjects.setRowCount(self.twSubjects.rowCount() + 1)

            for idx2, field in enumerate( subjectsFields ):
                self.twSubjects.setItem(self.twSubjects.rowCount() - 1, idx2 , QTableWidgetItem( self.pj[SUBJECTS][ idx ][field] ))

            # add cell for current state(s) after last subject field
            self.twSubjects.setItem(self.twSubjects.rowCount() - 1, len(subjectsFields) , QTableWidgetItem( '' ))



    def update_events_start_stop(self):
        '''
        update status start/stop of events
        take consideration of subject
        '''

        stateEventsList = [ self.pj['behaviors_conf'][x]['code'] for x in self.pj['behaviors_conf'] if STATE in self.pj['behaviors_conf'][x]['type'].upper() ]

        for row in range(0, self.twEvents.rowCount()):

            t = self.twEvents.item(row, tw_obs_fields['time'] ).text()

            if ':' in t:
                time = time2seconds(t)
            else:
                time = Decimal(t)

            code = self.twEvents.item(row, tw_obs_fields['code'] ).text()
            subject = self.twEvents.item(row, tw_obs_fields['subject'] ).text()

            # check if code is state
            if code in stateEventsList:

                # how many code before with same subject?
                '''
                for x in self.pj[OBSERVATIONS][self.observationId][EVENTS ] :

                    if x[ pj_obs_fields['code'] ] == code and x[ pj_obs_fields['time'] ]  < time and x[ pj_obs_fields['subject'] ] == subject:
                        pass
                '''

                if len(  [ x[ pj_obs_fields['code'] ] for x in self.pj[OBSERVATIONS][self.observationId][EVENTS ] if x[ pj_obs_fields['code'] ] == code and x[ pj_obs_fields['time'] ]  < time and x[ pj_obs_fields['subject'] ] == subject]) % 2: # test if odd

                    self.twEvents.item(row, tw_obs_fields['type'] ).setText('STOP')
                else:
                    self.twEvents.item(row, tw_obs_fields['type'] ).setText('START')


    def update_events_start_stop2(self, events):
        '''
        returns events with status (START/STOP or POINT)
        take consideration of subject
        '''


        stateEventsList = [ self.pj[ETHOGRAM][x]['code'] for x in self.pj[ETHOGRAM] if STATE in self.pj[ETHOGRAM][x]['type'].upper() ]

        eventsFlagged = []
        for event in events:

            time, subject, code = event[0:3]

            # check if code is state
            if code in stateEventsList:

                # how many code before with same subject?
                if len( [ x[ pj_obs_fields['code'] ] for x in events if x[ pj_obs_fields['code'] ] == code and x[ pj_obs_fields['time'] ]  < time and x[ pj_obs_fields['subject'] ] == subject]) % 2: # test if odd
                    flag = 'STOP'
                else:
                    flag = 'START'

            else:
                flag = 'POINT'

            eventsFlagged.append(event + [flag])

        return eventsFlagged


    def checkSameEvent(self, obsId, time, subject, code ):
        '''
        check if a same event is already in events list (time, subject, code)
        '''
        return [ time, subject, code ] in [[x[0],x[1],x[2]] for x in self.pj[OBSERVATIONS][obsId][EVENTS]]



    def writeEvent(self, event, memTime):
        '''
        add event from pressed key to observation

        offset is added to event time

        ask for modifiers if configured
        '''

        logging.debug('write event - event: {0}'.format( event ))

        # add time offset
        memTime += Decimal(self.pj[OBSERVATIONS][self.observationId][TIME_OFFSET]).quantize(Decimal('.001'))

        # check if a same event is already in events list (time, subject, code)
        if not 'row' in event and self.checkSameEvent( self.observationId, memTime, self.currentSubject, event['code'] ):
            QMessageBox.warning(self, programName, 'The same event already exists!\nSame time, code and subject.')
            return

        if not 'from map' in event:   # modifiers only for behaviors without coding map
            # check if event has modifiers
            modifier_str = ''

            if event['modifiers']:

                # pause media
                if self.pj[OBSERVATIONS][self.observationId]['type'] in [MEDIA]:

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
                if '|' in event['modifiers']:
                    modifiersStringsList = event['modifiers'].split('|')
                    for modifiersString in modifiersStringsList:
                        modifiersList.append([s.strip() for s in modifiersString.split(',')])

                else:
                    modifiersList.append([s.strip() for s in event['modifiers'].split(',')])

                modifierSelector = select_modifiers.ModifiersRadioButton(event['code'], modifiersList, '', 'normal')

                if modifierSelector.exec_():
                    modifiers = modifierSelector.getModifiers()
                    if len(modifiers) == 1:
                        modifier_str = modifiers[0]
                        if modifier_str == 'None':
                            modifier_str = ''
                    else:
                        modifier_str = '|'.join( modifiers )

                # restart media
                if self.pj[OBSERVATIONS][self.observationId]['type'] in [MEDIA]:

                    if self.playerType == VLC:

                        if self.playMode == FFMPEG:
                            if memState:
                                self.play_video()
                        else:

                            if memState == vlc.State.Playing:
                                self.play_video()

        else:
            modifier_str = event['from map']

        # update current state
        if not 'row' in event:
            if self.currentSubject:
                csj = []
                for idx in self.currentStates:
                    if idx in self.pj[SUBJECTS] and self.pj[SUBJECTS][idx]['name'] == self.currentSubject:
                        csj = self.currentStates[idx]
                        break

            else:  # no focal subject

                csj = self.currentStates['']

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

                if (event['excluded']  and cs in event['excluded'].split(',') ) or ( event['code'] == cs and  cm[cs] != modifier_str) :
                    # add excluded state event to observations (= STOP them)
                    self.pj[OBSERVATIONS][self.observationId][EVENTS].append( [memTime - Decimal('0.001'), self.currentSubject, cs, cm[cs], ''] )


        # remove key code from modifiers
        modifier_str = re.sub(' \(.\)', '', modifier_str)

        if 'comment' in event:
            comment = event['comment']
        else:
            comment = ''

        if 'subject' in event:
            subject = event['subject']
        else:
            subject = self.currentSubject

        # add event to pj
        if 'row' in event:
            self.pj[OBSERVATIONS][self.observationId][EVENTS][event['row']] =  [memTime, subject, event['code'], modifier_str, comment]
        else:
            self.pj[OBSERVATIONS][self.observationId][EVENTS].append( [memTime, subject, event['code'], modifier_str, comment] )

        # sort events in pj
        self.pj[OBSERVATIONS][self.observationId][EVENTS].sort()

        # reload all events in tw
        """
        self.twEvents.setRowCount(0)
        for idx,o in enumerate(self.pj[OBSERVATIONS][self.observationId][EVENTS]):

            self.twEvents.setRowCount(self.twEvents.rowCount() + 1)

            # time
            item = QTableWidgetItem( self.convertTime(o[ 0 ] ) )

            self.twEvents.setItem(self.twEvents.rowCount() - 1, 0, item)
            # subject
            item = QTableWidgetItem( o[ 1 ]  )
            self.twEvents.setItem(self.twEvents.rowCount() - 1, 1, item)
            # code
            item = QTableWidgetItem( o[ 2 ]  )
            self.twEvents.setItem(self.twEvents.rowCount() - 1, 2, item)

            # type
            item = QTableWidgetItem( ''  )
            self.twEvents.setItem(self.twEvents.rowCount() - 1, 3, item)

            # modifier
            item = QTableWidgetItem( o[ 3 ] )
            self.twEvents.setItem(self.twEvents.rowCount() - 1, 4, item)

            # comment
            item = QTableWidgetItem( o[ 4 ]  )
            self.twEvents.setItem(self.twEvents.rowCount() - 1, 5, item)

        self.update_events_start_stop()
        """
        self.loadEventsInTW(self.observationId)

        item = self.twEvents.item(  [i for i,t in enumerate( self.pj[OBSERVATIONS][self.observationId][EVENTS] ) if t[0] == memTime][0], 0  )

        self.twEvents.scrollToItem( item )

        self.projectChanged = True




    def fill_lwDetailed(self, obs_key, memLaps):
        '''
        fill listwidget with all events coded by key
        return index of behaviour
        '''

        # check if key duplicated
        items = []
        for idx in self.pj[ETHOGRAM]:
            if self.pj[ETHOGRAM][idx]['key'] == obs_key:

                txt = self.pj[ETHOGRAM][idx]['code']
                if  self.pj[ETHOGRAM][idx]['description']:
                    txt += ' - ' + self.pj[ETHOGRAM][idx]['description']
                items.append(txt)

                self.detailedObs[txt] = idx

        response = ''

        item, ok = QInputDialog.getItem(self, programName, 'The <b>' + obs_key + '</b> key codes more events.<br>Choose the correct one:' , items, 0, False)

        if ok and item:
            obs_idx = self.detailedObs[ item ]
            return obs_idx

        else:

            return None


    def getLaps(self):
        '''
        return cumulative laps time from begining of observation

        as Decimal in seconds

        no more add time offset!

        '''

        if self.pj[OBSERVATIONS][self.observationId]['type'] in [LIVE]:

            if self.liveObservationStarted:
                now = QTime()
                now.start()
                memLaps = Decimal(str(round( self.liveStartTime.msecsTo(now) / 1000, 3)))

                return memLaps

            else:

                QMessageBox.warning(self, programName, 'The live observation is not started')
                return None


        if self.pj[OBSERVATIONS][self.observationId]['type'] in [MEDIA]:

            if self.playerType == VLC:

                if self.playMode == FFMPEG:
                    # cumulative time

                    '''
                    memLaps = Decimal( self.FFmpegGlobalFrame * ( 1000 / self.fps.values()[0]) / 1000).quantize(Decimal('.001')) \
                              + Decimal(self.pj[OBSERVATIONS][self.observationId][TIME_OFFSET]).quantize(Decimal('.001'))
                    '''

                    memLaps = Decimal( self.FFmpegGlobalFrame * ( 1000 / list(self.fps.values())[0]) / 1000).quantize(Decimal('.001'))

                    return memLaps

                else: # playMode == VLC

                    # cumulative time
                    memLaps = Decimal(str(round(( sum(self.duration[0 : self.media_list.index_of_item(self.mediaplayer.get_media()) ]) \
                              + self.mediaplayer.get_time()) / 1000 ,3))) \

                    '''
                    memLaps = Decimal(str(round(( sum(self.duration[0 : self.media_list.index_of_item(self.mediaplayer.get_media()) ]) \
                              + self.mediaplayer.get_time()) / 1000 ,3))) \
                              + self.pj[OBSERVATIONS][self.observationId][TIME_OFFSET]
                    '''
                    return memLaps

    def full_event(self, obs_idx):
        '''
        ask modifiers from coding if configured and add them under 'from map' key
        '''

        event = dict( self.pj[ETHOGRAM][obs_idx] )
        # check if coding map
        if 'coding map' in self.pj[ETHOGRAM][obs_idx] and self.pj[ETHOGRAM][obs_idx]['coding map']:

            # pause if media and media playing
            if self.pj[OBSERVATIONS][self.observationId]['type'] in [MEDIA]:
                if self.playerType == VLC:
                    memState = self.mediaListPlayer.get_state()
                    if memState == vlc.State.Playing:
                        self.pause_video()

            self.codingMapWindow = coding_map.codingMapWindowClass( self.pj['coding_map'][ self.pj[ETHOGRAM][obs_idx]['coding map'] ] )

            self.codingMapWindow.resize(640, 640)
            if self.codingMapWindowGeometry:
                 self.codingMapWindow.restoreGeometry( self.codingMapWindowGeometry )

            if not self.codingMapWindow.exec_():
                return

            self.codingMapWindowGeometry = self.codingMapWindow.saveGeometry()

            event['from map'] = self.codingMapWindow.getCodes()

            # restart media
            if self.pj[OBSERVATIONS][self.observationId]['type'] in [MEDIA]:

                if self.playerType == VLC:
                    if memState == vlc.State.Playing:
                        self.play_video()

        return event



    def keyPressEvent(self, event):
        '''
        if (event.modifiers() & Qt.ShiftModifier):   # SHIFT

        QApplication.keyboardModifiers()

        http://qt-project.org/doc/qt-5.0/qtcore/qt.html#Key-enum

        ESC: 16777216
        '''

        '''print("focus", window.focusWidget() )'''

        if not self.observationId:
            return

        # beep
        if self.confirmSound:
            app.beep()

        if self.playerType == 'VIEWER':
            QMessageBox.critical(self, programName, 'The current observation is opened in VIEW mode.\nIt is not allowed to log events in this mode.')
            return

        # check if media ever played

        if self.playerType == VLC:
            if self.mediaListPlayer.get_state() == vlc.State.NothingSpecial:
                return

        ek = event.key()

        logging.debug('key event {0}'.format( ek ))

        if ek in [16777248, 16777249, 16777217, 16781571]: # shift tab ctrl
            return

        if ek == 16777216: # ESC
            self.switch_playing_mode()
            return

        # play / pause with space bar
        if ek == Qt.Key_Space and self.pj[OBSERVATIONS][self.observationId]['type'] in [MEDIA]:
            if self.mediaListPlayer.get_state() != vlc.State.Paused:
                self.pause_video()
            else:
                self.play_video()
            return

        if self.playMode == FFMPEG:
            if ek == 47 or ek == Qt.Key_Left:   # /   one frame back
                logging.debug('current frame {0}'.format( self.FFmpegGlobalFrame ))
                if self.FFmpegGlobalFrame > 1:
                    self.FFmpegGlobalFrame -= 2
                    newTime = 1000.0 * self.FFmpegGlobalFrame / list(self.fps.values())[0]
                    self.FFmpegTimerOut()
                    logging.debug('new frame {0}'.format( self.FFmpegGlobalFrame ))
                return

            if ek == 42 or ek == Qt.Key_Right:  # *  read next frame
                logging.debug('(next) current frame {0}'.format( self.FFmpegGlobalFrame ))
                self.FFmpegTimerOut()
                logging.debug('(next) new frame {0}'.format( self.FFmpegGlobalFrame ))
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
            flag_function = True
            if function_keys[ ek ] in [self.pj[ETHOGRAM][x]['key'] for x in self.pj[ETHOGRAM]]:
                obs_key = function_keys[ek]
        else:
            flag_function = False

        # get video time
        memLaps = self.getLaps()
        if memLaps == None:
            return

        if (ek in function_keys) or ((ek in range(33, 256)) and (ek not in [Qt.Key_Plus, Qt.Key_Minus])):

            obs_idx = -1
            count = 0

            if (ek in function_keys):
                ek_unichr = function_keys[ek]
            else:
                ek_unichr = chr(ek)

            for o in self.pj[ETHOGRAM]:

                if self.pj[ETHOGRAM][o]['key'] == ek_unichr:
                    obs_idx = o
                    count += 1

            # check if key codes more events
            if count > 1:

                flagPlayerPlaying = False
                if self.pj[OBSERVATIONS][self.observationId]['type'] in [MEDIA]:
                    if self.playerType == VLC:
                        if self.mediaListPlayer.get_state() != vlc.State.Paused:
                            flagPlayerPlaying = True
                            self.pause_video()

                # let user choose event
                obs_idx = self.fill_lwDetailed( ek_unichr, memLaps)

                if obs_idx:
                    count = 1

                if self.pj[OBSERVATIONS][self.observationId]['type'] in [MEDIA] and flagPlayerPlaying:
                    self.play_video()

            if count == 1:

                # check if focal subject is defined
                if not self.currentSubject and self.alertNoFocalSubject:

                    flagPlayerPlaying = False
                    if self.pj[OBSERVATIONS][self.observationId]['type'] in [MEDIA]:
                        if self.playerType == VLC:
                            if self.mediaListPlayer.get_state() != vlc.State.Paused:
                                flagPlayerPlaying = True
                                self.pause_video()

                    response = dialog.MessageDialog(programName, 'The focal subject is not defined. Do you want to continue?\nUse Preferences menu option to modify this behaviour.', [YES, NO])

                    if self.pj[OBSERVATIONS][self.observationId]['type'] in [MEDIA] and flagPlayerPlaying:
                        self.play_video()

                    if response == NO:
                        return
                """
                event = dict( self.pj[ETHOGRAM][obs_idx] )
                # check if coding map
                if 'coding map' in self.pj[ETHOGRAM][obs_idx] and self.pj[ETHOGRAM][obs_idx]['coding map']:

                    # pause if media and media playing
                    if self.pj[OBSERVATIONS][self.observationId]['type'] in [MEDIA]:
                        if self.playerType == VLC:
                            memState = self.mediaListPlayer.get_state()
                            if memState == vlc.State.Playing:
                                self.pause_video()

                    self.codingMapWindow = coding_map.codingMapWindowClass( self.pj['coding_map'][ self.pj[ETHOGRAM][obs_idx]['coding map'] ] )

                    self.codingMapWindow.resize(640, 640)
                    if self.codingMapWindowGeometry:
                         self.codingMapWindow.restoreGeometry( self.codingMapWindowGeometry )

                    if not self.codingMapWindow.exec_():
                        return

                    self.codingMapWindowGeometry = self.codingMapWindow.saveGeometry()

                    event['from map'] = self.codingMapWindow.getCodes()

                    # restart media
                    if self.pj[OBSERVATIONS][self.observationId]['type'] in [MEDIA]:

                        if self.playerType == VLC:
                            if memState == vlc.State.Playing:
                                self.play_video()
                """

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


                    self.statusbar.showMessage( 'Key not assigned (%s)' % ek_unichr , 5000)


        # coding map
        '''
        if ek == 16777216:    # ESC

            # pause if media and media playing
            if self.pj[OBSERVATIONS][self.observationId]['type'] in [MEDIA]:
                if self.playerType == VLC:
                    memState = self.mediaListPlayer.get_state()
                    if memState == vlc.State.Playing:
                        self.pause_video()
                if self.playerType == OPENCV:
                    memState = self.FFmpegTimerOut.isActive()
                    if memState:
                        self.pause_video()

            self.codingMap = coding_map.codingMapWindow('prova_map.boris_map')
            self.codingMap.resize(640, 640)
            self.codingMap.exec_()
            print 'returned', self.codingMap.getCodes()


            self.writeEvent({ "code": self.codingMap.getCodes(), "key": "map","modifiers": "", "excluded":"", "type": "Point event"}, memLaps)

            # restart media
            if self.pj[OBSERVATIONS][self.observationId]['type'] in [MEDIA]:

                if self.playerType == VLC:
                    if memState == vlc.State.Playing:
                        self.play_video()

                if self.playerType == OPENCV:
                    if memState:
                        self.play_video()
        '''



    def twEvents_doubleClicked(self):
        '''
        seek video to double clicked position ( add self.repositioningTimeOffset value)
        substract time offset if any
        '''

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
                        self.mediaplayer2.set_time( int(newTime) )

                else: # more media in player 1

                    # remember if player paused (go previous will start playing)
                    flagPaused = self.mediaListPlayer.get_state() == vlc.State.Paused

                    tot = 0
                    for idx, d in enumerate(self.duration):
                        if newTime >= tot and newTime < tot+d:
                            self.mediaListPlayer.play_item_at_index(idx)

                            # wait until media is played
                            while self.mediaListPlayer.get_state() != vlc.State.Playing:
                                pass

                            if flagPaused:
                                self.mediaListPlayer.pause()

                            self.mediaplayer.set_time( newTime -  sum(self.duration[0 : self.media_list.index_of_item(self.mediaplayer.get_media()) ]))

                            break
                        tot += d

                self.timer_out()


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
        FIXME select events between a time interval
        '''

        '''
        QMessageBox.warning(self, programName, 'Not available yet!')
        return
        '''

        def timeRegExp(s):
            '''
            extract time from 01:23:45.678
            '''
            pattern = r'\d{1,2}:\d{1,2}'
            if '.' in s:
                pattern += r'.\d{1,3}'
            if from_.count(':') == 2:
                pattern = r'\d{1,2}:' + pattern
            re_r = re.findall(pattern, s)
            if re_r:
                r_str = re_r[0]
                if not '.' in r_str:
                    r_str += '.000'
                if r_str.count(':') ==1:
                    r_str = '00:' + r_str
                return r_str
            else:
                return ''



        if self.twEvents.rowCount():
            text, ok = QInputDialog.getText(self, 'Select observations from interval', 'Interval: (example: 12.5-14.7 or 2:45.780-3:15.120 )' , QLineEdit.Normal,  '')

            if ok and text != '':

                if not '-' in text:
                    QMessageBox.critical(self, programName, 'Use - to separate initial value from final value')
                    return

                from_, to_ = text.split('-')[0:2]

                if ':' in from_:
                    from_time = timeRegExp(from_)
                    if from_time:
                        from_sec = time2seconds(from_time)
                    else:
                        QMessageBox.critical(self, programName, 'Time value not recognized: %s' % from_ )
                else:
                    try:
                        from_sec = Decimal(from_)
                    except InvalidOperation:
                        QMessageBox.critical(self, programName, 'Time value not recognized: %s' % from_ )

                if ':' in to_:
                    to_time = timeRegExp(to_)
                    if to_time:
                        to_sec = time2seconds(to_time)
                    else:
                        QMessageBox.critical(self, programName, 'Time value not recognized: %s' % to_ )
                else:
                    try:
                        to_sec = Decimal(to_)
                    except InvalidOperation:
                        QMessageBox.critical(self, programName, 'Time value not recognized: %s' % to_ )



                if to_sec < from_sec:
                    QMessageBox.critical(self, programName, 'The initial time is greater than the final time')
                    return

                self.twEvents.clearSelection()
                self.twEvents.setSelectionMode( QAbstractItemView.MultiSelection )
                for r in range(0, self.twEvents.rowCount()):

                    if ':' in self.twEvents.item(r, 0).text():
                        time = time2seconds( self.twEvents.item(r, 0).text() )
                    else:
                        time = Decimal(self.twEvents.item(r, 0).text())

                    if time >= from_sec and time <= to_sec:
                        self.twEvents.selectRow(r)

        else:
            QMessageBox.critical(self, programName, 'There are no events to select')



    def delete_all_events(self):
        '''
        delete all events in current observation
        '''

        if not self.observationId:
            self.no_observation()
            return

        response = dialog.MessageDialog(programName, 'Do you really want to delete all events from the current observation?', [YES, NO])

        if response == YES:
            self.pj[OBSERVATIONS][self.observationId][EVENTS] = []
            self.projectChanged = True
            self.loadEventsInTW(self.observationId)

            '''
            self.twEvents.setRowCount(0)
            self.projectChanged = True
            self.update_observations()
            '''



    def delete_selected_events(self):
        '''
        delete selected observations
        '''

        if not self.observationId:
            self.no_observation()
            return

        if not self.twEvents.selectedIndexes():
            QMessageBox.warning(self, programName, 'No event selected!')
        else:
            # list of rows to delete (set for unique)
            rows = set( [ item.row() for item in self.twEvents.selectedIndexes() ])

            self.pj[OBSERVATIONS][self.observationId][EVENTS] = [ event for idx,event in enumerate(self.pj[OBSERVATIONS][self.observationId][EVENTS]) if not idx in rows]

            self.projectChanged = True

            self.loadEventsInTW( self.observationId )


    def export_tabular_events(self, outputFormat):
        '''
        export events from selected observations in various formats: ODS, TSV, XLS
        '''

        def complete(l, max):
            '''
            complete list with empty string until len = max
            '''
            while len(l) < max:
                l.append('')
            return l

        # ask user observations to analyze
        result, selected_observations = self.selectObservations( MULTIPLE )

        if not selected_observations:
            return

        # filter subjects in observations
        observed_subjects = self.extract_observed_subjects( selected_observations )

        # ask user subject to export
        selected_subjects = self.select_subjects( observed_subjects )

        if not selected_subjects:
            return

        if len(selected_observations) > 1:  # choose directory for exporting more observations
            fd = QFileDialog(self)
            exportDir = fd.getExistingDirectory(self, "Choose a directory to export events", os.path.expanduser('~'), options=fd.ShowDirsOnly)
            if not exportDir:
                return

        for obsId in selected_observations:

            if len(selected_observations) == 1:
                fd = QFileDialog(self)

                if outputFormat == 'tsv':
                    defaultFilter = "Tab Separated Values (*.tsv);;All files (*)"

                if outputFormat == 'ods':
                    defaultFilter = 'Open Document Spreadsheet (*.ods);;All files (*)'

                if outputFormat == 'xls':
                    defaultFilter = 'Microsoft Excel (*.xls);;All files (*)'

                defaultName = obsId + '.' + outputFormat

                fileName = fd.getSaveFileName(self, 'Export events', defaultName , defaultFilter)
                if not fileName:
                    return
            else:
                fileName = exportDir + os.sep + safeFileName(obsId) + '.'+outputFormat

            eventsWithStatus =  self.update_events_start_stop2( self.pj[OBSERVATIONS][obsId][EVENTS] )

            max_modifiers = 0
            for event in eventsWithStatus:
                for c in pj_events_fields:
                    if c == 'modifier' and event[pj_obs_fields[c]]:
                        max_modifiers = max( max_modifiers, len(event[pj_obs_fields[c]].split('|')) )

            # media file number
            mediaNb = 0
            if self.pj[OBSERVATIONS][obsId]['type'] in [MEDIA]:
                for idx in self.pj[OBSERVATIONS][obsId][FILE]:
                    for media in self.pj[OBSERVATIONS][obsId][FILE][idx]:
                        mediaNb += 1

            rows = []

            # observation id
            rows.append( ['Observation id', obsId] )
            rows.append( [''] )

            # media file name
            if self.pj[OBSERVATIONS][obsId]['type'] in [MEDIA]:
                rows.append( ['Media file(s)'] )
            else:
                rows.append(['Live observation'])
            rows.append( [''] )

            if self.pj[OBSERVATIONS][obsId]['type'] in [MEDIA]:

                for idx in self.pj[OBSERVATIONS][obsId][FILE]:
                    for media in self.pj[OBSERVATIONS][obsId][FILE][idx]:
                        rows.append( [ 'Player #{0}'.format(idx), media ] )
            rows.append( [''] )

            # date
            if "date" in self.pj[OBSERVATIONS][obsId]:
                rows.append([ 'Observation date', self.pj[OBSERVATIONS][obsId]["date"].replace('T',' ') ])
            rows.append( [''] )

            # description
            if "description" in self.pj[OBSERVATIONS][obsId]:
                rows.append( [ 'Description', eol2space(self.pj[OBSERVATIONS][obsId]["description"]) ] )
            rows.append( [''] )

            # time offset
            if "time offset" in self.pj[OBSERVATIONS][obsId]:
                rows.append(  [ 'Time offset (s)', self.pj[OBSERVATIONS][obsId]["time offset"] ])
            rows.append( [''] )


            # independant variables
            if "independent_variables" in self.pj[OBSERVATIONS][obsId]:
                rows.append( [ 'independent variables' ])

                rows.append( [ 'variable', 'value' ] )

                for variable in self.pj[OBSERVATIONS][obsId]["independent_variables"]:
                    rows.append(  [ variable, self.pj[OBSERVATIONS][obsId]["independent_variables"][variable] ])

            rows.append( [''] )

            # write header
            col = 0
            header = []
            for c in pj_events_fields:
                if c == 'modifier':
                    for x in range(1, max_modifiers + 1):
                        header.append('Modifier %d' % x )
                else:
                    header.append( c )

            header.append( 'status' )
            rows.append( header )

            out = ''
            for event in eventsWithStatus:

                if (event[ pj_obs_fields['subject'] ] in selected_subjects) \
                   or (event[ pj_obs_fields['subject'] ] == '' and NO_FOCAL_SUBJECT in selected_subjects):

                    col = 0
                    fields = []
                    for c in pj_events_fields:

                        if c == 'modifier':
                            if event[pj_obs_fields[c]]:
                                modifiers = event[pj_obs_fields[c]].split('|')
                                while len(modifiers) < max_modifiers:
                                    modifiers.append('')

                                for m in modifiers:
                                    fields.append( m )
                            else:
                                for dummy in range(max_modifiers):
                                    fields.append( '' )

                        elif c == 'time':
                            fields.append( float( event[pj_obs_fields[c]]) )

                        elif c == 'comment':
                            fields.append( event[pj_obs_fields[c]].replace(os.linesep, ' ') )

                        else:
                            fields.append( event[pj_obs_fields[c]] )

                    # append status START/STOP
                    fields.append( event[-1] )

                    rows.append( fields )

            maxLen = max( [len(r) for r in rows] )
            data = tablib.Dataset()
            data.title = obsId

            for row in rows:
                data.append( complete( row, maxLen ) )

            if outputFormat == 'tsv':
                with open(fileName,'w') as f:
                    f.write(data.tsv)
            if outputFormat == 'ods':
                with open(fileName,'wb') as f:
                    f.write(data.ods)
            if outputFormat == 'xls':
                with open(fileName,'wb') as f:
                    f.write(data.xls)

            del data



    def export_string_events(self):
        '''
        export events from selected observations by subject in string format to plain text file
        behaviors are separated by pipe character (|) for use with BSA (see http://penelope.unito.it/bsa)
        '''

        # ask user to select observations
        result, selected_observations = self.selectObservations( MULTIPLE )

        if not selected_observations:
            return

        logging.debug('observations to export: {0}'.format( selected_observations))

        # filter subjects in observations
        observedSubjects = self.extract_observed_subjects( selected_observations )

        # ask user subject to analyze
        selected_subjects = self.select_subjects( observedSubjects )

        logging.debug('selected subjects: {0}'.format(selected_subjects))

        if not selected_subjects:
            return

        fd = QFileDialog(self)
        fileName = fd.getSaveFileName(self, "Export events as strings", "","Events file (*.txt *.tsv);;All files (*)")

        if fileName:
            f = open(fileName, "w")

            for obsId in selected_observations:

                # observation id
                f.write("# observation id: {0}{1}".format(obsId, os.linesep) )

                # observation descrition
                f.write("# observation description: {0}{1}".format(self.pj[OBSERVATIONS][obsId]['description'].replace(os.linesep,' ' ), os.linesep) )

                # media file name
                if self.pj[OBSERVATIONS][obsId]['type'] in [MEDIA]:

                    f.write('# Media file name: {0}{1}{1}'.format(', '.join(   [ os.path.basename(x) for x in self.pj[OBSERVATIONS][obsId][FILE][PLAYER1]  ]  ), os.linesep ) )

                if self.pj[OBSERVATIONS][obsId]['type'] in [LIVE]:
                    f.write('# Live observation{0}{0}'.format(os.linesep))

            for subj in selected_subjects:


                if subj:
                    subj_str = '{0}{1}:{0}'.format(os.linesep, subj)

                else:
                    subj_str = '{0}No focal subject:{0}'.format(os.linesep)

                f.write(subj_str)

                for obs in selected_observations:
                    s = ''

                    for event in self.pj[OBSERVATIONS][obs][EVENTS]:
                        if event[ pj_obs_fields['subject'] ] == subj or (subj == NO_FOCAL_SUBJECT and event[ pj_obs_fields['subject'] ] == ''):
                            s += event[ pj_obs_fields['code'] ] + self.behaviouralStringsSeparator

                    # remove last separator (if separator not empty)
                    if self.behaviouralStringsSeparator:
                        s = s[0 : -len(self.behaviouralStringsSeparator)]

                    if s:

                        f.write( s + os.linesep)

            f.close()

        else:
            return




    def closeEvent(self, event):
        '''
        check if current project is saved and close program
        '''
        if self.projectChanged:
            response = dialog.MessageDialog(programName, 'What to do about the current unsaved project?', ['Save', 'Discard', 'Cancel'])

            if response == 'Save':
                if self.save_project_activated() == 'not saved':
                    event.ignore()

            if response == 'Cancel':
                event.ignore()

        self.saveConfigFile()


    def actionQuit_activated(self):
        self.close()



    def import_observations(self):
        '''
        import events from file
        '''

        self.statusbar.showMessage('Function not yet implemented', 5000)



    def play_video(self):
        '''
        play video
        '''

        if self.playerType == VLC:

            if self.playMode == FFMPEG:

                self.FFmpegTimer.start()

            else:

                self.mediaListPlayer.play()

                # second video together
                if self.simultaneousMedia:
                    self.mediaListPlayer2.play()

                self.timer.start(200)


    def pause_video(self):
        '''
        pause media
        '''

        if self.playerType == VLC:

            if self.playMode == FFMPEG:
                self.FFmpegTimer.stop()
            else:

                if self.mediaListPlayer.get_state() != vlc.State.Paused:

                    self.mediaListPlayer.pause()  # play if paused
                    logging.debug('player #1 state: {0}'.format(self.mediaListPlayer.get_state()))

                    # second video together
                    if self.simultaneousMedia:
                        self.mediaListPlayer2.pause()
                        logging.debug('player #2 state {0}'.format(  self.mediaListPlayer2.get_state()))

                    self.timer.stop()



    def play_activated(self):
        '''
        button 'play' activated
        '''
        if self.observationId and self.pj[OBSERVATIONS][self.observationId]['type'] in [MEDIA]:
            self.play_video()


    def jumpBackward_activated(self):
        '''
        rewind from current position
        '''
        if self.playerType == VLC:

            if self.playMode == FFMPEG:

                currentTime = self.FFmpegGlobalFrame / list(self.fps.values())[0]

                logging.debug('currentTime %f' % currentTime)
                logging.debug('new time %f' % (currentTime - self.fast))
                logging.debug('new frame %d ' % int((currentTime - self.fast )  * list(self.fps.values())[0]))

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
                        self.mediaplayer.set_time(0)

                    # second video together
                    if self.simultaneousMedia:
                        if self.mediaplayer2.get_time() >= self.fast * 1000:

                            self.mediaplayer2.set_time( self.mediaplayer2.get_time() - self.fast * 1000 )

                        else:
                            self.mediaplayer2.set_time(0)

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

                logging.debug('currentTime %f' % currentTime)
                logging.debug('new time %f' % (currentTime + self.fast))
                logging.debug('new frame %d ' % int((currentTime + self.fast )  * list(self.fps.values())[0]))

                self.FFmpegGlobalFrame =  int((currentTime + self.fast )  * list(self.fps.values())[0])

                self.FFmpegTimerOut()

            else:

                if self.media_list.count() == 1:

                    logging.debug('get time {0}'.format(self.mediaplayer.get_time() ))
                    logging.debug('self.fast {0}'.format(self.fast ))

                    if self.mediaplayer.get_time() >= self.mediaplayer.get_length() - self.fast * 1000:
                        self.mediaplayer.set_time(self.mediaplayer.get_length())
                    else:
                        self.mediaplayer.set_time( self.mediaplayer.get_time() + self.fast * 1000 )

                    logging.debug('player 1 done')

                    # second video together
                    if self.simultaneousMedia:

                        if self.mediaplayer2.get_time() >= self.mediaplayer2.get_length() - self.fast * 1000:
                            self.mediaplayer2.set_time(self.mediaplayer2.get_length())
                        else:
                            self.mediaplayer2.set_time( self.mediaplayer2.get_time() + self.fast * 1000 )

                        logging.debug('player 2 done')


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



if __name__=="__main__":

    # check if argument
    from optparse import OptionParser
    usage = "usage: %prog [options]"
    parser = OptionParser(usage=usage)

    parser.add_option("-d", "--debug", action = "store_true", default = False, dest = "debug", help = "Verbose mode for debugging")
    parser.add_option("-v", "--version", action = "store_true", default = False, dest = "version", help = "Print version")

    (options, args) = parser.parse_args()

    if options.version:
        print('version: {0}'.format(__version__))
        sys.exit(0)

    app = QApplication(sys.argv)
    #app.setStyle("cleanlooks")

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
    try:
        import vlc
        availablePlayers.append(VLC)
    except:
        logging.critical('VLC media player not found')
        QMessageBox.critical(None, programName, 'This program requires the VLC media player.<br>Go to http://www.videolan.org/vlc',\
            QMessageBox.Ok | QMessageBox.Default, QMessageBox.NoButton)
        sys.exit(1)

    logging.info('VLC version %s' % vlc.libvlc_get_version().decode('utf-8'))
    if vlc.libvlc_get_version().decode('utf-8') < VLC_MIN_VERSION:
        QMessageBox.critical(None, programName, 'The VLC media player seems very old (%s).<br>Go to http://www.videolan.org/vlc to update it' \
            % vlc.libvlc_get_version(), QMessageBox.Ok | QMessageBox.Default, QMessageBox.NoButton)
        logging.critical('The VLC media player seems a little bit old (%s). Go to http://www.videolan.org/vlc to update it' % vlc.libvlc_get_version())
        sys.exit(2)


    app.setApplicationName(programName)
    window = MainWindow(availablePlayers)

    if __version__ == 'DEV':
        QMessageBox.warning(None, programName, 'This version is a DEVELOPMENT version and must be used only for testing.\nPlease report all bugs', \
            QMessageBox.Ok | QMessageBox.Default, QMessageBox.NoButton)

    if args:
        logging.debug('args[0]: ' + os.path.abspath(args[0]))
        window.open_project_json( os.path.abspath(args[0]) )

    window.show()
    window.raise_()
    splash.finish(window)

    sys.exit(app.exec_())
