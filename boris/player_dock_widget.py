"""
BORIS
Behavioral Observation Research Interactive Software
Copyright 2012-2025 Olivier Friard

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
from . import mpv2 as mpv
import config as cfg
import gui_utilities


from PySide6.QtWidgets import (
    QLabel,
    QDockWidget,
    QWidget,
    QHBoxLayout,
    QVBoxLayout,
    QSlider,
    QSizePolicy,
    QStackedWidget,
    QToolButton,
)
from PySide6.QtCore import Signal, QEvent, Qt, QTimer
from PySide6.QtGui import QIcon, QAction

import socket
import json
import subprocess


class Clickable_label(QLabel):
    """
    QLabel class for visualiziong frames for geometric measurments
    Label emits a signal when clicked
    """

    mouse_pressed_signal = Signal(int, QEvent)

    def __init__(self, id_, parent=None):
        QLabel.__init__(self, parent)
        self.id_ = id_

    def mousePressEvent(self, event):
        """
        label clicked
        """
        logging.debug(f"mousepress event: label {self.id_} clicked {event.pos()}")

        """
        super().mousePressEvent(event)
        x, y = event.pos().x(), event.pos().y()
        draw_on_pixmap(self, x, y)  # Example usage
        """

        self.mouse_pressed_signal.emit(self.id_, event)


def mpv_logger(player_id, loglevel, component, message):
    """
    redirect MPV log messages to general logging system
    """

    logging.debug(f"MPV player #{player_id}: [{loglevel}] {component}: {message}")


class macos_MPV:
    """
    class for managing mpv through iptc
    """

    playlist_count = 1
    playlist_pos = 1
    playlist: list = [{"filename": "aaaa"}, {"filename": "bbbbb"}]
    media_durations: list = []
    cumul_media_durations: list = []
    fps: list = []
    _pause: bool = False

    def __init__(self, socket_path=cfg.MPV_SOCKET, parent=None):
        self.socket_path = socket_path
        self.process = None
        self.sock = None
        self.init_mpv()
        self.init_socket()

    def init_mpv(self):
        """Start mpv process and embed it in the PySide6 application."""
        print("init_mpv")
        # print(f"{self.winId()=}")
        self.process = subprocess.Popen(
            [
                "mpv",
                "--no-border",
                "--osc=no",  # no on screen commands
                "--input-ipc-server=" + self.socket_path,
                # "--wid=" + str(int(self.winId())),  # Embed in the widget
                "--idle",  # Keeps mpv running with no video
            ],
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )

        print(self.process)

    def init_socket(self):
        """
        Initialize the JSON IPC socket.
        """
        print("init socket")
        self.sock = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        QTimer.singleShot(1000, self.connect_socket)  # Allow time for mpv to initialize

    def connect_socket(self):
        """
        Connect to the mpv IPC socket.
        """
        print("connect socket")
        try:
            self.sock.connect(self.socket_path)
            print("Connected to mpv IPC server.")
        except socket.error as e:
            print(f"Failed to connect to mpv IPC server: {e}")
        print("end of connect_socket")

    def send_command(self, command):
        """
        Send a JSON command to the mpv IPC server.
        """
        print(f"send command: {command}")
        try:
            # Create a Unix socket
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as client:
                # Connect to the MPV IPC server
                client.connect(self.socket_path)
                # Send the JSON command
                # print(f"{json.dumps(command).encode('utf-8')=}")
                client.sendall(json.dumps(command).encode("utf-8") + b"\n")
                # Receive the response
                response = client.recv(2000)
                print()
                print(f"{response=}")
                # Parse the response as JSON
                response_data = json.loads(response.decode("utf-8"))
                print(f"{response_data=}")
                # Return the 'data' field which contains the playback position
                return response_data.get("data")
        except FileNotFoundError:
            print("Error: Socket file not found.")
        except Exception as e:
            print(f"An error occurred: {e}")
        return None

    @property
    def time_pos(self):
        time_pos = self.send_command({"command": ["get_property", "time-pos"]})
        print(f"time pos: {time_pos}")
        return time_pos

    @property
    def duration(self):
        duration_ = self.send_command({"command": ["get_property", "duration"]})
        print(f"duration: {duration_}")
        return duration_

    @property
    def video_zoom(self):
        return self.send_command({"command": ["get_property", "video-zoom"]})

    @video_zoom.setter
    def video_zoom(self, value):
        self._video_zoom = value

    @property
    def pause(self):
        return 1

    @pause.setter
    def pause(self, value):
        return self.send_command({"command": ["set_property", "pause", value]})

    @property
    def estimated_frame_number(self):
        return self.send_command({"command": ["get_property", "estimated_frame_number-pos"]})

    def stop(self):
        return print("stopped")

    def playlist_append(self, media):
        self.playlist.append(media)

    def wait_until_playing(self):
        return

    def seek(self, value, mode: str):
        return

    @property
    def playback_time(self):
        playback_time_ = self.send_command({"command": ["get_property", "playback-time"]})
        print(f"playback_time: {playback_time_}")
        return playback_time_


class DW_player(QDockWidget):
    """
    Define the player class
    """

    key_pressed_signal = Signal(QEvent)
    volume_slider_moved_signal = Signal(int, int)
    mute_action_triggered_signal = Signal(int)
    view_signal = Signal(int, str, int)
    resize_signal = Signal(int)

    def __init__(self, id_, parent=None):
        super().__init__(parent)
        self.id_ = id_
        self.setWindowTitle(f"Player #{id_ + 1}")
        self.setObjectName(f"player{id_ + 1}")

        self.stack1 = QWidget()
        self.hlayout = QHBoxLayout()

        self.videoframe = QWidget(self)

        if sys.platform.startswith(cfg.MACOS_CODE):
            self.player = macos_MPV()
        else:
            self.player = mpv.MPV(
                wid=str(int(self.videoframe.winId())),
                vo="x11" if sys.platform.startswith("linux") else "",
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

        theme_mode = gui_utilities.theme_mode()

        self.mute_action.setIcon(QIcon(f":/volume_xmark_{theme_mode}"))
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
        theme_mode = gui_utilities.theme_mode()
        if self.player.mute:
            self.mute_action.setIcon(QIcon(f":/volume_xmark_{theme_mode}"))
        else:
            self.mute_action.setIcon(QIcon(f":/volume_off_{theme_mode}"))
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
