"""
BORIS
Behavioral Observation Research Interactive Software
Copyright 2012-2024 Olivier Friard

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

from PyQt5.QtGui import QMouseEvent, QPixmap, QPolygonF, QColor, QBrush, QPen
from PyQt5.QtCore import Qt, pyqtSignal, QEvent, QPoint
from PyQt5.QtWidgets import (
    QLabel,
    QHBoxLayout,
    QGraphicsView,
    QGraphicsScene,
    QWidget,
    QVBoxLayout,
    QLineEdit,
    QPushButton,
    QGraphicsPixmapItem,
    QGraphicsPolygonItem,
    QMessageBox,
    QInputDialog,
    QApplication,
)

import json
import binascii
from . import config as cfg

codeSeparator = ","
penWidth = 0
penStyle = Qt.NoPen


class BehaviorsCodingMapWindowClass(QWidget):
    class View(QGraphicsView):
        mousePress = pyqtSignal(QMouseEvent)
        mouseMove = pyqtSignal(QMouseEvent)

        def eventFilter(self, source, event):
            if event.type() == QEvent.MouseMove:
                self.mouseMove.emit(event)

            if event.type() == QEvent.MouseButtonPress:
                self.mousePress.emit(event)

            return QWidget.eventFilter(self, source, event)

        elList, points = [], []

        def __init__(self, parent):
            QGraphicsView.__init__(self, parent)
            self.setScene(QGraphicsScene(self))
            self.scene().update()

            self.viewport().installEventFilter(self)
            self.setMouseTracking(True)

    clickSignal = pyqtSignal(str, list)  # click signal to be sent to mainwindow
    keypressSignal = pyqtSignal(QEvent)
    close_signal = pyqtSignal(str)

    def __init__(self, behaviors_coding_map, idx=0):
        super(BehaviorsCodingMapWindowClass, self).__init__()

        self.polygonsList2 = []

        self.installEventFilter(self)

        self.codingMap = behaviors_coding_map
        self.idx = idx

        self.setWindowTitle(f"Behaviors coding map: {self.codingMap['name']}")
        Vlayout = QVBoxLayout()

        self.view = self.View(self)
        self.view.mousePress.connect(self.viewMousePressEvent)
        self.view.mouseMove.connect(self.mouse_move_event)

        Vlayout.addWidget(self.view)

        hBoxLayout1 = QHBoxLayout()

        self.label = QLabel("Behavior(s)")
        hBoxLayout1.addWidget(self.label)

        self.leareaCode = QLineEdit(self)
        hBoxLayout1.addWidget(self.leareaCode)

        self.btClose = QPushButton(cfg.CLOSE)
        self.btClose.clicked.connect(self.close)
        hBoxLayout1.addWidget(self.btClose)

        Vlayout.addLayout(hBoxLayout1)

        self.setLayout(Vlayout)

        self.loadMap()

    def closeEvent(self, event):
        self.close_signal.emit(self.codingMap["name"])
        event.accept()

    def eventFilter(self, receiver, event):
        """
        send event (if keypress) to main window
        """
        if event.type() == QEvent.KeyPress:
            self.keypressSignal.emit(event)
            return True
        else:
            return False

    def mouse_move_event(self, event):
        """
        display behavior under mouse position
        """

        self.leareaCode.clear()
        codes = []
        test = self.view.mapToScene(event.pos()).toPoint()
        for areaCode, pg in self.polygonsList2:
            if pg.contains(test):
                codes.append(areaCode)
        self.leareaCode.setText(", ".join(codes))

    def viewMousePressEvent(self, event) -> None:
        """
        insert clicked areas codes
        """

        test = self.view.mapToScene(event.pos()).toPoint()
        to_be_sent: list = []

        for areaCode, pg in self.polygonsList2:
            if pg.contains(test):
                to_be_sent.append(areaCode)

        if to_be_sent:
            self.clickSignal.emit(self.codingMap["name"], to_be_sent)

    def loadMap(self):
        """
        load bitmap from data
        show it in view scene
        """

        pixmap = QPixmap()
        pixmap.loadFromData(binascii.a2b_base64(self.codingMap["bitmap"]))

        self.view.setSceneRect(0, 0, pixmap.size().width(), pixmap.size().height())
        pixItem = QGraphicsPixmapItem(pixmap)
        pixItem.setPos(0, 0)
        self.view.scene().addItem(pixItem)

        for key in self.codingMap["areas"]:
            areaCode = self.codingMap["areas"][key]["code"]
            points = self.codingMap["areas"][key]["geometry"]

            newPolygon = QPolygonF()
            for p in points:
                newPolygon.append(QPoint(p[0], p[1]))

            # draw polygon
            polygon = QGraphicsPolygonItem()
            polygon.setPolygon(newPolygon)
            clr = QColor()
            clr.setRgba(self.codingMap["areas"][key]["color"])
            polygon.setPen(QPen(clr, penWidth, penStyle, Qt.RoundCap, Qt.RoundJoin))
            polygon.setBrush(QBrush(clr, Qt.SolidPattern))

            self.view.scene().addItem(polygon)

            self.polygonsList2.append([areaCode, polygon])


def show_behaviors_coding_map(self):
    """
    show a behavior coding map
    """

    if cfg.BEHAVIORS_CODING_MAP not in self.pj or not self.pj[cfg.BEHAVIORS_CODING_MAP]:
        QMessageBox.warning(self, cfg.programName, "No behaviors coding map found in current project")
        return

    items = [x["name"] for x in self.pj[cfg.BEHAVIORS_CODING_MAP]]
    if len(items) == 1:
        coding_map_name = items[0]
    else:
        item, ok = QInputDialog.getItem(self, "Select a coding map", "list of coding maps", items, 0, False)
        if ok and item:
            coding_map_name = item
        else:
            return

    if self.bcm_dict.get(coding_map_name, None) is not None:
        # if coding_map_name in self.bcm_dict and :
        self.bcm_dict[coding_map_name].show()
    else:
        self.bcm_dict[coding_map_name] = BehaviorsCodingMapWindowClass(
            self.pj[cfg.BEHAVIORS_CODING_MAP][items.index(coding_map_name)], idx=items.index(coding_map_name)
        )

        self.bcm_dict[coding_map_name].clickSignal.connect(self.click_signal_from_behaviors_coding_map)

        # self.bcm_dict[coding_map_name].close_signal.connect(self.close_behaviors_coding_map)

        self.bcm_dict[coding_map_name].resize(cfg.CODING_MAP_RESIZE_W, cfg.CODING_MAP_RESIZE_W)
        self.bcm_dict[coding_map_name].setWindowFlags(Qt.WindowStaysOnTopHint)
        self.bcm_dict[coding_map_name].show()


if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)

    if len(sys.argv) > 1:
        cm = json.loads(open(sys.argv[1]).read())
        codingMapWindow = BehaviorsCodingMapWindowClass(cm)
        codingMapWindow.resize(cfg.CODING_MAP_RESIZE_W, cfg.CODING_MAP_RESIZE_H)
        codingMapWindow.show()
        sys.exit(app.exec_())
