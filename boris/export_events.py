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

import datetime
import logging
import os
import re
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

    parameters = select_subj_behav.choose_obs_subj_behav_category(
        self,
        selected_observations,
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
    _, selectedObservations = select_observations.select_observations(
        self.pj, cfg.MULTIPLE, windows_title="Select observations for exporting events"
    )

    if not selectedObservations:
        return

    out = ""
    # check if coded behaviors are defined in ethogram
    ethogram_behavior_codes = {self.pj[cfg.ETHOGRAM][idx][cfg.BEHAVIOR_CODE] for idx in self.pj[cfg.ETHOGRAM]}
    behaviors_not_defined = []
    out = ""  # will contain the output
    for obs_id in selectedObservations:
        for event in self.pj[cfg.OBSERVATIONS][obs_id][cfg.EVENTS]:
            if event[cfg.EVENT_BEHAVIOR_FIELD_IDX] not in ethogram_behavior_codes:
                behaviors_not_defined.append(event[cfg.EVENT_BEHAVIOR_FIELD_IDX])
    if set(sorted(behaviors_not_defined)):
        out += (
            "The following behaviors are not defined in the ethogram: "
            f"<b>{', '.join(set(sorted(behaviors_not_defined)))}</b><br><br>"
        )

    # check if state events are paired
    not_paired_obs_list = []
    for obsId in selectedObservations:
        r, msg = project_functions.check_state_events_obs(
            obsId, self.pj[cfg.ETHOGRAM], self.pj[cfg.OBSERVATIONS][obsId], self.timeFormat
        )

        if not r:
            out += f"Observation: <strong>{obsId}</strong><br>{msg}<br>"
            not_paired_obs_list.append(obsId)

    if out:
        out = f"Some observations have UNPAIRED state events<br><br>{out}"
        self.results = dialog.Results_dialog()
        self.results.setWindowTitle(f"{cfg.programName} - Check selected observations")
        self.results.ptText.setReadOnly(True)
        self.results.ptText.appendHtml(out)
        self.results.pbSave.setVisible(False)
        self.results.pbCancel.setVisible(True)

        if not self.results.exec_():
            return

    parameters = select_subj_behav.choose_obs_subj_behav_category(
        self,
        selectedObservations,
        flagShowIncludeModifiers=False,
        flagShowExcludeBehaviorsWoEvents=False,
    )

    if not parameters["selected subjects"] or not parameters["selected behaviors"]:
        return

    if mode == "tabular":
        if len(selectedObservations) > 1:  # choose directory for exporting observations

            items = (
                "Tab Separated Values (*.tsv)",
                "Comma separated values (*.csv)",
                "Open Document Spreadsheet (*.ods)",
                "Microsoft Excel Spreadsheet XLSX (*.xlsx)",
                "Legacy Microsoft Excel Spreadsheet XLS (*.xls)",
                "HTML (*.html)",
            )
            item, ok = QInputDialog.getItem(self, "Export events format", "Available formats", items, 0, False)
            if not ok:
                return
            outputFormat = re.sub(".* \(\*\.", "", item)[:-1]

            exportDir = QFileDialog().getExistingDirectory(
                self,
                "Choose a directory to export events",
                os.path.expanduser("~"),
                options=QFileDialog.ShowDirsOnly,
            )
            if not exportDir:
                return

        if len(selectedObservations) == 1:
            extended_file_formats = [
                "Tab Separated Values (*.tsv)",
                "Comma Separated Values (*.csv)",
                "Open Document Spreadsheet ODS (*.ods)",
                "Microsoft Excel Spreadsheet XLSX (*.xlsx)",
                "Legacy Microsoft Excel Spreadsheet XLS (*.xls)",
                "HTML (*.html)",
            ]
            file_formats = ["tsv", "csv", "ods", "xlsx", "xls", "html"]

            fileName, filter_ = QFileDialog().getSaveFileName(
                self, "Export events", "", ";;".join(extended_file_formats)
            )
            if not fileName:
                return

            outputFormat = file_formats[extended_file_formats.index(filter_)]
            if pl.Path(fileName).suffix != "." + outputFormat:
                fileName = str(pl.Path(fileName)) + "." + outputFormat
                # check if file with new extension already exists
                if pl.Path(fileName).is_file():
                    if (
                        dialog.MessageDialog(
                            cfg.programName, f"The file {fileName} already exists.", [cfg.CANCEL, cfg.OVERWRITE]
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

        outputFormat = "dat"

    mem_command = ""  # remember user choice when file already exists
    for obsId in selectedObservations:
        if len(selectedObservations) > 1 or mode == "jwatcher":
            fileName = f"{pl.Path(exportDir) / util.safeFileName(obsId)}.{outputFormat}"
            # check if file with new extension already exists
            if mem_command != "Overwrite all" and pl.Path(fileName).is_file():
                if mem_command == "Skip all":
                    continue
                mem_command = dialog.MessageDialog(
                    cfg.programName,
                    f"The file {fileName} already exists.",
                    [cfg.OVERWRITE, "Overwrite all", "Skip", "Skip all", cfg.CANCEL],
                )
                if mem_command == cfg.CANCEL:
                    return
                if mem_command in ["Skip", "Skip all"]:
                    continue

        if mode == "tabular":
            export_function = export_observation.export_events
        if mode == "jwatcher":
            export_function = export_observation.export_events_jwatcher

        r, msg = export_function(
            parameters, obsId, self.pj[cfg.OBSERVATIONS][obsId], self.pj[cfg.ETHOGRAM], fileName, outputFormat
        )

        if not r and msg:
            QMessageBox.critical(None, cfg.programName, msg, QMessageBox.Ok | QMessageBox.Default, QMessageBox.NoButton)


def export_aggregated_events(self):
    """
    export aggregated events.
    Formats can be SQL (sql), SDIS (sds) or Tabular format (tsv, csv, ods, xlsx, xls, html)
    """

    _, selectedObservations = select_observations.select_observations(
        self.pj, cfg.MULTIPLE, "Select observations for exporting events"
    )
    if not selectedObservations:
        return

    # check if coded behaviors are defined in ethogram
    if project_functions.check_coded_behaviors_in_obs_list(self.pj, selectedObservations):
        return

    # check if state events are paired
    not_ok, selectedObservations = project_functions.check_state_events(self.pj, selectedObservations)
    if not_ok or not selectedObservations:
        return

    max_obs_length, selectedObsTotalMediaLength = observation_operations.observation_length(
        self.pj, selectedObservations
    )

    logging.debug(f"max_obs_length:{max_obs_length}  selectedObsTotalMediaLength:{selectedObsTotalMediaLength}")

    if max_obs_length == dec(-1):  # media length not available, user choose to not use events
        QMessageBox.warning(
            None,
            cfg.programName,
            ("The duration of one or more observation is not available"),
            QMessageBox.Ok | QMessageBox.Default,
            QMessageBox.NoButton,
        )
        return

    parameters = select_subj_behav.choose_obs_subj_behav_category(
        self,
        selectedObservations,
        maxTime=max_obs_length if len(selectedObservations) > 1 else selectedObsTotalMediaLength,
        flagShowIncludeModifiers=False,
        flagShowExcludeBehaviorsWoEvents=False,
    )

    if not parameters[cfg.SELECTED_SUBJECTS] or not parameters[cfg.SELECTED_BEHAVIORS]:
        return

    # check for grouping results
    flag_group = True
    if len(selectedObservations) > 1:
        flag_group = (
            dialog.MessageDialog(
                cfg.programName, "Group events from selected observations in one file?", [cfg.YES, cfg.NO]
            )
            == cfg.YES
        )

    extended_file_formats = [
        "Tab Separated Values (*.tsv)",
        "Comma Separated Values (*.csv)",
        "Open Document Spreadsheet ODS (*.ods)",
        "Microsoft Excel Spreadsheet XLSX (*.xlsx)",
        "Legacy Microsoft Excel Spreadsheet XLS (*.xls)",
        "HTML (*.html)",
        "SDIS (*.sds)",
        "SQL dump file (*.sql)",
    ]

    if flag_group:
        file_formats = [
            "tsv",
            "csv",
            "ods",
            "xlsx",
            "xls",
            "html",
            "sds",
            "sql",
        ]  # must be in same order than extended_file_formats

        fileName, filter_ = QFileDialog().getSaveFileName(
            self, "Export aggregated events", "", ";;".join(extended_file_formats)
        )

        if not fileName:
            return

        outputFormat = file_formats[extended_file_formats.index(filter_)]
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

        items = (
            "Tab Separated Values (*.tsv)",
            "Comma Separated values (*.csv)",
            "Open Document Spreadsheet (*.ods)",
            "Microsoft Excel Spreadsheet XLSX (*.xlsx)",
            "Legacy Microsoft Excel Spreadsheet XLS (*.xls)",
            "HTML (*.html)",
            "SDIS (*.sds)",
            "Timed Behavioral Sequences (*.tbs)",
        )
        item, ok = QInputDialog.getItem(self, "Export events format", "Available formats", items, 0, False)
        if not ok:
            return
        outputFormat = re.sub(".* \(\*\.", "", item)[:-1]

        exportDir = QFileDialog().getExistingDirectory(
            self, "Choose a directory to export events", os.path.expanduser("~"), options=QFileDialog.ShowDirsOnly
        )
        if not exportDir:
            return

    if outputFormat == "sql":
        _, _, conn = db_functions.load_aggregated_events_in_db(
            self.pj, parameters[cfg.SELECTED_SUBJECTS], selectedObservations, parameters[cfg.SELECTED_BEHAVIORS]
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

    header = [
        "Observation id",
        "Observation date",
        "Description",
        "Observation type",
        "Source",
        "Total length",
        "FPS",
    ]
    if cfg.INDEPENDENT_VARIABLES in self.pj:
        for idx in util.sorted_keys(self.pj[cfg.INDEPENDENT_VARIABLES]):
            header.append(self.pj[cfg.INDEPENDENT_VARIABLES][idx]["label"])

    header.extend(["Subject", "Behavior", "Behavioral category"])
    header.extend(["Modifiers"])
    header.extend(["Behavior type", "Start (s)", "Stop (s)", "Duration (s)", "Comment start", "Comment stop"])

    data = tablib.Dataset()
    # sort by start time
    start_idx = -5
    stop_idx = -4

    mem_command = ""  # remember user choice when file already exists
    for obsId in selectedObservations:
        d = export_observation.export_aggregated_events(self.pj, parameters, obsId)
        data.extend(d)

        if not flag_group and outputFormat not in ["sds", "tbs"]:
            fileName = f"{pl.Path(exportDir) / util.safeFileName(obsId)}.{outputFormat}"
            # check if file with new extension already exists
            if mem_command != cfg.OVERWRITE_ALL and pl.Path(fileName).is_file():
                if mem_command == "Skip all":
                    continue
                mem_command = dialog.MessageDialog(
                    cfg.programName,
                    f"The file {fileName} already exists.",
                    [cfg.OVERWRITE, cfg.OVERWRITE_ALL, "Skip", "Skip all", cfg.CANCEL],
                )
                if mem_command == cfg.CANCEL:
                    return
                if mem_command in ["Skip" "Skip all"]:
                    continue

            data = tablib.Dataset(*sorted(list(data), key=lambda x: float(x[start_idx])), headers=header)
            data.title = obsId
            r, msg = export_observation.dataset_write(data, fileName, outputFormat)
            if not r:
                QMessageBox.warning(
                    None, cfg.programName, msg, QMessageBox.Ok | QMessageBox.Default, QMessageBox.NoButton
                )
            data = tablib.Dataset()

    data = tablib.Dataset(*sorted(list(data), key=lambda x: float(x[start_idx])), headers=header)
    data.title = "Aggregated events"

    # TODO: finish
    if outputFormat == "tbs":  # Timed behavioral sequences
        out = ""
        for obsId in selectedObservations:
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
            util.datetime_iso8601(datetime.datetime.now())
        )
        for obsId in selectedObservations:
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
                    f"at {util.datetime_iso8601(datetime.datetime.now())}\nTimed <seconds>;\n"
                )

        if flag_group:
            with open(fileName, "wb") as f:
                f.write(str.encode(out))
        return

    if flag_group:
        r, msg = export_observation.dataset_write(data, fileName, outputFormat)
        if not r:
            QMessageBox.warning(None, cfg.programName, msg, QMessageBox.Ok | QMessageBox.Default, QMessageBox.NoButton)


def export_state_events_as_textgrid(self):
    """
    export state events as Praat textgrid
    """

    _, selectedObservations = select_observations.select_observations(self.pj, mode=cfg.MULTIPLE, windows_title="")

    if not selectedObservations:
        return

    plot_parameters = select_subj_behav.choose_obs_subj_behav_category(
        self,
        selectedObservations,
        flagShowIncludeModifiers=False,
        flagShowExcludeBehaviorsWoEvents=False,
    )

    if not plot_parameters[cfg.SELECTED_SUBJECTS] or not plot_parameters[cfg.SELECTED_BEHAVIORS]:
        return

    # check if state events are paired
    out = ""
    not_paired_obs_list = []
    for obsId in selectedObservations:
        r, msg = project_functions.check_state_events_obs(
            obsId, self.pj[cfg.ETHOGRAM], self.pj[cfg.OBSERVATIONS][obsId], self.timeFormat
        )

        if not r:
            # check if unpaired behavior is included in behaviors to extract
            for behav in plot_parameters[cfg.SELECTED_BEHAVIORS]:
                if f"behavior <b>{behav}</b>" in msg:
                    out += f"Observation: <strong>{obsId}</strong><br>{msg}<br>"
                    not_paired_obs_list.append(obsId)

    if out:
        out = "The observations with UNPAIRED state events will be removed from the analysis<br><br>" + out
        results = dialog.Results_dialog()
        results.setWindowTitle(f"{cfg.programName} - Check selected observations and selected behaviors")
        results.ptText.setReadOnly(True)
        results.ptText.appendHtml(out)
        results.pbSave.setVisible(False)
        results.pbCancel.setVisible(True)

        if not results.exec_():
            return

    # remove observations with unpaired state events
    selectedObservations = [x for x in selectedObservations if x not in not_paired_obs_list]
    if not selectedObservations:
        return

    exportDir = QFileDialog(self).getExistingDirectory(
        self, "Export events as Praat TextGrid", os.path.expanduser("~"), options=QFileDialog(self).ShowDirsOnly
    )
    if not exportDir:
        return

    mem_command = ""
    for obsId in selectedObservations:

        subjectheader = (
            "    item [{subjectIdx}]:\n"
            '        class = "IntervalTier"\n'
            '        name = "{subject}"\n'
            "        xmin = {intervalsMin}\n"
            "        xmax = {intervalsMax}\n"
            "        intervals: size = {intervalsSize}\n"
        )

        template = (
            "        intervals [{count}]:\n"
            "            xmin = {xmin}\n"
            "            xmax = {xmax}\n"
            '            text = "{name}"\n'
        )

        flagUnpairedEventFound = False

        totalMediaDuration = round(project_functions.observation_total_length(self.pj[cfg.OBSERVATIONS][obsId]), 3)

        cursor = db_functions.load_events_in_db(
            self.pj,
            plot_parameters[cfg.SELECTED_SUBJECTS],
            selectedObservations,
            plot_parameters[cfg.SELECTED_BEHAVIORS],
            time_interval=cfg.TIME_FULL_OBS,
        )

        cursor.execute(
            (
                "SELECT count(distinct subject) FROM events "
                "WHERE observation = ? AND subject IN ({}) AND type = 'STATE' ".format(
                    ",".join(["?"] * len(plot_parameters[cfg.SELECTED_SUBJECTS]))
                )
            ),
            [obsId] + plot_parameters[cfg.SELECTED_SUBJECTS],
        )

        subjectsNum = int(list(cursor.fetchall())[0][0])

        subjectsMin, subjectsMax = 0, totalMediaDuration

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

        subjectIdx = 0
        for subject in plot_parameters[cfg.SELECTED_SUBJECTS]:
            if subject not in [x[cfg.EVENT_SUBJECT_FIELD_IDX] for x in self.pj[cfg.OBSERVATIONS][obsId][cfg.EVENTS]]:
                continue

            subjectIdx += 1

            cursor.execute(
                "SELECT count(*) FROM events WHERE observation = ? AND subject = ? AND type = 'STATE' ",
                (obsId, subject),
            )
            intervalsSize = int(list(cursor.fetchall())[0][0] / 2)

            intervalsMin, intervalsMax = 0, totalMediaDuration

            out += subjectheader

            cursor.execute(
                (
                    "SELECT occurence, code FROM events "
                    "WHERE observation = ? AND subject = ? AND type = 'STATE' order by occurence"
                ),
                (obsId, subject),
            )

            rows = [{"occurence": util.float2decimal(r["occurence"]), "code": r["code"]} for r in cursor.fetchall()]
            if not rows:
                continue

            count = 0

            # check if 1st behavior starts at the beginning

            if rows[0]["occurence"] > 0:
                count += 1
                out += template.format(count=count, name="null", xmin=0.0, xmax=rows[0]["occurence"])

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
                    out += template.format(
                        count=count, name=row["code"], xmin=row["occurence"], xmax=rows[idx + 1]["occurence"]
                    )

                    # check if difference is > 0.001
                    if len(rows) > idx + 2:
                        if rows[idx + 2]["occurence"] - rows[idx + 1]["occurence"] > 0.001:

                            out += template.format(
                                count=count + 1,
                                name="null",
                                xmin=rows[idx + 1]["occurence"],
                                xmax=rows[idx + 2]["occurence"],
                            )
                            count += 1
                        else:
                            rows[idx + 2]["occurence"] = rows[idx + 1]["occurence"]

            # check if last event ends at the end of media file
            if rows[-1]["occurence"] < project_functions.observation_total_length(self.pj[cfg.OBSERVATIONS][obsId]):
                count += 1
                out += template.format(count=count, name="null", xmin=rows[-1]["occurence"], xmax=totalMediaDuration)

            # add info
            out = out.format(
                subjectIdx=subjectIdx,
                subject=subject,
                intervalsSize=count,
                intervalsMin=intervalsMin,
                intervalsMax=intervalsMax,
            )

        # check if file already exists
        if (
            mem_command != cfg.OVERWRITE_ALL
            and pl.Path(f"{pl.Path(exportDir) / util.safeFileName(obsId)}.textGrid").is_file()
        ):
            if mem_command == "Skip all":
                continue
            mem_command = dialog.MessageDialog(
                cfg.programName,
                f"The file <b>{pl.Path(exportDir) / util.safeFileName(obsId)}.textGrid</b> already exists.",
                [cfg.OVERWRITE, cfg.OVERWRITE_ALL, "Skip", "Skip all", cfg.CANCEL],
            )
            if mem_command == cfg.CANCEL:
                return
            if mem_command in ["Skip", "Skip all"]:
                continue

        try:
            with open(f"{pl.Path(exportDir) / util.safeFileName(obsId)}.textGrid", "w") as f:
                f.write(out)

            if flagUnpairedEventFound:
                QMessageBox.warning(
                    self,
                    cfg.programName,
                    "Some state events are not paired. They were excluded from export",
                    QMessageBox.Ok | QMessageBox.Default,
                    QMessageBox.NoButton,
                )

        except Exception:
            QMessageBox.critical(self, cfg.programName, "The file can not be saved")
