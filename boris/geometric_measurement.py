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
    QPlainTextEdit,
    QPushButton,
    QRadioButton,
    QVBoxLayout,
    QWidget,
    QColorDialog,
    QSpacerItem,
    QSizePolicy,
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
    mark_color: str = cfg.ACTIVE_MEASUREMENTS_COLOR
    flag_saved = True  # store if measurements are saved
    draw_mem: dict = {}

    def __init__(self):
        super().__init__()

        self.setWindowTitle("Geometric measurements")

        vbox = QVBoxLayout(self)

        self.rbPoint = QRadioButton("Point (left click)")
        vbox.addWidget(self.rbPoint)

        self.rbDistance = QRadioButton("Distance (start: left click, end: right click)")
        vbox.addWidget(self.rbDistance)

        self.rbArea = QRadioButton("Area (left click for area vertices, right click to close area)")
        vbox.addWidget(self.rbArea)

        self.rbAngle = QRadioButton("Angle (vertex: left click, segments: right click)")
        vbox.addWidget(self.rbAngle)

        hbox = QHBoxLayout()
        self.cbPersistentMeasurements = QCheckBox("Measurements are persistent")
        self.cbPersistentMeasurements.setChecked(True)
        hbox.addWidget(self.cbPersistentMeasurements)

        # color chooser
        self.bt_color_chooser = QPushButton("Choose color of marks", clicked=self.choose_marks_color)
        self.bt_color_chooser.setStyleSheet(f"QWidget {{background-color:{self.mark_color}}}")
        hbox.addWidget(self.bt_color_chooser)

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

        self.pte = QPlainTextEdit()
        vbox.addWidget(self.pte)
        self.pte.setReadOnly(True)
        self.pte.setLineWrapMode(QPlainTextEdit.NoWrap)
        # header
        self.pte.setPlainText("Player\tTime\tFrame index\ttype of measurement\tx\ty\tdistance\tarea\tangle")

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
        self.flag_saved = True

    def pbClose_clicked(self):
        """
        Close button
        """
        logging.debug("close function")
        self.close()

    def pbSave_clicked(self):
        """
        Save measurements results in plain text file
        """

        file_formats = [cfg.TSV, cfg.CSV, cfg.ODS, cfg.XLSX, cfg.HTML, cfg.PANDAS_DF]
        if flag_pyreadr_loaded:
            file_formats.append(cfg.RDS)

        file_name, filter_ = QFileDialog().getSaveFileName(
            self, "Save geometric measurements", "", ";;".join(file_formats)
        )
        if not file_name:
            return

        """file_name, _ = QFileDialog().getSaveFileName(
            self, "Save geometric measurements", "", "Text files (*.txt);;All files (*)"
        )"""

        # add correct file extension if not present
        if pl.Path(file_name).suffix != f".{cfg.FILE_NAME_SUFFIX[filter_]}":
            file_name = str(pl.Path(file_name)) + "." + cfg.FILE_NAME_SUFFIX[filter_]
            # check if file with new extension already exists
            if pl.Path(file_name).is_file():
                if (
                    dialog.MessageDialog(
                        cfg.programName, f"The file {file_name} already exists.", (cfg.CANCEL, cfg.OVERWRITE)
                    )
                    == cfg.CANCEL
                ):
                    return

        df = pd.read_csv(io.StringIO(self.pte.toPlainText()), sep="\t")

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
    self.measurement_w.pte.appendPlainText("\t".join([str(x) for x in results]))


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
        """
        QMessageBox.warning(
            self,
            cfg.programName,
            "The Focus area function is not yet available in frame-by-frame mode.",
            QMessageBox.Ok | QMessageBox.Default,
            QMessageBox.NoButton,
        )"""

    x, y = event.pos().x(), event.pos().y()

    # convert label coordinates in pixmap coordinates
    pixmap_x = int(
        x - (self.dw_player[n_player].frame_viewer.width() - self.dw_player[n_player].frame_viewer.pixmap().width()) / 2
    )
    pixmap_y = int(
        y
        - (self.dw_player[n_player].frame_viewer.height() - self.dw_player[n_player].frame_viewer.pixmap().height()) / 2
    )

    if self.pj[cfg.OBSERVATIONS][self.observationId][cfg.TYPE] == cfg.MEDIA:
        # convert pixmap coordinates in video coordinates
        x_video = round(
            (pixmap_x / self.dw_player[n_player].frame_viewer.pixmap().width()) * self.dw_player[n_player].player.width
        )
        y_video = round(
            (pixmap_y / self.dw_player[n_player].frame_viewer.pixmap().height())
            * self.dw_player[n_player].player.height
        )
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
        if event.button() == 1:  # left click
            draw_point(self, pixmap_x, pixmap_y, self.measurement_w.mark_color, n_player)
            if current_frame not in self.measurement_w.draw_mem:
                self.measurement_w.draw_mem[current_frame] = []

            self.measurement_w.draw_mem[current_frame].append(
                [n_player, "point", self.measurement_w.mark_color, x_video, y_video]
            )

            append_results(
                self,
                (
                    n_player + 1,
                    f"{self.getLaps():.03f}",
                    current_frame,
                    "Point",
                    x_video,
                    y_video,
                    cfg.NA,
                    cfg.NA,
                    cfg.NA,
                ),
            )

            self.measurement_w.flag_saved = False

    # distance
    elif self.measurement_w.rbDistance.isChecked():
        if event.button() == 1:  # left
            draw_point(self, pixmap_x, pixmap_y, self.measurement_w.mark_color, n_player)
            self.memx, self.memy = round(pixmap_x), round(pixmap_y)
            self.memx_video, self.memy_video = round(x_video), round(y_video)

        if event.button() == 2 and self.memx != -1 and self.memy != -1:
            draw_point(self, pixmap_x, pixmap_y, self.measurement_w.mark_color, n_player)
            draw_line(self, self.memx, self.memy, pixmap_x, pixmap_y, self.measurement_w.mark_color, n_player)

            if current_frame not in self.measurement_w.draw_mem:
                self.measurement_w.draw_mem[current_frame] = []

            self.measurement_w.draw_mem[current_frame].append(
                [n_player, "line", self.measurement_w.mark_color, self.memx_video, self.memy_video, x_video, y_video]
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
                    "Distance",
                    cfg.NA,
                    cfg.NA,
                    round(distance, 3),
                    cfg.NA,
                    cfg.NA,
                ),
            )

            self.measurement_w.flag_saved = False
            self.memx, self.memy = -1, -1

    # angle 1st clic -> vertex
    elif self.measurement_w.rbAngle.isChecked():
        if event.button() == 1:  # left for vertex
            draw_point(self, pixmap_x, pixmap_y, self.measurement_w.mark_color, n_player)
            self.memPoints = [(pixmap_x, pixmap_y)]
            self.mem_video = [(x_video, y_video)]

        if event.button() == 2 and len(self.memPoints):
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
                        "Angle",
                        cfg.NA,
                        cfg.NA,
                        cfg.NA,
                        cfg.NA,
                        round(util.angle(self.memPoints[0], self.memPoints[1], self.memPoints[2]), 1),
                    ),
                )

                self.measurement_w.flag_saved = False
                if current_frame not in self.measurement_w.draw_mem:
                    self.measurement_w.draw_mem[current_frame] = []

                self.measurement_w.draw_mem[current_frame].append(
                    [n_player, "angle", self.measurement_w.mark_color, self.mem_video]
                )

                self.memPoints, self.mem_video = [], []

    # Area
    elif self.measurement_w.rbArea.isChecked():
        if event.button() == 1:  # left
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

        if event.button() == 2 and len(self.memPoints) >= 2:
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
            area = util.polygon_area(self.mem_video)

            if current_frame not in self.measurement_w.draw_mem:
                self.measurement_w.draw_mem[current_frame] = []

            self.measurement_w.draw_mem[current_frame].append(
                [n_player, "polygon", self.measurement_w.mark_color, self.mem_video]
            )

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

            append_results(
                self,
                (
                    n_player + 1,
                    f"{self.getLaps():.03f}",
                    current_frame,
                    "Area",
                    cfg.NA,
                    cfg.NA,
                    cfg.NA,
                    round(area, 3),
                    cfg.NA,
                ),
            )

            self.measurement_w.flag_saved = False
            self.memPoints, self.mem_video = [], []

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
                    elementsColor = element[2]  # color
                else:
                    elementsColor = cfg.PASSIVE_MEASUREMENTS_COLOR

                if element[0] == idx:
                    if element[1] == "point":
                        x, y = scale_coord(element[3:])

                        draw_point(self, int(x), int(y), elementsColor, n_player=idx)

                    if element[1] == "line":
                        x1, y1, x2, y2 = scale_coord(element[3:])
                        draw_line(self, x1, y1, x2, y2, elementsColor, n_player=idx)
                        draw_point(self, x1, y1, elementsColor, n_player=idx)
                        draw_point(self, x2, y2, elementsColor, n_player=idx)

                    if element[1] == "angle":
                        x1, y1 = scale_coord(element[3][0])
                        x2, y2 = scale_coord(element[3][1])
                        x3, y3 = scale_coord(element[3][2])
                        draw_line(self, x1, y1, x2, y2, elementsColor, n_player=idx)
                        draw_line(self, x1, y1, x3, y3, elementsColor, n_player=idx)
                        draw_point(self, x1, y1, elementsColor, n_player=idx)
                        draw_point(self, x2, y2, elementsColor, n_player=idx)
                        draw_point(self, x3, y3, elementsColor, n_player=idx)

                    if element[1] == "polygon":
                        polygon = QPolygon()

                        for x, y in element[3]:
                            x, y = scale_coord([x, y])
                            polygon.append(QPoint(x, y))
                        painter = QPainter()
                        painter.begin(self.dw_player[idx].frame_viewer.pixmap())
                        painter.setPen(QColor(elementsColor))
                        painter.drawPolygon(polygon)
                        painter.end()
                        dw.frame_viewer.update()


if __name__ == "__main__":
    import sys

    app = QApplication(sys.argv)
    w = wgMeasurement(logging.getLogger().getEffectiveLevel())
    w.show()

    sys.exit(app.exec_())
