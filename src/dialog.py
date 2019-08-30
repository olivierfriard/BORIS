#!/usr/bin/env python3

"""
BORIS
Behavioral Observation Research Interactive Software
Copyright 2012-2019 Olivier Friard

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

from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *

import config
import utilities
import duration_widget
import version

'''
class multi_values_dialog(QDialog):
    """
    dialog for user input. Elements can be checkbox, lineedit, spinbox

    """

    def __init__(self, label_caption, elements_list):
        super().__init__()

        hbox = QVBoxLayout()
        self.label = QLabel()
        self.label.setText(label_caption)
        hbox.addWidget(self.label)

        self.elements = {}
        for element in elements_list:
            if element[0] == "cb":
                self.elements[element[1]] = QCheckBox(element[1])
                self.elements[element[1]].setChecked(element[2])
                hbox.addWidget(self.elements[element[1]])
            if element[0] == "le":
                lb = QLabel(element[1])
                hbox.addWidget(lb)
                self.elements[element[1]] = QLineEdit()
                hbox.addWidget(self.elements[element[1]])
            if element[0] == "sb":
                lb = QLabel(element[1])
                hbox.addWidget(lb)
                self.elements[element[1]] = QSpinBox()
                self.elements[element[1]].setRange(element[2], element[3])
                self.elements[element[1]].setSingleStep(element[4])
                self.elements[element[1]].setValue(element[5])
                hbox.addWidget(self.elements[element[1]])

        hbox2 = QHBoxLayout()

        self.pbCancel = QPushButton("Cancel")
        self.pbCancel.clicked.connect(self.reject)
        hbox2.addWidget(self.pbCancel)

        self.pbOK = QPushButton("OK")
        self.pbOK.clicked.connect(self.accept)
        self.pbOK.setDefault(True)
        hbox2.addWidget(self.pbOK)

        hbox.addLayout(hbox2)

        self.setLayout(hbox)

        self.setWindowTitle("title")
'''


def MessageDialog(title, text, buttons):
    response = ""
    message = QMessageBox()
    message.setWindowTitle(title)
    message.setText(text)
    message.setIcon(QMessageBox.Question)
    for button in buttons:
        message.addButton(button, QMessageBox.YesRole)

    message.setWindowFlags(Qt.WindowStaysOnTopHint)
    message.exec_()
    return message.clickedButton().text()


def error_message(task: str, exc_info: tuple) -> None:
    """
    show details about the error

    """
    error_type, error_file_name, error_lineno = utilities.error_info(exc_info)
    QMessageBox.critical(None, config.programName,
                         (f"An error occured during {task}.<br>"
                          f"BORIS version: {version.__version__}<br>"
                          f"Error: {error_type}<br>"
                          f"in {error_file_name} "
                          f"at line # {error_lineno}<br><br>"
                          "Please report this problem to improve the software at:<br>"
                          '<a href="https://github.com/olivierfriard/BORIS/issues">https://github.com/olivierfriard/BORIS/issues</a>'
                          ))


class Info_widget(QWidget):

    def __init__(self, parent=None):
        super(Info_widget, self).__init__(parent)

        self.setWindowTitle("BORIS")
        layout = QVBoxLayout()
        self.label = QLabel()
        layout.addWidget(self.label)
        self.lwi = QListWidget()
        layout.addWidget(self.lwi)
        self.setLayout(layout)


class Video_overlay_dialog(QDialog):
    """
    dialog to ask image file and position for video overlay
    """

    def __init__(self):
        super().__init__()

        vlayout = QVBoxLayout()
        vlayout.addWidget(QLabel("File"))
        hbox = QHBoxLayout()
        self.le_file_path = QLineEdit()
        hbox.addWidget(self.le_file_path)
        self.pb_browse = QPushButton("Browse", self, clicked=self.browse)
        hbox.addWidget(self.pb_browse)
        vlayout.addLayout(hbox)

        vlayout.addWidget(QLabel("Position: x,y"))
        self.le_overlay_position = QLineEdit()
        vlayout.addWidget(self.le_overlay_position)

        vlayout.addWidget(QLabel("Transparency"))
        self.sb_overlay_transparency = QSpinBox()
        self.sb_overlay_transparency.setRange(0, 255)
        self.sb_overlay_transparency.setSingleStep(1)
        self.sb_overlay_transparency.setValue(128)
        vlayout.addWidget(self.sb_overlay_transparency)

        self.cb_player = QComboBox()
        vlayout.addWidget(self.cb_player)

        hbox = QHBoxLayout()
        self.pb_cancel = QPushButton("Cancel", self, clicked=self.reject)
        hbox.addWidget(self.pb_cancel)
        self.pb_oK = QPushButton("OK", clicked=self.ok)
        '''self.pb_oK.clicked.connect(self.ok)'''
        self.pb_oK.setDefault(True)
        hbox.addWidget(self.pb_oK)

        vlayout.addLayout(hbox)

        self.setLayout(vlayout)

    def browse(self):
        fn = QFileDialog().getOpenFileName(self, "Choose an image file", "", "PNG files (*.png);;All files (*)")
        file_name = fn[0] if type(fn) is tuple else fn
        if file_name:
            self.le_file_path.setText(file_name)

    def ok(self):
        if not self.le_file_path.text():
            QMessageBox.warning(None, config.programName, "Select a file containing a PNG image",
                                QMessageBox.Ok | QMessageBox.Default, QMessageBox.NoButton)
            return

        if self.le_overlay_position.text() and "," not in self.le_overlay_position.text():
            QMessageBox.warning(None, config.programName, "The overlay position must be in x,y format",
                                QMessageBox.Ok | QMessageBox.Default, QMessageBox.NoButton)
            return
        if self.le_overlay_position.text():
            try:
                [int(x.strip()) for x in self.le_overlay_position.text().split(",")]
            except Exception:
                QMessageBox.warning(None, config.programName, "The overlay position must be in x,y format",
                                    QMessageBox.Ok | QMessageBox.Default, QMessageBox.NoButton)
                return
        self.accept()


class Input_dialog(QDialog):
    """
    dialog for user input. Elements can be checkbox, lineedit

    """

    def __init__(self, label_caption, elements_list):
        super().__init__()

        hbox = QVBoxLayout()
        self.label = QLabel()
        self.label.setText(label_caption)
        hbox.addWidget(self.label)

        self.elements = {}
        for element in elements_list:
            if element[0] == "cb":
                self.elements[element[1]] = QCheckBox(element[1])
                self.elements[element[1]].setChecked(element[2])
                hbox.addWidget(self.elements[element[1]])
            if element[0] == "le":
                lb = QLabel(element[1])
                hbox.addWidget(lb)
                self.elements[element[1]] = QLineEdit()
                hbox.addWidget(self.elements[element[1]])
            if element[0] == "sb":
                lb = QLabel(element[1])
                hbox.addWidget(lb)
                self.elements[element[1]] = QSpinBox()
                self.elements[element[1]].setRange(element[2], element[3])
                self.elements[element[1]].setSingleStep(element[4])
                self.elements[element[1]].setValue(element[5])
                hbox.addWidget(self.elements[element[1]])

        hbox2 = QHBoxLayout()

        self.pbCancel = QPushButton("Cancel")
        self.pbCancel.clicked.connect(self.reject)
        hbox2.addWidget(self.pbCancel)

        self.pbOK = QPushButton("OK")
        self.pbOK.clicked.connect(self.accept)
        self.pbOK.setDefault(True)
        hbox2.addWidget(self.pbOK)

        hbox.addLayout(hbox2)

        self.setLayout(hbox)

        self.setWindowTitle("title")



class DuplicateBehaviorCode(QDialog):
    """
    let user show between behaviors that are coded by same key
    """

    def __init__(self, text, codes_list):

        super(DuplicateBehaviorCode, self).__init__()

        self.setWindowTitle(config.programName)
        self.setWindowFlags(Qt.WindowStaysOnTopHint)

        Vlayout = QVBoxLayout()
        widget = QWidget(self)
        widget.setLayout(Vlayout)

        label = QLabel()
        label.setText(text)
        Vlayout.addWidget(label)

        self.lw = QListWidget(widget)
        self.lw.setObjectName("lw_modifiers")
        # TODO: to be enabled
        # lw.installEventFilter(self)

        '''
        if QT_VERSION_STR[0] == "4":
            lw.setItemSelected(item, True)
        else:
            item.setSelected(True)
        '''

        for code in codes_list:
            item = QListWidgetItem(code)
            self.lw.addItem(item)

        Vlayout.addWidget(self.lw)

        pbCancel = QPushButton("Cancel")
        pbCancel.clicked.connect(self.reject)
        Vlayout.addWidget(pbCancel)
        pbOK = QPushButton("OK")
        pbOK.setDefault(True)
        pbOK.clicked.connect(self.pbOK_clicked)
        Vlayout.addWidget(pbOK)

        self.setLayout(Vlayout)

        # self.installEventFilter(self)

        self.setMaximumSize(1024, 960)

    def getCode(self):
        """
        get selected behavior code
        """
        if self.lw.selectedItems():
            return self.lw.selectedItems()[0].text()

    def pbOK_clicked(self):
        self.accept()


class ChooseObservationsToImport(QDialog):
    """
    dialog for selectiong items
    """

    def __init__(self, text, observations_list):

        super(ChooseObservationsToImport, self).__init__()

        self.setWindowTitle(config.programName)
        self.setWindowFlags(Qt.WindowStaysOnTopHint)

        Vlayout = QVBoxLayout()
        widget = QWidget(self)
        widget.setLayout(Vlayout)

        label = QLabel()
        label.setText(text)
        Vlayout.addWidget(label)

        self.lw = QListWidget(widget)
        self.lw.setObjectName("lw_observations")
        self.lw.setSelectionMode(QAbstractItemView.ExtendedSelection)
        # TODO: to be enabled
        # lw.installEventFilter(self)

        '''
        if QT_VERSION_STR[0] == "4":
            lw.setItemSelected(item, True)
        else:
            item.setSelected(True)
        '''

        for code in observations_list:
            item = QListWidgetItem(code)
            self.lw.addItem(item)

        Vlayout.addWidget(self.lw)

        pbCancel = QPushButton("Cancel")
        pbCancel.clicked.connect(self.reject)
        Vlayout.addWidget(pbCancel)
        pbOK = QPushButton("OK")
        pbOK.setDefault(True)
        pbOK.clicked.connect(self.accept)
        Vlayout.addWidget(pbOK)

        self.setLayout(Vlayout)

        # self.installEventFilter(self)

        self.setMaximumSize(1024, 960)

    def get_selected_observations(self):
        """
        get selected_observations
        """
        return [item.text() for item in self.lw.selectedItems()]


class Ask_time(QDialog):
    """
    "Ask time" dialog box using duration widget in duration_widget module
    """

    def __init__(self, time_format):
        super().__init__()
        hbox = QVBoxLayout(self)
        self.label = QLabel()
        self.label.setText("Go to time")
        hbox.addWidget(self.label)

        self.time_widget = duration_widget.Duration_widget()
        if time_format == config.HHMMSS:
            self.time_widget.set_format_hhmmss()
        if time_format == config.S:
            self.time_widget.set_format_s()

        hbox.addWidget(self.time_widget)

        self.pbOK = QPushButton("OK")
        self.pbOK.clicked.connect(self.accept)
        self.pbOK.setDefault(True)

        self.pbCancel = QPushButton("Cancel")
        self.pbCancel.clicked.connect(self.reject)

        self.hbox2 = QHBoxLayout(self)
        self.hbox2.addItem(QSpacerItem(241, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))
        self.hbox2.addWidget(self.pbCancel)
        self.hbox2.addWidget(self.pbOK)
        hbox.addLayout(self.hbox2)
        self.setLayout(hbox)
        self.setWindowTitle("Time")



class EditSelectedEvents(QDialog):
    """
    "edit selected events" dialog box
    """

    def __init__(self):
        super().__init__()

        self.setWindowTitle("Edit selected events")

        hbox = QVBoxLayout(self)

        self.rbSubject = QRadioButton("Subject")
        self.rbSubject.setChecked(False)
        self.rbSubject.toggled.connect(self.rb_changed)
        hbox.addWidget(self.rbSubject)

        self.rbBehavior = QRadioButton("Behavior")
        self.rbBehavior.setChecked(False)
        self.rbBehavior.toggled.connect(self.rb_changed)
        hbox.addWidget(self.rbBehavior)

        self.lb = QLabel("New value")
        hbox.addWidget(self.lb)
        self.newText = QListWidget(self)
        hbox.addWidget(self.newText)

        self.rbComment = QRadioButton("Comment")
        self.rbComment.setChecked(False)
        self.rbComment.toggled.connect(self.rb_changed)
        hbox.addWidget(self.rbComment)

        self.lbComment = QLabel("New comment")
        hbox.addWidget(self.lbComment)

        self.commentText = QLineEdit()
        hbox.addWidget(self.commentText)

        hbox2 = QHBoxLayout(self)
        self.pbOK = QPushButton("OK")
        self.pbOK.clicked.connect(self.pbOK_clicked)
        self.pbCancel = QPushButton("Cancel")
        self.pbCancel.clicked.connect(self.pbCancel_clicked)
        hbox2.addWidget(self.pbCancel)
        hbox2.addWidget(self.pbOK)
        hbox.addLayout(hbox2)

        self.setLayout(hbox)


    def rb_changed(self):

        self.newText.setEnabled(not self.rbComment.isChecked())
        self.commentText.setEnabled(self.rbComment.isChecked())

        if self.rbSubject.isChecked():
            self.newText.clear()
            self.newText.addItems(self.all_subjects)

        if self.rbBehavior.isChecked():
            self.newText.clear()
            self.newText.addItems(self.all_behaviors)

        if self.rbComment.isChecked():
            self.newText.clear()


    def pbOK_clicked(self):
        if not self.rbSubject.isChecked() and not self.rbBehavior.isChecked() and not self.rbComment.isChecked():
            QMessageBox.warning(None, config.programName, "You must select a field to be edited",
                                QMessageBox.Ok | QMessageBox.Default, QMessageBox.NoButton)
            return

        if (self.rbSubject.isChecked() or self.rbBehavior.isChecked()) and self.newText.selectedItems() == []:
            QMessageBox.warning(None, config.programName, "You must select a new value from the list",
                                QMessageBox.Ok | QMessageBox.Default, QMessageBox.NoButton)
            return

        self.accept()

    def pbCancel_clicked(self):
        self.reject()


class FindInEvents(QWidget):
    """
    "find in events" dialog box
    """

    clickSignal = pyqtSignal(str)

    currentIdx = -1

    def __init__(self):
        super().__init__()

        self.setWindowTitle("Find in events")

        hbox = QVBoxLayout()

        self.cbSubject = QCheckBox("Subject")
        self.cbSubject.setChecked(True)
        hbox.addWidget(self.cbSubject)

        self.cbBehavior = QCheckBox("Behavior")
        self.cbBehavior.setChecked(True)
        hbox.addWidget(self.cbBehavior)

        self.cbModifier = QCheckBox("Modifiers")
        self.cbModifier.setChecked(True)
        hbox.addWidget(self.cbModifier)

        self.cbComment = QCheckBox("Comment")
        self.cbComment.setChecked(True)
        hbox.addWidget(self.cbComment)

        self.lbFind = QLabel("Find")
        hbox.addWidget(self.lbFind)

        self.findText = QLineEdit()
        hbox.addWidget(self.findText)

        self.cbFindInSelectedEvents = QCheckBox("Find in selected events")
        self.cbFindInSelectedEvents.setChecked(False)
        hbox.addWidget(self.cbFindInSelectedEvents)

        self.cb_case_sensitive = QCheckBox("Case sensitive")
        self.cb_case_sensitive.setChecked(False)
        hbox.addWidget(self.cb_case_sensitive)

        self.lb_message = QLabel()
        hbox.addWidget(self.lb_message)

        hbox2 = QHBoxLayout()
        self.pbOK = QPushButton("Find")
        self.pbOK.clicked.connect(lambda: self.click("FIND"))
        self.pbCancel = QPushButton("Close")
        self.pbCancel.clicked.connect(lambda: self.click("CLOSE"))
        hbox2.addWidget(self.pbCancel)
        hbox2.addWidget(self.pbOK)
        hbox.addLayout(hbox2)

        self.setLayout(hbox)

    def click(self, msg):
        self.clickSignal.emit(msg)


class FindReplaceEvents(QWidget):
    """
    "find replace events" dialog box
    """

    clickSignal = pyqtSignal(str)
    '''sendEventSignal = pyqtSignal(QEvent)'''

    def __init__(self):
        super().__init__()

        self.setWindowTitle("Find/Replace events")

        hbox = QVBoxLayout()

        self.cbSubject = QCheckBox("Subject")
        self.cbSubject.setChecked(False)
        hbox.addWidget(self.cbSubject)


        self.cbBehavior = QCheckBox("Behavior")
        self.cbBehavior.setChecked(False)
        hbox.addWidget(self.cbBehavior)

        self.cbModifier = QCheckBox("Modifiers")
        self.cbModifier.setChecked(False)
        hbox.addWidget(self.cbModifier)

        self.cbComment = QCheckBox("Comment")
        self.cbComment.setChecked(False)
        hbox.addWidget(self.cbComment)

        self.lbFind = QLabel("Find")
        hbox.addWidget(self.lbFind)

        self.findText = QLineEdit()
        hbox.addWidget(self.findText)

        self.lbReplace = QLabel("Replace")
        hbox.addWidget(self.lbReplace)

        self.replaceText = QLineEdit()
        hbox.addWidget(self.replaceText)

        self.cbFindInSelectedEvents = QCheckBox("Find/Replace in selected events")
        self.cbFindInSelectedEvents.setChecked(False)
        hbox.addWidget(self.cbFindInSelectedEvents)

        self.cb_case_sensitive = QCheckBox("Case sensitive")
        self.cb_case_sensitive.setChecked(False)
        hbox.addWidget(self.cb_case_sensitive)

        hbox2 = QHBoxLayout()

        self.pbCancel = QPushButton("Cancel")
        self.pbCancel.clicked.connect(lambda: self.click("CANCEL"))
        hbox2.addWidget(self.pbCancel)

        self.pbOK = QPushButton("Find and replace")
        self.pbOK.clicked.connect(lambda: self.click("FIND_REPLACE"))
        hbox2.addWidget(self.pbOK)

        self.pbFindReplaceAll = QPushButton("Find and replace all")
        self.pbFindReplaceAll.clicked.connect(lambda: self.click("FIND_REPLACE_ALL"))
        hbox2.addWidget(self.pbFindReplaceAll)

        hbox.addLayout(hbox2)
        self.setLayout(hbox)

    def click(self, msg):
        self.clickSignal.emit(msg)


class exlore_project_dialog(QDialog):
    """
    "explore project" dialog box
    """

    def __init__(self):
        super().__init__()

        self.setWindowTitle("Explore project")

        hbox = QVBoxLayout()

        self.lb_subject = QLabel("Subject")
        hbox.addWidget(self.lb_subject)
        self.find_subject = QLineEdit()
        hbox.addWidget(self.find_subject)

        self.lb_behav = QLabel("Behaviors")
        hbox.addWidget(self.lb_behav)
        self.find_behavior = QLineEdit()
        hbox.addWidget(self.find_behavior)

        self.lb_modifier = QLabel("Modifier")
        hbox.addWidget(self.lb_modifier)
        self.find_modifier = QLineEdit()
        hbox.addWidget(self.find_modifier)

        self.lb_comment = QLabel("Comment")
        hbox.addWidget(self.lb_comment)
        self.find_comment = QLineEdit()
        hbox.addWidget(self.find_comment)

        self.cb_case_sensitive = QCheckBox("Case sensitive")
        self.cb_case_sensitive.setChecked(False)
        hbox.addWidget(self.cb_case_sensitive)

        self.lb_message = QLabel()
        hbox.addWidget(self.lb_message)

        hbox2 = QHBoxLayout()
        self.pbOK = QPushButton("Find")
        self.pbOK.clicked.connect(self.accept)
        self.pbCancel = QPushButton("Cancel")
        self.pbCancel.clicked.connect(self.reject)
        hbox2.addWidget(self.pbCancel)
        hbox2.addWidget(self.pbOK)
        hbox.addLayout(hbox2)

        self.setLayout(hbox)


class Results_dialog(QDialog):
    """
    widget for visualizing text output
    """
    def __init__(self):
        super().__init__()

        self.setWindowTitle("")

        hbox = QVBoxLayout()

        self.lb = QLabel("")
        hbox.addWidget(self.lb)

        self.ptText = QPlainTextEdit()
        hbox.addWidget(self.ptText)

        hbox2 = QHBoxLayout()
        self.pbSave = QPushButton("Save text")
        self.pbSave.clicked.connect(self.save_results)
        hbox2.addWidget(self.pbSave)

        hbox2.addItem(QSpacerItem(241, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))

        self.pbCancel = QPushButton("Cancel")
        self.pbCancel.clicked.connect(self.reject)
        hbox2.addWidget(self.pbCancel)
        self.pbCancel.setVisible(False)

        self.pbOK = QPushButton("OK")
        self.pbOK.clicked.connect(self.accept)
        hbox2.addWidget(self.pbOK)

        hbox.addLayout(hbox2)

        self.setLayout(hbox)

        self.resize(540, 640)


    def save_results(self):
        """
        save content of self.ptText
        """

        fn = QFileDialog().getSaveFileName(self, "Save results", "", "Text files (*.txt *.tsv);;All files (*)")
        file_name = fn[0] if type(fn) is tuple else fn

        if file_name:
            try:
                with open(file_name, "w") as f:
                    f.write(self.ptText.toPlainText())
            except Exception:
                QMessageBox.critical(self, programName, f"The file {file_name} can not be saved")


class ResultsWidget(QWidget):
    """
    widget for visualizing text output
    """
    def __init__(self):
        super().__init__()

        self.setWindowTitle("")

        hbox = QVBoxLayout()

        self.lb = QLabel("")
        hbox.addWidget(self.lb)

        self.ptText = QPlainTextEdit()
        hbox.addWidget(self.ptText)

        hbox2 = QHBoxLayout()
        hbox2.addItem(QSpacerItem(241, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))

        self.pbSave = QPushButton("Save results")
        self.pbSave.clicked.connect(self.save_results)
        hbox2.addWidget(self.pbSave)

        self.pbOK = QPushButton("OK")
        self.pbOK.clicked.connect(self.close)
        hbox2.addWidget(self.pbOK)

        hbox.addLayout(hbox2)

        self.setLayout(hbox)

        self.resize(540, 640)


    def save_results(self):
        """
        save content of self.ptText
        """

        fn = QFileDialog().getSaveFileName(self, "Save results", "", "Text files (*.txt *.tsv);;All files (*)")
        file_name = fn[0] if type(fn) is tuple else fn

        if file_name:
            try:
                with open(file_name, "w") as f:
                    f.write(self.ptText.toPlainText())
            except Exception:
                QMessageBox.critical(self, programName, f"The file {file_name} can not be saved")


class View_data_head(QDialog):
    """
    widget for visualizing first rows of data file
    """

    def __init__(self):
        super().__init__()

        self.setWindowTitle("")

        vbox = QVBoxLayout()

        self.lb = QLabel("")
        vbox.addWidget(self.lb)

        self.tw = QTableWidget()
        vbox.addWidget(self.tw)

        self.label = QLabel("Enter the column indices to plot (time, value) separated by comma (,)")
        vbox.addWidget(self.label)

        self.le = QLineEdit()
        vbox.addWidget(self.le)

        hbox2 = QHBoxLayout()

        self.pbCancel = QPushButton("Cancel")
        self.pbCancel.clicked.connect(self.reject)
        hbox2.addWidget(self.pbCancel)

        self.pbOK = QPushButton("OK")
        self.pbOK.clicked.connect(self.accept)
        hbox2.addWidget(self.pbOK)

        vbox.addLayout(hbox2)

        self.setLayout(vbox)

        self.resize(540, 640)


class View_explore_project_results(QWidget):
    """
    widget for visualizing results of explore project
    """

    double_click_signal = pyqtSignal(str, int)

    def __init__(self):
        super().__init__()

        self.setWindowTitle("")

        vbox = QVBoxLayout()

        self.lb = QLabel("")
        vbox.addWidget(self.lb)

        self.tw = QTableWidget()
        self.tw.setSelectionBehavior(QTableView.SelectRows)
        self.tw.cellDoubleClicked[int, int].connect(self.tw_cellDoubleClicked)
        vbox.addWidget(self.tw)

        hbox2 = QHBoxLayout()

        self.pbOK = QPushButton("OK")
        self.pbOK.clicked.connect(self.close)
        hbox2.addWidget(self.pbOK)

        vbox.addLayout(hbox2)

        self.setLayout(vbox)

        # self.resize(540, 640)


    def tw_cellDoubleClicked(self, r, c):

        self.double_click_signal.emit(self.tw.item(r, 0).text(), int(self.tw.item(r, 1).text()))
