#!/usr/bin/env python3

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

import logging
from PyQt4.QtCore import *
from PyQt4.QtGui import *

from config import *
import dialog

class wgMeasurement(QWidget):
    """
    """

    closeSignal = pyqtSignal()
    flagSaved = True

    def __init__(self, log_level):
        super(wgMeasurement, self).__init__()

        logging.basicConfig(level=log_level)

        self.setWindowTitle("Geometric measurement")

        vbox = QVBoxLayout(self)

        self.rbDistance = QRadioButton("Distance (start: left click, end: right click)")
        vbox.addWidget(self.rbDistance)

        self.rbArea = QRadioButton("Area (left click for are vertices, right click to close area)")
        vbox.addWidget(self.rbArea)

        self.rbAngle = QRadioButton("Angle (vertex: left click, segments: right click)")
        vbox.addWidget(self.rbAngle)

        vbox.addWidget(QLabel("<b>Scale</b>"))

        hbox1 = QHBoxLayout(self)

        self.lbRef = QLabel("Reference")
        hbox1.addWidget(self.lbRef)

        self.lbPx = QLabel("Pixels")
        hbox1.addWidget(self.lbPx)

        vbox.addLayout(hbox1)

        hbox1 = QHBoxLayout(self)

        self.leRef = QLineEdit()
        self.leRef.setText("1")
        hbox1.addWidget(self.leRef)

        self.lePx = QLineEdit()
        self.lePx.setText("1")
        hbox1.addWidget(self.lePx)

        vbox.addLayout(hbox1)

        self.pte = QPlainTextEdit()
        vbox.addWidget(self.pte)

        hbox2 = QHBoxLayout(self)
        self.pbSave = QPushButton("Save results")
        hbox2.addWidget(self.pbSave)

        self.pbClose = QPushButton("Close")
        hbox2.addWidget(self.pbClose)

        vbox.addLayout(hbox2)

        self.pbClose.clicked.connect(self.pbClose_clicked)
        self.pbSave.clicked.connect(self.pbSave_clicked)

    def pbClose_clicked(self):
        if not self.flagSaved:
            response = dialog.MessageDialog(programName, "The current results are not saved. Do you want to save results before closing?", [YES, NO, CANCEL])
            if response == YES:
                self.pbSave_clicked()
            if response == CANCEL:
                return
        self.closeSignal.emit()


    def pbSave_clicked(self):
        """
        save results
        """
        if self.pte.toPlainText():
            fileName = QFileDialog(self).getSaveFileName(self, "Save measurement results", "", "Text files (*.txt);;All files (*)")
            if fileName:
                with open(fileName, "w") as f:
                    f.write(self.pte.toPlainText())
                self.flagSaved = True
        else:
            QMessageBox.information(self, programName, "There are no results to save")

