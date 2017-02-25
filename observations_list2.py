#!/usr/bin/env python

"""
BORIS
Behavioral Observation Research Interactive Software
Copyright 2012-2017 Olivier Friard


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

N = 2000

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


import random, string

def randomword(length):
   return ''.join(random.choice("abcdefghijklmnopqrstuvwxyz ") for i in range(length))





class observationsList_widget(QDialog):

    def __init__(self, data, parent=None):
        super(observationsList_widget, self).__init__(parent)

        self.data = data

        self.setWindowTitle("Observations list - " + config.programName)
        self.label = QLabel("")

        self.mode = config.SINGLE

        self.lineEdit = QLineEdit(self)
        self.lineEdit.textChanged.connect(self.view_filter)
        self.view = QTableWidget(self)
        self.view.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.view.setSortingEnabled(True)

        self.comboBox = QComboBox(self)

        '''
        self.comboBox.addItems(["Observation id",
                              "Date",
                              "Subjects",
                              "Description",
                              "Media file",
                              ])
        '''
        self.comboBox.currentIndexChanged.connect(self.view_filter)

        self.cbLogic = QComboBox(self)

        self.cbLogic.addItems(["in",
                               "not in",
                               "=",
                               "!=",
                               ">",
                               "<",
                               ">=",
                               "<="
                              ])
        self.cbLogic.currentIndexChanged.connect(self.view_filter)


        self.label = QLabel(self)

        self.pbSearch = QPushButton("Search")
        self.pbSearch.clicked.connect(self.view_filter)

        self.gridLayout = QGridLayout(self)
        self.gridLayout.addWidget(self.label,    0, 1, 1, 3)
        self.gridLayout.addWidget(self.comboBox, 1, 1, 1, 1)
        self.gridLayout.addWidget(self.cbLogic, 1, 2, 1, 1)
        self.gridLayout.addWidget(self.lineEdit, 1, 3, 1, 1)
        '''self.gridLayout.addWidget(self.pbSearch, 1, 3, 1, 1)'''

        self.gridLayout.addWidget(self.view, 2, 0, 1, 3)

        hbox2 = QHBoxLayout()

        spacerItem = QSpacerItem(241, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)
        hbox2.addItem(spacerItem)

        self.pbSelectAll = QPushButton("Select all")
        hbox2.addWidget(self.pbSelectAll)

        self.pbUnSelectAll = QPushButton("Unselect all")
        hbox2.addWidget(self.pbUnSelectAll)

        self.pbCancel = QPushButton("Cancel")
        hbox2.addWidget(self.pbCancel)

        self.pbOpen = QPushButton("Open")
        hbox2.addWidget(self.pbOpen)

        self.pbEdit = QPushButton("Edit")
        hbox2.addWidget(self.pbEdit)

        self.pbOk = QPushButton("OK")
        hbox2.addWidget(self.pbOk)

        self.gridLayout.addLayout(hbox2, 3, 0, 1, 3)

        self.pbSelectAll.clicked.connect(self.pbSelectAll_clicked)
        self.pbUnSelectAll.clicked.connect(self.pbUnSelectAll_clicked)

        self.pbCancel.clicked.connect(self.pbCancel_clicked)
        self.pbOk.clicked.connect(self.pbOk_clicked)
        self.pbOpen.clicked.connect(self.pbOpen_clicked)
        self.pbEdit.clicked.connect(self.pbEdit_clicked)

        self.view.doubleClicked.connect(self.view_doubleClicked)

        self.view.setRowCount(len(self.data))
        self.view.setColumnCount(len(self.data[0]))

        for r in range(len(self.data)):
            for c in range(len(self.data[0])):
                self.view.setItem(r, c, QTableWidgetItem(self.data[r][c]))



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



    def pbSelectAll_clicked(self):

        '''
        for r in range(self.view.rowCount()):
            for c in range(self.view.columnCount()):
                self.view.item(r, c).setSelected(True)
        '''

        for idx in range(self.view.rowCount()):
            table_item = self.view.item(idx, 0)
            table_item.setSelected(True)


    def pbUnSelectAll_clicked(self):
        for idx in range(self.view.rowCount()):
            table_item = self.view.item(idx, 0)
            table_item.setSelected(False)


    def pbCancel_clicked(self):
        self.close()

    def pbOk_clicked(self):
        self.done(1)

    def pbOpen_clicked(self):
        self.done(2)

    def pbEdit_clicked(self):
        self.done(3)


    def view_filter(self):
        """
        filter
        """
        
        def str2float(s):
            """
            convert str in int or float or return str
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


        
        if self.comboBox.currentIndex() <= 4 and len(self.lineEdit.text()) < 3:
            self.view.setRowCount(len(self.data))
            self.view.setColumnCount(len(self.data[0]))

            for r in range(len(self.data)):
                for c in range(len(self.data[0])):
                    self.view.setItem(r, c, QTableWidgetItem(self.data[r][c]))

        else:

            '''
            [self.comboBox.itemText(i) for i in range(self.comboBox.count())]
            
            columns = {"Observation id": 0, "Date": 1, "Description": 2, "Subjects": 3, "Media file": 4}
            '''

            if self.cbLogic.currentText() == "in":
                logic = in_
            if self.cbLogic.currentText() == "not in":
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


            self.view.setRowCount(0)
            search = self.lineEdit.text().upper()

            
            
            for r in self.data:
                #print(search, r[self.comboBox.currentIndex()])
                #print(logic(search, r[self.comboBox.currentIndex()].upper()))
                if logic(search, r[self.comboBox.currentIndex()].upper()):
                    self.view.setRowCount(self.view.rowCount() + 1)
                    for idx,c in enumerate(r):
                        self.view.setItem(self.view.rowCount()-1, idx, QTableWidgetItem(r[idx]))

        self.label.setText('{} observation{}'.format(self.view.rowCount(), "s" * (self.view.rowCount() > 1)))



if __name__ == '__main__':
    import sys
    app = QApplication(sys.argv)

    data = []
    for r in range(N):
        row = []
        for c in range(8):
            row.append(randomword(20))
        data.append(row)

    t = observationsList_widget(data)
    t.show()
    sys.exit(app.exec_())
