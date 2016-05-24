#!/usr/bin/env python3

"""
BORIS
Behavioral Observation Research Interactive Software
Copyright 2012-2016 Olivier Friard

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

try:
    from PyQt5.QtGui import *
    from PyQt5.QtCore import *
    from PyQt5.QtWidgets import *
except:
    from PyQt4.QtGui import *
    from PyQt4.QtCore import *

from config import *

if QT_VERSION_STR[0] == "4":
    from edit_event_ui import Ui_Form
else:
    from edit_event_ui5 import Ui_Form

class DlgEditEvent(QDialog, Ui_Form):

    def __init__(self, log_level, parent=None):

        super(DlgEditEvent, self).__init__(parent)
        logging.basicConfig(level=log_level)
        self.setupUi(self)

        self.pbOK.clicked.connect(self.accept)
        self.pbCancel.clicked.connect(self.reject)

