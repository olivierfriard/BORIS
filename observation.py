#!/usr/bin/env python3

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

class ThreadSignal(QObject):
    sig = pyqtSignal(int, float, str, str, str)

class Process(QThread):
    '''
    process for accurate video analysis
    '''

    def __init__(self, parent = None):
        QThread.__init__(self, parent)
        self.filePath = ''
        self.ffmpeg_bin = ''
        self.fileContentMD5 = ''
        self.nPlayer = ''
        self.filePath = ''
        self.signal = ThreadSignal()

    def run(self):

        nframe, videoTime = accurate_video_analysis( self.ffmpeg_bin, self.filePath )
        print( 'nframe, videoTime, fileContentMD5, nPlayer', nframe, videoTime, self.fileContentMD5, self.nPlayer )
        self.signal.sig.emit(nframe, videoTime, self.fileContentMD5, self.nPlayer, self.filePath)


out = ''
fps = 0

class Observation(QDialog, Ui_Form):

    def __init__(self, parent=None):

        super(Observation, self).__init__(parent)
        self.setupUi(self)

        self.lbMediaAnalysis.setText('')

        self.pbAddVideo.clicked.connect(lambda: self.add_media(PLAYER1))
        self.pbRemoveVideo.clicked.connect(lambda: self.remove_media(PLAYER1))

        self.pbAddVideo_2.clicked.connect(lambda: self.add_media(PLAYER2))
        self.pbRemoveVideo_2.clicked.connect(lambda: self.remove_media(PLAYER2))

        self.pbOK.clicked.connect(self.pbOK_clicked)
        self.pbCancel.clicked.connect( self.pbCancel_clicked )
        
        self.media_file_info = {}
        self.fileName2hash = {}
        self.availablePlayers = []
        
        self.flagAnalysisRunning = False
        
        self.mediaDurations = {}
        self.mediaFPS = {}


    def widgetEnabled(self, flag):
        self.tabProjectType.setEnabled(flag)
        if not flag:
            self.lbMediaAnalysis.setText('<b>A media analysis is running</b>')
        else:
            self.lbMediaAnalysis.setText('')


    def pbCancel_clicked(self):
        
        if self.flagAnalysisRunning:
            response = dialog.MessageDialog(programName, 'A media analysis is running. Do you want to cancel the new observation?', [YES, NO ])
    
            if response == YES:
                self.flagAnalysisRunning = False
                self.reject()
        else:

            self.reject()


    def closeEvent(self, event):
        if self.flagAnalysisRunning:
            QMessageBox.warning(self, programName , 'A media analysis is running. Please wait before closing window')
            event.ignore()


    def pbOK_clicked(self):

        def is_numeric(s):
            try:
                float(s)
                return True
            except ValueError:
                return False

        if self.flagAnalysisRunning:
            QMessageBox.warning(self, programName , 'A media analysis is running. Please wait before closing window')
            return

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

        # check if media list #2 populated and media list #1 empty
        if self.tabProjectType.currentIndex() == 0 and not self.lwVideo.count():
            QMessageBox.critical(self, programName , 'Add a media file in the first list!' )
            return

        self.accept()


    def processCompleted(self, nframe, videoTime, fileContentMD5, nPlayer, fileName):
        '''
        function triggered at the end of media file analysis with FFMPEG
        '''
        
        if nframe:
            self.media_file_info[ fileContentMD5 ]['nframe'] = nframe
            self.media_file_info[ fileContentMD5 ]['video_length'] = int(videoTime)   # ms
            self.mediaDurations[ fileName ] = int(videoTime)/1000
            self.mediaFPS[ fileName ] = nframe / (int(videoTime)/1000)
        else:
            QMessageBox.critical(self, programName, 'BORIS is not able to determine the frame rate of the video even after accurate analysis.\nCheck your video.', QMessageBox.Ok | QMessageBox.Default, QMessageBox.NoButton)
            return False

        self.widgetEnabled(True)

        if self.flagAnalysisRunning:
            QMessageBox.information(self, programName,'Video analysis done ( %s - %d frames ).' % (seconds2time(videoTime/1000), nframe) , QMessageBox.Ok | QMessageBox.Default, QMessageBox.NoButton)

        self.flagAnalysisRunning = False

        self.add_media_to_listview(nPlayer, fileName, fileContentMD5)

        return True



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
    
                if out != 'media error':
                    self.media_file_info[ fileContentMD5 ] = {'video_length': int(out) }
                    self.mediaDurations[ fileName ] = int(out)/1000
                else:
                    QMessageBox.critical(self, programName , 'This file do not seem to be a playable media file.')
                    return
    
                # check FPS
                if fps:
                    self.media_file_info[ fileContentMD5 ]['nframe'] = int(fps * int(out)/1000)
                    self.mediaFPS[ fileName ] = fps
                else:
                    if FFMPEG in self.availablePlayers:
                        response = dialog.MessageDialog(programName, 'BORIS is not able to determine the frame rate of the video.\nLaunch accurate video analysis?\nThis analysis may be long (half time of video)', [YES, NO ])
    
                        if response == YES:
                            self.process = Process()
                            self.process.signal.sig.connect(self.processCompleted)
                            self.process.fileContentMD5 = fileContentMD5
                            self.process.filePath = fileName #mediaPathName
                            self.process.ffmpeg_bin = self.ffmpeg_bin
                            self.process.nPlayer = nPlayer
                            self.process.start()

                            while not self.process.isRunning():
                                time.sleep(0.01)
                                continue

                            self.flagAnalysisRunning = True
                            self.widgetEnabled(False)

                        else:
                            self.media_file_info[ fileContentMD5 ]['nframe'] = 0
                    else:
                        self.media_file_info[ fileContentMD5 ]['nframe'] = 0

            else:
                if 'project_media_file_info' in self.pj and fileContentMD5 in self.pj['project_media_file_info']:
                    try:
                        self.mediaDurations[ fileName ] = self.pj['project_media_file_info'][fileContentMD5]["video_length"]/1000
                        self.mediaFPS[ fileName ] = self.pj['project_media_file_info'][fileContentMD5]["nframe"] / (self.pj['project_media_file_info'][fileContentMD5]["video_length"]/1000)
                    except:
                        pass

            self.add_media_to_listview(nPlayer, fileName, fileContentMD5)


    def add_media_to_listview(self, nPlayer, fileName, fileContentMD5):
        if not self.flagAnalysisRunning:

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

            self.fileName2hash[ fileName ] = fileContentMD5

    def remove_media(self, nPlayer):

        if nPlayer == PLAYER1:
            for selectedItem in self.lwVideo.selectedItems():
                print( self.lwVideo.row(selectedItem) )
                print( selectedItem.text() )
                try:
                    del self.media_file_info[ self.fileName2hash[ selectedItem.text() ] ]
                    del self.fileName2hash[ selectedItem.text() ]
                    del self.mediaDurations[ selectedItem.text() ]
                except:
                    pass

                self.lwVideo.takeItem(self.lwVideo.row(selectedItem))

        if nPlayer == PLAYER2:
            for selectedItem in self.lwVideo_2.selectedItems():

                try:
                    del self.media_file_info[ self.fileName2hash[ selectedItem.text() ] ]
                    del self.fileName2hash[ selectedItem.text() ]
                    del self.mediaDurations[ selectedItem.text() ]
                except:
                    pass

                self.lwVideo_2.takeItem(self.lwVideo_2.row(selectedItem))
