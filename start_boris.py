"""
BORIS
Behavioral Observation Research Interactive Software
Copyright 2012-2026 Olivier Friard

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

import sys


def configure_application_identity():
    if sys.platform == "darwin":
        try:
            from Foundation import NSBundle, NSProcessInfo
        except ImportError as exc:
            raise SystemExit(
                "The macOS launcher requires PyObjC. Run:\n"
                "uv run start_boris.py"
            ) from exc

        # Cocoa and Qt can cache the name during initialization. Change only
        # this process's in-memory metadata before importing Qt or BORIS.
        info = NSBundle.mainBundle().infoDictionary()
        if info is None:
            raise SystemExit("Cannot set the BORIS name: the main bundle has no information dictionary.")
        try:
            info["CFBundleName"] = "BORIS"
            info["CFBundleDisplayName"] = "BORIS"
        except (TypeError, AttributeError) as exc:
            raise SystemExit("Cannot set the BORIS name: the main bundle information dictionary is not writable.") from exc
        NSProcessInfo.processInfo().setProcessName_("BORIS")

    from PySide6.QtCore import QCoreApplication
    from PySide6.QtGui import QGuiApplication

    QCoreApplication.setApplicationName("BORIS")
    QGuiApplication.setApplicationDisplayName("BORIS")


def main():
    configure_application_identity()

    # BORIS creates QApplication after its OpenGL setup. Preserve all arguments
    # so the usual BORIS command-line parser handles them.
    from boris import main as boris_main

    return boris_main()


if __name__ == "__main__":
    sys.exit(main())
