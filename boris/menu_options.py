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


import logging
from . import config as cfg


def update_menu(self):
    """
    enable/disable menu option
    """
    logging.debug("function: menu_options")

    flag = self.project

    if not self.project:
        pn = ""
    else:
        if self.pj["project_name"]:
            pn = self.pj["project_name"]
        else:
            if self.projectFileName:
                pn = f"Unnamed project ({self.projectFileName})"
            else:
                pn = "Unnamed project"

    self.setWindowTitle(
        "{}{}{}".format(
            self.observationId + " - " * (self.observationId != ""), pn + (" - " * (pn != "")), cfg.programName
        )
    )

    # enabled if project loaded
    for action in (
        self.actionEdit_project,
        self.actionSave_project,
        self.actionSave_project_as,
        self.actionCheck_project,
        self.actionClose_project,
        self.actionSend_project,
        self.actionNew_observation,
        self.actionRemove_path_from_media_files,
        self.action_obs_list,
        self.actionExport_observations_list,
        self.actionExplore_project,
        self.menuExport_events,
        self.actionLoad_observations_file,
        self.actionExportEvents_2,
        self.actionExport_aggregated_events,
    ):
        action.setEnabled(flag)

    # observations

    # enabled if project contain one or more observations
    for w in [
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
    ]:
        w.setEnabled(self.pj[cfg.OBSERVATIONS] != {})

    # enabled if current observation
    flagObs = self.observationId != ""
    for action in (
        self.actionAdd_event,
        self.actionClose_observation,
        self.actionDelete_all_observations,
        self.actionSelect_observations,
        self.actionDelete_selected_observations,
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
    ):
        action.setEnabled(self.observationId != "")

    # self.actionExportEventString.setEnabled(flag)
    self.menuas_behavioural_sequences.setEnabled(flag)
    self.actionExport_events_as_Praat_TextGrid.setEnabled(flag)
    self.actionJWatcher.setEnabled(flag)

    self.actionCheckStateEvents.setEnabled(flag)
    self.actionCheckStateEventsSingleObs.setEnabled(flag)
    self.actionClose_unpaired_events.setEnabled(flag)
    self.actionRunEventOutside.setEnabled(flag)

    # enabled if media observation
    for action in (
        self.actionMedia_file_information,
        self.actionJumpForward,
        self.actionJumpBackward,
        self.actionJumpTo,
        self.actionZoom_level,
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
    ):

        action.setEnabled(self.playerType == cfg.MEDIA)

    # Tools
    self.actionShow_spectrogram.setEnabled(self.playerType == cfg.MEDIA)
    self.actionShow_the_sound_waveform.setEnabled(self.playerType == cfg.MEDIA)
    self.actionPlot_events_in_real_time.setEnabled(flagObs)

    self.actionShow_data_files.setEnabled(self.playerType == cfg.MEDIA)
    self.menuImage_overlay_on_video_2.setEnabled(self.playerType == cfg.MEDIA)

    self.actionAdd_image_overlay_on_video.setEnabled(self.playerType == cfg.MEDIA)
    self.actionRemove_image_overlay.setEnabled(self.playerType == cfg.MEDIA)

    # geometric measurements
    self.action_geometric_measurements.setEnabled(flagObs and self.geometric_measurements_mode == False)
    self.actionCoding_pad.setEnabled(flagObs)
    self.actionSubjects_pad.setEnabled(flagObs)
    self.actionBehaviors_coding_map.setEnabled(flagObs)

    # Analysis
    for w in [
        self.actionTime_budget,
        self.actionTime_budget_by_behaviors_category,
        self.actionTime_budget_report,
        self.action_behavior_binary_table,
        self.action_advanced_event_filtering,
        self.action_latency,
        self.menuPlot_events,
        self.menuInter_rater_reliability,
        self.menuSimilarities,
        self.menuCreate_transitions_matrix,
        self.actionSynthetic_binned_time_budget,
    ]:
        w.setEnabled(self.pj[cfg.OBSERVATIONS] != {})

    # statusbar labels
    for w in [self.lbTimeOffset, self.lbSpeed, self.lb_obs_time_interval]:
        w.setVisible(self.playerType == cfg.MEDIA)

    logging.debug("function: menu_options finished")
