import wave

import numpy as np
import pyqtgraph as pg
from PySide6.QtCore import QEvent, Qt, Signal
from PySide6.QtGui import QCloseEvent
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from . import config as cfg


class Plot_waveform_RT(QWidget):
    # Send keypress events to mainwindow
    sendEvent = Signal(QEvent)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Waveform")

        self.hidden: bool = False

        self.interval = 60  # visualization window (seconds)
        self.time_mem = -1

        self.cursor_color: str = cfg.REALTIME_PLOT_CURSOR_COLOR

        # ---- PyQtGraph setup ----
        pg.setConfigOptions(antialias=False)

        self.plot_widget = pg.PlotWidget()
        self.plot_widget.setBackground(None)
        self.plot_widget.showGrid(x=True, y=False, alpha=0.25)
        self.plot_widget.setLabel("bottom", "Time", units="s")

        # Performance-oriented options (good for ~5 FPS)
        self.plot_widget.setClipToView(True)
        self.plot_widget.setDownsampling(mode="peak")  # let pyqtgraph handle decimation
        self.plot_widget.setAutoVisible(y=True)

        # Curve item (updated with setData)
        self.curve = self.plot_widget.plot([], [], pen=pg.mkPen(width=1))

        # Cursor line (absolute time)
        self.cursor_line = pg.InfiniteLine(
            angle=90,
            movable=False,
            pen=pg.mkPen(self.cursor_color, width=1),
        )
        self.plot_widget.addItem(self.cursor_line)
        self.cursor_line.hide()

        layout = QVBoxLayout()
        layout.addWidget(self.plot_widget)

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

        self._x_axis = self.plot_widget.getAxis("bottom")

        # Storage
        self.sound_info = np.array([], dtype=np.int16)
        self.frame_rate = 0
        self.media_length = 0.0
        self.waveform_max = 1.0
        self.wav_file_path = ""

    def closeEvent(self, event: QCloseEvent):
        self.hidden = True
        event.accept()

    def eventFilter(self, receiver, event):
        """
        Forward keypress events to the main window.
        """
        if event.type() == QEvent.Type.KeyPress:
            self.sendEvent.emit(event)
            return True
        return False

    def get_wav_info(self, wav_file: str):
        """
        Read a WAV file and return (signal, frame_rate).
        """
        try:
            wav = wave.open(wav_file, "r")
            frames = wav.readframes(-1)
            signal = np.frombuffer(frames, dtype=np.int16)
            frame_rate = wav.getframerate()
            wav.close()
            return signal, frame_rate
        except Exception:
            return np.array([]), 0

    def load_wav(self, wav_file_path: str) -> dict:
        """
        Load a WAV file into memory.
        Returns a dict with either "error" or ("media_length", "frame_rate").
        """
        try:
            self.sound_info, self.frame_rate = self.get_wav_info(wav_file_path)
            if not self.frame_rate:
                return {"error": f"unknown format for file {wav_file_path}"}
        except FileNotFoundError:
            return {"error": "File not found: {}".format(wav_file_path)}

        self.media_length = len(self.sound_info) / self.frame_rate
        self.wav_file_path = wav_file_path
        self.waveform_max = float(np.max(np.abs(self.sound_info))) if self.sound_info.size else 1.0

        return {"media_length": self.media_length, "frame_rate": self.frame_rate}

    def time_interval_changed(self, action: int) -> None:
        """
        Increase/decrease the plotted time window by 5 seconds.
        """
        if action == -1 and self.interval <= 5:
            return
        self.interval += 5 * action
        self.plot_waveform(current_time=self.time_mem, force_plot=True)

    def _nice_step(self, raw_step: float) -> float:
        """
        Round a step to a 'nice' value: 1, 2, 5 * 10^k.
        """
        if raw_step <= 0:
            return 0.5
        exp = np.floor(np.log10(raw_step))
        base = raw_step / (10**exp)
        if base <= 1:
            nice = 1
        elif base <= 2:
            nice = 2
        elif base <= 5:
            nice = 5
        else:
            nice = 10
        return float(nice * (10**exp))

    def _estimate_label_px(self, decimals: int) -> int:
        """
        Rough estimate of tick label width in pixels.
        Fast heuristic to avoid calling font metrics at ~5 FPS.
        """
        # Conservative worst-case like '12345.67'
        chars = 6 + (1 if decimals > 0 else 0) + decimals
        px_per_char = 7
        return chars * px_per_char

    def _set_x_ticks_auto(self, start_time: float, end_time: float):
        """
        Set X ticks with an adaptive step to reduce label overlap.
        """
        if end_time <= start_time:
            return

        axis_width_px = int(self._x_axis.width())
        if axis_width_px <= 0:
            axis_width_px = 600

        span = float(end_time - start_time)
        if span <= 0:
            return

        # Choose label precision based on visible span
        if span <= 2:
            decimals = 2
        elif span <= 20:
            decimals = 1
        else:
            decimals = 0

        label_px = self._estimate_label_px(decimals)
        min_spacing_px = label_px + 12  # padding between labels

        px_per_sec = axis_width_px / span
        raw_step = min_spacing_px / max(px_per_sec, 1e-9)
        step = self._nice_step(raw_step)

        first = np.ceil(start_time / step) * step
        ticks = np.arange(first, end_time + 1e-9, step)

        fmt = f"{{:.{decimals}f}}"
        major = [(float(t), fmt.format(t)) for t in ticks]
        self._x_axis.setTicks([major])

    def plot_waveform(self, current_time: float | None, force_plot: bool = False, window_title: str = "") -> None:
        """
        Plot the waveform centered on current_time (absolute seconds).
        No manual downsampling: pyqtgraph handles decimation/clipping.
        Called ~5 times per second.
        """
        if not force_plot and current_time == self.time_mem:
            return

        if window_title:
            self.setWindowTitle(window_title)

        self.time_mem = current_time

        if current_time is None or self.sound_info.size == 0 or self.frame_rate <= 0:
            self.curve.setData([], [])
            self.cursor_line.hide()
            return

        half = self.interval / 2.0
        start_time = max(0.0, current_time - half)
        end_time = min(self.media_length, current_time + half)

        i0 = int(round(start_time * self.frame_rate))
        i1 = int(round(end_time * self.frame_rate))
        i0 = max(0, min(i0, len(self.sound_info)))
        i1 = max(0, min(i1, len(self.sound_info)))

        chunk = self.sound_info[i0:i1]
        if chunk.size == 0:
            self.curve.setData([], [])
            self.cursor_line.hide()
            return

        # Build absolute time axis without linspace (faster, fewer temporaries)
        n = chunk.shape[0]
        x = (np.arange(n, dtype=np.float32) / self.frame_rate) + np.float32(start_time)
        y = chunk.astype(np.float32, copy=False)

        # Fast update
        self.curve.setData(x, y)

        # Keep view stable and predictable
        self.plot_widget.setXRange(start_time, end_time, padding=0.0)
        self.plot_widget.setYRange(-self.waveform_max, self.waveform_max, padding=0.05)

        # Cursor (absolute time)
        if start_time <= current_time <= end_time:
            self.cursor_line.setValue(float(current_time))
            self.cursor_line.show()
        else:
            self.cursor_line.hide()

        # Adaptive major ticks to reduce overlap
        self._set_x_ticks_auto(start_time, end_time)
