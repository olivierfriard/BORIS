#!/usr/bin/env python3

"""
BORIS
Behavioral Observation Research Interactive Software
Copyright 2012-2017 Olivier Friard

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

codeSeparator = ","

try:
    from PyQt5.QtGui import *
    from PyQt5.QtCore import *
    from PyQt5.QtWidgets import *
except:
    from PyQt4.QtGui import *
    from PyQt4.QtCore import *

import json
import binascii
import os
import config

class BehaviorsCodingMapWindowClass(QWidget):

    class View(QGraphicsView):

        mousePress = pyqtSignal(QMouseEvent)
        def mousePressEvent(self, event):
            self.mousePress.emit(event)

        _start=0
        elList = []
        points = []

        def __init__(self, parent):
            QGraphicsView.__init__(self, parent)
            self.setScene(QGraphicsScene(self))
            self.scene().update()

    areasList = {}
    polygonsList2 = {}

    clickSignal = pyqtSignal(str)  # click signal to be sent to mainwindow
    keypressSignal = pyqtSignal(QEvent)

    def __init__(self, behaviors_coding_map):
        super(BehaviorsCodingMapWindowClass, self).__init__()
        
        self.installEventFilter(self)

        self.codingMap = behaviors_coding_map
        self.setWindowTitle("Behaviors coding map: {}".format(self.codingMap["name"]))
        Vlayout = QVBoxLayout(self)

        self.view = self.View(self)
        self.view.mousePress.connect(self.viewMousePressEvent)

        #self.leareaCode = QLineEdit(self)
        #self.leareaCode.setVisible(True)

        Vlayout.addWidget(self.view)
        #Vlayout.addWidget(self.leareaCode)

        hBoxLayout = QHBoxLayout(self)

        spacerItem = QSpacerItem(241, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)
        hBoxLayout.addItem(spacerItem)

        #self.pbCancel = QPushButton("Cancel")
        #hBoxLayout.addWidget(self.pbCancel)
        #self.pbCancel.clicked.connect(self.reject)

        self.btDone = QPushButton("Close", self)
        #self.btDone.clicked.connect(self.accept)
        self.btDone.clicked.connect(self.close)
        self.btDone.setVisible(True)

        hBoxLayout.addWidget(self.btDone)

        Vlayout.addLayout(hBoxLayout)

        self.setLayout(Vlayout)

        self.loadMap()

    '''
    def click(self, behaviorCode):
        self.clickSignal.emit(behaviorCode)
    '''

    def eventFilter(self, receiver, event):
        """
        send event (if keypress) to main window
        """
        if(event.type() == QEvent.KeyPress):
            self.keypressSignal.emit(event)
            return True
        else:
            return False


    def viewMousePressEvent(self, event):
        """
        insert clicked areas codes
        """

        test = self.view.mapToScene(event.pos()).toPoint()

        for areaCode, pg in self.polygonsList2:
            if pg.contains(test):
                self.clickSignal.emit(code)

        '''
        for code in self.polygonsList2:
            if self.polygonsList2[ code ].contains(test):
                self.clickSignal.emit(code)
        '''


    '''
    def getCodes(self):
        return self.leareaCode.text()
    '''


    def loadMap(self):
        """
        load bitmap from data
        show it in view scene
        """

        #self.areasList = self.codingMap

        bitmapContent = binascii.a2b_base64(self.areasList["bitmap"])

        pixmap = QPixmap()
        pixmap.loadFromData(bitmapContent)

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
            polygon = QGraphicsPolygonItem(None, None) if QT_VERSION_STR[0] == "4" else QGraphicsPolygonItem()
            polygon.setPolygon(newPolygon)
            clr = QColor()
            clr.setRgba(self.codingMap["areas"][key]["color"])
            polygon.setPen(QPen(clr, penWidth, penStyle, Qt.RoundCap, Qt.RoundJoin))
            polygon.setBrush(QBrush(clr, Qt.SolidPattern))

            self.view.scene().addItem(polygon)
            
            self.polygonsList2.append([areaCode, polygon])





        '''
        for area in self.areasList["areas"]:
            points = self.areasList["areas"][area]["geometry"]

            newPolygon = QPolygonF()
            for p in points:
                newPolygon.append(QPoint(p[0], p[1]))

            clr = QColor()
            clr.setRgba(self.areasList["areas"][area]['color'])

            # draw polygon
            #polygon = QGraphicsPolygonItem( None, None)
            #polygon.setPolygon(newPolygon)

            polygon = QGraphicsPolygonItem(newPolygon, None, None) if QT_VERSION_STR[0] == "4" else QGraphicsPolygonItem(newPolygon)

            polygon.setPen(QPen(clr, 0, Qt.NoPen, Qt.RoundCap, Qt.RoundJoin))

            polygon.setBrush(QBrush(clr, Qt.SolidPattern))

            self.view.scene().addItem(polygon)
            #self.polygonsList2[area] = polygon
            self.polygonsList2.append([areaCode, polygon])
        '''


if __name__ == '__main__':

    import sys
    app = QApplication(sys.argv)

    if len(sys.argv) > 1:
        cm = json.loads(open(sys.argv[1], "r").read())
        codingMapWindow = codingMapWindowClass(cm)
        codingMapWindow.resize(config.CODING_MAP_RESIZE_W, config.CODING_MAP_RESIZE_H)
        codingMapWindow.show()
        sys.exit(app.exec_())
