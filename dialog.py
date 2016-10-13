#!/usr/bin/env python

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

import config


def MessageDialog(title, text, buttons):
    response = ""
    message = QMessageBox()
    message.setWindowTitle(title)
    message.setText(text)
    message.setIcon(QMessageBox.Question)
    for button in buttons:
        message.addButton(button, QMessageBox.YesRole)

    message.setWindowFlags(Qt.WindowStaysOnTopHint)
    message.exec_()
    return message.clickedButton().text()


class DuplicateBehaviorCode(QDialog):
    """
    let user show between behaviors that are coded by same key
    """

    def __init__(self, text, codes_list):

        super(DuplicateBehaviorCode, self).__init__()

        self.setWindowTitle(config.programName)
        self.setWindowFlags(Qt.WindowStaysOnTopHint)

        Vlayout = QVBoxLayout()
        widget = QWidget(self)
        widget.setLayout(Vlayout)

        label = QLabel()
        label.setText(text)
        Vlayout.addWidget(label)

        self.lw = QListWidget(widget)
        self.lw.setObjectName("lw_modifiers")
        #TODO: to be enabled
        #lw.installEventFilter(self)

        '''
        if QT_VERSION_STR[0] == "4":
            lw.setItemSelected(item, True)
        else:
            item.setSelected(True)
        '''

        for code in codes_list:
            item = QListWidgetItem(code)
            self.lw.addItem(item)

        Vlayout.addWidget(self.lw)

        pbCancel = QPushButton("Cancel")
        pbCancel.clicked.connect(self.reject)
        Vlayout.addWidget(pbCancel)
        pbOK = QPushButton("OK")
        pbOK.setDefault(True)
        pbOK.clicked.connect(self.pbOK_clicked)
        Vlayout.addWidget(pbOK)

        self.setLayout(Vlayout)

        #self.installEventFilter(self)

        self.setMaximumSize(1024 , 960)

    def getCode(self):
        """
        get selected behavior code
        """
        if self.lw.selectedItems():
            return self.lw.selectedItems()[0].text()

    def pbOK_clicked(self):
        self.accept()


class ChooseObservationsToImport(QDialog):
    """

    """

    def __init__(self, text, observations_list):

        super(ChooseObservationsToImport, self).__init__()

        self.setWindowTitle(config.programName)
        self.setWindowFlags(Qt.WindowStaysOnTopHint)

        Vlayout = QVBoxLayout()
        widget = QWidget(self)
        widget.setLayout(Vlayout)

        label = QLabel()
        label.setText(text)
        Vlayout.addWidget(label)

        self.lw = QListWidget(widget)
        self.lw.setObjectName("lw_observations")
        self.lw.setSelectionMode(QAbstractItemView.ExtendedSelection)
        #TODO: to be enabled
        #lw.installEventFilter(self)

        '''
        if QT_VERSION_STR[0] == "4":
            lw.setItemSelected(item, True)
        else:
            item.setSelected(True)
        '''

        for code in observations_list:
            item = QListWidgetItem(code)
            self.lw.addItem(item)

        Vlayout.addWidget(self.lw)

        pbCancel = QPushButton("Cancel")
        pbCancel.clicked.connect(self.reject)
        Vlayout.addWidget(pbCancel)
        pbOK = QPushButton("OK")
        pbOK.setDefault(True)
        pbOK.clicked.connect(self.pbOK_clicked)
        Vlayout.addWidget(pbOK)

        self.setLayout(Vlayout)

        #self.installEventFilter(self)

        self.setMaximumSize(1024 , 960)

    def get_selected_observations(self):
        """
        get selected_observations
        """
        return [item.text() for item in self.lw.selectedItems()]

    def pbOK_clicked(self):
        self.accept()



class JumpTo(QDialog):
    """
    "jump to" dialog box
    """

    def __init__(self, timeFormat):
        super(JumpTo, self).__init__()
        hbox = QVBoxLayout(self)
        self.label = QLabel()
        self.label.setText("Go to time")
        hbox.addWidget(self.label)
        if timeFormat == "hh:mm:ss":
            self.te = QTimeEdit()
            self.te.setDisplayFormat("hh:mm:ss.zzz")
        else:
            self.te = QDoubleSpinBox()
            self.te.setMinimum(0)
            self.te.setMaximum(86400)
            self.te.setDecimals(3)
        hbox.addWidget(self.te)
        self.pbOK = QPushButton('OK')
        self.pbOK.clicked.connect(self.pbOK_clicked)
        self.pbCancel = QPushButton('Cancel')
        self.pbCancel.clicked.connect(self.pbCancel_clicked)
        hbox2 = QHBoxLayout(self)
        hbox2.addWidget(self.pbCancel)
        hbox2.addWidget(self.pbOK)
        hbox.addLayout(hbox2)
        self.setLayout(hbox)
        self.setWindowTitle('Jump to specific time')

    def pbOK_clicked(self):
        self.accept()

    def pbCancel_clicked(self):
        self.reject()



class EditSelectedEvents(QDialog):
    """
    "edit selected events" dialog box
    """

    def __init__(self):
        super(EditSelectedEvents, self).__init__()

        hbox = QVBoxLayout(self)

        self.rbSubject = QRadioButton("Subject")
        self.rbSubject.setChecked(False)
        hbox.addWidget(self.rbSubject)

        self.rbBehavior = QRadioButton("Behavior")
        self.rbBehavior.setChecked(False)
        hbox.addWidget(self.rbBehavior)

        self.rbComment = QRadioButton("Comment")
        self.rbComment.setChecked(False)
        hbox.addWidget(self.rbComment)

        self.label = QLabel("New text")
        hbox.addWidget(self.label)

        self.leText = QLineEdit()
        hbox.addWidget(self.leText)

        hbox2 = QHBoxLayout(self)
        self.pbOK = QPushButton("OK")
        self.pbOK.clicked.connect(self.pbOK_clicked)
        self.pbCancel = QPushButton("Cancel")
        self.pbCancel.clicked.connect(self.pbCancel_clicked)
        hbox2.addWidget(self.pbCancel)
        hbox2.addWidget(self.pbOK)
        hbox.addLayout(hbox2)

        self.setLayout(hbox)

        self.setWindowTitle("Edit selected events")

    def pbOK_clicked(self):
        if not self.rbSubject.isChecked() and not self.rbBehavior.isChecked()and not self.rbComment.isChecked():
            QMessageBox.warning(None, config.programName, "You must select a field to be edited",
            QMessageBox.Ok | QMessageBox.Default, QMessageBox.NoButton)
            return
        if self.rbBehavior.isChecked() and self.leText.text().upper() not in self.all_behaviors:
            QMessageBox.warning(None, config.programName, "This behavior is not in ethogram",
            QMessageBox.Ok | QMessageBox.Default, QMessageBox.NoButton)
            return
        if self.rbSubject.isChecked() and self.leText.text().upper() not in self.all_subjects:
            QMessageBox.warning(None, config.programName, "This subject is not in subject's list",
            QMessageBox.Ok | QMessageBox.Default, QMessageBox.NoButton)
            return

        self.accept()

    def pbCancel_clicked(self):
        self.reject()




"""
class EventType(QDialog):
    '''
    dialog for selecting the type of new event and if there is an associed coding map
    '''

    def __init__(self, parent=None):
        super(EventType, self).__init__(parent)

        self.setWindowTitle(config.programName)
        group = QButtonGroup()
        HLayout = QHBoxLayout()

        self.rbStateEvent = QRadioButton('State event')
        group.addButton(self.rbStateEvent)
        HLayout.addWidget(self.rbStateEvent)

        self.rbPointEvent = QRadioButton('Point event')
        group.addButton(self.rbPointEvent)
        HLayout.addWidget(self.rbPointEvent)

        self.cbCodingMap = QCheckBox('Coding map')

        layout = QVBoxLayout()

        layout.addLayout(HLayout)

        layout.addWidget(self.cbCodingMap)

        HButtonLayout = QHBoxLayout()
        self.pbCancel = QPushButton('Cancel')
        self.pbCancel.clicked.connect(self.pbCancel_clicked)
        HButtonLayout.addWidget(self.pbCancel)
        self.pbOK = QPushButton('OK')
        self.pbOK.clicked.connect(self.pbOK_clicked)
        HButtonLayout.addWidget(self.pbOK)

        layout.addLayout(HButtonLayout)

        self.setLayout(layout)


    def pbOK_clicked(self):
        self.accept()

    def pbCancel_clicked(self):
        self.reject()
"""
