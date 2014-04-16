#!/usr/bin/env python

"""
BORIS
Behavioral Observation Research Interactive Software
Copyright 2012-2013 Olivier Friard


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

from config import *

from PySide.QtCore import *
from PySide.QtGui import *

from edit_event_ui import Ui_Form

import re

class DlgEditEvent(QDialog, Ui_Form):

    def __init__(self, debug, parent=None):

        super(DlgEditEvent, self).__init__(parent)
        self.setupUi(self)

        self.DEBUG = debug

        self.cobCode.currentIndexChanged.connect(self.codeChanged)
        self.pbOK.clicked.connect(self.pbOK_clicked)
        self.pbCancel.clicked.connect(self.pbCancel_clicked)


    def codeChanged(self):

        if self.DEBUG: print 'cobCode current index', self.cobCode.currentText()

        ### selected code
        ### selectedCode = sorted( [ self.pj['behaviors_conf'][x]['code'] for x in self.pj['behaviors_conf']   ])[ self.cobCode.currentIndex() ]
        
        # selectedCode = self.cobCode.currentText()

        modif = [ self.pj['behaviors_conf'][x]['modifiers'] for x in self.pj['behaviors_conf']  if  self.pj['behaviors_conf'][x]['code'] ==  self.cobCode.currentText()]

        if self.DEBUG: print 'modif', modif

        self.cobModifier.clear()

        self.cobModifier.addItems( [''] + modif[0].split(',') )



    def pbOK_clicked(self):

        ### check time format
        '''
        if ':' in self.leTime.text():
            if re.match('^\d+:\d\d:\d\d\.\d$', self.leTime.text().strip()) or re.match('^\d+:\d\d:\d\d$', self.leTime.text().strip()):

                ssplit = self.leTime.text().strip().split(':')
                h, m, s = int(ssplit[0]), int(ssplit[1]), float(ssplit[2])
                print h,m,s

                if m > 59 or s > 59:
                    QMessageBox.warning(self, programName, self.leTime.text() + ' do not respect the hh:mm:ss.s format')
                    return
            
            else:
                QMessageBox.warning(self, programName, self.leTime.text() + ' do not respect hh:mm:ss nor hh:mm:ss.s format')
                return


        elif not self.leTime.text().replace('.', '' , 1).isdigit():
            QMessageBox.warning(self, programName, self.leTime.text() + ' is not a floating value')
            return
        '''


        ### check subject
        '''
        if self.leSubject.text() and self.leSubject.text().upper() not in [ self.pj['subjects_conf'][x]['name'].upper() for x in self.pj['behaviors_conf'] ]:
            QMessageBox.warning(self, programName, 'The subject <b>%s</b> is not in the list of available subjects' % (self.leSubject.text()))
            return
        '''
        '''
        if not self.leCode.text():
            QMessageBox.warning(self, programName, 'The event code is mandatory!')
            return
        '''

        #print [ self.pj['behaviors_conf'][x]['code'] for x in self.pj['behaviors_conf'] ]
        '''
        if not self.leCode.text().upper() in [ self.pj['behaviors_conf'][x]['code'].upper() for x in self.pj['behaviors_conf'] ]:
            QMessageBox.warning(self, programName, 'The <b>%s</b> code is not in the list of codes:<br>' % (self.leCode.text()) + ', '.join([ self.pj['behaviors_conf'][x]['code'] for x in self.pj['behaviors_conf'] ]))
            return
        '''

        self.accept()


    def pbCancel_clicked(self):
        self.reject()

