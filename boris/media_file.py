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

from PySide6.QtWidgets import QFileDialog

from . import config as cfg
from . import utilities as util
from . import dialog
from . import project_functions
from . import utilities as util


def get_info(self) -> None:
    """
    show info about media file (current media file if an observation is opened)
    """

    def media_analysis_str(ffmpeg_bin: str, media_full_path: str) -> str:
        r = util.accurate_media_analysis(ffmpeg_bin, media_full_path)

        if "error" in r:
            ffmpeg_output = f"File path: {media_full_path}<br><br>{r['error']}<br><br>"
        else:
            ffmpeg_output = f"<br><b>{r['analysis_program']} analysis</b><br>"

            ffmpeg_output += (
                f"File path: <b>{media_full_path}</b><br><br>"
                f"Duration: {r['duration']} seconds ({util.convertTime(self.timeFormat, r['duration'])})<br>"
                f"FPS: {r['fps']}<br>"
                f"Resolution: {r['resolution']} pixels<br>"
                f"Format long name: {r.get('format_long_name', cfg.NA)}<br>"
                f"Creation time: {r.get('creation_time', cfg.NA)}<br>"
                f"Number of frames: {r['frames_number']}<br>"
                f"Bitrate: {util.smart_size_format(r['bitrate'])}   <br>"
                f"Has video: {r['has_video']}<br>"
                f"Has audio: {r['has_audio']}<br>"
                f"File size: {util.smart_size_format(r.get('file size', cfg.NA))}<br>"
                f"Video codec: {r.get('video_codec', cfg.NA)}<br>"
                f"Audio codec: {r.get('audio_codec', cfg.NA)}<br>"
            )

        return ffmpeg_output

    if self.observationId and self.playerType == cfg.MEDIA:
        tot_output: str = ""

        for i, dw in enumerate(self.dw_player):
            if not (
                str(i + 1) in self.pj[cfg.OBSERVATIONS][self.observationId][cfg.FILE]
                and self.pj[cfg.OBSERVATIONS][self.observationId][cfg.FILE][str(i + 1)]
            ):
                continue

            mpv_output = (
                "<b>MPV information</b><br>"
                f"Duration: {dw.player.duration} seconds ({util.seconds2time(dw.player.duration)})<br>"
                # "Position: {} %<br>"
                f"FPS: {dw.player.container_fps}<br>"
                # "Rate: {}<br>"
                f"Resolution: {dw.player.width}x{dw.player.height} pixels<br>"
                # "Scale: {}<br>"
                f"Video format: {dw.player.video_format}<br>"
                # "State: {}<br>"
                # "Media Resource Location: {}<br>"
                # "File name: {}<br>"
                # "Track: {}/{}<br>"
                f"Number of media in media list: {dw.player.playlist_count}<br>"
                f"Current time position: {dw.player.time_pos}<br>"
                f"Aspect ratio: {round(dw.player.width / dw.player.height, 3)}<br>"
                # "is seekable? {}<br>"
                # "has_vout? {}<br>"
            )

            # FFmpeg/FFprobe analysis
            ffmpeg_output: str = ""
            for file_path in self.pj[cfg.OBSERVATIONS][self.observationId][cfg.FILE][str(i + 1)]:
                media_full_path = project_functions.full_path(file_path, self.projectFileName)
                ffmpeg_output += media_analysis_str(self.ffmpeg_bin, media_full_path)

            ffmpeg_output += f"<br>Total duration: {sum(self.dw_player[i].media_durations) / 1000} ({util.convertTime(self.timeFormat, sum(self.dw_player[i].media_durations) / 1000)})"

            tot_output += mpv_output + ffmpeg_output + "<br><hr>"

    else:  # no open observation
        file_paths, _ = QFileDialog().getOpenFileNames(self, "Select a media file", "", "Media files (*)")
        if not file_paths:
            return

        tot_output: str = ""
        for file_path in file_paths:
            tot_output += media_analysis_str(self.ffmpeg_bin, file_path)

    self.results = dialog.Results_dialog()
    self.results.setWindowTitle(f"{cfg.programName} - Media file information")
    self.results.ptText.appendHtml(tot_output)
    self.results.show()
