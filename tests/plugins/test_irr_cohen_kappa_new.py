from pathlib import Path
import sys

import pandas as pd
import pytest
from sklearn.metrics import cohen_kappa_score as sklearn_cohen_kappa_score

# Ensure package imports work when tests are run by path.
sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from boris.analysis_plugins import irr_cohen_kappa_new as plugin


@pytest.fixture
def suppress_ui(monkeypatch):
    monkeypatch.setattr(plugin.QInputDialog, "getInt", lambda *args, **kwargs: (3, True))
    warning_calls = []

    def _warning(*args, **kwargs):
        warning_calls.append((args, kwargs))

    monkeypatch.setattr(plugin.QMessageBox, "warning", _warning)
    return warning_calls


def _df(rows):
    return pd.DataFrame(
        rows,
        columns=[
            "Observation id",
            "Start (s)",
            "Stop (s)",
            "Subject",
            "Behavior",
        ],
    )


def test_run_returns_perfect_agreement_for_identical_segments(suppress_ui):
    df = _df(
        [
            ("obs1", 0.0, 1.0, "S", "A"),
            ("obs1", 1.0, 2.0, "S", "B"),
            ("obs2", 0.0, 1.0, "S", "A"),
            ("obs2", 1.0, 2.0, "S", "B"),
        ]
    )

    result = plugin.run(df)

    assert result.loc["obs1", "obs2"] == "1.000"
    assert result.loc["obs2", "obs1"] == "1.000"
    assert result.loc["obs1", "obs1"] == "1.000"
    assert suppress_ui == []


def test_instantaneous_events_are_compared_as_extra_point_observations(monkeypatch):
    monkeypatch.setattr(plugin.QInputDialog, "getInt", lambda *args, **kwargs: (3, True))
    monkeypatch.setattr(plugin.QMessageBox, "warning", lambda *args, **kwargs: None)

    captured_calls = []

    def capture_kappa(obs1_codes, obs2_codes):
        captured_calls.append((list(obs1_codes), list(obs2_codes)))
        return sklearn_cohen_kappa_score(obs1_codes, obs2_codes)

    monkeypatch.setattr(plugin, "cohen_kappa_score", capture_kappa)

    df = _df(
        [
            ("obs1", 0.0, 10.0, "S", "A"),
            ("obs1", 5.0, 5.0, "S", "E1"),
            ("obs2", 0.0, 10.0, "S", "A"),
        ]
    )

    result = plugin.run(df)

    assert result.loc["obs1", "obs2"] == "0.000"
    assert (["S|A", "S|A+S|E1"], ["S|A", "S|A"]) in captured_calls


def test_rounding_value_from_dialog_is_applied_before_interval_build(monkeypatch):
    monkeypatch.setattr(plugin.QInputDialog, "getInt", lambda *args, **kwargs: (2, True))
    monkeypatch.setattr(plugin.QMessageBox, "warning", lambda *args, **kwargs: None)

    df = _df(
        [
            ("obs1", 0.0049, 1.0049, "S", "A"),
            ("obs1", 1.0049, 2.0049, "S", "B"),
            ("obs2", 0.0, 1.0, "S", "A"),
            ("obs2", 1.0, 2.0, "S", "B"),
        ]
    )

    result = plugin.run(df)

    assert result.loc["obs1", "obs2"] == "1.000"


def test_nan_pairs_show_single_aggregated_warning(monkeypatch):
    monkeypatch.setattr(plugin.QInputDialog, "getInt", lambda *args, **kwargs: (3, True))
    warning_calls = []

    def _warning(parent, title, text):
        warning_calls.append((title, text))

    monkeypatch.setattr(plugin.QMessageBox, "warning", _warning)

    df = _df(
        [
            ("obs1", 0.0, 0.0, "S", "X"),
            ("obs2", 0.0, 0.0, "S", "X"),
            ("obs3", 0.0, 0.0, "S", "X"),
        ]
    )

    result = plugin.run(df)

    assert warning_calls and len(warning_calls) == 1
    title, text = warning_calls[0]
    assert title == "Cohen's Kappa not defined (NaN)"
    assert "- obs1 vs obs2" in text
    assert "- obs2 vs obs3" in text
    assert result.loc["obs1", "obs2"] == "NaN"
    assert result.loc["obs3", "obs3"] == "NaN"
