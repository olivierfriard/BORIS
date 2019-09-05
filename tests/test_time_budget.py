"""
module for testing time budget analysis

pytest -s -vv test_time_budget.py
"""

import pytest
import sys
import json
import os
sys.path.append("../src")

import time_budget_functions
import db_functions
from config import *


@pytest.fixture()
def before():
    os.system("rm -rf output")
    os.system("mkdir output")

class Test_time_budget(object):

    """
    start and end times are not taken into account
    """
  
    def test_time_budget1(self):
        

        VERIF = [{"subject": "subject1", "behavior": "p", "modifiers": "", "duration": 0, "duration_mean": 0, "duration_stdev": "NA", "number": "0", "inter_duration_mean": "NA", "inter_duration_stdev": "NA"}, {"subject": "subject1", "behavior": "s", "modifiers": "", "duration": 16.875, "duration_mean": 5.625, "duration_stdev": 1.021, "number": 3, "inter_duration_mean": 2.15, "inter_duration_stdev": 0.0}, {"subject": "subject2", "behavior": "p", "modifiers": "", "duration": 0, "duration_mean": 0, "duration_stdev": "NA", "number": "0", "inter_duration_mean": "NA", "inter_duration_stdev": "NA"}, {"subject": "subject2", "behavior": "s", "modifiers": "", "duration": 7.675, "duration_mean": 7.675, "duration_stdev": "NA", "number": 1, "inter_duration_mean": "NA", "inter_duration_stdev": "NA"}]

        pj = json.loads(open("files/test.boris").read())

        ethogram = pj[ETHOGRAM]
        selected_observations = ["observation #1"]
        parameters = {"selected subjects": ["subject1", "subject2"],
                      "selected behaviors": ["p", "s"],
                      INCLUDE_MODIFIERS: False,
                      EXCLUDE_BEHAVIORS: False,
                      "start time": 0,
                      "end time": 100.0}

        cursor = db_functions.load_events_in_db(pj,
                                                parameters[SELECTED_SUBJECTS],
                                                selected_observations,
                                                parameters[SELECTED_BEHAVIORS])

        out, categories = time_budget_functions.time_budget_analysis(ethogram,
                                                                     cursor,
                                                                     selected_observations,
                                                                     parameters,
                                                                     by_category=False)

        # open("files/test_time_budget1new.json", "w").write(json.dumps(out))
        assert out == VERIF


    def test_time_budget2(self):

        VERIF = [{"subject": "subject1", "behavior": "p", "modifiers": "", "duration": 0, "duration_mean": 0, "duration_stdev": "NA", "number": "0", "inter_duration_mean": "NA", "inter_duration_stdev": "NA"},
        {"subject": "subject2", "behavior": "p", "modifiers": "", "duration": 0, "duration_mean": 0, "duration_stdev": 0, "number": 2, "inter_duration_mean": 0.0, "inter_duration_stdev": "NA"}]

        pj = json.loads(open("files/test.boris").read())

        ethogram = pj[ETHOGRAM]
        selected_observations = ["observation #2"]
        parameters = {SELECTED_SUBJECTS: ["subject1", "subject2"],
                      SELECTED_BEHAVIORS: ["p"],
                      INCLUDE_MODIFIERS: False,
                      EXCLUDE_BEHAVIORS: False,
                      "start time": 0,
                      "end time": 100.0}

        cursor = db_functions.load_events_in_db(pj,
                                                parameters[SELECTED_SUBJECTS],
                                                selected_observations,
                                                parameters[SELECTED_BEHAVIORS])

        out, categories = time_budget_functions.time_budget_analysis(ethogram,
                                                                     cursor,
                                                                     selected_observations,
                                                                     parameters,
                                                                     by_category=False)

        # open("files/test_time_budget2.json", "w").write(json.dumps(out))

        assert out == VERIF



    def test_time_budget3(self):

        VERIF = [{"subject": "No focal subject", "behavior": "s", "modifiers": "", "duration": 59.625, "duration_mean": 9.937,
        "duration_stdev": 8.395, "number": 6, "inter_duration_mean": 49.268, "inter_duration_stdev": 84.012}, 
        {"subject": "No focal subject", "behavior": "p", "modifiers": "", "duration": 0, "duration_mean": 0, 
        "duration_stdev": "NA", "number": 6, "inter_duration_mean": 54.083, "inter_duration_stdev": 117.79}]

        pj = json.loads(open("files/test.boris").read())

        ethogram = pj[ETHOGRAM]
        selected_observations = ["observation #2"]
        parameters = {SELECTED_SUBJECTS: ["No focal subject"],
                      SELECTED_BEHAVIORS: ["s", "p"],
                      INCLUDE_MODIFIERS: True,
                      EXCLUDE_BEHAVIORS: True,
                      "start time": 0,
                      "end time": 320.0}

        cursor = db_functions.load_events_in_db(pj,
                                                parameters[SELECTED_SUBJECTS],
                                                selected_observations,
                                                parameters[SELECTED_BEHAVIORS])

        out, categories = time_budget_functions.time_budget_analysis(ethogram,
                                                                     cursor,
                                                                     selected_observations,
                                                                     parameters,
                                                                     by_category=False)

        # open("files/test_time_budget3.json", "w").write(json.dumps(out))

        assert out == VERIF


    def test_time_budget4(self):

        VERIF = [{"subject": "No focal subject", "behavior": "s", "modifiers": "", "duration": "UNPAIRED", "duration_mean": "UNPAIRED", "duration_stdev": "UNPAIRED", "number": "UNPAIRED", "inter_duration_mean": "UNPAIRED", "inter_duration_stdev": "UNPAIRED"}, {"subject": "No focal subject", "behavior": "p", "modifiers": "", "duration": 0, "duration_mean": 0, "duration_stdev": "NA", "number": 5, "inter_duration_mean": 3.272, "inter_duration_stdev": 0.309}]

        pj = json.loads(open("files/test.boris").read())

        ethogram = pj[ETHOGRAM]
        selected_observations = ["live not paired"]
        parameters = {SELECTED_SUBJECTS: ["No focal subject"],
                      SELECTED_BEHAVIORS: ["s", "p"],
                      INCLUDE_MODIFIERS: True,
                      EXCLUDE_BEHAVIORS: True,
                      "start time": 0,
                      "end time": 26.862}

        cursor = db_functions.load_events_in_db(pj,
                                                parameters[SELECTED_SUBJECTS],
                                                selected_observations,
                                                parameters[SELECTED_BEHAVIORS])

        out, categories = time_budget_functions.time_budget_analysis(ethogram,
                                                                     cursor,
                                                                     selected_observations,
                                                                     parameters,
                                                                     by_category=False)

        # open("files/test_time_budget4.json", "w").write(json.dumps(out))

        assert out == VERIF



    def test_time_budget5(self):
        """
        test time budget with modifiers
        """

        VERIF = [{"subject": "No focal subject", "behavior": "q", "modifiers": "m1", "duration": 0, "duration_mean": 0, "duration_stdev": "NA", "number": 1, "inter_duration_mean": "NA", "inter_duration_stdev": "NA"}, {"subject": "No focal subject", "behavior": "q", "modifiers": "m2", "duration": 0, "duration_mean": 0, "duration_stdev": "NA", "number": 1, "inter_duration_mean": "NA", "inter_duration_stdev": "NA"}, {"subject": "No focal subject", "behavior": "q", "modifiers": "m3", "duration": 0, "duration_mean": 0, "duration_stdev": "NA", "number": 1, "inter_duration_mean": "NA", "inter_duration_stdev": "NA"}, {"subject": "No focal subject", "behavior": "r", "modifiers": "m1", "duration": 8.775, "duration_mean": 8.775, "duration_stdev": "NA", "number": 1, "inter_duration_mean": "NA", "inter_duration_stdev": "NA"}, {"subject": "No focal subject", "behavior": "r", "modifiers": "None", "duration": 10.4, "duration_mean": 10.4, "duration_stdev": "NA", "number": 1, "inter_duration_mean": "NA", "inter_duration_stdev": "NA"}]

        pj = json.loads(open("files/test.boris").read())

        ethogram = pj[ETHOGRAM]
        selected_observations = ["modifiers"]
        parameters = {SELECTED_SUBJECTS: ["No focal subject"],
                      SELECTED_BEHAVIORS: ["q", "r"],
                      INCLUDE_MODIFIERS: True,
                      EXCLUDE_BEHAVIORS: False,
                      "start time": 0,
                      "end time": 180}

        cursor = db_functions.load_events_in_db(pj,
                                                parameters[SELECTED_SUBJECTS],
                                                selected_observations,
                                                parameters[SELECTED_BEHAVIORS],
                                                time_interval=TIME_ARBITRARY_INTERVAL)

        out, categories = time_budget_functions.time_budget_analysis(ethogram,
                                                                     cursor,
                                                                     selected_observations,
                                                                     parameters,
                                                                     by_category=False)

        # open("files/1.json", "w").write(json.dumps(out))

        assert out == VERIF
