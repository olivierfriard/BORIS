"""
BORIS
Behavioral Observation Research Interactive Software
Copyright 2012-2023 Olivier Friard

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

import logging
import io
import pandas as pd
import pathlib as pl

try:
    import pyreadr

    flag_pyreadr_loaded = True
except ModuleNotFoundError:
    flag_pyreadr_loaded = False


from PyQt5.QtCore import QPoint, Qt, pyqtSignal, QEvent
from PyQt5.QtGui import QColor, QPainter, QPolygon, QPixmap
from PyQt5.QtWidgets import (
    QApplication,
    QCheckBox,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QTableWidget,
    QTableWidgetItem,
    QPushButton,
    QRadioButton,
    QVBoxLayout,
    QWidget,
    QColorDialog,
    QSpacerItem,
    QSizePolicy,
    QAction,
)

from typing import Union, Optional, List, Tuple, Dict

from . import config as cfg
from . import dialog, menu_options
from . import utilities as util


class wgMeasurement(QWidget):
    """
    widget for geometric measurements
    """

    closeSignal = pyqtSignal()
    send_event_signal = pyqtSignal(QEvent)
    reload_image_signal  = pyqtSignal(int)
    save_picture_signal  = pyqtSignal(int)
    mark_color: str = cfg.ACTIVE_MEASUREMENTS_COLOR
    flag_saved = True  # store if measurements are saved
    draw_mem: dict = {}

    def __init__(self):
        super().__init__()

        self.setWindowTitle("Geometric measurements")

        vbox = QVBoxLayout(self)

        self.rbPoint = QRadioButton("Point (left click)")
        vbox.addWidget(self.rbPoint)

        self.rb_polygon = QRadioButton("Polyline (left click for vertices, right click to finish)")
        vbox.addWidget(self.rb_polygon)


        #self.rbDistance = QRadioButton("Distance (start: left click, end: right click)")
        #vbox.addWidget(self.rbDistance)

        self.rbArea = QRadioButton("Area (left click for area vertices, right click to close area)")
        vbox.addWidget(self.rbArea)

        self.rb_angle = QRadioButton("Angle (vertex: left click, segments: right click)")
        vbox.addWidget(self.rb_angle)


        hbox = QHBoxLayout()
        self.cbPersistentMeasurements = QCheckBox("Measurements are persistent")
        self.cbPersistentMeasurements.setChecked(True)
        hbox.addWidget(self.cbPersistentMeasurements)

        # color chooser
        self.bt_color_chooser = QPushButton("Choose color of marks", clicked=self.choose_marks_color)
        self.bt_color_chooser.setStyleSheet(f"QWidget {{background-color:{self.mark_color}}}")
        hbox.addWidget(self.bt_color_chooser)

        self.pb_save_picture = QPushButton("Save picture", clicked=self.pb_save_picture_clicked)
        hbox.addWidget(self.pb_save_picture)


        hbox.addItem(QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))

        vbox.addLayout(hbox)

        vbox.addWidget(QLabel("<b>Scale</b>"))

        hbox1 = QHBoxLayout()
        self.lbRef = QLabel("Reference")
        hbox1.addWidget(self.lbRef)
        self.lbPx = QLabel("Pixels")
        hbox1.addWidget(self.lbPx)
        vbox.addLayout(hbox1)

        hbox2 = QHBoxLayout()
        self.leRef = QLineEdit()
        self.leRef.setText("1")
        hbox2.addWidget(self.leRef)
        self.lePx = QLineEdit()
        self.lePx.setText("1")
        hbox2.addWidget(self.lePx)
        vbox.addLayout(hbox2)

        self.pte = QTableWidget()
        self.pte.verticalHeader().hide()

        # header
        self.measurements_header = [
            "Player",
            "Time",
            "Frame index",
            "Type of measurement",
            "x",
            "y",
            "Distance",
            "Area",
            "Angle",
            "Coordinates",
        ]
        self.pte.setColumnCount(len(self.measurements_header))
        self.pte.setHorizontalHeaderLabels(self.measurements_header)

        self.pte.setSelectionBehavior(QTableWidget.SelectRows)
        self.pte.setSelectionMode(QTableWidget.MultiSelection)

        self.pte.setContextMenuPolicy(Qt.ActionsContextMenu)

        self.action = QAction("Delete measurement")
        self.action.triggered.connect(self.delete_measurement)

        self.pte.addAction(self.action)

        vbox.addWidget(self.pte)

        self.status_lb = QLabel()
        vbox.addWidget(self.status_lb)

        hbox3 = QHBoxLayout()
        hbox3.addItem(QSpacerItem(40, 20, QSizePolicy.Expanding, QSizePolicy.Minimum))
        self.pbClear = QPushButton("Clear measurements", clicked=self.pbClear_clicked)
        hbox3.addWidget(self.pbClear)
        self.pbSave = QPushButton("Save results", clicked=self.pbSave_clicked)
        hbox3.addWidget(self.pbSave)
        self.pbClose = QPushButton("Close", clicked=self.pbClose_clicked)
        hbox3.addWidget(self.pbClose)
        vbox.addLayout(hbox3)

        self.installEventFilter(self)

    def eventFilter(self, receiver, event):
        """
        send event (if keypress) to main window
        """
        if event.type() == QEvent.KeyPress:
            self.send_event_signal.emit(event)
            return True
        else:
            return False

    def pb_save_picture_clicked(self):
        self.save_picture_signal.emit(1)

    def delete_measurement(self):
        """
        delete the selected measurement(s)
        """
        print(self.draw_mem)

        if not self.pte.selectedItems():
            return

        rows_to_delete = []
        for item in self.pte.selectedItems():
            if item.row() not in rows_to_delete:
                rows_to_delete.append(item.row())

        elements_to_delete = []
        for row in sorted(rows_to_delete, reverse=True):

            player = int(self.pte.item(row, 0).text())
            frame_idx = int(self.pte.item(row, 2).text())
            obj_type = self.pte.item(row, 3).text()
            coord = eval(self.pte.item(row, 9).text())

            if frame_idx in self.draw_mem:
                for idx, element in enumerate(self.draw_mem[frame_idx]):
                    if (element['player'] == player - 1) and (element['object_type']  == obj_type) and (element['coordinates'] == coord):
                        elements_to_delete.append((frame_idx, idx))

            self.pte.removeRow(row)
            self.pte.flag_saved = False

        for frame_idx, idx in sorted(elements_to_delete, reverse=True):
            self.draw_mem[frame_idx].pop(idx)

        print(f"after deletion {self.draw_mem=}")

        self.reload_image_signal.emit(1)
        #redraw_measurements(self.mw)

    def choose_marks_color(self):
        """
        show the color chooser dialog
        """
        cd = QColorDialog()
        cd.setWindowFlags(Qt.WindowStaysOnTopHint)
        cd.setOptions(QColorDialog.ShowAlphaChannel | QColorDialog.DontUseNativeDialog)
        cd.setCurrentColor(QColor(self.mark_color))

        if cd.exec_():
            new_color = cd.currentColor()
            self.bt_color_chooser.setStyleSheet(f"QWidget {{background-color:{new_color.name()}}}")
            self.mark_color = new_color.name()

    def closeEvent(self, event):
        """
        Intercept the close event to check if measurements are saved
        """

        logging.debug("close event")

        if not self.flag_saved:
            response = dialog.MessageDialog(
                cfg.programName,
                "The current measurements are not saved. Do you want to save the measurement results before closing?",
                (cfg.YES, cfg.NO, cfg.CANCEL),
            )
            if response == cfg.YES:
                self.pbSave_clicked()
            if response == cfg.CANCEL:
                event.ignore()
                return

        self.flag_saved = True
        self.draw_mem = {}
        self.closeSignal.emit()

    def pbClear_clicked(self):
        """
        clear measurements draw and results
        """

        if not self.flag_saved:
            response = dialog.MessageDialog(
                cfg.programName,
                "Confirm clearing",
                (cfg.YES, cfg.CANCEL),
            )
            if response == cfg.CANCEL:
                return

        self.draw_mem = {}
        self.pte.clear()
        self.pte.setColumnCount(len(self.measurements_header))
        self.pte.setRowCount(0)
        self.pte.setHorizontalHeaderLabels(self.measurements_header)
        self.flag_saved = True

    def pbClose_clicked(self):
        """
        Close button
        """
        logging.debug("close function")
        self.close()

    def pbSave_clicked(self):
        """
        Save measurements results
        """

        file_formats = [cfg.TSV, cfg.CSV, cfg.ODS, cfg.XLSX, cfg.HTML, cfg.PANDAS_DF]
        if flag_pyreadr_loaded:
            file_formats.append(cfg.RDS)

        file_name, filter_ = QFileDialog().getSaveFileName(self, "Save geometric measurements", "", ";;".join(file_formats))
        if not file_name:
            return

        # add correct file extension if not present
        if pl.Path(file_name).suffix != f".{cfg.FILE_NAME_SUFFIX[filter_]}":
            file_name = str(pl.Path(file_name)) + "." + cfg.FILE_NAME_SUFFIX[filter_]
            # check if file with new extension already exists
            if pl.Path(file_name).is_file():
                if (
                    dialog.MessageDialog(cfg.programName, f"The file {file_name} already exists.", (cfg.CANCEL, cfg.OVERWRITE))
                    == cfg.CANCEL
                ):
                    return

        plain_text: str = "\t".join(self.measurements_header) + "\n"
        for row in range(self.pte.rowCount()):
            row_content: list = []
            for col in range(self.pte.columnCount()):
                row_content.append(self.pte.item(row, col).text())
            plain_text += "\t".join(row_content) + "\n"

        plain_text = plain_text[:-1]

        df = pd.read_csv(io.StringIO(plain_text), sep="\t")

        try:
            if filter_ == cfg.ODS:
                df.to_excel(file_name, engine="odf", sheet_name="Geometric measurements", index=False, na_rep="NA")
                self.flag_saved = True
            if filter_ == cfg.XLSX:
                df.to_excel(file_name, sheet_name="Geometric measurements", index=False, na_rep="NA")
                self.flag_saved = True
            if filter_ == cfg.HTML:
                df.to_html(file_name, index=False, na_rep="NA")
                self.flag_saved = True
            if filter_ == cfg.CSV:
                df.to_csv(file_name, index=False, sep=",", na_rep="NA")
                self.flag_saved = True
            if filter_ == cfg.TSV:
                df.to_csv(file_name, index=False, sep="\t", na_rep="NA")
                self.flag_saved = True
            if filter_ == cfg.PANDAS_DF:
                df.to_pickle(file_name)
            if filter_ == cfg.RDS:
                pyreadr.write_rds(file_name, df)

        except Exception:
            QMessageBox.warning(self, cfg.programName, "An error occured during saving the measurement results")


def show_widget(self):
    """
    active the geometric measurement widget
    """

    def close_measurement_widget():
        """
        close the geometric measurement widget
        """

        logging.debug("close_measurement_widget")

        if self.observationId and self.pj[cfg.OBSERVATIONS][self.observationId][cfg.TYPE] == cfg.MEDIA:
            for n_player, dw in enumerate(self.dw_player):
                dw.frame_viewer.clear()
                dw.stack.setCurrentIndex(cfg.VIDEO_VIEWER)
                dw.setWindowTitle(f"Player #{n_player + 1}")
            self.actionPlay.setEnabled(True)

        if self.observationId and self.pj[cfg.OBSERVATIONS][self.observationId][cfg.TYPE] == cfg.IMAGES:
            for dw in self.dw_player:
                self.extract_frame(dw)

        self.geometric_measurements_mode = False
        self.measurement_w.draw_mem = {}

        self.measurement_w.close()
        menu_options.update_menu(self)

    self.geometric_measurements_mode = True
    self.pause_video()

    menu_options.update_menu(self)

    self.actionPlay.setEnabled(False)

    self.measurement_w = wgMeasurement()
    self.measurement_w.setWindowFlags(Qt.WindowStaysOnTopHint)
    self.measurement_w.closeSignal.connect(close_measurement_widget)
    self.measurement_w.send_event_signal.connect(self.signal_from_widget)
    self.measurement_w.reload_image_signal.connect(self.reload_frame)
    self.measurement_w.save_picture_signal.connect(self.save_picture_with_measurements)
    self.measurement_w.draw_mem = {}

    self.measurement_w.show()

    for dw in self.dw_player:
        dw.setWindowTitle("Geometric measurements")
        dw.stack.setCurrentIndex(cfg.PICTURE_VIEWER)
        self.extract_frame(dw)


def draw_point(self, x: int, y: int, color: str, n_player: int = 0) -> None:
    """
    draw point on frame-by-frame image
    """
    RADIUS = 6
    painter = QPainter()
    painter.begin(self.dw_player[n_player].frame_viewer.pixmap())
    painter.setPen(QColor(color))
    painter.drawEllipse(QPoint(x, y), RADIUS, RADIUS)
    # cross inside circle
    painter.drawLine(x - RADIUS, y, x + RADIUS, y)
    painter.drawLine(x, y - RADIUS, x, y + RADIUS)
    painter.end()
    self.dw_player[n_player].frame_viewer.update()


def draw_line(self, x1: int, y1: int, x2: int, y2: int, color: str, n_player: int = 0) -> None:
    """
    draw line on frame-by-frame image
    """
    painter = QPainter()
    painter.begin(self.dw_player[n_player].frame_viewer.pixmap())
    painter.setPen(QColor(color))
    painter.drawLine(x1, y1, x2, y2)
    painter.end()
    self.dw_player[n_player].frame_viewer.update()


def append_results(self, results: List):
    """
    append results to plain text widget
    """
    self.measurement_w.pte.setRowCount(self.measurement_w.pte.rowCount() + 1)
    for idx, x in enumerate(results):
        item = QTableWidgetItem()
        item.setText(str(x))
        item.setFlags(Qt.ItemIsSelectable | Qt.ItemIsEnabled)
        self.measurement_w.pte.setItem(self.measurement_w.pte.rowCount() - 1, idx, item)


def image_clicked(self, n_player: int, event) -> None:
    """
    Geometric measurements on image

    Args:
        n_player (int): id of clicked player
        event (Qevent): event (mousepressed)
    """

    logging.debug("function image_clicked")





    if not self.geometric_measurements_mode:
        return

    if self.mem_player != -1 and n_player != self.mem_player:
        self.mem_player = n_player
        return

    self.mem_player = n_player
    if self.pj[cfg.OBSERVATIONS][self.observationId][cfg.TYPE] == cfg.MEDIA:
        if self.dw_player[n_player].player.estimated_frame_number is not None:
            current_frame = self.dw_player[n_player].player.estimated_frame_number + 1
        else:
            current_frame = cfg.NA
    elif self.pj[cfg.OBSERVATIONS][self.observationId][cfg.TYPE] == cfg.IMAGES:
        current_frame = self.image_idx

    if not (hasattr(self, "measurement_w") and (self.measurement_w is not None) and (self.measurement_w.isVisible())):
        return
 
    x, y = event.pos().x(), event.pos().y()

    # convert label coordinates in pixmap coordinates
    pixmap_x = int(x - (self.dw_player[n_player].frame_viewer.width() - self.dw_player[n_player].frame_viewer.pixmap().width()) / 2)
    pixmap_y = int(y - (self.dw_player[n_player].frame_viewer.height() - self.dw_player[n_player].frame_viewer.pixmap().height()) / 2)

    if self.pj[cfg.OBSERVATIONS][self.observationId][cfg.TYPE] == cfg.MEDIA:
        # convert pixmap coordinates in video coordinates
        x_video = round((pixmap_x / self.dw_player[n_player].frame_viewer.pixmap().width()) * self.dw_player[n_player].player.width)
        y_video = round((pixmap_y / self.dw_player[n_player].frame_viewer.pixmap().height()) * self.dw_player[n_player].player.height)
    elif self.pj[cfg.OBSERVATIONS][self.observationId][cfg.TYPE] == cfg.IMAGES:
        original_width = QPixmap(self.images_list[self.image_idx]).size().width()
        original_height = QPixmap(self.images_list[self.image_idx]).size().height()
        x_video = round((pixmap_x / self.dw_player[n_player].frame_viewer.pixmap().width()) * original_width)
        y_video = round((pixmap_y / self.dw_player[n_player].frame_viewer.pixmap().height()) * original_height)

    if not (
        0 <= pixmap_x <= self.dw_player[n_player].frame_viewer.pixmap().width()
        and 0 <= pixmap_y <= self.dw_player[n_player].frame_viewer.pixmap().height()
    ):
        self.measurement_w.status_lb.setText("<b>The click is outside the video area</b>")
        return

    self.measurement_w.status_lb.clear()

    # point
    if self.measurement_w.rbPoint.isChecked():
        if event.button() == Qt.LeftButton:
            draw_point(self, pixmap_x, pixmap_y, self.measurement_w.mark_color, n_player)
            if current_frame not in self.measurement_w.draw_mem:
                self.measurement_w.draw_mem[current_frame] = []

            self.measurement_w.draw_mem[current_frame].append(
                {'player': n_player, 'object_type': cfg.POINT_OBJECT, "color": self.measurement_w.mark_color, "coordinates": [(x_video, y_video)]}
                )

            append_results(
                self,
                (
                    n_player + 1,
                    f"{self.getLaps():.03f}",
                    current_frame,
                    cfg.POINT_OBJECT,
                    x_video,
                    y_video,
                    cfg.NA,
                    cfg.NA,
                    cfg.NA,
                    str([(x_video, y_video)]),
                ),
            )

            self.measurement_w.flag_saved = False

        # distance
        '''
        elif self.measurement_w.rbDistance.isChecked():
            if event.button() == Qt.LeftButton:
                draw_point(self, pixmap_x, pixmap_y, self.measurement_w.mark_color, n_player)
                self.memx, self.memy = round(pixmap_x), round(pixmap_y)
                self.memx_video, self.memy_video = round(x_video), round(y_video)

            if event.button() == Qt.RightButton and self.memx != -1 and self.memy != -1:
                draw_point(self, pixmap_x, pixmap_y, self.measurement_w.mark_color, n_player)
                draw_line(self, self.memx, self.memy, pixmap_x, pixmap_y, self.measurement_w.mark_color, n_player)

                if current_frame not in self.measurement_w.draw_mem:
                    self.measurement_w.draw_mem[current_frame] = []

                self.measurement_w.draw_mem[current_frame].append(
                    {'player': n_player, 'object_type': cfg.SEGMENT_OBJECT, "color": self.measurement_w.mark_color, "coordinates": [(self.memx_video, self.memy_video), (x_video, y_video)]}
                    
                )

                distance = ((x_video - self.memx_video) ** 2 + (y_video - self.memy_video) ** 2) ** 0.5
                try:
                    distance = distance / float(self.measurement_w.lePx.text()) * float(self.measurement_w.leRef.text())
                except Exception:
                    QMessageBox.critical(
                        None,
                        cfg.programName,
                        "Check reference and pixel values! Values must be numeric.",
                        QMessageBox.Ok | QMessageBox.Default,
                        QMessageBox.NoButton,
                    )

                append_results(
                    self,
                    (
                        n_player + 1,
                        f"{self.getLaps():.03f}",
                        current_frame,
                        cfg.SEGMENT_OBJECT,
                        cfg.NA,
                        cfg.NA,
                        round(distance, 3),
                        cfg.NA,
                        cfg.NA,
                        str([(self.memx_video, self.memy_video), (x_video, y_video)]),
                    ),
                )

                self.measurement_w.flag_saved = False
                self.memx, self.memy = -1, -1
        '''

    # angle 1st clic -> vertex
    elif self.measurement_w.rb_angle.isChecked():
        if event.button() == Qt.LeftButton:
            draw_point(self, pixmap_x, pixmap_y, self.measurement_w.mark_color, n_player)
            self.memPoints = [(pixmap_x, pixmap_y)]
            self.mem_video = [(x_video, y_video)]

        if event.button() == Qt.RightButton and len(self.memPoints):
            draw_point(self, pixmap_x, pixmap_y, self.measurement_w.mark_color, n_player)
            draw_line(
                self,
                self.memPoints[0][0],
                self.memPoints[0][1],
                pixmap_x,
                pixmap_y,
                self.measurement_w.mark_color,
                n_player,
            )

            self.memPoints.append((pixmap_x, pixmap_y))
            self.mem_video.append((x_video, y_video))

            if len(self.memPoints) == 3:
                append_results(
                    self,
                    (
                        n_player + 1,
                        f"{self.getLaps():.03f}",
                        current_frame,
                        cfg.ANGLE_OBJECT,
                        cfg.NA,
                        cfg.NA,
                        cfg.NA,
                        cfg.NA,
                        round(util.angle(self.memPoints[0], self.memPoints[1], self.memPoints[2]), 1),
                        str(self.mem_video),
                    ),
                )

                self.measurement_w.flag_saved = False
                if current_frame not in self.measurement_w.draw_mem:
                    self.measurement_w.draw_mem[current_frame] = []

                self.measurement_w.draw_mem[current_frame].append(
                    {'player': n_player, 'object_type': cfg.ANGLE_OBJECT, "color": self.measurement_w.mark_color, "coordinates": self.mem_video}
                    )

                self.memPoints, self.mem_video = [], []

    # Area
    elif self.measurement_w.rbArea.isChecked():
        if event.button() == Qt.LeftButton:
            draw_point(self, pixmap_x, pixmap_y, self.measurement_w.mark_color)
            if len(self.memPoints):
                draw_line(
                    self,
                    self.memPoints[-1][0],
                    self.memPoints[-1][1],
                    pixmap_x,
                    pixmap_y,
                    self.measurement_w.mark_color,
                    n_player,
                )
            self.memPoints.append((pixmap_x, pixmap_y))
            self.mem_video.append((x_video, y_video))

        if event.button() == Qt.RightButton and len(self.memPoints) >= 2:

            '''
            draw_point(self, pixmap_x, pixmap_y, self.measurement_w.mark_color, n_player)
            draw_line(
                self,
                self.memPoints[-1][0],
                self.memPoints[-1][1],
                pixmap_x,
                pixmap_y,
                self.measurement_w.mark_color,
                n_player,
            )
            self.memPoints.append((pixmap_x, pixmap_y))
            self.mem_video.append((x_video, y_video))
            '''

            # close polygon
            draw_line(
                self,
                self.memPoints[-1][0],
                self.memPoints[-1][1],
                self.memPoints[0][0],
                self.memPoints[0][1],
                self.measurement_w.mark_color,
                n_player,
            )
            if current_frame not in self.measurement_w.draw_mem:
                self.measurement_w.draw_mem[current_frame] = []

            self.measurement_w.draw_mem[current_frame].append(
                {'player': n_player, 'object_type': cfg.POLYGON_OBJECT, "color": self.measurement_w.mark_color, "coordinates": self.mem_video}
                #[n_player, "polygon", self.measurement_w.mark_color, self.mem_video]
                )

            area = util.polygon_area(self.mem_video)
            try:
                area = area / (float(self.measurement_w.lePx.text()) ** 2) * float(self.measurement_w.leRef.text()) ** 2
            except Exception:
                QMessageBox.critical(
                    None,
                    cfg.programName,
                    "Check reference and pixel values! Values must be numeric.",
                    QMessageBox.Ok | QMessageBox.Default,
                    QMessageBox.NoButton,
                )

            length = util.polyline_length(self.mem_video)
            try:
                length = length / float(self.measurement_w.lePx.text()) * float(self.measurement_w.leRef.text())
            except Exception:
                QMessageBox.critical(
                    None,
                    cfg.programName,
                    "Check reference and pixel values! Values must be numeric.",
                    QMessageBox.Ok | QMessageBox.Default,
                    QMessageBox.NoButton,
                )

            append_results(
                self,
                (
                    n_player + 1,
                    f"{self.getLaps():.03f}",
                    current_frame,
                    cfg.POLYGON_OBJECT,
                    cfg.NA,
                    cfg.NA,
                    round(length, 1),
                    round(area, 1),
                    cfg.NA,
                    str(self.mem_video),
                ),
            )

            self.measurement_w.flag_saved = False
            self.memPoints, self.mem_video = [], []

    # polyline
    elif self.measurement_w.rb_polygon.isChecked():
        if event.button() == Qt.LeftButton:
            draw_point(self, pixmap_x, pixmap_y, self.measurement_w.mark_color)
            if len(self.memPoints):
                draw_line(
                    self,
                    self.memPoints[-1][0],
                    self.memPoints[-1][1],
                    pixmap_x,
                    pixmap_y,
                    self.measurement_w.mark_color,
                    n_player,
                )
            self.memPoints.append((pixmap_x, pixmap_y))
            self.mem_video.append((x_video, y_video))

        if event.button() == Qt.RightButton:
            if current_frame not in self.measurement_w.draw_mem:
                self.measurement_w.draw_mem[current_frame] = []

            self.measurement_w.draw_mem[current_frame].append(
                {'player': n_player, 'object_type': cfg.POLYLINE_OBJECT, "color": self.measurement_w.mark_color, "coordinates": self.mem_video}
                #[n_player, "polyline", self.measurement_w.mark_color, self.mem_video]
                )

            length = util.polyline_length(self.mem_video)
            try:
                length = length / float(self.measurement_w.lePx.text()) * float(self.measurement_w.leRef.text())
            except Exception:
                QMessageBox.critical(
                    None,
                    cfg.programName,
                    "Check reference and pixel values! Values must be numeric.",
                    QMessageBox.Ok | QMessageBox.Default,
                    QMessageBox.NoButton,
                )

            append_results(
                self,
                (
                    n_player + 1,
                    f"{self.getLaps():.03f}",
                    current_frame,
                    cfg.POLYLINE_OBJECT,
                    cfg.NA,
                    cfg.NA,
                    round(length, 1),
                    cfg.NA,
                    cfg.NA,
                    str(self.mem_video),
                ),
            )
            self.memPoints, self.mem_video = [], []
            self.measurement_w.flag_saved = False

    else:
        self.measurement_w.status_lb.setText("<b>Choose a measurement type!</b>")


def redraw_measurements(self):
    """
    redraw measurements from previous frames
    """

    def scale_coord(coord_list: list) -> List[int]:
        """
        scale coordinates from original media resolution to pixmap
        """

        if self.pj[cfg.OBSERVATIONS][self.observationId][cfg.TYPE] == cfg.IMAGES:
            # pixmap_size = QPixmap(self.images_list[self.image_idx]).size()
            original_width, original_height = self.current_image_size
        if self.pj[cfg.OBSERVATIONS][self.observationId][cfg.TYPE] == cfg.MEDIA:
            original_width = dw.player.width
            original_height = dw.player.height

        pixmap_coord_list: List[int] = []
        for idx, coord in enumerate(coord_list):
            if idx % 2 == 0:
                coord_pixmap = round(coord / original_width * dw.frame_viewer.pixmap().width())
            else:
                coord_pixmap = round(coord / original_height * dw.frame_viewer.pixmap().height())
            pixmap_coord_list.append(coord_pixmap)

        return pixmap_coord_list

    logging.debug("Redraw measurement marks")

    if not (hasattr(self, "measurement_w") and self.measurement_w is not None and self.measurement_w.isVisible()):
        return

    if not self.measurement_w.cbPersistentMeasurements.isChecked():
        self.measurement_w.draw_mem = {}
        return



    for idx, dw in enumerate(self.dw_player):
        if self.pj[cfg.OBSERVATIONS][self.observationId][cfg.TYPE] == cfg.MEDIA:
            if dw.player.estimated_frame_number is not None:
                current_frame = dw.player.estimated_frame_number + 1
            else:
                current_frame = cfg.NA
        if self.pj[cfg.OBSERVATIONS][self.observationId][cfg.TYPE] == cfg.IMAGES:
            current_frame = self.image_idx

        for frame in self.measurement_w.draw_mem:
            for element in self.measurement_w.draw_mem[frame]:
                if frame == current_frame:
                    elements_color = element['color']  
                else:
                    elements_color = cfg.PASSIVE_MEASUREMENTS_COLOR

                if element['player'] == idx:
                    if element['object_type'] == cfg.POINT_OBJECT:
                        x, y = scale_coord(element['coordinates'][0])
                        draw_point(self, int(x), int(y), elements_color, n_player=idx)

                    if element['object_type'] == cfg.SEGMENT_OBJECT:
                        x1, y1 = scale_coord(element['coordinates'][0])
                        x2, y2 = scale_coord(element['coordinates'][1])
                        draw_line(self, x1, y1, x2, y2, elements_color, n_player=idx)
                        draw_point(self, x1, y1, elements_color, n_player=idx)
                        draw_point(self, x2, y2, elements_color, n_player=idx)

                    if element['object_type'] == cfg.ANGLE_OBJECT:
                        x1, y1 = scale_coord(element['coordinates'][0])
                        x2, y2 = scale_coord(element['coordinates'][1])
                        x3, y3 = scale_coord(element['coordinates'][2])
                        draw_line(self, x1, y1, x2, y2, elements_color, n_player=idx)
                        draw_line(self, x1, y1, x3, y3, elements_color, n_player=idx)
                        draw_point(self, x1, y1, elements_color, n_player=idx)
                        draw_point(self, x2, y2, elements_color, n_player=idx)
                        draw_point(self, x3, y3, elements_color, n_player=idx)

                    if element['object_type'] == cfg.POLYGON_OBJECT:
                        polygon = QPolygon()

                        for x, y in element['coordinates']:
                            x, y = scale_coord([x, y])
                            polygon.append(QPoint(x, y))
                        painter = QPainter()
                        painter.begin(self.dw_player[idx].frame_viewer.pixmap())
                        painter.setPen(QColor(elements_color))
                        painter.drawPolygon(polygon)
                        painter.end()
                        dw.frame_viewer.update()

                    if element['object_type'] == cfg.POLYLINE_OBJECT:
                        for idx1, p1 in enumerate(element['coordinates'][:-1]):
                            x1, y1 = scale_coord(p1)
                            p2 = element['coordinates'][idx1 + 1]
                            x2, y2 = scale_coord(p2)

                            draw_line(self, x1, y1, x2, y2, elements_color, n_player=idx)


if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)
    w = wgMeasurement(logging.getLogger().getEffectiveLevel())
    w.show()

    sys.exit(app.exec_())
