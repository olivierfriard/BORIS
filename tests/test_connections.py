from types import SimpleNamespace

import pytest

from boris import config as cfg
from boris import connections


class Signal:
    def __init__(self):
        self.callbacks = []

    def connect(self, callback):
        self.callbacks.append(callback)

    def emit(self, *args):
        for callback in self.callbacks:
            callback(*args)


class Action:
    def __init__(self, *_):
        self.triggered = Signal()
        self.enabled = None
        self.visible = None
        self.separator = False

    def setEnabled(self, enabled):
        self.enabled = enabled

    def setVisible(self, visible):
        self.visible = visible

    def setSeparator(self, separator):
        self.separator = separator


class Header:
    def __init__(self):
        self.sortIndicatorChanged = Signal()
        self.context_policy = None
        self.actions = []

    def setContextMenuPolicy(self, policy):
        self.context_policy = policy

    def addAction(self, action):
        self.actions.append(action)


class Widget:
    def __init__(self):
        self.itemDoubleClicked = Signal()
        self.doubleClicked = Signal()
        self.clicked = Signal()
        self.context_policy = None
        self.actions = []
        self._header = Header()

    def setContextMenuPolicy(self, policy):
        self.context_policy = policy

    def horizontalHeader(self):
        return self._header

    def addAction(self, action):
        self.actions.append(action)


class Timer:
    def __init__(self, *_):
        self.timeout = Signal()
        self.interval = None
        self.starts = []

    def setInterval(self, interval):
        self.interval = interval

    def start(self, interval=None):
        self.starts.append(interval)


class Recorder:
    def __init__(self, name, calls):
        self.name = name
        self.calls = calls

    def __call__(self, *args, **kwargs):
        self.calls.append((self.name, args, kwargs))


class Window:
    def __init__(self, automatic_backup):
        self.calls = []
        self.config_param = {"automatic_backup": automatic_backup}
        self.automaticBackupTimer = Timer()
        self._actions = {}
        self._widgets = {}

    def __getattr__(self, name):
        if name.startswith("action") and not name.endswith("_activated"):
            return self._actions.setdefault(name, Action())
        if name.startswith("menu"):
            return self._actions.setdefault(name, Action())
        if name.endswith(("_doubleClicked", "_sorted")):
            return Recorder(name, self.calls)
        if name.startswith(("tw", "tv", "pb_")):
            return self._widgets.setdefault(name, Widget())
        return Recorder(name, self.calls)


@pytest.fixture
def connected_window(monkeypatch):
    monkeypatch.setattr(connections, "QAction", Action)
    monkeypatch.setattr(connections, "QTimer", Timer)
    window = Window(automatic_backup=4)
    connections.connections(window)
    return window


def test_connections_configure_actions_context_menus_and_timers(connected_window):
    window = connected_window

    assert window.actionUndo.enabled is False
    assert window.actionBehavior_bar_plot.visible is True
    assert window.actionPlot_events1.visible is False
    assert window.twEthogram.context_policy == connections.Qt.ContextMenuPolicy.ActionsContextMenu
    assert window.tv_events.context_policy == connections.Qt.ContextMenuPolicy.ActionsContextMenu
    assert window.twEthogram.horizontalHeader().sortIndicatorChanged.callbacks
    assert window.tv_events.horizontalHeader().actions == [window.actionConfigure_tvevents_columns]
    assert window.actionAdd_event in window.tv_events.actions
    assert window.actionDelete_selected_events in window.tv_events.actions
    assert sum(action.separator for action in window.tv_events.actions) == 4
    assert window.plot_timer.interval == cfg.SPECTRO_TIMER
    assert window.plot_timer.timeout.callbacks
    assert window.live_timer.timeout.callbacks
    assert window.automaticBackupTimer.starts == [240000]
    assert window.pb_live_obs.clicked.callbacks


def test_connections_do_not_start_automatic_backup_when_disabled(monkeypatch):
    monkeypatch.setattr(connections, "QAction", Action)
    monkeypatch.setattr(connections, "QTimer", Timer)
    window = Window(automatic_backup=0)

    connections.connections(window)

    assert window.automaticBackupTimer.starts == []


def test_connected_actions_invoke_local_and_module_callbacks(monkeypatch, connected_window):
    window = connected_window
    delegated = []
    monkeypatch.setattr(connections.preferences, "preferences", lambda owner: delegated.append(("preferences", owner)))
    monkeypatch.setattr(
        connections.observation_operations,
        "new_observation",
        lambda owner, mode, obsId: delegated.append(("new observation", owner, mode, obsId)),
    )
    monkeypatch.setattr(connections.event_operations, "add_event", lambda owner: delegated.append(("add event", owner)))
    monkeypatch.setattr(
        connections.time_budget_widget,
        "time_budget",
        lambda owner, **kwargs: delegated.append(("time budget", owner, kwargs)),
    )

    window.actionNew_project.triggered.emit()
    window.actionPreferences.triggered.emit()
    window.actionNew_observation.triggered.emit()
    window.actionAdd_event.triggered.emit()
    window.actionTime_budget.triggered.emit()
    window.pb_live_obs.clicked.emit()
    window.plot_timer.timeout.emit()
    window.twEthogram.itemDoubleClicked.emit()

    assert ("edit_project", (cfg.NEW,), {}) in window.calls
    assert ("preferences", window) in delegated
    assert ("new observation", window, cfg.NEW, "") in delegated
    assert ("add event", window) in delegated
    assert ("time budget", window, {"mode": "by_behavior"}) in delegated
    assert ("start_live_observation", (), {}) in window.calls
    assert ("plot_timer_out", (), {}) in window.calls
    assert ("twEthogram_doubleClicked", (), {}) in window.calls
