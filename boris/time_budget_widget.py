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
import pathlib
import sys
from boris import utilities

import tablib
from PyQt5.QtWidgets import *

from boris import dialog
from boris.config import *
from boris import gui_utilities
from boris.utilities import intfloatstr


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
        #self.lw.setEnabled(False)
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

        self.pbClose = QPushButton("Close", clicked=self.close_clicked)
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

        def complete(l: list, max_: int) -> list:
            """
            complete list with empty string until len = max

            Args:
                l (list): list to complete
                max_ (int): length of the returned list

            Returns:
                list: completed list
            """

            while len(l) < max_:
                l.append("")
            return l

        logging.debug("save time budget results to file")

        extended_file_formats = ["Tab Separated Values (*.tsv)",
                                 "Comma Separated Values (*.csv)",
                                 "Open Document Spreadsheet ODS (*.ods)",
                                 "Microsoft Excel Spreadsheet XLSX (*.xlsx)",
                                 "Legacy Microsoft Excel Spreadsheet XLS (*.xls)",
                                 "HTML (*.html)"]
        file_formats = ["tsv", "csv", "ods", "xlsx", "xls", "html"]

        file_name, filter_ = QFileDialog().getSaveFileName(self, "Save Time budget analysis", "", ";;".join(extended_file_formats))

        if not file_name:
            return

        outputFormat = file_formats[extended_file_formats.index(filter_)]
        if pathlib.Path(file_name).suffix != "." + outputFormat:
            file_name = str(pathlib.Path(file_name)) + "." + outputFormat
            # check if file with new extension already exists
            if pathlib.Path(file_name).is_file():
                if dialog.MessageDialog(programName,
                                        f"The file {file_name} already exists.",
                                        [CANCEL, OVERWRITE]) == CANCEL:
                    return

        rows = []

        # 1 observation
        if (self.lw.count() == 1
                and self.config_param.get(TIME_BUDGET_FORMAT, DEFAULT_TIME_BUDGET_FORMAT ) == COMPACT_TIME_BUDGET_FORMAT):
            col1, indep_var_label = [], []
            # add obs id
            col1.append(self.lw.item(0).text())
            # add obs date
            col1.append(self.pj[OBSERVATIONS][self.lw.item(0).text()].get("date", ""))

            # description
            col1.append(utilities.eol2space(self.pj[OBSERVATIONS][self.lw.item(0).text()].get(DESCRIPTION, "")))
            header = ["Observation id", "Observation date", "Description"]

            # indep var
            for var in self.pj[OBSERVATIONS][self.lw.item(0).text()].get(INDEPENDENT_VARIABLES, {}):
                indep_var_label.append(var)
                col1.append(self.pj[OBSERVATIONS][self.lw.item(0).text()][INDEPENDENT_VARIABLES][var])

            header.extend(indep_var_label)

            col1.extend([f"{self.min_time:0.3f}", f"{self.max_time:0.3f}", f"{self.max_time - self.min_time:0.3f}"])
            header.extend(["Time budget start", "Time budget stop", "Time budget duration"])

            for col_idx in range(self.twTB.columnCount()):
                header.append(self.twTB.horizontalHeaderItem(col_idx).text())
            rows.append(header)

            for row_idx in range(self.twTB.rowCount()):
                values = []
                for col_idx in range(self.twTB.columnCount()):
                    values.append(intfloatstr(self.twTB.item(row_idx, col_idx).text()))
                rows.append(col1 + values)

        else:
            # observations list
            rows.append(["Observations:"])
            for idx in range(self.lw.count()):
                rows.append([""])
                rows.append(["Observation id", self.lw.item(idx).text()])
                rows.append(["Observation date", self.pj[OBSERVATIONS][self.lw.item(idx).text()].get("date", "")])
                rows.append(["Description", utilities.eol2space(self.pj[OBSERVATIONS][self.lw.item(idx).text()].get(DESCRIPTION, ""))])

                if INDEPENDENT_VARIABLES in self.pj[OBSERVATIONS][self.lw.item(idx).text()]:
                    rows.append(["Independent variables:"])
                    for var in self.pj[OBSERVATIONS][self.lw.item(idx).text()][INDEPENDENT_VARIABLES]:
                        rows.append([var, self.pj[OBSERVATIONS][self.lw.item(idx).text()][INDEPENDENT_VARIABLES][var]])

            if self.excluded_behaviors_list.text():
                s1, s2 = self.excluded_behaviors_list.text().split(": ")
                rows.extend([[""], [s1] + s2.split(", ")])

            rows.extend([[""], [""], ["Time budget:"]])

            # write header
            header = []
            for col_idx in range(self.twTB.columnCount()):
                header.append(self.twTB.horizontalHeaderItem(col_idx).text())

            rows.append(header)
            rows.append([""])

            for row in range(self.twTB.rowCount()):
                values = []
                for col_idx in range(self.twTB.columnCount()):
                    values.append(intfloatstr(self.twTB.item(row, col_idx).text()))

                rows.append(values)

        max_row_length = max([len(r) for r in rows])
        data = tablib.Dataset()
        data.title = "Time budget"

        for row in rows:
            data.append(complete(row, max_row_length))

        if outputFormat in ["tsv", "csv", "html"]:
            with open(file_name, "wb") as f:
                f.write(str.encode(data.export(outputFormat)))
            return

        if outputFormat in ["ods", "xlsx", "xls"]:
            with open(file_name, "wb") as f:
                f.write(data.export(outputFormat))
            return
