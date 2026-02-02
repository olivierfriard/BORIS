"""
BORIS
Behavioral Observation Research Interactive Software
Copyright 2012-2026 Olivier Friard


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

import matplotlib

from . import config as cfg

matplotlib.use("QtAgg")

import matplotlib.ticker as mticker
import numpy as np
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PySide6.QtCore import QEvent, Qt, Signal
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget


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

        hlayout1.addStretch()

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
            # signal = np.fromstring(frames, dtype=np.int16)
            signal = np.frombuffer(frames, dtype=np.int16)
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
        self.waveform_max = float(np.max(np.abs(self.sound_info)))

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

    def plot_waveform(self, current_time: float | None, force_plot: bool = False, window_title: str = "") -> None:
        """
        Optimized waveform plotting: plot sound waveform centered on the current time.
        Uses downsampling to limit plotted points and absolute seconds on x-axis.
        """

        print(f"waveform {current_time=}    {self.time_mem=}")

        if not force_plot and current_time == self.time_mem:
            return

        if window_title:
            self.setWindowTitle(window_title)
        self.time_mem = current_time
        self.ax.clear()

        if current_time is None:
            return

        half = self.interval / 2.0
        # compute absolute window (clamped)
        start_time = max(0.0, current_time - half)
        end_time = min(self.media_length, current_time + half)

        # sample indices
        i0 = int(round(start_time * self.frame_rate))
        i1 = int(round(end_time * self.frame_rate))
        # clip to array bounds
        i0 = max(0, min(i0, len(self.sound_info)))
        i1 = max(0, min(i1, len(self.sound_info)))

        chunk = self.sound_info[i0:i1]
        if chunk.size == 0:
            # nothing to plot
            self.canvas.draw()
            return

        # Determine downsample factor so we draw at most max_points
        max_points = 3000  # tweak: number of points to plot for speed/quality tradeoff
        length = chunk.shape[0]
        if length <= max_points:
            # no downsampling needed
            y = chunk.astype(float)
            x = np.linspace(start_time, end_time, num=length)
        else:
            # block-aggregate: avoid fancy resampling for speed
            # compute block size (ceil)
            block = int(np.ceil(length / max_points))
            # trim chunk so it divides evenly into blocks
            trim = (block * max_points) - length
            if trim > 0:
                # pad on the right with zeros? better: trim the end a bit to make exact blocks
                chunk_padlen = length - (length % block)
                trimmed = chunk[:chunk_padlen]
            else:
                trimmed = chunk
            # reshape and compute mean (or RMS) per block
            reshaped = trimmed.reshape(-1, block)
            # use mean to preserve waveform shape; if you prefer amplitude envelope use np.abs then mean
            y = reshaped.mean(axis=1)
            # create absolute times for block centers
            # number of blocks:
            n_blocks = y.shape[0]
            # block centers times
            x = np.linspace(start_time, start_time + (len(trimmed) / self.frame_rate), num=n_blocks)

        # Plot (convert to float for matplotlib)
        self.ax.plot(x, y, linewidth=0.6)

        # set visible range and ticks (absolute time)
        self.ax.set_xlim(start_time, end_time)

        self.ax.set_ylim(-self.waveform_max, self.waveform_max)

        # Cursor: absolute time
        if start_time <= current_time <= end_time:
            self.ax.axvline(x=current_time, color=self.cursor_color, linestyle="-")

        # Format x ticks: use at most 8 major ticks
        # self.ax.xaxis.set_major_locator(mticker.MaxNLocator(nbins=8, prune="both"))
        self.ax.xaxis.set_major_locator(mticker.MultipleLocator(0.5))
        # optional minor ticks
        self.ax.xaxis.set_minor_locator(mticker.AutoMinorLocator(5))
        self.ax.tick_params(axis="x", which="minor", length=3)

        # Optionally label y-axis off (waveform amplitude might be large ints)
        self.ax.set_ylabel("")  # or keep as is

        self.canvas.draw()
