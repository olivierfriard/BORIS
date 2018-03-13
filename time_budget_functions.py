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
import math
from config import *
import db_functions
import project_functions

def default_value(ethogram, behav, param):
    """
    return value for duration in case of point event
    """
    default_value_ = 0
    if ({ethogram[idx]["type"] for idx in ethogram if ethogram[idx]["code"] == behav} == {"Point event"} 
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
        return math.sqrt(self.S / (self.k-2))



def synthetic_time_budget(pj, selected_observations, selected_subjects, selected_behaviors, include_modifiers, interval, start_time, end_time):

    parameters = [["duration", "Total duration"],
                  ["number", "Number of occurrences"],
                  ["duration mean", "Duration mean"],
                  ["duration stdev", "Duration std dev"],
                  ["proportion of time", "Proportion o time"],
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
    if include_modifiers:
        cursor.execute("SELECT distinct behavior, modifiers FROM aggregated_events")
        distinct_behav_modif = [[rows["behavior"], rows["modifiers"]] for rows in cursor.fetchall()]
    else:
        cursor.execute("SELECT distinct behavior FROM aggregated_events")
        distinct_behav_modif = [[rows["behavior"], ""] for rows in cursor.fetchall()]

    # add selected behaviors that are not observed
    for behav in selected_behaviors:
        if [x for x in distinct_behav_modif if x[0] == behav] == []:
            distinct_behav_modif.append([behav, "-"])

    behaviors = init_behav_modif(pj[ETHOGRAM],
                                 selected_subjects,
                                 distinct_behav_modif,
                                 include_modifiers,
                                 parameters)

    param_header = ["", "Total length (s)"]
    subj_header, behav_header, modif_header= [""]*len(param_header), [""]*len(param_header), [""]*len(param_header)

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

    # select time interval
    for obs_id in selected_observations:

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
            except:
                min_time = float(0)
            try:
                max_time = float(pj[OBSERVATIONS][obs_id][EVENTS][-1][0])
            except:
                max_time = float(obs_length)

        if interval == TIME_ARBITRARY_INTERVAL:
            min_time = float(start_time)
            max_time = float(end_time)

        cursor.execute("UPDATE aggregated_events SET start = ? WHERE observation = ? AND start < ? AND stop BETWEEN ? AND ?",
                      (min_time, obs_id, min_time, min_time, max_time, ))
        cursor.execute("UPDATE aggregated_events SET stop = ? WHERE observation = ? AND stop > ? AND start BETWEEN ? AND ?",
                      (max_time, obs_id, max_time, min_time, max_time, ))
                      
        cursor.execute("UPDATE aggregated_events SET start = ?, stop = ? WHERE observation = ? AND start < ? AND stop > ?",
                         (min_time, max_time, obs_id, min_time, max_time, ))

        for subject in selected_subjects:
            for behavior_modifiers in distinct_behav_modif:
                behavior, modifiers = behavior_modifiers
                behavior_modifiers_str = "|".join(behavior_modifiers) if modifiers else behavior
                
                # total duration
                cursor.execute(("SELECT SUM(stop-start) FROM aggregated_events "
                                "WHERE observation = ? AND subject = ? AND behavior = ? AND modifiers = ?"),
                              (obs_id, subject, behavior, modifiers,))
                for row in cursor.fetchall():
                    behaviors[subject][behavior_modifiers_str]["duration"] = 0 if row[0] is None else row[0]

                # number of occurences
                cursor.execute(("SELECT COUNT(*) FROM aggregated_events "
                                "WHERE observation = ? AND subject = ? AND behavior = ? AND modifiers = ?"),
                              (obs_id, subject, behavior, modifiers,))
                for row in cursor.fetchall():
                    behaviors[subject][behavior_modifiers_str]["number"] = 0 if row[0] is None else row[0]

                # mean duration
                cursor.execute(("SELECT AVG(stop-start) FROM aggregated_events "
                                "WHERE observation = ? AND subject = ? AND behavior = ? AND modifiers = ?"),
                              (obs_id, subject, behavior, modifiers,))
                for row in cursor.fetchall():
                    behaviors[subject][behavior_modifiers_str]["duration mean"] = 0 if row[0] is None else row[0]

                # std dev duration
                cursor.execute(("SELECT stdev(stop-start) FROM aggregated_events "
                               "WHERE observation = ? AND subject = ? AND behavior = ? AND modifiers = ?"),
                              (obs_id, subject, behavior, modifiers,))
                for row in cursor.fetchall():
                    behaviors[subject][behavior_modifiers_str]["duration stdev"] = 0 if row[0] is None else row[0]

                # % total duration
                cursor.execute(("SELECT SUM(stop-start)/? FROM aggregated_events "
                                "WHERE observation = ? AND subject = ? AND behavior = ? AND modifiers = ?"),
                              (max_time - min_time, obs_id, subject, behavior, modifiers,))
                for row in cursor.fetchall():
                    behaviors[subject][behavior_modifiers_str]["proportion of time"] = 0 if row[0] is None else row[0]

        columns = [obs_id, "{:0.3f}".format(max_time - min_time)]
        for subj in selected_subjects:
            for behavior_modifiers in distinct_behav_modif:
                behavior, modifiers = behavior_modifiers
                behavior_modifiers_str = "|".join(behavior_modifiers) if modifiers else behavior

                for param in parameters:
                    columns.append(behaviors[subj][behavior_modifiers_str][param[0]])

        data_report.append(columns)
        
    return True, msg, data_report


'''
def time_budget():
'''

