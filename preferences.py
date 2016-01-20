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

from PyQt4.QtCore import *
from PyQt4.QtGui import *
import os

from config import *
from utilities import *
from preferences_ui import Ui_prefDialog

class Preferences(QDialog, Ui_prefDialog):

    def __init__(self, parent=None):

        super(Preferences, self).__init__(parent)
        self.setupUi(self)

        self.pbBrowseFFmpegCacheDir.clicked.connect(self.browseFFmpegCacheDir)

        self.pbOK.clicked.connect(self.ok)
        self.pbCancel.clicked.connect(self.reject)


    def browseFFmpegCacheDir(self):
        """
        allow user select a cache dir for ffmpeg images
        """
        FFmpegCacheDir = QFileDialog().getExistingDirectory(self, "Select a directory", os.path.expanduser("~"), options=QFileDialog().ShowDirsOnly)

        if FFmpegCacheDir:
            self.leFFmpegCacheDir.setText(FFmpegCacheDir)

    def ok(self):
        self.accept()
