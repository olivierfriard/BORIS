import copy
import os
from pathlib import Path
import sys
from decimal import Decimal
from types import SimpleNamespace

import pytest
from PySide6.QtWidgets import QApplication, QTableView

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from boris import config as cfg


@pytest.fixture(scope="module")
def core_module():
    # Core parses command-line arguments and installs an exception hook on import.
    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setattr(sys, "argv", ["boris"])
        monkeypatch.setattr(sys, "excepthook", sys.excepthook)
        from boris import core

    return core


@pytest.fixture(scope="module")
def application():
    with pytest.MonkeyPatch.context() as monkeypatch:
        monkeypatch.setenv("QT_QPA_PLATFORM", os.environ.get("QT_QPA_PLATFORM", "offscreen"))
        app = QApplication.instance() or QApplication([])
        yield app


@pytest.fixture
def populate(core_module, application):
    views = []

    def populate_events(rows, observation_type=cfg.LIVE, state_codes=("s", "t"), subjects_filter=(), behaviors_filter=()):
        events = []
        for idx, (subject, code, modifier) in enumerate(rows):
            event = [Decimal(idx), subject, code, modifier, "comment"]
            if observation_type in (cfg.MEDIA, cfg.VIEWER_MEDIA):
                event.append(Decimal(idx * 25))
            elif observation_type in (cfg.IMAGES, cfg.VIEWER_IMAGES):
                event.extend([idx, f"image{idx}.jpg"])
            events.append(event)

        view = QTableView()
        views.append(view)
        window = SimpleNamespace(
            tv_events=view,
            playerType=observation_type,
            pj={
                cfg.ETHOGRAM: {
                    str(idx): {cfg.BEHAVIOR_CODE: code, cfg.TYPE: cfg.STATE_EVENT} for idx, code in enumerate(state_codes)
                },
                cfg.OBSERVATIONS: {"obs": {cfg.EVENTS: events}},
            },
        )
        original_events = copy.deepcopy(events)
        core_module.MainWindow.populate_tv_events(
            window,
            "obs",
            [field.capitalize() for field in cfg.TW_EVENTS_FIELDS[observation_type]],
            cfg.HHMMSS,
            behaviors_filter,
            subjects_filter,
        )
        assert events == original_events
        assert view.model().rowCount() == len(window.event_state)
        return window

    yield populate_events

    for view in views:
        view.deleteLater()
    application.processEvents()


@pytest.mark.parametrize("observation_type", [cfg.LIVE, cfg.MEDIA, cfg.IMAGES, cfg.VIEWER_LIVE, cfg.VIEWER_MEDIA, cfg.VIEWER_IMAGES])
def test_state_events_alternate_independently(populate, observation_type):
    window = populate(
        [
            ("A", "s", ""),
            ("A", "p", ""),
            ("B", "s", ""),
            ("A", "s", "m"),
            ("A", "s", ""),
            ("A", "t", ""),
            ("B", "s", ""),
            ("A", "s", "m"),
            ("A", "t", ""),
            ("", "s", ""),
            ("", "s", ""),
        ],
        observation_type=observation_type,
    )

    assert [row[-1] for row in window.event_state] == [
        cfg.START, "", cfg.START, cfg.START, cfg.STOP, cfg.START, cfg.STOP, cfg.STOP, cfg.STOP, cfg.START, cfg.STOP
    ]
    assert window.tv_idx2events_idx == list(range(11))


@pytest.mark.parametrize("rows", [[], [("A", "p", ""), ("A", "unknown", "")]])
def test_empty_ethogram_has_no_state_events(populate, rows):
    window = populate(rows, state_codes=())

    assert [row[-1] for row in window.event_state] == [""] * len(rows)


@pytest.mark.parametrize(
    "first, second",
    [
        (("A|s", "t", ""), ("A", "s|t", "")),
        (("A", "s", "m|x"), ("A", "s|m", "x")),
    ],
)
def test_pipe_characters_do_not_merge_state_groups(populate, first, second):
    window = populate([first, second, first, second], state_codes=(first[1], second[1]))

    assert [row[-1] for row in window.event_state] == [cfg.START, cfg.START, cfg.STOP, cfg.STOP]


def test_filtered_events_keep_states_and_source_indices(populate):
    window = populate(
        [("A", "s", ""), ("B", "s", ""), ("A", "p", ""), ("A", "s", ""), ("B", "s", "")],
        subjects_filter=("A",),
        behaviors_filter=("s",),
    )

    assert [row[-1] for row in window.event_state] == [cfg.START, cfg.STOP]
    assert window.tv_idx2events_idx == [0, 3]


def test_refresh_recalculates_states_after_event_deletion(populate, core_module):
    window = populate([("A", "s", ""), ("A", "s", ""), ("A", "s", "")])
    del window.pj[cfg.OBSERVATIONS]["obs"][cfg.EVENTS][0]

    core_module.MainWindow.populate_tv_events(
        window, "obs", [field.capitalize() for field in cfg.TW_EVENTS_FIELDS[cfg.LIVE]], cfg.HHMMSS, (), ()
    )

    assert [row[-1] for row in window.event_state] == [cfg.START, cfg.STOP]
    assert window.tv_idx2events_idx == [0, 1]


@pytest.fixture(params=[cfg.MEDIA, cfg.LIVE, cfg.IMAGES])
def duplicate_events_window(request):
    observation_type = request.param
    events = [
        [Decimal("1.250"), "A", "s", "m1", "first comment"],
        [Decimal("2.500"), "B", "p", "m2", "second comment"],
        [Decimal("3.750"), "", "s", "", "third comment"],
    ]
    if observation_type == cfg.MEDIA:
        for event in events:
            event.append(Decimal("NaN"))
    elif observation_type == cfg.IMAGES:
        for idx, event in enumerate(events):
            event[0] = Decimal("NaN")
            event.extend([idx + 10, f"image{idx}.jpg"])
    return SimpleNamespace(pj={cfg.OBSERVATIONS: {"obs": {cfg.TYPE: observation_type, cfg.EVENTS: events}}})


@pytest.mark.parametrize("row_idx", [0, 1, 2])
def test_same_event_finds_each_position(core_module, duplicate_events_window, row_idx):
    observation = duplicate_events_window.pj[cfg.OBSERVATIONS]["obs"]
    row = observation[cfg.EVENTS][row_idx]
    position = row[5] if observation[cfg.TYPE] == cfg.IMAGES else row[0]

    assert core_module.MainWindow.checkSameEvent(duplicate_events_window, "obs", position, row[1], row[2]) is True


@pytest.mark.parametrize("different_field", ["position", "subject", "code"])
def test_same_event_requires_all_three_fields(core_module, duplicate_events_window, different_field):
    observation = duplicate_events_window.pj[cfg.OBSERVATIONS]["obs"]
    position = 10 if observation[cfg.TYPE] == cfg.IMAGES else Decimal("1.250")
    query = {"position": position, "subject": "A", "code": "s"}
    query[different_field] = Decimal("99") if different_field == "position" else "other"

    assert core_module.MainWindow.checkSameEvent(
        duplicate_events_window, "obs", query["position"], query["subject"], query["code"]
    ) is False


def test_same_event_handles_empty_observation(core_module, duplicate_events_window):
    duplicate_events_window.pj[cfg.OBSERVATIONS]["obs"][cfg.EVENTS].clear()

    assert core_module.MainWindow.checkSameEvent(duplicate_events_window, "obs", Decimal("1.250"), "A", "s") is False


def test_same_event_handles_unsorted_events_and_ignores_modifiers(core_module, duplicate_events_window):
    observation = duplicate_events_window.pj[cfg.OBSERVATIONS]["obs"]
    events = observation[cfg.EVENTS]
    events.reverse()
    events[-1][3:5] = ["changed modifier", "changed comment"]
    position = 10 if observation[cfg.TYPE] == cfg.IMAGES else Decimal("1.250")

    assert core_module.MainWindow.checkSameEvent(duplicate_events_window, "obs", position, "A", "s") is True


def test_same_event_stops_at_first_match(core_module, duplicate_events_window):
    observation = duplicate_events_window.pj[cfg.OBSERVATIONS]["obs"]
    # This invalid trailing row must never be accessed after a match.
    observation[cfg.EVENTS].append([])
    position = 10 if observation[cfg.TYPE] == cfg.IMAGES else Decimal("1.250")

    assert core_module.MainWindow.checkSameEvent(duplicate_events_window, "obs", position, "A", "s") is True
