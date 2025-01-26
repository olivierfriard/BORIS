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

import logging
from PySide6.QtGui import QAction
from . import config as cfg
from pathlib import Path


def add_plugins_to_menu(self):
    """
    add plugins to the plugins menu
    """
    for plugin_name in self.config_param.get(cfg.ANALYSIS_PLUGINS, {}):
        logging.debug(f"adding plugin '{plugin_name}' to menu")
        # Create an action for each submenu option
        action = QAction(self, triggered=self.run_plugin)
        action.setText(plugin_name)

        self.menu_plugins.addAction(action)


def get_plugin_name(plugin_path: str):
    """
    get name of plugin
    """
    # search plugin name
    plugin_name = None
    with open(plugin_path, "r") as f_in:
        for line in f_in:
            if line.startswith("__plugin_name__"):
                plugin_name = line.split("=")[1].strip().replace('"', "")
                break
    return plugin_name


def load_plugins(self):
    """
    load selected plugins in analysis menu
    """
    self.menu_plugins.clear()
    self.config_param[cfg.ANALYSIS_PLUGINS] = {}

    # load BORIS plugins
    for file_ in (Path(__file__).parent / "analysis_plugins").glob("*.py"):
        if file_.name == "__init__.py":
            continue
        plugin_name = get_plugin_name(file_)
        if plugin_name is not None and plugin_name not in self.config_param.get(cfg.EXCLUDED_PLUGINS, set()):
            self.config_param[cfg.ANALYSIS_PLUGINS][plugin_name] = str(file_)

    # load personal plugins
    if self.config_param.get(cfg.PERSONAL_PLUGINS_DIR, ""):
        for file_ in Path(self.config_param.get(cfg.PERSONAL_PLUGINS_DIR, "")).glob("*.py"):
            if file_.name == "__init__.py":
                continue
            plugin_name = get_plugin_name(file_)
            if plugin_name is not None and plugin_name not in self.config_param.get(cfg.EXCLUDED_PLUGINS, set()):
                self.config_param[cfg.ANALYSIS_PLUGINS][plugin_name] = str(file_)

    print(f"{self.config_param.get(cfg.ANALYSIS_PLUGINS, {})=}")
