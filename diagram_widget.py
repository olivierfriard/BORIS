"""
BORIS
Behavioral Observation Research Interactive Software
Copyright 2012-2014 Olivier Friard


  This program is free software; you can redistribute it and/or modify
  it under the terms of the GNU General Public License as published by
  the Free Software Foundation; either version 2 of the License, or
  any later version.
  
  This program is distributed in the hope that it will be useful,
  but WITHOUT ANY WARRANTY; without even the implied warranty of
  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
  GNU General Public License for more details.
  
  You should have received a copy of the GNU General Public License
  along with this program; if not, write to the Free Software
  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
  MA 02110-1301, USA.
  

"""


import PySide
from PySide.QtCore import *
from PySide.QtGui import *


class gantResults(QWidget):
    '''
    class for displaying time diagram in new window
    a function for exporting data in SVG format is implemented
    '''

    def __init__(self,  svg_text = ''):

        self.svg_text = svg_text

        super(gantResults, self).__init__()

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

        self.pbClose.clicked.connect(self.pbClose_clicked)
        self.pbSave.clicked.connect(self.pbSave_clicked)


    def pbClose_clicked(self):
        self.close()


    def pbSave_clicked(self):
        
        if DEBUG: print 'save time diagram to a SVG file'
        fd = QFileDialog(self)
        fileName, filtr = fd.getSaveFileName(self, 'Save time diagram', '', 'SVG file (*.svg);;All files (*)')

        if fileName:
            f = open(fileName, 'w')
            f.write(self.svg_text)
            f.close()
