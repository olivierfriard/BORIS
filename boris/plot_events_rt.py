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



Plot events in real time
"""

import matplotlib

matplotlib.use("Qt5Agg")

import numpy as np
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel
from PySide6.QtCore import Signal, QEvent, Qt
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas

from matplotlib.figure import Figure

from . import config as cfg

# matplotlib.pyplot.switch_backend("Qt5Agg")


class Plot_events_RT(QWidget):
    # send keypress event to mainwindow
    sendEvent = Signal(QEvent)

    def __init__(self):
        super().__init__()
        self.setWindowTitle("Events plot")

        self.interval = 60  # default interval of visualization (in seconds)
        self.time_mem = -1

        self.events_mem = {"init": 0}

        self.cursor_color = cfg.REALTIME_PLOT_CURSOR_COLOR  # default cursor color
        self.observation_type = cfg.MEDIA
        self.groupby = "behaviors"  # group results by "behaviors" or "modifiers"

        self.figure = Figure()
        self.ax = self.figure.add_subplot(1, 1, 1)

        self.canvas = FigureCanvas(self.figure)

        layout = QVBoxLayout()
        layout.addWidget(self.canvas)

        hlayout1 = QHBoxLayout()
        hlayout1.addWidget(QLabel("Time interval"))
        hlayout1.addWidget(QPushButton("+", self, clicked=lambda: self.time_interval_changed(1), focusPolicy=Qt.NoFocus))
        hlayout1.addWidget(QPushButton("-", self, clicked=lambda: self.time_interval_changed(-1), focusPolicy=Qt.NoFocus))
        self.pb_mode = QPushButton("Include modifiers", self, clicked=self.change_mode, focusPolicy=Qt.NoFocus)
        hlayout1.addWidget(self.pb_mode)
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

    def change_mode(self) -> None:
        """
        Change plot mode
        "behaviors" -> plot behaviors without modifiers
        "modifiers" -> plot behaviors and modifiers
        """

        if self.groupby == "behaviors":
            self.groupby = "modifiers"
            self.pb_mode.setText("Show behaviors w/o modifiers")
        else:
            self.groupby = "behaviors"
            self.pb_mode.setText("Include modifiers")

    def time_interval_changed(self, action: int) -> None:
        """
        change the time interval for events plot

        Args:
            action (int): -1 decrease time interval, +1 increase time interval

        Returns:
            None
        """

        if action == -1 and self.interval <= 5:
            return
        self.interval += 5 * action
        self.plot_events(current_time=self.time_mem, force_plot=True)

    def aggregate_events(self, events: list, start: float, end: float) -> dict:
        """
        aggregate state events
        take consideration of subject and modifiers

        Args:
            events (list): list of events
            start (float): initial value
            end (float): final value

        Returns:
            dict

        """

        def group(subject: str, code: str, modifier: str) -> tuple:
            if self.groupby == "behaviors":
                return (subject, code)
            else:  # with modifiers
                return (subject, code, modifier)

        mem_behav = {}
        intervals_behav = {}

        for event in events:
            intervals_behav[group(event[1], event[2], event[3])] = [(0, 0)]

        for event in events:
            time_, subject, code, modifier = event[:4]
            key = group(subject, code, modifier)

            # check if code is state
            if code in self.state_events_list:
                if key in mem_behav and mem_behav[key] is not None:
                    # stop interval

                    # check if event is in interval start-end
                    if any(
                        (
                            start <= mem_behav[key] <= end,
                            start <= time_ <= end,
                            mem_behav[key] <= start and time_ > end,
                        )
                    ):
                        intervals_behav[key].append((float(mem_behav[key]), float(time_)))
                    mem_behav[key] = None
                else:
                    # start interval
                    mem_behav[key] = time_

            else:  # point event
                if start <= time_ <= end:
                    intervals_behav[key].append((float(time_), float(time_) + self.point_event_plot_duration * 50))  # point event -> 1 s

        # check if intervals are closed
        for k in mem_behav:
            if mem_behav[k] is not None:  # interval open
                if self.observation_type == cfg.LIVE:
                    intervals_behav[k].append((float(mem_behav[k]), float((end + start) / 2)))  # close interval with current time

                elif self.observation_type == cfg.MEDIA:
                    intervals_behav[k].append((float(mem_behav[k]), float(end)))  # close interval with end value

        return intervals_behav

    def plot_events(self, current_time: float, force_plot: bool = False):
        """
        plot events centered on the current time

        Args:
            current_time (float): time for displaying events
            force_plot (bool): force plot even if media paused
        """

        self.events = self.aggregate_events(self.events_list, current_time - self.interval / 2, current_time + self.interval / 2)

        if not force_plot and current_time == self.time_mem:
            return

        self.time_mem = current_time

        if self.events != self.events_mem:
            left, duration = {}, {}
            for k in self.events:
                left[k] = []
                duration[k] = []
                for interv in self.events[k]:
                    left[k].append(interv[0])
                    duration[k].append(interv[1] - interv[0])

            self.behaviors, self.durations, self.lefts, self.colors = [], [], [], []
            for k in self.events:
                if self.groupby == "behaviors":
                    subject_name, bevavior_code = k
                    if subject_name == "":
                        subject_name = "No focal"
                    behav_col = self.behav_color[bevavior_code]
                    self.behaviors.extend([f"{subject_name} - {bevavior_code}"] * len(self.events[k]))
                    self.colors.extend([behav_col] * len(self.events[k]))
                else:  # with modifiers
                    subject_name, bevavior_code, modifier = k
                    behav_col = self.behav_color[bevavior_code]
                    self.behaviors.extend([f"{subject_name} - {bevavior_code} ({modifier})"] * len(self.events[k]))
                    self.colors.extend([behav_col] * len(self.events[k]))

                self.lefts.extend(left[k])
                self.durations.extend(duration[k])

            self.events_mem = self.events

        self.ax.clear()
        self.ax.set_xlim(current_time - self.interval / 2, current_time + self.interval / 2)

        self.ax.axvline(x=current_time, color=self.cursor_color, linestyle="-")

        self.ax.barh(y=np.array(self.behaviors), width=self.durations, left=self.lefts, color=self.colors, height=0.5)

        self.canvas.draw()
        self.figure.canvas.flush_events()
