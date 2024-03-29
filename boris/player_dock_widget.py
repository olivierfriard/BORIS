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
import logging
import functools
from PyQt5.QtWidgets import (
    QLabel,
    QDockWidget,
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QSlider,
    QSizePolicy,
    QStackedWidget,
    QToolButton,
    QAction,
)
from PyQt5.QtCore import pyqtSignal, QEvent, Qt
from PyQt5.QtGui import QIcon

try:
    from . import mpv2 as mpv

    # check if MPV API v. 1
    # is v. 1 use the old version of mpv.py
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
    sys.exit()


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
        """logging.debug(f"mousepress event: label {self.id_} clicked")"""

        self.mouse_pressed_signal.emit(self.id_, event)


def mpv_logger(player_id, loglevel, component, message):
    """
    redirect MPV log messages to general logging system
    """

    logging.debug(f"MPV player #{player_id}: [{loglevel}] {component}: {message}")


class DW_player(QDockWidget):
    """
    Define the player class
    """

    key_pressed_signal = pyqtSignal(QEvent)
    volume_slider_moved_signal = pyqtSignal(int, int)
    mute_action_triggered_signal = pyqtSignal(int)
    view_signal = pyqtSignal(int, str, int)
    resize_signal = pyqtSignal(int)

    def __init__(self, id_, parent=None):
        super().__init__(parent)
        self.id_ = id_
        self.setWindowTitle(f"Player #{id_ + 1}")
        self.setObjectName(f"player{id_ + 1}")

        self.stack1 = QWidget()
        self.hlayout = QHBoxLayout()

        self.videoframe = QWidget(self)

        self.player = mpv.MPV(
            wid=str(int(self.videoframe.winId())),
            # vo='x11', # You may not need this
            log_handler=functools.partial(mpv_logger, self.id_),
            loglevel="debug",
        )

        self.player.screenshot_format = "png"
        self.hlayout.addWidget(self.videoframe)

        # layout volume slider and mute button
        self.vlayout = QVBoxLayout()

        # volume slider
        self.volume_slider = QSlider(Qt.Vertical, self)
        self.volume_slider.setFocusPolicy(Qt.NoFocus)
        self.volume_slider.setMaximum(100)
        self.volume_slider.setValue(50)
        self.volume_slider.sliderMoved.connect(self.volume_slider_moved)

        self.vlayout.addWidget(self.volume_slider)

        # mute button
        self.mute_button = QToolButton()
        self.mute_button.setFocusPolicy(Qt.NoFocus)
        self.mute_button.setAutoRaise(True)
        self.mute_action = QAction()
        self.mute_action.setIcon(QIcon(":/volume_xmark"))
        self.mute_action.triggered.connect(self.mute_action_triggered)
        self.mute_button.setDefaultAction(self.mute_action)

        self.vlayout.addWidget(self.mute_button)

        self.hlayout.addLayout(self.vlayout)

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

    def mute_action_triggered(self):
        """
        emit signal when mute action is triggered
        """
        if self.player.mute:
            self.mute_action.setIcon(QIcon(":/volume_xmark"))
        else:
            self.mute_action.setIcon(QIcon(":/volume_off"))
        self.mute_action_triggered_signal.emit(self.id_)

    def keyPressEvent(self, event):
        """
        emit signal when key pressed on dock widget
        """
        self.key_pressed_signal.emit(event)

    def resizeEvent(self, _):
        """
        emits signal when dockwidget resized
        """

        self.resize_signal.emit(self.id_)
