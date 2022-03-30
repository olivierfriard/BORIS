"""
BORIS
Behavioral Observation Research Interactive Software
Copyright 2012-2022 Olivier Friard

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
from . import menu_options

from PyQt5.QtCore import pyqtSignal, Qt
from PyQt5.QtWidgets import (
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

    closeSignal, clearSignal = pyqtSignal(), pyqtSignal()
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

        self.pbClose = QPushButton("Close", clicked=self.pbClose_clicked)
        hbox3.addWidget(self.pbClose)

        vbox.addLayout(hbox3)

    def closeEvent(self, event):

        print("close event")
        self.pbClose_clicked()

    def pbClear_clicked(self):
        """
        clear measurements draw and results
        """
        self.draw_mem = {}
        self.pte.clear()
        self.clearSignal.emit()

    def pbClose_clicked(self):

        print("pb close clicked")
        if not self.flagSaved:
            response = dialog.MessageDialog(
                cfg.programName,
                "The current measurements are not saved. Do you want to save results before closing?",
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
            fileName, _ = QFileDialog().getSaveFileName(
                self, "Save geometric measurements", "", "Text files (*.txt);;All files (*)"
            )
            if fileName:
                try:
                    with open(fileName, "w") as f:
                        f.write(self.pte.toPlainText())
                    self.flagSaved = True
                except Exception:
                    QMessageBox.warning(self, cfg.programName, "An error occured during saving the measurements")
        else:
            QMessageBox.information(self, cfg.programName, "There are no measurements to save")


def geometric_measurements(self):
    """
    active the geometric measurement widget
    """

    def close_measurement_widget():

        self.geometric_measurements_mode = False
        for n_player, dw in enumerate(self.dw_player):
            dw.frame_viewer.clear()
            dw.stack.setCurrentIndex(0)
            dw.setWindowTitle(f"Player #{n_player + 1}")
        self.measurement_w.close()
        menu_options.update_menu(self)

    """ to be deleted 2021-09-03
    def clear_measurements():
        pass
    """

    self.geometric_measurements_mode = True
    self.pause_video()

    menu_options.update_menu(self)

    self.measurement_w = wgMeasurement()
    self.measurement_w.draw_mem = {}
    self.measurement_w.setWindowFlags(Qt.WindowStaysOnTopHint)
    self.measurement_w.closeSignal.connect(close_measurement_widget)
    """ to be deleted 2021-09-03
    self.measurement_w.clearSignal.connect(clear_measurements)
    """
    self.measurement_w.show()

    for _, dw in enumerate(self.dw_player):
        dw.setWindowTitle("Geometric measurements")
        dw.stack.setCurrentIndex(1)
        self.extract_frame(dw)


if __name__ == "__main__":

    import sys

    app = QApplication(sys.argv)
    w = wgMeasurement(logging.getLogger().getEffectiveLevel())
    w.show()

    sys.exit(app.exec_())
