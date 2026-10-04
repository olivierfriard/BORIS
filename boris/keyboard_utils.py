"""
BORIS
Behavioral Observation Research Interactive Software
Copyright 2012-2026 Olivier Friard

This file is part of BORIS.

  BORIS is free software; you can redistribute it and/or modify
  it under the terms of the GNU General Public License as published by
  the Free Software Foundation; either version 3 of the License, or
  any later version.

  BORIS is distributed in the hope that it will be useful,
  but WITHOUT ANY WARRANTY; without even the implied warranty of
  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
  GNU General Public License for more details.

  You should have received a copy of the GNU General Public License
  along with this program; if not see <http://www.gnu.org/licenses/>.

"""

import sys

from PySide6.QtCore import Qt
from PySide6.QtGui import QKeySequence

MACOS_ARROW_KEYS = {
    Qt.Key.Key_Left,
    Qt.Key.Key_Right,
    Qt.Key.Key_Up,
    Qt.Key.Key_Down,
}


def normalize_modifiers(key: Qt.Key, modifiers: Qt.KeyboardModifier) -> Qt.KeyboardModifier:
    """
    macOS reports the arrow keys with the keypad modifier (Num+Left instead of Left)
    and the frame-by-frame and jump shortcuts did not work.
    Remove the keypad modifier of the arrow keys on macOS only.
    """
    if sys.platform.startswith("darwin") and key in MACOS_ARROW_KEYS:
        return Qt.KeyboardModifier(modifiers.value & ~Qt.KeyboardModifier.KeypadModifier.value)
    return modifiers


def key_sequence_from_key(key: Qt.Key, modifiers: Qt.KeyboardModifier) -> QKeySequence:
    """
    returns the key sequence of key with modifiers
    """
    return QKeySequence(int(key) | modifiers.value)
