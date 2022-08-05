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
from PyQt5.QtGui import QFont, QTextOption, QTextCursor

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

    if max_obs_length == dec(-1):  # media length not available, user choose to not use events
        QMessageBox.warning(
            None,
            cfg.programName,
            ("The duration of one or more observation is not available"),
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

    ok, msg, data_report = time_budget_functions.synthetic_time_budget(self.pj, selected_observations, synth_tb_param)
    if not ok:
        results = dialog.Results_dialog()
        results.setWindowTitle("Synthetic time budget")
        results.ptText.clear()
        results.ptText.setReadOnly(True)
        results.ptText.appendHtml(msg.replace("\n", "<br>"))
        results.exec_()
        return

    results = dialog.Results_dialog()
    results.dataset = True
    results.setWindowTitle("Synthetic time budget")
    font = QFont("Courier", 12)
    results.ptText.setFont(font)
    results.ptText.setWordWrapMode(QTextOption.NoWrap)
    results.ptText.setReadOnly(True)
    results.ptText.appendPlainText(data_report.export("cli", tablefmt="grid"))  # other available format: github
    results.ptText.moveCursor(QTextCursor.Start)
    results.resize(960, 640)

    if results.exec_() == cfg.SAVE_DATASET:
        extended_file_formats = [
            "Tab Separated Values (*.tsv)",
            "Comma Separated Values (*.csv)",
            "Open Document Spreadsheet ODS (*.ods)",
            "Microsoft Excel Spreadsheet XLSX (*.xlsx)",
            "Legacy Microsoft Excel Spreadsheet XLS (*.xls)",
            "HTML (*.html)",
            "Text file",  # tablib format: cli
        ]
        file_formats = ["tsv", "csv", "ods", "xlsx", "xls", "html", "cli"]

        file_name, filter_ = QFileDialog().getSaveFileName(
            self, "Synthetic time budget", "", ";;".join(extended_file_formats)
        )
        if not file_name:
            return

        output_format = file_formats[extended_file_formats.index(filter_)]
        if output_format != "cli" and pl.Path(file_name).suffix != "." + output_format:
            file_name = str(pl.Path(file_name)) + "." + output_format
            if pl.Path(file_name).is_file():
                if (
                    dialog.MessageDialog(
                        cfg.programName, f"The file {file_name} already exists.", [cfg.CANCEL, cfg.OVERWRITE]
                    )
                    == cfg.CANCEL
                ):
                    return

        if output_format in ["tsv", "csv", "html", "cli"]:
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

    if max_obs_length == dec(-1):  # media length not available, user choose to not use events
        QMessageBox.warning(
            None,
            cfg.programName,
            ("The duration of one or more observation is not available"),
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

    ok, data_report = time_budget_functions.synthetic_time_budget_bin(self.pj, selected_observations, synth_tb_param)

    if not ok:
        results = dialog.Results_dialog()
        results.setWindowTitle("Synthetic time budget with time bin")
        results.ptText.appendHtml("Error during the creation of the synthetic time budget with time bin")
        results.exec_()
        return

    results = dialog.Results_dialog()
    results.dataset = True
    results.setWindowTitle("Synthetic time budget by time bin")
    font = QFont("Courier", 12)
    results.ptText.setFont(font)
    results.ptText.setWordWrapMode(QTextOption.NoWrap)
    results.ptText.setReadOnly(True)
    results.ptText.appendPlainText(data_report.export("cli", tablefmt="grid"))  # other available format: github
    results.ptText.moveCursor(QTextCursor.Start)
    results.resize(960, 640)

    if results.exec_() == cfg.SAVE_DATASET:
        extended_file_formats = [
            "Tab Separated Values (*.tsv)",
            "Comma Separated Values (*.csv)",
            "Open Document Spreadsheet ODS (*.ods)",
            "Microsoft Excel Spreadsheet XLSX (*.xlsx)",
            "Legacy Microsoft Excel Spreadsheet XLS (*.xls)",
            "HTML (*.html)",
            "Text file",  # tablib format: cli
        ]
        file_formats = ["tsv", "csv", "ods", "xlsx", "xls", "html", "cli"]

        file_name, filter_ = QFileDialog().getSaveFileName(
            self, "Synthetic time budget with time bin", "", ";;".join(extended_file_formats)
        )
        if not file_name:
            return

        output_format = file_formats[extended_file_formats.index(filter_)]
        if output_format != "cli" and pl.Path(file_name).suffix != "." + output_format:
            file_name = str(pl.Path(file_name)) + "." + output_format
            if pl.Path(file_name).is_file():
                if (
                    dialog.MessageDialog(
                        cfg.programName, f"The file {file_name} already exists.", [cfg.CANCEL, cfg.OVERWRITE]
                    )
                    == cfg.CANCEL
                ):
                    return

        if output_format in ["tsv", "csv", "html", "cli"]:
            with open(file_name, "wb") as f:
                f.write(str.encode(data_report.export(output_format)))
        if output_format in ["ods", "xlsx", "xls"]:
            with open(file_name, "wb") as f:
                f.write(data_report.export(output_format))
