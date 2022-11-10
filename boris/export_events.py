"""
BORIS
Behavioral Observation Research Interactive Software
Copyright 2012-2022 Olivier Friard

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

from PyQt5.QtWidgets import QFileDialog, QMessageBox, QInputDialog


def export_events_as_behavioral_sequences(self, separated_subjects=False, timed=False):
    """
    export events from selected observations by subject as behavioral sequences (plain text file)
    behaviors are separated by character specified in self.behav_seq_separator (usually pipe |)
    for use with Behatrix (see http://www.boris.unito.it/pages/behatrix)

    Args:
        separated_subjects (bool):
        timed (bool):
    """

    # ask user for observations to analyze
    _, selected_observations = select_observations.select_observations(
        self.pj, cfg.MULTIPLE, "Select observations to export as behavioral sequences"
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

    start_coding, end_coding, _ = observation_operations.coding_time(self.pj[cfg.OBSERVATIONS], selected_observations)

    parameters = select_subj_behav.choose_obs_subj_behav_category(
        self,
        selected_observations,
        start_coding=start_coding,
        end_coding=end_coding,
        flagShowIncludeModifiers=True,
        flagShowExcludeBehaviorsWoEvents=False,
    )

    if not parameters[cfg.SELECTED_SUBJECTS] or not parameters[cfg.SELECTED_BEHAVIORS]:
        return

    fn = QFileDialog().getSaveFileName(
        self, "Export events as behavioral sequences", "", "Text files (*.txt);;All files (*)"
    )
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


def export_tabular_events(self, mode: str = "tabular"):
    """
    export events from selected observations in various formats: TSV, CSV, ODS, XLSX, XLS, HTML

    Args:
        mode (str): export mode: must be ["tabular", "jwatcher"]
    """

    # ask user observations to analyze
    _, selected_observations = select_observations.select_observations(
        self.pj, cfg.MULTIPLE, windows_title="Select observations for exporting events"
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

    max_obs_length, selectedObsTotalMediaLength = observation_operations.observation_length(
        self.pj, selected_observations
    )

    start_coding, end_coding, _ = observation_operations.coding_time(self.pj[cfg.OBSERVATIONS], selected_observations)

    parameters = select_subj_behav.choose_obs_subj_behav_category(
        self,
        selected_observations,
        start_coding=start_coding,
        end_coding=end_coding,
        maxTime=max_obs_length if len(selected_observations) > 1 else selectedObsTotalMediaLength,
        flagShowIncludeModifiers=False,
        flagShowExcludeBehaviorsWoEvents=False,
    )

    if not parameters[cfg.SELECTED_SUBJECTS] or not parameters[cfg.SELECTED_BEHAVIORS]:
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
                        dialog.MessageDialog(
                            cfg.programName, f"The file {file_name} already exists.", [cfg.CANCEL, cfg.OVERWRITE]
                        )
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
    for obsId in selected_observations:
        if len(selected_observations) > 1 or mode == "jwatcher":
            file_name = f"{pl.Path(exportDir) / util.safeFileName(obsId)}.{output_format}"
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
            export_function = export_observation.export_tabular_events
        if mode == "jwatcher":
            export_function = export_observation.export_events_jwatcher

        r, msg = export_function(
            parameters, obsId, self.pj[cfg.OBSERVATIONS][obsId], self.pj[cfg.ETHOGRAM], file_name, output_format
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
            "Total length": float,
            "FPS": float,
        }
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
        """
        max_modif_number = max(
            [
                len(self.pj[cfg.ETHOGRAM][idx][cfg.MODIFIERS])
                for idx in self.pj[cfg.ETHOGRAM]
                if self.pj[cfg.ETHOGRAM][idx][cfg.BEHAVIOR_CODE] in parameters[cfg.SELECTED_BEHAVIORS]
            ]
        )
        """

        for i in range(max_modif_number):
            fields_type_dict[f"Modifier #{i + 1}"] = str

        fields_type_dict.update(
            {
                "Behavior type": str,
                "Start (s)": float,
                "Stop (s)": float,
                "Duration (s)": float,
                "Image index start": float,  # add image index and image file path to header
                "Image index stop": float,
                "Image file path start": str,
                "Image file path stop": str,
                "Comment start": str,
                "Comment stop": str,
            }
        )

        return fields_type_dict

    _, selected_observations = select_observations.select_observations(
        self.pj, cfg.MULTIPLE, "Select observations for exporting events"
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

    max_obs_length, selectedObsTotalMediaLength = observation_operations.observation_length(
        self.pj, selected_observations
    )

    logging.debug(f"{max_obs_length=} {selectedObsTotalMediaLength=}")

    if max_obs_length == dec(-1):  # media length not available, user choose to not use events
        QMessageBox.warning(
            None,
            cfg.programName,
            ("The duration of one or more observation is not available"),
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
        maxTime=max_obs_length if len(selected_observations) > 1 else selectedObsTotalMediaLength,
        flagShowIncludeModifiers=False,
        flagShowExcludeBehaviorsWoEvents=False,
    )

    if not parameters[cfg.SELECTED_SUBJECTS] or not parameters[cfg.SELECTED_BEHAVIORS]:
        return

    # check for grouping results
    flag_group = True
    if len(selected_observations) > 1:
        flag_group = (
            dialog.MessageDialog(
                cfg.programName, "Group events from selected observations in one file?", [cfg.YES, cfg.NO]
            )
            == cfg.YES
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
                if (
                    dialog.MessageDialog(
                        cfg.programName, f"The file {fileName} already exists.", [cfg.CANCEL, cfg.OVERWRITE]
                    )
                    == cfg.CANCEL
                ):
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

    if outputFormat == "sql":
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

    tot_max_modifiers = 0
    for obs_id in selected_observations:
        _, max_modifiers = export_observation.export_aggregated_events(self.pj, parameters, obs_id)
        tot_max_modifiers = max(tot_max_modifiers, max_modifiers)

    # print(f"{tot_max_modifiers=}")

    data_grouped_obs = tablib.Dataset()
    # sort by start time
    start_idx = -9  # TODO: improve!
    stop_idx = -8
    obs_id_idx = 0

    mem_command = ""  # remember user choice when file already exists
    for obs_id in selected_observations:
        # print(f"{obs_id=}")
        data, max_modifiers = export_observation.export_aggregated_events(self.pj, parameters, obs_id)
        # print(f"{max_modifiers=}")

        if (not flag_group) and (outputFormat not in ["sds", "tbs"]):
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
                if mem_command in [cfg.SKIP, cfg.SKIP_ALL]:
                    continue

            data_single_obs = tablib.Dataset(
                *sorted(list(data), key=lambda x: (x[obs_id_idx], float(x[start_idx]))),
                headers=list(fields_type(max_modifiers).keys()),
            )
            data_single_obs.title = obs_id

            r, msg = export_observation.dataset_write(data_single_obs, fileName, outputFormat, dtype=fields_type)
            if not r:
                QMessageBox.warning(
                    None, cfg.programName, msg, QMessageBox.Ok | QMessageBox.Default, QMessageBox.NoButton
                )

        if max_modifiers < tot_max_modifiers:
            for i in range(tot_max_modifiers - max_modifiers):
                data.insert_col(
                    14,
                    col=[""] * (len(list(data))),
                    header=f"Modif #{i}",
                )
        data_grouped_obs.extend(data)

    data_grouped_obs_sorted = tablib.Dataset(
        *sorted(list(data_grouped_obs), key=lambda x: (x[obs_id_idx], float(x[start_idx]))),
        headers=list(fields_type(tot_max_modifiers).keys()),
    )
    data.title = "Aggregated events"

    # TODO: finish
    if outputFormat == "tbs":  # Timed behavioral sequences
        out = ""
        for obsId in selected_observations:
            # observation id
            out += f"# {obsId}\n"

            for event in list(data):
                if event[0] == obsId:
                    behavior = event[-8]
                    # replace various char by _
                    for char in [" ", "-", "/"]:
                        behavior = behavior.replace(char, "_")
                    subject = event[-9]
                    # replace various char by _
                    for char in [" ", "-", "/"]:
                        subject = subject.replace(char, "_")
                    event_start = f"{float(event[start_idx]):.3f}"  # start event (from end for independent variables)
                    if not event[stop_idx]:  # stop event (from end)
                        event_stop = f"{float(event[start_idx]) + 0.001:.3f}"
                    else:
                        event_stop = f"{float(event[stop_idx]):.3f}"

                    bs_timed = [f"{subject}_{behavior}"] * round((float(event_stop) - float(event_start)) * 100)
                    out += "|".join(bs_timed)

            out += "\n"

            if not flag_group:
                fileName = f"{pl.Path(exportDir) / util.safeFileName(obsId)}.{outputFormat}"
                with open(fileName, "wb") as f:
                    f.write(str.encode(out))
                out = ""

        if flag_group:
            with open(fileName, "wb") as f:
                f.write(str.encode(out))
        return

    if outputFormat == "sds":  # SDIS format
        out = ("% SDIS file created by BORIS (www.boris.unito.it) " "at {}\nTimed <seconds>;\n").format(
            util.datetime_iso8601(dt.datetime.now())
        )
        for obsId in selected_observations:
            # observation id
            out += "\n<{}>\n".format(obsId)

            for event in list(data):
                if event[0] == obsId:
                    behavior = event[-8]
                    # replace various char by _
                    for char in [" ", "-", "/"]:
                        behavior = behavior.replace(char, "_")
                    subject = event[-9]
                    # replace various char by _
                    for char in [" ", "-", "/"]:
                        subject = subject.replace(char, "_")
                    event_start = "{0:.3f}".format(
                        float(event[start_idx])
                    )  # start event (from end for independent variables)
                    if not event[stop_idx]:  # stop event (from end)
                        event_stop = "{0:.3f}".format(float(event[start_idx]) + 0.001)
                    else:
                        event_stop = "{0:.3f}".format(float(event[stop_idx]))
                    out += f"{subject}_{behavior},{event_start}-{event_stop} "

            out += "/\n\n"
            if not flag_group:
                """
                fileName = str(pathlib.Path(pathlib.Path(exportDir) / safeFileName(obsId)).with suffix("." + outputFormat))
                """
                fileName = f"{pl.Path(exportDir) / util.safeFileName(obsId)}.{outputFormat}"
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
        r, msg = export_observation.dataset_write(data_grouped_obs_sorted, fileName, outputFormat, dtype=fields_type)
        if not r:
            QMessageBox.warning(None, cfg.programName, msg, QMessageBox.Ok | QMessageBox.Default, QMessageBox.NoButton)


def export_events_as_textgrid(self):
    """
    export state events as Praat textgrid
    """

    _, selected_observations = select_observations.select_observations(self.pj, mode=cfg.MULTIPLE, windows_title="")

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
    )

    if not parameters[cfg.SELECTED_SUBJECTS] or not parameters[cfg.SELECTED_BEHAVIORS]:
        return

    exportDir = QFileDialog(self).getExistingDirectory(
        self, "Export events as Praat TextGrid", os.path.expanduser("~"), options=QFileDialog(self).ShowDirsOnly
    )
    if not exportDir:
        return

    mem_command = ""

    # see https://www.fon.hum.uva.nl/praat/manual/TextGrid_file_formats.html

    interval_subject_header = (
        "    item [{subject_index}]:\n"
        '        class = "IntervalTier"\n'
        '        name = "{subject}"\n'
        "        xmin = {intervalsMin}\n"
        "        xmax = {intervalsMax}\n"
        "        intervals: size = {intervalsSize}\n"
    )

    interval_template = (
        "        intervals [{count}]:\n"
        "            xmin = {xmin}\n"
        "            xmax = {xmax}\n"
        '            text = "{name}"\n'
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

    for obs_id in selected_observations:

        total_media_duration = round(
            observation_operations.observation_total_length(self.pj[cfg.OBSERVATIONS][obs_id]), 3
        )

        cursor = db_functions.load_events_in_db(
            self.pj,
            parameters[cfg.SELECTED_SUBJECTS],
            selected_observations,
            parameters[cfg.SELECTED_BEHAVIORS],
            time_interval=cfg.TIME_FULL_OBS,
        )

        cursor.execute(
            (
                "SELECT COUNT(DISTINCT subject) FROM events "
                "WHERE observation = ? AND subject IN ({}) AND type = 'STATE' ".format(
                    ",".join(["?"] * len(parameters[cfg.SELECTED_SUBJECTS]))
                )
            ),
            [obs_id] + parameters[cfg.SELECTED_SUBJECTS],
        )

        subjectsNum = int(list(cursor.fetchall())[0][0])

        subjectsMin, subjectsMax = 0, total_media_duration

        out = (
            'File type = "ooTextFile"\n'
            'Object class = "TextGrid"\n'
            "\n"
            f"xmin = {subjectsMin}\n"
            f"xmax = {subjectsMax}\n"
            "tiers? <exists>\n"
            f"size = {subjectsNum}\n"
            "item []:\n"
        )

        subject_index = 0
        for subject in parameters[cfg.SELECTED_SUBJECTS]:
            if subject not in [x[cfg.EVENT_SUBJECT_FIELD_IDX] for x in self.pj[cfg.OBSERVATIONS][obs_id][cfg.EVENTS]]:
                continue

            intervalsMin, intervalsMax = 0, total_media_duration

            # STATE events
            cursor.execute(
                (
                    "SELECT occurence, code FROM events "
                    "WHERE observation = ? AND subject = ? AND type = 'STATE' ORDER BY occurence"
                ),
                (obs_id, subject),
            )

            rows = [{"occurence": util.float2decimal(r["occurence"]), "code": r["code"]} for r in cursor.fetchall()]
            if not rows:
                continue

            out += interval_subject_header

            count = 0

            # check if 1st behavior starts at the beginning

            if rows[0]["occurence"] > 0:
                count += 1
                out += interval_template.format(count=count, name="null", xmin=0.0, xmax=rows[0]["occurence"])

            for idx, row in enumerate(rows):
                if idx % 2 == 0:

                    # check if events not interlacced
                    if row["code"] != rows[idx + 1]["code"]:
                        QMessageBox.critical(
                            None,
                            cfg.programName,
                            "The events are interlaced. It is not possible to produce the Praat TextGrid file",
                            QMessageBox.Ok | QMessageBox.Default,
                            QMessageBox.NoButton,
                        )
                        return

                    count += 1
                    out += interval_template.format(
                        count=count, name=row["code"], xmin=row["occurence"], xmax=rows[idx + 1]["occurence"]
                    )

                    # check if difference is > 0.001
                    if len(rows) > idx + 2:
                        if rows[idx + 2]["occurence"] - rows[idx + 1]["occurence"] > 0.001:

                            out += interval_template.format(
                                count=count + 1,
                                name="null",
                                xmin=rows[idx + 1]["occurence"],
                                xmax=rows[idx + 2]["occurence"],
                            )
                            count += 1
                        else:
                            rows[idx + 2]["occurence"] = rows[idx + 1]["occurence"]

            # check if last event ends at the end of media file
            if rows[-1]["occurence"] < observation_operations.observation_total_length(
                self.pj[cfg.OBSERVATIONS][obs_id]
            ):
                count += 1
                out += interval_template.format(
                    count=count, name="null", xmin=rows[-1]["occurence"], xmax=total_media_duration
                )

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
                    "SELECT occurence, code FROM events "
                    "WHERE observation = ? AND subject = ? AND type = 'POINT' ORDER BY occurence"
                ),
                (obs_id, subject),
            )

            rows = [{"occurence": util.float2decimal(r["occurence"]), "code": r["code"]} for r in cursor.fetchall()]
            if not rows:
                continue

            out += point_subject_header

            count = 0

            for idx, row in enumerate(rows):

                count += 1
                out += point_template.format(count=count, mark=row["code"], number=row["occurence"])

            # add info
            subject_index += 1
            out = out.format(
                subject_index=subject_index,
                subject=subject,
                intervalsSize=count,
                intervalsMin=intervalsMin,
                intervalsMax=intervalsMax,
            )

        # check if file already exists
        if (
            mem_command != cfg.OVERWRITE_ALL
            and pl.Path(f"{pl.Path(exportDir) / util.safeFileName(obs_id)}.textGrid").is_file()
        ):
            if mem_command == cfg.SKIP_ALL:
                continue
            mem_command = dialog.MessageDialog(
                cfg.programName,
                f"The file <b>{pl.Path(exportDir) / util.safeFileName(obs_id)}.textGrid</b> already exists.",
                [cfg.OVERWRITE, cfg.OVERWRITE_ALL, cfg.SKIP, cfg.SKIP_ALL, cfg.CANCEL],
            )
            if mem_command == cfg.CANCEL:
                return
            if mem_command in [cfg.SKIP, cfg.SKIP_ALL]:
                continue

        try:
            with open(f"{pl.Path(exportDir) / util.safeFileName(obs_id)}.textGrid", "w") as f:
                f.write(out)

        except Exception:
            QMessageBox.critical(self, cfg.programName, "The file can not be saved")
