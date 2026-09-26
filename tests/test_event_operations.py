"""Tests for event table operations."""

from collections import deque
from decimal import Decimal
from types import SimpleNamespace

import pytest
from PySide6.QtCore import Qt
from PySide6.QtWidgets import QAbstractItemView, QTableWidget, QTableWidgetItem

from boris import config as cfg
from boris import event_operations


class Value:
    def __init__(self):
        self.text = ""
        self.enabled = False

    def setText(self, text):
        self.text = text

    def setEnabled(self, enabled):
        self.enabled = enabled


class StatusBar:
    def __init__(self):
        self.messages = []

    def showMessage(self, text, timeout):
        self.messages.append((text, timeout))


class TitleWidget:
    def __init__(self):
        self.title = ""

    def setWindowTitle(self, title):
        self.title = title


class Owner:
    def __init__(self, qapp, player_type=cfg.LIVE, events=None):
        self.observationId = "obs"
        self.playerType = player_type
        self.image_idx = 1
        self.image_time_ref = Decimal("10")
        self.images_list = ["zero.jpg", "one.jpg", "two.jpg", "three.jpg"]
        self.currentSubject = "Alice"
        self.config_param = {"pause_before_addevent": False, "time_format": cfg.S}
        self.undo_queue = deque()
        self.undo_description = deque()
        self.actionUndo = Value()
        self.statusbar = StatusBar()
        self.dwEvents = TitleWidget()
        self.calls = []
        self.no_observation_calls = 0
        self.filtered_subjects = []
        self.filtered_behaviors = []
        if events is None:
            events = self.events_for_type(player_type)
        observation_type = cfg.IMAGES if player_type == cfg.VIEWER_IMAGES else player_type
        self.pj = {
            cfg.OBSERVATIONS: {"obs": {cfg.TYPE: observation_type, cfg.EVENTS: events}},
            cfg.SUBJECTS: {"0": {cfg.SUBJECT_NAME: "Alice"}, "1": {cfg.SUBJECT_NAME: "Bob"}},
            cfg.ETHOGRAM: {
                "0": {cfg.BEHAVIOR_CODE: "Run", cfg.MODIFIERS: {}},
                "1": {cfg.BEHAVIOR_CODE: "Sleep", cfg.MODIFIERS: {}},
            },
        }
        self.tv_events = QTableWidget(0, 1)
        self.refresh_table()

    @staticmethod
    def events_for_type(player_type):
        if player_type in (cfg.IMAGES, cfg.VIEWER_IMAGES):
            return [
                [Decimal("1"), "Alice", "Run", "m", "first", 1, "one.jpg"],
                [Decimal("3"), "Bob", "Sleep", "", "second", 3, "three.jpg"],
            ]
        if player_type in (cfg.MEDIA, cfg.VIEWER_MEDIA):
            return [[Decimal("1"), "Alice", "Run", "m", "first", 4], [Decimal("3"), "Bob", "Sleep", "", "second", 8]]
        return [[Decimal("1"), "Alice", "Run", "m", "first"], [Decimal("3"), "Bob", "Sleep", "", "second"]]

    @property
    def events(self):
        return self.pj[cfg.OBSERVATIONS][self.observationId][cfg.EVENTS]

    def refresh_table(self):
        self.tv_idx2events_idx = list(range(len(self.events)))
        self.tv_events.setRowCount(len(self.events))
        for row in range(len(self.events)):
            self.tv_events.setItem(row, 0, QTableWidgetItem(str(row)))

    def load_tw_events(self, observation_id):
        self.calls.append(("load", observation_id))
        self.refresh_table()

    def project_changed(self):
        self.calls.append(("changed",))

    def update_realtime_plot(self, **kwargs):
        self.calls.append(("plot", kwargs))

    def no_observation(self):
        self.no_observation_calls += 1

    def getLaps(self):
        return Decimal("9")

    def is_playing(self):
        return True

    def pause_video(self):
        self.calls.append(("pause",))

    def play_video(self):
        self.calls.append(("play",))

    def seek_mediaplayer(self, value):
        self.calls.append(("seek", value))
        return False

    def get_frame_index(self):
        return 42

    def full_event(self, key):
        return {
            cfg.BEHAVIOR_CODE: self.pj[cfg.ETHOGRAM][key][cfg.BEHAVIOR_CODE],
            cfg.MODIFIERS: self.pj[cfg.ETHOGRAM][key][cfg.MODIFIERS],
        }


class Combo:
    def __init__(self):
        self.items = []
        self.index = 0

    def addItems(self, values):
        self.items.extend(values)

    def findText(self, value, *_):
        return self.items.index(value)

    def setCurrentIndex(self, index):
        self.index = index

    def currentText(self):
        return self.items[self.index]


class PlainText:
    def __init__(self, text=""):
        self.text = text

    def toPlainText(self):
        return self.text

    def setPlainText(self, text):
        self.text = text


class Check:
    def __init__(self, checked=False): self.checked = checked
    def isChecked(self): return self.checked
    def setChecked(self, checked): self.checked = checked


class Number:
    def __init__(self, value=0): self.number = value
    def value(self): return self.number


class FakeEventDialog:
    def __init__(self, *, accepted=True, time_value=Decimal("2"), image_idx=2):
        self.accepted = accepted
        self.time_widget = SimpleNamespace(get_time=lambda: time_value)
        self.cobSubject = Combo()
        self.cobCode = Combo()
        self.leComment = PlainText("note")
        self.sb_image_idx = Number(image_idx)
        self.cb_set_time_na = Check(False)
        self.pb_set_to_current_time = SimpleNamespace(setVisible=lambda *_: None)

    def setWindowTitle(self, title): self.title = title
    def exec_(self): return self.accepted
    def exec(self): return self.accepted


@pytest.fixture
def owner(qapp):
    result = Owner(qapp)
    yield result
    result.tv_events.deleteLater()
    qapp.processEvents()


@pytest.fixture
def messages(monkeypatch):
    result = []
    monkeypatch.setattr(event_operations.QMessageBox, "warning", lambda *args: result.append(("warning", args)))
    monkeypatch.setattr(event_operations.QMessageBox, "critical", lambda *args: result.append(("critical", args)))
    return result


def select_rows(owner, *rows):
    owner.tv_events.clearSelection()
    owner.tv_events.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)
    for row in rows:
        owner.tv_events.selectRow(row)


def test_read_event_field_returns_value_na_or_none():
    assert event_operations.read_event_field([Decimal("1"), "Alice"], cfg.LIVE, cfg.SUBJECT) == "Alice"
    assert event_operations.read_event_field([Decimal("1")], cfg.MEDIA, cfg.FRAME_INDEX) == cfg.NA
    assert event_operations.read_event_field([], cfg.LIVE, cfg.IMAGE_INDEX) is None


def test_filter_show_and_find_dialogs(monkeypatch, owner):
    monkeypatch.setattr(event_operations.select_subj_behav, "choose_obs_subj_behav_category", lambda *_args, **_kwargs: {})
    event_operations.filter_events(owner)
    assert owner.calls == []

    monkeypatch.setattr(
        event_operations.select_subj_behav,
        "choose_obs_subj_behav_category",
        lambda *_args, **_kwargs: {cfg.SELECTED_SUBJECTS: [cfg.NO_FOCAL_SUBJECT, "Alice"], cfg.SELECTED_BEHAVIORS: ["Run"]},
    )
    event_operations.filter_events(owner)
    assert owner.filtered_subjects == [cfg.NO_FOCAL_SUBJECT, "Alice", ""]
    assert owner.filtered_behaviors == ["Run"]
    assert "filtered" in owner.dwEvents.title
    event_operations.show_all_events(owner)
    assert owner.filtered_subjects == []
    assert "(filtered)" not in owner.dwEvents.title

    class Find:
        def __init__(self):
            self.clickSignal = SimpleNamespace(connect=lambda callback: setattr(self, "callback", callback))
        def setWindowFlags(self, flags): self.flags = flags
        def show(self): self.shown = True
    owner.click_signal_find_in_events = lambda *_: None
    select_rows(owner, 1)
    monkeypatch.setattr(event_operations.dialog, "FindInEvents", Find)
    event_operations.find_events(owner)
    assert owner.find_dialog.rowsToFind == {1}
    assert owner.find_dialog.currentIdx == -1 and owner.find_dialog.shown

    owner.click_signal_find_replace_in_events = lambda *_: None
    monkeypatch.setattr(event_operations.dialog, "FindReplaceEvents", Find)
    event_operations.find_replace_events(owner)
    assert owner.find_replace_dialog.currentIdx_idx == -1
    assert owner.undo_description[-1] == "Undo Find/Replace operations"


def test_undo_queue_and_deletions(monkeypatch, owner, messages):
    event_operations.undo_event_operation(owner)
    assert owner.statusbar.messages[-1][0] == "The Undo buffer is empty"
    event_operations.fill_events_undo_list(owner, "Undo change")
    owner.events[0][4] = "changed"
    event_operations.undo_event_operation(owner)
    assert owner.events[0][4] == "first"
    assert owner.actionUndo.text == "Undo" and not owner.actionUndo.enabled

    owner.observationId = ""
    event_operations.delete_all_events(owner)
    assert owner.no_observation_calls == 1
    owner.observationId = "obs"
    owner.tv_idx2events_idx = []
    event_operations.delete_all_events(owner)
    assert "No events" in messages[-1][1][2]
    owner.refresh_table()
    monkeypatch.setattr(event_operations.dialog, "MessageDialog", lambda *_: cfg.NO)
    event_operations.delete_all_events(owner)
    assert len(owner.events) == 2
    monkeypatch.setattr(event_operations.dialog, "MessageDialog", lambda *_: cfg.YES)
    event_operations.delete_all_events(owner)
    assert owner.events == []


def test_delete_selected_events_handles_missing_observation_and_selection(owner, messages):
    owner.observationId = ""
    event_operations.delete_selected_events(owner)
    assert owner.no_observation_calls == 1
    owner.observationId = "obs"
    event_operations.delete_selected_events(owner)
    assert "No event selected" in messages[-1][1][2]
    select_rows(owner, 0)
    event_operations.delete_selected_events(owner)
    assert len(owner.events) == 1


@pytest.mark.parametrize("text, expected", [("", None), ("1", "minus sign"), ("bad-2", "not recognized"), ("3-1", "initial time")])
def test_select_events_between_validates_input(monkeypatch, owner, messages, text, expected):
    monkeypatch.setattr(event_operations.QInputDialog, "getText", lambda *_: (text, True))
    event_operations.select_events_between_activated(owner)
    if expected:
        assert expected in messages[-1][1][2]
    else:
        assert owner.tv_events.selectedIndexes() == []


def test_select_events_between_selects_decimal_and_clock_ranges(monkeypatch, owner):
    monkeypatch.setattr(event_operations.QInputDialog, "getText", lambda *_: (" 1 - 3 ", True))
    event_operations.select_events_between_activated(owner)
    assert {index.row() for index in owner.tv_events.selectedIndexes()} == {0, 1}
    monkeypatch.setattr(event_operations.QInputDialog, "getText", lambda *_: ("00:00:01.000-00:00:01.000", True))
    event_operations.select_events_between_activated(owner)
    assert {index.row() for index in owner.tv_events.selectedIndexes()} == {0}


def test_comments_and_copy_paste_clipboard(monkeypatch, owner, messages, qapp):
    event_operations.add_comment(owner)
    assert "No event selected" in messages[-1][1][2]
    select_rows(owner, 0, 1)
    monkeypatch.setattr(event_operations.QInputDialog, "getText", lambda *_args, **_kwargs: ("updated", False))
    event_operations.add_comment(owner)
    monkeypatch.setattr(event_operations.QInputDialog, "getText", lambda *_args, **_kwargs: ("updated", True))
    event_operations.add_comment(owner)
    assert [event[4] for event in owner.events] == ["updated", "updated"]

    event_operations.copy_selected_events(owner)
    assert "updated" in qapp.clipboard().text()
    owner.tv_events.clearSelection()
    event_operations.copy_selected_events(owner)
    assert "No event selected" in messages[-1][1][2]

    qapp.clipboard().setText("bad")
    class InvalidBox:
        Warning = object()
        def __init__(self, *_): self.executed = False
        def windowFlags(self): return 0
        def setWindowFlags(self, flags): self.flags = flags
        def exec(self): self.executed = True
    monkeypatch.setattr(event_operations, "QMessageBox", InvalidBox)
    event_operations.paste_clipboard_to_events(owner)
    monkeypatch.undo()

    qapp.clipboard().setText("2\tBob\tRun\t\tnew")
    event_operations.paste_clipboard_to_events(owner)
    assert [Decimal("2"), "Bob", "Run", "", "new"] in owner.events


def test_add_frame_indexes_and_edit_time(monkeypatch, qapp, messages):
    live = Owner(qapp)
    event_operations.add_frame_indexes(live)
    assert not live.calls
    media = Owner(qapp, cfg.MEDIA)
    media.events.append(["NA", "", "", "", "", 0])
    event_operations.add_frame_indexes(media)
    assert media.events[0][-1] == 42
    media.events.pop()
    media.refresh_table()

    event_operations.edit_time_selected_events(live)
    assert "No event selected" in messages[-1][1][2]
    select_rows(media, 0, 1)
    class TimeDialog:
        def __init__(self, *_):
            self.label = Value()
            self.time_widget = SimpleNamespace(get_time=lambda: Decimal("2"))
        def setWindowTitle(self, title): self.title = title
        def exec_(self): return True
    monkeypatch.setattr(event_operations.dialog, "Ask_time", TimeDialog)
    monkeypatch.setattr(event_operations.dialog, "MessageDialog", lambda *_: cfg.YES)
    monkeypatch.setattr(event_operations.time, "sleep", lambda *_: None)
    event_operations.edit_time_selected_events(media)
    assert media.events[0][0] == Decimal("3")
    assert media.events[0][-1] == 42
    media.tv_events.deleteLater()
    live.tv_events.deleteLater()
    qapp.processEvents()


@pytest.mark.parametrize("player_type", [cfg.LIVE, cfg.MEDIA])
def test_add_event_creates_media_and_live_events(monkeypatch, qapp, player_type):
    window = Owner(qapp, player_type)
    window.config_param["pause_before_addevent"] = player_type == cfg.MEDIA
    captured = []
    monkeypatch.setattr(event_operations, "DlgEditEvent", lambda **_kwargs: FakeEventDialog())
    monkeypatch.setattr(event_operations.write_event, "write_event", lambda _owner, event, value: captured.append((event, value)))
    monkeypatch.setattr(event_operations.time, "sleep", lambda *_: None)

    event_operations.add_event(window)

    assert captured[0][0][cfg.SUBJECT] == "Alice"
    assert captured[0][0][cfg.COMMENT] == "note"
    assert captured[0][1] == Decimal("2")
    assert ("plot", {"force_plot": True}) in window.calls
    if player_type == cfg.MEDIA:
        assert captured[0][0][cfg.FRAME_INDEX] == 42
        assert ("pause",) in window.calls and ("play",) in window.calls
    window.tv_events.deleteLater()


def test_add_event_handles_early_returns_and_image_times(monkeypatch, qapp, messages):
    window = Owner(qapp)
    window.observationId = ""
    event_operations.add_event(window)
    assert window.no_observation_calls == 1
    window.observationId = "obs"
    window.pj[cfg.ETHOGRAM] = {}
    event_operations.add_event(window)
    assert "ethogram" in messages[-1][1][2]

    image = Owner(qapp, cfg.IMAGES)
    image.pj[cfg.OBSERVATIONS]["obs"][cfg.USE_EXIF_DATE] = True
    image.pj[cfg.OBSERVATIONS]["obs"][cfg.SUBSTRACT_FIRST_EXIF_DATE] = True
    captured = []
    monkeypatch.setattr(event_operations, "DlgEditEvent", lambda **_kwargs: FakeEventDialog(image_idx=2))
    monkeypatch.setattr(event_operations.write_event, "write_event", lambda _owner, event, value: captured.append((event, value)))
    monkeypatch.setattr(event_operations.util, "extract_exif_DateTimeOriginal", lambda *_: Decimal("15.6789"))
    event_operations.add_event(image)
    assert captured[0][0][cfg.IMAGE_PATH] == "two.jpg"
    assert captured[0][1] == Decimal("5.678")

    lapse = Owner(qapp, cfg.IMAGES)
    lapse.pj[cfg.OBSERVATIONS]["obs"][cfg.TIME_LAPSE] = Decimal("1.5")
    monkeypatch.setattr(event_operations.write_event, "write_event", lambda _owner, event, value: captured.append((event, value)))
    event_operations.add_event(lapse)
    assert captured[-1][1] == Decimal("3.000")
    for item in (window, image, lapse): item.tv_events.deleteLater()


def test_add_event_rejects_missing_time_or_image_index(monkeypatch, qapp, messages):
    live = Owner(qapp)
    monkeypatch.setattr(event_operations, "DlgEditEvent", lambda **_kwargs: FakeEventDialog(time_value=None))
    event_operations.add_event(live)
    assert "Select a time" in messages[-1][1][2]
    image = Owner(qapp, cfg.IMAGES)
    monkeypatch.setattr(event_operations, "DlgEditEvent", lambda **_kwargs: FakeEventDialog(image_idx=0))
    event_operations.add_event(image)
    assert "image index" in messages[-1][1][2]
    live.tv_events.deleteLater()
    image.tv_events.deleteLater()


def test_edit_selected_events_delegates_and_applies_subject_behavior_and_comment(monkeypatch, owner, messages):
    event_operations.edit_selected_events(owner)
    assert "No event selected" in messages[-1][1][2]
    select_rows(owner, 0)
    delegated = []
    monkeypatch.setattr(event_operations, "edit_event", lambda value: delegated.append(value))
    event_operations.edit_selected_events(owner)
    assert delegated == [owner]

    class MultiDialog:
        def __init__(self):
            self.all_subjects = []
            self.all_behaviors = []
            self.rbSubject = Check(True)
            self.rbBehavior = Check(False)
            self.rbComment = Check(False)
            self.newText = SimpleNamespace(selectedItems=lambda: [SimpleNamespace(text=lambda: "Bob")])
            self.commentText = SimpleNamespace(text=lambda: "")
        def exec_(self): return True
    select_rows(owner, 0, 1)
    monkeypatch.setattr(event_operations, "EditSelectedEvents", MultiDialog)
    event_operations.edit_selected_events(owner)
    assert [event[1] for event in owner.events] == ["Bob", "Bob"]

    class CommentDialog(MultiDialog):
        def __init__(self):
            super().__init__()
            self.rbSubject = Check(False)
            self.rbComment = Check(True)
            self.commentText = SimpleNamespace(text=lambda: "bulk")
    monkeypatch.setattr(event_operations, "EditSelectedEvents", CommentDialog)
    event_operations.edit_selected_events(owner)
    assert [event[4] for event in owner.events] == ["bulk", "bulk"]


def test_edit_selected_events_updates_modifiers(monkeypatch, owner):
    select_rows(owner, 0, 1)
    owner.pj[cfg.ETHOGRAM]["0"][cfg.MODIFIERS] = {"0": {"type": cfg.SINGLE_SELECTION}}
    class MultiDialog:
        all_subjects = []
        all_behaviors = []
        rbSubject = Check(False)
        rbBehavior = Check(True)
        rbComment = Check(False)
        newText = SimpleNamespace(selectedItems=lambda: [SimpleNamespace(text=lambda: "Run")])
        commentText = SimpleNamespace(text=lambda: "")
        def exec_(self): return True
    class Modifiers:
        def __init__(self, *_): pass
        def exec_(self): return True
        def get_modifiers(self): return {"0": {"type": cfg.SINGLE_SELECTION, "selected": ["north", "east"]}}
    monkeypatch.setattr(event_operations, "EditSelectedEvents", MultiDialog)
    monkeypatch.setattr(event_operations.select_modifiers, "ModifiersList", Modifiers)
    event_operations.edit_selected_events(owner)
    assert [event[3] for event in owner.events] == ["north,east", "north,east"]


@pytest.mark.parametrize("player_type", [cfg.LIVE, cfg.MEDIA, cfg.IMAGES])
def test_edit_event_updates_events_for_each_observation_type(monkeypatch, qapp, player_type):
    window = Owner(qapp, player_type)
    select_rows(window, 0)
    window.config_param["pause_before_addevent"] = player_type == cfg.MEDIA
    captured = []
    monkeypatch.setattr(event_operations, "DlgEditEvent", lambda **_kwargs: FakeEventDialog())
    monkeypatch.setattr(event_operations.write_event, "write_event", lambda _owner, event, value: captured.append((event, value)) or 0)
    monkeypatch.setattr(event_operations.time, "sleep", lambda *_: None)
    event_operations.edit_event(window)
    assert captured[0][0]["row"] == 0
    assert captured[0][0][cfg.COMMENT] == "first"
    if player_type == cfg.MEDIA:
        assert captured[0][0][cfg.FRAME_INDEX] == 42
        assert ("pause",) in window.calls and ("play",) in window.calls
    if player_type == cfg.IMAGES:
        assert captured[0][0][cfg.IMAGE_PATH] == "one.jpg"
        assert captured[0][0][cfg.IMAGE_INDEX] == 2
    window.tv_events.deleteLater()


def test_edit_event_validates_selection_unknown_values_and_cancel(monkeypatch, qapp, messages):
    window = Owner(qapp)
    window.observationId = ""
    event_operations.edit_event(window)
    assert window.no_observation_calls == 1
    window.observationId = "obs"
    event_operations.edit_event(window)
    assert "Select an event" in messages[-1][1][2]

    select_rows(window, 0)
    window.events[0][1] = "Unknown"
    window.events[0][2] = "Missing"
    monkeypatch.setattr(event_operations, "DlgEditEvent", lambda **_kwargs: FakeEventDialog(accepted=False))
    event_operations.edit_event(window)
    assert len(messages) >= 3
    window.tv_events.deleteLater()


def test_remaining_small_operation_paths(monkeypatch, qapp, messages):
    empty = Owner(qapp)
    empty.events.clear()
    empty.refresh_table()
    monkeypatch.setattr(event_operations.QInputDialog, "getText", lambda *_: ("1-2", True))
    event_operations.select_events_between_activated(empty)
    assert "no events" in messages[-1][1][2].lower()

    ordinary = Owner(qapp)
    monkeypatch.setattr(event_operations.QInputDialog, "getText", lambda *_: ("1-bad", True))
    event_operations.select_events_between_activated(ordinary)
    assert "not recognized" in messages[-1][1][2]
    select_rows(ordinary, 0)
    captured_text = []
    monkeypatch.setattr(event_operations.QInputDialog, "getText", lambda *_args, **kwargs: captured_text.append(kwargs["text"]) or ("one", True))
    event_operations.add_comment(ordinary)
    assert captured_text == ["first"]
    select_rows(ordinary, 0, 1)
    ordinary.events[1][4] = "one"
    event_operations.add_comment(ordinary)
    assert captured_text[-1] == "one"

    event_operations.fill_events_undo_list(ordinary, "first")
    event_operations.fill_events_undo_list(ordinary, "second")
    event_operations.undo_event_operation(ordinary)
    assert ordinary.actionUndo.text == "first"
    monkeypatch.setattr(event_operations.cfg, "MAX_UNDO_QUEUE", 0)
    event_operations.fill_events_undo_list(ordinary, "limited")
    assert len(ordinary.undo_queue) == 3
    for item in (empty, ordinary): item.tv_events.deleteLater()
    qapp.processEvents()


def test_copy_paste_media_and_viewer_image_paths(monkeypatch, qapp):
    media = Owner(qapp, cfg.MEDIA, [[Decimal("1"), "A", "Run", "", ""]])
    select_rows(media, 0)
    event_operations.copy_selected_events(media)
    assert qapp.clipboard().text().endswith(cfg.NA)
    qapp.clipboard().setText("1\tA\tRun\t\t\tnot-an-index")
    event_operations.paste_clipboard_to_events(media)
    assert media.events[-1][-1] == "not-an-index"
    event_operations.paste_clipboard_to_events(media)
    assert len(media.events) == 2

    viewer = Owner(qapp, cfg.VIEWER_IMAGES)
    captured = []
    monkeypatch.setattr(event_operations, "DlgEditEvent", lambda **_kwargs: FakeEventDialog(image_idx=2))
    monkeypatch.setattr(event_operations.write_event, "write_event", lambda _owner, event, value: captured.append((event, value)))
    event_operations.add_event(viewer)
    assert captured[0][0][cfg.IMAGE_PATH] == ""
    media.tv_events.deleteLater()
    viewer.tv_events.deleteLater()
    qapp.processEvents()


def test_edit_selected_events_no_focal_and_missing_behavior(monkeypatch, owner):
    select_rows(owner, 0, 1)
    class Subjects:
        all_subjects = []
        all_behaviors = []
        rbSubject = Check(True)
        rbBehavior = Check(False)
        rbComment = Check(False)
        newText = SimpleNamespace(selectedItems=lambda: [SimpleNamespace(text=lambda: cfg.NO_FOCAL_SUBJECT)])
        commentText = SimpleNamespace(text=lambda: "")
        def exec_(self): return True
    monkeypatch.setattr(event_operations, "EditSelectedEvents", Subjects)
    event_operations.edit_selected_events(owner)
    assert [event[1] for event in owner.events] == ["", ""]

    class Missing(Subjects):
        rbSubject = Check(False)
        rbBehavior = Check(True)
        newText = SimpleNamespace(selectedItems=lambda: [SimpleNamespace(text=lambda: "Missing")])
    monkeypatch.setattr(event_operations, "EditSelectedEvents", Missing)
    event_operations.edit_selected_events(owner)


def test_edit_event_na_viewer_and_duplicate_retries(monkeypatch, qapp, messages):
    image = Owner(qapp, cfg.IMAGES)
    select_rows(image, 0)
    image.pj[cfg.OBSERVATIONS]["obs"][cfg.USE_EXIF_DATE] = True
    class NaDialog(FakeEventDialog):
        def __init__(self):
            super().__init__()
            self.cb_set_time_na = Check(True)
    captured = []
    monkeypatch.setattr(event_operations, "DlgEditEvent", lambda **_kwargs: NaDialog())
    monkeypatch.setattr(event_operations.util, "extract_exif_DateTimeOriginal", lambda *_: Decimal("1"))
    monkeypatch.setattr(event_operations.write_event, "write_event", lambda _owner, event, value: captured.append((event, value)) or 0)
    event_operations.edit_event(image)
    assert captured[0][1].is_nan()

    live = Owner(qapp)
    select_rows(live, 0)
    class Retry(FakeEventDialog):
        def __init__(self):
            super().__init__()
            self.calls = 0
        def exec(self):
            self.calls += 1
            return self.calls == 1
    retry = Retry()
    monkeypatch.setattr(event_operations, "DlgEditEvent", lambda **_kwargs: retry)
    monkeypatch.setattr(event_operations.write_event, "write_event", lambda *_: 1)
    event_operations.edit_event(live)
    assert retry.calls == 2
    image.tv_events.deleteLater()
    live.tv_events.deleteLater()
    qapp.processEvents()


def test_remaining_edit_and_time_dialog_branches(monkeypatch, qapp, messages):
    owner = Owner(qapp)
    monkeypatch.setattr(event_operations.QInputDialog, "getText", lambda *_: ("99:99:99.999-00:00:01.000", True))
    event_operations.select_events_between_activated(owner)
    assert "not recognized" in messages[-1][1][2]

    select_rows(owner, 0)
    class CancelTime:
        def __init__(self, *_):
            self.label = Value()
            self.time_widget = SimpleNamespace(get_time=lambda: Decimal("0"))
        def setWindowTitle(self, *_): pass
        def exec_(self): return False
    monkeypatch.setattr(event_operations.dialog, "Ask_time", CancelTime)
    event_operations.edit_time_selected_events(owner)
    class NoTime(CancelTime):
        def exec_(self): return True
    monkeypatch.setattr(event_operations.dialog, "Ask_time", NoTime)
    event_operations.edit_time_selected_events(owner)

    class PositiveTime(CancelTime):
        def __init__(self, *_):
            super().__init__()
            self.time_widget = SimpleNamespace(get_time=lambda: Decimal("1"))
        def exec_(self): return True
    monkeypatch.setattr(event_operations.dialog, "Ask_time", PositiveTime)
    monkeypatch.setattr(event_operations.util, "smart_time_format", lambda *_: "00:00:01.000")
    monkeypatch.setattr(event_operations.dialog, "MessageDialog", lambda *_: cfg.NO)
    event_operations.edit_time_selected_events(owner)

    invalid = Owner(qapp)
    select_rows(invalid, 0)
    class InvalidDialog(FakeEventDialog):
        def __init__(self):
            super().__init__(time_value=Decimal("NaN"))
            self.calls = 0
        def exec(self):
            self.calls += 1
            return self.calls == 1
    invalid_dialog = InvalidDialog()
    monkeypatch.setattr(event_operations, "DlgEditEvent", lambda **_kwargs: invalid_dialog)
    event_operations.edit_event(invalid)
    assert invalid_dialog.calls == 2
    for item in (owner, invalid): item.tv_events.deleteLater()
    qapp.processEvents()


def test_modifier_and_image_retry_variants(monkeypatch, qapp):
    owner = Owner(qapp)
    owner.events[1][3] = "m"
    select_rows(owner, 0, 1)
    owner.pj[cfg.ETHOGRAM]["0"][cfg.MODIFIERS] = {"0": {"type": cfg.NUMERIC_MODIFIER}}
    class Multi:
        all_subjects = []
        all_behaviors = []
        rbSubject = Check(False)
        rbBehavior = Check(True)
        rbComment = Check(False)
        newText = SimpleNamespace(selectedItems=lambda: [SimpleNamespace(text=lambda: "Run")])
        commentText = SimpleNamespace(text=lambda: "")
        def exec_(self): return True
    class Modifier:
        def __init__(self, *_): pass
        def exec_(self): return True
        def get_modifiers(self): return {"0": {"type": cfg.NUMERIC_MODIFIER, "selected": "12"}}
    monkeypatch.setattr(event_operations, "EditSelectedEvents", Multi)
    monkeypatch.setattr(event_operations.select_modifiers, "ModifiersList", Modifier)
    event_operations.edit_selected_events(owner)
    assert [event[3] for event in owner.events] == ["12", "12"]

    image = Owner(qapp, cfg.IMAGES)
    select_rows(image, 0)
    retry = FakeEventDialog()
    retry.calls = 0
    retry.exec = lambda: setattr(retry, "calls", retry.calls + 1) or retry.calls == 1
    monkeypatch.setattr(event_operations, "DlgEditEvent", lambda **_kwargs: retry)
    monkeypatch.setattr(event_operations.write_event, "write_event", lambda *_: 1)
    event_operations.edit_event(image)
    assert retry.calls == 2

    viewer_media = Owner(qapp, cfg.VIEWER_MEDIA)
    viewer_media.pj[cfg.OBSERVATIONS]["obs"][cfg.TYPE] = cfg.MEDIA
    event_operations.add_frame_indexes(viewer_media)
    assert viewer_media.calls == []
    for item in (owner, image, viewer_media): item.tv_events.deleteLater()
    qapp.processEvents()


def test_final_modifier_dialog_and_edit_event_initialization_paths(monkeypatch, qapp):
    owner = Owner(qapp)
    select_rows(owner, 0, 1)
    owner.pj[cfg.ETHOGRAM]["0"][cfg.MODIFIERS] = {
        "0": {"type": cfg.SINGLE_SELECTION},
        "1": {"type": cfg.NUMERIC_MODIFIER},
    }
    class Multi:
        all_subjects = []
        all_behaviors = []
        rbSubject = Check(False)
        rbBehavior = Check(True)
        rbComment = Check(False)
        newText = SimpleNamespace(selectedItems=lambda: [SimpleNamespace(text=lambda: "Run")])
        commentText = SimpleNamespace(text=lambda: "")
        def exec_(self): return True
    class Modifier:
        def __init__(self, *_): pass
        def exec_(self): return True
        def get_modifiers(self):
            return {
                "0": {"type": cfg.SINGLE_SELECTION, "selected": ["north"]},
                "1": {"type": cfg.NUMERIC_MODIFIER, "selected": "4"},
            }
    monkeypatch.setattr(event_operations, "EditSelectedEvents", Multi)
    monkeypatch.setattr(event_operations.select_modifiers, "ModifiersList", Modifier)
    event_operations.edit_selected_events(owner)
    assert [event[3] for event in owner.events] == ["north|4", "north|4"]

    owner.pj[cfg.ETHOGRAM]["0"][cfg.MODIFIERS] = {}
    event_operations.edit_selected_events(owner)
    assert [event[3] for event in owner.events] == ["", ""]

    viewer = Owner(qapp, cfg.VIEWER_LIVE)
    viewer.pj[cfg.OBSERVATIONS]["obs"][cfg.TYPE] = cfg.LIVE
    viewer.events[0][0] = Decimal("NaN")
    viewer.events[0][1] = ""
    select_rows(viewer, 0)
    dialog_instance = FakeEventDialog(accepted=False)
    monkeypatch.setattr(event_operations, "DlgEditEvent", lambda **_kwargs: dialog_instance)
    event_operations.edit_event(viewer)
    assert dialog_instance.cb_set_time_na.isChecked()
    assert dialog_instance.cobSubject.currentText() == cfg.NO_FOCAL_SUBJECT

    for item in (owner, viewer): item.tv_events.deleteLater()
    qapp.processEvents()


def test_edit_time_adds_missing_media_frame_index(monkeypatch, qapp):
    media = Owner(qapp, cfg.MEDIA, [[Decimal("1"), "Alice", "Run", "", "first"]])
    select_rows(media, 0)
    class TimeDialog:
        def __init__(self, *_):
            self.label = Value()
            self.time_widget = SimpleNamespace(get_time=lambda: Decimal("1"))
        def setWindowTitle(self, *_): pass
        def exec_(self): return True
    monkeypatch.setattr(event_operations.dialog, "Ask_time", TimeDialog)
    monkeypatch.setattr(event_operations.dialog, "MessageDialog", lambda *_: cfg.YES)
    monkeypatch.setattr(event_operations.time, "sleep", lambda *_: None)
    event_operations.edit_time_selected_events(media)
    assert media.events[0][-1] == 42
    media.tv_events.deleteLater()
    qapp.processEvents()
