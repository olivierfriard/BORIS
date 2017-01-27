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

class ModifiersCodingMapWindowClass(QDialog):

    class View(QGraphicsView):

        mousePress = pyqtSignal(QMouseEvent)
        def mousePressEvent(self, event):
            self.mousePress.emit( event )

        _start=0
        elList = []
        points = []

        def __init__(self, parent):
            QGraphicsView.__init__(self, parent)
            self.setScene(QGraphicsScene(self))
            self.scene().update()

    areasList = {}
    polygonsList2 = {}

    def __init__(self, modifiers_coding_map):
        super(ModifiersCodingMapWindowClass, self).__init__()

        self.codingMap = modifiers_coding_map
        self.setWindowTitle(self.codingMap["name"])
        Vlayout = QVBoxLayout(self)

        self.view = self.View(self)
        self.view.mousePress.connect(self.viewMousePressEvent)

        self.leareaCode = QLineEdit(self)
        self.leareaCode.setVisible(True)

        Vlayout.addWidget(self.view)
        Vlayout.addWidget(self.leareaCode)

        hBoxLayout = QHBoxLayout(self)

        spacerItem = QSpacerItem(241, 20, QSizePolicy.Expanding, QSizePolicy.Minimum)
        hBoxLayout.addItem(spacerItem)

        self.pbCancel = QPushButton("Cancel")
        hBoxLayout.addWidget(self.pbCancel)
        self.pbCancel.clicked.connect(self.reject)

        self.btDone = QPushButton("Done", self)
        self.btDone.clicked.connect(self.accept)
        self.btDone.setVisible(True)

        hBoxLayout.addWidget(self.btDone)

        #Vlayout.addWidget(self.btDone)
        Vlayout.addLayout(hBoxLayout)

        self.setLayout(Vlayout)

        self.loadMap()


    def viewMousePressEvent(self, event):
        """
        insert clicked areas codes
        """

        test = self.view.mapToScene(event.pos()).toPoint()

        for code in self.polygonsList2:
            if self.polygonsList2[ code ].contains(test):

                codes = self.leareaCode.text().split(codeSeparator)
                if "" in codes:
                    codes.remove("")

                # check if code already in codes list
                if code in codes:
                    codes.remove(code)
                else:
                    codes.append(code)

                self.leareaCode.setText(codeSeparator.join(sorted(codes)))

    def getCodes(self):
        return self.leareaCode.text()


    def loadMap(self):
        """
        load bitmap from data
        show it in view scene
        """

        self.areasList = self.codingMap

        bitmapContent = binascii.a2b_base64(self.areasList["bitmap"])

        pixmap = QPixmap()
        pixmap.loadFromData(bitmapContent)

        self.view.setSceneRect(0, 0, pixmap.size().width(), pixmap.size().height())
        pixItem = QGraphicsPixmapItem(pixmap)
        pixItem.setPos(0,0)
        self.view.scene().addItem(pixItem)

        for area in self.areasList["areas"]:
            points = self.areasList["areas"][area]["geometry"]

            newPolygon = QPolygonF()
            for p in points:
                newPolygon.append(QPoint(p[0], p[1]))

            clr = QColor( )
            clr.setRgba( self.areasList["areas"][ area]['color'] )

            # draw polygon
            #polygon = QGraphicsPolygonItem( None, None)
            #polygon.setPolygon(newPolygon)

            if QT_VERSION_STR[0] == "4":
                polygon = QGraphicsPolygonItem(newPolygon, None, None)
            else:
                polygon = QGraphicsPolygonItem(newPolygon)

            polygon.setPen(QPen(clr, 0, Qt.NoPen, Qt.RoundCap, Qt.RoundJoin))

            polygon.setBrush( QBrush(clr, Qt.SolidPattern))

            self.view.scene().addItem( polygon )
            self.polygonsList2[ area ] = polygon


if __name__ == '__main__':

    import sys
    app = QApplication(sys.argv)

    if len(sys.argv) > 1:
        cm = json.loads(open( sys.argv[1], "r").read())
        codingMapWindow = codingMapWindowClass(cm)
        codingMapWindow.resize(640, 640)
        codingMapWindow.show()
        sys.exit(app.exec_())
