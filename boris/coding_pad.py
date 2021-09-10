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
    close_signal = pyqtSignal(QRect)

    def __init__(self, pj, filtered_behaviors, parent=None):
        super().__init__(parent)
        self.pj = pj
        self.filtered_behaviors = filtered_behaviors
        '''
        self.button_css = ("border-radius: 0px; min-width: 50px; max-width: 200px; "
                           "min-height:50px; max-height:200px; font-weight: bold;")
        '''
        self.button_css = ("border-radius: 0px; min-width: 50px; min-height:50px; font-weight: bold; max-height:5000px; max-width: 5000px;")

        self.setWindowTitle("Coding pad")
        self.grid = QGridLayout(self)
        self.installEventFilter(self)
        self.compose()

        #self.resize(200,200)


    def compose(self):
        for i in reversed(range(self.grid.count())):
            self.grid.itemAt(i).widget().setParent(None)

        self.all_behaviors = [self.pj[cfg.ETHOGRAM][x][cfg.BEHAVIOR_CODE] for x in util.sorted_keys(self.pj[cfg.ETHOGRAM])]
        self.colors_dict = {}

        self.unique_behavioral_categories = sorted(set([self.pj[cfg.ETHOGRAM][x].get(cfg.BEHAVIOR_CATEGORY, "") for x in self.pj[cfg.ETHOGRAM]]))
        for idx, category in enumerate(self.unique_behavioral_categories):   # sorted list of unique behavior categories
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


    def addWidget(self, behaviorCode, i, j):

        self.grid.addWidget(Button(), i, j)
        index = self.grid.count() - 1
        widget = self.grid.itemAt(index).widget()

        if widget is not None:
            widget.pushButton.setText(behaviorCode)
            if self.unique_behavioral_categories != ['']:  # behavioral categories are used
                color = self.colors_dict[[self.pj[cfg.ETHOGRAM][x][cfg.BEHAVIOR_CATEGORY]
                                             for x in self.pj[cfg.ETHOGRAM] if self.pj[cfg.ETHOGRAM][x][cfg.BEHAVIOR_CODE] == behaviorCode][0]]
            else:
                # behavioral categories are not defined
                behavior_position = int([x for x in util.sorted_keys(self.pj[cfg.ETHOGRAM]) if self.pj[cfg.ETHOGRAM][x][cfg.BEHAVIOR_CODE] == behaviorCode][0])
                color = cfg.BEHAVIORS_PLOT_COLORS[behavior_position % len(cfg.BEHAVIORS_PLOT_COLORS)].replace("tab:", "")

            widget.color = color
            widget.pushButton.setStyleSheet(self.button_css + f"background-color: {color};")
            widget.pushButton.clicked.connect(lambda: self.click(behaviorCode))


    def resizeEvent(self, event):
        """
        Resize event
        button are redesigned with new font size
        """
        print("resize", event.size())
        for index in range(self.grid.count()):

            button_size = self.grid.itemAt(index).widget().pushButton.size()
            # print("button size", button_size)

            print(len(self.all_behaviors))
            font = QFont('Arial', 20)
            '''
            size = 500
            while True:
                font.setPixelSize(size)
                metrics = QFontMetrics(font)
                text_width = metrics.width(self.grid.itemAt(index).widget().pushButton.text())
                text_height = metrics.height()
                if (text_width < button_size.width()) and (text_height < button_size.height()) or (size < 20):
                    break
                size -= 10

            print("size", size, self.grid.itemAt(index).widget().pushButton.text())
            '''
            self.grid.itemAt(index).widget().pushButton.setFont(font)

            #metrics = QFontMetrics(self.grid.itemAt(index).widget().pushButton.font())
            #print(metrics.width(self.grid.itemAt(index).widget().pushButton.text()))


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


