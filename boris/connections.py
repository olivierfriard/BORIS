"""
BORIS
Behavioral Observation Research Interactive Software
Copyright 2012-2022 Olivier Friard

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


from PyQt5.QtWidgets import QAction
from PyQt5.QtCore import QTimer, Qt
from . import config as cfg
from . import video_equalizer
from . import behavior_binary_table
from . import transitions
from . import import_observations
from . import irr
from . import project_server
from . import events_snapshots


def connections(self):
    """
    create connections between widgets and functions
    """

    # menu file
    self.actionNew_project.triggered.connect(self.new_project_activated)
    self.actionOpen_project.triggered.connect(self.open_project_activated)
    self.actionNoldus_Observer_template.triggered.connect(self.import_project_from_observer_template)
    self.actionEdit_project.triggered.connect(self.edit_project_activated)
    self.actionCheck_project.triggered.connect(self.check_project_integrity)
    self.actionSave_project.triggered.connect(self.save_project_activated)
    self.actionSave_project_as.triggered.connect(self.save_project_as_activated)
    self.actionClose_project.triggered.connect(self.close_project)

    self.actionRemove_path_from_media_files.triggered.connect(self.remove_media_files_path)
    self.actionSend_project.triggered.connect(lambda: project_server.send_project_via_socket(self))

    self.menuCreate_subtitles_2.triggered.connect(self.create_subtitles)

    self.actionPreferences.triggered.connect(self.preferences)

    self.actionQuit.triggered.connect(self.actionQuit_activated)

    # menu observations
    self.actionNew_observation.triggered.connect(self.new_observation_triggered)
    self.actionOpen_observation.triggered.connect(lambda: self.open_observation("start"))
    self.actionView_observation.triggered.connect(lambda: self.open_observation(cfg.VIEW))
    self.actionEdit_observation_2.triggered.connect(self.edit_observation)
    self.actionObservationsList.triggered.connect(self.observations_list)

    self.actionClose_observation.triggered.connect(self.close_observation)

    self.actionAdd_event.triggered.connect(self.add_event)
    self.actionEdit_event.triggered.connect(self.edit_event)
    self.actionFilter_events.triggered.connect(self.filter_events)
    self.actionShow_all_events.triggered.connect(self.show_all_events)

    self.actionExport_observations_list.triggered.connect(self.export_observations_list_clicked)

    self.actionCheckStateEvents.triggered.connect(lambda: self.check_state_events("all"))
    self.actionCheckStateEventsSingleObs.triggered.connect(lambda: self.check_state_events("current"))
    self.actionClose_unpaired_events.triggered.connect(self.fix_unpaired_events)
    self.actionRunEventOutside.triggered.connect(self.run_event_outside)

    self.actionSelect_observations.triggered.connect(self.select_events_between_activated)

    self.actionEdit_selected_events.triggered.connect(self.edit_selected_events)
    self.actionEdit_event_time.triggered.connect(self.edit_time_selected_events)

    self.actionCopy_events.triggered.connect(self.copy_selected_events)
    self.actionPaste_events.triggered.connect(self.paste_clipboard_to_events)

    self.actionExplore_project.triggered.connect(self.explore_project)
    self.actionFind_events.triggered.connect(self.find_events)
    self.actionFind_replace_events.triggered.connect(self.find_replace_events)
    self.actionDelete_all_observations.triggered.connect(self.delete_all_events)
    self.actionDelete_selected_observations.triggered.connect(self.delete_selected_events)

    self.actionMedia_file_information.triggered.connect(self.media_file_info)

    self.actionLoad_observations_file.triggered.connect(lambda: import_observations.import_observations(self))

    self.actionExportEvents_2.triggered.connect(lambda: self.export_tabular_events("tabular"))

    # behavioral sequences
    # self.actionExportEventString.triggered.connect(lambda: self.export_events_as_behavioral_sequences(timed=False))
    self.actionseparated_subjects.triggered.connect(
        lambda: self.export_events_as_behavioral_sequences(separated_subjects=True, timed=False)
    )
    self.actiongrouped_subjects.triggered.connect(
        lambda: self.export_events_as_behavioral_sequences(separated_subjects=False, timed=False)
    )

    self.actionExport_aggregated_events.triggered.connect(self.export_aggregated_events)
    self.actionExport_events_as_Praat_TextGrid.triggered.connect(self.export_state_events_as_textgrid)
    self.actionJWatcher.triggered.connect(lambda: self.export_tabular_events("jwatcher"))

    self.actionExtract_events_from_media_files.triggered.connect(lambda: events_snapshots.extract_events(self))
    self.actionExtract_frames_from_media_files.triggered.connect(lambda: events_snapshots.events_snapshots(self))

    self.actionCohen_s_kappa.triggered.connect(lambda: irr.irr_cohen_kappa(self))
    self.actionNeedleman_Wunsch.triggered.connect(lambda: irr.needleman_wunch(self))

    self.actionAll_transitions.triggered.connect(lambda: transitions.transitions_matrix(self, "frequency"))
    self.actionNumber_of_transitions.triggered.connect(lambda: transitions.transitions_matrix(self, "number"))

    self.actionFrequencies_of_transitions_after_behaviors.triggered.connect(
        lambda: self.transitions_matrix("frequencies_after_behaviors")
    )

    # menu playback
    self.actionJumpTo.triggered.connect(self.jump_to)
    self.actionZoom_level.triggered.connect(self.zoom_level)
    self.actionDisplay_subtitles.triggered.connect(self.display_subtitles)
    self.actionVideo_equalizer.triggered.connect(lambda: video_equalizer.video_equalizer_show(self))

    # menu Tools
    self.action_block_dockwidgets.triggered.connect(self.block_dockwidgets)

    self.action_create_modifiers_coding_map.triggered.connect(self.modifiers_coding_map_creator)
    self.action_create_behaviors_coding_map.triggered.connect(self.behaviors_coding_map_creator)

    self.actionShow_spectrogram.triggered.connect(lambda: self.show_plot_widget("spectrogram", warning=True))
    self.actionShow_the_sound_waveform.triggered.connect(lambda: self.show_plot_widget("waveform", warning=True))
    self.actionPlot_events_in_real_time.triggered.connect(lambda: self.show_plot_widget("plot_events", warning=False))

    self.actionShow_data_files.triggered.connect(self.show_data_files)
    self.action_geometric_measurements.triggered.connect(self.geometric_measurements)
    self.actionBehaviors_coding_map.triggered.connect(self.show_behaviors_coding_map)

    self.actionCoding_pad.triggered.connect(self.show_coding_pad)
    self.actionSubjects_pad.triggered.connect(self.show_subjects_pad)

    # image overlay on video
    self.actionAdd_image_overlay_on_video.triggered.connect(self.add_image_overlay)
    self.actionRemove_image_overlay.triggered.connect(self.remove_image_overlay)

    self.actionRecode_resize_video.triggered.connect(lambda: self.ffmpeg_process("reencode_resize"))
    self.actionRotate_video.triggered.connect(lambda: self.ffmpeg_process("rotate"))
    self.actionMedia_file_information_2.triggered.connect(self.media_file_info)

    self.actionCreate_transitions_flow_diagram.triggered.connect(transitions.transitions_dot_script)
    self.actionCreate_transitions_flow_diagram_2.triggered.connect(transitions.transitions_flow_diagram)

    # menu Analysis
    self.actionTime_budget.triggered.connect(lambda: self.time_budget(mode="by_behavior"))
    self.actionTime_budget_by_behaviors_category.triggered.connect(lambda: self.time_budget(mode="by_category"))

    self.actionTime_budget_report.triggered.connect(self.synthetic_time_budget)
    self.actionSynthetic_binned_time_budget.triggered.connect(self.synthetic_binned_time_budget)

    self.actionBehavior_bar_plot.triggered.connect(self.behaviors_bar_plot)
    self.actionBehavior_bar_plot.setVisible(True)

    self.actionPlot_events1.setVisible(False)
    self.actionPlot_events2.triggered.connect(lambda: self.plot_events_triggered(mode="list"))

    self.action_behavior_binary_table.triggered.connect(lambda: behavior_binary_table.behavior_binary_table(self.pj))

    self.action_advanced_event_filtering.triggered.connect(self.advanced_event_filtering)

    # menu Help
    self.actionUser_guide.triggered.connect(self.actionUser_guide_triggered)
    self.actionAbout.triggered.connect(self.actionAbout_activated)
    self.actionCheckUpdate.triggered.connect(self.actionCheckUpdate_activated)

    # toolbar
    self.action_obs_list.triggered.connect(self.observations_list)
    self.actionPlay.triggered.connect(self.play_activated)
    self.actionReset.triggered.connect(self.reset_activated)
    self.actionJumpBackward.triggered.connect(self.jumpBackward_activated)
    self.actionJumpForward.triggered.connect(self.jumpForward_activated)

    self.actionFaster.triggered.connect(self.video_faster_activated)
    self.actionSlower.triggered.connect(self.video_slower_activated)
    self.actionNormalSpeed.triggered.connect(self.video_normalspeed_activated)

    self.actionCloseObs.triggered.connect(self.close_observation)
    self.actionCurrent_Time_Budget.triggered.connect(lambda: self.time_budget(mode="by_behavior", mode2="current"))
    self.actionPlot_current_observation.triggered.connect(lambda: self.plot_events_triggered(mode="current"))
    self.actionFind_in_current_obs.triggered.connect(self.find_events)

    # table Widget double click
    self.twEvents.itemDoubleClicked.connect(self.twEvents_doubleClicked)
    self.twEthogram.itemDoubleClicked.connect(self.twEthogram_doubleClicked)
    self.twSubjects.itemDoubleClicked.connect(self.twSubjects_doubleClicked)

    # Actions for twEthogram context menu
    self.twEthogram.setContextMenuPolicy(Qt.ActionsContextMenu)
    self.twEthogram.horizontalHeader().sortIndicatorChanged.connect(self.twEthogram_sorted)

    self.actionViewBehavior.triggered.connect(self.view_behavior)
    self.twEthogram.addAction(self.actionViewBehavior)

    self.actionFilterBehaviors.triggered.connect(lambda: self.filter_behaviors(table=cfg.ETHOGRAM))
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

    # Actions for twEvents menu
    self.twEvents.setContextMenuPolicy(Qt.ActionsContextMenu)

    self.twEvents.addAction(self.actionAdd_event)
    self.twEvents.addAction(self.actionEdit_selected_events)
    self.twEvents.addAction(self.actionEdit_event_time)

    self.twEvents.addAction(self.actionCopy_events)
    self.twEvents.addAction(self.actionPaste_events)

    separator2 = QAction(self)
    separator2.setSeparator(True)
    self.twEvents.addAction(separator2)

    self.twEvents.addAction(self.actionFind_events)
    self.twEvents.addAction(self.actionFind_replace_events)

    separator2 = QAction(self)
    separator2.setSeparator(True)
    self.twEvents.addAction(separator2)

    self.twEvents.addAction(self.actionFilter_events)
    self.twEvents.addAction(self.actionShow_all_events)

    separator2 = QAction(self)
    separator2.setSeparator(True)
    self.twEvents.addAction(separator2)

    self.twEvents.addAction(self.actionCheckStateEventsSingleObs)
    self.twEvents.addAction(self.actionClose_unpaired_events)

    self.twEvents.addAction(self.actionRunEventOutside)

    separator2 = QAction(self)
    separator2.setSeparator(True)
    self.twEvents.addAction(separator2)

    self.twEvents.addAction(self.actionDelete_selected_observations)
    self.twEvents.addAction(self.actionDelete_all_observations)

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
