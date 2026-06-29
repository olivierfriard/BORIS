from pathlib import Path
import sys

import pandas as pd

PERSONAL_PLUGINS_DIR = Path("/home/olivier/projects/BORIS_plugins")

sys.path.insert(0, str(PERSONAL_PLUGINS_DIR))
import behavior_by_frame as plugin


def _df(rows, extra_columns=None):
    columns = [
        "Observation id",
        "Observation type",
        "Subject",
        "Behavior",
        "Behavior type",
        "Start (s)",
        "Stop (s)",
        "Media duration (s)",
        "FPS (frame/s)",
    ]
    if extra_columns:
        columns.extend(extra_columns)
    return pd.DataFrame(rows, columns=columns)


def test_run_returns_current_behavior_for_each_video_frame():
    df = _df(
        [
            ("obs1", "MEDIA", "S1", "A", "State event", 0.0, 1.0, 2.0, 2.0),
            ("obs1", "MEDIA", "S1", "B", "State event", 1.0, 2.0, 2.0, 2.0),
        ]
    )

    result = plugin.run(df)

    assert result["Frame index"].tolist() == [0, 1, 2, 3]
    assert result["Time (s)"].tolist() == [0.0, 0.5, 1.0, 1.5]
    assert result["Behavior"].tolist() == ["A", "A", "B", "B"]


def test_run_orders_observations_alphabetically():
    df = _df(
        [
            ("obs2", "MEDIA", "S1", "B", "State event", 0.0, 0.5, 0.5, 2.0),
            ("obs1", "MEDIA", "S1", "A", "State event", 0.0, 0.5, 0.5, 2.0),
        ]
    )

    result = plugin.run(df)

    assert result["Observation id"].drop_duplicates().tolist() == ["obs1", "obs2"]


def test_observed_events_time_interval_limits_output_to_selected_events():
    df = _df(
        [
            ("obs1", "MEDIA", "S1", "A", "State event", 1.0, 2.0, 3.0, 2.0),
        ]
    )

    result = plugin.run(df, parameters={"time": "limit to events"})

    assert result["Frame index"].tolist() == [2, 3]
    assert result["Time (s)"].tolist() == [1.0, 1.5]
    assert result["Behavior"].tolist() == ["A", "A"]


def test_user_defined_time_interval_uses_selected_bounds():
    df = _df(
        [
            ("obs1", "MEDIA", "S1", "A", "State event", 0.0, 3.0, 3.0, 2.0),
        ]
    )

    result = plugin.run(df, parameters={"time": "time interval", "start time": 0.5, "end time": 1.5})

    assert result["Frame index"].tolist() == [1, 2]
    assert result["Time (s)"].tolist() == [0.5, 1.0]
    assert result["Behavior"].tolist() == ["A", "A"]


def test_media_duration_time_interval_uses_media_duration():
    df = _df(
        [
            ("obs1", "MEDIA", "S1", "A", "State event", 1.0, 1.5, 2.0, 2.0),
        ]
    )

    result = plugin.run(df, parameters={"time": "full obs"})

    assert result["Frame index"].tolist() == [0, 1, 2, 3]
    assert result["Time (s)"].tolist() == [0.0, 0.5, 1.0, 1.5]
    assert result["Behavior"].tolist() == ["", "", "A", ""]


def test_run_concatenates_cooccurring_behaviors_with_plus_separator():
    df = _df(
        [
            ("obs1", "MEDIA", "S1", "A", "State event", 0.0, 1.5, 2.0, 2.0),
            ("obs1", "MEDIA", "S1", "B", "State event", 0.5, 1.5, 2.0, 2.0),
        ]
    )

    result = plugin.run(df)

    assert result["Behavior"].tolist() == ["A", "A + B", "A + B", ""]
    assert " | " not in result.loc[result["Frame index"] == 1, "Behavior"].iloc[0]


def test_run_appends_modifiers_when_requested():
    df = _df(
        [
            ("obs1", "MEDIA", "S1", "A", "State event", 0.0, 1.0, 1.0, 2.0, "fast", pd.NA),
            ("obs1", "MEDIA", "S1", "B", "State event", 0.0, 1.0, 1.0, 2.0, pd.NA, "grain"),
        ],
        extra_columns=[("A", "speed"), ("B", "food")],
    )

    result_without_modifiers = plugin.run(df, parameters={"include modifiers": False})
    result_with_modifiers = plugin.run(df, parameters={"include modifiers": True})

    assert result_without_modifiers.loc[0, "Behavior"] == "A + B"
    assert result_with_modifiers.loc[0, "Behavior"] == "A|fast + B|grain"


def test_run_keeps_only_selected_subjects_and_behaviors_from_parameters():
    df = _df(
        [
            ("obs1", "MEDIA", "S1", "A", "State event", 0.0, 1.0, 1.0, 2.0),
            ("obs1", "MEDIA", "S2", "B", "State event", 0.0, 1.0, 1.0, 2.0),
            ("obs1", "MEDIA", "S2", "A", "State event", 0.0, 1.0, 1.0, 2.0),
            ("obs2", "MEDIA", "S2", "B", "State event", 0.0, 1.0, 1.0, 2.0),
        ]
    )

    result = plugin.run(
        df,
        parameters={
            "selected observations": ["obs1"],
            "selected subjects": ["S2"],
            "selected behaviors": ["B"],
        },
    )

    assert result["Observation id"].unique().tolist() == ["obs1"]
    assert result["Subject"].unique().tolist() == ["S2"]
    assert result["Behavior"].tolist() == ["B", "B"]


def test_run_reports_missing_columns():
    df = pd.DataFrame(
        [("obs1", "S1", "A", 0.0, 1.0)],
        columns=["Observation id", "Subject", "Behavior", "Start (s)", "Stop (s)"],
    )

    title, result = plugin.run(df)

    assert title == "Behavior by frame - Missing columns"
    assert result["missing column"].tolist() == ["FPS (frame/s)"]


def test_run_assigns_point_event_to_frame_index():
    df = _df(
        [
            ("obs1", "MEDIA", "S1", "P", "Point event", 0.5, 0.5, 1.5, 2.0),
        ]
    )

    result = plugin.run(df)

    assert result["Frame index"].tolist() == [0, 1, 2]
    assert result["Behavior"].tolist() == ["", "P", ""]


def test_run_ignores_non_media_observations_when_observation_type_is_present():
    df = _df(
        [
            ("obs1", "LIVE", "S1", "A", "State event", 0.0, 1.0, 1.0, 2.0),
            ("obs2", "MEDIA", "S1", "B", "State event", 0.0, 1.0, 1.0, 2.0),
        ]
    )

    result = plugin.run(df)

    assert result["Observation id"].unique().tolist() == ["obs2"]
    assert result["Behavior"].tolist() == ["B", "B"]
