#!/usr/bin/env python3

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

import os
import pathlib
import logging
from PyQt5.QtCore import Qt, QSettings
from PyQt5.QtWidgets import QAbstractItemView

from boris import observations_list
from boris.config import (INDEPENDENT_VARIABLES, OBSERVATIONS, DESCRIPTION, TEXT, NUMERIC,
                          TYPE, MEDIA, FILE, LIVE, OPEN, VIEW, EDIT, ETHOGRAM, EVENTS,
                          SINGLE, MULTIPLE, SELECT1, NO_FOCAL_SUBJECT, HHMMSS,
                          STATE, BEHAVIOR_CODE)
from boris import gui_utilities
from boris import utilities
from boris import project_functions


def select_observations(pj: dict,
                        mode: str,
                        windows_title: str = ""
                        ) -> tuple:
    """
    allow user to select observations
    mode: accepted values: OPEN, EDIT, SINGLE, MULTIPLE, SELECT1

    Args:
        pj (dict): BORIS project dictionary
        mode (str): mode for selection: OPEN, EDIT, SINGLE, MULTIPLE, SELECT1
        windows_title (str): title for windows

    Returns:
        str: selected mode: OPEN, EDIT, VIEW
        list: list of selected observations
    """

    obsListFields = ["id", "date", "description", "subjects", "observation duration", "exhaustivity %", "media"]
    indepVarHeader, column_type = [], [TEXT, TEXT, TEXT, TEXT, NUMERIC, NUMERIC, TEXT]

    if INDEPENDENT_VARIABLES in pj:
        for idx in utilities.sorted_keys(pj[INDEPENDENT_VARIABLES]):
            indepVarHeader.append(pj[INDEPENDENT_VARIABLES][idx]["label"])
            column_type.append(pj[INDEPENDENT_VARIABLES][idx]["type"])

    data = []
    not_paired = []
    state_events_list = [pj[ETHOGRAM][x][BEHAVIOR_CODE] for x in pj[ETHOGRAM] if STATE in pj[ETHOGRAM][x][TYPE].upper()]
    for obs in sorted(list(pj[OBSERVATIONS].keys())):
        date = pj[OBSERVATIONS][obs]["date"].replace("T", " ")
        descr = utilities.eol2space(pj[OBSERVATIONS][obs][DESCRIPTION])

        # subjects
        observedSubjects = [NO_FOCAL_SUBJECT if x == "" else x for x in project_functions.extract_observed_subjects(pj, [obs])]

        subjectsList = ", ".join(observedSubjects)

        # observed time interval
        interval = project_functions.observed_interval(pj[OBSERVATIONS][obs])
        observed_interval_str = str(interval[1] - interval[0]) 

        # media
        mediaList = []
        if pj[OBSERVATIONS][obs][TYPE] in [MEDIA]:
            if pj[OBSERVATIONS][obs][FILE]:
                for player in sorted(pj[OBSERVATIONS][obs][FILE].keys()):
                    for media in pj[OBSERVATIONS][obs][FILE][player]:
                        mediaList.append(f"#{player}: {media}")

            if len(mediaList) > 8:
                media = " ".join(mediaList)
            else:
                media = "\n".join(mediaList)

        elif pj[OBSERVATIONS][obs][TYPE] in [LIVE]:
            media = LIVE

        # independent variables
        indepvar = []
        if INDEPENDENT_VARIABLES in pj[OBSERVATIONS][obs]:
            for var_label in indepVarHeader:
                if var_label in pj[OBSERVATIONS][obs][INDEPENDENT_VARIABLES]:
                    indepvar.append(pj[OBSERVATIONS][obs][INDEPENDENT_VARIABLES][var_label])
                else:
                    indepvar.append("")

        # check unpaired events
        ok, _ = project_functions.check_state_events_obs(obs, pj[ETHOGRAM], pj[OBSERVATIONS][obs], HHMMSS)
        if not ok:
            not_paired.append(obs)

        # check exhaustivity of observation 
        exhaustivity = project_functions.check_observation_exhaustivity(pj[OBSERVATIONS][obs][EVENTS],
                                                                        [],
                                                                        state_events_list
                                                                       )


        data.append([obs, date, descr, subjectsList, observed_interval_str, str(exhaustivity), media] + indepvar)

    
    obsList = observations_list.observationsList_widget(data,
                                                        header=obsListFields + indepVarHeader,
                                                        column_type=column_type,
                                                        not_paired=not_paired)
    if windows_title:
        obsList.setWindowTitle(windows_title)

    obsList.pbOpen.setVisible(False)
    obsList.pbView.setVisible(False)
    obsList.pbEdit.setVisible(False)
    obsList.pbOk.setVisible(False)
    obsList.pbSelectAll.setVisible(False)
    obsList.pbUnSelectAll.setVisible(False)
    obsList.mode = mode

    if mode == OPEN:
        obsList.view.setSelectionMode(QAbstractItemView.SingleSelection)
        obsList.pbOpen.setVisible(True)

    if mode == VIEW:
        obsList.view.setSelectionMode(QAbstractItemView.SingleSelection)
        obsList.pbView.setVisible(True)

    if mode == EDIT:
        obsList.view.setSelectionMode(QAbstractItemView.SingleSelection)
        obsList.pbEdit.setVisible(True)

    if mode == SINGLE:
        obsList.view.setSelectionMode(QAbstractItemView.SingleSelection)
        obsList.pbOpen.setVisible(True)
        obsList.pbView.setVisible(True)
        obsList.pbEdit.setVisible(True)

    if mode == MULTIPLE:
        obsList.view.setSelectionMode(QAbstractItemView.MultiSelection)
        obsList.pbOk.setVisible(True)
        obsList.pbSelectAll.setVisible(True)
        obsList.pbUnSelectAll.setVisible(True)

    if mode == SELECT1:
        obsList.view.setSelectionMode(QAbstractItemView.SingleSelection)
        obsList.pbOk.setVisible(True)

    # restore window geometry
    gui_utilities.restore_geometry(obsList, "observations list", (900, 600))

    obsList.view.sortItems(0, Qt.AscendingOrder)
    for row in range(obsList.view.rowCount()):
        obsList.view.resizeRowToContents(row)

    selected_observations = []

    result = obsList.exec_()

    # saving window geometry in ini file
    gui_utilities.save_geometry(obsList, "observations list")

    if result:
        if obsList.view.selectedIndexes():
            for idx in obsList.view.selectedIndexes():
                if idx.column() == 0:   # first column
                    selected_observations.append(idx.data())

    if result == 0:  # cancel
        resultStr = ""
    if result == 1:   # select
        resultStr = "ok"
    if result == 2:   # open
        resultStr = OPEN
    if result == 3:   # edit
        resultStr = EDIT
    if result == 4:   # view
        resultStr = VIEW

    return resultStr, selected_observations
