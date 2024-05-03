"""
BORIS
Behavioral Observation Research Interactive Software
Copyright 2012-2024 Olivier Friard

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
import datetime as dt
import hashlib
import json
import logging
import math
import os
import pathlib as pl
import re
import socket
import subprocess
import sys
import urllib.parse
import wave
from decimal import Decimal as dec
from decimal import getcontext, ROUND_DOWN
from shutil import copyfile
from typing import Union, Tuple

import numpy as np
from PyQt5.QtGui import QPixmap, QImage

from PIL.ImageQt import Image

from . import config as cfg

try:
    from . import mpv2 as mpv

    # check if MPV API v. 1
    # is v. 1 use the old version of mpv.py
    try:
        if "libmpv.so.1" in mpv.sofile:
            from . import mpv as mpv
    except AttributeError:
        if "mpv-1.dll" in mpv.dll:
            from . import mpv as mpv

except RuntimeError:  # libmpv found but version too old
    from . import mpv as mpv


def mpv_lib_version() -> Tuple[str, str]:
    """
    Version of MPV library

    Returns:
        str: MPV library version
    """
    mpv_lib_file = None
    if sys.platform.startswith("linux"):
        mpv_lib_file = mpv.sofile
    if sys.platform.startswith("win"):
        mpv_lib_file = mpv.dll

    return (".".join([str(x) for x in mpv._mpv_client_api_version()]), mpv_lib_file)


def python_mpv_script_version() -> str:
    """
    version of python-mpv script
    """
    try:
        return mpv.__version__
    except Exception:
        return "Not found"


def error_info(exc_info: tuple) -> tuple:
    """
    return details about error
    usage: error_info(sys.exc_info())

    Args:
        sys.exc_info() (tuple):

    Returns:
        tuple: error type, error file name, error line number
    """

    exc_type, exc_obj, exc_tb = exc_info
    fname = os.path.split(exc_tb.tb_frame.f_code.co_filename)[1]

    return (f"{exc_type}: {exc_obj}", fname, exc_tb.tb_lineno)


def pil2pixmap(im: Image) -> QPixmap:
    """
    convert PIL image to pixmap
    see https://stackoverflow.com/questions/34697559/pil-image-to-qpixmap-conversion-issue
    """

    if im.mode == "RGB":
        r, g, b = im.split()
        im = Image.merge("RGB", (b, g, r))
    elif im.mode == "RGBA":
        r, g, b, a = im.split()
        im = Image.merge("RGBA", (b, g, r, a))
    elif im.mode == "L":
        im = im.convert("RGBA")

    im2 = im.convert("RGBA")
    data = im2.tobytes("raw", "RGBA")
    qim = QImage(data, im.size[0], im.size[1], QImage.Format_ARGB32)
    pixmap = QPixmap.fromImage(qim)
    return pixmap


def replace_leading_trailing_chars(s: str, old_char: str, new_char: str) -> str:
    """
    replace leading and trailing old_char by new_char

    Args:
        s: string
        old_char: character to be replaced
        new_char: character for replacing

    Returns:
        str: string with characters replaced
    """

    sp = s.partition(s.strip(old_char))

    return f"{sp[0].replace(old_char, new_char)}{sp[1]}{sp[2].replace(old_char, new_char)}"


def return_file_header(file_name: str, row_number: int = 5) -> list:
    """
    return file header

    Args:
        file_name (str): path of file
        row_number (int): number of rows to return

    Returns:
        list: first row_number row(s) of file_name
    """
    header: list = []
    try:
        with open(file_name) as f_in:
            for _ in range(row_number):
                header.append(f_in.readline())
    except Exception:
        return []
    return header


def return_file_header_footer(file_name: str, file_row_number: int = 0, row_number: int = 5) -> Tuple[list, list]:
    """
    return file header and footer

    Args:
        file_name (str): path of file
        file_row_number (int): total rows number of file
        row_number (int): number of rows to return

    Returns:
        list: first row_number row(s) of file_name
    """
    header: list = []
    footer: list = []
    try:
        row_idx: int = 0
        with open(file_name, "rt") as f_in:
            for row in f_in:
                if row_idx < row_number:
                    header.append(row.strip())
                if file_row_number > row_number * 2 and (row_idx >= file_row_number - row_number):
                    footer.append(row.strip())
                row_idx += 1

    except Exception:
        return [], []
    return header, footer


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


def convertTime(time_format: str, sec: Union[float, dec]) -> Union[str, None]:
    """
    convert time in base at the current format (S or HHMMSS)

    Args:
        sec (float): time in seconds

    Returns:
        string: time in base of current format (self.timeFormat S or cfg.HHMMSS)
    """

    if isinstance(sec, dec) and sec.is_nan():
        return cfg.NA

    if time_format == cfg.S:
        return f"{sec:.3f}"

    if time_format == cfg.HHMMSS:
        return seconds2time(sec)

    return None


def smart_time_format(sec: Union[float, dec], time_format: str = cfg.S, cutoff: dec = cfg.SMART_TIME_CUTOFF_DEFAULT) -> str:
    """
    Smart time format
    returns time in seconds if <= cutoff else in HH:MM:SS.ZZZ format
    """
    # cutoff = 0 follows the time format selectd by user
    if cutoff == 0:
        return convertTime(time_format, sec)
    if sec <= cutoff:
        return f"{sec:.3f}"
    else:
        return seconds2time(sec)


def convert_time_to_decimal(pj: dict) -> dict:
    """
    convert time of project from float to decimal

    Args:
        pj (dict): BORIS project

    Returns:
        dict: BORIS project
    """
    for obs_id in pj[cfg.OBSERVATIONS]:
        if cfg.TIME_OFFSET in pj[cfg.OBSERVATIONS][obs_id]:
            if pj[cfg.OBSERVATIONS][obs_id][cfg.TIME_OFFSET] is not None:
                pj[cfg.OBSERVATIONS][obs_id][cfg.TIME_OFFSET] = dec(str(pj[cfg.OBSERVATIONS][obs_id][cfg.TIME_OFFSET]))
            else:
                pj[cfg.OBSERVATIONS][obs_id][cfg.TIME_OFFSET] = dec("0.000")
        for idx, _ in enumerate(pj[cfg.OBSERVATIONS][obs_id][cfg.EVENTS]):
            pj[cfg.OBSERVATIONS][obs_id][cfg.EVENTS][idx][cfg.EVENT_TIME_FIELD_IDX] = dec(
                pj[cfg.OBSERVATIONS][obs_id][cfg.EVENTS][idx][cfg.EVENT_TIME_FIELD_IDX]
            ).quantize(dec(".001"))

    return pj


def count_media_file(media_files: dict) -> int:
    """
    count number of media file for observation
    """
    return sum([len(media_files[idx]) for idx in media_files])


def file_content_md5(file_name: str) -> str:
    """
    returns the MD5 sum of file content
    """
    hash_md5 = hashlib.md5()
    try:
        with open(file_name, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()
    except FileNotFoundError:
        return ""


def txt2np_array(
    file_name: str, columns_str: str, substract_first_value: str, converters=None, column_converter=None
) -> Tuple[bool, str, np.array]:
    """
    read a txt file (tsv or csv) and return a np array with columns cited in columns_str

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
    if converters is None:
        converters = {}
    if column_converter is None:
        column_converter = {}

    # check columns
    try:
        columns = [int(x) - 1 for x in columns_str.split(",")]
    except Exception:
        return False, f"Problem with columns {columns_str}", np.array([])

    # check converters
    np_converters: dict = {}
    for column_idx in column_converter:
        if column_converter[column_idx] in converters:
            conv_name = column_converter[column_idx]

            function = f"""def {conv_name}(INPUT):\n"""
            function += """    INPUT = INPUT.decode("utf-8") if isinstance(INPUT, bytes) else INPUT"""
            for line in converters[conv_name]["code"].split("\n"):
                function += f"    {line}\n"
            function += """    return OUTPUT"""

            try:
                exec(function)
            except Exception:
                return False, f"error in converter: {sys.exc_info()[1]}", np.array([])

            np_converters[column_idx - 1] = locals()[conv_name]

        else:
            return False, f"converter {cfg.converters_param[column_idx]} not found", np.array([])

    # snif txt file
    try:
        with open(file_name) as csvfile:
            buff = csvfile.read(4096)
            snif = csv.Sniffer()
            dialect = snif.sniff(buff)
            """has_header = snif.has_header(buff)"""
        # count number of header rows
        header_rows_nb = 0
        csv.register_dialect("dialect", dialect)
        with open(file_name, "r") as f:
            reader = csv.reader(f, dialect="dialect")
            for row in reader:
                if sum([isinstance(intfloatstr(x), str) for x in row]) == len(row):
                    header_rows_nb += 1

    except Exception:
        return False, f"{sys.exc_info()[1]}", np.array([])

    try:
        data = np.loadtxt(file_name, delimiter=dialect.delimiter, usecols=columns, skiprows=header_rows_nb, converters=np_converters)

    except Exception:
        return False, f"{sys.exc_info()[1]}", np.array([])

    # check if first value must be substracted
    if substract_first_value == "True":
        data[:, 0] -= data[:, 0][0]

    return True, "", data


def versiontuple(version_str: str) -> tuple:
    """
    Convert version from str to tuple of str

    Args:
        version_str (str): version

    Returns:
        tuple[str, str, str]: version in tuple format (for comparison)
    """
    filled = []
    for point in version_str.split("."):
        filled.append(point.zfill(8))
    return tuple(filled)


def behavior_user_color(ethogram: dict, behavior_code: str) -> Union[str, None]:
    """
    returns the color of behavior if defined else None
    """
    for x in ethogram:
        if ethogram[x][cfg.BEHAVIOR_CODE] == behavior_code:
            if ethogram[x].get(cfg.COLOR, None) == "":
                return None
            else:
                return ethogram[x].get(cfg.COLOR, None)

    return None


def behav_category_user_color(behavioral_categories: dict, name: str) -> Union[str, None]:
    """
    returns the color of the behavioral category if defined else None
    """
    for key in behavioral_categories:
        if behavioral_categories[key]["name"] == name:
            return behavioral_categories[key].get(cfg.COLOR, None)

    return None


def state_behavior_codes(ethogram: dict) -> list:
    """
    behavior codes defined as STATE event

    Args:
        ethogram (dict): ethogram dictionary

    Returns:
        list: list of behavior codes defined as STATE event

    """
    return [ethogram[x][cfg.BEHAVIOR_CODE] for x in ethogram if cfg.STATE in ethogram[x][cfg.TYPE].upper()]


def point_behavior_codes(ethogram: dict) -> list:
    """
    behavior codes defined as POINT event

    Args:
        ethogram (dict): ethogram dictionary

    Returns:
        list: list of behavior codes defined as POINT event

    """
    return [ethogram[x][cfg.BEHAVIOR_CODE] for x in ethogram if cfg.POINT in ethogram[x][cfg.TYPE].upper()]


def group_events(pj: dict, obs_id: str, include_modifiers: bool = False) -> dict:
    """
    group events by subject, behavior, modifier (if required)

    result is a dict like:

    {(subject, behavior, ""): list of tuple (start: Decimal, end: Decimal)}

    or with modifiers:

    {(subject, behavior, modifier): list of tuple (start: Decimal, end: Decimal)}

    in case of point events start=end
    """

    try:
        state_events_list = state_behavior_codes(pj[cfg.ETHOGRAM])
        point_events_list = point_behavior_codes(pj[cfg.ETHOGRAM])
        mem_behav = {}
        intervals_behav = {}

        for event in pj[cfg.OBSERVATIONS][obs_id][cfg.EVENTS]:
            time_ = event[cfg.EVENT_TIME_FIELD_IDX]
            subject = event[cfg.EVENT_SUBJECT_FIELD_IDX]
            code = event[cfg.EVENT_BEHAVIOR_FIELD_IDX]
            modifier = event[cfg.EVENT_MODIFIER_FIELD_IDX] if include_modifiers else ""

            # check if code is state
            if code in state_events_list:
                if (subject, code, modifier) in mem_behav and mem_behav[(subject, code, modifier)]:
                    if (subject, code, modifier) not in intervals_behav:
                        intervals_behav[(subject, code, modifier)] = []
                    intervals_behav[(subject, code, modifier)].append((mem_behav[(subject, code, modifier)], time_))

                    mem_behav[(subject, code, modifier)] = 0
                else:
                    mem_behav[(subject, code, modifier)] = time_

            # check if code is state
            if code in point_events_list:
                if (subject, code, modifier) not in intervals_behav:
                    intervals_behav[(subject, code, modifier)] = []
                intervals_behav[(subject, code, modifier)].append((time_, time_))

        return intervals_behav

    except Exception:
        return {"error": ""}


def get_current_states_modifiers_by_subject(
    state_behaviors_codes: list, events: list, subjects: dict, time_: dec, include_modifiers: bool = False
) -> dict:
    """
    get current states and modifiers (if requested) for subjects at given time

    Args:
        state_behaviors_codes (list): list of behavior codes defined as STATE event
        events (list): list of events
        subjects (dict): dictionary of subjects
        time (Decimal): time or image index for an observation from images
        include_modifiers (bool): include modifier if True (default: False)

    Returns:
        dict: current states by subject. dict of list
    """
    current_states: dict = {}
    if time_.is_nan():
        for idx in subjects:
            current_states[idx] = []
        return current_states

    # check if time contains NA
    if [x for x in events if x[cfg.EVENT_TIME_FIELD_IDX].is_nan()]:
        check_index = cfg.PJ_OBS_FIELDS[cfg.IMAGES][cfg.IMAGE_INDEX]
    else:
        check_index = cfg.EVENT_TIME_FIELD_IDX

    if include_modifiers:
        for idx in subjects:
            current_states[subjects[idx]["name"]] = {}
        for x in events:
            if x[check_index] > time_:
                break
            if x[cfg.EVENT_BEHAVIOR_FIELD_IDX] in state_behaviors_codes:
                if (x[cfg.EVENT_BEHAVIOR_FIELD_IDX], x[cfg.EVENT_MODIFIER_FIELD_IDX]) not in current_states[x[cfg.EVENT_SUBJECT_FIELD_IDX]]:
                    current_states[x[cfg.EVENT_SUBJECT_FIELD_IDX]][(x[cfg.EVENT_BEHAVIOR_FIELD_IDX], x[cfg.EVENT_MODIFIER_FIELD_IDX])] = (
                        False
                    )

                current_states[x[cfg.EVENT_SUBJECT_FIELD_IDX]][
                    (x[cfg.EVENT_BEHAVIOR_FIELD_IDX], x[cfg.EVENT_MODIFIER_FIELD_IDX])
                ] = not current_states[x[cfg.EVENT_SUBJECT_FIELD_IDX]][(x[cfg.EVENT_BEHAVIOR_FIELD_IDX], x[cfg.EVENT_MODIFIER_FIELD_IDX])]

        r: dict = {}
        for idx in subjects:
            r[idx] = [f"{bm[0]} ({bm[1]})" for bm in current_states[subjects[idx]["name"]] if current_states[subjects[idx]["name"]][bm]]

    else:
        for idx in subjects:
            current_states[subjects[idx]["name"]] = {}
            for b in state_behaviors_codes:
                current_states[subjects[idx]["name"]][b] = False
        for x in events:
            if x[check_index] > time_:
                break
            if x[cfg.EVENT_BEHAVIOR_FIELD_IDX] in state_behaviors_codes:
                current_states[x[cfg.EVENT_SUBJECT_FIELD_IDX]][x[cfg.EVENT_BEHAVIOR_FIELD_IDX]] = not current_states[
                    x[cfg.EVENT_SUBJECT_FIELD_IDX]
                ][x[cfg.EVENT_BEHAVIOR_FIELD_IDX]]

        r: dict = {}
        for idx in subjects:
            r[idx] = [b for b in state_behaviors_codes if current_states[subjects[idx]["name"]][b]]

    return r


def get_current_states_modifiers_by_subject_2(state_behaviors_codes: list, events: list, subjects: dict, time: dec) -> dict:
    """
    get current states and modifiers for subjects at given time
    differs from get_current_states_modifiers_by_subject in the output format: [behavior, modifiers]

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
            bl = [
                (x[cfg.EVENT_BEHAVIOR_FIELD_IDX], x[cfg.EVENT_MODIFIER_FIELD_IDX])
                for x in events
                if x[cfg.EVENT_SUBJECT_FIELD_IDX] == subjects[idx][cfg.SUBJECT_NAME]
                and x[cfg.EVENT_BEHAVIOR_FIELD_IDX] == sbc
                and x[cfg.EVENT_TIME_FIELD_IDX] <= time
            ]

            if len(bl) % 2:  # test if odd
                current_states[idx].append(bl[-1])

    return current_states


def get_current_points_by_subject(
    point_behaviors_codes: list,
    events: list,
    subjects: dict,
    time: dec,
    tolerance: dec,
    include_modifiers: bool = False,
) -> dict:
    """
    get point events for subjects between given time (time) and (time + tolerance)
    includes modifiers
    Args:
        point_behaviors_codes (list): list of behavior codes defined as POINT event
        events (list): list of events
        subjects (dict): dictionary of subjects
        time (Decimal): time (s)
        tolerance (Decimal): tolerance (s)
        include_modifiers (bool): True to include modifiers

    Returns:
        dict: current point behaviors by subject. dict of list
    """

    current_points = {}
    for idx in subjects:
        current_points[idx] = []
        for sbc in point_behaviors_codes:
            # if include_modifiers:
            point_events = [
                (x[cfg.EVENT_BEHAVIOR_FIELD_IDX], x[cfg.EVENT_MODIFIER_FIELD_IDX])
                for x in events
                if x[cfg.EVENT_SUBJECT_FIELD_IDX] == subjects[idx]["name"]
                and x[cfg.EVENT_BEHAVIOR_FIELD_IDX] == sbc
                # and abs(x[EVENT_TIME_FIELD_IDX] - time) <= tolerance
                and time <= x[cfg.EVENT_TIME_FIELD_IDX] < (time + tolerance)
            ]

            # else:
            #    point_events = [x[EVENT_BEHAVIOR_FIELD_IDX] for x in events
            #                    if x[EVENT_SUBJECT_FIELD_IDX] == subjects[idx]["name"]
            #                    and x[EVENT_BEHAVIOR_FIELD_IDX] == sbc
            #                   # and abs(x[EVENT_TIME_FIELD_IDX] - time) <= tolerance
            #                    and time <= x[EVENT_TIME_FIELD_IDX] < (time + tolerance)]
            for point_event in point_events:
                current_points[idx].append(point_event)

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
            buff = csvfile.read(4096)
            snif = csv.Sniffer()
            dialect = snif.sniff(buff)
            has_header = snif.has_header(buff)

        csv.register_dialect("dialect", dialect)
        rows_len: list = []
        with open(file_name, "r") as f:
            reader = csv.reader(f, dialect="dialect")
            for row in reader:
                if not row:
                    continue
                """
                if len(row) not in rows_len:
                    rows_len.append(len(row))
                    if len(rows_len) > 1:
                        break
                """
                rows_len.append(len(row))

        rows_number = len(rows_len)
        rows_uniq_len = set(rows_len)

        # test if file empty
        if not rows_uniq_len:
            return {"error": "The file is empty"}

        if len(rows_uniq_len) == 1:
            return {
                "homogeneous": True,
                "fields number": rows_len[0],
                "separator": dialect.delimiter,
                "rows number": rows_number,
                "has header": has_header,
            }
        else:
            return {"homogeneous": False}
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

    wav_file_path = pl.Path(tmp_dir) / pl.Path(media_file_path + ".wav").name

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

        p = subprocess.Popen(
            f'"{ffmpeg_bin}" -i "{media_file_path}" -y -ac 1 -vn "{wav_file_path}"',
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            shell=True,
        )
        out, error = p.communicate()
        out, error = out.decode("utf-8"), error.decode("utf-8")
        logging.debug(f"{out}, {error}")

        if "does not contain any stream" not in error:
            if wav_file_path.is_file():
                return str(wav_file_path)
            return ""
        else:
            return ""


def decimal_default(obj):
    if isinstance(obj, dec):
        return float(round(obj, 3))
    raise TypeError


def complete(lst: list, max_: int) -> list:
    """
    complete list with empty string ("") until len = max

    Args:
        lst (list): list to complete
        max_ (int): number of items to reach

    Returns:
        list: list completed to max_ items with empty string ("")
    """
    while len(lst) < max_:
        lst.append("")
    return lst


def datetime_iso8601(dt) -> str:
    """
    current date time in ISO8601 format without microseconds
    example: 2019-06-13 10:01:02

    Returns:
        str: date time in ISO8601 format without microseconds
    """
    return dt.isoformat(sep=" ", timespec="seconds")


def seconds_of_day(timestamp: dt.datetime) -> dec:
    """
    return the number of seconds since start of the day

    Returns:
        dev: number of seconds since the start of the day
    """

    # logging.debug("function: seconds_of_day")
    # logging.debug(f"{timestamp = }")

    t = timestamp.time()
    return dec(t.hour * 3600 + t.minute * 60 + t.second + t.microsecond / 1000000).quantize(dec("0.001"))


def sorted_keys(d: dict) -> list:
    """
    return list of sorted keys of provided dictionary

    Args:
        d (dict): dictionary

    Returns:
         list: dictionary keys sorted numerically
    """
    return [str(x) for x in sorted([int(x) for x in d.keys()])]


def intfloatstr(s: str) -> int:
    """
    convert str in int or float or return str
    """

    try:
        return int(s)
    except Exception:
        try:
            return f"{float(s):0.3f}"
        except Exception:
            return s


def distance(p1, p2):
    """
    euclidean distance between 2 points
    """
    x1, y1 = p1
    x2, y2 = p2
    return ((x1 - x2) ** 2 + (y1 - y2) ** 2) ** 0.5


def angle(vertex: tuple, side1: tuple, side2: tuple) -> float:
    """
    Determine the angle between 3 points (p1 must be the vertex)
    return angle in degree

    Args:
        vertex (tuple): vertex
        side1 (tuple): side 1
        side2 (tuple): side 2

    Returns:
        float: angle between side1 - vertex - side2
    """
    return (
        math.acos(
            (distance(vertex, side1) ** 2 + distance(vertex, side2) ** 2 - distance(side1, side2) ** 2)
            / (2 * distance(vertex, side1) * distance(vertex, side2))
        )
        / math.pi
        * 180
    )


def oriented_angle(P1: tuple, P2: tuple, P3: tuple) -> float:
    """
    Calculate the oriented angle between two segments.

    Args:
        P1: Coordinates of the vertex
        P2: Coordinates of the first point
        P3: Coordinates of the second point

    Returns:
        The oriented angle between the two segments in degrees.
    """

    x1, y1 = P1
    x2, y2 = P2
    x3, y3 = P1
    x4, y4 = P3

    angle_AB = math.atan2(y2 - y1, x2 - x1)
    angle_CD = math.atan2(y4 - y3, x4 - x3)

    oriented_angle = math.degrees(angle_AB - angle_CD)

    return oriented_angle


def mem_info():
    """
    get info about total mem, used mem and available mem using:
       "free -m" command on Linux
       "top -l 1 -s 0" command in MacOS
       "systeminfo" command on Windows

    Returns:
        bool: True if error
        dict: values ("total_memory", "used_memory", "free_memory")
    """

    if sys.platform.startswith("linux"):
        try:
            process = subprocess.run(["free", "-m"], stdout=subprocess.PIPE)
            # out, err = process.communicate()
            out = process.stdout
            _, tot_mem, used_mem, _, _, _, available_mem = [x.decode("utf-8") for x in out.split(b"\n")[1].split(b" ") if x != b""]
            return False, {
                "total_memory": int(tot_mem),
                "used_memory": int(used_mem),
                "free_memory": int(available_mem),
            }
        except Exception:
            return True, {"msg": error_info(sys.exc_info())[0]}

    if sys.platform.startswith("darwin"):
        try:
            output = subprocess.check_output(("top", "-l", "1", "-s", "0"))
            r = [x.decode("utf-8") for x in output.split(b"\n") if b"PhysMem" in x][0].split(" ")
            used_mem, free_mem = int(r[1].replace("M", "")), int(r[5].replace("M", ""))
            return False, {"total_memory": used_mem + free_mem, "used_memory": used_mem, "free_memory": free_mem}
        except Exception:
            return True, {"msg": error_info(sys.exc_info())[0]}

    if sys.platform.startswith("win"):
        try:
            output = subprocess.run(["wmic", "computersystem", "get", "TotalPhysicalMemory", "/", "Value"], stdout=subprocess.PIPE)
            tot_mem = int(output.stdout.strip().split(b"=")[-1].decode("utf-8")) / 1024 / 1024

            output = subprocess.run(["wmic", "OS", "get", "FreePhysicalMemory", "/", "Value"], stdout=subprocess.PIPE)
            free_mem = int(output.stdout.strip().split(b"=")[-1].decode("utf-8")) / 1024
            return False, {"total_memory": tot_mem, "free_memory": free_mem}

        except Exception:
            return True, {"msg": error_info(sys.exc_info())[0]}

    return True, {"msg": "Unknown operating system"}


def polygon_area(poly: list) -> float:
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


def polyline_length(poly: list) -> float:
    """
    length of polyline
    """
    tot = 0
    for p in range(1, len(poly)):
        x1, y1 = poly[p - 1]
        x2, y2 = poly[p]
        tot += ((x1 - x2) ** 2 + (y1 - y2) ** 2) ** 0.5

    return tot


def url2path(url: str) -> str:
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
    return dec(str(f))


def time2seconds(time_: str) -> dec:
    """
    convert hh:mm:ss.s to number of seconds (decimal)

    Args
        time (str): time (hh:mm:ss.zzz format)

    Returns:
        Decimal: time in seconds
    """

    if " " in time_:
        try:
            return dec(str(dt.datetime.strptime(time_, "%Y-%m-%d %H:%M:%S.%f").timestamp()))
        except Exception:
            return dec("0.000")
    else:
        try:
            flag_neg = "-" in time_
            time_ = time_.replace("-", "")
            tsplit = time_.split(":")
            h, m, s = int(tsplit[0]), int(tsplit[1]), dec(tsplit[2])
            return dec(-(h * 3600 + m * 60 + s)) if flag_neg else dec(h * 3600 + m * 60 + s)
        except Exception:
            return dec("0.000")


def seconds2time(sec: dec) -> str:
    """
    convert seconds to hh:mm:ss.sss format

    Args:
        sec (Decimal): time in seconds
    Returns:
        str: time in format hh:mm:ss
    """

    if math.isnan(sec):
        return cfg.NA

    # if sec > one day treat as date
    if sec > cfg.DATE_CUTOFF:
        t = dt.datetime.fromtimestamp(float(sec))
        return f"{t:%Y-%m-%d %H:%M:%S}.{t.microsecond / 1000:03.0f}"

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


def safe_xl_worksheet_title(title: str, output_format: str):
    """
    sanitize the XLS and XLSX worksheet title

    Args:
        title (str): title for worksheet
        output_format (str): xls or xlsx
    """
    if output_format in ("xls", "xlsx"):
        if output_format in ("xls"):
            title = title[:31]
        for forbidden_char in cfg.EXCEL_FORBIDDEN_CHARACTERS:
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


def test_ffmpeg_path(FFmpegPath: str) -> Tuple[bool, str]:
    """
    test if ffmpeg has valid path

    Args:
        FFmpegPath (str): ffmepg path to test

    Returns:
        bool: True: path found
        str: message
    """

    out, error = subprocess.Popen(f'"{FFmpegPath}" -version', stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True).communicate()
    logging.debug(f"test ffmpeg path output: {out}")
    logging.debug(f"test ffmpeg path error: {error}")

    if (b"avconv" in out) or (b"the Libav developers" in error):
        return False, "Please use FFmpeg from https://www.ffmpeg.org in place of FFmpeg from Libav project."

    if (b"ffmpeg version" not in out) and (b"ffmpeg version" not in error):
        return False, "FFmpeg is required but it was not found.<br>See https://www.ffmpeg.org"

    return True, ""


def check_ffmpeg_path() -> Tuple[bool, str]:
    """
    check for ffmpeg path
    firstly search for embedded version
    if not found search for system wide version (must be in the path)

    Returns:
        bool: True if ffmpeg path found else False
        str: if bool True returns ffmpegpath else returns error message
    """

    if sys.platform.startswith("linux") or sys.platform.startswith("darwin"):
        ffmpeg_path = pl.Path("")
        # search embedded ffmpeg
        if sys.argv[0].endswith("start_boris.py"):
            ffmpeg_path = pl.Path(sys.argv[0]).resolve().parent / "boris" / "misc" / "ffmpeg"
        if sys.argv[0].endswith("__main__.py"):
            ffmpeg_path = pl.Path(sys.argv[0]).resolve().parent / "misc" / "ffmpeg"

        if not ffmpeg_path.is_file():
            # search global ffmpeg
            ffmpeg_path = "ffmpeg"

        # test ffmpeg
        r, msg = test_ffmpeg_path(str(ffmpeg_path))
        if r:
            return True, str(ffmpeg_path)
        else:
            return False, "FFmpeg is not available"

    if sys.platform.startswith("win"):
        ffmpeg_path = pl.Path("")
        # search embedded ffmpeg
        if sys.argv[0].endswith("start_boris.py"):
            ffmpeg_path = pl.Path(sys.argv[0]).resolve().parent / "boris" / "misc" / "ffmpeg.exe"
        if sys.argv[0].endswith("__main__.py"):
            ffmpeg_path = pl.Path(sys.argv[0]).resolve().parent / "misc" / "ffmpeg.exe"

        if not ffmpeg_path.is_file():
            # search global ffmpeg
            ffmpeg_path = "ffmpeg"

        # test ffmpeg
        r, msg = test_ffmpeg_path(str(ffmpeg_path))
        if r:
            return True, str(ffmpeg_path)
        else:
            return False, "FFmpeg is not available"


def smart_size_format(n: Union[float, int, str, None]) -> str:
    """
    format with kb, Mb or Gb in base of value
    """
    if n is None:
        return cfg.NA
    if str(n) == "NA":
        return cfg.NA
    if math.isnan(n):
        return cfg.NA
    if n < 1_000:
        return f"{n:,.1f} b"
    if n < 1_000_000:
        return f"{n / 1_000:,.1f} Kb"
    if n < 1_000_000_000:
        return f"{n / 1_000_000:,.1f} Mb"
    return f"{n / 1_000_000_000:,.1f} Gb"


def ffprobe_media_analysis(ffmpeg_bin: str, file_name: str) -> dict:
    """
    analyse video parameters with ffprobe (if available)

    Args:
        ffmpeg_bin (str): ffmpeg path
        file_name (str): path of media file

    Returns:
        dict
    """
    # ffprobe -v quiet -print_format json -show_format -show_streams /tmp/ramdisk/video1.mp4
    ffprobe_bin = ffmpeg_bin.replace("ffmpeg", "ffprobe")

    command = f'"{ffprobe_bin}" -hide_banner -v error -print_format json -show_format -show_streams "{file_name}"'

    p = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)
    out, error = p.communicate()
    if error:
        return {"error": f"{error}"}

    try:
        hasVideo = False
        hasAudio = False
        """bitrate = None"""
        video_bitrate = None
        audio_bitrate = []
        resolution = None
        fps = 0
        sample_rate = None
        duration = None
        audio_duration = cfg.NA
        frames_number = None
        size = None
        audio_codec = None
        video_codec = None

        video_param = json.loads(out.decode("utf-8"))
        if "size" in video_param["format"]:
            size = int(video_param["format"]["size"])

        for stream in video_param["streams"]:
            if stream["codec_type"] == "video":
                hasVideo = True
                video_bitrate = int(stream["bit_rate"]) if "bit_rate" in stream else None
                resolution = f"{stream['width']}x{stream['height']}"

                """
                if "avg_frame_rate" in stream:
                    if stream["avg_frame_rate"] == "0/0":
                        fps = 0
                    else:
                        try:
                            fps = eval(stream["avg_frame_rate"])
                        except Exception:
                            fps = 0
                """
                if "r_frame_rate" in stream:
                    if stream["r_frame_rate"] == "0/0":
                        fps = 0
                    else:
                        try:
                            fps = eval(stream["r_frame_rate"])
                        except Exception:
                            fps = 0

                if "duration" in stream:
                    duration = float(stream["duration"])
                if "duration_ts" in stream:
                    frames_number = int(stream["duration_ts"])
                elif "nb_frames" in stream:
                    frames_number = int(stream["nb_frames"])
                else:
                    frames_number = None

                video_codec = stream["codec_long_name"] if "codec_long_name" in stream else None

            if stream["codec_type"] == "audio":
                hasAudio = True
                sample_rate = float(stream["sample_rate"]) if "sample_rate" in stream else cfg.NA
                # TODO manage audio_duration parameter
                audio_duration = float(stream["duration"]) if "duration" in stream else cfg.NA
                audio_codec = stream["codec_long_name"]
                audio_bitrate.append(int(stream.get("bit_rate", 0)))

        # check duration
        if duration is None:
            if "duration" in video_param["format"]:
                duration = float(video_param["format"]["duration"])
            else:
                duration = 0

        # check bit rate
        if "bit_rate" in video_param["format"]:
            all_bitrate = int(video_param["format"]["bit_rate"])
        else:
            all_bitrate = None

        if video_bitrate is None and all_bitrate is not None:
            video_bitrate = all_bitrate - sum(audio_bitrate)

        # extract format long name
        format_long_name = video_param["format"]["format_long_name"] if "format_long_name" in video_param["format"] else cfg.NA

        # extract creation time ("creation_time": "2023-03-22T16:50:32.000000Z")
        creation_time = cfg.NA
        if "tags" in video_param["format"] and "creation_time" in video_param["format"]["tags"]:
            creation_time = video_param["format"]["tags"]["creation_time"].replace("T", " ")
            if "." in creation_time:
                creation_time = creation_time.split(".")[0]

        return {
            "analysis_program": "ffprobe",
            "frames_number": frames_number,
            "duration_ms": duration * 1000,
            "duration": duration,
            "audio_duration": audio_duration,
            "fps": fps,
            "has_video": hasVideo,
            "has_audio": hasAudio,
            "bitrate": video_bitrate,
            "resolution": resolution,
            "sample_rate": sample_rate,
            "file size": size,
            "audio_codec": audio_codec,
            "video_codec": video_codec,
            "creation_time": creation_time,
            "format_long_name": format_long_name,
        }

    except Exception as e:
        raise
        return {"error": str(e)}


def accurate_media_analysis(ffmpeg_bin: str, file_name: str) -> dict:
    """
    analyse frame rate and video duration with ffprobe or ffmpeg if ffprobe not available
    Returns parameters: duration, duration_ms, bitrate, frames_number, fps, has_video (True/False), has_audio (True/False)

    Args:
        ffmpeg_bin (str): ffmpeg path
        file_name (str): path of media file

    Returns:
        dict containing keys: duration, duration_ms, frames_number, bitrate, fps, has_video, has_audio

    """

    ffprobe_results = ffprobe_media_analysis(ffmpeg_bin, file_name)

    logging.debug(f"file_name: {file_name}")
    logging.debug(f"ffprobe_results: {ffprobe_results}")

    if ("error" not in ffprobe_results) and (ffprobe_results["bitrate"] is not None):
        return ffprobe_results
    else:
        # use ffmpeg
        command = f'"{ffmpeg_bin}" -hide_banner -i "{file_name}" > {"NUL" if sys.platform.startswith("win") else "/dev/null"}'

        p = subprocess.Popen(command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True)

        duration, fps, hasVideo, hasAudio, bitrate = 0, 0, False, False, None
        try:
            _, error = p.communicate()
        except Exception as e:
            return {"error": str(e)}

        rows = error.split(b"\n")

        # check if file found and if invalid data found
        for row in rows:
            if b"No such file or directory" in row:
                return {"error": "No such file or directory"}
            if b"Invalid data found when processing input" in row:
                return {"error": "This file does not seem to be a media file"}

        # video duration
        try:
            for row in rows:
                if b"Duration" in row:
                    duration = time2seconds(row.split(b"Duration: ")[1].split(b",")[0].strip().decode("utf-8"))
                    break
        except Exception:
            duration = 0

        # bitrate
        try:
            for row in rows:
                if b"bitrate:" in row:
                    re_results = re.search(b"bitrate: (.{1,10}) kb", row, re.IGNORECASE)
                    if re_results:
                        bitrate = int(re_results.group(1).strip()) * 1000
                    break
        except Exception:
            bitrate = None

        # fps
        fps = 0
        try:
            for row in rows:
                if b" fps," in row:
                    re_results = re.search(b", (.{1,10}) fps,", row, re.IGNORECASE)
                    if re_results:
                        fps = dec(re_results.group(1).strip().decode("utf-8"))
                        break
        except Exception:
            fps = 0

        # check for video stream
        hasVideo, resolution = False, None
        try:
            for row in rows:
                if b"Stream #" in row and b"Video:" in row:
                    hasVideo = True
                    # get resolution \d{3,5}x\d{3,5}
                    re_results = re.search(r"\d{3,5}x\d{3,5}", row, re.IGNORECASE)
                    if re_results:
                        resolution = re_results.group(0).decode("utf-8")
                    break
        except Exception:
            hasVideo, resolution = False, None

        # check for audio stream
        hasAudio = False
        try:
            for row in rows:
                if b"Stream #" in row and b"Audio:" in row:
                    hasAudio = True
                    break
        except Exception:
            hasAudio = False

        if not hasVideo and not hasAudio:
            return {"error": "This file does not seem to be a media file"}

        return {
            "analysis_program": "ffmpeg",
            "frames_number": int(fps * duration),
            "duration_ms": duration * 1000,
            "duration": duration,
            "audio_duration": cfg.NA,
            "fps": fps,
            "has_video": hasVideo,
            "has_audio": hasAudio,
            "bitrate": bitrate,
            "resolution": resolution,
            "format_long_name": "",
        }


def behavior_color(colors_list: list, idx: int, default_color: str = "darkgray"):
    """
    return color with index corresponding to behavior index

    see BEHAVIORS_PLOT_COLORS list in config.py

    Args:
        colors_list (list): list of colors
        idx (int): index of behavior in all behaviors list (sorted)
        default_color (str): default color (if problem)

    Returns:
        str: color corresponding to behavior index

    """

    try:
        return colors_list[idx % len(colors_list)].replace("tab:", "")
    except Exception:
        return default_color


def all_behaviors(ethogram: dict) -> list:
    """
    extract all behaviors from the submitted ethogram
    behaviors are alphabetically sorted

    Args:
        ethogram (dict): ethogram

    Returns:
        list: behaviors code (alphabetically sorted)
    """

    return [ethogram[x][cfg.BEHAVIOR_CODE] for x in sorted_keys(ethogram)]


def all_subjects(subjects: dict) -> list:
    """
    extract all subjects from the subject configuration dictionary

    Args:
        subject configuration (dict)

    Returns:
        list: subjects name
    """

    return [subjects[x][cfg.SUBJECT_NAME] for x in sorted_keys(subjects)]


def has_coding_map(ethogram: dict, behavior_idx: str) -> bool:
    """
    check if behavior index has a coding map
    """
    if not ethogram.get(behavior_idx, False):
        return False
    if not ethogram[behavior_idx].get("coding map", False):
        return False
    return False


def dir_images_number(dir_path_str: str) -> dict:
    """
    return number of images in dir_path (see cfg.IMAGE_EXTENSIONS)
    """

    dir_path = pl.Path(dir_path_str)
    if not dir_path.is_dir():
        return {"error": f"The directory {dir_path_str} does not exists"}
    img_count = 0
    for pattern in cfg.IMAGE_EXTENSIONS:
        img_count += len(list(dir_path.glob(pattern)))
        img_count += len(list(dir_path.glob(pattern.upper())))
    return {"number of images": img_count}


def intersection(A, B, C, D):
    """
    line segments intersection with decimal precision
    return True when intersection else False
    """
    getcontext().prec = 28

    xa, ya = dec(str(A[0])), dec(str(A[1]))
    xb, yb = dec(str(B[0])), dec(str(B[1]))
    xc, yc = dec(str(C[0])), dec(str(C[1]))
    xd, yd = dec(str(D[0])), dec(str(D[1]))

    # check if first segment is vertical
    try:
        if xa == xb:
            slope = (yc - yd) / (xc - xd)
            intersept = yc - slope * xc
            xm = xa
            ym = slope * xm + intersept

        # check if second segment is vertical
        elif xc == xd:
            slope = (ya - yb) / (xa - xb)
            intersept = ya - slope * xa
            xm = xc
            ym = slope * xm + intersept
        else:
            xm = (
                (xd * xa * yc - xd * xb * yc - xd * xa * yb - xc * xa * yd + xc * xa * yb + xd * ya * xb + xc * xb * yd - xc * ya * xb)
                / (-yb * xd + yb * xc + ya * xd - ya * xc + xb * yd - xb * yc - xa * yd + xa * yc)
            ).quantize(dec(".001"), rounding=ROUND_DOWN)
            ym = (
                (yb * xc * yd - yb * yc * xd - ya * xc * yd + ya * yc * xd - xa * yb * yd + xa * yb * yc + ya * xb * yd - ya * xb * yc)
                / (-yb * xd + yb * xc + ya * xd - ya * xc + xb * yd - xb * yc - xa * yd + xa * yc)
            ).quantize(dec(".001"), rounding=ROUND_DOWN)

        xmin1, xmax1 = min(xa, xb), max(xa, xb)
        xmin2, xmax2 = min(xc, xd), max(xc, xd)
        ymin1, ymax1 = min(ya, yb), max(ya, yb)
        ymin2, ymax2 = min(yc, yd), max(yc, yd)

        return xm >= xmin1 and xm <= xmax1 and xm >= xmin2 and xm <= xmax2 and ym >= ymin1 and ym <= ymax1 and ym >= ymin2 and ym <= ymax2

    except Exception:  # for cases xa=xb=xc=xd
        return True
