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

import logging
import time
import tempfile
from decimal import Decimal
import pathlib as pl
from PyQt5.QtWidgets import QMessageBox, QFileDialog, QDateTimeEdit, QComboBox, QTableWidgetItem
from PyQt5.QtCore import Qt, QDateTime

from . import menu_options
from . import config as cfg
from . import dialog
from . import select_observations
from . import project_functions
from . import observation
from . import utilities as util


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

    file_name, filter_ = QFileDialog().getSaveFileName(self, "Export list of selected observations", "",
                                                       ";;".join(extended_file_formats))

    if file_name:
        output_format = file_formats[extended_file_formats.index(filter_)]
        if pl.Path(file_name).suffix != "." + output_format:
            file_name = str(pl.Path(file_name)) + "." + output_format
            # check if file name with extension already exists
            if pl.Path(file_name).is_file():
                if (dialog.MessageDialog(cfg.programName, f"The file {file_name} already exists.",
                                         [cfg.CANCEL, cfg.OVERWRITE]) == cfg.CANCEL):
                    return

        if not project_functions.export_observations_list(self.pj, selected_observations, file_name, output_format):
            QMessageBox.warning(self, cfg.programName, "File not created due to an error")


def observations_list(self):
    """
    show list of all observations of current project
    """

    if self.playerType == cfg.VIEWER:
        self.close_observation()

    result, selected_obs = self.selectObservations(cfg.SINGLE)

    if selected_obs:
        if result in [cfg.OPEN, cfg.VIEW, cfg.EDIT] and self.observationId:
            self.close_observation()
        if result == cfg.OPEN:
            load_observation(self, selected_obs[0], "start")
        if result == cfg.VIEW:
            load_observation(self, selected_obs[0], cfg.VIEW)
        if result == cfg.EDIT:
            if self.observationId != selected_obs[0]:
                self.new_observation(mode=cfg.EDIT, obsId=selected_obs[0])  # observation id to edit
            else:
                QMessageBox.warning(
                    self,
                    cfg.programName,
                    (f"The observation <b>{self.observationId}</b> is running!<br>"
                     "Close it before editing."),
                )


def open_observation(self, mode):
    """
    start or view an observation

    Args:
        mode (str): "start" to start observation
                    "view" to view observation
    """

    # check if current observation must be closed to open a new one
    if self.observationId:

        self.hide_data_files()
        response = dialog.MessageDialog(cfg.programName,
                                        "The current observation will be closed. Do you want to continue?",
                                        [cfg.YES, cfg.NO])
        if response == cfg.NO:
            self.show_data_files()
            return ""
        else:
            self.close_observation()

    if mode == "start":
        _, selectedObs = self.selectObservations(cfg.OPEN)
    if mode == cfg.VIEW:
        _, selectedObs = self.selectObservations(cfg.VIEW)

    if selectedObs:
        return load_observation(self, selectedObs[0], mode)
    else:
        return ""


def load_observation(self, obsId: str, mode: str = "start") -> str:
    """
    load observation obsId

    Args:
        obsId (str): observation id
        mode (str): "start" to start observation
                    "view"  to view observation
    """

    if obsId in self.pj[cfg.OBSERVATIONS]:

        self.observationId = obsId
        self.loadEventsInTW(self.observationId)

        if self.pj[cfg.OBSERVATIONS][self.observationId][cfg.TYPE] == cfg.LIVE:
            if mode == "start":
                self.playerType = cfg.LIVE
                self.initialize_new_live_observation()
            if mode == "view":
                self.playerType = cfg.VIEWER
                self.playMode = ""
                self.dwObservations.setVisible(True)

        if self.pj[cfg.OBSERVATIONS][self.observationId][cfg.TYPE] in [cfg.MEDIA]:

            if mode == "start":
                if not self.initialize_new_observation_mpv():
                    self.observationId = ""
                    self.twEvents.setRowCount(0)
                    menu_options.update_menu(self)
                    return "Error: loading observation problem"

            if mode == "view":
                self.playerType = cfg.VIEWER
                self.playMode = ""
                self.dwObservations.setVisible(True)

        menu_options.update_menu(self)
        # title of dock widget  “  ”
        self.dwObservations.setWindowTitle(f"Events for “{self.observationId}” observation")
        return ""

    else:
        return "Error: Observation not found"


def edit_observation(self):
    """
    edit observation
    """

    # check if current observation must be closed to open a new one
    if self.observationId:
        # hide data plot
        self.hide_data_files()
        if (dialog.MessageDialog(cfg.programName, "The current observation will be closed. Do you want to continue?",
                                 [cfg.YES, cfg.NO]) == cfg.NO):
            # restore plots
            self.show_data_files()
            return
        else:
            self.close_observation()

    _, selected_observations = self.selectObservations(cfg.EDIT)

    if selected_observations:
        self.new_observation(mode=cfg.EDIT, obsId=selected_observations[0])


def observation_length(self, selected_observations: list) -> tuple:
    """
    max length of selected observations
    total media length

    Args:
        selected_observations (list): list of selected observations

    Returns:
        float: maximum media length for all observations
        float: total media length for all observations
    """
    selectedObsTotalMediaLength = Decimal("0.0")
    max_obs_length = 0
    for obs_id in selected_observations:
        obs_length = project_functions.observation_total_length(self.pj[cfg.OBSERVATIONS][obs_id])
        if obs_length in [Decimal("0"), Decimal("-1")]:
            selectedObsTotalMediaLength = -1
            break
        max_obs_length = max(max_obs_length, obs_length)
        selectedObsTotalMediaLength += obs_length

    # an observation media length is not available
    if selectedObsTotalMediaLength == -1:
        # propose to user to use max event time
        if (dialog.MessageDialog(
                cfg.programName,
            (f"A media length is not available for the observation <b>{obs_id}</b>.<br>"
             "Use last event time as media length?"),
            [cfg.YES, cfg.NO],
        ) == cfg.YES):
            maxTime = 0  # max length for all events all subjects
            max_length = 0
            for obs_id in selected_observations:
                if self.pj[cfg.OBSERVATIONS][obs_id][cfg.EVENTS]:
                    maxTime += max(self.pj[cfg.OBSERVATIONS][obs_id][cfg.EVENTS])[0]
                    max_length = max(max_length, max(self.pj[cfg.OBSERVATIONS][obs_id][cfg.EVENTS])[0])

            logging.debug(f"max time all events all subjects: {maxTime}")

            max_obs_length = max_length
            selectedObsTotalMediaLength = maxTime

        else:
            max_obs_length = -1
            selectedObsTotalMediaLength = Decimal("-1")

    return (max_obs_length, selectedObsTotalMediaLength)


def new_observation(self, mode=cfg.NEW, obsId=""):
    """
    define a new observation or edit an existing observation
    """
    # check if current observation must be closed to create a new one
    if mode == cfg.NEW and self.observationId:
        # hide data plot
        self.hide_data_files()
        if (dialog.MessageDialog(cfg.programName, "The current observation will be closed. Do you want to continue?",
                                 [cfg.YES, cfg.NO]) == cfg.NO):

            # show data plot
            self.show_data_files()
            return
        else:
            self.close_observation()

    observationWindow = observation.Observation(
        tmp_dir=self.ffmpeg_cache_dir if
        (self.ffmpeg_cache_dir and pl.Path(self.ffmpeg_cache_dir).is_dir()) else tempfile.gettempdir(),
        project_path=self.projectFileName,
        converters=self.pj[cfg.CONVERTERS] if cfg.CONVERTERS in self.pj else {},
        time_format=self.timeFormat,
    )

    observationWindow.pj = dict(self.pj)
    observationWindow.mode = mode
    observationWindow.mem_obs_id = obsId
    observationWindow.chunk_length = self.chunk_length
    observationWindow.dteDate.setDateTime(QDateTime.currentDateTime())
    observationWindow.ffmpeg_bin = self.ffmpeg_bin
    observationWindow.project_file_name = self.projectFileName

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
            if (mode == cfg.EDIT and cfg.INDEPENDENT_VARIABLES in self.pj[cfg.OBSERVATIONS][obsId] and
                    indepVarLabel in self.pj[cfg.OBSERVATIONS][obsId][cfg.INDEPENDENT_VARIABLES]):
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
                        self.pj[cfg.INDEPENDENT_VARIABLES][i]["possible values"].split(",").index(txt))
                observationWindow.twIndepVariables.setCellWidget(observationWindow.twIndepVariables.rowCount() - 1, 2,
                                                                 comboBox)

            elif self.pj[cfg.INDEPENDENT_VARIABLES][i]["type"] == cfg.TIMESTAMP:
                cal = QDateTimeEdit()
                cal.setDisplayFormat("yyyy-MM-dd hh:mm:ss")
                cal.setCalendarPopup(True)
                if txt:
                    cal.setDateTime(QDateTime.fromString(txt, "yyyy-MM-ddThh:mm:ss"))
                observationWindow.twIndepVariables.setCellWidget(observationWindow.twIndepVariables.rowCount() - 1, 2,
                                                                 cal)
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
            self.pj[cfg.OBSERVATIONS][obsId]["date"] = self.pj[cfg.OBSERVATIONS][obsId]["date"].replace(" ",
                                                                                                        "T") + ":00"
        except ValueError:
            pass

        observationWindow.dteDate.setDateTime(
            QDateTime.fromString(self.pj[cfg.OBSERVATIONS][obsId]["date"], "yyyy-MM-ddThh:mm:ss"))
        observationWindow.teDescription.setPlainText(self.pj[cfg.OBSERVATIONS][obsId][cfg.DESCRIPTION])

        try:
            observationWindow.mediaDurations = self.pj[cfg.OBSERVATIONS][obsId][cfg.MEDIA_INFO]["length"]
            observationWindow.mediaFPS = self.pj[cfg.OBSERVATIONS][obsId][cfg.MEDIA_INFO]["fps"]
        except Exception:
            observationWindow.mediaDurations = {}
            observationWindow.mediaFPS = {}

        try:
            if "hasVideo" in self.pj[cfg.OBSERVATIONS][obsId][cfg.MEDIA_INFO]:
                observationWindow.mediaHasVideo = self.pj[cfg.OBSERVATIONS][obsId][cfg.MEDIA_INFO]["hasVideo"]
            if "hasAudio" in self.pj[cfg.OBSERVATIONS][obsId][cfg.MEDIA_INFO]:
                observationWindow.mediaHasAudio = self.pj[cfg.OBSERVATIONS][obsId][cfg.MEDIA_INFO]["hasAudio"]
        except Exception:
            logging.info("No Video/Audio information")

        # offset
        observationWindow.obs_time_offset.set_time(self.pj[cfg.OBSERVATIONS][obsId][cfg.TIME_OFFSET])

        observationWindow.twVideo1.setRowCount(0)
        for player in self.pj[cfg.OBSERVATIONS][obsId][cfg.FILE]:
            if player in self.pj[cfg.OBSERVATIONS][obsId][cfg.FILE] and self.pj[cfg.OBSERVATIONS][obsId][
                    cfg.FILE][player]:
                for mediaFile in self.pj[cfg.OBSERVATIONS][obsId][cfg.FILE][player]:
                    observationWindow.twVideo1.setRowCount(observationWindow.twVideo1.rowCount() + 1)

                    combobox = QComboBox()
                    combobox.addItems(cfg.ALL_PLAYERS)
                    combobox.setCurrentIndex(int(player) - 1)
                    observationWindow.twVideo1.setCellWidget(observationWindow.twVideo1.rowCount() - 1, 0, combobox)

                    item = QTableWidgetItem(mediaFile)
                    item.setFlags(Qt.ItemIsEnabled)
                    observationWindow.twVideo1.setItem(observationWindow.twVideo1.rowCount() - 1, 2, item)

                    # set offset
                    try:
                        observationWindow.twVideo1.setItem(
                            observationWindow.twVideo1.rowCount() - 1,
                            1,
                            QTableWidgetItem(str(self.pj[cfg.OBSERVATIONS][obsId][cfg.MEDIA_INFO]["offset"][player])),
                        )
                    except Exception:
                        observationWindow.twVideo1.setItem(observationWindow.twVideo1.rowCount() - 1, 1,
                                                           QTableWidgetItem("0.0"))

                    # duration and FPS
                    try:
                        item = QTableWidgetItem(
                            util.seconds2time(self.pj[cfg.OBSERVATIONS][obsId][cfg.MEDIA_INFO][cfg.LENGTH][mediaFile]))
                        item.setFlags(Qt.ItemIsEnabled)
                        observationWindow.twVideo1.setItem(observationWindow.twVideo1.rowCount() - 1, 3, item)

                        item = QTableWidgetItem(
                            f"{self.pj[cfg.OBSERVATIONS][obsId][cfg.MEDIA_INFO][cfg.FPS][mediaFile]:.2f}")
                        item.setFlags(Qt.ItemIsEnabled)
                        observationWindow.twVideo1.setItem(observationWindow.twVideo1.rowCount() - 1, 4, item)
                    except Exception:
                        pass

                    # has_video has_audio
                    try:
                        item = QTableWidgetItem(
                            str(self.pj[cfg.OBSERVATIONS][obsId][cfg.MEDIA_INFO]["hasVideo"][mediaFile]))
                        item.setFlags(Qt.ItemIsEnabled)
                        observationWindow.twVideo1.setItem(observationWindow.twVideo1.rowCount() - 1, 5, item)

                        item = QTableWidgetItem(
                            str(self.pj[cfg.OBSERVATIONS][obsId][cfg.MEDIA_INFO]["hasAudio"][mediaFile]))
                        item.setFlags(Qt.ItemIsEnabled)
                        observationWindow.twVideo1.setItem(observationWindow.twVideo1.rowCount() - 1, 6, item)
                    except Exception:
                        pass

        if self.pj[cfg.OBSERVATIONS][obsId]["type"] in [cfg.MEDIA]:
            observationWindow.tabProjectType.setCurrentIndex(cfg.MEDIA_TAB_IDX)

        if self.pj[cfg.OBSERVATIONS][obsId]["type"] in [cfg.LIVE]:
            observationWindow.tabProjectType.setCurrentIndex(cfg.LIVE_TAB_IDX)
            # sampling time
            observationWindow.sbScanSampling.setValue(self.pj[cfg.OBSERVATIONS][obsId].get(cfg.SCAN_SAMPLING_TIME, 0))
            # start from current time
            observationWindow.cb_start_from_current_time.setChecked(
                self.pj[cfg.OBSERVATIONS][obsId].get(cfg.START_FROM_CURRENT_TIME, False) or
                self.pj[cfg.OBSERVATIONS][obsId].get(cfg.START_FROM_CURRENT_EPOCH_TIME, False))
            # day/epoch time
            observationWindow.rb_day_time.setChecked(self.pj[cfg.OBSERVATIONS][obsId].get(
                cfg.START_FROM_CURRENT_TIME, False))
            observationWindow.rb_epoch_time.setChecked(self.pj[cfg.OBSERVATIONS][obsId].get(
                cfg.START_FROM_CURRENT_EPOCH_TIME, False))

        # spectrogram
        observationWindow.cbVisualizeSpectrogram.setEnabled(True)
        observationWindow.cbVisualizeSpectrogram.setChecked(self.pj[cfg.OBSERVATIONS][obsId].get(
            cfg.VISUALIZE_SPECTROGRAM, False))

        # waveform
        observationWindow.cb_visualize_waveform.setEnabled(True)
        observationWindow.cb_visualize_waveform.setChecked(self.pj[cfg.OBSERVATIONS][obsId].get(
            cfg.VISUALIZE_WAVEFORM, False))

        # observation time interval
        observationWindow.cb_observation_time_interval.setEnabled(True)
        if self.pj[cfg.OBSERVATIONS][obsId].get(cfg.OBSERVATION_TIME_INTERVAL, [0, 0]) != [0, 0]:
            observationWindow.cb_observation_time_interval.setChecked(True)
            observationWindow.observation_time_interval = self.pj[cfg.OBSERVATIONS][obsId].get(
                cfg.OBSERVATION_TIME_INTERVAL, [0, 0])
            observationWindow.cb_observation_time_interval.setText(
                ("Limit observation to a time interval: "
                 f"{self.pj[cfg.OBSERVATIONS][obsId][cfg.OBSERVATION_TIME_INTERVAL][0]} - "
                 f"{self.pj[cfg.OBSERVATIONS][obsId][cfg.OBSERVATION_TIME_INTERVAL][1]}"))

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
                                    self.pj[cfg.OBSERVATIONS][obsId][cfg.PLOT_DATA][idx2][cfg.DATA_PLOT_FIELDS[idx3]]))

                            observationWindow.tw_data_files.setCellWidget(
                                observationWindow.tw_data_files.rowCount() - 1, cfg.PLOT_DATA_PLOTCOLOR_IDX, combobox)
                        elif idx3 == cfg.PLOT_DATA_SUBSTRACT1STVALUE_IDX:
                            combobox2 = QComboBox()
                            combobox2.addItems(["False", "True"])
                            combobox2.setCurrentIndex(["False", "True"].index(
                                self.pj[cfg.OBSERVATIONS][obsId][cfg.PLOT_DATA][idx2][cfg.DATA_PLOT_FIELDS[idx3]]))

                            observationWindow.tw_data_files.setCellWidget(
                                observationWindow.tw_data_files.rowCount() - 1,
                                cfg.PLOT_DATA_SUBSTRACT1STVALUE_IDX,
                                combobox2,
                            )
                        elif idx3 == cfg.PLOT_DATA_CONVERTERS_IDX:
                            # convert dict to str
                            """
                            s = ""
                            for conv in self.pj[OBSERVATIONS][obsId][PLOT_DATA][idx2][DATA_PLOT_FIELDS[idx3]]:
                                s += "," if s else ""
                                s += "{}:{}".format(conv, self.pj[OBSERVATIONS][obsId][PLOT_DATA][idx2][DATA_PLOT_FIELDS[idx3]][conv])
                            """
                            observationWindow.tw_data_files.setItem(
                                observationWindow.tw_data_files.rowCount() - 1,
                                idx3,
                                QTableWidgetItem(
                                    str(self.pj[cfg.OBSERVATIONS][obsId][cfg.PLOT_DATA][idx2][
                                        cfg.DATA_PLOT_FIELDS[idx3]])),
                            )

                        else:
                            observationWindow.tw_data_files.setItem(
                                observationWindow.tw_data_files.rowCount() - 1,
                                idx3,
                                QTableWidgetItem(
                                    self.pj[cfg.OBSERVATIONS][obsId][cfg.PLOT_DATA][idx2][cfg.DATA_PLOT_FIELDS[idx3]]),
                            )

        # disabled due to problem when video goes back
        # if CLOSE_BEHAVIORS_BETWEEN_VIDEOS in self.pj[OBSERVATIONS][obsId]:
        #    observationWindow.cbCloseCurrentBehaviorsBetweenVideo.setChecked(self.pj[OBSERVATIONS][obsId][CLOSE_BEHAVIORS_BETWEEN_VIDEOS])

    rv = observationWindow.exec_()

    if rv:

        self.projectChanged = True

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
        # observation type: read project type from tab text
        self.pj[cfg.OBSERVATIONS][new_obs_id][cfg.TYPE] = observationWindow.tabProjectType.tabText(
            observationWindow.tabProjectType.currentIndex()).upper()

        # independent variables for observation
        self.pj[cfg.OBSERVATIONS][new_obs_id][cfg.INDEPENDENT_VARIABLES] = {}
        for r in range(observationWindow.twIndepVariables.rowCount()):

            # set dictionary as label (col 0) => value (col 2)
            if observationWindow.twIndepVariables.item(r, 1).text() == cfg.SET_OF_VALUES:
                self.pj[
                    cfg.OBSERVATIONS][new_obs_id][cfg.INDEPENDENT_VARIABLES][observationWindow.twIndepVariables.item(
                        r, 0).text()] = observationWindow.twIndepVariables.cellWidget(r, 2).currentText()
            elif observationWindow.twIndepVariables.item(r, 1).text() == cfg.TIMESTAMP:
                self.pj[cfg.OBSERVATIONS][new_obs_id][cfg.INDEPENDENT_VARIABLES][
                    observationWindow.twIndepVariables.item(r,
                                                            0).text()] = (observationWindow.twIndepVariables.cellWidget(
                                                                r, 2).dateTime().toString(Qt.ISODate))
            else:
                self.pj[cfg.OBSERVATIONS][new_obs_id][cfg.INDEPENDENT_VARIABLES][
                    observationWindow.twIndepVariables.item(r, 0).text()] = observationWindow.twIndepVariables.item(
                        r, 2).text()

        # observation time offset
        self.pj[cfg.OBSERVATIONS][new_obs_id][cfg.TIME_OFFSET] = observationWindow.obs_time_offset.get_time()

        if observationWindow.cb_observation_time_interval.isChecked():
            self.pj[cfg.OBSERVATIONS][new_obs_id][
                cfg.OBSERVATION_TIME_INTERVAL] = observationWindow.observation_time_interval

        self.display_statusbar_info(new_obs_id)

        # visualize spectrogram
        self.pj[cfg.OBSERVATIONS][new_obs_id][
            cfg.VISUALIZE_SPECTROGRAM] = observationWindow.cbVisualizeSpectrogram.isChecked()
        # visualize spectrogram
        self.pj[cfg.OBSERVATIONS][new_obs_id][
            cfg.VISUALIZE_WAVEFORM] = observationWindow.cb_visualize_waveform.isChecked()
        # time interval for observation
        self.pj[cfg.OBSERVATIONS][new_obs_id][
            cfg.OBSERVATION_TIME_INTERVAL] = observationWindow.observation_time_interval

        # plot data
        if observationWindow.tw_data_files.rowCount():
            self.pj[cfg.OBSERVATIONS][new_obs_id][cfg.PLOT_DATA] = {}
            for row in range(observationWindow.tw_data_files.rowCount()):
                self.pj[cfg.OBSERVATIONS][new_obs_id][cfg.PLOT_DATA][str(row)] = {}
                for idx2 in cfg.DATA_PLOT_FIELDS:
                    if idx2 in [cfg.PLOT_DATA_PLOTCOLOR_IDX, cfg.PLOT_DATA_SUBSTRACT1STVALUE_IDX]:
                        self.pj[cfg.OBSERVATIONS][new_obs_id][cfg.PLOT_DATA][
                            str(row)][cfg.DATA_PLOT_FIELDS[idx2]] = observationWindow.tw_data_files.cellWidget(
                                row, idx2).currentText()

                    elif idx2 == cfg.PLOT_DATA_CONVERTERS_IDX:
                        if observationWindow.tw_data_files.item(row, idx2).text():
                            self.pj[cfg.OBSERVATIONS][new_obs_id][cfg.PLOT_DATA][str(row)][
                                cfg.DATA_PLOT_FIELDS[idx2]] = eval(
                                    observationWindow.tw_data_files.item(row, idx2).text())
                        else:
                            self.pj[cfg.OBSERVATIONS][new_obs_id][cfg.PLOT_DATA][str(row)][
                                cfg.DATA_PLOT_FIELDS[idx2]] = {}

                    else:
                        self.pj[cfg.OBSERVATIONS][new_obs_id][cfg.PLOT_DATA][str(row)][
                            cfg.DATA_PLOT_FIELDS[idx2]] = observationWindow.tw_data_files.item(row, idx2).text()

        # Close current behaviors between video
        # disabled due to problem when video goes back
        # self.pj[OBSERVATIONS][new_obs_id][CLOSE_BEHAVIORS_BETWEEN_VIDEOS] =
        # observationWindow.cbCloseCurrentBehaviorsBetweenVideo.isChecked()
        self.pj[cfg.OBSERVATIONS][new_obs_id][cfg.CLOSE_BEHAVIORS_BETWEEN_VIDEOS] = False

        if self.pj[cfg.OBSERVATIONS][new_obs_id][cfg.TYPE] in [cfg.LIVE]:
            self.pj[cfg.OBSERVATIONS][new_obs_id][cfg.SCAN_SAMPLING_TIME] = observationWindow.sbScanSampling.value()
            self.pj[cfg.OBSERVATIONS][new_obs_id][cfg.START_FROM_CURRENT_TIME] = (
                observationWindow.cb_start_from_current_time.isChecked() and observationWindow.rb_day_time.isChecked())
            self.pj[cfg.OBSERVATIONS][new_obs_id][cfg.START_FROM_CURRENT_EPOCH_TIME] = (
                observationWindow.cb_start_from_current_time.isChecked() and
                observationWindow.rb_epoch_time.isChecked())

        # media file
        self.pj[cfg.OBSERVATIONS][new_obs_id][cfg.FILE] = {}

        # media
        if self.pj[cfg.OBSERVATIONS][new_obs_id][cfg.TYPE] in [cfg.MEDIA]:

            self.pj[cfg.OBSERVATIONS][new_obs_id][cfg.MEDIA_INFO] = {
                cfg.LENGTH: observationWindow.mediaDurations,
                cfg.FPS: observationWindow.mediaFPS,
            }

            try:
                self.pj[cfg.OBSERVATIONS][new_obs_id][cfg.MEDIA_INFO]["hasVideo"] = observationWindow.mediaHasVideo
                self.pj[cfg.OBSERVATIONS][new_obs_id][cfg.MEDIA_INFO]["hasAudio"] = observationWindow.mediaHasAudio
            except Exception:
                logging.info("error with media_info information")

            self.pj[cfg.OBSERVATIONS][new_obs_id][cfg.MEDIA_INFO]["offset"] = {}

            logging.debug(f"media_info: {self.pj[cfg.OBSERVATIONS][new_obs_id][cfg.MEDIA_INFO]}")

            for i in range(cfg.N_PLAYER):
                self.pj[cfg.OBSERVATIONS][new_obs_id][cfg.FILE][str(i + 1)] = []

            for row in range(observationWindow.twVideo1.rowCount()):
                self.pj[cfg.OBSERVATIONS][new_obs_id][cfg.FILE][observationWindow.twVideo1.cellWidget(
                    row, 0).currentText()].append(observationWindow.twVideo1.item(row, 2).text())
                # store offset for media player
                self.pj[cfg.OBSERVATIONS][new_obs_id][cfg.MEDIA_INFO]["offset"][observationWindow.twVideo1.cellWidget(
                    row, 0).currentText()] = float(observationWindow.twVideo1.item(row, 1).text())

        if rv == 1:  # save
            self.observationId = ""
            menu_options.update_menu(self)

        if rv == 2:  # start
            self.observationId = new_obs_id

            # title of dock widget
            self.dwObservations.setWindowTitle(f'Events for "{self.observationId}" observation')

            if self.pj[cfg.OBSERVATIONS][self.observationId][cfg.TYPE] in [cfg.LIVE]:

                self.playerType = cfg.LIVE
                self.initialize_new_live_observation()

            elif self.pj[cfg.OBSERVATIONS][self.observationId][cfg.TYPE] in [cfg.MEDIA]:
                self.playerType = cfg.VLC
                # load events in table widget
                if mode == cfg.EDIT:
                    self.loadEventsInTW(self.observationId)

                self.initialize_new_observation_mpv()

            menu_options.update_menu(self)