"""
BORIS
Behavioral Observation Research Interactive Software
Copyright 2012-2025 Olivier Friard

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

from decimal import Decimal as dec
import tablib
import logging
import os
import sys
import datetime as dt
import math
import pathlib
from io import StringIO
import pandas as pd
from typing import Tuple

try:
    import pyreadr

    flag_pyreadr_loaded = True
except ModuleNotFoundError:
    flag_pyreadr_loaded = False

from . import dialog
from . import config as cfg
from . import utilities as util
from . import project_functions
from . import observation_operations
from . import db_functions
from . import event_operations


def export_events_jwatcher(
    parameters: dict, obsId: str, observation: list, ethogram: dict, file_name: str, output_format: str
) -> Tuple[bool, str]:
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
    for subject in parameters[cfg.SELECTED_SUBJECTS]:
        # select events for current subject
        events = []
        for event in observation[cfg.EVENTS]:
            if event[cfg.EVENT_SUBJECT_FIELD_IDX] == subject or (
                subject == cfg.NO_FOCAL_SUBJECT and event[cfg.EVENT_SUBJECT_FIELD_IDX] == ""
            ):
                events.append(event)

        if not events:
            continue

        total_length = 0  # in seconds
        if observation[cfg.EVENTS]:
            total_length = observation[cfg.EVENTS][-1][0] - observation[cfg.EVENTS][0][0]  # last event time - first event time

        file_name_subject = str(pathlib.Path(file_name).parent / pathlib.Path(file_name).stem) + "_" + subject + ".dat"

        rows = ["FirstLineOfData"]  # to be completed
        rows.append("#-----------------------------------------------------------")
        rows.append(f"# Name: {pathlib.Path(file_name_subject).name}")
        rows.append("# Format: Focal Data File 1.0")
        rows.append(f"# Updated: {dt.datetime.now().isoformat()}")
        rows.append("#-----------------------------------------------------------")
        rows.append("")
        rows.append(f"FocalMasterFile={pathlib.Path(file_name_subject).with_suffix('.fmf')}")
        rows.append("")

        rows.append(f"# Observation started: {observation['date']}")
        try:
            start_time = dt.datetime.strptime(observation["date"], "%Y-%m-%dT%H:%M:%S")
        except ValueError:
            start_time = dt.datetime(1970, 1, 1, 0, 0)
        start_time_epoch = int((start_time - dt.datetime(1970, 1, 1, 0, 0)).total_seconds() * 1000)
        rows.append(f"StartTime={start_time_epoch}")

        stop_time = (start_time + dt.timedelta(seconds=float(total_length))).isoformat()
        stop_time_epoch = int(start_time_epoch + float(total_length) * 1000)

        rows.append(f"# Observation stopped: {stop_time}")
        rows.append(f"StopTime={stop_time_epoch}")

        rows.extend([""] * 3)
        rows.append("#BEGIN DATA")
        rows[0] = f"FirstLineOfData={len(rows) + 1}"

        all_observed_behaviors = []
        mem_number_of_state_events = {}
        for event in events:
            behav_code = event[cfg.EVENT_BEHAVIOR_FIELD_IDX]

            try:
                behavior_key = [ethogram[k][cfg.BEHAVIOR_KEY] for k in ethogram if ethogram[k][cfg.BEHAVIOR_CODE] == behav_code][0]
            except Exception:
                # coded behavior not defined in ethogram
                continue
            if [ethogram[k][cfg.TYPE] for k in ethogram if ethogram[k][cfg.BEHAVIOR_CODE] == behav_code] in [
                [cfg.STATE_EVENT],
                [cfg.STATE_EVENT_WITH_CODING_MAP],
            ]:
                if behav_code in mem_number_of_state_events:
                    mem_number_of_state_events[behav_code] += 1
                else:
                    mem_number_of_state_events[behav_code] = 1
                # skip the STOP event in case of STATE
                if mem_number_of_state_events[behav_code] % 2 == 0:
                    continue

            rows.append(f"{int(event[cfg.EVENT_TIME_FIELD_IDX] * 1000)}, {behavior_key}")
            if (event[cfg.EVENT_BEHAVIOR_FIELD_IDX], behavior_key) not in all_observed_behaviors:
                all_observed_behaviors.append((event[cfg.EVENT_BEHAVIOR_FIELD_IDX], behavior_key))

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
                cfg.programName,
                (f"The {fmf_file_path} file already exists.<br>What do you want to do?"),
                [cfg.OVERWRITE, "Skip file creation", cfg.CANCEL],
            )

            if fmf_creation_answer == cfg.CANCEL:
                return True, ""

        rows = []
        rows.append("#-----------------------------------------------------------")
        rows.append(f"# Name: {pathlib.Path(file_name_subject).with_suffix('.fmf').name}")
        rows.append("# Format: Focal Master File 1.0")
        rows.append(f"# Updated: {dt.datetime.now().isoformat()}")
        rows.append("#-----------------------------------------------------------")
        for behav, key in all_observed_behaviors:
            rows.append(f"Behaviour.name.{key}={behav}")
            behav_description = [ethogram[k][cfg.DESCRIPTION] for k in ethogram if ethogram[k][cfg.BEHAVIOR_CODE] == behav][0]
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

        if fmf_creation_answer == cfg.OVERWRITE or fmf_creation_answer == "":
            try:
                with open(fmf_file_path, "w") as f_out:
                    f_out.write("\n".join(rows))
            except Exception:
                return False, f"File FMF not created: {sys.exc_info()[1]}"

        # create FAF file
        faf_file_path = pathlib.Path(file_name_subject).with_suffix(".faf")
        faf_creation_answer = ""
        if faf_file_path.exists():
            faf_creation_answer = dialog.MessageDialog(
                cfg.programName,
                (f"The {faf_file_path} file already exists.<br>What do you want to do?"),
                [cfg.OVERWRITE, "Skip file creation", cfg.CANCEL],
            )
            if faf_creation_answer == cfg.CANCEL:
                return True, ""

        rows = []
        rows.append("#-----------------------------------------------------------")
        rows.append("# Name: {}".format(pathlib.Path(file_name_subject).with_suffix(".faf").name))
        rows.append("# Format: Focal Analysis Master File 1.0")
        rows.append("# Updated: {}".format(dt.datetime.now().isoformat()))
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

        for behav, key in all_observed_behaviors:
            rows.append(f"Behavior.isModified.{key}=false")
            rows.append(f"Behavior.isSubtracted.{key}=false")
            rows.append(f"Behavior.isIgnored.{key}=false")
            rows.append(f"Behavior.isEventAnalyzed.{key}=false")
            rows.append(f"Behavior.switchesOff.{key}=")
            rows.append("")

        if faf_creation_answer == "" or faf_creation_answer == cfg.OVERWRITE:
            try:
                with open(pathlib.Path(file_name_subject).with_suffix(".faf"), "w") as f_out:
                    f_out.write("\n".join(rows))
            except Exception:
                return False, f"File FAF not created: {sys.exc_info()[1]}"

    return True, ""


def export_tabular_events(
    pj: dict, parameters: dict, obs_id: str, observation: dict, ethogram: dict, file_name: str, output_format: str
) -> Tuple[bool, str]:
    """
    export events for one observation (obs_id)

    Args:
        parameters (dict): subjects, behaviors
        obs_id (str): observation id
        observation (dict): observation
        ethogram (dict): ethogram of project
        file_name (str): file name for exporting events
        output_format (str): output for exporting events

    Returns:
        bool: result: True if OK else False
        str: error message
    """

    logging.debug(f"function: export tabular events for {obs_id}")
    logging.debug(f"parameters: {parameters}")

    interval = parameters["time"]

    start_coding, end_coding, coding_duration = observation_operations.coding_time(pj[cfg.OBSERVATIONS], [obs_id])
    start_interval, end_interval = observation_operations.time_intervals_range(pj[cfg.OBSERVATIONS], [obs_id])

    if interval == cfg.TIME_EVENTS:
        min_time = start_coding
        max_time = end_coding

    if interval == cfg.TIME_FULL_OBS:
        if observation[cfg.TYPE] == cfg.MEDIA:
            max_media_duration, _ = observation_operations.media_duration(pj[cfg.OBSERVATIONS], [obs_id])
            min_time = dec("0")
            max_time = max_media_duration
            coding_duration = max_media_duration

        if observation[cfg.TYPE] in (cfg.LIVE, cfg.IMAGES):
            min_time = start_coding
            max_time = end_coding

    if interval == cfg.TIME_ARBITRARY_INTERVAL:
        min_time = parameters[cfg.START_TIME]
        max_time = parameters[cfg.END_TIME]

    if interval == cfg.TIME_OBS_INTERVAL:
        max_media_duration, _ = observation_operations.media_duration(pj[cfg.OBSERVATIONS], [obs_id])
        min_time = start_interval
        # Use max media duration for max time if no interval is defined (=0)
        max_time = end_interval if end_interval != 0 else max_media_duration

    logging.debug(f"min_time: {min_time}  max_time: {max_time}")

    events_with_status = project_functions.events_start_stop(ethogram, observation[cfg.EVENTS], observation[cfg.TYPE])

    # check max number of modifiers
    max_modifiers = 0
    for event in events_with_status:
        if not math.isnan(min_time) and not math.isnan(max_time):  # obs not from pictures
            if min_time <= event[cfg.EVENT_TIME_FIELD_IDX] <= max_time:
                if event[cfg.EVENT_MODIFIER_FIELD_IDX]:
                    max_modifiers = max(max_modifiers, len(event[cfg.EVENT_MODIFIER_FIELD_IDX].split("|")))
        else:
            if event[cfg.EVENT_MODIFIER_FIELD_IDX]:
                max_modifiers = max(max_modifiers, len(event[cfg.EVENT_MODIFIER_FIELD_IDX].split("|")))

    # media file number
    media_nb = util.count_media_file(observation[cfg.FILE])

    rows: list = []

    # fields and type
    fields_type: dict = {
        "Observation id": str,
        "Observation date": dt.datetime,
        "Description": str,
        "Observation duration": float,
        "Observation type": str,
        "Source": str,
        "Time offset (s)": str,
    }
    if media_nb == 1:
        fields_type["Media duration (s)"] = float
        fields_type["FPS"] = float
    else:
        fields_type["Media duration (s)"] = str
        fields_type["FPS"] = str

    # independent variables
    if cfg.INDEPENDENT_VARIABLES in observation:
        for variable in observation[cfg.INDEPENDENT_VARIABLES]:
            # TODO check variable type
            fields_type[variable] = str

    fields_type.update({"Subject": str, "Behavior": str, "Behavioral category": str})

    # modifiers
    for idx in range(max_modifiers):
        fields_type[f"Modifier #{idx + 1}"] = str

    fields_type.update(
        {
            "Behavior type": str,
            "Time": float,
            "Media file name": str,
            "Image index": float,  # add image index and image file path to header
            "Image file path": str,
            "Comment": str,
        }
    )

    # add header
    rows.append(list(fields_type.keys()))

    behavioral_category = project_functions.behavior_category(ethogram)

    duration1 = []  # in seconds
    if observation[cfg.TYPE] == cfg.MEDIA:
        try:
            for mediaFile in observation[cfg.FILE][cfg.PLAYER1]:
                duration1.append(observation[cfg.MEDIA_INFO][cfg.LENGTH][mediaFile])
        except KeyError:
            pass

    for event in events_with_status:
        if (not math.isnan(min_time)) and not (min_time <= event[cfg.EVENT_TIME_FIELD_IDX] <= max_time):
            continue
        if (
            (event[cfg.EVENT_SUBJECT_FIELD_IDX] in parameters[cfg.SELECTED_SUBJECTS])
            or (event[cfg.EVENT_SUBJECT_FIELD_IDX] == "" and cfg.NO_FOCAL_SUBJECT in parameters[cfg.SELECTED_SUBJECTS])
        ) and (event[cfg.EVENT_BEHAVIOR_FIELD_IDX] in parameters[cfg.SELECTED_BEHAVIORS]):
            fields: list = []
            fields.append(obs_id)
            fields.append(observation.get("date", "").replace("T", " "))
            fields.append(util.eol2space(observation.get(cfg.DESCRIPTION, "")))
            # total length
            fields.append(coding_duration if not coding_duration.is_nan() else cfg.NA)

            if observation[cfg.TYPE] == cfg.MEDIA:
                fields.append("Media file(s)")

                media_file_str, fps_str, media_durations_str = "", "", ""
                for player in observation[cfg.FILE]:
                    media_file_lst, fps_lst, media_durations_lst = [], [], []
                    if observation[cfg.FILE][player]:
                        for media_file in observation[cfg.FILE][player]:
                            media_file_lst.append(media_file)
                            fps_lst.append(f"{observation[cfg.MEDIA_INFO][cfg.FPS].get(media_file, cfg.NA):.3f}")
                            media_durations_lst.append(f"{observation[cfg.MEDIA_INFO][cfg.LENGTH].get(media_file, cfg.NA):.3f}")
                        if player > "1":
                            media_file_str += "|"
                            fps_str += "|"
                            media_durations_str += "|"
                        media_file_str += f"player #{player}:" + ";".join(media_file_lst)
                        fps_str += ";".join(fps_lst)
                        media_durations_str += ";".join(media_durations_lst)

                """
                # number of players
                n_players = len([x for x in observation[cfg.FILE] if observation[cfg.FILE][x]])
                media_file_str, fps_str = "", ""
                for player in observation[cfg.FILE]:
                    if observation[cfg.FILE][player]:
                        if media_file_str:
                            media_file_str += " "
                        if fps_str:
                            fps_str += " "
                        if n_players > 1:
                            media_file_str += f"player #{player}: "
                            fps_str += f"player #{player}: "
                        media_list, fps_list = [], []
                        for media_file in observation[cfg.FILE][player]:
                            media_list.append(media_file)
                            fps_list.append(f"{observation[cfg.MEDIA_INFO][cfg.FPS].get(media_file, cfg.NA):.3f}")
                        media_file_str += ";".join(media_list)
                        fps_str += ";".join(fps_list)
                """

                fields.append(media_file_str)

            elif observation[cfg.TYPE] == cfg.LIVE:
                fields.append("Live observation")
                fields.append(cfg.NA)
                media_durations_str = cfg.NA
                fps_str = cfg.NA

            elif observation[cfg.TYPE] == cfg.IMAGES:
                fields.append("From directories of images")
                dir_list = []
                for dir in observation[cfg.DIRECTORIES_LIST]:
                    dir_list.append(dir)
                fields.append(";".join(dir_list))
                media_durations_str = cfg.NA
                fps_str = cfg.NA

            else:
                fields.append("")

            # time offset
            fields.append(observation[cfg.TIME_OFFSET])

            # media duration
            fields.append(media_durations_str)

            # FPS
            fields.append(fps_str)

            # indep var
            if cfg.INDEPENDENT_VARIABLES in observation:
                for variable in observation[cfg.INDEPENDENT_VARIABLES]:
                    fields.append(observation[cfg.INDEPENDENT_VARIABLES][variable])

            fields.append(event[cfg.PJ_OBS_FIELDS[observation[cfg.TYPE]][cfg.SUBJECT]])
            fields.append(event[cfg.PJ_OBS_FIELDS[observation[cfg.TYPE]][cfg.BEHAVIOR_CODE]])

            # behavioral category
            try:
                behav_category = behavioral_category[event[cfg.PJ_OBS_FIELDS[observation[cfg.TYPE]][cfg.BEHAVIOR_CODE]]]
            except Exception:
                behav_category = ""
            fields.append(behav_category)

            # modifiers
            if max_modifiers:
                modifiers = event[cfg.PJ_OBS_FIELDS[observation[cfg.TYPE]][cfg.MODIFIER]].split("|")
                while len(modifiers) < max_modifiers:
                    modifiers.append("")

                for m in modifiers:
                    fields.append(m)

            # status (START/STOP)
            fields.append(event[-1])

            # time
            fields.append(util.convertTime(time_format=cfg.S, sec=event[cfg.EVENT_TIME_FIELD_IDX]))

            # check video file name containing the event
            if observation[cfg.TYPE] == cfg.MEDIA:
                video_file_name = observation_operations.event2media_file_name(observation, event[cfg.EVENT_TIME_FIELD_IDX])
                if video_file_name is None:
                    video_file_name = "Not found"

            elif observation[cfg.TYPE] in (cfg.LIVE, cfg.IMAGES):
                video_file_name = cfg.NA
            fields.append(video_file_name)

            # image file index
            if observation[cfg.TYPE] == cfg.IMAGES:
                fields.append(event[cfg.PJ_OBS_FIELDS[cfg.IMAGES][cfg.IMAGE_INDEX]])  # image file index
            elif observation[cfg.TYPE] == cfg.MEDIA:
                frame_idx = event_operations.read_event_field(event, cfg.MEDIA, cfg.FRAME_INDEX)
                fields.append(frame_idx)  # frame index
            elif observation[cfg.TYPE] == cfg.LIVE:
                fields.append(cfg.NA)
            else:
                fields.append("")

            # image file path
            if observation[cfg.TYPE] == cfg.IMAGES:
                fields.append(event[cfg.PJ_OBS_FIELDS[cfg.IMAGES][cfg.IMAGE_PATH]])  # image file path
            elif observation[cfg.TYPE] in (cfg.LIVE, cfg.MEDIA):
                fields.append(cfg.NA)
            else:
                fields.append("")

            # comment
            fields.append(event[cfg.PJ_OBS_FIELDS[observation[cfg.TYPE]][cfg.COMMENT]].replace(os.linesep, " "))

            rows.append(fields)

    max_len = max([len(r) for r in rows])
    data = tablib.Dataset()

    data.title = util.safe_xl_worksheet_title(obs_id, output_format)

    for row in rows:
        data.append(util.complete(row, max_len))

    r, msg = dataset_write(data, file_name, output_format, dtype=fields_type)

    return r, msg


def dataset_write(dataset: tablib.Dataset, file_name: str, output_format: str, dtype: dict = {}) -> tuple:  # -> tuple[bool, str]:
    """
    write a tablib dataset with aggregated events or tabular events to file in specified format (output_format)

    Args:
        dataset (tablib.dataset): dataset to write
        file_name (str): file name
        output_format (str): format of output
        dtype (dict): type of field

    Returns:
        bool: result. True if OK else False
        str: error message
    """

    logging.debug("function: dataset_write")

    try:
        if output_format in (cfg.PANDAS_DF_EXT, cfg.RDS_EXT):
            # build pandas dataframe from the tsv export of tablib dataset
            date_type: list = []
            for field_name in dtype:
                if dtype[field_name] == dt.datetime:
                    date_type.append(field_name)
            # delete data type from dtype
            for field_name in date_type:
                del dtype[field_name]

            df = pd.read_csv(
                StringIO(dataset.export(cfg.TSV_EXT)),
                sep="\t",
                dtype=dtype,
                parse_dates=date_type,
            )

            if output_format == cfg.PANDAS_DF_EXT:
                df.to_pickle(file_name)

            if output_format == cfg.RDS_EXT and flag_pyreadr_loaded:
                pyreadr.write_rds(file_name, df)

            return True, ""

        if output_format in (cfg.CSV_EXT, cfg.TSV_EXT, cfg.HTML_EXT):
            with open(file_name, "wb") as f:
                f.write(str.encode(dataset.export(output_format)))
            return True, ""

        if output_format in (cfg.ODS_EXT, cfg.XLS_EXT, cfg.XLSX_EXT):
            dataset.title = util.safe_xl_worksheet_title(dataset.title, output_format)

            with open(file_name, "wb") as f:
                f.write(dataset.export(output_format))
            return True, ""

        return False, f"Format {output_format} not found"

    except Exception:
        return False, str(sys.exc_info()[1])


def export_aggregated_events(pj: dict, parameters: dict, obsId: str, force_number_modifiers: int = 0) -> Tuple[tablib.Dataset, int]:
    """
    export aggregated events of one observation

    Args:
        pj (dict): BORIS project
        parameters (dict): subjects, behaviors
        obsId (str): observation id
        force_number_modifiers (int): force the number of modifiers to return

    Returns:
        tablib.Dataset:
        int: Maximum number of modifiers

    """
    logging.debug(f"function: export aggregated events {obsId} parameters: {parameters} ")

    observation = pj[cfg.OBSERVATIONS][obsId]
    interval = parameters["time"]

    data = tablib.Dataset()

    start_coding, end_coding, coding_duration = observation_operations.coding_time(pj[cfg.OBSERVATIONS], [obsId])
    start_interval, end_interval = observation_operations.time_intervals_range(pj[cfg.OBSERVATIONS], [obsId])

    if start_coding is None and end_coding is None:  # no events
        return data, 0

    if interval == cfg.TIME_EVENTS:
        min_time = float(start_coding)
        max_time = float(end_coding)

    if interval == cfg.TIME_FULL_OBS:
        if observation[cfg.TYPE] == cfg.MEDIA:
            max_media_duration, _ = observation_operations.media_duration(pj[cfg.OBSERVATIONS], [obsId])
            min_time = float(0)
            max_time = float(max_media_duration)
            coding_duration = max_media_duration
        if observation[cfg.TYPE] in (cfg.LIVE, cfg.IMAGES):
            min_time = float(start_coding)
            max_time = float(end_coding)

    if interval == cfg.TIME_ARBITRARY_INTERVAL:
        min_time = float(parameters[cfg.START_TIME])
        max_time = float(parameters[cfg.END_TIME])

    if interval == cfg.TIME_OBS_INTERVAL:
        max_media_duration, _ = observation_operations.media_duration(pj[cfg.OBSERVATIONS], [obsId])
        min_time = float(start_interval)
        # Use max media duration for max time if no interval is defined (=0)
        max_time = float(end_interval) if end_interval != 0 else float(max_media_duration)

    logging.debug(f"min_time: {min_time}  max_time: {max_time}")

    # obs description
    obs_description = util.eol2space(observation[cfg.DESCRIPTION])

    """
    obs_length = observation_operations.observation_total_length(pj[cfg.OBSERVATIONS][obsId])
    logging.debug(f"obs_length: {obs_length}")
    """

    _, _, connector = db_functions.load_aggregated_events_in_db(
        pj, parameters[cfg.SELECTED_SUBJECTS], [obsId], parameters[cfg.SELECTED_BEHAVIORS]
    )
    if connector is None:
        logging.critical("error when loading aggregated events in DB")
        return data, 0

    cursor = connector.cursor()

    # adapt start and stop to the selected time interval
    if not math.isnan(min_time) and not math.isnan(max_time):  # obs with timestamp
        # delete events outside time interval
        cursor.execute(
            "DELETE FROM aggregated_events WHERE observation = ? AND (start < ? AND stop < ?) OR (start > ? AND stop > ?)",
            (
                obsId,
                min_time,
                min_time,
                max_time,
                max_time,
            ),
        )

        cursor.execute(
            "UPDATE aggregated_events SET start = ? WHERE observation = ? AND start < ? AND stop BETWEEN ? AND ?",
            (
                min_time,
                obsId,
                min_time,
                min_time,
                max_time,
            ),
        )
        cursor.execute(
            "UPDATE aggregated_events SET stop = ? WHERE observation = ? AND stop > ? AND start BETWEEN ? AND ?",
            (
                max_time,
                obsId,
                max_time,
                min_time,
                max_time,
            ),
        )

        cursor.execute(
            "UPDATE aggregated_events SET start = ?, stop = ? WHERE observation = ? AND start < ? AND stop > ?",
            (
                min_time,
                max_time,
                obsId,
                min_time,
                max_time,
            ),
        )

    behavioral_category = project_functions.behavior_category(pj[cfg.ETHOGRAM])

    cursor.execute("SELECT DISTINCT modifiers FROM aggregated_events")

    if not force_number_modifiers:
        max_modifiers: int = 0
        for row in cursor.fetchall():
            if row["modifiers"]:
                max_modifiers = max(max_modifiers, row["modifiers"].count("|") + 1)
    else:
        max_modifiers = force_number_modifiers

    for subject in parameters[cfg.SELECTED_SUBJECTS]:
        # calculate observation duration by subject (by obs)
        cursor.execute(("SELECT SUM(stop - start) AS duration FROM aggregated_events WHERE subject = ? "), (subject,))
        duration_by_subject_by_obs = cursor.fetchone()["duration"]
        if duration_by_subject_by_obs is not None:
            duration_by_subject_by_obs = round(duration_by_subject_by_obs, 3)

        for behavior in parameters[cfg.SELECTED_BEHAVIORS]:
            cursor.execute(
                "SELECT DISTINCT modifiers FROM aggregated_events WHERE subject=? AND behavior=? ORDER BY modifiers",
                (
                    subject,
                    behavior,
                ),
            )

            rows_distinct_modifiers = list(x[0] for x in cursor.fetchall())

            for distinct_modifiers in rows_distinct_modifiers:
                cursor.execute(
                    (
                        "SELECT start, stop, type, modifiers, comment, comment_stop, "
                        "image_index_start, image_index_stop, image_path_start, image_path_stop "
                        "FROM aggregated_events "
                        "WHERE subject = ? AND behavior = ? AND modifiers = ? ORDER BY start, image_index_start"
                    ),
                    (subject, behavior, distinct_modifiers),
                )

                for row in cursor.fetchall():
                    media_file_name = cfg.NA

                    if observation[cfg.TYPE] == cfg.MEDIA:
                        observation_type = "Media file"

                        media_file_name = observation_operations.event2media_file_name(observation, row["start"])
                        if media_file_name is None:
                            media_file_name = "Not found"

                        media_file_str, fps_str, media_durations_str = "", "", ""

                        for player in observation[cfg.FILE]:
                            media_file_lst, fps_lst, media_durations_lst = [], [], []
                            if observation[cfg.FILE][player]:
                                for media_file in observation[cfg.FILE][player]:
                                    media_file_lst.append(media_file)
                                    fps_lst.append(f"{observation[cfg.MEDIA_INFO][cfg.FPS].get(media_file, cfg.NA):.3f}")
                                    media_durations_lst.append(f"{observation[cfg.MEDIA_INFO][cfg.LENGTH].get(media_file, cfg.NA):.3f}")
                                if player > "1":
                                    media_file_str += "|"
                                    fps_str += "|"
                                    media_durations_str += "|"
                                media_file_str += f"player #{player}:" + ";".join(media_file_lst)
                                fps_str += ";".join(fps_lst)
                                media_durations_str += ";".join(media_durations_lst)

                    if observation[cfg.TYPE] == cfg.LIVE:
                        observation_type = "Live observation"
                        media_file_str = cfg.NA
                        fps_str = cfg.NA
                        media_durations_str = cfg.NA

                    if observation[cfg.TYPE] == cfg.IMAGES:
                        observation_type = "From pictures"
                        media_file_str = ""
                        for dir in observation[cfg.DIRECTORIES_LIST]:
                            media_file_str += f"{dir}; "
                        fps_str = cfg.NA
                        # TODO: number of pictures in each directory
                        media_durations_str = cfg.NA

                    row_data = []

                    row_data.extend(
                        [
                            obsId,
                            observation["date"].replace("T", " "),
                            obs_description,
                            observation_type,
                            media_file_str,
                            pj[cfg.OBSERVATIONS][obsId][cfg.TIME_OFFSET],
                            f"{coding_duration:.3f}" if not coding_duration.is_nan() else cfg.NA,
                            media_durations_str,
                            fps_str,
                        ]
                    )

                    # independent variables
                    if cfg.INDEPENDENT_VARIABLES in pj:
                        for idx_var in util.sorted_keys(pj[cfg.INDEPENDENT_VARIABLES]):
                            if pj[cfg.INDEPENDENT_VARIABLES][idx_var]["label"] in observation[cfg.INDEPENDENT_VARIABLES]:
                                var_value = observation[cfg.INDEPENDENT_VARIABLES][pj[cfg.INDEPENDENT_VARIABLES][idx_var]["label"]]
                                if pj[cfg.INDEPENDENT_VARIABLES][idx_var]["type"] == "timestamp":
                                    var_value = var_value.replace("T", " ")

                                row_data.append(var_value)
                            else:
                                row_data.append("")

                    row_data.extend(
                        [
                            subject,
                            duration_by_subject_by_obs,
                            behavior,
                            behavioral_category[behavior] if behavioral_category[behavior] else "Not defined",
                        ]
                    )

                    # modifiers
                    if max_modifiers:
                        modifiers = row["modifiers"].split("|")
                        while len(modifiers) < max_modifiers:
                            modifiers.append("")
                        for modifier in modifiers:
                            row_data.append(modifier)

                    if row["type"] == cfg.POINT:
                        row_data.extend(
                            [
                                cfg.POINT,
                                f"{row['start']:.3f}" if row["start"] is not None else cfg.NA,  # start
                                f"{row['stop']:.3f}" if row["stop"] is not None else cfg.NA,  # stop
                                cfg.NA,  # duration
                                media_file_name,  # Media file name
                            ]
                        )

                    if row["type"] == cfg.STATE:
                        row_data.extend(
                            [
                                cfg.STATE,
                                f"{row['start']:.3f}" if row["start"] is not None else cfg.NA,
                                f"{row['stop']:.3f}" if row["stop"] is not None else cfg.NA,
                                # duration
                                f"{row['stop'] - row['start']:.3f}" if (row["stop"] is not None) and (row["start"] is not None) else cfg.NA,
                                media_file_name,  # Media file name
                            ]
                        )

                    row_data.extend(
                        [
                            row["image_index_start"],
                            row["image_index_stop"],
                            row["image_path_start"],
                            row["image_path_stop"],
                            row["comment"],
                            row["comment_stop"] if (row["type"] == cfg.STATE) else "",
                        ]
                    )

                    data.append(row_data)

    return data, max_modifiers


def events_to_behavioral_sequences(pj, obs_id: str, subj: str, parameters: dict, behav_seq_separator: str) -> str:
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

    out: str = ""
    current_states: list = []
    # add status (POINT, START, STOP) to event
    events_with_status = project_functions.events_start_stop(
        pj[cfg.ETHOGRAM], pj[cfg.OBSERVATIONS][obs_id][cfg.EVENTS], pj[cfg.OBSERVATIONS][obs_id][cfg.TYPE]
    )

    for event in events_with_status:
        # check if event in selected behaviors

        if event[cfg.EVENT_BEHAVIOR_FIELD_IDX] not in parameters[cfg.SELECTED_BEHAVIORS]:
            continue

        if event[cfg.EVENT_SUBJECT_FIELD_IDX] == subj or (subj == cfg.NO_FOCAL_SUBJECT and event[cfg.EVENT_SUBJECT_FIELD_IDX] == ""):
            # if event[cfg.EVENT_STATUS_FIELD_IDX] == cfg.POINT:
            if event[-1] == cfg.POINT:  # status is last element
                if current_states:
                    out += "+".join(current_states) + "+" + event[cfg.EVENT_BEHAVIOR_FIELD_IDX]
                else:
                    out += event[cfg.EVENT_BEHAVIOR_FIELD_IDX]

                if parameters[cfg.INCLUDE_MODIFIERS]:
                    out += "&" + event[cfg.EVENT_MODIFIER_FIELD_IDX].replace("|", "+")

                out += behav_seq_separator

            # if event[cfg.EVENT_STATUS_FIELD_IDX] == cfg.START:
            if event[-1] == cfg.START:  # status is last element
                if parameters[cfg.INCLUDE_MODIFIERS]:
                    current_states.append(
                        (
                            f"{event[cfg.EVENT_BEHAVIOR_FIELD_IDX]}"
                            f"{'&' if event[cfg.EVENT_MODIFIER_FIELD_IDX] else ''}"
                            f"{event[cfg.EVENT_MODIFIER_FIELD_IDX].replace('|', ';')}"
                        )
                    )
                else:
                    current_states.append(event[cfg.EVENT_BEHAVIOR_FIELD_IDX])

                out += "+".join(sorted(current_states))

                out += behav_seq_separator

            # if event[cfg.EVENT_STATUS_FIELD_IDX] == cfg.STOP:
            if event[-1] == cfg.STOP:
                if parameters[cfg.INCLUDE_MODIFIERS]:
                    behav_modif = (
                        f"{event[cfg.EVENT_BEHAVIOR_FIELD_IDX]}"
                        f"{'&' if event[cfg.EVENT_MODIFIER_FIELD_IDX] else ''}"
                        f"{event[cfg.EVENT_MODIFIER_FIELD_IDX].replace('|', ';')}"
                    )
                else:
                    behav_modif = event[cfg.EVENT_BEHAVIOR_FIELD_IDX]
                if behav_modif in current_states:
                    current_states.remove(behav_modif)

                if current_states:
                    out += "+".join(sorted(current_states))

                    out += behav_seq_separator

    # remove last separator (if separator not empty)
    if behav_seq_separator:
        out = out[0 : -len(behav_seq_separator)]

    return out


def events_to_behavioral_sequences_all_subj(pj, obs_id: str, subjects_list: list, parameters: dict, behav_seq_separator: str) -> str:
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
    current_states = {i: [] for i in subjects_list}
    events_with_status = project_functions.events_start_stop(
        pj[cfg.ETHOGRAM], pj[cfg.OBSERVATIONS][obs_id][cfg.EVENTS], pj[cfg.OBSERVATIONS][obs_id][cfg.TYPE]
    )

    for event in events_with_status:
        # check if event in selected behaviors
        if event[cfg.EVENT_BEHAVIOR_FIELD_IDX] not in parameters[cfg.SELECTED_BEHAVIORS]:
            continue

        if (event[cfg.EVENT_SUBJECT_FIELD_IDX] in subjects_list) or (
            event[cfg.EVENT_SUBJECT_FIELD_IDX] == "" and cfg.NO_FOCAL_SUBJECT in subjects_list
        ):
            subject = event[cfg.EVENT_SUBJECT_FIELD_IDX] if event[cfg.EVENT_SUBJECT_FIELD_IDX] else cfg.NO_FOCAL_SUBJECT

            if event[-1] == cfg.POINT:
                if current_states[subject]:
                    out += f"[{subject}]" + "+".join(current_states[subject]) + "+" + event[cfg.EVENT_BEHAVIOR_FIELD_IDX]
                else:
                    out += f"[{subject}]" + event[cfg.EVENT_BEHAVIOR_FIELD_IDX]

                if parameters[cfg.INCLUDE_MODIFIERS]:
                    out += "&" + event[cfg.EVENT_MODIFIER_FIELD_IDX].replace("|", "+")

                out += behav_seq_separator

            if event[-1] == cfg.START:
                if parameters[cfg.INCLUDE_MODIFIERS]:
                    current_states[subject].append(
                        (
                            f"{event[cfg.EVENT_BEHAVIOR_FIELD_IDX]}"
                            f"{'&' if event[cfg.EVENT_MODIFIER_FIELD_IDX] else ''}"
                            f"{event[cfg.EVENT_MODIFIER_FIELD_IDX].replace('|', ';')}"
                        )
                    )
                else:
                    current_states[subject].append(event[cfg.EVENT_BEHAVIOR_FIELD_IDX])

                out += f"[{subject}]" + "+".join(sorted(current_states[subject]))

                out += behav_seq_separator

            if event[-1] == cfg.STOP:
                if parameters[cfg.INCLUDE_MODIFIERS]:
                    behav_modif = (
                        f"{event[cfg.EVENT_BEHAVIOR_FIELD_IDX]}"
                        f"{'&' if event[cfg.EVENT_MODIFIER_FIELD_IDX] else ''}"
                        f"{event[cfg.EVENT_MODIFIER_FIELD_IDX].replace('|', ';')}"
                    )
                else:
                    behav_modif = event[cfg.EVENT_BEHAVIOR_FIELD_IDX]
                if behav_modif in current_states[subject]:
                    current_states[subject].remove(behav_modif)

                if current_states[subject]:
                    out += f"[{subject}]" + "+".join(sorted(current_states[subject]))

                    out += behav_seq_separator

    # remove last separator (if separator not empty)
    if behav_seq_separator:
        out = out[0 : -len(behav_seq_separator)]

    return out


def events_to_timed_behavioral_sequences(
    pj: dict, obs_id: str, subject: str, parameters: dict, precision: float, behav_seq_separator: str
) -> str:
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

    out: str = ""

    state_behaviors_codes = util.state_behavior_codes(pj[cfg.ETHOGRAM])
    delta = dec(str(round(precision, 3)))
    out = ""
    t = dec("0.000")

    current = []
    while t < pj[cfg.OBSERVATIONS][obs_id][cfg.EVENTS][-1][0]:
        """
        if out:
            out += behav_seq_separator
        """
        csbs = util.get_current_states_modifiers_by_subject(
            state_behaviors_codes,
            pj[cfg.OBSERVATIONS][obs_id][cfg.EVENTS],
            {"": {"name": subject}},
            t,
            include_modifiers=False,
        )[""]
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


def observation_to_behavioral_sequences(pj, selected_observations, parameters, behaviors_separator, separated_subjects, timed, file_name):
    try:
        with open(file_name, "w", encoding="utf-8") as out_file:
            for obs_id in selected_observations:
                # observation id
                out_file.write("\n" + f"# observation id: {obs_id}" + "\n")
                # observation description
                descr = pj[cfg.OBSERVATIONS][obs_id]["description"]
                if "\r\n" in descr:
                    descr = descr.replace("\r\n", "\n# ")
                elif "\r" in descr:
                    descr = descr.replace("\r", "\n# ")
                out_file.write(f"# observation description: {descr}\n\n")
                # media file name
                if pj[cfg.OBSERVATIONS][obs_id][cfg.TYPE] == cfg.MEDIA:
                    out_file.write(f"# Observation type: Media file{os.linesep}")
                    media_file_str = ""

                    for player in pj[cfg.OBSERVATIONS][obs_id][cfg.FILE]:
                        if pj[cfg.OBSERVATIONS][obs_id][cfg.FILE][player]:
                            media_file_str += f"player #{player}: "
                            # fps_str += f"player #{player}: "
                            for media_file in pj[cfg.OBSERVATIONS][obs_id][cfg.FILE][player]:
                                media_file_str += f"{media_file}; "
                                # fps_str += f"{pj[cfg.OBSERVATIONS][obs_id][cfg.MEDIA_INFO][cfg.FPS].get(media_file, cfg.NA):.3f}; "

                    out_file.write(f"# Media file path: {media_file_str}\n\n")
                if pj[cfg.OBSERVATIONS][obs_id][cfg.TYPE] == cfg.LIVE:
                    out_file.write(f"# Observation type: Live observation{os.linesep}{os.linesep}")

                if pj[cfg.OBSERVATIONS][obs_id][cfg.TYPE] == cfg.IMAGES:
                    out_file.write(f"# Observation type: From pictures{os.linesep}{os.linesep}")

                # independent variables
                if cfg.INDEPENDENT_VARIABLES in pj[cfg.OBSERVATIONS][obs_id]:
                    out_file.write("# Independent variables\n")

                    for variable in pj[cfg.OBSERVATIONS][obs_id][cfg.INDEPENDENT_VARIABLES]:
                        out_file.write(f"# {variable}: {pj[cfg.OBSERVATIONS][obs_id][cfg.INDEPENDENT_VARIABLES][variable]}\n")
                out_file.write("\n")

                # one sequence for all subjects
                if not separated_subjects:
                    out = events_to_behavioral_sequences_all_subj(
                        pj, obs_id, parameters[cfg.SELECTED_SUBJECTS], parameters, behaviors_separator
                    )
                    if out:
                        out_file.write(out + "\n")

                # one sequence by subject
                if separated_subjects:
                    # selected subjects
                    for subject in parameters[cfg.SELECTED_SUBJECTS]:
                        out_file.write(f"\n# {subject if subject else cfg.NO_FOCAL_SUBJECT}:\n")

                        if not timed:
                            out = events_to_behavioral_sequences(pj, obs_id, subject, parameters, behaviors_separator)

                        if timed:
                            out = events_to_timed_behavioral_sequences(pj, obs_id, subject, parameters, 0.001, behaviors_separator)

                        if out:
                            out_file.write(out + "\n")

            return True, ""

    except Exception:
        error_type, error_file_name, error_lineno = util.error_info(sys.exc_info())
        return False, f"{error_type} {error_file_name} {error_lineno}"
