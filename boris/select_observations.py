#!/usr/bin/env python3

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


from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import QAbstractItemView

from boris import observations_list
from boris.config import (INDEPENDENT_VARIABLES, OBSERVATIONS, DESCRIPTION, TEXT,
                    TYPE, MEDIA, FILE, LIVE, OPEN, VIEW, EDIT,
                    SINGLE, MULTIPLE, SELECT1, NO_FOCAL_SUBJECT)
from boris import utilities
from boris import project_functions


def select_observations(pj: dict, mode: str, windows_title: str = "") -> tuple:
    """
    allow user to select observations
    mode: accepted values: OPEN, EDIT, SINGLE, MULTIPLE, SELECT1

    Args:
        pj (dict): BORIS project dictionary
        mode (str): mode foe selection: OPEN, EDIT, SINGLE, MULTIPLE, SELECT1
        windows_title (str): title for windows

    Returns:
        str: selected mode: OPEN, EDIT, VIEW
        list: list of selected observations
    """

    obsListFields = ["id", "date", "description", "subjects", "media"]
    indepVarHeader, column_type = [], [TEXT] * len(obsListFields)

    if INDEPENDENT_VARIABLES in pj:
        for idx in utilities.sorted_keys(pj[INDEPENDENT_VARIABLES]):
            indepVarHeader.append(pj[INDEPENDENT_VARIABLES][idx]["label"])
            column_type.append(pj[INDEPENDENT_VARIABLES][idx]["type"])

    data = []
    for obs in sorted(list(pj[OBSERVATIONS].keys())):
        date = pj[OBSERVATIONS][obs]["date"].replace("T", " ")
        descr = utilities.eol2space(pj[OBSERVATIONS][obs][DESCRIPTION])

        # subjects
        observedSubjects = [NO_FOCAL_SUBJECT if x == "" else x for x in project_functions.extract_observed_subjects(pj, [obs])]

        ''' removed 2020-01-13
        if "" in observedSubjects:
            observedSubjects.remove("")
        '''
        subjectsList = ", ".join(observedSubjects)

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

        data.append([obs, date, descr, subjectsList, media] + indepvar)

    obsList = observations_list.observationsList_widget(data,
                                                        header=obsListFields + indepVarHeader,
                                                        column_type=column_type)
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

    obsList.resize(900, 600)

    obsList.view.sortItems(0, Qt.AscendingOrder)
    for row in range(obsList.view.rowCount()):
        obsList.view.resizeRowToContents(row)

    selectedObs = []

    result = obsList.exec_()

    if result:
        if obsList.view.selectedIndexes():
            for idx in obsList.view.selectedIndexes():
                if idx.column() == 0:   # first column
                    selectedObs.append(idx.data())

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

    return resultStr, selectedObs
