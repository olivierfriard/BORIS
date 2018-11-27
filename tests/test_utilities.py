"""
module for testing utilities.py

https://realpython.com/python-continuous-integration/
"""

import os
import sys
import decimal

sys.path.append("..")

import utilities


class Test_angle(object):
    def test_1(self):
        round(utilities.angle((0, 0), (0, 90), (90, 0)), 3) == 90.0

    def test_2(self):
        assert round(utilities.angle((0, 0), (90, 0), (90, 0)), 3) == 0.0

    def test_3(self):
        assert round(utilities.angle((0, 0), (90, 0), (0, 90)), 3) == 90.0


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
        assert utilities.time2seconds("11:22:33.44") == decimal.Decimal(
            "40953.44")

    def test_negative(self):
        assert utilities.time2seconds("-11:22:33.44") == decimal.Decimal(
            "-40953.44")

    def test_zero(self):
        assert utilities.time2seconds("00:00:00.000") == decimal.Decimal(
            "0.000")


class Test_seconds2time(object):
    def test_negative(self):
        assert utilities.seconds2time(
            decimal.Decimal(-2.123)) == "-00:00:02.123"

    def test_gt_86400(self):
        assert utilities.seconds2time(
            decimal.Decimal(86400.999)) == "24:00:00.999"

    def test_10(self):
        assert utilities.seconds2time(decimal.Decimal(10.0)) == "00:00:10.000"


class Test_safefilename(object):
    def test_filename_with_spaces(self):
        assert utilities.safeFileName("aaa bbb.ccc") == "aaa bbb.ccc"

    def test_filename_with_forbidden_chars(self):
        # ["/", "\\", ":", "*", "?", '"', "<", ">", "|"]
        assert utilities.safeFileName("aaa/bb\\b.c:cc ddd* ? \"www\" <> |"
                                      ) == "aaa_bb_b.c_cc ddd_ _ _www_ __ _"
