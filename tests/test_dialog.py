"""Tests for the reusable Qt dialogs and widgets."""

from decimal import Decimal
from pathlib import Path

import pytest
from PySide6.QtCore import QDateTime, QTime
from PySide6.QtWidgets import QDialog, QMessageBox, QTableWidgetItem

from boris import config as cfg
from boris import dialog


@pytest.fixture
def warnings(monkeypatch):
    messages = []
    monkeypatch.setattr(dialog.QMessageBox, "warning", lambda *args: messages.append(args))
    monkeypatch.setattr(dialog.QMessageBox, "critical", lambda *args: messages.append(args))
    return messages


def test_message_dialog_returns_the_clicked_button(monkeypatch):
    created = []

    class MessageBox:
        Question = object()
        YesRole = object()

        def __init__(self):
            self.buttons = []
            created.append(self)

        def setWindowTitle(self, title):
            self.title = title

        def setText(self, text):
            self.text = text

        def setIcon(self, icon):
            self.icon = icon

        def addButton(self, text, role):
            self.buttons.append((text, role))

        def windowFlags(self):
            return 0

        def setWindowFlags(self, flags):
            self.flags = flags

        def exec(self):
            return 0

        def clickedButton(self):
            return type("Button", (), {"text": lambda self: "Keep"})()

    monkeypatch.setattr(dialog, "QMessageBox", MessageBox)

    assert dialog.MessageDialog("Title", "Question", ("Discard", "Keep")) == "Keep"
    assert created[0].title == "Title"
    assert created[0].text == "Question"
    assert [button[0] for button in created[0].buttons] == ["Discard", "Keep"]


def test_global_error_message_logs_writes_and_copies_error(monkeypatch, tmp_path, qapp):
    errors = []

    class ErrorDialog:
        def __init__(self):
            self.pbOK = type("Button", (), {"setText": lambda self, text: setattr(self, "text", text)})()
            self.pbCancel = type(
                "Button", (), {"setVisible": lambda self, visible: setattr(self, "visible", visible), "setText": lambda self, text: setattr(self, "text", text)}
            )()
            self.ptText = type(
                "Text", (), {"setFont": lambda *_: None, "clear": lambda *_: None, "appendPlainText": lambda self, text: setattr(self, "text", text), "moveCursor": lambda *_: None}
            )()

        def setWindowTitle(self, title):
            self.title = title

        def exec_(self):
            return 0

    monkeypatch.setattr(dialog.pl.Path, "home", lambda: tmp_path)
    monkeypatch.setattr(dialog, "Results_dialog", ErrorDialog)
    monkeypatch.setattr(dialog.logger, "critical", errors.append)

    try:
        raise ValueError("broken")
    except ValueError as exc:
        dialog.global_error_message(type(exc), exc, exc.__traceback__)

    report = (tmp_path / "boris_error.log").read_text()
    assert "ValueError: broken" in report
    assert "ValueError: broken" in qapp.clipboard().text()
    assert "ValueError: broken" in errors[0]


def test_global_error_message_handles_log_write_failure_and_abort(monkeypatch):
    logged = []

    class ErrorDialog:
        def __init__(self):
            self.pbOK = type("Button", (), {"setText": lambda *_: None})()
            self.pbCancel = type("Button", (), {"setVisible": lambda *_: None, "setText": lambda *_: None})()
            self.ptText = type("Text", (), {"setFont": lambda *_: None, "clear": lambda *_: None, "appendPlainText": lambda *_: None, "moveCursor": lambda *_: None})()

        def setWindowTitle(self, title):
            self.title = title

        def exec_(self):
            return 1

    monkeypatch.setattr(dialog, "Results_dialog", ErrorDialog)
    monkeypatch.setattr(dialog.logger, "critical", logged.append)
    monkeypatch.setattr(dialog.pl.Path, "home", lambda: Path("/missing-home"))

    with pytest.raises(SystemExit, match="1"):
        dialog.global_error_message(RuntimeError, RuntimeError("broken"), None)

    assert "Impossible to write" in logged[-1]


@pytest.fixture
def time_widget(qapp):
    widget = dialog.get_time_widget()
    yield widget
    widget.close()
    widget.deleteLater()
    qapp.processEvents()


def test_time_widget_converts_every_format_and_toggles_sign(time_widget, warnings):
    time_widget.rb_seconds.setChecked(True)
    time_widget.le_seconds.setText("12.3456")
    assert time_widget.get_time() == Decimal("12.346")
    assert time_widget.stackedWidget.currentIndex() == 0

    time_widget.pb_sign_clicked()
    assert time_widget.pb_sign.text() == "-"
    assert time_widget.get_time() == Decimal("-12.346")
    time_widget.pb_sign_clicked()

    time_widget.rb_time.setChecked(True)
    time_widget.sb_hour.setValue(2)
    time_widget.te_time.setTime(QTime(0, 3, 4, 500))
    assert time_widget.get_time() == Decimal("7384.500")
    assert time_widget.stackedWidget.currentIndex() == 1

    time_widget.rb_datetime.setChecked(True)
    time_widget.dte.setDateTime(QDateTime.fromMSecsSinceEpoch(1234567))
    assert time_widget.get_time() == Decimal("1234.567")
    assert time_widget.stackedWidget.currentIndex() == 2
    assert warnings == []


def test_info_widget_initializes_its_label_and_list(qapp):
    info = dialog.Info_widget()
    try:
        assert info.windowTitle() == "BORIS"
        assert info.lwi.count() == 0
    finally:
        info.close()
        info.deleteLater()
        qapp.processEvents()


def test_time_widget_rejects_invalid_seconds_and_sets_short_and_date_times(time_widget, warnings):
    time_widget.rb_seconds.setChecked(True)
    time_widget.le_seconds.setText("not a number")
    assert time_widget.get_time().is_nan()
    assert "not a decimal number" in warnings[-1][2]

    time_widget.set_time(Decimal("-3661.234"))
    assert time_widget.pb_sign.text() == "-"
    assert time_widget.sb_hour.value() == 1
    assert time_widget.te_time.time() == QTime(0, 1, 1, 234)

    date_time = Decimal(cfg.DATE_CUTOFF + 10)
    time_widget.set_time(date_time)
    assert time_widget.rb_datetime.isChecked()
    assert time_widget.dte.dateTime().toMSecsSinceEpoch() == int(date_time * 1000)

    before = time_widget.le_seconds.text()
    time_widget.set_time(Decimal("NaN"))
    assert time_widget.le_seconds.text() == before


def test_time_widget_initial_value_is_applied(qapp):
    widget = dialog.get_time_widget(Decimal("1.250"))
    try:
        assert widget.le_seconds.text() == "1.250"
    finally:
        widget.close()
        widget.deleteLater()
        qapp.processEvents()


def test_ask_time_requires_a_format_and_a_valid_time(monkeypatch, qapp):
    warnings = []
    monkeypatch.setattr(dialog.QMessageBox, "warning", lambda *args: warnings.append(args))
    ask = dialog.Ask_time()
    try:
        ask.pb_ok_clicked()
        assert "Select an option" in warnings[-1][2]

        ask.time_widget.rb_seconds.setChecked(True)
        ask.time_widget.le_seconds.setText("invalid")
        ask.pb_ok_clicked()
        assert ask.result() == QDialog.DialogCode.Rejected

        ask.time_widget.le_seconds.setText("1")
        ask.pb_ok_clicked()
        assert ask.result() == QDialog.DialogCode.Accepted
    finally:
        ask.close()
        ask.deleteLater()
        qapp.processEvents()


def test_video_overlay_dialog_browse_and_validation(monkeypatch, warnings, qapp):
    overlay = dialog.Video_overlay_dialog()
    try:
        monkeypatch.setattr(dialog.QFileDialog, "getOpenFileName", lambda *_: ("", ""))
        overlay.browse()
        assert overlay.le_file_path.text() == ""

        monkeypatch.setattr(dialog.QFileDialog, "getOpenFileName", lambda *_: ("image.png", ""))
        overlay.browse()
        assert overlay.le_file_path.text() == "image.png"

        overlay.le_file_path.clear()
        overlay.ok()
        assert "Select a file" in warnings[-1][2]

        overlay.le_file_path.setText("image.png")
        overlay.le_overlay_position.setText("10")
        overlay.ok()
        assert "x,y format" in warnings[-1][2]

        overlay.le_overlay_position.setText("one,two")
        overlay.ok()
        assert "x,y format" in warnings[-1][2]

        overlay.le_overlay_position.setText("10, 20")
        overlay.ok()
        assert overlay.result() == QDialog.DialogCode.Accepted
    finally:
        overlay.close()
        overlay.deleteLater()
        qapp.processEvents()


def test_input_dialog_builds_all_supported_controls_and_defaults(qapp):
    elements = [
        (cfg.CHECKBOX, "Enabled", True),
        (cfg.LINE_EDIT, "Name"),
        (cfg.SPINBOX, "Count", 1, 10, 2, 5),
        (cfg.DOUBLE_SPINBOX, "Ratio", 0, 1, 0.1, 0.5, 3),
        (cfg.ITEMS_LIST, "Choice", (("First", ""), ("Second", "selected"))),
    ]
    input_dialog = dialog.Input_dialog("Configure", elements, "Options")
    try:
        assert input_dialog.windowTitle() == "Options"
        assert input_dialog.elements["Enabled"].isChecked()
        assert input_dialog.elements["Count"].value() == 5
        assert input_dialog.elements["Ratio"].decimals() == 3
        assert input_dialog.elements["Choice"].currentText() == "Second"

        fallback = dialog.Input_dialog("", [(cfg.ITEMS_LIST, "Fallback", (("First", ""),))])
        try:
            assert fallback.elements["Fallback"].currentIndex() == 0
        finally:
            fallback.close()
            fallback.deleteLater()
    finally:
        input_dialog.close()
        input_dialog.deleteLater()
        qapp.processEvents()


def test_item_selection_dialogs_return_current_selections(qapp):
    duplicates = dialog.Duplicate_items("Duplicated", ["A", "B"])
    chooser = dialog.ChooseObservationsToImport("Choose", ["one", "two"])
    try:
        assert duplicates.getCode() is None
        duplicates.lw.setCurrentRow(1)
        assert duplicates.getCode() == "B"

        assert chooser.get_selected_observations() == []
        chooser.lw.item(0).setSelected(True)
        chooser.lw.item(1).setSelected(True)
        assert chooser.get_selected_observations() == ["one", "two"]
    finally:
        duplicates.close()
        chooser.close()
        duplicates.deleteLater()
        chooser.deleteLater()
        qapp.processEvents()


def test_find_widgets_emit_the_requested_action(qapp):
    find = dialog.FindInEvents()
    replace = dialog.FindReplaceEvents()
    find_actions = []
    replace_actions = []
    find.clickSignal.connect(find_actions.append)
    replace.clickSignal.connect(replace_actions.append)
    try:
        assert find.cbSubject.isChecked()
        assert find.cbFindInSelectedEvents.isChecked() is False
        find.click("FIND")
        find.pbCancel.click()
        replace.pbCancel.click()
        replace.pbOK.click()
        replace.pbFindReplaceAll.click()
        assert find_actions == ["FIND", "CLOSE"]
        assert replace_actions == ["CANCEL", "FIND_REPLACE", "FIND_REPLACE_ALL"]
    finally:
        find.close()
        replace.close()
        find.deleteLater()
        replace.deleteLater()
        qapp.processEvents()


@pytest.mark.parametrize("result_type", [dialog.Results_dialog, dialog.Results_widget, dialog.Results_dialog_exit_code])
def test_results_widgets_save_text_cancel_and_report_errors(monkeypatch, tmp_path, qapp, result_type):
    messages = []
    result = result_type()
    result.ptText.setPlainText("report")
    try:
        monkeypatch.setattr(dialog.QFileDialog, "getSaveFileName", lambda *_: ("", ""))
        result.save_results()

        destination = tmp_path / f"{result_type.__name__}.txt"
        monkeypatch.setattr(dialog.QFileDialog, "getSaveFileName", lambda *_: (str(destination), ""))
        result.save_results()
        assert destination.read_text() == "report"

        monkeypatch.setattr(dialog.QFileDialog, "getSaveFileName", lambda *_: (str(tmp_path / "missing" / "report.txt"), ""))
        monkeypatch.setattr(dialog.QMessageBox, "critical", lambda *args: messages.append(args))
        result.save_results()
        assert "can not be saved" in messages[-1][2]
    finally:
        result.close()
        result.deleteLater()
        qapp.processEvents()


@pytest.mark.parametrize("result_type", [dialog.Results_dialog, dialog.Results_dialog_exit_code])
def test_result_dialogs_return_dataset_code_and_exit_status(qapp, result_type):
    result = result_type()
    try:
        result.dataset = True
        result.save_results()
        assert result.result() == cfg.SAVE_DATASET
        if result_type is dialog.Results_dialog_exit_code:
            result.done_(2)
            assert result.result() == 2
    finally:
        result.close()
        result.deleteLater()
        qapp.processEvents()


def test_results_widget_closes_after_dataset_save(qapp):
    result = dialog.Results_widget()
    try:
        result.dataset = True
        result.show()
        result.save_results()
        assert not result.isVisible()
    finally:
        result.close()
        result.deleteLater()
        qapp.processEvents()


def test_view_data_and_explore_results_signals(qapp):
    view = dialog.View_data()
    explore = dialog.View_explore_project_results()
    events = []
    explore.double_click_signal.connect(lambda name, row: events.append((name, row)))
    try:
        assert view.tw.verticalHeader().isHidden()
        explore.tw.setRowCount(1)
        explore.tw.setColumnCount(2)
        explore.tw.setItem(0, 0, QTableWidgetItem("observation"))
        explore.tw.setItem(0, 1, QTableWidgetItem("7"))
        explore.tw_cellDoubleClicked(0, 1)
        assert events == [("observation", 7)]
    finally:
        view.close()
        explore.close()
        view.deleteLater()
        explore.deleteLater()
        qapp.processEvents()
