"""
BORIS
Behavioral Observation Research Interactive Software
Copyright 2012-2024 Olivier Friard

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

import pathlib as pl
import logging
import time

from . import config as cfg
from . import dialog

from PyQt5.QtCore import QByteArray, QSettings


def read(self):
    """
    read config file
    """

    iniFilePath = pl.Path.home() / pl.Path(".boris")

    logging.debug(f"read config file: {iniFilePath}")

    if iniFilePath.is_file():
        settings = QSettings(str(iniFilePath), QSettings.IniFormat)

        try:
            self.config_param = settings.value("config")
        except Exception:
            self.config_param = None

        if self.config_param is None:
            self.config_param = cfg.INIT_PARAM

            # for back compatibility
            # display subtitles
            try:
                self.config_param[cfg.DISPLAY_SUBTITLES] = settings.value(cfg.DISPLAY_SUBTITLES) == "true"
            except Exception:
                self.config_param[cfg.DISPLAY_SUBTITLES] = False

            logging.debug(f"{cfg.DISPLAY_SUBTITLES}: {self.config_param[cfg.DISPLAY_SUBTITLES]}")

        try:
            logging.debug("restore geometry")

            self.restoreGeometry(settings.value("geometry"))
        except Exception:
            logging.warning("Error restoring geometry")
            pass

        self.saved_state = settings.value("dockwidget_positions")
        if not isinstance(self.saved_state, QByteArray):
            self.saved_state = None

        logging.debug(f"saved state: {self.saved_state}")

        self.timeFormat = cfg.HHMMSS
        try:
            self.timeFormat = settings.value("Time/Format")
        except Exception:
            self.timeFormat = cfg.HHMMSS

        logging.debug(f"time format: {self.timeFormat}")

        self.fast = 10
        try:
            self.fast = int(settings.value("Time/fast_forward_speed"))
        except Exception:
            self.fast = 10

        logging.debug(f"Time/fast_forward_speed: {self.fast}")

        self.repositioningTimeOffset = 0
        try:
            self.repositioningTimeOffset = int(settings.value("Time/Repositioning_time_offset"))
        except Exception:
            self.repositioningTimeOffset = 0

        logging.debug(f"Time/Repositioning_time_offset: {self.repositioningTimeOffset}")

        self.play_rate_step = 0.1
        try:
            self.play_rate_step = float(settings.value("Time/play_rate_step"))
        except Exception:
            self.play_rate_step = 0.1

        logging.debug(f"Time/play_rate_step: {self.play_rate_step}")

        self.automaticBackup = 0
        try:
            self.automaticBackup = int(settings.value("Automatic_backup"))
        except Exception:
            self.automaticBackup = 0

        # activate or desactivate autosave timer
        if self.automaticBackup:
            self.automaticBackupTimer.start(self.automaticBackup * 60000)
        else:
            self.automaticBackupTimer.stop()

        logging.debug(f"Autosave: {self.automaticBackup}")

        self.behav_seq_separator = "|"
        try:
            self.behav_seq_separator = settings.value("behavioural_strings_separator")
            if not self.behav_seq_separator:
                self.behav_seq_separator = "|"
        except Exception:
            self.behav_seq_separator = "|"

        logging.debug(f"behavioural_strings_separator: {self.behav_seq_separator}")

        self.close_the_same_current_event = False
        try:
            self.close_the_same_current_event = settings.value("close_the_same_current_event") == "true"
        except Exception:
            self.close_the_same_current_event = False

        logging.debug(f"close_the_same_current_event: {self.close_the_same_current_event}")

        self.confirmSound = False
        try:
            self.confirmSound = settings.value("confirm_sound") == "true"
        except Exception:
            self.confirmSound = False

        logging.debug(f"confirm_sound: {self.confirmSound}")

        self.alertNoFocalSubject = False
        try:
            self.alertNoFocalSubject = settings.value("alert_nosubject") == "true"
        except Exception:
            self.alertNoFocalSubject = False
        logging.debug(f"alert_nosubject: {self.alertNoFocalSubject}")

        try:
            self.beep_every = int(settings.value("beep_every"))
        except Exception:
            self.beep_every = 0
        logging.debug(f"beep_every: {self.beep_every}")

        self.trackingCursorAboveEvent = False
        try:
            self.trackingCursorAboveEvent = settings.value("tracking_cursor_above_event") == "true"
        except Exception:
            self.trackingCursorAboveEvent = False
        logging.debug(f"tracking_cursor_above_event: {self.trackingCursorAboveEvent}")

        # check for new version
        self.checkForNewVersion = False

        # print(f"{self.no_first_launch_dialog=}")

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
                            [cfg.YES, cfg.NO],
                        )
                        == cfg.YES
                    )
                else:
                    self.checkForNewVersion = settings.value("check_for_new_version") == "true"
            except Exception:
                self.checkForNewVersion = False
        logging.debug(f"Automatic check for new version: {self.checkForNewVersion}")

        # pause before add event
        self.pause_before_addevent = False
        try:
            self.pause_before_addevent = settings.value("pause_before_addevent") == "true"
        except Exception:
            self.pause_before_addevent = False

        logging.debug(f"pause_before_addevent: {self.pause_before_addevent}")

        if self.checkForNewVersion:
            if settings.value("last_check_for_new_version") and (
                int(time.mktime(time.localtime())) - int(settings.value("last_check_for_new_version")) > cfg.CHECK_NEW_VERSION_DELAY
            ):
                self.actionCheckUpdate_activated(flagMsgOnlyIfNew=True)

        logging.debug(f"last check for new version: {settings.value('last_check_for_new_version')}")

        self.ffmpeg_cache_dir = ""
        try:
            self.ffmpeg_cache_dir = settings.value("ffmpeg_cache_dir")
            if not self.ffmpeg_cache_dir:
                self.ffmpeg_cache_dir = ""
        except Exception:
            self.ffmpeg_cache_dir = ""
        logging.debug(f"ffmpeg_cache_dir: {self.ffmpeg_cache_dir}")

        # spectrogram
        self.spectrogramHeight = 80

        try:
            self.spectrogram_color_map = settings.value("spectrogram_color_map")
            if self.spectrogram_color_map is None:
                self.spectrogram_color_map = cfg.SPECTROGRAM_DEFAULT_COLOR_MAP
        except Exception:
            self.spectrogram_color_map = cfg.SPECTROGRAM_DEFAULT_COLOR_MAP

        try:
            self.spectrogram_time_interval = int(settings.value("spectrogram_time_interval"))
            if not self.spectrogram_time_interval:
                self.spectrogram_time_interval = cfg.SPECTROGRAM_DEFAULT_TIME_INTERVAL
        except Exception:
            self.spectrogram_time_interval = cfg.SPECTROGRAM_DEFAULT_TIME_INTERVAL

        # plot colors
        try:
            self.plot_colors = settings.value("plot_colors").split("|")
        except Exception:
            self.plot_colors = cfg.BEHAVIORS_PLOT_COLORS

        if "white" in self.plot_colors or "azure" in self.plot_colors or "snow" in self.plot_colors:
            if (
                dialog.MessageDialog(
                    cfg.programName,
                    ("The colors list contain colors that are very light.\n" "Do you want to reload the default colors list?"),
                    [cfg.NO, cfg.YES],
                )
                == cfg.YES
            ):
                self.plot_colors = cfg.BEHAVIORS_PLOT_COLORS

        # behavioral categories colors
        try:
            self.behav_category_colors = settings.value("behav_category_colors").split("|")
        except Exception:
            self.behav_category_colors = cfg.CATEGORY_COLORS_LIST

        if "white" in self.behav_category_colors or "azure" in self.behav_category_colors or "snow" in self.behav_category_colors:
            if (
                dialog.MessageDialog(
                    cfg.programName,
                    ("The colors list contain colors that are very light.\n" "Do you want to reload the default colors list?"),
                    [cfg.NO, cfg.YES],
                )
                == cfg.YES
            ):
                self.behav_category_colors = cfg.CATEGORY_COLORS_LIST

    else:  # no .boris file found
        logging.info("No config file found")
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
                    [cfg.NO, cfg.YES],
                )
                == cfg.YES
            )
        else:
            self.checkForNewVersion = False

    # recent projects
    logging.debug("read recent projects")
    recent_projects_file_path = pl.Path.home() / ".boris_recent_projects"
    if recent_projects_file_path.is_file():
        settings = QSettings(str(recent_projects_file_path), QSettings.IniFormat)
        try:
            self.recent_projects = settings.value("recent_projects").split("|||")
            while "" in self.recent_projects:
                self.recent_projects.remove("")
            self.set_recent_projects_menu()
        except Exception:
            self.recent_projects = []
    else:
        self.recent_projects = []


def save(self, lastCheckForNewVersion=0):
    """
    save config file in $HOME/.boris
    """

    file_path = pl.Path.home() / pl.Path(".boris")

    logging.debug(f"save config file: {file_path}")

    settings = QSettings(str(file_path), QSettings.IniFormat)

    settings.setValue("config", self.config_param)

    settings.setValue("geometry", self.saveGeometry())

    if self.saved_state:
        settings.setValue("dockwidget_positions", self.saved_state)

    settings.setValue("Time/Format", self.timeFormat)
    settings.setValue("Time/Repositioning_time_offset", self.repositioningTimeOffset)
    settings.setValue("Time/fast_forward_speed", self.fast)
    settings.setValue("Time/play_rate_step", self.play_rate_step)
    settings.setValue("Automatic_backup", self.automaticBackup)
    settings.setValue("behavioural_strings_separator", self.behav_seq_separator)
    settings.setValue("close_the_same_current_event", self.close_the_same_current_event)
    settings.setValue("confirm_sound", self.confirmSound)
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
    logging.debug("Save recent projects")

    settings = QSettings(str(pl.Path.home() / ".boris_recent_projects"), QSettings.IniFormat)
    settings.setValue("recent_projects", "|||".join(self.recent_projects))
