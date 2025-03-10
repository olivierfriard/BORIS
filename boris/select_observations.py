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

from typing import Tuple
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QAbstractItemView

from . import config as cfg
from . import gui_utilities, observations_list, project_functions
from . import utilities as util


def select_observations2(self, mode: str, windows_title: str = "") -> Tuple[str, list]:
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

    pj = self.pj

    fields_list = ["id", "date", "description", "subjects", "observation duration", "exhaustivity %", "media"]
    indep_var_header, column_type = [], [cfg.TEXT, cfg.TEXT, cfg.TEXT, cfg.TEXT, cfg.NUMERIC, cfg.NUMERIC, cfg.TEXT]

    if cfg.INDEPENDENT_VARIABLES in pj:
        for idx in util.sorted_keys(pj[cfg.INDEPENDENT_VARIABLES]):
            indep_var_header.append(pj[cfg.INDEPENDENT_VARIABLES][idx]["label"])
            column_type.append(pj[cfg.INDEPENDENT_VARIABLES][idx]["type"])

    state_events_list = util.state_behavior_codes(pj[cfg.ETHOGRAM])

    data: list = []
    not_paired: list = []

    if hash(str(self.pj[cfg.OBSERVATIONS])) != self.mem_hash_obs:
        for obs in sorted(list(pj[cfg.OBSERVATIONS].keys())):
            date = pj[cfg.OBSERVATIONS][obs]["date"].replace("T", " ")
            descr = util.eol2space(pj[cfg.OBSERVATIONS][obs][cfg.DESCRIPTION])

            # subjects
            observed_subjects = [cfg.NO_FOCAL_SUBJECT if x == "" else x for x in project_functions.extract_observed_subjects(pj, [obs])]

            subjectsList = ", ".join(observed_subjects)

            # observed time interval
            interval = project_functions.observed_interval(pj[cfg.OBSERVATIONS][obs])
            observed_interval_str = str(round(interval[1] - interval[0], 3))

            # media
            media: str = ""
            if pj[cfg.OBSERVATIONS][obs][cfg.TYPE] == cfg.MEDIA:
                media_list: list = []
                if pj[cfg.OBSERVATIONS][obs][cfg.FILE]:
                    for player in sorted(pj[cfg.OBSERVATIONS][obs][cfg.FILE].keys()):
                        for media in pj[cfg.OBSERVATIONS][obs][cfg.FILE][player]:
                            media_list.append(f"#{player}: {media}")

                if len(media_list) > 8:
                    media = " ".join(media_list)
                else:
                    media = "\n".join(media_list)

            if pj[cfg.OBSERVATIONS][obs][cfg.TYPE] == cfg.LIVE:
                media = cfg.LIVE

            if pj[cfg.OBSERVATIONS][obs][cfg.TYPE] == cfg.IMAGES:
                dir_list: list = []
                for dir_path in pj[cfg.OBSERVATIONS][obs].get(cfg.DIRECTORIES_LIST, []):
                    dir_list.append(dir_path)
                media = "; ".join(dir_list)

            # independent variables
            indepvar: list = []
            if cfg.INDEPENDENT_VARIABLES in pj[cfg.OBSERVATIONS][obs]:
                for var_label in indep_var_header:
                    if var_label in pj[cfg.OBSERVATIONS][obs][cfg.INDEPENDENT_VARIABLES]:
                        indepvar.append(pj[cfg.OBSERVATIONS][obs][cfg.INDEPENDENT_VARIABLES][var_label])
                    else:
                        indepvar.append("")

            # check unpaired events
            ok, _ = project_functions.check_state_events_obs(obs, pj[cfg.ETHOGRAM], pj[cfg.OBSERVATIONS][obs], cfg.HHMMSS)
            if not ok:
                not_paired.append(obs)

            # exhaustivity
            if pj[cfg.OBSERVATIONS][obs][cfg.TYPE] in (cfg.MEDIA, cfg.LIVE):
                # check exhaustivity of observation
                exhaustivity = project_functions.check_observation_exhaustivity(pj[cfg.OBSERVATIONS][obs][cfg.EVENTS], state_events_list)
            elif pj[cfg.OBSERVATIONS][obs][cfg.TYPE] == cfg.IMAGES:
                exhaustivity = project_functions.check_observation_exhaustivity_pictures(pj[cfg.OBSERVATIONS][obs])

            data.append([obs, date, descr, subjectsList, observed_interval_str, str(exhaustivity), media] + indepvar)

        obsList = observations_list.observationsList_widget(
            data, header=fields_list + indep_var_header, column_type=column_type, not_paired=not_paired
        )
        self.data = data
        self.mem_hash_obs = hash(str(self.pj[cfg.OBSERVATIONS]))

    else:
        obsList = observations_list.observationsList_widget(
            self.data, header=fields_list + indep_var_header, column_type=column_type, not_paired=not_paired
        )

    if windows_title:
        obsList.setWindowTitle(windows_title)

    obsList.pbOpen.setVisible(False)
    obsList.pbView.setVisible(False)
    obsList.pbEdit.setVisible(False)
    obsList.pbOk.setVisible(False)
    obsList.pbSelectAll.setVisible(False)
    obsList.pbUnSelectAll.setVisible(False)
    obsList.mode = mode

    if mode == cfg.OPEN:
        obsList.view.setSelectionMode(QAbstractItemView.SingleSelection)
        obsList.pbOpen.setVisible(True)

    if mode == cfg.VIEW:
        obsList.view.setSelectionMode(QAbstractItemView.SingleSelection)
        obsList.pbView.setVisible(True)

    if mode == cfg.EDIT:
        obsList.view.setSelectionMode(QAbstractItemView.SingleSelection)
        obsList.pbEdit.setVisible(True)

    if mode == cfg.SINGLE:
        obsList.view.setSelectionMode(QAbstractItemView.SingleSelection)
        obsList.pbOpen.setVisible(True)
        obsList.pbView.setVisible(True)
        obsList.pbEdit.setVisible(True)

    if mode == cfg.MULTIPLE:
        obsList.view.setSelectionMode(QAbstractItemView.MultiSelection)
        obsList.pbOk.setVisible(True)
        obsList.pbSelectAll.setVisible(True)
        obsList.pbUnSelectAll.setVisible(True)

    if mode == cfg.SELECT1:
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
                if idx.column() == 0:  # first column
                    selected_observations.append(idx.data())

    if result == 0:  # cancel
        resultStr = ""
    if result == 1:  # select
        resultStr = "ok"
    if result == 2:  # open
        resultStr = cfg.OPEN
    if result == 3:  # edit
        resultStr = cfg.EDIT
    if result == 4:  # view
        resultStr = cfg.VIEW

    return resultStr, selected_observations
