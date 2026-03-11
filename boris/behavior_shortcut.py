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
    Dialog per acquisire/modificare uno shortcut.
    """

    shortcutChanged = Signal(QKeySequence)

    def __init__(self, parent=None, title="Imposta scorciatoia", initial_sequence=None):
        super().__init__(parent)

        self.setWindowTitle(title)

        self._title_label = QLabel("Scegli una scorciatoia:", self)
        self._editor = QKeySequenceEdit(self)
        self._editor.setMaximumSequenceLength(1)

        self._info_label = QLabel("Shortcut corrente: nessuno", self)

        self._clear_btn = QPushButton("Pulisci", self)

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
        text = sequence.toString(QKeySequence.SequenceFormat.NativeText)
        self._info_label.setText(f"Shortcut corrente: {text or 'nessuno'}")

    @staticmethod
    def getShortcut(parent=None, title="Imposta scorciatoia", initial_sequence=None):
        dialog = ShortcutDialog(
            parent=parent,
            title=title,
            initial_sequence=initial_sequence,
        )
        result = dialog.exec()
        return dialog.shortcut(), result == QDialog.DialogCode.Accepted


if __name__ == "__main__":
    app = QApplication([])

    shortcut, accepted = ShortcutDialog.getShortcut(title="Configura shortcut", initial_sequence="Ctrl+A")

    if accepted:
        print("Shortcut scelto:", shortcut.toString(QKeySequence.SequenceFormat.NativeText))
        print("Portable:", shortcut.toString(QKeySequence.SequenceFormat.PortableText))
    else:
        print("Operazione annullata")

    app.exec()
