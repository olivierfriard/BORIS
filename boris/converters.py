"""
BORIS
Behavioral Observation Research Interactive Software
Copyright 2012-2024 Olivier Friard

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

import sys
import json
import urllib.error
import urllib.parse
import urllib.request


from PyQt5.QtWidgets import QMessageBox, QTableWidgetItem, QFileDialog, QInputDialog, QLineEdit

from . import dialog
from . import config as cfg


def pb_code_help_clicked(self):
    """
    help for writing converters
    """
    msg = QMessageBox()
    msg.setIcon(QMessageBox.Information)
    msg.setWindowTitle("Help for writing converters")

    msg.setText(
        (
            "A converter is a function that will convert a time value from external data into seconds.<br>"
            "A time value like 00:23:59 must be converted into seconds before to be plotted synchronously with your media.<br>"
            "For this you can use BORIS native converters or write your own converter.<br>"
            'A converter must be written using the <a href="www.python.org">Python3</a> language.<br>'
        )
    )

    # msg.setInformativeText("This is additional information")

    msg.setStandardButtons(QMessageBox.Ok)
    msg.exec_()


def add_converter(self):
    """
    Add a new converter
    """

    for w in [
        self.le_converter_name,
        self.le_converter_description,
        self.pteCode,
        self.pb_save_converter,
        self.pb_cancel_converter,
    ]:
        w.setEnabled(True)
    # disable buttons
    for w in [
        self.pb_add_converter,
        self.pb_modify_converter,
        self.pb_delete_converter,
        self.pb_load_from_file,
        self.pb_load_from_repo,
        self.tw_converters,
    ]:
        w.setEnabled(False)


def modify_converter(self):
    """
    Modifiy the selected converter
    """

    if not self.tw_converters.selectedIndexes():
        QMessageBox.warning(self, cfg.programName, "Select a converter in the table")
        return

    for w in [
        self.le_converter_name,
        self.le_converter_description,
        self.pteCode,
        self.pb_save_converter,
        self.pb_cancel_converter,
    ]:
        w.setEnabled(True)

    # disable buttons
    for w in [
        self.pb_add_converter,
        self.pb_modify_converter,
        self.pb_delete_converter,
        self.pb_load_from_file,
        self.pb_load_from_repo,
        self.tw_converters,
    ]:
        w.setEnabled(False)

    self.le_converter_name.setText(self.tw_converters.item(self.tw_converters.selectedIndexes()[0].row(), 0).text())
    self.le_converter_description.setText(self.tw_converters.item(self.tw_converters.selectedIndexes()[0].row(), 1).text())
    self.pteCode.setPlainText(self.tw_converters.item(self.tw_converters.selectedIndexes()[0].row(), 2).text().replace("@", "\n"))

    self.row_in_modification = self.tw_converters.selectedIndexes()[0].row()


def code_2_func(self, name: str, code: str):
    """
    convert code to function

    Args:
        name (str): function name
        code (str): Python code

    Returns:
        str: string containing Python function
    """

    function = f"def {name}(INPUT):\n"
    function += """    INPUT = INPUT.decode("utf-8") if isinstance(INPUT, bytes) else INPUT\n"""
    function += "\n".join(["    " + row for row in code.split("\n")])
    function += "\n    return OUTPUT"

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
    code: str = self.pteCode.toPlainText()
    if not code:
        QMessageBox.critical(self, "BORIS", "The converter must have Python code")
        return

    function = code_2_func(self, name=self.le_converter_name.text(), code=code)

    try:
        exec(function)
    except Exception:
        QMessageBox.critical(self, "BORIS", f"The code produces an error:<br><b>{sys.exc_info()[1]}</b>")
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

    # enable buttons
    for w in [
        self.pb_add_converter,
        self.pb_modify_converter,
        self.pb_delete_converter,
        self.pb_load_from_file,
        self.pb_load_from_repo,
        self.tw_converters,
    ]:
        w.setEnabled(True)


def cancel_converter(self):
    """Cancel converter"""

    for w in [self.le_converter_name, self.le_converter_description, self.pteCode]:
        w.setEnabled(False)
        w.clear()
    self.pb_save_converter.setEnabled(False)
    self.pb_cancel_converter.setEnabled(False)

    # enable buttons
    for w in [
        self.pb_add_converter,
        self.pb_modify_converter,
        self.pb_delete_converter,
        self.pb_load_from_file,
        self.pb_load_from_repo,
        self.tw_converters,
    ]:
        w.setEnabled(True)


def delete_converter(self):
    """
    Delete selected converter
    """

    if self.tw_converters.selectedIndexes():
        if dialog.MessageDialog("BORIS", "Confirm converter deletion", [cfg.CANCEL, cfg.OK]) == cfg.OK:
            self.tw_converters.removeRow(self.tw_converters.selectedIndexes()[0].row())
    else:
        QMessageBox.warning(self, cfg.programName, "Select a converter in the table")


def load_converters_from_file_repo(self, mode: str):
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
                except Exception:
                    QMessageBox.critical(self, cfg.programName, "This file does not contain converters...")
                    return

    if mode == "repo":
        converters_repo_URL = "https://www.boris.unito.it/static/converters.json"
        try:
            converters_from_repo = urllib.request.urlopen(converters_repo_URL).read().strip().decode("utf-8")
        except Exception:
            QMessageBox.critical(self, cfg.programName, "An error occured during retrieving converters from BORIS remote repository")
            return

        try:
            converters_from_file = eval(converters_from_repo)["BORIS converters"]
        except Exception:
            QMessageBox.critical(self, cfg.programName, "An error occured during retrieving converters from BORIS remote repository")
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
                            text, ok = QInputDialog.getText(
                                self,
                                "Converter conflict",
                                "The converter already exists<br>Rename it:",
                                QLineEdit.Normal,
                                converter,
                            )
                            if not ok:
                                break
                            if text in converter_names:
                                QMessageBox.critical(self, cfg.programName, "This name already exists in converters")

                            if not text.replace("_", "a").isalnum():
                                QMessageBox.critical(
                                    self,
                                    cfg.programName,
                                    "This name contains forbidden character(s).<br>Use a..z, A..Z, 0..9 _",
                                )

                            if text != converter and text not in converter_names and text.replace("_", "a").isalnum():
                                break

                        if ok:
                            converter_name = text
                        else:
                            continue
                    # test if code does not produce error
                    function = code_2_func(self, name=converter_name, code=converters_from_file[converter]["code"])

                    try:
                        exec(function)
                    except Exception:
                        QMessageBox.critical(
                            self,
                            "BORIS",
                            (f"The code of {converter_name} converter produces an error: " f"<br><b>{sys.exc_info()[1]}</b>"),
                        )

                    self.tw_converters.setRowCount(self.tw_converters.rowCount() + 1)
                    self.tw_converters.setItem(self.tw_converters.rowCount() - 1, 0, QTableWidgetItem(converter_name))
                    self.tw_converters.setItem(
                        self.tw_converters.rowCount() - 1,
                        1,
                        QTableWidgetItem(converters_from_file[converter]["description"]),
                    )
                    self.tw_converters.setItem(
                        self.tw_converters.rowCount() - 1,
                        2,
                        QTableWidgetItem(converters_from_file[converter]["code"].replace("\n", "@")),
                    )

                    self.flag_modified = True

            [self.tw_converters.resizeColumnToContents(idx) for idx in [0, 1]]
