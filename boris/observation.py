"""
BORIS
Behavioral Observation Research Interactive Software
Copyright 2012-2023 Olivier Friard

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
import logging
import os
import pathlib as pl

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor
from PyQt5.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QLabel,
    QComboBox,
    QPushButton,
    QMessageBox,
    QSpacerItem,
    QSizePolicy,
    QFileDialog,
    QTableWidgetItem,
    QApplication,
    QMenu,
    QListWidgetItem,
)

from . import config as cfg
from . import dialog, duration_widget, plot_data_module, project_functions
from . import utilities as util
from . import gui_utilities
from .observation_ui import Ui_Form


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
    def __init__(self, tmp_dir, project_path="", converters={}, time_format=cfg.S, parent=None):
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
        self.mem_dir = ""
        self.test = None

        self.setupUi(self)

        # insert duration widget for time offset
        self.obs_time_offset = duration_widget.Duration_widget(0)
        self.horizontalLayout_6.insertWidget(1, self.obs_time_offset)

        # observation type
        self.rb_media_files.toggled.connect(self.obs_type_changed)
        self.rb_live.toggled.connect(self.obs_type_changed)
        self.rb_images.toggled.connect(self.obs_type_changed)

        menu_items = [
            "media abs path|with absolute path",
            "media rel path|with relative path",
            {
                "from directory": [
                    "dir abs path|with absolute path ",
                    "dir rel path|wih relative path ",
                ]
            },
        ]
        menu = QMenu()
        menu.triggered.connect(lambda x: self.add_media(mode=x.statusTip()))
        self.add_button_menu(menu_items, menu)
        self.pbAddVideo.setMenu(menu)

        self.pbRemoveVideo.clicked.connect(self.remove_media)

        # add data file
        data_menu_items = [
            "data abs path|with absolute path",
            "data rel path|with relative path",
        ]

        menu_data = QMenu()
        menu_data.triggered.connect(lambda x: self.add_data_file(mode=x.statusTip()))
        self.add_button_menu(data_menu_items, menu_data)
        self.pb_add_data_file.setMenu(menu_data)

        self.pb_remove_data_file.clicked.connect(self.remove_data_file)
        self.pb_view_data_head.clicked.connect(self.view_data_file_head)
        self.pb_plot_data.clicked.connect(self.plot_data_file)

        self.pb_use_media_file_name_as_obsid.clicked.connect(self.use_media_file_name_as_obsid)
        self.pb_use_img_dir_as_obsid.clicked.connect(self.use_img_dir_as_obsid)

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

        # images
        self.pb_add_directory.clicked.connect(self.add_images_directory)
        self.pb_remove_directory.clicked.connect(self.remove_images_directory)

        self.tabWidget.setCurrentIndex(0)

        # geometry
        gui_utilities.restore_geometry(self, "new observation", (800, 650))

    def use_media_file_name_as_obsid(self) -> None:
        """
        set observation id with the media file name value (without path)
        """
        if not self.twVideo1.rowCount():
            QMessageBox.critical(self, cfg.programName, "A media file must be loaded in player #1")
            return

        first_media_file = ""
        for row in range(self.twVideo1.rowCount()):
            if int(self.twVideo1.cellWidget(row, 0).currentText()) == 1:
                first_media_file = self.twVideo1.item(row, 2).text()
                break
        # check if player #1 is used
        if not first_media_file:
            QMessageBox.critical(self, cfg.programName, "A media file must be loaded in player #1")
            return

        self.leObservationId.setText(pl.Path(first_media_file).name)

    def use_img_dir_as_obsid(self) -> None:
        """
        set observation id with the images directory (without path)
        """

        if not self.lw_images_directory.count():
            QMessageBox.critical(self, cfg.programName, "You have to select at least one images directory")
            return

        self.leObservationId.setText(pl.Path(self.lw_images_directory.item(0).text()).name)

    def obs_type_changed(self) -> None:
        """
        change stacked widget page in base at the observation type
        """

        for idx, rb in enumerate([self.rb_media_files, self.rb_live, self.rb_images]):
            if rb.isChecked():
                self.sw_observation_type.setCurrentIndex(idx + 1)

    def add_images_directory(self):
        """
        add path to images directory
        """
        dir_path = QFileDialog.getExistingDirectory(None, "Select directory", os.getenv("HOME"))
        result = util.dir_images_number(dir_path)
        if not result.get("number of images", 0):
            response = dialog.MessageDialog(
                cfg.programName,
                "The directory does not contain images (*.jpg, *.jpeg, *.png)",
                ["Cancel", "Add directory"],
            )
            if response == "Cancel":
                return

        self.lw_images_directory.addItem(QListWidgetItem(dir_path))

    def remove_images_directory(self):
        """
        remove dir path from the list
        """
        self.lw_images_directory.takeItem(self.lw_images_directory.currentRow())

    def add_button_menu(self, data, menu_obj):
        """
        add menu option from dictionary
        """
        if isinstance(data, dict):
            for k, v in data.items():
                sub_menu = QMenu(k, menu_obj)
                menu_obj.addMenu(sub_menu)
                self.add_button_menu(v, sub_menu)
        elif isinstance(data, list):
            for element in data:
                self.add_button_menu(element, menu_obj)
        else:
            action = menu_obj.addAction(data.split("|")[1])
            # tips are used to discriminate the menu option
            action.setStatusTip(data.split("|")[0])
            action.setIconVisibleInMenu(False)

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
                    QMessageBox.critical(self, cfg.programName, "The stop time comes before the start time")
                    self.cb_observation_time_interval.setChecked(False)
                    return
                self.observation_time_interval = [start_time, stop_time]
                self.cb_observation_time_interval.setText(
                    f"Limit observation to a time interval: {start_time} - {stop_time}"
                )
        else:
            self.observation_time_interval = [0, 0]
            self.cb_observation_time_interval.setText("Limit observation to a time interval")

    def tw_data_files_cellDoubleClicked(self, row, column):
        """
        double click on "Converters column"
        """
        if column == cfg.PLOT_DATA_CONVERTERS_IDX:
            if self.tw_data_files.item(row, cfg.PLOT_DATA_COLUMNS_IDX).text():
                w = AssignConverter(
                    self.tw_data_files.item(row, cfg.PLOT_DATA_COLUMNS_IDX).text(),
                    self.converters,
                    eval(self.tw_data_files.item(row, cfg.PLOT_DATA_CONVERTERS_IDX).text())
                    if self.tw_data_files.item(row, cfg.PLOT_DATA_CONVERTERS_IDX).text()
                    else "",
                )

                if w.exec_():
                    d = {}
                    for col_idx, cb in zip(
                        self.tw_data_files.item(row, cfg.PLOT_DATA_COLUMNS_IDX).text().split(","), w.cbb
                    ):
                        if cb.currentText() != "None":
                            d[col_idx] = cb.currentText()
                    self.tw_data_files.item(row, cfg.PLOT_DATA_CONVERTERS_IDX).setText(str(d))
            else:
                QMessageBox.critical(self, cfg.programName, "Select the columns to plot (time,value)")

    def plot_data_file(self):
        """
        show plot
        check if data can be plotted
        """

        if self.pb_plot_data.text() != "Show plot":
            self.test.close_plot()
            # update button text
            self.pb_plot_data.setText("Show plot")
            return

        if self.tw_data_files.selectedIndexes() or self.tw_data_files.rowCount() == 1:

            if self.tw_data_files.rowCount() == 1:
                row_idx = 0
            else:
                row_idx = self.tw_data_files.selectedIndexes()[0].row()

            filename = self.tw_data_files.item(row_idx, cfg.PLOT_DATA_FILEPATH_IDX).text()
            columns_to_plot = self.tw_data_files.item(row_idx, cfg.PLOT_DATA_COLUMNS_IDX).text()
            plot_title = self.tw_data_files.item(row_idx, cfg.PLOT_DATA_PLOTTITLE_IDX).text()

            # load converters in dictionary
            if self.tw_data_files.item(row_idx, cfg.PLOT_DATA_CONVERTERS_IDX).text():
                column_converter = eval(self.tw_data_files.item(row_idx, cfg.PLOT_DATA_CONVERTERS_IDX).text())
            else:
                column_converter = {}

            variable_name = self.tw_data_files.item(row_idx, cfg.PLOT_DATA_VARIABLENAME_IDX).text()
            time_interval = int(self.tw_data_files.item(row_idx, cfg.PLOT_DATA_TIMEINTERVAL_IDX).text())
            time_offset = int(self.tw_data_files.item(row_idx, cfg.PLOT_DATA_TIMEOFFSET_IDX).text())

            substract_first_value = self.tw_data_files.cellWidget(
                row_idx, cfg.PLOT_DATA_SUBSTRACT1STVALUE_IDX
            ).currentText()

            plot_color = self.tw_data_files.cellWidget(row_idx, cfg.PLOT_DATA_PLOTCOLOR_IDX).currentText()

            data_file_path = project_functions.full_path(filename, self.project_path)

            if not data_file_path:
                QMessageBox.critical(
                    self,
                    cfg.programName,
                    (
                        f"Data file not found:\n{filename}\n"
                        "If the file path is not stored the data file "
                        "must be in the same directory than your project"
                    ),
                )
                return

            self.test = plot_data_module.Plot_data(
                data_file_path,
                time_interval,  # time interval
                time_offset,  # time offset
                plot_color,  # plot style
                plot_title,  # plot title
                variable_name,
                columns_to_plot,
                substract_first_value,
                self.converters,
                column_converter,
                log_level=logging.getLogger().getEffectiveLevel(),
            )

            if self.test.error_msg:
                QMessageBox.critical(self, cfg.programName, f"Impossible to plot data:\n{self.test.error_msg}")
                del self.test
                return

            # self.test.setWindowFlags(self.test.windowFlags() | Qt.WindowStaysOnTopHint)
            self.test.show()
            self.test.update_plot(0)
            # update button text
            self.pb_plot_data.setText("Close plot")

        else:
            QMessageBox.warning(self, cfg.programName, "Select a data file")

    def add_data_file(self, mode=True):
        """
        user select a data file to be plotted synchronously with media file

        Args:
            flag_path (bool): True to store path of data file else False
        """

        if mode.split("|")[0] not in (
            "data abs path",
            "data rel path",
        ):
            QMessageBox.critical(
                self,
                cfg.programName,
                (f"Wrong mode to add a data file {mode}"),
            )
            return

        # check if project saved
        if (" w/o" in mode or " rel " in mode) and (not self.project_file_name):
            QMessageBox.critical(
                self,
                cfg.programName,
                (
                    "It is not possible to add a data file without path or with a relative path if the project is not already saved"
                ),
            )
            return

        # limit to 2 files
        if self.tw_data_files.rowCount() >= 2:
            QMessageBox.warning(
                self,
                cfg.programName,
                (
                    "It is not yet possible to plot more than 2 external data sources"
                    "This limitation will be removed in future"
                ),
            )
            return

        fd = QFileDialog()
        fd.setDirectory(os.path.expanduser("~") if (" abs " in mode) else str(pl.Path(self.project_path).parent))

        fn = fd.getOpenFileName(self, "Add data file", "", "All files (*)")
        file_name = fn[0] if type(fn) is tuple else fn

        if file_name:

            columns_to_plot = "1,2"  # columns to plot by default

            # check data file
            r = util.check_txt_file(file_name)  # check_txt_file defined in utilities

            if "error" in r:
                QMessageBox.critical(self, cfg.programName, r["error"])
                return

            if not r["homogeneous"]:  # not all rows have 2 columns
                QMessageBox.critical(self, cfg.programName, "This file does not contain a constant number of columns")
                return

            header = util.return_file_header(file_name, row_number=10)

            if not header:
                return  # problem with header

            w = dialog.View_data_head()
            w.setWindowTitle(f"Data file: {pl.Path(file_name).name}")
            """w.setWindowFlags(Qt.WindowStaysOnTopHint)"""

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
                            QMessageBox.critical(
                                self, cfg.programName, f"<b>{col}</b> does not seem to be a column index"
                            )
                            flag_ok = False
                            break
                        if col_idx <= 0 or col_idx > r["fields number"]:
                            QMessageBox.critical(self, cfg.programName, f"<b>{col}</b> is not a valid column index")
                            flag_ok = False
                            break
                    if flag_ok:
                        break
                else:
                    return

            else:
                return

            self.tw_data_files.setRowCount(self.tw_data_files.rowCount() + 1)

            if " rel " in mode:

                try:
                    file_path = str(pl.Path(file_name).relative_to(pl.Path(self.project_path).parent))
                except ValueError:
                    QMessageBox.critical(
                        self,
                        cfg.programName,
                        f"The directory <b>{pl.Path(file_name).parent}</b> is not contained in <b>{pl.Path(self.project_path).parent}</b>.",
                    )
                    return

            else:  # save absolute path
                file_path = file_name

            for col_idx, value in zip(
                [
                    cfg.PLOT_DATA_FILEPATH_IDX,
                    cfg.PLOT_DATA_COLUMNS_IDX,
                    cfg.PLOT_DATA_PLOTTITLE_IDX,
                    cfg.PLOT_DATA_VARIABLENAME_IDX,
                    cfg.PLOT_DATA_CONVERTERS_IDX,
                    cfg.PLOT_DATA_TIMEINTERVAL_IDX,
                    cfg.PLOT_DATA_TIMEOFFSET_IDX,
                ],
                [file_path, columns_to_plot, "", "", "", "60", "0"],
            ):
                item = QTableWidgetItem(value)
                if col_idx == cfg.PLOT_DATA_CONVERTERS_IDX:
                    item.setFlags(Qt.ItemIsEnabled)
                    item.setBackground(QColor(230, 230, 230))
                self.tw_data_files.setItem(self.tw_data_files.rowCount() - 1, col_idx, item)

            # substract first value
            combobox = QComboBox()
            combobox.addItems(["True", "False"])
            self.tw_data_files.setCellWidget(
                self.tw_data_files.rowCount() - 1, cfg.PLOT_DATA_SUBSTRACT1STVALUE_IDX, combobox
            )

            # plot line color
            combobox = QComboBox()
            combobox.addItems(cfg.DATA_PLOT_STYLES)
            self.tw_data_files.setCellWidget(self.tw_data_files.rowCount() - 1, cfg.PLOT_DATA_PLOTCOLOR_IDX, combobox)

    def view_data_file_head(self):
        """
        view first parts of data file
        """

        if not self.tw_data_files.selectedIndexes() and self.tw_data_files.rowCount() != 1:
            QMessageBox.warning(self, cfg.programName, "Select a data file")

        if self.tw_data_files.rowCount() == 1:
            data_file_path = project_functions.full_path(self.tw_data_files.item(0, 0).text(), self.project_path)
            columns_to_plot = self.tw_data_files.item(0, 1).text()
        else:
            data_file_path = project_functions.full_path(
                self.tw_data_files.item(self.tw_data_files.selectedIndexes()[0].row(), 0).text(), self.project_path
            )
            columns_to_plot = self.tw_data_files.item(self.tw_data_files.selectedIndexes()[0].row(), 1).text()

        file_parameters = util.check_txt_file(data_file_path)
        if "error" in file_parameters:
            QMessageBox.critical(self, cfg.programName, f"Error on file {data_file_path}: {file_parameters['error']}")
            return
        header = util.return_file_header(data_file_path)

        if header:

            w = dialog.View_data_head()
            w.setWindowTitle(f"Data file: {pl.Path(data_file_path).name}")
            w.label.setText("Index of columns to plot")
            w.le.setEnabled(False)
            w.le.setText(columns_to_plot)
            w.pbCancel.setVisible(False)

            w.tw.setColumnCount(file_parameters["fields number"])
            w.tw.setRowCount(len(header))

            for row in range(len(header)):
                for col, v in enumerate(header[row].split(file_parameters["separator"])):
                    w.tw.setItem(row, col, QTableWidgetItem(v))

            w.exec_()

        else:
            QMessageBox.critical(self, cfg.programName, f"Error on file {data_file_path}")

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
                QMessageBox.critical(self, cfg.programName, "The player #1 is not selected")
                self.cbVisualizeSpectrogram.setChecked(False)
                self.cb_visualize_waveform.setChecked(False)
                return
            """
            if dialog.MessageDialog(programName, ("You choose to visualize the spectrogram or waveform for the media in player #1.<br>"
                                                  "The WAV will be extracted from the media files, be patient"), [YES, NO]) == YES:
            """
            if True:

                w = dialog.Info_widget()
                w.resize(350, 100)
                # w.setWindowFlags(Qt.WindowStaysOnTopHint)
                w.setWindowTitle("BORIS")
                w.label.setText("Extracting WAV from media files...")

                for row in range(self.twVideo1.rowCount()):
                    # check if player 1
                    if self.twVideo1.cellWidget(row, 0).currentText() != "1":
                        continue

                    media_file_path = project_functions.full_path(
                        self.twVideo1.item(row, cfg.MEDIA_FILE_PATH_IDX).text(), self.project_path
                    )
                    if self.twVideo1.item(row, cfg.HAS_AUDIO_IDX).text() == "False":
                        QMessageBox.critical(
                            self, cfg.programName, f"The media file {media_file_path} does not seem to have audio"
                        )
                        flag_wav_produced = False
                        break

                    if os.path.isfile(media_file_path):
                        w.show()
                        QApplication.processEvents()

                        if util.extract_wav(self.ffmpeg_bin, media_file_path, self.tmp_dir) == "":
                            QMessageBox.critical(
                                self,
                                cfg.programName,
                                f"Error during extracting WAV of the media file {media_file_path}",
                            )
                            flag_wav_produced = False
                            break

                        w.hide()

                        flag_wav_produced = True
                    else:
                        QMessageBox.warning(self, cfg.programName, f"<b>{media_file_path}</b> file not found")

                if not flag_wav_produced:
                    self.cbVisualizeSpectrogram.setChecked(False)
                    self.cb_visualize_waveform.setChecked(False)
            """
            else:
                self.cbVisualizeSpectrogram.setChecked(False)
                self.cb_visualize_waveform.setChecked(False)
            """

    def closeEvent(self, event):
        """
        close observation windows
        """
        if self.test is not None:
            self.test.close_plot()

    def pbCancel_clicked(self):
        """
        observation creation cancelled
        """
        if self.test is not None:
            self.test.close_plot()
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
            self.qm.setText("The <b>observation id</b> is mandatory and must be unique.")
            self.qm.exec_()
            return False

        # check if observation_type
        if not any((self.rb_media_files.isChecked(), self.rb_live.isChecked(), self.rb_images.isChecked())):
            self.qm = QMessageBox()
            self.qm.setIcon(QMessageBox.Critical)
            self.qm.setText("Choose an observation type.")
            self.qm.exec_()
            return False

        if self.rb_media_files.isChecked():  # observation based on media file(s)
            # check player number
            players_list = []
            players = {}  # for storing duration
            for row in range(self.twVideo1.rowCount()):
                players_list.append(int(self.twVideo1.cellWidget(row, 0).currentText()))
                if int(self.twVideo1.cellWidget(row, 0).currentText()) not in players:
                    players[int(self.twVideo1.cellWidget(row, 0).currentText())] = [
                        util.time2seconds(self.twVideo1.item(row, 3).text())
                    ]
                else:
                    players[int(self.twVideo1.cellWidget(row, 0).currentText())].append(
                        util.time2seconds(self.twVideo1.item(row, 3).text())
                    )

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
                QMessageBox.critical(
                    self,
                    cfg.programName,
                    (
                        "It is not possible to play another media synchronously "
                        "when many media are queued in the first media player"
                    ),
                )
                return False

            # check that the longuest media is in player #1
            durations = []
            for i in sorted(list(players.keys())):
                durations.append(sum(players[i]))
            if [x for x in durations[1:] if x > durations[0]]:
                QMessageBox.critical(self, cfg.programName, "The longuest media file(s) must be loaded in player #1")
                return False

            # check offset for media files
            for row in range(self.twVideo1.rowCount()):
                if not is_numeric(self.twVideo1.item(row, 1).text()):
                    QMessageBox.critical(
                        self,
                        cfg.programName,
                        (
                            "The offset value "
                            f"<b>{self.twVideo1.item(row, 1).text()}</b>"
                            " is not recognized as a numeric value.<br>"
                            "Use decimal number of seconds (e.g. -58.5 or 32)"
                        ),
                    )
                    return False

            # check offset for external data files
            for row in range(self.tw_data_files.rowCount()):
                if not is_numeric(self.tw_data_files.item(row, cfg.PLOT_DATA_TIMEOFFSET_IDX).text()):
                    QMessageBox.critical(
                        self,
                        cfg.programName,
                        (
                            "The external data file start value "
                            f"<b>{self.tw_data_files.item(row, cfg.PLOT_DATA_TIMEOFFSET_IDX).text()}</b>"
                            " is not recognized as a numeric value.<br>"
                            "Use decimal number of seconds (e.g. -58.5 or 32)"
                        ),
                    )
                    return False

        if self.rb_images.isChecked():  # observation based on images directory
            if not self.lw_images_directory.count():
                QMessageBox.critical(self, cfg.programName, "You have to select at least one images directory")
                return False

        # check if indep variables are correct type
        for row in range(self.twIndepVariables.rowCount()):
            if self.twIndepVariables.item(row, 1).text() == cfg.NUMERIC:
                if self.twIndepVariables.item(row, 2).text() and not is_numeric(
                    self.twIndepVariables.item(row, 2).text()
                ):
                    QMessageBox.critical(
                        self,
                        cfg.programName,
                        f"The <b>{self.twIndepVariables.item(row, 0).text()}</b> variable must be numeric!",
                    )
                    return False

        # check if new obs and observation id already present or if edit obs and id changed
        if (self.mode == "new") or (self.mode == "edit" and self.leObservationId.text() != self.mem_obs_id):
            if self.leObservationId.text() in self.pj[cfg.OBSERVATIONS]:
                QMessageBox.critical(
                    self,
                    cfg.programName,
                    (
                        f"The observation id <b>{self.leObservationId.text()}</b> is already used!<br>"
                        f"{self.pj[cfg.OBSERVATIONS][self.leObservationId.text()]['description']}<br>"
                        f"{self.pj[cfg.OBSERVATIONS][self.leObservationId.text()]['date']}"
                    ),
                )
                return False

        for row in range(self.twIndepVariables.rowCount()):
            if self.twIndepVariables.item(row, 1).text() == cfg.NUMERIC:
                if self.twIndepVariables.item(row, 2).text() and not is_numeric(
                    self.twIndepVariables.item(row, 2).text()
                ):
                    QMessageBox.critical(
                        self,
                        cfg.programName,
                        f"The <b>{self.twIndepVariables.item(row, 0).text()}</b> variable must be numeric!",
                    )
                    return False

        return True

    def pbLaunch_clicked(self):
        """
        Close window and start observation
        """

        if self.check_parameters():
            if self.test is not None:
                self.test.close_plot()
            self.done(2)

    def pbSave_clicked(self):
        """
        Close window and save observation
        """
        if self.check_parameters():
            self.state = "accepted"
            if self.test is not None:
                self.test.close_plot()
            self.accept()
        else:
            self.state = "refused"

    def check_media(self, file_path: str, mode: str) -> tuple:
        """
        check media and add them to list view if duration > 0

        Args:
            file_path (str): media file path to be checked
            mode (str): mode for adding media file

        Returns:
             bool: False if file is media else True
             str: error message or empty string
        """

        media_info = util.accurate_media_analysis(self.ffmpeg_bin, file_path)
        if "error" in media_info:
            return False, media_info["error"]
        else:
            if media_info["duration"] > 0:

                if " rel " in mode:
                    # convert to relative path (relative to BORIS project file)
                    file_path = str(pl.Path(file_path).relative_to(pl.Path(self.project_path).parent))

                self.mediaDurations[file_path] = float(media_info["duration"])
                self.mediaFPS[file_path] = float(media_info["fps"])
                self.mediaHasVideo[file_path] = media_info["has_video"]
                self.mediaHasAudio[file_path] = media_info["has_audio"]
                self.add_media_to_listview(file_path)
                return (False, "")
            else:
                return (True, "Media duration not available")

    def add_media(self, mode: str):
        """
        add media

        Args:
            mode (str): mode for adding the media file
        """

        if mode.split("|")[0] not in (
            "media abs path",
            "media rel path",
            "dir abs path",
            "dir rel path",
        ):
            QMessageBox.critical(
                self,
                cfg.programName,
                (f"Wrong mode to add media {mode}"),
            )
            return

        # check if project saved
        if (" w/o" in mode or " rel " in mode) and (not self.project_file_name):
            QMessageBox.critical(
                self,
                cfg.programName,
                (
                    "It is not possible to add a media file without path or with a relative path if the project is not already saved"
                ),
            )
            return

        fd = QFileDialog()
        if self.mem_dir:
            fd.setDirectory(self.mem_dir if (" abs " in mode) else str(pl.Path(self.project_path).parent))
        else:
            fd.setDirectory(os.path.expanduser("~") if (" abs " in mode) else str(pl.Path(self.project_path).parent))

        if "media " in mode:

            fn = fd.getOpenFileNames(self, "Add media file(s)", "", "All files (*)")
            file_paths = fn[0] if type(fn) is tuple else fn

            if file_paths:
                # store directory for next usage
                self.mem_dir = str(pl.Path(file_paths[0]).parent)
                # check if media dir in contained in the BORIS file project dir
                if " rel " in mode:
                    try:
                        pl.Path(file_paths[0]).parent.relative_to(pl.Path(self.project_path).parent)
                    except ValueError:
                        QMessageBox.critical(
                            self,
                            cfg.programName,
                            f"The directory <b>{pl.Path(file_paths[0]).parent}</b> is not contained in <b>{pl.Path(self.project_path).parent}</b>.",
                        )
                        return

                for file_path in file_paths:
                    (error, msg) = self.check_media(file_path, mode)
                    if error:
                        QMessageBox.critical(self, cfg.programName, f"<b>{file_path}</b>. {msg}")

        if "dir " in mode:

            dir_name = fd.getExistingDirectory(self, "Select directory")
            if dir_name:
                response = ""
                for file_path in glob.glob(dir_name + os.sep + "*"):
                    (error, msg) = self.check_media(file_path, mode)
                    if error:
                        if response != "Skip all non media files":
                            response = dialog.MessageDialog(
                                cfg.programName,
                                f"<b>{file_path}</b> {msg}",
                                ["Continue", "Skip all non media files", "Cancel"],
                            )
                            if response == "Cancel":
                                break

        for w in [
            self.cbVisualizeSpectrogram,
            self.cb_visualize_waveform,
            self.cb_observation_time_interval,
            self.cbCloseCurrentBehaviorsBetweenVideo,
        ]:
            w.setEnabled(self.twVideo1.rowCount() > 0)

        # disabled for problems
        self.cbCloseCurrentBehaviorsBetweenVideo.setEnabled(False)

    def add_media_to_listview(self, file_name):
        """
        add media file path to list widget
        """

        self.twVideo1.setRowCount(self.twVideo1.rowCount() + 1)

        for col_idx, s in enumerate(
            (
                None,
                0,
                file_name,
                util.seconds2time(self.mediaDurations[file_name]),
                f"{self.mediaFPS[file_name]:.2f}",
                self.mediaHasVideo[file_name],
                self.mediaHasAudio[file_name],
            )
        ):
            if col_idx == 0:  # player combobox
                combobox = QComboBox()
                combobox.addItems(cfg.ALL_PLAYERS)
                self.twVideo1.setCellWidget(self.twVideo1.rowCount() - 1, col_idx, combobox)
            else:
                item = QTableWidgetItem(f"{s}")
                if col_idx != 1:  # only offset is editable by user
                    item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)

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
            QMessageBox.warning(self, cfg.programName, "No data file selected")

    def remove_media(self):
        """
        remove all selected media files from list widget
        """

        if self.twVideo1.selectedIndexes():
            rows_to_delete = set([x.row() for x in self.twVideo1.selectedIndexes()])
            for row in sorted(rows_to_delete, reverse=True):
                media_path = self.twVideo1.item(row, cfg.MEDIA_FILE_PATH_IDX).text()
                self.twVideo1.removeRow(row)
                if media_path not in [
                    self.twVideo1.item(idx, cfg.MEDIA_FILE_PATH_IDX).text() for idx in range(self.twVideo1.rowCount())
                ]:
                    try:
                        del self.mediaDurations[media_path]
                    except NameError:
                        pass
                    try:
                        del self.mediaFPS[media_path]
                    except NameError:
                        pass

            for w in [
                self.cbVisualizeSpectrogram,
                self.cb_visualize_waveform,
                self.cb_observation_time_interval,
                self.cbCloseCurrentBehaviorsBetweenVideo,
            ]:
                w.setEnabled(self.twVideo1.rowCount() > 0)

            # disabled for problems
            self.cbCloseCurrentBehaviorsBetweenVideo.setEnabled(False)

        else:
            QMessageBox.warning(self, cfg.programName, "No media file selected")
