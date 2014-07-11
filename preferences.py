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

from preferences_ui import Ui_prefDialog

class Preferences(QDialog, Ui_prefDialog):

    def __init__(self, parent=None):
        
        super(Preferences, self).__init__(parent)
        self.setupUi(self)

        ### make invisible "Save complete media path in project"
        self.cbSaveMediaFilePath.setVisible(False)

        self.pbOK.clicked.connect(self.accept)
        self.pbCancel.clicked.connect(self.reject)
