#!/usr/bin/env python

"""

BORIS
Behavioral Observation Research Interactive Software
Copyright 2012-2015 Olivier Friard


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

from config import *

from PyQt4.QtCore import *
from PyQt4.QtGui import *

from observation_ui import Ui_Form
import os
import vlc
import time
import sys

class Observation(QDialog, Ui_Form):

    def __init__(self, parent=None):

        super(Observation, self).__init__(parent)
        self.setupUi(self)

        self.pbAddVideo.clicked.connect(lambda: self.add_media(PLAYER1))
        self.pbRemoveVideo.clicked.connect(lambda: self.remove_media(PLAYER1))

        self.pbAddVideo_2.clicked.connect(lambda: self.add_media(PLAYER2))
        self.pbRemoveVideo_2.clicked.connect(lambda: self.remove_media(PLAYER2))

        self.pbOK.clicked.connect(self.pbOK_clicked)
        self.pbCancel.clicked.connect( self.reject)
        
        self.mediaDurations = { PLAYER1:[], PLAYER2:[] }

    def pbOK_clicked(self):

        def is_numeric(s):
            try:
                float(s)
                return True
            except ValueError:
                return False

        # check time offset
        if not is_numeric(self.leTimeOffset.text()):
            QMessageBox.warning(self, programName , '<b>%s</b> is not recognized as a valid time offset format' % self.leTimeOffset.text())
            return

        # check if indep variables are correct type
        for row in range(0, self.twIndepVariables.rowCount()):

            if self.twIndepVariables.item(row, 1).text() == NUMERIC:
                if self.twIndepVariables.item(row, 2).text() and not is_numeric( self.twIndepVariables.item(row, 2).text() ):
                    QMessageBox.critical(self, programName , 'The <b>%s</b> variable must be numeric!' %  self.twIndepVariables.item(row, 0).text())
                    return


        # check if observation id not empty
        if not self.leObservationId.text():
            QMessageBox.warning(self, programName , 'The <b>observation id</b> is mandatory and must be unique!' )
            return

        # check if new obs and observation id already present
        if self.mode == 'new':
            if self.leObservationId.text() in self.pj['observations']:
                QMessageBox.critical(self, programName , 'The observation id <b>%s</b> is already used!<br>' %  (self.leObservationId.text())  + self.pj['observations'][self.leObservationId.text()]['description'] + '<br>' + self.pj['observations'][self.leObservationId.text()]['date']  )
                return

        # check if edit obs and id changed
        if self.mode == 'edit' and self.leObservationId.text() != self.mem_obs_id:
            if self.leObservationId.text() in self.pj['observations']:
                QMessageBox.critical(self, programName , 'The observation id <b>%s</b> is already used!<br>' %  (self.leObservationId.text())  + self.pj['observations'][self.leObservationId.text()]['description'] + '<br>' + self.pj['observations'][self.leObservationId.text()]['date']  )
                return

        # check if media list #2 popolated and media list #1 empty
        if self.tabProjectType.currentIndex() == 0 and not self.lwVideo.count():
            QMessageBox.critical(self, programName , 'Add a media file in the first list!' )
            return

        self.accept()


    def add_media(self, nPlayer):
        fd = QFileDialog(self)

        os.chdir( os.path.expanduser("~")  )

        fileName = fd.getOpenFileName(self, 'Add media file', '', 'All files (*)')
        if fileName:

            #media_list = self.instance.media_list_new()
            #media_list.add_media(media)

            # play media a while
            
            mediaplayer = self.instance.media_player_new()
            
            
            
            if sys.platform.startswith("linux"): # for Linux using the X Server
                print( self.videoFrame)
                print( self.videoFrame.winId())
                mediaplayer.set_xwindow(self.videoFrame.winId())

            #mediaListPlayer = self.instance.media_list_player_new()
            #mediaListPlayer.set_media_player(mediaplayer)

            #mediaListPlayer.set_media_list(media_list)


            media = self.instance.media_new( fileName )
            media.parse()
            mediaplayer.set_media( media )

            print( 'before play item' )
            
            #mediaListPlayer.play_item_at_index( 0 )
            mediaplayer.play()
            print( 'after play item' )    
            # play mediaListPlayer for a while to obtain media information
            while True:
                if mediaplayer.get_state() == vlc.State.Playing:
                    break
                if mediaplayer.get_state() == vlc.State.Ended:
                    QMessageBox.critical(self, programName , 'This file do not seem to be a playable media file.')
                    return
                time.sleep(3)                
                print( mediaplayer.get_state()  ) 
    
            mediaplayer.pause()
    
            #app.processEvents()
            #self.mediaplayer.set_time(0)



            if not media.get_duration():
                QMessageBox.critical(self, programName , 'This file do not seem to be a playable media file.')
                return

            self.mediaDurations[nPlayer].append( media.get_duration()/1000 )
            
            if nPlayer == PLAYER1:
                if self.lwVideo.count() and self.lwVideo_2.count():
                    QMessageBox.critical(self, programName , 'It is not yet possible to play a second media when more media are loaded in the first media player' )
                    return False
                self.lwVideo.addItems( [fileName] )

            if nPlayer == PLAYER2:
                if self.lwVideo.count()>1:
                    QMessageBox.critical(self, programName , 'It is not yet possible to play a second media when more media are loaded in the first media player' )
                    return False
                self.lwVideo_2.addItems( [fileName] )



    def remove_media(self, nPlayer):

        if nPlayer == PLAYER1:
            for selectedItem in self.lwVideo.selectedItems():
                print( self.lwVideo.row(selectedItem) )
                print( self.mediaDurations[nPlayer] )
                if self.mediaDurations[nPlayer]:
                    del self.mediaDurations[nPlayer][self.lwVideo.row(selectedItem)]
                self.lwVideo.takeItem(self.lwVideo.row(selectedItem))

        if nPlayer == PLAYER2:
            for selectedItem in self.lwVideo_2.selectedItems():
                if self.mediaDurations[nPlayer]:
                    del self.mediaDurations[nPlayer][self.lwVideo_2.row(selectedItem)]
                self.lwVideo_2.takeItem(self.lwVideo_2.row(selectedItem))

        print( self.mediaDurations )
