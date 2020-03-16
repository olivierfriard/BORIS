#!/usr/bin/env python3

"""
BORIS
Behavioral Observation Research Interactive Software
Copyright 2012-2018 Olivier Friard

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
    return True and coordinates of intersection point otherwise
    return False,None
    """
    getcontext().prec = 28

    Dec = decimal.Decimal
    xa, ya = Dec(str(A[0])), Dec(str(A[1]))
    xb, yb = Dec(str(B[0])), Dec(str(B[1]))
    xc, yc = Dec(str(C[0])), Dec(str(C[1]))
    xd, yd = Dec(str(D[0])), Dec(str(D[1]))

    # check if first segment is vertical
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
        # round Decimal result: .quantize(Dec('.001'), rounding=decimal.ROUND_DOWN)
        xm = ((xd * xa * yc - xd * xb * yc - xd * xa * yb - xc * xa * yd + xc * xa * yb + xd * ya * xb + xc * xb * yd - xc * ya * xb) / (-yb * xd + yb * xc + ya * xd - ya * xc + xb * yd - xb * yc - xa * yd + xa * yc)).quantize(Dec('.001'), rounding=decimal.ROUND_DOWN)
        ym = ((yb * xc * yd - yb * yc * xd - ya * xc * yd + ya * yc * xd - xa * yb * yd + xa * yb * yc + ya * xb * yd - ya * xb * yc) / (-yb * xd + yb * xc + ya * xd - ya * xc + xb * yd - xb * yc - xa * yd + xa * yc)).quantize(Dec('.001'), rounding=decimal.ROUND_DOWN)

    xmin1, xmax1 = min(xa, xb), max(xa, xb)
    xmin2, xmax2 = min(xc, xd), max(xc, xd)
    ymin1, ymax1 = min(ya, yb), max(ya, yb)
    ymin2, ymax2 = min(yc, yd), max(yc, yd)

    return (xm >= xmin1 and xm <= xmax1 and xm >= xmin2 and xm <= xmax2 and ym >= ymin1 and ym <= ymax1 and ym >= ymin2 and ym <= ymax2)


class ModifiersMapCreatorWindow(QMainWindow):

    closed = pyqtSignal()

    class View(QGraphicsView):
        """
        class for handling mousepress event in QGraphicsView
        """
        mousePress = pyqtSignal(QMouseEvent)
        def mousePressEvent(self, event):
            self.mousePress.emit( event )

        _start = 0
        elList, points = [], []

        def __init__(self, parent):
            QGraphicsView.__init__(self, parent)
            self.setBackgroundBrush(QColor(128, 128, 128))
            self.setScene(QGraphicsScene(self))
            self.scene().update()

    bitmapFileName,mapName, fileName  = "", "", ""
    flagNewArea, flagMapChanged = False, False
    areasList, polygonsList2 = {}, {}
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


        self.view = self.View(self)
        self.view.mousePress.connect(self.viewMousePressEvent)

        self.btLoad = QPushButton("Load bitmap", self)
        self.btLoad.clicked.connect(self.loadBitmap)
        self.btLoad.setVisible(False)

        self.btNewArea = QPushButton("New modifier", self)
        self.btNewArea.clicked.connect(self.newArea)
        self.btNewArea.setVisible(False)

        self.hlayout = QHBoxLayout()

        self.lb = QLabel("Modifier")
        self.lb.setVisible(False)
        self.hlayout.addWidget(self.lb)

        self.leAreaCode = QLineEdit(self)
        self.leAreaCode.setVisible(False)
        self.hlayout.addWidget(self.leAreaCode)

        self.btColor = QPushButton()
        self.btColor.clicked.connect(self.chooseColor)
        self.btColor.setVisible(False)
        self.btColor.setStyleSheet("QWidget {{background-color:{}}}".format(self.areaColor.name()))
        self.hlayout.addWidget(self.btColor)

        self.slAlpha = QSlider(Qt.Horizontal)
        self.slAlpha.setRange(20, 100)
        self.slAlpha.setValue(50)
        self.slAlpha.valueChanged.connect(self.slAlpha_changed)
        self.slAlpha.setVisible(False)
        self.hlayout.addWidget(self.slAlpha)

        self.slAlpha_changed(50)


        '''
        self.btCancelMap = QPushButton("Cancel modifiers map", self)
        self.btCancelMap.clicked.connect(self.cancelMap)
        self.btCancelMap.setVisible(False)
        '''

        layout = QVBoxLayout()
        layout.addWidget(self.view)
        layout.addWidget(self.btLoad)

        hlayout2 = QHBoxLayout()
        hlayout2.addWidget(self.btNewArea)

        self.btSaveArea = QPushButton("Save modifier", self)
        self.btSaveArea.clicked.connect(self.saveArea)
        self.btSaveArea.setVisible(False)
        hlayout2.addWidget(self.btSaveArea)

        self.btCancelAreaCreation = QPushButton("Cancel new modifier", self)
        self.btCancelAreaCreation.clicked.connect(self.cancelAreaCreation)
        self.btCancelAreaCreation.setVisible(False)
        hlayout2.addWidget(self.btCancelAreaCreation)


        self.btDeleteArea = QPushButton("Delete selected modifier", self)
        self.btDeleteArea.clicked.connect(self.deleteArea)
        self.btDeleteArea.setVisible(True)
        self.btDeleteArea.setEnabled(False)
        hlayout2.addWidget(self.btDeleteArea)

        layout.addLayout(hlayout2)
        layout.addLayout(self.hlayout)

        '''layout.addWidget(self.btCancelMap)'''

        main_widget = QWidget(self)
        main_widget.setLayout(layout)
        self.setCentralWidget(main_widget)

        self.statusBar().showMessage("")


    def slAlpha_changed(self, val):
        """
        opacity slider value changed
        """

        self.btColor.setText("Opacity: {} %".format(val))
        self.areaColor.setAlpha(int(val / 100 * 255))

        if self.selectedPolygon:
            self.selectedPolygon.setBrush(self.areaColor)
            self.areasList[self.leAreaCode.text()]["color"] = self.areaColor.rgba()

        if self.closedPolygon:
            self.closedPolygon.setBrush(self.areaColor)


    def chooseColor(self):
        """
        area color button clocked
        """
        cd = QColorDialog()

        cd.setOptions(QColorDialog.ShowAlphaChannel)

        col = cd.getColor()
        if col.isValid():
            self.btColor.setStyleSheet("QWidget {background-color:%s}" % col.name())
            self.areaColor = col

        if self.selectedPolygon:
            self.selectedPolygon.setBrush(self.areaColor)
            self.areasList[self.leAreaCode.text()]["color"] = self.areaColor.rgba()

        if self.closedPolygon:
            self.closedPolygon.setBrush(self.areaColor)


    def closeEvent(self, event):

        if self.flagMapChanged:

            response = dialog.MessageDialog("BORIS - Modifiers map creator", "What to do about the current unsaved modifiers coding map?", ["Save", "Discard", "Cancel"])

            if response == "Save":
                if not self.saveMap_clicked():
                    event.ignore()

            if response == "Cancel":
                event.ignore()
                return

        self.closed.emit()
        event.accept()


    def viewMousePressEvent(self, event):
        """
        check if area selected with mouse
        """

        if not self.bitmapFileName:
            return

        self.btDeleteArea.setEnabled(False)

        test = self.view.mapToScene(event.pos()).toPoint()

        if test.x()<0 or test.y()<0 or test.x() > self.pixmap.size().width() or test.y() > self.pixmap.size().height():
            return

        if not self.flagNewArea:   # test clicked point for areas
            txt = ""

            # reset selected polygon to default pen
            if self.selectedPolygon:
                self.selectedPolygon.setPen( QPen(designColor, penWidth, penStyle, Qt.RoundCap, Qt.RoundJoin) )
                self.selectedPolygon = None
                self.selectedPolygonMemBrush = None

            for areaCode in self.polygonsList2:

                if self.polygonsList2[areaCode].contains( test ):

                    if txt:
                        txt += ','

                    txt += areaCode
                    self.selectedPolygon = self.polygonsList2[areaCode]
                    self.selectedPolygonAreaCode = areaCode

                    self.selectedPolygonMemBrush = self.selectedPolygon.brush()

                    self.selectedPolygon.setPen(QPen(QColor(255, 0, 0, 255), 2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))

                    self.leAreaCode.setText(areaCode)
                    self.leAreaCode.setVisible(True)
                    self.btDeleteArea.setEnabled(True)

                    self.areaColor = self.selectedPolygon.brush().color()
                    self.btColor.setStyleSheet("QWidget {{background-color:{}}}".format(self.selectedPolygon.brush().color().name()))
                    self.btColor.setVisible(True)

                    self.slAlpha.setValue(int(self.selectedPolygon.brush().color().alpha() / 255 * 100))
                    self.slAlpha.setVisible(True)

                    break

            if txt:
                self.statusBar().showMessage("Modifier{}: {}".format("s" if "," in txt else "", txt))
            else:
                self.statusBar().showMessage("")

            if not self.selectedPolygon:
                self.leAreaCode.setVisible(False)
                self.btColor.setVisible(False)
                self.slAlpha.setVisible(False)
            return

        # delete last line item
        if (event.buttons() & Qt.RightButton) and not self.closedPolygon:

            if self.view.points:
                self.view.points = self.view.points[0:-1]

            if self.view.points:
                self.view._start = QPoint( self.view.points[-1][0], self.view.points[-1][1])
            else:
                self.view._start = None

            # remove graphical elements
            if self.view.elList:
                self.view.scene().removeItem(self.view.elList[-1])
                self.view.elList = self.view.elList[0:-1]

        # add line item
        if event.buttons() == Qt.LeftButton and not self.closedPolygon:

            if self.view._start :

                end = test

                # test is polygon is crossed
                if len(self.view.points) >= 3:

                    for idx, point in enumerate(self.view.points[:-2]):

                        if intersection(self.view.points[idx], self.view.points[idx + 1], self.view.points[-1], (int(end.x()), int(end.y()))) :
                            QMessageBox.critical(self, "", "The polygon edges can not be intersected")
                            return

                # test if polygon closed (dist min 10 px)
                if abs(end.x() - self.view.points[0][0]) < 10 and abs(end.y() - self.view.points[0][1]) < 10:

                    line = QGraphicsLineItem(QLineF(self.view._start, QPoint( self.view.points[0][0], self.view.points[0][1])))
                    line.setPen(QPen(designColor, penWidth, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))

                    self.view.scene().addItem( line )
                    self.view.elList.append(line)

                    self.statusBar().showMessage("Area completed")

                    # create polygon
                    newPolygon = QPolygonF()
                    for p in self.view.points:
                        newPolygon.append(QPoint(p[0], p[1]))

                    # draw polygon a red polygon
                    self.closedPolygon = QGraphicsPolygonItem(newPolygon)

                    self.closedPolygon.setPen(QPen(designColor, penWidth, penStyle, Qt.RoundCap, Qt.RoundJoin))

                    self.closedPolygon.setBrush( self.areaColor )

                    self.view.scene().addItem( self.closedPolygon )

                    return


                self.view.points.append( (  int(end.x()), int(end.y())) )

                line = QGraphicsLineItem(QLineF(self.view._start, end))

                line.setPen(QPen(designColor, 2, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))

                self.view.scene().addItem( line )
                self.view.elList.append(line)

                self.view._start = test

            else:   # first point

                self.view._start = test

                ellipse = QGraphicsEllipseItem( self.view._start.x(), self.view._start.y(), 3, 3)
                ellipse.setPen(QPen(designColor, 1, Qt.SolidLine, Qt.RoundCap, Qt.RoundJoin))

                brush = QBrush()
                brush.setStyle(Qt.SolidPattern)
                brush.setColor(designColor)
                ellipse.setBrush( brush )

                self.view.scene().addItem( ellipse )
                self.view.elList.append(ellipse)

                self.view.points.append( ( self.view._start.x(), self.view._start.y()) )


    def mapName_clicked(self):
        """
        change map name
        """
        text, ok = QInputDialog.getText(self, "Modifiers map name", "Enter a name for the modifiers map", QLineEdit.Normal, self.mapName )
        if ok:
            self.mapName = text
            self.setWindowTitle("{} - Modifiers map creator tool - {}".format(programName, self.mapName))

    def newMap(self):
        """
        create a new map
        """

        if self.flagMapChanged:

            response = dialog.MessageDialog(programName + ' - Modifiers map creator', 'What to do about the current unsaved coding map?', ['Save', 'Discard', 'Cancel'])

            if response == 'Save':
                if not self.saveMap_clicked():
                    return

            if response == 'Cancel':
                return


        self.cancelMap()

        text, ok = QInputDialog.getText(self, 'Map name', 'Enter a name for the new map')
        if ok:
            self.mapName = text
        else:
            return

        if self.mapName == '':
            QMessageBox.critical(self, '' , 'You must define a name for the new map' )
            return

        if self.mapName in ['areas','bitmap']:
            QMessageBox.critical(self, '' , 'This name is not allowed' )
            return


        self.setWindowTitle(programName + ' - Map creator tool - ' + self.mapName)

        self.btLoad.setVisible(True)
        '''self.btCancelMap.setVisible(True)'''

        self.statusBar().showMessage('Click "Load bitmap" button to select and load a bitmap into the viewer')



    def openMap(self):
        """
        load bitmap from data
        show it in view scene
        """
        if self.flagMapChanged:

            response = dialog.MessageDialog(programName + ' - Map creator', 'What to do about the current unsaved coding map?', ['Save', 'Discard', 'Cancel'])

            if response == "Save":
                if not self.saveMap_clicked():
                    return

            if response == "Cancel":
                return

        fn = QFileDialog().getOpenFileName(self, 'Open a coding map', '', 'BORIS coding map (*.boris_map);;All files (*)')
        fileName = fn[0] if type(fn) is tuple else fn

        if fileName:

            try:
                self.codingMap = json.loads( open( fileName , 'r').read() )
            except:
                QMessageBox.critical(self, programName, "The file {} seems not a behaviors coding map...".format(fileName))
                return              

            self.cancelMap()
            
            self.mapName = self.codingMap['name']

            self.setWindowTitle(programName + ' - Map creator tool - ' + self.mapName)

            self.bitmapFileName = True

            self.fileName = fileName

            self.areasList = self.codingMap['areas']   # dictionary of dictionaries
            bitmapContent = binascii.a2b_base64( self.codingMap['bitmap'] )

            self.pixmap.loadFromData(bitmapContent)

            self.btDeleteArea.setEnabled(False)


            self.view.setSceneRect(0, 0, self.pixmap.size().width(), self.pixmap.size().height())
            pixItem = QGraphicsPixmapItem(self.pixmap)
            pixItem.setPos(0,0)
            self.view.scene().addItem(pixItem)

            for areaCode in self.areasList:
                points = self.areasList[ areaCode ]['geometry']

                newPolygon = QPolygonF()
                for p in points:
                    newPolygon.append(QPoint(p[0], p[1]))


                clr = QColor( )
                clr.setRgba( self.areasList[ areaCode ]['color'] )

                # draw polygon
                polygon = QGraphicsPolygonItem()


                polygon.setPolygon(newPolygon)

                polygon.setPen(QPen(clr, penWidth, penStyle, Qt.RoundCap, Qt.RoundJoin))

                polygon.setBrush( QBrush( clr, Qt.SolidPattern ) )

                self.view.scene().addItem( polygon )
                self.polygonsList2[ areaCode ] = polygon

            self.btNewArea.setVisible(True)

            self.btLoad.setVisible(False)

            self.saveMapAction.setEnabled(True)
            self.saveAsMapAction.setEnabled(True)
            self.mapNameAction.setEnabled(True)
            self.statusBar().showMessage('Click "New area" to create a new area')
        else:
            self.statusBar().showMessage('No file', 5000)



    def saveMap(self):

        if self.fileName:

            # create dict with map name key
            mapDict = { 'name' : self.mapName}

            # add areas
            mapDict['areas'] = self.areasList

            import io

            # Save QPixmap to QByteArray via QBuffer.
            byte_array = QByteArray()
            buffer = QBuffer(byte_array)
            buffer.open(QIODevice.WriteOnly)
            self.pixmap.save(buffer, 'PNG')

            string_io = io.BytesIO( byte_array )

            string_io.seek(0)

            # add bitmap
            mapDict[ 'bitmap' ] = binascii.b2a_base64(string_io.read()).decode('utf-8')

            with open(self.fileName, 'w') as outfile:
                outfile.write(json.dumps( mapDict ))

            self.flagMapChanged = False

            return True
        else:
            return False


    def saveAsMap_clicked(self):

        filters = "Modifiers map (*.boris_map);;All files (*)"

        fn = QFileDialog(self).getSaveFileName(self, "Save modifiers map as", "", filters)
        if type(fn) is tuple:
            self.fileName, _ = fn
        else:
            self.fileName = fn

        if self.fileName:
            if os.path.splitext(self.fileName)[1] != '.boris_map':
                self.fileName += '.boris_map'
            self.saveMap()


    def saveMap_clicked(self):


        if not self.fileName:

            fn = QFileDialog(self).getSaveFileName(self, 'Save modifiers map', self.mapName + '.boris_map' , 'BORIS MAP (*.boris_map);;All files (*)')
            if type(fn) is tuple:
                self.fileName, _ = fn
            else:
                self.fileName = fn

            if self.fileName and os.path.splitext(self.fileName)[1] != '.boris_map':
                self.fileName += '.boris_map'

        if self.fileName:
            return self.saveMap()

        return False


    def newArea(self):

        if not self.bitmapFileName:
            QMessageBox.critical(self, programName , "A bitmap must be loaded before to define areas")
            return

        if self.selectedPolygon:
            self.selectedPolygon.setPen( QPen(designColor, penWidth, penStyle, Qt.RoundCap, Qt.RoundJoin) )
            self.selectedPolygon = None

        self.flagNewArea = True
        self.btSaveArea.setVisible(True)
        self.btCancelAreaCreation.setVisible(True)
        self.btNewArea.setVisible(False)
        self.lb.setVisible(True)
        self.leAreaCode.clear()
        self.leAreaCode.setVisible(True)
        self.btColor.setVisible(True)
        self.slAlpha.setVisible(True)
        self.btDeleteArea.setVisible(False)

        self.statusBar().showMessage('Select the vertices of the area for this modifier with the mouse (right click will cancel the last point)')

    def saveArea(self):

        if not self.closedPolygon:
            QMessageBox.critical(self, programName , 'You must close your area before saving it.\nThe last vertex must correspond to the first one.' )

        if len(self.view.points) < 3:
            QMessageBox.critical(self, programName , 'You must define a closed area' )
            return

        # check if no area code
        if not self.leAreaCode.text():
            QMessageBox.critical(self, programName , 'You must define a code for the new modifier' )
            return

        # check if not allowed character
        for c in "|,()":
            if c in self.leAreaCode.text():
                QMessageBox.critical(self, programName , 'The modifier contains a character that is not allowed <b>()|,</b>.' )
                return

        # check if area code already used

        if self.leAreaCode.text() in self.areasList:
            QMessageBox.critical(self, programName , "The modifier is already in use" )
            return

        # create polygon
        newPolygon = QPolygon()
        for p in self.view.points:
            newPolygon.append(QPoint(p[0], p[1]))

        self.areasList[ self.leAreaCode.text() ] = {'geometry': self.view.points, 'color': self.areaColor.rgba() }

        # remove all lines
        for l in self.view.elList:
            self.view.scene().removeItem( l )

        # draw polygon
        self.closedPolygon.setBrush( QBrush( self.areaColor, Qt.SolidPattern ) )
        self.polygonsList2[ self.leAreaCode.text()  ] = self.closedPolygon
        self.closedPolygon = None
        self.view._start = 0
        self.view.points = []
        self.view.elList = []
        self.flagNewArea = False
        self.closedPolygon = None

        self.btSaveArea.setVisible(False)
        self.btCancelAreaCreation.setVisible(False)
        self.lb.setVisible(False)
        self.leAreaCode.setVisible(False)
        self.btColor.setVisible(False)
        self.slAlpha.setVisible(False)
        self.btDeleteArea.setVisible(True)
        self.btNewArea.setVisible(True)

        self.leAreaCode.setText("")

        self.flagMapChanged = True
        self.statusBar().showMessage("New modifier saved", 5000)

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
        self.btDeleteArea.setVisible(True)
        self.btSaveArea.setVisible(False)
        self.lb.setVisible(False)

        self.btColor.setVisible(False)
        self.slAlpha.setVisible(False)
        self.btNewArea.setVisible(True)

        self.leAreaCode.setVisible(False)
        self.leAreaCode.setText("")


    def deleteArea(self):
        """
        remove selected area from map
        """
        print("cancel")

        print(self.selectedPolygon)
        print( self.closedPolygon )
        print( self.view.elList )

        if self.selectedPolygon:
            print("selected polygon")
            self.view.scene().removeItem(self.selectedPolygon)
            self.view.scene().removeItem( self.polygonsList2[self.selectedPolygonAreaCode])

            del self.polygonsList2[self.selectedPolygonAreaCode]
            del self.areasList[self.selectedPolygonAreaCode]

            self.flagMapChanged = True


        # remove all lines
        '''
        for l in self.view.elList:
            self.view.scene().removeItem(l)
        '''

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

    def cancelMap(self):
        """
        remove current map
        """
        self.flagNewArea = False
        self.areasList = {}
        self.polygonsList2 = {}
        self.view.scene().clear()
        self.btLoad.setVisible(False)
        '''self.btCancelMap.setVisible(False)'''
        self.btDeleteArea.setVisible(False)
        self.btNewArea.setVisible(False)
        self.saveMapAction.setEnabled(False)
        self.saveAsMapAction.setEnabled(False)
        self.mapNameAction.setEnabled(False)
        self.statusBar().showMessage("")
        self.flagMapChanged = False


    def loadBitmap(self):
        '''
        load bitmap as background for coding map
        resize bitmap to 512 px if bigger
        '''

        maxSize = 512

        fn = QFileDialog().getOpenFileName(self, "Load bitmap", "", "bitmap files (*.png *.jpg);;All files (*)")
        fileName = fn[0] if type(fn) is tuple else fn

        if fileName:
            self.bitmapFileName = fileName

            self.pixmap.load(self.bitmapFileName)

            if self.pixmap.size().width() > maxSize or self.pixmap.size().height() > maxSize:
                self.pixmap = self.pixmap.scaled (maxSize, maxSize, Qt.KeepAspectRatio)
                QMessageBox.information(self, programName , 'The bitmap was resized to %d x %d pixels\nThe original file was not modified' % (self.pixmap.size().width(), self.pixmap.size().height() ) )

            # scale image
            # pixmap = pixmap.scaled (256, 256, Qt.KeepAspectRatio)

            self.view.setSceneRect(0, 0, self.pixmap.size().width(), self.pixmap.size().height())
            pixitem = QGraphicsPixmapItem(self.pixmap)
            pixitem.setPos(0, 0)
            self.view.scene().addItem(pixitem)

            self.btNewArea.setVisible(True)

            self.btLoad.setVisible(False)
            self.saveMapAction.setEnabled(True)
            self.saveAsMapAction.setEnabled(True)
            self.mapNameAction.setEnabled(True)

            self.statusBar().showMessage("""Click "New modifier" to create a new modifier""")

            self.flagMapChanged = True

if __name__ == '__main__':

    import sys
    app = QApplication(sys.argv)
    window = ModifiersMapCreatorWindow()
    window.resize(640, 640)
    window.show()
    sys.exit(app.exec_())
