#!/usr/bin/env python

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


import PySide   ### qwebwidget
from PySide.QtCore import *
from PySide.QtGui import *


class diagram(QWidget):
    '''
    class for displaying time diagram in new window
    a function for exporting data in SVG format is implemented
    '''

    def __init__(self, debug, svg_text = ''):

        self.svg_text = svg_text

        super(diagram, self).__init__()

        self.DEBUG = debug

        self.label = QLabel()
        self.label.setText('')

        ### load image

        self.webview = PySide.QtWebKit.QWebView()

        self.webview.setHtml(svg_text)

        hbox = QVBoxLayout(self)

        hbox.addWidget(self.webview)

        hbox2 = QHBoxLayout(self)

        self.pbSave = QPushButton('Save diagram')
        hbox2.addWidget(self.pbSave)

        spacerItem = QSpacerItem(241, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)
        hbox2.addItem(spacerItem)

        self.pbClose = QPushButton('Close')
        hbox2.addWidget(self.pbClose)

        hbox.addLayout(hbox2)

        self.setWindowTitle('Time diagram')

        self.pbClose.clicked.connect(self.close)
        self.pbSave.clicked.connect(self.pbSave_clicked)


    def pbSave_clicked(self):
        
        if self.DEBUG: print 'save time diagram to a SVG file'
        fd = QFileDialog(self)
        fileName, filtr = fd.getSaveFileName(self, 'Save time diagram', '', 'SVG file (*.svg);;All files (*)')

        if fileName:
            f = open(fileName, 'w')
            f.write(self.svg_text)
            f.close()
