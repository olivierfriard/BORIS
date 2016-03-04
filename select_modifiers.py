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


from PyQt4.QtCore import *
from PyQt4.QtGui import *
import re
import config

class ModifiersRadioButton(QDialog):

    #sendEvent = pyqtSignal(QEvent)

    def __init__(self, code, modifiers_list, currentModifier):

        super(ModifiersRadioButton, self).__init__()

        self.setWindowTitle(config.programName)

        currentModifierList = currentModifier.split("|")

        Vlayout = QVBoxLayout()
        widget = QWidget(self)
        widget.setLayout(Vlayout)

        label = QLabel()
        label.setText("Choose the modifier{0} for <b>{1}</b> event".format( 's'*(len(modifiers_list)>1), code))
        Vlayout.addWidget(label)

        count = 1
        for idx, modifiers in enumerate(modifiers_list):

            if len(modifiers_list) > 1:
                lb = QLabel()
                lb.setText("Modifiers #{}".format(count))
                count += 1
                Vlayout.addWidget(lb)

            lw = QListWidget(widget)
            lw.setObjectName("lw_modifiers")
            lw.installEventFilter(self)
            lw.addItem(QListWidgetItem("None"))

            for modifier in modifiers:

                item = QListWidgetItem(modifier)
                lw.addItem(item)

                if currentModifierList != [""]:
                    if re.sub(" \(.\)", "", modifier) == currentModifierList[idx]:
                        lw.setItemSelected(item, True)

            Vlayout.addWidget(lw)

        pbOK = QPushButton("OK")
        pbOK.clicked.connect(self.pbOK_clicked)
        Vlayout.addWidget(pbOK)

        self.setLayout(Vlayout)

        self.installEventFilter(self)

        #self.show()

    def eventFilter(self, receiver, event):
        '''
        send event (if keypress) to main window
        '''
        if(event.type() == QEvent.KeyPress):
            ek = event.key()
            print(ek, chr(ek))
            print("({})".format(ek).upper())

            for widget in self.children():
                if widget.objectName() == "lw_modifiers":
                    for item in widget.items():
                        if "({})".format(ek).upper() in item.text().upper():
                            widget.setItemSelected(item, True)

            return True
        else:
            return False

    """
    def keyPressEvent(self, event):
        print("keypressed")

        ek = event.key()

        print( ek )
        print('(' + chr(ek + 32) + ')')

        if ek == 16777220 or ek == 16777221:
            self.accept()
            return

        for widget in self.children():
            if widget.objectName() == "lw_modifiers":
                for item in widget.selectedItems():
                    if '(' + chr(ek + 32) + ')' in item.text():
                        widget.setItemSelected(item, True)

        '''
        # check radio button if key are pressed
        l = self.layout()
        modifiers = []
        for i in range(0, l.count()):   # iterate on all widget/layout
            layout = l.itemAt(i).layout()
            if (layout) and (type(layout) is QHBoxLayout):
                for j in range(0, layout.count()):   # iterate on all widget
                    widget = layout.itemAt(j).widget()
                    if (widget != 0) and (type(widget) is QRadioButton):
                        if '(' + chr(ek + 32) + ')' in widget.text():
                            widget.setChecked(True)
        '''
    """

    def getModifiers(self):
        """
        get modifiers
        returns list of selected modifiers
        """
        modifiers = []
        for widget in self.children():
            if widget.objectName() == "lw_modifiers":
                for item in widget.selectedItems():
                    modifiers.append(re.sub(" \(.\)", "",item.text()))
        return modifiers



    def pbOK_clicked(self):
        self.accept()
