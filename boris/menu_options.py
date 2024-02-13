"""
BORIS
Behavioral Observation Research Interactive Software
Copyright 2012-2024 Olivier Friard

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


import logging
from . import config as cfg
from PyQt5.QtCore import QSize


def update_windows_title(self):
    """
    update the main window title
    """

    if not self.project:
        project_name = ""
    else:
        if self.pj[cfg.PROJECT_NAME]:
            project_name = self.pj[cfg.PROJECT_NAME]
        else:
            if self.projectFileName:
                project_name = f"Unnamed project ({self.projectFileName})"
            else:
                project_name = "Unnamed project"

    self.setWindowTitle(
        f"{self.observationId + ' - ' * (self.observationId != '')}{project_name}{'*' * self.projectChanged}{(' - ' * (project_name != ''))}{cfg.programName}"
    )


def update_menu(self):
    """
    enable/disable menu option
    """
    logging.debug("function: menu_options")

    project_opened = self.project
    observation_is_active = self.observationId != ""
    project_contains_obs = self.pj[cfg.OBSERVATIONS] != {}

    update_windows_title(self)

    self.toolBar.setIconSize(
        QSize(
            self.config_param.get(cfg.TOOLBAR_ICON_SIZE, cfg.DEFAULT_TOOLBAR_ICON_SIZE_VALUE),
            self.config_param.get(cfg.TOOLBAR_ICON_SIZE, cfg.DEFAULT_TOOLBAR_ICON_SIZE_VALUE),
        )
    )

    # enabled if project loaded
    for action in (
        self.actionEdit_project,
        self.actionSave_project,
        self.actionSave_project_as,
        self.actionExport_project,
        self.actionCheck_project,
        self.actionClose_project,
        self.actionSend_project,
        self.actionNew_observation,
        self.actionRemove_path_from_media_files,
        self.action_create_observations,
        self.action_obs_list,
        self.actionExport_observations_list,
        self.actionExplore_project,
        self.menuExport_events,
        self.actionLoad_observations_file,
        self.actionExportEvents_2,
        self.actionExport_aggregated_events,
        self.menuas_behavioural_sequences,
        self.actionExport_events_as_Praat_TextGrid,
        self.actionJWatcher,
        self.actionCheckStateEvents,
        self.actionCheckStateEventsSingleObs,
        self.actionClose_unpaired_events,
        self.actionRunEventOutside,
    ):
        action.setEnabled(project_opened)

    # observations

    # enabled if project contain one or more observations
    for w in (
        self.actionOpen_observation,
        self.actionEdit_observation_2,
        self.actionView_observation,
        self.actionObservationsList,
        self.action_obs_list,
        self.actionExport_observations_list,
        self.actionCheckStateEvents,
        self.actionExplore_project,
        self.actionClose_unpaired_events,
        self.menuExport_events,
        self.menuCreate_subtitles_2,
        self.actionExtract_events_from_media_files,
        self.actionExtract_frames_from_media_files,
        self.actionRemove_observations,
        self.menuMedia_file_Images_directories,
        # self.actionSet_paths_relative_to_project_directory,
    ):
        w.setEnabled(project_contains_obs)

    # enabled if current observation
    for action in (
        self.actionAdd_event,
        self.actionClose_observation,
        self.actionDelete_all_events,
        self.actionSelect_observations,
        self.actionDelete_selected_events,
        self.actionEdit_event,
        self.actionEdit_event_time,
        self.actionCopy_events,
        self.actionPaste_events,
        self.actionFind_events,
        self.actionFind_replace_events,
        self.actionCloseObs,
        self.actionCurrent_Time_Budget,
        self.actionPlot_current_observation,
        self.actionFind_in_current_obs,
        self.actionEdit_selected_events,
        self.actionPlot_current_time_budget,
    ):
        action.setEnabled(observation_is_active)

    # enabled if media observation
    for action in (
        self.actionMedia_file_information,
        self.actionJumpForward,
        self.actionJumpBackward,
        self.actionJumpTo,
        self.actionZoom_level,
        self.actionRotate_current_video,
        self.actionDisplay_subtitles,
        self.actionPlay,
        self.actionReset,
        self.actionFaster,
        self.actionSlower,
        self.actionNormalSpeed,
        self.actionPrevious,
        self.actionNext,
        self.actionSnapshot,
        self.actionFrame_backward,
        self.actionFrame_forward,
        self.actionVideo_equalizer,
        self.actionShow_spectrogram,
        self.actionShow_the_sound_waveform,
        self.actionPlot_events_in_real_time,
        self.actionShow_data_files,
        self.menuImage_overlay_on_video_2,
        self.actionAdd_image_overlay_on_video,
        self.actionRemove_image_overlay,
        self.actionAdd_frame_indexes,
    ):
        action.setEnabled(self.playerType == cfg.MEDIA)

    # geometric measurements
    self.action_geometric_measurements.setEnabled(observation_is_active and self.geometric_measurements_mode is False)
    self.actionCoding_pad.setEnabled(observation_is_active)
    self.actionSubjects_pad.setEnabled(observation_is_active)
    self.actionBehaviors_coding_map.setEnabled(observation_is_active)

    for action in (
        self.actionJumpForward,
        self.actionJumpBackward,
        self.actionJumpTo,
        self.actionReset,
        self.actionPrevious,
        self.actionNext,
        self.actionSnapshot,
        self.actionFrame_backward,
        self.actionFrame_forward,
    ):
        action.setEnabled(self.playerType in [cfg.MEDIA, cfg.IMAGES])

    # Analysis
    for w in [
        self.actionTime_budget,
        self.actionTime_budget_by_behaviors_category,
        self.actionTime_budget_report,
        self.action_behavior_binary_table,
        self.action_advanced_event_filtering,
        self.action_latency,
        self.action_cooccurence,
        self.menuPlot_events,
        self.menuInter_rater_reliability,
        self.menuSimilarities,
        self.menuCreate_transitions_matrix,
        self.actionSynthetic_binned_time_budget,
    ]:
        w.setEnabled(project_contains_obs)

    # statusbar labels
    for w in (self.lbTimeOffset, self.lb_obs_time_interval):
        w.setVisible(self.playerType == cfg.MEDIA)

    logging.debug("function: menu_options finished")
