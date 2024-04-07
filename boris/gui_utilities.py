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


def set_icons(self):
    """
    set icons of actions
    """

    # menu
    self.actionTime_budget.setIcon(QIcon(":/time_budget"))
    self.actionPlot_events2.setIcon(QIcon(":/plot_events"))
    self.action_advanced_event_filtering.setIcon(QIcon(":/filter"))
    self.actionPreferences.setIcon(QIcon(":/preferences"))

    self.action_obs_list.setIcon(QIcon(":/observations_list"))

    self.actionPlay.setIcon(QIcon(":/play"))
    self.actionReset.setIcon(QIcon(":/reset"))
    self.actionJumpBackward.setIcon(QIcon(":/jump_backward"))
    self.actionJumpForward.setIcon(QIcon(":/jump_forward"))

    self.actionFaster.setIcon(QIcon(":/faster"))
    self.actionSlower.setIcon(QIcon(":/slower"))
    self.actionNormalSpeed.setIcon(QIcon(":/normal_speed"))

    self.actionPrevious.setIcon(QIcon(":/previous"))
    self.actionNext.setIcon(QIcon(":/next"))

    self.actionSnapshot.setIcon(QIcon(":/snapshot"))

    self.actionFrame_backward.setIcon(QIcon(":/frame_backward"))
    self.actionFrame_forward.setIcon(QIcon(":/frame_forward"))
    self.actionCloseObs.setIcon(QIcon(":/close_observation"))
    self.actionCurrent_Time_Budget.setIcon(QIcon(":/time_budget"))
    self.actionPlot_current_observation.setIcon(QIcon(":/plot_events"))

    self.actionPlot_events_in_real_time.setIcon(QIcon(":/plot_real_time"))

    self.actionBehavior_bar_plot.setIcon(QIcon(":/plot_time_budget"))
    self.actionPlot_current_time_budget.setIcon(QIcon(":/plot_time_budget"))
    self.action_geometric_measurements.setIcon(QIcon(":/measurement"))
    self.actionFind_in_current_obs.setIcon(QIcon(":/find"))
    self.actionExplore_project.setIcon(QIcon(":/explore"))
