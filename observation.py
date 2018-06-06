#!/usr/bin/env python3

"""
BORIS
Behavioral Observation Research Interactive Software
Copyright 2012-2018 Olivier Friard


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
from pathlib import Path
import numpy

from config import *
import utilities
from utilities import *
import dialog
import plot_spectrogram
import plot_data_module
import project_functions

MEDIA_FILE_PATH_IDX = 2
HAS_AUDIO_IDX = 6

if QT_VERSION_STR[0] == "4":
    from observation_ui import Ui_Form
else:
    from observation_ui5 import Ui_Form

out = ""
fps = 0

class AssignConverter(QDialog):
    """
    dialog for assigning converter to selected column
    """

    def __init__(self, columns, converters, col_conv):
        super().__init__()

        self.setWindowTitle("Converters")

        self.vbox = QVBoxLayout()

        self.label = QLabel()
        self.label.setText("Assign converter to column")
        self.vbox.addWidget(self.label)

        self.cbb = []
        for column_idx in columns.split(","):
            hbox = QHBoxLayout()
            hbox.addWidget(QLabel("Column #{}:".format(column_idx)))
            self.cbb.append(QComboBox())
            self.cbb[-1].addItems(["None"] + sorted(converters.keys()))

            if column_idx in col_conv:
                self.cbb[-1].setCurrentIndex((["None"] + sorted(converters.keys())).index(col_conv[column_idx]))
            else:
                self.cbb[-1].setCurrentIndex(0)
            hbox.addWidget(self.cbb[-1])
            self.vbox.addLayout(hbox)

        hbox1 = QHBoxLayout()
        self.pbOK = QPushButton("OK")
        self.pbOK.clicked.connect(self.accept)
        self.pbCancel = QPushButton("Cancel")
        self.pbCancel.clicked.connect(self.reject)
        spacerItem = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)
        hbox1.addItem(spacerItem)
        hbox1.addWidget(self.pbCancel)
        hbox1.addWidget(self.pbOK)
        self.vbox.addLayout(hbox1)

        self.setLayout(self.vbox)


class Observation(QDialog, Ui_Form):

    def __init__(self, tmp_dir, project_path="", converters={}, log_level="", parent=None):
        """
        Args:
            tmp_dir (str): path of temporary directory
            project_path (str): path of project
            converters (dict): converters dictionary
            log_level: level of log 
        """

        super().__init__(parent)

        self.tmp_dir = tmp_dir
        self.project_path = project_path
        self.converters = converters

        if log_level:
            logging.basicConfig(level=log_level)

        self.setupUi(self)

        self.pbAddVideo.clicked.connect(lambda: self.add_media(PLAYER1, flag_path=True))
        self.pb_add_media_without_path.clicked.connect(lambda: self.add_media(PLAYER1, flag_path=False))
        self.pbRemoveVideo.clicked.connect(lambda: self.remove_media(PLAYER1))
        self.pbAddMediaFromDir.clicked.connect(lambda: self.add_media_from_dir(PLAYER1, flag_path=True))
        self.pb_add_all_media_from_dir_without_path.clicked.connect(lambda: self.add_media_from_dir(PLAYER1, flag_path=False))
        
        self.pb_add_data_file.clicked.connect(lambda: self.add_data_file(flag_path=True))
        self.pb_add_data_file_wo_path.clicked.connect(lambda: self.add_data_file(flag_path=False))
        self.pb_view_data_head.clicked.connect(self.view_data_file_head)
        self.pb_plot_data.clicked.connect(self.plot_data_file)
        self.pb_remove_data_file.clicked.connect(self.remove_data_file)

        self.cbVisualizeSpectrogram.clicked.connect(self.generate_spectrogram)

        self.pbSave.clicked.connect(self.pbSave_clicked)
        self.pbLaunch.clicked.connect(self.pbLaunch_clicked)
        self.pbCancel.clicked.connect(self.pbCancel_clicked)
        
        self.tw_data_files.cellDoubleClicked[int, int].connect(self.tw_data_files_cellDoubleClicked)

        self.mediaDurations, self.mediaFPS, self.mediaHasVideo, self.mediaHasAudio = {}, {}, {}, {}

        self.cbVisualizeSpectrogram.setEnabled(False)
        self.cbCloseCurrentBehaviorsBetweenVideo.setEnabled(False)

        self.tabWidget.setCurrentIndex(0)

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

    def tw_data_files_cellDoubleClicked(self, row, column):
        """
        double click on "Converters column"
        """
        if column == PLOT_DATA_CONVERTERS_IDX:
            if self.tw_data_files.item(row, PLOT_DATA_COLUMNS_IDX).text():
                w = AssignConverter(self.tw_data_files.item(row, PLOT_DATA_COLUMNS_IDX).text(), self.converters,
                                    eval(self.tw_data_files.item(row, PLOT_DATA_CONVERTERS_IDX).text()) if self.tw_data_files.item(row, PLOT_DATA_CONVERTERS_IDX).text() else "")

                if w.exec_():
                    d = {}
                    for col_idx, cb in zip(self.tw_data_files.item(row, PLOT_DATA_COLUMNS_IDX).text().split(","), w.cbb):
                        if cb.currentText() != "None":
                            d[col_idx] = cb.currentText()
                    self.tw_data_files.item(row, PLOT_DATA_CONVERTERS_IDX).setText(str(d))
            else:
                QMessageBox.critical(self, programName, "Select the columns to plot (time,value)")


    def plot_data_file(self):
        """
        check if data can be plotted
        """

        if self.pb_plot_data.text() == "Show plot":

            if self.tw_data_files.selectedIndexes() or self.tw_data_files.rowCount() == 1:
    
                if self.tw_data_files.rowCount() == 1:
                    row_idx = 0
                else:
                    row_idx = self.tw_data_files.selectedIndexes()[0].row()
    
                filename = self.tw_data_files.item(row_idx, PLOT_DATA_FILEPATH_IDX).text()
                columns_to_plot = self.tw_data_files.item(row_idx, PLOT_DATA_COLUMNS_IDX).text()
                plot_title = self.tw_data_files.item(row_idx, PLOT_DATA_PLOTTITLE_IDX).text()
    
                # load converters in dictionary
                if self.tw_data_files.item(row_idx, PLOT_DATA_CONVERTERS_IDX).text():
                    column_converter = eval(self.tw_data_files.item(row_idx, PLOT_DATA_CONVERTERS_IDX).text())
                    '''
                    for idx_conv in self.tw_data_files.item(row_idx, PLOT_DATA_CONVERTERS_IDX).text().split(","):
                        idx, conv = idx_conv.split(":")
                        column_converter[int(idx)] = conv
                    '''
                else:
                    column_converter = {}
    
                variable_name  = self.tw_data_files.item(row_idx, PLOT_DATA_VARIABLENAME_IDX).text()
                time_interval = int(self.tw_data_files.item(row_idx, PLOT_DATA_TIMEINTERVAL_IDX).text())
                time_offset = int(self.tw_data_files.item(row_idx, PLOT_DATA_TIMEOFFSET_IDX).text())
    
                substract_first_value = self.tw_data_files.cellWidget(row_idx, PLOT_DATA_SUBSTRACT1STVALUE_IDX).currentText()
                
                plot_color = self.tw_data_files.cellWidget(row_idx, PLOT_DATA_PLOTCOLOR_IDX).currentText()
    
                data_file_path = project_functions.media_full_path(filename, self.project_path)

                if not data_file_path:
                    QMessageBox.critical(self, programName, ("Data file not found:\n{}\n"
                                                             "If the file path is not stored the data file "
                                                             "must be in the same directory than your project").format(filename))
                    return
    
                self.test = plot_data_module.Plot_data(data_file_path,
                                                  time_interval, # time interval
                                                  time_offset,   # time offset
                                                  plot_color,    # plot style
                                                  plot_title,    # plot title
                                                  variable_name, 
                                                  columns_to_plot,
                                                  substract_first_value,
                                                  self.converters,
                                                  column_converter,
                                                  log_level=logging.getLogger().getEffectiveLevel()
                                                  )
    
                if self.test.error_msg:
                    QMessageBox.critical(self, programName, "Impossible to plot data:\n{}".format(self.test.error_msg))
                    del self.test
                    return
    
                '''
                print(test.plotter.data)
    
                print(Path(self.tmp_dir).joinpath(file_content_md5(filename)))
                numpy.save(Path(self.tmp_dir).joinpath(file_content_md5(filename)), test.plotter.data)
                '''
                
                self.test.setWindowFlags(Qt.WindowStaysOnTopHint)
                self.test.show()
                self.test.update_plot(0)
                self.pb_plot_data.setText("Close plot")
    
            else:
                QMessageBox.warning(self, programName, "Select a data file")
        
        else: # close plot
            self.test.close_plot()
            self.pb_plot_data.setText("Show plot")


    def add_data_file(self, flag_path=True):
        """
        user select a data file to be plotted synchronously with media file
        
        Args:
            flag_path (bool): true to store path of data file else False
        """

        # limit to 2 files
        if self.tw_data_files.rowCount() >= 2:
            QMessageBox.warning(self, programName , ("It is not yet possible to plot more than 2 external data"
                                                     "This limitation will be removed in future"))
            return

        QMessageBox.warning(self, programName, "This function is experimental.<br>Please report any bug")

        fd = QFileDialog(self)
        fd.setDirectory(os.path.expanduser("~") if flag_path else str(Path(self.project_path).parent))

        fn = fd.getOpenFileName(self, "Add data file", "", "All files (*)")
        file_name = fn[0] if type(fn) is tuple else fn

        if file_name:

            columns_to_plot = "1,2" # columns to plot by default

            # check data file
            r = check_txt_file(file_name) # check_txt_file defined in utilities

            if "error" in r:
                QMessageBox.critical(self, programName , r["error"])
                return

            if not r["homogeneous"]: # not all rows have 2 columns
                QMessageBox.critical(self, programName , "This file does not contain a constant number of columns")
                return

            header = self.return_file_header(file_name)
            if header:
                text, ok = QInputDialog.getText(self, "Data file: {}".format(Path(file_name).name),
                                                ("This file contains {} columns. 2 are required for the plot.<br>"
                                                 "<pre>{}</pre><br>"
                                                 "Enter the column indices to plot (time,value) separated by comma").format(r["fields number"], header))
                if ok:
                    if len(text.split(",")) != 2:
                        QMessageBox.critical(self, programName , "Indicate only 2 column indices")
                        return
                    columns_to_plot = str(text).replace(" ", "")
                    for col in text.split(","):
                        try:
                            col_idx = int(col)
                        except:
                            QMessageBox.critical(self, programName , "<b>{}</b> does not seem to be a column index".format(col))
                            return
                        if col_idx < 0 or col_idx > r["fields number"]:
                            QMessageBox.critical(self, programName , "<b>{}</b> is not a valid column index".format(col))
                            return
                else:
                    return
            else:
                return # problem with header

            self.tw_data_files.setRowCount(self.tw_data_files.rowCount() + 1)
            
            if not flag_path:
                file_name = str(Path(file_name).name)
            
            for col_idx, value in zip([PLOT_DATA_FILEPATH_IDX, PLOT_DATA_COLUMNS_IDX,
                                       PLOT_DATA_PLOTTITLE_IDX, PLOT_DATA_VARIABLENAME_IDX,
                                       PLOT_DATA_CONVERTERS_IDX, PLOT_DATA_TIMEINTERVAL_IDX,
                                       PLOT_DATA_TIMEOFFSET_IDX],
                                      [file_name, columns_to_plot,
                                       "", "",
                                       "", "60",
                                       "0"]):
                item = QTableWidgetItem(value)
                if col_idx == PLOT_DATA_CONVERTERS_IDX:
                    item.setFlags(Qt.ItemIsEnabled)
                self.tw_data_files.setItem(self.tw_data_files.rowCount() - 1, col_idx, item)

            # substract first value
            combobox = QComboBox()
            combobox.addItems(["True", "False"])
            self.tw_data_files.setCellWidget(self.tw_data_files.rowCount() - 1, PLOT_DATA_SUBSTRACT1STVALUE_IDX, combobox)

            # plot line color  
            combobox = QComboBox()
            combobox.addItems(DATA_PLOT_STYLES)
            self.tw_data_files.setCellWidget(self.tw_data_files.rowCount() - 1, PLOT_DATA_PLOTCOLOR_IDX, combobox)


    def return_file_header(self, file_name):
        """
        return file header
        
        Args:
            file_name (str): path of file
            
        Returns:
            str: 5 first rows of file
        """
        header = ""
        try:
            with open(file_name) as f_in:
                for _ in range(5):
                    header += f_in.readline()
        except:
            QMessageBox.critical(self, programName, str(sys.exc_info()[1]))
            return ""
        return header
        

    def view_data_file_head(self):
        """
        view first parts of data file
        """
        if self.tw_data_files.selectedIndexes() or self.tw_data_files.rowCount() == 1:

            if self.tw_data_files.rowCount() == 1:
                header = self.return_file_header(self.tw_data_files.item(0, 0).text())
            else:
                header = self.return_file_header(self.tw_data_files.item(self.tw_data_files.selectedIndexes()[0].row(), 0).text())

            if header:
                dialog.MessageDialog(programName, "<pre>{}</pre>".format(header), [OK])

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
        else:
            QMessageBox.warning(self, programName, "Select a data file")


    def generate_spectrogram(self):
        """
        generate spectrogram of all media files loaded in player #1
        """


        if self.cbVisualizeSpectrogram.isChecked():
            flag_spectro_produced = False
            # check if player 1 is selected
            flag_player1 = False
            for row in range(self.twVideo1.rowCount()):
                if self.twVideo1.cellWidget(row, 0).currentText() == "1":
                    flag_player1 = True
            
            if not flag_player1:
                QMessageBox.critical(self, programName , "The player #1 is not selected")
                self.cbVisualizeSpectrogram.setChecked(False)
                return
                
            if dialog.MessageDialog(programName, ("You choose to visualize the spectrogram for the media in player #1.<br>"
                                                  "Choose YES to generate the spectrogram.\n\n"
                                                  "Spectrogram generation can take some time for long media, be patient"), [YES, NO]) == YES:

                if not self.ffmpeg_cache_dir:
                    tmp_dir = tempfile.gettempdir()
                else:
                    tmp_dir = self.ffmpeg_cache_dir

                w = dialog.Info_widget()
                w.resize(350, 100)
                w.setWindowFlags(Qt.WindowStaysOnTopHint)
                w.setWindowTitle("BORIS")
                w.label.setText("Generating spectrogram...")

                for row in range(self.twVideo1.rowCount()):
                    # check if player 1
                    if self.twVideo1.cellWidget(row, 0).currentText() != "1":
                        continue

                    media_file_path = project_functions.media_full_path(self.twVideo1.item(row, MEDIA_FILE_PATH_IDX).text(), self.project_path)
                    if self.twVideo1.item(row, HAS_AUDIO_IDX).text() == "False":
                        QMessageBox.critical(self, programName , "The media file {} do not seem to have audio".format(media_file_path))
                        continue
                    
                    if os.path.isfile(media_file_path):
                        
                        process = plot_spectrogram.create_spectrogram_multiprocessing(mediaFile=media_file_path,
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
                        flag_spectro_produced = True
                    else:
                        QMessageBox.warning(self, programName , "<b>{}</b> file not found".format(media_file_path))
                
                if not flag_spectro_produced:
                    self.cbVisualizeSpectrogram.setChecked(False)
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
            """
            check if s is numeric (float)
            
            Args:
                s (str/int/float): value to test
                
            Returns:
                boolean: True if numeric else False
            """
            try:
                float(s)
                return True
            except ValueError:
                return False

        # check player number
        players_list = []
        players = {} # for storing duration
        for row in range(self.twVideo1.rowCount()):
            players_list.append(int(self.twVideo1.cellWidget(row, 0).currentText()))
            if int(self.twVideo1.cellWidget(row, 0).currentText()) not in players:
                players[int(self.twVideo1.cellWidget(row, 0).currentText())] = [utilities.time2seconds(self.twVideo1.item(row, 3).text())]
            else:
                players[int(self.twVideo1.cellWidget(row, 0).currentText())].append(utilities.time2seconds(self.twVideo1.item(row, 3).text()))

        print(players)

        # check if player#1 used
        if min(players_list) > 1:
            QMessageBox.critical(self, programName , "A media file must be loaded in player #1")
            return False
        # check if players are used in crescent order
        if set(list(range(min(players_list), max(players_list) + 1))) != set(players_list):
            QMessageBox.critical(self, programName , "Some player are not used. Please reorganize your media file")
            return False
        # check that longuest media is in player #1
        durations = []
        for i in players:
            durations.append(sum(players[i]))
        print(durations)
        if [x for x in durations[1:] if x > durations[0]]:
            QMessageBox.critical(self, programName , "The longuest media file(s) must be loaded in player #1")
            return False

        # check time offset
        if not is_numeric(self.leTimeOffset.text()):
            QMessageBox.critical(self, programName , "<b>{}</b> is not recognized as a valid time offset format".format(self.leTimeOffset.text()))
            return False

        # check if indep variables are correct type
        for row in range(self.twIndepVariables.rowCount()):
            if self.twIndepVariables.item(row, 1).text() == NUMERIC:
                if self.twIndepVariables.item(row, 2).text() and not is_numeric( self.twIndepVariables.item(row, 2).text() ):
                    QMessageBox.critical(self, programName,
                                         "The <b>{}</b> variable must be numeric!".format(self.twIndepVariables.item(row, 0).text()))
                    return False

        # check if observation id not empty
        if not self.leObservationId.text():
            QMessageBox.warning(self, programName , "The <b>observation id</b> is mandatory and must be unique!" )
            return False

        # check if new obs and observation id already present or if edit obs and id changed
        if (self.mode == "new") or (self.mode == "edit" and self.leObservationId.text() != self.mem_obs_id):
            if self.leObservationId.text() in self.pj[OBSERVATIONS]:
                QMessageBox.critical(self, programName,
                                     "The observation id <b>{0}</b> is already used!<br>{1}<br>{2}".format(self.leObservationId.text(),
                                                                                                           self.pj['observations'][self.leObservationId.text()]['description'],
                                                                                                           self.pj['observations'][self.leObservationId.text()]['date']))
                return False

        # check if media list #2 populated and media list #1 empty
        if self.tabProjectType.currentIndex() == 0 and not self.twVideo1.rowCount():
            QMessageBox.critical(self, programName , "Add a media file in the first media player!" )
            return False

        # check offset for external data files
        for row in range(self.tw_data_files.rowCount()):
            if not is_numeric(self.tw_data_files.item(row, PLOT_DATA_TIMEOFFSET_IDX).text()):
                QMessageBox.critical(self, programName,
                                     ("The external data file start value <b>{}</b> is not recognized as a numeric value.<br>"
                                     "Use decimal number of seconds (e.g. -58.5 or 32)").format(
                                     self.tw_data_files.item(row, PLOT_DATA_TIMEOFFSET_IDX).text()))
                return False
        
        for row in range(self.twIndepVariables.rowCount()):
            if self.twIndepVariables.item(row, 1).text() == NUMERIC:
                if self.twIndepVariables.item(row, 2).text() and not is_numeric( self.twIndepVariables.item(row, 2).text() ):
                    QMessageBox.critical(self, programName,
                                         "The <b>{}</b> variable must be numeric!".format(self.twIndepVariables.item(row, 0).text()))
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


    def check_media(self, n_player, file_path, flag_path):
        """
        check media and add them to list view if duration > 0
        
        Args:
            file_path (str): media file path to be checked
            flag_path (bool): True include full path of media else only basename
            
        Returns:
             bool: True if file is media else False
        """

        #nframes, videoDuration_ms, videoDuration_s, fps, hasVideo, hasAudio = accurate_media_analysis(self.ffmpeg_bin, file_path)
        r = utilities.accurate_media_analysis2(self.ffmpeg_bin, file_path)
        if "error" in r:
            return False
        else:
            if r["duration"] > 0:
                if not flag_path:
                    file_path = str(Path(file_path).name)
                self.mediaDurations[file_path] = r["duration"]
                self.mediaFPS[file_path] = r["fps"]
                self.mediaHasVideo[file_path] = r["has_video"]
                self.mediaHasAudio[file_path] = r["has_audio"]
                self.add_media_to_listview(n_player, file_path, "")
                return True
            else:
                return False


    def add_media(self, n_player, flag_path):
        """
        add media in player nPlayer
        
        Args:
            n_player (str): player
            flag_path (bool): True include full path of media else only basename
        """
        # check if more media in player1 before adding media to player2
        if n_player == PLAYER2 and self.twVideo1.rowCount() > 1:
            QMessageBox.critical(self, programName, ("It is not yet possible to play a second media "
                                                     "when more media are loaded in the first media player"))
            return

        fd = QFileDialog()
        fd.setDirectory(os.path.expanduser("~") if flag_path else str(Path(self.project_path).parent))

        fn = fd.getOpenFileNames(self, "Add media file(s)", "", "All files (*)")
        file_paths = fn[0] if type(fn) is tuple else fn

        if file_paths:
            for file_path in file_paths:
                if not self.check_media(n_player, file_path, flag_path):
                    QMessageBox.critical(self, programName, "The <b>{file_path}</b> file does not seem to be a media file.".format(
                                 file_path=file_path))

        self.cbVisualizeSpectrogram.setEnabled(self.twVideo1.rowCount() > 0)
        self.cbCloseCurrentBehaviorsBetweenVideo.setEnabled(self.twVideo1.rowCount() > 0)


    def add_media_from_dir(self, n_player, flag_path):
        """
        add all media from a selected directory

        Args:
            nPlayer (str): player
            flag_path (bool): True include full path of media else only basename
        """
        
        fd = QFileDialog(self)
        fd.setDirectory(os.path.expanduser("~") if flag_path else str(Path(self.project_path).parent))

        dir_name = fd.getExistingDirectory(self, "Select directory")
        if dir_name:
            r = ""
            for file_path in glob.glob(dir_name + os.sep + "*"):
                if not self.check_media(n_player, file_path, flag_path):
                    if r != "Skip all non media files":
                        r = dialog.MessageDialog(programName,
                                                 ("The <b>{file_path}</b> file does not seem to be a media file."
                                                  "").format(file_path=file_path),
                                                 ["Continue", "Skip all non media files", "Cancel"])
                        if r == "Cancel":
                            break


        self.cbVisualizeSpectrogram.setEnabled(self.twVideo1.rowCount() > 0)
        self.cbCloseCurrentBehaviorsBetweenVideo.setEnabled(self.twVideo1.rowCount() > 0)


    def add_media_to_listview(self, nPlayer, fileName, fileContentMD5):
        """
        add media file path to list widget
        """

        '''
        if not self.twVideo1.rowCount() and nPlayer == PLAYER2:
            QMessageBox.critical(self, programName, "Add the first media file to Player #1")
            return False

        if (self.twVideo1.rowCount() and self.twVideo2.rowCount()) or (self.twVideo2.rowCount() > 1):
            QMessageBox.critical(self, programName, ("It is not yet possible to play a second media "
                                                     "when more media are loaded in the first media player"))
            return False
        '''

        '''
        if nPlayer == PLAYER1:
            twVideo = self.twVideo1
        if nPlayer == PLAYER2:
            twVideo = self.twVideo2
        '''

        #twVideo = self.twVideo1

        self.twVideo1.setRowCount(self.twVideo1.rowCount() + 1)
        
        for col_idx, s in enumerate([None, 0, fileName, seconds2time(self.mediaDurations[fileName]), self.mediaFPS[fileName],
                                 self.mediaHasVideo[fileName], self.mediaHasAudio[fileName]]):
            if col_idx == 0: # player combobox
                combobox = QComboBox()
                combobox.addItems(ALL_PLAYERS)
                self.twVideo1.setCellWidget(self.twVideo1.rowCount() - 1, col_idx, combobox)
            else:
                item = QTableWidgetItem("{}".format(s))
                if col_idx != 1:  # only offset is editable by user
                    item.setFlags(Qt.ItemIsEnabled)

                self.twVideo1.setItem(self.twVideo1.rowCount() - 1, col_idx, item)


    def remove_data_file(self):
        """
        remove selected data file from list widget
        """
        if self.tw_data_files.selectedIndexes():
            self.tw_data_files.removeRow(self.tw_data_files.selectedIndexes()[0].row())
        else:
            QMessageBox.warning(self, programName, "Select a data file")

    def remove_media(self, nPlayer):
        """
        remove selected item from list widget
        """

        if self.twVideo1.selectedIndexes():
            mediaPath = self.twVideo1.item(self.twVideo1.selectedIndexes()[0].row(), 1).text()
            self.twVideo1.removeRow(self.twVideo1.selectedIndexes()[0].row())

            # FIXME ! check if media in same or other player
            if mediaPath not in [self.twVideo2.item(idx, 0).text() for idx in range(self.twVideo2.rowCount())]:
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

if __name__ == '__main__':

    import sys

    converters = {
  "convert_time_ecg":{
   "name":"convert_time_ecg",
   "description":"convert '%d/%m/%Y %H:%M:%S.%f' in seconds from epoch",
   "code":"\nimport datetime\nepoch = datetime.datetime.utcfromtimestamp(0)\ndatetime_format = \"%d/%m/%Y %H:%M:%S.%f\"\n\nOUTPUT = (datetime.datetime.strptime(INPUT, datetime_format) - epoch).total_seconds()\n"
  },
  "hhmmss_2_seconds":{
   "name":"hhmmss_2_seconds",
   "description":"convert HH:MM:SS in seconds",
   "code":"\nh, m, s = INPUT.split(':')\nOUTPUT = int(h) * 3600 + int(m) * 60 + int(s)\n\n"
  }
 }
    
    app = QApplication(sys.argv)
    w = Observation("/tmp", converters)
    w.ffmpeg_bin="ffmpeg"
    w.mode = "new"
    w.pj = """{
 "time_format":"hh:mm:ss",
 "project_date":"2018-05-23T14:05:50",
 "project_name":"",
 "project_description":"",
 "project_format_version":"4.0",
 "subjects_conf":{
  "0":{
   "key":"1",
   "name":"111",
   "description":""
  },
  "1":{
   "key":"2",
   "name":"222",
   "description":""
  }
 },
 "behaviors_conf":{
  "0":{
   "type":"Point event",
   "key":"P",
   "code":"p",
   "description":"",
   "category":"",
   "modifiers":"",
   "excluded":"",
   "coding map":""
  },
  "1":{
   "type":"Point event",
   "key":"S",
   "code":"s",
   "description":"",
   "category":"",
   "modifiers":"",
   "excluded":"",
   "coding map":""
  }
 },
 "observations":{
  "3video":{
   "file":{
    "1":[
     "/home/olivier/gdrive/ownCloud/media_files_boris/50FPS.mp4"
    ],
    "2":[
     "/home/olivier/gdrive/ownCloud/media_files_boris/60FPS.mp4"
    ],
    "3":[
     "/home/olivier/gdrive/ownCloud/media_files_boris/mire1.mp4"
    ]
   },
   "type":"MEDIA",
   "date":"2018-05-23T14:07:07",
   "description":"",
   "time offset":0.0,
   "events":[],
   "independent_variables":{},
   "time offset second player":0.0,
   "visualize_spectrogram":false,
   "close_behaviors_between_videos":false,
   "media_info":{
    "length":{
     "/home/olivier/gdrive/ownCloud/media_files_boris/mire1.mp4":180.27,
     "/home/olivier/gdrive/ownCloud/media_files_boris/50FPS.mp4":180.05,
     "/home/olivier/gdrive/ownCloud/media_files_boris/60FPS.mp4":180.05
    },
    "fps":{
     "/home/olivier/gdrive/ownCloud/media_files_boris/mire1.mp4":23.98,
     "/home/olivier/gdrive/ownCloud/media_files_boris/50FPS.mp4":50.0,
     "/home/olivier/gdrive/ownCloud/media_files_boris/60FPS.mp4":60.0
    },
    "hasVideo":{
     "/home/olivier/gdrive/ownCloud/media_files_boris/mire1.mp4":true,
     "/home/olivier/gdrive/ownCloud/media_files_boris/50FPS.mp4":true,
     "/home/olivier/gdrive/ownCloud/media_files_boris/60FPS.mp4":true
    },
    "hasAudio":{
     "/home/olivier/gdrive/ownCloud/media_files_boris/mire1.mp4":true,
     "/home/olivier/gdrive/ownCloud/media_files_boris/50FPS.mp4":true,
     "/home/olivier/gdrive/ownCloud/media_files_boris/60FPS.mp4":true
    }
   }
  },
  "dummy":{
   "file":{
    "1":[
     "/home/olivier/Videos/media_files/mire1.mp4"
    ],
    "2":[]
   },
   "type":"MEDIA",
   "date":"2018-05-23T14:10:10",
   "description":"",
   "time offset":0.0,
   "events":[],
   "independent_variables":{},
   "time offset second player":0.0,
   "visualize_spectrogram":false,
   "close_behaviors_between_videos":false,
   "media_info":{
    "length":{
     "/home/olivier/Videos/media_files/mire1.mp4":180.27
    },
    "fps":{
     "/home/olivier/Videos/media_files/mire1.mp4":23.98
    },
    "hasVideo":{
     "/home/olivier/Videos/media_files/mire1.mp4":true
    },
    "hasAudio":{
     "/home/olivier/Videos/media_files/mire1.mp4":true
    }
   }
  },
  "3video 2":{
   "file":{
    "1":[
     "video1.mp4"
    ],
    "2":[
     "video2.mp4"
    ],
    "3":[
     "video3.mp4"
    ]    
   },
   "type":"MEDIA",
   "date":"2018-05-24T01:16:47",
   "description":"",
   "time offset":0.0,
   "events":[],
   "independent_variables":{},
   "time offset second player":0.0,
   "visualize_spectrogram":false,
   "close_behaviors_between_videos":false,
   "media_info":{
    "length":{
     "video1.mp4":179.96,
     "video2.mp4":179.96,
     "video3.mp4":179.96
    },
    "fps":{
     "video1.mp4":25.0,
     "video2.mp4":25.0,
     "video3.mp4":25.0
    },
    "hasVideo":{
     "video1.mp4":true,
     "video2.mp4":true,
     "video3.mp4":true
    },
    "hasAudio":{
     "video1.mp4":false,
     "video2.mp4":false,
     "video3.mp4":true
    }
   }
  }
 },
 "behavioral_categories":[],
 "independent_variables":{},
 "coding_map":{},
 "behaviors_coding_map":[],
 "converters":{}
}

    
"""
    w.show()
    w.exec_()
    sys.exit()

