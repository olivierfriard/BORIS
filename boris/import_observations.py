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

import json
import datetime
from pathlib import Path
import pandas as pd

from PySide6.QtWidgets import (
    QMessageBox,
    QFileDialog,
)

from . import config as cfg
from . import dialog
from . import utilities as util


def load_observations_from_boris_project(self, project_file_path: str):
    """
    import observations from a BORIS project file
    """

    if self.projectFileName and project_file_path == self.projectFileName:
        QMessageBox.critical(
            None,
            cfg.programName,
            "This project is already open",
            QMessageBox.Ok | QMessageBox.Default,
            QMessageBox.NoButton,
        )
        return

    try:
        fromProject = json.loads(open(project_file_path, "r").read())
    except Exception:
        QMessageBox.critical(self, cfg.programName, "This project file seems corrupted")
        return

    # transform time to decimal
    fromProject = util.convert_time_to_decimal(fromProject)  # function in utilities.py

    dbc = dialog.ChooseObservationsToImport("Choose the observations to import:", sorted(list(fromProject[cfg.OBSERVATIONS].keys())))

    if not dbc.exec_():
        return
    selected_observations = dbc.get_selected_observations()
    if selected_observations:
        flagImported = False

        # set of behaviors in current projet ethogram
        behav_set = set([self.pj[cfg.ETHOGRAM][idx][cfg.BEHAVIOR_CODE] for idx in self.pj[cfg.ETHOGRAM]])

        # set of subjects in current projet
        subjects_set = set([self.pj[cfg.SUBJECTS][idx][cfg.SUBJECT_NAME] for idx in self.pj[cfg.SUBJECTS]])

        for obs_id in selected_observations:
            # check if behaviors are in current project ethogram
            new_behav_set = set(
                [
                    event[cfg.EVENT_BEHAVIOR_FIELD_IDX]
                    for event in fromProject[cfg.OBSERVATIONS][obs_id][cfg.EVENTS]
                    if event[cfg.EVENT_BEHAVIOR_FIELD_IDX] not in behav_set
                ]
            )
            if new_behav_set:
                diag_result = dialog.MessageDialog(
                    cfg.programName,
                    (f"Some coded behaviors in <b>{obs_id}</b> are " f"not defined in the ethogram:<br><b>{', '.join(new_behav_set)}</b>"),
                    ["Interrupt import", "Skip observation", "Import observation"],
                )
                if diag_result == "Interrupt import":
                    return
                if diag_result == "Skip observation":
                    continue

            # check if subjects are in current project
            new_subject_set = set(
                [
                    event[cfg.EVENT_SUBJECT_FIELD_IDX]
                    for event in fromProject[cfg.OBSERVATIONS][obs_id][cfg.EVENTS]
                    if event[cfg.EVENT_SUBJECT_FIELD_IDX] not in subjects_set
                ]
            )
            if new_subject_set and new_subject_set != {""}:
                diag_result = dialog.MessageDialog(
                    cfg.programName,
                    (f"Some coded subjects in <b>{obs_id}</b> are not defined in the project:<br>" f"<b>{', '.join(new_subject_set)}</b>"),
                    ["Interrupt import", "Skip observation", "Import observation"],
                )

                if diag_result == "Interrupt import":
                    return

                if diag_result == "Skip observation":
                    continue

            if obs_id in self.pj[cfg.OBSERVATIONS].keys():
                diag_result = dialog.MessageDialog(
                    cfg.programName,
                    (f"The observation <b>{obs_id}</b>" "already exists in the current project.<br>"),
                    ["Interrupt import", "Skip observation", "Rename observation"],
                )
                if diag_result == "Interrupt import":
                    return

                if diag_result == "Rename observation":
                    self.pj[cfg.OBSERVATIONS][f"{obs_id} (imported at {util.datetime_iso8601(datetime.datetime.now())})"] = dict(
                        fromProject[cfg.OBSERVATIONS][obs_id]
                    )
                    flagImported = True
            else:
                self.pj[cfg.OBSERVATIONS][obs_id] = dict(fromProject[cfg.OBSERVATIONS][obs_id])
                flagImported = True

        if flagImported:
            QMessageBox.information(self, cfg.programName, "Observations imported successfully")
            self.project_changed()


def load_observations_from_spreadsheet(self, project_file_path: str):
    """
    import observations from a spreadsheet file
    """

    if Path(project_file_path).suffix.upper() == ".XLSX":
        engine = "openpyxl"
    elif Path(project_file_path).suffix.upper() == ".ODS":
        engine = "odf"
    else:
        QMessageBox.warning(
            None,
            cfg.programName,
            ("The type of file was not recognized. Must be Microsoft-Excel XLSX format or OpenDocument ODS"),
            QMessageBox.Ok | QMessageBox.Default,
            QMessageBox.NoButton,
        )
        return

    try:
        df = pd.read_excel(project_file_path, sheet_name=0, engine=engine)
    except Exception:
        QMessageBox.warning(
            None,
            cfg.programName,
            ("The type of file was not recognized. Must be Microsoft-Excel XLSX format or OpenDocument ODS"),
            QMessageBox.Ok | QMessageBox.Default,
            QMessageBox.NoButton,
        )
        return

    expected_labels: list = ["time", "subject", "code", "modifier", "comment"]

    df.columns = df.columns.str.upper()

    for column in expected_labels:
        if column.upper() not in list(df.columns):
            QMessageBox.warning(
                None,
                cfg.programName,
                (
                    f"The {column} column was not found in the file header.<br>"
                    "For information the current file header contains the following labels:<br>"
                    f"{'<br>'.join(['<b>' + util.replace_leading_trailing_chars(x, ' ', '&#9608;') + '</b>' for x in df.columns])}<br>"
                    "<br>"
                    "The first row of the spreadsheet must contain the following labels:<br>"
                    f"{'<br>'.join(['<b>' + x + '</b>' for x in expected_labels])}<br>"
                    "<br>The order is not mandatory."
                ),
                QMessageBox.Ok | QMessageBox.Default,
                QMessageBox.NoButton,
            )
            return 1
    event: dict = {}
    events: list = []
    for _, row in df.iterrows():
        for label in expected_labels:
            event[label] = row[label.upper()] if str(row[label.upper()]) != "nan" else ""
        events.append([event["time"], event["subject"], event["code"], event["modifier"], event["comment"]])

    if events:
        self.pj[cfg.OBSERVATIONS][self.observationId]["events"].extend(events)
        self.load_tw_events(self.observationId)

        QMessageBox.information(self, cfg.programName, "Observations imported successfully")
        self.project_changed()


def import_observations(self):
    """
    import observations from project file
    """

    file_name, _ = QFileDialog().getOpenFileName(
        None, "Choose a file", "", "BORIS project files (*.boris);;Spreadsheet files (*.ods *.xlsx *);;All files (*)"
    )

    if not file_name:
        return

    if Path(file_name).suffix == ".boris":
        load_observations_from_boris_project(self, file_name)

    if Path(file_name).suffix in (".ods", ".xlsx"):
        if not self.observationId:
            QMessageBox.warning(
                None,
                cfg.programName,
                ("Please open or create a new observation before importing from a spreadsheet file"),
                QMessageBox.Ok,
                QMessageBox.NoButton,
            )
            return

        load_observations_from_spreadsheet(self, file_name)
