"""
BORIS
Behavioral Observation Research Interactive Software
Copyright 2012-2022 Olivier Friard

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

from math import log2
import os
import logging
import time
import tempfile
from decimal import Decimal as dec
import pathlib as pl
import datetime
from PyQt5.QtWidgets import (
    QMessageBox,
    QFileDialog,
    QDateTimeEdit,
    QComboBox,
    QTableWidgetItem,
    QSlider,
    QMainWindow,
    QDockWidget,
)
from PyQt5.QtCore import Qt, QDateTime, QTimer
from PyQt5.QtGui import QFont, QIcon

from PyQt5 import QtTest

from . import menu_options
from . import config as cfg
from . import dialog
from . import select_observations
from . import project_functions
from . import observation
from . import utilities as util
from . import plot_data_module
from . import player_dock_widget


def export_observations_list_clicked(self):
    """
    export the list of observations
    """

    resultStr, selected_observations = select_observations.select_observations(self.pj, cfg.MULTIPLE)
    if not resultStr or not selected_observations:
        return

    extended_file_formats = [
        "Tab Separated Values (*.tsv)",
        "Comma Separated Values (*.csv)",
        "Open Document Spreadsheet ODS (*.ods)",
        "Microsoft Excel Spreadsheet XLSX (*.xlsx)",
        "Legacy Microsoft Excel Spreadsheet XLS (*.xls)",
        "HTML (*.html)",
    ]
    file_formats = ["tsv", "csv", "ods", "xlsx", "xls", "html"]

    file_name, filter_ = QFileDialog().getSaveFileName(
        self, "Export list of selected observations", "", ";;".join(extended_file_formats)
    )

    if not file_name:
        return

    output_format = file_formats[extended_file_formats.index(filter_)]
    if pl.Path(file_name).suffix != "." + output_format:
        file_name = str(pl.Path(file_name)) + "." + output_format
        # check if file name with extension already exists
        if pl.Path(file_name).is_file():
            if (
                dialog.MessageDialog(
                    cfg.programName, f"The file {file_name} already exists.", [cfg.CANCEL, cfg.OVERWRITE]
                )
                == cfg.CANCEL
            ):
                return

    if not project_functions.export_observations_list(self.pj, selected_observations, file_name, output_format):
        QMessageBox.warning(self, cfg.programName, "File not created due to an error")


def observations_list(self):
    """
    show list of all observations of current project
    """

    logging.debug(f"observations list")

    if self.playerType in cfg.VIEWERS:
        close_observation(self)

    result, selected_obs = select_observations.select_observations(self.pj, cfg.SINGLE)

    if not selected_obs:
        return

    if self.observationId:

        self.hide_data_files()
        response = dialog.MessageDialog(
            cfg.programName, "The current observation will be closed. Do you want to continue?", (cfg.YES, cfg.NO)
        )
        if response == cfg.NO:
            self.show_data_files()
            return ""
        else:
            close_observation(self)

        QtTest.QTest.qWait(1000)

    if result == cfg.OPEN:
        # select_observations.select_observations(self.pj, cfg.OPEN)
        load_observation(self, selected_obs[0], cfg.OBS_START)

    if result == cfg.VIEW:
        load_observation(self, selected_obs[0], cfg.VIEW)

    if result == cfg.EDIT:
        if self.observationId != selected_obs[0]:
            new_observation(self, mode=cfg.EDIT, obsId=selected_obs[0])  # observation id to edit
        else:
            QMessageBox.warning(
                self,
                cfg.programName,
                (f"The observation <b>{self.observationId}</b> is running!<br>" "Close it before editing."),
            )

    logging.debug(f"end observations list")


def open_observation(self, mode: str) -> str:
    """
    start or view an observation

    Args:
        mode (str): "start" to start observation
                    "view" to view observation
    """

    logging.debug(f"open observation")

    # check if current observation must be closed to open a new one
    if self.observationId:

        self.hide_data_files()
        response = dialog.MessageDialog(
            cfg.programName, "The current observation will be closed. Do you want to continue?", (cfg.YES, cfg.NO)
        )
        if response == cfg.NO:
            self.show_data_files()
            return ""
        else:
            close_observation(self)
    selected_observations = []
    if mode == cfg.OBS_START:
        _, selected_observations = select_observations.select_observations(self.pj, cfg.OPEN)
    if mode == cfg.VIEW:
        _, selected_observations = select_observations.select_observations(self.pj, cfg.VIEW)

    if selected_observations:
        return load_observation(self, selected_observations[0], mode)
    else:
        return ""


def load_observation(self, obs_id: str, mode: str = cfg.OBS_START) -> str:
    """
    load observation obs_id

    Args:
        obsId (str): observation id
        mode (str): "start" to start observation
                    "view"  to view observation
    """

    logging.debug(f"load observation")

    if obs_id not in self.pj[cfg.OBSERVATIONS]:
        return "Error: Observation not found"

    if self.pj[cfg.OBSERVATIONS][obs_id][cfg.TYPE] not in [cfg.IMAGES, cfg.LIVE, cfg.MEDIA]:
        return f"Error: Observation type {self.pj[cfg.OBSERVATIONS][obs_id][cfg.TYPE]} not found"

    self.observationId = obs_id

    if self.pj[cfg.OBSERVATIONS][self.observationId][cfg.TYPE] == cfg.IMAGES:

        self.image_idx = 0
        self.images_list = []

        if mode == cfg.OBS_START:
            self.playerType = cfg.IMAGES
            initialize_new_images_observation(self)

        if mode == cfg.VIEW:
            self.playerType = cfg.VIEWER_IMAGES
            self.dwEvents.setVisible(True)

    if self.pj[cfg.OBSERVATIONS][self.observationId][cfg.TYPE] == cfg.LIVE:

        if mode == cfg.OBS_START:
            initialize_new_live_observation(self)

        if mode == cfg.VIEW:
            self.playerType = cfg.VIEWER_LIVE
            self.dwEvents.setVisible(True)

    if self.pj[cfg.OBSERVATIONS][self.observationId][cfg.TYPE] == cfg.MEDIA:

        if mode == cfg.OBS_START:
            if not initialize_new_media_observation(self):
                self.observationId = ""
                self.twEvents.setRowCount(0)
                menu_options.update_menu(self)
                return "Error: loading observation problem"

        if mode == cfg.VIEW:
            self.playerType = cfg.VIEWER_MEDIA
            self.dwEvents.setVisible(True)

    self.load_tw_events(self.observationId)

    menu_options.update_menu(self)
    # title of dock widget  “  ”
    self.dwEvents.setWindowTitle(f"Events for “{self.observationId}” observation")

    logging.debug(f"end load observation")
    return ""


def edit_observation(self):
    """
    edit observation
    """

    # check if current observation must be closed to open a new one
    if self.observationId:
        # hide data plot
        self.hide_data_files()
        if (
            dialog.MessageDialog(
                cfg.programName, "The current observation will be closed. Do you want to continue?", (cfg.YES, cfg.NO)
            )
            == cfg.NO
        ):
            # restore plots
            self.show_data_files()
            return
        else:
            close_observation(self)

    _, selected_observations = select_observations.select_observations(
        self.pj, cfg.EDIT, windows_title="Edit observation"
    )

    if selected_observations:
        new_observation(self, mode=cfg.EDIT, obsId=selected_observations[0])


def remove_observations(self):
    """
    remove observations from project file
    """

    _, selected_observations = select_observations.select_observations(
        self.pj, cfg.MULTIPLE, windows_title="Remove observations"
    )
    if not selected_observations:
        return

    if len(selected_observations) > 1:
        msg = "all the selected observations"
    else:
        msg = "the selected observation"
    response = dialog.MessageDialog(
        cfg.programName,
        (
            "<b>The removal of observations is irreversible (better make a backup of your project before?)</b>."
            f"<br>Are you sure to remove {msg}?<br><br>"
            f"{'<br>'.join(selected_observations)}"
        ),
        (cfg.YES, cfg.CANCEL),
    )
    if response == cfg.YES:
        for obs_id in selected_observations:
            del self.pj[cfg.OBSERVATIONS][obs_id]
            self.project_changed()


def observation_length(pj: dict, selected_observations: list) -> tuple:
    """
    max length of selected observations
    total media length

    Args:
        selected_observations (list): list of selected observations

    Returns:
        float: maximum media length for all observations
        float: total media length for all observations
    """
    selectedObsTotalMediaLength = dec("0.0")
    max_obs_length = dec(0)
    for obs_id in selected_observations:
        obs_length = project_functions.observation_total_length(pj[cfg.OBSERVATIONS][obs_id])
        if obs_length == dec(-2):  # IMAGES OBS with time not available
            selectedObsTotalMediaLength = dec(-2)
            break
        if obs_length in [dec(0), dec(-1)]:
            selectedObsTotalMediaLength = dec(-1)
            break
        max_obs_length = max(max_obs_length, obs_length)
        selectedObsTotalMediaLength += obs_length

    # an observation media length is not available
    if selectedObsTotalMediaLength == -1:
        # propose to user to use max event time
        if (
            dialog.MessageDialog(
                cfg.programName,
                (
                    f"The observation length is not available (<b>{obs_id}</b>).<br>"
                    "Use last event time as observation length?"
                ),
                (cfg.YES, cfg.NO),
            )
            == cfg.YES
        ):
            try:
                maxTime = dec(0)  # max length for all events all subjects
                max_length = dec(0)
                for obs_id in selected_observations:
                    if pj[cfg.OBSERVATIONS][obs_id][cfg.EVENTS]:
                        maxTime += max(pj[cfg.OBSERVATIONS][obs_id][cfg.EVENTS])[0]
                        max_length = max(max_length, max(pj[cfg.OBSERVATIONS][obs_id][cfg.EVENTS])[0])

                logging.debug(f"max time all events all subjects: {maxTime}")

                max_obs_length = max_length
                selectedObsTotalMediaLength = maxTime
            except Exception:
                max_obs_length = dec(-1)
                selectedObsTotalMediaLength = dec(-1)

        else:
            max_obs_length = dec(-1)
            selectedObsTotalMediaLength = dec(-1)

    if selectedObsTotalMediaLength == dec(-2):  # IMAGES OBS with time not available
        max_obs_length = dec("NaN")
        selectedObsTotalMediaLength = dec("NaN")

    return (max_obs_length, selectedObsTotalMediaLength)


def new_observation(self, mode=cfg.NEW, obsId=""):
    """
    define a new observation or edit an existing observation

    Args:
        mode (str): NEW or EDIT
        obsId (str): observation Id to be edited

    """
    # check if current observation must be closed to create a new one
    if mode == cfg.NEW and self.observationId:
        # hide data plot
        self.hide_data_files()
        if (
            dialog.MessageDialog(
                cfg.programName, "The current observation will be closed. Do you want to continue?", (cfg.YES, cfg.NO)
            )
            == cfg.NO
        ):

            # show data plot
            self.show_data_files()
            return
        else:
            close_observation(self)

    observationWindow = observation.Observation(
        tmp_dir=self.ffmpeg_cache_dir
        if (self.ffmpeg_cache_dir and pl.Path(self.ffmpeg_cache_dir).is_dir())
        else tempfile.gettempdir(),
        project_path=self.projectFileName,
        converters=self.pj[cfg.CONVERTERS] if cfg.CONVERTERS in self.pj else {},
        time_format=self.timeFormat,
    )

    observationWindow.pj = dict(self.pj)
    observationWindow.sw_observation_type.setCurrentIndex(0)  # no observation type
    observationWindow.mode = mode
    observationWindow.mem_obs_id = obsId
    observationWindow.chunk_length = self.chunk_length
    observationWindow.dteDate.setDateTime(QDateTime.currentDateTime())
    observationWindow.ffmpeg_bin = self.ffmpeg_bin
    observationWindow.project_file_name = self.projectFileName
    observationWindow.rb_no_time.setChecked(True)

    # add independent variables
    if cfg.INDEPENDENT_VARIABLES in self.pj:

        observationWindow.twIndepVariables.setRowCount(0)
        for i in util.sorted_keys(self.pj[cfg.INDEPENDENT_VARIABLES]):

            observationWindow.twIndepVariables.setRowCount(observationWindow.twIndepVariables.rowCount() + 1)

            # label
            item = QTableWidgetItem()
            indepVarLabel = self.pj[cfg.INDEPENDENT_VARIABLES][i]["label"]
            item.setText(indepVarLabel)
            item.setFlags(Qt.ItemIsEnabled)
            observationWindow.twIndepVariables.setItem(observationWindow.twIndepVariables.rowCount() - 1, 0, item)

            # var type
            item = QTableWidgetItem()
            item.setText(self.pj[cfg.INDEPENDENT_VARIABLES][i]["type"])
            item.setFlags(Qt.ItemIsEnabled)  # not modifiable
            observationWindow.twIndepVariables.setItem(observationWindow.twIndepVariables.rowCount() - 1, 1, item)

            # var value
            item = QTableWidgetItem()
            # check if obs has independent variables and var label is a key
            if (
                mode == cfg.EDIT
                and cfg.INDEPENDENT_VARIABLES in self.pj[cfg.OBSERVATIONS][obsId]
                and indepVarLabel in self.pj[cfg.OBSERVATIONS][obsId][cfg.INDEPENDENT_VARIABLES]
            ):
                txt = self.pj[cfg.OBSERVATIONS][obsId][cfg.INDEPENDENT_VARIABLES][indepVarLabel]

            elif mode == cfg.NEW:
                txt = self.pj[cfg.INDEPENDENT_VARIABLES][i]["default value"]
            else:
                txt = ""

            if self.pj[cfg.INDEPENDENT_VARIABLES][i]["type"] == cfg.SET_OF_VALUES:
                comboBox = QComboBox()
                comboBox.addItems(self.pj[cfg.INDEPENDENT_VARIABLES][i]["possible values"].split(","))
                if txt in self.pj[cfg.INDEPENDENT_VARIABLES][i]["possible values"].split(","):
                    comboBox.setCurrentIndex(
                        self.pj[cfg.INDEPENDENT_VARIABLES][i]["possible values"].split(",").index(txt)
                    )
                observationWindow.twIndepVariables.setCellWidget(
                    observationWindow.twIndepVariables.rowCount() - 1, 2, comboBox
                )

            elif self.pj[cfg.INDEPENDENT_VARIABLES][i]["type"] == cfg.TIMESTAMP:
                cal = QDateTimeEdit()
                cal.setDisplayFormat("yyyy-MM-dd hh:mm:ss")
                cal.setCalendarPopup(True)
                if txt:
                    cal.setDateTime(QDateTime.fromString(txt, "yyyy-MM-ddThh:mm:ss"))
                observationWindow.twIndepVariables.setCellWidget(
                    observationWindow.twIndepVariables.rowCount() - 1, 2, cal
                )
            else:
                item.setText(txt)
                observationWindow.twIndepVariables.setItem(observationWindow.twIndepVariables.rowCount() - 1, 2, item)

        observationWindow.twIndepVariables.resizeColumnsToContents()

    # adapt time offset for current time format
    if self.timeFormat == cfg.S:
        observationWindow.obs_time_offset.set_format_s()
    if self.timeFormat == cfg.HHMMSS:
        observationWindow.obs_time_offset.set_format_hhmmss()

    if mode == cfg.EDIT:

        observationWindow.setWindowTitle(f'Edit observation "{obsId}"')
        mem_obs_id = obsId
        observationWindow.leObservationId.setText(obsId)

        # check date format for old versions of BORIS app
        try:
            time.strptime(self.pj[cfg.OBSERVATIONS][obsId]["date"], "%Y-%m-%d %H:%M")
            self.pj[cfg.OBSERVATIONS][obsId]["date"] = (
                self.pj[cfg.OBSERVATIONS][obsId]["date"].replace(" ", "T") + ":00"
            )
        except ValueError:
            pass

        observationWindow.dteDate.setDateTime(
            QDateTime.fromString(self.pj[cfg.OBSERVATIONS][obsId]["date"], "yyyy-MM-ddThh:mm:ss")
        )
        observationWindow.teDescription.setPlainText(self.pj[cfg.OBSERVATIONS][obsId][cfg.DESCRIPTION])

        try:
            observationWindow.mediaDurations = self.pj[cfg.OBSERVATIONS][obsId][cfg.MEDIA_INFO][cfg.LENGTH]
            observationWindow.mediaFPS = self.pj[cfg.OBSERVATIONS][obsId][cfg.MEDIA_INFO][cfg.FPS]
        except Exception:
            observationWindow.mediaDurations = {}
            observationWindow.mediaFPS = {}

        try:
            if cfg.HAS_VIDEO in self.pj[cfg.OBSERVATIONS][obsId][cfg.MEDIA_INFO]:
                observationWindow.mediaHasVideo = self.pj[cfg.OBSERVATIONS][obsId][cfg.MEDIA_INFO][cfg.HAS_VIDEO]
            if cfg.HAS_AUDIO in self.pj[cfg.OBSERVATIONS][obsId][cfg.MEDIA_INFO]:
                observationWindow.mediaHasAudio = self.pj[cfg.OBSERVATIONS][obsId][cfg.MEDIA_INFO][cfg.HAS_AUDIO]
        except Exception:
            logging.info("No Video/Audio information")

        # offset
        observationWindow.obs_time_offset.set_time(self.pj[cfg.OBSERVATIONS][obsId][cfg.TIME_OFFSET])

        if self.pj[cfg.OBSERVATIONS][obsId]["type"] == cfg.MEDIA:
            observationWindow.rb_media_files.setChecked(True)

            observationWindow.twVideo1.setRowCount(0)
            for player in self.pj[cfg.OBSERVATIONS][obsId][cfg.FILE]:
                if (
                    player in self.pj[cfg.OBSERVATIONS][obsId][cfg.FILE]
                    and self.pj[cfg.OBSERVATIONS][obsId][cfg.FILE][player]
                ):
                    for mediaFile in self.pj[cfg.OBSERVATIONS][obsId][cfg.FILE][player]:
                        observationWindow.twVideo1.setRowCount(observationWindow.twVideo1.rowCount() + 1)

                        combobox = QComboBox()
                        combobox.addItems(cfg.ALL_PLAYERS)
                        combobox.setCurrentIndex(int(player) - 1)
                        observationWindow.twVideo1.setCellWidget(observationWindow.twVideo1.rowCount() - 1, 0, combobox)

                        # set offset
                        try:
                            observationWindow.twVideo1.setItem(
                                observationWindow.twVideo1.rowCount() - 1,
                                1,
                                QTableWidgetItem(
                                    str(self.pj[cfg.OBSERVATIONS][obsId][cfg.MEDIA_INFO]["offset"][player])
                                ),
                            )
                        except Exception:
                            observationWindow.twVideo1.setItem(
                                observationWindow.twVideo1.rowCount() - 1, 1, QTableWidgetItem("0.0")
                            )

                        item = QTableWidgetItem(mediaFile)
                        item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                        observationWindow.twVideo1.setItem(observationWindow.twVideo1.rowCount() - 1, 2, item)

                        # duration and FPS
                        try:
                            item = QTableWidgetItem(
                                util.seconds2time(
                                    self.pj[cfg.OBSERVATIONS][obsId][cfg.MEDIA_INFO][cfg.LENGTH][mediaFile]
                                )
                            )
                            item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                            observationWindow.twVideo1.setItem(observationWindow.twVideo1.rowCount() - 1, 3, item)

                            item = QTableWidgetItem(
                                f"{self.pj[cfg.OBSERVATIONS][obsId][cfg.MEDIA_INFO][cfg.FPS][mediaFile]:.2f}"
                            )
                            item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                            observationWindow.twVideo1.setItem(observationWindow.twVideo1.rowCount() - 1, 4, item)
                        except Exception:
                            pass

                        # has_video has_audio
                        try:
                            item = QTableWidgetItem(
                                str(self.pj[cfg.OBSERVATIONS][obsId][cfg.MEDIA_INFO][cfg.HAS_VIDEO][mediaFile])
                            )
                            item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                            observationWindow.twVideo1.setItem(observationWindow.twVideo1.rowCount() - 1, 5, item)

                            item = QTableWidgetItem(
                                str(self.pj[cfg.OBSERVATIONS][obsId][cfg.MEDIA_INFO][cfg.HAS_AUDIO][mediaFile])
                            )
                            item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                            observationWindow.twVideo1.setItem(observationWindow.twVideo1.rowCount() - 1, 6, item)
                        except Exception:
                            pass

            # spectrogram
            observationWindow.cbVisualizeSpectrogram.setEnabled(True)
            observationWindow.cbVisualizeSpectrogram.setChecked(
                self.pj[cfg.OBSERVATIONS][obsId].get(cfg.VISUALIZE_SPECTROGRAM, False)
            )

            # waveform
            observationWindow.cb_visualize_waveform.setEnabled(True)
            observationWindow.cb_visualize_waveform.setChecked(
                self.pj[cfg.OBSERVATIONS][obsId].get(cfg.VISUALIZE_WAVEFORM, False)
            )

            # plot data
            if cfg.PLOT_DATA in self.pj[cfg.OBSERVATIONS][obsId]:
                if self.pj[cfg.OBSERVATIONS][obsId][cfg.PLOT_DATA]:

                    observationWindow.tw_data_files.setRowCount(0)
                    for idx2 in util.sorted_keys(self.pj[cfg.OBSERVATIONS][obsId][cfg.PLOT_DATA]):
                        observationWindow.tw_data_files.setRowCount(observationWindow.tw_data_files.rowCount() + 1)
                        for idx3 in cfg.DATA_PLOT_FIELDS:
                            if idx3 == cfg.PLOT_DATA_PLOTCOLOR_IDX:
                                combobox = QComboBox()
                                combobox.addItems(cfg.DATA_PLOT_STYLES)
                                combobox.setCurrentIndex(
                                    cfg.DATA_PLOT_STYLES.index(
                                        self.pj[cfg.OBSERVATIONS][obsId][cfg.PLOT_DATA][idx2][
                                            cfg.DATA_PLOT_FIELDS[idx3]
                                        ]
                                    )
                                )

                                observationWindow.tw_data_files.setCellWidget(
                                    observationWindow.tw_data_files.rowCount() - 1,
                                    cfg.PLOT_DATA_PLOTCOLOR_IDX,
                                    combobox,
                                )
                            elif idx3 == cfg.PLOT_DATA_SUBSTRACT1STVALUE_IDX:
                                combobox2 = QComboBox()
                                combobox2.addItems(["False", "True"])
                                combobox2.setCurrentIndex(
                                    ["False", "True"].index(
                                        self.pj[cfg.OBSERVATIONS][obsId][cfg.PLOT_DATA][idx2][
                                            cfg.DATA_PLOT_FIELDS[idx3]
                                        ]
                                    )
                                )

                                observationWindow.tw_data_files.setCellWidget(
                                    observationWindow.tw_data_files.rowCount() - 1,
                                    cfg.PLOT_DATA_SUBSTRACT1STVALUE_IDX,
                                    combobox2,
                                )
                            elif idx3 == cfg.PLOT_DATA_CONVERTERS_IDX:
                                # convert dict to str
                                observationWindow.tw_data_files.setItem(
                                    observationWindow.tw_data_files.rowCount() - 1,
                                    idx3,
                                    QTableWidgetItem(
                                        str(
                                            self.pj[cfg.OBSERVATIONS][obsId][cfg.PLOT_DATA][idx2][
                                                cfg.DATA_PLOT_FIELDS[idx3]
                                            ]
                                        )
                                    ),
                                )

                            else:
                                observationWindow.tw_data_files.setItem(
                                    observationWindow.tw_data_files.rowCount() - 1,
                                    idx3,
                                    QTableWidgetItem(
                                        self.pj[cfg.OBSERVATIONS][obsId][cfg.PLOT_DATA][idx2][
                                            cfg.DATA_PLOT_FIELDS[idx3]
                                        ]
                                    ),
                                )

        if self.pj[cfg.OBSERVATIONS][obsId]["type"] == cfg.IMAGES:
            observationWindow.rb_images.setChecked(True)
            observationWindow.lw_images_directory.addItems(
                self.pj[cfg.OBSERVATIONS][obsId].get(cfg.DIRECTORIES_LIST, [])
            )
            observationWindow.rb_use_exif.setChecked(self.pj[cfg.OBSERVATIONS][obsId].get(cfg.USE_EXIF_DATE, False))
            if self.pj[cfg.OBSERVATIONS][obsId].get(cfg.TIME_LAPSE, 0):
                observationWindow.rb_time_lapse.setChecked(True)
                observationWindow.sb_time_lapse.setValue(self.pj[cfg.OBSERVATIONS][obsId].get(cfg.TIME_LAPSE, 0))

        if self.pj[cfg.OBSERVATIONS][obsId]["type"] in [cfg.LIVE]:
            observationWindow.rb_live.setChecked(True)
            # sampling time
            observationWindow.sbScanSampling.setValue(self.pj[cfg.OBSERVATIONS][obsId].get(cfg.SCAN_SAMPLING_TIME, 0))
            # start from current time
            observationWindow.cb_start_from_current_time.setChecked(
                self.pj[cfg.OBSERVATIONS][obsId].get(cfg.START_FROM_CURRENT_TIME, False)
                or self.pj[cfg.OBSERVATIONS][obsId].get(cfg.START_FROM_CURRENT_EPOCH_TIME, False)
            )
            # day/epoch time
            observationWindow.rb_day_time.setChecked(
                self.pj[cfg.OBSERVATIONS][obsId].get(cfg.START_FROM_CURRENT_TIME, False)
            )
            observationWindow.rb_epoch_time.setChecked(
                self.pj[cfg.OBSERVATIONS][obsId].get(cfg.START_FROM_CURRENT_EPOCH_TIME, False)
            )

        # observation time interval
        observationWindow.cb_observation_time_interval.setEnabled(True)
        if self.pj[cfg.OBSERVATIONS][obsId].get(cfg.OBSERVATION_TIME_INTERVAL, [0, 0]) != [0, 0]:
            observationWindow.cb_observation_time_interval.setChecked(True)
            observationWindow.observation_time_interval = self.pj[cfg.OBSERVATIONS][obsId].get(
                cfg.OBSERVATION_TIME_INTERVAL, [0, 0]
            )
            observationWindow.cb_observation_time_interval.setText(
                (
                    "Limit observation to a time interval: "
                    f"{self.pj[cfg.OBSERVATIONS][obsId][cfg.OBSERVATION_TIME_INTERVAL][0]} - "
                    f"{self.pj[cfg.OBSERVATIONS][obsId][cfg.OBSERVATION_TIME_INTERVAL][1]}"
                )
            )

        # disabled due to problem when video goes back
        # if CLOSE_BEHAVIORS_BETWEEN_VIDEOS in self.pj[OBSERVATIONS][obsId]:
        #    observationWindow.cbCloseCurrentBehaviorsBetweenVideo.setChecked(self.pj[OBSERVATIONS][obsId][CLOSE_BEHAVIORS_BETWEEN_VIDEOS])

    rv = observationWindow.exec_()

    if rv:

        self.project_changed()

        new_obs_id = observationWindow.leObservationId.text().strip()

        if mode == cfg.NEW:
            self.observationId = new_obs_id
            self.pj[cfg.OBSERVATIONS][self.observationId] = {
                cfg.FILE: [],
                cfg.TYPE: "",
                "date": "",
                cfg.DESCRIPTION: "",
                cfg.TIME_OFFSET: 0,
                cfg.EVENTS: [],
                cfg.OBSERVATION_TIME_INTERVAL: [0, 0],
            }

        # check if id changed
        if mode == cfg.EDIT and new_obs_id != obsId:

            logging.info(f"observation id {obsId} changed in {new_obs_id}")

            self.pj[cfg.OBSERVATIONS][new_obs_id] = dict(self.pj[cfg.OBSERVATIONS][obsId])
            del self.pj[cfg.OBSERVATIONS][obsId]

        # observation date
        self.pj[cfg.OBSERVATIONS][new_obs_id]["date"] = observationWindow.dteDate.dateTime().toString(Qt.ISODate)
        self.pj[cfg.OBSERVATIONS][new_obs_id][cfg.DESCRIPTION] = observationWindow.teDescription.toPlainText()

        # observation type: read project type from radio buttons
        if observationWindow.rb_media_files.isChecked():
            self.pj[cfg.OBSERVATIONS][new_obs_id][cfg.TYPE] = cfg.MEDIA
        if observationWindow.rb_live.isChecked():
            self.pj[cfg.OBSERVATIONS][new_obs_id][cfg.TYPE] = cfg.LIVE
        if observationWindow.rb_images.isChecked():
            self.pj[cfg.OBSERVATIONS][new_obs_id][cfg.TYPE] = cfg.IMAGES

        # independent variables for observation
        self.pj[cfg.OBSERVATIONS][new_obs_id][cfg.INDEPENDENT_VARIABLES] = {}
        for r in range(observationWindow.twIndepVariables.rowCount()):

            # set dictionary as label (col 0) => value (col 2)
            if observationWindow.twIndepVariables.item(r, 1).text() == cfg.SET_OF_VALUES:
                self.pj[cfg.OBSERVATIONS][new_obs_id][cfg.INDEPENDENT_VARIABLES][
                    observationWindow.twIndepVariables.item(r, 0).text()
                ] = observationWindow.twIndepVariables.cellWidget(r, 2).currentText()
            elif observationWindow.twIndepVariables.item(r, 1).text() == cfg.TIMESTAMP:
                self.pj[cfg.OBSERVATIONS][new_obs_id][cfg.INDEPENDENT_VARIABLES][
                    observationWindow.twIndepVariables.item(r, 0).text()
                ] = (observationWindow.twIndepVariables.cellWidget(r, 2).dateTime().toString(Qt.ISODate))
            else:
                self.pj[cfg.OBSERVATIONS][new_obs_id][cfg.INDEPENDENT_VARIABLES][
                    observationWindow.twIndepVariables.item(r, 0).text()
                ] = observationWindow.twIndepVariables.item(r, 2).text()

        # observation time offset
        self.pj[cfg.OBSERVATIONS][new_obs_id][cfg.TIME_OFFSET] = observationWindow.obs_time_offset.get_time()

        if observationWindow.cb_observation_time_interval.isChecked():
            self.pj[cfg.OBSERVATIONS][new_obs_id][
                cfg.OBSERVATION_TIME_INTERVAL
            ] = observationWindow.observation_time_interval

        self.display_statusbar_info(new_obs_id)

        # visualize spectrogram
        self.pj[cfg.OBSERVATIONS][new_obs_id][
            cfg.VISUALIZE_SPECTROGRAM
        ] = observationWindow.cbVisualizeSpectrogram.isChecked()
        # visualize spectrogram
        self.pj[cfg.OBSERVATIONS][new_obs_id][
            cfg.VISUALIZE_WAVEFORM
        ] = observationWindow.cb_visualize_waveform.isChecked()
        # time interval for observation
        self.pj[cfg.OBSERVATIONS][new_obs_id][
            cfg.OBSERVATION_TIME_INTERVAL
        ] = observationWindow.observation_time_interval

        # plot data
        if observationWindow.tw_data_files.rowCount():
            self.pj[cfg.OBSERVATIONS][new_obs_id][cfg.PLOT_DATA] = {}
            for row in range(observationWindow.tw_data_files.rowCount()):
                self.pj[cfg.OBSERVATIONS][new_obs_id][cfg.PLOT_DATA][str(row)] = {}
                for idx2 in cfg.DATA_PLOT_FIELDS:
                    if idx2 in [cfg.PLOT_DATA_PLOTCOLOR_IDX, cfg.PLOT_DATA_SUBSTRACT1STVALUE_IDX]:
                        self.pj[cfg.OBSERVATIONS][new_obs_id][cfg.PLOT_DATA][str(row)][
                            cfg.DATA_PLOT_FIELDS[idx2]
                        ] = observationWindow.tw_data_files.cellWidget(row, idx2).currentText()

                    elif idx2 == cfg.PLOT_DATA_CONVERTERS_IDX:
                        if observationWindow.tw_data_files.item(row, idx2).text():
                            self.pj[cfg.OBSERVATIONS][new_obs_id][cfg.PLOT_DATA][str(row)][
                                cfg.DATA_PLOT_FIELDS[idx2]
                            ] = eval(observationWindow.tw_data_files.item(row, idx2).text())
                        else:
                            self.pj[cfg.OBSERVATIONS][new_obs_id][cfg.PLOT_DATA][str(row)][
                                cfg.DATA_PLOT_FIELDS[idx2]
                            ] = {}

                    else:
                        self.pj[cfg.OBSERVATIONS][new_obs_id][cfg.PLOT_DATA][str(row)][
                            cfg.DATA_PLOT_FIELDS[idx2]
                        ] = observationWindow.tw_data_files.item(row, idx2).text()

        # Close current behaviors between video
        # disabled due to problem when video goes back
        # self.pj[OBSERVATIONS][new_obs_id][CLOSE_BEHAVIORS_BETWEEN_VIDEOS] =
        # observationWindow.cbCloseCurrentBehaviorsBetweenVideo.isChecked()
        self.pj[cfg.OBSERVATIONS][new_obs_id][cfg.CLOSE_BEHAVIORS_BETWEEN_VIDEOS] = False

        if self.pj[cfg.OBSERVATIONS][new_obs_id][cfg.TYPE] == cfg.LIVE:
            self.pj[cfg.OBSERVATIONS][new_obs_id][cfg.SCAN_SAMPLING_TIME] = observationWindow.sbScanSampling.value()
            self.pj[cfg.OBSERVATIONS][new_obs_id][cfg.START_FROM_CURRENT_TIME] = (
                observationWindow.cb_start_from_current_time.isChecked() and observationWindow.rb_day_time.isChecked()
            )
            self.pj[cfg.OBSERVATIONS][new_obs_id][cfg.START_FROM_CURRENT_EPOCH_TIME] = (
                observationWindow.cb_start_from_current_time.isChecked() and observationWindow.rb_epoch_time.isChecked()
            )

        # images dir
        if self.pj[cfg.OBSERVATIONS][new_obs_id][cfg.TYPE] == cfg.IMAGES:
            self.pj[cfg.OBSERVATIONS][new_obs_id][cfg.DIRECTORIES_LIST] = [
                observationWindow.lw_images_directory.item(i).text()
                for i in range(observationWindow.lw_images_directory.count())
            ]
            self.pj[cfg.OBSERVATIONS][new_obs_id][cfg.USE_EXIF_DATE] = observationWindow.rb_use_exif.isChecked()
            if observationWindow.rb_time_lapse.isChecked():
                self.pj[cfg.OBSERVATIONS][new_obs_id][cfg.TIME_LAPSE] = observationWindow.sb_time_lapse.value()
            else:
                self.pj[cfg.OBSERVATIONS][new_obs_id][cfg.TIME_LAPSE] = 0

        # media file
        self.pj[cfg.OBSERVATIONS][new_obs_id][cfg.FILE] = {}

        # media
        if self.pj[cfg.OBSERVATIONS][new_obs_id][cfg.TYPE] == cfg.MEDIA:

            self.pj[cfg.OBSERVATIONS][new_obs_id][cfg.MEDIA_INFO] = {
                cfg.LENGTH: observationWindow.mediaDurations,
                cfg.FPS: observationWindow.mediaFPS,
            }

            try:
                self.pj[cfg.OBSERVATIONS][new_obs_id][cfg.MEDIA_INFO][cfg.HAS_VIDEO] = observationWindow.mediaHasVideo
                self.pj[cfg.OBSERVATIONS][new_obs_id][cfg.MEDIA_INFO][cfg.HAS_AUDIO] = observationWindow.mediaHasAudio
            except Exception:
                logging.info("error with media_info information")

            self.pj[cfg.OBSERVATIONS][new_obs_id][cfg.MEDIA_INFO]["offset"] = {}

            logging.debug(f"media_info: {self.pj[cfg.OBSERVATIONS][new_obs_id][cfg.MEDIA_INFO]}")

            for i in range(cfg.N_PLAYER):
                self.pj[cfg.OBSERVATIONS][new_obs_id][cfg.FILE][str(i + 1)] = []

            for row in range(observationWindow.twVideo1.rowCount()):
                self.pj[cfg.OBSERVATIONS][new_obs_id][cfg.FILE][
                    observationWindow.twVideo1.cellWidget(row, 0).currentText()
                ].append(observationWindow.twVideo1.item(row, 2).text())
                # store offset for media player
                self.pj[cfg.OBSERVATIONS][new_obs_id][cfg.MEDIA_INFO]["offset"][
                    observationWindow.twVideo1.cellWidget(row, 0).currentText()
                ] = float(observationWindow.twVideo1.item(row, 1).text())

        if rv == 1:  # save
            self.observationId = ""
            menu_options.update_menu(self)

        if rv == 2:  # start
            self.observationId = new_obs_id

            # title of dock widget
            self.dwEvents.setWindowTitle(f"Events for “{self.observationId}“ observation")

            if self.pj[cfg.OBSERVATIONS][self.observationId][cfg.TYPE] == cfg.LIVE:
                self.playerType = cfg.LIVE
                initialize_new_live_observation(self)

            if self.pj[cfg.OBSERVATIONS][self.observationId][cfg.TYPE] == cfg.MEDIA:
                self.playerType = cfg.MEDIA
                # load events in table widget
                initialize_new_media_observation(self)

            if self.pj[cfg.OBSERVATIONS][self.observationId][cfg.TYPE] == cfg.IMAGES:
                # QMessageBox.critical(self, cfg.programName, "Observation from images directory is not yet implemented")
                initialize_new_images_observation(self)

            self.load_tw_events(self.observationId)
            menu_options.update_menu(self)


def close_observation(self):
    """
    close current observation
    """

    logging.info(f"Close observation {self.playerType}")

    logging.info(f"Check state events")
    # check observation events
    flag_ok, msg = project_functions.check_state_events_obs(
        self.observationId,
        self.pj[cfg.ETHOGRAM],
        self.pj[cfg.OBSERVATIONS][self.observationId],
        time_format=cfg.HHMMSS,
    )

    if not flag_ok:

        out = f"The current observation has state event(s) that are not PAIRED:<br><br>{msg}"
        results = dialog.Results_dialog()
        results.setWindowTitle(f"{cfg.programName} - Check selected observations")
        results.ptText.setReadOnly(True)
        results.ptText.appendHtml(out)
        results.pbSave.setVisible(False)
        results.pbCancel.setText("Close observation")
        results.pbCancel.setVisible(True)
        results.pbOK.setText("Fix unpaired state events")

        if results.exec_():  # fix events

            w = dialog.Ask_time(self.timeFormat)
            w.setWindowTitle("Fix UNPAIRED state events")
            w.label.setText("Fix UNPAIRED events at time")

            if w.exec_():
                fix_at_time = w.time_widget.get_time()
                events_to_add = project_functions.fix_unpaired_state_events(
                    self.pj[cfg.ETHOGRAM],
                    self.pj[cfg.OBSERVATIONS][self.observationId],
                    fix_at_time - dec("0.001"),
                )
                if events_to_add:
                    self.pj[cfg.OBSERVATIONS][self.observationId][cfg.EVENTS].extend(events_to_add)
                    self.project_changed()
                    self.pj[cfg.OBSERVATIONS][self.observationId][cfg.EVENTS].sort()

                    self.load_tw_events(self.observationId)
                    item = self.twEvents.item(
                        [
                            i
                            for i, t in enumerate(self.pj[cfg.OBSERVATIONS][self.observationId][cfg.EVENTS])
                            if t[0] == fix_at_time
                        ][0],
                        0,
                    )
                    self.twEvents.scrollToItem(item)
                    return
            else:
                return

    logging.info(f"Check state events done")

    self.saved_state = self.saveState()

    if self.playerType == cfg.MEDIA:

        logging.info(f"Stop plot timer")
        self.plot_timer.stop()

        for i, player in enumerate(self.dw_player):
            if (
                str(i + 1) in self.pj[cfg.OBSERVATIONS][self.observationId][cfg.FILE]
                and self.pj[cfg.OBSERVATIONS][self.observationId][cfg.FILE][str(i + 1)]
            ):
                logging.info(f"Stop player #{i + 1}")
                player.player.stop()

        self.verticalLayout_3.removeWidget(self.video_slider)

        if self.video_slider is not None:
            self.video_slider.setVisible(False)
            self.video_slider.deleteLater()
            self.video_slider = None

    if self.playerType == cfg.LIVE:
        self.liveTimer.stop()
        self.w_live.setVisible(False)
        self.liveObservationStarted = False
        self.liveStartTime = None

    if (
        cfg.PLOT_DATA in self.pj[cfg.OBSERVATIONS][self.observationId]
        and self.pj[cfg.OBSERVATIONS][self.observationId][cfg.PLOT_DATA]
    ):
        for x in self.ext_data_timer_list:
            x.stop()
        for pd in self.plot_data:
            self.plot_data[pd].close_plot()

    logging.info(f"close tool window")

    self.close_tool_windows()

    self.observationId = ""

    if self.playerType in (cfg.MEDIA, cfg.IMAGES):
        """
        for idx, _ in enumerate(self.dw_player):
            #del self.dw_player[idx].stack
            self.removeDockWidget(self.dw_player[idx])
            sip.delete(self.dw_player[idx])
            self.dw_player[idx] = None
        """

        for dw in self.dw_player:

            logging.info(f"remove dock widget")

            self.removeDockWidget(dw)
            # sip.delete(dw)
            # dw = None

    # self.dw_player = []

    self.statusbar.showMessage("", 0)

    self.dwEvents.setVisible(False)

    self.w_obs_info.setVisible(False)

    self.twEvents.setRowCount(0)

    self.lb_current_media_time.clear()
    self.lb_player_status.clear()

    self.currentSubject = ""
    self.lbFocalSubject.setText(cfg.NO_FOCAL_SUBJECT)

    # clear current state(s) column in subjects table
    for i in range(self.twSubjects.rowCount()):
        self.twSubjects.item(i, len(cfg.subjectsFields)).setText("")

    for w in [self.lbTimeOffset, self.lbSpeed, self.lb_obs_time_interval]:
        w.clear()
    self.play_rate, self.playerType = 1, ""

    menu_options.update_menu(self)

    logging.info(f"Observation {self.playerType} closed")


def initialize_new_media_observation(self):
    """
    initialize new observation from media file(s)
    """

    logging.debug("function: initialize new observation for media file(s)")

    for dw in [self.dwEthogram, self.dwSubjects, self.dwEvents]:
        dw.setVisible(True)

    ok, msg = project_functions.check_if_media_available(
        self.pj[cfg.OBSERVATIONS][self.observationId], self.projectFileName
    )

    if not ok:
        QMessageBox.critical(
            self,
            cfg.programName,
            (
                f"{msg}<br><br>The observation will be opened in VIEW mode.<br>"
                "It will not be possible to log events.<br>"
                "Modify the media path to point an existing media file "
                "to log events or copy media file in the BORIS project directory."
            ),
            QMessageBox.Ok | QMessageBox.Default,
            QMessageBox.NoButton,
        )
        self.playerType = cfg.VIEWER_MEDIA
        return True

    self.playerType = cfg.MEDIA
    self.fps = 0

    self.w_live.setVisible(False)
    self.w_obs_info.setVisible(True)

    font = QFont()
    font.setPointSize(15)
    self.lb_current_media_time.setFont(font)

    # initialize video slider
    self.video_slider = QSlider(Qt.Horizontal, self)
    self.video_slider.setFocusPolicy(Qt.NoFocus)
    self.video_slider.setMaximum(cfg.SLIDER_MAXIMUM)
    self.video_slider.sliderMoved.connect(self.video_slider_sliderMoved)
    self.video_slider.sliderReleased.connect(self.video_slider_sliderReleased)
    self.verticalLayout_3.addWidget(self.video_slider)

    # add all media files to media lists
    self.setDockOptions(QMainWindow.AnimatedDocks | QMainWindow.AllowNestedDocks)
    self.dw_player = []
    # create dock widgets for players

    for i in range(cfg.N_PLAYER):
        n_player = str(i + 1)
        if (
            n_player not in self.pj[cfg.OBSERVATIONS][self.observationId][cfg.FILE]
            or not self.pj[cfg.OBSERVATIONS][self.observationId][cfg.FILE][n_player]
        ):
            continue

        if i == 0:  # first player
            p = player_dock_widget.DW_player(i, self)
            self.dw_player.append(p)

            @p.player.property_observer("time-pos")
            def time_observer(_name, value):
                if value is not None:
                    self.time_observer_signal.emit(value)

        else:
            self.dw_player.append(player_dock_widget.DW_player(i, self))

        self.dw_player[-1].setFloating(False)
        self.dw_player[-1].setVisible(False)
        self.dw_player[-1].setFeatures(QDockWidget.DockWidgetFloatable | QDockWidget.DockWidgetMovable)

        # place 4 players at the top of the main window and 4 at the bottom
        self.addDockWidget(Qt.TopDockWidgetArea if i < 4 else Qt.BottomDockWidgetArea, self.dw_player[-1])

        self.dw_player[i].setVisible(True)

        # for receiving mouse event from frame viewer
        self.dw_player[i].frame_viewer.mouse_pressed_signal.connect(self.frame_image_clicked)

        # for receiving key event from dock widget
        self.dw_player[i].key_pressed_signal.connect(self.signal_from_widget)

        # for receiving event from volume slider
        self.dw_player[i].volume_slider_moved_signal.connect(self.set_volume)

        # for receiving resize event from dock widget
        self.dw_player[i].resize_signal.connect(self.resize_dw)
        """
        # for receiving event resize and clicked (Zoom - crop)
        self.dw_player[i].view_signal.connect(self.signal_from_dw)
        """

        # add durations list
        self.dw_player[i].media_durations = []
        # add fps list
        self.dw_player[i].fps = {}

        for mediaFile in self.pj[cfg.OBSERVATIONS][self.observationId][cfg.FILE][n_player]:

            logging.debug(f"media file: {mediaFile}")

            media_full_path = project_functions.full_path(mediaFile, self.projectFileName)

            logging.debug(f"media_full_path: {media_full_path}")

            # media duration
            try:
                mediaLength = (
                    self.pj[cfg.OBSERVATIONS][self.observationId][cfg.MEDIA_INFO][cfg.LENGTH][mediaFile] * 1000
                )
                mediaFPS = self.pj[cfg.OBSERVATIONS][self.observationId][cfg.MEDIA_INFO][cfg.FPS][mediaFile]
            except Exception:

                logging.debug("media_info key not found")

                r = util.accurate_media_analysis(self.ffmpeg_bin, media_full_path)
                if "error" not in r:
                    if cfg.MEDIA_INFO not in self.pj[cfg.OBSERVATIONS][self.observationId]:
                        self.pj[cfg.OBSERVATIONS][self.observationId][cfg.MEDIA_INFO] = {
                            cfg.LENGTH: {},
                            cfg.FPS: {},
                        }
                        if cfg.LENGTH not in self.pj[cfg.OBSERVATIONS][self.observationId][cfg.MEDIA_INFO]:
                            self.pj[cfg.OBSERVATIONS][self.observationId][cfg.MEDIA_INFO][cfg.LENGTH] = {}
                        if cfg.FPS not in self.pj[cfg.OBSERVATIONS][self.observationId][cfg.MEDIA_INFO]:
                            self.pj[cfg.OBSERVATIONS][self.observationId][cfg.MEDIA_INFO][cfg.FPS] = {}

                    self.pj[cfg.OBSERVATIONS][self.observationId][cfg.MEDIA_INFO][cfg.LENGTH][mediaFile] = r["duration"]
                    self.pj[cfg.OBSERVATIONS][self.observationId][cfg.MEDIA_INFO][cfg.FPS][mediaFile] = r["fps"]

                    mediaLength = r["duration"] * 1000
                    mediaFPS = r["fps"]

                    self.project_changed()

            self.dw_player[i].media_durations.append(int(mediaLength))
            self.dw_player[i].fps[mediaFile] = mediaFPS

            self.dw_player[i].player.playlist_append(media_full_path)
            # self.dw_player[i].player.loadfile(media_full_path)
            # self.dw_player[i].player.pause = True

        self.dw_player[i].player.hwdec = "auto-safe"
        self.dw_player[i].player.playlist_pos = 0
        self.dw_player[i].player.wait_until_playing()
        self.dw_player[i].player.pause = True
        self.dw_player[i].player.wait_until_paused()
        self.dw_player[i].player.seek(0, "absolute")
        # do not close when playing finished
        self.dw_player[i].player.keep_open = True
        self.dw_player[i].player.keep_open_pause = False

        # position media
        if cfg.OBSERVATION_TIME_INTERVAL in self.pj[cfg.OBSERVATIONS][self.observationId]:
            self.seek_mediaplayer(
                int(self.pj[cfg.OBSERVATIONS][self.observationId][cfg.OBSERVATION_TIME_INTERVAL][0]), player=i
            )

        # restore zoom level
        if cfg.ZOOM_LEVEL in self.pj[cfg.OBSERVATIONS][self.observationId][cfg.MEDIA_INFO]:
            self.dw_player[i].player.video_zoom = log2(
                self.pj[cfg.OBSERVATIONS][self.observationId][cfg.MEDIA_INFO][cfg.ZOOM_LEVEL].get(n_player, 0)
            )

        # restore subtitle visibility
        if cfg.DISPLAY_MEDIA_SUBTITLES in self.pj[cfg.OBSERVATIONS][self.observationId][cfg.MEDIA_INFO]:
            self.dw_player[i].player.sub_visibility = self.pj[cfg.OBSERVATIONS][self.observationId][cfg.MEDIA_INFO][
                cfg.DISPLAY_MEDIA_SUBTITLES
            ].get(n_player, True)

        # restore overlays
        if cfg.OVERLAY in self.pj[cfg.OBSERVATIONS][self.observationId][cfg.MEDIA_INFO]:
            if n_player in self.pj[cfg.OBSERVATIONS][self.observationId][cfg.MEDIA_INFO][cfg.OVERLAY]:
                self.overlays[i] = self.dw_player[i].player.create_image_overlay()
                self.resize_dw(i)

    menu_options.update_menu(self)

    self.time_observer_signal.connect(self.mpv_timer_out)

    self.actionPlay.setIcon(QIcon(":/play"))

    self.display_statusbar_info(self.observationId)

    self.currentSubject = ""
    # store state behaviors for subject current state
    self.state_behaviors_codes = tuple(util.state_behavior_codes(self.pj[cfg.ETHOGRAM]))

    self.lbSpeed.setText(f"Player rate: x{self.play_rate:.3f}")

    # spectrogram
    if (
        cfg.VISUALIZE_SPECTROGRAM in self.pj[cfg.OBSERVATIONS][self.observationId]
        and self.pj[cfg.OBSERVATIONS][self.observationId][cfg.VISUALIZE_SPECTROGRAM]
    ):

        tmp_dir = (
            self.ffmpeg_cache_dir
            if self.ffmpeg_cache_dir and os.path.isdir(self.ffmpeg_cache_dir)
            else tempfile.gettempdir()
        )

        wav_file_path = (
            pl.Path(tmp_dir)
            / pl.Path(
                self.dw_player[0].player.playlist[self.dw_player[0].player.playlist_pos]["filename"] + ".wav"
            ).name
        )

        if not wav_file_path.is_file():
            self.generate_wav_file_from_media()

        self.show_plot_widget("spectrogram", warning=False)

    # waveform
    if (
        cfg.VISUALIZE_WAVEFORM in self.pj[cfg.OBSERVATIONS][self.observationId]
        and self.pj[cfg.OBSERVATIONS][self.observationId][cfg.VISUALIZE_WAVEFORM]
    ):

        tmp_dir = (
            self.ffmpeg_cache_dir
            if self.ffmpeg_cache_dir and os.path.isdir(self.ffmpeg_cache_dir)
            else tempfile.gettempdir()
        )

        wav_file_path = (
            pl.Path(tmp_dir)
            / pl.Path(
                self.dw_player[0].player.playlist[self.dw_player[0].player.playlist_pos]["filename"] + ".wav"
            ).name
        )

        if not wav_file_path.is_file():
            self.generate_wav_file_from_media()

        self.show_plot_widget("waveform", warning=False)

    # external data plot
    if (
        cfg.PLOT_DATA in self.pj[cfg.OBSERVATIONS][self.observationId]
        and self.pj[cfg.OBSERVATIONS][self.observationId][cfg.PLOT_DATA]
    ):

        self.plot_data = {}
        self.ext_data_timer_list = []
        count = 0
        for idx in self.pj[cfg.OBSERVATIONS][self.observationId][cfg.PLOT_DATA]:
            if count == 0:

                data_file_path = project_functions.full_path(
                    self.pj[cfg.OBSERVATIONS][self.observationId][cfg.PLOT_DATA][idx]["file_path"],
                    self.projectFileName,
                )
                if not data_file_path:
                    QMessageBox.critical(
                        self,
                        cfg.programName,
                        "Data file not found:\n{}".format(
                            self.pj[cfg.OBSERVATIONS][self.observationId][cfg.PLOT_DATA][idx]["file_path"]
                        ),
                    )
                    return False

                w1 = plot_data_module.Plot_data(
                    data_file_path,
                    int(self.pj[cfg.OBSERVATIONS][self.observationId][cfg.PLOT_DATA][idx]["time_interval"]),
                    str(self.pj[cfg.OBSERVATIONS][self.observationId][cfg.PLOT_DATA][idx]["time_offset"]),
                    self.pj[cfg.OBSERVATIONS][self.observationId][cfg.PLOT_DATA][idx]["color"],
                    self.pj[cfg.OBSERVATIONS][self.observationId][cfg.PLOT_DATA][idx]["title"],
                    self.pj[cfg.OBSERVATIONS][self.observationId][cfg.PLOT_DATA][idx]["variable_name"],
                    self.pj[cfg.OBSERVATIONS][self.observationId][cfg.PLOT_DATA][idx]["columns"],
                    self.pj[cfg.OBSERVATIONS][self.observationId][cfg.PLOT_DATA][idx]["substract_first_value"],
                    self.pj[cfg.CONVERTERS] if cfg.CONVERTERS in self.pj else {},
                    self.pj[cfg.OBSERVATIONS][self.observationId][cfg.PLOT_DATA][idx]["converters"],
                    log_level=logging.getLogger().getEffectiveLevel(),
                )

                if w1.error_msg:
                    QMessageBox.critical(
                        self,
                        cfg.programName,
                        (
                            f"Impossible to plot data from file {os.path.basename(self.pj[cfg.OBSERVATIONS][self.observationId][cfg.PLOT_DATA][idx]['file_path'])}:\n"
                            f"{w1.error_msg}"
                        ),
                    )
                    del w1
                    return False

                w1.setWindowFlags(Qt.WindowStaysOnTopHint)
                w1.sendEvent.connect(self.signal_from_widget)  # keypress event

                w1.show()

                self.ext_data_timer_list.append(QTimer())
                self.ext_data_timer_list[-1].setInterval(w1.time_out)
                self.ext_data_timer_list[-1].timeout.connect(lambda: self.timer_plot_data_out(w1))
                self.timer_plot_data_out(w1)

                self.plot_data[count] = w1

            if count == 1:

                data_file_path = project_functions.full_path(
                    self.pj[cfg.OBSERVATIONS][self.observationId][cfg.PLOT_DATA][idx]["file_path"],
                    self.projectFileName,
                )
                if not data_file_path:
                    QMessageBox.critical(
                        self,
                        cfg.programName,
                        "Data file not found:\n{}".format(
                            self.pj[cfg.OBSERVATIONS][self.observationId][cfg.PLOT_DATA][idx]["file_path"]
                        ),
                    )
                    return False

                w2 = plot_data_module.Plot_data(
                    data_file_path,
                    int(self.pj[cfg.OBSERVATIONS][self.observationId][cfg.PLOT_DATA][idx]["time_interval"]),
                    str(self.pj[cfg.OBSERVATIONS][self.observationId][cfg.PLOT_DATA][idx]["time_offset"]),
                    self.pj[cfg.OBSERVATIONS][self.observationId][cfg.PLOT_DATA][idx]["color"],
                    self.pj[cfg.OBSERVATIONS][self.observationId][cfg.PLOT_DATA][idx]["title"],
                    self.pj[cfg.OBSERVATIONS][self.observationId][cfg.PLOT_DATA][idx]["variable_name"],
                    self.pj[cfg.OBSERVATIONS][self.observationId][cfg.PLOT_DATA][idx]["columns"],
                    self.pj[cfg.OBSERVATIONS][self.observationId][cfg.PLOT_DATA][idx]["substract_first_value"],
                    self.pj[cfg.CONVERTERS] if cfg.CONVERTERS in self.pj else {},
                    self.pj[cfg.OBSERVATIONS][self.observationId][cfg.PLOT_DATA][idx]["converters"],
                    log_level=logging.getLogger().getEffectiveLevel(),
                )

                if w2.error_msg:
                    QMessageBox.critical(
                        self,
                        cfg.programName,
                        "Impossible to plot data from file {}:\n{}".format(
                            os.path.basename(
                                self.pj[cfg.OBSERVATIONS][self.observationId][cfg.PLOT_DATA][idx]["file_path"]
                            ),
                            w2.error_msg,
                        ),
                    )
                    del w2
                    return False

                w2.setWindowFlags(Qt.WindowStaysOnTopHint)
                w2.sendEvent.connect(self.signal_from_widget)

                w2.show()
                self.ext_data_timer_list.append(QTimer())
                self.ext_data_timer_list[-1].setInterval(w2.time_out)
                self.ext_data_timer_list[-1].timeout.connect(lambda: self.timer_plot_data_out(w2))
                self.timer_plot_data_out(w2)

                self.plot_data[count] = w2

            count += 1

    # check if "filtered behaviors"
    if cfg.FILTERED_BEHAVIORS in self.pj[cfg.OBSERVATIONS][self.observationId]:
        self.load_behaviors_in_twEthogram(self.pj[cfg.OBSERVATIONS][self.observationId][cfg.FILTERED_BEHAVIORS])

    # restore windows state: dockwidget positions ...
    if self.saved_state is None:
        self.saved_state = self.saveState()
        self.restoreState(self.saved_state)
    else:
        try:
            self.restoreState(self.saved_state)
        except TypeError:
            logging.critical("state not restored: Type error")
            self.saved_state = self.saveState()
            self.restoreState(self.saved_state)

    for player in self.dw_player:
        player.setVisible(True)

    # initial synchro
    for n_player in range(1, len(self.dw_player)):
        self.sync_time(n_player, 0)

    self.mpv_timer_out(value=0.0)

    return True


def initialize_new_live_observation(self):
    """
    initialize a new live observation
    """
    logging.debug(f"function: initialize new live obs: {self.observationId}")

    self.playerType = cfg.LIVE

    self.pb_live_obs.setMinimumHeight(60)

    font = QFont()
    font.setPointSize(48)
    self.lb_current_media_time.setFont(font)

    for dw in [self.dwEthogram, self.dwSubjects, self.dwEvents]:
        dw.setVisible(True)

    self.w_live.setVisible(True)  # button start
    self.w_obs_info.setVisible(True)

    menu_options.update_menu(self)

    self.liveObservationStarted = False
    self.pb_live_obs.setText("Start live observation")

    if self.pj[cfg.OBSERVATIONS][self.observationId].get(cfg.START_FROM_CURRENT_TIME, False):
        current_time = util.seconds_of_day(datetime.datetime.now())
    elif self.pj[cfg.OBSERVATIONS][self.observationId].get(cfg.START_FROM_CURRENT_EPOCH_TIME, False):
        current_time = time.mktime(datetime.datetime.now().timetuple())
    else:
        current_time = 0

    self.lb_current_media_time.setText(util.convertTime(self.timeFormat, current_time))

    # display observation time interval (if any)
    self.lb_obs_time_interval.setVisible(True)
    self.display_statusbar_info(self.observationId)

    self.currentSubject = ""
    # store state behaviors for subject current state
    self.state_behaviors_codes = tuple(util.state_behavior_codes(self.pj[cfg.ETHOGRAM]))

    self.lbCurrentStates.setText("")

    self.liveStartTime = None
    self.liveTimer.stop()

    self.get_events_current_row()


def initialize_new_images_observation(self):
    """
    initialize a new observation from directories of images
    """

    for dw in [self.dwEthogram, self.dwSubjects, self.dwEvents]:
        dw.setVisible(True)
    self.w_live.setVisible(False)  # button start

    # check if directories are available
    ok, msg = project_functions.check_directories_availability(
        self.pj[cfg.OBSERVATIONS][self.observationId], self.projectFileName
    )

    if not ok:
        QMessageBox.critical(
            self,
            cfg.programName,
            (
                f"{msg}<br><br>The observation will be opened in VIEW mode.<br>"
                "It will not be possible to log events.<br>"
                "Modify the directoriy path(s) to point existing directory "
            ),
            QMessageBox.Ok | QMessageBox.Default,
            QMessageBox.NoButton,
        )
        self.playerType = cfg.VIEWER_IMAGES
        return

    # count number of images in all directories
    tot_images_number = 0
    for dir_path in self.pj[cfg.OBSERVATIONS][self.observationId].get(cfg.DIRECTORIES_LIST, []):
        result = util.dir_images_number(dir_path)
        tot_images_number += result.get("number of images", 0)

    if not tot_images_number:
        QMessageBox.critical(
            self,
            cfg.programName,
            (
                f"No images were found in directory(ies).<br><br>The observation will be opened in VIEW mode.<br>"
                "It will not be possible to log events.<br>"
                "Modify the directoriy path(s) to point existing directory "
            ),
            QMessageBox.Ok | QMessageBox.Default,
            QMessageBox.NoButton,
        )
        self.playerType = cfg.VIEWER_IMAGES
        return

    self.playerType = cfg.IMAGES
    # load image paths
    # directories user order is maintained
    # images are sorted inside each directory
    self.images_list = []
    for dir_path in self.pj[cfg.OBSERVATIONS][self.observationId].get(cfg.DIRECTORIES_LIST, []):
        for pattern in cfg.IMAGE_EXTENSIONS:
            self.images_list.extend(
                sorted(
                    list(
                        set(
                            [str(x) for x in pl.Path(dir_path).glob(pattern)]
                            + [str(x) for x in pl.Path(dir_path).glob(pattern.upper())]
                        )
                    )
                )
            )

    # logging.debug(self.images_list)

    self.image_idx = 0
    self.image_time_ref = None

    # self.w_live.setVisible(True)

    self.setDockOptions(QMainWindow.AnimatedDocks | QMainWindow.AllowNestedDocks)
    self.dw_player = []
    i = 0
    self.dw_player.append(player_dock_widget.DW_player(i, self))
    self.addDockWidget(Qt.TopDockWidgetArea, self.dw_player[i])
    self.dw_player[i].setFeatures(QDockWidget.DockWidgetFloatable | QDockWidget.DockWidgetMovable)

    self.dw_player[i].setVisible(True)

    # for receiving mouse event from frame viewer
    self.dw_player[i].frame_viewer.mouse_pressed_signal.connect(self.frame_image_clicked)

    # for receiving key event from dock widget
    self.dw_player[i].key_pressed_signal.connect(self.signal_from_widget)

    # for receiving resize event from dock widget
    self.dw_player[i].resize_signal.connect(self.resize_dw)

    self.dw_player[i].stack.setCurrentIndex(cfg.PICTURE_VIEWER)

    menu_options.update_menu(self)

    self.display_statusbar_info(self.observationId)

    self.currentSubject = ""
    # store state behaviors for subject current state
    self.state_behaviors_codes = tuple(util.state_behavior_codes(self.pj[cfg.ETHOGRAM]))

    # check if "filtered behaviors"
    if cfg.FILTERED_BEHAVIORS in self.pj[cfg.OBSERVATIONS][self.observationId]:
        self.load_behaviors_in_twEthogram(self.pj[cfg.OBSERVATIONS][self.observationId][cfg.FILTERED_BEHAVIORS])

    # restore windows state: dockwidget positions ...
    if self.saved_state is None:
        self.saved_state = self.saveState()
        self.restoreState(self.saved_state)
    else:
        try:
            self.restoreState(self.saved_state)
        except TypeError:
            logging.critical("state not restored: Type error")
            self.saved_state = self.saveState()
            self.restoreState(self.saved_state)

    """
    self.twEvents.setColumnCount(len(cfg.IMAGES_TW_EVENTS_FIELDS))
    self.twEvents.setHorizontalHeaderLabels(cfg.IMAGES_TW_EVENTS_FIELDS)
    """

    self.extract_frame(self.dw_player[i])
    self.w_obs_info.setVisible(True)

    self.get_events_current_row()
