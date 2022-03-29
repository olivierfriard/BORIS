import os
import logging
import subprocess
from decimal import Decimal

from . import config as cfg
from . import utilities as util
from . import dialog
from . import project_functions
from . import db_functions

from PyQt5.QtWidgets import QInputDialog, QMessageBox, QFileDialog


def events_snapshots(self):
    """
    create snapshots corresponding to coded events
    if observations are from media file and media files have video
    """

    result, selected_observations = self.selectObservations(cfg.MULTIPLE)
    if not selected_observations:
        return

    # check if obs are MEDIA
    live_obs_list = []
    for obs_id in selected_observations:
        if self.pj[cfg.OBSERVATIONS][obs_id][cfg.TYPE] in [cfg.LIVE]:
            live_obs_list.append(obs_id)
    if live_obs_list:
        out = "The following observations are live observations and will not be used<br><br>"
        out += "<br>".join(live_obs_list)
        results = dialog.Results_dialog()
        results.setWindowTitle(cfg.programName)
        results.ptText.setReadOnly(True)
        results.ptText.appendHtml(out)
        results.pbSave.setVisible(False)
        results.pbCancel.setVisible(True)
        if not results.exec_():
            return

    # remove live  observations
    selected_observations = [x for x in selected_observations if x not in live_obs_list]
    if not selected_observations:
        return

    # check if state events are paired
    out = ""
    not_paired_obs_list = []
    for obsId in selected_observations:
        r, msg = project_functions.check_state_events_obs(
            obsId, self.pj[cfg.ETHOGRAM], self.pj[cfg.OBSERVATIONS][obsId], self.timeFormat
        )

        if not r:
            out += f"Observation: <strong>{obsId}</strong><br>{msg}<br>"
            not_paired_obs_list.append(obsId)

    if out:
        out = "The observations with UNPAIRED state events will be removed from the analysis<br><br>" + out
        results = dialog.Results_dialog()
        results.setWindowTitle(f"{cfg.programName} - Check selected observations")
        results.ptText.setReadOnly(True)
        results.ptText.appendHtml(out)
        results.pbSave.setVisible(False)
        results.pbCancel.setVisible(True)

        if not results.exec_():
            return

    # remove observations with unpaired state events
    selected_observations = [x for x in selected_observations if x not in not_paired_obs_list]
    if not selected_observations:
        return

    parameters = self.choose_obs_subj_behav_category(
        selected_observations, maxTime=0, flagShowIncludeModifiers=False, flagShowExcludeBehaviorsWoEvents=False
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

    try:
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
                                Decimal("0.000")
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
                                start = Decimal("0.000")

                            if cfg.POINT in behavior_state:

                                media_path = project_functions.media_full_path(
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
                                            [OK, "Abort"],
                                        )
                                        if response == OK:
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

                                    media_path = project_functions.media_full_path(
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
                                    out, error = p.communicate()

    except Exception:
        dialog.error_message2()
