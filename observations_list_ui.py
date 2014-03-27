# -*- coding: utf-8 -*-

# Form implementation generated from reading ui file 'observations_list.ui'
#
# Created: Fri Mar 28 00:29:53 2014
#      by: pyside-uic 0.2.13 running on PySide 1.1.1
#
# WARNING! All changes made in this file will be lost!

from PySide import QtCore, QtGui

class Ui_observationsList(object):
    def setupUi(self, observationsList):
        observationsList.setObjectName("observationsList")
        observationsList.setWindowModality(QtCore.Qt.WindowModal)
        observationsList.resize(905, 319)
        self.verticalLayout_2 = QtGui.QVBoxLayout(observationsList)
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.verticalLayout = QtGui.QVBoxLayout()
        self.verticalLayout.setObjectName("verticalLayout")
        self.twObservations = QtGui.QTableWidget(observationsList)
        self.twObservations.setEditTriggers(QtGui.QAbstractItemView.NoEditTriggers)
        self.twObservations.setDragDropOverwriteMode(False)
        self.twObservations.setSelectionMode(QtGui.QAbstractItemView.ExtendedSelection)
        self.twObservations.setSelectionBehavior(QtGui.QAbstractItemView.SelectRows)
        self.twObservations.setObjectName("twObservations")
        self.twObservations.setColumnCount(5)
        self.twObservations.setRowCount(0)
        item = QtGui.QTableWidgetItem()
        self.twObservations.setHorizontalHeaderItem(0, item)
        item = QtGui.QTableWidgetItem()
        self.twObservations.setHorizontalHeaderItem(1, item)
        item = QtGui.QTableWidgetItem()
        self.twObservations.setHorizontalHeaderItem(2, item)
        item = QtGui.QTableWidgetItem()
        self.twObservations.setHorizontalHeaderItem(3, item)
        item = QtGui.QTableWidgetItem()
        self.twObservations.setHorizontalHeaderItem(4, item)
        self.verticalLayout.addWidget(self.twObservations)
        self.horizontalLayout = QtGui.QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        spacerItem = QtGui.QSpacerItem(40, 20, QtGui.QSizePolicy.Expanding, QtGui.QSizePolicy.Minimum)
        self.horizontalLayout.addItem(spacerItem)
        self.pbCancel = QtGui.QPushButton(observationsList)
        self.pbCancel.setObjectName("pbCancel")
        self.horizontalLayout.addWidget(self.pbCancel)
        self.pbSelectAll = QtGui.QPushButton(observationsList)
        self.pbSelectAll.setObjectName("pbSelectAll")
        self.horizontalLayout.addWidget(self.pbSelectAll)
        self.pbUnSelectAll = QtGui.QPushButton(observationsList)
        self.pbUnSelectAll.setObjectName("pbUnSelectAll")
        self.horizontalLayout.addWidget(self.pbUnSelectAll)
        self.pbEdit = QtGui.QPushButton(observationsList)
        self.pbEdit.setObjectName("pbEdit")
        self.horizontalLayout.addWidget(self.pbEdit)
        self.pbOpen = QtGui.QPushButton(observationsList)
        self.pbOpen.setObjectName("pbOpen")
        self.horizontalLayout.addWidget(self.pbOpen)
        self.pbOK = QtGui.QPushButton(observationsList)
        self.pbOK.setObjectName("pbOK")
        self.horizontalLayout.addWidget(self.pbOK)
        self.verticalLayout.addLayout(self.horizontalLayout)
        self.verticalLayout_2.addLayout(self.verticalLayout)

        self.retranslateUi(observationsList)
        QtCore.QMetaObject.connectSlotsByName(observationsList)

    def retranslateUi(self, observationsList):
        observationsList.setWindowTitle(QtGui.QApplication.translate("observationsList", "Observations list", None, QtGui.QApplication.UnicodeUTF8))
        self.twObservations.horizontalHeaderItem(0).setText(QtGui.QApplication.translate("observationsList", "id", None, QtGui.QApplication.UnicodeUTF8))
        self.twObservations.horizontalHeaderItem(1).setText(QtGui.QApplication.translate("observationsList", "Date", None, QtGui.QApplication.UnicodeUTF8))
        self.twObservations.horizontalHeaderItem(2).setText(QtGui.QApplication.translate("observationsList", "Description", None, QtGui.QApplication.UnicodeUTF8))
        self.twObservations.horizontalHeaderItem(3).setText(QtGui.QApplication.translate("observationsList", "Media #1", None, QtGui.QApplication.UnicodeUTF8))
        self.twObservations.horizontalHeaderItem(4).setText(QtGui.QApplication.translate("observationsList", "Media #2", None, QtGui.QApplication.UnicodeUTF8))
        self.pbCancel.setText(QtGui.QApplication.translate("observationsList", "Cancel", None, QtGui.QApplication.UnicodeUTF8))
        self.pbSelectAll.setText(QtGui.QApplication.translate("observationsList", "Select all", None, QtGui.QApplication.UnicodeUTF8))
        self.pbUnSelectAll.setText(QtGui.QApplication.translate("observationsList", "Unselect all", None, QtGui.QApplication.UnicodeUTF8))
        self.pbEdit.setText(QtGui.QApplication.translate("observationsList", "Edit", None, QtGui.QApplication.UnicodeUTF8))
        self.pbOpen.setText(QtGui.QApplication.translate("observationsList", "Open", None, QtGui.QApplication.UnicodeUTF8))
        self.pbOK.setText(QtGui.QApplication.translate("observationsList", "OK", None, QtGui.QApplication.UnicodeUTF8))

