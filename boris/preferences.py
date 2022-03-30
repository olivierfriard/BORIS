"""
BORIS
Behavioral Observation Research Interactive Software
Copyright 2012-2022 Olivier Friard

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

"""

import logging
import os
import pathlib
import sys

from . import dialog
from . import gui_utilities
from . import menu_options
from . import config as cfg

from .preferences_ui import Ui_prefDialog

from PyQt5.QtWidgets import QDialog, QFileDialog, MessageDialog


class Preferences(QDialog, Ui_prefDialog):
    def __init__(self, parent=None):

        super().__init__()
        self.setupUi(self)

        self.pbBrowseFFmpegCacheDir.clicked.connect(self.browseFFmpegCacheDir)

        self.pb_reset_behav_colors.clicked.connect(self.reset_behav_colors)
        self.pb_reset_category_colors.clicked.connect(self.reset_category_colors)

        self.pb_refresh.clicked.connect(self.refresh_preferences)
        self.pbOK.clicked.connect(self.accept)
        self.pbCancel.clicked.connect(self.reject)

        self.flag_refresh = False
        self.flag_reset_frames_memory = False

    def refresh_preferences(self):
        """
        allow user to delete the config file (.boris)
        """
        if (
            MessageDialog(
                "BORIS",
                ("Refresh will re-initialize " "all your preferences and close BORIS"),
                [cfg.CANCEL, "Refresh preferences"],
            )
            == "Refresh preferences"
        ):
            self.flag_refresh = True
            self.accept()

    def browseFFmpegCacheDir(self):
        """
        allow user select a cache dir for ffmpeg images
        """
        FFmpegCacheDir = QFileDialog().getExistingDirectory(
            self, "Select a directory", os.path.expanduser("~"), options=QFileDialog().ShowDirsOnly
        )
        if FFmpegCacheDir:
            self.leFFmpegCacheDir.setText(FFmpegCacheDir)

    def reset_behav_colors(self):
        """
        reset behavior colors to default
        """
        self.te_behav_colors.setPlainText("\n".join(cfg.BEHAVIORS_PLOT_COLORS))

        logging.debug("reset behaviors colors to default")

    def reset_category_colors(self):
        """
        reset category colors to default
        """
        self.te_category_colors.setPlainText("\n".join(cfg.CATEGORY_COLORS_LIST))

        logging.debug("reset category colors to default")


def preferences(self):
    """
    show preferences window
    """

    try:
        preferencesWindow = preferences.Preferences()
        preferencesWindow.tabWidget.setCurrentIndex(0)

        if self.timeFormat == cfg.S:
            preferencesWindow.cbTimeFormat.setCurrentIndex(0)

        if self.timeFormat == cfg.HHMMSS:
            preferencesWindow.cbTimeFormat.setCurrentIndex(1)

        preferencesWindow.sbffSpeed.setValue(self.fast)
        preferencesWindow.cb_adapt_fast_jump.setChecked(self.config_param.get(cfg.ADAPT_FAST_JUMP, False))
        preferencesWindow.sbRepositionTimeOffset.setValue(self.repositioningTimeOffset)
        preferencesWindow.sbSpeedStep.setValue(self.play_rate_step)
        # automatic backup
        preferencesWindow.sbAutomaticBackup.setValue(self.automaticBackup)
        # separator for behavioural strings
        preferencesWindow.leSeparator.setText(self.behaviouralStringsSeparator)
        # close same event indep of modifiers
        preferencesWindow.cbCloseSameEvent.setChecked(self.close_the_same_current_event)
        # confirm sound
        preferencesWindow.cbConfirmSound.setChecked(self.confirmSound)
        # beep every
        preferencesWindow.sbBeepEvery.setValue(self.beep_every)
        # alert no focal subject
        preferencesWindow.cbAlertNoFocalSubject.setChecked(self.alertNoFocalSubject)
        # tracking cursor above event
        preferencesWindow.cbTrackingCursorAboveEvent.setChecked(self.trackingCursorAboveEvent)
        # check for new version
        preferencesWindow.cbCheckForNewVersion.setChecked(self.checkForNewVersion)
        # display subtitles
        preferencesWindow.cb_display_subtitles.setChecked(self.config_param[cfg.DISPLAY_SUBTITLES])
        # pause before add event
        preferencesWindow.cb_pause_before_addevent.setChecked(self.pause_before_addevent)

        preferencesWindow.cb_compact_time_budget.setChecked(
            self.config_param.get(cfg.TIME_BUDGET_FORMAT, cfg.DEFAULT_TIME_BUDGET_FORMAT)
            == cfg.COMPACT_TIME_BUDGET_FORMAT
        )

        # FFmpeg for frame by frame mode
        preferencesWindow.lbFFmpegPath.setText(f"FFmpeg path: {self.ffmpeg_bin}")
        preferencesWindow.leFFmpegCacheDir.setText(self.ffmpeg_cache_dir)
        preferencesWindow.sbFFmpegCacheDirMaxSize.setValue(self.ffmpeg_cache_dir_max_size)

        # frame-by-frame mode
        """
        if self.config_param.get(SAVE_FRAMES, DEFAULT_FRAME_MODE) == MEMORY:
            preferencesWindow.rb_save_frames_in_mem.setChecked(True)
        if self.config_param.get(SAVE_FRAMES, DEFAULT_FRAME_MODE) == DISK:
            preferencesWindow.rb_save_frames_on_disk.setChecked(True)
        for w in [preferencesWindow.lb_memory_frames, preferencesWindow.sb_frames_memory_size, preferencesWindow.lb_memory_info]:
            w.setEnabled(preferencesWindow.rb_save_frames_in_mem.isChecked())
        for w in [preferencesWindow.lb_storage_dir]:
            w.setEnabled(preferencesWindow.rb_save_frames_on_disk.isChecked())

        preferencesWindow.sb_frames_memory_size.setValue(self.config_param.get(MEMORY_FOR_FRAMES, DEFAULT_MEMORY_FOR_FRAMES))
        """
        """
        r, mem = utilities.mem_info()
        if not r:
            preferencesWindow.lb_memory_info.setText((f"Total memory: {mem.get('total_memory', 'Not available')} Mb"
                                                        f"<br>Free memory: {mem.get('free_memory', 'Not available')} Mb"))
        else:
            preferencesWindow.lb_memory_info.setText("Memory information not available")

        # frames buffer
        preferencesWindow.lb_memory_info.setText(f"{preferencesWindow.lb_memory_info.text()}")



        preferencesWindow.cbFrameBitmapFormat.clear()
        preferencesWindow.cbFrameBitmapFormat.addItems(FRAME_BITMAP_FORMAT_LIST)

        try:
            preferencesWindow.cbFrameBitmapFormat.setCurrentIndex(FRAME_BITMAP_FORMAT_LIST.index(self.frame_bitmap_format))
        except Exception:
            preferencesWindow.cbFrameBitmapFormat.setCurrentIndex(FRAME_BITMAP_FORMAT_LIST.index(FRAME_DEFAULT_BITMAP_FORMAT))
        """

        # spectrogram
        preferencesWindow.cbSpectrogramColorMap.clear()
        preferencesWindow.cbSpectrogramColorMap.addItems(cfg.SPECTROGRAM_COLOR_MAPS)
        try:
            preferencesWindow.cbSpectrogramColorMap.setCurrentIndex(
                cfg.SPECTROGRAM_COLOR_MAPS.index(self.spectrogram_color_map)
            )
        except Exception:
            preferencesWindow.cbSpectrogramColorMap.setCurrentIndex(
                cfg.SPECTROGRAM_COLOR_MAPS.index(cfg.SPECTROGRAM_DEFAULT_COLOR_MAP)
            )

        try:
            preferencesWindow.cbSpectrogramColorMap.setCurrentIndex(
                cfg.SPECTROGRAM_COLOR_MAPS.index(self.spectrogram_color_map)
            )
        except Exception:
            preferencesWindow.cbSpectrogramColorMap.setCurrentIndex(
                cfg.SPECTROGRAM_COLOR_MAPS.index(cfg.SPECTROGRAM_DEFAULT_COLOR_MAP)
            )

        try:
            preferencesWindow.sb_time_interval.setValue(self.spectrogram_time_interval)
        except Exception:
            preferencesWindow.sb_time_interval.setValue(cfg.SPECTROGRAM_DEFAULT_TIME_INTERVAL)

        # behavior colors
        if not self.plot_colors:
            self.plot_colors = cfg.BEHAVIORS_PLOT_COLORS
        preferencesWindow.te_behav_colors.setPlainText("\n".join(self.plot_colors))

        # category colors
        if not self.behav_category_colors:
            self.behav_category_colors = cfg.CATEGORY_COLORS_LIST
        preferencesWindow.te_category_colors.setPlainText("\n".join(self.behav_category_colors))

        gui_utilities.restore_geometry(preferencesWindow, "preferences", (700, 500))

        if preferencesWindow.exec_():

            gui_utilities.save_geometry(preferencesWindow, "preferences")

            if preferencesWindow.flag_refresh:
                # refresh preferences remove the config file

                logging.debug("flag refresh ")

                self.config_param["refresh_preferences"] = True
                self.close()
                # check if refresh canceled for not saved project
                if "refresh_preferences" in self.config_param:
                    if (pathlib.Path.home() / ".boris").exists():
                        os.remove(pathlib.Path.home() / ".boris")
                    sys.exit()

            if preferencesWindow.cbTimeFormat.currentIndex() == 0:
                self.timeFormat = cfg.S

            if preferencesWindow.cbTimeFormat.currentIndex() == 1:
                self.timeFormat = cfg.HHMMSS

            self.fast = preferencesWindow.sbffSpeed.value()

            self.config_param[cfg.ADAPT_FAST_JUMP] = preferencesWindow.cb_adapt_fast_jump.isChecked()

            self.repositioningTimeOffset = preferencesWindow.sbRepositionTimeOffset.value()

            self.play_rate_step = preferencesWindow.sbSpeedStep.value()

            self.automaticBackup = preferencesWindow.sbAutomaticBackup.value()
            if self.automaticBackup:
                self.automaticBackupTimer.start(self.automaticBackup * 60000)
            else:
                self.automaticBackupTimer.stop()

            self.behaviouralStringsSeparator = preferencesWindow.leSeparator.text()

            self.close_the_same_current_event = preferencesWindow.cbCloseSameEvent.isChecked()

            self.confirmSound = preferencesWindow.cbConfirmSound.isChecked()

            self.beep_every = preferencesWindow.sbBeepEvery.value()

            self.alertNoFocalSubject = preferencesWindow.cbAlertNoFocalSubject.isChecked()

            self.trackingCursorAboveEvent = preferencesWindow.cbTrackingCursorAboveEvent.isChecked()

            self.checkForNewVersion = preferencesWindow.cbCheckForNewVersion.isChecked()

            self.config_param[cfg.DISPLAY_SUBTITLES] = preferencesWindow.cb_display_subtitles.isChecked()
            """
            st_track_number = 0 if self.config_param[DISPLAY_SUBTITLES] else -1
            for player in self.dw_player:
                player.mediaplayer.video_set_spu(st_track_number)
            """

            self.pause_before_addevent = preferencesWindow.cb_pause_before_addevent.isChecked()

            if self.observationId:
                self.loadEventsInTW(self.observationId)
                self.display_statusbar_info(self.observationId)

            # result

            if preferencesWindow.cb_compact_time_budget.isChecked():
                self.config_param[cfg.TIME_BUDGET_FORMAT] = cfg.COMPACT_TIME_BUDGET_FORMAT
            else:
                self.config_param[cfg.TIME_BUDGET_FORMAT] = cfg.DEFAULT_TIME_BUDGET_FORMAT

            self.ffmpeg_cache_dir = preferencesWindow.leFFmpegCacheDir.text()
            self.ffmpeg_cache_dir_max_size = preferencesWindow.sbFFmpegCacheDirMaxSize.value()

            # spectrogram
            self.spectrogram_color_map = preferencesWindow.cbSpectrogramColorMap.currentText()
            # self.spectrogramHeight = preferencesWindow.sbSpectrogramHeight.value()
            self.spectrogram_time_interval = preferencesWindow.sb_time_interval.value()

            # behav colors
            self.plot_colors = preferencesWindow.te_behav_colors.toPlainText().split()
            # category colors
            self.behav_category_colors = preferencesWindow.te_category_colors.toPlainText().split()

            menu_options.update_menu(self)

            self.saveConfigFile()

    except Exception:
        dialog.error_message2()
