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

from PyQt5.QtWidgets import (QLabel, QFrame, QDockWidget, QWidget,
                             QHBoxLayout, QSlider, QSizePolicy, QStackedWidget,
                             QMessageBox
                             )
from PyQt5.QtCore import (pyqtSignal, QEvent, Qt, QSize)
from PyQt5.QtGui import (QPalette, QColor)

import logging
from boris.config import programName


class Click_label(QLabel):
    """
    QLabel class for visualiziong frames (frame-by-frame mode)
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
        self.mouse_pressed_signal.emit(self.id_, event)


class Video_frame(QFrame):
    """
    QFrame class for visualizing video with VLC
    Frame emits a signal when clicked or resized
    """

    video_frame_signal = pyqtSignal(str, int)
    x_click, y_click = 0, 0

    def sizeHint(self):
        return QSize(150, 200)


    # def mouseDoubleClickEvent(self, QMouseEvent):
    #    """handle double click on video frame""""


    def mousePressEvent(self, QMouseEvent):
        """
        emits signal when mouse pressed on video
        """

        xm, ym = QMouseEvent.x(), QMouseEvent.y()
        button = QMouseEvent.button()

        xf, yf = self.geometry().width(), self.geometry().height()

        if not self.v_resolution:
            QMessageBox.warning(self, programName,
                                ("The focus video area is not available<br>"
                                 "because the video resolution is not available.<br>"
                                 "Try to re-encode the video (Tools > Resize/re-encode video)")
                                )
            return
        if xf / yf >= self.h_resolution / self.v_resolution:
            yv = yf
            xv = int(yf * self.h_resolution / self.v_resolution)
            x_start_video = int((xf - xv) / 2)
            y_start_video = 0
            x_end_video = x_start_video + xv
            y_end_video = yv

            if xm < x_start_video or xm > x_end_video:
                self.video_frame_signal.emit("clicked_out_of_video", button)
                return

            x_click_video = xm - x_start_video
            y_click_video = ym

        if xf / yf < self.h_resolution / self.v_resolution:
            xv = xf
            yv = int(xf / (self.h_resolution / self.v_resolution))
            y_start_video = int((yf - yv) / 2)
            x_start_video = 0
            y_end_video = y_start_video + yv
            x_end_video = xv

            if ym < y_start_video or ym > y_end_video:
                self.video_frame_signal.emit("clicked_out_of_video", button)
                return

            y_click_video = ym - y_start_video
            x_click_video = xm

        self.x_click = int(x_click_video / xv * self.h_resolution)
        self.y_click = int(y_click_video / yv * self.v_resolution)

        self.video_frame_signal.emit("clicked", button)

    def resizeEvent(self, dummy):
        """
        emits signal when video resized
        """

        logging.debug("video frame resized")

        self.video_frame_signal.emit("resized", 0)


class DW(QDockWidget):

    key_pressed_signal = pyqtSignal(QEvent)
    volume_slider_moved_signal = pyqtSignal(int, int)
    view_signal = pyqtSignal(int, str, int)

    def __init__(self, id_, parent=None):
        super().__init__(parent)
        self.id_ = id_
        self.zoomed = False
        self.setWindowTitle(f"Player #{id_ + 1}")
        self.setObjectName(f"player{id_ + 1}")

        self.stack1 = QWidget()
        self.hlayout = QHBoxLayout()
        self.videoframe = Video_frame()
        self.videoframe.video_frame_signal.connect(self.view_signal_triggered)
        self.palette = self.videoframe.palette()
        self.palette.setColor(QPalette.Window, QColor(0, 0, 0))
        self.videoframe.setPalette(self.palette)
        self.videoframe.setAutoFillBackground(True)
        self.hlayout.addWidget(self.videoframe)
        self.volume_slider = QSlider(Qt.Vertical, self)
        self.volume_slider.setMaximum(100)
        self.volume_slider.setValue(50)
        self.volume_slider.sliderMoved.connect(self.volume_slider_moved)
        self.hlayout.addWidget(self.volume_slider)
        self.stack1.setLayout(self.hlayout)

        self.stack2 = QWidget()
        self.hlayout2 = QHBoxLayout()
        self.frame_viewer = Click_label(id_)

        self.frame_viewer.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
        self.frame_viewer.setAlignment(Qt.AlignCenter)
        self.frame_viewer.setStyleSheet("QLabel {background-color: black;}")

        self.hlayout2.addWidget(self.frame_viewer)
        self.stack2.setLayout(self.hlayout2)

        self.stack = QStackedWidget(self)
        self.stack.addWidget(self.stack1)
        self.stack.addWidget(self.stack2)

        self.setWidget(self.stack)


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


    def view_signal_triggered(self, msg, button):
        """
        transmit signal received by video frame
        """
        self.view_signal.emit(self.id_, msg, button)
