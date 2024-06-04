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

import logging
import sys
import pathlib as pl
import traceback
import platform
import datetime as dt
import subprocess
from decimal import Decimal as dec
from typing import Union

from PyQt5.QtCore import Qt, pyqtSignal, QT_VERSION_STR, PYQT_VERSION_STR, QRect, QTime, QDateTime, QSize
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
    QDateTimeEdit,
    QTimeEdit,
    QAbstractSpinBox,
    QRadioButton,
    QStackedWidget,
    QFrame,
)
from PyQt5.QtGui import QFont, QTextCursor

from . import config as cfg
from . import version
from . import utilities as util


def MessageDialog(title: str, text: str, buttons: tuple) -> str:
    """
    generic message dialog

    Return
        str: text of the clicked button
    """
    message = QMessageBox()
    message.setWindowTitle(title)
    message.setText(text)
    message.setIcon(QMessageBox.Question)
    for button in buttons:
        message.addButton(button, QMessageBox.YesRole)

    # message.setWindowFlags(Qt.WindowStaysOnTopHint)
    message.exec_()
    return message.clickedButton().text()


def global_error_message(exception_type, exception_value, traceback_object):
    """
    Global error management
    save error using loggin.critical and stdout
    """

    error_text: str = (
        f"BORIS version: {version.__version__}\n"
        f"OS: {platform.uname().system} {platform.uname().release} {platform.uname().version}\n"
        f"CPU: {platform.uname().machine} {platform.uname().processor}\n"
        f"Python {platform.python_version()} ({'64-bit' if sys.maxsize > 2**32 else '32-bit'})\n"
        f"Qt {QT_VERSION_STR} - PyQt {PYQT_VERSION_STR}\n"
        f"MPV library version: {util.mpv_lib_version()[0]}\n"
        f"MPV library file path: {util.mpv_lib_version()[1]}\n\n"
        f"Error succeded at {dt.datetime.now():%Y-%m-%d %H:%M}\n\n"
    )
    error_text += "".join(traceback.format_exception(exception_type, exception_value, traceback_object))

    # system info
    systeminfo = ""
    if sys.platform.startswith("win"):
        systeminfo = subprocess.getoutput("systeminfo")
    if sys.platform.startswith("linux"):
        systeminfo = subprocess.getoutput("cat /etc/*rel*; uname -a")

    error_text += f"\n\nSystem info\n===========\n\n{systeminfo}"

    # write to stdout
    logging.critical(error_text)

    # write to $HOME/boris_error.log
    try:
        with open(pl.Path.home() / "boris_error.log", "w") as f_error:
            f_error.write(error_text)
            f_error.write("\nSystem info:\n")
            f_error.write(systeminfo + "\n")
    except Exception:
        logging.critical(f"Impossible to write to {pl.Path.home() / 'boris_error.log'}")

    # copy to clipboard
    cb = QApplication.clipboard()
    cb.clear(mode=cb.Clipboard)
    cb.setText(error_text, mode=cb.Clipboard)

    text: str = (
        f"An error has occured!\n\n"
        "to improve the software please report this problem at:\n"
        "https://github.com/olivierfriard/BORIS/issues\n\n"
        "Please no screenshot, the error message was copied to the clipboard.\n\n"
        "Thank you for your collaboration!\n\n"
        f"{error_text}"
    )

    errorbox = Results_dialog()

    errorbox.setWindowTitle("BORIS - An error occured")
    errorbox.pbOK.setText("Abort")
    errorbox.pbCancel.setVisible(True)
    errorbox.pbCancel.setText("Ignore and try to continue")

    font = QFont()
    font.setFamily("monospace")
    errorbox.ptText.setFont(font)
    errorbox.ptText.clear()
    errorbox.ptText.appendPlainText(text)

    errorbox.ptText.moveCursor(QTextCursor.Start)

    ret = errorbox.exec_()

    if ret == 1:  # Abort
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


class get_time_widget(QWidget):
    """
    widget for selecting a time in various formats: secondes, HH:MM:SS:ZZZ or YYYY-mm-DD HH:MM:SS:ZZZ
    """

    def __init__(self, time_value=dec(0), parent=None):
        super().__init__(parent)

        self.setWindowTitle("BORIS")

        self.widget = QWidget()
        self.widget.setObjectName("widget")
        self.widget.setGeometry(QRect(130, 220, 302, 63))
        self.verticalLayout_3 = QVBoxLayout(self.widget)
        self.verticalLayout_3.setObjectName("verticalLayout_3")
        self.verticalLayout_3.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout_3 = QHBoxLayout()
        self.horizontalLayout_3.setObjectName("horizontalLayout_3")
        self.verticalLayout_2 = QVBoxLayout()
        self.verticalLayout_2.setObjectName("verticalLayout_2")
        self.label = QLabel(self.widget)
        self.label.setObjectName("label")

        self.verticalLayout_2.addWidget(self.label)

        self.pb_sign = QPushButton(self.widget)
        self.pb_sign.setObjectName("pb_sign")
        self.pb_sign.setMaximumSize(QSize(40, 16777215))

        self.verticalLayout_2.addWidget(self.pb_sign)

        self.horizontalLayout_3.addLayout(self.verticalLayout_2)

        self.verticalLayout = QVBoxLayout()
        self.verticalLayout.setObjectName("verticalLayout")
        self.horizontalLayout = QHBoxLayout()
        self.horizontalLayout.setObjectName("horizontalLayout")
        self.rb_seconds = QRadioButton(self.widget)
        self.rb_seconds.setObjectName("rb_seconds")

        self.horizontalLayout.addWidget(self.rb_seconds)

        self.rb_time = QRadioButton(self.widget)
        self.rb_time.setObjectName("rb_time")

        self.horizontalLayout.addWidget(self.rb_time)

        self.rb_datetime = QRadioButton(self.widget)
        self.rb_datetime.setObjectName("rb_datetime")

        self.horizontalLayout.addWidget(self.rb_datetime)

        self.horizontalLayout.addStretch()

        self.verticalLayout.addLayout(self.horizontalLayout)

        self.stackedWidget = QStackedWidget(self.widget)
        self.stackedWidget.setObjectName("stackedWidget")
        self.stackedWidget.setFrameShape(QFrame.NoFrame)
        self.seconds = QWidget()
        self.seconds.setObjectName("seconds")
        self.widget1 = QWidget(self.seconds)
        self.widget1.setObjectName("widget1")
        # self.widget1.setGeometry(QRect(10, 0, 163, 27))
        self.horizontalLayout_4 = QHBoxLayout(self.widget1)
        self.horizontalLayout_4.setObjectName("horizontalLayout_4")
        self.horizontalLayout_4.setContentsMargins(0, 0, 0, 0)
        self.le_seconds = QLineEdit(self.widget1)
        self.le_seconds.setObjectName("le_seconds")

        self.horizontalLayout_4.addWidget(self.le_seconds)

        self.lb_seconds = QLabel(self.widget1)
        self.lb_seconds.setObjectName("lb_seconds")

        self.horizontalLayout_4.addWidget(self.lb_seconds)

        self.horizontalLayout_4.addStretch()

        self.stackedWidget.addWidget(self.seconds)
        self.hhmmss = QWidget()
        self.hhmmss.setObjectName("hhmmss")
        self.widget2 = QWidget(self.hhmmss)
        self.widget2.setMinimumWidth(500)
        self.widget2.setObjectName("widget2")
        self.widget2.setGeometry(QRect(0, 0, 213, 28))
        self.horizontalLayout_2 = QHBoxLayout(self.widget2)
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.horizontalLayout_2.setContentsMargins(0, 0, 0, 0)
        self.lb_hour = QLabel(self.widget2)
        self.lb_hour.setObjectName("lb_hour")

        self.horizontalLayout_2.addWidget(self.lb_hour)

        self.sb_hour = QSpinBox(self.widget2)
        self.sb_hour.setObjectName("sb_hour")
        self.sb_hour.setButtonSymbols(QAbstractSpinBox.NoButtons)

        self.horizontalLayout_2.addWidget(self.sb_hour)

        self.lb_hhmmss = QLabel(self.widget2)
        self.lb_hhmmss.setObjectName("lb_hhmmss")

        self.horizontalLayout_2.addWidget(self.lb_hhmmss)

        self.te_time = QTimeEdit(self.widget2)
        self.te_time.setObjectName("te_time")
        self.te_time.adjustSize()
        # self.te_time.setMinimumWidth(200)
        # self.widget2.adjustSize()

        self.horizontalLayout_2.addWidget(self.te_time)

        self.horizontalLayout_2.addStretch()

        self.stackedWidget.addWidget(self.hhmmss)
        self.page_2 = QWidget()
        self.page_2.setObjectName("page_2")
        self.dte = QDateTimeEdit(self.page_2)

        self.dte.setObjectName("dte")
        # self.dte.setGeometry(QRect(10, 0, 164, 26))
        self.stackedWidget.addWidget(self.page_2)

        self.verticalLayout.addWidget(self.stackedWidget)

        self.horizontalLayout_3.addLayout(self.verticalLayout)

        self.verticalLayout_3.addLayout(self.horizontalLayout_3)

        self.line = QFrame(self.widget)
        self.line.setObjectName("line")
        self.line.setFrameShape(QFrame.HLine)
        self.line.setFrameShadow(QFrame.Sunken)

        self.verticalLayout_3.addWidget(self.line)

        self.setLayout(self.verticalLayout_3)

        self.stackedWidget.setCurrentIndex(0)

        self.label.setText("")
        self.pb_sign.setText("+")
        self.rb_seconds.setText("Seconds")
        self.rb_time.setText("hh:mm:ss")
        self.rb_datetime.setText("Date time")
        self.le_seconds.setText("")
        self.lb_seconds.setText("seconds")
        self.lb_hour.setText("hour")
        self.lb_hhmmss.setText("mm:ss.ms")
        self.te_time.setDisplayFormat("mm:ss.zzz")
        self.dte.setDisplayFormat("yyyy-MM-dd hh:mm:ss:zzz")
        self.dte.adjustSize()
        font = QFont()
        font.setPointSize(14)
        self.pb_sign.setFont(font)

        self.rb_seconds.toggled.connect(self.format_changed)
        self.rb_time.toggled.connect(self.format_changed)
        self.rb_datetime.toggled.connect(self.format_changed)
        self.sb_hour.setMaximum(cfg.HOUR_CUTOFF)
        self.pb_sign.clicked.connect(self.pb_sign_clicked)

        if time_value:
            self.set_time(time_value)

        self.format_changed()

        self.adjustSize()

    def format_changed(self):
        if self.rb_seconds.isChecked():
            self.stackedWidget.setCurrentIndex(0)
        if self.rb_time.isChecked():
            self.stackedWidget.setCurrentIndex(1)
        if self.rb_datetime.isChecked():
            self.stackedWidget.setCurrentIndex(2)

        self.le_seconds.setEnabled(self.rb_seconds.isChecked())
        self.le_seconds.adjustSize()
        self.lb_seconds.setEnabled(self.rb_seconds.isChecked())
        self.sb_hour.setEnabled(self.rb_time.isChecked())
        self.te_time.setEnabled(self.rb_time.isChecked())
        self.lb_hour.setEnabled(self.rb_time.isChecked())
        self.lb_hhmmss.setEnabled(self.rb_time.isChecked())
        self.dte.setEnabled(self.rb_datetime.isChecked())

    def pb_sign_clicked(self):
        if self.pb_sign.text() == "+":
            self.pb_sign.setText("-")
        else:
            self.pb_sign.setText("+")

    def get_time(self) -> Union[dec, None]:
        """
        Get time from the selected format in the time widget

        Returns:
            dec: time in seconds (None if no format selected)
        """

        time_sec = None

        if self.rb_seconds.isChecked():
            try:
                time_sec = float(self.le_seconds.text())
            except Exception:
                QMessageBox.warning(
                    None,
                    cfg.programName,
                    f"The value of seconds ({self.le_seconds.text()}) is not a decimal number",
                    QMessageBox.Ok | QMessageBox.Default,
                    QMessageBox.NoButton,
                )
                return None

        if self.rb_time.isChecked():
            time_sec = self.sb_hour.value() * 3600
            time_sec += self.te_time.time().msecsSinceStartOfDay() / 1000

        if self.rb_datetime.isChecked():
            time_sec = self.dte.dateTime().toMSecsSinceEpoch() / 1000

        if self.pb_sign.text() == "-":
            time_sec = -time_sec

        return dec(time_sec) if time_sec is not None else None

    def set_time(self, new_time: dec) -> None:
        """
        set time on time widget
        """

        self.pb_sign.setText("-" if new_time < 0 else "+")

        # seconds
        self.le_seconds.setText(f"{new_time:0.3f}")

        if new_time <= cfg.DATE_CUTOFF:  # hh:mm:ss.zzz
            h = int(abs(new_time) // 3600)
            m = int((abs(new_time) - h * 3600) // 60)
            s = int((abs(new_time) - h * 3600 - m * 60))
            ms = round((abs(new_time) - h * 3600 - m * 60 - s) * 1000)

            self.sb_hour.setValue(h)
            self.te_time.setTime(QTime(0, m, s, ms))
        else:
            self.sb_hour.setValue(0)
            self.te_time.setTime(QTime(0, 0, 0, 0))

            self.dte.setDateTime(QDateTime().fromMSecsSinceEpoch(int(new_time * 1000)))
            self.rb_datetime.setChecked(True)


'''
class get_time_widget(QWidget):
    """
    widget for selecting a time in various formats: secondes, HH:MM:SS:ZZZ or YYYY-mm-DD HH:MM:SS:ZZZ
    """

    def __init__(self, time_value=0, parent=None):
        super().__init__(parent)

        self.setWindowTitle("BORIS")

        self.widget = QWidget()
        self.widget.setObjectName("widget")

        self.widget.setGeometry(QRect(60, 171, 278, 124))
        self.verticalLayout = QVBoxLayout(self.widget)
        self.verticalLayout.setContentsMargins(0, 0, 0, 0)
        self.horizontalLayout_2 = QHBoxLayout()
        self.horizontalLayout_2.setObjectName("horizontalLayout_2")
        self.pb_sign = QPushButton(self.widget, clicked=self.pb_sign_clicked)
        self.pb_sign.setText("+")
        font = QFont()
        font.setPointSize(14)
        self.pb_sign.setFont(font)

        self.horizontalLayout_2.addWidget(self.pb_sign)

        self.gridLayout_3 = QGridLayout()
        self.gridLayout = QGridLayout()

        self.rb_seconds = QRadioButton(self.widget)
        self.rb_seconds.toggled.connect(self.format_changed)
        self.gridLayout.addWidget(self.rb_seconds, 0, 0, 1, 1)

        self.le_seconds = QLineEdit(self.widget)
        self.le_seconds.setText("0.000")
        self.le_seconds.setValidator(QRegExpValidator(QRegExp("([0-9]+([.][0-9]*)?|[.][0-9]+)")))
        self.gridLayout.addWidget(self.le_seconds, 0, 1, 1, 1)

        self.lb_seconds = QLabel(self.widget)
        self.lb_seconds.setText("seconds")
        self.lb_seconds.setIndent(0)
        self.gridLayout.addWidget(self.lb_seconds, 0, 2, 1, 1)

        self.lb_hour = QLabel(self.widget)
        self.lb_hour.setText("hour")
        self.lb_hour.setIndent(0)
        self.gridLayout.addWidget(self.lb_hour, 1, 1, 1, 1)

        self.lb_hhmmss = QLabel(self.widget)
        self.lb_hhmmss.setText("mm:ss.ms")
        self.gridLayout.addWidget(self.lb_hhmmss, 1, 2, 1, 1)

        self.rb_time = QRadioButton(self.widget)
        self.rb_time.toggled.connect(self.format_changed)
        self.gridLayout.addWidget(self.rb_time, 2, 0, 1, 1)

        self.sb_hour = QSpinBox(self.widget)
        self.sb_hour.setButtonSymbols(QAbstractSpinBox.NoButtons)
        self.sb_hour.setMinimum(0)
        self.sb_hour.setMaximum(cfg.HOUR_CUTOFF)
        self.sb_hour.setDisplayIntegerBase(10)
        self.gridLayout.addWidget(self.sb_hour, 2, 1, 1, 1)

        self.te_time = QTimeEdit(self.widget)
        self.te_time.setDisplayFormat("mm:ss.zzz")
        self.gridLayout.addWidget(self.te_time, 2, 2, 1, 1)

        self.gridLayout_3.addLayout(self.gridLayout, 0, 0, 1, 1)

        self.gridLayout_2 = QGridLayout()
        self.rb_datetime = QRadioButton(self.widget)
        self.rb_datetime.toggled.connect(self.format_changed)

        self.gridLayout_2.addWidget(self.rb_datetime, 0, 0, 1, 1)

        self.dte = QDateTimeEdit(self.widget)
        self.dte.setDisplayFormat("yyyy-MM-dd hh:mm:ss.zzz")

        self.gridLayout_2.addWidget(self.dte, 0, 1, 1, 1)

        self.gridLayout_3.addLayout(self.gridLayout_2, 1, 0, 1, 1)

        self.horizontalLayout_2.addLayout(self.gridLayout_3)

        self.verticalLayout.addLayout(self.horizontalLayout_2)

        self.setLayout(self.verticalLayout)

        if time_value:
            self.set_time(time_value)

        self.format_changed()

    def format_changed(self):
        self.le_seconds.setEnabled(self.rb_seconds.isChecked())
        self.lb_seconds.setEnabled(self.rb_seconds.isChecked())
        self.sb_hour.setEnabled(self.rb_time.isChecked())
        self.te_time.setEnabled(self.rb_time.isChecked())
        self.lb_hour.setEnabled(self.rb_time.isChecked())
        self.lb_hhmmss.setEnabled(self.rb_time.isChecked())
        self.dte.setEnabled(self.rb_datetime.isChecked())

    def pb_sign_clicked(self):
        if self.pb_sign.text() == "+":
            self.pb_sign.setText("-")
        else:
            self.pb_sign.setText("+")

    def get_time(self) -> dec:
        """
        return time in seconds
        """

        if self.rb_seconds.isChecked():
            try:
                time_sec = float(self.le_seconds.text())
            except Exception:
                QMessageBox.warning(
                    None,
                    cfg.programName,
                    "The value is not a decimal number",
                    QMessageBox.Ok | QMessageBox.Default,
                    QMessageBox.NoButton,
                )
                return None

        if self.rb_time.isChecked():
            time_sec = self.sb_hour.value() * 3600
            time_sec += self.te_time.time().msecsSinceStartOfDay() / 1000

        if self.rb_datetime.isChecked():
            time_sec = self.dte.dateTime().toMSecsSinceEpoch() / 1000

        if self.pb_sign.text() == "-":
            time_sec = -time_sec

        return dec(time_sec)

    def set_time(self, new_time: float) -> None:
        self.pb_sign.setText("-" if new_time < 0 else "+")

        # seconds
        self.le_seconds.setText(f"{new_time:0.3f}")

        # hh:mm:ss.zzz
        h = int(abs(new_time) // 3600)
        m = int((abs(new_time) - h * 3600) // 60)
        s = int((abs(new_time) - h * 3600 - m * 60))
        ms = round((abs(new_time) - h * 3600 - m * 60 - s) * 1000)

        self.sb_hour.setValue(h)
        self.te_time.setTime(QTime(0, m, s, ms))

        if new_time > cfg.DATE_CUTOFF:
            self.dte.setDateTime(QDateTime().fromMSecsSinceEpoch(int(new_time * 1000)))
'''


class Ask_time(QDialog):
    def __init__(self, time_value=0):
        super().__init__()
        self.setWindowTitle("")

        hbox = QVBoxLayout(self)
        self.label = QLabel()
        self.label.setText("")
        hbox.addWidget(self.label)

        self.time_widget = get_time_widget(time_value)

        hbox.addWidget(self.time_widget)

        self.pbOK = QPushButton("OK", clicked=self.pb_ok_clicked)
        self.pbOK.setDefault(True)

        self.pbCancel = QPushButton("Cancel")
        self.pbCancel.clicked.connect(self.reject)

        self.hbox2 = QHBoxLayout(self)
        self.hbox2.addItem(QSpacerItem(241, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))
        self.hbox2.addWidget(self.pbCancel)
        self.hbox2.addWidget(self.pbOK)
        hbox.addLayout(self.hbox2)
        self.setLayout(hbox)

        # if time_value:
        #    self.time_widget.set_time(time_value)

    def pb_ok_clicked(self):
        if (
            not self.time_widget.rb_seconds.isChecked()
            and not self.time_widget.rb_time.isChecked()
            and not self.time_widget.rb_datetime.isChecked()
        ):
            QMessageBox.warning(
                None,
                cfg.programName,
                "Select an option",
                QMessageBox.Ok | QMessageBox.Default,
                QMessageBox.NoButton,
            )
            return
        # test time value
        if self.time_widget.get_time() is None:
            return

        self.accept()


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
        spinbox (sb)
        doubleSpinbox (dsb)
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
                # 6 - number of decimals

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
                    self.elements[element[1]].setCurrentIndex([idx for idx, x in enumerate(element[2]) if x[1] == "selected"][0])
                except Exception:
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


class Duplicate_items(QDialog):
    """
    let user show between behaviors/subjects that are coded by same key
    """

    def __init__(self, text, codes_list):
        super(Duplicate_items, self).__init__()

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

        hlayout = QHBoxLayout()
        hlayout.addItem(QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))

        pbCancel = QPushButton("Cancel", clicked=self.reject)
        hlayout.addWidget(pbCancel)

        pbOK = QPushButton("OK", clicked=self.accept)
        pbOK.setDefault(True)
        hlayout.addWidget(pbOK)

        Vlayout.addLayout(hlayout)

        self.setLayout(Vlayout)

        # self.installEventFilter(self)

        self.setMaximumSize(1024, 960)

    def getCode(self):
        """
        get selected behavior code
        """
        if self.lw.selectedItems():
            return self.lw.selectedItems()[0].text()
        else:
            return None


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


'''
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
'''


class FindInEvents(QWidget):
    """
    "find in events" dialog box
    """

    clickSignal = pyqtSignal(str)

    currentIdx: int = -1

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
        self.pbCancel = QPushButton(cfg.CLOSE)
        self.pbCancel.clicked.connect(lambda: self.click(cfg.CLOSE))
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

    def __init__(self):
        super().__init__()

        self.setWindowTitle("Find/Replace events")

        hbox = QVBoxLayout()

        self.combo_fields = QComboBox()
        self.combo_fields.addItems(("Choose a field", "Subject", "Behavior", "Modifiers", "Comment"))
        hbox.addWidget(self.combo_fields)

        # self.cbSubject = QCheckBox("Subject")
        # self.cbSubject.setChecked(False)
        # hbox.addWidget(self.cbSubject)

        # self.cbBehavior = QCheckBox("Behavior")
        # self.cbBehavior.setChecked(False)
        # hbox.addWidget(self.cbBehavior)

        # self.cbModifier = QCheckBox("Modifiers")
        # self.cbModifier.setChecked(False)
        # hbox.addWidget(self.cbModifier)

        # self.cbComment = QCheckBox("Comment")
        # self.cbComment.setChecked(False)
        # hbox.addWidget(self.cbComment)

        self.lbFind = QLabel("Find")
        hbox.addWidget(self.lbFind)

        self.findText = QLineEdit()
        hbox.addWidget(self.findText)

        self.lbReplace = QLabel("Replace")
        hbox.addWidget(self.lbReplace)

        self.replaceText = QLineEdit()
        hbox.addWidget(self.replaceText)

        self.cbFindInSelectedEvents = QCheckBox("Find/Replace only in selected events")
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

        self.lb_results = QLabel(" ")
        hbox.addWidget(self.lb_results)

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
        hbox2.addItem(QSpacerItem(241, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))

        self.pbSave = QPushButton("Save results", clicked=self.save_results)
        hbox2.addWidget(self.pbSave)

        self.pbCancel = QPushButton(cfg.CANCEL, clicked=self.reject)
        hbox2.addWidget(self.pbCancel)
        self.pbCancel.setVisible(False)

        self.pbOK = QPushButton(cfg.OK, clicked=self.accept)
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

        vbox.addWidget(QLabel("Descriptive statistics"))

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
