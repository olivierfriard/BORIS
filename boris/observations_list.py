#!/usr/bin/env python3

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

from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

from boris import config
from boris import dialog
from boris.utilities import *

commands_index = {"Start": 2, "Edit": 3, "View": 4}


class MyTableWidgetItem(QTableWidgetItem):
    def __init__(self, text, sortKey):
        QTableWidgetItem.__init__(self, text, QTableWidgetItem.UserType)
        self.sortKey = sortKey

    # Qt uses a simple < check for sorting items, override this to use the sortKey
    def __lt__(self, other):
        return self.sortKey < other.sortKey


class observationsList_widget(QDialog):

    def __init__(self, data: list, header: list, column_type: list, parent=None):

        super(observationsList_widget, self).__init__(parent)

        self.data = data
        self.column_type = column_type

        self.setWindowTitle(f"Observations list - {config.programName}")
        self.label = QLabel("")

        self.mode = config.SINGLE

        self.lineEdit = QLineEdit(self)
        self.lineEdit.textChanged.connect(self.view_filter)
        self.view = QTableWidget(self)
        self.view.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.view.setSortingEnabled(True)

        self.comboBox = QComboBox(self)
        self.comboBox.currentIndexChanged.connect(self.view_filter)

        self.cbLogic = QComboBox(self)
        self.cbLogic.addItems(["contains",
                               "does not contain",
                               "=",
                               "!=",
                               ">",
                               "<",
                               ">=",
                               "<=",
                               "between (use and to separate terms)"
                               ])
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

        self.pbCancel = QPushButton("Cancel", clicked=self.pbCancel_clicked)
        hbox2.addWidget(self.pbCancel)

        self.pbOpen = QPushButton("Start", clicked=self.pbOpen_clicked)
        hbox2.addWidget(self.pbOpen)

        self.pbView = QPushButton("View", clicked=self.pbView_clicked)
        hbox2.addWidget(self.pbView)

        self.pbEdit = QPushButton("Edit", clicked=self.pbEdit_clicked)
        hbox2.addWidget(self.pbEdit)

        self.pbOk = QPushButton("OK", clicked=self.pbOk_clicked)
        hbox2.addWidget(self.pbOk)

        self.gridLayout.addLayout(hbox2, 3, 0, 1, 3)

        self.view.doubleClicked.connect(self.view_doubleClicked)

        self.view.setRowCount(len(self.data))
        self.view.setColumnCount(len(self.data[0]))

        self.view.setHorizontalHeaderLabels(header)

        for r in range(len(self.data)):
            for c in range(len(self.data[0])):
                self.view.setItem(r, c, self.set_item(r, c))

        self.view.resizeColumnsToContents()

        self.comboBox.addItems(header)

        self.view.setEditTriggers(QAbstractItemView.NoEditTriggers)
        self.label.setText("{} observation{}".format(self.view.rowCount(), "s" * (self.view.rowCount() > 1)))


    def view_doubleClicked(self, index):

        if self.mode == config.MULTIPLE:
            return

        if self.mode == config.OPEN or self.mode == config.EDIT:
            self.done(2)
            return

        if self.mode == config.SELECT1:
            self.done(2)
            return

        response = dialog.MessageDialog(config.programName, "What do you want to do with this observation?",
                                        list(commands_index.keys()) + [config.CANCEL])
        if response == config.CANCEL:
            return
        else:
            self.done(commands_index[response])


    def pbSelection_clicked(self, mode):
        """
        select or unselect all filtered observations
        """

        for idx in range(self.view.rowCount()):
            table_item = self.view.item(idx, 0)
            table_item.setSelected(mode == "select")


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

        if self.column_type[c] == config.NUMERIC:
            try:
                item = MyTableWidgetItem(self.data[r][c], float(self.data[r][c]))
            except Exception:
                item = MyTableWidgetItem(self.data[r][c], 0)
        else:
            item = MyTableWidgetItem(self.data[r][c], self.data[r][c])
        return item


    def view_filter(self):
        """
        filter
        """

        def str2float(s):
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

        def equal(s, l):
            l_num, s_num = str2float(l), str2float(s)
            if type(l_num) == type(s_num):
                return l_num == s_num
            else:
                return l == s

        def not_equal(s, l):
            l_num, s_num = str2float(l), str2float(s)
            if type(l_num) == type(s_num):
                return l_num != s_num
            else:
                return l != s

        def gt(s, l):
            l_num, s_num = str2float(l), str2float(s)
            if type(l_num) == type(s_num):
                return l_num > s_num
            else:
                return l > s

        def lt(s, l):
            l_num, s_num = str2float(l), str2float(s)
            if type(l_num) == type(s_num):
                return l_num < s_num
            else:
                return l < s

        def gt_or_equal(s, l):
            l_num, s_num = str2float(l), str2float(s)
            if type(l_num) == type(s_num):
                return l_num >= s_num
            else:
                return l >= s

        def lt_or_equal(s, l):
            l_num, s_num = str2float(l), str2float(s)
            if type(l_num) == type(s_num):
                return l_num <= s_num
            else:
                return l <= s

        def between(s, l):
            if len(s.split(" AND ")) != 2:
                return None
            s1, s2 = s.split(" AND ")
            s1_num, s2_num = str2float(s1), str2float(s2)
            if type(s1_num) != type(s2_num):
                return None
            l_num = str2float(l)
            if type(s1_num) == type(l_num):
                return l_num >= s1_num and l_num <= s2_num
            else:
                return l >= s1 and l <= s2

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
