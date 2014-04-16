#!/usr/bin/env python
#-*- coding:utf-8 -*-

"""
BORIS
Behavioral Observation Research Interactive Software
Copyright 2012-2014 Olivier Friard


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

from PySide.QtCore import *
from PySide.QtGui import *

class observationsList_widget(QDialog):

    def __init__(self, parent=None):
        super(observationsList_widget, self).__init__(parent)

        self.label = QLabel(self)

        self.lineEdit       = QLineEdit(self)
        self.view           = QTableView(self)
        self.view.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.comboBox       = QComboBox(self)
        self.label          = QLabel(self)

        self.gridLayout = QGridLayout(self)
        self.gridLayout.addWidget(self.label, 0, 1, 1, 3)
        self.gridLayout.addWidget(self.comboBox, 1, 1, 1, 1)
        self.gridLayout.addWidget(self.lineEdit, 1, 2, 1, 1)
        self.gridLayout.addWidget(self.view, 2, 0, 1, 3)


        hbox2 = QHBoxLayout(self)


        spacerItem = QSpacerItem(241, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)
        hbox2.addItem(spacerItem)

        self.pbSelectAll = QPushButton('Select all')
        hbox2.addWidget(self.pbSelectAll)

        self.pbUnSelectAll = QPushButton('Unselect all')
        hbox2.addWidget(self.pbUnSelectAll)


        self.pbClose = QPushButton('Close')
        hbox2.addWidget(self.pbClose)

        self.pb = QPushButton('')
        hbox2.addWidget(self.pb)

        self.gridLayout.addLayout(hbox2, 3, 0, 1, 3)

        self.model = QStandardItemModel(self)

        self.proxy = QSortFilterProxyModel(self)
        self.proxy.setSourceModel(self.model)

        self.view.setModel(self.proxy)

        self.lineEdit.textChanged.connect(self.on_lineEdit_textChanged)
        self.comboBox.currentIndexChanged.connect(self.on_comboBox_currentIndexChanged)

        self.horizontalHeader = self.view.horizontalHeader()
        self.horizontalHeader.sectionClicked.connect(self.on_view_horizontalHeader_sectionClicked)

        '''
        FIXME
        self.pbSelectAll.clicked.connect(self.pbSelectAll_clicked)
        self.pbUnSelectAll.clicked.connect(self.pbUnSelectAll_clicked)
        '''

        self.pbClose.clicked.connect(self.pbClose_clicked)
        self.pb.clicked.connect(self.pb_clicked)

    '''
    def pbSelectAll_clicked(self):

        if self.proxy.rowCount():
            self.view.setSelection(QRect(QPoint(1,1),QSize(1,1)),QItemSelectionModel.Select)
    '''

    '''
    def pbUnSelectAll_clicked(self):
        pass
    '''

    def pbClose_clicked(self):
        self.close()

    def pb_clicked(self):
        self.accept()



    def on_view_horizontalHeader_sectionClicked(self, logicalIndex):

        self.logicalIndex = logicalIndex
        self.menuValues = QMenu(self)
        self.signalMapper = QSignalMapper(self)

        self.comboBox.blockSignals(True)
        self.comboBox.setCurrentIndex(self.logicalIndex)
        self.comboBox.blockSignals(True)

        valuesUnique = [ self.model.item(row, self.logicalIndex).text() for row in range(self.model.rowCount()) ]

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
        filterString = QRegExp(  "", Qt.CaseInsensitive, QRegExp.RegExp )

        self.proxy.setFilterRegExp(filterString)
        self.proxy.setFilterKeyColumn(filterColumn)


    def on_signalMapper_mapped(self, i):
        stringAction = self.signalMapper.mapping(i).text()
        filterColumn = self.logicalIndex
        filterString = QRegExp(  stringAction, Qt.CaseSensitive, QRegExp.FixedString )

        self.proxy.setFilterRegExp(filterString)
        self.proxy.setFilterKeyColumn(filterColumn)


    def on_lineEdit_textChanged(self, text):
        search = QRegExp(    text,  Qt.CaseInsensitive,  QRegExp.RegExp )

        self.proxy.setFilterRegExp(search)


    def on_comboBox_currentIndexChanged(self, index):
        '''combo box changed'''
        self.proxy.setFilterKeyColumn(index)



