"""
BORIS
Behavioral Observation Research Interactive Software
Copyright 2012-2025 Olivier Friard

  This program is free software; you can redistribute it and/or modify
  it under the terms of the GNU General Public License as published by
  the Free Software Foundation; either version 2 of the License, or
  (at your option) any later version.

  This program is distributed in the hope that it will be useful,
  but WITHOUT ANY WARRANTY; without even the implied warranty of
  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
  GNU General Public License for more details.

  You should have received a copy of the GNU General Public License
  along with this program; if not, write to the Free Software
  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
  MA 02110-1301, USA.
"""

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QAction

from . import config as cfg
from . import (
    about,
    behav_coding_map_creator,
    behavior_binary_table,
    behaviors_coding_map,
    coding_pad,
    event_operations,
    events_snapshots,
    export_events,
    geometric_measurement,
    image_overlay,
    import_observations,
    irr,
    latency,
    cooccurence,
    media_file,
    observation_operations,
    preferences,
    project_import_export,
    synthetic_time_budget,
    time_budget_widget,
    transitions,
    video_equalizer,
    video_operations,
    project_functions,
    external_processes,
)

from . import state_events as state_events


def connections(self):
    """
    create connections between widgets and functions
    """

    # menu file
    self.actionNew_project.triggered.connect(lambda: self.edit_project(cfg.NEW))
    self.actionOpen_project.triggered.connect(self.open_project_activated)
    self.actionNoldus_Observer_template.triggered.connect(self.import_project_from_observer_template)
    self.actionEdit_project.triggered.connect(self.edit_project_activated)
    self.actionCheck_project.triggered.connect(self.check_project_integrity)
    self.actionSave_project.triggered.connect(self.save_project_activated)
    self.actionSave_project_as.triggered.connect(self.save_project_as_activated)
    self.actionExport_project.triggered.connect(lambda: project_import_export.export_project_as_pickle_object(self.pj))
    self.actionClose_project.triggered.connect(self.close_project)

    self.action_media_file_and_images_directories_relative_path.triggered.connect(self.set_media_files_path_relative_to_project_dir)
    self.action_data_files_relative_path.triggered.connect(self.set_data_files_path_relative_to_project_dir)

    self.action_remove_media_files_and_images_directories_path.triggered.connect(self.remove_media_files_path)
    self.action_remove_data_files_path.triggered.connect(self.remove_data_files_path)

    self.menuCreate_subtitles_2.triggered.connect(self.create_subtitles)

    self.actionPreferences.triggered.connect(lambda: preferences.preferences(self))

    self.actionQuit.triggered.connect(self.actionQuit_activated)

    # menu observations
    self.actionNew_observation.triggered.connect(lambda: observation_operations.new_observation(self, mode=cfg.NEW, obsId=""))

    self.actionOpen_observation.triggered.connect(lambda: observation_operations.open_observation(self, mode=cfg.OBS_START))
    self.actionView_observation.triggered.connect(lambda: observation_operations.open_observation(self, mode=cfg.VIEW))
    self.actionEdit_observation_2.triggered.connect(lambda: observation_operations.edit_observation(self))
    self.actionObservationsList.triggered.connect(lambda: observation_operations.observations_list(self))

    self.actionClose_observation.triggered.connect(lambda: observation_operations.close_observation(self))

    self.action_create_observations.triggered.connect(lambda: observation_operations.create_observations(self))
    self.actionRemove_observations.triggered.connect(lambda: observation_operations.remove_observations(self))

    self.actionAdd_event.triggered.connect(lambda: event_operations.add_event(self))
    self.actionEdit_event.triggered.connect(lambda: event_operations.edit_event(self))
    self.actionUndo.setEnabled(False)
    self.actionUndo.triggered.connect(lambda: event_operations.undo_event_operation(self))
    self.actionFilter_events.triggered.connect(lambda: event_operations.filter_events(self))
    self.actionShow_all_events.triggered.connect(lambda: event_operations.show_all_events(self))

    # twevent header
    # self.actionConfigure_twEvents_columns.triggered.connect(self.configure_twevents_columns)

    # tv_events header
    self.actionConfigure_tvevents_columns.triggered.connect(self.configure_tvevents_columns)

    self.actionExport_observations_list.triggered.connect(lambda: observation_operations.export_observations_list_clicked(self))

    self.actionCheckStateEvents.triggered.connect(lambda: state_events.check_state_events(self, mode="all"))
    self.actionCheckStateEventsSingleObs.triggered.connect(lambda: state_events.check_state_events(self, mode="current"))
    self.actionClose_unpaired_events.triggered.connect(lambda: state_events.fix_unpaired_events(self))
    self.actionAdd_frame_indexes.triggered.connect(lambda: event_operations.add_frame_indexes(self))

    self.actionRunEventOutside.triggered.connect(self.run_event_outside)

    self.actionSelect_observations.triggered.connect(lambda: event_operations.select_events_between_activated(self))

    self.actionEdit_selected_events.triggered.connect(lambda: event_operations.edit_selected_events(self))
    self.actionEdit_event_time.triggered.connect(lambda: event_operations.edit_time_selected_events(self))

    self.actionCopy_events.triggered.connect(lambda: event_operations.copy_selected_events(self))
    self.actionPaste_events.triggered.connect(lambda: event_operations.paste_clipboard_to_events(self))

    self.actionExplore_project.triggered.connect(lambda: project_functions.explore_project(self))
    self.actionFind_events.triggered.connect(lambda: event_operations.find_events(self))
    self.actionFind_replace_events.triggered.connect(lambda: event_operations.find_replace_events(self))
    self.actionDelete_all_events.triggered.connect(lambda: event_operations.delete_all_events(self))
    self.actionDelete_selected_events.triggered.connect(lambda: event_operations.delete_selected_events(self))

    self.actionMedia_file_information.triggered.connect(lambda: media_file.get_info(self))

    self.actionLoad_observations_file.triggered.connect(lambda: import_observations.import_observations(self))

    self.actionExportEvents_2.triggered.connect(lambda: export_events.export_tabular_events(self, mode="tabular"))

    # behavioral sequences
    # self.actionExportEventString.triggered.connect(lambda: self.export_events_as_behavioral_sequences(timed=False))
    self.actionseparated_subjects.triggered.connect(
        lambda: export_events.export_events_as_behavioral_sequences(self, separated_subjects=True, timed=False)
    )
    self.actiongrouped_subjects.triggered.connect(
        lambda: export_events.export_events_as_behavioral_sequences(self, separated_subjects=False, timed=False)
    )

    self.actionExport_aggregated_events.triggered.connect(lambda: export_events.export_aggregated_events(self))
    self.actionExport_events_as_Praat_TextGrid.triggered.connect(lambda: export_events.export_events_as_textgrid(self))
    self.actionJWatcher.triggered.connect(lambda: export_events.export_tabular_events(self, "jwatcher"))

    self.actionExtract_events_from_media_files.triggered.connect(lambda: events_snapshots.extract_events(self))
    self.actionExtract_frames_from_media_files.triggered.connect(lambda: events_snapshots.events_snapshots(self))

    self.actionCohen_s_kappa.triggered.connect(lambda: irr.irr_cohen_kappa(self))
    self.actionNeedleman_Wunsch.triggered.connect(lambda: irr.needleman_wunch(self))

    self.actionAll_transitions.triggered.connect(lambda: transitions.transitions_matrix(self, "frequency"))
    self.actionNumber_of_transitions.triggered.connect(lambda: transitions.transitions_matrix(self, "number"))

    self.actionFrequencies_of_transitions_after_behaviors.triggered.connect(
        lambda: transitions.transitions_matrix(self, "frequencies_after_behaviors")
    )

    # menu playback
    self.actionJumpTo.triggered.connect(self.jump_to)
    self.action_deinterlace.triggered.connect(lambda: video_operations.deinterlace(self))
    self.actionZoom_level.triggered.connect(lambda: video_operations.zoom_level(self))
    self.actionRotate_current_video.triggered.connect(lambda: video_operations.rotate_displayed_video(self))
    self.actionDisplay_subtitles.triggered.connect(lambda: video_operations.display_subtitles(self))
    self.actionVideo_equalizer.triggered.connect(lambda: video_equalizer.video_equalizer_show(self))

    # menu Tools
    self.action_block_dockwidgets.triggered.connect(self.block_dockwidgets)

    self.action_create_modifiers_coding_map.triggered.connect(self.modifiers_coding_map_creator)
    self.action_create_behaviors_coding_map.triggered.connect(lambda: behav_coding_map_creator.behaviors_coding_map_creator(self))

    self.actionShow_spectrogram.triggered.connect(lambda: self.show_plot_widget("spectrogram", warning=True))
    self.actionShow_the_sound_waveform.triggered.connect(lambda: self.show_plot_widget("waveform", warning=True))
    self.actionPlot_events_in_real_time.triggered.connect(lambda: self.show_plot_widget("plot_events", warning=False))

    self.actionShow_data_files.triggered.connect(self.show_data_files)
    self.action_geometric_measurements.triggered.connect(lambda: geometric_measurement.show_widget(self))

    self.actionBehaviors_coding_map.triggered.connect(lambda: behaviors_coding_map.show_behaviors_coding_map(self))

    self.actionCoding_pad.triggered.connect(lambda: coding_pad.show_coding_pad(self))
    self.actionSubjects_pad.triggered.connect(self.show_subjects_pad)

    # image overlay on video
    self.actionAdd_image_overlay_on_video.triggered.connect(lambda: image_overlay.add_image_overlay(self))
    self.actionRemove_image_overlay.triggered.connect(lambda: image_overlay.remove_image_overlay(self))

    self.actionRecode_resize_video.triggered.connect(lambda: external_processes.ffmpeg_process(self, "reencode_resize"))
    self.actionRotate_video.triggered.connect(lambda: external_processes.ffmpeg_process(self, "rotate"))
    self.actionMerge_media_files.triggered.connect(lambda: external_processes.ffmpeg_process(self, "merge"))
    self.actionMedia_file_information_2.triggered.connect(lambda: media_file.get_info(self))

    self.actionCreate_transitions_flow_diagram.triggered.connect(transitions.transitions_dot_script)
    self.actionCreate_transitions_flow_diagram_2.triggered.connect(transitions.transitions_flow_diagram)

    # menu Analysis

    self.actionTime_budget.triggered.connect(lambda: time_budget_widget.time_budget(self, mode="by_behavior"))
    self.actionTime_budget_by_behaviors_category.triggered.connect(lambda: time_budget_widget.time_budget(self, mode="by_category"))

    self.actionTime_budget_report.triggered.connect(lambda: synthetic_time_budget.synthetic_time_budget(self))
    self.actionSynthetic_binned_time_budget.triggered.connect(lambda: synthetic_time_budget.synthetic_binned_time_budget(self))

    self.actionBehavior_bar_plot.triggered.connect(lambda: self.behaviors_bar_plot(mode="list"))
    self.actionBehavior_bar_plot.setVisible(True)

    self.actionPlot_events1.setVisible(False)
    self.actionPlot_events2.triggered.connect(lambda: self.plot_events_triggered(mode="list"))

    self.action_behavior_binary_table.triggered.connect(lambda: behavior_binary_table.behavior_binary_table(self))

    self.action_advanced_event_filtering.triggered.connect(self.advanced_event_filtering)

    self.action_latency.triggered.connect(lambda: latency.get_latency(self))

    self.action_cooccurence.triggered.connect(lambda: cooccurence.get_cooccurence(self))

    # menu Help
    self.actionUser_guide.triggered.connect(self.actionUser_guide_triggered)
    self.actionAbout.triggered.connect(lambda: about.actionAbout_activated(self))
    self.actionCheckUpdate.triggered.connect(self.actionCheckUpdate_activated)

    # toolbar
    self.action_obs_list.triggered.connect(lambda: observation_operations.observations_list(self))
    self.actionPlay.triggered.connect(self.play_activated)
    self.actionReset.triggered.connect(self.reset_activated)
    self.actionJumpBackward.triggered.connect(self.jumpBackward_activated)
    self.actionJumpForward.triggered.connect(self.jumpForward_activated)

    self.actionFaster.triggered.connect(lambda: video_operations.video_faster_activated(self))
    self.actionSlower.triggered.connect(lambda: video_operations.video_slower_activated(self))
    self.actionNormalSpeed.triggered.connect(lambda: video_operations.video_normalspeed_activated(self))

    self.actionPrevious.triggered.connect(self.previous_media_file)
    self.actionNext.triggered.connect(self.next_media_file)

    self.actionSnapshot.triggered.connect(lambda: video_operations.snapshot(self))

    self.actionFrame_backward.triggered.connect(self.previous_frame)
    self.actionFrame_forward.triggered.connect(self.next_frame)

    self.actionCloseObs.triggered.connect(lambda: observation_operations.close_observation(self))
    self.actionCurrent_Time_Budget.triggered.connect(lambda: time_budget_widget.time_budget(self, mode="by_behavior", mode2="current"))
    self.actionPlot_current_observation.triggered.connect(lambda: self.plot_events_triggered(mode="current"))

    self.actionPlot_current_time_budget.triggered.connect(lambda: self.behaviors_bar_plot(mode="current"))

    self.actionFind_in_current_obs.triggered.connect(lambda: event_operations.find_events(self))

    # table Widget double click
    # self.twEvents.itemDoubleClicked.connect(self.twEvents_doubleClicked)
    self.twEthogram.itemDoubleClicked.connect(self.twEthogram_doubleClicked)
    self.twSubjects.itemDoubleClicked.connect(self.twSubjects_doubleClicked)

    # events tableview
    self.tv_events.doubleClicked.connect(self.tv_events_doubleClicked)

    # Actions for twEthogram context menu
    self.twEthogram.setContextMenuPolicy(Qt.ActionsContextMenu)
    self.twEthogram.horizontalHeader().sortIndicatorChanged.connect(self.twEthogram_sorted)

    self.actionViewBehavior.triggered.connect(self.view_behavior)
    self.twEthogram.addAction(self.actionViewBehavior)

    self.actionFilterBehaviors.triggered.connect(
        lambda: self.filter_behaviors(table=cfg.ETHOGRAM, behavior_type=cfg.STATE_EVENT_TYPES + cfg.POINT_EVENT_TYPES)
    )
    self.twEthogram.addAction(self.actionFilterBehaviors)

    self.actionShowAllBehaviors.triggered.connect(self.show_all_behaviors)
    self.twEthogram.addAction(self.actionShowAllBehaviors)

    # Actions for twSubjects context menu
    self.twSubjects.setContextMenuPolicy(Qt.ActionsContextMenu)
    self.twSubjects.horizontalHeader().sortIndicatorChanged.connect(self.sort_twSubjects)
    self.actionFilterSubjects.triggered.connect(self.filter_subjects)
    self.twSubjects.addAction(self.actionFilterSubjects)

    self.actionShowAllSubjects.triggered.connect(self.show_all_subjects)
    self.twSubjects.addAction(self.actionShowAllSubjects)

    # actions for twEvents horizontal header menu
    # tw_headers = self.twEvents.horizontalHeader()
    # tw_headers.setContextMenuPolicy(Qt.ActionsContextMenu)
    # tw_headers.addAction(self.actionConfigure_twEvents_columns)

    tv_headers = self.tv_events.horizontalHeader()
    tv_headers.setContextMenuPolicy(Qt.ActionsContextMenu)
    tv_headers.addAction(self.actionConfigure_tvevents_columns)

    # Actions for twEvents menu
    # self.twEvents.setContextMenuPolicy(Qt.ActionsContextMenu)

    # self.twEvents.addAction(self.actionAdd_event)
    # self.twEvents.addAction(self.actionEdit_selected_events)
    # self.twEvents.addAction(self.actionEdit_event_time)

    # self.twEvents.addAction(self.actionCopy_events)
    # self.twEvents.addAction(self.actionPaste_events)

    # separator2 = QAction(self)
    # separator2.setSeparator(True)
    # self.twEvents.addAction(separator2)

    # self.twEvents.addAction(self.actionFind_events)
    # self.twEvents.addAction(self.actionFind_replace_events)

    # separator2 = QAction(self)
    # separator2.setSeparator(True)
    # self.twEvents.addAction(separator2)

    # self.twEvents.addAction(self.actionFilter_events)
    # self.twEvents.addAction(self.actionShow_all_events)

    # separator2 = QAction(self)
    # separator2.setSeparator(True)
    # self.twEvents.addAction(separator2)

    # self.twEvents.addAction(self.actionCheckStateEventsSingleObs)
    # self.twEvents.addAction(self.actionClose_unpaired_events)

    # self.twEvents.addAction(self.actionRunEventOutside)

    # separator2 = QAction(self)
    # separator2.setSeparator(True)
    # self.twEvents.addAction(separator2)

    # self.twEvents.addAction(self.actionDelete_selected_events)

    # Actions for tv_events menu
    self.tv_events.setContextMenuPolicy(Qt.ActionsContextMenu)

    self.tv_events.addAction(self.actionAdd_event)
    self.tv_events.addAction(self.actionEdit_selected_events)
    self.tv_events.addAction(self.actionEdit_event_time)

    self.tv_events.addAction(self.actionCopy_events)
    self.tv_events.addAction(self.actionPaste_events)

    separator2 = QAction(self)
    separator2.setSeparator(True)
    self.tv_events.addAction(separator2)

    self.tv_events.addAction(self.actionFind_events)
    self.tv_events.addAction(self.actionFind_replace_events)

    separator2 = QAction(self)
    separator2.setSeparator(True)
    self.tv_events.addAction(separator2)

    self.tv_events.addAction(self.actionFilter_events)
    self.tv_events.addAction(self.actionShow_all_events)

    separator2 = QAction(self)
    separator2.setSeparator(True)
    self.tv_events.addAction(separator2)

    self.tv_events.addAction(self.actionCheckStateEventsSingleObs)
    self.tv_events.addAction(self.actionClose_unpaired_events)

    self.tv_events.addAction(self.actionAdd_frame_indexes)

    self.tv_events.addAction(self.actionRunEventOutside)

    separator2 = QAction(self)
    separator2.setSeparator(True)
    self.tv_events.addAction(separator2)

    self.tv_events.addAction(self.actionDelete_selected_events)

    # Actions for twSubjects context menu
    self.actionDeselectCurrentSubject.triggered.connect(lambda: self.update_subject(""))

    self.twSubjects.setContextMenuPolicy(Qt.ActionsContextMenu)
    self.twSubjects.addAction(self.actionDeselectCurrentSubject)

    # subjects

    # timer for plot visualization
    self.plot_timer = QTimer(self)
    # TODO check value of interval
    self.plot_timer.setInterval(cfg.SPECTRO_TIMER)
    self.plot_timer.timeout.connect(self.plot_timer_out)

    # timer for timing the live observation
    self.liveTimer = QTimer(self)
    self.liveTimer.timeout.connect(self.liveTimer_out)

    # timer for automatic backup
    self.automaticBackupTimer = QTimer(self)
    self.automaticBackupTimer.timeout.connect(self.automatic_backup)
    if self.automaticBackup:
        self.automaticBackupTimer.start(self.automaticBackup * 60000)

    self.pb_live_obs.clicked.connect(self.start_live_observation)
