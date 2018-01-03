#!/usr/bin/env python3

"""
BORIS
Behavioral Observation Research Interactive Software
Copyright 2012-2018 Olivier Friard

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
import dialog
from config import *

if QT_VERSION_STR[0] == "4":
    from converters_ui import Ui_converters
else:
    from converters_ui5 import Ui_converters


class Converters(QDialog, Ui_converters):

    def __init__(self, converters, parent=None):

        super(Converters, self).__init__(parent)
        self.setupUi(self)

        self.converters = converters

        self.pb_add_converter.clicked.connect(self.add_converter)
        self.pb_modify_converter.clicked.connect(self.modify_converter)
        self.pb_save_converter.clicked.connect(self.save_converter)
        self.pb_cancel_converter.clicked.connect(self.cancel_converter)
        self.pb_delete_converter.clicked.connect(self.delete_converter)

        self.pbOK.clicked.connect(self.pb_ok_clicked)
        self.pb_cancel_widget.clicked.connect(self.pb_cancel_widget_clicked)
        
        self.row_in_modification = -1
        self.flag_modified = False

        for w in [self.leName, self.leDescription, self.pteCode, self.pb_save_converter, self.pb_cancel_converter]:
            w.setEnabled(False)
            
        self.load_converters()


    def add_converter(self):
        """Add a new converter"""

        for w in [self.leName, self.leDescription, self.pteCode, self.pb_save_converter, self.pb_cancel_converter]:
            w.setEnabled(True)
        self.tw_converters.setEnabled(False)


    def modify_converter(self):
        """Modifiy the selected converter"""

        if not self.tw_converters.selectedIndexes():
            QMessageBox.warning(self, programName, "Select a converter in the table")
            return

        for w in [self.leName, self.leDescription, self.pteCode, self.pb_save_converter, self.pb_cancel_converter]:
            w.setEnabled(True)
        self.tw_converters.setEnabled(False)

        self.leName.setText(self.tw_converters.item(self.tw_converters.selectedIndexes()[0].row(), 0).text())
        self.leDescription.setText(self.tw_converters.item(self.tw_converters.selectedIndexes()[0].row(), 1).text())
        self.pteCode.setPlainText(self.tw_converters.item(self.tw_converters.selectedIndexes()[0].row(), 2).text().replace("@", "\n"))
        
        self.row_in_modification = self.tw_converters.selectedIndexes()[0].row()


    def save_converter(self):
        """Save converter"""

        # test code with evel
        code = self.pteCode.toPlainText()
        try:
            eval(code)
        except:
            print(sys.exc_info()[1])
            QMessageBox.critical(self, "BORIS", "The code produced an error:<br><b>{}</b>".format(sys.exc_info()[1]))
            return
            

        if self.row_in_modification == -1:
            self.tw_converters.setRowCount(self.tw_converters.rowCount() + 1)
            row = self.tw_converters.rowCount() - 1
        else:
            row = self.row_in_modification

        self.tw_converters.setItem(row, 0, QTableWidgetItem(self.leName.text()))
        self.tw_converters.setItem(row, 1, QTableWidgetItem(self.leDescription.text()))
        self.tw_converters.setItem(row, 2, QTableWidgetItem(self.pteCode.toPlainText().replace("\n", "@")))

        self.row_in_modification = -1

        for w in [self.leName, self.leDescription, self.pteCode]:
            w.setEnabled(False)
            w.clear()
        self.pb_save_converter.setEnabled(False)
        self.pb_cancel_converter.setEnabled(False)
        self.tw_converters.setEnabled(True)
        
        self.flag_modified = True


    def cancel_converter(self):
        """Cancel converter"""

        for w in [self.leName, self.leDescription, self.pteCode]:
            w.setEnabled(False)
            w.clear()
        self.pb_save_converter.setEnabled(False)
        self.pb_cancel_converter.setEnabled(False)
        self.tw_converters.setEnabled(True)


    def delete_converter(self):
        """Delete selected converter"""

        if self.tw_converters.selectedIndexes():
            if dialog.MessageDialog("BORIS", "Confirm converter deletion", [CANCEL, OK]) == OK:
                self.tw_converters.removeRow(self.tw_converters.selectedIndexes()[0].row())
        else:
            QMessageBox.warning(self, programName, "Select a converter in the table")


    def load_converters(self):
        """
        load converters in table
        """
        self.tw_converters.setRowCount(0)
        for converter in self.converters:
            self.tw_converters.setRowCount(self.tw_converters.rowCount() + 1)
            self.tw_converters.setItem(self.tw_converters.rowCount() - 1, 0,
                 QTableWidgetItem(converter["name"]))
            self.tw_converters.setItem(self.tw_converters.rowCount() - 1, 1,
                 QTableWidgetItem(converter["description"]))
            self.tw_converters.setItem(self.tw_converters.rowCount() - 1, 2,
                 QTableWidgetItem(converter["code"].replace("\n", "@")))

        self.tw_converters.resizeColumnToContents(0)
        self.tw_converters.resizeColumnToContents(1)


    def pb_ok_clicked(self):
        """populate converters and close widget"""
        
        converters = []
        for row in range(self.tw_converters.rowCount()):
            
            conv = {}
            conv["name"] = self.tw_converters.item(row, 0).text()
            conv["description"] = self.tw_converters.item(row, 1).text()
            conv["code"] = self.tw_converters.item(row, 2).text().replace("@", "\n")
            converters.append(conv)
        
        self.converters = converters
        self.accept()


    def pb_cancel_widget_clicked(self):
        if self.flag_modified:
            if dialog.MessageDialog("BORIS", "The converters were modified. Are sure to quit?", [CANCEL, OK]) == OK:
                self.reject()
        else:
            self.reject()


if __name__ == '__main__':

    CONVERTERS = [
{
"name": "convert_time_ecg",
"description": "convert '%d/%m/%Y %H:%M:%S.%f' in seconds from epoch",
"code":
"""
import datetime
epoch = datetime.datetime.utcfromtimestamp(0)
datetime_format = "%d/%m/%Y %H:%M:%S.%f"

OUTPUT = (datetime.datetime.strptime(INPUT, datetime_format) - epoch).total_seconds()
"""
},
{
"name": "hhmmss_2_seconds",
"description": "convert HH:MM:SS in seconds",

"code":

"""
h, m, s = INPUT.split(':')
OUTPUT = int(h) * 3600 + int(m) * 60 + int(s)

"""
}
]


    import sys
    app = QApplication(sys.argv)

    class_ = Converters(CONVERTERS)
    class_.show()
    
    r = class_.exec_()
    print(r)
    if r:
        print(class_.converters)

    sys.exit()
