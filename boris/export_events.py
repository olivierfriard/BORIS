"""
BORIS
Behavioral Observation Research Interactive Software
Copyright 2012-2024 Olivier Friard

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

import datetime as dt
import logging
import math
import os
import tablib
import pathlib as pl
from decimal import Decimal as dec

from . import observation_operations
from . import utilities as util
from . import config as cfg
from . import select_observations
from . import export_observation
from . import select_subj_behav
from . import project_functions
from . import dialog
from . import db_functions

from PyQt5.QtWidgets import QApplication, QFileDialog, QMessageBox, QInputDialog


def export_events_as_behavioral_sequences(self, separated_subjects=False, timed=False):
    """
    export events from selected observations by subject as behavioral sequences (plain text file)
    behaviors are separated by character specified in self.behav_seq_separator (usually pipe |)
    for use with Behatrix (see https://www.boris.unito.it/pages/behatrix)

    Args:
        separated_subjects (bool):
        timed (bool):
    """

    # ask user for observations to analyze
    _, selected_observations = select_observations.select_observations2(
        self, cfg.MULTIPLE, "Select observations to export as behavioral sequences"
    )

    if not selected_observations:
        return

    # check if coded behaviors are defined in ethogram
    if project_functions.check_coded_behaviors_in_obs_list(self.pj, selected_observations):
        return

    # check if state events are paired
    not_ok, selected_observations = project_functions.check_state_events(self.pj, selected_observations)
    if not_ok or not selected_observations:
        return

    if len(selected_observations) == 1:
        max_media_duration_all_obs, _ = observation_operations.media_duration(self.pj[cfg.OBSERVATIONS], selected_observations)
        start_coding, end_coding, _ = observation_operations.coding_time(self.pj[cfg.OBSERVATIONS], selected_observations)
    else:
        max_media_duration_all_obs = None
        start_coding, end_coding = dec("NaN"), dec("NaN")

    parameters = select_subj_behav.choose_obs_subj_behav_category(
        self,
        selected_observations,
        start_coding=start_coding,
        end_coding=end_coding,
        maxTime=max_media_duration_all_obs,
        flagShowIncludeModifiers=True,
        flagShowExcludeBehaviorsWoEvents=False,
        n_observations=len(selected_observations),
    )

    if parameters == {}:
        return
    if not parameters[cfg.SELECTED_SUBJECTS] or not parameters[cfg.SELECTED_BEHAVIORS]:
        QMessageBox.warning(None, cfg.programName, "Select subject(s) and behavior(s) to analyze")
        return

    fn = QFileDialog().getSaveFileName(self, "Export events as behavioral sequences", "", "Text files (*.txt);;All files (*)")
    file_name = fn[0] if type(fn) is tuple else fn

    if file_name:
        r, msg = export_observation.observation_to_behavioral_sequences(
            pj=self.pj,
            selected_observations=selected_observations,
            parameters=parameters,
            behaviors_separator=self.behav_seq_separator,
            separated_subjects=separated_subjects,
            timed=timed,
            file_name=file_name,
        )
        if not r:
            logging.critical(f"Error while exporting events as behavioral sequences: {msg}")
            QMessageBox.critical(
                None,
                cfg.programName,
                f"Error while exporting events as behavioral sequences:<br>{msg}",
                QMessageBox.Ok | QMessageBox.Default,
                QMessageBox.NoButton,
            )


def export_tabular_events(self, mode: str = "tabular") -> None:
    """
    * select observations
    * export events from the selected observations in various formats: TSV, CSV, ODS, XLSX, XLS, HTML

    Args:
        mode (str): export mode: must be ["tabular", "jwatcher"]
    """

    # ask user observations to analyze
    _, selected_observations = select_observations.select_observations2(
        self, cfg.MULTIPLE, windows_title="Select observations for exporting events"
    )

    if not selected_observations:
        return

    if mode == "jwatcher":
        # check if images observation in list
        max_obs_length, _ = observation_operations.observation_length(self.pj, selected_observations)

        # exit with message if events do not have timestamp
        if max_obs_length.is_nan():
            QMessageBox.critical(
                None,
                cfg.programName,
                ("This function is not available for observations with events that do not have timestamp"),
                QMessageBox.Ok | QMessageBox.Default,
                QMessageBox.NoButton,
            )
            return

    # check if coded behaviors are defined in ethogram
    if project_functions.check_coded_behaviors_in_obs_list(self.pj, selected_observations):
        return

    # check if state events are paired
    not_ok, selected_observations = project_functions.check_state_events(self.pj, selected_observations)
    if not_ok or not selected_observations:
        return

    if len(selected_observations) == 1:
        max_media_duration_all_obs, _ = observation_operations.media_duration(self.pj[cfg.OBSERVATIONS], selected_observations)
        start_coding, end_coding, _ = observation_operations.coding_time(self.pj[cfg.OBSERVATIONS], selected_observations)
    else:
        max_media_duration_all_obs = None
        start_coding, end_coding = dec("NaN"), dec("NaN")

    parameters = select_subj_behav.choose_obs_subj_behav_category(
        self,
        selected_observations,
        start_coding=start_coding,
        end_coding=end_coding,
        maxTime=max_media_duration_all_obs,
        flagShowIncludeModifiers=False,
        flagShowExcludeBehaviorsWoEvents=False,
        n_observations=len(selected_observations),
    )
    if parameters == {}:
        return
    if not parameters[cfg.SELECTED_SUBJECTS] or not parameters[cfg.SELECTED_BEHAVIORS]:
        QMessageBox.warning(None, cfg.programName, "Select subject(s) and behavior(s) to analyze")
        return

    if mode == "tabular":
        available_formats = (
            cfg.TSV,
            cfg.CSV,
            cfg.ODS,
            cfg.XLSX,
            cfg.XLS,
            cfg.HTML,
            cfg.PANDAS_DF,
            cfg.RDS,
        )
        if len(selected_observations) > 1:  # choose directory for exporting observations
            item, ok = QInputDialog.getItem(
                self,
                "Export events format",
                "Available formats",
                available_formats,
                0,
                False,
            )
            if not ok:
                return
            output_format = cfg.FILE_NAME_SUFFIX[item]

            exportDir = QFileDialog().getExistingDirectory(
                self,
                "Choose a directory to export events",
                os.path.expanduser("~"),
                options=QFileDialog.ShowDirsOnly,
            )
            if not exportDir:
                return

        if len(selected_observations) == 1:
            file_name, filter_ = QFileDialog().getSaveFileName(self, "Export events", "", ";;".join(available_formats))
            if not file_name:
                return

            output_format = cfg.FILE_NAME_SUFFIX[filter_]
            if pl.Path(file_name).suffix != "." + output_format:
                file_name = str(pl.Path(file_name)) + "." + output_format
                # check if file with new extension already exists
                if pl.Path(file_name).is_file():
                    if (
                        dialog.MessageDialog(cfg.programName, f"The file {file_name} already exists.", [cfg.CANCEL, cfg.OVERWRITE])
                        == cfg.CANCEL
                    ):
                        return

    if mode == "jwatcher":
        exportDir = QFileDialog().getExistingDirectory(
            self, "Choose a directory to export events", os.path.expanduser("~"), options=QFileDialog.ShowDirsOnly
        )
        if not exportDir:
            return

        output_format = "dat"

    mem_command = ""  # remember user choice when file already exists
    for obs_id in selected_observations:
        if len(selected_observations) > 1 or mode == "jwatcher":
            file_name = f"{pl.Path(exportDir) / util.safeFileName(obs_id)}.{output_format}"
            # check if file with new extension already exists
            if mem_command != cfg.OVERWRITE_ALL and pl.Path(file_name).is_file():
                if mem_command == cfg.SKIP_ALL:
                    continue
                mem_command = dialog.MessageDialog(
                    cfg.programName,
                    f"The file {file_name} already exists.",
                    [cfg.OVERWRITE, cfg.OVERWRITE_ALL, cfg.SKIP, cfg.SKIP_ALL, cfg.CANCEL],
                )
                if mem_command == cfg.CANCEL:
                    return
                if mem_command in [cfg.SKIP, cfg.SKIP_ALL]:
                    continue

        if mode == "tabular":
            r, msg = export_observation.export_tabular_events(
                self.pj,
                parameters,
                obs_id,
                self.pj[cfg.OBSERVATIONS][obs_id],
                self.pj[cfg.ETHOGRAM],
                file_name,
                output_format,
            )

        if mode == "jwatcher":
            r, msg = export_observation.export_events_jwatcher(
                parameters, obs_id, self.pj[cfg.OBSERVATIONS][obs_id], self.pj[cfg.ETHOGRAM], file_name, output_format
            )

        if not r and msg:
            QMessageBox.critical(None, cfg.programName, msg, QMessageBox.Ok | QMessageBox.Default, QMessageBox.NoButton)


def export_aggregated_events(self):
    """
    - select observations.
    - select subjects and behaviors
    - export events in aggregated format

    Formats can be SQL (sql), SDIS (sds) or Tabular format (tsv, csv, ods, xlsx, xls, html)
    """

    def fields_type(max_modif_number: int) -> dict:
        fields_type_dict: dict = {
            "Observation id": str,
            "Observation date": dt.datetime,
            "Description": str,
            "Observation type": str,
            "Source": str,
            "Time offset (s)": str,
            "Coding duration": float,
            "Media duration (s)": str,
            "FPS (frame/s)": str,
        }
        # TODO: "Media duration (s)" and "FPS (frame/s)" can be float for observation from 1 video

        if cfg.INDEPENDENT_VARIABLES in self.pj:
            for idx in util.sorted_keys(self.pj[cfg.INDEPENDENT_VARIABLES]):
                if self.pj[cfg.INDEPENDENT_VARIABLES][idx]["type"] == "timestamp":
                    fields_type_dict[self.pj[cfg.INDEPENDENT_VARIABLES][idx]["label"]] = dt.datetime
                elif self.pj[cfg.INDEPENDENT_VARIABLES][idx]["type"] == "numeric":
                    fields_type_dict[self.pj[cfg.INDEPENDENT_VARIABLES][idx]["label"]] = float
                else:
                    fields_type_dict[self.pj[cfg.INDEPENDENT_VARIABLES][idx]["label"]] = str

        fields_type_dict.update(
            {
                "Subject": str,
                "Observation duration by subject by observation": float,
                "Behavior": str,
                "Behavioral category": str,
            }
        )

        # max number of modifiers
        for i in range(max_modif_number):
            fields_type_dict[f"Modifier #{i + 1}"] = str

        fields_type_dict.update(
            {
                "Behavior type": str,
                "Start (s)": float,
                "Stop (s)": float,
                "Duration (s)": float,
                "Media file name": str,
                "Image index start": float,  # add image index and image file path to header
                "Image index stop": float,
                "Image file path start": str,
                "Image file path stop": str,
                "Comment start": str,
                "Comment stop": str,
            }
        )

        return fields_type_dict

    _, selected_observations = select_observations.select_observations2(self, cfg.MULTIPLE, "Select observations for exporting events")
    if not selected_observations:
        return

    # check if coded behaviors are defined in ethogram
    if project_functions.check_coded_behaviors_in_obs_list(self.pj, selected_observations):
        return

    # check if state events are paired
    not_ok, selected_observations = project_functions.check_state_events(self.pj, selected_observations)
    if not_ok or not selected_observations:
        return

    if len(selected_observations) == 1:
        max_media_duration_all_obs, _ = observation_operations.media_duration(self.pj[cfg.OBSERVATIONS], selected_observations)
        start_coding, end_coding, _ = observation_operations.coding_time(self.pj[cfg.OBSERVATIONS], selected_observations)
    else:
        max_media_duration_all_obs = None
        start_coding, end_coding = dec("NaN"), dec("NaN")

    parameters = select_subj_behav.choose_obs_subj_behav_category(
        self,
        selected_observations,
        start_coding=start_coding,
        end_coding=end_coding,
        maxTime=max_media_duration_all_obs,
        flagShowIncludeModifiers=False,
        flagShowExcludeBehaviorsWoEvents=False,
        n_observations=len(selected_observations),
    )
    if parameters == {}:
        return
    if not parameters[cfg.SELECTED_SUBJECTS] or not parameters[cfg.SELECTED_BEHAVIORS]:
        QMessageBox.warning(None, cfg.programName, "Select subject(s) and behavior(s) to analyze")
        return

    # check for grouping results
    flag_group = True
    if len(selected_observations) > 1:
        flag_group = (
            dialog.MessageDialog(cfg.programName, "Group events from selected observations in one file?", [cfg.YES, cfg.NO]) == cfg.YES
        )

    if flag_group:
        file_formats = (
            cfg.TSV,
            cfg.CSV,
            cfg.ODS,
            cfg.XLSX,
            cfg.XLS,
            cfg.HTML,
            cfg.SDIS,
            cfg.TBS,
            cfg.SQL,
            cfg.PANDAS_DF,
            cfg.RDS,
        )

        fileName, filter_ = QFileDialog().getSaveFileName(self, "Export aggregated events", "", ";;".join(file_formats))

        if not fileName:
            return

        outputFormat = cfg.FILE_NAME_SUFFIX[filter_]
        if pl.Path(fileName).suffix != "." + outputFormat:
            # check if file with new extension already exists
            fileName = str(pl.Path(fileName)) + "." + outputFormat
            if pl.Path(fileName).is_file():
                if dialog.MessageDialog(cfg.programName, f"The file {fileName} already exists.", [cfg.CANCEL, cfg.OVERWRITE]) == cfg.CANCEL:
                    return

    else:  # not grouping
        file_formats = (
            cfg.TSV,
            cfg.CSV,
            cfg.ODS,
            cfg.XLSX,
            cfg.XLS,
            cfg.HTML,
            cfg.SDIS,
            cfg.TBS,
            cfg.PANDAS_DF,
            cfg.RDS,
        )
        item, ok = QInputDialog.getItem(self, "Export events format", "Available formats", file_formats, 0, False)
        if not ok:
            return
        # read the output format code
        outputFormat = cfg.FILE_NAME_SUFFIX[item]

        exportDir = QFileDialog().getExistingDirectory(
            self, "Choose a directory to export events", os.path.expanduser("~"), options=QFileDialog.ShowDirsOnly
        )
        if not exportDir:
            return

    if outputFormat == cfg.SQL_EXT:
        _, _, conn = db_functions.load_aggregated_events_in_db(
            self.pj, parameters[cfg.SELECTED_SUBJECTS], selected_observations, parameters[cfg.SELECTED_BEHAVIORS]
        )
        try:
            with open(fileName, "w") as f:
                for line in conn.iterdump():
                    f.write(f"{line}\n")
        except Exception:
            QMessageBox.critical(
                None,
                cfg.programName,
                f"The file {fileName} can not be saved",
                QMessageBox.Ok | QMessageBox.Default,
                QMessageBox.NoButton,
            )

        return

    # compute the maximum number of modifiers
    tot_max_modifiers: int = 0
    for obs_id in selected_observations:
        _, max_modifiers = export_observation.export_aggregated_events(self.pj, parameters, obs_id)
        tot_max_modifiers = max(tot_max_modifiers, max_modifiers)

    data_grouped_obs = tablib.Dataset()

    mem_command: str = ""  # remember user choice when file already exists
    header = list(fields_type(tot_max_modifiers).keys())

    for obs_id in selected_observations:
        logging.debug(f"Exporting aggregated events for obs Id: {obs_id}")

        data_single_obs, _ = export_observation.export_aggregated_events(
            self.pj, parameters, obs_id, force_number_modifiers=tot_max_modifiers
        )

        try:
            # order by start time
            index = header.index("Start (s)")
            if cfg.NA not in [x[index] for x in list(data_single_obs)]:
                data_single_obs_sorted = tablib.Dataset(
                    *sorted(list(data_single_obs), key=lambda x: float(x[index])),
                    headers=list(fields_type(tot_max_modifiers).keys()),
                )
            else:
                # order by image index
                index = header.index("Image index start")
                data_single_obs_sorted = tablib.Dataset(
                    *sorted(list(data_single_obs), key=lambda x: float(x[index])),
                    headers=list(fields_type(tot_max_modifiers).keys()),
                )
        except Exception:
            # if error no order
            data_single_obs_sorted = tablib.Dataset(
                *list(data_single_obs),
                headers=list(fields_type(tot_max_modifiers).keys()),
            )

        data_single_obs_sorted.title = obs_id

        if (not flag_group) and (outputFormat not in (cfg.SDIS_EXT, cfg.TBS_EXT)):
            fileName = f"{pl.Path(exportDir) / util.safeFileName(obs_id)}.{outputFormat}"
            # check if file with new extension already exists
            if mem_command != cfg.OVERWRITE_ALL and pl.Path(fileName).is_file():
                if mem_command == cfg.SKIP_ALL:
                    continue
                mem_command = dialog.MessageDialog(
                    cfg.programName,
                    f"The file {fileName} already exists.",
                    [cfg.OVERWRITE, cfg.OVERWRITE_ALL, cfg.SKIP, cfg.SKIP_ALL, cfg.CANCEL],
                )
                if mem_command == cfg.CANCEL:
                    return
                if mem_command in (cfg.SKIP, cfg.SKIP_ALL):
                    continue

            r, msg = export_observation.dataset_write(data_single_obs_sorted, fileName, outputFormat, dtype=fields_type(max_modifiers))
            if not r:
                QMessageBox.warning(None, cfg.programName, msg, QMessageBox.Ok | QMessageBox.Default, QMessageBox.NoButton)

        if len(data_single_obs_sorted) and max_modifiers < tot_max_modifiers:
            for i in range(tot_max_modifiers - max_modifiers):
                data_single_obs_sorted.insert_col(
                    14,
                    col=[""] * (len(list(data_single_obs_sorted))),
                    header=f"Modif #{i}",
                )
        data_grouped_obs.extend(data_single_obs_sorted)

    data_grouped_obs_all = tablib.Dataset(headers=list(fields_type(tot_max_modifiers).keys()))
    data_grouped_obs_all.extend(data_grouped_obs)
    data_grouped_obs_all.title = "Aggregated events"

    start_idx = header.index("Start (s)")
    stop_idx = header.index("Stop (s)")

    if outputFormat == cfg.TBS_EXT:  # Timed behavioral sequences
        out: str = ""
        for obs_id in selected_observations:
            # observation id
            out += f"# {obs_id}\n"

            for event in list(data_grouped_obs_all):
                if event[0] == obs_id:
                    behavior = event[header.index("Behavior")]
                    subject = event[header.index("Subject")]
                    # replace various char by _
                    for char in (" ", "-", "/"):
                        behavior = behavior.replace(char, "_")
                        subject = subject.replace(char, "_")
                    event_start = f"{float(event[start_idx]):.3f}"  # start event
                    if not event[stop_idx]:  # stop event (from end)
                        event_stop = f"{float(event[start_idx]) + 0.001:.3f}"
                    else:
                        event_stop = f"{float(event[stop_idx]):.3f}"

                    bs_timed = [f"{subject}_{behavior}"] * round((float(event_stop) - float(event_start)) * 100)
                    out += "|".join(bs_timed)

            out += "\n"

            if not flag_group:
                fileName = f"{pl.Path(exportDir) / util.safeFileName(obs_id)}.{outputFormat}"
                with open(fileName, "wb") as f:
                    f.write(str.encode(out))
                out = ""

        if flag_group:
            with open(fileName, "wb") as f:
                f.write(str.encode(out))
        return

    if outputFormat == cfg.SDIS_EXT:  # SDIS format
        out: str = "% SDIS file created by BORIS (www.boris.unito.it) " f"at {util.datetime_iso8601(dt.datetime.now())}\nTimed <seconds>;\n"
        for obs_id in selected_observations:
            # observation id
            out += "\n<{}>\n".format(obs_id)

            for event in list(data_grouped_obs_all):
                if event[0] == obs_id:
                    behavior = event[header.index("Behavior")]
                    subject = event[header.index("Subject")]
                    # replace various char by _
                    for char in (" ", "-", "/"):
                        behavior = behavior.replace(char, "_")
                        subject = subject.replace(char, "_")

                    event_start = f"{float(event[start_idx]):.3f}"  # start event
                    if not event[stop_idx]:  # stop event (from end)
                        event_stop = f"{float(event[start_idx]) + 0.001:.3f}"
                    else:
                        event_stop = f"{float(event[stop_idx]):.3f}"
                    out += f"{subject}_{behavior},{event_start}-{event_stop} "

            out += "/\n\n"
            if not flag_group:
                fileName = f"{pl.Path(exportDir) / util.safeFileName(obs_id)}.{outputFormat}"
                with open(fileName, "wb") as f:
                    f.write(str.encode(out))
                out = (
                    "% SDIS file created by BORIS (www.boris.unito.it) "
                    f"at {util.datetime_iso8601(dt.datetime.now())}\nTimed <seconds>;\n"
                )

        if flag_group:
            with open(fileName, "wb") as f:
                f.write(str.encode(out))
        return

    if flag_group:
        r, msg = export_observation.dataset_write(data_grouped_obs_all, fileName, outputFormat, dtype=fields_type(max_modifiers))
        if not r:
            QMessageBox.warning(None, cfg.programName, msg, QMessageBox.Ok | QMessageBox.Default, QMessageBox.NoButton)


def export_events_as_textgrid(self) -> None:
    """
    * select observations
    * select subjects, behaviors and time interval
    * export state events of selected observations as Praat textgrid
    """

    _, selected_observations = select_observations.select_observations2(self, mode=cfg.MULTIPLE, windows_title="")

    if not selected_observations:
        return

    # check if coded behaviors are defined in ethogram
    if project_functions.check_coded_behaviors_in_obs_list(self.pj, selected_observations):
        return

    # check if state events are paired
    not_ok, selected_observations = project_functions.check_state_events(self.pj, selected_observations)
    if not_ok or not selected_observations:
        return

    max_obs_length, _ = observation_operations.observation_length(self.pj, selected_observations)

    # exit with message if events do not have timestamp
    if max_obs_length.is_nan():
        QMessageBox.critical(
            None,
            cfg.programName,
            ("This function is not available for observations with events that do not have timestamp"),
            QMessageBox.Ok | QMessageBox.Default,
            QMessageBox.NoButton,
        )
        return

    start_coding, end_coding, _ = observation_operations.coding_time(self.pj[cfg.OBSERVATIONS], selected_observations)

    parameters = select_subj_behav.choose_obs_subj_behav_category(
        self,
        selected_observations,
        start_coding=start_coding,
        end_coding=end_coding,
        flagShowIncludeModifiers=False,
        flagShowExcludeBehaviorsWoEvents=False,
        maxTime=max_obs_length,
        n_observations=len(selected_observations),
    )
    if parameters == {}:
        return
    if not parameters[cfg.SELECTED_SUBJECTS] or not parameters[cfg.SELECTED_BEHAVIORS]:
        QMessageBox.warning(None, cfg.programName, "Select subject(s) and behavior(s) to export")
        return

    export_dir = QFileDialog(self).getExistingDirectory(
        self, "Export events as Praat TextGrid", os.path.expanduser("~"), options=QFileDialog(self).ShowDirsOnly
    )
    if not export_dir:
        return

    mem_command = ""

    # see https://www.fon.hum.uva.nl/praat/manual/TextGrid_file_formats.html

    interval_subject_header = (
        "    item [{subject_index}]:\n"
        '        class = "IntervalTier"\n'
        '        name = "{subject}"\n'
        "        xmin = 0.0\n"
        "        xmax = {intervalsMax}\n"
        "        intervals: size = {intervalsSize}\n"
    )

    interval_template = (
        "        intervals [{count}]:\n" "            xmin = {xmin}\n" "            xmax = {xmax}\n" '            text = "{name}"\n'
    )

    point_subject_header = (
        "    item [{subject_index}]:\n"
        '        class = "TextTier"\n'
        '        name = "{subject}"\n'
        "        xmin = {intervalsMin}\n"
        "        xmax = {intervalsMax}\n"
        "        points: size = {intervalsSize}\n"
    )

    point_template = "        points [{count}]:\n" "            number = {number}\n" '            mark = "{mark}"\n'

    # widget for results
    self.results = dialog.Results_dialog()
    self.results.setWindowTitle(f"{cfg.programName} - Export events as Praat TextGrid")
    self.results.show()

    ok, msg, db_connector = db_functions.load_aggregated_events_in_db(
        self.pj, parameters[cfg.SELECTED_SUBJECTS], selected_observations, parameters[cfg.SELECTED_BEHAVIORS]
    )

    if db_connector is None:
        logging.critical("Error when loading aggregated events in DB")
        return

    cursor = db_connector.cursor()

    file_count: int = 0

    for obs_id in selected_observations:
        if parameters["time"] == cfg.TIME_EVENTS:
            start_coding, end_coding, coding_duration = observation_operations.coding_time(self.pj[cfg.OBSERVATIONS], [obs_id])
            if start_coding is None and end_coding is None:  # no events
                self.results.ptText.appendHtml(f"The observation <b>{obs_id}</b> does not have events.")
                QApplication.processEvents()
                continue

            if math.isnan(start_coding) or math.isnan(end_coding):  # obs with no timestamp
                self.results.ptText.appendHtml(f"The observation <b>{obs_id}</b> does not have timestamp.")
                QApplication.processEvents()
                continue

            min_time = float(start_coding)
            max_time = float(end_coding)

        if parameters["time"] == cfg.TIME_FULL_OBS:
            if self.pj[cfg.OBSERVATIONS][obs_id][cfg.TYPE] == cfg.MEDIA:
                max_media_duration, _ = observation_operations.media_duration(self.pj[cfg.OBSERVATIONS], [obs_id])
                min_time = float(0)
                max_time = float(max_media_duration)
                coding_duration = max_media_duration

            if self.pj[cfg.OBSERVATIONS][obs_id][cfg.TYPE] in (cfg.LIVE, cfg.IMAGES):
                start_coding, end_coding, coding_duration = observation_operations.coding_time(self.pj[cfg.OBSERVATIONS], [obs_id])
                if start_coding is None and end_coding is None:  # no events
                    self.results.ptText.appendHtml(f"The observation <b>{obs_id}</b> does not have events.")
                    QApplication.processEvents()
                    continue
                if math.isnan(start_coding) or math.isnan(end_coding):  # obs with no timestamp
                    self.results.ptText.appendHtml(f"The observation <b>{obs_id}</b> does not have timestamp.")
                    QApplication.processEvents()
                    continue

                min_time = float(start_coding)
                max_time = float(end_coding)

        if parameters["time"] == cfg.TIME_ARBITRARY_INTERVAL:
            min_time = float(parameters[cfg.START_TIME])
            max_time = float(parameters[cfg.END_TIME])

        # delete events outside time interval
        cursor.execute(
            "DELETE FROM aggregated_events WHERE observation = ? AND (start < ? AND stop < ?) OR (start > ? AND stop > ?)",
            (
                obs_id,
                min_time,
                min_time,
                max_time,
                max_time,
            ),
        )
        cursor.execute(
            "UPDATE aggregated_events SET start = ? WHERE observation = ? AND start < ? AND stop BETWEEN ? AND ?",
            (
                min_time,
                obs_id,
                min_time,
                min_time,
                max_time,
            ),
        )
        cursor.execute(
            "UPDATE aggregated_events SET stop = ? WHERE observation = ? AND stop > ? AND start BETWEEN ? AND ?",
            (
                max_time,
                obs_id,
                max_time,
                min_time,
                max_time,
            ),
        )
        cursor.execute(
            "UPDATE aggregated_events SET start = ?, stop = ? WHERE observation = ? AND start < ? AND stop > ?",
            (
                min_time,
                max_time,
                obs_id,
                min_time,
                max_time,
            ),
        )

        next_obs: bool = False

        """
        total_media_duration = round(
            observation_operations.observation_total_length(self.pj[cfg.OBSERVATIONS][obs_id]), 3
        )
        """

        cursor.execute(
            (
                "SELECT COUNT(DISTINCT subject) FROM aggregated_events "
                "WHERE observation = ? AND subject IN ({}) AND type = 'STATE' ".format(
                    ",".join(["?"] * len(parameters[cfg.SELECTED_SUBJECTS]))
                )
            ),
            [obs_id] + parameters[cfg.SELECTED_SUBJECTS],
        )

        subjectsNum = int(cursor.fetchone()[0])
        """subjectsMin = min_time"""
        subjectsMax = max_time

        out = (
            'File type = "ooTextFile"\n'
            'Object class = "TextGrid"\n'
            "\n"
            f"xmin = 0.0\n"
            f"xmax = {subjectsMax}\n"
            "tiers? <exists>\n"
            f"size = {subjectsNum}\n"
            "item []:\n"
        )

        subject_index = 0
        for subject in parameters[cfg.SELECTED_SUBJECTS]:
            if subject not in [
                x[cfg.EVENT_SUBJECT_FIELD_IDX] if x[cfg.EVENT_SUBJECT_FIELD_IDX] else cfg.NO_FOCAL_SUBJECT
                for x in self.pj[cfg.OBSERVATIONS][obs_id][cfg.EVENTS]
            ]:
                continue

            intervalsMin, intervalsMax = min_time, max_time

            # STATE events
            cursor.execute(
                (
                    "SELECT start, stop, behavior FROM aggregated_events "
                    "WHERE observation = ? AND subject = ? AND type = 'STATE' ORDER BY start"
                ),
                (obs_id, subject),
            )

            rows = [
                {"start": util.float2decimal(r["start"]), "stop": util.float2decimal(r["stop"]), "code": r["behavior"]}
                for r in cursor.fetchall()
            ]
            if not rows:
                continue

            out += interval_subject_header

            count = 0

            # check if 1st behavior starts at the beginning
            if rows[0]["start"] > 0:
                count += 1
                out += interval_template.format(count=count, name="null", xmin=0.0, xmax=rows[0]["start"])

            for idx, row in enumerate(rows):
                # check if events are overlapping
                if (idx + 1 < len(rows)) and (row["stop"] > rows[idx + 1]["start"]):
                    self.results.ptText.appendHtml(
                        (
                            f"The events overlap for subject <b>{subject}</b> in the observation <b>{obs_id}</b>. "
                            "It is not possible to create the Praat TextGrid file."
                        )
                    )
                    QApplication.processEvents()

                    next_obs = True
                    break

                count += 1

                if (idx + 1 < len(rows)) and (rows[idx + 1]["start"] - dec("0.001") <= row["stop"] < rows[idx + 1]["start"]):
                    xmax = rows[idx + 1]["start"]
                else:
                    xmax = row["stop"]

                out += interval_template.format(count=count, name=row["code"], xmin=row["start"], xmax=xmax)

                # check if no behavior
                if (idx + 1 < len(rows)) and (row["stop"] < rows[idx + 1]["start"] - dec("0.001")):
                    count += 1
                    out += interval_template.format(
                        count=count,
                        name="null",
                        xmin=row["stop"],
                        xmax=rows[idx + 1]["start"],
                    )

            if next_obs:
                break

            # check if last event ends at the end of media file
            if rows[-1]["stop"] < max_time:
                count += 1
                out += interval_template.format(count=count, name="null", xmin=rows[-1]["stop"], xmax=max_time)

            # add info
            subject_index += 1
            out = out.format(
                subject_index=subject_index,
                subject=subject,
                intervalsSize=count,
                intervalsMin=intervalsMin,
                intervalsMax=intervalsMax,
            )

            # POINT events
            cursor.execute(
                (
                    "SELECT start, behavior FROM aggregated_events "
                    "WHERE observation = ? AND subject = ? AND type = 'POINT' ORDER BY start"
                ),
                (obs_id, subject),
            )

            rows = [{"start": util.float2decimal(r["start"]), "code": r["behavior"]} for r in cursor.fetchall()]
            if not rows:
                continue

            out += point_subject_header

            count = 0

            for idx, row in enumerate(rows):
                count += 1
                out += point_template.format(count=count, mark=row["code"], number=row["start"])

            # add info
            subject_index += 1
            out = out.format(
                subject_index=subject_index,
                subject=subject,
                intervalsSize=count,
                intervalsMin=intervalsMin,
                intervalsMax=intervalsMax,
            )

        if next_obs:
            continue

        # check if file already exists
        if mem_command != cfg.OVERWRITE_ALL and pl.Path(f"{pl.Path(export_dir) / util.safeFileName(obs_id)}.textGrid").is_file():
            if mem_command == cfg.SKIP_ALL:
                continue
            mem_command = dialog.MessageDialog(
                cfg.programName,
                f"The file <b>{pl.Path(export_dir) / util.safeFileName(obs_id)}.textGrid</b> already exists.",
                [cfg.OVERWRITE, cfg.OVERWRITE_ALL, cfg.SKIP, cfg.SKIP_ALL, cfg.CANCEL],
            )
            if mem_command == cfg.CANCEL:
                return
            if mem_command in (cfg.SKIP, cfg.SKIP_ALL):
                continue

        try:
            with open(f"{pl.Path(export_dir) / util.safeFileName(obs_id)}.textGrid", "w") as f:
                f.write(out)
            file_count += 1
            self.results.ptText.appendHtml(f"File {pl.Path(export_dir) / util.safeFileName(obs_id)}.textGrid was created.")
            QApplication.processEvents()
        except Exception:
            self.results.ptText.appendHtml(f"The file {pl.Path(export_dir) / util.safeFileName(obs_id)}.textGrid can not be created.")
            QApplication.processEvents()

    self.results.ptText.appendHtml(f"Done.  {file_count} file(s) were created in {export_dir}.")
    QApplication.processEvents()
