"""Tests for the behaviors coding map creator."""

import json
import runpy
import sys
import warnings
from types import SimpleNamespace

import pytest
from PySide6 import QtWidgets
from PySide6.QtCore import QEvent, QPoint, QPointF, Qt
from PySide6.QtGui import QColor, QMouseEvent, QPixmap, QPolygonF
from PySide6.QtWidgets import QGraphicsPolygonItem

from boris import behav_coding_map_creator, config


@pytest.fixture
def window(qapp):
    creator = behav_coding_map_creator.BehaviorsMapCreatorWindow(["A", "B"])
    creator.bcm_list = []
    creator.bitmapFileName = ""
    creator.mapName = ""
    creator.fileName = ""
    creator.flagNewArea = False
    creator.flag_map_changed = False
    creator.polygonsList2 = []
    creator.view.elList = []
    creator.view.points = []
    creator.view._start = None
    yield creator
    creator.flag_map_changed = False
    creator.close()
    creator.deleteLater()
    qapp.processEvents()


def test_creator_initial_state(window):
    assert window.codes_list == ["A", "B"]
    assert window.area_list.count() == 0
    assert not window.saveMapAction.isEnabled()
    assert not window.addToProject.isEnabled()


def add_area(window, code="A", points=((0, 0), (20, 0), (20, 20)), color=QColor("lime")):
    polygon = QGraphicsPolygonItem(QPolygonF([QPoint(*point) for point in points]))
    polygon.setBrush(color)
    window.view.scene().addItem(polygon)
    window.polygonsList2.append([code, polygon])
    window.update_area_list()
    return polygon


def set_bitmap(window, size=100):
    window.bitmapFileName = "bitmap.png"
    window.pixmap = QPixmap(size, size)
    window.pixmap.fill(QColor("white"))
    window.view.setSceneRect(0, 0, size, size)


def test_make_coding_map_dict_and_add_to_project(window, monkeypatch):
    set_bitmap(window)
    add_area(window)
    emitted = []
    window.mapName = "Map"
    window.signal_add_to_project.connect(emitted.append)

    window.add_to_project(None)

    assert emitted[0]["name"] == "Map"
    assert emitted[0]["areas"]["0"]["code"] == "A"
    assert emitted[0]["areas"]["0"]["geometry"] == [[0, 0], [20, 0], [20, 20]]
    assert emitted[0]["bitmap"]


def test_add_to_project_rejects_empty_maps(window, monkeypatch):
    messages = []
    monkeypatch.setattr(behav_coding_map_creator.QMessageBox, "critical", lambda *args: messages.append(args))

    window.add_to_project(None)

    assert "does not contain any behavior area" in messages[0][2]


def test_area_selection_editing_and_opacity(window, monkeypatch):
    polygon = add_area(window)
    window.area_list_item_click(window.area_list.item(0))
    monkeypatch.setattr(behav_coding_map_creator.QInputDialog, "getItem", lambda *_: ("B", True))

    window.edit_area_code()
    window.slAlpha_changed(60)

    assert window.leAreaCode.text() == "B"
    assert window.polygonsList2[0][0] == "B"
    assert polygon.brush().color().alpha() == int(0.6 * 255)
    assert not window.btDeleteArea.isHidden()


def test_choose_color_updates_selected_and_new_polygons(window, monkeypatch):
    polygon = add_area(window)
    window.selectedPolygon = polygon
    window.closedPolygon = QGraphicsPolygonItem()
    window.slAlpha.setValue(50)

    class ColorDialog:
        DontUseNativeDialog = 0

        def setWindowFlags(self, *_):
            pass

        def setOptions(self, *_):
            pass

        def exec(self):
            return True

        def currentColor(self):
            return QColor("blue")

    monkeypatch.setattr(behav_coding_map_creator, "QColorDialog", ColorDialog)

    window.chooseColor()
    window.slAlpha_changed(55)

    assert polygon.brush().color().name() == "#0000ff"
    assert window.closedPolygon.brush().color().name() == "#0000ff"


def test_save_map_and_save_as_map(window, monkeypatch, tmp_path):
    set_bitmap(window)
    add_area(window)
    window.mapName = "Map"
    window.flag_map_changed = True
    file_name = tmp_path / "map.behav_coding_map"
    window.fileName = str(file_name)

    assert window.saveMap() is True
    assert json.loads(file_name.read_text())["name"] == "Map"
    assert window.flag_map_changed is False

    second_file = tmp_path / "map_copy"
    monkeypatch.setattr(behav_coding_map_creator.QFileDialog, "getSaveFileName", lambda *_: (str(second_file), ""))
    window.save_as_map_clicked()

    assert (tmp_path / "map_copy.behav_coding_map").is_file()


def test_save_map_clicked_handles_cancel_and_missing_extension(window, monkeypatch, tmp_path):
    set_bitmap(window)
    add_area(window)
    monkeypatch.setattr(behav_coding_map_creator.QFileDialog, "getSaveFileName", lambda *_: ("", ""))

    assert window.save_map_clicked() is False

    monkeypatch.setattr(
        behav_coding_map_creator.QFileDialog,
        "getSaveFileName",
        lambda *_: (str(tmp_path / "map"), ""),
    )
    assert window.save_map_clicked() is True
    assert (tmp_path / "map.behav_coding_map").is_file()


def test_open_map_loads_valid_data_and_rejects_invalid_files(window, monkeypatch, tmp_path):
    invalid_file = tmp_path / "invalid.map"
    invalid_file.write_text("not json")
    messages = []
    monkeypatch.setattr(behav_coding_map_creator.QMessageBox, "critical", lambda *args: messages.append(args))
    monkeypatch.setattr(behav_coding_map_creator.QFileDialog, "getOpenFileName", lambda *_: (str(invalid_file), ""))

    window.openMap()

    assert "not a behaviors coding map" in messages[0][2]

    set_bitmap(window)
    add_area(window)
    window.mapName = "Loaded"
    valid_file = tmp_path / "valid.behav_coding_map"
    valid_file.write_text(json.dumps(window.make_coding_map_dict()))
    window.cancelMap()
    monkeypatch.setattr(behav_coding_map_creator.QFileDialog, "getOpenFileName", lambda *_: (str(valid_file), ""))

    window.openMap()

    assert window.mapName == "Loaded"
    assert window.area_list.count() == 1
    assert window.addToProject.isEnabled()


def test_new_area_save_area_cancel_and_delete(window, monkeypatch):
    messages = []
    monkeypatch.setattr(behav_coding_map_creator.QMessageBox, "critical", lambda *args: messages.append(args))

    window.newArea()
    assert messages

    set_bitmap(window)
    window.newArea()
    assert window.flagNewArea is True
    assert not window.btSaveArea.isHidden()

    window.saveArea()
    assert any("must close your area" in message[2] for message in messages)

    polygon = QGraphicsPolygonItem(QPolygonF([QPoint(0, 0), QPoint(10, 0), QPoint(10, 10)]))
    window.view.scene().addItem(polygon)
    window.closedPolygon = polygon
    window.view.points = [(0, 0), (10, 0), (10, 10)]
    window.leAreaCode.setText("A")
    window.saveArea()

    assert window.area_list.count() == 1
    assert window.flag_map_changed is True

    window.area_list_item_click(window.area_list.item(0))
    window.deleteArea()
    assert not window.polygonsList2

    window.closedPolygon = QGraphicsPolygonItem()
    window.view.scene().addItem(window.closedPolygon)
    window.view.elList = [QGraphicsPolygonItem()]
    window.view.scene().addItem(window.view.elList[0])
    window.cancelAreaCreation()
    assert window.closedPolygon is None
    assert window.view.points == []


def test_map_name_new_map_and_close_event(window, monkeypatch):
    errors = []
    window.bcm_list = ["EXISTING"]
    monkeypatch.setattr(behav_coding_map_creator.QMessageBox, "critical", lambda *args: errors.append(args))
    name_answers = iter([("existing", True), ("New map", True)])
    monkeypatch.setattr(behav_coding_map_creator.QInputDialog, "getText", lambda *_: next(name_answers))

    window.mapName_clicked()
    assert window.mapName == "New map"
    assert errors

    loaded = []
    monkeypatch.setattr(behav_coding_map_creator.QInputDialog, "getText", lambda *_: ("Another", True))
    monkeypatch.setattr(window, "loadBitmap", lambda: loaded.append(True))
    window.newMap()
    assert window.mapName == "Another"
    assert loaded == [True]

    class CloseEvent:
        def __init__(self):
            self.accepted = False
            self.ignored = False

        def accept(self):
            self.accepted = True

        def ignore(self):
            self.ignored = True

    window.flag_map_changed = True
    monkeypatch.setattr(behav_coding_map_creator.dialog, "MessageDialog", lambda *_: config.CANCEL)
    event = CloseEvent()
    window.closeEvent(event)
    assert event.ignored

    monkeypatch.setattr(behav_coding_map_creator.dialog, "MessageDialog", lambda *_: config.DISCARD)
    event = CloseEvent()
    window.closeEvent(event)
    assert event.accepted


def test_load_bitmap_resize_and_cancel_map(window, monkeypatch, tmp_path):
    image_path = tmp_path / "bitmap.png"
    pixmap = QPixmap(20, 10)
    pixmap.fill(QColor("white"))
    assert pixmap.save(str(image_path))
    monkeypatch.setattr(behav_coding_map_creator.QFileDialog, "getOpenFileName", lambda *_: (str(image_path), ""))

    window.loadBitmap()
    assert window.bitmapFileName == str(image_path)
    assert window.saveMapAction.isEnabled()

    info = []
    monkeypatch.setattr(behav_coding_map_creator.QMessageBox, "information", lambda *args: info.append(args))
    monkeypatch.setattr(behav_coding_map_creator.QInputDialog, "getInt", lambda *_args, **_kwargs: (100, True))
    window.resize_clicked()
    assert window.pixmap.size().width() == 100
    assert info

    add_area(window)
    monkeypatch.setattr(behav_coding_map_creator.dialog, "MessageDialog", lambda *_: config.NO)
    window.resize_clicked()
    assert window.polygonsList2

    window.cancelMap()
    assert not window.polygonsList2
    assert not window.saveMapAction.isEnabled()


def test_mouse_selection_and_polygon_creation(window, monkeypatch):
    set_bitmap(window)
    window.view.mapToScene = lambda point: QPointF(point)

    class MouseEvent:
        def __init__(self, point, button):
            self.point = QPoint(*point)
            self.button = button

        def pos(self):
            return self.point

        def buttons(self):
            return self.button

    area = add_area(window, points=((0, 0), (30, 0), (30, 30), (0, 30)))
    window.viewMousePressEvent(MouseEvent((10, 10), Qt.LeftButton))
    assert window.selectedPolygon == area

    window.flagNewArea = True
    window.viewMousePressEvent(MouseEvent((40, 40), Qt.LeftButton))
    window.viewMousePressEvent(MouseEvent((60, 40), Qt.LeftButton))
    window.viewMousePressEvent(MouseEvent((60, 60), Qt.LeftButton))
    window.viewMousePressEvent(MouseEvent((60, 60), Qt.MiddleButton))
    assert window.closedPolygon is not None

    window.closedPolygon = None
    window.viewMousePressEvent(MouseEvent((40, 40), Qt.RightButton))
    assert len(window.view.points) == 2


def test_entry_point_requires_project_and_shows_creator(monkeypatch):
    warnings = []
    owner = SimpleNamespace(project=False)
    monkeypatch.setattr(behav_coding_map_creator.QMessageBox, "warning", lambda *args: warnings.append(args))

    behav_coding_map_creator.behaviors_coding_map_creator(owner)

    assert warnings

    shown = []

    class Creator:
        def __init__(self, codes):
            self.codes = codes
            self.signal_add_to_project = SimpleNamespace(connect=lambda callback: None)
            self.bcm_list = []

        def move(self, *_):
            pass

        def resize(self, *_):
            pass

        def show(self):
            shown.append(True)

    owner = SimpleNamespace(
        project=True,
        pj={config.ETHOGRAM: {"0": {config.BEHAVIOR_CODE: "A"}}},
        pos=lambda: QPoint(0, 0),
        behaviors_coding_map_creator_signal_addtoproject=lambda *_: None,
    )
    monkeypatch.setattr(behav_coding_map_creator, "BehaviorsMapCreatorWindow", Creator)

    behav_coding_map_creator.behaviors_coding_map_creator(owner)

    assert owner.mapCreatorWindow.codes == ["A"]
    assert shown == [True]


def test_map_name_and_new_map_cancellation_paths(window, monkeypatch):
    monkeypatch.setattr(behav_coding_map_creator.QInputDialog, "getText", lambda *_: ("", False))
    window.mapName_clicked()

    window.flag_map_changed = True
    monkeypatch.setattr(behav_coding_map_creator.dialog, "MessageDialog", lambda *_: config.CANCEL)
    window.newMap()
    assert window.flag_map_changed is True

    monkeypatch.setattr(behav_coding_map_creator.dialog, "MessageDialog", lambda *_: config.SAVE)
    monkeypatch.setattr(window, "save_map_clicked", lambda: False)
    window.newMap()

    window.flag_map_changed = False
    monkeypatch.setattr(behav_coding_map_creator.QInputDialog, "getText", lambda *_: ("", False))
    window.newMap()


def test_open_map_cancellation_and_invalid_type(window, monkeypatch, tmp_path):
    monkeypatch.setattr(behav_coding_map_creator.QFileDialog, "getOpenFileName", lambda *_: ("", ""))
    window.openMap()

    invalid_file = tmp_path / "wrong_type.behav_coding_map"
    invalid_file.write_text(json.dumps({"coding_map_type": "other"}))
    messages = []
    monkeypatch.setattr(behav_coding_map_creator.QMessageBox, "critical", lambda *args: messages.append(args))
    monkeypatch.setattr(behav_coding_map_creator.QFileDialog, "getOpenFileName", lambda *_: (str(invalid_file), ""))
    window.openMap()

    assert "not a BORIS behaviors coding map" in messages[0][2]


def test_close_event_save_failure_and_save_map_without_filename(window, monkeypatch):
    class CloseEvent:
        def __init__(self):
            self.ignored = False
            self.accepted = False

        def ignore(self):
            self.ignored = True

        def accept(self):
            self.accepted = True

    assert window.saveMap() is False
    window.flag_map_changed = True
    monkeypatch.setattr(behav_coding_map_creator.dialog, "MessageDialog", lambda *_: config.SAVE)
    monkeypatch.setattr(window, "save_map_clicked", lambda: False)
    event = CloseEvent()
    window.closeEvent(event)

    assert event.ignored
    assert event.accepted


def test_new_area_validation_and_selected_area_reset(window, monkeypatch):
    set_bitmap(window)
    selected = add_area(window)
    window.selectedPolygon = selected
    window.newArea()
    assert window.selectedPolygon is None

    messages = []
    monkeypatch.setattr(behav_coding_map_creator.QMessageBox, "critical", lambda *args: messages.append(args))
    window.closedPolygon = QGraphicsPolygonItem(QPolygonF([QPoint(0, 0), QPoint(10, 0), QPoint(10, 10)]))
    window.view.points = [(0, 0), (10, 0), (10, 10)]
    window.saveArea()

    assert "define a code" in messages[-1][2]


def test_mouse_outside_empty_selection_and_polygon_errors(window, monkeypatch):
    class MouseEvent:
        def __init__(self, point, button):
            self.point = QPoint(*point)
            self.button = button

        def pos(self):
            return self.point

        def buttons(self):
            return self.button

    window.viewMousePressEvent(MouseEvent((1, 1), Qt.LeftButton))
    set_bitmap(window)
    window.view.mapToScene = lambda point: QPointF(point)
    window.viewMousePressEvent(MouseEvent((-1, 0), Qt.LeftButton))

    selected = add_area(window)
    window.selectedPolygon = selected
    window.viewMousePressEvent(MouseEvent((80, 80), Qt.LeftButton))
    assert window.selectedPolygon is None

    messages = []
    window.flagNewArea = True
    window.view.points = [(10, 10), (40, 10), (40, 40)]
    window.view._start = QPoint(40, 40)
    monkeypatch.setattr(behav_coding_map_creator.util, "intersection", lambda *_: True)
    monkeypatch.setattr(behav_coding_map_creator.QMessageBox, "critical", lambda *args: messages.append(args))
    window.viewMousePressEvent(MouseEvent((10, 40), Qt.LeftButton))
    assert "can not be intersected" in messages[0][2]


def test_mouse_closes_polygon_when_clicking_near_first_point(window):
    class MouseEvent:
        def pos(self):
            return QPoint(5, 5)

        def buttons(self):
            return Qt.LeftButton

    set_bitmap(window)
    window.view.mapToScene = lambda point: QPointF(point)
    window.flagNewArea = True
    window.view.points = [(0, 0), (30, 0), (30, 30)]
    window.view._start = QPoint(30, 30)

    window.viewMousePressEvent(MouseEvent())

    assert window.closedPolygon is not None


def test_load_bitmap_and_resize_cancellation(window, monkeypatch):
    monkeypatch.setattr(behav_coding_map_creator.QFileDialog, "getOpenFileName", lambda *_: ("", ""))
    window.loadBitmap()
    assert not window.bitmapFileName

    set_bitmap(window)
    monkeypatch.setattr(behav_coding_map_creator.QInputDialog, "getInt", lambda *_args, **_kwargs: (100, False))
    window.resize_clicked()
    assert window.pixmap.size().width() == 100


def test_area_selection_replaces_selection_and_unknown_code_uses_first_choice(window, monkeypatch):
    add_area(window)
    window.area_list_item_click(window.area_list.item(0))
    window.area_list_item_click(window.area_list.item(0))
    window.leAreaCode.setText("unknown")
    window.selectedPolygon = None
    monkeypatch.setattr(behav_coding_map_creator.QInputDialog, "getItem", lambda *_: ("A", True))

    window.edit_area_code()

    assert window.leAreaCode.text() == "A"


def test_make_coding_map_dict_serializes_multiple_areas(window):
    set_bitmap(window)
    add_area(window, "A")
    add_area(window, "B", ((30, 0), (50, 0), (50, 20)))

    coding_map = window.make_coding_map_dict()

    assert list(coding_map["areas"]) == ["0", "1"]
    assert coding_map["areas"]["1"]["code"] == "B"


def test_save_as_map_cancellation(window, monkeypatch):
    monkeypatch.setattr(behav_coding_map_creator.QFileDialog, "getSaveFileName", lambda *_: ("", ""))

    assert window.save_as_map_clicked() is None


def test_new_map_duplicate_name_and_open_map_unsaved_cancellation(window, monkeypatch):
    errors = []
    window.bcm_list = ["EXISTING"]
    answers = iter([("existing", True), ("", False)])
    monkeypatch.setattr(behav_coding_map_creator.QInputDialog, "getText", lambda *_: next(answers))
    monkeypatch.setattr(behav_coding_map_creator.QMessageBox, "critical", lambda *args: errors.append(args))

    window.newMap()

    assert errors

    window.flag_map_changed = True
    monkeypatch.setattr(behav_coding_map_creator.dialog, "MessageDialog", lambda *_: "Cancel")
    window.openMap()
    monkeypatch.setattr(behav_coding_map_creator.dialog, "MessageDialog", lambda *_: "Save")
    monkeypatch.setattr(window, "save_map_clicked", lambda: False)
    window.openMap()


def test_save_area_removes_temporary_graphics(window, monkeypatch):
    set_bitmap(window)
    window.newArea()
    polygon = QGraphicsPolygonItem(QPolygonF([QPoint(0, 0), QPoint(10, 0), QPoint(10, 10)]))
    temporary_item = QGraphicsPolygonItem()
    window.view.scene().addItem(polygon)
    window.view.scene().addItem(temporary_item)
    window.closedPolygon = polygon
    window.view.points = [(0, 0), (10, 0), (10, 10)]
    window.view.elList = [temporary_item]
    window.leAreaCode.setText("A")

    window.saveArea()

    assert temporary_item.scene() is None


def test_mouse_handles_empty_right_click_and_legacy_middle_closure(window, monkeypatch):
    class MouseEvent:
        def __init__(self, point, button):
            self.point = QPoint(*point)
            self.button = button

        def pos(self):
            return self.point

        def buttons(self):
            return self.button

    class MiddleOnlyForEquality:
        def __and__(self, _):
            return 0

        def __eq__(self, other):
            return other == Qt.MiddleButton

    set_bitmap(window)
    window.view.mapToScene = lambda point: QPointF(point)
    window.flagNewArea = True
    window.view.points = []
    window.view._start = QPoint(1, 1)
    window.viewMousePressEvent(MouseEvent((1, 1), Qt.RightButton))
    assert window.view._start is None

    window.view.points = [(0, 0), (30, 0), (30, 30), (0, 30)]
    window.view._start = QPoint(30, 30)
    monkeypatch.setattr(behav_coding_map_creator.util, "intersection", lambda *_: False)
    window.viewMousePressEvent(MouseEvent((30, 30), MiddleOnlyForEquality()))

    assert window.closedPolygon is not None
    assert window.view.points[-1] == (0, 0)

    window.closedPolygon = None
    window.view.points = [(0, 0), (30, 0), (30, 30), (0, 30)]
    window.view._start = QPoint(0, 30)
    errors = []
    monkeypatch.setattr(behav_coding_map_creator.util, "intersection", lambda *_: True)
    monkeypatch.setattr(behav_coding_map_creator.QMessageBox, "critical", lambda *args: errors.append(args))
    window.viewMousePressEvent(MouseEvent((0, 30), MiddleOnlyForEquality()))

    assert "can not be intersected" in errors[0][2]


def test_view_forwards_mouse_events(window):
    received = []
    event = QMouseEvent(
        QEvent.Type.MouseButtonPress,
        QPointF(0, 0),
        QPointF(0, 0),
        QPointF(0, 0),
        Qt.LeftButton,
        Qt.LeftButton,
        Qt.NoModifier,
    )
    window.view.mousePress.connect(received.append)

    window.view.mousePressEvent(event)

    assert received == [event]


def test_module_main_entry_point(monkeypatch):
    class Application:
        def __init__(self, *_):
            pass

        def exec(self):
            return 0

    monkeypatch.setattr(QtWidgets, "QApplication", Application)
    monkeypatch.setattr(sys, "exit", lambda *_: None)
    monkeypatch.setattr(behav_coding_map_creator.gui_utilities, "resize_center", lambda *_: None)

    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", message="'boris.behav_coding_map_creator' found in sys.modules")
        runpy.run_module("boris.behav_coding_map_creator", run_name="__main__")
