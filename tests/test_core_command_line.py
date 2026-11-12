"""Importing core must preserve its caller's arguments and exception hook."""

import os
import subprocess
import sys
from pathlib import Path

import pytest


@pytest.mark.parametrize("arguments", [["--collect-only", "-q"], ["--version"], ["--help"]])
def test_import_leaves_caller_state_alone(arguments):
    root = Path(__file__).resolve().parents[1]
    environment = os.environ.copy()
    environment["PYTHONPATH"] = str(root) + os.pathsep + environment.get("PYTHONPATH", "")
    result = subprocess.run(
        [
            sys.executable,
            "-c",
            (
                "import sys; from PySide6.QtWidgets import QApplication; "
                "app = QApplication([]); "
                "sys.argv = ['caller', *sys.argv[1:]]; "
                "original = sys.argv[:]; "
                "original_hook = sys.excepthook; "
                "from boris import core; "
                "import_hook = sys.excepthook; "
                "sys.excepthook = original_hook; "
                "assert import_hook is original_hook; "
                "assert sys.argv == original; "
                "assert core.MainWindow.no_first_launch_dialog is False; "
                "print('import-complete')"
            ),
            *arguments,
        ],
        cwd=root,
        env=environment,
        capture_output=True,
        text=True,
        timeout=30,
        check=False,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert result.stdout.strip() == "import-complete"


def test_main_still_handles_version(monkeypatch, capsys):
    from boris import core

    monkeypatch.setattr(sys, "argv", ["boris", "--version"])
    with pytest.raises(SystemExit) as exit_info:
        core.main()
    assert exit_info.value.code == 0
    assert capsys.readouterr().out == f"version {core.__version__} release date: {core.__version_date__}\n"


def test_main_still_rejects_unknown_options(monkeypatch, capsys):
    from boris import core

    monkeypatch.setattr(sys, "argv", ["boris", "--not-a-boris-option"])
    with pytest.raises(SystemExit) as exit_info:
        core.main()
    assert exit_info.value.code == 2
    assert "no such option: --not-a-boris-option" in capsys.readouterr().err


@pytest.mark.parametrize("arguments, expected", [([], False), (["--no-first-launch-dialog"], True)])
def test_main_applies_first_launch_option_before_starting_gui(monkeypatch, arguments, expected):
    from boris import core

    class StopBeforeGui(Exception):
        pass

    def check_option_and_stop(*args):
        assert core.MainWindow.no_first_launch_dialog is expected
        assert sys.excepthook is core.excepthook
        raise StopBeforeGui

    monkeypatch.setattr(sys, "excepthook", sys.__excepthook__)
    monkeypatch.setattr(sys, "argv", ["boris", *arguments])
    monkeypatch.setattr(core.MainWindow, "no_first_launch_dialog", not expected)
    monkeypatch.setattr(core, "QApplication", check_option_and_stop)
    with pytest.raises(StopBeforeGui):
        core.main()
