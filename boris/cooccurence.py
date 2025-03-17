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


Module for analyzing the co-occurence of behaviors

"""

from . import config as cfg
from . import select_subj_behav
from . import dialog
from . import utilities as util
from . import select_observations

from . import project_functions, observation_operations

from PySide6.QtWidgets import QMessageBox
from PySide6.QtGui import QFont, QTextOption
from . import portion as I
import itertools
import logging
from decimal import Decimal as dec


def get_cooccurence(self):
    """
    get co-occurence of selected behaviors
    """

    QMessageBox.warning(
        None,
        cfg.programName,
        (
            "This function is experimental. Please test it and report any bug and suggestions at <br>"
            '<a href="https://github.com/olivierfriard/BORIS/issues">'
            "https://github.com/olivierfriard/BORIS/issues</a><br>"
            "Thank you for your collaboration!"
        ),
        QMessageBox.Ok | QMessageBox.Default,
        QMessageBox.NoButton,
    )

    def interval_len(interval: I) -> dec:
        """ "
        returns duration of an interval or a set of intervals
        """
        if interval.empty:
            return dec(0)
        else:
            return dec(sum([x.upper - x.lower for x in interval]))

    _, selected_observations = select_observations.select_observations2(
        self, cfg.MULTIPLE, windows_title="Select the observations for behaviors co-occurence analysis"
    )

    if not selected_observations:
        return

    # check if coded behaviors are defined in ethogram
    if project_functions.check_coded_behaviors_in_obs_list(self.pj, selected_observations):
        return

    # check if state events are paired
    not_ok, selected_observations = project_functions.check_state_events(self.pj, selected_observations)
    if not_ok or not selected_observations:
        return

    max_media_duration_all_obs, _ = observation_operations.media_duration(self.pj[cfg.OBSERVATIONS], selected_observations)

    start_coding, end_coding, _ = observation_operations.coding_time(self.pj[cfg.OBSERVATIONS], selected_observations)
    # exit with message if events do not have timestamp
    if start_coding.is_nan():
        QMessageBox.critical(
            None,
            cfg.programName,
            ("This function is not available for observations with events that do not have timestamp"),
            QMessageBox.Ok | QMessageBox.Default,
            QMessageBox.NoButton,
        )
        return

    start_interval, end_interval = observation_operations.time_intervals_range(self.pj[cfg.OBSERVATIONS], selected_observations)

    # loop on choose subjects /behaviors until parameters are OK
    while True:
        flag_ok: bool = True
        parameters = select_subj_behav.choose_obs_subj_behav_category(
            self,
            selected_observations,
            start_coding=start_coding,
            end_coding=end_coding,
            # start_interval=start_interval,
            # end_interval=end_interval,
            start_interval=None,
            end_interval=None,
            maxTime=max_media_duration_all_obs,
            n_observations=len(selected_observations),
            show_include_modifiers=False,
            show_exclude_non_coded_behaviors=True,
        )

        if not parameters:  # cancel button pressed
            return

        if not parameters[cfg.SELECTED_SUBJECTS]:
            QMessageBox.warning(None, cfg.programName, "Select the subject(s) to analyze")
            flag_ok = False

        # check number of behaviors (must be <=4)
        if flag_ok and len(parameters[cfg.SELECTED_BEHAVIORS]) > 4:
            QMessageBox.warning(None, cfg.programName, "You cannot select more than 4 behaviors")
            flag_ok = False

        # check number of behaviors (must be > 1)
        if flag_ok and len(parameters[cfg.SELECTED_BEHAVIORS]) < 2:
            QMessageBox.warning(None, cfg.programName, "You must select almost 2 behaviors")
            flag_ok = False

        if flag_ok:
            break

    logging.debug(f"{parameters[cfg.SELECTED_BEHAVIORS]}")

    state_events_list = util.state_behavior_codes(self.pj[cfg.ETHOGRAM])

    events_interval: dict = {}
    mem_events_interval: dict = {}

    for obs_id in selected_observations:
        events_interval[obs_id] = {}
        mem_events_interval[obs_id] = {}

        for event in self.pj[cfg.OBSERVATIONS][obs_id][cfg.EVENTS]:
            if event[cfg.EVENT_SUBJECT_FIELD_IDX] not in events_interval[obs_id]:
                events_interval[obs_id][event[cfg.EVENT_SUBJECT_FIELD_IDX]] = {}
                mem_events_interval[obs_id][event[cfg.EVENT_SUBJECT_FIELD_IDX]] = {}

            if event[cfg.EVENT_BEHAVIOR_FIELD_IDX] not in events_interval[obs_id][event[cfg.EVENT_SUBJECT_FIELD_IDX]]:
                events_interval[obs_id][event[cfg.EVENT_SUBJECT_FIELD_IDX]][event[cfg.EVENT_BEHAVIOR_FIELD_IDX]] = I.empty()
                mem_events_interval[obs_id][event[cfg.EVENT_SUBJECT_FIELD_IDX]][event[cfg.EVENT_BEHAVIOR_FIELD_IDX]] = []

            # state event
            if event[cfg.EVENT_BEHAVIOR_FIELD_IDX] in state_events_list:
                mem_events_interval[obs_id][event[cfg.EVENT_SUBJECT_FIELD_IDX]][event[cfg.EVENT_BEHAVIOR_FIELD_IDX]].append(
                    event[cfg.EVENT_TIME_FIELD_IDX]
                )
                if len(mem_events_interval[obs_id][event[cfg.EVENT_SUBJECT_FIELD_IDX]][event[cfg.EVENT_BEHAVIOR_FIELD_IDX]]) == 2:
                    events_interval[obs_id][event[cfg.EVENT_SUBJECT_FIELD_IDX]][event[cfg.EVENT_BEHAVIOR_FIELD_IDX]] |= I.closedopen(
                        mem_events_interval[obs_id][event[cfg.EVENT_SUBJECT_FIELD_IDX]][event[cfg.EVENT_BEHAVIOR_FIELD_IDX]][0],
                        mem_events_interval[obs_id][event[cfg.EVENT_SUBJECT_FIELD_IDX]][event[cfg.EVENT_BEHAVIOR_FIELD_IDX]][1],
                    )
                    mem_events_interval[obs_id][event[cfg.EVENT_SUBJECT_FIELD_IDX]][event[cfg.EVENT_BEHAVIOR_FIELD_IDX]] = []
            # point event
            else:
                events_interval[obs_id][event[cfg.EVENT_SUBJECT_FIELD_IDX]][event[cfg.EVENT_BEHAVIOR_FIELD_IDX]] |= I.singleton(
                    event[cfg.EVENT_TIME_FIELD_IDX]
                )

    logging.debug(f"events_interval: {events_interval}")

    cooccurence_results: dict = {}

    for obs_id in selected_observations:
        logging.debug(f"obs_id: {obs_id}")

        for subject in parameters[cfg.SELECTED_SUBJECTS]:
            if subject == "No focal subject":
                subj = ""
            else:
                subj = subject

            if subject not in cooccurence_results:
                cooccurence_results[subject] = {}

            logging.debug(f"subject {subject}")

            for n_combinations in range(2, len(parameters[cfg.SELECTED_BEHAVIORS]) + 1):
                union = I.empty()

                logging.debug(f"{n_combinations=}")

                for combination in itertools.combinations(parameters[cfg.SELECTED_BEHAVIORS], n_combinations):
                    logging.debug(f"{combination=}")
                    if subj in events_interval[obs_id]:
                        # init
                        if combination[0] in events_interval[obs_id][subj]:
                            union = events_interval[obs_id][subj][combination[0]]
                        else:
                            union = I.empty()

                        logging.debug(f"{combination[0]=} {union=}")

                        for combination2 in combination[1:]:
                            if combination2 in events_interval[obs_id][subj]:
                                inter2 = events_interval[obs_id][subj][combination2]
                            else:
                                inter2 = I.empty()

                            logging.debug(f"{combination2=} {inter2=}")

                            union &= inter2

                        if combination not in cooccurence_results[subject]:
                            cooccurence_results[subject][combination] = 0

                        logging.debug(f"{combination=} {union=}")
                        cooccurence_results[subject][combination] += interval_len(union)
                    else:
                        if combination not in cooccurence_results[subject]:
                            cooccurence_results[subject][combination] = 0
                        cooccurence_results[subject][combination] += 0

                    logging.debug(f"{cooccurence_results[subject][combination]=}")

    logging.debug(cooccurence_results)

    out = f"<b>Co-occurence of behaviors: {','.join(parameters[cfg.SELECTED_BEHAVIORS])}</b><br><br>"
    for subject in parameters[cfg.SELECTED_SUBJECTS]:
        out += f"<br>Subject <b>{subject}</b><br><br>"
        for combination in cooccurence_results[subject]:
            if parameters[cfg.EXCLUDE_BEHAVIORS] and not cooccurence_results[subject][combination]:
                continue
            duration = f"<b>{cooccurence_results[subject][combination]}</b>" if cooccurence_results[subject][combination] else "0"
            out += f"<b>{'</b> and <b>'.join(combination)}</b>: {duration} s<br>"

    self.results = dialog.Results_dialog()
    self.results.setWindowTitle("Behaviors co-occurence")
    self.results.ptText.setFont(QFont("Courier", 12))
    self.results.ptText.setWordWrapMode(QTextOption.NoWrap)
    self.results.ptText.setReadOnly(True)
    self.results.ptText.clear()
    self.results.ptText.appendHtml(out)
    self.results.show()
