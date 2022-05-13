"""
BORIS
Behavioral Observation Research Interactive Software
Copyright 2012-2022 Olivier Friard

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
Module for analyzing the latency of behaviors after another behavior(s) (marker)

"""

from . import config as cfg
from . import utilities as util
from . import select_subj_behav
from . import dialog
from . import select_observations

from PyQt5.QtWidgets import QMessageBox


def get_latency(self):
    """
    get latency (time after marker/stimulus)
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

    SUBJECT, BEHAVIOR, MODIFIERS = 0, 1, 2

    _, selected_observations = select_observations.select_observations(
        self.pj, cfg.SINGLE, windows_title="Select one observation for latency analysis"
    )
    if not selected_observations:
        return

    parameters = select_subj_behav.choose_obs_subj_behav_category(
        self,
        selected_observations,
        flagShowExcludeBehaviorsWoEvents=False,
        window_title="Select the marker behaviors (stimulus)",
    )
    if not parameters[cfg.SELECTED_SUBJECTS] or not parameters[cfg.SELECTED_BEHAVIORS]:
        return
    marker_behaviors = parameters[cfg.SELECTED_BEHAVIORS]
    marker_subjects = parameters[cfg.SELECTED_SUBJECTS]
    include_marker_modifiers = parameters[cfg.INCLUDE_MODIFIERS]

    print(f"{marker_behaviors=} {marker_subjects=} {include_marker_modifiers=}")

    parameters = select_subj_behav.choose_obs_subj_behav_category(
        self, selected_observations, flagShowExcludeBehaviorsWoEvents=False, window_title="Select the latency behaviors"
    )
    if not parameters[cfg.SELECTED_SUBJECTS] or not parameters[cfg.SELECTED_BEHAVIORS]:
        return
    behaviors = parameters[cfg.SELECTED_BEHAVIORS]
    latency_subjects = parameters[cfg.SELECTED_SUBJECTS]
    include_latency_modifiers = parameters[cfg.INCLUDE_MODIFIERS]

    print(f"{behaviors=} {latency_subjects=} {include_latency_modifiers=}")

    results = {}
    for obs_id in selected_observations:
        print(f"{obs_id=}")

        grouped_events = util.group_events(self.pj, obs_id, include_modifiers=True)
        print(f"{grouped_events=}")
        print()

        for marker_behavior in marker_behaviors:

            print(f"{marker_behavior=}")

            marker_idx = 0

            for sbm_marker in grouped_events:

                if all(
                    (
                        sbm_marker[BEHAVIOR] == marker_behavior,
                        any(
                            (
                                sbm_marker[SUBJECT] in marker_subjects,
                                all((sbm_marker[SUBJECT] == "", cfg.NO_FOCAL_SUBJECT in marker_subjects)),
                            )
                        ),
                    )
                ):

                    for idx1, event1 in enumerate(grouped_events[sbm_marker]):

                        marker_idx += 1
                        print(f"{marker_idx=}")

                        if not include_marker_modifiers:
                            marker_key = sbm_marker[:2]  # remove modifier
                        else:
                            marker_key = sbm_marker

                        # add time
                        marker_key = (grouped_events[sbm_marker][idx1][0],) + marker_key + (marker_idx,)
                        if marker_key not in results:
                            results[marker_key] = {}

                        if idx1 < len(grouped_events[sbm_marker]) - 1:
                            limit = grouped_events[sbm_marker][idx1 + 1][0]
                        else:
                            limit = self.pj[cfg.OBSERVATIONS][obs_id][cfg.EVENTS][-1][cfg.EVENT_TIME_FIELD_IDX] + 1

                        for sbm_latency in grouped_events:
                            if all(
                                (
                                    sbm_latency[BEHAVIOR] in behaviors,
                                    any(
                                        (
                                            sbm_latency[SUBJECT] in latency_subjects,
                                            all((sbm_latency[SUBJECT] == "", cfg.NO_FOCAL_SUBJECT in latency_subjects)),
                                        )
                                    ),
                                )
                            ):
                                for event in grouped_events[sbm_latency]:
                                    if event[0] >= event1[0] and event[0] < limit:

                                        if not include_latency_modifiers:
                                            latency_key = sbm_latency[:2]  # remove modifier
                                        else:
                                            latency_key = sbm_latency

                                        # print(latency_key, " after ", marker_key, ":", event[0] - event1[0])

                                        if latency_key not in results[marker_key]:
                                            results[marker_key][latency_key] = []
                                        results[marker_key][latency_key].append(event[0] - event1[0])

    print(f"{results=}")

    out = ""

    for marker in sorted(results.keys()):

        subject = cfg.NO_FOCAL_SUBJECT if marker[1] == "" else marker[1]
        if include_marker_modifiers:
            out += f"Marker: <b>{marker[2]}</b> at {marker[0]} s (subject: {subject} - modifiers: {marker[-1]})<br><br>"
        else:
            out += f"Marker: <b>{marker[2]}</b> at {marker[0]} s (subject: {subject})<br><br>"
        for behav in results[marker]:
            subject = cfg.NO_FOCAL_SUBJECT if behav[SUBJECT] == "" else behav[SUBJECT]
            if include_latency_modifiers:
                out += f"\nLatency for behavior: <b>{behav[BEHAVIOR]}</b> (subject: {subject} - modifiers: {behav[MODIFIERS]})<br>"
            else:
                out += f"\nLatency for behavior:  <b>{behav[BEHAVIOR]}</b> (subject: {subject})<br>"

            out += "first occurrence: "
            out += f"{sorted(results[marker][behav])[0]} s<br>"
            out += f"all occurrences: "

            out += ", ".join([f"{x} s" for x in sorted(results[marker][behav])])
            out += "<br><br>"

        out += "<br><br>"

    self.results = dialog.ResultsWidget()
    self.results.setWindowTitle("Latency")
    self.results.ptText.clear()
    self.results.ptText.setReadOnly(True)
    self.results.ptText.appendHtml(out)
    self.results.show()
