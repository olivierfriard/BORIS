"""
BORIS
Behavioral Observation Research Interactive Software
Copyright 2012-2020 Olivier Friard

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
from boris import dialog
from decimal import Decimal

from boris.config import *
from boris import utilities
from boris import project_functions
from boris import db_functions


def export_events_jwatcher(parameters: list,
                           obsId: str,
                           observation: list,
                           ethogram: dict,
                           file_name: str,
                           output_format: str):
    """
    export events jwatcher .dat format

    Args:
        parameters (dict): subjects, behaviors
        obsId (str): observation id
        observation (dict): observation
        ethogram (dict): ethogram of project
        file_name (str): file name for exporting events
        output_format (str): Not used for compatibility with export_events function

    Returns:
        bool: result: True if OK else False
        str: error message
    """
    try:
        for subject in parameters["selected subjects"]:

            # select events for current subject
            events = []
            for event in observation[EVENTS]:
                if event[SUBJECT_EVENT_FIELD] == subject or (subject == "No focal subject" and event[SUBJECT_EVENT_FIELD] == ""):
                    events.append(event)

            if not events:
                continue

            total_length = 0   # in seconds
            if observation[EVENTS]:
                total_length = observation[EVENTS][-1][0] - observation[EVENTS][0][0]  # last event time - first event time

            file_name_subject = str(pathlib.Path(file_name).parent / pathlib.Path(file_name).stem) + "_" + subject + ".dat"

            rows = ["FirstLineOfData"]  # to be completed
            rows.append("#-----------------------------------------------------------")
            rows.append(f"# Name: {pathlib.Path(file_name_subject).name}")
            rows.append("# Format: Focal Data File 1.0")
            rows.append(f"# Updated: {datetime.datetime.now().isoformat()}")
            rows.append("#-----------------------------------------------------------")
            rows.append("")
            rows.append(f"FocalMasterFile={pathlib.Path(file_name_subject).with_suffix('.fmf')}")
            rows.append("")

            rows.append(f"# Observation started: {observation['date']}")
            try:
                start_time = datetime.datetime.strptime(observation["date"], '%Y-%m-%dT%H:%M:%S')
            except ValueError:
                start_time = datetime.datetime(1970, 1, 1, 0, 0)
            start_time_epoch = int((start_time - datetime.datetime(1970, 1, 1, 0, 0)).total_seconds() * 1000)
            rows.append(f"StartTime={start_time_epoch}")

            stop_time = (start_time + datetime.timedelta(seconds=float(total_length))).isoformat()
            stop_time_epoch = int(start_time_epoch + float(total_length) * 1000)

            rows.append(f"# Observation stopped: {stop_time}")
            rows.append(f"StopTime={stop_time_epoch}")

            rows.extend([""] * 3)
            rows.append("#BEGIN DATA")
            rows[0] = f"FirstLineOfData={len(rows) + 1}"

            all_observed_behaviors = []
            mem_number_of_state_events = {}
            for event in events:
                behav_code = event[EVENT_BEHAVIOR_FIELD_IDX]

                try:
                    behavior_key = [ethogram[k][BEHAVIOR_KEY] for k in ethogram if ethogram[k][BEHAVIOR_CODE] == behav_code][0]
                except Exception:
                    # coded behavior not defined in ethogram
                    continue
                if [ethogram[k][TYPE] for k in ethogram if ethogram[k][BEHAVIOR_CODE] == behav_code] == [STATE_EVENT]:
                    if behav_code in mem_number_of_state_events:
                        mem_number_of_state_events[behav_code] += 1
                    else:
                        mem_number_of_state_events[behav_code] = 1
                    # skip the STOP event in case of STATE
                    if mem_number_of_state_events[behav_code] % 2 == 0:
                        continue

                rows.append(f"{int(event[EVENT_TIME_FIELD_IDX] * 1000)}, {behavior_key}")
                if (event[EVENT_BEHAVIOR_FIELD_IDX], behavior_key) not in all_observed_behaviors:
                    all_observed_behaviors.append((event[EVENT_BEHAVIOR_FIELD_IDX], behavior_key))

            rows.append(f"{int(events[-1][0] * 1000)}, EOF\n")

            try:
                with open(file_name_subject, "w") as f_out:
                    f_out.write("\n".join(rows))
            except Exception:
                return False, f"File DAT not created for subject {subject}: {sys.exc_info()[1]}"

            # create fmf file
            fmf_file_path = pathlib.Path(file_name_subject).with_suffix(".fmf")
            fmf_creation_answer = ""
            if fmf_file_path.exists():
                fmf_creation_answer = dialog.MessageDialog(
                    programName,
                    (f"The {fmf_file_path} file already exists.<br>"
                     "What do you want to do?"),
                    [OVERWRITE, "Skip file creation", CANCEL])

                if fmf_creation_answer == CANCEL:
                    return True, ""

            rows = []
            rows.append("#-----------------------------------------------------------")
            rows.append(f"# Name: {pathlib.Path(file_name_subject).with_suffix('.fmf').name}")
            rows.append("# Format: Focal Master File 1.0")
            rows.append(f"# Updated: {datetime.datetime.now().isoformat()}")
            rows.append("#-----------------------------------------------------------")
            for (behav, key) in all_observed_behaviors:
                rows.append(f"Behaviour.name.{key}={behav}")
                behav_description = [ethogram[k][DESCRIPTION] for k in ethogram if ethogram[k][BEHAVIOR_CODE] == behav][0]
                rows.append(f"Behaviour.description.{key}={behav_description}")

            rows.append(f"DurationMilliseconds={int(float(total_length) * 1000)}")
            rows.append("CountUp=false")
            rows.append("Question.1=")
            rows.append("Question.2=")
            rows.append("Question.3=")
            rows.append("Question.4=")
            rows.append("Question.5=")
            rows.append("Question.6=")
            rows.append("Notes=")
            rows.append("Supplementary=\n")

            if fmf_creation_answer == OVERWRITE or fmf_creation_answer == "":
                try:
                    with open(fmf_file_path, "w") as f_out:
                        f_out.write("\n".join(rows))
                except Exception:
                    return False, f"File FMF not created: {sys.exc_info()[1]}"

            # create FAF file
            faf_file_path = pathlib.Path(file_name_subject).with_suffix(".faf")
            faf_creation_answer = ""
            if faf_file_path.exists():
                faf_creation_answer = dialog.MessageDialog(programName,
                                                           (f"The {faf_file_path} file already exists.<br>"
                                                            "What do you want to do?"),
                                                           [OVERWRITE, "Skip file creation", CANCEL])
                if faf_creation_answer == CANCEL:
                    return True, ""

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
            rows.append("OutOfSightCode=")
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
                rows.append(f"Behavior.isModified.{key}=false")
                rows.append(f"Behavior.isSubtracted.{key}=false")
                rows.append(f"Behavior.isIgnored.{key}=false")
                rows.append(f"Behavior.isEventAnalyzed.{key}=false")
                rows.append(f"Behavior.switchesOff.{key}=")
                rows.append("")

            if faf_creation_answer == "" or faf_creation_answer == OVERWRITE:
                try:
                    with open(pathlib.Path(file_name_subject).with_suffix(".faf"), "w") as f_out:
                        f_out.write("\n".join(rows))
                except Exception:
                    return False, f"File FAF not created: {sys.exc_info()[1]}"

        return True, ""

    except Exception:
        logging.critical("Error during exporting the events for JWatcher")
        dialog.error_message("exporting the events for JWatcher", sys.exc_info())
        return False, ""


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

    total_length = f"{project_functions.observation_total_length(observation):.3f}"

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
    elif observation["type"] in [LIVE]:
        rows.append(["Live observation"])
    else:
        rows.append(["?"])
    rows.append([""])

    if observation[TYPE] in [MEDIA]:
        for player in sorted(list(observation[FILE].keys())):
            for media in observation[FILE][player]:
                rows.append([f"Player #{player}", media])
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

    header.extend(["Subject", "Behavior", "Behavioral category"])

    behavioral_category = project_functions.behavior_category(ethogram)

    for x in range(1, max_modifiers + 1):
        header.append(f"Modifier {x}")
    header.extend(["Comment", "Status"])

    rows.append(header)

    duration1 = []   # in seconds
    if observation["type"] in [MEDIA]:
        try:
            for mediaFile in observation[FILE][PLAYER1]:
                duration1.append(observation[MEDIA_INFO]["length"][mediaFile])
        except KeyError:
            pass

    for event in eventsWithStatus:
        if (((event[SUBJECT_EVENT_FIELD] in parameters["selected subjects"])
                or (event[SUBJECT_EVENT_FIELD] == "" and NO_FOCAL_SUBJECT in parameters["selected subjects"]))
                and (event[BEHAVIOR_EVENT_FIELD] in parameters["selected behaviors"])):

            fields = []
            fields.append(utilities.intfloatstr(str(event[EVENT_TIME_FIELD_IDX])))

            if observation["type"] in [MEDIA]:

                time_ = event[EVENT_TIME_FIELD_IDX] - observation[TIME_OFFSET]
                if time_ < 0:
                    time_ = 0

                if duration1:
                    mediaFileIdx = [idx1 for idx1, x in enumerate(duration1) if time_ >= sum(duration1[0:idx1])][-1]
                    fields.append(observation[FILE][PLAYER1][mediaFileIdx])
                    fields.append(total_length)
                    # FPS
                    try:
                        fields.append(observation[MEDIA_INFO]["fps"][observation[FILE][PLAYER1][mediaFileIdx]])  # fps
                    except KeyError:
                        fields.append("NA")
                else:
                    fields.append("NA")  # media file
                    fields.append("NA")  # FPS

            if observation["type"] in [LIVE]:
                fields.append(LIVE)  # media
                fields.append(total_length)  # total length
                fields.append("NA")   # FPS

            fields.append(event[EVENT_SUBJECT_FIELD_IDX])
            fields.append(event[EVENT_BEHAVIOR_FIELD_IDX])

            # behavioral category

            try:
                behav_category = behavioral_category[event[EVENT_BEHAVIOR_FIELD_IDX]]
            except Exception:
                behav_category = ""
            fields.append(behav_category)

            # modifiers
            if max_modifiers:
                modifiers = event[EVENT_MODIFIER_FIELD_IDX].split("|")
                while len(modifiers) < max_modifiers:
                    modifiers.append("")

                for m in modifiers:
                    fields.append(m)

            # comment
            fields.append(event[EVENT_COMMENT_FIELD_IDX].replace(os.linesep, " "))
            # status
            fields.append(event[-1])

            rows.append(fields)

    maxLen = max([len(r) for r in rows])
    data = tablib.Dataset()

    data.title = utilities.safe_xl_worksheet_title(obsId, output_format)
    '''
    if output_format in ["xls", "xlsx"]:
        for forbidden_char in EXCEL_FORBIDDEN_CHARACTERS:
            data.title = data.title.replace(forbidden_char, " ")
        if output_format in ["xls"]:
            if len(data.title) > 31:
                data.title = data.title[0:31]
    '''

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

    logging.debug("function: dataset_write")

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

        dataset.title = utilities.safe_xl_worksheet_title(dataset.title, output_format)
        '''
        if output_format in ["xls", "xlsx"]:
            # check worksheet title
            for forbidden_char in EXCEL_FORBIDDEN_CHARACTERS:
                dataset.title = dataset.title.replace(forbidden_char, " ")
        '''
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

        return False, f"Format {output_format} not found"

    except Exception:
        return False, str(sys.exc_info()[1])


def export_aggregated_events(pj: dict, parameters: dict, obsId: str):
    """
    export aggregated events

    Args:
        pj (dict): BORIS project
        parameters (dict): subjects, behaviors
        obsId (str): observation id

    Returns:
        tablib.Dataset:

    """
    logging.debug(f"function: export aggregated events {parameters} {obsId}")

    interval = parameters["time"]
    start_time = parameters[START_TIME]
    end_time = parameters[END_TIME]

    data = tablib.Dataset()
    observation = pj[OBSERVATIONS][obsId]

    # obs description
    obs_description = observation["description"]

    duration1 = []   # in seconds
    if observation[TYPE] in [MEDIA]:
        try:
            for mediaFile in observation[FILE][PLAYER1]:
                if MEDIA_INFO in observation:
                    duration1.append(observation[MEDIA_INFO]["length"][mediaFile])
        except Exception:
            duration1 = []

    obs_length = project_functions.observation_total_length(pj[OBSERVATIONS][obsId])
    if obs_length == Decimal("-1"):  # media length not available
        interval = TIME_EVENTS

    logging.debug(f"obs_length: {obs_length}")

    ok, msg, connector = db_functions.load_aggregated_events_in_db(pj,
                                                                   parameters[SELECTED_SUBJECTS],
                                                                   [obsId],
                                                                   parameters[SELECTED_BEHAVIORS])
    if connector is None:
        logging.critical(f"error when loading aggregated events in DB")
        return data

    # time
    cursor = connector.cursor()

    if interval == TIME_FULL_OBS:
        min_time = float(0)
        max_time = float(obs_length)

    if interval == TIME_EVENTS:
        try:
            min_time = float(pj[OBSERVATIONS][obsId][EVENTS][0][0])
        except Exception:
            min_time = float(0)
        try:
            max_time = float(pj[OBSERVATIONS][obsId][EVENTS][-1][0])
        except Exception:
            max_time = float(obs_length)

    if interval == TIME_ARBITRARY_INTERVAL:
        min_time = float(start_time)
        max_time = float(end_time)

    # adapt start and stop to the selected time interval
    cursor.execute("UPDATE aggregated_events SET start = ? WHERE observation = ? AND start < ? AND stop BETWEEN ? AND ?",
                   (min_time, obsId, min_time, min_time, max_time, ))
    cursor.execute("UPDATE aggregated_events SET stop = ? WHERE observation = ? AND stop > ? AND start BETWEEN ? AND ?",
                   (max_time, obsId, max_time, min_time, max_time, ))

    cursor.execute("UPDATE aggregated_events SET start = ?, stop = ? WHERE observation = ? AND start < ? AND stop > ?",
                   (min_time, max_time, obsId, min_time, max_time, ))

    cursor.execute("DELETE FROM aggregated_events WHERE observation = ? AND (start < ? AND stop < ?) OR (start > ? AND stop > ?)",
                   (obsId, min_time, min_time, max_time, max_time, ))


    behavioral_category = project_functions.behavior_category(pj[ETHOGRAM])

    for subject in parameters[SELECTED_SUBJECTS]:

        for behavior in parameters[SELECTED_BEHAVIORS]:

            cursor.execute("SELECT distinct modifiers FROM aggregated_events where subject=? AND behavior=? order by modifiers",
                           (subject, behavior,))

            rows_distinct_modifiers = list(x[0] for x in cursor.fetchall())

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
                            try:
                                fpsString = observation[MEDIA_INFO]["fps"][observation[FILE][PLAYER1][mediaFileIdx]]
                            except Exception:
                                fpsString = "NA"
                        else:
                            try:
                                if len(observation[FILE][PLAYER1]) == 1:
                                    mediaFileString = observation[FILE][PLAYER1][0]
                                else:
                                    mediaFileString = "NA"
                            except Exception:
                                mediaFileString = "NA"
                            fpsString = "NA"

                    if observation[TYPE] in [LIVE]:
                        mediaFileString = "LIVE"
                        fpsString = "NA"

                    if row["type"] == POINT:

                        row_data = []
                        row_data.extend([obsId,
                                         observation["date"].replace("T", " "),
                                         obs_description,
                                         mediaFileString,
                                         f"{obs_length:.3f}" if obs_length != Decimal("-1") else "NA",
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
                                         behavioral_category[behavior],
                                         row["modifiers"],
                                         POINT,
                                         f"{row['start']:.3f}",  # start
                                         f"{row['stop']:.3f}",  # stop
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
                                             obs_description,
                                             mediaFileString,
                                             f"{obs_length:.3f}" if obs_length != Decimal("-1") else "NA",
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
                                             behavioral_category[behavior],
                                             row["modifiers"],
                                             STATE,
                                             f"{row['start']:.3f}",
                                             f"{row['stop']:.3f}",
                                             f"{row['stop'] - row['start']:.3f}",
                                             row["comment"],
                                             row["comment_stop"]
                                             ])
                            data.append(row_data)

    return data


def events_to_behavioral_sequences(pj,
                                   obs_id: str,
                                   subj: str,
                                   parameters: dict,
                                   behav_seq_separator: str) -> str:
    """
    return the behavioral sequence (behavioral string) for subject in obs_id

    Args:
        pj (dict): project
        obs_id (str): observation id
        subj (str): subject
        parameters (dict): parameters
        behav_seq_separator (str): separator of behviors in behavioral sequences

    Returns:
        str: behavioral string for selected subject in selected observation
    """

    out = ""
    current_states = []
    events_with_status = project_functions.events_start_stop(pj[ETHOGRAM], pj[OBSERVATIONS][obs_id][EVENTS])

    for event in events_with_status:
        # check if event in selected behaviors
        if event[EVENT_BEHAVIOR_FIELD_IDX] not in parameters[SELECTED_BEHAVIORS]:
            continue

        if event[EVENT_SUBJECT_FIELD_IDX] == subj or (subj == NO_FOCAL_SUBJECT and event[EVENT_SUBJECT_FIELD_IDX] == ""):

            if event[-1] == POINT:
                if current_states:
                    out += "+".join(current_states) + "+" + event[EVENT_BEHAVIOR_FIELD_IDX]
                else:
                    out += event[EVENT_BEHAVIOR_FIELD_IDX]

                if parameters[INCLUDE_MODIFIERS]:
                    out += "&" + event[EVENT_MODIFIER_FIELD_IDX].replace("|", "+")

                out += behav_seq_separator

            if event[-1] == START:
                if parameters[INCLUDE_MODIFIERS]:
                    current_states.append((f"{event[EVENT_BEHAVIOR_FIELD_IDX]}"
                                           f"{'&' if event[EVENT_MODIFIER_FIELD_IDX] else ''}"
                                           f"{event[EVENT_MODIFIER_FIELD_IDX].replace('|', ';')}"))
                else:
                    current_states.append(event[EVENT_BEHAVIOR_FIELD_IDX])

                out += "+".join(sorted(current_states))

                out += behav_seq_separator

            if event[-1] == STOP:

                if parameters[INCLUDE_MODIFIERS]:
                    behav_modif = (f"{event[EVENT_BEHAVIOR_FIELD_IDX]}"
                                   f"{'&' if event[EVENT_MODIFIER_FIELD_IDX] else ''}"
                                   f"{event[EVENT_MODIFIER_FIELD_IDX].replace('|', ';')}")
                else:
                    behav_modif = event[EVENT_BEHAVIOR_FIELD_IDX]
                if behav_modif in current_states:
                    current_states.remove(behav_modif)

                if current_states:
                    out += "+".join(sorted(current_states))

                    out += behav_seq_separator

    # remove last separator (if separator not empty)
    if behav_seq_separator:
        out = out[0: -len(behav_seq_separator)]

    return out


def events_to_behavioral_sequences_all_subj(pj,
                                   obs_id: str,
                                   subjects_list: list,
                                   parameters: dict,
                                   behav_seq_separator: str) -> str:
    """
    return the behavioral sequences for all selected subjects in obs_id

    Args:
        pj (dict): project
        obs_id (str): observation id
        subjects_list (list): list of subjects
        parameters (dict): parameters
        behav_seq_separator (str): separator of behviors in behavioral sequences

    Returns:
        str: behavioral sequences for all selected subjects in selected observation
    """

    out = ""
    current_states = {i:[] for i in subjects_list}
    events_with_status = project_functions.events_start_stop(pj[ETHOGRAM], pj[OBSERVATIONS][obs_id][EVENTS])

    for event in events_with_status:
        # check if event in selected behaviors
        if event[EVENT_BEHAVIOR_FIELD_IDX] not in parameters[SELECTED_BEHAVIORS]:
            continue

        if (event[EVENT_SUBJECT_FIELD_IDX] in subjects_list) or (event[EVENT_SUBJECT_FIELD_IDX] == "" and NO_FOCAL_SUBJECT in subjects_list):

            subject = event[EVENT_SUBJECT_FIELD_IDX] if event[EVENT_SUBJECT_FIELD_IDX] else NO_FOCAL_SUBJECT

            if event[-1] == POINT:
                if current_states[subject]:
                    out += f"[{subject}]" + "+".join(current_states[subject]) + "+" + event[EVENT_BEHAVIOR_FIELD_IDX]
                else:
                    out += f"[{subject}]" + event[EVENT_BEHAVIOR_FIELD_IDX]

                if parameters[INCLUDE_MODIFIERS]:
                    out += "&" + event[EVENT_MODIFIER_FIELD_IDX].replace("|", "+")

                out += behav_seq_separator

            if event[-1] == START:
                if parameters[INCLUDE_MODIFIERS]:
                    current_states[subject].append((f"{event[EVENT_BEHAVIOR_FIELD_IDX]}"
                                           f"{'&' if event[EVENT_MODIFIER_FIELD_IDX] else ''}"
                                           f"{event[EVENT_MODIFIER_FIELD_IDX].replace('|', ';')}"))
                else:
                    current_states[subject].append(event[EVENT_BEHAVIOR_FIELD_IDX])

                out += f"[{subject}]" + "+".join(sorted(current_states[subject]))

                out += behav_seq_separator

            if event[-1] == STOP:

                if parameters[INCLUDE_MODIFIERS]:
                    behav_modif = (f"{event[EVENT_BEHAVIOR_FIELD_IDX]}"
                                   f"{'&' if event[EVENT_MODIFIER_FIELD_IDX] else ''}"
                                   f"{event[EVENT_MODIFIER_FIELD_IDX].replace('|', ';')}")
                else:
                    behav_modif = event[EVENT_BEHAVIOR_FIELD_IDX]
                if behav_modif in current_states[subject]:
                    current_states[subject].remove(behav_modif)

                if current_states[subject]:
                    out += f"[{subject}]" + "+".join(sorted(current_states[subject]))

                    out += behav_seq_separator

    # remove last separator (if separator not empty)
    if behav_seq_separator:
        out = out[0: -len(behav_seq_separator)]

    return out


def events_to_timed_behavioral_sequences(pj: dict,
                                         obs_id: str,
                                         subject: str,
                                         parameters: dict,
                                         precision: float,
                                         behav_seq_separator: str) -> str:
    """
    return the behavioral string for subject in obsId

    Args:
        pj (dict): project
        obs_id (str): observation id
        subj (str): subject
        parameters (dict): parameters
        precision (float): time value for scan sample
        behav_seq_separator (str): separator of behviors in behavioral sequences

    Returns:
        str: behavioral string for selected subject in selected observation
    """

    out = ""
    current_states = []
    # events_with_status = project_functions.events_start_stop(pj[ETHOGRAM], pj[OBSERVATIONS][obs_id][EVENTS])

    state_behaviors_codes = utilities.state_behavior_codes(pj[ETHOGRAM])
    delta = Decimal(str(round(precision, 3)))
    out = ""
    t = Decimal("0.000")

    current = []
    while t < pj[OBSERVATIONS][obs_id][EVENTS][-1][0]:
        '''
        if out:
            out += behav_seq_separator
        '''
        csbs = utilities.get_current_states_modifiers_by_subject(state_behaviors_codes,
                                                                 pj[OBSERVATIONS][obs_id][EVENTS],
                                                                 {"": {"name": subject}},
                                                                 t,
                                                                 include_modifiers=False)[""]
        if csbs:
            if current:
                if csbs == current[-1]:
                    current.append("+".join(csbs))
                else:
                    out.append(current)
                    current = [csbs]
            else:
                current = [csbs]

        t += delta

    return out


def observation_to_behavioral_sequences(pj,
                                        selected_observations,
                                        parameters,
                                        behaviors_separator,
                                        separated_subjects,
                                        timed,
                                        file_name):

    try:
        with open(file_name, "w", encoding="utf-8") as out_file:
            for obs_id in selected_observations:
                # observation id
                out_file.write("\n" + f"# observation id: {obs_id}" + "\n")
                # observation description
                descr = pj[OBSERVATIONS][obs_id]["description"]
                if "\r\n" in descr:
                    descr = descr.replace("\r\n", "\n# ")
                elif "\r" in descr:
                    descr = descr.replace("\r", "\n# ")
                out_file.write(f"# observation description: {descr}\n\n")
                # media file name
                if pj[OBSERVATIONS][obs_id][TYPE] in [MEDIA]:
                    out_file.write(f"# Media file name: {', '.join([os.path.basename(x) for x in pj[OBSERVATIONS][obs_id][FILE][PLAYER1]])}\n\n")
                if pj[OBSERVATIONS][obs_id][TYPE] in [LIVE]:
                    out_file.write(f"# Live observation{os.linesep}{os.linesep}")

                # independent variables
                if INDEPENDENT_VARIABLES in pj[OBSERVATIONS][obs_id]:
                    out_file.write("# Independent variables\n")

                    for variable in pj[OBSERVATIONS][obs_id][INDEPENDENT_VARIABLES]:
                        out_file.write(f"# {variable}: {pj[OBSERVATIONS][obs_id][INDEPENDENT_VARIABLES][variable]}\n")
                out_file.write("\n")

                # one sequence for all subjects
                if not separated_subjects:
                    out = events_to_behavioral_sequences_all_subj(pj,
                                                                  obs_id,
                                                                  parameters[SELECTED_SUBJECTS],
                                                                  parameters,
                                                                  behaviors_separator)
                    if out:
                        out_file.write(out + "\n")

                # one sequence by subject
                if separated_subjects:
                    # selected subjects
                    for subject in parameters[SELECTED_SUBJECTS]:
                        out_file.write(f"\n# {subject if subject else NO_FOCAL_SUBJECT}:\n")

                        if not timed:
                            out = events_to_behavioral_sequences(pj,
                                                                obs_id,
                                                                subject,
                                                                parameters,
                                                                behaviors_separator)
                        if timed:
                            out = events_to_timed_behavioral_sequences(pj,
                                                                    obs_id,
                                                                    subject,
                                                                    parameters,
                                                                    0.001,
                                                                    behaviors_separator)

                        if out:
                            out_file.write(out + "\n")

            return True, ""

    except Exception:
        raise
        error_type, error_file_name, error_lineno = utilities.error_info(sys.exc_info())
        return False, f"{error_type} {error_file_name} {error_lineno}"
