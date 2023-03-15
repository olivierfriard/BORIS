"""
BORIS
Behavioral Observation Research Interactive Software
Copyright 2012-2023 Olivier Friard

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
import sys
import pathlib as pl
import traceback
import platform
import datetime as dt
from decimal import Decimal as dec

from PyQt5.QtCore import Qt, pyqtSignal, QT_VERSION_STR, PYQT_VERSION_STR
from PyQt5.QtWidgets import (
    QApplication,
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSizePolicy,
    QSpacerItem,
    QSpinBox,
    QDoubleSpinBox,
    QTableView,
    QTableWidget,
    QVBoxLayout,
    QWidget,
)
from PyQt5.QtGui import QFont

from . import config as cfg
from . import duration_widget
from . import version


def MessageDialog(title: str, text: str, buttons: tuple) -> str:

    message = QMessageBox()
    message.setWindowTitle(title)
    message.setText(text)
    message.setIcon(QMessageBox.Question)
    for button in buttons:
        message.addButton(button, QMessageBox.YesRole)

    # message.setWindowFlags(Qt.WindowStaysOnTopHint)
    message.exec_()
    return message.clickedButton().text()


'''
def error_message_box(task, error_type, error_file_name, error_lineno):
    # do NOT use this function directly, use error_message function
    """
    show a critical dialog

    """
    QMessageBox.critical(None, cfg.programName, (f"BORIS version: {version.__version__}<br>"
                                                 f"An error occured during the execution of <b>{task}</b>.<br>"
                                                 f"Error: {error_type}<br>"
                                                 f"in {error_file_name} "
                                                 f"at line # {error_lineno}<br><br>"
                                                 "to improve the software please report this problem at:<br>"
                                                 '<a href="https://github.com/olivierfriard/BORIS/issues">'
                                                 'https://github.com/olivierfriard/BORIS/issues</a><br>'
                                                 "or by email (See the About page on the BORIS web site.<br><br>"
                                                 "Thank you for your collaboration!"))
'''


def error_message_box(error_traceback):
    # do NOT use this function directly, use error_message function
    """
    show a critical dialog

    """
    QMessageBox.critical(
        None,
        cfg.programName,
        (
            f"BORIS version: {version.__version__}<br><br>"
            f"<b>An error has occured</b>:<br>"
            f"{error_traceback}<br><br>"
            "to improve the software please report this problem at:<br>"
            '<a href="https://github.com/olivierfriard/BORIS/issues">'
            "https://github.com/olivierfriard/BORIS/issues</a><br>"
            "or by email (See the About page on the BORIS web site.<br><br>"
            "Thank you for your collaboration!"
        ),
    )


def error_message() -> None:
    """
    Show details about the error in a message box
    write entry to log as CRITICAL
    """

    error_traceback = traceback.format_exc().replace("Traceback (most recent call last):", "").replace("\n", " ")

    logging.critical(error_traceback)
    error_message_box(error_traceback)


def global_error_message(exception_type, exception_value, traceback_object):
    """
    global error management
    save error using loggin.critical and append error message to ~/boris.log
    """

    error_text: str = (
        f"BORIS version: {version.__version__}\n"
        f"OS: {platform.uname().system} {platform.uname().release} {platform.uname().version}\n"
        f"CPU: {platform.uname().machine} {platform.uname().processor}\n"
        f"Python {platform.python_version()} ({'64-bit' if sys.maxsize > 2**32 else '32-bit'})\n"
        f"Qt {QT_VERSION_STR} - PyQt {PYQT_VERSION_STR}\n"
        f"{dt.datetime.now():%Y-%m-%d %H:%M}\n\n"
    )
    error_text += "".join(traceback.format_exception(exception_type, exception_value, traceback_object))

    logging.critical(error_text)

    # append to boris.log file
    try:
        with open(pl.Path.home() / "boris.log", "a") as f_out:
            f_out.write(error_text + "\n")
            f_out.write("-" * 80 + "\n")
    except Exception:
        print(f"Cannot write to {pl.Path.home() / 'boris.log'} file")
        logging.critical(f"Cannot write to {pl.Path.home() / 'boris.log'} file")

    # copy to clipboard
    cb = QApplication.clipboard()
    cb.clear(mode=cb.Clipboard)
    cb.setText(error_text, mode=cb.Clipboard)

    error_text: str = error_text.replace("\r\n", "\n").replace("\n", "<br>")

    text: str = (
        f"<b>An error has occured</b>:<br><br>"
        f"{error_text}<br>"
        "to improve the software please report this problem at:<br>"
        '<a href="https://github.com/olivierfriard/BORIS/issues">'
        "https://github.com/olivierfriard/BORIS/issues</a><br>"
        "Please no screenshot, the error message was copied to the clipboard.<br><br>"
        "Thank you for your collaboration!"
    )

    errorbox = QMessageBox()
    errorbox.setWindowTitle("BORIS error occured")
    errorbox.setText(text)
    errorbox.setTextFormat(Qt.RichText)
    errorbox.setStandardButtons(QMessageBox.Abort)

    _ = errorbox.addButton("Ignore and try to continue", QMessageBox.RejectRole)

    ret = errorbox.exec_()

    if ret == QMessageBox.Abort:
        sys.exit(1)


class Info_widget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

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
        self.cb_player = QComboBox()
        vlayout.addWidget(self.cb_player)

        hbox = QHBoxLayout()
        hbox.addWidget(QLabel("Image file"))
        self.le_file_path = QLineEdit()
        hbox.addWidget(self.le_file_path)
        vlayout.addLayout(hbox)

        hbox = QHBoxLayout()
        self.pb_browse = QPushButton("Browse", self, clicked=self.browse)
        hbox.addItem(QSpacerItem(241, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))
        hbox.addWidget(self.pb_browse)
        vlayout.addLayout(hbox)

        hbox = QHBoxLayout()
        hbox.addWidget(QLabel("Position: x,y"))
        self.le_overlay_position = QLineEdit()
        hbox.addWidget(self.le_overlay_position)
        vlayout.addLayout(hbox)

        hbox = QHBoxLayout()
        hbox.addWidget(QLabel("Transparency %"))
        self.sb_overlay_transparency = QSpinBox()
        self.sb_overlay_transparency.setRange(0, 100)
        self.sb_overlay_transparency.setSingleStep(1)
        self.sb_overlay_transparency.setValue(90)
        hbox.addWidget(self.sb_overlay_transparency)
        vlayout.addLayout(hbox)

        # self.sb_overlay_transparency.setEnabled(False)

        hbox = QHBoxLayout()
        self.pb_cancel = QPushButton("Cancel", self, clicked=self.reject)
        hbox.addWidget(self.pb_cancel)
        self.pb_OK = QPushButton("OK", clicked=self.ok)

        self.pb_OK.setDefault(True)
        hbox.addWidget(self.pb_OK)

        vlayout.addLayout(hbox)

        self.setLayout(vlayout)

    def browse(self):
        fn = QFileDialog().getOpenFileName(self, "Choose an image file", "", "PNG files (*.png);;All files (*)")
        file_name = fn[0] if type(fn) is tuple else fn
        if file_name:
            self.le_file_path.setText(file_name)

    def ok(self):
        if not self.le_file_path.text():
            QMessageBox.warning(
                None,
                cfg.programName,
                "Select a file containing a PNG image",
                QMessageBox.Ok | QMessageBox.Default,
                QMessageBox.NoButton,
            )
            return

        if self.le_overlay_position.text() and "," not in self.le_overlay_position.text():
            QMessageBox.warning(
                None,
                cfg.programName,
                "The overlay position must be in x,y format",
                QMessageBox.Ok | QMessageBox.Default,
                QMessageBox.NoButton,
            )
            return
        if self.le_overlay_position.text():
            try:
                [int(x.strip()) for x in self.le_overlay_position.text().split(",")]
            except Exception:
                QMessageBox.warning(
                    None,
                    cfg.programName,
                    "The overlay position must be in x,y format",
                    QMessageBox.Ok | QMessageBox.Default,
                    QMessageBox.NoButton,
                )
                return
        self.accept()


class Input_dialog(QDialog):
    """
    dialog for user input. Elements can be:
        checkbox (cb): Tuple(str, str, bool)
        lineedit (le): Tuple(str, str)
        spinbox (sp)
        items list (il)

    """

    def __init__(self, label_caption: str, elements_list: list, title: str = ""):
        super().__init__()

        self.setWindowTitle(title)

        hbox = QVBoxLayout()
        self.label = QLabel()
        self.label.setText(label_caption)
        hbox.addWidget(self.label)

        self.elements: dict = {}
        for element in elements_list:

            if element[0] == "cb":  # checkbox
                self.elements[element[1]] = QCheckBox(element[1])
                self.elements[element[1]].setChecked(element[2])
                hbox.addWidget(self.elements[element[1]])

            if element[0] == "le":  # line edit
                lb = QLabel(element[1])
                hbox.addWidget(lb)
                self.elements[element[1]] = QLineEdit()
                hbox.addWidget(self.elements[element[1]])

            if element[0] == "sb":  # spinbox
                # 1 - Label
                # 2 - minimum value
                # 3 - maximum value
                # 4 - step
                # 5 - initial value

                lb = QLabel(element[1])
                hbox.addWidget(lb)
                self.elements[element[1]] = QSpinBox()
                self.elements[element[1]].setRange(element[2], element[3])
                self.elements[element[1]].setSingleStep(element[4])
                self.elements[element[1]].setValue(element[5])
                hbox.addWidget(self.elements[element[1]])

            if element[0] == "dsb":  # doubleSpinbox
                # 1 - Label
                # 2 - minimum value
                # 3 - maximum value
                # 4 - step
                # 5 - initial value
                # 6 - number of decimas

                lb = QLabel(element[1])
                hbox.addWidget(lb)
                self.elements[element[1]] = QDoubleSpinBox()
                self.elements[element[1]].setRange(element[2], element[3])
                self.elements[element[1]].setSingleStep(element[4])
                self.elements[element[1]].setValue(element[5])
                self.elements[element[1]].setDecimals(element[6])
                hbox.addWidget(self.elements[element[1]])

            if element[0] == "il":  # items list
                # 1 - Label
                # 2 - Values (tuple of tuple: 0 - value; 1 - "", "selected")
                lb = QLabel(element[1])
                hbox.addWidget(lb)
                self.elements[element[1]] = QComboBox()
                self.elements[element[1]].addItems([x[0] for x in element[2]])  # take first element of tuple
                try:
                    self.elements[element[1]].setCurrentIndex(
                        [idx for idx, x in enumerate(element[2]) if x[1] == "selected"][0]
                    )
                except:
                    self.elements[element[1]].setCurrentIndex(0)
                hbox.addWidget(self.elements[element[1]])

        hbox2 = QHBoxLayout()

        self.pbCancel = QPushButton(cfg.CANCEL)
        self.pbCancel.clicked.connect(self.reject)
        hbox2.addWidget(self.pbCancel)

        self.pbOK = QPushButton(cfg.OK, clicked=self.accept)
        self.pbOK.setDefault(True)
        hbox2.addWidget(self.pbOK)

        hbox.addLayout(hbox2)

        self.setLayout(hbox)


class DuplicateBehaviorCode(QDialog):
    """
    let user show between behaviors that are coded by same key
    """

    def __init__(self, text, codes_list):

        super(DuplicateBehaviorCode, self).__init__()

        self.setWindowTitle(cfg.programName)
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

        self.setWindowTitle(cfg.programName)

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

        for code in observations_list:
            item = QListWidgetItem(code)
            self.lw.addItem(item)

        Vlayout.addWidget(self.lw)

        hlayout = QHBoxLayout()
        hlayout.addItem(QSpacerItem(241, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))
        pbCancel = QPushButton("Cancel", clicked=self.reject)
        hlayout.addWidget(pbCancel)
        pbOK = QPushButton("OK", clicked=self.accept)
        pbOK.setDefault(True)
        hlayout.addWidget(pbOK)

        Vlayout.addLayout(hlayout)

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
        if time_format == cfg.HHMMSS:
            self.time_widget.set_format_hhmmss()
        if time_format == cfg.S:
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
    """
    sendEventSignal = pyqtSignal(QEvent)
    """

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

        self.pbCancel = QPushButton(cfg.CANCEL, clicked=lambda: self.click("CANCEL"))
        hbox2.addWidget(self.pbCancel)

        self.pbOK = QPushButton("Find and replace", clicked=lambda: self.click("FIND_REPLACE"))
        hbox2.addWidget(self.pbOK)

        self.pbFindReplaceAll = QPushButton("Find and replace all", clicked=lambda: self.click("FIND_REPLACE_ALL"))
        hbox2.addWidget(self.pbFindReplaceAll)

        hbox.addLayout(hbox2)
        self.setLayout(hbox)

    def click(self, msg):
        self.clickSignal.emit(msg)


'''
class explore_project_dialog(QDialog):
    """
    "explore project" dialog box
    """

    def __init__(self):
        super().__init__()

        self.setWindowTitle("Explore project")

        hbox = QVBoxLayout()

        hbox.addWidget(QLabel("Search in all observations"))

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
'''


class Results_dialog(QDialog):
    """
    widget for visualizing text output
    """

    def __init__(self):
        super().__init__()

        self.dataset = False

        self.setWindowTitle("")

        hbox = QVBoxLayout()

        self.lb = QLabel("")
        hbox.addWidget(self.lb)

        self.ptText = QPlainTextEdit()
        self.ptText.setReadOnly(True)
        hbox.addWidget(self.ptText)

        hbox2 = QHBoxLayout()
        self.pbSave = QPushButton("Save results", clicked=self.save_results)
        hbox2.addWidget(self.pbSave)

        hbox2.addItem(QSpacerItem(241, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))

        self.pbCancel = QPushButton(cfg.CANCEL, clicked=self.reject)
        hbox2.addWidget(self.pbCancel)
        self.pbCancel.setVisible(False)

        self.pbOK = QPushButton(cfg.OK)
        self.pbOK.clicked.connect(self.accept)
        hbox2.addWidget(self.pbOK)

        hbox.addLayout(hbox2)
        self.setLayout(hbox)

        self.resize(800, 640)

    def save_results(self):
        """
        save content of self.ptText
        """

        if not self.dataset:
            fn = QFileDialog().getSaveFileName(self, "Save results", "", "Text files (*.txt *.tsv);;All files (*)")
            file_name = fn[0] if type(fn) is tuple else fn

            if not file_name:
                return
            try:
                with open(file_name, "w") as f:
                    f.write(self.ptText.toPlainText())
            except Exception:
                QMessageBox.critical(self, cfg.programName, f"The file {file_name} can not be saved")

        else:
            self.done(cfg.SAVE_DATASET)


class View_data(QDialog):
    """
    widget for visualizing rows of data file
    """

    def __init__(self):
        super().__init__()

        self.setWindowTitle("")

        vbox = QVBoxLayout()

        self.lb = QLabel("")
        vbox.addWidget(self.lb)

        self.tw = QTableWidget()
        self.tw.verticalHeader().hide()
        vbox.addWidget(self.tw)

        self.stats = QPlainTextEdit()
        font = QFont()
        font.setFamily("Monospace")
        self.stats.setFont(font)

        vbox.addWidget(self.stats)

        self.label = QLabel("Enter the column indices to plot (time, value) separated by comma (,)")
        vbox.addWidget(self.label)

        self.le = QLineEdit()
        vbox.addWidget(self.le)

        hbox2 = QHBoxLayout()

        hbox2.addItem(QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))

        self.pbCancel = QPushButton("Cancel", clicked=self.reject)
        hbox2.addWidget(self.pbCancel)

        self.pbOK = QPushButton("OK", clicked=self.accept)
        hbox2.addWidget(self.pbOK)

        vbox.addLayout(hbox2)

        self.setLayout(vbox)

        self.resize(800, 640)


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
        hbox2.addWidget(QPushButton("OK", clicked=self.close))

        vbox.addLayout(hbox2)

        self.setLayout(vbox)

        # self.resize(540, 640)

    def tw_cellDoubleClicked(self, r, c):

        self.double_click_signal.emit(self.tw.item(r, 0).text(), int(self.tw.item(r, 1).text()))
