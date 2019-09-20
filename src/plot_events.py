#!/usr/bin/env python3

"""
BORIS
Behavioral Observation Research Interactive Software
Copyright 2012-2019 Olivier Friard

This file is part of BORIS.

  BORIS is free software; you can redistribute it and/or modify
  it under the terms of the GNU General Public License as published by
  the Free Software Foundation; either version 3 of the License, or
  any later version.

  BORIS is distributed in the hope that it will be useful,
  but WITHOUT ANY WARRANTY; without even the implied warranty of
  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
  GNU General Public License for more details.

  You should have received a copy of the GNU General Public License
  along with this program; if not see <http://www.gnu.org/licenses/>.

"""



import datetime as dt
import json
import pathlib

import matplotlib
import matplotlib.dates
import matplotlib.font_manager as font_manager
import matplotlib.transforms as mtransforms
import numpy as np
from matplotlib import colors as mcolors
from matplotlib.dates import (HOURLY, MICROSECONDLY, MINUTELY, MONTHLY,
                              SECONDLY, WEEKLY, DateFormatter, RRuleLocator,
                              rrulewrapper)

import db_functions
import project_functions
import utilities
from config import *

matplotlib.use("Qt5Agg")
import matplotlib.pyplot as plt


plt_colors = dict(mcolors.BASE_COLORS, **mcolors.CSS4_COLORS)


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


def behaviors_bar_plot(pj, selected_observations, selected_subjects, selected_behaviors, include_modifiers,
                       interval, start_time, end_time,
                       plot_directory, output_format):
    """
    scatter plot
    """
    parameters = [["duration", "Total duration"],
                  ]

    ok, msg, db_connector = db_functions.load_aggregated_events_in_db(pj,
                                                                      selected_subjects,
                                                                      selected_observations,
                                                                      selected_behaviors)


    if not ok:
        return False, msg, None

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


    # select time interval
    for obs_id in selected_observations:

        if len(selected_subjects) > 1:
            fig, axs = plt.subplots(nrows=1, ncols=len(selected_subjects), sharey=True)
        else:
            fig, ax = plt.subplots(nrows=1, ncols=len(selected_subjects), sharey=True)
            axs = np.ndarray(shape=(1), dtype=type(ax))
            axs[0] = ax

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

        cursor.execute("UPDATE aggregated_events SET start = ? WHERE observation = ? AND start < ? AND stop BETWEEN ? AND ?",
                       (min_time, obs_id, min_time, min_time, max_time, ))
        cursor.execute("UPDATE aggregated_events SET stop = ? WHERE observation = ? AND stop > ? AND start BETWEEN ? AND ?",
                       (max_time, obs_id, max_time, min_time, max_time, ))
        cursor.execute("UPDATE aggregated_events SET start = ?, stop = ? WHERE observation = ? AND start < ? AND stop > ?",
                       (min_time, max_time, obs_id, min_time, max_time, ))

        for subject in selected_subjects:
            for behavior_modifiers in distinct_behav_modif:
                behavior, modifiers = behavior_modifiers

                # skip if behavior defined as POINT
                if POINT in project_functions.event_type(behavior, pj[ETHOGRAM]):
                    continue

                behavior_modifiers_str = "|".join(behavior_modifiers) if modifiers else behavior

                # total duration
                cursor.execute(("SELECT SUM(stop-start) FROM aggregated_events "
                                "WHERE observation = ? AND subject = ? AND behavior = ? AND modifiers = ?"),
                               (obs_id, subject, behavior, modifiers,))
                for row in cursor.fetchall():
                    behaviors[subject][behavior_modifiers_str]["duration"] = 0 if row[0] is None else row[0]

        print("behaviors")
        print(behaviors)

        print()
        print("sorted(distinct_behav_modif)", sorted(distinct_behav_modif))

        max_length = 0
        behaviors_duration = {}
        mb = {}

        for ax_idx, subj in enumerate(selected_subjects):
            behaviors_duration[subj] = {}

            behavior_ticks = []

            for behavior_modifiers in sorted(distinct_behav_modif):

                behavior, modifiers = behavior_modifiers

                # skip if behavior defined as POINT
                if POINT in project_functions.event_type(behavior, pj[ETHOGRAM]):
                    continue

                if behavior not in behaviors_duration[subj]:
                    behaviors_duration[subj][behavior] = [[], []]

                behavior_modifiers_str = "|".join(behavior_modifiers) if modifiers else behavior

                if behavior not in behavior_ticks:
                    behavior_ticks.append(behavior)

                for param in parameters:
                    behaviors_duration[subj][behavior][0].append(behaviors[subj][behavior_modifiers_str][param[0]])
                    behaviors_duration[subj][behavior][1].append(modifiers)
                    max_length = max(max_length, len(behaviors_duration[subj][behavior][1]))


            print()
            print("behaviors_duration", behaviors_duration)
            print()
            print("behavior_ticks", behavior_ticks)
            print()


        behavior_mod_ticks = behavior_ticks[:]
        for ax_idx, subj in enumerate(selected_subjects):

            print("subject", subj)
            md_lgd = []
            b = {}
            for i in range(max_length):

                b[i] = []

                for behavior in sorted(behaviors_duration[subj].keys()):
                    try:
                        b[i].append(behaviors_duration[subj][behavior][0][i])
                        if include_modifiers:

                            if behaviors_duration[subj][behavior][1][i]:
                                md_lgd.append(behavior + " " + behaviors_duration[subj][behavior][1][i])
                            else:
                                md_lgd.append(behavior)
                    except Exception:
                        b[i].append(0)

            print()
            print("behavior_mod_ticks", behavior_mod_ticks)
            print()
            print("b")
            print(b)
            print()
            print("md_lgd")
            print(md_lgd)

            ind = np.arange(len(behavior_ticks))

            width = 0.35       # the width of the bars: can also be len(x) sequence



            pp = []
            max_obs = 0
            bottom_ = []

            idx_color = 0

            for i in sorted(b.keys()):

                if i == 0:
                    pp.append(axs[ax_idx].bar(
                        ind,
                        b[i],
                        width,
                        color=BEHAVIORS_PLOT_COLORS[idx_color:idx_color + len(b[i])]))
                else:
                    pp.append(axs[ax_idx].bar(
                        ind,
                        b[i],
                        width,
                        color=BEHAVIORS_PLOT_COLORS[idx_color:idx_color + len(b[i])],
                        bottom=bottom_))


                idx_color += len(b[i])

                if not bottom_:
                    bottom_ = b[i]
                else:
                    bottom_ = [x + bottom_[idx] for idx, x in enumerate(b[i])]

                max_obs = max(max_obs, sum(b[i]))

            if ax_idx == 0:
                axs[ax_idx].set_ylabel("Duration (s)")
            axs[ax_idx].set_xlabel("Behaviors")
            axs[ax_idx].set_title(f"{subj}")

            axs[ax_idx].set_xticks(ind)
            axs[ax_idx].set_xticklabels(behavior_mod_ticks, rotation=90)
            axs[ax_idx].set_yticks(np.arange(0, max(bottom_), 50))

            lgd_col = []
            for p in pp:
                for r in p:
                    if r.get_height():
                        lgd_col.append(r)

            plt.legend(lgd_col, md_lgd)


        if plot_directory:
            output_file_name = str(
                pathlib.Path(
                    pathlib.Path(plot_directory) /
                    utilities.safeFileName(obs_id)).with_suffix("." + file_format))

            plt.savefig(output_file_name)
        else:
            plt.show()


def create_events_plot(pj,
                       selected_observations,
                       parameters,
                       plot_colors=BEHAVIORS_PLOT_COLORS,
                       plot_directory="",
                       file_format="png"):


    selected_subjects = parameters[SELECTED_SUBJECTS]
    selected_behaviors = parameters[SELECTED_BEHAVIORS]
    include_modifiers = parameters[INCLUDE_MODIFIERS]
    interval = parameters[TIME_INTERVAL]
    start_time = parameters[START_TIME]
    end_time = parameters[END_TIME]

    ok, msg, db_connector = db_functions.load_aggregated_events_in_db(pj,
                                                                      selected_subjects,
                                                                      selected_observations,
                                                                      selected_behaviors)

    if not ok:
        return False, msg, None
    cursor = db_connector.cursor()

    # if modifiers not to be included set modifiers to ""
    if not include_modifiers:
        cursor.execute("UPDATE aggregated_events SET modifiers = ''")

    cursor.execute("SELECT distinct behavior, modifiers FROM aggregated_events")
    distinct_behav_modif = [[rows["behavior"], rows["modifiers"]] for rows in cursor.fetchall()]

    # add selected behaviors that are not observed
    for behav in selected_behaviors:
        if [x for x in distinct_behav_modif if x[0] == behav] == []:
            distinct_behav_modif.append([behav, "-"])

    distinct_behav_modif = sorted(distinct_behav_modif)
    max_len = len(distinct_behav_modif)

    all_behaviors = [pj[ETHOGRAM][x][BEHAVIOR_CODE] for x in utilities.sorted_keys(pj[ETHOGRAM])]

    par1 = 1
    bar_height = 0.5
    init = dt.datetime(2017, 1, 1)

    for obs_id in selected_observations:

        if len(selected_subjects) > 1:
            fig, axs = plt.subplots(figsize=(20, 8), nrows=len(selected_subjects), ncols=1, sharex=True)
        else:
            fig, ax = plt.subplots(figsize=(20, 8), nrows=len(selected_subjects), ncols=1, sharex=True)
            axs = np.ndarray(shape=(1), dtype=type(ax))
            axs[0] = ax


        ok, msg, db_connector = db_functions.load_aggregated_events_in_db(
            pj,
            selected_subjects,
            [obs_id],
            selected_behaviors)

        cursor = db_connector.cursor()
        # if modifiers not to be included set modifiers to ""
        if not include_modifiers:
            cursor.execute("UPDATE aggregated_events SET modifiers = ''")
        cursor = db_connector.cursor()

        cursor.execute("SELECT distinct behavior, modifiers FROM aggregated_events")
        distinct_behav_modif = [[rows["behavior"], rows["modifiers"]] for rows in cursor.fetchall()]

        # add selected behaviors that are not observed
        if not parameters["exclude behaviors"]:
            for behav in selected_behaviors:
                if [x for x in distinct_behav_modif if x[0] == behav] == []:
                    distinct_behav_modif.append([behav, "-"])

        distinct_behav_modif = sorted(distinct_behav_modif)
        max_len = len(distinct_behav_modif)


        # time
        obs_length = project_functions.observation_total_length(pj[OBSERVATIONS][obs_id])
        if obs_length == -1:  # media length not available
            interval = TIME_EVENTS

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

        cursor.execute("UPDATE aggregated_events SET start = ? WHERE observation = ? AND start < ? AND stop BETWEEN ? AND ?",
                       (min_time, obs_id, min_time, min_time, max_time, ))
        cursor.execute("UPDATE aggregated_events SET stop = ? WHERE observation = ? AND stop > ? AND start BETWEEN ? AND ?",
                       (max_time, obs_id, max_time, min_time, max_time, ))
        cursor.execute("UPDATE aggregated_events SET start = ?, stop = ? WHERE observation = ? AND start < ? AND stop > ?",
                       (min_time, max_time, obs_id, min_time, max_time, ))

        ylabels = [" ".join(x) for x in distinct_behav_modif]
        for ax_idx, subject in enumerate(selected_subjects):

            if parameters["exclude behaviors"]:
                cursor.execute("SELECT distinct behavior, modifiers FROM aggregated_events WHERE subject = ?", (subject, ))
                distinct_behav_modif = [[rows["behavior"], rows["modifiers"]] for rows in cursor.fetchall()]

                # add selected behaviors that are not observed
                if not parameters["exclude behaviors"]:
                    for behav in selected_behaviors:
                        if [x for x in distinct_behav_modif if x[0] == behav] == []:
                            distinct_behav_modif.append([behav, "-"])

                distinct_behav_modif = sorted(distinct_behav_modif)
                max_len = len(distinct_behav_modif)
                ylabels = [" ".join(x) for x in distinct_behav_modif]

            if not ax_idx:
                axs[ax_idx].set_title(f"Observation {obs_id}\n{subject}", fontsize=14)
            else:
                axs[ax_idx].set_title(subject, fontsize=14)
            bars = {}
            i = 0
            for behavior_modifiers in distinct_behav_modif:
                behavior, modifiers = behavior_modifiers
                behavior_modifiers_str = "|".join(behavior_modifiers) if modifiers else behavior
                bars[behavior_modifiers_str] = []

                # total duration
                cursor.execute(("SELECT start,stop FROM aggregated_events "
                                "WHERE observation = ? AND subject = ? AND behavior = ? AND modifiers = ?"),
                               (obs_id, subject, behavior, modifiers,))
                for row in cursor.fetchall():
                    bars[behavior_modifiers_str].append((row["start"], row["stop"]))

                    start_date = matplotlib.dates.date2num(init + dt.timedelta(seconds=row["start"]))
                    end_date = matplotlib.dates.date2num(
                        init + dt.timedelta(seconds=row["stop"] + POINT_EVENT_PLOT_DURATION * (row["stop"] == row["start"])))
                    try:
                        bar_color = utilities.behavior_color(plot_colors, all_behaviors.index(behavior))
                    except Exception:
                        bar_color = "darkgray"
                    bar_color = POINT_EVENT_PLOT_COLOR if row["stop"] == row["start"] else bar_color

                    # sage colors removed from matplotlib colors list
                    if bar_color in ["sage", "darksage", "lightsage"]:
                        bar_color = {"darksage": "#598556", "lightsage": "#bcecac", "sage": "#87ae73"}[bar_color]

                    try:
                        axs[ax_idx].barh((i * par1) + par1, end_date - start_date, left=start_date, height=bar_height,
                                         align="center", edgecolor=bar_color, color=bar_color, alpha=1)
                    except Exception:
                        axs[ax_idx].barh((i * par1) + par1, end_date - start_date, left=start_date, height=bar_height,
                                         align="center", edgecolor="darkgray", color="darkgray", alpha=1)

                i += 1

            axs[ax_idx].set_ylim(bottom=0, top=(max_len * par1) + par1)
            pos = np.arange(par1, max_len * par1 + par1 + 1, par1)
            axs[ax_idx].set_yticks(pos[:len(ylabels)])

            axs[ax_idx].set_yticklabels(ylabels, fontdict={"fontsize": 10})

            axs[ax_idx].set_ylabel("Behaviors" + " (modifiers)" * include_modifiers, fontdict={"fontsize": 10})

            axs[ax_idx].set_xlim(left=matplotlib.dates.date2num(init + dt.timedelta(seconds=min_time)),
                                 right=matplotlib.dates.date2num(init + dt.timedelta(seconds=max_time + 1)))

            axs[ax_idx].grid(color="g", linestyle=":")
            axs[ax_idx].xaxis_date()
            axs[ax_idx].xaxis.set_major_formatter(DateFormatter("%H:%M:%S"))
            axs[ax_idx].set_xlabel("Time (HH:MM:SS)", fontdict={"fontsize": 12})
            axs[ax_idx].invert_yaxis()

        fig.autofmt_xdate()
        plt.tight_layout()

        if len(selected_observations) > 1:
            output_file_name = str(pathlib.Path(pathlib.Path(plot_directory) / utilities.safeFileName(obs_id)).with_suffix(
                "." + file_format))
            plt.savefig(output_file_name)
        else:
            plt.show()




"""
# TEST time
def create_events_plot_new(pj,
                       selected_observations,
                       parameters,
                       plot_colors=BEHAVIORS_PLOT_COLORS,
                       plot_directory="",
                       file_format="png"):


    selected_subjects = parameters["selected subjects"]
    selected_behaviors = parameters["selected behaviors"]
    include_modifiers = parameters["include modifiers"]
    interval = parameters[TIME_INTERVAL]
    start_time = parameters[START_TIME]
    end_time = parameters[END_TIME]

    ok, msg, db_connector = db_functions.load_aggregated_events_in_db(pj,
                                                       selected_subjects,
                                                       selected_observations,
                                                       selected_behaviors)

    if not ok:
        return False, msg, None
    cursor = db_connector.cursor()

    # if modifiers not to be included set modifiers to ""
    if not include_modifiers:
        cursor.execute("UPDATE aggregated_events SET modifiers = ''")

    cursor.execute("SELECT distinct behavior, modifiers FROM aggregated_events")

    '''
    distinct_behav_modif = [[rows["behavior"], rows["modifiers"]] for rows in cursor.fetchall()]


    # add selected behaviors that are not observed
    for behav in selected_behaviors:
        if [x for x in distinct_behav_modif if x[0] == behav] == []:
            distinct_behav_modif.append([behav, "-"])

    distinct_behav_modif = sorted(distinct_behav_modif)
    max_len = len(distinct_behav_modif)
    '''

    all_behaviors = [pj[ETHOGRAM][x][BEHAVIOR_CODE] for x in utilities.sorted_keys(pj[ETHOGRAM])]

    par1 = 1
    bar_height = 0.5
    init = dt.datetime(2017, 1, 1)

    for obs_id in selected_observations:

        if len(selected_subjects) > 1:
            fig, axs = plt.subplots(figsize=(20, 8), nrows=len(selected_subjects), ncols=1, sharex=True)
        else:
            fig, ax = plt.subplots(figsize=(20, 8), nrows=len(selected_subjects), ncols=1, sharex=True)
            axs = np.ndarray(shape=(1), dtype=type(ax))
            axs[0] = ax


        '''
        ok, msg, db_connector = db_functions.load_aggregated_events_in_db(
            pj,
            selected_subjects,
            [obs_id],
            selected_behaviors)

        cursor = db_connector.cursor()
        # if modifiers not to be included set modifiers to ""
        if not include_modifiers:
            cursor.execute("UPDATE aggregated_events SET modifiers = ''")
        cursor = db_connector.cursor()
        '''

        cursor.execute("SELECT distinct behavior, modifiers FROM aggregated_events WHERE observation = ?", (obs_id, ))
        distinct_behav_modif = [[rows["behavior"], rows["modifiers"]] for rows in cursor.fetchall()]

        # add selected behaviors that are not observed
        if not parameters["exclude behaviors"]:
            for behav in selected_behaviors:
                if [x for x in distinct_behav_modif if x[0] == behav] == []:
                    distinct_behav_modif.append([behav, "-"])

        distinct_behav_modif = sorted(distinct_behav_modif)
        max_len = len(distinct_behav_modif)


        # time
        obs_length = project_functions.observation_total_length(pj[OBSERVATIONS][obs_id])
        if obs_length == -1: # media length not available
            interval = TIME_EVENTS

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

        cursor.execute("UPDATE aggregated_events SET start = ? WHERE observation = ? AND start < ? AND stop BETWEEN ? AND ?",
                       (min_time, obs_id, min_time, min_time, max_time, ))
        cursor.execute("UPDATE aggregated_events SET stop = ? WHERE observation = ? AND stop > ? AND start BETWEEN ? AND ?",
                       (max_time, obs_id, max_time, min_time, max_time, ))
        cursor.execute("UPDATE aggregated_events SET start = ?, stop = ? WHERE observation = ? AND start < ? AND stop > ?",
                       (min_time, max_time, obs_id, min_time, max_time, ))

        ylabels = [" ".join(x) for x in distinct_behav_modif]
        for ax_idx, subject in enumerate(selected_subjects):

            if parameters["exclude behaviors"]:
                cursor.execute("SELECT distinct behavior, modifiers FROM aggregated_events WHERE subject = ? AND observation = ?",
                               (subject, obs_id, ))
                distinct_behav_modif = [[rows["behavior"], rows["modifiers"]] for rows in cursor.fetchall()]

                # add selected behaviors that are not observed
                if not parameters["exclude behaviors"]:
                    for behav in selected_behaviors:
                        if [x for x in distinct_behav_modif if x[0] == behav] == []:
                            distinct_behav_modif.append([behav, "-"])

                distinct_behav_modif = sorted(distinct_behav_modif)
                max_len = len(distinct_behav_modif)
                ylabels = [" ".join(x) for x in distinct_behav_modif]

            if not ax_idx:
                axs[ax_idx].set_title("Observation {}\n{}".format(obs_id, subject), fontsize=14)
            else:
                axs[ax_idx].set_title(subject, fontsize=14)
            bars = {}
            i = 0
            for behavior_modifiers in distinct_behav_modif:
                behavior, modifiers = behavior_modifiers
                behavior_modifiers_str = "|".join(behavior_modifiers) if modifiers else behavior
                bars[behavior_modifiers_str] = []

                # total duration
                cursor.execute(("SELECT start,stop FROM aggregated_events "
                                "WHERE observation = ? AND subject = ? AND behavior = ? AND modifiers = ?"),
                               (obs_id, subject, behavior, modifiers,))
                for row in cursor.fetchall():
                    bars[behavior_modifiers_str].append((row["start"], row["stop"]))

                    start_date = matplotlib.dates.date2num(init + dt.timedelta(seconds=row["start"]))
                    end_date = matplotlib.dates.date2num(
                        init + dt.timedelta(seconds=row["stop"] + POINT_EVENT_PLOT_DURATION * (row["stop"] == row["start"])))
                    try:
                        bar_color = utilities.behavior_color(plot_colors, all_behaviors.index(behavior))
                    except Exception:
                        bar_color = "darkgray"
                    bar_color = POINT_EVENT_PLOT_COLOR if row["stop"] == row["start"] else bar_color

                    # sage colors removed from matplotlib colors list
                    if bar_color in ["sage", "darksage", "lightsage"]:
                        bar_color = {"darksage": "#598556", "lightsage": "#bcecac", "sage": "#87ae73"}[bar_color]

                    try:
                        axs[ax_idx].barh((i * par1) + par1, end_date - start_date, left=start_date, height=bar_height,
                                         align="center", edgecolor=bar_color, color=bar_color, alpha=1)
                    except Exception:
                        axs[ax_idx].barh((i * par1) + par1, end_date - start_date, left=start_date, height=bar_height,
                                         align="center", edgecolor="darkgray", color="darkgray", alpha=1)

                i += 1

            axs[ax_idx].set_ylim(bottom=0, top=(max_len * par1) + par1)
            pos = np.arange(par1, max_len * par1 + par1 + 1, par1)
            axs[ax_idx].set_yticks(pos[:len(ylabels)])

            axs[ax_idx].set_yticklabels(ylabels, fontdict={"fontsize": 10})

            axs[ax_idx].set_ylabel("Behaviors" + " (modifiers)" * include_modifiers, fontdict={"fontsize": 10})

            axs[ax_idx].set_xlim(left=matplotlib.dates.date2num(init + dt.timedelta(seconds=min_time)),
                                 right=matplotlib.dates.date2num(init + dt.timedelta(seconds=max_time + 1)))

            axs[ax_idx].grid(color="g", linestyle=":")
            axs[ax_idx].xaxis_date()
            axs[ax_idx].xaxis.set_major_formatter(DateFormatter("%H:%M:%S"))
            axs[ax_idx].set_xlabel("Time (HH:MM:SS)", fontdict={"fontsize": 12})
            axs[ax_idx].invert_yaxis()

        fig.autofmt_xdate()
        plt.tight_layout()

        if len(selected_observations) > 1:
            output_file_name = str(pathlib.Path(pathlib.Path(plot_directory) / utilities.safeFileName(obs_id)).with_suffix(
                "." + file_format))
            plt.savefig(output_file_name)
        else:
            plt.show()
"""
