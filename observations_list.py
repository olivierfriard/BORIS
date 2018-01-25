#!/usr/bin/env python

"""
BORIS
Behavioral Observation Research Interactive Software
Copyright 2012-2018 Olivier Friard


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


try:
    from PyQt5.QtGui import *
    from PyQt5.QtCore import *
    from PyQt5.QtWidgets import *
except:
    from PyQt4.QtGui import *
    from PyQt4.QtCore import *

import os
import dialog
import config
from utilities import *


class MyTableWidgetItem(QTableWidgetItem):
    def __init__(self, text, sortKey):
            QTableWidgetItem.__init__(self, text, QTableWidgetItem.UserType)
            self.sortKey = sortKey

    #Qt uses a simple < check for sorting items, override this to use the sortKey
    def __lt__(self, other):
            return self.sortKey < other.sortKey


class observationsList_widget(QDialog):

    def __init__(self, data, header, column_type, parent=None):
        super(observationsList_widget, self).__init__(parent)

        self.data = data
        self.column_type = column_type

        self.setWindowTitle("Observations list - " + config.programName)
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
        self.gridLayout.addWidget(self.label,    0, 0, 1, 3)
        self.gridLayout.addWidget(self.comboBox, 1, 0, 1, 1)
        self.gridLayout.addWidget(self.cbLogic,  1, 1, 1, 1)
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

        self.pbCancel = QPushButton("Cancel")
        hbox2.addWidget(self.pbCancel)

        self.pbOpen = QPushButton("Start")
        hbox2.addWidget(self.pbOpen)

        self.pbEdit = QPushButton("Edit")
        hbox2.addWidget(self.pbEdit)

        self.pbOk = QPushButton("OK")
        hbox2.addWidget(self.pbOk)

        self.gridLayout.addLayout(hbox2, 3, 0, 1, 3)

        self.pbCancel.clicked.connect(self.pbCancel_clicked)
        self.pbOk.clicked.connect(self.pbOk_clicked)
        self.pbOpen.clicked.connect(self.pbOpen_clicked)
        self.pbEdit.clicked.connect(self.pbEdit_clicked)

        self.view.doubleClicked.connect(self.view_doubleClicked)

        self.view.setRowCount(len(self.data))
        self.view.setColumnCount(len(self.data[0]))

        self.view.setHorizontalHeaderLabels(header)

        for r in range(len(self.data)):
            for c in range(len(self.data[0])):
                self.view.setItem(r, c, self.set_item(r, c))

        self.view.resizeColumnsToContents()

        self.comboBox.addItems(header)

        self.view.setEditTriggers(QAbstractItemView.NoEditTriggers);
        self.label.setText("{} observation{}".format(self.view.rowCount(), "s" * (self.view.rowCount()>1)))



    def view_doubleClicked(self, index):

        if self.mode == config.MULTIPLE:
           return

        if self.mode == config.OPEN or self.mode == config.EDIT:
            self.done(2)
            return

        if self.mode == config.SELECT1:
            self.done(2)
            return

        response = dialog.MessageDialog(config.programName, "What do you want to do with this observation?", ["Open", "Edit", config.CANCEL])
        if response == "Open":
            self.done(2)
        if response == "Edit":
            self.done(3)



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

    def set_item(self, r, c):

        if self.column_type[c] == config.NUMERIC:
            try:
                item = MyTableWidgetItem(self.data[r][c], float(self.data[r][c]))
            except:
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
            except:
                return s

        def in_(s, l):
            return s in l

        def not_in(s, l):
            return s not in l

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


        #if self.comboBox.currentIndex() <= 4 and len(self.lineEdit.text()) < 3:
        if not self.lineEdit.text():
            self.view.setRowCount(len(self.data))
            #self.view.setColumnCount(len(self.data[0]))

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
            except:
                pass
        self.label.setText('{} observation{}'.format(self.view.rowCount(), "s" * (self.view.rowCount() > 1)))

