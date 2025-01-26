"""
BORIS
Behavioral Observation Research Interactive Software
Copyright 2012-2025 Olivier Friard


  This program is free software; you can redistribute it and/or modify
  it under the terms of the GNU General Public License as published by
  the Free Software Foundation; either version 2 of the License, or
  (at your option) any later version.

  This program is distributed in the hope that it will be useful,
  but WITHOUT ANY WARRANTY; without even the implied warranty of
  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
  GNU General Public License for more details.

  You should have received a copy of the GNU General Public License
  along with this program; if not, write to the Free Software
  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
  MA 02110-1301, USA.

"""

import wave
from . import config as cfg
import matplotlib

matplotlib.use("Qt5Agg")

import numpy as np
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel
from PySide6.QtCore import Signal, QEvent, Qt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.ticker as mticker

# matplotlib.pyplot.switch_backend("Qt5Agg")


class Plot_waveform_RT(QWidget):
    # send keypress event to mainwindow
    sendEvent = Signal(QEvent)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Waveform")

        self.interval = 60  # interval of visualization (in seconds)
        self.time_mem = -1

        self.cursor_color: str = cfg.REALTIME_PLOT_CURSOR_COLOR

        self.spectro_color_map = matplotlib.pyplot.get_cmap("viridis")

        self.figure = Figure()
        self.ax = self.figure.add_subplot(1, 1, 1)

        self.canvas = FigureCanvas(self.figure)

        layout = QVBoxLayout()
        layout.addWidget(self.canvas)

        hlayout1 = QHBoxLayout()
        hlayout1.addWidget(QLabel("Time interval"))
        hlayout1.addWidget(
            QPushButton(
                "+",
                self,
                clicked=lambda: self.time_interval_changed(1),
                focusPolicy=Qt.NoFocus,
            )
        )
        hlayout1.addWidget(
            QPushButton(
                "-",
                self,
                clicked=lambda: self.time_interval_changed(-1),
                focusPolicy=Qt.NoFocus,
            )
        )
        layout.addLayout(hlayout1)

        self.setLayout(layout)

        self.installEventFilter(self)

    def eventFilter(self, receiver, event):
        """
        send event (if keypress) to main window
        """
        if event.type() == QEvent.KeyPress:
            self.sendEvent.emit(event)
            return True
        else:
            return False

    def get_wav_info(self, wav_file: str):
        """
        read wav file and extract information

        Args:
            wav_file (str): path of wav file

        Returns:
            np.array: signal contained in wav file
            int: frame rate of wav file

        """
        try:
            wav = wave.open(wav_file, "r")
            frames = wav.readframes(-1)
            signal = np.fromstring(frames, dtype=np.int16)
            frame_rate = wav.getframerate()
            wav.close()
            return signal, frame_rate
        except Exception:
            return np.array([]), 0

    def load_wav(self, wav_file_path: str) -> dict:
        """
        load wav file in numpy array

        Args:
            wav_file_path (str): path of wav file

        Returns:
            dict: "error" key if error, "media_length" and "frame_rate"
        """

        try:
            self.sound_info, self.frame_rate = self.get_wav_info(wav_file_path)
            if not self.frame_rate:
                return {"error": f"unknown format for file {wav_file_path}"}
        except FileNotFoundError:
            return {"error": "File not found: {}".format(wav_file_path)}

        self.media_length = len(self.sound_info) / self.frame_rate
        self.wav_file_path = wav_file_path

        return {"media_length": self.media_length, "frame_rate": self.frame_rate}

    def time_interval_changed(self, action: int) -> None:
        """
        change the time interval for plotting waveform

        Args:
            action (int): -1 decrease time interval, +1 increase time interval

        Returns:
            None
        """

        if action == -1 and self.interval <= 5:
            return
        self.interval += 5 * action
        self.plot_waveform(current_time=self.time_mem, force_plot=True)

    def plot_waveform(self, current_time: float, force_plot: bool = False):
        """
        plot sound waveform centered on the current time

        Args:
            current_time (float): time for displaying waveform
            force_plot (bool): force plot even if media paused
        """

        if not force_plot and current_time == self.time_mem:
            return

        self.time_mem = current_time

        self.ax.clear()

        # start
        if current_time <= self.interval / 2:
            time_ = np.linspace(
                0,
                len(self.sound_info[: int((self.interval) * self.frame_rate)]) / self.frame_rate,
                num=len(self.sound_info[: int((self.interval) * self.frame_rate)]),
            )
            self.ax.plot(time_, self.sound_info[: int((self.interval) * self.frame_rate)])

            self.ax.set_xlim(current_time - self.interval / 2, current_time + self.interval / 2)

            # cursor
            self.ax.axvline(x=current_time, color=self.cursor_color, linestyle="-")

        elif current_time >= self.media_length - self.interval / 2:
            i = int(round(len(self.sound_info) - (self.interval * self.frame_rate), 0))

            time_ = np.linspace(
                0,
                len(self.sound_info[i:]) / self.frame_rate,
                num=len(self.sound_info[i:]),
            )
            self.ax.plot(time_, self.sound_info[i:])

            lim1 = current_time - (self.media_length - self.interval / 2)
            lim2 = lim1 + self.interval

            self.ax.set_xlim(lim1, lim2)

            self.ax.xaxis.set_major_locator(mticker.FixedLocator(self.ax.get_xticks().tolist()))
            self.ax.set_xticklabels([str(round(w + self.media_length - self.interval, 1)) for w in self.ax.get_xticks()])

            # cursor
            self.ax.axvline(x=lim1 + self.interval / 2, color=self.cursor_color, linestyle="-")

        # middle
        else:
            start = (current_time - self.interval / 2) * self.frame_rate
            end = (current_time + self.interval / 2) * self.frame_rate

            time_ = np.linspace(
                0,
                len(self.sound_info[int(round(start, 0)) : int(round(end, 0))]) / self.frame_rate,
                num=len(self.sound_info[int(round(start, 0)) : int(round(end, 0))]),
            )

            self.ax.plot(time_, self.sound_info[int(round(start, 0)) : int(round(end, 0))])

            self.ax.xaxis.set_major_locator(mticker.FixedLocator(self.ax.get_xticks().tolist()))
            self.ax.set_xticklabels([str(round(current_time + w - self.interval / 2, 1)) for w in self.ax.get_xticks()])

            # cursor
            self.ax.axvline(x=self.interval / 2, color=self.cursor_color, linestyle="-")
        """self.figure.subplots_adjust(wspace=0, hspace=0)"""

        self.canvas.draw()
