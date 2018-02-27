"""
BORIS
Behavioral Observation Research Interactive Software
Copyright 2012-2018 Olivier Friard


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
from config import *


def load_events_in_db(pj, selectedSubjects, selectedObservations, selectedBehaviors):
    """
    populate a memory sqlite database with events from selectedObservations, 
    selectedSubjects and selectedBehaviors
    
    Args:
        pj (dict): project dictionary
        selectedObservations (list):
        selectedSubjects (list):
        selectedBehaviors (list):
        
    Returns:
        database cursor:

    """
    
    # selected behaviors defined as state event
    state_behaviors_codes = [pj[ETHOGRAM][x]["code"] for x in pj[ETHOGRAM]
                                 if STATE in pj[ETHOGRAM][x][TYPE].upper()
                                    and pj[ETHOGRAM][x]["code"] in selectedBehaviors]

    # selected behaviors defined as point event
    point_behaviors_codes = [pj[ETHOGRAM][x]["code"] for x in pj[ETHOGRAM]
                                 if POINT in pj[ETHOGRAM][x][TYPE].upper()
                                    and pj[ETHOGRAM][x]["code"] in selectedBehaviors]
    
    db = sqlite3.connect(":memory:", isolation_level=None)

    db.row_factory = sqlite3.Row
    cursor = db.cursor()
    cursor.execute("""CREATE TABLE events (observation TEXT,
                                           subject TEXT,
                                           code TEXT,
                                           type TEXT,
                                           modifiers TEXT,
                                           occurence FLOAT,
                                           comment TEXT)""")

    for subject_to_analyze in selectedSubjects:

        for obsId in selectedObservations:

            for event in pj[OBSERVATIONS][obsId][EVENTS]:

                if event[EVENT_BEHAVIOR_FIELD_IDX] in selectedBehaviors:

                    # extract time, code, modifier and comment (time:0, subject:1, code:2, modifier:3, comment:4)
                    if ((subject_to_analyze == NO_FOCAL_SUBJECT and event[EVENT_SUBJECT_FIELD_IDX] == "") or
                            (event[EVENT_SUBJECT_FIELD_IDX] == subject_to_analyze)):

                        r = cursor.execute("""INSERT INTO events
                                               (observation, subject, code, type, modifiers, occurence, comment)
                                                VALUES (?,?,?,?,?,?,?)""",
                        (obsId,
                         NO_FOCAL_SUBJECT if event[EVENT_SUBJECT_FIELD_IDX] == "" else event[EVENT_SUBJECT_FIELD_IDX],
                         event[EVENT_BEHAVIOR_FIELD_IDX],
                         STATE if event[EVENT_BEHAVIOR_FIELD_IDX] in state_behaviors_codes else POINT,
                         event[EVENT_MODIFIER_FIELD_IDX], 
                         str(event[EVENT_TIME_FIELD_IDX]),
                         event[EVENT_COMMENT_FIELD_IDX]))

    db.commit()
    return cursor



def load_aggregated_events_in_db(pj, selectedSubjects, selectedObservations, selectedBehaviors):
    """
    populate a memory sqlite database with aggregated events from selectedObservations, selectedSubjects and selectedBehaviors
    
    Args:
        pj (dict): project dictionary
        selectedObservations (list):
        selectedSubjects (list):
        selectedBehaviors (list):
        
    Returns:
        database connector:

    """

    if not selectedObservations:
        selectedObservations = sorted([x for x in pj[OBSERVATIONS]])

    if not selectedSubjects:
        selectedSubjects = sorted([pj[SUBJECTS][x]["name"] for x in pj[SUBJECTS]] + [NO_FOCAL_SUBJECT])

    if not selectedBehaviors:
        selectedBehaviors = sorted([pj[ETHOGRAM][x]["code"] for x in pj[ETHOGRAM]])



    # selected behaviors defined as state event
    state_behaviors_codes = [pj[ETHOGRAM][x]["code"] for x in pj[ETHOGRAM]
                                 if STATE in pj[ETHOGRAM][x][TYPE].upper()
                                    and pj[ETHOGRAM][x]["code"] in selectedBehaviors]

    # selected behaviors defined as point event
    point_behaviors_codes = [pj[ETHOGRAM][x]["code"] for x in pj[ETHOGRAM]
                                 if POINT in pj[ETHOGRAM][x][TYPE].upper()
                                    and pj[ETHOGRAM][x]["code"] in selectedBehaviors]


    cursor1 = load_events_in_db(pj, selectedSubjects, selectedObservations, selectedBehaviors)

    db = sqlite3.connect(":memory:")
    db.row_factory = sqlite3.Row
    cursor2 = db.cursor()
    cursor2.execute("""CREATE TABLE aggregated_events
                              (id INTEGER PRIMARY KEY ASC,
                               observation TEXT,
                               subject TEXT,
                               behavior TEXT,
                               type TEXT,
                               modifiers TEXT,
                               start FLOAT,
                               stop FLOAT,
                               comment TEXT)""")

    for obsId in selectedObservations:
        for subject in selectedSubjects:
            for behavior in selectedBehaviors:
    
                cursor1.execute(("SELECT occurence, modifiers, comment FROM events "
                                 "WHERE observation = ? AND subject = ? AND code = ? ORDER by occurence"), (obsId, subject, behavior))
                rows = list(cursor1.fetchall())

                for idx, row in enumerate(rows):
    
                    if behavior in point_behaviors_codes:
                        
                        cursor2.execute(("INSERT INTO aggregated_events (observation, subject, behavior, type, modifiers, start, stop) "
                                        "VALUES (?,?,?,?,?,?,?)"),
                                        (obsId, subject, behavior, POINT, row["modifiers"].strip(), row["occurence"], row["occurence"]))

                    if behavior in state_behaviors_codes:
                        if idx % 2 == 0:
                            cursor2.execute(("INSERT INTO aggregated_events (observation, subject, behavior, type, modifiers, start, stop) "
                                            "VALUES (?,?,?,?,?,?,?)"),
                                            (obsId, subject, behavior, STATE, row["modifiers"].strip(),
                                             row["occurence"], rows[idx + 1]["occurence"]))

    db.commit()
    return db



