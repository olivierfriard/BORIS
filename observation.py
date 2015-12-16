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

from PyQt4.QtCore import *
from PyQt4.QtGui import *
import os
import time
import hashlib
import tempfile
from config import *
from utilities import *
import dialog
import plot_spectrogram
import glob

from observation_ui import Ui_Form

out = ''
fps = 0

"""
class ThreadSignalSpectrogram(QObject):
    sig = pyqtSignal(str)


class ProcessSpectro(QThread):
    '''
    process for spectrogram creation
    '''
    def __init__(self, chunk_length, parent=None):
        QThread.__init__(self, parent)
        self.fileName = ''
        self.chunk_length = chunk_length
        self.signal = ThreadSignalSpectrogram()

    def run(self):
        print(self.filename, self.chunk_length)
        fileName1stChunk = plot_spectrogram.graph_spectrogram(self.fileName, self.chunk_length)
        self.signal.sig.emit(fileName1stChunk)
"""

class Observation(QDialog, Ui_Form):

    def __init__(self, parent=None):

        super(Observation, self).__init__(parent)
        self.setupUi(self)

        self.lbMediaAnalysis.setText("")

        self.pbAddVideo.clicked.connect(lambda: self.add_media(PLAYER1))
        self.pbRemoveVideo.clicked.connect(lambda: self.remove_media(PLAYER1))
        self.pbAddMediaFromDir.clicked.connect(lambda: self.add_media_from_dir(PLAYER1))

        self.pbAddVideo_2.clicked.connect(lambda: self.add_media(PLAYER2))
        self.pbRemoveVideo_2.clicked.connect(lambda: self.remove_media(PLAYER2))

        self.cbVisualizeSpectrogram.clicked.connect( self.generate_spectrogram )

        self.pbOK.clicked.connect(self.pbOK_clicked)
        self.pbCancel.clicked.connect( self.pbCancel_clicked )

        self.media_file_info = {}
        self.fileName2hash = {}
        self.availablePlayers = []

        self.flagAnalysisRunning = False
        self.spectrogramFinished = False

        self.mediaDurations = {}
        self.mediaFPS = {}

        self.cbVisualizeSpectrogram.setEnabled(False)
        self.cbCloseCurrentBehaviorsBetweenVideo.setEnabled(False)

    """
    def processSpectrogramCompleted(self, fileName1stChunk):
        '''
        function triggered at the end of spectrogram creation
        '''

        print('fileName1stChunk',fileName1stChunk)
        self.spectrogramFinished = True

        self.infobutton.setText('Go!')

        self.spectro = Spectrogram( fileName1stChunk )
        self.spectro.show()
        self.timer_spectro.start()

        self.PlayPause()
    """


    def generate_spectrogram(self):

        if self.cbVisualizeSpectrogram.isChecked():

            if not self.ffmpeg_bin:
                QMessageBox.warning(self, programName, ("You chose to visualize the spectrogram during observation "
                                                       "but FFmpeg was not found and it is required for this feature.<br>"
                                                       "See File > Preferences menu option > Frame-by-frame mode"))
                self.cbVisualizeSpectrogram.setChecked(False)
                return


            response = dialog.MessageDialog(programName, ("You chose to visualize the spectrogram for the media in player #1.<br>"
                                                          "Choose YES to generate the spectrogram.\n\n"
                                                          "Spectrogram generation can take some time for long media, be patient"), [YES, NO ])
            if response == YES:

                # check temp dir for images from ffmpeg
                if not self.ffmpeg_cache_dir:
                    tmp_dir = tempfile.gettempdir()
                else:
                    tmp_dir = self.ffmpeg_cache_dir

                self.lbMediaAnalysis.setText("<b>Spectrogram generation...</b>")
                QApplication.processEvents()

                for index in range(self.lwVideo.count()):
                    _ = plot_spectrogram.graph_spectrogram(mediaFile=self.lwVideo.item(index).text(), tmp_dir=tmp_dir, chunk_size=self.chunk_length, ffmpeg_bin=self.ffmpeg_bin)  # return first chunk PNG file (not used)

                self.lbMediaAnalysis.setText("<b>Spectrogram was generated successfully</b>")
                QApplication.processEvents()


                """
                self.spectrogramFinished = False
                process = ProcessSpectro()
                process.signal.sig.connect(self.processSpectrogramCompleted)


                print(self.lwVideo.item(0).text() )

                process.fileName = self.lwVideo.item(0).text()
                process.chunk_length = CHUNK
                process.start()

                print('started')

                while not process.isRunning():
                    time.sleep(0.01)
                    continue


                print('started2')
                """

            else:
                self.cbVisualizeSpectrogram.setChecked(False)


    def widgetEnabled(self, flag):
        '''
        enable/disable widget for selecting media file
        '''
        self.tabProjectType.setEnabled(flag)
        if not flag:
            self.lbMediaAnalysis.setText("<b>A media analysis is running</b>")
        else:
            self.lbMediaAnalysis.setText('')


    def pbCancel_clicked(self):

        if self.flagAnalysisRunning:
            if dialog.MessageDialog(programName, "A media analysis is running. Do you want to cancel the new observation?", [YES, NO ]) == YES:
                self.flagAnalysisRunning = False
                self.reject()
        else:
            self.reject()


    def closeEvent(self, event):
        if self.flagAnalysisRunning:
            QMessageBox.warning(self, programName , "A media analysis is running. Please wait before closing window")
            event.ignore()


    def pbOK_clicked(self):

        def is_numeric(s):
            try:
                float(s)
                return True
            except ValueError:
                return False

        if self.flagAnalysisRunning:
            QMessageBox.warning(self, programName , "A media analysis is running. Please wait before closing window")
            return

        # check time offset
        if not is_numeric(self.leTimeOffset.text()):
            QMessageBox.warning(self, programName , "<b>{}</b> is not recognized as a valid time offset format".format(self.leTimeOffset.text()))
            return

        # check if indep variables are correct type
        for row in range(0, self.twIndepVariables.rowCount()):

            if self.twIndepVariables.item(row, 1).text() == NUMERIC:
                if self.twIndepVariables.item(row, 2).text() and not is_numeric( self.twIndepVariables.item(row, 2).text() ):
                    QMessageBox.critical(self, programName , "The <b>{}</b> variable must be numeric!".format(self.twIndepVariables.item(row, 0).text()))
                    return

        # check if observation id not empty
        if not self.leObservationId.text():
            QMessageBox.warning(self, programName , "The <b>observation id</b> is mandatory and must be unique!" )
            return

        # check if new obs and observation id already present or if edit obs and id changed
        if (self.mode == "new") or (self.mode == "edit" and self.leObservationId.text() != self.mem_obs_id):
            if self.leObservationId.text() in self.pj[OBSERVATIONS]:
                QMessageBox.critical(self, programName , "The observation id <b>{0}</b> is already used!<br>{1}<br>{2}".format(self.leObservationId.text(),
                                                                                                                             self.pj['observations'][self.leObservationId.text()]['description'],
                                                                                                                             self.pj['observations'][self.leObservationId.text()]['date']))

                return

        # check if media list #2 populated and media list #1 empty
        if self.tabProjectType.currentIndex() == 0 and not self.lwVideo.count():
            QMessageBox.critical(self, programName , "Add a media file in the first media player!" )
            return

        self.accept()


    def processCompleted(self, nframe, videoTime, fileContentMD5, nPlayer, fileName):
        '''
        function triggered at the end of media file analysis with FFMPEG
        '''

        if nframe:
            self.media_file_info[ fileContentMD5 ]["nframe"] = nframe

            # analysis with ffmpeg made on first 60 seconds so the video duration is not available
            #self.media_file_info[ fileContentMD5 ]['video_length'] = int(videoTime)   # ms
            #self.mediaDurations[ fileName ] = int(videoTime)/1000
            self.mediaFPS[fileName] = nframe / (int(videoTime)/1000)
        else:
            QMessageBox.critical(self, programName, ("BORIS is not able to determine the frame rate of the video "
                                                     "even after accurate analysis.\nCheck your video."),
                                                     QMessageBox.Ok | QMessageBox.Default, QMessageBox.NoButton)
            return False

        self.widgetEnabled(True)

        if self.flagAnalysisRunning:
            QMessageBox.information(self, programName, "Video analysis done:<br>Length: {} s.<br>Frame rate: {} FPS.".format(seconds2time(self.mediaDurations[fileName]),
                                                                                                                            nframe / (videoTime/1000)),
                                                                                                                            QMessageBox.Ok | QMessageBox.Default, QMessageBox.NoButton)

        self.flagAnalysisRunning = False
        self.add_media_to_listview(nPlayer, fileName, fileContentMD5)
        return True


    def check_media(self, fileName, nPlayer):
        try:
            mediaLength = self.mediaDurations[fileName]
            mediaFPS = self.mediaFPS[fileName]
        except:
            # check if md5 checksum already in project_media_file_info dictionary
            fileContentMD5 = hashfile( fileName, hashlib.md5())
            if (not "project_media_file_info" in self.pj) \
               or ("project_media_file_info" in self.pj and not fileContentMD5 in self.pj["project_media_file_info"]):

                out, fps, nvout = playWithVLC(fileName)

                if out != "media error":
                    self.media_file_info[ fileContentMD5 ] = {"video_length": int(out) }
                    self.mediaDurations[ fileName ] = int(out)/1000
                else:
                    QMessageBox.critical(self, programName , "This file do not seem to be a playable media file.")
                    return

                # check FPS
                if nvout:  # media file has video
                    if fps:
                        self.media_file_info[ fileContentMD5 ]["nframe"] = int(fps * int(out)/1000)
                        self.mediaFPS[ fileName ] = fps
                    else:
                        if FFMPEG in self.availablePlayers:
                            response = dialog.MessageDialog(programName, ("BORIS is not able to determine the frame rate of the video.\n"
                                                                          "Launch accurate video analysis?"), [YES, NO ])

                            if response == YES:
                                self.process = Process()  # class in utilities.py
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
                                self.media_file_info[fileContentMD5]["nframe"] = 0
                        else:
                            self.media_file_info[fileContentMD5]["nframe"] = 0
                else:
                    self.media_file_info[fileContentMD5]["nframe"] = 0

            else:
                if "project_media_file_info" in self.pj and fileContentMD5 in self.pj["project_media_file_info"]:
                    try:
                        self.mediaDurations[fileName] = self.pj["project_media_file_info"][fileContentMD5]["video_length"]/1000
                        self.mediaFPS[fileName] = self.pj["project_media_file_info"][fileContentMD5]["nframe"] / (self.pj["project_media_file_info"][fileContentMD5]["video_length"]/1000)
                        self.media_file_info[fileContentMD5]["video_length"] = self.pj["project_media_file_info"][fileContentMD5]["video_length"]
                        self.media_file_info[fileContentMD5]["nframe"] = self.pj["project_media_file_info"][fileContentMD5]["nframe"]
                    except:
                        pass

        self.add_media_to_listview(nPlayer, fileName, fileContentMD5)


    def add_media(self, nPlayer):
        '''
        add media in player
        '''
        # check if more media in player1 before adding media to player2
        if nPlayer == PLAYER2 and self.lwVideo.count() > 1:
            QMessageBox.critical(self, programName, "It is not yet possible to play a second media when more media are loaded in the first media player" )
            return

        os.chdir(os.path.expanduser("~"))
        fileName = QFileDialog(self).getOpenFileName(self, "Add media file", "", "All files (*)")

        if fileName:
            self.check_media(fileName, nPlayer)

        self.cbVisualizeSpectrogram.setEnabled( self.lwVideo.count() > 0 )
        self.cbCloseCurrentBehaviorsBetweenVideo.setEnabled( self.lwVideo.count() > 0 )

    def add_media_from_dir(self, nPlayer):
        '''
        add all media from a selected directory
        '''
        dirName = QFileDialog().getExistingDirectory(self, "Select directory")
        if dirName:
            print(dirName)
            for fileName in glob.glob(dirName + os.sep + "*" ):
                self.check_media(fileName, nPlayer)
        self.cbVisualizeSpectrogram.setEnabled(self.lwVideo.count() > 0)
        self.cbCloseCurrentBehaviorsBetweenVideo.setEnabled( self.lwVideo.count() > 0 )


    def add_media_to_listview(self, nPlayer, fileName, fileContentMD5):
        '''
        add media file path to list widget
        '''
        if not self.flagAnalysisRunning:

            if nPlayer == PLAYER1:
                if self.lwVideo.count() and self.lwVideo_2.count():
                    QMessageBox.critical(self, programName, "It is not yet possible to play a second media when more media are loaded in the first media player" )
                    return False
                self.lwVideo.addItems([fileName])

            if nPlayer == PLAYER2:
                if self.lwVideo.count() > 1:
                    QMessageBox.critical(self, programName, "It is not yet possible to play a second media when more media are loaded in the first media player" )
                    return False
                self.lwVideo_2.addItems([fileName])

            self.fileName2hash[fileName] = fileContentMD5


    def remove_media(self, nPlayer):
        '''
        remove selected item from list widget
        '''

        if nPlayer == PLAYER1:
            for selectedItem in self.lwVideo.selectedItems():
                mem = selectedItem.text()
                self.lwVideo.takeItem(self.lwVideo.row(selectedItem))

                # check if media file path no more in the 2 listwidget
                if not mem in [ self.lwVideo.item(idx).text() for idx in range(self.lwVideo.count())] \
                   and not mem in [ self.lwVideo_2.item(idx).text() for idx in range(self.lwVideo_2.count())]:
                    try:
                        del self.media_file_info[ self.fileName2hash[mem]]
                        del self.fileName2hash[mem]
                        del self.mediaDurations[mem]
                    except:
                        pass

        if nPlayer == PLAYER2:
            for selectedItem in self.lwVideo_2.selectedItems():
                mem = selectedItem.text()
                self.lwVideo_2.takeItem(self.lwVideo_2.row(selectedItem))

                # check if media file path no more in the 2 listwidget
                if not mem in [self.lwVideo.item(idx).text() for idx in range(self.lwVideo.count())] \
                   and not mem in [self.lwVideo_2.item(idx).text() for idx in range(self.lwVideo_2.count())]:
                    try:
                        del self.media_file_info[self.fileName2hash[selectedItem.text()]]
                        del self.fileName2hash[selectedItem.text()]
                        del self.mediaDurations[selectedItem.text()]
                    except:
                        pass

        self.cbVisualizeSpectrogram.setEnabled(self.lwVideo.count() > 0)
        self.cbCloseCurrentBehaviorsBetweenVideo.setEnabled( self.lwVideo.count() > 0 )
