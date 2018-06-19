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
import datetime
import pathlib

from config import *
import utilities
import project_functions
import db_functions


def export_events_jwatcher(parameters, obsId, observation, ethogram, file_name, output_format):
    """
    export events jwatcher .dat format

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

    # TODO: check "no focal subject"
    print("selected subjects", parameters["selected subjects"])
    
    for subject in parameters["selected subjects"]:

        # select events for current subject
        events = []
        for event in observation[EVENTS]:
            if event[SUBJECT_EVENT_FIELD] == subject or (subject == "No focal subject" and event[SUBJECT_EVENT_FIELD] == ""):
                events.append(event)

        total_length = 0   # in seconds
        if observation[EVENTS]:
            total_length = observation[EVENTS][-1][0] - observation[EVENTS][0][0]  # last event time - first event time

        file_name_subject = str(pathlib.Path(file_name).parent / pathlib.Path(file_name).stem) + "_" + subject + ".dat"

        rows = ["FirstLineOfData"]
        rows.append("#-----------------------------------------------------------")
        rows.append("# Name: {}".format(pathlib.Path(file_name_subject).name))
        rows.append("# Format: Focal Data File 1.0")
        rows.append("# Updated: {}".format(datetime.datetime.now().isoformat()))
        rows.append("#-----------------------------------------------------------")
        rows.append("")
        rows.append("FocalMasterFile={}".format(pathlib.Path(file_name_subject).with_suffix(".fmf")))
        rows.append("")

        rows.append("# Observation started: {}".format(observation["date"]))
        try:
            start_time = datetime.datetime.strptime(observation["date"], '%Y-%m-%dT%H:%M:%S')
        except ValueError:
            start_time = datetime.datetime(1970, 1, 1, 0, 0)
        start_time_epoch = int((start_time - datetime.datetime(1970, 1, 1, 0, 0)).total_seconds() * 1000)
        rows.append("StartTime={}".format(start_time_epoch))

        stop_time = (start_time + datetime.timedelta(seconds=float(total_length))).isoformat()
        stop_time_epoch = int(start_time_epoch + float(total_length) * 1000)
    
        rows.append("# Observation stopped: {}".format(stop_time))
        rows.append("StopTime={}".format(stop_time_epoch))

        rows.extend([""] * 3)
        rows.append("#BEGIN DATA")
        rows[0] = "FirstLineOfData={}".format(len(rows) + 1)

        all_observed_behaviors = []
        for event in events:
            behavior_key = [ethogram[k][BEHAVIOR_KEY] for k in ethogram if ethogram[k][BEHAVIOR_CODE] == event[EVENT_BEHAVIOR_FIELD_IDX]][0]
            rows.append("{time_ms}, {bevavior_key}".format(time_ms=int(event[EVENT_TIME_FIELD_IDX] * 1000),
                                                           bevavior_key=behavior_key))
            if (event[EVENT_BEHAVIOR_FIELD_IDX], behavior_key) not in all_observed_behaviors:
                all_observed_behaviors.append((event[EVENT_BEHAVIOR_FIELD_IDX], behavior_key))

        rows.append("{}, {}".format(int(events[-1][0] * 1000), "EOF\n"))

        try:
            with open(file_name_subject, "w") as f_out:
                f_out.write("\n".join(rows))
        except:
            return False, "File DAT not created for subject {}: {}".format(subject, sys.exc_info()[1])

        # create fmf file
        rows = []
        rows.append("#-----------------------------------------------------------")
        rows.append("# Name: {}".format(pathlib.Path(file_name_subject).with_suffix(".fmf").name))
        rows.append("# Format: Focal Master File 1.0")
        rows.append("# Updated: {}".format(datetime.datetime.now().isoformat()))
        rows.append("#-----------------------------------------------------------")
        for (behav, key) in all_observed_behaviors:
            rows.append("Behaviour.name.{}={}".format(key, behav))
            rows.append("Behaviour.description.{}={}".format(key, ""))
            
        rows.append("DurationMilliseconds={}".format(int(float(total_length) * 1000)))
        rows.append("CountUp=false")
        rows.append("Question.1=")
        rows.append("Question.2=")
        rows.append("Question.3=")
        rows.append("Question.4=")
        rows.append("Question.5=")
        rows.append("Question.6=")
        rows.append("Notes=")
        rows.append("Supplementary=\n")

        try:
            with open(pathlib.Path(file_name_subject).with_suffix(".fmf"), "w") as f_out:
                f_out.write("\n".join(rows))
        except:
            return False, "File FMF not created: {}".format(sys.exc_info()[1])

        # create FAF file
        rows = []
        rows.append("#-----------------------------------------------------------")
        rows.append("# Name: {}".format(pathlib.Path(file_name_subject).with_suffix(".faf").name))
        rows.append("# Format: Focal Analysis Master File 1.0")
        rows.append("# Updated: {}".format(datetime.datetime.now().isoformat()))
        rows.append("#-----------------------------------------------------------")
        rows.append("FocalMasterFile={}".format(str(pathlib.Path(file_name_subject).with_suffix(".fmf"))))
        rows.append("")
        rows.append("TimeBinDuration=0.0")
        rows.append("EndWithLastCompleteBin=true")
        rows.append("")
        rows.append("ScoreFromBeginning=true")
        rows.append("ScoreFromBehavior=false")
        rows.append("ScoreFromFirstBehavior=false")
        rows.append("ScoreFromOffset=false")
        rows.append("")
        rows.append("Offset=0.0")
        rows.append("BehaviorToScoreFrom=")
        rows.append("")
        rows.append("OutOfSightCode=???")
        rows.append("")
        rows.append("Report.StateNaturalInterval.Occurrence=false")
        rows.append("Report.StateNaturalInterval.TotalTime=false")
        rows.append("Report.StateNaturalInterval.Average=false")
        rows.append("Report.StateNaturalInterval.StandardDeviation=false")
        rows.append("Report.StateNaturalInterval.ProportionOfTime=false")
        rows.append("Report.StateNaturalInterval.ProportionOfTimeInSight=false")
        rows.append("Report.StateNaturalInterval.ConditionalProportionOfTime=false")
        rows.append("")
        rows.append("Report.StateNaturalDuration.Occurrence=false")
        rows.append("Report.StateNaturalDuration.TotalTime=false")
        rows.append("Report.StateNaturalDuration.Average=false")
        rows.append("Report.StateNaturalDuration.StandardDeviation=false")
        rows.append("Report.StateNaturalDuration.ProportionOfTime=false")
        rows.append("Report.StateNaturalDuration.ProportionOfTimeInSight=false")
        rows.append("Report.StateNaturalDuration.ConditionalProportionOfTime=false")
        rows.append("")
        rows.append("Report.StateAllInterval.Occurrence=false")
        rows.append("Report.StateAllInterval.TotalTime=false")
        rows.append("Report.StateAllInterval.Average=false")
        rows.append("Report.StateAllInterval.StandardDeviation=false")
        rows.append("Report.StateAllInterval.ProportionOfTime=false")
        rows.append("Report.StateAllInterval.ProportionOfTimeInSight=false")
        rows.append("Report.StateAllInterval.ConditionalProportionOfTime=false")
        rows.append("")
        rows.append("Report.StateAllDuration.Occurrence=true")
        rows.append("Report.StateAllDuration.TotalTime=true")
        rows.append("Report.StateAllDuration.Average=true")
        rows.append("Report.StateAllDuration.StandardDeviation=false")
        rows.append("Report.StateAllDuration.ProportionOfTime=false")
        rows.append("Report.StateAllDuration.ProportionOfTimeInSight=true")
        rows.append("Report.StateAllDuration.ConditionalProportionOfTime=false")
        rows.append("")
        rows.append("Report.EventNaturalInterval.EventCount=false")
        rows.append("Report.EventNaturalInterval.Occurrence=false")
        rows.append("Report.EventNaturalInterval.Average=false")
        rows.append("Report.EventNaturalInterval.StandardDeviation=false")
        rows.append("Report.EventNaturalInterval.ConditionalNatEventCount=false")
        rows.append("Report.EventNaturalInterval.ConditionalNatRate=false")
        rows.append("Report.EventNaturalInterval.ConditionalNatIntervalOccurance=false")
        rows.append("Report.EventNaturalInterval.ConditionalNatIntervalAverage=false")
        rows.append("Report.EventNaturalInterval.ConditionalNatIntervalStandardDeviation=false")
        rows.append("Report.EventNaturalInterval.ConditionalAllEventCount=false")
        rows.append("Report.EventNaturalInterval.ConditionalAllRate=false")
        rows.append("Report.EventNaturalInterval.ConditionalAllIntervalOccurance=false")
        rows.append("Report.EventNaturalInterval.ConditionalAllIntervalAverage=false")
        rows.append("Report.EventNaturalInterval.ConditionalAllIntervalStandardDeviation=false")
        rows.append("")
        rows.append("AllCodesMutuallyExclusive=true")
        rows.append("")

        for (behav, key) in all_observed_behaviors:
            rows.append("Behavior.isModified.{}=false".format(key))
            rows.append("Behavior.isSubtracted.{}=false".format(key))
            rows.append("Behavior.isIgnored.{}=false".format(key))
            rows.append("Behavior.isEventAnalyzed.{}=false".format(key))
            rows.append("Behavior.switchesOff.{}=".format(key))
            rows.append("")

        try:
            with open(pathlib.Path(file_name_subject).with_suffix(".faf"), "w") as f_out:
                f_out.write("\n".join(rows))
        except:
            return False, "File FAF not created: {}".format(sys.exc_info()[1])


    return True, ""


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
    if observation["type"] == MEDIA:
        for player in observation[FILE]:
            mediaNb += len(observation[FILE][player])

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
        for player in sorted(list(observation[FILE].keys())):
            for media in observation[FILE][player]:
                rows.append(["Player #{0}".format(player), media])
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
        rows.extend([["independent variables"], ["variable", "value"]])

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
        except KeyError:
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
                fields.append(LIVE)  # media
                fields.append(total_length)  # total length
                fields.append("NA")   # FPS

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
        bool: result. True if OK else False
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
        return False, str(sys.exc_info()[1])


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

    ok, msg, connector = db_functions.load_aggregated_events_in_db(pj,
                                                                   parameters["selected subjects"],
                                                                   [obsId],
                                                                   parameters["selected behaviors"])
    if not ok:
        data

    cursor = connector.cursor()

    for subject in parameters["selected subjects"]:

        for behavior in parameters["selected behaviors"]:

            cursor.execute("select distinct modifiers from aggregated_events where subject=? AND behavior=? order by modifiers",
                           (subject, behavior,))
            rows_distinct_modifiers = list(x[0].strip() for x in cursor.fetchall())

            for distinct_modifiers in rows_distinct_modifiers:

                cursor.execute(("SELECT start, stop, type, modifiers, comment, comment_stop FROM aggregated_events "
                                "WHERE subject = ? AND behavior = ? AND modifiers = ? ORDER by start"),
                               (subject, behavior, distinct_modifiers))
                rows = list(cursor.fetchall())

                for row in rows:

                    if observation[TYPE] in [MEDIA]:
                        if duration1:
                            mediaFileIdx = [idx1 for idx1, x in enumerate(duration1) if row["start"] >= sum(duration1[0:idx1])][-1]
                            mediaFileString = observation[FILE][PLAYER1][mediaFileIdx]
                            fpsString = observation["media_info"]["fps"][observation[FILE][PLAYER1][mediaFileIdx]]
                        else:
                            mediaFileString = "-"
                            fpsString = "NA"

                    if observation[TYPE] in [LIVE]:
                        mediaFileString = "LIVE"
                        fpsString = "NA"

                    if row["type"] == POINT:

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
                                         "{0:.3f}".format(row["start"]),  # start
                                         "{0:.3f}".format(row["stop"]),  # stop
                                         "NA",  # duration
                                         row["comment"],
                                         ""
                                         ])
                        data.append(row_data)

                    if row["type"] == STATE:
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
                                             "{0:.3f}".format(row["start"]),
                                             "{0:.3f}".format(row["stop"]),
                                             "{0:.3f}".format(row["stop"] - row["start"]),
                                             row["comment"],
                                             row["comment_stop"]
                                             ])
                            data.append(row_data)

    return data
