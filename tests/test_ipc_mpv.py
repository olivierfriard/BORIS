"""Regression tests for IPC logging and the existing persistent socket protocol."""

import json
import subprocess
from unittest.mock import Mock

import pytest

from boris import ipc_mpv


@pytest.fixture
def player(tmp_path, monkeypatch):
    """Create an IPC player without starting an external process.

    Function written by Codex - ChatGPT 6.
    """
    monkeypatch.setattr(ipc_mpv.subprocess, "Popen", Mock())
    return ipc_mpv.IPC_MPV(socket_path=str(tmp_path / "mpvsocket0"))


def test_process_uses_a_log_file_instead_of_unread_pipes(player):
    """Verify mpv output cannot fill an unread pipe and block playback.

    Function written by Codex - ChatGPT 6.
    """
    args, kwargs = ipc_mpv.subprocess.Popen.call_args
    assert "--quiet" in args[0]
    assert kwargs["stdin"] == subprocess.DEVNULL
    assert kwargs["stderr"] == subprocess.STDOUT
    assert kwargs["stdout"].name == player.log_path
    assert kwargs["stdout"].closed
    assert player.RESPONSE_TIMEOUT == 2.0


def test_log_tail_returns_only_the_last_lines(player, tmp_path):
    """Keep only the requested diagnostic lines, including invalid bytes.

    Function written by Codex - ChatGPT 6.
    """
    (tmp_path / "mpvsocket0.log").write_bytes(b"first\nsecond\nlast\xff\n")
    assert player.log_tail(2) == "second\nlast\ufffd\n"


def test_log_tail_tolerates_a_missing_file(player, tmp_path):
    """Allow startup errors to be reported even when the log is missing.

    Function written by Codex - ChatGPT 6.
    """
    (tmp_path / "mpvsocket0.log").unlink()
    assert player.log_tail() == ""


def test_command_preserves_request_ids_and_handles_split_responses(player):
    """Retain dsanmiguel's buffering, event filtering, and response matching.

    Function written by Codex - ChatGPT 6.
    """
    player._sock = Mock()
    player._sock.recv.side_effect = [
        b'{"event":"tick"}\n{"request_id":2,"error":"success","data":20}\n{"request_',
        b'id":1,"error":"success","data":10}\n',
    ]

    assert player.send_command({"command": ["get_property", "time-pos"]}) == 10
    assert player.send_command({"command": ["get_property", "duration"]}) == 20
    commands = [json.loads(call.args[0]) for call in player._sock.sendall.call_args_list]
    assert [command["request_id"] for command in commands] == [1, 2]
    assert player._sock.recv.call_count == 2


def test_command_keeps_the_socket_after_an_unavailable_property(player):
    """A property that is not ready must not close the persistent socket.

    Function written by Codex - ChatGPT 6.
    """
    player._sock = Mock()
    player._sock.recv.return_value = b'{"request_id":1,"error":"property unavailable"}\n'
    assert player.send_command({"command": ["get_property", "time-pos"]}) is None
    player._sock.close.assert_not_called()
