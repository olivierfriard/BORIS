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
'''import vlc'''
import time
import sys
import hashlib
import subprocess

from utilities import *
import dialog



def accurate_video_analysis(ffmpeg_bin, fileName):
    '''
    analyse frame rate and length of video with ffmpeg
    '''

    if sys.platform.startswith("win"):
        cmdOutput = 'NUL'
    else:
        cmdOutput = '/dev/null'
    command2 = '"{0}" -i "{1}" -f image2pipe -qscale 31 - > {2}'.format(ffmpeg_bin, fileName, cmdOutput)
    
    p = subprocess.Popen(command2, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True )

    error = p.communicate()[1]
    error= error.decode('utf-8')
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




out = ''
fps = 0

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
        
        '''self.mediaDurations = { PLAYER1:[], PLAYER2:[] }'''
        self.media_file_info = {}
        self.fileName2hash = {}

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
            fileContentMD5 = hashfile( fileName, hashlib.md5())

            # check if md5 checksum already in project_media_file_info dictionary
            if (not 'project_media_file_info' in self.pj) \
               or ('project_media_file_info' in self.pj and not fileContentMD5 in self.pj['project_media_file_info']):
        
                vlc_script = """
import vlc
instance = vlc.Instance()
mediaplayer = instance.media_player_new()
media = instance.media_new('%s')
mediaplayer.set_media(media)
media.parse()
mediaplayer.play()
global out
global fps
out = ''
fps = 0
result = None
while True:
    if mediaplayer.get_state() == vlc.State.Playing:
        break
    if mediaplayer.get_state() == vlc.State.Ended:
        result = 'media error'
        break
    time.sleep(3)                

if result:
    out = result
else:
    out = media.get_duration()
fps = mediaplayer.get_fps()
mediaplayer.stop()
""" % fileName

                exec(vlc_script, globals(), locals())
    
                print ('out',out)
                print('fps',fps)
    
                if out != 'media error':
                    self.media_file_info[ fileContentMD5 ] = {'video_length': int(out) }
                else:
                    QMessageBox.critical(self, programName , 'This file do not seem to be a playable media file.')
                    return
    
                # check FPS
                if fps:
                    self.media_file_info[ fileContentMD5 ]['nframe'] = int(fps * int(out)/1000)
                else:
                    if self.ffmpeg_bin:
                        response = dialog.MessageDialog(programName, 'BORIS is not able to determine the frame rate of the video.\nLaunch accurate video analysis?\nThis analysis may be long (half time of video)', [YES, NO ])
    
                        if response == YES:
                            nframe, videoTime = accurate_video_analysis( self.ffmpeg_bin, fileName )
                            print('videoTime from ffmpeg', videoTime)
                            print('fps from ffmpeg', (videoTime /1000) / nframe)
                            if nframe:
                                self.media_file_info[ fileContentMD5 ]['nframe'] = nframe
                                self.media_file_info[ fileContentMD5 ]['video_length'] = int(videoTime)   # ms
                            else:
                                QMessageBox.critical(self, programName , 'ffmpeg is not able to analyze this file...')
                                self.media_file_info[ fileContentMD5 ]['nframe'] = 0
                        else:
                            self.media_file_info[ fileContentMD5 ]['nframe'] = 0
                    else:
                        self.media_file_info[ fileContentMD5 ]['nframe'] = 0
                    

            if nPlayer == PLAYER1:
                if self.lwVideo.count() and self.lwVideo_2.count():
                    QMessageBox.critical(self, programName , 'It is not yet possible to play a second media when more media are loaded in the first media player' )
                    return False
                self.lwVideo.addItems( [fileName] )
                self.fileName2hash[ fileName ] = fileContentMD5

            if nPlayer == PLAYER2:
                if self.lwVideo.count()>1:
                    QMessageBox.critical(self, programName , 'It is not yet possible to play a second media when more media are loaded in the first media player' )
                    return False
                self.lwVideo_2.addItems( [fileName] )
                self.fileName2hash[ fileName ] = fileContentMD5



    def remove_media(self, nPlayer):

        if nPlayer == PLAYER1:
            for selectedItem in self.lwVideo.selectedItems():
                print( self.lwVideo.row(selectedItem) )
                print( selectedItem.text() )
                self.media_file_info[ self.fileName2hash[ selectedItem.text() ] ]
                del self.fileName2hash[ selectedItem.text() ]

                self.lwVideo.takeItem(self.lwVideo.row(selectedItem))

        if nPlayer == PLAYER2:
            for selectedItem in self.lwVideo_2.selectedItems():

                del self.fileName2hash[ selectedItem.text() ]
                self.media_file_info[ self.fileName2hash[ selectedItem.text() ] ]
                self.lwVideo_2.takeItem(self.lwVideo_2.row(selectedItem))
