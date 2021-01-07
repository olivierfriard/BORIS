"""
BORIS
Behavioral Observation Research Interactive Software
Copyright 2012-2021 Olivier Friard


  This program is free software; you can redistribute it and/or modify
  it under the terms of the GNU General Public License as published by
  the Free Software Foundation; either version 2 of the License, or
  (at your option) any later version.

  This program is distributed in the hope that it will be useful,
  but WITHOUT ANY WARRANTY; without even the implied warranty of
  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
  GNU General Public License for more details.

  You should have received a copy of the GNU General Public License
  along with this program; if not, write to the Free Software
  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
  MA 02110-1301, USA.

"""

import sqlite3
import os
import logging
from boris.config import *
from boris import project_functions

import time


'''
def load_events_in_intervals(pj: dict,
                      selected_subjects: list,
                      selected_observations: list,
                      selected_behaviors: list,
                      time_interval: str = TIME_FULL_OBS):

    intervals = {}
    state_behaviors_codes = [pj[ETHOGRAM][x][BEHAVIOR_CODE] for x in pj[ETHOGRAM]
                                if STATE in pj[ETHOGRAM][x][TYPE].upper()
                                and pj[ETHOGRAM][x][BEHAVIOR_CODE] in selected_behaviors]

    # selected behaviors defined as point event
    point_behaviors_codes = [pj[ETHOGRAM][x][BEHAVIOR_CODE] for x in pj[ETHOGRAM]
                                if POINT in pj[ETHOGRAM][x][TYPE].upper()
                                and pj[ETHOGRAM][x][BEHAVIOR_CODE] in selected_behaviors]

    for subject_to_analyze in selected_subjects:

        for obsId in selected_observations:

            for event in pj[OBSERVATIONS][obsId][EVENTS]:

                if event[EVENT_BEHAVIOR_FIELD_IDX] in selected_behaviors:

                    # extract time, code, modifier and comment (time:0, subject:1, code:2, modifier:3, comment:4)
                    if ((subject_to_analyze == NO_FOCAL_SUBJECT and event[EVENT_SUBJECT_FIELD_IDX] == "") or
                            (event[EVENT_SUBJECT_FIELD_IDX] == subject_to_analyze)):

                        r = cursor.execute(("INSERT INTO events "
                                            "(observation, subject, code, type, modifiers, occurence, comment) "
                                            "VALUES (?,?,?,?,?,?,?)"),
                                           (obsId,
                                            NO_FOCAL_SUBJECT if event[EVENT_SUBJECT_FIELD_IDX] == "" else event[EVENT_SUBJECT_FIELD_IDX],
                                            event[EVENT_BEHAVIOR_FIELD_IDX],
                                            STATE if event[EVENT_BEHAVIOR_FIELD_IDX] in state_behaviors_codes else POINT,
                                            event[EVENT_MODIFIER_FIELD_IDX],
                                            str(event[EVENT_TIME_FIELD_IDX]),
                                            event[EVENT_COMMENT_FIELD_IDX]))

    db.commit()
    return cursor
'''




def load_events_in_db(pj: dict,
                      selected_subjects: list,
                      selected_observations: list,
                      selected_behaviors: list,
                      time_interval: str = TIME_FULL_OBS):
    """
    populate a memory sqlite database with events from selected_observations,
    selected_subjects and selected_behaviors

    Args:
        pj (dict): project dictionary
        selected_observations (list):
        selected_subjects (list):
        selected_behaviors (list):
        time_interval (str): time interval for loading events (TIME_FULL_OBS / TIME_EVENTS / TIME_ARBITRARY_INTERVAL)

    Returns:
        database cursor:

    """

    # selected behaviors defined as state event
    state_behaviors_codes = [pj[ETHOGRAM][x][BEHAVIOR_CODE] for x in pj[ETHOGRAM]
                                 if STATE in pj[ETHOGRAM][x][TYPE].upper()
                                    and pj[ETHOGRAM][x][BEHAVIOR_CODE] in selected_behaviors]

    # selected behaviors defined as point event
    point_behaviors_codes = [pj[ETHOGRAM][x][BEHAVIOR_CODE] for x in pj[ETHOGRAM]
                                 if POINT in pj[ETHOGRAM][x][TYPE].upper()
                                    and pj[ETHOGRAM][x][BEHAVIOR_CODE] in selected_behaviors]

    db = sqlite3.connect(":memory:", isolation_level=None)
    # db = sqlite3.connect("/tmp/1.sqlite", isolation_level=None)

    db.row_factory = sqlite3.Row
    cursor = db.cursor()
    cursor.execute(("CREATE TABLE events (observation TEXT, "
                    "subject TEXT, "
                    "code TEXT, "
                    "type TEXT, "
                    "modifiers TEXT, "
                    "occurence FLOAT, "
                    "comment TEXT)"))

    cursor.execute("CREATE INDEX observation_idx ON events(observation)")
    cursor.execute("CREATE INDEX subject_idx ON events(subject)")
    cursor.execute("CREATE INDEX code_idx ON events(code)")
    cursor.execute("CREATE INDEX modifiers_idx ON events(modifiers)")

    for subject_to_analyze in selected_subjects:

        for obsId in selected_observations:

            for event in pj[OBSERVATIONS][obsId][EVENTS]:

                if event[EVENT_BEHAVIOR_FIELD_IDX] in selected_behaviors:

                    # extract time, code, modifier and comment (time:0, subject:1, code:2, modifier:3, comment:4)
                    if ((subject_to_analyze == NO_FOCAL_SUBJECT and event[EVENT_SUBJECT_FIELD_IDX] == "") or
                            (event[EVENT_SUBJECT_FIELD_IDX] == subject_to_analyze)):

                        r = cursor.execute(("INSERT INTO events "
                                            "(observation, subject, code, type, modifiers, occurence, comment) "
                                            "VALUES (?,?,?,?,?,?,?)"),
                                           (obsId,
                                            NO_FOCAL_SUBJECT if event[EVENT_SUBJECT_FIELD_IDX] == "" else event[EVENT_SUBJECT_FIELD_IDX],
                                            event[EVENT_BEHAVIOR_FIELD_IDX],
                                            STATE if event[EVENT_BEHAVIOR_FIELD_IDX] in state_behaviors_codes else POINT,
                                            event[EVENT_MODIFIER_FIELD_IDX],
                                            str(event[EVENT_TIME_FIELD_IDX]),
                                            event[EVENT_COMMENT_FIELD_IDX]))

    db.commit()
    return cursor


def load_aggregated_events_in_db(pj: dict,
                                 selected_subjects: list,
                                 selected_observations: list,
                                 selected_behaviors: list):
    """
    populate a memory sqlite database with aggregated events from selected_observations, selected_subjects and selected_behaviors

    Args:
        pj (dict): project dictionary
        selected_observations (list):
        selected_subjects (list):
        selected_behaviors (list):

    Returns:
        bool: True if OK else False
        str: error message
        database connector: db connector if bool True else None

    """

    logging.debug(f"function: load_aggregated_events_in_db")

    # if no observation selected select all
    if not selected_observations:
        selected_observations = sorted([x for x in pj[OBSERVATIONS]])

    # if no subject selected select all
    if not selected_subjects:
        selected_subjects = sorted([pj[SUBJECTS][x][SUBJECT_NAME] for x in pj[SUBJECTS]] + [NO_FOCAL_SUBJECT])

    # if no behavior selected select all
    if not selected_behaviors:
        selected_behaviors = sorted([pj[ETHOGRAM][x][BEHAVIOR_CODE] for x in pj[ETHOGRAM]])

    # check if state events are paired
    out = ""
    for obsId in selected_observations:
        r, msg = project_functions.check_state_events_obs(obsId, pj[ETHOGRAM],
                                                          pj[OBSERVATIONS][obsId],
                                                          HHMMSS)
        if not r:
            out += f"Observation: <strong>{obsId}</strong><br>{msg}<br>"
    if out:
        return False, out, None

    # selected behaviors defined as state event
    state_behaviors_codes = [pj[ETHOGRAM][x][BEHAVIOR_CODE] for x in pj[ETHOGRAM]
                                 if STATE in pj[ETHOGRAM][x][TYPE].upper()
                                    and pj[ETHOGRAM][x][BEHAVIOR_CODE] in selected_behaviors]

    # selected behaviors defined as point event
    point_behaviors_codes = [pj[ETHOGRAM][x][BEHAVIOR_CODE] for x in pj[ETHOGRAM]
                                 if POINT in pj[ETHOGRAM][x][TYPE].upper()
                                    and pj[ETHOGRAM][x][BEHAVIOR_CODE] in selected_behaviors]

    db = sqlite3.connect(":memory:")
    #db = sqlite3.connect("/tmp/1.sqlite", isolation_level=None)

    db.row_factory = sqlite3.Row
    cursor2 = db.cursor()
    cursor2.execute(("CREATE TABLE aggregated_events "
                     "(id INTEGER PRIMARY KEY ASC, "
                     "observation TEXT, "
                     "subject TEXT, "
                     "behavior TEXT, "
                     "type TEXT, "
                     "modifiers TEXT, "
                     "start FLOAT, "
                     "stop FLOAT, "
                     "comment TEXT, "
                     "comment_stop TEXT)"))

    cursor2.execute("CREATE INDEX observation_idx ON aggregated_events(observation)")
    cursor2.execute("CREATE INDEX subject_idx ON aggregated_events(subject)")
    cursor2.execute("CREATE INDEX behavior_idx ON aggregated_events(behavior)")
    cursor2.execute("CREATE INDEX modifiers_idx ON aggregated_events(modifiers)")

    # too slow! cursor1 = load_events_in_db(pj, selected_subjects, selected_observations, selected_behaviors)

    for obsId in selected_observations:

        cursor1 = load_events_in_db(pj, selected_subjects, [obsId], selected_behaviors)

        for subject in selected_subjects:
            for behavior in selected_behaviors:

                cursor1.execute("SELECT DISTINCT modifiers FROM events WHERE subject=? AND code=? ORDER BY modifiers",
                                (subject, behavior, ))

                rows_distinct_modifiers = list(x[0] for x in cursor1.fetchall())

                for distinct_modifiers in rows_distinct_modifiers:

                    cursor1.execute(("SELECT occurence, comment FROM events "
                                     "WHERE subject = ? AND code = ? AND modifiers = ? ORDER by occurence"),
                                    (subject, behavior, distinct_modifiers))
                    rows = list(cursor1.fetchall())

                    for idx, row in enumerate(rows):

                        if behavior in point_behaviors_codes:
                            cursor2.execute(("INSERT INTO aggregated_events (observation, subject, behavior, type, modifiers, "
                                             "                               start, stop, comment, comment_stop) "
                                            "VALUES (?,?,?,?,?,?,?,?,?)"),
                                            (obsId, subject, behavior, POINT, distinct_modifiers,
                                             row["occurence"], row["occurence"], row["comment"], "",))

                        if behavior in state_behaviors_codes:
                            if idx % 2 == 0:
                                cursor2.execute(("INSERT INTO aggregated_events (observation, subject, behavior, type, modifiers,"
                                                 "                               start, stop, comment, comment_stop) "
                                                "VALUES (?,?,?,?,?,?,?,?,?)"),
                                                (obsId, subject, behavior, STATE, distinct_modifiers,
                                                 row["occurence"], rows[idx + 1]["occurence"], row["comment"], rows[idx + 1]["comment"]))

    db.commit()

    return True, "", db


def load_aggregated_events_in_intervals(pj: dict,
                                 selected_subjects: list,
                                 selected_observations: list,
                                 selected_behaviors: list):
    """
    populate a memory sqlite database with aggregated events from selected_observations, selected_subjects and selected_behaviors

    Args:
        pj (dict): project dictionary
        selected_observations (list):
        selected_subjects (list):
        selected_behaviors (list):

    Returns:
        bool: True if OK else False
        str: error message
        database connector: db connector if bool True else None

    """

    logging.debug(f"function: load_aggregated_events_in_db")

    # if no observation selected select all
    if not selected_observations:
        selected_observations = sorted([x for x in pj[OBSERVATIONS]])

    # if no subject selected select all
    if not selected_subjects:
        selected_subjects = sorted([pj[SUBJECTS][x][SUBJECT_NAME] for x in pj[SUBJECTS]] + [NO_FOCAL_SUBJECT])

    # if no behavior selected select all
    if not selected_behaviors:
        selected_behaviors = sorted([pj[ETHOGRAM][x][BEHAVIOR_CODE] for x in pj[ETHOGRAM]])

    intervals = {}

    # check if state events are paired
    out = ""
    for obsId in selected_observations:
        r, msg = project_functions.check_state_events_obs(obsId, pj[ETHOGRAM],
                                                          pj[OBSERVATIONS][obsId],
                                                          HHMMSS)
        if not r:
            out += f"Observation: <strong>{obsId}</strong><br>{msg}<br>"
    if out:
        return False, out, None

    # selected behaviors defined as state event
    state_behaviors_codes = [pj[ETHOGRAM][x][BEHAVIOR_CODE] for x in pj[ETHOGRAM]
                                 if STATE in pj[ETHOGRAM][x][TYPE].upper()
                                    and pj[ETHOGRAM][x][BEHAVIOR_CODE] in selected_behaviors]

    # selected behaviors defined as point event
    point_behaviors_codes = [pj[ETHOGRAM][x][BEHAVIOR_CODE] for x in pj[ETHOGRAM]
                                 if POINT in pj[ETHOGRAM][x][TYPE].upper()
                                    and pj[ETHOGRAM][x][BEHAVIOR_CODE] in selected_behaviors]

    db = sqlite3.connect(":memory:")

    for obsId in selected_observations:

        cursor1 = load_events_in_db(pj, selected_subjects, [obsId], selected_behaviors)

        for subject in selected_subjects:
            intervals[subject] = {}
            for behavior in selected_behaviors:
                intervals[subject][behaviors] = []

                cursor1.execute("SELECT DISTINCT modifiers FROM events WHERE subject=? AND code=? ORDER BY modifiers",
                                (subject, behavior, ))

                rows_distinct_modifiers = list(x[0] for x in cursor1.fetchall())

                for distinct_modifiers in rows_distinct_modifiers:

                    cursor1.execute(("SELECT occurence, comment FROM events "
                                     "WHERE subject = ? AND code = ? AND modifiers = ? ORDER by occurence"),
                                    (subject, behavior, distinct_modifiers))
                    rows = list(cursor1.fetchall())

                    for idx, row in enumerate(rows):

                        if behavior in point_behaviors_codes:
                            intervals[subject][behavior].append = P.singleton(row["occurence"])
                            cursor2.execute(("INSERT INTO aggregated_events (observation, subject, behavior, type, modifiers, "
                                             "                               start, stop, comment, comment_stop) "
                                            "VALUES (?,?,?,?,?,?,?,?,?)"),
                                            (obsId, subject, behavior, POINT, distinct_modifiers,
                                             row["occurence"], row["occurence"], row["comment"], "",))

                        if behavior in state_behaviors_codes:
                            if idx % 2 == 0:
                                cursor2.execute(("INSERT INTO aggregated_events (observation, subject, behavior, type, modifiers,"
                                                 "                               start, stop, comment, comment_stop) "
                                                "VALUES (?,?,?,?,?,?,?,?,?)"),
                                                (obsId, subject, behavior, STATE, distinct_modifiers,
                                                 row["occurence"], rows[idx + 1]["occurence"], row["comment"], rows[idx + 1]["comment"]))

    db.commit()

    return True, "", db
