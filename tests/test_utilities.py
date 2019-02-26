"""
module for testing utilities.py

https://realpython.com/python-continuous-integration/

pytest -s -vv test_utilities.py
"""

import pytest
import hashlib
import glob
import os
import sys
from decimal import Decimal
import json
import datetime
import numpy as np

sys.path.append("../src")

import utilities
import config


@pytest.fixture()
def before():
    os.system("rm -rf output")
    os.system("mkdir output")


class Test_accurate_media_analysis(object):

    def test_media_ok(self):
        r = utilities.accurate_media_analysis("ffmpeg", "files/geese1.mp4")
        assert r == {'frames_number': 1548, 'duration_ms': Decimal('61920.00'),
                    'duration': Decimal('61.92'), 'fps': Decimal('25'),
                    'has_video': True, 'has_audio': True, 'bitrate': 901,
                    'resolution': '640x480'}

    def test_no_media(self):
        r = utilities.accurate_media_analysis("ffmpeg", "files/test.boris")
        assert r == {'error': 'This file do not seem to be a media file'}

    def test_media_does_not_exist(self):
        r = utilities.accurate_media_analysis("ffmpeg", "files/xxx")
        assert r == {'error': 'This file do not seem to be a media file'}



class Test_angle(object):
    def test_1(self):
        round(utilities.angle((0, 0), (0, 90), (90, 0)), 3) == 90.0

    def test_2(self):
        assert round(utilities.angle((0, 0), (90, 0), (90, 0)), 3) == 0.0

    def test_3(self):
        assert round(utilities.angle((0, 0), (90, 0), (0, 90)), 3) == 90.0


class Test_behavior_color(object):
    def test_idx0(self):
        assert utilities.behavior_color(config.BEHAVIORS_PLOT_COLORS, 0) == "tab:blue"

    def test_idx1000(self):
        assert utilities.behavior_color(config.BEHAVIORS_PLOT_COLORS, 1000) == "midnightblue"


class Test_bytes_to_str(object):
    def test_bytes(self):
        assert utilities.bytes_to_str(b"abc 2.3") == "abc 2.3"

    def test_str(self):
        assert utilities.bytes_to_str("abc 2.3") == "abc 2.3"


class Test_check_txt_file(object):
    def test_csv(self):
        r = utilities.check_txt_file("files/test_check_txt_file_test_csv.csv")
        assert r == {'homogeneous': True, 'fields number': 7, 'separator': ','}

    def test_tsv(self):
        r = utilities.check_txt_file("files/test_check_txt_file_test_tsv.tsv")
        assert r =={'homogeneous': True, 'fields number': 5, 'separator': '\t'}

    def test_no_homogeneous(self):
        r = utilities.check_txt_file("files/test.boris")
        assert r == {'homogeneous': False}

    def test_file_does_not_exists(self):
        r = utilities.check_txt_file("files/xxx")
        assert r == {'error': "[Errno 2] No such file or directory: 'files/xxx'"}


class Test_complete(object):
    def test_list_3_to_8(self):
        assert utilities.complete(["a","b","c"], 8) == ["a", "b", "c", "", "", "", "", ""]

    def test_empty_list(self):
        assert utilities.complete([], 4) == ["", "", "", ""]

    def test_list_longer_then_max(self):
        assert utilities.complete(["a","b","c","d"], 3) == ["a","b","c","d"]



class Test_convert_time_to_decimal(object):
    def test_1(self):
        pj = json.loads(open("files/test2.boris").read())
        r = utilities.convert_time_to_decimal(pj)

        txt = open("files/test.txt").read()
        pj_dec = eval(txt)
        assert r == pj_dec


class Test_datetime_iso8601(object):
    def test_1(self):
        r = utilities.datetime_iso8601(datetime.datetime(2018, 12, 1, 22, 36, 7, 652523))
        assert r == "2018-12-01 22:36:07"


class Test_decimal_default(object):
    def test_1(self):
        assert utilities.decimal_default(Decimal("1.456")) == 1.456
        assert isinstance(utilities.decimal_default(Decimal("1.456")), float)


class Test_distance(object):
    def test_1(self):
        utilities.distance((10, 10), (80, 120)) == 130.38404810405297


class Test_eol2space(object):
    def test_rn(self):
        assert utilities.eol2space("aaa\r\nbbb") == "aaa bbb"

    def test_n(self):
        assert utilities.eol2space("aaa\nbbb") == "aaa bbb"

    def test_r(self):
        assert utilities.eol2space("aaa\rbbb") == "aaa bbb"


class Test_extract_frames(object):
    @pytest.mark.usefixtures("before")
    def test_png(self):
        utilities.extract_frames(ffmpeg_bin="ffmpeg",
                                 start_frame=1,
                                 second=2,
                                 current_media_path="files/geese1.mp4",
                                 fps=25,
                                 imageDir="output",
                                 md5_media_path=hashlib.md5("files/geese1.mp4".encode("utf-8")).hexdigest(),
                                 extension="png",
                                 frame_resize=256,
                                 number_of_seconds=2)
        files_list = sorted(glob.glob("output/*.png"))
        assert len(files_list) == 50
        assert files_list[0] == "output/BORIS@040d8545ab408b6c5f87b6316da9e4bf_00000001.png"

    @pytest.mark.usefixtures("before")
    def test_jpg(self):
        utilities.extract_frames(ffmpeg_bin="ffmpeg",
                                 start_frame=1,
                                 second=2,
                                 current_media_path="files/geese1.mp4",
                                 fps=25,
                                 imageDir="output",
                                 md5_media_path=hashlib.md5("files/geese1.mp4".encode("utf-8")).hexdigest(),
                                 extension="jpg",
                                 frame_resize=256,
                                 number_of_seconds=2)
        files_list = sorted(glob.glob("output/*.jpg"))
        assert len(files_list) == 50
        assert files_list[0] == "output/BORIS@040d8545ab408b6c5f87b6316da9e4bf_00000001.jpg"


    # add test for dimensions

class Test_extract_wav(object):

    @pytest.mark.usefixtures("before")
    def test_wav_from_mp4(self):
        r = utilities.extract_wav(ffmpeg_bin="ffmpeg",
                                  media_file_path="files/geese1.mp4",
                                  tmp_dir="output")
        assert r == "output/geese1.mp4.wav"
        assert os.path.isfile("output/geese1.mp4.wav")


class Test_file_content_md5(object):

    def test_file(self):
        r = utilities.file_content_md5(file_name="files/geese1.mp4")
        assert r == "66e19a1e182b7564c4e8c2b1874623b8"

    def test_file_not_existing(self):
        r = utilities.file_content_md5(file_name="files/xxx")
        assert r == ""


class Test_float2decimal(object):

    def test_1(self):
        r = utilities.float2decimal(0.001)
        assert r == Decimal(str(0.001))


class Test_get_current_points_by_subject(object):

    def test_no_events(self):
        pj = json.loads(open("files/test.boris").read())
        r = utilities.get_current_points_by_subject(point_behaviors_codes=["p"],
                                  events=pj["observations"]["observation #1"]["events"],
                                  subjects=pj["subjects_conf"],
                                  time=Decimal("3"),
                                  tolerance=Decimal("3"))
        assert r == {'0': [], '1': []}

    def test_events(self):
        pj_float = json.loads(open("files/test.boris").read())
        pj = utilities.convert_time_to_decimal(pj_float)
        r = utilities.get_current_points_by_subject(point_behaviors_codes=["p"],
                                  events=pj["observations"]["offset positif"]["events"],
                                  subjects={"0":{"key":"", "name": "", "description":"no focal subject"}},
                                  time=Decimal("22.6"),
                                  tolerance=Decimal("1"))
        assert r == {'0': [['p', '']]}



class Test_get_current_states_by_subject(object):
    def test_t0(self):
        pj_float = json.loads(open("files/test.boris").read())
        pj = utilities.convert_time_to_decimal(pj_float)
        r = utilities.get_current_states_by_subject(state_behaviors_codes=["s"],
                                                events=pj["observations"]["observation #1"]["events"],
                                                subjects=pj["subjects_conf"],
                                                time=Decimal("0"))
        assert r == {'0': [], '1': []}


    def test_t4(self):
        pj_float = json.loads(open("files/test.boris").read())
        pj = utilities.convert_time_to_decimal(pj_float)
        r = utilities.get_current_states_by_subject(state_behaviors_codes=["s"],
                                                events=pj["observations"]["observation #1"]["events"],
                                                subjects=pj["subjects_conf"],
                                                time=Decimal("4.0"))
        assert r == {'0': ['s'], '1': []}


    def test_t8(self):
        pj_float = json.loads(open("files/test.boris").read())
        pj = utilities.convert_time_to_decimal(pj_float)
        r = utilities.get_current_states_by_subject(state_behaviors_codes=["s"],
                                                events=pj["observations"]["observation #1"]["events"],
                                                subjects=pj["subjects_conf"],
                                                time=Decimal("8.0"))
        assert r == {'0': [], '1': []}


    def test_t_neg(self):
        pj_float = json.loads(open("files/test.boris").read())
        pj = utilities.convert_time_to_decimal(pj_float)
        r = utilities.get_current_states_by_subject(state_behaviors_codes=["s"],
                                                events=pj["observations"]["observation #1"]["events"],
                                                subjects=pj["subjects_conf"],
                                                time=Decimal("-12.456"))
        # print(r)
        assert r == {'0': [], '1': []}


    def test_no_state_events(self):
        pj_float = json.loads(open("files/test.boris").read())
        pj = utilities.convert_time_to_decimal(pj_float)
        r = utilities.get_current_states_by_subject(state_behaviors_codes=["s"],
                                                events=pj["observations"]["offset positif"]["events"],
                                                subjects=pj["subjects_conf"],
                                                time=Decimal("30"))
        #print(r)
        assert r == {'0': [], '1': []}


    def test_events_with_modifiers(self):
        pj_float = json.loads(open("files/test.boris").read())
        pj = utilities.convert_time_to_decimal(pj_float)
        r = utilities.get_current_states_by_subject(state_behaviors_codes=["r","s"],
                                                events=pj["observations"]["modifiers"]["events"],
                                                subjects={"0":{"key":"", "name": "", "description":"no focal subject"}},
                                                time=Decimal("20"))
        #print(r)
        assert r == {'0': ['r']}



'''
class Test_get_ip_address(object):
    def test_1(self):
        print(utilities.get_ip_address())
'''


class Test_intfloatstr(object):
    def test_str(self):
        assert utilities.intfloatstr("abc") == "abc"

    def test_int(self):
        assert utilities.intfloatstr("8") == 8

    def test_float(self):
        assert utilities.intfloatstr("1.458") == "1.458"



class Test_polygon_area(object):
    def test_polygon(self):
        assert round(utilities.polygon_area([(0, 0), (90, 0), (0, 90)])) == 4050

    def test_empty_polygon(self):
        assert round(
            utilities.polygon_area([(0, 0), (90, 0), (0, 90), (90, 90)])) == 0


class Test_return_file_header(object):
    def test_file_ok(self):
        r = utilities.return_file_header("files/test_export_events_tabular.tsv")
        # print(r)
        assert r == ['Observation id\tobservation #1\t\t\t\t\t\t\t\n',
        '\t\t\t\t\t\t\t\t\n',
        'Media file(s)\t\t\t\t\t\t\t\t\n',
        '\t\t\t\t\t\t\t\t\n',
        'Player #1\tvideo_test_25fps_360s.mp4\t\t\t\t\t\t\t\n']

    def test_no_file(self):
        r = utilities.return_file_header("files/xxx")
        assert r == []

    def test_short_file(self):
        r = utilities.return_file_header("files/Test_events_to_behavioral_sequences_test_5_observation_not_paired")
        assert r == ['p|s|s+p|s+p|p|s|s+p|s|s', '', '', '', '']



class Test_safefilename(object):
    def test_filename_with_spaces(self):
        assert utilities.safeFileName("aaa bbb.ccc") == "aaa bbb.ccc"

    def test_filename_with_forbidden_chars(self):
        # ["/", "\\", ":", "*", "?", '"', "<", ">", "|"]
        assert utilities.safeFileName("aaa/bb\\b.c:cc ddd* ? \"www\" <> |"
                                      ) == "aaa_bb_b.c_cc ddd_ _ _www_ __ _"


class Test_seconds2time(object):
    def test_negative(self):
        assert utilities.seconds2time(
            Decimal(-2.123)) == "-00:00:02.123"

    def test_gt_86400(self):
        assert utilities.seconds2time(
            Decimal(86400.999)) == "24:00:00.999"

    def test_10(self):
        assert utilities.seconds2time(Decimal(10.0)) == "00:00:10.000"


class Test_sorted_keys(object):
    def test_numeric_keys(self):
        r = utilities.sorted_keys({5: "a", 4: "7", 0: "z", 6: "a"})
        #print(r)
        assert r == ['0', '4', '5', '6']

    def test_str_keys(self):
        r = utilities.sorted_keys({"10": "x", "0": "x", "1": "x", "11": "x", "05": "x"})
        #print(r)
        assert r == ['0', '1', '5', '10', '11']


class Test_state_behavior_codes(object):

    def test_1(self):
        pj_float = json.loads(open("files/test.boris").read())
        r = utilities.state_behavior_codes(pj_float["behaviors_conf"])
        # print(r)
        assert r == ['s', 'r', 'm']

    def test_empty_ethogram(self):
        r = utilities.state_behavior_codes({})
        assert r == []


class Test_test_ffmpeg_path(object):

    def test_path_ok(self):
        r = utilities.test_ffmpeg_path("ffmpeg")
        # print(r)
        assert r == (True, '')

    def test_path_do_no_exist(self):
        r = utilities.test_ffmpeg_path("xxx/ffmpeg")
        # print(r)
        assert r == (False, 'FFmpeg is required but it was not found...<br>See https://www.ffmpeg.org')


class Test_time2seconds(object):
    def test_positive(self):
        assert utilities.time2seconds("11:22:33.44") == Decimal(
            "40953.44")

    def test_negative(self):
        assert utilities.time2seconds("-11:22:33.44") == Decimal(
            "-40953.44")

    def test_zero(self):
        assert utilities.time2seconds("00:00:00.000") == Decimal(
            "0.000")


class Test_txt2np_array(object):
    def test_no_file(self):
        r = utilities.txt2np_array(file_name="files/xxx",
                                    columns_str="4,6",
                                    substract_first_value="False",
                                    converters={},
                                    column_converter={})
        # print(r)
        assert r[0] == False
        assert r[1] == "[Errno 2] No such file or directory: 'files/xxx'"
        assert list(r[2].shape) == [0]

    def test_file_csv_no_converter(self):
        r = utilities.txt2np_array(file_name="files/test_check_txt_file_test_csv.csv",
                                    columns_str="4,6",
                                    substract_first_value="False",
                                    converters={},
                                    column_converter={})
        assert r[0] == False
        assert r[1] == "could not convert string to float: '14:38:58'"
        assert list(r[2].shape) == [0]


    def test_file_csv_converter(self):
        r = utilities.txt2np_array(file_name="files/test_check_txt_file_test_csv.csv",
                                    columns_str="4,6",
                                    substract_first_value="False",
                                    converters={
  "HHMMSS_2_seconds":{
   "name":"HHMMSS_2_seconds",
   "description":"convert HH:MM:SS in seconds since 1970-01-01",
   "code":"\nh, m, s = INPUT.split(':')\nOUTPUT = int(h) * 3600 + int(m) * 60 + int(s)\n\n"
  }
 },
                                    column_converter={4: "HHMMSS_2_seconds"})
        assert r[0] == True
        assert r[1] == ""
        assert r[2][0, 0] == 52738.0
        assert r[2][1, 0] == 52740.0
        assert r[2][0, 1] == 12.4144278
        assert list(r[2].shape) == [10658, 2]


class Test_url2path(object):
    def test_1(self):
        assert utilities.url2path(
            "file:///home/olivier/v%C3%A9lo/test") == "/home/olivier/vélo/test"


class Test_versiontuple(object):

    def test_1(self):
        r = utilities.versiontuple("1.2.3")
        assert r == (1,2,3)

    def test_2(self):
        r = utilities.versiontuple("1.2")
        assert r == (1,2)

    def test_3(self):
        r = utilities.versiontuple("1")
        assert r == (1,)
