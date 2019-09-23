"""
BORIS
Behavioral Observation Research Interactive Software
Copyright 2012-2019 Olivier Friard

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

import os
import pathlib
import re
import time

import intervals as I  # python-intervals (https://pypi.org/project/python-intervals)
from PyQt5.QtWidgets import QMessageBox

import db_functions
import dialog
import project_functions
import select_observations
import utilities
from config import *


def ic(i):
    return I.closed(i[0], i[1])


def event_filtering(pj: dict):

    result, selected_observations = select_observations.select_observations(pj,
                                                                            MULTIPLE,
                                                                            "Select observations for advanced event filtering")
    if not selected_observations:
        return

    # check if state events are paired
    out = ""
    not_paired_obs_list = []
    for obs_id in selected_observations:
        r, msg = project_functions.check_state_events_obs(obs_id, pj[ETHOGRAM],
                                                          pj[OBSERVATIONS][obs_id])

        if not r:
            out += f"Observation: <strong>{obs_id}</strong><br>{msg}<br>"
            not_paired_obs_list.append(obs_id)

    if out:
        out = f"The observations with UNPAIRED state events will be removed from tha analysis<br><br>{out}"
        results = dialog.Results_dialog()
        results.setWindowTitle(f"{programName} - Check selected observations")
        results.ptText.setReadOnly(True)
        results.ptText.appendHtml(out)
        results.pbSave.setVisible(False)
        results.pbCancel.setVisible(True)

        if not results.exec_():
            return
    selected_observations = [x for x in selected_observations if x not in not_paired_obs_list]
    if not selected_observations:
        return

    # observations length
    max_obs_length, selectedObsTotalMediaLength = project_functions.observation_length(pj, selected_observations)
    if max_obs_length == -1:  # media length not available, user choose to not use events
        return

    parameters = dialog.choose_obs_subj_behav_category(pj,
                                                       selected_observations,
                                                       maxTime=max_obs_length,
                                                       flagShowIncludeModifiers=False,
                                                       flagShowExcludeBehaviorsWoEvents=False,
                                                       by_category=False)

    if not parameters[SELECTED_SUBJECTS] or not parameters[SELECTED_BEHAVIORS]:
        QMessageBox.warning(None, programName, "Select subject(s) and behavior(s) to analyze")
        return

    print("load in db")
    t1 = time.time()
    ok, msg, db_connector = db_functions.load_aggregated_events_in_db(pj,
                                                                      parameters[SELECTED_SUBJECTS],
                                                                      selected_observations,
                                                                      parameters[SELECTED_BEHAVIORS])

    cursor = db_connector.cursor()
    events = {}

    cursor.execute("SELECT observation, subject, behavior, start, stop FROM aggregated_events")

    for row in cursor.fetchall():

        for event in row:
            obs, subj, behav, start, stop = row
            if obs not in events:
                events[obs] = {}
            if subj + "|" + behav not in events[obs]:
                events[obs][subj + "|" + behav] = ic([start, stop])
            else:
                events[obs][subj + "|" + behav] = events[obs][subj + "|" + behav] | ic([start, stop])

    t2 = time.time()
    print(f"db loaded: {t2 - t1}")

    w = dialog.Advanced_event_filtering_dialog(events)
    w.exec_()
