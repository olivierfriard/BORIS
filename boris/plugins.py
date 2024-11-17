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

import logging
from PySide6.QtGui import QAction
from . import config as cfg
from pathlib import Path


def load_plugins(self):
    """
    load selected plugins in analysis menu
    """
    self.menu_plugins.clear()
    self.config_param[cfg.ANALYSIS_PLUGINS] = {}

    for file_ in (Path(__file__).parent / "analysis_plugins").glob("*.py"):
        if file_.name == "__init__.py":
            continue
        with open(file_, "r") as f_in:
            content = f_in.readlines()
        plugin_name: str = ""
        for line in content:
            if line.startswith("__plugin_name__"):
                plugin_name = line.split("=")[1].strip().replace('"', "")
                break
        if plugin_name and plugin_name not in self.config_param.get(cfg.EXCLUDED_PLUGINS, set()):
            self.config_param[cfg.ANALYSIS_PLUGINS][plugin_name] = file_.stem

    print(f"{self.config_param.get(cfg.ANALYSIS_PLUGINS, {})=}")

    for plugin_name in self.config_param.get(cfg.ANALYSIS_PLUGINS, {}):
        logging.debug(f"adding plugin '{plugin_name}' to menu")
        # Create an action for each submenu option
        action = QAction(self, triggered=self.run_plugin)
        action.setText(plugin_name)

        self.menu_plugins.addAction(action)
