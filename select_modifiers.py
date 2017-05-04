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
from config import *
from utilities import sorted_keys

class ModifiersList(QDialog):

    def __init__(self, code, modifiers_dict, currentModifier):

        super().__init__()
        self.setWindowTitle(programName)
        self.setWindowFlags(Qt.WindowStaysOnTopHint)

        self.modifiers_dict = dict(modifiers_dict)
        currentModifierList = currentModifier.split("|")

        V1layout = QVBoxLayout()
        label = QLabel()
        label.setText("Choose the modifier{0} for <b>{1}</b> behavior".format("s" * (len(self.modifiers_dict) > 1), code))
        V1layout.addWidget(label)

        Hlayout = QHBoxLayout()
        self.modifiersSetNumber = 0

        for idx in sorted_keys(modifiers_dict):

            V2layout = QVBoxLayout()

            self.modifiersSetNumber += 1
            '''if len(modifiers_dict) > 1:'''

            lb = QLabel()
            lb.setText("Modifier <b>{}</b>".format(self.modifiers_dict[idx]["name"]))
            V2layout.addWidget(lb)

            if self.modifiers_dict[idx]["type"] in [SINGLE_SELECTION, MULTI_SELECTION]:
                lw = QListWidget()
                self.modifiers_dict[idx]["widget"] = lw
                lw.setObjectName("lw_modifiers")
                lw.installEventFilter(self)

                item = QListWidgetItem("None")
                lw.addItem(item)
                if QT_VERSION_STR[0] == "4":
                    lw.setItemSelected(item, True)
                else:
                    item.setSelected(True)

                #lw.setFixedHeight(len(modifiers_dict[idx]["values"])*20)
                for modifier in self.modifiers_dict[idx]["values"]:
                    item = QListWidgetItem(modifier)
                    if self.modifiers_dict[idx]["type"] == MULTI_SELECTION:
                        item.setCheckState(Qt.Unchecked)

                        # previously selected
                        if currentModifierList != [""] and modifier in currentModifierList[int(idx)]:
                            item.setCheckState(Qt.Checked)
                    lw.addItem(item)
                    if self.modifiers_dict[idx]["type"] == SINGLE_SELECTION:
                        if currentModifierList != [""] and re.sub(" \(.\)", "", modifier) == currentModifierList[int(idx)]:
                            if QT_VERSION_STR[0] == "4":
                                lw.setItemSelected(item, True)
                            else:
                                item.setSelected(True)
                V2layout.addWidget(lw)

            if self.modifiers_dict[idx]["type"] in [NUMERIC_MODIFIER]:
                le = QLineEdit()
                self.modifiers_dict[idx]["widget"] = le

                if currentModifierList != [""] and currentModifierList[int(idx)] != "None":
                    le.setText(currentModifierList[int(idx)])

                V2layout.addWidget(le)

                # vertical spacer
                spacerItem = QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding)
                V2layout.addItem(spacerItem)

            Hlayout.addLayout(V2layout)

        V1layout.addLayout(Hlayout)

        H2layout = QHBoxLayout()
        H2layout.addStretch(1)

        pbCancel = QPushButton(CANCEL)
        pbCancel.clicked.connect(self.reject)
        H2layout.addWidget(pbCancel)

        pbOK = QPushButton(OK)
        pbOK.setDefault(True)
        pbOK.clicked.connect(self.pbOK_clicked)
        H2layout.addWidget(pbOK)

        V1layout.addLayout(H2layout)
        self.setLayout(V1layout)

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

                        if ek in function_keys:
                            if "({})".format(function_keys[ek]) in widget.item(index).text().upper():
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
        for idx in sorted_keys(self.modifiers_dict):

            self.modifiers_dict[idx]["selected"] = []
            if self.modifiers_dict[idx]["type"] == MULTI_SELECTION:

                for j in range(self.modifiers_dict[idx]["widget"].count()):

                    if self.modifiers_dict[idx]["widget"].item(j).checkState() == Qt.Checked:
                        self.modifiers_dict[idx]["selected"].append(self.modifiers_dict[idx]["widget"].item(j).text())

            if self.modifiers_dict[idx]["type"] == SINGLE_SELECTION:
                for item in self.modifiers_dict[idx]["widget"].selectedItems():
                    self.modifiers_dict[idx]["selected"].append(re.sub(" \(.*\)", "", item.text()))

            if self.modifiers_dict[idx]["type"] == NUMERIC_MODIFIER:
                self.modifiers_dict[idx]["selected"] = self.modifiers_dict[idx]["widget"].text() if self.modifiers_dict[idx]["widget"].text() else "None"

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

        for idx in sorted_keys(self.modifiers_dict):
            if self.modifiers_dict[idx]["type"] == NUMERIC_MODIFIER:
                if self.modifiers_dict[idx]["widget"].text():
                    try:
                       val = float(self.modifiers_dict[idx]["widget"].text())
                    except:
                        QMessageBox.warning(self, programName, "<b>{}</b> is not a numeric value".format(self.modifiers_dict[idx]["widget"].text()))
                        return

        self.accept()
