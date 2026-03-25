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

from PySide6.QtCore import QEvent, Qt, Signal
from PySide6.QtGui import QKeyEvent, QKeySequence
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)


class CapturedShortcut:
    """
    Preserve the exact text for single printable keys while delegating
    non-printable combinations to QKeySequence.
    """

    def __init__(self, sequence=None, exact_text=""):
        if isinstance(sequence, str):
            sequence = QKeySequence.fromString(sequence, QKeySequence.SequenceFormat.PortableText)

        self._sequence = sequence if isinstance(sequence, QKeySequence) else QKeySequence(sequence or "")
        self._exact_text = exact_text

    def toString(self, fmt=QKeySequence.SequenceFormat.NativeText) -> str:
        if self._exact_text:
            return self._exact_text
        return self._sequence.toString(fmt)

    def isEmpty(self) -> bool:
        return not self.toString(QKeySequence.SequenceFormat.PortableText)

    def qkeysequence(self) -> QKeySequence:
        return self._sequence


class ShortcutDialog(QDialog):
    """
    Dialog for shortcut setting using low-level key events.
    """

    shortcutChanged = Signal(object)

    def __init__(self, parent=None, title="Set shortcut", initial_sequence=None):
        super().__init__(parent)

        self.setWindowTitle(title)
        self._shortcut = CapturedShortcut()

        self._title_label = QLabel("Choose a shortcut:", self)

        self._capture_btn = QPushButton("Press a key combination", self)
        self._capture_btn.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self._capture_btn.installEventFilter(self)

        self._info_label = QLabel("Current shortcut: None", self)

        self._clear_btn = QPushButton("Clean", self)

        self._buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel, self)

        top_layout = QHBoxLayout()
        top_layout.addWidget(self._capture_btn)
        top_layout.addWidget(self._clear_btn)

        layout = QVBoxLayout(self)
        layout.addWidget(self._title_label)
        layout.addLayout(top_layout)
        layout.addWidget(self._info_label)
        layout.addWidget(self._buttons)

        if initial_sequence:
            self.setShortcut(initial_sequence)

        self._clear_btn.clicked.connect(self.clear)
        self._buttons.accepted.connect(self.accept)
        self._buttons.rejected.connect(self.reject)

        self._on_shortcut_changed(self.shortcut())

    def eventFilter(self, watched: QWidget, event: QEvent) -> bool:
        if watched is self._capture_btn and event.type() == QEvent.Type.KeyPress:
            self._handle_key_press(event)
            return True
        return super().eventFilter(watched, event)

    def shortcut(self) -> CapturedShortcut:
        return self._shortcut

    def shortcutText(self, fmt=QKeySequence.SequenceFormat.NativeText) -> str:
        return self._shortcut.toString(fmt)

    def shortcutPortableText(self) -> str:
        return self._shortcut.toString(QKeySequence.SequenceFormat.PortableText)

    def setShortcut(self, sequence):
        exact_text = ""
        if isinstance(sequence, str):
            exact_text = sequence if len(sequence) == 1 else ""
            sequence = QKeySequence.fromString(sequence, QKeySequence.SequenceFormat.PortableText)
        self._shortcut = CapturedShortcut(sequence=sequence, exact_text=exact_text)
        self._on_shortcut_changed(self._shortcut)
        self.shortcutChanged.emit(self._shortcut)

    def clear(self):
        self._shortcut = CapturedShortcut()
        self._on_shortcut_changed(self._shortcut)
        self.shortcutChanged.emit(self._shortcut)
        self._capture_btn.setFocus()

    def _handle_key_press(self, event: QKeyEvent) -> None:
        key = event.key()

        if key in (Qt.Key.Key_Control, Qt.Key.Key_Shift, Qt.Key.Key_Alt, Qt.Key.Key_Meta):
            return

        if key == Qt.Key.Key_Escape:
            self.reject()
            return

        modifiers = event.modifiers()
        text = event.text()
        has_non_shift_modifier = bool(modifiers & (Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.AltModifier | Qt.KeyboardModifier.MetaModifier))

        if text and text.isprintable() and not has_non_shift_modifier:
            self._shortcut = CapturedShortcut(QKeySequence(text), exact_text=text)
            self._on_shortcut_changed(self._shortcut)
            self.shortcutChanged.emit(self._shortcut)
            return

        key_value = int(key) | modifiers.value
        sequence = QKeySequence(key_value)

        if sequence.isEmpty():
            return

        self._shortcut = CapturedShortcut(sequence=sequence)
        self._on_shortcut_changed(self._shortcut)
        self.shortcutChanged.emit(self._shortcut)

    def _on_shortcut_changed(self, sequence: CapturedShortcut):
        text = sequence.toString(QKeySequence.SequenceFormat.PortableText)
        self._info_label.setText(f"Current shortcut: {text or 'None'}")
        self._capture_btn.setText(text or "Press a key combination")

    @staticmethod
    def getShortcut(parent=None, title="Set shortcut", initial_sequence=None):
        dialog = ShortcutDialog(
            parent=parent,
            title=title,
            initial_sequence=initial_sequence,
        )
        dialog._capture_btn.setFocus()
        result = dialog.exec()
        return dialog.shortcut(), result == QDialog.DialogCode.Accepted


if __name__ == "__main__":
    app = QApplication([])

    shortcut, accepted = ShortcutDialog.getShortcut(title="Configure shortcut", initial_sequence="")

    if accepted:
        print("Shortcut:", shortcut.toString(QKeySequence.SequenceFormat.NativeText))
        print("Portable:", shortcut.toString(QKeySequence.SequenceFormat.PortableText))
    else:
        print("Cancelled operation")
