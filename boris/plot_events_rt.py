"""
plot waveform in real time
"""


import matplotlib
matplotlib.use("Qt5Agg")
#import matplotlib.ticker as mticker
import numpy as np
from PyQt5.QtWidgets import (QWidget, QVBoxLayout)
from PyQt5.QtCore import pyqtSignal, QEvent
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas

from matplotlib.figure import Figure


class Plot_events_RT(QWidget):

    # send keypress event to mainwindow
    sendEvent = pyqtSignal(QEvent)

    def __init__(self):
        super().__init__()

        self.interval = 60  # interval of visualization (in seconds)
        self.time_mem = -1

        self.events_mem = {"init": 0}

        self.cursor_color = "red"

        self.figure = Figure()
        self.ax = self.figure.add_subplot(1, 1, 1)

        self.canvas = FigureCanvas(self.figure)
        layout = QVBoxLayout()

        layout.addWidget(self.canvas)
        self.setLayout(layout)


    def aggregate_events(self, events, start, end) -> dict:
        """
        aggregate state events
        take consideration of subject and modifiers

        return dict


        AltGr + p -> þ
        """

        try:
            mem_behav = {}
            intervals_behav = {}

            for event in events:
                intervals_behav[f"{event[1]}þ{event[2]}þ{event[3]}"] = [(0,0)]

            for event in events:

                time_, subject, code, modifier = event[:4]

                # check if code is state
                if code in self.state_events_list:

                    if f"{subject}þ{code}þ{modifier}" in mem_behav and mem_behav[f"{subject}þ{code}þ{modifier}"]:
                        #stop interval

                        # check if event is in interval start-end
                        if (start <= mem_behav[f"{subject}þ{code}þ{modifier}"] <= end) \
                            or (start <= time_ <= end) \
                            or (mem_behav[f"{subject}þ{code}þ{modifier}"] <= start and time_ > end):
                                intervals_behav[f"{subject}þ{code}þ{modifier}"].append((float(mem_behav[f"{subject}þ{code}þ{modifier}"]), float(time_)))
                        mem_behav[f"{subject}þ{code}þ{modifier}"] = 0
                    else:
                        # start interval
                        mem_behav[f"{subject}þ{code}þ{modifier}"] = time_

            return intervals_behav

        except Exception:
            raise
            return {"error": ""}


    def plot_events(self, current_time: float):
        """
        plot events centered on the current time

        Args:
            current_time (float): time for displaying events
        """

        self.events = self.aggregate_events(self.events_list,
                                               current_time - self.interval / 2,
                                               current_time + self.interval / 2)

        if current_time == self.time_mem:
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

