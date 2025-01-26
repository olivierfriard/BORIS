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
from PySide6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QTableWidget,
    QSpacerItem,
    QAbstractItemView,
    QSizePolicy,
)


class ExclusionMatrix(QDialog):
    def __init__(self):
        super().__init__()

        hbox = QVBoxLayout(self)

        self.label = QLabel()
        self.label.setText(
            ("Check if behaviors are mutually exclusive.\n" "The Point events (displayed on blue background) cannot be excluded)")
        )
        hbox.addWidget(self.label)

        self.twExclusions = QTableWidget()
        self.twExclusions.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.twExclusions.setAlternatingRowColors(True)
        self.twExclusions.setEditTriggers(QAbstractItemView.NoEditTriggers)
        hbox.addWidget(self.twExclusions)

        hbox2 = QHBoxLayout()
        spacer_item = QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)
        hbox2.addItem(spacer_item)

        self.pb_select_all = QPushButton("Check all")
        self.pb_select_all.clicked.connect(lambda: self.pb_cb_selection("select"))
        hbox2.addWidget(self.pb_select_all)

        self.pb_unselect_all = QPushButton("Uncheck all")
        self.pb_unselect_all.clicked.connect(lambda: self.pb_cb_selection("unselect"))
        hbox2.addWidget(self.pb_unselect_all)

        self.pb_revert_selection = QPushButton("Revert check")
        self.pb_revert_selection.clicked.connect(lambda: self.pb_cb_selection("revert"))
        hbox2.addWidget(self.pb_revert_selection)

        self.pb_check_selected = QPushButton("Check selected")
        self.pb_check_selected.clicked.connect(lambda: self.pb_selected(True))
        hbox2.addWidget(self.pb_check_selected)

        self.pb_uncheck_selected = QPushButton("Uncheck selected")
        self.pb_uncheck_selected.clicked.connect(lambda: self.pb_selected(False))
        hbox2.addWidget(self.pb_uncheck_selected)

        self.pbCancel = QPushButton("Cancel")
        self.pbCancel.clicked.connect(self.reject)
        hbox2.addWidget(self.pbCancel)

        self.pbOK = QPushButton("OK", clicked=self.accept)
        hbox2.addWidget(self.pbOK)

        hbox.addLayout(hbox2)
        self.setLayout(hbox)

        self.setWindowTitle("Behaviors exclusion matrix")
        self.setGeometry(100, 100, 600, 400)

    def pb_selected(self, to_check: bool):
        """
        check/uncheck the checkbox in selected cells

        Args:
            to_check (boolean): True to check else False
        """
        for selected_range in self.twExclusions.selectedRanges():
            for row in range(selected_range.topRow(), selected_range.bottomRow() + 1):
                for column in range(self.twExclusions.columnCount()):
                    try:
                        self.twExclusions.cellWidget(row, column).setChecked(to_check)
                    except Exception:
                        logging.warning(f"Error during checking/unchecking for {row}/{column} in exclusion matrix")
        self.cb_clicked()

    def pb_cb_selection(self, mode):
        """
        button for checkbox selection/deselection and revert selection

        Args:
            mode (str): select, unselect, revert

        """

        for r in range(self.twExclusions.rowCount()):
            for c in range(self.twExclusions.columnCount()):
                if mode == "select":
                    state = True
                if mode == "unselect":
                    state = False
                try:
                    if mode == "revert":
                        state = not self.twExclusions.cellWidget(r, c).isChecked()
                    self.twExclusions.cellWidget(r, c).setChecked(state)
                except Exception:
                    logging.warning(f"Error during checking/unchecking for {r}/{c} in exclusion matrix")

    def cb_clicked(self):
        """
        de/select the corresponding checkbox
        """
        for r, r_name in enumerate(self.stateBehaviors + self.point_behaviors):
            for c, c_name in enumerate(self.stateBehaviors):
                if c_name != r_name:
                    try:
                        if f"{c_name}|{r_name}" in self.checkboxes:
                            self.checkboxes[f"{c_name}|{r_name}"].setChecked(self.checkboxes[f"{r_name}|{c_name}"].isChecked())
                    except Exception:
                        logging.warning(f"Error during checking/unchecking for {r_name}/{c_name} in exclusion matrix")
