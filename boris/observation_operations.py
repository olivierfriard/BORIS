"""
BORIS
Behavioral Observation Research Interactive Software
Copyright 2012-2025 Olivier Friard

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
import json
import subprocess
import socket
import sys
from decimal import Decimal as dec
import pathlib as pl
import datetime as dt
from typing import List, Tuple, Optional


from PySide6.QtWidgets import (
    QMessageBox,
    QFileDialog,
    QDateTimeEdit,
    QComboBox,
    QTableWidgetItem,
    QSlider,
    QMainWindow,
    QDockWidget,
)
from PySide6.QtCore import Qt, QDateTime, QTimer
from PySide6.QtGui import QFont, QIcon, QTextCursor

from PySide6 import QtTest

from . import menu_options
from . import config as cfg
from . import dialog
from . import select_observations
from . import project_functions
from . import observation
from . import utilities as util
from . import plot_data_module
from . import player_dock_widget
from . import gui_utilities
from . import video_operations
from . import state_events


def export_observations_list_clicked(self):
    """
    export the list of observations
    """

    resultStr, selected_observations = select_observations.select_observations2(self, cfg.MULTIPLE)
    if not resultStr or not selected_observations:
        return

    file_formats = [
        cfg.TSV,
        cfg.CSV,
        cfg.ODS,
        cfg.XLSX,
        cfg.XLS,
        cfg.HTML,
    ]

    file_name, filter_ = QFileDialog().getSaveFileName(self, "Export list of selected observations", "", ";;".join(file_formats))

    if not file_name:
        return

    output_format = cfg.FILE_NAME_SUFFIX[filter_]
    if pl.Path(file_name).suffix != "." + output_format:
        file_name = str(pl.Path(file_name)) + "." + output_format
        # check if file name with extension already exists
        if pl.Path(file_name).is_file():
            if dialog.MessageDialog(cfg.programName, f"The file {file_name} already exists.", [cfg.CANCEL, cfg.OVERWRITE]) == cfg.CANCEL:
                return

    if not project_functions.export_observations_list(self.pj, selected_observations, file_name, output_format):
        QMessageBox.warning(self, cfg.programName, "File not created due to an error")


def observations_list(self):
    """
    show list of all observations of current project
    """

    logging.debug("observations list")

    if self.playerType in cfg.VIEWERS:
        close_observation(self)

    result, selected_obs = select_observations.select_observations2(self, cfg.SINGLE)

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
                (f"The observation <b>{self.observationId}</b> is running!<br>Close it before editing."),
            )

    logging.debug("end observations list")


def open_observation(self, mode: str) -> str:
    """
    start or view an observation

    Args:
        mode (str): "start" to start observation
                    "view" to view observation
    """

    logging.debug("open observation")

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
        _, selected_observations = select_observations.select_observations2(self, cfg.OPEN)
    if mode == cfg.VIEW:
        _, selected_observations = select_observations.select_observations2(self, cfg.VIEW)

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

    logging.debug("load observation")

    if obs_id not in self.pj[cfg.OBSERVATIONS]:
        return "Error: Observation not found"

    if self.pj[cfg.OBSERVATIONS][obs_id][cfg.TYPE] not in (cfg.IMAGES, cfg.LIVE, cfg.MEDIA):
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
                close_observation(self)
                # self.observationId = ""
                # self.twEvents.setRowCount(0)
                # menu_options.update_menu(self)
                return "Error: loading observation problem"

        if mode == cfg.VIEW:
            self.playerType = cfg.VIEWER_MEDIA
            self.dwEvents.setVisible(True)

    self.load_tw_events(self.observationId)

    menu_options.update_menu(self)
    # title of dock widget  “  ”
    self.dwEvents.setWindowTitle(f"Events for “{self.observationId}” observation")

    logging.debug("end load observation")
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
            dialog.MessageDialog(cfg.programName, "The current observation will be closed. Do you want to continue?", (cfg.YES, cfg.NO))
            == cfg.NO
        ):
            # restore plots
            self.show_data_files()
            return
        else:
            close_observation(self)

    _, selected_observations = select_observations.select_observations2(self, cfg.EDIT, windows_title="Edit observation")

    if selected_observations:
        new_observation(self, mode=cfg.EDIT, obsId=selected_observations[0])


def remove_observations(self):
    """
    remove observations from project file
    """

    _, selected_observations = select_observations.select_observations2(self, cfg.MULTIPLE, windows_title="Remove observations")
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


def coding_time(observations: dict, observations_list: list) -> Tuple[Optional[dec], Optional[dec], Optional[dec]]:
    """
    returns first even timestamp, last event timestamp and duration of observation

    Args:
        observations (dict): observations of project
        observations_list (list): list of selected observations

    Returns:
        decimal.Decimal: time of first coded event, None if no event, dec(NaN) if no timestamp
        decimal.Decimal: time of last coded event, None if no event, dec(NaN) if no timestamp
        decimal.Decimal: duration of coding, None if no event, dec(NaN) if no timestamp

    """
    start_coding_list = []
    end_coding_list = []
    for obs_id in observations_list:
        observation = observations[obs_id]
        if observation[cfg.EVENTS]:
            # check if events contain a NA timestamp
            if [event[cfg.EVENT_TIME_FIELD_IDX] for event in observation[cfg.EVENTS] if event[cfg.EVENT_TIME_FIELD_IDX].is_nan()]:
                return dec("NaN"), dec("NaN"), dec("NaN")
            start_coding_list.append(observation[cfg.EVENTS][0][cfg.EVENT_TIME_FIELD_IDX])
            end_coding_list.append(observation[cfg.EVENTS][-1][cfg.EVENT_TIME_FIELD_IDX])

    if not start_coding_list:
        start_coding = None
    else:
        if start_coding_list == [x for x in start_coding_list if not x.is_nan()]:
            start_coding = min([x for x in start_coding_list if not x.is_nan()])
        else:
            start_coding = dec("NaN")

    if not end_coding_list:
        end_coding = None
    else:
        if end_coding_list == [x for x in end_coding_list if not x.is_nan()]:
            end_coding = min([x for x in end_coding_list if not x.is_nan()])
        else:
            end_coding = dec("NaN")

    if any((start_coding is None, end_coding is None)):
        coding_duration = None
    elif any((start_coding.is_nan(), end_coding.is_nan())):
        coding_duration = dec("NaN")
    else:
        coding_duration = end_coding - start_coding

    return start_coding, end_coding, coding_duration


def time_intervals_range(observations: dict, observations_list: list) -> Tuple[Optional[dec], Optional[dec]]:
    """
    returns earliest start interval and latest end interval

    Args:
        observations (dict): observations of project
        observations_list (list): list of selected observations

    Returns:
        decimal.Decimal: time of earliest start interval
        decimal.Decimal: time of latest end interval

    """
    start_interval_list: list = []
    end_interval_list: list = []
    for obs_id in observations_list:
        observation = observations[obs_id]
        offset = observation[cfg.TIME_OFFSET]
        # check if observation interval is defined
        if (
            not observation.get(cfg.OBSERVATION_TIME_INTERVAL, [None, None])[0]
            and not observation.get(cfg.OBSERVATION_TIME_INTERVAL, [None, None])[1]
        ):
            return None, None

        start_interval_list.append(dec(observation[cfg.OBSERVATION_TIME_INTERVAL][0]) + offset)
        end_interval_list.append(dec(observation[cfg.OBSERVATION_TIME_INTERVAL][1]) + offset)

    if not start_interval_list:
        earliest_start_interval = None
    else:
        earliest_start_interval = min([x for x in start_interval_list])

    if not end_interval_list:
        latest_end_interval = None
    else:
        latest_end_interval = max([x for x in end_interval_list])

    return earliest_start_interval, latest_end_interval


def observation_total_length(observation: dict) -> dec:
    """
    Observation media duration (if any)

    media observation: if media duration is not available returns 0
                       if more media are queued, returns sum of media duration
                       if the last event is recorded after the length of media returns the last event time

    live observation: returns last event time

    observation from pictures: returns last event
                               if no events returns dec(0)
                               if no time returns dec(-2)


    Args:
        observation (dict): observation dictionary

    Returns:
        decimal.Decimal: total length in seconds (-2 if observation from pictures)

    """

    if observation[cfg.TYPE] == cfg.IMAGES:
        if observation[cfg.EVENTS]:
            try:
                first_event = obs_length = min(observation[cfg.EVENTS])[cfg.TW_OBS_FIELD[cfg.IMAGES]["time"]]
                last_event = obs_length = max(observation[cfg.EVENTS])[cfg.TW_OBS_FIELD[cfg.IMAGES]["time"]]
                obs_length = last_event - first_event
            except Exception:
                logging.critical("Length of observation from images not available")
                obs_length = dec(-2)
        else:
            obs_length = dec(0)
        return obs_length

    if observation[cfg.TYPE] == cfg.LIVE:
        if observation[cfg.EVENTS]:
            obs_length = max(observation[cfg.EVENTS])[cfg.EVENT_TIME_FIELD_IDX]
        else:
            obs_length = dec(0)
        return obs_length

    if observation[cfg.TYPE] == cfg.MEDIA:
        media_max_total_length = dec(0)

        media_total_length = {}

        for nplayer in observation[cfg.FILE]:
            if not observation[cfg.FILE][nplayer]:
                continue

            media_total_length[nplayer] = dec(0)
            for mediaFile in observation[cfg.FILE][nplayer]:
                mediaLength = 0
                try:
                    mediaLength = observation[cfg.MEDIA_INFO][cfg.LENGTH][mediaFile]
                    media_total_length[nplayer] += dec(mediaLength)
                except Exception:
                    logging.critical(f"media length not found for {mediaFile}")
                    mediaLength = -1
                    media_total_length[nplayer] = -1
                    break

        if -1 in [media_total_length[x] for x in media_total_length]:
            return dec(-1)

        # totalMediaLength = max([total_media_length[x] for x in total_media_length])

        media_max_total_length = max([media_total_length[x] for x in media_total_length])

        if observation[cfg.EVENTS]:
            if max(observation[cfg.EVENTS])[cfg.EVENT_TIME_FIELD_IDX] > media_max_total_length:
                media_max_total_length = max(observation[cfg.EVENTS])[cfg.EVENT_TIME_FIELD_IDX]

        return media_max_total_length

    logging.critical("observation not LIVE nor MEDIA")

    return dec(0)


def media_duration(observations: dict, selected_observations: list) -> Tuple[Optional[dec], Optional[dec]]:
    """
    maximum media duration and total media duration of selected observations

    Args:
        observations (dict): observations dict
        selected_observations (list): list of selected observations

    Returns:
        decimal.Decimal: maximum media duration for all observations, None if observation not from media
        decimal.Decimal: total media duration for all observations, None if observation not from media
    """
    max_media_duration_all_obs = dec("0.0")
    total_media_duration_all_obs = dec("0.0")
    for obs_id in selected_observations:
        if observations[obs_id][cfg.TYPE] != cfg.MEDIA:
            return None, None
        total_media_duration = dec(0)

        nplayer = "1"  # check only player 1 as it must contain the longest media file
        for media_file in observations[obs_id][cfg.FILE][nplayer]:
            try:
                media_duration = observations[obs_id][cfg.MEDIA_INFO][cfg.LENGTH][media_file]
                total_media_duration += dec(media_duration)
            except Exception:
                logging.critical(f"media length not found for {media_file}")
                return None, None
        total_media_duration_all_obs += total_media_duration
        max_media_duration_all_obs = max(max_media_duration_all_obs, total_media_duration)

    return max_media_duration_all_obs, total_media_duration_all_obs


def observation_length(pj: dict, selected_observations: list) -> tuple:
    """
    max length of selected observations
    total media length

    Args:
        selected_observations (list): list of selected observations

    Returns:
        decimal.Decimal: maximum media length for all observations
        decimal.Decimal: total media length for all observations
    """
    selectedObsTotalMediaLength = dec("0.0")
    max_obs_length = dec(0)
    for obs_id in selected_observations:
        obs_length = observation_total_length(pj[cfg.OBSERVATIONS][obs_id])
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
                (f"The observation length is not available (<b>{obs_id}</b>).<br>Use last event time as observation length?"),
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


def new_observation(self, mode: str = cfg.NEW, obsId: str = "") -> None:
    """
    define a new observation or edit an existing observation

    Args:
        mode (str): NEW or EDIT
        obsId (str): observation Id to be edited

    Retruns:
        None

    """
    # check if current observation must be closed to create a new one
    if mode == cfg.NEW and self.observationId:
        # hide data plot
        self.hide_data_files()
        if (
            dialog.MessageDialog(cfg.programName, "The current observation will be closed. Do you want to continue?", (cfg.YES, cfg.NO))
            == cfg.NO
        ):
            # show data plot
            self.show_data_files()
            return
        else:
            close_observation(self)

    observationWindow = observation.Observation(
        tmp_dir=self.ffmpeg_cache_dir if (self.ffmpeg_cache_dir and pl.Path(self.ffmpeg_cache_dir).is_dir()) else tempfile.gettempdir(),
        project_path=self.projectFileName,
        converters=self.pj.get(cfg.CONVERTERS, {}),
        time_format=self.timeFormat,
    )

    observationWindow.pj = dict(self.pj)
    observationWindow.sw_observation_type.setCurrentIndex(0)  # no observation type
    observationWindow.mode = mode
    observationWindow.mem_obs_id = obsId
    observationWindow.chunk_length = self.chunk_length
    observationWindow.dteDate.setDateTime(QDateTime.currentDateTime())
    # observationWindow.de_date_offset.setDateTime(QDateTime.currentDateTime())
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
                    comboBox.setCurrentIndex(self.pj[cfg.INDEPENDENT_VARIABLES][i]["possible values"].split(",").index(txt))
                observationWindow.twIndepVariables.setCellWidget(observationWindow.twIndepVariables.rowCount() - 1, 2, comboBox)

            elif self.pj[cfg.INDEPENDENT_VARIABLES][i]["type"] == cfg.TIMESTAMP:
                cal = QDateTimeEdit()
                cal.setDisplayFormat("yyyy-MM-dd hh:mm:ss.zzz")
                cal.setCalendarPopup(True)
                if len(txt) == len("yyyy-MM-ddThh:mm:ss"):
                    txt += ".000"
                cal.setDateTime(QDateTime.fromString(txt, "yyyy-MM-ddThh:mm:ss.zzz"))

                observationWindow.twIndepVariables.setCellWidget(observationWindow.twIndepVariables.rowCount() - 1, 2, cal)
            else:
                item.setText(txt)
                observationWindow.twIndepVariables.setItem(observationWindow.twIndepVariables.rowCount() - 1, 2, item)

        observationWindow.twIndepVariables.resizeColumnsToContents()

    # adapt time offset for current time format
    if self.timeFormat == cfg.S:
        observationWindow.obs_time_offset.rb_seconds.setChecked(True)
    if self.timeFormat == cfg.HHMMSS:
        # observationWindow.obs_time_offset.set_format_hhmmss()
        observationWindow.obs_time_offset.rb_time.setChecked(True)

    observationWindow.obs_time_offset.set_time(0)

    if mode == cfg.EDIT:
        observationWindow.setWindowTitle(f'Edit observation "{obsId}"')
        """mem_obs_id = obsId"""
        observationWindow.leObservationId.setText(obsId)

        # check date format for old versions of BORIS app
        try:
            time.strptime(self.pj[cfg.OBSERVATIONS][obsId]["date"], "%Y-%m-%d %H:%M")
            self.pj[cfg.OBSERVATIONS][obsId]["date"] = self.pj[cfg.OBSERVATIONS][obsId]["date"].replace(" ", "T") + ":00.000"
            logging.info("Old observation date/time format was converted")
        except ValueError:
            pass

        # print(f"{self.pj[cfg.OBSERVATIONS][obsId]['date']=}")

        # test new date (with msec)
        if len(self.pj[cfg.OBSERVATIONS][obsId]["date"]) == len("yyyy-MM-ddThh:mm:ss.zzz"):
            observationWindow.dteDate.setDateTime(QDateTime.fromString(self.pj[cfg.OBSERVATIONS][obsId]["date"], "yyyy-MM-ddThh:mm:ss.zzz"))
        elif len(self.pj[cfg.OBSERVATIONS][obsId]["date"]) == len("yyyy-MM-ddThh:mm:ss"):
            observationWindow.dteDate.setDateTime(QDateTime.fromString(self.pj[cfg.OBSERVATIONS][obsId]["date"], "yyyy-MM-ddThh:mm:ss"))

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
        if self.pj[cfg.OBSERVATIONS][obsId][cfg.TIME_OFFSET] > cfg.DATE_CUTOFF:
            observationWindow.obs_time_offset.rb_datetime.setChecked(True)

        # time offset
        if self.pj[cfg.OBSERVATIONS][obsId][cfg.TIME_OFFSET]:
            observationWindow.cb_time_offset.setChecked(True)
            observationWindow.obs_time_offset.set_time(self.pj[cfg.OBSERVATIONS][obsId][cfg.TIME_OFFSET])

        if self.pj[cfg.OBSERVATIONS][obsId]["type"] == cfg.MEDIA:
            observationWindow.rb_media_files.setChecked(True)

            observationWindow.twVideo1.setRowCount(0)
            for player in self.pj[cfg.OBSERVATIONS][obsId][cfg.FILE]:
                if player in self.pj[cfg.OBSERVATIONS][obsId][cfg.FILE] and self.pj[cfg.OBSERVATIONS][obsId][cfg.FILE][player]:
                    for mediaFile in self.pj[cfg.OBSERVATIONS][obsId][cfg.FILE][player]:
                        observationWindow.twVideo1.setRowCount(observationWindow.twVideo1.rowCount() + 1)

                        combobox = QComboBox()
                        combobox.addItems(cfg.ALL_PLAYERS)
                        combobox.setCurrentIndex(int(player) - 1)
                        observationWindow.twVideo1.setCellWidget(observationWindow.twVideo1.rowCount() - 1, 0, combobox)

                        # set media file offset
                        try:
                            observationWindow.twVideo1.setItem(
                                observationWindow.twVideo1.rowCount() - 1,
                                1,
                                QTableWidgetItem(str(self.pj[cfg.OBSERVATIONS][obsId][cfg.MEDIA_INFO]["offset"][player])),
                            )
                        except Exception:
                            observationWindow.twVideo1.setItem(observationWindow.twVideo1.rowCount() - 1, 1, QTableWidgetItem("0.0"))

                        item = QTableWidgetItem(mediaFile)
                        item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                        observationWindow.twVideo1.setItem(observationWindow.twVideo1.rowCount() - 1, 2, item)

                        # duration and FPS
                        try:
                            item = QTableWidgetItem(
                                util.seconds2time(self.pj[cfg.OBSERVATIONS][obsId][cfg.MEDIA_INFO][cfg.LENGTH][mediaFile])
                            )
                            item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                            observationWindow.twVideo1.setItem(observationWindow.twVideo1.rowCount() - 1, 3, item)

                            item = QTableWidgetItem(f"{self.pj[cfg.OBSERVATIONS][obsId][cfg.MEDIA_INFO][cfg.FPS][mediaFile]:.2f}")
                            item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                            observationWindow.twVideo1.setItem(observationWindow.twVideo1.rowCount() - 1, 4, item)
                        except Exception:
                            pass

                        # has_video has_audio
                        try:
                            item = QTableWidgetItem(str(self.pj[cfg.OBSERVATIONS][obsId][cfg.MEDIA_INFO][cfg.HAS_VIDEO][mediaFile]))
                            item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                            observationWindow.twVideo1.setItem(observationWindow.twVideo1.rowCount() - 1, 5, item)

                            item = QTableWidgetItem(str(self.pj[cfg.OBSERVATIONS][obsId][cfg.MEDIA_INFO][cfg.HAS_AUDIO][mediaFile]))
                            item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
                            observationWindow.twVideo1.setItem(observationWindow.twVideo1.rowCount() - 1, 6, item)
                        except Exception:
                            pass

            observationWindow.cbCloseCurrentBehaviorsBetweenVideo.setEnabled(observationWindow.twVideo1.rowCount() > 0)
            # spectrogram
            observationWindow.cbVisualizeSpectrogram.setEnabled(True)
            observationWindow.cbVisualizeSpectrogram.setChecked(self.pj[cfg.OBSERVATIONS][obsId].get(cfg.VISUALIZE_SPECTROGRAM, False))
            # waveform
            observationWindow.cb_visualize_waveform.setEnabled(True)
            observationWindow.cb_visualize_waveform.setChecked(self.pj[cfg.OBSERVATIONS][obsId].get(cfg.VISUALIZE_WAVEFORM, False))
            # use Creation date metadata tag as offset
            observationWindow.cb_media_creation_date_as_offset.setEnabled(True)

            # DEVELOPMENT (REMOVE BEFORE RELEASE)
            # observationWindow.cb_media_creation_date_as_offset.setEnabled(False)

            observationWindow.cb_media_creation_date_as_offset.setChecked(
                self.pj[cfg.OBSERVATIONS][obsId].get(cfg.MEDIA_CREATION_DATE_AS_OFFSET, False)
            )

            # scan sampling
            observationWindow.sb_media_scan_sampling.setValue(self.pj[cfg.OBSERVATIONS][obsId].get(cfg.MEDIA_SCAN_SAMPLING_DURATION, 0))
            # image display duration
            observationWindow.sb_image_display_duration.setValue(self.pj[cfg.OBSERVATIONS][obsId].get(cfg.IMAGE_DISPLAY_DURATION, 1))

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
                                        self.pj[cfg.OBSERVATIONS][obsId][cfg.PLOT_DATA][idx2][cfg.DATA_PLOT_FIELDS[idx3]]
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
                                        self.pj[cfg.OBSERVATIONS][obsId][cfg.PLOT_DATA][idx2][cfg.DATA_PLOT_FIELDS[idx3]]
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
                                        str(self.pj[cfg.OBSERVATIONS][obsId][cfg.PLOT_DATA][idx2][cfg.DATA_PLOT_FIELDS[idx3]])
                                    ),
                                )

                            else:
                                observationWindow.tw_data_files.setItem(
                                    observationWindow.tw_data_files.rowCount() - 1,
                                    idx3,
                                    QTableWidgetItem(self.pj[cfg.OBSERVATIONS][obsId][cfg.PLOT_DATA][idx2][cfg.DATA_PLOT_FIELDS[idx3]]),
                                )

        if self.pj[cfg.OBSERVATIONS][obsId]["type"] == cfg.IMAGES:
            observationWindow.rb_images.setChecked(True)
            observationWindow.lw_images_directory.addItems(self.pj[cfg.OBSERVATIONS][obsId].get(cfg.DIRECTORIES_LIST, []))
            observationWindow.rb_use_exif.setChecked(self.pj[cfg.OBSERVATIONS][obsId].get(cfg.USE_EXIF_DATE, False))
            if self.pj[cfg.OBSERVATIONS][obsId].get(cfg.TIME_LAPSE, 0):
                observationWindow.rb_time_lapse.setChecked(True)
                observationWindow.sb_time_lapse.setValue(self.pj[cfg.OBSERVATIONS][obsId].get(cfg.TIME_LAPSE, 0))

        if self.pj[cfg.OBSERVATIONS][obsId]["type"] == cfg.LIVE:
            observationWindow.rb_live.setChecked(True)
            # sampling time
            observationWindow.sbScanSampling.setValue(self.pj[cfg.OBSERVATIONS][obsId].get(cfg.SCAN_SAMPLING_TIME, 0))
            # start from current time
            observationWindow.cb_start_from_current_time.setChecked(
                self.pj[cfg.OBSERVATIONS][obsId].get(cfg.START_FROM_CURRENT_TIME, False)
                or self.pj[cfg.OBSERVATIONS][obsId].get(cfg.START_FROM_CURRENT_EPOCH_TIME, False)
            )
            # day/epoch time
            observationWindow.rb_day_time.setChecked(self.pj[cfg.OBSERVATIONS][obsId].get(cfg.START_FROM_CURRENT_TIME, False))
            observationWindow.rb_epoch_time.setChecked(self.pj[cfg.OBSERVATIONS][obsId].get(cfg.START_FROM_CURRENT_EPOCH_TIME, False))

        # observation time interval
        observationWindow.cb_observation_time_interval.setEnabled(True)
        if self.pj[cfg.OBSERVATIONS][obsId].get(cfg.OBSERVATION_TIME_INTERVAL, [0, 0]) != [0, 0]:
            observationWindow.cb_observation_time_interval.setChecked(True)
            observationWindow.observation_time_interval = self.pj[cfg.OBSERVATIONS][obsId].get(cfg.OBSERVATION_TIME_INTERVAL, [0, 0])
            observationWindow.cb_observation_time_interval.setText(
                (
                    "Limit observation to a time interval: "
                    f"{self.pj[cfg.OBSERVATIONS][obsId].get(cfg.OBSERVATION_TIME_INTERVAL, [0, 0])[0]} - "
                    f"{self.pj[cfg.OBSERVATIONS][obsId].get(cfg.OBSERVATION_TIME_INTERVAL, [0, 0])[1]}"
                )
            )

        if cfg.CLOSE_BEHAVIORS_BETWEEN_VIDEOS in self.pj[cfg.OBSERVATIONS][obsId]:
            observationWindow.cbCloseCurrentBehaviorsBetweenVideo.setChecked(
                self.pj[cfg.OBSERVATIONS][obsId][cfg.CLOSE_BEHAVIORS_BETWEEN_VIDEOS]
            )

    rv = observationWindow.exec()

    # save geometry
    gui_utilities.save_geometry(observationWindow, "new observation")

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
        self.pj[cfg.OBSERVATIONS][new_obs_id]["date"] = observationWindow.dteDate.dateTime().toString("yyyy-MM-ddTHH:mm:ss.zzz")
        # observation description
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
                self.pj[cfg.OBSERVATIONS][new_obs_id][cfg.INDEPENDENT_VARIABLES][observationWindow.twIndepVariables.item(r, 0).text()] = (
                    observationWindow.twIndepVariables.cellWidget(r, 2).currentText()
                )
            elif observationWindow.twIndepVariables.item(r, 1).text() == cfg.TIMESTAMP:
                self.pj[cfg.OBSERVATIONS][new_obs_id][cfg.INDEPENDENT_VARIABLES][observationWindow.twIndepVariables.item(r, 0).text()] = (
                    observationWindow.twIndepVariables.cellWidget(r, 2).dateTime().toString(Qt.ISODate)
                )
            else:
                self.pj[cfg.OBSERVATIONS][new_obs_id][cfg.INDEPENDENT_VARIABLES][observationWindow.twIndepVariables.item(r, 0).text()] = (
                    observationWindow.twIndepVariables.item(r, 2).text()
                )

        # observation time offset
        if observationWindow.cb_time_offset.isChecked():
            self.pj[cfg.OBSERVATIONS][new_obs_id][cfg.TIME_OFFSET] = observationWindow.obs_time_offset.get_time()
        else:
            self.pj[cfg.OBSERVATIONS][new_obs_id][cfg.TIME_OFFSET] = dec("0.0")

        # add date (epoch) if date offset checked
        # if observationWindow.cb_date_offset.isChecked():
        #    print(f"{observationWindow.de_date_offset.date().toString(Qt.ISODate)=}")
        #    date_timestamp = dec(dt.datetime.strptime(observationWindow.de_date_offset.date().toString(Qt.ISODate), "%Y-%m-%d").timestamp())
        #    self.pj[cfg.OBSERVATIONS][new_obs_id][cfg.TIME_OFFSET] += date_timestamp

        if observationWindow.cb_observation_time_interval.isChecked():
            self.pj[cfg.OBSERVATIONS][new_obs_id][cfg.OBSERVATION_TIME_INTERVAL] = observationWindow.observation_time_interval

        self.display_statusbar_info(new_obs_id)

        # visualize spectrogram
        self.pj[cfg.OBSERVATIONS][new_obs_id][cfg.VISUALIZE_SPECTROGRAM] = observationWindow.cbVisualizeSpectrogram.isChecked()
        # visualize waveform
        self.pj[cfg.OBSERVATIONS][new_obs_id][cfg.VISUALIZE_WAVEFORM] = observationWindow.cb_visualize_waveform.isChecked()
        # use Creation date metadata tag as offset
        self.pj[cfg.OBSERVATIONS][new_obs_id][cfg.MEDIA_CREATION_DATE_AS_OFFSET] = (
            observationWindow.cb_media_creation_date_as_offset.isChecked()
        )

        # media scan sampling
        self.pj[cfg.OBSERVATIONS][new_obs_id][cfg.MEDIA_SCAN_SAMPLING_DURATION] = observationWindow.sb_media_scan_sampling.value()
        # image display duration
        self.pj[cfg.OBSERVATIONS][new_obs_id][cfg.IMAGE_DISPLAY_DURATION] = observationWindow.sb_image_display_duration.value()

        # time interval for observation
        self.pj[cfg.OBSERVATIONS][new_obs_id][cfg.OBSERVATION_TIME_INTERVAL] = observationWindow.observation_time_interval

        # plot data
        if observationWindow.tw_data_files.rowCount():
            self.pj[cfg.OBSERVATIONS][new_obs_id][cfg.PLOT_DATA] = {}
            for row in range(observationWindow.tw_data_files.rowCount()):
                self.pj[cfg.OBSERVATIONS][new_obs_id][cfg.PLOT_DATA][str(row)] = {}
                for idx2 in cfg.DATA_PLOT_FIELDS:
                    if idx2 in [cfg.PLOT_DATA_PLOTCOLOR_IDX, cfg.PLOT_DATA_SUBSTRACT1STVALUE_IDX]:
                        self.pj[cfg.OBSERVATIONS][new_obs_id][cfg.PLOT_DATA][str(row)][cfg.DATA_PLOT_FIELDS[idx2]] = (
                            observationWindow.tw_data_files.cellWidget(row, idx2).currentText()
                        )

                    elif idx2 == cfg.PLOT_DATA_CONVERTERS_IDX:
                        if observationWindow.tw_data_files.item(row, idx2).text():
                            self.pj[cfg.OBSERVATIONS][new_obs_id][cfg.PLOT_DATA][str(row)][cfg.DATA_PLOT_FIELDS[idx2]] = eval(
                                observationWindow.tw_data_files.item(row, idx2).text()
                            )
                        else:
                            self.pj[cfg.OBSERVATIONS][new_obs_id][cfg.PLOT_DATA][str(row)][cfg.DATA_PLOT_FIELDS[idx2]] = {}

                    else:
                        self.pj[cfg.OBSERVATIONS][new_obs_id][cfg.PLOT_DATA][str(row)][cfg.DATA_PLOT_FIELDS[idx2]] = (
                            observationWindow.tw_data_files.item(row, idx2).text()
                        )

        # Close current behaviors between video
        self.pj[cfg.OBSERVATIONS][new_obs_id][cfg.CLOSE_BEHAVIORS_BETWEEN_VIDEOS] = (
            observationWindow.cbCloseCurrentBehaviorsBetweenVideo.isChecked()
        )

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
                observationWindow.lw_images_directory.item(i).text() for i in range(observationWindow.lw_images_directory.count())
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

            if self.pj[cfg.OBSERVATIONS][new_obs_id][cfg.MEDIA_CREATION_DATE_AS_OFFSET]:
                self.pj[cfg.OBSERVATIONS][new_obs_id][cfg.MEDIA_INFO][cfg.MEDIA_CREATION_TIME] = observationWindow.media_creation_time

            try:
                self.pj[cfg.OBSERVATIONS][new_obs_id][cfg.MEDIA_INFO][cfg.HAS_VIDEO] = observationWindow.mediaHasVideo
                self.pj[cfg.OBSERVATIONS][new_obs_id][cfg.MEDIA_INFO][cfg.HAS_AUDIO] = observationWindow.mediaHasAudio
            except Exception:
                logging.warning("error with media_info information")

            self.pj[cfg.OBSERVATIONS][new_obs_id][cfg.MEDIA_INFO]["offset"] = {}

            logging.debug(f"media_info: {self.pj[cfg.OBSERVATIONS][new_obs_id][cfg.MEDIA_INFO]}")

            for i in range(cfg.N_PLAYER):
                self.pj[cfg.OBSERVATIONS][new_obs_id][cfg.FILE][str(i + 1)] = []

            for row in range(observationWindow.twVideo1.rowCount()):
                self.pj[cfg.OBSERVATIONS][new_obs_id][cfg.FILE][observationWindow.twVideo1.cellWidget(row, 0).currentText()].append(
                    observationWindow.twVideo1.item(row, 2).text()
                )
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
                if not initialize_new_media_observation(self):
                    close_observation(self)
                    return "Observation not launched"

            if self.pj[cfg.OBSERVATIONS][self.observationId][cfg.TYPE] == cfg.IMAGES:
                # QMessageBox.critical(self, cfg.programName, "Observation from images directory is not yet implemented")
                initialize_new_images_observation(self)

            self.load_tw_events(self.observationId)
            menu_options.update_menu(self)


def close_observation(self):
    """
    close current observation
    """

    logging.info(f"Close observation (player type: {self.playerType})")

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
            state_events.fix_unpaired_events(self, silent_mode=True)

    self.saved_state = self.saveState()

    if self.playerType == cfg.MEDIA:
        self.media_scan_sampling_mem = []
        logging.info("Stop plot timer")
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
        self.pb_live_obs.setEnabled(False)
        self.w_live.setVisible(False)
        self.liveObservationStarted = False
        self.liveStartTime = None

    if cfg.PLOT_DATA in self.pj[cfg.OBSERVATIONS][self.observationId] and self.pj[cfg.OBSERVATIONS][self.observationId][cfg.PLOT_DATA]:
        for x in self.ext_data_timer_list:
            x.stop()
        for pd in self.plot_data:
            self.plot_data[pd].close_plot()

    logging.info("close tool window")

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
            logging.info("remove dock widget")
            dw.player.log_handler = None
            self.removeDockWidget(dw)

            del dw
            # sip.delete(dw)
            # dw = None

    # self.dw_player = []

    self.statusbar.showMessage("", 0)

    self.dwEvents.setVisible(False)

    self.w_obs_info.setVisible(False)

    # self.twEvents.setRowCount(0)

    self.lb_current_media_time.clear()
    self.lb_player_status.clear()
    self.lb_video_info.clear()
    self.lb_zoom_level.clear()

    self.currentSubject = ""
    self.lbFocalSubject.setText(cfg.NO_FOCAL_SUBJECT)

    # clear current state(s) column in subjects table
    for i in range(self.twSubjects.rowCount()):
        self.twSubjects.item(i, len(cfg.subjectsFields)).setText("")

    for w in (self.lbTimeOffset, self.lb_obs_time_interval):
        w.clear()
    self.play_rate, self.playerType = 1, ""

    menu_options.update_menu(self)

    logging.info(f"Observation {self.playerType} closed")


def check_creation_date(self) -> Tuple[int, dict]:
    """
    check if media file exists
    check if Creation Date tag is present in metadata of media file

    Returns:
        int: 0 if OK else error code: 1 -> media file date not used, 2 -> media file not found

    """

    not_tagged_media_list: list = []
    media_creation_time: dict = {}

    for nplayer in cfg.ALL_PLAYERS:
        if nplayer in self.pj[cfg.OBSERVATIONS][self.observationId].get(cfg.FILE, {}):
            for media_file in self.pj[cfg.OBSERVATIONS][self.observationId][cfg.FILE][nplayer]:
                media_path = project_functions.full_path(media_file, self.projectFileName)
                media_info = util.accurate_media_analysis(self.ffmpeg_bin, media_path)

                if cfg.MEDIA_CREATION_TIME not in media_info or media_info[cfg.MEDIA_CREATION_TIME] == cfg.NA:
                    not_tagged_media_list.append(media_path)
                else:
                    creation_time_epoch = int(dt.datetime.strptime(media_info[cfg.MEDIA_CREATION_TIME], "%Y-%m-%d %H:%M:%S").timestamp())
                    media_creation_time[media_path] = creation_time_epoch

    """
    for row in range(self.twVideo1.rowCount()):
        if self.twVideo1.item(row, 2).text() not in media_not_found_list:
            media_info = util.accurate_media_analysis(self.ffmpeg_bin, self.twVideo1.item(row, 2).text())
            if cfg.MEDIA_CREATION_TIME not in media_info or media_info[cfg.MEDIA_CREATION_TIME] == cfg.NA:
                not_tagged_media_list.append(self.twVideo1.item(row, 2).text())
            else:
                creation_time_epoch = int(dt.datetime.strptime(media_info[cfg.MEDIA_CREATION_TIME], "%Y-%m-%d %H:%M:%S").timestamp())
                self.media_creation_time[self.twVideo1.item(row, 2).text()] = creation_time_epoch
    """

    if not_tagged_media_list:
        dlg = dialog.Results_dialog()
        dlg.setWindowTitle("BORIS")
        dlg.pbOK.setText("Yes")
        dlg.pbCancel.setVisible(True)
        dlg.pbCancel.setText("No")

        dlg.ptText.clear()
        dlg.ptText.appendHtml(
            (
                "Some media file does not contain the <b>Creation date/time</b> metadata tag:<br>"
                f"{'<br>'.join(not_tagged_media_list)}<br><br>"
                "Use the media file date/time instead?"
            )
        )
        dlg.ptText.moveCursor(QTextCursor.Start)
        ret = dlg.exec_()

        if ret == 1:  #  use file creation time
            for media in not_tagged_media_list:
                media_creation_time[media] = pl.Path(media).stat().st_ctime
            return (0, media_creation_time)  # OK use media file creation date/time
        else:
            return (1, {})
    else:
        return (0, media_creation_time)  # OK all media have a 'creation time' tag


def init_mpv(self):
    """Start mpv process and embed it in the PySide6 application."""

    print("start MPV process")

    """
    print(f"{self.winId()=}")
    print(f"{str(int(self.winId()))=}")
    """

    subprocess.Popen(
        [
            "mpv",
            "--no-border",
            "--ontop",  # mpv window on top
            "--osc=no",  # no on screen commands
            "--input-ipc-server=" + cfg.MPV_SOCKET,
            # "--wid=" + str(int(self.winId())),  # Embed in the widget
            "--idle",  # Keeps mpv running with no video
        ],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )

    # print(f"init mpv:  {self.mpv_process=}")


def send_command(command):
    """Send a JSON command to the mpv IPC server."""

    print(f"send commnand {command}")
    # print(f"{self.mpv_process=}")

    try:
        # Create a Unix socket
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
            # Connect to the MPV IPC server
            from pathlib import Path

            print(f"{Path(cfg.MPV_SOCKET).is_socket()=}")

            client.connect(cfg.MPV_SOCKET)
            # Send the JSON command
            client.sendall(json.dumps(command).encode("utf-8") + b"\n")
            # Receive the response
            response = client.recv(2000)

            print()
            print(f"{response=}")

            # Parse the response as JSON
            response_splitted = response.split(b"\n")
            print(f"{response_splitted=}")
            data = None
            for r in response_splitted:
                print(f"{r=}")
                if not r:
                    continue
                response_data = json.loads(r.decode("utf-8"))
                if "data" in response_data:
                    data = response_data.get("data")
            # response_data = json.loads(response.decode("utf-8"))
            # print(f"{response_data=}")
            # return response_data.get("data")

            return data

    except FileNotFoundError:
        raise
        print("Error: Socket file not found.")
    except Exception as e:
        raise
        print(f"An error occurred: {e}")
    return None


def initialize_new_media_observation(self) -> bool:
    """
    initialize new observation from media file(s)
    """

    logging.debug("function: initialize new observation for media file(s)")

    for dw in (self.dwEthogram, self.dwSubjects, self.dwEvents):
        dw.setVisible(True)

    ok, msg = project_functions.check_if_media_available(self.pj[cfg.OBSERVATIONS][self.observationId], self.projectFileName)

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

    if sys.platform.startswith(cfg.MACOS_CODE):
        pass
        init_mpv(self)

        # print(f"{self.process=}")

    self.playerType = cfg.MEDIA
    self.fps = 0

    self.pb_live_obs.setEnabled(False)
    self.w_live.setVisible(False)
    self.w_obs_info.setVisible(True)

    font = QFont()
    font.setPointSize(15)
    self.lb_current_media_time.setFont(font)
    self.lb_video_info.setFont(font)
    self.lb_zoom_level.setFont(font)

    # initialize video slider
    self.video_slider = QSlider(Qt.Horizontal, self)
    self.video_slider.setFocusPolicy(Qt.NoFocus)
    self.video_slider.setMaximum(cfg.SLIDER_MAXIMUM)
    self.video_slider.sliderMoved.connect(self.video_slider_sliderMoved)
    self.video_slider.sliderReleased.connect(self.video_slider_sliderReleased)
    self.verticalLayout_3.addWidget(self.video_slider)

    # add all media files to media lists
    self.setDockOptions(QMainWindow.AnimatedDocks | QMainWindow.AllowNestedDocks)
    self.dw_player: list = []

    # check if media creation time used as offset
    # TODO check if cfg.MEDIA_CREATION_TIME dict is present
    """
    if self.pj[cfg.OBSERVATIONS][self.observationId].get(cfg.MEDIA_CREATION_DATE_AS_OFFSET, False):
        r, media_creation_time = check_creation_date(self)

        if r:
            return False
        self.pj[cfg.OBSERVATIONS][self.observationId][cfg.MEDIA_INFO][cfg.MEDIA_CREATION_TIME] = dict(media_creation_time)
    """

    # create dock widgets for players

    if not sys.platform.startswith(cfg.MACOS_CODE):
        for i in range(cfg.N_PLAYER):
            n_player = str(i + 1)
            if (
                n_player not in self.pj[cfg.OBSERVATIONS][self.observationId][cfg.FILE]
                or not self.pj[cfg.OBSERVATIONS][self.observationId][cfg.FILE][n_player]
            ):
                continue

            # Not pretty but the unique solution I have found to capture the click signal for each player

            if i == 0:  # first player
                p0 = player_dock_widget.DW_player(0, self)

                @p0.player.property_observer("time-pos")
                def time_observer(_name, value):
                    if value is not None:
                        self.time_observer_signal.emit(value)

                @p0.player.property_observer("eof-reached")
                def eof_reached(_name, value):
                    if value is not None:
                        self.mpv_eof_reached_signal.emit(value)

                @p0.player.on_key_press("MBTN_LEFT")
                def mbtn_left0():
                    self.video_click_signal.emit(0, "MBTN_LEFT")

                @p0.player.on_key_press("MBTN_RIGHT")
                def mbtn_right0():
                    self.video_click_signal.emit(0, "MBTN_RIGHT")

                @p0.player.on_key_press("MBTN_LEFT_DBL")
                def mbtn_left_dbl0():
                    self.video_click_signal.emit(0, "MBTN_LEFT_DBL")

                @p0.player.on_key_press("MBTN_RIGHT_DBL")
                def mbtn_right_dbl0():
                    self.video_click_signal.emit(0, "MBTN_RIGHT_DBL")

                @p0.player.on_key_press("Ctrl+WHEEL_UP")
                def ctrl_wheel_up0():
                    self.video_click_signal.emit(0, "Ctrl+WHEEL_UP")

                @p0.player.on_key_press("Ctrl+WHEEL_DOWN")
                def ctrl_wheel_down0():
                    self.video_click_signal.emit(0, "Ctrl+WHEEL_DOWN")

                @p0.player.on_key_press("WHEEL_UP")
                def wheel_up0():
                    self.video_click_signal.emit(0, "WHEEL_UP")

                @p0.player.on_key_press("WHEEL_DOWN")
                def wheel_down0():
                    self.video_click_signal.emit(0, "WHEEL_DOWN")

                @p0.player.on_key_press("Shift+WHEEL_UP")
                def shift_wheel_up0():
                    self.video_click_signal.emit(0, "Shift+WHEEL_UP")

                @p0.player.on_key_press("Shift+WHEEL_DOWN")
                def shift_wheel_down0():
                    self.video_click_signal.emit(0, "Shift+WHEEL_DOWN")

                @p0.player.on_key_press("Shift+MBTN_LEFT")
                def shift_mbtn_left0():
                    self.video_click_signal.emit(0, "Shift+MBTN_LEFT")

                self.dw_player.append(p0)

            if i == 1:  # second player
                p1 = player_dock_widget.DW_player(1, self)

                @p1.player.on_key_press("MBTN_LEFT")
                def mbtn_left1():
                    self.video_click_signal.emit(1, "MBTN_LEFT")

                @p1.player.on_key_press("MBTN_RIGHT")
                def mbtn_right1():
                    self.video_click_signal.emit(1, "MBTN_RIGHT")

                @p1.player.on_key_press("MBTN_LEFT_DBL")
                def mbtn_left_dbl1():
                    self.video_click_signal.emit(1, "MBTN_LEFT_DBL")

                @p1.player.on_key_press("MBTN_RIGHT_DBL")
                def mbtn_right_dbl1():
                    self.video_click_signal.emit(1, "MBTN_RIGHT_DBL")

                @p1.player.on_key_press("Ctrl+WHEEL_UP")
                def ctrl_wheel_up1():
                    self.video_click_signal.emit(1, "Ctrl+WHEEL_UP")

                @p1.player.on_key_press("Ctrl+WHEEL_DOWN")
                def ctrl_wheel_down1():
                    self.video_click_signal.emit(1, "Ctrl+WHEEL_DOWN")

                @p1.player.on_key_press("WHEEL_UP")
                def wheel_up1():
                    self.video_click_signal.emit(1, "WHEEL_UP")

                @p1.player.on_key_press("WHEEL_DOWN")
                def wheel_down1():
                    self.video_click_signal.emit(1, "WHEEL_DOWN")

                @p1.player.on_key_press("Shift+WHEEL_UP")
                def shift_wheel_up1():
                    self.video_click_signal.emit(1, "Shift+WHEEL_UP")

                @p1.player.on_key_press("Shift+WHEEL_DOWN")
                def shift_wheel_down1():
                    self.video_click_signal.emit(1, "Shift+WHEEL_DOWN")

                @p1.player.on_key_press("Shift+MBTN_LEFT")
                def shift_mbtn_left1():
                    self.video_click_signal.emit(1, "Shift+MBTN_LEFT")

                self.dw_player.append(p1)

            if i == 2:
                p2 = player_dock_widget.DW_player(2, self)

                @p2.player.on_key_press("MBTN_LEFT")
                def mbtn_left2():
                    self.video_click_signal.emit(2, "MBTN_LEFT")

                @p2.player.on_key_press("MBTN_RIGHT")
                def mbtn_right2():
                    self.video_click_signal.emit(2, "MBTN_RIGHT")

                @p2.player.on_key_press("MBTN_LEFT_DBL")
                def mbtn_left_dbl2():
                    self.video_click_signal.emit(2, "MBTN_LEFT_DBL")

                @p2.player.on_key_press("MBTN_RIGHT_DBL")
                def mbtn_right_dbl2():
                    self.video_click_signal.emit(2, "MBTN_RIGHT_DBL")

                @p2.player.on_key_press("Ctrl+WHEEL_UP")
                def ctrl_wheel_up2():
                    self.video_click_signal.emit(2, "Ctrl+WHEEL_UP")

                @p2.player.on_key_press("Ctrl+WHEEL_DOWN")
                def ctrl_wheel_down2():
                    self.video_click_signal.emit(2, "Ctrl+WHEEL_DOWN")

                @p2.player.on_key_press("WHEEL_UP")
                def wheel_up2():
                    self.video_click_signal.emit(2, "WHEEL_UP")

                @p2.player.on_key_press("WHEEL_DOWN")
                def wheel_down2():
                    self.video_click_signal.emit(2, "WHEEL_DOWN")

                @p2.player.on_key_press("Shift+WHEEL_UP")
                def shift_wheel_up2():
                    self.video_click_signal.emit(2, "Shift+WHEEL_UP")

                @p2.player.on_key_press("Shift+WHEEL_DOWN")
                def shift_wheel_down2():
                    self.video_click_signal.emit(2, "Shift+WHEEL_DOWN")

                @p2.player.on_key_press("Shift+MBTN_LEFT")
                def shift_mbtn_left2():
                    self.video_click_signal.emit(2, "Shift+MBTN_LEFT")

                self.dw_player.append(p2)

            if i == 3:
                p3 = player_dock_widget.DW_player(3, self)

                @p3.player.on_key_press("MBTN_LEFT")
                def mbtn_left3():
                    self.video_click_signal.emit(3, "MBTN_LEFT")

                @p3.player.on_key_press("MBTN_RIGHT")
                def mbtn_right3():
                    self.video_click_signal.emit(3, "MBTN_RIGHT")

                @p3.player.on_key_press("MBTN_LEFT_DBL")
                def mbtn_left_dbl3():
                    self.video_click_signal.emit(3, "MBTN_LEFT_DBL")

                @p3.player.on_key_press("MBTN_RIGHT_DBL")
                def mbtn_right_dbl3():
                    self.video_click_signal.emit(3, "MBTN_RIGHT_DBL")

                @p3.player.on_key_press("Ctrl+WHEEL_UP")
                def ctrl_wheel_up3():
                    self.video_click_signal.emit(3, "Ctrl+WHEEL_UP")

                @p3.player.on_key_press("Ctrl+WHEEL_DOWN")
                def ctrl_wheel_down3():
                    self.video_click_signal.emit(3, "Ctrl+WHEEL_DOWN")

                @p3.player.on_key_press("WHEEL_UP")
                def wheel_up3():
                    self.video_click_signal.emit(3, "WHEEL_UP")

                @p3.player.on_key_press("WHEEL_DOWN")
                def wheel_down3():
                    self.video_click_signal.emit(3, "WHEEL_DOWN")

                @p3.player.on_key_press("Shift+WHEEL_UP")
                def shift_wheel_up3():
                    self.video_click_signal.emit(3, "Shift+WHEEL_UP")

                @p3.player.on_key_press("Shift+WHEEL_DOWN")
                def shift_wheel_down3():
                    self.video_click_signal.emit(3, "Shift+WHEEL_DOWN")

                @p3.player.on_key_press("Shift+MBTN_LEFT")
                def shift_mbtn_left3():
                    self.video_click_signal.emit(3, "Shift+MBTN_LEFT")

                self.dw_player.append(p3)

            if i == 4:
                p4 = player_dock_widget.DW_player(4, self)

                @p4.player.on_key_press("MBTN_LEFT")
                def mbtn_left4():
                    self.video_click_signal.emit(4, "MBTN_LEFT")

                @p4.player.on_key_press("MBTN_RIGHT")
                def mbtn_right4():
                    self.video_click_signal.emit(4, "MBTN_RIGHT")

                @p4.player.on_key_press("MBTN_LEFT_DBL")
                def mbtn_left_dbl4():
                    self.video_click_signal.emit(4, "MBTN_LEFT_DBL")

                @p4.player.on_key_press("MBTN_RIGHT_DBL")
                def mbtn_right_dbl4():
                    self.video_click_signal.emit(4, "MBTN_RIGHT_DBL")

                @p4.player.on_key_press("Ctrl+WHEEL_UP")
                def ctrl_wheel_up4():
                    self.video_click_signal.emit(4, "Ctrl+WHEEL_UP")

                @p4.player.on_key_press("Ctrl+WHEEL_DOWN")
                def ctrl_wheel_down4():
                    self.video_click_signal.emit(4, "Ctrl+WHEEL_DOWN")

                @p4.player.on_key_press("WHEEL_UP")
                def wheel_up4():
                    self.video_click_signal.emit(4, "WHEEL_UP")

                @p4.player.on_key_press("WHEEL_DOWN")
                def wheel_down4():
                    self.video_click_signal.emit(4, "WHEEL_DOWN")

                @p4.player.on_key_press("Shift+WHEEL_UP")
                def shift_wheel_up4():
                    self.video_click_signal.emit(4, "Shift+WHEEL_UP")

                @p4.player.on_key_press("Shift+WHEEL_DOWN")
                def shift_wheel_down4():
                    self.video_click_signal.emit(4, "Shift+WHEEL_DOWN")

                @p4.player.on_key_press("Shift+MBTN_LEFT")
                def shift_mbtn_left4():
                    self.video_click_signal.emit(4, "Shift+MBTN_LEFT")

                self.dw_player.append(p4)

            if i == 5:
                p5 = player_dock_widget.DW_player(5, self)

                @p5.player.on_key_press("MBTN_LEFT")
                def mbtn_left5():
                    self.video_click_signal.emit(5, "MBTN_LEFT")

                @p5.player.on_key_press("MBTN_RIGHT")
                def mbtn_right5():
                    self.video_click_signal.emit(5, "MBTN_RIGHT")

                @p5.player.on_key_press("MBTN_LEFT_DBL")
                def mbtn_left_dbl5():
                    self.video_click_signal.emit(5, "MBTN_LEFT_DBL")

                @p5.player.on_key_press("MBTN_RIGHT_DBL")
                def mbtn_right_dbl5():
                    self.video_click_signal.emit(5, "MBTN_RIGHT_DBL")

                @p5.player.on_key_press("Ctrl+WHEEL_UP")
                def ctrl_wheel_up5():
                    self.video_click_signal.emit(5, "Ctrl+WHEEL_UP")

                @p5.player.on_key_press("Ctrl+WHEEL_DOWN")
                def ctrl_wheel_down5():
                    self.video_click_signal.emit(5, "Ctrl+WHEEL_DOWN")

                @p5.player.on_key_press("WHEEL_UP")
                def wheel_up5():
                    self.video_click_signal.emit(5, "WHEEL_UP")

                @p5.player.on_key_press("WHEEL_DOWN")
                def wheel_down5():
                    self.video_click_signal.emit(5, "WHEEL_DOWN")

                @p5.player.on_key_press("Shift+WHEEL_UP")
                def shift_wheel_up5():
                    self.video_click_signal.emit(5, "Shift+WHEEL_UP")

                @p5.player.on_key_press("Shift+WHEEL_DOWN")
                def shift_wheel_down5():
                    self.video_click_signal.emit(5, "Shift+WHEEL_DOWN")

                @p5.player.on_key_press("Shift+MBTN_LEFT")
                def shift_mbtn_left5():
                    self.video_click_signal.emit(5, "Shift+MBTN_LEFT")

                self.dw_player.append(p5)

            if i == 6:
                p6 = player_dock_widget.DW_player(6, self)

                @p6.player.on_key_press("MBTN_LEFT")
                def mbtn_left6():
                    self.video_click_signal.emit(6, "MBTN_LEFT")

                @p6.player.on_key_press("MBTN_RIGHT")
                def mbtn_right6():
                    self.video_click_signal.emit(6, "MBTN_RIGHT")

                @p6.player.on_key_press("MBTN_LEFT_DBL")
                def mbtn_left_dbl6():
                    self.video_click_signal.emit(6, "MBTN_LEFT_DBL")

                @p6.player.on_key_press("MBTN_RIGHT_DBL")
                def mbtn_right_dbl6():
                    self.video_click_signal.emit(6, "MBTN_RIGHT_DBL")

                @p6.player.on_key_press("Ctrl+WHEEL_UP")
                def ctrl_wheel_up6():
                    self.video_click_signal.emit(6, "Ctrl+WHEEL_UP")

                @p6.player.on_key_press("Ctrl+WHEEL_DOWN")
                def ctrl_wheel_down6():
                    self.video_click_signal.emit(6, "Ctrl+WHEEL_DOWN")

                @p6.player.on_key_press("WHEEL_UP")
                def wheel_up6():
                    self.video_click_signal.emit(6, "WHEEL_UP")

                @p6.player.on_key_press("WHEEL_DOWN")
                def wheel_down6():
                    self.video_click_signal.emit(6, "WHEEL_DOWN")

                @p6.player.on_key_press("Shift+WHEEL_UP")
                def shift_wheel_up6():
                    self.video_click_signal.emit(6, "Shift+WHEEL_UP")

                @p6.player.on_key_press("Shift+WHEEL_DOWN")
                def shift_wheel_down6():
                    self.video_click_signal.emit(6, "Shift+WHEEL_DOWN")

                @p6.player.on_key_press("Shift+MBTN_LEFT")
                def shift_mbtn_left6():
                    self.video_click_signal.emit(6, "Shift+MBTN_LEFT")

                self.dw_player.append(p6)

            if i == 7:
                p7 = player_dock_widget.DW_player(7, self)

                @p7.player.on_key_press("MBTN_LEFT")
                def mbtn_left7():
                    self.video_click_signal.emit(7, "MBTN_LEFT")

                @p7.player.on_key_press("MBTN_RIGHT")
                def mbtn_right7():
                    self.video_click_signal.emit(7, "MBTN_RIGHT")

                @p7.player.on_key_press("MBTN_LEFT_DBL")
                def mbtn_left_dbl7():
                    self.video_click_signal.emit(7, "MBTN_LEFT_DBL")

                @p7.player.on_key_press("MBTN_RIGHT_DBL")
                def mbtn_right_dbl7():
                    self.video_click_signal.emit(7, "MBTN_RIGHT_DBL")

                @p7.player.on_key_press("Ctrl+WHEEL_UP")
                def ctrl_wheel_up7():
                    self.video_click_signal.emit(7, "Ctrl+WHEEL_UP")

                @p7.player.on_key_press("Ctrl+WHEEL_DOWN")
                def ctrl_wheel_down7():
                    self.video_click_signal.emit(7, "Ctrl+WHEEL_DOWN")

                @p7.player.on_key_press("WHEEL_UP")
                def wheel_up7():
                    self.video_click_signal.emit(7, "WHEEL_UP")

                @p7.player.on_key_press("WHEEL_DOWN")
                def wheel_down7():
                    self.video_click_signal.emit(7, "WHEEL_DOWN")

                @p7.player.on_key_press("Shift+WHEEL_UP")
                def shift_wheel_up7():
                    self.video_click_signal.emit(7, "Shift+WHEEL_UP")

                @p7.player.on_key_press("Shift+WHEEL_DOWN")
                def shift_wheel_down7():
                    self.video_click_signal.emit(7, "Shift+WHEEL_DOWN")

                @p7.player.on_key_press("Shift+MBTN_LEFT")
                def shift_mbtn_left7():
                    self.video_click_signal.emit(7, "Shift+MBTN_LEFT")

                self.dw_player.append(p7)

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

            # for receiving event from mute toolbutton
            self.dw_player[i].mute_action_triggered_signal.connect(self.set_mute)

            # for receiving resize event from dock widget
            self.dw_player[i].resize_signal.connect(self.resize_dw)

            # add durations list
            self.dw_player[i].media_durations: list = []
            self.dw_player[i].cumul_media_durations: List[int] = [0]  # [idx for idx,x in enumerate(l) if l[idx-1]<pos<=x]

            # add fps list
            self.dw_player[i].fps = {}

            for mediaFile in self.pj[cfg.OBSERVATIONS][self.observationId][cfg.FILE][n_player]:
                logging.debug(f"media file: {mediaFile}")

                media_full_path = project_functions.full_path(mediaFile, self.projectFileName)

                logging.debug(f"media_full_path: {media_full_path}")

                # media duration
                try:
                    mediaLength = self.pj[cfg.OBSERVATIONS][self.observationId][cfg.MEDIA_INFO][cfg.LENGTH][mediaFile] * 1000
                    mediaFPS = self.pj[cfg.OBSERVATIONS][self.observationId][cfg.MEDIA_INFO][cfg.FPS][mediaFile]
                except Exception:
                    logging.debug("media_info key not found in project")

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
                        self.pj[cfg.OBSERVATIONS][self.observationId][cfg.MEDIA_INFO][cfg.FPS][mediaFile] = r[cfg.FPS]

                        mediaLength = r["duration"] * 1000
                        mediaFPS = r[cfg.FPS]

                        self.project_changed()

                self.dw_player[i].media_durations.append(int(mediaLength))
                self.dw_player[i].cumul_media_durations.append(self.dw_player[i].cumul_media_durations[-1] + int(mediaLength))

                self.dw_player[i].fps[mediaFile] = mediaFPS

                # add media file to playlist
                self.dw_player[i].player.playlist_append(media_full_path)

                # add media file name to player window title
                self.dw_player[i].setWindowTitle(f"Player #{i + 1} ({pl.Path(media_full_path).name})")

            # media duration cumuled in seconds
            self.dw_player[i].cumul_media_durations_sec = [round(dec(x / 1000), 3) for x in self.dw_player[i].cumul_media_durations]

            # check if BORIS is running on a Windows VM with the 'WMIC COMPUTERSYSTEM GET SERIALNUMBER' command
            # because "auto" or "auto-safe" crash in Windows VM
            # see https://superuser.com/questions/1128339/how-can-i-detect-if-im-within-a-vm-or-not

            flag_vm = False
            if sys.platform.startswith("win"):
                p = subprocess.Popen(
                    ["WMIC", "BIOS", "GET", "SERIALNUMBER"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    shell=True,
                )
                out, _ = p.communicate()
                flag_vm = b"SerialNumber  \r\r\n0 " in out
                logging.debug(f"Running on Windows VM: {flag_vm}")

            if not flag_vm:
                self.dw_player[i].player.hwdec = self.config_param.get(cfg.MPV_HWDEC, cfg.MPV_HWDEC_DEFAULT_VALUE)
            else:
                self.dw_player[i].player.hwdec = cfg.MPV_HWDEC_NO

            logging.debug(f"Player hwdec of player #{i} set to: {self.dw_player[i].player.hwdec}")
            self.config_param[cfg.MPV_HWDEC] = self.dw_player[i].player.hwdec

            self.dw_player[i].player.playlist_pos = 0
            self.dw_player[i].player.wait_until_playing()
            self.dw_player[i].player.pause = True
            time.sleep(0.2)
            # self.dw_player[i].player.wait_until_paused()
            self.dw_player[i].player.seek(0, "absolute")
            # do not close when playing finished
            self.dw_player[i].player.keep_open = True
            self.dw_player[i].player.keep_open_pause = False

            self.dw_player[i].player.image_display_duration = self.pj[cfg.OBSERVATIONS][self.observationId].get(
                cfg.IMAGE_DISPLAY_DURATION, 1
            )

            # position media
            self.seek_mediaplayer(
                int(self.pj[cfg.OBSERVATIONS][self.observationId].get(cfg.OBSERVATION_TIME_INTERVAL, [0, 0])[0]), player=i
            )

            # restore video zoom level
            if cfg.ZOOM_LEVEL in self.pj[cfg.OBSERVATIONS][self.observationId][cfg.MEDIA_INFO]:
                self.dw_player[i].player.video_zoom = log2(
                    self.pj[cfg.OBSERVATIONS][self.observationId][cfg.MEDIA_INFO][cfg.ZOOM_LEVEL].get(n_player, 0)
                )

            # restore video pan
            if cfg.PAN_X in self.pj[cfg.OBSERVATIONS][self.observationId][cfg.MEDIA_INFO]:
                self.dw_player[i].player.video_pan_x = self.pj[cfg.OBSERVATIONS][self.observationId][cfg.MEDIA_INFO][cfg.PAN_X].get(
                    n_player, 0
                )
            if cfg.PAN_Y in self.pj[cfg.OBSERVATIONS][self.observationId][cfg.MEDIA_INFO]:
                self.dw_player[i].player.video_pan_y = self.pj[cfg.OBSERVATIONS][self.observationId][cfg.MEDIA_INFO][cfg.PAN_Y].get(
                    n_player, 0
                )

            # restore rotation angle
            if cfg.ROTATION_ANGLE in self.pj[cfg.OBSERVATIONS][self.observationId][cfg.MEDIA_INFO]:
                self.dw_player[i].player.video_rotate = self.pj[cfg.OBSERVATIONS][self.observationId][cfg.MEDIA_INFO][
                    cfg.ROTATION_ANGLE
                ].get(n_player, 0)

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

    else:  # macos
        print(self.pj[cfg.OBSERVATIONS][self.observationId][cfg.FILE])

        for mediaFile in self.pj[cfg.OBSERVATIONS][self.observationId][cfg.FILE]["1"]:
            logging.debug(f"media file: {mediaFile}")

            media_full_path = project_functions.full_path(mediaFile, self.projectFileName)
            send_command({"command": ["loadfile", media_full_path]})
            # pause
            send_command({"command": ["set_property", "pause", True]})
            send_command({"command": ["set_property", "time-pos", 0]})

    menu_options.update_menu(self)

    self.time_observer_signal.connect(self.mpv_timer_out)
    self.mpv_eof_reached_signal.connect(self.mpv_eof_reached)
    self.video_click_signal.connect(self.player_clicked)

    self.actionPlay.setIcon(QIcon(f":/play_{gui_utilities.theme_mode()}"))

    self.display_statusbar_info(self.observationId)

    self.currentSubject = ""
    # store state behaviors for subject current state
    self.state_behaviors_codes = tuple(util.state_behavior_codes(self.pj[cfg.ETHOGRAM]))

    video_operations.display_play_rate(self)
    video_operations.display_zoom_level(self)

    # spectrogram
    if (
        cfg.VISUALIZE_SPECTROGRAM in self.pj[cfg.OBSERVATIONS][self.observationId]
        and self.pj[cfg.OBSERVATIONS][self.observationId][cfg.VISUALIZE_SPECTROGRAM]
    ):
        tmp_dir = self.ffmpeg_cache_dir if self.ffmpeg_cache_dir and os.path.isdir(self.ffmpeg_cache_dir) else tempfile.gettempdir()

        wav_file_path = (
            pl.Path(tmp_dir) / pl.Path(self.dw_player[0].player.playlist[self.dw_player[0].player.playlist_pos]["filename"] + ".wav").name
        )

        if not wav_file_path.is_file():
            self.generate_wav_file_from_media()

        self.show_plot_widget("spectrogram", warning=False)

    # waveform
    if (
        cfg.VISUALIZE_WAVEFORM in self.pj[cfg.OBSERVATIONS][self.observationId]
        and self.pj[cfg.OBSERVATIONS][self.observationId][cfg.VISUALIZE_WAVEFORM]
    ):
        tmp_dir = self.ffmpeg_cache_dir if self.ffmpeg_cache_dir and os.path.isdir(self.ffmpeg_cache_dir) else tempfile.gettempdir()

        wav_file_path = (
            pl.Path(tmp_dir) / pl.Path(self.dw_player[0].player.playlist[self.dw_player[0].player.playlist_pos]["filename"] + ".wav").name
        )

        if not wav_file_path.is_file():
            self.generate_wav_file_from_media()

        self.show_plot_widget("waveform", warning=False)

    # external data plot
    if cfg.PLOT_DATA in self.pj[cfg.OBSERVATIONS][self.observationId] and self.pj[cfg.OBSERVATIONS][self.observationId][cfg.PLOT_DATA]:
        self.plot_data = {}
        self.ext_data_timer_list = []
        count = 0
        for idx in self.pj[cfg.OBSERVATIONS][self.observationId][cfg.PLOT_DATA]:
            if count == 0:
                data_ok: bool = True
                data_file_path = project_functions.full_path(
                    self.pj[cfg.OBSERVATIONS][self.observationId][cfg.PLOT_DATA][idx]["file_path"],
                    self.projectFileName,
                )
                if not data_file_path:
                    QMessageBox.critical(
                        self,
                        cfg.programName,
                        "Data file not found:\n{}".format(self.pj[cfg.OBSERVATIONS][self.observationId][cfg.PLOT_DATA][idx]["file_path"]),
                    )
                    data_ok = False
                    # return False

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
                            "Impossible to plot data from file "
                            f"{os.path.basename(self.pj[cfg.OBSERVATIONS][self.observationId][cfg.PLOT_DATA][idx]['file_path'])}:\n"
                            f"{w1.error_msg}"
                        ),
                    )
                    del w1
                    data_ok = False
                    # return False

                if data_ok:
                    w1.setWindowFlags(Qt.WindowStaysOnTopHint)
                    w1.sendEvent.connect(self.signal_from_widget)  # keypress event

                    w1.show()

                    self.ext_data_timer_list.append(QTimer())
                    self.ext_data_timer_list[-1].setInterval(w1.time_out)
                    self.ext_data_timer_list[-1].timeout.connect(lambda: self.timer_plot_data_out(w1))
                    self.timer_plot_data_out(w1)

                    self.plot_data[count] = w1

            if count == 1:
                data_ok: bool = True
                data_file_path = project_functions.full_path(
                    self.pj[cfg.OBSERVATIONS][self.observationId][cfg.PLOT_DATA][idx]["file_path"],
                    self.projectFileName,
                )
                if not data_file_path:
                    QMessageBox.critical(
                        self,
                        cfg.programName,
                        "Data file not found:\n{}".format(self.pj[cfg.OBSERVATIONS][self.observationId][cfg.PLOT_DATA][idx]["file_path"]),
                    )
                    data_ok = False
                    # return False

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
                        (
                            f"Impossible to plot data from file "
                            f"{os.path.basename(self.pj[cfg.OBSERVATIONS][self.observationId][cfg.PLOT_DATA][idx]['file_path'])}:\n{w2.error_msg}"
                        ),
                    )
                    del w2
                    data_ok = False
                    # return False

                if data_ok:
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

    self.load_tw_events(self.observationId)

    # initial synchro
    if not sys.platform.startswith(cfg.MACOS_CODE):
        for n_player in range(1, len(self.dw_player)):
            self.sync_time(n_player, 0)

    self.mpv_timer_out(value=0.0)

    """
    if self.pj[cfg.OBSERVATIONS][self.observationId][cfg.MEDIA_INFO].get(cfg.OVERLAY, {}):
        for i in range(cfg.N_PLAYER):
            # restore overlays
            if str(i + 1) in self.pj[cfg.OBSERVATIONS][self.observationId][cfg.MEDIA_INFO][cfg.OVERLAY]:
                self.overlays[i] = self.dw_player[i].player.create_image_overlay()
                self.resize_dw(i)
    """

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

    # button start enabled
    self.pb_live_obs.setEnabled(True)

    self.w_live.setVisible(True)
    self.w_obs_info.setVisible(True)

    menu_options.update_menu(self)

    self.liveObservationStarted = False
    self.pb_live_obs.setText("Start live observation")

    if self.pj[cfg.OBSERVATIONS][self.observationId].get(cfg.START_FROM_CURRENT_TIME, False):
        current_time = util.seconds_of_day(dt.datetime.now())
    elif self.pj[cfg.OBSERVATIONS][self.observationId].get(cfg.START_FROM_CURRENT_EPOCH_TIME, False):
        current_time = time.mktime(dt.datetime.now().timetuple())
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

    self.load_tw_events(self.observationId)

    self.get_events_current_row()


def initialize_new_images_observation(self):
    """
    initialize a new observation from directories of images
    """

    for dw in (self.dwEthogram, self.dwSubjects, self.dwEvents):
        dw.setVisible(True)
    # disable start live button
    self.pb_live_obs.setEnabled(False)
    self.w_live.setVisible(False)

    # check if directories are available
    ok, msg = project_functions.check_directories_availability(self.pj[cfg.OBSERVATIONS][self.observationId], self.projectFileName)

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
        full_dir_path = project_functions.full_path(dir_path, self.projectFileName)
        result = util.dir_images_number(full_dir_path)
        tot_images_number += result.get("number of images", 0)

    if not tot_images_number:
        QMessageBox.critical(
            self,
            cfg.programName,
            (
                "No images were found in directory(ies).<br><br>The observation will be opened in VIEW mode.<br>"
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
    self.images_list: list = []
    for dir_path in self.pj[cfg.OBSERVATIONS][self.observationId].get(cfg.DIRECTORIES_LIST, []):
        full_dir_path = project_functions.full_path(dir_path, self.projectFileName)
        for pattern in cfg.IMAGE_EXTENSIONS:
            self.images_list.extend(
                sorted(
                    list(
                        set(
                            [str(x) for x in pl.Path(full_dir_path).glob(pattern)]
                            + [str(x) for x in pl.Path(full_dir_path).glob(pattern.upper())]
                        )
                    )
                )
            )

    # logging.debug(self.images_list)

    self.image_idx = 0
    self.image_time_ref = None

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

    self.extract_frame(self.dw_player[i])
    self.w_obs_info.setVisible(True)

    self.get_events_current_row()


def event2media_file_name(observation: dict, timestamp: dec) -> Optional[str]:
    """
    returns the media file name corresponding to the event (start time in case of state event)

    Args:
        observation (dict): observation
        timestamp (dec): time stamp

    Returns:
        str: name of media file containing the event
    """

    cumul_media_durations: list = [dec(0)]
    for media_file in observation[cfg.FILE][cfg.PLAYER1]:
        media_duration = dec(str(observation[cfg.MEDIA_INFO][cfg.LENGTH][media_file]))
        cumul_media_durations.append(round(cumul_media_durations[-1] + media_duration, 3))

    cumul_media_durations.remove(dec(0))

    # test if timestamp is at end of last media
    if timestamp == cumul_media_durations[-1]:
        player_idx = len(observation[cfg.FILE][cfg.PLAYER1]) - 1
    else:
        player_idx = -1
        for idx, value in enumerate(cumul_media_durations):
            start = 0 if idx == 0 else cumul_media_durations[idx - 1]
            if start <= timestamp < value:
                player_idx = idx
                break

    if player_idx != -1:
        video_file_name = observation[cfg.FILE][cfg.PLAYER1][player_idx]
    else:
        video_file_name = None

    return video_file_name


def create_observations(self):
    """
    Create observations from a media file directory
    """
    # print(self.pj[cfg.OBSERVATIONS])

    dir_path = QFileDialog.getExistingDirectory(None, "Select directory", os.getenv("HOME"))
    if not dir_path:
        return

    dlg = dialog.Input_dialog(
        label_caption="Set the following observation parameters",
        elements_list=[
            ("cb", "Recurse the subdirectories", False),
            ("cb", "Save the absolute media file path", True),
            ("cb", "Visualize spectrogram", False),
            ("cb", "Visualize waveform", False),
            ("cb", "Media creation date as offset", False),
            ("cb", "Close behaviors between videos", False),
            ("dsb", "Time offset (in seconds)", 0.0, 86400, 1, 0, 3),
            ("dsb", "Media scan sampling duration (in seconds)", 0.0, 86400, 1, 0, 3),
        ],
        title="Observation parameters",
    )
    if not dlg.exec_():
        return

    file_count: int = 0

    if dlg.elements["Recurse the subdirectories"].isChecked():
        files_list = pl.Path(dir_path).rglob("*")
    else:
        files_list = pl.Path(dir_path).glob("*")

    for file in files_list:
        if not file.is_file():
            continue
        r = util.accurate_media_analysis(ffmpeg_bin=self.ffmpeg_bin, file_name=file)
        if "error" not in r:
            if not r.get("frames_number", 0):
                continue

            if dlg.elements["Save the absolute media file path"].isChecked():
                media_file = str(file)
            else:
                try:
                    media_file = str(file.relative_to(pl.Path(self.projectFileName).parent))
                except ValueError:
                    QMessageBox.critical(
                        self,
                        cfg.programName,
                        (
                            f"the media file <b>{file}</b> can not be relative to the project directory "
                            f"(<b>{pl.Path(self.projectFileName).parent}</b>)"
                            "<br><br>Aborting the creation of observations"
                        ),
                    )
                    return

            if media_file in self.pj[cfg.OBSERVATIONS]:
                QMessageBox.critical(
                    self,
                    cfg.programName,
                    (f"The observation <b>{media_file}</b> already exists.<br><br>Aborting the creation of observations"),
                )
                return

            self.pj[cfg.OBSERVATIONS][media_file] = {
                "file": {"1": [media_file], "2": [], "3": [], "4": [], "5": [], "6": [], "7": [], "8": []},
                "type": "MEDIA",
                "date": dt.datetime.now().replace(microsecond=0).isoformat(),
                "description": "",
                "time offset": dec(str(round(dlg.elements["Time offset (in seconds)"].value(), 3))),
                "events": [],
                "observation time interval": [0, 0],
                "independent_variables": {},
                "visualize_spectrogram": dlg.elements["Visualize spectrogram"].isChecked(),
                "visualize_waveform": dlg.elements["Visualize waveform"].isChecked(),
                "media_creation_date_as_offset": dlg.elements["Media creation date as offset"].isChecked(),
                "media_scan_sampling_duration": dec(str(round(dlg.elements["Media scan sampling duration (in seconds)"].value(), 3))),
                "image_display_duration": 1,
                "close_behaviors_between_videos": dlg.elements["Close behaviors between videos"].isChecked(),
                "media_info": {
                    "length": {media_file: r["duration"]},
                    "fps": {media_file: r["duration"]},
                    "hasVideo": {media_file: r["has_video"]},
                    "hasAudio": {media_file: r["has_audio"]},
                    "offset": {"1": 0.0},
                },
            }
            file_count += 1
            self.project_changed()

    if file_count:
        message: str = f"{file_count} observation(s) were created" if file_count > 1 else "One observation was created"
    else:
        message: str = f"No media file were found in {dir_path}"

    QMessageBox.information(self, cfg.programName, message)
