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


Video widget for macOS

On macOS mpv can not draw into the window of another process and the --wid option of libmpv
does not work with Qt widgets. The video is drawn in a QOpenGLWidget with the mpv render API instead.

The player is an EmbeddedMPV (see player_dock_widget.py).
The render context must be released (release_render_context) before the mpv player is terminated.
"""

import ctypes
import logging
import time
import weakref

from PySide6.QtCore import QCoreApplication, QElapsedTimer, QEventLoop, Qt, Signal
from PySide6.QtGui import QSurfaceFormat
from PySide6.QtOpenGLWidgets import QOpenGLWidget

from . import mpv2 as mpv

logger = logging.getLogger(__name__)

GL_COLOR_BUFFER_BIT = 0x00004000

# number of wheel angle units for one wheel step (see QWheelEvent.angleDelta)
WHEEL_STEP = 120

# The screenshots (used for the geometric measurements and the frame extraction) are made by software
# and mpv can not use the frames decoded by VideoToolbox without copy-back.
# The copy-back adds about 5% of CPU usage of one core (1440x1080 H.264 video, Apple silicon)
HWDEC_COPY_BACK = {"auto": "auto-copy", "auto-safe": "auto-copy-safe"}

_opengl_lib = ctypes.CDLL("/System/Library/Frameworks/OpenGL.framework/OpenGL")

# all video widgets, for releasing them before BORIS quits
_widgets = weakref.WeakSet()


def _get_proc_address(_ctx, name: bytes):
    """
    returns the address of an OpenGL function (called by mpv)
    """
    try:
        return ctypes.cast(getattr(_opengl_lib, name.decode("ascii")), ctypes.c_void_p).value
    except AttributeError:
        return None


# keep a reference on the callback to prevent garbage collection
_get_proc_address_fn = mpv.MpvGlGetProcAddressFn(_get_proc_address)


def set_opengl_defaults() -> None:
    """
    Set the OpenGL defaults required by the video widgets.
    Must be called before the QApplication is created.
    """
    surface_format = QSurfaceFormat()
    surface_format.setVersion(3, 2)
    surface_format.setProfile(QSurfaceFormat.OpenGLContextProfile.CoreProfile)
    QSurfaceFormat.setDefaultFormat(surface_format)

    # keep the OpenGL context of the video widget when its dock widget is floated or docked again
    QCoreApplication.setAttribute(Qt.ApplicationAttribute.AA_ShareOpenGLContexts)


def release_all() -> None:
    """
    release the render contexts and terminate the mpv players of all video widgets
    """
    for widget in list(_widgets):
        widget.release_render_context()
        player, widget.player = widget.player, None
        if player is not None and player.handle:
            logger.info("Terminate mpv player")
            player.terminate()


class EmbeddedMPV(mpv.MPV):
    """
    libmpv player displayed in a VideoRenderWidget
    """

    def __init__(self, video_widget, **kwargs):
        # video-timing-offset=0: mpv sends the frames at their display time (see VideoRenderWidget.paintGL)
        super().__init__(vo="libmpv", video_timing_offset=0, **kwargs)
        self._video_widget = video_widget
        video_widget.set_player(self)

    def __setattr__(self, name, value):
        if name == "hwdec" and isinstance(value, str):
            value = HWDEC_COPY_BACK.get(value, value)
        super().__setattr__(name, value)

    def __getattr__(self, name):
        value = super().__getattr__(name)
        if name == "hwdec":
            # recent mpv versions return a list of hwdec APIs
            if isinstance(value, list):
                value = ",".join(value)
            # return the value of the BORIS preferences
            return next((k for k, v in HWDEC_COPY_BACK.items() if v == value), value)
        return value

    def command(self, name, *args, decoder=mpv.strict_decoder, **kwargs):
        if name.replace("_", "-").startswith("screenshot"):
            # The render context can be required for the screenshot and works only in the GUI thread:
            # a synchronous command would block the GUI thread and mpv forever
            future = self.command_async(name, *args, decoder=decoder, **kwargs)
            return self._video_widget.process_render_work_until_done(future)
        return super().command(name, *args, decoder=decoder, **kwargs)


class VideoRenderWidget(QOpenGLWidget):
    """
    Widget displaying the video of a libmpv player with the mpv render API.

    The mouse clicks and the wheel events are sent to mpv, so that the mpv key bindings
    (player.on_key_press) work like with a native mpv window.
    """

    _mpv_update_signal = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.player = None
        self._render_ctx = None
        self._vid_to_restore = None
        self._wheel_angle = 0
        self._mpv_update_signal.connect(self._mpv_update, Qt.ConnectionType.QueuedConnection)
        _widgets.add(self)

    def set_player(self, player) -> None:
        """
        set the mpv player (created with vo="libmpv") to display
        """
        self.player = player
        if self.isValid():
            self.makeCurrent()
            self._create_render_context()
            self.doneCurrent()

    def wait_until_ready(self, timeout: int = 5000) -> bool:
        """
        Wait until the widget has created its OpenGL context.
        mpv can not open the video of a media file before.

        Args:
            timeout (int): maximum waiting time in ms

        Returns:
            bool: True if the widget is ready to display the video
        """
        timer = QElapsedTimer()
        timer.start()
        while self._render_ctx is None and timer.elapsed() < timeout:
            QCoreApplication.processEvents(QEventLoop.ProcessEventsFlag.ExcludeUserInputEvents, 50)
        if self._render_ctx is None:
            logger.warning("The OpenGL context of the video widget is not available")
        return self._render_ctx is not None

    def release_render_context(self) -> None:
        """
        free the mpv render context. Must be done before terminating the mpv player
        """
        if self._render_ctx is None:
            return
        self.makeCurrent()
        self._free_render_context()
        self.doneCurrent()

    def _create_render_context(self) -> None:
        """
        create the mpv render context. The OpenGL context of the widget must be current
        """
        if self.player is None or self._render_ctx is not None:
            return
        logger.debug("Create mpv render context")
        self._render_ctx = mpv.MpvRenderContext(
            self.player,
            "opengl",
            opengl_init_params={"get_proc_address": _get_proc_address_fn},
        )
        # called by a mpv thread
        self._render_ctx.update_cb = self._mpv_update_signal.emit

        self._restore_video_track()

    def _restore_video_track(self) -> None:
        """
        mpv disables the video track if it was loaded without render context
        or if the previous render context was freed
        """
        vid, self._vid_to_restore = self._vid_to_restore, None
        try:
            if vid is None:
                tracks = [t for t in (self.player.track_list or []) if t.get("type") == "video"]
                if tracks and not any(t.get("selected") for t in tracks):
                    vid = next((t["id"] for t in tracks if not t.get("albumart")), None)
            if vid is not None:
                logger.debug(f"Restore video track {vid}")
                self.player.vid = vid
        except Exception as e:
            logger.warning(f"Error restoring the video track: {e}")

    def _free_render_context(self) -> None:
        """
        free the mpv render context. The OpenGL context of the widget must be current
        """
        logger.debug("Free mpv render context")
        render_ctx, self._render_ctx = self._render_ctx, None
        render_ctx.free()

    def _context_about_to_be_destroyed(self) -> None:
        """
        the OpenGL context of the widget will be destroyed (e.g. the widget changed of window).
        A new one will be created and initializeGL called again.
        """
        if self._render_ctx is None:
            return
        try:
            vid = self.player.vid
            if vid not in (None, False, "no"):
                self._vid_to_restore = vid
        except Exception as e:
            logger.debug(f"Video track not available: {e}")
        self.release_render_context()

    def _can_paint(self) -> bool:
        """
        Qt does not repaint a widget that is not visible
        """
        window = self.window()
        handle = window.windowHandle()
        return self.isVisible() and not window.isMinimized() and handle is not None and handle.isExposed()

    def process_render_work_until_done(self, future, timeout: float = 10.0):
        """
        Do the work of the render context in the GUI thread until the mpv command is done

        Args:
            future (Future): future of an asynchronous mpv command
            timeout (float): maximum waiting time in seconds

        Returns:
            the result of the mpv command
        """
        deadline = time.monotonic() + timeout
        while not future.done():
            if time.monotonic() > deadline:
                future.cancel()
                raise TimeoutError("The mpv command was not completed")
            # the new frames are rendered at once because mpv can wait for them (e.g. screenshot after frame step)
            self._mpv_update(render_now=True)
            time.sleep(0.002)
        return future.result()

    def _mpv_update(self, render_now: bool = False) -> None:
        """
        mpv has a new frame to display or work to do on the render thread

        Args:
            render_now (bool): render the new frame at once instead of waiting for the next paint event
        """
        if self._render_ctx is None:
            return
        self.makeCurrent()
        try:
            new_frame = self._render_ctx.update()
            if new_frame and not self._can_paint():
                # consume the frame without drawing it: mpv waits for each frame to be rendered
                self._render_ctx.render(skip_rendering=True, block_for_target_time=False)
                new_frame = False
            elif new_frame and render_now:
                self._render()
        finally:
            self.doneCurrent()
        if new_frame:
            self.update()

    def initializeGL(self) -> None:
        self.context().aboutToBeDestroyed.connect(self._context_about_to_be_destroyed, Qt.ConnectionType.DirectConnection)
        self._create_render_context()

    def paintGL(self) -> None:
        if self._render_ctx is None:
            functions = self.context().functions()
            functions.glClearColor(0, 0, 0, 1)
            functions.glClear(GL_COLOR_BUFFER_BIT)
            return
        self._render()

    def _render(self) -> None:
        """
        render the current frame in the framebuffer of the widget. The OpenGL context of the widget must be current
        """
        ratio = self.devicePixelRatioF()
        self._render_ctx.render(
            flip_y=True,
            # do not block the GUI thread until the display time of the frame (video-timing-offset is 0)
            block_for_target_time=False,
            opengl_fbo={
                "w": round(self.width() * ratio),
                "h": round(self.height() * ratio),
                "fbo": self.defaultFramebufferObject(),
            },
        )

    def _mpv_key_name(self, key: str, modifiers) -> str:
        """
        returns the mpv name of key with modifiers (e.g. Shift+MBTN_LEFT)
        """
        prefix = ""
        if modifiers & Qt.KeyboardModifier.ShiftModifier:
            prefix += "Shift+"
        # Qt reports the Command key as ControlModifier and the Control key as MetaModifier
        if modifiers & (Qt.KeyboardModifier.ControlModifier | Qt.KeyboardModifier.MetaModifier):
            prefix += "Ctrl+"
        if modifiers & Qt.KeyboardModifier.AltModifier:
            prefix += "Alt+"
        return prefix + key

    def _send_mouse_position(self, position) -> None:
        """
        update the mpv mouse-pos property (in widget coordinates)
        """
        self.player.command("mouse", int(position.x()), int(position.y()))

    def _send_mouse_button(self, event, suffix: str = "") -> None:
        button = {
            Qt.MouseButton.LeftButton: "MBTN_LEFT",
            Qt.MouseButton.RightButton: "MBTN_RIGHT",
            Qt.MouseButton.MiddleButton: "MBTN_MID",
        }.get(event.button())
        if self.player is None or button is None:
            event.ignore()
            return
        self._send_mouse_position(event.position())
        self.player.keypress(self._mpv_key_name(button + suffix, event.modifiers()))
        event.accept()

    def mousePressEvent(self, event) -> None:
        self._send_mouse_button(event)

    def mouseDoubleClickEvent(self, event) -> None:
        self._send_mouse_button(event, "_DBL")

    def wheelEvent(self, event) -> None:
        if self.player is None:
            event.ignore()
            return
        delta = event.angleDelta()
        angle = delta.y()
        if not angle and event.modifiers() & Qt.KeyboardModifier.ShiftModifier:
            # macOS changes the vertical scrolling in horizontal scrolling when Shift is pressed
            angle = delta.x()
        if not angle:
            event.ignore()
            return
        event.accept()

        # accumulate the small angles sent by trackpads and send one mpv wheel event by step
        if (angle > 0) != (self._wheel_angle > 0):
            self._wheel_angle = 0
        self._wheel_angle += angle
        steps = int(self._wheel_angle / WHEEL_STEP)
        if not steps:
            return
        self._wheel_angle -= steps * WHEEL_STEP

        self._send_mouse_position(event.position())
        key_name = self._mpv_key_name("WHEEL_UP" if steps > 0 else "WHEEL_DOWN", event.modifiers())
        for _ in range(abs(steps)):
            self.player.keypress(key_name)
