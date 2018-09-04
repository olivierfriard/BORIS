#!/usr/bin/env python3

"""
BORIS
Behavioral Observation Research Interactive Software
Copyright 2012-2018 Olivier Friard

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


'''import logging'''

try:
    from PyQt5.QtGui import *
    from PyQt5.QtCore import *
    from PyQt5.QtWidgets import *
    from edit_event_ui5 import Ui_Form
except:
    from PyQt4.QtGui import *
    from PyQt4.QtCore import *
    from edit_event_ui import Ui_Form

from config import HHMMSS, S, HHMMSSZZZ
from utilities import seconds2time

class DlgEditEvent(QDialog, Ui_Form):

    def __init__(self, log_level, current_time, time_format, show_set_current_time=False, parent=None):

        super().__init__(parent)
        '''logging.basicConfig(level=log_level)'''
        self.setupUi(self)

        self.pb_set_to_current_time.setVisible(show_set_current_time)
        self.current_time = current_time
        
        self.dsbTime.setVisible(time_format==S)
        self.teTime.setVisible(time_format==HHMMSS)

        self.pb_set_to_current_time.clicked.connect(self.set_to_current_time)
        self.pbOK.clicked.connect(self.accept)
        self.pbCancel.clicked.connect(self.reject)

    def set_to_current_time(self):
        """
        set time to current media time
        """
        self.teTime.setTime(QTime.fromString(seconds2time(self.current_time), HHMMSSZZZ))
        self.dsbTime.setValue(float(self.current_time))

