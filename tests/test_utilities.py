"""
BORIS
Behavioral Observation Research Interactive Software
Copyright 2012-2020 Olivier Friard

module for testing utilities.py

https://realpython.com/python-continuous-integration/

pytest test_utilities.py
"""

import pytest
import os
import sys
from decimal import Decimal
import json
import datetime
import numpy as np

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from boris import utilities
from boris import config


@pytest.fixture()
def before():
    os.system("rm -rf output")
    os.system("mkdir output")


class Test_accurate_media_analysis(object):
    def test_media_ok(self):
        r = utilities.accurate_media_analysis("ffmpeg", "files/geese1.mp4")
        assert r == {
            "frames_number": 1548,
            "duration_ms": Decimal("61920.00"),
            "duration": Decimal("61.92"),
            "fps": Decimal("25"),
            "has_video": True,
            "has_audio": True,
            "bitrate": 901,
            "resolution": "640x480",
        }

    def test_no_media(self):
        r = utilities.accurate_media_analysis("ffmpeg", "files/test.boris")
        assert "error" in r
        # assert r == {'error': 'This file do not seem to be a media file'}

    def test_media_does_not_exist(self):
        r = utilities.accurate_media_analysis("ffmpeg", "files/xxx")
        assert "error" in r
        # assert r == {'error': 'This file do not seem to be a media file'}


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
        assert r == {"homogeneous": True, "fields number": 7, "separator": ","}

    def test_tsv(self):
        r = utilities.check_txt_file("files/test_check_txt_file_test_tsv.tsv")
        assert r == {"homogeneous": True, "fields number": 5, "separator": "\t"}

    def test_no_homogeneous(self):
        r = utilities.check_txt_file("files/test.boris")
        assert r == {"homogeneous": False}

    def test_file_does_not_exists(self):
        r = utilities.check_txt_file("files/xxx")
        assert r == {"error": "[Errno 2] No such file or directory: 'files/xxx'"}

    def test_empty_file(self):
        r = utilities.check_txt_file("files/empty_file")
        assert r == {"error": "Could not determine delimiter"}


class Test_complete(object):
    def test_list_3_to_8(self):
        assert utilities.complete(["a", "b", "c"], 8) == ["a", "b", "c", "", "", "", "", ""]

    def test_empty_list(self):
        assert utilities.complete([], 4) == ["", "", "", ""]

    def test_list_longer_then_max(self):
        assert utilities.complete(["a", "b", "c", "d"], 3) == ["a", "b", "c", "d"]


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


class Test_error_info(object):
    def test_error1(self):
        try:
            1 / 0
        except:
            r = utilities.error_info(sys.exc_info())
            assert str(r[0]) == "division by zero"
            assert r[1] == "test_utilities.py"


class Test_extract_wav(object):
    @pytest.mark.usefixtures("before")
    def test_wav_from_mp4(self):
        r = utilities.extract_wav(ffmpeg_bin="ffmpeg", media_file_path="files/geese1.mp4", tmp_dir="output")
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
        r = utilities.get_current_points_by_subject(
            point_behaviors_codes=["p"],
            events=pj[config.OBSERVATIONS]["observation #1"]["events"],
            subjects=pj["subjects_conf"],
            time=Decimal("3"),
            tolerance=Decimal("3"),
        )
        assert r == {"0": [], "1": []}

    def test_events_with_modifiers1(self):
        pj_float = json.loads(open("files/test.boris").read())
        pj = utilities.convert_time_to_decimal(pj_float)
        r = utilities.get_current_points_by_subject(
            point_behaviors_codes=["p"],
            events=pj[config.OBSERVATIONS]["offset positif"]["events"],
            subjects={"0": {"key": "", "name": "", "description": "no focal subject"}},
            time=Decimal("22.000"),
            tolerance=Decimal("1"),
            include_modifiers=True,
        )
        assert r == {"0": [("p", "")]}

    def test_events_with_modifiers2(self):
        # no events should correspond to selected behavior
        pj_float = json.loads(open("files/test.boris").read())
        pj = utilities.convert_time_to_decimal(pj_float)
        r = utilities.get_current_points_by_subject(
            point_behaviors_codes=["p"],
            events=pj[config.OBSERVATIONS]["modifiers"][config.EVENTS],
            subjects={"0": {"key": "", "name": "", "description": "no focal subject"}},
            time=Decimal("8.000"),
            tolerance=Decimal("5"),
            include_modifiers=True,
        )
        assert r == {"0": []}

    def test_events_with_modifiers3(self):
        # no events should correspond to selected behavior
        pj_float = json.loads(open("files/test.boris").read())
        pj = utilities.convert_time_to_decimal(pj_float)
        r = utilities.get_current_points_by_subject(
            point_behaviors_codes=["q"],
            events=pj[config.OBSERVATIONS]["modifiers"][config.EVENTS],
            subjects={"0": {"key": "", "name": "", "description": "no focal subject"}},
            time=Decimal("8.000"),
            tolerance=Decimal("5"),
            include_modifiers=True,
        )
        assert r == {"0": [("q", "m1"), ("q", "m2")]}

    def test_events_without_modifiers1(self):
        pj_float = json.loads(open("files/test.boris").read())
        pj = utilities.convert_time_to_decimal(pj_float)
        r = utilities.get_current_points_by_subject(
            point_behaviors_codes=["p"],
            events=pj[config.OBSERVATIONS]["offset positif"]["events"],
            subjects={"0": {"key": "", "name": "", "description": "no focal subject"}},
            time=Decimal("22.000"),
            tolerance=Decimal("1"),
            include_modifiers=False,
        )
        assert r == {"0": [("p", "")]}

    def test_events_without_modifiers2(self):
        pj_float = json.loads(open("files/test.boris").read())
        pj = utilities.convert_time_to_decimal(pj_float)
        r = utilities.get_current_points_by_subject(
            point_behaviors_codes=["p"],
            events=pj[config.OBSERVATIONS]["modifiers"]["events"],
            subjects={"0": {"key": "", "name": "", "description": "no focal subject"}},
            time=Decimal("8.000"),
            tolerance=Decimal("5"),
            include_modifiers=True,
        )
        assert r == {"0": []}


class Test_get_current_states_by_subject(object):
    def test_t0(self):
        pj_float = json.loads(open("files/test.boris").read())
        pj = utilities.convert_time_to_decimal(pj_float)
        r = utilities.get_current_states_modifiers_by_subject(
            state_behaviors_codes=["s"],
            events=pj["observations"]["observation #1"]["events"],
            subjects=pj["subjects_conf"],
            time=Decimal("0"),
            include_modifiers=False,
        )
        assert r == {"0": [], "1": []}

    def test_t4(self):
        pj_float = json.loads(open("files/test.boris").read())
        pj = utilities.convert_time_to_decimal(pj_float)
        r = utilities.get_current_states_modifiers_by_subject(
            state_behaviors_codes=["s"],
            events=pj["observations"]["observation #1"]["events"],
            subjects=pj["subjects_conf"],
            time=Decimal("4.0"),
            include_modifiers=False,
        )
        assert r == {"0": ["s"], "1": []}

    def test_t8(self):
        pj_float = json.loads(open("files/test.boris").read())
        pj = utilities.convert_time_to_decimal(pj_float)
        r = utilities.get_current_states_modifiers_by_subject(
            state_behaviors_codes=["s"],
            events=pj["observations"]["observation #1"]["events"],
            subjects=pj["subjects_conf"],
            time=Decimal("8.0"),
            include_modifiers=False,
        )
        assert r == {"0": [], "1": []}

    def test_t_neg(self):
        pj_float = json.loads(open("files/test.boris").read())
        pj = utilities.convert_time_to_decimal(pj_float)
        r = utilities.get_current_states_modifiers_by_subject(
            state_behaviors_codes=["s"],
            events=pj["observations"]["observation #1"]["events"],
            subjects=pj["subjects_conf"],
            time=Decimal("-12.456"),
            include_modifiers=False,
        )
        # print(r)
        assert r == {"0": [], "1": []}

    def test_no_state_events(self):
        pj_float = json.loads(open("files/test.boris").read())
        pj = utilities.convert_time_to_decimal(pj_float)
        r = utilities.get_current_states_modifiers_by_subject(
            state_behaviors_codes=["s"],
            events=pj["observations"]["offset positif"]["events"],
            subjects=pj["subjects_conf"],
            time=Decimal("30"),
            include_modifiers=False,
        )
        # print(r)
        assert r == {"0": [], "1": []}

    def test_events_with_modifiers_not_required(self):
        pj_float = json.loads(open("files/test.boris").read())
        pj = utilities.convert_time_to_decimal(pj_float)
        r = utilities.get_current_states_modifiers_by_subject(
            state_behaviors_codes=["r", "s"],
            events=pj["observations"]["modifiers"]["events"],
            subjects={"0": {"key": "", "name": "", "description": "no focal subject"}},
            time=Decimal("20"),
            include_modifiers=False,
        )
        # print(r)
        assert r == {"0": ["r"]}

    def test_events_with_modifiers_required(self):
        pj_float = json.loads(open("files/test.boris").read())
        pj = utilities.convert_time_to_decimal(pj_float)
        r = utilities.get_current_states_modifiers_by_subject(
            state_behaviors_codes=["r", "s"],
            events=pj["observations"]["modifiers"]["events"],
            subjects={"0": {"key": "", "name": "", "description": "no focal subject"}},
            time=Decimal("20"),
            include_modifiers=True,
        )
        # print(r)
        assert r == {"0": ["r (m1)"]}


"""
class Test_get_ip_address(object):
    def test_1(self):
        print(utilities.get_ip_address())
        assert False
"""


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
        assert round(utilities.polygon_area([(0, 0), (90, 0), (0, 90), (90, 90)])) == 0


class Test_return_file_header(object):
    def test_file_ok(self):
        r = utilities.return_file_header("files/test_export_events_tabular.tsv")
        # print(r)
        assert r == [
            "Observation id\tobservation #1\t\t\t\t\t\t\t\n",
            "\t\t\t\t\t\t\t\t\n",
            "Media file(s)\t\t\t\t\t\t\t\t\n",
            "\t\t\t\t\t\t\t\t\n",
            "Player #1\tvideo_test_25fps_360s.mp4\t\t\t\t\t\t\t\n",
        ]

    def test_no_file(self):
        r = utilities.return_file_header("files/xxx")
        assert r == []

    def test_short_file(self):
        r = utilities.return_file_header("files/Test_events_to_behavioral_sequences_test_5_observation_not_paired")
        assert r == ["p|s|s+p|s+p|p|s|s+p|s|s", "", "", "", ""]


class Test_safefilename(object):
    def test_filename_with_spaces(self):
        assert utilities.safeFileName("aaa bbb.ccc") == "aaa bbb.ccc"

    def test_filename_with_forbidden_chars(self):
        # ["/", "\\", ":", "*", "?", '"', "<", ">", "|"]
        assert utilities.safeFileName('aaa/bb\\b.c:cc ddd* ? "www" <> |') == "aaa_bb_b.c_cc ddd_ _ _www_ __ _"


class Test_safe_xl_worksheet_title(object):
    def test_long_title_xls(self):
        assert (
            utilities.safe_xl_worksheet_title("0123456789012345678901234567890123456789", "xls")
            == "0123456789012345678901234567890"
        )

    def test_long_title_xlsx(self):
        assert (
            utilities.safe_xl_worksheet_title("0123456789012345678901234567890123456789", "xlsx")
            == "0123456789012345678901234567890123456789"
        )

    def test_long_title_tsv(self):
        assert (
            utilities.safe_xl_worksheet_title("0123456789012345678901234567890123456789", "tsv")
            == "0123456789012345678901234567890123456789"
        )

    def test_title_with_forbidden_chars_xls(self):
        # \/*[]:?
        assert (
            utilities.safe_xl_worksheet_title(r"000\000/000*000[000]000:000?000 000", "xls")
            == "000 000 000 000 000 000 000 000"
        )

    def test_title_with_forbidden_chars_xlsx(self):
        # \/*[]:?
        assert (
            utilities.safe_xl_worksheet_title(r"000\000/000*000[000]000:000?000 000", "xls")
            == "000 000 000 000 000 000 000 000"
        )


class Test_seconds_of_day(object):
    def test1(self):
        assert utilities.seconds_of_day(datetime.datetime(2002, 12, 25, 0, 0, 10, 123)) == Decimal("10.000")

    def test2(self):
        assert utilities.seconds_of_day(datetime.datetime(2002, 12, 25, 0, 0, 10, 123000)) == Decimal("10.123")

    def test3(self):
        assert utilities.seconds_of_day(datetime.datetime(2002, 12, 25, 1, 2, 3, 654321)) == Decimal("3723.654")


class Test_seconds2time(object):
    def test_negative(self):
        assert utilities.seconds2time(Decimal(-2.123)) == "-00:00:02.123"

    def test_gt_86400(self):
        assert utilities.seconds2time(Decimal(86400.999)) == "24:00:00.999"

    def test_10(self):
        assert utilities.seconds2time(Decimal(10.0)) == "00:00:10.000"


class Test_sorted_keys(object):
    def test_numeric_keys(self):
        r = utilities.sorted_keys({5: "a", 4: "7", 0: "z", 6: "a"})
        assert r == ["0", "4", "5", "6"]

    def test_str_keys(self):
        r = utilities.sorted_keys({"10": "x", "0": "x", "1": "x", "11": "x", "05": "x"})
        assert r == ["0", "1", "5", "10", "11"]

    def test_empty_dict(self):
        r = utilities.sorted_keys({})
        assert r == []


class Test_state_behavior_codes(object):
    def test_1(self):
        pj_float = json.loads(open("files/test.boris").read())
        r = utilities.state_behavior_codes(pj_float["behaviors_conf"])
        # print(r)
        assert r == ["s", "r", "m"]

    def test_empty_ethogram(self):
        r = utilities.state_behavior_codes({})
        assert r == []


class Test_test_ffmpeg_path(object):
    def test_path_ok(self):
        r = utilities.test_ffmpeg_path("ffmpeg")
        # print(r)
        assert r == (True, "")

    def test_path_do_no_exist(self):
        r = utilities.test_ffmpeg_path("xxx/ffmpeg")
        # print(r)
        assert r == (False, "FFmpeg is required but it was not found...<br>See https://www.ffmpeg.org")


class Test_time2seconds(object):
    def test_positive(self):
        assert utilities.time2seconds("11:22:33.44") == Decimal("40953.44")

    def test_negative(self):
        assert utilities.time2seconds("-11:22:33.44") == Decimal("-40953.44")

    def test_zero(self):
        assert utilities.time2seconds("00:00:00.000") == Decimal("0.000")

    def test_wrong_input(self):
        assert utilities.time2seconds("aaaaa") == Decimal("0.000")


class Test_txt2np_array(object):
    def test_no_file(self):
        r = utilities.txt2np_array(
            file_name="files/xxx", columns_str="4,6", substract_first_value="False", converters={}, column_converter={}
        )
        # print(r)
        assert r[0] == False
        assert r[1] == "[Errno 2] No such file or directory: 'files/xxx'"
        assert list(r[2].shape) == [0]

    def test_file_csv_no_converter(self):
        r = utilities.txt2np_array(
            file_name="files/test_check_txt_file_test_csv.csv",
            columns_str="4,6",
            substract_first_value="False",
            converters={},
            column_converter={},
        )
        assert r[0] == False
        assert r[1] == "could not convert string to float: '14:38:58'"
        assert list(r[2].shape) == [0]

    def test_file_csv_converter(self):
        r = utilities.txt2np_array(
            file_name="files/test_check_txt_file_test_csv.csv",
            columns_str="4,6",
            substract_first_value="False",
            converters={
                "HHMMSS_2_seconds": {
                    "name": "HHMMSS_2_seconds",
                    "description": "convert HH:MM:SS in seconds since 1970-01-01",
                    "code": "\nh, m, s = INPUT.split(':')\nOUTPUT = int(h) * 3600 + int(m) * 60 + int(s)\n\n",
                }
            },
            column_converter={4: "HHMMSS_2_seconds"},
        )
        assert r[0] == True
        assert r[1] == ""
        assert r[2][0, 0] == 52738.0
        assert r[2][1, 0] == 52740.0
        assert r[2][0, 1] == 12.4144278
        assert list(r[2].shape) == [10658, 2]


class Test_url2path(object):
    def test_1(self):
        assert utilities.url2path("file:///home/olivier/v%C3%A9lo/test") == "/home/olivier/vélo/test"


class Test_versiontuple(object):
    def test_1(self):
        r = utilities.versiontuple("1.2.3")
        assert r == ("00000001", "00000002", "00000003")

    def test_2(self):
        r = utilities.versiontuple("1.2")
        assert r == ("00000001", "00000002")

    def test_3(self):
        r = utilities.versiontuple("1")
        assert r == ("00000001",)

    def test_4(self):
        r = utilities.versiontuple("")
        assert r == ("00000000",)
