#!/usr/bin/env python3

"""
BORIS
Behavioral Observation Research Interactive Software
Copyright 2012-2018 Olivier Friard


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

try:
    from PyQt5.QtGui import *
    from PyQt5.QtWidgets import *
except:
    from PyQt4.QtGui import *

class Info_widget(QWidget):

    def __init__(self, parent = None):
        super(Info_widget, self).__init__(parent)

        self.setWindowTitle("BORIS")
        layout = QVBoxLayout()
        self.label = QLabel()
        layout.addWidget(self.label)
        self.lwi = QListWidget()
        layout.addWidget(self.lwi)
        self.setLayout(layout)
