#!/usr/bin/env python3

"""
BORIS
Behavioral Observation Research Interactive Software
Copyright 2012-2017 Olivier Friard

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

import re
import config

class ModifiersList(QDialog):

    def __init__(self, code, modifiers_list, currentModifier):

        super(ModifiersList, self).__init__()

        self.setWindowTitle(config.programName)
        self.setWindowFlags(Qt.WindowStaysOnTopHint)

        currentModifierList = currentModifier.split("|")

        Vlayout = QVBoxLayout()
        widget = QWidget(self)
        widget.setLayout(Vlayout)

        label = QLabel()
        label.setText("Choose the modifier{0} for <b>{1}</b> event".format("s" * (len(modifiers_list) > 1), code))
        Vlayout.addWidget(label)

        self.modifiersSetNumber = 0

        for idx, modifiers in enumerate(modifiers_list):

            self.modifiersSetNumber += 1
            if len(modifiers_list) > 1:
                lb = QLabel()
                lb.setText("Modifiers #{}".format(self.modifiersSetNumber))
                Vlayout.addWidget(lb)

            lw = QListWidget(widget)
            lw.setObjectName("lw_modifiers")
            lw.installEventFilter(self)

            item = QListWidgetItem("None")
            lw.addItem(item)
            if QT_VERSION_STR[0] == "4":
                lw.setItemSelected(item, True)
            else:
                item.setSelected(True)

            for modifier in modifiers:

                item = QListWidgetItem(modifier)
                lw.addItem(item)

                if currentModifierList != [""]:
                    if re.sub(" \(.\)", "", modifier) == currentModifierList[idx]:

                        if QT_VERSION_STR[0] == "4":
                            lw.setItemSelected(item, True)
                        else:
                            item.setSelected(True)

            Vlayout.addWidget(lw)

        pbCancel = QPushButton("Cancel")
        pbCancel.clicked.connect(self.reject)
        Vlayout.addWidget(pbCancel)
        pbOK = QPushButton("OK")
        pbOK.setDefault(True)
        pbOK.clicked.connect(self.pbOK_clicked)
        Vlayout.addWidget(pbOK)

        self.setLayout(Vlayout)

        self.installEventFilter(self)
        #self.setMinimumSize(630, 50)
        self.setMaximumSize(1024 , 960)


    def eventFilter(self, receiver, event):
        """
        send event (if keypress) to main window
        """
        if(event.type() == QEvent.KeyPress):
            ek = event.key()
            # close dialog if enter pressed
            if ek == 16777220:   # Key_Enter
            #if ek == Qt.Key_Enter:
                self.accept()
                return True

            for widget in self.children():
                if widget.objectName() == "lw_modifiers":
                    for index in range(widget.count()):

                        if ek in config.function_keys:
                            if "({})".format(config.function_keys[ek]) in widget.item(index).text().upper():
                                if QT_VERSION_STR[0] == "4":
                                    widget.setItemSelected(widget.item(index), True)

                                else:
                                    widget.item(index).setSelected(True)

                                if self.modifiersSetNumber == 1:
                                    self.accept()
                                    return True

                        if ek < 1114112 and "({})".format(chr(ek)).upper() in widget.item(index).text().upper():

                            if QT_VERSION_STR[0] == "4":
                                widget.setItemSelected(widget.item(index), True)
                            else:
                                widget.item(index).setSelected(True)

                            # close dialog if one set of modifiers
                            if self.modifiersSetNumber == 1:
                                self.accept()
                                return True

            return True
        else:
            return False

    def getModifiers(self):
        """
        get modifiers
        returns list of selected modifiers
        """
        modifiers = []
        for widget in self.children():
            if widget.objectName() == "lw_modifiers":
                for item in widget.selectedItems():
                    modifiers.append(re.sub(" \(.*\)", "", item.text()))
        return modifiers

    def pbOK_clicked(self):
        self.accept()
