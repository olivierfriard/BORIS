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

from PySide6.QtGui import QAction


def load_plugins(self):
    for action in self.menu_plugins.actions():
        if not action.text().startswith("Load"):
            self.menu_plugins.removeAction(action)

    for option in ["Option 1", "Option 2", "Option 3"]:
        print(option)
        # Create an action for each submenu option
        action = QAction(option, self)
        self.menu_plugins.addAction(action)
