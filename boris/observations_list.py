"""
BORIS
Behavioral Observation Research Interactive Software
Copyright 2012-2025 Olivier Friard


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

from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QTableWidgetItem,
    QLabel,
    QLineEdit,
    QTableWidget,
    QAbstractItemView,
    QComboBox,
    QGridLayout,
    QHBoxLayout,
    QSpacerItem,
    QPushButton,
    QDialog,
    QSizePolicy,
)

from . import config as cfg
from . import dialog

commands_index = {"Start": 2, "Edit": 3, "View": 4}


class MyTableWidgetItem(QTableWidgetItem):
    def __init__(self, text, sortKey):
        QTableWidgetItem.__init__(self, text, QTableWidgetItem.UserType)
        self.sortKey = sortKey

    # Qt uses a simple < check for sorting items, override this to use the sortKey
    def __lt__(self, other):
        if isinstance(self.sortKey, str) and isinstance(other.sortKey, str):
            return self.sortKey.lower() < other.sortKey.lower()
        else:
            return self.sortKey < other.sortKey


class observationsList_widget(QDialog):
    def __init__(
        self,
        data: list,
        header: list,
        column_type: list,
        not_paired: list = [],
        parent=None,
    ):
        super(observationsList_widget, self).__init__(parent)

        self.data = data
        self.not_paired = not_paired
        self.column_type = column_type

        self.setWindowTitle(f"Observations list - {cfg.programName}")
        self.label = QLabel("")

        self.mode = cfg.SINGLE

        self.lineEdit = QLineEdit(self)
        self.lineEdit.textChanged.connect(self.view_filter)
        self.view = QTableWidget(self)
        self.view.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.view.setSortingEnabled(True)

        self.comboBox = QComboBox(self)
        self.comboBox.currentIndexChanged.connect(self.view_filter)

        self.cbLogic = QComboBox(self)
        self.cbLogic.addItems(
            [
                "contains",
                "does not contain",
                "=",
                "!=",
                ">",
                "<",
                ">=",
                "<=",
                "between (use and to separate terms)",
            ]
        )
        self.cbLogic.currentIndexChanged.connect(self.view_filter)

        self.label = QLabel(self)

        self.gridLayout = QGridLayout(self)
        self.gridLayout.addWidget(self.label, 0, 0, 1, 3)
        self.gridLayout.addWidget(self.comboBox, 1, 0, 1, 1)
        self.gridLayout.addWidget(self.cbLogic, 1, 1, 1, 1)
        self.gridLayout.addWidget(self.lineEdit, 1, 2, 1, 1)

        self.gridLayout.addWidget(self.view, 2, 0, 1, 3)

        hbox2 = QHBoxLayout()

        spacerItem = QSpacerItem(241, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)
        hbox2.addItem(spacerItem)

        self.pbSelectAll = QPushButton("Select all")
        self.pbSelectAll.clicked.connect(lambda: self.pbSelection_clicked("select"))
        hbox2.addWidget(self.pbSelectAll)

        self.pbUnSelectAll = QPushButton("Unselect all")
        self.pbUnSelectAll.clicked.connect(lambda: self.pbSelection_clicked("unselect"))
        hbox2.addWidget(self.pbUnSelectAll)

        self.pbCancel = QPushButton(cfg.CANCEL, clicked=self.pbCancel_clicked)
        hbox2.addWidget(self.pbCancel)

        self.pbOpen = QPushButton("Start", clicked=self.pbOpen_clicked)
        hbox2.addWidget(self.pbOpen)

        self.pbView = QPushButton("View", clicked=self.pbView_clicked)
        hbox2.addWidget(self.pbView)

        self.pbEdit = QPushButton("Edit", clicked=self.pbEdit_clicked)
        hbox2.addWidget(self.pbEdit)

        self.pbOk = QPushButton(cfg.OK, clicked=self.pbOk_clicked)
        hbox2.addWidget(self.pbOk)

        self.gridLayout.addLayout(hbox2, 3, 0, 1, 3)

        self.view.doubleClicked.connect(self.view_doubleClicked)

        self.view.setRowCount(len(self.data))
        if self.data:
            self.view.setColumnCount(len(self.data[0]))

        self.view.setHorizontalHeaderLabels(header)

        for r in range(len(self.data)):
            for c in range(len(self.data[0])):
                self.view.setItem(r, c, self.set_item(r, c))

        self.view.resizeColumnsToContents()

        self.comboBox.addItems(header)

        self.view.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.label.setText(f"{self.view.rowCount()} observation{'s' * (self.view.rowCount() > 1)}")

    def view_doubleClicked(self, index):
        if self.mode == cfg.MULTIPLE:
            return

        if self.mode == cfg.OPEN or self.mode == cfg.EDIT:
            self.done(2)
            return

        if self.mode == cfg.SELECT1:
            self.done(2)
            return

        response = dialog.MessageDialog(
            cfg.programName,
            "What do you want to do with this observation?",
            list(commands_index.keys()) + [cfg.CANCEL],
        )
        if response == cfg.CANCEL:
            return
        else:
            self.done(commands_index[response])

    def pbSelection_clicked(self, mode):
        """
        select or unselect all filtered observations
        """
        if mode == "select":
            self.view.selectAll()
        if mode == "unselect":
            self.view.clearSelection()

    def pbCancel_clicked(self):
        self.close()

    def pbOk_clicked(self):
        self.done(1)

    def pbOpen_clicked(self):
        self.done(2)

    def pbEdit_clicked(self):
        self.done(3)

    def pbView_clicked(self):
        self.done(4)

    def set_item(self, r, c):
        if self.column_type[c] == cfg.NUMERIC:
            try:
                item = MyTableWidgetItem(self.data[r][c], float(self.data[r][c]))
            except Exception:
                item = MyTableWidgetItem(self.data[r][c], 0)
        else:
            item = MyTableWidgetItem(self.data[r][c], self.data[r][c])

        # if obs_id in not_paired -> set background color to red
        if c == 0 and self.data[r][c] in self.not_paired:
            item.setBackground(QColor(255, 0, 0, 128))
            # item.setForeground(QBrush(QColor(0, 255, 0)))

        return item

    def view_filter(self):
        """
        filter
        """

        def str2float(s: str):
            """
            convert str in float or return str
            """
            try:
                return float(s)
            except Exception:
                return s

        def in_(s, lst):
            return s in lst

        def not_in(s, lst):
            return s not in lst

        def equal(s, x):
            x_num, s_num = str2float(x), str2float(s)
            if type(x_num) == type(s_num):
                return x_num == s_num
            else:
                return x == s

        def not_equal(s, x):
            x_num, s_num = str2float(x), str2float(s)
            if type(x_num) == type(s_num):
                return x_num != s_num
            else:
                return x != s

        def gt(s, x):
            x_num, s_num = str2float(x), str2float(s)
            if type(x_num) == type(s_num):
                return x_num > s_num
            else:
                return x > s

        def lt(s, x):
            x_num, s_num = str2float(x), str2float(s)
            if type(x_num) == type(s_num):
                return x_num < s_num
            else:
                return x < s

        def gt_or_equal(s, x):
            x_num, s_num = str2float(x), str2float(s)
            if type(x_num) == type(s_num):
                return x_num >= s_num
            else:
                return x >= s

        def lt_or_equal(s, x):
            x_num, s_num = str2float(x), str2float(s)
            if type(x_num) == type(s_num):
                return x_num <= s_num
            else:
                return x <= s

        def between(s, x):
            if len(s.split(" AND ")) != 2:
                return None
            s1, s2 = s.split(" AND ")
            s1_num, s2_num = str2float(s1), str2float(s2)
            if type(s1_num) != type(s2_num):
                return None
            x_num = str2float(x)
            if type(s1_num) == type(x_num):
                return s1_num <= x_num <= s2_num
            else:
                return s1 <= x <= s2

        if not self.lineEdit.text():
            self.view.setRowCount(len(self.data))

            for r in range(len(self.data)):
                for c in range(len(self.data[0])):
                    self.view.setItem(r, c, self.set_item(r, c))

        else:
            if self.cbLogic.currentText() == "contains":
                logic = in_
            if self.cbLogic.currentText() == "does not contain":
                logic = not_in
            if self.cbLogic.currentText() == "=":
                logic = equal
            if self.cbLogic.currentText() == "!=":
                logic = not_equal
            if self.cbLogic.currentText() == ">":
                logic = gt
            if self.cbLogic.currentText() == "<":
                logic = lt
            if self.cbLogic.currentText() == ">=":
                logic = gt_or_equal
            if self.cbLogic.currentText() == "<=":
                logic = lt_or_equal
            if "between" in self.cbLogic.currentText():
                logic = between

            self.view.setRowCount(0)
            search = self.lineEdit.text().upper()
            try:
                for r, row in enumerate(self.data):
                    if logic(search, row[self.comboBox.currentIndex()].upper()):
                        self.view.setRowCount(self.view.rowCount() + 1)
                        for c, _ in enumerate(row):
                            self.view.setItem(self.view.rowCount() - 1, c, self.set_item(r, c))
            except Exception:
                pass
        self.label.setText(f"{self.view.rowCount()} observation{'s' * (self.view.rowCount() > 1)}")
