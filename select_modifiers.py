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

    def __init__(self, code, modifiers_dict, currentModifier):

        super(ModifiersList, self).__init__()

        self.modifiers_dict = modifiers_dict

        self.setWindowTitle(config.programName)
        self.setWindowFlags(Qt.WindowStaysOnTopHint)

        currentModifierList = currentModifier.split("|")
        print("currentModifierList",currentModifierList)

        Vlayout = QVBoxLayout()
        widget = QWidget(self)
        widget.setLayout(Vlayout)

        label = QLabel()
        label.setText("Choose the modifier{0} for <b>{1}</b> behavior".format("s" * (len(modifiers_dict) > 1), code))
        Vlayout.addWidget(label)

        self.modifiersSetNumber = 0

        for idx in sorted(modifiers_dict.keys()):

            self.modifiersSetNumber += 1
            if len(modifiers_dict) > 1:
                lb = QLabel()
                lb.setText("Modifiers <b>{}</b>".format(modifiers_dict[idx]["name"]))
                Vlayout.addWidget(lb)

            lw = QListWidget(widget)
            self.modifiers_dict[idx]["widget"] = lw
            lw.setObjectName("lw_modifiers")

            lw.installEventFilter(self)

            item = QListWidgetItem("None")
            lw.addItem(item)
            if QT_VERSION_STR[0] == "4":
                lw.setItemSelected(item, True)
            else:
                item.setSelected(True)

            lw.setFixedHeight(len(modifiers_dict[idx]["values"])*20)
            for modifier in modifiers_dict[idx]["values"]:

                item = QListWidgetItem(modifier)

                if modifiers_dict[idx]["type"] == config.MULTI_SELECTION:
                    item.setCheckState(Qt.Unchecked)

                    # previously selected
                    if currentModifierList != [""] and modifier in currentModifierList[idx].split(","):
                        item.setCheckState(Qt.Checked)

                lw.addItem(item)

                if modifiers_dict[idx]["type"] == config.SINGLE_SELECTION:
                    if currentModifierList != [""] and re.sub(" \(.\)", "", modifier) == currentModifierList[idx]:
                        if QT_VERSION_STR[0] == "4":
                            lw.setItemSelected(item, True)
                        else:
                            item.setSelected(True)

            Vlayout.addWidget(lw)

        pbCancel = QPushButton(config.CANCEL)
        pbCancel.clicked.connect(self.reject)
        Vlayout.addWidget(pbCancel)
        pbOK = QPushButton(config.OK)
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

            #if ek == 16777220:   # Key_Enter

            if ek == Qt.Key_Escape: # close
                self.reject()
                return False

            if ek == Qt.Key_Enter or ek == Qt.Key_Return: # enter or enter from numeric pad
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
        for idx in sorted(self.modifiers_dict.keys()):

            self.modifiers_dict[idx]["selected"] = []
            if self.modifiers_dict[idx]["type"] == config.MULTI_SELECTION:

                for j in range(self.modifiers_dict[idx]["widget"].count()):

                    if self.modifiers_dict[idx]["widget"].item(j).checkState() == Qt.Checked:
                        #modifiers.append()
                        self.modifiers_dict[idx]["selected"].append(self.modifiers_dict[idx]["widget"].item(j).text())

            if self.modifiers_dict[idx]["type"] == config.SINGLE_SELECTION:
                for item in self.modifiers_dict[idx]["widget"].selectedItems():
                    #modifiers.append(re.sub(" \(.*\)", "", item.text()))
                    self.modifiers_dict[idx]["selected"].append(re.sub(" \(.*\)", "", item.text()))

        '''
        for widget in self.children():
            if widget.objectName() == "lw_modifiers_classic":
                for item in widget.selectedItems():
                    modifiers.append(re.sub(" \(.*\)", "", item.text()))
            if widget.objectName() == "lw_modifiers_from_set":
                for idx in range(widget.count()):
                    if widget.item(idx).checkState() == Qt.Checked:
                        modifiers.append(widget.item(idx).text())
        '''

        return self.modifiers_dict

    def pbOK_clicked(self):
        self.accept()
