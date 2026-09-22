import copy
from types import SimpleNamespace

import pytest
from PySide6.QtCore import QByteArray, QSettings

from boris import config as cfg
from boris import config_file


class RecordingTimer:
    def __init__(self):
        self.calls = []

    def start(self, interval):
        self.calls.append(("start", interval))

    def stop(self):
        self.calls.append(("stop",))


class Window:
    def __init__(self, config_param=None, no_first_launch_dialog=True):
        self.config_param = config_param or {}
        self.no_first_launch_dialog = no_first_launch_dialog
        self.automaticBackup = 3
        self.automaticBackupTimer = RecordingTimer()
        self.saved_state = None
        self.restored_geometry = []
        self.recent_menu_updates = 0
        self.update_checks = []

    def restoreGeometry(self, geometry):
        self.restored_geometry.append(geometry)
        return True

    def saveGeometry(self):
        return QByteArray(b"window geometry")

    def set_recent_projects_menu(self):
        self.recent_menu_updates += 1

    def actionCheckUpdate_activated(self, **kwargs):
        self.update_checks.append(kwargs)


@pytest.fixture
def config_home(monkeypatch, tmp_path):
    monkeypatch.setattr(config_file.pl.Path, "home", lambda: tmp_path)
    monkeypatch.setattr(cfg, "INIT_PARAM", copy.deepcopy(cfg.INIT_PARAM))
    return tmp_path


def settings(path):
    return QSettings(str(path), QSettings.Format.IniFormat)


def full_config():
    values = copy.deepcopy(cfg.INIT_PARAM)
    values.update(
        {
            "time_format": cfg.S,
            "fast_forward_speed": 2.5,
            "repositioning_time_offset": 7,
            "play_rate_step": 0.2,
            "automatic_backup": 1,
            "behav_seq_separator": ";",
            "close_the_same_current_event": True,
            "confirm_sound": True,
            "alert_if_no_focal_subject": True,
            "beep_every": 9,
            "tracking_cursor_above_event": True,
            "pause_before_addevent": True,
            "spectrogram_color_map": "plasma",
            "spectrogram_time_interval": 15,
            "plot_colors": ["black", "red"],
            "behav_category_colors": ["green", "blue"],
        }
    )
    return values


def test_save_writes_config_and_recent_projects(config_home):
    window = Window(config_param=full_config())
    window.saved_state = QByteArray(b"dock positions")
    window.checkForNewVersion = True
    window.ffmpeg_cache_dir = "/tmp/ffmpeg-cache"
    window.recent_projects = ["one.boris", "two.boris"]

    config_file.save(window, lastCheckForNewVersion=12345)

    config_settings = settings(config_home / ".boris")
    recent_settings = settings(config_home / ".boris_recent_projects")
    assert config_settings.value("config") == window.config_param
    assert config_settings.value("geometry") == QByteArray(b"window geometry")
    assert config_settings.value("dockwidget_positions") == QByteArray(b"dock positions")
    assert config_settings.value("last_check_for_new_version") == 12345
    assert config_settings.value("ffmpeg_cache_dir") == "/tmp/ffmpeg-cache"
    assert config_settings.value("plot_colors") == "black|red"
    assert recent_settings.value("recent_projects") == "one.boris|||two.boris"


def test_read_restores_saved_values_timer_update_check_and_recent_projects(config_home):
    config_settings = settings(config_home / ".boris")
    config_settings.setValue("config", full_config())
    config_settings.setValue("geometry", QByteArray(b"stored geometry"))
    config_settings.setValue("dockwidget_positions", QByteArray(b"stored docks"))
    config_settings.setValue("check_for_new_version", "true")
    config_settings.setValue("last_check_for_new_version", "0")
    config_settings.setValue("ffmpeg_cache_dir", "/tmp/cache")
    config_settings.sync()
    recent_settings = settings(config_home / ".boris_recent_projects")
    recent_settings.setValue("recent_projects", "one.boris|||two.boris|||")
    recent_settings.sync()
    window = Window(no_first_launch_dialog=False)

    config_file.read(window)

    assert window.config_param == full_config()
    assert window.restored_geometry == [QByteArray(b"stored geometry")]
    assert window.saved_state == QByteArray(b"stored docks")
    assert window.automaticBackupTimer.calls == [("start", 180000)]
    assert window.ffmpeg_cache_dir == "/tmp/cache"
    assert window.checkForNewVersion is True
    assert window.update_checks == [{"flagMsgOnlyIfNew": True}]
    assert window.recent_projects == ["one.boris", "two.boris"]
    assert window.recent_menu_updates == 1


def test_read_migrates_legacy_settings_and_resets_light_colors(monkeypatch, config_home):
    config_settings = settings(config_home / ".boris")
    config_settings.setValue("config", {"legacy_config": True})
    config_settings.setValue("Time/Format", cfg.HHMMSS)
    config_settings.setValue("Time/fast_forward_speed", "1.5")
    config_settings.setValue("Time/Repositioning_time_offset", "4")
    config_settings.setValue("Time/play_rate_step", "0.5")
    config_settings.setValue("Automatic_backup", "0")
    config_settings.setValue("behavioural_strings_separator", "")
    config_settings.setValue("close_the_same_current_event", "true")
    config_settings.setValue("confirm_sound", "true")
    config_settings.setValue("alert_nosubject", "true")
    config_settings.setValue("beep_every", "6")
    config_settings.setValue("tracking_cursor_above_event", "true")
    config_settings.setValue("pause_before_addevent", "true")
    config_settings.setValue("spectrogram_color_map", "magma")
    config_settings.setValue("spectrogram_time_interval", "12")
    config_settings.setValue("plot_colors", "white|black")
    config_settings.setValue("behav_category_colors", "azure|blue")
    config_settings.sync()
    window = Window()
    messages = []
    monkeypatch.setattr(config_file.dialog, "MessageDialog", lambda *args: messages.append(args) or cfg.YES)

    config_file.read(window)

    assert window.config_param["fast_forward_speed"] == 1.5
    assert window.config_param["repositioning_time_offset"] == 4
    assert window.config_param["play_rate_step"] == 0.5
    assert window.config_param["automatic_backup"] == 0
    assert window.automaticBackupTimer.calls == [("stop",)]
    assert window.config_param["behav_seq_separator"] == "|"
    assert window.config_param["close_the_same_current_event"] is True
    assert window.config_param["confirm_sound"] is True
    assert window.config_param["alert_if_no_focal_subject"] is True
    assert window.config_param["beep_every"] == 6
    assert window.config_param["spectrogram_color_map"] == "magma"
    assert window.config_param["spectrogram_time_interval"] == 12
    assert window.config_param["plot_colors"] == cfg.BEHAVIORS_PLOT_COLORS
    assert window.config_param["behav_category_colors"] == cfg.CATEGORY_COLORS_LIST
    assert window.ffmpeg_cache_dir == ""
    assert len(messages) == 2


@pytest.mark.parametrize("reply, expected", [(cfg.YES, True), (cfg.NO, False)])
def test_read_without_a_config_file_asks_about_update_checks(monkeypatch, config_home, reply, expected):
    window = Window(no_first_launch_dialog=False)
    monkeypatch.setattr(config_file.dialog, "MessageDialog", lambda *_: reply)

    config_file.read(window)

    assert window.checkForNewVersion is expected
    assert window.config_param == cfg.INIT_PARAM
    assert window.recent_projects == []
