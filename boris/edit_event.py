#!/usr/bin/env python3

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

from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

from boris import duration_widget
from boris.config import HHMMSS, HHMMSSZZZ, S, programName
from boris.edit_event_ui import Ui_Form
from boris.utilities import seconds2time


class DlgEditEvent(QDialog, Ui_Form):

    def __init__(self, log_level,
                 time_value=0,
                 current_time=0,
                 time_format=S,
                 show_set_current_time=False,
                 parent=None):

        super().__init__(parent)
        self.setupUi(self)
        self.time_value = time_value

        self.pb_set_to_current_time.setVisible(show_set_current_time)
        self.current_time = current_time

        self.dsbTime.setVisible(False)
        self.teTime.setVisible(False)

        self.time_widget = duration_widget.Duration_widget(self.time_value)
        if time_format == S:
            self.time_widget.set_format_s()
        if time_format == HHMMSS:
            self.time_widget.set_format_hhmmss()

        self.horizontalLayout_2.insertWidget(0, self.time_widget)


        self.pb_set_to_current_time.clicked.connect(self.set_to_current_time)
        self.pbOK.clicked.connect(self.accept)
        self.pbCancel.clicked.connect(self.reject)


    def set_to_current_time(self):
        """
        set time to current media time
        """

        self.time_widget.set_time(float(self.current_time))


class EditSelectedEvents(QDialog):
    """
    "edit selected events" dialog box
    """

    def __init__(self):
        super(EditSelectedEvents, self).__init__()

        self.setWindowTitle("Edit selected events")

        hbox = QVBoxLayout(self)

        self.rbSubject = QRadioButton("Subject")
        self.rbSubject.setChecked(False)
        self.rbSubject.toggled.connect(self.rb_changed)
        hbox.addWidget(self.rbSubject)

        self.rbBehavior = QRadioButton("Behavior")
        self.rbBehavior.setChecked(False)
        self.rbBehavior.toggled.connect(self.rb_changed)
        hbox.addWidget(self.rbBehavior)

        self.lb = QLabel("New value")
        hbox.addWidget(self.lb)
        self.newText = QListWidget(self)
        hbox.addWidget(self.newText)

        self.rbComment = QRadioButton("Comment")
        self.rbComment.setChecked(False)
        self.rbComment.toggled.connect(self.rb_changed)
        hbox.addWidget(self.rbComment)

        self.lbComment = QLabel("New comment")
        hbox.addWidget(self.lbComment)

        self.commentText = QLineEdit()
        hbox.addWidget(self.commentText)

        hbox2 = QHBoxLayout(self)
        self.pbOK = QPushButton("OK")
        self.pbOK.clicked.connect(self.pbOK_clicked)
        self.pbCancel = QPushButton("Cancel")
        self.pbCancel.clicked.connect(self.pbCancel_clicked)
        hbox2.addWidget(self.pbCancel)
        hbox2.addWidget(self.pbOK)
        hbox.addLayout(hbox2)

        self.setLayout(hbox)

    def rb_changed(self):

        self.newText.setEnabled(not self.rbComment.isChecked())
        self.commentText.setEnabled(self.rbComment.isChecked())

        if self.rbSubject.isChecked():
            self.newText.clear()
            self.newText.addItems(self.all_subjects)

        if self.rbBehavior.isChecked():
            self.newText.clear()
            self.newText.addItems(self.all_behaviors)

        if self.rbComment.isChecked():
            self.newText.clear()


    def pbOK_clicked(self):
        if not self.rbSubject.isChecked() and not self.rbBehavior.isChecked() and not self.rbComment.isChecked():
            QMessageBox.warning(None, programName, "You must select a field to be edited",
                                QMessageBox.Ok | QMessageBox.Default, QMessageBox.NoButton)
            return

        if (self.rbSubject.isChecked() or self.rbBehavior.isChecked()) and self.newText.selectedItems() == []:
            QMessageBox.warning(None, programName, "You must select a new value from the list",
                                QMessageBox.Ok | QMessageBox.Default, QMessageBox.NoButton)
            return

        self.accept()

    def pbCancel_clicked(self):
        self.reject()


if __name__ == '__main__':
    import sys
    app = QApplication(sys.argv)
    w = DlgEditEvent(None, time_value=3.141, current_time=0, time_format=S, show_set_current_time=True)
    w.show()
    sys.exit(app.exec_())
