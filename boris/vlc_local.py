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

    dll = None
    plugin_path = ""

    if sys.platform.startswith("linux"):
        # for Linux VLC must be installed
        return dll, plugin_path

    vlc_dll_path = pathlib.Path("")

    if sys.platform.startswith("win"):
        
        if sys.argv[0].endswith("start_boris.py"):
            vlc_dll_path = pathlib.Path(sys.argv[0]).resolve().parent / "boris" / "misc" / "libvlc.dll"

        if sys.argv[0].endswith("__main__.py"):
            vlc_dll_path = pathlib.Path(sys.argv[0]).resolve().parent / "misc" / "libvlc.dll"

        print(f"vlc_dll_path: {vlc_dll_path}")
        if not vlc_dll_path.is_file():
            print("The vlc dll was not found!")
            return dll, plugin_path

        dll = ctypes.CDLL(str(vlc_dll_path))
        plugin_path = str(pathlib.Path(sys.argv[0]).resolve().parent / "misc" / "plugins")


    if sys.platform.startswith("darwin"):

        libvlccore_path = pathlib.Path("")
        if sys.argv[0].endswith("start_boris.py"):
            libvlccore_path = pathlib.Path(sys.argv[0]).resolve().parent / "boris" / "misc" / "VLC" / "lib" / "libvlccore.dylib"
            vlc_dll_path = pathlib.Path(sys.argv[0]).resolve().parent / "boris" / "misc" / "VLC" / "lib" / "libvlc.dylib"
            plugin_path = pathlib.Path(sys.argv[0]).resolve().parent / "boris" / "misc" / "VLC" / "plugins"

        if sys.argv[0].endswith("__main__.py"):
            libvlccore_path = pathlib.Path(sys.argv[0]).resolve().parent / "misc" / "VLC" / "lib" / "libvlccore.dylib"
            vlc_dll_path = pathlib.Path(sys.argv[0]).resolve().parent / "misc" / "VLC" / "lib" / "libvlc.dylib"
            plugin_path = pathlib.Path(sys.argv[0]).resolve().parent / "misc" / "VLC" / "plugins"

        if vlc_dll_path.is_file():
            if libvlccore_path.is_file():
                ctypes.CDLL(str(libvlccore_path))
            else:
                print(f"libvlc core not found: {vlc_dll_path}")
            dll = ctypes.CDLL(str(vlc_dll_path))

        return dll, str(plugin_path)

    return dll, plugin_path


if __name__ == "__main__":
    print(find_local_libvlc())
