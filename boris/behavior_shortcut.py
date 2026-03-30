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

from PySide6.QtCore import Signal
from PySide6.QtGui import QKeySequence
from PySide6.QtWidgets import (
    QApplication,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QKeySequenceEdit,
    QLabel,
    QPushButton,
    QVBoxLayout,
)


class ShortcutDialog(QDialog):
    """
    Dialog for shortcut setting.
    """

    shortcutChanged = Signal(QKeySequence)

    def __init__(self, parent=None, title="Set shortcut", initial_sequence=None):
        super().__init__(parent)

        self.setWindowTitle(title)

        self._title_label = QLabel("Choose a shortcut:", self)
        self._editor = QKeySequenceEdit(self)
        self._editor.setMaximumSequenceLength(1)

        self._info_label = QLabel("Current shortcut: None", self)

        self._clear_btn = QPushButton("Clean", self)

        self._buttons = QDialogButtonBox(QDialogButtonBox.StandardButton.Ok | QDialogButtonBox.StandardButton.Cancel, self)

        top_layout = QHBoxLayout()
        top_layout.addWidget(self._editor)
        top_layout.addWidget(self._clear_btn)

        layout = QVBoxLayout(self)
        layout.addWidget(self._title_label)
        layout.addLayout(top_layout)
        layout.addWidget(self._info_label)
        layout.addWidget(self._buttons)

        if initial_sequence:
            self.setShortcut(initial_sequence)

        self._editor.keySequenceChanged.connect(self._on_shortcut_changed)
        self._editor.keySequenceChanged.connect(self.shortcutChanged)
        self._clear_btn.clicked.connect(self.clear)
        self._buttons.accepted.connect(self.accept)
        self._buttons.rejected.connect(self.reject)

        self._on_shortcut_changed(self.shortcut())

    def shortcut(self) -> QKeySequence:
        return self._editor.keySequence()

    def shortcutText(self, fmt=QKeySequence.SequenceFormat.NativeText) -> str:
        return self.shortcut().toString(fmt)

    def shortcutPortableText(self) -> str:
        return self.shortcut().toString(QKeySequence.SequenceFormat.PortableText)

    def setShortcut(self, sequence):
        if isinstance(sequence, str):
            sequence = QKeySequence.fromString(sequence, QKeySequence.SequenceFormat.PortableText)
        self._editor.setKeySequence(sequence)
        self._on_shortcut_changed(self._editor.keySequence())

    def clear(self):
        self._editor.clear()
        empty = QKeySequence()
        self._on_shortcut_changed(empty)
        self.shortcutChanged.emit(empty)

    def _on_shortcut_changed(self, sequence: QKeySequence):

        # if len(sequence.toString(QKeySequence.SequenceFormat.PortableText)) == 1:
        #    text = sequence.toString(QKeySequence.SequenceFormat.PortableText).lower()
        # else:
        text = sequence.toString(QKeySequence.SequenceFormat.PortableText)

        self._info_label.setText(f"Current shortcut: {text or 'None'}")

    @staticmethod
    def getShortcut(parent=None, title="Set shortcut", initial_sequence=None):
        dialog = ShortcutDialog(
            parent=parent,
            title=title,
            initial_sequence=initial_sequence,
        )
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

    # app.exec()
