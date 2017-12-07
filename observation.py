#!/usr/bin/env python3

"""
BORIS
Behavioral Observation Research Interactive Software
Copyright 2012-2017 Olivier Friard


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

try:
    from PyQt5.QtGui import *
    from PyQt5.QtCore import *
    from PyQt5.QtWidgets import *
except:
    from PyQt4.QtGui import *
    from PyQt4.QtCore import *

import os
import time
import hashlib
import tempfile
import glob
import logging

from config import *
from utilities import *
import dialog
import plot_spectrogram
import recode_widget

if QT_VERSION_STR[0] == "4":
    from observation_ui import Ui_Form
else:
    from observation_ui5 import Ui_Form

out = ""
fps = 0

class Observation(QDialog, Ui_Form):

    def __init__(self, log_level, parent=None):

        super(Observation, self).__init__(parent)
        logging.basicConfig(level=log_level)

        self.setupUi(self)

        self.lbMediaAnalysis.setText("")

        self.pbAddVideo.clicked.connect(lambda: self.add_media(PLAYER1))
        self.pbRemoveVideo.clicked.connect(lambda: self.remove_media(PLAYER1))
        self.pbAddMediaFromDir.clicked.connect(lambda: self.add_media_from_dir(PLAYER1))
        
        self.pb_add_data_file.clicked.connect(self.add_data_file)
        self.pb_view_data_head.clicked.connect(self.view_data_file_head)
        self.pb_remove_data_file.clicked.connect(self.remove_data_file)

        self.pbAddVideo_2.clicked.connect(lambda: self.add_media(PLAYER2))
        self.pbRemoveVideo_2.clicked.connect(lambda: self.remove_media(PLAYER2))

        self.cbVisualizeSpectrogram.clicked.connect(self.generate_spectrogram)

        self.pbSave.clicked.connect(self.pbSave_clicked)
        self.pbLaunch.clicked.connect(self.pbLaunch_clicked)
        self.pbCancel.clicked.connect(self.pbCancel_clicked)

        self.mediaDurations, self.mediaFPS, self.mediaHasVideo, self.mediaHasAudio = {}, {}, {}, {}

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

    def add_data_file(self):
        """
        user select a data file to be plotted synchronously with media file
        """
        os.chdir(os.path.expanduser("~"))
        fn = QFileDialog(self).getOpenFileName(self, "Add data file", "", "All files (*)")
        file_name = fn[0] if type(fn) is tuple else fn

        if file_name:
            
            columns_to_plot = "1,2"
            # check data file
            r = check_txt_file(file_name)
            if not r["homogeneous"]: # not all rows have 2 fields
                QMessageBox.critical(self, programName , "This file does not contain a constant number of fields")
                return

            if r["fields number"] != 2: # number of fields is != 2 
                text, ok = QInputDialog.getText(self, "This file contains {} fields. 2 are required".format(r["fields number"]), "Enter the column number to plot (time,value)")
                if ok:
                    if len(str(text).split(",")) != 2:
                        QMessageBox.critical(self, programName , "Indicate only 2 columns")
                        return
                    columns_to_plot = str(text).replace(" ", "")
                else:
                    return
            
            
            self.tw_data_files.setRowCount(self.tw_data_files.rowCount() + 1)

            self.tw_data_files.setItem(self.tw_data_files.rowCount() - 1, PLOT_DATA_FILEPATH_IDX, QTableWidgetItem(file_name))

            self.tw_data_files.setItem(self.tw_data_files.rowCount() - 1, PLOT_DATA_COLUMNS_IDX, QTableWidgetItem(columns_to_plot))
            # plot title
            self.tw_data_files.setItem(self.tw_data_files.rowCount() - 1, PLOT_DATA_PLOTTITLE_IDX, QTableWidgetItem(""))
            # variable name
            self.tw_data_files.setItem(self.tw_data_files.rowCount() - 1, PLOT_DATA_VARIABLENAME_IDX, QTableWidgetItem(""))

            # time interval
            self.tw_data_files.setItem(self.tw_data_files.rowCount() - 1, PLOT_DATA_TIMEINTERVAL_IDX, QTableWidgetItem("60"))

            # offset
            self.tw_data_files.setItem(self.tw_data_files.rowCount() - 1, PLOT_DATA_TIMEOFFSET_IDX, QTableWidgetItem("0"))


            # substract first value
            combobox = QComboBox()
            combobox.addItems(["False", "True"])
            self.tw_data_files.setCellWidget(self.tw_data_files.rowCount() - 1, PLOT_DATA_SUBSTRACT1STVALUE_IDX, combobox)

            # plot line color  
            combobox = QComboBox()
            combobox.addItems(DATA_PLOT_STYLES)
            self.tw_data_files.setCellWidget(self.tw_data_files.rowCount() - 1, PLOT_DATA_PLOTCOLOR_IDX, combobox)
            

    def view_data_file_head(self):
        """
        view first parts of data file
        """
        if self.tw_data_files.selectedIndexes():
            text = ""
            try:
                with open(self.tw_data_files.item(self.tw_data_files.selectedIndexes()[0].row(), 0).text()) as f_in:
                    for _ in range(5):
                        text += f_in.readline()
            except:
                QMessageBox.critical(self, programName, str(sys.exc_info()[0]))

            if text:
                dialog.MessageDialog(programName, "<pre>"+text+"</pre>", [OK])

                '''
                self.data_file_head = dialog.ResultsWidget()
                #self.results.setWindowFlags(Qt.WindowStaysOnTopHint)
                self.data_file_head.resize(540, 340)
                self.data_file_head.setWindowTitle(programName + " - Data file first lines")
                self.data_file_head.lb.setText(os.path.basename(self.tw_data_files.item(self.tw_data_files.selectedIndexes()[0].row(), 0).text()))
                self.data_file_head.ptText.setReadOnly(True)
                self.data_file_head.ptText.appendHtml("<pre>" + text + "</pre>")
                
                self.data_file_head.show()
                '''



    def generate_spectrogram(self):
        """
        generate spectrogram of all media files loaded in player #1
        """

        if self.cbVisualizeSpectrogram.isChecked():

            if dialog.MessageDialog(programName, ("You choose to visualize the spectrogram for the media in player #1.<br>"
                                                  "Choose YES to generate the spectrogram.\n\n"
                                                  "Spectrogram generation can take some time for long media, be patient"), [YES, NO]) == YES:

                if not self.ffmpeg_cache_dir:
                    tmp_dir = tempfile.gettempdir()
                else:
                    tmp_dir = self.ffmpeg_cache_dir

                w = recode_widget.Info_widget()
                w.resize(350, 100)
                w.setWindowFlags(Qt.WindowStaysOnTopHint)
                w.setWindowTitle("BORIS")
                w.label.setText("Generating spectrogram...")

                #for media in self.pj[OBSERVATIONS][self.observationId][FILE][PLAYER1]:
                for row in range(self.twVideo1.rowCount()):
                    if os.path.isfile(self.twVideo1.item(row, 0).text()):
                        process = plot_spectrogram.create_spectrogram_multiprocessing(mediaFile=self.twVideo1.item(row, 0).text(),
                                                                                      tmp_dir=tmp_dir,
                                                                                      chunk_size=self.chunk_length,
                                                                                      ffmpeg_bin=self.ffmpeg_bin,
                                                                                      spectrogramHeight=self.spectrogramHeight,
                                                                                      spectrogram_color_map=self.spectrogram_color_map)
                        if process:
                            w.show()
                            while True:
                                QApplication.processEvents()
                                if not process.is_alive():
                                    w.hide()
                                    break
                    else:
                        QMessageBox.warning(self, programName , "<b>{}</b> file not found".format(self.twVideo1.item(row, 0).text()))
            else:
                self.cbVisualizeSpectrogram.setChecked(False)


    def pbCancel_clicked(self):
        self.reject()

    def check_parameters(self):
        """
        check observation parameters
        
        return True if everything OK else False
        """
        def is_numeric(s):
            try:
                float(s)
                return True
            except ValueError:
                return False

        # check time offset
        if not is_numeric(self.leTimeOffset.text()):
            QMessageBox.warning(self, programName , "<b>{}</b> is not recognized as a valid time offset format".format(self.leTimeOffset.text()))
            return False

        # check if indep variables are correct type
        for row in range(0, self.twIndepVariables.rowCount()):

            if self.twIndepVariables.item(row, 1).text() == NUMERIC:
                if self.twIndepVariables.item(row, 2).text() and not is_numeric( self.twIndepVariables.item(row, 2).text() ):
                    QMessageBox.critical(self, programName , "The <b>{}</b> variable must be numeric!".format(self.twIndepVariables.item(row, 0).text()))
                    return False

        # check if observation id not empty
        if not self.leObservationId.text():
            QMessageBox.warning(self, programName , "The <b>observation id</b> is mandatory and must be unique!" )
            return False

        # check if new obs and observation id already present or if edit obs and id changed
        if (self.mode == "new") or (self.mode == "edit" and self.leObservationId.text() != self.mem_obs_id):
            if self.leObservationId.text() in self.pj[OBSERVATIONS]:
                QMessageBox.critical(self, programName, "The observation id <b>{0}</b> is already used!<br>{1}<br>{2}".format(self.leObservationId.text(),
                                                                                                                             self.pj['observations'][self.leObservationId.text()]['description'],
                                                                                                                             self.pj['observations'][self.leObservationId.text()]['date']))
                return False

        # check if media list #2 populated and media list #1 empty
        if self.tabProjectType.currentIndex() == 0 and not self.twVideo1.rowCount():
            QMessageBox.critical(self, programName , "Add a media file in the first media player!" )
            return False

        return True


    def pbLaunch_clicked(self):
        """
        Close window and start observation
        """

        if self.check_parameters():
            self.done(2)


    def pbSave_clicked(self):
        """
        Close window and save observation
        """
        if self.check_parameters():
            self.accept()


    def check_media(self, filePaths, nPlayer):
        """
        check media and add them to list view if duration > 0
        
        parameters:

        filePaths -- paths of media files
        nPlayer -- player #
        """

        for filePath in filePaths:
            nframes, videoDuration_ms, videoDuration_s, fps, hasVideo, hasAudio = accurate_media_analysis(self.ffmpeg_bin, filePath)

            if videoDuration_s > 0:
                self.mediaDurations[filePath] = videoDuration_s
                self.mediaFPS[filePath] = fps
                self.mediaHasVideo[filePath] = hasVideo
                self.mediaHasAudio[filePath] = hasAudio
                self.add_media_to_listview(nPlayer, filePath, "")
            else:
                QMessageBox.critical(self, programName, "The <b>{filePath}</b> file does not seem to be a media file.".format(filePath=filePath))


    def add_media(self, nPlayer):
        """
        add media in player nPlayer
        """
        # check if more media in player1 before adding media to player2
        if nPlayer == PLAYER2 and self.twVideo1.rowCount() > 1:
            QMessageBox.critical(self, programName, "It is not yet possible to play a second media when more media are loaded in the first media player" )
            return

        os.chdir(os.path.expanduser("~"))
        fn = QFileDialog(self).getOpenFileNames(self, "Add media file(s)", "", "All files (*)")
        fileNames = fn[0] if type(fn) is tuple else fn

        if fileNames:
            self.check_media(fileNames, nPlayer)

        self.cbVisualizeSpectrogram.setEnabled(self.twVideo1.rowCount() > 0)
        self.cbCloseCurrentBehaviorsBetweenVideo.setEnabled(self.twVideo1.rowCount() > 0)


    def add_media_from_dir(self, nPlayer):
        """
        add all media from a selected directory
        """
        dirName = QFileDialog().getExistingDirectory(self, "Select directory")
        if dirName:
            for fileName in glob.glob(dirName + os.sep + "*"):
                self.check_media(fileName, nPlayer)
        self.cbVisualizeSpectrogram.setEnabled(self.twVideo1.rowCount() > 0)
        self.cbCloseCurrentBehaviorsBetweenVideo.setEnabled(self.twVideo1.rowCount() > 0)


    def add_media_to_listview(self, nPlayer, fileName, fileContentMD5):
        """
        add media file path to list widget
        """

        if not self.twVideo1.rowCount() and nPlayer == PLAYER2:
            QMessageBox.critical(self, programName, "Add the first media file to Player #1")
            return False

        if self.twVideo1.rowCount() and self.twVideo2.rowCount():
            QMessageBox.critical(self, programName, "It is not yet possible to play a second media when more media are loaded in the first media player")
            return False

        if self.twVideo2.rowCount() > 1:
            QMessageBox.critical(self, programName, "It is not yet possible to play a second media when more media are loaded in the first media player")
            return False

        if nPlayer == PLAYER1:
            twVideo = self.twVideo1
        if nPlayer == PLAYER2:
            twVideo = self.twVideo2

        twVideo.setRowCount(twVideo.rowCount() + 1)
        twVideo.setItem(twVideo.rowCount()-1, 0, QTableWidgetItem(fileName) )
        twVideo.setItem(twVideo.rowCount()-1, 1, QTableWidgetItem("{}".format(seconds2time(self.mediaDurations[fileName]))))
        twVideo.setItem(twVideo.rowCount()-1, 2, QTableWidgetItem("{}".format(self.mediaFPS[fileName])))
        twVideo.setItem(twVideo.rowCount()-1, 3, QTableWidgetItem("{}".format(self.mediaHasVideo[fileName])))
        twVideo.setItem(twVideo.rowCount()-1, 4, QTableWidgetItem("{}".format(self.mediaHasAudio[fileName])))


    def remove_data_file(self):
        """
        remove selected data file from list widget
        """
        if self.tw_data_files.selectedIndexes():
            self.tw_data_files.removeRow(self.tw_data_files.selectedIndexes()[0].row())

    def remove_media(self, nPlayer):
        """
        remove selected item from list widget
        """

        if nPlayer == PLAYER1:

            if self.twVideo1.selectedIndexes():
                mediaPath = self.twVideo1.item(self.twVideo1.selectedIndexes()[0].row(),0).text()
                self.twVideo1.removeRow(self.twVideo1.selectedIndexes()[0].row())

                if mediaPath not in [self.twVideo2.item(idx, 0).text() for idx in range(self.twVideo2.rowCount())]:
                    try:
                        del self.mediaDurations[mediaPath]
                    except:
                        pass
                    try:
                        del self.mediaFPS[mediaPath]
                    except:
                        pass

        if nPlayer == PLAYER2:
            if self.twVideo2.selectedIndexes():
                mediaPath = self.twVideo2.item(self.twVideo2.selectedIndexes()[0].row(),0).text()
                self.twVideo2.removeRow(self.twVideo2.selectedIndexes()[0].row())

                if mediaPath not in [ self.twVideo1.item(idx, 0).text() for idx in range(self.twVideo1.rowCount())]:
                    try:
                        del self.mediaDurations[mediaPath]
                    except:
                        pass
                    try:
                        del self.mediaFPS[mediaPath]
                    except:
                        pass

        self.cbVisualizeSpectrogram.setEnabled(self.twVideo1.rowCount() > 0)
        self.cbCloseCurrentBehaviorsBetweenVideo.setEnabled(self.twVideo1.rowCount() > 0)
