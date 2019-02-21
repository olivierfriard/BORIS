#!/usr/bin/env python3

"""
BORIS
Behavioral Observation Research Interactive Software
Copyright 2012-2019 Olivier Friard

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
except ModuleNotFoundError:
    from PyQt4.QtCore import *
    from PyQt4.QtGui import *

import math
import csv
import re
import subprocess
import hashlib
import urllib.parse
import sys
import os
import logging
import subprocess
from decimal import *
import math
import datetime
import socket
import pathlib
import numpy as np

from config import *


def return_file_header(file_name, row_number=5):
    """
    return file header

    Args:
        file_name (str): path of file
        row_number (int): number of rows to return

    Returns:
        list: first row_number row(s) of file_name
    """
    header = []
    try:
        with open(file_name) as f_in:
            for _ in range(row_number):
                header.append(f_in.readline())
    except Exception:
        return []
    return header


def bytes_to_str(b: bytes) -> str:
    """
    Translate bytes to string.

    Args:
        b (bytes): byte to convert

    Returns:
        str: converted byte
    """

    if isinstance(b, bytes):
        fileSystemEncoding = sys.getfilesystemencoding()
        # hack for PyInstaller
        if fileSystemEncoding is None:
            fileSystemEncoding = "UTF-8"
        return b.decode(fileSystemEncoding)
    else:
        return b

'''
def video_resize_reencode(video_paths: list,
                          horiz_resol: int,
                          ffmpeg_bin: str,
                          quality: int=2000) -> bool:
    """
    resize and recode one or more video with ffmpeg

    Args:
        video_paths (list): list of video paths
        horiz_resol (int): horizontal resolution (in pixels)
        ffmpeg_bin (str): path of ffmpeg program
        quality (int): ffmpeg bitrate

    Returns:
        bool: True
    """

    for video_path in video_paths:
        ffmpeg_command = ('"{ffmpeg_bin}" -y -i "{input_}" '
                          '-vf scale={horiz_resol}:-1 -b:v {quality}k '
                          '"{input_}.re-encoded.{horiz_resol}px.avi" ').format(ffmpeg_bin=ffmpeg_bin,
                                                                               input_=video_path,
                                                                               quality=quality,
                                                                               horiz_resol=horiz_resol)
        p = subprocess.Popen(ffmpeg_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        p.communicate()

    return True
'''


'''
def video_rotate(video_paths: list,
                 rotation_idx: int,
                 ffmpeg_bin: str,
                 quality:int=2000) -> bool:
    """
    rotate a video using ffmpeg at same bitrate (quality)

    Args:
        video_paths (list): list of video paths
        rotation_idx (int): type of rotation: 1 = 90 clockwise, 2 = 90 counter clockwise, 3 = 180
        ffmpeg_bin (str): path of ffmpeg program
        quality (int): ffmpeg bitrate / 1000 (k)
    Returns:
        bool: True

    """
    for video_path in video_paths:

        # check bitrate
        r = accurate_media_analysis(ffmpeg_bin, video_path)
        if "error" not in r and r["bitrate"] != -1:
            quality = r["bitrate"]

        if rotation_idx in [1, 2]:
            ffmpeg_command = ('"{ffmpeg_bin}" -y -i "{input_}" '
                              '-vf "transpose={rotation_idx}" -codec:a copy -b:v {quality}k '
                              '"{input_}.rotated{rotation}.avi" ').format(ffmpeg_bin=ffmpeg_bin,
                                                                          input_=video_path,
                                                                          quality=quality,
                                                                          rotation_idx=rotation_idx,
                                                                          rotation=["", "90", "-90"][rotation_idx]
                                                                          )
        if rotation_idx == 3:  # 180
            ffmpeg_command = ('"{ffmpeg_bin}" -y -i "{input_}" '
                              '-vf "transpose=2,transpose=2" -codec:a copy -b:v {quality}k '
                              '"{input_}.rotated180.avi" ').format(ffmpeg_bin=ffmpeg_bin,
                                                                   input_=video_path,
                                                                   quality=quality)

        p = subprocess.Popen(ffmpeg_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        p.communicate()

    return True
'''

def convert_time_to_decimal(pj: dict) -> dict:
    """
    convert time from float to decimal

    Args:
        pj (dict): BORIS project

    Returns:
        dict: BORIS project
    """

    for obsId in pj[OBSERVATIONS]:
        if "time offset" in pj[OBSERVATIONS][obsId]:
            pj[OBSERVATIONS][obsId]["time offset"] = Decimal(str(pj[OBSERVATIONS][obsId]["time offset"]))
        for idx, event in enumerate(pj[OBSERVATIONS][obsId][EVENTS]):
            pj[OBSERVATIONS][obsId][EVENTS][idx][pj_obs_fields["time"]] = Decimal(
                str(pj[OBSERVATIONS][obsId][EVENTS][idx][pj_obs_fields["time"]]))

    return pj


def file_content_md5(file_name: str) -> str:
    hash_md5 = hashlib.md5()
    try:
        with open(file_name, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    except FileNotFoundError:
        return ""


def txt2np_array(file_name, columns_str, substract_first_value, converters={}, column_converter={}):
    """
    read a txt file (tsv or csv) and return np array with passed columns

    Args:
        file_name (str): path of the file to load in numpy array
        columns_str (str): indexes of columns to be loaded. First columns must be the timestamp. Example: "4,5"
        substract_first_value (str): "True" or "False"
        converters (dict): dictionary containing converters
        column_converter (dict): dcitionary key: column index, value: converter name

    Returns:
        bool: True if data successfullly loaded, False if case of error
        str: error message. Empty if success
        numpy array: data. Empty if not data failed to be loaded

    """
    # check columns
    try:
        columns = [int(x) - 1 for x in columns_str.split(",")]
    except Exception:
        return False, "Problem with columns {}".format(columns_str), np.array([])

    # check converters
    np_converters = {}
    for column_idx in column_converter:
        if column_converter[column_idx] in converters:

            conv_name = column_converter[column_idx]

            function = """def {}(INPUT):\n""".format(conv_name)
            function += """    INPUT = INPUT.decode("utf-8") if isinstance(INPUT, bytes) else INPUT"""
            for line in converters[conv_name]["code"].split("\n"):
                function += "    {}\n".format(line)
            function += """    return OUTPUT"""

            try:
                exec(function)
            except Exception:
                return False, "error in converter: {}".format(sys.exc_info()[1]), np.array([])

            np_converters[column_idx - 1] = locals()[conv_name]

        else:
            return False, "converter {} not found".format(converters_param[column_idx]), np.array([])

    # snif txt file
    try:
        with open(file_name) as csvfile:
            buff = csvfile.read(1024)
            snif = csv.Sniffer()
            dialect = snif.sniff(buff)
            has_header = snif.has_header(buff)
    except Exception:
        return False, "{}".format(sys.exc_info()[1]), np.array([])

    try:
        data = np.loadtxt(file_name,
                          delimiter=dialect.delimiter,
                          usecols=columns,
                          skiprows=has_header,
                          converters=np_converters)
    except Exception:
        return False, "{}".format(sys.exc_info()[1]), np.array([])

    # check if first value must be substracted
    if substract_first_value == "True":
        data[:, 0] -= data[:, 0][0]

    return True, "", data


def versiontuple(version_str: str) -> tuple:
    """Convert version from text to tuple

    Args:
        version_str (str): version

    Returns:
        tuple: version in tuple format (for comparison)
    """
    return tuple(map(int, (version_str.split("."))))


def state_behavior_codes(ethogram):
    """
    behavior codes defined as STATE event

    Args:
        ethogram (dict): ethogram dictionary

    Returns:
        list: list of behavior codes defined as STATE event

    """
    return [ethogram[x][BEHAVIOR_CODE] for x in ethogram if "STATE" in ethogram[x][TYPE].upper()]


def get_current_states_by_subject(state_behaviors_codes: list,
                                  events: list,
                                  subjects: dict,
                                  time: Decimal) -> dict:
    """
    get current states for subjects at given time (modifiers are not returned)
    Args:
        state_behaviors_codes (list): list of behavior codes defined as STATE event
        events (list): list of events
        subjects (dict): dictionary of subjects
        time (Decimal): time

    Returns:
        dict: current states by subject. dict of list
    """
    current_states = {}
    for idx in subjects:
        current_states[idx] = []
        for sbc in state_behaviors_codes:
            if len([x[EVENT_BEHAVIOR_FIELD_IDX] for x in events
                    if x[EVENT_SUBJECT_FIELD_IDX] == subjects[idx]["name"]
                    and x[EVENT_BEHAVIOR_FIELD_IDX] == sbc
                    and x[EVENT_TIME_FIELD_IDX] <= time]) % 2:  # test if odd
                current_states[idx].append(sbc)

    return current_states


def get_current_points_by_subject(point_behaviors_codes: list,
                                  events: list,
                                  subjects: dict,
                                  time: Decimal,
                                  tolerance: Decimal) -> dict:
    """
    get near point events for subjects at given time
    Args:
        point_behaviors_codes (list): list of behavior codes defined as POINT event
        events (list): list of events
        subjects (dict): dictionary of subjects
        time (Decimal): time (s)
        tolerance (Decimal): tolerance (s)

    Returns:
        dict: current states by subject. dict of list
    """
    current_points = {}
    for idx in subjects:
        current_points[idx] = []
        for sbc in point_behaviors_codes:
            events = [[x[EVENT_BEHAVIOR_FIELD_IDX], x[EVENT_MODIFIER_FIELD_IDX]] for x in events
                      if x[EVENT_SUBJECT_FIELD_IDX] == subjects[idx]["name"]
                      and x[EVENT_BEHAVIOR_FIELD_IDX] == sbc
                      and abs(x[EVENT_TIME_FIELD_IDX] - time) <= tolerance]

            for event in events:
                current_points[idx].append(event)

    return current_points


def get_ip_address():
    """Get current IP address

    Args:

    Returns:
        str: IP address
    """
    s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
    s.connect(("8.8.8.8", 80))
    return s.getsockname()[0]


def check_txt_file(file_name: str) -> dict:
    """
    Extract parameters of txt file (test for tsv csv)

    Args:
        filename (str): path of file to be analyzed

    Returns:
        dict: {"homogeneous": True or False,
               "fields_number": number of fields,
               "separator": separator char
              }
    """
    try:
        # snif txt file
        with open(file_name) as csvfile:
            buff = csvfile.read(1024)
            snif = csv.Sniffer()
            dialect = snif.sniff(buff)
            has_header = snif.has_header(buff)
            logging.debug("dialect.delimiter: {}".format(dialect.delimiter))

        csv.register_dialect("dialect", dialect)
        rows_len = []
        with open(file_name, "r") as f:
            reader = csv.reader(f, dialect="dialect")
            for row in reader:
                logging.debug("row: {}".format(row))
                if not row:
                    continue
                if len(row) not in rows_len:
                    rows_len.append(len(row))
                    if len(rows_len) > 1:
                        break

        # test if file empty
        if not len(rows_len):
            return {"error": "The file is empty"}

        if len(rows_len) == 1 and rows_len[0] >= 2:
            return {"homogeneous": True, "fields number": rows_len[0], "separator": dialect.delimiter}

        if len(rows_len) > 1:
            return {"homogeneous": False}
        else:
            return {"homogeneous": True, "fields number": rows_len[0], "separator": dialect.delimiter}
    except Exception:
        return {"error": str(sys.exc_info()[1])}


def extract_wav(ffmpeg_bin: str, media_file_path: str, tmp_dir: str) -> str:
    """
    extract wav from media file and save file in tmp_dir

    Args:
        media_file_path (str): media file path
        tmp_dir (str): temporary dir where to save wav file

    Returns:
        str: wav file path or "" if error
    """

    '''
    wav_file_path = "{tmp_dir}{sep}{mediaBaseName}.wav".format(tmp_dir=tmp_dir,
                                                               sep=os.sep,
                                                               mediaBaseName=os.path.basename(media_file_path))
    '''

    wav_file_path = pathlib.Path(tmp_dir) / pathlib.Path(media_file_path + ".wav").name

    # if os.path.isfile(wav_file_path):
    if wav_file_path.is_file():
        return str(wav_file_path)
    else:
        p = subprocess.Popen('"{ffmpeg_bin}" -i "{media_file_path}" -y -ac 1 -vn "{wav_file_path}"'.format(ffmpeg_bin=ffmpeg_bin,
                                                                                                           media_file_path=media_file_path,
                                                                                                           wav_file_path=wav_file_path),
                             stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE,
                             shell=True)
        out, error = p.communicate()
        out, error = out.decode("utf-8"), error.decode("utf-8")

        if "does not contain any stream" not in error:
            if wav_file_path.is_file():
                return str(wav_file_path)
            return ""
        else:
            return ""


'''
def extract_frames_old(ffmpeg_bin: str,
                   start_frame: int,
                   second: float,
                   current_media_path,
                   fps,
                   imageDir,
                   md5_media_path,
                   extension,
                   frame_resize,
                   number_of_seconds):
    """
    extract frames from media file and save them in imageDir directory

    Args:
        ffmpeg_bin (str): path for ffmpeg
        start_frame (int): extract frames from frame
        second (float): second to begin extraction of frames
        currentMedia (str): path for current media
        fps (float): number of frame by second
        imageDir (str): path of dir where to save frames
        md5_media_path (str): md5 of file name content
        extension (str): image format
        frame_resize (int): horizontal resolution of frame
        number_of_seconds (int): number of seconds to extract

    """

    if not os.path.isfile("{imageDir}{sep}BORIS@{md5_media_path}_{frame:08}.{extension}".format(
            imageDir=imageDir,
            sep=os.sep,
            md5_media_path=md5_media_path,
            frame=start_frame + 1,
            extension=extension)):

        ffmpeg_command = ('"{ffmpeg_bin}" -ss {second:.3f} '
                          '-loglevel quiet '
                          '-i "{current_media_path}" '
                          '-start_number {start_number} '
                          '-vframes {number_of_frames} '
                          '-vf scale={frame_resize}:-1 '
                          '"{imageDir}{sep}BORIS@{md5_media_path}_%08d.{extension}"').format(
                              ffmpeg_bin=ffmpeg_bin,
                              second=second,
                              current_media_path=current_media_path,
                              start_number=start_frame,
                              number_of_frames=number_of_seconds * fps,
                              imageDir=imageDir,
                              sep=os.sep,
                              md5_media_path=md5_media_path,
                              extension=extension,
                              frame_resize=frame_resize)

        logging.debug("ffmpeg command: {}".format(ffmpeg_command))

        p = subprocess.Popen(ffmpeg_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, error = p.communicate()
        out, error = out.decode("utf-8"), error.decode("utf-8")

        if error:
            logging.debug("ffmpeg error: {}".format(error))

    # check before frame
    if start_frame - 1 > 0 and not os.path.isfile("{imageDir}{sep}BORIS@{md5_media_path}_{frame:08}.{extension}".format(imageDir=imageDir,
                          sep=os.sep,
                          md5_media_path=md5_media_path,
                          frame=start_frame - 1,
                          extension=extension)):

        if round(start_frame - fps * number_of_seconds) < 1:
            start_frame_before = 1
            second_before = 0
        else:
            start_frame_before = round(start_frame - fps * number_of_seconds)
            second_before = second - number_of_seconds

        ffmpeg_command = ('"{ffmpeg_bin}" -ss {second} '
                          "-loglevel quiet "
                          '-i "{current_media_path}" '
                          '-start_number {start_number} '
                          '-vframes {number_of_frames} '
                          '-vf scale={frame_resize}:-1 '
                          '"{imageDir}{sep}BORIS@{md5_media_path}_%08d.{extension}"').format(
            ffmpeg_bin=ffmpeg_bin,
            second=second_before,
            current_media_path=current_media_path,
            start_number=start_frame_before,
            number_of_frames=number_of_seconds * fps + 2,  # +2 to obtain current frame
            imageDir=imageDir,
            sep=os.sep,
            md5_media_path=md5_media_path,
            extension=extension,
            frame_resize=frame_resize)

        logging.debug("ffmpeg command (before): {}".format(ffmpeg_command))

        p = subprocess.Popen(ffmpeg_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, error = p.communicate()
        out, error = out.decode("utf-8"), error.decode("utf-8")

        if error:
            logging.debug("ffmpeg error: {}".format(error))
'''

def extract_frames(ffmpeg_bin: str,
                   start_frame: int,
                   second: float,
                   current_media_path,
                   fps,
                   imageDir,
                   md5_media_path,
                   extension,
                   frame_resize,
                   number_of_seconds):
    """
    extract frames from media file and save them in imageDir directory

    Args:
        ffmpeg_bin (str): path for ffmpeg
        start_frame (int): extract frames from frame
        second (float): second to begin extraction of frames
        currentMedia (str): path for current media
        fps (float): number of frame by second
        imageDir (str): path of dir where to save frames
        md5_media_path (str): md5 of file name content
        extension (str): image format
        frame_resize (int): horizontal resolution of frame
        number_of_seconds (int): number of seconds to extract

    """

    '''
    if not os.path.isfile(f"{imageDir}{sep}BORIS@{md5_media_path}_{frame:08}.{extension}".format(
            imageDir=imageDir,
            sep=os.sep,
            md5_media_path=md5_media_path,
            frame=start_frame + 1,
            extension=extension)):
    '''

    ffmpeg_command = (f'"{ffmpeg_bin}" -ss {second:.3f} '
                      '-loglevel quiet '
                      f'-i "{current_media_path}" '
                      f'-start_number {start_frame} '
                      f'-vframes {number_of_seconds * fps} '
                      f'-vf scale={frame_resize}:-1 '
                      f'"{imageDir}{os.sep}BORIS@{md5_media_path}_%08d.{extension}"')
    '''
                       .format(
                          ffmpeg_bin=ffmpeg_bin,
                          second=second,
                          current_media_path=current_media_path,
                          start_number=start_frame,
                          number_of_frames=number_of_seconds * fps,
                          imageDir=imageDir,
                          sep=os.sep,
                          md5_media_path=md5_media_path,
                          extension=extension,
                          frame_resize=frame_resize)
    '''

    logging.debug(f"ffmpeg command: {ffmpeg_command}")

    p = subprocess.Popen(ffmpeg_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, error = p.communicate()
    out, error = out.decode("utf-8"), error.decode("utf-8")

    if error:
        logging.debug(f"ffmpeg error: {error}")

    # check before frame
    if start_frame - 1 > 0 and not os.path.isfile(f"{imageDir}{os.sep}BORIS@{md5_media_path}_{start_frame - 1:08}.{extension}"):

        start_frame_before = max(1, round(start_frame - fps * number_of_seconds))
        second_before = (start_frame_before - 1) / fps

        number_of_frames = start_frame - start_frame_before

        logging.debug(f"start_frame_before {start_frame_before} second_before {second_before} number_of_frames  {number_of_frames}")

        ffmpeg_command = (f'"{ffmpeg_bin}" -ss {second_before} '
                          "-loglevel quiet "
                          f'-i "{current_media_path}" '
                          f'-start_number {start_frame_before} '
                          f'-vframes {number_of_frames} '
                          f'-vf scale={frame_resize}:-1 '
                          f'"{imageDir}{os.sep}BORIS@{md5_media_path}_%08d.{extension}"')

        logging.debug("ffmpeg command (before): {}".format(ffmpeg_command))

        p = subprocess.Popen(ffmpeg_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, error = p.communicate()
        out, error = out.decode("utf-8"), error.decode("utf-8")

        if error:
            logging.debug("ffmpeg error: {}".format(error))




def decimal_default(obj):
    if isinstance(obj, Decimal):
        return float(obj)
    raise TypeError


def complete(l: list, max_: int):
    """
    complete list with empty string ("") until len = max

    Args:
        l (list): list to complete
        max_ (int): number of items to reach

    Returns:
        list: list completed to max_ items with empty string ("")
    """
    while len(l) < max_:
        l.append("")
    return l


def datetime_iso8601(dt):
    """
    current date time in ISO8601 format

    Returns:
        str: date time in ISO8601 format
    """
    return dt.isoformat().replace("T", " ").split(".")[0]

'''
def behavior2color(behavior, behaviors):
    """
    return color for behavior
    """
    return PLOT_BEHAVIORS_COLORS[behaviors.index(behavior)]
'''

'''
def replace_spaces(l):
    """
    replace sapces with _ in strings contained in list
    """

    return [x.replace(" ", "_") for x in l]
'''

def sorted_keys(d: dict) -> list:
    """
    return list of sorted keys of provided dictionary

    Args:
        d (dict): dictionary

    Returns:
         list: dictionary keys sorted numerically
    """
    return [str(x) for x in sorted([int(x) for x in d.keys()])]


'''
def bestTimeUnit(t: float):
    """
    Return time in best format

    Args:
        t (float): time in seconds

    Returns:


    """
    unit = "s"
    if t >= 60:
        t = t / 60
        unit = "min"
    if t > 60:
        t = t / 60
        unit = "h"
    return t, unit
'''

def intfloatstr(s: str):
    """
    convert str in int or float or return str
    """

    try:
        return int(s)
    except Exception:
        try:
            return "{:0.3f}".format(float(s))
        except Exception:
            return s


def distance(p1, p2):
    """
    euclidean distance between 2 points
    """
    x1, y1 = p1
    x2, y2 = p2
    return ((x1 - x2) ** 2 + (y1 - y2) ** 2) ** 0.5


def angle(p1, p2, p3):
    """
    angle between 3 points (p1 must be the vertex)
    return angle in degree

    Args:
        p1 (tuple): vertex
        p2 (tuple): side 1
        p3 (tuple): side 2

    Returns:
        float: angle between side1 - vertex - side2
    """
    return math.acos(
        (distance(p1, p2) ** 2 + distance(p1, p3)**2 - distance(p2, p3)**2) / (2 * distance(p1, p2) * distance(p1, p3))) / math.pi * 180


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

'''
def hashfile(fileName, hasher, blocksize=65536):
    """
    return hash of file content
    """
    with open(fileName, 'rb') as afile:
        buf = afile.read(blocksize)
        while len(buf) > 0:
            hasher.update(buf)
            buf = afile.read(blocksize)
    return hasher.hexdigest()
'''

def url2path(url):
    """
    convert URL in local path name
    under windows, check if path name begin with /
    """

    path = urllib.parse.unquote(urllib.parse.urlparse(url).path)
    # check / for windows
    if sys.platform.startswith("win") and path.startswith("/"):
        path = path[1:]
    return path


def float2decimal(f):
    """
    return decimal value
    """
    return Decimal(str(f))


def time2seconds(time: str) -> Decimal:
    """
    convert hh:mm:ss.s to number of seconds (decimal)

    Args
        time (str): time (hh:mm:ss.zzz format)

    Returns:
        Decimal: time in seconds
    """
    flagNeg = '-' in time
    time = time.replace("-", "")

    tsplit = time.split(":")

    h, m, s = int(tsplit[0]), int(tsplit[1]), Decimal(tsplit[2])

    if flagNeg:
        return Decimal(- (h * 3600 + m * 60 + s))
    else:
        return Decimal(h * 3600 + m * 60 + s)


def seconds2time(sec):
    """
    convert seconds to hh:mm:ss.sss format

    Args:
        sec (Decimal): time in seconds
    Returns:
        str: time in format hh:mm:ss
    """
    flagNeg = sec < 0
    sec = abs(sec)

    hours = 0

    minutes = int(sec / 60)
    if minutes >= 60:
        hours = int(minutes / 60)
        minutes = minutes % 60

    secs = sec - hours * 3600 - minutes * 60
    ssecs = "%06.3f" % secs

    return "%s%02d:%02d:%s" % ('-' * flagNeg, hours, minutes, ssecs)


def safeFileName(s):
    """
    replace characters not allowed in file name by _
    """
    fileName = s
    notAllowedChars = ["/", "\\", ":", "*", "?", '"', "<", ">", "|"]
    for char in notAllowedChars:
        fileName = fileName.replace(char, "_")

    return fileName


def eol2space(s: str) -> str:
    """
    replace EOL char by space for all platforms

    Args:
        s (str): string to be converted

    Returns:
        str: string where /rn /r /n are converted in space
    """
    return s.replace('\r\n', ' ').replace('\n', ' ').replace('\r', ' ')


def test_ffmpeg_path(FFmpegPath):
    """
    test if ffmpeg has valid path

    Args:
        FFmpegPath (str): ffmepg path to test

    Returns:
        bool: True: path found
        str: message
    """

    out, error = subprocess.Popen('"{0}" -version'.format(FFmpegPath),
                                  stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE, shell=True).communicate()
    logging.debug("test ffmpeg path output: {}".format(out))
    logging.debug("test ffmpeg path error: {}".format(error))

    if (b'avconv' in out) or (b'the Libav developers' in error):
        return False, 'Please use FFmpeg from https://www.ffmpeg.org in place of FFmpeg from Libav project.'

    if (b'ffmpeg version' not in out) and (b'ffmpeg version' not in error):
        return False, "FFmpeg is required but it was not found...<br>See https://www.ffmpeg.org"

    return True, ""


'''
def playWithVLC(fileName):
    """
    play media in filename and return out, fps and has_vout (number of video)
    """

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
'''

def check_ffmpeg_path():
    """
    check for ffmpeg path

    Returns:
        bool: True if ffmpeg path found else False
        str: if bool True returns ffmpegpath else returns error message
    """

    if os.path.isfile(sys.path[0]):  # pyinstaller
        syspath = os.path.dirname(sys.path[0])
    else:
        syspath = sys.path[0]

    if sys.platform.startswith("linux") or sys.platform.startswith("darwin"):

        r = False
        if os.path.exists(os.path.abspath(os.path.join(syspath, os.pardir)) + "/FFmpeg/ffmpeg"):
            ffmpeg_bin = os.path.abspath(os.path.join(syspath, os.pardir)) + "/FFmpeg/ffmpeg"
            r, msg = test_ffmpeg_path(ffmpeg_bin)
            if r:
                return True, ffmpeg_bin

        # check if ffmpeg in same directory than boris.py
        if os.path.exists(syspath + "/ffmpeg"):
            ffmpeg_bin = syspath + "/ffmpeg"
            r, msg = test_ffmpeg_path(ffmpeg_bin)
            if r:
                return True, ffmpeg_bin

        # check for ffmpeg in system path
        ffmpeg_bin = "ffmpeg"
        r, msg = test_ffmpeg_path(ffmpeg_bin)
        if r:
            return True, ffmpeg_bin
        else:
            logging.critical("FFmpeg is not available")
            return False, "FFmpeg is not available"

    if sys.platform.startswith("win"):

        r = False
        if os.path.exists(os.path.abspath(os.path.join(syspath, os.pardir)) + "\\FFmpeg\\ffmpeg.exe"):
            ffmpeg_bin = os.path.abspath(os.path.join(syspath, os.pardir)) + "\\FFmpeg\\ffmpeg.exe"
            r, msg = test_ffmpeg_path(ffmpeg_bin)
            if r:
                return True, ffmpeg_bin

        if os.path.exists(syspath + "\\ffmpeg.exe"):
            ffmpeg_bin = syspath + "\\ffmpeg.exe"
            r, msg = test_ffmpeg_path(ffmpeg_bin)
            if r:
                return True, ffmpeg_bin
            else:
                logging.critical("FFmpeg is not available")
                return False, "FFmpeg is not available"

    return False, "FFmpeg is not available"


def accurate_media_analysis(ffmpeg_bin, file_name):
    """
    analyse frame rate and video duration with ffmpeg
    Returns parameters: duration, duration_ms, bitrate, frames_number, fps, has_video (True/False), has_audio (True/False)

    Args:
        ffmpeg_bin (str): ffmpeg path
        file_name (str): path of media file

    Returns:
        dict containing keys: duration, duration_ms, frames_number, bitrate, fps, has_video, has_audio

    """

    command = '"{0}" -i "{1}" > {2}'.format(ffmpeg_bin, file_name, "NUL" if sys.platform.startswith("win") else "/dev/null")

    p = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)

    duration, fps, hasVideo, hasAudio, bitrate = 0, 0, False, False, -1
    try:
        error = p.communicate()[1].decode("utf-8")
    except Exception:
        return {"error": "Error reading file"}

    # check for invalid data
    '''
    if "Invalid data found when processing input" in error:
        return {"error": "Invalid data found when processing input"}
    '''

    rows = error.split("\n")

    # video duration
    try:
        for r in rows:
            if "Duration" in r:
                duration = time2seconds(r.split("Duration: ")[1].split(",")[0].strip())
                break
    except Exception:
        duration = 0

    # bitrate
    try:
        for r in rows:
            if "bitrate:" in r:
                re_results = re.search("bitrate: (.{1,10}) kb", r, re.IGNORECASE)
                if re_results:
                    bitrate = int(re_results.group(1).strip())
                break
    except Exception:
        bitrate = -1

    # fps
    fps = 0
    try:
        for r in rows:
            if " fps," in r:
                re_results = re.search(", (.{1,10}) fps,", r, re.IGNORECASE)
                if re_results:
                    fps = Decimal(re_results.group(1).strip())
                    break
    except Exception:
        fps = 0

    # check for video stream
    hasVideo = False
    resolution = None
    try:
        for r in rows:
            if "Stream #" in r and "Video:" in r:
                hasVideo = True
                # get resolution \d{3,5}x\d{3,5}
                re_results = re.search("\d{3,5}x\d{3,5}", r, re.IGNORECASE)
                if re_results:
                    resolution = re_results.group(0)
                break
    except Exception:
        hasVideo = None
        resolution = None

    # check for audio stream
    hasAudio = False
    try:
        for r in rows:
            if "Stream #" in r and "Audio:" in r:
                hasAudio = True
                break
    except Exception:
        hasAudio = None

    if duration == 0 or bitrate == -1:
        return {"error": "This file do not seem to be a media file"}

    return {"frames_number": int(fps * duration),
            "duration_ms": duration * 1000,
            "duration": duration,
            "fps": fps,
            "has_video": hasVideo,
            "has_audio": hasAudio,
            "bitrate": bitrate,
            "resolution": resolution}



def behavior_color(colors_list, idx):
    """
    return color with index corresponding to behavior index

    see BEHAVIORS_PLOT_COLORS list in config.py
    """

    try:
        return colors_list[idx % len(colors_list)]
    except Exception:
        return "darkgray"

'''
class ThreadSignal(QObject):
    sig = pyqtSignal(int, float, float, float, bool, bool, str, str, str)
'''
