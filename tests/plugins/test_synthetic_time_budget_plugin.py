from decimal import Decimal as dec
from pathlib import Path
import sys

PERSONAL_PLUGINS_DIR = Path("/home/olivier/projects/BORIS_plugins")
PROJECT_ROOT = Path(__file__).resolve().parents[2]

sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PERSONAL_PLUGINS_DIR))
import synthetic_time_budget as plugin

from boris import config as cfg


def event(time, subject, behavior, modifiers="", comment=""):
    return [dec(str(time)), subject, behavior, modifiers, comment]


def behavior(code, type_, modifiers=""):
    return {
        cfg.BEHAVIOR_CODE: code,
        cfg.TYPE: type_,
        cfg.MODIFIERS: modifiers,
        cfg.BEHAVIOR_CATEGORY: "",
    }


def media_observation(events, length=10, interval=None):
    return {
        cfg.TYPE: cfg.MEDIA,
        cfg.EVENTS: events,
        cfg.FILE: {"1": ["media.mp4"]},
        cfg.MEDIA_INFO: {cfg.LENGTH: {"media.mp4": dec(str(length))}},
        cfg.TIME_OFFSET: dec("0"),
        cfg.OBSERVATION_TIME_INTERVAL: interval or [0, 0],
    }


def project(observations, ethogram=None):
    return {
        cfg.ETHOGRAM: ethogram
        or {
            "0": behavior("A", cfg.STATE_EVENT),
            "1": behavior("B", cfg.STATE_EVENT),
            "2": behavior("P", cfg.POINT_EVENT),
        },
        cfg.SUBJECTS: {"0": {cfg.SUBJECT_NAME: "S1"}, "1": {cfg.SUBJECT_NAME: "S2"}},
        cfg.OBSERVATIONS: observations,
    }


def parameters(**overrides):
    params = {
        cfg.SELECTED_SUBJECTS: ["S1"],
        cfg.SELECTED_BEHAVIORS: ["A", "B", "P"],
        cfg.INCLUDE_MODIFIERS: False,
        cfg.EXCLUDE_NON_CODED_MODIFIERS: False,
        cfg.TIME_INTERVAL: cfg.TIME_FULL_OBS,
        cfg.START_TIME: None,
        cfg.END_TIME: None,
        cfg.EXCLUDED_BEHAVIORS: [],
    }
    params.update(overrides)
    return params


def data_row(data_report):
    return list(list(data_report)[-1])


def test_synthetic_time_budget_calculates_state_and_point_values():
    pj = project(
        {
            "obs1": media_observation(
                [
                    event(0, "S1", "A"),
                    event(4, "S1", "A"),
                    event(4, "S1", "B"),
                    event(10, "S1", "B"),
                    event(2, "S1", "P"),
                ]
            )
        }
    )

    ok, msg, report = plugin.synthetic_time_budget(pj, ["obs1"], parameters())

    assert ok, msg
    row = data_row(report)
    assert row[0:2] == ["obs1", "10.000"]
    assert row[2:7] == ["4.000", 1, "4.000", cfg.NA, "0.400"]
    assert row[7:12] == ["6.000", 1, "6.000", cfg.NA, "0.600"]
    assert row[12:17] == [cfg.NA, 1, cfg.NA, cfg.NA, cfg.NA]


def test_excluded_state_behavior_is_subtracted_from_total_time():
    pj = project(
        {
            "obs1": media_observation(
                [
                    event(0, "S1", "A"),
                    event(4, "S1", "A"),
                    event(4, "S1", "B"),
                    event(10, "S1", "B"),
                ]
            )
        }
    )

    ok, msg, report = plugin.synthetic_time_budget(
        pj,
        ["obs1"],
        parameters(**{cfg.SELECTED_BEHAVIORS: ["A", "B"], cfg.EXCLUDED_BEHAVIORS: ["B"]}),
    )

    assert ok, msg
    row = data_row(report)
    assert row[6] == "1.000"
    assert row[11] == "0.600"


def test_user_defined_time_interval_clips_state_events():
    pj = project({"obs1": media_observation([event(0, "S1", "A"), event(10, "S1", "A")])})

    ok, msg, report = plugin.synthetic_time_budget(
        pj,
        ["obs1"],
        parameters(
            **{
                cfg.SELECTED_BEHAVIORS: ["A"],
                cfg.TIME_INTERVAL: cfg.TIME_ARBITRARY_INTERVAL,
                cfg.START_TIME: dec("2"),
                cfg.END_TIME: dec("6"),
            },
        ),
    )

    assert ok, msg
    row = data_row(report)
    assert row[1] == "4.000"
    assert row[2:7] == ["4.000", 1, "4.000", cfg.NA, "1.000"]


def test_observation_time_interval_is_supported():
    pj = project(
        {
            "obs1": media_observation(
                [event(0, "S1", "A"), event(10, "S1", "A")],
                interval=[2, 6],
            )
        }
    )

    ok, msg, report = plugin.synthetic_time_budget(
        pj,
        ["obs1"],
        parameters(**{cfg.SELECTED_BEHAVIORS: ["A"], cfg.TIME_INTERVAL: cfg.TIME_OBS_INTERVAL}),
    )

    assert ok, msg
    assert data_row(report)[2:7] == ["4.000", 1, "4.000", cfg.NA, "1.000"]


def test_modifiers_can_include_all_ethogram_combinations():
    ethogram = {
        "0": behavior(
            "A",
            cfg.STATE_EVENT,
            {"0": {"name": "speed", "values": ["fast", "slow"]}},
        )
    }
    pj = project({"obs1": media_observation([event(0, "S1", "A", "fast"), event(5, "S1", "A", "fast")])}, ethogram)

    ok, msg, report = plugin.synthetic_time_budget(
        pj,
        ["obs1"],
        parameters(
            **{
                cfg.SELECTED_BEHAVIORS: ["A"],
                cfg.INCLUDE_MODIFIERS: True,
                cfg.EXCLUDE_NON_CODED_MODIFIERS: False,
            },
        ),
    )

    rows = [list(row) for row in report]
    assert ok, msg
    assert rows[2][2:17:5] == ["fast", "slow", "None"]
    assert data_row(report)[2] == "5.000"
    assert data_row(report)[7] == 0.0
    assert data_row(report)[12] == 0.0


def test_modifiers_can_be_limited_to_observed_values():
    ethogram = {
        "0": behavior(
            "A",
            cfg.STATE_EVENT,
            {"0": {"name": "speed", "values": ["fast", "slow"]}},
        )
    }
    pj = project({"obs1": media_observation([event(0, "S1", "A", "fast"), event(5, "S1", "A", "fast")])}, ethogram)

    ok, msg, report = plugin.synthetic_time_budget(
        pj,
        ["obs1"],
        parameters(
            **{
                cfg.SELECTED_BEHAVIORS: ["A"],
                cfg.INCLUDE_MODIFIERS: True,
                cfg.EXCLUDE_NON_CODED_MODIFIERS: True,
            },
        ),
    )

    assert ok, msg
    rows = [list(row) for row in report]
    assert rows[2][2:7] == ["fast"] * 5
    assert data_row(report)[2:7] == ["5.000", 1, "5.000", cfg.NA, "0.500"]


def test_run_uses_dialog_selection_for_excluded_behaviors(monkeypatch):
    pj = project(
        {
            "obs1": media_observation(
                [
                    event(0, "S1", "A"),
                    event(4, "S1", "A"),
                    event(4, "S1", "B"),
                    event(10, "S1", "B"),
                ]
            )
        }
    )
    monkeypatch.setattr(plugin, "ask_excluded_behaviors", lambda behaviors: (False, ["B"]))

    title, output = plugin.run(pj, parameters(**{cfg.SELECTED_BEHAVIORS: ["A", "B"]}))

    assert title == "Synthetic time budget"
    assert "1.000" in output
    assert "0.600" in output


def test_run_returns_canceled_message_when_dialog_is_canceled(monkeypatch):
    pj = project({"obs1": media_observation([event(0, "S1", "A"), event(5, "S1", "A")])})
    monkeypatch.setattr(plugin, "ask_excluded_behaviors", lambda behaviors: (True, []))

    assert plugin.run(pj, parameters(**{cfg.SELECTED_BEHAVIORS: ["A"]})) == ("Synthetic time budget", "Analysis canceled.")


def test_unpaired_state_events_return_error():
    pj = project({"obs1": media_observation([event(0, "S1", "A")])})

    ok, msg, report = plugin.synthetic_time_budget(pj, ["obs1"], parameters(**{cfg.SELECTED_BEHAVIORS: ["A"]}))

    assert not ok
    assert report is None
    assert "obs1" in msg
