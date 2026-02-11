from pathlib import Path
import sys

import pandas as pd
import pytest

# Ensure direct plugin-module imports work without importing the full BORIS package.
sys.path.insert(0, str(Path(__file__).resolve().parents[2] / "boris" / "analysis_plugins"))
import irr_weighted_cohen_kappa_with_modifiers_new as plugin


MOD_A = ("A", "modifiers")
MOD_B = ("B", "modifiers")
MOD_X = ("X", "modifiers")


@pytest.fixture
def suppress_ui(monkeypatch):
    monkeypatch.setattr(plugin.QInputDialog, "getInt", lambda *args, **kwargs: (3, True))
    monkeypatch.setattr(plugin.QInputDialog, "getDouble", lambda *args, **kwargs: (1.0, True))
    warning_calls = []

    def _warning(*args, **kwargs):
        warning_calls.append((args, kwargs))

    monkeypatch.setattr(plugin.QMessageBox, "warning", _warning)
    return warning_calls


def _df(rows, modifier_columns):
    return pd.DataFrame(
        rows,
        columns=[
            "Observation id",
            "Start (s)",
            "Stop (s)",
            "Subject",
            "Behavior",
            *modifier_columns,
        ],
    )


def test_weighted_modifiers_returns_perfect_agreement_for_identical_data(suppress_ui):
    df = _df(
        [
            ("obs1", 0.0, 1.0, "S", "A", "m1", ""),
            ("obs1", 1.0, 2.0, "S", "B", "", "n1"),
            ("obs2", 0.0, 1.0, "S", "A", "m1", ""),
            ("obs2", 1.0, 2.0, "S", "B", "", "n1"),
        ],
        modifier_columns=[MOD_A, MOD_B],
    )

    result_df, result_text = plugin.run(df)

    assert result_df.loc["obs1", "obs2"] == "1.000"
    assert result_df.loc["obs2", "obs1"] == "1.000"
    assert "obs1 - obs2" in result_text
    assert "Event weight=1.0" in result_text
    assert suppress_ui == []


def test_modifier_value_changes_label_and_kappa(monkeypatch):
    monkeypatch.setattr(plugin.QInputDialog, "getInt", lambda *args, **kwargs: (3, True))
    monkeypatch.setattr(plugin.QInputDialog, "getDouble", lambda *args, **kwargs: (1.0, True))
    monkeypatch.setattr(plugin.QMessageBox, "warning", lambda *args, **kwargs: None)

    df = _df(
        [
            ("obs1", 0.0, 1.0, "S", "A", "m1"),
            ("obs1", 1.0, 2.0, "S", "B", ""),
            ("obs2", 0.0, 1.0, "S", "A", "m2"),
            ("obs2", 1.0, 2.0, "S", "B", ""),
        ],
        modifier_columns=[MOD_A],
    )

    result_df, _ = plugin.run(df)

    assert result_df.loc["obs1", "obs2"] == "0.333"


def test_event_weight_changes_event_disagreement_impact_with_modifiers(monkeypatch):
    monkeypatch.setattr(plugin.QInputDialog, "getInt", lambda *args, **kwargs: (3, True))
    monkeypatch.setattr(plugin.QMessageBox, "warning", lambda *args, **kwargs: None)

    df = _df(
        [
            ("obs1", 0.0, 1.0, "S", "A", "seg"),
            ("obs1", 1.0, 2.0, "S", "B", "seg"),
            ("obs1", 1.5, 1.5, "S", "A", "evt"),
            ("obs2", 0.0, 1.0, "S", "A", "seg"),
            ("obs2", 1.0, 2.0, "S", "B", "seg"),
        ],
        modifier_columns=[MOD_A],
    )

    monkeypatch.setattr(plugin.QInputDialog, "getDouble", lambda *args, **kwargs: (0.0, True))
    result_df_zero, _ = plugin.run(df.copy())

    monkeypatch.setattr(plugin.QInputDialog, "getDouble", lambda *args, **kwargs: (1.0, True))
    result_df_one, _ = plugin.run(df.copy())

    assert result_df_zero.loc["obs1", "obs2"] == "1.000"
    assert result_df_one.loc["obs1", "obs2"] == "0.500"


def test_nan_pairs_show_single_aggregated_warning_with_modifiers(monkeypatch):
    monkeypatch.setattr(plugin.QInputDialog, "getInt", lambda *args, **kwargs: (3, True))
    monkeypatch.setattr(plugin.QInputDialog, "getDouble", lambda *args, **kwargs: (1.0, True))
    warning_calls = []

    def _warning(parent, title, text):
        warning_calls.append((title, text))

    monkeypatch.setattr(plugin.QMessageBox, "warning", _warning)

    df = _df(
        [
            ("obs1", 0.0, 0.0, "S", "X", "m"),
            ("obs2", 0.0, 0.0, "S", "X", "m"),
            ("obs3", 0.0, 0.0, "S", "X", "m"),
        ],
        modifier_columns=[MOD_X],
    )

    result_df, _ = plugin.run(df)

    assert warning_calls and len(warning_calls) == 1
    title, text = warning_calls[0]
    assert title == "Cohen's Kappa not defined (NaN)"
    assert "- obs1 vs obs2" in text
    assert "- obs2 vs obs3" in text
    assert result_df.loc["obs1", "obs2"] == "NaN"
    assert result_df.loc["obs3", "obs3"] == "NaN"
