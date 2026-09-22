import pytest
from PySide6.QtGui import QKeySequence
from PySide6.QtWidgets import QDialog, QDialogButtonBox

from boris import behavior_shortcut


@pytest.fixture
def shortcut_dialog(qapp):
    dialog = behavior_shortcut.ShortcutDialog(title="Behavior shortcut")
    yield dialog
    dialog.close()
    dialog.deleteLater()
    qapp.processEvents()


def portable_text(sequence):
    return sequence.toString(QKeySequence.SequenceFormat.PortableText)


def test_dialog_starts_empty_with_the_requested_title(shortcut_dialog):
    assert shortcut_dialog.windowTitle() == "Behavior shortcut"
    assert shortcut_dialog._editor.maximumSequenceLength() == 1
    assert shortcut_dialog.shortcut().isEmpty()
    assert shortcut_dialog.shortcutText() == ""
    assert shortcut_dialog.shortcutPortableText() == ""
    assert shortcut_dialog._info_label.text() == "Current shortcut: None"


def test_dialog_initializes_and_updates_shortcuts(shortcut_dialog):
    changed = []
    shortcut_dialog.shortcutChanged.connect(lambda sequence: changed.append(portable_text(sequence)))

    shortcut_dialog.setShortcut("Ctrl+Shift+K")

    assert shortcut_dialog.shortcutPortableText() == "Ctrl+Shift+K"
    assert shortcut_dialog.shortcutText(QKeySequence.SequenceFormat.PortableText) == "Ctrl+Shift+K"
    assert shortcut_dialog._info_label.text() == "Current shortcut: Ctrl+Shift+K"
    assert changed == ["Ctrl+Shift+K"]

    shortcut_dialog.setShortcut(QKeySequence("Alt+F4"))

    assert shortcut_dialog.shortcutPortableText() == "Alt+F4"
    assert shortcut_dialog._info_label.text() == "Current shortcut: Alt+F4"
    assert changed == ["Ctrl+Shift+K", "Alt+F4"]


def test_clear_resets_the_shortcut_and_notifies_listeners(shortcut_dialog):
    shortcut_dialog.setShortcut("F2")
    changed = []
    shortcut_dialog.shortcutChanged.connect(lambda sequence: changed.append(portable_text(sequence)))

    shortcut_dialog.clear()

    assert shortcut_dialog.shortcut().isEmpty()
    assert shortcut_dialog._info_label.text() == "Current shortcut: None"
    assert changed == [""]


def test_clear_notifies_listeners_when_the_shortcut_is_already_empty(shortcut_dialog):
    changed = []
    shortcut_dialog.shortcutChanged.connect(lambda sequence: changed.append(portable_text(sequence)))

    shortcut_dialog.clear()

    assert shortcut_dialog.shortcut().isEmpty()
    assert changed == [""]


def test_dialog_buttons_accept_and_reject(shortcut_dialog):
    shortcut_dialog._buttons.button(QDialogButtonBox.StandardButton.Ok).click()
    assert shortcut_dialog.result() == QDialog.DialogCode.Accepted

    shortcut_dialog.reject()
    assert shortcut_dialog.result() == QDialog.DialogCode.Rejected


@pytest.mark.parametrize(
    "result, accepted",
    [(QDialog.DialogCode.Accepted, True), (QDialog.DialogCode.Rejected, False)],
)
def test_get_shortcut_returns_the_selected_sequence_and_dialog_result(monkeypatch, result, accepted):
    monkeypatch.setattr(behavior_shortcut.ShortcutDialog, "exec", lambda _: result)

    sequence, was_accepted = behavior_shortcut.ShortcutDialog.getShortcut(
        title="Configure behavior shortcut", initial_sequence="Ctrl+S"
    )

    assert portable_text(sequence) == "Ctrl+S"
    assert was_accepted is accepted
