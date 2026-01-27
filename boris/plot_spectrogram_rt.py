"""
BORIS
Behavioral Observation Research Interactive Software
Copyright 2012-2026 Olivier Friard

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

import wave

import matplotlib

matplotlib.use("QtAgg")


import matplotlib.ticker as mticker
import numpy as np
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from PySide6.QtCore import QEvent, Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)
from scipy import signal

from . import config as cfg


class Plot_spectrogram_RT(QWidget):
    # send keypress event to mainwindow
    sendEvent = Signal(QEvent)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Spectrogram")

        self.interval = 10  # interval of visualization (in seconds)
        self.time_mem = -1

        self.cursor_color = cfg.REALTIME_PLOT_CURSOR_COLOR

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

        hlayout2 = QHBoxLayout()
        hlayout2.addWidget(QLabel("Frequency interval"))
        self.sb_freq_min = QSpinBox(valueChanged=self.frequency_interval_changed, focusPolicy=Qt.NoFocus)
        self.sb_freq_min.setRange(0, 200000)
        self.sb_freq_min.setSingleStep(100)
        self.sb_freq_max = QSpinBox(valueChanged=self.frequency_interval_changed, focusPolicy=Qt.NoFocus)
        self.sb_freq_max.setRange(0, 200000)
        self.sb_freq_max.setSingleStep(100)
        hlayout2.addWidget(self.sb_freq_min)
        hlayout2.addWidget(self.sb_freq_max)
        hlayout2.addStretch()
        layout.addLayout(hlayout2)

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

    def get_wav_info(self, wav_file: str) -> tuple[np.array, int]:
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
            sound_info = np.frombuffer(frames, dtype=np.int16)
            frame_rate = wav.getframerate()
            wav.close()
            return sound_info, frame_rate
        except Exception:
            return np.array([]), 0

    def time_interval_changed(self, action: int):
        """
        change the time interval for plotting spectrogram

        Args:
            action (int): -1 decrease time interval, +1 increase time interval

        Returns:
            None
        """

        if action == -1 and self.interval <= 5:
            return
        self.interval += 5 * action
        self.plot_spectro(current_time=self.time_mem, force_plot=True)

    def frequency_interval_changed(self):
        """
        change the frequency interval for plotting spectrogram
        """
        self.plot_spectro(current_time=self.time_mem, force_plot=True)

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
            return {"error": f"File not found: {wav_file_path}"}

        self.media_length = len(self.sound_info) / self.frame_rate

        self.wav_file_path = wav_file_path

        return {"media_length": self.media_length, "frame_rate": self.frame_rate}

    def _compute_spectrogram(
        self,
        x: np.ndarray,
        nfft: int,
        noverlap: int,
        window_type: str,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Compute spectrogram using scipy.signal.spectrogram and return
        frequencies (f), times (t, relative to the chunk start), and Sxx (power).
        """
        # choose window
        if window_type in ("hanning", "hann"):
            window = "hann"
        elif window_type == "hamming":
            window = "hamming"
        elif window_type == "blackmanharris":
            window = "blackmanharris"
        else:
            window = "hann"

        # scipy.signal.spectrogram: nperseg = NFFT, noverlap as provided
        f, t, Sxx = signal.spectrogram(
            x,
            fs=self.frame_rate,
            window=window,
            nperseg=nfft,
            noverlap=noverlap,
            mode="psd",
            scaling="density",
            detrend=False,
        )
        # Sxx shape: (freq_bins, time_bins)
        return f, t, Sxx

    def plot_spectro(self, current_time: float | None, force_plot: bool = False, window_title: str = "") -> tuple[float, bool] | None:
        # (keep the beginning of your existing method: caching, retrieving config params, early returns)
        if not force_plot and current_time == self.time_mem:
            return
        if window_title:
            self.setWindowTitle(window_title)
        self.time_mem = current_time
        self.ax.clear()

        window_type = self.config_param.get(cfg.SPECTROGRAM_WINDOW_TYPE, cfg.SPECTROGRAM_DEFAULT_WINDOW_TYPE)
        nfft = int(self.config_param.get(cfg.SPECTROGRAM_NFFT, cfg.SPECTROGRAM_DEFAULT_NFFT))
        noverlap = int(self.config_param.get(cfg.SPECTROGRAM_NOVERLAP, cfg.SPECTROGRAM_DEFAULT_NOVERLAP))
        use_vrange = self.config_param.get(cfg.SPECTROGRAM_USE_VMIN_VMAX, cfg.SPECTROGRAM_USE_VMIN_VMAX_DEFAULT)
        vmin = self.config_param.get(cfg.SPECTROGRAM_VMIN, cfg.SPECTROGRAM_DEFAULT_VMIN) if use_vrange else None
        vmax = self.config_param.get(cfg.SPECTROGRAM_VMAX, cfg.SPECTROGRAM_DEFAULT_VMAX) if use_vrange else None

        if current_time is None:
            return

        # compute chunk start index and slice
        half = self.interval / 2.0
        start_time = max(0.0, current_time - half)
        end_time = min(self.media_length, current_time + half)

        # compute sample indices
        i0 = int(round(start_time * self.frame_rate))
        i1 = int(round(end_time * self.frame_rate))
        chunk = self.sound_info[i0:i1]

        if chunk.size == 0:
            return

        # compute spectrogram
        f, t_rel, Sxx = self._compute_spectrogram(chunk, nfft=nfft, noverlap=noverlap, window_type=window_type)

        # convert t_rel (relative to chunk start) to absolute times
        t_abs = t_rel + start_time

        # mask frequency range if user set sb_freq_min/max
        fmin = self.sb_freq_min.value()
        fmax = self.sb_freq_max.value()
        freq_mask = (f >= fmin) & (f <= fmax)
        if not freq_mask.any():
            # nothing to show in freq range
            return

        f_show = f[freq_mask]
        Sxx_show = Sxx[freq_mask, :]

        # convert power to dB for better dynamic range (optional)
        # add a tiny epsilon to avoid log(0)
        Sxx_db = 10.0 * np.log10(Sxx_show + 1e-20)

        # plotting with pcolormesh: need 2D grid edges
        # create extents using midpoints for pcolormesh edges
        t_edges = np.concatenate(
            [
                t_abs - 0.5 * np.diff(np.concatenate(([t_abs[0] - (t_abs[1] - t_abs[0])], t_abs))).astype(float),
                [t_abs[-1] + 0.5 * (t_abs[-1] - t_abs[-2] if len(t_abs) > 1 else 1.0)],
            ]
        )
        f_edges = np.concatenate(
            [
                f_show - 0.5 * np.diff(np.concatenate(([f_show[0] - (f_show[1] - f_show[0])], f_show))).astype(float),
                [f_show[-1] + 0.5 * (f_show[-1] - f_show[-2] if len(f_show) > 1 else 1.0)],
            ]
        )

        # simpler way: use pcolormesh with meshgrid of t_abs and f_show:
        T, F = np.meshgrid(t_abs, f_show)

        pcm = self.ax.pcolormesh(
            T,
            F,
            Sxx_db,
            shading="auto",
            cmap=self.spectro_color_map,
            vmin=vmin,
            vmax=vmax,
        )

        # set limits and cursor
        self.ax.set_xlim(start_time, end_time)
        self.ax.set_ylim(fmin, fmax)

        # draw cursor at current_time (absolute)
        # if the cursor is inside current plotting window
        if start_time <= current_time <= end_time:
            self.ax.axvline(x=current_time, color=self.cursor_color, linestyle="-")

        # colorbar optional (can be toggled)
        # self.figure.colorbar(pcm, ax=self.ax, format="%+2.0f dB")

        # TICKS: use data-driven ticks from t_abs
        # Major locator: at most N major ticks
        # self.ax.xaxis.set_major_locator(mticker.MaxNLocator(nbins=8, prune="both"))
        self.ax.xaxis.set_major_locator(mticker.MultipleLocator(0.5))

        # Minor ticks: 2 minor ticks between majors
        self.ax.xaxis.set_minor_locator(mticker.AutoMinorLocator(5))
        self.ax.tick_params(axis="x", which="minor", length=3)

        # Format x-axis labels to show one decimal second (or mm:ss if you prefer)
        def fmt_seconds(x, pos):
            # x is absolute time in seconds; show rounded seconds with one decimal
            return f"{x:.1f}"

        self.ax.xaxis.set_major_formatter(mticker.FuncFormatter(fmt_seconds))

        # draw canvas
        self.canvas.draw()
