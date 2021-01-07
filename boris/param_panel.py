#!/usr/bin/env python3

"""
BORIS
Behavioral Observation Research Interactive Software
Copyright 2012-2021 Olivier Friard

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
import os
import sys

from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QDialog

from boris import duration_widget
from boris.config import *
from boris.param_panel_ui import Ui_Dialog


class Param_panel(QDialog, Ui_Dialog):

    def __init__(self, parent=None):

        super().__init__()
        self.setupUi(self)

        # insert duration widget for time offset
        self.start_time = duration_widget.Duration_widget(0)
        self.horizontalLayout.insertWidget(1, self.start_time)
        self.end_time = duration_widget.Duration_widget(0)
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

        self.rb_full.clicked.connect(lambda: self.rb_time(TIME_FULL_OBS))
        self.rb_limit.clicked.connect(lambda: self.rb_time(TIME_EVENTS))
        self.rb_interval.clicked.connect(lambda: self.rb_time(TIME_ARBITRARY_INTERVAL))


    def rb_time(self, button):
        """
        time
        """
        self.frm_time_interval.setEnabled(button == TIME_ARBITRARY_INTERVAL)


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
        all_events = [self.pj[OBSERVATIONS][x][EVENTS] for x in self.pj[OBSERVATIONS] if x in selected_observations]

        for events in all_events:
            for event in events:
                if (event[EVENT_SUBJECT_FIELD_IDX] in selected_subjects
                        or (not event[EVENT_SUBJECT_FIELD_IDX] and NO_FOCAL_SUBJECT in selected_subjects)):
                    observed_behaviors.append(event[EVENT_BEHAVIOR_FIELD_IDX])

        # remove duplicate
        return list(set(observed_behaviors))


    def cb_changed(self):
        selectedSubjects = []
        for idx in range(self.lwSubjects.count()):
            cb = self.lwSubjects.itemWidget(self.lwSubjects.item(idx))
            if cb and cb.isChecked():
                selectedSubjects.append(cb.text())

        # FIX ME
        observedBehaviors = self.extract_observed_behaviors(self.selectedObservations, selectedSubjects)

        logging.debug(f"observed behaviors: {observedBehaviors}")

        for idx in range(self.lwBehaviors.count()):

            if self.lwBehaviors.item(idx).data(33) != "category":
                if self.lwBehaviors.item(idx).text() in observedBehaviors:
                    self.lwBehaviors.item(idx).setCheckState(Qt.Checked)
                else:
                    self.lwBehaviors.item(idx).setCheckState(Qt.Unchecked)
