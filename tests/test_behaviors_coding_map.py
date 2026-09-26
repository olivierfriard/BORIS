from types import SimpleNamespace

import pytest
from PySide6.QtCore import QBuffer, QEvent, QIODevice, QPoint, QPointF, Qt
from PySide6.QtGui import QColor, QMouseEvent, QPixmap

from boris import behaviors_coding_map, config as cfg


def bitmap_data():
    pixmap = QPixmap(20, 20)
    pixmap.fill(QColor("white"))
    buffer = QBuffer()
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    assert pixmap.save(buffer, "PNG")
    return bytes(buffer.data().toBase64()).decode()


def coding_map():
    return {
        "name": "Map",
        "bitmap": bitmap_data(),
        "areas": {
            "first": {"code": "A", "geometry": [(0, 0), (10, 0), (10, 10), (0, 10)], "color": QColor("red").rgba()},
            "second": {"code": "B", "geometry": [(5, 5), (15, 5), (15, 15), (5, 15)], "color": QColor("blue").rgba()},
        },
    }


def mouse_event(event_type, position=QPointF(1, 1)):
    return QMouseEvent(
        event_type,
        position,
        position,
        position,
        Qt.MouseButton.LeftButton if event_type == QEvent.Type.MouseButtonPress else Qt.MouseButton.NoButton,
        Qt.MouseButton.LeftButton if event_type == QEvent.Type.MouseButtonPress else Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.NoModifier,
    )


@pytest.fixture
def map_window(qapp):
    window = behaviors_coding_map.BehaviorsCodingMapWindowClass(coding_map(), idx=3)
    yield window
    window.close()
    window.deleteLater()
    qapp.processEvents()


def test_window_loads_bitmap_polygons_and_title(map_window):
    assert map_window.windowTitle() == "Behaviors coding map: Map"
    assert map_window.idx == 3
    assert len(map_window.polygonsList2) == 2
    assert [code for code, _ in map_window.polygonsList2] == ["A", "B"]
    assert map_window.polygonsList2[0][1].brush().color().name() == "#ff0000"
    assert map_window.polygonsList2[1][1].brush().color().name() == "#0000ff"
    assert len(map_window.view.scene().items()) == 3


def test_mouse_motion_and_click_report_all_matching_areas(monkeypatch, map_window):
    monkeypatch.setattr(map_window.view, "mapToScene", lambda _: QPointF(7, 7))
    clicked = []
    map_window.clickSignal.connect(lambda name, codes: clicked.append((name, codes)))
    event = SimpleNamespace(position=lambda: QPointF(1, 1))

    map_window.mouse_move_event(event)
    map_window.viewMousePressEvent(event)

    assert map_window.leareaCode.text() == "A, B"
    assert clicked == [("Map", ["A", "B"])]


def test_clicking_outside_an_area_does_not_emit_a_signal(monkeypatch, map_window):
    monkeypatch.setattr(map_window.view, "mapToScene", lambda _: QPointF(19, 19))
    clicked = []
    map_window.clickSignal.connect(lambda *args: clicked.append(args))

    map_window.viewMousePressEvent(SimpleNamespace(position=lambda: QPointF(1, 1)))

    assert clicked == []


def test_event_filters_forward_mouse_and_key_events(map_window):
    mouse_pressed, mouse_moved, keys = [], [], []
    map_window.view.mousePress.connect(mouse_pressed.append)
    map_window.view.mouseMove.connect(mouse_moved.append)
    map_window.keypressSignal.connect(keys.append)

    assert not map_window.view.eventFilter(map_window.view.viewport(), mouse_event(QEvent.Type.MouseMove))
    assert not map_window.view.eventFilter(map_window.view.viewport(), mouse_event(QEvent.Type.MouseButtonPress))
    key_event = QEvent(QEvent.Type.KeyPress)
    assert map_window.eventFilter(map_window, key_event)
    assert not map_window.eventFilter(map_window, QEvent(QEvent.Type.Enter))

    assert len(mouse_moved) == 1
    assert len(mouse_pressed) == 1
    assert mouse_moved[0].type() == QEvent.Type.MouseMove
    assert mouse_pressed[0].type() == QEvent.Type.MouseButtonPress
    assert keys == [key_event]


def test_close_event_emits_the_coding_map_name(map_window):
    closed = []
    map_window.close_signal.connect(closed.append)

    map_window.close()

    assert closed == ["Map"]


class SignalRecorder:
    def __init__(self):
        self.connected = []

    def connect(self, callback):
        self.connected.append(callback)


class FakeCodingMapWindow:
    def __init__(self, coding_map, idx):
        self.coding_map = coding_map
        self.idx = idx
        self.clickSignal = SignalRecorder()
        self.calls = []

    def resize(self, *size):
        self.calls.append(("resize", size))

    def setWindowFlags(self, flags):
        self.calls.append(("flags", flags))

    def show(self):
        self.calls.append(("show",))


def owner(maps):
    return SimpleNamespace(
        pj={cfg.BEHAVIORS_CODING_MAP: maps},
        bcm_dict={},
        click_signal_from_behaviors_coding_map=lambda *_: None,
    )


def test_show_map_warns_when_the_project_has_no_maps(monkeypatch):
    window = owner([])
    warnings = []
    monkeypatch.setattr(behaviors_coding_map.QMessageBox, "warning", lambda *args: warnings.append(args))

    behaviors_coding_map.show_behaviors_coding_map(window)

    assert "No behaviors coding map" in warnings[0][2]


def test_show_map_creates_then_reuses_the_single_available_window(monkeypatch):
    window = owner([coding_map()])
    monkeypatch.setattr(behaviors_coding_map, "BehaviorsCodingMapWindowClass", FakeCodingMapWindow)

    behaviors_coding_map.show_behaviors_coding_map(window)
    created = window.bcm_dict["Map"]
    behaviors_coding_map.show_behaviors_coding_map(window)

    assert created.idx == 0
    assert len(created.clickSignal.connected) == 1
    assert created.calls == [
        ("resize", (cfg.CODING_MAP_RESIZE_W, cfg.CODING_MAP_RESIZE_W)),
        ("flags", Qt.WindowType.WindowStaysOnTopHint),
        ("show",),
        ("show",),
    ]


def test_show_map_selects_requested_map_or_stops_when_selection_is_cancelled(monkeypatch):
    first = coding_map()
    second = {**coding_map(), "name": "Second map"}
    window = owner([first, second])
    monkeypatch.setattr(behaviors_coding_map, "BehaviorsCodingMapWindowClass", FakeCodingMapWindow)
    monkeypatch.setattr(behaviors_coding_map.QInputDialog, "getItem", lambda *_: ("Second map", True))

    behaviors_coding_map.show_behaviors_coding_map(window)

    assert window.bcm_dict["Second map"].idx == 1

    cancelled_window = owner([first, second])
    monkeypatch.setattr(behaviors_coding_map.QInputDialog, "getItem", lambda *_: ("", False))
    behaviors_coding_map.show_behaviors_coding_map(cancelled_window)
    assert cancelled_window.bcm_dict == {}
