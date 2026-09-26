"""Tests for the modifier editor dialog."""

import json

import pytest
from PySide6.QtWidgets import QWidget

from boris import add_modifier, config


@pytest.fixture
def modifier_dialog(qapp):
    editor = add_modifier.addModifierDialog("", subjects=[("Alice", "A"), ("Bob", "")], ask_at_stop_enabled=True)
    editor.tabMem = -1
    editor.itemPositionMem = -1
    yield editor
    editor.close()
    editor.deleteLater()
    qapp.processEvents()


def values(editor):
    return [editor.lwModifiers.item(index).text() for index in range(editor.lwModifiers.count())]


def test_initialization_from_json_and_empty_dialog(qapp, modifier_dialog):
    assert modifier_dialog.tabWidgetModifiersSets.count() == 0
    assert modifier_dialog.pb_add_subjects.isEnabled()

    source = {
        "0": {"name": "Locations", "description": "Where", "type": config.SINGLE_SELECTION, "values": ["North"]},
        "1": {
            "name": "Phase",
            "description": "",
            "type": config.MULTI_SELECTION,
            "ask at stop": True,
            "values": ["Start", "Stop"],
        },
    }
    editor = add_modifier.addModifierDialog(json.dumps(source), ask_at_stop_enabled=True)
    try:
        assert editor.tabWidgetModifiersSets.count() == 2
        assert editor.cb_ask_at_stop.isChecked()
        assert editor.modifiers_sets_dict == source
    finally:
        editor.close()
        editor.deleteLater()
        qapp.processEvents()


def test_add_set_and_update_metadata_and_type(modifier_dialog):
    modifier_dialog.add_set_of_modifiers()

    assert modifier_dialog.tabWidgetModifiersSets.count() == 1
    assert modifier_dialog.modifiers_sets_dict["0"]["type"] == config.SINGLE_SELECTION

    modifier_dialog.le_name.setText(" Location ")
    modifier_dialog.le_description.setText(" Description ")
    modifier_dialog.cbType.setCurrentIndex(config.NUMERIC_MODIFIER)

    assert modifier_dialog.modifiers_sets_dict["0"]["name"] == "Location"
    assert modifier_dialog.modifiers_sets_dict["0"]["description"] == "Description"
    assert modifier_dialog.modifiers_sets_dict["0"]["type"] == config.NUMERIC_MODIFIER
    assert not modifier_dialog.lwModifiers.isEnabled()

    modifier_dialog.cbType.setCurrentIndex(config.EXTERNAL_DATA_MODIFIER)
    assert modifier_dialog.lb_name.text() == "Variable name"


def test_add_modifier_validates_text_codes_and_duplicates(modifier_dialog, monkeypatch):
    modifier_dialog.add_set_of_modifiers()
    messages = []
    monkeypatch.setattr(add_modifier.QMessageBox, "critical", lambda *args: messages.append(args))

    modifier_dialog.leModifier.setText("bad, modifier")
    modifier_dialog.addModifier()
    modifier_dialog.leModifier.setText("")
    modifier_dialog.addModifier()
    modifier_dialog.leModifier.setText("North")
    modifier_dialog.leCode.setText("too long")
    modifier_dialog.addModifier()
    modifier_dialog.leCode.setText("F1")
    modifier_dialog.addModifier()

    assert values(modifier_dialog) == ["North (F1)"]

    modifier_dialog.leModifier.setText("North (F1)")
    modifier_dialog.addModifier()
    modifier_dialog.leModifier.setText("South")
    modifier_dialog.leCode.setText("(")
    modifier_dialog.addModifier()
    modifier_dialog.leCode.setText("F1")
    modifier_dialog.addModifier()

    assert any("not allowed" in message[2] for message in messages)
    assert any("No modifier" in message[2] for message in messages)
    assert any("shortcut code" in message[2] for message in messages)


def test_modify_move_sort_and_remove_modifiers(modifier_dialog, monkeypatch):
    modifier_dialog.add_set_of_modifiers()
    for value in ("Charlie", "Alice", "Bob"):
        modifier_dialog.leModifier.setText(value)
        if value == "Bob":
            modifier_dialog.leCode.setText("B")
        modifier_dialog.addModifier()

    modifier_dialog.lwModifiers.setCurrentRow(2)
    modifier_dialog.modifyModifier()
    assert modifier_dialog.leModifier.text() == "Bob"
    assert modifier_dialog.leCode.text() == "B"
    modifier_dialog.addModifier()

    modifier_dialog.lwModifiers.setCurrentRow(1)
    modifier_dialog.moveModifierUp()
    modifier_dialog.moveModifierDown()
    modifier_dialog.sort_modifiers()
    assert values(modifier_dialog) == ["Alice", "Bob (B)", "Charlie"]

    modifier_dialog.lwModifiers.setCurrentRow(0)
    modifier_dialog.removeModifier()
    assert values(modifier_dialog) == ["Bob (B)", "Charlie"]

    messages = []
    monkeypatch.setattr(add_modifier.QMessageBox, "information", lambda *args: messages.append(args))
    modifier_dialog.lwModifiers.setCurrentRow(-1)
    modifier_dialog.modifyModifier()
    assert messages


def test_add_subjects_load_file_and_sort(modifier_dialog, monkeypatch, tmp_path):
    modifier_dialog.add_set_of_modifiers()
    modifier_dialog.add_subjects()
    assert values(modifier_dialog) == ["Alice (A)", "Bob"]

    modifiers_file = tmp_path / "modifiers.txt"
    modifiers_file.write_text("Zulu\nAlice (A)\nbad,name\n")
    messages = []
    monkeypatch.setattr(add_modifier.QFileDialog, "getOpenFileName", lambda *_: (str(modifiers_file), ""))
    monkeypatch.setattr(add_modifier.QMessageBox, "critical", lambda *args: messages.append(args))
    modifier_dialog.add_modifiers_from_file()
    modifier_dialog.sort_modifiers()

    assert values(modifier_dialog) == ["Alice (A)", "Bob", "Zulu"]
    assert messages


def test_move_and_remove_modifier_sets(modifier_dialog, monkeypatch):
    modifier_dialog.add_set_of_modifiers()
    modifier_dialog.le_name.setText("First")
    modifier_dialog.add_set_of_modifiers()
    modifier_dialog.le_name.setText("Second")

    modifier_dialog.moveSetLeft()
    assert modifier_dialog.modifiers_sets_dict["0"]["name"] == "Second"
    modifier_dialog.moveSetRight()
    assert modifier_dialog.modifiers_sets_dict["1"]["name"] == "Second"

    monkeypatch.setattr(add_modifier.dialog, "MessageDialog", lambda *_: config.YES)
    modifier_dialog.remove_set_of_modifiers()
    modifier_dialog.remove_set_of_modifiers()

    assert modifier_dialog.tabWidgetModifiersSets.count() == 0


def test_tab_changes_button_responses_and_get_modifiers(modifier_dialog, monkeypatch):
    modifier_dialog.add_set_of_modifiers()
    modifier_dialog.le_name.setText("First")
    modifier_dialog.leModifier.setText("North")
    modifier_dialog.addModifier()
    modifier_dialog.add_set_of_modifiers()
    modifier_dialog.le_name.setText("Second")
    modifier_dialog.leModifier.setText("unsaved")

    monkeypatch.setattr(add_modifier.dialog, "MessageDialog", lambda *_: config.NO)
    modifier_dialog.tabWidgetModifiersSets.setCurrentIndex(0)
    assert modifier_dialog.tabWidgetModifiersSets.currentIndex() == 1

    monkeypatch.setattr(add_modifier.dialog, "MessageDialog", lambda *_: config.YES)
    modifier_dialog.tabWidgetModifiersSets.setCurrentIndex(0)
    assert values(modifier_dialog) == ["North"]

    modifier_dialog.cb_ask_at_stop.setChecked(True)
    result = json.loads(modifier_dialog.get_modifiers())
    assert result["0"]["ask at stop"] is True
    assert "1" not in result

    modifier_dialog.leModifier.setText("working")
    monkeypatch.setattr(add_modifier.dialog, "MessageDialog", lambda *_: config.CANCEL)
    modifier_dialog.pb_pushed(config.OK)
    assert modifier_dialog.result() == 0
    monkeypatch.setattr(add_modifier.dialog, "MessageDialog", lambda *_: config.CLOSE)
    modifier_dialog.pb_pushed(config.CANCEL)
    assert modifier_dialog.result() == 0


def test_rare_validation_and_cancellation_paths(modifier_dialog, monkeypatch):
    messages = []
    monkeypatch.setattr(add_modifier.QMessageBox, "information", lambda *args: messages.append(args))
    monkeypatch.setattr(add_modifier.QMessageBox, "warning", lambda *args: messages.append(args))

    modifier_dialog.add_set_of_modifiers()
    modifier_dialog.modifiers_sets_dict["0"] = {}
    modifier_dialog.add_set_of_modifiers()
    assert messages

    modifier_dialog.tabWidgetModifiersSets.removeTab(0)
    modifier_dialog.modifiers_sets_dict = {}
    modifier_dialog.remove_set_of_modifiers()
    assert any("not possible to remove" in message[2] for message in messages)

    modifier_dialog.tabWidgetModifiersSets.addTab(QWidget(), "Set #1")
    modifier_dialog.tabWidgetModifiersSets.setCurrentIndex(0)
    modifier_dialog.set_name_changed()
    modifier_dialog.modifiers_sets_dict = {}
    modifier_dialog.set_description_changed()
    modifier_dialog.modifiers_sets_dict = {}
    modifier_dialog.type_changed()

    monkeypatch.setattr(add_modifier.QFileDialog, "getOpenFileName", lambda *_: ("", ""))
    modifier_dialog.add_modifiers_from_file()
    monkeypatch.setattr(add_modifier.QFileDialog, "getOpenFileName", lambda *_: ("/missing/modifiers.txt", ""))
    modifier_dialog.add_modifiers_from_file()
    assert any("Error reading modifiers" in message[2] for message in messages)


def test_insert_positions_duplicate_modifiers_and_acceptance(modifier_dialog, monkeypatch, tmp_path):
    modifier_dialog.add_set_of_modifiers()
    modifier_dialog.itemPositionMem = 0
    modifier_dialog.add_subjects()
    assert values(modifier_dialog) == ["Bob", "Alice (A)"]

    modifiers_file = tmp_path / "modifiers.txt"
    modifiers_file.write_text("Zulu\n")
    monkeypatch.setattr(add_modifier.QFileDialog, "getOpenFileName", lambda *_: (str(modifiers_file), ""))
    modifier_dialog.add_modifiers_from_file()
    assert values(modifier_dialog)[0] == "Zulu"

    modifier_dialog.itemPositionMem = -1
    modifier_dialog.lwModifiers.clear()
    modifier_dialog.modifiers_sets_dict["0"]["values"] = []
    modifier_dialog.leModifier.setText("North")
    modifier_dialog.addModifier()
    errors = []
    monkeypatch.setattr(add_modifier.QMessageBox, "critical", lambda *args: errors.append(args))
    modifier_dialog.leModifier.setText("North")
    modifier_dialog.addModifier()
    assert "already in the list" in errors[0][2]

    modifier_dialog.leModifier.clear()
    modifier_dialog.pb_pushed(config.OK)
    assert modifier_dialog.result() == 1


def test_legacy_second_empty_dictionary_check_is_covered(modifier_dialog):
    class ChangingTruthDictionary(dict):
        def __init__(self):
            super().__init__({"0": {"name": "", "description": "", "type": config.SINGLE_SELECTION, "values": []}})
            self.calls = 0

        def __bool__(self):
            self.calls += 1
            return self.calls == 1

    modifier_dialog.add_set_of_modifiers()
    modifier_dialog.modifiers_sets_dict = ChangingTruthDictionary()
    modifier_dialog.leModifier.setText("North")
    modifier_dialog.leCode.setText("N")

    modifier_dialog.addModifier()

    assert values(modifier_dialog) == ["North (N)"]


def test_modifier_initializes_empty_dictionary_and_removes_first_set(modifier_dialog, monkeypatch):
    modifier_dialog.add_set_of_modifiers()
    modifier_dialog.modifiers_sets_dict = {}
    modifier_dialog.leModifier.setText("North")
    modifier_dialog.addModifier()
    assert values(modifier_dialog) == ["North"]

    modifier_dialog.le_name.setText("First")
    modifier_dialog.add_set_of_modifiers()
    modifier_dialog.le_name.setText("Second")
    modifier_dialog.tabWidgetModifiersSets.setCurrentIndex(0)
    monkeypatch.setattr(add_modifier.dialog, "MessageDialog", lambda *_: config.YES)

    modifier_dialog.remove_set_of_modifiers()

    assert modifier_dialog.modifiers_sets_dict["0"]["name"] == "Second"
