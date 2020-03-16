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


import json
import os
import urllib.error
import urllib.parse
import urllib.request

from PyQt5.QtCore import *
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *

import dialog
from config import *
from converters_ui import Ui_converters


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

        self.pb_load_from_file.clicked.connect(lambda: self.load_converters_from_file_repo("file"))
        self.pb_load_from_repo.clicked.connect(lambda: self.load_converters_from_file_repo("repo"))

        self.pbOK.clicked.connect(self.pb_ok_clicked)
        self.pb_cancel_widget.clicked.connect(self.pb_cancel_widget_clicked)

        self.pb_code_help.clicked.connect(self.pb_code_help_clicked)

        self.row_in_modification = -1
        self.flag_modified = False

        for w in [self.le_converter_name, self.le_converter_description, self.pteCode, self.pb_save_converter, self.pb_cancel_converter]:
            w.setEnabled(False)

        self.load_converters_in_table()


    def pb_code_help_clicked(self):
        """
        help for writing converters
        """
        msg = QMessageBox()
        msg.setIcon(QMessageBox.Information)
        msg.setWindowTitle("Help for writing converters")

        msg.setText(("A converter is a function that will convert a time value from external data into seconds.<br>"
                     "A time value like 00:23:59 must be converted into seconds before to be plotted synchronously with your media.<br>"
                     "For this you can use BORIS native converters or write your own converter.<br>"
                     "A converter must be written using the <a href=\"www.python.org\">Python3</a> language.<br>"

))

        #msg.setInformativeText("This is additional information")

        msg.setStandardButtons(QMessageBox.Ok)
        msg.exec_()

    def add_converter(self):
        """Add a new converter"""

        for w in [self.le_converter_name, self.le_converter_description, self.pteCode, self.pb_save_converter, self.pb_cancel_converter]:
            w.setEnabled(True)
        self.tw_converters.setEnabled(False)


    def modify_converter(self):
        """Modifiy the selected converter"""

        if not self.tw_converters.selectedIndexes():
            QMessageBox.warning(self, programName, "Select a converter in the table")
            return

        for w in [self.le_converter_name, self.le_converter_description, self.pteCode, self.pb_save_converter, self.pb_cancel_converter]:
            w.setEnabled(True)
        self.tw_converters.setEnabled(False)

        self.le_converter_name.setText(self.tw_converters.item(self.tw_converters.selectedIndexes()[0].row(), 0).text())
        self.le_converter_description.setText(self.tw_converters.item(self.tw_converters.selectedIndexes()[0].row(), 1).text())
        self.pteCode.setPlainText(self.tw_converters.item(self.tw_converters.selectedIndexes()[0].row(), 2).text().replace("@", "\n"))

        self.row_in_modification = self.tw_converters.selectedIndexes()[0].row()


    def code_2_func(self, name, code):
        """
        convert code to function

        Args:
            name (str): function name
            code (str): Python code

        Returns:
            str: string containing Python function
        """

        function = """def {}(INPUT):\n""".format(name)
        function += """    INPUT = INPUT.decode("utf-8") if isinstance(INPUT, bytes) else INPUT\n"""
        function += "\n".join(["    " + row for row in code.split("\n")])
        function += """\n    return OUTPUT"""

        return function


    def save_converter(self):
        """Save converter"""

        # check if name
        self.le_converter_name.setText(self.le_converter_name.text().strip())
        if not self.le_converter_name.text():
            QMessageBox.critical(self, "BORIS", "The converter must have a name")
            return

        if not self.le_converter_name.text().replace("_", "a").isalnum():
            QMessageBox.critical(self, "BORIS", "Forbidden characters are used in converter name.<br>Use a..z, A..Z, 0..9 _")
            return

        # test code with exec
        code = self.pteCode.toPlainText()
        if not code:
            QMessageBox.critical(self, "BORIS", "The converter must have Python code")
            return

        function = self.code_2_func(self.le_converter_name.text(), code)

        try:
            exec(function)
        except:
            QMessageBox.critical(self, "BORIS", "The code produces an error:<br><b>{}</b>".format(sys.exc_info()[1]))
            return


        if self.row_in_modification == -1:
            self.tw_converters.setRowCount(self.tw_converters.rowCount() + 1)
            row = self.tw_converters.rowCount() - 1
        else:
            row = self.row_in_modification

        self.tw_converters.setItem(row, 0, QTableWidgetItem(self.le_converter_name.text()))
        self.tw_converters.setItem(row, 1, QTableWidgetItem(self.le_converter_description.text()))
        self.tw_converters.setItem(row, 2, QTableWidgetItem(self.pteCode.toPlainText().replace("\n", "@")))

        self.row_in_modification = -1

        for w in [self.le_converter_name, self.le_converter_description, self.pteCode]:
            w.setEnabled(False)
            w.clear()
        self.pb_save_converter.setEnabled(False)
        self.pb_cancel_converter.setEnabled(False)
        self.tw_converters.setEnabled(True)

        self.flag_modified = True


    def cancel_converter(self):
        """Cancel converter"""

        for w in [self.le_converter_name, self.le_converter_description, self.pteCode]:
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


    def load_converters_in_table(self):
        """
        load converters in table
        """
        self.tw_converters.setRowCount(0)

        for converter in sorted(self.converters.keys()):
            self.tw_converters.setRowCount(self.tw_converters.rowCount() + 1)
            self.tw_converters.setItem(self.tw_converters.rowCount() - 1, 0,
                 QTableWidgetItem(converter)) # id / name
            self.tw_converters.setItem(self.tw_converters.rowCount() - 1, 1,
                 QTableWidgetItem(self.converters[converter]["description"]))
            self.tw_converters.setItem(self.tw_converters.rowCount() - 1, 2,
             QTableWidgetItem(self.converters[converter]["code"].replace("\n", "@")))

        [self.tw_converters.resizeColumnToContents(idx) for idx in [0,1]]


    def load_converters_from_file_repo(self, mode):
        """
        Load converters from file (JSON) or BORIS remote repository

        Args:
            mode (str): string "repo" or "file"
        """

        converters_from_file = {}
        if mode == "file":
            fn = QFileDialog(self).getOpenFileName(self, "Load converters from file", "", "All files (*)")
            file_name = fn[0] if type(fn) is tuple else fn

            if file_name:
                with open(file_name, "r") as f_in:
                    try:
                        converters_from_file = json.loads(f_in.read())["BORIS converters"]
                    except:
                        QMessageBox.critical(self, programName, "This file does not contain converters...")
                        return

        if mode == "repo":

            converters_repo_URL = "http://www.boris.unito.it/static/converters.json"
            try:
                converters_from_repo = urllib.request.urlopen(converters_repo_URL).read().strip().decode("utf-8")
            except:
                QMessageBox.critical(self, programName, "An error occured during retrieving converters from BORIS remote repository")
                return

            try:
                converters_from_file = eval(converters_from_repo)["BORIS converters"]
            except:
                QMessageBox.critical(self, programName, "An error occured during retrieving converters from BORIS remote repository")
                return


        if converters_from_file:

            diag_choose_conv = dialog.ChooseObservationsToImport("Choose the converters to load:", sorted(list(converters_from_file.keys())))

            if diag_choose_conv.exec_():

                selected_converters = diag_choose_conv.get_selected_observations()
                if selected_converters:

                    # extract converter names from table
                    converter_names = []
                    for row in range(self.tw_converters.rowCount()):
                        converter_names.append(self.tw_converters.item(row, 0).text())

                    for converter in selected_converters:
                        converter_name = converter

                        if converter in converter_names:
                            while True:
                                text, ok = QInputDialog.getText(self, "Converter conflict",
                                                                      "The converter already exists<br>Rename it:",
                                                                      QLineEdit.Normal,
                                                                      converter)
                                if not ok:
                                    break
                                if text in converter_names:
                                    QMessageBox.critical(self, programName, "This name already exists in converters")

                                if not text.replace("_", "a").isalnum():
                                    QMessageBox.critical(self, programName, "This name contains forbidden character(s).<br>Use a..z, A..Z, 0..9 _")

                                if text != converter and text not in converter_names and text.replace("_", "a").isalnum():
                                    break

                            if ok:
                                converter_name = text
                            else:
                                continue
                        # test if code does not produce error
                        function = self.code_2_func(converter_name, converters_from_file[converter]["code"])

                        try:
                            exec(function)
                        except:
                            QMessageBox.critical(self, "BORIS",
                                                 (f"The code of {converter_name} converter "
                                                  f"produces an error:<br><b>{sys.exc_info()[1]}</b>"))

                        self.tw_converters.setRowCount(self.tw_converters.rowCount() + 1)
                        self.tw_converters.setItem(self.tw_converters.rowCount() - 1, 0,
                            QTableWidgetItem(converter_name))
                        self.tw_converters.setItem(self.tw_converters.rowCount() - 1, 1,
                            QTableWidgetItem(converters_from_file[converter]["description"]))
                        self.tw_converters.setItem(self.tw_converters.rowCount() - 1, 2,
                            QTableWidgetItem(converters_from_file[converter]["code"].replace("\n", "@")))

                        self.flag_modified = True

                [self.tw_converters.resizeColumnToContents(idx) for idx in [0,1]]


    def pb_ok_clicked(self):
        """populate converters and close widget"""

        converters = {}
        for row in range(self.tw_converters.rowCount()):
            converters[self.tw_converters.item(row, 0).text()] = {"name": self.tw_converters.item(row, 0).text(),
                                                                  "description": self.tw_converters.item(row, 1).text(),
                                                                  "code": self.tw_converters.item(row, 2).text().replace("@", "\n")
                                                                 }

        self.converters = converters
        self.accept()


    def pb_cancel_widget_clicked(self):
        if self.flag_modified:
            if dialog.MessageDialog("BORIS", "The converters were modified. Are sure to quit?", [CANCEL, OK]) == OK:
                self.reject()
        else:
            self.reject()


if __name__ == '__main__':

    CONVERTERS = {
        "BORIS converters": {
            "convert_time_ecg": {
                "name":
                "convert_time_ecg",
                "description":
                "convert '%d/%m/%Y %H:%M:%S.%f' in seconds from epoch",
                "code":
                """
    import datetime
    epoch = datetime.datetime.utcfromtimestamp(0)
    datetime_format = "%d/%m/%Y %H:%M:%S.%f"

    OUTPUT = (datetime.datetime.strptime(INPUT, datetime_format) - epoch).total_seconds()
    """
            },
            "hhmmss_2_seconds": {
                "name":
                "hhmmss_2_seconds",
                "description":
                "convert HH:MM:SS in seconds",
                "code":
                """
    h, m, s = INPUT.split(':')
    OUTPUT = int(h) * 3600 + int(m) * 60 + int(s)

    """
            }
        }
    }



    import sys

    app = QApplication(sys.argv)

    class_ = Converters(CONVERTERS["BORIS converters"])
    class_.show()

    r = class_.exec_()
    print(r)
    if r:
        print(class_.converters)

    sys.exit()
