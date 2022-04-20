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

from math import log2
import pathlib as pl
import logging
from . import config as cfg
from . import dialog


def snapshot(self):
    """
    take snapshot of current video at current position
    snapshot is saved on media path
    """

    if self.pj[cfg.OBSERVATIONS][self.observationId][cfg.TYPE] in [cfg.MEDIA]:

        if self.playerType == cfg.VLC:

            for i, player in enumerate(self.dw_player):
                if (
                    str(i + 1) in self.pj[cfg.OBSERVATIONS][self.observationId][cfg.FILE]
                    and self.pj[cfg.OBSERVATIONS][self.observationId][cfg.FILE][str(i + 1)]
                ):

                    p = pl.Path(self.dw_player[0].player.playlist[self.dw_player[0].player.playlist_pos]["filename"])

                    snapshot_file_path = str(p.parent / f"{p.stem}_{player.player.time_pos}.png")

                    player.player.screenshot_to_file(snapshot_file_path)


def zoom_level(self):
    """
    display dialog for zoom level
    """
    players_list = []
    for idx, dw in enumerate(self.dw_player):
        zoom_levels = []
        for choice in [2, 1, 0.5, 0.25]:
            zoom_levels.append((str(choice), "selected" if log2(choice) == dw.player.video_zoom else ""))
        players_list.append(("il", f"Player #{idx + 1}", zoom_levels))

    zl = dialog.Input_dialog("Select the zoom level", players_list)
    if not zl.exec_():
        return

    if cfg.ZOOM_LEVEL not in self.pj[cfg.OBSERVATIONS][self.observationId][cfg.MEDIA_INFO]:
        self.pj[cfg.OBSERVATIONS][self.observationId][cfg.MEDIA_INFO][cfg.ZOOM_LEVEL] = {}

    for idx, dw in enumerate(self.dw_player):
        if self.pj[cfg.OBSERVATIONS][self.observationId][cfg.MEDIA_INFO][cfg.ZOOM_LEVEL].get(
            str(idx + 1), dw.player.video_zoom
        ) != float(zl.elements[f"Player #{idx + 1}"].currentText()):
            dw.player.video_zoom = log2(float(zl.elements[f"Player #{idx + 1}"].currentText()))
            self.pj[cfg.OBSERVATIONS][self.observationId][cfg.MEDIA_INFO][cfg.ZOOM_LEVEL][str(idx + 1)] = float(
                zl.elements[f"Player #{idx + 1}"].currentText()
            )
            self.projectChanged = True


def display_subtitles(self):
    """
    display dialog for subtitles display
    """
    players_list = []
    for idx, dw in enumerate(self.dw_player):
        if cfg.DISPLAY_MEDIA_SUBTITLES in self.pj[cfg.OBSERVATIONS][self.observationId][cfg.MEDIA_INFO]:
            default = self.pj[cfg.OBSERVATIONS][self.observationId][cfg.MEDIA_INFO][cfg.DISPLAY_MEDIA_SUBTITLES].get(
                str(idx + 1), dw.player.sub_visibility
            )
        else:
            default = dw.player.sub_visibility
        players_list.append(("cb", f"Player #{idx + 1}", default))

    st = dialog.Input_dialog("Display subtitles", players_list)
    if not st.exec_():
        return

    if cfg.DISPLAY_MEDIA_SUBTITLES not in self.pj[cfg.OBSERVATIONS][self.observationId][cfg.MEDIA_INFO]:
        self.pj[cfg.OBSERVATIONS][self.observationId][cfg.MEDIA_INFO][cfg.DISPLAY_MEDIA_SUBTITLES] = {}

    for idx, dw in enumerate(self.dw_player):
        if (
            self.pj[cfg.OBSERVATIONS][self.observationId][cfg.MEDIA_INFO][cfg.DISPLAY_MEDIA_SUBTITLES].get(
                str(idx + 1), dw.player.sub_visibility
            )
            != st.elements[f"Player #{idx + 1}"].isChecked()
        ):
            dw.player.sub_visibility = st.elements[f"Player #{idx + 1}"].isChecked()
            self.pj[cfg.OBSERVATIONS][self.observationId][cfg.MEDIA_INFO][cfg.DISPLAY_MEDIA_SUBTITLES][
                str(idx + 1)
            ] = st.elements[f"Player #{idx + 1}"].isChecked()
            self.projectChanged = True


def video_normalspeed_activated(self):
    """
    set playing speed at normal speed (1x)
    """

    if self.playerType == cfg.VLC and self.playMode == cfg.MPV:
        self.play_rate = 1
        for i, player in enumerate(self.dw_player):
            if (
                str(i + 1) in self.pj[cfg.OBSERVATIONS][self.observationId][cfg.FILE]
                and self.pj[cfg.OBSERVATIONS][self.observationId][cfg.FILE][str(i + 1)]
            ):
                player.player.speed = self.play_rate

        self.lbSpeed.setText(f"x{self.play_rate:.3f}")

        logging.debug(f"play rate: {self.play_rate:.3f}")


def video_faster_activated(self):
    """
    increase playing speed by play_rate_step value
    """

    if self.playerType == cfg.VLC and self.playMode == cfg.MPV:

        if self.play_rate + self.play_rate_step <= 60:
            self.play_rate += self.play_rate_step
            for i, player in enumerate(self.dw_player):
                if (
                    str(i + 1) in self.pj[cfg.OBSERVATIONS][self.observationId][cfg.FILE]
                    and self.pj[cfg.OBSERVATIONS][self.observationId][cfg.FILE][str(i + 1)]
                ):
                    player.player.speed = self.play_rate
            self.lbSpeed.setText(f"x{self.play_rate:.3f}")

            logging.debug(f"play rate: {self.play_rate:.3f}")


def video_slower_activated(self):
    """
    decrease playing speed by play_rate_step value
    """

    if self.playerType == cfg.VLC and self.playMode == cfg.MPV:

        if self.play_rate - self.play_rate_step >= 0.1:
            self.play_rate -= self.play_rate_step

            for i, player in enumerate(self.dw_player):
                player.player.speed = round(self.play_rate, 3)

            self.lbSpeed.setText(f"x{self.play_rate:.3f}")

            logging.debug(f"play rate: {self.play_rate:.3f}")