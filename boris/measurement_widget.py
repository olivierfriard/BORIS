"""
BORIS
Behavioral Observation Research Interactive Software
Copyright 2012-2025 Olivier Friard

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

from PySide6.QtCore import Signal

# from PySide6.QtGui import *
from PySide6.QtWidgets import (
    QApplication,
    QWidget,
    QRadioButton,
    QLabel,
    QHBoxLayout,
    QVBoxLayout,
    QLineEdit,
    QPlainTextEdit,
    QCheckBox,
    QPushButton,
    QFileDialog,
    QMessageBox,
)
from . import dialog
from . import config as cfg


class wgMeasurement(QWidget):
    """ """

    closeSignal, clearSignal = Signal(), Signal()
    flagSaved = True
    draw_mem = []

    def __init__(self):
        super().__init__()

        self.setWindowTitle("Geometric measurements")

        vbox = QVBoxLayout(self)

        self.rbPoint = QRadioButton("Point (left click)")
        vbox.addWidget(self.rbPoint)

        self.rbDistance = QRadioButton("Distance (start: left click, end: right click)")
        vbox.addWidget(self.rbDistance)

        self.rbArea = QRadioButton("Area (left click for area vertices, right click to close area)")
        vbox.addWidget(self.rbArea)

        self.rbAngle = QRadioButton("Angle (vertex: left click, segments: right click)")
        vbox.addWidget(self.rbAngle)

        self.cbPersistentMeasurements = QCheckBox("Measurements are persistent")
        self.cbPersistentMeasurements.setChecked(True)
        vbox.addWidget(self.cbPersistentMeasurements)

        vbox.addWidget(QLabel("<b>Scale</b>"))

        hbox1 = QHBoxLayout()

        self.lbRef = QLabel("Reference")
        hbox1.addWidget(self.lbRef)

        self.lbPx = QLabel("Pixels")
        hbox1.addWidget(self.lbPx)

        vbox.addLayout(hbox1)

        hbox2 = QHBoxLayout()

        self.leRef = QLineEdit()
        self.leRef.setText("1")
        hbox2.addWidget(self.leRef)

        self.lePx = QLineEdit()
        self.lePx.setText("1")
        hbox2.addWidget(self.lePx)

        vbox.addLayout(hbox2)

        self.pte = QPlainTextEdit()
        vbox.addWidget(self.pte)

        self.status_lb = QLabel()
        vbox.addWidget(self.status_lb)

        hbox3 = QHBoxLayout()

        self.pbClear = QPushButton("Clear measurements", clicked=self.pbClear_clicked)
        hbox3.addWidget(self.pbClear)

        self.pbSave = QPushButton("Save results", clicked=self.pbSave_clicked)
        hbox3.addWidget(self.pbSave)

        self.pbClose = QPushButton(cfg.CLOSE, clicked=self.pbClose_clicked)
        hbox3.addWidget(self.pbClose)

        vbox.addLayout(hbox3)

    def pbClear_clicked(self):
        """
        clear measurements draw and results
        """
        self.draw_mem = {}
        self.pte.clear()
        self.clearSignal.emit()

    def pbClose_clicked(self):
        if not self.flagSaved:
            response = dialog.MessageDialog(
                cfg.programName,
                "The current results are not saved. Do you want to save results before closing?",
                [cfg.YES, cfg.NO, cfg.CANCEL],
            )
            if response == cfg.YES:
                self.pbSave_clicked()
            if response == cfg.CANCEL:
                return
        self.closeSignal.emit()

    def pbSave_clicked(self):
        """
        save results
        """
        if self.pte.toPlainText():
            fileName, _ = QFileDialog().getSaveFileName(self, "Save measurement results", "", "Text files (*.txt);;All files (*)")
            if fileName:
                with open(fileName, "w") as f:
                    f.write(self.pte.toPlainText())
                self.flagSaved = True
        else:
            QMessageBox.information(self, cfg.programName, "There are no results to save")


if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)
    w = wgMeasurement(logging.getLogger().getEffectiveLevel())
    w.show()

    sys.exit(app.exec_())
