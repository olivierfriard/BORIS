"""
BORIS
Behavioral Observation Research Interactive Software
Copyright 2012-2024 Olivier Friard


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
import logging
from typing import Optional, Tuple
from . import config as cfg
from . import project_functions
from . import event_operations


def load_events_in_db(
    pj: dict,
    selected_subjects: list,
    selected_observations: list,
    selected_behaviors: list,
    time_interval: str = cfg.TIME_FULL_OBS,
):
    """
    populate a memory sqlite database with events from selected_observations,
    selected_subjects and selected_behaviors

    Args:
        pj (dict): project dictionary
        selected_observations (list):
        selected_subjects (list):
        selected_behaviors (list):
        time_interval (str): time interval for loading events (cfg.TIME_FULL_OBS / TIME_cfg.EVENTS / TIME_ARBITRARY_INTERVAL)

    Returns:
        database cursor:

    """

    # selected behaviors defined as state event
    state_behaviors_codes = [
        pj[cfg.ETHOGRAM][x][cfg.BEHAVIOR_CODE]
        for x in pj[cfg.ETHOGRAM]
        if cfg.STATE in pj[cfg.ETHOGRAM][x][cfg.TYPE].upper() and pj[cfg.ETHOGRAM][x][cfg.BEHAVIOR_CODE] in selected_behaviors
    ]

    # selected behaviors defined as point event
    """
    point_behaviors_codes = [
        pj[cfg.ETHOGRAM][x][cfg.BEHAVIOR_CODE]
        for x in pj[cfg.ETHOGRAM]
        if cfg.POINT in pj[cfg.ETHOGRAM][x][cfg.TYPE].upper()
        and pj[cfg.ETHOGRAM][x][cfg.BEHAVIOR_CODE] in selected_behaviors
    ]
    """

    db = sqlite3.connect(":memory:", isolation_level=None)
    """
    import os
    os.system("rm /tmp/ramdisk/events.sqlite")
    db = sqlite3.connect("/tmp/ramdisk/events.sqlite", isolation_level=None)
    """

    db.row_factory = sqlite3.Row
    cursor = db.cursor()
    cursor.execute(
        (
            "CREATE TABLE events (observation TEXT, "
            "subject TEXT, "
            "code TEXT, "
            "type TEXT, "
            "modifiers TEXT, "
            "occurence FLOAT, "
            "comment TEXT,"
            "image_index INTEGER,"
            "image_path TEXT)"
        )
    )

    cursor.execute("CREATE INDEX observation_idx ON events(observation)")
    cursor.execute("CREATE INDEX subject_idx ON events(subject)")
    cursor.execute("CREATE INDEX code_idx ON events(code)")
    cursor.execute("CREATE INDEX modifiers_idx ON events(modifiers)")

    for subject_to_analyze in selected_subjects:
        for obs_id in selected_observations:
            for event in pj[cfg.OBSERVATIONS][obs_id][cfg.EVENTS]:
                if event[cfg.EVENT_BEHAVIOR_FIELD_IDX] in selected_behaviors:
                    # extract time, code, modifier and comment (time:0, subject:1, code:2, modifier:3, comment:4)
                    if (subject_to_analyze == cfg.NO_FOCAL_SUBJECT and event[cfg.EVENT_SUBJECT_FIELD_IDX] == "") or (
                        event[cfg.EVENT_SUBJECT_FIELD_IDX] == subject_to_analyze
                    ):
                        if pj[cfg.OBSERVATIONS][obs_id][cfg.TYPE] in (cfg.MEDIA, cfg.LIVE):
                            cursor.execute(
                                (
                                    "INSERT INTO events "
                                    "(observation, subject, code, type, modifiers, occurence, comment, image_index) "
                                    "VALUES (?,?,?,?,?,?,?,?)"
                                ),
                                (
                                    obs_id,
                                    cfg.NO_FOCAL_SUBJECT
                                    if event[cfg.EVENT_SUBJECT_FIELD_IDX] == ""
                                    else event[cfg.EVENT_SUBJECT_FIELD_IDX],
                                    event[cfg.EVENT_BEHAVIOR_FIELD_IDX],
                                    cfg.STATE if event[cfg.EVENT_BEHAVIOR_FIELD_IDX] in state_behaviors_codes else cfg.POINT,
                                    event[cfg.EVENT_MODIFIER_FIELD_IDX],
                                    float(event[cfg.EVENT_TIME_FIELD_IDX]) if not event[cfg.EVENT_TIME_FIELD_IDX].is_nan() else None,
                                    event[cfg.EVENT_COMMENT_FIELD_IDX],
                                    # frame index or NA
                                    event_operations.read_event_field(event, pj[cfg.OBSERVATIONS][obs_id][cfg.TYPE], cfg.FRAME_INDEX),
                                ),
                            )

                        if pj[cfg.OBSERVATIONS][obs_id][cfg.TYPE] == cfg.IMAGES:
                            cursor.execute(
                                (
                                    "INSERT INTO events "
                                    "(observation, subject, code, type, modifiers, occurence, comment, image_index, image_path) "
                                    "VALUES (?,?,?,?,?,?,?,?,?)"
                                ),
                                (
                                    obs_id,
                                    cfg.NO_FOCAL_SUBJECT
                                    if event[cfg.EVENT_SUBJECT_FIELD_IDX] == ""
                                    else event[cfg.EVENT_SUBJECT_FIELD_IDX],
                                    event[cfg.EVENT_BEHAVIOR_FIELD_IDX],
                                    cfg.STATE if event[cfg.EVENT_BEHAVIOR_FIELD_IDX] in state_behaviors_codes else cfg.POINT,
                                    event[cfg.EVENT_MODIFIER_FIELD_IDX],
                                    float(event[cfg.EVENT_TIME_FIELD_IDX]) if not event[cfg.EVENT_TIME_FIELD_IDX].is_nan() else None,
                                    event[cfg.EVENT_COMMENT_FIELD_IDX],
                                    event[cfg.PJ_OBS_FIELDS[cfg.IMAGES][cfg.IMAGE_INDEX]],
                                    event[cfg.PJ_OBS_FIELDS[cfg.IMAGES][cfg.IMAGE_PATH]],
                                ),
                            )

    db.commit()
    return cursor


def load_aggregated_events_in_db(
    pj: dict, selected_subjects: list, selected_observations: list, selected_behaviors: list
) -> Tuple[bool, str, Optional[sqlite3.Connection]]:
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

    logging.debug("function: load_aggregated_events_in_db")

    # if no observation selected select all
    if not selected_observations:
        selected_observations = sorted([x for x in pj[cfg.OBSERVATIONS]])

    # if no subject selected select all
    if not selected_subjects:
        selected_subjects = sorted([pj[cfg.SUBJECTS][x][cfg.SUBJECT_NAME] for x in pj[cfg.SUBJECTS]] + [cfg.NO_FOCAL_SUBJECT])

    # if no behavior selected select all
    if not selected_behaviors:
        selected_behaviors = sorted([pj[cfg.ETHOGRAM][x][cfg.BEHAVIOR_CODE] for x in pj[cfg.ETHOGRAM]])

    # check if state events are paired
    out = ""
    for obs_id in selected_observations:
        r, msg = project_functions.check_state_events_obs(obs_id, pj[cfg.ETHOGRAM], pj[cfg.OBSERVATIONS][obs_id], cfg.HHMMSS)
        if not r:
            out += f"Observation: <strong>{obs_id}</strong><br>{msg}<br>"
    if out:
        return False, out, None

    # selected behaviors defined as state event
    state_behaviors_codes = [
        pj[cfg.ETHOGRAM][x][cfg.BEHAVIOR_CODE]
        for x in pj[cfg.ETHOGRAM]
        if cfg.STATE in pj[cfg.ETHOGRAM][x][cfg.TYPE].upper() and pj[cfg.ETHOGRAM][x][cfg.BEHAVIOR_CODE] in selected_behaviors
    ]

    # selected behaviors defined as point event
    point_behaviors_codes = [
        pj[cfg.ETHOGRAM][x][cfg.BEHAVIOR_CODE]
        for x in pj[cfg.ETHOGRAM]
        if cfg.POINT in pj[cfg.ETHOGRAM][x][cfg.TYPE].upper() and pj[cfg.ETHOGRAM][x][cfg.BEHAVIOR_CODE] in selected_behaviors
    ]

    db = sqlite3.connect(":memory:")

    """
    import os
    os.system("rm /tmp/ramdisk/aggreg.sqlite")
    db = sqlite3.connect("/tmp/ramdisk/aggreg.sqlite", isolation_level=None)
    """

    db.row_factory = sqlite3.Row
    cursor2 = db.cursor()
    cursor2.execute(
        (
            "CREATE TABLE aggregated_events "
            "(id INTEGER PRIMARY KEY ASC, "
            "observation TEXT, "
            "subject TEXT, "
            "behavior TEXT, "
            "type TEXT, "
            "modifiers TEXT, "
            "start FLOAT, "
            "stop FLOAT, "
            "comment TEXT, "
            "comment_stop TEXT,"
            "image_index_start INTEGER,"
            "image_index_stop INTEGER,"
            "image_path_start TEXT,"
            "image_path_stop TEXT)"
        )
    )

    cursor2.execute("CREATE INDEX observation_idx ON aggregated_events(observation)")
    cursor2.execute("CREATE INDEX subject_idx ON aggregated_events(subject)")
    cursor2.execute("CREATE INDEX behavior_idx ON aggregated_events(behavior)")
    cursor2.execute("CREATE INDEX modifiers_idx ON aggregated_events(modifiers)")

    # too slow! cursor1 = load_events_in_db(pj, selected_subjects, selected_observations, selected_behaviors)

    insert_sql = (
        "INSERT INTO aggregated_events (observation, subject, behavior, type, modifiers, "
        "                               start, stop, comment, comment_stop, "
        "image_index_start, image_index_stop, image_path_start, image_path_stop) "
        "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)"
    )

    for obs_id in selected_observations:
        cursor1 = load_events_in_db(pj, selected_subjects, [obs_id], selected_behaviors)

        for subject in selected_subjects:
            for behavior in selected_behaviors:
                cursor1.execute(
                    "SELECT DISTINCT modifiers FROM events WHERE subject=? AND code=? ORDER BY modifiers",
                    (
                        subject,
                        behavior,
                    ),
                )

                rows_distinct_modifiers = list(x[0] for x in cursor1.fetchall())

                for distinct_modifiers in rows_distinct_modifiers:
                    cursor1.execute(
                        (
                            "SELECT occurence, comment, image_index, image_path FROM events "
                            "WHERE subject = ? AND code = ? AND modifiers = ? ORDER by occurence"
                        ),
                        (subject, behavior, distinct_modifiers),
                    )
                    rows = list(cursor1.fetchall())

                    for idx, row in enumerate(rows):
                        if behavior in point_behaviors_codes:
                            data = (
                                obs_id,
                                subject,
                                behavior,
                                cfg.POINT,
                                distinct_modifiers,
                                row["occurence"],
                                row["occurence"],
                                row["comment"],
                                "",  # no stop comment for point event
                                row["image_index"],
                                row["image_index"],
                                row["image_path"],
                                row["image_path"],
                            )
                            cursor2.execute(insert_sql, data)

                        if behavior in state_behaviors_codes:
                            if idx % 2 == 0:
                                data = (
                                    obs_id,
                                    subject,
                                    behavior,
                                    cfg.STATE,
                                    distinct_modifiers,
                                    row["occurence"],
                                    rows[idx + 1]["occurence"],
                                    row["comment"],
                                    rows[idx + 1]["comment"],
                                    row["image_index"],
                                    rows[idx + 1]["image_index"],
                                    row["image_path"],
                                    rows[idx + 1]["image_path"],
                                )

                                cursor2.execute(insert_sql, data)

    db.commit()

    return True, "", db
