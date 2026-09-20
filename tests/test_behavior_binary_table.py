"""Tests for behavior binary table generation."""

from decimal import Decimal
from types import SimpleNamespace

import tablib

from boris import behavior_binary_table, config


OBSERVATION_ID = "observation"
SUBJECT_ID = "subject-1"
SUBJECT_NAME = "Alice"


def make_project():
    return {
        config.ETHOGRAM: {
            "0": {config.BEHAVIOR_CODE: "P", config.TYPE: config.POINT_EVENT},
            "1": {config.BEHAVIOR_CODE: "S", config.TYPE: config.STATE_EVENT},
        },
        config.SUBJECTS: {SUBJECT_ID: {config.SUBJECT_NAME: SUBJECT_NAME}},
        config.OBSERVATIONS: {
            OBSERVATION_ID: {
                config.EVENTS: [
                    [Decimal("1"), SUBJECT_NAME, "S", "rest", ""],
                    [Decimal("1.2"), SUBJECT_NAME, "P", "chirp", ""],
                    [Decimal("1.8"), SUBJECT_NAME, "P", "chirp", ""],
                    [Decimal("2"), SUBJECT_NAME, "P", "chirp", ""],
                    [Decimal("3"), SUBJECT_NAME, "S", "rest", ""],
                    [Decimal("4"), SUBJECT_NAME, "S", "rest", ""],
                    [Decimal("4.9"), SUBJECT_NAME, "P", "chirp", ""],
                    [Decimal("5"), SUBJECT_NAME, "S", "rest", ""],
                ],
                config.TIME_OFFSET: Decimal("0"),
                config.OBSERVATION_TIME_INTERVAL: [1, 0],
            }
        },
    }


def make_parameters(time_mode=config.TIME_EVENTS, include_modifiers=False):
    return {
        config.SELECTED_SUBJECTS: [SUBJECT_NAME],
        config.SELECTED_BEHAVIORS: ["P", "S"],
        config.INCLUDE_MODIFIERS: include_modifiers,
        config.EXCLUDE_BEHAVIORS: False,
        config.START_TIME: Decimal("0"),
        config.END_TIME: Decimal("6"),
        "time": time_mode,
    }


def test_binary_table_counts_state_and_point_events_in_event_range():
    result = behavior_binary_table.create_behavior_binary_table(
        make_project(), [OBSERVATION_ID], make_parameters(), Decimal("1")
    )

    dataset = result[OBSERVATION_ID][SUBJECT_NAME]

    assert dataset.headers == ["time", "P", "S"]
    assert list(dataset) == [
        (1.0, 2, 1),
        (2.0, 1, 1),
        (3.0, 0, 0),
        (4.0, 1, 1),
        (5.0, 0, 0),
    ]


def test_binary_table_keeps_modifier_names_in_headers():
    result = behavior_binary_table.create_behavior_binary_table(
        make_project(), [OBSERVATION_ID], make_parameters(include_modifiers=True), Decimal("1")
    )

    dataset = result[OBSERVATION_ID][SUBJECT_NAME]

    assert dataset.headers == ["time", "P (chirp)", "S (rest)"]
    assert list(dataset)[0] == (1.0, 2, 1)


def test_binary_table_uses_observation_duration_for_full_observation(monkeypatch):
    monkeypatch.setattr(behavior_binary_table.observation_operations, "observation_length", lambda *_: (Decimal("6"), Decimal("6")))

    result = behavior_binary_table.create_behavior_binary_table(
        make_project(), [OBSERVATION_ID], make_parameters(config.TIME_FULL_OBS), Decimal("1")
    )

    dataset = result[OBSERVATION_ID][SUBJECT_NAME]

    assert [row[0] for row in dataset] == [0.0, 1.0, 2.0, 3.0, 4.0, 5.0, 6.0]


def test_binary_table_uses_configured_observation_interval(monkeypatch):
    project = make_project()
    project[config.OBSERVATIONS][OBSERVATION_ID][config.OBSERVATION_TIME_INTERVAL] = [1, 3]
    monkeypatch.setattr(behavior_binary_table.observation_operations, "observation_length", lambda *_: (Decimal("6"), Decimal("6")))

    result = behavior_binary_table.create_behavior_binary_table(
        project, [OBSERVATION_ID], make_parameters(config.TIME_OBS_INTERVAL), Decimal("1")
    )

    dataset = result[OBSERVATION_ID][SUBJECT_NAME]

    assert list(dataset) == [(1.0, 2, 1), (2.0, 1, 1), (3.0, 0, 0)]


def test_binary_table_reports_error_when_no_selected_behavior_is_defined():
    parameters = make_parameters()
    parameters[config.SELECTED_BEHAVIORS] = ["unknown"]

    assert behavior_binary_table.create_behavior_binary_table(
        make_project(), [OBSERVATION_ID], parameters, Decimal("1")
    ) == {"error": True, "msg": "No events selected"}


def test_binary_table_uses_observation_length_when_event_range_is_empty(monkeypatch):
    project = make_project()
    project[config.OBSERVATIONS][OBSERVATION_ID][config.EVENTS] = []
    parameters = make_parameters()
    parameters[config.SELECTED_SUBJECTS] = [config.NO_FOCAL_SUBJECT]
    monkeypatch.setattr(behavior_binary_table.observation_operations, "observation_length", lambda *_: (Decimal("2"), Decimal("2")))

    result = behavior_binary_table.create_behavior_binary_table(project, [OBSERVATION_ID], parameters, Decimal("1"))

    dataset = result[OBSERVATION_ID][config.NO_FOCAL_SUBJECT]
    assert dataset.headers == ["time", "P", "S"]
    assert list(dataset) == [(0.0, 0, 0), (1.0, 0, 0), (2.0, 0, 0)]


def test_binary_table_excludes_selected_behaviors_that_were_not_observed():
    parameters = make_parameters()
    parameters[config.SELECTED_BEHAVIORS].append("unknown")
    parameters[config.EXCLUDE_BEHAVIORS] = True

    result = behavior_binary_table.create_behavior_binary_table(
        make_project(), [OBSERVATION_ID], parameters, Decimal("1")
    )

    assert result[OBSERVATION_ID][SUBJECT_NAME].headers == ["time", "P", "S"]


def configure_dialog_workflow(monkeypatch, parameters=None):
    window = SimpleNamespace(pj=make_project())
    if parameters is None:
        parameters = make_parameters()

    monkeypatch.setattr(
        behavior_binary_table.select_observations,
        "select_observations2",
        lambda *_: (False, [OBSERVATION_ID]),
    )
    monkeypatch.setattr(behavior_binary_table.project_functions, "check_coded_behaviors_in_obs_list", lambda *_: False)
    monkeypatch.setattr(behavior_binary_table.project_functions, "check_state_events", lambda *_: (False, [OBSERVATION_ID]))
    monkeypatch.setattr(behavior_binary_table.observation_operations, "media_duration", lambda *_: (Decimal("6"), Decimal("6")))
    monkeypatch.setattr(
        behavior_binary_table.observation_operations,
        "coding_time",
        lambda *_: (Decimal("1"), Decimal("5"), Decimal("4")),
    )
    monkeypatch.setattr(
        behavior_binary_table.observation_operations,
        "time_intervals_range",
        lambda *_: (Decimal("1"), Decimal("5")),
    )
    monkeypatch.setattr(behavior_binary_table.select_subj_behav, "choose_obs_subj_behav_category", lambda *_args, **_kwargs: parameters)

    return window


def test_behavior_binary_table_stops_when_observation_selection_is_cancelled(monkeypatch):
    window = SimpleNamespace(pj=make_project())
    warnings = []
    monkeypatch.setattr(behavior_binary_table.QMessageBox, "warning", lambda *args: warnings.append(args))
    monkeypatch.setattr(behavior_binary_table.select_observations, "select_observations2", lambda *_: (False, []))
    monkeypatch.setattr(
        behavior_binary_table.project_functions,
        "check_coded_behaviors_in_obs_list",
        lambda *_: (_ for _ in ()).throw(AssertionError("unexpected validation")),
    )

    behavior_binary_table.behavior_binary_table(window)

    assert len(warnings) == 1


def test_behavior_binary_table_warns_when_subject_or_behavior_is_missing(monkeypatch):
    parameters = make_parameters()
    parameters[config.SELECTED_SUBJECTS] = []
    window = configure_dialog_workflow(monkeypatch, parameters)
    warnings = []
    monkeypatch.setattr(behavior_binary_table.QMessageBox, "warning", lambda *args: warnings.append(args))

    behavior_binary_table.behavior_binary_table(window)

    assert warnings[-1][2] == "Select subject(s) and behavior(s) to analyze"


def test_behavior_binary_table_stops_when_coded_behaviors_are_missing(monkeypatch):
    window = SimpleNamespace(pj=make_project())
    monkeypatch.setattr(behavior_binary_table.QMessageBox, "warning", lambda *_: None)
    monkeypatch.setattr(behavior_binary_table.select_observations, "select_observations2", lambda *_: (False, [OBSERVATION_ID]))
    monkeypatch.setattr(behavior_binary_table.project_functions, "check_coded_behaviors_in_obs_list", lambda *_: True)
    monkeypatch.setattr(
        behavior_binary_table.project_functions,
        "check_state_events",
        lambda *_: (_ for _ in ()).throw(AssertionError("unexpected state validation")),
    )

    behavior_binary_table.behavior_binary_table(window)


def test_behavior_binary_table_stops_when_state_events_are_not_paired(monkeypatch):
    window = configure_dialog_workflow(monkeypatch)
    monkeypatch.setattr(behavior_binary_table.QMessageBox, "warning", lambda *_: None)
    monkeypatch.setattr(behavior_binary_table.project_functions, "check_state_events", lambda *_: (True, [OBSERVATION_ID]))
    monkeypatch.setattr(
        behavior_binary_table.observation_operations,
        "media_duration",
        lambda *_: (_ for _ in ()).throw(AssertionError("unexpected duration calculation")),
    )

    behavior_binary_table.behavior_binary_table(window)


def test_behavior_binary_table_stops_when_parameter_dialog_is_cancelled(monkeypatch):
    window = configure_dialog_workflow(monkeypatch, parameters={})
    monkeypatch.setattr(behavior_binary_table.QMessageBox, "warning", lambda *_: None)
    monkeypatch.setattr(
        behavior_binary_table.QInputDialog,
        "getDouble",
        lambda *_: (_ for _ in ()).throw(AssertionError("unexpected interval dialog")),
    )

    behavior_binary_table.behavior_binary_table(window)


def test_behavior_binary_table_stops_when_interval_dialog_is_cancelled(monkeypatch):
    window = configure_dialog_workflow(monkeypatch)
    monkeypatch.setattr(behavior_binary_table.QMessageBox, "warning", lambda *_: None)
    monkeypatch.setattr(behavior_binary_table.QInputDialog, "getDouble", lambda *_: (1.0, False))
    monkeypatch.setattr(
        behavior_binary_table,
        "create_behavior_binary_table",
        lambda *_: (_ for _ in ()).throw(AssertionError("unexpected table generation")),
    )

    behavior_binary_table.behavior_binary_table(window)


def test_behavior_binary_table_warns_when_table_generation_returns_an_error(monkeypatch):
    window = configure_dialog_workflow(monkeypatch)
    warnings = []
    monkeypatch.setattr(behavior_binary_table.QMessageBox, "warning", lambda *args: warnings.append(args))
    monkeypatch.setattr(behavior_binary_table.QInputDialog, "getDouble", lambda *_: (1.0, True))
    monkeypatch.setattr(behavior_binary_table, "create_behavior_binary_table", lambda *_: {"error": True, "msg": "No events selected"})

    behavior_binary_table.behavior_binary_table(window)

    assert warnings[-1][2] == "No events selected"


def test_behavior_binary_table_exports_one_file_per_subject(monkeypatch, tmp_path):
    window = configure_dialog_workflow(monkeypatch)
    dataset = tablib.Dataset(headers=["time", "P"])
    dataset.append([1.0, 2])
    generated_parameters = []
    monkeypatch.setattr(behavior_binary_table.QMessageBox, "warning", lambda *_: None)
    monkeypatch.setattr(behavior_binary_table.QInputDialog, "getDouble", lambda *_: (1.5, True))
    monkeypatch.setattr(
        behavior_binary_table.QFileDialog,
        "getSaveFileName",
        lambda *_: (str(tmp_path / "binary_table"), config.CSV),
    )

    def create_table(project, observations, parameters, interval):
        generated_parameters.append((project, observations, parameters, interval))
        return {OBSERVATION_ID: {SUBJECT_NAME: dataset}}

    monkeypatch.setattr(behavior_binary_table, "create_behavior_binary_table", create_table)

    behavior_binary_table.behavior_binary_table(window)

    assert generated_parameters[0][1:] == ([OBSERVATION_ID], make_parameters(), Decimal("1.5"))
    output_file = tmp_path / "binary_table_Alice.csv"
    assert output_file.read_text() == "time,P\n1.0,2\n"


def test_behavior_binary_table_stops_when_save_dialog_is_cancelled(monkeypatch):
    window = configure_dialog_workflow(monkeypatch)
    dataset = tablib.Dataset(headers=["time"])
    monkeypatch.setattr(behavior_binary_table.QMessageBox, "warning", lambda *_: None)
    monkeypatch.setattr(behavior_binary_table.QInputDialog, "getDouble", lambda *_: (1.0, True))
    monkeypatch.setattr(behavior_binary_table, "create_behavior_binary_table", lambda *_: {OBSERVATION_ID: {SUBJECT_NAME: dataset}})
    monkeypatch.setattr(behavior_binary_table.QFileDialog, "getSaveFileName", lambda *_: ("", config.CSV))

    behavior_binary_table.behavior_binary_table(window)


def test_behavior_binary_table_stops_when_existing_base_file_is_not_overwritten(monkeypatch, tmp_path):
    window = configure_dialog_workflow(monkeypatch)
    dataset = tablib.Dataset(headers=["time"])
    (tmp_path / "binary_table.csv").write_text("existing")
    monkeypatch.setattr(behavior_binary_table.QMessageBox, "warning", lambda *_: None)
    monkeypatch.setattr(behavior_binary_table.QInputDialog, "getDouble", lambda *_: (1.0, True))
    monkeypatch.setattr(behavior_binary_table, "create_behavior_binary_table", lambda *_: {OBSERVATION_ID: {SUBJECT_NAME: dataset}})
    monkeypatch.setattr(
        behavior_binary_table.QFileDialog,
        "getSaveFileName",
        lambda *_: (str(tmp_path / "binary_table"), config.CSV),
    )
    monkeypatch.setattr(behavior_binary_table.dialog, "MessageDialog", lambda *_: config.CANCEL)

    behavior_binary_table.behavior_binary_table(window)

    assert not (tmp_path / "binary_table_Alice.csv").exists()


def test_behavior_binary_table_stops_when_existing_subject_file_is_not_overwritten(monkeypatch, tmp_path):
    window = configure_dialog_workflow(monkeypatch)
    dataset = tablib.Dataset(headers=["time"])
    output_file = tmp_path / "binary_table_Alice.csv"
    output_file.write_text("existing")
    monkeypatch.setattr(behavior_binary_table.QMessageBox, "warning", lambda *_: None)
    monkeypatch.setattr(behavior_binary_table.QInputDialog, "getDouble", lambda *_: (1.0, True))
    monkeypatch.setattr(behavior_binary_table, "create_behavior_binary_table", lambda *_: {OBSERVATION_ID: {SUBJECT_NAME: dataset}})
    monkeypatch.setattr(
        behavior_binary_table.QFileDialog,
        "getSaveFileName",
        lambda *_: (str(tmp_path / "binary_table.csv"), config.CSV),
    )
    monkeypatch.setattr(behavior_binary_table.dialog, "MessageDialog", lambda *_: config.CANCEL)

    behavior_binary_table.behavior_binary_table(window)

    assert output_file.read_text() == "existing"


def test_behavior_binary_table_exports_multiple_observations(monkeypatch, tmp_path):
    window = configure_dialog_workflow(monkeypatch)
    observations = [OBSERVATION_ID, "second observation"]
    dataset = tablib.Dataset(headers=["time", "P"])
    dataset.append([1.0, 2])
    monkeypatch.setattr(behavior_binary_table.QMessageBox, "warning", lambda *_: None)
    monkeypatch.setattr(behavior_binary_table.select_observations, "select_observations2", lambda *_: (False, observations))
    monkeypatch.setattr(behavior_binary_table.project_functions, "check_state_events", lambda *_: (False, observations))
    monkeypatch.setattr(behavior_binary_table.QInputDialog, "getDouble", lambda *_: (1.0, True))
    monkeypatch.setattr(behavior_binary_table.QInputDialog, "getItem", lambda *_: (config.CSV, True))
    monkeypatch.setattr(behavior_binary_table.QFileDialog, "getExistingDirectory", lambda *_args, **_kwargs: str(tmp_path))
    monkeypatch.setattr(
        behavior_binary_table,
        "create_behavior_binary_table",
        lambda *_: {observation: {SUBJECT_NAME: dataset} for observation in observations},
    )

    behavior_binary_table.behavior_binary_table(window)

    assert (tmp_path / "observation_Alice.csv").is_file()
    assert (tmp_path / f"{behavior_binary_table.util.safeFileName('second observation_Alice')}.csv").is_file()


def test_behavior_binary_table_skips_all_existing_multiple_observation_files(monkeypatch, tmp_path):
    window = configure_dialog_workflow(monkeypatch)
    observations = [OBSERVATION_ID, "second observation"]
    dataset = tablib.Dataset(headers=["time"])
    output_files = [
        tmp_path / "observation_Alice.csv",
        tmp_path / f"{behavior_binary_table.util.safeFileName('second observation_Alice')}.csv",
    ]
    for output_file in output_files:
        output_file.write_text("existing")
    monkeypatch.setattr(behavior_binary_table.QMessageBox, "warning", lambda *_: None)
    monkeypatch.setattr(behavior_binary_table.select_observations, "select_observations2", lambda *_: (False, observations))
    monkeypatch.setattr(behavior_binary_table.project_functions, "check_state_events", lambda *_: (False, observations))
    monkeypatch.setattr(behavior_binary_table.QInputDialog, "getDouble", lambda *_: (1.0, True))
    monkeypatch.setattr(behavior_binary_table.QInputDialog, "getItem", lambda *_: (config.CSV, True))
    monkeypatch.setattr(behavior_binary_table.QFileDialog, "getExistingDirectory", lambda *_args, **_kwargs: str(tmp_path))
    monkeypatch.setattr(
        behavior_binary_table,
        "create_behavior_binary_table",
        lambda *_: {observation: {SUBJECT_NAME: dataset} for observation in observations},
    )
    monkeypatch.setattr(behavior_binary_table.dialog, "MessageDialog", lambda *_: "Skip all")

    behavior_binary_table.behavior_binary_table(window)

    assert [output_file.read_text() for output_file in output_files] == ["existing", "existing"]


def test_behavior_binary_table_stops_when_multiple_format_dialog_is_cancelled(monkeypatch):
    window = configure_dialog_workflow(monkeypatch)
    observations = [OBSERVATION_ID, "second observation"]
    monkeypatch.setattr(behavior_binary_table.QMessageBox, "warning", lambda *_: None)
    monkeypatch.setattr(behavior_binary_table.select_observations, "select_observations2", lambda *_: (False, observations))
    monkeypatch.setattr(behavior_binary_table.project_functions, "check_state_events", lambda *_: (False, observations))
    monkeypatch.setattr(behavior_binary_table.QInputDialog, "getDouble", lambda *_: (1.0, True))
    monkeypatch.setattr(behavior_binary_table.QInputDialog, "getItem", lambda *_: (config.CSV, False))
    monkeypatch.setattr(behavior_binary_table, "create_behavior_binary_table", lambda *_: {})

    behavior_binary_table.behavior_binary_table(window)


def test_behavior_binary_table_stops_when_multiple_export_directory_is_cancelled(monkeypatch):
    window = configure_dialog_workflow(monkeypatch)
    observations = [OBSERVATION_ID, "second observation"]
    monkeypatch.setattr(behavior_binary_table.QMessageBox, "warning", lambda *_: None)
    monkeypatch.setattr(behavior_binary_table.select_observations, "select_observations2", lambda *_: (False, observations))
    monkeypatch.setattr(behavior_binary_table.project_functions, "check_state_events", lambda *_: (False, observations))
    monkeypatch.setattr(behavior_binary_table.QInputDialog, "getDouble", lambda *_: (1.0, True))
    monkeypatch.setattr(behavior_binary_table.QInputDialog, "getItem", lambda *_: (config.CSV, True))
    monkeypatch.setattr(behavior_binary_table.QFileDialog, "getExistingDirectory", lambda *_args, **_kwargs: "")
    monkeypatch.setattr(behavior_binary_table, "create_behavior_binary_table", lambda *_: {})

    behavior_binary_table.behavior_binary_table(window)


def test_behavior_binary_table_exports_binary_formats(monkeypatch, tmp_path):
    window = configure_dialog_workflow(monkeypatch)
    dataset = tablib.Dataset(headers=["time", "P"])
    dataset.append([1.0, 2])
    monkeypatch.setattr(behavior_binary_table.QMessageBox, "warning", lambda *_: None)
    monkeypatch.setattr(behavior_binary_table.QInputDialog, "getDouble", lambda *_: (1.0, True))
    monkeypatch.setattr(
        behavior_binary_table.QFileDialog,
        "getSaveFileName",
        lambda *_: (str(tmp_path / "binary_table.xlsx"), config.XLSX),
    )
    monkeypatch.setattr(behavior_binary_table, "create_behavior_binary_table", lambda *_: {OBSERVATION_ID: {SUBJECT_NAME: dataset}})

    behavior_binary_table.behavior_binary_table(window)

    assert (tmp_path / "binary_table_Alice.xlsx").read_bytes().startswith(b"PK")


def test_behavior_binary_table_reports_export_errors(monkeypatch, tmp_path):
    window = configure_dialog_workflow(monkeypatch)
    errors = []

    class FailingDataset:
        def export(self, _):
            raise ValueError("export failed")

    monkeypatch.setattr(behavior_binary_table.QMessageBox, "warning", lambda *_: None)
    monkeypatch.setattr(behavior_binary_table.QMessageBox, "critical", lambda *args: errors.append(args))
    monkeypatch.setattr(behavior_binary_table.QInputDialog, "getDouble", lambda *_: (1.0, True))
    monkeypatch.setattr(
        behavior_binary_table.QFileDialog,
        "getSaveFileName",
        lambda *_: (str(tmp_path / "binary_table.csv"), config.CSV),
    )
    monkeypatch.setattr(
        behavior_binary_table,
        "create_behavior_binary_table",
        lambda *_: {OBSERVATION_ID: {SUBJECT_NAME: FailingDataset()}},
    )

    behavior_binary_table.behavior_binary_table(window)

    assert "export failed" in errors[0][2]
