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


from config import *

from PyQt4.QtCore import *
from PyQt4.QtGui import *

from add_modifier_ui import Ui_Dialog


class addModifierDialog(QDialog, Ui_Dialog):

    def __init__(self, modifiersStr, parent=None):

        super(addModifierDialog, self).__init__(parent)
        self.setupUi(self)

        self.modifierStr = modifiersStr

        self.pbAddModifier.clicked.connect(self.addModifier)
        self.pbAddSet.clicked.connect(self.addSet)
        self.pbRemoveSet.clicked.connect(self.removeSet)
        self.pbModifyModifier.clicked.connect(self.modifyModifier)
        self.pbRemoveModifier.clicked.connect(self.removeModifier)
        self.pbOK.clicked.connect(self.accept)
        self.pbCancel.clicked.connect(self.reject)

        self.tabWidgetModifiersSets.currentChanged.connect(self.tabWidgetModifiersSets_changed)

        # store modifiers in list

        if self.modifierStr:
            self.modifiersSets_list = []
            for modifiersSet in self.modifierStr.split('|'):
                self.modifiersSets_list.append( modifiersSet.split(','))
        else:
            self.modifiersSets_list = [[]]

        # create tab
        for i in range(len(self.modifiersSets_list)-1):
            self.tabWidgetModifiersSets.addTab( QWidget(), 'Set #%d' % (i+2))

        # set first tab as active
        self.lwModifiers.addItems( self.modifiersSets_list[0] )


    def addSet(self):
        self.tabWidgetModifiersSets.addTab( QWidget(), 'Set #%d' % (len(self.modifiersSets_list)+1))
        self.modifiersSets_list.append([])


    def removeSet(self):
        '''
        remove set of modifiers
        '''
        self.modifiersSets_list.pop( self.tabWidgetModifiersSets.currentIndex() )
        self.tabWidgetModifiersSets.removeTab(self.tabWidgetModifiersSets.currentIndex())


    def modifyModifier(self):
        '''
        modify modifier <- arrow
        '''
        
        if self.lwModifiers.currentIndex().row() >= 0:
            txt = self.lwModifiers.currentItem().text()
            code = ''
            if '(' in txt and ')' in txt:
                code = txt.split('(')[1].split(')')[0]

            self.leModifier.setText( txt.split('(')[0].strip())
            self.leCode.setText( code )

            self.modifiersSets_list[ self.tabWidgetModifiersSets.currentIndex() ].remove( self.lwModifiers.currentItem().text() )
            self.lwModifiers.takeItem(  self.lwModifiers.currentIndex().row()  )




    def removeModifier(self):
        '''
        remove modifier from set
        '''

        if self.lwModifiers.currentIndex().row() >= 0:
            self.modifiersSets_list[ self.tabWidgetModifiersSets.currentIndex() ].remove( self.lwModifiers.currentItem().text() )
            self.lwModifiers.takeItem(  self.lwModifiers.currentIndex().row()  )



    def addModifier(self):
        '''
        add a modifier to set
        '''

        txt = self.leModifier.text()

        for c in '(|)':
            if c in txt:
                QMessageBox.critical(self, programName, 'The modifier contain a character that is not allowed (|)!')
                self.leModifier.setFocus()
                return

        if txt:
            if len(self.leCode.text()) > 1:
                QMessageBox.critical(self, programName, 'The modifier key code can not exceed one key')
                self.leCode.setFocus()
                return

            if self.leCode.text():
                for c in '(|)':
                    if c in self.leCode.text():
                        QMessageBox.critical(self, programName, 'The modifier key code is not allowed (|)!')
                        self.leCode.setFocus()
                        return
                
                
                # check if code already exists
                if '(' + self.leCode.text() + ')' in self.getModifiers():
                    QMessageBox.critical(self, programName, 'The code %s already exists!' % self.leCode.text())
                    self.leCode.setFocus()
                    return
                txt += ' (%s)' % self.leCode.text()

            self.lwModifiers.addItem(  txt)
            self.modifiersSets_list[ self.tabWidgetModifiersSets.currentIndex() ].append( txt )
            self.leModifier.setText('')
            self.leCode.setText('')

        else:
            QMessageBox.critical(self, programName, 'No modifier to add!')
            self.leModifier.setFocus()



    def tabWidgetModifiersSets_changed(self, tabIndex):
        self.lwModifiers.clear()
        self.lwModifiers.addItems( self.modifiersSets_list[tabIndex] )


    def getModifiers(self):

        txt = ''
        for modifiersSet in self.modifiersSets_list:
            if modifiersSet:
                txt += ','.join(modifiersSet) + '|'
        txt = txt[:-1]

        return txt
