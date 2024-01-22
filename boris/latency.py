"""
BORIS
Behavioral Observation Research Interactive Software
Copyright 2012-2024 Olivier Friard

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


Module for analyzing the latency of behaviors after another behavior(s) (marker)

"""

from . import config as cfg
from . import select_subj_behav
from . import dialog
from . import select_observations
from . import project_functions, observation_operations

from PyQt5.QtWidgets import QMessageBox


def get_latency(self):
    """
    get latency (time after marker/stimulus)
    """

    QMessageBox.warning(
        None,
        cfg.programName,
        (
            "This function is experimental. Please test it and report any bug at <br>"
            '<a href="https://github.com/olivierfriard/BORIS/issues">'
            "https://github.com/olivierfriard/BORIS/issues</a><br>"
            "Thank you for your collaboration!"
        ),
        QMessageBox.Ok | QMessageBox.Default,
        QMessageBox.NoButton,
    )

    SUBJECT, BEHAVIOR, MODIFIERS = 0, 1, 2

    _, selected_observations = select_observations.select_observations2(
        self, cfg.SELECT1, windows_title="Select one observation for latency analysis"
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

    parameters: dict = select_subj_behav.choose_obs_subj_behav_category(
        self,
        selected_observations,
        flagShowExcludeBehaviorsWoEvents=False,
        window_title="Select the marker behaviors (stimulus)",
        n_observations=len(selected_observations),
    )

    if parameters == {}:
        return

    if not parameters[cfg.SELECTED_SUBJECTS] or not parameters[cfg.SELECTED_BEHAVIORS]:
        QMessageBox.warning(None, cfg.programName, "Select subject(s) and behavior(s) to analyze")
        return

    marker_behaviors = parameters[cfg.SELECTED_BEHAVIORS]
    marker_subjects = parameters[cfg.SELECTED_SUBJECTS]
    include_marker_modifiers = parameters[cfg.INCLUDE_MODIFIERS]

    print(f"{marker_behaviors=} {marker_subjects=} {include_marker_modifiers=}")

    parameters: dict = select_subj_behav.choose_obs_subj_behav_category(
        self, selected_observations, flagShowExcludeBehaviorsWoEvents=False, window_title="Select the latency behaviors"
    )
    if not parameters[cfg.SELECTED_SUBJECTS] or not parameters[cfg.SELECTED_BEHAVIORS]:
        return
    latency_behaviors = parameters[cfg.SELECTED_BEHAVIORS]
    latency_subjects = parameters[cfg.SELECTED_SUBJECTS]
    include_latency_modifiers = parameters[cfg.INCLUDE_MODIFIERS]

    print(f"{latency_behaviors=} {latency_subjects=} {include_latency_modifiers=}")

    results: dict = {}
    for obs_id in selected_observations:
        print(f"{obs_id=}")

        events_with_status = project_functions.events_start_stop(
            self.pj[cfg.ETHOGRAM],
            self.pj[cfg.OBSERVATIONS][obs_id][cfg.EVENTS],
            self.pj[cfg.OBSERVATIONS][obs_id][cfg.TYPE],
        )

        print(f"{events_with_status=}")

        for idx, event in enumerate(events_with_status):
            print(f"{event=}")

            print(f"{event[cfg.EVENT_STATUS_FIELD_IDX]=}")

            print(f"{event[cfg.EVENT_BEHAVIOR_FIELD_IDX]=}")

            print(f"{event[cfg.EVENT_SUBJECT_FIELD_IDX]=}")

            if all(
                (
                    event[cfg.EVENT_STATUS_FIELD_IDX] in (cfg.START, cfg.POINT),
                    event[cfg.EVENT_BEHAVIOR_FIELD_IDX] in marker_behaviors,
                    any(
                        (
                            event[cfg.EVENT_SUBJECT_FIELD_IDX] in marker_subjects,
                            all((event[cfg.EVENT_SUBJECT_FIELD_IDX] == "", cfg.NO_FOCAL_SUBJECT in marker_subjects)),
                        )
                    ),
                )
            ):
                if include_marker_modifiers:
                    marker = event[cfg.EVENT_TIME_FIELD_IDX : cfg.EVENT_MODIFIER_FIELD_IDX + 1]
                else:
                    marker = event[cfg.EVENT_TIME_FIELD_IDX : cfg.EVENT_BEHAVIOR_FIELD_IDX + 1]

                print(f"{marker=}")

                if marker not in results:
                    results[marker] = {}

                for event2 in events_with_status[idx + 1 :]:
                    if all(
                        (
                            event2[cfg.EVENT_STATUS_FIELD_IDX] in (cfg.START, cfg.POINT),
                            event2[cfg.EVENT_BEHAVIOR_FIELD_IDX] in latency_behaviors,
                            any(
                                (
                                    event2[cfg.EVENT_SUBJECT_FIELD_IDX] in latency_subjects,
                                    all(
                                        (
                                            event2[cfg.EVENT_SUBJECT_FIELD_IDX] == "",
                                            cfg.NO_FOCAL_SUBJECT in latency_subjects,
                                        )
                                    ),
                                )
                            ),
                        )
                    ):
                        print(event, event2)
                        if include_latency_modifiers:
                            latency = event2[cfg.EVENT_SUBJECT_FIELD_IDX : cfg.EVENT_MODIFIER_FIELD_IDX + 1]
                        else:
                            latency = event2[cfg.EVENT_SUBJECT_FIELD_IDX : cfg.EVENT_BEHAVIOR_FIELD_IDX + 1]

                        # print(f"{marker=}")
                        print(f"{latency=}")
                        if latency not in results[marker]:
                            results[marker][latency] = []
                        results[marker][latency].append(event2[cfg.EVENT_TIME_FIELD_IDX] - event[cfg.EVENT_TIME_FIELD_IDX])

                        print(f"{results[marker][latency]=}")

                    # check if new marker
                    if all(
                        (
                            event2[cfg.EVENT_STATUS_FIELD_IDX] in (cfg.START, cfg.POINT),
                            event2[cfg.EVENT_BEHAVIOR_FIELD_IDX] in marker_behaviors,
                            any(
                                (
                                    event2[cfg.EVENT_SUBJECT_FIELD_IDX] in marker_subjects,
                                    all(
                                        (
                                            event2[cfg.EVENT_SUBJECT_FIELD_IDX] == "",
                                            cfg.NO_FOCAL_SUBJECT in marker_subjects,
                                        )
                                    ),
                                )
                            ),
                        )
                    ):
                        break

        break

    # print()
    # import pprint
    # pprint.pprint(results)

    out = ""

    for marker in sorted(results.keys()):
        subject = cfg.NO_FOCAL_SUBJECT if marker[cfg.EVENT_SUBJECT_FIELD_IDX] == "" else marker[1]
        if include_marker_modifiers:
            out += f"Marker: <b>{marker[cfg.EVENT_BEHAVIOR_FIELD_IDX]}</b> at {marker[cfg.EVENT_TIME_FIELD_IDX]} s (subject: {subject} - modifiers: {marker[cfg.EVENT_MODIFIER_FIELD_IDX]})<br><br>"
        else:
            out += f"Marker: <b>{marker[cfg.EVENT_BEHAVIOR_FIELD_IDX]}</b> at {marker[cfg.EVENT_TIME_FIELD_IDX]} s (subject: {subject})<br><br>"
        for behav in results[marker]:
            subject = cfg.NO_FOCAL_SUBJECT if behav[SUBJECT] == "" else behav[SUBJECT]
            if include_latency_modifiers:
                out += f"\nLatency for behavior: <b>{behav[BEHAVIOR]}</b> (subject: {subject} - modifiers: {behav[MODIFIERS]})<br>"
            else:
                out += f"\nLatency for behavior:  <b>{behav[BEHAVIOR]}</b> (subject: {subject})<br>"

            out += "first occurrence: "
            out += f"{sorted(results[marker][behav])[0]} s<br>"
            out += "all occurrences: "

            out += ", ".join([f"{x} s" for x in sorted(results[marker][behav])])
            out += "<br><br>"

        out += "<br><br>"

    self.results = dialog.Results_dialog()
    self.results.setWindowTitle("Latency")
    self.results.ptText.clear()
    self.results.ptText.appendHtml(out)
    self.results.show()
