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
from matplotlib import pyplot
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

SPECTROGRAM_DYNAMIC_RANGE_DB = 70.0
PRAAT_LIKE_COLOR_MAP = "afmhot"


def _praat_spectrogram_parameters() -> tuple[float, float, float, parselmouth.SpectralAnalysisWindowShape]:
    """
    Return Praat's standard spectrogram parameters.
    """
    return 0.005, 0.002, 20.0, parselmouth.SpectralAnalysisWindowShape.GAUSSIAN


def _spectrogram_levels(spectrogram_db: np.ndarray, fixed_levels: tuple[float, float] | None = None) -> tuple[float, float]:
    """
    Return Praat/Parselmouth-style display levels for a spectrogram in dB.
    """
    if fixed_levels is not None:
        return fixed_levels

    max_db = float(np.nanmax(spectrogram_db))
    if not np.isfinite(max_db):
        return (-SPECTROGRAM_DYNAMIC_RANGE_DB, 0.0)
    return (max_db - SPECTROGRAM_DYNAMIC_RANGE_DB, max_db)


def _lookup_table_from_colormap(color_map, n_colors: int = 256) -> np.ndarray:
    """
    Build a PyQtGraph lookup table from a Matplotlib or PyQtGraph colormap name/object.
    """
    if hasattr(color_map, "getLookupTable"):
        return color_map.getLookupTable(0.0, 1.0, n_colors)

    if hasattr(color_map, "__call__"):
        rgba = color_map(np.linspace(0.0, 1.0, n_colors))
    else:
        rgba = pyplot.get_cmap(str(color_map))(np.linspace(0.0, 1.0, n_colors))

    return np.asarray(rgba[:, :3] * 255, dtype=np.ubyte)


def _apply_pre_emphasis(sound: parselmouth.Sound, enabled: bool) -> parselmouth.Sound:
    """
    Apply Praat pre-emphasis to a sound chunk when requested.
    """
    if enabled:
        sound.pre_emphasize()
    return sound


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
        self.spectro_color_map = pyplot.get_cmap(PRAAT_LIKE_COLOR_MAP)

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

        self._apply_color_map()

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

    def _apply_color_map(self):
        """
        Apply the currently configured color map to the PyQtGraph image item.
        """
        try:
            lookup_table = _lookup_table_from_colormap(self.spectro_color_map)
        except Exception:
            lookup_table = _lookup_table_from_colormap(PRAAT_LIKE_COLOR_MAP)
        self.img.setLookupTable(lookup_table)

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

        window_length, time_step, frequency_step, window_shape = _praat_spectrogram_parameters()
        try:
            sound_part = self.sound.extract_part(from_time=start_time, to_time=end_time, preserve_times=False)
            sound_part = _apply_pre_emphasis(
                sound_part,
                self.config_param.get(cfg.SPECTROGRAM_PRE_EMPHASIZE, cfg.SPECTROGRAM_PRE_EMPHASIZE_DEFAULT),
            )
            spectrogram = sound_part.to_spectrogram(
                window_length=window_length,
                maximum_frequency=maximum_frequency,
                time_step=time_step,
                frequency_step=frequency_step,
                window_shape=window_shape,
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
        self._apply_color_map()

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
            levels = _spectrogram_levels(Sxx_db)

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
