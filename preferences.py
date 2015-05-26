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

from PyQt4.QtCore import *
from PyQt4.QtGui import *
import os

from config import *
from preferences_ui import Ui_prefDialog

class Preferences(QDialog, Ui_prefDialog):

    def __init__(self, parent=None):
        
        super(Preferences, self).__init__(parent)
        self.setupUi(self)

        self.cbAllowFrameByFrameMode.stateChanged.connect(self.cbChanged)

        self.pbBrowseFFmpeg.clicked.connect(self.browseFFmpeg)

        self.pbBrowseFFmpegCacheDir.clicked.connect(self.browseFFmpegCacheDir)

        self.pbOK.clicked.connect(self.ok)
        self.pbCancel.clicked.connect(self.reject)

    def cbChanged(self, state):
        self.pbBrowseFFmpeg.setEnabled( state == Qt.Checked )
        self.lbFFmpeg.setEnabled( state == Qt.Checked )
        self.leFFmpegPath.setEnabled( state == Qt.Checked )
        self.pbBrowseFFmpegCacheDir.setEnabled( state == Qt.Checked )
        self.lbFFmpegCacheDir.setEnabled( state == Qt.Checked )
        self.leFFmpegCacheDir.setEnabled( state == Qt.Checked )
        self.lbFFmpegCacheDirMaxSize.setEnabled( state == Qt.Checked )
        self.sbFFmpegCacheDirMaxSize.setEnabled( state == Qt.Checked )


    def browseFFmpeg(self):
        '''
        allow user search for ffmpeg
        '''
        fd = QFileDialog(self)
        fileName = fd.getOpenFileName(self, 'Select FFmpeg program', '', 'All files (*)')
        if fileName:
            self.leFFmpegPath.setText( fileName )
            self.testFFmpeg()

    def browseFFmpegCacheDir(self):
        '''
        allow user select a cache dir for ffmpeg images
        '''
        fd = QFileDialog(self)
        FFmpegCacheDir = fd.getExistingDirectory(self, 'Select a directory', os.path.expanduser('~'), options=fd.ShowDirsOnly)

        if FFmpegCacheDir:
            self.leFFmpegCacheDir.setText( FFmpegCacheDir )




    def testFFmpeg(self):
        '''
        test if FFmepg is running
        '''
        import subprocess
        out, error = subprocess.Popen(self.leFFmpegPath.text() + ' -version' ,stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True ).communicate()

        out = out.decode('utf-8')
        error = error.decode('utf-8')

        if 'avconv' in out:
            QMessageBox.warning(None, programName, 'Please use FFmpeg in place of avconv.\nSee https://www.ffmpeg.org', \
                QMessageBox.Ok | QMessageBox.Default, QMessageBox.NoButton)
            return False
        
        if 'the Libav developers' in error:
            QMessageBox.warning(None, programName, 'Please use FFmpeg from https://www.ffmpeg.org in place of FFmpeg from Libav project.', \
                QMessageBox.Ok | QMessageBox.Default, QMessageBox.NoButton)
            return False

        if not 'ffmpeg version' in out:
            QMessageBox.warning(None, programName, 'It seems that it is not the correct FFmpeg program... See https://www.ffmpeg.org', \
                QMessageBox.Ok | QMessageBox.Default, QMessageBox.NoButton)
            return False
        return True
        


    def ok(self):

        if self.cbAllowFrameByFrameMode.isChecked() and self.leFFmpegPath.text():
            if not self.testFFmpeg():
                return
            
        self.accept()
