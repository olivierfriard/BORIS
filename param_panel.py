#!/usr/bin/env python3

"""
BORIS
Behavioral Observation Research Interactive Software
Copyright 2012-2016 Olivier Friard

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

try:
    from PyQt5.QtGui import *
    from PyQt5.QtCore import *
    from PyQt5.QtWidgets import *
except:
    from PyQt4.QtGui import *
    from PyQt4.QtCore import *

import os
import logging

from config import *

if QT_VERSION_STR[0] == "4":
    from param_panel_ui import Ui_Dialog
else:
    from param_panel_ui5 import Ui_Dialog

class Param_panel(QDialog, Ui_Dialog):

    def __init__(self, parent=None):

        super(Param_panel, self).__init__(parent)
        self.setupUi(self)

        self.pbSelectAllSubjects.clicked.connect(lambda: self.subjects_button_clicked("select all"))
        self.pbUnselectAllSubjects.clicked.connect(lambda: self.subjects_button_clicked("unselect all"))
        self.pbReverseSubjectsSelection.clicked.connect(lambda: self.subjects_button_clicked("reverse selection"))

        self.pbSelectAllBehaviors.clicked.connect(lambda: self.behaviors_button_clicked("select all"))
        self.pbUnselectAllBehaviors.clicked.connect(lambda: self.behaviors_button_clicked("unselect all"))
        self.pbReverseBehaviorsSelection.clicked.connect(lambda: self.behaviors_button_clicked("reverse selection"))

        self.pbOK.clicked.connect(self.ok)
        self.pbCancel.clicked.connect(self.reject)

        self.lwBehaviors.itemClicked.connect(self.behavior_item_clicked)


    def subjects_button_clicked(self, command):
        for idx in range(self.lwSubjects.count()):
            cb = self.lwSubjects.itemWidget(self.lwSubjects.item(idx))
            if command == "select all":
                cb.setChecked(True)
            if command == "unselect all":
                cb.setChecked(False)
            if command == "reverse selection":
                cb.setChecked(not cb.isChecked() )

    def behaviors_button_clicked(self, command):
        for idx in range(self.lwBehaviors.count()):
            cb = self.lwBehaviors.itemWidget(self.lwBehaviors.item(idx))
            if command == "select all":
                cb.setChecked(True)
            if command == "unselect all":
                cb.setChecked(False)
            if command == "reverse selection":
                cb.setChecked(not cb.isChecked())


    def ok(self):


        selectedSubjects = []
        for idx in range(self.lwSubjects.count()):
            cb = self.lwSubjects.itemWidget(self.lwSubjects.item(idx))
            if cb.isChecked():
                selectedSubjects.append(cb.text())
        self.selectedSubjects = selectedSubjects

        '''
        selectedBehaviors = []
        for idx in range(self.lwBehaviors.count()):
            cb = self.lwBehaviors.itemWidget(self.lwBehaviors.item(idx))
            if cb.isChecked():
                selectedBehaviors.append(cb.text())
        self.selectedBehaviors = selectedBehaviors
        '''

        selectedBehaviors = []
        for idx in range(self.lwBehaviors.count()):
            if self.lwBehaviors.item(idx).checkState() == Qt.Checked:
                selectedBehaviors.append(self.lwBehaviors.item(idx).text())
        self.selectedBehaviors = selectedBehaviors

        self.accept()


    def behavior_item_clicked(self, item):
        print("item clicked")

        if item.data(33) == "category":
            category = item.data(34)
            for i in range(self.lwBehaviors.count()):
                if self.lwBehaviors.item(i).data(34) == category and self.lwBehaviors.item(i).data(33) != "category":

                    '''
                    if self.lwBehaviors.item(i).checkState() == Qt.Unchecked:
                        self.lwBehaviors.item(i).setCheckState(Qt.Checked)
                    else:
                        self.lwBehaviors.item(i).setCheckState(Qt.Unchecked)
                    '''
                    if item.data(35):
                        self.lwBehaviors.item(i).setCheckState(Qt.Unchecked)
                    else:
                        self.lwBehaviors.item(i).setCheckState(Qt.Checked)

            item.setData(35, not item.data(35))



    def cb_changed(self):
        selectedSubjects = []
        for idx in range(self.lwSubjects.count()):
            cb = self.lwSubjects.itemWidget(self.lwSubjects.item(idx))
            if cb and cb.isChecked():
                selectedSubjects.append(cb.text())

        observedBehaviors = self.extract_observed_behaviors( self.selectedObservations, selectedSubjects )

        logging.debug("observed behaviors: {0}".format(observedBehaviors))

        for idx in range(self.lwBehaviors.count()):
            '''
            cb = self.lwBehaviors.itemWidget(self.lwBehaviors.item(idx))
            cb.setChecked( cb.text() in observedBehaviors)
            '''

            if self.lwBehaviors.item(idx).data(33) != "category":
                if  self.lwBehaviors.item(idx).text() in observedBehaviors:
                    self.lwBehaviors.item(idx).setCheckState(Qt.Checked)
                else:
                    self.lwBehaviors.item(idx).setCheckState(Qt.Unchecked)

