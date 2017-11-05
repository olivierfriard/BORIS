#!/usr/bin/env python3

"""
BORIS
Behavioral Observation Research Interactive Software
Copyright 2012-2017 Olivier Friard

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

try:
    from PyQt5.QtGui import *
    from PyQt5.QtCore import *
    from PyQt5.QtWidgets import *
except:
    from PyQt4.QtGui import *
    from PyQt4.QtCore import *

import os

from config import *
from utilities import *

if QT_VERSION_STR[0] == "4":
    from preferences_ui import Ui_prefDialog
else:
    from preferences_ui5 import Ui_prefDialog

class Preferences(QDialog, Ui_prefDialog):

    def __init__(self, parent=None):

        super(Preferences, self).__init__(parent)
        self.setupUi(self)

        self.pbBrowseFFmpegCacheDir.clicked.connect(self.browseFFmpegCacheDir)
        self.pb_reset_colors.clicked.connect(self.reset_colors)

        self.pbOK.clicked.connect(self.ok)
        self.pbCancel.clicked.connect(self.reject)


    def browseFFmpegCacheDir(self):
        """
        allow user select a cache dir for ffmpeg images
        """
        FFmpegCacheDir = QFileDialog().getExistingDirectory(self, "Select a directory", os.path.expanduser("~"), options=QFileDialog().ShowDirsOnly)

        if FFmpegCacheDir:
            self.leFFmpegCacheDir.setText(FFmpegCacheDir)

    def reset_colors(self):
        self.te_plot_colors.setPlainText("\n".join(BEHAVIORS_PLOT_COLORS))

    def ok(self):
        self.accept()
