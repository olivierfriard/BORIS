"""
BORIS
Behavioral Observation Research Interactive Software
Copyright 2012-2024 Olivier Friard

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
import pathlib as pl
from decimal import Decimal as dec
from io import StringIO
import pandas as pd
import time

try:
    import pyreadr

    flag_pyreadr_loaded = True
except ModuleNotFoundError:
    flag_pyreadr_loaded = False


import tablib
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QFileDialog,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QListWidget,
    QMessageBox,
    QPushButton,
    QSizePolicy,
    QSpacerItem,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
    QApplication,
)

from . import config as cfg
from . import (
    db_functions,
    dialog,
    gui_utilities,
    observation_operations,
    project_functions,
    select_observations,
    select_subj_behav,
    time_budget_functions,
)
from . import utilities as util


class timeBudgetResults(QWidget):
    """
    class for displaying time budget results in new window
    a function for exporting data in TSV, CSV, XLS and ODS formats is implemented

    Args:
        pj (dict): BORIS project
    """

    def __init__(self, pj, config_param):
        super().__init__()

        self.pj = pj
        self.config_param = config_param

        hbox = QVBoxLayout(self)

        self.label = QLabel("")
        hbox.addWidget(self.label)

        self.lw = QListWidget()
        # self.lw.setEnabled(False)
        self.lw.setMaximumHeight(100)
        hbox.addWidget(self.lw)

        self.lbTotalObservedTime = QLabel("")
        hbox.addWidget(self.lbTotalObservedTime)

        # behaviors excluded from total time
        self.excluded_behaviors_list = QLabel("")
        hbox.addWidget(self.excluded_behaviors_list)

        self.twTB = QTableWidget()
        hbox.addWidget(self.twTB)

        hbox2 = QHBoxLayout()

        self.pbSave = QPushButton("Save results", clicked=self.pbSave_clicked)
        hbox2.addWidget(self.pbSave)

        spacerItem = QSpacerItem(241, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)
        hbox2.addItem(spacerItem)

        self.pbClose = QPushButton(cfg.CLOSE, clicked=self.close_clicked)
        hbox2.addWidget(self.pbClose)

        hbox.addLayout(hbox2)

        self.setWindowTitle("Time budget")

    def close_clicked(self):
        """
        save geometry of widget and close it
        """
        gui_utilities.save_geometry(self, "time budget")
        self.close()

    def pbSave_clicked(self):
        """
        save time budget analysis results in TSV, CSV, ODS, XLS format
        """

        def complete(lst: list, max_: int) -> list:
            """
            complete list with empty string until len = max

            Args:
                lst (list): list to complete
                max_ (int): length of the returned list

            Returns:
                list: completed list
            """

            lst.extend([""] * (max_ - len(lst)))
            return lst

        logging.debug("save time budget results to file")

        file_formats = (cfg.TSV, cfg.CSV, cfg.ODS, cfg.XLSX, cfg.XLS, cfg.HTML, cfg.TEXT_FILE, cfg.PANDAS_DF, cfg.RDS)

        file_name, filter_ = QFileDialog().getSaveFileName(self, "Save Time budget analysis", "", ";;".join(file_formats))

        if not file_name:
            return

        # add correct file extension if not present
        if pl.Path(file_name).suffix != f".{cfg.FILE_NAME_SUFFIX[filter_]}":
            if cfg.FILE_NAME_SUFFIX[filter_] != "cli":
                file_name = str(pl.Path(file_name)) + "." + cfg.FILE_NAME_SUFFIX[filter_]
            else:
                file_name = str(pl.Path(file_name))
            # check if file with new extension already exists
            if pl.Path(file_name).is_file():
                if (
                    dialog.MessageDialog(cfg.programName, f"The file {file_name} already exists.", [cfg.CANCEL, cfg.OVERWRITE])
                    == cfg.CANCEL
                ):
                    return

        rows: list = []

        header: list = ["Observation id", "Observation date", "Description"]
        # indep var labels
        header.extend([self.pj[cfg.INDEPENDENT_VARIABLES][idx]["label"] for idx in self.pj[cfg.INDEPENDENT_VARIABLES]])
        header.extend(["Time budget start", "Time budget stop", "Time budget duration"])

        for idx in range(self.twTB.columnCount()):
            header.append(self.twTB.horizontalHeaderItem(idx).text())
        rows.append(header)

        col1: list = []
        # add obs id
        if self.lw.count() == 1:
            col1.append(self.lw.item(0).text())
        else:
            col1.append("NA, observations grouped")

        # add obs date
        if self.lw.count() == 1:
            col1.append(self.pj[cfg.OBSERVATIONS][self.lw.item(0).text()].get("date", "").replace("T", " "))
        else:
            # TODO: check if date is the same for all selected obs
            col1.append("NA, observations grouped")

        # description
        if self.lw.count() == 1:
            col1.append(util.eol2space(self.pj[cfg.OBSERVATIONS][self.lw.item(0).text()].get(cfg.DESCRIPTION, "")))
        else:
            col1.append("NA, observations grouped")

        # indep var values
        for idx in self.pj.get(cfg.INDEPENDENT_VARIABLES, []):
            if self.lw.count() == 1:
                # var has value in obs?
                if self.pj[cfg.INDEPENDENT_VARIABLES][idx]["label"] in self.pj[cfg.OBSERVATIONS][self.lw.item(0).text()].get(
                    cfg.INDEPENDENT_VARIABLES, []
                ):
                    col1.append(
                        self.pj[cfg.OBSERVATIONS][self.lw.item(0).text()][cfg.INDEPENDENT_VARIABLES][
                            self.pj[cfg.INDEPENDENT_VARIABLES][idx]["label"]
                        ]
                    )
                else:
                    col1.append("")
            else:
                # TODO: check if var value is the same for all selected obs
                col1.append("NA, observations grouped")

        if self.time_interval == cfg.TIME_ARBITRARY_INTERVAL:
            col1.extend([f"{self.min_time:0.3f}", f"{self.max_time:0.3f}", f"{self.max_time - self.min_time:0.3f}"])

        if self.time_interval == cfg.TIME_FULL_OBS:
            col1.extend(["Full observation", "Full observation", "Full observation"])

        if self.time_interval == cfg.TIME_EVENTS:
            col1.extend(["Limited to coded events", "Limited to coded events", "Limited to coded events"])

        for row_idx in range(self.twTB.rowCount()):
            values = []
            for col_idx in range(self.twTB.columnCount()):
                values.append(util.intfloatstr(self.twTB.item(row_idx, col_idx).text()))
            rows.append(col1 + values)

        """
        else:
            # observations list
            obs_header = ["Observation id", "Observation date", "Description"]

            # indep var
            obs_header.extend(
                [self.pj[cfg.INDEPENDENT_VARIABLES][idx]["label"] for idx in self.pj[cfg.INDEPENDENT_VARIABLES]]
            )

            obs_header.extend(["Time budget start", "Time budget stop", "Time budget duration"])

            obs_rows = []
            obs_rows.append(obs_header)
            for idx in range(self.lw.count()):
                row = []
                # obs id
                row.append(self.lw.item(idx).text())
                row.append(self.pj[cfg.OBSERVATIONS][self.lw.item(idx).text()].get("date", ""))
                row.append(util.eol2space(self.pj[cfg.OBSERVATIONS][self.lw.item(idx).text()].get(cfg.DESCRIPTION, "")))

                for idx2 in self.pj.get(cfg.INDEPENDENT_VARIABLES, []):
                    # var has value in obs?
                    if self.pj[cfg.INDEPENDENT_VARIABLES][idx2]["label"] in self.pj[cfg.OBSERVATIONS][
                        self.lw.item(idx).text()
                    ].get(cfg.INDEPENDENT_VARIABLES, []):
                        row.append(
                            self.pj[cfg.OBSERVATIONS][self.lw.item(idx).text()][cfg.INDEPENDENT_VARIABLES][
                                self.pj[cfg.INDEPENDENT_VARIABLES][idx2]["label"]
                            ]
                        )
                    else:
                        row.append("")
                # start stop duration
                row.extend([f"{self.min_time:0.3f}", f"{self.max_time:0.3f}", f"{self.max_time - self.min_time:0.3f}"])

                obs_rows.append(row)

            # write file with observations information
            data = tablib.Dataset()
            data.title = "Time budget - Observations information"

            for row in obs_rows:
                data.append(complete(row, max([len(r) for r in obs_rows])))

            with open(pl.Path(file_name).with_suffix(f".observations_info.{cfg.FILE_NAME_SUFFIX[filter_]}"), "wb") as f:
                if filter_ in [cfg.TSV, cfg.CSV, cfg.HTML]:
                    f.write(str.encode(data.export(cfg.FILE_NAME_SUFFIX[filter_])))
                if filter_ in [cfg.ODS, cfg.XLSX, cfg.XLS]:
                    f.write(data.export(cfg.FILE_NAME_SUFFIX[filter_]))
        """

        """
            rows.append(["Observations:"])
            for idx in range(self.lw.count()):
                rows.append([""])
                rows.append(["Observation id", self.lw.item(idx).text()])
                rows.append(["Observation date", self.pj[cfg.OBSERVATIONS][self.lw.item(idx).text()].get("date", "")])
                rows.append(
                    [
                        "Description",
                        util.eol2space(self.pj[cfg.OBSERVATIONS][self.lw.item(idx).text()].get(cfg.DESCRIPTION, "")),
                    ]
                )

                if cfg.INDEPENDENT_VARIABLES in self.pj[cfg.OBSERVATIONS][self.lw.item(idx).text()]:
                    rows.append(["Independent variables:"])
                    for var in self.pj[cfg.OBSERVATIONS][self.lw.item(idx).text()][cfg.INDEPENDENT_VARIABLES]:
                        rows.append(
                            [var, self.pj[cfg.OBSERVATIONS][self.lw.item(idx).text()][cfg.INDEPENDENT_VARIABLES][var]]
                        )

            if self.excluded_behaviors_list.text():
                s1, s2 = self.excluded_behaviors_list.text().split(": ")
                rows.extend([[""], [s1] + s2.split(", ")])

            rows.extend([[""], [""], ["Time budget:"]])


            # write header

            header = [self.twTB.horizontalHeaderItem(col_idx).text() for col_idx in range(self.twTB.columnCount())]
            rows.append(header)

            for row in range(self.twTB.rowCount()):
                values = []
                for col_idx in range(self.twTB.columnCount()):
                    values.append(util.intfloatstr(self.twTB.item(row, col_idx).text()))
                rows.append(values)
        """

        data = tablib.Dataset()
        data.title = "Time budget"

        for row in rows:
            data.append(complete(row, max([len(r) for r in rows])))

        if filter_ in (cfg.PANDAS_DF, cfg.RDS):
            pass

            # build pandas dataframe from the tsv export of tablib dataset
            dtype = {
                "Observation id": str,
                "Observation date": str,
                "Description": str,
                "Time budget start": str,
                "Time budget stop": str,
                "Time budget duration": str,
                "Subject": str,
                "Behavior": str,
                "Modifiers": str,
                "Total number of occurences": float,
                "Total duration (s)": float,
                "Duration mean (s)": float,
                "Duration std dev": float,
                "inter-event intervals mean (s)": float,
                "inter-event intervals std dev": float,
                "% of total length	": float,
            }

            # indep var values
            for idx in self.pj.get(cfg.INDEPENDENT_VARIABLES, []):
                if self.pj[cfg.INDEPENDENT_VARIABLES][idx]["type"] == "numeric":
                    dtype[self.pj[cfg.INDEPENDENT_VARIABLES][idx]["label"]] = float
                else:
                    dtype[self.pj[cfg.INDEPENDENT_VARIABLES][idx]["label"]] = str

            df = pd.read_csv(
                StringIO(data.export("tsv")),
                sep="\t",
                dtype=dtype,
                parse_dates=[1],
            )

            if filter_ == cfg.PANDAS_DF:
                df.to_pickle(file_name)

            if flag_pyreadr_loaded and filter_ == cfg.RDS:
                pyreadr.write_rds(file_name, df)

            return

        # write results
        with open(file_name, "wb") as f:
            if filter_ in (cfg.TSV, cfg.CSV, cfg.HTML, cfg.TEXT_FILE):
                f.write(str.encode(data.export(cfg.FILE_NAME_SUFFIX[filter_])))
            if filter_ in (cfg.ODS, cfg.XLSX, cfg.XLS):
                f.write(data.export(cfg.FILE_NAME_SUFFIX[filter_]))


def time_budget(self, mode: str, mode2: str = "list"):
    """
    time budget (by behavior or category)

    Args:
        mode (str): ["by_behavior", "by_category"]
        mode2 (str): must be in ["list", "current"]
    """

    if mode2 == "current":
        if self.observationId:
            selected_observations = [self.observationId]
        else:
            return

    if mode2 == "list":
        _, selected_observations = select_observations.select_observations2(self, mode=cfg.MULTIPLE, windows_title="")

        if not selected_observations:
            return

    # check if coded behaviors are defined in ethogram
    if project_functions.check_coded_behaviors_in_obs_list(self.pj, selected_observations):
        return

    # check if state events are paired
    not_ok, selected_observations = project_functions.check_state_events(self.pj, selected_observations)
    if not_ok or not selected_observations:
        return

    flagGroup: bool = False
    if len(selected_observations) > 1:
        flagGroup = (
            dialog.MessageDialog(cfg.programName, "Group the selected observations in a single time budget analysis?", [cfg.YES, cfg.NO])
            == cfg.YES
        )

    max_media_duration_all_obs, total_media_duration_all_obs = observation_operations.media_duration(
        self.pj[cfg.OBSERVATIONS], selected_observations
    )

    logging.debug(f"max_media_duration_all_obs: {max_media_duration_all_obs}, total_media_duration_all_obs={total_media_duration_all_obs}")

    start_coding, end_coding, _ = observation_operations.coding_time(self.pj[cfg.OBSERVATIONS], selected_observations)

    parameters: dict = select_subj_behav.choose_obs_subj_behav_category(
        self,
        selected_observations,
        start_coding=start_coding,
        end_coding=end_coding,
        maxTime=max_media_duration_all_obs,
        by_category=(mode == "by_category"),
        n_observations=len(selected_observations),
    )
    if parameters == {}:
        return

    if not parameters[cfg.SELECTED_SUBJECTS] or not parameters[cfg.SELECTED_BEHAVIORS]:
        QMessageBox.warning(None, cfg.programName, "Select subject(s) and behavior(s) to analyze")
        return

    logging.debug(f"{parameters=}")

    # ask for excluding behaviors durations from total time
    if start_coding is not None and not start_coding.is_nan():
        cancel_pressed, parameters[cfg.EXCLUDED_BEHAVIORS] = self.filter_behaviors(
            title="Select behaviors to exclude from the total time",
            text=("The duration of the selected behaviors will " "be subtracted from the total time"),
            table="",
            behavior_type=[cfg.STATE_EVENT],
        )
        if cancel_pressed:
            return
    else:
        parameters[cfg.EXCLUDED_BEHAVIORS] = []

    self.statusbar.showMessage(f"Generating time budget for {len(selected_observations)} observation(s)")
    QApplication.processEvents()

    # check if time_budget window must be used
    if flagGroup or len(selected_observations) == 1:
        t0 = time.time()

        cursor = db_functions.load_events_in_db(
            self.pj,
            parameters[cfg.SELECTED_SUBJECTS],
            selected_observations,
            parameters[cfg.SELECTED_BEHAVIORS],
            time_interval=cfg.TIME_FULL_OBS,
        )

        """
        cursor.execute("SELECT code, occurence, type FROM events ")
        print()
        for row in cursor.fetchall():
            print(row["code"], row["occurence"], row["type"])
        print()
        """

        total_observation_time = 0
        for obsId in selected_observations:
            obs_length = observation_operations.observation_total_length(self.pj[cfg.OBSERVATIONS][obsId])

            if obs_length == dec(-1):  # media length not available
                parameters[cfg.TIME_INTERVAL] = cfg.TIME_EVENTS

            if obs_length == dec(-2):  # images obs without time
                parameters[cfg.TIME_INTERVAL] = cfg.TIME_EVENTS

            if parameters[cfg.TIME_INTERVAL] == cfg.TIME_FULL_OBS:  # media file duration
                min_time = float(0)
                # check if the last event is recorded after media file length
                try:
                    if float(self.pj[cfg.OBSERVATIONS][obsId][cfg.EVENTS][-1][0]) > float(obs_length):
                        max_time = float(self.pj[cfg.OBSERVATIONS][obsId][cfg.EVENTS][-1][0])
                    else:
                        max_time = float(obs_length)
                except Exception:
                    max_time = float(obs_length)

            if parameters[cfg.TIME_INTERVAL] == cfg.TIME_EVENTS:  # events duration
                try:
                    min_time = float(self.pj[cfg.OBSERVATIONS][obsId][cfg.EVENTS][0][0])  # first event
                except Exception:
                    min_time = float(0)
                try:
                    max_time = float(self.pj[cfg.OBSERVATIONS][obsId][cfg.EVENTS][-1][0])  # last event
                except Exception:
                    # TODO: set to 0 if no events ?
                    max_time = float(obs_length)

            if parameters[cfg.TIME_INTERVAL] == cfg.TIME_ARBITRARY_INTERVAL:
                min_time = float(parameters[cfg.START_TIME])
                max_time = float(parameters[cfg.END_TIME])

                # check intervals
                for subj in parameters[cfg.SELECTED_SUBJECTS]:
                    for behav in parameters[cfg.SELECTED_BEHAVIORS]:
                        if cfg.POINT in self.eventType(behav).upper():
                            continue
                        # extract modifiers

                        cursor.execute(
                            "SELECT distinct modifiers FROM events WHERE observation = ? AND subject = ? AND code = ?",
                            (obsId, subj, behav),
                        )
                        distinct_modifiers = list(cursor.fetchall())

                        # logging.debug("distinct_modifiers: {}".format(distinct_modifiers))

                        for modifier in distinct_modifiers:
                            # logging.debug("modifier #{}#".format(modifier[0]))

                            # insert events at boundaries of time interval
                            if (
                                len(
                                    cursor.execute(
                                        (
                                            "SELECT * FROM events "
                                            "WHERE observation = ? AND subject = ? AND code = ? AND modifiers = ? "
                                            "AND occurence < ?"
                                        ),
                                        (obsId, subj, behav, modifier[0], min_time),
                                    ).fetchall()
                                )
                                % 2
                            ):
                                cursor.execute(
                                    ("INSERT INTO events (observation, subject, code, type, modifiers, occurence) VALUES (?,?,?,?,?,?)"),
                                    (obsId, subj, behav, "STATE", modifier[0], min_time),
                                )

                            if (
                                len(
                                    cursor.execute(
                                        (
                                            "SELECT * FROM events WHERE observation = ? AND subject = ? AND code = ? "
                                            "AND modifiers = ? AND occurence > ?"
                                        ),
                                        (obsId, subj, behav, modifier[0], max_time),
                                    ).fetchall()
                                )
                                % 2
                            ):
                                cursor.execute(
                                    ("INSERT INTO events (observation, subject, code, type, modifiers, occurence) " "VALUES (?,?,?,?,?,?)"),
                                    (obsId, subj, behav, "STATE", modifier[0], max_time),
                                )
                        try:
                            cursor.execute("COMMIT")
                        except Exception:
                            pass

            total_observation_time += max_time - min_time

            # delete all events out of time interval from db
            cursor.execute(
                "DELETE FROM events WHERE observation = ? AND (occurence < ? OR occurence > ?)",
                (obsId, min_time, max_time),
            )
            try:
                cursor.execute("COMMIT")
            except Exception:
                pass

            """
            cursor.execute("SELECT code, occurence, type FROM events WHERE observation = ?", (obsId,))
            print()
            for row in cursor.fetchall():
                print(row["code"], row["occurence"], row["type"])
            print()
            """

        out, categories = time_budget_functions.time_budget_analysis(
            self.pj[cfg.ETHOGRAM], cursor, selected_observations, parameters, by_category=(mode == "by_category")
        )

        # check excluded behaviors
        excl_behaviors_total_time = {}
        for element in out:
            if element["subject"] not in excl_behaviors_total_time:
                excl_behaviors_total_time[element["subject"]] = 0
            if element["behavior"] in parameters[cfg.EXCLUDED_BEHAVIORS]:
                excl_behaviors_total_time[element["subject"]] += element["duration"] if not isinstance(element["duration"], str) else 0

        # widget for results visualization
        self.tb = timeBudgetResults(self.pj, self.config_param)

        # add min and max time
        self.tb.time_interval = parameters[cfg.TIME_INTERVAL]
        self.tb.min_time = min_time
        self.tb.max_time = max_time

        # observations list
        self.tb.label.setText("Selected observations")
        for obs_id in selected_observations:
            # self.tb.lw.addItem(f"{obs_id}  {self.pj[OBSERVATIONS][obs_id]['date']}  {self.pj[OBSERVATIONS][obs_id]['description']}")
            self.tb.lw.addItem(obs_id)

        # media length
        if len(selected_observations) > 1:
            if total_observation_time:
                if self.timeFormat == cfg.HHMMSS:
                    self.tb.lbTotalObservedTime.setText(f"Total observation length: {util.seconds2time(total_observation_time)}")
                if self.timeFormat == cfg.S:
                    self.tb.lbTotalObservedTime.setText(f"Total observation length: {float(total_observation_time):0.3f}")
            else:
                self.tb.lbTotalObservedTime.setText("Total observation length: not available")
        else:
            if self.timeFormat == cfg.HHMMSS:
                self.tb.lbTotalObservedTime.setText(f"Analysis from {util.seconds2time(min_time)} to {util.seconds2time(max_time)}")
            if self.timeFormat == cfg.S:
                self.tb.lbTotalObservedTime.setText(f"Analysis from {float(min_time):0.3f} to {float(max_time):0.3f} s")

        # behaviors excluded from total time
        if parameters[cfg.EXCLUDED_BEHAVIORS]:
            self.tb.excluded_behaviors_list.setText(
                "Behaviors excluded from total time: " + (", ".join(parameters[cfg.EXCLUDED_BEHAVIORS]))
            )
        else:
            self.tb.excluded_behaviors_list.setVisible(False)

        self.statusbar.showMessage(f"Time budget generated in {round(time.time() - t0, 3)} s")
        logging.debug("Time budget generated", 5000)

        if mode == "by_behavior":
            tb_fields = [
                "Subject",
                "Behavior",
                "Modifiers",
                "Total number of occurences",
                "Total duration (s)",
                "Duration mean (s)",
                "Duration std dev",
                "inter-event intervals mean (s)",
                "inter-event intervals std dev",
                "% of total length",
            ]
            fields = [
                "subject",
                "behavior",
                "modifiers",
                "number",
                "duration",
                "duration_mean",
                "duration_stdev",
                "inter_duration_mean",
                "inter_duration_stdev",
            ]

            self.tb.twTB.setColumnCount(len(tb_fields))
            self.tb.twTB.setHorizontalHeaderLabels(tb_fields)

            for row in out:
                self.tb.twTB.setRowCount(self.tb.twTB.rowCount() + 1)
                column = 0
                for field in fields:
                    if isinstance(row[field], float):
                        item = QTableWidgetItem(f"{row[field]:.3f}")
                    else:
                        item = QTableWidgetItem(str(row[field]).replace(" ()", ""))
                    # no modif allowed
                    item.setFlags(Qt.ItemIsEnabled)
                    self.tb.twTB.setItem(self.tb.twTB.rowCount() - 1, column, item)
                    column += 1

                # % of total time
                if row["duration"] in (0, cfg.NA):
                    item = QTableWidgetItem(str(row["duration"]))
                elif row["duration"] not in ("-", cfg.UNPAIRED) and not start_coding.is_nan():
                    tot_time = float(total_observation_time)
                    # substract time of excluded behaviors from the total for the subject
                    if row["subject"] in excl_behaviors_total_time and row["behavior"] not in parameters[cfg.EXCLUDED_BEHAVIORS]:
                        tot_time -= excl_behaviors_total_time[row["subject"]]
                    item = QTableWidgetItem(f"{row['duration'] / tot_time * 100:.1f}" if tot_time > 0 else cfg.NA)

                else:
                    item = QTableWidgetItem("-")

                item.setFlags(Qt.ItemIsEnabled)
                self.tb.twTB.setItem(self.tb.twTB.rowCount() - 1, column, item)

        if mode == "by_category":
            tb_fields = ["Subject", "Category", "Total number", "Total duration (s)"]
            fields = ["number", "duration"]

            self.tb.twTB.setColumnCount(len(tb_fields))
            self.tb.twTB.setHorizontalHeaderLabels(tb_fields)

            for subject in categories:
                for category in categories[subject]:
                    self.tb.twTB.setRowCount(self.tb.twTB.rowCount() + 1)

                    column = 0
                    item = QTableWidgetItem(subject)
                    item.setFlags(Qt.ItemIsEnabled)
                    self.tb.twTB.setItem(self.tb.twTB.rowCount() - 1, column, item)

                    column = 1
                    if category == "":
                        item = QTableWidgetItem("No category")
                    else:
                        item = QTableWidgetItem(category)
                    item.setFlags(Qt.ItemIsEnabled)
                    self.tb.twTB.setItem(self.tb.twTB.rowCount() - 1, column, item)

                    for field in fields:
                        column += 1

                        if field == "duration":
                            try:
                                item = QTableWidgetItem(f"{categories[subject][category][field]:0.3f}")
                            except Exception:
                                item = QTableWidgetItem(categories[subject][category][field])
                        else:
                            item = QTableWidgetItem(str(categories[subject][category][field]))
                        item.setFlags(Qt.ItemIsEnabled)
                        item.setTextAlignment(Qt.AlignRight | Qt.AlignVCenter)
                        self.tb.twTB.setItem(self.tb.twTB.rowCount() - 1, column, item)

        self.tb.twTB.resizeColumnsToContents()

        gui_utilities.restore_geometry(self.tb, "time budget", (0, 0))

        self.tb.show()

    if not flagGroup and len(selected_observations) > 1:
        output_format, ok = QInputDialog.getItem(
            self,
            "Time budget analysis format",
            "Available formats",
            (
                cfg.TSV,
                cfg.CSV,
                cfg.ODS,
                cfg.ODS_WB,
                cfg.XLSX,
                cfg.XLSX_WB,
                cfg.HTML,
                cfg.XLS,
            ),
            0,
            False,
        )
        if not ok:
            return

        extension = cfg.FILE_NAME_SUFFIX[output_format]

        if output_format in (cfg.ODS_WB, cfg.XLSX_WB):
            workbook = tablib.Databook()

            wb_file_name, filter_ = QFileDialog(self).getSaveFileName(self, "Save Time budget analysis", "", output_format)
            if not wb_file_name:
                return

            if pl.Path(wb_file_name).suffix != f".{cfg.FILE_NAME_SUFFIX[filter_]}":
                wb_file_name = str(pl.Path(wb_file_name)) + "." + cfg.FILE_NAME_SUFFIX[filter_]
                # check if file with new extension already exists
                if pl.Path(wb_file_name).is_file():
                    if (
                        dialog.MessageDialog(cfg.programName, f"The file {wb_file_name} already exists.", [cfg.CANCEL, cfg.OVERWRITE])
                        == cfg.CANCEL
                    ):
                        return

        else:  # not workbook
            exportDir = QFileDialog(self).getExistingDirectory(
                self,
                "Choose a directory to save the time budget analysis",
                os.path.expanduser("~"),
                options=QFileDialog.ShowDirsOnly,
            )
            if not exportDir:
                return

        if mode == "by_behavior":
            tb_fields = [
                "Subject",
                "Behavior",
                "Modifiers",
                "Total number of occurences",
                "Total duration (s)",
                "Duration mean (s)",
                "Duration std dev",
                "inter-event intervals mean (s)",
                "inter-event intervals std dev",
                "% of total length",
            ]
            fields = [
                "subject",
                "behavior",
                "modifiers",
                "number",
                "duration",
                "duration_mean",
                "duration_stdev",
                "inter_duration_mean",
                "inter_duration_stdev",
            ]

        if mode == "by_category":
            tb_fields = ["Subject", "Category", "Total number of occurences", "Total duration (s)"]
            fields = ["subject", "category", "number", "duration"]

        mem_command = ""
        for obsId in selected_observations:
            cursor = db_functions.load_events_in_db(self.pj, parameters[cfg.SELECTED_SUBJECTS], [obsId], parameters[cfg.SELECTED_BEHAVIORS])

            obs_length = observation_operations.observation_total_length(self.pj[cfg.OBSERVATIONS][obsId])

            if obs_length == -1:
                obs_length = 0

            if parameters[cfg.TIME_INTERVAL] == cfg.TIME_FULL_OBS:
                min_time = float(0)
                # check if the last event is recorded after media file length
                try:
                    if float(self.pj[cfg.OBSERVATIONS][obsId][cfg.EVENTS][-1][0]) > float(obs_length):
                        max_time = float(self.pj[cfg.OBSERVATIONS][obsId][cfg.EVENTS][-1][0])
                    else:
                        max_time = float(obs_length)
                except Exception:
                    max_time = float(obs_length)

            if parameters[cfg.TIME_INTERVAL] == cfg.TIME_EVENTS:
                try:
                    min_time = float(self.pj[cfg.OBSERVATIONS][obsId][cfg.EVENTS][0][0])
                except Exception:
                    min_time = float(0)
                try:
                    max_time = float(self.pj[cfg.OBSERVATIONS][obsId][cfg.EVENTS][-1][0])
                except Exception:
                    max_time = float(obs_length)

            if parameters[cfg.TIME_INTERVAL] == cfg.TIME_ARBITRARY_INTERVAL:
                min_time = float(parameters[cfg.START_TIME])
                max_time = float(parameters[cfg.END_TIME])

                # check intervals
                for subj in parameters[cfg.SELECTED_SUBJECTS]:
                    for behav in parameters[cfg.SELECTED_BEHAVIORS]:
                        if cfg.POINT in project_functions.event_type(behav, self.pj[cfg.ETHOGRAM]):  # self.eventType(behav).upper():
                            continue
                        # extract modifiers
                        # if plot_parameters["include modifiers"]:

                        cursor.execute(
                            "SELECT distinct modifiers FROM events WHERE observation = ? AND subject = ? AND code = ?",
                            (obsId, subj, behav),
                        )
                        distinct_modifiers = list(cursor.fetchall())

                        for modifier in distinct_modifiers:
                            if (
                                len(
                                    cursor.execute(
                                        (
                                            "SELECT * FROM events "
                                            "WHERE observation = ? AND subject = ? "
                                            "AND code = ? AND modifiers = ? AND occurence < ?"
                                        ),
                                        (obsId, subj, behav, modifier[0], min_time),
                                    ).fetchall()
                                )
                                % 2
                            ):
                                cursor.execute(
                                    ("INSERT INTO events (observation, subject, code, type, modifiers, occurence) " "VALUES (?,?,?,?,?,?)"),
                                    (obsId, subj, behav, "STATE", modifier[0], min_time),
                                )
                            if (
                                len(
                                    cursor.execute(
                                        (
                                            "SELECT * FROM events WHERE observation = ? AND subject = ? AND code = ?"
                                            " AND modifiers = ? AND occurence > ?"
                                        ),
                                        (obsId, subj, behav, modifier[0], max_time),
                                    ).fetchall()
                                )
                                % 2
                            ):
                                cursor.execute(
                                    ("INSERT INTO events (observation, subject, code, type, modifiers, occurence) " "VALUES (?,?,?,?,?,?)"),
                                    (obsId, subj, behav, cfg.STATE, modifier[0], max_time),
                                )
                        try:
                            cursor.execute("COMMIT")
                        except Exception:
                            pass

            cursor.execute(
                "DELETE FROM events WHERE observation = ? AND (occurence < ? OR occurence > ?)",
                (obsId, min_time, max_time),
            )

            out, categories = time_budget_functions.time_budget_analysis(
                self.pj[cfg.ETHOGRAM], cursor, [obsId], parameters, by_category=(mode == "by_category")
            )

            # check excluded behaviors
            excl_behaviors_total_time = {}
            for element in out:
                if element["subject"] not in excl_behaviors_total_time:
                    excl_behaviors_total_time[element["subject"]] = 0
                if element["behavior"] in parameters[cfg.EXCLUDED_BEHAVIORS]:
                    excl_behaviors_total_time[element["subject"]] += element["duration"] if element["duration"] != "NA" else 0

            rows: list = []
            col1: list = []
            # observation id
            col1.append(obsId)
            col1.append(self.pj[cfg.OBSERVATIONS][obsId].get("date", "").replace("T", ""))
            col1.append(util.eol2space(self.pj[cfg.OBSERVATIONS][obsId].get(cfg.DESCRIPTION, "")))
            header = ["Observation id", "Observation date", "Description"]

            indep_var_label: list = []
            indep_var_values: list = []
            for _, v in self.pj.get(cfg.INDEPENDENT_VARIABLES, {}).items():
                indep_var_label.append(v["label"])
                indep_var_values.append(self.pj[cfg.OBSERVATIONS][obsId].get(cfg.INDEPENDENT_VARIABLES, {}).get(v["label"], ""))

            header.extend(indep_var_label)
            col1.extend(indep_var_values)

            # interval analysis
            if dec(min_time).is_nan():  # check if observation has timestamp
                col1.extend([cfg.NA, cfg.NA, cfg.NA])
            else:
                col1.extend([f"{min_time:0.3f}", f"{max_time:0.3f}", f"{max_time - min_time:0.3f}"])
            header.extend(["Time budget start", "Time budget stop", "Time budget duration"])

            if mode == "by_behavior":
                # header
                rows.append(header + tb_fields)

                for row in out:
                    values = []
                    for field in fields:
                        values.append(str(row[field]).replace(" ()", ""))
                    # % of total time
                    if row["duration"] in (0, cfg.NA):
                        values.append(row["duration"])
                    elif row["duration"] not in ("-", cfg.UNPAIRED) and not start_coding.is_nan():
                        tot_time = float(max_time - min_time)
                        # substract duration of excluded behaviors from total time for each subject
                        if row["subject"] in excl_behaviors_total_time and row["behavior"] not in parameters[cfg.EXCLUDED_BEHAVIORS]:
                            tot_time -= excl_behaviors_total_time[row["subject"]]
                        # % of tot time
                        values.append(round(row["duration"] / tot_time * 100, 1) if tot_time > 0 else cfg.NA)
                    else:
                        values.append("-")

                    rows.append(col1 + values)

            if mode == "by_category":
                rows.append(header + tb_fields)

                for subject in categories:
                    for category in categories[subject]:
                        values = []
                        values.append(subject)
                        if category == "":
                            values.append("No category")
                        else:
                            values.append(category)

                        values.append(categories[subject][category]["number"])
                        try:
                            values.append(f"{categories[subject][category]['duration']:0.3f}")
                        except Exception:
                            values.append(categories[subject][category]["duration"])

                        rows.append(col1 + values)

            data = tablib.Dataset()
            data.title = obsId
            for row in rows:
                data.append(util.complete(row, max([len(r) for r in rows])))

            # check worksheet/workbook title for forbidden char (excel)
            data.title = util.safe_xl_worksheet_title(data.title, extension)

            if output_format in (cfg.ODS_WB, cfg.XLSX_WB):
                workbook.add_sheet(data)

            else:
                file_name = f"{pl.Path(exportDir) / pl.Path(util.safeFileName(obsId))}.{extension}"
                if mem_command != cfg.OVERWRITE_ALL and pl.Path(file_name).is_file():
                    if mem_command == "Skip all":
                        continue
                    mem_command = dialog.MessageDialog(
                        cfg.programName,
                        f"The file {file_name} already exists.",
                        [cfg.OVERWRITE, cfg.OVERWRITE_ALL, cfg.SKIP, cfg.SKIP_ALL, cfg.CANCEL],
                    )
                    if mem_command == cfg.CANCEL:
                        return
                    if mem_command in (cfg.SKIP, cfg.SKIP_ALL):
                        continue

                with open(file_name, "wb") as f:
                    if output_format in (cfg.TSV, cfg.CSV, cfg.HTML):
                        f.write(str.encode(data.export(cfg.FILE_NAME_SUFFIX[output_format])))

                    if output_format in (cfg.ODS, cfg.XLSX, cfg.XLS):
                        f.write(data.export(cfg.FILE_NAME_SUFFIX[output_format]))

        if output_format == cfg.XLSX_WB:
            with open(wb_file_name, "wb") as f:
                f.write(workbook.xlsx)
        if output_format == cfg.ODS_WB:
            with open(wb_file_name, "wb") as f:
                f.write(workbook.ods)
