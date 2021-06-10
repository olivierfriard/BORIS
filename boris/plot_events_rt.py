"""
plot waveform in real time
"""


import matplotlib
matplotlib.use("Qt5Agg")
#import matplotlib.ticker as mticker
import numpy as np
from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel)
from PyQt5.QtCore import pyqtSignal, QEvent
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas

from matplotlib.figure import Figure


class Plot_events_RT(QWidget):

    # send keypress event to mainwindow
    sendEvent = pyqtSignal(QEvent)

    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"Events plot")

        self.interval = 60  # interval of visualization (in seconds)
        self.time_mem = -1

        self.events_mem = {"init": 0}

        self.cursor_color = "red"
        self.groupby = "behaviors"  # group results by "behaviors" or "modifiers"

        self.figure = Figure()
        self.ax = self.figure.add_subplot(1, 1, 1)

        self.canvas = FigureCanvas(self.figure)

        layout = QVBoxLayout()
        layout.addWidget(self.canvas)

        hlayout1 = QHBoxLayout()
        hlayout1.addWidget(QLabel("Time interval"))
        button_time_inc = QPushButton("+", self)
        button_time_inc.clicked.connect(lambda: self.time_interval_changed(1))
        button_time_dec = QPushButton("-", self)
        button_time_dec.clicked.connect(lambda: self.time_interval_changed(-1))
        hlayout1.addWidget(button_time_inc)
        hlayout1.addWidget(button_time_dec)
        layout.addLayout(hlayout1)

        self.setLayout(layout)

        self.installEventFilter(self)


    def eventFilter(self, receiver, event):
        """
        send event (if keypress) to main window
        """
        if(event.type() == QEvent.KeyPress):
            self.sendEvent.emit(event)
            return True
        else:
            return False

    def time_interval_changed(self, action: int):
        """
        change the time interval for events plot

        Args:
            action (int): -1 decrease time interval, +1 increase time interval
        """
        if action == -1 and self.interval <= 5:
            return
        self.interval += (5 * action)
        self.plot_events(current_time=self.time_mem, force_plot=True)


    def aggregate_events(self,
                         events:list,
                         start:float,
                         end:float) -> dict:
        """
        aggregate state events
        take consideration of subject and modifiers

        Args:
            events (list): list of events
            start (float): initial value
            end (float): final value

        Returns:
            dict

        AltGr + p -> þ
        """

        def group(subject, code, modifier):
            if self.groupby == "behaviors":
                return f"{subject}þ{code}"
            else:  # with modifiers
                return f"{subject}þ{code}þ{modifier}"

        try:
            mem_behav = {}
            intervals_behav = {}

            for event in events:
                intervals_behav[group(event[1], event[2], event[3])] = [(0,0)]

            for event in events:

                time_, subject, code, modifier = event[:4]
                key = group(subject, code, modifier)

                # check if code is state
                if code in self.state_events_list:

                    if key in mem_behav and mem_behav[key]:
                        # stop interval

                        # check if event is in interval start-end
                        if (start <= mem_behav[key] <= end) \
                            or (start <= time_ <= end) \
                            or (mem_behav[key] <= start and time_ > end):
                                intervals_behav[key].append((float(mem_behav[key]), float(time_)))
                        mem_behav[key] = 0
                    else:
                        # start interval
                        mem_behav[key] = time_

                else:  # point event

                    if start <= time_ <= end:
                        intervals_behav[key].append((float(time_), float(time_) + self.point_event_plot_duration * 50))  # point event -> 1 s

            # check if intervals are closed
            for k in mem_behav:
                if mem_behav[k]:  # interval open
                    print(f"{k} is open at: {mem_behav[k]}")
                    intervals_behav[k].append((float(mem_behav[k]), float((end + start) / 2)))  # close interval with current time
                    print(f"closed with {float((end + start) / 2)}")

            return intervals_behav

        except Exception:
            raise
            return {"error": ""}


    def plot_events(self, current_time: float, force_plot: bool=False):
        """
        plot events centered on the current time

        Args:
            current_time (float): time for displaying events
            force_plot (bool): force plot even if media paused
        """

        self.events = self.aggregate_events(self.events_list,
                                            current_time - self.interval / 2,
                                            current_time + self.interval / 2
                                            )

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
                    subject_name, bevavior_code = k.split('þ')
                    behav_col = self.behav_color[bevavior_code]
                    self.behaviors.extend([f"{subject_name} - {bevavior_code}"] * len(self.events[k]))
                    self.colors.extend([behav_col] * len(self.events[k]))
                else:  # with modifiers
                    subject_name, bevavior_code, modifier = k.split('þ')
                    behav_col = self.behav_color[bevavior_code]
                    self.behaviors.extend([f"{subject_name} - {bevavior_code} ({modifier})"] * len(self.events[k]))
                    self.colors.extend([behav_col] * len(self.events[k]))

                self.lefts.extend(left[k])
                self.durations.extend(duration[k])

            self.events_mem = self.events

        self.ax.clear()
        self.ax.set_xlim(current_time - self.interval / 2, current_time + self.interval / 2)

        self.ax.axvline(x=current_time, color=self.cursor_color, linestyle="-")

        self.ax.barh(y=np.array(self.behaviors),
                    width=self.durations,
                    left=self.lefts,
                    color=self.colors,
                    height=0.5)

        #self.figure.subplots_adjust(wspace=0, hspace=0)

        self.canvas.draw()
        self.figure.canvas.flush_events()

