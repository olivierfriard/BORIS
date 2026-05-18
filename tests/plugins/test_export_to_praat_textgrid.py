from pathlib import Path
import sys

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from boris import config
from boris.analysis_plugins import export_to_praat_textgrid as plugin


def _df(rows):
    return pd.DataFrame(
        rows,
        columns=[
            "Observation id",
            "Subject",
            "Behavior",
            "Behavior type",
            "Start (s)",
            "Stop (s)",
        ],
    )


def test_overlapping_behaviors_for_same_subject_use_separate_tiers():
    df = _df(
        [
            ("obs1", "S1", "A", config.STATE_EVENT, 0.0, 5.0),
            ("obs1", "S1", "B", config.STATE_EVENT, 2.0, 7.0),
        ]
    )

    textgrid = plugin.build_textgrid(df, "obs1", xmin=0.0, xmax=8.0)

    assert 'size = 2' in textgrid
    assert 'name = "S1_A"' in textgrid
    assert 'name = "S1_B"' in textgrid
    assert 'text = "A"' in textgrid
    assert 'text = "B"' in textgrid
    assert "xmin = 2" in textgrid
    assert "xmax = 7" in textgrid


def test_overlapping_intervals_inside_same_subject_behavior_are_split():
    df = _df(
        [
            ("obs1", "S1", "A", config.STATE_EVENT, 0.0, 4.0),
            ("obs1", "S1", "A", config.STATE_EVENT, 2.0, 6.0),
        ]
    )

    textgrid = plugin.build_textgrid(df, "obs1", xmin=0.0, xmax=6.0)

    assert 'size = 2' in textgrid
    assert 'name = "S1_A"' in textgrid
    assert 'name = "S1_A_2"' in textgrid


def test_point_events_are_exported_as_text_tiers():
    df = _df(
        [
            ("obs1", "S1", "P", config.POINT_EVENT, 1.0, 1.0),
            ("obs1", "S1", "P", config.POINT_EVENT, 3.0, 3.0),
        ]
    )

    textgrid = plugin.build_textgrid(df, "obs1", xmin=0.0, xmax=4.0)

    assert 'class = "TextTier"' in textgrid
    assert 'name = "S1_P"' in textgrid
    assert "points: size = 2" in textgrid
    assert "number = 1" in textgrid
    assert "number = 3" in textgrid


def test_export_textgrids_uses_selected_arbitrary_interval(tmp_path):
    df = _df([("obs1", "S1", "A", config.STATE_EVENT, 2.0, 5.0)])
    project = {config.OBSERVATIONS: {"obs1": {}}}
    parameters = {
        config.TIME: config.TIME_ARBITRARY_INTERVAL,
        config.START_TIME: 2.0,
        config.END_TIME: 6.0,
    }

    message = plugin.export_textgrids(df, tmp_path, project=project, parameters=parameters)

    output_path = tmp_path / "obs1.TextGrid"
    assert f"Saved: {output_path}" == message
    textgrid = output_path.read_text(encoding="utf-8")
    assert "xmin = 2" in textgrid
    assert "xmax = 6" in textgrid
