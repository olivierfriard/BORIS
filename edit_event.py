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


import logging
from PyQt4.QtCore import *
from PyQt4.QtGui import *

import re
from config import *
import select_modifiers
import coding_map

from edit_event_ui import Ui_Form

class DlgEditEvent(QDialog, Ui_Form):

    def __init__(self, log_level, parent=None):

        super(DlgEditEvent, self).__init__(parent)
        logging.basicConfig(level=log_level)
        self.setupUi(self)

        self.currentModifier = ''

        #self.cobCode.currentIndexChanged.connect(self.codeChanged)
        self.pbOK.clicked.connect(self.accept)
        self.pbCancel.clicked.connect(self.reject)

        # embed modifiers selection
        self.mod = select_modifiers.ModifiersRadioButton('', [], '', 'embedded')
        self.VBoxLayout = QVBoxLayout()
        self.VBoxLayout.addWidget(self.mod)

        self.groupBox.setLayout(self.VBoxLayout)


    def codeMap_clicked(self):
        '''
        show a coding map window
        '''
        codingMap = [ self.pj['behaviors_conf'][x]['coding map'] for x in self.pj['behaviors_conf']  if  self.pj['behaviors_conf'][x]['code'] ==  self.cobCode.currentText() and self.pj['behaviors_conf'][x]['coding map']]
        
        codingMapWindow = coding_map.codingMapWindowClass( self.pj['coding_map'][ codingMap[0] ] )

        codingMapWindow.resize(640, 640)
        '''
        if self.codingMapWindowGeometry:
             self.codingMapWindow.restoreGeometry( self.codingMapWindowGeometry )
        '''

        if not codingMapWindow.exec_():
            return

        '''self.codingMapWindowGeometry = self.codingMapWindow.saveGeometry()'''

        self.mod.setText( codingMap[0] + '\nArea(s): ' + codingMapWindow.getCodes() )


    def codeChanged(self):


        # check if selected code has coding map
        codingMap = [ self.pj['behaviors_conf'][x]['coding map'] for x in self.pj['behaviors_conf']  if  self.pj['behaviors_conf'][x]['code'] ==  self.cobCode.currentText() and self.pj['behaviors_conf'][x]['coding map']]
        if codingMap:

            self.groupBox.setTitle('Coding map')
            # delete widget
            self.mod.setParent(None)
            self.mod = QPushButton( codingMap[0] + '\nArea(s): ' + self.currentModifier)
            self.mod.clicked.connect(self.codeMap_clicked)
            self.VBoxLayout.addWidget(self.mod)

        else:   # no coding map

            modifiers = [ self.pj['behaviors_conf'][x]['modifiers'] for x in self.pj['behaviors_conf']  if  self.pj['behaviors_conf'][x]['code'] ==  self.cobCode.currentText()][0]

            modifiersList = []
            if '|' in modifiers:
                modifiersStringsList = modifiers.split('|')
                for modifiersString in modifiersStringsList:
                    modifiersList.append([s.strip() for s in modifiersString.split(',')])

            else:
                modifiersList.append([s.strip() for s in modifiers.split(',')])

            # delete widget
            self.mod.setParent(None)
            if modifiersList != [['']]:
                self.groupBox.setTitle('Modifiers')

                self.mod = select_modifiers.ModifiersRadioButton(self.cobCode.currentText(), modifiersList, self.currentModifier, 'embedded')
            else:
                self.groupBox.setTitle('')
                self.mod = select_modifiers.ModifiersRadioButton('', [], '', 'embedded')
    
            self.VBoxLayout.addWidget(self.mod)
