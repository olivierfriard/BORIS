"""
BORIS
Behavioral Observation Research Interactive Software
Copyright 2012-2022 Olivier Friard

module for testing db_functions.py

pytest -vv test_db_functions.py
"""

import os
import sys
import json

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from boris import db_functions


class Test_load_events_in_db(object):
    def test_1(self):

        pj = json.loads(open("files/test.boris").read())

        cursor = db_functions.load_events_in_db(pj, ["subject1"], ["observation #1"], ["s"])
        cursor.execute(
            "SELECT occurence FROM events WHERE observation = ? AND subject = ? AND code = ?",
            ("observation #1", "subject1", "s"),
        )
        out = ""
        for r in cursor.fetchall():
            out += "{}\n".format(r[0])

        REF = """3.3\n7.75\n9.9\n16.2\n18.35\n24.475\n"""
        assert out == REF

    def test_2(self):

        pj = json.loads(open("files/test.boris").read())

        cursor = db_functions.load_events_in_db(pj, ["subject2"], ["live"], ["s", "p"])
        cursor.execute(
            "SELECT occurence FROM events WHERE observation = ? AND subject = ? AND code = ?", ("live", "subject2", "s")
        )
        out = ""
        for r in cursor.fetchall():
            out += "{}\n".format(r[0])

        REF = """12.509\n20.685\n"""

        assert out == REF

    def test_3(self):
        """
        no focal subject, observation with not paired events
        """

        pj = json.loads(open("files/test.boris").read())

        cursor = db_functions.load_events_in_db(pj, ["No focal subject"], ["live not paired"], ["s", "p"])
        cursor.execute(
            "SELECT occurence FROM events WHERE observation = ? AND subject = ? AND code = ?",
            ("live not paired", "No focal subject", "s"),
        )
        out = ""
        for r in cursor.fetchall():
            out += "{}\n".format(r[0])

        REF = """2.718\n10.478\n12.926\n17.47\n19.502\n24.318\n26.862\n"""

        assert out == REF


class Test_load_aggregated_events_in_db(object):
    def test_dump(self):

        pj = json.loads(open("files/test.boris").read())

        ok, msg, db = db_functions.load_aggregated_events_in_db(pj, [], ["observation #1", "observation #2"], [])
        out = ""
        for line in db.iterdump():
            out += line + "\n"

        print(out == open("files/test_db_functions_test1").read())

    def test_not_ok(self):
        """
        test with observation with state events NOT PAIRED
        """

        pj = json.loads(open("files/test.boris").read())

        ok, msg, db = db_functions.load_aggregated_events_in_db(pj, [], ["live not paired"], [])

        assert ok == False

    def test_no_observation(self):
        """
        test with no observation
        """

        pj = json.loads(open("files/test.boris").read())

        ok, msg, db = db_functions.load_aggregated_events_in_db(pj, [], [], [])

        assert ok == False
