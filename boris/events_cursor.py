"""
BORIS
Behavioral Observation Research Interactive Software
Copyright 2012-2025 Olivier Friard


  This program is free software; you can redistribute it and/or modify
  it under the terms of the GNU General Public License as published by
  the Free Software Foundation; either version 2 of the License, or
  (at your option) any later version.

  This program is distributed in the hope that it will be useful,
  but WITHOUT ANY WARRANTY; without even the implied warranty of
  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
  GNU General Public License for more details.

  You should have received a copy of the GNU General Public License
  along with this program; if not, write to the Free Software
  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
  MA 02110-1301, USA.

"""

from PySide6.QtCore import QPoint, Qt
from PySide6.QtGui import QPolygon, QPen, QColor, QBrush, QPainter
from PySide6.QtWidgets import QStyledItemDelegate


class StyledItemDelegateTriangle(QStyledItemDelegate):
    """
    painter for tv_events with current time highlighting
    """

    def __init__(self, row, parent=None):
        super(StyledItemDelegateTriangle, self).__init__(parent)
        self.row = row

    def paint(self, painter, option, index):
        """
        draw a red triangle on ceel corresponfing to current event
        """

        super(StyledItemDelegateTriangle, self).paint(painter, option, index)

        if self.row == -1:
            return
        if index.row() == self.row:
            triangle = QPolygon(
                [
                    QPoint(option.rect.x() + 15, option.rect.y()),
                    QPoint(option.rect.x(), option.rect.y() - 5),
                    QPoint(option.rect.x(), option.rect.y() + 5),
                ]
            )

            painter.save()
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setBrush(QBrush(QColor(Qt.red)))
            painter.setPen(QPen(QColor(Qt.red)))
            painter.drawPolygon(triangle)
            painter.restore()
