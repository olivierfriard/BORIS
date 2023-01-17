"""
BORIS
Behavioral Observation Research Interactive Software
Copyright 2012-2023 Olivier Friard

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

from . import config as cfg
from . import utilities as util
from . import dialog
from . import project_functions
from PyQt5.QtWidgets import QFileDialog


def get_info(self):
    """
    show info about media file (current media file if observation opened)
    """

    if self.observationId and self.playerType == cfg.MEDIA:

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

            for file_path in self.pj[cfg.OBSERVATIONS][self.observationId][cfg.FILE][str(i + 1)]:
                media_full_path = project_functions.full_path(file_path, self.projectFileName)
                r = util.accurate_media_analysis(self.ffmpeg_bin, media_full_path)
                nframes = r["frames_number"]
                if "error" in r:
                    ffmpeg_output += "File path: {filePath}<br><br>{error}<br><br>".format(
                        filePath=media_full_path, error=r["error"]
                    )
                else:

                    ffmpeg_output += (
                        f"File path: {media_full_path}<br>"
                        f"Duration: {r['duration']} seconds ({util.convertTime(self.timeFormat, r['duration'])})<br>"
                        f"Resolution: {r['resolution']}<br>"
                        f"Number of frames: {r['frames_number']}<br>"
                        f"Bitrate: {r['bitrate']} k<br>"
                        f"FPS: {r['fps']}<br>"
                        f"Has video: {r['has_video']}<br>"
                        f"Has audio: {r['has_audio']}<br>"
                        f"File size: {r.get('file size', 'NA')}<br>"
                        f"Video codec: {r.get('video_codec', 'NA')}<br>"
                        f"Audio codec: {r.get('audio_codec', 'NA')}<br>"
                    )

                ffmpeg_output += f"Total duration: {sum(self.dw_player[i].media_durations) / 1000} ({util.convertTime(self.timeFormat, sum(self.dw_player[i].media_durations) / 1000)})"

            tot_output += mpv_output + ffmpeg_output + "<br><hr>"

        self.results = dialog.Results_dialog()
        self.results.setWindowTitle(cfg.programName + " - Media file information")
        self.results.ptText.appendHtml(tot_output)
        self.results.show()

    else:  # no open observation

        fn = QFileDialog().getOpenFileName(self, "Select a media file", "", "Media files (*)")
        file_path = fn[0] if type(fn) is tuple else fn

        if file_path:
            self.results = dialog.Results_dialog()
            self.results.setWindowTitle(f"{cfg.programName} - Media file information")
            self.results.ptText.appendHtml("<br><b>FFmpeg analysis</b><hr>")
            r = util.accurate_media_analysis(self.ffmpeg_bin, file_path)
            if "error" in r:
                self.results.ptText.appendHtml(f"File path: {file_path}<br><br>{r['error']}<br><br>")
            else:
                self.results.ptText.appendHtml(
                    (
                        f"File path: {file_path}<br>"
                        f"Duration: {r['duration']} seconds ({util.convertTime(self.timeFormat, r['duration'])})<br>"
                        f"Resolution: {r['resolution']}<br>"
                        f"Number of frames: {r['frames_number']}<br>"
                        f"Bitrate: {r['bitrate']} k<br>"
                        f"FPS: {r['fps']}<br>"
                        f"Has video: {r['has_video']}<br>"
                        f"Has audio: {r['has_audio']}<br>"
                        f"File size: {r.get('file size', 'NA')}<br>"
                        f"Video codec: {r.get('video_codec', 'NA')}<br>"
                        f"Audio codec: {r.get('audio_codec', 'NA')}<br>"
                    )
                )

            self.results.show()
