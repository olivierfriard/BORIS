"""
BORIS
Behavioral Observation Research Interactive Software
Copyright 2012-2021 Olivier Friard

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


from . import config as cfg
from . import utilities as util


class Button(QWidget):
    def __init__(self, parent=None):
        super(Button, self).__init__(parent)
        self.pushButton = QPushButton()
        self.pushButton.setFocusPolicy(Qt.NoFocus)
        layout = QHBoxLayout()
        layout.addWidget(self.pushButton)
        self.setLayout(layout)


class CodingPad(QWidget):

    clickSignal = pyqtSignal(str)
    sendEventSignal = pyqtSignal(QEvent)
    close_signal = pyqtSignal(QRect, dict)

    def __init__(self, pj, filtered_behaviors, parent=None):
        super().__init__(parent)
        self.pj = pj
        self.filtered_behaviors = filtered_behaviors

        self.preferences = {"button font size": 20,
                                       "button color": "category"}

        self.button_css = ("border-radius: 0px; min-width: 50px; min-height:50px; font-weight: bold; max-height:5000px; max-width: 5000px;")
        self.button_css = ("min-width: 50px; min-height:50px; font-weight: bold; max-height:5000px; max-width: 5000px;")

        self.setWindowTitle("Coding pad")

        self.grid = QGridLayout(self)

        self.installEventFilter(self)
        self.compose()


    def config(self):
        """
        Configure the coding pad
        """
        if self.cb_config.currentIndex() == 1:   # increase text size
            self.preferences["button font size"] += 4
        if self.cb_config.currentIndex() == 2:   # decrease text size
            self.preferences["button font size"] += 4
        if self.cb_config.currentIndex() == 3:
            self.preferences["button color"] = cfg.BEHAVIOR_CATEGORY
        if self.cb_config.currentIndex() == 4:
            self.preferences["button color"] = "behavior"
        if self.cb_config.currentIndex() == 5:
            self.preferences["button color"] = "no color"



        self.cb_config.setCurrentIndex(0)
        self.button_configuration()


    def compose(self):
        """
        Add buttons to coding pad
        """
        for i in reversed(range(self.grid.count())):
            if self.grid.itemAt(i).widget() is not None:
                self.grid.itemAt(i).widget().setParent(None)

        # combobox for coding pad configuration
        vlayout = QHBoxLayout()
        self.cb_config = QComboBox()
        self.cb_config.addItems(["Choose an option to configure",
                                 "Increase button text size",
                                 "Decrease button text size",
                                 "Color button by behavioral category",
                                 "Color button by behavior",
                                 "No color"])
        self.cb_config.currentIndexChanged.connect(self.config)
        vlayout.addWidget(self.cb_config)
        self.grid.addLayout(vlayout, 0, 1, 1, 1)

        self.all_behaviors = [self.pj[cfg.ETHOGRAM][x][cfg.BEHAVIOR_CODE] for x in util.sorted_keys(self.pj[cfg.ETHOGRAM])]
        self.colors_dict = {}

        # sorted list of unique behavior categories
        self.unique_behavioral_categories = sorted(set([self.pj[cfg.ETHOGRAM][x].get(cfg.BEHAVIOR_CATEGORY, "") for x in self.pj[cfg.ETHOGRAM]]))
        for idx, category in enumerate(self.unique_behavioral_categories):
            self.colors_dict[category] = cfg.CATEGORY_COLORS_LIST[idx % len(cfg.CATEGORY_COLORS_LIST)]

        behaviorsList = [[self.pj[cfg.ETHOGRAM][x][cfg.BEHAVIOR_CATEGORY], self.pj[cfg.ETHOGRAM][x][cfg.BEHAVIOR_CODE]]
                            for x in util.sorted_keys(self.pj[cfg.ETHOGRAM])
                            if cfg.BEHAVIOR_CATEGORY in self.pj[cfg.ETHOGRAM][x] and self.pj[cfg.ETHOGRAM][x][cfg.BEHAVIOR_CODE] in self.filtered_behaviors]

        # square grid dimension
        dim = int(len(behaviorsList)**0.5 + 0.999)

        c = 0
        for i in range(1, dim + 1):
            for j in range(1, dim + 1):
                if c >= len(behaviorsList):
                    break
                self.addWidget(behaviorsList[c][1], i, j)
                c += 1

        self.button_configuration()


    def addWidget(self, behaviorCode, i, j):

        self.grid.addWidget(Button(), i, j)
        index = self.grid.count() - 1
        widget = self.grid.itemAt(index).widget()

        if widget is not None:
            widget.pushButton.setText(behaviorCode)
            widget.pushButton.clicked.connect(lambda: self.click(behaviorCode))


    def button_configuration(self):
        """
        configure the font and color of buttons
        """

        for index in range(self.grid.count()):
            if self.grid.itemAt(index).widget() is None:
                continue
            behavior_code = self.grid.itemAt(index).widget().pushButton.text()
            if self.preferences["button color"] == cfg.BEHAVIOR_CATEGORY:
                color = self.colors_dict[[self.pj[cfg.ETHOGRAM][x][cfg.BEHAVIOR_CATEGORY]
                                             for x in self.pj[cfg.ETHOGRAM] if self.pj[cfg.ETHOGRAM][x][cfg.BEHAVIOR_CODE] == behavior_code][0]]
            if self.preferences["button color"] == "behavior":
                # behavioral categories are not defined
                behavior_position = int([x for x in util.sorted_keys(self.pj[cfg.ETHOGRAM]) if self.pj[cfg.ETHOGRAM][x][cfg.BEHAVIOR_CODE] == behavior_code][0])
                color = cfg.BEHAVIORS_PLOT_COLORS[behavior_position % len(cfg.BEHAVIORS_PLOT_COLORS)].replace("tab:", "")
            if self.preferences["button color"] == "no color":
                color = cfg.NO_COLOR_CODING_PAD
            self.grid.itemAt(index).widget().pushButton.setStyleSheet(self.button_css + f"background-color: {color};")
            font = QFont("Arial", self.preferences["button font size"])
            self.grid.itemAt(index).widget().pushButton.setFont(font)



    def resizeEvent(self, event):
        """
        Resize event
        button are redesigned with new font size
        """
        self.button_configuration()


    def click(self, behaviorCode):
        """
        Button clicked
        """
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
        self.close_signal.emit(self.geometry(), self.preferences)


