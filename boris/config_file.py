"""
BORIS
Behavioral Observation Research Interactive Software
Copyright 2012-2026 Olivier Friard

This file is part of BORIS.

  BORIS is free software; you can redistribute it and/or modify
  it under the terms of the GNU General Public License as published by
  the Free Software Foundation; either version 3 of the License, or
  any later version.

  BORIS is distributed in the hope that it will be useful,
  but WITHOUT ANY WARRANTY; without even the implied warranty of
  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
  GNU General Public License for more details.

  You should have received a copy of the GNU General Public License
  along with this program; if not see <http://www.gnu.org/licenses/>.

Read and write the BORIS config file
"""

import logging
import pathlib as pl
import time

from PySide6.QtCore import QByteArray, QSettings

from . import config as cfg
from . import dialog

logger = logging.getLogger(__name__)


def read(self) -> None:
    """
    read config file
    """

    ini_file_path = pl.Path.home() / pl.Path(".boris")

    logger.debug(f"read config file: {ini_file_path}")

    if ini_file_path.is_file():
        settings = QSettings(str(ini_file_path), QSettings.Format.IniFormat)

        try:
            self.config_param = settings.value("config")
        except Exception:  # noqa: BLE001
            self.config_param = {}

        if self.config_param == {}:
            self.config_param = cfg.INIT_PARAM

            # for back compatibility
            # display subtitles
            try:
                self.config_param[cfg.DISPLAY_SUBTITLES] = settings.value(cfg.DISPLAY_SUBTITLES) == "true"
            except Exception:  # noqa: BLE001
                self.config_param[cfg.DISPLAY_SUBTITLES] = False

            logger.debug(f"{cfg.DISPLAY_SUBTITLES}: {self.config_param[cfg.DISPLAY_SUBTITLES]}")

        try:
            logger.debug("restore geometry")

            self.restoreGeometry(settings.value("geometry"))
        except Exception:  # noqa: BLE001
            logger.warning("Error restoring geometry")

        self.saved_state = settings.value("dockwidget_positions")
        if not isinstance(self.saved_state, QByteArray):
            self.saved_state = None

        # time format
        if self.config_param.get("time_format", None) is None:
            time_format = cfg.HHMMSS  # default
            try:
                time_format = settings.value("Time/Format")
            except Exception:  # noqa: BLE001
                time_format = cfg.HHMMSS
            self.config_param["time_format"] = time_format

        logger.debug(f"time format: {self.config_param['time_format']}")

        # fast forward value
        if self.config_param.get("fast_forward_speed", None) is None:
            fast = cfg.FAST_FORWARD_DEFAULT_VALUE
            try:
                fast = float(settings.value("Time/fast_forward_speed"))
            except Exception:  # noqa: BLE001
                fast = cfg.FAST_FORWARD_DEFAULT_VALUE
            self.config_param["fast_forward_speed"] = fast

        logger.debug(f"fast_forward_speed: {self.config_param['fast_forward_speed']}")

        # repositioning_time_offset
        if self.config_param.get("repositioning_time_offset", None) is None:
            repositioningTimeOffset = 0
            try:
                repositioningTimeOffset = int(settings.value("Time/Repositioning_time_offset"))
            except Exception:  # noqa: BLE001
                repositioningTimeOffset = 0
            self.config_param["repositioning_time_offset"] = repositioningTimeOffset

        logger.debug(f"repositioning_time_offset: {self.config_param['repositioning_time_offset']}")

        # play_rate_step
        if self.config_param.get("play_rate_step", None) is None:
            play_rate_step = 0.1
            try:
                play_rate_step = float(settings.value("Time/play_rate_step"))
            except Exception:  # noqa: BLE001
                play_rate_step = 0.1
            self.config_param["play_rate_step"] = play_rate_step

        logger.debug(f"play_rate_step: {self.config_param['play_rate_step']}")

        self.automaticBackup = 0
        try:
            self.automaticBackup = int(settings.value("Automatic_backup"))
        except Exception:  # noqa: BLE001
            self.automaticBackup = 0

        # activate or desactivate autosave timer
        if self.automaticBackup:
            self.automaticBackupTimer.start(self.automaticBackup * 60000)
        else:
            self.automaticBackupTimer.stop()

        logger.debug(f"Autosave: {self.automaticBackup}")

        self.behav_seq_separator = "|"
        try:
            self.behav_seq_separator = settings.value("behavioural_strings_separator")
            if not self.behav_seq_separator:
                self.behav_seq_separator = "|"
        except Exception:  # noqa: BLE001
            self.behav_seq_separator = "|"

        logger.debug(f"behavioural_strings_separator: {self.behav_seq_separator}")

        # close_the_same_current_event
        if self.config_param.get("close_the_same_current_event", None) is None:
            close_the_same_current_event = False
            try:
                close_the_same_current_event = settings.value("close_the_same_current_event") == "true"
            except Exception:  # noqa: BLE001
                close_the_same_current_event = False
            self.config_param["close_the_same_current_event"] = close_the_same_current_event

        logger.debug(f"close_the_same_current_event: {self.config_param['close_the_same_current_event']}")

        if self.config_param.get("confirm_sound", None) is None:
            confirm_sound = False
            try:
                confirm_sound = settings.value("confirm_sound") == "true"
            except Exception:  # noqa: BLE001
                confirm_sound = False
            self.config_param["confirm_sound"] = confirm_sound

        logger.debug(f"confirm_sound: {self.config_param['confirm_sound']}")

        self.alertNoFocalSubject = False
        try:
            self.alertNoFocalSubject = settings.value("alert_nosubject") == "true"
        except Exception:  # noqa: BLE001
            self.alertNoFocalSubject = False
        logger.debug(f"alert_nosubject: {self.alertNoFocalSubject}")

        try:
            self.beep_every = int(settings.value("beep_every"))
        except Exception:  # noqa: BLE001
            self.beep_every = 0
        logger.debug(f"beep_every: {self.beep_every}")

        self.trackingCursorAboveEvent = False
        try:
            self.trackingCursorAboveEvent = settings.value("tracking_cursor_above_event") == "true"
        except Exception:  # noqa: BLE001
            self.trackingCursorAboveEvent = False
        logger.debug(f"tracking_cursor_above_event: {self.trackingCursorAboveEvent}")

        # check for new version
        self.checkForNewVersion = False

        if not self.no_first_launch_dialog:
            try:
                if settings.value("check_for_new_version") is None:
                    self.checkForNewVersion = (
                        dialog.MessageDialog(
                            cfg.programName,
                            (
                                "Allow BORIS to automatically check for new version and news?\n"
                                "(An internet connection is required)\n"
                                "You can change this option in the Preferences (File > Preferences)"
                            ),
                            (cfg.YES, cfg.NO),
                        )
                        == cfg.YES
                    )
                else:
                    self.checkForNewVersion = settings.value("check_for_new_version") == "true"
            except Exception:  # noqa: BLE001
                self.checkForNewVersion = False
        logger.debug(f"Automatic check for new version: {self.checkForNewVersion}")

        # pause before add event
        self.pause_before_addevent = False
        try:
            self.pause_before_addevent = settings.value("pause_before_addevent") == "true"
        except Exception:  # noqa: BLE001
            self.pause_before_addevent = False

        logger.debug(f"pause_before_addevent: {self.pause_before_addevent}")

        if (
            self.checkForNewVersion
            and settings.value("last_check_for_new_version")
            and (int(time.mktime(time.localtime())) - int(settings.value("last_check_for_new_version")) > cfg.CHECK_NEW_VERSION_DELAY)
        ):
            self.actionCheckUpdate_activated(flagMsgOnlyIfNew=True)

        logger.debug(f"last check for new version: {settings.value('last_check_for_new_version')}")

        self.ffmpeg_cache_dir = ""
        try:
            self.ffmpeg_cache_dir = settings.value("ffmpeg_cache_dir")
            if not self.ffmpeg_cache_dir:
                self.ffmpeg_cache_dir = ""
        except Exception:  # noqa: BLE001
            self.ffmpeg_cache_dir = ""
        logger.debug(f"ffmpeg_cache_dir: {self.ffmpeg_cache_dir}")

        try:
            self.spectrogram_color_map = settings.value("spectrogram_color_map")
            if self.spectrogram_color_map is None:
                self.spectrogram_color_map = cfg.SPECTROGRAM_DEFAULT_COLOR_MAP
        except Exception:  # noqa: BLE001
            self.spectrogram_color_map = cfg.SPECTROGRAM_DEFAULT_COLOR_MAP

        try:
            self.spectrogram_time_interval = int(settings.value("spectrogram_time_interval"))
            if not self.spectrogram_time_interval:
                self.spectrogram_time_interval = cfg.SPECTROGRAM_DEFAULT_TIME_INTERVAL
        except Exception:  # noqa: BLE001
            self.spectrogram_time_interval = cfg.SPECTROGRAM_DEFAULT_TIME_INTERVAL

        # plot colors
        try:
            self.plot_colors = settings.value("plot_colors").split("|")
        except Exception:  # noqa: BLE001
            self.plot_colors = cfg.BEHAVIORS_PLOT_COLORS

        if ("white" in self.plot_colors or "azure" in self.plot_colors or "snow" in self.plot_colors) and (
            dialog.MessageDialog(
                cfg.programName,
                ("The colors list contain colors that are very light.\nDo you want to reload the default colors list?"),
                (cfg.NO, cfg.YES),
            )
            == cfg.YES
        ):
            self.plot_colors = cfg.BEHAVIORS_PLOT_COLORS

        # behavioral categories colors
        try:
            self.behav_category_colors = settings.value("behav_category_colors").split("|")
        except Exception:  # noqa: BLE001
            self.behav_category_colors = cfg.CATEGORY_COLORS_LIST

        if ("white" in self.behav_category_colors or "azure" in self.behav_category_colors or "snow" in self.behav_category_colors) and (
            dialog.MessageDialog(
                cfg.programName,
                ("The colors list contain colors that are very light.\nDo you want to reload the default colors list?"),
                (cfg.NO, cfg.YES),
            )
            == cfg.YES
        ):
            self.behav_category_colors = cfg.CATEGORY_COLORS_LIST

    else:  # no .boris file found
        logger.info("No config file found")
        # ask user for checking for new version
        if not self.no_first_launch_dialog:
            self.checkForNewVersion = (
                dialog.MessageDialog(
                    cfg.programName,
                    (
                        "Allow BORIS to automatically check for new version?\n"
                        "(An internet connection is required)\n"
                        "You can change this option in the"
                        " Preferences (File > Preferences)"
                    ),
                    (cfg.NO, cfg.YES),
                )
                == cfg.YES
            )
        else:
            self.checkForNewVersion = False

        self.config_param = cfg.INIT_PARAM

    # recent projects
    logger.debug("read recent projects")
    self.recent_projects = []
    recent_projects_file_path = pl.Path.home() / ".boris_recent_projects"
    if recent_projects_file_path.is_file():
        settings = QSettings(str(recent_projects_file_path), QSettings.Format.IniFormat)
        try:
            self.recent_projects = settings.value("recent_projects").split("|||")
            while "" in self.recent_projects:
                self.recent_projects.remove("")
            self.set_recent_projects_menu()
        except Exception:  # noqa: BLE001
            logger.warning("recent projects file not created")


def save(self, lastCheckForNewVersion=0):
    """
    save config file in $HOME/.boris
    """

    file_path = pl.Path.home() / pl.Path(".boris")

    logger.debug(f"save config file: {file_path}")

    settings = QSettings(str(file_path), QSettings.Format.IniFormat)

    settings.setValue("config", self.config_param)

    settings.setValue("geometry", self.saveGeometry())

    if self.saved_state:
        settings.setValue("dockwidget_positions", self.saved_state)

    settings.setValue("Time/Format", self.config_param["time_format"])
    settings.setValue("Time/Repositioning_time_offset", self.config_param["repositioning_time_offset"])
    settings.setValue("Time/fast_forward_speed", self.config_param["fast_forward_speed"])
    settings.setValue("Time/play_rate_step", self.config_param["play_rate_step"])
    settings.setValue("Automatic_backup", self.automaticBackup)
    settings.setValue("behavioural_strings_separator", self.behav_seq_separator)
    settings.setValue("close_the_same_current_event", self.config_param["close_the_same_current_event"])
    settings.setValue("confirm_sound", self.config_param["confirm_sound"])
    settings.setValue("beep_every", self.beep_every)
    settings.setValue("alert_nosubject", self.alertNoFocalSubject)
    settings.setValue("tracking_cursor_above_event", self.trackingCursorAboveEvent)
    settings.setValue("check_for_new_version", self.checkForNewVersion)
    # settings.setValue(DISPLAY_SUBTITLES, self.config_param[DISPLAY_SUBTITLES])
    settings.setValue("pause_before_addevent", self.pause_before_addevent)

    if lastCheckForNewVersion:
        settings.setValue("last_check_for_new_version", lastCheckForNewVersion)

    # FFmpeg
    settings.setValue("ffmpeg_cache_dir", self.ffmpeg_cache_dir)
    # spectrogram
    settings.setValue("spectrogram_color_map", self.spectrogram_color_map)
    settings.setValue("spectrogram_time_interval", self.spectrogram_time_interval)
    # plot colors
    settings.setValue("plot_colors", "|".join(self.plot_colors))
    # behavioral categories colors
    settings.setValue("behav_category_colors", "|".join(self.behav_category_colors))

    # recent projects
    logger.debug("Save recent projects")

    settings = QSettings(str(pl.Path.home() / ".boris_recent_projects"), QSettings.Format.IniFormat)
    settings.setValue("recent_projects", "|||".join(self.recent_projects))
