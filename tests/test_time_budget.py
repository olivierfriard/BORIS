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

    def test_time_budget1(self):

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
        assert json.loads(open("files/test_time_budget1.json").read()) == out

