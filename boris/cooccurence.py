"""
BORIS
Behavioral Observation Research Interactive Software
Copyright 2012-2023 Olivier Friard

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

"""
Module for analyzing the co.occurence of behaviors

"""

from . import config as cfg
from . import select_subj_behav
from . import dialog
from . import utilities as util
from . import select_observations

from . import project_functions, observation_operations

from PyQt5.QtWidgets import QMessageBox
from PyQt5.QtGui import QFont, QTextOption
from . import portion as I
import itertools
from decimal import Decimal as dec


def get_cooccurence(self):
    """
    get co-occurence of selected behaviors
    """

    """
    QMessageBox.warning(
        None,
        cfg.programName,
        (
            f"This function is experimental. Please test it and report any bug at <br>"
            '<a href="https://github.com/olivierfriard/BORIS/issues">'
            "https://github.com/olivierfriard/BORIS/issues</a><br>"
            "or by email (See the About page on the BORIS web site.<br><br>"
            "Thank you for your collaboration!"
        ),
        QMessageBox.Ok | QMessageBox.Default,
        QMessageBox.NoButton,
    )
    """

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

    parameters = select_subj_behav.choose_obs_subj_behav_category(
        self,
        selected_observations,
        flagShowExcludeBehaviorsWoEvents=False,
        window_title="Select the behaviors",
        n_observations=len(selected_observations),
    )

    if parameters == {}:
        return

    if not parameters[cfg.SELECTED_SUBJECTS] or not parameters[cfg.SELECTED_BEHAVIORS]:
        QMessageBox.warning(None, cfg.programName, "Select subject(s) and behavior(s) to analyze")
        return

    print(f"{parameters[cfg.SELECTED_BEHAVIORS]=}")

    marker_subjects = parameters[cfg.SELECTED_SUBJECTS]
    include_marker_modifiers = parameters[cfg.INCLUDE_MODIFIERS]

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

    print(events_interval)

    cooocurence_results: dict = {}

    for obs_id in selected_observations:

        print()
        print(obs_id)

        for subject in parameters[cfg.SELECTED_SUBJECTS]:
            if subject == "No focal subject":
                subj = ""
            else:
                subj = subject

            if subject not in cooocurence_results:
                cooocurence_results[subject] = {}

            # out += f"Subject <b>{subject}</b><br><br>"
            print()
            print(subject)

            for n_combinations in range(2, len(parameters[cfg.SELECTED_BEHAVIORS]) + 1):
                union = I.empty()

                print(f"{n_combinations=}")

                for combination in itertools.combinations(parameters[cfg.SELECTED_BEHAVIORS], n_combinations):
                    print(f"{combination=}")
                    if subj in events_interval[obs_id]:
                        # init
                        if combination[0] in events_interval[obs_id][subj]:
                            union = events_interval[obs_id][subj][combination[0]]
                        else:
                            union = I.empty()

                        print(f"{combination[0]=} {union=}")

                        for combination2 in combination[1:]:
                            if combination2 in events_interval[obs_id][subj]:
                                inter2 = events_interval[obs_id][subj][combination2]
                            else:
                                inter2 = I.empty()

                            print(f"{combination2=} {inter2=}")

                            union &= inter2

                        if combination not in cooocurence_results[subject]:
                            cooocurence_results[subject][combination] = 0

                        print(f"{combination=} {union=}")
                        cooocurence_results[subject][combination] += interval_len(union)
                    else:
                        if combination not in cooocurence_results[subject]:
                            cooocurence_results[subject][combination] = 0
                        cooocurence_results[subject][combination] += 0

                    print()
                    print(f"{cooocurence_results[subject][combination]=}")

                    # duration = f"<b>{interval_len(union)}</b>" if interval_len(union) else "0"
                    # out += f"<b>{'</b> and <b>'.join(combination)}</b>: {duration} s<br>"

                    # print(f"Subject: {subject}    Behaviors {' and '.join(combination)}: {interval_len(union)} s")

                # out += "<br>"

            # out += "<br>"

    print(cooocurence_results)

    out = "<b>Co-occurence of behaviors</b><br><br>"
    for subject in parameters[cfg.SELECTED_SUBJECTS]:
        out += f"<br>Subject <b>{subject}</b><br><br>"
        for combination in cooocurence_results[subject]:
            out += f"<b>{'</b> and <b>'.join(combination)}</b>: {cooocurence_results[subject][combination]} s<br>"

    self.results = dialog.Results_dialog()
    self.results.setWindowTitle("Behaviors co-occurence")
    self.results.ptText.setFont(QFont("Courier", 12))
    self.results.ptText.setWordWrapMode(QTextOption.NoWrap)
    self.results.ptText.setReadOnly(True)
    self.results.ptText.clear()
    self.results.ptText.appendHtml(out)
    self.results.show()
