#!/usr/bin/env python3

"""
BORIS
Behavioral Observation Research Interactive Software
Copyright 2012-2020 Olivier Friard

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
import os

from boris.config import BEHAVIORS_PLOT_COLORS, CANCEL
from boris.dialog import MessageDialog
from boris.preferences_ui import Ui_prefDialog
from PyQt5.QtWidgets import QDialog, QFileDialog


class Preferences(QDialog, Ui_prefDialog):

    def __init__(self, parent=None):

        super().__init__()
        self.setupUi(self)

        self.pbBrowseFFmpegCacheDir.clicked.connect(self.browseFFmpegCacheDir)
        self.rb_save_frames_in_mem.toggled.connect(self.rb_frames_mem_disk)
        self.rb_save_frames_on_disk.toggled.connect(self.rb_frames_mem_disk)
        self.cb_reset_frames_memory.clicked.connect(self.reset_frames_memory)

        self.pb_reset_colors.clicked.connect(self.reset_colors)

        self.pb_refresh.clicked.connect(self.refresh_preferences)
        self.pbOK.clicked.connect(self.accept)
        self.pbCancel.clicked.connect(self.reject)

        self.flag_refresh = False
        self.flag_reset_frames_memory = False


    def rb_frames_mem_disk(self):
        """
        change where extracted frames will be saved: disk or memory
        """
        for w in [self.lb_memory_frames, self.sb_frames_memory_size, self.lb_memory_info]:
            w.setEnabled(self.rb_save_frames_in_mem.isChecked())

        for w in [self.lb_storage_dir]:
            w.setEnabled(self.rb_save_frames_on_disk.isChecked())


    def reset_frames_memory(self):
        """
        reset memory used for frames storage.
        Reset is done after closing the Preferences window.
        """
        self.flag_reset_frames_memory = self.cb_reset_frames_memory.isChecked()


    def refresh_preferences(self):
        """
        allow user to delete the config file (.boris)
        """
        if MessageDialog("BORIS",
                         ("Refresh will re-initialize "
                          "all your preferences and close BORIS"),
                         [CANCEL, "Refresh preferences"]) == "Refresh preferences":
            self.flag_refresh = True
            self.accept()


    def browseFFmpegCacheDir(self):
        """
        allow user select a cache dir for ffmpeg images
        """
        FFmpegCacheDir = QFileDialog().getExistingDirectory(self,
                                                            "Select a directory",
                                                            os.path.expanduser("~"),
                                                            options=QFileDialog().ShowDirsOnly)
        if FFmpegCacheDir:
            self.leFFmpegCacheDir.setText(FFmpegCacheDir)


    def reset_colors(self):
        """
        reset behavior colors to default
        """
        self.te_plot_colors.setPlainText("\n".join(BEHAVIORS_PLOT_COLORS))

        logging.debug("reset behaviors colors to default")
