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

from config import *

from PySide.QtCore import *
from PySide.QtGui import *

from observation_ui import Ui_Form
import os

class Observation(QDialog, Ui_Form):

    def __init__(self, parent=None):

        super(Observation, self).__init__(parent)
        self.setupUi(self)

        self.pbAddVideo.clicked.connect(self.add_media)
        self.pbRemoveVideo.clicked.connect(self.remove_media)

        self.pbAddVideo_2.clicked.connect(self.add_media_2)
        self.pbRemoveVideo_2.clicked.connect(self.remove_media2)


        self.pbOK.clicked.connect(self.pbOK_clicked)
        self.pbCancel.clicked.connect(self.pbCancel_clicked)


    def pbOK_clicked(self):
        
        def is_numeric(s):
            try:
                float(s)
                return True
            except ValueError:
                return False

        ### check if indep variables are correct type
        for row in range(0, self.twIndepVariables.rowCount()):

            if self.twIndepVariables.item(row, 1).text() == 'numeric':
                if not is_numeric( self.twIndepVariables.item(row, 2).text() ):
                    QMessageBox.critical(self, programName , 'The <b>%s</b> variable must be numeric!' %  self.twIndepVariables.item(row, 0).text())
                    return


        ### check if observation id not empty
        if not self.leObservationId.text():
            QMessageBox.warning(self, programName , 'The <b>observation id</b> is mandatory and must be unique!' )
            return

        ### check if new obs and observation id already present
        if self.mode == 'new':
            if self.leObservationId.text() in self.pj['observations']:
                QMessageBox.critical(self, programName , 'The observation id <b>%s</b> is already used!<br>' %  (self.leObservationId.text())  + self.pj['observations'][self.leObservationId.text()]['description'] + '<br>' + self.pj['observations'][self.leObservationId.text()]['date']  )
                return

        ### check if edit obs and id changed
        if self.mode == 'edit' and self.leObservationId.text() != self.mem_obs_id:
            if self.leObservationId.text() in self.pj['observations']:
                QMessageBox.critical(self, programName , 'The observation id <b>%s</b> is already used!<br>' %  (self.leObservationId.text())  + self.pj['observations'][self.leObservationId.text()]['description'] + '<br>' + self.pj['observations'][self.leObservationId.text()]['date']  )
                return

        ### check if media list #2 popolated and media list #1 empty
        if not self.lwVideo.count():
            QMessageBox.critical(self, programName , 'Add a media file in the first list!' )
            return

        self.accept()


    def pbCancel_clicked(self):
        self.reject()


    def add_media(self):
        fd = QFileDialog(self)

        os.chdir( os.path.expanduser("~")  )

        fileName, filter_ = fd.getOpenFileName(self, 'Add media file', '', 'All files (*)')
        if fileName:
            self.lwVideo.addItems( [fileName] )


    def add_media_2(self):
        fd = QFileDialog(self)
        fileName, filter_ = fd.getOpenFileName(self, 'Add media file', '', 'All files (*)')
        if fileName:
            self.lwVideo_2.addItems( [fileName] )


    def remove_media(self):

        for SelectedItem in self.lwVideo.selectedItems():
            self.lwVideo.takeItem(self.lwVideo.row(SelectedItem))

    def remove_media2(self):

        for SelectedItem in self.lwVideo_2.selectedItems():
            self.lwVideo_2.takeItem(self.lwVideo_2.row(SelectedItem))

