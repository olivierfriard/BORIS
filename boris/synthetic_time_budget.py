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

import logging
import pathlib as pl
from decimal import Decimal as dec

from PyQt5.QtWidgets import QFileDialog, QMessageBox

from . import config as cfg
from . import (
    dialog,
    project_functions,
    select_observations,
    select_subj_behav,
    time_budget_functions,
    observation_operations,
)


def synthetic_time_budget(self):
    """
    Synthetic time budget
    """

    _, selected_observations = select_observations.select_observations(
        self.pj, mode=cfg.MULTIPLE, windows_title="Select observations for synthetic time budget"
    )

    if not selected_observations:
        return

    out = ""
    # check if coded behaviors are defined in ethogram
    ethogram_behavior_codes = {self.pj[cfg.ETHOGRAM][idx][cfg.BEHAVIOR_CODE] for idx in self.pj[cfg.ETHOGRAM]}
    behaviors_not_defined = []
    out = ""  # will contain the output
    for obs_id in selected_observations:
        for event in self.pj[cfg.OBSERVATIONS][obs_id][cfg.EVENTS]:
            if event[cfg.EVENT_BEHAVIOR_FIELD_IDX] not in ethogram_behavior_codes:
                behaviors_not_defined.append(event[cfg.EVENT_BEHAVIOR_FIELD_IDX])
    if set(sorted(behaviors_not_defined)):
        out += f"The following behaviors are not defined in the ethogram: <b>{', '.join(set(sorted(behaviors_not_defined)))}</b><br><br>"

    # check if state events are paired
    not_paired_obs_list = []
    for obs_id in selected_observations:
        r, msg = project_functions.check_state_events_obs(
            obs_id, self.pj[cfg.ETHOGRAM], self.pj[cfg.OBSERVATIONS][obs_id], self.timeFormat
        )
        if not r:
            out += f"Observation: <strong>{obs_id}</strong><br>{msg}<br>"
            not_paired_obs_list.append(obs_id)

    if out:
        if not_paired_obs_list:
            out += "<br>The observations with UNPAIRED state events will be removed from the analysis"
        self.results = dialog.Results_dialog()
        self.results.setWindowTitle(cfg.programName + " - Check selected observations")
        self.results.ptText.setReadOnly(True)
        self.results.ptText.appendHtml(out)
        self.results.pbSave.setVisible(False)
        self.results.pbCancel.setVisible(True)

        if not self.results.exec_():
            return

    # remove observations with unpaired state events
    selected_observations = [x for x in selected_observations if x not in not_paired_obs_list]
    if not selected_observations:
        return

    max_obs_length, selectedObsTotalMediaLength = observation_operations.observation_length(
        self.pj, selected_observations
    )

    if max_obs_length == dec(-1):  # media length not available, user choose to not use events
        QMessageBox.warning(
            None,
            cfg.programName,
            ("The observation length is not available"),
            QMessageBox.Ok | QMessageBox.Default,
            QMessageBox.NoButton,
        )
        return

    logging.debug(f"max_obs_length: {max_obs_length}, selectedObsTotalMediaLength: {selectedObsTotalMediaLength}")

    synth_tb_param = select_subj_behav.choose_obs_subj_behav_category(
        self,
        selected_observations,
        maxTime=max_obs_length if len(selected_observations) > 1 else selectedObsTotalMediaLength,
        flagShowExcludeBehaviorsWoEvents=False,
        by_category=False,
    )

    if not synth_tb_param[cfg.SELECTED_SUBJECTS] or not synth_tb_param[cfg.SELECTED_BEHAVIORS]:
        return

    # ask for excluding behaviors durations from total time
    if not max_obs_length.is_nan():
        cancel_pressed, synth_tb_param[cfg.EXCLUDED_BEHAVIORS] = self.filter_behaviors(
            title="Select behaviors to exclude from the total time",
            text=("The duration of the selected behaviors will " "be subtracted from the total time"),
            table="",
            behavior_type=[cfg.STATE_EVENT],
        )

        if cancel_pressed:
            return
    else:
        synth_tb_param[cfg.EXCLUDED_BEHAVIORS] = []

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
        self, "Synthetic time budget", "", ";;".join(extended_file_formats)
    )
    if not file_name:
        return

    output_format = file_formats[extended_file_formats.index(filter_)]
    if pl.Path(file_name).suffix != "." + output_format:
        file_name = str(pl.Path(file_name)) + "." + output_format
        if pl.Path(file_name).is_file():
            if (
                dialog.MessageDialog(
                    cfg.programName, f"The file {file_name} already exists.", [cfg.CANCEL, cfg.OVERWRITE]
                )
                == cfg.CANCEL
            ):
                return

    ok, msg, data_report = time_budget_functions.synthetic_time_budget(self.pj, selected_observations, synth_tb_param)
    if not ok:
        results = dialog.Results_dialog()
        results.setWindowTitle("Synthetic time budget")
        results.ptText.clear()
        results.ptText.setReadOnly(True)
        results.ptText.appendHtml(msg.replace("\n", "<br>"))
        results.exec_()
        return

    # print(data_report.export("cli", tablefmt="github"))

    if output_format in ["tsv", "csv", "html"]:
        with open(file_name, "wb") as f:
            f.write(str.encode(data_report.export(output_format)))
    if output_format in ["ods", "xlsx", "xls"]:
        with open(file_name, "wb") as f:
            f.write(data_report.export(output_format))


def synthetic_binned_time_budget(self):
    """
    Synthetic time budget with time bin
    """

    """
    QMessageBox.warning(
        None,
        cfg.programName,
        (
            f"This function is experimental. Please test it and report any bug at <br>"
            '<a href="https://github.com/olivierfriard/BORIS/issues">'
            "https://github.com/olivierfriard/BORIS/issues</a><br>"
            "or by email (See the About page on the BORIS web site.<br><br>"
            "Thank you for your collaboration!"
        ),
        QMessageBox.Ok | QMessageBox.Default,
        QMessageBox.NoButton,
    )
    """
    _, selected_observations = select_observations.select_observations(
        self.pj, mode=cfg.MULTIPLE, windows_title="Select observations for synthetic binned time budget"
    )

    if not selected_observations:
        return

    out = ""
    # check if coded behaviors are defined in ethogram
    ethogram_behavior_codes = {self.pj[cfg.ETHOGRAM][idx][cfg.BEHAVIOR_CODE] for idx in self.pj[cfg.ETHOGRAM]}
    behaviors_not_defined = []
    out = ""  # will contain the output
    for obs_id in selected_observations:
        for event in self.pj[cfg.OBSERVATIONS][obs_id][cfg.EVENTS]:
            if event[cfg.EVENT_BEHAVIOR_FIELD_IDX] not in ethogram_behavior_codes:
                behaviors_not_defined.append(event[cfg.EVENT_BEHAVIOR_FIELD_IDX])
    if set(sorted(behaviors_not_defined)):
        out += f"The following behaviors are not defined in the ethogram: <b>{', '.join(set(sorted(behaviors_not_defined)))}</b><br><br>"

    # check if state events are paired
    not_paired_obs_list = []
    for obs_id in selected_observations:
        r, msg = project_functions.check_state_events_obs(
            obs_id, self.pj[cfg.ETHOGRAM], self.pj[cfg.OBSERVATIONS][obs_id], self.timeFormat
        )
        if not r:
            out += f"Observation: <strong>{obs_id}</strong><br>{msg}<br>"
            not_paired_obs_list.append(obs_id)

    if out:
        if not_paired_obs_list:
            out += "<br>The observations with UNPAIRED state events will not be used in the analysis"
        self.results = dialog.Results_dialog()
        self.results.setWindowTitle(f"{cfg.programName} - Check selected observations")
        self.results.ptText.setReadOnly(True)
        self.results.ptText.appendHtml(out)
        self.results.pbSave.setVisible(False)
        self.results.pbCancel.setVisible(True)

        if not self.results.exec_():
            return

    # remove observations with unpaired state events
    selected_observations = [x for x in selected_observations if x not in not_paired_obs_list]
    if not selected_observations:
        return

    max_obs_length, selectedObsTotalMediaLength = observation_operations.observation_length(
        self.pj, selected_observations
    )

    if max_obs_length == dec(-1):  # media length not available, user choose to not use events
        QMessageBox.warning(
            None,
            cfg.programName,
            ("The observation length is not available"),
            QMessageBox.Ok | QMessageBox.Default,
            QMessageBox.NoButton,
        )
        return

    logging.debug(f"max_obs_length: {max_obs_length}, selectedObsTotalMediaLength: {selectedObsTotalMediaLength}")

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

    synth_tb_param = select_subj_behav.choose_obs_subj_behav_category(
        self,
        selected_observations,
        maxTime=max_obs_length if len(selected_observations) > 1 else selectedObsTotalMediaLength,
        flagShowExcludeBehaviorsWoEvents=False,
        by_category=False,
        show_time_bin_size=True,
    )

    if not synth_tb_param[cfg.SELECTED_SUBJECTS] or not synth_tb_param[cfg.SELECTED_BEHAVIORS]:
        return

    # ask for excluding behaviors durations from total time
    if not max_obs_length.is_nan():
        cancel_pressed, synth_tb_param[cfg.EXCLUDED_BEHAVIORS] = self.filter_behaviors(
            title="Select behaviors to exclude",
            text=("The duration of the selected behaviors will " "be subtracted from the total time"),
            table="",
            behavior_type=[cfg.STATE_EVENT],
        )
        if cancel_pressed:
            return
    else:
        synth_tb_param[cfg.EXCLUDED_BEHAVIORS] = []

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
        self, "Synthetic time budget with time bin", "", ";;".join(extended_file_formats)
    )
    if not file_name:
        return

    output_format = file_formats[extended_file_formats.index(filter_)]
    if pl.Path(file_name).suffix != "." + output_format:
        file_name = str(pl.Path(file_name)) + "." + output_format
        if pl.Path(file_name).is_file():
            if (
                dialog.MessageDialog(
                    cfg.programName, f"The file {file_name} already exists.", [cfg.CANCEL, cfg.OVERWRITE]
                )
                == cfg.CANCEL
            ):
                return

    ok, data_report = time_budget_functions.synthetic_time_budget_bin(self.pj, selected_observations, synth_tb_param)

    if not ok:
        results = dialog.Results_dialog()
        results.setWindowTitle("Synthetic time budget with time bin")
        results.ptText.clear()
        results.ptText.setReadOnly(True)
        results.ptText.appendHtml(msg.replace("\n", "<br>"))
        results.exec_()
        return

    if output_format in ["tsv", "csv", "html"]:
        with open(file_name, "wb") as f:
            f.write(str.encode(data_report.export(output_format)))
    if output_format in ["ods", "xlsx", "xls"]:
        with open(file_name, "wb") as f:
            f.write(data_report.export(output_format))
