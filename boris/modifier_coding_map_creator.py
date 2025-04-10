"""
BORIS
Behavioral Observation Research Interactive Software
Copyright 2012-2025 Olivier Friard

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

# to run this file, use
# python -m boris.modifier_coding_map_creator

import binascii
import io
import json
from pathlib import Path
import re
import gui_utilities

from PySide6.QtCore import (
    Qt,
    Signal,
    QPoint,
    QByteArray,
    QBuffer,
    QIODevice,
    QLineF,
)
from PySide6.QtGui import QColor, QBrush, QMouseEvent, QPixmap, QIcon, QPen, QPolygon, QPolygonF, QAction
from PySide6.QtWidgets import (
    QGraphicsPolygonItem,
    QGraphicsEllipseItem,
    QGraphicsPixmapItem,
    QGraphicsLineItem,
    QMainWindow,
    QGraphicsView,
    QPushButton,
    QLabel,
    QHBoxLayout,
    QLineEdit,
    QSlider,
    QGraphicsScene,
    QWidget,
    QColorDialog,
    QVBoxLayout,
    QMessageBox,
    QInputDialog,
    QFileDialog,
    QApplication,
    QListWidget,
    QSplitter,
    QSpacerItem,
    QSizePolicy,
    QFrame,
)

from . import config as cfg
from . import dialog
from . import utilities as util

designColor = QColor(255, 0, 0, 128)  # red opacity: 50%
penWidth: int = 0
penStyle = Qt.NoPen
selectedBrush = QBrush()
selectedBrush.setStyle(Qt.SolidPattern)
selectedBrush.setColor(QColor(255, 255, 0, 255))


class ModifiersMapCreatorWindow(QMainWindow):
    closed = Signal()

    class View(QGraphicsView):
        """
        class for handling mousepress event in QGraphicsView
        """

        mousePress = Signal(QMouseEvent)

        def mousePressEvent(self, event):
            self.mousePress.emit(event)

        _start: int = 0
        elList: list = []
        points: list = []

        def __init__(self, parent):
            QGraphicsView.__init__(self, parent)
            self.setBackgroundBrush(QColor(128, 128, 128))
            self.setScene(QGraphicsScene(self))
            self.scene().update()

    bitmapFileName: str = ""
    mapName: str = ""
    fileName: str = ""
    flagNewArea: bool = False
    flag_map_changed: bool = False
    areasList: dict = {}
    polygonsList2: dict = {}
    areaColor = QColor("lime")

    def __init__(self):
        super(ModifiersMapCreatorWindow, self).__init__()

        self.pixmap = QPixmap()
        self.closedPolygon = None
        self.selectedPolygon = None

        self.setWindowTitle("BORIS - Modifiers map creator")

        self.newMapAction = QAction(QIcon(), "&New modifiers map", self)
        self.newMapAction.setShortcut("Ctrl+N")
        self.newMapAction.setStatusTip("Create a new modifiers map")
        self.newMapAction.triggered.connect(self.newMap)

        self.openMapAction = QAction(QIcon(), "&Open modifiers map", self)
        self.openMapAction.setShortcut("Ctrl+O")
        self.openMapAction.setStatusTip("Open a modifiers map")
        self.openMapAction.triggered.connect(self.openMap)

        self.saveMapAction = QAction(QIcon(), "&Save modifiers map", self)
        self.saveMapAction.setShortcut("Ctrl+S")
        self.saveMapAction.setStatusTip("Save modifiers map")
        self.saveMapAction.setEnabled(False)
        self.saveMapAction.triggered.connect(self.saveMap_clicked)

        self.saveAsMapAction = QAction(QIcon(), "Save modifiers map as", self)
        self.saveAsMapAction.setStatusTip("Save modifiers map as")
        self.saveAsMapAction.setEnabled(False)
        self.saveAsMapAction.triggered.connect(self.saveAsMap_clicked)

        self.mapNameAction = QAction(QIcon(), "&Modifiers map name", self)
        self.mapNameAction.setShortcut("Ctrl+M")
        self.mapNameAction.setStatusTip("Change modifiers map name")
        self.mapNameAction.setEnabled(False)
        self.mapNameAction.triggered.connect(self.mapName_clicked)

        self.exitAction = QAction(QIcon(), "&Close", self)
        self.exitAction.setStatusTip("Close modifiers map creator")
        self.exitAction.triggered.connect(self.close)

        menubar = self.menuBar()
        fileMenu = menubar.addMenu("&Modifiers Map creator")
        fileMenu.addAction(self.newMapAction)
        fileMenu.addAction(self.openMapAction)
        fileMenu.addAction(self.saveMapAction)
        fileMenu.addAction(self.saveAsMapAction)
        fileMenu.addSeparator()
        fileMenu.addAction(self.mapNameAction)
        fileMenu.addSeparator()
        fileMenu.addAction(self.exitAction)

        splitter1 = QSplitter(Qt.Vertical)

        self.view = self.View(self)
        self.view.mousePress.connect(self.viewMousePressEvent)
        splitter1.addWidget(self.view)

        vlayout_list = QVBoxLayout()
        vlayout_list.addWidget(QLabel("List of modifiers"))

        self.area_list = QListWidget(self)
        self.area_list.itemClicked.connect(self.area_list_item_click)
        vlayout_list.addWidget(self.area_list)
        w = QWidget()
        w.setLayout(vlayout_list)
        splitter1.addWidget(w)
        splitter1.setSizes([300, 100])
        splitter1.setStretchFactor(2, 8)

        hlayout_cmd = QHBoxLayout()

        self.btNewArea = QPushButton("New modifier", self)
        self.btNewArea.clicked.connect(self.newArea)
        self.btNewArea.setVisible(False)
        hlayout_cmd.addWidget(self.btNewArea)

        self.btSaveArea = QPushButton("Save modifier", self)
        self.btSaveArea.clicked.connect(self.saveArea)
        self.btSaveArea.setVisible(False)
        hlayout_cmd.addWidget(self.btSaveArea)

        self.btCancelAreaCreation = QPushButton("Cancel new modifier", self)
        self.btCancelAreaCreation.clicked.connect(self.cancelAreaCreation)
        self.btCancelAreaCreation.setVisible(False)
        hlayout_cmd.addWidget(self.btCancelAreaCreation)

        hlayout_cmd.addItem(QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum))

        self.btDeleteArea = QPushButton("Delete selected modifier", self)
        self.btDeleteArea.clicked.connect(self.deleteArea)
        self.btDeleteArea.setVisible(False)
        self.btDeleteArea.setEnabled(False)
        hlayout_cmd.addWidget(self.btDeleteArea)

        hlayout_area = QHBoxLayout()

        self.lb = QLabel("Modifier")
        self.lb.setVisible(False)
        hlayout_area.addWidget(self.lb)

        self.leAreaCode = QLineEdit(self)
        self.leAreaCode.setVisible(False)
        hlayout_area.addWidget(self.leAreaCode)

        self.btColor = QPushButton()
        self.btColor.clicked.connect(self.chooseColor)
        self.btColor.setVisible(False)
        self.btColor.setStyleSheet(f"QWidget {{ background-color:{self.areaColor.name()} }}")
        hlayout_area.addWidget(self.btColor)

        self.slAlpha = QSlider(Qt.Horizontal)
        self.slAlpha.setRange(20, 100)
        self.slAlpha.setValue(50)
        self.slAlpha.valueChanged.connect(self.slAlpha_changed)
        self.slAlpha.setVisible(False)
        hlayout_area.addWidget(self.slAlpha)

        self.slAlpha_changed(50)

        vlayout_frame = QVBoxLayout()
        vlayout_frame.addLayout(hlayout_cmd)
        vlayout_frame.addLayout(hlayout_area)
        vlayout_frame.addItem(QSpacerItem(20, 40, QSizePolicy.Minimum, QSizePolicy.Expanding))

        frame = QFrame()
        frame.setFrameStyle(QFrame.Panel | QFrame.Plain)
        frame.setMinimumHeight(120)
        frame.setMaximumHeight(120)

        frame.setLayout(vlayout_frame)

        vlayout = QVBoxLayout()

        vlayout.addWidget(splitter1)
        vlayout.addWidget(frame)

        main_widget = QWidget(self)
        main_widget.setLayout(vlayout)
        self.setCentralWidget(main_widget)

        self.statusBar().showMessage("")

    def area_list_item_click(self, item):
        """
        select the polygon corresponding to the clicked area
        """

        if self.selectedPolygon:
            self.selectedPolygon.setPen(QPen(designColor, penWidth, penStyle, Qt.RoundCap, Qt.RoundJoin))
            self.selectedPolygon = None
            self.selectedPolygonMemBrush = None

        modifier_name = item.text()

        self.selectedPolygon = self.polygonsList2[item.text()]

        self.selectedPolygonMemBrush = self.selectedPolygon.brush()

        self.selectedPolygonAreaCode = modifier_name

        self.selectedPolygon.setPen(QPen(QColor(255, 0, 0, 255), 2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))

        self.leAreaCode.setText(modifier_name)
        for widget in (self.lb, self.leAreaCode, self.btSaveArea, self.btDeleteArea, self.btColor, self.slAlpha):
            widget.setVisible(True)

        self.btSaveArea.setText("Update modifier")
        self.btDeleteArea.setEnabled(True)

        self.areaColor = self.selectedPolygon.brush().color()
        self.btColor.setStyleSheet(f"QWidget {{background-color:{self.selectedPolygon.brush().color().name()}}}")

        self.slAlpha.setValue(int(self.areaColor.alpha() / 255 * 100))

    def get_current_alpha_value(self) -> str | None:
        """
        returns current alpha value (from button text)
        """
        match = re.search(r"(\d+)", self.btColor.text())

        if match:
            opacity_value = int(match.group(1))  # Convert the extracted string to an integer
            return opacity_value
        else:
            return None

    def slAlpha_changed(self, val):
        """
        opacity slider value changed
        """

        self.btColor.setText(f"Opacity: {val}")
        self.areaColor.setAlpha(int(val / 100 * 255))

        if self.selectedPolygon:
            self.selectedPolygon.setBrush(self.areaColor)

            # self.areasList[self.leAreaCode.text()]["color"] = self.areaColor.rgba()

        if self.closedPolygon:
            self.closedPolygon.setBrush(self.areaColor)

    def chooseColor(self):
        """
        area color button clicked
        """
        cd = QColorDialog()
        cd.setWindowFlags(Qt.WindowStaysOnTopHint)
        cd.setOptions(QColorDialog.ShowAlphaChannel | QColorDialog.DontUseNativeDialog)

        if cd.exec():
            self.areaColor = cd.currentColor()
            self.areaColor.setAlpha(int(self.get_current_alpha_value() / 100 * 255))

            self.btColor.setStyleSheet(f"QWidget {{background-color:{self.areaColor.name()}}}")

            if self.selectedPolygon:
                self.selectedPolygon.setBrush(self.areaColor)
                self.areasList[self.leAreaCode.text()]["color"] = self.areaColor.rgba()

            if self.closedPolygon:
                self.closedPolygon.setBrush(self.areaColor)

    def closeEvent(self, event):
        if self.flag_map_changed:
            response = dialog.MessageDialog(
                "BORIS - Modifiers map creator",
                "What to do about the current unsaved modifiers coding map?",
                [cfg.SAVE, cfg.DISCARD, cfg.CANCEL],
            )

            if response == cfg.SAVE:
                if not self.saveMap_clicked():
                    event.ignore()

            if response == cfg.CANCEL:
                event.ignore()
                return

        self.closed.emit()
        event.accept()

    def viewMousePressEvent(self, event):
        """
        check if area selected with mouse
        """

        def new_polygon():
            """
            create a newpolygon
            """
            newPolygon = QPolygonF()
            for p in self.view.points:
                newPolygon.append(QPoint(p[0], p[1]))

            # draw polygon a red polygon
            self.closedPolygon = QGraphicsPolygonItem(newPolygon)
            self.closedPolygon.setPen(QPen(designColor, penWidth, penStyle, Qt.RoundCap, Qt.RoundJoin))
            self.closedPolygon.setBrush(self.areaColor)
            self.view.scene().addItem(self.closedPolygon)

        def add_last_line():
            """
            add last line to start point
            """
            line = QGraphicsLineItem(
                QLineF(
                    self.view._start,
                    QPoint(self.view.points[0][0], self.view.points[0][1]),
                )
            )
            line.setPen(
                QPen(
                    designColor,
                    penWidth,
                    Qt.SolidLine,
                    Qt.RoundCap,
                    Qt.RoundJoin,
                )
            )

            self.view.scene().addItem(line)
            self.view.elList.append(line)

            self.statusBar().showMessage("Area completed")

        if not self.bitmapFileName:
            return

        self.btDeleteArea.setEnabled(False)

        # test = self.view.mapToScene(event.pos()).toPoint()
        test = self.view.mapToScene(event.position().toPoint()).toPoint()

        if test.x() < 0 or test.y() < 0 or test.x() > self.pixmap.size().width() or test.y() > self.pixmap.size().height():
            return

        if not self.flagNewArea:  # test clicked point for areas
            txt = ""

            # reset selected polygon to default pen
            if self.selectedPolygon:
                self.selectedPolygon.setPen(QPen(designColor, penWidth, penStyle, Qt.RoundCap, Qt.RoundJoin))
                self.selectedPolygon = None
                self.selectedPolygonMemBrush = None

            for idx, areaCode in enumerate(sorted(self.polygonsList2.keys())):
                for widget in (self.lb, self.leAreaCode, self.btSaveArea, self.btDeleteArea, self.btColor, self.slAlpha):
                    widget.setVisible(False)

                if self.polygonsList2[areaCode].contains(test):
                    txt += "," if txt else ""

                    txt += areaCode
                    self.selectedPolygon = self.polygonsList2[areaCode]
                    self.selectedPolygonAreaCode = areaCode

                    self.selectedPolygonMemBrush = self.selectedPolygon.brush()

                    self.selectedPolygon.setPen(
                        QPen(
                            QColor(255, 0, 0, 255),
                            2,
                            Qt.SolidLine,
                            Qt.RoundCap,
                            Qt.RoundJoin,
                        )
                    )

                    self.leAreaCode.setText(areaCode)
                    self.btDeleteArea.setEnabled(True)

                    # select area in list widget
                    item = self.area_list.item(idx)
                    self.area_list.setCurrentItem(item)

                    for widget in (self.lb, self.leAreaCode, self.btSaveArea, self.btDeleteArea, self.btColor, self.slAlpha):
                        widget.setVisible(True)

                    self.areaColor = self.selectedPolygon.brush().color()
                    self.btColor.setStyleSheet(f"QWidget {{background-color:{self.selectedPolygon.brush().color().name()} }}")

                    self.slAlpha.setValue(int(self.areaColor.alpha() / 255 * 100))

                    break

            if txt:
                self.statusBar().showMessage(f"Modifier{'s' if ',' in txt else ''}: {txt}")
            else:
                self.statusBar().showMessage("")

            if not self.selectedPolygon:
                self.leAreaCode.setVisible(False)
                self.btColor.setVisible(False)
                self.slAlpha.setVisible(False)
            return

        # right button: delete last line item
        if (event.buttons() & Qt.RightButton) and not self.closedPolygon:
            if self.view.points:
                self.view.points = self.view.points[0:-1]

            if self.view.points:
                self.view._start = QPoint(self.view.points[-1][0], self.view.points[-1][1])
            else:
                self.view._start = None

            # remove graphical elements
            if self.view.elList:
                self.view.scene().removeItem(self.view.elList[-1])
                self.view.elList = self.view.elList[0:-1]

        # middle button automatically close the polygon
        if (event.buttons() & Qt.MiddleButton) and not self.closedPolygon:
            add_last_line()
            new_polygon()

        # add line item
        if event.buttons() == Qt.LeftButton and not self.closedPolygon:
            if self.view._start:
                end = test

                # test is polygon is crossed
                if len(self.view.points) >= 3:
                    for idx, point in enumerate(self.view.points[:-2]):
                        if util.intersection(
                            self.view.points[idx],
                            self.view.points[idx + 1],
                            self.view.points[-1],
                            (int(end.x()), int(end.y())),
                        ):
                            QMessageBox.critical(self, "", "The polygon edges can not be intersected")
                            return

                # test if polygon closed (dist min 10 px)
                if abs(end.x() - self.view.points[0][0]) < 10 and abs(end.y() - self.view.points[0][1]) < 10:
                    add_last_line()
                    new_polygon()

                    return

                self.view.points.append((int(end.x()), int(end.y())))

                line = QGraphicsLineItem(QLineF(self.view._start, end))

                line.setPen(QPen(designColor, 2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))

                self.view.scene().addItem(line)
                self.view.elList.append(line)

                self.view._start = test

            else:  # first point
                self.view._start = test

                ellipse = QGraphicsEllipseItem(self.view._start.x(), self.view._start.y(), 3, 3)
                ellipse.setPen(QPen(designColor, 1, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))

                brush = QBrush()
                brush.setStyle(Qt.SolidPattern)
                brush.setColor(designColor)
                ellipse.setBrush(brush)

                self.view.scene().addItem(ellipse)
                self.view.elList.append(ellipse)

                self.view.points.append((self.view._start.x(), self.view._start.y()))

    def mapName_clicked(self):
        """
        change map name
        """
        text, ok = QInputDialog.getText(
            self,
            "Modifiers map name",
            "Enter a name for the modifiers map",
            QLineEdit.Normal,
            self.mapName,
        )
        if ok:
            self.mapName = text
            self.setWindowTitle(f"{cfg.programName} - Modifiers map creator tool - {self.mapName}")

    def newMap(self):
        """
        create a new map
        """

        if self.flag_map_changed:
            response = dialog.MessageDialog(
                cfg.programName + " - Modifiers map creator",
                "What to do about the current unsaved coding map?",
                ["Save", "Discard", "Cancel"],
            )

            if response == "Save":
                if not self.saveMap_clicked():
                    return

            if response == "Cancel":
                return

        self.cancelMap()

        text, ok = QInputDialog.getText(self, "Map name", "Enter a name for the new map")
        if ok:
            self.mapName = text
        else:
            return

        if self.mapName == "":
            QMessageBox.critical(self, "", "You must define a name for the new map")
            return

        if self.mapName in ["areas", "bitmap"]:
            QMessageBox.critical(self, "", "This name is not allowed")
            return

        self.setWindowTitle(cfg.programName + " - Map creator tool - " + self.mapName)

        self.loadBitmap()

    def openMap(self):
        """
        load bitmap from data
        show it in view scene
        """
        if self.flag_map_changed:
            response = dialog.MessageDialog(
                cfg.programName + " - Map creator",
                "What to do about the current unsaved coding map?",
                (cfg.SAVE, cfg.DISCARD, cfg.CANCEL),
            )

            if response == cfg.SAVE:
                if not self.saveMap_clicked():
                    return

            if response == cfg.CANCEL:
                return

        fileName, _ = QFileDialog().getOpenFileName(
            self,
            "Open a coding map",
            "",
            "BORIS coding map (*.boris_map);;All files (*)",
        )

        if not fileName:
            return
        try:
            self.codingMap = json.loads(open(fileName, "r").read())
        except Exception:
            QMessageBox.critical(
                self,
                cfg.programName,
                f"The file {fileName} seems not a behaviors coding map...",
            )
            return

        self.cancelMap()

        self.mapName = self.codingMap["name"]

        self.setWindowTitle(cfg.programName + " - Map creator tool - " + self.mapName)

        self.bitmapFileName = True

        self.fileName = fileName

        self.areasList = self.codingMap["areas"]  # dictionary of dictionaries

        bitmapContent = binascii.a2b_base64(self.codingMap["bitmap"])

        self.pixmap.loadFromData(bitmapContent)

        self.btDeleteArea.setEnabled(False)

        self.view.setSceneRect(0, 0, self.pixmap.size().width(), self.pixmap.size().height())
        pixItem = QGraphicsPixmapItem(self.pixmap)
        pixItem.setPos(0, 0)
        self.view.scene().addItem(pixItem)

        for areaCode in self.areasList:
            points = self.areasList[areaCode]["geometry"]

            newPolygon = QPolygonF()
            for p in points:
                newPolygon.append(QPoint(p[0], p[1]))

            clr = QColor()
            clr.setRgba(self.areasList[areaCode]["color"])

            # draw polygon
            polygon = QGraphicsPolygonItem()

            polygon.setPolygon(newPolygon)

            polygon.setPen(QPen(clr, penWidth, penStyle, Qt.RoundCap, Qt.RoundJoin))

            polygon.setBrush(QBrush(clr, Qt.SolidPattern))

            self.view.scene().addItem(polygon)
            self.polygonsList2[areaCode] = polygon

        self.btNewArea.setVisible(True)

        self.saveMapAction.setEnabled(True)
        self.saveAsMapAction.setEnabled(True)
        self.mapNameAction.setEnabled(True)

        self.update_area_list()

        self.statusBar().showMessage('Click the "New modifier" button to create a new modifier')

    def saveMap(self) -> bool:
        """
        save the modifier coding map on file
        """
        if not self.fileName:
            return False
        # create dict with map name key
        mapDict = {"name": self.mapName}

        # add areas
        mapDict["areas"] = self.areasList

        # Save QPixmap to QByteArray via QBuffer.
        byte_array = QByteArray()
        buffer = QBuffer(byte_array)
        buffer.open(QIODevice.WriteOnly)
        self.pixmap.save(buffer, "PNG")

        string_io = io.BytesIO(byte_array)

        string_io.seek(0)

        # add bitmap
        mapDict["bitmap"] = binascii.b2a_base64(string_io.read()).decode("utf-8")

        with open(self.fileName, "w") as outfile:
            outfile.write(json.dumps(mapDict))

        self.flag_map_changed = False

        return True

    def saveAsMap_clicked(self):
        filters = "Modifiers map (*.boris_map);;All files (*)"

        fn = QFileDialog(self).getSaveFileName(self, "Save modifiers map as", "", filters)
        if type(fn) is tuple:
            self.fileName, _ = fn
        else:
            self.fileName = fn

        if self.fileName:
            # if os.path.splitext(self.fileName)[1] != ".boris_map":
            if Path(self.fileName).suffix != ".boris_map":
                self.fileName += ".boris_map"
            self.saveMap()

    def saveMap_clicked(self):
        if not self.fileName:
            fn = QFileDialog(self).getSaveFileName(
                self,
                "Save modifiers map",
                self.mapName + ".boris_map",
                "BORIS MAP (*.boris_map);;All files (*)",
            )
            if type(fn) is tuple:
                self.fileName, _ = fn
            else:
                self.fileName = fn

            if self.fileName and Path(self.fileName).suffix() != ".boris_map":
                self.fileName += ".boris_map"

        if self.fileName:
            return self.saveMap()

        return False

    def newArea(self):
        """
        create a new area
        """
        if not self.bitmapFileName:
            QMessageBox.critical(self, cfg.programName, "An image must be loaded before to define areas")
            return

        if self.selectedPolygon:
            self.selectedPolygon.setPen(QPen(designColor, penWidth, penStyle, Qt.RoundCap, Qt.RoundJoin))
            self.selectedPolygon = None

        self.flagNewArea = True
        self.leAreaCode.clear()

        for widget in (
            self.btSaveArea,
            self.btCancelAreaCreation,
            self.lb,
            self.leAreaCode,
            self.btColor,
            self.slAlpha,
        ):
            widget.setVisible(True)

        self.btSaveArea.setText("Save modifier")

        self.btNewArea.setVisible(False)
        self.btDeleteArea.setVisible(False)

        self.statusBar().showMessage(
            "Draw a polygon by clicking the vertices (right-click will delete the last point, middle-click will close the polygon)"
        )

    def saveArea(self):
        """
        save the new modifier in the list
        """

        # check if not allowed character
        for c in cfg.CHAR_FORBIDDEN_IN_MODIFIERS:
            if c in self.leAreaCode.text():
                QMessageBox.critical(
                    self,
                    cfg.programName,
                    f"The modifier contains a character that is not allowed <b>{cfg.CHAR_FORBIDDEN_IN_MODIFIERS}</b>.",
                )
                return

        # check if modification
        if "save" in self.btSaveArea.text().lower():
            if not self.closedPolygon:
                QMessageBox.critical(
                    self,
                    cfg.programName,
                    "You must close your area before saving it.\nThe last vertex must correspond to the first one.",
                )

            if len(self.view.points) < 3:
                QMessageBox.critical(self, cfg.programName, "You must define a closed area")
                return

            # check if no modifier name
            if not self.leAreaCode.text():
                QMessageBox.critical(self, cfg.programName, "You must define a code for the new modifier")
                return

            # check if modifier name already used
            if self.leAreaCode.text() in self.areasList:
                QMessageBox.critical(self, cfg.programName, "The modifier name is already in use")
                return

            # create polygon
            newPolygon = QPolygon()
            for p in self.view.points:
                newPolygon.append(QPoint(p[0], p[1]))

            self.areasList[self.leAreaCode.text()] = {
                "geometry": self.view.points,
                "color": self.areaColor.rgba(),
            }

            # remove all lines
            for line in self.view.elList:
                self.view.scene().removeItem(line)

            # draw polygon
            self.closedPolygon.setBrush(QBrush(self.areaColor, Qt.SolidPattern))
            self.polygonsList2[self.leAreaCode.text()] = self.closedPolygon
            self.closedPolygon = None
            self.view._start = 0
            self.view.points = []
            self.view.elList = []
            self.flagNewArea = False

            self.statusBar().showMessage("New modifier saved", 5000)

        else:  # modification
            if self.leAreaCode.text() not in self.polygonsList2:
                self.polygonsList2[self.leAreaCode.text()] = self.polygonsList2.pop(self.area_list.currentItem().text())
                self.polygonsList2[self.leAreaCode.text()].setBrush(self.areaColor)

            self.statusBar().showMessage("Modifier modified", 5000)

        for widget in (
            self.btSaveArea,
            self.btCancelAreaCreation,
            self.lb,
            self.leAreaCode,
            self.btColor,
            self.slAlpha,
            self.btDeleteArea,
            self.btNewArea,
        ):
            widget.setVisible(False)

        self.btNewArea.setVisible(True)
        self.leAreaCode.setText("")
        self.update_area_list()
        self.flag_map_changed = True

    def cancelAreaCreation(self):
        if self.closedPolygon:
            self.view.scene().removeItem(self.closedPolygon)
            self.closedPolygon = None

        # remove all lines
        for line in self.view.elList:
            self.view.scene().removeItem(line)

        self.view.elList = []

        self.view._start = 0
        self.view.points = []
        self.flagNewArea = False
        self.btCancelAreaCreation.setVisible(False)
        self.btDeleteArea.setVisible(True)
        self.btSaveArea.setVisible(False)
        self.lb.setVisible(False)

        self.btColor.setVisible(False)
        self.slAlpha.setVisible(False)
        self.btNewArea.setVisible(True)

        self.leAreaCode.setVisible(False)
        self.leAreaCode.setText("")

    def update_area_list(self):
        """
        update the area list widget
        """
        self.area_list.clear()

        print(f"{self.polygonsList2=}")

        for modifier_name in sorted(self.polygonsList2.keys()):
            self.area_list.addItem(modifier_name)

    def deleteArea(self):
        """
        remove selected area from map
        """

        if self.selectedPolygon:
            self.view.scene().removeItem(self.selectedPolygon)

            if self.selectedPolygonAreaCode:
                self.view.scene().removeItem(self.polygonsList2[self.selectedPolygonAreaCode])
                del self.polygonsList2[self.selectedPolygonAreaCode]
                del self.areasList[self.selectedPolygonAreaCode]

            self.selectedPolygonAreaCode = None
            self.selectedPolygon = None

            self.flag_map_changed = True

        self.view.elList = []

        self.view._start = 0
        self.view.points = []
        self.flagNewArea = False

        for widget in (self.btSaveArea, self.lb, self.btColor, self.slAlpha, self.leAreaCode):
            widget.setVisible(False)

        self.btNewArea.setVisible(True)

        self.leAreaCode.setText("")
        self.statusBar().showMessage("")

        self.update_area_list()

    def cancelMap(self):
        """
        remove current map
        """
        self.flagNewArea = False
        self.areasList = {}
        self.polygonsList2 = {}
        self.view.scene().clear()
        self.btDeleteArea.setVisible(False)
        self.btNewArea.setVisible(False)
        self.saveMapAction.setEnabled(False)
        self.saveAsMapAction.setEnabled(False)
        self.mapNameAction.setEnabled(False)
        self.statusBar().showMessage("")
        self.flag_map_changed = False

    def loadBitmap(self):
        """
        load bitmap as background for coding map
        """

        fileName, _ = QFileDialog().getOpenFileName(self, "Load bitmap", "", "bitmap files (*.png *.jpg);;All files (*)")

        if not fileName:
            return
        self.bitmapFileName = fileName

        self.pixmap.load(self.bitmapFileName)

        # scale image
        """
        if self.pixmap.size().width() > maxSize or self.pixmap.size().height() > maxSize:
            self.pixmap = self.pixmap.scaled(maxSize, maxSize, Qt.KeepAspectRatio)
            QMessageBox.information(
                self,
                cfg.programName,
                "The bitmap was resized to %d x %d pixels\nThe original file was not modified"
                % (self.pixmap.size().width(), self.pixmap.size().height()),
            )
        """

        self.view.setSceneRect(0, 0, self.pixmap.size().width(), self.pixmap.size().height())
        pixitem = QGraphicsPixmapItem(self.pixmap)
        pixitem.setPos(0, 0)
        self.view.scene().addItem(pixitem)

        self.btNewArea.setVisible(True)

        self.saveMapAction.setEnabled(True)
        self.saveAsMapAction.setEnabled(True)
        self.mapNameAction.setEnabled(True)

        self.statusBar().showMessage("""Click "New modifier" to create a new modifier""")

        self.flag_map_changed = True


if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)
    window = ModifiersMapCreatorWindow()

    gui_utilities.resize_center(app, window, cfg.CODING_MAP_RESIZE_W, cfg.CODING_MAP_RESIZE_H)

    window.show()
    sys.exit(app.exec())
