"""
BORIS
Behavioral Observation Research Interactive Software
Copyright 2012-2020 Olivier Friard

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


from PyQt5.QtGui import *
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *

import decimal
from decimal import getcontext
import json
import binascii
import os
import io

from boris.config import *
from boris import dialog

designColor = QColor(255, 0, 0, 128)  # red opacity: 50%
penWidth = 0
penStyle = Qt.NoPen
selectedBrush = QBrush()
selectedBrush.setStyle(Qt.SolidPattern)
selectedBrush.setColor(QColor(255, 255, 0, 255))


def intersection(A, B, C, D):
    """
    line segments intersection with decimal precision
    return True when intersection else False
    """
    getcontext().prec = 28

    Dec = decimal.Decimal
    xa, ya = Dec(str(A[0])), Dec(str(A[1]))
    xb, yb = Dec(str(B[0])), Dec(str(B[1]))
    xc, yc = Dec(str(C[0])), Dec(str(C[1]))
    xd, yd = Dec(str(D[0])), Dec(str(D[1]))

    # check if first segment is vertical
    try:
        if xa == xb:
            slope = (yc - yd) / (xc - xd)
            intersept = yc - slope * xc
            xm = xa
            ym = slope * xm + intersept

        # check if second segment is vertical
        elif xc == xd:
            slope = (ya - yb) / (xa - xb)
            intersept = ya - slope * xa
            xm = xc
            ym = slope * xm + intersept
        else:
            xm = ((xd * xa * yc - xd * xb * yc - xd * xa * yb - xc * xa * yd + xc * xa * yb
                   + xd * ya * xb + xc * xb * yd - xc * ya * xb) /
                  (-yb * xd + yb * xc + ya * xd - ya * xc + xb * yd - xb * yc - xa * yd +
                   xa * yc)).quantize(
                       Dec('.001'), rounding=decimal.ROUND_DOWN)
            ym = ((yb * xc * yd - yb * yc * xd - ya * xc * yd + ya * yc * xd - xa * yb * yd
                   + xa * yb * yc + ya * xb * yd - ya * xb * yc) /
                  (-yb * xd + yb * xc + ya * xd - ya * xc + xb * yd - xb * yc - xa * yd +
                   xa * yc)).quantize(
                       Dec('.001'), rounding=decimal.ROUND_DOWN)

        xmin1, xmax1 = min(xa, xb), max(xa, xb)
        xmin2, xmax2 = min(xc, xd), max(xc, xd)
        ymin1, ymax1 = min(ya, yb), max(ya, yb)
        ymin2, ymax2 = min(yc, yd), max(yc, yd)

        return (xm >= xmin1 and xm <= xmax1 and xm >= xmin2 and xm <= xmax2 and ym >= ymin1 and ym <= ymax1 and ym >= ymin2 and ym <= ymax2)

    except Exception:  # for cases xa=xb=xc=xd
        return True


class BehaviorsMapCreatorWindow(QMainWindow):

    signal_add_to_project = pyqtSignal(dict)

    class View(QGraphicsView):
        """
        class for handling mousepress event in QGraphicsView
        """
        mousePress = pyqtSignal(QMouseEvent)

        def mousePressEvent(self, event):
            self.mousePress.emit(event)

        _start = 0
        elList, points = [], []

        def __init__(self, parent):
            QGraphicsView.__init__(self, parent)
            self.setBackgroundBrush(QColor(128, 128, 128))
            self.setScene(QGraphicsScene(self))
            self.scene().update()

    bitmapFileName, mapName, fileName = "", "", ""
    flagNewArea, flagMapChanged = False, False
    polygonsList2 = []
    areaColor = QColor("lime")

    def __init__(self, arg):

        self.codes_list = arg

        super(BehaviorsMapCreatorWindow, self).__init__()

        self.pixmap = QPixmap()
        self.closedPolygon = None
        self.selectedPolygon = None

        self.setWindowTitle("BORIS - Behaviors coding map creator")

        self.newMapAction = QAction(QIcon(), "&New behaviors coding map", self)
        self.newMapAction.setShortcut("Ctrl+N")
        self.newMapAction.setStatusTip("Create a new behaviors coding map")
        self.newMapAction.triggered.connect(self.newMap)

        self.openMapAction = QAction(QIcon(), "&Open a behaviors coding map", self)
        self.openMapAction.setShortcut("Ctrl+O")
        self.openMapAction.setStatusTip("Open a behaviors coding map")
        self.openMapAction.triggered.connect(self.openMap)

        self.saveMapAction = QAction(QIcon(), "&Save the current behaviors coding map", self)
        self.saveMapAction.setShortcut("Ctrl+S")
        self.saveMapAction.setStatusTip("Save the current behaviors coding map")
        self.saveMapAction.setEnabled(False)
        self.saveMapAction.triggered.connect(self.saveMap_clicked)

        self.saveAsMapAction = QAction(QIcon(), "Save the current behaviors coding map as ...", self)
        self.saveAsMapAction.setStatusTip("Save the current behaviors coding map as ...")
        self.saveAsMapAction.setEnabled(False)
        self.saveAsMapAction.triggered.connect(self.saveAsMap_clicked)

        self.mapNameAction = QAction(QIcon(), "&Edit name of behaviors coding map", self)
        self.mapNameAction.setShortcut("Ctrl+M")
        self.mapNameAction.setStatusTip("Edit name of behaviors coding map")
        self.mapNameAction.setEnabled(False)
        self.mapNameAction.triggered.connect(self.mapName_clicked)

        self.addToProject = QAction(QIcon(), "Add coding map to project", self)
        self.addToProject.setStatusTip("Add coding map to project")
        self.addToProject.setEnabled(False)
        self.addToProject.triggered.connect(self.add_to_project)

        self.exitAction = QAction(QIcon(), "&Close", self)
        self.exitAction.setStatusTip("Close")
        self.exitAction.triggered.connect(self.close)

        menubar = self.menuBar()
        fileMenu = menubar.addMenu("&File")
        fileMenu.addAction(self.newMapAction)
        fileMenu.addAction(self.openMapAction)
        fileMenu.addAction(self.saveMapAction)
        fileMenu.addAction(self.saveAsMapAction)
        fileMenu.addSeparator()
        fileMenu.addAction(self.mapNameAction)
        fileMenu.addSeparator()
        fileMenu.addAction(self.addToProject)
        fileMenu.addSeparator()
        fileMenu.addAction(self.exitAction)


        splitter1 = QSplitter(Qt.Vertical)
        '''
        splitter1.addWidget(splitter1)
        splitter1.addWidget(bottom)
        '''

        '''vlayout_list = QVBoxLayout()'''

        self.view = self.View(self)
        self.view.mousePress.connect(self.viewMousePressEvent)
        splitter1.addWidget(self.view)

        vlayout_list = QVBoxLayout()
        vlayout_list.addWidget(QLabel("Defined area"))

        self.area_list = QListWidget(self)
        # self.area_list.setMaximumHeight(120)
        self.area_list.itemClicked.connect(self.area_list_item_click)
        vlayout_list.addWidget(self.area_list)
        w = QWidget()
        w.setLayout(vlayout_list)
        splitter1.addWidget(w)
        splitter1.setSizes([300, 100])
        splitter1.setStretchFactor(2, 8)




        self.btLoad = QPushButton("Load bitmap", self)
        self.btLoad.clicked.connect(self.loadBitmap)
        self.btLoad.setVisible(False)

        hlayout_cmd = QHBoxLayout()

        self.btNewArea = QPushButton("New behavior area", self)
        self.btNewArea.clicked.connect(self.newArea)
        self.btNewArea.setVisible(False)
        hlayout_cmd.addWidget(self.btNewArea)

        self.btSaveArea = QPushButton("Save the behavior area", self)
        self.btSaveArea.clicked.connect(self.saveArea)
        self.btSaveArea.setVisible(False)
        hlayout_cmd.addWidget(self.btSaveArea)

        self.btCancelAreaCreation = QPushButton("Cancel", self)
        self.btCancelAreaCreation.clicked.connect(self.cancelAreaCreation)
        self.btCancelAreaCreation.setVisible(False)
        hlayout_cmd.addWidget(self.btCancelAreaCreation)

        self.btDeleteArea = QPushButton("Delete selected behavior area", self)
        self.btDeleteArea.clicked.connect(self.deleteArea)
        self.btDeleteArea.setVisible(False)
        hlayout_cmd.addWidget(self.btDeleteArea)

        hlayout_area = QHBoxLayout()

        self.lb = QLabel("Behavior")
        self.lb.setVisible(False)
        hlayout_area.addWidget(self.lb)

        self.leAreaCode = QLineEdit(self)
        self.leAreaCode.setReadOnly(True)
        self.leAreaCode.setVisible(False)
        self.leAreaCode.setEnabled(False)
        hlayout_area.addWidget(self.leAreaCode)

        self.btEditAreaCode = QPushButton("Select behavior")
        self.btEditAreaCode.clicked.connect(self.edit_area_code)
        self.btEditAreaCode.setVisible(False)
        hlayout_area.addWidget(self.btEditAreaCode)

        self.btColor = QPushButton()
        self.btColor.clicked.connect(self.chooseColor)
        self.btColor.setVisible(False)
        self.btColor.setStyleSheet(f"QWidget {{background-color:{self.areaColor.name()}}}")
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

        '''
        vlayout.addWidget(self.view)
        vlayout.addWidget(QLabel("Defined area"))
        vlayout.addWidget(self.area_list)
        '''
        vlayout.addWidget(splitter1)
        '''vlayout.addLayout(vlayout_view_list)'''

        vlayout.addWidget(frame)
        vlayout.addWidget(self.btLoad)

        main_widget = QWidget(self)
        main_widget.setLayout(vlayout)
        self.setCentralWidget(main_widget)

        self.statusBar().showMessage("")


    def add_to_project(self, item):
        """
        add coding map to project
        """

        mapDict = self.make_coding_map_dict()
        self.signal_add_to_project.emit(mapDict)


    def area_list_item_click(self, item):
        """
        select the polygon corresponding to the clicked area
        """

        if self.selectedPolygon:
            self.selectedPolygon.setPen(QPen(designColor, penWidth, penStyle, Qt.RoundCap, Qt.RoundJoin))
            self.selectedPolygon = None
            self.selectedPolygonMemBrush = None

        idx = int(item.text().split("#")[1])
        ac, pg = self.polygonsList2[idx]

        self.selectedPolygon = pg

        self.selectedPolygonMemBrush = self.selectedPolygon.brush()

        self.selectedPolygon.setPen(QPen(QColor(255, 0, 0, 255), 2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))

        self.lb.setVisible(True)
        self.leAreaCode.setText(ac)
        self.leAreaCode.setVisible(True)
        self.btEditAreaCode.setVisible(True)

        self.btDeleteArea.setVisible(True)

        self.areaColor = self.selectedPolygon.brush().color()
        self.btColor.setStyleSheet(f"QWidget {{background-color:{self.selectedPolygon.brush().color().name()}}}")
        self.btColor.setVisible(True)

        self.slAlpha.setValue(int(self.selectedPolygon.brush().color().alpha() / 255 * 100))
        self.slAlpha.setVisible(True)


    def edit_area_code(self):
        """
        select a behavior
        """

        if self.leAreaCode.text() in self.codes_list:
            code_index = self.codes_list.index(self.leAreaCode.text())
        else:
            code_index = 0

        item, ok = QInputDialog.getItem(self, "Select a behavior", "Available behaviors", self.codes_list, code_index, False)
        self.leAreaCode.setText(item)

        if self.selectedPolygon:
            for idx, area in enumerate(self.polygonsList2):
                ac, pg = area
                if pg == self.selectedPolygon:
                    self.polygonsList2[idx] = [self.leAreaCode.text(), pg]
                    break

            self.update_area_list()


    def slAlpha_changed(self, val):
        """
        opacity slider value changed
        """

        self.btColor.setText(f"Opacity: {val} %")
        self.areaColor.setAlpha(int(val / 100 * 255))

        if self.selectedPolygon:
            self.selectedPolygon.setBrush(self.areaColor)
            for idx, area in enumerate(self.polygonsList2):
                ac, pg = area
                if pg == self.selectedPolygon:
                    pg.setBrush(self.areaColor)
                    self.polygonsList2[idx] = [ac, pg]
                    break

        if self.closedPolygon:
            self.closedPolygon.setBrush(self.areaColor)


    def chooseColor(self):
        """
        area color button clicked
        """
        cd = QColorDialog()

        col = cd.getColor()
        if col.isValid():
            self.btColor.setStyleSheet("QWidget {background-color:%s}" % col.name())
            self.areaColor = col
            self.areaColor.setAlpha(int(self.slAlpha.value() / 100 * 255))

        if self.selectedPolygon:
            self.selectedPolygon.setBrush(self.areaColor)

            for idx, area in enumerate(self.polygonsList2):
                ac, pg = area
                if pg == self.selectedPolygon:
                    pg.setBrush(self.areaColor)
                    self.polygonsList2[idx] = [ac, pg]
                    break

        if self.closedPolygon:
            self.closedPolygon.setBrush(self.areaColor)


    def closeEvent(self, event):

        if self.flagMapChanged:

            response = dialog.MessageDialog("BORIS - Modifiers map creator",
                                            "What to do about the current unsaved modifiers coding map?",
                                            ["Save", "Discard", "Cancel"])

            if response == "Save":
                if not self.saveMap_clicked():
                    event.ignore()

            if response == "Cancel":
                event.ignore()
                return

        event.accept()


    def viewMousePressEvent(self, event):
        """
        check if area selected with mouse
        """

        if not self.bitmapFileName:
            return

        test = self.view.mapToScene(event.pos()).toPoint()  # coordinates of clicked point

        if test.x() < 0 or test.y() < 0 or test.x() > self.pixmap.size().width() or test.y() > self.pixmap.size().height():
            return

        if not self.flagNewArea:   # test clicked point for areas

            # reset selected polygon to default pen
            if self.selectedPolygon:
                self.selectedPolygon.setPen(QPen(designColor, penWidth, penStyle, Qt.RoundCap, Qt.RoundJoin))
                self.selectedPolygon = None
                self.selectedPolygonMemBrush = None

            for areaCode, pg in self.polygonsList2:

                if pg.contains(test):

                    self.selectedPolygon = pg

                    self.selectedPolygonMemBrush = self.selectedPolygon.brush()

                    self.selectedPolygon.setPen(QPen(QColor(255, 0, 0, 255), 2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))

                    self.lb.setVisible(True)
                    self.leAreaCode.setText(areaCode)
                    self.leAreaCode.setVisible(True)
                    # self.leAreaCode.setEnabled(False)
                    self.btEditAreaCode.setVisible(True)

                    self.btDeleteArea.setVisible(True)

                    self.areaColor = self.selectedPolygon.brush().color()
                    self.btColor.setStyleSheet(f"QWidget {{background-color:{self.selectedPolygon.brush().color().name()}}}")
                    self.btColor.setVisible(True)

                    self.slAlpha.setValue(int(self.selectedPolygon.brush().color().alpha() / 255 * 100))
                    self.slAlpha.setVisible(True)

                    break

            if not self.selectedPolygon:
                self.leAreaCode.setVisible(False)
                self.lb.setVisible(False)
                self.btDeleteArea.setVisible(False)
                self.btEditAreaCode.setVisible(False)
                self.btColor.setVisible(False)
                self.slAlpha.setVisible(False)
            return

        # delete last line item
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

        # add line item
        if event.buttons() == Qt.LeftButton and not self.closedPolygon:

            if self.view._start:

                end = test

                # test is polygon is crossed
                if len(self.view.points) >= 3:

                    for idx, point in enumerate(self.view.points[:-2]):

                        if intersection(self.view.points[idx], self.view.points[idx + 1],
                                        self.view.points[-1], (int(end.x()), int(end.y()))):
                            QMessageBox.critical(self, "", "The polygon edges can not be intersected")
                            return

                # test if polygon closed (dist min 10 px)
                if abs(end.x() - self.view.points[0][0]) < 10 and abs(end.y() - self.view.points[0][1]) < 10:

                    line = QGraphicsLineItem(QLineF(self.view._start, QPoint(self.view.points[0][0], self.view.points[0][1])))
                    line.setPen(QPen(designColor, penWidth, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))

                    self.view.scene().addItem(line)
                    self.view.elList.append(line)

                    self.statusBar().showMessage("Area completed")

                    # create polygon
                    newPolygon = QPolygonF()
                    for p in self.view.points:
                        newPolygon.append(QPoint(p[0], p[1]))

                    # draw polygon a red polygon


                    self.closedPolygon = QGraphicsPolygonItem(newPolygon)

                    self.closedPolygon.setPen(QPen(designColor, penWidth, penStyle, Qt.RoundCap, Qt.RoundJoin))
                    self.closedPolygon.setBrush(self.areaColor)

                    self.view.scene().addItem(self.closedPolygon)

                    return


                self.view.points.append((int(end.x()), int(end.y())))

                line = QGraphicsLineItem(QLineF(self.view._start, end))

                line.setPen(QPen(designColor, 2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))

                self.view.scene().addItem(line)
                self.view.elList.append(line)

                self.view._start = test

            else:   # first point

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
        Edit map name
        """

        while True:
            map_name, ok = QInputDialog.getText(self, "Behaviors coding map name",
                                                "Enter a name for the coding map",
                                                QLineEdit.Normal, self.mapName)
            if map_name.upper() in self.bcm_list:
                QMessageBox.critical(self, "",
                                ("The name for the new coding map already exists.<br>"
                                f"{', '.join(self.bcm_list)} are already defined.<br>"
                                "To reuse the same name the existing coding map must be deleted (File > Edit project)"
                                )
                                    )
            if ok and map_name and map_name.upper() not in self.bcm_list:
                self.mapName = map_name
                self.setWindowTitle(f"{programName} - Behaviors coding map creator - {self.mapName}")
                break
            if not ok:
                return


    def newMap(self):
        """
        create a new map
        """

        if self.flagMapChanged:

            response = dialog.MessageDialog(programName + " - Behaviors coding map creator",
                                            "What to do about the current unsaved coding map?",
                                            [SAVE, DISCARD, CANCEL])

            if response == SAVE:
                if not self.saveMap_clicked():
                    return

            if response == CANCEL:
                return

        self.cancelMap()

        while True:
            map_name, ok = QInputDialog.getText(self, "Behaviors coding map name",
                                                "Enter a name for the new coding map")
            if map_name.upper() in self.bcm_list:
                QMessageBox.critical(self, "",
                                ("The name for the new coding map already exists.<br>"
                                f"{', '.join(self.bcm_list)} are already defined.<br>"
                                "To reuse the same name the existing coding map must be deleted (File > Edit project)"
                                )
                                    )
            if ok and map_name and map_name.upper() not in self.bcm_list:
                self.mapName = map_name
                break
            if not ok:
                return

        '''
        if not self.mapName:
            QMessageBox.critical(self, "", "You must define a name for the new coding map")
            return
        '''

        self.setWindowTitle(f"{programName} - Behaviors coding map creator tool - {self.mapName}")

        self.btLoad.setVisible(True)
        self.statusBar().showMessage('Click "Load bitmap" button to select and load a bitmap into the viewer')



    def openMap(self):
        """
        open a coding map from file

        load bitmap from data
        show it in view scene
        """
        if self.flagMapChanged:
            response = dialog.MessageDialog(programName + " - Behaviors coding map creator",
                                            "What to do about the current unsaved coding map?",
                                            ['Save', 'Discard', 'Cancel'])

            if (response == "Save" and not self.saveMap_clicked()) or (response == "Cancel"):
                return

        fn = QFileDialog(self).getOpenFileName(self, "Open a behaviors coding map", "",
                                               "Behaviors coding map (*.behav_coding_map);;All files (*)")
        fileName = fn[0] if type(fn) is tuple else fn

        if fileName:

            try:
                self.codingMap = json.loads(open(fileName, "r").read())
            except Exception:
                QMessageBox.critical(self, programName, f"The file {fileName} is not a behaviors coding map.")
                return

            if "coding_map_type" not in self.codingMap or self.codingMap["coding_map_type"] != "BORIS behaviors coding map":
                QMessageBox.critical(self, programName, f"The file {fileName} is not a BORIS behaviors coding map.")

            self.cancelMap()

            self.mapName = self.codingMap["name"]

            self.setWindowTitle(f"{programName} - Behaviors coding map creator - {self.mapName}")

            self.bitmapFileName = True

            self.fileName = fileName

            bitmapContent = binascii.a2b_base64(self.codingMap["bitmap"])

            self.pixmap.loadFromData(bitmapContent)

            self.view.setSceneRect(0, 0, self.pixmap.size().width(), self.pixmap.size().height())
            self.view.setMinimumHeight(self.pixmap.size().height())
            # self.view.setMaximumHeight(self.pixmap.size().height())
            pixItem = QGraphicsPixmapItem(self.pixmap)
            pixItem.setPos(0, 0)
            self.view.scene().addItem(pixItem)

            for key in self.codingMap["areas"]:
                areaCode = self.codingMap["areas"][key]["code"]
                points = self.codingMap["areas"][key]["geometry"]

                newPolygon = QPolygonF()
                for p in points:
                    newPolygon.append(QPoint(p[0], p[1]))

                # draw polygon
                '''polygon = QGraphicsPolygonItem(None, None) if QT_VERSION_STR[0] == "4" else QGraphicsPolygonItem()'''
                polygon = QGraphicsPolygonItem()
                polygon.setPolygon(newPolygon)
                clr = QColor()
                clr.setRgba(self.codingMap["areas"][key]["color"])
                polygon.setPen(QPen(clr, penWidth, penStyle, Qt.RoundCap, Qt.RoundJoin))
                polygon.setBrush(QBrush(clr, Qt.SolidPattern))

                self.view.scene().addItem(polygon)

                self.polygonsList2.append([areaCode, polygon])

            self.btNewArea.setVisible(True)
            self.btLoad.setVisible(False)

            self.saveMapAction.setEnabled(True)
            self.saveAsMapAction.setEnabled(True)
            self.addToProject.setEnabled(True)
            self.mapNameAction.setEnabled(True)

            self.update_area_list()

        else:
            self.statusBar().showMessage("No file", 5000)

    def make_coding_map_dict(self):
        mapDict = {"coding_map_type": "BORIS behaviors coding map",
                   "name": self.mapName,
                   "areas": {}}

        for ac, pg in self.polygonsList2:
            if not mapDict["areas"]:
                idx = 0
            else:
                idx = max(mapDict["areas"].keys()) + 1

            points = []
            for p in range(pg.polygon().count()):
                points.append([int(pg.polygon().value(p).x()), int(pg.polygon().value(p).y())])

            mapDict["areas"][idx] = {"code": ac, "geometry": points, "color": pg.brush().color().rgba()}

        mapDict["areas"] = json.loads(json.dumps(mapDict["areas"]))

        # Save QPixmap to QByteArray via QBuffer.
        byte_array = QByteArray()
        buffer = QBuffer(byte_array)
        buffer.open(QIODevice.WriteOnly)
        self.pixmap.save(buffer, "PNG")
        string_io = io.BytesIO(byte_array)
        string_io.seek(0)

        # add codified bitmap
        mapDict["bitmap"] = binascii.b2a_base64(string_io.read()).decode("utf-8")

        return mapDict



    def saveMap(self):
        """
        save current coding map in JSON format
        """

        if self.fileName:
            mapDict = self.make_coding_map_dict()

            with open(self.fileName, "w") as outfile:
                outfile.write(json.dumps(mapDict))

            self.flagMapChanged = False

            return True
        else:
            return False


    def saveAsMap_clicked(self):

        filters = "Behaviors coding map (*.behav_coding_map);;All files (*)"

        fn = QFileDialog(self).getSaveFileName(self, "Save behaviors coding map as", "", filters)
        self.fileName = fn[0] if type(fn) is tuple else fn

        if self.fileName:
            if os.path.splitext(self.fileName)[1] != ".behav_coding_map":
                self.fileName += ".behav_coding_map"
            self.saveMap()


    def saveMap_clicked(self):

        if not self.fileName:
            fn = QFileDialog().getSaveFileName(self,
                                               "Save modifiers map",
                                               self.mapName + ".behav_coding_map",
                                               "Behaviors coding map (*.behav_coding_map);;All files (*)")
            self.fileName = fn[0] if type(fn) is tuple else fn

            if self.fileName and os.path.splitext(self.fileName)[1] != ".behav_coding_map":
                self.fileName += ".behav_coding_map"

        if self.fileName:
            return self.saveMap()

        return False


    def newArea(self):

        if not self.bitmapFileName:
            QMessageBox.critical(self, programName, "A bitmap must be loaded before to define areas")
            return

        if self.selectedPolygon:
            self.selectedPolygon.setPen(QPen(designColor, penWidth, penStyle, Qt.RoundCap, Qt.RoundJoin))
            self.selectedPolygon = None

        self.flagNewArea = True
        self.btSaveArea.setVisible(True)
        self.btCancelAreaCreation.setVisible(True)
        self.btNewArea.setVisible(False)
        self.lb.setVisible(True)
        self.leAreaCode.clear()
        self.leAreaCode.setVisible(True)
        # self.leAreaCode.setEnabled(False)
        self.btEditAreaCode.setVisible(True)
        self.btColor.setVisible(True)
        self.slAlpha.setVisible(True)
        self.btDeleteArea.setVisible(False)

        self.statusBar().showMessage(("Click on bitmap to set the vertices of the area with the mouse "
                                      "(right click will cancel the last point)"))

    def saveArea(self):

        if not self.closedPolygon:
            QMessageBox.critical(self, programName, ("You must close your area before saving it.\n"
                                                     "The last vertex must correspond to the first one."))

        if len(self.view.points) < 3:
            QMessageBox.critical(self, programName, "You must define a closed area")
            return

        # check if no area code
        if not self.leAreaCode.text():
            QMessageBox.critical(self, programName, "You must define a code for the new behavior area")
            return

        # remove all lines
        for l in self.view.elList:
            self.view.scene().removeItem(l)

        # draw polygon
        self.closedPolygon.setBrush(QBrush(self.areaColor, Qt.SolidPattern))
        # self.polygonsList2[self.leAreaCode.text()] = self.closedPolygon
        self.polygonsList2.append([self.leAreaCode.text(), self.closedPolygon])

        self.closedPolygon, self.flagNewArea = None, None
        self.view._start = 0
        self.view.points, self.view.elList = [], []

        for widget in [self.btSaveArea, self.btCancelAreaCreation, self.lb,
                       self.leAreaCode, self.btEditAreaCode, self.btColor, self.slAlpha,
                       self.btDeleteArea, self.btNewArea]:
            widget.setVisible(False)

        self.btNewArea.setVisible(True)

        self.leAreaCode.setText("")

        self.flagMapChanged = True
        self.statusBar().showMessage("New area saved", 5000)

        self.update_area_list()


    def cancelAreaCreation(self):
        if self.closedPolygon:
            self.view.scene().removeItem(self.closedPolygon)
            self.closedPolygon = None

        # remove all lines
        for l in self.view.elList:
            self.view.scene().removeItem(l)

        self.view.elList = []

        self.view._start = 0
        self.view.points = []
        self.flagNewArea = False
        self.btCancelAreaCreation.setVisible(False)
        self.btDeleteArea.setVisible(False)
        self.btSaveArea.setVisible(False)
        self.lb.setVisible(False)

        self.btColor.setVisible(False)
        self.slAlpha.setVisible(False)
        self.btNewArea.setVisible(True)

        self.leAreaCode.setVisible(False)
        self.leAreaCode.setText("")

        self.btEditAreaCode.setVisible(False)


    def update_area_list(self):
        self.area_list.clear()
        for idx, area in enumerate(self.polygonsList2):
            ac, pg = area
            self.area_list.addItem(f"{ac} #{idx}")



    def deleteArea(self):
        """
        remove selected area from map
        """

        if self.selectedPolygon:
            self.view.scene().removeItem(self.selectedPolygon)

            to_delete = -1
            for idx, area in enumerate(self.polygonsList2):
                ac, pg = area
                if pg == self.selectedPolygon:
                    to_delete = idx

            if to_delete != -1:
                del self.polygonsList2[to_delete]

            self.flagMapChanged = True

        self.view.elList = []

        self.view._start = 0
        self.view.points = []
        self.flagNewArea = False
        self.btSaveArea.setVisible(False)
        self.lb.setVisible(False)

        self.btColor.setVisible(False)
        self.slAlpha.setVisible(False)
        self.btNewArea.setVisible(True)

        self.leAreaCode.setVisible(False)
        self.leAreaCode.setText("")
        self.btEditAreaCode.setVisible(False)

        self.btDeleteArea.setVisible(False)
        self.statusBar().showMessage("")

        self.update_area_list()

    def cancelMap(self):
        """
        remove current map
        """
        self.flagNewArea = False
        self.polygonsList2 = []
        self.view.scene().clear()
        self.btLoad.setVisible(False)
        self.btDeleteArea.setVisible(False)
        self.btNewArea.setVisible(False)
        self.saveMapAction.setEnabled(False)
        self.saveAsMapAction.setEnabled(False)
        self.addToProject.setEnabled(False)
        self.mapNameAction.setEnabled(False)
        self.statusBar().showMessage("")

        self.flagMapChanged = False


    def loadBitmap(self):
        """
        load bitmap as background for coding map
        resize bitmap to CODING_MAP_RESIZE_W x CODING_MAP_RESIZE_H defined in config.py
        """

        fn = QFileDialog(self).getOpenFileName(self, "Load bitmap", "", "bitmap files (*.png *.jpg);;All files (*)")
        fileName = fn[0] if type(fn) is tuple else fn

        if fileName:
            self.bitmapFileName = fileName

            self.pixmap.load(self.bitmapFileName)

            # scale image
            if self.pixmap.size().width() > CODING_MAP_RESIZE_W or self.pixmap.size().height() > CODING_MAP_RESIZE_H:
                self.pixmap = self.pixmap.scaled(CODING_MAP_RESIZE_W, CODING_MAP_RESIZE_H, Qt.KeepAspectRatio)
                QMessageBox.information(self, programName,
                    (f"The bitmap was resized to {self.pixmap.size().width()}x{self.pixmap.size().height()} pixels\n"
                        "The original file was not modified"))

            self.view.setSceneRect(0, 0, self.pixmap.size().width(), self.pixmap.size().height())
            pixitem = QGraphicsPixmapItem(self.pixmap)
            pixitem.setPos(0, 0)
            self.view.scene().addItem(pixitem)

            self.btNewArea.setVisible(True)

            self.btLoad.setVisible(False)
            self.saveMapAction.setEnabled(True)
            self.saveAsMapAction.setEnabled(True)
            self.addToProject.setEnabled(True)
            self.mapNameAction.setEnabled(True)

            self.statusBar().showMessage("""Click "New behavior area" to create a new behavior area""")

            self.flagMapChanged = True


if __name__ == '__main__':

    import sys
    app = QApplication(sys.argv)
    window = BehaviorsMapCreatorWindow(["North zone", "East zone", "South zone", "West zone"])
    window.resize(CODING_MAP_RESIZE_W, CODING_MAP_RESIZE_H)
    window.show()
    sys.exit(app.exec_())
