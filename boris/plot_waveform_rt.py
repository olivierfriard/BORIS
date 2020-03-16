"""
BORIS
Behavioral Observation Research Interactive Software
Copyright 2012-2020 Olivier Friard


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
matplotlib.use("Qt5Agg")
import numpy as np
from PyQt5.QtWidgets import *
from PyQt5.QtCore import pyqtSignal, QEvent
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

Y_MIN = 0
Y_MAX = 20000
VMIN = -40

class Plot_waveform_RT(QWidget):

    # send keypress event to mainwindow
    sendEvent = pyqtSignal(QEvent)

    def get_wav_info(self, wav_file: str):
        """
        read wav file and extract information
        """
        try:
            wav = wave.open(wav_file, "r")
            frames = wav.readframes(-1)
            signal = np.fromstring(frames, "Int16")
            frame_rate = wav.getframerate()
            wav.close()
            return signal, frame_rate
        except Exception:
            return np.array([]), 0

    def __init__(self):
        super().__init__()

        self.interval = 60 # interval of visualization (in seconds)
        self.time_mem = -1

        self.cursor_color = "red"

        self.figure = Figure()

        self.canvas = FigureCanvas(self.figure)
        layout = QVBoxLayout()

        layout.addWidget(self.canvas)
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

        return {"media_length": self.media_length,
                "frame_rate": self.frame_rate}


    def plot_waveform(self, current_time: float):
        """
        plot sound waveform centered on the current time

        Args:
            current_time (float): time for displaying waveform
        """

        if current_time == self.time_mem:
            return

        self.time_mem = current_time

        ax = self.figure.add_subplot(1, 1, 1)

        ax.clear()

        # start
        if current_time <= self.interval / 2:

            '''
            Pxx, freqs, bins, im = ax.specgram(self.sound_info[: int((self.interval) * self.frame_rate)],
                                               mode = 'psd' ,
                                               NFFT=1024,
                                               Fs=self.frame_rate,
                                               noverlap=900,
                                               vmin=VMIN)
            '''

            time_ = np.linspace(0, len(self.sound_info[: int((self.interval) * self.frame_rate)]) / self.frame_rate, num=len(self.sound_info[: int((self.interval) * self.frame_rate)]))
            ax.plot(time_, self.sound_info[: int((self.interval) * self.frame_rate)])

            ax.set_xlim( current_time - self.interval / 2  , current_time + self.interval / 2)

            #ax.set_ylim(Y_MIN, Y_MAX)

            # cursor
            ax.axvline(x=current_time, color=self.cursor_color, linestyle="-")


        elif current_time >= self.media_length - self.interval / 2:

            i = int(round(len(self.sound_info) - (self.interval * self.frame_rate), 0))

            '''
            Pxx, freqs, bins, im = ax.specgram(self.sound_info[i : ],
                                               mode = "psd",
                                               NFFT=1024,
                                               Fs=self.frame_rate,
                                               noverlap=900,
                                               vmin=VMIN)
            '''

            time_ = np.linspace(0, len(self.sound_info[i : ])/self.frame_rate, num=len(self.sound_info[i : ]))
            ax.plot(time_, self.sound_info[i : ])

            lim1 = current_time - (self.media_length - self.interval / 2)
            lim2 = lim1 + self.interval

            ax.set_xlim( lim1  , lim2)

            #ax.set_ylim(Y_MIN, Y_MAX)

            ax.set_xticklabels([str(round(w + self.media_length - self.interval, 1)) for w in ax.get_xticks()])

            # cursor
            ax.axvline(x=lim1 + self.interval / 2, color=self.cursor_color, linestyle="-")

        # middle
        else:

            start = (current_time - self.interval/2)* self.frame_rate
            end = (current_time + self.interval/2)* self.frame_rate

            '''
            Pxx, freqs, bins, im = ax.specgram(self.sound_info[int(round((current_time - self.interval/2) * self.frame_rate, 0)):
                                                               int(round((current_time + self.interval/2) * self.frame_rate, 0))],
                                           mode = 'psd' ,
                                           NFFT=1024,
                                           Fs=self.frame_rate,
                                           noverlap=900,
                                               vmin=VMIN)
            '''
            time_ = np.linspace(0, len(self.sound_info[int(round((current_time - self.interval/2) * self.frame_rate, 0)):
                                                               int(round((current_time + self.interval/2) * self.frame_rate, 0))])/self.frame_rate, num=len(self.sound_info[int(round((current_time - self.interval/2) * self.frame_rate, 0)):
                                                               int(round((current_time + self.interval/2) * self.frame_rate, 0))]))
            ax.plot(time_, self.sound_info[int(round((current_time - self.interval/2) * self.frame_rate, 0)):
                                                               int(round((current_time + self.interval/2) * self.frame_rate, 0))])

            #ax.set_ylim(Y_MIN, Y_MAX)

            ax.set_xticklabels([str(round(current_time + w - self.interval / 2, 1)) for w in ax.get_xticks()])

            # cursor
            ax.axvline(x=self.interval/2 , color=self.cursor_color, linestyle="-")

        self.figure.subplots_adjust(wspace=0, hspace=0)

        self.canvas.draw()


