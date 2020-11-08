"""
BORIS
Behavioral Observation Research Interactive Software
Copyright 2012-2020 Olivier Friard

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


import glob
import hashlib
import logging
import os
import tempfile
import time
from pathlib import Path

import numpy
from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

from boris import dialog
from boris import duration_widget
from boris import plot_data_module
from boris import project_functions
from boris import utilities
from boris.config import *
from boris.observation_ui import Ui_Form
from boris.utilities import *


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
            hbox.addWidget(QLabel(f"Column #{column_idx}:"))
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

    def __init__(self, tmp_dir, project_path="", converters={}, time_format=S, parent=None):
        """
        Args:
            tmp_dir (str): path of temporary directory
            project_path (str): path of project
            converters (dict): converters dictionary
        """

        super().__init__()

        self.tmp_dir = tmp_dir
        self.project_path = project_path
        self.converters = converters
        self.time_format = time_format
        self.observation_time_interval = [0, 0]

        self.setupUi(self)

        # insert duration widget for time offset
        self.obs_time_offset = duration_widget.Duration_widget(0)
        self.horizontalLayout_6.insertWidget(1, self.obs_time_offset)

        self.pbAddVideo.clicked.connect(lambda: self.add_media(flag_path=True))
        self.pb_add_media_without_path.clicked.connect(lambda: self.add_media(flag_path=False))
        self.pbRemoveVideo.clicked.connect(self.remove_media)
        self.pbAddMediaFromDir.clicked.connect(lambda: self.add_media_from_dir(flag_path=True))
        self.pb_add_all_media_from_dir_without_path.clicked.connect(lambda: self.add_media_from_dir(flag_path=False))

        self.pb_add_data_file.clicked.connect(lambda: self.add_data_file(flag_path=True))
        self.pb_add_data_file_wo_path.clicked.connect(lambda: self.add_data_file(flag_path=False))
        self.pb_remove_data_file.clicked.connect(self.remove_data_file)
        self.pb_view_data_head.clicked.connect(self.view_data_file_head)
        self.pb_plot_data.clicked.connect(self.plot_data_file)

        self.cbVisualizeSpectrogram.clicked.connect(self.extract_wav)
        self.cb_visualize_waveform.clicked.connect(self.extract_wav)
        self.cb_observation_time_interval.clicked.connect(self.limit_time_interval)

        self.pbSave.clicked.connect(self.pbSave_clicked)
        self.pbLaunch.clicked.connect(self.pbLaunch_clicked)
        self.pbCancel.clicked.connect(self.pbCancel_clicked)

        self.tw_data_files.cellDoubleClicked[int, int].connect(self.tw_data_files_cellDoubleClicked)

        self.mediaDurations, self.mediaFPS, self.mediaHasVideo, self.mediaHasAudio = {}, {}, {}, {}

        self.cbVisualizeSpectrogram.setEnabled(False)
        self.cb_visualize_waveform.setEnabled(False)
        self.cb_observation_time_interval.setEnabled(True)

        # disabled due to problem when video goes back
        self.cbCloseCurrentBehaviorsBetweenVideo.setChecked(False)
        self.cbCloseCurrentBehaviorsBetweenVideo.setEnabled(False)

        self.cb_start_from_current_time.stateChanged.connect(self.cb_start_from_current_time_changed)

        self.tabWidget.setCurrentIndex(0)


    def cb_start_from_current_time_changed(self):
        """
        enable/disable radiobox for type of time selection
        """
        self.rb_day_time.setEnabled(self.cb_start_from_current_time.isChecked())
        self.rb_epoch_time.setEnabled(self.cb_start_from_current_time.isChecked())

    def limit_time_interval(self):
        """
        ask user a time interval for limiting the media observation
        """

        if self.cb_observation_time_interval.isChecked():
            time_interval_dialog = dialog.Ask_time(self.time_format)
            time_interval_dialog.time_widget.set_time(0)
            time_interval_dialog.setWindowTitle("Start observation at")
            time_interval_dialog.label.setText("Start observation at")
            start_time, stop_time = 0, 0
            if time_interval_dialog.exec_():
                start_time = time_interval_dialog.time_widget.get_time()
            else:
                self.cb_observation_time_interval.setChecked(False)
                return
            time_interval_dialog.time_widget.set_time(0)
            time_interval_dialog.setWindowTitle("Stop observation at")
            time_interval_dialog.label.setText("Stop observation at")
            if time_interval_dialog.exec_():
                stop_time = time_interval_dialog.time_widget.get_time()
            else:
                self.cb_observation_time_interval.setChecked(False)
                return

            if start_time or stop_time:
                if stop_time <= start_time:
                    QMessageBox.critical(self, programName, "The stop time comes before the start time")
                    self.cb_observation_time_interval.setChecked(False)
                    return
                self.observation_time_interval = [start_time, stop_time]
                self.cb_observation_time_interval.setText(f"Limit observation to a time interval: {start_time} - {stop_time}")
        else:
            self.observation_time_interval = [0, 0]
            self.cb_observation_time_interval.setText("Limit observation to a time interval")


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
        show plot
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
                else:
                    column_converter = {}

                variable_name  = self.tw_data_files.item(row_idx, PLOT_DATA_VARIABLENAME_IDX).text()
                time_interval = int(self.tw_data_files.item(row_idx, PLOT_DATA_TIMEINTERVAL_IDX).text())
                time_offset = int(self.tw_data_files.item(row_idx, PLOT_DATA_TIMEOFFSET_IDX).text())

                substract_first_value = self.tw_data_files.cellWidget(row_idx, PLOT_DATA_SUBSTRACT1STVALUE_IDX).currentText()

                plot_color = self.tw_data_files.cellWidget(row_idx, PLOT_DATA_PLOTCOLOR_IDX).currentText()

                data_file_path = project_functions.media_full_path(filename, self.project_path)

                if not data_file_path:
                    QMessageBox.critical(self, programName, (f"Data file not found:\n{filename}\n"
                                                             "If the file path is not stored the data file "
                                                             "must be in the same directory than your project"))
                    return

                self.test = plot_data_module.Plot_data(data_file_path,
                                                  time_interval,  # time interval
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
                    QMessageBox.critical(self, programName, f"Impossible to plot data:\n{self.test.error_msg}")
                    del self.test
                    return

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
            flag_path (bool): True to store path of data file else False
        """

        # check if project saved
        if (not flag_path) and (not self.project_file_name):
            QMessageBox.critical(self, programName, ("It is not possible to add data file without full path "
                                                     "if the project is not saved"))
            return

        # limit to 2 files
        if self.tw_data_files.rowCount() >= 2:
            QMessageBox.warning(self, programName, ("It is not yet possible to plot more than 2 external data sources"
                                                    "This limitation will be removed in future"))
            return

        fd = QFileDialog()
        fd.setDirectory(os.path.expanduser("~") if flag_path else str(Path(self.project_path).parent))

        fn = fd.getOpenFileName(self, "Add data file", "", "All files (*)")
        file_name = fn[0] if type(fn) is tuple else fn

        if file_name:

            columns_to_plot = "1,2"  # columns to plot by default

            # check data file
            r = utilities.check_txt_file(file_name)  # check_txt_file defined in utilities

            if "error" in r:
                QMessageBox.critical(self, programName, r["error"])
                return

            if not r["homogeneous"]:  # not all rows have 2 columns
                QMessageBox.critical(self, programName, "This file does not contain a constant number of columns")
                return

            header = utilities.return_file_header(file_name, row_number=10)

            if header:
                w = dialog.View_data_head()
                w.setWindowTitle(f"Data file: {Path(file_name).name}")
                #w.setWindowFlags(Qt.WindowStaysOnTopHint)

                w.tw.setColumnCount(r["fields number"])
                w.tw.setRowCount(len(header))

                for row in range(len(header)):
                    for col, v in enumerate(header[row].split(r["separator"])):
                        item = QTableWidgetItem(v)
                        item.setFlags(Qt.ItemIsEnabled)
                        w.tw.setItem(row, col, item)

                while True:
                    flag_ok = True
                    if w.exec_():
                        columns_to_plot = w.le.text().replace(" ", "")
                        for col in columns_to_plot.split(","):
                            try:
                                col_idx = int(col)
                            except ValueError:
                                QMessageBox.critical(self, programName, f"<b>{col}</b> does not seem to be a column index")
                                flag_ok = False
                                break
                            if col_idx <= 0 or col_idx > r["fields number"]:
                                QMessageBox.critical(self, programName, f"<b>{col}</b> is not a valid column index")
                                flag_ok = False
                                break
                        if flag_ok:
                            break
                    else:
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
                    item.setBackground(QColor(230, 230, 230))
                self.tw_data_files.setItem(self.tw_data_files.rowCount() - 1, col_idx, item)

            # substract first value
            combobox = QComboBox()
            combobox.addItems(["True", "False"])
            self.tw_data_files.setCellWidget(self.tw_data_files.rowCount() - 1, PLOT_DATA_SUBSTRACT1STVALUE_IDX, combobox)

            # plot line color
            combobox = QComboBox()
            combobox.addItems(DATA_PLOT_STYLES)
            self.tw_data_files.setCellWidget(self.tw_data_files.rowCount() - 1, PLOT_DATA_PLOTCOLOR_IDX, combobox)


    def view_data_file_head(self):
        """
        view first parts of data file
        """
        if self.tw_data_files.selectedIndexes() or self.tw_data_files.rowCount() == 1:
            if self.tw_data_files.rowCount() == 1:
                data_file_path = project_functions.media_full_path(self.tw_data_files.item(0, 0).text(), self.project_path)
            else:
                data_file_path = project_functions.media_full_path(self.tw_data_files.item(
                                                                       self.tw_data_files.selectedIndexes()[0].row(), 0).text(),
                                                                       self.project_path)

            file_parameters = utilities.check_txt_file(data_file_path)
            if "error" in file_parameters:
                QMessageBox.critical(self, programName,
                                     f"Error on file {data_file_path}: {file_parameters['error']}")
                return
            header = utilities.return_file_header(data_file_path)

            if header:

                w = dialog.View_data_head()
                w.setWindowTitle(f"Data file: {Path(data_file_path).name}")
                w.setWindowFlags(Qt.WindowStaysOnTopHint)
                w.label.setVisible(False)
                w.le.setVisible(False)

                w.tw.setColumnCount(file_parameters["fields number"])
                w.tw.setRowCount(len(header))

                for row in range(len(header)):
                    for col, v in enumerate(header[row].split(file_parameters["separator"])):
                        w.tw.setItem(row, col, QTableWidgetItem(v))

                w.exec_()

            else:
                QMessageBox.critical(self, programName, f"Error on file {data_file_path}")

        else:
            QMessageBox.warning(self, programName, "Select a data file")


    def extract_wav(self):
        """
        extract wav of all media files loaded in player #1
        """

        if self.cbVisualizeSpectrogram.isChecked() or self.cb_visualize_waveform.isChecked():
            flag_wav_produced = False
            # check if player 1 is selected
            flag_player1 = False
            for row in range(self.twVideo1.rowCount()):
                if self.twVideo1.cellWidget(row, 0).currentText() == "1":
                    flag_player1 = True

            if not flag_player1:
                QMessageBox.critical(self, programName, "The player #1 is not selected")
                self.cbVisualizeSpectrogram.setChecked(False)
                self.cb_visualize_waveform.setChecked(False)
                return

            '''
            if dialog.MessageDialog(programName, ("You choose to visualize the spectrogram or waveform for the media in player #1.<br>"
                                                  "The WAV will be extracted from the media files, be patient"), [YES, NO]) == YES:
            '''
            if True:

                w = dialog.Info_widget()
                w.resize(350, 100)
                w.setWindowFlags(Qt.WindowStaysOnTopHint)
                w.setWindowTitle("BORIS")
                w.label.setText("Extracting WAV from media files...")

                for row in range(self.twVideo1.rowCount()):
                    # check if player 1
                    if self.twVideo1.cellWidget(row, 0).currentText() != "1":
                        continue

                    media_file_path = project_functions.media_full_path(self.twVideo1.item(row, MEDIA_FILE_PATH_IDX).text(),
                                                                        self.project_path)
                    if self.twVideo1.item(row, HAS_AUDIO_IDX).text() == "False":
                        QMessageBox.critical(self, programName, f"The media file {media_file_path} do not seem to have audio")
                        flag_wav_produced = False
                        break

                    if os.path.isfile(media_file_path):
                        w.show()
                        QApplication.processEvents()

                        if utilities.extract_wav(self.ffmpeg_bin, media_file_path, self.tmp_dir) == "":
                            QMessageBox.critical(self, programName,
                                                 f"Error during extracting WAV of the media file {media_file_path}")
                            flag_wav_produced = False
                            break

                        w.hide()

                        flag_wav_produced = True
                    else:
                        QMessageBox.warning(self, programName, f"<b>{media_file_path}</b> file not found")

                if not flag_wav_produced:
                    self.cbVisualizeSpectrogram.setChecked(False)
                    self.cb_visualize_waveform.setChecked(False)
            '''
            else:
                self.cbVisualizeSpectrogram.setChecked(False)
                self.cb_visualize_waveform.setChecked(False)
            '''


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

        # check if observation id not empty
        if not self.leObservationId.text():
            self.qm = QMessageBox()
            self.qm.setIcon(QMessageBox.Critical)
            self.qm.setText("The <b>observation id</b> is mandatory and must be unique!")
            self.qm.exec_()
            return False


        if self.tabProjectType.currentIndex() == 0:  # observation based on media file
            # check player number
            players_list = []
            players = {}  # for storing duration
            for row in range(self.twVideo1.rowCount()):
                players_list.append(int(self.twVideo1.cellWidget(row, 0).currentText()))
                if int(self.twVideo1.cellWidget(row, 0).currentText()) not in players:
                    players[int(self.twVideo1.cellWidget(row, 0).currentText())] = [
                        utilities.time2seconds(self.twVideo1.item(row, 3).text())
                    ]
                else:
                    players[int(self.twVideo1.cellWidget(row, 0).currentText())].append(
                        utilities.time2seconds(self.twVideo1.item(row, 3).text()))

            # check if player #1 is used
            if not players_list or min(players_list) > 1:
                self.qm = QMessageBox()
                self.qm.setIcon(QMessageBox.Critical)
                self.qm.setText("A media file must be loaded in player #1")
                self.qm.exec_()
                return False

            # check if players are used in crescent order
            if set(list(range(min(players_list), max(players_list) + 1))) != set(players_list):
                self.qm = QMessageBox()
                self.qm.setIcon(QMessageBox.Critical)
                self.qm.setText("Some player are not used. Please reorganize your media files")
                self.qm.exec_()
                return False

            # check if more media in player #1 and media in other players
            if len(players[1]) > 1 and set(players.keys()) != {1}:
                self.qm = QMessageBox()
                self.qm.setIcon(QMessageBox.Critical)
                self.qm.setText(("It is not possible to play another media synchronously "
                                 "when many media are queued in the first media player"))
                self.qm.exec_()
                return False

            # check that the longuest media is in player #1
            durations = []
            for i in sorted(list(players.keys())):
                durations.append(sum(players[i]))
            if [x for x in durations[1:] if x > durations[0]]:
                QMessageBox.critical(self, programName, "The longuest media file(s) must be loaded in player #1")
                return False

            # check offset for media files
            for row in range(self.twVideo1.rowCount()):
                if not is_numeric(self.twVideo1.item(row, 1).text()):
                    QMessageBox.critical(self, programName,
                                         ("The offset value "
                                          f"<b>{self.twVideo1.item(row, 1).text()}</b>"
                                          " is not recognized as a numeric value.<br>"
                                          "Use decimal number of seconds (e.g. -58.5 or 32)"))
                    return False

            # check offset for external data files
            for row in range(self.tw_data_files.rowCount()):
                if not is_numeric(self.tw_data_files.item(row, PLOT_DATA_TIMEOFFSET_IDX).text()):
                    QMessageBox.critical(self, programName,
                                         ("The external data file start value "
                                          f"<b>{self.tw_data_files.item(row, PLOT_DATA_TIMEOFFSET_IDX).text()}</b>"
                                          " is not recognized as a numeric value.<br>"
                                          "Use decimal number of seconds (e.g. -58.5 or 32)"))
                    return False


        # check if indep variables are correct type
        for row in range(self.twIndepVariables.rowCount()):
            if self.twIndepVariables.item(row, 1).text() == NUMERIC:
                if self.twIndepVariables.item(row, 2).text() and not is_numeric(self.twIndepVariables.item(row, 2).text()):
                    QMessageBox.critical(self, programName,
                                         f"The <b>{self.twIndepVariables.item(row, 0).text()}</b> variable must be numeric!")
                    return False

        # check if new obs and observation id already present or if edit obs and id changed
        if (self.mode == "new") or (self.mode == "edit" and self.leObservationId.text() != self.mem_obs_id):
            if self.leObservationId.text() in self.pj[OBSERVATIONS]:
                QMessageBox.critical(self, programName,
                                     (f"The observation id <b>{self.leObservationId.text(),}</b> is already used!<br>"
                                      f"{self.pj[OBSERVATIONS][self.leObservationId.text()]['description']}<br>"
                                      f"{self.pj[OBSERVATIONS][self.leObservationId.text()]['date']}"))
                return False



        for row in range(self.twIndepVariables.rowCount()):
            if self.twIndepVariables.item(row, 1).text() == NUMERIC:
                if self.twIndepVariables.item(row, 2).text() and not is_numeric(self.twIndepVariables.item(row, 2).text()):
                    QMessageBox.critical(self, programName,
                                         f"The <b>{self.twIndepVariables.item(row, 0).text()}</b> variable must be numeric!")
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
            self.state = "accepted"
            self.accept()
        else:
            self.state = "refused"


    def check_media(self, file_path, flag_path):
        """
        check media and add them to list view if duration > 0

        Args:
            file_path (str): media file path to be checked
            flag_path (bool): True include full path of media else only basename

        Returns:
             bool: True if file is media else False
             str: error message or empty string
        """

        r = utilities.accurate_media_analysis(self.ffmpeg_bin, file_path)
        if "error" in r:
            return False, r["error"]
        else:
            if r["duration"] > 0:
                if not flag_path:
                    file_path = str(Path(file_path).name)
                self.mediaDurations[file_path] = float(r["duration"])
                self.mediaFPS[file_path] = float(r["fps"])
                self.mediaHasVideo[file_path] = r["has_video"]
                self.mediaHasAudio[file_path] = r["has_audio"]
                self.add_media_to_listview(file_path)
                return True, ""
            else:
                return False, "duration not available"


    def add_media(self, flag_path):
        """
        add media

        Args:
            flag_path (bool): if True include full path of media else only basename
        """

        # check if project saved
        if (not flag_path) and (not self.project_file_name):
            QMessageBox.critical(self, programName, ("It is not possible to add media without full path "
                                                     "if the project is not saved"))
            return

        # check if more media in player1 before adding media to player2
        '''
        if n_player == PLAYER2 and self.twVideo1.rowCount() > 1:
            QMessageBox.critical(self, programName, ("It is not yet possible to play a second media "
                                                     "when more media are loaded in the first media player"))
            return
        '''

        fd = QFileDialog()
        fd.setDirectory(os.path.expanduser("~") if flag_path else str(Path(self.project_path).parent))

        fn = fd.getOpenFileNames(self, "Add media file(s)", "", "All files (*)")
        file_paths = fn[0] if type(fn) is tuple else fn

        if file_paths:
            for file_path in file_paths:
                r, msg = self.check_media(file_path, flag_path)
                if not r:
                    QMessageBox.critical(self, programName,
                                         f"<b>{file_path}</b>. {msg}")

        for w in [self.cbVisualizeSpectrogram, self.cb_visualize_waveform,
                  self.cb_observation_time_interval, self.cbCloseCurrentBehaviorsBetweenVideo]:
            w.setEnabled(self.twVideo1.rowCount() > 0)

        # disabled for problems
        self.cbCloseCurrentBehaviorsBetweenVideo.setEnabled(False)


    def add_media_from_dir(self, flag_path):
        """
        add all media from a selected directory

        Args:
            flag_path (bool): True include full path of media else only basename
        """

        # check if project saved
        if (not flag_path) and (not self.project_file_name):
            QMessageBox.critical(self, programName, ("It is not possible to add media without full path "
                                                     "if the project is not saved"))
            return

        fd = QFileDialog()
        fd.setDirectory(os.path.expanduser("~") if flag_path else str(Path(self.project_path).parent))

        dir_name = fd.getExistingDirectory(self, "Select directory")
        if dir_name:
            r, response = "", ""
            for file_path in glob.glob(dir_name + os.sep + "*"):
                r, msg = self.check_media(file_path, flag_path)
                if not r:
                    if response != "Skip all non media files":
                        response = dialog.MessageDialog(programName,
                                                 f"<b>{file_path}</b> {msg}",
                                                 ["Continue", "Skip all non media files", "Cancel"])
                        if response == "Cancel":
                            break

        for w in [self.cbVisualizeSpectrogram, self.cb_visualize_waveform,
                  self.cb_observation_time_interval, self.cbCloseCurrentBehaviorsBetweenVideo]:
            w.setEnabled(self.twVideo1.rowCount() > 0)

        # disabled for problems
        self.cbCloseCurrentBehaviorsBetweenVideo.setEnabled(False)


    def add_media_to_listview(self, file_name):
        """
        add media file path to list widget
        """

        self.twVideo1.setRowCount(self.twVideo1.rowCount() + 1)

        for col_idx, s in enumerate([None,
                                     0,
                                     file_name,
                                     seconds2time(self.mediaDurations[file_name]),
                                     f"{self.mediaFPS[file_name]:.2f}",
                                     self.mediaHasVideo[file_name],
                                     self.mediaHasAudio[file_name]]):
            if col_idx == 0:  # player combobox
                combobox = QComboBox()
                combobox.addItems(ALL_PLAYERS)
                self.twVideo1.setCellWidget(self.twVideo1.rowCount() - 1, col_idx, combobox)
            else:
                item = QTableWidgetItem(f"{s}")
                if col_idx != 1:  # only offset is editable by user
                    item.setFlags(Qt.ItemIsEnabled)

                self.twVideo1.setItem(self.twVideo1.rowCount() - 1, col_idx, item)


    def remove_data_file(self):
        """
        remove all selected data file from list widget
        """
        if self.tw_data_files.selectedIndexes():
            rows_to_delete = set([x.row() for x in self.tw_data_files.selectedIndexes()])
            for row in sorted(rows_to_delete, reverse=True):
                self.tw_data_files.removeRow(row)
        else:
            QMessageBox.warning(self, programName, "No data file selected")


    def remove_media(self):
        """
        remove all selected media files from list widget
        """

        if self.twVideo1.selectedIndexes():
            rows_to_delete = set([x.row() for x in self.twVideo1.selectedIndexes()])
            for row in sorted(rows_to_delete, reverse=True):
                media_path = self.twVideo1.item(row, MEDIA_FILE_PATH_IDX).text()
                self.twVideo1.removeRow(row)
                if media_path not in [self.twVideo1.item(idx, MEDIA_FILE_PATH_IDX).text() for idx in range(self.twVideo1.rowCount())]:
                    try:
                        del self.mediaDurations[mediaPath]
                    except NameError:
                        pass
                    try:
                        del self.mediaFPS[mediaPath]
                    except NameError:
                        pass

            for w in [self.cbVisualizeSpectrogram, self.cb_visualize_waveform,
                      self.cb_observation_time_interval, self.cbCloseCurrentBehaviorsBetweenVideo]:
                w.setEnabled(self.twVideo1.rowCount() > 0)

            # disabled for problems
            self.cbCloseCurrentBehaviorsBetweenVideo.setEnabled(False)

        else:
            QMessageBox.warning(self, programName, "No media file selected")
