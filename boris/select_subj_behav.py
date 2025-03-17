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
from decimal import Decimal as dec
from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QCheckBox, QListWidgetItem, QMessageBox

from . import config as cfg
from . import gui_utilities, param_panel, project_functions
from . import utilities as util


def choose_obs_subj_behav_category(
    self,
    selected_observations: list,
    start_coding: Optional[dec] = dec("NaN"),  #  Union[..., None]
    end_coding: Optional[dec] = dec("NaN"),
    start_interval: Optional[dec] = dec("NaN"),
    end_interval: Optional[dec] = dec("NaN"),
    maxTime: Optional[dec] = None,
    show_include_modifiers: bool = True,
    show_exclude_non_coded_behaviors: bool = True,
    by_category: bool = False,
    n_observations: int = 1,
    show_time_bin_size: bool = False,
    window_title: str = "Select subjects and behaviors",
    show_exclude_non_coded_modifiers: bool = False,
) -> dict:
    """
    show window for:
    - selection of subjects
    - selection of behaviors (based on selected subjects)
    - selection of time interval
    - inclusion/exclusion of modifiers
    - inclusion/exclusion of behaviors without events (show_exclude_non_coded_behaviors == True)
    - selection of time bin size (show_time_bin_size == True)

    Args:
        selected_observations (list): List of selected observations
        ...
        show_exclude_non_coded_modifiers (bool): display the Exclude non coded modifiers checkbox

    Returns:
        dict: {"selected subjects": selectedSubjects,
            "selected behaviors": selectedBehaviors,
            "include modifiers": True/False,
            "exclude behaviors": True/False,
            "time": TIME_FULL_OBS / TIME_EVENTS / TIME_ARBITRARY_INTERVAL / TIME_OBS_INTERVAL
            "start time": startTime,
            "end time": endTime
            }

    """

    paramPanelWindow = param_panel.Param_panel()
    paramPanelWindow.resize(400, 400)
    paramPanelWindow.setWindowTitle(window_title)
    paramPanelWindow.selectedObservations = selected_observations
    paramPanelWindow.pj = self.pj
    paramPanelWindow.extract_observed_behaviors = self.extract_observed_behaviors

    paramPanelWindow.cbIncludeModifiers.setVisible(show_include_modifiers)
    paramPanelWindow.cb_exclude_non_coded_modifiers.setVisible(show_exclude_non_coded_modifiers)
    paramPanelWindow.cbExcludeBehaviors.setVisible(show_exclude_non_coded_behaviors)
    # show_time_bin_size:
    paramPanelWindow.frm_time_bin_size.setVisible(show_time_bin_size)

    if by_category:
        paramPanelWindow.cbIncludeModifiers.setVisible(False)
        paramPanelWindow.cbExcludeBehaviors.setVisible(False)
        paramPanelWindow.cb_exclude_non_coded_modifiers.setVisible(False)

    # set state of cb_exclude_non_coded_modifiers
    paramPanelWindow.cb_exclude_non_coded_modifiers.setEnabled(paramPanelWindow.cbIncludeModifiers.isChecked())

    paramPanelWindow.media_duration = maxTime
    paramPanelWindow.start_coding = start_coding
    paramPanelWindow.end_coding = end_coding
    paramPanelWindow.start_interval = start_interval
    paramPanelWindow.end_interval = end_interval

    if self.timeFormat == cfg.S:
        paramPanelWindow.start_time.rb_seconds.setChecked(True)
        paramPanelWindow.end_time.rb_seconds.setChecked(True)
    if self.timeFormat == cfg.HHMMSS:
        paramPanelWindow.start_time.rb_time.setChecked(True)
        paramPanelWindow.end_time.rb_time.setChecked(True)

    if n_observations > 1:
        paramPanelWindow.frm_time_interval.setVisible(False)
    else:
        if (start_coding is None) or (start_coding.is_nan()):
            paramPanelWindow.rb_observed_events.setEnabled(False)
            paramPanelWindow.frm_time_interval.setVisible(False)
            paramPanelWindow.rb_user_defined.setVisible(False)
            paramPanelWindow.rb_obs_interval.setVisible(False)
            paramPanelWindow.rb_media_duration.setVisible(False)
        else:
            paramPanelWindow.frm_time_interval.setEnabled(False)
            paramPanelWindow.start_time.set_time(start_coding)
            paramPanelWindow.end_time.set_time(end_coding)

    # check observation time interval
    if start_interval is None or start_interval.is_nan() or end_interval is None or end_interval.is_nan():
        paramPanelWindow.rb_obs_interval.setEnabled(False)

    if selected_observations:
        observedSubjects = project_functions.extract_observed_subjects(self.pj, selected_observations)
    else:
        # load all subjects and "No focal subject"
        observedSubjects = [self.pj[cfg.SUBJECTS][x][cfg.SUBJECT_NAME] for x in self.pj[cfg.SUBJECTS]] + [""]
    selectedSubjects = []

    # add 'No focal subject'
    if "" in observedSubjects:
        selectedSubjects.append(cfg.NO_FOCAL_SUBJECT)
        paramPanelWindow.item = QListWidgetItem(paramPanelWindow.lwSubjects)
        paramPanelWindow.ch = QCheckBox()
        paramPanelWindow.ch.setText(cfg.NO_FOCAL_SUBJECT)
        paramPanelWindow.ch.stateChanged.connect(paramPanelWindow.cb_changed)
        paramPanelWindow.ch.setChecked(True)
        paramPanelWindow.lwSubjects.setItemWidget(paramPanelWindow.item, paramPanelWindow.ch)

    all_subjects = [self.pj[cfg.SUBJECTS][x][cfg.SUBJECT_NAME] for x in util.sorted_keys(self.pj[cfg.SUBJECTS])]

    for subject in all_subjects:
        paramPanelWindow.item = QListWidgetItem(paramPanelWindow.lwSubjects)
        paramPanelWindow.ch = QCheckBox()
        paramPanelWindow.ch.setText(subject)
        paramPanelWindow.ch.stateChanged.connect(paramPanelWindow.cb_changed)
        if subject in observedSubjects:
            selectedSubjects.append(subject)
            paramPanelWindow.ch.setChecked(True)

        paramPanelWindow.lwSubjects.setItemWidget(paramPanelWindow.item, paramPanelWindow.ch)

    logging.debug(f"selected subjects: {selectedSubjects}")

    if selected_observations:
        observedBehaviors = self.extract_observed_behaviors(selected_observations, selectedSubjects)  # not sorted
    else:
        # load all behaviors
        observedBehaviors = [self.pj[cfg.ETHOGRAM][x][cfg.BEHAVIOR_CODE] for x in self.pj[cfg.ETHOGRAM]]

    logging.debug(f"observed behaviors: {observedBehaviors}")

    if cfg.BEHAVIORAL_CATEGORIES in self.pj:
        categories = self.pj[cfg.BEHAVIORAL_CATEGORIES][:]
        # check if behavior not included in a category
        try:
            if "" in [
                self.pj[cfg.ETHOGRAM][idx][cfg.BEHAVIOR_CATEGORY]
                for idx in self.pj[cfg.ETHOGRAM]
                if cfg.BEHAVIOR_CATEGORY in self.pj[cfg.ETHOGRAM][idx]
            ]:
                categories += [""]
        except Exception:
            categories = ["###no category###"]

    else:
        categories = ["###no category###"]

    for category in categories:
        if category != "###no category###":
            if category == "":
                paramPanelWindow.item = QListWidgetItem("No category")
                paramPanelWindow.item.setData(34, "No category")
            else:
                paramPanelWindow.item = QListWidgetItem(category)
                paramPanelWindow.item.setData(34, category)

            font = QFont()
            font.setBold(True)
            paramPanelWindow.item.setFont(font)
            paramPanelWindow.item.setData(33, "category")
            paramPanelWindow.item.setData(35, False)

            paramPanelWindow.lwBehaviors.addItem(paramPanelWindow.item)

        for behavior in [self.pj[cfg.ETHOGRAM][x][cfg.BEHAVIOR_CODE] for x in util.sorted_keys(self.pj[cfg.ETHOGRAM])]:
            if (categories == ["###no category###"]) or (
                behavior
                in [
                    self.pj[cfg.ETHOGRAM][x][cfg.BEHAVIOR_CODE]
                    for x in self.pj[cfg.ETHOGRAM]
                    if cfg.BEHAVIOR_CATEGORY in self.pj[cfg.ETHOGRAM][x] and self.pj[cfg.ETHOGRAM][x][cfg.BEHAVIOR_CATEGORY] == category
                ]
            ):
                paramPanelWindow.item = QListWidgetItem(behavior)
                if behavior in observedBehaviors:
                    paramPanelWindow.item.setCheckState(Qt.Checked)
                else:
                    paramPanelWindow.item.setCheckState(Qt.Unchecked)

                if category != "###no category###":
                    paramPanelWindow.item.setData(33, "behavior")
                    if category == "":
                        paramPanelWindow.item.setData(34, "No category")
                    else:
                        paramPanelWindow.item.setData(34, category)

                paramPanelWindow.lwBehaviors.addItem(paramPanelWindow.item)

    gui_utilities.restore_geometry(paramPanelWindow, "param panel", (600, 500))

    if not paramPanelWindow.exec_():
        return {}

    gui_utilities.save_geometry(paramPanelWindow, "param panel")

    selectedSubjects = paramPanelWindow.selectedSubjects
    selectedBehaviors = paramPanelWindow.selectedBehaviors

    logging.debug(f"selected subjects: {selectedSubjects}")
    logging.debug(f"selected behaviors: {selectedBehaviors}")

    if paramPanelWindow.rb_user_defined.isChecked():
        startTime = paramPanelWindow.start_time.get_time()
        endTime = paramPanelWindow.end_time.get_time()

        if startTime > endTime:
            QMessageBox.warning(
                None,
                cfg.programName,
                "The start time is after the end time",
                QMessageBox.Ok | QMessageBox.Default,
                QMessageBox.NoButton,
            )
            return {cfg.SELECTED_SUBJECTS: [], cfg.SELECTED_BEHAVIORS: []}

    elif paramPanelWindow.rb_obs_interval.isChecked() and not ((start_interval is None) or start_interval.is_nan()):
        startTime = paramPanelWindow.start_time.get_time()
        endTime = paramPanelWindow.end_time.get_time()

    else:
        startTime = None
        endTime = None

    # if startTime is None:
    #    startTime = dec("NaN")
    # if endTime is None:
    #    endTime = dec("NaN")

    if paramPanelWindow.rb_media_duration.isChecked():
        time_param = cfg.TIME_FULL_OBS
    if paramPanelWindow.rb_observed_events.isChecked():
        time_param = cfg.TIME_EVENTS
    if paramPanelWindow.rb_obs_interval.isChecked():
        time_param = cfg.TIME_OBS_INTERVAL
    if paramPanelWindow.rb_user_defined.isChecked():
        time_param = cfg.TIME_ARBITRARY_INTERVAL

    return {
        cfg.SELECTED_SUBJECTS: selectedSubjects,
        cfg.SELECTED_BEHAVIORS: selectedBehaviors,
        cfg.INCLUDE_MODIFIERS: paramPanelWindow.cbIncludeModifiers.isChecked(),
        cfg.EXCLUDE_BEHAVIORS: paramPanelWindow.cbExcludeBehaviors.isChecked(),
        cfg.EXCLUDE_NON_CODED_MODIFIERS: paramPanelWindow.cb_exclude_non_coded_modifiers.isChecked(),
        "time": time_param,
        cfg.START_TIME: startTime,
        cfg.END_TIME: endTime,
        cfg.TIME_BIN_SIZE: paramPanelWindow.sb_time_bin_size.value(),
    }
