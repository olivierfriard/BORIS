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
import math
import re
import subprocess
import urllib.parse
import sys
from PyQt4.QtCore import *
from PyQt4.QtGui import *
from decimal import *


def hashfile(fileName, hasher, blocksize=65536):
    '''
    return hash of file content
    '''
    with open(fileName,'rb') as afile:
        buf = afile.read(blocksize)
        while len(buf) > 0:
            hasher.update(buf)
            buf = afile.read(blocksize)
    return hasher.hexdigest()


def url2path(url):
    '''
    convert URL in local path name
    under windows, check if path name begin with /
    '''

    path = urllib.parse.urlparse(url).path
    # check / for windows
    if sys.platform.startswith('win') and path.startswith('/'):
        path = path[1:]
    return path



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
    '''
    convert seconds to hh:mm:ss.sss format
    '''
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
    '''
    replace EOL char by space for all platforms
    '''
    return s.replace('\r\n',' ').replace('\n',' ').replace('\r',' ' )


def test_ffmpeg_path(FFmpegPath):
    """
    test if ffmpeg has valid path
    """

    out, error = subprocess.Popen('"{0}" -version'.format(FFmpegPath) ,stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True ).communicate()
    out, error = out.decode('utf-8'), error.decode('utf-8')

    if 'avconv' in out:
        return False, 'Please use FFmpeg in place of avconv.\nSee https://www.ffmpeg.org'

    if 'the Libav developers' in error:
        return False, 'Please use FFmpeg from https://www.ffmpeg.org in place of FFmpeg from Libav project.'

    if not 'ffmpeg version' in out and not 'ffmpeg version' in error:
        return False, 'It seems that <b>{}</b> is not the correct FFmpeg program...<br>See https://www.ffmpeg.org'.format(FFmpegPath  )

    return True, ''


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


def accurate_video_analysis(ffmpeg_bin, fileName):
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
    #command2 = '"{0}" -i "{1}" -ss 0 -t 60 -f image2pipe -qscale 31 - > {2}'.format(ffmpeg_bin, fileName, cmdOutput)
    command2 = '"{0}" -i "{1}" > {2}'.format(ffmpeg_bin, fileName, cmdOutput)

    p = subprocess.Popen(command2, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)

    error = p.communicate()[1].decode('utf-8')

    rows = error.split('\r')
    '''print(rows)
    print(len(rows))

    print( rows[0].split("\n") )'''

    # video duration
    duration = 0
    try:
        for r in rows[0].split("\n"):
            if 'Duration' in r:
                duration = time2seconds(r.split('Duration: ')[1].split(',')[0].strip())
                break
    except:
        duration = 0

    # fps
    fps = 0
    try:
        for r in rows[0].split("\n"):
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
        for r in rows[0].split("\n"):
            if 'Stream #' in r and 'Video:' in r:
                hasVideo = True
                break
    except:
        hasVideo = None

    # check for audio stream
    hasAudio = False
    try:
        for r in rows[0].split("\n"):
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
        nframe, videoTime, videoDuration, fps, hasVideo, hasAudio = accurate_video_analysis( self.ffmpeg_bin, self.filePath )
        self.signal.sig.emit(nframe, videoTime, videoDuration, fps,  hasVideo, hasAudio, self.fileContentMD5, self.nPlayer, self.filePath)
