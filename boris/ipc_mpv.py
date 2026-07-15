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

import json
import logging
import os
import socket
import subprocess
import threading
import time

import config as cfg

logger = logging.getLogger(__name__)


class IPC_MPV:
    """
    class for managing mpv through Inter Process Communication (IPC)
    """

    CONNECT_TIMEOUT = 2.0
    RESPONSE_TIMEOUT = 2.0
    RETRY_DELAY = 0.05
    LOAD_TIMEOUT = 5.0

    media_durations: list = []
    cumul_media_durations: list = []
    fps: list = []
    _pause: bool = False

    def __init__(self, socket_path: str = cfg.MPV_SOCKET, parent=None):
        self.socket_path = socket_path
        self.process = None
        self._sock = None
        self._recv_buffer = b""
        self._next_request_id = 1
        self._pending_responses = {}
        self._socket_lock = threading.RLock()
        self.init_mpv()

    def init_mpv(self):
        """
        Start mpv process and embed it in the PySide6 application.
        """
        with self._socket_lock:
            self._reset_connection(log_level="debug")
            self._remove_stale_socket_file()

            logger.info("Start mpv ipc process")
            self.process = subprocess.Popen(
                [
                    "mpv",
                    "--ontop",
                    "--no-border",
                    "--osc=no",  # no on screen commands
                    "--input-ipc-server=" + self.socket_path,
                    # "--wid=" + str(int(self.winId())),  # Embed in the widget
                    "--idle=yes",  # Keeps mpv running with no video
                    "--keep-open=always",
                    "--input-default-bindings=no",
                    "--input-vo-keyboard=no",
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )

    def _remove_stale_socket_file(self):
        if os.path.exists(self.socket_path):
            try:
                os.unlink(self.socket_path)
            except OSError as exc:
                logger.debug(f"Unable to remove stale mpv IPC socket {self.socket_path}: {exc}")

    def _reset_connection(self, reason: str = "", log_level: str = "warning"):
        if self._sock is not None:
            try:
                self._sock.close()
            except OSError:
                pass
        self._sock = None
        self._recv_buffer = b""
        self._pending_responses = {}

        if reason:
            getattr(logger, log_level)(reason)

    def close(self):
        with self._socket_lock:
            self._reset_connection(log_level="debug")

    def _ensure_process(self):
        if self.process is not None and self.process.poll() is not None:
            returncode = self.process.returncode
            logger.warning(f"mpv IPC process exited with code {returncode}; restarting")
            self.process = None
            self.init_mpv()

    def _connect_socket(self) -> bool:
        if self._sock is not None:
            return True

        self._ensure_process()

        deadline = time.monotonic() + self.CONNECT_TIMEOUT
        last_error = None

        while time.monotonic() < deadline:
            if not os.path.exists(self.socket_path):
                time.sleep(self.RETRY_DELAY)
                continue

            client = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
            client.settimeout(self.RESPONSE_TIMEOUT)

            try:
                client.connect(self.socket_path)
            except OSError as exc:
                last_error = exc
                client.close()
                time.sleep(self.RETRY_DELAY)
                continue

            self._sock = client
            self._recv_buffer = b""
            logger.debug(f"Connected to mpv IPC socket {self.socket_path}")
            return True

        if last_error is None:
            logger.warning(f"mpv IPC socket {self.socket_path} did not appear before timeout")
        else:
            logger.warning(f"Unable to connect to mpv IPC socket {self.socket_path}: {last_error}")
        return False

    def _next_id(self) -> int:
        request_id = self._next_request_id
        self._next_request_id += 1
        return request_id

    def _read_message(self) -> dict:
        # mpv JSON IPC is newline-delimited JSON over a stream socket. recv()
        # can return partial or multiple messages, so keep a byte buffer.
        while True:
            newline_idx = self._recv_buffer.find(b"\n")
            if newline_idx != -1:
                raw_message = self._recv_buffer[:newline_idx].strip()
                self._recv_buffer = self._recv_buffer[newline_idx + 1 :]
                if not raw_message:
                    continue

                try:
                    return json.loads(raw_message.decode("utf-8"))
                except json.JSONDecodeError as exc:
                    logger.warning(f"Invalid mpv IPC JSON message: {exc}")
                    continue

            chunk = self._sock.recv(4096)
            if not chunk:
                raise ConnectionError("mpv IPC socket closed by peer")
            self._recv_buffer += chunk

    def _read_response(self, request_id: int):
        if request_id in self._pending_responses:
            return self._pending_responses.pop(request_id)

        deadline = time.monotonic() + self.RESPONSE_TIMEOUT

        while time.monotonic() < deadline:
            response = self._read_message()
            response_request_id = response.get("request_id")

            if response_request_id == request_id:
                return response

            if response_request_id is not None:
                self._pending_responses[response_request_id] = response
                logger.debug(f"Queued out-of-order mpv IPC response for request_id={response_request_id}")
                continue

            logger.debug(f"Ignoring unsolicited mpv IPC message: {response}")

        raise TimeoutError(f"Timed out waiting for mpv IPC response request_id={request_id}")

    def send_command(self, command):
        """
        Send a JSON command to the mpv IPC server.
        """
        with self._socket_lock:
            request_id = self._next_id()
            payload = dict(command)
            payload["request_id"] = request_id

            for attempt in range(2):
                if not self._connect_socket():
                    if attempt == 0 and self.process is not None and self.process.poll() is not None:
                        self.init_mpv()
                        continue
                    return None

                try:
                    self._sock.sendall(json.dumps(payload).encode("utf-8") + b"\n")
                    response_data = self._read_response(request_id)
                    if response_data.get("error") not in ("success", "property unavailable"):
                        logger.warning(f"mpv IPC command failed: command={command} response={response_data}")
                    elif response_data.get("error") == "property unavailable":
                        logger.debug(f"mpv IPC property unavailable: command={command}")
                    return response_data.get("data")
                except (BrokenPipeError, ConnectionError, OSError, TimeoutError) as exc:
                    logger.warning(f"mpv IPC command transport error: command={command} error={exc}")
                    self._reset_connection(reason="Resetting mpv IPC connection after transport failure", log_level="debug")

                    if self.process is not None and self.process.poll() is not None and attempt == 0:
                        self.init_mpv()
                    elif attempt == 0:
                        continue

        return None

    @property
    def time_pos(self):
        time_pos = self.send_command({"command": ["get_property", "time-pos"]})
        return time_pos

    @property
    def duration(self):
        duration_ = self.send_command({"command": ["get_property", "duration"]})
        return duration_

    @property
    def video_zoom(self):
        return self.send_command({"command": ["get_property", "video-zoom"]})

    @video_zoom.setter
    def video_zoom(self, value):
        self.send_command({"command": ["set_property", "video-zoom", value]})
        return

    @property
    def pause(self):
        return self.send_command({"command": ["get_property", "pause"]})

    @pause.setter
    def pause(self, value):
        return self.send_command({"command": ["set_property", "pause", value]})

    @property
    def mute(self):
        return self.send_command({"command": ["get_property", "mute"]})

    @mute.setter
    def mute(self, value):
        return self.send_command({"command": ["set_property", "mute", value]})

    @property
    def estimated_frame_number(self):
        return self.send_command({"command": ["get_property", "estimated-frame-number"]})

    def stop(self):
        self.send_command({"command": ["stop"]})
        return

    @property
    def playlist(self):
        return self.send_command({"command": ["get_property", "playlist"]})

    def playlist_next(self):
        self.send_command({"command": ["playlist-next"]})
        return

    def playlist_prev(self):
        self.send_command({"command": ["playlist-prev"]})
        return

    @property
    def playlist_pos(self):
        return self.send_command({"command": ["get_property", "playlist-pos"]})

    @playlist_pos.setter
    def playlist_pos(self, value):
        return self.send_command({"command": ["set_property", "playlist-pos", value]})

    @property
    def playlist_count(self):
        return self.send_command({"command": ["get_property", "playlist-count"]})

    def playlist_append(self, media):
        return self.send_command({"command": ["loadfile", media, "append"]})

    def wait_until_playing(self):
        deadline = time.monotonic() + self.LOAD_TIMEOUT

        while time.monotonic() < deadline:
            playlist_count = self.playlist_count
            duration = self.duration
            if playlist_count and duration is not None:
                return True
            time.sleep(self.RETRY_DELAY)

        logger.debug(f"Timed out waiting for mpv IPC media readiness on {self.socket_path}")
        return False

    def seek(self, value, mode: str):
        self.send_command({"command": ["seek", value, mode]})
        return

    @property
    def playback_time(self):
        playback_time_ = self.send_command({"command": ["get_property", "playback-time"]})
        return playback_time_

    def frame_step(self):
        self.send_command({"command": ["frame-step"]})
        return

    def frame_back_step(self):
        self.send_command({"command": ["frame-back-step"]})
        return

    def screenshot_to_file(self, value):
        self.send_command({"command": ["screenshot-to-file", value, "video"]})
        return

    @property
    def speed(self):
        return self.send_command({"command": ["get_property", "speed"]})

    @speed.setter
    def speed(self, value):
        self.send_command({"command": ["set_property", "speed", value]})
        return

    @property
    def video_rotate(self):
        return self.send_command({"command": ["get_property", "video-rotate"]})

    @video_rotate.setter
    def video_rotate(self, value):
        self.send_command({"command": ["set_property", "video-rotate", value]})
        return

    @property
    def sub_visibility(self):
        return self.send_command({"command": ["get_property", "sub-visibility"]})

    @sub_visibility.setter
    def sub_visibility(self, value):
        self.send_command({"command": ["set_property", "sub-visibility", value]})
        return

    @property
    def brightness(self):
        return self.send_command({"command": ["get_property", "brightness"]})

    @brightness.setter
    def brightness(self, value):
        self.send_command({"command": ["set_property", "brightness", value]})
        return

    @property
    def contrast(self):
        return self.send_command({"command": ["get_property", "contrast"]})

    @contrast.setter
    def contrast(self, value):
        self.send_command({"command": ["set_property", "contrast", value]})
        return

    @property
    def saturation(self):
        return self.send_command({"command": ["get_property", "saturation"]})

    @saturation.setter
    def saturation(self, value):
        self.send_command({"command": ["set_property", "saturation", value]})
        return

    @property
    def gamma(self):
        return self.send_command({"command": ["get_property", "gamma"]})

    @gamma.setter
    def gamma(self, value):
        self.send_command({"command": ["set_property", "gamma", value]})
        return

    @property
    def hue(self):
        return self.send_command({"command": ["get_property", "hue"]})

    @hue.setter
    def hue(self, value):
        self.send_command({"command": ["set_property", "hue", value]})
        return

    @property
    def container_fps(self):
        return self.send_command({"command": ["get_property", "container-fps"]})

    @property
    def width(self):
        return self.send_command({"command": ["get_property", "width"]})

    @property
    def height(self):
        return self.send_command({"command": ["get_property", "height"]})

    @property
    def video_format(self):
        return self.send_command({"command": ["get_property", "video-format"]})

    @property
    def deinterlace(self):
        return self.send_command({"command": ["get_property", "deinterlace"]})

    @deinterlace.setter
    def deinterlace(self, value):
        self.send_command({"command": ["set_property", "deinterlace", value]})
        return

    @property
    def audio_bitrate(self):
        return self.send_command({"command": ["get_property", "audio-bitrate"]})

    @property
    def eof_reached(self):
        return self.send_command({"command": ["get_property", "eof-reached"]})

    @property
    def core_idle(self):
        return self.send_command({"command": ["get_property", "core-idle"]})

    @property
    def video_pan_x(self):
        return self.send_command({"command": ["get_property", "video-pan-x"]})

    @video_pan_x.setter
    def video_pan_x(self, value):
        self.send_command({"command": ["set_property", "video-pan-x", value]})
        return

    @property
    def video_pan_y(self):
        return self.send_command({"command": ["get_property", "video-pan-y"]})

    @video_pan_y.setter
    def video_pan_y(self, value):
        self.send_command({"command": ["set_property", "video-pan-y", value]})
        return

    """
    @property
    def xxx(self):
        return self.send_command({"command": ["get_property", "xxx"]})

    @xxx.setter
    def xxx(self, value):
        self.send_command({"command": ["set_property", "xxx", value]})
        return
    """
