"""
BORIS
Behavioral Observation Research Interactive Software
Copyright 2012-2022 Olivier Friard

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
import pathlib
import sys
from decimal import Decimal as dec
from shutil import copyfile

import tablib

from . import config as cfg
from . import db_functions
from . import portion as I
from . import utilities as util


def check_observation_exhaustivity(events: list, ethogram: list, state_events_list: list = []):
    """
    check if observation is continous
    if ethogram not empty state events list is determined else
    """

    def interval_len(interval):
        if interval.empty:
            return dec(0)
        else:
            return sum([x.upper - x.lower for x in interval])

    def interval_number(interval):
        if interval.empty:
            return dec(0)
        else:
            return len(interval)

    if ethogram:
        state_events_list = [
            ethogram[x][cfg.BEHAVIOR_CODE] for x in ethogram if cfg.STATE in ethogram[x][cfg.TYPE].upper()
        ]

    events_interval = {}
    mem_events_interval = {}

    for event in events:
        if event[cfg.EVENT_SUBJECT_FIELD_IDX] not in events_interval:
            events_interval[event[cfg.EVENT_SUBJECT_FIELD_IDX]] = {}
            mem_events_interval[event[cfg.EVENT_SUBJECT_FIELD_IDX]] = {}

        if event[cfg.EVENT_BEHAVIOR_FIELD_IDX] not in events_interval[event[cfg.EVENT_SUBJECT_FIELD_IDX]]:
            events_interval[event[cfg.EVENT_SUBJECT_FIELD_IDX]][event[cfg.EVENT_BEHAVIOR_FIELD_IDX]] = I.empty()
            mem_events_interval[event[cfg.EVENT_SUBJECT_FIELD_IDX]][event[cfg.EVENT_BEHAVIOR_FIELD_IDX]] = []

        if event[cfg.EVENT_BEHAVIOR_FIELD_IDX] in state_events_list:
            mem_events_interval[event[cfg.EVENT_SUBJECT_FIELD_IDX]][event[cfg.EVENT_BEHAVIOR_FIELD_IDX]].append(
                event[cfg.EVENT_TIME_FIELD_IDX])
            if len(mem_events_interval[event[cfg.EVENT_SUBJECT_FIELD_IDX]][event[cfg.EVENT_BEHAVIOR_FIELD_IDX]]) == 2:
                events_interval[event[cfg.EVENT_SUBJECT_FIELD_IDX]][event[cfg.EVENT_BEHAVIOR_FIELD_IDX]] |= \
                        I.closedopen(mem_events_interval[event[cfg.EVENT_SUBJECT_FIELD_IDX]][event[cfg.EVENT_BEHAVIOR_FIELD_IDX]][0],
                                    mem_events_interval[event[cfg.EVENT_SUBJECT_FIELD_IDX]][event[cfg.EVENT_BEHAVIOR_FIELD_IDX]][1])
                mem_events_interval[event[cfg.EVENT_SUBJECT_FIELD_IDX]][event[cfg.EVENT_BEHAVIOR_FIELD_IDX]] = []
        else:
            events_interval[event[cfg.EVENT_SUBJECT_FIELD_IDX]][event[cfg.EVENT_BEHAVIOR_FIELD_IDX]] |= I.singleton(
                event[cfg.EVENT_TIME_FIELD_IDX])

    if events:
        obs_theo_dur = max(events)[cfg.EVENT_TIME_FIELD_IDX] - min(events)[cfg.EVENT_TIME_FIELD_IDX]
    else:
        obs_theo_dur = dec("0")

    count = 0
    total_duration = 0
    for subject in events_interval:
        '''
        print("\n\nsubject", subject)
        '''

        tot_behav_for_subject = I.empty()
        for behav in events_interval[subject]:
            tot_behav_for_subject |= events_interval[subject][behav]
        '''
        print(f"tot\n{tot_behav_for_subject}")
        '''

        obs_real_dur = interval_len(tot_behav_for_subject)

        if obs_real_dur >= obs_theo_dur:
            obs_real_dur = obs_theo_dur

        total_duration += obs_real_dur
        '''
        print(f"theo dur: {obs_theo_dur}  real: {obs_real_dur}  exhaustiv %: {obs_real_dur/obs_theo_dur}")
        '''
    '''
    print(f"  {total_duration/(len(events_interval) * obs_theo_dur) } ")
    '''
    if len(events_interval) and obs_theo_dur:
        exhausivity_percent = total_duration / (len(events_interval) * obs_theo_dur) * 100
    else:
        exhausivity_percent = 0

    return round(exhausivity_percent, 1)


def behavior_category(ethogram: dict) -> dict:
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


def check_coded_behaviors(pj: dict) -> set:
    """
    check if behaviors coded in events are defined in ethogram

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


def check_if_media_available(observation: dict, project_file_name: str) -> bool:
    """
    check if media files available

    Args:
        observation (dict): observation to be checked

    Returns:
        bool: True if media files found or for live observation
               else False
        str: error message
    """
    if observation[cfg.TYPE] in [cfg.LIVE]:
        return True, ""

    for nplayer in cfg.ALL_PLAYERS:
        if nplayer in observation[cfg.FILE]:
            if not isinstance(observation[cfg.FILE][nplayer], list):
                return False, "error"
            for media_file in observation[cfg.FILE][nplayer]:
                if not media_full_path(media_file, project_file_name):
                    return False, f"Media file <b>{media_file}</b> not found"
    return True, ""


def check_state_events_obs(obsId: str, ethogram: dict, observation: dict, time_format: str = cfg.HHMMSS) -> tuple:
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

    flagStateEvent = False
    subjects = [event[cfg.EVENT_SUBJECT_FIELD_IDX] for event in observation[cfg.EVENTS]]
    ethogram_behaviors = {ethogram[idx][cfg.BEHAVIOR_CODE] for idx in ethogram}

    for subject in sorted(set(subjects)):

        behaviors = [
            event[cfg.EVENT_BEHAVIOR_FIELD_IDX]
            for event in observation[cfg.EVENTS]
            if event[cfg.EVENT_SUBJECT_FIELD_IDX] == subject
        ]

        for behavior in sorted(set(behaviors)):
            if behavior not in ethogram_behaviors:
                # return (False, "The behaviour <b>{}</b> is not defined in the ethogram.<br>".format(behavior))
                continue
            else:
                if cfg.STATE in event_type(behavior, ethogram).upper():
                    flagStateEvent = True
                    lst, memTime = [], {}
                    for event in [
                            event for event in observation[cfg.EVENTS]
                            if event[cfg.EVENT_BEHAVIOR_FIELD_IDX] == behavior and
                            event[cfg.EVENT_SUBJECT_FIELD_IDX] == subject
                    ]:

                        behav_modif = [event[cfg.EVENT_BEHAVIOR_FIELD_IDX], event[cfg.EVENT_MODIFIER_FIELD_IDX]]

                        if behav_modif in lst:
                            lst.remove(behav_modif)
                            del memTime[str(behav_modif)]
                        else:
                            lst.append(behav_modif)
                            memTime[str(behav_modif)] = event[cfg.EVENT_TIME_FIELD_IDX]

                    for event in lst:
                        out += ('The behavior <b>{behavior}</b> {modifier} is not PAIRED for subject'
                                ' "<b>{subject}</b>" at <b>{time}</b><br>').format(
                                    behavior=behavior,
                                    modifier=("(modifier " + event[1] + ") ") if event[1] else "",
                                    subject=subject if subject else cfg.NO_FOCAL_SUBJECT,
                                    time=memTime[str(event)]
                                    if time_format == cfg.S else util.seconds2time(memTime[str(event)]),
                                )

    return (False, out) if out else (True, "No problem detected")


def check_project_integrity(pj: dict,
                            time_format: str,
                            project_file_name: str,
                            media_file_available: bool = True) -> str:
    """
    check project integrity
    check if behaviors in observations are in ethogram
    check unpaired state events
    check if behavior belong to behavioral category that do not more exist
    check for leading and trailing spaces and special chars in modifiers
    check if media file are available
    check if media length available

    Args:
        pj (dict): BORIS project
        time_format (str): time format
        project_file_name (str): project file name
        media_file_access(bool): check if media file are available

    Returns:
        str: message
    """
    out = ""

    try:
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
                        out += (f"The behavior <b>{pj[cfg.ETHOGRAM][idx][cfg.BEHAVIOR_CODE]}</b> belongs "
                                f"to the behavioral category <b>{pj[cfg.ETHOGRAM][idx][cfg.BEHAVIOR_CATEGORY]}</b> "
                                "that is no more in behavioral categories list.")

        # check for leading/trailing spaces/special chars in modifiers defined in ethogram
        for idx in pj[cfg.ETHOGRAM]:
            for k in pj[cfg.ETHOGRAM][idx][cfg.MODIFIERS]:
                for value in pj[cfg.ETHOGRAM][idx][cfg.MODIFIERS][k]["values"]:
                    modifier_code = value.split(" (")[0]
                    if modifier_code.strip() != modifier_code:
                        out += "<br><br>" if out else ""
                        out += ("The following <b>modifier</b> defined in ethogram "
                                "has leading/trailing spaces or special chars: "
                                f"<b>{modifier_code.replace(' ', '&#9608;')}</b>")

        # check if all media are available
        if media_file_available:
            for obs_id in pj[cfg.OBSERVATIONS]:
                ok, msg = check_if_media_available(pj[cfg.OBSERVATIONS][obs_id], project_file_name)
                if not ok:
                    out += "<br><br>" if out else ""
                    out += f"Observation: <b>{obs_id}</b><br>{msg}"

        # check if media length available
        for obs_id in pj[cfg.OBSERVATIONS]:
            if pj[cfg.OBSERVATIONS][obs_id][cfg.TYPE] in [cfg.LIVE]:
                continue
            for nplayer in cfg.ALL_PLAYERS:
                if nplayer in pj[cfg.OBSERVATIONS][obs_id][cfg.FILE]:
                    for media_file in pj[cfg.OBSERVATIONS][obs_id][cfg.FILE][nplayer]:
                        try:
                            pj[cfg.OBSERVATIONS][obs_id][cfg.MEDIA_INFO][cfg.LENGTH][media_file]
                        except KeyError:
                            out += "<br><br>" if out else ""
                            out += f"Observation: <b>{obs_id}</b><br>Length not available for media file <b>{media_file}</b>"

        # check for leading/trailing spaces/special chars in observation id
        for obs_id in pj[cfg.OBSERVATIONS]:
            if obs_id != obs_id.strip():
                out += "<br><br>" if out else ""
                out += ("The following <b>observation id</b> "
                        "has leading/trailing spaces or special chars: "
                        f"<b>{obs_id}</b>")

        return out
    except Exception:
        return str(sys.exc_info()[1])


def create_subtitles(pj: dict, selected_observations: list, parameters: dict, export_dir: str) -> tuple:
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

    def subject_color(subject):
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
                """<font color="{}">""".format(
                    cfg.subtitlesColors[parameters["selected subjects"].index(row["subject"]) %
                                        len(cfg.subtitlesColors)]),
                "</font>",
            )

    try:
        ok, msg, db_connector = db_functions.load_aggregated_events_in_db(pj, parameters["selected subjects"],
                                                                          selected_observations,
                                                                          parameters["selected behaviors"])
        if not ok:
            return False, msg

        cursor = db_connector.cursor()
        flag_ok = True
        msg = ""
        for obsId in selected_observations:
            if pj[cfg.OBSERVATIONS][obsId][cfg.TYPE] in [cfg.LIVE]:
                out = ""
                cursor.execute(
                    ("SELECT subject, behavior, start, stop, type, modifiers FROM aggregated_events "
                     "WHERE observation = ? AND subject in ({}) "
                     "AND behavior in ({}) "
                     "ORDER BY start").format(",".join(["?"] * len(parameters["selected subjects"])),
                                              ",".join(["?"] * len(parameters["selected behaviors"]))),
                    [obsId] + parameters["selected subjects"] + parameters["selected behaviors"],
                )

                for idx, row in enumerate(cursor.fetchall()):
                    col1, col2 = subject_color(row["subject"])
                    if parameters["include modifiers"]:
                        modifiers_str = "\n{}".format(row["modifiers"].replace("|", ", "))
                    else:
                        modifiers_str = ""
                    out += ("{idx}\n"
                            "{start} --> {stop}\n"
                            "{col1}{subject}: {behavior}"
                            "{modifiers}"
                            "{col2}\n\n").format(
                                idx=idx + 1,
                                start=util.seconds2time(row["start"]).replace(".", ","),
                                stop=util.seconds2time(row["stop"] if row["type"] == cfg.STATE else row["stop"] +
                                                       cfg.POINT_EVENT_ST_DURATION).replace(".", ","),
                                col1=col1,
                                col2=col2,
                                subject=row["subject"],
                                behavior=row["behavior"],
                                modifiers=modifiers_str,
                            )
                '''
                file_name = str(pathlib.Path(pathlib.Path(export_dir) / util.safeFileName(obsId)).with suffix(".srt"))
                '''
                file_name = f"{pathlib.Path(export_dir) / util.safeFileName(obsId)}.srt"
                try:
                    with open(file_name, "w") as f:
                        f.write(out)
                except Exception:
                    flag_ok = False
                    msg += "observation: {}\ngave the following error:\n{}\n".format(obsId, str(sys.exc_info()[1]))

            elif pj[cfg.OBSERVATIONS][obsId][cfg.TYPE] in [cfg.MEDIA]:

                for nplayer in cfg.ALL_PLAYERS:
                    if not pj[cfg.OBSERVATIONS][obsId][cfg.FILE][nplayer]:
                        continue
                    init = 0
                    for mediaFile in pj[cfg.OBSERVATIONS][obsId][cfg.FILE][nplayer]:
                        try:
                            end = init + pj[cfg.OBSERVATIONS][obsId][cfg.MEDIA_INFO][cfg.LENGTH][mediaFile]
                        except KeyError:
                            return False, f"The length for media file {mediaFile} is not available"
                        out = ""

                        cursor.execute(
                            ("SELECT subject, behavior, type, start, stop, modifiers FROM aggregated_events "
                             "WHERE observation = ? AND start BETWEEN ? and ? "
                             "AND subject in ({}) "
                             "AND behavior in ({}) "
                             "ORDER BY start").format(
                                 ",".join(["?"] * len(parameters["selected subjects"])),
                                 ",".join(["?"] * len(parameters["selected behaviors"])),
                             ),
                            [obsId, init, end] + parameters["selected subjects"] + parameters["selected behaviors"],
                        )

                        for idx, row in enumerate(cursor.fetchall()):
                            col1, col2 = subject_color(row["subject"])
                            if parameters["include modifiers"]:
                                modifiers_str = "\n{}".format(row["modifiers"].replace("|", ", "))
                            else:
                                modifiers_str = ""

                            out += (
                                "{idx}\n"
                                "{start} --> {stop}\n"
                                "{col1}{subject}: {behavior}"
                                "{modifiers}"
                                "{col2}\n\n").format(
                                    idx=idx + 1,
                                    start=util.seconds2time(row["start"] - init).replace(".", ","),
                                    stop=util.seconds2time((row["stop"] if row["type"] == cfg.STATE else row["stop"] +
                                                            cfg.POINT_EVENT_ST_DURATION) - init).replace(".", ","),
                                    col1=col1,
                                    col2=col2,
                                    subject=row["subject"],
                                    behavior=row["behavior"],
                                    modifiers=modifiers_str,
                                )
                        '''
                        file_name = str(pathlib.Path(pathlib.Path(export_dir) / pathlib.Path(mediaFile).name).with suffix(".srt"))
                        '''
                        file_name = f"{pathlib.Path(export_dir) / pathlib.Path(mediaFile).name}.srt"
                        try:
                            with open(file_name, "w") as f:
                                f.write(out)
                        except Exception:
                            flag_ok = False
                            msg += f"observation: {obsId}\ngave the following error:\n{sys.exc_info()[1]}\n"

                        init = end

        return flag_ok, msg
    except Exception:
        return False, str(sys.exc_info()[1])


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
    data.headers = ["Observation id", "Date", "Description", "Subjects", "Media files/Live observation"]

    indep_var_header = []
    if cfg.INDEPENDENT_VARIABLES in pj:
        for idx in util.sorted_keys(pj[cfg.INDEPENDENT_VARIABLES]):
            indep_var_header.append(pj[cfg.INDEPENDENT_VARIABLES][idx]["label"])
    data.headers.extend(indep_var_header)

    for obs_id in selected_observations:

        subjects_list = sorted(
            list(set([x[cfg.EVENT_SUBJECT_FIELD_IDX] for x in pj[cfg.OBSERVATIONS][obs_id][cfg.EVENTS]])))
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

        data.append([
            obs_id, pj[cfg.OBSERVATIONS][obs_id]["date"], pj[cfg.OBSERVATIONS][obs_id]["description"], subjects,
            ", ".join(media_files)
        ] + indep_var)

    if output_format in ["tsv", "csv", "html"]:
        try:
            with open(file_name, "wb") as f:
                f.write(str.encode(data.export(output_format)))
        except Exception:
            return False
    if output_format in ["ods", "xlsx", "xls"]:
        try:
            with open(file_name, "wb") as f:
                f.write(data.export(output_format))
        except Exception:
            return False

    return True


def remove_media_files_path(pj):
    """
    remove path from media files
    tested

    Args:
        pj (dict): project file

    Returns:
        dict: project without media file paths
    """

    for obs_id in pj[cfg.OBSERVATIONS]:
        if pj[cfg.OBSERVATIONS][obs_id][cfg.TYPE] not in [cfg.MEDIA]:
            continue
        for n_player in cfg.ALL_PLAYERS:
            if n_player in pj[cfg.OBSERVATIONS][obs_id][cfg.FILE]:
                for idx, media_file in enumerate(pj[cfg.OBSERVATIONS][obs_id][cfg.FILE][n_player]):
                    p = str(pathlib.Path(media_file).name)
                    if p != media_file:
                        pj[cfg.OBSERVATIONS][obs_id][cfg.FILE][n_player][idx] = p
                        if cfg.MEDIA_INFO in pj[cfg.OBSERVATIONS][obs_id]:
                            for info in [cfg.LENGTH, "hasAudio", "hasVideo", "fps"]:
                                if (info in pj[cfg.OBSERVATIONS][obs_id][cfg.MEDIA_INFO] and
                                        media_file in pj[cfg.OBSERVATIONS][obs_id][cfg.MEDIA_INFO][info]):
                                    pj[cfg.OBSERVATIONS][obs_id][cfg.MEDIA_INFO][info][p] = pj[
                                        cfg.OBSERVATIONS][obs_id][cfg.MEDIA_INFO][info][media_file]
                                    del pj[cfg.OBSERVATIONS][obs_id][cfg.MEDIA_INFO][info][media_file]

    return dict(pj)


def media_full_path(media_file: str, project_file_name: str) -> str:
    """
    media full path
    add path of BORIS project if media without path

    Args:
        media_file (str): media file path
        project_file_name (str): project file name

    Returns:
        str: media full path
    """

    media_path = pathlib.Path(media_file)
    if media_path.exists():
        return str(media_path)
    else:
        project_path = pathlib.Path(project_file_name)
        p = project_path.parent / media_path.name
        if p.exists():
            return str(p)
        else:
            return ""


def observed_interval(observation: dict):
    """
    Observed interval for observation

    Args:
        observation (dict): observation dictionary

    Returns:
        List of 2 Decimals: time of first observed event, time of last observed event
    """
    if observation[cfg.EVENTS]:
        return (min(observation[cfg.EVENTS])[cfg.EVENT_TIME_FIELD_IDX],
                max(observation[cfg.EVENTS])[cfg.EVENT_TIME_FIELD_IDX])
    else:
        return (dec("0.0"), dec("0.0"))


def observation_total_length(observation: dict):
    """
    Total length of media file(s) for observation
    tested

    media: if media length not available return 0
           if more media are queued, return sum of media length
           if the last event is recorded after the length of media returns the last event time

    live: return last event time

    Args:
        observation (dict): observation dictionary

    Returns:
        Decimal: total length in seconds

    """

    if observation[cfg.TYPE] == cfg.LIVE:
        if observation[cfg.EVENTS]:
            obs_length = max(observation[cfg.EVENTS])[cfg.EVENT_TIME_FIELD_IDX]
        else:
            obs_length = dec("0.0")
        return obs_length

    if observation[cfg.TYPE] == cfg.MEDIA:
        media_max_total_length = dec("0.0")

        media_total_length = {}

        for nplayer in observation[cfg.FILE]:
            if not observation[cfg.FILE][nplayer]:
                continue

            media_total_length[nplayer] = dec("0.0")
            for mediaFile in observation[cfg.FILE][nplayer]:
                mediaLength = 0
                try:
                    mediaLength = observation[cfg.MEDIA_INFO][cfg.LENGTH][mediaFile]
                    media_total_length[nplayer] += dec(mediaLength)
                except Exception:
                    logging.critical(f"media length not found for {mediaFile}")
                    mediaLength = -1
                    media_total_length[nplayer] = -1
                    break

        if -1 in [media_total_length[x] for x in media_total_length]:
            return dec("-1")

        # totalMediaLength = max([total_media_length[x] for x in total_media_length])

        media_max_total_length = max([media_total_length[x] for x in media_total_length])

        if observation[cfg.EVENTS]:
            if max(observation[cfg.EVENTS])[cfg.EVENT_TIME_FIELD_IDX] > media_max_total_length:
                media_max_total_length = max(observation[cfg.EVENTS])[cfg.EVENT_TIME_FIELD_IDX]

        return media_max_total_length

    logging.critical("observation not LIVE nor MEDIA")

    return dec("0.0")


def events_start_stop(ethogram, events):
    """
    returns events with status (START/STOP or POINT)
    take consideration of subject

    Args:
        events (list): list of events

    Returns:
        list: list of events with type (POINT or STATE)
    """

    state_events_list = util.state_behavior_codes(ethogram)

    events_flagged = []
    for event in events:
        time, subject, code, modifier = (
            event[cfg.EVENT_TIME_FIELD_IDX],
            event[cfg.EVENT_SUBJECT_FIELD_IDX],
            event[cfg.EVENT_BEHAVIOR_FIELD_IDX],
            event[cfg.EVENT_MODIFIER_FIELD_IDX],
        )
        # check if code is state
        if code in state_events_list:
            # how many code before with same subject?
            if (len([
                    x[cfg.EVENT_BEHAVIOR_FIELD_IDX]
                    for x in events
                    if x[cfg.EVENT_BEHAVIOR_FIELD_IDX] == code and x[cfg.EVENT_TIME_FIELD_IDX] < time and
                    x[cfg.EVENT_SUBJECT_FIELD_IDX] == subject and x[cfg.EVENT_MODIFIER_FIELD_IDX] == modifier
            ]) % 2):  # test if odd
                flag = cfg.STOP
            else:
                flag = cfg.START
        else:
            flag = cfg.POINT

        events_flagged.append(event + [flag])

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
        return projectFileName, projectChanged, {"error": f"File {projectFileName} not found"}, msg

    try:
        if projectFileName.endswith(".boris.gz"):
            file_in = gzip.open(projectFileName, mode="rt", encoding="utf-8")
        else:
            file_in = open(projectFileName, "r")
        file_content = file_in.read()
    except PermissionError:
        return projectFileName, projectChanged, {f"error": f"File {projectFileName}: Permission denied"}, msg
    except Exception:
        return projectFileName, projectChanged, {f"error": f"Error on file {projectFileName}: {sys.exc_info()[1]}"}, msg

    try:
        pj = json.loads(file_content)
    except json.decoder.JSONDecodeError:
        return projectFileName, projectChanged, {"error": "This project file seems corrupted"}, msg
    except Exception:
        return projectFileName, projectChanged, {f"error": f"Error on file {projectFileName}: {sys.exc_info()[1]}"}, msg

    # transform time to decimal
    pj = util.convert_time_to_decimal(pj)

    # add coding_map key to old project files
    if "coding_map" not in pj:
        pj["coding_map"] = {}
        projectChanged = True

    # add subject description
    if "project_format_version" in pj:
        for idx in [x for x in pj[cfg.SUBJECTS]]:
            if "description" not in pj[cfg.SUBJECTS][idx]:
                pj[cfg.SUBJECTS][idx]["description"] = ""
                projectChanged = True

    # check if project file version is newer than current BORIS project file version
    if "project_format_version" in pj and dec(pj["project_format_version"]) > dec(cfg.project_format_version):
        return (
            projectFileName,
            projectChanged,
            {
                "error": ("This project file was created with a more recent version of BORIS.<br>"
                          f"You must update BORIS to <b>v. >= {pj['project_format_version']}</b> to open this project")
            },
            msg,
        )

    # check if old version  v. 0 *.obs
    if "project_format_version" not in pj:

        # convert VIDEO, AUDIO -> MEDIA
        pj["project_format_version"] = cfg.project_format_version
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
            "Choose a new file name for saving it.")
        projectFileName = ""

    # update modifiers to JSON format

    # check if project format version < 4 (modifiers were str)
    project_lowerthan4 = False
    if "project_format_version" in pj and util.versiontuple(pj["project_format_version"]) < util.versiontuple("4.0"):
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
                            "values": modif_set.split(",")
                        }
                    pj[cfg.ETHOGRAM][idx]["modifiers"] = dict(modif_set_dict)
            else:
                pj[cfg.ETHOGRAM][idx]["modifiers"] = {}

        if not project_lowerthan4:
            msg = "The project version was updated from {} to {}".format(pj["project_format_version"],
                                                                         cfg.project_format_version)
            pj["project_format_version"] = cfg.project_format_version
            projectChanged = True

    # add category key if not found
    for idx in pj[cfg.ETHOGRAM]:
        if "category" not in pj[cfg.ETHOGRAM][idx]:
            pj[cfg.ETHOGRAM][idx]["category"] = ""

    # if one file is present in player #1 -> set "media_info" key with value of media_file_info
    for obs in pj[cfg.OBSERVATIONS]:
        if pj[cfg.OBSERVATIONS][obs][cfg.TYPE] in [cfg.MEDIA] and cfg.MEDIA_INFO not in pj[cfg.OBSERVATIONS][obs]:
            pj[cfg.OBSERVATIONS][obs][cfg.MEDIA_INFO] = {cfg.LENGTH: {}, "fps": {}, "hasVideo": {}, "hasAudio": {}}
            for player in [cfg.PLAYER1, cfg.PLAYER2]:
                # fix bug Anne Maijer 2017-07-17
                if pj[cfg.OBSERVATIONS][obs][cfg.FILE] == []:
                    pj[cfg.OBSERVATIONS][obs][cfg.FILE] = {"1": [], "2": []}

                for media_file_path in pj[cfg.OBSERVATIONS][obs]["file"][player]:
                    # FIX: ffmpeg path
                    ret, msg = util.check_ffmpeg_path()
                    if not ret:
                        return projectFileName, projectChanged, {"error": "FFmpeg path not found"}, ""
                    else:
                        ffmpeg_bin = msg

                    r = util.accurate_media_analysis(ffmpeg_bin, media_file_path)

                    if "duration" in r and r["duration"]:
                        pj[cfg.OBSERVATIONS][obs][cfg.MEDIA_INFO][cfg.LENGTH][media_file_path] = float(r["duration"])
                        pj[cfg.OBSERVATIONS][obs][cfg.MEDIA_INFO][cfg.FPS][media_file_path] = float(r["fps"])
                        pj[cfg.OBSERVATIONS][obs][cfg.MEDIA_INFO]["hasVideo"][media_file_path] = r["has_video"]
                        pj[cfg.OBSERVATIONS][obs][cfg.MEDIA_INFO]["hasAudio"][media_file_path] = r["has_audio"]
                        project_updated, projectChanged = True, True
                    else:  # file path not found
                        if ("media_file_info" in pj[cfg.OBSERVATIONS][obs] and
                                len(pj[cfg.OBSERVATIONS][obs]["media_file_info"]) == 1 and
                                len(pj[cfg.OBSERVATIONS][obs][cfg.FILE][cfg.PLAYER1]) == 1 and
                                len(pj[cfg.OBSERVATIONS][obs][cfg.FILE][cfg.PLAYER2]) == 0):
                            media_md5_key = list(pj[cfg.OBSERVATIONS][obs]["media_file_info"].keys())[0]
                            # duration
                            pj[cfg.OBSERVATIONS][obs][cfg.MEDIA_INFO] = {
                                cfg.LENGTH: {
                                    media_file_path:
                                        pj[cfg.OBSERVATIONS][obs]["media_file_info"][media_md5_key]["video_length"] /
                                        1000
                                }
                            }
                            projectChanged = True

                            # FPS
                            if "nframe" in pj[cfg.OBSERVATIONS][obs]["media_file_info"][media_md5_key]:
                                pj[cfg.OBSERVATIONS][obs][cfg.MEDIA_INFO][cfg.FPS] = {
                                    media_file_path:
                                        pj[cfg.OBSERVATIONS][obs]["media_file_info"][media_md5_key]["nframe"] /
                                        (pj[cfg.OBSERVATIONS][obs]["media_file_info"][media_md5_key]["video_length"] /
                                         1000)
                                }
                            else:
                                pj[cfg.OBSERVATIONS][obs][cfg.MEDIA_INFO][cfg.FPS] = {media_file_path: 0}

    # update project to v.7 for time offset second player
    project_lowerthan7 = False
    for obs in pj[cfg.OBSERVATIONS]:
        if "time offset second player" in pj[cfg.OBSERVATIONS][obs]:
            if cfg.MEDIA_INFO not in pj[cfg.OBSERVATIONS][obs]:
                pj[cfg.OBSERVATIONS][obs][cfg.MEDIA_INFO] = {}
            if "offset" not in pj[cfg.OBSERVATIONS][obs][cfg.MEDIA_INFO]:
                pj[cfg.OBSERVATIONS][obs][cfg.MEDIA_INFO]["offset"] = {}
            for player in pj[cfg.OBSERVATIONS][obs][cfg.FILE]:
                pj[cfg.OBSERVATIONS][obs][cfg.MEDIA_INFO]["offset"][player] = 0.0
            if pj[cfg.OBSERVATIONS][obs]["time offset second player"]:
                pj[cfg.OBSERVATIONS][obs][cfg.MEDIA_INFO]["offset"]["2"] = float(
                    pj[cfg.OBSERVATIONS][obs]["time offset second player"])

            del pj[cfg.OBSERVATIONS][obs]["time offset second player"]
            project_lowerthan7 = True

            msg = (
                f"The project file was converted to the new format (v. {cfg.project_format_version}) in use with your version of BORIS.<br>"
                f"Please note that this new version will NOT be compatible with previous BORIS versions "
                f"(&lt; v. {cfg.project_format_version}).<br>")

            projectChanged = True

    if project_lowerthan7:

        msg = (f"The project was updated to the current project version ({cfg.project_format_version}).")

        try:
            old_project_file_name = projectFileName.replace(".boris", f".v{pj['project_format_version']}.boris")
            copyfile(projectFileName, old_project_file_name)
            msg += f"\n\nThe old file project was saved as {old_project_file_name}"
        except Exception:
            pass

        pj["project_format_version"] = cfg.project_format_version

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


def fix_unpaired_state_events(obsId, ethogram, observation, fix_at_time):
    """
    fix unpaired state events in observation

    Args:
        obsId (str): observation id
        ethogram (dict): ethogram dictionary
        observation (dict): observation dictionary
        fix_at_time (Decimal): time to fix the unpaired events

    Returns:
        list: list of events with state events fixed
    """

    out = ""
    closing_events_to_add = []
    flagStateEvent = False
    subjects = [event[cfg.EVENT_SUBJECT_FIELD_IDX] for event in observation[cfg.EVENTS]]
    ethogram_behaviors = {ethogram[idx][cfg.BEHAVIOR_CODE] for idx in ethogram}

    for subject in sorted(set(subjects)):

        behaviors = [
            event[cfg.EVENT_BEHAVIOR_FIELD_IDX]
            for event in observation[cfg.EVENTS]
            if event[cfg.EVENT_SUBJECT_FIELD_IDX] == subject
        ]

        for behavior in sorted(set(behaviors)):
            if (behavior in ethogram_behaviors) and (cfg.STATE in event_type(behavior, ethogram).upper()):

                flagStateEvent = True
                lst, memTime = [], {}
                for event in [
                        event for event in observation[cfg.EVENTS]
                        if event[cfg.EVENT_BEHAVIOR_FIELD_IDX] == behavior and
                        event[cfg.EVENT_SUBJECT_FIELD_IDX] == subject
                ]:

                    behav_modif = [event[cfg.EVENT_BEHAVIOR_FIELD_IDX], event[cfg.EVENT_MODIFIER_FIELD_IDX]]

                    if behav_modif in lst:
                        lst.remove(behav_modif)
                        del memTime[str(behav_modif)]
                    else:
                        lst.append(behav_modif)
                        memTime[str(behav_modif)] = event[cfg.EVENT_TIME_FIELD_IDX]

                for event in lst:

                    last_event_time = max([fix_at_time] + [x[0] for x in closing_events_to_add])

                    closing_events_to_add.append([last_event_time + dec("0.001"), subject, behavior, event[1],
                                                  ""]  # modifiers  # comment
                                                )

    return closing_events_to_add
