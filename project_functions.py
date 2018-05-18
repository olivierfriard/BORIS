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

import logging
import os
import sys
import json
import pathlib
from shutil import copyfile
from decimal import *
import copy

from config import *
import db_functions
import utilities


def remove_media_files_path(pj):
    """
    remove path from media files
    tested
    
    Args:
        pj (dict): project file
    
    Returns:
        dict: project without media file paths
    """

    for obs_id in pj[OBSERVATIONS]:
        if pj[OBSERVATIONS][obs_id][TYPE] not in [MEDIA]:
            continue
        for n_player in ALL_PLAYERS:
            if n_player in pj[OBSERVATIONS][obs_id][FILE]:
                for idx, media_file in enumerate(pj[OBSERVATIONS][obs_id][FILE][n_player]):
                    p = str(pathlib.Path(media_file).name)
                    if p != media_file:
                        pj[OBSERVATIONS][obs_id][FILE][n_player][idx] = p
                        if "media_info" in pj[OBSERVATIONS][obs_id]:
                            for info in ["length", "hasAudio", "hasVideo", "fps"]:
                                if info in pj[OBSERVATIONS][obs_id]["media_info"] and media_file in pj[OBSERVATIONS][obs_id]["media_info"][info]:
                                    pj[OBSERVATIONS][obs_id]["media_info"][info][p] = pj[OBSERVATIONS][obs_id]["media_info"][info][media_file]
                                    del pj[OBSERVATIONS][obs_id]["media_info"][info][media_file]

    return copy.deepcopy(pj)


def media_full_path(media_file, project_file_name):
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
    if media_path.resolve() == media_path and media_path.exists():
        return str(media_path)
    else:
        project_path = pathlib.Path(project_file_name)
        p = project_path.parent / media_path.name
        if p.exists():
            return str(p)
        else:
            return ""


def check_if_media_available(observation, project_file_name):
    """
    check if media files available
    
    Args:
        observation (dict): observation to be checked
        
    Returns:
         bool: True if media files found or for live observation
               else False
    """
    if observation[TYPE] in [LIVE]:
        return True, ""
        
    for nplayer in ALL_PLAYERS:
        if nplayer in observation[FILE]:
            if not isinstance(observation[FILE][nplayer], list):
                return False, "error"
            for media_file in observation[FILE][nplayer]:
                if not media_full_path(media_file, project_file_name):
                    return False, "Media file <b>{}</b> not found".format(media_file)
    return True, ""


def create_subtitles(pj, selected_observations, parameters, export_dir):
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
        if subject == NO_FOCAL_SUBJECT:
            return "", ""
        else:
            return """<font color="{}">""".format(subtitlesColors[parameters["selected subjects"].index(row["subject"]) % len(subtitlesColors)]), "</font>"

    try:
        ok, msg, db_connector = db_functions.load_aggregated_events_in_db(pj,
                                                           parameters["selected subjects"],
                                                           selected_observations,
                                                           parameters["selected behaviors"])
        if not ok:
            return False, msg

        cursor = db_connector.cursor()
        flag_ok = True
        msg = ""
        for obsId in selected_observations:
            if pj[OBSERVATIONS][obsId][TYPE] in [LIVE]:
                out = ""
                cursor.execute(("SELECT subject, behavior, start, stop, type, modifiers FROM aggregated_events "
                                "WHERE observation = ? AND subject in ({}) "
                                "AND behavior in ({}) "
                                "ORDER BY start").format(",".join(["?"] * len(parameters["selected subjects"])),
                                                         ",".join(["?"] * len(parameters["selected behaviors"]))),
                                [obsId] + parameters["selected subjects"] + parameters["selected behaviors"])
    
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
                         "{col2}\n\n").format(idx=idx + 1,
                                                         start=utilities.seconds2time(row["start"]).replace(".", ","),
                                                         stop=utilities.seconds2time(row["stop"] if row["type"] == STATE else row["stop"] + POINT_EVENT_ST_DURATION).replace(".", ","),
                                                         col1=col1, col2=col2,
                                                         subject=row["subject"],
                                                         behavior=row["behavior"],
                                                         modifiers=modifiers_str)
    
                file_name = str(pathlib.Path(pathlib.Path(export_dir) / utilities.safeFileName(obsId)).with_suffix(".srt"))
                try:
                    with open(file_name, "w") as f:
                        f.write(out)
                except:
                    flag_ok = False
                    msg += "observation: {}\ngave the following error:\n{}\n".format(obsId, str(sys.exc_info()[1]))

            elif pj[OBSERVATIONS][obsId][TYPE] in [MEDIA]:

                for nplayer in ALL_PLAYERS:
                    if not pj[OBSERVATIONS][obsId][FILE][nplayer]:
                        continue
                    init = 0
                    for mediaFile in pj[OBSERVATIONS][obsId][FILE][nplayer]:
                        end = init + pj[OBSERVATIONS][obsId]["media_info"]["length"][mediaFile]
                        out = ""
                        cursor.execute(("SELECT subject, behavior, type, start, stop, modifiers FROM aggregated_events "
                                        "WHERE observation = ? AND start BETWEEN ? and ? "
                                        "AND subject in ({}) "
                                        "AND behavior in ({}) "
                                        "ORDER BY start").format(",".join(["?"] * len(parameters["selected subjects"])),
                                                                 ",".join(["?"] * len(parameters["selected behaviors"]))),
                                        [obsId, init, end] + parameters["selected subjects"] + parameters["selected behaviors"])

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
                                    "{col2}\n\n").format(idx=idx + 1,
                                                                        start=utilities.seconds2time(row["start"] - init).replace(".", ","),
                                                                        stop=utilities.seconds2time((row["stop"] if row["type"] == STATE else row["stop"] + POINT_EVENT_ST_DURATION) - init).replace(".", ","),
                                                                        col1=col1, col2=col2,
                                                                        subject=row["subject"],
                                                                        behavior=row["behavior"],
                                                                        modifiers=modifiers_str)
    
                        file_name = str(pathlib.Path(pathlib.Path(export_dir) / pathlib.PurePosixPath(mediaFile).name).with_suffix(".srt"))
                        try:
                            with open(file_name, "w") as f:
                                f.write(out)
                        except:
                            flag_ok = False
                            msg += "observation: {}\ngave the following error:\n{}\n".format(obsId, str(sys.exc_info()[1]))
    
                        init = end

        return flag_ok, msg
    except:
        return False, str(sys.exc_info()[1])


def observation_total_length(observation):
    """
    Total length of observation
    tested
    
    media: if media length not available return 0
            if more media are queued, return sum of media length
    
    live: return last event time
    
    Args:
        observation (dict): observation dictionary
        
    Returns:
        Decimal: total length in seconds

    """

    if observation[TYPE] == LIVE:
        if observation[EVENTS]:
            totalMediaLength = max(observation[EVENTS])[EVENT_TIME_FIELD_IDX]
        else:
            totalMediaLength = Decimal("0.0")
        return totalMediaLength

    if observation[TYPE] == MEDIA:
        totalMediaLength, totalMediaLength1, totalMediaLength2 = Decimal("0.0"), Decimal("0.0"), Decimal("0.0")

        total_media_length = {}

        for player in [PLAYER1, PLAYER2]:
            total_media_length[player] = Decimal("0.0")
            for mediaFile in observation[FILE][player]:
                mediaLength = 0
                try:
                    mediaLength = observation["media_info"]["length"][mediaFile]
                except:
                    #nframe, videoTime, videoDuration, fps, hasVideo, hasAudio = accurate_media_analysis(self.ffmpeg_bin, mediaFile)
                    r = utilities.accurate_media_analysis2(self.ffmpeg_bin, mediaFile)
                    if "media_info" not in observation:
                        observation["media_info"] = {"length": {}, "fps": {}}
                        if "length" not in observation["media_info"]:
                            observation["media_info"]["length"] = {}
                        if "fps" not in observation["media_info"]:
                            observation["media_info"]["fps"] = {}
    
                    observation["media_info"]["length"][mediaFile] = r["duration"]
                    observation["media_info"]["fps"][mediaFile] = r["fps"]
    
                    mediaLength = r["duration"]
    
                total_media_length[player] += Decimal(mediaLength)
        
        if -1 in [total_media_length[x] for x in total_media_length]:
            return -1

        totalMediaLength = max([total_media_length[x] for x in total_media_length])

        if observation[EVENTS]:
            if max(observation[EVENTS])[EVENT_TIME_FIELD_IDX] > totalMediaLength:
                totalMediaLength = max(observation[EVENTS])[EVENT_TIME_FIELD_IDX]

        return totalMediaLength

    return Decimal("0.0")


def events_start_stop(ethogram, events):
    """
    returns events with status (START/STOP or POINT)
    take consideration of subject
    
    Args:
        events (list): list of events

    Returns:
        list: list of events with type (POINT or STATE)
    """

    state_events_list = utilities.state_behavior_codes(ethogram) # from utilities

    events_flagged = []
    for event in events:
        time, subject, code, modifier = event[EVENT_TIME_FIELD_IDX], event[EVENT_SUBJECT_FIELD_IDX], event[EVENT_BEHAVIOR_FIELD_IDX], event[EVENT_MODIFIER_FIELD_IDX]
        # check if code is state
        if code in state_events_list:
            # how many code before with same subject?
            if len([x[EVENT_BEHAVIOR_FIELD_IDX] for x in events
                                                 if x[EVENT_BEHAVIOR_FIELD_IDX] == code
                                                    and x[EVENT_TIME_FIELD_IDX] < time
                                                    and x[EVENT_SUBJECT_FIELD_IDX] == subject
                                                    and x[EVENT_MODIFIER_FIELD_IDX] == modifier]) % 2: # test if odd
                flag = STOP
            else:
                flag = START
        else:
            flag = POINT

        events_flagged.append(event + [flag])

    return events_flagged


def extract_observed_subjects(pj, selected_observations):
    """
    extract unique subjects present in observations list
    
    return: list
    """

    observed_subjects = []

    # extract events from selected observations
    for events in [pj[OBSERVATIONS][x][EVENTS] for x in pj[OBSERVATIONS] if x in selected_observations]:
        for event in events:
            observed_subjects.append(event[EVENT_SUBJECT_FIELD_IDX])

    # remove duplicate
    return list(set(observed_subjects))


def open_project_json(projectFileName):
    """
    open project json
    
    Args:
        projectFileName (str): path of project
        
    Returns:
        str: project path
        bool: True if project changed
        dict: BORIS project
        str: message
    """

    logging.debug("open project: {0}".format(projectFileName))

    projectChanged = False
    msg = ""

    if not os.path.isfile(projectFileName):
        return projectFileName, projectChanged, {"error": "File {} not found".format(projectFileName)}, msg

    s = open(projectFileName, "r").read()

    try:
        pj = json.loads(s)
    except:
        return projectFileName, projectChanged, {"error": "This project file seems corrupted"}, msg


    # transform time to decimal
    pj = utilities.convert_time_to_decimal(pj)

    # add coding_map key to old project files
    if not "coding_map" in pj:
        pj["coding_map"] = {}
        projectChanged = True

    # add subject description
    if "project_format_version" in pj:
        for idx in [x for x in pj[SUBJECTS]]:
            if not "description" in pj[SUBJECTS][idx]:
                pj[SUBJECTS][idx]["description"] = ""
                projectChanged = True

    # check if project file version is newer than current BORIS project file version
    if "project_format_version" in pj and Decimal(pj["project_format_version"]) > Decimal(project_format_version):
      
        return projectFileName, projectChanged, {"error": ("This project file was created with a more recent version of BORIS.\n"
                                                 "You must update BORIS to open it")}, msg


    # check if old version  v. 0 *.obs
    if "project_format_version" not in pj:

        # convert VIDEO, AUDIO -> MEDIA
        pj['project_format_version'] = project_format_version
        projectChanged = True

        for obs in [x for x in pj[OBSERVATIONS]]:

            # remove 'replace audio' key
            if "replace audio" in pj[OBSERVATIONS][obs]:
                del pj[OBSERVATIONS][obs]['replace audio']

            if pj[OBSERVATIONS][obs][TYPE] in ['VIDEO', 'AUDIO']:
                pj[OBSERVATIONS][obs][TYPE] = MEDIA

            # convert old media list in new one
            if len(pj[OBSERVATIONS][obs][FILE]):
                d1 = {PLAYER1: [pj[OBSERVATIONS][obs][FILE][0]]}

            if len(pj[OBSERVATIONS][obs][FILE]) == 2:
                d1[PLAYER2] = [pj[OBSERVATIONS][obs][FILE][1]]

            pj[OBSERVATIONS][obs][FILE] = d1

        # convert VIDEO, AUDIO -> MEDIA
        for idx in [x for x in pj[SUBJECTS]]:
            key, name = pj[SUBJECTS][idx]
            pj[SUBJECTS][idx] = {"key": key, "name": name, "description": ""}
        
        msg = ("The project file was converted to the new format (v. {}) in use with your version of BORIS.<br>"
                                                    "Choose a new file name for saving it.").format(project_format_version)
        projectFileName = ""


    for obs in pj[OBSERVATIONS]:
        if not "time offset second player" in pj[OBSERVATIONS][obs]:
            pj[OBSERVATIONS][obs]["time offset second player"] = Decimal("0.0")
            projectChanged = True

    # update modifiers to JSON format

    project_lowerthan4 = False

    logging.debug("project_format_version: {}".format(utilities.versiontuple(pj["project_format_version"])))

    if "project_format_version" in pj and utilities.versiontuple(pj["project_format_version"]) < utilities.versiontuple("4.0"):

        for idx in pj[ETHOGRAM]:
            if pj[ETHOGRAM][idx]["modifiers"]:
                if isinstance(pj[ETHOGRAM][idx]["modifiers"], str):
                    project_lowerthan4 = True
                    modif_set_list = pj[ETHOGRAM][idx]["modifiers"].split("|")
                    modif_set_dict = {}
                    for modif_set in modif_set_list:
                        modif_set_dict[str(len(modif_set_dict))] = {"name": "", "type": SINGLE_SELECTION, "values": modif_set.split(",")}
                    pj[ETHOGRAM][idx]["modifiers"] = dict(modif_set_dict)
            else:
                pj[ETHOGRAM][idx]["modifiers"] = {}

        if not project_lowerthan4:
            msg = "The project version was updated from {} to {}".format(pj["project_format_version"], project_format_version)
            pj["project_format_version"] = project_format_version
            projectChanged = True


    # add category key if not found
    for idx in pj[ETHOGRAM]:
        if "category" not in pj[ETHOGRAM][idx]:
            pj[ETHOGRAM][idx]["category"] = ""

    logging.debug("project_lowerthan4: {}".format(project_lowerthan4))

    if project_lowerthan4:

        copyfile(projectFileName, projectFileName.replace(".boris", "_old_version.boris"))
        
        msg = ("The project was updated to the current project version ({project_format_version}).\n\n"
               "The old file project was saved as {project_file_name}").format(project_format_version=project_format_version,
                                                                               project_file_name=projectFileName.replace(".boris", "_old_version.boris"))

    # if one file is present in player #1 -> set "media_info" key with value of media_file_info
    project_updated = False

    for obs in pj[OBSERVATIONS]:
        if pj[OBSERVATIONS][obs][TYPE] in [MEDIA] and "media_info" not in pj[OBSERVATIONS][obs]:
            pj[OBSERVATIONS][obs]['media_info'] = {"length": {}, "fps": {}, "hasVideo": {}, "hasAudio": {}}
            for player in [PLAYER1, PLAYER2]:
                # fix bug Anne Maijer 2017-07-17
                if pj[OBSERVATIONS][obs]["file"] == []:
                    pj[OBSERVATIONS][obs]["file"] = {"1": [], "2": []}

                for media_file_path in pj[OBSERVATIONS][obs]["file"][player]:
                    # FIX: ffmpeg path
                    
                    ret, msg = utilities.check_ffmpeg_path()
                    if not ret:
                        return projectFileName, projectChanged, {"error": "FFmpeg path not found"}, ""
                    else:
                        ffmpeg_bin = msg

                    #nframe, videoTime, videoDuration, fps, hasVideo, hasAudio = utilities.accurate_media_analysis(ffmpeg_bin, media_file_path)
                    r = utilities.accurate_media_analysis2(ffmpeg_bin, media_file_path)
                    if "error" in r:
                        return projectFileName, projectChanged, {"error": r["error"]}, ""

                    if r["duration"]:
                        pj[OBSERVATIONS][obs]["media_info"]["length"][media_file_path] = r["duration"]
                        pj[OBSERVATIONS][obs]["media_info"]["fps"][media_file_path] = r["fps"]
                        pj[OBSERVATIONS][obs]["media_info"]["hasVideo"][media_file_path] = r["has_video"]
                        pj[OBSERVATIONS][obs]["media_info"]["hasAudio"][media_file_path] = r["has_audio"]
                        project_updated, projectChanged = True, True
                    else:  # file path not found
                        if ("media_file_info" in pj[OBSERVATIONS][obs]
                            and len(pj[OBSERVATIONS][obs]["media_file_info"]) == 1
                            and len(pj[OBSERVATIONS][obs]["file"][PLAYER1]) == 1
                            and len(pj[OBSERVATIONS][obs]["file"][PLAYER2]) == 0):
                                media_md5_key = list(pj[OBSERVATIONS][obs]["media_file_info"].keys())[0]
                                # duration
                                pj[OBSERVATIONS][obs]["media_info"] = {"length": {media_file_path:
                                         pj[OBSERVATIONS][obs]["media_file_info"][media_md5_key]["video_length"]/1000}}
                                project_updated, projectChanged = True, True

                                # FPS
                                if "nframe" in pj[OBSERVATIONS][obs]["media_file_info"][media_md5_key]:
                                    pj[OBSERVATIONS][obs]['media_info']['fps'] = {media_file_path:
                                         pj[OBSERVATIONS][obs]['media_file_info'][media_md5_key]['nframe']
                                         / (pj[OBSERVATIONS][obs]['media_file_info'][media_md5_key]['video_length']/1000)}
                                else:
                                    pj[OBSERVATIONS][obs]['media_info']['fps'] = {media_file_path: 0}

    if project_updated:
        msg = "The media files information was updated to the new project format."
        
    return projectFileName, projectChanged, pj, msg


def event_type(code, ethogram):
    """
    returns type of event for code

    Args:
        ethogram (dict); etogram of project
        code (str): behavior code

    Returns:
        str: STATE, POINT or None if code not found in ethogram
    """

    for idx in ethogram:
        if ethogram[idx][BEHAVIOR_CODE] == code:
            return ethogram[idx][TYPE].upper()
    return None


def check_events(obsId, ethogram, observation):
    """
    Check if coded events are in ethogram
    
    Args:
        obsId (str): id of observation to check
        ethogram (dict): ethogram of project
        observation (dict): observation to be checked

    Returns:
        list: list of behaviors found in observations but not in ethogram
    """

    coded_behaviors = {event[EVENT_BEHAVIOR_FIELD_IDX] for event in observation[EVENTS]}
    behaviors_in_ethogram = [ethogram[idx][BEHAVIOR_CODE] for idx in ethogram]

    not_in_ethogram = [coded_behavior for coded_behavior in coded_behaviors if coded_behavior not in behaviors_in_ethogram]
    return not_in_ethogram


def check_state_events_obs(obsId, ethogram, observation, time_format=HHMMSS):
    """
    check state events for the observation obsId
    check if number is odd

    Args:
        obsId (str): id of observation to check
        ethogram (dict): ethogram of project
        observation (dict): observation to be checked
        time_firmat (str): time format

    Returns:
        set (bool, str): if OK True else False , message
    """

    out = ""

    # check if behaviors are defined as "state event"
    event_types = {ethogram[idx]["type"] for idx in ethogram}

    if not event_types or event_types == {"Point event"}:
        return (True, "No behavior is defined as `State event`")

    flagStateEvent = False
    subjects = [event[EVENT_SUBJECT_FIELD_IDX] for event in observation[EVENTS]]
    ethogram_behaviors = {ethogram[idx]["code"] for idx in ethogram}

    for subject in sorted(set(subjects)):

        behaviors = [event[EVENT_BEHAVIOR_FIELD_IDX] for event in observation[EVENTS]
                     if event[EVENT_SUBJECT_FIELD_IDX] == subject]

        for behavior in sorted(set(behaviors)):
            if behavior not in ethogram_behaviors:
                return (False, "The behaviour <b>{}</b> is not defined in the ethogram.<br>".format(behavior))
            else:
                if STATE in event_type(behavior, ethogram).upper():
                    flagStateEvent = True
                    lst, memTime = [], {}
                    for event in [event for event in observation[EVENTS]
                                  if event[EVENT_BEHAVIOR_FIELD_IDX] == behavior and
                                  event[EVENT_SUBJECT_FIELD_IDX] == subject]:

                        behav_modif = [event[EVENT_BEHAVIOR_FIELD_IDX], event[EVENT_MODIFIER_FIELD_IDX]]

                        if behav_modif in lst:
                            lst.remove(behav_modif)
                            del memTime[str(behav_modif)]
                        else:
                            lst.append(behav_modif)
                            memTime[str(behav_modif)] = event[EVENT_TIME_FIELD_IDX]

                    for event in lst:
                        out += ("""The behavior <b>{behavior}</b> {modifier} is not PAIRED for subject"""
                                """ "<b>{subject}</b>" at <b>{time}</b><br>""").format(
                                      behavior=behavior,
                                      modifier=("(modifier "+ event[1] + ") ") if event[1] else "",
                                      subject=subject if subject else NO_FOCAL_SUBJECT,
                                      time=memTime[str(event)] if time_format == S else utilities.seconds2time(memTime[str(event)]))

    return (False, out) if out else (True, "All state events are PAIRED")


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
    subjects = [event[EVENT_SUBJECT_FIELD_IDX] for event in observation[EVENTS]]
    ethogram_behaviors = {ethogram[idx]["code"] for idx in ethogram}

    for subject in sorted(set(subjects)):

        behaviors = [event[EVENT_BEHAVIOR_FIELD_IDX] for event in observation[EVENTS]
                     if event[EVENT_SUBJECT_FIELD_IDX] == subject]

        for behavior in sorted(set(behaviors)):
            if (behavior in ethogram_behaviors) and (STATE in event_type(behavior, ethogram).upper()):

                flagStateEvent = True
                lst, memTime = [], {}
                for event in [event for event in observation[EVENTS]
                              if event[EVENT_BEHAVIOR_FIELD_IDX] == behavior and
                              event[EVENT_SUBJECT_FIELD_IDX] == subject]:

                    behav_modif = [event[EVENT_BEHAVIOR_FIELD_IDX], event[EVENT_MODIFIER_FIELD_IDX]]

                    if behav_modif in lst:
                        lst.remove(behav_modif)
                        del memTime[str(behav_modif)]
                    else:
                        lst.append(behav_modif)
                        memTime[str(behav_modif)] = event[EVENT_TIME_FIELD_IDX]

                for event in lst:

                    last_event_time = max([fix_at_time] + [x[0] for x in closing_events_to_add])
                    print("last_event_time", last_event_time, type(last_event_time))

                    closing_events_to_add.append([last_event_time + Decimal("0.001"),
                                                  subject,
                                                  behavior,
                                                  event[1], # modifiers
                                                  "" # comment
                                                  ])
                    
                    '''
                    out += ("""The behavior <b>{behavior}</b> {modifier} is not PAIRED for subject"""
                            """ "<b>{subject}</b>" at <b>{time}</b><br>""").format(
                                  behavior=behavior,
                                  modifier=("(modifier "+ event[1] + ") ") if event[1] else "",
                                  subject=subject if subject else NO_FOCAL_SUBJECT,
                                  time=memTime[str(event)] if time_format == S else utilities.seconds2time(memTime[str(event)]))
                    '''

    return closing_events_to_add



def check_project_integrity(pj, time_format, project_file_name):
    """
    check project integrity
    
    check if behaviors in observations are in ethogram
    
    Args:
        pj (dict): BORIS project
    
    Returns:
        str: message
    """
    out = ""
    
    # check for behavior not in ethogram
    # remove because already tested bt check_state_events_obs function
    '''
    behav_not_in_ethogram = []
    for obs_id in pj[OBSERVATIONS]:
        behav_not_in_ethogram.extend(check_events(obs_id, pj[ETHOGRAM], pj[OBSERVATIONS][obs_id]))
    for behav in behav_not_in_ethogram:
        if out:
            out += "<br><br>"
        out += ("The behavior <b>{}</b> is found in observation "
                "but not is not present in ethogram.").format(behav)
    '''
    try:
        # check for unpaired state events
        for obs_id in pj[OBSERVATIONS]:
            ok, msg = check_state_events_obs(obs_id, pj[ETHOGRAM], pj[OBSERVATIONS][obs_id], time_format)
            if not ok:
                if out:
                    out += "<br><br>"
                out += "Observation: <b>{}</b><br>{}".format(obs_id, msg)
    
        # check if behavior belong to category that is not in categories list
        for idx in pj[ETHOGRAM]:
            if BEHAVIOR_CATEGORY in pj[ETHOGRAM][idx]:
                if pj[ETHOGRAM][idx][BEHAVIOR_CATEGORY]:
                    if pj[ETHOGRAM][idx][BEHAVIOR_CATEGORY] not in pj[BEHAVIORAL_CATEGORIES]:
                        if out:
                            out += "<br><br>"
                        out += ("The behavior <b>{}</b> belongs to the behavioral category <b>{}</b> "
                               "that is no more in behavioral categories list.").format(pj[ETHOGRAM][idx][BEHAVIOR_CODE],
                                                                                        pj[ETHOGRAM][idx][BEHAVIOR_CATEGORY])
    
        # check if all media are available
        for obs_id in pj[OBSERVATIONS]:
            ok, msg = check_if_media_available(pj[OBSERVATIONS][obs_id], project_file_name)
            if not ok:
                if out:
                    out += "<br><br>"
                out += "Observation: <b>{}</b><br>{}".format(obs_id, msg)
    
        return out
    except:
        return str(sys.exc_info()[1])

