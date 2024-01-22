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
"""

import pathlib as pl
import logging
from PyQt5.QtCore import QSettings
from PyQt5.QtWidgets import QWidget
from PyQt5.QtGui import QIcon


def save_geometry(widget: QWidget, widget_name: str):
    """
    save window geometry in ini file
    """

    try:
        ini_file_path = pl.Path.home() / pl.Path(".boris")
        if ini_file_path.is_file():
            settings = QSettings(str(ini_file_path), QSettings.IniFormat)
            settings.setValue(f"{widget_name} geometry", widget.saveGeometry())
    except Exception:
        logging.warning(f"error during saving {widget_name} geometry")


def restore_geometry(widget: QWidget, widget_name: str, default_geometry):
    """
    restore window geometry in ini file
    """

    try:
        ini_file_path = pl.Path.home() / pl.Path(".boris")
        if ini_file_path.is_file():
            settings = QSettings(str(ini_file_path), QSettings.IniFormat)
            widget.restoreGeometry(settings.value(f"{widget_name} geometry"))
    except Exception:
        logging.warning(f"error during restoring {widget_name} geometry")
        if default_geometry != (0, 0):
            try:
                widget.resize(default_geometry[0], default_geometry[1])
            except Exception:
                logging.warning("Error during restoring default")


def set_icons(self, mode: str):
    """
    disabled: #5f5f5f
    dark: #DFE1E2
    light: #000000
    """

    suffix = mode
    # menu
    self.actionTime_budget.setIcon(QIcon(f":/time_budget_fa_{suffix}"))
    self.actionPlot_events2.setIcon(QIcon(f":/plot_events_fa_{suffix}"))
    self.action_advanced_event_filtering.setIcon(QIcon(f":/filter_fa_{suffix}"))
    self.actionPreferences.setIcon(QIcon(f":/preferences_fa_{suffix}"))

    # toolbar
    """
    if mode == "disabled" and not self.action_obs_list.isEnabled():
        self.action_obs_list.setIcon(QIcon(":/observations_list_fa_disabled"))
    """

    self.action_obs_list.setIcon(QIcon(f":/observations_list_fa_{suffix}"))

    self.actionPlay.setIcon(QIcon(f":/play_fa_{suffix}"))
    self.actionReset.setIcon(QIcon(f":/reset_fa_{suffix}"))
    self.actionJumpBackward.setIcon(QIcon(f":/jump_backward_fa_{suffix}"))
    self.actionJumpForward.setIcon(QIcon(f":/jump_forward_fa_{suffix}"))

    self.actionFaster.setIcon(QIcon(f":/faster_fa_{suffix}"))
    self.actionSlower.setIcon(QIcon(f":/slower_fa_{suffix}"))
    self.actionNormalSpeed.setIcon(QIcon(f":/normal_speed_fa_{suffix}"))

    self.actionPrevious.setIcon(QIcon(f":/previous_fa_{suffix}"))
    self.actionNext.setIcon(QIcon(f":/next_fa_{suffix}"))

    self.actionSnapshot.setIcon(QIcon(f":/snapshot_fa_{suffix}"))

    self.actionFrame_backward.setIcon(QIcon(f":/frame_backward_fa_{suffix}"))
    self.actionFrame_forward.setIcon(QIcon(f":/frame_forward_fa_{suffix}"))
    self.actionCloseObs.setIcon(QIcon(f":/close_observation_fa_{suffix}"))
    self.actionCurrent_Time_Budget.setIcon(QIcon(f":/time_budget_fa_{suffix}"))
    self.actionPlot_current_observation.setIcon(QIcon(f":/plot_events_fa_{suffix}"))

    self.actionPlot_events_in_real_time.setIcon(QIcon(f":/plot_real_time_fa_{suffix}"))

    self.actionBehavior_bar_plot.setIcon(QIcon(f":/plot_time_budget_fa_{suffix}"))
    self.actionPlot_current_time_budget.setIcon(QIcon(f":/plot_time_budget_fa_{suffix}"))
    self.action_geometric_measurements.setIcon(QIcon(f":/measurement_fa_{suffix}"))
    self.actionFind_in_current_obs.setIcon(QIcon(f":/find_fa_{suffix}"))
    self.actionExplore_project.setIcon(QIcon(f":/explore_fa_{suffix}"))
