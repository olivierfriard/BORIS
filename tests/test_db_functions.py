"""
module for testing db_functions.py
"""

import db_functions

import os
import sys
import project_functions
from config import *
import subprocess

_, _, pj, _ = project_functions.open_project_json("test.boris")


def test_load_events_1():
    cursor = db_functions.load_events_in_db(pj, ["subject1"], ["observation #1"], ["s"])
    cursor.execute("SELECT occurence FROM events WHERE observation = ? AND subject = ? AND code = ?", ("observation #1", "subject1", "s"))
    out = ""
    for r in cursor.fetchall():
        out += '{}\n'.format(r[0])

    REF = """3.3
7.75
9.9
16.2
18.35
24.475
"""
    assert out ==  REF


def test_load_events_2():
    cursor = db_functions.load_events_in_db(pj, ["subject2"], ["live"], ["s", "p"])
    cursor.execute("SELECT occurence FROM events WHERE observation = ? AND subject = ? AND code = ?", ("live", "subject2", "s"))
    out = ""
    for r in cursor.fetchall():
        out += '{}\n'.format(r[0])

    REF = """12.509
20.685
"""

    assert out ==  REF
    return out

def test_load_events_3():
    cursor = db_functions.load_events_in_db(pj, ["No focal subject"], ["live not paired"], ["s", "p"])
    cursor.execute("SELECT occurence FROM events WHERE observation = ? AND subject = ? AND code = ?", ("live not paired", "No focal subject", "s"))
    out = ""
    for r in cursor.fetchall():
        out += '{}\n'.format(r[0])

    REF = """2.718
10.478
12.926
17.47
19.502
24.318
26.862
"""

    assert out ==  REF
    return out


def test_load_aggregated_events_1():
    ok, msg, db = db_functions.load_aggregated_events_in_db(pj, [], ["observation #1", "observation #2"], [])
    out = ""
    for line in db.iterdump():
        out += line + "\n"

    REF ="""BEGIN TRANSACTION;
CREATE TABLE aggregated_events
                              (id INTEGER PRIMARY KEY ASC,
                               observation TEXT,
                               subject TEXT,
                               behavior TEXT,
                               type TEXT,
                               modifiers TEXT,
                               start FLOAT,
                               stop FLOAT,
                               comment TEXT);
INSERT INTO "aggregated_events" VALUES(1,'observation #1','subject1','s','STATE','',3.3,7.75,NULL);
INSERT INTO "aggregated_events" VALUES(2,'observation #1','subject1','s','STATE','',9.9,16.2,NULL);
INSERT INTO "aggregated_events" VALUES(3,'observation #1','subject1','s','STATE','',18.35,24.475,NULL);
INSERT INTO "aggregated_events" VALUES(4,'observation #1','subject2','s','STATE','',38.425,46.1,NULL);
INSERT INTO "aggregated_events" VALUES(5,'observation #2','No focal subject','p','POINT','',32.825,32.825,NULL);
INSERT INTO "aggregated_events" VALUES(6,'observation #2','No focal subject','p','POINT','',34.15,34.15,NULL);
INSERT INTO "aggregated_events" VALUES(7,'observation #2','No focal subject','p','POINT','',34.925,34.925,NULL);
INSERT INTO "aggregated_events" VALUES(8,'observation #2','No focal subject','p','POINT','',299.715,299.715,NULL);
INSERT INTO "aggregated_events" VALUES(9,'observation #2','No focal subject','p','POINT','',301.34,301.34,NULL);
INSERT INTO "aggregated_events" VALUES(10,'observation #2','No focal subject','p','POINT','',303.24,303.24,NULL);
INSERT INTO "aggregated_events" VALUES(11,'observation #2','No focal subject','s','STATE','',1.8,8.125,NULL);
INSERT INTO "aggregated_events" VALUES(12,'observation #2','No focal subject','s','STATE','',10.25,23.35,NULL);
INSERT INTO "aggregated_events" VALUES(13,'observation #2','No focal subject','s','STATE','',26.775,31.475,NULL);
INSERT INTO "aggregated_events" VALUES(14,'observation #2','No focal subject','s','STATE','',227.765,253.49,NULL);
INSERT INTO "aggregated_events" VALUES(15,'observation #2','No focal subject','s','STATE','',255.34,261.14,NULL);
INSERT INTO "aggregated_events" VALUES(16,'observation #2','No focal subject','s','STATE','',303.79,307.765,NULL);
INSERT INTO "aggregated_events" VALUES(17,'observation #2','subject1','s','STATE','',266.165,276.69,NULL);
INSERT INTO "aggregated_events" VALUES(18,'observation #2','subject1','s','STATE','',280.965,294.215,NULL);
INSERT INTO "aggregated_events" VALUES(19,'observation #2','subject2','p','POINT','',314.49,314.49,NULL);
INSERT INTO "aggregated_events" VALUES(20,'observation #2','subject2','p','POINT','',316.065,316.065,NULL);
INSERT INTO "aggregated_events" VALUES(21,'observation #2','subject2','s','STATE','',286.215,292.065,NULL);
INSERT INTO "aggregated_events" VALUES(22,'observation #2','subject2','s','STATE','',317.39,320.365,NULL);
COMMIT;
"""

    assert out == REF
    return out


def test_load_aggregated_events_2():
    ok, msg, db = db_functions.load_aggregated_events_in_db(pj, [], ["live not paired"], [])
    assert ok == False
    return ok

for f in [test_load_events_1,
          test_load_events_2,
          test_load_events_3,
          test_load_aggregated_events_1,
          test_load_aggregated_events_2]:
    print(f)
    print(f())
    print("=====================================")
