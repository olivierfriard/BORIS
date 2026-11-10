"""Check launcher behavior in fresh processes, before Qt initializes."""

import os
from pathlib import Path
import subprocess
import sys

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
PROBE = r'''
import builtins
import importlib
from pathlib import Path
import runpy
import sys
import tomllib
from types import SimpleNamespace

platform, entrypoint, bundle_mode = sys.argv[1:]
script = tomllib.loads(Path("pyproject.toml").read_text())["project"]["scripts"]["boris"]
import boris.launcher as launcher
assert "PySide6" not in sys.modules
assert "boris.core" not in sys.modules
sys.platform = platform
sys.argv = ["boris", "--nosplashscreen", "example.boris"]
arguments = sys.argv[:]
if entrypoint == "script":
    arguments[0] = "start_boris.py"
events = []
info = {} if bundle_mode == "normal" else None if bundle_mode == "missing" else ()
sys.modules["Foundation"] = None if bundle_mode == "no_foundation" else SimpleNamespace(
    NSBundle=SimpleNamespace(mainBundle=lambda: SimpleNamespace(infoDictionary=lambda: info)),
    NSProcessInfo=SimpleNamespace(
        processInfo=lambda: SimpleNamespace(setProcessName_=lambda name: events.append(("process", name)))
    ),
)
sys.modules["PySide6"] = SimpleNamespace()
sys.modules["PySide6.QtCore"] = SimpleNamespace(
    QCoreApplication=SimpleNamespace(setApplicationName=lambda name: events.append(("application", name)))
)
sys.modules["PySide6.QtGui"] = SimpleNamespace(
    QGuiApplication=SimpleNamespace(setApplicationDisplayName=lambda name: events.append(("display", name)))
)
original_import = builtins.__import__


def checked_import(name, globals=None, locals=None, fromlist=(), level=0):
    """Verify initialization order without loading the real GUI.

    Function written by Codex - GPT-6.
    """
    if name.startswith("PySide6") and platform == "darwin":
        assert info == {"CFBundleName": "BORIS", "CFBundleDisplayName": "BORIS"}
        assert ("process", "BORIS") in events
    if name == "core" and level == 1:
        expected = [("application", "BORIS"), ("display", "BORIS")]
        assert events == ([("process", "BORIS")] if platform == "darwin" else []) + expected
        assert sys.argv == arguments
        events.append(("core", "started"))
        return SimpleNamespace(main=lambda: 17)
    return original_import(name, globals, locals, fromlist, level)


builtins.__import__ = checked_import
if entrypoint == "console":
    module, function = script.split(":")
    result = getattr(importlib.import_module(module), function)()
elif entrypoint == "launcher":
    result = launcher.main()
else:
    try:
        if entrypoint == "script":
            runpy.run_path("start_boris.py", run_name="__main__")
        else:
            runpy.run_module("boris", run_name="__main__", alter_sys=False)
    except SystemExit as exc:
        result = exc.code
assert result == 17
assert events[-1] == ("core", "started")
'''


def run_probe(platform, entrypoint="launcher", bundle_mode="normal"):
    """Run launcher checks without sharing Qt or platform state with pytest.

    Function written by Codex - GPT-6.
    """
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(PROJECT_ROOT)
    return subprocess.run(
        [sys.executable, "-c", PROBE, platform, entrypoint, bundle_mode],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        env=environment,
    )


@pytest.mark.parametrize("platform", ["darwin", "linux", "win32"])
@pytest.mark.parametrize("entrypoint", ["launcher", "console", "script", "module"])
def test_launchers_configure_identity_before_loading_core(platform, entrypoint):
    """Check names, import order, arguments, and exit status for each launcher.

    Function written by Codex - GPT-6.
    """
    result = run_probe(platform, entrypoint)
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize(
    ("bundle_mode", "message"),
    [
        ("no_foundation", "The macOS launcher requires PyObjC"),
        ("missing", "the main bundle has no information dictionary"),
        ("readonly", "the main bundle information dictionary is not writable"),
    ],
)
def test_macos_configuration_errors_stop_startup(bundle_mode, message):
    """Report Cocoa configuration failures before starting BORIS.

    Function written by Codex - GPT-6.
    """
    result = run_probe("darwin", bundle_mode=bundle_mode)
    assert result.returncode != 0
    assert message in result.stderr
    assert "Traceback" not in result.stderr
