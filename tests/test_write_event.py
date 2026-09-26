from decimal import Decimal
from pathlib import Path
from types import SimpleNamespace

import pytest

from boris import config as cfg
from boris import write_event


class RecordingLabel:
    def __init__(self):
        self.text = ""

    def setText(self, text):
        self.text = text


class RecordingWindow:
    def __init__(self, observation_type, tmp_path, events=None):
        self.observationId = "obs"
        self.playerType = observation_type
        self.currentSubject = "Alice"
        self.liveObservationStarted = True
        self.projectFileName = str(tmp_path / "project.boris")
        self.config_param = {"close_the_same_current_event": True}
        self.subject_name_index = {"Alice": "subject-1"}
        self.state_behaviors_codes = ["state", "other state"]
        self.plot_data = {}
        self.lbCurrentStates = RecordingLabel()
        self.calls = []
        self.same_event = False
        self.current_states = {"subject-1": [], "": []}
        self.final_states = {"subject-1": [], "": []}

        self.pj = {
            cfg.OBSERVATIONS: {
                self.observationId: {
                    cfg.TYPE: observation_type,
                    cfg.EVENTS: events or [],
                    cfg.TIME_OFFSET: "0",
                    cfg.DIRECTORIES_LIST: [],
                }
            },
            cfg.SUBJECTS: {"subject-1": {cfg.SUBJECT_NAME: "Alice"}},
            cfg.ETHOGRAM: {
                "state": {cfg.BEHAVIOR_CODE: "state", cfg.TYPE: cfg.STATE_EVENT, cfg.MODIFIERS: {}},
                "other": {cfg.BEHAVIOR_CODE: "other state", cfg.TYPE: cfg.STATE_EVENT, cfg.MODIFIERS: {}},
                "point": {cfg.BEHAVIOR_CODE: "point", cfg.TYPE: cfg.POINT_EVENT, cfg.MODIFIERS: {}},
            },
        }
        player = SimpleNamespace(
            playlist=[{"filename": str(tmp_path / "media.mp4")}], playlist_pos=0, pause=False, time_pos=Decimal("1")
        )
        self.dw_player = [SimpleNamespace(player=player)]

    def checkSameEvent(self, *_):
        return self.same_event

    def load_tw_events(self, observation_id):
        self.calls.append(("load", observation_id))

    def project_changed(self):
        self.calls.append(("changed",))

    def get_events_current_row(self):
        self.calls.append(("current row",))

    def getLaps(self):
        return Decimal("100")

    def show_current_states_in_subjects_table(self):
        self.calls.append(("show states",))

    def pause_video(self):
        self.calls.append(("pause",))

    def play_video(self):
        self.calls.append(("play",))


@pytest.fixture
def write_event_dependencies(monkeypatch):
    dialogs = []
    undo_messages = []

    monkeypatch.setattr(write_event.dialog, "MessageDialog", lambda *args: dialogs.append(args))
    monkeypatch.setattr(write_event.event_operations, "fill_events_undo_list", lambda _, message: undo_messages.append(message))

    def current_states(window):
        def get_states(*_, include_modifiers=False):
            return window.final_states if include_modifiers else window.current_states

        return get_states

    return SimpleNamespace(dialogs=dialogs, undo_messages=undo_messages, current_states=current_states)


def event(code="point", **values):
    result = {cfg.BEHAVIOR_CODE: code, cfg.MODIFIERS: {}, cfg.EXCLUDED: "", cfg.TYPE: cfg.POINT_EVENT}
    result.update(values)
    return result


def install_states(monkeypatch, dependencies, window):
    monkeypatch.setattr(write_event.util, "get_current_states_modifiers_by_subject", dependencies.current_states(window))


@pytest.mark.parametrize("observation_type", [cfg.LIVE, cfg.MEDIA, cfg.IMAGES])
def test_add_event_uses_the_observation_format(monkeypatch, tmp_path, write_event_dependencies, observation_type):
    window = RecordingWindow(observation_type, tmp_path)
    install_states(monkeypatch, write_event_dependencies, window)
    values = {cfg.SUBJECT: "Bob", cfg.COMMENT: "note"}
    if observation_type == cfg.MEDIA:
        values[cfg.FRAME_INDEX] = Decimal("42")
    if observation_type == cfg.IMAGES:
        values[cfg.IMAGE_INDEX] = Decimal("2")
        values[cfg.IMAGE_PATH] = str(tmp_path / "images" / "two.jpg")

    assert write_event.write_event(window, event(**values), Decimal("3")) == 0

    saved = window.pj[cfg.OBSERVATIONS][window.observationId][cfg.EVENTS]
    assert saved[0][:5] == [Decimal("3"), "Bob", "point", "", "note"]
    if observation_type == cfg.MEDIA:
        assert saved[0][5] == Decimal("42")
    if observation_type == cfg.IMAGES:
        assert saved[0][5:] == [Decimal("2"), "images/two.jpg"]
    assert write_event_dependencies.undo_messages == ["Undo last event insertion"]
    assert window.calls[-4:] == [("load", "obs"), ("changed",), ("current row",), ("show states",)]


@pytest.mark.parametrize("observation_type", [cfg.LIVE, cfg.MEDIA, cfg.IMAGES])
def test_edit_event_replaces_and_sorts_the_observation(monkeypatch, tmp_path, write_event_dependencies, observation_type):
    if observation_type == cfg.IMAGES:
        events = [[Decimal("0"), "Alice", "point", "", "", Decimal("4"), "four.jpg"]]
        values = {"row": 0, cfg.IMAGE_INDEX: Decimal("2"), cfg.IMAGE_PATH: str(tmp_path / "two.jpg")}
    elif observation_type == cfg.MEDIA:
        events = [[Decimal("4"), "Alice", "point", "", "", cfg.NA]]
        values = {"row": 0, cfg.FRAME_INDEX: Decimal("24")}
    else:
        events = [[Decimal("4"), "Alice", "point", "", ""]]
        values = {"row": 0}
    window = RecordingWindow(observation_type, tmp_path, events)
    install_states(monkeypatch, write_event_dependencies, window)

    assert write_event.write_event(window, event(**{cfg.SUBJECT: "Bob", cfg.COMMENT: "edited", **values}), Decimal("2")) == 0

    saved = window.pj[cfg.OBSERVATIONS]["obs"][cfg.EVENTS][0]
    assert saved[:5] == [Decimal("2"), "Bob", "point", "", "edited"]
    assert write_event_dependencies.undo_messages == ["Undo last event edition"]
    if observation_type == cfg.MEDIA:
        assert saved[5] == Decimal("24")
    if observation_type == cfg.IMAGES:
        assert saved[5:] == [Decimal("2"), "two.jpg"]


def test_returns_for_empty_event_and_live_interval_errors(monkeypatch, tmp_path, write_event_dependencies):
    window = RecordingWindow(cfg.LIVE, tmp_path)
    install_states(monkeypatch, write_event_dependencies, window)
    window.pj[cfg.OBSERVATIONS]["obs"][cfg.OBSERVATION_TIME_INTERVAL] = [Decimal("2"), Decimal("5")]

    assert write_event.write_event(window, None, Decimal("3")) == 1
    assert write_event.write_event(window, event(), Decimal("1")) == 1
    window.liveObservationStarted = False
    assert write_event.write_event(window, event(), Decimal("NaN")) == 1
    assert len(write_event_dependencies.dialogs) == 2
    assert not window.calls


@pytest.mark.parametrize("observation_type", [cfg.LIVE, cfg.MEDIA, cfg.IMAGES])
def test_returns_when_an_event_would_be_duplicated(monkeypatch, tmp_path, write_event_dependencies, observation_type):
    existing = [Decimal("3"), "Alice", "point", "", ""]
    values = {}
    if observation_type == cfg.MEDIA:
        existing.append(cfg.NA)
    elif observation_type == cfg.IMAGES:
        existing.extend([Decimal("3"), "three.jpg"])
        values = {cfg.IMAGE_INDEX: Decimal("3"), cfg.IMAGE_PATH: str(tmp_path / "three.jpg")}
    window = RecordingWindow(observation_type, tmp_path, [existing])
    window.same_event = True
    install_states(monkeypatch, write_event_dependencies, window)

    assert write_event.write_event(window, event(**values), Decimal("3")) == 1
    assert len(write_event_dependencies.dialogs) == 1
    assert write_event_dependencies.undo_messages == []


@pytest.mark.parametrize("observation_type", [cfg.LIVE, cfg.IMAGES])
def test_returns_when_an_edited_position_would_be_duplicated(monkeypatch, tmp_path, write_event_dependencies, observation_type):
    if observation_type == cfg.IMAGES:
        events = [[Decimal("0"), "Alice", "point", "", "", Decimal("1"), "one.jpg"]]
        values = {"row": 0, cfg.IMAGE_INDEX: Decimal("2"), cfg.IMAGE_PATH: str(tmp_path / "two.jpg")}
        mem_time = Decimal("0")
    else:
        events = [[Decimal("1"), "Alice", "point", "", ""]]
        values = {"row": 0}
        mem_time = Decimal("2")
    window = RecordingWindow(observation_type, tmp_path, events)
    window.same_event = True
    install_states(monkeypatch, write_event_dependencies, window)

    assert write_event.write_event(window, event(**values), mem_time) == 1
    assert len(write_event_dependencies.dialogs) == 1


def test_media_offsets_creation_time_and_timestamp_range(monkeypatch, tmp_path, write_event_dependencies):
    window = RecordingWindow(cfg.MEDIA, tmp_path)
    observation = window.pj[cfg.OBSERVATIONS]["obs"]
    observation[cfg.TIME_OFFSET] = "1.2349"
    observation[cfg.MEDIA_CREATION_DATE_AS_OFFSET] = True
    observation[cfg.MEDIA_INFO] = {cfg.MEDIA_CREATION_TIME: {Path(window.dw_player[0].player.playlist[0]["filename"]).as_posix(): "10"}}
    install_states(monkeypatch, write_event_dependencies, window)

    assert write_event.write_event(window, event(), Decimal("2")) == 0
    assert observation[cfg.EVENTS][0][0] == Decimal("13.235")

    range_window = RecordingWindow(cfg.MEDIA, tmp_path)
    install_states(monkeypatch, write_event_dependencies, range_window)
    assert write_event.write_event(range_window, event(), Decimal("2147483648")) == 1
    assert len(write_event_dependencies.dialogs) == 1


def test_modifiers_from_map_and_external_data_are_saved(monkeypatch, tmp_path, write_event_dependencies):
    window = RecordingWindow(cfg.LIVE, tmp_path)
    install_states(monkeypatch, write_event_dependencies, window)
    assert write_event.write_event(window, event(**{"from map": "mapped (shortcut)"}), Decimal("1")) == 0
    assert window.pj[cfg.OBSERVATIONS]["obs"][cfg.EVENTS][0][3] == "mapped"

    external_window = RecordingWindow(cfg.LIVE, tmp_path)
    external_window.plot_data = {
        "column": SimpleNamespace(y_label="temperature", lb_value=SimpleNamespace(text=lambda: "17.5"))
    }
    install_states(monkeypatch, write_event_dependencies, external_window)
    modifiers = {"0": {"type": cfg.EXTERNAL_DATA_MODIFIER, "name": "Temperature"}}
    assert write_event.write_event(external_window, event(**{cfg.MODIFIERS: modifiers}), Decimal("1")) == 0
    assert external_window.pj[cfg.OBSERVATIONS]["obs"][cfg.EVENTS][0][3] == "17.5"


def test_selector_modifiers_pause_and_resume_media(monkeypatch, tmp_path, write_event_dependencies):
    window = RecordingWindow(cfg.MEDIA, tmp_path)
    install_states(monkeypatch, write_event_dependencies, window)

    class Selector:
        def __init__(self, *_):
            pass

        def exec_(self):
            return True

        def get_modifiers(self):
            return {
                "0": {"type": cfg.SINGLE_SELECTION, "selected": ["one"]},
                "1": {"type": cfg.MULTI_SELECTION, "selected": ["two", "three"]},
                "2": {"type": cfg.NUMERIC_MODIFIER, "selected": "4"},
            }

    monkeypatch.setattr(write_event.select_modifiers, "ModifiersList", Selector)
    modifiers = {
        "0": {"type": cfg.SINGLE_SELECTION},
        "1": {"type": cfg.MULTI_SELECTION},
        "2": {"type": cfg.NUMERIC_MODIFIER},
    }

    assert write_event.write_event(window, event(**{cfg.MODIFIERS: modifiers}), Decimal("1")) == 0
    assert window.pj[cfg.OBSERVATIONS]["obs"][cfg.EVENTS][0][3] == "one|two,three|4"
    assert ("pause",) in window.calls
    assert ("play",) in window.calls


def test_selector_cancellation_does_not_save_or_create_undo_entry(monkeypatch, tmp_path, write_event_dependencies):
    window = RecordingWindow(cfg.LIVE, tmp_path)
    install_states(monkeypatch, write_event_dependencies, window)

    class CancelledSelector:
        def __init__(self, *_):
            pass

        def exec_(self):
            return False

    monkeypatch.setattr(write_event.select_modifiers, "ModifiersList", CancelledSelector)
    assert write_event.write_event(window, event(**{cfg.MODIFIERS: {"0": {"type": cfg.SINGLE_SELECTION}}}), Decimal("1")) is None
    assert window.pj[cfg.OBSERVATIONS]["obs"][cfg.EVENTS] == []
    assert write_event_dependencies.undo_messages == []


def test_external_modifier_is_preserved_while_editing(monkeypatch, tmp_path, write_event_dependencies):
    window = RecordingWindow(cfg.LIVE, tmp_path, [[Decimal("1"), "Alice", "point", "saved", ""]])
    install_states(monkeypatch, write_event_dependencies, window)
    modifiers = {"0": {"type": cfg.EXTERNAL_DATA_MODIFIER, "name": "temperature"}}

    assert (
        write_event.write_event(
            window,
            event(**{"row": 0, "original_modifiers": "saved", cfg.MODIFIERS: modifiers}),
            Decimal("1"),
        )
        == 0
    )
    assert window.pj[cfg.OBSERVATIONS]["obs"][cfg.EVENTS][0][3] == "saved"


@pytest.mark.parametrize("paused, time_pos", [(True, Decimal("1")), (False, None)])
def test_selector_handles_paused_and_stopped_media(monkeypatch, tmp_path, write_event_dependencies, paused, time_pos):
    window = RecordingWindow(cfg.MEDIA, tmp_path)
    window.dw_player[0].player.pause = paused
    window.dw_player[0].player.time_pos = time_pos
    install_states(monkeypatch, write_event_dependencies, window)

    class Selector:
        def __init__(self, *_):
            pass

        def exec_(self):
            return True

        def get_modifiers(self):
            return {"0": {"type": cfg.SINGLE_SELECTION, "selected": ["choice"]}}

    monkeypatch.setattr(write_event.select_modifiers, "ModifiersList", Selector)
    assert write_event.write_event(window, event(**{cfg.MODIFIERS: {"0": {"type": cfg.SINGLE_SELECTION}}}), Decimal("1")) == 0
    assert ("pause",) not in window.calls
    assert ("play",) not in window.calls


def test_ask_at_stop_does_not_request_modifiers_for_a_start(monkeypatch, tmp_path, write_event_dependencies):
    window = RecordingWindow(cfg.LIVE, tmp_path)
    install_states(monkeypatch, write_event_dependencies, window)
    modifiers = {"0": {"type": cfg.EXTERNAL_DATA_MODIFIER, "name": "temperature", "ask at stop": True}}

    assert write_event.write_event(window, event("state", **{cfg.TYPE: cfg.STATE_EVENT, cfg.MODIFIERS: modifiers}), Decimal("1")) == 0
    assert window.pj[cfg.OBSERVATIONS]["obs"][cfg.EVENTS][0][3] == ""


def test_missing_unfocused_subject_state_does_not_prevent_a_point_event(monkeypatch, tmp_path, write_event_dependencies):
    window = RecordingWindow(cfg.LIVE, tmp_path)
    window.currentSubject = ""
    calls = 0

    def current_states(*_, include_modifiers=False):
        nonlocal calls
        calls += 1
        if include_modifiers:
            return {"": []}
        return {}

    monkeypatch.setattr(write_event.util, "get_current_states_modifiers_by_subject", current_states)

    assert write_event.write_event(window, event(), Decimal("1")) == 0
    assert window.pj[cfg.OBSERVATIONS]["obs"][cfg.EVENTS] == [[Decimal("1.000"), "", "point", "", ""]]
    assert calls == 2


def test_state_lookup_stops_at_the_event_position(monkeypatch, tmp_path, write_event_dependencies):
    events = [
        [Decimal("1"), "Alice", "state", "active", ""],
        [Decimal("3"), "Alice", "point", "", ""],
    ]
    window = RecordingWindow(cfg.LIVE, tmp_path, events)
    window.current_states = {"subject-1": ["state"], "": []}
    install_states(monkeypatch, write_event_dependencies, window)

    assert write_event.write_event(window, event(), Decimal("2")) == 0
    assert window.pj[cfg.OBSERVATIONS]["obs"][cfg.EVENTS][1] == [Decimal("2.000"), "Alice", "point", "", ""]


def test_excluding_state_with_ask_at_stop_updates_the_matching_start(monkeypatch, tmp_path, write_event_dependencies):
    events = [[Decimal("1"), "Alice", "state", "", ""], [Decimal("3"), "Alice", "point", "", ""]]
    window = RecordingWindow(cfg.LIVE, tmp_path, events)
    window.current_states = {"subject-1": ["state"], "": []}
    window.pj[cfg.ETHOGRAM]["state"][cfg.MODIFIERS] = {
        "0": {"type": cfg.SINGLE_SELECTION, "ask at stop": True},
        "1": {"type": cfg.NUMERIC_MODIFIER},
    }
    install_states(monkeypatch, write_event_dependencies, window)

    class Selector:
        def __init__(self, *_args, **_kwargs):
            pass

        def exec_(self):
            return True

        def get_modifiers(self):
            return {
                "0": {"type": cfg.SINGLE_SELECTION, "selected": ["stop choice"]},
                "1": {"type": cfg.NUMERIC_MODIFIER, "selected": "6"},
            }

    monkeypatch.setattr(write_event.select_modifiers, "ModifiersList", Selector)
    assert write_event.write_event(window, event(**{cfg.EXCLUDED: "state"}), Decimal("2")) == 0
    assert window.pj[cfg.OBSERVATIONS]["obs"][cfg.EVENTS] == [
        [Decimal("1"), "Alice", "state", "stop choice|6", ""],
        [Decimal("1.999"), "Alice", "state", "stop choice|6", ""],
        [Decimal("2.000"), "Alice", "point", "", ""],
        [Decimal("3"), "Alice", "point", "", ""],
    ]


def test_cancelling_an_excluded_state_modifier_does_not_save_the_event(monkeypatch, tmp_path, write_event_dependencies):
    events = [[Decimal("1"), "Alice", "state", "", ""]]
    window = RecordingWindow(cfg.LIVE, tmp_path, events)
    window.current_states = {"subject-1": ["state"], "": []}
    window.pj[cfg.ETHOGRAM]["state"][cfg.MODIFIERS] = {"0": {"type": cfg.SINGLE_SELECTION, "ask at stop": True}}
    install_states(monkeypatch, write_event_dependencies, window)

    class CancelledSelector:
        def __init__(self, *_args, **_kwargs):
            pass

        def exec_(self):
            return False

    monkeypatch.setattr(write_event.select_modifiers, "ModifiersList", CancelledSelector)

    assert write_event.write_event(window, event(**{cfg.EXCLUDED: "state"}), Decimal("2")) is None
    assert window.pj[cfg.OBSERVATIONS]["obs"][cfg.EVENTS] == events


def test_ask_at_stop_assigns_the_start_modifier(monkeypatch, tmp_path, write_event_dependencies):
    events = [[Decimal("1"), "Alice", "state", "", ""], [Decimal("2"), "Alice", "point", "", ""]]
    window = RecordingWindow(cfg.LIVE, tmp_path, events)
    window.current_states = {"subject-1": ["state"], "": []}
    install_states(monkeypatch, write_event_dependencies, window)
    modifiers = {"0": {"type": cfg.EXTERNAL_DATA_MODIFIER, "name": "temperature", "ask at stop": True}}
    window.plot_data = {"temperature": SimpleNamespace(y_label="temperature", lb_value=SimpleNamespace(text=lambda: "20"))}

    assert write_event.write_event(window, event("state", **{cfg.TYPE: cfg.STATE_EVENT, cfg.MODIFIERS: modifiers}), Decimal("2")) == 0
    assert window.pj[cfg.OBSERVATIONS]["obs"][cfg.EVENTS] == [
        [Decimal("1"), "Alice", "state", "20", ""],
        [Decimal("2"), "Alice", "point", "", ""],
        [Decimal("2.000"), "Alice", "state", "20", ""],
    ]


def test_current_state_is_closed_with_its_modifier(monkeypatch, tmp_path, write_event_dependencies):
    events = [[Decimal("1"), "Alice", "state", "active", ""]]
    window = RecordingWindow(cfg.LIVE, tmp_path, events)
    window.current_states = {"subject-1": ["state"], "": []}
    install_states(monkeypatch, write_event_dependencies, window)

    assert write_event.write_event(window, event("state", **{cfg.TYPE: cfg.STATE_EVENT}), Decimal("2")) == 0
    assert window.pj[cfg.OBSERVATIONS]["obs"][cfg.EVENTS][-1] == [Decimal("2"), "Alice", "state", "active", ""]


@pytest.mark.parametrize("observation_type", [cfg.LIVE, cfg.MEDIA, cfg.IMAGES])
def test_excluded_current_state_is_closed(monkeypatch, tmp_path, write_event_dependencies, observation_type):
    if observation_type == cfg.IMAGES:
        events = [[Decimal("0"), "Alice", "state", "active", "", Decimal("1"), "one.jpg"]]
        values = {cfg.IMAGE_INDEX: Decimal("2"), cfg.IMAGE_PATH: str(tmp_path / "two.jpg")}
        mem_time = Decimal("20")
    elif observation_type == cfg.MEDIA:
        events = [[Decimal("1"), "Alice", "state", "active", "", cfg.NA]]
        values = {}
        mem_time = Decimal("2")
    else:
        events = [[Decimal("1"), "Alice", "state", "active", ""]]
        values = {}
        mem_time = Decimal("2")
    window = RecordingWindow(observation_type, tmp_path, events)
    window.current_states = {"subject-1": ["state"], "": []}
    install_states(monkeypatch, write_event_dependencies, window)

    assert write_event.write_event(window, event("point", **{cfg.EXCLUDED: "state", **values}), mem_time) == 0
    saved = window.pj[cfg.OBSERVATIONS]["obs"][cfg.EVENTS]
    stop = next(row for row in saved if row[2] == "state" and row != events[0])
    assert stop[3] == "active"
    if observation_type == cfg.IMAGES:
        assert stop[5:] == [Decimal("2"), "two.jpg"]
    else:
        assert stop[0] == mem_time - Decimal("0.001")
