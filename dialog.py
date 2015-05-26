#!/usr/bin/env python

"""
BORIS
Behavioral Observation Research Interactive Software
Copyright 2012-2015 Olivier Friard

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


from PyQt4.QtGui import *
import config

def MessageDialog(title, text, buttons):
    response = ''
    message = QMessageBox()
    message.setWindowTitle(title)
    message.setText(text)
    message.setIcon(QMessageBox.Question)
    for button in buttons:
        message.addButton(button, QMessageBox.YesRole)
    
    message.exec_()
    return message.clickedButton().text()
    


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
