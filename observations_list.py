#!/usr/bin/env python

"""
BORIS
Behavioral Observation Research Interactive Software
Copyright 2012-2016 Olivier Friard


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

class observationsList_widget(QDialog):

    def __init__(self, parent=None):
        super(observationsList_widget, self).__init__(parent)

        self.setWindowTitle("Observations list - " + config.programName)
        self.label = QLabel(self)

        self.mode = config.SINGLE

        self.lineEdit = QLineEdit(self)
        self.view = QTableView(self)
        self.view.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.comboBox = QComboBox(self)
        self.label = QLabel(self)

        self.gridLayout = QGridLayout(self)
        self.gridLayout.addWidget(self.label, 0, 1, 1, 3)
        self.gridLayout.addWidget(self.comboBox, 1, 1, 1, 1)
        self.gridLayout.addWidget(self.lineEdit, 1, 2, 1, 1)
        self.gridLayout.addWidget(self.view, 2, 0, 1, 3)

        hbox2 = QHBoxLayout(self)
        
        self.sort_label = QLabel( "Sort order")

        hbox2.addWidget(self.sort_label)
        
        self.cbSort = QComboBox()
        self.cbSort.addItems(["Observation id ascending", "Observation id descending",
                              "Date ascending", "Date descending",
                              "Subjects ascending", "Subjects descending",
                              "Description ascending", "Description descending",
                              "Media file ascending", "Media file descending",
                              ]) 
        self.cbSort.currentIndexChanged.connect(self.sort_order_changed)
        hbox2.addWidget(self.cbSort)
        
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

        self.pbSelect = QPushButton("OK")
        hbox2.addWidget(self.pbSelect)

        self.gridLayout.addLayout(hbox2, 3, 0, 1, 3)

        self.model = QStandardItemModel(self)

        self.proxy = QSortFilterProxyModel(self)
        self.proxy.setSourceModel(self.model)

        self.view.setModel(self.proxy)

        self.lineEdit.textChanged.connect(self.on_lineEdit_textChanged)
        self.comboBox.currentIndexChanged.connect(self.on_comboBox_currentIndexChanged)

        self.horizontalHeader = self.view.horizontalHeader()
        self.horizontalHeader.sectionClicked.connect(self.on_view_horizontalHeader_sectionClicked)

        self.pbSelectAll.clicked.connect(self.pbSelectAll_clicked)
        self.pbUnSelectAll.clicked.connect(self.pbUnSelectAll_clicked)

        self.pbCancel.clicked.connect(self.pbCancel_clicked)
        self.pbSelect.clicked.connect(self.pbSelect_clicked)
        self.pbOpen.clicked.connect(self.pbOpen_clicked)
        self.pbEdit.clicked.connect(self.pbEdit_clicked)

        self.view.doubleClicked.connect(self.view_doubleClicked)

    def sort_order_changed(self, idx):
        sortOrder = ("descending" in self.cbSort.itemText(idx))
        for i, text in enumerate(["Observation id", "Date", "Description", "Subjects", "Media"]):
            if text in self.cbSort.itemText(idx):
                columnToSort = i
            
        self.proxy.sort (columnToSort, sortOrder)

        iniFilePath = os.path.expanduser("~") + os.sep + ".boris"
        try:
            settings = QSettings(iniFilePath, QSettings.IniFormat)
            settings.setValue("observations_list_order", self.cbSort.itemText(idx))
        except:
            pass


    def view_doubleClicked(self, index):

        if self.mode == config.MULTIPLE:
           return

        if self.mode == config.OPEN or self.mode == config.EDIT:
            self.done(2)
            return

        if self.mode == config.SELECT1:
            self.done(2)
            return


        response = dialog.MessageDialog(config.programName, 'What do you want to do with this observation?', ['Open', 'Edit', 'Cancel'])
        if response == 'Open':
            self.done(2)
        if response == 'Edit':
            self.done(3)



    def pbSelectAll_clicked(self):

        for idx in range(self.proxy.rowCount()):
            self.view.selectRow(idx)

    def pbUnSelectAll_clicked(self):
        self.view.clearSelection()

    def pbCancel_clicked(self):
        self.close()

    def pbSelect_clicked(self):
        self.done(1)

    def pbOpen_clicked(self):
        self.done(2)

    def pbEdit_clicked(self):
        self.done(3)

    def on_view_horizontalHeader_sectionClicked(self, logicalIndex):

        self.logicalIndex = logicalIndex
        self.menuValues = QMenu(self)
        self.signalMapper = QSignalMapper(self)

        self.comboBox.blockSignals(True)
        self.comboBox.setCurrentIndex(self.logicalIndex)
        self.comboBox.blockSignals(True)

        valuesUnique = [self.model.item(row, self.logicalIndex).text() for row in range(self.model.rowCount())]

        actionAll = QAction('All', self)
        actionAll.triggered.connect(self.on_actionAll_triggered)
        self.menuValues.addAction(actionAll)
        self.menuValues.addSeparator()

        for actionNumber, actionName in enumerate(sorted(list(set(valuesUnique)))):
            action = QAction(actionName, self)
            self.signalMapper.setMapping(action, actionNumber)
            action.triggered.connect(self.signalMapper.map)
            self.menuValues.addAction(action)

        self.signalMapper.mapped.connect(self.on_signalMapper_mapped)

        headerPos = self.view.mapToGlobal(self.horizontalHeader.pos())

        posY = headerPos.y() + self.horizontalHeader.height()
        posX = headerPos.x() + self.horizontalHeader.sectionPosition(self.logicalIndex)

        self.menuValues.exec_(QPoint(posX, posY))


    def on_actionAll_triggered(self):
        filterColumn = self.logicalIndex
        filterString = QRegExp("", Qt.CaseInsensitive, QRegExp.RegExp)

        self.proxy.setFilterRegExp(filterString)
        self.proxy.setFilterKeyColumn(filterColumn)


    def on_signalMapper_mapped(self, i):
        stringAction = self.signalMapper.mapping(i).text()
        filterColumn = self.logicalIndex
        filterString = QRegExp(stringAction, Qt.CaseSensitive, QRegExp.FixedString)

        self.proxy.setFilterRegExp(filterString)
        self.proxy.setFilterKeyColumn(filterColumn)


    def on_lineEdit_textChanged(self, text):
        '''
        text edit changed
        '''
        self.proxy.setFilterRegExp(QRegExp(text, Qt.CaseInsensitive, QRegExp.RegExp ))
        self.label.setText('{} observation{}'.format(self.proxy.rowCount(), "s" * (self.proxy.rowCount()>1)))


    def on_comboBox_currentIndexChanged(self, index):
        '''
        combo box changed
        '''
        self.proxy.setFilterKeyColumn(index)
