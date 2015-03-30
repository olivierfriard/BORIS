#!/usr/bin/env python

from __future__ import division
from __future__ import print_function

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

__version__ = '2.03'
__version_date__ = '2015-03-30'
__RC__ = ''

function_keys = {16777264: 'F1',16777265: 'F2',16777266: 'F3',16777267: 'F4',16777268: 'F5', 16777269: 'F6', 16777270: 'F7', 16777271: 'F8', 16777272: 'F9', 16777273: 'F10',16777274: 'F11', 16777275: 'F12'}

slider_maximum = 1000

import sys
import logging

logging.basicConfig(level=logging.DEBUG)

try:
    from PySide.QtCore import *
    from PySide.QtGui import *
except:
    print('PySide not installed! See http://qt-project.org/wiki/PySide')
    sys.exit()

import qrc_boris

from config import *

video, live = 0, 1

import time
import os
from encodings import hex_codec
import json
from decimal import *
import re
import urlparse
import hashlib
import commands
import sqlite3


import subprocess as sp

import dialog

from boris_ui import *

from edit_event import *

from project import *
import preferences
import observation
import coding_map
import map_creator
import select_modifiers
from time_utilities import *


import obs_list2

import svg

import PySide.QtNetwork
import PySide.QtWebKit


def hashfile(fileName, hasher, blocksize=65536):
    '''
    return hash of file content
    '''
    with open(fileName) as afile:
        buf = afile.read(blocksize)
        while len(buf) > 0:
            hasher.update(buf)
            buf = afile.read(blocksize)
    return hasher.hexdigest()
    
    



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


def accurate_video_analysis(ffmpeg_bin, fileName):
    '''
    analyse frame rate and tiem of video with ffmpeg
    '''

    command2 = '%s -i %s -f image2pipe -qscale 31 - > /dev/null' % (ffmpeg_bin, fileName)

    p = sp.Popen(command2, stdout=sp.PIPE, stderr=sp.PIPE, shell=True )

    error = p.communicate()[1]

    rows = error.split('\r')
    out = ''
    for rowIdx in range(len(rows)-1, 0, -1):
        if 'frame=' in rows[rowIdx]:
            out = rows[rowIdx]
            break
    if out:
        nframe = int(out.split(' fps=')[0].replace('frame=','').strip())
        timeStr = out.split('time=')[1].split(' ')[0].strip()
        time = time2seconds(timeStr) * 1000

        return nframe, time
    else:
        return None, None


class ThreadSignal(QObject):
    sig = Signal(int, float, str)

class Process(QThread):
    '''
    process for accurate video analysis
    '''

    def __init__(self, parent = None):
        QThread.__init__(self, parent)
        #self.exiting = False
        self.videoPath = ''
        self.ffmpeg_bin = ''
        self.obsId = ''
        self.signal = ThreadSignal()

    def run(self):

        nframe, videoTime = accurate_video_analysis( self.ffmpeg_bin, self.videoPath )
        self.signal.sig.emit(nframe, videoTime, self.obsId)




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
        for idx in xrange(self.lw.count()):
            self.lw.itemWidget(self.lw.item(idx)).setChecked(True)

    def pbUnSelectAll_clicked(self):
        '''uncheck all items'''
        for idx in xrange(self.lw.count()):
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



class MainWindow(QMainWindow, Ui_MainWindow):

    DEBUG = False

    pj = {"time_format": HHMMSS, "project_date": "", "project_name": "", "project_description": "", "subjects_conf" : {}, "behaviors_conf": {}, OBSERVATIONS: {} , 'coding_map':{} }
    project = False

    observationId = ''   ### current observation id

    timeOffset = 0.0

    confirmSound = False          ### if True each keypress will be confirmed by a beep
    embedPlayer = True            ### if True the VLC player will be embedded in the main window
    alertNoFocalSubject = False   ### if True an alert will show up if no focal subject

    timeFormat = HHMMSS       ### 's' or 'hh:mm:ss'
    repositioningTimeOffset = 0

    #ObservationsChanged = False
    projectChanged = False

    liveObservationStarted = False

    projectFileName = ''
    mediaTotalLength = None

    automaticBackup = 0

    behaviouralStringsSeparator = '|'

    duration = []

    simultaneousMedia = False ### if second player was created

    ### time laps
    fast = 10

    currentStates = {}
    flag_slow = False
    play_rate = 1

    play_rate_step = 0.1

    currentSubject = ''  ### contains the current subject of observation

    detailedObs = {}

    codingMapWindowGeometry = 0
    
    projectWindowGeometry = 0   ### memorize size of project window
    
    imageDirectory = ''
    
    # FFmpeg
    allowFrameByFrame = False

    # path for ffmpeg/ffmpeg.exe program
    ffmpeg_bin = ''
    ffmpeg_cache_dir = ''
    ffmpeg_cache_dir_max_size = 0

    # dictionary for FPS storing
    fps = {}
    
    playMode = VLC
    
    cleaningThread = TempDirCleanerThread()


    def __init__(self, availablePlayers , parent = None):

        super(MainWindow, self).__init__(parent)
        self.setupUi(self)

        #self.playerType = ''
        self.availablePlayers = availablePlayers
        self.installEventFilter(self)
        ### set icons
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
        
        self.lbFocalSubject.setText( 'No focal subject' )
        
        font = QFont()
        font.setPointSize(15)
        self.lbFocalSubject.setFont(font)
        self.lbCurrentStates.setFont(font)

        # add label to status bar
        self.lbTime = QLabel()
        self.lbTime.setFrameStyle(QFrame.StyledPanel)
        self.lbTime.setMinimumWidth(160)

        # current subjects
        self.lbSubject = QLabel()
        self.lbSubject.setFrameStyle(QFrame.StyledPanel)
        self.lbSubject.setMinimumWidth(160)

        # time offset
        self.lbTimeOffset = QLabel()
        self.lbTimeOffset.setFrameStyle(QFrame.StyledPanel)
        self.lbTimeOffset.setMinimumWidth(160)

        # speed
        self.lbSpeed = QLabel()
        self.lbSpeed.setFrameStyle(QFrame.StyledPanel)
        self.lbSpeed.setMinimumWidth(40)

        self.statusbar.addPermanentWidget(self.lbTime)
        self.statusbar.addPermanentWidget(self.lbSubject)

        self.statusbar.addPermanentWidget(self.lbTimeOffset)
        self.statusbar.addPermanentWidget(self.lbSpeed)

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



    def create_ffmpeg_tab(self):
        
        pass
        #self.toolBox.setItemEnabled (1, True)



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
        self.actionMedia_file_information.setEnabled(flag)
        self.menuCreate_subtitles_2.setEnabled(flag)

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
        #self.menuCreate_subtitles_2.setEnabled(flagObs)
        
        self.actionJumpForward.setEnabled( flagObs)
        self.actionJumpBackward.setEnabled( flagObs)
        self.actionJumpTo.setEnabled( flagObs)
        self.actionPlay.setEnabled( flagObs)
        self.actionPause.setEnabled( flagObs)
        self.actionReset.setEnabled( flagObs)
        self.actionFaster.setEnabled( flagObs)        
        self.actionSlower.setEnabled( flagObs)
        self.actionNormalSpeed.setEnabled( flagObs)        
        self.actionPrevious.setEnabled( flagObs)
        self.actionNext.setEnabled( flagObs)
        self.actionSnapshot.setEnabled( flagObs)

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
        self.actionNew_observation.triggered.connect(self.new_observation)
        self.actionOpen_observation.triggered.connect(self.open_observation)
        self.actionObservationsList.triggered.connect(self.observations_list)
        
        self.actionClose_observation.triggered.connect(self.close_observation)
                

        self.actionAdd_event.triggered.connect(self.add_event)
        self.actionEdit_event.triggered.connect(self.edit_event)

        self.actionSelect_observations.triggered.connect(self.select_events_between_activated)

        self.actionDelete_all_observations.triggered.connect(self.delete_all_events)
        self.actionDelete_selected_observations.triggered.connect(self.delete_selected_events)


        self.actionLoad_observations_file.triggered.connect(self.import_observations)
        self.actionExportEventTabular.triggered.connect(self.export_tabular_events)
        self.actionODS_format.triggered.connect(self.export_tabular_events_ods)

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
        self.twConfiguration.itemDoubleClicked.connect(self.twConfiguration_doubleClicked)
        self.twSubjects.itemDoubleClicked.connect(self.twSubjects_doubleClicked)

        # toolbox
        '''self.toolBox.currentChanged.connect( self.switch_playing_mode )'''

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
        result, selectedObs = self.selectObservations( OPEN )

        if selectedObs:
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
        
                    self.new_observation( EDIT, selectedObs[0])   # observation id to edit
                else:
                    QMessageBox.warning(self, programName , 'The observation <b>%s</b> is running!<br>Close it before editing.' % self.observationId)
                

    def actionCheckUpdate_activated(self):
        
        '''
        check BORIS web site for updates
        '''
        try:
            import urllib2
            msg = 'The version you are using is the last one: <b>%s</b>' %  __version__

            if __RC__:
                msg += '<b> RC%s</b>' % __RC__

                versionURL = 'http://penelope.unito.it/boris/static/ver.rc.dat'
                newRCdate, newRCversion = urllib2.urlopen( versionURL ).read().strip().split(':')
                if newRCdate > __version_date__:
                    msg = 'A new Release Candidate is available: <b>RC%s</b><br>Go to <a href="http://penelope.unito.it/boris">http://penelope.unito.it/boris</a> to install it.<br><br>Remember to report all bugs you will find! ;-)' % newRCversion

            else:
                versionURL = 'http://penelope.unito.it/boris/static/ver.dat'
                lastVersion = Decimal(urllib2.urlopen( versionURL ).read().strip())

                if lastVersion > Decimal(__version__):
                    msg = 'A new version is available: v. <b>%s</b><br>Go to <a href="http://penelope.unito.it/boris">http://penelope.unito.it/boris</a> to install it.' % str(lastVersion)

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
                            
                            self.mediaplayer.set_time( newTime -  sum(self.duration[0 : self.media_list.index_of_item(self.mediaplayer.get_media()) ]))
                            
                            break
                        tot += d
                else:
                    QMessageBox.warning(self, programName , 'The indicated position is behind the total media duration (%s)' % seconds2time(sum(self.duration)/1000))


    def previous_media_file(self):
        '''
        go to previous media file (if any)
        '''
        if self.playerType == VLC:

            if self.playMode == FFMPEG:
    
                currentMedia = ''
                
                
                for idx,media in enumerate(self.pj[OBSERVATIONS][self.observationId]['file']['1']):
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
                self.mediaplayer.video_set_spu(0)



    def next_media_file(self):
        '''
        go to next media file (if any)
        '''
        if self.playerType == VLC:

            if self.playMode == FFMPEG:
    
                for idx,media in enumerate(self.pj[OBSERVATIONS][self.observationId]['file']['1']):
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
                    
                    self.mediaListPlayer.next()
    
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
                self.mediaplayer.video_set_spu(0)






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
        self.lbSubject.setText( 'No focal subject' )
        self.lbFocalSubject.setText( 'No focal subject' )        


    def selectSubject(self, subject):
        '''
        deselect the current subject
        '''
        self.currentSubject = subject
        self.lbSubject.setText( 'Subject: %s' % (self.currentSubject))
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

        # frame by frame
        preferencesWindow.cbAllowFrameByFrameMode.setChecked( self.allowFrameByFrame )
        
        preferencesWindow.pbBrowseFFmpeg.setEnabled( preferencesWindow.cbAllowFrameByFrameMode.isChecked() )
        preferencesWindow.lbFFmpeg.setEnabled( preferencesWindow.cbAllowFrameByFrameMode.isChecked() )
        preferencesWindow.leFFmpegPath.setEnabled( preferencesWindow.cbAllowFrameByFrameMode.isChecked() )

        preferencesWindow.pbBrowseFFmpegCacheDir.setEnabled( preferencesWindow.cbAllowFrameByFrameMode.isChecked() )
        preferencesWindow.lbFFmpegCacheDir.setEnabled( preferencesWindow.cbAllowFrameByFrameMode.isChecked() )
        preferencesWindow.leFFmpegCacheDir.setEnabled( preferencesWindow.cbAllowFrameByFrameMode.isChecked() )

        preferencesWindow.lbFFmpegCacheDirMaxSize.setEnabled( preferencesWindow.cbAllowFrameByFrameMode.isChecked() )
        preferencesWindow.sbFFmpegCacheDirMaxSize.setEnabled( preferencesWindow.cbAllowFrameByFrameMode.isChecked() )

        preferencesWindow.leFFmpegPath.setText( self.ffmpeg_bin )
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
        FFMPEG mode:
        read next frame and update image
        '''

        logging.debug('FFmpegTimerOut function')


        fps = self.fps.values()[0]
        
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


        for idx, media in enumerate(self.pj[OBSERVATIONS][self.observationId]['file']['1']):
            if requiredFrame *frameMs < sum(self.duration[0:idx + 1 ]):
                currentMedia = media
                currentIdx = idx
                frameCurrentMedia = requiredFrame - sum(self.duration[0:idx]) / frameMs
                break

        md5FileName = hashlib.md5(currentMedia).hexdigest()


        logging.debug('imagesList {0}'.format( self.imagesList ))

        logging.debug('image {0}'.format( '%s-%d' % (md5FileName, int(frameCurrentMedia/ fps)) ))

        #if not '%s-%d' % (md5FileName, int(frameCurrentMedia/ fps)) in self.imagesList:
        if True:

            # extract frames for 1 second from current position

            ffmpeg_command = '%(ffmpeg_bin)s -ss %(pos)d -loglevel quiet -i "%(currentMedia)s" -vframes %(fps)s -qscale:v 2 "%(imageDir)s%(sep)sBORIS_%(fileName)s-%(pos)d_%%d.%(extension)s"' \
            % {'ffmpeg_bin': self.ffmpeg_bin,
            'pos': int(frameCurrentMedia/ fps),
            'currentMedia': currentMedia,
            'fps': str(round(fps) +1),
            'imageDir': self.imageDirectory,
            'sep': os.sep,
            'fileName': md5FileName,
            'extension': 'jpg'
            }
            #ffmpeg_command = self.ffmpeg_bin + ' -ss %d  -loglevel quiet -i %s -vframes '+ str(int(fps)) +' -qscale:v 2 '+ self.imageDirectory + os.sep +  md5FileName +'-%d_%%d.jpg' 

            #command = ffmpeg_command % (int(frameCurrentMedia/ fps), currentMedia,  int(frameCurrentMedia / fps) )

            logging.debug('ffmpeg command: {0}'.format( ffmpeg_command ))

            #os.system(ffmpeg_command)

            p = subprocess.Popen( ffmpeg_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True )
            out, error = p.communicate()
            
            logging.debug('ffmpeg error: {0}'.format( error ))

            self.imagesList.update( [ '%s-%d' % (md5FileName, int(frameCurrentMedia/ fps)) ] )

        logging.debug('frame current media: {0}'.format( frameCurrentMedia ))
        
        

        img = '%(imageDir)s%(sep)sBORIS_%(fileName)s-%(second)d_%(frame)d.%(extension)s' % \
              {'imageDir': self.imageDirectory, 'sep': os.sep, 'fileName': md5FileName, 'second':  int(frameCurrentMedia / fps),
               'frame':( frameCurrentMedia - int(frameCurrentMedia / fps)*fps)+1,
               'extension': 'jpg'}

        #img = self.imageDirectory + os.sep + '%s-%d-%d.%s' % ( md5FileName, int(frameCurrentMedia / 25), ( frameCurrentMedia - int(frameCurrentMedia / 25)*25)+1 , 'jpg' )

        if not os.path.isfile(img):
            logging.warning('image not found: {0}'.format( img ))
            return


        pixmap = QtGui.QPixmap( img )

        self.lbFFmpeg.setPixmap( pixmap.scaled(self.lbFFmpeg.size(), Qt.KeepAspectRatio))
        

        self.FFmpegGlobalFrame = requiredFrame
       
        currentTime = self.getLaps() * 1000

        self.lbTime.setText( '%s frame: %d' % ( self.convertTime( currentTime /1000), self.FFmpegGlobalFrame))

        # extract State events
        StateBehaviorsCodes = [ self.pj['behaviors_conf'][x]['code'] for x in [y for y in self.pj['behaviors_conf']
                                if 'State' in self.pj['behaviors_conf'][y]['type']] ]

        self.currentStates = {}
        
        # add states for no focal subject
        self.currentStates[ '' ] = []
        for sbc in StateBehaviorsCodes:
            if len(  [ x[ pj_obs_fields['code'] ] for x in self.pj[OBSERVATIONS][self.observationId][EVENTS ]
                       if x[ pj_obs_fields['subject'] ] == '' and x[ pj_obs_fields['code'] ] == sbc and x[ pj_obs_fields['time'] ] <= currentTime /1000 ] ) % 2: ### test if odd
                self.currentStates[''].append(sbc)

        # add states for all configured subjects
        for idx in self.pj[SUBJECTS]:

            # add subject index
            self.currentStates[ idx ] = []
            for sbc in StateBehaviorsCodes:
                if len( [ x[ pj_obs_fields['code'] ] for x in self.pj[OBSERVATIONS][self.observationId][EVENTS ] 
                           if x[ pj_obs_fields['subject'] ] == self.pj[SUBJECTS][idx]['name'] and x[ pj_obs_fields['code'] ] == sbc and x[ pj_obs_fields['time'] ] <= currentTime / 1000 ] ) % 2: ### test if odd
                    self.currentStates[idx].append(sbc)

        # show current states
        if self.currentSubject:
            # get index of focal subject (by name)
            idx = [idx for idx in self.pj[SUBJECTS] if self.pj[SUBJECTS][idx]['name'] == self.currentSubject][0]
            self.lbCurrentStates.setText(  '%s' % (', '.join(self.currentStates[ idx ]))) 
        else:
            self.lbCurrentStates.setText(  '%s' % (', '.join(self.currentStates[ '' ]))) 

        # show selected subjects
        for idx in sorted( self.pj[SUBJECTS].keys() ):

            self.twSubjects.item(int(idx), len( subjectsFields ) ).setText( ','.join(self.currentStates[idx]) )


    def processCompleted(self, nframe, videoTime, obsId):
        
        if not nframe:
            QMessageBox.critical(self, programName, 'BORIS is not able to determine the frame rate of the video even after accurate analysis.\nCheck your video.', QMessageBox.Ok | QMessageBox.Default, QMessageBox.NoButton)
            return False

        self.statusbar.showMessage('', 0)            
        QMessageBox.information(self, programName,'Video analysis done ( %s - %d frames )\nOpen the observation again.' % (seconds2time(videoTime/1000), nframe) , QMessageBox.Ok | QMessageBox.Default, QMessageBox.NoButton)

        
        self.fps[ urlparse.urlparse(self.mediaplayer.get_media().get_mrl()).path ] = round( videoTime / nframe,2  )

        if not 'media_file_info' in self.pj[OBSERVATIONS][ obsId]:
            self.pj[OBSERVATIONS][ obsId]['media_file_info'] = {}

        self.pj[OBSERVATIONS][ obsId]['media_file_info'][ hashfile( urlparse.urlparse(self.mediaplayer.get_media().get_mrl()).path , hashlib.md5()) ] = {'nframe': nframe, 'video_length': videoTime}
        self.projectChanged = True

        return True



    def initialize_new_observation_vlc(self):
        '''
        initialize new observation for VLC
        '''

        logging.debug('initialize new observation for VLC')

        self.playerType = VLC
        self.playerMode = FFMPEG
        
        self.fps = {}

        # creating a basic vlc instance
        self.instance = vlc.Instance()

        # creating an empty vlc media player
        self.mediaplayer = self.instance.media_player_new()

        self.mediaListPlayer = self.instance.media_list_player_new()
        self.mediaListPlayer.set_media_player(self.mediaplayer)

        self.media_list = self.instance.media_list_new()

        self.media_list2 = self.instance.media_list_new()

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

        self.toolBox.insertItem(0, self.videoTab, 'Audio/Video')


        self.ffmpegLayout = QHBoxLayout()

        self.lbFFmpeg = QLabel(self)
        self.lbFFmpeg.setBackgroundRole(QPalette.Base)

        self.ffmpegLayout.addWidget(self.lbFFmpeg)

        self.ffmpegTab = QtGui.QWidget()
        
        self.ffmpegTab.setLayout(self.ffmpegLayout)

        self.toolBox.insertItem(1, self.ffmpegTab, 'Frame by frame')

        self.toolBar.setEnabled(True)
        self.dwObservations.setVisible(True)
        self.toolBox.setVisible(True)
        self.lbFocalSubject.setVisible(True)
        self.lbCurrentStates.setVisible(True)

        self.mediaListPlayer.stop()

        # empty media list
        while self.media_list.count():
            self.media_list.remove_index(0)

        self.mediaListPlayer.set_media_list(self.media_list)

        logging.debug('media list count: {0}'.format(self.media_list.count()))

        # empty media list
        while self.media_list2.count():
            self.media_list2.remove_index(0)

        # init duration of media file
        del self.duration[0: len(self.duration)]

        self.FFmpegTimer = QTimer(self)
        self.FFmpegTimer.timeout.connect(self.FFmpegTimerOut)
        
        self.FFmpegTimerTick = 40
        self.FFmpegTimer.setInterval(self.FFmpegTimerTick)

        # add all media files to media list 
        if '1' in self.pj[OBSERVATIONS][self.observationId]['file'] and self.pj[OBSERVATIONS][self.observationId]['file']['1']:

            self.simultaneousMedia = False

            for mediaFile in self.pj[OBSERVATIONS][self.observationId]['file']['1']:

                if os.path.isfile( mediaFile ):

                    media = self.instance.media_new( mediaFile )
                    media.parse()

                    self.duration.append(media.get_duration())

                    # store video length in project file
                    hf = hashfile( mediaFile , hashlib.md5())

                    if not MEDIA_FILE_INFO in self.pj[OBSERVATIONS][ self.observationId ]:
                        self.pj[OBSERVATIONS][ self.observationId][MEDIA_FILE_INFO] = {}
                        self.projectChanged = True

                    if not hf in self.pj[OBSERVATIONS][ self.observationId][MEDIA_FILE_INFO]:
                        self.pj[OBSERVATIONS][ self.observationId][MEDIA_FILE_INFO][ hf ] = {'video_length': media.get_duration() }
                        self.projectChanged = True

                    self.media_list.add_media(media)

                else:

                    QMessageBox.critical(self, programName, '%s not found!<br>Fix the media path in the observation before playing it' % mediaFile, QMessageBox.Ok | QMessageBox.Default, QMessageBox.NoButton)
                    memObsId = self.observationId
                    self.close_observation()

                    self.new_observation( EDIT, memObsId)
                    return False


            # add media list to media player list
            self.mediaListPlayer.set_media_list(self.media_list)

            app.processEvents()
            # display media player in videoframe

            if self.embedPlayer:

                if sys.platform == "linux2": # for Linux using the X Server
                    self.mediaplayer.set_xwindow(self.videoframe.winId())

                elif sys.platform == "win32": # for Windows
                    ### http://srinikom.github.io/pyside-bz-archive/523.html
                    import ctypes
                    ctypes.pythonapi.PyCObject_AsVoidPtr.restype = ctypes.c_void_p
                    ctypes.pythonapi.PyCObject_AsVoidPtr.argtypes = [ctypes.py_object]

                    int_hwnd = ctypes.pythonapi.PyCObject_AsVoidPtr(self.videoframe.winId())

                    self.mediaplayer.set_hwnd(int_hwnd)

            # for mac always embed player
            if sys.platform == "darwin": # for MacOS
                self.mediaplayer.set_nsobject(self.videoframe.winId())

            app.processEvents()



            for idx in range(self.media_list.count()):
                app.processEvents()
                self.mediaListPlayer.play_item_at_index( idx )
                print('wait for playing video')
                while self.mediaListPlayer.get_state() != vlc.State.Playing:
                    time.sleep(3)
                    #print(3)
                    pass
                self.mediaListPlayer.pause()
                app.processEvents()

                if self.mediaplayer.get_fps() == 0 and  FFMPEG in self.availablePlayers:   # FPS not available from VLC

                    flagOK = False
                    
                    if MEDIA_FILE_INFO in self.pj[OBSERVATIONS][self.observationId]:
                        
                        hashFile = hashfile( urlparse.urlparse(self.mediaplayer.get_media().get_mrl()).path , hashlib.md5())

                        if hashFile in self.pj[OBSERVATIONS][self.observationId][MEDIA_FILE_INFO]:

                            if 'video_length' in self.pj[OBSERVATIONS][self.observationId][MEDIA_FILE_INFO][hashFile]:
                                videoLength = self.pj[OBSERVATIONS][self.observationId][MEDIA_FILE_INFO][hashFile]['video_length']
                            else:
                                videoLength = 0

                            if 'nframe' in self.pj[OBSERVATIONS][self.observationId][MEDIA_FILE_INFO][hashFile]:
                                nframe = self.pj[OBSERVATIONS][self.observationId][MEDIA_FILE_INFO][hashFile]['nframe']
                            else:
                                nframe = 0

                            logging.debug('media length: {0}, number of frames: {1}'.format(videoLength, nframe))

                            if videoLength and nframe:
                                self.fps[ urlparse.urlparse(self.mediaplayer.get_media().get_mrl()).path ] = round( videoLength / nframe,2 )
                                flagOK = True

                    if not flagOK and FFMPEG in self.availablePlayers:

                        response = dialog.MessageDialog(programName, 'BORIS is not able to determine the frame rate of the video.\nLaunch accurate video analysis?\nThis analysis may be long (half time of video)', [YES, NO ])
                        if response == YES:
                            logging.debug('path of video to analyze: %s' % urlparse.urlparse(self.mediaplayer.get_media().get_mrl()).path)
        
                            self.process = Process()
                            self.process.signal.sig.connect(self.processCompleted)
                            self.process.obsId = self.observationId
                            self.process.videoPath = urlparse.urlparse(self.mediaplayer.get_media().get_mrl()).path
                            self.process.ffmpeg_bin = self.ffmpeg_bin
                            self.process.start()

                            while not self.process.isRunning():
                                time.sleep(0.01)
                                continue

                            self.close_observation()
                            self.statusbar.showMessage('Video analysis. Please wait...',0)
                            return False
        
                        else:

                            return False

                else:
                    self.fps[ urlparse.urlparse(self.mediaplayer.get_media().get_mrl()).path ] = self.mediaplayer.get_fps()

            # check if fps changes between media
            if FFMPEG in self.availablePlayers:
                if len(set( self.fps.values() )) != 1:
                    QMessageBox.critical(self, programName, 'The video files have different frame rates:\n%s\n\nYou can only queue video files with same frame rate.' % (', '.join([str(i) for i in self.fps.values()])),\
                     QMessageBox.Ok | QMessageBox.Default, QMessageBox.NoButton)
                    return False


            # show first frame of video
            app.processEvents()

            self.mediaListPlayer.play_item_at_index( 0 )
            app.processEvents()

            # play mediaListPlayer for a while to obtain media information
            while self.mediaListPlayer.get_state() != vlc.State.Playing:
                time.sleep(3)
                pass
            self.mediaListPlayer.pause()

            app.processEvents()

            self.mediaplayer.set_time(0)

            # no subtitles
            self.mediaplayer.video_set_spu(0)

        else:
            QMessageBox.warning(self, programName , 'You must choose a media file to code')
            return False



        # check if media list player 1 contains more than 1 media
        if '1' in self.pj[OBSERVATIONS][self.observationId]['file'] and len(self.pj[OBSERVATIONS][self.observationId]['file']['1']) > 1 \
            and \
           '2' in self.pj[OBSERVATIONS][self.observationId]['file'] and  self.pj[OBSERVATIONS][self.observationId]['file']['2']:
               QMessageBox.warning(self, programName , 'It is not yet possible to play a second media when many media are loaded in the first media player' )
               

        # check for second media to be played together
        elif '2' in self.pj[OBSERVATIONS][self.observationId]['file'] and  self.pj[OBSERVATIONS][self.observationId]['file']['2']:
                
                # create 2nd mediaplayer
                self.simultaneousMedia = True

                self.mediaplayer2 = self.instance.media_player_new()

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
                
                
                # add media file
                for mediaFile in self.pj[OBSERVATIONS][self.observationId]['file']['2']:

                    if os.path.isfile( mediaFile ):    

                        media = self.instance.media_new( mediaFile )
                        media.parse()
                        
                        logging.debug( 'media file 2 {0}  duration {1}'.format(mediaFile, media.get_duration()))

                        self.media_list2.add_media(media)


                self.mediaListPlayer2.set_media_list(self.media_list2)
                
                if self.embedPlayer:
                    if sys.platform == "linux2": # for Linux using the X Server
                        self.mediaplayer2.set_xwindow(self.videoframe2.winId())
    
                    elif sys.platform == "win32": # for Windows
                        # http://srinikom.github.io/pyside-bz-archive/523.html
                        import ctypes
                        ctypes.pythonapi.PyCObject_AsVoidPtr.restype = ctypes.c_void_p
                        ctypes.pythonapi.PyCObject_AsVoidPtr.argtypes = [ctypes.py_object]

                        int_hwnd = ctypes.pythonapi.PyCObject_AsVoidPtr(self.videoframe2.winId())
                        
                        self.mediaplayer2.set_hwnd(int_hwnd)
            
                        # self.mediaplayer.set_hwnd(self.videoframe.winId())


                    elif sys.platform == "darwin": # for MacOS
                        self.mediaplayer2.set_nsobject(self.videoframe2.windId())

                # show first frame of video
                app.processEvents()

                self.mediaListPlayer2.play()
                app.processEvents()

                while self.mediaListPlayer2.get_state() != vlc.State.Playing:
                    time.sleep(3)
                    pass
                self.mediaListPlayer2.pause()
                app.processEvents()

                self.mediaplayer2.set_time(0)
                if TIME_OFFSET_SECOND_PLAYER in self.pj[OBSERVATIONS][self.observationId] \
                    and self.pj[OBSERVATIONS][self.observationId][TIME_OFFSET_SECOND_PLAYER]:
                    if self.pj[OBSERVATIONS][self.observationId][TIME_OFFSET_SECOND_PLAYER] > 0:
                        self.mediaplayer2.set_time( int( self.pj[OBSERVATIONS][self.observationId][TIME_OFFSET_SECOND_PLAYER] *1000) )


                # no subtitles
                self.mediaplayer2.video_set_spu(0)


        self.videoTab.setEnabled(True)
        self.toolBox.setItemEnabled (video, True)
        self.toolBox.setCurrentIndex(video)

        self.toolBar.setEnabled(True)
        self.display_timeoffset_statubar( self.pj[OBSERVATIONS][self.observationId][TIME_OFFSET] )
        self.timer.start(200)

        return True


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

                    self.twEvents.setItem(row, tw_obs_fields[field_type] , QTableWidgetItem(  field ) )

                else:
                    self.twEvents.setItem(row, tw_obs_fields[field_type] , QTableWidgetItem(''))

            row += 1

        self.update_events_start_stop()



    def selectObservations(self, mode):
        '''
        show observations list window
        mode: accepted values: SINGLE, MULTIPLE, SELECT1
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

            for idx in sorted( list(self.pj[ INDEPENDENT_VARIABLES ].keys())  ):
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
            if self.pj[OBSERVATIONS][obs]['type'] in [MEDIA]:
                for idx in self.pj[OBSERVATIONS][obs]['file']:
                    for media in self.pj[OBSERVATIONS][obs]['file'][idx]:
                        mediaList.append('#%s: %s' % (idx , media))

                media = '\n'.join( mediaList )
            elif self.pj[OBSERVATIONS][obs]['type'] in [LIVE]:
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

        self.create_live_tab()

        self.toolBox.setVisible(True)
        
        self.dwObservations.setVisible(True)
        
        self.simultaneousMedia = False

        self.lbFocalSubject.setVisible(True)
        self.lbCurrentStates.setVisible(True)


        self.liveTab.setEnabled(True)
        self.toolBox.setItemEnabled (0, True)   ### enable tab
        self.toolBox.setCurrentIndex(0)  ### show tab

        self.toolBar.setEnabled(False)

        self.liveObservationStarted = False
        self.textButton.setText('Start live observation')
        self.lbTimeLive.setText('00:00:00.000')

        self.liveStartTime = None
        self.liveTimer.stop()

        


    def new_observation(self, mode = NEW, obsId = ''):
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

        observationWindow.mode = mode
        observationWindow.mem_obs_id = obsId

        observationWindow.dteDate.setDateTime( QDateTime.currentDateTime() )

        # add indepvariables
        if INDEPENDENT_VARIABLES in self.pj:
            observationWindow.twIndepVariables.setRowCount(0)
            for i in sorted( self.pj[INDEPENDENT_VARIABLES].keys() ):

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
                
            


            if '1' in self.pj[OBSERVATIONS][obsId]['file'] and self.pj[OBSERVATIONS][obsId]['file']['1']:

                observationWindow.lwVideo.addItems( self.pj[OBSERVATIONS][obsId]['file']['1'] )

            # check if simultaneous 2nd media
            if '2' in self.pj[OBSERVATIONS][obsId]['file'] and self.pj[OBSERVATIONS][obsId]['file']['2']:   ### media for 2nd player

                observationWindow.lwVideo_2.addItems( self.pj[OBSERVATIONS][obsId]['file']['2'] )


            if self.pj[OBSERVATIONS][obsId]['type'] in [MEDIA]:
                observationWindow.tabProjectType.setCurrentIndex(video)


            if self.pj[OBSERVATIONS][obsId]['type'] in [LIVE]:
                observationWindow.tabProjectType.setCurrentIndex(live)




        #####################################################################################
        #####################################################################################

        if observationWindow.exec_():

            self.projectChanged = True

            new_obs_id = observationWindow.leObservationId.text()

            if mode == NEW:

                self.observationId = new_obs_id
                self.pj[OBSERVATIONS][self.observationId] = { 'file': [], 'type': '' ,  'date': '', 'description': '','time offset': 0, 'events': [] }


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

                ### set dictionary as label (col 0) => value (col 2)
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
                
                fileName['1'] = []
                if observationWindow.lwVideo.count():
                    
                    for i in range(observationWindow.lwVideo.count()):
                        observationWindow.lwVideo.item(i)
                    
                        if self.saveMediaFilePath:
                            ### save full path 
                            fileName['1'].append (  observationWindow.lwVideo.item(i).text() )
                        else:
                            fileName['1'].append ( os.path.basename( observationWindow.lwVideo.item(i).text() ) )


                fileName['2'] = []

                if observationWindow.lwVideo_2.count():
                    
                    for i in range(observationWindow.lwVideo_2.count()):
                        observationWindow.lwVideo_2.item(i)
                    
                        if self.saveMediaFilePath:
                            # save full path 
                            fileName['2'].append (  observationWindow.lwVideo_2.item(i).text() )
                        else:
                            fileName['2'].append ( os.path.basename( observationWindow.lwVideo_2.item(i).text() ) )


                self.pj[OBSERVATIONS][new_obs_id]['file'] = fileName


            if mode == NEW:
                self.menu_options()

                # title of dock widget
                self.dwObservations.setWindowTitle('Events for ' + self.observationId) 

                if self.pj[OBSERVATIONS][self.observationId]['type'] in [LIVE]:

                    self.playerType = LIVE
                    self.initialize_new_live_observation()

                else:
                    self.playerType = VLC
                    self.initialize_new_observation_vlc()
    

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
            # empty media list
            while self.media_list.count():
                self.media_list.remove_index(0)

            if self.simultaneousMedia:
                self.mediaplayer2.stop()
                while self.media_list2.count():
                    self.media_list2.remove_index(0)

            while self.video1layout.count():
                item = self.video1layout.takeAt(0)
                item.widget().deleteLater()
    
            if self.simultaneousMedia:
                while self.video2layout.count():
                    item = self.video2layout.takeAt(0)
                    item.widget().deleteLater()
                    self.simultaneousMedia = False
    
            self.videoTab.deleteLater()

            self.actionFrame_by_frame.setChecked(False)
            
            self.playMode = VLC


            # FFMPEG
            
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

        self.menu_options()



    def readConfigFile(self):
        '''
        read config file
        '''
        logging.info('read config file')

        if os.path.isfile( os.path.expanduser('~') + os.sep + '.boris' ):
            settings = QSettings(os.path.expanduser('~') + os.sep + '.boris' , QSettings.IniFormat)

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


            self.saveMediaFilePath = True

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

            self.allowFrameByFrame = False
            try:
                self.allowFrameByFrame = ( settings.value('allow_frame_by_frame') == 'true' )
            except:
                self.allowFrameByFrame = False

            self.ffmpeg_bin = ''
            try:
                self.ffmpeg_bin = settings.value('ffmpeg_bin')
                if not self.ffmpeg_bin:
                    self.ffmpeg_bin = ''
            except:
                self.ffmpeg_bin = ''

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


    def saveConfigFile(self):
        '''
        save config file
        '''

        logging.info('save config file')

        settings = QSettings(os.path.expanduser('~') + os.sep + '.boris', QSettings.IniFormat)

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
                        if (subject_to_analyze == 'No focal subject' and event[1] == '') \
                            or ( event[1] == subject_to_analyze ):

                            if event[1] == '':
                                subjectStr = 'No focal subject'
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
            subjectsSelection.ch.setText( 'No focal subject' )
            subjectsSelection.ch.setChecked(True)
            subjectsSelection.lw.setItemWidget(subjectsSelection.item, subjectsSelection.ch)

        all_subjects = sorted( [  self.pj['subjects_conf'][x][ 'name' ]  for x in self.pj['subjects_conf'] ] )

        for subject in all_subjects:

            #logging.debug('subject: {0}'.format( subject ))

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



    def select_behaviors(self):
        '''
        allow user to select behaviors 
        '''

        behaviorsSelection = checkingBox_list()

        allBehaviors = sorted( [  self.pj['behaviors_conf'][x][ 'code' ]  for x in self.pj['behaviors_conf'] ] )

        for behavior in allBehaviors:

            if self.DEBUG: print(behavior)  

            behaviorsSelection.item = QListWidgetItem(behaviorsSelection.lw)
            behaviorsSelection.ch = QCheckBox()
            behaviorsSelection.ch.setText( behavior )

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



    def time_budget(self):
        '''
        time budget
        '''
        logging.info('Time budget function')

        # OBSERVATIONS

        # ask user observations to analyze
        result, selectedObservations = self.selectObservations( MULTIPLE )

        if not selectedObservations:
            return

        # SUBJECTS

        # extract subjects present in observations
        observed_subjects = self.extract_observed_subjects( selectedObservations )
        
        # ask user for subjects to analyze
        selectedSubjects = self.select_subjects( observed_subjects )
    
        if not selectedSubjects:
            return

        selectedBehaviors = self.select_behaviors()

        if not selectedBehaviors:
            return

        includeModifiers = dialog.MessageDialog(programName, 'Include modifiers?', [YES, NO])

        cursor = self.loadEventsInDB( selectedSubjects, selectedObservations, selectedBehaviors )

        out = []
        for subject in selectedSubjects:

            for behavior in selectedBehaviors:
                
                if includeModifiers == YES:

                    cursor.execute( "SELECT distinct modifiers FROM events WHERE subject = ? AND code = ?", (subject, behavior) )
                    distinct_modifiers = list(cursor.fetchall() )

                    if not distinct_modifiers:
                        out.append(  { 'subject': subject , 'behavior': behavior, 'modifiers': '-' , 'duration': '-', 'mean': '-', 'number': 0, 'inter_duration_mean': '-' } )
                        continue
                    if 'POINT' in self.eventType(behavior).upper():

                        for modifier in distinct_modifiers:
                            cursor.execute( "SELECT occurence FROM events WHERE subject = ? AND code = ? AND modifiers = ? ORDER BY observation, occurence", ( subject, behavior, modifier[0] ))
                            rows = cursor.fetchall()
                            inter_duration = 0
                            for idx, row in enumerate(rows):
                                if idx > 0:
                                    inter_duration += float(row[0]) - float(rows[idx-1][0])

                            if inter_duration == 0:
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
        
                                if inter_duration == 0:
                                    inter_duration = 'NA'
                                else:
                                    inter_duration = round(inter_duration/ (len(rows)/2-1),3)
                                out.append( { 'subject': subject , 'behavior': behavior, 'modifiers': modifier[0], 'duration': tot_duration, 'mean': round(tot_duration/(len(rows)/2),3),\
                                               'number': int(len(rows)/2), 'inter_duration_mean': inter_duration } )

                else:  # no modifiers
                    if 'POINT' in self.eventType(behavior).upper():
                        cursor.execute( "SELECT occurence FROM events WHERE subject = ? AND code = ?  order by observation, occurence", ( subject, behavior ) )
                        rows =  cursor.fetchall()
                        if not len( rows ):
                            out.append({ 'subject': subject , 'behavior': behavior, 'modifiers': 'NA', 'duration': '-', 'mean': '-', 'number': 0, 'inter_duration_mean': '-'})
                            continue
                        
                        inter_duration = 0
                        for idx,row in enumerate(rows):
                            if idx > 0:
                                inter_duration += float(row[0]) - float(rows[idx-1][0])

                        if inter_duration == 0:
                            inter_duration =  'NA'
                        else:
                            inter_duration = round(inter_duration/(len(rows) - 1),3)

                        out.append(  { 'subject': subject , 'behavior': behavior, 'modifiers': 'NA', 'duration': '-', 'mean': '-', 'number': len(rows), 'inter_duration_mean': inter_duration}  )
                            

                    if 'STATE' in self.eventType(behavior).upper():
                        cursor.execute( "SELECT occurence FROM events where subject = ? AND code = ? order by observation, occurence", (subject, behavior) )
                        rows = list(cursor.fetchall() )
                        if not len( rows ):
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

                            if inter_duration == 0:
                                inter_duration = 'NA'
                            else:
                                inter_duration = round(inter_duration/ (len(rows)/2-1),3)

                            out.append( { 'subject': subject , 'behavior': behavior, 'modifiers': 'NA', 'duration': tot_duration, 'mean': round(tot_duration/(len(rows)/2),3),\
                                           'number': int(len(rows)/2), 'inter_duration_mean': inter_duration/ (len(rows)/2-1) } )


        # min max
        cursor.execute( "SELECT min(occurence), max(occurence) FROM events" )
        min_, max_ = cursor.fetchall()[0]
        
        if min_ and max_:
            obsDuration = float(max_) - float(min_)
        else:
            obsDuration = 0

        # widget for results visualization
        self.tb = timeBudgetResults(self.DEBUG, self.pj)

        # observations list
        self.tb.label.setText( 'Selected observations' )
        for obs in selectedObservations:
            self.tb.lw.addItem(obs)


        tb_fields = ['Subject', 'Behavior', 'Modifiers', 'Total number', 'Total duration (s)', 'Duration mean (s)', 'inter-event intervals mean (s)', '% of total time']
        self.tb.twTB.setColumnCount( len( tb_fields ) )
        self.tb.twTB.setHorizontalHeaderLabels(tb_fields)

        fields = ['subject', 'behavior',  'modifiers', 'number', 'duration', 'mean', 'inter_duration_mean']

        for row in out:
            self.tb.twTB.setRowCount(self.tb.twTB.rowCount() + 1)

            column = 0 

            for field in fields:

                #item = QTableWidgetItem(str( row[field]).replace(' ()','' ))
                item = QTableWidgetItem(unicode( row[field]).replace(' ()','' ))
                # no modif allowed
                item.setFlags(Qt.ItemIsEnabled)
                self.tb.twTB.setItem(self.tb.twTB.rowCount() - 1, column , item)

                column += 1

            # % of total time
            #print(row['duration'])
            if row['duration'] != '-' and row['duration'] != 0 and row['duration'] != UNPAIRED and obsDuration: 
                item = QTableWidgetItem(str( round( row['duration'] / obsDuration * 100,1)  ) )
            else:
                item = QTableWidgetItem( '-' )

            item.setFlags(Qt.ItemIsEnabled)
            self.tb.twTB.setItem(self.tb.twTB.rowCount() - 1, column , item)

        self.tb.twTB.resizeColumnsToContents()

        self.tb.show()



    def plot_events(self):
        '''
        plot events
        '''

        # ask user for one observation to plot
        result, selectedObservations = self.selectObservations( SELECT1 )

        logging.debug('Selected observations: {0}'.format(selectedObservations))

        if not selectedObservations:
            return

        maxTime = 0
        
        if self.pj[OBSERVATIONS][ selectedObservations[0] ]['type'] == MEDIA:

            for mediaFile in self.pj[OBSERVATIONS][ selectedObservations[0] ]['file'][PLAYER1]:
    
                if os.path.isfile(mediaFile):
                    hf = hashfile( mediaFile , hashlib.md5())
                    if MEDIA_FILE_INFO in self.pj[OBSERVATIONS][ selectedObservations[0] ] and hf in self.pj[OBSERVATIONS][ selectedObservations[0] ][MEDIA_FILE_INFO]:
                        maxTime += self.pj[OBSERVATIONS][ selectedObservations[0] ][MEDIA_FILE_INFO][ hf ][ 'video_length' ]
                else: # file not found
                    QMessageBox.warning(self, programName , 'The media file <b>{0}</b> was not found!\nEdit the observation <b>{1}</b> and try again.'.format( mediaFile, selectedObservations[0]))
                    return
    
            if not maxTime:
                QMessageBox.warning(self, programName , 'The video length was not found!\nOpen your observation, close it and try again.')
                return

            maxTime /= 1000

        else: # LIVE
            maxTime = max(self.pj[OBSERVATIONS][ selectedObservations[0] ][EVENTS])[0]
            
        logging.debug('max time: {0}'.format(maxTime))

        # extract subjects present in observations
        observedSubjects = self.extract_observed_subjects( selectedObservations )

        selectedSubjects = self.select_subjects( observedSubjects )
    
        logging.debug('selected subjects: {0}'.format(selectedSubjects))
    
        if not selectedSubjects:
            return

        selectedBehaviors = self.select_behaviors()

        logging.debug('Selected behaviors: {0}'.format(selectedBehaviors))
        if not selectedBehaviors:
            return

        includeModifiers = dialog.MessageDialog(programName, 'Include modifiers?', [YES, NO])

        cursor = self.loadEventsInDB( selectedSubjects, selectedObservations, selectedBehaviors )

        # min max
        '''
        cursor.execute( "SELECT min(occurence), max(occurence) FROM events" )
        minTime, maxTime = cursor.fetchall()[0]
        
        if self.DEBUG: print ('minTime, maxTime',minTime, maxTime )
        '''



        # tracks number
        trackNb = len( selectedSubjects ) * len( selectedBehaviors ) 

        # figure

        # set rotation
        if self.timeFormat == HHMMSS:
             rotation = -45
        if self.timeFormat == S:
             rotation = 0

        width = 1000
        #xm = 1000

        left_margin = 10
        right_margin = 80
        
        x_init = 250
        y_init = 100
        spacer = 10   # distance between elements
        header_height = 160
        top_margin = 10

        h = 20   # height of element
        w = 1

        red = (255,0,0)
        blue = (0,0,255)
        black = (0,0,0)
        white = (255,255,255)


        height = top_margin + (trackNb ) * (h + spacer) + 280
        
        scene = svg.Scene('',  height, width)

        # white background
        scene.add(svg.Rectangle((0,0), height, width , white))

        # time line
        scene.add(svg.Rectangle((x_init, y_init), 1, ( width - x_init - right_margin ) , black))
        
        #scene.add(svg.Line((x_init + xm, y_init - h // 4), (x_init + xm, y_init), black ))

        

        tick, maxScale = getTimeValues( maxTime )

        scene.add( svg.Text(( x_init + ( width - x_init - right_margin ) - 2, y_init - h // 4 - 2 ), self.convertTime( maxScale ), 12, rotation) )
        for i in range( int(maxScale/tick) ):

            scene.add(svg.Line((round(x_init + i * (( width - x_init - right_margin ) / int(maxScale/tick)    )), y_init - h // 4), \
                               (round(x_init + i * (( width - x_init - right_margin ) / int(maxScale/tick))), y_init), black ))

            scene.add( svg.Text(( round(x_init + i * (( width - x_init - right_margin ) / int(maxScale/tick))), y_init - h // 4 - 2 ), \
                                self.convertTime( i * tick  ), 12, rotation) )

        y_init += 30

        for subject in selectedSubjects:

            scene.add( svg.Text(( left_margin , y_init ), 'Subject: ' + subject, 14) )
            y_init += h

            for behavior in selectedBehaviors:

                if includeModifiers == YES:

                    cursor.execute( "SELECT distinct modifiers FROM events WHERE subject = ? AND code = ?", (subject, behavior) )
                    distinct_modifiers = list(cursor.fetchall() )

                    for modifier in distinct_modifiers:
                        cursor.execute( "SELECT occurence FROM events WHERE subject = ? AND code = ? AND modifiers = ? ORDER BY observation, occurence", ( subject, behavior, modifier[0] ))
                        rows = cursor.fetchall()

                        if modifier[0]:
                            print( behavior )
                            print( modifier )
                            behaviorOut = unicode('{0} ({1})').format(behavior, modifier[0].replace('|',','))
                        else:
                            behaviorOut = behavior

                        scene.add( svg.Text(( left_margin, y_init + h - 2), behaviorOut, 16) )

                        for idx, row in enumerate(rows):
                            if 'POINT' in self.eventType(behavior).upper():
                                scene.add(svg.Rectangle( (x_init + round(row[0] / maxScale * ( width - x_init - right_margin )), y_init), h, w, red) )
    
                            if 'STATE' in self.eventType(behavior).upper():
                                if idx % 2 == 0:

                                    try:
                                        begin, end = row[0], rows[idx + 1][0]
                                        scene.add(svg.Rectangle( (x_init + round(begin / maxScale * ( width - x_init - right_margin )), y_init), h,   round((end - begin) / maxScale * ( width - x_init - right_margin ) )     , blue))
                                    except:
                                        if 'No focal subject' in subject:
                                            sbj = ''
                                        else:
                                            sbj =  'for subject <b>{0}</b>'.format( subject )
                                        QMessageBox.critical(self, programName, 'The STATE behavior <b>{0}</b> is not paired{1}'.format(behavior, sbj) )

                        y_init += h + spacer

                else:

                    cursor.execute( "SELECT occurence FROM events WHERE subject = ? AND code = ? ORDER BY observation, occurence", (subject, behavior) )
                    rows = list(cursor.fetchall() )
                    if 'STATE' in self.eventType(behavior).upper() and len( rows ) % 2:
                        print( UNPAIRED )
                        continue

                    behaviorOut = '%s' % behavior
                    scene.add( svg.Text(( left_margin, y_init + h - 2), behaviorOut, 16) )
    
                    for idx, row in enumerate(rows):

                        if 'POINT' in self.eventType(behavior).upper():
                            scene.add(svg.Rectangle( (x_init + round(row[0] / maxScale * ( width - x_init - right_margin )), y_init), h, w, red) )

                        if 'STATE' in self.eventType(behavior).upper():
                            if idx % 2 == 0:
                                begin, end = row[0], rows[idx + 1][0]
                                scene.add(svg.Rectangle( (x_init + round(begin / maxScale * ( width - x_init - right_margin )), y_init), h,   round((end - begin) / maxScale * ( width - x_init - right_margin ) )     , blue))

                    y_init += h + spacer

            # subject separator
            scene.add(svg.Rectangle((left_margin, y_init), 1, width - right_margin -left_margin, black))

            y_init += h + spacer

        svg_text = scene.svg_text()
        
        
        self.gr = diagram(self.DEBUG, svg_text)
        self.gr.show()
            





    def open_project_json(self, projectFileName):
        '''
        open project  json
        '''
        if not os.path.isfile(projectFileName):
            QMessageBox.warning(self, programName , 'File not found')
            return

        s = open(projectFileName, 'r').read()

        self.pj = json.loads(s)
        
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
                if len( self.pj[OBSERVATIONS][obs]['file'] ):
                    d1 = { '1':  [self.pj[OBSERVATIONS][obs]['file'][0]] }

                if len( self.pj[OBSERVATIONS][obs]['file'] ) == 2:
                    d1['2'] =  [self.pj[OBSERVATIONS][obs]['file'][1]]

                self.pj[OBSERVATIONS][obs]['file'] = d1

            # convert VIDEO, AUDIO -> MEDIA

            for idx in [x for x in self.pj['subjects_conf']]:

                key, name = self.pj[SUBJECTS][idx]
                self.pj[SUBJECTS][idx] = {'key': key, 'name': name, 'description':''}


            QMessageBox.information(self, programName , 'The project file was converted to the new format (v. %s) in use with your version of BORIS.\nChoose a new file name for saving it.' % project_format_version)

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
        fileName = fd.getOpenFileName(self, 'Open project', '', 'Project files (*.boris);;Old project files (*.obs);;All files (*)')[0]

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
            self.twConfiguration.setRowCount(0)   ### behaviors
            self.twSubjects.setRowCount(0)
            self.twEvents.setRowCount(0)


        newProjectWindow = projectDialog(self.DEBUG)

        if self.projectWindowGeometry:
            newProjectWindow.restoreGeometry( self.projectWindowGeometry)

        newProjectWindow.setWindowTitle(mode + ' project')
        newProjectWindow.tabProject.setCurrentIndex(0)   ### project information

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

                for idx in sorted ( self.pj[SUBJECTS].keys() ):

                    newProjectWindow.twSubjects.setRowCount(newProjectWindow.twSubjects.rowCount() + 1)

                    for i, field in enumerate( subjectsFields ):
                        item = QTableWidgetItem(self.pj[SUBJECTS][idx][field])   
                        newProjectWindow.twSubjects.setItem(newProjectWindow.twSubjects.rowCount() - 1, i ,item)

                newProjectWindow.twSubjects.setSortingEnabled(False)

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
                        for idx in self.pj[OBSERVATIONS][obs]['file']:
                            for media in self.pj[OBSERVATIONS][obs]['file'][idx]:
                                mediaList.append('#%s: %s' % (idx , media))

                    elif self.pj[OBSERVATIONS][obs]['type'] in [LIVE]:
                        mediaList = [LIVE]
                    

                    item = QTableWidgetItem('\n'.join( mediaList )) 
                    newProjectWindow.twObservations.setItem(newProjectWindow.twObservations.rowCount() - 1, 3, item)

                newProjectWindow.twObservations.resizeColumnsToContents()


            # configuration of behaviours
            if self.pj['behaviors_conf']:

                newProjectWindow.signalMapper = QSignalMapper(self)
                newProjectWindow.comboBoxes = []

                for i in sorted( self.pj['behaviors_conf'].keys() ):
                    newProjectWindow.twBehaviors.setRowCount(newProjectWindow.twBehaviors.rowCount() + 1)

                    for field in fields:

                        item = QTableWidgetItem()

                        if field == 'type':

                            # add combobox with event type
                            newProjectWindow.comboBoxes.append(QComboBox())
                            newProjectWindow.comboBoxes[-1].addItems(observation_types)
                            newProjectWindow.comboBoxes[-1].setCurrentIndex( observation_types.index(self.pj['behaviors_conf'][i][field]) )

                            newProjectWindow.signalMapper.setMapping(newProjectWindow.comboBoxes[-1], newProjectWindow.twBehaviors.rowCount() - 1)
                            newProjectWindow.comboBoxes[-1].currentIndexChanged['int'].connect(newProjectWindow.signalMapper.map)

                            newProjectWindow.twBehaviors.setCellWidget(newProjectWindow.twBehaviors.rowCount() - 1, fields[field], newProjectWindow.comboBoxes[-1])

                        else:
                            if field in self.pj['behaviors_conf'][i]:
                                item.setText( self.pj['behaviors_conf'][i][field] )
                            else:
                                item.setText( '' )

                            if field in ['excluded', 'coding map', 'modifiers']:
                                item.setFlags(Qt.ItemIsEnabled)

                            newProjectWindow.twBehaviors.setItem(newProjectWindow.twBehaviors.rowCount() - 1, fields[field] ,item)

                newProjectWindow.signalMapper.mapped['int'].connect(newProjectWindow.comboBoxChanged)

                newProjectWindow.twBehaviors.resizeColumnsToContents()

            

            # load independent variables 
            if INDEPENDENT_VARIABLES in self.pj:
                for i in sorted( self.pj[ INDEPENDENT_VARIABLES ].keys() ):
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
            'subjects_conf' : {},\
            'behaviors_conf': {}, \
            OBSERVATIONS: {},
            'coding_map': {} }
        
        ### pass copy of self.pj
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

                self.pj['behaviors_conf'] =  newProjectWindow.obs

                self.load_obs_in_lwConfiguration()
                
                self.pj['subjects_conf'] =  newProjectWindow.subjects_conf

                if self.DEBUG: print('subjects', self.pj['subjects_conf'])

                self.load_subjects_in_twSubjects()
                
                # load variables
                self.pj[ INDEPENDENT_VARIABLES ] =  newProjectWindow.indVar

                if self.DEBUG: print(INDEPENDENT_VARIABLES, self.pj[INDEPENDENT_VARIABLES])

            # observations (check if observation deleted)
            self.toolBar.setEnabled(True)

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
        self.projectFileName, filtr = fd.getSaveFileName(self, 'Save project as', os.path.dirname(self.projectFileName), 'Projects file (*.boris);;All files (*)')

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

            self.projectFileName, filtr = fd.getSaveFileName(self, 'Save project', txt, 'Projects file (*.boris);;All files (*)')

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
            if len(  [ x[ pj_obs_fields['code'] ] for x in self.pj[OBSERVATIONS][self.observationId][EVENTS ] if x[ pj_obs_fields['subject'] ] == '' and x[ pj_obs_fields['code'] ] == sbc and x[ pj_obs_fields['time'] ] <= currentTime  ] ) % 2: ### test if odd
                self.currentStates[''].append(sbc)

        # add states for all configured subjects
        for idx in self.pj['subjects_conf']:

            ### add subject index
            self.currentStates[ idx ] = []
            for sbc in StateBehaviorsCodes:
                if len(  [ x[ pj_obs_fields['code'] ] for x in self.pj[OBSERVATIONS][self.observationId][EVENTS ] if x[ pj_obs_fields['subject'] ] == self.pj['subjects_conf'][idx]['name'] and x[ pj_obs_fields['code'] ] == sbc and x[ pj_obs_fields['time'] ] <= currentTime  ] ) % 2: ### test if odd
                    self.currentStates[idx].append(sbc)


        # show current states
        if self.currentSubject:
            # get index of focal subject (by name)
            idx = [idx for idx in self.pj['subjects_conf'] if self.pj['subjects_conf'][idx]['name'] == self.currentSubject][0]
            self.lbCurrentStates.setText(  '%s' % (', '.join(self.currentStates[ idx ]))) 
        else:
            self.lbCurrentStates.setText(  '%s' % (', '.join(self.currentStates[ '' ]))) 

        # show selected subjects
        for idx in sorted( self.pj['subjects_conf'].keys() ):

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
        # ask user observations to analyze
        result, selectedObservations = self.selectObservations( MULTIPLE )
        if not selectedObservations:
            return
        
        # filter subjects in observations
        observedSubjects = self.extract_observed_subjects( selectedObservations )

        selectedSubjects = self.select_subjects( observedSubjects )

        if not selectedSubjects:
            logging.info('No subjects selected')
            return

        selectedBehaviors = self.select_behaviors()

        if not selectedBehaviors:
            logging.info('No behaviors selected')
            return


        includeModifiers = dialog.MessageDialog(programName, 'Include modifiers?', [YES, NO])

        cursor = self.loadEventsInDB( selectedSubjects, selectedObservations, selectedBehaviors )

        for obsId in selectedObservations:

            # extract file name of first video of first player

            for media in self.pj[OBSERVATIONS][ obsId ]['file'][PLAYER1]:
                
                if os.path.isfile( media ):
                    fileName = media + '.srt'
                else:
    
                    response = dialog.MessageDialog(programName, '{0} not found!\nDo you want to choose another place to save subtitles? '.format(media), [YES, NO])
                    if response == YES:
                        fd = QFileDialog(self)
                        fileName, _ = fd.getSaveFileName(self, 'Save subtitles file', '','Subtitles files (*.srt *.txt);;All files (*)')
                        if not fileName:
                            continue
                    else:
                        continue

                # TODO add subtitle for enqueued media
                '''
                hf = hashfile( mediaFile , hashlib.md5())
                if MEDIA_FILE_INFO in self.pj[OBSERVATIONS][ selectedObservations[0] ] and hf in self.pj[OBSERVATIONS][ selectedObservations[0] ][MEDIA_FILE_INFO]:
                    maxTime += self.pj[OBSERVATIONS][ selectedObservations[0] ][MEDIA_FILE_INFO][ hf ][ 'video_length' ]
                '''


                subtitles = []
                for subject in selectedSubjects:

                    for behavior in selectedBehaviors:
    
                        cursor.execute( "SELECT occurence, modifiers FROM events where observation = ? AND subject = ? AND  code = ? ORDER BY code, occurence", (obsId, subject, behavior) )
                        rows = list(cursor.fetchall() )
                        if 'STATE' in self.eventType(behavior).upper() and len( rows ) % 2:
                            print( UNPAIRED )
                            continue
    
                        for idx, row in enumerate(rows):
    
                            # subtitle color
                            if subject == 'No focal subject':
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

        # ask user observations to analyze
        result, selectedObservations = self.selectObservations( MULTIPLE )
        if not selectedObservations:
            return
        
        # filter subjects in observations
        observedSubjects = self.extract_observed_subjects( selectedObservations )

        selectedSubjects = self.select_subjects( observedSubjects )

        if not selectedSubjects:
            return

        selectedBehaviors = self.select_behaviors()

        if not selectedBehaviors:
            return

        fd = QFileDialog(self)

        if format_ == 'sql':
            fileName, _ = fd.getSaveFileName(self, 'Export aggregated events in SQL format', '' , 'SQL dump file file (*.sql);;All files (*)')
    
            out = '''CREATE TABLE events (id INTEGER PRIMARY KEY ASC, observation TEXT, date DATE, subject TEXT, behavior TEXT, modifiers TEXT, event_type TEXT, start FLOAT, stop FLOAT);''' + os.linesep
            out += 'BEGIN TRANSACTION;'

            sqlTemplate = '''INSERT INTO events ( observation, date, subject, behavior, modifiers, event_type, start, stop ) VALUES ("{0}","{1}","{2}","{3}","{4}","{5}",{6},{7} );'''+ os.linesep

        if format_ == 'tab':
            fileName, _ = fd.getSaveFileName(self, 'Export aggregated events in tabular format', '' , 'Events file (*.tsv *.txt);;All files (*)')
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
                        print( UNPAIRED ,':',obsId , subject, behavior  )
                        print(rows)
                        continue

                    for idx, row in enumerate(rows):

                        if 'POINT' in self.eventType(behavior).upper():

                            if format_ == 'sql':
                                template = sqlTemplate
                            if format_ == 'tab':
                                template = tabTemplate

                            out += template.format( obsId.encode('UTF-8') , self.pj[OBSERVATIONS][obsId]['date'], subject.encode('UTF-8'), behavior.encode('UTF-8'), row[1].encode('UTF-8'), 'POINT', row[0], 0 )

                        if 'STATE' in self.eventType(behavior).upper():
                            if idx % 2 == 0:

                                if format_ == 'sql':
                                    template = sqlTemplate
                                if format_ == 'tab':
                                    template = tabTemplate

                                out += template.format( obsId.encode('UTF-8') , self.pj[OBSERVATIONS][obsId]['date'], subject.encode('UTF-8'), behavior.encode('UTF-8'), row[1].encode('UTF-8'), 'STATE', row[0],  rows[idx + 1][0] )


        if format_ == 'sql':
            out += 'END TRANSACTION;'


        with open(fileName, 'w') as f:
            f.write( out )

        self.statusbar.showMessage('Aggregated events exported successfully', 0)


    def media_file_info(self):
        '''
        show info about current video
        '''
        if self.observationId:
            
            out = ''
            import platform
            if platform.system() in ['Linux', 'Darwin']:
                

                for idx in self.pj[OBSERVATIONS][self.observationId]['file']:
                    
                    for file_ in self.pj[OBSERVATIONS][self.observationId]['file'][idx]:

                        r = os.system( 'file -b ' + file_ )
    
                        if not r:
                            out += '<b>'+os.path.basename(file_) + '</b><br>'
                            out += commands.getoutput('file -b ' + file_ ) + '<br>'


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

                QMessageBox.about(self, programName + ' - Media file information', out + '<br><br>Total duration: %s s' % (self.convertTime(self.mediaplayer.get_length()/1000)  ) )


        else:
            self.no_observation()


    def switch_playing_mode(self):
        '''
        switch between frame mode and VLC mode
        triggered by frame by frame button and toolbox item change
        '''

        if self.playerType == VLC:

            if self.playMode == FFMPEG:

                self.playMode = VLC

                logging.debug('new VLC time: {0}'.format( int( self.FFmpegGlobalFrame  * (1000/self.fps.values()[0]))))

                # seek VLC on current time from FFmpeg mode
                for idx, media in enumerate(self.pj[OBSERVATIONS][self.observationId]['file']['1']):
                    if self.FFmpegGlobalFrame < sum(self.duration[0:idx + 1]):
    
                        self.mediaListPlayer.play_item_at_index( idx )

                        while self.mediaListPlayer.get_state() != vlc.State.Playing:
                            time.sleep(2)
                            pass
                        self.mediaListPlayer.pause()

                        frameMedia = self.FFmpegGlobalFrame - sum(self.duration[0:idx])
                        break

                self.mediaplayer.set_time( int( frameMedia * (1000/self.fps.values()[0])) )

                self.toolBox.setCurrentIndex(0)

                self.FFmpegTimer.stop()
                
                logging.info( 'ffmpeg timer stopped') 

                # set thread for cleaning temp directory
                if self.ffmpeg_cache_dir_max_size:
                    self.cleaningThread.exiting = True

                self.timer.start()

            elif FFMPEG in self.availablePlayers:
                
                # check if multi mode
                if self.media_list2.count():

                    logging.warning( 'Frame-by-frame mode is not available in multi-player mode' )

                    app.beep()
                    self.actionFrame_by_frame.setChecked(False)
                    self.statusbar.showMessage('Frame-by-frame mode is not available in multi-player mode', 5000)

                    return
                
                self.playMode = FFMPEG

                if self.mediaListPlayer.get_state() == vlc.State.Playing:
                    self.mediaListPlayer.pause()

                self.timer.stop()
                
                # check temp dir for images from ffmpeg
                if not self.ffmpeg_cache_dir:
                    import tempfile
                    self.imageDirectory = tempfile.gettempdir()
                else:
                    self.imageDirectory = self.ffmpeg_cache_dir

                # load list of images in a set 
                if not self.imagesList:
                    import glob
                    self.imagesList.update(  [ f.replace( self.imageDirectory + os.sep, '' ).split('_')[0] for f in glob.glob(self.imageDirectory + os.sep + '*')  ] )

                logging.debug('frame-by-frame mode activated. Image directory {0}'.format( self.imageDirectory ))

                # show frame-by_frame tab
                self.toolBox.setCurrentIndex(1)
                
                
                currentTime = self.mediaplayer.get_time()
                currentFrame = round(currentTime / 40 )
        
                self.FFmpegGlobalFrame = currentFrame

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


        logging.info( 'new play mode: {0}'.format( self.playMode ))
            

    def snapshot(self):
        '''
        take snapshot of current video
        snapshot is saved on media path
        '''
        
        if self.pj[OBSERVATIONS][self.observationId]['type'] in [MEDIA]:
        
            if self.playerType == VLC:
    
                if self.playMode == FFMPEG:
    
                    for idx,media in enumerate(self.pj[OBSERVATIONS][self.observationId]['file']['1']):
                        if self.FFmpegGlobalFrame < sum(self.duration[0:idx + 1]):
        
                            dirName, fileName = os.path.split( media )
                            self.lbFFmpeg.pixmap().save(dirName + os.sep + os.path.splitext( fileName )[0] +  '_'+ str(self.FFmpegGlobalFrame) +'.png')
                            break
    
                else:  # VLC
    
                    current_media_path = urlparse.urlparse(self.mediaplayer.get_media().get_mrl()).path
                    dirName, fileName = os.path.split( current_media_path )
                    time = str(self.mediaplayer.get_time())
                    self.mediaplayer.video_take_snapshot(0, dirName + os.sep + os.path.splitext( fileName )[0] +  '_'+ time +'.png' ,0,0)
                    
                    # check if multi mode
                    if self.media_list2.count():
                        current_media_path = urlparse.urlparse(self.mediaplayer2.get_media().get_mrl()).path
                        dirName, fileName = os.path.split( current_media_path )
                        time = str(self.mediaplayer2.get_time())
                        self.mediaplayer2.video_take_snapshot(0, dirName + os.sep + os.path.splitext( fileName )[0] +  '_'+ time +'.png' ,0,0)
                        




    def video_normalspeed_activated(self):
        '''
        set playing speed at normal speed
        '''


        if self.playerType == VLC:

            if self.playMode == FFMPEG:
    
                if self.FFmpegTimer.interval() > 0:
                    self.FFmpegTimer.setInterval( 40)
                self.lbSpeed.setText('x%.3f' %  1.0)

            else:

                self.play_rate = 1
                self.mediaplayer.set_rate(self.play_rate)
    
                if self.media_list2.count():
                    self.mediaplayer2.set_rate(self.play_rate)
    
                self.lbSpeed.setText('x' + str(self.play_rate))
    
                logging.info('play rate: {0}'.format(self.play_rate))





    def video_faster_activated(self):
        '''
        increase playing speed by play_rate_step value
        '''
        if self.playerType == VLC:

            if self.playMode == FFMPEG:
    
                if self.FFmpegTimer.interval() > 0:
                    self.FFmpegTimer.setInterval( self.FFmpegTimer.interval() - 2 )
                self.lbSpeed.setText('x%.3f' %  (1/self.FFmpegTimer.interval()/ (self.fps.values()[0]/1000)))

            else:

                if self.play_rate + self.play_rate_step <= 8:
                    self.play_rate += self.play_rate_step
                    self.mediaplayer.set_rate(self.play_rate)
                    
                    if self.media_list2.count():
                        self.mediaplayer2.set_rate(self.play_rate)
                    
                    self.lbSpeed.setText('x' + str(self.play_rate))
    
                logging.info('play rate: {0}'.format(self.play_rate))




    def video_slower_activated(self):
        '''
        decrease playing speed by play_rate_step value
        '''

        if self.playerType == VLC:

            if self.playMode == FFMPEG:

                if self.FFmpegTimer.interval() < 10000:
                    self.FFmpegTimer.setInterval( self.FFmpegTimer.interval() + 2 )
    
                self.lbSpeed.setText('x%.3f' %  (1/self.FFmpegTimer.interval()/ (self.fps.values()[0]/1000)))

            else:

                if self.play_rate - self.play_rate_step >= 0.1:
                    self.play_rate -= self.play_rate_step
                    self.mediaplayer.set_rate(self.play_rate)
        
                    if self.media_list2.count():
                        self.mediaplayer2.set_rate(self.play_rate)
        
                    self.lbSpeed.setText('x' + str(self.play_rate))
    
                logging.info('play rate: {0}'.format(self.play_rate))




    def add_event(self):
        '''
        manually add event to observation
        '''
        
        if not self.observationId:
            self.no_observation()
            return

        editWindow = DlgEditEvent(self.DEBUG)
        editWindow.setWindowTitle('Add a new event')

        # send pj to edit_event window
        editWindow.pj = self.pj

        if self.timeFormat == HHMMSS:
            editWindow.dsbTime.setVisible(False)

        if self.timeFormat == S:
            editWindow.teTime.setVisible(False)


        sortedSubjects = [''] + sorted( [ self.pj['subjects_conf'][x]['name'] for x in self.pj['subjects_conf'] ])

        editWindow.cobSubject.addItems( sortedSubjects )

        sortedCodes = sorted( [ self.pj['behaviors_conf'][x]['code'] for x in self.pj['behaviors_conf'] ])

        editWindow.cobCode.addItems( sortedCodes )

        # activate signal
        editWindow.cobCode.currentIndexChanged.connect(editWindow.codeChanged)

        editWindow.currentModifier = ''

        if editWindow.exec_():  #button OK

            if self.timeFormat == HHMMSS:
                newTime = time2seconds(editWindow.teTime.time().toString('hh:mm:ss.zzz'))

            if self.timeFormat == S:
                newTime = editWindow.dsbTime.value()

            memTime = newTime

            # get modifier(s)
            # check mod type (QPushButton or QDialog)
            if type(editWindow.mod)  is select_modifiers.ModifiersRadioButton:
                modifiers = editWindow.mod.getModifiers()
                if self.DEBUG: print('r 3441 modifiers', modifiers)

                if len(modifiers) == 1:
                    modifier_str = modifiers[0]
                    if modifier_str == 'None':
                        modifier_str = ''
                else:
                    modifier_str = '|'.join( modifiers )

            #QPushButton coding map
            if type(editWindow.mod)  is QPushButton:
                modifier_str = editWindow.mod.text().split('\n')[1].replace('Area(s): ','')


            new_event = { 'time': newTime, \
            'subject': editWindow.cobSubject.currentText(), \
            'code': editWindow.cobCode.currentText() ,\
            'type': '',\
            'modifier': modifier_str,\
            'comment': editWindow.leComment.toPlainText() }


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



    def edit_event(self):
        '''
        edit each event items from the selected row
        '''
        if not self.observationId:
            self.no_observation()
            return

        if self.twEvents.selectedItems():

            editWindow = DlgEditEvent(self.DEBUG)
            editWindow.setWindowTitle('Edit event parameters')

            # pass project to window
            editWindow.pj = self.pj
            editWindow.currentModifier = ''

            row = self.twEvents.selectedItems()[0].row()   # first selected event

            if self.timeFormat == HHMMSS:
                editWindow.dsbTime.setVisible(False)

                time = QTime()
                h,m,s = seconds2time( self.pj[OBSERVATIONS][self.observationId][EVENTS][row][ 0 ] ).split(':')
                s, ms = s.split('.')
                time.setHMS(int(h),int(m),int(s),int(ms))
                editWindow.teTime.setTime( time )

            if self.timeFormat == S:
                editWindow.teTime.setVisible(False)

                editWindow.dsbTime.setValue( self.pj[OBSERVATIONS][self.observationId][EVENTS][row][ 0 ] )


            sortedSubjects = [''] + sorted( [ self.pj['subjects_conf'][x]['name'] for x in self.pj['subjects_conf'] ])
            
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
            editWindow.currentModifier = self.pj[OBSERVATIONS][self.observationId][EVENTS][row][ pj_obs_fields['modifier'] ]

            # comment
            editWindow.leComment.setPlainText( self.pj[OBSERVATIONS][self.observationId][EVENTS][row][ pj_obs_fields['comment'] ])

            # load modifiers
            editWindow.codeChanged()
            
            # activate signal
            editWindow.cobCode.currentIndexChanged.connect(editWindow.codeChanged)

            if editWindow.exec_():  #button OK
            
                self.projectChanged = True

                if self.timeFormat == HHMMSS:
                    newTime = time2seconds(editWindow.teTime.time().toString('hh:mm:ss.zzz'))

                if self.timeFormat == S:
                    newTime = editWindow.dsbTime.value()

                # check mod type (QPushButton or QDialog)
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


                self.pj[OBSERVATIONS][self.observationId][EVENTS][row] = [newTime, editWindow.cobSubject.currentText(), editWindow.cobCode.currentText(), modifier_str ,editWindow.leComment.toPlainText()]
                self.pj[OBSERVATIONS][self.observationId][EVENTS].sort()
                self.loadEventsInTW( self.observationId )

        else:
            QMessageBox.warning(self, programName, 'Select an event to edit')

    def no_media(self):
        QMessageBox.warning(self, programName, 'There is no media available')

    def no_project(self):
        QMessageBox.warning(self, programName, 'There is no project')


    def no_observation(self):
        QMessageBox.warning(self, programName, 'There is no current observation')


    def twConfiguration_doubleClicked(self):
        '''
        add observation by double click
        '''
        if self.observationId:
            if self.twConfiguration.selectedIndexes():
    
                obs_idx = self.twConfiguration.selectedIndexes()[0].row()
                code = self.twConfiguration.item(obs_idx, 1).text()
                self.writeEvent(  self.pj['behaviors_conf'] [ [ x for x in self.pj['behaviors_conf'] if self.pj['behaviors_conf'][x]['code'] == code][0] ], self.getLaps())

        else: 
            self.no_observation()

    def actionAbout_activated(self):
        '''
        about window
        '''
        import platform

        ver = __version__
        if __RC__:
            ver += ' RC' + __RC__

        players = []
        players.append( "VLC media player v. %s" % bytes_to_str(vlc.libvlc_get_version()))
        if FFMPEG in self.availablePlayers:
            players.append('FFmpeg for frame-by-frame mode')

        QMessageBox.about(self, "About " + programName,
        """<b>%s</b> v. %s - %s
        <p>Copyright &copy; 2012-2015 Olivier Friard - University of Torino - Italy<br>
        <br>
        The author would like to acknowledge Sergio Castellano, Marco Gamba, Valentina Matteucci and Laura Ozella for their precious help.<br>
        <br>
        See <a href="http://penelope.unito.it/boris">penelope.unito.it/boris</a> for more details.<br>
        <p>Python %s - Qt %s - PySide %s on %s<br><br>
        Available media players:<br>%s""" % \
        (programName, ver, __version_date__, platform.python_version(), PySide.QtCore.__version__, PySide.__version__, platform.system(), '<br>'.join(players)))



    def hsVideo_sliderMoved(self):

        '''
        media position slider moved
        adjust media position
        '''

        if self.pj[OBSERVATIONS][self.observationId]['type'] in [MEDIA]:

            sliderPos = self.hsVideo.value() / (slider_maximum - 1)

            if self.playerType == VLC:
                videoPosition = sliderPos * self.mediaplayer.get_length()
    
                self.mediaplayer.set_time( int(videoPosition) )
    
                if self.media_list2.count():
                    if videoPosition <= self.mediaplayer2.get_length():
                        self.mediaplayer2.set_time( int(videoPosition) )
                    else:
                        self.mediaplayer2.set_time( self.mediaplayer2.get_length() )


    def timer_out(self):
        '''
        indicate the video current position and total length for VLC player

        Time offset is NOT added!

        triggered by timer

        '''

        if self.pj[OBSERVATIONS][self.observationId]['type'] in [MEDIA]:

            # cumulative time
            currentTime = self.getLaps() * 1000   

            # current media time
            mediaTime = self.mediaplayer.get_time()

            # check if second video
            if self.media_list2.count():
                
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

                        logging.debug('mediaTime2 {0}'.format(mediaTime2))
                        
                        if mediaTime2 < abs(self.pj[OBSERVATIONS][self.observationId][TIME_OFFSET_SECOND_PLAYER] *1000):


                            if self.mediaListPlayer.get_state() == vlc.State.Playing:
                                
                                self.mediaplayer.set_time( 0 )
                                self.mediaListPlayer.pause()
                        else:
                            if self.mediaListPlayer2.get_state() == vlc.State.Playing:
                                self.mediaListPlayer.play()
                        
                        


            currentTimeOffset = Decimal(currentTime /1000) + Decimal(self.pj[OBSERVATIONS][self.observationId][TIME_OFFSET])

            #globalCurrentTime = (sum(self.duration[0 : self.media_list.index_of_item(self.mediaplayer.get_media()) ]) + self.mediaplayer.get_time())

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
                    if len(  [ x[ pj_obs_fields['code'] ] for x in self.pj[OBSERVATIONS][self.observationId][EVENTS ] if x[ pj_obs_fields['subject'] ] == '' and x[ pj_obs_fields['code'] ] == sbc and x[ pj_obs_fields['time'] ] <= currentTimeOffset  ] ) % 2: ### test if odd
                        self.currentStates[''].append(sbc)

                # add states for all configured subjects
                for idx in self.pj['subjects_conf']:

                    # add subject index
                    self.currentStates[ idx ] = []
                    for sbc in StateBehaviorsCodes:
                        if len(  [ x[ pj_obs_fields['code'] ] for x in self.pj[OBSERVATIONS][self.observationId][EVENTS ] if x[ pj_obs_fields['subject'] ] == self.pj['subjects_conf'][idx]['name'] and x[ pj_obs_fields['code'] ] == sbc and x[ pj_obs_fields['time'] ] <= currentTimeOffset  ] ) % 2: ### test if odd
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
                for idx in sorted( self.pj['subjects_conf'].keys() ):
                    self.twSubjects.item(int(idx), len( subjectsFields ) ).setText( ','.join(self.currentStates[idx]) )


                # update status bar
                msg = ''

                if self.mediaListPlayer.get_state() == vlc.State.Playing or self.mediaListPlayer.get_state() == vlc.State.Paused:
                    msg = '%s: <b>%s / %s</b>' % ( self.mediaplayer.get_media().get_meta(0),\
                                                   self.convertTime(Decimal(mediaTime / 1000)  ),\
                                                   self.convertTime(Decimal(self.mediaplayer.get_length() / 1000) ) )
                    
                    '''
                    self.convertTime(Decimal(mediaTime / 1000) + self.pj[OBSERVATIONS][self.observationId][TIME_OFFSET] ),\
                    self.convertTime(Decimal(self.mediaplayer.get_length() / 1000) + self.pj[OBSERVATIONS][self.observationId][TIME_OFFSET]) )
                    '''

                    if self.media_list.count() > 1:
                        msg += ' | total: <b>%s / %s</b>' % ( (self.convertTime( Decimal(currentTime/1000) ),\
                                                               self.convertTime( Decimal(totalGlobalTime / 1000) ) ) )

                        '''
                        self.convertTime( Decimal(totalGlobalTime / 1000)+ self.pj[OBSERVATIONS][self.observationId][TIME_OFFSET]) ) )
                        '''

                    if self.mediaListPlayer.get_state() == vlc.State.Paused:
                        msg += ' (paused)'

                if msg:

                    # show time on status bar
                    self.lbTime.setText( msg )

                    # set video scroll bar
                    self.hsVideo.setValue(mediaTime / self.mediaplayer.get_length() * (slider_maximum - 1))

            else:

                self.statusbar.showMessage('Media length not available now', 0)



    def load_obs_in_lwConfiguration(self):
        '''
        fill behaviors configuration table widget with behaviors from pj
        '''

        self.twConfiguration.setRowCount(0)

        if self.pj['behaviors_conf']:

            for idx in sorted(self.pj['behaviors_conf'].keys()):

                if self.DEBUG: print('conf', idx)

                self.twConfiguration.setRowCount(self.twConfiguration.rowCount() + 1)
                
                for col, field in enumerate(['key','code','type','description','modifiers','excluded']):
                    self.twConfiguration.setItem(self.twConfiguration.rowCount() - 1, col , QTableWidgetItem( self.pj['behaviors_conf'][idx][field] ))
                

    def load_subjects_in_twSubjects(self):
        '''
        fill subjects table widget with subjects from self.subjects_conf
        '''

        self.twSubjects.setRowCount(0)
        
        for idx in sorted( self.pj[SUBJECTS].keys() ):

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
            
            if self.DEBUG: print( 'row',row )

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

        
        stateEventsList = [ self.pj['behaviors_conf'][x]['code'] for x in self.pj['behaviors_conf'] if STATE in self.pj['behaviors_conf'][x]['type'].upper() ]

        if self.DEBUG: print( 'state events list:', stateEventsList)

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
        '''

        # add time offset
        memTime += + Decimal(self.pj[OBSERVATIONS][self.observationId][TIME_OFFSET]).quantize(Decimal('.001'))

        if self.DEBUG: print('add event to observation id:', self.observationId)

        if self.DEBUG: print('event', event)

        # check if a same event is already in events list (time, subject, code)
        if self.checkSameEvent( self.observationId, memTime, self.currentSubject, event['code'] ):
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
    
    
                if self.DEBUG: print('modifier', modifier_str)
        else:
            modifier_str = event['from map']


        # update current state

        if 'STATE' in event['type'].upper():

            if self.DEBUG: print('self.currentSubject:', self.currentSubject)
            if self.DEBUG: print('self.currentStates:',self.currentStates)

            if self.currentSubject:
                csj = []
                for idx in self.currentStates:
                    if idx in self.pj['subjects_conf'] and self.pj['subjects_conf'][idx]['name'] == self.currentSubject:
                        csj = self.currentStates[idx]
                        break

            else:  # no focal subject
                if self.DEBUG: print('no focal self.currentStates', self.currentStates)
                csj = self.currentStates['']

            if self.DEBUG: print('csj:', csj)   ### current state for current subject
            if self.DEBUG: print('code modifier', event['code'], event['modifiers'])

            # current modifiers
            cm = {}
            for cs in csj :
                for ev in self.pj[OBSERVATIONS][self.observationId][EVENTS ]:
                    if ev[0] > memTime:   #time
                        break
    
                    if ev[1] == self.currentSubject:   # current subject name
                        if ev[2] == cs:   #code
                            cm[cs] = ev[3]

            if self.DEBUG: print('cm', cm)


            for cs in csj :
                #if cs in event['excluded'].split(','):
                if (event['excluded']  and cs in event['excluded'].split(',') ) or ( event['code'] == cs and  cm[cs] != modifier_str) :
                    # add excluded state event to observations (= STOP them)
                    self.pj[OBSERVATIONS][self.observationId][EVENTS].append( [memTime - Decimal('0.001'), self.currentSubject, cs, cm[cs], ''] )



        # check if coding map
        '''
        if 'from map' in event:
            modifier_str = event['from map']
        '''

        # remove key code from modifiers
        modifier_str = re.sub(' \(.\)', '', modifier_str)

        # add event to pj        
        self.pj[OBSERVATIONS][self.observationId][EVENTS].append( [memTime, self.currentSubject, event['code'], modifier_str, ''] )

        # sort events in pj
        self.pj[OBSERVATIONS][self.observationId][EVENTS].sort()

        # reload all events in tw
        self.twEvents.setRowCount(0)
        for o in self.pj[OBSERVATIONS][self.observationId][EVENTS]:

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

            # modifier
            item = QTableWidgetItem( o[ 4 ]  )
            self.twEvents.setItem(self.twEvents.rowCount() - 1, 5, item)

        self.update_events_start_stop()

        item = self.twEvents.item(  [i for i,t in enumerate( self.pj[OBSERVATIONS][self.observationId][EVENTS] ) if t[0] == memTime][0], 0  )

        self.twEvents.scrollToItem( item )

        self.projectChanged = True




    def fill_lwDetailed(self, obs_key, memLaps):
        '''
        fill listwidget with all events coded by key
        return index of behaviour
        '''

        ### check if key duplicated
        if self.DEBUG: print('fill_lwDetail function')

        items = []
        for idx in self.pj['behaviors_conf']:
            if self.pj['behaviors_conf'][idx]['key'] == obs_key:

                txt = self.pj['behaviors_conf'][idx]['code']
                if  self.pj['behaviors_conf'][idx]['description']:
                    txt += ' - ' + self.pj['behaviors_conf'][idx]['description']
                items.append(txt)

                self.detailedObs[txt] = idx

        response = ''

        item, ok = QInputDialog.getItem(self, programName, 'The <b>' + obs_key + '</b> key codes more events.<br>Choose the correct one:' , items, 0, False)

        if ok and item:
            if self.DEBUG:print('selected code:', item)

            obs_idx = self.detailedObs[ item ]
            if self.DEBUG:print('obs_idx', obs_idx)
            
            return obs_idx
            #self.writeEvent(self.pj['behaviors_conf'][obs_idx], memLaps)

        else:

            return None


    def getLaps(self):
        '''
        return cumulative laps time from begining of observation

        as Decimal in seconds

        no more add time offset!
        #add time offset for video observation if any
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

                    memLaps = Decimal( self.FFmpegGlobalFrame * ( 1000 / self.fps.values()[0]) / 1000).quantize(Decimal('.001')) 

                    return memLaps

                else:

                    # cumulative time
                    memLaps = Decimal(str(round(( sum(self.duration[0 : self.media_list.index_of_item(self.mediaplayer.get_media()) ]) \
                              + self.mediaplayer.get_time()) / 1000 ,3))) \
                    
                    '''
                    memLaps = Decimal(str(round(( sum(self.duration[0 : self.media_list.index_of_item(self.mediaplayer.get_media()) ]) \
                              + self.mediaplayer.get_time()) / 1000 ,3))) \
                              + self.pj[OBSERVATIONS][self.observationId][TIME_OFFSET]
                    '''
                    return memLaps





    def keyPressEvent(self, event):
        
        '''if self.DEBUG: print "keyPressEvent function"'''

        '''
        if (event.modifiers() & Qt.ShiftModifier):
            print 'Shift!'

        print QApplication.keyboardModifiers()
        
        http://qt-project.org/doc/qt-5.0/qtcore/qt.html#Key-enum
        
        ESC: 16777216
        '''

        if not self.observationId:
            return
        
        # beep
        if self.confirmSound:
            app.beep()

        ### check if media ever played
        if self.playerType == VLC:
            if self.mediaListPlayer.get_state() == vlc.State.NothingSpecial:
                return

        ek = event.key()

        logging.debug('key event {0}'.format( ek ))

        '''
        if ek in function_keys:
            print('F key', function_keys[ek])
        '''
        


        if ek in [16777248,  16777249, 16777217, 16781571]: ### shift tab ctrl
            return


        # play / pause with space bar
        if ek == Qt.Key_Space and self.pj[OBSERVATIONS][self.observationId]['type'] in [MEDIA]:   
            self.pause_video()
            return

        # jump with arrow keys
        '''
        FIXME jump with arrow keys
        if ek in [Qt.Key_Left, Qt.Key_Right, Qt.Key_Down, Qt.Key_Up, Qt.Key_PageUp, Qt.Key_PageDown]:

            if ek == Qt.Key_Up or ek == Qt.Key_PageUp :
                self.jumpForward_activated()

            if ek == Qt.Key_Down or ek == Qt.Key_PageDown:
                self.jumpBackward_activated()
            
            if ek == Qt.Key_Left:
                pass
            
            if ek == Qt.Key_Right:
                if self.playerType == OPENCV:
                    self.FFmpegTimerOut()

            return
        '''


        if self.playerType == VLC and self.playMode == FFMPEG:

            # /   one frame back
            if ek == 47:  # /   one frame back

                logging.debug('current frame {0}'.format( self.FFmpegGlobalFrame ))

                if self.FFmpegGlobalFrame > 1:
                    self.FFmpegGlobalFrame -= 2
    
                    newTime = 1000.0 * self.FFmpegGlobalFrame / self.fps.values()[0]
    
                    self.FFmpegTimerOut()

                    logging.debug('new frame {0}'.format( self.FFmpegGlobalFrame ))

                return

            ### *  read next frame
            if ek == 42:  

                logging.debug('(next) current frame {0}'.format( self.FFmpegGlobalFrame ))

                self.FFmpegTimerOut()
                
                logging.debug('(next) new frame {0}'.format( self.FFmpegGlobalFrame ))
                
                return


        if not self.pj['behaviors_conf']:
            QMessageBox.about(self, programName, 'Behaviours are not configured')
            return

        obs_key = None
        
        ### check if key is function key
        if (ek in function_keys):
            flag_function = True
            if function_keys[ ek ] in [self.pj['behaviors_conf'][x]['key'] for x in self.pj['behaviors_conf']]:
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
                ek_unichr = unichr(ek)

            for o in self.pj['behaviors_conf']:

                if self.pj['behaviors_conf'][o]['key'] == ek_unichr:
                    obs_idx = o
                    count += 1

            # check if key codes more events
            if count > 1:
                if self.DEBUG: print('multi code key')

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

                # check if coding map
                if 'coding map' in self.pj['behaviors_conf'][obs_idx] and self.pj['behaviors_conf'][obs_idx]['coding map']:

                    # pause if media and media playing
                    if self.pj[OBSERVATIONS][self.observationId]['type'] in [MEDIA]:
                        if self.playerType == VLC:
                            memState = self.mediaListPlayer.get_state()
                            if memState == vlc.State.Playing:
                                self.pause_video()
        
                    self.codingMapWindow = coding_map.codingMapWindowClass( self.pj['coding_map'][ self.pj['behaviors_conf'][obs_idx]['coding map'] ] ) 

                    self.codingMapWindow.resize(640, 640)
                    if self.codingMapWindowGeometry:
                         self.codingMapWindow.restoreGeometry( self.codingMapWindowGeometry )

                    if not self.codingMapWindow.exec_():
                        return

                    self.codingMapWindowGeometry = self.codingMapWindow.saveGeometry()
                    if self.DEBUG: print('returned codes', self.codingMapWindow.getCodes())
        
                    '''
                    {    "key": "J",   "code": "jump",    "description": "jumping",  "modifiers": "foo,bar|foo,bar|foo,bar",     "excluded": "",   "type": "Point event"   }
                    '''
                    event = dict( self.pj['behaviors_conf'][obs_idx] )
                    event['from map'] = self.codingMapWindow.getCodes()

                    self.writeEvent(event, memLaps)
        
                    # restart media
                    if self.pj[OBSERVATIONS][self.observationId]['type'] in [MEDIA]:
        
                        if self.playerType == VLC:
                            if memState == vlc.State.Playing:
                                self.play_video()
        
                else: # no coding map

                    self.writeEvent(self.pj['behaviors_conf'][obs_idx], memLaps)

            elif count == 0:

                ### check if key defines a suject
                flag_subject = False
                for idx in self.pj['subjects_conf']:
                
                    if ek_unichr == self.pj['subjects_conf'][idx]['key']:
                        flag_subject = True
                        if self.DEBUG: print('subject', ek_unichr , self.pj['subjects_conf'][idx]['name'])
                        
                        ### select or deselect current subject
                        if self.currentSubject == self.pj['subjects_conf'][idx]['name']:
                            self.deselectSubject()
                        else:
                            self.selectSubject( self.pj['subjects_conf'][idx]['name'] )

                if not flag_subject:

                    if self.DEBUG: print('%s key not assigned' % ek_unichr)
                    
                    self.statusbar.showMessage( 'Key not assigned (%s)' % ek_unichr , 5000)


        ### coding map
        '''
        if ek == 16777216:    ### ESC

            ### pause if media and media playing
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

            ### restart media
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
        if self.DEBUG: print('twEvents_doubleClicked')

        if self.twEvents.selectedIndexes():

            row = self.twEvents.selectedIndexes()[0].row()  
        
            if ':' in self.twEvents.item(row, 0).text():
                time = time2seconds(  self.twEvents.item(row, 0).text()  )
            else:
                time  = Decimal( self.twEvents.item(row, 0).text() )

            # substract time offset
            time -= self.pj[OBSERVATIONS][self.observationId][TIME_OFFSET]

            if time + self.repositioningTimeOffset >= 0:
                newtime = (time + self.repositioningTimeOffset ) * 1000
            else:
                newtime = 0


            if self.playMode == VLC:

                if self.DEBUG: print('self.mediaListPlayer.get_state()', self.mediaListPlayer.get_state())
    
                # remember if player paused (go previous will start playing)
                flagPaused = self.mediaListPlayer.get_state() == vlc.State.Paused
    
                if self.DEBUG: print('newtime', newtime)
    
                if len(self.duration) > 1:
    
                    if self.DEBUG: print('durations:', self.duration)
    
                    tot = 0
                    for idx, d in enumerate(self.duration):
                        if newtime >= tot and newtime < d:
                            if self.DEBUG: print('video index:', idx)
                            self.mediaListPlayer.play_item_at_index( idx )
                            if self.DEBUG: print('newtime - tot:',  int(newtime) - tot)
                            self.mediaplayer.set_time( int(newtime) - tot )
                        tot += d
    
                else:   # 1 video
    
                    self.mediaplayer.set_time( int(newtime) )
                    
                    if self.media_list2.count():
                        self.mediaplayer2.set_time( int(newtime) )
    
    
                if flagPaused and self.mediaListPlayer.get_state() != vlc.State.Paused:
    
                    if self.DEBUG: print('new state',self.mediaListPlayer.get_state())
                    while self.mediaListPlayer.get_state() != vlc.State.Playing:
                        if self.DEBUG: print('state (while)',self.mediaListPlayer.get_state())
                        time.sleep(2)
                        pass
    
                    self.mediaListPlayer.pause()
    
                    if self.media_list2.count():
                        self.mediaListPlayer2.pause()



            if self.playMode == FFMPEG:

                
                currentFrame = round( newtime/ 40 )
        
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
    
                ### select or deselect current subject
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
            
            ### list of rows to delete (set for unique)
            rows = set( [ item.row() for item in self.twEvents.selectedIndexes() ])
            
            if self.DEBUG: print([ event for idx,event in enumerate(self.pj[OBSERVATIONS][self.observationId][EVENTS]) if not idx in rows])
            
            self.pj[OBSERVATIONS][self.observationId][EVENTS] = [ event for idx,event in enumerate(self.pj[OBSERVATIONS][self.observationId][EVENTS]) if not idx in rows]

            self.projectChanged = True

            self.loadEventsInTW( self.observationId )



    def export_tabular_events_ods(self):
        '''
        export events from selected observations in ODS format
        '''

        # ask user observations to analyze
        result, selected_observations = self.selectObservations( MULTIPLE )

        # filter subjects in observations
        observed_subjects = self.extract_observed_subjects( selected_observations )

        # ask user subject to export
        selected_subjects = self.select_subjects( observed_subjects )

        if self.DEBUG: print('\nselected subjects', selected_subjects)

        if not selected_subjects:
            return


        if len(selected_observations) > 1:  # choose directory for exporting more observations
            fd = QFileDialog(self)
            exportDir = fd.getExistingDirectory(self, 'Choose a directory to export events', os.path.expanduser('~'), options=fd.ShowDirsOnly)
            if not exportDir:
                return

        try:
            import ezodf
        except:
            print('Function not available')
            return

        for obsId in selected_observations:
            
            if len(selected_observations) == 1:
                fd = QFileDialog(self)
                fileName, _ = fd.getSaveFileName(self, 'Export events', obsId + '.ods' , 'Open Document Spreadsheet (*.ods);;All files (*)')
                if not fileName:
                    return
            else:
                fileName = exportDir + os.sep + safeFileName(obsId) + '.ods'


            eventsWithStatus =  self.update_events_start_stop2( self.pj[OBSERVATIONS][obsId][EVENTS] ) 

            max_modifiers = 0
            for event in eventsWithStatus:
                for c in pj_events_fields:
                    if c == 'modifier' and event[pj_obs_fields[c]]:
                        max_modifiers = max( max_modifiers, len(event[pj_obs_fields[c]].split('|')) )
            
            if self.DEBUG: print('max_modifiers',max_modifiers)

            # media file number
            mediaNb = 0
            if self.pj[OBSERVATIONS][obsId]['type'] in [MEDIA]:
                for idx in self.pj[OBSERVATIONS][obsId]['file']:
                    for media in self.pj[OBSERVATIONS][obsId]['file'][idx]:
                        mediaNb += 1

            ods = ezodf.newdoc('ods', fileName)

            # check number of rows for independent variables
            if "independent_variables" in self.pj[OBSERVATIONS][obsId]:
                nbVar = len(self.pj[OBSERVATIONS][obsId]["independent_variables"])
            else:
                nbVar = 0

            sheet = ezodf.Sheet('Events for ' + obsId, size=(len( eventsWithStatus ) + mediaNb + 20+ nbVar+4, 8 + max_modifiers)) 
            ods.sheets += sheet

            row = 0
            
            # observation id
            sheet[ row, 0].set_value( 'Observation id' )
            sheet[ row, 1].set_value( obsId )
            row += 2
            
            # media file name
            if self.pj[OBSERVATIONS][obsId]['type'] in [MEDIA]:
                sheet[ row, 0].set_value( 'Media file(s)' )
            else:
                sheet[ row, 0].set_value( 'Live observation' )
            row += 1

            if self.pj[OBSERVATIONS][obsId]['type'] in [MEDIA]:

                for idx in self.pj[OBSERVATIONS][obsId]['file']:
                    for media in self.pj[OBSERVATIONS][obsId]['file'][idx]:
                        sheet[ row, 0].set_value( 'Player #{0}'.format(idx) )
                        sheet[ row, 1].set_value( media )
                        row += 1

            row += 1

            # date
            if "date" in self.pj[OBSERVATIONS][obsId]:
                sheet[ row, 0].set_value( 'Observation date' )
                sheet[ row, 1].set_value( self.pj[OBSERVATIONS][obsId]["date"].replace('T',' ') )

            row += 2

            # description
            if "description" in self.pj[OBSERVATIONS][obsId]:
                sheet[ row, 0].set_value( 'Description' )
                sheet[ row, 1].set_value( self.pj[OBSERVATIONS][obsId]["description"].replace(os.linesep, ' ') )

            row += 2

            # time offset
            if "time offset" in self.pj[OBSERVATIONS][obsId]:
                sheet[ row, 0].set_value( 'Time offset (s)' )
                sheet[ row, 1].set_value( self.pj[OBSERVATIONS][obsId]["time offset"] )

            row += 2


            # independant variables
            if "independent_variables" in self.pj[OBSERVATIONS][obsId]:
                sheet[ row, 0].set_value( 'independent variables' )
                row += 1
                sheet[ row, 0].set_value('variable') 
                sheet[ row, 1].set_value('value')
                row += 1

                for variable in self.pj[OBSERVATIONS][obsId]["independent_variables"]:
                    sheet[ row, 0].set_value(variable) 
                    sheet[ row, 1].set_value(self.pj[OBSERVATIONS][obsId]["independent_variables"][variable])
                    row += 1

            row += 2

            

            # write header
            col = 0
            for c in pj_events_fields:
                if c == 'modifier':
                    for x in range(1, max_modifiers + 1):
                        sheet[ row, col].set_value('Modifier %d' % x )
                        col += 1

                else:
                    sheet[ row, col].set_value( c )
                    col += 1

            sheet[ row, col].set_value( 'status' )

            row += 1

            out = ''
            for event in eventsWithStatus:

                if (event[ pj_obs_fields['subject'] ] in selected_subjects) \
                   or (event[ pj_obs_fields['subject'] ] == '' and 'No focal subject' in selected_subjects):

                    col = 0
                    for c in pj_events_fields:

                        if c == 'modifier':
                            if event[pj_obs_fields[c]]:
                                modifiers = event[pj_obs_fields[c]].split('|')
                                while len(modifiers) < max_modifiers:
                                    modifiers.append('')
    
                                for m in modifiers:
                                    sheet[ row, col].set_value( m )
                                    col += 1
                            else:
                                col += 1

                        elif c == 'time':
                            sheet[ row, col].set_value( float( event[pj_obs_fields[c]]) )
                            col += 1

                        elif c == 'comment':
                            sheet[ row, col].set_value( event[pj_obs_fields[c]].replace(os.linesep, ' ') )
                            col += 1

                        else:
                            sheet[ row, col].set_value(  event[pj_obs_fields[c]]  ) 
                            col += 1


                    # append status START/STOP
                    sheet[ row, col].set_value( event[-1] )

                    row += 1

            ods.save()

    def export_tabular_events(self):
        '''
        export events from selected observations to plain text file (tsv)
        '''

        # ask user observations to analyze
        result, selected_observations = self.selectObservations( MULTIPLE )

        # filter subjects in observations
        observed_subjects = self.extract_observed_subjects( selected_observations )

        # ask user subject to export
        selected_subjects = self.select_subjects( observed_subjects )

        if self.DEBUG: print('\nselected subjects', selected_subjects)

        if not selected_subjects:
            return


        if len(selected_observations) >1:  # choose directory for exporting more observations
            fd = QFileDialog(self)
            exportDir = fd.getExistingDirectory(self, 'Choose a directory to export events', os.path.expanduser('~'), options=fd.ShowDirsOnly)
            if not exportDir:
                return

        for obsId in selected_observations:
            
            if len(selected_observations) == 1:
                fd = QFileDialog(self)
                fileName, _ = fd.getSaveFileName(self, 'Export events', obsId + '.tsv' , 'Events file (*.tsv *.txt);;All files (*)')
                if not fileName:
                    return
            else:
                fileName = exportDir + os.sep + safeFileName(obsId) + '.tsv'
            
            with open( fileName, 'w') as outfile:

                # observation id
                outfile.write('Observation id\t{obsId}{eol}'.format(obsId = obsId, eol = os.linesep))
                outfile.write(os.linesep)

                # media file name
                outfile.write('Media file(s){0}'.format(os.linesep))
                if self.pj[OBSERVATIONS][obsId]['type'] in [MEDIA]:
                    for idx in self.pj[OBSERVATIONS][obsId]['file']:
                        for media in self.pj[OBSERVATIONS][obsId]['file'][idx]:
                            outfile.write('Player #{0}\t{1}{2}'.format(idx, media, os.linesep) )

                outfile.write(os.linesep)

                # date
                if "date" in self.pj[OBSERVATIONS][obsId]:
                    outfile.write('Observation date\t{0}{1}'.format(self.pj[OBSERVATIONS][obsId]["date"].replace('T',' '),os.linesep))
                outfile.write(os.linesep)


                # description
                if "description" in self.pj[OBSERVATIONS][obsId]:
                    outfile.write('Description\t{0}{1}'.format(self.pj[OBSERVATIONS][obsId]["description"]..replace('\r\n',' ').replace('\n',' ').replace('\r',' ' ),os.linesep))
                outfile.write(os.linesep)

                # time offset
                if "time offset" in self.pj[OBSERVATIONS][obsId]:
                    outfile.write('Time offset (s)\t{0}{1}'.format(self.pj[OBSERVATIONS][obsId]["time offset"],os.linesep))
                outfile.write(os.linesep)

                # independant variables
                if "independent_variables" in self.pj[OBSERVATIONS][obsId]:
                    outfile.write('Independent variables{0}'.format(os.linesep))
                    outfile.write('variable\tvalue{0}'.format(os.linesep))
                    for variable in self.pj[OBSERVATIONS][obsId]["independent_variables"]:
                        outfile.write('{0}\t{1}{2}'.format(variable, self.pj[OBSERVATIONS][obsId]["independent_variables"][variable], os.linesep))

                outfile.write(os.linesep)
                outfile.write(os.linesep)

                eventsWithStatus =  self.update_events_start_stop2( self.pj[OBSERVATIONS][obsId][EVENTS] ) 

                max_modifiers = 0
                for event in eventsWithStatus:
                    for c in pj_events_fields:
                        if c == 'modifier' and event[pj_obs_fields[c]]:
                            max_modifiers = max( max_modifiers, len(event[pj_obs_fields[c]].split('|')) )

                # write header
                outfile.write('Events{0}'.format(os.linesep))
                out = '{0}\t{1}{2}'.format( '\t'.join(  pj_events_fields), 'status', os.linesep ) 
                if max_modifiers > 1:
                    out = out.replace('modifier', '\t'.join([ 'Modifier %d' % x for x in range(1, max_modifiers + 1) ]))
                outfile.write(out)

                out = ''
                for event in eventsWithStatus:

                    if (event[ pj_obs_fields['subject'] ] in selected_subjects) \
                       or (event[ pj_obs_fields['subject'] ] == '' and 'No focal subject' in selected_subjects):

                        row = []
                        for c in pj_events_fields:
                            if c == 'modifier' :
                                modifiers = event[pj_obs_fields[c]].split('|')
                                while len(modifiers)<max_modifiers:
                                    modifiers.append('')
                                s = '\t'.join( modifiers )
                            elif c == 'comment':
                                s = unicode( event[pj_obs_fields[c]].replace('\r\n',' ').replace('\n',' ').replace('\r',' ' ))
                            else:
                                s = unicode( event[pj_obs_fields[c]])
                            row.append( s )

                        # append status START/STOP
                        row.append( event[-1] )

                        outfile.write( '\t'.join(row).encode('UTF-8') + os.linesep)


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
        fileName, _ = fd.getSaveFileName(self,'Export events as strings', '','Events file (*.txt *.tsv);;All files (*)')

        if fileName:
            f = open(fileName, 'w')

            for obsId in selected_observations:

                # observation id
                f.write('# observation id: {0}{1}'.format(obsId.encode('UTF-8'), os.linesep) )

                # observation descrition
                f.write('# observation description: {0}{1}'.format(self.pj[OBSERVATIONS][obsId]['description'].encode('UTF-8').replace(os.linesep,' ' ), os.linesep) )

                # media file name
                if self.pj[OBSERVATIONS][obsId]['type'] in [MEDIA]:

                    f.write('# Media file name: {0}{1}{1}'.format(', '.join(   [ os.path.basename(x) for x in self.pj[OBSERVATIONS][obsId]['file']['1']  ]  ), os.linesep ) )

                if self.pj[OBSERVATIONS][obsId]['type'] in [LIVE]:
                    f.write('# Live observation{0}{0}'.format(os.linesep))

            for subj in selected_subjects:
                

                if subj:
                    subj_str = '{0}{1}:{0}'.format(os.linesep, subj.encode('UTF-8')) 

                else:
                    subj_str = '{0}No focal subject:{0}'.format(os.linesep) 

                f.write(subj_str)

                for obs in selected_observations:
                    s = ''
                    
                    for event in self.pj[OBSERVATIONS][obs][EVENTS]:
                        if event[ pj_obs_fields['subject'] ] == subj or (subj == 'No focal subject' and event[ pj_obs_fields['subject'] ] == ''):
                            s += event[ pj_obs_fields['code'] ] + self.behaviouralStringsSeparator
    
                    # remove last separator (if separator not empty)
                    if self.behaviouralStringsSeparator:
                        s = s[0 : -len(self.behaviouralStringsSeparator)]
    
                    if s:

                        f.write( s.encode('UTF-8') + os.linesep)

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

        self.statusbar.showMessage('Function not yet implemented for OpenCV player', 5000)        



    def play_video(self):
        '''
        play video
        '''

        if self.playerType == VLC:

            if self.playMode == FFMPEG:

                self.FFmpegTimer.start() 

            else:

                logging.debug('self.media_list.count(): {0}'.format( self.media_list.count()))
    
                if self.media_list.count():

                    self.mediaListPlayer.play()
                    logging.debug('player #1 state: {0}'.format(self.mediaListPlayer.get_state()))
    
                    if self.media_list2.count():   # second video together

                        self.mediaListPlayer2.play()
                        logging.debug('player #2 state'.format(  self.mediaListPlayer2.get_state()))
                else:

                    self.no_media()




    def pause_video(self):
        '''
        pause media
        '''

        if self.playerType == VLC:
            
            if self.playMode == FFMPEG:

                if self.FFmpegTimer.isActive():
                    self.FFmpegTimer.stop() 
                else:
                    self.FFmpegTimer.start() 
            else:

                if self.media_list.count():
                    self.mediaListPlayer.pause()  # play if paused
    
                    logging.debug('player #1 state: {0}'.format(self.mediaListPlayer.get_state()))
                    
                    if self.media_list2.count():
                        self.mediaListPlayer2.pause()
                        logging.debug('player #2 state'.format(  self.mediaListPlayer2.get_state()))
                else:
                    self.no_media()



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
                currentTime = self.FFmpegGlobalFrame / self.fps.values()[0] 
    
                logging.debug('currentTime %f' % currentTime)
                logging.debug('new time %f' % (currentTime - self.fast)) 
                logging.debug('new frame %d ' % int((currentTime - self.fast )  * self.fps.values()[0]))
   
    
                if int((currentTime - self.fast ) * self.fps.values()[0]) > 0:
                    self.FFmpegGlobalFrame = int((currentTime - self.fast ) * self.fps.values()[0])
    
                else:
                    self.FFmpegGlobalFrame = 0   #### position to init
                self.FFmpegTimerOut()

            else:

                if self.media_list.count() == 1:
                    if self.mediaplayer.get_time() >= self.fast * 1000:
                        self.mediaplayer.set_time( self.mediaplayer.get_time() - self.fast * 1000 )
                    else:
                        self.mediaplayer.set_time(0)
                    if self.media_list2.count():
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
                            while self.mediaListPlayer.get_state() != vlc.State.Playing:
                                pass
                                
                            if flagPaused:
                                logging.debug(self.mediaListPlayer.get_state())
                                self.mediaListPlayer.pause()
                            
                            self.mediaplayer.set_time( newTime -  sum(self.duration[0 : self.media_list.index_of_item(self.mediaplayer.get_media()) ]))
                            
                            break
                        tot += d
    
                else:
                    self.no_media()

                # no subtitles
                self.mediaplayer.video_set_spu(0)




    def jumpForward_activated(self):
        '''
        forward from current position 
        '''

        if self.playerType == VLC:

            if self.playMode == FFMPEG:

                currentTime = self.FFmpegGlobalFrame / self.fps.values()[0] 
    
                logging.debug('currentTime %f' % currentTime)
                logging.debug('new time %f' % (currentTime + self.fast)) 
                logging.debug('new frame %d ' % int((currentTime + self.fast )  * self.fps.values()[0]))
    
                self.FFmpegGlobalFrame =  int((currentTime + self.fast )  * self.fps.values()[0])

                self.FFmpegTimerOut()

            else:


                if self.media_list.count() == 1:
                    if self.mediaplayer.get_time() >= self.mediaplayer.get_length() - self.fast * 1000:
        
                        self.mediaplayer.set_time(self.mediaplayer.get_length())
        
                    else:
                        self.mediaplayer.set_time( self.mediaplayer.get_time() + self.fast * 1000 )
        
        
                    if self.media_list2.count():
                        if self.mediaplayer2.get_time() >= self.mediaplayer2.get_length() - self.fast * 1000:
            
                            self.mediaplayer2.set_time(self.mediaplayer2.get_length())
            
                        else:
                            self.mediaplayer2.set_time( self.mediaplayer2.get_time() + self.fast * 1000 )
    
                elif self.media_list.count() > 1:
                    
                    newTime = (sum(self.duration[0 : self.media_list.index_of_item(self.mediaplayer.get_media()) ]) + self.mediaplayer.get_time()) + self.fast * 1000
    
                    if newTime < sum(self.duration):
    
                        ### remember if player paused (go previous will start playing)
                        flagPaused = self.mediaListPlayer.get_state() == vlc.State.Paused
                        
                        if self.DEBUG: print('flagPaused', flagPaused)
    
                        tot = 0
                        for idx, d in enumerate(self.duration):
                            if newTime >= tot and newTime < tot+d:
                                self.mediaListPlayer.play_item_at_index(idx)
                                
                                ### wait until media is played    
                                while self.mediaListPlayer.get_state() != vlc.State.Playing:
                                    pass
                                    
                                if flagPaused:
                                    if self.DEBUG: print(self.mediaListPlayer.get_state())
                                    self.mediaListPlayer.pause()
                                
                                #time.sleep(0.5)
                                print(newTime -  sum(self.duration[0 : self.media_list.index_of_item(self.mediaplayer.get_media()) ]))
                                self.mediaplayer.set_time( newTime -  sum(self.duration[0 : self.media_list.index_of_item(self.mediaplayer.get_media()) ]))
                                
                                break
                            tot += d
    
                else:
                    self.no_media()

                # no subtitles
                self.mediaplayer.video_set_spu(0)




    def reset_activated(self):
        '''
        reset video to beginning
        '''
        logging.debug('Reset activated')

        self.mediaplayer.pause()
        self.mediaplayer.set_time(0)

        if self.media_list2.count():
            self.mediaplayer2.pause()
            self.mediaplayer2.set_time(0)


    def stopClicked(self):
        
        logging.debug('Stop activated')
        
        self.mediaplayer.stop()

        if self.media_list2.count():
            self.mediaplayer2.stop()



if __name__=="__main__":
    
    ### check if argument
    from optparse import OptionParser
    usage = "usage: %prog [options]"
    parser = OptionParser(usage=usage)
    
    parser.add_option("-d", "--debug", action = "store_true", default = False, dest = "debug", help = "Verbose mode for debugging")
    parser.add_option("-v", "--version", action = "store_true", default = False, dest = "version", help = "Print version")
   
    (options, args) = parser.parse_args()

    if options.version:
        print(__version__)
        sys.exit(0)


    app = QApplication(sys.argv)

    start = time.time() 
    splash = QSplashScreen(QPixmap( os.path.dirname(os.path.realpath(__file__)) + "/splash.png"))
    splash.show()
    splash.raise_()
    while time.time() - start < 1:
        time.sleep(0.001)
        app.processEvents()



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

    logging.info('VLC version %s' % vlc.libvlc_get_version()[0])
    if vlc.libvlc_get_version() < VLC_MIN_VERSION:
        QMessageBox.critical(None, programName, 'The VLC media player seems very old (%s).<br>Go to http://www.videolan.org/vlc to update it' \
            % vlc.libvlc_get_version(), QMessageBox.Ok | QMessageBox.Default, QMessageBox.NoButton)
        logging.critical('The VLC media player seems a little bit old (%s). Go to http://www.videolan.org/vlc to update it' % vlc.libvlc_get_version())
        sys.exit(2)


    # check for ffmpeg

    allowFrameByFrame = False
    ffmpeg_bin = ''
    if os.path.isfile( os.path.expanduser('~') + os.sep + '.boris' ):
        settings = QSettings(os.path.expanduser('~') + os.sep + '.boris' , QSettings.IniFormat)
        try:
            allowFrameByFrame = ( settings.value('allow_frame_by_frame') == 'true' )
        except:
            allowFrameByFrame = False

        if allowFrameByFrame:
            try:
                ffmpeg_bin = settings.value('ffmpeg_bin')
                if not ffmpeg_bin:
                    ffmpeg_bin = ''
            except:
                ffmpeg_bin = ''
            
    logging.debug('ffmpeg_bin: %s' % ffmpeg_bin)



    if allowFrameByFrame:
        '''
        if not ffmpeg_bin:
            if sys.platform in ('linux2','darwin'):
                ffmpeg_bin = 'ffmpeg'
            if sys.platform in ('win32'):
                ffmpeg_bin = 'ffmpeg.exe'
        '''

        import subprocess
        try:
            if subprocess.Popen(ffmpeg_bin + ' -version' ,stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True ).communicate()[0] :
                availablePlayers.append(FFMPEG)
        except:
            logging.warning('ffmpeg not found')

    app.setApplicationName(programName)
    window = MainWindow(availablePlayers)

    window.DEBUG = options.debug

    if not window.DEBUG:
        if 'RC' in __version_date__:
            QMessageBox.warning(None, programName, 'This version is a release candidate and must be used only for testing.\nPlease report all bugs', \
                QMessageBox.Ok | QMessageBox.Default, QMessageBox.NoButton)

    if args:
        logging.debug('args[0]: ' + os.path.abspath(args[0]))
        window.open_project_json( os.path.abspath(args[0]) )

    window.show()
    window.raise_()
    splash.finish(window)

    sys.exit(app.exec_())
