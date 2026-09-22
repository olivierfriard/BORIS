import json
from types import SimpleNamespace

import pytest
from PySide6.QtWidgets import QLineEdit, QPlainTextEdit, QPushButton, QTableWidget, QTableWidgetItem, QWidget

from boris import config as cfg
from boris import converters


class ConverterWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.le_converter_name = QLineEdit(self)
        self.le_converter_description = QLineEdit(self)
        self.pteCode = QPlainTextEdit(self)
        self.tw_converters = QTableWidget(0, 3, self)
        for name in (
            "pb_save_converter",
            "pb_cancel_converter",
            "pb_add_converter",
            "pb_modify_converter",
            "pb_delete_converter",
            "pb_load_from_file",
            "pb_load_from_repo",
        ):
            setattr(self, name, QPushButton(self))
        self.row_in_modification = -1
        self.flag_modified = False


@pytest.fixture
def converter_window(qapp):
    window = ConverterWindow()
    yield window
    window.close()
    window.deleteLater()
    qapp.processEvents()


def add_row(window, name="existing", description="description", code="OUTPUT = 1"):
    row = window.tw_converters.rowCount()
    window.tw_converters.setRowCount(row + 1)
    for column, value in enumerate((name, description, code.replace("\n", "@"))):
        window.tw_converters.setItem(row, column, QTableWidgetItem(value))


def errors(monkeypatch):
    messages = []
    monkeypatch.setattr(converters.QMessageBox, "critical", lambda *args: messages.append(("critical", args)))
    monkeypatch.setattr(converters.QMessageBox, "warning", lambda *args: messages.append(("warning", args)))
    return messages


def test_code_to_func_builds_a_converter_that_accepts_bytes():
    source = converters.code_2_func(None, "seconds", "OUTPUT = int(INPUT) + 2")
    namespace = {}
    exec(source, namespace)

    assert namespace["seconds"]("3") == 5
    assert namespace["seconds"](b"4") == 6


def test_add_modify_and_cancel_toggle_editor_controls(monkeypatch, converter_window):
    messages = errors(monkeypatch)
    converters.add_converter(converter_window)
    assert converter_window.le_converter_name.isEnabled()
    assert not converter_window.pb_add_converter.isEnabled()

    converters.modify_converter(converter_window)
    assert messages[-1][0] == "warning"

    add_row(converter_window, "old_name", "old description", "OUTPUT = 1\nOUTPUT += 1")
    converter_window.tw_converters.selectRow(0)
    converters.modify_converter(converter_window)
    assert converter_window.le_converter_name.text() == "old_name"
    assert converter_window.le_converter_description.text() == "old description"
    assert converter_window.pteCode.toPlainText() == "OUTPUT = 1\nOUTPUT += 1"
    assert converter_window.row_in_modification == 0

    converters.cancel_converter(converter_window)
    assert not converter_window.le_converter_name.isEnabled()
    assert converter_window.pb_add_converter.isEnabled()
    assert converter_window.pteCode.toPlainText() == ""


@pytest.mark.parametrize(
    "name, code, message",
    [
        ("", "OUTPUT = 1", "must have a name"),
        ("bad name", "OUTPUT = 1", "Forbidden characters"),
        ("valid", "", "must have Python code"),
        ("valid", "OUTPUT =", "produces an error"),
    ],
)
def test_save_converter_rejects_invalid_input(monkeypatch, converter_window, name, code, message):
    messages = errors(monkeypatch)
    converter_window.le_converter_name.setText(name)
    converter_window.pteCode.setPlainText(code)

    converters.save_converter(converter_window)

    assert converter_window.tw_converters.rowCount() == 0
    assert message in messages[-1][1][2]


def test_save_converter_adds_and_updates_rows(converter_window):
    converter_window.le_converter_name.setText("seconds")
    converter_window.le_converter_description.setText("Convert to seconds")
    converter_window.pteCode.setPlainText("OUTPUT = int(INPUT)")

    converters.save_converter(converter_window)

    assert converter_window.tw_converters.rowCount() == 1
    assert converter_window.tw_converters.item(0, 2).text() == "OUTPUT = int(INPUT)"
    assert converter_window.flag_modified is True
    assert converter_window.pb_add_converter.isEnabled()

    converter_window.row_in_modification = 0
    converter_window.le_converter_name.setText("updated")
    converter_window.le_converter_description.setText("Updated converter")
    converter_window.pteCode.setPlainText("OUTPUT = 7")
    converters.save_converter(converter_window)

    assert converter_window.tw_converters.rowCount() == 1
    assert converter_window.tw_converters.item(0, 0).text() == "updated"
    assert converter_window.tw_converters.item(0, 1).text() == "Updated converter"


def test_delete_converter_requires_selection_and_confirmation(monkeypatch, converter_window):
    messages = errors(monkeypatch)
    converters.delete_converter(converter_window)
    assert messages[-1][0] == "warning"

    add_row(converter_window)
    converter_window.tw_converters.selectRow(0)
    monkeypatch.setattr(converters.dialog, "MessageDialog", lambda *_: cfg.CANCEL)
    converters.delete_converter(converter_window)
    assert converter_window.tw_converters.rowCount() == 1

    monkeypatch.setattr(converters.dialog, "MessageDialog", lambda *_: cfg.OK)
    converters.delete_converter(converter_window)
    assert converter_window.tw_converters.rowCount() == 0


class Selector:
    def __init__(self, selected, accepted=True):
        self.selected = selected
        self.accepted = accepted

    def exec_(self):
        return self.accepted

    def get_selected_observations(self):
        return self.selected


def test_load_converters_from_file_handles_invalid_cancelled_and_selected_data(monkeypatch, tmp_path, converter_window):
    messages = errors(monkeypatch)
    invalid_file = tmp_path / "invalid.json"
    invalid_file.write_text("{}")
    monkeypatch.setattr(converters.QFileDialog, "getOpenFileName", lambda *_: (str(invalid_file), ""))
    converters.load_converters_from_file_repo(converter_window, "file")
    assert messages[-1][0] == "critical"

    valid_file = tmp_path / "converters.json"
    valid_file.write_text(
        json.dumps(
            {
                "BORIS converters": {
                    "seconds": {"description": "Convert", "code": "OUTPUT = int(INPUT)"},
                }
            }
        )
    )
    monkeypatch.setattr(converters.QFileDialog, "getOpenFileName", lambda *_: (str(valid_file), ""))
    monkeypatch.setattr(converters.dialog, "ChooseObservationsToImport", lambda *_: Selector([], accepted=True))
    converters.load_converters_from_file_repo(converter_window, "file")
    assert converter_window.tw_converters.rowCount() == 0

    monkeypatch.setattr(converters.dialog, "ChooseObservationsToImport", lambda *_: Selector(["seconds"]))
    converters.load_converters_from_file_repo(converter_window, "file")
    assert converter_window.tw_converters.item(0, 0).text() == "seconds"
    assert converter_window.tw_converters.item(0, 2).text() == "OUTPUT = int(INPUT)"


def test_load_converters_from_file_renames_conflicts(monkeypatch, tmp_path, converter_window):
    add_row(converter_window, "seconds")
    converter_file = tmp_path / "converters.json"
    converter_file.write_text(
        json.dumps({"BORIS converters": {"seconds": {"description": "New", "code": "OUTPUT = 2"}}})
    )
    monkeypatch.setattr(converters.QFileDialog, "getOpenFileName", lambda *_: (str(converter_file), ""))
    monkeypatch.setattr(converters.dialog, "ChooseObservationsToImport", lambda *_: Selector(["seconds"]))
    monkeypatch.setattr(converters.QInputDialog, "getText", lambda *_: ("seconds_2", True))

    converters.load_converters_from_file_repo(converter_window, "file")

    assert converter_window.tw_converters.item(1, 0).text() == "seconds_2"
    assert converter_window.tw_converters.item(1, 1).text() == "New"


def test_load_converters_retries_invalid_conflict_names(monkeypatch, tmp_path, converter_window):
    messages = errors(monkeypatch)
    add_row(converter_window, "seconds")
    converter_file = tmp_path / "converters.json"
    converter_file.write_text(
        json.dumps({"BORIS converters": {"seconds": {"description": "New", "code": "OUTPUT = 2"}}})
    )
    responses = iter([("seconds", True), ("bad name", True), ("seconds_2", True)])
    monkeypatch.setattr(converters.QFileDialog, "getOpenFileName", lambda *_: (str(converter_file), ""))
    monkeypatch.setattr(converters.dialog, "ChooseObservationsToImport", lambda *_: Selector(["seconds"]))
    monkeypatch.setattr(converters.QInputDialog, "getText", lambda *_: next(responses))

    converters.load_converters_from_file_repo(converter_window, "file")

    assert converter_window.tw_converters.item(1, 0).text() == "seconds_2"
    assert [message[0] for message in messages] == ["critical", "critical"]


def test_load_converters_skips_a_conflict_when_renaming_is_cancelled(monkeypatch, tmp_path, converter_window):
    add_row(converter_window, "seconds")
    converter_file = tmp_path / "converters.json"
    converter_file.write_text(
        json.dumps({"BORIS converters": {"seconds": {"description": "New", "code": "OUTPUT = 2"}}})
    )
    monkeypatch.setattr(converters.QFileDialog, "getOpenFileName", lambda *_: (str(converter_file), ""))
    monkeypatch.setattr(converters.dialog, "ChooseObservationsToImport", lambda *_: Selector(["seconds"]))
    monkeypatch.setattr(converters.QInputDialog, "getText", lambda *_: ("seconds", False))

    converters.load_converters_from_file_repo(converter_window, "file")

    assert converter_window.tw_converters.rowCount() == 1


def test_load_converters_does_not_import_invalid_code(monkeypatch, tmp_path, converter_window):
    messages = errors(monkeypatch)
    converter_file = tmp_path / "converters.json"
    converter_file.write_text(
        json.dumps({"BORIS converters": {"broken": {"description": "Broken", "code": "OUTPUT ="}}})
    )
    monkeypatch.setattr(converters.QFileDialog, "getOpenFileName", lambda *_: (str(converter_file), ""))
    monkeypatch.setattr(converters.dialog, "ChooseObservationsToImport", lambda *_: Selector(["broken"]))

    converters.load_converters_from_file_repo(converter_window, "file")

    assert converter_window.tw_converters.rowCount() == 0
    assert messages[-1][0] == "critical"


def test_load_converters_from_repo_handles_errors_and_imports(monkeypatch, converter_window):
    messages = errors(monkeypatch)
    monkeypatch.setattr(converters.urllib.request, "urlopen", lambda *_: (_ for _ in ()).throw(OSError("offline")))
    converters.load_converters_from_file_repo(converter_window, "repo")
    assert messages[-1][0] == "critical"

    monkeypatch.setattr(converters.urllib.request, "urlopen", lambda *_: SimpleNamespace(read=lambda: b"not a mapping"))
    converters.load_converters_from_file_repo(converter_window, "repo")
    assert messages[-1][0] == "critical"

    response = {"BORIS converters": {"repo_converter": {"description": "From repo", "code": "OUTPUT = 3"}}}
    monkeypatch.setattr(
        converters.urllib.request,
        "urlopen",
        lambda *_: SimpleNamespace(read=lambda: repr(response).encode()),
    )
    monkeypatch.setattr(converters.dialog, "ChooseObservationsToImport", lambda *_: Selector(["repo_converter"]))
    converters.load_converters_from_file_repo(converter_window, "repo")
    assert converter_window.tw_converters.item(0, 0).text() == "repo_converter"


def test_code_help_configures_and_executes_message_box(monkeypatch, converter_window):
    created = []

    class HelpMessage:
        Information = "information"
        StandardButton = SimpleNamespace(Ok="ok")

        def __init__(self):
            self.calls = []
            created.append(self)

        def setIcon(self, value):
            self.calls.append(("icon", value))

        def setWindowTitle(self, value):
            self.calls.append(("title", value))

        def setText(self, value):
            self.calls.append(("text", value))

        def setStandardButtons(self, value):
            self.calls.append(("buttons", value))

        def exec_(self):
            self.calls.append(("exec",))

    monkeypatch.setattr(converters, "QMessageBox", HelpMessage)

    converters.pb_code_help_clicked(converter_window)

    assert ("title", "Help for writing converters") in created[0].calls
    assert ("buttons", "ok") in created[0].calls
    assert ("exec",) in created[0].calls
