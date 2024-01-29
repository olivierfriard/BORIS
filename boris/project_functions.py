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

import gzip
import json
import logging
import os
import pathlib as pl
import sys
from decimal import Decimal as dec
from shutil import copyfile
from typing import List, Tuple, Dict

import tablib
from PyQt5.QtWidgets import QMessageBox, QTableWidgetItem, QAbstractItemView
from PyQt5.QtCore import Qt

from . import config as cfg
from . import db_functions
from . import dialog
from . import portion as I
from . import utilities as util
from . import version
from . import observation_operations


def check_observation_exhaustivity(
    events: List[list],
    state_events_list: list = [],
) -> float:
    """
    calculate the observation exhaustivity
    if ethogram not empty state events list is determined else

    Args:
        events (List[list]): events
        ethogram (list):
    """

    def interval_len(interval: I) -> dec:
        """ "
        returns duration of an interval or a set of intervals
        """
        if interval.empty:
            return dec(0)
        else:
            return dec(sum([x.upper - x.lower for x in interval]))

    events_interval: dict = {}
    mem_events_interval: dict = {}

    for event in events:
        if event[cfg.EVENT_SUBJECT_FIELD_IDX] not in events_interval:
            events_interval[event[cfg.EVENT_SUBJECT_FIELD_IDX]] = {}
            mem_events_interval[event[cfg.EVENT_SUBJECT_FIELD_IDX]] = {}

        if event[cfg.EVENT_BEHAVIOR_FIELD_IDX] not in events_interval[event[cfg.EVENT_SUBJECT_FIELD_IDX]]:
            events_interval[event[cfg.EVENT_SUBJECT_FIELD_IDX]][event[cfg.EVENT_BEHAVIOR_FIELD_IDX]] = I.empty()
            mem_events_interval[event[cfg.EVENT_SUBJECT_FIELD_IDX]][event[cfg.EVENT_BEHAVIOR_FIELD_IDX]] = []

        # state event
        if event[cfg.EVENT_BEHAVIOR_FIELD_IDX] in state_events_list:
            mem_events_interval[event[cfg.EVENT_SUBJECT_FIELD_IDX]][event[cfg.EVENT_BEHAVIOR_FIELD_IDX]].append(
                event[cfg.EVENT_TIME_FIELD_IDX]
            )
            if len(mem_events_interval[event[cfg.EVENT_SUBJECT_FIELD_IDX]][event[cfg.EVENT_BEHAVIOR_FIELD_IDX]]) == 2:
                events_interval[event[cfg.EVENT_SUBJECT_FIELD_IDX]][event[cfg.EVENT_BEHAVIOR_FIELD_IDX]] |= I.closedopen(
                    mem_events_interval[event[cfg.EVENT_SUBJECT_FIELD_IDX]][event[cfg.EVENT_BEHAVIOR_FIELD_IDX]][0],
                    mem_events_interval[event[cfg.EVENT_SUBJECT_FIELD_IDX]][event[cfg.EVENT_BEHAVIOR_FIELD_IDX]][1],
                )
                mem_events_interval[event[cfg.EVENT_SUBJECT_FIELD_IDX]][event[cfg.EVENT_BEHAVIOR_FIELD_IDX]] = []
        # point event
        else:
            events_interval[event[cfg.EVENT_SUBJECT_FIELD_IDX]][event[cfg.EVENT_BEHAVIOR_FIELD_IDX]] |= I.singleton(
                event[cfg.EVENT_TIME_FIELD_IDX]
            )

    if events:
        # coding duration
        event_timestamps = [event[cfg.EVENT_TIME_FIELD_IDX] for event in events]
        obs_theo_dur = max(event_timestamps) - min(event_timestamps)
    else:
        obs_theo_dur = dec("0")

    total_duration = 0
    for subject in events_interval:
        tot_behav_for_subject = I.empty()
        for behav in events_interval[subject]:
            tot_behav_for_subject |= events_interval[subject][behav]

        obs_real_dur = interval_len(tot_behav_for_subject)

        if obs_real_dur >= obs_theo_dur:
            obs_real_dur = obs_theo_dur

        total_duration += obs_real_dur

    if len(events_interval) and obs_theo_dur:
        exhausivity_percent = total_duration / (len(events_interval) * obs_theo_dur) * 100
    else:
        exhausivity_percent = 0

    return round(exhausivity_percent, 1)


def check_observation_exhaustivity_pictures(obs) -> float:
    """
    check exhaustivity of coding for observations from pictures
    """
    if obs[cfg.TYPE] != cfg.IMAGES:
        return -1
    tot_images_number = 0

    for dir_path in obs.get(cfg.DIRECTORIES_LIST, []):
        result = util.dir_images_number(dir_path)
        tot_images_number += result.get("number of images", 0)

    if not tot_images_number:
        return "No pictures found"

    # list of paths of coded images
    coded_images_number = len(set([x[cfg.PJ_OBS_FIELDS[cfg.IMAGES][cfg.IMAGE_PATH]] for x in obs[cfg.EVENTS]]))

    return round(coded_images_number / tot_images_number * 100, 1)


def behavior_category(ethogram: dict) -> Dict[str, str]:
    """
    returns a dictionary containing the behavioral category of each behavior

    Args:
        ethogram (dict): ethogram

    Returns:
        dict: dictionary containing behavioral category (value) for each behavior code (key)
    """

    behavioral_category = {}
    for idx in ethogram:
        if cfg.BEHAVIOR_CATEGORY in ethogram[idx]:
            behavioral_category[ethogram[idx][cfg.BEHAVIOR_CODE]] = ethogram[idx][cfg.BEHAVIOR_CATEGORY]
        else:
            behavioral_category[ethogram[idx][cfg.BEHAVIOR_CODE]] = ""
    return behavioral_category


def check_if_media_available(observation: dict, project_file_name: str) -> Tuple[bool, str]:
    """
    check if media files available for media and images observations

    Args:
        observation (dict): observation to be checked

    Returns:
        bool: True if media files found or for live observation
               else False
        str: error message
    """
    if observation[cfg.TYPE] == cfg.LIVE:
        return (True, "")

    # TODO: check all files before returning False
    if observation[cfg.TYPE] == cfg.IMAGES:
        for img_dir in observation.get(cfg.DIRECTORIES_LIST, []):
            if not full_path(img_dir, project_file_name):
                return (False, f"The images directory <b>{img_dir}</b> was not found")
        return (True, "")

    if observation[cfg.TYPE] == cfg.MEDIA:
        for nplayer in cfg.ALL_PLAYERS:
            if nplayer in observation.get(cfg.FILE, {}):
                if not isinstance(observation[cfg.FILE][nplayer], list):
                    return (False, "error")
                for media_file in observation[cfg.FILE][nplayer]:
                    if not full_path(media_file, project_file_name):
                        return (False, f"Media file <b>{media_file}</b> was not found")
        return (True, "")

    return (False, "Observation type not found")


def check_directories_availability(observation: dict, project_file_name: str) -> Tuple[bool, str]:
    """
    check if directories are available

    Args:
        observation (dict): observation to be checked

    Returns:
        bool: True if all directories were found or for live observation
               else False
        str: error message
    """
    if observation[cfg.TYPE] == cfg.LIVE:
        return (True, "")

    for dir_path in observation.get(cfg.DIRECTORIES_LIST, []):
        if not full_path(dir_path, project_file_name):
            return (False, f"Directory <b>{dir_path}</b> not found")

    return (True, "")


def check_coded_behaviors_in_obs_list(pj: dict, observations_list: list) -> bool:
    """
    check if coded behaviors in a list of observations are defined in the ethogram
    """
    out = ""
    ethogram_behavior_codes = {pj[cfg.ETHOGRAM][idx][cfg.BEHAVIOR_CODE] for idx in pj[cfg.ETHOGRAM]}
    behaviors_not_defined = []
    out = ""  # will contain the output
    for obs_id in observations_list:
        for event in pj[cfg.OBSERVATIONS][obs_id][cfg.EVENTS]:
            if event[cfg.EVENT_BEHAVIOR_FIELD_IDX] not in ethogram_behavior_codes:
                behaviors_not_defined.append(event[cfg.EVENT_BEHAVIOR_FIELD_IDX])
    if set(sorted(behaviors_not_defined)):
        out += f"The following behaviors are not defined in the ethogram: <b>{', '.join(set(sorted(behaviors_not_defined)))}</b><br><br>"
        results = dialog.Results_dialog()
        results.setWindowTitle(f"{cfg.programName} - Check selected observations")
        results.ptText.setReadOnly(True)
        results.ptText.appendHtml(out)
        results.pbSave.setVisible(False)
        results.pbCancel.setVisible(True)
        if not results.exec_():
            return True
    return False


def check_coded_behaviors(pj: dict) -> set:
    """
    check if behaviors coded in events are defined in ethogram for all observations

    Args:
        pj (dict): project dictionary

    Returns:
        set: behaviors present in observations that are not define in ethogram
    """

    # set of behaviors defined in ethogram
    ethogram_behavior_codes = {pj[cfg.ETHOGRAM][idx][cfg.BEHAVIOR_CODE] for idx in pj[cfg.ETHOGRAM]}
    behaviors_not_defined = []

    for obs_id in pj[cfg.OBSERVATIONS]:
        for event in pj[cfg.OBSERVATIONS][obs_id][cfg.EVENTS]:
            if event[cfg.EVENT_BEHAVIOR_FIELD_IDX] not in ethogram_behavior_codes:
                behaviors_not_defined.append(event[cfg.EVENT_BEHAVIOR_FIELD_IDX])
    return set(sorted(behaviors_not_defined))


def check_state_events_obs(obsId: str, ethogram: dict, observation: dict, time_format: str = cfg.HHMMSS) -> Tuple[bool, str]:
    """
    check state events for the observation obsId
    check if behaviors in observation are defined in ethogram
    check if number is odd

    Args:
        obsId (str): id of observation to check
        ethogram (dict): ethogram of project
        observation (dict): observation to be checked
        time_format (str): time format

    Returns:
        tuple (bool, str): if OK True else False , message
    """

    out = ""

    # check if behaviors are defined as "state event"
    event_types = {ethogram[idx]["type"] for idx in ethogram}

    if not event_types or event_types == {"Point event"}:
        return (True, "No behavior is defined as `State event`")

    subjects = [event[cfg.EVENT_SUBJECT_FIELD_IDX] for event in observation[cfg.EVENTS]]
    ethogram_behaviors = {ethogram[idx][cfg.BEHAVIOR_CODE] for idx in ethogram}

    for subject in sorted(set(subjects)):
        behaviors = [
            event[cfg.EVENT_BEHAVIOR_FIELD_IDX] for event in observation[cfg.EVENTS] if event[cfg.EVENT_SUBJECT_FIELD_IDX] == subject
        ]

        for behavior in sorted(set(behaviors)):
            if behavior not in ethogram_behaviors:
                # return (False, "The behaviour <b>{}</b> is not defined in the ethogram.<br>".format(behavior))
                continue
            else:
                if cfg.STATE in event_type(behavior, ethogram).upper():
                    lst: list = []
                    memTime: dict = {}
                    for event in [
                        event
                        for event in observation[cfg.EVENTS]
                        if event[cfg.EVENT_BEHAVIOR_FIELD_IDX] == behavior and event[cfg.EVENT_SUBJECT_FIELD_IDX] == subject
                    ]:
                        behav_modif = [
                            event[cfg.EVENT_BEHAVIOR_FIELD_IDX],
                            event[cfg.EVENT_MODIFIER_FIELD_IDX],
                        ]

                        if behav_modif in lst:
                            lst.remove(behav_modif)
                            del memTime[str(behav_modif)]
                        else:
                            lst.append(behav_modif)
                            memTime[str(behav_modif)] = event[cfg.EVENT_TIME_FIELD_IDX]

                    for event in lst:
                        out += (
                            f"The behavior <b>{behavior}</b> "
                            f"{('(modifier ' + event[1] + ') ') if event[1] else ''} is not PAIRED "
                            f'for subject "<b>{subject if subject else cfg.NO_FOCAL_SUBJECT}</b>" at '
                            f"<b>{memTime[str(event)] if time_format == cfg.S else util.seconds2time(memTime[str(event)])}</b><br>"
                        )

    return (False, out) if out else (True, "No problem detected")


def check_state_events(pj: dict, observations_list: list) -> Tuple[bool, tuple]:
    """
    check if state events are paired in a list of observations
    use check_state_events_obs function
    """

    logging.info("Check state events")

    out = ""
    not_paired_obs_list = []
    for obs_id in observations_list:
        r, msg = check_state_events_obs(obs_id, pj[cfg.ETHOGRAM], pj[cfg.OBSERVATIONS][obs_id])

        if not r:
            out += f"Observation: <strong>{obs_id}</strong><br>{msg}<br>"
            not_paired_obs_list.append(obs_id)

    if out:
        out = f"The observations with UNPAIRED state events will be removed from the analysis<br><br>{out}"
        results = dialog.Results_dialog()
        results.setWindowTitle(f"{cfg.programName} - Check selected observations")
        results.ptText.setReadOnly(True)
        results.ptText.appendHtml(out)
        results.pbSave.setVisible(False)
        results.pbCancel.setVisible(True)
        if not results.exec_():
            return True, []

    # remove observations with unpaired state events
    new_observations_list = [x for x in observations_list if x not in not_paired_obs_list]
    if not new_observations_list:
        QMessageBox.warning(None, cfg.programName, "The observation list is empty")

    logging.info("Check state events done")

    return False, new_observations_list  # no state events are unpaired


def check_project_integrity(
    pj: dict,
    time_format: str,
    project_file_name: str,
    media_file_available: bool = True,
) -> str:
    """
    check project integrity
    check if behaviors in observations are in ethogram
    check unpaired state events
    check if timestamp between -2147483647 and 2147483647 (2**31 - 1)
    check if behavior belong to behavioral category that do not more exist
    check for leading and trailing spaces and special chars in modifiers
    check if media file are available
    check if media length available
    check independent variables

    Args:
        pj (dict): BORIS project
        time_format (str): time format
        project_file_name (str): project file name
        media_file_access(bool): check if media file are available

    Returns:
        str: message
    """
    out = ""

    # check if coded behaviors are defined in ethogram
    r = check_coded_behaviors(pj)
    if r:
        out += f"The following behaviors are not defined in the ethogram: <b>{', '.join(r)}</b><br>"

    # check for unpaired state events
    for obs_id in pj[cfg.OBSERVATIONS]:
        ok, msg = check_state_events_obs(obs_id, pj[cfg.ETHOGRAM], pj[cfg.OBSERVATIONS][obs_id], time_format)
        if not ok:
            out += "<br><br>" if out else ""
            out += f"Observation: <b>{obs_id}</b><br>{msg}"

    # check if behavior belong to category that is not in categories list
    for idx in pj[cfg.ETHOGRAM]:
        if cfg.BEHAVIOR_CATEGORY in pj[cfg.ETHOGRAM][idx]:
            if pj[cfg.ETHOGRAM][idx][cfg.BEHAVIOR_CATEGORY]:
                if pj[cfg.ETHOGRAM][idx][cfg.BEHAVIOR_CATEGORY] not in pj[cfg.BEHAVIORAL_CATEGORIES]:
                    out += "<br><br>" if out else ""
                    out += (
                        f"The behavior <b>{pj[cfg.ETHOGRAM][idx][cfg.BEHAVIOR_CODE]}</b> belongs "
                        f"to the behavioral category <b>{pj[cfg.ETHOGRAM][idx][cfg.BEHAVIOR_CATEGORY]}</b> "
                        "that is no more in behavioral categories list."
                    )

    # check for leading/trailing spaces/special chars in modifiers defined in ethogram
    for idx in pj[cfg.ETHOGRAM]:
        for k in pj[cfg.ETHOGRAM][idx][cfg.MODIFIERS]:
            for value in pj[cfg.ETHOGRAM][idx][cfg.MODIFIERS][k]["values"]:
                modifier_code = value.split(" (")[0]
                if modifier_code.strip() != modifier_code:
                    out += "<br><br>" if out else ""
                    out += (
                        "The following <b>modifier</b> defined in ethogram "
                        "has leading/trailing spaces or special chars: "
                        f"<b>{util.replace_leading_trailing_chars(modifier_code, old_char=' ', new_char='&#9608;')}</b>"
                    )

    # check if all media are available
    if media_file_available:
        for obs_id in pj[cfg.OBSERVATIONS]:
            ok, msg = check_if_media_available(pj[cfg.OBSERVATIONS][obs_id], project_file_name)
            if not ok:
                out += "<br><br>" if out else ""
                out += f"Observation: <b>{obs_id}</b><br>{msg}"

    out_events = ""
    for obs_id in pj[cfg.OBSERVATIONS]:
        # check if timestamp between -2147483647 and 2147483647
        for event in pj[cfg.OBSERVATIONS][obs_id][cfg.EVENTS]:
            timestamp = event[cfg.PJ_OBS_FIELDS[pj[cfg.OBSERVATIONS][obs_id][cfg.TYPE]][cfg.TIME]]
            if not timestamp.is_nan() and not (-2147483647 <= timestamp <= 2147483647):
                out_events += f"Observation: <b>{obs_id}</b><br>The timestamp {timestamp} is not between -2147483647 and 2147483647.<br>"

        # check if media length available
        if pj[cfg.OBSERVATIONS][obs_id][cfg.TYPE] == cfg.MEDIA:
            for nplayer in cfg.ALL_PLAYERS:
                if nplayer in pj[cfg.OBSERVATIONS][obs_id][cfg.FILE]:
                    for media_file in pj[cfg.OBSERVATIONS][obs_id][cfg.FILE][nplayer]:
                        try:
                            pj[cfg.OBSERVATIONS][obs_id][cfg.MEDIA_INFO][cfg.LENGTH][media_file]
                        except KeyError:
                            out += "<br><br>" if out else ""
                            out += f"Observation: <b>{obs_id}</b><br>Length not available for media file <b>{media_file}</b>"

    out += "<br><br>" if out else ""
    out += out_events

    # check for leading/trailing spaces/special chars in observation id
    for obs_id in pj[cfg.OBSERVATIONS]:
        if obs_id != obs_id.strip():
            out += "<br><br>" if out else ""
            out += (
                "The following <b>observation id</b> "
                "has leading/trailing spaces or special chars: "
                f"<b>{util.replace_leading_trailing_chars(obs_id, ' ', '&#9608;')}</b>"
            )

    # check independent variables present in observations are defined
    defined_var_label = [pj[cfg.INDEPENDENT_VARIABLES][idx]["label"] for idx in pj.get(cfg.INDEPENDENT_VARIABLES, {})]
    not_defined: dict = {}
    for obs_id in pj[cfg.OBSERVATIONS]:
        if cfg.INDEPENDENT_VARIABLES not in pj[cfg.OBSERVATIONS][obs_id]:
            continue
        for var_label in pj[cfg.OBSERVATIONS][obs_id][cfg.INDEPENDENT_VARIABLES]:
            if var_label not in defined_var_label:
                if var_label not in not_defined:
                    not_defined[var_label] = [obs_id]
                else:
                    not_defined[var_label].append(obs_id)
    if not_defined:
        out += "<br><br>" if out else ""
        for var_label in not_defined:
            out += (
                f"The independent variable <b>{util.replace_leading_trailing_chars(var_label, ' ', '&#9608;')}</b> "
                f"present in {len(not_defined[var_label])} observation(s) is not defined.<br>"
            )

    # check values of independent variables
    defined_set_var_label: dict = dict(
        [
            (
                pj[cfg.INDEPENDENT_VARIABLES][idx]["label"],
                pj[cfg.INDEPENDENT_VARIABLES][idx]["possible values"],
            )
            for idx in pj.get(cfg.INDEPENDENT_VARIABLES, {})
            if pj[cfg.INDEPENDENT_VARIABLES][idx]["type"] == "value from set"
        ]
    )

    out += "<br><br>" if out else ""
    for obs_id in pj[cfg.OBSERVATIONS]:
        if cfg.INDEPENDENT_VARIABLES not in pj[cfg.OBSERVATIONS][obs_id]:
            continue
        for var_label in pj[cfg.OBSERVATIONS][obs_id][cfg.INDEPENDENT_VARIABLES]:
            if var_label in defined_set_var_label:
                if pj[cfg.OBSERVATIONS][obs_id][cfg.INDEPENDENT_VARIABLES][var_label] not in defined_set_var_label[var_label].split(","):
                    out += (
                        f"{obs_id}: the <b>{pj[cfg.OBSERVATIONS][obs_id][cfg.INDEPENDENT_VARIABLES][var_label]}</b> value "
                        f" is not allowed for {var_label} (choose between {defined_set_var_label[var_label]})<br>"
                    )

    return out


def create_subtitles(pj: dict, selected_observations: list, parameters: dict, export_dir: str) -> Tuple[bool, str]:
    """
    create subtitles for selected observations, subjects and behaviors

    Args:
        pj (dict): project
        selected_observations (list): list of observations
        parameters (dict):
        export_dir (str): directory to save subtitles

    Returns:
        bool: True if OK else False
        str: error message
    """

    def subject_color(subject: str) -> Tuple[str, str]:
        """
        subject color

        Args:
            subject (str): subject name

        Returns:
            str: HTML tag for color font (beginning)
            str: HTML tag for color font (closing)
        """
        if subject == cfg.NO_FOCAL_SUBJECT:
            return "", ""
        else:
            return (
                f"""<font color="{cfg.subtitlesColors[
                        parameters[cfg.SELECTED_SUBJECTS].index(row['subject']) % len(cfg.subtitlesColors)
                    ]}">""",
                "</font>",
            )

    ok, msg, db_connector = db_functions.load_aggregated_events_in_db(
        pj,
        parameters[cfg.SELECTED_SUBJECTS],
        selected_observations,
        parameters[cfg.SELECTED_BEHAVIORS],
    )
    if not ok:
        return False, msg

    cursor = db_connector.cursor()
    flag_ok = True
    msg = ""
    mem_command = ""
    for obs_id in selected_observations:
        if pj[cfg.OBSERVATIONS][obs_id][cfg.TYPE] == cfg.LIVE:
            out = ""
            if parameters["time"] in (cfg.TIME_EVENTS, cfg.TIME_FULL_OBS):
                cursor.execute(
                    (
                        "SELECT subject, behavior, start, stop, type, modifiers FROM aggregated_events "
                        "WHERE observation = ? "
                        "AND subject in ({}) "
                        "AND behavior in ({}) "
                        "ORDER BY start"
                    ).format(
                        ",".join(["?"] * len(parameters[cfg.SELECTED_SUBJECTS])),
                        ",".join(["?"] * len(parameters[cfg.SELECTED_BEHAVIORS])),
                    ),
                    [
                        obs_id,
                    ]
                    + parameters[cfg.SELECTED_SUBJECTS]
                    + parameters[cfg.SELECTED_BEHAVIORS],
                )

            else:  # arbitrary 'time interval'
                cursor.execute(
                    (
                        "SELECT subject, behavior, start, stop, type, modifiers FROM aggregated_events "
                        "WHERE observation = ? "
                        "AND (start BETWEEN ? AND ?) "
                        "AND subject in ({}) "
                        "AND behavior in ({}) "
                        "ORDER BY start"
                    ).format(
                        ",".join(["?"] * len(parameters[cfg.SELECTED_SUBJECTS])),
                        ",".join(["?"] * len(parameters[cfg.SELECTED_BEHAVIORS])),
                    ),
                    [
                        obs_id,
                        float(parameters[cfg.START_TIME]),
                        float(parameters[cfg.END_TIME]),
                    ]
                    + parameters[cfg.SELECTED_SUBJECTS]
                    + parameters[cfg.SELECTED_BEHAVIORS],
                )

            for idx, row in enumerate(cursor.fetchall()):
                col1, col2 = subject_color(row["subject"])
                if parameters["include modifiers"]:
                    modifiers_str = f"\n{row['modifiers'].replace('|', ', ')}"
                else:
                    modifiers_str = ""
                out += ("{idx}\n" "{start} --> {stop}\n" "{col1}{subject}: {behavior}" "{modifiers}" "{col2}\n\n").format(
                    idx=idx + 1,
                    start=util.seconds2time(row["start"]).replace(".", ","),
                    stop=util.seconds2time(row["stop"] if row["type"] == cfg.STATE else row["stop"] + cfg.POINT_EVENT_ST_DURATION).replace(
                        ".", ","
                    ),
                    col1=col1,
                    col2=col2,
                    subject=row["subject"],
                    behavior=row["behavior"],
                    modifiers=modifiers_str,
                )

            file_name = pl.Path(export_dir) / pl.Path(util.safeFileName(obs_id)).with_suffix(".srt")

            if mem_command not in (cfg.OVERWRITE_ALL, cfg.SKIP_ALL) and file_name.is_file():
                mem_command = dialog.MessageDialog(
                    cfg.programName,
                    f"The file {file_name} already exists.",
                    [
                        cfg.OVERWRITE,
                        cfg.OVERWRITE_ALL,
                        cfg.SKIP,
                        cfg.SKIP_ALL,
                        cfg.CANCEL,
                    ],
                )
                if mem_command == cfg.CANCEL:
                    return False, ""
                if mem_command in (cfg.SKIP, cfg.SKIP_ALL):
                    continue

            try:
                with file_name.open("w", encoding="utf-8") as f_out:
                    f_out.write(out)
            except Exception:
                flag_ok = False
                msg += f"observation: {obs_id}\ngave the following error:\n{str(sys.exc_info()[1])}\n"

        if pj[cfg.OBSERVATIONS][obs_id][cfg.TYPE] == cfg.MEDIA:
            for nplayer in cfg.ALL_PLAYERS:
                if not pj[cfg.OBSERVATIONS][obs_id][cfg.FILE][nplayer]:
                    continue
                init = 0
                for media_file in pj[cfg.OBSERVATIONS][obs_id][cfg.FILE][nplayer]:
                    try:
                        end = init + pj[cfg.OBSERVATIONS][obs_id][cfg.MEDIA_INFO][cfg.LENGTH][media_file]
                    except KeyError:
                        return (
                            False,
                            f"The length for media file {media_file} is not available",
                        )
                    out = ""

                    if parameters["time"] in (cfg.TIME_EVENTS, cfg.TIME_FULL_OBS):
                        cursor.execute(
                            (
                                "SELECT subject, behavior, start, stop, type, modifiers FROM aggregated_events "
                                "WHERE observation = ? "
                                "AND (start BETWEEN ? AND ?) "
                                "AND subject in ({}) "
                                "AND behavior in ({}) "
                                "ORDER BY start"
                            ).format(
                                ",".join(["?"] * len(parameters[cfg.SELECTED_SUBJECTS])),
                                ",".join(["?"] * len(parameters[cfg.SELECTED_BEHAVIORS])),
                            ),
                            [
                                obs_id,
                                init,
                                end,
                            ]
                            + parameters[cfg.SELECTED_SUBJECTS]
                            + parameters[cfg.SELECTED_BEHAVIORS],
                        )

                    else:  # arbitrary 'time interval'
                        cursor.execute(
                            (
                                "SELECT subject, behavior, type, start, stop, modifiers FROM aggregated_events "
                                "WHERE observation = ? "
                                "AND (start BETWEEN ? AND ?) "
                                "AND (start BETWEEN ? AND ?) "
                                "AND subject in ({}) "
                                "AND behavior in ({}) "
                                "ORDER BY start"
                            ).format(
                                ",".join(["?"] * len(parameters[cfg.SELECTED_SUBJECTS])),
                                ",".join(["?"] * len(parameters[cfg.SELECTED_BEHAVIORS])),
                            ),
                            [
                                obs_id,
                                init,
                                end,
                                float(parameters[cfg.START_TIME]),
                                float(parameters[cfg.END_TIME]),
                            ]
                            + parameters[cfg.SELECTED_SUBJECTS]
                            + parameters[cfg.SELECTED_BEHAVIORS],
                        )

                    for idx, row in enumerate(cursor.fetchall()):
                        col1, col2 = subject_color(row["subject"])
                        if parameters["include modifiers"]:
                            modifiers_str = f"\n{row['modifiers'].replace('|', ', ')}"
                        else:
                            modifiers_str = ""

                        out += ("{idx}\n" "{start} --> {stop}\n" "{col1}{subject}: {behavior}" "{modifiers}" "{col2}\n\n").format(
                            idx=idx + 1,
                            start=util.seconds2time(row["start"] - init).replace(".", ","),
                            stop=util.seconds2time(
                                (row["stop"] if row["type"] == cfg.STATE else row["stop"] + cfg.POINT_EVENT_ST_DURATION) - init
                            ).replace(".", ","),
                            col1=col1,
                            col2=col2,
                            subject=row["subject"],
                            behavior=row["behavior"],
                            modifiers=modifiers_str,
                        )
                    file_name = pl.Path(export_dir) / pl.Path(pl.Path(media_file).stem).with_suffix(".srt")

                    if mem_command not in (cfg.OVERWRITE_ALL, cfg.SKIP_ALL) and file_name.is_file():
                        mem_command = dialog.MessageDialog(
                            cfg.programName,
                            f"The file {file_name} already exists.",
                            [
                                cfg.OVERWRITE,
                                cfg.OVERWRITE_ALL,
                                cfg.SKIP,
                                cfg.SKIP_ALL,
                                cfg.CANCEL,
                            ],
                        )
                        if mem_command == cfg.CANCEL:
                            return False, ""
                        if mem_command in (cfg.SKIP, cfg.SKIP_ALL):
                            continue
                    try:
                        with file_name.open("w", encoding="utf-8") as f_out:
                            f_out.write(out)
                    except Exception:
                        flag_ok = False
                        msg += f"observation: {obs_id}\ngave the following error:\n{sys.exc_info()[1]}\n"

                    init = end

    return flag_ok, msg


def export_observations_list(pj: dict, selected_observations: list, file_name: str, output_format: str) -> bool:
    """
    create file with a list of selected observations

    Args:
        pj (dict): project dictionary
        selected_observations (list): list of observations to export
        file_name (str): path of file to save list of observations
        output_format (str): format output

    Returns:
        bool: True of OK else False
    """

    data = tablib.Dataset()
    data.headers = [
        "Observation id",
        "Date",
        "Description",
        "Subjects",
        "Media files/Live observation",
    ]

    indep_var_header = []
    if cfg.INDEPENDENT_VARIABLES in pj:
        for idx in util.sorted_keys(pj[cfg.INDEPENDENT_VARIABLES]):
            indep_var_header.append(pj[cfg.INDEPENDENT_VARIABLES][idx]["label"])
    data.headers.extend(indep_var_header)

    for obs_id in selected_observations:
        subjects_list = sorted(list(set([x[cfg.EVENT_SUBJECT_FIELD_IDX] for x in pj[cfg.OBSERVATIONS][obs_id][cfg.EVENTS]])))
        if "" in subjects_list:
            subjects_list = [cfg.NO_FOCAL_SUBJECT] + subjects_list
            subjects_list.remove("")
        subjects = ", ".join(subjects_list)

        if pj[cfg.OBSERVATIONS][obs_id][cfg.TYPE] == cfg.LIVE:
            media_files = ["Live observation"]
        elif pj[cfg.OBSERVATIONS][obs_id][cfg.TYPE] == cfg.MEDIA:
            media_files = []
            if pj[cfg.OBSERVATIONS][obs_id][cfg.FILE]:
                for player in sorted(pj[cfg.OBSERVATIONS][obs_id][cfg.FILE].keys()):
                    for media in pj[cfg.OBSERVATIONS][obs_id][cfg.FILE][player]:
                        media_files.append(f"#{player}: {media}")

        # independent variables
        indep_var = []
        if cfg.INDEPENDENT_VARIABLES in pj[cfg.OBSERVATIONS][obs_id]:
            for var_label in indep_var_header:
                if var_label in pj[cfg.OBSERVATIONS][obs_id][cfg.INDEPENDENT_VARIABLES]:
                    indep_var.append(pj[cfg.OBSERVATIONS][obs_id][cfg.INDEPENDENT_VARIABLES][var_label])
                else:
                    indep_var.append("")

        data.append(
            [
                obs_id,
                pj[cfg.OBSERVATIONS][obs_id]["date"],
                pj[cfg.OBSERVATIONS][obs_id]["description"],
                subjects,
                ", ".join(media_files),
            ]
            + indep_var
        )

    if output_format in (cfg.TSV_EXT, cfg.CSV_EXT, cfg.HTML_EXT):
        try:
            with open(file_name, "wb") as f:
                f.write(str.encode(data.export(output_format)))
        except Exception:
            return False
    if output_format in [cfg.ODS_EXT, cfg.XLS_EXT, cfg.XLSX_EXT]:
        try:
            with open(file_name, "wb") as f:
                f.write(data.export(output_format))
        except Exception:
            return False

    return True


def set_media_paths_relative_to_project_dir(pj: dict, project_file_name: str) -> bool:
    """
    set path from media files and path of images directory relative to the project directory

    Args:
        pj (dict): project
        project_file_name (str): path of the project file

    Returns:
        bool: True if project changed else False
    """

    # chek if media and images dir are relative to project dir
    for obs_id in pj[cfg.OBSERVATIONS]:
        if pj[cfg.OBSERVATIONS][obs_id][cfg.TYPE] == cfg.IMAGES:
            for img_dir in pj[cfg.OBSERVATIONS][obs_id][cfg.DIRECTORIES_LIST]:
                try:
                    pl.Path(img_dir).relative_to(pl.Path(project_file_name).parent)
                except ValueError:
                    if pl.Path(img_dir).is_absolute() or not (pl.Path(project_file_name).parent / pl.Path(img_dir)).is_dir():
                        QMessageBox.critical(
                            None,
                            cfg.programName,
                            f"Observation <b>{obs_id}</b>:<br>the path of <b>{img_dir}</b> is not relative to <b>{project_file_name}</b>.",
                        )
                        return False

        if pj[cfg.OBSERVATIONS][obs_id][cfg.TYPE] == cfg.MEDIA:
            for n_player in cfg.ALL_PLAYERS:
                if n_player in pj[cfg.OBSERVATIONS][obs_id][cfg.FILE]:
                    for idx, media_file in enumerate(pj[cfg.OBSERVATIONS][obs_id][cfg.FILE][n_player]):
                        try:
                            pl.Path(media_file).relative_to(pl.Path(project_file_name).parent)
                        except ValueError:
                            if pl.Path(media_file).is_absolute() or not (pl.Path(project_file_name).parent / pl.Path(media_file)).is_file():
                                QMessageBox.critical(
                                    None,
                                    cfg.programName,
                                    (
                                        f"Observation <b>{obs_id}</b>:"
                                        f"<br>the path of <b>{media_file}</b> is not relative to <b>{project_file_name}</b>"
                                    ),
                                )
                                return False

    # set media path and image dir relative to project dir
    flag_changed = False
    for obs_id in pj[cfg.OBSERVATIONS]:
        if pj[cfg.OBSERVATIONS][obs_id][cfg.TYPE] == cfg.IMAGES:
            new_dir_list = []
            for img_dir in pj[cfg.OBSERVATIONS][obs_id][cfg.DIRECTORIES_LIST]:
                try:
                    new_dir_list.append(str(pl.Path(img_dir).relative_to(pl.Path(project_file_name).parent)))
                except ValueError:
                    if not pl.Path(img_dir).is_absolute() and (pl.Path(project_file_name).parent / pl.Path(img_dir)).is_dir():
                        new_dir_list.append(img_dir)

            if pj[cfg.OBSERVATIONS][obs_id][cfg.DIRECTORIES_LIST] != new_dir_list:
                flag_changed = True
            pj[cfg.OBSERVATIONS][obs_id][cfg.DIRECTORIES_LIST] = new_dir_list

        if pj[cfg.OBSERVATIONS][obs_id][cfg.TYPE] == cfg.MEDIA:
            for n_player in cfg.ALL_PLAYERS:
                if n_player in pj[cfg.OBSERVATIONS][obs_id][cfg.FILE]:
                    for idx, media_file in enumerate(pj[cfg.OBSERVATIONS][obs_id][cfg.FILE][n_player]):
                        try:
                            p = str(pl.Path(media_file).relative_to(pl.Path(project_file_name).parent))
                        except ValueError:
                            if (
                                not pl.Path(media_file).is_absolute()
                                and (pl.Path(project_file_name).parent / pl.Path(media_file)).is_file()
                            ):
                                p = media_file
                        if p != media_file:
                            flag_changed = True
                            pj[cfg.OBSERVATIONS][obs_id][cfg.FILE][n_player][idx] = p
                            if cfg.MEDIA_INFO in pj[cfg.OBSERVATIONS][obs_id]:
                                for info in [
                                    cfg.LENGTH,
                                    cfg.HAS_AUDIO,
                                    cfg.HAS_VIDEO,
                                    cfg.FPS,
                                ]:
                                    if (
                                        info in pj[cfg.OBSERVATIONS][obs_id][cfg.MEDIA_INFO]
                                        and media_file in pj[cfg.OBSERVATIONS][obs_id][cfg.MEDIA_INFO][info]
                                    ):
                                        # add new file path
                                        pj[cfg.OBSERVATIONS][obs_id][cfg.MEDIA_INFO][info][p] = pj[cfg.OBSERVATIONS][obs_id][
                                            cfg.MEDIA_INFO
                                        ][info][media_file]
                                        # remove old path
                                        del pj[cfg.OBSERVATIONS][obs_id][cfg.MEDIA_INFO][info][media_file]
    return flag_changed


def set_data_paths_relative_to_project_dir(pj: dict, project_file_name: str) -> bool:
    """
    set path from media files and path of images directory relative to the project directory

        Args:
        pj (dict): project
        project_file_name (str): path of the project file

    Returns:
        bool: True if project changed else False
    """
    # chek if data paths are relative to project dir
    for obs_id in pj[cfg.OBSERVATIONS]:
        for _, v in pj[cfg.OBSERVATIONS][obs_id].get(cfg.PLOT_DATA, {}).items():
            if cfg.FILE_PATH in v:
                try:
                    pl.Path(v[cfg.FILE_PATH]).relative_to(pl.Path(project_file_name).parent)
                except ValueError:
                    # check if file is in project dir
                    if (
                        pl.Path(v[cfg.FILE_PATH]).is_absolute()
                        or not (pl.Path(project_file_name).parent / pl.Path(v[cfg.FILE_PATH])).is_file()
                    ):
                        QMessageBox.critical(
                            None,
                            cfg.programName,
                            (
                                f"Observation <b>{obs_id}</b>:"
                                f"<br>the path of <b>{v[cfg.FILE_PATH]}</b> "
                                f"is not relative to <b>{project_file_name}</b>."
                            ),
                        )
                        return False

    flag_changed = False
    for obs_id in pj[cfg.OBSERVATIONS]:
        if pj[cfg.OBSERVATIONS][obs_id][cfg.TYPE] != cfg.MEDIA:
            continue
        for idx, v in pj[cfg.OBSERVATIONS][obs_id].get(cfg.PLOT_DATA, {}).items():
            if cfg.FILE_PATH in v:
                try:
                    p = str(pl.Path(v[cfg.FILE_PATH]).relative_to(pl.Path(project_file_name).parent))
                except ValueError:
                    # check if file is in project dir
                    if (
                        not pl.Path(v[cfg.FILE_PATH]).is_absolute()
                        and (pl.Path(project_file_name).parent / pl.Path(v[cfg.FILE_PATH])).is_file()
                    ):
                        p = v[cfg.FILE_PATH]

                if p != v[cfg.FILE_PATH]:
                    pj[cfg.OBSERVATIONS][obs_id][cfg.PLOT_DATA][idx][cfg.FILE_PATH] = p
                    flag_changed = True

    return flag_changed


def remove_data_files_path(pj: dict) -> None:
    """
    remove path from data files

    Args:
        pj (dict): project file

    Returns:
        None
    """

    for obs_id in pj[cfg.OBSERVATIONS]:
        if pj[cfg.OBSERVATIONS][obs_id][cfg.TYPE] != cfg.MEDIA:
            continue
        if cfg.PLOT_DATA in pj[cfg.OBSERVATIONS][obs_id]:
            for idx in pj[cfg.OBSERVATIONS][obs_id][cfg.PLOT_DATA]:
                if "file_path" in pj[cfg.OBSERVATIONS][obs_id][cfg.PLOT_DATA][idx]:
                    p = str(pl.Path(pj[cfg.OBSERVATIONS][obs_id][cfg.PLOT_DATA][idx]["file_path"]).name)
                    if p != pj[cfg.OBSERVATIONS][obs_id][cfg.PLOT_DATA][idx]["file_path"]:
                        pj[cfg.OBSERVATIONS][obs_id][cfg.PLOT_DATA][idx]["file_path"] = p


def remove_media_files_path(pj: dict, project_file_name: str) -> bool:
    """
    remove path from media files and from images directory
    tested

    Args:
        pj (dict): project file

    Returns:
        None
    """

    file_not_found = []
    # check if media and images dir
    for obs_id in pj[cfg.OBSERVATIONS]:
        if pj[cfg.OBSERVATIONS][obs_id][cfg.TYPE] == cfg.IMAGES:
            for img_dir in pj[cfg.OBSERVATIONS][obs_id][cfg.DIRECTORIES_LIST]:
                if full_path(pl.Path(img_dir).name, project_file_name) == "":
                    file_not_found.append(img_dir)

        if pj[cfg.OBSERVATIONS][obs_id][cfg.TYPE] == cfg.MEDIA:
            for n_player in cfg.ALL_PLAYERS:
                if n_player in pj[cfg.OBSERVATIONS][obs_id][cfg.FILE]:
                    for idx, media_file in enumerate(pj[cfg.OBSERVATIONS][obs_id][cfg.FILE][n_player]):
                        if full_path(pl.Path(media_file).name, project_file_name) == "":
                            file_not_found.append(media_file)

    file_not_found = set(file_not_found)
    if file_not_found:
        if (
            dialog.MessageDialog(
                cfg.programName,
                (
                    "Some media files / images directories will not be found after this operation:<br><br>"
                    f"{',<br>'.join(file_not_found)}"
                    "<br><br>Are you sure to continue?"
                ),
                [cfg.YES, cfg.NO],
            )
            == cfg.NO
        ):
            return False

    flag_changed = False
    for obs_id in pj[cfg.OBSERVATIONS]:
        if pj[cfg.OBSERVATIONS][obs_id][cfg.TYPE] == cfg.IMAGES:
            new_img_dir_list = []
            for img_dir in pj[cfg.OBSERVATIONS][obs_id][cfg.DIRECTORIES_LIST]:
                if img_dir != pl.Path(img_dir).name:
                    flag_changed = True
                new_img_dir_list.append(str(pl.Path(img_dir).name))
            pj[cfg.OBSERVATIONS][obs_id][cfg.DIRECTORIES_LIST] = new_img_dir_list

        if pj[cfg.OBSERVATIONS][obs_id][cfg.TYPE] == cfg.MEDIA:
            for n_player in cfg.ALL_PLAYERS:
                if n_player in pj[cfg.OBSERVATIONS][obs_id][cfg.FILE]:
                    for idx, media_file in enumerate(pj[cfg.OBSERVATIONS][obs_id][cfg.FILE][n_player]):
                        p = pl.Path(media_file).name
                        if p != media_file:
                            flag_changed = True
                            pj[cfg.OBSERVATIONS][obs_id][cfg.FILE][n_player][idx] = p
                            if cfg.MEDIA_INFO in pj[cfg.OBSERVATIONS][obs_id]:
                                for info in [
                                    cfg.LENGTH,
                                    cfg.HAS_AUDIO,
                                    cfg.HAS_VIDEO,
                                    cfg.FPS,
                                ]:
                                    if (
                                        info in pj[cfg.OBSERVATIONS][obs_id][cfg.MEDIA_INFO]
                                        and media_file in pj[cfg.OBSERVATIONS][obs_id][cfg.MEDIA_INFO][info]
                                    ):
                                        # add new file path
                                        pj[cfg.OBSERVATIONS][obs_id][cfg.MEDIA_INFO][info][p] = pj[cfg.OBSERVATIONS][obs_id][
                                            cfg.MEDIA_INFO
                                        ][info][media_file]
                                        # remove old path
                                        del pj[cfg.OBSERVATIONS][obs_id][cfg.MEDIA_INFO][info][media_file]

    return flag_changed


def full_path(path: str, project_file_name: str) -> str:
    """
    returns the media/data full path or the images directory full path
    add path of BORIS project if media/data/pictures dir with relative path

    Args:
        path (str): file path or images directory path
        project_file_name (str): project file name

    Returns:
        str: full path
    """

    source_path = pl.Path(path)
    if source_path.exists():
        return str(source_path)
    else:
        # check relative path (to project path)
        project_path = pl.Path(project_file_name)
        if (project_path.parent / source_path).exists():
            return str(project_path.parent / source_path)
        else:
            return ""


def observed_interval(observation: dict) -> Tuple[dec, dec]:
    """
    Observed interval for observation

    Args:
        observation (dict): observation dictionary

    Returns:
        Tuple of 2 Decimals: time of first observed event, time of last observed event
    """
    if not observation[cfg.EVENTS]:
        return (dec("0.0"), dec("0.0"))
    if observation[cfg.TYPE] in (cfg.MEDIA, cfg.LIVE):
        """
        print("=" * 120)
        print(observation[cfg.EVENTS])
        print("=" * 120)
        """

        event_timestamp = [event[cfg.PJ_OBS_FIELDS[observation[cfg.TYPE]][cfg.TIME]] for event in observation[cfg.EVENTS]]

        return (
            min(event_timestamp),
            max(event_timestamp),
        )
    if observation[cfg.TYPE] == cfg.IMAGES:
        events = [x[cfg.PJ_OBS_FIELDS[observation[cfg.TYPE]][cfg.IMAGE_INDEX]] for x in observation[cfg.EVENTS]]

        return (dec(min(events)), dec(max(events)))


def events_start_stop(ethogram: dict, events: list, obs_type: str) -> List[tuple]:
    """
    returns events with status (START/STOP or POINT)

    Args:
        events (list): list of events

    Returns:
        list: list of events with type (POINT or STATE)
    """

    state_events_list = util.state_behavior_codes(ethogram)

    events_flagged: list = []
    for idx, event in enumerate(events):
        _, subject, code, modifier = event[: cfg.EVENT_MODIFIER_FIELD_IDX + 1]

        # check if code is state
        if code in state_events_list:
            # how many code before with same subject?
            if (
                len(
                    [
                        x[cfg.EVENT_BEHAVIOR_FIELD_IDX]
                        for idx1, x in enumerate(events)
                        if x[cfg.EVENT_BEHAVIOR_FIELD_IDX] == code
                        and idx1 < idx
                        and x[cfg.EVENT_SUBJECT_FIELD_IDX] == subject
                        and x[cfg.EVENT_MODIFIER_FIELD_IDX] == modifier
                    ]
                )
                % 2
            ):  # test if odd
                flag = cfg.STOP
            else:
                flag = cfg.START
        else:
            flag = cfg.POINT

        # no frame_index
        if obs_type == cfg.MEDIA and len(event) == 5:
            events_flagged.append(
                tuple(event)
                + (
                    cfg.NA,
                    flag,
                )
            )
        else:
            events_flagged.append(tuple(event) + (flag,))

    return events_flagged


def extract_observed_subjects(pj: dict, selected_observations: list) -> list:
    """
    extract unique subjects present in observations list

    return: list
    """

    observed_subjects = []

    # extract events from selected observations
    for events in [pj[cfg.OBSERVATIONS][x][cfg.EVENTS] for x in pj[cfg.OBSERVATIONS] if x in selected_observations]:
        for event in events:
            observed_subjects.append(event[cfg.EVENT_SUBJECT_FIELD_IDX])

    # remove duplicate
    return list(set(observed_subjects))


def open_project_json(projectFileName: str) -> tuple:
    """
    open BORIS project file in json format or GZ compressed json format

    Args:
        projectFileName (str): path of project

    Returns:
        str: project path
        bool: True if project changed
        dict: BORIS project
        str: message
    """

    logging.debug(f"open project: {projectFileName}")

    projectChanged = False
    msg = ""

    if not os.path.isfile(projectFileName):
        return (
            projectFileName,
            projectChanged,
            {"error": f"File {projectFileName} not found"},
            msg,
        )

    try:
        if projectFileName.endswith(".boris.gz"):
            file_in = gzip.open(projectFileName, mode="rt", encoding="utf-8")
        else:
            file_in = open(projectFileName, "r")
        file_content = file_in.read()
    except PermissionError:
        return (
            projectFileName,
            projectChanged,
            {"error": f"File {projectFileName}: Permission denied"},
            msg,
        )
    except Exception:
        return (
            projectFileName,
            projectChanged,
            {"error": f"Error on file {projectFileName}: {sys.exc_info()[1]}"},
            msg,
        )

    try:
        pj = json.loads(file_content)
    except json.decoder.JSONDecodeError:
        return (
            projectFileName,
            projectChanged,
            {"error": "This project file seems corrupted"},
            msg,
        )
    except Exception:
        return (
            projectFileName,
            projectChanged,
            {"error": f"Error on file {projectFileName}: {sys.exc_info()[1]}"},
            msg,
        )

    # transform time to decimal
    pj = util.convert_time_to_decimal(pj)

    # add coding_map key to old project files
    if "coding_map" not in pj:
        pj["coding_map"] = {}
        projectChanged = True

    # add subject description
    if cfg.PROJECT_VERSION in pj:
        for idx in [x for x in pj[cfg.SUBJECTS]]:
            if "description" not in pj[cfg.SUBJECTS][idx]:
                pj[cfg.SUBJECTS][idx]["description"] = ""
                projectChanged = True

    # check if project file version is newer than current BORIS project file version
    if cfg.PROJECT_VERSION in pj and util.versiontuple(pj[cfg.PROJECT_VERSION]) > util.versiontuple(version.__version__):
        return (
            projectFileName,
            projectChanged,
            {
                "error": (
                    "This project file was created with a more recent version of BORIS.<br>"
                    f"You must update BORIS to <b>v. >= {pj[cfg.PROJECT_VERSION]}</b> to open this project"
                )
            },
            msg,
        )

    # check if old version  v. 0 *.obs
    if cfg.PROJECT_VERSION not in pj:
        # convert VIDEO, AUDIO -> MEDIA
        pj[cfg.PROJECT_VERSION] = cfg.project_format_version
        projectChanged = True

        for obs in [x for x in pj[cfg.OBSERVATIONS]]:
            # remove 'replace audio' key
            if "replace audio" in pj[cfg.OBSERVATIONS][obs]:
                del pj[cfg.OBSERVATIONS][obs]["replace audio"]

            if pj[cfg.OBSERVATIONS][obs][cfg.TYPE] in ["VIDEO", "AUDIO"]:
                pj[cfg.OBSERVATIONS][obs][cfg.TYPE] = cfg.MEDIA

            # convert old media list in new one
            if len(pj[cfg.OBSERVATIONS][obs][cfg.FILE]):
                d1 = {cfg.PLAYER1: [pj[cfg.OBSERVATIONS][obs][cfg.FILE][0]]}

            if len(pj[cfg.OBSERVATIONS][obs][cfg.FILE]) == 2:
                d1[cfg.PLAYER2] = [pj[cfg.OBSERVATIONS][obs][cfg.FILE][1]]

            pj[cfg.OBSERVATIONS][obs][cfg.FILE] = d1

        # convert VIDEO, AUDIO -> MEDIA
        for idx in [x for x in pj[cfg.SUBJECTS]]:
            key, name = pj[cfg.SUBJECTS][idx]
            pj[cfg.SUBJECTS][idx] = {"key": key, "name": name, "description": ""}

        msg = (
            f"The project file was converted to the new format (v. {cfg.project_format_version}) in use with your version of BORIS.<br>"
            "Choose a new file name for saving it."
        )
        projectFileName = ""

    # update modifiers to JSON format

    # check if project format version < 4 (modifiers were str)
    project_lowerthan4 = False
    if cfg.PROJECT_VERSION in pj and util.versiontuple(pj[cfg.PROJECT_VERSION]) < util.versiontuple("4.0"):
        for idx in pj[cfg.ETHOGRAM]:
            if pj[cfg.ETHOGRAM][idx]["modifiers"]:
                if isinstance(pj[cfg.ETHOGRAM][idx]["modifiers"], str):
                    project_lowerthan4 = True
                    modif_set_list = pj[cfg.ETHOGRAM][idx]["modifiers"].split("|")
                    modif_set_dict = {}
                    for modif_set in modif_set_list:
                        modif_set_dict[str(len(modif_set_dict))] = {
                            "name": "",
                            "type": cfg.SINGLE_SELECTION,
                            "values": modif_set.split(","),
                        }
                    pj[cfg.ETHOGRAM][idx]["modifiers"] = dict(modif_set_dict)
            else:
                pj[cfg.ETHOGRAM][idx]["modifiers"] = {}

        if not project_lowerthan4:
            msg = "The project version was updated from {} to {}".format(pj[cfg.PROJECT_VERSION], cfg.project_format_version)
            pj[cfg.PROJECT_VERSION] = cfg.project_format_version
            projectChanged = True

    # add category key if not found
    for idx in pj[cfg.ETHOGRAM]:
        if "category" not in pj[cfg.ETHOGRAM][idx]:
            pj[cfg.ETHOGRAM][idx]["category"] = ""

    # if one file is present in player #1 -> set "media_info" key with value of media_file_info
    for obs in pj[cfg.OBSERVATIONS]:
        if pj[cfg.OBSERVATIONS][obs][cfg.TYPE] in [cfg.MEDIA] and cfg.MEDIA_INFO not in pj[cfg.OBSERVATIONS][obs]:
            pj[cfg.OBSERVATIONS][obs][cfg.MEDIA_INFO] = {
                cfg.LENGTH: {},
                cfg.FPS: {},
                cfg.HAS_VIDEO: {},
                cfg.HAS_AUDIO: {},
            }
            for player in (cfg.PLAYER1, cfg.PLAYER2):
                # fix bug Anne Maijer 2017-07-17
                if pj[cfg.OBSERVATIONS][obs][cfg.FILE] == []:
                    pj[cfg.OBSERVATIONS][obs][cfg.FILE] = {"1": [], "2": []}

                for media_file_path in pj[cfg.OBSERVATIONS][obs]["file"][player]:
                    # FIX: ffmpeg path
                    ret, ffmpeg_bin = util.check_ffmpeg_path()
                    if not ret:
                        return (
                            projectFileName,
                            projectChanged,
                            {"error": "FFmpeg path not found"},
                            "",
                        )
                    else:
                        ffmpeg_bin = msg

                    r = util.accurate_media_analysis(ffmpeg_bin, media_file_path)

                    if "duration" in r and r["duration"]:
                        pj[cfg.OBSERVATIONS][obs][cfg.MEDIA_INFO][cfg.LENGTH][media_file_path] = float(r["duration"])
                        pj[cfg.OBSERVATIONS][obs][cfg.MEDIA_INFO][cfg.FPS][media_file_path] = float(r["fps"])
                        pj[cfg.OBSERVATIONS][obs][cfg.MEDIA_INFO][cfg.HAS_VIDEO][media_file_path] = r["has_video"]
                        pj[cfg.OBSERVATIONS][obs][cfg.MEDIA_INFO][cfg.HAS_AUDIO][media_file_path] = r["has_audio"]
                        projectChanged = True
                    else:  # file path not found
                        if (
                            cfg.MEDIA_FILE_INFO in pj[cfg.OBSERVATIONS][obs]
                            and len(pj[cfg.OBSERVATIONS][obs][cfg.MEDIA_FILE_INFO]) == 1
                            and len(pj[cfg.OBSERVATIONS][obs][cfg.FILE][cfg.PLAYER1]) == 1
                            and len(pj[cfg.OBSERVATIONS][obs][cfg.FILE][cfg.PLAYER2]) == 0
                        ):
                            media_md5_key = list(pj[cfg.OBSERVATIONS][obs][cfg.MEDIA_FILE_INFO].keys())[0]
                            # duration
                            pj[cfg.OBSERVATIONS][obs][cfg.MEDIA_INFO] = {
                                cfg.LENGTH: {
                                    media_file_path: pj[cfg.OBSERVATIONS][obs][cfg.MEDIA_FILE_INFO][media_md5_key]["video_length"] / 1000
                                }
                            }
                            projectChanged = True

                            # FPS
                            if "nframe" in pj[cfg.OBSERVATIONS][obs][cfg.MEDIA_FILE_INFO][media_md5_key]:
                                pj[cfg.OBSERVATIONS][obs][cfg.MEDIA_INFO][cfg.FPS] = {
                                    media_file_path: pj[cfg.OBSERVATIONS][obs][cfg.MEDIA_FILE_INFO][media_md5_key]["nframe"]
                                    / (pj[cfg.OBSERVATIONS][obs][cfg.MEDIA_FILE_INFO][media_md5_key]["video_length"] / 1000)
                                }
                            else:
                                pj[cfg.OBSERVATIONS][obs][cfg.MEDIA_INFO][cfg.FPS] = {media_file_path: 0}

    # update project to v.7 for time offset second player
    project_lowerthan7 = False
    for obs in pj[cfg.OBSERVATIONS]:
        if "time offset second player" in pj[cfg.OBSERVATIONS][obs]:
            if cfg.MEDIA_INFO not in pj[cfg.OBSERVATIONS][obs]:
                pj[cfg.OBSERVATIONS][obs][cfg.MEDIA_INFO] = {}
            if cfg.OFFSET not in pj[cfg.OBSERVATIONS][obs][cfg.MEDIA_INFO]:
                pj[cfg.OBSERVATIONS][obs][cfg.MEDIA_INFO][cfg.OFFSET] = {}
            for player in pj[cfg.OBSERVATIONS][obs][cfg.FILE]:
                pj[cfg.OBSERVATIONS][obs][cfg.MEDIA_INFO][cfg.OFFSET][player] = 0.0
            if pj[cfg.OBSERVATIONS][obs]["time offset second player"]:
                pj[cfg.OBSERVATIONS][obs][cfg.MEDIA_INFO][cfg.OFFSET]["2"] = float(pj[cfg.OBSERVATIONS][obs]["time offset second player"])

            del pj[cfg.OBSERVATIONS][obs]["time offset second player"]
            project_lowerthan7 = True

            msg = (
                f"The project file was converted to the new format (v. {cfg.project_format_version}) in use with your version of BORIS.<br>"
                f"Please note that this new version will NOT be compatible with previous BORIS versions "
                f"(&lt; v. {cfg.project_format_version}).<br>"
            )

            projectChanged = True

    if project_lowerthan7:
        msg = f"The project was updated to the current project version ({cfg.project_format_version})."

        try:
            old_project_file_name = projectFileName.replace(".boris", f".v{pj['project_format_version']}.boris")
            copyfile(projectFileName, old_project_file_name)
            msg += f"\n\nThe old file project was saved as {old_project_file_name}"
        except Exception:
            QMessageBox.critical(cfg.programName, f"Error saving old project to {old_project_file_name}")

        pj[cfg.PROJECT_VERSION] = cfg.project_format_version

    return projectFileName, projectChanged, pj, msg


def event_type(code: str, ethogram: dict) -> str:
    """
    returns type of event for code

    Args:
        ethogram (dict); ethogram of project
        code (str): behavior code

    Returns:
        str: "STATE EVENT", "POINT EVENT" or None if code not found in ethogram
    """

    for idx in ethogram:
        if ethogram[idx][cfg.BEHAVIOR_CODE] == code:
            return ethogram[idx][cfg.TYPE].upper()
    return None


def fix_unpaired_state_events(ethogram: dict, observation: dict, fix_at_time: dec) -> list:
    """
    fix unpaired state events in observation

    Args:
        ethogram (dict): ethogram dictionary
        observation (dict): observation dictionary
        fix_at_time (Decimal): time to fix the unpaired events

    Returns:
        list: list of events with state events fixed
    """

    closing_events_to_add: list = []
    subjects: list = [event[cfg.EVENT_SUBJECT_FIELD_IDX] for event in observation[cfg.EVENTS]]
    ethogram_behaviors: dict = {ethogram[idx][cfg.BEHAVIOR_CODE] for idx in ethogram}

    for subject in sorted(set(subjects)):
        behaviors: list = [
            event[cfg.EVENT_BEHAVIOR_FIELD_IDX] for event in observation[cfg.EVENTS] if event[cfg.EVENT_SUBJECT_FIELD_IDX] == subject
        ]

        for behavior in sorted(set(behaviors)):
            if (behavior in ethogram_behaviors) and (cfg.STATE in event_type(behavior, ethogram).upper()):
                lst, memTime = [], {}
                for event in [
                    event
                    for event in observation[cfg.EVENTS]
                    if event[cfg.EVENT_BEHAVIOR_FIELD_IDX] == behavior and event[cfg.EVENT_SUBJECT_FIELD_IDX] == subject
                ]:
                    behav_modif = [
                        event[cfg.EVENT_BEHAVIOR_FIELD_IDX],
                        event[cfg.EVENT_MODIFIER_FIELD_IDX],
                    ]

                    if behav_modif in lst:
                        lst.remove(behav_modif)
                        del memTime[str(behav_modif)]
                    else:
                        lst.append(behav_modif)
                        memTime[str(behav_modif)] = event[cfg.EVENT_TIME_FIELD_IDX]

                for event in lst:
                    last_event_time = max([fix_at_time] + [x[0] for x in closing_events_to_add])

                    closing_events_to_add.append(
                        [
                            last_event_time + dec("0.001"),
                            subject,
                            behavior,
                            event[1],  # modifiers
                            "Event automatically added by the fix unpaired state events function",
                            cfg.NA,  # frame index
                        ]
                    )

    return closing_events_to_add


def fix_unpaired_state_events2(ethogram: dict, events: list, fix_at_time: dec) -> list:
    """
    fix unpaired state events in events list

    Args:
        ethogram (dict): ethogram dictionary
        events (list): list of events
        fix_at_time (Decimal): time to fix the unpaired events

    Returns:
        list: list of events with state events fixed
    """

    closing_events_to_add: list = []
    subjects: list = [event[cfg.EVENT_SUBJECT_FIELD_IDX] for event in events]
    ethogram_behaviors: dict = {ethogram[idx][cfg.BEHAVIOR_CODE] for idx in ethogram}

    for subject in sorted(set(subjects)):
        behaviors: list = [event[cfg.EVENT_BEHAVIOR_FIELD_IDX] for event in events if event[cfg.EVENT_SUBJECT_FIELD_IDX] == subject]

        for behavior in sorted(set(behaviors)):
            if (behavior in ethogram_behaviors) and (cfg.STATE in event_type(behavior, ethogram).upper()):
                lst, memTime = [], {}
                for event in [
                    event
                    for event in events
                    if event[cfg.EVENT_BEHAVIOR_FIELD_IDX] == behavior and event[cfg.EVENT_SUBJECT_FIELD_IDX] == subject
                ]:
                    behav_modif = [
                        event[cfg.EVENT_BEHAVIOR_FIELD_IDX],
                        event[cfg.EVENT_MODIFIER_FIELD_IDX],
                    ]

                    if behav_modif in lst:
                        lst.remove(behav_modif)
                        del memTime[str(behav_modif)]
                    else:
                        lst.append(behav_modif)
                        memTime[str(behav_modif)] = event[cfg.EVENT_TIME_FIELD_IDX]

                for event in lst:
                    last_event_time = max([fix_at_time] + [x[0] for x in closing_events_to_add])

                    closing_events_to_add.append(
                        [
                            # last_event_time + dec("0.001"),
                            last_event_time,
                            subject,
                            behavior,
                            event[1],  # modifiers
                            "Event automatically added by the fix unpaired state events function",
                            cfg.NA,  # frame index
                        ]
                    )

    return closing_events_to_add


def has_audio(observation: dict, media_file_path: str) -> bool:
    """
    check if media file has audio
    """
    if cfg.HAS_AUDIO in observation[cfg.MEDIA_INFO]:
        if media_file_path in observation[cfg.MEDIA_INFO][cfg.HAS_AUDIO]:
            if observation[cfg.MEDIA_INFO][cfg.HAS_AUDIO][media_file_path]:
                return True
    return False


def explore_project(self) -> None:
    """
    search various elements (subjects, behaviors, modifiers, comments) in all observations
    """

    def double_click_explore_project(obs_id, event_idx):
        """
        manage double-click on tablewidget of explore project results
        """
        observation_operations.load_observation(self, obs_id, cfg.VIEW)

        self.tv_events.selectRow(event_idx - 1)
        index = self.tv_events.model().index(event_idx - 1, 0)
        self.tv_events.scrollTo(index, QAbstractItemView.EnsureVisible)
        # self.twEvents.scrollToItem(self.twEvents.item(event_idx - 1, 0))

    elements_list = ("Subject", "Behavior", "Modifier", "Comment")
    elements = []
    for element in elements_list:
        elements.append(("le", element))
    elements.append(("cb", "Case sensitive", False))

    explore_dlg = dialog.Input_dialog(
        label_caption="Search in all observations",
        elements_list=elements,
        title="Explore project",
    )
    explore_dlg.pbOK.setText("Find")
    if not explore_dlg.exec_():
        return

    nb_fields: int = 0
    results: list = []
    for element in elements_list:
        nb_fields += explore_dlg.elements[element].text() != ""

    for obs_id in sorted(self.pj[cfg.OBSERVATIONS]):
        for event_idx, event in enumerate(self.pj[cfg.OBSERVATIONS][obs_id][cfg.EVENTS]):
            nb_results = 0
            for text, idx in (
                (explore_dlg.elements["Subject"].text(), cfg.EVENT_SUBJECT_FIELD_IDX),
                (explore_dlg.elements["Behavior"].text(), cfg.EVENT_BEHAVIOR_FIELD_IDX),
                (explore_dlg.elements["Modifier"].text(), cfg.EVENT_MODIFIER_FIELD_IDX),
                (explore_dlg.elements["Comment"].text(), cfg.EVENT_COMMENT_FIELD_IDX),
            ):
                if text:
                    if any(
                        (
                            (explore_dlg.elements["Case sensitive"].isChecked() and text in event[idx]),
                            (not explore_dlg.elements["Case sensitive"].isChecked() and text.upper() in event[idx].upper()),
                        )
                    ):
                        nb_results += 1

            if nb_results == nb_fields:
                results.append((obs_id, event_idx + 1))

    if results:
        self.results_dialog = dialog.View_explore_project_results()
        self.results_dialog.setWindowTitle("Explore project results")
        self.results_dialog.setWindowFlags(Qt.WindowStaysOnTopHint)
        self.results_dialog.double_click_signal.connect(double_click_explore_project)
        txt = f"<b>{len(results)}</b> events"
        txt2 = ""
        for element in elements_list:
            if explore_dlg.elements[element].text():
                txt2 += f"<b>{explore_dlg.elements[element].text()}</b> in {element}<br>"
        if txt2:
            txt += " for<br>"
        self.results_dialog.lb.setText(txt + txt2)
        self.results_dialog.tw.setColumnCount(2)
        self.results_dialog.tw.setRowCount(len(results))
        self.results_dialog.tw.setHorizontalHeaderLabels(["Observation id", "row index"])

        for row, result in enumerate(results):
            for i in range(0, 2):
                self.results_dialog.tw.setItem(row, i, QTableWidgetItem(str(result[i])))
                self.results_dialog.tw.item(row, i).setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)

        self.results_dialog.show()

    else:
        QMessageBox.information(self, cfg.programName, "No events found")
