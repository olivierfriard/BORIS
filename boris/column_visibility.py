"""
BORIS
Behavioral Observation Research Interactive Software
Copyright 2012-2026 Olivier Friard

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


Show / hide the columns of the ethogram, subjects and events tables.

A right click on the header of a table shows the list of its columns with check boxes.
The hidden columns (header labels) are saved at once in the BORIS configuration file ($HOME/.boris)
in the [hidden_columns] section (the config_param dictionary is saved only when BORIS is closed).
"""

import functools
import pathlib as pl

from PySide6.QtCore import QPoint, QSettings, Qt
from PySide6.QtWidgets import QAbstractItemView, QMenu

ETHOGRAM = "ethogram"
SUBJECTS = "subjects"
EVENTS = "events"


def _settings() -> QSettings:
    return QSettings(str(pl.Path.home() / ".boris"), QSettings.Format.IniFormat)


def hidden_columns(table_name: str) -> list:
    """
    returns the header labels of the hidden columns of the table
    """
    return _settings().value(f"hidden_columns/{table_name}", [], type=list)


def save_hidden_columns(table_name: str, labels: list) -> None:
    settings = _settings()
    settings.setValue(f"hidden_columns/{table_name}", list(labels))
    settings.sync()


def column_labels(view: QAbstractItemView) -> list:
    """
    returns the header labels of the columns of view
    """
    model = view.model()
    if model is None:
        return []
    return [
        str(model.headerData(column, Qt.Orientation.Horizontal, Qt.ItemDataRole.DisplayRole) or "") for column in range(model.columnCount())
    ]


def apply_hidden_columns(view: QAbstractItemView, table_name: str) -> None:
    """
    hide the saved hidden columns of the table (at least one column remains visible)
    """
    hidden = hidden_columns(table_name)
    labels = column_labels(view)
    for column, label in enumerate(labels):
        view.setColumnHidden(column, label in hidden)
    if labels and all(view.isColumnHidden(column) for column in range(len(labels))):
        view.setColumnHidden(0, False)


def set_column_visible(view: QAbstractItemView, table_name: str, label: str, visible: bool) -> None:
    hidden = [x for x in hidden_columns(table_name) if x != label]
    if not visible:
        hidden.append(label)
    save_hidden_columns(table_name, hidden)
    apply_hidden_columns(view, table_name)


def show_all_columns(view: QAbstractItemView, table_name: str) -> None:
    save_hidden_columns(table_name, [])
    apply_hidden_columns(view, table_name)


def columns_menu(view: QAbstractItemView, table_name: str) -> QMenu:
    """
    returns a menu with the columns of view as check boxes
    """
    menu = QMenu(view)
    labels = column_labels(view)
    visible = [column for column in range(len(labels)) if not view.isColumnHidden(column)]
    for column, label in enumerate(labels):
        action = menu.addAction(label or f"Column {column + 1}")
        action.setCheckable(True)
        action.setChecked(column in visible)
        # the last visible column can not be hidden
        action.setEnabled(visible != [column])
        action.toggled.connect(functools.partial(set_column_visible, view, table_name, label))
    menu.addSeparator()
    show_all = menu.addAction("Show all columns")
    show_all.setEnabled(len(visible) < len(labels))
    show_all.triggered.connect(functools.partial(show_all_columns, view, table_name))
    return menu


def show_columns_menu(view: QAbstractItemView, table_name: str, global_position: QPoint) -> None:
    columns_menu(view, table_name).exec(global_position)


def setup(view: QAbstractItemView, table_name: str) -> None:
    """
    show the columns menu with a right click on the header of view and hide the saved hidden columns
    """
    header = view.horizontalHeader()
    header.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
    header.setToolTip("Right-click to show or hide columns")
    header.customContextMenuRequested.connect(lambda position: show_columns_menu(view, table_name, header.mapToGlobal(position)))
    apply_hidden_columns(view, table_name)
