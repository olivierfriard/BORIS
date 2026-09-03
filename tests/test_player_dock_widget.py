"""Tests for player dock widget mouse events."""
# ruff: noqa: E402

import os
import sys
from types import SimpleNamespace

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "boris")))

from PySide6.QtCore import QPoint, Qt
from PySide6.QtTest import QSignalSpy, QTest
from PySide6.QtWidgets import QApplication

from boris.core import MainWindow
from boris.player_dock_widget import Clickable_video_frame


def application():
    """Return the application instance required by QWidget tests."""
    return QApplication.instance() or QApplication([])


def test_video_frame_emits_player_id_on_left_click():
    app = application()
    frame = Clickable_video_frame(3)
    frame.resize(100, 100)
    frame.show()
    spy = QSignalSpy(frame.left_clicked_signal)

    QTest.mouseClick(frame, Qt.MouseButton.LeftButton, pos=QPoint(10, 10))
    app.processEvents()

    assert spy.count() == 1
    assert spy.at(0) == [3]


def test_video_frame_ignores_right_click():
    app = application()
    frame = Clickable_video_frame(2)
    frame.resize(100, 100)
    frame.show()
    spy = QSignalSpy(frame.left_clicked_signal)

    QTest.mouseClick(frame, Qt.MouseButton.RightButton, pos=QPoint(10, 10))
    app.processEvents()

    assert spy.count() == 0


def test_left_click_command_selects_player():
    window = SimpleNamespace(current_player=0)

    MainWindow.player_clicked(window, 3, "MBTN_LEFT")

    assert window.current_player == 3
