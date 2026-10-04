"""Test the macOS render lifecycle without requiring a native OpenGL context."""

import ctypes
import importlib.util
from functools import partial
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, call

import pytest

from boris import mpv2, player_dock_widget


@pytest.fixture
def renderer(monkeypatch):
    """Load the renderer with a stand-in for the macOS OpenGL framework.

    Function written by Codex - ChatGPT 6.
    """
    path = Path(__file__).resolve().parents[1] / "boris" / "video_render_widget.py"
    spec = importlib.util.spec_from_file_location("boris._test_video_render_widget", path)
    module = importlib.util.module_from_spec(spec)
    with monkeypatch.context() as patch:
        patch.setattr(ctypes, "CDLL", Mock())
        spec.loader.exec_module(module)
    return module


def test_application_shutdown_releases_context_before_terminating_player(renderer, monkeypatch):
    """Release each context before its player, and allow repeated cleanup.

    Function written by Codex - ChatGPT 6.
    """
    events = Mock()
    player = SimpleNamespace(handle=True, terminate=events.terminate)
    context = SimpleNamespace(free=events.free)
    widget = SimpleNamespace(
        player=player,
        _render_ctx=context,
        makeCurrent=events.makeCurrent,
        doneCurrent=events.doneCurrent,
    )
    widget._free_render_context = partial(renderer.VideoRenderWidget._free_render_context, widget)
    widget.release_render_context = partial(renderer.VideoRenderWidget.release_render_context, widget)
    monkeypatch.setattr(renderer, "_widgets", [widget])

    renderer.release_all()
    renderer.release_all()

    assert events.mock_calls == [call.makeCurrent(), call.free(), call.doneCurrent(), call.terminate()]
    assert widget.player is None
    assert widget._render_ctx is None


def test_dock_release_detaches_the_player_from_the_render_widget():
    """Do not terminate an observation's player again at application shutdown.

    Function written by Codex - ChatGPT 6.
    """
    video = SimpleNamespace(player=object(), release_render_context=Mock())
    dock = SimpleNamespace(videoframe=video)

    player_dock_widget.DW_player.release_video_output(dock)

    video.release_render_context.assert_called_once_with()
    assert video.player is None


def test_screenshot_waits_for_render_work_instead_of_blocking_the_gui(renderer):
    """Screenshots must process the render work needed by asynchronous mpv commands.

    Function written by Codex - ChatGPT 6.
    """
    future = object()
    video = SimpleNamespace(process_render_work_until_done=Mock(return_value="screenshot"))
    player = SimpleNamespace(_video_widget=video, command_async=Mock(return_value=future))

    result = renderer.EmbeddedMPV.command(player, "screenshot-to-file", "frame.png")

    assert result == "screenshot"
    player.command_async.assert_called_once_with("screenshot-to-file", "frame.png", decoder=mpv2.strict_decoder)
    video.process_render_work_until_done.assert_called_once_with(future)
