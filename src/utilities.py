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


import csv
import datetime
import hashlib
import logging
import math
import os
import pathlib
import re
import socket
import subprocess
import sys
import urllib.parse
import wave
from decimal import *
from shutil import copyfile

import numpy as np
import psutil
from PyQt5.QtCore import *
from PyQt5.QtGui import QImage, QPixmap, qRgb
from PyQt5.QtWidgets import *

from config import *


def error_info(exc_info: tuple) -> tuple:
    """
    return details about error

    Args:
        sys.exc_info() (tuple):

    Returns:
        tuple: error type, error file name, error line number
    """

    exc_type, exc_obj, exc_tb = exc_info
    fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]
    return (exc_obj, fname, exc_tb.tb_lineno)


def return_file_header(file_name: str, row_number: int = 5) -> list:
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


def convert_time_to_decimal(pj: dict) -> dict:
    """
    convert time of project from float to decimal

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
                pj[OBSERVATIONS][obsId][EVENTS][idx][pj_obs_fields["time"]]).quantize(Decimal(".001"))

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


def txt2np_array(file_name: str,
                 columns_str: str,
                 substract_first_value: str,
                 converters={},
                 column_converter={}):
    """
    read a txt file (tsv or csv) and return np array with passed columns

    Args:
        file_name (str): path of the file to load in numpy array
        columns_str (str): indexes of columns to be loaded. First columns must be the timestamp. Example: "4,5"
        substract_first_value (str): "True" or "False"
        converters (dict): dictionary containing converters
        column_converter (dict): dictionary key: column index, value: converter name

    Returns:
        bool: True if data successfullly loaded, False if case of error
        str: error message. Empty if success
        numpy array: data. Empty if not data failed to be loaded

    """

    # check columns
    try:
        columns = [int(x) - 1 for x in columns_str.split(",")]
    except Exception:
        return False, f"Problem with columns {columns_str}", np.array([])

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
                return False, f"error in converter: {sys.exc_info()[1]}", np.array([])

            np_converters[column_idx - 1] = locals()[conv_name]

        else:
            return False, f"converter {converters_param[column_idx]} not found", np.array([])

    # snif txt file
    try:
        with open(file_name) as csvfile:
            buff = csvfile.read(1024)
            snif = csv.Sniffer()
            dialect = snif.sniff(buff)
            has_header = snif.has_header(buff)
    except Exception:
        return False, f"{sys.exc_info()[1]}", np.array([])

    try:
        data = np.loadtxt(file_name,
                          delimiter=dialect.delimiter,
                          usecols=columns,
                          skiprows=has_header,
                          converters=np_converters)
    except Exception:
        return False, f"{sys.exc_info()[1]}", np.array([])

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
    try:
        return tuple(map(int, (version_str.split("."))))
    except Exception:
        return ()


def state_behavior_codes(ethogram: dict) -> list:
    """
    behavior codes defined as STATE event

    Args:
        ethogram (dict): ethogram dictionary

    Returns:
        list: list of behavior codes defined as STATE event

    """
    return [ethogram[x][BEHAVIOR_CODE] for x in ethogram if "STATE" in ethogram[x][TYPE].upper()]


def get_current_states_modifiers_by_subject(state_behaviors_codes: list,
                                            events: list,
                                            subjects: dict,
                                            time: Decimal,
                                            include_modifiers: bool = False) -> dict:
    """
    get current states and modifiers (if requested) for subjects at given time

    Args:
        state_behaviors_codes (list): list of behavior codes defined as STATE event
        events (list): list of events
        subjects (dict): dictionary of subjects
        time (Decimal): time
        include_modifiers (bool): include modifier if True (default: False)

    Returns:
        dict: current states by subject. dict of list
    """
    current_states = {}

    if include_modifiers:
        for idx in subjects:
            current_states[idx] = []
            for sbc in state_behaviors_codes:
                bl = [(x[EVENT_BEHAVIOR_FIELD_IDX], x[EVENT_MODIFIER_FIELD_IDX]) for x in events
                      if x[EVENT_SUBJECT_FIELD_IDX] == subjects[idx][SUBJECT_NAME]
                      and x[EVENT_BEHAVIOR_FIELD_IDX] == sbc
                      and x[EVENT_TIME_FIELD_IDX] <= time]

                if len(bl) % 2:  # test if odd
                    current_states[idx].append(bl[-1][0] + f" ({bl[-1][1]})" * (bl[-1][1] != ""))

    else:
        for idx in subjects:
            current_states[idx] = []
            for sbc in state_behaviors_codes:
                if len([x[EVENT_BEHAVIOR_FIELD_IDX] for x in events
                        if x[EVENT_SUBJECT_FIELD_IDX] == subjects[idx][SUBJECT_NAME]
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

            logging.debug(f"dialect.delimiter: {dialect.delimiter}")

        csv.register_dialect("dialect", dialect)
        rows_len = []
        with open(file_name, "r") as f:
            reader = csv.reader(f, dialect="dialect")
            for row in reader:

                logging.debug(f"row: {row}")

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

    wav_file_path = pathlib.Path(tmp_dir) / pathlib.Path(media_file_path + ".wav").name

    # check if media file is a wav file
    try:
        wav = wave.open(media_file_path, "r")
        wav.close()
        logging.debug(f"{media_file_path} is a WAV file. Copying in the temp directory...")
        copyfile(media_file_path, wav_file_path)
        logging.debug(f"{media_file_path} copied in {wav_file_path}")
        return str(wav_file_path)
    except Exception:
        if wav_file_path.is_file():
            return str(wav_file_path)
        # extract wav file using FFmpeg

        p = subprocess.Popen(f'"{ffmpeg_bin}" -i "{media_file_path}" -y -ac 1 -vn "{wav_file_path}"',
                             stdout=subprocess.PIPE,
                             stderr=subprocess.PIPE,
                             shell=True)
        out, error = p.communicate()
        out, error = out.decode("utf-8"), error.decode("utf-8")
        logging.debug(f"{out}, {error}")

        if "does not contain any stream" not in error:
            if wav_file_path.is_file():
                return str(wav_file_path)
            return ""
        else:
            return ""


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

    ffmpeg_command = (f'"{ffmpeg_bin}" -ss {second:.3f} '
                      '-loglevel quiet '
                      f'-i "{current_media_path}" '
                      f'-start_number {start_frame} '
                      f'-vframes {number_of_seconds * fps} '
                      f'-vf scale={frame_resize}:-1 '
                      f'"{pathlib.Path(imageDir) / pathlib.Path(f"BORIS@{md5_media_path}_%08d.{extension}")}"'
                      )

    logging.debug(f"ffmpeg command: {ffmpeg_command}")

    p = subprocess.Popen(ffmpeg_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, error = p.communicate()
    out, error = out.decode("utf-8"), error.decode("utf-8")

    if error:
        logging.debug(f"ffmpeg error: {error}")

    # check before frame
    if (start_frame - 1 > 0
            and not os.path.isfile(pathlib.Path(imageDir) / pathlib.Path(f"BORIS@{md5_media_path}_{start_frame - 1:08}.{extension}"))):

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
                          # f'"{imageDir}{os.sep}BORIS@{md5_media_path}_%08d.{extension}"'
                          f'"{pathlib.Path(imageDir) / pathlib.Path(f"BORIS@{md5_media_path}_%08d.{extension}")}"'
                          )

        logging.debug(f"ffmpeg command (before): {ffmpeg_command}")

        p = subprocess.Popen(ffmpeg_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
        out, error = p.communicate()
        out, error = out.decode("utf-8"), error.decode("utf-8")

        if error:
            logging.debug(f"ffmpeg error: {error}")


def extract_frames_mem(ffmpeg_bin: str,
                       start_frame: int,
                       second: float,
                       current_media_path,
                       fps: int,
                       resolution: tuple,
                       frame_resize: int,
                       number_of_seconds: int) -> (list, tuple):

    """
    extract frames from media file and return in a list in QPixmap format

    Args:
        ffmpeg_bin (str): path for ffmpeg
        start_frame (int): extract frames from frame
        second (float): second to begin extraction of frames
        current_media_path (str): path for current media
        fps (float): number of frame by second
        resolution (list): resolution (w, h)
        number_of_seconds (int): number of seconds to extract

    Returns:
        list: extracted frames in pixmap format
        tuple: (new horizontal resolution, new vertical resolution
    """

    def toQImage(frame, copy=False):
        gray_color_table = [qRgb(i, i, i) for i in range(256)]
        if frame is None:
            return QImage()

        im = np.asarray(frame)
        if im.dtype == np.uint8:
            if len(im.shape) == 2:
                qim = QImage(im.data, im.shape[1], im.shape[0], im.strides[0], QImage.Format_Indexed8)
                qim.setColorTable(gray_color_table)
                return qim.copy() if copy else qim
            elif len(im.shape) == 3:
                if im.shape[2] == 3:
                    qim = QImage(im.data, im.shape[1], im.shape[0], im.strides[0], QImage.Format_RGB888)
                    return qim.copy() if copy else qim
                elif im.shape[2] == 4:
                    qim = QImage(im.data, im.shape[1], im.shape[0], im.strides[0], QImage.Format_ARGB32)
                    return qim.copy() if copy else qim

    if frame_resize:
        new_h_resolution = frame_resize
        new_v_resolution = round(resolution[1] * (frame_resize / resolution[0]))
    else:
        new_h_resolution, new_v_resolution = resolution

    logging.debug(f"new resolution: {new_h_resolution} x {new_v_resolution}")

    ffmpeg_command = ["ffmpeg", "-loglevel", "info",
                      "-i", current_media_path,
                      "-hide_banner",
                      "-ss", str((start_frame - 1) / fps),
                      "-vframes", str(int(fps * number_of_seconds)),
                      "-s", f"{new_h_resolution}x{new_v_resolution}",
                      "-f", "image2pipe",
                      "-pix_fmt", "rgb24",
                      "-vcodec", "rawvideo", "-",
                      ]
    pipe = subprocess.Popen(ffmpeg_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, bufsize=10**8)

    # print("stderr", self.pipe.stderr)

    frames = []
    for f in range(start_frame, start_frame + int(fps * number_of_seconds)):
        raw_image = pipe.stdout.read(new_h_resolution * new_v_resolution * 3)
        if not len(raw_image):

            logging.debug("frames stream finished")

            return [], ()

        frames.append(QPixmap.fromImage(toQImage(np.fromstring(raw_image, dtype="uint8").reshape((new_v_resolution, new_h_resolution, 3)))))

    return frames, (new_h_resolution, new_v_resolution)


def decimal_default(obj):
    if isinstance(obj, Decimal):
        return float(round(obj, 3))
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
    # l.extend([""] * (max_ - len(l)))
    return l


def datetime_iso8601(dt) -> str:
    """
    current date time in ISO8601 format without milliseconds
    example: 2019-06-13 10:01:02

    Returns:
        str: date time in ISO8601 format
    """
    return dt.isoformat(" ").split(".")[0]


def seconds_of_day(dt) -> Decimal:
    """
    return the number of seconds since start of the day
    """

    return Decimal((dt - datetime.datetime.combine(dt.date(), datetime.time(0))).total_seconds()).quantize(Decimal("0.001"))


def sorted_keys(d: dict) -> list:
    """
    return list of sorted keys of provided dictionary

    Args:
        d (dict): dictionary

    Returns:
         list: dictionary keys sorted numerically
    """
    return [str(x) for x in sorted([int(x) for x in d.keys()])]


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


def rss_memory_used(pid):
    """
    get RSS memory used by process pid

    Args:
        pid (int): process id
    Returns:
        int: RSS memory used by process pid in Mb

    """
    try:
        return round(psutil.Process(pid).memory_info().rss / 1024 / 1024)
    except exception:
        return -1


def rss_memory_percent_used(pid):
    """
    get RSS memory percent used by process pid

    Args:
        pid (int): process id
    Returns:
        float: RSS memory percent used by process pid

    """
    try:
        return psutil.Process(pid).memory_percent(memtype='rss')
    except Exception:
        return -1


def available_memory():
    """
    get available memory on system
    """
    try:
        return psutil.virtual_memory().available
    except Exception:
        return -1

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


def time2seconds(time_: str) -> Decimal:
    """
    convert hh:mm:ss.s to number of seconds (decimal)

    Args
        time (str): time (hh:mm:ss.zzz format)

    Returns:
        Decimal: time in seconds
    """

    try:
        flag_neg = "-" in time_
        time_ = time_.replace("-", "")
        tsplit = time_.split(":")
        h, m, s = int(tsplit[0]), int(tsplit[1]), Decimal(tsplit[2])
        return Decimal(- (h * 3600 + m * 60 + s)) if flag_neg else Decimal(h * 3600 + m * 60 + s)
    except Exception:
        return Decimal("0.000")


def seconds2time(sec):
    """
    convert seconds to hh:mm:ss.sss format

    Args:
        sec (Decimal): time in seconds
    Returns:
        str: time in format hh:mm:ss
    """
    neg_sign = "-" * (sec < 0)
    abs_sec = abs(sec)

    hours = 0

    minutes = int(abs_sec / 60)
    if minutes >= 60:
        hours = int(minutes / 60)
        minutes = minutes % 60

    ssecs = f"{abs_sec - hours * 3600 - minutes * 60:06.3f}"

    return f"{neg_sign}{hours:02}:{minutes:02}:{ssecs}"


def safeFileName(s: str) -> str:
    """
    replace characters not allowed in file name by _
    """
    fileName = s
    notAllowedChars = ["/", "\\", ":", "*", "?", '"', "<", ">", "|", "\n", "\r"]
    for char in notAllowedChars:
        fileName = fileName.replace(char, "_")

    return fileName


def safe_xl_worksheet_title(title: str,
                            output_format: str):
    """
    sanitize the XLS and XLSX worksheet title
    
    Args:
        title (str): title for worksheet
        output_format (str): xls or xlsx
    """
    if output_format in ["xls", "xlsx"]:
        if output_format in ["xls"]:
            title = title[:31]
        for forbidden_char in EXCEL_FORBIDDEN_CHARACTERS:
            title = title.replace(forbidden_char, " ")
    return title


def eol2space(s: str) -> str:
    """
    replace EOL char by space for all platforms

    Args:
        s (str): string to be converted

    Returns:
        str: string where /rn /r /n are converted in space
    """
    return s.replace("\r\n", " ").replace("\n", " ").replace("\r", " ")


def test_ffmpeg_path(FFmpegPath):
    """
    test if ffmpeg has valid path

    Args:
        FFmpegPath (str): ffmepg path to test

    Returns:
        bool: True: path found
        str: message
    """

    out, error = subprocess.Popen(f'"{FFmpegPath}" -version',
                                  stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE, shell=True).communicate()
    logging.debug(f"test ffmpeg path output: {out}")
    logging.debug(f"test ffmpeg path error: {error}")

    if (b'avconv' in out) or (b'the Libav developers' in error):
        return False, 'Please use FFmpeg from https://www.ffmpeg.org in place of FFmpeg from Libav project.'

    if (b'ffmpeg version' not in out) and (b'ffmpeg version' not in error):
        return False, "FFmpeg is required but it was not found...<br>See https://www.ffmpeg.org"

    return True, ""


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

    command = f'"{ffmpeg_bin}" -i "{file_name}" > {"NUL" if sys.platform.startswith("win") else "/dev/null"}'


    '''
    TO BE DELETED 2019-10-04
    command = '"{ffmpeg_bin}" -i "{file_name}" > {null_output}'.format(ffmpeg_bin=ffmpeg_bin,
                                                                       file_name=file_name,
                                                                       null_output="NUL" if sys.platform.startswith("win") else "/dev/null")
    '''

    p = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)

    duration, fps, hasVideo, hasAudio, bitrate = 0, 0, False, False, -1
    try:
        error = p.communicate()[1].decode("utf-8")
    except Exception:
        return {"error": "Error reading file"}

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
