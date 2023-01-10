"""
BORIS
Behavioral Observation Research Interactive Software
Copyright 2012-2022 Olivier Friard

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

# add misc directory to search path for mpv-1.dll
import os
import sys
import logging
import pathlib as pl
import datetime as dt

os.environ["PATH"] = os.path.dirname(__file__) + os.sep + "misc" + os.pathsep + os.environ["PATH"]

try:
    from . import mpv2 as mpv

    # check if MPV API v. 1
    try:
        if "libmpv.so.1" in mpv.sofile:
            from . import mpv as mpv
    except AttributeError:
        if "mpv-1.dll" in mpv.dll:
            from . import mpv as mpv

except RuntimeError:  # libmpv found but version too old
    from . import mpv as mpv

except OSError:  # libmpv not found
    msg = "LIBMPV library not found!\n"
    logging.critical(msg)
    # append to boris.log file
    with open(pl.Path("~").expanduser() / "boris.log", "a") as f_out:
        f_out.write(f"{dt.datetime.now():%Y-%m-%d %H:%M}\n")
        f_out.write(msg)
        f_out.write("-" * 80 + "\n")
    sys.exit()


from PyQt5.QtWidgets import QLabel, QDockWidget, QWidget, QHBoxLayout, QSlider, QSizePolicy, QStackedWidget
from PyQt5.QtCore import pyqtSignal, QEvent, Qt

import logging


class Clickable_label(QLabel):
    """
    QLabel class for visualiziong frames for geometric measurments
    Label emits a signal when clicked
    """

    mouse_pressed_signal = pyqtSignal(int, QEvent)

    def __init__(self, id_, parent=None):
        QLabel.__init__(self, parent)
        self.id_ = id_

    def mousePressEvent(self, event):
        """
        label clicked
        """

        logging.debug(f"mousepress event: label {self.id_} clicked")

        self.mouse_pressed_signal.emit(self.id_, event)


class DW_player(QDockWidget):

    key_pressed_signal = pyqtSignal(QEvent)
    volume_slider_moved_signal = pyqtSignal(int, int)
    view_signal = pyqtSignal(int, str, int)
    resize_signal = pyqtSignal(int)

    def __init__(self, id_, parent=None):
        super().__init__(parent)
        self.id_ = id_
        self.zoomed = False
        self.setWindowTitle(f"Player #{id_ + 1}")
        self.setObjectName(f"player{id_ + 1}")

        self.stack1 = QWidget()
        self.hlayout = QHBoxLayout()

        self.videoframe = QWidget(self)

        self.player = mpv.MPV(
            wid=str(int(self.videoframe.winId())),
            # vo='x11', # You may not need this
            log_handler=None,
            loglevel="debug",
        )

        self.player.screenshot_format = "png"
        self.hlayout.addWidget(self.videoframe)

        self.volume_slider = QSlider(Qt.Vertical, self)
        self.volume_slider.setFocusPolicy(Qt.NoFocus)
        self.volume_slider.setMaximum(100)
        self.volume_slider.setValue(50)
        self.volume_slider.sliderMoved.connect(self.volume_slider_moved)

        self.hlayout.addWidget(self.volume_slider)

        self.stack1.setLayout(self.hlayout)

        self.stack2 = QWidget()
        self.hlayout2 = QHBoxLayout()
        self.frame_viewer = Clickable_label(id_)

        self.frame_viewer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.frame_viewer.setAlignment(Qt.AlignCenter)
        self.frame_viewer.setStyleSheet("QLabel {background-color: black;}")

        self.hlayout2.addWidget(self.frame_viewer)
        self.stack2.setLayout(self.hlayout2)

        self.stack = QStackedWidget(self)
        self.stack.addWidget(self.stack1)
        self.stack.addWidget(self.stack2)

        self.setWidget(self.stack)

        self.stack.setCurrentIndex(0)

    def volume_slider_moved(self):
        """
        emit signal when volume slider moved
        """
        self.volume_slider_moved_signal.emit(self.id_, self.volume_slider.value())

    def keyPressEvent(self, event):
        """
        emit signal when key pressed on dock widget
        """
        self.key_pressed_signal.emit(event)

    '''
    def view_signal_triggered(self, msg, button):
        """
        transmit signal received by video frame
        """
        self.view_signal.emit(self.id_, msg, button)
    '''

    def resizeEvent(self, dummy):
        """
        emits signal when dockwidget resized
        """

        self.resize_signal.emit(self.id_)
