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

import logging
import pathlib as pl
import shutil
from math import log2

from PySide6.QtWidgets import QFileDialog

from . import config as cfg
from . import dialog


def deinterlace(self):
    """
    change the deinterlace status of player
    """

    logging.info("change deinterlace status of player")

    for dw in self.dw_player:
        dw.player.deinterlace = self.action_deinterlace.isChecked()


def snapshot(self):
    """
    MEDIA obs: take snapshot of current video at current position
    IMAGES obs: save a copy of the current image

    snapshot is saved on media path following the template: MEDIA-FILE-NAME_TIME-POSITION.png
    """

    if self.playerType == cfg.MEDIA:
        for i, player in enumerate(self.dw_player):
            if (
                str(i + 1) in self.pj[cfg.OBSERVATIONS][self.observationId][cfg.FILE]
                and self.pj[cfg.OBSERVATIONS][self.observationId][cfg.FILE][str(i + 1)]
            ):
                p = pl.Path(self.dw_player[0].player.playlist[self.dw_player[0].player.playlist_pos]["filename"])

                snapshot_file_path = str(p.parent / f"{p.stem}_{player.player.time_pos:0.3f}.png")

                player.player.screenshot_to_file(snapshot_file_path)
                self.statusbar.showMessage(f"Video snapshot saved in {snapshot_file_path}", 0)

                logging.debug(f"video snapshot saved in {snapshot_file_path}")

    if self.playerType == cfg.IMAGES:
        output_file_name, _ = QFileDialog().getSaveFileName(
            self, "Save copy of the current image", pl.Path(self.images_list[self.image_idx]).name
        )
        if output_file_name:
            shutil.copyfile(self.images_list[self.image_idx], output_file_name)
            self.statusbar.showMessage(f"Image saved in {output_file_name}", 0)

            logging.debug(f"video snapshot saved in {output_file_name}")


def zoom_level(self):
    """
    display dialog box for setting the zoom level
    """
    logging.info("change zoom level of player")

    players_list: list = []
    for idx, dw in enumerate(self.dw_player):
        players_list.append(("dsb", f"Player #{idx + 1}", 0.1, 12, 0.1, 2**dw.player.video_zoom, 1))

        """
        zoom_levels: list = []
        for choice in (2, 1, 0.5, 0.25):
            zoom_levels.append((str(choice), "selected" if log2(choice) == dw.player.video_zoom else ""))
        players_list.append(("il", f"Player #{idx + 1}", zoom_levels))
        """

    zl = dialog.Input_dialog(label_caption="Select the zoom level", elements_list=players_list, title="Video zoom level")
    if not zl.exec_():
        return

    if cfg.ZOOM_LEVEL not in self.pj[cfg.OBSERVATIONS][self.observationId][cfg.MEDIA_INFO]:
        self.pj[cfg.OBSERVATIONS][self.observationId][cfg.MEDIA_INFO][cfg.ZOOM_LEVEL] = {}

    for idx, dw in enumerate(self.dw_player):
        if (
            self.pj[cfg.OBSERVATIONS][self.observationId][cfg.MEDIA_INFO][cfg.ZOOM_LEVEL].get(str(idx + 1), dw.player.video_zoom)
            != zl.elements[f"Player #{idx + 1}"].value()
        ):
            dw.player.video_zoom = log2(float(zl.elements[f"Player #{idx + 1}"].value()))

            logging.debug(f"video zoom changed in {dw.player.video_zoom} for player {idx + 1}")

            self.pj[cfg.OBSERVATIONS][self.observationId][cfg.MEDIA_INFO][cfg.ZOOM_LEVEL][str(idx + 1)] = float(
                zl.elements[f"Player #{idx + 1}"].value()
            )
            display_zoom_level(self)
            self.project_changed()


def rotate_displayed_video(self):
    """
    rotate the displayed video
    """
    players_list: list = []
    for idx, dw in enumerate(self.dw_player):
        rotation_angles: list = []
        for choice in (0, 90, 180, 270):
            rotation_angles.append((str(choice), "selected" if choice == dw.player.video_rotate else ""))
        players_list.append(("il", f"Player #{idx + 1}", rotation_angles))

    w = dialog.Input_dialog(label_caption="Select the rotation angle", elements_list=players_list, title="Video rotation angle")
    if not w.exec_():
        return
    if cfg.ROTATION_ANGLE not in self.pj[cfg.OBSERVATIONS][self.observationId][cfg.MEDIA_INFO]:
        self.pj[cfg.OBSERVATIONS][self.observationId][cfg.MEDIA_INFO][cfg.ROTATION_ANGLE] = {}

    for idx, dw in enumerate(self.dw_player):
        if self.pj[cfg.OBSERVATIONS][self.observationId][cfg.MEDIA_INFO][cfg.ROTATION_ANGLE].get(
            str(idx + 1), dw.player.video_rotate
        ) != float(w.elements[f"Player #{idx + 1}"].currentText()):
            dw.player.video_rotate = int(w.elements[f"Player #{idx + 1}"].currentText())

            logging.debug(f"video rotation changed to {dw.player.video_rotate} for player {idx + 1}")

            self.pj[cfg.OBSERVATIONS][self.observationId][cfg.MEDIA_INFO][cfg.ROTATION_ANGLE][str(idx + 1)] = int(
                w.elements[f"Player #{idx + 1}"].currentText()
            )
            self.project_changed()


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

            logging.debug(f"subtitle visibility for player {idx + 1}: {dw.player.sub_visibility}")

            self.pj[cfg.OBSERVATIONS][self.observationId][cfg.MEDIA_INFO][cfg.DISPLAY_MEDIA_SUBTITLES][str(idx + 1)] = st.elements[
                f"Player #{idx + 1}"
            ].isChecked()
            self.project_changed()


def display_zoom_level(self) -> None:
    """
    display the zoom level
    """
    msg: str = "Zoom level: <b>"
    for player in self.dw_player:
        msg += f"{2**player.player.video_zoom:.1f} "
    msg += "</b>"
    self.lb_zoom_level.setText(msg)


def display_play_rate(self) -> None:
    """
    display current play rate in status bar widget
    """

    self.lb_video_info.setText(f"Play rate: <b>x{self.play_rate:.3f}</b>")

    logging.debug(f"play rate: {self.play_rate:.3f}")


def video_normalspeed_activated(self):
    """
    set playing speed at normal speed (1x)
    """

    if self.playerType != cfg.MEDIA:
        return

    self.play_rate = 1
    for i, player in enumerate(self.dw_player):
        if (
            str(i + 1) in self.pj[cfg.OBSERVATIONS][self.observationId][cfg.FILE]
            and self.pj[cfg.OBSERVATIONS][self.observationId][cfg.FILE][str(i + 1)]
        ):
            player.player.speed = self.play_rate

    display_play_rate(self)


def video_faster_activated(self):
    """
    increase playing speed by play_rate_step value
    """

    if self.playerType != cfg.MEDIA:
        return

    if self.play_rate + self.play_rate_step <= 60:
        self.play_rate += self.play_rate_step
        for i, player in enumerate(self.dw_player):
            if (
                str(i + 1) in self.pj[cfg.OBSERVATIONS][self.observationId][cfg.FILE]
                and self.pj[cfg.OBSERVATIONS][self.observationId][cfg.FILE][str(i + 1)]
            ):
                player.player.speed = self.play_rate

        display_play_rate(self)


def video_slower_activated(self):
    """
    decrease playing speed by play_rate_step value
    """

    if self.playerType != cfg.MEDIA:
        return

    if self.play_rate - self.play_rate_step >= 0.1:
        self.play_rate -= self.play_rate_step

        for i, player in enumerate(self.dw_player):
            player.player.speed = round(self.play_rate, 3)

        display_play_rate(self)
