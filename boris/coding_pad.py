#!/usr/bin/env python3

"""
BORIS
Behavioral Observation Research Interactive Software
Copyright 2012-2020 Olivier Friard

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


from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *

import sys
from boris.config import *
from boris.utilities import *


class CodingPad(QWidget):

    clickSignal = pyqtSignal(str)
    sendEventSignal = pyqtSignal(QEvent)
    close_signal = pyqtSignal(QRect)

    def __init__(self, pj, filtered_behaviors, parent=None):
        super(CodingPad, self).__init__(parent)
        self.pj = pj
        self.filtered_behaviors = filtered_behaviors

        self.setWindowTitle("Coding pad")
        self.grid = QGridLayout(self)
        self.installEventFilter(self)
        self.compose()

    def compose(self):
        for i in reversed(range(self.grid.count())):
            self.grid.itemAt(i).widget().setParent(None)

        self.colors_dict = {}
        if BEHAVIORAL_CATEGORIES in self.pj:
            for idx, category in enumerate(set([self.pj[ETHOGRAM][x]["category"]
                                                for x in self.pj[ETHOGRAM]
                                                if "category" in self.pj[ETHOGRAM][x]])):
                self.colors_dict[category] = CATEGORY_COLORS_LIST[idx % len(CATEGORY_COLORS_LIST)]

        if self.colors_dict:
            behaviorsList = [[self.pj[ETHOGRAM][x]["category"], self.pj[ETHOGRAM][x]["code"]]
                             for x in sorted_keys(self.pj[ETHOGRAM])
                             if "category" in self.pj[ETHOGRAM][x] and self.pj[ETHOGRAM][x]["code"] in self.filtered_behaviors]
        else:
            behaviorsList = [["", self.pj[ETHOGRAM][x]["code"]]
                             for x in sorted_keys(self.pj[ETHOGRAM]) if self.pj[ETHOGRAM][x]["code"] in self.filtered_behaviors]
        dim = int(len(behaviorsList)**0.5 + 0.999)

        c = 0
        for i in range(1, dim + 1):
            for j in range(1, dim + 1):
                if c >= len(behaviorsList):
                    break
                self.addWidget(behaviorsList[c][1], i, j)
                c += 1


    def addWidget(self, behaviorCode, i, j):

        self.grid.addWidget(Button(), i, j)
        index = self.grid.count() - 1
        widget = self.grid.itemAt(index).widget()

        if widget is not None:
            widget.pushButton.setText(behaviorCode)
            if self.colors_dict:
                color = self.colors_dict[[self.pj[ETHOGRAM][x]["category"]
                                         for x in self.pj[ETHOGRAM] if self.pj[ETHOGRAM][x]["code"] == behaviorCode][0]]
            else:
                color = CATEGORY_COLORS_LIST[0]
            widget.pushButton.setStyleSheet(("background-color: {}; border-radius: 0px; min-width: 50px;max-width: 200px; "
                                             "min-height:50px; max-height:200px; font-weight: bold;").format(color))
            widget.pushButton.clicked.connect(lambda: self.click(behaviorCode))


    def click(self, behaviorCode):
        self.clickSignal.emit(behaviorCode)


    def eventFilter(self, receiver, event):
        """
        send event (if keypress) to main window
        """
        if(event.type() == QEvent.KeyPress):
            self.sendEventSignal.emit(event)
            return True
        else:
            return False

    def closeEvent(self, event):
        """
        send event for widget geometry memory
        """
        self.close_signal.emit(self.geometry())


class Button(QWidget):
    def __init__(self, parent=None):
        super(Button, self).__init__(parent)
        self.pushButton = QPushButton()
        self.pushButton.setFocusPolicy(Qt.NoFocus)
        layout = QHBoxLayout()
        layout.addWidget(self.pushButton)
        self.setLayout(layout)
