import os
import subprocess
import sys

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from boris import config as cfg
from boris import observation_operations


class FakeTimer:
    def __init__(self):
        self.stop_calls = 0

    def stop(self):
        self.stop_calls += 1


class FakeLayout:
    def __init__(self):
        self.removed_widgets = []

    def removeWidget(self, widget):
        self.removed_widgets.append(widget)


class FakeWidget:
    def __init__(self):
        self.clear_calls = 0
        self.delete_later_calls = 0
        self.visible_values = []
        self.text_values = []

    def clear(self):
        self.clear_calls += 1

    def deleteLater(self):
        self.delete_later_calls += 1

    def setText(self, value):
        self.text_values.append(value)

    def setVisible(self, value):
        self.visible_values.append(value)


class FakeStatusBar:
    def __init__(self):
        self.messages = []

    def showMessage(self, message, timeout):
        self.messages.append((message, timeout))


class FakeSubjectsTable:
    def rowCount(self):
        return 0


class FakeEmbeddedMpvPlayer:
    def __init__(self, events=None, stop_error=None, terminate_error=None):
        self._log_handler = object()
        self.events = events if events is not None else []
        self.stop_calls = 0
        self.stop_error = stop_error
        self.terminate_calls = 0
        self.terminate_error = terminate_error

    def stop(self):
        self.stop_calls += 1
        self.events.append("stop")

        if self.stop_error is not None:
            raise self.stop_error

    def terminate(self):
        self.terminate_calls += 1
        self.events.append("terminate")

        if self.terminate_error is not None:
            raise self.terminate_error


class FakeProcess:
    def __init__(self, wait_error=None):
        self.kill_calls = 0
        self.terminate_calls = 0
        self.wait_calls = []
        self.wait_error = wait_error

    def kill(self):
        self.kill_calls += 1

    def terminate(self):
        self.terminate_calls += 1

    def wait(self, timeout):
        self.wait_calls.append(timeout)

        if self.wait_error is not None:
            raise self.wait_error


class FakeIpcMpvPlayer:
    def __init__(self, process):
        self.process = process
        self.stop_calls = 0
        self.terminate_calls = 0

    def stop(self):
        self.stop_calls += 1

    def terminate(self):
        self.terminate_calls += 1


class FakeDockWidget:
    def __init__(self, player, events=None):
        self.delete_later_calls = 0
        self.events = events if events is not None else []
        self.player = player

    def deleteLater(self):
        self.delete_later_calls += 1
        self.events.append("deleteLater")


class FakeObservationWindow:
    def __init__(self, player_docks, ipc_mode=False, events=None):
        self.MPV_IPC_MODE = ipc_mode
        self.close_observation_tools_calls = 0
        self.currentSubject = "subject"
        self.dwEvents = FakeWidget()
        self.dw_player = player_docks
        self.events = events if events is not None else []
        self.ext_data_timer_list = []
        self.lbFocalSubject = FakeWidget()
        self.lb_current_media_time = FakeWidget()
        self.lb_obs_time_interval = FakeWidget()
        self.lb_player_status = FakeWidget()
        self.lb_video_info = FakeWidget()
        self.lb_zoom_level = FakeWidget()
        self.lbTimeOffset = FakeWidget()
        self.main_window_activation_timer = FakeTimer()
        self.observationId = "observation-1"
        self.playerType = cfg.MEDIA
        self.plot_data = {}
        self.plot_timer = FakeTimer()
        self.removed_docks = []
        self.statusbar = FakeStatusBar()
        self.twSubjects = FakeSubjectsTable()
        self.verticalLayout_3 = FakeLayout()
        self.video_slider = FakeWidget()
        self.w_obs_info = FakeWidget()

        self.pj = {
            cfg.ETHOGRAM: {},
            cfg.OBSERVATIONS: {
                self.observationId: {
                    cfg.FILE: {"1": ["media.mp4"]},
                    cfg.PLOT_DATA: {},
                }
            },
        }

    def close_observation_tools(self):
        self.close_observation_tools_calls += 1

    def removeDockWidget(self, dock_widget):
        self.removed_docks.append(dock_widget)
        self.events.append("removeDockWidget")

    def saveState(self):
        return b"state"


def allow_observation_close(monkeypatch):
    monkeypatch.setattr(observation_operations.menu_options, "update_menu", lambda self: None)
    monkeypatch.setattr(observation_operations.project_functions, "check_state_events_obs", lambda *args, **kwargs: (True, ""))


def test_shutdown_embedded_mpv_stops_clears_callback_and_terminates():
    events = []
    player = FakeEmbeddedMpvPlayer(events=events)

    observation_operations._shutdown_mpv_player(player, player_number=1, ipc_mode=False)

    assert player.stop_calls == 1
    assert player._log_handler is None
    assert player.terminate_calls == 1
    assert events == ["stop", "terminate"]


def test_shutdown_embedded_mpv_continues_when_stop_fails():
    events = []
    player = FakeEmbeddedMpvPlayer(events=events, stop_error=RuntimeError("stop failed"))

    observation_operations._shutdown_mpv_player(player, player_number=1, ipc_mode=False)

    assert player.stop_calls == 1
    assert player._log_handler is None
    assert player.terminate_calls == 1
    assert events == ["stop", "terminate"]


def test_shutdown_ipc_mpv_kills_process_when_wait_times_out():
    process = FakeProcess(wait_error=subprocess.TimeoutExpired(cmd="mpv", timeout=3))
    player = FakeIpcMpvPlayer(process)

    observation_operations._shutdown_mpv_player(player, player_number=1, ipc_mode=True)

    assert player.stop_calls == 1
    assert player.terminate_calls == 0
    assert process.terminate_calls == 1
    assert process.wait_calls == [3]
    assert process.kill_calls == 1


def test_close_observation_shuts_down_embedded_mpv_before_removing_dock(monkeypatch):
    allow_observation_close(monkeypatch)
    events = []
    player = FakeEmbeddedMpvPlayer(events=events)
    player_dock = FakeDockWidget(player, events=events)
    window = FakeObservationWindow([player_dock], events=events)

    observation_operations.close_observation(window)

    assert player.stop_calls == 1
    assert player._log_handler is None
    assert player.terminate_calls == 1
    assert window.removed_docks == [player_dock]
    assert player_dock.delete_later_calls == 1
    assert window.dw_player == []
    assert events == ["stop", "terminate", "removeDockWidget", "deleteLater"]


def test_close_observation_still_removes_dock_when_embedded_terminate_fails(monkeypatch):
    allow_observation_close(monkeypatch)
    player = FakeEmbeddedMpvPlayer(terminate_error=RuntimeError("terminate failed"))
    player_dock = FakeDockWidget(player)
    window = FakeObservationWindow([player_dock])

    observation_operations.close_observation(window)

    assert player.stop_calls == 1
    assert player.terminate_calls == 1
    assert window.removed_docks == [player_dock]
    assert player_dock.delete_later_calls == 1
    assert window.dw_player == []
