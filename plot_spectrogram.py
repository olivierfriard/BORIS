#!/usr/bin/env python3

"""
BORIS
Behavioral Observation Research Interactive Software
Copyright 2012-2016 Olivier Friard


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


A spectrogram, or sonogram, is a visual representation of the spectrum
of frequencies in a sound.  Horizontal axis represents time, Vertical axis
represents frequency, and color represents amplitude.

remove blank border arount pyplot:
http://stackoverflow.com/questions/11837979/removing-white-space-around-a-saved-image-in-matplotlib

"""

try:
    from PyQt5.QtGui import *
    from PyQt5.QtCore import *
    from PyQt5.QtWidgets import *
except:
    from PyQt4.QtGui import *
    from PyQt4.QtCore import *

import sys
import os
import wave
import subprocess
import multiprocessing
try:
    import numpy as np
    import matplotlib
except:
    pass
import recode_widget


class Spectrogram(QWidget):

    # send keypress event to mainwindow
    sendEvent = pyqtSignal(QEvent)

    memChunk = ''

    def __init__(self, fileName1stChunk, parent = None):

        super(Spectrogram, self).__init__(parent)

        self.pixmap = QPixmap()

        self.pixmap.load(fileName1stChunk)
        self.w, self.h = self.pixmap.width(), self.pixmap.height()

        #self.setGeometry(300, 300, 1000, self.h + 50)

        self.resize(1000, self.h + 50)

        self.setMinimumHeight(self.h + 50)
        self.setMaximumHeight(self.h + 50)

        self.scene = QGraphicsScene(self)
        self.scene.setBackgroundBrush(QColor(0, 0, 0, 255))

        self.scene.setSceneRect(0, 0, 100, 100)

        if QT_VERSION_STR[0] == "4":
            self.line = QGraphicsLineItem(0, 0, 0, self.h, scen =self.scene)
        else:
            self.line = QGraphicsLineItem(0, 0, 0, self.h)

        self.line.setPen(QPen(QColor(0, 0, 255, 255), 2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))
        self.line.setZValue(100.0)
        self.scene.addItem(self.line)

        self.view = QGraphicsView(self.scene)
        #self.view.showMaximized()

        hbox = QHBoxLayout(self)
        hbox.addWidget(self.view)

        self.setWindowTitle("Spectrogram")
        #self.setWindowFlags(Qt.WindowMinimizeButtonHint) # only for Linux

        self.installEventFilter(self)


    def eventFilter(self, receiver, event):
        '''
        send event (if keypress) to main window
        '''
        if(event.type() == QEvent.KeyPress):
            self.sendEvent.emit(event)
            return True
        else:
            return False


def graph_spectrogram(mediaFile, tmp_dir, chunk_size, ffmpeg_bin):

    def extract_wav(mediaFile, tmp_dir):
        """
        extract wav from media file
        """

        wavTmpPath = "{tmp_dir}{sep}{mediaBaseName}.wav".format(tmp_dir=tmp_dir,
                                                                  sep=os.sep,
                                                                  mediaBaseName=os.path.basename(mediaFile))

        if os.path.isfile(wavTmpPath):
            return wavTmpPath
        else:
            p = subprocess.Popen('{ffmpeg_bin} -i "{mediaFile}" -y -ac 1 -vn "{wavTmpPath}"'.format(ffmpeg_bin=ffmpeg_bin,
                                                                                                      mediaFile=mediaFile,
                                                                                                      wavTmpPath=wavTmpPath),
                                                                                                      stdout=subprocess.PIPE,
                                                                                                      stderr=subprocess.PIPE,
                                                                                                      shell=True)
            out, error = p.communicate()
            out, error = out.decode("utf-8"), error.decode("utf-8")

            if not out:
                return wavTmpPath
            else:
                return None


    def get_wav_info(wav_file):

        wav = wave.open(wav_file, "r")
        frames = wav.readframes(-1)
        sound_info = pylab.fromstring(frames, "Int16")
        frame_rate = wav.getframerate()
        wav.close()
        return sound_info, frame_rate

    matplotlib.use("Agg")
    import pylab # do not move. It is important that this line is after the previous one

    fileName1stChunk = ""
    mediaBaseName = os.path.basename( mediaFile )

    wav_file = extract_wav(mediaFile, tmp_dir)
    if not wav_file:
        return None

    sound_info, frame_rate = get_wav_info(wav_file)
    wav_length = round(len(sound_info) / frame_rate, 3)

    i = 0
    while True:

        chunkFileName = "{}.{}-{}.spectrogram.png".format(wav_file, i, i + chunk_size)
        if not os.path.isfile(chunkFileName):

            sound_info_slice = sound_info[i * frame_rate: (i + chunk_size) * frame_rate]

            # complete bitmat spectrogram chunk if shorter than chunk length
            if len(sound_info_slice) / frame_rate < chunk_size:
                concat = np.zeros((chunk_size - len(sound_info_slice) / frame_rate )* frame_rate)
                sound_info_slice = np.concatenate((sound_info_slice, concat))

            pylab.figure(num=None, dpi=100, figsize=(int( len(sound_info_slice)/frame_rate), 1))
            pylab.gca().set_axis_off()
            pylab.margins(0, 0)
            pylab.gca().xaxis.set_major_locator(pylab.NullLocator())
            pylab.gca().yaxis.set_major_locator(pylab.NullLocator())
            #pylab.specgram(sound_info_slice, Fs=frame_rate, cmap=matplotlib.pyplot.get_cmap('Greys'),scale_by_freq=False)
            pylab.specgram(sound_info_slice, Fs=frame_rate, scale_by_freq=False)
            pylab.savefig(chunkFileName, bbox_inches='tight', pad_inches=0)
            pylab.clf()
            pylab.close()

        if not fileName1stChunk:
            fileName1stChunk = chunkFileName

        i += chunk_size
        if i >= wav_length:
            break

    return fileName1stChunk


def create_spectrogram_multiprocessing(mediaFile, tmp_dir, chunk_size, ffmpeg_bin):
    
    process_timer = QTimer()
    
    
    process = multiprocessing.Process(target=graph_spectrogram, args=(mediaFile, tmp_dir, chunk_size, ffmpeg_bin, ))
    process.start()
    
    return process
