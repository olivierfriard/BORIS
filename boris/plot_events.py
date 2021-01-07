#!/usr/bin/env python3

"""
BORIS
Behavioral Observation Research Interactive Software
Copyright 2012-2021 Olivier Friard

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
import logging
import pathlib
import sys

import matplotlib
matplotlib.use("Qt5Agg")
import matplotlib.dates
import matplotlib.font_manager as font_manager
import matplotlib.pyplot as plt
import matplotlib.transforms as mtransforms
import numpy as np
from matplotlib import colors as mcolors
from matplotlib.dates import (HOURLY, MICROSECONDLY, MINUTELY, MONTHLY,
                              SECONDLY, WEEKLY, DateFormatter, RRuleLocator,
                              rrulewrapper)

from boris import db_functions
from boris import project_functions
from boris import utilities
from boris.config import *




plt_colors = dict(mcolors.BASE_COLORS, **mcolors.CSS4_COLORS)


def default_value(ethogram, behavior, parameter):
    """
    return value for duration in case of point event
    """
    default_value_ = 0
    if (project_functions.event_type(behavior, ethogram) == "POINT EVENT"
            and parameter in ["duration"]):
        default_value_ = "NA"
    return default_value_


def init_behav_modif(ethogram: dict,
                     selected_subjects: list,
                     distinct_behav_modif,
                     include_modifiers,
                     parameters):
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

            for parameter in parameters:
                behaviors[subj][behav_modif_str][parameter[0]] = default_value(ethogram, behav_modif_str, parameter[0])

    return behaviors


def init_behav(ethogram: dict,
                     selected_subjects: list,
                     distinct_behaviors,
                     parameters):
    """
    initialize dictionary with subject, behaviors and modifiers
    """
    behaviors = {}
    for subj in selected_subjects:
        behaviors[subj] = {}
        for behavior in distinct_behaviors:
            if behavior not in behaviors[subj]:
                behaviors[subj][behavior] = {}
            for parameter in parameters:
                behaviors[subj][behavior][parameter] = default_value(ethogram, behavior, parameter)
    return behaviors


def create_behaviors_bar_plot(pj: dict,
                       selected_observations: list,
                       param: dict,
                       plot_directory: str,
                       output_format: str,
                       plot_colors:list=BEHAVIORS_PLOT_COLORS):
    """
    time budget bar plot

    Args:
        pj (dict): project
        param (dict): parameters
        plot_directory (str): path of directory
        output_format (str): image format

    Returns:
        dict:
    """

    selected_subjects = param[SELECTED_SUBJECTS]
    selected_behaviors = param[SELECTED_BEHAVIORS]
    time_interval = param["time"]
    start_time = param[START_TIME]
    end_time = param[END_TIME]

    parameters = ["duration", "number of occurences"]

    ok, msg, db_connector = db_functions.load_aggregated_events_in_db(pj,
                                                                      selected_subjects,
                                                                      selected_observations,
                                                                      selected_behaviors)

    if not ok:
        return {"error": True, "message": msg}
    try:

        # extract all behaviors from ethogram for colors in plot
        all_behaviors = [pj[ETHOGRAM][x][BEHAVIOR_CODE] for x in utilities.sorted_keys(pj[ETHOGRAM])]

        for obs_id in selected_observations:

            cursor = db_connector.cursor()
            # distinct behaviors
            cursor.execute("SELECT distinct behavior FROM aggregated_events WHERE observation = ?",
                           (obs_id,))
            distinct_behav = [rows["behavior"] for rows in cursor.fetchall()]

            # add selected behaviors that are not observed
            '''
            if not param[EXCLUDE_BEHAVIORS]:
                for behavior in selected_behaviors:
                    if [x for x in distinct_behav if x == behavior] == []:
                        distinct_behav.append(behavior)
            '''

            # distinct subjects
            cursor.execute("SELECT distinct subject FROM aggregated_events WHERE observation = ?",
                           (obs_id,))
            distinct_subjects = [rows["subject"] for rows in cursor.fetchall()]

            behaviors = init_behav(pj[ETHOGRAM],
                                distinct_subjects,
                                distinct_behav,
                                parameters)

            # plot creation
            if len(distinct_subjects) > 1:
                fig, axs = plt.subplots(nrows=1, ncols=len(distinct_subjects), sharey=True)
                fig2, axs2 = plt.subplots(nrows=1, ncols=len(distinct_subjects), sharey=True)

            else:
                fig, ax = plt.subplots(nrows=1, ncols=len(distinct_subjects), sharey=True)
                axs = np.ndarray(shape=(1), dtype=type(ax))
                axs[0] = ax

                fig2, ax2 = plt.subplots(nrows=1, ncols=len(distinct_subjects), sharey=True)
                axs2 = np.ndarray(shape=(1), dtype=type(ax2))
                axs2[0] = ax2

            fig.suptitle("Durations of behaviors")
            fig2.suptitle("Number of occurences of behaviors")

            # if modifiers not to be included set modifiers to ""
            cursor.execute("UPDATE aggregated_events SET modifiers = ''")

            # time
            obs_length = project_functions.observation_total_length(pj[OBSERVATIONS][obs_id])
            if obs_length == -1:
                obs_length = 0

            if param["time"] == TIME_FULL_OBS:
                min_time = float(0)
                max_time = float(obs_length)

            if param["time"] == TIME_EVENTS:
                try:
                    min_time = float(pj[OBSERVATIONS][obs_id][EVENTS][0][0])
                except Exception:
                    min_time = float(0)
                try:
                    max_time = float(pj[OBSERVATIONS][obs_id][EVENTS][-1][0])
                except Exception:
                    max_time = float(obs_length)

            if param["time"] == TIME_ARBITRARY_INTERVAL:
                min_time = float(start_time)
                max_time = float(end_time)

            cursor.execute("UPDATE aggregated_events SET start = ? WHERE observation = ? AND start < ? AND stop BETWEEN ? AND ?",
                        (min_time, obs_id, min_time, min_time, max_time, ))
            cursor.execute("UPDATE aggregated_events SET stop = ? WHERE observation = ? AND stop > ? AND start BETWEEN ? AND ?",
                        (max_time, obs_id, max_time, min_time, max_time, ))
            cursor.execute("UPDATE aggregated_events SET start = ?, stop = ? WHERE observation = ? AND start < ? AND stop > ?",
                        (min_time, max_time, obs_id, min_time, max_time, ))

            for ax_idx, subject in enumerate(sorted(distinct_subjects)):

                for behavior in distinct_behav:

                    # number of occurences
                    cursor.execute(("SELECT COUNT(*) AS count FROM aggregated_events "
                                    "WHERE observation = ? AND subject = ? AND behavior = ?"),
                                (obs_id, subject, behavior, ))
                    for row in cursor.fetchall():
                        behaviors[subject][behavior]["number of occurences"] = 0 if row["count"] is None else row["count"]

                    # total duration
                    if STATE in project_functions.event_type(behavior, pj[ETHOGRAM]):
                        cursor.execute(("SELECT SUM(stop - start) AS duration FROM aggregated_events "
                                        "WHERE observation = ? AND subject = ? AND behavior = ?"),
                                    (obs_id, subject, behavior, ))
                        for row in cursor.fetchall():
                            behaviors[subject][behavior]["duration"] = 0 if row["duration"] is None else row["duration"]

                durations, n_occurences, colors, x_labels, colors_duration, x_labels_duration = [], [], [], [], [], []

                for behavior in sorted(distinct_behav):

                    if param[EXCLUDE_BEHAVIORS] and behaviors[subject][behavior]["number of occurences"] == 0:
                        continue

                    n_occurences.append(behaviors[subject][behavior]["number of occurences"])
                    x_labels.append(behavior)
                    try:
                        colors.append(utilities.behavior_color(plot_colors, all_behaviors.index(behavior)))
                    except Exception:
                        colors.append("darkgray")

                    if STATE in project_functions.event_type(behavior, pj[ETHOGRAM]):
                        durations.append(behaviors[subject][behavior]["duration"])
                        x_labels_duration.append(behavior)
                        try:
                            colors_duration.append(utilities.behavior_color(plot_colors, all_behaviors.index(behavior)))
                        except Exception:
                            colors_duration.append("darkgray")


                #width = 0.35       # the width of the bars: can also be len(x) sequence

                axs2[ax_idx].bar(np.arange(len(n_occurences)),
                                n_occurences,
                                #width,
                                color=colors
                                )


                axs[ax_idx].bar(np.arange(len(durations)),
                                durations,
                                #width,
                                color=colors_duration
                                )

                if ax_idx == 0:
                    axs[ax_idx].set_ylabel("Duration (s)")
                axs[ax_idx].set_xlabel("Behaviors")
                axs[ax_idx].set_title(f"{subject}")

                axs[ax_idx].set_xticks(np.arange(len(durations)))
                axs[ax_idx].set_xticklabels(x_labels_duration, rotation='vertical', fontsize=8)

                if ax_idx == 0:
                    axs2[ax_idx].set_ylabel("Number of occurences")
                axs2[ax_idx].set_xlabel("Behaviors")
                axs2[ax_idx].set_title(f"{subject}")

                axs2[ax_idx].set_xticks(np.arange(len(n_occurences)))
                axs2[ax_idx].set_xticklabels(x_labels, rotation='vertical', fontsize=8)


            fig.align_labels()
            fig.tight_layout(rect=[0, 0.03, 1, 0.95])

            fig2.align_labels()
            fig2.tight_layout(rect=[0, 0.03, 1, 0.95])


            if plot_directory:
                # output_file_name = f"{pathlib.Path(plot_directory) / utilities.safeFileName(obs_id)}.{output_format}"
                fig.savefig(f"{pathlib.Path(plot_directory) / utilities.safeFileName(obs_id)}.duration.{output_format}")
                fig2.savefig(f"{pathlib.Path(plot_directory) / utilities.safeFileName(obs_id)}.number_of_occurences.{output_format}")
                plt.close()
            else:
                fig.show()
                fig2.show()

        return {}

    except Exception:
        error_type, error_file_name, error_lineno = utilities.error_info(sys.exc_info())
        logging.critical(f"Error in time budget bar plot: {error_type} {error_file_name} {error_lineno}")
        return {"error": True, "exception": sys.exc_info()}


def create_events_plot(pj,
                       selected_observations,
                       parameters,
                       plot_colors=BEHAVIORS_PLOT_COLORS,
                       plot_directory="",
                       file_format="png"):

    """
    create a time diagram plot (sort of gantt chart)
    with matplotlib barh function (https://matplotlib.org/3.1.0/api/_as_gen/matplotlib.pyplot.barh.html)
    """

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
                cursor.execute(("SELECT start, stop FROM aggregated_events "
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
            plt.savefig(f"{pathlib.Path(plot_directory) / utilities.safeFileName(obs_id)}.{file_format}")
        else:
            plt.show()
