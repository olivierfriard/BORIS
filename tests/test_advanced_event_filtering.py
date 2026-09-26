"""Tests for advanced event filtering."""

import sqlite3
from decimal import Decimal
from types import SimpleNamespace

import pytest

from boris import advanced_event_filtering, config


def make_events():
    return {
        "obs-1": {
            "Alice|Run": advanced_event_filtering.ico([1, 3]) | advanced_event_filtering.ico([4, 6]),
            "Bob|Rest": advanced_event_filtering.ico([2, 5]),
        },
        "obs-2": {"Alice|Run": advanced_event_filtering.ico([2, 4])},
    }


@pytest.fixture
def filtering_dialog(qapp):
    dialog = advanced_event_filtering.Advanced_event_filtering_dialog(make_events())
    yield dialog
    dialog.close()
    dialog.deleteLater()
    qapp.processEvents()


def test_interval_helpers_create_expected_boundaries():
    assert str(advanced_event_filtering.icc([1, 2])) == "[1,2]"
    assert str(advanced_event_filtering.ico([1, 2])) == "[1,2)"
    assert str(advanced_event_filtering.io([1, 2])) == "(1,2)"


def test_dialog_populates_lists_and_inserts_selected_tokens(filtering_dialog, monkeypatch):
    warnings = []
    monkeypatch.setattr(advanced_event_filtering.QMessageBox, "warning", lambda *args: warnings.append(args))

    filtering_dialog.add_subj_behav()
    filtering_dialog.add_logic()
    assert len(warnings) == 2

    filtering_dialog.lw1.setCurrentRow(0)
    filtering_dialog.lw2.setCurrentRow(0)
    filtering_dialog.add_subj_behav()
    filtering_dialog.lw3.setCurrentRow(0)
    filtering_dialog.add_logic()
    filtering_dialog.lw3.setCurrentRow(1)
    filtering_dialog.add_logic()

    assert '"Alice|Rest"' in filtering_dialog.logic.text()
    assert " & " in filtering_dialog.logic.text()
    assert " | " in filtering_dialog.logic.text()


def test_filter_handles_empty_invalid_detailed_and_summary_results(filtering_dialog, monkeypatch):
    warnings = []
    monkeypatch.setattr(advanced_event_filtering.QMessageBox, "warning", lambda *args: warnings.append(args))

    filtering_dialog.filter()
    assert filtering_dialog.out == []

    filtering_dialog.logic.setText('"Alice|Run')
    filtering_dialog.filter()
    assert "Wrong number" in warnings[-1][2]

    filtering_dialog.logic.setText('"Alice|Run" &')
    filtering_dialog.filter()
    assert "Error in" in filtering_dialog.out[0][1]

    filtering_dialog.logic.setText('"Alice|Run"')
    filtering_dialog.rb_details.setChecked(True)
    filtering_dialog.filter()
    assert filtering_dialog.tw.horizontalHeaderItem(0).text() == "Observation id"
    assert len(filtering_dialog.out) == 3

    filtering_dialog.rb_summary.setChecked(True)
    filtering_dialog.filter()
    assert filtering_dialog.tw.columnCount() == len(filtering_dialog.summary_header)
    assert filtering_dialog.out[0][1] == "2"
    assert filtering_dialog.out[0][4] != "NA"


def test_filter_missing_behavior_produces_no_intervals(filtering_dialog):
    filtering_dialog.logic.setText('"Nobody|Unknown"')

    filtering_dialog.filter()

    assert filtering_dialog.out == []
    assert "Nobody|Unknown" in filtering_dialog.events["obs-1"]


def test_filter_reports_key_errors_from_malformed_event_mappings(qapp):
    class KeyErrorMapping(dict):
        def __contains__(self, _):
            return True

        def __getitem__(self, _):
            raise KeyError

    dialog = advanced_event_filtering.Advanced_event_filtering_dialog({"obs": KeyErrorMapping({"Alice|Run": None})})
    try:
        dialog.logic.setText('"Alice|Run"')
        dialog.rb_details.setChecked(True)
        dialog.filter()

        assert dialog.out == [["obs", "subject / behavior not found", config.NA, config.NA, config.NA]]
    finally:
        dialog.close()
        dialog.deleteLater()
        qapp.processEvents()


def test_save_results_writes_text_and_binary_exports(filtering_dialog, monkeypatch, tmp_path):
    filtering_dialog.logic.setText('"Alice|Run"')
    filtering_dialog.filter()
    monkeypatch.setattr(
        advanced_event_filtering.QFileDialog,
        "getSaveFileName",
        lambda *_: (str(tmp_path / "results"), config.CSV),
    )

    filtering_dialog.save_results()
    assert (tmp_path / "results.csv").read_text().startswith("Observation id")

    monkeypatch.setattr(
        advanced_event_filtering.QFileDialog,
        "getSaveFileName",
        lambda *_: (str(tmp_path / "results.xlsx"), config.XLSX),
    )
    filtering_dialog.save_results()
    assert (tmp_path / "results.xlsx").read_bytes().startswith(b"PK")

    filtering_dialog.rb_details.setChecked(True)
    monkeypatch.setattr(
        advanced_event_filtering.QFileDialog,
        "getSaveFileName",
        lambda *_: (str(tmp_path / "details.csv"), config.CSV),
    )
    filtering_dialog.save_results()
    assert (tmp_path / "details.csv").read_text().startswith("Observation id,Comment")


def test_save_results_handles_cancellation_existing_files_and_errors(filtering_dialog, monkeypatch, tmp_path):
    filtering_dialog.logic.setText('"Alice|Run"')
    filtering_dialog.filter()
    monkeypatch.setattr(advanced_event_filtering.QFileDialog, "getSaveFileName", lambda *_: ("", config.CSV))
    filtering_dialog.save_results()

    existing_file = tmp_path / "results.csv"
    existing_file.write_text("existing")
    monkeypatch.setattr(
        advanced_event_filtering.QFileDialog,
        "getSaveFileName",
        lambda *_: (str(tmp_path / "results"), config.CSV),
    )
    monkeypatch.setattr(advanced_event_filtering.dialog, "MessageDialog", lambda *_: config.CANCEL)
    filtering_dialog.save_results()
    assert existing_file.read_text() == "existing"

    errors = []
    monkeypatch.setattr(advanced_event_filtering.QMessageBox, "critical", lambda *args: errors.append(args))
    monkeypatch.setattr(advanced_event_filtering.dialog, "MessageDialog", lambda *_: config.OVERWRITE)
    monkeypatch.setattr(advanced_event_filtering.tablib.Dataset, "export", lambda *_: (_ for _ in ()).throw(ValueError("export failed")))
    filtering_dialog.save_results()
    assert "can not be saved" in errors[0][2]


def make_database():
    database = sqlite3.connect(":memory:")
    cursor = database.cursor()
    cursor.execute("CREATE TABLE aggregated_events (observation, subject, behavior, start, stop)")
    cursor.executemany(
        "INSERT INTO aggregated_events VALUES (?, ?, ?, ?, ?)",
        [
            ("obs-1", "Alice", "Run", 1.0, 3.0),
            ("obs-1", "Alice", "Run", 4.0, 4.0),
            ("obs-2", "Bob", "Rest", 2.0, 5.0),
        ],
    )
    return database


def configure_event_filtering(monkeypatch, database, parameters):
    owner = SimpleNamespace(
        pj={config.OBSERVATIONS: {"obs-1": {}, "obs-2": {}}},
        config_param={"time_format": config.S},
    )
    monkeypatch.setattr(advanced_event_filtering.select_observations, "select_observations2", lambda *_: (False, ["obs-1", "obs-2"]))
    monkeypatch.setattr(advanced_event_filtering.project_functions, "check_state_events", lambda *_: (False, ["obs-1", "obs-2"]))
    monkeypatch.setattr(advanced_event_filtering.observation_operations, "coding_time", lambda *_: (Decimal("1"), Decimal("5"), Decimal("4")))
    monkeypatch.setattr(advanced_event_filtering.observation_operations, "media_duration", lambda *_: (Decimal("5"), Decimal("5")))
    monkeypatch.setattr(advanced_event_filtering.observation_operations, "time_intervals_range", lambda *_: (Decimal("1"), Decimal("5")))
    monkeypatch.setattr(advanced_event_filtering.select_subj_behav, "choose_obs_subj_behav_category", lambda *_args, **_kwargs: parameters)
    monkeypatch.setattr(advanced_event_filtering.db_functions, "load_aggregated_events_in_db", lambda *_: (True, "", database))
    return owner


def test_event_filtering_builds_intervals_and_shows_dialog(monkeypatch):
    database = make_database()
    parameters = {
        config.SELECTED_SUBJECTS: ["Alice", "Bob"],
        config.SELECTED_BEHAVIORS: ["Run", "Rest"],
        config.TIME_INTERVAL: config.TIME_EVENTS,
    }
    owner = configure_event_filtering(monkeypatch, database, parameters)
    shown = []

    class ResultDialog:
        def __init__(self, events):
            self.events = events
            self.lb_time_interval = SimpleNamespace(setText=lambda value: shown.append(value))

        def exec_(self):
            shown.append("executed")

    monkeypatch.setattr(advanced_event_filtering, "Advanced_event_filtering_dialog", ResultDialog)

    try:
        advanced_event_filtering.event_filtering(owner)
        assert str(shown[0]).startswith("Time interval:")
        assert shown[-1] == "executed"
    finally:
        database.close()


def test_event_filtering_stops_on_cancel_invalid_state_nan_and_parameters(monkeypatch):
    owner = SimpleNamespace(pj={config.OBSERVATIONS: {}}, config_param={"time_format": config.S})
    warnings, errors = [], []
    monkeypatch.setattr(advanced_event_filtering.QMessageBox, "warning", lambda *args: warnings.append(args))
    monkeypatch.setattr(advanced_event_filtering.QMessageBox, "critical", lambda *args: errors.append(args))
    monkeypatch.setattr(advanced_event_filtering.select_observations, "select_observations2", lambda *_: (False, []))
    advanced_event_filtering.event_filtering(owner)

    monkeypatch.setattr(advanced_event_filtering.select_observations, "select_observations2", lambda *_: (False, ["obs"]))
    monkeypatch.setattr(advanced_event_filtering.project_functions, "check_state_events", lambda *_: (True, ["obs"]))
    advanced_event_filtering.event_filtering(owner)

    monkeypatch.setattr(advanced_event_filtering.project_functions, "check_state_events", lambda *_: (False, ["obs"]))
    monkeypatch.setattr(advanced_event_filtering.observation_operations, "coding_time", lambda *_: (Decimal("NaN"), Decimal("0"), Decimal("0")))
    advanced_event_filtering.event_filtering(owner)
    assert errors


def test_event_filtering_stops_on_missing_parameters_and_uses_arbitrary_bounds(monkeypatch):
    database = make_database()
    owner = configure_event_filtering(monkeypatch, database, {})
    warnings = []
    monkeypatch.setattr(advanced_event_filtering.QMessageBox, "warning", lambda *args: warnings.append(args))

    try:
        advanced_event_filtering.event_filtering(owner)

        parameters = {
            config.SELECTED_SUBJECTS: [],
            config.SELECTED_BEHAVIORS: ["Run"],
            config.TIME_INTERVAL: config.TIME_ARBITRARY_INTERVAL,
            config.START_TIME: Decimal("2"),
            config.END_TIME: Decimal("4"),
        }
        monkeypatch.setattr(
            advanced_event_filtering.select_subj_behav,
            "choose_obs_subj_behav_category",
            lambda *_args, **_kwargs: parameters,
        )
        advanced_event_filtering.event_filtering(owner)
        assert warnings

        parameters[config.SELECTED_SUBJECTS] = ["Alice"]
        shown = []

        class ResultDialog:
            def __init__(self, events):
                shown.append(events)
                self.lb_time_interval = SimpleNamespace(setText=lambda *_: None)

            def exec_(self):
                pass

        monkeypatch.setattr(advanced_event_filtering, "Advanced_event_filtering_dialog", ResultDialog)
        advanced_event_filtering.event_filtering(owner)
        assert shown
    finally:
        database.close()
