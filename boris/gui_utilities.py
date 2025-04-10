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

import pathlib as pl
import logging
from PySide6.QtCore import QSettings
from PySide6.QtWidgets import QWidget, QApplication
from PySide6.QtGui import QIcon


def theme_mode() -> str:
    """
    return the theme mode (dark or light) of the OS
    """
    palette = QApplication.instance().palette()
    color = palette.window().color()
    return "dark" if color.value() < 128 else "light"  # Dark mode if the color value is less than 128


def save_geometry(widget: QWidget, widget_name: str):
    """
    save window geometry in ini file
    """

    ini_file_path = pl.Path.home() / pl.Path(".boris")
    if ini_file_path.is_file():
        try:
            settings = QSettings(str(ini_file_path), QSettings.IniFormat)
            settings.setValue(f"{widget_name} geometry", widget.saveGeometry())
        except Exception:
            logging.warning(f"error during saving {widget_name} geometry")


def restore_geometry(widget: QWidget, widget_name: str, default_width_height):
    """
    restore window geometry in ini file
    """

    def default_resize(widget, default_width_height):
        if default_width_height != (0, 0):
            try:
                widget.resize(default_width_height[0], default_width_height[1])
            except Exception:
                logging.warning("Error during restoring default")

    logging.debug(f"restore geometry function for {widget_name}")
    try:
        ini_file_path = pl.Path.home() / pl.Path(".boris")
        if ini_file_path.is_file():
            settings = QSettings(str(ini_file_path), QSettings.IniFormat)
            print(settings.value(f"{widget_name} geometry"))
            widget.restoreGeometry(settings.value(f"{widget_name} geometry"))
            logging.debug(f"geometry restored for {widget_name}  {settings.value(f'{widget_name} geometry')}")
        else:
            default_resize(widget, default_width_height)
    except Exception:
        logging.warning(f"error during restoring {widget_name} geometry")
        default_resize(widget, default_width_height)


def set_icons(self, theme_mode: str) -> None:
    """
    set icons of actions
    """

    # menu
    self.action_obs_list.setIcon(QIcon(f":/observations_list_{theme_mode}"))

    self.actionTime_budget.setIcon(QIcon(f":/time_budget_{theme_mode}"))
    self.actionPlot_events2.setIcon(QIcon(f":/plot_events_{theme_mode}"))
    self.action_advanced_event_filtering.setIcon(QIcon(f":/filter_{theme_mode}"))

    self.actionPreferences.setIcon(QIcon(f":/preferences_{theme_mode}"))

    self.actionPlay.setIcon(QIcon(f":/play_{theme_mode}"))
    self.actionReset.setIcon(QIcon(f":/reset_{theme_mode}"))
    self.actionJumpBackward.setIcon(QIcon(f":/jump_backward_{theme_mode}"))
    self.actionJumpForward.setIcon(QIcon(f":/jump_forward_{theme_mode}"))

    self.actionFaster.setIcon(QIcon(f":/faster_{theme_mode}"))
    self.actionSlower.setIcon(QIcon(f":/slower_{theme_mode}"))
    self.actionNormalSpeed.setIcon(QIcon(f":/normal_speed_{theme_mode}"))

    self.actionPrevious.setIcon(QIcon(f":/previous_{theme_mode}"))
    self.actionNext.setIcon(QIcon(f":/next_{theme_mode}"))

    self.actionSnapshot.setIcon(QIcon(f":/snapshot_{theme_mode}"))

    self.actionFrame_backward.setIcon(QIcon(f":/frame_backward_{theme_mode}"))
    self.actionFrame_forward.setIcon(QIcon(f":/frame_forward_{theme_mode}"))
    self.actionCloseObs.setIcon(QIcon(f":/close_observation_{theme_mode}"))
    self.actionCurrent_Time_Budget.setIcon(QIcon(f":/time_budget_{theme_mode}"))
    self.actionPlot_current_observation.setIcon(QIcon(f":/plot_events_{theme_mode}"))

    self.actionPlot_events_in_real_time.setIcon(QIcon(f":/plot_real_time_{theme_mode}"))

    self.actionBehavior_bar_plot.setIcon(QIcon(f":/plot_time_budget_{theme_mode}"))
    self.actionPlot_current_time_budget.setIcon(QIcon(f":/plot_time_budget_{theme_mode}"))
    self.action_geometric_measurements.setIcon(QIcon(f":/measurement_{theme_mode}"))
    self.actionFind_in_current_obs.setIcon(QIcon(f":/find_{theme_mode}"))
    self.actionExplore_project.setIcon(QIcon(f":/explore_{theme_mode}"))


def resize_center(app, window, width: int, height: int) -> None:
    """
    resize and center window
    """
    window.resize(width, height)
    screen_geometry = app.primaryScreen().geometry()
    if window.height() > screen_geometry.height():
        window.resize(window.width(), int(screen_geometry.height() * 0.8))
    if window.width() > screen_geometry.width():
        window.resize(screen_geometry.width(), window.height())
    # center
    center_x = (screen_geometry.width() - window.width()) // 2
    center_y = (screen_geometry.height() - window.height()) // 2

    window.move(center_x, center_y)
