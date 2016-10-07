#!/usr/bin/env python3.4

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
"""

try:
    from PyQt5.QtCore import *
    from PyQt5.QtWidgets import *
except:
    from PyQt4.QtCore import *
    from PyQt4.QtGui import *

import math
import re
import subprocess
import urllib.parse
import sys
import os
import logging
from config import *

from decimal import *
import math


def behavior2color(behavior, behaviors):
    """
    return color for behavior
    """
    return PLOT_BEHAVIORS_COLORS[behaviors.index(behavior)]


def replace_spaces(l):
    return [x.replace(" ", "_") for x in l]


def bestTimeUnit(t: int) -> str:
    """
    Return time in best format

    Keyword argument:
    t -- time (in seconds)
    """
    unit = "s"
    if t >=  60:
        t = t / 60
        unit = "min"
    if t > 60:
        t = t / 60
        unit = "h"
    return t, unit


def intfloatstr(s):
    """
    convert str in int or float or return str
    """

    try:
        val = int(s)
        return val
    except:
        try:
            val = float(s)
            return "{:0.3f}".format(val)
        except:
            return s


def distance(p1, p2):
    """
    distance between 2 points
    """
    x1, y1 = p1
    x2, y2 = p2
    return ((x1 - x2)**2 + (y1 - y2)**2)**0.5

def angle(p1, p2, p3):
    """
    angle between 3 points (p1 must be the vertex)
    return angle in degree
    """
    return math.acos( (distance(p1,p2)**2 + distance(p1,p3)**2 - distance(p2,p3)**2) / (2 * distance(p1,p2) * distance(p1,p3)) )/math.pi*180

def polygon_area(poly):
    """
    area of polygon
    from http://www.mathopenref.com/coordpolygonarea.html
    """
    tot = 0
    for p in range(len(poly)):
        x1, y1 = poly[p]
        n = (p + 1) % len(poly)
        x2, y2 = poly[n]
        tot += x1 * y2 - x2 * y1

    return abs(tot / 2)


def hashfile(fileName, hasher, blocksize=65536):
    """
    return hash of file content
    """
    with open(fileName,'rb') as afile:
        buf = afile.read(blocksize)
        while len(buf) > 0:
            hasher.update(buf)
            buf = afile.read(blocksize)
    return hasher.hexdigest()


def url2path(url):
    """
    convert URL in local path name
    under windows, check if path name begin with /
    """

    path = urllib.parse.unquote(urllib.parse.urlparse(url).path)
    # check / for windows
    if sys.platform.startswith('win') and path.startswith('/'):
        path = path[1:]
    return path

def float2decimal(f):
    return Decimal(str(f))


def time2seconds(time):
    '''
    convert hh:mm:ss.s to number of seconds (decimal)
    '''
    flagNeg = '-' in time
    time = time.replace("-", "")

    tsplit= time.split(":")

    h, m, s = int( tsplit[0] ), int( tsplit[1] ), Decimal( tsplit[2] )

    if flagNeg:
        return Decimal(-(h * 3600 + m * 60 + s))
    else:
        return Decimal(h * 3600 + m * 60 + s)


def seconds2time(sec):
    """
    convert seconds to hh:mm:ss.sss format
    """
    flagNeg = sec < 0
    sec = abs(sec)

    hours = 0

    minutes = int(sec / 60)
    if minutes >= 60:
        hours = int(minutes /60)
        minutes = minutes % 60

    secs = sec - hours*3600 - minutes * 60
    ssecs = "%06.3f" % secs

    return  "%s%02d:%02d:%s" % ('-' * flagNeg, hours, minutes, ssecs )



def safeFileName(s):
    '''replace characters not allowed in file name by _'''
    fileName = s
    notAllowedChars = ['/','\\']
    for char in notAllowedChars:
        fileName = fileName.replace(char, '_')

    return fileName

def eol2space(s):
    """
    replace EOL char by space for all platforms
    """
    return s.replace('\r\n',' ').replace('\n',' ').replace('\r',' ' )


def test_ffmpeg_path(FFmpegPath):
    """
    test if ffmpeg has valid path
    """

    out, error = subprocess.Popen('"{0}" -version'.format(FFmpegPath) ,stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True ).communicate()
    logging.debug("test ffmpeg path output: {}".format(out))
    logging.debug("test ffmpeg path error: {}".format(error))

    if (b'avconv' in out) or (b'the Libav developers' in error):
        return False, 'Please use FFmpeg from https://www.ffmpeg.org in place of FFmpeg from Libav project.'

    if (b'ffmpeg version' not in out) and (b'ffmpeg version' not in error):
        return False, "FFmpeg is required but it was not found...<br>See https://www.ffmpeg.org"

    return True, ""


def playWithVLC(fileName):
    '''
    play media in filename and return out, fps and has_vout (number of video)
    '''

    import vlc
    import time
    instance = vlc.Instance()
    mediaplayer = instance.media_player_new()
    media = instance.media_new(fileName)
    mediaplayer.set_media(media)
    media.parse()
    mediaplayer.play()
    global out
    global fps
    out, fps, result = '', 0, None
    while True:
        if mediaplayer.get_state() == vlc.State.Playing:
            break
        if mediaplayer.get_state() == vlc.State.Ended:
            result = 'media error'
            break
        time.sleep(3)

    if result:
        out = result
    else:
        out = media.get_duration()
    fps = mediaplayer.get_fps()
    nvout = mediaplayer.has_vout()
    mediaplayer.stop()

    return out, fps, nvout

def check_ffmpeg_path():
    """
    check ffmpeg path
    """

    if os.path.isfile(sys.path[0]):  # pyinstaller
        syspath = os.path.dirname(sys.path[0])
    else:
        syspath = sys.path[0]

    if sys.platform.startswith("linux") or sys.platform.startswith("darwin"):

        r = False
        if os.path.exists( os.path.abspath(os.path.join(syspath, os.pardir )) + "/FFmpeg/ffmpeg"):
            ffmpeg_bin = os.path.abspath(os.path.join(syspath, os.pardir )) + "/FFmpeg/ffmpeg"
            r, msg = test_ffmpeg_path(ffmpeg_bin)
            if r:
                return ffmpeg_bin

        # check if ffmpeg in same directory than boris.py
        if os.path.exists(syspath + "/ffmpeg"):
            ffmpeg_bin = syspath + "/ffmpeg"
            r, msg = test_ffmpeg_path(ffmpeg_bin)
            if r:
               return ffmpeg_bin

        # check for ffmpeg in system path
        ffmpeg_bin = "ffmpeg"
        r, msg = test_ffmpeg_path(ffmpeg_bin)
        if r:
            return ffmpeg_bin
        else:
            logging.critical("FFmpeg is not available")
            QMessageBox.critical(None, programName, msg, QMessageBox.Ok | QMessageBox.Default, QMessageBox.NoButton)
            return False

    if sys.platform.startswith("win"):

        r = False
        if os.path.exists(os.path.abspath(os.path.join(syspath, os.pardir)) + "\\FFmpeg\\ffmpeg.exe"):
            ffmpeg_bin = os.path.abspath(os.path.join(syspath, os.pardir )) + "\\FFmpeg\\ffmpeg.exe"
            r, msg = test_ffmpeg_path( ffmpeg_bin)
            if r:
                return ffmpeg_bin

        if os.path.exists(syspath + "\\ffmpeg.exe"):
            ffmpeg_bin = syspath + "\\ffmpeg.exe"
            r, msg = test_ffmpeg_path( ffmpeg_bin)
            if r:
                return ffmpeg_bin
            else:
                logging.critical("FFmpeg is not available")
                QMessageBox.critical(None, programName, "FFmpeg is not available.<br>Go to http://www.ffmpeg.org to download it", QMessageBox.Ok | QMessageBox.Default, QMessageBox.NoButton)
                return False

    return False


def accurate_media_analysis(ffmpeg_bin, fileName):
    """
    analyse frame rate and video duration with ffmpeg

    return:
    total number of frames
    duration in ms (for compatibility)
    duration in s
    frame per second
    hasVideo: boolean
    hasAudio: boolean
    """

    if sys.platform.startswith("win"):
        cmdOutput = 'NUL'
    else:
        cmdOutput = '/dev/null'

    command2 = '"{0}" -i "{1}" > {2}'.format(ffmpeg_bin, fileName, cmdOutput)

    p = subprocess.Popen(command2, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)

    duration, fps, hasVideo, hasAudio  = 0, 0, False, False
    try:
        error = p.communicate()[1].decode('utf-8')
    except:
        return int(fps * duration), duration*1000, duration, fps, hasVideo, hasAudio

    rows = error.split("\n")

    # video duration
    try:
        for r in rows:
            if 'Duration' in r:
                duration = time2seconds(r.split('Duration: ')[1].split(',')[0].strip())
                break
    except:
        duration = 0

    # fps
    fps = 0
    try:
        for r in rows:
            if ' fps,' in r:
                re_results = re.search(', (.{1,5}) fps,', r, re.IGNORECASE)
                if re_results:
                    fps = Decimal(re_results.group(1).strip())
                    break
    except:
        fps = 0

    # check for video stream
    hasVideo = False
    try:
        for r in rows:
            if 'Stream #' in r and 'Video:' in r:
                hasVideo = True
                break
    except:
        hasVideo = None

    # check for audio stream
    hasAudio = False
    try:
        for r in rows:
            if 'Stream #' in r and 'Audio:' in r:
                hasAudio = True
                break
    except:
        hasAudio = None


    # video nframe and time
    '''
    nframe = 0
    time_ = 0
    print(rows)
    try:
        for rowIdx in range(len(rows) - 1, 0, -1):
            if 'frame=' in rows[rowIdx]:
                print( rows[rowIdx] )
                re_results1 = re.search('frame=(.*)fps=', rows[rowIdx], re.IGNORECASE)
                if re_results1:
                    nframe = int(re_results1.group(1).strip())
                    print('nframe',nframe)
                re_results2 = re.search('time=(.*)bitrate=', rows[rowIdx], re.IGNORECASE)
                if re_results2:
                    time_ = time2seconds(re_results2.group(1).strip()) *1000
                break

    except:
        nframe = 0
        time_ = 0
    '''

    return int(fps * duration), duration*1000, duration, fps, hasVideo, hasAudio

class ThreadSignal(QObject):
    sig = pyqtSignal(int, float, float, float, bool, bool, str, str, str)

class Process(QThread):
    """
    process for accurate video analysis
    """
    def __init__(self, parent = None):
        QThread.__init__(self, parent)
        self.filePath = ''
        self.ffmpeg_bin = ''
        self.fileContentMD5 = ''
        self.nPlayer = ''
        self.filePath = ''
        self.signal = ThreadSignal()

    def run(self):
        nframe, videoTime, videoDuration, fps, hasVideo, hasAudio = accurate_media_analysis( self.ffmpeg_bin, self.filePath )
        self.signal.sig.emit(nframe, videoTime, videoDuration, fps,  hasVideo, hasAudio, self.fileContentMD5, self.nPlayer, self.filePath)
