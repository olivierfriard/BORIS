"""
module for testing time budget analysis

pytest -s -vv test_time_budget.py
"""

import pytest
import sys
import json
import os

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

print(sys.path)

from boris import time_budget_functions
from boris import db_functions
from boris import config


@pytest.fixture()
def before():
    os.system("rm -rf output")
    os.system("mkdir output")


class Test_time_budget(object):
    """
    start and end times are not taken into account
    """

    def test_time_budget1(self):
        VERIF = [
            {
                "subject": "subject1",
                "behavior": "p",
                "modifiers": "",
                "duration": "NA",
                "duration_mean": "NA",
                "duration_stdev": "NA",
                "number": "0",
                "inter_duration_mean": "NA",
                "inter_duration_stdev": "NA",
            },
            {
                "subject": "subject1",
                "behavior": "s",
                "modifiers": "",
                "duration": 16.875,
                "duration_mean": 5.625,
                "duration_stdev": 1.021,
                "number": 3,
                "inter_duration_mean": 2.15,
                "inter_duration_stdev": 0.0,
            },
            {
                "subject": "subject2",
                "behavior": "p",
                "modifiers": "",
                "duration": "NA",
                "duration_mean": "NA",
                "duration_stdev": "NA",
                "number": "0",
                "inter_duration_mean": "NA",
                "inter_duration_stdev": "NA",
            },
            {
                "subject": "subject2",
                "behavior": "s",
                "modifiers": "",
                "duration": 7.675,
                "duration_mean": 7.675,
                "duration_stdev": "NA",
                "number": 1,
                "inter_duration_mean": "NA",
                "inter_duration_stdev": "NA",
            },
        ]

        pj = json.loads(open("files/test.boris").read())

        ethogram = pj[config.ETHOGRAM]
        selected_observations = ["observation #1"]
        parameters = {
            config.SELECTED_SUBJECTS: ["subject1", "subject2"],
            config.SELECTED_BEHAVIORS: ["p", "s"],
            config.INCLUDE_MODIFIERS: False,
            config.EXCLUDE_BEHAVIORS: False,
            "start time": 0,
            "end time": 100.0,
        }

        cursor = db_functions.load_events_in_db(
            pj, parameters[config.SELECTED_SUBJECTS], selected_observations, parameters[config.SELECTED_BEHAVIORS]
        )

        out, categories = time_budget_functions.time_budget_analysis(ethogram, cursor, selected_observations, parameters, by_category=False)

        #  open("/tmp/test_time_budget1.json", "w").write(json.dumps(out))
        assert out == VERIF

    def test_time_budget2(self):
        VERIF = [
            {
                "subject": "subject1",
                "behavior": "p",
                "modifiers": "",
                "duration": "NA",
                "duration_mean": "NA",
                "duration_stdev": "NA",
                "number": "0",
                "inter_duration_mean": "NA",
                "inter_duration_stdev": "NA",
            },
            {
                "subject": "subject2",
                "behavior": "p",
                "modifiers": "",
                "duration": "NA",
                "duration_mean": "NA",
                "duration_stdev": "NA",
                "number": 2,
                "inter_duration_mean": 0.0,
                "inter_duration_stdev": "NA",
            },
        ]

        pj = json.loads(open("files/test.boris").read())

        ethogram = pj[config.ETHOGRAM]
        selected_observations = ["observation #2"]
        parameters = {
            config.SELECTED_SUBJECTS: ["subject1", "subject2"],
            config.SELECTED_BEHAVIORS: ["p"],
            config.INCLUDE_MODIFIERS: False,
            config.EXCLUDE_BEHAVIORS: False,
            "start time": 0,
            "end time": 100.0,
        }

        cursor = db_functions.load_events_in_db(
            pj, parameters[config.SELECTED_SUBJECTS], selected_observations, parameters[config.SELECTED_BEHAVIORS]
        )

        out, categories = time_budget_functions.time_budget_analysis(ethogram, cursor, selected_observations, parameters, by_category=False)

        # open("/tmp/test_time_budget2.json", "w").write(json.dumps(out))

        assert out == VERIF

    def test_time_budget3(self):
        VERIF = [
            {
                "subject": "No focal subject",
                "behavior": "s",
                "modifiers": "",
                "duration": 59.625,
                "duration_mean": 9.937,
                "duration_stdev": 8.395,
                "number": 6,
                "inter_duration_mean": 49.268,
                "inter_duration_stdev": 84.012,
            },
            {
                "subject": "No focal subject",
                "behavior": "p",
                "modifiers": "",
                "duration": "NA",
                "duration_mean": "NA",
                "duration_stdev": "NA",
                "number": 6,
                "inter_duration_mean": 54.083,
                "inter_duration_stdev": 117.79,
            },
        ]

        pj = json.loads(open("files/test.boris").read())

        ethogram = pj[config.ETHOGRAM]
        selected_observations = ["observation #2"]
        parameters = {
            config.SELECTED_SUBJECTS: ["No focal subject"],
            config.SELECTED_BEHAVIORS: ["s", "p"],
            config.INCLUDE_MODIFIERS: True,
            config.EXCLUDE_BEHAVIORS: True,
            "start time": 0,
            "end time": 320.0,
        }

        cursor = db_functions.load_events_in_db(
            pj, parameters[config.SELECTED_SUBJECTS], selected_observations, parameters[config.SELECTED_BEHAVIORS]
        )

        out, categories = time_budget_functions.time_budget_analysis(ethogram, cursor, selected_observations, parameters, by_category=False)

        # open("/tmp/test_time_budget3.json", "w").write(json.dumps(out))

        assert out == VERIF

    def test_time_budget4(self):
        VERIF = [
            {
                "subject": "No focal subject",
                "behavior": "s",
                "modifiers": "",
                "duration": "UNPAIRED",
                "duration_mean": "UNPAIRED",
                "duration_stdev": "UNPAIRED",
                "number": "UNPAIRED",
                "inter_duration_mean": "UNPAIRED",
                "inter_duration_stdev": "UNPAIRED",
            },
            {
                "subject": "No focal subject",
                "behavior": "p",
                "modifiers": "",
                "duration": "NA",
                "duration_mean": "NA",
                "duration_stdev": "NA",
                "number": 5,
                "inter_duration_mean": 3.272,
                "inter_duration_stdev": 0.309,
            },
        ]

        pj = json.loads(open("files/test.boris").read())

        ethogram = pj[config.ETHOGRAM]
        selected_observations = ["live not paired"]
        parameters = {
            config.SELECTED_SUBJECTS: ["No focal subject"],
            config.SELECTED_BEHAVIORS: ["s", "p"],
            config.INCLUDE_MODIFIERS: True,
            config.EXCLUDE_BEHAVIORS: True,
            "start time": 0,
            "end time": 26.862,
        }

        cursor = db_functions.load_events_in_db(
            pj, parameters[config.SELECTED_SUBJECTS], selected_observations, parameters[config.SELECTED_BEHAVIORS]
        )

        out, categories = time_budget_functions.time_budget_analysis(ethogram, cursor, selected_observations, parameters, by_category=False)

        # open("/tmp/test_time_budget4.json", "w").write(json.dumps(out))

        assert out == VERIF

    def test_time_budget5(self):
        """
        test time budget with modifiers
        """

        VERIF = [
            {
                "subject": "No focal subject",
                "behavior": "q",
                "modifiers": "m1",
                "duration": "NA",
                "duration_mean": "NA",
                "duration_stdev": "NA",
                "number": 1,
                "inter_duration_mean": "NA",
                "inter_duration_stdev": "NA",
            },
            {
                "subject": "No focal subject",
                "behavior": "q",
                "modifiers": "m2",
                "duration": "NA",
                "duration_mean": "NA",
                "duration_stdev": "NA",
                "number": 1,
                "inter_duration_mean": "NA",
                "inter_duration_stdev": "NA",
            },
            {
                "subject": "No focal subject",
                "behavior": "q",
                "modifiers": "m3",
                "duration": "NA",
                "duration_mean": "NA",
                "duration_stdev": "NA",
                "number": 1,
                "inter_duration_mean": "NA",
                "inter_duration_stdev": "NA",
            },
            {
                "subject": "No focal subject",
                "behavior": "r",
                "modifiers": "m1",
                "duration": 8.775,
                "duration_mean": 8.775,
                "duration_stdev": "NA",
                "number": 1,
                "inter_duration_mean": "NA",
                "inter_duration_stdev": "NA",
            },
            {
                "subject": "No focal subject",
                "behavior": "r",
                "modifiers": "None",
                "duration": 10.4,
                "duration_mean": 10.4,
                "duration_stdev": "NA",
                "number": 1,
                "inter_duration_mean": "NA",
                "inter_duration_stdev": "NA",
            },
        ]

        pj = json.loads(open("files/test.boris").read())

        ethogram = pj[config.ETHOGRAM]
        selected_observations = ["modifiers"]
        parameters = {
            config.SELECTED_SUBJECTS: ["No focal subject"],
            config.SELECTED_BEHAVIORS: ["q", "r"],
            config.INCLUDE_MODIFIERS: True,
            config.EXCLUDE_BEHAVIORS: False,
            "start time": 0,
            "end time": 180,
        }

        cursor = db_functions.load_events_in_db(
            pj,
            parameters[config.SELECTED_SUBJECTS],
            selected_observations,
            parameters[config.SELECTED_BEHAVIORS],
            time_interval=config.TIME_ARBITRARY_INTERVAL,
        )

        out, categories = time_budget_functions.time_budget_analysis(ethogram, cursor, selected_observations, parameters, by_category=False)

        # open("/tmp/test_time_budget5.json", "w").write(json.dumps(out))

        assert out == VERIF
