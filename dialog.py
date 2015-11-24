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
from PyQt4.QtCore import *
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


class JumpTo(QDialog):
    '''
    "jump to" dialog box
    '''

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
    '''
    "edit selected events" dialog box
    '''

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
            QMessageBox.warning(None, config.programName, "You must select a field to be edited",\
            QMessageBox.Ok | QMessageBox.Default, QMessageBox.NoButton)
            return
        if self.rbBehavior.isChecked() and self.leText.text().upper() not in self.all_behaviors:
            QMessageBox.warning(None, config.programName, "This behavior is not in ethogram",\
            QMessageBox.Ok | QMessageBox.Default, QMessageBox.NoButton)
            return
        if self.rbSubject.isChecked() and self.leText.text().upper() not in self.all_subjects:
            QMessageBox.warning(None, config.programName, "This subject is not in subject's list",\
            QMessageBox.Ok | QMessageBox.Default, QMessageBox.NoButton)
            return

        self.accept()

    def pbCancel_clicked(self):
        self.reject()


class Spectrogram(QWidget):

    def __init__(self, fileName1stChunk, parent = None):

        super(Spectrogram, self).__init__(parent)

        self.pixmap = QPixmap()
        self.pixmap.load( fileName1stChunk )
        self.w, self.h = self.pixmap.width(), self.pixmap.height()

        print( 'pixmap.width(), pixmap.height()',self.pixmap.width(), self.pixmap.height() )

        self.setGeometry(300, 300, 1000, self.h + 50)

        self.scene = QGraphicsScene(self)
        self.scene.setBackgroundBrush (QColor(0,0,0,255))

        self.scene.setSceneRect(0, 0, 100, 100)

        self.line = QGraphicsLineItem(0, 0, 0, self.h, scene = self.scene)
        self.line.setPen(QPen(QColor(255,0,0,255), 2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        self.line.setZValue(100.0)
        self.scene.addItem(self.line)

        self.view = QGraphicsView(self.scene)
        #self.view.showMaximized()

        hbox = QHBoxLayout(self)
        hbox.addWidget(self.view)

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
