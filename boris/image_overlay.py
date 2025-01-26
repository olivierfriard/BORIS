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
from . import config as cfg
from . import dialog


def add_image_overlay(self) -> None:
    """
    add an image overlay on video from an image
    """

    logging.debug("function add_image_overlay")

    try:
        w = dialog.Video_overlay_dialog()
        items = [f"Player #{i + 1}" for i, _ in enumerate(self.dw_player)]
        w.cb_player.addItems(items)
        if not w.exec_():
            return

        idx = w.cb_player.currentIndex()

        if cfg.OVERLAY not in self.pj[cfg.OBSERVATIONS][self.observationId][cfg.MEDIA_INFO]:
            self.pj[cfg.OBSERVATIONS][self.observationId][cfg.MEDIA_INFO][cfg.OVERLAY] = {}
        self.pj[cfg.OBSERVATIONS][self.observationId][cfg.MEDIA_INFO][cfg.OVERLAY][str(idx + 1)] = {
            "file name": w.le_file_path.text(),
            "overlay position": w.le_overlay_position.text(),
            "transparency": w.sb_overlay_transparency.value(),
        }
        self.overlays[idx] = self.dw_player[idx].player.create_image_overlay()
        self.project_changed()
        self.resize_dw(idx)

    except Exception:
        logging.debug("error in add_image_overlay function")


def remove_image_overlay(self) -> None:
    """
    remove image overlay from all players
    """
    keys_to_delete: list = []
    for n_player in self.pj[cfg.OBSERVATIONS][self.observationId][cfg.MEDIA_INFO].get(cfg.OVERLAY, {}):
        keys_to_delete.append(n_player)
        try:
            self.overlays[int(n_player) - 1].remove()
        except Exception:
            logging.debug("Error removing image overlay")
    for n_player in keys_to_delete:
        del self.pj[cfg.OBSERVATIONS][self.observationId][cfg.MEDIA_INFO][cfg.OVERLAY][n_player]
