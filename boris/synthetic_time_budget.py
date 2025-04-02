"""
BORIS
Behavioral Observation Research Interactive Software
Copyright 2012-2025 Olivier Friard

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

from PySide6.QtWidgets import QFileDialog, QMessageBox
from PySide6.QtGui import QFont, QTextOption, QTextCursor

from . import config as cfg
from . import (
    dialog,
    project_functions,
    select_observations,
    select_subj_behav,
    time_budget_functions,
    observation_operations,
)


def synthetic_time_budget(self) -> None:
    """
    Synthetic time budget
    """

    logging.debug("synthetic time budget function")

    _, selected_observations = select_observations.select_observations2(
        self, mode=cfg.MULTIPLE, windows_title="Select observations for synthetic time budget"
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

    max_media_duration_all_obs, _ = observation_operations.media_duration(self.pj[cfg.OBSERVATIONS], selected_observations)

    start_coding, end_coding, _ = observation_operations.coding_time(self.pj[cfg.OBSERVATIONS], selected_observations)

    start_interval, end_interval = observation_operations.time_intervals_range(self.pj[cfg.OBSERVATIONS], selected_observations)

    synth_tb_param = select_subj_behav.choose_obs_subj_behav_category(
        self,
        selected_observations,
        start_coding=start_coding,
        end_coding=end_coding,
        # start_interval=start_interval,
        # end_interval=end_interval,
        start_interval=None,
        end_interval=None,
        maxTime=max_media_duration_all_obs,
        show_exclude_non_coded_behaviors=False,
        by_category=False,
        n_observations=len(selected_observations),
        show_exclude_non_coded_modifiers=True,
    )

    if synth_tb_param == {}:
        return

    if not synth_tb_param[cfg.SELECTED_SUBJECTS] or not synth_tb_param[cfg.SELECTED_BEHAVIORS]:
        QMessageBox.warning(None, cfg.programName, "Select subject(s) and behavior(s) to analyze")
        return

    # ask for excluding behaviors durations from total time
    if not start_coding.is_nan():
        cancel_pressed, synth_tb_param[cfg.EXCLUDED_BEHAVIORS] = self.filter_behaviors(
            title="Select behaviors to exclude from the total time",
            text="The duration of the selected behaviors will be subtracted from the total time",
            table="",
            behavior_type=cfg.STATE_EVENT_TYPES,
        )
        if cancel_pressed:
            return
    else:
        synth_tb_param[cfg.EXCLUDED_BEHAVIORS] = []

    ok, msg, data_report = time_budget_functions.synthetic_time_budget(self.pj, selected_observations, synth_tb_param)

    results = dialog.Results_dialog()
    results.setWindowTitle("Synthetic time budget")
    if not ok:
        results.ptText.clear()
        results.ptText.setReadOnly(True)
        results.ptText.appendHtml(msg.replace("\n", "<br>"))
        results.exec_()
        return

    results.dataset = True
    font = QFont("Courier", 12)
    results.ptText.setFont(font)
    results.ptText.setWordWrapMode(QTextOption.NoWrap)
    results.ptText.setReadOnly(True)
    results.ptText.appendPlainText(data_report.export("cli", tablefmt="grid"))  # other available format: github
    results.ptText.moveCursor(QTextCursor.Start)
    results.resize(960, 640)

    if results.exec_() == cfg.SAVE_DATASET:
        file_formats = [
            cfg.TSV,
            cfg.CSV,
            cfg.ODS,
            cfg.XLSX,
            cfg.XLS,
            cfg.HTML,
            cfg.TEXT_FILE,  # tablib format: cli
        ]

        file_name, filter_ = QFileDialog().getSaveFileName(self, "Synthetic time budget", "", ";;".join(file_formats))
        if not file_name:
            return

        output_format = cfg.FILE_NAME_SUFFIX[filter_]

        if pl.Path(file_name).suffix != "." + output_format:
            if filter_ != cfg.TEXT_FILE:
                file_name = str(pl.Path(file_name)) + "." + output_format
            else:
                file_name = str(pl.Path(file_name))
            if pl.Path(file_name).is_file():
                if (
                    dialog.MessageDialog(cfg.programName, f"The file {file_name} already exists.", [cfg.CANCEL, cfg.OVERWRITE])
                    == cfg.CANCEL
                ):
                    return

        with open(file_name, "wb") as f:
            if filter_ in (cfg.TSV, cfg.CSV, cfg.HTML, cfg.TEXT_FILE):
                f.write(str.encode(data_report.export(output_format)))
            if filter_ in (cfg.ODS, cfg.XLSX, cfg.XLS):
                f.write(data_report.export(output_format))


def synthetic_binned_time_budget(self) -> None:
    """
    Synthetic time budget with time bin
    """

    _, selected_observations = select_observations.select_observations2(
        self, mode=cfg.MULTIPLE, windows_title="Select observations for synthetic binned time budget"
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

    max_media_duration_all_obs, total_media_duration_all_obs = observation_operations.media_duration(
        self.pj[cfg.OBSERVATIONS], selected_observations
    )

    start_coding, end_coding, _ = observation_operations.coding_time(self.pj[cfg.OBSERVATIONS], selected_observations)

    start_interval, end_interval = observation_operations.time_intervals_range(self.pj[cfg.OBSERVATIONS], selected_observations)

    # exit with message if events do not have timestamp
    if start_coding.is_nan():
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
        start_coding=start_coding,
        end_coding=end_coding,
        # start_interval=start_interval,
        # end_interval=end_interval,
        start_interval=None,
        end_interval=None,
        maxTime=max_media_duration_all_obs,
        show_exclude_non_coded_behaviors=False,
        by_category=False,
        n_observations=len(selected_observations),
        show_time_bin_size=True,
        show_exclude_non_coded_modifiers=True,
    )

    if synth_tb_param == {}:
        return

    if not synth_tb_param[cfg.SELECTED_SUBJECTS] or not synth_tb_param[cfg.SELECTED_BEHAVIORS]:
        QMessageBox.warning(None, cfg.programName, "Select subject(s) and behavior(s) to analyze")
        return

    # ask for excluding behaviors durations from total time
    cancel_pressed, synth_tb_param[cfg.EXCLUDED_BEHAVIORS] = self.filter_behaviors(
        title="Select behaviors to exclude",
        text=("The duration of the selected behaviors will be subtracted from the total time"),
        table="",
        behavior_type=cfg.STATE_EVENT_TYPES,
    )
    if cancel_pressed:
        return

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
        file_formats = [
            cfg.TSV,
            cfg.CSV,
            cfg.ODS,
            cfg.XLSX,
            cfg.XLS,
            cfg.HTML,
            cfg.TEXT_FILE,
        ]

        file_name, filter_ = QFileDialog().getSaveFileName(
            self, "Save the Synthetic time budget with time bin", "", ";;".join(file_formats)
        )
        if not file_name:
            return

        output_format = cfg.FILE_NAME_SUFFIX[filter_]

        if pl.Path(file_name).suffix != "." + output_format:
            if filter_ != cfg.TEXT_FILE:
                file_name = str(pl.Path(file_name)) + "." + output_format
            else:
                file_name = str(pl.Path(file_name))
            if pl.Path(file_name).is_file():
                if (
                    dialog.MessageDialog(cfg.programName, f"The file {file_name} already exists.", (cfg.CANCEL, cfg.OVERWRITE))
                    == cfg.CANCEL
                ):
                    return

        with open(file_name, "wb") as f:
            if filter_ in (cfg.TSV, cfg.CSV, cfg.HTML, cfg.TEXT_FILE):
                f.write(str.encode(data_report.export(output_format)))
            if filter_ in (cfg.ODS, cfg.XLSX, cfg.XLS):
                f.write(data_report.export(output_format))
