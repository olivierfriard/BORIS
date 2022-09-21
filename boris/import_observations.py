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


import json
import datetime

from PyQt5.QtWidgets import (
    QMessageBox,
    QFileDialog,
)

from . import config as cfg
from . import dialog
from . import utilities as util


def import_observations(self):
    """
    import observations from project file
    """

    fn = QFileDialog().getOpenFileName(
        None, "Choose a BORIS project file", "", "Project files (*.boris);;All files (*)"
    )
    fileName = fn[0] if type(fn) is tuple else fn

    if self.projectFileName and fileName == self.projectFileName:
        QMessageBox.critical(
            None,
            cfg.programName,
            "This project is already open",
            QMessageBox.Ok | QMessageBox.Default,
            QMessageBox.NoButton,
        )
        return

    if fileName:
        try:
            fromProject = json.loads(open(fileName, "r").read())
        except Exception:
            QMessageBox.critical(self, cfg.programName, "This project file seems corrupted")
            return

        # transform time to decimal
        fromProject = util.convert_time_to_decimal(fromProject)  # function in utilities.py

        dbc = dialog.ChooseObservationsToImport(
            "Choose the observations to import:", sorted(list(fromProject[cfg.OBSERVATIONS].keys()))
        )

        if dbc.exec_():

            selected_observations = dbc.get_selected_observations()
            if selected_observations:
                flagImported = False

                # set of behaviors in current projet ethogram
                behav_set = set([self.pj[cfg.ETHOGRAM][idx][cfg.BEHAVIOR_CODE] for idx in self.pj[cfg.ETHOGRAM]])

                # set of subjects in current projet
                subjects_set = set([self.pj[cfg.SUBJECTS][idx][cfg.SUBJECT_NAME] for idx in self.pj[cfg.SUBJECTS]])

                for obsId in selected_observations:

                    # check if behaviors are in current project ethogram
                    new_behav_set = set(
                        [
                            event[cfg.EVENT_BEHAVIOR_FIELD_IDX]
                            for event in fromProject[cfg.OBSERVATIONS][obsId][cfg.EVENTS]
                            if event[cfg.EVENT_BEHAVIOR_FIELD_IDX] not in behav_set
                        ]
                    )
                    if new_behav_set:
                        diag_result = dialog.MessageDialog(
                            cfg.programName,
                            (
                                f"Some coded behaviors in <b>{obsId}</b> are "
                                f"not defined in the ethogram:<br><b>{', '.join(new_behav_set)}</b>"
                            ),
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
                            for event in fromProject[cfg.OBSERVATIONS][obsId][cfg.EVENTS]
                            if event[cfg.EVENT_SUBJECT_FIELD_IDX] not in subjects_set
                        ]
                    )
                    if new_subject_set and new_subject_set != {""}:
                        diag_result = dialog.MessageDialog(
                            cfg.programName,
                            (
                                f"Some coded subjects in <b>{obsId}</b> are not defined in the project:<br>"
                                f"<b>{', '.join(new_subject_set)}</b>"
                            ),
                            ["Interrupt import", "Skip observation", "Import observation"],
                        )

                        if diag_result == "Interrupt import":
                            return

                        if diag_result == "Skip observation":
                            continue

                    if obsId in self.pj[cfg.OBSERVATIONS].keys():
                        diag_result = dialog.MessageDialog(
                            cfg.programName,
                            (f"The observation <b>{obsId}</b>" "already exists in the current project.<br>"),
                            ["Interrupt import", "Skip observation", "Rename observation"],
                        )
                        if diag_result == "Interrupt import":
                            return

                        if diag_result == "Rename observation":
                            self.pj[cfg.OBSERVATIONS][
                                f"{obsId} (imported at {util.datetime_iso8601(datetime.datetime.now())})"
                            ] = dict(fromProject[cfg.OBSERVATIONS][obsId])
                            flagImported = True
                    else:
                        self.pj[cfg.OBSERVATIONS][obsId] = dict(fromProject[cfg.OBSERVATIONS][obsId])
                        flagImported = True

                if flagImported:
                    QMessageBox.information(self, cfg.programName, "Observations imported successfully")
                    self.project_changed()
