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

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QDialog

from . import config as cfg
from .param_panel_ui import Ui_Dialog
from . import dialog


class Param_panel(QDialog, Ui_Dialog):
    def __init__(self, parent=None):
        super().__init__()
        self.setupUi(self)

        self.media_duration = None

        # insert duration widget for time offset
        self.start_time = dialog.get_time_widget(0)
        self.horizontalLayout.insertWidget(1, self.start_time)
        self.end_time = dialog.get_time_widget(0)
        self.horizontalLayout_6.insertWidget(1, self.end_time)

        self.pbSelectAllSubjects.clicked.connect(lambda: self.subjects_button_clicked("select all"))
        self.pbUnselectAllSubjects.clicked.connect(lambda: self.subjects_button_clicked("unselect all"))
        self.pbReverseSubjectsSelection.clicked.connect(lambda: self.subjects_button_clicked("reverse selection"))

        self.pbSelectAllBehaviors.clicked.connect(lambda: self.behaviors_button_clicked("select all"))
        self.pbUnselectAllBehaviors.clicked.connect(lambda: self.behaviors_button_clicked("unselect all"))
        self.pbReverseBehaviorsSelection.clicked.connect(lambda: self.behaviors_button_clicked("reverse selection"))

        self.pbOK.clicked.connect(self.ok)
        self.pbCancel.clicked.connect(self.reject)

        self.lwBehaviors.itemClicked.connect(self.behavior_item_clicked)

        self.rb_observed_events.setChecked(True)

        self.rb_media_duration.clicked.connect(lambda: self.rb_time_interval_selection(cfg.TIME_FULL_OBS))
        self.rb_observed_events.clicked.connect(lambda: self.rb_time_interval_selection(cfg.TIME_EVENTS))
        self.rb_user_defined.clicked.connect(lambda: self.rb_time_interval_selection(cfg.TIME_ARBITRARY_INTERVAL))
        self.rb_obs_interval.clicked.connect(lambda: self.rb_time_interval_selection(cfg.TIME_OBS_INTERVAL))

        self.cbIncludeModifiers.stateChanged.connect(self.cb_exclude_non_coded_modifiers_visibility)

        self.cb_exclude_non_coded_modifiers.setVisible(False)

    def cb_exclude_non_coded_modifiers_visibility(self):
        """
        set visibility of cb_exclude_non_coded_modifiers
        """
        self.cb_exclude_non_coded_modifiers.setEnabled(self.cbIncludeModifiers.isChecked())

    def rb_time_interval_selection(self, button):
        """
        select the time interval for operation
        """
        if button == cfg.TIME_ARBITRARY_INTERVAL:
            self.frm_time_interval.setEnabled(True)
            self.frm_time_interval.setVisible(True)

        elif button == cfg.TIME_EVENTS and len(self.selectedObservations) == 1:
            self.start_time.set_time(self.start_coding)
            self.end_time.set_time(self.end_coding)
            self.frm_time_interval.setEnabled(False)
            self.frm_time_interval.setVisible(True)

        elif button == cfg.TIME_FULL_OBS and len(self.selectedObservations) == 1 and self.media_duration is not None:
            self.start_time.set_time(0)
            self.end_time.set_time(self.media_duration)
            self.frm_time_interval.setEnabled(False)
            self.frm_time_interval.setVisible(True)

        elif button == cfg.TIME_OBS_INTERVAL:
            if not ((self.start_interval is None) or self.start_interval.is_nan()):
                # Set start_time and end_time widgets values even if it is not shown with
                # more than 1 observation as some analyses might use it (eg: advanced event filtering)

                print(f"{self.end_interval=}")

                end_interval = self.end_interval if self.end_interval != 0 else self.media_duration

                print(f"{end_interval=}")

                self.start_time.set_time(self.start_interval)
                self.end_time.set_time(end_interval)
                self.frm_time_interval.setEnabled(False)
                if len(self.selectedObservations) == 1:
                    self.frm_time_interval.setVisible(True)

        else:
            self.frm_time_interval.setVisible(False)

    def subjects_button_clicked(self, command):
        for idx in range(self.lwSubjects.count()):
            cb = self.lwSubjects.itemWidget(self.lwSubjects.item(idx))
            if command == "select all":
                cb.setChecked(True)
            if command == "unselect all":
                cb.setChecked(False)
            if command == "reverse selection":
                cb.setChecked(not cb.isChecked())

    def behaviors_button_clicked(self, command):
        for idx in range(self.lwBehaviors.count()):
            if self.lwBehaviors.item(idx).data(33) != "category":
                if command == "select all":
                    self.lwBehaviors.item(idx).setCheckState(Qt.Checked)

                if command == "unselect all":
                    self.lwBehaviors.item(idx).setCheckState(Qt.Unchecked)

                if command == "reverse selection":
                    if self.lwBehaviors.item(idx).checkState() == Qt.Checked:
                        self.lwBehaviors.item(idx).setCheckState(Qt.Unchecked)
                    else:
                        self.lwBehaviors.item(idx).setCheckState(Qt.Checked)

    def ok(self):
        selectedSubjects = []
        for idx in range(self.lwSubjects.count()):
            cb = self.lwSubjects.itemWidget(self.lwSubjects.item(idx))
            if cb.isChecked():
                selectedSubjects.append(cb.text())
        self.selectedSubjects = selectedSubjects

        selectedBehaviors = []
        for idx in range(self.lwBehaviors.count()):
            if self.lwBehaviors.item(idx).checkState() == Qt.Checked:
                selectedBehaviors.append(self.lwBehaviors.item(idx).text())
        self.selectedBehaviors = selectedBehaviors

        self.accept()

    def behavior_item_clicked(self, item):
        """
        check / uncheck behaviors belonging to the clicked category
        """

        if item.data(33) == "category":
            category = item.data(34)
            for i in range(self.lwBehaviors.count()):
                if self.lwBehaviors.item(i).data(34) == category and self.lwBehaviors.item(i).data(33) != "category":
                    if item.data(35):
                        self.lwBehaviors.item(i).setCheckState(Qt.Unchecked)
                    else:
                        self.lwBehaviors.item(i).setCheckState(Qt.Checked)

            item.setData(35, not item.data(35))

    def extract_observed_behaviors(self, selected_observations, selected_subjects):
        """
        extract unique behaviors codes from obs_id observation and selected subjects
        """

        observed_behaviors = []

        # extract events from selected observations
        all_events = [self.pj[cfg.OBSERVATIONS][x][cfg.EVENTS] for x in self.pj[cfg.OBSERVATIONS] if x in selected_observations]

        for events in all_events:
            for event in events:
                if event[cfg.EVENT_SUBJECT_FIELD_IDX] in selected_subjects or (
                    not event[cfg.EVENT_SUBJECT_FIELD_IDX] and cfg.NO_FOCAL_SUBJECT in selected_subjects
                ):
                    observed_behaviors.append(event[cfg.EVENT_BEHAVIOR_FIELD_IDX])

        # remove duplicate
        return list(set(observed_behaviors))

    def cb_changed(self):
        selected_subjects: list = []
        for idx in range(self.lwSubjects.count()):
            cb = self.lwSubjects.itemWidget(self.lwSubjects.item(idx))
            if cb and cb.isChecked():
                selected_subjects.append(cb.text())

        observed_behaviors = self.extract_observed_behaviors(self.selectedObservations, selected_subjects)

        for idx in range(self.lwBehaviors.count()):
            if self.lwBehaviors.item(idx).data(33) != "category":
                if self.lwBehaviors.item(idx).text() in observed_behaviors:
                    self.lwBehaviors.item(idx).setCheckState(Qt.Checked)
                else:
                    self.lwBehaviors.item(idx).setCheckState(Qt.Unchecked)
