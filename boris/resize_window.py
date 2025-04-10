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


def resize_center(app, window, width, height):
    window.resize(width, height)
    screen_geometry = app.primaryScreen().geometry()
    if window.height() > screen_geometry.height():
        window.resize(window.width(), int(screen_geometry.height() * 0.8))
    if window.width() > screen_geometry.width():
        window.resize(screen_geometry.width(), window.height())
    # center
    center_x = (screen_geometry.width() - window.width()) // 2
    center_y = (screen_geometry.height() - window.height()) // 2

    window.move(center_x, center_y)
