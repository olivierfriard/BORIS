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


def load_plugins(self):
    """
    load selected plugins in analysis menu
    """
    self.menu_plugins.clear()

    for plugin in self.config_param.get(cfg.ANALYSIS_PLUGINS, []):
        logging.debug(f"adding plugin {plugin} to menu")
        # Create an action for each submenu option
        action = QAction(self, triggered=self.run_plugin)
        action.setText(plugin)

        self.menu_plugins.addAction(action)
