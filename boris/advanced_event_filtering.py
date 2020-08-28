"""
BORIS
Behavioral Observation Research Interactive Software
Copyright 2012-2020 Olivier Friard

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

import os
import pathlib
import re
import statistics
import sys

#import intervals as Interval  # python-intervals (https://pypi.org/project/python-intervals)
import portion as Interval    # replace python-intervals (https://pypi.org/project/portion/)
import tablib
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QIcon
from PyQt5.QtWidgets import (QDialog, QFileDialog, QHBoxLayout, QLabel,
                             QLineEdit, QListWidget, QMessageBox, QPushButton,
                             QRadioButton, QSizePolicy, QSpacerItem,
                             QTableWidget, QTableWidgetItem, QVBoxLayout)

from boris import (db_functions, dialog, project_functions,
                   select_observations, utilities)
from boris.config import *


def icc(i: list):
    """
    create a closed-closed interval
    """
    return Interval.closed(i[0], i[1])


def ico(i: list):
    """
    create a closed-open interval
    """
    return Interval.closedopen(i[0], i[1])


def io(i: list):
    """
    create a open interval
    """
    return Interval.open(i[0], i[1])


class Advanced_event_filtering_dialog(QDialog):
    """
    Dialog for visualizing advanced event filtering results
    """

    summary_header = ["Observation id", "Number of occurences", "Total duration (s)", "Duration mean (s)", "Std Dev"]
    details_header = ["Observation id", "Comment", "Start time", "Stop time", "Duration (s)"]

    def __init__(self, events):
        super().__init__()

        self.events = events
        self.out = []
        self.setWindowTitle("Advanced event filtering")

        vbox = QVBoxLayout()

        lb = QLabel("Filter")
        vbox.addWidget(lb)

        hbox = QHBoxLayout()
        self.logic = QLineEdit("")
        hbox.addWidget(self.logic)
        self.pb_filter = QPushButton("Filter events", clicked=self.filter)
        hbox.addWidget(self.pb_filter)
        self.pb_clear = QPushButton("Clear", clicked=self.logic.clear)
        self.pb_clear.setIcon(QIcon.fromTheme("edit-clear"))
        hbox.addWidget(self.pb_clear)
        vbox.addLayout(hbox)

        hbox = QHBoxLayout()
        self.rb_summary = QRadioButton("Summary", toggled=self.filter)
        self.rb_summary.setChecked(True)
        hbox.addWidget(self.rb_summary)
        self.rb_details = QRadioButton("Details", toggled=self.filter)
        hbox.addWidget(self.rb_details)
        vbox.addLayout(hbox)

        hbox = QHBoxLayout()
        vbox2 = QVBoxLayout()
        vbox2.addWidget(QLabel("Subjects"))
        self.lw1 = QListWidget()
        vbox2.addWidget(self.lw1)
        hbox.addLayout(vbox2)

        vbox2 = QVBoxLayout()
        vbox2.addWidget(QLabel("Behaviors"))
        self.lw2 = QListWidget()
        vbox2.addWidget(self.lw2)
        hbox.addLayout(vbox2)
        self.add_subj_behav_button = QPushButton("", clicked=self.add_subj_behav)
        self.add_subj_behav_button.setIcon(QIcon.fromTheme("go-up"))
        hbox.addWidget(self.add_subj_behav_button)

        vbox2 = QVBoxLayout()
        vbox2.addWidget(QLabel("Logical operators"))
        self.lw3 = QListWidget()
        self.lw3.addItems(["AND", "OR"])
        vbox2.addWidget(self.lw3)
        hbox.addLayout(vbox2)
        self.add_logic_button = QPushButton("", clicked=self.add_logic)
        self.add_logic_button.setIcon(QIcon.fromTheme("go-up"))
        hbox.addWidget(self.add_logic_button)

        vbox.addLayout(hbox)

        self.lb_results = QLabel("Results")
        vbox.addWidget(self.lb_results)

        self.tw = QTableWidget(self)
        vbox.addWidget(self.tw)

        hbox = QHBoxLayout()
        hbox.addItem(QSpacerItem(241, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))
        self.pb_save = QPushButton("Save results", clicked=self.save_results)
        hbox.addWidget(self.pb_save)
        self.pb_close = QPushButton("Close", clicked=self.close)
        hbox.addWidget(self.pb_close)
        vbox.addLayout(hbox)

        self.setLayout(vbox)

        subjects_list, behaviors_list = [], []
        for obs_id in events:
            for subj_behav in events[obs_id]:
                subj, behav = subj_behav.split("|")
                subjects_list.append(subj)
                behaviors_list.append(behav)
        subjects_set = sorted(set(subjects_list))
        behaviors_set = sorted(set(behaviors_list))

        self.lw1.addItems(subjects_set)
        self.lw2.addItems(behaviors_set)

        self.resize(640, 640)


    def add_subj_behav(self):
        """
        add subject|behavior of selected listwidgets items in lineEdit
        """
        if self.lw1.currentItem() and self.lw2.currentItem():
            self.logic.insert(f'"{self.lw1.currentItem().text()}|{self.lw2.currentItem().text()}" ')
        else:
            QMessageBox.warning(self, programName, "Select a subject and a behavior")


    def add_logic(self):
        """
        add selected logic operaton to lineedit
        """
        if self.lw3.currentItem():

            text = ""
            if self.lw3.currentItem().text() == "AND":
                text = " & "
            if self.lw3.currentItem().text() == "OR":
                text = " | "
            if text:
                self.logic.insert(text)
        else:
            QMessageBox.warning(self, programName, "Select a logical operator")


    def filter(self):
        """
        filter events
        """
        if not self.logic.text():
            return
        if self.logic.text().count('"') % 2:
            QMessageBox.warning(self, programName, f'Wrong number of double quotes (")')
            return

        sb_list = re.findall('"([^"]*)"', self.logic.text())

        self.out = []
        flag_error = False
        for obs_id in self.events:
            logic = self.logic.text()
            for sb in set(sb_list):
                logic = logic.replace(f'"{sb}"', f'self.events[obs_id]["{sb}"]')
                if sb not in self.events[obs_id]:
                    self.events[obs_id][sb] = io([0, 0])

            try:
                eval_result = eval(logic)
                for i in eval_result:
                    if not i.empty:
                        self.out.append([obs_id, "", f"{i.lower}", f"{i.upper}", f"{i.upper - i.lower:.3f}"])
            except KeyError:
                self.out.append([obs_id, "subject / behavior not found", "NA", "NA", "NA"])
            except Exception:
                # out += f"Error in {self.logic.text()}" + "\n"
                error_type, error_file_name, error_lineno = utilities.error_info(sys.exc_info())
                self.out.append([obs_id, f"Error in {self.logic.text()}: {error_type} ", "NA", "NA", "NA"])
                flag_error = True

        self.tw.clear()

        if flag_error or self.rb_details.isChecked():

            self.lb_results.setText(f"Results ({len(self.out)} event{'s'*(len(self.out) > 1)})")

            self.tw.setRowCount(len(self.out))
            self.tw.setColumnCount(len(self.details_header))  # obs_id, comment, start, stop, duration
            self.tw.setHorizontalHeaderLabels(self.details_header)

        if not flag_error and self.rb_summary.isChecked():

            summary = {}
            for row in self.out:
                obs_id, _, start, stop, duration = row
                if obs_id not in summary:
                    summary[obs_id] = []
                summary[obs_id].append(float(duration))

            self.out = []
            for obs_id in summary:

                self.out.append([
                    obs_id,
                    str(len(summary[obs_id])),
                    str(round(sum(summary[obs_id]), 3)),
                    str(round(statistics.mean(summary[obs_id]), 3)),
                    str(round(statistics.stdev(summary[obs_id]), 3))
                    if len(summary[obs_id]) > 1 else "NA"
                ])

            self.lb_results.setText(f"Results ({len(summary)} observation{'s'*(len(summary) > 1)})")
            self.tw.setRowCount(len(summary))
            self.tw.setColumnCount(len(self.summary_header))  # obs_id, mean, stdev
            self.tw.setHorizontalHeaderLabels(self.summary_header)

        for r in range(len(self.out)):
            for c in range(self.tw.columnCount()):
                item = QTableWidgetItem()
                item.setText(self.out[r][c])
                item.setFlags(Qt.ItemIsEnabled)
                self.tw.setItem(r, c, item)


    def save_results(self):
        """
        save results
        """

        extended_file_formats = ["Tab Separated Values (*.tsv)",
                                 "Comma Separated Values (*.csv)",
                                 "Open Document Spreadsheet ODS (*.ods)",
                                 "Microsoft Excel Spreadsheet XLSX (*.xlsx)",
                                 "Legacy Microsoft Excel Spreadsheet XLS (*.xls)",
                                 "HTML (*.html)"]
        file_formats = ["tsv",
                        "csv",
                        "ods",
                        "xlsx",
                        "xls",
                        "html"]

        file_name, filter_ = QFileDialog().getSaveFileName(None, "Save results", "", ";;".join(extended_file_formats))
        if not file_name:
            return

        output_format = file_formats[extended_file_formats.index(filter_)]

        if pathlib.Path(file_name).suffix != "." + output_format:
            file_name = str(pathlib.Path(file_name)) + "." + output_format
            # check if file with new extension already exists
            if pathlib.Path(file_name).is_file():
                if dialog.MessageDialog(programName,
                                        f"The file {file_name} already exists.",
                                        [CANCEL, OVERWRITE]) == CANCEL:
                    return

        if self.rb_details.isChecked():
            tablib_dataset = tablib.Dataset(headers=self.details_header)
        if self.rb_summary.isChecked():
            tablib_dataset = tablib.Dataset(headers=self.summary_header)
        tablib_dataset.title = utilities.safe_xl_worksheet_title(self.logic.text(), output_format)

        [tablib_dataset.append(x) for x in self.out]

        try:
            if output_format in ["csv", "tsv", "html"]:
                with open(file_name, "wb") as f:
                    f.write(str.encode(tablib_dataset.export(output_format)))

            if output_format in ["ods", "xlsx", "xls"]:
                with open(file_name, "wb") as f:
                    f.write(tablib_dataset.export(output_format))

        except Exception:
            QMessageBox.critical(self, programName, f"The file {file_name} can not be saved")


def event_filtering(pj: dict):
    """
    advanced event filtering
    the python-intervals module is used to do operations on intervals (intersection, union)
    """

    result, selected_observations = select_observations.select_observations(pj,
                                                                            MULTIPLE,
                                                                            "Select observations for advanced event filtering")
    if not selected_observations:
        return

    # check if state events are paired
    out = ""
    not_paired_obs_list = []
    for obs_id in selected_observations:
        r, msg = project_functions.check_state_events_obs(obs_id, pj[ETHOGRAM],
                                                          pj[OBSERVATIONS][obs_id])

        if not r:
            out += f"Observation: <strong>{obs_id}</strong><br>{msg}<br>"
            not_paired_obs_list.append(obs_id)

    if out:
        out = f"The observations with UNPAIRED state events will be removed from tha analysis<br><br>{out}"
        results = dialog.Results_dialog()
        results.setWindowTitle(f"{programName} - Check selected observations")
        results.ptText.setReadOnly(True)
        results.ptText.appendHtml(out)
        results.pbSave.setVisible(False)
        results.pbCancel.setVisible(True)

        if not results.exec_():
            return
    selected_observations = [x for x in selected_observations if x not in not_paired_obs_list]
    if not selected_observations:
        return

    # observations length
    max_obs_length, selectedObsTotalMediaLength = project_functions.observation_length(pj, selected_observations)
    if max_obs_length == -1:  # media length not available, user choose to not use events
        return

    parameters = dialog.choose_obs_subj_behav_category(pj,
                                                       selected_observations,
                                                       maxTime=max_obs_length,
                                                       flagShowIncludeModifiers=False,
                                                       flagShowExcludeBehaviorsWoEvents=False,
                                                       by_category=False)

    if not parameters[SELECTED_SUBJECTS] or not parameters[SELECTED_BEHAVIORS]:
        QMessageBox.warning(None, programName, "Select subject(s) and behavior(s) to analyze")
        return

    ok, msg, db_connector = db_functions.load_aggregated_events_in_db(pj,
                                                                      parameters[SELECTED_SUBJECTS],
                                                                      selected_observations,
                                                                      parameters[SELECTED_BEHAVIORS])

    cursor = db_connector.cursor()

    # create intervals from DB
    cursor.execute("SELECT observation, subject, behavior, start, stop FROM aggregated_events")
    events = {}
    for row in cursor.fetchall():
        for event in row:
            obs, subj, behav, start, stop = row
            # check if start and stop are in selected time interval
            if stop < parameters[START_TIME]:
                continue
            if start > parameters[END_TIME]:
                continue
            if start < parameters[START_TIME]:
                start = float(parameters[START_TIME])
            if stop > parameters[END_TIME]:
                stop = float(parameters[END_TIME])

            if obs not in events:
                events[obs] = {}

            # use function in base at event (state or point)
            interval_func = icc if start == stop else ico

            if f"{subj}|{behav}" not in events[obs]:
                events[obs][f"{subj}|{behav}"] = interval_func([start, stop])
            else:
                events[obs][f"{subj}|{behav}"] = events[obs][f"{subj}|{behav}"] | interval_func([start, stop])

    w = Advanced_event_filtering_dialog(events)
    w.exec_()
