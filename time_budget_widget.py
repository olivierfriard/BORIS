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

from PySide.QtCore import *
from PySide.QtGui import *

from config import *

class timeBudgetResults(QWidget):
    '''
    class for displaying time budget results in new window
    a function for exporting data in TSV format is implemented
    '''

    def __init__(self, debug, pj):
        super(timeBudgetResults, self).__init__()

        self.DEBUG = debug
        self.pj = pj
        self.label = QLabel()
        self.label.setText('')
        self.lw = QListWidget()
        self.lw.setEnabled(False)
        self.lw.setMaximumHeight(100)
        self.twTB = QTableWidget()
                
        hbox = QVBoxLayout(self)

        hbox.addWidget(self.label)
        hbox.addWidget(self.lw)
        hbox.addWidget(self.twTB)

        hbox2 = QHBoxLayout(self)


        self.pbSave = QPushButton('Save results')
        hbox2.addWidget(self.pbSave)

        spacerItem = QSpacerItem(241, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)
        hbox2.addItem(spacerItem)


        self.pbClose = QPushButton('Close')
        hbox2.addWidget(self.pbClose)

        hbox.addLayout(hbox2)

        self.setWindowTitle('Time budget')


        self.pbClose.clicked.connect(self.pbClose_clicked)
        self.pbSave.clicked.connect(self.pbSave_clicked)



    def pbClose_clicked(self):
        self.close()

    def pbSave_clicked(self):
        '''
        save time budget analysis results in TSV format
        '''

        if self.DEBUG: print 'save time budget results to file in TSV format'

        fd = QFileDialog(self)
        fileName, filtr = fd.getSaveFileName(self, 'Save results', '','Results file (*.txt *.tsv);;All files (*)')

        if fileName:
            f = open(fileName, 'w')

            ### observations list
            f.write('Observations:\n')
            for idx in xrange(self.lw.count()):
                f.write(self.lw.item(idx).text() + '\n')

            ### check if only one observation was selected
            if self.lw.count() == 1:
                f.write('\n')

                ### write independant variables to file
                if INDEPENDENT_VARIABLES in self.pj[ OBSERVATIONS ][  self.lw.item(0).text() ]:
                    if self.DEBUG: print 'indep var of selected observation ' , self.pj[ OBSERVATIONS ][  self.lw.item(0).text() ][ INDEPENDENT_VARIABLES ]

                    for var in self.pj[ OBSERVATIONS ][  self.lw.item(0).text() ][ INDEPENDENT_VARIABLES ]:
                        f.write( var + '\t' + self.pj[ OBSERVATIONS ][  self.lw.item(0).text() ][ INDEPENDENT_VARIABLES ][ var ] + '\n')

            f.write('\n\nTime budget:\n')
            ### write header
            f.write( 'Subject\tBehavior\tTotal number\tTotal duration\tDuration mean\t% of total time\n' )

            for row in range( self.twTB.rowCount()):
                for col in range(self.twTB.columnCount()):
                    f.write( self.twTB.item(row,col).text().encode('utf8') + '\t' )
                f.write('\n')
            f.close()
