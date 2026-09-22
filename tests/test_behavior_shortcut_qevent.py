import pytest
from PySide6.QtCore import QEvent, Qt
from PySide6.QtGui import QKeyEvent, QKeySequence
from PySide6.QtWidgets import QDialog, QDialogButtonBox, QPushButton

from boris import behavior_shortcut_qevent


def portable_text(shortcut):
    return shortcut.toString(QKeySequence.SequenceFormat.PortableText)


def key_event(key, text="", modifiers=Qt.KeyboardModifier.NoModifier):
    return QKeyEvent(QEvent.Type.KeyPress, key, modifiers, text)


@pytest.fixture
def shortcut_dialog(qapp):
    dialog = behavior_shortcut_qevent.ShortcutDialog(title="Behavior shortcut")
    yield dialog
    dialog.close()
    dialog.deleteLater()
    qapp.processEvents()


def test_captured_shortcut_preserves_exact_printable_text_and_sequences():
    printable = behavior_shortcut_qevent.CapturedShortcut(QKeySequence("A"), exact_text="A")
    sequence = behavior_shortcut_qevent.CapturedShortcut("Ctrl+S")
    empty = behavior_shortcut_qevent.CapturedShortcut()

    assert printable.toString(QKeySequence.SequenceFormat.PortableText) == "A"
    assert portable_text(sequence) == "Ctrl+S"
    assert portable_text(sequence.qkeysequence()) == "Ctrl+S"
    assert empty.isEmpty()
    assert not sequence.isEmpty()


def test_dialog_initializes_sets_and_clears_shortcuts(shortcut_dialog):
    changed = []
    shortcut_dialog.shortcutChanged.connect(lambda shortcut: changed.append(portable_text(shortcut)))

    assert shortcut_dialog.shortcut().isEmpty()
    assert shortcut_dialog._capture_btn.text() == "Press a key combination"

    shortcut_dialog.setShortcut("A")
    assert shortcut_dialog.shortcutPortableText() == "A"
    assert shortcut_dialog.shortcutText(QKeySequence.SequenceFormat.PortableText) == "A"
    assert shortcut_dialog._info_label.text() == "Current shortcut: A"
    assert changed == ["A"]

    shortcut_dialog.setShortcut(QKeySequence("Ctrl+S"))
    assert shortcut_dialog.shortcutPortableText() == "Ctrl+S"
    assert changed == ["A", "Ctrl+S"]

    shortcut_dialog.clear()
    assert shortcut_dialog.shortcut().isEmpty()
    assert shortcut_dialog._info_label.text() == "Current shortcut: None"
    assert shortcut_dialog._capture_btn.text() == "Press a key combination"
    assert changed == ["A", "Ctrl+S", ""]


def test_dialog_initial_sequence_and_buttons(qapp):
    dialog = behavior_shortcut_qevent.ShortcutDialog(title="Configure shortcut", initial_sequence="Alt+F4")
    try:
        assert dialog.windowTitle() == "Configure shortcut"
        assert dialog.shortcutPortableText() == "Alt+F4"
        dialog._buttons.button(QDialogButtonBox.StandardButton.Ok).click()
        assert dialog.result() == QDialog.DialogCode.Accepted
        dialog.reject()
        assert dialog.result() == QDialog.DialogCode.Rejected
    finally:
        dialog.close()
        dialog.deleteLater()
        qapp.processEvents()


def test_event_filter_handles_capture_button_and_other_widgets(shortcut_dialog):
    assert shortcut_dialog.eventFilter(shortcut_dialog._capture_btn, key_event(Qt.Key.Key_A, "a"))
    assert shortcut_dialog.shortcutPortableText() == "a"

    other_button = QPushButton()
    try:
        assert not shortcut_dialog.eventFilter(other_button, QEvent(QEvent.Type.Enter))
    finally:
        other_button.deleteLater()


def test_modifier_keys_are_ignored_and_escape_rejects_the_dialog(shortcut_dialog):
    shortcut_dialog._handle_key_press(key_event(Qt.Key.Key_Control))
    assert shortcut_dialog.shortcut().isEmpty()

    shortcut_dialog._handle_key_press(key_event(Qt.Key.Key_Escape))
    assert shortcut_dialog.result() == QDialog.DialogCode.Rejected


def test_printable_keys_preserve_case_and_shift(shortcut_dialog):
    changed = []
    shortcut_dialog.shortcutChanged.connect(lambda shortcut: changed.append(portable_text(shortcut)))

    shortcut_dialog._handle_key_press(key_event(Qt.Key.Key_A, "A", Qt.KeyboardModifier.ShiftModifier))

    assert shortcut_dialog.shortcutPortableText() == "A"
    assert shortcut_dialog._capture_btn.text() == "A"
    assert changed == ["A"]


@pytest.mark.parametrize(
    "key, modifiers, expected",
    [
        (Qt.Key.Key_S, Qt.KeyboardModifier.ControlModifier, "Ctrl+S"),
        (Qt.Key.Key_F4, Qt.KeyboardModifier.AltModifier, "Alt+F4"),
    ],
)
def test_non_shift_modifier_keys_use_qt_sequences(shortcut_dialog, key, modifiers, expected):
    shortcut_dialog._handle_key_press(key_event(key, "s", modifiers))

    assert shortcut_dialog.shortcutPortableText() == expected


def test_empty_qt_sequence_is_ignored(monkeypatch, shortcut_dialog):
    class EmptySequence:
        def __init__(self, *_):
            pass

        def isEmpty(self):
            return True

    monkeypatch.setattr(behavior_shortcut_qevent, "QKeySequence", EmptySequence)

    shortcut_dialog._handle_key_press(key_event(Qt.Key.Key_S, "", Qt.KeyboardModifier.ControlModifier))
    monkeypatch.undo()

    assert shortcut_dialog.shortcut().isEmpty()


@pytest.mark.parametrize(
    "result, accepted",
    [(QDialog.DialogCode.Accepted, True), (QDialog.DialogCode.Rejected, False)],
)
def test_get_shortcut_returns_the_selected_sequence_and_result(monkeypatch, result, accepted):
    monkeypatch.setattr(behavior_shortcut_qevent.ShortcutDialog, "exec", lambda _: result)

    shortcut, was_accepted = behavior_shortcut_qevent.ShortcutDialog.getShortcut(initial_sequence="Ctrl+K")

    assert portable_text(shortcut) == "Ctrl+K"
    assert was_accepted is accepted
