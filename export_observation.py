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

import tablib
import logging
import os
import sys

from config import *
import utilities
import project_functions
import db_functions


def export_events(parameters, obsId, observation, ethogram, file_name, output_format):
    """
    export events

    Args:
        parameters (dict): subjects, behaviors
        obsId (str): observation id
        observation (dict): observation
        ethogram (dict): ethogram of project
        file_name (str): file name for exporting events
        output_format (str): output for exporting events

    Returns:
        bool: result: True if OK else False
        str: error message
    """

    total_length = "{0:.3f}".format(project_functions.observation_total_length(observation))

    eventsWithStatus = project_functions.events_start_stop(ethogram, observation[EVENTS])

    # check max number of modifiers
    max_modifiers = 0
    for event in eventsWithStatus:
        for c in pj_events_fields:
            if c == "modifier" and event[pj_obs_fields[c]]:
                max_modifiers = max(max_modifiers, len(event[pj_obs_fields[c]].split("|")))

    # media file number
    mediaNb = 0
    if observation["type"] in [MEDIA]:
        for idx in observation[FILE]:
            for media in observation[FILE][idx]:
                mediaNb += 1

    rows = []

    # observation id
    rows.append(["Observation id", obsId])
    rows.append([""])

    # media file name
    if observation["type"] in [MEDIA]:
        rows.append(["Media file(s)"])
    else:
        rows.append(["Live observation"])
    rows.append([""])

    if observation[TYPE] in [MEDIA]:

        for idx in observation[FILE]:
            for media in observation[FILE][idx]:
                rows.append(["Player #{0}".format(idx), media])
    rows.append([""])

    # date
    if "date" in observation:
        rows.append(["Observation date", observation["date"].replace("T", " ")])
    rows.append([""])

    # description
    if "description" in observation:
        rows.append(["Description", utilities.eol2space(observation["description"])])
    rows.append([""])

    # time offset
    if "time offset" in observation:
        rows.append(["Time offset (s)", observation["time offset"]])
    rows.append([""])

    # independent variables
    if INDEPENDENT_VARIABLES in observation:
        rows.extend([["independent variables"],["variable", "value"]])

        for variable in observation[INDEPENDENT_VARIABLES]:
            rows.append([variable, observation[INDEPENDENT_VARIABLES][variable]])

    rows.append([""])

    # write table header
    col = 0
    header = ["Time"]
    header.extend(["Media file path", "Total length", "FPS"])

    header.extend(["Subject", "Behavior"])
    for x in range(1, max_modifiers + 1):
        header.append("Modifier {}".format(x))
    header.extend(["Comment", "Status"])

    rows.append(header)

    duration1 = []   # in seconds
    if observation["type"] in [MEDIA]:
        try:
            for mediaFile in observation[FILE][PLAYER1]:
                duration1.append(observation["media_info"]["length"][mediaFile])
        except:
            pass

    for event in eventsWithStatus:
        
        if (((event[SUBJECT_EVENT_FIELD] in parameters["selected subjects"]) or
           (event[SUBJECT_EVENT_FIELD] == "" and NO_FOCAL_SUBJECT in parameters["selected subjects"])) and
           (event[BEHAVIOR_EVENT_FIELD] in parameters["selected behaviors"])):

            fields = []
            fields.append(utilities.intfloatstr(str(event[EVENT_TIME_FIELD_IDX])))

            if observation["type"] in [MEDIA]:

                time_ = event[EVENT_TIME_FIELD_IDX] - observation[TIME_OFFSET]
                if time_ < 0:
                    time_ = 0

                mediaFileIdx = [idx1 for idx1, x in enumerate(duration1) if time_ >= sum(duration1[0:idx1])][-1]
                fields.append(utilities.intfloatstr(str(observation[FILE][PLAYER1][mediaFileIdx])))
                fields.append(total_length)
                fields.append(observation["media_info"]["fps"][observation[FILE][PLAYER1][mediaFileIdx]])  # fps

            if observation["type"] in [LIVE]:
                fields.append(LIVE) # media
                fields.append(total_length) # total length
                fields.append("NA") # FPS

            fields.append(event[EVENT_SUBJECT_FIELD_IDX])
            fields.append(event[EVENT_BEHAVIOR_FIELD_IDX])

            modifiers = event[EVENT_MODIFIER_FIELD_IDX].split("|")
            while len(modifiers) < max_modifiers:
                modifiers.append("")

            for m in modifiers:
                fields.append(m)
            fields.append(event[EVENT_COMMENT_FIELD_IDX].replace(os.linesep, " "))
            # status
            fields.append(event[-1])

            rows.append(fields)

    maxLen = max([len(r) for r in rows])
    data = tablib.Dataset()

    data.title = obsId
    # check if worksheet name will be > 31 char
    if output_format in ["xls", "xlsx"]:
        for forbidden_char in r"\/*[]:?":
            data.title = data.title.replace(forbidden_char, " ")

    if output_format in ["xls"]:
        if len(data.title) > 31:
            data.title = data.title[0:31]

    for row in rows:
        data.append(utilities.complete(row, maxLen))

    r, msg = dataset_write(data, file_name, output_format)

    return r, msg


def dataset_write(dataset, file_name, output_format):
    """
    write a tablib dataset to file in specified format
    
    Args:
        dataset (tablib.dataset): dataset to write
        file_name (str): file name
        output_format (str): format of output
        
    Returns:
        bool: result
        str: error message
    """

    try:
        if output_format == "tsv":
            with open(file_name, "wb") as f:
                f.write(str.encode(dataset.tsv))
            return True, ""
        if output_format == "csv":
            with open(file_name, "wb") as f:
                f.write(str.encode(dataset.csv))
            return True, ""
        if output_format == "ods":
            with open(file_name, "wb") as f:
                f.write(dataset.ods)
            return True, ""

        if output_format in ["xls", "xlsx"]:
            # check worksheet title
            for forbidden_char in EXCEL_FORBIDDEN_CHARACTERS:
                dataset.title = dataset.title.replace(forbidden_char, " ")

        if output_format == "xlsx":
            with open(file_name, "wb") as f:
                f.write(dataset.xlsx)
            return True, ""

        if output_format == "xls":
            if len(dataset.title) > 31:
                dataset.title = dataset.title[:31]
            with open(file_name, "wb") as f:
                f.write(dataset.xls)
            return True, ""

        if output_format == "html":
            with open(file_name, "wb") as f:
                f.write(str.encode(dataset.html))
            return True, ""

        return False, "Format {} not found".format(output_format)

    except:
        errorMsg = sys.exc_info()[1]
        return False, str(errorMsg)



def export_aggregated_events(pj, parameters, obsId):
    """
    export aggregated events

    Args:
        pj (dict): BORIS project
        parameters (dict): subjects, behaviors
        obsId (str): observation id

    Returns:
        tablib.Dataset:

    """
    data = tablib.Dataset()
    observation = pj[OBSERVATIONS][obsId]

    duration1 = []   # in seconds
    if observation[TYPE] in [MEDIA]:
        try:
            for mediaFile in observation[FILE][PLAYER1]:
                if "media_info" in observation:
                    duration1.append(observation["media_info"]["length"][mediaFile])
        except:
            duration1 = []

    total_length = "{0:.3f}".format(project_functions.observation_total_length(observation))

    cursor = db_functions.load_events_in_db(pj,
                                            parameters["selected subjects"],
                                            [obsId],
                                            parameters["selected behaviors"])

    for subject in parameters["selected subjects"]:

        for behavior in parameters["selected behaviors"]:

            cursor.execute("SELECT occurence, modifiers, comment FROM events WHERE observation = ? AND subject = ? AND code = ? ORDER by occurence",
                           (obsId, subject, behavior))
            rows = list(cursor.fetchall())

            for idx, row in enumerate(rows):

                if observation[TYPE] in [MEDIA]:
                    if duration1:
                        mediaFileIdx = [idx1 for idx1, x in enumerate(duration1) if row["occurence"] >= sum(duration1[0:idx1])][-1]
                        mediaFileString = observation[FILE][PLAYER1][mediaFileIdx]
                        fpsString = observation["media_info"]["fps"][observation[FILE][PLAYER1][mediaFileIdx]]
                    else:
                        mediaFileString = "-"
                        fpsString = "NA"

                if observation[TYPE] in [LIVE]:
                    mediaFileString = "LIVE"
                    fpsString = "NA"

                if POINT in project_functions.event_type(behavior, pj[ETHOGRAM]):

                    row_data = []
                    row_data.extend([obsId,
                                observation["date"].replace("T", " "),
                                mediaFileString,
                                total_length,
                                fpsString])

                    # independent variables
                    if INDEPENDENT_VARIABLES in pj:
                        for idx_var in utilities.sorted_keys(pj[INDEPENDENT_VARIABLES]):
                            if pj[INDEPENDENT_VARIABLES][idx_var]["label"] in observation[INDEPENDENT_VARIABLES]:
                               row_data.append(observation[INDEPENDENT_VARIABLES][pj[INDEPENDENT_VARIABLES][idx_var]["label"]])
                            else:
                                row_data.append("")

                    row_data.extend([subject,
                                behavior,
                                row["modifiers"].strip(),
                                POINT,
                                "{0:.3f}".format(row["occurence"]), # start
                                "NA", # stop
                                "NA", # duration
                                row["comment"],
                                ""
                                ])
                    data.append(row_data)

                if STATE in project_functions.event_type(behavior, pj[ETHOGRAM]):
                    if idx % 2 == 0:
                        row_data = []
                        row_data.extend([obsId,
                                observation["date"].replace("T", " "),
                                mediaFileString,
                                total_length,
                                fpsString])

                        # independent variables
                        if INDEPENDENT_VARIABLES in pj:
                            for idx_var in utilities.sorted_keys(pj[INDEPENDENT_VARIABLES]):
                                if pj[INDEPENDENT_VARIABLES][idx_var]["label"] in observation[INDEPENDENT_VARIABLES]:
                                   row_data.append(observation[INDEPENDENT_VARIABLES][pj[INDEPENDENT_VARIABLES][idx_var]["label"]])
                                else:
                                    row_data.append("")

                        row_data.extend([subject,
                                behavior,
                                row["modifiers"].strip(),
                                STATE,
                                "{0:.3f}".format(row["occurence"]),
                                "{0:.3f}".format(rows[idx + 1]["occurence"]),
                                "{0:.3f}".format(rows[idx + 1]["occurence"] - row["occurence"]),
                                row["comment"],
                                rows[idx + 1]["comment"]
                                ])
                        data.append(row_data)

    return data

