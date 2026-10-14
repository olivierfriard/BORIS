"""Launch BORIS with its macOS and Qt names set before GUI initialization.

Run from the project directory:
    uv run launch_boris_macos.py [BORIS options]

PyObjC is needed only on macOS. Bundle metadata is changed in memory for this
process; no Python installation files or BORIS settings are changed.
"""

import sys


def configure_application_identity():
    if sys.platform == "darwin":
        try:
            from Foundation import NSBundle, NSProcessInfo
        except ImportError as exc:
            raise SystemExit(
                "The macOS launcher requires PyObjC. Run:\n"
                "uv run launch_boris_macos.py"
            ) from exc

        # Cocoa and Qt can cache the name during initialization, so update the
        # main bundle before importing Qt or creating an NSApplication.
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

    # BORIS owns QApplication creation, including its OpenGL initialization.
    # Keep sys.argv intact so its command-line options reach the usual parser.
    from boris import main as boris_main

    return boris_main()


if __name__ == "__main__":
    sys.exit(main())
