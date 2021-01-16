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

import boris.dialog as dialog
import logging
import math
import statistics
import sys
import time
from decimal import Decimal as dec

import tablib
from boris import portion as I

from boris import db_functions, project_functions, utilities
from boris.config import *


def default_value(ethogram, behav, param):
    """
    return value for duration in case of point event
    """
    default_value_ = 0
    if (project_functions.event_type(behav, ethogram) == "POINT EVENT"
            and param in ["duration"]):
        default_value_ = "-"
    return default_value_


def init_behav_modif(ethogram, selected_subjects, distinct_behav_modif, include_modifiers, parameters):
    """
    initialize dictionary with subject, behaviors and modifiers
    """
    behaviors = {}
    for subj in selected_subjects:
        behaviors[subj] = {}
        for behav_modif in distinct_behav_modif:

            behav, modif = behav_modif
            behav_modif_str = "|".join(behav_modif) if modif else behav

            if behav_modif_str not in behaviors[subj]:
                behaviors[subj][behav_modif_str] = {}

            for param in parameters:
                behaviors[subj][behav_modif_str][param[0]] = default_value(ethogram, behav_modif_str, param[0])

    return behaviors


def init_behav_modif_bin(ethogram, selected_subjects, distinct_behav_modif, include_modifiers, parameters):
    """
    initialize dictionary with subject, behaviors and modifiers
    """
    behaviors = {}
    for subj in selected_subjects:
        behaviors[subj] = {}
        for behav_modif in distinct_behav_modif:

            #behav, modif = behav_modif
            #behav_modif_str = "|".join(behav_modif) if modif else behav
            behav_modif_str = behav_modif


            if behav_modif_str not in behaviors[subj]:
                behaviors[subj][behav_modif_str] = {}

            for param in parameters:
                behaviors[subj][behav_modif_str][param[0]] = default_value(ethogram, behav_modif_str, param[0])

    return behaviors


class StdevFunc:
    """
    class to enable std dev function in SQL
    """
    def __init__(self):
        self.M = 0.0
        self.S = 0.0
        self.k = 1

    def step(self, value):
        if value is None:
            return
        tM = self.M
        self.M += (value - tM) / self.k
        self.S += (value - tM) * (value - self.M)
        self.k += 1

    def finalize(self):
        if self.k < 3:
            return None
        return math.sqrt(self.S / (self.k - 2))


def synthetic_time_budget_bin(pj: dict,
                              selected_observations: list,
                              parameters_obs: dict
                              ):
    """
    create a synthetic time budget divised in time bin

    Args:
        pj (dict): project dictionary
        selected_observations (list): list of observations to include in time budget
        parameters_obs (dict):

    Returns:
        bool: True if everything OK
        str: message
        tablib.Dataset: dataset containing synthetic time budget data
    """

    def interval_len(interval):
        if interval.empty:
            return dec(0)
        else:
            return sum([x.upper-x.lower for x in interval])

    def interval_number(interval):
        if interval.empty:
            return dec(0)
        else:
            return len(interval)

    def interval_mean(interval):
        if interval.empty:
            return dec(0)
        else:
            return sum([x.upper-x.lower for x in interval])/len(interval)

    def interval_std_dev(interval):
        if interval.empty:
            return "NA"
        else:
            try:
                return round(statistics.stdev([x.upper-x.lower for x in interval]), 3)
            except:
                return "NA"

    try:
        selected_subjects = parameters_obs[SELECTED_SUBJECTS]
        selected_behaviors = parameters_obs[SELECTED_BEHAVIORS]
        include_modifiers = parameters_obs[INCLUDE_MODIFIERS]
        time_interval = parameters_obs["time"]
        start_time = parameters_obs[START_TIME]
        end_time = parameters_obs[END_TIME]
        time_bin_size = dec(parameters_obs[TIME_BIN_SIZE])
        
        parameters = [["duration", "Total duration"],
                      ["number", "Number of occurrences"],
                      ["duration mean", "Duration mean"],
                      ["duration stdev", "Duration std dev"],
                      ["proportion of time", "Proportion of time"],
                      ]

        data_report = tablib.Dataset()
        data_report.title = "Synthetic time budget with time bin"

        distinct_behav_modif = []
        for obs_id in selected_observations:
            for event in pj[OBSERVATIONS][obs_id][EVENTS]:
                if include_modifiers:
                    if (event[EVENT_BEHAVIOR_FIELD_IDX], event[EVENT_MODIFIER_FIELD_IDX]) not in distinct_behav_modif:
                        distinct_behav_modif.append((event[EVENT_BEHAVIOR_FIELD_IDX], event[EVENT_MODIFIER_FIELD_IDX]))
                else:
                    if (event[EVENT_BEHAVIOR_FIELD_IDX], "") not in distinct_behav_modif:
                        distinct_behav_modif.append((event[EVENT_BEHAVIOR_FIELD_IDX], ""))

        distinct_behav_modif.sort()

        '''
        print("distinct_behav_modif", distinct_behav_modif)
        '''

        # add selected behaviors that are not observed
        for behav in selected_behaviors:
            if [x for x in distinct_behav_modif if x[0] == behav] == []:
                distinct_behav_modif.append([behav, ""])

        '''
        print("distinct_behav_modif with not observed behav", distinct_behav_modif)
        '''

        behaviors = init_behav_modif_bin(pj[ETHOGRAM],
                                     selected_subjects,
                                     distinct_behav_modif,
                                     include_modifiers,
                                     parameters)

        '''
        print("init behaviors", behaviors)

        print(f"selected subjects: {selected_subjects}")
        '''

        param_header = ["Observations id", "Total length (s)", "Time interval (s)"]
        subj_header, behav_header, modif_header = [""] * len(param_header), [""] * len(param_header), [""] * len(param_header)
        subj_header[1] = "Subjects:"
        behav_header[1] = "Behaviors:"
        modif_header[1] = "Modifiers:"

        for subj in selected_subjects:
            for behavior_modifiers in distinct_behav_modif:
                behavior, modifiers = behavior_modifiers
                behavior_modifiers_str = "|".join(behavior_modifiers) if modifiers else behavior
                for param in parameters:
                    subj_header.append(subj)
                    behav_header.append(behavior)
                    modif_header.append(modifiers)
                    param_header.append(param[1])

        data_report.append(subj_header)
        data_report.append(behav_header)
        if include_modifiers:
            data_report.append(modif_header)
        data_report.append(param_header)

        state_events_list = [pj[ETHOGRAM][x][BEHAVIOR_CODE] for x in pj[ETHOGRAM] if STATE in pj[ETHOGRAM][x][TYPE].upper()]
        # select time interval
        for obs_id in selected_observations:

            obs_length = project_functions.observation_total_length(pj[OBSERVATIONS][obs_id])

            if obs_length == -1:
                obs_length = 0
            if time_interval == TIME_FULL_OBS:
                min_time = dec(0)
                max_time = dec(obs_length)

            if time_interval == TIME_EVENTS:
                try:
                    min_time = dec(pj[OBSERVATIONS][obs_id][EVENTS][0][0])
                except Exception:
                    min_time = dec(0)
                try:
                    max_time = dec(pj[OBSERVATIONS][obs_id][EVENTS][-1][0])
                except Exception:
                    max_time = dec(obs_length)

            if time_interval == TIME_ARBITRARY_INTERVAL:
                min_time = dec(start_time)
                max_time = dec(end_time)

            #print("observation:", obs_id)
            events_interval = {}
            mem_events_interval = {}

            for event in pj[OBSERVATIONS][obs_id][EVENTS]:
                if event[EVENT_SUBJECT_FIELD_IDX] == "":
                    current_subject = NO_FOCAL_SUBJECT
                else:
                    current_subject = event[EVENT_SUBJECT_FIELD_IDX]

                if current_subject not in selected_subjects:
                    continue
                if current_subject not in events_interval:
                    events_interval[current_subject] = {}
                    mem_events_interval[current_subject] = {}

                if include_modifiers:
                    modif = event[EVENT_MODIFIER_FIELD_IDX]
                else:
                    modif = ""
                if (event[EVENT_BEHAVIOR_FIELD_IDX], modif) not in distinct_behav_modif:
                    continue

                if (event[EVENT_BEHAVIOR_FIELD_IDX], modif) not in events_interval[current_subject]:
                    events_interval[current_subject][(event[EVENT_BEHAVIOR_FIELD_IDX], modif)] = I.empty()
                    mem_events_interval[current_subject][(event[EVENT_BEHAVIOR_FIELD_IDX], modif)] = []

                if event[EVENT_BEHAVIOR_FIELD_IDX] in state_events_list:
                    mem_events_interval[current_subject][(event[EVENT_BEHAVIOR_FIELD_IDX], modif)].append(event[EVENT_TIME_FIELD_IDX])
                    if len(mem_events_interval[current_subject][(event[EVENT_BEHAVIOR_FIELD_IDX], modif)]) == 2:
                        events_interval[current_subject][(event[EVENT_BEHAVIOR_FIELD_IDX], modif)] |= \
                                I.closedopen(mem_events_interval[current_subject][(event[EVENT_BEHAVIOR_FIELD_IDX], modif)][0],
                                            mem_events_interval[current_subject][(event[EVENT_BEHAVIOR_FIELD_IDX], modif)][1])
                        mem_events_interval[current_subject][(event[EVENT_BEHAVIOR_FIELD_IDX],
                                                                             modif)] = []
                else:
                    events_interval[current_subject][(event[EVENT_BEHAVIOR_FIELD_IDX], modif)] |= I.singleton(event[EVENT_TIME_FIELD_IDX])

            '''
            print("\n\n events interval", events_interval)
            '''

            time_bin_start = min_time

            if time_bin_size:
                time_bin_end = time_bin_start + time_bin_size
                if time_bin_end > max_time:
                    time_bin_end = max_time
            else:
                time_bin_end = max_time
            '''
            print("time_bin_start type", type(time_bin_start))
            '''
            while True:

                for subject in events_interval:

                    # check behavior to exclude from total time
                    time_to_subtract = 0
                    if EXCLUDED_BEHAVIORS in parameters_obs:
                        for behav in events_interval[subject]:
                            if behav[0] in parameters_obs.get(EXCLUDED_BEHAVIORS, []):
                                interval_intersec = events_interval[subject][behav] & I.closed(time_bin_start, time_bin_end)
                                time_to_subtract += interval_len(interval_intersec)
                                
                    for behav in events_interval[subject]:

                        interval_intersec = events_interval[subject][behav] & I.closed(time_bin_start, time_bin_end)

                        dur = interval_len(interval_intersec)
                        nocc = interval_number(interval_intersec)
                        mean = interval_mean(interval_intersec)
                        '''
                        print(interval_intersec)
                        print(subject, behav)

                        print("duration", dur)
                        print("n. occ", nocc)
                        print("mean", mean)
                        print("std dev", interval_std_dev(interval_intersec))

                        print(time_bin_start)
                        print(time_bin_end)
                        print(time_to_subtract)
                        '''
                        if behav[0] in parameters_obs.get(EXCLUDED_BEHAVIORS, []):
                            proportion = dur / ((time_bin_end - time_bin_start))
                        else:
                            proportion = dur / ((time_bin_end - time_bin_start) - time_to_subtract)

                        behaviors[subject][behav]["duration"] = dur
                        behaviors[subject][behav]["number"] = nocc
                        behaviors[subject][behav]["duration mean"] = mean
                        behaviors[subject][behav]["duration stdev"] = interval_std_dev(interval_intersec)
                        behaviors[subject][behav]["proportion of time"] = f"{proportion:.3f}"

                columns = [obs_id, f"{max_time - min_time:0.3f}", f"{time_bin_start:.3f}-{time_bin_end:.3f}"]
                for subject in selected_subjects:
                    for behavior_modifiers in distinct_behav_modif:
                        behavior, modifiers = behavior_modifiers
                        #behavior_modifiers_str = "|".join(behavior_modifiers) if modifiers else behavior
                        behavior_modifiers_str = behavior_modifiers

                        for param in parameters:
                            columns.append(behaviors[subject][behavior_modifiers_str][param[0]])
                            #columns.append(behaviors[subject][behavior][param[0]])

                data_report.append(columns)

                time_bin_start = time_bin_end
                time_bin_end = time_bin_start + time_bin_size
                if time_bin_end > max_time:
                    time_bin_end = max_time
                #print(f"start: {time_bin_start} end: {time_bin_end}  max time: {max_time}")

                if time_bin_start == time_bin_end:
                    break

    except Exception:
        dialog.error_message("synthetic_time_budget_bin", sys.exc_info())
        return (False,
                tablib.Dataset())

    return True, data_report
    

def synthetic_time_budget(pj: dict,
                          selected_observations: list,
                          parameters_obs: dict):
    """
    create a synthetic time budget

    Args:
        pj (dict): project dictionary
        selected_observations (list): list of observations to include in time budget
        parameters_obs (dict):

    Returns:
        bool: True if everything OK
        str: message
        tablib.Dataset: dataset containing synthetic time budget data
    """
    try:
        selected_subjects = parameters_obs[SELECTED_SUBJECTS]
        selected_behaviors = parameters_obs[SELECTED_BEHAVIORS]
        include_modifiers = parameters_obs[INCLUDE_MODIFIERS]
        interval = parameters_obs["time"]
        start_time = parameters_obs["start time"]
        end_time = parameters_obs["end time"]

        parameters = [["duration", "Total duration"],
                      ["number", "Number of occurrences"],
                      ["duration mean", "Duration mean"],
                      ["duration stdev", "Duration std dev"],
                      ["proportion of time", "Proportion of time"],
                      ]

        data_report = tablib.Dataset()
        data_report.title = "Synthetic time budget"


        ok, msg, db_connector = db_functions.load_aggregated_events_in_db(pj,
                                                                          selected_subjects,
                                                                          selected_observations,
                                                                          selected_behaviors)

        if not ok:
            return False, msg, None

        db_connector.create_aggregate("stdev", 1, StdevFunc)
        cursor = db_connector.cursor()

        # modifiers
        if include_modifiers:
            cursor.execute("SELECT distinct behavior, modifiers FROM aggregated_events")
            distinct_behav_modif = [[rows["behavior"], rows["modifiers"]] for rows in cursor.fetchall()]
        else:
            cursor.execute("SELECT distinct behavior FROM aggregated_events")
            distinct_behav_modif = [[rows["behavior"], ""] for rows in cursor.fetchall()]

        # add selected behaviors that are not observed
        for behav in selected_behaviors:
            if [x for x in distinct_behav_modif if x[0] == behav] == []:
                distinct_behav_modif.append([behav, ""])

        behaviors = init_behav_modif(pj[ETHOGRAM],
                                     selected_subjects,
                                     distinct_behav_modif,
                                     include_modifiers,
                                     parameters)

        param_header = ["Observations id", "Total length (s)"]
        subj_header, behav_header, modif_header = [""] * len(param_header), [""] * len(param_header), [""] * len(param_header)
        subj_header[1] = "Subjects:"
        behav_header[1] = "Behaviors:"
        modif_header[1] = "Modifiers:"

        for subj in selected_subjects:
            for behavior_modifiers in distinct_behav_modif:
                behavior, modifiers = behavior_modifiers
                behavior_modifiers_str = "|".join(behavior_modifiers) if modifiers else behavior
                for param in parameters:
                    subj_header.append(subj)
                    behav_header.append(behavior)
                    modif_header.append(modifiers)
                    param_header.append(param[1])

        '''
        if parameters_obs["group observations"]:
            cursor.execute("UPDATE aggregated_events SET observation = 'all' " )
            #selected_observations = ["all"]
        '''

        data_report.append(subj_header)
        data_report.append(behav_header)
        if include_modifiers:
            data_report.append(modif_header)
        data_report.append(param_header)

        # select time interval
        for obs_id in selected_observations:

            ok, msg, db_connector = db_functions.load_aggregated_events_in_db(pj,
                                                                              selected_subjects,
                                                                              [obs_id],
                                                                              selected_behaviors)

            if not ok:
                return False, msg, None

            db_connector.create_aggregate("stdev", 1, StdevFunc)
            cursor = db_connector.cursor()

            # if modifiers not to be included set modifiers to ""
            if not include_modifiers:
                cursor.execute("UPDATE aggregated_events SET modifiers = ''")

            # time
            obs_length = project_functions.observation_total_length(pj[OBSERVATIONS][obs_id])
            if obs_length == -1:
                obs_length = 0

            if interval == TIME_FULL_OBS:
                min_time = float(0)
                max_time = float(obs_length)

            if interval == TIME_EVENTS:
                try:
                    min_time = float(pj[OBSERVATIONS][obs_id][EVENTS][0][0])
                except Exception:
                    min_time = float(0)
                try:
                    max_time = float(pj[OBSERVATIONS][obs_id][EVENTS][-1][0])
                except Exception:
                    max_time = float(obs_length)

            if interval == TIME_ARBITRARY_INTERVAL:
                min_time = float(start_time)
                max_time = float(end_time)

            # adapt start and stop to the selected time interval
            cursor.execute("UPDATE aggregated_events SET start = ? WHERE observation = ? AND start < ? AND stop BETWEEN ? AND ?",
                           (min_time, obs_id, min_time, min_time, max_time, ))
            cursor.execute("UPDATE aggregated_events SET stop = ? WHERE observation = ? AND stop > ? AND start BETWEEN ? AND ?",
                           (max_time, obs_id, max_time, min_time, max_time, ))

            cursor.execute("UPDATE aggregated_events SET start = ?, stop = ? WHERE observation = ? AND start < ? AND stop > ?",
                           (min_time, max_time, obs_id, min_time, max_time, ))

            cursor.execute("DELETE FROM aggregated_events WHERE observation = ? AND (start < ? AND stop < ?) OR (start > ? AND stop > ?)",
                           (obs_id, min_time, min_time, max_time, max_time, ))

            for subject in selected_subjects:

                # check if behaviors are to exclude from total time
                time_to_subtract = 0
                if EXCLUDED_BEHAVIORS in parameters_obs:
                    for excluded_behav in parameters_obs[EXCLUDED_BEHAVIORS]:
                        cursor.execute(("SELECT SUM(stop-start) "
                                        "FROM aggregated_events "
                                        "WHERE observation = ? AND subject = ? AND behavior = ? "),
                                       (obs_id, subject, excluded_behav,))
                        for row in cursor.fetchall():
                            if row[0] is not None:
                                time_to_subtract += row[0]

                for behavior_modifiers in distinct_behav_modif:
                    behavior, modifiers = behavior_modifiers
                    behavior_modifiers_str = "|".join(behavior_modifiers) if modifiers else behavior

                    cursor.execute(("SELECT SUM(stop-start), COUNT(*), AVG(stop-start), stdev(stop-start) "
                                    "FROM aggregated_events "
                                    "WHERE observation = ? AND subject = ? AND behavior = ? AND modifiers = ? "),
                                   (obs_id, subject, behavior, modifiers,))


                    for row in cursor.fetchall():
                        behaviors[subject][behavior_modifiers_str]["duration"] = (0 if row[0] is None
                                                                                  else f"{row[0]:.3f}")

                        behaviors[subject][behavior_modifiers_str]["number"] = 0 if row[1] is None else row[1]
                        behaviors[subject][behavior_modifiers_str]["duration mean"] = (0 if row[2] is None
                                                                                       else f"{row[2]:.3f}")
                        behaviors[subject][behavior_modifiers_str]["duration stdev"] = (0 if row[3] is None
                                                                                        else f"{row[3]:.3f}")

                        if behavior not in parameters_obs[EXCLUDED_BEHAVIORS]:
                            try:
                                behaviors[subject][behavior_modifiers_str]["proportion of time"] = (
                                    0 if row[0] is None
                                    else f"{row[0] / ((max_time - min_time) - time_to_subtract):.3f}")
                            except ZeroDivisionError:
                                behaviors[subject][behavior_modifiers_str]["proportion of time"] = "-"
                        else:
                            # behavior subtracted
                            behaviors[subject][behavior_modifiers_str]["proportion of time"] = (
                                0 if row[0] is None
                                else f"{row[0] / (max_time - min_time):.3f}")

            columns = [obs_id, f"{max_time - min_time:0.3f}"]
            for subj in selected_subjects:
                for behavior_modifiers in distinct_behav_modif:
                    behavior, modifiers = behavior_modifiers
                    behavior_modifiers_str = "|".join(behavior_modifiers) if modifiers else behavior

                    for param in parameters:
                        columns.append(behaviors[subj][behavior_modifiers_str][param[0]])

            data_report.append(columns)

    except Exception:
        dialog.error_message("synthetic_time_budget", sys.exc_info())

        return (False,
                msg,
                tablib.Dataset())

    return True, msg, data_report


def time_budget_analysis(ethogram: dict,
                         cursor,
                         selected_observations: list,
                         parameters: dict,
                         by_category: bool=False):
    """
    extract number of occurrences, total duration, mean ...
    if start_time = 0 and end_time = 0 all events are extracted

    Args:
        ethogram (dict): project ethogram
        cursor: cursor on temporary database
        selected_observations (list): selected observations
        parameters (dict): parameters for analysis
        by_category (bool): True for grouping in category else False

    Returns:
        list: results
        dict:
    """

    try:
        categories, out = {}, []
        for subject in parameters[SELECTED_SUBJECTS]:
            out_cat, categories[subject] = [], {}

            for behavior in parameters[SELECTED_BEHAVIORS]:

                if parameters[INCLUDE_MODIFIERS]:

                    cursor.execute("SELECT DISTINCT modifiers FROM events WHERE subject = ? AND code = ?", (subject, behavior))
                    distinct_modifiers = list(cursor.fetchall())

                    if not distinct_modifiers:
                        if not parameters[EXCLUDE_BEHAVIORS]:

                            if STATE in project_functions.event_type(behavior, ethogram):

                                out.append({"subject": subject,
                                            "behavior": behavior,
                                            "modifiers": "",
                                            "duration": 0,
                                            "duration_mean": 0,
                                            "duration_stdev": "NA",
                                            "number": "0",
                                            "inter_duration_mean": "NA",
                                            "inter_duration_stdev": "NA"})
                            else:  # point
                                out.append({"subject": subject,
                                            "behavior": behavior,
                                            "modifiers": "",
                                            "duration": 0,
                                            "duration_mean": 0,
                                            "duration_stdev": "NA",
                                            "number": "0",
                                            "inter_duration_mean": "NA",
                                            "inter_duration_stdev": "NA"})
                        continue

                    if POINT in project_functions.event_type(behavior, ethogram):

                        for modifier in distinct_modifiers:
                            cursor.execute(("SELECT occurence, observation FROM events "
                                            "WHERE subject = ? "
                                            "AND code = ? "
                                            "AND modifiers = ? "
                                            "ORDER BY observation, occurence"),
                                        (subject, behavior, modifier[0]))

                            rows = cursor.fetchall()

                            # inter events duration
                            all_event_interdurations = []
                            for idx, row in enumerate(rows):
                                if idx and row[1] == rows[idx - 1][1]:
                                    all_event_interdurations.append(float(row[0]) - float(rows[idx - 1][0]))

                            out_cat.append({
                                "subject": subject,
                                "behavior": behavior,
                                "modifiers": modifier[0],
                                "duration": NA,
                                "duration_mean": NA,
                                "duration_stdev": NA,
                                "number": len(rows),
                                "inter_duration_mean":
                                round(statistics.mean(all_event_interdurations), 3)
                                if len(all_event_interdurations) else NA,
                                "inter_duration_stdev":
                                round(statistics.stdev(all_event_interdurations), 3)
                                if len(all_event_interdurations) > 1 else NA
                            })

                    if STATE in project_functions.event_type(behavior, ethogram):

                        for modifier in distinct_modifiers:
                            cursor.execute(("SELECT occurence, observation FROM events "
                                            "WHERE subject = ? "
                                            "AND code = ? "
                                            "AND modifiers = ? "
                                            "ORDER BY observation, occurence"),
                                        (subject, behavior, modifier[0]))

                            rows = list(cursor.fetchall())
                            if len(rows) % 2:
                                out.append({"subject": subject, "behavior": behavior,
                                            "modifiers": modifier[0], "duration": UNPAIRED,
                                            "duration_mean": UNPAIRED, "duration_stdev": UNPAIRED,
                                            "number": UNPAIRED, "inter_duration_mean": UNPAIRED,
                                            "inter_duration_stdev": UNPAIRED})
                            else:
                                all_event_durations, all_event_interdurations = [], []
                                for idx, row in enumerate(rows):
                                    # event
                                    if idx % 2 == 0:
                                        new_init, new_end = float(row[0]), float(rows[idx + 1][0])

                                        all_event_durations.append(new_end - new_init)

                                    # inter event if same observation
                                    if idx % 2 and idx != len(rows) - 1 and row[1] == rows[idx + 1][1]:
                                        if (parameters["start time"] <= row[0] <= parameters["end time"]
                                                and parameters["start time"] <= rows[idx + 1][0] <= parameters["end time"]):
                                            all_event_interdurations.append(float(rows[idx + 1][0]) - float(row[0]))

                                out_cat.append({
                                    "subject":
                                    subject,
                                    "behavior":
                                    behavior,
                                    "modifiers":
                                    modifier[0],
                                    "duration":
                                    round(sum(all_event_durations), 3),
                                    "duration_mean":
                                    round(statistics.mean(all_event_durations), 3)
                                    if len(all_event_durations) else "NA",
                                    "duration_stdev":
                                    round(statistics.stdev(all_event_durations), 3)
                                    if len(all_event_durations) > 1 else "NA",
                                    "number":
                                    len(all_event_durations),
                                    "inter_duration_mean":
                                    round(statistics.mean(all_event_interdurations), 3)
                                    if len(all_event_interdurations) else "NA",
                                    "inter_duration_stdev":
                                    round(statistics.stdev(all_event_interdurations), 3)
                                    if len(all_event_interdurations) > 1 else "NA"
                                })

                else:  # no modifiers

                    if POINT in project_functions.event_type(behavior, ethogram):

                        cursor.execute(("SELECT occurence,observation FROM events "
                                        "WHERE subject = ? AND code = ? ORDER BY observation, occurence"),
                                    (subject, behavior))

                        rows = list(cursor.fetchall())

                        if len(selected_observations) == 1:
                            new_rows = []
                            for occurence, observation in rows:
                                new_occurence = max(float(parameters["start time"]), occurence)
                                new_occurence = min(new_occurence, float(parameters["end time"]))
                                new_rows.append([new_occurence, observation])
                            rows = list(new_rows)

                        # include behaviors without events
                        if not len(rows):
                            if not parameters[EXCLUDE_BEHAVIORS]:
                                out.append({"subject": subject,
                                            "behavior": behavior,
                                            "modifiers": "",
                                            "duration": NA,
                                            "duration_mean": NA,
                                            "duration_stdev": NA,
                                            "number": "0",
                                            "inter_duration_mean": NA,
                                            "inter_duration_stdev": NA})
                            continue

                        # inter events duration
                        all_event_interdurations = []
                        for idx, row in enumerate(rows):
                            if idx and row[1] == rows[idx - 1][1]:
                                all_event_interdurations.append(float(row[0]) - float(rows[idx - 1][0]))

                        out_cat.append({
                            "subject": subject,
                            "behavior": behavior,
                            "modifiers": "",
                            "duration": NA,
                            "duration_mean": NA,
                            "duration_stdev": NA,
                            "number": len(rows),
                            "inter_duration_mean":
                            round(statistics.mean(all_event_interdurations), 3)
                            if len(all_event_interdurations) else NA,
                            "inter_duration_stdev":
                            round(statistics.stdev(all_event_interdurations), 3)
                            if len(all_event_interdurations) > 1 else NA
                        })

                    if STATE in project_functions.event_type(behavior, ethogram):

                        cursor.execute(("SELECT occurence, observation FROM events "
                                        "WHERE subject = ? AND code = ? ORDER BY observation, occurence"),
                                    (subject, behavior))

                        rows = list(cursor.fetchall())
                        if not len(rows):
                            if not parameters[EXCLUDE_BEHAVIORS]:  # include behaviors without events
                                out.append({"subject": subject, "behavior": behavior,
                                            "modifiers": "", "duration": 0, "duration_mean": 0,
                                            "duration_stdev": "NA", "number": 0, "inter_duration_mean": "-",
                                            "inter_duration_stdev": "-"})
                            continue

                        if len(rows) % 2:
                            out.append({"subject": subject, "behavior": behavior, "modifiers": "",
                                        "duration": UNPAIRED, "duration_mean": UNPAIRED, "duration_stdev": UNPAIRED,
                                        "number": UNPAIRED, "inter_duration_mean": UNPAIRED,
                                        "inter_duration_stdev": UNPAIRED})
                        else:
                            all_event_durations, all_event_interdurations = [], []
                            for idx, row in enumerate(rows):
                                # event
                                if idx % 2 == 0:
                                    new_init, new_end = float(row[0]), float(rows[idx + 1][0])

                                    all_event_durations.append(new_end - new_init)

                                # inter event if same observation
                                if idx % 2 and idx != len(rows) - 1 and row[1] == rows[idx + 1][1]:
                                    if (parameters["start time"] <= row[0] <= parameters["end time"]
                                            and parameters["start time"] <= rows[idx + 1][0] <= parameters["end time"]):
                                        all_event_interdurations.append(float(rows[idx + 1][0]) - float(row[0]))

                            out_cat.append({
                                "subject":
                                subject,
                                "behavior":
                                behavior,
                                "modifiers":
                                "",
                                "duration": round(sum(all_event_durations), 3),
                                "duration_mean": round(statistics.mean(all_event_durations), 3)
                                if len(all_event_durations) else NA,
                                "duration_stdev":
                                round(statistics.stdev(all_event_durations), 3)
                                if len(all_event_durations) > 1 else NA,
                                "number": len(all_event_durations),
                                "inter_duration_mean": round(statistics.mean(all_event_interdurations), 3)
                                if len(all_event_interdurations) else NA,
                                "inter_duration_stdev": round(statistics.stdev(all_event_interdurations), 3)
                                if len(all_event_interdurations) > 1 else NA
                            })

            out += out_cat

            if by_category:  # and flagCategories:

                for behav in out_cat:

                    try:
                        category = [ethogram[x]["category"] for x in ethogram
                                    if "category" in ethogram[x] and ethogram[x]["code"] == behav['behavior']][0]
                    except Exception:
                        category = ""

                    if category in categories[subject]:
                        if behav["duration"] not in ["-", "NA"] and categories[subject][category]["duration"] not in ["-", "NA"]:
                            categories[subject][category]["duration"] += behav["duration"]
                        else:
                            categories[subject][category]["duration"] = "-"
                        categories[subject][category]["number"] += behav["number"]
                    else:
                        categories[subject][category] = {"duration": behav["duration"], "number": behav["number"]}

        out_sorted = []
        for subject in parameters[SELECTED_SUBJECTS]:
            for behavior in parameters[SELECTED_BEHAVIORS]:
                for row in out:
                    if row["subject"] == subject and row["behavior"] == behavior:
                        out_sorted.append(row)

        # http://stackoverflow.com/questions/673867/python-arbitrary-order-by
        return out_sorted, categories

    except Exception:
        dialog.error_message("time_budget", sys.exc_info())

        return [], []
