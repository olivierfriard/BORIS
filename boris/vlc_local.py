"""
BORIS
Behavioral Observation Research Interactive Software
Copyright 2012-2020 Olivier Friard

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

# check if library in same dir than vlc.py

import pathlib
import sys
import ctypes
import os

def find_local_libvlc():

    print("sys.argv (vlc local)", sys.argv)

    dll = None
    plugin_path = ""

    if sys.platform.startswith("linux"):
        # for Linux VLC must be installed
        return dll, plugin_path

    p = pathlib.Path(sys.argv[0])
    parent_dir = p.resolve().parent

    vlc_dll_path = pathlib.Path("")
    if sys.argv[0].endswith("start_behatrix.py"):
        vlc_dll_path = pathlib.Path(sys.argv[0]).resolve().parent / "boris" / "misc" / "libvlc.dll"

    if sys.argv[0].endswith("__main__.py"):
        vlc_dll_path = pathlib.Path(sys.argv[0]).resolve().parent / "misc" / "libvlc.dll"

    print(f"vlc_dll_path: {vlc_dll_path}")
    if not vlc_dll_path.is_file():
        print("The vlc dll was not found!")
        return dll, plugin_path

    if sys.platform.startswith("win"):
        dll = ctypes.CDLL(libname)
        plugin_path = str(pathlib.Path(sys.argv[0]).resolve().parent / "misc" / "plugins")

    if sys.platform.startswith("darwin"):

        libvlccore_path = parent_dir / "VLC" / "lib" / "libvlccore.dylib"
        libvlc_path = parent_dir / "VLC" / "lib" / "libvlc.dylib"

        if libvlccore_path.exists():
            ctypes.CDLL(str(libvlccore_path))
        if libvlc_path.exists():
            dll = ctypes.CDLL(str(libvlc_path))

        plugin_path = parent_dir / "VLC" / "plugins"
        if plugin_path.exists():
            plugin_path = str(plugin_path)

    return dll, plugin_path


if __name__ == "__main__":
    print(find_local_libvlc())
