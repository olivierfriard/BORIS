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
Module containing functions for state events

"""

from decimal import Decimal as dec

from PyQt5.QtWidgets import QMessageBox

from . import config as cfg
from . import dialog, project_functions, select_observations


def check_state_events(self, mode: str = "all") -> None:
    """
    check state events for each subject
    use check_state_events_obs function in project_functions.py

    Args:
        mode (str): current: check current observation / all: ask user to select observations
    """

    tot_out = ""
    if mode == "current":
        if self.observationId:
            _, msg = project_functions.check_state_events_obs(
                self.observationId,
                self.pj[cfg.ETHOGRAM],
                self.pj[cfg.OBSERVATIONS][self.observationId],
                self.timeFormat,
            )
            tot_out = f"Observation: <strong>{self.observationId}</strong><br>{msg}<br><br>"

    if mode == "all":
        if not self.pj[cfg.OBSERVATIONS]:
            QMessageBox.warning(
                self,
                cfg.programName,
                "The project does not contain any observation",
                QMessageBox.Ok | QMessageBox.Default,
                QMessageBox.NoButton,
            )
            return

        # ask user observations to analyze
        _, selectedObservations = select_observations.select_observations(self.pj, mode=cfg.MULTIPLE, windows_title="")
        if not selectedObservations:
            return

        for obsId in sorted(selectedObservations):
            r, msg = project_functions.check_state_events_obs(
                obsId, self.pj[cfg.ETHOGRAM], self.pj[cfg.OBSERVATIONS][obsId], self.timeFormat
            )

            tot_out += f"<strong>{obsId}</strong><br>{msg}<br>"

    results = dialog.Results_dialog()
    results.setWindowTitle("Check state events")
    results.ptText.clear()
    results.ptText.setReadOnly(True)
    results.ptText.appendHtml(tot_out)
    results.exec_()


def fix_unpaired_events(self):
    """
    fix unpaired state events
    """

    if self.observationId:

        r, msg = project_functions.check_state_events_obs(
            self.observationId, self.pj[cfg.ETHOGRAM], self.pj[cfg.OBSERVATIONS][self.observationId]
        )
        if "not PAIRED" not in msg:
            QMessageBox.information(
                None,
                cfg.programName,
                "All state events are already paired",
                QMessageBox.Ok | QMessageBox.Default,
                QMessageBox.NoButton,
            )
            return

        w = dialog.Ask_time(self.timeFormat)
        w.setWindowTitle("Fix UNPAIRED state events")
        w.label.setText("Fix UNPAIRED events at time")

        if w.exec_():
            fix_at_time = w.time_widget.get_time()

            events_to_add = project_functions.fix_unpaired_state_events(
                self.pj[cfg.ETHOGRAM],
                self.pj[cfg.OBSERVATIONS][self.observationId],
                fix_at_time - dec("0.001"),
            )

            if events_to_add:
                self.pj[cfg.OBSERVATIONS][self.observationId][cfg.EVENTS].extend(events_to_add)
                self.project_changed()
                self.pj[cfg.OBSERVATIONS][self.observationId][cfg.EVENTS].sort()
                self.load_tw_events(self.observationId)
                item = self.twEvents.item(
                    [
                        i
                        for i, t in enumerate(self.pj[cfg.OBSERVATIONS][self.observationId][cfg.EVENTS])
                        if t[0] == fix_at_time
                    ][0],
                    0,
                )
                self.twEvents.scrollToItem(item)

    # selected observations
    else:
        _, selected_observations = select_observations.select_observations(self.pj, mode=cfg.MULTIPLE, windows_title="")
        if not selected_observations:
            return

        # check if state events are paired
        out = ""
        not_paired_obs_list = []
        for obs_id in selected_observations:
            r, msg = project_functions.check_state_events_obs(
                obs_id, self.pj[cfg.ETHOGRAM], self.pj[cfg.OBSERVATIONS][obs_id]
            )
            if "NOT PAIRED" in msg.upper():
                fix_at_time = max(x[0] for x in self.pj[cfg.OBSERVATIONS][obs_id][cfg.EVENTS])
                events_to_add = project_functions.fix_unpaired_state_events(
                    self.pj[cfg.ETHOGRAM], self.pj[cfg.OBSERVATIONS][obs_id], fix_at_time
                )
                if events_to_add:
                    events_backup = self.pj[cfg.OBSERVATIONS][obs_id][cfg.EVENTS][:]
                    self.pj[cfg.OBSERVATIONS][obs_id][cfg.EVENTS].extend(events_to_add)

                    # check if modified obs if fixed
                    r, msg = project_functions.check_state_events_obs(
                        obs_id, self.pj[cfg.ETHOGRAM], self.pj[cfg.OBSERVATIONS][obs_id]
                    )
                    if "NOT PAIRED" in msg.upper():
                        out += f"The observation <b>{obs_id}</b> can not be automatically fixed.<br><br>"
                        self.pj[cfg.OBSERVATIONS][obs_id][cfg.EVENTS] = events_backup
                    else:
                        out += f"<b>{obs_id}</b><br>"
                        self.project_changed()
        if out:
            out = "The following observations were modified to fix the unpaired state events:<br><br>" + out
            self.results = dialog.Results_dialog()
            self.results.setWindowTitle(cfg.programName + " - Fixed observations")
            self.results.ptText.setReadOnly(True)
            self.results.ptText.appendHtml(out)
            self.results.pbSave.setVisible(False)
            self.results.pbCancel.setVisible(True)
            self.results.exec_()
        else:
            QMessageBox.information(
                None,
                cfg.programName,
                "All state events are already paired",
                QMessageBox.Ok | QMessageBox.Default,
                QMessageBox.NoButton,
            )
