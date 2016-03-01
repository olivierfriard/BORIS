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

import logging
from PyQt4.QtCore import *
from PyQt4.QtGui import *
import os
import tablib

from config import *

class timeBudgetResults(QWidget):
    """
    class for displaying time budget results in new window
    a function for exporting data in TSV format is implemented
    """

    def __init__(self, log_level, pj):
        super(timeBudgetResults, self).__init__()

        logging.basicConfig(level=log_level)
        self.pj = pj
        self.label = QLabel()
        self.label.setText('')
        self.lw = QListWidget()
        self.lw.setEnabled(False)
        self.lw.setMaximumHeight(100)
        self.lbTotalObservedTime = QLabel()
        self.lbTotalObservedTime.setText("")
        self.twTB = QTableWidget()

        hbox = QVBoxLayout(self)

        hbox.addWidget(self.label)
        hbox.addWidget(self.lw)
        hbox.addWidget(self.lbTotalObservedTime)
        hbox.addWidget(self.twTB)

        hbox2 = QHBoxLayout(self)


        self.pbSave = QPushButton("Save results")
        hbox2.addWidget(self.pbSave)

        spacerItem = QSpacerItem(241, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)
        hbox2.addItem(spacerItem)

        self.pbClose = QPushButton("Close")
        hbox2.addWidget(self.pbClose)

        hbox.addLayout(hbox2)

        self.setWindowTitle("Time budget")


        self.pbClose.clicked.connect(self.close)
        self.pbSave.clicked.connect(self.pbSave_clicked)


    def pbSave_clicked(self):
        """
        save time budget analysis results in TSV, CSV, ODS, XLS format
        """

        def complete(l, max):
            """
            complete list with empty string until len = max
            """
            while len(l) < max:
                l.append("")
            return l

        logging.debug("save time budget results to file")

        fileName, filter_ = QFileDialog(self).getSaveFileNameAndFilter(self, "Save Time budget analysis", "","Tab Separated Values (*.txt *.tsv);;Comma Separated Values (*.txt *.csv);;Microsoft Excel XLS (*.xls);;Open Document Spreadsheet ODS (*.ods);;All files (*)")

        if fileName:

            rows = []

            # observations list
            rows.append( ['Observations:'] )
            for idx in range(self.lw.count()):
                rows.append( [ self.lw.item(idx).text() ] )

            # check if only one observation was selected
            if self.lw.count() == 1:
                rows.append( [''] )

                # write independant variables to file
                if INDEPENDENT_VARIABLES in self.pj[ OBSERVATIONS ][  self.lw.item(0).text() ]:
                    rows.append( ['Independent variables:'] )
                    for var in self.pj[ OBSERVATIONS ][self.lw.item(0).text()][INDEPENDENT_VARIABLES]:
                        rows.append([var, self.pj[ OBSERVATIONS ][self.lw.item(0).text() ][ INDEPENDENT_VARIABLES ][ var ] ] )

            rows.append( [''] )
            rows.append( [''] )
            rows.append( ['Time budget:'] )

            # write header
            cols = []
            for col in range(self.twTB.columnCount() ):
                cols.append( self.twTB.horizontalHeaderItem(col).text() )

            rows.append( cols )
            rows.append([""])

            for row in range( self.twTB.rowCount()):
                values = []
                for col in range(self.twTB.columnCount()):
                    values.append( self.twTB.item(row,col).text() )
                rows.append( values )


            maxLen = max( [len(r) for r in rows] )
            data = tablib.Dataset()
            data.title = "Time budget"

            for row in rows:
                data.append( complete( row, maxLen ) )

            if 'tsv' in filter_ and not fileName.upper().endswith( '.TSV' ):
                fileName += '.tsv'
            if 'csv' in filter_ and not fileName.upper().endswith( '.CSV' ):
                fileName += '.csv'
            if 'ods' in filter_ and not fileName.upper().endswith( '.ODS' ):
                fileName += '.ods'
            if 'xls' in filter_ and not fileName.upper().endswith( '.XLS' ):
                fileName += '.xls'

            if fileName.upper().endswith('.TSV'):
                with open(fileName,'w') as f:
                    f.write(data.tsv)
                return

            if fileName.upper().endswith('.CSV'):
                with open(fileName,'w') as f:
                    f.write(data.csv)
                return

            if fileName.upper().endswith('.ODS'):
                with open(fileName,'wb') as f:
                    f.write(data.ods)
                return

            if fileName.upper().endswith('.XLS'):
                with open(fileName,'wb') as f:
                    f.write(data.xls)
                return

            QMessageBox.warning(self, programName, 'You must choose a format: TSV, CSV, ODS or XLS')
