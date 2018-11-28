"""
module for testing utilities.py

https://realpython.com/python-continuous-integration/
"""

import os
import sys
from decimal import Decimal
import json


sys.path.append("..")

import utilities
import config

class Test_accurate_media_analysis(object):
    def test_media_ok(self):
        r = utilities.accurate_media_analysis("ffmpeg", "files/geese1.mp4")
        assert r == {'frames_number': 1548, 'duration_ms': Decimal('61920.00'),
                    'duration': Decimal('61.92'), 'fps': Decimal('25'),
                    'has_video': True, 'has_audio': True, 'bitrate': 901}

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
        pj = json.loads(open("files/test.boris").read())
        r = utilities.convert_time_to_decimal(pj)

        txt = open("files/test.txt").read()
        pj_dec = eval(txt)
        assert r == pj_dec


class Test_polygon_area(object):
    def test_polygon(self):
        assert round(utilities.polygon_area([(0, 0), (90, 0), (0, 90)])) == 4050

    def test_empty_polygon(self):
        assert round(
            utilities.polygon_area([(0, 0), (90, 0), (0, 90), (90, 90)])) == 0


class Test_url2path(object):
    def test_1(self):
        assert utilities.url2path(
            "file:///home/olivier/v%C3%A9lo/test") == "/home/olivier/vélo/test"


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


class Test_seconds2time(object):
    def test_negative(self):
        assert utilities.seconds2time(
            Decimal(-2.123)) == "-00:00:02.123"

    def test_gt_86400(self):
        assert utilities.seconds2time(
            Decimal(86400.999)) == "24:00:00.999"

    def test_10(self):
        assert utilities.seconds2time(Decimal(10.0)) == "00:00:10.000"


class Test_safefilename(object):
    def test_filename_with_spaces(self):
        assert utilities.safeFileName("aaa bbb.ccc") == "aaa bbb.ccc"

    def test_filename_with_forbidden_chars(self):
        # ["/", "\\", ":", "*", "?", '"', "<", ">", "|"]
        assert utilities.safeFileName("aaa/bb\\b.c:cc ddd* ? \"www\" <> |"
                                      ) == "aaa_bb_b.c_cc ddd_ _ _www_ __ _"
