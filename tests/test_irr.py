"""
module for testing time budget analysis

pytest -s -vv test_irr.py
"""

import pytest
import sys
import json
import os
sys.path.append("../src")

import irr
import db_functions
from config import *
import decimal


@pytest.fixture()
def before():
    os.system("rm -rf output")
    os.system("mkdir output")

class Test_irr(object):

    def test_irr1(self):

        pj = json.loads(open("files/test.boris").read())

        ethogram = pj[ETHOGRAM]
        selected_observations = ["observation #1", "observation #1"]
        selected_subjects = ["subject1", "subject2"]

        r, s, db = cursor = db_functions.load_aggregated_events_in_db(pj,
                                              selected_subjects,
                                              selected_observations,
                                              ["s"])
        assert r == True

        cursor = db.cursor()
        K, msg = irr.cohen_kappa(cursor,
                               obsid1 = selected_observations[0],
                               obsid2 = selected_observations[1],
                               interval = decimal.Decimal("1.0"),
                               selected_subjects = selected_subjects,
                               include_modifiers = False)


        assert K == 1



    def test_irr2(self):

        pj = json.loads(open("files/test.boris").read())

        ethogram = pj[ETHOGRAM]
        selected_observations = ["observation #1", "observation #2"]
        selected_subjects = ["subject1", "subject2"]

        parameters = {"selected subjects": ["subject1", "subject2"],
                      "selected behaviors": ["p", "s"],
                      INCLUDE_MODIFIERS: False,
                      EXCLUDE_BEHAVIORS: False,
                      "start time": 0,
                      "end time": 100.0}

        r, s, db = cursor = db_functions.load_aggregated_events_in_db(pj,
                                              selected_subjects,
                                              selected_observations,
                                              ["s"])

        cursor = db.cursor()
        K, msg = irr.cohen_kappa(cursor,
                               obsid1 = selected_observations[0],
                               obsid2 = selected_observations[1],
                               interval = decimal.Decimal("1.0"),
                               selected_subjects = selected_subjects,
                               include_modifiers = False)


        assert K == -0.036

