import logging

from . import config as cfg
from . import utilities as util
from . import dialog
from . import project_functions
from PyQt5.QtWidgets import QFileDialog


def get_info(self):
    """
    show info about media file (current media file if observation opened)
    """

    if self.observationId and self.playerType == cfg.VLC:

        tot_output = ""

        for i, dw in enumerate(self.dw_player):
            if not (
                str(i + 1) in self.pj[cfg.OBSERVATIONS][self.observationId][cfg.FILE]
                and self.pj[cfg.OBSERVATIONS][self.observationId][cfg.FILE][str(i + 1)]
            ):
                continue

            logging.info(f"Video format: {dw.player.video_format}")
            logging.info(f"number of media in media list: {dw.player.playlist_count}")
            logging.info(f"Current time position: {dw.player.time_pos}  duration: {dw.player.duration}")

            logging.info(f"FPS: {dw.player.container_fps}")

            # logging.info("Rate: {}".format(player.mediaplayer.get_rate()))
            logging.info(f"Video size: {dw.player.width}x{dw.player.height}  ratio: ")

            logging.info(f"Aspect ratio: {round(dw.player.width / dw.player.height, 3)}")
            # logging.info("is seekable? {0}".format(player.mediaplayer.is_seekable()))
            # logging.info("has_vout? {0}".format(player.mediaplayer.has_vout()))

            mpv_output = (
                "<b>MPV information</b><br>"
                f"Video format: {dw.player.video_format}<br>"
                # "State: {}<br>"
                # "Media Resource Location: {}<br>"
                # "File name: {}<br>"
                # "Track: {}/{}<br>"
                f"Number of media in media list: {dw.player.playlist_count}<br>"
                f"Current time position: {dw.player.time_pos}<br>"
                f"duration: {dw.player.duration}<br>"
                # "Position: {} %<br>"
                f"FPS: {dw.player.container_fps}<br>"
                # "Rate: {}<br>"
                f"Video size: {dw.player.width}x{dw.player.height}<br>"
                # "Scale: {}<br>"
                f"Aspect ratio: {round(dw.player.width / dw.player.height, 3)}<br>"
                # "is seekable? {}<br>"
                # "has_vout? {}<br>"
            )

            # FFmpeg analysis
            ffmpeg_output = "<br><b>FFmpeg analysis</b><br>"

            for filePath in self.pj[cfg.OBSERVATIONS][self.observationId][cfg.FILE][str(i + 1)]:
                media_full_path = project_functions.media_full_path(filePath, self.projectFileName)
                r = util.accurate_media_analysis(self.ffmpeg_bin, media_full_path)
                nframes = r["frames_number"]
                if "error" in r:
                    ffmpeg_output += "File path: {filePath}<br><br>{error}<br><br>".format(
                        filePath=media_full_path, error=r["error"]
                    )
                else:
                    ffmpeg_output += (
                        "File path: {}<br>Duration: {}<br>Bitrate: {}k<br>"
                        "FPS: {}<br>Has video: {}<br>Has audio: {}<br><br>"
                    ).format(
                        media_full_path,
                        self.convertTime(r["duration"]),
                        r["bitrate"],
                        r["fps"],
                        r["has_video"],
                        r["has_audio"],
                    )

                ffmpeg_output += "Total duration: {} (hh:mm:ss.sss)".format(
                    self.convertTime(sum(self.dw_player[i].media_durations) / 1000)
                )

            tot_output += mpv_output + ffmpeg_output + "<br><hr>"

        self.results = dialog.ResultsWidget()
        self.results.setWindowTitle(cfg.programName + " - Media file information")
        self.results.ptText.setReadOnly(True)
        self.results.ptText.appendHtml(tot_output)
        self.results.show()

    else:  # no open observation

        fn = QFileDialog().getOpenFileName(self, "Select a media file", "", "Media files (*)")
        filePath = fn[0] if type(fn) is tuple else fn

        if filePath:
            self.results = dialog.ResultsWidget()
            self.results.setWindowTitle(cfg.programName + " - Media file information")
            self.results.ptText.setReadOnly(True)
            self.results.ptText.appendHtml("<br><b>FFmpeg analysis</b><hr>")
            r = util.accurate_media_analysis(self.ffmpeg_bin, filePath)
            if "error" in r:
                self.results.ptText.appendHtml(
                    "File path: {filePath}<br><br>{error}<br><br>".format(filePath=filePath, error=r["error"])
                )
            else:
                self.results.ptText.appendHtml(
                    (
                        "File path: {}<br>Duration: {}<br>Bitrate: {}k<br>"
                        "FPS: {}<br>Has video: {}<br>Has audio: {}<br><br>"
                    ).format(
                        filePath,
                        self.convertTime(r["duration"]),
                        r["bitrate"],
                        r["fps"],
                        r["has_video"],
                        r["has_audio"],
                    )
                )

            self.results.show()
