#!/usr/bin/env python

"""
BORIS
Behavioral Observation Research Interactive Software
Copyright 2012-2014 Olivier Friard


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

from PySide.QtCore import *
from PySide.QtGui import *

from observations_list_ui import Ui_observationsList

class ObservationsList(QDialog, Ui_observationsList):

    def __init__(self, parent=None):
        
        super(ObservationsList, self).__init__(parent)
        self.setupUi(self)


        self.twObservations.itemDoubleClicked.connect(self.twObservations_doubleClicked)

        self.pbOK.clicked.connect(self.pbOK_clicked)
        self.pbOpen.clicked.connect(self.pbOpen_clicked)
        self.pbEdit.clicked.connect(self.pbEdit_clicked)
        self.pbCancel.clicked.connect(self.pbCancel_clicked)
        self.pbSelectAll.clicked.connect(self.pbSelectAll_clicked)
        self.pbUnSelectAll.clicked.connect(self.pbUnSelectAll_clicked)

    def pbUnSelectAll_clicked(self):
        self.twObservations.clearSelection()

    def pbSelectAll_clicked(self):
        self.twObservations.selectAll()

    def pbOK_clicked(self):
        self.accept()


    def twObservations_doubleClicked(self):
        if self.twObservations.selectedIndexes():
            self.accept()

    def pbOpen_clicked(self):
        
        self.accept()

    def pbEdit_clicked(self):
        
        self.accept()

    def pbCancel_clicked(self):
        self.reject()

