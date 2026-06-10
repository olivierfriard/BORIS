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

import numpy as np
import parselmouth
import pyqtgraph as pg
from PySide6.QtCore import QEvent, Qt, Signal
from PySide6.QtGui import QCloseEvent, QColor
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QSpinBox,
    QVBoxLayout,
    QWidget,
)

from . import config as cfg


def _spectral_window_shape(window_type: str) -> parselmouth.SpectralAnalysisWindowShape:
    """
    Translate BORIS spectrogram preferences to Praat/Parselmouth window shapes.
    """
    window_type = window_type.lower()
    if window_type in ("hanning", "hann"):
        return parselmouth.SpectralAnalysisWindowShape.HANNING
    if window_type == "hamming":
        return parselmouth.SpectralAnalysisWindowShape.HAMMING
    return parselmouth.SpectralAnalysisWindowShape.HANNING


def _spectrogram_parameters(nfft: int, noverlap: int, frame_rate: float) -> tuple[float, float, float]:
    """
    Convert the existing NFFT/noverlap settings to Praat spectrogram parameters.
    """
    nfft = max(2, int(nfft))
    noverlap = min(max(0, int(noverlap)), nfft - 1)
    frame_rate = float(frame_rate)

    window_length = nfft / frame_rate
    time_step = (nfft - noverlap) / frame_rate
    frequency_step = frame_rate / nfft
    return window_length, time_step, frequency_step


class Plot_spectrogram_RT(QWidget):
    # send keypress event to mainwindow
    sendEvent = Signal(QEvent)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Spectrogram")

        # Optional: avoid OpenGL glitches with other GPU widgets (e.g. mpv vo=gpu)
        pg.setConfigOptions(useOpenGL=False)

        self.hidden: bool = False

        self.interval = 10  # interval of visualization (in seconds)
        self.time_mem = -1

        self.cursor_color = cfg.REALTIME_PLOT_CURSOR_COLOR

        # ---- PyQtGraph widgets/items ----
        self.plot = pg.PlotWidget()
        self.plot.setLabel("bottom", "Time", units="s")
        self.plot.setLabel("left", "Frequency", units="Hz")
        self.plot.showGrid(x=True, y=True, alpha=0.2)
        self.plot.setMouseEnabled(x=False, y=False)
        self.img = pg.ImageItem()
        self.plot.addItem(self.img)

        # Playhead cursor
        self.playhead = pg.InfiniteLine(pos=0, angle=90, movable=False, pen=pg.mkPen(self._qcolor(self.cursor_color)))
        self.plot.addItem(self.playhead)

        # Colormap (viridis-like)
        cmap = pg.colormap.get("viridis")
        self.img.setLookupTable(cmap.getLookupTable(0.0, 1.0, 256))

        # Layout
        layout = QVBoxLayout()
        layout.addWidget(self.plot)

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

        # runtime state
        self.sound_info = np.array([], dtype=np.int16)
        self.sound = None
        self.frame_rate = 0
        self.media_length = 0.0
        self.wav_file_path = ""
        self.config_param = {}

        # cache last levels to keep visualization stable
        self._fixed_levels = None  # (lo, hi)

    def closeEvent(self, event: QCloseEvent):
        self.hidden = True
        # Accept close
        event.accept()

    @staticmethod
    def _qcolor(color) -> QColor:
        """
        Accepts config cursor color formats:
        - QColor
        - "#RRGGBB"
        - (r,g,b) or (r,g,b,a)
        - named colors
        """
        if isinstance(color, QColor):
            return color
        try:
            if isinstance(color, (tuple, list)) and len(color) in (3, 4):
                return QColor(*color)
            if isinstance(color, str):
                return QColor(color)
        except Exception:
            pass
        return QColor("red")

    def eventFilter(self, receiver, event):
        """
        send event (if keypress) to main window
        """
        if event.type() == QEvent.KeyPress:
            self.sendEvent.emit(event)
            return True
        return False

    def get_wav_info(self, wav_file: str) -> tuple[np.ndarray, int]:
        """
        read wav file and extract information
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
        """
        try:
            sound = parselmouth.Sound(wav_file_path)
            self.sound = sound.convert_to_mono() if sound.n_channels > 1 else sound
            self.sound_info = np.asarray(self.sound.values[0], dtype=np.float64)
            self.frame_rate = int(round(float(self.sound.sampling_frequency)))
        except FileNotFoundError:
            return {"error": f"File not found: {wav_file_path}"}
        except Exception:
            self.sound = None
            self.sound_info = np.array([])
            self.frame_rate = 0
            return {"error": f"unknown format for file {wav_file_path}"}

        self.media_length = float(self.sound.duration)
        self.wav_file_path = wav_file_path
        self._fixed_levels = None

        # reasonable defaults for frequency boxes
        if self.sb_freq_max.value() == 0:
            self.sb_freq_max.setValue(min(12000, int(self.frame_rate / 2)))

        return {"media_length": self.media_length, "frame_rate": self.frame_rate}

    def _compute_spectrogram(
        self,
        start_time: float,
        end_time: float,
        nfft: int,
        noverlap: int,
        window_type: str,
        maximum_frequency: float,
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """
        Compute a Praat spectrogram and return frequencies, times relative to
        start_time, and power values shaped as (freq_bins, time_bins).
        """
        if self.sound is None:
            return np.array([]), np.array([]), np.array([[]])
        if end_time <= start_time:
            return np.array([]), np.array([]), np.array([[]])

        window_length, time_step, frequency_step = _spectrogram_parameters(nfft, noverlap, self.frame_rate)
        try:
            sound_part = self.sound.extract_part(from_time=start_time, to_time=end_time, preserve_times=False)
            spectrogram = sound_part.to_spectrogram(
                window_length=window_length,
                maximum_frequency=maximum_frequency,
                time_step=time_step,
                frequency_step=frequency_step,
                window_shape=_spectral_window_shape(window_type),
            )
        except Exception:
            return np.array([]), np.array([]), np.array([[]])

        return (
            np.asarray(spectrogram.ys(), dtype=np.float64),
            np.asarray(spectrogram.xs(), dtype=np.float64),
            np.asarray(spectrogram.values, dtype=np.float64),
        )

    def plot_spectro(
        self,
        current_time: float | None,
        force_plot: bool = False,
        window_title: str = "",
    ) -> tuple[float, bool] | None:
        """
        Plot spectrogram (PyQtGraph)
        """
        if not force_plot and current_time == self.time_mem:
            return
        if window_title:
            self.setWindowTitle(window_title)
        self.time_mem = current_time

        if current_time is None:
            return
        if self.frame_rate <= 0 or self.sound is None or self.sound_info.size == 0:
            return

        window_type = self.config_param.get(cfg.SPECTROGRAM_WINDOW_TYPE, cfg.SPECTROGRAM_DEFAULT_WINDOW_TYPE)
        nfft = int(self.config_param.get(cfg.SPECTROGRAM_NFFT, cfg.SPECTROGRAM_DEFAULT_NFFT))
        noverlap = int(self.config_param.get(cfg.SPECTROGRAM_NOVERLAP, cfg.SPECTROGRAM_DEFAULT_NOVERLAP))

        use_vrange = self.config_param.get(cfg.SPECTROGRAM_USE_VMIN_VMAX, cfg.SPECTROGRAM_USE_VMIN_VMAX_DEFAULT)
        vmin = self.config_param.get(cfg.SPECTROGRAM_VMIN, cfg.SPECTROGRAM_DEFAULT_VMIN) if use_vrange else None
        vmax = self.config_param.get(cfg.SPECTROGRAM_VMAX, cfg.SPECTROGRAM_DEFAULT_VMAX) if use_vrange else None

        # compute chunk [start_time, end_time]
        half = self.interval / 2.0
        start_time = max(0.0, float(current_time) - half)
        end_time = min(self.media_length, float(current_time) + half)

        # frequency mask from UI
        fmin = self.sb_freq_min.value()
        fmax = self.sb_freq_max.value()
        if fmax <= fmin:
            return

        maximum_frequency = min(float(fmax), self.frame_rate / 2.0)

        # spectrogram on chunk
        f, t_rel, Sxx = self._compute_spectrogram(
            start_time,
            end_time,
            nfft=nfft,
            noverlap=noverlap,
            window_type=window_type,
            maximum_frequency=maximum_frequency,
        )
        if t_rel.size == 0 or f.size == 0 or Sxx.size == 0:
            return

        # absolute time axis
        t_abs = t_rel + start_time

        freq_mask = (f >= fmin) & (f <= fmax)
        if not freq_mask.any():
            return

        f_show = f[freq_mask]
        Sxx_show = Sxx[freq_mask, :]

        # dB
        Sxx_db = 10.0 * np.log10(Sxx_show + 1e-20)  # power->dB
        Sxx_db = np.asarray(Sxx_db, dtype=np.float32)

        # --- levels (stabilize image) ---
        if use_vrange and (vmin is not None) and (vmax is not None):
            levels = (float(vmin), float(vmax))
            self._fixed_levels = levels
        else:
            # keep a stable mapping: compute once, then reuse
            if self._fixed_levels is None:
                lo, hi = np.percentile(Sxx_db, [5, 99.5])
                if not np.isfinite(lo) or not np.isfinite(hi) or hi <= lo:
                    lo, hi = float(np.nanmin(Sxx_db)), float(np.nanmax(Sxx_db))
                    if hi <= lo:
                        hi = lo + 1.0
                self._fixed_levels = (float(lo), float(hi))
            levels = self._fixed_levels

        # --- image mapping in real coordinates (sec, Hz) ---
        # pg.ImageItem expects array shaped (x, y) visually, but here we control rect so it’s fine.
        # We'll display with rows=freq, cols=time, and setRect accordingly.
        self.img.setImage(Sxx_db.T, levels=levels, autoLevels=False)

        t0 = float(t_abs[0])
        t1 = float(t_abs[-1])
        f0 = float(f_show[0])
        f1 = float(f_show[-1])
        w = max(1e-9, t1 - t0)
        h = max(1e-9, f1 - f0)
        self.img.setRect(pg.QtCore.QRectF(t0, f0, w, h))

        # view limits
        self.plot.setXRange(start_time, end_time, padding=0.0)
        self.plot.setYRange(fmin, fmax, padding=0.0)

        # playhead
        self.playhead.setPos(float(current_time))

        # ticks: you can customize; simplest is default.
        # If you want 0.5s ticks like matplotlib:
        ax = self.plot.getAxis("bottom")
        ax.setTickSpacing(major=0.5, minor=0.1)
