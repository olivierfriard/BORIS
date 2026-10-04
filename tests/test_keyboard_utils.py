"""
module for testing keyboard_utils.py (arrow keys reported with the keypad modifier on macOS)

pytest -s -vv test_keyboard_utils.py
"""

import os
import sys

from PySide6.QtCore import Qt

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from boris import keyboard_utils


def test_macos_arrow_keypad_modifier_is_removed(monkeypatch):
    monkeypatch.setattr(keyboard_utils.sys, "platform", "darwin")
    for key, text in ((Qt.Key.Key_Left, "Left"), (Qt.Key.Key_Right, "Right"), (Qt.Key.Key_Up, "Up"), (Qt.Key.Key_Down, "Down")):
        modifiers = keyboard_utils.normalize_modifiers(key, Qt.KeyboardModifier.KeypadModifier)
        assert modifiers == Qt.KeyboardModifier.NoModifier
        assert keyboard_utils.key_sequence_from_key(key, modifiers).toString() == text


def test_macos_arrow_keeps_other_modifiers(monkeypatch):
    monkeypatch.setattr(keyboard_utils.sys, "platform", "darwin")
    modifiers = keyboard_utils.normalize_modifiers(Qt.Key.Key_Left, Qt.KeyboardModifier.KeypadModifier | Qt.KeyboardModifier.ShiftModifier)
    assert modifiers == Qt.KeyboardModifier.ShiftModifier
    assert keyboard_utils.key_sequence_from_key(Qt.Key.Key_Left, modifiers).toString() == "Shift+Left"


def test_macos_keypad_digit_keeps_keypad_modifier(monkeypatch):
    monkeypatch.setattr(keyboard_utils.sys, "platform", "darwin")
    modifiers = keyboard_utils.normalize_modifiers(Qt.Key.Key_1, Qt.KeyboardModifier.KeypadModifier)
    assert modifiers == Qt.KeyboardModifier.KeypadModifier


def test_non_macos_keeps_keypad_modifier(monkeypatch):
    monkeypatch.setattr(keyboard_utils.sys, "platform", "linux")
    modifiers = keyboard_utils.normalize_modifiers(Qt.Key.Key_Left, Qt.KeyboardModifier.KeypadModifier)
    assert modifiers == Qt.KeyboardModifier.KeypadModifier
    assert keyboard_utils.key_sequence_from_key(Qt.Key.Key_Left, modifiers).toString() == "Num+Left"
