#!/usr/bin/env python

from __future__ import division

"""
BORIS
Behavioral Observation Research Interactive Software
Copyright 2012-2014 Olivier Friard


  This program is free software; you can redistribute it and/or modify
  it under the terms of the GNU General Public License as published by
  the Free Software Foundation; either version 2 of the License, or
  (at your option) any later version.
  
  This program is distributed in the hope that it will be useful,
  but WITHOUT ANY WARRANTY; without even the implied warranty of
  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
  GNU General Public License for more details.
  
  You should have received a copy of the GNU General Public License
  along with this program; if not, write to the Free Software
  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
  MA 02110-1301, USA.

"""

'''
TODO: check if observation has many media and OpenCV player selected

frame by frame problem with OpenCV:
http://stackoverflow.com/questions/11260042/reverse-video-playback-in-opencv

show on VLC:
http://mih.voxindeserto.de/vlc_movieoverlays.html

'''


__version__ = '1.3'
__version_date__ = 'development version-'

function_keys = {16777264: 'F1',16777265: 'F2',16777266: 'F3',16777267: 'F4',16777268: 'F5', 16777269: 'F6', 16777270: 'F7', 16777271: 'F8', 16777272: 'F9', 16777273: 'F10',16777274: 'F11', 16777275: 'F12'}

slider_maximum = 1000

import qrc_boris

from config import *

status_template = '%s %s'
audio_video_tab_index = 0
live_tab_index = 1

video, live = 0, 1

import sys
import time
import os
from encodings import hex_codec
import json

from PySide.QtCore import *
from PySide.QtGui import *

import dialog

from boris_ui import *

from edit_event import *

from project import *
import preferences
import observation
#import observations_list

import obs_list2

import svg

import PySide.QtNetwork
import PySide.QtWebKit


def bytes_to_str(b):
    '''
    Translate bytes to string.
    '''
    if isinstance(b, bytes):
        
        fileSystemEncoding = sys.getfilesystemencoding()

        ### hack for PyInstaller
        if fileSystemEncoding == None:
            fileSystemEncoding = 'UTF-8'

        return b.decode( fileSystemEncoding )
    else:
        return b


from time_budget_widget import *

from diagram_widget import *

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

        self.pbOK = QPushButton('OK')
        self.pbOK.clicked.connect(self.pbOK_clicked)
        self.pbCancel = QPushButton('Cancel')
        self.pbCancel.clicked.connect(self.pbCancel_clicked)

        hbox2 = QHBoxLayout(self)

        hbox2.addWidget(self.pbCancel)
        hbox2.addWidget(self.pbOK)

        hbox.addLayout(hbox2)

        self.setLayout(hbox)

        self.setWindowTitle('')

    def pbOK_clicked(self):
        self.accept()
        
    def pbCancel_clicked(self):
        self.reject()


class JumpTo(QDialog):

    def __init__(self):
        super(JumpTo, self).__init__()

        hbox = QVBoxLayout(self)

        self.label = QLabel()
        self.label.setText('Go to time')
        hbox.addWidget(self.label)

        self.te = QTimeEdit()
        self.te.setDisplayFormat('hh:mm:ss.zzz')
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

        self.setWindowTitle('Go to time')

    def pbOK_clicked(self):
        self.accept()
        
    def pbCancel_clicked(self):
        self.reject()



class MainWindow(QMainWindow, Ui_MainWindow):

    DEBUG = False

    pj = {"time_format": HHMMSS, "project_date": "", "project_name": "", "project_description": "", "subjects_conf" : {}, "behaviors_conf": {}, "observations": {}  }
    project = False

    observationId = ''   ### current observation id

    timeOffset = 0.0
    saveMediaFilePath = True
    confirmSound = False          ### if True a beep will confirm each keypress
    embedPlayer = True            ### if True the VLC player will be embedded in the main window
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
    
    currentSubject = ''  ### contains the current subject of observation
    

    detailedObs = {}

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
        self.actionPrevious.setIcon(QIcon(':/previous.png'))
        self.actionNext.setIcon(QIcon(':/next.png'))

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
        self.toolBox.removeItem(0)
        self.toolBox.setVisible(False)

        ### start with dock widget invisible 
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

        '''
        self.hsVideo = QSlider(QtCore.Qt.Horizontal, self)
        self.hsVideo.setMaximum(slider_maximum)
        self.hsVideo.setVisible(False)
        '''


        '''
        if self.playerType == OPENCV:
            
            self.hsVideo = QSlider(Qt.Horizontal, self)
            self.hsVideo.setMaximum(slider_maximum)
    
            self.video1layout = QHBoxLayout()

            self.lbOpenCV = QLabel(self)
            self.lbOpenCV.setBackgroundRole(QPalette.Base)

            self.video1layout.addWidget(self.lbOpenCV)
    
            self.vboxlayout = QtGui.QVBoxLayout()
            self.vboxlayout.addLayout(self.video1layout)
            self.vboxlayout.addWidget(self.hsVideo)
    
            self.videoTab = QtGui.QWidget()
            
            self.videoTab.setLayout(self.vboxlayout)
    
            self.toolBox.insertItem(0, self.videoTab, 'Audio/Video')
        '''
        '''
        if self.playerType == VLC:
            ### creating a basic vlc instance
    
            self.instance = vlc.Instance()
    
            ### creating an empty vlc media player
            self.mediaplayer = self.instance.media_player_new()
    
            self.mediaListPlayer = self.instance.media_list_player_new()
            self.mediaListPlayer.set_media_player(self.mediaplayer)
    
            self.media_list = self.instance.media_list_new()
    
            self.media_list2 = self.instance.media_list_new()
    
            # In this widget, the video will be drawn
            self.videoframe = QtGui.QFrame()
            self.palette = self.videoframe.palette()
            self.palette.setColor (QtGui.QPalette.Window, QtGui.QColor(0,0,0))
            self.videoframe.setPalette(self.palette)
            self.videoframe.setAutoFillBackground(True)
    
            self.volumeslider = QtGui.QSlider(QtCore.Qt.Vertical, self)
            self.volumeslider.setMaximum(100)
            self.volumeslider.setValue(self.mediaplayer.audio_get_volume())
            self.volumeslider.setToolTip("Volume")
            self.volumeslider.sliderMoved.connect(self.setVolume)

            self.hsVideo = QSlider(QtCore.Qt.Horizontal, self)
            self.hsVideo.setMaximum(slider_maximum)

            self.video1layout = QtGui.QHBoxLayout()
            self.video1layout.addWidget(self.videoframe)
            self.video1layout.addWidget(self.volumeslider)
    
            self.vboxlayout = QtGui.QVBoxLayout()
    
            self.vboxlayout.addLayout(self.video1layout)
    
            self.vboxlayout.addWidget(self.hsVideo)
    
            self.videoTab = QtGui.QWidget()
            
            self.videoTab.setLayout(self.vboxlayout)
    
            self.toolBox.insertItem(0, self.videoTab, 'Audio/Video')
        '''


        ### live tab
        self.liveLayout = QtGui.QGridLayout()
        self.textButton = QPushButton('Start live observation')
        self.textButton.clicked.connect(self.start_live_observation)
        self.liveLayout.addWidget(self.textButton)

        self.lbTimeLive = QLabel()
        self.lbTimeLive.setAlignment(Qt.AlignCenter)
        font = QFont('Monospace')
        font.setPointSize(48)
        self.lbTimeLive.setFont(font)
        self.lbTimeLive.setText("00:00")
        self.liveLayout.addWidget(self.lbTimeLive)

        self.liveTab = QtGui.QWidget()
        self.liveTab.setLayout(self.liveLayout)

        self.toolBox.insertItem(2, self.liveTab, 'Live')

        '''
        self.videoTab.setEnabled(False)

        self.liveTab.setEnabled(False)

        self.toolBox.setItemEnabled (video, False)
        self.toolBox.setItemEnabled (audio, False)
        self.toolBox.setItemEnabled (live, False)

        ###default tab
        self.toolBox.setCurrentIndex(video)
        '''


        ### add label to status bar
        #self.statusbar.setMinimumHeight(40)
        
        self.lbTime = QLabel()
        self.lbTime.setFrameStyle(QFrame.StyledPanel)
        self.lbTime.setMinimumWidth(160)
        #self.lbTime.setText('Position: <font size=5><b>0:00:00.0</b></font>')
        
        
        ### current subjects
        self.lbSubject = QLabel()
        self.lbSubject.setFrameStyle(QFrame.StyledPanel)
        self.lbSubject.setMinimumWidth(160)
        #self.lbSubject.setMinimumHeight(40)


        ### current states
        self.lbState = QLabel()
        self.lbState.setFrameStyle(QFrame.StyledPanel)
        
        self.lbState.setMinimumWidth(220)


        ### time offset
        self.lbTimeOffset = QLabel()
        self.lbTimeOffset.setFrameStyle(QFrame.StyledPanel)
        self.lbTimeOffset.setMinimumWidth(160)

        ### speed
        self.lbSpeed = QLabel()
        self.lbSpeed.setFrameStyle(QFrame.StyledPanel)
        self.lbSpeed.setMinimumWidth(40)
        #self.lbSpeed.setText('x1')

        self.statusbar.addPermanentWidget(self.lbTime)
        self.statusbar.addPermanentWidget(self.lbSubject)

        self.statusbar.addPermanentWidget(self.lbState)
        self.statusbar.addPermanentWidget(self.lbTimeOffset)
        self.statusbar.addPermanentWidget(self.lbSpeed)


        ##self.verticalHeader = QHeaderView(Qt.Vertical)
        ##self.verticalHeader.sectionDoubleClicked.connect(self.twEvents_doubleClicked)
        
        ##self.twEvents.setVerticalHeader(self.verticalHeader)

        #self.horizontalHeader = QHeaderView(Qt.Horizontal)
        #self.twEvents.setHorizontalHeader(self.horizontalHeader)

        self.twEvents.setColumnCount( len(tw_events_fields) )
        self.twEvents.setHorizontalHeaderLabels(tw_events_fields)

        self.menu_options()

        self.connections()

    def mediaObject_finished(self):

        self.mediaplayer.pause()
        self.mediaplayer.set_position(0)

        if self.DEBUG: print 'Ended'




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

        ### project menu
        self.actionEdit_project.setEnabled(flag)
        self.actionSave_project.setEnabled(flag)
        self.actionSave_project_as.setEnabled(flag)
        self.actionClose_project.setEnabled(flag)
        self.actionMedia_file_information.setEnabled(flag)

        ### observations

        ### enabled if project
        self.actionNew_observation.setEnabled(flag)

        self.actionObservationsList.setEnabled( self.pj['observations'] != {})
        self.actionOpen_observation_2.setEnabled( self.pj['observations'] != {})
        self.actionEdit_observation.setEnabled( self.pj['observations'] != {})


        ### enabled if observation
        flagObs = self.observationId != ''
        
        self.actionAdd_event.setEnabled(flagObs)
        self.actionClose_observation.setEnabled(flagObs)
        self.actionLoad_observations_file.setEnabled(flagObs)
        
        self.menuExport_events.setEnabled(flag)
        self.actionExportEventTabular.setEnabled(flagObs)

        self.actionDelete_all_observations.setEnabled(flagObs)
        self.actionSort_observations.setEnabled(flagObs)
        self.actionSelect_observations.setEnabled(flagObs)
        self.actionDelete_selected_observations.setEnabled(flagObs)
        self.actionEdit_event.setEnabled(flagObs)
        self.actionMedia_file_information.setEnabled(flagObs)
        
        
        self.actionJumpForward.setEnabled( flagObs)
        self.actionJumpBackward.setEnabled( flagObs)
        self.actionJumpTo.setEnabled( flagObs)
        self.actionPlay.setEnabled( flagObs)
        self.actionPause.setEnabled( flagObs)
        self.actionReset.setEnabled( flagObs)
        self.actionFaster.setEnabled( flagObs)        
        self.actionSlower.setEnabled( flagObs)
        self.actionPrevious.setEnabled( flagObs)
        self.actionNext.setEnabled( flagObs)


        self.actionTime_budget.setEnabled( self.pj['observations'] != {} )
        self.actionVisualize_data.setEnabled( self.pj['observations'] != {} )


    def connections(self):

        #self.focusOutEvent[QFocusEvent].connect (self.focusOutEvent)

        ### menu file
        self.actionNew_project.triggered.connect(self.new_project_activated)
        self.actionOpen_project.triggered.connect(self.open_project_activated)
        self.actionEdit_project.triggered.connect(self.edit_project_activated)
        self.actionSave_project.triggered.connect(self.save_project_activated)
        self.actionSave_project_as.triggered.connect(self.save_project_as_activated)
        self.actionClose_project.triggered.connect(self.close_project)

        self.actionMedia_file_information.triggered.connect(self.media_file_info)

        self.actionPreferences.triggered.connect(self.preferences)

        self.actionQuit.triggered.connect(self.actionQuit_activated)

        ### menu observations
        self.actionNew_observation.triggered.connect(self.new_observation)

        self.actionObservationsList.triggered.connect(self.observations_list)
        
        self.actionOpen_observation_2.triggered.connect(self.open_observation)
        self.actionEdit_observation.triggered.connect(self.edit_observation)
        self.actionClose_observation.triggered.connect(self.close_observation)
                

        self.actionAdd_event.triggered.connect(self.add_event)
        self.actionEdit_event.triggered.connect(self.edit_event)

        #self.actionSort_observations.triggered.connect(self.sort_events)

        self.actionSelect_observations.triggered.connect(self.select_events_between_activated)

        self.actionDelete_all_observations.triggered.connect(self.delete_all_events)
        self.actionDelete_selected_observations.triggered.connect(self.delete_selected_events)


        self.actionLoad_observations_file.triggered.connect(self.import_observations)
        self.actionExportEventTabular.triggered.connect(self.export_tabular_events)
        self.actionExportEventString.triggered.connect(self.export_string_events)

        ### playback
        self.actionJumpTo.triggered.connect(self.jump_to)

        ### menu Analyze
        self.actionTime_budget.triggered.connect(self.time_budget)
        self.actionVisualize_data.triggered.connect(self.visualize_data)


        self.actionAbout.triggered.connect(self.actionAbout_activated)
        self.actionCheckUpdate.triggered.connect(self.actionCheckUpdate_activated)
        

        ### toolbar
        self.actionPlay.triggered.connect(self.play_activated)
        self.actionPause.triggered.connect(self.pause_video)
        self.actionReset.triggered.connect(self.reset_activated)
        self.actionJumpBackward.triggered.connect(self.jumpBackward_activated)
        self.actionJumpForward.triggered.connect(self.jumpForward_activated)

        self.actionFaster.triggered.connect(self.video_faster_activated)
        self.actionSlower.triggered.connect(self.video_slower_activated)

        self.actionPrevious.triggered.connect(self.previous_media_file)
        self.actionNext.triggered.connect(self.next_media_file)



        ### table Widget double click
        self.twEvents.itemDoubleClicked.connect(self.twEvents_doubleClicked)
        self.twConfiguration.itemDoubleClicked.connect(self.twConfiguration_doubleClicked)
        self.twSubjects.itemDoubleClicked.connect(self.twSubjects_doubleClicked)


        ### player
        '''self.hsVideo.sliderMoved.connect(self.hsVideo_sliderMoved)'''


        ### Actions for twEvents context menu
        self.twEvents.setContextMenuPolicy(Qt.ActionsContextMenu)

        self.twEvents.addAction(self.actionEdit_event)
        self.twEvents.addAction(self.actionDelete_selected_observations)
        self.twEvents.addAction(self.actionDelete_all_observations)


        ### Actions for twSubjects context menu
        self.actionDeselectCurrentSubject.triggered.connect(self.deselectSubject)
        
        self.twSubjects.setContextMenuPolicy(Qt.ActionsContextMenu)
        self.twSubjects.addAction(self.actionDeselectCurrentSubject)

        ### subjects
        

        ### timer for playing
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.timer_out)
        

        ### timer for timing the live observation
        self.liveTimer = QTimer(self)
        self.liveTimer.timeout.connect(self.liveTimer_out)

        self.readConfigFile()

        ### timer for automatic backup
        self.automaticBackupTimer = QTimer(self)
        self.automaticBackupTimer.timeout.connect(self.automatic_backup)
        if self.automaticBackup:
            self.automaticBackupTimer.start( self.automaticBackup * 60000 )


    def observations_list(self):
        '''
        view all observations
        '''
        ### check if an observation is running
        if self.observationId:
            QMessageBox.critical(self, programName , 'You must close the running observation before.' )
            return

        result, selectedObs = self.selectObservations( LIST )
        
        if selectedObs:

            if result == OPEN:
                
                self.observationId = selectedObs[0]
    
                ### load events in table widget
                self.loadEventsInTW(self.observationId)
    
                ### set player type
                '''
                FIXME
                
                
                if 'playertype' in self.pj['observations'][self.observationId]:
                    self.playerType = self.pj['observations'][self.observationId][ 'playertype' ]
                else:   ### set first player available (VLC by default)
                    self.playerType = self.availablePlayers[0]
                '''
                self.playerType = VLC
                
                
                if self.playerType == VLC:
                    if self.initialize_new_observation_vlc():
       
                        self.menu_options()
        
                        ### title of dock widget
                        self.dwObservations.setWindowTitle('Events for ' + self.observationId) 
        
                        #self.sort_events()
        
                    else:
        
                        self.observationId = ''
                        self.twEvents.setRowCount(0)
                        self.menu_options()
    
                if self.playerType == OPENCV:
                    print 'opencv'
                    self.initialize_new_observation_opencv()
                    self.menu_options()
                    ### title of dock widget
                    self.dwObservations.setWindowTitle('Events for ' + self.observationId) 

        
            if result == EDIT:
                if self.observationId != selectedObs[0]:
        
                    self.new_observation( EDIT, selectedObs[0])   ### observation id to edit
                else:
                    QMessageBox.warning(self, programName , 'The observation <b>%s</b> is running!<br>Close it before editing.' % self.observationId)
                

    def actionCheckUpdate_activated(self):
        
        '''
        check BORIS web site for updates
        '''
        try:
            import urllib2
            lastVersion = float(urllib2.urlopen('http://penelope.unito.it/boris/ver.dat' ).read().strip())
            if lastVersion > float(__version__):
                QMessageBox.information(self, programName , 'The new version (v. <b>%s</b>) is available!<br>Go to <a href="http://penelope.unito.it/boris">http://penelope.unito.it/boris</a>.' % str(lastVersion))
            else:
                QMessageBox.information(self, programName , 'The version you are using is the last one')
        except:
            QMessageBox.warning(self, programName , 'Can not check for updates...')



    def jump_to(self):
        '''
        jump to the user specified media position
        '''
        jt = JumpTo()
        if jt.exec_():

            if self.DEBUG: print '\njump to time:', jt.te.time().toString('hh:mm:ss')
            
            ### newTime = int( self.time2seconds( jt.te.time().toString('hh:mm:ss') ) * 1000)
            
            
            newTime = int(self.time2seconds(jt.te.time().toString('hh:mm:ss.zzz')) * 1000)
            
            if self.DEBUG: print '\new time:', newTime

            if self.DEBUG: print 'media list count', self.media_list.count()

            if self.media_list.count() == 1:

                if newTime < self.mediaplayer.get_length():
                    self.mediaplayer.set_time( newTime )
                else:
                    QMessageBox.warning(self, programName , 'The indicated position is behind the end of media (%s)' % self.seconds2time(self.mediaplayer.get_length()/1000))

            elif self.media_list.count() > 1:

                if self.DEBUG: print newTime
                if self.DEBUG: print sum(self.duration)
                
                if newTime < sum(self.duration):

                    ### remember if player paused (go previous will start playing)
                    flagPaused = self.mediaListPlayer.get_state() == vlc.State.Paused
                    
                    if self.DEBUG: print 'flagPaused', flagPaused

                    tot = 0
                    for idx, d in enumerate(self.duration):
                        if newTime >= tot and newTime < tot+d:
                            self.mediaListPlayer.play_item_at_index(idx)
                            
                            ### wait until media is played    
                            while self.mediaListPlayer.get_state() != vlc.State.Playing:
                                pass
                                
                            if flagPaused:
                                if self.DEBUG: print self.mediaListPlayer.get_state()
                                self.mediaListPlayer.pause()
                            
                            #time.sleep(0.5)
                            print newTime -  sum(self.duration[0 : self.media_list.index_of_item(self.mediaplayer.get_media()) ])
                            self.mediaplayer.set_time( newTime -  sum(self.duration[0 : self.media_list.index_of_item(self.mediaplayer.get_media()) ]))
                            
                            break
                        tot += d
                    #sum(self.duration[0 : self.media_list.index_of_item(self.mediaplayer.get_media()) ]) + self.mediaplayer.get_time()
                else:
                    QMessageBox.warning(self, programName , 'The indicated position is behind the total media duration (%s)' % self.seconds2time(sum(self.duration)/1000))


    def previous_media_file(self):
        '''
        go to previous media file (if any)
        '''
        if self.playerType == VLC:
            ### check if media not first media
            if self.media_list.index_of_item(self.mediaplayer.get_media()) > 0:

                ### remember if player paused (go previous will start playing)
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

        if self.playerType == OPENCV:
            self.statusbar.showMessage('Function not yet implemented for OpenCV player', 5000)



    def next_media_file(self):
        '''
        go to previous media file (if any)
        '''
        if self.playerType == VLC:
            ### check if media not first media
            if self.media_list.index_of_item(self.mediaplayer.get_media()) <  self.media_list.count() - 1:
            
                ### remember if player paused (go previous will start playing)
                flagPaused = self.mediaListPlayer.get_state() == vlc.State.Paused
                
                if self.DEBUG: print 'flagPaused', flagPaused
                
                self.mediaListPlayer.next()

                ### wait until media is played    
                while self.mediaListPlayer.get_state() != vlc.State.Playing:
                    pass
                    
                if flagPaused:
                    if self.DEBUG: print self.mediaListPlayer.get_state()
                    self.mediaListPlayer.pause()
            
            else:
                if self.media_list.count() == 1:
                    self.statusbar.showMessage('There is only one media file', 5000)
                else:
                    if self.media_list.index_of_item(self.mediaplayer.get_media()) == self.media_list.count() - 1:
                        self.statusbar.showMessage('The last media is playing', 5000)

        if self.playerType == OPENCV:
            self.statusbar.showMessage('Function not yet implemented for OpenCV player', 5000)



    def setVolume(self):
        if self.DEBUG: print 'Volume player #1:', self.volumeslider.value()
        self.mediaplayer.audio_set_volume( self.volumeslider.value() )

    def setVolume2(self):
        if self.DEBUG: print 'Volume player #2:', self.volumeslider2.value()
        self.mediaplayer2.audio_set_volume(self.volumeslider2.value() )


    def automatic_backup(self):
        '''
        save project every x minutes if current observation
        '''

        if self.observationId:
            if self.DEBUG: print 'automatic backup'
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
        
        if self.DEBUG: print self.saveMediaFilePath, type(self.saveMediaFilePath)
        preferencesWindow.cbSaveMediaFilePath.setChecked( self.saveMediaFilePath )

        ### automatic backup
        preferencesWindow.sbAutomaticBackup.setValue( self.automaticBackup )

        ### separator for behavioural strings
        preferencesWindow.leSeparator.setText( self.behaviouralStringsSeparator )

        ### confirm sound
        preferencesWindow.cbConfirmSound.setChecked( self.confirmSound )

        ### embed player
        preferencesWindow.cbEmbedPlayer.setChecked( self.embedPlayer )



        if preferencesWindow.exec_():

            if preferencesWindow.cbTimeFormat.currentIndex() == 0:
                self.timeFormat = S

            if preferencesWindow.cbTimeFormat.currentIndex() == 1:
                self.timeFormat = HHMMSS

            self.fast = preferencesWindow.sbffSpeed.value()

            self.repositioningTimeOffset = preferencesWindow.sbRepositionTimeOffset.value()

            self.saveMediaFilePath = preferencesWindow.cbSaveMediaFilePath.isChecked()

            self.automaticBackup = preferencesWindow.sbAutomaticBackup.value()
            if self.automaticBackup:
                self.automaticBackupTimer.start( self.automaticBackup * 60000 )
            else:
                self.automaticBackupTimer.stop()

            self.behaviouralStringsSeparator = preferencesWindow.leSeparator.text()

            self.confirmSound = preferencesWindow.cbConfirmSound.isChecked()

            self.embedPlayer = preferencesWindow.cbEmbedPlayer.isChecked()


            if self.observationId:
                self.loadEventsInTW( self.observationId )
                self.display_timeoffset_statubar()

            self.saveConfigFile()
        

    def initialize_new_observation_opencv(self):
        '''
        initialize new observation for OpenCV
        '''
        if self.DEBUG: print 'initialize new observation for OpenCV'


        #self.hsVideo = QSlider(Qt.Horizontal, self)
        #self.hsVideo.setMaximum(slider_maximum)

        self.video1layout = QHBoxLayout()

        self.lbOpenCV = QLabel(self)
        self.lbOpenCV.setBackgroundRole(QPalette.Base)

        
        self.video1layout.addWidget(self.lbOpenCV)


        self.vboxlayout = QtGui.QVBoxLayout()
        self.vboxlayout.addLayout(self.video1layout)
        self.vboxlayout.addWidget(self.hsVideo)
        self.hsVideo.setVisible(True)

        self.videoTab = QtGui.QWidget()
        
        self.videoTab.setLayout(self.vboxlayout)

        self.toolBox.insertItem(0, self.videoTab, 'Audio/Video')
        
        self.toolBar.setEnabled(True)
        self.dwObservations.setVisible(True)
        self.toolBox.setVisible(True)
        self.lbFocalSubject.setVisible(True)
        self.lbCurrentStates.setVisible(True)
        
        self.lbOpenCV.setVisible(True)

        ### check file for mediaplayer #1
        if '1' in self.pj['observations'][self.observationId]['file'] and self.pj['observations'][self.observationId]['file']['1']:

            for mediaFile in self.pj['observations'][self.observationId]['file']['1']:

                if self.DEBUG: print 'media file', mediaFile, 'is file', os.path.isfile( mediaFile )

                if os.path.isfile( mediaFile ):

                    if self.DEBUG: print 'open media file with open cv'
                    self.cap = cv2.VideoCapture(mediaFile)
                    
                    if self.DEBUG:
                        print "Video Properties:"
                        print "\t Width: ",self.cap.get(cv2.cv.CV_CAP_PROP_FRAME_WIDTH)
                        print "\t Height: ",self.cap.get(cv2.cv.CV_CAP_PROP_FRAME_HEIGHT)
                        print "\t FourCC: ",self.cap.get(cv2.cv.CV_CAP_PROP_FOURCC)
                        print "\t Framerate: ",self.cap.get(cv2.cv.CV_CAP_PROP_FPS)
                        print "\t Number of Frames: ",self.cap.get(7)
                    
                        print "\t Total length (s) ",self.cap.get(7) / self.cap.get(cv2.cv.CV_CAP_PROP_FPS)
                    
                    self.mediaTotalLength = self.cap.get(7) / self.cap.get(cv2.cv.CV_CAP_PROP_FPS)   ### in seconds

                else:

                    QMessageBox.critical(self, programName, '%s not found!<br>Fix the media path in the observation before playing it' % mediaFile, QMessageBox.Ok | QMessageBox.Default, QMessageBox.NoButton)
                    memObsId = self.observationId
                    self.close_observation()

                    self.new_observation( 'edit', memObsId)
                    return False

        
        self.videoTab.setEnabled(True)
        self.toolBox.setItemEnabled (video, True)
        self.toolBox.setCurrentIndex(video)
        



        self.openCVtimer = QTimer(self)
        self.openCVtimer.timeout.connect(self.openCVtimerOut)
        if self.DEBUG: print 'start opencv timer'
        self.openCVtick = 40
        self.openCVtimer.setInterval(self.openCVtick)

        ### show first frame
        self.openCVtimerOut()
        
        ### reset to init
        self.cap.set(cv2.cv.CV_CAP_PROP_POS_FRAMES, 0)

        self.lbTime.setText( self.convertTime( 0 ))
        self.hsVideo.setValue( 0)



    def openCVtimerOut(self):
        '''
        read frame and update image
        '''

        if self.cap.isOpened():
            ret, frame = self.cap.read()
            print 'ret', ret

            if frame == None:
                print 'frame error'
                return

            height, width, bytesPerComponent = frame.shape
            bytesPerLine = 3 * width
            # Convert to RGB for QImage
            cv2.cvtColor(frame, cv.CV_BGR2RGB, frame)
        
            qimage = QImage(frame.data, width, height, bytesPerLine, QImage.Format_RGB888)

            pixmap = QPixmap.fromImage( qimage )
            
            self.lbOpenCV.setPixmap(pixmap)
            
            currentTime = self.cap.get(cv2.cv.CV_CAP_PROP_POS_FRAMES) / self.cap.get(cv2.cv.CV_CAP_PROP_FPS)   ### in sec

            ### extract State events
            StateBehaviorsCodes = [ self.pj['behaviors_conf'][x]['code'] for x in [y for y in self.pj['behaviors_conf'] if 'State' in self.pj['behaviors_conf'][y]['type']] ]

            self.currentStates = {}
            
            ### add states for no focal subject
            self.currentStates[ '' ] = []
            for sbc in StateBehaviorsCodes:
                if len(  [ x[ pj_obs_fields['code'] ] for x in self.pj['observations'][self.observationId]['events' ] if x[ pj_obs_fields['subject'] ] == '' and x[ pj_obs_fields['code'] ] == sbc and x[ pj_obs_fields['time'] ] <= currentTime / 1000 ] ) % 2: ### test if odd
                    self.currentStates[''].append(sbc)

            ### add states for all configured subjects
            for idx in self.pj['subjects_conf']:

                ### add subject index
                self.currentStates[ idx ] = []
                for sbc in StateBehaviorsCodes:
                    if len(  [ x[ pj_obs_fields['code'] ] for x in self.pj['observations'][self.observationId]['events' ] if x[ pj_obs_fields['subject'] ] == self.pj['subjects_conf'][idx]['name'] and x[ pj_obs_fields['code'] ] == sbc and x[ pj_obs_fields['time'] ] <= currentTime / 1000 ] ) % 2: ### test if odd
                        self.currentStates[idx].append(sbc)

            if self.currentStates[ '' ]:
                self.lbState.setText('Current state(s): <b>' + '</b> ,<b> '.join(self.currentStates[ '' ]) + '</b>' )

            else:
                self.lbState.clear()

            ### show current states
            if self.currentSubject:
                ### get index of focal subject (by name)
                idx = [idx for idx in self.pj['subjects_conf'] if self.pj['subjects_conf'][idx]['name'] == self.currentSubject][0]
                self.lbCurrentStates.setText(  '%s' % (', '.join(self.currentStates[ idx ]))) 
            else:
                self.lbCurrentStates.setText(  '%s' % (', '.join(self.currentStates[ '' ]))) 

            ### show selected subjects
            for idx in sorted( self.pj['subjects_conf'].keys() ):

                self.twSubjects.item(int(idx), 2 ).setText( ','.join(self.currentStates[idx]) )

            self.lbTime.setText( self.convertTime( currentTime ))
            self.hsVideo.setValue( currentTime / self.mediaTotalLength * (slider_maximum - 1))


    def initialize_new_observation_vlc(self):
        '''
        initialize new observation for VLC
        '''

        if self.DEBUG: print 'initialize new observation for VLC'
        
        ### creating a basic vlc instance
        self.instance = vlc.Instance()

        ### creating an empty vlc media player
        self.mediaplayer = self.instance.media_player_new()

        self.mediaListPlayer = self.instance.media_list_player_new()
        self.mediaListPlayer.set_media_player(self.mediaplayer)

        self.media_list = self.instance.media_list_new()

        self.media_list2 = self.instance.media_list_new()

        # In this widget, the video will be drawn
        self.videoframe = QtGui.QFrame()
        self.palette = self.videoframe.palette()
        self.palette.setColor (QtGui.QPalette.Window, QtGui.QColor(0,0,0))
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

        self.toolBox.insertItem(0, self.videoTab, 'Audio/Video')

        self.toolBar.setEnabled(True)
        self.dwObservations.setVisible(True)
        self.toolBox.setVisible(True)
        self.lbFocalSubject.setVisible(True)
        self.lbCurrentStates.setVisible(True)

        self.mediaListPlayer.stop()

        ### empty media list
        while self.media_list.count():
            self.media_list.remove_index(0)

        self.mediaListPlayer.set_media_list(self.media_list)

        if self.DEBUG: print 'self.media_list.count()', self.media_list.count()

        ### empty media list
        while self.media_list2.count():
            self.media_list2.remove_index(0)

        #self.simultaneousMedia = False

        ### delete second player
        '''
        if self.simultaneousMedia:

            del self.mediaplayer2

            self.vboxlayout.removeWidget(self.videoframe2)
            self.vboxlayout.removeWidget(self.volumeslider2)

            self.videoframe2.deleteLater()

            self.volumeslider2.deleteLater()
            
            self.simultaneousMedia = False
        '''



        ### init duration of media file
        del self.duration[0: len(self.duration)]

        if self.pj['observations'][self.observationId]['type'] in [LIVE]:

            #if self.DEBUG: print 'set up live observation', live
            self.simultaneousMedia = False

            self.liveTab.setEnabled(True)
            self.toolBox.setItemEnabled (live_tab_index, True)   ### enable live tab
            self.toolBox.setCurrentIndex(live_tab_index)  ### show live tab

            self.toolBar.setEnabled(False)

            self.liveObservationStarted = False
            self.textButton.setText('Start live observation')
            self.lbTimeLive.setText('00:00:00.000')
    
            self.liveStartTime = None
            self.liveTimer.stop()

            return True


        ### MEDIA CODING

        if self.pj['observations'][self.observationId]['type'] in [MEDIA]:

            if self.DEBUG: print 'init video coding. obs id:', self.observationId

            #self.fileName = self.pj['observations'][self.observationId]['file']

            ### check file for mediaplayer #1
            if '1' in self.pj['observations'][self.observationId]['file'] and self.pj['observations'][self.observationId]['file']['1']:

                self.simultaneousMedia = False
                for mediaFile in self.pj['observations'][self.observationId]['file']['1']:

                    if self.DEBUG: print 'media file', mediaFile, 'is file', os.path.isfile( mediaFile )

                    if os.path.isfile( mediaFile ):

                        media = self.instance.media_new( mediaFile )
                        media.parse()
                        if self.DEBUG: print 'media file',mediaFile ,'duration', media.get_duration()

                        self.duration.append(media.get_duration())

                        self.media_list.add_media(media)

                    else:

                        QMessageBox.critical(self, programName, '%s not found!<br>Fix the media path in the observation before playing it' % mediaFile, QMessageBox.Ok | QMessageBox.Default, QMessageBox.NoButton)
                        memObsId = self.observationId
                        self.close_observation()

                        self.new_observation( 'edit', memObsId)
                        return False


                self.mediaListPlayer.set_media_list(self.media_list)
                if self.DEBUG: print 'duration', self.duration

                ### display media player in videofram

                if self.DEBUG: print 'embed player:', self.embedPlayer
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
            
                    elif sys.platform == "darwin": # for MacOS
                        self.mediaplayer.set_nsobject(self.videoframe.winId())


                ### show first frame of video
                if self.DEBUG: print   'app.hasPendingEvents()', app.hasPendingEvents()
                app.processEvents()

                #self.mediaListPlayer.play()

                self.mediaListPlayer.play_item_at_index( 0 )
                app.processEvents()

                ### self.mediaListPlayer.play()
                while self.mediaListPlayer.get_state() != vlc.State.Playing:
                    pass
                self.mediaListPlayer.pause()
                app.processEvents()

                self.mediaplayer.set_time(0)
                

            else:
                QMessageBox.warning(self, programName , 'You must choose a media file to code')
                return False


            ### check if media list player 1 contains more than 1 media
            if '1' in self.pj['observations'][self.observationId]['file'] and len(self.pj['observations'][self.observationId]['file']['1']) > 1 and \
               '2' in self.pj['observations'][self.observationId]['file'] and  self.pj['observations'][self.observationId]['file']['2']:
                   QMessageBox.warning(self, programName , 'It is not yet possible to play a second media when many media are loaded in the first media player' )
                   


            ### check for second media to be played together
            elif '2' in self.pj['observations'][self.observationId]['file'] and  self.pj['observations'][self.observationId]['file']['2']:
                    
                    ### create 2nd mediaplayer
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
                    
                    
                    ### add media file
                    for mediaFile in self.pj['observations'][self.observationId]['file']['2']:
    
                        if os.path.isfile( mediaFile ):    
    
                            media = self.instance.media_new( mediaFile )
                            media.parse()
                            if self.DEBUG: print 'media file 2',mediaFile ,'duration', media.get_duration()
    
                            self.media_list2.add_media(media)
    
    
                    self.mediaListPlayer2.set_media_list(self.media_list2)
                    
                    if self.embedPlayer:
                        if sys.platform == "linux2": # for Linux using the X Server
                            self.mediaplayer2.set_xwindow(self.videoframe2.winId())
        
                        elif sys.platform == "win32": # for Windows
                            ### http://srinikom.github.io/pyside-bz-archive/523.html
                            import ctypes
                            ctypes.pythonapi.PyCObject_AsVoidPtr.restype = ctypes.c_void_p
                            ctypes.pythonapi.PyCObject_AsVoidPtr.argtypes = [ctypes.py_object]
                
                            int_hwnd = ctypes.pythonapi.PyCObject_AsVoidPtr(self.videoframe2.winId())
                            
                            self.mediaplayer2.set_hwnd(int_hwnd)
                
                            ### self.mediaplayer.set_hwnd(self.videoframe.winId())
        
        
                        elif sys.platform == "darwin": # for MacOS
                            self.mediaplayer2.set_nsobject(self.videoframe2.windId())
    
                    ### show first frame of video
                    if self.DEBUG: print   'app.hasPendingEvents()',       app.hasPendingEvents()
                    app.processEvents()


                    self.mediaListPlayer2.play()
                    app.processEvents()
                    
                    ### self.mediaListPlayer.play()
                    while self.mediaListPlayer2.get_state() != vlc.State.Playing:
                        pass
                    self.mediaListPlayer2.pause()
                    app.processEvents()
                    self.mediaplayer2.set_time(0)




            self.videoTab.setEnabled(True)
            self.toolBox.setItemEnabled (video, True)
            self.toolBox.setCurrentIndex(video)
            
            self.toolBar.setEnabled(True)
            self.timer.start(200)

            return True


    def edit_observation(self):
        
        ### let user choose one observation to edit
        result, selectedObs = self.selectObservations( EDIT )
        
        ### check if observation to edit is running
        if selectedObs:
            if self.observationId != selectedObs[0]:
    
                self.new_observation( EDIT, selectedObs[0])   ### observation id to edit
            else:
                QMessageBox.warning(self, programName , 'The observation <b>%s</b> is running!<br>Close it before editing.' % self.observationId)

    
    def loadEventsInTW(self, obsId):
        ### load events in table widget
        self.twEvents.setRowCount(len( self.pj['observations'][obsId]['events'] ))
        row = 0

        for event in self.pj['observations'][obsId]['events']:

            for field_type in tw_events_fields:
                
                if field_type in pj_events_fields:

                    field = event[ pj_obs_fields[field_type]  ]
                    if field_type == 'time':
                        field = self.convertTime( field) 
                        
                    self.twEvents.setItem(row, tw_obs_fields[field_type] , QTableWidgetItem(str(field)))

                else:
                    self.twEvents.setItem(row, tw_obs_fields[field_type] , QTableWidgetItem(''))

            row += 1

        self.update_events_start_stop()

    def open_observation(self):

        ### check if curretn observation is running
        if self.observationId:
            QMessageBox.critical(self, programName , 'You must close the running observation before.' )
            return

        result, selectedObs = self.selectObservations( OPEN )

        if selectedObs:
            self.observationId = selectedObs[0]

            ### load events in table widget
            self.loadEventsInTW(self.observationId)

            ### set player type
            '''
            FIXME
            
            
            if 'playertype' in self.pj['observations'][self.observationId]:
                self.playerType = self.pj['observations'][self.observationId][ 'playertype' ]
            else:   ### set first player available (VLC by default)
                self.playerType = self.availablePlayers[0]
            '''
            self.playerType = VLC
            
            
            if self.playerType == VLC:
                if self.initialize_new_observation_vlc():
   
                    self.menu_options()
    
                    ### title of dock widget
                    self.dwObservations.setWindowTitle('Events for ' + self.observationId) 
    
                    #self.sort_events()
    
                else:
    
                    self.observationId = ''
                    self.twEvents.setRowCount(0)
                    self.menu_options()

            if self.playerType == OPENCV:
                print 'opencv'
                self.initialize_new_observation_opencv()
                self.menu_options()
                ### title of dock widget
                self.dwObservations.setWindowTitle('Events for ' + self.observationId) 



    def selectObservations(self, mode):
        '''
        show observations list window
        mode: accepted values: EDIT, OPEN, LIST, SELECT
        
        '''

        obsList = obs_list2.observationsList_widget()
        obsList.pb.setText(mode)
        
        obsList.pbOpen.setVisible(False)
        obsList.pbEdit.setVisible(False)

        if mode in [EDIT, OPEN, LIST]:
            obsList.view.setSelectionMode( QAbstractItemView.SingleSelection )

        if mode == LIST:
            obsList.pbOpen.setVisible(True)
            obsList.pbEdit.setVisible(True)
            obsList.pb.setVisible(False)

        obsList.pbSelectAll.setVisible(False)
        obsList.pbUnSelectAll.setVisible(False)
        
        obsListFields = ['id', 'date', 'description', 'media']
        indepVarHeader = []
        if INDEPENDENT_VARIABLES in self.pj:
            
            if self.DEBUG: print self.pj[ INDEPENDENT_VARIABLES ]
            
            for idx in sorted( list(self.pj[ INDEPENDENT_VARIABLES ].keys())  ):
                print idx, self.pj[ INDEPENDENT_VARIABLES ][ idx ]['label']
                indepVarHeader.append(  self.pj[ INDEPENDENT_VARIABLES ][ idx ]['label'] )

        if self.DEBUG: print obsListFields
        
        obsList.model.setHorizontalHeaderLabels(obsListFields + indepVarHeader)
        obsList.comboBox.addItems(obsListFields + indepVarHeader)

        for obs in sorted( list(self.pj['observations'].keys()) ):
            
            date = self.pj['observations'][obs]['date'].replace('T',' ')
            descr = self.pj['observations'][obs]['description']

            '''
            media = ''
            if self.pj['observations'][obs]['type'] in [MEDIA]:
                media =  '  '.join(   [ os.path.basename(x) for x in self.pj['observations'][obs]['file']['1']  ]    )
            elif self.pj['observations'][obs]['type'] in [LIVE]:
                media = LIVE
            '''
                
            mediaList = []
            if self.pj['observations'][obs]['type'] in [MEDIA]:
                for idx in self.pj['observations'][obs]['file']:
                    for media in self.pj['observations'][obs]['file'][idx]:
                        mediaList.append('#%s: %s' % (idx , media))
    
                media = '\n'.join( mediaList )
            elif self.pj['observations'][obs]['type'] in [LIVE]:
                media = LIVE

            ### indep var
            indepVar = []
            if INDEPENDENT_VARIABLES in self.pj['observations'][obs]:
                for var in indepVarHeader:
                    if var in self.pj['observations'][obs][ INDEPENDENT_VARIABLES ]:
                        indepVar.append( QStandardItem( self.pj['observations'][obs][ INDEPENDENT_VARIABLES ][var] ) )

            obsList.model.invisibleRootItem().appendRow( [ QStandardItem(obs), QStandardItem(date), QStandardItem(descr) , QStandardItem( media )]  +  indepVar )

        obsList.view.setEditTriggers(QAbstractItemView.NoEditTriggers);
        obsList.label.setText( '%d observation(s)' % obsList.model.rowCount())

        obsList.resize(800, 600)

        selectedObs = []
        
        result = obsList.exec_()
        print 'result', result
        
        if result:
            if obsList.view.selectedIndexes():
                for idx in obsList.view.selectedIndexes():
                    if idx.column() == 0:   ### first column
                        selectedObs.append( idx.data() )

        if result == 0:
            resultStr = ''
        if result == 1:
            resultStr = 'ok'
        if result == 2:
            resultStr = OPEN
        if result == 3:
            resultStr = EDIT
        

        return resultStr, selectedObs


    """
    def observations_list(self, mode):
        '''
        show observations list window
        open: allow user to select the observation to open
        edit: allow user to select the observation to edit
        select: allow user to select the one or more observations
        '''

    
        if self.pj['observations']:

            obsList = observations_list.ObservationsList()
            
            obsList.setGeometry(self.pos().x() + 100, self.pos().y() + 130, 700, 400)

            obsList.twObservations.setRowCount(0)

            if mode == 'open':

                if self.DEBUG: print 'open observation', self.pj['observations']
                obsList.twObservations.setSelectionMode( QAbstractItemView.SingleSelection )
                obsList.pbEdit.setVisible(False)
                obsList.pbOK.setVisible(False)
                obsList.pbSelectAll.setVisible(False)
                obsList.pbUnSelectAll.setVisible(False)

            if mode == 'edit':
                obsList.twObservations.setSelectionMode( QAbstractItemView.SingleSelection )
                obsList.pbOpen.setVisible(False)
                obsList.pbOK.setVisible(False)
                obsList.pbSelectAll.setVisible(False)
                obsList.pbUnSelectAll.setVisible(False)

            if mode == 'select':
                obsList.twObservations.setSelectionMode( QAbstractItemView.ExtendedSelection )
                obsList.pbOpen.setVisible(False)
                obsList.pbEdit.setVisible(False)


            #if self.pj['observations']:
            for obs in sorted( list(self.pj['observations'].keys()) ):

                if self.DEBUG: print 'observation:', obs

                obsList.twObservations.setRowCount(obsList.twObservations.rowCount() + 1)

                item = QTableWidgetItem(obs) 
                obsList.twObservations.setItem(obsList.twObservations.rowCount() - 1, 0 ,item)

                item = QTableWidgetItem( self.pj['observations'][obs]['date'].replace('T',' ') ) 
                obsList.twObservations.setItem(obsList.twObservations.rowCount() - 1, 1 ,item)

                item = QTableWidgetItem( self.pj['observations'][obs]['description'].replace('\r\n',' ').replace('\n',' ').replace('\r',' ') ) 
                obsList.twObservations.setItem(obsList.twObservations.rowCount() - 1, 2 ,item)

                ### media file
                if self.pj['observations'][obs]['type'] in ['MEDIA']:
                    item = QTableWidgetItem( '  '.join(   [ os.path.basename(x) for x in self.pj['observations'][obs]['file']['1']  ]    )) 
                elif self.pj['observations'][obs]['type'] in ['LIVE']:
                    item = QTableWidgetItem( 'Live' )
                else:
                    item = QTableWidgetItem( '' )

                obsList.twObservations.setItem(obsList.twObservations.rowCount() - 1, 3 ,item)


                if '2' in self.pj['observations'][obs]['file'] and self.pj['observations'][obs]['file']['2']:

                    item = QTableWidgetItem( '  '.join( [ os.path.basename(x) for x in self.pj['observations'][obs]['file']['2'] ] )) 
                    obsList.twObservations.setItem(obsList.twObservations.rowCount() - 1, 4 ,item)


            obsList.twObservations.resizeColumnsToContents()

       
            if obsList.exec_():

                ### print 'obsList result', obsList.result()

                if obsList.twObservations.selectedIndexes():

                    ### return selected observations
                    if mode == 'select':
                        selected_obsId = []
                        print 'obsList.twObservations.selectedIndexes()', obsList.twObservations.selectedIndexes()
                        for i in obsList.twObservations.selectedIndexes():
                            ### print i.row()
                            if obsList.twObservations.item( i.row(), 0).text() not in selected_obsId:
                                selected_obsId.append( obsList.twObservations.item( i.row(), 0).text() )

                        if self.DEBUG: print 'selected observations id', selected_obsId
                        return selected_obsId

                    ### open observation
                    if mode == 'open':
                        
                        self.observationId = obsList.twObservations.item( obsList.twObservations.selectedIndexes()[0].row(), 0).text()
        
                        ### load events
                        self.twEvents.setRowCount(len( self.pj['observations'][self.observationId]['events'] ))
                        row = 0
        
                        for event in self.pj['observations'][self.observationId]['events']:
        
                            for field_type in tw_events_fields:
                                
                                if field_type in pj_events_fields:
        
                                    field = event[ pj_obs_fields[field_type]  ]
                                    self.twEvents.setItem(row, tw_obs_fields[field_type] , QTableWidgetItem(str(field)))
        
                                else:
                                    self.twEvents.setItem(row, tw_obs_fields[field_type] , QTableWidgetItem(''))
        
                            row += 1
        
        
                        if self.initialize_new_observation():
                        
        
                            self.menu_options()
        
                            ### title of dock widget
                            self.dwObservations.setWindowTitle('Events for ' + self.observationId) 
        
                            self.sort_events()

                        else:

                            self.observationId = ''
                            self.twEvents.setRowCount(0)
                            self.menu_options()


                    ### edit observation
                    if mode == 'edit':

                        ### check if observation to edit is running
                        if self.observationId != obsList.twObservations.item( obsList.twObservations.selectedIndexes()[0].row(), 0).text():

                            self.new_observation( 'edit', obsList.twObservations.item( obsList.twObservations.selectedIndexes()[0].row(), 0).text())   ### observation id to edit
                        else:
                            QMessageBox.warning(self, programName , 'The observation <b>%s</b> is running!<br>Close it before editing.' % self.observationId)
    """


    def new_observation(self, mode = 'new', obsId = ''):
        '''
        define a new observation or edit an observation
        '''

        if self.DEBUG: print 'mode', mode

        ### check if current observation must be closed to create a new one
        if mode == 'new' and self.observationId:
            response = dialog.MessageDialog(programName, 'The current observation will be closed. Do you want to continue?', ['Yes', 'No'])
            if response == 'No':
                return
            else:
                self.close_observation()


        observationWindow = observation.Observation()
        
        observationWindow.setGeometry(self.pos().x() + 100, self.pos().y() + 130, 600, 400)
        
        observationWindow.pj = self.pj

        observationWindow.mode = mode
        observationWindow.mem_obs_id = obsId

        observationWindow.dteDate.setDateTime( QDateTime.currentDateTime() )

        ### add indepvariables
        if INDEPENDENT_VARIABLES in self.pj:
            observationWindow.twIndepVariables.setRowCount(0)
            for i in sorted( self.pj[INDEPENDENT_VARIABLES].keys() ):
                
                if self.DEBUG: print 'variable label',  self.pj[INDEPENDENT_VARIABLES][i]['label']
                
                observationWindow.twIndepVariables.setRowCount(observationWindow.twIndepVariables.rowCount() + 1)

                ### label
                item = QTableWidgetItem()
                indepVarLabel = self.pj[INDEPENDENT_VARIABLES][i]['label'] 
                item.setText( indepVarLabel )
                item.setFlags(Qt.ItemIsEnabled)
                observationWindow.twIndepVariables.setItem(observationWindow.twIndepVariables.rowCount() - 1, 0, item)

                ### var type
                item = QTableWidgetItem()
                item.setText( self.pj[INDEPENDENT_VARIABLES][i]['type']  )
                item.setFlags(Qt.ItemIsEnabled)   ### not modifiable
                observationWindow.twIndepVariables.setItem(observationWindow.twIndepVariables.rowCount() - 1, 1, item)

                
                ### var value
                item = QTableWidgetItem()
                ### check if obs has independent variables and var label is a key
                if mode == 'edit' and INDEPENDENT_VARIABLES in self.pj['observations'][obsId] and indepVarLabel in self.pj['observations'][obsId][INDEPENDENT_VARIABLES]:
                    txt = self.pj['observations'][obsId][INDEPENDENT_VARIABLES][indepVarLabel]

                elif mode == 'new':
                    txt = self.pj[INDEPENDENT_VARIABLES][i]['default value']
                else:
                    txt = ''

                item.setText( txt )
                observationWindow.twIndepVariables.setItem(observationWindow.twIndepVariables.rowCount() - 1, 2, item)


            observationWindow.twIndepVariables.resizeColumnsToContents()

        ### set player type
        observationWindow.rbVLC.setEnabled( VLC in self.availablePlayers )
        observationWindow.rbOpenCV.setEnabled(OPENCV in self.availablePlayers)

        '''FIXME to be removed
        if mode == 'new':
            if self.timeFormat == S:
                observationWindow.teTimeOffset.setVisible(False)
            if self.timeFormat == HHMMSS:
                observationWindow.leTimeOffset.setVisible(False)
        '''
        if self.timeFormat == S:
            observationWindow.teTimeOffset.setVisible(False)
        if self.timeFormat == HHMMSS:
            observationWindow.leTimeOffset.setVisible(False)
        
        if self.pj[OBSERVATIONS][obsId]['time offset'] < 0:
            observationWindow.rbSubstract.setChecked(True)

        if mode == 'edit':

            observationWindow.setWindowTitle('Edit observation ' + obsId )
            mem_obs_id = obsId
            observationWindow.leObservationId.setText( obsId )
            observationWindow.dteDate.setDateTime( QDateTime.fromString( self.pj[OBSERVATIONS][obsId]['date'], 'yyyy-MM-ddThh:mm:ss') )
            observationWindow.teDescription.setPlainText( self.pj[OBSERVATIONS][obsId]['description'] )

            if self.timeFormat == S:
                '''observationWindow.teTimeOffset.setVisible(False)'''
                observationWindow.leTimeOffset.setText( self.convertTime( abs(self.pj[OBSERVATIONS][obsId]['time offset']) ))

            if self.timeFormat == HHMMSS:
                '''observationWindow.leTimeOffset.setVisible(False)'''

                time = QTime()
                h,m,s_dec = self.seconds2time( abs(self.pj[OBSERVATIONS][obsId]['time offset'])).split(':')
                s, ms = s_dec.split('.')
                time.setHMS(int(h),int(m),int(s),int(ms))
                observationWindow.teTimeOffset.setTime( time )


            if '1' in self.pj[OBSERVATIONS][obsId]['file'] and self.pj[OBSERVATIONS][obsId]['file']['1']:

                observationWindow.lwVideo.addItems( self.pj[OBSERVATIONS][obsId]['file']['1'] )

            ### check if simultaneous 2nd media
            if '2' in self.pj[OBSERVATIONS][obsId]['file'] and self.pj[OBSERVATIONS][obsId]['file']['2']:   ### media for 2nd player

                observationWindow.lwVideo_2.addItems( self.pj[OBSERVATIONS][obsId]['file']['2'] )


            if self.pj[OBSERVATIONS][obsId]['type'] in [MEDIA]:
                observationWindow.tabProjectType.setCurrentIndex(video)

                '''
                FIXME no more player type
                if 'playertype' in self.pj["observations"][obsId]:
                    observationWindow.rbVLC.setChecked(self.pj["observations"][obsId]['playertype'] == VLC)
                    observationWindow.rbOpenCV.setChecked(self.pj["observations"][obsId]['playertype'] == OPENCV)
                '''

            if self.pj[OBSERVATIONS][obsId]['type'] in [LIVE]:
                observationWindow.tabProjectType.setCurrentIndex(live)




        #####################################################################################
        #####################################################################################

        if observationWindow.exec_():
            '''
            ### check if observation id not empty
            if not observationWindow.leObservationId.text():
                QMessageBox.warning(self, programName , 'The <b>observation id</b> is mandatory!' )
                return
            '''

            ### check VLC
            '''
            FIXME no more player type
            if observationWindow.rbVLC.isChecked():
                self.playerType = VLC

            if observationWindow.rbOpenCV.isChecked():
                self.playerType = OPENCV
            '''

            self.playerType = VLC

            self.projectChanged = True

            ### check if new id already used
            '''
            if mode == 'new' and observationWindow.leObservationId.text():
                if observationWindow.leObservationId.text() in self.pj['observations']:
                    QMessageBox.warning(self, programName , 'The observation id <b>%s</b> is already used!' % observationWindow.leObservationId.text())
                    return
            '''

            new_obs_id = observationWindow.leObservationId.text()


            if mode == 'new':

                self.observationId = new_obs_id

                self.pj['observations'][self.observationId] = { 'file': [], 'type': '' ,  'date': '', 'description': '','time offset': 0, 'events': [] }


            ### check if id changed
            if mode == 'edit' and new_obs_id != obsId:

                ### check if changed id already used
                '''
                if new_obs_id in self.pj['observations']:
                    QMessageBox.warning(self, programName , 'An observation id <b>%s</b> is already used!' % new_obs_id)
                    return
                '''

                ### self.observationId = new_obs_id
                if self.DEBUG: 'observation id', obsId, 'changed in', new_obs_id

                self.pj['observations'][ new_obs_id ] = self.pj['observations'][ obsId ]
                del self.pj['observations'][ obsId ]


            '''
            FIXME
            self.pj['observations'][new_obs_id]['playertype'] = self.playerType'''

            ### observation date
            self.pj['observations'][new_obs_id]['date'] = observationWindow.dteDate.dateTime().toString(Qt.ISODate)

            self.pj['observations'][new_obs_id]['description'] = observationWindow.teDescription.toPlainText()

            ### observation type: read project type from tab text
            self.pj['observations'][new_obs_id]['type'] = observationWindow.tabProjectType.tabText( observationWindow.tabProjectType.currentIndex() ).upper()

            ### independent variables for observation
            self.pj['observations'][new_obs_id][INDEPENDENT_VARIABLES] = {}
            for r in range(0, observationWindow.twIndepVariables.rowCount()):

                ### set dictionary as label (col 0) => value (col 2)
                self.pj['observations'][new_obs_id][INDEPENDENT_VARIABLES][ observationWindow.twIndepVariables.item(r, 0).text() ] = observationWindow.twIndepVariables.item(r, 2).text()


            ### observation time offset

            if self.timeFormat == HHMMSS:
                self.timeOffset = self.time2seconds(observationWindow.teTimeOffset.time().toString('hh:mm:ss.zzz'))

            if self.timeFormat == S:
                self.timeOffset = abs( float( observationWindow.leTimeOffset.text() ))

            if observationWindow.rbSubstract.isChecked():
                self.timeOffset = - self.timeOffset

            self.pj['observations'][new_obs_id]['time offset'] = self.timeOffset

            self.display_timeoffset_statubar()

            ### media file
            fileName = {}

            ### media
            if self.pj['observations'][new_obs_id]['type'] in [MEDIA]:
                
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
                            ### save full path 
                            fileName['2'].append (  observationWindow.lwVideo_2.item(i).text() )
                        else:
                            fileName['2'].append ( os.path.basename( observationWindow.lwVideo_2.item(i).text() ) )


                if self.DEBUG: print 'media fileName', fileName

                self.pj['observations'][new_obs_id]['file'] = fileName


            if mode == 'new':
                
                self.menu_options()
                
                ### title of dock widget
                self.dwObservations.setWindowTitle('Events for ' + self.observationId) 
                
                if self.playerType == VLC:
                    self.initialize_new_observation_vlc()

                if self.playerType == OPENCV:
                    self.initialize_new_observation_opencv()


    def close_observation(self):
        '''
        close current observation
        '''

        if self.DEBUG: print '\nClose observation', self.playerType

        self.observationId = ''

        if self.playerType == VLC:
            self.timer.stop()
            self.mediaplayer.stop()
            ### empty media list
            while self.media_list.count():
                self.media_list.remove_index(0)

            if self.simultaneousMedia:
                self.mediaplayer2.stop()
                while self.media_list2.count():
                    self.media_list2.remove_index(0)

        if self.playerType == OPENCV:

            self.openCVtimer.stop()

            self.cap.release()
            #cv2.destroyAllWindows()

        self.statusbar.showMessage('',0)

        ### delete layout

        while self.video1layout.count():
            item = self.video1layout.takeAt(0)
            item.widget().deleteLater()

        '''
        while self.vboxlayout.count():
            item = self.vboxlayout.takeAt(0)
            item.widget().deleteLater()
        '''
        if self.simultaneousMedia:
            while self.video2layout.count():
                item = self.video2layout.takeAt(0)
                item.widget().deleteLater()
                self.simultaneousMedia = False


        self.videoTab.deleteLater()

        self.toolBar.setEnabled(False)
        self.dwObservations.setVisible(False)
        self.toolBox.setVisible(False)
        self.lbFocalSubject.setVisible(False)
        self.lbCurrentStates.setVisible(False)

        self.twEvents.setRowCount(0)

        self.lbTime.clear()
        self.lbSubject.clear()

        self.lbState.clear()
        self.lbTimeOffset.clear()
        self.lbSpeed.clear()

        self.menu_options()



    def readConfigFile(self):
        '''
        read config file
        '''
        if self.DEBUG: print 'read config file'
        

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

            ### Saving file basename disabled
            '''
            try:
                self.saveMediaFilePath = (settings.value('Save_media_file_path') == 'true')
            except:
                self.saveMediaFilePath = True
            '''

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


    def saveConfigFile(self):
        '''
        save config file
        '''

        if self.DEBUG: print 'save config file'

        settings = QSettings(os.path.expanduser('~') + os.sep + '.boris', QSettings.IniFormat)

        #settings.setValue('MainWindow/State', self.saveState())
        settings.setValue('MainWindow/Size', self.size())
        settings.setValue('MainWindow/Position', self.pos())

        settings.setValue('Time/Format', self.timeFormat )
        settings.setValue('Time/Repositioning_time_offset', self.repositioningTimeOffset )
        settings.setValue('Time/fast_forward_speed', self.fast )

        settings.setValue('Save_media_file_path', self.saveMediaFilePath )

        settings.setValue('Automatic_backup', self.automaticBackup )

        if self.DEBUG: print 'behaviouralStringsSeparator:', self.behaviouralStringsSeparator

        settings.setValue('behavioural_strings_separator', self.behaviouralStringsSeparator )

        settings.setValue('confirm_sound', self.confirmSound)

        settings.setValue('embed_player', self.embedPlayer)


    def edit_project_activated(self):

        if self.project:
            self.edit_project('edit')
        else:
            QMessageBox.warning(self, programName, 'There is no project to edit')



    def display_timeoffset_statubar(self):
        ### display in status bar
        if self.timeOffset:
        
            if self.timeFormat == S:
                timeOffset = str( self.timeOffset ) 
            
            elif self.timeFormat == HHMMSS:

                timeOffset = self.seconds2time( self.timeOffset )
                
            self.lbTimeOffset.setText('Time offset: <b>%s</b>' % timeOffset )
        else:
            self.lbTimeOffset.clear()


    def observation_analysis(self, behaviors):
        '''
        analyze time budget etc
        behaviors [ [time, code, modifier]  ]
        '''

        if self.DEBUG: print 'observation analysis', behaviors

        states = {}
        points = {}

        for behavior in behaviors:

            time, code, modifier = behavior

            for event in self.pj['behaviors_conf']:

                if code == self.pj['behaviors_conf'][event]['code']:

                    ### if event has modifiers and no modifier selected
                    if not modifier and self.pj['behaviors_conf'][event]['modifiers']:
                        modifier = 'no modifier'

                    if 'STATE' in self.pj['behaviors_conf'][event]['type'].upper():

                        if code +'###' + modifier in states:
                            states[code +'###' + modifier ].append( time )
                        else:
                            states[code +'###' + modifier] = [ time ]
                            
                    if 'POINT' in self.pj['behaviors_conf'][event]['type'].upper():

                        if code +'###' + modifier in points:
                            points[code +'###' + modifier ].append(time)
                        else:
                            points[code +'###' + modifier] = [time]

        if self.DEBUG: print 'states',states
        ### states stats
        states_paired = {}
        
        for code in states:
            
            #tot_duration = 0

            ### check if values are paired
            if len(states[code]) % 2:
                if self.DEBUG: print 'Events are not paired for ' + code.replace('###',' ')
                QMessageBox.warning(self, programName , 'Events are not paired for the <b>%s</b> event' % code.replace('###',' ') )

            count = 0
            while len(states[code]) >= 2:
                t1 = states[code].pop(0)
                t2 = states[code].pop(0)

                if code in states_paired:
                    states_paired[code].append((t1, t2))
                else:
                    states_paired[code] = [(t1, t2)]

        if self.DEBUG: print 'states paired',states_paired
        return points, states_paired



    def analyze_subject(self, selected_subjects, selected_observations ):
        '''
        analyze subjects / behaviors
        return 2 dictionaries:
        { 'subject|behavior': [(t1,t2),(t3,t4),(t5,t6)] } for state behaviors
        { 'subject|behavior': [t1,t2,t3,t4,t5,t6] } for point behaviors
        '''

        if self.DEBUG: print 'selected_subjects', selected_subjects
        
        ### filter observations by selected subject

        states_results = {}
        points_results = {}

        for subject_to_analyze in selected_subjects:
            
            #if self.DEBUG: print 'subject to analyze:', subject_to_analyze
            
            subject_states = {}

            for obs_id in selected_observations:

                ### extract time, code and modifier
                if subject_to_analyze == 'No subject':
                    behaviors_to_analyze = [[x[0], x[2], x[3] ] for x in self.pj['observations'][obs_id]['events'] if x[1] == '']   ### pass time and code
                else:
                    behaviors_to_analyze = [[x[0], x[2], x[3]] for x in self.pj['observations'][obs_id]['events'] if x[1] == subject_to_analyze]   ### pass time and code

                points, states_paired = self.observation_analysis(behaviors_to_analyze)

                for behavior in states_paired:
                    if subject_to_analyze + '|' + behavior in states_results:
                        states_results[ subject_to_analyze + '|' + behavior ].extend( states_paired[behavior] )
                    else:
                        states_results[ subject_to_analyze + '|' + behavior ] = states_paired[behavior]
                
                
                
                for behavior in points:
                    if subject_to_analyze + '|' + behavior in points_results:
                        points_results[ subject_to_analyze + '|' + behavior ].extend( points[behavior] )
                    else:
                        points_results[ subject_to_analyze + '|' + behavior ] = points[behavior]

        if self.DEBUG:
            print 'states results', states_results
            print 'points results', points_results

        return states_results, points_results




    def extract_observed_subjects(self, selected_observations):
        '''
        extract unique subjects from obs_id observation 
        '''
        
        observed_subjects = []
        
        ### extract events from selected observations
        all_events =   [ self.pj['observations'][x]['events'] for x in self.pj['observations'] if x in selected_observations]
        for events in all_events:
            for event in events:
                observed_subjects.append( event[pj_obs_fields['subject']] )
        
        ### remove duplicate
        observed_subjects = list( set( observed_subjects ) )

        return observed_subjects


    def select_subjects(self, observed_subjects):
        '''
        allow user to select subjects from current project
        add no subject if observations do no contain subject
        '''

        subjectsSelection = checkingBox_list()

        all_subjects = sorted( [  self.pj['subjects_conf'][x][ 'name' ]  for x in self.pj['subjects_conf'] ] )

        for subject in all_subjects:

            if self.DEBUG: print subject    #### subject code

            subjectsSelection.item = QListWidgetItem(subjectsSelection.lw)

            subjectsSelection.ch = QCheckBox()

            subjectsSelection.ch.setText( subject )

            
            if subject in observed_subjects:

                subjectsSelection.ch.setChecked(True)

            subjectsSelection.lw.setItemWidget(subjectsSelection.item, subjectsSelection.ch)

        ### add 'No subject'
        if '' in observed_subjects:
            
            subjectsSelection.item = QListWidgetItem(subjectsSelection.lw)
            subjectsSelection.ch = QCheckBox()
            subjectsSelection.ch.setText( 'No subject' )
            subjectsSelection.lw.setItemWidget(subjectsSelection.item, subjectsSelection.ch)


        subjectsSelection.setWindowTitle('Select subjects to analyze')
        subjectsSelection.label.setText('Available subjects')

        subj_sel = []

        if subjectsSelection.exec_():

            for idx in xrange(subjectsSelection.lw.count()):

                check_box = subjectsSelection.lw.itemWidget(subjectsSelection.lw.item(idx))
                if check_box.isChecked():
                    subj_sel.append( check_box.text() )

            return subj_sel
        else:
            return []

    def combinationsCodeModifier(self):
        '''
        returns all code and modifier combinations
        'no modifier' if event has modifiers but no one selected
        '''
        codes = []
        for event in self.pj['behaviors_conf']:

            if self.pj['behaviors_conf'][event]['modifiers']:

                ### add event without modifier
                codes.append( self.pj['behaviors_conf'][event]['code'] + '###' + 'no modifier')
                ### add code with all modifiers
                for modifier in self.pj['behaviors_conf'][event]['modifiers'].split(','):
                    codes.append( self.pj['behaviors_conf'][event]['code'] + '###' + modifier)
            else:   ### event without modifier
                codes.append( self.pj['behaviors_conf'][event]['code'] + '###' )

        return codes


    def time_budget(self):
        '''
        time budget
        '''

        if self.DEBUG: print 'Time budget function'

        ### OBSERVATIONS

        ### ask user observations to analyze
        result, selected_observations = self.selectObservations( SELECT )

        if not selected_observations:
            return

        ### SUBJECTS

        ### extract subjects present in observations
        observed_subjects = self.extract_observed_subjects( selected_observations )
        
        if self.DEBUG: print '\nobserved subjects', observed_subjects

        if observed_subjects != ['']:

            ### ask user for subjects to analyze
            selected_subjects = self.select_subjects( observed_subjects )
    
            if self.DEBUG: print '\nselected subjects', selected_subjects
    
            if not selected_subjects:
                return

        else:   ### no subjects

            selected_subjects = ['No subject']


        states_results, points_results = self.analyze_subject( selected_subjects, selected_observations )

        if self.DEBUG: print '\nstates_results', states_results
        
        if self.DEBUG: print '\npoint_results', points_results

        out = []
        tot_duration = {}
        
        ### extract all event codes and modifier
        codes = self.combinationsCodeModifier()

        print 'all code modifier combinations', codes

        for subject_to_analyze in selected_subjects:
            
            tot_duration[ subject_to_analyze ] = 0 

            for behavior in codes:

                duration = 0
                number = 0

                ### state events
                if subject_to_analyze + '|' + behavior in states_results:

                    for event in states_results[ subject_to_analyze + '|' + behavior ]:
                        number += 1
                        duration += event[1] - event[0]

                    tot_duration[ subject_to_analyze ] += duration


                    if self.DEBUG: print 'behavior',behavior.split('###')

                    if number:
                        out.append( {'subject':subject_to_analyze, 'behavior': '%s (%s)' % tuple(behavior.split('###')),  'number': number, 'duration': duration, 'mean': round( duration/number, 1)  } )
                    else:
                        out.append( {'subject': subject_to_analyze, 'behavior': '%s (%s)' % tuple(behavior.split('###')),  'number': 0, 'duration': 0, 'mean': 0 } )

                ### point events
                if subject_to_analyze + '|' + behavior in points_results:

                    number = len( points_results[ subject_to_analyze + '|' + behavior ] )
                    duration = '-'

                    out.append( {'subject':subject_to_analyze, 'behavior': '%s (%s)' % tuple(behavior.split('###')) , 'number': number, 'duration':duration, 'mean':'-' } )

                if self.DEBUG:
                     if out: print out[-1]

            if self.DEBUG: print '\nsubject', subject_to_analyze, 'tot_duration[ subject_to_analyze ]', tot_duration[ subject_to_analyze ]

        ### widget for results visualization
        self.tb = timeBudgetResults(self.DEBUG)

        ### observations list
        self.tb.label.setText( 'Selected observations' )
        for obs in selected_observations:
            self.tb.lw.addItem(obs)


        tb_fields = ['Subject', 'Behavior', 'Total number', 'Total duration', 'Duration mean', '% of total time']
        self.tb.twTB.setColumnCount( len( tb_fields ) )
        self.tb.twTB.setHorizontalHeaderLabels(tb_fields)

        fields = ['subject', 'behavior', 'number', 'duration', 'mean']

        for row in out:
            if self.DEBUG: print 'row', row
            self.tb.twTB.setRowCount(self.tb.twTB.rowCount() + 1)

            column = 0 

            for field in fields:
                if self.DEBUG: print 'field',field
                item = QTableWidgetItem(str( row[field]).replace(' ()','' ))
                ### no modif allowed
                item.setFlags(Qt.ItemIsEnabled)
                self.tb.twTB.setItem(self.tb.twTB.rowCount() - 1, column , item)

                column += 1
                
            if self.DEBUG: print 'tot_duration[ row[0] ]', tot_duration[ row['subject'] ]
                
            if row['duration'] != '-' and tot_duration[ row['subject'] ]: 
                item = QTableWidgetItem(str( round( row['duration'] / tot_duration[ row['subject']  ] * 100,1)  ) )
            else:
                item = QTableWidgetItem( '-' )

            item.setFlags(Qt.ItemIsEnabled)
            self.tb.twTB.setItem(self.tb.twTB.rowCount() - 1, column , item)

        self.tb.twTB.resizeColumnsToContents()

        self.tb.show()



    def visualize_data(self):


        ### ask user for observations to analyze
        result, selected_observations = self.selectObservations( SELECT )
        if not selected_observations:
            return

        ### filter subjects in observations
        observed_subjects = self.extract_observed_subjects( selected_observations )


        if observed_subjects != ['']:
            ### ask user subject to analyze
            selected_subjects = self.select_subjects( observed_subjects )
    
            if self.DEBUG: print '\nselected subjects', selected_subjects
    
            if not selected_subjects:
                return

        else:   ### no subjects
            selected_subjects = ['No subject']


        states_results, points_results = self.analyze_subject( selected_subjects, selected_observations )

        ### extract all event codes and modifier
        codes = self.combinationsCodeModifier()
        if self.DEBUG: print 'all code modifier combinations', codes

        ### extract highest time and track number
        max_time, track_nb = 0, 0

        for subject_to_analyze in selected_subjects:

            for behavior in codes:

                if subject_to_analyze + '|' + behavior in states_results:
                    track_nb += 1

                    for event in states_results[ subject_to_analyze + '|' + behavior ]:
                        max_time = max( max_time, event[0], event[1] )

                if subject_to_analyze + '|' + behavior in points_results:
                    track_nb += 1
                    
                    for event in points_results[ subject_to_analyze + '|' + behavior ]:
                        max_time = max( max_time, event )


        if self.DEBUG:
            print 'tracks number', track_nb
            print 'max time', max_time, type(max_time)
            print '\nstates results', states_results
            print '\points results', points_results

        ### figure

        ### set rotation
        if self.timeFormat == HHMMSS:
             rotation = -45
        if self.timeFormat == S:
             rotation = 0

        width = 1000
        #xm = 1000

        left_margin = 10
        right_margin = 30
        
        x_init = 250
        y_init = 100
        spacer = 10   ### distance between elements
        header_height = 160
        top_margin = 10

        h = 20   ### height of element
        w = 1

        red = (255,0,0)
        blue = (0,0,255)
        black = (0,0,0)
        white = (255,255,255)


        height = top_margin + (track_nb ) * (h + spacer) + 280
        
        scene = svg.Scene('',  height, width)

        ### white background
        scene.add(svg.Rectangle((0,0), height, width , white))

        ### time line
        scene.add(svg.Rectangle((x_init, y_init), 1, ( width - x_init - right_margin ) , black))
        
        #scene.add(svg.Line((x_init + xm, y_init - h // 4), (x_init + xm, y_init), black ))

        ### total time
        scene.add( svg.Text(( x_init + ( width - x_init - right_margin ) - 2, y_init - h // 4 - 2 ), self.convertTime( max_time ), 12, rotation) )

        #scene.add(svg.Rectangle((x_init, y_init), 1, ( width - x_init - right_margin ) , black))

        step = round(max_time /100 * 10)
        if self.DEBUG: print 'step', step

        ### draw tick
        for i in range(10 + 1 ):   ### every tenth of total time
            
            ### if self.DEBUG: print round(x_init + i * (( width - x_init - right_margin ) /100 * 10))

            scene.add(svg.Line((round(x_init + i * (( width - x_init - right_margin ) /100 * 10)), y_init - h // 4), \
                               (round(x_init + i * (( width - x_init - right_margin ) /100 * 10)), y_init), black ))

            if i <10:
                
                scene.add( svg.Text(( round(x_init + i * (( width - x_init - right_margin ) /100 * 10)), y_init - h // 4 - 2 ), \
                self.convertTime( i * round(max_time /100 * 10, 1) ), 12, rotation) )

        y_init += 30

        for subject in selected_subjects:
            
            ### subject
            scene.add( svg.Text(( left_margin , y_init ), 'Subject: ' + subject, 14) )
            y_init += h

            for behavior in codes:

                if subject + '|' + behavior in points_results:
                    behaviorOut = '%s (%s)' % tuple(behavior.split('###')) 
                    scene.add( svg.Text(( left_margin, y_init + h - 2), behaviorOut.replace(' ()','' ), 16) )

                    for event in points_results[ subject + '|' + behavior ]:
                        scene.add(svg.Rectangle( (x_init + round(event / max_time * ( width - x_init - right_margin )), y_init), h, w, red) )

                    y_init += h + spacer

                if subject + '|' + behavior in states_results:
                    behaviorOut = '%s (%s)' % tuple(behavior.split('###'))
                    scene.add( svg.Text(( left_margin, y_init + h - 2), behaviorOut.replace(' ()','' ), 16) )

                    for event in states_results[ subject + '|' + behavior ]:
                        scene.add(svg.Rectangle( (x_init + round(event[0] / max_time * ( width - x_init - right_margin )), y_init), h,   round((event[1] - event[0]) / max_time * ( width - x_init - right_margin ) )     , blue))

                    y_init += h + spacer

            ### subject separator
            scene.add(svg.Rectangle((left_margin, y_init), 0.5, width - right_margin -left_margin, black))

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
        
        if self.DEBUG: print 'pj', self.pj

        ### check if project file version is newer than current BORIS project file version
        if 'project_format_version' in self.pj and float(self.pj['project_format_version']) > float(project_format_version):
            QMessageBox.critical(self, programName , 'This project file was created with a more recent version of BORIS.\nUpdate your version of BORIS to load it' )
            self.pj = {"time_format": "hh:mm:ss",\
            "project_date": "",\
            "project_name": "",\
            "project_description": "",\
            "subjects_conf" : {},\
            "behaviors_conf": {},\
            "observations": {} }
            return


        ### check if old version  v. 0 *.obs
        if 'project_format_version' not in self.pj:
            if self.DEBUG: print 'project format version:', 0

            ### convert VIDEO, AUDIO -> MEDIA
            self.pj['project_format_version'] = project_format_version

            for obs in [x for x in self.pj['observations']]:

                ### remove 'replace audio' key
                if 'replace audio' in self.pj['observations'][obs]:
                    del self.pj['observations'][obs]['replace audio']

                if self.pj['observations'][obs]['type'] in ['VIDEO','AUDIO']:
                    self.pj['observations'][obs]['type'] = MEDIA

                ### convert old media list in new one
                if len( self.pj['observations'][obs]['file'] ):
                    d1 = { '1':  [self.pj['observations'][obs]['file'][0]] }

                if len( self.pj['observations'][obs]['file'] ) == 2:
                    d1['2'] =  [self.pj['observations'][obs]['file'][1]]

                self.pj['observations'][obs]['file'] = d1

                if self.DEBUG: print "self.pj['observations'][obs]['file']", self.pj['observations'][obs]['file']

            ### convert VIDEO, AUDIO -> MEDIA

            for idx in [x for x in self.pj['subjects_conf']]:

                key, name = self.pj['subjects_conf'][idx]
                self.pj['subjects_conf'][idx] = {'key': key, 'name': name}


            QMessageBox.information(self, programName , 'The project file was converted to the new format (v. %s) in use with your version of BORIS.\nChoose a new file name for saving it.' % project_format_version)

            projectFileName = ''

        ### check program version
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

        ### check if current observation
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

        if self.DEBUG: print 'initialize new project'

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

        ### check if current observation
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


    def time2seconds(self, time):
        '''
        convert hh:mm:ss.s to number of seconds (float)
        '''
        flagNeg = '-' in time
        time = time.replace('-','')

        tsplit= time.split(':')
        
        h, m, s = int( tsplit[0] ), int( tsplit[1] ), float( tsplit[2] )
        

        #h, m, s = [ int(t) for t in time.split(':')]

        if flagNeg:
            return -(h * 3600 + m * 60 + s)
        else:
            return h * 3600 + m * 60 + s


    def seconds2time(self, sec):
        '''
        convert seconds to hh:mm:ss.sss format
        '''
        
        flagNeg = sec < 0
        sec = abs(sec)
        
        hours = 0
       
        minutes = int(sec / 60)
        if minutes >= 60:
            hours = int(minutes /60)
            minutes = minutes % 60

        secs = sec - hours*3600 - minutes * 60
        ssecs = '%06.3f' % secs

        return  "%s%02d:%02d:%s" % ('-' * flagNeg, hours, minutes, ssecs )


    def convertTime(self, sec):
        '''
        convert time in base of current format
        '''
        '''
        if self.timeOffset:
            sec += self.timeOffset
        '''

        if self.timeFormat == S:

            return '%.3f' % sec
            '''
            if self.playerType == VLC:
                return '%.1f' % sec

            if self.playerType == OPENCV:
                return '%.3f' % sec
            '''

        if self.timeFormat == HHMMSS:
            return self.seconds2time(sec)


    def edit_project(self, mode):

        '''
        project management
        mode: new/edit
        '''

        if self.observationId:
            QMessageBox.critical(self, programName , 'Close the running observation before creating/modifying the project.' )
            return

        if mode == 'new':

            if self.projectChanged:
                response = dialog.MessageDialog(programName, 'What to do about the current unsaved project?', ['Save', 'Discard', 'Cancel'])
                #response = dialog.MessageDialog(programName, 'The current project is not saved. Do you want to continue?', ['Yes', 'No'])

                if response == 'Save':
                    self.save_project_activated()

                if response == 'Cancel':
                    return

            '''self.pj = {"time_format": "hh:mm:ss", "project_date": "", "project_name": "", "project_description": "", "subjects_conf" : {}, "behaviors_conf": {}, "observations": {} }'''

            ### empty main window tables
            self.twConfiguration.setRowCount(0)   ### behaviors
            self.twSubjects.setRowCount(0)
            self.twEvents.setRowCount(0)


        newProjectWindow = DlgProject(self.DEBUG)
        
        newProjectWindow.setGeometry(self.pos().x() + 100, self.pos().y() + 130, 600, 400)

        newProjectWindow.setWindowTitle(mode + ' project')
        newProjectWindow.tabProject.setCurrentIndex(0)   ### project information

        newProjectWindow.obs = self.pj['behaviors_conf']
        newProjectWindow.subjects_conf = self.pj['subjects_conf']

        if self.pj['time_format'] == S:
            newProjectWindow.rbSeconds.setChecked(True)
            
        if self.pj['time_format'] == HHMMSS:
            newProjectWindow.rbHMS.setChecked(True)

        ### memorize video file name
        memVideoFileName = '@'

        if mode == 'new':

            newProjectWindow.dteDate.setDateTime( QDateTime.currentDateTime() )

        if mode == 'edit':

            if self.pj['project_name']: 
                newProjectWindow.leProjectName.setText(self.pj["project_name"])

            newProjectWindow.lbProjectFilePath.setText( 'Project file path: ' + self.projectFileName )

            if self.pj['project_description']: 
                newProjectWindow.teDescription.setPlainText(self.pj["project_description"])

            if self.pj['project_date']:

                if self.DEBUG: print 'project date:', self.pj['project_date']

                q = QDateTime.fromString(self.pj['project_date'], 'yyyy-MM-ddThh:mm:ss')

                newProjectWindow.dteDate.setDateTime( q )
            else:
                newProjectWindow.dteDate.setDateTime( QDateTime.currentDateTime() )



            ### load subjects in editor
            if self.pj['subjects_conf']:

                for idx in sorted ( self.pj['subjects_conf'].keys() ):

                    newProjectWindow.twSubjects.setRowCount(newProjectWindow.twSubjects.rowCount() + 1)

                    for i, field in enumerate(['key','name']):   ### key, name
                        item = QTableWidgetItem(self.pj['subjects_conf'][idx][field])   
                        newProjectWindow.twSubjects.setItem(newProjectWindow.twSubjects.rowCount() - 1, i ,item)

                newProjectWindow.twSubjects.setSortingEnabled(False)

                newProjectWindow.twSubjects.resizeColumnsToContents()


            ### load observation in project window
            newProjectWindow.twObservations.setRowCount(0)
            if self.pj['observations']:

                for obs in sorted( self.pj['observations'].keys() ):

                    if self.DEBUG: print 'observation:', obs

                    newProjectWindow.twObservations.setRowCount(newProjectWindow.twObservations.rowCount() + 1)

                    item = QTableWidgetItem(obs) 
                    newProjectWindow.twObservations.setItem(newProjectWindow.twObservations.rowCount() - 1, 0, item)

                    item = QTableWidgetItem( self.pj['observations'][obs]['date'].replace('T',' ') ) 
                    newProjectWindow.twObservations.setItem(newProjectWindow.twObservations.rowCount() - 1, 1, item)

                    item = QTableWidgetItem( self.pj['observations'][obs]['description'] ) 
                    newProjectWindow.twObservations.setItem(newProjectWindow.twObservations.rowCount() - 1, 2, item)

                    ### FIXME
                    mediaList = []
                    if self.pj['observations'][obs]['type'] in [MEDIA]:
                        for idx in self.pj['observations'][obs]['file']:
                            for media in self.pj['observations'][obs]['file'][idx]:
                                mediaList.append('#%s: %s' % (idx , media))

                    elif self.pj['observations'][obs]['type'] in [LIVE]:
                        mediaList = [LIVE]
                    

                    item = QTableWidgetItem('\n'.join( mediaList )) 
                    newProjectWindow.twObservations.setItem(newProjectWindow.twObservations.rowCount() - 1, 3, item)

                newProjectWindow.twObservations.resizeColumnsToContents()



            ### configuration of behaviours
            if self.pj['behaviors_conf']:

                for i in sorted( self.pj['behaviors_conf'].keys() ):
                    newProjectWindow.twBehaviors.setRowCount(newProjectWindow.twBehaviors.rowCount() + 1)

                    for field in self.pj['behaviors_conf'][i]:

                        item = QTableWidgetItem()

                        if field == 'type':

                            comboBox = QComboBox()
                            for observation in observation_types:
                                comboBox.addItem(observation)
                            comboBox.setCurrentIndex( observation_types.index(self.pj['behaviors_conf'][i][field]) )

                            newProjectWindow.twBehaviors.setCellWidget(newProjectWindow.twBehaviors.rowCount() - 1, 0, comboBox)

                        else:
                            item.setText( self.pj['behaviors_conf'][i][field] )

                            if field == 'excluded':
                                item.setFlags(Qt.ItemIsEnabled)

                            newProjectWindow.twBehaviors.setItem(newProjectWindow.twBehaviors.rowCount() - 1, fields[field] ,item)

                newProjectWindow.twBehaviors.resizeColumnsToContents()

            ### load independent variables 
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
        
        ### pass copy of self.pj
        newProjectWindow.pj = dict(self.pj)

        ##################################################################################################################################
        ##################################################################################################################################

        if newProjectWindow.exec_():  #button OK

            self.pj = dict( newProjectWindow.pj )

            if mode == 'new':
                self.projectFileName = ''
                self.pj = {"time_format": "hh:mm:ss",\
                "project_date": "",\
                "project_name": "",\
                "project_description": "",\
                "subjects_conf" : {},\
                "behaviors_conf": {},\
                "observations": {} }

            self.project = True

            self.pj["project_name"] = newProjectWindow.leProjectName.text()
            self.pj["project_date"] = newProjectWindow.dteDate.dateTime().toString(Qt.ISODate)
            self.pj["project_description"] = newProjectWindow.teDescription.toPlainText()

            ### time format
            if newProjectWindow.rbSeconds.isChecked():
                self.timeFormat = S

            if newProjectWindow.rbHMS.isChecked():
                self.timeFormat = HHMMSS

            self.pj["time_format"] = self.timeFormat


            ### configuration
            if newProjectWindow.lbObservationsState.text() != '':
                QMessageBox.warning(self, programName, newProjectWindow.lbObservationsState.text())
            else:

                if self.DEBUG: print 'behaviors config', newProjectWindow.obs

                self.twConfiguration.setRowCount(0)

                self.pj['behaviors_conf'] =  newProjectWindow.obs
                if self.DEBUG: print 'behaviours configuration', self.pj['behaviors_conf']

                self.load_obs_in_lwConfiguration()

                self.pj['subjects_conf'] =  newProjectWindow.subjects_conf

                if self.DEBUG: print 'subjects', self.pj['subjects_conf']

                self.load_subjects_in_twSubjects()
                
                ### load variables
                self.pj[ INDEPENDENT_VARIABLES ] =  newProjectWindow.indVar

                if self.DEBUG: print INDEPENDENT_VARIABLES, self.pj[INDEPENDENT_VARIABLES]

            ### observations (check if observation deleted)
            self.toolBar.setEnabled(True)

            self.initialize_new_project()
            self.menu_options()


    def new_project_activated(self):

        if self.DEBUG: print 'new project'
        self.edit_project('new')


    def save_project_json(self, projectFileName):
        '''
        save project to JSON file
        '''

        if self.DEBUG: print 'save project json projectFileName:',  projectFileName

        #self.sort_events()
        
        self.pj['project_format_version'] = project_format_version
        
        s = json.dumps(self.pj, indent=4)

        f = open(projectFileName, 'w')

        f.write(s)
        f.close()

        self.projectChanged = False



    def save_project_as_activated(self):
        '''save current project asking for a new file name'''

        if self.DEBUG: print 'save project as function'
        fd = QFileDialog(self)
        self.projectFileName, filtr = fd.getSaveFileName(self, 'Save project as', os.path.dirname(self.projectFileName), 'Projects file (*.boris);;All files (*)')

        if not self.projectFileName:
            return 'Not saved'

        ### add .boris if filter = 'Projects file (*.boris)'
        if  filtr == 'Projects file (*.boris)' and os.path.splitext(self.projectFileName)[1] != '.boris':
            self.projectFileName += '.boris'

        self.save_project_json(self.projectFileName)



    def save_project_activated(self):
        '''save current project'''

        print 'self.projectFileName', self.projectFileName

        if self.DEBUG: print 'save project function'
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

            ### add .boris if filter = 'Projects file (*.boris)'
            if  filtr == 'Projects file (*.boris)' and os.path.splitext(self.projectFileName)[1] != '.boris':
                self.projectFileName += '.boris'

            self.save_project_json(self.projectFileName)

        else:
            self.save_project_json(self.projectFileName)

        return ''


    def liveTimer_out(self):

        currentTime = self.getLaps()

        t = self.seconds2time(currentTime)

        self.lbTimeLive.setText(t)

        ### current state(s)

        ### extract State events
        StateBehaviorsCodes = [ self.pj['behaviors_conf'][x]['code'] for x in [y for y in self.pj['behaviors_conf'] if 'State' in self.pj['behaviors_conf'][y]['type']] ]

        self.currentStates = {}
        
        ### add states for no focal subject
        self.currentStates[ '' ] = []
        for sbc in StateBehaviorsCodes:
            if len(  [ x[ pj_obs_fields['code'] ] for x in self.pj['observations'][self.observationId]['events' ] if x[ pj_obs_fields['subject'] ] == '' and x[ pj_obs_fields['code'] ] == sbc and x[ pj_obs_fields['time'] ] <= currentTime  ] ) % 2: ### test if odd
                self.currentStates[''].append(sbc)

        ### add states for all configured subjects
        for idx in self.pj['subjects_conf']:

            ### add subject index
            self.currentStates[ idx ] = []
            for sbc in StateBehaviorsCodes:
                if len(  [ x[ pj_obs_fields['code'] ] for x in self.pj['observations'][self.observationId]['events' ] if x[ pj_obs_fields['subject'] ] == self.pj['subjects_conf'][idx]['name'] and x[ pj_obs_fields['code'] ] == sbc and x[ pj_obs_fields['time'] ] <= currentTime  ] ) % 2: ### test if odd
                    self.currentStates[idx].append(sbc)

        if self.currentStates[ '' ]:
            self.lbState.setText('Current state(s): <b>' + '</b> ,<b> '.join(self.currentStates[ '' ]) + '</b>' )

        else:
            self.lbState.clear()


        ### show current states
        if self.currentSubject:
            ### get index of focal subject (by name)
            idx = [idx for idx in self.pj['subjects_conf'] if self.pj['subjects_conf'][idx]['name'] == self.currentSubject][0]
            self.lbCurrentStates.setText(  '%s' % (', '.join(self.currentStates[ idx ]))) 
        else:
            self.lbCurrentStates.setText(  '%s' % (', '.join(self.currentStates[ '' ]))) 

        ### show selected subjects
        for idx in sorted( self.pj['subjects_conf'].keys() ):

            self.twSubjects.item(int(idx), 2 ).setText( ','.join(self.currentStates[idx]) )



    def start_live_observation(self):
        '''
        activate the live observation mode (without media file)
        '''

        if self.DEBUG: print 'start live observation, self.liveObservationStarted:', self.liveObservationStarted

        if not self.liveObservationStarted:

            if self.twEvents.rowCount():
                response = dialog.MessageDialog(programName, 'The current events will be deleted. Do you want to continue?', ['Yes', 'No'])
                if response == 'No':
                    return

                self.twEvents.setRowCount(0)
                
                self.pj['observations'][self.observationId]['events'] = []
                self.projectChanged = True
                #self.loadEventsInTW(self.observationId)


                
            self.liveObservationStarted = True
            self.textButton.setText('Stop live observation')
    
            self.liveStartTime = QTime()
            ### set to now
            self.liveStartTime.start()

            ### start timer
            self.liveTimer.start(100)

        else:

            self.liveObservationStarted = False
            self.textButton.setText('Start live observation')
    
            self.liveStartTime = None
            self.liveTimer.stop()
            
            self.lbTimeLive.setText('00:00:00.000')
            


    def media_file_info(self):
        '''
        show info about current video
        '''
        if self.observationId:
            
            out = ''
            import platform
            if platform.system() in ['Linux', 'Darwin']:
                import commands

                for f in self.pj['observations'][self.observationId]['file']:

                    if self.DEBUG: print 'file:', f

                    r = os.system( 'file -b ' + f )

                    if not r:
                        out += '<b>'+os.path.basename(f) + '</b><br>'
                        out += commands.getoutput('file -b ' + f ) + '<br>'

            if self.pj['observations'][self.observationId]['type'] in [MEDIA]:
                QMessageBox.about(self, programName + ' - Media file information', out + '<br><br>Total duration: %s s<br>Video: %s<br>Is seekable: %s' \
                % (self.convertTime(self.mediaplayer.get_length()/1000), str(self.player.hasVideo()), str(self.player.isSeekable()) ) )



                media = player.get_media()
                print('State: %s' % self.mediaplayer.get_state())
                print('Media: %s' % bytes_to_str(media.get_mrl()))
                print('Track: %s/%s' % (self.mediaplayer.video_get_track(), player.video_get_track_count()))
                print('Current time: %s/%s' % (self.mediaplayer.get_time(), media.get_duration()))
                print('Position: %s' % self.mediaplayer.get_position())
                print('FPS: %s (%d ms)' % (self.mediaplayer.get_fps(), mspf()))
                print('Rate: %s' % self.mediaplayer.get_rate())
                print('Video size: %s' % str(self.mediaplayer.video_get_size(0)))  # num=0
                print('Scale: %s' % self.mediaplayer.video_get_scale())
                print('Aspect ratio: %s' % self.mediaplayer.video_get_aspect_ratio())




        else:
            self.no_observation()




    def video_faster_activated(self):
        '''
        increase playing speed
        '''
        if self.playerType == VLC:
            if self.play_rate < 8:
                self.play_rate += 0.1
                self.mediaplayer.set_rate(self.play_rate)
                
                if self.media_list2.count():
                    self.mediaplayer2.set_rate(self.play_rate)
                
                self.lbSpeed.setText('x' + str(self.play_rate))
    
            if self.DEBUG: print 'play rate:', self.play_rate

        if self.playerType == OPENCV:

            if self.openCVtimer.interval() > 0:
                self.openCVtimer.setInterval( self.openCVtimer.interval() - 2 )
            self.lbSpeed.setText('x%.3f' %  (1/self.openCVtimer.interval()/ (self.cap.get(cv2.cv.CV_CAP_PROP_FPS)/1000)))



    def video_slower_activated(self):
        '''
        decrease playing speed
        '''

        if self.playerType == VLC:
            if self.play_rate > 0.2:
                self.play_rate -= 0.1
                self.mediaplayer.set_rate(self.play_rate)
    
                if self.media_list2.count():
                    self.mediaplayer2.set_rate(self.play_rate)
    
                self.lbSpeed.setText('x' + str(self.play_rate))
    
            if self.DEBUG: print 'play rate:',self.play_rate

        if self.playerType == OPENCV:
            if self.openCVtimer.interval() < 10000:
                self.openCVtimer.setInterval( self.openCVtimer.interval() + 2 )
            self.lbSpeed.setText('x%.3f' %  (1/self.openCVtimer.interval()/ (self.cap.get(cv2.cv.CV_CAP_PROP_FPS)/1000)))



    def add_event(self):
        '''
        manually add event to observation
        '''
        if self.DEBUG: print 'manually add new event'

        if not self.observationId:
            self.no_observation()
            return

        editWindow = DlgEditEvent(self.DEBUG)
        editWindow.setWindowTitle('Add a new event')

        ### send pj to edit_event window
        editWindow.pj = self.pj

        if self.timeFormat == HHMMSS:
            editWindow.dsbTime.setVisible(False)

        if self.timeFormat == S:
            editWindow.teTime.setVisible(False)


        sortedSubjects = [''] + sorted( [ self.pj['subjects_conf'][x]['name'] for x in self.pj['subjects_conf'] ])

        editWindow.cobSubject.addItems( sortedSubjects )

        
        sortedCodes = sorted( [ self.pj['behaviors_conf'][x]['code'] for x in self.pj['behaviors_conf'] ])

        editWindow.cobCode.addItems( sortedCodes )


        if editWindow.exec_():  #button OK


            if self.timeFormat == HHMMSS:
                newTime = self.time2seconds(editWindow.teTime.time().toString('hh:mm:ss.zzz'))

            if self.timeFormat == S:
                newTime = editWindow.dsbTime.value()

            memTime = newTime

            new_event = { 'time': newTime, \
            'subject': editWindow.cobSubject.currentText(), \
            'code': editWindow.cobCode.currentText() ,\
            'type': '',\
            'modifier': editWindow.cobModifier.currentText(),\
            'comment': editWindow.leComment.toPlainText() }

            
            self.pj['observations'][self.observationId]['events'].append( [ newTime, editWindow.cobSubject.currentText(),  editWindow.cobCode.currentText() , editWindow.cobModifier.currentText(), editWindow.leComment.toPlainText()]  )
            
            self.pj['observations'][self.observationId]['events'].sort()
            
            self.loadEventsInTW( self.observationId )
            
            

            if self.DEBUG: print 'EVENTS:', self.pj['observations'][self.observationId]['events']

            ### get item from twEvents at memTime row position
            item = self.twEvents.item(  [i for i,t in enumerate( self.pj['observations'][self.observationId]['events'] ) if t[0] == memTime][0], 0  )

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

            editWindow.pj = self.pj 

            row = self.twEvents.selectedItems()[0].row()   ### first selected event

            if self.DEBUG: print 'row to edit:', row
            if self.DEBUG: print 'self.pj[observations][events][row]', self.pj['observations'][self.observationId]['events'][row]


            if self.timeFormat == HHMMSS:
                editWindow.dsbTime.setVisible(False)

                time = QTime()
                h,m,s = self.seconds2time( self.pj['observations'][self.observationId]['events'][row][ 0 ] ).split(':')
                s, ms = s.split('.')
                time.setHMS(int(h),int(m),int(s),int(ms))
                editWindow.teTime.setTime( time )

            if self.timeFormat == S:
                editWindow.teTime.setVisible(False)

                editWindow.dsbTime.setValue( self.pj['observations'][self.observationId]['events'][row][ 0 ] )


            sortedSubjects = [''] + sorted( [ self.pj['subjects_conf'][x]['name'] for x in self.pj['subjects_conf'] ])
            
            editWindow.cobSubject.addItems( sortedSubjects )
            
            if self.pj['observations'][self.observationId]['events'][row][ 1 ] in sortedSubjects:
                editWindow.cobSubject.setCurrentIndex( sortedSubjects.index( self.pj['observations'][self.observationId]['events'][row][ 1 ] ) )
            else:
                QMessageBox.warning(self, programName, 'The subject <b>%s</b> do not exists more in the subject\'s list' %   self.pj['observations'][self.observationId]['events'][row][ 1 ]  )
                editWindow.cobSubject.setCurrentIndex( 0 )


            sortedCodes = sorted( [ self.pj['behaviors_conf'][x]['code'] for x in self.pj['behaviors_conf'] ])

            editWindow.cobCode.addItems( sortedCodes )

            ### check if selected code is in code's list (no modification of codes)
            if self.pj['observations'][self.observationId]['events'][row][ 2 ] in sortedCodes:
                editWindow.cobCode.setCurrentIndex( sortedCodes.index( self.pj['observations'][self.observationId]['events'][row][ 2 ] ) )
            else:
                QMessageBox.warning(self, programName, 'The code <b>%s</b> do not exists more in the code\'s list' % self.pj['observations'][self.observationId]['events'][row][ 2 ])
                editWindow.cobCode.setCurrentIndex( 0 )

            '''editWindow.leModifier.setText( self.twEvents.item(row, tw_obs_fields['modifier']).text())'''

            ### comment
            editWindow.leComment.setPlainText( self.pj['observations'][self.observationId]['events'][row][ 4 ])

            ### load modifiers
            editWindow.codeChanged()

            ### extract modifers for current code

            modif = [ self.pj['behaviors_conf'][x]['modifiers'] for x in self.pj['behaviors_conf'] if self.pj['behaviors_conf'][x]['code'] ==  self.pj['observations'][self.observationId]['events'][row][ 2 ] ]
            if modif:
                editWindow.cobModifier.setCurrentIndex( ([''] + modif[0].split(',')).index( self.pj['observations'][self.observationId]['events'][row][ 3 ] ) )
            else:
                editWindow.cobModifier.setCurrentIndex( 0 )

            if editWindow.exec_():  #button OK
            
                self.projectChanged = True

                if self.timeFormat == HHMMSS:
                    newTime = self.time2seconds(editWindow.teTime.time().toString('hh:mm:ss.zzz'))

                if self.timeFormat == S:
                    newTime = editWindow.dsbTime.value()

                self.pj['observations'][self.observationId]['events'][row] = [newTime, editWindow.cobSubject.currentText(), editWindow.cobCode.currentText(), editWindow.cobModifier.currentText() ,editWindow.leComment.toPlainText()]
                self.pj['observations'][self.observationId]['events'].sort()
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
                
                if self.DEBUG: print 'obs_idx', obs_idx
            
                if self.DEBUG: print 'behavior code',  code
                if self.DEBUG: print 'behavior', self.pj['behaviors_conf'] [ [ x for x in self.pj['behaviors_conf'] if self.pj['behaviors_conf'][x]['code'] == code][0] ]

                self.writeEvent(  self.pj['behaviors_conf'] [ [ x for x in self.pj['behaviors_conf'] if self.pj['behaviors_conf'][x]['code'] == code][0] ], self.getLaps())
        else: 
            self.no_observation()

    def actionAbout_activated(self):
        '''
        about window
        '''
        import platform

        players = []
        if VLC in self.availablePlayers:
            players.append( "VLC media player v. %s" % bytes_to_str(vlc.libvlc_get_version()))
        if OPENCV in self.availablePlayers:
            players.append('OpenCV 2')


        QMessageBox.about(self, "About " + programName,
        """<b>%s</b> v. %s
        <p>Copyright &copy; 2012-2014 Olivier Friard - Universit&agrave; degli Studi di Torino.<br>
        <br>
        The author would like to acknowledge Sergio Castellano, Marco Gamba, Valentina Matteucci and Laura Ozella for their precious help.<br>
        <br>
        See <a href="http://penelope.unito.it/boris">penelope.unito.it/boris</a> for more details.<br>
        <p>Python %s - Qt %s - PySide %s on %s<br><br>
        Available player(s):<br>%s""" % \
        (programName, __version__, platform.python_version(), PySide.QtCore.__version__, PySide.__version__, platform.system(), '<br>'.join(players)))



    def hsVideo_sliderMoved(self):

        '''
        media position slider moved
        adjust media position
        '''

        if self.pj['observations'][self.observationId]['type'] in [MEDIA]:

            sliderPos = self.hsVideo.value() / (slider_maximum - 1)

            if self.playerType == VLC:
                videoPosition = sliderPos * self.mediaplayer.get_length()
    
                if self.DEBUG: print 'video position', videoPosition
    
                self.mediaplayer.set_time( int(videoPosition) )
    
                if self.media_list2.count():
                    if videoPosition <= self.mediaplayer2.get_length():
                        self.mediaplayer2.set_time( int(videoPosition) )
                    else:
                        self.mediaplayer2.set_time( self.mediaplayer2.get_length() )

            if self.playerType == OPENCV:

                self.cap.set(cv2.cv.CV_CAP_PROP_POS_FRAMES,  sliderPos * self.mediaTotalLength * self.cap.get(cv2.cv.CV_CAP_PROP_FPS) )


    def timer_out(self):
        '''
        indicate the video current position and total length for VLC player
        '''

        if self.pj['observations'][self.observationId]['type'] in [MEDIA]:

            currentTime = self.mediaplayer.get_time()

            ### get cumulative current time
            '''
            if self.DEBUG:
                print 'media list count', self.media_list.count()
                
                print 'self.mediaplayer',self.mediaplayer
                print 'self.mediaplayer.get_media()',self.mediaplayer.get_media()
                
                print 'self.media_list.index_of_item(self.mediaplayer.get_media())', self.media_list.index_of_item(self.mediaplayer.get_media())
                
                print self.duration[0 : self.media_list.index_of_item(self.mediaplayer.get_media()) ]
            '''
            
            globalCurrentTime = (sum(self.duration[0 : self.media_list.index_of_item(self.mediaplayer.get_media()) ]) + self.mediaplayer.get_time())

            totalGlobalTime = sum(self.duration)

            if self.mediaplayer.get_length():

                self.mediaTotalLength = self.mediaplayer.get_length() / 1000

                ### current state(s)

                ### extract State events
                StateBehaviorsCodes = [ self.pj['behaviors_conf'][x]['code'] for x in [y for y in self.pj['behaviors_conf'] if 'State' in self.pj['behaviors_conf'][y]['type']] ]

                self.currentStates = {}
                
                ### add states for no focal subject
                self.currentStates[ '' ] = []
                for sbc in StateBehaviorsCodes:
                    if len(  [ x[ pj_obs_fields['code'] ] for x in self.pj['observations'][self.observationId]['events' ] if x[ pj_obs_fields['subject'] ] == '' and x[ pj_obs_fields['code'] ] == sbc and x[ pj_obs_fields['time'] ] <= currentTime / 1000 ] ) % 2: ### test if odd
                        self.currentStates[''].append(sbc)

                ### add states for all configured subjects
                for idx in self.pj['subjects_conf']:

                    ### add subject index
                    self.currentStates[ idx ] = []
                    for sbc in StateBehaviorsCodes:
                        if len(  [ x[ pj_obs_fields['code'] ] for x in self.pj['observations'][self.observationId]['events' ] if x[ pj_obs_fields['subject'] ] == self.pj['subjects_conf'][idx]['name'] and x[ pj_obs_fields['code'] ] == sbc and x[ pj_obs_fields['time'] ] <= currentTime / 1000 ] ) % 2: ### test if odd
                            self.currentStates[idx].append(sbc)

                if self.currentStates[ '' ]:
                    self.lbState.setText('Current state(s): <b>' + '</b> ,<b> '.join(self.currentStates[ '' ]) + '</b>' )

                else:
                    self.lbState.clear()


                ### show current states
                if self.currentSubject:
                    ### get index of focal subject (by name)
                    idx = [idx for idx in self.pj['subjects_conf'] if self.pj['subjects_conf'][idx]['name'] == self.currentSubject][0]
                    self.lbCurrentStates.setText(  '%s' % (', '.join(self.currentStates[ idx ]))) 
                else:
                    self.lbCurrentStates.setText(  '%s' % (', '.join(self.currentStates[ '' ]))) 

                ### show selected subjects
                for idx in sorted( self.pj['subjects_conf'].keys() ):

                    self.twSubjects.item(int(idx), 2 ).setText( ','.join(self.currentStates[idx]) )

                msg = ''

                if self.mediaListPlayer.get_state() == vlc.State.Playing or self.mediaListPlayer.get_state() == vlc.State.Paused:
                    msg = '%s: <b>%s / %s</b>' % ( self.mediaplayer.get_media().get_meta(0), self.convertTime(self.mediaplayer.get_time() / 1000), self.convertTime(self.mediaplayer.get_length() / 1000) )

                    if self.media_list.count() > 1:
                        msg += ' | total: <b>%s / %s</b>' % ( (self.convertTime( globalCurrentTime/1000 + self.timeOffset), self.convertTime( totalGlobalTime / 1000) ) )

                    if self.mediaListPlayer.get_state() == vlc.State.Paused:
                        msg += ' (paused)'

                if msg:

                    ### show time on status bar
                    self.lbTime.setText( msg )

                    ### set video scroll bar
                    self.hsVideo.setValue( currentTime / self.mediaplayer.get_length() * (slider_maximum - 1))

            else:

                self.statusbar.showMessage('Media length not available now', 0)



    def load_obs_in_lwConfiguration(self):
        '''
        fill behaviors configuration table widget with behaviors from pj
        '''
        
        if self.DEBUG: print 'load behaviors conf',self.pj['behaviors_conf']

        self.twConfiguration.setRowCount(0)

        if self.pj['behaviors_conf']:

            for idx in sorted(self.pj['behaviors_conf'].keys()):

                if self.DEBUG: print 'conf', idx

                self.twConfiguration.setRowCount(self.twConfiguration.rowCount() + 1)
                
                for col, field in enumerate(['key','code','type','description','modifiers','excluded']):
                    self.twConfiguration.setItem(self.twConfiguration.rowCount() - 1, col , QTableWidgetItem( self.pj['behaviors_conf'][idx][field] ))
                

    def load_subjects_in_twSubjects(self):
        '''
        fill subjects table widget with subjects from self.subjects_conf
        '''
        
        if self.DEBUG: print 'load subjects conf',self.pj['subjects_conf']
        
        self.twSubjects.setRowCount(0)
        
        for idx in sorted( self.pj['subjects_conf'].keys() ):

            if self.DEBUG: print 'row', idx

            self.twSubjects.setRowCount(self.twSubjects.rowCount() + 1)
                
            for i,field in enumerate(['key','name']): ### key, subject name
                self.twSubjects.setItem(self.twSubjects.rowCount() - 1, i , QTableWidgetItem( self.pj['subjects_conf'][ idx ][field] ))

            ### add cell for current state(s)
            self.twSubjects.setItem(self.twSubjects.rowCount() - 1, 2 , QTableWidgetItem( '' ))



    def update_events_start_stop(self):
        '''
        update status start/stop of events
        take consideration of subject
        '''
        
        if self.DEBUG: print '\nupdate events for start/stop'
        
        for row in range(0, self.twEvents.rowCount()):

            event = []
            t = self.twEvents.item(row, tw_obs_fields['time'] ).text()

            if ':' in t:
                time = float(self.time2seconds(t))
            else:
                time = float(t)
            
            if self.DEBUG: print 'update events start/stop  time:', time
            
            code = self.twEvents.item(row, tw_obs_fields['code'] ).text()
            subject = self.twEvents.item(row, tw_obs_fields['subject'] ).text()
            
            ### check if code is state
            if code in [ self.pj['behaviors_conf'][x]['code'] for x in self.pj['behaviors_conf'] if 'STATE' in self.pj['behaviors_conf'][x]['type'].upper() ]:

                ### how many code before with same subject?

                if len(  [ x[ pj_obs_fields['code'] ] for x in self.pj['observations'][self.observationId]['events' ] if x[ pj_obs_fields['code'] ] == code and x[ pj_obs_fields['time'] ]  < time and x[ pj_obs_fields['subject'] ] == subject]) % 2: ### test if odd

                    self.twEvents.item(row, tw_obs_fields['type'] ).setText('STOP')
                else:
                    self.twEvents.item(row, tw_obs_fields['type'] ).setText('START')


    def writeEvent(self, event, memTime):
        '''
        add event from pressed key to observation
        '''

        if self.DEBUG: print 'add event to observation id:', self.observationId
        
        ### check if a same event is already in events list
        event_list = [ memTime, self.currentSubject, event['code'] ]
        if event_list in [[x[0],x[1],x[2]] for x in self.pj['observations'][self.observationId]['events']]:
            QMessageBox.warning(self, programName, 'The same event already exists!')
            return None

        ### check if event has modifiers
        modifier_str = ''

        if event['modifiers']:
            
            if self.pj['observations'][self.observationId]['type'] in [MEDIA]:

                if self.playerType == VLC:
                    memState = self.mediaListPlayer.get_state()
                    if memState == vlc.State.Playing:
                        self.pause_video()

                if self.playerType == OPENCV:
                    memState = self.openCVtimerOut.isActive()
                    if memState:
                        self.pause_video()


            response = ''
            items =  [''] + [s.strip() for s in event['modifiers'].split(',')]

            item, ok = QInputDialog.getItem(self, 'Choose the modifier', 'Modifiers for ' + event['code'], items, 0, False)

            if ok and item:
                modifier_str = item


            if self.pj['observations'][self.observationId]['type'] in [MEDIA]:

                if self.DEBUG: print 'media state:', memState

                if self.playerType == VLC:
                    if memState == vlc.State.Playing:
                        self.play_video()

                if self.playerType == OPENCV:
                    if memState:
                        self.play_video()

            if self.DEBUG: print 'modifier', modifier_str


        ### update current state

        if 'STATE' in event['type'].upper():


            if self.DEBUG: print 'current subject:', self.currentSubject

            if self.currentSubject:
                csj = []
                for idx in self.currentStates:
                    if idx in self.pj['subjects_conf'] and self.pj['subjects_conf'][idx]['name'] == self.currentSubject:
                        csj = self.currentStates[idx]
                        break
            else:  ### no focal subject
                if self.DEBUG: print 'self.currentStates', self.currentStates
                csj = self.currentStates['']

            if self.DEBUG: print 'current states:',csj
            if self.DEBUG: print 'event code', event['code'], event['modifiers']


            '''
            if (event['code'] in csj and modifier_str):

                 ### STOP current state event/modifier if same event with different modifier
                column = 0
                self.twEvents.setRowCount(self.twEvents.rowCount() + 1)

                for field in [  self.convertTime( memTime - 0.1 ) , self.currentSubject, event['code'], '', modifier_str, '' ]:
                
                    if self.DEBUG: print self.twEvents.rowCount() - 1, column, field
                
                    item = QTableWidgetItem(field)
                    self.twEvents.setItem(self.twEvents.rowCount() - 1, column ,item)
                    column += 1
            '''




            if event['excluded']:
                ### states to remove from current states

                ### extract current states for current subject
                

                for cs in csj :
                    if cs in event['excluded'].split(','):

                        ### add excluded state event to observations (= STOP them)
                        
                        self.pj['observations'][self.observationId]['events'].append( [memTime - 0.1, self.currentSubject, cs, '', ''] )
                        '''
                        column = 0
                        self.twEvents.setRowCount(self.twEvents.rowCount() + 1)
                
                        for field in [  self.convertTime( memTime - 0.1 ) , self.currentSubject, cs, '','', '' ]:
                
                            if self.DEBUG: print self.twEvents.rowCount() - 1, column, field
                
                            item = QTableWidgetItem(field)
                            self.twEvents.setItem(self.twEvents.rowCount() - 1, column ,item)
                            column += 1
                        '''


        ### add event to pj
        self.pj['observations'][self.observationId]['events'].append( [memTime, self.currentSubject, event['code'], modifier_str, ''] )

        ### sort events in pj
        self.pj['observations'][self.observationId]['events'].sort()

        self.twEvents.setRowCount(0)
        for o in self.pj['observations'][self.observationId]['events']:

            self.twEvents.setRowCount(self.twEvents.rowCount() + 1)

            ### time
            item = QTableWidgetItem( self.convertTime(o[ 0] ) )
            self.twEvents.setItem(self.twEvents.rowCount() - 1, 0, item)
            ### subject
            item = QTableWidgetItem( o[ 1]  )
            self.twEvents.setItem(self.twEvents.rowCount() - 1, 1, item)
            ### code
            item = QTableWidgetItem( o[ 2]  )
            self.twEvents.setItem(self.twEvents.rowCount() - 1, 2, item)
            
            ### type
            item = QTableWidgetItem( ''  )
            self.twEvents.setItem(self.twEvents.rowCount() - 1, 3, item)

            ### modifier
            item = QTableWidgetItem( o[ 3]  )
            self.twEvents.setItem(self.twEvents.rowCount() - 1, 4, item)

            ### modifier
            item = QTableWidgetItem( o[ 4]  )
            self.twEvents.setItem(self.twEvents.rowCount() - 1, 5, item)

        self.update_events_start_stop()

        ### get item from twEvents at memTime row position
        print
        print 'memtime', memTime
        print self.pj['observations'][self.observationId]['events'] 
        print  
        print [i for i,t in enumerate( self.pj['observations'][self.observationId]['events'] ) if t[0] == memTime]
        item = self.twEvents.item(  [i for i,t in enumerate( self.pj['observations'][self.observationId]['events'] ) if t[0] == memTime][0], 0  )

        self.twEvents.scrollToItem( item )

       
        self.projectChanged = True


    def fill_lwDetailed(self, obs_key, memLaps):
        '''
        fill listwidget with all events coded by key
        '''

        ### check if key duplicated
        if self.DEBUG: print 'fill_lwDetail function'

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
            if self.DEBUG:print 'selected code:', item

            obs_idx = self.detailedObs[ item ]
            
            self.writeEvent(self.pj['behaviors_conf'][obs_idx], memLaps)


    def getLaps(self):
        '''
        return cumulative laps time from begining of observation

        in seconds (float))
        
        
        add time offset for video observation if any
        '''
        ###  if self.DEBUG: print 'self.observationId', self.observationId
        
        
        if self.pj['observations'][self.observationId]['type'] in [LIVE]:

            if self.liveObservationStarted:
                now = QTime()
                now.start()
                memLaps = self.liveStartTime.msecsTo(now) / 1000
                return round(memLaps, 1)

            else:

                QMessageBox.warning(self, programName, 'The live observation is not started')
                return None



        if self.pj['observations'][self.observationId]['type'] in [MEDIA]:

            ### remove for global time: memLaps = self.mediaplayer.get_time() / 1000 + self.timeOffset
            
            if self.playerType == VLC:
                ### cumulative time
                memLaps = ( sum(self.duration[0 : self.media_list.index_of_item(self.mediaplayer.get_media()) ]) + self.mediaplayer.get_time()) / 1000 + self.timeOffset
                return round(memLaps, 3)

            if self.playerType == OPENCV:
                if self.cap.isOpened():
                    return round(self.cap.get(cv2.cv.CV_CAP_PROP_POS_FRAMES) / self.cap.get(cv2.cv.CV_CAP_PROP_FPS) ,3)

    '''
    def eventFilter(self, widget, event):
        
        if (event.type() == QEvent.KeyPress):
            print 'keypressed' , widget, event.key()
    '''


    def keyPressEvent(self, event):
        
        if self.DEBUG: print 'keyPressEvent function'
        '''
        if (event.modifiers() & Qt.ShiftModifier):
            print 'Shift!'

        print QApplication.keyboardModifiers()
        
        http://qt-project.org/doc/qt-5.0/qtcore/qt.html#Key-enum
        '''

        if not self.observationId:
            return
        
        ### beep
        if self.confirmSound:
            print '\a'

        ### check if media ever played
        if self.playerType == VLC:
            if self.mediaListPlayer.get_state() == vlc.State.NothingSpecial:
                return

            if self.DEBUG:
                print 'player state', self.mediaListPlayer.get_state()

        ek = event.key()

        if self.DEBUG:
            print 'key event:', ek
            if ek in function_keys:
                print 'F key', function_keys[ek]

            

        if ek in [16777248,  16777249, 16777217, 16781571]: ### shift tab ctrl
            return

        ### play / pause with space bar
        if ek == Qt.Key_Space and self.pj['observations'][self.observationId]['type'] in [MEDIA]:   

            if self.DEBUG:
                if self.playerType == VLC:
                    print 'space player #1 state', self.mediaListPlayer.get_state()

            self.pause_video()
            return

        ### jump with arrow keys
        '''
        FIXME
        if ek in [Qt.Key_Left, Qt.Key_Right, Qt.Key_Down, Qt.Key_Up, Qt.Key_PageUp, Qt.Key_PageDown]:

            if ek == Qt.Key_Up or ek == Qt.Key_PageUp :
                self.jumpForward_activated()

            if ek == Qt.Key_Down or ek == Qt.Key_PageDown:
                self.jumpBackward_activated()
            
            if ek == Qt.Key_Left:
                pass
            
            if ek == Qt.Key_Right:
                if self.playerType == OPENCV:
                    self.openCVtimerOut()

            return
        '''
        
        
        if  self.playerType == OPENCV:
            if ek == 47:  ### /   one frame back
                print 'frame', self.cap.get(cv2.cv.CV_CAP_PROP_POS_FRAMES)
                newFrame = self.cap.get(cv2.cv.CV_CAP_PROP_POS_FRAMES) - 2

                newTime = 1000.0 * newFrame / self.cap.get(cv2.cv.CV_CAP_PROP_FPS)

                print 'newFrame', newFrame
                
                self.cap.set(cv2.cv.CV_CAP_PROP_POS_MSEC, newTime);
                
                #self.cap.set(cv2.cv.CV_CAP_PROP_POS_FRAMES, newFrame )

                #self.openCVtimerOut()

                print 'frame', self.cap.get(cv2.cv.CV_CAP_PROP_POS_FRAMES)                

                return
                
            if ek == 42:  ### *  read next frame
                print 'frame', self.cap.get(cv2.cv.CV_CAP_PROP_POS_FRAMES)
                self.openCVtimerOut()
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


        if (ek in function_keys) or ((ek in range(33, 256)) and (ek not in [Qt.Key_Plus, Qt.Key_Minus])):

            memLaps = self.getLaps()
            if memLaps == None:
                return

            obs_idx = -1
            count = 0

            if (ek in function_keys):
                ek_unichr = function_keys[ek]
            else:
                ek_unichr = unichr(ek)

            if self.DEBUG: print 'ek_unichr'  ,ek_unichr

            for o in self.pj['behaviors_conf']:

                if self.pj['behaviors_conf'][o]['key'] == ek_unichr:
                    if self.DEBUG: print 'OK', ek_unichr

                    obs_idx = o
                    count += 1

            ### check if key codes more events
            if count > 1:
                if self.DEBUG: print 'multi code key'

                flagPlayerPlaying = False
                if self.pj['observations'][self.observationId]['type'] in [MEDIA]:
                    
                    if self.playerType == VLC:
                        if self.mediaListPlayer.get_state() != vlc.State.Paused:
                            flagPlayerPlaying = True
                            self.pause_video()

                    if self.playerType == OPENCV:
                        self.pause_video()

                ### let user choose event
                self.fill_lwDetailed( ek_unichr, memLaps)

                if self.pj['observations'][self.observationId]['type'] in [MEDIA] and flagPlayerPlaying:
                    self.play_video()

            elif count == 1:

                self.writeEvent(self.pj['behaviors_conf'][obs_idx], memLaps)

            else:

                ### check if key defines a suject
                flag_subject = False
                for idx in self.pj['subjects_conf']:
                
                    if ek_unichr == self.pj['subjects_conf'][idx]['key']:
                        flag_subject = True
                        if self.DEBUG: print 'subject', ek_unichr , self.pj['subjects_conf'][idx]['name']
                        
                        ### select or deselect current subject
                        if self.currentSubject == self.pj['subjects_conf'][idx]['name']:
                            self.deselectSubject()
                        else:
                            self.selectSubject( self.pj['subjects_conf'][idx]['name'] )
                            '''
                            self.currentSubject = self.pj['subjects_conf'][idx]['name']
                            self.lbSubject.setText( 'Focal subject: <b>%s</b>' % (self.currentSubject))
                            self.lbFocalSubject.setText( ' Focal subject: <b>%s</b>' % (self.currentSubject) )
                            '''

                if not flag_subject:

                    if self.DEBUG: print '%s key not assigned' % ek_unichr
                    
                    self.statusbar.showMessage( 'Key not assigned (%s)' % ek_unichr , 5000)





    def twEvents_doubleClicked(self):
        '''
        seek video to double clicked position ( add self.repositioningTimeOffset value)
        substract time offset if any
        '''
        if self.DEBUG: print 'twEvents_doubleClicked'

        if self.twEvents.selectedIndexes():

            row = self.twEvents.selectedIndexes()[0].row()  
        
            if ':' in self.twEvents.item(row, 0).text():
                time = self.time2seconds(  self.twEvents.item(row, 0).text()  )
            else:
                time  = float( self.twEvents.item(row, 0).text() )

            ### substract time offset
            time -= self.timeOffset

            if time + self.repositioningTimeOffset >= 0:
                newtime = (time + self.repositioningTimeOffset ) * 1000
            else:
                newtime = 0


            ### FIXME
            if self.DEBUG: print 'self.mediaListPlayer.get_state()', self.mediaListPlayer.get_state()

            ### remember if player paused (go previous will start playing)
            flagPaused = self.mediaListPlayer.get_state() == vlc.State.Paused

            if self.DEBUG: print 'newtime', newtime

            if len(self.duration) > 1:
                if self.DEBUG: print 'durations:', self.duration
                tot = 0
                for idx, d in enumerate(self.duration):
                    if newtime >= tot and newtime < d:
                        if self.DEBUG: print 'video index:', idx
                        self.mediaListPlayer.play_item_at_index( idx )
                        if self.DEBUG: print 'newtime - tot:',  int(newtime) - tot
                        self.mediaplayer.set_time( int(newtime) - tot )
                    tot += d

            else:   ### 1 video

                self.mediaplayer.set_time( int(newtime) )
                
                if self.media_list2.count():
                    self.mediaplayer2.set_time( int(newtime) )


            if flagPaused and self.mediaListPlayer.get_state() != vlc.State.Paused:

                if self.DEBUG: print 'new state',self.mediaListPlayer.get_state()
                while self.mediaListPlayer.get_state() != vlc.State.Playing:
                    if self.DEBUG: print 'state (while)',self.mediaListPlayer.get_state()
                    pass

                self.mediaListPlayer.pause()

                if self.media_list2.count():
                    self.mediaListPlayer2.pause()



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
                    self.deselectSubject(self.twSubjects.item(row, 1).text())
        else: 
            self.no_observation()




    def select_events_between_activated(self):
        '''
        select observations between a time interval
        '''

        QMessageBox.warning(self, programName, 'Not available yet!')
        return


        if self.twEvents.rowCount():
            text, ok = QInputDialog.getText(self, 'Select observations from interval', 'Interval: (example: 12.5-14.7)' , QLineEdit.Normal,  '')
            if ok and text != '':
                from_, to_ = [ float(s.strip()) for s in text.split('-')[0:2] ]

                if to_ < from_:
                    QMessageBox.about(self, programName, 'The begin value is greater than the end value!')
                    return


                for r in range(0, self.twEvents.rowCount()):

                    if ':' in self.twEvents.item(r, 0).text():
                        time = self.time2seconds( self.twEvents.item(r, 0).text() )
                    else:
                        time = float(self.twEvents.item(r, 0).text())
                        
                    if time >= from_ and time <= to_:
                        #self.twEvents.setItemSelected(self.twEvents.item(r, 0), True)
                        self.twEvents.selectRow(r)

            
        else:
            QMessageBox.warning(self, programName, 'There are no observations to select!')

        
        '''
        if self.twEvents.selectedItems():
            ask_value = frmAskValue()
            ask_value.setWindowTitle('Select observations between interval')
    
            if ask_value.exec_():  #button OK
                from_ = str(ask_value.leFrom.text()).strip()
                to_ = str(ask_value.leTo.text()).strip()
                if float(to_) < float(from_):
                    QMessageBox.about(self, programName, 'The begin value is greater than the end value!')
                    return
            else:
                return
    
    
            for r in range(0, self.twEvents.rowCount()):
                time = float(self.twEvents.item(r, 0).text())
                if time >= float(from_) and time <= float(to_):
                    self.twEvents.setItemSelected (self.twEvents.item(r, 0), True)
        else:
            QMessageBox.warning(self, programName, 'There are no observations to select!')
        '''

    '''
    def sort_events(self):
        
        sort events chronologically
        and
        update self.pj
        

        if self.DEBUG: print 'sort events'

        if not self.observationId:
            return

        if self.twEvents.rowCount():

            observ_list = []

            for row in range(0, self.twEvents.rowCount()):

                event = []

                for field_type in tw_events_fields:

                    if field_type == 'time':
                        t = self.twEvents.item(row, tw_obs_fields[field_type] ).text()
                        if ':' in t:
                            time = float(self.time2seconds(t))
                        else:
                            time = float(t)
                        event.append(time)

                    else:

                        event.append( self.twEvents.item(row, tw_obs_fields[field_type]).text() )

                observ_list.append(event)

            observ_list.sort()

            if self.DEBUG: print observ_list

            self.twEvents.setRowCount(0)

            for o in observ_list:

                self.twEvents.setRowCount(self.twEvents.rowCount() + 1)
                
                
                for field_type in tw_events_fields:
                    
                    if field_type == 'time':
                        item = QTableWidgetItem( self.convertTime(o[ tw_obs_fields[ field_type ]] ) )
                    else:

                        item = QTableWidgetItem( o[ tw_obs_fields[ field_type ] ] )
                    self.twEvents.setItem(self.twEvents.rowCount() - 1, tw_obs_fields[ field_type ], item)

        ### update pj
        self.update_observations()
        self.update_events_start_stop()
    '''


    def delete_all_events(self):
        '''
        delete all events in current observation
        '''
        
        if not self.observationId:
            self.no_observation()
            return

        response = dialog.MessageDialog(programName, 'Do you really want to delete all events from the current observation?', ['Yes', 'No'])

        if response == 'Yes':
            self.pj['observations'][self.observationId]['events'] = []
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
            
            if self.DEBUG: print [ event for idx,event in enumerate(self.pj['observations'][self.observationId]['events']) if not idx in rows]
            
            self.pj['observations'][self.observationId]['events'] = [ event for idx,event in enumerate(self.pj['observations'][self.observationId]['events']) if not idx in rows]

            self.projectChanged = True

            self.loadEventsInTW( self.observationId )




    def export_tabular_events(self):
        '''
        export events from current observation to plain text file
        '''

        if not self.twEvents.rowCount():
            QMessageBox.warning(self, programName, 'There are no events to export!')
        else:
            fd = QFileDialog(self)
            fileName, filtr = fd.getSaveFileName(self,'Export events', '','Events file (*.txt *.tsv);;All files (*)')

            if fileName:
                f = open(fileName, 'w')

                ### media file name
                f.write('#Media file(s):\n')
                if self.pj['observations'][self.observationId]['type'] in [MEDIA]:

                    for idx in self.pj['observations'][self.observationId]['file']:
                        for media in self.pj['observations'][self.observationId]['file'][idx]:
                            f.write('#Player #%s\t%s\n' % (idx, media) )

                f.write('#\n#\n')

                ### write video length
                '''  TO DO: replace with total length if any
                if self.pj['observations'][self.observationId]['type'] == 'MEDIA':
                    f.write('#media total length\t%f\n' % ( self.mediaplayer.get_length() / 1000.0 ))
                '''

                ### write header
                f.write('#%s\n' % ( '\t'.join(  tw_events_fields ) ))

                for r in range(0, self.twEvents.rowCount()):

                    row = []
                    
                    for c in tw_events_fields:
                        if self.twEvents.item(r, tw_obs_fields[c]):
                            if c == 'time' and self.timeFormat == HHMMSS:
                                s = str(self.time2seconds( self.twEvents.item(r, tw_obs_fields[c]).text() ))
                            else:
                                s = self.twEvents.item(r, tw_obs_fields[c]).text()

                            row.append( s )
                        else:
                            row.append('')

                    s = '\t'.join(row) + '\n'
                    s2 = s.encode('UTF-8')

                    f.write(s2)

                f.close()

            else:
                return



    def export_string_events(self):
        '''
        export events from current observation by subject in string format to plain text file
        behaviors are separated by pipe character (|) for use with BSA
        '''

        ### ask user to select observations
        result, selected_observations = self.selectObservations( SELECT )
        
        if not selected_observations:
            return
            
        if self.DEBUG: print 'observations to export:', selected_observations


        fd = QFileDialog(self)
        fileName, filtr = fd.getSaveFileName(self,'Export events as strings', '','Events file (*.txt *.tsv);;All files (*)')

        if fileName:
            f = open(fileName, 'w')


            for obs in selected_observations:

                ### observation id
                f.write('# observation id: %s\n' %  obs )

                ### observation descrition
                f.write('# observation description: %s\n' %  self.pj['observations'][obs]['description'].replace('\n',' ' ) )


                ### media file name
                if self.pj['observations'][obs]['type'] in [MEDIA]:

                    f.write('# Media file name: %s\n\n' % (', '.join(   [ os.path.basename(x) for x in self.pj['observations'][obs]['file']['1']  ]  )  ) )

                if self.pj['observations'][obs]['type'] in [LIVE]:
                    f.write('# Live observation\n\n')


            sortedSubjects = [''] + sorted( [ self.pj['subjects_conf'][x]['name'] for x in self.pj['subjects_conf'] ])

            for subj in sortedSubjects:

                if subj:
                    subj_str = '\nSubject: ' + subj.encode('UTF-8') + '\n'

                else:
                    subj_str = '\nWithout subject:\n'

                f.write(subj_str)

                for obs in selected_observations:
                    s = ''
                    
                    for event in self.pj['observations'][obs]['events']:
                        if event[ pj_obs_fields['subject'] ] == subj:
                            s += event[ pj_obs_fields['code'] ] + self.behaviouralStringsSeparator
    
                        '''
                        ### check if subject
                        if self.twEvents.item(r, tw_obs_fields['subject']).text() == subj:
                            s += self.twEvents.item(r, tw_obs_fields['code']).text() + self.behaviouralStringsSeparator
                        '''
    
                    ### remove last separator (if separator not empty)
                    if self.behaviouralStringsSeparator:
                        s = s[0 : -len(self.behaviouralStringsSeparator)]
    
                    if s:

                        f.write( s.encode('UTF-8') + '\n')

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


    '''
    def update_observations(self):
        
        ### update events in pj
        
        if self.DEBUG: print 'update_observations (events)'

        events = []
        for r in range(0, self.twEvents.rowCount()):

            row = []
            
            for field in pj_events_fields:
                if self.twEvents.item(r, tw_obs_fields[ field ]):

                    if field == 'time':
                        if self.timeFormat == 'hh:mm:ss':
                            s = self.time2seconds( self.twEvents.item(r, tw_obs_fields[ field ] ).text() )
                        else:
                            s = float( self.twEvents.item(r, tw_obs_fields[ field ]).text() )
                    else:
                        s = self.twEvents.item(r, tw_obs_fields[ field ]).text()

                    row.append( s )
                else:
                    row.append('')

            if self.DEBUG: print 'event:', row
            events.append(row)

        self.pj['observations'][self.observationId]['events'] = events
        '''




    def import_observations(self):
        '''
        import events from file
        '''

        self.statusbar.showMessage('Function not yet implemented for OpenCV player', 5000)        

        '''
        FIXME import observations
        
        if not self.observationId:
            self.no_observation()
            return ''

        if self.twEvents.rowCount():

            response = dialog.MessageDialog(programName, 'The observation already contains event(s). Do you want to append events or replace them?', ['Append', 'Replace', 'Cancel'])

            if response == 'Replace':
                self.twEvents.setRowCount(0)

            if response == 'Cancel':
                return

        fd = QFileDialog(self)
        fileName = fd.getOpenFileName(self, 'Import events file', '', 'Text files (*.txt *.tsv);;All files (*)')[0]
        if fileName:
            ### read file and decode it
            f = open(fileName,'r')
            rows_utf8 = f.readlines()
            rows = [ row.decode('utf8') for row in rows_utf8]
            f.close()

            lineRow = 0
            for row in rows:

                lineRow += 1

                if row and '#media total length' in row:
                    self.mediaTotalLength = float(row.split('\t')[1].strip())
                    #self.statusbar.showMessage(str(self.mediaTotalLength), 0)

                if row and row[0] == '#':
                    continue

                if len( row.split('\t') ) != len( tw_events_fields ):
                    QMessageBox.warning(self, programName, 'Error in configuration file at line %d' % lineRow)
                    return

                self.twEvents.setRowCount(self.twEvents.rowCount() + 1)
                column = 0
                for field in row.replace('\n','').split('\t') :

                    item = QTableWidgetItem(field)
                    self.twEvents.setItem(self.twEvents.rowCount() - 1, column ,item)
                    column += 1

            
            self.pj['observations'][self.observationId]['events'].sort()
            self.projectChanged = True
        '''
            



    def play_video(self):
        '''
        play video
        '''

        if self.playerType == VLC:
            if self.DEBUG: print 'self.media_list.count()', self.media_list.count()
            if self.media_list.count():
                self.mediaListPlayer.play()
                if self.DEBUG: print 'player #1 state', self.mediaListPlayer.get_state()
                
                if self.media_list2.count():   ### second video together
                    self.mediaListPlayer2.play()
    
                    if self.DEBUG: print 'player #2 state',  self.mediaListPlayer2.get_state()
            else:
                self.no_media()

        if self.playerType == OPENCV:
            self.openCVtimer.start() 



    def pause_video(self):
        '''
        pause media
        '''

        if self.playerType == VLC:
            if self.media_list.count():
                self.mediaListPlayer.pause()  ### play if paused
                
                if self.DEBUG: print 'player #1 state', self.mediaListPlayer.get_state()
                
                if self.media_list2.count():
                    self.mediaListPlayer2.pause() 
        
                    if self.DEBUG: print 'player #2 state',  self.mediaListPlayer2.get_state()
            else:
                self.no_media()

        if self.playerType == OPENCV:
            if self.openCVtimer.isActive():
                self.openCVtimer.stop()   ### stop
            else:
                self.openCVtimer.start()   ### start



    def play_activated(self):

        if self.observationId and self.pj['observations'][self.observationId]['type'] in [MEDIA]:

            self.play_video()
            


    def jumpBackward_activated(self):
        '''
        rewind from current position 
        '''
        if self.playerType == VLC:
            ''' FIXME work only in current media '''
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

                if self.DEBUG: print newTime
                if self.DEBUG: print sum(self.duration)
                
                ### remember if player paused (go previous will start playing)
                flagPaused = self.mediaListPlayer.get_state() == vlc.State.Paused
                
                if self.DEBUG: print 'flagPaused', flagPaused

                tot = 0
                for idx, d in enumerate(self.duration):
                    if newTime >= tot and newTime < tot+d:
                        self.mediaListPlayer.play_item_at_index(idx)
                        
                        ### wait until media is played    
                        while self.mediaListPlayer.get_state() != vlc.State.Playing:
                            pass
                            
                        if flagPaused:
                            if self.DEBUG: print self.mediaListPlayer.get_state()
                            self.mediaListPlayer.pause()
                        
                        #time.sleep(0.5)
                        print newTime -  sum(self.duration[0 : self.media_list.index_of_item(self.mediaplayer.get_media()) ])
                        self.mediaplayer.set_time( newTime -  sum(self.duration[0 : self.media_list.index_of_item(self.mediaplayer.get_media()) ]))
                        
                        break
                    tot += d

            else:
                self.no_media()

        if self.playerType == OPENCV:
            currentTime = self.cap.get(cv2.cv.CV_CAP_PROP_POS_FRAMES) / self.cap.get(cv2.cv.CV_CAP_PROP_FPS) 

            if self.DEBUG:
                print 'currentTime', currentTime
                print 'new time', currentTime - self.fast 
                print 'new frame', (currentTime - self.fast )  *self.cap.get(cv2.cv.CV_CAP_PROP_FPS)
                print 'total', self.cap.get(7)

            if (currentTime - self.fast )  *self.cap.get(cv2.cv.CV_CAP_PROP_FPS) > 0:
                self.cap.set(cv2.cv.CV_CAP_PROP_POS_FRAMES, (currentTime - self.fast )  *self.cap.get(cv2.cv.CV_CAP_PROP_FPS) )
            else:
                self.cap.set(cv2.cv.CV_CAP_PROP_POS_FRAMES, 0)   #### position to init
            self.openCVtimerOut()


    def jumpForward_activated(self):
        '''
        forward from current position 
        '''

        if self.playerType == VLC:
            ''' FIXME work only in current media '''
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

                if self.DEBUG: print newTime
                if self.DEBUG: print sum(self.duration)
                
                if newTime < sum(self.duration):

                    ### remember if player paused (go previous will start playing)
                    flagPaused = self.mediaListPlayer.get_state() == vlc.State.Paused
                    
                    if self.DEBUG: print 'flagPaused', flagPaused

                    tot = 0
                    for idx, d in enumerate(self.duration):
                        if newTime >= tot and newTime < tot+d:
                            self.mediaListPlayer.play_item_at_index(idx)
                            
                            ### wait until media is played    
                            while self.mediaListPlayer.get_state() != vlc.State.Playing:
                                pass
                                
                            if flagPaused:
                                if self.DEBUG: print self.mediaListPlayer.get_state()
                                self.mediaListPlayer.pause()
                            
                            #time.sleep(0.5)
                            print newTime -  sum(self.duration[0 : self.media_list.index_of_item(self.mediaplayer.get_media()) ])
                            self.mediaplayer.set_time( newTime -  sum(self.duration[0 : self.media_list.index_of_item(self.mediaplayer.get_media()) ]))
                            
                            break
                        tot += d

    
            else:
                self.no_media()
        
        if self.playerType == OPENCV:
            currentTime = self.cap.get(cv2.cv.CV_CAP_PROP_POS_FRAMES) / self.cap.get(cv2.cv.CV_CAP_PROP_FPS) 

            if self.DEBUG: print 'currentTime', currentTime
            if self.DEBUG: print 'new time', currentTime + self.fast 
            if self.DEBUG: print 'new frame', (currentTime + self.fast )  *self.cap.get(cv2.cv.CV_CAP_PROP_FPS)
            if self.DEBUG: print 'total', self.cap.get(7)
            
                        
            if (currentTime + self.fast )  *self.cap.get(cv2.cv.CV_CAP_PROP_FPS) < self.cap.get(7):
                self.cap.set(cv2.cv.CV_CAP_PROP_POS_FRAMES,  (currentTime + self.fast )  *self.cap.get(cv2.cv.CV_CAP_PROP_FPS) )
            else:
                self.cap.set(cv2.cv.CV_CAP_PROP_POS_FRAMES, self.cap.get(7))   #### position to end
            self.openCVtimerOut()




    def reset_activated(self):
        '''
        reset video to beginning
        '''
        if self.DEBUG: print 'Reset'

        self.mediaplayer.pause()
        self.mediaplayer.set_time(0)

        if self.media_list2.count():
            self.mediaplayer2.pause()
            self.mediaplayer2.set_time(0)


    def stopClicked(self):
        
        if self.DEBUG: print 'Stop'
        
        self.mediaplayer.stop()

        if self.media_list2.count():
            self.mediaplayer2.stop()



if __name__=="__main__":
    
    app = QApplication(sys.argv)

    start = time.time() 
    splash = QSplashScreen(QPixmap( os.path.dirname(os.path.realpath(__file__)) + "/splash.png"))
    splash.show()
    splash.raise_()
    while time.time() - start < 1:
        time.sleep(0.001)
        app.processEvents()


    ### check if argument
    from optparse import OptionParser
    usage = "usage: %prog [options]"
    parser = OptionParser(usage=usage)
    
    parser.add_option("-d", "--debug", action = "store_true", default = False, dest = "debug", help = "Verbose mode for debugging")
    #parser.add_option("-o", "--opencv", action = "store_true", default = False, dest = "opencv", help = "Use OpenCV (useful for frame access)")
    
    (options, args) = parser.parse_args()

    availablePlayers = []

    ### load VLC
    try:
        import vlc
        availablePlayers.append(VLC)
    except:
        print 'The VLC media player can not be loaded.'


    ### load OpenCV
    ''' DISABLED FOR NOW
    try:
        import numpy
        import cv2
        from cv2 import cv
        availablePlayers.append(OPENCV)

    except:
        print 'OpenCV can not be loaded.'
    '''

    if not availablePlayers:
        QMessageBox.critical(None, programName, 'This program requires the VLC media player library or the OpenCV Python module and it seems that they are not installed on your system.<br>Go to http://www.videolan.org/vlc to install it', QMessageBox.Ok | QMessageBox.Default, QMessageBox.NoButton)
        sys.exit(1)

    app.setApplicationName(programName)
    window = MainWindow(availablePlayers)

    window.DEBUG = options.debug

    if args:

        print os.path.abspath(args[0])
        window.open_project_json( os.path.abspath(args[0]) )

    window.show()
    window.raise_()
    splash.finish(window)

    sys.exit(app.exec_())
