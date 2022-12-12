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
import os
import pathlib
import subprocess
from decimal import Decimal as dec

from PyQt5.QtWidgets import QFileDialog, QInputDialog, QMessageBox

from . import config as cfg
from . import db_functions, dialog, project_functions, select_observations, select_subj_behav
from . import utilities as util


def events_snapshots(self):
    """
    create snapshots corresponding to coded events
    if observations are from media file and media files have video
    """

    _, selected_observations = select_observations.select_observations(
        self.pj, cfg.MULTIPLE, windows_title="Select observations for snapshots"
    )
    if not selected_observations:
        return

    # check if obs are MEDIA
    live_images_obs_list = []
    for obs_id in selected_observations:
        if self.pj[cfg.OBSERVATIONS][obs_id][cfg.TYPE] in [cfg.LIVE, cfg.IMAGES]:
            live_images_obs_list.append(obs_id)

    if live_images_obs_list:
        out = "The following observations are live observations or observation from images and will be removed from analysis<br><br>"
        out += "<br>".join(live_images_obs_list)
        results = dialog.Results_dialog()
        results.setWindowTitle(cfg.programName)
        results.ptText.setReadOnly(True)
        results.ptText.appendHtml(out)
        results.pbSave.setVisible(False)
        results.pbCancel.setVisible(True)
        if not results.exec_():
            return

    # remove live observations
    selected_observations = [x for x in selected_observations if x not in live_images_obs_list]
    if not selected_observations:
        return

    # check if state events are paired
    not_ok, selected_observations = project_functions.check_state_events(self.pj, selected_observations)
    if not_ok or not selected_observations:
        return

    parameters = select_subj_behav.choose_obs_subj_behav_category(
        self,
        selected_observations,
        start_coding=dec("NaN"),
        end_coding=dec("NaN"),
        flagShowIncludeModifiers=False,
        flagShowExcludeBehaviorsWoEvents=False,
        n_observations=len(selected_observations),
    )

    if not parameters[cfg.SELECTED_SUBJECTS] or not parameters[cfg.SELECTED_BEHAVIORS]:
        return

    # Ask for time interval around the event
    while True:
        text, ok = QInputDialog.getDouble(
            self, "Time interval around the events", "Time (in seconds):", 0.0, 0.0, 86400, 1
        )
        if not ok:
            return
        try:
            time_interval = util.float2decimal(text)
            break
        except Exception:
            QMessageBox.warning(self, cfg.programName, f"<b>{text}</b> is not recognized as time")

    # directory for saving frames
    exportDir = QFileDialog().getExistingDirectory(
        self,
        "Choose a directory to extract events",
        os.path.expanduser("~"),
        options=QFileDialog(self).ShowDirsOnly,
    )
    if not exportDir:
        return

    cursor = db_functions.load_events_in_db(
        self.pj,
        parameters[cfg.SELECTED_SUBJECTS],
        selected_observations,
        parameters[cfg.SELECTED_BEHAVIORS],
        time_interval=cfg.TIME_FULL_OBS,
    )

    for obsId in selected_observations:

        for nplayer in self.pj[cfg.OBSERVATIONS][obsId][cfg.FILE]:

            if not self.pj[cfg.OBSERVATIONS][obsId][cfg.FILE][nplayer]:
                continue
            duration1 = []  # in seconds
            for mediaFile in self.pj[cfg.OBSERVATIONS][obsId][cfg.FILE][nplayer]:
                duration1.append(self.pj[cfg.OBSERVATIONS][obsId][cfg.MEDIA_INFO][cfg.LENGTH][mediaFile])

            for subject in parameters[cfg.SELECTED_SUBJECTS]:

                for behavior in parameters[cfg.SELECTED_BEHAVIORS]:

                    cursor.execute(
                        "SELECT occurence FROM events WHERE observation = ? AND subject = ? AND code = ?",
                        (obsId, subject, behavior),
                    )
                    rows = [{"occurence": util.float2decimal(r["occurence"])} for r in cursor.fetchall()]

                    behavior_state = project_functions.event_type(behavior, self.pj[cfg.ETHOGRAM])

                    for idx, row in enumerate(rows):

                        mediaFileIdx = [
                            idx1 for idx1, x in enumerate(duration1) if row["occurence"] >= sum(duration1[0:idx1])
                        ][-1]

                        # check if media has video
                        flag_no_video = False
                        try:
                            flag_no_video = not self.pj[cfg.OBSERVATIONS][obsId][cfg.MEDIA_INFO][cfg.HAS_VIDEO][
                                self.pj[cfg.OBSERVATIONS][obsId][cfg.FILE][nplayer][mediaFileIdx]
                            ]
                        except Exception:
                            flag_no_video = True

                        if flag_no_video:
                            logging.debug(
                                f"Media {self.pj[cfg.OBSERVATIONS][obsId][cfg.FILE][nplayer][mediaFileIdx]} does not have video"
                            )
                            flag_no_video = True
                            response = dialog.MessageDialog(
                                cfg.programName,
                                (
                                    "The following media file does not have video.<br>"
                                    f"{self.pj[cfg.OBSERVATIONS][obsId][cfg.FILE][nplayer][mediaFileIdx]}"
                                ),
                                [cfg.OK, "Abort"],
                            )
                            if response == cfg.OK:
                                continue
                            if response == "Abort":
                                return

                        # check FPS
                        mediafile_fps = 0
                        try:
                            if self.pj[cfg.OBSERVATIONS][obsId][cfg.MEDIA_INFO][cfg.FPS][
                                self.pj[cfg.OBSERVATIONS][obsId][cfg.FILE][nplayer][mediaFileIdx]
                            ]:
                                mediafile_fps = util.float2decimal(
                                    self.pj[cfg.OBSERVATIONS][obsId][cfg.MEDIA_INFO][cfg.FPS][
                                        self.pj[cfg.OBSERVATIONS][obsId][cfg.FILE][nplayer][mediaFileIdx]
                                    ]
                                )
                        except Exception:
                            mediafile_fps = 0

                        if not mediafile_fps:
                            logging.debug(
                                f"FPS not found for {self.pj[cfg.OBSERVATIONS][obsId][cfg.FILE][nplayer][mediaFileIdx]}"
                            )
                            response = dialog.MessageDialog(
                                cfg.programName,
                                (
                                    "The FPS was not found for the following media file:<br>"
                                    f"{self.pj[cfg.OBSERVATIONS][obsId][cfg.FILE][nplayer][mediaFileIdx]}"
                                ),
                                [cfg.OK, "Abort"],
                            )
                            if response == cfg.OK:
                                continue
                            if response == "Abort":
                                return

                        globalStart = (
                            dec("0.000")
                            if row["occurence"] < time_interval
                            else round(row["occurence"] - time_interval, 3)
                        )
                        start = round(
                            row["occurence"]
                            - time_interval
                            - util.float2decimal(sum(duration1[0:mediaFileIdx]))
                            - self.pj[cfg.OBSERVATIONS][obsId][cfg.TIME_OFFSET],
                            3,
                        )
                        if start < time_interval:
                            start = dec("0.000")

                        if cfg.POINT in behavior_state:

                            media_path = project_functions.full_path(
                                self.pj[cfg.OBSERVATIONS][obsId][cfg.FILE][nplayer][mediaFileIdx],
                                self.projectFileName,
                            )

                            vframes = 1 if not time_interval else int(mediafile_fps * time_interval * 2)
                            ffmpeg_command = (
                                f'"{self.ffmpeg_bin}" '
                                f"-ss {start:.3f} "
                                f'-i "{media_path}" '
                                f"-vframes {vframes} "
                                f'"{exportDir}{os.sep}'
                                f"{util.safeFileName(obsId)}"
                                f"_PLAYER{nplayer}"
                                f"_{util.safeFileName(subject)}"
                                f"_{util.safeFileName(behavior)}"
                                f'_{start:.3f}_%08d.{self.frame_bitmap_format.lower()}"'
                            )

                            logging.debug(f"ffmpeg command: {ffmpeg_command}")

                            p = subprocess.Popen(
                                ffmpeg_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True
                            )
                            out, error = p.communicate()

                        if cfg.STATE in behavior_state:
                            if idx % 2 == 0:

                                # check if stop is on same media file
                                if (
                                    mediaFileIdx
                                    != [
                                        idx1
                                        for idx1, x in enumerate(duration1)
                                        if rows[idx + 1]["occurence"] >= sum(duration1[0:idx1])
                                    ][-1]
                                ):
                                    response = dialog.MessageDialog(
                                        cfg.programName,
                                        (
                                            "The event extends on 2 video. "
                                            "At the moment it no possible to extract frames "
                                            "for this type of event.<br>"
                                        ),
                                        [cfg.OK, "Abort"],
                                    )
                                    if response == cfg.OK:
                                        continue
                                    if response == "Abort":
                                        return

                                globalStop = round(rows[idx + 1]["occurence"] + time_interval, 3)

                                stop = round(
                                    rows[idx + 1]["occurence"]
                                    + time_interval
                                    - util.float2decimal(sum(duration1[0:mediaFileIdx]))
                                    - self.pj[cfg.OBSERVATIONS][obsId][cfg.TIME_OFFSET],
                                    3,
                                )

                                # check if start after length of media
                                try:
                                    if (
                                        start
                                        > self.pj[cfg.OBSERVATIONS][obsId][cfg.MEDIA_INFO][cfg.LENGTH][
                                            self.pj[cfg.OBSERVATIONS][obsId][cfg.FILE][nplayer][mediaFileIdx]
                                        ]
                                    ):
                                        continue
                                except Exception:
                                    continue

                                media_path = project_functions.full_path(
                                    self.pj[cfg.OBSERVATIONS][obsId][cfg.FILE][nplayer][mediaFileIdx],
                                    self.projectFileName,
                                )

                                extension = "png"
                                vframes = int((stop - start) * mediafile_fps + time_interval * mediafile_fps * 2)
                                ffmpeg_command = (
                                    f'"{self.ffmpeg_bin}" -ss {start:.3f} '
                                    f'-i "{media_path}" '
                                    f"-vframes {vframes} "
                                    f'"{exportDir}{os.sep}'
                                    f"{util.safeFileName(obsId)}"
                                    f"_PLAYER{nplayer}"
                                    f"_{util.safeFileName(subject)}"
                                    f"_{util.safeFileName(behavior)}"
                                    f'_{start:.3f}_%08d.{self.frame_bitmap_format.lower()}"'
                                )

                                logging.debug(f"ffmpeg command: {ffmpeg_command}")

                                p = subprocess.Popen(
                                    ffmpeg_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True
                                )
                                out, _ = p.communicate()


def extract_events(self):
    """
    extract sub-sequences from media files corresponding to coded events with FFmpeg
    in case of point event, from -n to +n seconds are extracted (n is asked to user)
    """

    _, selected_observations = select_observations.select_observations(
        self.pj, cfg.MULTIPLE, windows_title="Select observations for extracting events"
    )
    if not selected_observations:
        return

    # check if obs are MEDIA
    live_images_obs_list = []
    for obs_id in selected_observations:
        if self.pj[cfg.OBSERVATIONS][obs_id][cfg.TYPE] in [cfg.LIVE, cfg.IMAGES]:
            live_images_obs_list.append(obs_id)

    if live_images_obs_list:
        out = "The following observations are live observations or observation from images and will be removed from analysis<br><br>"
        out += "<br>".join(live_images_obs_list)
        results = dialog.Results_dialog()
        results.setWindowTitle(cfg.programName)
        results.ptText.setReadOnly(True)
        results.ptText.appendHtml(out)
        results.pbSave.setVisible(False)
        results.pbCancel.setVisible(True)
        if results.exec_():
            # remove live observations
            selected_observations = [x for x in selected_observations if x not in live_images_obs_list]
            if not selected_observations:
                return
        else:
            return

    # check if state events are paired
    not_ok, selected_observations = project_functions.check_state_events(self.pj, selected_observations)
    if not_ok or not selected_observations:
        return

    parameters = select_subj_behav.choose_obs_subj_behav_category(
        self,
        selected_observations,
        start_coding=dec("NaN"),
        end_coding=dec("NaN"),
        flagShowIncludeModifiers=False,
        flagShowExcludeBehaviorsWoEvents=False,
    )

    if not parameters[cfg.SELECTED_SUBJECTS] or not parameters[cfg.SELECTED_BEHAVIORS]:
        return

    # Ask for time interval around the event
    while True:
        text, ok = QInputDialog.getDouble(
            self, "Time interval around the events", "Time (in seconds):", 0.0, 0.0, 86400, 1
        )
        if not ok:
            return
        try:
            timeOffset = util.float2decimal(text)
            break
        except Exception:
            QMessageBox.warning(self, cfg.programName, f"<b>{text}</b> is not recognized as time")

    # ask for video / audio extraction
    items_to_extract, ok = QInputDialog.getItem(
        self, "Tracks to extract", "Tracks", ("Video and audio", "Only video", "Only audio"), 0, False
    )
    if not ok:
        return

    export_dir = QFileDialog().getExistingDirectory(
        self,
        "Choose a directory to extract events",
        os.path.expanduser("~"),
        options=QFileDialog(self).ShowDirsOnly,
    )
    if not export_dir:
        return

    cursor = db_functions.load_events_in_db(
        self.pj,
        parameters[cfg.SELECTED_SUBJECTS],
        selected_observations,
        parameters[cfg.SELECTED_BEHAVIORS],
        time_interval=cfg.TIME_FULL_OBS,
    )

    """
    ffmpeg_extract_command = (
        '"{ffmpeg_bin}" -i "{input_}" -y -ss {start} -to {stop} {codecs} '
        ' "{dir_}{sep}{obsId}_{player}_{subject}_{behavior}_{globalStart}'
        '-{globalStop}{extension}" '
    )
    """
    ffmpeg_extract_command = (
        '"{ffmpeg_bin}" -ss {start} -i "{input_}" -y -t {duration} {codecs} '
        ' "{dir_}{sep}{obs_id}_{player}_{subject}_{behavior}_{globalStart}'
        '-{globalStop}{extension}" '
    )

    for obs_id in selected_observations:

        for nplayer in self.pj[cfg.OBSERVATIONS][obs_id][cfg.FILE]:

            if not self.pj[cfg.OBSERVATIONS][obs_id][cfg.FILE][nplayer]:
                continue

            duration1 = []  # in seconds
            for mediaFile in self.pj[cfg.OBSERVATIONS][obs_id][cfg.FILE][nplayer]:
                duration1.append(self.pj[cfg.OBSERVATIONS][obs_id][cfg.MEDIA_INFO][cfg.LENGTH][mediaFile])

            for subject in parameters[cfg.SELECTED_SUBJECTS]:

                for behavior in parameters[cfg.SELECTED_BEHAVIORS]:

                    cursor.execute(
                        "SELECT occurence FROM events WHERE observation = ? AND subject = ? AND code = ?",
                        (obs_id, subject, behavior),
                    )
                    rows = [{"occurence": util.float2decimal(r["occurence"])} for r in cursor.fetchall()]

                    behavior_state = project_functions.event_type(behavior, self.pj[cfg.ETHOGRAM])
                    if cfg.STATE in behavior_state and len(rows) % 2:  # unpaired events
                        continue

                    for idx, row in enumerate(rows):

                        mediaFileIdx = [
                            idx1 for idx1, x in enumerate(duration1) if row["occurence"] >= sum(duration1[0:idx1])
                        ][-1]

                        # check if media has video
                        try:
                            if self.pj[cfg.OBSERVATIONS][obs_id][cfg.MEDIA_INFO][cfg.HAS_VIDEO][
                                self.pj[cfg.OBSERVATIONS][obs_id][cfg.FILE][nplayer][mediaFileIdx]
                            ]:
                                codecs = "-acodec copy -vcodec copy"
                                # extract extension from video file
                                extension = pathlib.Path(
                                    self.pj[cfg.OBSERVATIONS][obs_id][cfg.FILE][nplayer][mediaFileIdx]
                                ).suffix
                                if not extension:
                                    extension = ".mp4"
                            else:
                                codecs = "-vn"
                                extension = ".wav"

                                logging.debug(
                                    f"Media {self.pj[cfg.OBSERVATIONS][obs_id][cfg.FILE][nplayer][mediaFileIdx]} does not have video"
                                )

                        except Exception:

                            logging.debug(
                                f"has_video not found for: {self.pj[cfg.OBSERVATIONS][obs_id][cfg.FILE][nplayer][mediaFileIdx]}"
                            )

                            continue

                        globalStart = (
                            dec("0.000") if row["occurence"] < timeOffset else round(row["occurence"] - timeOffset, 3)
                        )
                        start = round(
                            row["occurence"]
                            - timeOffset
                            - util.float2decimal(sum(duration1[0:mediaFileIdx]))
                            - self.pj[cfg.OBSERVATIONS][obs_id][cfg.TIME_OFFSET],
                            3,
                        )
                        if start < timeOffset:
                            start = dec("0.000")

                        if cfg.POINT in behavior_state:

                            globalStop = round(row["occurence"] + timeOffset, 3)

                            stop = round(
                                row["occurence"]
                                + timeOffset
                                - util.float2decimal(sum(duration1[0:mediaFileIdx]))
                                - self.pj[cfg.OBSERVATIONS][obs_id][cfg.TIME_OFFSET],
                                3,
                            )

                            ffmpeg_command = ffmpeg_extract_command.format(
                                ffmpeg_bin=self.ffmpeg_bin,
                                input_=project_functions.full_path(
                                    self.pj[cfg.OBSERVATIONS][obs_id][cfg.FILE][nplayer][mediaFileIdx],
                                    self.projectFileName,
                                ),
                                start=start,
                                stop=stop,
                                codecs=codecs,
                                globalStart=globalStart,
                                globalStop=globalStop,
                                dir_=export_dir,
                                sep=os.sep,
                                obs_id=util.safeFileName(obs_id),
                                player="PLAYER{}".format(nplayer),
                                subject=util.safeFileName(subject),
                                behavior=util.safeFileName(behavior),
                                extension=extension,
                            )

                            logging.debug(f"ffmpeg command: {ffmpeg_command}")

                            p = subprocess.Popen(
                                ffmpeg_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True
                            )
                            out, _ = p.communicate()

                        if cfg.STATE in behavior_state:
                            if idx % 2 == 0:

                                # check if stop is on same media file
                                if (
                                    mediaFileIdx
                                    != [
                                        idx1
                                        for idx1, x in enumerate(duration1)
                                        if rows[idx + 1]["occurence"] >= sum(duration1[0:idx1])
                                    ][-1]
                                ):
                                    response = dialog.MessageDialog(
                                        cfg.programName,
                                        (
                                            "The event extends on 2 successive video. "
                                            " At the moment it is not possible to extract this type of event.<br>"
                                        ),
                                        [cfg.OK, "Abort"],
                                    )
                                    if response == cfg.OK:
                                        continue
                                    if response == "Abort":
                                        return

                                globalStop = round(rows[idx + 1]["occurence"] + timeOffset, 3)

                                stop = round(
                                    rows[idx + 1]["occurence"]
                                    + timeOffset
                                    - util.float2decimal(sum(duration1[0:mediaFileIdx]))
                                    - self.pj[cfg.OBSERVATIONS][obs_id][cfg.TIME_OFFSET],
                                    3,
                                )

                                # check if start after length of media
                                if (
                                    start
                                    > self.pj[cfg.OBSERVATIONS][obs_id][cfg.MEDIA_INFO][cfg.LENGTH][
                                        self.pj[cfg.OBSERVATIONS][obs_id][cfg.FILE][nplayer][mediaFileIdx]
                                    ]
                                ):
                                    continue

                                ffmpeg_command = ffmpeg_extract_command.format(
                                    ffmpeg_bin=self.ffmpeg_bin,
                                    input_=project_functions.full_path(
                                        self.pj[cfg.OBSERVATIONS][obs_id][cfg.FILE][nplayer][mediaFileIdx],
                                        self.projectFileName,
                                    ),
                                    start=start,
                                    duration=stop - start,
                                    codecs="",
                                    globalStart=globalStart,
                                    globalStop=globalStop,
                                    dir_=export_dir,
                                    sep=os.sep,
                                    obs_id=util.safeFileName(obs_id),
                                    player=f"PLAYER{nplayer}",
                                    subject=util.safeFileName(subject),
                                    behavior=util.safeFileName(behavior),
                                    extension=extension,
                                )

                                logging.debug("ffmpeg command: {}".format(ffmpeg_command))
                                p = subprocess.Popen(
                                    ffmpeg_command, stdout=subprocess.PIPE, stderr=subprocess.PIPE, shell=True
                                )
                                out, _ = p.communicate()

    self.statusbar.showMessage(f"Media sequence extracted in {export_dir}", 0)
