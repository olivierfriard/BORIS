"""
BORIS
Behavioral Observation Research Interactive Software
Copyright 2012-2025 Olivier Friard

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
from pathlib import Path
import sys
from . import dialog
from . import gui_utilities
from . import menu_options
from . import config as cfg
from . import config_file
from . import plugins

from .preferences_ui import Ui_prefDialog

from PySide6.QtWidgets import QDialog, QFileDialog, QListWidgetItem, QMessageBox
from PySide6.QtCore import Qt
from PySide6.QtGui import QFont


class Preferences(QDialog, Ui_prefDialog):
    def __init__(self, parent=None):
        super().__init__()
        self.setupUi(self)

        # plugins
        self.pb_browse_plugins_dir.clicked.connect(self.browse_plugins_dir)

        self.pbBrowseFFmpegCacheDir.clicked.connect(self.browseFFmpegCacheDir)

        self.pb_reset_behav_colors.clicked.connect(self.reset_behav_colors)
        self.pb_reset_category_colors.clicked.connect(self.reset_category_colors)

        self.pb_refresh.clicked.connect(self.refresh_preferences)
        self.pbOK.clicked.connect(self.accept)
        self.pbCancel.clicked.connect(self.reject)

        self.flag_refresh = False

        # Create a monospace QFont
        monospace_font = QFont("Courier New")  # or "Monospace", "Consolas", "Liberation Mono", etc.
        monospace_font.setStyleHint(QFont.Monospace)
        monospace_font.setPointSize(12)
        self.pte_plugin_code.setFont(monospace_font)

    def browse_plugins_dir(self):
        """
        get the personal plugins directory
        """
        directory = QFileDialog.getExistingDirectory(None, "Select the plugins directory", self.le_personal_plugins_dir.text())
        if not directory:
            return

        self.le_personal_plugins_dir.setText(directory)
        self.lw_personal_plugins.clear()
        for file_ in Path(directory).glob("*.py"):
            if file_.name.startswith("_"):
                continue
            plugin_name = plugins.get_plugin_name(file_)
            if plugin_name is None:
                continue
            # check if personal plugin name is in BORIS plugins (case sensitive)
            if plugin_name in [self.lv_all_plugins.item(i).text() for i in range(self.lv_all_plugins.count())]:
                continue
            item = QListWidgetItem(plugin_name)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            item.setCheckState(Qt.Checked)
            item.setData(100, str(file_))
            self.lw_personal_plugins.addItem(item)

        if self.lw_personal_plugins.count() == 0:
            QMessageBox.warning(self, cfg.programName, f"No plugin found in {directory}")

    def refresh_preferences(self):
        """
        allow user to delete the config file (.boris)
        """
        if (
            dialog.MessageDialog(
                "BORIS",
                ("Refresh will re-initialize all your preferences and close BORIS"),
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
        FFmpegCacheDir = QFileDialog.getExistingDirectory(
            self,
            "Select a directory",
            os.path.expanduser("~"),
            options=QFileDialog.ShowDirsOnly,
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

    def show_plugin_info(item):
        """
        display information about the clicked plugin
        """

        if item.text() not in self.config_param[cfg.ANALYSIS_PLUGINS]:
            return

        plugin_path = item.data(100)

        # Python plugins
        if Path(plugin_path).suffix == ".py":
            import importlib

            module_name = Path(plugin_path).stem
            spec = importlib.util.spec_from_file_location(module_name, plugin_path)
            plugin_module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(plugin_module)
            attributes_list = dir(plugin_module)

            out: list = []
            out.append((plugin_module.__plugin_name__ + "\n") if "__plugin_name__" in attributes_list else "No plugin name provided")
            out.append(plugin_module.__author__ if "__author__" in attributes_list else "No author provided")
            version_str: str = ""
            if "__version__" in attributes_list:
                version_str += str(plugin_module.__version__)
            if "__version_date__" in attributes_list:
                version_str += " " if version_str else ""
                version_str += f"({plugin_module.__version_date__})"

            out.append(f"Version: {version_str}\n" if version_str else "No version provided")

            # out.append(plugin_module.run.__doc__.strip())
            # description
            if "__description__" in attributes_list:
                out.append("Description:\n")
            out.append(plugin_module.__description__ if "__description__" in attributes_list else "No description provided")

            preferencesWindow.pte_plugin_description.setPlainText("\n".join(out))

        # R plugins
        if Path(plugin_path).suffix == ".R":
            plugin_description = plugins.get_r_plugin_description(plugin_path)
            if plugin_description is not None:
                preferencesWindow.pte_plugin_description.setPlainText("\n".join(plugin_description.split("\\n")))
            else:
                preferencesWindow.pte_plugin_description.setPlainText("No description provided")

        # display plugin code
        try:
            with open(plugin_path, "r") as f_in:
                plugin_code = f_in.read()
        except Exception:
            plugin_code = "Not available"

        preferencesWindow.pte_plugin_code.setPlainText(plugin_code)

    preferencesWindow = Preferences()
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
    preferencesWindow.leSeparator.setText(self.behav_seq_separator)
    # close same event indep of modifiers
    preferencesWindow.cbCloseSameEvent.setChecked(self.close_the_same_current_event)
    # confirm sound
    preferencesWindow.cbConfirmSound.setChecked(self.confirmSound)
    # beep every
    preferencesWindow.sbBeepEvery.setValue(self.beep_every)
    # frame step size
    # preferencesWindow.sb_frame_step_size.setValue(self.config_param.get(cfg.FRAME_STEP_SIZE, cfg.FRAME_STEP_SIZE_DEFAULT_VALUE))

    # alert no focal subject
    preferencesWindow.cbAlertNoFocalSubject.setChecked(self.alertNoFocalSubject)
    # tracking cursor above event
    preferencesWindow.cbTrackingCursorAboveEvent.setChecked(self.trackingCursorAboveEvent)
    # check for new version
    preferencesWindow.cbCheckForNewVersion.setChecked(self.checkForNewVersion)
    # display subtitles
    preferencesWindow.cb_display_subtitles.setChecked(self.config_param.get(cfg.DISPLAY_SUBTITLES, False))
    # pause before add event
    preferencesWindow.cb_pause_before_addevent.setChecked(self.pause_before_addevent)
    # MPV hwdec
    preferencesWindow.cb_hwdec.clear()
    preferencesWindow.cb_hwdec.addItems(cfg.MPV_HWDEC_OPTIONS)
    try:
        preferencesWindow.cb_hwdec.setCurrentIndex(
            cfg.MPV_HWDEC_OPTIONS.index(self.config_param.get(cfg.MPV_HWDEC, cfg.MPV_HWDEC_DEFAULT_VALUE))
        )
    except Exception:
        preferencesWindow.cb_hwdec.setCurrentIndex(cfg.MPV_HWDEC_OPTIONS.index(cfg.MPV_HWDEC_DEFAULT_VALUE))
    # check integrity
    preferencesWindow.cb_check_integrity_at_opening.setChecked(self.config_param.get(cfg.CHECK_PROJECT_INTEGRITY, True))

    # BORIS plugins
    preferencesWindow.lv_all_plugins.itemClicked.connect(show_plugin_info)

    preferencesWindow.lv_all_plugins.clear()

    for file_ in (Path(__file__).parent / "analysis_plugins").glob("*.py"):
        if file_.name.startswith("_"):
            continue
        plugin_name = plugins.get_plugin_name(file_)
        if plugin_name is not None:
            item = QListWidgetItem(plugin_name)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            if plugin_name in self.config_param.get(cfg.EXCLUDED_PLUGINS, set()):
                item.setCheckState(Qt.Unchecked)
            else:
                item.setCheckState(Qt.Checked)
            item.setData(100, str(file_))
            preferencesWindow.lv_all_plugins.addItem(item)

    # personal plugins
    preferencesWindow.le_personal_plugins_dir.setText(self.config_param.get(cfg.PERSONAL_PLUGINS_DIR, ""))
    preferencesWindow.lw_personal_plugins.itemClicked.connect(show_plugin_info)

    preferencesWindow.lw_personal_plugins.clear()
    if self.config_param.get(cfg.PERSONAL_PLUGINS_DIR, ""):
        # Python plugins
        for file_ in Path(self.config_param[cfg.PERSONAL_PLUGINS_DIR]).glob("*.py"):
            if file_.name.startswith("_"):
                continue
            plugin_name = plugins.get_plugin_name(file_)
            if plugin_name is None:
                continue
            # check if personal plugin name is in BORIS plugins (case sensitive)
            if plugin_name in [preferencesWindow.lv_all_plugins.item(i).text() for i in range(preferencesWindow.lv_all_plugins.count())]:
                continue
            item = QListWidgetItem(plugin_name)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            if plugin_name in self.config_param.get(cfg.EXCLUDED_PLUGINS, set()):
                item.setCheckState(Qt.Unchecked)
            else:
                item.setCheckState(Qt.Checked)
            item.setData(100, str(file_))
            preferencesWindow.lw_personal_plugins.addItem(item)

        # R plugins
        for file_ in Path(self.config_param[cfg.PERSONAL_PLUGINS_DIR]).glob("*.R"):
            plugin_name = plugins.get_r_plugin_name(file_)
            if plugin_name is None:
                continue
            # check if personal plugin name is in BORIS plugins (case sensitive)
            if plugin_name in [preferencesWindow.lv_all_plugins.item(i).text() for i in range(preferencesWindow.lv_all_plugins.count())]:
                continue
            item = QListWidgetItem(plugin_name)
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            if plugin_name in self.config_param.get(cfg.EXCLUDED_PLUGINS, set()):
                item.setCheckState(Qt.Unchecked)
            else:
                item.setCheckState(Qt.Checked)
            item.setData(100, str(file_))
            preferencesWindow.lw_personal_plugins.addItem(item)

    # PROJET FILE INDENTATION
    preferencesWindow.combo_project_file_indentation.clear()
    preferencesWindow.combo_project_file_indentation.addItems(cfg.PROJECT_FILE_INDENTATION_COMBO_OPTIONS)
    try:
        preferencesWindow.combo_project_file_indentation.setCurrentIndex(
            cfg.PROJECT_FILE_INDENTATION_OPTIONS.index(
                self.config_param.get(
                    cfg.PROJECT_FILE_INDENTATION,
                    cfg.PROJECT_FILE_INDENTATION_DEFAULT_VALUE,
                )
            )
        )
    except Exception:
        preferencesWindow.combo_project_file_indentation.setCurrentText(
            cfg.PROJECT_FILE_INDENTATION_COMBO_OPTIONS[
                cfg.PROJECT_FILE_INDENTATION_OPTIONS.index(cfg.PROJECT_FILE_INDENTATION_DEFAULT_VALUE)
            ]
        )

    # FFmpeg for frame by frame mode
    preferencesWindow.lbFFmpegPath.setText(f"FFmpeg path: {self.ffmpeg_bin}")
    preferencesWindow.leFFmpegCacheDir.setText(self.ffmpeg_cache_dir)

    # spectrogram
    preferencesWindow.cbSpectrogramColorMap.clear()
    preferencesWindow.cbSpectrogramColorMap.addItems(cfg.SPECTROGRAM_COLOR_MAPS)
    try:
        preferencesWindow.cbSpectrogramColorMap.setCurrentIndex(cfg.SPECTROGRAM_COLOR_MAPS.index(self.spectrogram_color_map))
    except Exception:
        preferencesWindow.cbSpectrogramColorMap.setCurrentIndex(cfg.SPECTROGRAM_COLOR_MAPS.index(cfg.SPECTROGRAM_DEFAULT_COLOR_MAP))
    # time interval
    try:
        preferencesWindow.sb_time_interval.setValue(self.spectrogram_time_interval)
    except Exception:
        preferencesWindow.sb_time_interval.setValue(cfg.SPECTROGRAM_DEFAULT_TIME_INTERVAL)
    # window type
    preferencesWindow.cb_window_type.setCurrentText(self.config_param.get(cfg.SPECTROGRAM_WINDOW_TYPE, cfg.SPECTROGRAM_DEFAULT_WINDOW_TYPE))
    # NFFT
    preferencesWindow.cb_NFFT.setCurrentText(self.config_param.get(cfg.SPECTROGRAM_NFFT, cfg.SPECTROGRAM_DEFAULT_NFFT))
    # noverlap
    preferencesWindow.sb_noverlap.setValue(self.config_param.get(cfg.SPECTROGRAM_NOVERLAP, cfg.SPECTROGRAM_DEFAULT_NOVERLAP))
    # vmin
    preferencesWindow.sb_vmin.setValue(self.config_param.get(cfg.SPECTROGRAM_VMIN, cfg.SPECTROGRAM_DEFAULT_VMIN))
    # vmax
    preferencesWindow.sb_vmax.setValue(self.config_param.get(cfg.SPECTROGRAM_VMAX, cfg.SPECTROGRAM_DEFAULT_VMAX))

    # behavior colors
    if not self.plot_colors:
        self.plot_colors = cfg.BEHAVIORS_PLOT_COLORS
    preferencesWindow.te_behav_colors.setPlainText("\n".join(self.plot_colors))

    # category colors
    if not self.behav_category_colors:
        self.behav_category_colors = cfg.CATEGORY_COLORS_LIST
    preferencesWindow.te_category_colors.setPlainText("\n".join(self.behav_category_colors))

    # interface
    preferencesWindow.sb_toolbar_icon_size.setValue(self.config_param.get(cfg.TOOLBAR_ICON_SIZE, cfg.DEFAULT_TOOLBAR_ICON_SIZE_VALUE))

    gui_utilities.restore_geometry(preferencesWindow, "preferences", (700, 500))

    while True:
        if preferencesWindow.exec():
            if preferencesWindow.sb_vmin.value() >= preferencesWindow.sb_vmax.value():
                QMessageBox.warning(self, cfg.programName, "Spectrogram parameters: the vmin value must be lower than the vmax value.")
                continue

            if preferencesWindow.sb_noverlap.value() >= int(preferencesWindow.cb_NFFT.currentText()):
                QMessageBox.warning(self, cfg.programName, "Spectrogram parameters: the noverlap value must be lower than the NFFT value.")
                continue

            gui_utilities.save_geometry(preferencesWindow, "preferences")

            if preferencesWindow.flag_refresh:
                # refresh preferences remove the config file

                logging.debug("flag refresh ")

                self.config_param["refresh_preferences"] = True
                self.close()
                # check if refresh canceled for not saved project
                if "refresh_preferences" in self.config_param:
                    if (Path.home() / ".boris").exists():
                        os.remove(Path.home() / ".boris")
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

            self.behav_seq_separator = preferencesWindow.leSeparator.text()

            self.close_the_same_current_event = preferencesWindow.cbCloseSameEvent.isChecked()

            self.confirmSound = preferencesWindow.cbConfirmSound.isChecked()

            self.beep_every = preferencesWindow.sbBeepEvery.value()

            # frame step size
            # self.config_param[cfg.FRAME_STEP_SIZE] = preferencesWindow.sb_frame_step_size.value()

            self.alertNoFocalSubject = preferencesWindow.cbAlertNoFocalSubject.isChecked()

            self.trackingCursorAboveEvent = preferencesWindow.cbTrackingCursorAboveEvent.isChecked()

            self.checkForNewVersion = preferencesWindow.cbCheckForNewVersion.isChecked()

            self.config_param[cfg.DISPLAY_SUBTITLES] = preferencesWindow.cb_display_subtitles.isChecked()

            self.pause_before_addevent = preferencesWindow.cb_pause_before_addevent.isChecked()

            # MPV hwdec
            self.config_param[cfg.MPV_HWDEC] = cfg.MPV_HWDEC_OPTIONS[preferencesWindow.cb_hwdec.currentIndex()]

            # check project integrity
            self.config_param[cfg.CHECK_PROJECT_INTEGRITY] = preferencesWindow.cb_check_integrity_at_opening.isChecked()

            # update BORIS analysis plugins
            self.config_param[cfg.ANALYSIS_PLUGINS] = {}
            self.config_param[cfg.EXCLUDED_PLUGINS] = set()
            for i in range(preferencesWindow.lv_all_plugins.count()):
                if preferencesWindow.lv_all_plugins.item(i).checkState() == Qt.Checked:
                    self.config_param[cfg.ANALYSIS_PLUGINS][preferencesWindow.lv_all_plugins.item(i).text()] = (
                        preferencesWindow.lv_all_plugins.item(i).data(100)
                    )
                else:
                    self.config_param[cfg.EXCLUDED_PLUGINS].add(preferencesWindow.lv_all_plugins.item(i).text())

            # update personal plugins
            self.config_param[cfg.PERSONAL_PLUGINS_DIR] = preferencesWindow.le_personal_plugins_dir.text()
            for i in range(preferencesWindow.lw_personal_plugins.count()):
                if preferencesWindow.lw_personal_plugins.item(i).checkState() == Qt.Checked:
                    self.config_param[cfg.ANALYSIS_PLUGINS][preferencesWindow.lw_personal_plugins.item(i).text()] = (
                        preferencesWindow.lw_personal_plugins.item(i).data(100)
                    )
                else:
                    self.config_param[cfg.EXCLUDED_PLUGINS].add(preferencesWindow.lw_personal_plugins.item(i).text())

            plugins.load_plugins(self)
            plugins.add_plugins_to_menu(self)

            # project file indentation
            self.config_param[cfg.PROJECT_FILE_INDENTATION] = cfg.PROJECT_FILE_INDENTATION_OPTIONS[
                preferencesWindow.combo_project_file_indentation.currentIndex()
            ]

            if self.observationId:
                self.load_tw_events(self.observationId)
                self.display_statusbar_info(self.observationId)

            self.ffmpeg_cache_dir = preferencesWindow.leFFmpegCacheDir.text()

            # spectrogram
            self.spectrogram_color_map = preferencesWindow.cbSpectrogramColorMap.currentText()
            self.spectrogram_time_interval = preferencesWindow.sb_time_interval.value()
            # window type
            self.config_param[cfg.SPECTROGRAM_WINDOW_TYPE] = preferencesWindow.cb_window_type.currentText()
            # NFFT
            self.config_param[cfg.SPECTROGRAM_NFFT] = preferencesWindow.cb_NFFT.currentText()
            # noverlap
            self.config_param[cfg.SPECTROGRAM_NOVERLAP] = preferencesWindow.sb_noverlap.value()
            # vmin
            self.config_param[cfg.SPECTROGRAM_VMIN] = preferencesWindow.sb_vmin.value()
            # vmax
            self.config_param[cfg.SPECTROGRAM_VMAX] = preferencesWindow.sb_vmax.value()

            # behav colors
            self.plot_colors = preferencesWindow.te_behav_colors.toPlainText().split()
            # category colors
            self.behav_category_colors = preferencesWindow.te_category_colors.toPlainText().split()

            # interface
            self.config_param[cfg.TOOLBAR_ICON_SIZE] = preferencesWindow.sb_toolbar_icon_size.value()

            menu_options.update_menu(self)

            config_file.save(self)

            break

        else:
            break

    # activate main window
    self.activateWindow()
