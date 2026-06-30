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

"""

import logging
import os
import sys
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QApplication, QDialog, QFileDialog, QListWidgetItem, QMessageBox

from . import config as cfg
from . import config_file, dialog, gui_utilities, menu_options, plugins
from .preferences_ui import Ui_prefDialog

PLUGIN_PATH_ROLE = 100
PLUGIN_NAME_ROLE = 101


class Preferences(QDialog, Ui_prefDialog):
    def __init__(self, parent=None):
        super().__init__()
        self.setupUi(self)

        # plugins
        self.pb_browse_official_plugins_dir.clicked.connect(self.browse_official_plugins_dir)
        self.pb_refresh_official_plugins_releases.clicked.connect(self.refresh_official_plugins_releases)
        self.pb_download_official_plugins.clicked.connect(self.download_official_plugins)
        self.pb_browse_plugins_dir.clicked.connect(self.browse_plugins_dir)
        self.pb_clear_plugins_dir.clicked.connect(self.clear_plugins_dir)

        self.pbBrowseFFmpegCacheDir.clicked.connect(self.browseFFmpegCacheDir)

        self.pb_reset_behav_colors.clicked.connect(self.reset_behav_colors)
        self.pb_reset_category_colors.clicked.connect(self.reset_category_colors)

        self.pb_refresh.clicked.connect(self.refresh_preferences)
        self.pbOK.clicked.connect(self.accept)
        self.pbCancel.clicked.connect(self.reject)

        self.pb_reset_spectro_values.clicked.connect(self.reset_spectro_values)
        self.cb_use_vmin_vmax.toggled.connect(self.cb_vmin_vmax_changed)

        self.flag_refresh = False

        # Create a monospace QFont
        monospace_font = QFont("Courier New")
        monospace_font.setStyleHint(QFont.Monospace)
        monospace_font.setPointSize(12)
        self.pte_plugin_code.setFont(monospace_font)
        self.reset_official_plugins_release_combo()
        self.installed_official_plugins_source = plugins.official_plugins_branch_source()

    def reset_official_plugins_release_combo(self):
        """
        reset the official plugins release selector to the default branch
        """
        self.cb_official_plugins_release.clear()
        source = plugins.official_plugins_branch_source()
        self.cb_official_plugins_release.addItem(source["text"], source)

    def official_plugins_source_index(self, source: dict) -> int:
        """
        return the index of the official plugins source in the release selector
        """
        archive_url = source.get("archive_url", "")
        for index in range(self.cb_official_plugins_release.count()):
            item_source = plugins.normalize_official_plugins_source(self.cb_official_plugins_release.itemData(index))
            if item_source.get("archive_url") == archive_url:
                return index
        return -1

    def set_official_plugins_source(self, source: dict | None):
        """
        select and remember the official plugins source.
        """
        source = plugins.normalize_official_plugins_source(source)
        index = self.official_plugins_source_index(source)
        if index < 0:
            self.cb_official_plugins_release.addItem(source["text"], source)
            index = self.cb_official_plugins_release.count() - 1

        self.cb_official_plugins_release.setCurrentIndex(index)
        self.installed_official_plugins_source = source

    def current_official_plugins_source(self) -> dict[str, str]:
        """
        return the source selected for the next official plugins download.
        """
        return plugins.normalize_official_plugins_source(self.cb_official_plugins_release.currentData())

    def plugin_item_text(self, plugin_name: str, plugin_version: str | None = None) -> str:
        """
        return the displayed plugin name with version, when available
        """
        return f"{plugin_name} (v. {plugin_version})" if plugin_version else plugin_name

    def plugin_item_name(self, item: QListWidgetItem) -> str:
        """
        return the plugin name stored in a list item
        """
        return item.data(PLUGIN_NAME_ROLE) or item.text()

    def populate_python_plugins_list(
        self,
        list_widget,
        plugin_files: list[Path],
        excluded_plugins: set | None = None,
        skip_plugin_names: set | None = None,
    ) -> set[str]:
        """
        populate a list widget with Python plugins
        """
        excluded_plugins = excluded_plugins or set()
        skip_plugin_names = skip_plugin_names or set()
        plugin_names: set[str] = set()

        list_widget.clear()
        for file_ in plugin_files:
            plugin_name = plugins.get_plugin_name(file_)
            if plugin_name is None or plugin_name in skip_plugin_names:
                continue

            plugin_version = plugins.get_plugin_version(file_)
            item = QListWidgetItem(self.plugin_item_text(plugin_name, plugin_version))
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            if plugin_name in excluded_plugins:
                item.setCheckState(Qt.CheckState.Unchecked)
            else:
                item.setCheckState(Qt.CheckState.Checked)
            item.setData(PLUGIN_PATH_ROLE, str(file_))
            item.setData(PLUGIN_NAME_ROLE, plugin_name)
            list_widget.addItem(item)
            plugin_names.add(plugin_name)

        return plugin_names

    def official_plugin_names(self) -> set[str]:
        """
        return the names currently displayed in the official plugins list
        """
        return {self.plugin_item_name(self.lv_all_plugins.item(i)) for i in range(self.lv_all_plugins.count())}

    def browse_official_plugins_dir(self):
        """
        get the official BORIS plugins repository directory
        """
        directory = QFileDialog.getExistingDirectory(
            None,
            "Select the official BORIS plugins repository directory",
            self.le_official_plugins_dir.text(),
        )
        if not directory:
            return

        self.le_official_plugins_dir.setText(directory)
        config_param = {cfg.OFFICIAL_PLUGINS_DIR: directory}
        self.populate_python_plugins_list(self.lv_all_plugins, plugins.get_official_plugin_files(config_param))

        if self.le_personal_plugins_dir.text():
            self.populate_python_plugins_list(
                self.lw_personal_plugins,
                plugins.get_python_plugin_files(self.le_personal_plugins_dir.text()),
                skip_plugin_names=self.official_plugin_names(),
            )

    def refresh_official_plugins_releases(self):
        """
        fetch the official BORIS plugins releases list from GitHub
        """
        current_source = self.current_official_plugins_source()

        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        release_error = None
        try:
            releases = plugins.list_official_plugins_releases()
        except Exception as exc:
            releases = []
            release_error = exc
        finally:
            QApplication.restoreOverrideCursor()

        if release_error is not None:
            QMessageBox.critical(self, cfg.programName, f"Error loading official BORIS plugins releases:\n\n{release_error}")
            return

        self.reset_official_plugins_release_combo()
        for release in releases:
            self.cb_official_plugins_release.addItem(release["text"], release)

        index = self.official_plugins_source_index(current_source)
        if index < 0:
            self.cb_official_plugins_release.addItem(current_source["text"], current_source)
            index = self.cb_official_plugins_release.count() - 1
        self.cb_official_plugins_release.setCurrentIndex(index)

        if not releases:
            QMessageBox.information(self, cfg.programName, "No official BORIS plugins release found.")

    def download_official_plugins(self):
        """
        download or update the official BORIS plugins repository
        """
        target_dir = (
            Path(self.le_official_plugins_dir.text()).expanduser()
            if self.le_official_plugins_dir.text()
            else plugins.get_default_external_plugins_dir()
        )

        source = self.current_official_plugins_source()
        archive_url = source["archive_url"]
        archive_text = source["text"]

        if target_dir.exists() and any(target_dir.iterdir()):
            answer = QMessageBox.question(
                self,
                cfg.programName,
                (
                    f"Download/update official BORIS plugins in:\n{target_dir}\n\n"
                    f"Source: {archive_text}\n\n"
                    "Existing files in this directory will be replaced.\n\n"
                    "Continue?"
                ),
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if answer != QMessageBox.StandardButton.Yes:
                return

        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        download_error = None
        try:
            plugin_dir = plugins.download_official_plugins_repository(target_dir, archive_url)
        except Exception as exc:
            download_error = exc
        finally:
            QApplication.restoreOverrideCursor()

        if download_error is not None:
            QMessageBox.critical(self, cfg.programName, f"Error downloading official BORIS plugins:\n\n{download_error}")
            return

        self.installed_official_plugins_source = source
        self.le_official_plugins_dir.setText(str(target_dir))
        config_param = {cfg.OFFICIAL_PLUGINS_DIR: str(target_dir)}
        self.populate_python_plugins_list(self.lv_all_plugins, plugins.get_official_plugin_files(config_param))

        if self.le_personal_plugins_dir.text():
            self.populate_python_plugins_list(
                self.lw_personal_plugins,
                plugins.get_python_plugin_files(self.le_personal_plugins_dir.text()),
                skip_plugin_names=self.official_plugin_names(),
            )

        QMessageBox.information(self, cfg.programName, f"Official BORIS plugins updated from {archive_text}:\n{plugin_dir}")

    def reset_spectro_values(self):
        """
        reset spectrogram values to default
        """
        self.cbSpectrogramColorMap.setCurrentIndex(cfg.SPECTROGRAM_COLOR_MAPS.index(cfg.SPECTROGRAM_DEFAULT_COLOR_MAP))
        self.sb_time_interval.setValue(cfg.SPECTROGRAM_DEFAULT_TIME_INTERVAL)
        self.cb_window_type.setCurrentText(cfg.SPECTROGRAM_DEFAULT_WINDOW_TYPE)
        self.cb_NFFT.setCurrentText(cfg.SPECTROGRAM_DEFAULT_NFFT)
        self.sb_noverlap.setValue(cfg.SPECTROGRAM_DEFAULT_NOVERLAP)
        self.cb_pre_emphasize.setChecked(cfg.SPECTROGRAM_PRE_EMPHASIZE_DEFAULT)
        self.cb_use_vmin_vmax.setChecked(cfg.SPECTROGRAM_USE_VMIN_VMAX_DEFAULT)
        self.cb_vmin_vmax_changed()
        self.sb_vmin.setValue(cfg.SPECTROGRAM_DEFAULT_VMIN)
        self.sb_vmax.setValue(cfg.SPECTROGRAM_DEFAULT_VMAX)

    def cb_vmin_vmax_changed(self):
        """
        activate or de-activate vmin and vmax
        """
        for w in (self.sb_vmin, self.sb_vmax, self.label_vmin, self.label_vmin_2, self.label_vmax, self.label_vmax_2):
            w.setEnabled(self.cb_use_vmin_vmax.isChecked())

    def browse_plugins_dir(self):
        """
        get the personal plugins directory
        """
        directory = QFileDialog.getExistingDirectory(None, "Select the plugins directory", self.le_personal_plugins_dir.text())
        if not directory:
            return

        self.le_personal_plugins_dir.setText(directory)
        self.populate_python_plugins_list(
            self.lw_personal_plugins,
            plugins.get_python_plugin_files(directory),
            skip_plugin_names=self.official_plugin_names(),
        )

        if self.lw_personal_plugins.count() == 0:
            QMessageBox.warning(self, cfg.programName, f"No plugin found in {directory}")

    def clear_plugins_dir(self):
        """
        clear the personal plugins directory path without deleting files
        """
        self.le_personal_plugins_dir.clear()
        self.lw_personal_plugins.clear()
        self.pte_plugin_description.clear()
        self.pte_plugin_code.clear()

    def refresh_preferences(self):
        """
        allow user to delete the config file (.boris)
        """
        if (
            dialog.MessageDialog(
                "BORIS",
                ("Refresh will re-initialize all your preferences and close BORIS"),
                (cfg.CANCEL, "Refresh preferences"),
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

        plugin_path = item.data(PLUGIN_PATH_ROLE)
        if not plugin_path:
            return

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
            plugin_name = item.data(PLUGIN_NAME_ROLE) or plugins.get_r_plugin_name(plugin_path)
            plugin_version = plugins.get_r_plugin_version(plugin_path)
            plugin_description = plugins.get_r_plugin_description(plugin_path)
            out: list = []
            out.append((plugin_name + "\n") if plugin_name else "No plugin name provided")
            out.append(f"Version: {plugin_version}\n" if plugin_version else "No version provided")
            if plugin_description is not None:
                out.append("Description:\n")
                out.append("\n".join(plugin_description.split("\\n")))
            else:
                out.append("No description provided")
            preferencesWindow.pte_plugin_description.setPlainText("\n".join(out))

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

    # Official BORIS plugins
    preferencesWindow.lv_all_plugins.itemClicked.connect(show_plugin_info)

    configured_plugins_dir = self.config_param.get(cfg.OFFICIAL_PLUGINS_DIR, "")
    preferencesWindow.le_official_plugins_dir.setText(configured_plugins_dir)
    preferencesWindow.set_official_plugins_source(self.config_param.get(cfg.OFFICIAL_PLUGINS_SOURCE))
    preferencesWindow.populate_python_plugins_list(
        preferencesWindow.lv_all_plugins,
        plugins.get_official_plugin_files(self.config_param),
        self.config_param.get(cfg.EXCLUDED_PLUGINS, set()),
    )

    # personal plugins
    preferencesWindow.le_personal_plugins_dir.setText(self.config_param.get(cfg.PERSONAL_PLUGINS_DIR, ""))
    preferencesWindow.lw_personal_plugins.itemClicked.connect(show_plugin_info)

    if self.config_param.get(cfg.PERSONAL_PLUGINS_DIR, ""):
        # Python plugins
        preferencesWindow.populate_python_plugins_list(
            preferencesWindow.lw_personal_plugins,
            plugins.get_python_plugin_files(self.config_param[cfg.PERSONAL_PLUGINS_DIR]),
            self.config_param.get(cfg.EXCLUDED_PLUGINS, set()),
            preferencesWindow.official_plugin_names(),
        )

        # R plugins
        for file_ in Path(self.config_param[cfg.PERSONAL_PLUGINS_DIR]).glob("*.R"):
            plugin_name = plugins.get_r_plugin_name(file_)
            if plugin_name is None:
                continue
            # check if personal plugin name is in BORIS plugins (case sensitive)
            if plugin_name in preferencesWindow.official_plugin_names():
                continue
            plugin_version = plugins.get_r_plugin_version(file_)
            item = QListWidgetItem(preferencesWindow.plugin_item_text(plugin_name, plugin_version))
            item.setFlags(item.flags() | Qt.ItemIsUserCheckable)
            if plugin_name in self.config_param.get(cfg.EXCLUDED_PLUGINS, set()):
                item.setCheckState(Qt.CheckState.Unchecked)
            else:
                item.setCheckState(Qt.CheckState.Checked)
            item.setData(PLUGIN_PATH_ROLE, str(file_))
            item.setData(PLUGIN_NAME_ROLE, plugin_name)
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
    # pre-emphasize
    preferencesWindow.cb_pre_emphasize.setChecked(
        self.config_param.get(cfg.SPECTROGRAM_PRE_EMPHASIZE, cfg.SPECTROGRAM_PRE_EMPHASIZE_DEFAULT)
    )
    # use vmin/xmax
    preferencesWindow.cb_use_vmin_vmax.setChecked(
        self.config_param.get(cfg.SPECTROGRAM_USE_VMIN_VMAX, cfg.SPECTROGRAM_USE_VMIN_VMAX_DEFAULT)
    )
    preferencesWindow.cb_vmin_vmax_changed()
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
            if preferencesWindow.cb_use_vmin_vmax.isChecked() and preferencesWindow.sb_vmin.value() >= preferencesWindow.sb_vmax.value():
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

            # update official BORIS analysis plugins
            self.config_param[cfg.OFFICIAL_PLUGINS_DIR] = preferencesWindow.le_official_plugins_dir.text()
            self.config_param[cfg.OFFICIAL_PLUGINS_SOURCE] = preferencesWindow.installed_official_plugins_source
            self.config_param[cfg.ANALYSIS_PLUGINS] = {}
            self.config_param[cfg.EXCLUDED_PLUGINS] = set()
            for i in range(preferencesWindow.lv_all_plugins.count()):
                item = preferencesWindow.lv_all_plugins.item(i)
                plugin_name = preferencesWindow.plugin_item_name(item)
                if item.checkState() == Qt.CheckState.Checked:
                    self.config_param[cfg.ANALYSIS_PLUGINS][plugin_name] = item.data(PLUGIN_PATH_ROLE)
                else:
                    self.config_param[cfg.EXCLUDED_PLUGINS].add(plugin_name)

            # update personal plugins
            self.config_param[cfg.PERSONAL_PLUGINS_DIR] = preferencesWindow.le_personal_plugins_dir.text()
            for i in range(preferencesWindow.lw_personal_plugins.count()):
                item = preferencesWindow.lw_personal_plugins.item(i)
                plugin_name = preferencesWindow.plugin_item_name(item)
                if item.checkState() == Qt.CheckState.Checked:
                    self.config_param[cfg.ANALYSIS_PLUGINS][plugin_name] = item.data(PLUGIN_PATH_ROLE)
                else:
                    self.config_param[cfg.EXCLUDED_PLUGINS].add(plugin_name)

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
            # pre-emphasize
            self.config_param[cfg.SPECTROGRAM_PRE_EMPHASIZE] = preferencesWindow.cb_pre_emphasize.isChecked()
            # use vmin/vmax
            self.config_param[cfg.SPECTROGRAM_USE_VMIN_VMAX] = preferencesWindow.cb_use_vmin_vmax.isChecked()
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
