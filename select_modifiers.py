#!/usr/bin/env python

"""
BORIS
Behavioral Observation Research Interactive Software
Copyright 2012-2014 Olivier Friard

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

from PySide.QtCore import *
from PySide.QtGui import *
import re
import config


class ModifiersRadioButton(QDialog):

    def __init__(self, code, modifiers_list, currentModifier, mode):   ### mode: normal / embeded

        super(ModifiersRadioButton, self).__init__()

        self.setWindowTitle(config.programName)

        currentModifierList = currentModifier.split('|')

        Vlayout = QVBoxLayout() 
        widget = QWidget(self)  
        widget.setLayout(Vlayout)
    
        if mode == 'normal':
            label = QLabel()
            label.setText('Choose the modifier' + 's'*(len(modifiers_list)-1) + ' for <b>' + code + '</b> event')
            Vlayout.addWidget(label)

        count = 1
        for idx, modifiers in enumerate(modifiers_list):

            if len(modifiers_list) > 1:
                lb = QLabel()
                lb.setText('Modifiers #%d' % count)
                count += 1
                Vlayout.addWidget(lb)
            
            group = QButtonGroup(widget)
            HLayout = QHBoxLayout()
            
            txt = 'None'
            r = QRadioButton(txt)
            r.setChecked(True)
            group.addButton(r)
            HLayout.addWidget(r)

            for modifier in modifiers:
                txt = modifier
                r = QRadioButton( txt )

                ### check if current modifier
                
                if currentModifierList != ['']:
                    print 'r75 ',modifier, currentModifierList[idx]
                    
                    if re.sub(' \(.\)', '', modifier) == currentModifierList[idx]:
                    #if modifier == currentModifierList[idx]:
                        r.setChecked(True)
                group.addButton(r)
                HLayout.addWidget(r)

            Vlayout.addLayout(HLayout)

        if mode == 'normal':
            pbOK = QPushButton('OK')
            pbOK.clicked.connect(self.pbOK_clicked)
            Vlayout.addWidget(pbOK)

        self.setLayout(Vlayout)
        self.show()


    def keyPressEvent(self, event):
        print( 'key press event' )
        ek = event.key()
        if ek == 16777220 or ek == 16777221:
            self.accept()

        ### check radio button if key are pressed
        l = self.layout()
        modifiers = []
        for i in range(0, l.count()):   ### iterate on all widget/layout
            layout = l.itemAt(i).layout()
            if (layout) and (type(layout) is QHBoxLayout):
                for j in range(0, layout.count()):   ### iterate on all widget 
                    widget = layout.itemAt(j).widget()
                    if (widget != 0) and (type(widget) is QRadioButton):
                        if '(' + chr(ek + 32) + ')' in widget.text():
                            widget.setChecked(True)


    def getModifiers(self):
        '''
        get modifiers
        returns list of selected modifiers
        '''

        l = self.layout()
        modifiers = []
        for i in range(0, l.count()):   ### iterate on all widget/layout
            layout = l.itemAt(i).layout()
            if (layout) and (type(layout) is QHBoxLayout):
                for j in range(0, layout.count()):   ### iterate on all widget 
                    widget = layout.itemAt(j).widget()
                    if (widget != 0) and (type(widget) is QRadioButton):
                        if widget.isChecked():
                            modifiers.append(  re.sub(' \(.\)', '', widget.text())  )

        return modifiers

    def pbOK_clicked(self):
        self.accept()
